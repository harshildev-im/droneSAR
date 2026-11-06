import tkinter as tk
from tkinter import messagebox
from database import Database


class LoginWindow:

    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success

        self.root.title("White Cloud DMS 1.0 - Login")
        self.root.geometry("400x300")
        self.root.configure(bg="black")

        # Title
        tk.Label(
            root,
            text="White Cloud DMS 1.0",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="black"
        ).pack(pady=20)

        # User ID
        tk.Label(
            root,
            text="User ID",
            fg="white",
            bg="black"
        ).pack()

        self.userid_entry = tk.Entry(
            root,
            width=30
        )
        self.userid_entry.pack(pady=5)

        # Password
        tk.Label(
            root,
            text="Password",
            fg="white",
            bg="black"
        ).pack()

        self.password_entry = tk.Entry(
            root,
            width=30,
            show="*"
        )
        self.password_entry.pack(pady=5)

        # Buttons
        tk.Button(
            root,
            text="Login",
            width=15,
            command=self.login
        ).pack(pady=10)

        tk.Button(
            root,
            text="Sign Up",
            width=15,
            command=self.signup
        ).pack()

        # Database
        self.db = Database()

        if not self.db.connect_db():
            messagebox.showerror(
                "Database Error",
                "Could not connect to the database."
            )

    def login(self):

        userid = self.userid_entry.get().strip()
        password = self.password_entry.get()

        if not userid or not password:
            messagebox.showwarning(
                "Login",
                "Please enter User ID and Password."
            )
            return

        success = self.db.authenticate_user(
            userid,
            password
        )

        if success:

            messagebox.showinfo(
                "Login",
                "Login successful!"
            )
            self.db.disconnect_db()
            self.root.destroy()

            # Start main application
            self.on_login_success(userid)

        else:

            messagebox.showerror(
                "Login",
                "Invalid User ID or Password."
            )

    def signup(self):

        userid = self.userid_entry.get().strip()
        password = self.password_entry.get()

        if not userid or not password:
            messagebox.showwarning(
                "Sign Up",
                "Please enter User ID and Password."
            )
            return

        success, message = self.db.create_user(
            userid,
            password
        )

        if success:

            messagebox.showinfo(
                "Sign Up",
                message
            )

            self.password_entry.delete(
                0,
                tk.END
            )

        else:

            messagebox.showerror(
                "Sign Up",
                message
            )