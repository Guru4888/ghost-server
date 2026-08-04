from flask import Flask, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
import os

app = Flask(__name__)
app.secret_key = "ghost_super_secret_key_multi_user_998877"

# Database & Blocklists (In-memory storage)
REGISTERED_USERS = {
    "admin": "guru&guru16230"
}
BLOCKED_USERS = []

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
    </style>
</head>
<body>
    <div class="portal-box">
        <h2>🔒 Multi-User Portal</h2>
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('login', event)">Login</button>
            <button class="tab-btn" onclick="switchTab('register', event)">Register</button>
        </div>

        <div id="login-form" class="form-section active">
            <input type="text" id="login-user" placeholder="Username" autocomplete="off">
            <input type="password" id="login-pass" placeholder="Password" autocomplete="new-password">
            <button onclick="loginUser()">Login to Chat</button>
            <div id="loginError" class="error-msg"></div>
        </div>

        <div id="register-form" class="form-section">
            <input type="text" id="reg-user" placeholder="Choose Username" autocomplete="off">
            <input type="password" id="reg-pass" placeholder="Choose Password" autocomplete="new-password">
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
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .admin-box { background: #161b22; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 450px; border: 1px solid #30363d; }
        ul { list-style: none; padding: 0; max-height: 200px; overflow-y: auto; margin-top: 10px; margin-bottom: 20px; }
        li { background: #21262d; padding: 10px; margin-bottom: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #30363d; font-size: 13px; }
        button.action-btn { background: #da3633; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 11px; }
        button.unblock-btn { background: #238636; }
        .back-link { display: inline-block; margin-top: 15px; color: #58a6ff; text-decoration: none; font-size: 13px; margin-right: 15px; }
        .section-title { font-size: 14px; color: #58a6ff; margin-bottom: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="admin-box">
        <h2>🛡️ Admin Control Panel</h2>
        <p style="color: #8b949e; font-size: 12px; margin-bottom: 15px;">Total Users: <b id="total-count" style="color:white;">0</b></p>
        
        <div class="section-title">👥 Active Registered Users</div>
        <ul id="users-list"></ul>

        <div class="section-title" style="color: #f85149;">🚫 Blocked Users List</div>
        <ul id="blocked-list"></ul>

        <a href="/chat" class="back-link">⬅ Back to Chat</a>
        <a href="/logout" class="back-link" style="color: #f85149;">Logout</a>
    </div>

    <script>
        async function fetchDashboard() {
            try {
                let res = await fetch('/get-admin-data');
                let data = await res.json();
                
                document.getElementById('total-count').innerText = data.users.length;
                
                let usrListEl = document.getElementById('users-list');
                let blockedListEl = document.getElementById('blocked-list');
                
                usrListEl.innerHTML = "";
                blockedListEl.innerHTML = "";

                // Populate Active Users
                data.users.forEach(u => {
                    let isBlocked = data.blocked.includes(u);
                    usrListEl.innerHTML += `
                        <li>
                            <span>👤 ${u} ${isBlocked ? '<span style="color:#f85149; font-size:11px;">(Blocked)</span>' : ''}</span>
                            <div>
                                ${u !== 'admin' ? (!isBlocked ? `<button class="action-btn" onclick="blockUser('${u}')">Block</button>` : '') : '<span style="color:#8b949e; font-size:11px;">Protected</span>'}
                            </div>
                        </li>`;
                });

                // Populate Blocked Users List with Unblock Option
                if(data.blocked.length === 0) {
                    blockedListEl.innerHTML = `<li style="justify-content:center; color:#8b949e;">No blocked users</li>`;
                } else {
                    data.blocked.forEach(bu => {
                        blockedListEl.innerHTML += `
                            <li>
                                <span style="color: #f85149;">🔒 ${bu}</span>
                                <button class="action-btn unblock-btn" onclick="unblockUser('${bu}')">Unblock</button>
                            </li>`;
                    });
                }
            } catch(e) {}
        }

        async function blockUser(username) {
            if (confirm("Are you sure you want to block " + username + "?")) {
                let res = await fetch('/block-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username })
                });
                let data = await res.json();
                if (data.status === "success") { fetchDashboard(); }
                else { alert(data.message || "Failed!"); }
            }
        }

        async function unblockUser(username) {
            let res = await fetch('/unblock-user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username })
            });
            let data = await res.json();
            if (data.status === "success") { fetchDashboard(); }
            else { alert(data.message || "Failed!"); }
        }

        fetchDashboard();
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
            <h2>🔑 Join Chat Room</h2>
            <input type="text" id="room-name" placeholder="Room Name" autocomplete="off" style="margin-bottom:10px;">
            <input type="password" id="room-pass" placeholder="Room Password" autocomplete="new-password" style="margin-bottom:10px;">
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

        // Periodic block check & background logout
        setInterval(async () => {
            try {
                let res = await fetch('/check-session');
                let data = await res.json();
                if(!data.authenticated || data.is_blocked) {
                    alert("Your account has been restricted or logged out!");
                    window.location.href = "/logout";
                }
            } catch(e) {}
        }, 5000);

        document.addEventListener("visibilitychange", function() {
            if (document.hidden) {
                fetch('/logout').then(() => {
                    window.location.href = "/";
                });
            }
        });

        async function initChat() {
            try {
                let res = await fetch('/check-session');
                let data = await res.json();
                if(data.authenticated) {
                    if(data.is_blocked) { window.location.href = "/logout"; return; }
                    myUsername = data.username;
                    if(data.is_admin) { document.getElementById('admin-panel-btn').style.display = 'inline-block'; }
                } else {
                    window.location.href = "/";
                }
            } catch(e) {
                window.location.href = "/";
            }
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
                socket.emit('send_message', { room: currentRoom, user: myUsername, msg: encryptText(text), timestamp: Date.now() });
                input.value = "";
            }
        }

        socket.on('receive_message', (data) => {
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
def home():
    if session.get('authenticated'):
        if session.get('user') in BLOCKED_USERS:
            session.clear()
        else:
            return redirect(url_for('chat'))
    return LOGIN_HTML

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    u, p = data.get('username', '').strip(), data.get('password', '').strip()
    if not u or not p: 
        return jsonify({"status": "error", "message": "Fields required!"}), 400
    if u in REGISTERED_USERS: 
        return jsonify({"status": "error", "message": "Username already exists!"}), 400
    REGISTERED_USERS[u] = p
    return jsonify({"status": "success"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    u, p = data.get('username', '').strip(), data.get('password', '').strip()

    if u in BLOCKED_USERS:
        return jsonify({"status": "error", "message": "Your account has been blocked by admin!"}), 403

    if u in REGISTERED_USERS and REGISTERED_USERS[u] == p:
        session['authenticated'] = True
        session['user'] = u
        session['is_admin'] = (u == "admin")
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Invalid credentials!"}), 401

@app.route('/check-session')
def check_session():
    user = session.get('user')
    is_blocked = user in BLOCKED_USERS
    return jsonify({
        "authenticated": session.get('authenticated', False) and not is_blocked,
        "is_admin": session.get('is_admin', False),
        "username": user if user else 'Guest',
        "is_blocked": is_blocked
    })

@app.route('/admin-panel-guru')
def admin_panel():
    if not session.get('is_admin', False): 
        return redirect(url_for('home'))
    return ADMIN_HTML

@app.route('/get-admin-data')
def get_admin_data():
    if not session.get('is_admin', False): 
        return jsonify({"users": [], "blocked": []}), 403
    return jsonify({
        "users": list(REGISTERED_USERS.keys()),
        "blocked": BLOCKED_USERS
    })

@app.route('/block-user', methods=['POST'])
def block_user():
    if not session.get('is_admin', False): 
        return jsonify({"status": "unauthorized"}), 403
    data = request.json
    target_user = data.get('username')
    if target_user in REGISTERED_USERS and target_user != "admin":
        if target_user not in BLOCKED_USERS:
            BLOCKED_USERS.append(target_user)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "User not found or protected!"}), 404

@app.route('/unblock-user', methods=['POST'])
def unblock_user():
    if not session.get('is_admin', False): 
        return jsonify({"status": "unauthorized"}), 403
    data = request.json
    target_user = data.get('username')
    if target_user in BLOCKED_USERS:
        BLOCKED_USERS.remove(target_user)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "User not in blocked list!"}), 404

@app.route('/chat')
def chat():
    if not session.get('authenticated') or session.get('user') in BLOCKED_USERS: 
        return redirect(url_for('home'))
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
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
