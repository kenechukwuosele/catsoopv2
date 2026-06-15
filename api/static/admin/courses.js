// Course & week management, overview, grades/queue panels, icon picker

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

async function loadOverview(){
  const courses=await loadCourses();
  document.getElementById('stat-courses').textContent=courses.length;
  let totalWeeks=0;
  for(const c of courses){
    try{const r=await fetch(`${API}/admin/courses/${c.id}/weeks`);const d=await r.json();totalWeeks+=(d.weeks||[]).length;}catch{}
  }
  document.getElementById('stat-weeks').textContent=totalWeeks;
}
