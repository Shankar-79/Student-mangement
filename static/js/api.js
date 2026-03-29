
'use strict';

const Auth = {
  save(data) { localStorage.setItem('mis_session', JSON.stringify(data)); },
  load()     { try { return JSON.parse(localStorage.getItem('mis_session')); } catch { return null; } },
  clear()    { localStorage.removeItem('mis_session'); },
  token()    { return this.load()?.token || ''; },
  user()     { return this.load() || null; },
  role()     { return this.load()?.role || ''; },
};


async function api(method, path, body = null) {
  const opts = {
    method,
    headers: {
      'Content-Type':    'application/json',
      'X-Session-Token': Auth.token(),
    },
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res  = await fetch(path, opts);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: { error: 'Network error' } };
  }
}

const GET  = (path)       => api('GET',  path);
const POST = (path, body) => api('POST', path, body);


let _toastTimer;
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className   = `show ${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.className = '', 3500);
}


function showSpinner() { document.getElementById('spinner')?.classList.add('show'); }
function hideSpinner() { document.getElementById('spinner')?.classList.remove('show'); }


function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }
function closeAllModals() {
  document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
}
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) closeAllModals();
});


function openSidebar() {
  document.getElementById('sidebar')?.classList.add('open');
  document.getElementById('sbOverlay')?.classList.add('open');
}
function closeSidebar() {
  document.getElementById('sidebar')?.classList.remove('open');
  document.getElementById('sbOverlay')?.classList.remove('open');
}


function showLogout() { openModal('logoutModal'); }
async function doLogout() {
  try { await POST('/api/logout'); } catch (_) {}
  Auth.clear();

  location.replace('/pages/login.html');
}


function setDateLabel(id = 'dateLabel') {
  const el = document.getElementById(id);
  if (el) el.textContent = new Date().toLocaleDateString('en-IN', {
    weekday:'long', day:'numeric', month:'long', year:'numeric'
  });
}


async function requireAuth(role) {
  const local = Auth.user();


  if (!local || !local.token) {
    location.replace('/pages/login.html');
    return null;
  }


  if (role && local.role !== role) {
    Auth.clear();
    location.replace('/pages/login.html');
    return null;
  }

    const verifyPath = role === 'admin' ? '/api/admin/ping' : '/api/ping';
  const res = await api('GET', verifyPath);

  if (res.status === 401 || res.status === 403) {
  
    Auth.clear();
    location.replace('/pages/login.html');
    return null;
  }

  return local;
}

function setSidebarUser(user) {
  const nameEl   = document.getElementById('sbName');
  const subEl    = document.getElementById('sbSub');
  const avatarEl = document.getElementById('sbAvatar');
  if (nameEl)   nameEl.textContent   = user.name || '';
  if (subEl)    subEl.textContent    = user.roll || (user.role === 'admin' ? 'Administrator' : '');
  if (avatarEl) {
    // Admin sidebar avatar is an icon element, don't overwrite it
    if (avatarEl.querySelector('i')) return;
    avatarEl.textContent = (user.name || 'U')[0].toUpperCase();
  }
}


function esc(str) {
  return String(str ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmt(n) {
  return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function fmtDate(s) {
  if (!s) return '—';
  try { return new Date(s).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' }); }
  catch { return s; }
}

function gradeLetter(pct) {
  if (pct >= 80) return 'A';
  if (pct >= 65) return 'B';
  if (pct >= 50) return 'C';
  return 'D';
}
function gradeClass(pct) {
  if (pct >= 80) return 'a';
  if (pct >= 65) return 'b';
  if (pct >= 50) return 'c';
  return 'd';
}

function statusClass(s) {
  return s?.toLowerCase() || 'pending';
}

function categoryClass(c) {
  return (c || 'general').toLowerCase();
}


function validateForm(formEl) {
  let ok = true;
  formEl.querySelectorAll('[required]').forEach(el => {
    if (!el.value.trim()) {
      el.classList.add('err');
      ok = false;
    } else {
      el.classList.remove('err');
    }
  });
  return ok;
}


function formData(formEl) {
  const obj = {};
  new FormData(formEl).forEach((v, k) => obj[k] = v);
  return obj;
}
