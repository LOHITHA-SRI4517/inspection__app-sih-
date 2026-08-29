from flask import Flask, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = "smart_inspection_system_2026_secure_key"

DATABASE = "inspection.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# CREATE / UPDATE DATABASE
# ============================================================

def create_database():

    conn = get_connection()

    # USERS TABLE
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

    # ISSUES TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'Reported',
            priority TEXT DEFAULT 'Low'
        )
    """)

    # Add priority column if an old database already exists
    columns = conn.execute("PRAGMA table_info(issues)").fetchall()
    column_names = [column["name"] for column in columns]

    if "priority" not in column_names:
        conn.execute("""
            ALTER TABLE issues
            ADD COLUMN priority TEXT DEFAULT 'Low'
        """)

    # DEFAULT AUTHORITY ACCOUNT
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
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    # DEFAULT INSPECTOR ACCOUNT
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
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    padding: 18px 8%;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.navbar a {
    color: white;
    text-decoration: none;
    margin-left: 20px;
    font-weight: bold;
}

.container {
    max-width: 1150px;
    margin: auto;
    padding: 30px 20px;
}

.card {
    background: white;
    padding: 30px;
    border-radius: 18px;
    margin-bottom: 25px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.08);
}

.hero {
    text-align: center;
    padding: 70px 30px;
    background: linear-gradient(135deg, #eff6ff, #eef2ff);
}

.hero h1 {
    font-size: 42px;
    color: #1e3a8a;
}

.hero p {
    font-size: 19px;
    line-height: 1.7;
    max-width: 750px;
    margin: 20px auto;
}

.btn {
    display: inline-block;
    background: #2563eb;
    color: white;
    padding: 13px 22px;
    border-radius: 9px;
    border: none;
    cursor: pointer;
    text-decoration: none;
    font-size: 15px;
    margin: 5px;
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

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 20px;
}

.feature {
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 5px 18px rgba(0,0,0,0.07);
}

input, select, textarea {
    width: 100%;
    padding: 13px;
    margin-top: 7px;
    margin-bottom: 17px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 15px;
}

textarea {
    min-height: 100px;
}

h1, h2 {
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
    color: #059669;
    font-weight: bold;
}

.badge {
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

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 18px;
    margin: 25px 0;
}

.stat-card {
    background: white;
    padding: 25px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 5px 18px rgba(0,0,0,0.08);
}

.stat-number {
    font-size: 35px;
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
    padding: 13px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
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
        margin-left: 8px;
        font-size: 13px;
    }

    .hero h1 {
        font-size: 30px;
    }

    .container {
        padding: 15px;
    }
}

</style>
"""


# ============================================================
# NAVIGATION BAR - ROLE BASED
# ============================================================

def navbar():

    if "user_id" not in session:
        return ""

    role = session["role"]

    links = '<a href="/home">🏠 Home</a>'

    # Dashboard only for Authority and Inspector
    if role in ["Authority", "Inspector"]:
        links += '<a href="/dashboard">📊 Dashboard</a>'

    links += '<a href="/logout">🚪 Logout</a>'

    return f"""
    <div class="navbar">
        <div>
            <b>🏛️ Smart Inspection System</b>
        </div>
        <div>
            {links}
        </div>
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
        <div><b>🏛️ Smart Inspection System</b></div>
        <div><a href="/login">🔐 Login</a></div>
    </div>

    <div class="hero">

        <h1>🏛️ Smart Inspection & Monitoring System</h1>

        <p>
            A digital platform designed to simplify inspections,
            report issues efficiently and ensure timely resolution.
        </p>

        <a class="btn" href="/login">🔐 Login to System</a>

    </div>

    <div class="container">

        <div class="card">
            <h2>📌 Problem Statement</h2>
            <p>
                Traditional inspection processes often depend on manual
                records and delayed communication. Our system provides
                a centralized digital platform for reporting and
                monitoring inspection issues.
            </p>
        </div>

        <h2 style="text-align:center;">👥 Who Uses This System?</h2>

        <div class="grid">

            <div class="feature">
                <h3>👨‍💼 Authority</h3>
                <p>Manages users, monitors issues and updates their status.</p>
            </div>

            <div class="feature">
                <h3>🔍 Inspector</h3>
                <p>Conducts inspections and monitors reported issues.</p>
            </div>

            <div class="feature">
                <h3>👷 Worker</h3>
                <p>Conducts and submits inspections without dashboard access.</p>
            </div>

        </div>

    </div>

    <div class="footer">
        Smart Inspection & Monitoring System | Project Expo 2026
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

                <button class="btn" type="submit" style="width:100%;">
                    🔐 Login
                </button>

            </form>

            <p style="text-align:center;">
                <a href="/forgot-password">Forgot Password?</a>
            </p>

            <p class="error">{error}</p>

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
            WHERE unique_id = ? AND LOWER(name) = LOWER(?)
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
            message = "✅ Password reset successfully! You can now login."

        else:
            error = "❌ Unique ID and Name do not match."

        conn.close()

    return f"""
    {STYLE}

    <div class="navbar">
        <b>🏛️ Smart Inspection System</b>
        <a href="/login">← Login</a>
    </div>

    <div class="container">

        <div class="card" style="max-width:500px; margin:50px auto;">

            <h1>🔑 Reset Password</h1>

            <p>Enter your registered details to reset your password.</p>

            <form method="POST">

                <label>🆔 Unique ID</label>
                <input type="text" name="unique_id" required>

                <label>👤 Full Name</label>
                <input type="text" name="name" required>

                <label>🔐 New Password</label>
                <input type="password" name="new_password" required>

                <button class="btn btn-green" type="submit">
                    Reset Password
                </button>

            </form>

            <p class="success">{message}</p>
            <p class="error">{error}</p>

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
# HOME PAGE - ROLE BASED
# ============================================================

@app.route("/home")
def home():

    if "user_id" not in session:
        return redirect(url_for("login"))

    role = session["role"]
    name = session["name"]

    if role == "Authority":

        buttons = """
        <a class="btn btn-purple" href="/users">
            👥 Manage Users
        </a>

        <a class="btn btn-green" href="/dashboard">
            📊 Manage Issues
        </a>
        """

    elif role == "Inspector":

        buttons = """
        <a class="btn" href="/inspection">
            📋 Conduct Inspection
        </a>

        <a class="btn btn-green" href="/dashboard">
            📊 View Dashboard
        </a>
        """

    elif role == "Worker":

        buttons = """
        <a class="btn" href="/inspection">
            📋 Conduct Inspection
        </a>

        <p class="info">
            👷 Workers can submit inspections but do not have
            access to the monitoring dashboard.
        </p>
        """

    else:

        buttons = "<p>No features assigned to this role.</p>"

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card" style="text-align:center;">

            <h1>Welcome, {name}! 👋</h1>

            <p>
                Authorized Role:
                <span class="badge">{role}</span>
            </p>

            <div class="info">
                🔐 Role-Based Access Control is active.
            </div>

            {buttons}

        </div>

        <div class="card">

            <h2>🎯 Inspection Workflow</h2>

            <p style="font-size:18px; line-height:2;">
                🔍 Identify Issue →
                📤 Report Issue →
                📊 Monitor Progress →
                🔧 Take Action →
                ✅ Resolve Issue
            </p>

        </div>

    </div>
    """


# ============================================================
# USER MANAGEMENT - AUTHORITY ONLY
# ============================================================

@app.route("/users", methods=["GET", "POST"])
def users():

    if "user_id" not in session or session["role"] != "Authority":
        return redirect(url_for("home"))

    message = ""

    if request.method == "POST":

        name = request.form["name"].strip()
        password = request.form["password"]
        role = request.form["role"]

        prefixes = {
            "Authority": "AUTH",
            "Inspector": "INS",
            "Worker": "WORK"
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
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

        message = f"""
        <div class="info">
            ✅ <b>User Created Successfully!</b><br><br>
            🆔 Unique ID: <b>{unique_id}</b><br>
            👤 Name: <b>{name}</b><br>
            🏷️ Role: <b>{role}</b><br>
            🔑 Password: <b>{password}</b><br><br>
            ⚠️ Please save these credentials.
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
            <td><span class="badge">{user["role"]}</span></td>
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
                <input type="text" name="name" required>

                <label>🔑 Password</label>
                <input type="password" name="password" required>

                <label>🏷️ Role</label>

                <select name="role">
                    <option value="Inspector">Inspector</option>
                    <option value="Worker">Worker</option>
                    <option value="Authority">Authority</option>
                </select>

                <button class="btn btn-purple" type="submit">
                    ➕ Create User
                </button>

            </form>

        </div>

        <div class="card">

            <h2>👥 Registered Users</h2>

            <div style="overflow-x:auto;">

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

    </div>
    """


# ============================================================
# INSPECTION - INSPECTOR AND WORKER
# ============================================================

@app.route("/inspection", methods=["GET", "POST"])
def inspection():

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only Inspector and Worker can conduct inspection
    if session["role"] not in ["Inspector", "Worker"]:
        return redirect(url_for("home"))

    if request.method == "POST":

        location = request.form["location"].strip()
        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]
        description = request.form["description"].strip()

        detected_issues = []

        if cleanliness == "No":
            detected_issues.append("Cleanliness")

        if safety == "No":
            detected_issues.append("Safety")

        if facilities == "No":
            detected_issues.append("Facilities")

        conn = get_connection()

        for issue in detected_issues:

            # Count previous reports of SAME location + SAME issue
            previous_count = conn.execute("""
                SELECT COUNT(*) AS count
                FROM issues
                WHERE LOWER(location) = LOWER(?)
                AND issue_type = ?
            """, (location, issue)).fetchone()["count"]

            # Include current submission
            total_reports = previous_count + 1

            # AUTOMATIC PRIORITY
            if total_reports > 3:
                priority = "High"
            elif total_reports >= 2:
                priority = "Medium"
            else:
                priority = "Low"

            conn.execute("""
                INSERT INTO issues
                (location, issue_type, description, created_at, status, priority)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                location,
                issue,
                description,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Reported",
                priority
            ))

        conn.commit()
        conn.close()

        if detected_issues:
            result = "⚠️ Issues Reported: " + ", ".join(detected_issues)
        else:
            result = "✅ Inspection completed successfully. No issues found!"

        # Different buttons for Worker and Inspector
        if session["role"] == "Worker":
            next_button = """
            <a class="btn" href="/inspection">
                📋 New Inspection
            </a>
            """
        else:
            next_button = """
            <a class="btn" href="/inspection">
                📋 New Inspection
            </a>

            <a class="btn btn-green" href="/dashboard">
                📊 Dashboard
            </a>
            """

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

                {next_button}

            </div>

        </div>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📋 Conduct Inspection</h1>

            <p>
                Evaluate the location and report any issues found.
            </p>

            <form method="POST">

                <label>📍 Location</label>

                <input
                    type="text"
                    name="location"
                    placeholder="Example: Block A - Second Floor"
                    required
                >

                <label>🧹 Cleanliness</label>

                <select name="cleanliness">
                    <option value="Yes">Good ✅</option>
                    <option value="No">Issue Found ❌</option>
                </select>

                <label>🛡️ Safety</label>

                <select name="safety">
                    <option value="Yes">Good ✅</option>
                    <option value="No">Issue Found ❌</option>
                </select>

                <label>🏢 Facilities</label>

                <select name="facilities">
                    <option value="Yes">Good ✅</option>
                    <option value="No">Issue Found ❌</option>
                </select>

                <label>📝 Additional Description</label>

                <textarea
                    name="description"
                    placeholder="Describe the issue if required..."
                ></textarea>

                <button class="btn" type="submit">
                    📤 Submit Inspection
                </button>

            </form>

        </div>

    </div>
    """


# ============================================================
# DASHBOARD - AUTHORITY AND INSPECTOR ONLY
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    # WORKERS CANNOT ACCESS DASHBOARD
    if session["role"] not in ["Authority", "Inspector"]:
        return redirect(url_for("home"))

    conn = get_connection()

    # High priority first, then Medium, then Low
    issues = conn.execute("""
        SELECT *
        FROM issues
        ORDER BY
            CASE priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            id DESC
    """).fetchall()

    total = conn.execute(
        "SELECT COUNT(*) AS count FROM issues"
    ).fetchone()["count"]

    reported = conn.execute("""
        SELECT COUNT(*) AS count
        FROM issues WHERE status = 'Reported'
    """).fetchone()["count"]

    progress = conn.execute("""
        SELECT COUNT(*) AS count
        FROM issues WHERE status = 'In Progress'
    """).fetchone()["count"]

    resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM issues WHERE status = 'Resolved'
    """).fetchone()["count"]

    conn.close()

    rows = ""

    for issue in issues:

        status = issue["status"]
        issue_id = issue["id"]
        priority = issue["priority"]

        # Priority badge
        if priority == "High":
            priority_display = "🔴 High"
            priority_class = "priority-high"

        elif priority == "Medium":
            priority_display = "🟠 Medium"
            priority_class = "priority-medium"

        else:
            priority_display = "🟢 Low"
            priority_class = "priority-low"

        # Authority actions
        if status == "Reported":

            if session["role"] == "Authority":
                action = f"""
                <a class="btn btn-orange"
                   href="/update/{issue_id}/In%20Progress">
                    🟡 Start Action
                </a>
                """
            else:
                action = "🔒 View Only"

        elif status == "In Progress":

            if session["role"] == "Authority":
                action = f"""
                <a class="btn btn-green"
                   href="/update/{issue_id}/Resolved">
                    ✅ Mark Resolved
                </a>
                """
            else:
                action = "🔄 Action in Progress"

        else:
            action = "✅ Completed"

        rows += f"""
        <tr>
            <td>{issue["location"]}</td>
            <td>{issue["issue_type"]}</td>
            <td>
                <span class="badge {priority_class}">
                    {priority_display}
                </span>
            </td>
            <td>{issue["description"] or "-"}</td>
            <td>{issue["created_at"]}</td>
            <td>{status}</td>
            <td>{action}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="7" style="text-align:center;">
                🎉 No issues have been reported yet.
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
            | Role: <span class="badge">{session["role"]}</span>
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

        </div>

        <div class="card">

            <h2>🚨 Reported Inspection Issues</h2>

            <p>
                🔴 High priority issues are displayed first.
            </p>

            <div style="overflow-x:auto;">

                <table>

                    <tr>
                        <th>📍 Location</th>
                        <th>⚠️ Issue Type</th>
                        <th>🚨 Priority</th>
                        <th>📝 Description</th>
                        <th>📅 Reported Time</th>
                        <th>📌 Status</th>
                        <th>⚙️ Action</th>
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

    if (
        "user_id" not in session
        or session["role"] != "Authority"
    ):
        return redirect(url_for("home"))

    allowed_statuses = [
        "Reported",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:
        return "❌ Invalid status."

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
# RUN FLASK APPLICATION
# ============================================================

if __name__ == "__main__":

    print("========================================")
    print(" Smart Inspection System is Starting...")
    print(" Open: http://127.0.0.1:5000")
    print("========================================")

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )