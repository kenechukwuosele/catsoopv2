from .config import SERVER_BASE_URL
from .affect import generate_affect_script


def generate_question_catsoop(q: dict) -> str:
    """Convert a question dict to a native CatSooP <question> block (for problem pages)."""
    qtype = q.get("type", "multiplechoice")
    text = q.get("question", "")
    answer = q.get("answer", "")
    options = q.get("options", [])
    tolerance = q.get("tolerance", "0.01")
    test_code = q.get("test_code", "")

    if qtype == "multiplechoice":
        choices = repr([str(o) for o in options]) if options else "[]"
        soln = repr(answer) if answer else '""'
        return f"""<question multiplechoice>
csq_prompt = {repr(text)}
csq_options = {choices}
csq_soln = {soln}
csq_renderer = "radio"
csq_npoints = 1
csq_soln_mode = "value"
</question>
"""
    elif qtype == "truefalse":
        soln = repr(answer) if answer else '"True"'
        return f"""<question multiplechoice>
csq_prompt = {repr(text)}
csq_options = ["True", "False"]
csq_soln = {soln}
csq_renderer = "radio"
csq_npoints = 1
csq_soln_mode = "value"
</question>
"""
    elif qtype == "shortanswer":
        return f"""<question smallbox>
csq_prompt = {repr(text)}
csq_soln = {repr(answer)}
csq_npoints = 1
csq_size = 30
</question>
"""
    elif qtype == "numerical":
        return f"""<question expression>
csq_prompt = {repr(text)}
csq_soln = [{repr(answer)}]
csq_npoints = 1
</question>
"""
    elif qtype == "symbolic":
        return f"""<question expression>
csq_prompt = {repr(text)}
csq_soln = [{repr(answer)}]
csq_npoints = 1
csq_syntax = "base"
</question>
"""
    elif qtype == "pythoncode":
        return f"""<question pythoncode>
csq_prompt = {repr(text)}
csq_initial = {repr("# Write your solution here\ndef solution():\n    pass")}
csq_soln = {repr(answer)}
csq_tests = {repr([{"code": test_code or "assert solution() is not None", "name": "Test"}])}
csq_npoints = 1
</question>
"""
    else:
        return f"""<question smallbox>
csq_prompt = {repr(text)}
csq_soln = {repr(answer)}
csq_npoints = 1
csq_size = 30
</question>
"""


def generate_native_quiz(course_id: str, week_id: str, questions: list, time_limit_minutes: int = 0) -> str:
    """
    Generate a quiz.catsoop file with native <question> tags.
    Accepts either SQLite ORM objects (legacy) or plain dicts (new file-based format).
    CatSooP handles all grading and logging natively.
    Hints are fetched from FastAPI using csq_name as the key.
    """
    import html as html_mod
    import json as json_mod

    def esc(text):
        return html_mod.escape(str(text))

    qtype_map = {
        "multiple-choice": "multiplechoice",
        "multiple_choice": "multiplechoice",
        "checkbox": "multiplechoice",
        "short-answer": "smallbox",
        "short_answer": "smallbox",
        "numerical": "expression",
        "symbolic": "expression",
        "pythoncode": "pythoncode",
    }

    question_tags = []
    question_names = []  # list of csq_names for hint JS

    for i, q in enumerate(questions):
        # Support both ORM objects and plain dicts
        if hasattr(q, "csq_name"):
            name = q.csq_name
        elif isinstance(q, dict) and q.get("csq_name"):
            name = q["csq_name"]
        else:
            qid = q.id if hasattr(q, "id") else q.get("id", i)
            name = f"q_{qid}"

        raw_type = (
            q.question_type if hasattr(q, "question_type")
            else q.get("question_type") or q.get("type", "short-answer")
        )
        text = (
            q.question_text if hasattr(q, "question_text")
            else q.get("question_text") or q.get("text", "")
        )
        options = (
            q.options if hasattr(q, "options")
            else q.get("options") or []
        )
        # Support both correct_answer (singular) and correct_answers (plural / legacy)
        if hasattr(q, "correct_answers"):
            correct = q.correct_answers or []
        elif isinstance(q, dict):
            ca = q.get("correct_answer")
            if ca is None:
                ca = q.get("correct_answers") or q.get("correctAnswers", [])
            correct = [ca] if isinstance(ca, str) else (list(ca) if ca else [])
        else:
            correct = []

        catsoop_type = qtype_map.get(raw_type, "smallbox")
        question_names.append(name)

        if catsoop_type == "multiplechoice":
            is_checkbox = raw_type in ("checkbox", "multiple_select")
            renderer = "checkbox" if is_checkbox else "radio"
            _opts = [str(o) for o in (options or [])]
            if is_checkbox:
                _soln = [str(i) in correct or i in correct for i in range(len(_opts))]
                soln_mode_line = ""
            else:
                correct_idx = next(
                    (idx for idx in range(len(_opts)) if str(idx) in correct or idx in correct or _opts[idx] in correct),
                    0,
                )
                _soln = _opts[correct_idx] if _opts else ""
                soln_mode_line = 'csq_soln_mode = "value"'
            tag = f'''<question multiplechoice>
csq_prompt = {repr(text)}
csq_options = {_opts!r}
csq_soln = {_soln!r}
csq_renderer = {renderer!r}
csq_name = {name!r}
csq_npoints = 1
csq_nsubmits = 1
{soln_mode_line}
</question>'''
        elif catsoop_type == "smallbox":
            answer = str(correct[0]) if correct else ""
            tag = f'''<question smallbox>
csq_prompt = {repr(text)}
csq_soln = {repr(answer)}
csq_name = {name!r}
csq_npoints = 1
csq_nsubmits = 1
csq_size = 30
</question>'''
        elif catsoop_type == "expression":
            answer = str(correct[0]) if correct else "0"
            tag = f'''<question expression>
csq_prompt = {repr(text)}
csq_soln = [{repr(answer)}]
csq_name = {name!r}
csq_npoints = 1
csq_nsubmits = 1
</question>'''
        elif catsoop_type == "pythoncode":
            tag = f'''<question pythoncode>
csq_prompt = {repr(text)}
csq_initial = {repr("# Write your solution here\ndef solution():\n    pass")}
csq_soln = {repr(str(correct[0]) if correct else "")}
csq_tests = {repr([{"code": "assert solution() is not None", "name": "Test"}])}
csq_name = {name!r}
csq_npoints = 1
csq_nsubmits = 1
</question>'''
        else:
            answer = str(correct[0]) if correct else ""
            tag = f'''<question smallbox>
csq_prompt = {repr(text)}
csq_soln = {repr(answer)}
csq_name = {name!r}
csq_npoints = 1
csq_nsubmits = 1
csq_size = 30
</question>'''

        question_tags.append(tag)

    question_count = len(question_tags)
    names_json = json_mod.dumps(question_names)

    header = f'''<python>
cs_content_header = "Quiz: {esc(course_id)} - {esc(week_id)}"
cs_show_due = True
cs_update_questions_cache = True
import json, os as _os
_api_base = _os.environ.get("CU_QUIZ_BASE_URL", "http://localhost:8000")
_cu_secret = _os.environ.get("CU_QUIZ_SECRET", "")
_cu_admins = {{u.strip() for u in _os.environ.get("CU_QUIZ_ADMINS", "").split(",") if u.strip()}}
_cu_token = ""
if _cu_secret:
    try:
        import jwt as _jwt, time as _time
        _cu_token = _jwt.encode(
            {{"sub": cs_username, "is_admin": cs_username in _cu_admins,
              "iat": int(_time.time()), "exp": int(_time.time()) + 8*3600}},
            _cu_secret, algorithm="HS256")
    except Exception:
        _cu_token = ""
print(f'<script data-username="{{cs_username}}">')
print(f'window.__cs_username = "{{cs_username}}";')
print(f'window.__cs_user_role = "{{cs_user_info.get("role", "Student")}}";')
print(f'window.__quizQuestionNames = {names_json};')
print(f'window.__course = "{esc(course_id)}";')
print(f'window.__week = "{esc(week_id)}";')
print(f'window.__CU_API_BASE = "{{_api_base}}";')
print(f'window.__CU_TOKEN = "{{_cu_token}}";')
print('</script>')
print('<script>')
print('(function(){{ var t=window.__CU_TOKEN; if(!t) return; var _f=window.fetch.bind(window);')
print('  window.fetch=function(url,opts){{ opts=opts||{{}}; var u=typeof url==="string"?url:(url&&url.url)||"";')
print('    if(u.indexOf(window.__CU_API_BASE)===0){{ var h=new Headers(opts.headers||{{}}); if(!h.has("Authorization")) h.set("Authorization","Bearer "+t); opts.headers=h; }}')
print('    return _f(url,opts);')
print('  }};')
print('}})();')
print('</script>')
</python>

<style>
.question {{ margin-bottom: 1.5em; }}
.hint-btn-container {{ margin-top: 8px; }}
@keyframes __fa-shake {{
  0%,100%{{ transform:translateX(0); }}
  20%{{ transform:translateX(-8px); }}
  40%{{ transform:translateX(8px); }}
  60%{{ transform:translateX(-6px); }}
  80%{{ transform:translateX(6px); }}
}}
#__xp-badge:hover {{ opacity:0.95; cursor:pointer; }}
#__xp-panel {{ display:none;position:fixed;top:48px;right:12px;z-index:998;background:#1a1f2e;border:1px solid #2d3748;border-radius:10px;padding:14px 18px;color:#fff;font-family:sans-serif;font-size:13px;min-width:200px;box-shadow:0 8px 24px rgba(0,0,0,0.5); }}
</style>
<script src="https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.14/dist/face-api.js" defer></script>

'''

    timer_label = f' ({time_limit_minutes} min)' if time_limit_minutes else ''
    start_onclick = "document.getElementById('quiz-start-screen').style.display='none';document.getElementById('quiz-questions').style.display='block';"
    if time_limit_minutes:
        start_onclick += f"localStorage.setItem('__qt_{esc(course_id)}_{esc(week_id)}',Date.now());if(window.__startQuizTimer)window.__startQuizTimer();"

    if question_count > 0:
        body = "\n\n".join(question_tags)
        body = f'''<div id="__quiz-timer-bar" style="display:none;position:sticky;top:0;z-index:1000;background:#1f2937;color:#fff;text-align:center;padding:8px;font-size:14px;font-family:sans-serif;">
  ⏱ Time remaining: <span id="__quiz-timer-display">{"--:--" if not time_limit_minutes else f"{time_limit_minutes}:00"}</span>
</div>

<!-- Face authentication overlay -->
<div id="__face-auth-overlay" style="position:fixed;inset:0;z-index:10000;background:rgba(10,12,20,0.96);display:flex;align-items:center;justify-content:center;">
  <div id="__fa-card" style="background:#1a1f2e;border-radius:16px;padding:36px 32px;width:340px;text-align:center;box-shadow:0 24px 60px rgba(0,0,0,0.6);border:1px solid #2d3748;">
    <div id="__fa-step" style="font-size:11px;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:14px;font-family:sans-serif;">Checking...</div>
    <h2 id="__fa-title" style="color:#f9fafb;font-size:20px;margin:0 0 8px;font-family:sans-serif;font-weight:700;">🔐 Identity Check</h2>
    <p id="__fa-subtitle" style="color:#9ca3af;font-size:13px;margin:0 0 22px;font-family:sans-serif;line-height:1.5;">Starting camera...</p>
    <div style="position:relative;width:200px;height:200px;margin:0 auto 18px;">
      <video id="__fa-video" style="width:200px;height:200px;border-radius:50%;object-fit:cover;transform:scaleX(-1);background:#000;" autoplay muted playsinline></video>
      <svg style="position:absolute;top:0;left:0;width:200px;height:200px;pointer-events:none;" viewBox="0 0 200 200">
        <ellipse cx="100" cy="100" rx="90" ry="97" fill="none" stroke-width="3" stroke-dasharray="6 3" id="__fa-oval-ring" stroke="#f59e0b"/>
      </svg>
    </div>
    <div id="__fa-status" style="font-size:13px;color:#9ca3af;font-family:sans-serif;margin-bottom:18px;min-height:18px;"></div>
    <button id="__fa-btn" style="display:none;background:linear-gradient(135deg,#4f8ef7,#3b7de8);color:#fff;border:none;border-radius:8px;padding:13px 0;font-size:15px;cursor:pointer;font-family:sans-serif;font-weight:600;width:100%;box-shadow:0 4px 12px rgba(79,142,247,0.4);transition:opacity 0.15s;" onclick="window.__faceAuthAction && window.__faceAuthAction()">Enroll Face</button>
    <div style="margin-top:14px;font-size:11px;color:#4b5563;font-family:sans-serif;">Having trouble? Contact your instructor</div>
  </div>
</div>

<div id="quiz-start-screen" style="display:none;text-align:center;padding:40px 20px;">
  <h2 style="color:#2c3e50;margin-bottom:16px;">Quiz: {esc(week_id)}</h2>
  <p style="font-size:1.1em;color:#555;margin-bottom:8px;">This quiz contains <strong>{question_count}</strong> question{"s" if question_count != 1 else ""}{timer_label}.</p>
  <p style="font-size:0.95em;color:#777;margin-bottom:24px;">You can check and submit your answers when ready.</p>
  <button onclick="{start_onclick}" style="background:#4CAF50;color:white;padding:14px 36px;border:none;border-radius:6px;cursor:pointer;font-size:1.1em;">Start Quiz</button>
</div>
<div id="quiz-questions" style="display:none;">
{body}
<div style="text-align:center;margin-top:32px;padding:16px 0;border-top:1px solid #e5e7eb;">
  <button id="__quiz-done-btn" onclick="if(window.__triggerQuizDone)window.__triggerQuizDone()" style="background:#4CAF50;color:white;padding:12px 32px;border:none;border-radius:6px;cursor:pointer;font-size:1em;">✓ Mark as Done</button>
  <p id="__quiz-done-msg" style="display:none;color:#22c55e;margin-top:8px;font-size:0.95em;">Quiz submitted! Your instructor has been notified.</p>
</div>
</div>'''
    else:
        body = '<p style="text-align:center;padding:40px;color:#888;">No questions available yet. Ask your instructor to add some!</p>'

    # Hint JS: fetches from FastAPI using csq_name and course/week context
    hint_script = f'''
<script>
(function() {{
    const API = (function() {{
        const base = window.__CU_API_BASE || '{SERVER_BASE_URL}';
        try {{
            const u = new URL(base);
            const h = window.location.hostname;
            if (h && h !== 'localhost' && h !== '127.0.0.1' &&
                (u.hostname === 'localhost' || u.hostname === '127.0.0.1')) {{
                return window.location.protocol + '//' + h + ':' + u.port;
            }}
        }} catch(e) {{}}
        return base;
    }})();
    const course = window.__course || '{esc(course_id)}';
    const week = window.__week || '{esc(week_id)}';
    const hintCache = {{}};
    const hintLevel = {{}};

    async function fetchHints(qname) {{
        if (hintCache[qname] !== undefined) return hintCache[qname];
        try {{
            const r = await fetch(API + '/admin/hints/' + course + '/' + week + '/' + qname);
            if (!r.ok) throw new Error();
            const d = await r.json();
            hintCache[qname] = d.hints || [];
        }} catch {{
            hintCache[qname] = [];
        }}
        return hintCache[qname];
    }}

    function addHintButton(qname, container) {{
        const btn = document.createElement('button');
        btn.textContent = '💡 Hint';
        btn.style.cssText = 'background:#f59e0b;color:white;padding:6px 12px;border:none;border-radius:4px;cursor:pointer;font-size:12px;margin-top:8px;';

        const hintBox = document.createElement('div');
        hintBox.style.cssText = 'display:none;margin-top:6px;padding:10px;border-radius:4px;background:#fffbeb;border:1px solid #fde68a;';

        btn.onclick = async function() {{
            const hints = await fetchHints(qname);
            if (!hints.length) {{
                hintBox.style.display = 'block';
                hintBox.innerHTML = '<div style="font-size:13px;color:#92400e;">No hints available.</div>';
                btn.disabled = true; btn.textContent = 'No hints';
                return;
            }}
            if (!hintLevel[qname]) hintLevel[qname] = 0;
            if (hintLevel[qname] >= hints.length) return;
            hintLevel[qname]++;
            hintBox.style.display = 'block';
            const div = document.createElement('div');
            div.style.cssText = 'margin-bottom:6px;font-size:13px;color:#92400e;';
            div.innerHTML = '<b>Hint ' + hintLevel[qname] + ' of ' + hints.length + ':</b> ' + hints[hintLevel[qname]-1].text;
            hintBox.appendChild(div);
            if (hintLevel[qname] >= hints.length) {{
                btn.disabled = true; btn.textContent = 'No more hints';
            }} else {{
                btn.textContent = 'Next Hint (' + hintLevel[qname] + '/' + hints.length + ')';
            }}
        }};
        container.appendChild(btn);
        container.appendChild(hintBox);
    }}

    function initHints() {{
        const qnames = window.__quizQuestionNames || [];
        qnames.forEach(function(qname) {{
            const div = document.getElementById('cs_qdiv_' + qname);
            if (div) {{
                const container = document.createElement('div');
                container.className = 'hint-btn-container';
                container.style.cssText = 'margin-top:8px;';
                div.appendChild(container);
                addHintButton(qname, container);
            }}
        }});
    }}

    function initWS() {{
        if (window.__liveWS) return;
        const room = (window.__course || 'unknown') + '/' + (window.__week || 'unknown');
        const username = window.__cs_username || 'anon';
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = API.replace(/^https?:[/][/]/, '');
        try {{
            const ws = new WebSocket(proto + '//' + wsHost + '/ws?token=' + encodeURIComponent(window.__CU_TOKEN || ''));
            ws.onopen = () => {{ ws.send(JSON.stringify({{ type: 'JOIN', username, room }})); window.__liveWS = ws; }};
            ws.onmessage = e => {{
                try {{
                    const msg = JSON.parse(e.data);
                    if (msg.type === 'PUSH_HINT' && msg.target_username === username) {{
                        const el = document.createElement('div');
                        el.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:14px;font-size:14px;color:#92400e;z-index:9999;max-width:320px;box-shadow:0 4px 12px rgba(0,0,0,0.15);';
                        el.innerHTML = '<b>💡 Instructor Hint:</b><br>' + msg.hint_text + '<br><button onclick="this.parentElement.remove()" style="margin-top:6px;padding:2px 10px;">Dismiss</button>';
                        document.body.appendChild(el);
                    }}
                }} catch {{}}
            }};
            ws.onclose = () => {{ window.__liveWS = null; }};
        }} catch {{}}
    }}

    function showBadgeToast(badges) {{
        badges.forEach(function(b, i) {{
            setTimeout(function() {{
                const toast = document.createElement('div');
                toast.style.cssText = 'position:fixed;bottom:' + (20 + i * 80) + 'px;left:50%;transform:translateX(-50%);background:#1f2937;color:#fff;padding:12px 24px;border-radius:10px;font-size:15px;z-index:9999;box-shadow:0 4px 16px rgba(0,0,0,0.35);text-align:center;min-width:200px;';
                toast.innerHTML = '<div style="font-size:28px;margin-bottom:4px;">' + b.icon + '</div><div style="font-weight:600;">Badge Unlocked!</div><div style="font-size:13px;opacity:0.8;margin-top:2px;">' + b.label + '</div>';
                document.body.appendChild(toast);
                setTimeout(function() {{ toast.remove(); }}, 5000);
            }}, i * 600);
        }});
    }}

    function initXPWidget() {{
        const badge = document.createElement('div');
        badge.id = '__xp-badge';
        badge.title = 'Click to see your stats';
        badge.style.cssText = 'position:fixed;top:8px;right:12px;z-index:999;background:linear-gradient(135deg,#1f2937,#111827);color:#fff;padding:5px 16px;border-radius:20px;font-size:13px;font-family:sans-serif;display:flex;gap:10px;align-items:center;user-select:none;box-shadow:0 2px 10px rgba(0,0,0,0.45);border:1px solid #374151;';
        badge.innerHTML = '<span>⭐ <span id="__xp-val" style="font-weight:700;">0</span> XP</span><span>🔥 <span id="__streak-val" style="font-weight:700;">0</span></span>';
        const panel = document.createElement('div');
        panel.id = '__xp-panel';
        panel.innerHTML = '<div style="font-weight:700;margin-bottom:8px;color:#f9fafb;">Your Stats</div><div id="__xp-detail">Loading...</div><div id="__xp-badges-row" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;"></div>';
        document.body.appendChild(badge);
        document.body.appendChild(panel);
        badge.addEventListener('click', function() {{
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }});
        document.addEventListener('click', function(e) {{
            if (!badge.contains(e.target) && !panel.contains(e.target)) panel.style.display = 'none';
        }});
        const u = window.__cs_username || '';
        const c = window.__course || '';
        if (u && c) {{
            fetch(API + '/' + c + '/my-stats?username=' + encodeURIComponent(u))
                .then(function(r) {{ return r.json(); }})
                .then(function(data) {{
                    const xEl = document.getElementById('__xp-val');
                    const sEl = document.getElementById('__streak-val');
                    const det = document.getElementById('__xp-detail');
                    const br  = document.getElementById('__xp-badges-row');
                    if (xEl) xEl.textContent = data.xp != null ? data.xp : 0;
                    if (sEl) sEl.textContent = data.streak != null ? data.streak : 0;
                    if (det) det.innerHTML = 'Rank <b>#' + (data.rank || '—') + '</b> &nbsp;·&nbsp; <b>' + (data.xp || 0) + ' XP</b> &nbsp;·&nbsp; 🔥 <b>' + (data.streak || 0) + ' days</b>';
                    if (br && data.badges && data.badges.length) {{
                        br.innerHTML = data.badges.map(function(b) {{
                            return '<span style="padding:2px 10px;border-radius:12px;background:#2d3748;font-size:11px;">' + b.icon + ' ' + b.label + '</span>';
                        }}).join('');
                    }}
                }}).catch(function(err) {{ console.error('[xp-widget] my-stats failed:', err); }});
        }}
    }}

    function updateXPWidget(xp, streak) {{
        const xEl = document.getElementById('__xp-val');
        const sEl = document.getElementById('__streak-val');
        if (xEl) {{
            xEl.textContent = xp;
            xEl.style.transition = 'transform 0.25s';
            xEl.style.transform = 'scale(1.35)';
            setTimeout(function() {{ xEl.style.transform = 'scale(1)'; }}, 260);
        }}
        if (sEl) sEl.textContent = streak;
    }}

    async function initFaceAuth() {{
        const overlay = document.getElementById('__face-auth-overlay');
        if (!overlay) return;
        const PASS = function() {{
            if (stream) {{ stream.getTracks().forEach(function(t) {{ t.stop(); }}); stream = null; }}
            overlay.style.transition = 'opacity 0.6s';
            overlay.style.opacity = '0';
            setTimeout(function() {{
                overlay.remove();
                // If a timed quiz was already started, resume it instead of showing start screen
                if (window.__checkResumeTimer && window.__checkResumeTimer()) return;
                const qs = document.getElementById('quiz-start-screen');
                if (qs) qs.style.display = 'block';
            }}, 650);
        }};
        const username = window.__cs_username || '';
        if (!username) {{ PASS(); return; }}

        const titleEl    = document.getElementById('__fa-title');
        const subtitleEl = document.getElementById('__fa-subtitle');
        const stepEl     = document.getElementById('__fa-step');
        const statusEl   = document.getElementById('__fa-status');
        const btnEl      = document.getElementById('__fa-btn');
        const videoEl    = document.getElementById('__fa-video');
        const ring       = document.getElementById('__fa-oval-ring');
        const card       = document.getElementById('__fa-card');

        function setStatus(t, col) {{ if (statusEl) {{ statusEl.innerHTML = t; statusEl.style.color = col || '#9ca3af'; }} }}
        function setRing(col, dash) {{ if (ring) {{ ring.setAttribute('stroke', col); ring.setAttribute('stroke-dasharray', dash ? '6 3' : 'none'); }} }}

        if (subtitleEl) subtitleEl.textContent = 'Checking identity...';

        let enrolled = false;
        try {{
            const ctrl = new AbortController();
            const tid = setTimeout(function() {{ ctrl.abort(); }}, 8000);
            const r = await fetch(API + '/' + course + '/face-status?username=' + encodeURIComponent(username), {{signal: ctrl.signal}});
            clearTimeout(tid);
            enrolled = (await r.json()).enrolled;
        }} catch(e) {{
            console.error('[face-auth] face-status check failed:', e);
            if (subtitleEl) subtitleEl.textContent = 'Verification server unreachable. Contact your instructor.';
            setStatus('⚠️ Cannot reach verification server', '#ef4444');
            return;
        }}

        let stream = null;
        try {{
            stream = await navigator.mediaDevices.getUserMedia({{video: {{facingMode:'user'}}, audio:false}});
            videoEl.srcObject = stream;
        }} catch(e) {{
            console.error('[face-auth] camera access failed:', e);
            if (subtitleEl) subtitleEl.textContent = 'Camera access denied. Enable camera and refresh.';
            setStatus('⚠️ Camera required for identity check', '#ef4444');
            return;
        }}

        const MODEL_URL = API + '/static/models/';
        const MAX_RETRIES = 4;
        let modelsLoaded = false;
        for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {{
            try {{
                if (subtitleEl) subtitleEl.textContent = attempt === 1
                    ? 'Loading face models... (first visit only)'
                    : 'Retrying model load (attempt ' + attempt + '/' + MAX_RETRIES + ')...';
                setStatus('📡 Connecting to face recognition service...', '#9ca3af');
                await Promise.all([
                    faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                    faceapi.nets.faceLandmark68TinyNet.loadFromUri(MODEL_URL),
                    faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
                    faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL)
                ]);
                modelsLoaded = true;
                break;
            }} catch(e) {{
                console.error('[face-auth] model load attempt ' + attempt + ' failed:', e);
                if (attempt < MAX_RETRIES) {{
                    const wait = attempt * 3;
                    if (subtitleEl) subtitleEl.textContent = '⚠️ Your network seems unstable, retrying in ' + wait + 's...';
                    setStatus('⚠️ Network unstable, retrying...', '#f59e0b');
                    await new Promise(function(res) {{ setTimeout(res, wait * 1000); }});
                }}
            }}
        }}
        if (!modelsLoaded) {{
            console.error('[face-auth] all model load attempts failed');
            if (subtitleEl) subtitleEl.textContent = 'Could not load face models after ' + MAX_RETRIES + ' attempts. Your network may be unstable.';
            setStatus('⚠️ Face recognition unavailable, quiz unlocked without verification', '#f59e0b');
            if (btnEl) {{ btnEl.textContent = 'Skip (not recommended)'; btnEl.style.display = 'block'; btnEl.onclick = function() {{ PASS(); }}; }}
            return;
        }}

        if (stepEl) stepEl.textContent = enrolled ? 'Step 2 of 2' : 'Step 1 of 2 == First-time setup';
        if (titleEl) titleEl.textContent = enrolled ? '🔐 Verify Your Identity' : '📸 Set Up Face ID';
        if (subtitleEl) subtitleEl.textContent = enrolled
            ? 'Look at the camera to confirm it is you.'
            : 'Center your face in the circle. We will remember you for future quizzes.';
        if (btnEl) btnEl.textContent = enrolled ? 'Verify Identity' : 'Enroll My Face';

        let currentDescriptor = null;

        var loop = setInterval(async function() {{
            try {{
                const det = await faceapi
                    .detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions())
                    .withFaceLandmarks(true)
                    .withFaceDescriptor();
                if (det) {{
                    currentDescriptor = Array.from(det.descriptor);
                    setRing('#22c55e', false);
                    setStatus('✅ Face detected, click below to continue', '#22c55e');
                    if (btnEl) btnEl.style.display = 'block';
                }} else {{
                    currentDescriptor = null;
                    setRing('#f59e0b', true);
                    setStatus('Position your face in the circle', '#9ca3af');
                    if (btnEl) btnEl.style.display = 'none';
                }}
            }} catch(e) {{}}
        }}, 800);

        const stopAll = function() {{ clearInterval(loop); if (stream) stream.getTracks().forEach(function(t) {{ t.stop(); }}); }};

        async function captureMultiSample(n, intervalMs) {{
            const samples = [];
            for (let i = 0; i < n; i++) {{
                setStatus('Hold still… ' + (n - i) + ' frame' + (n - i === 1 ? '' : 's') + ' left', '#9ca3af');
                await new Promise(function(r) {{ setTimeout(r, intervalMs); }});
                try {{
                    const det = await faceapi
                        .detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions())
                        .withFaceLandmarks(true)
                        .withFaceDescriptor();
                    if (det) samples.push(Array.from(det.descriptor));
                }} catch(e) {{}}
            }}
            if (samples.length === 0) return null;
            const avg = new Array(128).fill(0);
            for (const s of samples) {{ for (let j = 0; j < 128; j++) avg[j] += s[j]; }}
            return avg.map(function(v) {{ return v / samples.length; }});
        }}

        window.__faceAuthAction = async function() {{
            if (!currentDescriptor) return;
            if (btnEl) {{ btnEl.disabled = true; btnEl.textContent = enrolled ? 'Verifying...' : 'Capturing...'; }}
            try {{
                let descriptor;
                if (!enrolled) {{
                    descriptor = await captureMultiSample(5, 600);
                    if (!descriptor) {{
                        setStatus('Could not capture face clearly. Try again.', '#ef4444');
                        if (btnEl) {{ btnEl.disabled = false; btnEl.textContent = 'Enroll My Face'; }}
                        return;
                    }}
                }} else {{
                    descriptor = currentDescriptor;
                }}
                const endpoint = enrolled ? '/verify-face' : '/enroll-face';
                const r = await fetch(API + '/' + course + endpoint, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{username: username, descriptor: descriptor}})
                }});
                if (r.status === 409) {{
                    setStatus('⚠️ Already enrolled. Contact your instructor to reset.', '#f59e0b');
                    if (btnEl) {{ btnEl.disabled = false; btnEl.textContent = 'Enroll My Face'; }}
                    return;
                }}
                const d = await r.json();
                if (!enrolled || d.verified) {{
                    setStatus('✅ ' + (enrolled ? 'Identity confirmed!' : 'Enrolled! Welcome.'), '#22c55e');
                    setRing('#22c55e', false);
                    stopAll();
                    setTimeout(PASS, 1100);
                }} else {{
                    if (btnEl) {{ btnEl.disabled = false; btnEl.textContent = 'Try Again'; }}
                    setStatus('❌ Face not recognised. Try adjusting your position.', '#ef4444');
                    setRing('#ef4444', false);
                    if (card) {{ card.style.animation = '__fa-shake 0.4s ease'; setTimeout(function() {{ card.style.animation = ''; }}, 450); }}
                }}
            }} catch(e) {{
                if (btnEl) {{ btnEl.disabled = false; btnEl.textContent = enrolled ? 'Try Again' : 'Enroll My Face'; }}
            }}
        }};

        // Clean up if overlay is removed externally
        const obs = new MutationObserver(function() {{
            if (!document.getElementById('__face-auth-overlay')) {{ stopAll(); obs.disconnect(); }}
        }});
        obs.observe(document.body, {{childList: true}});
    }}

    if (document.readyState !== 'complete') {{
        document.addEventListener('DOMContentLoaded', function() {{ initHints(); initWS(); initXPWidget(); initFaceAuth(); }});
    }} else {{
        initHints(); initWS(); initXPWidget(); initFaceAuth();
    }}

    window.__triggerQuizDone = async function() {{
        const btn = document.getElementById('__quiz-done-btn');
        const msg = document.getElementById('__quiz-done-msg');
        if (btn) {{ btn.disabled = true; btn.style.background = '#9ca3af'; }}
        if (msg) msg.style.display = 'block';
        if (window.__liveWS && window.__liveWS.readyState === WebSocket.OPEN) {{
            window.__liveWS.send(JSON.stringify({{
                type: 'QUIZ_DONE',
                username: window.__cs_username || 'unknown',
                course: window.__course,
                week: window.__week,
                timestamp: new Date().toISOString()
            }}));
        }}
        const u = window.__cs_username || '';
        if (!u) return;
        if (window.__quizTimerKey) localStorage.removeItem(window.__quizTimerKey);
        try {{
            const r = await fetch(API + '/' + course + '/' + week + '/quiz-complete', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{username: u}})
            }});
            const data = await r.json();
            console.log('[quiz-complete]', data);
            if (data.status === 'already_processed') return;
            if (data.new_total_xp != null) updateXPWidget(data.new_total_xp, data.streak || 0);
            if (data.badges_earned && data.badges_earned.length > 0) {{
                showBadgeToast(data.badges_earned);
            }}
        }} catch(e) {{ console.error('[quiz-complete] error:', e); }}
    }};
}})();
</script>
'''

    timer_script = ""
    if time_limit_minutes:
        timer_script = f'''
<script>
(function() {{
    const QUIZ_DURATION_S = {time_limit_minutes} * 60;
    const TIMER_KEY = '__qt_{esc(course_id)}_{esc(week_id)}';
    let quizSecondsLeft = QUIZ_DURATION_S;
    let quizTimerInterval = null;

    function startQuizTimer(secondsOverride) {{
        if (quizTimerInterval) clearInterval(quizTimerInterval);
        quizSecondsLeft = (secondsOverride !== undefined) ? secondsOverride : QUIZ_DURATION_S;
        const bar = document.getElementById('__quiz-timer-bar');
        if (bar) bar.style.display = 'block';
        quizTimerInterval = setInterval(function() {{
            quizSecondsLeft--;
            const m = Math.floor(quizSecondsLeft / 60);
            const s = quizSecondsLeft % 60;
            const display = document.getElementById('__quiz-timer-display');
            if (display) {{
                display.textContent = m + ':' + String(s).padStart(2, '0');
                if (quizSecondsLeft <= 300) display.style.color = '#ef4444';
            }}
            if (quizSecondsLeft <= 0) {{
                clearInterval(quizTimerInterval);
                if (display) display.textContent = '0:00';
                document.querySelectorAll('#quiz-questions input, #quiz-questions textarea, #quiz-questions select').forEach(function(el) {{ el.disabled = true; }});
                const msg = document.createElement('div');
                msg.style.cssText = 'text-align:center;padding:16px;font-size:1.1em;';
                msg.innerHTML = '<b style="color:#ef4444;">⏰ Time is up!</b>';
                const qDiv = document.getElementById('quiz-questions');
                if (qDiv) qDiv.prepend(msg);
                if (window.__triggerQuizDone) window.__triggerQuizDone();
            }}
        }}, 1000);
    }}

    // Called from PASS() — if the student already started the quiz in a prior
    // page load, resume the timer from the correct remaining seconds.
    window.__checkResumeTimer = function() {{
        const stored = localStorage.getItem(TIMER_KEY);
        if (!stored) return false;
        const elapsed = Math.floor((Date.now() - parseInt(stored)) / 1000);
        const remaining = QUIZ_DURATION_S - elapsed;
        const startScreen = document.getElementById('quiz-start-screen');
        const questionsDiv = document.getElementById('quiz-questions');
        if (remaining <= 0) {{
            if (startScreen) startScreen.style.display = 'none';
            if (questionsDiv) questionsDiv.style.display = 'block';
            document.querySelectorAll('#quiz-questions input, #quiz-questions textarea, #quiz-questions select').forEach(function(el) {{ el.disabled = true; }});
            const bar = document.getElementById('__quiz-timer-bar');
            if (bar) {{ bar.style.display = 'block'; bar.style.background = '#dc2626'; }}
            const disp = document.getElementById('__quiz-timer-display');
            if (disp) disp.textContent = '0:00';
            if (window.__triggerQuizDone) window.__triggerQuizDone();
        }} else {{
            if (startScreen) startScreen.style.display = 'none';
            if (questionsDiv) questionsDiv.style.display = 'block';
            startQuizTimer(remaining);
        }}
        return true;
    }};

    window.__startQuizTimer = startQuizTimer;
    window.__quizTimerKey = TIMER_KEY;
}})();
</script>
'''

    affect_script = generate_affect_script(SERVER_BASE_URL)
    return header + body + hint_script + timer_script + affect_script
