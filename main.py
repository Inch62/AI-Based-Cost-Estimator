import customtkinter as ctk
import login
import homepage

user_info = {}

def on_login(email, username):
    global user_info, login_frame, homepage_frame, contract_frame
    user_info = {"email": email, "username": username}
    login_frame.pack_forget()
    homepage_frame, contract_frame = homepage.create_homepage_frame(root, username, email, on_back)
    homepage_frame.pack(expand=True, fill="both")

def on_back():
    global login_frame, homepage_frame
    if homepage_frame:
        homepage_frame.pack_forget()
    login_frame = login.create_login_frame(root, on_login)
    login_frame.pack(expand=True, fill="both")

def main():
    global root, login_frame, homepage_frame
    root = ctk.CTk()
    root.title("zFinder AI")
    root.geometry("800x600")

    login_frame = login.create_login_frame(root, on_login)
    login_frame.pack(expand=True, fill="both")

    root.mainloop()

if __name__ == "__main__":
    main()
