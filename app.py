from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghost_super_secret_key_998877"

# Standard Gunicorn/Render compatible SocketIO setup
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/', methods=['GET'])
def home():
    return render_template('chat.html')

@app.route('/logout')
def logout():
    session.clear()
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
