import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import threading
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
GLOBAL_CREDENTIALS_FILE = 'credentials.json'
ACCOUNTS_CONFIG_FILE = 'accounts_config.json'

class AccountManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Gmail Monitor - Account Manager")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Load existing accounts
        self.accounts = self.load_accounts()
        
        self.setup_ui()
        self.refresh_account_list()
    
    def load_accounts(self):
        """Load accounts from JSON file"""
        if os.path.exists(ACCOUNTS_CONFIG_FILE):
            try:
                with open(ACCOUNTS_CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading accounts: {e}")
        return []
    
    def save_accounts(self):
        """Save accounts to JSON file"""
        try:
            with open(ACCOUNTS_CONFIG_FILE, 'w') as f:
                json.dump(self.accounts, f, indent=2)
            return True
        except Exception as e:
            self.log_message(f"Error saving accounts: {e}", "error")
            return False
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Gmail Monitor Account Manager", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Add New Account", padding="10")
        input_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        # Name input
        ttk.Label(input_frame, text="Account Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(input_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Email input
        ttk.Label(input_frame, text="Email Address:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(input_frame, textvariable=self.email_var, width=40)
        self.email_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=(5, 0))
        
        # Add button
        self.add_button = ttk.Button(input_frame, text="Add Account & Authenticate", 
                                    command=self.add_account)
        self.add_button.grid(row=0, column=2, rowspan=2, padx=(10, 0))
        
        # Current accounts section
        accounts_frame = ttk.LabelFrame(main_frame, text="Current Accounts", padding="10")
        accounts_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        accounts_frame.columnconfigure(0, weight=1)
        
        # Treeview for accounts
        self.accounts_tree = ttk.Treeview(accounts_frame, columns=("Email", "Token", "History"), 
                                         show="tree headings", height=6)
        self.accounts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Configure columns
        self.accounts_tree.heading("#0", text="Name")
        self.accounts_tree.heading("Email", text="Email")
        self.accounts_tree.heading("Token", text="Token File")
        self.accounts_tree.heading("History", text="History File")
        
        self.accounts_tree.column("#0", width=200)
        self.accounts_tree.column("Email", width=250)
        self.accounts_tree.column("Token", width=150)
        self.accounts_tree.column("History", width=150)
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(accounts_frame, orient="vertical", command=self.accounts_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.accounts_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Remove button
        remove_button = ttk.Button(accounts_frame, text="Remove Selected", 
                                  command=self.remove_account)
        remove_button.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear log button
        clear_log_button = ttk.Button(log_frame, text="Clear Log", command=self.clear_log)
        clear_log_button.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)
        
        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="Refresh", command=self.refresh_account_list).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Save & Close", command=self.save_and_close).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to add account
        self.root.bind('<Return>', lambda event: self.add_account())
        
        self.log_message("Account Manager started. Ready to add accounts.")
    
    def log_message(self, message, level="info"):
        """Add message to log"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        if level == "error":
            prefix = "❌"
        elif level == "success":
            prefix = "✅"
        elif level == "warning":
            prefix = "⚠️"
        else:
            prefix = "ℹ️"
        
        log_entry = f"[{timestamp}] {prefix} {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
    
    def get_next_file_numbers(self):
        """Get the next available token and history file numbers"""
        existing_numbers = set()
        for account in self.accounts:
            # Extract number from token file
            token_file = account.get('token_file', '')
            if token_file.startswith('token') and token_file.endswith('.json'):
                try:
                    num = int(token_file[5:-5])  # Remove 'token' and '.json'
                    existing_numbers.add(num)
                except ValueError:
                    pass
        
        # Find the next available number
        next_num = 1
        while next_num in existing_numbers:
            next_num += 1
        
        return next_num
    
    def authenticate_account(self, email, token_file):
        """Authenticate the account using Google OAuth"""
        try:
            self.log_message(f"Starting authentication for {email}...")
            
            if not os.path.exists(GLOBAL_CREDENTIALS_FILE):
                self.log_message("credentials.json not found! Please ensure it's in the same directory.", "error")
                return False
            
            creds = None
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GLOBAL_CREDENTIALS_FILE, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            # Test the connection
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            
            if profile.get('emailAddress') != email:
                self.log_message(f"Warning: Authenticated email ({profile.get('emailAddress')}) doesn't match entered email ({email})", "warning")
            
            self.log_message(f"Successfully authenticated {email}!", "success")
            return True
            
        except Exception as e:
            self.log_message(f"Authentication failed for {email}: {str(e)}", "error")
            return False
    
    def add_account(self):
        """Add a new account"""
        name = self.name_var.get().strip()
        email = self.email_var.get().strip()
        
        if not name or not email:
            messagebox.showerror("Error", "Please enter both account name and email address.")
            return
        
        # Check if email already exists
        for account in self.accounts:
            if account['email'].lower() == email.lower():
                messagebox.showerror("Error", f"Account with email {email} already exists.")
                return
        
        # Get next file numbers
        file_num = self.get_next_file_numbers()
        token_file = f"token{file_num}.json"
        history_file = f"history{file_num}.txt"
        
        # Disable the add button during authentication
        self.add_button.config(state="disabled")
        self.add_button.config(text="Authenticating...")
        
        def auth_thread():
            """Authentication in a separate thread to prevent UI freezing"""
            try:
                if self.authenticate_account(email, token_file):
                    # Add to accounts list
                    new_account = {
                        'name': name,
                        'email': email,
                        'token_file': token_file,
                        'history_file': history_file
                    }
                    self.accounts.append(new_account)
                    
                    # Save to file
                    if self.save_accounts():
                        self.log_message(f"Successfully added new account: {name} ({email})", "success")
                        
                        # Clear fields and refresh UI on main thread
                        self.root.after(0, self.clear_fields_and_refresh)
                    else:
                        # Remove from accounts list if save failed
                        self.accounts.remove(new_account)
                        self.log_message("Failed to save account configuration.", "error")
                else:
                    # Clean up token file if authentication failed
                    if os.path.exists(token_file):
                        os.remove(token_file)
                    self.log_message(f"Failed to add account: {name} ({email})", "error")
            
            finally:
                # Re-enable button on main thread
                self.root.after(0, lambda: self.add_button.config(state="normal", text="Add Account & Authenticate"))
        
        # Start authentication in background thread
        auth_thread = threading.Thread(target=auth_thread, daemon=True)
        auth_thread.start()
    
    def clear_fields_and_refresh(self):
        """Clear input fields and refresh the account list"""
        self.name_var.set("")
        self.email_var.set("")
        self.refresh_account_list()
    
    def remove_account(self):
        """Remove selected account"""
        selected_item = self.accounts_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an account to remove.")
            return
        
        item = selected_item[0]
        account_email = self.accounts_tree.item(item)['values'][0]
        
        # Confirm removal
        if messagebox.askyesno("Confirm", f"Are you sure you want to remove the account: {account_email}?"):
            # Find and remove the account
            for i, account in enumerate(self.accounts):
                if account['email'] == account_email:
                    removed_account = self.accounts.pop(i)
                    
                    # Optionally remove token and history files
                    if messagebox.askyesno("Remove Files", 
                                         f"Do you want to remove the associated files?\n"
                                         f"- {removed_account['token_file']}\n"
                                         f"- {removed_account['history_file']}"):
                        try:
                            if os.path.exists(removed_account['token_file']):
                                os.remove(removed_account['token_file'])
                            if os.path.exists(removed_account['history_file']):
                                os.remove(removed_account['history_file'])
                            self.log_message(f"Removed files for {account_email}", "success")
                        except Exception as e:
                            self.log_message(f"Error removing files: {e}", "error")
                    
                    self.save_accounts()
                    self.refresh_account_list()
                    self.log_message(f"Removed account: {account_email}", "success")
                    break
    
    def refresh_account_list(self):
        """Refresh the accounts treeview"""
        # Clear existing items
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        
        # Add current accounts
        for account in self.accounts:
            self.accounts_tree.insert("", "end", 
                                    text=account['name'],
                                    values=(account['email'], 
                                           account['token_file'], 
                                           account['history_file']))
        
        self.log_message(f"Currently monitoring {len(self.accounts)} accounts:")
        for account in self.accounts:
            self.log_message(f"  • {account['name']} ({account['email']})")
    
    def save_and_close(self):
        """Save accounts and close the application"""
        if self.save_accounts():
            self.log_message("Configuration saved successfully!", "success")
            self.root.after(1000, self.root.quit)  # Close after 1 second
        else:
            messagebox.showerror("Error", "Failed to save configuration.")

def main():
    """Main function to run the Account Manager"""
    root = tk.Tk()
    app = AccountManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()
