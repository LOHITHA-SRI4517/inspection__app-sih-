from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory
)
import sqlite3
import os
import uuid
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = "smart_inspection_system_2026_secure_key"

DATABASE = "inspection.db"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

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

def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def calculate_priority(report_count):
    """
    Priority Rules:
    1 report       = Low
    2 or 3 reports = Medium
    More than 3    = High
    """

    if report_count > 3:
        return "High"
    elif report_count >= 2:
        return "Medium"
    else:
        return "Low"


def priority_badge(priority):

    classes = {
        "Low": "priority-low",
        "Medium": "priority-medium",
        "High": "priority-high"
    }

    icons = {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🔴"
    }

    return f"""
    <span class="badge {classes.get(priority, '')}">
        {icons.get(priority, '⚪')} {priority}
    </span>
    """


def require_login():

    if "user_id" not in session:
        return False

    return True


# ============================================================
# DATABASE CREATION AND UPDATES
# ============================================================

def add_column_if_missing(conn, table, column, definition):
    """Prevents errors when upgrading an old database."""

    columns = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    column_names = [column_info["name"] for column_info in columns]

    if column not in column_names:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def create_database():

    conn = get_connection()

    # --------------------------------------------------------
    # USERS TABLE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ISSUES TABLE
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'Reported',
            priority TEXT DEFAULT 'Low',
            photo TEXT,
            reporter_id INTEGER,
            latitude TEXT,
            longitude TEXT,
            verified INTEGER DEFAULT 0
        )
    """)

    # Update old databases automatically
    add_column_if_missing(conn, "issues", "priority",
                          "TEXT DEFAULT 'Low'")
    add_column_if_missing(conn, "issues", "photo",
                          "TEXT")
    add_column_if_missing(conn, "issues", "reporter_id",
                          "INTEGER")
    add_column_if_missing(conn, "issues", "latitude",
                          "TEXT")
    add_column_if_missing(conn, "issues", "longitude",
                          "TEXT")
    add_column_if_missing(conn, "issues", "verified",
                          "INTEGER DEFAULT 0")

    # --------------------------------------------------------
    # INSPECTION ASSIGNMENTS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            status TEXT DEFAULT 'Assigned'
        )
    """)

    # --------------------------------------------------------
    # CCTV FEEDS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cctv_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            feed_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # MEETINGS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            meeting_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # DEFAULT AUTHORITY
    # --------------------------------------------------------

    authority = conn.execute(
        "SELECT * FROM users WHERE unique_id = ?",
        ("ADMIN001",)
    ).fetchone()

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
            current_time()
        ))

    # --------------------------------------------------------
    # DEFAULT INSPECTOR
    # --------------------------------------------------------

    inspector = conn.execute(
        "SELECT * FROM users WHERE unique_id = ?",
        ("INS001",)
    ).fetchone()

    if inspector is None:

        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "INS001",
            "Inspection Officer",
            generate_password_hash("inspector123"),
            "Inspector",
            current_time()
        ))

    # --------------------------------------------------------
    # DEFAULT WORKER
    # --------------------------------------------------------

    worker = conn.execute(
        "SELECT * FROM users WHERE unique_id = ?",
        ("WORK001",)
    ).fetchone()

    if worker is None:

        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "WORK001",
            "Demo Field Worker",
            generate_password_hash("worker123"),
            "Worker",
            current_time()
        ))

    conn.commit()
    conn.close()


create_database()


# ============================================================
# WEBSITE DESIGN
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
    padding: 17px 7%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
}

.navbar a {
    color: white;
    text-decoration: none;
    margin-left: 14px;
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
    border-radius: 18px;
    margin-bottom: 25px;
    box-shadow: 0 7px 22px rgba(0,0,0,0.08);
}

.hero {
    text-align: center;
    padding: 70px 25px;
    background: linear-gradient(135deg, #eff6ff, #eef2ff);
}

.hero h1 {
    font-size: 42px;
    color: #1e3a8a;
}

.btn {
    display: inline-block;
    background: #2563eb;
    color: white;
    padding: 12px 18px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    text-decoration: none;
    margin: 4px;
    font-size: 14px;
}

.btn-green { background: #059669; }
.btn-purple { background: #7c3aed; }
.btn-orange { background: #ea580c; }
.btn-red { background: #dc2626; }

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 18px;
}

.feature {
    background: #ffffff;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.06);
}

input, select, textarea {
    width: 100%;
    padding: 12px;
    margin-top: 7px;
    margin-bottom: 16px;
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

.error {
    color: #dc2626;
    font-weight: bold;
}

.success {
    color: #166534;
    font-weight: bold;
}

.badge {
    padding: 6px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    background: #e0e7ff;
}

.priority-low {
    background: #dcfce7;
    color: #166534;
}

.priority-medium {
    background: #fef3c7;
    color: #92400e;
}

.priority-high {
    background: #fee2e2;
    color: #991b1b;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 18px;
    margin: 20px 0;
}

.stat-card {
    background: white;
    padding: 22px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 5px 18px rgba(0,0,0,0.08);
}

.stat-number {
    font-size: 34px;
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

.evidence-photo {
    width: 100px;
    max-height: 80px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid #cbd5e1;
}

.footer {
    text-align: center;
    padding: 25px;
    color: #64748b;
}

@media(max-width: 700px) {

    .navbar {
        padding: 14px;
    }

    .navbar a {
        margin-left: 7px;
    }

    .hero h1 {
        font-size: 29px;
    }

    .container {
        padding: 15px;
    }

    .card {
        padding: 18px;
    }
}

</style>
"""


# ============================================================
# NAVIGATION
# ============================================================

def navbar():

    if "user_id" not in session:
        return ""

    links = """
        <a href="/home">🏠 Home</a>
        <a href="/dashboard">📊 Dashboard</a>
    """

    if session["role"] in ["Worker", "Inspector"]:
        links += """
            <a href="/inspection">📋 Inspection</a>
        """

    if session["role"] == "Authority":
        links += """
            <a href="/users">👥 Users</a>
            <a href="/assignments">🎲 Assign</a>
            <a href="/analytics">📈 Analytics</a>
            <a href="/cctv">📹 CCTV</a>
            <a href="/meetings">🎥 Meetings</a>
        """

    links += """
        <a href="/logout">🚪 Logout</a>
    """

    return f"""
    <div class="navbar">
        <div><b>🏛️ Smart Monitoring & Inspection</b></div>
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
        <b>🏛️ Smart Monitoring & Inspection System</b>
        <div><a href="/login">🔐 Login</a></div>
    </div>

    <div class="hero">
        <h1>🏛️ Smart Real-Time Monitoring & Inspection System</h1>

        <p style="font-size:18px; max-width:800px; margin:auto;">
            A centralized digital platform for real-time monitoring,
            surprise inspections, evidence capture, smart priority
            detection and inspection management.
        </p>

        <br>
        <a class="btn" href="/login">🔐 Login to System</a>
    </div>

    <div class="container">

        <div class="grid">

            <div class="feature">
                <h3>📱 Mobile Inspection</h3>
                <p>Workers and inspection teams can submit reports from the field.</p>
            </div>

            <div class="feature">
                <h3>📸 Live Evidence</h3>
                <p>Upload photos as evidence for inspection reports.</p>
            </div>

            <div class="feature">
                <h3>📍 Location Monitoring</h3>
                <p>Capture inspection locations and optional GPS coordinates.</p>
            </div>

            <div class="feature">
                <h3>🤖 Smart Priority</h3>
                <p>Repeated issues automatically receive higher priority.</p>
            </div>

            <div class="feature">
                <h3>🎲 Automated Assignment</h3>
                <p>Inspection duties can be randomly assigned to field staff.</p>
            </div>

            <div class="feature">
                <h3>📊 Real-Time Dashboard</h3>
                <p>Authorities can monitor all inspection activities and issues.</p>
            </div>

        </div>

        <div class="card">
            <h2>🎯 Inspection Workflow</h2>
            <p style="font-size:17px; line-height:2;">
                👷 Field Inspection →
                📸 Evidence Capture →
                📤 Issue Report →
                🤖 Smart Priority Detection →
                👨‍💼 Authority Verification →
                🔧 Action →
                ✅ Resolution
            </p>
        </div>

    </div>

    <div class="footer">
        Smart Real-Time Monitoring & Inspection System | Project Prototype 2026
    </div>
    """


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("home"))

    error = ""

    if request.method == "POST":

        unique_id = request.form["unique_id"].strip().upper()
        password = request.form["password"]

        conn = get_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE unique_id = ?",
            (unique_id,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

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

        <div class="card" style="max-width:500px; margin:60px auto;">

            <h1 style="text-align:center;">🔐 System Login</h1>

            <form method="POST">

                <label>🆔 Unique ID</label>
                <input type="text" name="unique_id" required>

                <label>🔑 Password</label>
                <input type="password" name="password" required>

                <button class="btn" style="width:100%;" type="submit">
                    Login
                </button>

            </form>

            <p class="error">{error}</p>

            <p style="text-align:center;">
                <a href="/forgot-password">Forgot Password?</a>
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

    if request.method == "POST":

        unique_id = request.form["unique_id"].strip().upper()

        conn = get_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE unique_id = ?",
            (unique_id,)
        ).fetchone()

        conn.close()

        if user:
            message = """
            <div class="info">
                ✅ Password reset request noted.<br><br>
                Please contact the System Authority to reset your password.
                For this project prototype, the Authority manages password resets.
            </div>
            """
        else:
            message = "<p class='error'>❌ User ID not found.</p>"

    return f"""
    {STYLE}

    <div class="container">
        <div class="card" style="max-width:500px; margin:60px auto;">

            <h1>🔑 Forgot Password</h1>

            <p>
                Enter your Unique ID. Contact the System Authority
                for a secure password reset.
            </p>

            {message}

            <form method="POST">

                <label>🆔 Unique ID</label>
                <input name="unique_id" required>

                <button class="btn" type="submit">
                    Request Password Reset
                </button>

            </form>

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

    if not require_login():
        return redirect(url_for("login"))

    role = session["role"]

    buttons = ""

    if role in ["Worker", "Inspector"]:
        buttons += """
        <a class="btn" href="/inspection">📋 Conduct Inspection</a>
        """

    if role == "Authority":
        buttons += """
        <a class="btn btn-purple" href="/users">👥 Manage Users</a>
        <a class="btn btn-orange" href="/assignments">🎲 Assign Inspection</a>
        <a class="btn btn-green" href="/analytics">📈 View Analytics</a>
        """

    buttons += """
        <a class="btn btn-green" href="/dashboard">📊 Dashboard</a>
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
                🔐 Role-based access is active. Your available features
                depend on your authorized role.
            </div>

            {buttons}

        </div>

        <div class="card">
            <h2>🎯 Smart Inspection Workflow</h2>

            <p style="font-size:17px; line-height:2;">
                🔍 Inspect → 📸 Capture Evidence →
                📤 Report → 🤖 Analyze Priority →
                👨‍💼 Verify → 🔧 Take Action → ✅ Resolve
            </p>
        </div>

    </div>
    """


# ============================================================
# USER MANAGEMENT - AUTHORITY
# ============================================================

@app.route("/users", methods=["GET", "POST"])
def users():

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

    message = ""

    if request.method == "POST":

        action = request.form.get("action", "create")

        # ----------------------------------------------------
        # CREATE USER
        # ----------------------------------------------------

        if action == "create":

            name = request.form["name"].strip()
            password = request.form["password"]
            role = request.form["role"]

            prefixes = {
                "Authority": "AUTH",
                "Inspector": "INS",
                "Worker": "WORK",
                "Officer": "OFF"
            }

            unique_id = prefixes[role] + uuid.uuid4().hex[:6].upper()

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
                current_time()
            ))

            conn.commit()
            conn.close()

            message = f"""
            <div class="info">
                ✅ User created successfully!<br><br>
                🆔 ID: <b>{unique_id}</b><br>
                👤 Name: <b>{name}</b><br>
                🏷️ Role: <b>{role}</b><br>
                🔑 Password: <b>{password}</b>
            </div>
            """

        # ----------------------------------------------------
        # AUTHORITY PASSWORD RESET
        # ----------------------------------------------------

        elif action == "reset":

            user_id = request.form["reset_unique_id"].strip().upper()
            new_password = request.form["new_password"]

            conn = get_connection()

            result = conn.execute("""
                UPDATE users
                SET password = ?
                WHERE unique_id = ?
            """, (
                generate_password_hash(new_password),
                user_id
            ))

            conn.commit()
            conn.close()

            if result.rowcount > 0:
                message = """
                <div class="info">
                    ✅ Password reset successfully.
                </div>
                """
            else:
                message = """
                <p class="error">❌ User ID not found.</p>
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

            <h2>➕ Create New User</h2>

            <form method="POST">

                <input type="hidden" name="action" value="create">

                <label>Full Name</label>
                <input name="name" required>

                <label>Password</label>
                <input type="password" name="password" required>

                <label>Role</label>
                <select name="role">
                    <option value="Worker">Worker</option>
                    <option value="Inspector">Inspector</option>
                    <option value="Officer">Officer</option>
                    <option value="Authority">Authority</option>
                </select>

                <button class="btn btn-purple">➕ Create User</button>

            </form>

        </div>


        <div class="card">

            <h2>🔑 Reset User Password</h2>

            <form method="POST">

                <input type="hidden" name="action" value="reset">

                <label>User Unique ID</label>
                <input name="reset_unique_id" required>

                <label>New Password</label>
                <input type="password" name="new_password" required>

                <button class="btn btn-orange">
                    🔑 Reset Password
                </button>

            </form>

        </div>


        <div class="card">

            <h2>👥 Registered Users</h2>

            <div style="overflow-x:auto;">
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Role</th>
                    </tr>
                    {rows}
                </table>
            </div>

        </div>

    </div>
    """


# ============================================================
# INSPECTION - WORKER AND INSPECTOR
# ============================================================

@app.route("/inspection", methods=["GET", "POST"])
def inspection():

    if not require_login():
        return redirect(url_for("login"))

    if session["role"] not in ["Worker", "Inspector"]:
        return "⛔ Only Workers and Inspectors can conduct inspections."

    if request.method == "POST":

        location = request.form["location"].strip()
        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]
        description = request.form["description"].strip()

        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")

        # ----------------------------------------------------
        # PHOTO UPLOAD
        # ----------------------------------------------------

        photo_name = None
        photo = request.files.get("photo")

        if photo and photo.filename:

            if allowed_file(photo.filename):

                extension = photo.filename.rsplit(".", 1)[1].lower()

                photo_name = (
                    uuid.uuid4().hex
                    + "."
                    + extension
                )

                photo.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        photo_name
                    )
                )

        # ----------------------------------------------------
        # DETECT ISSUES
        # ----------------------------------------------------

        detected_issues = []

        if cleanliness == "No":
            detected_issues.append("Cleanliness")

        if safety == "No":
            detected_issues.append("Safety")

        if facilities == "No":
            detected_issues.append("Facilities")

        conn = get_connection()

        for issue_type in detected_issues:

            # Count previous issues at this location
            previous_count = conn.execute("""
                SELECT COUNT(*) AS count
                FROM issues
                WHERE LOWER(location) = LOWER(?)
            """, (location,)).fetchone()["count"]

            # Add current issue to count
            total_count = previous_count + 1

            priority = calculate_priority(total_count)

            conn.execute("""
                INSERT INTO issues
                (
                    location, issue_type, description,
                    created_at, status, priority,
                    photo, reporter_id, latitude,
                    longitude, verified
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                location,
                issue_type,
                description,
                current_time(),
                "Reported",
                priority,
                photo_name,
                session["user_id"],
                latitude,
                longitude,
                0
            ))

        # Mark assignment completed if available
        conn.execute("""
            UPDATE assignments
            SET status = 'Completed'
            WHERE user_id = ?
            AND LOWER(location) = LOWER(?)
            AND status = 'Assigned'
        """, (
            session["user_id"],
            location
        ))

        conn.commit()
        conn.close()

        if detected_issues:
            result = "⚠️ Issues Reported: " + ", ".join(detected_issues)
        else:
            result = "✅ Inspection completed successfully. No issues found!"

        return f"""
        {STYLE}
        {navbar()}

        <div class="container">
            <div class="card" style="text-align:center;">

                <h1>✅ Inspection Submitted!</h1>

                <div class="info">
                    📍 Location: <b>{location}</b><br><br>
                    {result}
                </div>

                <a class="btn" href="/inspection">📋 New Inspection</a>
                <a class="btn btn-green" href="/dashboard">📊 Dashboard</a>

            </div>
        </div>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📋 Field Inspection & Evidence Capture</h1>

            <p>
                Complete the inspection and upload photo evidence
                when an issue is found.
            </p>

            <form method="POST" enctype="multipart/form-data">

                <label>📍 Location / Area</label>
                <input
                    name="location"
                    placeholder="Example: Block A - Second Floor"
                    required
                >

                <label>🧹 Is the area clean?</label>
                <select name="cleanliness">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">No ❌ - Issue Found</option>
                </select>

                <label>🛡️ Is the area safe?</label>
                <select name="safety">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">No ❌ - Issue Found</option>
                </select>

                <label>🏢 Are facilities working properly?</label>
                <select name="facilities">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">No ❌ - Issue Found</option>
                </select>

                <label>📸 Upload Photo Evidence</label>
                <input
                    type="file"
                    name="photo"
                    accept="image/*"
                >

                <label>📍 GPS Coordinates (Optional)</label>
                <input
                    id="latitude"
                    name="latitude"
                    placeholder="Latitude"
                >

                <input
                    id="longitude"
                    name="longitude"
                    placeholder="Longitude"
                >

                <button
                    type="button"
                    class="btn btn-purple"
                    onclick="getLocation()"
                >
                    📍 Get My Location
                </button>

                <label>📝 Description</label>
                <textarea
                    name="description"
                    placeholder="Describe the issue or observation..."
                ></textarea>

                <button class="btn" type="submit">
                    📤 Submit Inspection
                </button>

            </form>

        </div>

    </div>

    <script>
    function getLocation() {{
        if (navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(
                function(position) {{
                    document.getElementById("latitude").value =
                        position.coords.latitude;

                    document.getElementById("longitude").value =
                        position.coords.longitude;
                }},
                function() {{
                    alert("Unable to get location. Please allow location permission.");
                }}
            );
        }} else {{
            alert("Geolocation is not supported by this browser.");
        }}
    }}
    </script>
    """


# ============================================================
# SERVE UPLOADED PHOTOS
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not require_login():
        return redirect(url_for("login"))

    conn = get_connection()

    # Authority sees everything.
    # Workers and inspectors see their own reports only.
    if session["role"] == "Authority":

        issues = conn.execute("""
            SELECT issues.*, users.name AS reporter_name
            FROM issues
            LEFT JOIN users
            ON issues.reporter_id = users.id
            ORDER BY
                CASE priority
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    ELSE 3
                END,
                issues.id DESC
        """).fetchall()

        filter_sql = ""
        params = ()

    else:

        issues = conn.execute("""
            SELECT issues.*, users.name AS reporter_name
            FROM issues
            LEFT JOIN users
            ON issues.reporter_id = users.id
            WHERE issues.reporter_id = ?
            ORDER BY issues.id DESC
        """, (session["user_id"],)).fetchall()

        filter_sql = " WHERE reporter_id = ? "
        params = (session["user_id"],)

    total = len(issues)
    reported = sum(1 for issue in issues
                   if issue["status"] == "Reported")
    progress = sum(1 for issue in issues
                   if issue["status"] == "In Progress")
    resolved = sum(1 for issue in issues
                   if issue["status"] == "Resolved")
    high = sum(1 for issue in issues
               if issue["priority"] == "High")

    conn.close()

    rows = ""

    for issue in issues:

        issue_id = issue["id"]

        if issue["photo"]:
            photo_html = f"""
            <a href="/uploads/{issue["photo"]}" target="_blank">
                <img
                    class="evidence-photo"
                    src="/uploads/{issue["photo"]}"
                    alt="Evidence"
                >
            </a>
            """
        else:
            photo_html = "No Photo"

        if issue["latitude"] and issue["longitude"]:
            location_html = f"""
            📍 {issue["location"]}<br>
            <small>
                {issue["latitude"]}, {issue["longitude"]}
            </small>
            """
        else:
            location_html = f"📍 {issue['location']}"

        # Authority controls verification and status
        if session["role"] == "Authority":

            if issue["verified"] == 0:
                verification = f"""
                <a class="btn btn-purple"
                   href="/verify/{issue_id}">
                   🔍 Verify
                </a>
                """
            else:
                verification = "✅ Verified"

            status = issue["status"]

            if status == "Reported":
                action = f"""
                <a class="btn btn-orange"
                   href="/update/{issue_id}/In%20Progress">
                   🟡 Start
                </a>
                """

            elif status == "In Progress":
                action = f"""
                <a class="btn btn-green"
                   href="/update/{issue_id}/Resolved">
                   ✅ Resolve
                </a>
                """

            else:
                action = "✅ Completed"

            action = verification + "<br>" + action

        else:
            action = "🔒 View Only"

        anomaly = ""

        if issue["priority"] == "High":
            anomaly = """
            <br><small style="color:#dc2626;">
            ⚠️ Repeat issue detected
            </small>
            """

        rows += f"""
        <tr>
            <td>{location_html}</td>
            <td>{issue["issue_type"]}</td>
            <td>{issue["description"] or "-"}</td>
            <td>{priority_badge(issue["priority"])}{anomaly}</td>
            <td>{photo_html}</td>
            <td>{issue["status"]}</td>
            <td>{issue["created_at"]}</td>
            <td>{action}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="8" style="text-align:center;">
                🎉 No inspection issues found.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <h1>📊 Real-Time Monitoring Dashboard</h1>

        <p>
            Welcome <b>{session["name"]}</b> |
            <span class="badge">{session["role"]}</span>
        </p>

        <div class="dashboard-grid">

            <div class="stat-card">
                <div class="stat-number">{total}</div>
                <p>Total Issues</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{reported}</div>
                <p>🔴 Reported</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{progress}</div>
                <p>🟡 In Progress</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{resolved}</div>
                <p>🟢 Resolved</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{high}</div>
                <p>🔴 High Priority</p>
            </div>

        </div>

        <div class="card">

            <h2>🚨 Inspection Reports</h2>

            <div style="overflow-x:auto;">

                <table>

                    <tr>
                        <th>Location</th>
                        <th>Issue</th>
                        <th>Description</th>
                        <th>Priority</th>
                        <th>Evidence</th>
                        <th>Status</th>
                        <th>Time</th>
                        <th>Action</th>
                    </tr>

                    {rows}

                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# VERIFY EVIDENCE - AUTHORITY
# ============================================================

@app.route("/verify/<int:issue_id>")
def verify_issue(issue_id):

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

    conn = get_connection()

    conn.execute("""
        UPDATE issues
        SET verified = 1
        WHERE id = ?
    """, (issue_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ============================================================
# UPDATE ISSUE STATUS - AUTHORITY
# ============================================================

@app.route("/update/<int:issue_id>/<status>")
def update_status(issue_id, status):

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

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
# RANDOM INSPECTION ASSIGNMENT - AUTHORITY
# ============================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

    message = ""

    conn = get_connection()

    workers = conn.execute("""
        SELECT id, name, unique_id, role
        FROM users
        WHERE role IN ('Worker', 'Inspector')
    """).fetchall()

    if request.method == "POST":

        location = request.form["location"].strip()

        if workers:

            selected = random.choice(workers)

            conn.execute("""
                INSERT INTO assignments
                (user_id, location, assigned_at, status)
                VALUES (?, ?, ?, ?)
            """, (
                selected["id"],
                location,
                current_time(),
                "Assigned"
            ))

            conn.commit()

            message = f"""
            <div class="info">
                🎲 <b>Inspection Assigned Automatically!</b><br><br>
                📍 Location: <b>{location}</b><br>
                👤 Assigned To: <b>{selected["name"]}</b>
                ({selected["unique_id"]})
            </div>
            """

    assignment_list = conn.execute("""
        SELECT assignments.*, users.name, users.unique_id
        FROM assignments
        JOIN users ON assignments.user_id = users.id
        ORDER BY assignments.id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for assignment in assignment_list:
        rows += f"""
        <tr>
            <td>{assignment["location"]}</td>
            <td>{assignment["name"]}</td>
            <td>{assignment["unique_id"]}</td>
            <td>{assignment["assigned_at"]}</td>
            <td>{assignment["status"]}</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>🎲 Automated Inspection Assignment</h1>

            <p>
                The system randomly assigns inspection duties to
                available Workers or Inspectors.
            </p>

            {message}

            <form method="POST">

                <label>📍 Location to Inspect</label>
                <input name="location" required>

                <button class="btn btn-purple">
                    🎲 Randomly Assign Inspector
                </button>

            </form>

        </div>

        <div class="card">

            <h2>📋 Assignment History</h2>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Assigned To</th>
                    <th>ID</th>
                    <th>Time</th>
                    <th>Status</th>
                </tr>
                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# ANALYTICS - AUTHORITY
# ============================================================

@app.route("/analytics")
def analytics():

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

    conn = get_connection()

    locations = conn.execute("""
        SELECT
            location,
            COUNT(*) AS reports
        FROM issues
        GROUP BY LOWER(location)
        ORDER BY reports DESC
    """).fetchall()

    workers = conn.execute("""
        SELECT
            users.name,
            users.unique_id,
            COUNT(issues.id) AS inspections
        FROM users
        LEFT JOIN issues
        ON users.id = issues.reporter_id
        WHERE users.role IN ('Worker', 'Inspector')
        GROUP BY users.id
        ORDER BY inspections DESC
    """).fetchall()

    conn.close()

    location_rows = ""

    for item in locations:

        priority = calculate_priority(item["reports"])

        location_rows += f"""
        <tr>
            <td>{item["location"]}</td>
            <td>{item["reports"]}</td>
            <td>{priority_badge(priority)}</td>
        </tr>
        """

    worker_rows = ""

    for worker in workers:

        worker_rows += f"""
        <tr>
            <td>{worker["name"]}</td>
            <td>{worker["unique_id"]}</td>
            <td>{worker["inspections"]}</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📈 Inspection Analytics & Anomaly Detection</h1>

            <div class="info">
                🤖 Smart Rule: Locations with repeated reports
                automatically receive increased priority.
            </div>

            <h2>🚨 Repeat Problem Locations</h2>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Number of Reports</th>
                    <th>Smart Priority</th>
                </tr>
                {location_rows or "<tr><td colspan='3'>No data available</td></tr>"}
            </table>

        </div>

        <div class="card">

            <h2>👷 Inspection Activity</h2>

            <table>
                <tr>
                    <th>Name</th>
                    <th>ID</th>
                    <th>Reports Submitted</th>
                </tr>
                {worker_rows or "<tr><td colspan='3'>No workers available</td></tr>"}
            </table>

        </div>

    </div>
    """


# ============================================================
# CCTV MODULE - AUTHORITY
# ============================================================

@app.route("/cctv", methods=["GET", "POST"])
def cctv():

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

    conn = get_connection()

    if request.method == "POST":

        location = request.form["location"].strip()
        feed_url = request.form["feed_url"].strip()

        conn.execute("""
            INSERT INTO cctv_feeds
            (location, feed_url, created_at)
            VALUES (?, ?, ?)
        """, (
            location,
            feed_url,
            current_time()
        ))

        conn.commit()

    feeds = conn.execute("""
        SELECT * FROM cctv_feeds
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for feed in feeds:

        rows += f"""
        <tr>
            <td>{feed["location"]}</td>
            <td>
                <a class="btn"
                   href="{feed["feed_url"]}"
                   target="_blank">
                   📹 Open Monitoring Feed
                </a>
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📹 CCTV Monitoring Integration</h1>

            <p>
                Add an authorized CCTV monitoring or camera feed URL.
                Real CCTV integration requires access to actual cameras.
            </p>

            <form method="POST">

                <label>📍 Camera Location</label>
                <input name="location" required>

                <label>🔗 Authorized CCTV / Monitoring URL</label>
                <input type="url" name="feed_url" required>

                <button class="btn">➕ Add Monitoring Link</button>

            </form>

        </div>

        <div class="card">

            <h2>📹 Monitoring Locations</h2>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Feed</th>
                </tr>
                {rows or "<tr><td colspan='2'>No feeds added yet.</td></tr>"}
            </table>

        </div>

    </div>
    """


# ============================================================
# MEETING / VIDEO CONFERENCE MODULE
# ============================================================

@app.route("/meetings", methods=["GET", "POST"])
def meetings():

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

    conn = get_connection()

    if request.method == "POST":

        title = request.form["title"].strip()
        meeting_url = request.form["meeting_url"].strip()

        conn.execute("""
            INSERT INTO meetings
            (title, meeting_url, created_at)
            VALUES (?, ?, ?)
        """, (
            title,
            meeting_url,
            current_time()
        ))

        conn.commit()

    meeting_list = conn.execute("""
        SELECT * FROM meetings
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for meeting in meeting_list:

        rows += f"""
        <tr>
            <td>{meeting["title"]}</td>
            <td>{meeting["created_at"]}</td>
            <td>
                <a class="btn btn-purple"
                   href="{meeting["meeting_url"]}"
                   target="_blank">
                   🎥 Join Meeting
                </a>
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>🎥 Video Conference Coordination</h1>

            <p>
                Add authorized meeting links for coordination between
                Authorities, Project Incharges and Field Staff.
            </p>

            <form method="POST">

                <label>Meeting Title</label>
                <input name="title" required>

                <label>Meeting URL</label>
                <input type="url" name="meeting_url" required>

                <button class="btn btn-purple">
                    ➕ Add Meeting
                </button>

            </form>

        </div>

        <div class="card">

            <h2>🎥 Available Meetings</h2>

            <table>
                <tr>
                    <th>Meeting</th>
                    <th>Created</th>
                    <th>Join</th>
                </tr>
                {rows or "<tr><td colspan='3'>No meetings available.</td></tr>"}
            </table>

        </div>

    </div>
    """


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    print("=" * 55)
    print(" Smart Real-Time Monitoring System is Starting...")
    print(" Open: http://127.0.0.1:5000")
    print("=" * 55)

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
