// Loaded last — orchestrates all panels, startup, and icon pickers.
// All feature modules (auth, ui-core, courses, questions-hints,
// monitoring, students, gamification) must be loaded before this file.

function initApp() {
  populateCourseDropdowns();
  loadOverview();
  const sel = document.getElementById('pw-course-select');
  if (sel) {
    populateCourseSelect(sel, __cuSession.role === 'lecturer' ? __cuSession.courses : null);
  }
}

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

// Initialize icon pickers (runs once when this script loads, after DOM is ready)
initIconPicker('icon-picker','course-icon','selected-icon-preview');
initIconPicker('edit-icon-picker','edit-course-icon','edit-selected-icon-preview');

// Startup: restore session from stored token or show login
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
