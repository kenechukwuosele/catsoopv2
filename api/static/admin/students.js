// Student list, password reset, lecturer management

var _resetPwTarget = '';

function populateCourseSelect(sel, allowedCourses) {
  const prev = sel.value;
  loadCourses().then(courses => {
    const filtered = allowedCourses ? courses.filter(c => allowedCourses.includes(c.id)) : courses;
    sel.innerHTML = '<option value="">Select a course…</option>';
    filtered.forEach(c => {
      const o = document.createElement('option');
      o.value = c.id; o.textContent = c.name || c.id;
      if (c.id === prev) o.selected = true;
      sel.appendChild(o);
    });
  }).catch(() => {});
}

async function loadStudentsPanel() {
  const course = document.getElementById('pw-course-select').value;
  const tbody = document.getElementById('pw-student-tbody');
  const countEl = document.getElementById('pw-student-count');
  if (!course) {
    tbody.innerHTML = '<tr><td colspan="3" style="color:var(--muted);text-align:center;padding:20px;">Select a course above</td></tr>';
    countEl.textContent = '';
    return;
  }
  tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--muted);padding:20px;">Loading…</td></tr>';
  try {
    const r = await fetch(`${API}/lecturer/students?course=${encodeURIComponent(course)}`);
    if (!r.ok) { const d = await r.json(); toast(d.detail || 'Error loading students', 'error'); return; }
    const data = await r.json();
    const students = data.students || [];
    countEl.textContent = students.length + ' student' + (students.length !== 1 ? 's' : '');
    if (!students.length) {
      tbody.innerHTML = '<tr><td colspan="3" style="color:var(--muted);text-align:center;padding:20px;">No students in this course yet</td></tr>';
      return;
    }
    tbody.innerHTML = students.map(s => {
      const lastActive = s.last_active ? new Date(s.last_active * 1000).toLocaleDateString() : '—';
      return `<tr>
        <td style="font-family:var(--mono);font-weight:500;">${escapeHtml(s.username)}</td>
        <td style="color:var(--muted);font-size:0.85em;">${escapeHtml(lastActive)}</td>
        <td style="text-align:right;">
          <button class="btn btn-ghost btn-sm" onclick="openResetPassword('${escapeHtml(s.username)}')">🔑 Reset</button>
        </td>
      </tr>`;
    }).join('');
  } catch(e) { toast('Network error: ' + e.message, 'error'); }
}

function openResetPassword(username) {
  _resetPwTarget = username;
  document.getElementById('reset-pw-username').textContent = username;
  document.getElementById('reset-pw-new').value = '';
  document.getElementById('reset-pw-confirm').value = '';
  document.getElementById('reset-pw-error').style.display = 'none';
  document.getElementById('reset-pw-success').style.display = 'none';
  document.getElementById('reset-pw-submit').style.display = '';
  openModal('modal-reset-pw');
  setTimeout(() => document.getElementById('reset-pw-new').focus(), 50);
}

async function doResetPassword() {
  const pw1 = document.getElementById('reset-pw-new').value;
  const pw2 = document.getElementById('reset-pw-confirm').value;
  const err  = document.getElementById('reset-pw-error');
  err.style.display = 'none';
  if (pw1.length < 6) { err.textContent = 'Password must be at least 6 characters.'; err.style.display = 'block'; return; }
  if (pw1 !== pw2)    { err.textContent = 'Passwords do not match.'; err.style.display = 'block'; return; }
  const course = document.getElementById('pw-course-select').value;
  const btn = document.getElementById('reset-pw-submit');
  btn.disabled = true; btn.textContent = 'Resetting…';
  try {
    const r = await fetch(`${API}/lecturer/students/${encodeURIComponent(_resetPwTarget)}/reset-password`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({course, new_password: pw1})
    });
    const d = await r.json();
    if (!r.ok) { err.textContent = d.detail || 'Reset failed'; err.style.display = 'block'; btn.disabled = false; btn.textContent = 'Reset Password'; return; }
    document.getElementById('reset-pw-display').textContent = pw1;
    document.getElementById('reset-pw-success').style.display = 'block';
    btn.style.display = 'none';
    toast('Password reset for ' + _resetPwTarget);
  } catch(e) {
    err.textContent = 'Network error.'; err.style.display = 'block';
    btn.disabled = false; btn.textContent = 'Reset Password';
  }
}

function copyResetPw() {
  const pw = document.getElementById('reset-pw-display').textContent;
  navigator.clipboard.writeText(pw).then(() => toast('Copied to clipboard'));
}

async function loadLecturersPanel() {
  const tbody = document.getElementById('lec-table-body');
  tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted);text-align:center;">Loading...</td></tr>';
  try {
    const r = await fetch(`${API}/admin/lecturers`);
    if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
    const d = await r.json();
    const rows = d.lecturers || [];
    document.getElementById('lec-count').textContent = rows.length;
    tbody.innerHTML = rows.length
      ? rows.map(l => `<tr>
          <td style="font-family:var(--mono);">${escapeHtml(l.username)}</td>
          <td>${escapeHtml(l.name || '—')}</td>
          <td style="color:var(--muted);">${escapeHtml(l.email || '—')}</td>
          <td>${escapeHtml((l.courses || []).join(', ') || '—')}</td>
          <td style="color:var(--muted);font-size:0.85em;">${escapeHtml((l.registered_at || '').substring(0, 16))}</td>
          <td><button class="btn btn-danger btn-sm" onclick="deleteLecturer('${escapeHtml(l.username)}')">Remove</button></td>
        </tr>`).join('')
      : '<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:16px;">No lecturers registered yet</td></tr>';
  } catch(e) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted);text-align:center;">Error: ' + escapeHtml(e.message) + '</td></tr>';
  }
}

async function openRegisterLecturer() {
  const sel = document.getElementById('reg-lec-courses');
  sel.innerHTML = '';
  try {
    const courses = await loadCourses();
    courses.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id; opt.textContent = c.name || c.id;
      sel.appendChild(opt);
    });
  } catch {}
  openModal('modal-register-lecturer');
}

async function registerLecturer() {
  const username = document.getElementById('reg-lec-username').value.trim();
  const name     = document.getElementById('reg-lec-name').value.trim();
  const email    = document.getElementById('reg-lec-email').value.trim();
  const password = document.getElementById('reg-lec-password').value;
  const courses  = Array.from(document.getElementById('reg-lec-courses').selectedOptions).map(o => o.value);
  const errEl    = document.getElementById('reg-lec-error');
  errEl.style.display = 'none';

  if (!username || !name || !password) {
    errEl.textContent = 'Username, full name, and password are required.';
    errEl.style.display = 'block'; return;
  }
  try {
    const r = await fetch(`${API}/admin/lecturers`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, name, email, password, courses})
    });
    const d = await r.json();
    if (r.ok) {
      toast('Lecturer registered!');
      closeModal('modal-register-lecturer');
      ['reg-lec-username','reg-lec-name','reg-lec-email','reg-lec-password'].forEach(id => document.getElementById(id).value = '');
      loadLecturersPanel();
    } else {
      errEl.textContent = d.detail || 'Registration failed';
      errEl.style.display = 'block';
    }
  } catch(e) {
    errEl.textContent = 'Request failed: ' + e.message;
    errEl.style.display = 'block';
  }
}

async function deleteLecturer(username) {
  if (!confirm(`Remove lecturer "${username}"? This cannot be undone.`)) return;
  try {
    const r = await fetch(`${API}/admin/lecturers/${encodeURIComponent(username)}`, {method: 'DELETE'});
    if (r.ok) { toast('Lecturer removed'); loadLecturersPanel(); }
    else { const d = await r.json(); toast(d.detail || 'Error', 'error'); }
  } catch { toast('Failed', 'error'); }
}

async function syncCatSooPInstructors() {
  try {
    const r = await fetch(`${API}/admin/sync-instructors`, {method: 'POST'});
    const d = await r.json();
    if (r.ok) {
      const msg = d.synced
        ? `Synced ${d.synced} instructor(s): ${d.synced_usernames.join(', ')}`
        : `No new instructors found (${d.already_exist} already registered)`;
      toast(msg);
      loadLecturersPanel();
    } else {
      toast(d.detail || 'Sync failed', 'error');
    }
  } catch(e) {
    toast('Sync failed: ' + e.message, 'error');
  }
}
