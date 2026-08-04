from flask import Flask, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghost_super_secret_key_998877"

REGISTERED_USERS = {
    "admin": "guru&guru16230"
}

FAILED_ATTEMPTS = {}
BLOCKED_IPS = {}
BLOCKED_USERS = {}
UNBLOCK_REQUESTS = {}
USER_SESSIONS = {}

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Access Portal</title>
    <style>
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; user-select: none; }
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
        .unblock-btn-link { background: none; border: none; color: #58a6ff; font-size: 12px; cursor: pointer; text-decoration: underline; margin-top: 12px; width: 100%; }
    </style>
</head>
<body>
    <div class="portal-box" id="main-container">
        <h2>🔒 Secure Portal</h2>
        <div class="tabs" id="portal-tabs">
            <button class="tab-btn active" onclick="switchTab('login', event)">Login</button>
            <button class="tab-btn" onclick="switchTab('register', event)">Register</button>
        </div>

        <div id="login-form" class="form-section active">
            <input type="text" id="login-user" placeholder="Username" autocomplete="off">
            <input type="password" id="login-pass" placeholder="Password" autocomplete="new-password">
            <button onclick="loginUser()">Login to Chat</button>
            <div id="loginError" class="error-msg"></div>
            <button class="unblock-btn-link" onclick="requestUnblockPrompt()">Forgot / Request Unblock Access?</button>
        </div>

        <div id="register-form" class="form-section">
            <input type="text" id="reg-user" placeholder="Choose Username" autocomplete="off">
            <input type="password" id="reg-pass" placeholder="Choose Custom Password" autocomplete="new-password">
            <button onclick="registerUser()">Create Account</button>
            <div id="regMsg" class="error-msg"></div>
        </div>
    </div>

    <script>
        function switchTab(tab, event) {
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

        async function requestUnblockPrompt() {
            let u = prompt("Enter your Username or ID to send unblock request to Admin:");
            if(u && u.trim() !== "") {
                let res = await fetch('/manual-unblock-request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: u.trim() })
                });
                let data = await res.json();
                if(data.status === "success") {
                    alert("✅ Unblock request successfully sent to Admin!");
                } else {
                    alert("❌ Failed to send request.");
                }
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
                alert("🚨 Your account or device is blocked by admin security.");
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
                setTimeout(() => switchTab('login', {target: document.querySelector('.tab-btn')}), 1500);
            } else {
                msgEl.className = "error-msg";
                msgEl.innerText = result.message || "Registration failed!";
            }
        }
    </script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <style>
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; user-select: none; }
        .admin-container { display: flex; gap: 20px; width: 90%; max-width: 900px; }
        .admin-box { background: #161b22; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 100%; border: 1px solid #30363d; }
        ul { list-style: none; padding: 0; text-align: left; max-height: 220px; overflow-y: auto; margin-top: 15px; }
        li { background: #21262d; padding: 10px; margin-bottom: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #30363d; font-size: 13px; }
        button.action-btn { background: #238636; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 11px; margin-left: 3px; }
        button.block-btn { background: #da3633; }
        button.delete-user-btn { background: #8957e5; }
        .back-link { display: inline-block; margin-top: 15px; color: #58a6ff; text-decoration: none; font-size: 13px; margin-right: 15px; }
    </style>
</head>
<body>
    <div class="admin-container">
        <div class="admin-box">
            <h2>🛡️ Control Panel (Strict 0% Logs Mode)</h2>
            <p style="color: #8b949e; font-size: 12px;">Unblock & Reset Requests</p>
            <ul id="requests-list"></ul>
            <div style="margin-top: 15px; border-top: 1px solid #30363d; padding-top: 10px;">
                <p style="color: #8b949e; font-size: 12px;">Active Users Management</p>
                <ul id="users-list"></ul>
            </div>
            <a href="/chat" class="back-link">⬅ Chat</a>
            <a href="/" class="back-link" style="color: #f85149;">Logout</a>
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
                    reqListEl.innerHTML += `<li><div><b>👤 ${req.username}</b></div> <button class="action-btn" onclick="approveUnblock('${req.username}', '${req.ip}')">Unblock</button></li>`;
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
                if (data.status === "success") { alert("User deleted!"); fetchAdminData(); }
                else { alert(data.message || "Failed!"); }
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
        body { background-color: #0d1117; color: #ffffff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; user-select: none; }
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
        input { width: 100%; padding: 10px; background: #0d1117; border: 1px solid #30363d; color: white; border-radius: 6px; outline: none; user-select: text; }
        button.btn-send { padding: 10px 18px; background: #238636; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        #video-container { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 1000; justify-content: center; align-items: center; flex-direction: column; }
        video { width: 80%; max-width: 400px; border-radius: 8px; background: black; margin-bottom: 10px; }
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

    <div id="video-container">
        <video id="localVideo" autoplay playsinline muted></video>
        <video id="remoteVideo" autoplay playsinline></video>
        <button class="btn-send" style="background:#da3633;" onclick="endCall()">End Call</button>
    </div>

    <div id="chat-screen">
        <div class="top-bar">
            <div>
                <h3>👻 Ghost Tunnel</h3>
                <span id="display-room-id" style="font-size: 0.75rem; color: #8b949e;">Connecting...</span>
            </div>
            <div class="call-btns">
                <button id="e2ee-btn" class="btn-call btn-e2ee" onclick="toggleE2EE()">🔐 E2EE: OFF</button>
                <button class="btn-call btn-audio" onclick="startCall('audio')">📞 Audio</button>
                <button class="btn-call btn-video" onclick="startCall('video')">📹 Video</button>
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
        let localStream, peerConnection;
        
        let isE2EEActive = localStorage.getItem('ghost_e2ee') === 'true';
        updateE2EEButtonUI();

        socket.on('connect', () => {
            console.log("Connected to Socket.io Server, ID:", socket.id);
        });

        document.addEventListener('contextmenu', event => event.preventDefault());

        async function triggerInstantLogout() {
            try {
                navigator.sendBeacon('/logout-session');
                localStorage.clear();
                sessionStorage.clear();
            } catch(e) {}
        }

        window.addEventListener("pagehide", triggerInstantLogout);
        window.addEventListener("beforeunload", triggerInstantLogout);
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) triggerInstantLogout();
        });

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
            localStorage.setItem('ghost_e2ee', isE2EEActive);
            updateE2EEButtonUI();
        }

        function updateE2EEButtonUI() {
            const btn = document.getElementById('e2ee-btn');
            if (isE2EEActive) { 
                btn.className = "btn-call btn-e2ee active"; 
                btn.innerText = "🔐 E2EE: ON"; 
            } else { 
                btn.className = "btn-call btn-e2ee"; 
                btn.innerText = "🔐 E2EE: OFF"; 
            }
        }

        function encryptText(text) { return !isE2EEActive ? text : "ENC[" + btoa(text) + "]"; }
        function decryptText(text) {
            if (text.startsWith("ENC[")) {
                try { return "🔒 " + atob(text.substring(4, text.length - 1)) + " (E2EE)"; } catch(e) { return text; }
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
                console.log("Joined room:", currentRoom);
            } else {
                alert("Please enter both Room Name and Password!");
            }
        }

        function sendMessage() {
            const input = document.getElementById('msg-input');
            const text = input.value.trim();
            if (text !== "") {
                if (!currentRoom) {
                    alert("Error: You have not joined any room yet!");
                    return;
                }
                console.log("Sending message to room:", currentRoom);
                socket.emit('send_message', { room: currentRoom, user: myUsername, msg: encryptText(text), timestamp: Date.now() });
                input.value = "";
            }
        }

        socket.on('receive_message', (data) => {
            console.log("Received message:", data);
            const now = Date.now();
            const msgTimestamp = data.timestamp || now;
            
            const msgBox = document.getElementById('messages');
            const isMe = data.user === myUsername;
            const msgCard = document.createElement('div');
            msgCard.className = `msg-card ${isMe ? 'my-msg' : 'other-msg'}`;
            msgCard.innerHTML = `<span class="user-id">${data.user}</span><div>${decryptText(data.msg)}</div>`;
            msgBox.appendChild(msgCard);
            msgBox.scrollTop = msgBox.scrollHeight;

            let remainingLife = 60000 - (now - msgTimestamp);
            if (remainingLife < 1000) remainingLife = 1000;
            setTimeout(() => { if(msgCard.parentNode) msgCard.parentNode.removeChild(msgCard); }, remainingLife);
        });

        const servers = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

        async function startCall(type) {
            if (!currentRoom) { alert("Join a room first!"); return; }
            document.getElementById('video-container').style.display = 'flex';
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: type === 'video', audio: true });
                document.getElementById('localVideo').srcObject = localStream;
                
                peerConnection = new RTCPeerConnection(servers);
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

                peerConnection.ontrack = event => {
                    document.getElementById('remoteVideo').srcObject = event.streams[0];
                };

                peerConnection.onicecandidate = event => {
                    if (event.candidate) {
                        socket.emit('ice_candidate', { room: currentRoom, candidate: event.candidate });
                    }
                };

                let offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                socket.emit('offer', { room: currentRoom, offer: offer });
            } catch (err) {
                alert("Call permission denied or not supported.");
                endCall();
            }
        }

        socket.on('offer', async (data) => {
            document.getElementById('video-container').style.display = 'flex';
            peerConnection = new RTCPeerConnection(servers);
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                document.getElementById('localVideo').srcObject = localStream;
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
            } catch(e) {}

            peerConnection.ontrack = event => {
                document.getElementById('remoteVideo').srcObject = event.streams[0];
            };

            peerConnection.onicecandidate = event => {
                if (event.candidate) {
                    socket.emit('ice_candidate', { room: currentRoom, candidate: event.candidate });
                }
            };

            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
            let answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            socket.emit('answer', { room: currentRoom, answer: answer });
        });

        socket.on('answer', async (data) => {
            if(peerConnection) {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
            }
        });

        socket.on('ice_candidate', async (data) => {
            if (peerConnection && data.candidate) {
                await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            }
        });

        function endCall() {
            if (localStream) localStream.getTracks().forEach(track => track.stop());
            if (peerConnection) peerConnection.close();
            document.getElementById('video-container').style.display = 'none';
        }
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

@app.route('/manual-unblock-request', methods=['POST'])
def manual_unblock_request():
    data = request.json
    username = data.get('username', '').strip()
    if username:
        UNBLOCK_REQUESTS["manual_" + username] = {"username": username, "status": "Pending"}
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid username"}), 400

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
            if u: BLOCKED_USERS[u] = True
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
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "User not found!"}), 404

@app.route('/instant-block', methods=['POST'])
def instant_block():
    if not session.get('is_admin', False): return jsonify({"status": "unauthorized"}), 403
    u = request.json.get('username')
    BLOCKED_USERS[u] = True
    UNBLOCK_REQUESTS["manual_" + u] = {"username": u, "status": "Pending"}
    return jsonify({"status": "success"})

@app.route('/approve-unblock', methods=['POST'])
def approve_unblock():
    if not session.get('is_admin', False): return jsonify({"status": "unauthorized"}), 403
    data = request.json
    ip = data.get('ip')
    username = data.get('username')
    if ip:
        BLOCKED_IPS.pop(ip, None)
        UNBLOCK_REQUESTS.pop(ip, None)
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
def handle_join(data):
    join_room(data['room'])

@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, to=data['room'])

@socketio.on('offer')
def handle_offer(data):
    emit('offer', data, to=data['room'], include_self=False)

@socketio.on('answer')
def handle_answer(data):
    emit('answer', data, to=data['room'], include_self=False)

@socketio.on('ice_candidate')
def handle_ice(data):
    emit('ice_candidate', data, to=data['room'], include_self=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
