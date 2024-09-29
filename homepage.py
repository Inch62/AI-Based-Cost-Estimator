import customtkinter as ctk
import tkinter as tk
import json
import uuid
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from tkinter import messagebox
from tkinter import simpledialog
from unit import scrap


API_KEY = "AIzaSyAk6BXxfDfj3Ag2ZPVtb31ltaWEfymzn_s"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class ChatFrame(ctk.CTkFrame):
    def __init__(self, master, contract, on_back_to_subscription):
        super().__init__(master=master)
        self.on_back_to_subscription = on_back_to_subscription
        self.contract = contract

        self.chat_history = tk.Text(self, width=80, height=30, wrap=tk.WORD, bg="black", fg="white", font=('Arial', 12))
        self.chat_history.tag_configure("ai", foreground="white", justify='left')
        self.chat_history.tag_configure("user", foreground="white", justify='right')
        self.chat_history.configure(state='disabled')
        self.chat_history.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.user_input = tk.Text(self, width=60, height=3, wrap=tk.WORD, bg="white", fg="black", font=('Arial', 12))
        self.user_input.pack(pady=10, padx=10, side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.send_button = ctk.CTkButton(self, text="Send", command=self.handle_send)
        self.send_button.pack(pady=10, padx=10, side=tk.LEFT)

        self.back_button = ctk.CTkButton(self, text="Back", command=self.handle_back)
        self.back_button.pack(pady=10, padx=10, side=tk.LEFT)

        self.display_initial_analysis()

    def handle_back(self):
        self.master.destroy()
        self.on_back_to_subscription()

    def scrape_repair_costs(self, product_name):
        try:
            conditions = self.contract['product_details'].get('Condition', '').lower()
            keywords = ["battery", "display", "software issue", "touch screen", "panel glass", "camera lens"]
            condition_cost_mapping = {}

            for keyword in keywords:
                if keyword in conditions:
                    search_url = f"https://www.ifixit.com/Search?query={product_name.replace(' ', '+')}+{keyword.replace(' ', '+')}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    response = requests.get(search_url, headers=headers)
                    soup = BeautifulSoup(response.text, 'html.parser')

                    for cost_item in soup.find_all('div', class_='search-result'):
                        try:
                            part_cost = cost_item.find('span', class_='price').get_text().strip()
                            part_cost = float(part_cost.replace('$', '').replace(',', ''))
                            condition_cost_mapping[keyword] = part_cost
                            break
                        except (AttributeError, ValueError):
                            continue

            # Use default prices from unit.py if scraping did not find the cost
            for keyword in keywords:
                if keyword in conditions and keyword not in condition_cost_mapping:
                    condition_cost_mapping[keyword] = scrap.get(keyword, 0)

            return condition_cost_mapping

        except Exception as e:
            print(f"Error scraping repair costs: {str(e)}")
            return {}

    def calculate_recommended_price(self, contract):
        try:
            base_price = float(contract['price'])
            condition_costs = self.scrape_repair_costs(contract['product_name'])
            total_repair_cost = sum(condition_costs.values())

            years_used = int(contract['product_details']['Year used'])
            depreciation_rate = years_used / 10.0

            recommended_price = base_price - total_repair_cost - (base_price * depreciation_rate)
            return recommended_price, total_repair_cost, depreciation_rate

        except KeyError as e:
            print(f"Error: Missing key '{e.args[0]}' in contract data")
        except Exception as e:
            print(f"Error calculating recommended price: {str(e)}")
        return None, 0.0, 0.0

    def analyze_product(self, question):
        try:
            recommended_price, total_repair_cost, depreciation_rate = self.calculate_recommended_price(self.contract)
            condition_costs = self.scrape_repair_costs(self.contract['product_name'])

            product_details = (
                f"Product Name: {self.contract['product_name']}\n"
                f"Price: ${self.contract['price']}\n"
                f"Specifications:\n"
                f"  Storage: {self.contract['product_details'].get('Storage', '')}\n"
                f"  RAM: {self.contract['product_details'].get('RAM', '')}\n"
                f"  Display: {self.contract['product_details'].get('Display', '')}\n"
                f"  Year used: {self.contract['product_details'].get('Year used', '')}\n"
                f"  Condition: {self.contract['product_details'].get('Condition', '')}\n"
            )

            repair_costs_str = "\n".join([f"  - {cond}: ${cost:.2f}" for cond, cost in condition_costs.items()])

            prompt = (
                f"{product_details}\n"
                f"Question: {question}\n"
            )

            if "breakdown and recommend" in question.lower():
                prompt += (
                    f"Recommended Price: ${recommended_price:.2f}\n"
                    f"\n**Breakdown of Repair Costs:**\n"
                    f"{repair_costs_str}\n"
                    f"Depreciation Rate: {depreciation_rate:.2f}\n"
                )

            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            return f"AI: Error processing your request. {str(e)}"

    def handle_send(self):
        user_text = self.user_input.get("1.0", tk.END).strip()
        if user_text:
            self.add_to_chat(user_text, "user")
            self.user_input.delete("1.0", tk.END)
            ai_response = self.analyze_product(user_text)
            self.add_to_chat(ai_response, "ai")

    def add_to_chat(self, text, sender):
        self.chat_history.configure(state='normal')
        self.chat_history.insert(tk.END, f"{sender}: {text}\n", sender)
        self.chat_history.configure(state='disabled')
        self.chat_history.yview(tk.END)

    def display_initial_analysis(self):
        initial_analysis = self.analyze_product("breakdown and recommend")
        self.add_to_chat(initial_analysis, "ai")

def load_contract():
    try:
        with open('temp.json', 'r') as f:
            contract = json.load(f)

        if contract['price'] == "N/A":
            contract['price'] = simpledialog.askfloat("Enter Price", "Enter the price of the device", minvalue=0.0, parent=None)
            with open('temp.json', 'w') as f:
                json.dump(contract, f, indent=4)

        print("Contract loaded from temp.json:", contract)

        if not isinstance(contract, dict):
            raise ValueError("The content of temp.json is not a single contract.")

        return contract

    except FileNotFoundError:
        print("Error: temp.json not found.")
    except json.JSONDecodeError:
        print("Error: Failed to parse temp.json. Invalid JSON format.")
    except Exception as e:
        print(f"Error loading contract: {str(e)}")
    return None

def open_chat():
    try:
        contract = load_contract()
        if contract:
            open_window = ctk.CTkToplevel()
            open_window.geometry("800x600")
            open_window.title(f"Chat with AI")

            chat_frame = ChatFrame(open_window, contract, on_back_to_subscription=lambda: open_window.destroy())
            chat_frame.pack(fill="both", expand=True)

            open_window.mainloop()

    except Exception as e:
        print(f"Error opening chat: {str(e)}")

def save_contract(product_id, seller_name, product_name, price, product_details):
    new_contract = {
        "product_id": product_id,
        "seller_name": seller_name,
        "product_name": product_name,
        "price": price,
        "product_details": product_details,
        "bidder_name": "-",
        "bidder_email": "-",
        "counter_offer": "-",
        "status": "Pending"
    }

    try:
        with open("contract.json", "r") as f:
            contracts = json.load(f)
    except FileNotFoundError:
        contracts = []

    contracts.append(new_contract)

    with open("contract.json", "w") as f:
        json.dump(contracts, f, indent=4)

    print(f"Contract saved with Product ID: {product_id}")


def open_create_deal_window(username):
    create_deal_window = ctk.CTkToplevel()
    create_deal_window.geometry("400x800")
    create_deal_window.title("Create Deal")

    # Function to save contract details
    def save_contract1(product_id, seller_name, product_name, price, product_details):
        contract = {
            "product_id": product_id,
            "seller_name": seller_name,
            "product_name": product_name,
            "price": "N/A",
            "product_details": product_details
        }
        # Example save function implementation
        with open('temp.json', 'w') as json_file:
            json.dump(contract, json_file, indent=4)
        open_chat()

    # Function to handle "Ask AI" button click
    def ask_ai():
        product_id = str(uuid.uuid4())[:8]
        product_name = product_name_entry.get().strip()
        seller_name = seller_name_entry.get().strip()
        price = price_entry.get().strip()
        ram = ram_entry.get().strip()
        storage = storage_entry.get().strip()
        processor = processor_entry.get().strip()
        display = display_entry.get().strip()
        year_of_purchase = year_of_purchase_entry.get().strip()
        product_condition = product_condition_entry.get().strip()

        # Check if all fields except price are filled
        if (product_name and seller_name and ram and storage and processor and
            display and year_of_purchase and product_condition):
            product_details = {
                "RAM": ram,
                "Storage": storage,
                "Processor": processor,
                "Display": display,
                "Year used": year_of_purchase,
                "Condition": product_condition
            }

            save_contract1(product_id, seller_name, product_name, price, product_details)
        else:
            messagebox.showerror("Error", "Please fill in all details except for Price.")

    # Product Name
    ctk.CTkLabel(create_deal_window, text="Product Name:").pack(pady=10)
    product_name_entry = ctk.CTkEntry(create_deal_window)
    product_name_entry.pack(pady=5)

    # Seller Name
    ctk.CTkLabel(create_deal_window, text="Seller Name:").pack(pady=10)
    seller_name_entry = ctk.CTkEntry(create_deal_window)
    seller_name_entry.insert(0, username)  # Insert username as default value
    seller_name_entry.pack(pady=5)

    # Price and Ask AI Button
    price_frame = ctk.CTkFrame(create_deal_window)
    price_frame.pack(pady=10, fill=tk.X)

    ctk.CTkLabel(price_frame, text="Price:").pack(pady=5, padx=5, side=tk.LEFT)
    price_entry = ctk.CTkEntry(price_frame)
    price_entry.pack(pady=5, padx=5, side=tk.LEFT, expand=True)

    ctk.CTkButton(price_frame, text="Ask AI", command=ask_ai).pack(pady=5, padx=5, side=tk.LEFT)

    # Row Frame for RAM, Storage, Processor
    row_frame = ctk.CTkFrame(create_deal_window)
    row_frame.pack(pady=10, fill=tk.X)

    # RAM
    ctk.CTkLabel(row_frame, text="RAM:").pack(pady=5, padx=5, side=tk.LEFT)
    ram_entry = ctk.CTkEntry(row_frame)
    ram_entry.pack(pady=5, padx=5, side=tk.LEFT, expand=True)

    # Storage
    ctk.CTkLabel(row_frame, text="Storage:").pack(pady=5, padx=5, side=tk.LEFT)
    storage_entry = ctk.CTkEntry(row_frame)
    storage_entry.pack(pady=5, padx=5, side=tk.LEFT, expand=True)

    # Processor
    ctk.CTkLabel(row_frame, text="Processor:").pack(pady=5, padx=5, side=tk.LEFT)
    processor_entry = ctk.CTkEntry(row_frame)
    processor_entry.pack(pady=5, padx=5, side=tk.LEFT, expand=True)

    # Display
    ctk.CTkLabel(create_deal_window, text="Display:").pack(pady=10)
    display_entry = ctk.CTkEntry(create_deal_window)
    display_entry.pack(pady=5)

    # Year of Purchase
    ctk.CTkLabel(create_deal_window, text="Year used:").pack(pady=10)
    year_of_purchase_entry = ctk.CTkEntry(create_deal_window)
    year_of_purchase_entry.pack(pady=5)

    # Product Condition
    ctk.CTkLabel(create_deal_window, text="Product Condition:").pack(pady=10)
    product_condition_entry = ctk.CTkEntry(create_deal_window)
    product_condition_entry.pack(pady=5)

    def submit_contract():
        product_id = str(uuid.uuid4())[:8]
        product_name = product_name_entry.get()
        seller_name = seller_name_entry.get()
        price = price_entry.get()
        ram = ram_entry.get()
        storage = storage_entry.get()
        processor = processor_entry.get()
        display = display_entry.get()
        year_of_purchase = year_of_purchase_entry.get()
        product_condition = product_condition_entry.get()
        product_details = {
            "RAM": ram,
            "Storage": storage,
            "Processor": processor,
            "Display": display,
            "Year used": year_of_purchase,
            "Condition": product_condition
        }

        save_contract(product_id, seller_name, product_name, price, product_details)
        create_deal_window.destroy()

    # Submit Contract Button
    ctk.CTkButton(create_deal_window, text="Submit Contract", command=submit_contract).pack(pady=10)

    create_deal_window.mainloop()
    
def show_product_details(contract):
    details_frame = ctk.CTkToplevel()
    details_frame.geometry("400x300")
    details_frame.title("Product Details")

    # Creating a frame to hold the product details
    details_container = ctk.CTkFrame(details_frame)
    details_container.pack(pady=20, padx=20, fill="both", expand=True)

    # Iterating through product details and adding them to the container
    for key, value in contract["product_details"].items():
        detail_label = ctk.CTkLabel(details_container, text=f"{key}: {value}", wraplength=380)
        detail_label.pack(anchor="w", pady=2, padx=2)

    close_button = ctk.CTkButton(details_frame, text="Close", command=details_frame.destroy)
    close_button.pack(pady=10)

def open_negotiate_window(product_id, username, email):
    negotiate_window = ctk.CTkToplevel()
    negotiate_window.geometry("400x300")
    negotiate_window.title("Negotiate")

    ctk.CTkLabel(negotiate_window, text="Counter Offer:").pack(pady=10)
    counter_offer_entry = ctk.CTkEntry(negotiate_window)
    counter_offer_entry.pack(pady=5)

    ctk.CTkLabel(negotiate_window, text="Message:").pack(pady=10)
    message_textbox = ctk.CTkTextbox(negotiate_window, height=5)
    message_textbox.pack(pady=5)

    def submit_negotiation():
        counter_offer = counter_offer_entry.get()
        message = message_textbox.get("1.0", ctk.END).strip()
        save_negotiation(product_id, counter_offer, message, username, email)
        negotiate_window.destroy()

    ctk.CTkButton(negotiate_window, text="OK", command=submit_negotiation).pack(pady=10)

    def accept_offer():
        # Set default values for bidder's name, email, counter offer, and message
        bidder_name = username
        bidder_email = email
        counter_offer = counter_offer_entry.get()  # Get the counter offer from the entry field
        message = "I want to buy this at the given price"

        # Save negotiation details
        save_negotiation(product_id, counter_offer, message, bidder_name, bidder_email)
        negotiate_window.destroy()

    ctk.CTkButton(negotiate_window, text="Accept Offer", command=accept_offer).pack(pady=10)

    negotiate_window.mainloop()

def open_ordered_deals_window(username):
    ordered_deals_window = ctk.CTkToplevel()
    ordered_deals_window.title("All Biddings")
    ordered_deals_window.geometry("800x400")

    # Title
    ctk.CTkLabel(ordered_deals_window, text="All Biddings", font=("Arial", 20, "bold")).pack(pady=10)

    # Table headers
    headers = ["Product ID", "Seller Name", "Product Name", "Price", "Status"]
    headers_frame = ctk.CTkFrame(ordered_deals_window)
    headers_frame.pack(fill="x")

    for col, header in enumerate(headers):
        ctk.CTkLabel(headers_frame, text=header, font=("Arial", 12, "bold")).pack(side="left", padx=5, pady=5)

    try:
        with open("negotiated.json", "r") as f:
            negotiated_data = json.load(f)
    except FileNotFoundError:
        negotiated_data = []

    if not any(negotiation.get("bidder_name") == username for negotiation in negotiated_data):
        ctk.CTkLabel(ordered_deals_window, text="No biddings found.", font=("Arial", 12)).pack(pady=20)
    else:
        for negotiation in negotiated_data:
            if negotiation.get("bidder_name") == username:
                deal_frame = ctk.CTkFrame(ordered_deals_window)
                deal_frame.pack(fill="x")

                # Use get() to safely access dictionary keys
                product_id = negotiation.get("product_id", "N/A")
                seller_name = negotiation.get("seller_name", "N/A")
                product_name = negotiation.get("product_name", "N/A")
                price = negotiation.get("price", "N/A")
                status = negotiation.get("status", "N/A")

                ctk.CTkLabel(deal_frame, text=product_id, width=15, anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(deal_frame, text=seller_name, width=15, anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(deal_frame, text=product_name, width=15, anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(deal_frame, text=price, width=10, anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(deal_frame, text=status, width=10, anchor="w").pack(side="left", padx=5, pady=5)

    # OK Button
    ok_button = ctk.CTkButton(ordered_deals_window, text="OK", command=ordered_deals_window.destroy)
    ok_button.pack(pady=10)

    ordered_deals_window.mainloop()

def save_negotiation(product_id, counter_offer, message, username, email):
    try:
        with open("negotiated.json", "r") as f:
            negotiated_data = json.load(f)
            if not isinstance(negotiated_data, list):
                negotiated_data = []
    except (FileNotFoundError, json.JSONDecodeError):
        negotiated_data = []

    with open("contract.json", "r") as f:
        contracts = json.load(f)

    product = next((item for item in contracts if item["product_id"] == product_id), None)
    if product:
        negotiation_data = product.copy()
        negotiation_data["bidder_name"] = username
        negotiation_data["bidder_email"] = email
        negotiation_data["counter_offer"] = counter_offer
        negotiation_data["message"] = message

        existing_negotiation = next((item for item in negotiated_data if item.get("product_id") == product_id), None)
        if existing_negotiation:
            negotiation_data["negotiation_id"] = len(negotiated_data) + 1
            negotiated_data.append(negotiation_data)
        else:
            negotiated_data.append(negotiation_data)

        with open("negotiated.json", "w") as file:
            json.dump(negotiated_data, file, indent=4)
        print("Negotiation saved")
    else:
        print(f"Product with ID '{product_id}' not found in contracts.json")


def create_homepage_frame(root, username, email, on_back):
    frame = ctk.CTkFrame(root)
    frame.pack(expand=True, fill="both")

    username_label = ctk.CTkLabel(frame, text=f"Welcome, {username}", font=("Arial", 24, "bold"))
    username_label.grid(row=0, column=0, padx=10, pady=10, columnspan=3)

    nav_bar = ctk.CTkFrame(frame)
    nav_bar.grid(row=1, column=0, columnspan=3, pady=10)

    create_deal_button = ctk.CTkButton(nav_bar, text="Create Deal", command=lambda: open_create_deal_window(username))
    create_deal_button.pack(side="left", padx=10)

    my_deal_offers_button = ctk.CTkButton(nav_bar, text="My Deal Offers", command=lambda: open_my_deal_offers_window(username))
    my_deal_offers_button.pack(side="left", padx=10)

    ordered_deals_button = ctk.CTkButton(nav_bar, text="Ordered Deals", command=lambda: open_ordered_deals_window(username))
    ordered_deals_button.pack(side="left", padx=10)

    # Add Refresh Button
    refresh_button = ctk.CTkButton(nav_bar, text="Refresh", command=lambda: refresh_homepage(root, contract_frame, username, email))
    refresh_button.pack(side="left", padx=10)

    logout_button = ctk.CTkButton(nav_bar, text="Logout", command= on_back)
    logout_button.pack(side="right", padx=10)

    # Create a frame to hold the contracts
    contract_frame = ctk.CTkFrame(frame)
    contract_frame.grid(row=2, column=0, padx=10, pady=10, columnspan=3)

    # Load contracts initially
    load_contracts(contract_frame, username, email)

    return frame, contract_frame

def load_contracts(frame, username, email):
    # Clear the frame before loading contracts
    for widget in frame.winfo_children():
        widget.destroy()

    with open("contract.json", "r") as f:
        contracts = json.load(f)

    headers = ["Product ID", "Seller Name", "Product Name", "Price", "Product Details", "Deal Status","Offer"]
    for col, header in enumerate(headers):
        header_label = ctk.CTkLabel(frame, text=header, font=("Arial", 12, "bold"))
        header_label.grid(row=0, column=col, padx=5, pady=5)

    row = 1
    for contract in contracts:
        if contract["seller_name"] != username and contract["status"] == "Pending":
            contract.pop("bidder_name", None)
            contract.pop("bidder_email", None)
            contract.pop("counter_offer", None)
            
            for col, key in enumerate(contract.keys()):
                if key == "product_details":
                    button = ctk.CTkButton(frame, text="View", command=lambda c=contract: show_product_details(c))
                    button.grid(row=row, column=col, padx=5, pady=5)
                else:
                    value_label = ctk.CTkLabel(frame, text=contract[key])
                    value_label.grid(row=row, column=col, padx=5, pady=5)
            
            negotiate_button = ctk.CTkButton(frame, text="Negotiate", command=lambda pid=contract["product_id"]: open_negotiate_window(pid, username, email))
            negotiate_button.grid(row=row, column=len(contract.keys()), padx=5, pady=5)

           # ask_ai_button = ctk.CTkButton(frame, text="Ask AI", command=open_chat)
           # ask_ai_button.grid(row=row, column=len(contract.keys())+1, padx=5, pady=5)

            row += 1


def refresh_homepage(root, contract_frame, username, email):
    # Destroy the contract_frame to clear existing contract listings
    for widget in contract_frame.winfo_children():
        widget.destroy()
    
    # Reload contracts into the cleared contract_frame
    load_contracts(contract_frame, username, email)

def logout(root):
    # Destroy the main root window (homepage)
    #root.destroy()
    on_back

    # Create a new login window
    new_root = ctk.CTk()
    new_root.title("Ebay-like App - Login")
    new_root.geometry("400x300")

    login_frame = login.create_login_frame(new_root, on_login)
    login_frame.pack(expand=True, fill="both")

    new_root.mainloop()


"""
def open_my_deal_offers_window(username):
    my_deal_offers_window = ctk.CTkToplevel()
    my_deal_offers_window.title("My Contracts")
    my_deal_offers_window.geometry("800x400")

    # Title
    ctk.CTkLabel(my_deal_offers_window, text="My Contracts", font=("Arial", 20, "bold")).pack(pady=10)

    # Table headers (excluding "Product Details")
    headers = ["Product ID", "Seller Name", "Product Name", "Price", "Year of Purchase", "Product Condition", "Deal Status", "Action"]
    headers_frame = ctk.CTkFrame(my_deal_offers_window)
    headers_frame.pack()

    for col, header in enumerate(headers):
        ctk.CTkLabel(headers_frame, text=header, font=("Arial", 12, "bold")).pack(side="left", padx=5, pady=5)

    try:
        with open("contract.json", "r") as f:
            contracts = json.load(f)
    except FileNotFoundError:
        contracts = []

    for contract in contracts:
        if contract.get("seller_name") == username:
            contract_frame = ctk.CTkFrame(my_deal_offers_window)
            contract_frame.pack()

            # Use get() to safely access dictionary keys
            product_id = contract.get("product_id", "N/A")
            seller_name = contract.get("seller_name", "N/A")
            product_name = contract.get("product_name", "N/A")
            price = contract.get("price", "N/A")
            year_of_purchase = contract.get("year_of_purchase", "N/A")
            product_condition = contract.get("product_condition", "N/A")
            status = contract.get("status", "N/A")

            ctk.CTkLabel(contract_frame, text=product_id).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(contract_frame, text=seller_name).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(contract_frame, text=product_name).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(contract_frame, text=price).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(contract_frame, text=year_of_purchase).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(contract_frame, text=product_condition).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(contract_frame, text=status).pack(side="left", padx=5, pady=5)

            ctk.CTkButton(contract_frame, text="View Deals", command=lambda cid=product_id: view_deals(cid)).pack(side="left", padx=5, pady=5)

    my_deal_offers_window.mainloop()

"""
def open_my_deal_offers_window(username):
    my_deal_offers_window = ctk.CTkToplevel()
    my_deal_offers_window.title("My Contracts")
    my_deal_offers_window.geometry("800x400")

    # Title
    ctk.CTkLabel(my_deal_offers_window, text="My Contracts", font=("Arial", 20, "bold")).pack(pady=10)

    # Table headers (excluding "Product Details")
    headers = ["Product ID", "Seller Name", "Product Name", "Price", "Year of Purchase", "Deal Status", "Action"]
    headers_frame = ctk.CTkFrame(my_deal_offers_window)
    headers_frame.pack(fill="x")

    # Define fixed widths for each column
    column_widths = [15, 15, 15, 10, 10, 15, 10, 10]

    for col, header in enumerate(headers):
        ctk.CTkLabel(headers_frame, text=header, font=("Arial", 12, "bold"), width=column_widths[col], anchor="w").pack(side="left", padx=5, pady=5)

    try:
        with open("contract.json", "r") as f:
            contracts = json.load(f)
    except FileNotFoundError:
        contracts = []

    if not any(contract.get("seller_name") == username for contract in contracts):
        ctk.CTkLabel(my_deal_offers_window, text="No contracts found.", font=("Arial", 12)).pack(pady=20)
        ctk.CTkButton(my_deal_offers_window, text="OK", command=my_deal_offers_window.destroy).pack()
    else:
        for contract in contracts:
            if contract.get("seller_name") == username:
                contract_frame = ctk.CTkFrame(my_deal_offers_window)
                contract_frame.pack(fill="x")

                # Use get() to safely access dictionary keys
                product_id = contract.get("product_id", "N/A")
                seller_name = contract.get("seller_name", "N/A")
                product_name = contract.get("product_name", "N/A")
                price = contract.get("price", "N/A")
                year_of_purchase = contract.get("year_of_purchase", "N/A")
               # product_condition = contract.get("product_condition", "N/A")
                status = contract.get("status", "N/A")

                ctk.CTkLabel(contract_frame, text=product_id, width=column_widths[0], anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(contract_frame, text=seller_name, width=column_widths[1], anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(contract_frame, text=product_name, width=column_widths[2], anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(contract_frame, text=price, width=column_widths[3], anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(contract_frame, text=year_of_purchase, width=column_widths[4], anchor="w").pack(side="left", padx=5, pady=5)
               # ctk.CTkLabel(contract_frame, text=product_condition, width=column_widths[5], anchor="w").pack(side="left", padx=5, pady=5)
                ctk.CTkLabel(contract_frame, text=status, width=column_widths[6], anchor="w").pack(side="left", padx=5, pady=5)

                ctk.CTkButton(contract_frame, text="View Deals", command=lambda cid=product_id: view_deals(cid)).pack(side="left", padx=5, pady=5)
                

    my_deal_offers_window.mainloop()


def view_deals(product_id):
    negotiate_window = ctk.CTkToplevel()
    negotiate_window.title("Negotiation Details")
    negotiate_window.geometry("600x400")

    ctk.CTkLabel(negotiate_window, text="Negotiation Details", font=("Arial", 20, "bold")).pack(pady=10)

    try:
        with open("negotiated.json", "r") as f:
            negotiated_data = json.load(f)
    except FileNotFoundError:
        negotiated_data = []

    negotiation_found = False
    for negotiation in negotiated_data:
        if negotiation["product_id"] == product_id:
            negotiation_found = True

            ctk.CTkLabel(negotiate_window, text=f"Bidder Name: {negotiation['bidder_name']}").pack(pady=5)
            ctk.CTkLabel(negotiate_window, text=f"Bidder Email: {negotiation['bidder_email']}").pack(pady=5)
            ctk.CTkLabel(negotiate_window, text=f"Counter Offer: {negotiation['counter_offer']}").pack(pady=5)
            ctk.CTkLabel(negotiate_window, text=f"Message:\n{negotiation['message']}").pack(pady=5)

            # Accept and Refuse buttons
            action_frame = ctk.CTkFrame(negotiate_window)
            action_frame.pack(pady=10)

            accept_button = ctk.CTkButton(action_frame, text="Accept", command=lambda pid=product_id, window=negotiate_window: accept_offer(pid, window))
            accept_button.pack(side="left", padx=10)

            refuse_button = ctk.CTkButton(action_frame, text="Refuse", command=lambda pid=product_id, window=negotiate_window: refuse_offer(pid, window))
            refuse_button.pack(side="left", padx=10)

            break

    if not negotiation_found:
        ctk.CTkLabel(negotiate_window, text="No Bidding Available").pack(pady=20)

    # Make the window modal
    negotiate_window.grab_set()
    negotiate_window.wait_window()

def accept_offer(product_id, negotiate_window):
    # Update status to "Accepted" in contract.json
    with open("contract.json", "r+") as f:
        contracts = json.load(f)
        for contract in contracts:
            if contract["product_id"] == product_id:
                contract["status"] = "Accepted"
                break
        f.seek(0)
        json.dump(contracts, f, indent=4)
        f.truncate()

    # Update status to "Accepted" in negotiated.json
    with open("negotiated.json", "r+") as f:
        negotiated_data = json.load(f)
        for negotiation in negotiated_data:
            if negotiation["product_id"] == product_id:
                negotiation["status"] = "Accepted"
                break
        f.seek(0)
        json.dump(negotiated_data, f, indent=4)
        f.truncate()

    print(f"Accepted offer for Product ID: {product_id}")
    negotiate_window.destroy()

def refuse_offer(product_id, negotiate_window):
    # Update status to "Refused" in contract.json
    with open("contract.json", "r+") as f:
        contracts = json.load(f)
        for contract in contracts:
            if contract["product_id"] == product_id:
                contract["status"] = "Refused"
                break
        f.seek(0)
        json.dump(contracts, f, indent=4)
        f.truncate()

    # Update status to "Refused" in negotiated.json
    with open("negotiated.json", "r+") as f:
        negotiated_data = json.load(f)
        for negotiation in negotiated_data:
            if negotiation["product_id"] == product_id:
                negotiation["status"] = "Refused"
                break
        f.seek(0)
        json.dump(negotiated_data, f, indent=4)
        f.truncate()

    print(f"Refused offer for Product ID: {product_id}")
    negotiate_window.destroy()



