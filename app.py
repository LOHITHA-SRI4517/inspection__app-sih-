from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory
)
import sqlite3
from datetime import datetime
import uuid
import os
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.utils import secure_filename


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = "smart_inspection_system_2026_secure_key"

DATABASE = "inspection.db"
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def login_required():
    return "user_id" in session


def authority_required():
    return (
        "user_id" in session
        and session.get("role") == "Authority"
    )


def calculate_priority(location):
    """
    Priority Rule:
    1 occurrence  = Low
    2-3 occurrences = Medium
    4+ occurrences = High
    """

    conn = get_connection()

    count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM issues
        WHERE LOWER(location) = LOWER(?)
    """, (location,)).fetchone()["count"]

    conn.close()

    # +1 because the new issue is not inserted yet
    occurrence = count + 1

    if occurrence >= 4:
        return "High"

    elif occurrence >= 2:
        return "Medium"

    return "Low"


# ============================================================
# CREATE DATABASE
# ============================================================

def create_database():

    conn = get_connection()

    # USERS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # INSPECTION ASSIGNMENTS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            instructions TEXT,
            scheduled_date TEXT,
            status TEXT DEFAULT 'Assigned',
            created_at TEXT NOT NULL,
            FOREIGN KEY(worker_id) REFERENCES users(id)
        )
    """)

    # ISSUES
    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            worker_id INTEGER,
            location TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            description TEXT,
            photo TEXT,
            latitude TEXT,
            longitude TEXT,
            priority TEXT DEFAULT 'Low',
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'Pending Verification',
            FOREIGN KEY(assignment_id) REFERENCES assignments(id),
            FOREIGN KEY(worker_id) REFERENCES users(id)
        )
    """)

    # CCTV CAMERAS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            camera_name TEXT NOT NULL,
            stream_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # DEFAULT AUTHORITY
    authority = conn.execute("""
        SELECT * FROM users
        WHERE unique_id = ?
    """, ("ADMIN001",)).fetchone()

    if authority is None:

        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "ADMIN001",
            "System Authority",
            generate_password_hash("admin123"),
            "Authority",
            now()
        ))

    # DEFAULT WORKER
    worker = conn.execute("""
        SELECT * FROM users
        WHERE unique_id = ?
    """, ("WORK001",)).fetchone()

    if worker is None:

        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "WORK001",
            "Demo Worker",
            generate_password_hash("worker123"),
            "Worker",
            now()
        ))

    conn.commit()
    conn.close()


create_database()


# ============================================================
# WEBSITE STYLE
# ============================================================

STYLE = """
<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f7fb;
    color: #1e293b;
}

.navbar {
    background: linear-gradient(90deg, #0f172a, #1d4ed8);
    color: white;
    padding: 17px 8%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
}

.navbar a {
    color: white;
    text-decoration: none;
    margin-left: 15px;
    font-weight: bold;
}

.container {
    max-width: 1200px;
    margin: auto;
    padding: 30px 20px;
}

.card {
    background: white;
    padding: 28px;
    border-radius: 16px;
    margin-bottom: 25px;
    box-shadow: 0 6px 22px rgba(0,0,0,0.08);
}

.hero {
    text-align: center;
    padding: 70px 25px;
    background: linear-gradient(135deg, #eff6ff, #eef2ff);
}

.hero h1 {
    font-size: 40px;
    color: #1e3a8a;
}

.btn {
    display: inline-block;
    background: #2563eb;
    color: white;
    padding: 11px 18px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    text-decoration: none;
    margin: 4px;
    font-size: 14px;
}

.btn-green {
    background: #059669;
}

.btn-purple {
    background: #7c3aed;
}

.btn-orange {
    background: #ea580c;
}

.btn-red {
    background: #dc2626;
}

input, select, textarea {
    width: 100%;
    padding: 12px;
    margin-top: 7px;
    margin-bottom: 17px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 15px;
}

textarea {
    min-height: 100px;
}

h1, h2, h3 {
    color: #1e3a8a;
}

.info {
    background: #eff6ff;
    padding: 15px;
    border-left: 5px solid #2563eb;
    border-radius: 7px;
    margin: 15px 0;
}

.success {
    background: #dcfce7;
    padding: 15px;
    border-left: 5px solid #16a34a;
    border-radius: 7px;
    margin: 15px 0;
}

.error {
    background: #fee2e2;
    color: #991b1b;
    padding: 12px;
    border-radius: 7px;
    margin: 10px 0;
}

.badge {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 20px;
    background: #e0e7ff;
    font-size: 13px;
    font-weight: bold;
}

.priority-high {
    background: #fee2e2;
    color: #991b1b;
}

.priority-medium {
    background: #fef3c7;
    color: #92400e;
}

.priority-low {
    background: #dcfce7;
    color: #166534;
}

.status-pending {
    background: #ede9fe;
    color: #6d28d9;
}

.status-reported {
    background: #fee2e2;
    color: #991b1b;
}

.status-progress {
    background: #fef3c7;
    color: #92400e;
}

.status-resolved {
    background: #dcfce7;
    color: #166534;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 18px;
}

.feature {
    background: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.07);
}

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 18px;
    margin: 22px 0;
}

.stat-card {
    background: white;
    padding: 22px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 5px 18px rgba(0,0,0,0.08);
}

.stat-number {
    font-size: 32px;
    font-weight: bold;
    color: #2563eb;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th {
    background: #1e3a8a;
    color: white;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
}

.photo {
    width: 110px;
    max-height: 90px;
    object-fit: cover;
    border-radius: 8px;
}

.footer {
    text-align: center;
    padding: 25px;
    color: #64748b;
}

@media(max-width: 700px) {

    .navbar {
        padding: 15px;
    }

    .navbar a {
        margin-left: 6px;
    }

    .hero h1 {
        font-size: 29px;
    }

    .container {
        padding: 15px;
    }

    table {
        font-size: 13px;
    }
}

</style>
"""


# ============================================================
# NAVIGATION BAR
# ============================================================

def navbar():

    if "user_id" not in session:
        return ""

    role = session.get("role")

    links = """
        <a href="/home">🏠 Home</a>
        <a href="/dashboard">📊 Dashboard</a>
    """

    if role == "Authority":
        links += """
            <a href="/users">👥 Users</a>
            <a href="/assignments">📋 Assign</a>
            <a href="/cameras">📹 CCTV</a>
        """

    elif role == "Worker":
        links += """
            <a href="/my-assignments">📋 My Tasks</a>
        """

    links += """
        <a href="/logout">🚪 Logout</a>
    """

    return f"""
    <div class="navbar">
        <div><b>🏛️ Smart Inspection System</b></div>
        <div>{links}</div>
    </div>
    """


# ============================================================
# LANDING PAGE
# ============================================================

@app.route("/")
def landing():

    return f"""
    {STYLE}

    <div class="navbar">
        <b>🏛️ Smart Inspection System</b>
        <a href="/login">🔐 Login</a>
    </div>

    <div class="hero">

        <h1>🏛️ Smart Real-Time Monitoring & Inspection System</h1>

        <p>
            A centralized digital platform for inspection assignment,
            real-time monitoring, evidence-based reporting and
            efficient issue resolution.
        </p>

        <a class="btn" href="/login">
            🔐 Login to System
        </a>

    </div>

    <div class="container">

        <div class="grid">

            <div class="feature">
                <h3>📋 Smart Assignment</h3>
                Authority assigns inspections directly to workers.
            </div>

            <div class="feature">
                <h3>📸 Live Evidence</h3>
                Workers upload photographs as inspection proof.
            </div>

            <div class="feature">
                <h3>📍 Geo Information</h3>
                Inspection reports can include location coordinates.
            </div>

            <div class="feature">
                <h3>📊 Real-Time Dashboard</h3>
                Authorities monitor all inspection activities.
            </div>

        </div>

        <div class="card">

            <h2>⚙️ Inspection Workflow</h2>

            <p style="font-size:17px; line-height:2;">
                👨‍💼 Authority Assigns Inspection
                → 👷 Worker Receives Assignment
                → 🔍 Inspection Conducted
                → 📸 Evidence Submitted
                → 👨‍💼 Authority Verifies
                → 🔧 Action Started
                → ✅ Issue Resolved
            </p>

        </div>

    </div>

    <div class="footer">
        Smart Real-Time Monitoring & Inspection System | Project 2026
    </div>
    """


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if login_required():
        return redirect(url_for("home"))

    error = ""

    if request.method == "POST":

        unique_id = request.form["unique_id"].strip().upper()
        password = request.form["password"]

        conn = get_connection()

        user = conn.execute("""
            SELECT * FROM users
            WHERE unique_id = ?
        """, (unique_id,)).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"], password
        ):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        error = "❌ Invalid Unique ID or Password."

    return f"""
    {STYLE}

    <div class="navbar">
        <b>🏛️ Smart Inspection System</b>
        <a href="/">← Back</a>
    </div>

    <div class="container">

        <div class="card"
             style="max-width:500px; margin:50px auto;">

            <h1 style="text-align:center;">🔐 Login</h1>

            <form method="POST">

                <label>🆔 Unique ID</label>
                <input type="text"
                       name="unique_id"
                       required>

                <label>🔑 Password</label>
                <input type="password"
                       name="password"
                       required>

                <button class="btn"
                        style="width:100%;"
                        type="submit">
                    Login
                </button>

            </form>

            <p class="error">{error}</p>

            <p style="text-align:center;">
                <a href="/forgot-password">
                    Forgot Password?
                </a>
            </p>

        </div>

    </div>
    """


# ============================================================
# FORGOT PASSWORD
# ============================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    message = ""
    error = ""

    if request.method == "POST":

        unique_id = request.form["unique_id"].strip().upper()
        name = request.form["name"].strip()
        new_password = request.form["new_password"]

        conn = get_connection()

        user = conn.execute("""
            SELECT * FROM users
            WHERE unique_id = ?
            AND LOWER(name) = LOWER(?)
        """, (unique_id, name)).fetchone()

        if user:

            conn.execute("""
                UPDATE users
                SET password = ?
                WHERE id = ?
            """, (
                generate_password_hash(new_password),
                user["id"]
            ))

            conn.commit()
            message = "✅ Password changed successfully! Please login."

        else:
            error = "❌ User details do not match."

        conn.close()

    return f"""
    {STYLE}

    <div class="container">

        <div class="card"
             style="max-width:500px; margin:50px auto;">

            <h1>🔑 Reset Password</h1>

            <p class="info">
                For this project demo, verify your Unique ID and Name
                before changing your password.
            </p>

            <form method="POST">

                <label>🆔 Unique ID</label>
                <input name="unique_id" required>

                <label>👤 Full Name</label>
                <input name="name" required>

                <label>🔑 New Password</label>
                <input type="password"
                       name="new_password"
                       minlength="6"
                       required>

                <button class="btn"
                        type="submit">
                    Change Password
                </button>

            </form>

            <p class="success">{message}</p>
            <p class="error">{error}</p>

            <a href="/login">← Back to Login</a>

        </div>

    </div>
    """


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("landing"))


# ============================================================
# HOME
# ============================================================

@app.route("/home")
def home():

    if not login_required():
        return redirect(url_for("login"))

    role = session["role"]

    if role == "Authority":

        buttons = """
        <a class="btn btn-purple" href="/assignments">
            📋 Assign Inspection
        </a>

        <a class="btn btn-green" href="/dashboard">
            📊 Monitor Reports
        </a>

        <a class="btn" href="/users">
            👥 Manage Users
        </a>
        """

    elif role == "Worker":

        buttons = """
        <a class="btn" href="/my-assignments">
            📋 View My Assigned Inspections
        </a>

        <a class="btn btn-green" href="/dashboard">
            📊 View My Reports
        </a>
        """

    else:
        buttons = """
        <a class="btn" href="/dashboard">
            📊 Dashboard
        </a>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card" style="text-align:center;">

            <h1>Welcome, {session["name"]}! 👋</h1>

            <p>
                Role:
                <span class="badge">{role}</span>
            </p>

            <div class="info">
                🔐 You can access features based on your assigned role.
            </div>

            {buttons}

        </div>

        <div class="card">

            <h2>🎯 How the System Works</h2>

            <p style="font-size:17px; line-height:2;">
                📋 Assignment →
                👷 Worker Inspection →
                📸 Evidence →
                👨‍💼 Verification →
                🚨 Priority →
                🔧 Action →
                ✅ Resolution
            </p>

        </div>

    </div>
    """


# ============================================================
# USER MANAGEMENT - AUTHORITY
# ============================================================

@app.route("/users", methods=["GET", "POST"])
def users():

    if not authority_required():
        return "⛔ Access Denied."

    message = ""

    if request.method == "POST":

        name = request.form["name"].strip()
        password = request.form["password"]
        role = request.form["role"]

        prefixes = {
            "Authority": "AUTH",
            "Worker": "WORK"
        }

        unique_id = (
            prefixes[role]
            + uuid.uuid4().hex[:6].upper()
        )

        conn = get_connection()

        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            unique_id,
            name,
            generate_password_hash(password),
            role,
            now()
        ))

        conn.commit()
        conn.close()

        message = f"""
        <div class="success">
            ✅ User Created Successfully!<br><br>
            🆔 Unique ID: <b>{unique_id}</b><br>
            👤 Name: <b>{name}</b><br>
            🏷️ Role: <b>{role}</b><br>
            ⚠️ Please give the ID and password securely to the user.
        </div>
        """

    conn = get_connection()

    all_users = conn.execute("""
        SELECT unique_id, name, role
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for user in all_users:
        rows += f"""
        <tr>
            <td>{user["unique_id"]}</td>
            <td>{user["name"]}</td>
            <td>{user["role"]}</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>👥 User Management</h1>

            {message}

            <form method="POST">

                <label>👤 Full Name</label>
                <input name="name" required>

                <label>🔑 Password</label>
                <input type="password"
                       name="password"
                       minlength="6"
                       required>

                <label>🏷️ Role</label>
                <select name="role">
                    <option value="Worker">Worker</option>
                    <option value="Authority">Authority</option>
                </select>

                <button class="btn btn-purple"
                        type="submit">
                    ➕ Create User
                </button>

            </form>

        </div>

        <div class="card">

            <h2>Registered Users</h2>

            <table>
                <tr>
                    <th>Unique ID</th>
                    <th>Name</th>
                    <th>Role</th>
                </tr>

                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# ASSIGN INSPECTION - AUTHORITY
# ============================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not authority_required():
        return "⛔ Access Denied. Only Authority can assign inspections."

    conn = get_connection()

    workers = conn.execute("""
        SELECT * FROM users
        WHERE role = 'Worker'
        ORDER BY name
    """).fetchall()

    message = ""

    if request.method == "POST":

        worker_choice = request.form["worker_id"]
        location = request.form["location"].strip()
        instructions = request.form["instructions"].strip()
        scheduled_date = request.form["scheduled_date"]

        # RANDOM ASSIGNMENT
        if worker_choice == "RANDOM":

            random_worker = conn.execute("""
                SELECT * FROM users
                WHERE role = 'Worker'
                ORDER BY RANDOM()
                LIMIT 1
            """).fetchone()

            if random_worker is None:
                conn.close()
                return "❌ No workers available."

            worker_id = random_worker["id"]
            worker_name = random_worker["name"]

        else:

            worker_id = int(worker_choice)

            selected_worker = conn.execute("""
                SELECT * FROM users WHERE id = ?
            """, (worker_id,)).fetchone()

            worker_name = selected_worker["name"]

        conn.execute("""
            INSERT INTO assignments
            (worker_id, location, instructions,
             scheduled_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            worker_id,
            location,
            instructions,
            scheduled_date,
            "Assigned",
            now()
        ))

        conn.commit()

        message = f"""
        <div class="success">
            ✅ Inspection Assigned Successfully!<br><br>
            👷 Assigned Worker: <b>{worker_name}</b><br>
            📍 Location: <b>{location}</b>
        </div>
        """

    all_assignments = conn.execute("""
        SELECT assignments.*, users.name AS worker_name
        FROM assignments
        JOIN users ON assignments.worker_id = users.id
        ORDER BY assignments.id DESC
    """).fetchall()

    conn.close()

    worker_options = """
        <option value="RANDOM">
            🎲 Random Worker Assignment
        </option>
    """

    for worker in workers:
        worker_options += f"""
        <option value="{worker["id"]}">
            {worker["name"]} ({worker["unique_id"]})
        </option>
        """

    rows = ""

    for assignment in all_assignments:
        rows += f"""
        <tr>
            <td>{assignment["worker_name"]}</td>
            <td>{assignment["location"]}</td>
            <td>{assignment["scheduled_date"] or "-"}</td>
            <td>{assignment["status"]}</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📋 Assign Inspection</h1>

            {message}

            <form method="POST">

                <label>👷 Select Worker</label>

                <select name="worker_id" required>
                    {worker_options}
                </select>

                <label>📍 Inspection Location</label>
                <input name="location"
                       placeholder="Example: Institute Block A"
                       required>

                <label>📅 Scheduled Date</label>
                <input type="date"
                       name="scheduled_date">

                <label>📝 Instructions</label>
                <textarea name="instructions"
                          placeholder="What should the worker inspect?"></textarea>

                <button class="btn btn-purple"
                        type="submit">
                    📋 Assign Inspection
                </button>

            </form>

        </div>

        <div class="card">

            <h2>📋 All Inspection Assignments</h2>

            <table>
                <tr>
                    <th>Worker</th>
                    <th>Location</th>
                    <th>Date</th>
                    <th>Status</th>
                </tr>

                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# WORKER - MY ASSIGNMENTS
# ============================================================

@app.route("/my-assignments")
def my_assignments():

    if not login_required():
        return redirect(url_for("login"))

    if session["role"] != "Worker":
        return "⛔ This page is for Workers only."

    conn = get_connection()

    assignments_list = conn.execute("""
        SELECT * FROM assignments
        WHERE worker_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    rows = ""

    for assignment in assignments_list:

        if assignment["status"] == "Assigned":
            action = f"""
            <a class="btn"
               href="/inspection/{assignment["id"]}">
                🔍 Start Inspection
            </a>
            """

        else:
            action = "✅ Submitted"

        rows += f"""
        <tr>
            <td>{assignment["location"]}</td>
            <td>{assignment["instructions"] or "-"}</td>
            <td>{assignment["scheduled_date"] or "-"}</td>
            <td>
                <span class="badge">
                    {assignment["status"]}
                </span>
            </td>
            <td>{action}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="5" style="text-align:center;">
                📭 No inspections assigned to you yet.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <h1>📋 My Assigned Inspections</h1>

        <div class="info">
            👷 You can only view inspections assigned to your account.
        </div>

        <div class="card">

            <table>
                <tr>
                    <th>📍 Location</th>
                    <th>📝 Instructions</th>
                    <th>📅 Date</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>

                {rows}

            </table>

        </div>

    </div>
    """


# ============================================================
# CONDUCT INSPECTION - WORKER
# ============================================================

@app.route("/inspection/<int:assignment_id>",
           methods=["GET", "POST"])
def inspection(assignment_id):

    if not login_required():
        return redirect(url_for("login"))

    if session["role"] != "Worker":
        return "⛔ Only Workers can conduct inspections."

    conn = get_connection()

    assignment = conn.execute("""
        SELECT * FROM assignments
        WHERE id = ?
        AND worker_id = ?
    """, (
        assignment_id,
        session["user_id"]
    )).fetchone()

    conn.close()

    if assignment is None:
        return "⛔ This inspection is not assigned to you."

    if assignment["status"] != "Assigned":
        return "⚠️ This inspection has already been submitted."

    if request.method == "POST":

        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]
        description = request.form["description"].strip()

        latitude = request.form["latitude"].strip()
        longitude = request.form["longitude"].strip()

        detected_issues = []

        if cleanliness == "No":
            detected_issues.append("Cleanliness")

        if safety == "No":
            detected_issues.append("Safety")

        if facilities == "No":
            detected_issues.append("Facilities")

        photo_filename = ""

        photo = request.files.get("photo")

        if photo and photo.filename:

            if allowed_file(photo.filename):

                extension = (
                    photo.filename.rsplit(".", 1)[1].lower()
                )

                photo_filename = (
                    uuid.uuid4().hex
                    + "."
                    + extension
                )

                photo.save(os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    photo_filename
                ))

            else:
                return "❌ Only PNG, JPG, JPEG or GIF images allowed."

        # If issue exists, photo is strongly required
        if detected_issues and not photo_filename:
            return """
            <h2>⚠️ Evidence Photo Required</h2>
            <p>Please upload a photograph as proof when an issue is found.</p>
            <a href="javascript:history.back()">← Go Back</a>
            """

        conn = get_connection()

        if detected_issues:

            priority = calculate_priority(
                assignment["location"]
            )

            for issue_type in detected_issues:

                conn.execute("""
                    INSERT INTO issues
                    (assignment_id, worker_id, location,
                     issue_type, description, photo,
                     latitude, longitude, priority,
                     created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    assignment_id,
                    session["user_id"],
                    assignment["location"],
                    issue_type,
                    description,
                    photo_filename,
                    latitude,
                    longitude,
                    priority,
                    now(),
                    "Pending Verification"
                ))

        conn.execute("""
            UPDATE assignments
            SET status = 'Submitted'
            WHERE id = ?
        """, (assignment_id,))

        conn.commit()
        conn.close()

        if detected_issues:

            result = f"""
            ⚠️ Issues submitted for Authority Verification.<br><br>
            Issue Types: <b>{", ".join(detected_issues)}</b><br>
            Priority: <b>{priority}</b>
            """

        else:
            result = """
            ✅ Inspection completed successfully.
            No issues were found.
            """

        return f"""
        {STYLE}
        {navbar()}

        <div class="container">

            <div class="card" style="text-align:center;">

                <h1>✅ Inspection Submitted!</h1>

                <div class="info">
                    📍 Location: <b>{assignment["location"]}</b>
                    <br><br>
                    {result}
                </div>

                <a class="btn"
                   href="/my-assignments">
                    📋 My Assignments
                </a>

            </div>

        </div>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>🔍 Conduct Inspection</h1>

            <div class="info">
                📍 Location:
                <b>{assignment["location"]}</b><br><br>

                📝 Instructions:
                {assignment["instructions"] or "General inspection"}
            </div>

            <form method="POST"
                  enctype="multipart/form-data">

                <h3>🧹 Cleanliness</h3>

                <select name="cleanliness">
                    <option value="Yes">Yes - Satisfactory ✅</option>
                    <option value="No">No - Issue Found ❌</option>
                </select>

                <h3>🛡️ Safety</h3>

                <select name="safety">
                    <option value="Yes">Yes - Satisfactory ✅</option>
                    <option value="No">No - Issue Found ❌</option>
                </select>

                <h3>🏢 Facilities</h3>

                <select name="facilities">
                    <option value="Yes">Yes - Satisfactory ✅</option>
                    <option value="No">No - Issue Found ❌</option>
                </select>

                <label>📸 Upload Evidence Photo</label>
                <input type="file"
                       name="photo"
                       accept="image/*">

                <label>📍 Latitude (Optional)</label>
                <input name="latitude"
                       placeholder="Example: 16.5062">

                <label>📍 Longitude (Optional)</label>
                <input name="longitude"
                       placeholder="Example: 80.6480">

                <label>📝 Description</label>

                <textarea
                    name="description"
                    placeholder="Describe any problem found..."></textarea>

                <button class="btn"
                        type="submit">
                    📤 Submit Inspection
                </button>

            </form>

        </div>

    </div>
    """


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_connection()

    if session["role"] == "Worker":

        issues = conn.execute("""
            SELECT issues.*, users.name AS worker_name
            FROM issues
            JOIN users ON issues.worker_id = users.id
            WHERE issues.worker_id = ?
            ORDER BY issues.id DESC
        """, (
            session["user_id"],
        )).fetchall()

    else:

        issues = conn.execute("""
            SELECT issues.*, users.name AS worker_name
            FROM issues
            LEFT JOIN users ON issues.worker_id = users.id
            ORDER BY
                CASE issues.priority
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    ELSE 3
                END,
                issues.id DESC
        """).fetchall()

    total = len(issues)
    pending = sum(
        1 for i in issues
        if i["status"] == "Pending Verification"
    )
    progress = sum(
        1 for i in issues
        if i["status"] == "In Progress"
    )
    resolved = sum(
        1 for i in issues
        if i["status"] == "Resolved"
    )

    conn.close()

    rows = ""

    for issue in issues:

        issue_id = issue["id"]
        status = issue["status"]

        priority_class = (
            "priority-" + issue["priority"].lower()
        )

        if status == "Pending Verification":
            status_class = "status-pending"

            if session["role"] == "Authority":
                action = f"""
                <a class="btn"
                   href="/update/{issue_id}/Reported">
                    ✅ Verify
                </a>
                """
            else:
                action = "⏳ Waiting for Verification"

        elif status == "Reported":

            status_class = "status-reported"

            if session["role"] == "Authority":
                action = f"""
                <a class="btn btn-orange"
                   href="/update/{issue_id}/In%20Progress">
                    🔧 Start Action
                </a>
                """
            else:
                action = "👀 Authority Review"

        elif status == "In Progress":

            status_class = "status-progress"

            if session["role"] == "Authority":
                action = f"""
                <a class="btn btn-green"
                   href="/update/{issue_id}/Resolved">
                    ✅ Resolve
                </a>
                """
            else:
                action = "🔄 Action in Progress"

        else:

            status_class = "status-resolved"
            action = "✅ Completed"

        photo_html = "-"

        if issue["photo"]:
            photo_html = f"""
            <a href="/uploads/{issue["photo"]}"
               target="_blank">
                <img class="photo"
                     src="/uploads/{issue["photo"]}">
            </a>
            """

        location_info = issue["location"]

        if issue["latitude"] and issue["longitude"]:
            location_info += f"""
            <br><small>
            📍 {issue["latitude"]},
            {issue["longitude"]}
            </small>
            """

        rows += f"""
        <tr>
            <td>{issue["worker_name"] or "-"}</td>
            <td>{location_info}</td>
            <td>{issue["issue_type"]}</td>
            <td>
                <span class="badge {priority_class}">
                    {issue["priority"]}
                </span>
            </td>
            <td>{issue["description"] or "-"}</td>
            <td>{photo_html}</td>
            <td>
                <span class="badge {status_class}">
                    {status}
                </span>
            </td>
            <td>{action}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="8" style="text-align:center;">
                🎉 No reports available.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <h1>📊 Smart Monitoring Dashboard</h1>

        <p>
            Welcome, <b>{session["name"]}</b>
            |
            <span class="badge">{session["role"]}</span>
        </p>

        <div class="dashboard-grid">

            <div class="stat-card">
                <div class="stat-number">{total}</div>
                <p>Total Reports</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{pending}</div>
                <p>🟣 Pending Verification</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{progress}</div>
                <p>🟡 In Progress</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{resolved}</div>
                <p>🟢 Resolved</p>
            </div>

        </div>

        <div class="card">

            <h2>🚨 Inspection Reports</h2>

            <div style="overflow-x:auto;">

                <table>

                    <tr>
                        <th>👷 Worker</th>
                        <th>📍 Location</th>
                        <th>Issue</th>
                        <th>Priority</th>
                        <th>Description</th>
                        <th>📸 Evidence</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>

                    {rows}

                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# UPDATE ISSUE STATUS - AUTHORITY ONLY
# ============================================================

@app.route("/update/<int:issue_id>/<status>")
def update_status(issue_id, status):

    if not authority_required():
        return "⛔ Access Denied."

    allowed_statuses = [
        "Reported",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:
        return "❌ Invalid Status."

    conn = get_connection()

    conn.execute("""
        UPDATE issues
        SET status = ?
        WHERE id = ?
    """, (status, issue_id))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ============================================================
# CCTV MONITORING - AUTHORITY ONLY
# ============================================================

@app.route("/cameras", methods=["GET", "POST"])
def cameras():

    if not authority_required():
        return "⛔ Access Denied."

    conn = get_connection()

    message = ""

    if request.method == "POST":

        location = request.form["location"].strip()
        camera_name = request.form["camera_name"].strip()
        stream_url = request.form["stream_url"].strip()

        conn.execute("""
            INSERT INTO cameras
            (location, camera_name, stream_url, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            location,
            camera_name,
            stream_url,
            now()
        ))

        conn.commit()
        message = "✅ CCTV connection added successfully."

    cameras_list = conn.execute("""
        SELECT * FROM cameras
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for camera in cameras_list:
        rows += f"""
        <tr>
            <td>{camera["camera_name"]}</td>
            <td>{camera["location"]}</td>
            <td>
                <a class="btn"
                   href="{camera["stream_url"]}"
                   target="_blank">
                    📹 Open Feed
                </a>
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📹 CCTV Monitoring</h1>

            <div class="info">
                Add only authorized CCTV dashboard or
                browser-compatible stream URLs.
                🔐 Do not expose private camera passwords.
            </div>

            <p class="success">{message}</p>

            <form method="POST">

                <label>📹 Camera Name</label>
                <input name="camera_name" required>

                <label>📍 Location</label>
                <input name="location" required>

                <label>🔗 Authorized CCTV URL</label>
                <input type="url"
                       name="stream_url"
                       placeholder="https://..."
                       required>

                <button class="btn"
                        type="submit">
                    ➕ Add CCTV
                </button>

            </form>

        </div>

        <div class="card">

            <h2>📹 Registered Cameras</h2>

            <table>
                <tr>
                    <th>Camera</th>
                    <th>Location</th>
                    <th>Monitoring</th>
                </tr>

                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# UPLOADED PHOTOS
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# ERROR - FILE TOO LARGE
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return """
    <h2>❌ File Too Large</h2>
    <p>Please upload an image smaller than 10 MB.</p>
    <a href="javascript:history.back()">← Go Back</a>
    """, 413


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    print("========================================")
    print(" SMART INSPECTION SYSTEM IS STARTING...")
    print(" Open: http://127.0.0.1:5000")
    print("========================================")

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
