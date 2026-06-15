// Gamification panel, face auth panel, performance panel

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

    const totalXP = rows.reduce((s, r) => s + r.xp, 0);
    const activeStreaks = rows.filter(r => r.streak > 0).length;
    const totalBadges = rows.reduce((s, r) => s + r.badges, 0);
    document.getElementById('gam-total-xp').textContent = totalXP.toLocaleString();
    document.getElementById('gam-active-streaks').textContent = activeStreaks;
    document.getElementById('gam-total-badges').textContent = totalBadges;
    document.getElementById('gam-student-count').textContent = rows.length;

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
