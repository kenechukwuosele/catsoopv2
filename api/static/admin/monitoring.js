// Live session WebSocket, student grid, live files, engagement monitoring

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
