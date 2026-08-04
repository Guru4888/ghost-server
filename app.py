from flask import Flask, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import sqlite3
import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "ghost_super_secret_key_multi_user_998877"

DB_FILE = "database.db"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            sec_question TEXT,
            sec_answer TEXT,
            last_seen TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blocked (
            username TEXT PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            owner TEXT,
            contact_username TEXT,
            PRIMARY KEY (owner, contact_username)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_messages (
            id TEXT PRIMARY KEY,
            room TEXT,
            sender TEXT,
            recipient TEXT,
            data TEXT,
            timestamp REAL
        )
    ''')
    # Settings table for global beep interval (default 30 seconds = 30000 ms)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('beep_interval', '30000')")
    
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, sec_question, sec_answer, last_seen) VALUES (?, ?, ?, ?, ?)", 
                       ("admin", "guru&guru16230", "Master Key", "guru", "Never"))
    conn.commit()
    conn.close()

init_db()

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=120, ping_interval=25)

@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

CALC_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Calculator</title>
    <style>
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; user-select: none; -webkit-tap-highlight-color: transparent; }
        #calc-container { background: #161b22; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 300px; border: 1px solid #30363d; display: block; z-index: 10; position: relative; }
        #calc-screen { width: 100%; height: 50px; background: #010409; border: 1px solid #30363d; color: white; font-size: 1.5rem; text-align: right; padding: 10px; box-sizing: border-box; border-radius: 6px; margin-bottom: 15px; overflow-x: auto; }
        .calc-keys { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .calc-btn { padding: 15px; background: #21262d; color: white; border: 1px solid #30363d; border-radius: 6px; font-size: 1.1rem; font-weight: bold; cursor: pointer; touch-action: manipulation; }
        .calc-btn:active { background: #484f58; }
        .calc-btn.op { background: #1f6feb; }
        .calc-btn.op:active { background: #388bfd; }
        .calc-btn.equal { background: #238636; grid-column: span 2; }
        .calc-btn.equal:active { background: #2ea043; }

        #portal-container { display: none; background: #161b22; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 330px; text-align: center; border: 1px solid #30363d; z-index: 10; position: relative; }
        #portal-container input, #portal-container select { width: 100%; padding: 10px; margin: 6px 0; background: #010409; border: 1px solid #30363d; color: white; border-radius: 6px; box-sizing: border-box; outline: none; }
        .secure-pass { -webkit-text-security: disc; text-security: disc; }
        #portal-container button.portal-submit { width: 100%; padding: 10px; background: #238636; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 8px; }
        #portal-container button.portal-submit:hover { background: #2ea043; }
        .tab-btn { background: #21262d; color: #8b949e; border: 1px solid #30363d; padding: 8px 6px; cursor: pointer; border-radius: 6px; font-weight: bold; width: 31%; font-size: 11px; }
        .tab-btn.active { background: #1f6feb; color: white; border-color: #1f6feb; }
        .tabs { display: flex; justify-content: space-between; margin-bottom: 15px; }
        .form-section { display: none; }
        .form-section.active { display: block; }
        .error-msg { color: #f85149; font-size: 12px; margin-top: 5px; }
        .success-msg { color: #3fb950; font-size: 12px; margin-top: 5px; }
    </style>
</head>
<body>
    <div id="calc-container">
        <div id="calc-screen">0</div>
        <div class="calc-keys">
            <button class="calc-btn" data-val="C">C</button>
            <button class="calc-btn" data-val="(">(</button>
            <button class="calc-btn" data-val=")">)</button>
            <button class="calc-btn op" data-val="/">/</button>
            <button class="calc-btn" data-val="7">7</button>
            <button class="calc-btn" data-val="8">8</button>
            <button class="calc-btn" data-val="9">9</button>
            <button class="calc-btn op" data-val="*">*</button>
            <button class="calc-btn" data-val="4">4</button>
            <button class="calc-btn" data-val="5">5</button>
            <button class="calc-btn" data-val="6">6</button>
            <button class="calc-btn op" data-val="-">-</button>
            <button class="calc-btn" data-val="1">1</button>
            <button class="calc-btn" data-val="2">2</button>
            <button class="calc-btn" data-val="3">3</button>
            <button class="calc-btn op" data-val="+">+</button>
            <button class="calc-btn" data-val="0">0</button>
            <button class="calc-btn" data-val=".">.</button>
            <button class="calc-btn equal" data-val="=">=</button>
        </div>
    </div>

    <div id="portal-container">
        <h2>🔒 Multi-User Portal</h2>
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('login', event)">Login</button>
            <button class="tab-btn" onclick="switchTab('register', event)">Register</button>
            <button class="tab-btn" onclick="switchTab('forgot', event)">Forgot?</button>
        </div>

        <div id="login-form" class="form-section active">
            <input type="text" id="login-user" placeholder="Username" autocomplete="off">
            <input type="text" id="login-pass" placeholder="Password" autocomplete="off" class="secure-pass" readonly onfocus="this.removeAttribute('readonly');">
            <button class="portal-submit" onclick="loginUser()">Login to Portal</button>
            <div id="loginError" class="error-msg"></div>
        </div>

        <div id="register-form" class="form-section">
            <input type="text" id="reg-user" placeholder="Choose Username" autocomplete="off">
            <input type="text" id="reg-pass" placeholder="Choose Password" autocomplete="off" class="secure-pass" readonly onfocus="this.removeAttribute('readonly');">
            <select id="reg-q">
                <option value="What is your pet name?">What is your pet name?</option>
                <option value="What was your first school?">What was your first school?</option>
                <option value="What is your favorite food?">What is your favorite food?</option>
            </select>
            <input type="text" id="reg-ans" placeholder="Security Answer (for reset)" autocomplete="off">
            <button class="portal-submit" onclick="registerUser()">Create Account</button>
            <div id="regMsg" class="error-msg"></div>
        </div>

        <div id="forgot-form" class="form-section">
            <input type="text" id="forgot-user" placeholder="Enter Username" autocomplete="off" onblur="fetchSecQuestion()">
            <div id="q-display" style="color: #58a6ff; font-size: 11px; margin: 4px 0; text-align: left;"></div>
            <input type="text" id="forgot-ans" placeholder="Security Answer" autocomplete="off">
            <input type="text" id="forgot-new-pass" placeholder="New Password" autocomplete="off" class="secure-pass" readonly onfocus="this.removeAttribute('readonly');">
            <button class="portal-submit" onclick="resetPassword()" style="background: #d29922; color: #0d1117;">Verify & Reset</button>
            <div id="forgotMsg" class="error-msg"></div>
        </div>
    </div>

    <script>
        let calcExpr = "";
        document.querySelectorAll('.calc-btn').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                handleCalcInput(this.getAttribute('data-val'));
            });
            button.addEventListener('touchend', function(e) {
                e.preventDefault();
                handleCalcInput(this.getAttribute('data-val'));
            });
        });

        function handleCalcInput(val) {
            if (val === 'C') {
                calcExpr = "";
                document.getElementById("calc-screen").innerText = "0";
            } else if (val === '=') {
                if (calcExpr === "786=" || calcExpr === "786" || calcExpr.trim() === "786") {
                    document.getElementById("calc-container").style.display = "none";
                    document.getElementById("portal-container").style.display = "block";
                    return;
                }
                try {
                    let res = eval(calcExpr);
                    document.getElementById("calc-screen").innerText = res;
                    calcExpr = res.toString();
                } catch (e) {
                    document.getElementById("calc-screen").innerText = "Error";
                    calcExpr = "";
                }
            } else {
                calcExpr += val;
                document.getElementById("calc-screen").innerText = calcExpr;
            }
        }

        function switchTab(tab, event) {
            document.querySelectorAll('.form-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            if(tab === 'login') {
                document.getElementById('login-form').classList.add('active');
                event.target.classList.add('active');
            } else if(tab === 'register') {
                document.getElementById('register-form').classList.add('active');
                event.target.classList.add('active');
            } else {
                document.getElementById('forgot-form').classList.add('active');
                event.target.classList.add('active');
            }
        }

        async function fetchSecQuestion() {
            const user = document.getElementById("forgot-user").value.trim();
            if(!user) return;
            let res = await fetch('/get-question?username=' + encodeURIComponent(user));
            let data = await res.json();
            if(res.ok) { document.getElementById("q-display").innerText = "Question: " + data.question; }
            else { document.getElementById("q-display").innerText = "User not found!"; }
        }

        async function loginUser() {
            let response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: document.getElementById("login-user").value.trim(), password: document.getElementById("login-pass").value.trim() })
            });
            let result = await response.json();
            if (response.ok && result.status === "success") { window.location.href = "/chat"; }
            else { document.getElementById("loginError").innerText = result.message || "Login failed!"; }
        }

        async function registerUser() {
            let response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: document.getElementById("reg-user").value.trim(), password: document.getElementById("reg-pass").value.trim(), question: document.getElementById("reg-q").value, answer: document.getElementById("reg-ans").value.trim() })
            });
            let result = await response.json();
            let msgEl = document.getElementById("regMsg");
            if (response.ok && result.status === "success") {
                msgEl.className = "success-msg"; msgEl.innerText = "Account created! You can now login.";
                setTimeout(() => switchTab('login', {target: document.querySelectorAll('.tab-btn')[0]}), 1500);
            } else {
                msgEl.className = "error-msg"; msgEl.innerText = result.message || "Registration failed!";
            }
        }

        async function resetPassword() {
            let response = await fetch('/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: document.getElementById("forgot-user").value.trim(), answer: document.getElementById("forgot-ans").value.trim(), new_password: document.getElementById("forgot-new-pass").value.trim() })
            });
            let result = await response.json();
            let msgEl = document.getElementById("forgotMsg");
            if (response.ok && result.status === "success") {
                msgEl.className = "success-msg"; msgEl.innerText = "Password updated! You can now login.";
                setTimeout(() => switchTab('login', {target: document.querySelectorAll('.tab-btn')[0]}), 1500);
            } else {
                msgEl.className = "error-msg"; msgEl.innerText = result.message || "Reset failed!";
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
        .admin-box { background: #161b22; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 480px; border: 1px solid #30363d; max-height: 90vh; overflow-y: auto; }
        ul { list-style: none; padding: 0; max-height: 130px; overflow-y: auto; margin-top: 5px; margin-bottom: 15px; }
        li { background: #21262d; padding: 10px; margin-bottom: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #30363d; font-size: 13px; }
        .btn-group { display: flex; gap: 5px; }
        button.action-btn { background: #da3633; color: white; border: none; padding: 5px 8px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 11px; }
        button.block-btn { background: #d29922; color: #0d1117; }
        button.unblock-btn { background: #238636; }
        button.monitor-btn { background: #1f6feb; }
        .back-link { display: inline-block; margin-top: 15px; color: #58a6ff; text-decoration: none; font-size: 13px; margin-right: 15px; }
        .section-title { font-size: 13px; color: #58a6ff; margin-bottom: 5px; font-weight: bold; }
        #monitor-section { margin-top: 10px; background: #010409; border: 1px solid #30363d; border-radius: 6px; padding: 10px; display: none; }
        #monitor-messages { height: 120px; overflow-y: auto; background: #0d1117; padding: 8px; border-radius: 4px; font-size: 12px; margin-top: 8px; }
    </style>
</head>
<body>
    <div class="admin-box">
        <h2>🛡️ Admin Control Panel</h2>
        <p style="color: #8b949e; font-size: 12px; margin-bottom: 15px;">Total Users: <b id="total-count" style="color:white;">0</b></p>
        
        <!-- Beep Timing Control Section -->
        <div class="section-title" style="color: #d29922;">⏰ Unread Alarm / Beep Interval Settings</div>
        <div style="background: #010409; border: 1px solid #30363d; border-radius: 6px; padding: 10px; margin-bottom: 15px;">
            <div style="font-size: 11px; color: #8b949e; margin-bottom: 6px;">Set alarm interval for all users (in seconds):</div>
            <div style="display: flex; gap: 5px;">
                <input type="number" id="beep-time-input" placeholder="e.g. 30" style="flex:1; padding:6px; background:#161b22; border:1px solid #30363d; color:white; border-radius:4px; font-size:12px;" autocomplete="off">
                <button class="action-btn" style="background:#238636;" onclick="updateBeepTime()">Update All</button>
                <button class="action-btn" style="background:#da3633;" onclick="turnOffGlobalAlarm()">Turn Off All Alarms</button>
            </div>
            <div id="beep-msg" style="font-size: 11px; margin-top: 4px; color: #3fb950;"></div>
        </div>

        <div class="section-title">👥 Active Registered Users</div>
        <ul id="users-list"></ul>

        <div class="section-title" style="color: #f85149;">🚫 Blocked Users List</div>
        <ul id="blocked-list"></ul>

        <div class="section-title" style="color: #58a6ff;">📡 Active Chat Rooms (Live Monitor)</div>
        <ul id="active-rooms-list">
            <li style="justify-content:center; color:#8b949e;">No active rooms right now</li>
        </ul>

        <div class="section-title" style="color: #58a6ff;">🔍 Spy / Monitor Room Manual</div>
        <div style="display: flex; gap: 5px; margin-top: 5px;">
            <input type="text" id="spy-room-input" placeholder="Enter Room Name to Spy" style="flex:1; padding:6px; background:#010409; border:1px solid #30363d; color:white; border-radius:4px; font-size:12px;" autocomplete="off">
            <button class="action-btn monitor-btn" onclick="startSpying()">Read Chats</button>
        </div>

        <div id="monitor-section">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span id="spy-room-title" style="font-weight:bold; color:#3fb950; font-size:12px;">Room: </span>
                <button onclick="stopSpying()" style="background:#da3633; border:none; color:white; padding:2px 6px; border-radius:3px; font-size:10px; cursor:pointer;">Close</button>
            </div>
            <div id="monitor-messages"></div>
        </div>

        <div style="margin-top: 15px;">
            <a href="/chat" class="back-link">⬅ Back to Lobby</a>
            <a href="/logout" class="back-link" style="color: #f85149;">Logout</a>
        </div>
    </div>

    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io({ transports: ['polling', 'websocket'] });
        let spyingRoom = null;

        async function fetchDashboard() {
            try {
                let res = await fetch('/get-admin-data');
                let data = await res.json();
                document.getElementById('total-count').innerText = data.users.length;
                document.getElementById('beep-time-input').value = data.beep_interval / 1000; // ms to seconds

                let usrListEl = document.getElementById('users-list');
                let blockedListEl = document.getElementById('blocked-list');
                usrListEl.innerHTML = ""; blockedListEl.innerHTML = "";

                data.users.forEach(u => {
                    let isBlocked = data.blocked.includes(u);
                    usrListEl.innerHTML += `
                        <li>
                            <span>👤 ${u} ${isBlocked ? '<span style="color:#f85149; font-size:11px;">(Blocked)</span>' : ''}</span>
                            <div class="btn-group">
                                ${u !== 'admin' ? `
                                    ${!isBlocked ? `<button class="action-btn block-btn" onclick="blockUser('${u}')">Block</button>` : ''}
                                    <button class="action-btn" onclick="deleteUser('${u}')">Delete</button>
                                ` : '<span style="color:#8b949e; font-size:11px;">Protected</span>'}
                            </div>
                        </li>`;
                });

                if(data.blocked.length === 0) { blockedListEl.innerHTML = `<li style="justify-content:center; color:#8b949e;">No blocked users</li>`; }
                else {
                    data.blocked.forEach(bu => {
                        blockedListEl.innerHTML += `
                            <li>
                                <span style="color: #f85149;">🔒 ${bu}</span>
                                <div class="btn-group">
                                    <button class="action-btn unblock-btn" onclick="unblockUser('${bu}')">Unblock</button>
                                    <button class="action-btn" onclick="deleteUser('${bu}')">Delete</button>
                                </div>
                            </li>`;
                    });
                }
            } catch(e) {}
        }

        async function updateBeepTime() {
            let secs = document.getElementById('beep-time-input').value.trim();
            if(!secs || isNaN(secs) || secs <= 0) { alert("Enter valid seconds!"); return; }
            let res = await fetch('/admin-update-beep', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ seconds: parseInt(secs) })
            });
            let data = await res.json();
            if(data.status === 'success') {
                document.getElementById('beep-msg').innerText = "Beep timing updated successfully for all users!";
                setTimeout(() => document.getElementById('beep-msg').innerText = "", 3000);
            }
        }

        async function turnOffGlobalAlarm() {
            let res = await fetch('/admin-update-beep', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ seconds: 0 }) // 0 means turned off
            });
            let data = await res.json();
            if(data.status === 'success') {
                document.getElementById('beep-msg').innerText = "All Alarms Turned Off Globally!";
                setTimeout(() => document.getElementById('beep-msg').innerText = "", 3000);
            }
        }

        async function blockUser(username) {
            if (confirm("Are you sure you want to block " + username + "?")) {
                let res = await fetch('/block-user', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: username }) });
                if ((await res.json()).status === "success") { fetchDashboard(); }
            }
        }

        async function unblockUser(username) {
            let res = await fetch('/unblock-user', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: username }) });
            if ((await res.json()).status === "success") { fetchDashboard(); }
        }

        async function deleteUser(username) {
            if (confirm("Are you sure you want to permanently delete " + username + "?")) {
                let res = await fetch('/delete-user', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: username }) });
                if ((await res.json()).status === "success") { fetchDashboard(); }
            }
        }

        function startSpying() {
            const roomName = document.getElementById('spy-room-input').value.trim();
            if(!roomName) { alert("Enter room name first!"); return; }
            if(spyingRoom) { socket.emit('admin_leave_spy', { room: spyingRoom }); }
            spyingRoom = roomName;
            document.getElementById('monitor-section').style.display = 'block';
            document.getElementById('spy-room-title').innerText = "Room: " + roomName;
            document.getElementById('monitor-messages').innerHTML = "";
            socket.emit('admin_join_spy', { room: roomName });
        }

        function stopSpying() {
            if(spyingRoom) { socket.emit('admin_leave_spy', { room: spyingRoom }); }
            spyingRoom = null;
            document.getElementById('monitor-section').style.display = 'none';
        }

        function spySpecificRoom(roomName) {
            document.getElementById('spy-room-input').value = roomName;
            startSpying();
        }

        socket.on('admin_rooms_list', (rooms) => {
            let listEl = document.getElementById('active-rooms-list');
            if(rooms.length === 0) { listEl.innerHTML = `<li style="justify-content:center; color:#8b949e;">No active rooms right now</li>`; return; }
            listEl.innerHTML = "";
            rooms.forEach(r => {
                listEl.innerHTML += `<li><span>👻 ${r.room} <b style="color:#3fb950;">(${r.users} users)</b></span><button class="action-btn monitor-btn" onclick="spySpecificRoom('${r.room}')">Read Chats</button></li>`;
            });
        });

        socket.on('admin_spy_receive', (data) => {
            let box = document.getElementById('monitor-messages');
            box.innerHTML += `<div><b>${data.user}:</b> ${data.msg}</div>`;
            box.scrollTop = box.scrollHeight;
        });

        setInterval(() => { socket.emit('get_admin_rooms'); }, 3000);
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
    <title>Ghost Secret Tunnel - Lobby</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { background-color: #0d1117; color: #ffffff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; user-select: none; }
        #security-warning { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 9999; justify-content: center; align-items: center; color: #f85149; font-size: 1.5rem; font-weight: bold; text-align: center; padding: 20px; }
        
        #room-lobby { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #0d1117; z-index: 999; display: flex; justify-content: center; align-items: center; }
        .lobby-box { background: #161b22; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 380px; text-align: center; border: 1px solid #30363d; max-height: 90vh; overflow-y: auto; }
        .lobby-box input { width: 100%; padding: 10px; margin: 6px 0; background: #010409; border: 1px solid #30363d; color: white; border-radius: 6px; box-sizing: border-box; outline: none; }
        .secure-pass { -webkit-text-security: disc; text-security: disc; }
        .lobby-box button { width: 100%; padding: 10px; background: #1f6feb; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 8px; }
        .lobby-box button:hover { background: #388bfd; }

        .contacts-section { margin-top: 15px; text-align: left; border-top: 1px solid #30363d; padding-top: 10px; }
        .contacts-section h4 { font-size: 12px; color: #8b949e; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
        .contact-item { background: #21262d; padding: 8px 10px; margin-bottom: 6px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #30363d; font-size: 13px; }
        .contact-actions { display: flex; gap: 4px; }
        .btn-mini { padding: 4px 8px; border-radius: 4px; border: none; font-size: 11px; font-weight: bold; cursor: pointer; color: white; }
        .btn-chat-contact { background: #238636; }
        .btn-del-contact { background: #da3633; }

        .rooms-history { margin-top: 12px; text-align: left; border-top: 1px solid #30363d; padding-top: 10px; }
        .rooms-history h4 { font-size: 12px; color: #8b949e; margin-bottom: 6px; }
        .room-item { background: #21262d; padding: 8px 12px; margin-bottom: 6px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #30363d; font-size: 13px; cursor: pointer; }
        .room-item:hover { border-color: #58a6ff; }

        #chat-screen { display: none; width: 95%; max-width: 500px; height: 85vh; background: #161b22; border-radius: 12px; flex-direction: column; border: 1px solid #30363d; overflow: hidden; }
        .top-bar { background: #21262d; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; }
        .top-bar h3 { margin: 0; font-size: 0.9rem; color: #58a6ff; }
        .status-text { font-size: 0.65rem; color: #8b949e; display: block; }
        .call-btns { display: flex; gap: 3px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
        .btn-call { padding: 4px 6px; border-radius: 5px; border: none; font-size: 0.65rem; font-weight: bold; cursor: pointer; color: white; }
        .btn-audio { background-color: #1f6feb; }
        .btn-video { background-color: #8957e5; }
        .btn-e2ee { background-color: #30363d; color: #8b949e; border: 1px solid #484f58; }
        .btn-e2ee.active { background-color: #238636; color: white; border-color: #2ea043; }
        .btn-alarm-off { background-color: #da3633; color: white; font-size: 0.65rem; display: none; }
        .btn-admin { background-color: #d29922; display: none; color: #0d1117; }
        .btn-logout-manual { background-color: #da3633; color: white; }
        
        #messages { flex-grow: 1; overflow-y: auto; padding: 15px; background: #0d1117; display: flex; flex-direction: column; gap: 12px; }
        .msg-card { padding: 6px 10px; max-width: 75%; word-wrap: break-word; font-size: 0.9rem; position: relative; background: #21262d; border-radius: 8px; border: 1px solid #30363d; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        .my-msg { align-self: flex-end; background: #1f382b; }
        .other-msg { align-self: flex-start; }
        .user-id { font-size: 0.7em; color: #8b949e; margin-bottom: 2px; display: block; font-weight: bold; }
        .msg-footer { display: flex; justify-content: flex-end; align-items: center; gap: 6px; font-size: 0.65rem; margin-top: 2px; color: #cbd5e1; }
        .ticks { font-size: 0.85rem; font-family: monospace; color: #8b949e; }
        .ticks.seen { color: #53bdeb !important; }
        
        .input-box { display: flex; padding: 10px; background: #21262d; gap: 6px; border-top: 1px solid #30363d; flex-direction: column; }
        .input-row { display: flex; gap: 6px; width: 100%; align-items: center; }
        input[type="text"] { width: 100%; padding: 10px; background: #010409; border: 1px solid #30363d; color: white; border-radius: 6px; outline: none; user-select: text; }
        button.btn-send { padding: 10px 14px; background: #238636; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .btn-attach { background: #30363d; color: #58a6ff; border: 1px solid #484f58; padding: 10px 12px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 1rem; }
        #typing-indicator { font-size: 0.75rem; color: #3fb950; font-style: italic; height: 12px; }
        
        .chat-media { max-width: 100%; max-height: 200px; border-radius: 6px; margin-top: 4px; display: block; cursor: pointer; }
        
        #video-container { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.98); z-index: 1000; flex-direction: column; }
        .video-box { position: relative; width: 100%; height: 100%; display: flex; flex-direction: column; }
        .video-header-bar { display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; background: #161b22; border-bottom: 1px solid #30363d; z-index: 10; }
        .video-split-container { display: flex; flex-direction: column; width: 100%; flex-grow: 1; height: calc(100vh - 60px); }
        .video-half { width: 100%; height: 50%; position: relative; background: black; display: flex; justify-content: center; align-items: center; overflow: hidden; border-bottom: 1px solid #30363d; }
        video { width: 100%; height: 100%; object-fit: cover; }
        .video-label { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.6); color: white; padding: 3px 8px; font-size: 0.75rem; border-radius: 4px; z-index: 5; font-weight: bold; }
        .call-control-bar { display: flex; gap: 10px; padding: 10px 15px; background: #161b22; justify-content: center; align-items: center; border-top: 1px solid #30363d; }
    </style>
</head>
<body>
    <div id="security-warning">⚠️ Screen Recording / Capture Detected!<br>Access Restricted for Security.</div>

    <div id="room-lobby">
        <div class="lobby-box">
            <h3>🌐 Ghost Contacts & Rooms</h3>
            <p style="color: #8b949e; font-size: 11px; margin-bottom: 8px;">Add friends or join custom rooms.</p>
            
            <div style="display: flex; gap: 5px; margin-bottom: 6px;">
                <input type="text" id="add-contact-input" placeholder="Enter Friend Username" autocomplete="off" style="margin:0;">
                <button onclick="addContact()" style="width: auto; margin:0; background:#238636; padding: 0 12px;">Add</button>
            </div>
            <div id="contact-error" style="color: #f85149; font-size: 11px; margin-bottom: 6px; text-align: left;"></div>

            <div class="contacts-section">
                <h4>👥 My Contacts <span id="contact-count" style="color:#58a6ff;">(0)</span></h4>
                <div id="contacts-list" style="max-height: 120px; overflow-y: auto;">
                    <div style="color: #8b949e; font-size: 11px; text-align: center; padding: 5px;">No contacts added yet</div>
                </div>
            </div>

            <div style="margin: 12px 0 6px 0; border-top: 1px solid #30363d; padding-top: 8px;">
                <input type="text" id="room-name-input" placeholder="Manual Room Name" autocomplete="off">
                <input type="text" id="room-pass-input" placeholder="Room Password" autocomplete="off" class="secure-pass" readonly onfocus="this.removeAttribute('readonly');">
                <button id="gate-btn" onclick="joinProtectedRoom()">Join / Create Manual Room</button>
                <div id="gate-error" style="color: #f85149; font-size: 12px; margin-top: 4px;"></div>
            </div>

            <div class="rooms-history">
                <h4>📂 Recent Rooms</h4>
                <div id="joined-rooms-list" style="max-height: 100px; overflow-y: auto;">
                    <div style="color: #8b949e; font-size: 11px; text-align: center; padding: 3px;">No rooms joined yet</div>
                </div>
            </div>
            <button onclick="instantLogout()" style="background: #da3633; margin-top: 12px;">🚪 Logout Portal</button>
        </div>
    </div>

    <!-- Call Screen -->
    <div id="video-container">
        <div class="video-box">
            <div class="video-header-bar">
                <span id="call-status-title" style="color: #58a6ff; font-weight: bold; font-size: 0.9rem;">Secure Call Connected</span>
                <div style="display:flex; gap:5px;">
                    <button class="btn-call" id="mute-mic-btn" style="background:#21262d; border:1px solid #30363d; padding:6px 10px;" onclick="toggleMicrophone()">🎙️ Mute Mic</button>
                    <button class="btn-call" style="background:#1f6feb; padding:6px 10px;" onclick="switchCamera()">🔄 Camera</button>
                </div>
            </div>
            <div class="video-split-container">
                <div class="video-half" id="local-video-pane">
                    <span class="video-label">👤 You (My Camera)</span>
                    <video id="localVideo" autoplay playsinline muted></video>
                </div>
                <div class="video-half" id="remote-video-pane">
                    <span class="video-label">👥 Partner</span>
                    <video id="remoteVideo" autoplay playsinline></video>
                </div>
            </div>
            <div class="call-control-bar">
                <button class="btn-send" style="background:#da3633; width:100%;" onclick="endCall()">🔴 End Call</button>
            </div>
        </div>
    </div>

    <div id="chat-screen">
        <div class="top-bar">
            <div>
                <h3 id="room-title">👻 Ghost Tunnel</h3>
                <span id="display-status" class="status-text">● Secure Room Connected</span>
            </div>
            <div class="call-btns">
                <button id="alarm-off-btn" class="btn-call btn-alarm-off" onclick="userTurnOffAlarm()">🔕 Mute Alarm</button>
                <button id="e2ee-btn" class="btn-call btn-e2ee" onclick="toggleE2EE()">🔐</button>
                <button class="btn-call btn-audio" onclick="startCall('audio')">📞 Audio</button>
                <button class="btn-call btn-video" onclick="startCall('video')">📹 Video</button>
                <button id="admin-panel-btn" class="btn-call btn-admin" onclick="window.location.href='/admin-panel-guru'">🛡️</button>
                <button class="btn-call btn-logout-manual" onclick="returnToLobby()">🔙 Lobby</button>
            </div>
        </div>
        
        <div id="messages"></div>
        
        <div class="input-box">
            <div id="typing-indicator"></div>
            <div class="input-row">
                <input type="file" id="file-input" style="display:none;" onchange="uploadAndSendFile()">
                <button class="btn-attach" onclick="document.getElementById('file-input').click()" title="Attach Photo or File">📎</button>
                <input type="text" id="msg-input" placeholder="Type a message..." autocomplete="off" oninput="notifyTyping()" onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="btn-send" onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('keyup', (e) => { if (e.key === 'PrintScreen') { triggerSecurityAlert(); } });
        document.addEventListener("visibilitychange", async () => {
            if (document.hidden) {
                try { await fetch('/logout', { method: 'GET', cache: "no-store" }); } catch(e) {}
                wipeAndExit();
            }
        });

        async function instantLogout() {
            try { await fetch('/logout', { method: 'GET', cache: "no-store" }); } catch(e) {}
            wipeAndExit();
        }

        function wipeAndExit() {
            document.body.innerHTML = "<div style='background:#0d1117; color:#f85149; display:flex; justify-content:center; align-items:center; height:100vh; font-family:Arial; font-size:1.5rem; font-weight:bold; text-align:center;'>⚠️ Page Not Available / Session Expired</div>";
            window.location.href = "/";
        }

        function triggerSecurityAlert() { document.getElementById('security-warning').style.display = 'flex'; }

        const socket = io({ transports: ['polling', 'websocket'], reconnection: true, reconnectionAttempts: Infinity, timeout: 30000 });

        let currentRoom = "";
        let roomPassword = "";
        let myUsername = "User";
        let typingTimeout = null;
        let lastSender = null;
        let isE2EEActive = localStorage.getItem('ghost_e2ee') === 'true';
        let currentFacingMode = 'user';
        let isMicMuted = false;
        
        let unreadAlertInterval = null;
        let currentGlobalBeepInterval = 30000; // Default 30s

        updateE2EEButtonUI();
        renderJoinedRooms();

        // Server se current beep interval fetch karo
        async function fetchInitialSettings() {
            try {
                let res = await fetch('/get-settings');
                let data = await res.json();
                if(res.ok) { currentGlobalBeepInterval = data.beep_interval; }
            } catch(e){}
        }
        fetchInitialSettings();

        // Secret Alarm Sound Generator
        function playSecretAlarmSound() {
            if (currentGlobalBeepInterval <= 0) return; // Agar admin ne band kiya hai toh beep nahi bajegi
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();

                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
                gainNode.gain.setValueAtTime(0.15, audioCtx.currentTime);

                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);

                oscillator.start();
                oscillator.stop(audioCtx.currentTime + 0.3);
            } catch (e) {
                console.log("Audio alert failed");
            }
        }

        socket.on('trigger_unread_alarm', () => {
            if (currentGlobalBeepInterval <= 0) return; // Agar 0 hai toh alarm trigger hi nahi hoga
            if (!unreadAlertInterval) {
                unreadAlertInterval = setInterval(() => {
                    playSecretAlarmSound();
                }, currentGlobalBeepInterval);
                document.getElementById('alarm-off-btn').style.display = 'inline-block';
            }
        });

        socket.on('stop_unread_alarm', () => {
            stopUserAlarmLocal();
        });

        // User khud apne end se alarm band kar sakta hai
        function userTurnOffAlarm() {
            stopUserAlarmLocal();
        }

        function stopUserAlarmLocal() {
            if (unreadAlertInterval) {
                clearInterval(unreadAlertInterval);
                unreadAlertInterval = null;
            }
            document.getElementById('alarm-off-btn').style.display = 'none';
        }

        // Admin jab timing change karega ya off karega toh sabke liye update ho jayega
        socket.on('global_beep_update', (data) => {
            currentGlobalBeepInterval = data.beep_interval;
            if (currentGlobalBeepInterval <= 0) {
                stopUserAlarmLocal(); // Agar admin ne poori tarah off kar diya
            } else if (unreadAlertInterval) {
                // Agar alarm chal raha hai toh naye interval ke sath restart karo
                clearInterval(unreadAlertInterval);
                unreadAlertInterval = setInterval(() => {
                    playSecretAlarmSound();
                }, currentGlobalBeepInterval);
            }
        });

        async function initChat() {
            try {
                let res = await fetch('/check-session', {cache: "no-store"});
                let data = await res.json();
                if(data.authenticated) {
                    if(data.is_blocked || data.is_deleted) { instantLogout(); return; }
                    myUsername = data.username;
                    if(data.is_admin) { document.getElementById('admin-panel-btn').style.display = 'inline-block'; }
                    fetchContacts();
                } else { window.location.href = "/"; }
            } catch(e) { window.location.href = "/"; }
        }
        initChat();

        async function fetchContacts() {
            try {
                let res = await fetch('/get-contacts');
                let data = await res.json();
                if(res.ok) { renderContactsList(data.contacts); }
            } catch(e) {}
        }

        function renderContactsList(contacts) {
            let listEl = document.getElementById('contacts-list');
            document.getElementById('contact-count').innerText = `(${contacts.length})`;
            if(contacts.length === 0) {
                listEl.innerHTML = `<div style="color: #8b949e; font-size: 11px; text-align: center; padding: 5px;">No contacts added yet</div>`;
                return;
            }
            listEl.innerHTML = "";
            contacts.forEach(c => {
                listEl.innerHTML += `
                    <div class="contact-item">
                        <span>👤 ${c}</span>
                        <div class="contact-actions">
                            <button class="btn-mini btn-chat-contact" onclick="startDirectChat('${c}')">Chat</button>
                            <button class="btn-mini btn-del-contact" onclick="removeContact('${c}')">✕</button>
                        </div>
                    </div>
                `;
            });
        }

        async function addContact() {
            const input = document.getElementById('add-contact-input');
            const errEl = document.getElementById('contact-error');
            const targetUser = input.value.trim();
            errEl.innerText = "";
            if(!targetUser) { errEl.innerText = "Enter a username!"; return; }

            let res = await fetch('/add-contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ contact: targetUser })
            });
            let result = await res.json();
            if(res.ok && result.status === 'success') {
                input.value = "";
                fetchContacts();
            } else {
                errEl.innerText = result.message || "Failed to add contact";
            }
        }

        async function removeContact(targetUser) {
            let res = await fetch('/remove-contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ contact: targetUser })
            });
            if(res.ok) { fetchContacts(); }
        }

        function startDirectChat(friendName) {
            let users = [myUsername, friendName].sort();
            currentRoom = "private_" + users[0] + "_" + users[1];
            roomPassword = "ghost_secure_direct_pass_999";
            socket.emit('verify_and_join', { room: currentRoom, password: roomPassword, user: myUsername });
        }

        function saveRoomToHistory(name) {
            if(name.startsWith("private_")) return;
            let history = JSON.parse(localStorage.getItem('ghost_rooms_history') || '[]');
            if (!history.includes(name)) { history.push(name); localStorage.setItem('ghost_rooms_history', JSON.stringify(history)); }
            renderJoinedRooms();
        }

        function renderJoinedRooms() {
            let historyListEl = document.getElementById('joined-rooms-list');
            let history = JSON.parse(localStorage.getItem('ghost_rooms_history') || '[]');
            if(history.length === 0) { historyListEl.innerHTML = `<div style="color: #8b949e; font-size: 11px; text-align: center; padding: 3px;">No rooms joined yet</div>`; return; }
            historyListEl.innerHTML = "";
            history.forEach(rName => {
                historyListEl.innerHTML += `<div class="room-item" onclick="quickSelectRoom('${rName}')"><span>👻 ${rName}</span><span style="font-size:10px; color:#58a6ff;">Select ➔</span></div>`;
            });
        }

        function quickSelectRoom(rName) {
            document.getElementById("room-name-input").value = rName;
            document.getElementById("room-pass-input").value = "";
            document.getElementById("room-pass-input").focus();
        }

        function joinProtectedRoom() {
            const rName = document.getElementById("room-name-input").value.trim();
            const rPass = document.getElementById("room-pass-input").value.trim();
            const errEl = document.getElementById("gate-error");
            const btnEl = document.getElementById("gate-btn");
            if(!rName || !rPass) { errEl.innerText = "Please enter room name and password!"; return; }
            errEl.innerText = ""; btnEl.innerText = "Connecting..."; btnEl.disabled = true;
            currentRoom = rName; roomPassword = rPass;
            socket.emit('verify_and_join', { room: currentRoom, password: roomPassword, user: myUsername });
            setTimeout(() => { if(btnEl.innerText === "Connecting...") { btnEl.innerText = "Join / Create Manual Room"; btnEl.disabled = false; } }, 6000);
        }

        socket.on('room_join_response', (data) => {
            const btnEl = document.getElementById("gate-btn");
            if(btnEl) { btnEl.innerText = "Join / Create Manual Room"; btnEl.disabled = false; }
            if(data.status === "success") {
                saveRoomToHistory(currentRoom);
                document.getElementById('room-lobby').style.display = 'none';
                document.getElementById('chat-screen').style.display = 'flex';
                let displayTitle = currentRoom.startsWith("private_") ? "Direct Secure Chat" : currentRoom;
                document.getElementById('room-title').innerText = "👻 " + displayTitle + ` (${data.active_users} online)`;
                
                socket.emit('stop_my_unread_alarm', { room: currentRoom, user: myUsername });
                socket.emit('fetch_pending_messages', { room: currentRoom, user: myUsername });
            } else {
                alert(data.message || "Incorrect room password!");
                document.getElementById('gate-error').innerText = data.message || "Incorrect room password!";
            }
        });

        socket.on('receive_pending_batch', (data) => {
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msgData => {
                    appendMessageToScreen(msgData, false);
                });
                socket.emit('ack_pending_received', { room: currentRoom, user: myUsername });
            }
        });

        function returnToLobby() {
            socket.emit('leave_current_room', { room: currentRoom, user: myUsername });
            currentRoom = ""; roomPassword = "";
            document.getElementById('chat-screen').style.display = 'none';
            document.getElementById('room-lobby').style.display = 'flex';
            document.getElementById('messages').innerHTML = "";
            renderJoinedRooms();
            fetchContacts();
        }

        socket.on('room_users_update', (data) => {
            if(data.room === currentRoom) {
                let displayTitle = currentRoom.startsWith("private_") ? "Direct Secure Chat" : currentRoom;
                document.getElementById('room-title').innerText = "👻 " + displayTitle + ` (${data.active_users} online)`;
                document.getElementById('display-status').innerText = `● Connected (${data.users.join(', ')})`;
            }
        });

        function toggleE2EE() {
            isE2EEActive = !isE2EEActive;
            localStorage.setItem('ghost_e2ee', isE2EEActive);
            updateE2EEButtonUI();
        }

        function updateE2EEButtonUI() {
            const btn = document.getElementById('e2ee-btn');
            if (isE2EEActive) { btn.className = "btn-call btn-e2ee active"; btn.innerText = "🔐ON"; } 
            else { btn.className = "btn-call btn-e2ee"; btn.innerText = "🔐OFF"; }
        }

        function encryptText(text) { return !isE2EEActive ? text : "ENC[" + btoa(text) + "]"; }
        function decryptText(text) {
            if (text.startsWith("ENC[")) {
                try { return "🔒 " + atob(text.substring(4, text.length - 1)); } catch(e) { return text; }
            }
            return text;
        }

        function notifyTyping() {
            socket.emit('typing', { room: currentRoom, user: myUsername });
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => { socket.emit('stop_typing', { room: currentRoom, user: myUsername }); }, 1000);
        }

        function sendMessage() {
            const input = document.getElementById('msg-input');
            const text = input.value.trim();
            if (text !== "") {
                socket.emit('stop_typing', { room: currentRoom, user: myUsername });
                const msgId = 'msg_' + Date.now() + "_" + Math.random().toString(36).substring(2, 7);
                const messageData = { 
                    id: msgId, 
                    room: currentRoom, 
                    sender: myUsername, 
                    user: myUsername, 
                    type: 'text', 
                    content: encryptText(text), 
                    timestamp: Date.now() 
                };
                appendMessageToScreen(messageData, true);
                socket.emit('send_message', { room: currentRoom, password: roomPassword, data: messageData });
                input.value = "";
            }
        }

        async function uploadAndSendFile() {
            const fileInput = document.getElementById('file-input');
            if (fileInput.files.length === 0) return;
            const file = fileInput.files[0];
            let formData = new FormData();
            formData.append('file', file);
            
            try {
                let res = await fetch('/upload-attachment', { method: 'POST', body: formData });
                let result = await res.json();
                if(res.ok && result.status === 'success') {
                    const msgId = 'msg_' + Date.now() + "_" + Math.random().toString(36).substring(2, 7);
                    const messageData = { 
                        id: msgId, 
                        room: currentRoom, 
                        sender: myUsername,
                        user: myUsername, 
                        type: file.type.startsWith('image/') ? 'image' : 'file', 
                        content: result.file_url, 
                        filename: file.name,
                        timestamp: Date.now() 
                    };
                    appendMessageToScreen(messageData, true);
                    socket.emit('send_message', { room: currentRoom, password: roomPassword, data: messageData });
                } else {
                    alert(result.message || "Upload failed!");
                }
            } catch(e) { alert("File upload error!"); }
            fileInput.value = "";
        }

        function manualDeleteMessage(msgId) {
            socket.emit('delete_message_for_everyone', { room: currentRoom, password: roomPassword, id: msgId });
        }

        socket.on('remove_message_card', (data) => {
            let card = document.getElementById('card_' + data.id);
            if(card) {
                card.style.transition = "opacity 0.3s ease";
                card.style.opacity = "0";
                setTimeout(() => card.remove(), 300);
            }
        });

        const activeTimers = {};

        function scheduleAutoDelete(msgId) {
            if (activeTimers[msgId]) return;
            activeTimers[msgId] = setTimeout(() => {
                let card = document.getElementById('card_' + msgId);
                if(card) {
                    card.style.transition = "opacity 0.5s ease";
                    card.style.opacity = "0";
                    setTimeout(() => card.remove(), 500);
                }
            }, 60000);
        }

        function appendMessageToScreen(data, isMine) {
            const msgBox = document.getElementById('messages');
            if(document.getElementById('card_' + data.id)) return;

            const msgCard = document.createElement('div');
            msgCard.id = 'card_' + data.id;
            msgCard.className = `msg-card ${isMine ? 'my-msg' : 'other-msg'}`;
            
            let showUserHeading = (data.user !== lastSender);
            lastSender = data.user;
            let userHTML = showUserHeading ? `<span class="user-id">${data.user}</span>` : '';
            let ticksHTML = isMine ? `<span id="tick_${data.id}" class="ticks">✓</span>` : '';
            let deleteBtnHTML = isMine ? `<button onclick="manualDeleteMessage('${data.id}')" style="background:none; border:none; color:#f85149; font-size:10px; cursor:pointer;" title="Delete for Everyone">🗑️ Delete</button>` : '';

            let contentHTML = "";
            if (data.type === 'image') {
                contentHTML = `<a href="${data.content}" target="_blank"><img src="${data.content}" class="chat-media"></a>`;
            } else if (data.type === 'file') {
                contentHTML = `<a href="${data.content}" target="_blank" style="color: #58a6ff; text-decoration: underline;">📁 Download File (${data.filename || 'Attachment'})</a>`;
            } else {
                contentHTML = `<div>${decryptText(data.content)}</div>`;
            }

            msgCard.innerHTML = `
                ${userHTML}
                ${contentHTML}
                <div class="msg-footer">
                    ${deleteBtnHTML}
                    <span>${new Date(data.timestamp || Date.now()).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    ${ticksHTML}
                </div>
            `;
            
            msgBox.appendChild(msgCard);
            msgBox.scrollTop = msgBox.scrollHeight;

            if(!isMine) {
                socket.emit('message_seen', { room: currentRoom, password: roomPassword, id: data.id });
                scheduleAutoDelete(data.id);
            }
        }

        socket.on('receive_message', (data) => {
            appendMessageToScreen(data, data.user === myUsername);
        });

        socket.on('message_delivered', (data) => {
            let tickEl = document.getElementById('tick_' + data.id);
            if(tickEl && tickEl.innerText === "✓") { tickEl.innerText = "✓✓"; }
        });

        socket.on('message_seen_ack', (data) => {
            let tickEl = document.getElementById('tick_' + data.id);
            if(tickEl) { 
                tickEl.innerText = "✓✓"; 
                tickEl.className = "ticks seen"; 
                scheduleAutoDelete(data.id);
            }
        });

        socket.on('display_typing', (data) => {
            if(data.user !== myUsername) { document.getElementById('typing-indicator').innerText = data.user + " is typing..."; }
        });

        socket.on('hide_typing', (data) => {
            if(data.user !== myUsername) { document.getElementById('typing-indicator').innerText = ""; }
        });

        let localStream, peerConnection;
        let currentCallType = 'video';
        const servers = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

        async function startCall(type) {
            currentCallType = type;
            isMicMuted = false;
            updateMicButtonUI();
            document.getElementById('video-container').style.display = 'flex';
            const localVidEl = document.getElementById('localVideo');
            const remoteVidEl = document.getElementById('remoteVideo');
            const statusTitle = document.getElementById('call-status-title');
            const localPane = document.getElementById('local-video-pane');

            try {
                if (type === 'video') {
                    statusTitle.innerText = "📹 Video Call Connected";
                    localPane.style.display = 'flex';
                    localStream = await navigator.mediaDevices.getUserMedia({ 
                        video: { facingMode: currentFacingMode }, 
                        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } 
                    });
                } else {
                    statusTitle.innerText = "📞 Audio Call Connected";
                    localPane.style.display = 'none';
                    localStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
                }

                localVidEl.srcObject = localStream;
                peerConnection = new RTCPeerConnection(servers);
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
                
                peerConnection.ontrack = e => {
                    remoteVidEl.srcObject = e.streams[0];
                    remoteVidEl.play().catch(() => {});
                };

                peerConnection.onicecandidate = e => { 
                    if (e.candidate) { socket.emit('ice_candidate', { room: currentRoom, password: roomPassword, candidate: e.candidate, type: type }); }
                };

                let offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                socket.emit('offer', { room: currentRoom, password: roomPassword, offer: offer, type: type });
            } catch (err) { alert("Microphone/Camera permission denied!"); endCall(); }
        }

        function toggleMicrophone() {
            if (!localStream) return;
            isMicMuted = !isMicMuted;
            localStream.getAudioTracks().forEach(track => {
                track.enabled = !isMicMuted;
            });
            updateMicButtonUI();
        }

        function updateMicButtonUI() {
            const btn = document.getElementById('mute-mic-btn');
            if (isMicMuted) {
                btn.style.background = "#da3633";
                btn.innerText = "🔇 Unmute Mic";
            } else {
                btn.style.background = "#21262d";
                btn.innerText = "🎙️ Mute Mic";
            }
        }

        async function switchCamera() {
            if (!localStream) return;
            currentFacingMode = (currentFacingMode === 'user') ? 'environment' : 'user';
            const tracks = localStream.getVideoTracks();
            if (tracks.length > 0) { tracks[0].stop(); }
            try {
                let newStream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: currentFacingMode },
                    audio: true
                });
                let videoTrack = newStream.getVideoTracks()[0];
                let sender = peerConnection.getSenders().find(s => s.track && s.track.kind === 'video');
                if (sender) { sender.replaceTrack(videoTrack); }
                localStream = newStream;
                document.getElementById('localVideo').srcObject = localStream;
            } catch(e) { alert("Could not switch camera!"); }
        }

        socket.on('offer', async (data) => {
            currentCallType = data.type;
            isMicMuted = false;
            updateMicButtonUI();
            document.getElementById('video-container').style.display = 'flex';
            const statusTitle = document.getElementById('call-status-title');
            const localVidEl = document.getElementById('localVideo');
            const remoteVidEl = document.getElementById('remoteVideo');
            const localPane = document.getElementById('local-video-pane');
            
            statusTitle.innerText = data.type === 'video' ? "📹 Video Call Connected" : "📞 Audio Call Connected";
            localPane.style.display = (data.type === 'video') ? 'flex' : 'none';

            peerConnection = new RTCPeerConnection(servers);
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ 
                    video: data.type === 'video' ? { facingMode: currentFacingMode } : false, 
                    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } 
                });
                localVidEl.srcObject = localStream;
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
            } catch(e){}

            peerConnection.ontrack = e => {
                remoteVidEl.srcObject = e.streams[0];
                remoteVidEl.play().catch(() => {});
            };

            peerConnection.onicecandidate = e => { 
                if (e.candidate) { socket.emit('ice_candidate', { room: currentRoom, password: roomPassword, candidate: e.candidate, type: data.type }); }
            };

            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
            let ans = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(ans);
            socket.emit('answer', { room: currentRoom, password: roomPassword, answer: ans });
        });

        socket.on('answer', async (data) => { if(peerConnection) await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer)); });
        socket.on('ice_candidate', async (data) => { if (peerConnection && data.candidate) await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate)); });

        function endCall() {
            if (localStream) { localStream.getTracks().forEach(t => t.stop()); }
            if (peerConnection) { peerConnection.close(); peerConnection = null; }
            document.getElementById('localVideo').srcObject = null;
            document.getElementById('remoteVideo').srcObject = null;
            document.getElementById('video-container').style.display = 'none';
        }
    </script>
</body>
</html>
"""

ROOM_PASSWORDS = {}
ROOM_USERS = {}
ONLINE_USERS = set()
ROOM_FILES = {}
USER_SID_MAP = {}

@app.route('/')
def home():
    session.clear()
    return CALC_LOGIN_HTML

@app.route('/logout')
def logout():
    u = session.get('user')
    if u:
        ONLINE_USERS.discard(u)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_seen = ? WHERE username = ?", (datetime.datetime.now().strftime("%I:%M %p"), u))
        conn.commit()
        conn.close()
    session.clear()
    return redirect(url_for('home'))

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    u, p = data.get('username', '').strip(), data.get('password', '').strip()
    q, a = data.get('question', '').strip(), data.get('answer', '').strip()
    if not u or not p or not a: return jsonify({"status": "error", "message": "All fields required!"}), 400
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (u,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Username already exists!"}), 400
    cursor.execute("INSERT INTO users (username, password, sec_question, sec_answer, last_seen) VALUES (?, ?, ?, ?, ?)", (u, p, q, a, "Never"))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/get-question')
def get_question():
    u = request.args.get('username', '').strip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT sec_question FROM users WHERE username = ?", (u,))
    row = cursor.fetchone()
    conn.close()
    return jsonify({"question": row[0]}) if row else (jsonify({"error": "User not found"}), 404)

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    u, ans, p = data.get('username', '').strip(), data.get('answer', '').strip(), data.get('new_password', '').strip()
    if not u or not ans or not p: return jsonify({"status": "error", "message": "All fields required!"}), 400
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT sec_answer FROM users WHERE username = ?", (u,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Username not found!"}), 404
    if row[0].lower() != ans.lower():
        conn.close()
        return jsonify({"status": "error", "message": "Incorrect Security Answer!"}), 401
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (p, u))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    u, p = data.get('username', '').strip(), data.get('password', '').strip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blocked WHERE username = ?", (u,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "User is blocked!"}), 403
    cursor.execute("SELECT password FROM users WHERE username = ?", (u,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == p:
        session['authenticated'] = True
        session['user'] = u
        session['is_admin'] = (u == "admin")
        ONLINE_USERS.add(u)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid username or password!"}), 401

@app.route('/check-session')
def check_session():
    user = session.get('user')
    if not user: return jsonify({"authenticated": False})
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blocked WHERE username = ?", (user,))
    is_blocked = cursor.fetchone() is not None
    cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
    is_deleted = cursor.fetchone() is None
    conn.close()
    if session.get('authenticated') and not is_blocked and not is_deleted: ONLINE_USERS.add(user)
    return jsonify({"authenticated": session.get('authenticated', False) and not is_blocked and not is_deleted, "is_admin": session.get('is_admin', False), "username": user, "is_blocked": is_blocked, "is_deleted": is_deleted})

@app.route('/get-settings')
def get_settings():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = 'beep_interval'")
    row = cursor.fetchone()
    conn.close()
    val = int(row[0]) if row else 30000
    return jsonify({"beep_interval": val})

@app.route('/get-contacts')
def get_contacts():
    user = session.get('user')
    if not user: return jsonify({"contacts": []}), 401
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT contact_username FROM contacts WHERE owner = ?", (user,))
    contacts = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify({"contacts": contacts})

@app.route('/add-contact', methods=['POST'])
def add_contact():
    user = session.get('user')
    if not user: return jsonify({"status": "error", "message": "Unauthorized"}), 401
    target = request.json.get('contact', '').strip()
    if not target: return jsonify({"status": "error", "message": "Enter a username"}), 400
    if target == user: return jsonify({"status": "error", "message": "Cannot add yourself"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (target,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "User does not exist!"}), 404

    cursor.execute("SELECT * FROM contacts WHERE owner = ? AND contact_username = ?", (user, target))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Already in contacts!"}), 400

    cursor.execute("INSERT INTO contacts (owner, contact_username) VALUES (?, ?)", (user, target))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/remove-contact', methods=['POST'])
def remove_contact():
    user = session.get('user')
    if not user: return jsonify({"status": "error", "message": "Unauthorized"}), 401
    target = request.json.get('contact', '').strip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contacts WHERE owner = ? AND contact_username = ?", (user, target))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/upload-attachment', methods=['POST'])
def upload_attachment():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        unique_name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)
        return jsonify({"status": "success", "file_url": f"/static/uploads/{unique_name}"})
    return jsonify({"status": "error", "message": "Upload failed"}), 400

@app.route('/admin-panel-guru')
def admin_panel():
    if not session.get('is_admin', False): return redirect(url_for('home'))
    return ADMIN_HTML

@app.route('/get-admin-data')
def get_admin_data():
    if not session.get('is_admin', False): return jsonify({}), 403
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users")
    users = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT username FROM blocked")
    blocked = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT value FROM app_settings WHERE key = 'beep_interval'")
    row = cursor.fetchone()
    beep_interval = int(row[0]) if row else 30000
    conn.close()
    return jsonify({"users": users, "blocked": blocked, "beep_interval": beep_interval})

@app.route('/admin-update-beep', methods=['POST'])
def admin_update_beep():
    if not session.get('is_admin', False): return jsonify({}), 403
    seconds = request.json.get('seconds', 30)
    millis = int(seconds) * 1000
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE app_settings SET value = ? WHERE key = 'beep_interval'", (str(millis),))
    conn.commit()
    conn.close()
    # Real-time broadcast to everyone
    socketio.emit('global_beep_update', {"beep_interval": millis})
    return jsonify({"status": "success"})

@app.route('/block-user', methods=['POST'])
def block_user():
    if not session.get('is_admin', False): return jsonify({}), 403
    u = request.json.get('username')
    if u and u != "admin":
        ONLINE_USERS.discard(u)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO blocked (username) VALUES (?)", (u,))
        conn.commit()
        conn.close()
    return jsonify({"status": "success"})

@app.route('/unblock-user', methods=['POST'])
def unblock_user():
    if not session.get('is_admin', False): return jsonify({}), 403
    u = request.json.get('username')
    if u:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blocked WHERE username = ?", (u,))
        conn.commit()
        conn.close()
    return jsonify({"status": "success"})

@app.route('/delete-user', methods=['POST'])
def delete_user():
    if not session.get('is_admin', False): return jsonify({}), 403
    u = request.json.get('username')
    if u and u != "admin":
        ONLINE_USERS.discard(u)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (u,))
        cursor.execute("DELETE FROM blocked WHERE username = ?", (u,))
        cursor.execute("DELETE FROM contacts WHERE owner = ? OR contact_username = ?", (u, u))
        conn.commit()
        conn.close()
    return jsonify({"status": "success"})

@app.route('/chat')
def chat():
    user = session.get('user')
    if not user: return redirect(url_for('home'))
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blocked WHERE username = ?", (user,))
    is_blocked = cursor.fetchone() is not None
    cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
    is_deleted = cursor.fetchone() is None
    conn.close()
    if not session.get('authenticated') or is_blocked or is_deleted: return redirect(url_for('home'))
    return CHAT_HTML

@socketio.on('verify_and_join')
def handle_room_verification(data):
    room = data.get('room')
    password = data.get('password')
    username = data.get('user', 'User')
    USER_SID_MAP[username] = request.sid
    if room not in ROOM_PASSWORDS: ROOM_PASSWORDS[room] = password
    if ROOM_PASSWORDS.get(room) == password:
        join_room(room)
        if room not in ROOM_USERS: ROOM_USERS[room] = []
        if username not in ROOM_USERS[room]: ROOM_USERS[room].append(username)
        emit('room_join_response', {"status": "success", "active_users": len(ROOM_USERS[room])})
        emit('room_users_update', {"room": room, "active_users": len(ROOM_USERS[room]), "users": ROOM_USERS[room]}, to=room)
    else:
        emit('room_join_response', {"status": "error", "message": "Incorrect room password!"})

@socketio.on('fetch_pending_messages')
def handle_fetch_pending(data):
    room = data.get('room')
    username = data.get('user')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, data FROM pending_messages WHERE room = ? AND recipient = ?", (room, username))
    rows = cursor.fetchall()
    pending_list = []
    for row in rows:
        msg_id, msg_str = row[0], row[1]
        try:
            import ast
            msg_json = ast.literal_eval(msg_str)
            pending_list.append(msg_json)
        except Exception as e:
            print("Error loading pending message:", e)
    conn.close()
    if pending_list:
        emit('receive_pending_batch', {"messages": pending_list}, to=request.sid)

@socketio.on('ack_pending_received')
def handle_ack_pending(data):
    room = data.get('room')
    username = data.get('user')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_messages WHERE room = ? AND recipient = ?", (room, username))
    conn.commit()
    conn.close()

@socketio.on('stop_my_unread_alarm')
def handle_stop_alarm(data):
    username = data.get('user')
    if username in USER_SID_MAP:
        emit('stop_unread_alarm', to=USER_SID_MAP[username])

@socketio.on('leave_current_room')
def handle_leave_room(data):
    room = data.get('room')
    username = data.get('user')
    if room in ROOM_USERS and username in ROOM_USERS[room]:
        ROOM_USERS[room].remove(username)
        if len(ROOM_USERS[room]) == 0:
            ROOM_USERS.pop(room, None)
            ROOM_PASSWORDS.pop(room, None)
            if room in ROOM_FILES:
                for fpath in ROOM_FILES[room]:
                    try:
                        full_path = os.path.join(app.root_path, fpath.lstrip('/'))
                        if os.path.exists(full_path): os.remove(full_path)
                    except Exception as e:
                        print("Error deleting file:", e)
                ROOM_FILES.pop(room, None)
        leave_room(room)
        emit('room_users_update', {"room": room, "active_users": len(ROOM_USERS.get(room, [])), "users": ROOM_USERS.get(room, [])}, to=room)

@socketio.on('get_admin_rooms')
def handle_get_admin_rooms():
    if session.get('is_admin', False):
        active_rooms = [{"room": r, "users": len(users)} for r, users in ROOM_USERS.items() if len(users) > 0]
        emit('admin_rooms_list', active_rooms)

@socketio.on('admin_join_spy')
def handle_admin_join_spy(data):
    if session.get('is_admin', False): join_room(data.get('room'))

@socketio.on('admin_leave_spy')
def handle_admin_leave_spy(data):
    if session.get('is_admin', False): leave_room(data.get('room'))

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    if ROOM_PASSWORDS.get(room) == data.get('password'):
        msg_data = data['data']
        if msg_data.get('type') in ['image', 'file']:
            if room not in ROOM_FILES: ROOM_FILES[room] = []
            ROOM_FILES[room].append(msg_data['content'])
        
        active_users_in_room = ROOM_USERS.get(room, [])
        if len(active_users_in_room) <= 1:
            if room.startswith("private_"):
                parts = room.split("_")
                recipient = parts[2] if parts[1] == msg_data['sender'] else parts[1]
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO pending_messages (id, room, sender, recipient, data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                               (msg_data['id'], room, msg_data['sender'], recipient, str(msg_data), msg_data['timestamp']))
                conn.commit()
                conn.close()

                if recipient in USER_SID_MAP:
                    emit('trigger_unread_alarm', to=USER_SID_MAP[recipient])
        
        emit('receive_message', msg_data, to=room, include_self=False)
        emit('admin_spy_receive', msg_data, to=room)
        emit('message_delivered', {"id": msg_data['id']}, to=room)

@socketio.on('message_seen')
def handle_seen(data):
    room = data['room']
    if ROOM_PASSWORDS.get(room) == data.get('password'):
        emit('message_seen_ack', {"id": data['id']}, to=room)

@socketio.on('delete_message_for_everyone')
def handle_delete_for_everyone(data):
    room = data.get('room')
    msg_id = data.get('id')
    if ROOM_PASSWORDS.get(room) == data.get('password'):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_messages WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()
        emit('remove_message_card', {"id": msg_id}, to=room)

@socketio.on('typing')
def handle_typing(data): emit('display_typing', data, to=data['room'], include_self=False)

@socketio.on('stop_typing')
def handle_stop_typing(data): emit('hide_typing', data, to=data['room'], include_self=False)

@socketio.on('offer')
def handle_offer(data): 
    if ROOM_PASSWORDS.get(data['room']) == data.get('password'): emit('offer', data, to=data['room'], include_self=False)

@socketio.on('answer')
def handle_answer(data): 
    if ROOM_PASSWORDS.get(data['room']) == data.get('password'): emit('answer', data, to=data['room'], include_self=False)

@socketio.on('ice_candidate')
def handle_ice(data): 
    if ROOM_PASSWORDS.get(data['room']) == data.get('password'): emit('ice_candidate', data, to=data['room'], include_self=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
