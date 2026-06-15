const API = window.location.origin;
const APP = 'http://localhost:7667';

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

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

function initApp() {
  populateCourseDropdowns();
  loadOverview();
  // Populate the password-reset course dropdown
  const sel = document.getElementById('pw-course-select');
  if (sel) {
    populateCourseSelect(sel, __cuSession.role === 'lecturer' ? __cuSession.courses : null);
  }
}

// --- Startup: check stored token or show login ---
(function() {
  const tok = getToken();
  if (tok) {
    try {
      const payload = JSON.parse(atob(tok.split('.')[1]));
      const now = Math.floor(Date.now() / 1000);
      if (payload.exp && payload.exp > now) {
        __cuSession = {
          role: payload.is_lecturer ? 'lecturer' : 'admin',
          name: payload.name || payload.sub || 'User',
          courses: payload.courses || []
        };
        hideLogin();
        applyRole();
        initApp();
        return;
      }
    } catch(e) {}
    clearToken();
  }
  showLogin();
})();

const Q_TYPES = {
  multiplechoice: {label:'Multiple Choice', badge:'q-type-mc'},
  truefalse: {label:'True / False', badge:'q-type-tf'},
  shortanswer: {label:'Short Answer', badge:'q-type-sa'},
  numerical: {label:'Numerical', badge:'q-type-num'},
  symbolic: {label:'Symbolic Math', badge:'q-type-sym'},
  pythoncode: {label:'Python Code', badge:'q-type-py'}
};

function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  document.querySelector(`[onclick="showPanel('${name}')"]`).classList.add('active');
  document.getElementById('current-panel-title').textContent=name.charAt(0).toUpperCase()+name.slice(1);
  if(name==='overview') loadOverview();
  if(name==='grades') loadGradesPanel();
  if(name==='queue') loadQueuePanel();
  if(name==='hints') loadHintStats();
  if(name==='live'){
    (async()=>{
      await populateCourseDropdowns();
      const lc=document.getElementById('live-course');
      if(!lc.value){const first=lc.querySelector('option[value]:not([value=""])');if(first)lc.value=first.value;}
      await loadWeeksForCourse('live-course','live-week');
      const lw=document.getElementById('live-week');
      if(!lw.value){const first=lw.querySelector('option[value]:not([value=""])');if(first)lw.value=first.value;}
      if(lc.value&&lw.value) loadMonitoringPanel();
    })();
  }
  if(name==='performance') loadPerformance();
  if(name==='gamification') loadGamificationPanel();
  if(name==='faceauth') loadFaceAuthPanel();
  if(name==='lecturers') { loadLecturersPanel(); }
  if(name==='students') loadStudentsPanel();
}

function toast(msg,type='success') {
  const t=document.getElementById('toast');
  t.textContent=(type==='success'?'✓ ':'✗ ')+msg;
  t.className='show '+type;
  setTimeout(()=>t.className='',3000);
}

function openModal(id){document.getElementById(id).classList.add('show');}
function closeModal(id){document.getElementById(id).classList.remove('show');}

function mdInsert(id,prefix,suffix) {
  const ta=document.getElementById(id);
  const start=ta.selectionStart,end=ta.selectionEnd;
  const lineStart=ta.value.lastIndexOf('\n',start-1)+1;
  ta.value=ta.value.substring(0,lineStart)+prefix+ta.value.substring(lineStart,end)+suffix+ta.value.substring(end);
  ta.focus();
}
function mdWrap(id,before,after) {
  const ta=document.getElementById(id);
  const start=ta.selectionStart,end=ta.selectionEnd;
  const sel=ta.value.substring(start,end)||'text';
  ta.value=ta.value.substring(0,start)+before+sel+after+ta.value.substring(end);
  ta.setSelectionRange(start+before.length,start+before.length+sel.length);
  ta.focus();
}

// Problem builder with all question types
function addProblem() {
  const list=document.getElementById('problems-list');
  const num=list.children.length+1;
  const card=document.createElement('div'); card.className='problem-card';
  card.innerHTML=`
    <div class="problem-card-header">
      <span class="problem-card-num">Problem ${num}</span>
      <button class="remove-btn" onclick="this.closest('.problem-card').remove();renumberProblems()">✕ Remove</button>
    </div>
    <div class="problem-fields">
      <div class="field" style="grid-column:1/-1;">
        <label>Question Type</label>
        <select class="prob-type" onchange="updateProblemFields(this)">
          <option value="multiplechoice">Multiple Choice</option>
          <option value="truefalse">True / False</option>
          <option value="shortanswer">Short Answer</option>
          <option value="numerical">Numerical Answer</option>
          <option value="symbolic">Symbolic Math</option>
          <option value="pythoncode">Python Code</option>
        </select>
      </div>
      <div class="field full-width" style="grid-column:1/-1;">
        <label>Question</label>
        <textarea class="prob-question" placeholder="Enter question..." rows="2"></textarea>
      </div>
      <div class="field full-width prob-answer-section" style="grid-column:1/-1;">
        <label>Correct Answer</label>
        <input type="text" class="prob-answer" placeholder="e.g. 42 or Newton's Second Law"/>
      </div>
      <div class="field prob-tolerance-section" style="display:none;">
        <label>Tolerance (±)</label>
        <input type="text" class="prob-tolerance" placeholder="e.g. 0.01"/>
      </div>
      <div class="field prob-options-section" style="display:none;grid-column:1/-1;">
        <label>Options (one per line)</label>
        <textarea class="prob-options" rows="3" placeholder="Option A&#10;Option B&#10;Option C"></textarea>
      </div>
      <div class="field prob-testcode-section" style="display:none;grid-column:1/-1;">
        <label>Test Code</label>
        <textarea class="prob-testcode" rows="3" placeholder="assert solution() == expected_value"></textarea>
      </div>
    </div>`;
  list.appendChild(card);
}

function updateProblemFields(select) {
  const card=select.closest('.problem-card');
  const type=select.value;
  card.querySelector('.prob-tolerance-section').style.display = type==='numerical'?'':'none';
  card.querySelector('.prob-options-section').style.display = type==='multiplechoice'?'':'none';
  card.querySelector('.prob-testcode-section').style.display = type==='pythoncode'?'':'none';
  card.querySelector('.prob-answer-section').style.display = type==='pythoncode'?'none':'';
  if(type==='truefalse') card.querySelector('.prob-answer').placeholder='true or false';
  else if(type==='numerical') card.querySelector('.prob-answer').placeholder='e.g. 9.8';
  else if(type==='symbolic') card.querySelector('.prob-answer').placeholder='e.g. (x+1)**2';
  else card.querySelector('.prob-answer').placeholder='Correct answer';
}

function renumberProblems() {
  document.querySelectorAll('#problems-list .problem-card').forEach((c,i)=>{
    c.querySelector('.problem-card-num').textContent='Problem '+(i+1);
  });
}

function getProblems() {
  return [...document.querySelectorAll('#problems-list .problem-card')].map(card=>({
    type: card.querySelector('.prob-type').value,
    question: card.querySelector('.prob-question').value.trim(),
    answer: card.querySelector('.prob-answer')?.value.trim()||'',
    tolerance: card.querySelector('.prob-tolerance')?.value.trim()||'0.01',
    options: card.querySelector('.prob-options')?.value.trim().split('\n').filter(Boolean)||[],
    test_code: card.querySelector('.prob-testcode')?.value.trim()||''
  })).filter(p=>p.question);
}

async function loadCourses() {
  try{const r=await fetch(`${API}/admin/courses`);const d=await r.json();return d.courses||[];}
  catch{return[];}
}

async function populateCourseDropdowns() {
  const courses=await loadCourses();
  ['week-course','q-course','gen-course','h-course','view-course','att-course','gr-course','lf-course','lf-view-course','hint-view-course','gam-course','live-course'].forEach(id=>{
    const el=document.getElementById(id);if(!el)return;
    const cur=el.value;el.innerHTML='<option value="">Select course...</option>';
    courses.forEach(c=>el.innerHTML+=`<option value="${c.id}" ${c.id===cur?'selected':''}>${c.name}</option>`);
  });
  updateCoursesTable(courses);
  loadHintStats();
}

async function uploadLiveFile() {
  const course=document.getElementById('lf-course').value;
  const week=document.getElementById('lf-week').value;
  const fileInput=document.getElementById('lf-file');
  const status=document.getElementById('lf-status');
  if(!course||!week){toast('Select course and week','error');return;}
  if(!fileInput.files.length){toast('Choose a file','error');return;}
  status.textContent='Uploading...';
  const file=fileInput.files[0];
  const reader=new FileReader();
  reader.onload=async()=>{
    const base64=reader.result.split(',')[1]||'';
    const payload={
      course,
      week,
      filename:file.name,
      content_type:file.type||'application/octet-stream',
      data_base64:base64
    };
    try{
      const r=await fetch(`${API}/admin/live-file`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload)
      });
      const d=await r.json();
      if(r.ok){toast('Live file uploaded!');fileInput.value='';loadLiveFileMeta();}
      else toast(d.detail||'Upload failed','error');
    }catch{toast('Failed to connect','error');}
    status.textContent='';
  };
  reader.readAsDataURL(file);
}

async function loadLiveFileMeta() {
  const course=document.getElementById('lf-view-course').value;
  const week=document.getElementById('lf-view-week').value;
  const el=document.getElementById('lf-meta');
  if(!course||!week){el.textContent='Select a course and week to view the current live file.';return;}
  try{
    const r=await fetch(`${API}/admin/live-file/${course}/${week}`);
    const d=await r.json();
    if(!d){
      el.textContent='No live file uploaded yet.';
      return;
    }
    const link=`${API}/live-file/${course}/${week}`;
    el.innerHTML=`<div><strong>File:</strong> ${d.filename}</div><div><strong>Type:</strong> ${d.content_type}</div><div><strong>Uploaded:</strong> ${d.uploaded_at}</div><div style="margin-top:8px;display:flex;gap:8px;align-items:center;"><a href="${link}" target="_blank" style="color:var(--accent);">Open live file</a><button onclick="deleteLiveFile()" style="background:#c0392b;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;">Remove</button></div>`;
  }catch{
    el.textContent='Failed to load live file.';
  }
}

async function deleteLiveFile() {
  const course=document.getElementById('lf-view-course').value;
  const week=document.getElementById('lf-view-week').value;
  if(!course||!week){toast('Select course and week','error');return;}
  if(!confirm(`Remove live file for ${course} / ${week}?`))return;
  try{
    const r=await fetch(`${API}/admin/live-file/${course}/${week}`,{method:'DELETE'});
    if(r.ok){toast('Live file removed');loadLiveFileMeta();}
    else{const d=await r.json();toast(d.detail||'Delete failed','error');}
  }catch{toast('Failed to connect','error');}
}

function updateCoursesTable(courses) {
  const tbody=document.getElementById('courses-table-body');
  if(!courses.length){tbody.innerHTML='<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:20px;">No courses yet</td></tr>';return;}
  tbody.innerHTML=courses.map(c=>`
    <tr>
      <td><span class="badge badge-blue">${c.icon||''} ${c.id}</span></td>
      <td>${c.number||'—'}</td>
      <td style="color:var(--muted);max-width:180px;">${c.description||'—'}</td>
      <td style="display:flex;gap:6px;flex-wrap:wrap;">
        <button class="btn btn-ghost btn-sm" onclick="openEditCourse('${c.id}')">✏️</button>
        <button class="btn btn-ghost btn-sm" onclick="if(confirm('Delete course \\'${c.name}\\' and all its content?'))deleteCourse('${c.id}')">🗑️</button>
        <button class="btn btn-ghost btn-sm" onclick="openWeeksModal('${c.id}')">📁 Weeks</button>
        <a href="${APP}/${c.id}" target="_blank" class="btn btn-ghost btn-sm">↗</a>
      </td>
    </tr>`).join('');
}

async function loadGradesPanel() {
  const courses=await loadCourses();
  const grid=document.getElementById('grades-course-grid');
  if(!courses.length){grid.innerHTML='<p style="color:var(--muted);">No courses found.</p>';return;}
  grid.innerHTML=courses.map(c=>`
    <div class="course-feature-card">
      <h3><span class="badge badge-blue">${c.number||'—'}</span> ${c.name}</h3>
      <div class="links">
        <a href="${APP}/${c.id}/gradebook" target="_blank">📋 View Gradebook</a>
      </div>
    </div>`).join('');
}

async function loadQueuePanel() {
  const courses=await loadCourses();
  const grid=document.getElementById('queue-course-grid');
  if(!courses.length){grid.innerHTML='<p style="color:var(--muted);">No courses found.</p>';return;}
  grid.innerHTML=courses.map(c=>`
    <div class="course-feature-card">
      <h3><span class="badge badge-blue">${c.number||'—'}</span> ${c.name}</h3>
      <div class="links">
         <a href="${APP}/${c.id}/queue" target="_blank">🙋 Open Queue</a>
         <a href="${APP}/${c.id}/queue?manage=1" target="_blank">⚙️ Manage Queue</a>
      </div>
    </div>`).join('');
}

async function loadWeekSettings() {
  const course=document.getElementById('gr-course').value;
  const week=document.getElementById('gr-week').value;
  if(!course||!week){document.getElementById('week-settings-display').style.display='none';return;}
  try{
    const r=await fetch(`${API}/admin/courses/${course}/weeks`);
    const d=await r.json();
    const w=(d.weeks||[]).find(x=>x.id===week);
    if(!w){return;}
    document.getElementById('gr-due-date').value=w.due_date?.replace(' ','T')||'';
    document.getElementById('gr-grace').value=w.grace_period||0;
    document.getElementById('gr-penalty').value=w.lateness_penalty||0;
    document.getElementById('gr-allow-late').checked=w.allow_late!==false;
    document.getElementById('week-settings-display').style.display='block';
  }catch{}
}

async function saveWeekSettings() {
  const course=document.getElementById('gr-course').value;
  const week=document.getElementById('gr-week').value;
  if(!course||!week){toast('Select course and week','error');return;}
  const due_date=document.getElementById('gr-due-date').value.replace('T',' ');
  const grace_period=parseInt(document.getElementById('gr-grace').value)||0;
  const lateness_penalty=parseFloat(document.getElementById('gr-penalty').value)||0;
  const allow_late=document.getElementById('gr-allow-late').checked;
  try{
    const weeksRes=await fetch(`${API}/admin/courses/${course}/weeks`);
    const weeksData=await weeksRes.json();
    const w=(weeksData.weeks||[]).find(x=>x.id===week);
    const r=await fetch(`${API}/admin/courses/${course}/weeks/${week}`,{
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title:w?.title||week,content:w?.content||'',lecture_title:w?.lecture_title||'',lecture_content:'',due_date,grace_period,lateness_penalty,allow_late})
    });
    if(r.ok)toast('Settings saved!');else toast('Error saving','error');
  }catch{toast('Failed to connect','error');}
}

async function createCourse() {
  const name=document.getElementById('course-name').value.trim();
  const number=document.getElementById('course-number').value.trim();
  const desc=document.getElementById('course-desc').value.trim();
  const content=document.getElementById('course-content').value.trim();
  const icon=document.getElementById('course-icon').value.trim();
  if(!name){toast('Course name required','error');return;}
  document.getElementById('course-status').textContent='Creating...';
  try{
    const r=await fetch(`${API}/admin/courses`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,number,description:desc,content,icon})});
    const d=await r.json();
    if(r.ok){toast(`"${name}" created!`);clearCourseForm();populateCourseDropdowns();}
    else toast(d.detail||'Error','error');
  }catch{toast('Failed to connect','error');}
  document.getElementById('course-status').textContent='';
}

async function deleteCourse(courseId) {
  try{
    const r=await fetch(`${API}/admin/courses/${courseId}`,{method:'DELETE'});
    if(r.ok){toast('Course deleted');populateCourseDropdowns();}
    else{const d=await r.json();toast(d.detail||'Delete failed','error');}
  }catch{toast('Failed to connect','error');}
}

function clearCourseForm(){['course-name','course-number','course-desc','course-content','course-icon'].forEach(id=>document.getElementById(id).value='');document.getElementById('selected-icon-preview').textContent='';document.querySelectorAll('.icon-option').forEach(el=>el.classList.remove('selected'));}

async function createWeek() {
  const course=document.getElementById('week-course').value;
  const weekId=document.getElementById('week-id').value.trim();
  const title=document.getElementById('week-title').value.trim();
  const content=document.getElementById('week-content').value.trim();
  const lectureTitle=document.getElementById('lecture-title').value.trim();
  const lectureContent=document.getElementById('lecture-content').value.trim();
  const problems=getProblems();
  const dueDate=document.getElementById('week-due-date').value.replace('T',' ');
  const releaseDate=document.getElementById('week-release-date').value.replace('T',' ');
  const gracePeriod=parseInt(document.getElementById('week-grace').value)||0;
  const latenessPenalty=parseFloat(document.getElementById('week-penalty').value)||0;
  const allowLate=document.getElementById('week-allow-late').checked;
  if(!course||!weekId||!title){toast('Course, week ID and title required','error');return;}
  document.getElementById('week-status').textContent='Creating all files...';
  try{
    const r=await fetch(`${API}/admin/courses/${course}/weeks`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({week_id:weekId,title,content,lecture_title:lectureTitle,lecture_content:lectureContent,practice_problems:problems,due_date:dueDate,release_date:releaseDate,grace_period:gracePeriod,lateness_penalty:latenessPenalty,allow_late:allowLate,time_limit_minutes:parseInt(document.getElementById('week-time-limit').value)||0})
    });
    const d=await r.json();
    if(r.ok){
      toast(`Week "${title}" created! (${d.week_id})`);
      ['week-id','week-title','week-content','lecture-title','lecture-content','week-due-date','week-grace','week-penalty','week-time-limit'].forEach(id=>document.getElementById(id).value='');
      document.getElementById('problems-list').innerHTML='';
      document.getElementById('week-allow-late').checked=true;
      document.getElementById('week-time-limit').value='0';
    }else toast(d.detail||'Error','error');
  }catch{toast('Failed to connect','error');}
  document.getElementById('week-status').textContent='';
}

async function loadWeeksForCourse(courseSelectId,weekSelectId) {
  const courseId=document.getElementById(courseSelectId).value;
  const weekSelect=document.getElementById(weekSelectId);
  weekSelect.innerHTML='<option value="">Select week...</option>';
  if(!courseId)return;
  try{
    const r=await fetch(`${API}/admin/courses/${courseId}/weeks`);
    const d=await r.json();
    (d.weeks||[]).forEach(w=>weekSelect.innerHTML+=`<option value="${w.id}">${w.title}</option>`);
  }catch{}
}

async function openEditCourse(courseId) {
  const courses=await loadCourses();
  const c=courses.find(x=>x.id===courseId);if(!c)return;
  document.getElementById('edit-course-id').value=courseId;
  document.getElementById('edit-course-number').value=c.number||'';
  document.getElementById('edit-course-desc').value=c.description||'';
  document.getElementById('edit-course-content').value=c.content||'';
  document.getElementById('edit-course-icon').value=c.icon||'';
  document.getElementById('edit-selected-icon-preview').textContent=c.icon||'';
  document.querySelectorAll('#edit-icon-picker .icon-option').forEach(el=>{
    el.classList.toggle('selected',el.textContent===c.icon);
  });
  openModal('modal-edit-course');
}

async function saveCourseEdit() {
  const id=document.getElementById('edit-course-id').value;
  try{
    const r=await fetch(`${API}/admin/courses/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({number:document.getElementById('edit-course-number').value.trim(),description:document.getElementById('edit-course-desc').value.trim(),content:document.getElementById('edit-course-content').value.trim(),icon:document.getElementById('edit-course-icon').value.trim()})});
    if(r.ok){toast('Course updated!');closeModal('modal-edit-course');populateCourseDropdowns();}
    else toast('Error','error');
  }catch{toast('Failed','error');}
}

async function openWeeksModal(courseId) {
  document.getElementById('modal-weeks-course-name').textContent=courseId;
  openModal('modal-weeks');
  const tbody=document.getElementById('modal-weeks-body');
  tbody.innerHTML='<tr><td colspan="4" style="color:var(--muted);text-align:center;">Loading...</td></tr>';
  try{
    const r=await fetch(`${API}/admin/courses/${courseId}/weeks`);
    const d=await r.json();
    const weeks=d.weeks||[];
    if(!weeks.length){tbody.innerHTML='<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:16px;">No weeks yet</td></tr>';return;}
    tbody.innerHTML=weeks.map(w=>`
      <tr>
        <td><span class="badge badge-blue">${w.id}</span></td>
        <td>${w.title}</td>
        <td style="font-size:0.8em;color:var(--muted);">${w.release_date||'—'}</td>
        <td style="font-size:0.8em;color:var(--muted);">${w.due_date||'—'}</td>
        <td style="display:flex;gap:6px;">
          <button class="btn btn-ghost btn-sm" onclick="openEditWeek('${courseId}','${w.id}')">✏️ Edit</button>
          <a href="${APP}/${courseId}/${w.id}" target="_blank" class="btn btn-ghost btn-sm">↗</a>
          <button class="btn btn-warning btn-sm" onclick="resetSubmissions('${courseId}','${w.id}')" title="Delete all student submissions for this week">🔄 Reset</button>
        </td>
      </tr>`).join('');
  }catch{tbody.innerHTML='<tr><td colspan="4" style="color:var(--muted);">Error</td></tr>';}
}

async function resetSubmissions(courseId,weekId){
  if(!confirm(`Delete ALL student submissions for ${courseId}/${weekId}?\nThis cannot be undone.`))return;
  const r=await fetch(`${API}/admin/courses/${encodeURIComponent(courseId)}/weeks/${encodeURIComponent(weekId)}/submissions`,{method:'DELETE'});
  const d=await r.json();
  if(r.ok)showToast(`Submissions reset — ${d.logs_deleted} log(s) deleted`);
  else showToast('Reset failed: '+(d.detail||r.status),true);
}

async function openEditWeek(courseId,weekId) {
  try{
    const r=await fetch(`${API}/admin/courses/${courseId}/weeks`);
    const d=await r.json();
    const w=(d.weeks||[]).find(x=>x.id===weekId);if(!w)return;
    document.getElementById('edit-week-course-id').value=courseId;
    document.getElementById('edit-week-id').value=weekId;
    document.getElementById('edit-week-title').value=w.title||'';
    document.getElementById('edit-week-content').value=w.content||'';
    document.getElementById('edit-due-date').value=w.due_date?.replace(' ','T')||'';
    document.getElementById('edit-release-date').value=w.release_date?.replace(' ','T')||'';
    document.getElementById('edit-time-limit').value=w.time_limit_minutes||0;
    document.getElementById('edit-grace').value=w.grace_period||0;
    document.getElementById('edit-penalty').value=w.lateness_penalty||0;
    document.getElementById('edit-allow-late').checked=w.allow_late!==false;
    document.getElementById('edit-lecture-title').value=w.lecture_title||'';
    document.getElementById('edit-lecture-content').value='';
    closeModal('modal-weeks');
    openModal('modal-edit-week');
  }catch{toast('Failed to load week','error');}
}

async function saveWeekEdit() {
  const courseId=document.getElementById('edit-week-course-id').value;
  const weekId=document.getElementById('edit-week-id').value;
  const title=document.getElementById('edit-week-title').value.trim();
  if(!title){toast('Title required','error');return;}
  try{
    const r=await fetch(`${API}/admin/courses/${courseId}/weeks/${weekId}`,{
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        title,content:document.getElementById('edit-week-content').value.trim(),
        lecture_title:document.getElementById('edit-lecture-title').value.trim(),
        lecture_content:document.getElementById('edit-lecture-content').value.trim(),
        due_date:document.getElementById('edit-due-date').value.replace('T',' '),
        release_date:document.getElementById('edit-release-date').value.replace('T',' '),
        time_limit_minutes:parseInt(document.getElementById('edit-time-limit').value)||0,
        grace_period:parseInt(document.getElementById('edit-grace').value)||0,
        lateness_penalty:parseFloat(document.getElementById('edit-penalty').value)||0,
        allow_late:document.getElementById('edit-allow-late').checked
      })
    });
    if(r.ok){toast('Week updated!');closeModal('modal-edit-week');}
    else toast('Error','error');
  }catch{toast('Failed','error');}
}

function addOption(){const l=document.getElementById('options-list');const r=document.createElement('div');r.className='option-row';r.innerHTML='<input type="text" placeholder="Option"/><button class="remove-btn" onclick="removeOption(this)">✕</button>';l.appendChild(r);}
function removeOption(b){b.parentElement.remove();}
function toggleOptions(){const t=document.getElementById('q-type').value;const s=document.getElementById('options-section');if(t==='true_false'){document.getElementById('options-list').innerHTML='<div class="option-row"><input type="text" value="True" readonly/></div><div class="option-row"><input type="text" value="False" readonly/></div>';s.style.display='';}else if(t==='short_answer'){s.style.display='none';}else{s.style.display='';}}

async function addQuestion(){
  const course=document.getElementById('q-course').value;
  const week=document.getElementById('q-week').value;
  const text=document.getElementById('q-text').value.trim();
  const type=document.getElementById('q-type').value;
  const correctRaw=document.getElementById('q-correct').value.trim();
  const points=parseInt(document.getElementById('q-points').value)||1;
  if(!course||!week||!text){toast('Fill course, week, and question text','error');return;}
  const options=[...document.querySelectorAll('#options-list .option-row input')].map(i=>i.value.trim()).filter(Boolean);
  try{
    const r=await fetch(`${API}/admin/questions/${course}/${week}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question_text:text,question_type:type,options,correct_answer:correctRaw,points})});
    const d=await r.json();
    if(r.ok){toast('Question added!');document.getElementById('q-text').value='';document.getElementById('q-correct').value='';loadQuestionsView();}
    else toast(d.detail||'Error','error');
  }catch{toast('Failed','error');}
}

async function loadQuestionsView(){
  const course=document.getElementById('view-course').value;
  const week=document.getElementById('view-week').value;
  const tbody=document.getElementById('questions-table-body');
  if(!course||!week)return;
  tbody.innerHTML='<tr><td colspan="4" style="color:var(--muted);text-align:center;">Loading...</td></tr>';
  try{
    const r=await fetch(`${API}/admin/questions/${course}/${week}`);
    const data=await r.json();
    const qs=data.questions||[];
    if(!qs.length){tbody.innerHTML='<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:16px;">No questions</td></tr>';return;}
    tbody.innerHTML=qs.map(q=>`<tr><td><span class="badge badge-blue">${q.csq_name}</span></td><td style="max-width:280px;">${(q.question_text||'').substring(0,80)}${(q.question_text||'').length>80?'...':''}</td><td><span class="badge badge-purple">${q.question_type}</span></td><td><button class="btn btn-danger btn-sm" onclick="deleteQuestion('${course}','${week}','${q.csq_name}')">Delete</button></td></tr>`).join('');
  }catch{tbody.innerHTML='<tr><td colspan="4" style="color:var(--muted);">Error</td></tr>';}
}

async function deleteQuestion(c,w,csq_name){if(!confirm('Delete?'))return;try{const r=await fetch(`${API}/admin/questions/${c}/${w}/${csq_name}`,{method:'DELETE'});if(r.ok){toast('Deleted');loadQuestionsView();}else toast('Error','error');}catch{toast('Failed','error');}}

async function generateQuestionsFromNotes(){
  const c=document.getElementById('gen-course').value;
  const w=document.getElementById('gen-week').value;
  if(!c||!w){toast('Select course and week first','error');return;}
  const topic=document.getElementById('gen-topic').value.trim();
  const num=parseInt(document.getElementById('gen-num').value)||3;
  const qtype=document.getElementById('gen-type').value;
  const withHints=document.getElementById('gen-hints').value==='1';
  const status=document.getElementById('gen-status');
  const preview=document.getElementById('gen-preview-section');
  const tbody=document.getElementById('gen-preview-body');
  status.textContent=`✨ Generating ${num} question${num>1?'s':''}…`;
  preview.style.display='none';
  try{
    const r=await fetch(`${API}/admin/rag/generate-questions/${c}/${w}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic,num_questions:num,question_type:qtype,with_hints:withHints})});
    const d=await r.json();
    if(!r.ok){status.textContent='';toast(d.detail||'Generation failed','error');return;}
    const imported=d.imported||0;
    const errCount=(d.errors||[]).length;
    status.textContent=`✅ Imported ${imported}${errCount?' ('+errCount+' failed)':''}`;
    if(imported>0){
      tbody.innerHTML=(d.questions||[]).map(q=>`<tr>
        <td style="max-width:300px;">${(q.question_text||'').substring(0,100)}${(q.question_text||'').length>100?'…':''}</td>
        <td><span class="badge badge-purple">${q.question_type}</span></td>
        <td style="max-width:200px;">${(q.correct_answer||'').substring(0,60)}</td>
        <td><span class="badge badge-yellow">${q.hints_count||0}</span></td>
      </tr>`).join('');
      preview.style.display='block';
      // refresh questions table if the same week is selected
      const vc=document.getElementById('view-course').value;
      const vw=document.getElementById('view-week').value;
      if(vc===c&&vw===w)loadQuestionsView();
    }
    if(errCount)toast(`${errCount} question(s) failed to generate — check console`,'error');
  }catch(e){status.textContent='';toast('Failed: '+e.message,'error');}
}

async function deleteAllQuestions(){const c=document.getElementById('view-course').value;const w=document.getElementById('view-week').value;if(!c||!w){toast('Select course and week','error');return;}if(!confirm('Delete ALL questions for this week?'))return;try{const r=await fetch(`${API}/admin/questions/${c}/${w}`,{method:'DELETE'});if(r.ok){toast('All questions deleted');loadQuestionsView();}else toast('Error','error');}catch{toast('Failed','error');}}

async function loadQuestionsForHints(){const c=document.getElementById('h-course').value;const w=document.getElementById('h-week').value;const s=document.getElementById('h-question');s.innerHTML='<option value="">Select question...</option>';if(!c||!w)return;try{const r=await fetch(`${API}/admin/questions/${c}/${w}`);const d=await r.json();(d.questions||[]).forEach(q=>s.innerHTML+=`<option value="${q.csq_name}">${(q.question_text||'').substring(0,60)}...</option>`);}catch{}}

async function loadHintsTable(){const c=document.getElementById('hint-view-course').value;const w=document.getElementById('hint-view-week').value;const tb=document.getElementById('hints-table-body');if(!c||!w){tb.innerHTML='<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:20px;">Select course and week</td></tr>';return;}tb.innerHTML='<tr><td colspan="5" style="color:var(--muted);text-align:center;">Loading...</td></tr>';try{const r=await fetch(`${API}/admin/questions/${c}/${w}`);const d=await r.json();const qs=d.questions||[];if(!qs.length){tb.innerHTML='<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:16px;">No questions</td></tr>';return;}const rows=await Promise.all(qs.map(async q=>{let hintCount='—';try{const hr=await fetch(`${API}/admin/hints/${c}/${w}/${q.csq_name}`);const hd=await hr.json();hintCount=(hd.hints||[]).length;}catch{}return`<tr><td><span class="badge badge-blue">${q.csq_name}</span></td><td style="max-width:280px;">${(q.question_text||'').substring(0,80)}${(q.question_text||'').length>80?'...':''}</td><td><span class="badge badge-purple">${q.question_type}</span></td><td><span class="badge badge-yellow">${hintCount}</span></td><td><button class="btn btn-ghost btn-sm" onclick="editQuestionHints('${c}','${w}','${q.csq_name}')">Edit</button> <button class="btn btn-danger btn-sm" onclick="deleteQuestionHints('${c}','${w}','${q.csq_name}')">Delete</button></td></tr>`;}));tb.innerHTML=rows.join('');}catch{tb.innerHTML='<tr><td colspan="5" style="color:var(--muted);">Error</td></tr>';}}

async function loadExistingHints(){const c=document.getElementById('h-course').value;const w=document.getElementById('h-week').value;const csq=document.getElementById('h-question').value;['hint-1','hint-2','hint-3','hint-4','hint-5'].forEach(id=>document.getElementById(id).value='');if(!csq||!c||!w)return;try{const r=await fetch(`${API}/admin/hints/${c}/${w}/${csq}`);const d=await r.json();const hints=d.hints||[];hints.forEach(h=>{const el=document.getElementById('hint-'+h.number);if(el)el.value=h.text;});}catch{}}

async function editQuestionHints(c,w,csq_name){document.getElementById('h-course').value=c;document.getElementById('h-week').value=w;await loadWeeksForCourse('h-course','h-week');document.getElementById('h-week').value=w;await loadQuestionsForHints();document.getElementById('h-question').value=csq_name;await loadExistingHints();document.querySelector('[onclick="showPanel(\'hints\')"]').click();}

async function deleteQuestionHints(c,w,csq_name){if(!confirm('Delete all hints for this question?'))return;try{const r=await fetch(`${API}/admin/hints/${c}/${w}/${csq_name}`,{method:'DELETE'});if(r.ok){toast('Hints deleted');loadHintsTable();}else toast('Error','error');}catch{toast('Failed','error');}}

async function deleteAllHints(){const c=document.getElementById('h-course').value;const w=document.getElementById('h-week').value;const csq=document.getElementById('h-question').value;if(!csq){toast('Select a question first','error');return;}if(!confirm('Delete ALL hints for this question?'))return;try{const r=await fetch(`${API}/admin/hints/${c}/${w}/${csq}`,{method:'DELETE'});if(r.ok){toast('All hints deleted!');['hint-1','hint-2','hint-3','hint-4','hint-5'].forEach(id=>document.getElementById(id).value='');loadHintsTable();}else toast('Error','error');}catch{toast('Failed','error');}}

async function generateSingleHintAI(num){const c=document.getElementById('h-course').value;const w=document.getElementById('h-week').value;const csq=document.getElementById('h-question').value;const s=document.getElementById('h-question');const qt=s.options[s.selectedIndex]?.text;if(!csq){toast('Select a question first','error');return;}document.getElementById('h-status').textContent=`✨ Generating Hint ${num}...`;try{const r=await fetch(`${API}/admin/hints/generate-single/${c}/${w}/${csq}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question_text:qt,hint_number:num})});const d=await r.json();if(r.ok&&d.hint){document.getElementById('hint-'+num).value=d.hint;toast(`Hint ${num} generated!`);}else toast(d.detail||'Error','error');}catch{toast('Failed','error');}document.getElementById('h-status').textContent='';}

async function loadHintStats(){const c=document.getElementById('hint-view-course').value;const w=document.getElementById('hint-view-week').value;if(!c||!w)return;try{const r=await fetch(`${API}/admin/hints/stats/${c}/${w}`);const d=await r.json();document.getElementById('hint-total-questions').textContent=d.questions_with_hints||0;document.getElementById('hint-total-hints').textContent=d.total_hints||0;document.getElementById('hint-avg-usage').textContent='—';document.getElementById('hint-low-score').textContent='—';}catch{}}

async function saveHints(){const c=document.getElementById('h-course').value;const w=document.getElementById('h-week').value;const csq=document.getElementById('h-question').value;const hints=[];for(let i=1;i<=5;i++){const v=document.getElementById('hint-'+i).value.trim();if(v)hints.push(v);}if(!csq||!hints.length){toast('Select question and enter at least one hint','error');return;}try{const r=await fetch(`${API}/admin/hints/${c}/${w}/${csq}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hints})});if(r.ok)toast('Hints saved!');else toast('Error','error');}catch{toast('Failed','error');}}

async function generateAllHintsAI(){const c=document.getElementById('hint-view-course').value;const w=document.getElementById('hint-view-week').value;if(!c||!w){toast('Select course and week first','error');return;}if(!confirm(`Pre-generate hints for ALL questions in ${c}/${w}? This may take several minutes.`))return;const btn=document.getElementById('btn-generate-all');if(btn){btn.disabled=true;btn.textContent='⏳ Generating...';}try{const r=await fetch(`${API}/admin/hints/generate-all/${c}/${w}`,{method:'POST'});const d=await r.json();if(r.ok){toast(`✅ Generated: ${d.generated}, Skipped: ${d.skipped}${d.errors.length?' | Errors: '+d.errors.length:''}`);loadHintsTable();}else toast(d.detail||'Error','error');}catch{toast('Failed','error');}if(btn){btn.disabled=false;btn.textContent='⚡ Pre-generate All';}}
async function generateHintsAI(){const c=document.getElementById('h-course').value;const w=document.getElementById('h-week').value;const csq=document.getElementById('h-question').value;const s=document.getElementById('h-question');const qt=s.options[s.selectedIndex]?.text;if(!csq){toast('Select a question first','error');return;}document.getElementById('h-status').textContent='✨ Generating...';try{const r=await fetch(`${API}/admin/hints/generate/${c}/${w}/${csq}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question_text:qt})});const d=await r.json();if(r.ok&&d.hints){['hint-1','hint-2','hint-3','hint-4','hint-5'].forEach(id=>document.getElementById(id).value='');d.hints.forEach((h,i)=>{const el=document.getElementById('hint-'+(i+1));if(el)el.value=h;});toast('Hints generated!');}else toast(d.detail||'Error','error');}catch{toast('Failed','error');}document.getElementById('h-status').textContent='';}

async function loadAttempts(){const c=document.getElementById('att-course').value;const w=document.getElementById('att-week').value;const tb=document.getElementById('attempts-table-body');if(!c||!w)return;tb.innerHTML='<tr><td colspan="4" style="color:var(--muted);text-align:center;">Loading...</td></tr>';try{const r=await fetch(`${API}/${c}/${w}/grades`);const d=await r.json();const a=d.grades||[];if(!a.length){tb.innerHTML='<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:16px;">No submissions yet</td></tr>';return;}tb.innerHTML=a.map(x=>`<tr><td>${escapeHtml(x.username)}</td><td><span class="badge badge-green">${escapeHtml(String(x.score))}/${escapeHtml(String(x.total))}</span></td><td><span class="badge ${x.percent>=70?'badge-green':x.percent>=40?'badge-yellow':'badge-red'}">${escapeHtml(String(x.percent))}%</span></td><td style="color:var(--muted);font-size:0.8em;">${escapeHtml((x.last_submit||'').substring(0,16))||'—'}</td></tr>`).join('');}catch{tb.innerHTML='<tr><td colspan="4" style="color:var(--muted);">Error loading grades</td></tr>';}}

async function publishQuiz() {
  // No-op: questions are written directly to quiz.catsoop on creation/deletion.
}

let liveSocket=null;
let liveStudents={};

function prependFeed(feed, safeHtml) {
  const div = document.createElement('div');
  div.innerHTML = safeHtml;
  feed.insertBefore(div.firstChild, feed.firstChild);
  while (feed.children.length > 50) feed.removeChild(feed.lastChild);
}

function connectLiveSession() {
  const course=document.getElementById('live-course').value;
  const week=document.getElementById('live-week').value;
  const status=document.getElementById('live-connection-status');
  const grid=document.getElementById('live-student-grid');
  const feed=document.getElementById('live-feed');
  if(!course||!week){status.textContent='Select course and week to start monitoring.';grid.innerHTML='';return;}
  if(liveSocket){liveSocket.close();liveSocket=null;}
  liveStudents={};
  status.textContent='🔄 Connecting...';
  const wsUrl=API.replace('http://','').replace('https://','');
  const proto=API.startsWith('https')?'wss:':'ws:';
  liveSocket=new WebSocket(`${proto}//${wsUrl}/ws?token=${encodeURIComponent(getToken())}`);
  liveSocket.onopen=()=>{
    liveSocket.send(JSON.stringify({type:'JOIN',username:'Instructor',room:course+'/'+week}));
    status.textContent='🟢 Connected to '+course+'/'+week;
    feed.innerHTML='<div style="color:var(--muted);padding:4px;">Connected. Waiting for student activity...</div>';
    renderLiveGrid();
  };
  liveSocket.onclose=()=>{status.textContent='🔴 Disconnected';liveSocket=null;};
  loadMonitoringPanel();
  liveSocket.onmessage=(e)=>{
    try{
      const msg=JSON.parse(e.data);
      const ts=new Date().toLocaleTimeString();
      if(msg.type==='STUDENT_JOIN'){
        if(!liveStudents[msg.username])liveStudents[msg.username]={username:msg.username,affect:'unknown',score:'—',hints:0,questions:0,lastSeen:Date.now()};
        prependFeed(feed,'<div style="color:var(--green);font-size:0.82em;">'+escapeHtml(ts)+' → '+escapeHtml(msg.username)+' joined</div>');
      }else if(msg.type==='STUDENT_LEAVE'){
        prependFeed(feed,'<div style="color:var(--red);font-size:0.82em;">'+escapeHtml(ts)+' ← '+escapeHtml(msg.username)+' left</div>');
        delete liveStudents[msg.username];
      }else if(msg.type==='SUBMISSION'){
        if(liveStudents[msg.username]){liveStudents[msg.username].score=msg.score||'✓';liveStudents[msg.username].questions=(liveStudents[msg.username].questions||0)+1;liveStudents[msg.username].lastSeen=Date.now();}
        prependFeed(feed,'<div style="color:var(--accent);font-size:0.82em;">'+escapeHtml(ts)+' 📝 '+escapeHtml(msg.username)+' '+(msg.score!==undefined?'scored '+escapeHtml(String(msg.score)):'submitted')+'</div>');
      }else if(msg.type==='AFFECT_CHANGE'){
        if(liveStudents[msg.username]){liveStudents[msg.username].affect=msg.affect_state;liveStudents[msg.username].lastSeen=Date.now();}
        prependFeed(feed,'<div style="font-size:0.82em;">'+escapeHtml(ts)+' 👤 '+escapeHtml(msg.username)+' → '+escapeHtml(msg.affect_state||'')+'</div>');
      }else if(msg.type==='HINT_USED'){
        if(liveStudents[msg.username]){liveStudents[msg.username].hints=(liveStudents[msg.username].hints||0)+1;liveStudents[msg.username].lastSeen=Date.now();}
        prependFeed(feed,'<div style="color:var(--yellow);font-size:0.82em;">'+escapeHtml(ts)+' 💡 '+escapeHtml(msg.username)+' used hint</div>');
      }
      renderLiveGrid();
    }catch(e){}
  };
}

function affectColor(state){
  const colors={focused:'#22c55e',confused:'#f59e0b',disengaged:'#ef4444',distracted:'#64748b',fatigued:'#8b5cf6',unknown:'#64748b'};
  return colors[state]||colors.unknown;
}

function renderLiveGrid(){
  const grid=document.getElementById('live-student-grid');
  const entries=Object.values(liveStudents);
  if(!entries.length){grid.innerHTML='<div style="grid-column:1/-1;color:var(--muted);text-align:center;padding:20px;">No students connected yet</div>';return;}
  grid.innerHTML=entries.map(s=>{
    const color=affectColor(s.affect);
    return '<div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:12px;border-left:3px solid '+escapeHtml(color)+';">'+
      '<div style="font-weight:600;font-size:0.9em;">'+escapeHtml(s.username)+'</div>'+
      '<div style="display:flex;gap:12px;margin-top:6px;font-size:0.78em;color:var(--muted);">'+
        '<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:'+escapeHtml(color)+';margin-right:4px;"></span>'+escapeHtml(s.affect||'unknown')+'</span>'+
        '<span>📝 '+escapeHtml(String(s.score))+'</span>'+
        '<span>💡 '+escapeHtml(String(s.hints))+'</span>'+
      '</div>'+
    '</div>';
  }).join('');
}

async function loadOverview(){
  const courses=await loadCourses();
  document.getElementById('stat-courses').textContent=courses.length;
  let totalWeeks=0;
  for(const c of courses){
    try{const r=await fetch(`${API}/admin/courses/${c.id}/weeks`);const d=await r.json();totalWeeks+=(d.weeks||[]).length;}catch{}
  }
  document.getElementById('stat-weeks').textContent=totalWeeks;
}

// populateCourseDropdowns() is now called by initApp() after auth

const ICONS=['📘','📗','📙','📕','📓','📔','📒','📚','🎓','🔬','🧪','⚗️','🔭','🧮','📐','📏','🖥️','💻','⌨️','🖱️','🌐','🔢','➕','✖️','📊','📈','🧬','🦠','🌍','🌎','🌏','🗺️','📍','🧭','⚡','🔋','🔌','💡','🔦','📡','🛰️','🚀','🛸','🎯','🏆','🥇','📝','✏️','🖊️','🖋️'];

function initIconPicker(containerId,hiddenId,previewId){
  const container=document.getElementById(containerId);
  if(!container)return;
  container.innerHTML='';
  ICONS.forEach(icon=>{
    const el=document.createElement('span');
    el.className='icon-option';
    el.textContent=icon;
    el.onclick=()=>{
      container.querySelectorAll('.icon-option').forEach(e=>e.classList.remove('selected'));
      el.classList.add('selected');
      document.getElementById(hiddenId).value=icon;
      document.getElementById(previewId).textContent=icon;
    };
    container.appendChild(el);
  });
}

async function loadPerformance() {
  const tb=document.getElementById('performance-table-body');
  try{
    const r=await fetch(`${API}/admin/performance`);
    const d=await r.json();
    const perf=d.performance||[];
    if(!perf.length){tb.innerHTML='<tr><td colspan="8" style="color:var(--muted);text-align:center;padding:20px;">No performance data yet</td></tr>';return;}
    tb.innerHTML=perf.map(p=>`
      <tr>
        <td><span class="badge badge-blue">${p.course}</span></td>
        <td>${p.week}</td>
        <td>${p.total_students}</td>
        <td>${p.total_attempts}</td>
        <td><span class="badge ${p.avg_score>=70?'badge-green':p.avg_score>=40?'badge-yellow':'badge-red'}">${p.avg_score}%</span></td>
        <td>${p.max_score}%</td>
        <td>${p.min_score}%</td>
        <td>${p.hints_used}</td>
      </tr>`).join('');
  }catch{tb.innerHTML='<tr><td colspan="8" style="color:var(--muted);">Error loading performance</td></tr>';}
}

initIconPicker('icon-picker','course-icon','selected-icon-preview');
initIconPicker('edit-icon-picker','edit-course-icon','edit-selected-icon-preview');

// ── Gamification panel ──────────────────────────────────────────────────────
const BADGE_LABELS = {
  first_attempt: {label:'First Attempt', icon:'🎯'},
  streak_3:      {label:'3-Day Streak',  icon:'🔥'},
  streak_7:      {label:'7-Day Streak',  icon:'🌟'},
  top_class:     {label:'Top of Class',  icon:'🏆'},
};

async function loadGamificationPanel() {
  const course = document.getElementById('gam-course').value;
  const tbody = document.getElementById('gam-table-body');
  const breakdown = document.getElementById('gam-badge-breakdown');
  if (!course) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:20px;">Select a course to load data</td></tr>';
    breakdown.innerHTML = '<div style="color:var(--muted);font-size:0.85em;">Select a course to load badge data</div>';
    return;
  }
  tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;">Loading...</td></tr>';
  try {
    const r = await fetch(`${API}/${course}/leaderboard`);
    if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
    const d = await r.json();
    const rows = d.leaderboard || [];

    // stat cards
    const totalXP = rows.reduce((s, r) => s + r.xp, 0);
    const activeStreaks = rows.filter(r => r.streak > 0).length;
    const totalBadges = rows.reduce((s, r) => s + r.badges, 0);
    document.getElementById('gam-total-xp').textContent = totalXP.toLocaleString();
    document.getElementById('gam-active-streaks').textContent = activeStreaks;
    document.getElementById('gam-total-badges').textContent = totalBadges;
    document.getElementById('gam-student-count').textContent = rows.length;

    // leaderboard table
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:16px;">No students have earned XP yet</td></tr>';
    } else {
      const rankIcons = ['🥇','🥈','🥉'];
      tbody.innerHTML = rows.map(row => `
        <tr>
          <td style="font-family:var(--mono);font-weight:600;">${rankIcons[row.rank-1]||escapeHtml(String(row.rank))}</td>
          <td>${escapeHtml(row.username)}</td>
          <td><span class="badge badge-blue">${escapeHtml(row.xp.toLocaleString())} XP</span></td>
          <td style="color:${row.streak>=7?'var(--yellow)':row.streak>=3?'var(--accent)':'var(--muted)'};">${row.streak > 0 ? '🔥 ' + escapeHtml(String(row.streak)) : '—'}</td>
          <td>${row.badges > 0 ? '<span class="badge badge-green">'+escapeHtml(String(row.badges))+'</span>' : '<span style="color:var(--muted);">—</span>'}</td>
        </tr>`).join('');
    }

    // badge breakdown — fetch individual stats per student
    const badgeCounts = {};
    await Promise.all(rows.map(async row => {
      try {
        const sr = await fetch(`${API}/${course}/my-stats?username=${encodeURIComponent(row.username)}`);
        const sd = await sr.json();
        (sd.badges || []).forEach(b => { badgeCounts[b.type] = (badgeCounts[b.type] || 0) + 1; });
      } catch {}
    }));

    const maxBadge = Math.max(1, ...Object.values(badgeCounts));
    const badgeHtml = Object.entries(BADGE_LABELS).map(([type, meta]) => {
      const count = badgeCounts[type] || 0;
      const pct = Math.round((count / (rows.length || 1)) * 100);
      const barW = Math.round((count / maxBadge) * 100);
      return `<div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:1.1em;min-width:24px;">${meta.icon}</span>
        <div style="flex:1;">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:0.82em;color:var(--text);">${meta.label}</span>
            <span style="font-family:var(--mono);font-size:0.78em;color:var(--muted);">${count} student${count!==1?'s':''} (${pct}%)</span>
          </div>
          <div style="height:6px;background:var(--surface2);border-radius:3px;overflow:hidden;">
            <div style="height:100%;width:${barW}%;background:var(--accent);border-radius:3px;transition:width 0.4s;"></div>
          </div>
        </div>
      </div>`;
    }).join('');
    breakdown.innerHTML = badgeHtml || '<div style="color:var(--muted);font-size:0.85em;">No badges earned yet</div>';
  } catch(e) {
    console.error('[gamification panel]', e);
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;">Error: ' + e.message + '</td></tr>';
  }
}

// ── Face Auth panel ─────────────────────────────────────────────────────────
async function loadFaceAuthPanel() {
  const tbody = document.getElementById('fa-table-body');
  tbody.innerHTML = '<tr><td colspan="3" style="color:var(--muted);text-align:center;">Loading...</td></tr>';
  try {
    const r = await fetch(`${API}/admin/face-enrollments`);
    if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
    const d = await r.json();
    const rows = d.enrollments || [];
    document.getElementById('fa-count').textContent = rows.length;
    tbody.innerHTML = rows.length
      ? rows.map(e => `<tr>
          <td style="font-family:var(--mono);">${escapeHtml(e.username)}</td>
          <td style="color:var(--muted);font-size:0.85em;">${escapeHtml((e.enrolled_at||'').substring(0,16))}</td>
          <td><button class="btn btn-danger btn-sm" onclick="resetFaceEnroll('${escapeHtml(e.username)}')">Reset</button></td>
        </tr>`).join('')
      : '<tr><td colspan="3" style="color:var(--muted);text-align:center;padding:16px;">No students enrolled yet</td></tr>';
  } catch(e) {
    console.error('[face-auth panel]', e);
    tbody.innerHTML = '<tr><td colspan="3" style="color:var(--muted);text-align:center;">Error: ' + e.message + '</td></tr>';
  }
}

async function resetFaceEnroll(username) {
  if (!confirm(`Reset face enrollment for "${username}"? They will be prompted to re-enroll on their next quiz visit.`)) return;
  try {
    const r = await fetch(`${API}/admin/face-enrollments/${username}`, {method:'DELETE'});
    if (r.ok) { toast('Enrollment reset'); loadFaceAuthPanel(); }
    else { const d = await r.json(); toast(d.detail || 'Error', 'error'); }
  } catch { toast('Failed to reset', 'error'); }
}

// ─── Student password reset ──────────────────────────────────────────────────

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

var _resetPwTarget = '';

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

// ─── Student monitoring ───────────────────────────────────────────────────────

async function loadMonitoringPanel() {
  const c = document.getElementById('live-course').value;
  const w = document.getElementById('live-week').value;
  if (!c || !w) { return; }
  document.getElementById('live-history-label').textContent = c + ' / ' + w;
  const tbody = document.getElementById('mon-table-body');
  tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:20px;">Loading...</td></tr>';
  try {
    const r = await fetch(`${API}/admin/engagement/${encodeURIComponent(c)}/${encodeURIComponent(w)}`);
    if (!r.ok) { toast('Failed to load monitoring data','error'); return; }
    const d = await r.json();
    document.getElementById('mon-total-students').textContent = d.total_students;
    document.getElementById('mon-total-samples').textContent = d.total_samples;
    document.getElementById('mon-avg-score').textContent = d.avg_engagement;
    document.getElementById('mon-avg-face').textContent = d.avg_face_pct + '%';
    if (!d.students.length) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:20px;">No monitoring data for this week yet</td></tr>';
      return;
    }
    tbody.innerHTML = d.students.map(s => {
      const scoreColor = s.avg_engagement >= 70 ? 'var(--green)' : s.avg_engagement >= 40 ? '#f59e0b' : 'var(--red)';
      const faceColor  = s.face_pct >= 70 ? 'var(--green)' : '#f59e0b';
      const lastSeen   = s.last_seen ? new Date(s.last_seen).toLocaleString() : '—';
      return `<tr>
        <td><strong>${escapeHtml(s.username)}</strong></td>
        <td style="text-align:center;">${s.sessions}</td>
        <td style="text-align:center;">${s.samples}</td>
        <td style="text-align:center;color:${scoreColor};font-weight:600;">${s.avg_engagement}</td>
        <td style="text-align:center;color:${faceColor};font-weight:600;">${s.face_pct}%</td>
        <td style="text-align:center;color:var(--green);">${s.affect.focused}</td>
        <td style="text-align:center;color:var(--red);">${s.affect.disengaged}</td>
        <td style="text-align:center;color:var(--muted);">${s.affect.distracted}</td>
        <td style="font-size:0.8em;color:var(--muted);">${escapeHtml(lastSeen)}</td>
      </tr>`;
    }).join('');
  } catch(e) { toast('Error: ' + e.message, 'error'); }
}

// ─── Lecturer management ──────────────────────────────────────────────────────

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
  // Populate course select
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
