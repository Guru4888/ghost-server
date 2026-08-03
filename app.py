from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghostsecret12345"

# Main Web App Login Password
APP_PASSWORD = "guru&guru16230"

socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Fake 404 Error Page Template
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
    </style>
</head>
<body>
    <h1>404</h1>
    <p><b>Page Not Available</b></p>
    <div class="error-code">The requested URL was not found on this server or the session has expired.</div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_password = request.form.get('password')
        if user_password == APP_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('chat'))
        else:
            return FAKE_404_HTML, 404
    return render_template('login.html')

@app.route('/chat')
def chat():
    # Direct link access safeguard: Returns 404 Not Available
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
    else:
        emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
