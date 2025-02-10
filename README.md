# LAN-Chat Application  
A real-time chat application built in Python that enables seamless messaging and file transfers over a Local Area Network (LAN). This project supports both public and private messaging, one-click file uploads/downloads, and displays an online users list—all wrapped in an intuitive user interface built with Tkinter, ttkthemes, and CustomTkinter.

**Features:**  
- Seamless real-time messaging  
- Private messaging and file transfers  
- One-click file download via an integrated HTTP server  
- Online users list displayed in the GUI  
- Intuitive and responsive UI for ease of use

**Technologies Used:**  
Python 3, Tkinter, ttkthemes, CustomTkinter, PIL (Pillow), socket programming, HTTPServer, threading, JSON, datetime, os, and Requests.

**Project Structure:**  
LAN-Chat/  
&nbsp;&nbsp;&nbsp;&nbsp;├── server.py  — Server-side code handling client connections, messaging, and file transfers  
&nbsp;&nbsp;&nbsp;&nbsp;├── client.py  — Client-side code providing the chat GUI, file upload/download, and private messaging  
&nbsp;&nbsp;&nbsp;&nbsp;└── README.md  — This documentation file

This structure separates the server and client functionalities, making the code easier to navigate and maintain.

## Installation

### Prerequisites
- Python 3.6 or higher must be installed on your system.
- Ensure that pip is installed to manage Python packages.


**Installation:**  
1. Clone the repository:  
   `git clone https://github.com/yourusername/LAN-Chat.git`  
2. Navigate to the project directory:  
   `cd LAN-Chat`  
3. Install the required dependencies using pip:  
   `pip install ttkthemes customtkinter pillow requests`

**Usage:**  
- **Start the Server:** Open a terminal, navigate to the project directory, and run:  
  `python server.py`  
  This will start the chat server and the HTTP file server.
- **Run the Client:** Open another terminal (or use an IDE), navigate to the project directory, and run:  
  `python client.py`  
  On the login screen, enter your username and server IP (default is `127.0.0.1`), then click **Connect**. Use the chat interface to send messages, transfer files, or send private messages.


