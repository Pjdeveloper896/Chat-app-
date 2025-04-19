from flask import Flask, render_template_string, send_file
from flask_socketio import SocketIO, emit
import qrcode
import qrcode.image.svg
import socket
from io import BytesIO
import sqlite3
import os

app = Flask(__name__)
socketio = SocketIO(app)

# --- DB Setup ---
def init_db():
    if not os.path.exists("chat.db"):
        conn = sqlite3.connect("chat.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

# --- Local IP Helper ---
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

# --- QR Code Generator ---
def generate_qr_code_svg(ip):
    url = f'http://{ip}:5000'
    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(url, image_factory=factory)
    img_io = BytesIO()
    img.save(img_io)
    img_io.seek(0)
    return img_io

# --- HTML Template ---
base_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Chat App</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
  <div class="flex justify-center items-center min-h-screen">
    <div class="text-center w-full max-w-md">
      <h1 class="text-3xl font-bold mb-4">Chat App</h1>
      <p class="text-lg mb-4">Scan the QR code below to join:</p>
      <img src="/generate_qr" alt="QR Code" class="mx-auto mb-4" />
      
      <div class="bg-white shadow rounded p-4">
        <div id="messages" class="h-48 overflow-y-auto bg-gray-200 p-2 rounded mb-2 text-left text-sm"></div>
        <input type="text" id="message" placeholder="Type a message..." class="w-full p-2 border rounded mb-2" />
        <button id="sendMessage" class="w-full p-2 bg-blue-500 text-white rounded">Send</button>
      </div>
    </div>
  </div>

  <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
  <script>
    const socket = io();
    const sendMessageButton = document.getElementById('sendMessage');
    const messageInput = document.getElementById('message');
    const messagesDiv = document.getElementById('messages');

    sendMessageButton.addEventListener('click', () => {
      const message = messageInput.value.trim();
      if (message) {
        socket.emit('send_message', message);
        messageInput.value = '';
      }
    });

    socket.on('receive_message', (message) => {
      const newMessage = document.createElement('div');
      newMessage.textContent = message;
      messagesDiv.appendChild(newMessage);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    });
  </script>
</body>
</html>
'''

# --- Routes ---
@app.route("/")
def home():
    # Fetch old messages from SQLite
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM messages")
    rows = cursor.fetchall()
    conn.close()
    
    messages_html = ''.join(f"<div>{row[0]}</div>" for row in rows)
    full_html = base_html.replace('<div id="messages"', f'<div id="messages">{messages_html}')
    
    return render_template_string(full_html)

@app.route("/generate_qr")
def generate_qr():
    ip = get_local_ip()
    img_io = generate_qr_code_svg(ip)
    return send_file(img_io, mimetype='image/svg+xml')

# --- WebSocket Events ---
@socketio.on("send_message")
def handle_message(data):
    # Save to database
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (content) VALUES (?)", (data,))
    conn.commit()
    conn.close()
    
    emit("receive_message", data, broadcast=True)

# --- Run App ---
if __name__ == "__main__":
    init_db()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
