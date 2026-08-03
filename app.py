from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghost_super_secret_key_998877"

# Aapka Master Password
APP_PASSWORD = "guru&guru16230"

# Fix: async_mode ko explicitly threading kar diya hai taaki Gunicorn ke sath error na aaye
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

FAKE_404_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>404 Page Not Available</title>
    <style>
        body { background: #fff; color: #000; font-family: Arial; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        h1 { font-size: 3rem; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>404</h1>
    <p><b>Page Not Available</b></p>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    if session.get('authenticated'):
        return redirect(url_for('chat'))
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
    if not session.get('authenticated'):
        return FAKE_404_HTML, 404
    return render_template('chat.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

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
