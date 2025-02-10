import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ttkthemes import ThemedTk
import socket
import threading
import os
import requests
import json
from datetime import datetime
import customtkinter as ctk
from PIL import Image, ImageTk
import webbrowser

class ChatGUI:
    def __init__(self):
        self.window = ThemedTk(theme="arc")
        self.window.title("Chat Application")
        self.window.geometry("1200x800")
        self.window.minsize(800, 600)
        
        # Initialize client properties
        self.host = '127.0.0.1'
        self.chat_port = 5555
        self.http_port = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.download_folder = 'downloads'
        self.online_users = set()
        
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
            
        # Create main containers
        self.create_login_frame()
        self.create_chat_frame()
        
        # Show login frame first
        self.show_login_frame()
        
    def create_login_frame(self):
        self.login_frame = ttk.Frame(self.window, padding="20")
        
        # Login widgets
        ttk.Label(self.login_frame, text="Chat Login", font=('Helvetica', 24)).pack(pady=20)
        
        # Username entry
        username_frame = ttk.Frame(self.login_frame)
        username_frame.pack(fill='x', pady=10)
        ttk.Label(username_frame, text="Username:").pack(side='left', padx=5)
        self.username_entry = ttk.Entry(username_frame)
        self.username_entry.pack(side='left', fill='x', expand=True, padx=5)
        
        # Server details
        server_frame = ttk.Frame(self.login_frame)
        server_frame.pack(fill='x', pady=10)
        ttk.Label(server_frame, text="Server:").pack(side='left', padx=5)
        self.server_entry = ttk.Entry(server_frame)
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.pack(side='left', fill='x', expand=True, padx=5)
        
        # Connect button
        ttk.Button(self.login_frame, text="Connect", command=self.connect_to_server).pack(pady=20)
        
        # Status label
        self.login_status = ttk.Label(self.login_frame, text="")
        self.login_status.pack(pady=10)
        
    def create_chat_frame(self):
        self.chat_frame = ttk.Frame(self.window)
        
        # Create left panel for chat
        left_panel = ttk.Frame(self.chat_frame)
        left_panel.pack(side='left', fill='both', expand=True)
        
        # Message area
        self.message_area = tk.Text(left_panel, wrap='word', state='disabled')
        self.message_area.pack(fill='both', expand=True, padx=5, pady=5)
        self.message_area.tag_configure('server', foreground='gray')
        self.message_area.tag_configure('private', foreground='blue')
        self.message_area.tag_configure('file', foreground='green', underline=1)
        
        # Input area
        input_frame = ttk.Frame(left_panel)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        self.message_input = ttk.Entry(input_frame)
        self.message_input.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.message_input.bind('<Return>', lambda e: self.send_message())
        
        ttk.Button(input_frame, text="Send", command=self.send_message).pack(side='left')
        ttk.Button(input_frame, text="File", command=self.show_file_dialog).pack(side='left', padx=5)
        
        # Create right panel for users list
        right_panel = ttk.Frame(self.chat_frame, width=200)
        right_panel.pack(side='right', fill='y', padx=5, pady=5)
        right_panel.pack_propagate(False)
        
        # Users list with search
        ttk.Label(right_panel, text="Online Users").pack(fill='x')
        self.user_search = ttk.Entry(right_panel)
        self.user_search.pack(fill='x', pady=5)
        self.user_search.bind('<KeyRelease>', self.filter_users)
        
        # Users listbox with scrollbar
        users_frame = ttk.Frame(right_panel)
        users_frame.pack(fill='both', expand=True)
        
        self.users_listbox = tk.Listbox(users_frame)
        self.users_listbox.pack(side='left', fill='both', expand=True)
        
        users_scrollbar = ttk.Scrollbar(users_frame, orient='vertical', 
                                      command=self.users_listbox.yview)
        users_scrollbar.pack(side='right', fill='y')
        self.users_listbox.configure(yscrollcommand=users_scrollbar.set)
        
        # Right-click menu for users
        self.user_menu = tk.Menu(self.window, tearoff=0)
        self.user_menu.add_command(label="Send Private Message", 
                                 command=self.create_pm_dialog)
        self.user_menu.add_command(label="Send Private File", 
                                 command=self.send_private_file)
        
        self.users_listbox.bind('<Button-3>', self.show_user_menu)
        
    def show_login_frame(self):
        self.chat_frame.pack_forget()
        self.login_frame.pack(fill='both', expand=True)
        
    def show_chat_frame(self):
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill='both', expand=True)
        
    def connect_to_server(self):
        self.username = self.username_entry.get().strip()
        self.host = self.server_entry.get().strip()
        
        if not self.username:
            self.login_status.config(text="Please enter a username")
            return
            
        try:
            self.socket.connect((self.host, self.chat_port))
            self.socket.send(self.username.encode())
            
            response = self.socket.recv(1024).decode()
            if response == "USERNAME_TAKEN":
                self.login_status.config(text="Username already taken")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                return
                
            if response.startswith("SERVER_INFO|"):
                parts = response.split("|")
                self.http_port = int(parts[1])
                if len(parts) > 2:
                    self.online_users = set(parts[2].split(","))
                    self.update_users_list()
                
                # Start receive thread
                receive_thread = threading.Thread(target=self.receive_messages)
                receive_thread.daemon = True
                receive_thread.start()
                
                # Show chat frame
                self.show_chat_frame()
                
        except Exception as e:
            self.login_status.config(text=f"Connection error: {str(e)}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
    def receive_messages(self):
        while True:
            try:
                message = self.socket.recv(1024).decode()
                if message:
                    # Update users list for join/leave messages
                    if "joined the chat!" in message:
                        username = message.split()[0].strip()
                        self.online_users.add(username)
                        self.update_users_list()
                    elif "left the chat!" in message:
                        username = message.split()[0].strip()
                        self.online_users.discard(username)
                        self.update_users_list()
                    
                    # Add message to chat area
                    self.add_message(message)
            except:
                print("Disconnected from server")
                break
                
    def add_message(self, message):
        self.message_area.config(state='normal')

        # Determine message type and apply appropriate tag
        if message.startswith('\n[') and 'SERVER:' in message:
            if 'uploaded file' in message or 'sent you a private file' in message:
                # Extract filename from the message and create a clickable link
                filename = message.split("'")[1]  # Extract filename using split
                self.message_area.insert('end', message + '\n', 'file')
                self.message_area.tag_bind('file', '<Button-1>', lambda e, file=filename: self.handle_file_click(file))
            else:
                self.message_area.insert('end', message + '\n', 'server')
        elif '[PM' in message:
            self.message_area.insert('end', message + '\n', 'private')
        else:
            self.message_area.insert('end', message + '\n')

        self.message_area.config(state='disabled')
        self.message_area.see('end')

    def handle_file_click(self, filename):
        try:
            file_url = f"http://{self.host}:{self.http_port}/{filename}"
            headers = {'X-Username': self.username}

            response = requests.get(file_url, headers=headers)

            if response.status_code == 200:
                file_path = os.path.join(self.download_folder, filename)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                messagebox.showinfo("Success", f"File downloaded to {file_path}")
            elif response.status_code == 403:
                messagebox.showerror("Error", "Access denied. This file was not shared with you.")
            else:
                messagebox.showerror("Error", f"Error downloading file: HTTP {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Error downloading file: {str(e)}")

        
    def send_message(self):
        message = self.message_input.get().strip()
        if not message:
            return

        # Check if a user is selected from the right-side user list for private message
        if self.users_listbox.curselection():
            recipient = self.users_listbox.get(self.users_listbox.curselection())
            self.socket.send(f"/pm {recipient} {message}".encode())

            # Do not manually display the message here, as it will be shown when received from the server

        else:
            # Send public message if no user is selected
            self.socket.send(message.encode())

            # Display the public message sent by the user
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.add_message(f"[{timestamp}] You: {message}")

        # Clear the input box and deselect the user
        self.message_input.delete(0, 'end')
        self.users_listbox.selection_clear(0, 'end')

            
    def show_file_dialog(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            if self.users_listbox.curselection():
                # Send to selected user
                recipient = self.users_listbox.get(self.users_listbox.curselection())
                self.send_file(filepath, recipient)
            else:
                # Send to all
                self.send_file(filepath)
                
    def send_file(self, filepath, recipient='all'):
        try:
            if not os.path.exists(filepath):
                messagebox.showerror("Error", "File does not exist")
                return

            filename = os.path.basename(filepath)
            
            upload_url = f"http://{self.host}:{self.http_port}"
            
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            headers = {
                'X-Filename': filename,
                'X-Username': self.username,
                'X-Recipient': recipient
            }
            
            response = requests.post(
                upload_url,
                data=file_data,
                headers=headers
            )
            
            if response.status_code != 200:
                messagebox.showerror("Error", f"Error uploading file: {response.text}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error uploading file: {str(e)}")
            
    def download_file(self, filename):
        try:
            file_url = f"http://{self.host}:{self.http_port}/{filename}"
            
            headers = {
                'X-Username': self.username
            }
            
            response = requests.get(file_url, headers=headers)
            
            if response.status_code == 200:
                file_path = os.path.join(self.download_folder, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                messagebox.showinfo("Success", 
                                  f"File downloaded to {file_path}")
            elif response.status_code == 403:
                messagebox.showerror("Error", 
                                   "Access denied. This file was not shared with you.")
            else:
                messagebox.showerror("Error", 
                                   f"Error downloading file: HTTP {response.status_code}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error downloading file: {str(e)}")
            
    def update_users_list(self):
        self.users_listbox.delete(0, 'end')
        for user in sorted(self.online_users):
            if user != self.username:  # Don't show current user
                self.users_listbox.insert('end', user)
                
    def filter_users(self, event=None):
        search_term = self.user_search.get().lower()
        self.users_listbox.delete(0, 'end')
        for user in sorted(self.online_users):
            if user != self.username and search_term in user.lower():
                self.users_listbox.insert('end', user)
                
    def show_user_menu(self, event):
        try:
            self.users_listbox.selection_clear(0, 'end')
            self.users_listbox.selection_set(
                self.users_listbox.nearest(event.y))
            self.user_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.user_menu.grab_release()
            
    def create_pm_dialog(self):
        if not self.users_listbox.curselection():
            return
            
        recipient = self.users_listbox.get(self.users_listbox.curselection())
        
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Message to {recipient}")
        dialog.geometry("400x200")
        
        message_entry = ttk.Entry(dialog)
        message_entry.pack(fill='x', padx=10, pady=10)
        
        def send():
            message = message_entry.get().strip()
            if message:
                self.socket.send(f"/pm {recipient} {message}".encode())
                dialog.destroy()
                
        ttk.Button(dialog, text="Send", command=send).pack(pady=10)
        
    def send_private_file(self):
        if not self.users_listbox.curselection():
            return
            
        recipient = self.users_listbox.get(self.users_listbox.curselection())
        filepath = filedialog.askopenfilename()
        
        if filepath:
            self.send_file(filepath, recipient)
            
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = ChatGUI()
    app.run()