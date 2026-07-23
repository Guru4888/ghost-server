from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.secret_key = "ghostsecret12345"  # session ke liye zaruri
socketio = SocketIO(app, async_mode='eventlet')

# Yaha password change kar sakte ho
APP_PASSWORD = "1234"
CHAT_PASSWORD = "abcd"

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
