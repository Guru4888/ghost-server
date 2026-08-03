import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "ghostsecret12345"
socketio = SocketIO(app, async_mode='eventlet')

APP_PASSWORD = "1234"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for('chat'))
        else:
            return render_template("login.html", error="Wrong Password!")
    return render_template("login.html")

@app.route("/chat")
def chat():
    if not session.get("logged_in"):
        return redirect(url_for('login'))
    return render_template("chat.html")

@socketio.on('send_message')
def handle_msg(data):
    # Sender User ID aur Message dono ko sabhi connected clients tak bhejna
    user_id = data.get('user', 'Anonymous')
    message = data.get('msg', '')
    emit('receive_message', {'user': user_id, 'msg': message}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
