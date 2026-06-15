const API = window.location.origin;
const APP = 'http://localhost:7667';

// --- Token management ---
function getToken() { return localStorage.getItem('cu_admin_token') || ''; }
function setToken(t) { localStorage.setItem('cu_admin_token', t); }
function clearToken() { localStorage.removeItem('cu_admin_token'); }

// --- Session state ---
var __cuSession = {role: '', name: '', courses: []};

// --- Login overlay ---
function showLogin() {
  const ol = document.getElementById('login-overlay');
  if (ol) ol.style.display = 'flex';
}
function hideLogin() {
  const ol = document.getElementById('login-overlay');
  if (ol) ol.style.display = 'none';
}

async function doLogin() {
  const uname = (document.getElementById('login-username').value || '').trim();
  const pw    = document.getElementById('login-password').value;
  const err   = document.getElementById('login-error');
  err.style.display = 'none';
  if (!pw) { err.textContent = 'Enter your password.'; err.style.display = 'block'; return; }
  try {
    const r = await window.__rawFetch(API + '/admin/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username: uname, password: pw})
    });
    const d = await r.json();
    if (!r.ok) { err.textContent = d.detail || 'Invalid credentials'; err.style.display = 'block'; return; }
    setToken(d.token);
    __cuSession = {role: d.role || 'admin', name: d.name || d.username || 'Admin', courses: d.courses || []};
    document.getElementById('login-password').value = '';
    hideLogin();
    applyRole();
    initApp();
  } catch(e) {
    err.textContent = 'Server unreachable.'; err.style.display = 'block';
  }
}

function doLogout() {
  clearToken();
  __cuSession = {role: '', name: '', courses: []};
  document.getElementById('login-username').value = '';
  document.getElementById('login-password').value = '';
  document.getElementById('login-error').style.display = 'none';
  showLogin();
}

function applyRole() {
  const isAdmin = __cuSession.role === 'admin';
  document.querySelectorAll('[data-admin-only]').forEach(el => {
    el.style.display = isAdmin ? '' : 'none';
  });
  const footer = document.getElementById('sidebar-user');
  if (footer) footer.textContent = __cuSession.name || '';
}

// --- Fetch interceptor: auto-inject Authorization header for API calls ---
window.__rawFetch = window.fetch.bind(window);
(function() {
  const _orig = window.__rawFetch;
  window.fetch = function(url, opts) {
    const tok = getToken();
    if (tok && typeof url === 'string' && url.startsWith(API)) {
      opts = opts || {};
      opts.headers = Object.assign({'Authorization': 'Bearer ' + tok}, opts.headers || {});
    }
    return _orig.call(this, url, opts).then(function(resp) {
      if (resp.status === 401 && typeof url === 'string' && url.startsWith(API)) {
        clearToken();
        showLogin();
      }
      return resp;
    });
  };
})();
