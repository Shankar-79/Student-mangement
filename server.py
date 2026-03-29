"""
server.py  —  Student MIS Backend  (MySQL / XAMPP edition)
===========================================================
Uses: http.server + mysql.connector + json + hashlib + secrets
NO Flask required.

SETUP:
  1. Start XAMPP → Apache + MySQL
  2. Make sure database 'student_mis' exists with all tables & data
  3. pip install mysql-connector-python
  4. python server.py
  5. Open http://localhost:8000

Update DB_CONFIG below if your MySQL password is set.
"""

import json
import hashlib
import os
import mimetypes
import secrets
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Install check ─────────────────────────────────────────────
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    print("\n  ERROR: mysql-connector-python is not installed.")
    print("  Fix:   pip install mysql-connector-python\n")
    raise SystemExit(1)

# ══════════════════════════════════════════════════════════════
# CONFIG  —  update password if you set one in XAMPP
# ══════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "",           # XAMPP default = empty string
    "database": "student_mis",
    "charset":  "utf8mb4",
    "autocommit": False,
}

PORT     = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════════
# DATABASE HELPERS
# ══════════════════════════════════════════════════════════════
def get_db():
    """Open and return a new MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)

def qrows(cursor):
    """Return all rows as a list of plain dicts."""
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def qrow(cursor):
    """Return one row as a plain dict, or None."""
    cols = [d[0] for d in cursor.description]
    row  = cursor.fetchone()
    return dict(zip(cols, row)) if row else None

def scalar(cursor):
    """Return the first column of the first row."""
    row = cursor.fetchone()
    return row[0] if row else 0

def hash_pw(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

# ══════════════════════════════════════════════════════════════
# IN-MEMORY SESSION STORE
# ══════════════════════════════════════════════════════════════
_sessions = {}   # token -> {user_id, role, name, roll, _token}

def session_create(data):
    tok = secrets.token_hex(32)
    _sessions[tok] = dict(data)
    return tok

def session_get(tok):
    return _sessions.get(tok or "")

def session_delete(tok):
    _sessions.pop(tok or "", None)

# ══════════════════════════════════════════════════════════════
# STARTUP DB CHECK
# ══════════════════════════════════════════════════════════════
def check_db():
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM admins")
        count = cur.fetchone()[0]
        cur.close(); conn.close()
        print(f"  OK  MySQL connected  —  student_mis  ({count} admin record(s))")
    except MySQLError as e:
        print(f"\n  FAILED  MySQL error: {e}")
        print("  Check:")
        print("    * XAMPP MySQL is running")
        print("    * Database 'student_mis' exists with all tables")
        print("    * DB_CONFIG credentials match your XAMPP setup\n")
        raise SystemExit(1)

# ══

# ── Ping (session verify) ─────────────────────────────────────
def api_ping(body, qs, session):
    return 200, {"ok": True, "role": session.get("role")}


def api_login(body, qs):
    try:
        data = json.loads(body)
    except Exception:
        return 400, {"ok": False, "error": "Bad request body"}

    role  = data.get("role", "student").strip()
    uname = data.get("username", "").strip()
    pw    = data.get("password", "").strip()

    if not uname or not pw:
        return 400, {"ok": False, "error": "Username and password are required"}

    pw_hash = pw
    conn    = get_db()
    cur     = conn.cursor()
    try:
        if role == "admin":
            cur.execute(
                "SELECT * FROM admins WHERE username=%s AND password=%s",
                (uname, pw_hash)
            )
            r = qrow(cur)
            if r:
                tok = session_create({"user_id": r["id"], "role": "admin",
                                      "name": r["name"], "roll": ""})
                return 200, {"ok": True, "token": tok, "role": "admin", "name": r["name"]}
        else:
            cur.execute(
                "SELECT * FROM students WHERE (email=%s OR roll_no=%s) AND password=%s",
                (uname, uname, pw_hash)
            )
            r = qrow(cur)
            if r:
                tok = session_create({"user_id": r["id"], "role": "student",
                                      "name": r["name"], "roll": r["roll_no"]})
                return 200, {"ok": True, "token": tok, "role": "student",
                             "name": r["name"], "roll": r["roll_no"], "id": r["id"]}

        return 401, {"ok": False, "error": "Invalid username or password"}

    except MySQLError as e:
        print(f"  LOGIN DB ERROR: {e}")
        return 500, {"ok": False, "error": "Database error during login"}
    finally:
        cur.close(); conn.close()


def api_logout(body, qs, session):
    session_delete(session.get("_token", ""))
    return 200, {"ok": True}

def api_dashboard(body, qs, session):
    sid  = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM students WHERE id=%s", (sid,))
        student = qrow(cur)

        cur.execute("SELECT * FROM notices ORDER BY created_at DESC LIMIT 5")
        notices = qrows(cur)

        cur.execute("""
            SELECT a.*, s.name AS subject_name
            FROM attendance a
            JOIN subjects s ON s.id = a.subject_id
            WHERE a.student_id = %s
        """, (sid,))
        att = qrows(cur)

        cur.execute("""
            SELECT m.*, s.name AS subject_name
            FROM marks m
            JOIN subjects s ON s.id = m.subject_id
            WHERE m.student_id = %s
            ORDER BY m.exam_date DESC
        """, (sid,))
        mks = qrows(cur)

        cur.execute("""
            SELECT COUNT(*) AS cnt,
                   COALESCE(SUM(amount), 0) AS total
            FROM payments
            WHERE student_id = %s AND status != 'Paid'
        """, (sid,))
        pending = qrow(cur)

        total_c  = sum(a["total_classes"] for a in att)
        attended = sum(a["attended"]      for a in att)
        att_pct  = round(attended / total_c * 100, 1) if total_c else 0

        return 200, {
            "student":      student,
            "notices":      notices,
            "attendance":   att,
            "marks":        mks,
            "pending_fees": pending,
            "att_pct":      att_pct,
        }
    finally:
        cur.close(); conn.close()

def api_profile_get(body, qs, session):
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM students WHERE id=%s", (session["user_id"],))
        return 200, qrow(cur)
    finally:
        cur.close(); conn.close()

def api_profile_update(body, qs, session):
    d   = json.loads(body)
    sid = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE students SET name=%s, email=%s, phone=%s, dob=%s, address=%s WHERE id=%s",
            (d["name"], d["email"], d.get("phone",""),
             d.get("dob","") or None, d.get("address",""), sid)
        )
        conn.commit()
        for s in _sessions.values():
            if s.get("user_id") == sid:
                s["name"] = d["name"]
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()


def api_payments(body, qs, session):
    sid  = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM payments WHERE student_id=%s ORDER BY created_at DESC", (sid,))
        pmts = qrows(cur)

        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN status='Paid'  THEN amount END), 0) AS paid,
                COALESCE(SUM(CASE WHEN status!='Paid' THEN amount END), 0) AS due,
                COALESCE(SUM(amount), 0) AS total
            FROM payments WHERE student_id=%s
        """, (sid,))
        summary = qrow(cur)

        return 200, {"payments": pmts, "summary": summary}
    finally:
        cur.close(); conn.close()

def api_admin_dashboard(body, qs, session):
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM students ORDER BY name")
        students = qrows(cur)

        cur.execute("SELECT * FROM subjects ORDER BY name")
        subjects = qrows(cur)

        cur.execute("""
            SELECT n.*, a.name AS admin_name
            FROM notices n
            LEFT JOIN admins a ON a.id = n.admin_id
            ORDER BY n.created_at DESC
        """)
        notices = qrows(cur)

        cur.execute("""
            SELECT p.*, s.name AS student_name, s.roll_no
            FROM payments p
            JOIN students s ON s.id = p.student_id
            ORDER BY p.created_at DESC
        """)
        payments = qrows(cur)

        cur.execute("""
            SELECT m.*, s.name AS student_name, sub.name AS subject_name
            FROM marks m
            JOIN students s   ON s.id  = m.student_id
            JOIN subjects sub ON sub.id = m.subject_id
            ORDER BY m.created_at DESC LIMIT 100
        """)
        marks_all = qrows(cur)

        cur.execute("""
            SELECT a.*, s.name AS student_name, sub.name AS subject_name
            FROM attendance a
            JOIN students s   ON s.id  = a.student_id
            JOIN subjects sub ON sub.id = a.subject_id
            ORDER BY a.updated_at DESC LIMIT 100
        """)
        att_all = qrows(cur)

        cur.execute("SELECT COUNT(*) FROM students");             sc = scalar(cur)
        cur.execute("SELECT COUNT(*) FROM payments WHERE status!='Paid'"); pc = scalar(cur)
        cur.execute("SELECT COUNT(*) FROM notices");              nc = scalar(cur)
        cur.execute("SELECT COUNT(*) FROM subjects");             uc = scalar(cur)

        return 200, {
            "students":   students,
            "subjects":   subjects,
            "notices":    notices,
            "payments":   payments,
            "marks":      marks_all,
            "attendance": att_all,
            "stats": {"students": sc, "pending": pc, "notices": nc, "subjects": uc},
        }
    finally:
        cur.close(); conn.close()


def api_student_add(body, qs, session):
    d = json.loads(body)
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO students
                (roll_no,name,email,password,phone,branch,year,section,dob,address)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            d["roll_no"], d["name"], d["email"], hash_pw(d["password"]),
            d.get("phone",""), d["branch"], int(d.get("year",1)),
            d.get("section","A"), d.get("dob","") or None, d.get("address","")
        ))
        conn.commit()
        return 200, {"ok": True}
    except MySQLError:
        conn.rollback()
        return 400, {"ok": False, "error": "Roll number or email already exists"}
    finally:
        cur.close(); conn.close()

def api_student_update(body, qs, session):
    d   = json.loads(body)
    sid = int(qs.get("id",["0"])[0])
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE students
            SET name=%s,email=%s,phone=%s,branch=%s,year=%s,section=%s,dob=%s,address=%s
            WHERE id=%s
        """, (
            d["name"], d["email"], d.get("phone",""), d["branch"],
            int(d.get("year",1)), d.get("section","A"),
            d.get("dob","") or None, d.get("address",""), sid
        ))
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()

def api_student_delete(body, qs, session):
    sid  = int(qs.get("id",["0"])[0])
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM students WHERE id=%s", (sid,))
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()


def api_marks_add(body, qs, session):
    d = json.loads(body)
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO marks
                (student_id,subject_id,exam_type,marks,max_marks,exam_date)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            int(d["student_id"]), int(d["subject_id"]),
            d.get("exam_type","Mid-Term"), float(d["marks"]),
            float(d.get("max_marks",100)), d.get("exam_date","") or None
        ))
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()

def api_marks_delete(body, qs, session):
    mid  = int(qs.get("id",["0"])[0])
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM marks WHERE id=%s", (mid,))
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()


def api_attendance_add(body, qs, session):
    d     = json.loads(body)
    sid   = int(d["student_id"])
    subid = int(d["subject_id"])
    tot   = int(d["total_classes"])
    att   = int(d["attended"])
    mon   = d.get("month_year","")
    conn  = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id FROM attendance
            WHERE student_id=%s AND subject_id=%s AND month_year=%s
        """, (sid, subid, mon))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE attendance
                SET total_classes=%s, attended=%s, updated_at=NOW()
                WHERE id=%s
            """, (tot, att, existing[0]))
        else:
            cur.execute("""
                INSERT INTO attendance
                    (student_id,subject_id,total_classes,attended,month_year)
                VALUES (%s,%s,%s,%s,%s)
            """, (sid, subid, tot, att, mon))

        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()

def api_attendance_delete(body, qs, session):
    aid  = int(qs.get("id",["0"])[0])
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM attendance WHERE id=%s", (aid,))
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()


def api_notice_add(body, qs, session):
    d    = json.loads(body)
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO notices (title,body,category,admin_id) VALUES (%s,%s,%s,%s)",
            (d["title"], d["body"], d.get("category","General"), session["user_id"])
        )
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()

def api_notice_delete(body, qs, session):
    nid  = int(qs.get("id",["0"])[0])
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM notices WHERE id=%s", (nid,))
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()


def api_payment_add(body, qs, session):
    d    = json.loads(body)
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO payments
                (student_id,description,amount,due_date,paid_date,status,receipt_no)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            int(d["student_id"]), d["description"], float(d["amount"]),
            d.get("due_date","") or None, d.get("paid_date","") or None,
            d.get("status","Pending"), d.get("receipt_no","")
        ))
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()

def api_payment_update(body, qs, session):
    pid  = int(qs.get("id",["0"])[0])
    d    = json.loads(body)
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE payments SET status=%s, paid_date=%s, receipt_no=%s WHERE id=%s",
            (d["status"], d.get("paid_date","") or None,
             d.get("receipt_no",""), pid)
        )
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()

def api_payment_delete(body, qs, session):
    pid  = int(qs.get("id",["0"])[0])
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM payments WHERE id=%s", (pid,))
        conn.commit()
        return 200, {"ok": True}
    finally:
        cur.close(); conn.close()

ROUTES = {
    ("POST", "/api/login"):                    (api_login,             False, None),
    ("POST", "/api/logout"):                   (api_logout,            True,  None),
    ("GET",  "/api/ping"):                     (api_ping,              True,  "student"),
    ("GET",  "/api/admin/ping"):               (api_ping,              True,  "admin"),
    ("GET",  "/api/dashboard"):                (api_dashboard,         True,  "student"),
    ("GET",  "/api/profile"):                  (api_profile_get,       True,  "student"),
    ("POST", "/api/profile"):                  (api_profile_update,    True,  "student"),
    ("GET",  "/api/payments"):                 (api_payments,          True,  "student"),
    ("GET",  "/api/admin/dashboard"):          (api_admin_dashboard,   True,  "admin"),
    ("POST", "/api/admin/student/add"):        (api_student_add,       True,  "admin"),
    ("POST", "/api/admin/student/update"):     (api_student_update,    True,  "admin"),
    ("POST", "/api/admin/student/delete"):     (api_student_delete,    True,  "admin"),
    ("POST", "/api/admin/marks/add"):          (api_marks_add,         True,  "admin"),
    ("POST", "/api/admin/marks/delete"):       (api_marks_delete,      True,  "admin"),
    ("POST", "/api/admin/attendance/add"):     (api_attendance_add,    True,  "admin"),
    ("POST", "/api/admin/attendance/delete"):  (api_attendance_delete, True,  "admin"),
    ("POST", "/api/admin/notice/add"):         (api_notice_add,        True,  "admin"),
    ("POST", "/api/admin/notice/delete"):      (api_notice_delete,     True,  "admin"),
    ("POST", "/api/admin/payment/add"):        (api_payment_add,       True,  "admin"),
    ("POST", "/api/admin/payment/update"):     (api_payment_update,    True,  "admin"),
    ("POST", "/api/admin/payment/delete"):     (api_payment_delete,    True,  "admin"),
}

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        if "/api/" in self.path:
            print(f"  {self.command} {self.path.split('?')[0]}  {fmt % args}")

    def send_json(self, code, data):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control",  "no-store")
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,X-Session-Token")
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, req_path):
        if req_path in ("/", ""):
            req_path = "/pages/login.html"

        full = os.path.normpath(os.path.join(BASE_DIR, req_path.lstrip("/")))

        if not full.startswith(BASE_DIR):          # block traversal
            self.send_response(403); self.end_headers(); return

        if os.path.isdir(full):
            full = os.path.join(full, "login.html")

        if not os.path.isfile(full):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"404 Not Found: {req_path}".encode())
            return

        mime, _ = mimetypes.guess_type(full)
        mime     = mime or "application/octet-stream"

        with open(full, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header("Content-Type",   mime)
        self.send_header("Content-Length", str(len(data)))
        if "html" in mime:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
        else:
            self.send_header("Cache-Control", "max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,X-Session-Token")
        self.end_headers()

    def handle_request(self, method):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"
        qs     = parse_qs(parsed.query)

        if not path.startswith("/api"):
            self.serve_file(path)
            return

        route = ROUTES.get((method, path))
        if not route:
            self.send_json(404, {"error": f"Unknown endpoint: {method} {path}"})
            return

        handler_fn, needs_auth, required_role = route
        session = None

        if needs_auth:
            token   = self.headers.get("X-Session-Token", "").strip()
            session = session_get(token)
            if not session:
                self.send_json(401, {"error": "Not authenticated. Please log in."})
                return
            if required_role and session.get("role") != required_role:
                self.send_json(403, {"error": "Access forbidden."})
                return
            session["_token"] = token

        length = int(self.headers.get("Content-Length", 0) or 0)
        body   = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"

        try:
            if needs_auth:
                code, result = handler_fn(body, qs, session)
            else:
                code, result = handler_fn(body, qs)
            self.send_json(code, result)
        except MySQLError as e:
            print(f"  DB ERROR: {e}")
            self.send_json(500, {"error": f"Database error: {e}"})
        except Exception as e:
            traceback.print_exc()
            self.send_json(500, {"error": str(e)})

    def do_GET(self):  self.handle_request("GET")
    def do_POST(self): self.handle_request("POST")

if __name__ == "__main__":
    print("\n" + "=" * 52)
    print("  Student MIS  —  MySQL / XAMPP Edition")
    print("=" * 52)

    check_db()

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"  Server   ->  http://localhost:{PORT}")
    print(f"  Admin    ->  admin  /  admin@123")
    print(f"  Student  ->  arjun@student.edu  /  pass@123")
    print("=" * 52 + "\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")