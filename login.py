import customtkinter as ctk
from tkinter import messagebox
import json

# Function to create the main login frame
def create_login_frame(root, on_login):
    frame = ctk.CTkFrame(root)
    frame.pack(expand=True, fill="both")

    # Centered heading "zFinder AI"
    heading_label = ctk.CTkLabel(frame, text="zFinder AI", font=("Arial", 24, "bold"))
    heading_label.grid(row=0, column=0, columnspan=2, pady=(100, 20))  # Adjust top padding for centering

    # Card-like layout for inputs and buttons
    card_frame = ctk.CTkFrame(frame)
    card_frame.grid(row=1, column=0, padx=50, pady=50, columnspan=2)

    username_label = ctk.CTkLabel(card_frame, text="Username:")
    username_label.grid(row=1, column=0, padx=10, pady=10)

    username_entry = ctk.CTkEntry(card_frame)
    username_entry.grid(row=1, column=1, padx=10, pady=10)

    email_label = ctk.CTkLabel(card_frame, text="Email:")
    email_label.grid(row=0, column=0, padx=10, pady=10)

    email_entry = ctk.CTkEntry(card_frame)
    email_entry.grid(row=0, column=1, padx=10, pady=10)

    

    password_label = ctk.CTkLabel(card_frame, text="Password:")
    password_label.grid(row=2, column=0, padx=10, pady=10)

    password_entry = ctk.CTkEntry(card_frame, show='*')
    password_entry.grid(row=2, column=1, padx=10, pady=10)

    def login():
        email = email_entry.get()
        username = username_entry.get()
        password = password_entry.get()

        if email and username and password:
            if validate_login(email, username, password):
                on_login(email, username)
            else:
                messagebox.showerror("Error", "User not found")
        else:
            messagebox.showerror("Error", "All fields are required")

    login_button = ctk.CTkButton(card_frame, text="Login", command=login)
    login_button.grid(row=3, columnspan=2, pady=20)

    create_account_button = ctk.CTkButton(frame, text="Create Account", command=create_account_window)
    create_account_button.grid(row=2, column=0, columnspan=2, pady=10)

    return frame

# Function to create the "Create Account" window
def create_account_window():
    account_window = ctk.CTk()
    account_window.title("Create Account")
    account_window.geometry("400x300")

    account_frame = ctk.CTkFrame(account_window)
    account_frame.pack(expand=True, fill="both")

    username_label = ctk.CTkLabel(account_frame, text="Username:")
    username_label.grid(row=0, column=0, padx=10, pady=10)

    username_entry = ctk.CTkEntry(account_frame)
    username_entry.grid(row=0, column=1, padx=10, pady=10)

    email_label = ctk.CTkLabel(account_frame, text="Email:")
    email_label.grid(row=1, column=0, padx=10, pady=10)

    email_entry = ctk.CTkEntry(account_frame)
    email_entry.grid(row=1, column=1, padx=10, pady=10)

    password_label = ctk.CTkLabel(account_frame, text="Password:")
    password_label.grid(row=2, column=0, padx=10, pady=10)

    password_entry = ctk.CTkEntry(account_frame, show='*')
    password_entry.grid(row=2, column=1, padx=10, pady=10)

    def save_account():
        username = username_entry.get()
        email = email_entry.get()
        password = password_entry.get()

        if username and email and password:
            save_to_database(username, email, password)
            account_window.destroy()
        else:
            messagebox.showerror("Error", "All fields are required")

    ok_button = ctk.CTkButton(account_frame, text="OK", command=save_account)
    ok_button.grid(row=3, columnspan=2, pady=20)

    account_window.mainloop()

# Function to save account details to user_db.json
def save_to_database(username, email, password):
    user_data = {"username": username, "email": email, "password": password}

    with open("user_db.json", "a") as f:
        json.dump(user_data, f)
        f.write("\n")  # Write each user data on a new line

# Function to validate login credentials
def validate_login(email, username, password):
    with open("user_db.json", "r") as f:
        for line in f:
            user_data = json.loads(line)
            if user_data["email"] == email and user_data["username"] == username and user_data["password"] == password:
                return True
    return False
