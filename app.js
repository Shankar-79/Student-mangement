let currentUser = null;

/* ============================
   LOAD USER
============================ */
function loadUser() {
    let id = localStorage.getItem("sm_current");
    if (!id) window.location.href = "login.html";

    let users = JSON.parse(localStorage.getItem("sm_users") || "{}");
    currentUser = users[id];
}
loadUser();

/* Page Elements */
const pages = document.querySelectorAll(".page");
const pageTitle = document.getElementById("pageTitle");

/* ============================
   SIDEBAR COLLAPSE
============================ */
document.getElementById("sidebarToggle").onclick = () => {
    document.getElementById("sidebar").classList.toggle("collapsed");
};


/* ============================
   SIDEBAR NAVIGATION
============================ */
const navButtons = document.querySelectorAll(".nav-btn");

navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
        // Remove active state
        navButtons.forEach(b => b.classList.remove("active"));

        // Add active
        btn.classList.add("active");

        // Switch page
        const view = btn.dataset.view;
        pages.forEach(p => p.classList.remove("active"));
        document.getElementById("page-" + view).classList.add("active");

        pageTitle.textContent = view.toUpperCase();
        render(view);
    });
});


/* ============================
   DASHBOARD RENDER
============================ */
function renderDashboard() {

    document.getElementById("dashName").textContent = currentUser.name;

    let att = JSON.parse(localStorage.getItem("att_" + currentUser.id) || "{}");
    document.getElementById("dashAttendance").textContent =
        Object.keys(att).length + " records";

    let pays = JSON.parse(localStorage.getItem("pay_" + currentUser.id) || "[]");
    document.getElementById("dashPayments").textContent =
        pays.length + " payments";

    let regs = JSON.parse(localStorage.getItem("reg_" + currentUser.id) || "[]");
    document.getElementById("dashCourses").textContent =
        regs.join(", ") || "None";

    let res = JSON.parse(localStorage.getItem("res_" + currentUser.id) || "null");
    document.getElementById("dashResult").textContent =
        res ? ("SGPA: " + res.sgpa) : "No result";
}


/* ============================
   PROFILE RENDER + SAVE
============================ */
function renderProfile() {
    document.getElementById("p-name").value = currentUser.name;
    document.getElementById("p-email").value = currentUser.email || "";
    document.getElementById("p-phone").value = currentUser.phone || "";
    document.getElementById("p-course").value = currentUser.course || "";
    document.getElementById("p-address").value = currentUser.address || "";
}

document.getElementById("saveProfileBtn").onclick = () => {
    let users = JSON.parse(localStorage.getItem("sm_users") || "{}");

    users[currentUser.id].name = document.getElementById("p-name").value;
    users[currentUser.id].email = document.getElementById("p-email").value;
    users[currentUser.id].phone = document.getElementById("p-phone").value;
    users[currentUser.id].course = document.getElementById("p-course").value;
    users[currentUser.id].address = document.getElementById("p-address").value;

    localStorage.setItem("sm_users", JSON.stringify(users));
    currentUser = users[currentUser.id];

    alert("Profile saved!");
};



/* ============================
   ATTENDANCE (MARK + FILTER)
============================ */
document.getElementById("filterBtn").onclick = () => {
    let date = document.getElementById("filterFrom").value;
    let to = document.getElementById("filterTo").value;
    let status = document.getElementById("att-status").value;

    let key = "att_" + currentUser.id;
    let att = JSON.parse(localStorage.getItem(key) || "{}");

    // --- MARK ATTENDANCE ---
    if (date && !to) {
        att[date] = status;
        localStorage.setItem(key, JSON.stringify(att));
        alert("Attendance Marked!");
        renderAttendance();
        return;
    }

    // --- FILTER ATTENDANCE ---
    filterAttendance(date, to, status);
};


/* RESET FILTER */
document.getElementById("resetFilter").onclick = () => {
    document.getElementById("filterFrom").value = "";
    document.getElementById("filterTo").value = "";
    document.getElementById("att-status").value = "Present";
    renderAttendance();
};


/* FILTER TABLE */
function filterAttendance(from, to, statusFilter) {
    let key = "att_" + currentUser.id;
    let att = JSON.parse(localStorage.getItem(key) || "{}");

    let tbody = document.querySelector("#att-table tbody");
    tbody.innerHTML = "";

    let entries = Object.entries(att).sort((a, b) => new Date(a[0]) - new Date(b[0]));

    entries.forEach(([date, status]) => {
        if (from && date < from) return;
        if (to && date > to) return;
        if (statusFilter && status !== statusFilter) return;

        tbody.innerHTML += `
            <tr>
                <td>${date}</td>
                <td>${status}</td>
            </tr>
        `;
    });
}


/* FULL TABLE */
function renderAttendance() {
    let key = "att_" + currentUser.id;
    let att = JSON.parse(localStorage.getItem(key) || "{}");

    let tbody = document.querySelector("#att-table tbody");
    tbody.innerHTML = "";

    let entries = Object.entries(att).sort((a, b) => new Date(a[0]) - new Date(b[0]));

    entries.forEach(([date, status]) => {
        tbody.innerHTML += `
            <tr>
                <td>${date}</td>
                <td>${status}</td>
            </tr>
        `;
    });
}



/* ============================
   REGISTRATION PAGE
============================ */
function renderRegistration() {
    let regs = JSON.parse(localStorage.getItem("reg_" + currentUser.id) || "[]");

    // Mark checkboxes
    document.querySelectorAll(".course-chk").forEach(chk => {
        chk.checked = regs.includes(chk.value);
    });

    // Registered table
    let tbody = document.querySelector("#reg-table tbody");
    tbody.innerHTML = "";

    let courseNames = {
        "Math101": "Mathematics 101",
        "CS201": "Computer Science 201",
        "ENG150": "English Communication"
    };

    regs.forEach(code => {
        tbody.innerHTML += `
            <tr>
                <td>${code}</td>
                <td>${courseNames[code] || "Unknown"}</td>
            </tr>
        `;
    });
}

document.getElementById("course-save").onclick = () => {
    let selected = [...document.querySelectorAll(".course-chk:checked")].map(c => c.value);

    localStorage.setItem("reg_" + currentUser.id, JSON.stringify(selected));
    alert("Courses Saved!");

    renderRegistration();
};



/* ============================
   PAYMENT PAGE
============================ */
document.getElementById("pay-btn").onclick = () => {
    let amount = document.getElementById("pay-amount").value;
    let mode = document.getElementById("pay-mode").value;

    if (!amount) return alert("Enter amount");

    let key = "pay_" + currentUser.id;
    let pays = JSON.parse(localStorage.getItem(key) || "[]");

    pays.push({
        amount,
        mode,
        date: new Date().toLocaleString()
    });

    localStorage.setItem(key, JSON.stringify(pays));

    alert("Payment recorded!");
    renderPayment();
};

function renderPayment() {
    let key = "pay_" + currentUser.id;
    let pays = JSON.parse(localStorage.getItem(key) || "[]");

    let tbody = document.querySelector("#pay-table tbody");
    tbody.innerHTML = "";

    pays.forEach(p => {
        tbody.innerHTML += `
            <tr>
                <td>₹${p.amount}</td>
                <td>${p.mode}</td>
                <td>${p.date}</td>
            </tr>
        `;
    });
}



/* ============================
   RESULT PAGE
============================ */
function getGrade(marks) {
    if (marks >= 90) return "A+";
    if (marks >= 80) return "A";
    if (marks >= 70) return "B+";
    if (marks >= 60) return "B";
    if (marks >= 50) return "C";
    if (marks >= 40) return "D";
    return "F";
}

function calculateSGPA(subjects) {
    let total = 0;
    subjects.forEach(sub => {
        total += (sub.marks / sub.max) * 100;
    });

    let avg = total / subjects.length;
    return (avg / 10).toFixed(2);
}

function renderResult() {
    let key = "res_" + currentUser.id;
    let data = JSON.parse(localStorage.getItem(key) || "null");

    let tbody = document.querySelector("#result-table tbody");
    let sgpaVal = document.getElementById("sgpa-value");

    tbody.innerHTML = "";

    if (!data || !data.subjects || data.subjects.length === 0) {
        sgpaVal.textContent = "--";
        tbody.innerHTML = `<tr><td colspan="5">No results added</td></tr>`;
        return;
    }

    let sgpa = calculateSGPA(data.subjects);
    sgpaVal.textContent = sgpa;

    data.subjects.forEach(sub => {
        tbody.innerHTML += `
            <tr>
                <td>${sub.code}</td>
                <td>${sub.name}</td>
                <td>${sub.marks}</td>
                <td>${sub.max}</td>
                <td>${getGrade(sub.marks)}</td>
            </tr>
        `;
    });

    data.sgpa = sgpa;
    localStorage.setItem(key, JSON.stringify(data));
}

document.getElementById("add-subject").onclick = () => {
    let code = document.getElementById("sub-code").value.trim();
    let name = document.getElementById("sub-name").value.trim();
    let marks = Number(document.getElementById("sub-marks").value);
    let max = Number(document.getElementById("sub-max").value);

    if (!code || !name || !marks || !max) {
        alert("Please fill all fields!");
        return;
    }

    let key = "res_" + currentUser.id;
    let data = JSON.parse(localStorage.getItem(key) || '{"subjects":[]}');

    data.subjects.push({ code, name, marks, max });

    localStorage.setItem(key, JSON.stringify(data));
    renderResult();

    document.getElementById("sub-code").value = "";
    document.getElementById("sub-name").value = "";
    document.getElementById("sub-marks").value = "";
    document.getElementById("sub-max").value = "";
};



/* ============================
   LOGOUT
============================ */
document.getElementById("logoutBtn").onclick = () => {
    localStorage.removeItem("sm_current");
    window.location.href = "login.html";
};


/* ============================
   INITIAL PAGE LOAD
============================ */
function render(view) {
    if (view === "dashboard") renderDashboard();
    if (view === "profile") renderProfile();
    if (view === "attendance") renderAttendance();
    if (view === "registration") renderRegistration();
    if (view === "payment") renderPayment();
    if (view === "result") renderResult();
}

renderDashboard();    // default page
renderAttendance();
renderRegistration();
renderPayment();
renderResult();
