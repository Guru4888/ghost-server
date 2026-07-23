import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import uuid
from collections import defaultdict
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Passwords
APP_PASSWORD = "1234"
CHAT_PASSWORD = "abcd"

# Room data
rooms = defaultdict(lambda: {"users": [], "messages": []})

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        if request.form.get('app_password')!= APP_PASSWORD:
            error = "App password galat hai"
        else:
            session['user'] = request.form.get('username')
            return redirect(url_for('chat'))
    return render_template('index.html', error=error)

@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', username=session['user'])

@app.route('/change_app_password', methods=['POST'])
def change_app_password():
    global APP_PASSWORD
    old = request.form.get('old_password')
    new = request.form.get('new_password')
    if old == APP_PASSWORD:
        APP_PASSWORD = new
    return redirect(url_for('index'))

@app.route('/change_chat_password', methods=['POST'])
def change_chat_password():
    global CHAT_PASSWORD
    old = request.form.get('old_password')
    new = request.form.get('new_password')
    if old == CHAT_PASSWORD:
        CHAT_PASSWORD = new
    return redirect(url_for('chat'))

@socketio.on('join')
def handle_join(data):
    room = data['room']
    username = session['user']
    password = data['password']
    
    if password!= CHAT_PASSWORD:
        emit('error', {'msg': 'Chat password galat hai'})
        return
    
    if len(rooms[room]["users"]) >= 2:
        emit('error', {'msg': 'Room full hai. Sirf 2 log allowed'})
        return
    
    join_room(room)
    rooms[room]["users"].append(username)
    send({'msg': f'{username} join hua'}, to=room)
    
    for msg in rooms[room]["messages"]:
        emit('message', msg)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    msg = {'user': session['user'], 'text': data['text'], 'time': time.time()}
    rooms[room]["messages"].append(msg)
    if len(rooms[room]["messages"]) > 50:
        rooms[room]["messages"].pop(0)
    send(msg, to=room)
    
    socketio.start_background_task(delete_after_30, room, msg)

def delete_after_30(room, msg):
    time.sleep(30)
    if msg in rooms[room]["messages"]:
        rooms[room]["messages"].remove(msg)
        emit('delete_message', msg, to=room)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
