document.getElementById("loginBtn").onclick = () => {
    let id = loginId.value.trim();
    let pw = loginPass.value.trim();

    if (!id || !pw) return alert("Enter ID & Password");

    let users = JSON.parse(localStorage.getItem("sm_users") || "{}");

    if (!users[id]) {
        users[id] = { id, password: pw, name: "Student " + id };
    }

    if (users[id].password !== pw) return alert("Incorrect Password!");

    localStorage.setItem("sm_users", JSON.stringify(users));
    localStorage.setItem("sm_current", id);

    window.location.href = "dashboard.html";
};
