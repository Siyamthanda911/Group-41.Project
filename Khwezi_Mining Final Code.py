
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import sqlite3
import hashlib
import secrets
import hmac
import os
import re
import smtplib
import time
import tempfile
from email.message import EmailMessage

st.set_page_config(page_title="Khwezi Mining Monitoring", page_icon="⛏️", layout="wide")


# Simple mining-themed design; no embedded images or image encoding.

st.markdown("""
<style>
:root {color-scheme:light;}
[data-testid="stApp"] {background:#f3f7fb;color:#10243b;}
[data-testid="stHeader"] {background:rgba(243,247,251,.9);}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#102439,#081523) !important;}
[data-testid="stSidebar"] * {color:#f4f8fc !important;}
/* Make the Logout button visible without hovering or clicking. */
[data-testid="stSidebar"] .stButton button {
    background:#f4b739 !important;
    color:#102439 !important;
    border:2px solid #ffd879 !important;
    font-weight:800 !important;
    width:100% !important;
    opacity:1 !important;
}
[data-testid="stSidebar"] .stButton button * {color:#102439 !important;}
[data-testid="stSidebar"] .stButton button:hover {background:#ffd879 !important;color:#102439 !important;}

[data-testid="stSidebar"] [data-testid="stRadio"] label {border-radius:10px;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#f4b739;border-radius:9px;padding:5px 8px;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) * {color:#0c2135 !important;font-weight:800;}
[data-testid="stMetric"] {background:#fff;border:1px solid #dae5ee;border-top:4px solid #ffb329;border-radius:15px;padding:15px 17px;box-shadow:0 4px 14px #1d395c12;min-height:115px;}
[data-testid="stMetricLabel"] {color:#465a6b;}
[data-testid="stMetricValue"] {color:#10243b;font-weight:800;}
[data-testid="stDataFrame"] {border-radius:12px;overflow:hidden;border:1px solid #d6e2eb;}
[data-testid="stVerticalBlock"] h1 {color:#10243b;}
.stButton button[kind="primary"] {background:#f3ad24;color:#10243b;border:0;font-weight:800;}
.mine-hero {position:relative;overflow:hidden;border-radius:18px;background:linear-gradient(90deg,#0d2742 0%,#103553 60%,#e7a733 100%);padding:23px 25px;margin-bottom:22px;min-height:155px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 8px 24px #17324e26;}
.mine-hero .tag {color:#ffca60;font-size:12px;font-weight:800;letter-spacing:2px;}
.mine-hero h1 {color:#fff !important;font-size:31px;line-height:1.12;margin:9px 0;}
.mine-hero p {color:#e2ecf6;font-size:13px;margin:0;}
.role-card {padding:13px;border-radius:12px;background:#203b51;margin:9px 0 17px;border-left:4px solid #ffba3e;}
.role-card .small {font-size:11px;color:#a9c1d2 !important;letter-spacing:1px;}
.role-card .role {font-size:17px;font-weight:800;color:#fff !important;}
</style>
""", unsafe_allow_html=True)

def mining_header(title, description):
    st.markdown(f"""<div class="mine-hero"><div><div class="tag">⛏ KHWEZI MINING · OPERATIONS CONTROL</div><h1>{title}</h1><p>{description}</p></div></div>""", unsafe_allow_html=True)

def themed_chart(fig):
    fig.update_layout(template="plotly_white",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#ffffff",font=dict(color="#19364f"),colorway=["#e7a12c","#1686be","#21a76c","#e85e55"],margin=dict(l=18,r=18,t=60,b=20),title_font=dict(size=18,color="#102b46"))
    fig.update_yaxes(gridcolor="#e9eff5")
    return fig

BASE_DIR = Path(__file__).resolve().parent

# START-FRESH MODE: each new Streamlit server launch starts with the original
# sample data and an empty user database. Page refreshes and normal interactions
# on the same running server preserve data and accounts.
@st.cache_resource
def fresh_run_workspace():
    return tempfile.TemporaryDirectory(prefix="khwezi_mining_fresh_launch_")

RUN_DIR = Path(fresh_run_workspace().name)
DATA_FILES = ["workers.csv", "incidents.csv", "equipment.csv", "maintenance.csv"]
DATA_DIR = RUN_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def create_sample_data():
    files = {
        "workers.csv": pd.DataFrame([
            ["W001","Mining","Drill Operator","Day","Yes","Complete","Low",2,0,0,"Low"],
            ["W002","Mining","LHD Operator","Night","No","Complete","High",5,2,1,"High"],
            ["W003","Maintenance","Fitter","Day","Yes","Incomplete","Medium",3,1,0,"Medium"],
            ["W004","Processing","Plant Operator","Night","Yes","Complete","High",4,1,1,"High"],
            ["W005","Safety","Safety Representative","Day","Yes","Complete","Low",1,0,0,"Low"],
        ], columns=["Worker ID","Department","Job Role","Shift","PPE Compliance","Safety Training Status","Fatigue Level","Safety Observations","Near Misses","Previous Incidents","Risk Level"]),
        "incidents.csv": pd.DataFrame([
            ["INC001","2026-08-01","08:15","Day","Pit","Mining","Near Miss","Medium","No","No","Poor visibility","Improve lighting","Closed"],
            ["INC002","2026-08-04","22:30","Night","Workshop","Maintenance","Hand Injury","High","Yes","Yes","Improper tool use","Refresher training","Open"],
            ["INC003","2026-08-08","14:20","Day","Plant","Processing","Slip/Fall","Low","No","No","Spillage","Improve housekeeping","Closed"],
            ["INC004","2026-08-12","01:10","Night","Ramp","Mining","Vehicle Interaction","Critical","No","No","Fatigue","Fatigue management","Under Investigation"],
        ], columns=["Incident ID","Date","Time","Shift","Location","Department","Incident Type","Severity","Injury Status","Lost-time Injury","Cause","Corrective Action","Incident Status"]),
        "equipment.csv": pd.DataFrame([
            ["TRK-001","Haul Truck","CAT",4200,76,4.2,43,"Good","Good","Normal","Available",10,95],
            ["TRK-012","Haul Truck","CAT",6800,104,9.2,48,"Good","Worn","Warning","Due",36,78],
            ["LHD-003","Loader","Sandvik",5100,88,6.4,31,"Good","Good","Normal","Available",20,88],
            ["DRL-004","Drill","Epiroc",7350,97,8.6,29,"Warning","Good","Warning","Overdue",42,72],
            ["CONV-01","Conveyor","OEM",9100,69,3.8,18,"Good","N/A","Normal","Under Maintenance",55,65],
        ], columns=["Equipment ID","Equipment Type","Manufacturer","Operating Hours","Temperature","Vibration","Fuel Consumption","Brake Status","Tyre Status","Engine Status","Maintenance Status","Downtime","Availability"]),
        "maintenance.csv": pd.DataFrame([
            ["TRK-001","2026-07-20","2026-09-20","Completed",10,1],
            ["TRK-012","2026-06-15","2026-09-01","Due",36,3],
            ["LHD-003","2026-08-01","2026-10-01","Completed",20,0],
            ["DRL-004","2026-05-20","2026-08-20","Overdue",42,4],
            ["CONV-01","2026-09-02","2026-09-15","Under Maintenance",55,2],
        ], columns=["Equipment ID","Last Maintenance","Next Maintenance","Maintenance Status","Downtime","Repeated Alerts"])
    }
    for name, df in files.items():
        path = DATA_DIR / name
        if not path.exists():
            df.to_csv(path, index=False)

create_sample_data()

def load_data():
    return (
        pd.read_csv(DATA_DIR / "workers.csv"),
        pd.read_csv(DATA_DIR / "incidents.csv"),
        pd.read_csv(DATA_DIR / "equipment.csv"),
        pd.read_csv(DATA_DIR / "maintenance.csv"),
    )

def save_data(df, filename):
    df.to_csv(DATA_DIR / filename, index=False)

# User accounts are stored separately from the mining CSV data.
USER_DB = RUN_DIR / "khwezi_users_fresh.db"
# Account database and mining edits last only for this Streamlit server run.
ROLES = ["Safety Officer", "Mining Engineer", "Maintenance Engineer", "Manager"]

def db_connection():
    return sqlite3.connect(USER_DB)

def initialize_users():
    # New account database: email is required for every account.
    with db_connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT,
            status TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )""")
        db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
                      ON users(email)""")
        db.execute("""CREATE TABLE IF NOT EXISTS password_resets (
            username TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS account_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            administrator TEXT NOT NULL,
            action TEXT NOT NULL,
            target_username TEXT NOT NULL,
            action_time TEXT DEFAULT CURRENT_TIMESTAMP
        )""")

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 260000)
    return salt + ":" + digest.hex()

def verify_password(password, stored):
    try:
        salt, digest = stored.split(":", 1)
        return hmac.compare_digest(hash_password(password, salt), stored)
    except (ValueError, TypeError):
        return False

def account_count():
    with db_connection() as db:
        return db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

def register_user(username, password, email):
    # The first account is the administrator; later accounts need approval.
    with db_connection() as db:
        if db.execute("SELECT 1 FROM users WHERE username = ? OR lower(email) = ?", (username, email.lower())).fetchone():
            return False
        first = db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        role = "Administrator" if first else None
        status = "Approved" if first else "Pending"
        db.execute("INSERT INTO users (username, password_hash, role, status, email) VALUES (?, ?, ?, ?, ?)",
                   (username, hash_password(password), role, status, email.lower()))
    return True

def authenticate(username, password):
    with db_connection() as db:
        account = db.execute("SELECT password_hash, role, status FROM users WHERE username = ?",
                             (username,)).fetchone()
    if not account or not verify_password(password, account[0]):
        return None, "Incorrect username or password."
    if account[2] == "Deactivated":
        return None, "Your account has been deactivated. Contact the Administrator."
    if account[2] != "Approved":
        return None, "Your account is awaiting Administrator approval."
    return account[1], None

def smtp_settings():
    """Set these as environment variables on the computer running Streamlit."""
    return {
        "host": os.environ.get("KHWEZI_SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("KHWEZI_SMTP_PORT", "587")),
        "user": os.environ.get("KHWEZI_SMTP_USER", ""),
        "password": os.environ.get("KHWEZI_SMTP_PASSWORD", ""),
        "sender": os.environ.get("KHWEZI_SMTP_FROM", os.environ.get("KHWEZI_SMTP_USER", "")),
    }

def send_reset_email(to_email, code):
    cfg = smtp_settings()
    if not cfg["user"] or not cfg["password"] or not cfg["sender"]:
        raise RuntimeError("Email service is not configured")
    message = EmailMessage()
    message["Subject"] = "Khwezi Mining password reset code"
    message["From"] = cfg["sender"]
    message["To"] = to_email
    message.set_content(
        f"Your Khwezi Mining password reset code is: {code}\n\n"
        "This code expires in 15 minutes and can be used once.\n"
        "If you did not request it, ignore this email.\n"
    )
    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as smtp:
        smtp.starttls()
        smtp.login(cfg["user"], cfg["password"])
        smtp.send_message(message)

def request_password_reset(email):
    """Do not disclose whether an email belongs to an account."""
    with db_connection() as db:
        account = db.execute(
            "SELECT username FROM users WHERE lower(email) = ?", (email.lower().strip(),)
        ).fetchone()
        if not account:
            return
        username = account[0]
        # Limit repeated requests for the same account to one per 60 seconds.
        old = db.execute("SELECT expires_at FROM password_resets WHERE username = ?", (username,)).fetchone()
        if old and old[0] > int(time.time()) + 14 * 60:
            return
        code = f"{secrets.randbelow(100000000):08d}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        # Send before replacing the existing code; email errors do not invalidate it.
        send_reset_email(email.lower().strip(), code)
        db.execute("INSERT OR REPLACE INTO password_resets (username, token_hash, expires_at, attempts) VALUES (?, ?, ?, 0)",
                   (username, code_hash, int(time.time()) + 900))

def reset_password(email, code, new_password):
    with db_connection() as db:
        account = db.execute("SELECT username FROM users WHERE lower(email) = ?", (email.lower().strip(),)).fetchone()
        if not account:
            return False
        username = account[0]
        entry = db.execute("SELECT token_hash, expires_at, attempts FROM password_resets WHERE username = ?", (username,)).fetchone()
        if not entry or entry[1] < int(time.time()) or entry[2] >= 5:
            return False
        if not hmac.compare_digest(hashlib.sha256(code.strip().encode()).hexdigest(), entry[0]):
            db.execute("UPDATE password_resets SET attempts = attempts + 1 WHERE username = ?", (username,))
            return False
        db.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hash_password(new_password), username))
        db.execute("DELETE FROM password_resets WHERE username = ?", (username,))
        db.execute("INSERT INTO account_audit (administrator, action, target_username) VALUES (?, ?, ?)",
                   ("Self-service", "Password reset", username))
        return True

initialize_users()

PERMISSIONS = {
    "Administrator":{"Dashboard","Worker Safety","Incidents","Equipment","Maintenance","Risk Assessment","Reports","Manage Users"},
    "Safety Officer":{"Dashboard","Worker Safety","Incidents","Risk Assessment","Reports"},
    "Mining Engineer":{"Dashboard","Worker Safety","Incidents","Equipment","Maintenance","Risk Assessment","Reports"},
    "Maintenance Engineer":{"Dashboard","Equipment","Maintenance","Reports"},
    "Manager":{"Dashboard","Worker Safety","Incidents","Equipment","Maintenance","Risk Assessment","Reports"},
}

def equipment_condition(temperature, vibration):
    if temperature > 100 or vibration > 8:
        return "CRITICAL"
    if 80 <= temperature <= 100 or 5 <= vibration <= 8:
        return "WARNING"
    return "NORMAL"

def calculate_availability(operating_time, downtime):
    total_time = operating_time + downtime
    if total_time <= 0:
        return 0.0
    return (operating_time / total_time) * 100

def risk_classification(likelihood, consequence):
    score = likelihood * consequence
    if score <= 4:
        classification = "Low"
    elif score <= 9:
        classification = "Medium"
    elif score <= 16:
        classification = "High"
    else:
        classification = "Critical"
    return score, classification

def worker_warning(worker):
    warnings = []
    if str(worker["PPE Compliance"]).lower() != "yes":
        warnings.append("PPE non-compliance")
    if str(worker["Safety Training Status"]).lower() != "complete":
        warnings.append("Safety training incomplete")
    if str(worker["Fatigue Level"]).lower() == "high":
        warnings.append("High fatigue level")
    if int(worker["Near Misses"]) >= 2:
        warnings.append("Repeated near misses")
    return "; ".join(warnings) if warnings else "No immediate warning"

def create_alerts(workers, incidents, equipment, maintenance):
    alerts = []

    for _, worker in workers.iterrows():
        message = worker_warning(worker)
        if message != "No immediate warning":
            alerts.append({
                "Category":"Worker Safety",
                "ID":worker["Worker ID"],
                "Level":"WARNING",
                "Message":message,
                "Recommended Action":"Review worker safety conditions and apply appropriate controls."
            })

    for _, incident in incidents.iterrows():
        severity = str(incident["Severity"]).lower()
        if severity in ["high","critical"]:
            alerts.append({
                "Category":"Safety Incident",
                "ID":incident["Incident ID"],
                "Level":severity.upper(),
                "Message":f"{severity.upper()} severity safety incident",
                "Recommended Action":"Investigate the incident and implement the required corrective action."
            })

    for _, machine in equipment.iterrows():
        condition = equipment_condition(float(machine["Temperature"]), float(machine["Vibration"]))
        if condition != "NORMAL":
            alerts.append({
                "Category":"Equipment",
                "ID":machine["Equipment ID"],
                "Level":condition,
                "Message":f'Temperature = {machine["Temperature"]} °C, Vibration = {machine["Vibration"]} mm/s',
                "Recommended Action":"Inspect equipment and initiate appropriate maintenance/safety procedures."
            })
        if float(machine["Availability"]) < 75:
            alerts.append({
                "Category":"Equipment",
                "ID":machine["Equipment ID"],
                "Level":"WARNING",
                "Message":f'Low equipment availability ({machine["Availability"]:.1f}%)',
                "Recommended Action":"Investigate downtime and prioritise maintenance where necessary."
            })

    for _, record in maintenance.iterrows():
        status = str(record["Maintenance Status"]).lower()
        if status == "overdue":
            alerts.append({
                "Category":"Maintenance",
                "ID":record["Equipment ID"],
                "Level":"CRITICAL",
                "Message":"Maintenance overdue",
                "Recommended Action":"Schedule the equipment for maintenance as soon as possible."
            })
        if float(record["Downtime"]) >= 40:
            alerts.append({
                "Category":"Maintenance",
                "ID":record["Equipment ID"],
                "Level":"WARNING",
                "Message":f'Excessive downtime ({record["Downtime"]} hours)',
                "Recommended Action":"Investigate the cause of excessive downtime."
            })
        if int(record["Repeated Alerts"]) >= 3:
            alerts.append({
                "Category":"Maintenance",
                "ID":record["Equipment ID"],
                "Level":"WARNING",
                "Message":f'Repeated equipment alerts ({record["Repeated Alerts"]})',
                "Recommended Action":"Perform a detailed inspection to identify recurring equipment problems."
            })
    return pd.DataFrame(alerts)

for key, value in {"logged_in":False,"username":None,"role":None}.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Block access if the Administrator deactivates or removes a signed-in account.
if st.session_state.logged_in:
    with db_connection() as db:
        current_account = db.execute(
            "SELECT role, status FROM users WHERE username = ?",
            (st.session_state.username,)
        ).fetchone()
    if not current_account or current_account[1] != "Approved":
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.rerun()
    st.session_state.role = current_account[0]

if not st.session_state.logged_in:
    st.markdown("""
    <style>
    [data-testid="stMainBlockContainer"] {max-width: 1050px; padding-top: 3rem;}
    .login-brand {background:linear-gradient(110deg,#102c47 0%,#17415a 65%,#d99b25 100%);border-radius:20px;padding:26px 32px;margin-bottom:26px;box-shadow:0 12px 30px #16334a25;}
    .login-brand .eyebrow {color:#ffd273;font-size:12px;font-weight:800;letter-spacing:2px;}
    .login-brand h1 {color:white !important;font-size:36px;margin:10px 0 8px;}
    .login-brand p {color:#eaf4fc;margin:0;font-size:15px;}
    .login-caption {color:#52677c;font-size:13px;text-align:center;margin-top:16px;}
    </style>
    <div class="login-brand">
      <div class="eyebrow">⛏ KHWEZI MINING · SECURE ACCESS</div>
      <h1>Mining Operations Portal</h1>
      <p>Health, safety and equipment monitoring · Authorised personnel only</p>
    </div>
    """, unsafe_allow_html=True)
    left, middle, right = st.columns([1, 1.5, 1])
    with middle:
        sign_in_tab, register_tab, reset_tab = st.tabs(["🔐 Sign In", "👤 Create Account", "🔑 Forgot Password"])
        with sign_in_tab:
            st.markdown("### Welcome back")
            with st.form("secure_login"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                login = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            if login:
                role, error = authenticate(username.strip(), password)
                if error:
                    st.error(error)
                else:
                    st.session_state.logged_in = True
                    st.session_state.username = username.strip()
                    st.session_state.role = role
                    st.rerun()
        with register_tab:
            st.markdown("### Create your account")
            if account_count() == 0:
                st.info("First-time setup: the first registered account becomes the Administrator. Register the authorised Administrator first.")
            else:
                st.caption("New accounts require Administrator approval before sign-in.")
            with st.form("register_account"):
                new_username = st.text_input("Create Username")
                new_email = st.text_input("Email address", placeholder="name@example.com")
                new_password = st.text_input("Create password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                st.caption("Password: at least 6 characters, including at least one number.")
                create = st.form_submit_button("Create Account", type="primary", use_container_width=True)
            if create:
                if not new_username.strip():
                    st.error("Enter a username.")
                elif not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", new_email.strip()):
                    st.error("Enter a valid email address.")
                elif len(new_password) < 6 or not any(c.isdigit() for c in new_password):
                    st.error("Invalid password: use at least 6 characters and include a number.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif not register_user(new_username.strip(), new_password, new_email.strip()):
                    st.error("That username or email is already registered.")
                else:
                    st.success("Account created! Sign in now." if account_count() == 1 else "Account created! Wait for the Administrator to approve your role before signing in.")
        with reset_tab:
            st.markdown("### Reset your password")
            st.caption("Enter the email address linked to your account. A one-time code will be sent if it is registered.")
            with st.form("request_password_reset"):
                recovery_email = st.text_input("Registered email address")
                request_code = st.form_submit_button("Send Reset Code", type="primary")
            if request_code:
                if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recovery_email.strip()):
                    st.error("Enter a valid email address.")
                else:
                    try:
                        request_password_reset(recovery_email)
                        st.info("If this email is registered, a reset code has been sent. Check your inbox and spam folder.")
                    except (RuntimeError, smtplib.SMTPException, OSError, TimeoutError):
                        st.error("Email could not be sent. Ask the application administrator to check email configuration.")
            with st.form("confirm_password_reset"):
                reset_email = st.text_input("Email address used for the reset")
                reset_code = st.text_input("8-digit reset code")
                replacement = st.text_input("New password", type="password")
                replacement_confirm = st.text_input("Confirm new password", type="password")
                reset_submit = st.form_submit_button("Set New Password", type="primary")
            if reset_submit:
                if len(replacement) < 6 or not any(c.isdigit() for c in replacement):
                    st.error("Password must contain at least 6 characters and one number.")
                elif replacement != replacement_confirm:
                    st.error("Passwords do not match.")
                elif not re.fullmatch(r"\d{8}", reset_code.strip()):
                    st.error("Enter the 8-digit reset code from your email.")
                elif reset_password(reset_email, reset_code, replacement):
                    st.success("Password updated. You can now sign in with your new password.")
                else:
                    st.error("Invalid or expired reset code. Request a new one.")
        st.markdown('<div class="login-caption">🔒 Individual accounts · Role-based access · Khwezi Mining</div>', unsafe_allow_html=True)
    st.stop()

workers, incidents, equipment, maintenance = load_data()
equipment["Availability"] = equipment.apply(
    lambda row: calculate_availability(float(row["Operating Hours"]), float(row["Downtime"])),
    axis=1
)
alerts = create_alerts(workers, incidents, equipment, maintenance)

st.sidebar.markdown("## ⛏️ KHWEZI MINING")
ROLE_ICONS={"Administrator":"🛡️","Safety Officer":"👷","Mining Engineer":"⛏️","Maintenance Engineer":"🛠️","Manager":"📊"}
role_icon=ROLE_ICONS.get(st.session_state.role,"👤")
st.sidebar.markdown(f'<div class="role-card"><div class="small">SIGNED-IN USER</div><div class="role">{role_icon} {st.session_state.username}</div><div>{st.session_state.role}</div><div>🟢 Active session</div></div>',unsafe_allow_html=True)


if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

order = ["Dashboard","Worker Safety","Incidents","Equipment","Maintenance","Risk Assessment","Reports","Manage Users"]
NAV_ICONS={"Dashboard":"🏠","Worker Safety":"👷","Incidents":"🚨","Equipment":"🚛","Maintenance":"🛠️","Risk Assessment":"📋","Reports":"📊","Manage Users":"👥"}
allowed=[item for item in order if item in PERMISSIONS[st.session_state.role]]
selected=st.sidebar.radio("NAVIGATION",allowed,format_func=lambda x:f"{NAV_ICONS[x]}  {x}")
page=selected
st.sidebar.caption("SAFE PEOPLE • RELIABLE EQUIPMENT")

if page == "Dashboard":
    mining_header("Mining Monitoring Dashboard", "Site overview · safety · equipment · production")
    ppe = (workers["PPE Compliance"].astype(str).str.lower() == "yes").mean() * 100
    critical = int((alerts["Level"] == "CRITICAL").sum()) if not alerts.empty else 0
    available = int((equipment["Maintenance Status"].astype(str).str.lower() == "available").sum())
    under = int((equipment["Maintenance Status"].astype(str).str.lower() == "under maintenance").sum())
    high_risk = int(workers["Risk Level"].astype(str).str.lower().isin(["high","critical"]).sum())
    equipment_alerts = int((alerts["Category"] == "Equipment").sum()) if not alerts.empty else 0

    c = st.columns(4)
    c[0].metric("Total Workers", len(workers))
    c[1].metric("Safety Incidents", len(incidents))
    c[2].metric("Near Misses", int(workers["Near Misses"].sum()))
    c[3].metric("PPE Compliance", f"{ppe:.1f}%")

    c = st.columns(4)
    c[0].metric("High-Risk Observations", high_risk)
    c[1].metric("Total Equipment", len(equipment))
    c[2].metric("Available Equipment", available)
    c[3].metric("Under Maintenance", under)

    c = st.columns(3)
    c[0].metric("Equipment Alerts", equipment_alerts)
    c[1].metric("Average Availability", f'{equipment["Availability"].mean():.1f}%')
    c[2].metric("Critical Alerts", critical)

    st.subheader("Active Alerts")
    if not alerts.empty:
        st.dataframe(alerts, use_container_width=True, hide_index=True)
    else:
        st.success("No active alerts.")

    summary = incidents.groupby("Department").size().reset_index(name="Incidents")
    st.plotly_chart(themed_chart(px.bar(summary, x="Department", y="Incidents", title="Safety Incidents by Department")), use_container_width=True)
    st.plotly_chart(themed_chart(px.bar(equipment, x="Equipment ID", y="Availability", title="Equipment Availability (%)")), use_container_width=True)

elif page == "Worker Safety":
    mining_header("Worker Health and Safety Monitoring", "Workforce compliance and safety intelligence")
    view = workers.copy()
    view["System Warning"] = view.apply(worker_warning, axis=1)
    st.dataframe(view, use_container_width=True, hide_index=True)

    st.subheader("Add New Worker")
    with st.form("worker_form"):
        worker_id = st.text_input("Worker ID")
        department = st.text_input("Department")
        job_role = st.text_input("Job Role")
        shift = st.selectbox("Shift", ["Day","Night"])
        ppe_compliance = st.selectbox("PPE Compliance", ["Yes","No"])
        training = st.selectbox("Safety Training Status", ["Complete","Incomplete"])
        fatigue = st.selectbox("Fatigue Level", ["Low","Medium","High"])
        observations = st.number_input("Safety Observations", 0, step=1)
        near_misses = st.number_input("Near Misses", 0, step=1)
        previous_incidents = st.number_input("Previous Incidents", 0, step=1)
        risk_level = st.selectbox("Risk Level", ["Low","Medium","High","Critical"])
        submit_worker = st.form_submit_button("Save Worker", type="primary")

    if submit_worker:
        if not worker_id.strip():
            st.error("Worker ID is required.")
        elif worker_id in workers["Worker ID"].astype(str).values:
            st.error("Worker ID already exists.")
        else:
            new_worker = pd.DataFrame([[
                worker_id, department, job_role, shift, ppe_compliance, training,
                fatigue, int(observations), int(near_misses), int(previous_incidents), risk_level
            ]], columns=workers.columns)
            save_data(pd.concat([workers,new_worker], ignore_index=True), "workers.csv")
            st.success("Worker saved successfully.")
            st.rerun()

elif page == "Incidents":
    mining_header("Safety Incident Database", "Record incidents and identify operational trends")
    search = st.text_input("Search incidents")
    severity_filter = st.selectbox("Filter by severity", ["All","Low","Medium","High","Critical"])
    incident_view = incidents.copy()

    if search:
        mask = incident_view.astype(str).apply(
            lambda column: column.str.contains(search, case=False, na=False)
        ).any(axis=1)
        incident_view = incident_view[mask]

    if severity_filter != "All":
        incident_view = incident_view[
            incident_view["Severity"].astype(str).str.lower() == severity_filter.lower()
        ]

    st.dataframe(incident_view, use_container_width=True, hide_index=True)
    st.subheader("Add New Incident")

    with st.form("incident_form"):
        incident_id = st.text_input("Incident ID")
        incident_date = st.date_input("Date")
        incident_time = st.text_input("Time", value="08:00")
        incident_shift = st.selectbox("Shift", ["Day","Night"])
        incident_location = st.text_input("Location")
        incident_department = st.text_input("Department")
        incident_type = st.text_input("Incident Type")
        severity = st.selectbox("Severity", ["Low","Medium","High","Critical"])
        injury = st.selectbox("Injury Status", ["No","Yes"])
        lost_time = st.selectbox("Lost-time Injury", ["No","Yes"])
        cause = st.text_input("Cause")
        corrective_action = st.text_input("Corrective Action")
        incident_status = st.selectbox("Incident Status", ["Open","Under Investigation","Closed"])
        submit_incident = st.form_submit_button("Save Incident", type="primary")

    if submit_incident:
        if not incident_id.strip():
            st.error("Incident ID is required.")
        elif incident_id in incidents["Incident ID"].astype(str).values:
            st.error("Incident ID already exists.")
        else:
            new_incident = pd.DataFrame([[
                incident_id, str(incident_date), incident_time, incident_shift,
                incident_location, incident_department, incident_type, severity,
                injury, lost_time, cause, corrective_action, incident_status
            ]], columns=incidents.columns)
            save_data(pd.concat([incidents,new_incident], ignore_index=True), "incidents.csv")
            st.rerun()

    incident_counts = incidents["Incident Type"].value_counts().reset_index()
    incident_counts.columns = ["Incident Type","Count"]
    st.plotly_chart(themed_chart(px.bar(incident_counts, x="Incident Type", y="Count", title="Incidents by Type")), use_container_width=True)

elif page == "Equipment":
    mining_header("Equipment Database and Condition Monitoring", "Haul trucks · drills · vibration · temperature")
    equipment_view = equipment.copy()
    equipment_view["Condition"] = equipment_view.apply(
        lambda row: equipment_condition(float(row["Temperature"]), float(row["Vibration"])), axis=1
    )
    st.dataframe(equipment_view, use_container_width=True, hide_index=True)

    equipment_id = st.selectbox("Select Equipment ID", equipment["Equipment ID"].tolist())
    selected_machine = equipment[equipment["Equipment ID"] == equipment_id].iloc[0]
    temperature = float(selected_machine["Temperature"])
    vibration = float(selected_machine["Vibration"])
    condition = equipment_condition(temperature, vibration)

    c = st.columns(4)
    c[0].metric("Temperature", f"{temperature:g} °C")
    c[1].metric("Vibration", f"{vibration:g} mm/s")
    c[2].metric("Availability", f'{selected_machine["Availability"]:.1f}%')
    c[3].metric("Condition", condition)

    if condition == "NORMAL":
        st.success("NORMAL: Equipment is operating within the defined prototype monitoring limits.")
    elif condition == "WARNING":
        st.warning("WARNING: Equipment is approaching or has entered a warning threshold. Inspection and continued monitoring are recommended.")
    else:
        st.error("CRITICAL: Equipment condition exceeds the defined prototype threshold. Immediate inspection is required.")

    st.caption("Educational prototype thresholds: Temperature <80°C Normal, 80–100°C Warning, >100°C Critical; Vibration <5 mm/s Normal, 5–8 mm/s Warning, >8 mm/s Critical.")
    st.plotly_chart(themed_chart(px.bar(equipment, x="Equipment ID", y="Temperature", title="Equipment Temperature (°C)")), use_container_width=True)
    st.plotly_chart(themed_chart(px.bar(equipment, x="Equipment ID", y="Vibration", title="Equipment Vibration (mm/s)")), use_container_width=True)

    st.subheader("Register New Equipment")
    with st.form("new_equipment_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_id = st.text_input("Equipment ID")
            new_type = st.selectbox("Equipment Type", ["Haul Truck", "Loader", "Excavator", "Drill", "Bulldozer", "Crusher", "Conveyor", "Other"])
            new_manufacturer = st.text_input("Manufacturer")
            new_hours = st.number_input("Operating Hours", min_value=0.0, step=1.0)
            new_temp = st.number_input("Temperature (°C)", min_value=0.0, step=1.0)
            new_vibration = st.number_input("Vibration (mm/s)", min_value=0.0, step=0.1)
        with col2:
            new_fuel = st.number_input("Fuel Consumption", min_value=0.0, step=1.0)
            new_brakes = st.selectbox("Brake Status", ["Good", "Warning", "Faulty", "N/A"])
            new_tyres = st.selectbox("Tyre Status", ["Good", "Worn", "Damaged", "N/A"])
            new_engine = st.selectbox("Engine Status", ["Normal", "Warning", "Critical", "N/A"])
            new_maintenance = st.selectbox("Maintenance Status", ["Available", "Due", "Overdue", "Under Maintenance"])
            new_downtime = st.number_input("Downtime (hours)", min_value=0.0, step=1.0)
        save_equipment = st.form_submit_button("Save Equipment", type="primary")

    if save_equipment:
        new_id = new_id.strip()
        if not new_id or not new_manufacturer.strip():
            st.error("Equipment ID and Manufacturer are required.")
        elif new_id in equipment["Equipment ID"].astype(str).values:
            st.error("Equipment ID already exists. Use a unique ID.")
        else:
            availability = calculate_availability(float(new_hours), float(new_downtime))
            new_row = pd.DataFrame([{
                "Equipment ID": new_id,
                "Equipment Type": new_type,
                "Manufacturer": new_manufacturer.strip(),
                "Operating Hours": new_hours,
                "Temperature": new_temp,
                "Vibration": new_vibration,
                "Fuel Consumption": new_fuel,
                "Brake Status": new_brakes,
                "Tyre Status": new_tyres,
                "Engine Status": new_engine,
                "Maintenance Status": new_maintenance,
                "Downtime": new_downtime,
                "Availability": availability
            }])
            save_data(pd.concat([equipment, new_row[equipment.columns]], ignore_index=True), "equipment.csv")
            st.success(f"Equipment {new_id} registered successfully.")
            st.rerun()

elif page == "Maintenance":
    mining_header("Equipment Maintenance Monitoring", "Fleet readiness and maintenance priorities")
    maintenance_view = maintenance.merge(
        equipment[["Equipment ID","Operating Hours","Availability"]],
        on="Equipment ID", how="left"
    )
    st.dataframe(maintenance_view, use_container_width=True, hide_index=True)

    priority = maintenance_view[
        maintenance_view["Maintenance Status"].astype(str).str.lower().isin(["due","overdue","under maintenance"])
        | (maintenance_view["Downtime"] >= 40)
        | (maintenance_view["Repeated Alerts"] >= 3)
        | (maintenance_view["Availability"] < 75)
    ]

    st.subheader("Maintenance Priority Equipment")
    if not priority.empty:
        st.dataframe(priority, use_container_width=True, hide_index=True)
    else:
        st.success("No equipment currently requires priority maintenance.")

    st.plotly_chart(themed_chart(px.bar(maintenance_view, x="Equipment ID", y="Availability", title="Equipment Availability (%)")), use_container_width=True)
    st.info("Availability = Operating Time / (Operating Time + Downtime) × 100.")

elif page == "Risk Assessment":
    mining_header("Mining Risk Assessment", "Likelihood × consequence · risk controls")
    st.write("Risk Score = Likelihood × Consequence")
    c = st.columns(2)
    with c[0]:
        likelihood = st.slider("Likelihood", 1, 5, 3)
    with c[1]:
        consequence = st.slider("Consequence", 1, 5, 3)

    score, classification = risk_classification(likelihood, consequence)
    c = st.columns(2)
    c[0].metric("Risk Score", score)
    c[1].metric("Risk Classification", classification)
    st.write("**1–4 Low | 5–9 Medium | 10–16 High | 17–25 Critical**")

    if classification == "Low":
        st.success("Low risk.")
    elif classification == "Medium":
        st.warning("Medium risk. Monitor the condition and apply appropriate controls.")
    elif classification == "High":
        st.error("HIGH RISK: Corrective action is required.")
    else:
        st.error("CRITICAL RISK: Immediate management action is required.")

elif page == "Reports":
    mining_header("Interactive Mining Data Analysis", "Actionable insights from site records")
    question = st.selectbox("Select a mining question", [
        "How many safety incidents occurred?",
        "Which department has the highest number of incidents?",
        "Which shift records the most incidents?",
        "What percentage of workers comply with PPE requirements?",
        "How many near misses have been recorded?",
        "Which equipment has the highest downtime?",
        "Which equipment has the lowest availability?",
        "Which equipment has the highest vibration?",
        "Which equipment has the highest operating temperature?",
        "What is the average equipment availability?",
        "Which equipment requires maintenance?",
        "How many critical alerts are currently active?"
    ])

    if question == "How many safety incidents occurred?":
        st.success(f"Total safety incidents: {len(incidents)}")
    elif question == "Which department has the highest number of incidents?":
        result = incidents["Department"].value_counts()
        st.success(f"{result.idxmax()} has the highest number of incidents: {result.max()}.")
    elif question == "Which shift records the most incidents?":
        result = incidents["Shift"].value_counts()
        st.success(f"{result.idxmax()} shift records the most incidents: {result.max()}.")
    elif question == "What percentage of workers comply with PPE requirements?":
        result = (workers["PPE Compliance"].astype(str).str.lower() == "yes").mean() * 100
        st.success(f"PPE compliance: {result:.2f}%.")
    elif question == "How many near misses have been recorded?":
        st.success(f'Total near misses: {int(workers["Near Misses"].sum())}.')
    elif question == "Which equipment has the highest downtime?":
        result = equipment.loc[equipment["Downtime"].idxmax()]
        st.success(f'{result["Equipment ID"]} has the highest downtime: {result["Downtime"]} hours.')
    elif question == "Which equipment has the lowest availability?":
        result = equipment.loc[equipment["Availability"].idxmin()]
        st.success(f'{result["Equipment ID"]} has the lowest availability: {result["Availability"]:.2f}%.')
    elif question == "Which equipment has the highest vibration?":
        result = equipment.loc[equipment["Vibration"].idxmax()]
        st.success(f'{result["Equipment ID"]} has the highest vibration: {result["Vibration"]} mm/s.')
    elif question == "Which equipment has the highest operating temperature?":
        result = equipment.loc[equipment["Temperature"].idxmax()]
        st.success(f'{result["Equipment ID"]} has the highest temperature: {result["Temperature"]} °C.')
    elif question == "What is the average equipment availability?":
        st.success(f'Average equipment availability: {equipment["Availability"].mean():.2f}%.')
    elif question == "Which equipment requires maintenance?":
        result = maintenance[
            maintenance["Maintenance Status"].astype(str).str.lower().isin(["due","overdue","under maintenance"])
        ]
        st.dataframe(result, use_container_width=True, hide_index=True)
    elif question == "How many critical alerts are currently active?":
        number = int((alerts["Level"] == "CRITICAL").sum()) if not alerts.empty else 0
        st.success(f"Critical alerts currently active: {number}.")

elif page == "Manage Users":
    mining_header("User Management", "Approve, deactivate, reactivate or remove accounts")
    with db_connection() as db:
        user_table = pd.read_sql_query(
            "SELECT username AS Username, role AS Role, status AS Status FROM users ORDER BY username", db
        )
    st.dataframe(user_table, use_container_width=True, hide_index=True)

    pending = user_table[user_table["Status"] == "Pending"]
    st.subheader("Approve New Accounts")
    if pending.empty:
        st.success("No accounts awaiting approval.")
    else:
        with st.form("approve_user"):
            selected_user = st.selectbox("Pending username", pending["Username"].tolist())
            selected_role = st.selectbox("Assign role", ROLES)
            approve = st.form_submit_button("Approve Account", type="primary")
        if approve:
            with db_connection() as db:
                db.execute("UPDATE users SET role = ?, status = 'Approved' WHERE username = ? AND status = 'Pending'",
                           (selected_role, selected_user))
                db.execute(
                    "INSERT INTO account_audit (administrator, action, target_username) VALUES (?, ?, ?)",
                    (st.session_state.username, "Approved as " + selected_role, selected_user)
                )
            st.success(f"{selected_user} approved as {selected_role}.")
            st.rerun()

    st.subheader("Deactivate or Reactivate Account")
    # Administrators cannot disable their own account.
    other_users = user_table[user_table["Username"] != st.session_state.username]
    eligible = other_users[other_users["Status"].isin(["Approved", "Deactivated"])]
    if eligible.empty:
        st.info("No accounts available to deactivate or reactivate.")
    else:
        with st.form("change_account_status"):
            account_name = st.selectbox("Select account", eligible["Username"].tolist())
            current_status = eligible.loc[eligible["Username"] == account_name, "Status"].iloc[0]
            new_status = "Deactivated" if current_status == "Approved" else "Approved"
            st.caption(f"Current status: {current_status}. Action: {new_status}.")
            update_status = st.form_submit_button(
                "Deactivate Account" if new_status == "Deactivated" else "Reactivate Account"
            )
        if update_status:
            with db_connection() as db:
                db.execute(
                    "UPDATE users SET status = ? WHERE username = ? AND status = ? AND role != 'Administrator'",
                    (new_status, account_name, current_status)
                )
                if db.total_changes:
                    db.execute(
                        "INSERT INTO account_audit (administrator, action, target_username) VALUES (?, ?, ?)",
                        (st.session_state.username, new_status, account_name)
                    )
            st.success(f"{account_name}: {new_status}.")
            st.rerun()

    st.subheader("Remove Account Permanently")
    removable = other_users[other_users["Role"] != "Administrator"]
    if removable.empty:
        st.info("No accounts available for removal.")
    else:
        with st.form("remove_account"):
            remove_name = st.selectbox("Account to remove", removable["Username"].tolist())
            st.warning("This permanently deletes the selected login account. Mining records are not deleted.")
            confirm_removal = st.checkbox(f"I confirm that I want to remove {remove_name}.")
            remove = st.form_submit_button("Remove User")
        if remove:
            if not confirm_removal:
                st.error("Please confirm account removal first.")
            else:
                with db_connection() as db:
                    cursor = db.execute(
                        "DELETE FROM users WHERE username = ? AND role != 'Administrator'",
                        (remove_name,)
                    )
                    if cursor.rowcount:
                        db.execute(
                            "INSERT INTO account_audit (administrator, action, target_username) VALUES (?, ?, ?)",
                            (st.session_state.username, "Removed", remove_name)
                        )
                st.success(f"{remove_name} has been removed.")
                st.rerun()

    with st.expander("Account Activity History"):
        with db_connection() as db:
            history = pd.read_sql_query(
                """SELECT administrator AS Administrator, action AS Action,
                          target_username AS Username, action_time AS Time
                   FROM account_audit ORDER BY id DESC""", db
            )
        st.dataframe(history, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("MINN2020A Computer Programming for Mining | Khwezi Mining Health, Safety and Equipment Monitoring Application | Educational Prototype")
