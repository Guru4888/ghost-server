from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
# Secure Secret Key for Sessions
app.secret_key = "ghost_super_secret_key_998877"

# Main Master App Password (jo aapne maanga tha)
APP_PASSWORD = "guru&guru16230"

socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

FAKE_404_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 Page Not Available</title>
    <style>
        body {
            background-color: #ffffff;
            color: #000000;
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            text-align: center;
        }
        h1 { font-size: 3rem; margin-bottom: 10px; color: #333; }
        p { font-size: 1.2rem; color: #666; margin-bottom: 20px; }
        .error-code { font-size: 0.9rem; color: #999; }
        a.secret-btn {
            margin-top: 25px;
            color: #ccc;
            text-decoration: none;
            font-size: 0.8rem;
        }
        a.secret-btn:hover { color: #333; }
    </style>
</head>
<body>
    <h1>404</h1>
    <p><b>Page Not Available</b></p>
    <div class="error-code">The requested URL was not found on this server or the session has expired.</div>
    <a href="/" class="secret-btn">Return to Portal</a>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    # Agar pehle se authenticated hai toh direct chat/room par bhej do
    if session.get('authenticated'):
        return redirect(url_for('chat'))
    # Nahi toh fake calculator wala index page khulega
    return render_template('index.html')

@app.route('/verify-master', methods=['POST'])
def verify_master():
    data = request.json
    entered_password = data.get('password')
    
    if entered_password == APP_PASSWORD:
        session['authenticated'] = True
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Invalid Password"}), 401

@app.route('/chat')
def chat():
    # Strict Session Validation
    if not session.get('authenticated'):
        return FAKE_404_HTML, 404
    return render_template('chat.html')

@app.route('/logout')
def logout():
    session.clear()
    return FAKE_404_HTML, 404

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room')
    if room:
        join_room(room)

@socketio.on('send_message')
def handle_send_message(data):
    room = data.get('room')
    if room:
        emit('receive_message', data, to=room)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
