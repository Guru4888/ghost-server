from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ghost_secret_key_123'
socketio = SocketIO(app, cors_allowed_origins="*")

APP_PASSWORD = "1234"
CHAT_PASSWORD = "abcd"

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error="Password galat hai bhai")
    return render_template('login.html')

@app.route('/chat')
def chat():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('chat.html')

@socketio.on('verify_password')
def verify_password(data):
    if data['password'] == CHAT_PASSWORD:
        emit('password_status', {'status': 'ok'})
    else:
        emit('password_status', {'status': 'wrong'})

@socketio.on('send_message')
def handle_message(data):
    if data:
        emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True) # <- bas ye add hua
