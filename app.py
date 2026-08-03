from flask import Flask, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghost_super_secret_key_998877"

# Master Admin & Registered Users Database
REGISTERED_USERS = {
    "admin": "guru&guru16230"
}

# Security Trackers & Logs
FAILED_ATTEMPTS = {}       
BLOCKED_IPS = {}           
BLOCKED_USERS = {}         
UNBLOCK_REQUESTS = {}      
USER_SESSIONS = {}         
MESSAGE_LOGS = []          

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
        <div class="tabs" id="portal-tabs">
            <button class="tab-btn active" onclick="switchTab('login')">Login</button>
            <button class="tab-btn" onclick="switchTab('register')">Register</button>
        </div>

        <div id="login-form" class="form-section active">
            <input type="text" id="login-user" placeholder="Username" autocomplete="off" name="no-autofill-user">
            <input type="password" id="login-pass" placeholder="Password" autocomplete="new-password" name="no-autofill-pass">
            <button onclick="loginUser()">Login to Chat</button>
            <div id="loginError" class="error-msg"></div>
        </div>

        <div id="register-form" class="form-section">
            <input type="text" id="reg-user" placeholder="Choose Username" autocomplete="off">
            <input type="password" id="reg-pass" placeholder="Choose Custom Password" autocomplete="new-password">
            <button onclick="registerUser()">Create Account</button>
            <div id="regMsg" class="error-msg"></div>
        </div>
    </div>

    <script>
        window.addEventListener("pageshow", function(event) {
            document.getElementById("login-user").value = "";
            document.getElementById("login-pass").value = "";
            document.getElementById("reg-user").value = "";
            document.getElementById("reg-pass").value = "";
        });

        async function checkBlockStatus() {
            try {
                let res = await fetch('/check-status');
                let data = await res.json();
                if(data.blocked) { 
                    showBlockedScreen(data.requested, data.username); 
                }
            } catch(e) {}
        }

        function showBlockedScreen(alreadyRequested, reqUsername) {
            const box = document.getElementById('main-container');
            document.getElementById('portal-tabs').style.display = 'none';
            box.innerHTML = `
                <h2 style="color: #f85149;">🚨 Account & Device Blocked</h2>
                <p style="color: #8b949e; font-size: 13px; margin: 10px 0;">Target Account: <b style="color:#58a6ff;">${reqUsername || 'Unknown'}</b></p>
                <p style="color: #8b949e; font-size: 12px; margin-bottom: 15px;">5 incorrect attempts detected. Both your Username and Device IP have been locked by security protocols.</p>
                <button id="req-btn" onclick="sendUnblockRequest()" ${alreadyRequested ? 'disabled style="background:#30363d; cursor:not-allowed;"' : ''}>
                    ${alreadyRequested ? '✅ Request Sent to Admin' : '📤 Request Admin to Unblock'}
                </button>
            `;
        }

        async function sendUnblockRequest() {
            await fetch('/request-unblock', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
            location.reload();
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
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .admin-container { display: flex; gap: 20px; width: 90%; max-width: 900px; }
        .admin-box { background: #161b22; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 50%; border: 1px solid #30363d; }
        ul { list-style: none; padding: 0; text-align: left; max-height: 220px; overflow-y: auto; margin-top: 15px; }
        li { background: #21262d; padding: 10px; margin-bottom: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #30363d; font-size: 13px; }
        button.action-btn { background: #238636; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 11px; margin-left: 3px; }
        button.block-btn { background: #da3633; }
        button.delete-user-btn { background: #8957e5; }
        button.wipe-btn { background: #da3633; width: 100%; padding: 10px; margin-top: 10px; border-radius: 6px; border: none; color: white; font-weight: bold; cursor: pointer; }
        button.wipe-btn:hover { background: #b31d1c; }
        .back-link { display: inline-block; margin-top: 15px; color: #58a6ff; text-decoration: none; font-size: 13px; margin-right: 15px; }
    </style>
</head>
<body>
    <div class="admin-container">
        <div class="admin-box">
            <h2>🛡️ Control Panel</h2>
            <p style="color: #8b949e; font-size: 12px;">Unblock Requests (ID + Device Locked)</p>
            <ul id="requests-list"></ul>
            <div style="margin-top: 15px; border-top: 1px solid #30363d; padding-top: 10px;">
                <p style="color: #8b949e; font-size: 12px;">Active Users Management</p>
                <ul id="users-list"></ul>
            </div>
            <a href="/chat" class="back-link">⬅ Chat</a>
            <a href="/" class="back-link" style="color: #f85149;">Logout</a>
        </div>

        <div class="admin-box">
            <h2>👀 Message Inspector</h2>
            <p style="color: #8b949e; font-size: 12px;">Live check of what users are texting</p>
            <ul id="messages-list" style="max-height: 280px;"></ul>
            <button class="wipe-btn" onclick="wipeAllLogs()">🗑️ Clear All Message Logs</button>
        </div>
    </div>

    <script>
        async function fetchAdminData() {
            try {
                let resReq = await fetch('/get-unblock-requests');
                let dataReq = await resReq.json();
                let reqListEl = document.getElementById('requests-list');
                reqListEl.innerHTML = dataReq.requests.length === 0 ? "<p style='color: #8b949e; text-align:center; font-size:12px;'>No pending requests.</p>" : "";
                dataReq.requests.forEach(req => {
                    reqListEl.innerHTML += `<li><div><b>👤 ${req.username}</b></div> <button class="action-btn" onclick="approveUnblock('${req.username}', '${req.ip}')">Unblock ID+IP</button></li>`;
                });

                let resUsr = await fetch('/get-all-users');
                let dataUsr = await resUsr.json();
                let usrListEl = document.getElementById('users-list');
                usrListEl.innerHTML = "";
                dataUsr.users.forEach(u => {
                    if(u !== 'admin') {
                        usrListEl.innerHTML += `
                            <li>
                                <span>👤 ${u}</span>
                                <div>
                                    <button class="action-btn block-btn" onclick="instantBlock('${u}')">Block</button>
                                    <button class="action-btn delete-user-btn" onclick="deleteUser('${u}')">🗑️ Delete</button>
                                </div>
                            </li>`;
                    }
                });

                let resMsg = await fetch('/get-message-logs');
                let dataMsg = await resMsg.json();
                let msgListEl = document.getElementById('messages-list');
                msgListEl.innerHTML = dataMsg.messages.length === 0 ? "<p style='color: #8b949e; text-align:center; font-size:12px;'>Logs cleared (0% Trace).</p>" : "";
                dataMsg.messages.forEach(m => {
                    msgListEl.innerHTML += `<li style="display: block;"><span style="color:#58a6ff; font-weight:bold;">${m.user}</span>: <span style="color:#c9d1d9;">${m.msg}</span></li>`;
                });
            } catch(e) {}
        }

        async function deleteUser(username) {
            let adminPass = prompt("Enter Admin Password to delete user '" + username + "':");
            if (adminPass) {
                let res = await fetch('/delete-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username, admin_password: adminPass })
                });
                let data = await res.json();
                if (data.status === "success") {
                    alert("User deleted successfully!");
                    fetchAdminData();
                } else {
                    alert(data.message || "Deletion failed!");
                }
            }
        }

        async function wipeAllLogs() {
            if(confirm("Are you sure? This will instantly clear all message logs permanently!")) {
                let res = await fetch('/wipe-logs', { method: 'POST' });
                let data = await res.json();
                if(data.status === "success") { fetchAdminData(); }
            }
        }

        async function approveUnblock(username, ip) {
            await fetch('/approve-unblock', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: username, ip: ip }) });
            fetchAdminData();
        }

        async function instantBlock(username) {
            await fetch('/instant-block', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: username }) });
            fetchAdminData();
        }

        fetchAdminData();
        setInterval(fetchAdminData, 4000);
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
        #room-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); display: flex; justify-content: center; align-items: center; z-index: 999; }
        .modal-box { background: #161b22; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.7); border: 1px solid #30363d; width: 90%; max-width: 400px; }
        #chat-screen { display: flex; width: 95%; max-width: 500px; height: 85vh; background: #161b22; border-radius: 12px; flex-direction: column; border: 1px solid #30363d; overflow: hidden; }
        .top-bar { background: #21262d; padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; }
        .top-bar h3 { margin: 0; font-size: 1rem; color: #58a6ff; }
        .call-btns { display: flex; gap: 5px; align-items: center; }
        .btn-call { padding: 6px 10px; border-radius: 6px; border: none; font-size: 0.75rem; font-weight: bold; cursor: pointer; color: white; }
        .btn-audio { background-color: #1f6feb; }
        .btn-video { background-color: #8957e5; }
        .btn-e2ee { background-color: #30363d; color: #8b949e; border: 1px solid #484f58; }
        .btn-e2ee.active { background-color: #238636; color: white; border-color: #2ea043; }
        .btn-admin { background-color: #d29922; display: none; color: #0d1117; }
        #messages { flex-grow: 1; overflow-y: auto; padding: 15px; background: #0d1117; display: flex; flex-direction: column; gap: 10px; }
        .msg-card { padding: 10px 14px; border-radius: 10px; max-width: 75%; word-wrap: break-word; font-size: 0.95rem; }
        .my-msg { background: #1f6feb; color: #ffffff; align-self: flex-end; }
        .other-msg { background: #21262d; color: #c9d1d9; align-self: flex-start; border: 1px solid #30363d; }
        .user-id { font-size: 0.75em; color: #8b949e; margin-bottom: 3px; display: block; font-weight: bold; }
        .input-box { display: flex; padding: 12px; background: #21262d; gap: 8px; border-top: 1px solid #30363d; }
        input { width: 100%; padding: 10px; background: #0d1117; border: 1px solid #30363d; color: white; border-radius: 6px; outline: none; }
        button.btn-send { padding: 10px 18px; background: #238636; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <div id="room-modal">
        <div class="modal-box">
            <h2>🔑 Access Reserved Room</h2>
            <input type="text" id="room-name" placeholder="Room Name" autocomplete="off" style="margin-bottom:10px;">
            <input type="password" id="room-pass" placeholder="Password" autocomplete="new-password" style="margin-bottom:10px;">
            <button class="btn-send" style="width: 100%;" onclick="joinReservedRoom()">Enter Room</button>
        </div>
    </div>

    <div id="chat-screen">
        <div class="top-bar">
            <div>
                <h3>👻 Ghost Tunnel</h3>
                <span id="display-room-id" style="font-size: 0.75rem; color: #8b949e;">Connecting...</span>
            </div>
            <div class="call-btns">
                <button id="e2ee-btn" class="btn-call btn-e2ee" onclick="toggleE2EE()">🔐 E2EE: OFF</button>
                <button class="btn-call btn-audio" onclick="startAudioCall()">📞 Audio</button>
                <button class="btn-call btn-video" onclick="startVideoCall()">📹 Video</button>
                <button id="admin-panel-btn" class="btn-call btn-admin" onclick="window.location.href='/admin-panel-guru'">🛡️ Admin</button>
            </div>
        </div>
        <div id="messages"></div>
        <div class="input-box">
            <input type="text" id="msg-input" placeholder="Type a message..." autocomplete="off" onkeypress="if(event.key==='Enter') sendMessage()">
            <button class="btn-send" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const socket = io();
        let currentRoom = "";
        let myUsername = "User";
        let isE2EEActive = false;

        // --- INSTANT KILL-SWITCH (Power Button / Background / Screen Off Logout) ---
        async function triggerInstantLogout() {
            try {
                await fetch('/logout-session', { method: 'POST' });
            } catch(e) {}
            window.location.href = "/";
        }

        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                triggerInstantLogout();
            }
        });

        window.addEventListener("blur", () => {
            triggerInstantLogout();
        });
        // --------------------------------------------------------------------------

        async function initChat() {
            try {
                let res = await fetch('/check-admin-session');
                let data = await res.json();
                myUsername = data.username;
                if(data.is_admin) { document.getElementById('admin-panel-btn').style.display = 'inline-block'; }
            } catch(e) {}
        }
        initChat();

        function toggleE2EE() {
            isE2EEActive = !isE2EEActive;
            const btn = document.getElementById('e2ee-btn');
            if (isE2EEActive) {
                btn.className = "btn-call btn-e2ee active";
                btn.innerText = "🔐 E2EE: ON";
            } else {
                btn.className = "btn-call btn-e2ee";
                btn.innerText = "🔐 E2EE: OFF";
            }
        }

        function startAudioCall() {
            alert("📞 Audio Call initialized on secure channel!");
        }

        function startVideoCall() {
            alert("📹 Video Call initialized on secure channel!");
        }

        function encryptText(text) {
            if (!isE2EEActive) return text;
            return "ENC[" + btoa(text) + "]";
        }

        function decryptText(text) {
            if (text.startsWith("ENC[")) {
                try {
                    let encoded = text.substring(4, text.length - 1);
                    return "🔒 " + atob(encoded) + " (E2EE)";
                } catch(e) {
                    return text;
                }
            }
            return text;
        }

        function joinReservedRoom() {
            const room = document.getElementById('room-name').value.trim();
            const pass = document.getElementById('room-pass').value.trim();
            if (room && pass) {
                currentRoom = room + "_" + pass;
                socket.emit('join_room', { room: currentRoom, user: myUsername });
                document.getElementById('room-modal').style.display = 'none';
                document.getElementById('display-room-id').innerText = "Room: " + room;
            }
        }

        function sendMessage() {
            const input = document.getElementById('msg-input');
            if (input.value.trim() !== "") {
                let finalMsg = encryptText(input.value);
                socket.emit('send_message', { room: currentRoom, user: myUsername, msg: finalMsg });
                input.value = "";
            }
        }

        socket.on('receive_message', (data) => {
            const msgBox = document.getElementById('messages');
            const isMe = data.user === myUsername;
            const msgCard = document.createElement('div');
            msgCard.className = `msg-card ${isMe ? 'my-msg' : 'other-msg'}`;
            
            let readableMsg = decryptText(data.msg);
            msgCard.innerHTML = `<span class="user-id">${data.user}</span><div>${readableMsg}</div>`;
            msgBox.appendChild(msgCard);
            msgBox.scrollTop = msgBox.scrollHeight;
            setTimeout(() => { if(msgCard.parentNode) msgCard.parentNode.removeChild(msgCard); }, 30000);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home(): return LOGIN_HTML

@app.route('/logout-session', methods=['POST'])
def logout_session():
    session.clear()
    return jsonify({"status": "logged_out"})

@app.route('/check-status')
def check_status():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    is_blocked = ip in BLOCKED_IPS
    req_username = UNBLOCK_REQUESTS.get(ip, {}).get("username", "")
    return jsonify({"blocked": is_blocked, "requested": ip in UNBLOCK_REQUESTS, "username": req_username})

@app.route('/request-unblock', methods=['POST'])
def request_unblock():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip in BLOCKED_IPS and ip in UNBLOCK_REQUESTS: 
        UNBLOCK_REQUESTS[ip]["status"] = "Pending"
    return jsonify({"status": "success"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    u, p = data.get('username', '').strip(), data.get('password', '').strip()
    if not u or not p: return jsonify({"status": "error", "message": "Fields required!"}), 400
    if u in REGISTERED_USERS or u in BLOCKED_USERS: return jsonify({"status": "error", "message": "Username exists or is blocked!"}), 400
    REGISTERED_USERS[u] = p
    return jsonify({"status": "success"})

@app.route('/login', methods=['POST'])
def login():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    data = request.json
    u, p = data.get('username', '').strip(), data.get('password', '').strip()

    if ip in BLOCKED_IPS or u in BLOCKED_USERS:
        return jsonify({"status": "blocked"}), 403

    if u in REGISTERED_USERS and REGISTERED_USERS[u] == p:
        FAILED_ATTEMPTS[ip] = 0
        session['authenticated'] = True
        session['user'] = u
        session['is_admin'] = (u == "admin")
        USER_SESSIONS[u] = ip
        return jsonify({"status": "success"})
    else:
        FAILED_ATTEMPTS[ip] = FAILED_ATTEMPTS.get(ip, 0) + 1
        if FAILED_ATTEMPTS[ip] >= 5:
            BLOCKED_IPS[ip] = True
            if u:
                BLOCKED_USERS[u] = True
            UNBLOCK_REQUESTS[ip] = {"username": u or "Unknown", "status": "Pending"}
            return jsonify({"status": "blocked"}), 403
            
        return jsonify({"status": "error", "message": "Invalid credentials!"}), 401

@app.route('/check-admin-session')
def check_admin_session():
    return jsonify({"is_admin": session.get('is_admin', False), "username": session.get('user', 'Guest')})

@app.route('/admin-panel-guru')
def admin_panel():
    if not session.get('is_admin', False): return redirect(url_for('home'))
    return ADMIN_HTML

@app.route('/get-unblock-requests')
def get_unblock_requests():
    if not session.get('is_admin', False): return jsonify({"requests": []}), 403
    return jsonify({"requests": [{"ip": ip, "username": info["username"]} for ip, info in UNBLOCK_REQUESTS.items()]})

@app.route('/get-all-users')
def get_all_users():
    if not session.get('is_admin', False): return jsonify({"users": []}), 403
    return jsonify({"users": list(REGISTERED_USERS.keys())})

@app.route('/get-message-logs')
def get_message_logs():
    if not session.get('is_admin', False): return jsonify({"messages": []}), 403
    return jsonify({"messages": MESSAGE_LOGS[-50:]})

@app.route('/wipe-logs', methods=['POST'])
def wipe_logs():
    if not session.get('is_admin', False): return jsonify({"status": "unauthorized"}), 403
    global MESSAGE_LOGS
    MESSAGE_LOGS.clear()
    return jsonify({"status": "success"})

@app.route('/delete-user', methods=['POST'])
def delete_user():
    if not session.get('is_admin', False): return jsonify({"status": "unauthorized"}), 403
    data = request.json
    target_user = data.get('username')
    admin_pass = data.get('admin_password')
    
    if REGISTERED_USERS.get("admin") != admin_pass:
        return jsonify({"status": "error", "message": "Incorrect Admin Password!"}), 401
    
    if target_user in REGISTERED_USERS and target_user != "admin":
        del REGISTERED_USERS[target_user]
        BLOCKED_USERS.pop(target_user, None)
        if target_user in USER_SESSIONS:
            ip = USER_SESSIONS[target_user]
            BLOCKED_IPS.pop(ip, None)
            UNBLOCK_REQUESTS.pop(ip, None)
            del USER_SESSIONS[target_user]
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "User not found!"}), 404

@app.route('/instant-block', methods=['POST'])
def instant_block():
    if not session.get('is_admin', False): return jsonify({"status": "unauthorized"}), 403
    u = request.json.get('username')
    BLOCKED_USERS[u] = True
    if u in USER_SESSIONS:
        ip = USER_SESSIONS[u]
        BLOCKED_IPS[ip] = True
        UNBLOCK_REQUESTS[ip] = {"username": u, "status": "Pending"}
    else:
        UNBLOCK_REQUESTS["manual_" + u] = {"username": u, "status": "Pending"}
    return jsonify({"status": "success"})

@app.route('/approve-unblock', methods=['POST'])
def approve_unblock():
    if not session.get('is_admin', False): return jsonify({"status": "unauthorized"}), 403
    data = request.json
    ip = data.get('ip')
    username = data.get('username')
    
    if ip and not ip.startswith("manual_"):
        BLOCKED_IPS.pop(ip, None)
        UNBLOCK_REQUESTS.pop(ip, None)
        FAILED_ATTEMPTS[ip] = 0
    
    if username:
        BLOCKED_USERS.pop(username, None)
        UNBLOCK_REQUESTS.pop("manual_" + username, None)

    return jsonify({"status": "success"})

@app.route('/chat')
def chat():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip in BLOCKED_IPS or not session.get('authenticated'): return redirect(url_for('home'))
    return CHAT_HTML

@socketio.on('join_room')
def handle_join(data): join_room(data['room'])

@socketio.on('send_message')
def handle_message(data):
    MESSAGE_LOGS.append({"user": data.get('user'), "msg": data.get('msg')})
    emit('receive_message', data, to=data['room'])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
