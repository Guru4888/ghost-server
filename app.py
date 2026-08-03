from flask import Flask, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghost_super_secret_key_998877"

# Aapka Master Password
APP_PASSWORD = "guru&guru16230"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 1. Master Password Login Page
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Access</title>
    <style>
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .portal-box { background: #161b22; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 320px; text-align: center; border: 1px solid #30363d; }
        .portal-box input { width: 100%; padding: 12px; margin: 10px 0; background: #010409; border: 1px solid #30363d; color: white; border-radius: 6px; box-sizing: border-box; outline: none; }
        .portal-box button { width: 100%; padding: 12px; background: #238636; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .portal-box button:hover { background: #2ea043; }
        .error-msg { color: #f85149; font-size: 13px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="portal-box">
        <h2>🔒 System Access</h2>
        <p style="color: #8b949e; font-size: 13px; margin-bottom: 15px;">Enter Master App Password</p>
        <input type="password" id="masterPassword" placeholder="Enter Access Password">
        <button onclick="verifyMasterPassword()">Access Portal</button>
        <div id="loginError" class="error-msg"></div>
    </div>
    <script>
        async function verifyMasterPassword() {
            const enteredPass = document.getElementById("masterPassword").value;
            try {
                let response = await fetch('/verify-master', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: enteredPass })
                });
                let result = await response.json();
                if (response.ok && result.status === "success") {
                    window.location.href = "/chat";
                } else {
                    document.getElementById("loginError").innerText = "Incorrect Master Password!";
                }
            } catch (err) {
                document.getElementById("loginError").innerText = "Server error, try again!";
            }
        }
    </script>
</body>
</html>
"""

# 2. Chat Room Page with Smart Call Lock Security
CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ghost Secret Tunnel</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { background-color: #0d1117; color: #ffffff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        #room-modal, #call-modal, #lock-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); display: flex; justify-content: center; align-items: center; z-index: 999; }
        .modal-box { background: #161b22; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.7); border: 1px solid #30363d; width: 90%; max-width: 400px; }
        #chat-screen { display: flex; width: 95%; max-width: 500px; height: 85vh; background: #161b22; border-radius: 12px; flex-direction: column; border: 1px solid #30363d; box-shadow: 0 4px 25px rgba(0,0,0,0.8); overflow: hidden; }
        .top-bar { background: #21262d; padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; }
        .top-bar h3 { margin: 0; font-size: 1rem; color: #58a6ff; }
        .call-btns { display: flex; gap: 6px; }
        .btn-call { padding: 6px 10px; border-radius: 6px; border: none; font-size: 0.8rem; font-weight: bold; cursor: pointer; color: white; }
        .btn-audio { background-color: #238636; }
        .btn-video { background-color: #1f6feb; }
        .btn-lock { background-color: #da3633; }
        #messages { flex-grow: 1; overflow-y: auto; padding: 15px; background: #0d1117; display: flex; flex-direction: column; gap: 10px; }
        .msg-card { padding: 10px 14px; border-radius: 10px; max-width: 75%; word-wrap: break-word; font-size: 0.95rem; position: relative; transition: opacity 0.5s ease; }
        .my-msg { background: #1f6feb; color: #ffffff; align-self: flex-end; border-bottom-right-radius: 2px; }
        .other-msg { background: #21262d; color: #c9d1d9; align-self: flex-start; border-bottom-left-radius: 2px; border: 1px solid #30363d; }
        .user-id { font-size: 0.75em; color: #8b949e; margin-bottom: 3px; display: block; font-weight: bold; }
        .timer-tag { font-size: 0.65em; opacity: 0.75; float: right; margin-top: 4px; margin-left: 10px; }
        .input-box { display: flex; padding: 12px; background: #21262d; gap: 8px; border-top: 1px solid #30363d; }
        input { width: 100%; padding: 10px; background: #0d1117; border: 1px solid #30363d; color: white; border-radius: 6px; outline: none; margin-bottom: 10px; }
        button.btn-send { padding: 10px 18px; background: #238636; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <div id="room-modal">
        <div class="modal-box">
            <h2>🔑 Access Reserved Room</h2>
            <p style="font-size: 0.8rem; color: #8b949e;">Apne reserved room ka name aur password daalein:</p>
            <input type="text" id="room-name" placeholder="Reserved Room Name" autocomplete="off">
            <input type="password" id="room-pass" placeholder="Room Secret Password" autocomplete="new-password">
            <button class="btn-send" style="width: 100%; margin-top: 5px;" onclick="joinReservedRoom()">Enter Reserved Room</button>
        </div>
    </div>

    <div id="lock-screen" style="display: none;">
        <div class="modal-box">
            <h2>🔒 Vault Locked</h2>
            <p style="color: #8b949e; font-size: 0.85rem; margin-bottom: 15px;">Enter PIN to Unlock Chat</p>
            <input type="password" id="unlock-pass" placeholder="Enter PIN">
            <button class="btn-send" style="width: 100%; margin-top:8px;" onclick="unlockChat()">Unlock Tunnel</button>
        </div>
    </div>

    <div id="call-modal" style="display: none;">
        <div class="modal-box">
            <h3 id="call-title">🔒 Encrypted Call</h3>
            <p id="call-status" style="color: #3fb950; margin: 15px 0;">Connecting Untraceable Direct Stream...</p>
            <button class="btn-call" style="background: #da3633; width: 100%;" onclick="endCall()">🔴 End Call</button>
        </div>
    </div>

    <div id="chat-screen">
        <div class="top-bar">
            <div>
                <h3>👻 Ghost Tunnel</h3>
                <span id="display-room-id" style="font-size: 0.75rem; color: #8b949e;">Room: Connecting...</span>
            </div>
            <div class="call-btns">
                <button class="btn-call btn-audio" onclick="startCall('Audio Call')">📞 Audio</button>
                <button class="btn-call btn-video" onclick="startCall('Video Call')">📹 Video</button>
                <button class="btn-call btn-lock" onclick="lockChat()">🔒 Lock</button>
            </div>
        </div>
        <div id="messages"></div>
        <div class="input-box">
            <input type="text" id="msg-input" placeholder="Type a message..." autocomplete="off" onkeypress="if(event.key==='Enter') sendMessage()" style="margin-bottom:0;">
            <button class="btn-send" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const socket = io();
        let myAgentID = "Agent_" + Math.floor(1000 + Math.random() * 9000);
        let currentRoom = "";
        let isCallActive = false;

        function joinReservedRoom() {
            const room = document.getElementById('room-name').value.trim();
            const pass = document.getElementById('room-pass').value.trim();
            if (room !== "" && pass !== "") {
                currentRoom = room + "_" + pass;
                socket.emit('join_room', { room: currentRoom, user: myAgentID });
                document.getElementById('room-modal').style.display = 'none';
                document.getElementById('display-room-id').innerText = "Room: " + room + " | " + myAgentID;
            } else {
                alert("Please enter both Room Name and Password!");
            }
        }

        function lockChat() { document.getElementById('lock-screen').style.display = 'flex'; }
        function unlockChat() {
            const pass = document.getElementById('unlock-pass').value;
            if (pass === "guru16230") {
                document.getElementById('lock-screen').style.display = 'none';
                document.getElementById('unlock-pass').value = "";
            } else { alert("Incorrect PIN!"); }
        }

        function sendMessage() {
            const input = document.getElementById('msg-input');
            if (input.value.trim() !== "") {
                const msgId = 'msg_' + Date.now();
                socket.emit('send_message', { id: msgId, room: currentRoom, user: myAgentID, msg: input.value });
                input.value = "";
            }
        }

        function removeMsgElement(msgCard) {
            if (msgCard && msgCard.parentNode) {
                msgCard.style.opacity = '0';
                setTimeout(() => { if (msgCard.parentNode) msgCard.parentNode.removeChild(msgCard); }, 500);
            }
        }

        socket.on('receive_message', (data) => {
            const msgBox = document.getElementById('messages');
            const isMe = data.user === myAgentID;
            const msgCard = document.createElement('div');
            msgCard.id = data.id;
            msgCard.className = `msg-card ${isMe ? 'my-msg' : 'other-msg'}`;
            msgCard.innerHTML = `<span class="user-id">${data.user}</span><div>${data.msg}</div><span class="timer-tag">🔥 Auto-Shred</span>`;
            msgBox.appendChild(msgCard);
            msgBox.scrollTop = msgBox.scrollHeight;
            setTimeout(() => { removeMsgElement(msgCard); }, 60000);
        });

        function startCall(type) {
            isCallActive = true;
            document.getElementById('call-title').innerText = "🔒 " + type;
            document.getElementById('call-modal').style.display = 'flex';
        }

        function endCall() {
            isCallActive = false;
            document.getElementById('call-modal').style.display = 'none';
        }

        // Smart Visibility Logic: Background mein call chalti rahegi, par agar phone lock hua toh call cut ho jayegi
        document.addEventListener("visibilitychange", function() {
            if (document.hidden && isCallActive) {
                // Agar phone lock hua ya screen off hui, toh visibility state 'hidden' ke sath time gap check hota hai ya turant cut hoti hai.
                // Mobile par power button dabane se document hidden ho jata hai aur page visibility turant zero ho jati hai.
                endCall();
                alert("🔒 Security Alert: Call terminated instantly due to device lock/screen off.");
            }
        });
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    if session.get('authenticated'):
        return redirect(url_for('chat'))
    return LOGIN_HTML

@app.route('/verify-master', methods=['POST'])
def verify_master():
    data = request.json
    if data and data.get('password') == APP_PASSWORD:
        session['authenticated'] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 401

@app.route('/chat')
def chat():
    if not session.get('authenticated'):
        return redirect(url_for('home'))
    return CHAT_HTML

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room')
    if room: join_room(room)

@socketio.on('send_message')
def handle_send_message(data):
    room = data.get('room')
    if room: emit('receive_message', data, to=room)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
