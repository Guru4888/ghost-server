from flask import Flask
from flask_socketio import SocketIO, emit, join_room
import time, threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'zero_footprint_2026'
socketio = SocketIO(app, cors_allowed_origins="*")
temp_buffer = {}

def auto_wipe(room_id):
    time.sleep(10)
    if room_id in temp_buffer:
        del temp_buffer[room_id]

@socketio.on('join')
def on_join(data):
    join_room(data['room'])

@socketio.on('send_msg')
def on_msg(data):
    room = data['room']
    if room not in temp_buffer: temp_buffer = []
    temp_buffer.append(data)
    emit('new_msg', data, room=room)
    t = threading.Thread(target=auto_wipe, args=(room,))
    t.daemon = True
    t.start()

@app.route('/')
def home():
    return "Ghost Server is Live 👻"

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
