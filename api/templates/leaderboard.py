from .config import SERVER_BASE_URL

LEADERBOARD_SENTINEL = "<!-- __CU_LEADERBOARD__ -->"


def generate_leaderboard_page(course: str) -> str:
    base = SERVER_BASE_URL
    return f"""<python>
cs_content_header = "Leaderboard"
import os as _os
try:
    cs_username = cs_user_info.get('username', '')
except Exception:
    cs_username = ''
_cu_secret = _os.environ.get("CU_QUIZ_SECRET", "")
_cu_admins = {{u.strip() for u in _os.environ.get("CU_QUIZ_ADMINS", "").split(",") if u.strip()}}
_cu_token = ""
if cs_username and _cu_secret:
    try:
        import jwt as _jwt, time as _time
        _cu_token = _jwt.encode({{"sub": cs_username, "is_admin": cs_username in _cu_admins,
                                  "iat": int(_time.time()), "exp": int(_time.time())+8*3600}},
                                 _cu_secret, algorithm="HS256")
    except Exception:
        _cu_token = ""
print('<script>window.__cs_username = "' + cs_username + '"; window.__CU_TOKEN = "' + _cu_token + '"; window.__CU_API_BASE = "{base}";</script>')
print('<script>(function(){{var t=window.__CU_TOKEN;if(!t)return;var _f=window.fetch.bind(window);window.fetch=function(u,o){{o=o||{{}};var us=typeof u==="string"?u:(u&&u.url)||"";if(us.indexOf(window.__CU_API_BASE)===0){{var h=new Headers(o.headers||{{}});if(!h.has("Authorization"))h.set("Authorization","Bearer "+t);o.headers=h;}}return _f(u,o);}};}})();</script>')
</python>

<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
#__lb-page {{
  font-family: 'Nunito', ui-rounded, sans-serif;
  max-width: 660px;
  margin: 0 auto;
  color: #3c3c3c;
}}
#__lb-page .__lbp-heading {{
  font-size: 28px;
  font-weight: 900;
  color: #1c1c1c;
  margin: 0 0 4px;
  letter-spacing: -0.02em;
}}
#__lb-page .__lbp-sub {{
  font-size: 14px;
  color: #777;
  margin: 0 0 28px;
}}
#__lb-page .__lbp-podium {{
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 24px;
}}
#__lb-page .__lbp-pod {{
  text-align: center;
  width: 130px;
  flex-shrink: 0;
  animation: __lbpUp .5s cubic-bezier(.22,1,.36,1) both;
}}
#__lb-page .__lbp-pod:nth-child(1) {{ animation-delay:.08s; }}
#__lb-page .__lbp-pod:nth-child(2) {{ animation-delay:0s; }}
#__lb-page .__lbp-pod:nth-child(3) {{ animation-delay:.16s; }}
@keyframes __lbpUp {{
  from {{ opacity:0; transform:translateY(14px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
#__lb-page .__lbp-medal {{ font-size: 28px; margin-bottom: 6px; }}
#__lb-page .__lbp-platform {{
  border-radius: 12px 12px 0 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: flex-end;
  padding: 12px 8px 12px;
  border: 2px solid transparent;
  border-bottom: none;
}}
#__lb-page .__lbp-platform.p1 {{ background: #fff9e6; border-color: #ffc800; height: 104px; }}
#__lb-page .__lbp-platform.p2 {{ background: #f4f6f9; border-color: #c8d0dc; height: 82px; }}
#__lb-page .__lbp-platform.p3 {{ background: #fff3ec; border-color: #f5b88e; height: 66px; }}
#__lb-page .__lbp-pname {{
  font-size: 12px; font-weight: 800; color: #3c3c3c;
  max-width: 116px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
#__lb-page .__lbp-pxp {{ font-size: 12px; color: #777; margin-top: 3px; font-weight: 600; }}
#__lb-page .__lbp-pxp b {{ color: #1cb0f6; }}
#__lb-page .__lbp-scroll {{
  max-height: 420px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #e5e5e5 transparent;
  margin-bottom: 20px;
}}
#__lb-page .__lbp-row {{
  display: grid;
  grid-template-columns: 36px 1fr 80px 64px 52px;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border-radius: 12px;
  margin-bottom: 4px;
  background: #fff;
  border: 2px solid #e5e5e5;
  font-size: 14px;
  font-weight: 600;
  transition: border-color .15s;
  animation: __lbRowIn .35s ease both;
}}
#__lb-page .__lbp-row:hover {{ border-color: #d0d0d0; }}
#__lb-page .__lbp-row.me {{
  background: #f0fef4;
  border-color: #58cc02;
}}
@keyframes __lbRowIn {{
  from {{ opacity:0; transform:translateX(-8px); }}
  to   {{ opacity:1; transform:translateX(0); }}
}}
#__lb-page .__lr-rank {{ text-align:center; font-size:13px; color:#afafaf; font-weight:700; }}
#__lb-page .__lr-name {{ color:#3c3c3c; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
#__lb-page .__lr-name.me {{ color:#58cc02; }}
#__lb-page .__lr-xp {{ text-align:right; color:#1cb0f6; }}
#__lb-page .__lr-streak {{ text-align:right; color:#ff4b4b; }}
#__lb-page .__lr-badges {{ text-align:right; color:#afafaf; font-size:13px; }}
#__lb-page .__lbp-mycard {{
  background: #f0fef4;
  border: 2px solid #58cc02;
  border-radius: 16px;
  padding: 16px 20px;
}}
#__lb-page .__lbp-mycard-title {{ font-size: 13px; font-weight: 800; color: #58cc02; text-transform: uppercase; letter-spacing: .08em; margin: 0 0 10px; }}
#__lb-page .__lbp-chips {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }}
#__lb-page .__lbp-chip {{
  padding: 5px 14px; border-radius: 20px;
  font-size: 13px; font-weight: 800;
  display: inline-flex; align-items: center; gap: 4px;
}}
#__lb-page .__lbp-chip.rank {{ background: #e8e0ff; color: #7c3aed; }}
#__lb-page .__lbp-chip.xp {{ background: #dcf3ff; color: #0086c9; }}
#__lb-page .__lbp-chip.streak {{ background: #ffe8e8; color: #e53333; }}
#__lb-page .__lbp-badgelist {{ display: flex; gap: 7px; flex-wrap: wrap; }}
#__lb-page .__lbp-badge {{
  padding: 4px 12px; border-radius: 20px;
  background: #fff9c6; color: #8a6400;
  font-size: 12px; font-weight: 700;
  border: 1.5px solid #ffc800;
}}
#__lb-page .__lbp-empty {{ text-align:center; padding:32px; color:#afafaf; font-size:14px; font-weight:600; }}
</style>

<div id="__lb-page">
  <p class="__lbp-heading">🏆 {course} Leaderboard</p>
  <p class="__lbp-sub">Top students ranked by XP</p>
  <div class="__lbp-podium" id="__lbp-podium"></div>
  <div class="__lbp-scroll"><div class="__lbp-rows" id="__lbp-rows"></div></div>
  <div id="__lbp-mycard" style="display:none;">
    <p class="__lbp-mycard-title">Your stats</p>
    <div class="__lbp-chips" id="__lbp-chips"></div>
    <div class="__lbp-badgelist" id="__lbp-badgelist"></div>
  </div>
</div>

<script>
(function() {{
  var BASE = '{base}';
  var COURSE = '{course}';
  var username = window.__cs_username || '';

  var MEDALS = ['🥇','🥈','🥉'];
  var PCLS   = ['p1','p2','p3'];
  var ORDER  = [1,0,2];

  function renderPodium(rows) {{
    var el = document.getElementById('__lbp-podium');
    if (!el || !rows.length) return;
    var html = '';
    ORDER.forEach(function(i) {{
      if (!rows[i]) return;
      var r = rows[i];
      var me = r.username === username;
      html += '<div class="__lbp-pod">' +
        '<div class="__lbp-medal">' + MEDALS[i] + '</div>' +
        '<div class="__lbp-platform ' + PCLS[i] + '">' +
          '<div class="__lbp-pname">' + r.username + (me ? ' (you)' : '') + '</div>' +
          '<div class="__lbp-pxp">⭐ <b>' + r.xp + '</b> XP</div>' +
        '</div>' +
      '</div>';
    }});
    el.innerHTML = html;
  }}

  function renderRows(rows) {{
    var el = document.getElementById('__lbp-rows');
    if (!el || rows.length <= 3) return;
    var html = '';
    rows.slice(3).forEach(function(r, idx) {{
      var me = r.username === username;
      html += '<div class="__lbp-row' + (me ? ' me' : '') + '" style="animation-delay:' + (idx*45) + 'ms">' +
        '<div class="__lr-rank">' + r.rank + '</div>' +
        '<div class="__lr-name' + (me ? ' me' : '') + '">' + r.username + (me ? ' <span style="font-weight:600;font-size:11px;">(you)</span>' : '') + '</div>' +
        '<div class="__lr-xp">⭐ ' + r.xp + '</div>' +
        '<div class="__lr-streak">🔥 ' + r.streak + '</div>' +
        '<div class="__lr-badges">' + (r.badges || 0) + ' 🏅</div>' +
      '</div>';
    }});
    el.innerHTML = html;
    var meRow = el.querySelector('.me');
    if (meRow) setTimeout(function() {{ meRow.scrollIntoView({{block:'center', behavior:'smooth'}}); }}, 350);
  }}

  fetch(BASE + '/' + COURSE + '/leaderboard')
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      var rows = d.leaderboard || [];
      if (!rows.length) {{
        document.getElementById('__lbp-podium').innerHTML =
          '<p class="__lbp-empty">No scores yet — be the first to complete a quiz!</p>';
        return;
      }}
      renderPodium(rows);
      renderRows(rows);
    }}).catch(function() {{
      document.getElementById('__lbp-podium').innerHTML =
        '<p style="color:#ef4444;font-size:14px;">Could not load leaderboard.</p>';
    }});

  if (username) {{
    fetch(BASE + '/' + COURSE + '/my-stats?username=' + encodeURIComponent(username))
      .then(function(r) {{ return r.json(); }})
      .then(function(d) {{
        var card = document.getElementById('__lbp-mycard');
        if (!card) return;
        card.style.display = 'block';
        var chips = document.getElementById('__lbp-chips');
        if (chips) {{
          chips.innerHTML =
            '<span class="__lbp-chip rank"># ' + (d.rank || '—') + '</span>' +
            '<span class="__lbp-chip xp">⭐ ' + (d.xp || 0) + ' XP</span>' +
            '<span class="__lbp-chip streak">🔥 ' + (d.streak || 0) + ' day streak</span>';
        }}
        var bl = document.getElementById('__lbp-badgelist');
        if (bl) {{
          if (d.badges && d.badges.length) {{
            bl.innerHTML = d.badges.map(function(b) {{
              return '<span class="__lbp-badge">' + b.icon + ' ' + b.label + '</span>';
            }}).join('');
          }} else {{
            bl.innerHTML = '<span style="color:#afafaf;font-size:13px;font-weight:600;">No badges yet — keep going!</span>';
          }}
        }}
      }}).catch(function() {{}});
  }}
}})();
</script>
"""


def generate_leaderboard_widget(course: str) -> str:
    base = SERVER_BASE_URL
    return f"""<python>
import os as _os
try:
    cs_username = cs_user_info.get('username', '')
except Exception:
    cs_username = ''
_cu_secret = _os.environ.get("CU_QUIZ_SECRET", "")
_cu_admins = {{u.strip() for u in _os.environ.get("CU_QUIZ_ADMINS", "").split(",") if u.strip()}}
_cu_token = ""
if cs_username and _cu_secret:
    try:
        import jwt as _jwt, time as _time
        _cu_token = _jwt.encode({{"sub": cs_username, "is_admin": cs_username in _cu_admins,
                                  "iat": int(_time.time()), "exp": int(_time.time())+8*3600}},
                                 _cu_secret, algorithm="HS256")
    except Exception:
        _cu_token = ""
print('<script>window.__cs_username = window.__cs_username || "' + cs_username + '"; window.__CU_TOKEN = window.__CU_TOKEN || "' + _cu_token + '"; window.__CU_API_BASE = window.__CU_API_BASE || "{base}";</script>')
print('<script>(function(){{if(window.__cuFetchInstalled)return;window.__cuFetchInstalled=true;var t=window.__CU_TOKEN;if(!t)return;var _f=window.fetch.bind(window);window.fetch=function(u,o){{o=o||{{}};var us=typeof u==="string"?u:(u&&u.url)||"";if(us.indexOf(window.__CU_API_BASE)===0){{var h=new Headers(o.headers||{{}});if(!h.has("Authorization"))h.set("Authorization","Bearer "+t);o.headers=h;}}return _f(u,o);}};}})();</script>')
</python>
{LEADERBOARD_SENTINEL}
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
#__lb-widget {{
  font-family: 'Nunito', ui-rounded, sans-serif;
  border-top: 2px solid #e5e5e5;
  margin-top: 48px;
  padding-top: 32px;
  color: #3c3c3c;
}}
#__lb-widget .__lbw-head {{
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 6px;
}}
#__lb-widget .__lbw-title {{
  font-size: 20px; font-weight: 900;
  color: #1c1c1c; letter-spacing: -0.02em; margin: 0;
}}
#__lb-widget .__lbw-sub {{
  font-size: 13px; color: #afafaf; font-weight: 600; margin: 0 0 22px;
}}
#__lb-widget .__lbw-icon {{
  background: #fff4d4; border: 2px solid #ffc800;
  border-radius: 10px; width: 34px; height: 34px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 17px; flex-shrink: 0;
}}
#__lb-podium {{
  display: flex; justify-content: center;
  align-items: flex-end; gap: 8px; margin-bottom: 20px;
}}
.__lbw-pod {{ text-align: center; width: 116px; flex-shrink: 0; }}
@keyframes __lbwUp {{
  from {{ opacity:0; transform:translateY(12px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
.__lbw-pod {{ animation: __lbwUp .48s cubic-bezier(.22,1,.36,1) both; }}
.__lbw-pod:nth-child(1) {{ animation-delay:.08s; }}
.__lbw-pod:nth-child(2) {{ animation-delay:0s; }}
.__lbw-pod:nth-child(3) {{ animation-delay:.16s; }}
.__lbw-medal {{ font-size: 26px; margin-bottom: 5px; }}
.__lbw-platform {{
  border-radius: 10px 10px 0 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: flex-end;
  padding: 10px 6px 10px;
  border: 2px solid transparent; border-bottom: none;
}}
.__lbw-platform.w1 {{ background:#fff9e6; border-color:#ffc800; height:96px; }}
.__lbw-platform.w2 {{ background:#f4f6f9; border-color:#c8d0dc; height:76px; }}
.__lbw-platform.w3 {{ background:#fff3ec; border-color:#f5b88e; height:62px; }}
.__lbw-pname {{
  font-size: 11px; font-weight: 800; color: #3c3c3c;
  max-width: 104px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.__lbw-pxp {{ font-size: 11px; color: #afafaf; margin-top: 3px; font-weight: 700; }}
.__lbw-pxp b {{ color: #1cb0f6; }}
.__lbw-scroll {{
  max-height: 320px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #e5e5e5 transparent;
  margin-bottom: 16px;
}}
.__lbw-row {{
  display: grid;
  grid-template-columns: 32px 1fr 72px 54px 44px;
  align-items: center; gap: 6px;
  padding: 9px 12px; border-radius: 10px; margin-bottom: 4px;
  background: #fff; border: 2px solid #e5e5e5;
  font-size: 13px; font-weight: 700;
  transition: border-color .15s;
  animation: __lbwRowIn .32s ease both;
}}
.__lbw-row:hover {{ border-color: #cfcfcf; }}
.__lbw-row.me {{ background:#f0fef4; border-color:#58cc02; }}
@keyframes __lbwRowIn {{
  from {{ opacity:0; transform:translateX(-8px); }}
  to   {{ opacity:1; transform:translateX(0); }}
}}
.__lwr-rank {{ text-align:center; color:#c8c8c8; font-size:12px; }}
.__lwr-name {{ color:#3c3c3c; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.__lwr-name.me {{ color:#58cc02; }}
.__lwr-xp {{ text-align:right; color:#1cb0f6; }}
.__lwr-streak {{ text-align:right; color:#ff4b4b; }}
.__lwr-badges {{ text-align:right; color:#c8c8c8; font-size:12px; }}
#__lb-mine {{
  padding: 13px 16px; border-radius: 14px;
  background: #f0fef4; border: 2px solid #58cc02;
}}
.__lbm-chips {{ display:flex; gap:7px; flex-wrap:wrap; margin-bottom:9px; }}
.__lbm-chip {{
  padding:4px 12px; border-radius:20px;
  font-size:12px; font-weight:800;
}}
.__lbm-chip.rank {{ background:#ede9ff; color:#7c3aed; }}
.__lbm-chip.xp   {{ background:#dcf3ff; color:#0086c9; }}
.__lbm-chip.str  {{ background:#ffe8e8; color:#e53333; }}
.__lbm-badges {{ display:flex; gap:6px; flex-wrap:wrap; }}
.__lbm-badge {{
  padding:3px 10px; border-radius:20px;
  background:#fff9c6; color:#8a6400;
  font-size:12px; font-weight:700;
  border:1.5px solid #ffc800;
}}
.__lbw-empty {{ text-align:center; padding:24px; color:#c8c8c8; font-size:14px; font-weight:700; }}
</style>

<div id="__lb-widget">
  <div class="__lbw-head">
    <span class="__lbw-icon">🏆</span>
    <h3 class="__lbw-title">{course} Leaderboard</h3>
  </div>
  <p class="__lbw-sub">Top students ranked by XP</p>
  <div id="__lb-podium"></div>
  <div class="__lbw-scroll"><div class="__lbw-rows" id="__lb-table"></div></div>
  <div id="__lb-mine" style="display:none;">
    <div class="__lbm-chips" id="__lb-mine-chips"></div>
    <div class="__lbm-badges" id="__lb-mine-badges"></div>
  </div>
</div>

<script>
(function() {{
  var BASE = '{base}';
  var COURSE = '{course}';
  var username = '';
  try {{ username = window.__cs_username || ''; }} catch(e) {{}}

  var MEDALS = ['🥇','🥈','🥉'];
  var WCLS   = ['w1','w2','w3'];
  var ORDER  = [1,0,2];

  function renderPodium(rows) {{
    var pod = document.getElementById('__lb-podium');
    if (!pod || !rows.length) return;
    var html = '';
    ORDER.forEach(function(i) {{
      if (!rows[i]) return;
      var r = rows[i];
      var me = r.username === username;
      html += '<div class="__lbw-pod">' +
        '<div class="__lbw-medal">' + MEDALS[i] + '</div>' +
        '<div class="__lbw-platform ' + WCLS[i] + '">' +
          '<div class="__lbw-pname">' + r.username + (me ? ' (you)' : '') + '</div>' +
          '<div class="__lbw-pxp">⭐ <b>' + r.xp + '</b> XP</div>' +
        '</div>' +
      '</div>';
    }});
    pod.innerHTML = html;
  }}

  function renderRows(rows) {{
    var tbl = document.getElementById('__lb-table');
    if (!tbl || rows.length <= 3) return;
    var html = '';
    rows.slice(3).forEach(function(r, idx) {{
      var me = r.username === username;
      html += '<div class="__lbw-row' + (me ? ' me' : '') + '" style="animation-delay:' + (idx * 40) + 'ms">' +
        '<div class="__lwr-rank">' + r.rank + '</div>' +
        '<div class="__lwr-name' + (me ? ' me' : '') + '">' + r.username + (me ? ' <span style="font-weight:600;font-size:10px">(you)</span>' : '') + '</div>' +
        '<div class="__lwr-xp">⭐ ' + r.xp + '</div>' +
        '<div class="__lwr-streak">🔥 ' + r.streak + '</div>' +
        '<div class="__lwr-badges">' + (r.badges || 0) + '🏅</div>' +
      '</div>';
    }});
    tbl.innerHTML = html;
    var meRow = tbl.querySelector('.me');
    if (meRow) setTimeout(function() {{ meRow.scrollIntoView({{block:'center', behavior:'smooth'}}); }}, 350);
  }}

  fetch(BASE + '/' + COURSE + '/leaderboard')
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      var rows = d.leaderboard || [];
      if (!rows.length) {{
        document.getElementById('__lb-podium').innerHTML =
          '<div class="__lbw-empty">No scores yet — complete a quiz to appear here!</div>';
        return;
      }}
      renderPodium(rows);
      renderRows(rows);
    }}).catch(function() {{}});

  if (username) {{
    fetch(BASE + '/' + COURSE + '/my-stats?username=' + encodeURIComponent(username))
      .then(function(r) {{ return r.json(); }})
      .then(function(d) {{
        var mine = document.getElementById('__lb-mine');
        var chips = document.getElementById('__lb-mine-chips');
        var mb = document.getElementById('__lb-mine-badges');
        if (!mine) return;
        mine.style.display = 'block';
        if (chips) {{
          chips.innerHTML =
            '<span class="__lbm-chip rank"># ' + (d.rank || '—') + '</span>' +
            '<span class="__lbm-chip xp">⭐ ' + (d.xp || 0) + ' XP</span>' +
            '<span class="__lbm-chip str">🔥 ' + (d.streak || 0) + ' day streak</span>';
        }}
        if (mb && d.badges && d.badges.length) {{
          mb.innerHTML = d.badges.map(function(b) {{
            return '<span class="__lbm-badge">' + b.icon + ' ' + b.label + '</span>';
          }}).join('');
        }}
      }}).catch(function() {{}});
  }}
}})();
</script>
"""
