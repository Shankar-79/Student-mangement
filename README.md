# Student MIS — Pure Python + HTML/CSS/JS

No Flask. No XAMPP. No external packages.
Uses Python's built-in `http.server` + `sqlite3`.

---

## ▶ Run in 2 steps

```bash

python server.py
```

Open → **http://localhost:8000**

The database (`mis.db`) is created automatically with sample data on first run.

---

## 🔑 Login Credentials

| Role    | Username / Email      | Password    |
|---------|-----------------------|-------------|
| Admin   | `admin`               | `admin@123` |
| Student | `arjun@student.edu`   | `pass@123`  |
| Student | `priya@student.edu`   | `pass@123`  |
| Student | `rahul@student.edu`   | `pass@123`  |

---

## 📁 Project Structure

```
mis/
├── server.py               ← Python backend (http.server + sqlite3)
├── mis.db                  ← SQLite DB (auto-created on first run)
│
├── pages/
│   ├── login.html          ← Login page (student + admin toggle)
│   ├── dashboard.html      ← Student dashboard (cards + charts)
│   ├── profile.html        ← Student profile view + edit
│   ├── payments.html       ← Fee history with filter
│   └── admin.html          ← Full admin CRUD panel
│
└── static/
    ├── css/
    │   └── style.css       ← Complete design system
    └── js/
        └── api.js          ← Shared: fetch helper, auth, toast, modal, sidebar
```

---

## ✨ Features

**No dependencies** — runs with `python server.py`, nothing to install.

**Student Module**
- Login with email or roll number
- Dashboard: stat cards, Chart.js bar + doughnut charts, marks table, notices
- Profile: view + edit (saves to DB via fetch)
- Payments: history table with Paid/Pending/Overdue filter

**Admin Module**
- Tab-based dashboard (Students, Marks, Attendance, Notices, Payments)
- Students: Add via modal, Edit via modal (pre-filled), Delete with confirm
- Marks: Add + delete records
- Attendance: Add/update + delete (upsert by student+subject+month)
- Notices: Post + delete with categories
- Payments: Add + update status + delete

**UI/UX**
- Fixed sidebar desktop, slide-in sidebar mobile with overlay
- Logout confirmation modal on every page
- Toast notifications for all actions
- Full client-side form validation
- Loading spinner for async operations
- Responsive — works on mobile, tablet, desktop
