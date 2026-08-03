from flask import Flask, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghost_super_secret_key_998877"

# Master Admin Password & Credentials
REGISTERED_USERS = {
    "admin": "guru&guru16230"
}

# Security Trackers & Request System
FAILED_ATTEMPTS = {}       # {ip: count}
BLOCKED_IPS = {}           # {ip: True}
UNBLOCK_REQUESTS = {}      # {ip: {"username": username, "status": "Pending"}}

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 1. Login & Registration Portal HTML
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Access Portal</title>
    <style>
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .portal-box { background: #161b22; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 320px; text-align: center; border: 1px solid #30363d; }
        .portal-box input { width: 100%; padding: 12px; margin: 8px 0; background: #010409; border: 1px solid #30363d; color: white; border-radius: 6px; box-sizing: border-box; outline: none; }
        .portal-box button { width: 100%; padding: 12px; background: #238636; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .portal-box button:hover { background: #2ea043; }
        .tab-btn { background: #21262d; color: #8b949e; border: 1px solid #30363d; padding: 8px 12px; cursor: pointer; border-radius: 6px; font-weight: bold; width: 48%; }
        .tab-btn.active { background: #1f6feb; color: white; border-color: #1f6feb; }
        .tabs { display: flex; justify-content: space-between; margin-bottom: 15px; }
        .form-section { display: none; }
        .form-section.active { display: block; }
        .error-msg { color: #f85149; font-size: 13px; margin-top: 5px; }
        .success-msg { color: #3fb950; font-size: 13px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="portal-box" id="main-container">
        <h2>🔒 Secure Portal</h2>
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('login')">Login</button>
            <button class="tab-btn" onclick="switchTab('register')">Register</button>
        </div>

        <!-- Login Form -->
        <div id="login-form" class="form-section active">
            <input type="text" id="login-user" placeholder="Username" autocomplete="off">
            <input type="password" id="login-pass" placeholder="Password" autocomplete="new-password">
            <button id="loginBtn" onclick="loginUser()">Login to Chat</button>
            <div id="loginError" class="error-msg"></div>
        </div>

        <!-- Register Form -->
        <div id="register-form" class="form-section">
            <input type="text" id="reg-user" placeholder="Choose Username" autocomplete="off">
            <input type="password" id="reg-pass" placeholder="Choose Custom Password" autocomplete="new-password">
            <button onclick="registerUser()">Create Account</button>
            <div id="regMsg" class="error-msg"></div>
        </div>
    </div>

    <script>
        async function checkBlockStatus() {
            let res = await fetch('/check-status');
            let data = await res.json();
            if(data.blocked) {
                showBlockedScreen(data.requested, data.username);
            }
        }

        function showBlockedScreen(alreadyRequested, reqUsername) {
            const box = document.getElementById('main-container');
            box.innerHTML = `
                <h2 style="color: #f85149;">🚨 Device Blocked</h2>
                <p style="color: #8b949e; font-size: 13px; margin: 10px 0;">Attempted User: <b style="color:#58a6ff;">${reqUsername || 'Unknown'}</b></p>
                <p style="color: #8b949e; font-size: 12px; margin-bottom: 15px;">Blocked due to multiple failed login attempts.</p>
                <button id="req-btn" onclick="sendUnblockRequest()" ${alreadyRequested ? 'disabled style="background:#30363d; cursor:not-allowed;"' : ''}>
                    ${alreadyRequested ? '✅ Request Sent to Admin' : '📤 Request Admin to Unblock'}
                </button>
                <div id="req-msg" style="margin-top: 10px; font-size: 13px; color: ${alreadyRequested ? '#3fb950' : '#8b949e'};">
                    ${alreadyRequested ? 'Waiting for admin approval...' : ''}
                </div>
            `;
        }

        async function sendUnblockRequest() {
            let res = await fetch('/request-unblock', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
            let data = await res.json();
            if(data.status === "success") {
                document.getElementById('req-btn').innerText = "✅ Request Sent to Admin";
                document.getElementById('req-btn').disabled = true;
                document.getElementById('req-btn').style.background = "#30363d";
                document.getElementById('req-msg').style.color = "#3fb950";
                document.getElementById('req-msg').innerText = "Request sent successfully! Wait for admin.";
            }
        }

        function switchTab(tab) {
            document.querySelectorAll('.form-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            if(tab === 'login') {
                document.getElementById('login-form').classList.add('active');
                event.target.classList.add('active');
            } else {
                document.getElementById('register-form').classList.add('active');
                event.target.classList.add('active');
            }
        }

        async function loginUser() {
            const user = document.getElementById("login-user").value.trim();
            const pass = document.getElementById("login-pass").value.trim();
            let response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: user, password: pass })
            });
            let result = await response.json();
            if (response.ok && result.status === "success") {
                window.location.href = "/chat";
            } else if (result.status === "blocked") {
                showBlockedScreen(false, user);
            } else {
                document.getElementById("loginError").innerText = result.message || "Login failed!";
            }
        }

        async function registerUser() {
            const user = document.getElementById("reg-user").value.trim();
            const pass = document.getElementById("reg-pass").value.trim();
            let response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: user, password: pass })
            });
            let result = await response.json();
            let msgEl = document.getElementById("regMsg");
            if (response.ok && result.status === "success") {
                msgEl.className = "success-msg";
                msgEl.innerText = "Account created! You can now login.";
                setTimeout(() => switchTab('login'), 1500);
            } else {
                msgEl.className = "error-msg";
                msgEl.innerText = result.message || "Registration failed!";
            }
        }

        checkBlockStatus();
    </script>
</body>
</html>
"""

# 2. Admin Panel Page HTML
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <style>
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .admin-box { background: #161b22; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 440px; text-align: center; border: 1px solid #30363d; }
        ul { list-style: none; padding: 0; text-align: left; max-height: 260px; overflow-y: auto; margin-top: 15px; }
        li { background: #21262d; padding: 12px; margin-bottom: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #30363d; font-size: 13px; }
        button.unblock-btn { background: #238636; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button.unblock-btn:hover { background: #2ea043; }
        .back-link { display: inline-block; margin-top: 15px; color: #58a6ff; text-decoration: none; font-size: 13px; margin-right: 15px; }
    </style>
</head>
<body>
    <div class="admin-box">
        <h2>🛡️ Admin Control Panel</h2>
        <p style="color: #8b949e; font-size: 13px;">Secure Unblock Requests</p>
        <ul id="requests-list"></ul>
        <a href="/chat" class="back-link">⬅ Back to Chat</a>
        <a href="/" class="back-link" style="color: #f85149;">Logout</a>
    </div>

    <script>
        async function fetchRequests() {
            let res = await fetch('/get-unblock-requests');
            let data = await res.json();
            let listEl = document.getElementById('requests-list');
            listEl.innerHTML = "";
            if(data.requests.length === 0) {
                listEl.innerHTML = "<p style='color: #8b949e; text-align:center;'>No unblock requests.</p>";
                return;
            }
            data.requests.forEach(req => {
                listEl.innerHTML += `
                    <li>
                        <div>
                            <b>👤 User: <span style="color:#58a6ff; font-size:14px;">${req.username}</span></b><br>
                            <span style='color:#8b949e; font-size:11px;'>IP: ${req.ip}</span>
                        </div> 
                        <button class="unblock-btn" onclick="approveUnblock('${req.ip}')">Unblock</button>
                    </li>`;
            });
        }

        async function approveUnblock(ip) {
            await fetch('/approve-unblock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip: ip })
            });
            fetchRequests();
        }

        fetchRequests();
        setInterval(fetchRequests, 5000);
    </script>
</body>
</html>
"""

# 3. Chat Room Page HTML
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
        .call-btns { display: flex; gap: 5px; align-items: center; }
        .btn-call { padding: 6px 8px; border-radius: 6px; border: none; font-size: 0.75rem; font-weight: bold; cursor: pointer; color: white; }
        .btn-audio { background-color: #238636; }
        .btn-video { background-color: #1f6feb; }
        .btn-admin { background-color: #8957e5; display: none; }
        .btn-lock { background-color: #da3633; }
        #messages { flex-grow: 1; overflow-y: auto; padding: 15px; background: #0d1117; display: flex; flex-direction: column; gap: 10px; }
        .msg-card { padding: 10px 14px; border-radius: 10px; max-width: 75%; word-wrap: break-word; font-size: 0.95rem; position: relative; }
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
            <input type="text" id="room-name" placeholder="Reserved Room Name" autocomplete="off">
            <input type="password" id="room-pass" placeholder="Room Secret Password" autocomplete="new-password">
            <button class="btn-send" style="width: 100%; margin-top: 5px;" onclick="joinReservedRoom()">Enter Room</button>
        </div>
    </div>

    <div id="lock-screen" style="display: none;">
        <div class="modal-box">
            <h2>🔒 Vault Locked</h2>
            <input type="password" id="unlock-pass" placeholder="Enter PIN">
            <button class="btn-send" style="width: 100%; margin-top:8px;" onclick="unlockChat()">Unlock</button>
        </div>
    </div>

    <div id="call-modal" style="display: none;">
        <div class="modal-box">
            <h3 id="call-title">🔒 Encrypted Call</h3>
            <p id="call-status" style="color: #3fb950; margin: 15px 0; font-size:14px;">Connecting...</p>
            <button class="btn-call" style="background: #da3633; width: 100%; padding:10px;" onclick="endCall()">🔴 End Call</button>
        </div>
    </div>

    <div id="chat-screen">
        <div class="top-bar">
            <div>
                <h3>👻 Ghost Tunnel</h3>
                <span id="display-room-id" style="font-size: 0.75rem; color: #8b949e;">Room: Connecting...</span>
            </div>
            <div class="call-btns">
                <button class="btn-call btn-audio" onclick="startCall()">📞</button>
                <button class="btn-call btn-video" onclick="startCall()">📹</button>
                <button id="admin-panel-btn" class="btn-call btn-admin" onclick="window.location.href='/admin-panel-guru'">🛡️ Admin</button>
                <button class="btn-call btn-lock" onclick="lockChat()">🔒</button>
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

        // Check if current user is admin to display admin panel button
        async function checkAdminAccess() {
            let res = await fetch('/check-admin-session');
            let data = await res.json();
            if(data.is_admin) {
                document.getElementById('admin-panel-btn').style.display = 'inline-block';
            }
        }
        checkAdminAccess();

        function joinReservedRoom() {
            const room = document.getElementById('room-name').value.trim();
            const pass = document.getElementById('room-pass').value.trim();
            if (room !== "" && pass !== "") {
                currentRoom = room + "_" + pass;
                socket.emit('join_room', { room: currentRoom, user: myAgentID });
                document.getElementById('room-modal').style.display = 'none';
                document.getElementById('display-room-id').innerText = "Room: " + room + " | " + myAgentID;
            } else { alert("Enter Room Name & Password!"); }
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

        socket.on('receive_message', (data) => {
            const msgBox = document.getElementById('messages');
            const isMe = data.user === myAgentID;
            const msgCard = document.createElement('div');
            msgCard.className = `msg-card ${isMe ? 'my-msg' : 'other-msg'}`;
            msgCard.innerHTML = `<span class="user-id">${data.user}</span><div>${data.msg}</div><span class="timer-tag">🔥 Auto-Shred</span>`;
            msgBox.appendChild(msgCard);
            msgBox.scrollTop = msgBox.scrollHeight;
            setTimeout(() => { if(msgCard.parentNode) msgCard.parentNode.removeChild(msgCard); }, 60000);
        });

        function startCall() { isCallActive = true; document.getElementById('call-modal').style.display = 'flex'; }
        function endCall() { isCallActive = false; document.getElementById('call-modal').style.display = 'none'; }

        document.addEventListener("visibilitychange", function() {
            if (document.hidden) {
                if (isCallActive) endCall();
                fetch('/logout');
            }
        });
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    return LOGIN_HTML

@app.route('/check-status', methods=['GET'])
def check_status():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    is_blocked = user_ip in BLOCKED_IPS
    has_requested = user_ip in UNBLOCK_REQUESTS
    req_username = UNBLOCK_REQUESTS.get(user_ip, {}).get("username", "") if has_requested else ""
    return jsonify({"blocked": is_blocked, "requested": has_requested, "username": req_username})

@app.route('/request-unblock', methods=['POST'])
def request_unblock():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip in BLOCKED_IPS and user_ip in UNBLOCK_REQUESTS:
        UNBLOCK_REQUESTS[user_ip]["status"] = "Pending"
    return jsonify({"status": "success"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({"status": "error", "message": "All fields are required!"}), 400
    if username in REGISTERED_USERS:
        return jsonify({"status": "error", "message": "Username already exists!"}), 400
    REGISTERED_USERS[username] = password
    return jsonify({"status": "success"})

@app.route('/login', methods=['POST'])
def login():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip in BLOCKED_IPS:
        return jsonify({"status": "blocked"}), 403

    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if username in REGISTERED_USERS and REGISTERED_USERS[username] == password:
        FAILED_ATTEMPTS[user_ip] = 0
        session['authenticated'] = True
        session['user'] = username
        session['is_admin'] = (username == "admin")
        return jsonify({"status": "success"})
    else:
        FAILED_ATTEMPTS[user_ip] = FAILED_ATTEMPTS.get(user_ip, 0) + 1
        if FAILED_ATTEMPTS[user_ip] >= 5:
            BLOCKED_IPS[user_ip] = True
            UNBLOCK_REQUESTS[user_ip] = {"username": username if username else "Unknown", "status": "Pending"}
            return jsonify({"status": "blocked"}), 403
            
        remaining = 5 - FAILED_ATTEMPTS[user_ip]
        return jsonify({"status": "error", "message": f"Invalid credentials! {remaining} attempts left."}), 401

@app.route('/check-admin-session', methods=['GET'])
def check_admin_session():
    return jsonify({"is_admin": session.get('is_admin', False)})

@app.route('/admin-panel-guru', methods=['GET'])
def admin_panel():
    if not session.get('is_admin', False):
        return redirect(url_for('home'))
    return ADMIN_HTML

@app.route('/get-unblock-requests', methods=['GET'])
def get_unblock_requests():
    if not session.get('is_admin', False):
        return jsonify({"requests": []}), 403
    req_list = [{"ip": ip, "username": info["username"]} for ip, info in UNBLOCK_REQUESTS.items()]
    return jsonify({"requests": req_list})

@app.route('/approve-unblock', methods=['POST'])
def approve_unblock():
    if not session.get('is_admin', False):
        return jsonify({"status": "unauthorized"}), 403
    data = request.json
    ip = data.get('ip')
    if ip in BLOCKED_IPS: del BLOCKED_IPS[ip]
    if ip in UNBLOCK_REQUESTS: del UNBLOCK_REQUESTS[ip]
    if ip in FAILED_ATTEMPTS: FAILED_ATTEMPTS[ip] = 0
    return jsonify({"status": "success"})

@app.route('/chat')
def chat():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip in BLOCKED_IPS or not session.get('authenticated'):
        return redirect(url_for('home'))
    return CHAT_HTML

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({"status": "logged_out"})

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)

@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, to=data['room'])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
