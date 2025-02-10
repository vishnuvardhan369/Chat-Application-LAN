import socket
import threading
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse, unquote

class FileTransferHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            path = unquote(parsed_url.path)[1:]  # Remove leading '/' and decode
            
            # Check if the file is meant for this user
            requesting_user = self.headers.get('X-Username')
            if not requesting_user:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'Username required')
                return
                
            file_path = os.path.join('server_files', path)
            
            # Check if file exists and user has permission
            if os.path.exists(file_path):
                # Read file metadata
                meta_path = f"{file_path}.meta"
                if os.path.exists(meta_path):
                    with open(meta_path, 'r') as f:
                        metadata = json.load(f)
                        if metadata['recipient'] != 'all' and metadata['recipient'] != requesting_user:
                            self.send_response(403)
                            self.end_headers()
                            self.wfile.write(b'Access denied')
                            return
                
                # Send the file if authorized
                with open(file_path, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'File not found')
                
        except Exception as e:
            print(f"Error serving file: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal server error')

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            file_data = self.rfile.read(content_length)
            
            filename = self.headers.get('X-Filename')
            username = self.headers.get('X-Username')
            recipient = self.headers.get('X-Recipient', 'all')  # 'all' for public files
            
            if not filename or not username:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Missing filename or username')
                return

            # Save the file
            file_path = os.path.join('server_files', filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Save metadata
            meta_path = f"{file_path}.meta"
            metadata = {
                'sender': username,
                'recipient': recipient,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(meta_path, 'w') as f:
                json.dump(metadata, f)

            # Notify appropriate users about the upload
            timestamp = datetime.now().strftime("%H:%M:%S")
            if recipient == 'all':
                notification = f"\n[{timestamp}] SERVER: {username} uploaded file '{filename}' (click here to download {filename})"
                self.server.chat_server.broadcast(notification)
            else:
                notification = f"\n[{timestamp}] SERVER: {username} sent you a private file '{filename}' (click here to download {filename})"
                self.server.chat_server.send_private_message(recipient, notification)
                sender_notification = f"\n[{timestamp}] SERVER: File '{filename}' sent privately to {recipient}"
                self.server.chat_server.send_private_message(username, sender_notification)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'File uploaded successfully')
            
        except Exception as e:
            print(f"Error handling file upload: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'Error uploading file: {str(e)}'.encode())

    def log_message(self, format, *args):
        pass

class ChatServer:
    def __init__(self, chat_host='0.0.0.0', chat_port=5555, http_port=8000):
        self.chat_host = chat_host
        self.chat_port = chat_port
        self.http_port = http_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # {client_socket: username}
        self.username_to_socket = {}  # {username: client_socket}
        self.upload_folder = 'server_files'
        
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

        self.http_server = HTTPServer((chat_host, http_port), FileTransferHandler)
        self.http_server.chat_server = self

    def start_http_server(self):
        print(f"HTTP server started on port {self.http_port}")
        self.http_server.serve_forever()

    def broadcast(self, message, exclude_client=None):
        for client in self.clients:
            if client != exclude_client:
                try:
                    client.send(message.encode())
                except:
                    self.remove_client(client)

    def send_private_message(self, recipient_username, message):
        if recipient_username in self.username_to_socket:
            try:
                self.username_to_socket[recipient_username].send(message.encode())
                return True
            except:
                return False
        return False

    def handle_client(self, client_socket, address):
        try:
            username = client_socket.recv(1024).decode()
            
            # Check if username is already taken
            if username in self.username_to_socket:
                client_socket.send("USERNAME_TAKEN".encode())
                client_socket.close()
                return
                
            self.clients[client_socket] = username
            self.username_to_socket[username] = client_socket
            
            # Send server info and user list
            user_list = list(self.username_to_socket.keys())
            server_info = f"SERVER_INFO|{self.http_port}|{','.join(user_list)}"
            client_socket.send(server_info.encode())
            
            # Announce new user
            announcement = f"\n{username} joined the chat!"
            self.broadcast(announcement, client_socket)
            print(f"New connection from {address} - Username: {username}")

            while True:
                try:
                    message = client_socket.recv(1024).decode()
                    if message:
                        if message.startswith("/pm "):
                            # Handle private message
                            parts = message[4:].split(" ", 1)
                            if len(parts) == 2:
                                recipient, content = parts
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                pm_message = f"[{timestamp}] [PM from {username}]: {content}"
                                
                                if self.send_private_message(recipient, pm_message):
                                    # Send confirmation to sender
                                    sender_message = f"[{timestamp}] [PM to {recipient}]: {content}"
                                    client_socket.send(sender_message.encode())
                                else:
                                    client_socket.send(f"Error: User '{recipient}' not found or offline.".encode())
                        else:
                            # Handle public message
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            formatted_msg = f"[{timestamp}] {username}: {message}"
                            print(formatted_msg)
                            self.broadcast(formatted_msg, client_socket)
                except:
                    break

        finally:
            self.remove_client(client_socket)

    def remove_client(self, client_socket):
        if client_socket in self.clients:
            username = self.clients[client_socket]
            del self.clients[client_socket]
            del self.username_to_socket[username]
            client_socket.close()
            self.broadcast(f"\n{username} left the chat!")

    def start(self):
        http_thread = threading.Thread(target=self.start_http_server)
        http_thread.daemon = True
        http_thread.start()

        self.server_socket.bind((self.chat_host, self.chat_port))
        self.server_socket.listen()
        print(f"Chat server started on {self.chat_host}:{self.chat_port}")

        while True:
            client_socket, address = self.server_socket.accept()
            thread = threading.Thread(target=self.handle_client, 
                                   args=(client_socket, address))
            thread.daemon = True
            thread.start()

if __name__ == "__main__":
    server = ChatServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.http_server.shutdown()
        server.server_socket.close()