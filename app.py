from flask import Flask, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import sqlite3
import datetime

app = Flask(__name__)
# Permanent Secret Key taaki server restart hone par session wipe na ho
app.secret_key = "ghost_super_secret_key_fixed_persistent_998877"

DB_FILE = "database.db"

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
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, sec_question, sec_answer, last_seen) VALUES (?, ?, ?, ?, ?)", 
                       ("admin", "guru&guru16230", "Master Key", "guru", "Never"))
    conn.commit()
    conn.close()

init_db()

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', ping_timeout=120, ping_interval=25, logger=True, engineio_logger=True)

@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calculator & System Portal</title>
    <style>
        body { background: #0d1117; color: white; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; user-select: none; }
        
        /* Calculator Screen Style */
        #calc-screen { display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; position: fixed; top: 0; left: 0; background: #0d1117; z-index: 1000; }
        .calculator { background: #161b22; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 280px; border: 1px solid #30363d; text-align: center; }
        #calc-display { width: 100%; height: 45px; background: #010409; border: 1px solid #30363d; color: #3fb950; font-size: 22px; text-align: right; padding: 5px 10px; margin-bottom: 12px; border-radius: 6px; box-sizing: border-box; }
        .calc-keys { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
        .calc-btn { padding: 12px; background: #21262d; color: white; border: 1px solid #30363d; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; }
        .calc-btn:hover { background: #30363d; }
        .calc-btn.operator { background: #1f6feb; border-color: #1f6feb; }
        .calc-btn.equal { background: #238636; border-color: #238636; grid-column: span 2; }
        .calc-btn.clear { background: #da3633; border-color: #da3633; }

        /* Portal Box Style */
        #portal-screen { display: none; justify-content: center; align-items: center; width: 100%; height: 100%; }
        .portal-box { background: #161b22; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); width: 330px; text-align: center; border: 1px solid #30363d; }
        .portal-box input, .portal-box select { width: 100%; padding: 10px; margin: 6px 0; background: #010409; border: 1px solid #30363d; color: white; border-radius: 6px; box-sizing: border-box; outline: none; }
        .secure-pass { -webkit-text-security: disc; text-security: disc; }
        .portal-box button { width: 100%; padding: 10px; background: #238636; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 8px; }
        .portal-box button:hover { background: #2ea043; }
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
    <!-- Calculator Screen -->
    <div id="calc-screen">
        <div class="calculator">
            <input type="text" id="calc-display" readonly value="0">
            <div class="calc-keys">
                <button class="calc-btn clear" onclick="clearCalc()">C</button>
                <button class="calc-btn" onclick="pressCalc('(')">(</button>
                <button class="calc-btn" onclick="pressCalc(')')">)</button>
                <button class="calc-btn operator" onclick="pressCalc('/')">/</button>
                
                <button class="calc-btn" onclick="pressCalc('7')">7</button>
                <button class="calc-btn" onclick="pressCalc('8')">8</button>
                <button class="calc-btn" onclick="pressCalc('9')">9</button>
                <button class="calc-btn operator" onclick="pressCalc('*')">*</button>
                
                <button class="calc-btn" onclick="pressCalc('4')">4</button>
                <button class="calc-btn" onclick="pressCalc('5')">5</button>
                <button class="calc-btn" onclick="pressCalc('6')">6</button>
                <button class="calc-btn operator" onclick="pressCalc('-')">-</button>
                
                <button class="calc-btn" onclick="pressCalc('1')">1</button>
                <button class="calc-btn" onclick="pressCalc('2')">2</button>
                <button class="calc-btn" onclick="pressCalc('3')">3</button>
                <button class="calc-btn operator" onclick="pressCalc('+')">+</button>
                
                <button class="calc-btn" onclick="pressCalc('0')">0</button>
                <button class="calc-btn" onclick="pressCalc('.')">.</button>
                <button class="calc-btn equal" onclick="calculateResult()">=</button>
            </div>
        </div>
    </div>

    <!-- Actual Portal Screen -->
    <div id="portal-screen">
        <div class="portal-box" autocomplete="off">
            <h2>🔒 Multi-User Portal</h2>
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('login', event)">Login</button>
                <button class="tab-btn" onclick="switchTab('register', event)">Register</button>
                <button class="tab-btn" onclick="switchTab('forgot', event)">Forgot?</button>
            </div>

            <div id="login-form" class="form-section active">
                <input type="text" id="login-user" placeholder="Username" autocomplete="off">
                <input type="text" id="login-pass" placeholder="Password" autocomplete="off" class="secure-pass" readonly onfocus="this.removeAttribute('readonly');">
                <button onclick="loginUser()">Login to Portal</button>
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
                <button onclick="registerUser()">Create Account</button>
                <div id="regMsg" class="error-msg"></div>
            </div>

            <div id="forgot-form" class="form-section">
                <input type="text" id="forgot-user" placeholder="Enter Username" autocomplete="off" onblur="fetchSecQuestion()">
                <div id="q-display" style="color: #58a6ff; font-size: 11px; margin: 4px 0; text-align: left;"></div>
                <input type="text" id="forgot-ans" placeholder="Security Answer" autocomplete="off">
                <input type="text" id="forgot-new-pass" placeholder="New Password" autocomplete="off" class="secure-pass" readonly onfocus="this.removeAttribute('readonly');">
                <button onclick="resetPassword()" style="background: #d29922; color: #0d1117;">Verify & Reset</button>
                <div id="forgotMsg" class="error-msg"></div>
            </div>
        </div>
    </div>

    <script>
        let calcInput = "0";

        function pressCalc(val) {
            if(calcInput === "0" && val !== '.') {
                calcInput = val;
            } else {
                calcInput += val;
            }
            document.getElementById("calc-display").value = calcInput;
        }

        function clearCalc() {
            calcInput = "0";
            document.getElementById("calc-display").value = calcInput;
        }

        function calculateResult() {
            // Secret Code Trigger: Agar user '786' type karke '=' dabaye toh portal khul jayega
            if(calcInput.trim() === "786") {
                document.getElementById("calc-screen").style.display = "none";
                document.getElementById("portal-screen").style.display = "flex";
                return;
            }

            try {
                let res = eval(calcInput);
                calcInput = res.toString();
                document.getElementById("calc-display").value = calcInput;
            } catch(e) {
                document.getElementById("calc-display").value = "Error";
                calcInput = "0";
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
            if(res.ok) {
                document.getElementById("q-display").innerText = "Question: " + data.question;
            } else {
                document.getElementById("q-display").innerText = "User not found!";
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
            const q = document.getElementById("reg-q").value;
            const ans = document.getElementById("reg-ans").value.trim();
            let response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: user, password: pass, question: q, answer: ans })
            });
            let result = await response.json();
            let msgEl = document.getElementById("regMsg");
            if (response.ok && result.status === "success") {
                msgEl.className = "success-msg";
                msgEl.innerText = "Account created! You can now login.";
                setTimeout(() => switchTab('login', {target: document.querySelectorAll('.tab-btn')[0]}), 1500);
            } else {
                msgEl.className = "error-msg";
                msgEl.innerText = result.message || "Registration failed!";
            }
        }

        async function resetPassword() {
            const user = document.getElementById("forgot-user").value.trim();
            const ans = document.getElementById("forgot-ans").value.trim();
            const pass = document.getElementById("forgot-new-pass").value.trim();
            let response = await fetch('/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: user, answer: ans, new_password: pass })
            });
            let result = await response.json();
            let msgEl = document.getElementById("forgotMsg");
            if (response.ok && result.status === "success") {
                msgEl.className = "success-msg";
                msgEl.innerText = "Password updated! You can now login.";
                setTimeout(() => switchTab('login', {target: document.querySelectorAll('.tab-btn')[0]}), 1500);
            } else {
                msgEl.className = "error-msg";
                msgEl.innerText = result.message || "Reset failed!";
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
        .header-info { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-bottom: 15px; }
        .user-tag { background: #21262d; padding: 4px 8px; border-radius: 4px; font-size: 12px; color: #3fb950; border: 1px solid #30363d; font-weight: bold; }
    </style>
</head>
<body>
    <div class="admin-box">
        <div class="header-info">
            <h2>🛡️ Admin Panel</h2>
            <div id="current-user-tag" class="user-tag">👤 Loading...</div>
        </div>
        <p style="color: #8b949e; font-size: 12px; margin-bottom: 15px;">Total Users: <b id="total-count" style="color:white;">0</b></p>
        
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

        <div style="margin-top: 15px; display: flex; justify-content: space-between; align-items: center;">
            <a href="/chat" class="back-link" style="margin-top:0;">⬅ Back to Lobby</a>
            <a href="/logout" class="back-link" style="color: #f85149; margin-top:0;">🚪 Logout</a>
        </div>
    </div>

    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io({ transports: ['polling', 'websocket'] });
        let spyingRoom = null;

        async function fetchUserInfo() {
            try {
                let res = await fetch('/check-session', {cache: "no-store"});
                let data = await res.json();
                if(data.authenticated) {
                    document.getElementById('current-user-tag').innerText = "👤 " + data.username;
                }
            } catch(e) {}
        }
        fetchUserInfo();

        async function fetchDashboard() {
            try {
                let res = await fetch('/get-admin-data');
                let data = await res.json();
                document.getElementById('total-count').innerText = data.users.length;
                let usrListEl = document.getElementById('users-list');
                let blockedListEl = document.getElementById('blocked-list');
                usrListEl.innerHTML = "";
                blockedListEl.innerHTML = "";

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

                if(data.blocked.length === 0) {
                    blockedListEl.innerHTML = `<li style="justify-content:center; color:#8b949e;">No blocked users</li>`;
                } else {
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

        async function blockUser(username) {
            if (confirm("Are you sure you want to block " + username + "?")) {
                let res = await fetch('/block-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username })
                });
                let data = await res.json();
                if (data.status === "success") { fetchDashboard(); }
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
        }

        async function deleteUser(username) {
            if (confirm("Are you sure you want to permanently delete " + username + "?")) {
                let res = await fetch('/delete-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username })
                });
                let data = await res.json();
                if (data.status === "success") { fetchDashboard(); }
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
            if(rooms.length === 0) {
                listEl.innerHTML = `<li style="justify-content:center; color:#8b949e;">No active rooms right now</li>`;
                return;
            }
            listEl.innerHTML = "";
            rooms.forEach(r => {
                listEl.innerHTML += `
                    <li>
                        <span>👻 ${r.room} <b style="color:#3fb950;">(${r.users} users)</b></span>
                        <button class="action-btn monitor-btn" onclick="spySpecificRoom('${r.room}')">Read Chats</button>
                    </li>`;
            });
        });

        socket.on('admin_spy_receive', (data) => {
            let box = document.getElementById('monitor-messages');
            box.innerHTML += `<div><b>${data.user}:</b> ${data.msg}</div>`;
            box.scrollTop = box.scrollHeight;
        });

        setInterval(() => {
            socket.emit('get_admin_rooms');
        }, 3000);

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
        .lobby-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }
        .lobby-user-tag { font-size: 11px; color: #3fb950; font-weight: bold; background: #21262d; padding: 3px 6px; border-radius: 4px; border: 1px solid #30363d; }
        .lobby-box input { width: 100%; padding: 10px; margin: 6px 0; background: #010409; border: 1px solid #30363d; color: white; border-radius: 6px; box-sizing: border-box; outline: none; }
        .secure-pass { -webkit-text-security: disc; text-security: disc; }
        .lobby-box button { width: 100%; padding: 10px; background: #1f6feb; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 8px; }
        .lobby-box button:hover { background: #388bfd; }

        .rooms-history { margin-top: 15px; text-align: left; }
        .rooms-history h4 { font-size: 12px; color: #8b949e; margin-bottom: 8px; border-bottom: 1px solid #30363d; padding-bottom: 4px; }
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
        .btn-admin { background-color: #d29922; display: none; color: #0d1117; }
        .btn-logout-manual { background-color: #da3633; color: white; }
        #messages { flex-grow: 1; overflow-y: auto; padding: 15px; background: #0d1117; display: flex; flex-direction: column; gap: 12px; }
        .msg-card { padding: 4px 8px; max-width: 75%; word-wrap: break-word; font-size: 0.9rem; position: relative; background: transparent !important; border: none !important; }
        .my-msg { align-self: flex-end; }
        .other-msg { align-self: flex-start; }
        .user-id { font-size: 0.7em; color: #8b949e; margin-bottom: 2px; display: block; font-weight: bold; }
        .msg-footer { display: flex; justify-content: flex-end; align-items: center; gap: 4px; font-size: 0.65rem; margin-top: 2px; color: #cbd5e1; }
        .ticks { font-size: 0.85rem; font-family: monospace; color: #8b949e; }
        .ticks.seen { color: #53bdeb !important; }
        .input-box { display: flex; padding: 12px; background: #21262d; gap: 8px; border-top: 1px solid #30363d; flex-direction: column; }
        .input-row { display: flex; gap: 8px; width: 100%; }
        input { width: 100%; padding: 10px; background: #010409; border: 1px solid #30363d; color: white; border-radius: 6px; outline: none; user-select: text; }
        button.btn-send { padding: 10px 18px; background: #238636; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        #typing-indicator { font-size: 0.75rem; color: #3fb950; font-style: italic; height: 15px; }
        #video-container { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 1000; justify-content: center; align-items: center; flex-direction: column; }
        video { width: 80%; max-width: 400px; border-radius: 8px; background: black; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div id="security-warning">⚠️ Screen Recording / Capture Detected!<br>Access Restricted for Security.</div>

    <div id="room-lobby">
        <div class="lobby-box">
            <div class="lobby-header">
                <h3 style="margin:0; font-size: 15px;">🌐 Room Gateway</h3>
                <div id="lobby-user-tag" class="lobby-user-tag">👤 Loading...</div>
            </div>
            <p style="color: #8b949e; font-size: 11px; margin-bottom: 10px;">Enter room details to create or join.</p>
            
            <input type="text" id="room-name-input" placeholder="Room Name" autocomplete="off">
            <input type="text" id="room-pass-input" placeholder="Room Password" autocomplete="off" class="secure-pass" readonly onfocus="this.removeAttribute('readonly');">
            <button id="gate-btn" onclick="joinProtectedRoom()">Join / Create Room</button>
            <div id="gate-error" style="color: #f85149; font-size: 12px; margin-top: 6px;"></div>

            <div class="rooms-history">
                <h4>📂 Recently Joined Rooms</h4>
                <div id="joined-rooms-list" style="max-height: 140px; overflow-y: auto;">
                    <div style="color: #8b949e; font-size: 11px; text-align: center; padding: 5px;">No rooms joined yet</div>
                </div>
            </div>

            <button onclick="instantLogout()" style="background: #da3633; margin-top: 15px;">🚪 Logout Portal</button>
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
                <h3 id="room-title">👻 Ghost Tunnel</h3>
                <span id="display-status" class="status-text">● Secure Room Connected</span>
            </div>
            <div class="call-btns">
                <button id="e2ee-btn" class="btn-call btn-e2ee" onclick="toggleE2EE()">🔐</button>
                <button class="btn-call btn-audio" onclick="startCall('audio')">📞</button>
                <button class="btn-call btn-video" onclick="startCall('video')">📹</button>
                <button id="admin-panel-btn" class="btn-call btn-admin" onclick="window.location.href='/admin-panel-guru'">🛡️</button>
                <button class="btn-call btn-logout-manual" onclick="returnToLobby()" title="Back to Lobby">⬅ Lobby</button>
                <button class="btn-call btn-logout-manual" onclick="instantLogout()" title="Logout">🚪</button>
            </div>
        </div>
        <div id="messages"></div>
        <div class="input-box">
            <div id="typing-indicator"></div>
            <div class="input-row">
                <input type="text" id="msg-input" placeholder="Type a message..." autocomplete="off" oninput="notifyTyping()" onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="btn-send" onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('keyup', (e) => {
            if (e.key === 'PrintScreen') { triggerSecurityAlert(); }
        });

        if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
            const originalGetDisplayMedia = navigator.mediaDevices.getDisplayMedia;
            navigator.mediaDevices.getDisplayMedia = function(constraints) {
                triggerSecurityAlert();
                return originalGetDisplayMedia.call(navigator.mediaDevices, constraints);
            };
        }

        async function instantLogout() {
            try { await fetch('/logout', { method: 'GET', cache: "no-store" }); } catch(e) {}
            wipeAndExit();
        }

        function wipeAndExit() {
            document.body.innerHTML = "<div style='background:#0d1117; color:#f85149; display:flex; justify-content:center; align-items:center; height:100vh; font-family:Arial; font-size:1.5rem; font-weight:bold; text-align:center;'>⚠️ Session Ended</div>";
            window.location.href = "/";
        }

        function triggerSecurityAlert() {
            document.getElementById('security-warning').style.display = 'flex';
        }

        const socket = io({ 
            transports: ['polling', 'websocket'],
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            timeout: 30000
        });

        let currentRoom = "";
        let roomPassword = "";
        let myUsername = "User";
        let typingTimeout = null;
        let lastSender = null;
        
        let isE2EEActive = localStorage.getItem('ghost_e2ee') === 'true';
        updateE2EEButtonUI();

        renderJoinedRooms();

        async function initChat() {
            try {
                let res = await fetch('/check-session', {cache: "no-store"});
                let data = await res.json();
                if(data.authenticated) {
                    if(data.is_blocked || data.is_deleted) { instantLogout(); return; }
                    myUsername = data.username;
                    document.getElementById('lobby-user-tag').innerText = "👤 " + myUsername;
                    if(data.is_admin) { document.getElementById('admin-panel-btn').style.display = 'inline-block'; }
                } else { window.location.href = "/"; }
            } catch(e) { window.location.href = "/"; }
        }
        initChat();

        function saveRoomToHistory(name) {
            let history = JSON.parse(localStorage.getItem('ghost_rooms_history') || '[]');
            if (!history.includes(name)) {
                history.push(name);
                localStorage.setItem('ghost_rooms_history', JSON.stringify(history));
            }
            renderJoinedRooms();
        }

        function renderJoinedRooms() {
            let historyListEl = document.getElementById('joined-rooms-list');
            let history = JSON.parse(localStorage.getItem('ghost_rooms_history') || '[]');

            if(history.length === 0) {
                historyListEl.innerHTML = `<div style="color: #8b949e; font-size: 11px; text-align: center; padding: 5px;">No rooms joined yet</div>`;
                return;
            }

            historyListEl.innerHTML = "";
            history.forEach(rName => {
                historyListEl.innerHTML += `
                    <div class="room-item" onclick="quickSelectRoom('${rName}')">
                        <span>👻 ${rName}</span>
                        <span style="font-size:10px; color:#58a6ff;">Select ➔</span>
                    </div>
                `;
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

            if(!rName || !rPass) {
                errEl.innerText = "Please enter both room name and password!";
                return;
            }

            errEl.innerText = "";
            btnEl.innerText = "Connecting...";
            btnEl.disabled = true;

            currentRoom = rName;
            roomPassword = rPass;

            socket.emit('verify_and_join', { room: currentRoom, password: roomPassword, user: myUsername });

            setTimeout(() => {
                if(btnEl.innerText === "Connecting...") {
                    btnEl.innerText = "Join / Create Room";
                    btnEl.disabled = false;
                }
            }, 6000);
        }

        socket.on('room_join_response', (data) => {
            const btnEl = document.getElementById("gate-btn");
            if(btnEl) {
                btnEl.innerText = "Join / Create Room";
                btnEl.disabled = false;
            }

            if(data.status === "success") {
                saveRoomToHistory(currentRoom); 
                document.getElementById('room-lobby').style.display = 'none';
                document.getElementById('chat-screen').style.display = 'flex';
                document.getElementById('room-title').innerText = "👻 " + currentRoom + ` (${data.active_users} online)`;
            } else {
                alert(data.message || "Incorrect room password!");
                document.getElementById('gate-error').innerText = data.message || "Incorrect room password!";
            }
        });

        function returnToLobby() {
            socket.emit('leave_current_room', { room: currentRoom, user: myUsername });
            currentRoom = "";
            roomPassword = "";
            document.getElementById('chat-screen').style.display = 'none';
            document.getElementById('room-lobby').style.display = 'flex';
            document.getElementById('messages').innerHTML = "";
            renderJoinedRooms();
        }

        socket.on('room_users_update', (data) => {
            if(data.room === currentRoom) {
                document.getElementById('room-title').innerText = "👻 " + currentRoom + ` (${data.active_users} online)`;
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
            typingTimeout = setTimeout(() => {
                socket.emit('stop_typing', { room: currentRoom, user: myUsername });
            }, 1000);
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
                    user: myUsername, 
                    msg: encryptText(text), 
                    timestamp: Date.now() 
                };
                appendMessageToScreen(messageData, true);
                socket.emit('send_message', { room: currentRoom, password: roomPassword, data: messageData });
                input.value = "";
            }
        }

        function appendMessageToScreen(data, isMine) {
            const now = Date.now();
            const msgTimestamp = data.timestamp || now;
            const msgBox = document.getElementById('messages');
            
            const msgCard = document.createElement('div');
            msgCard.className = `msg-card ${isMine ? 'my-msg' : 'other-msg'}`;
            
            let showUserHeading = (data.user !== lastSender);
            lastSender = data.user;

            let userHTML = showUserHeading ? `<span class="user-id">${data.user}</span>` : '';
            let ticksHTML = isMine ? `<span id="tick_${data.id}" class="ticks">✓</span>` : '';
            
            msgCard.innerHTML = `
                ${userHTML}
                <div>${decryptText(data.msg)}</div>
                <div class="msg-footer">
                    <span>${new Date(msgTimestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    ${ticksHTML}
                </div>
            `;
            
            msgBox.appendChild(msgCard);
            msgBox.scrollTop = msgBox.scrollHeight;

            if(!isMine) {
                socket.emit('message_seen', { room: currentRoom, password: roomPassword, id: data.id });
            }

            let remainingLife = 60000 - (now - msgTimestamp);
            if (remainingLife < 1000) remainingLife = 1000;
            setTimeout(() => { if(msgCard.parentNode) msgCard.parentNode.removeChild(msgCard); }, remainingLife);
        }

        socket.on('receive_message', (data) => {
            if (data.user !== myUsername) {
                appendMessageToScreen(data, false);
            }
        });

        socket.on('message_delivered', (data) => {
            let tickEl = document.getElementById('tick_' + data.id);
            if(tickEl) { tickEl.innerText = "✓✓"; }
        });

        socket.on('message_seen_ack', (data) => {
            let tickEl = document.getElementById('tick_' + data.id);
            if(tickEl) {
                tickEl.innerText = "✓✓";
                tickEl.className = "ticks seen";
            }
        });

        socket.on('display_typing', (data) => {
            if(data.user !== myUsername) {
                document.getElementById('typing-indicator').innerText = data.user + " is typing...";
            }
        });

        socket.on('hide_typing', (data) => {
            if(data.user !== myUsername) {
                document.getElementById('typing-indicator').innerText = "";
            }
        });

        let localStream, peerConnection;
        const servers = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };
        async function startCall(type) {
            document.getElementById('video-container').style.display = 'flex';
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: type === 'video', audio: true });
                document.getElementById('localVideo').srcObject = localStream;
                peerConnection = new RTCPeerConnection(servers);
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
                peerConnection.ontrack = e => document.getElementById('remoteVideo').srcObject = e.streams[0];
                peerConnection.onicecandidate = e => { if (e.candidate) socket.emit('ice_candidate', { room: currentRoom, password: roomPassword, candidate: e.candidate }); };
                let offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                socket.emit('offer', { room: currentRoom, password: roomPassword, offer: offer });
            } catch (err) { alert("Call error"); endCall(); }
        }
        socket.on('offer', async (data) => {
            document.getElementById('video-container').style.display = 'flex';
            peerConnection = new RTCPeerConnection(servers);
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                document.getElementById('localVideo').srcObject = localStream;
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
            } catch(e){}
            peerConnection.ontrack = e => document.getElementById('remoteVideo').srcObject = e.streams[0];
            peerConnection.onicecandidate = e => { if (e.candidate) socket.emit('ice_candidate', { room: currentRoom, password: roomPassword, candidate: e.candidate }); };
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
            let ans = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(ans);
            socket.emit('answer', { room: currentRoom, password: roomPassword, answer: ans });
        });
        socket.on('answer', async (data) => { if(peerConnection) await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer)); });
        socket.on('ice_candidate', async (data) => { if (peerConnection && data.candidate) await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate)); });
        function endCall() {
            if (localStream) localStream.getTracks().forEach(t => t.stop());
            if (peerConnection) peerConnection.close();
            document.getElementById('video-container').style.display = 'none';
        }
    </script>
</body>
</html>
"""

ROOM_PASSWORDS = {}
ROOM_USERS = {}
ONLINE_USERS = set()

@app.route('/')
def home():
    if session.get('authenticated'):
        return redirect(url_for('chat'))
    return LOGIN_HTML

@app.route('/logout')
def logout():
    u = session.get('user')
    if u:
        ONLINE_USERS.discard(u)
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_seen = ? WHERE username = ?", (now_str, u))
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
    
    cursor.execute("INSERT INTO users (username, password, sec_question, sec_answer, last_seen) VALUES (?, ?, ?, ?, ?)", 
                   (u, p, q, a, "Never"))
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
    if row:
        return jsonify({"question": row[0]})
    return jsonify({"error": "User not found"}), 404

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    u = data.get('username', '').strip()
    ans = data.get('answer', '').strip()
    p = data.get('new_password', '').strip()
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
        session.permanent = True
        session['authenticated'] = True
        session['user'] = u
        session['is_admin'] = (u == "admin")
        ONLINE_USERS.add(u)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid username or password!"}), 401

@app.route('/check-session')
def check_session():
    user = session.get('user')
    if not user:
        return jsonify({"authenticated": False})
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blocked WHERE username = ?", (user,))
    is_blocked = cursor.fetchone() is not None
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
    is_deleted = cursor.fetchone() is None
    conn.close()
    
    if session.get('authenticated') and not is_blocked and not is_deleted:
        ONLINE_USERS.add(user)
    
    return jsonify({
        "authenticated": session.get('authenticated', False) and not is_blocked and not is_deleted,
        "is_admin": session.get('is_admin', False),
        "username": user,
        "is_blocked": is_blocked,
        "is_deleted": is_deleted
    })

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
    conn.close()
    return jsonify({"users": users, "blocked": blocked})

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
    
    if not session.get('authenticated') or is_blocked or is_deleted: 
        return redirect(url_for('home'))
    return CHAT_HTML

@socketio.on('verify_and_join')
def handle_room_verification(data):
    room = data.get('room')
    password = data.get('password')
    username = data.get('user', 'User')
    
    if room not in ROOM_PASSWORDS:
        ROOM_PASSWORDS[room] = password
        
    if ROOM_PASSWORDS.get(room) == password:
        join_room(room)
        
        if room not in ROOM_USERS:
            ROOM_USERS[room] = []
        if username not in ROOM_USERS[room]:
            ROOM_USERS[room].append(username)
            
        emit('room_join_response', {
            "status": "success", 
            "active_users": len(ROOM_USERS[room])
        })
        emit('room_users_update', {
            "room": room, 
            "active_users": len(ROOM_USERS[room]), 
            "users": ROOM_USERS[room]
        }, to=room)
    else:
        emit('room_join_response', {"status": "error", "message": "Incorrect room password!"})

@socketio.on('leave_current_room')
def handle_leave_room(data):
    room = data.get('room')
    username = data.get('user')
    if room in ROOM_USERS and username in ROOM_USERS[room]:
        ROOM_USERS[room].remove(username)
        if len(ROOM_USERS[room]) == 0:
            ROOM_USERS.pop(room, None)
            ROOM_PASSWORDS.pop(room, None)
        leave_room(room)
        emit('room_users_update', {
            "room": room, 
            "active_users": len(ROOM_USERS.get(room, [])), 
            "users": ROOM_USERS.get(room, [])
        }, to=room)

@socketio.on('get_admin_rooms')
def handle_get_admin_rooms():
    if session.get('is_admin', False):
        active_rooms = [{"room": r, "users": len(users)} for r, users in ROOM_USERS.items() if len(users) > 0]
        emit('admin_rooms_list', active_rooms)

@socketio.on('admin_join_spy')
def handle_admin_join_spy(data):
    if session.get('is_admin', False):
        room = data.get('room')
        join_room(room)

@socketio.on('admin_leave_spy')
def handle_admin_leave_spy(data):
    if session.get('is_admin', False):
        room = data.get('room')
        leave_room(room)

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    if ROOM_PASSWORDS.get(room) == data.get('password'):
        msg_data = data['data']
        emit('receive_message', msg_data, to=room)
        emit('admin_spy_receive', msg_data, to=room)
        emit('message_delivered', {"id": msg_data['id']}, to=room)

@socketio.on('message_seen')
def handle_seen(data):
    room = data['room']
    if ROOM_PASSWORDS.get(room) == data.get('password'):
        emit('message_seen_ack', {"id": data['id']}, to=room)

@socketio.on('typing')
def handle_typing(data):
    emit('display_typing', data, to=data['room'], include_self=False)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    emit('hide_typing', data, to=data['room'], include_self=False)

@socketio.on('offer')
def handle_offer(data): 
    if ROOM_PASSWORDS.get(data['room']) == data.get('password'):
        emit('offer', data, to=data['room'], include_self=False)

@socketio.on('answer')
def handle_answer(data): 
    if ROOM_PASSWORDS.get(data['room']) == data.get('password'):
        emit('answer', data, to=data['room'], include_self=False)

@socketio.on('ice_candidate')
def handle_ice(data): 
    if ROOM_PASSWORDS.get(data['room']) == data.get('password'):
        emit('ice_candidate', data, to=data['room'], include_self=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
