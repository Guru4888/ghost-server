from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghostsecret12345"

# Main Web App Login Password Updated Here
APP_PASSWORD = "guru&guru16230"

socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_password = request.form.get('password')
        if user_password == APP_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error="Invalid Secret Access Key!")
    return render_template('login.html')

@app.route('/chat')
def chat():
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return render_template('chat.html')

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
