from flask import Flask, render_template, request, session, redirect
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "ghostsecret12345"  # session ke liye zaruri
socketio = SocketIO(app)

APP_PASSWORD = "1234"
CHAT_PASSWORD = "abcd"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == APP_PASSWORD:
            session["logged_in"] = True
            return redirect("/chat")  # login ke baad chat pe bhej dega
        else:
            return render_template("login.html", error="Wrong Password!")
    return render_template("login.html")

@app.route("/chat")
def chat():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("chat.html")

@socketio.on('verify_password')
def verify(data):
    if data['password'] == CHAT_PASSWORD:
        emit('password_status', {'status': 'ok'})
    else:
        emit('password_status', {'status': 'wrong'})

@socketio.on('send_message')
def handle_msg(data):
    emit('receive_message', data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
