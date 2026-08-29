from flask import Flask, request, redirect, url_for, session, send_from_directory
import sqlite3
import os
import uuid
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "smart_inspection_system_2026_secure_key"

DATABASE = "inspection.db"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ========================= DATABASE =========================

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def priority(count):
    if count > 3:
        return "High"
    if count >= 2:
        return "Medium"
    return "Low"

def require_login():
    return "user_id" in session

def init_db():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")

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
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        location TEXT NOT NULL,
        assigned_at TEXT NOT NULL,
        status TEXT DEFAULT 'Assigned'
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS cctv_feeds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location TEXT NOT NULL,
        feed_url TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        meeting_url TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")

    defaults = [
        ("ADMIN001", "System Authority", "admin123", "Authority"),
        ("INS001", "Inspection Officer", "inspector123", "Inspector"),
        ("WORK001", "Demo Field Worker", "worker123", "Worker"),
    ]

    for uid, name, password, role in defaults:
        user = conn.execute("SELECT id FROM users WHERE unique_id=?", (uid,)).fetchone()
        if not user:
            conn.execute(
                "INSERT INTO users (unique_id,name,password,role,created_at) VALUES (?,?,?,?,?)",
                (uid, name, generate_password_hash(password), role, now())
            )

    conn.commit()
    conn.close()

init_db()


# ========================= DESIGN =========================

STYLE = """
<style>
*{box-sizing:border-box} body{margin:0;font-family:Arial,sans-serif;background:#f4f7fb;color:#1e293b}
.navbar{background:linear-gradient(90deg,#0f172a,#1d4ed8);color:white;padding:17px 7%;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.navbar a{color:white;text-decoration:none;margin-left:14px;font-weight:bold}
.container{max-width:1200px;margin:auto;padding:30px 20px}
.card{background:white;padding:28px;border-radius:18px;margin-bottom:25px;box-shadow:0 7px 22px rgba(0,0,0,.08)}
.hero{text-align:center;padding:70px 25px;background:linear-gradient(135deg,#eff6ff,#eef2ff)}
.hero h1{font-size:40px;color:#1e3a8a}
.btn{display:inline-block;background:#2563eb;color:white;padding:11px 17px;border-radius:8px;border:none;cursor:pointer;text-decoration:none;margin:4px;font-size:14px}
.btn-green{background:#059669}.btn-purple{background:#7c3aed}.btn-orange{background:#ea580c}.btn-red{background:#dc2626}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}
.feature,.stat-card{background:white;padding:22px;border-radius:14px;box-shadow:0 4px 15px rgba(0,0,0,.06)}
.dashboard-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:18px;margin:20px 0}
.stat-card{text-align:center}.stat-number{font-size:32px;font-weight:bold;color:#2563eb}
input,select,textarea{width:100%;padding:12px;margin-top:7px;margin-bottom:16px;border:1px solid #cbd5e1;border-radius:8px;font-size:15px}
textarea{min-height:100px}h1,h2,h3{color:#1e3a8a}
.info{background:#eff6ff;padding:15px;border-left:5px solid #2563eb;border-radius:7px;margin:15px 0}
.error{color:#dc2626;font-weight:bold}.success{color:#166534;font-weight:bold}
.badge{display:inline-block;padding:6px 10px;border-radius:20px;font-size:12px;font-weight:bold;background:#e0e7ff}
.low{background:#dcfce7;color:#166534}.medium{background:#fef3c7;color:#92400e}.high{background:#fee2e2;color:#991b1b}
table{width:100%;border-collapse:collapse}th{background:#1e3a8a;color:white}th,td{padding:12px;text-align:left;border-bottom:1px solid #e2e8f0}
.evidence-photo{width:100px;height:75px;object-fit:cover;border-radius:8px}
.footer{text-align:center;padding:25px;color:#64748b}
@media(max-width:700px){.navbar{padding:14px}.navbar a{margin-left:7px}.hero h1{font-size:28px}.container{padding:15px}.card{padding:18px}}
</style>
"""

def page(content):
    return STYLE + navbar() + f'<div class="container">{content}</div>'

def navbar():
    if not require_login():
        return ""
    links = '<a href="/home">🏠 Home</a><a href="/dashboard">📊 Dashboard</a>'
    if session.get("role") in ("Worker", "Inspector"):
        links += '<a href="/my-assignments">📌 My Assignments</a><a href="/inspection">📋 Inspection</a>'
    if session.get("role") == "Authority":
        links += '<a href="/users">👥 Users</a><a href="/assignments">🎲 Assign</a><a href="/analytics">📈 Analytics</a><a href="/cctv">📹 CCTV</a><a href="/meetings">🎥 Meetings</a>'
    links += '<a href="/logout">🚪 Logout</a>'
    return f'<div class="navbar"><div><b>🏛️ Smart Monitoring & Inspection</b></div><div>{links}</div></div>'

def priority_html(value):
    cls = {"Low":"low","Medium":"medium","High":"high"}.get(value,"")
    icon = {"Low":"🟢","Medium":"🟡","High":"🔴"}.get(value,"⚪")
    return f'<span class="badge {cls}">{icon} {value}</span>'


# ========================= AUTH =========================

@app.route("/")
def landing():
    return STYLE + """
    <div class="navbar"><b>🏛️ Smart Monitoring & Inspection System</b><a href="/login">🔐 Login</a></div>
    <div class="hero">
      <h1>🏛️ Smart Real-Time Monitoring & Inspection System</h1>
      <p>A centralized platform for inspections, evidence capture, assignments and issue monitoring.</p>
      <br><a class="btn" href="/login">🔐 Login to System</a>
    </div>
    <div class="container"><div class="grid">
      <div class="feature"><h3>📋 Inspections</h3><p>Field staff submit inspection results.</p></div>
      <div class="feature"><h3>📸 Evidence</h3><p>Photo evidence can be uploaded.</p></div>
      <div class="feature"><h3>🎲 Assignment</h3><p>Authority assigns inspection locations.</p></div>
      <div class="feature"><h3>📊 Dashboard</h3><p>Monitor issues and their status.</p></div>
    </div></div>
    """

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        uid = request.form.get("unique_id","").strip().upper()
        password = request.form.get("password","")
        conn = get_connection()
        user = conn.execute("SELECT * FROM users WHERE unique_id=?", (uid,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        error = "❌ Invalid Unique ID or Password."

    return STYLE + f"""
    <div class="navbar"><b>🏛️ Smart Inspection System</b><a href="/">← Back</a></div>
    <div class="container"><div class="card" style="max-width:500px;margin:60px auto">
    <h1 style="text-align:center">🔐 System Login</h1>
    <form method="POST">
    <label>🆔 Unique ID</label><input name="unique_id" required>
    <label>🔑 Password</label><input type="password" name="password" required>
    <button class="btn" style="width:100%">Login</button>
    </form><p class="error">{error}</p>
    </div></div>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

@app.route("/home")
def home():
    if not require_login():
        return redirect(url_for("login"))
    role = session["role"]
    buttons = '<a class="btn btn-green" href="/dashboard">📊 Dashboard</a>'
    if role in ("Worker","Inspector"):
        buttons = '<a class="btn btn-purple" href="/my-assignments">📌 My Assignments</a><a class="btn" href="/inspection">📋 Conduct Inspection</a>' + buttons
    elif role == "Authority":
        buttons = '<a class="btn btn-purple" href="/users">👥 Manage Users</a><a class="btn btn-orange" href="/assignments">🎲 Assign Inspection</a><a class="btn btn-green" href="/analytics">📈 Analytics</a>' + buttons
    return page(f"""
    <div class="card" style="text-align:center"><h1>Welcome, {session['name']}! 👋</h1>
    <p>Role: <span class="badge">{role}</span></p>
    <div class="info">🔐 Role-based access is active.</div>{buttons}</div>
    """)


# ========================= USERS =========================

@app.route("/users", methods=["GET","POST"])
def users():
    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.",403
    message = ""
    conn = get_connection()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            name = request.form["name"].strip()
            password = request.form["password"]
            role = request.form["role"]
            prefix = {"Authority":"AUTH","Inspector":"INS","Worker":"WORK","Officer":"OFF"}[role]
            uid = prefix + uuid.uuid4().hex[:6].upper()
            conn.execute("INSERT INTO users (unique_id,name,password,role,created_at) VALUES (?,?,?,?,?)",
                         (uid,name,generate_password_hash(password),role,now()))
            conn.commit()
            message = f'<div class="info">✅ User created!<br>🆔 <b>{uid}</b><br>👤 {name}<br>🏷️ {role}</div>'
        elif action == "reset":
            uid = request.form["reset_unique_id"].strip().upper()
            new_password = request.form["new_password"]
            result = conn.execute("UPDATE users SET password=? WHERE unique_id=?",
                                  (generate_password_hash(new_password),uid))
            conn.commit()
            message = '<div class="info">✅ Password reset successfully.</div>' if result.rowcount else '<p class="error">❌ User not found.</p>'

    users_list = conn.execute("SELECT unique_id,name,role FROM users ORDER BY id DESC").fetchall()
    conn.close()
    rows = "".join(f"<tr><td>{u['unique_id']}</td><td>{u['name']}</td><td>{u['role']}</td></tr>" for u in users_list)
    return page(f"""
    <div class="card"><h1>👥 User Management</h1>{message}
    <h2>➕ Create User</h2><form method="POST"><input type="hidden" name="action" value="create">
    <label>Name</label><input name="name" required><label>Password</label><input type="password" name="password" required>
    <label>Role</label><select name="role"><option>Worker</option><option>Inspector</option><option>Officer</option><option>Authority</option></select>
    <button class="btn btn-purple">➕ Create User</button></form></div>
    <div class="card"><h2>🔑 Reset Password</h2><form method="POST"><input type="hidden" name="action" value="reset">
    <label>User ID</label><input name="reset_unique_id" required><label>New Password</label><input type="password" name="new_password" required>
    <button class="btn btn-orange">Reset Password</button></form></div>
    <div class="card"><h2>Registered Users</h2><table><tr><th>ID</th><th>Name</th><th>Role</th></tr>{rows}</table></div>
    """)


# ========================= ASSIGNMENTS =========================

@app.route("/assignments", methods=["GET","POST"])
def assignments():
    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.",403

    conn = get_connection()
    message = ""
    workers = conn.execute("SELECT id,name,unique_id FROM users WHERE role IN ('Worker','Inspector')").fetchall()

    if request.method == "POST":
        location = request.form.get("location","").strip()
        if workers and location:
            selected = random.choice(workers)
            conn.execute("INSERT INTO assignments (user_id,location,assigned_at,status) VALUES (?,?,?,?)",
                         (selected["id"],location,now(),"Assigned"))
            conn.commit()
            message = f"<div class='info'>🎲 Inspection assigned!<br>📍 <b>{location}</b><br>👤 <b>{selected['name']}</b> ({selected['unique_id']})</div>"
        else:
            message = "<p class='error'>No Worker/Inspector available.</p>"

    assignment_list = conn.execute("""
        SELECT assignments.*,users.name,users.unique_id FROM assignments
        JOIN users ON assignments.user_id=users.id ORDER BY assignments.id DESC
    """).fetchall()
    conn.close()

    rows = "".join(f"<tr><td>{a['location']}</td><td>{a['name']}</td><td>{a['unique_id']}</td><td>{a['assigned_at']}</td><td>{a['status']}</td></tr>" for a in assignment_list)
    return page(f"""
    <div class="card"><h1>🎲 Automated Inspection Assignment</h1><p>Randomly assign an inspection location to a Worker or Inspector.</p>{message}
    <form method="POST"><label>📍 Location to Inspect</label><input name="location" required>
    <button class="btn btn-purple">🎲 Randomly Assign</button></form></div>
    <div class="card"><h2>📋 Assignment History</h2><div style="overflow-x:auto"><table>
    <tr><th>Location</th><th>Assigned To</th><th>ID</th><th>Time</th><th>Status</th></tr>
    {rows or "<tr><td colspan='5'>No assignments yet.</td></tr>"}</table></div></div>
    """)

@app.route("/my-assignments")
def my_assignments():
    if not require_login():
        return redirect(url_for("login"))
    if session["role"] not in ("Worker","Inspector"):
        return "⛔ Access Denied.",403

    conn = get_connection()
    items = conn.execute("SELECT * FROM assignments WHERE user_id=? ORDER BY id DESC",(session["user_id"],)).fetchall()
    conn.close()

    rows = ""
    for a in items:
        if a["status"] == "Assigned":
            status = '<span class="badge medium">🟡 Assigned</span>'
            action = f'<a class="btn" href="/inspection?assignment_id={a["id"]}">🔍 Start Inspection</a>'
        else:
            status = '<span class="badge low">🟢 Completed</span>'
            action = "✅ Completed"
        rows += f"<tr><td>📍 {a['location']}</td><td>{a['assigned_at']}</td><td>{status}</td><td>{action}</td></tr>"

    return page(f"""
    <div class="card"><h1>📌 My Inspection Assignments</h1>
    <div class="info">👋 These are the inspections assigned to you by the Authority.</div>
    <div style="overflow-x:auto"><table><tr><th>Location</th><th>Assigned Time</th><th>Status</th><th>Action</th></tr>
    {rows or "<tr><td colspan='4' style='text-align:center'>📭 No assignments available.</td></tr>"}
    </table></div></div>
    """)


# ========================= INSPECTION =========================

@app.route("/inspection", methods=["GET","POST"])
def inspection():
    if not require_login():
        return redirect(url_for("login"))
    if session["role"] not in ("Worker","Inspector"):
        return "⛔ Only Workers and Inspectors can conduct inspections.",403

    if request.method == "POST":
        location = request.form["location"].strip()
        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]
        description = request.form.get("description","").strip()
        latitude = request.form.get("latitude","")
        longitude = request.form.get("longitude","")
        assignment_id = request.form.get("assignment_id","")

        photo_name = None
        photo = request.files.get("photo")
        if photo and photo.filename and allowed_file(photo.filename):
            extension = photo.filename.rsplit(".",1)[1].lower()
            photo_name = uuid.uuid4().hex + "." + extension
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"],photo_name))

        detected = []
        if cleanliness == "No": detected.append("Cleanliness")
        if safety == "No": detected.append("Safety")
        if facilities == "No": detected.append("Facilities")

        conn = get_connection()
        for issue_type in detected:
            previous = conn.execute("SELECT COUNT(*) AS count FROM issues WHERE LOWER(location)=LOWER(?)",(location,)).fetchone()["count"]
            p = priority(previous + 1)
            conn.execute("""INSERT INTO issues
            (location,issue_type,description,created_at,status,priority,photo,reporter_id,latitude,longitude,verified)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (location,issue_type,description,now(),"Reported",p,photo_name,session["user_id"],latitude,longitude,0))

        if assignment_id:
            conn.execute("UPDATE assignments SET status='Completed' WHERE id=? AND user_id=?",(assignment_id,session["user_id"]))
        else:
            conn.execute("UPDATE assignments SET status='Completed' WHERE user_id=? AND LOWER(location)=LOWER(?) AND status='Assigned'",
                         (session["user_id"],location))
        conn.commit()
        conn.close()

        result = "⚠️ Issues Reported: " + ", ".join(detected) if detected else "✅ Inspection completed successfully. No issues found!"
        return page(f'<div class="card" style="text-align:center"><h1>✅ Inspection Submitted!</h1><div class="info">📍 <b>{location}</b><br><br>{result}</div><a class="btn" href="/my-assignments">📌 My Assignments</a><a class="btn btn-green" href="/dashboard">Dashboard</a></div>')

    assignment_id = request.args.get("assignment_id","")
    assigned_location = ""
    if assignment_id:
        conn = get_connection()
        assignment = conn.execute("SELECT * FROM assignments WHERE id=? AND user_id=? AND status='Assigned'",
                                  (assignment_id,session["user_id"])).fetchone()
        conn.close()
        if assignment:
            assigned_location = assignment["location"]
        else:
            assignment_id = ""

    return page(f"""
    <div class="card"><h1>📋 Field Inspection & Evidence Capture</h1>
    <form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="assignment_id" value="{assignment_id}">
    <label>📍 Location / Area</label><input name="location" value="{assigned_location}" placeholder="Example: Block A - Second Floor" required>
    <label>🧹 Is the area clean?</label><select name="cleanliness"><option value="Yes">Yes ✅</option><option value="No">No ❌ - Issue Found</option></select>
    <label>🛡️ Is the area safe?</label><select name="safety"><option value="Yes">Yes ✅</option><option value="No">No ❌ - Issue Found</option></select>
    <label>🏢 Are facilities working properly?</label><select name="facilities"><option value="Yes">Yes ✅</option><option value="No">No ❌ - Issue Found</option></select>
    <label>📸 Upload Photo Evidence</label><input type="file" name="photo" accept="image/*">
    <label>Latitude (Optional)</label><input id="latitude" name="latitude">
    <label>Longitude (Optional)</label><input id="longitude" name="longitude">
    <button type="button" class="btn btn-purple" onclick="getLocation()">📍 Get My Location</button>
    <label>📝 Description</label><textarea name="description" placeholder="Describe the issue or observation..."></textarea>
    <button class="btn" type="submit">📤 Submit Inspection</button>
    </form></div>
    <script>
    function getLocation(){{
      if(navigator.geolocation){{
        navigator.geolocation.getCurrentPosition(function(p){{
          document.getElementById('latitude').value=p.coords.latitude;
          document.getElementById('longitude').value=p.coords.longitude;
        }},function(){{alert('Please allow location permission.');}});
      }}else{{alert('Geolocation is not supported.');}}
    }}
    </script>
    """)


# ========================= DASHBOARD =========================

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"],filename)

@app.route("/dashboard")
def dashboard():
    if not require_login():
        return redirect(url_for("login"))

    conn = get_connection()
    if session["role"] == "Authority":
        issues = conn.execute("""SELECT issues.*,users.name AS reporter_name FROM issues
        LEFT JOIN users ON issues.reporter_id=users.id
        ORDER BY CASE issues.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,issues.id DESC""").fetchall()
    else:
        issues = conn.execute("""SELECT issues.*,users.name AS reporter_name FROM issues
        LEFT JOIN users ON issues.reporter_id=users.id WHERE issues.reporter_id=? ORDER BY issues.id DESC""",
        (session["user_id"],)).fetchall()
    conn.close()

    total=len(issues)
    reported=sum(i["status"]=="Reported" for i in issues)
    progress=sum(i["status"]=="In Progress" for i in issues)
    resolved=sum(i["status"]=="Resolved" for i in issues)
    high=sum(i["priority"]=="High" for i in issues)

    rows=""
    for i in issues:
        photo = f'<a href="/uploads/{i["photo"]}" target="_blank"><img class="evidence-photo" src="/uploads/{i["photo"]}"></a>' if i["photo"] else "No Photo"
        location = f"📍 {i['location']}" + (f"<br><small>{i['latitude']}, {i['longitude']}</small>" if i["latitude"] and i["longitude"] else "")
        if session["role"]=="Authority":
            verify = f'<a class="btn btn-purple" href="/verify/{i["id"]}">🔍 Verify</a>' if not i["verified"] else "✅ Verified"
            if i["status"]=="Reported":
                update=f'<a class="btn btn-orange" href="/update/{i["id"]}/In%20Progress">🟡 Start</a>'
            elif i["status"]=="In Progress":
                update=f'<a class="btn btn-green" href="/update/{i["id"]}/Resolved">✅ Resolve</a>'
            else: update="✅ Completed"
            action=verify+"<br>"+update
        else:
            action="🔒 View Only"
        rows += f"<tr><td>{location}</td><td>{i['issue_type']}</td><td>{i['description'] or '-'}</td><td>{priority_html(i['priority'])}</td><td>{photo}</td><td>{i['status']}</td><td>{i['created_at']}</td><td>{action}</td></tr>"

    stats = f"""<div class="dashboard-grid">
    <div class="stat-card"><div class="stat-number">{total}</div>Total Issues</div>
    <div class="stat-card"><div class="stat-number">{reported}</div>🔴 Reported</div>
    <div class="stat-card"><div class="stat-number">{progress}</div>🟡 In Progress</div>
    <div class="stat-card"><div class="stat-number">{resolved}</div>🟢 Resolved</div>
    <div class="stat-card"><div class="stat-number">{high}</div>🔴 High Priority</div></div>"""

    return page(f"""<h1>📊 Real-Time Monitoring Dashboard</h1>{stats}
    <div class="card"><h2>🚨 Inspection Reports</h2><div style="overflow-x:auto"><table>
    <tr><th>Location</th><th>Issue</th><th>Description</th><th>Priority</th><th>Evidence</th><th>Status</th><th>Time</th><th>Action</th></tr>
    {rows or "<tr><td colspan='8'>🎉 No inspection issues found.</td></tr>"}</table></div></div>""")

@app.route("/verify/<int:issue_id>")
def verify_issue(issue_id):
    if not require_login() or session["role"]!="Authority": return "⛔ Access Denied.",403
    conn=get_connection(); conn.execute("UPDATE issues SET verified=1 WHERE id=?",(issue_id,)); conn.commit(); conn.close()
    return redirect(url_for("dashboard"))

@app.route("/update/<int:issue_id>/<status>")
def update_status(issue_id,status):
    if not require_login() or session["role"]!="Authority": return "⛔ Access Denied.",403
    if status not in ("Reported","In Progress","Resolved"): return "❌ Invalid Status.",400
    conn=get_connection(); conn.execute("UPDATE issues SET status=? WHERE id=?",(status,issue_id)); conn.commit(); conn.close()
    return redirect(url_for("dashboard"))


# ========================= ANALYTICS =========================

@app.route("/analytics")
def analytics():
    if not require_login() or session["role"]!="Authority": return "⛔ Access Denied.",403
    conn=get_connection()
    locations=conn.execute("SELECT location,COUNT(*) AS reports FROM issues GROUP BY LOWER(location) ORDER BY reports DESC").fetchall()
    workers=conn.execute("""SELECT users.name,users.unique_id,COUNT(issues.id) AS inspections FROM users
    LEFT JOIN issues ON users.id=issues.reporter_id WHERE users.role IN ('Worker','Inspector')
    GROUP BY users.id ORDER BY inspections DESC""").fetchall()
    conn.close()
    lr="".join(f"<tr><td>{x['location']}</td><td>{x['reports']}</td><td>{priority_html(priority(x['reports']))}</td></tr>" for x in locations)
    wr="".join(f"<tr><td>{x['name']}</td><td>{x['unique_id']}</td><td>{x['inspections']}</td></tr>" for x in workers)
    return page(f"""
    <div class="card"><h1>📈 Inspection Analytics</h1><div class="info">🤖 Repeated reports receive increased priority.</div>
    <h2>🚨 Repeat Problem Locations</h2><table><tr><th>Location</th><th>Reports</th><th>Priority</th></tr>{lr or "<tr><td colspan='3'>No data</td></tr>"}</table></div>
    <div class="card"><h2>👷 Inspection Activity</h2><table><tr><th>Name</th><th>ID</th><th>Reports Submitted</th></tr>{wr or "<tr><td colspan='3'>No data</td></tr>"}</table></div>
    """)


# ========================= CCTV & MEETINGS =========================

@app.route("/cctv",methods=["GET","POST"])
def cctv():
    if not require_login() or session["role"]!="Authority": return "⛔ Access Denied.",403
    conn=get_connection()
    if request.method=="POST":
        conn.execute("INSERT INTO cctv_feeds (location,feed_url,created_at) VALUES (?,?,?)",
                     (request.form["location"].strip(),request.form["feed_url"].strip(),now()))
        conn.commit()
    feeds=conn.execute("SELECT * FROM cctv_feeds ORDER BY id DESC").fetchall(); conn.close()
    rows="".join(f'<tr><td>{f["location"]}</td><td><a class="btn" href="{f["feed_url"]}" target="_blank">📹 Open Feed</a></td></tr>' for f in feeds)
    return page(f"""<div class="card"><h1>📹 CCTV Monitoring</h1><form method="POST">
    <label>Camera Location</label><input name="location" required><label>Authorized Feed URL</label><input type="url" name="feed_url" required>
    <button class="btn">➕ Add Monitoring Link</button></form></div>
    <div class="card"><table><tr><th>Location</th><th>Feed</th></tr>{rows or "<tr><td colspan='2'>No feeds added.</td></tr>"}</table></div>""")

@app.route("/meetings",methods=["GET","POST"])
def meetings():
    if not require_login() or session["role"]!="Authority": return "⛔ Access Denied.",403
    conn=get_connection()
    if request.method=="POST":
        conn.execute("INSERT INTO meetings (title,meeting_url,created_at) VALUES (?,?,?)",
                     (request.form["title"].strip(),request.form["meeting_url"].strip(),now()))
        conn.commit()
    meetings_list=conn.execute("SELECT * FROM meetings ORDER BY id DESC").fetchall(); conn.close()
    rows="".join(f'<tr><td>{m["title"]}</td><td>{m["created_at"]}</td><td><a class="btn btn-purple" href="{m["meeting_url"]}" target="_blank">🎥 Join Meeting</a></td></tr>' for m in meetings_list)
    return page(f"""<div class="card"><h1>🎥 Video Conference Coordination</h1><form method="POST">
    <label>Meeting Title</label><input name="title" required><label>Meeting URL</label><input type="url" name="meeting_url" required>
    <button class="btn btn-purple">➕ Add Meeting</button></form></div>
    <div class="card"><table><tr><th>Meeting</th><th>Created</th><th>Join</th></tr>{rows or "<tr><td colspan='3'>No meetings available.</td></tr>"}</table></div>""")


if __name__ == "__main__":
    print("Smart Real-Time Monitoring & Inspection System")
    print("Open: http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
