def generate_affect_script(server_base_url: str = "") -> str:
    return f'''
<div id="__affect-widget" style="position:fixed;bottom:12px;right:12px;z-index:9999;background:#111;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.5);font-family:sans-serif;width:240px;">
  <div id="__affect-header" style="display:flex;align-items:center;justify-content:space-between;padding:5px 8px;background:#1f2937;">
    <span id="__affect-status-text" style="font-size:11px;color:#9ca3af;">📷 Loading…</span>
    <button id="__affect-toggle" onclick="(function(){{var b=document.getElementById('__affect-body'),t=document.getElementById('__affect-toggle'),h=b.style.display==='none';b.style.display=h?'block':'none';t.textContent=h?'▾':'▸';}})()" style="background:none;border:none;color:#9ca3af;font-size:11px;cursor:pointer;padding:0 2px;line-height:1;">▾</button>
  </div>
  <div id="__affect-body">
    <div style="position:relative;width:240px;height:180px;background:#000;">
      <video id="__affect-video" width="240" height="180" muted playsinline style="display:block;transform:scaleX(-1);"></video>
      <canvas id="__affect-canvas" width="240" height="180" style="position:absolute;top:0;left:0;pointer-events:none;"></canvas>
    </div>
    <div id="__affect-label" style="text-align:center;font-size:11px;padding:4px;color:#fff;background:#374151;">Initializing…</div>
    <div id="__affect-expression-bar" style="display:flex;gap:2px;padding:3px 4px;background:#111;flex-wrap:wrap;"></div>
  </div>
</div>
<script>
(function() {{
if (window.__affectInjected) return;
window.__affectInjected = true;

const API = (function() {{
    const base = window.__CU_API_BASE || '{server_base_url}';
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
const attemptSessionId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + '-' + Math.random().toString(36).slice(2);
let videoStream = null, videoEl = null, canvasEl = null, canvasCtx = null;
let lastInteractionTime = Date.now(), lastEngagementSent = 0, lastAffectState = null;
let pageClicks = 0, keypressCount = 0;

document.addEventListener('click', () => {{ pageClicks++; lastInteractionTime = Date.now(); }});
document.addEventListener('keydown', () => {{ keypressCount++; lastInteractionTime = Date.now(); }});

const pathParts = window.location.pathname.split('/').filter(Boolean);
let course = '', week = '';
if (pathParts.length >= 2 && pathParts[0] !== 'courses') {{ course = pathParts[0]; week = pathParts[1]; }}
else if (pathParts.length >= 3 && pathParts[0] === 'courses') {{ course = pathParts[1]; week = pathParts[2]; }}
if (!course) course = 'unknown';
if (!week) week = 'unknown';

function __setStatus(text, color) {{
  const el = document.getElementById('__affect-status-text');
  if (el) {{ el.textContent = text; el.style.color = color || '#9ca3af'; }}
}}

function __setLabel(text, bgColor) {{
  const el = document.getElementById('__affect-label');
  if (el) {{ el.textContent = text; el.style.background = bgColor || '#374151'; }}
}}

function __setExprBar(expressions) {{
  const bar = document.getElementById('__affect-expression-bar');
  if (!bar || !expressions) {{ if (bar) bar.innerHTML = ''; return; }}
  const top = Object.entries(expressions)
    .filter(([,v]) => v > 0.1)
    .sort(([,a],[,b]) => b - a)
    .slice(0, 4);
  const emojis = {{ happy:'😊', sad:'😞', angry:'😠', fearful:'😨', disgusted:'🤢', surprised:'😲', neutral:'😐' }};
  bar.innerHTML = top.map(([k, v]) =>
    `<span style="font-size:10px;color:#9ca3af;">${{emojis[k] || k[0]}}${{Math.round(v*100)}}%</span>`
  ).join('');
}}

function affectColor(state) {{
  if (state === 'focused')    return '#22c55e';
  if (state === 'confused')   return '#eab308';
  if (state === 'struggling') return '#f97316';
  if (state === 'disengaged') return '#f59e0b';
  if (state === 'distracted') return '#ef4444';
  return '#6b7280';
}}

const AFFECT_LABELS = {{
  focused:    '✓ Focused',
  confused:   '? Confused',
  struggling: '! Struggling',
  disengaged: '⚠ Disengaged',
  distracted: '✕ Distracted',
}};

// Detect face with landmarks + expressions when available.
async function detectFaceRich() {{
  if (!window.faceapi || !videoEl || !videoStream) return null;
  try {{
    if (!faceapi.nets.tinyFaceDetector.isLoaded) return null;
    const hasLandmarks = faceapi.nets.faceLandmark68TinyNet.isLoaded;
    const hasExpressions = faceapi.nets.faceExpressionNet.isLoaded;
    const opts = new faceapi.TinyFaceDetectorOptions({{ inputSize: 224, scoreThreshold: 0.2 }});
    if (hasLandmarks && hasExpressions) {{
      return await faceapi.detectSingleFace(videoEl, opts).withFaceLandmarks(true).withFaceExpressions() || null;
    }} else if (hasLandmarks) {{
      return await faceapi.detectSingleFace(videoEl, opts).withFaceLandmarks(true) || null;
    }} else {{
      const d = await faceapi.detectSingleFace(videoEl, opts) || null;
      return d ? {{ detection: d, landmarks: null, expressions: null }} : null;
    }}
  }} catch(e) {{ return null; }}
}}

function dist2d(a, b) {{ return Math.hypot(a.x - b.x, a.y - b.y); }}

// Eye Aspect Ratio from 6 eye landmark points
function calcEAR(eyePts) {{
  if (!eyePts || eyePts.length < 6) return null;
  const v1 = dist2d(eyePts[1], eyePts[5]);
  const v2 = dist2d(eyePts[2], eyePts[4]);
  const h  = dist2d(eyePts[0], eyePts[3]);
  return h > 0 ? (v1 + v2) / (2 * h) : null;
}}

// Mouth open ratio: inner lip vertical span / face height
function calcMouthOpen(mouthPts, faceHeight) {{
  if (!mouthPts || mouthPts.length < 20 || !faceHeight) return null;
  const inner = mouthPts.slice(12);
  const topY = Math.min(...inner.map(p => p.y));
  const botY = Math.max(...inner.map(p => p.y));
  return (botY - topY) / faceHeight;
}}

// Head roll in degrees from eye centre line
function calcHeadRoll(landmarks) {{
  const le = landmarks.getLeftEye();
  const re = landmarks.getRightEye();
  const lcx = le.reduce((s,p)=>s+p.x,0)/le.length;
  const lcy = le.reduce((s,p)=>s+p.y,0)/le.length;
  const rcx = re.reduce((s,p)=>s+p.x,0)/re.length;
  const rcy = re.reduce((s,p)=>s+p.y,0)/re.length;
  return Math.atan2(rcy - lcy, rcx - lcx) * 180 / Math.PI;
}}

function estimateHeadPoseFromBox(box) {{
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  const vw = (videoEl && videoEl.videoWidth) || 240;
  const vh = (videoEl && videoEl.videoHeight) || 180;
  const normX = (cx / vw) - 0.5;
  const normY = (cy / vh) - 0.5;
  if (Math.abs(normX) < 0.2 && Math.abs(normY) < 0.2) return {{ pose: 'center', yaw: normX * 90, pitch: normY * 45 }};
  if (Math.abs(normX) > Math.abs(normY)) return {{ pose: normX < 0 ? 'right' : 'left', yaw: normX * 90, pitch: normY * 45 }};
  return {{ pose: 'down', yaw: normX * 90, pitch: normY * 45 }};
}}

function computeEngagement(present, gaze, headPose, inactivity) {{
  let score = 100;
  if (!present) score -= 45;
  if (!gaze) score -= 20;
  if (headPose === 'down') score -= 15;
  else if (headPose === 'left' || headPose === 'right') score -= 10;
  if (inactivity > 120) score -= 30; else if (inactivity > 60) score -= 15;
  return Math.max(0, Math.min(100, score));
}}

function computeAffect(score, inactivity, facePresent, expressions, rollDeg) {{
  if (!facePresent || inactivity > 90) return 'distracted';
  if (expressions) {{
    const angry = expressions.angry || 0;
    const fearful = expressions.fearful || 0;
    const surprised = expressions.surprised || 0;
    if (angry > 0.25 || fearful > 0.25) return 'struggling';
    if (surprised > 0.3 || Math.abs(rollDeg || 0) > 20) return 'confused';
  }}
  if (inactivity > 60 || score < 30) return 'disengaged';
  return 'focused';
}}

async function ensureStream() {{
  if (videoStream) return true;
  try {{
    videoStream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
    videoEl = document.getElementById('__affect-video');
    canvasEl = document.getElementById('__affect-canvas');
    if (canvasEl) canvasCtx = canvasEl.getContext('2d');
    videoEl.srcObject = videoStream;
    await videoEl.play();
    renderLoop();
    return true;
  }} catch {{
    __setStatus('📷 Cam off', '#6b7280');
    __setLabel('Camera unavailable', '#374151');
    return false;
  }}
}}

async function renderLoop() {{
  if (!videoEl || !videoStream) {{ setTimeout(renderLoop, 2000); return; }}
  const result = await detectFaceRich();
  if (canvasCtx && canvasEl) {{
    const cw = canvasEl.width, ch = canvasEl.height;
    canvasCtx.clearRect(0, 0, cw, ch);
    if (result) {{
      const box = result.detection ? result.detection.box : result.box;
      const inact = Math.floor((Date.now() - lastInteractionTime) / 1000);
      const hp = estimateHeadPoseFromBox(box);
      const score = computeEngagement(true, hp.pose === 'center', hp.pose, inact);
      let roll = null;
      if (result.landmarks) {{ try {{ roll = calcHeadRoll(result.landmarks); }} catch(e) {{}} }}
      const state = computeAffect(score, inact, true, result.expressions, roll);
      const color = affectColor(state);
      const mx = cw - box.x - box.width;
      canvasCtx.strokeStyle = color; canvasCtx.lineWidth = 2;
      canvasCtx.strokeRect(mx, box.y, box.width, box.height);
      canvasCtx.fillStyle = color + '22';
      canvasCtx.fillRect(mx, box.y, box.width, box.height);
      __setLabel(AFFECT_LABELS[state] || state, color);
      __setStatus('📷 Monitoring', '#22c55e');
      __setExprBar(result.expressions || null);
    }} else {{
      canvasCtx.strokeStyle = '#6b7280'; canvasCtx.lineWidth = 1;
      canvasCtx.setLineDash([4, 4]);
      canvasCtx.strokeRect(4, 4, cw - 8, ch - 8);
      canvasCtx.setLineDash([]);
      canvasCtx.fillStyle = 'rgba(107,114,128,0.7)';
      canvasCtx.font = '11px sans-serif'; canvasCtx.textAlign = 'center';
      canvasCtx.fillText('No face detected', cw / 2, ch / 2);
      __setLabel('No face detected', '#374151');
      __setStatus('📷 Monitoring', '#9ca3af');
      __setExprBar(null);
    }}
  }}
  setTimeout(renderLoop, 2000);
}}

async function collectSample() {{
  if (!window.faceapi || !faceapi.nets.tinyFaceDetector.isLoaded) return;
  const now = Date.now();
  const isFirst = lastEngagementSent === 0;
  if (!isFirst && now - lastEngagementSent < 20000) return;
  lastEngagementSent = now;
  const inactivity = Math.floor((now - lastInteractionTime) / 1000);
  let facePresent = false, gazeCentered = false, headPose = 'center';
  let yaw = null, pitch = null, roll = null;
  let ear = null, mouthOpen = null, smileScore = null;
  let expressions = null;

  if (await ensureStream()) {{
    const result = await detectFaceRich();
    if (result) {{
      facePresent = true;
      const box = result.detection ? result.detection.box : result.box;
      const hp = estimateHeadPoseFromBox(box);
      headPose = hp.pose; yaw = hp.yaw; pitch = hp.pitch;
      gazeCentered = headPose === 'center';

      if (result.landmarks) {{
        try {{
          roll = calcHeadRoll(result.landmarks);
          const lEye = result.landmarks.getLeftEye();
          const rEye = result.landmarks.getRightEye();
          const earL = calcEAR(lEye);
          const earR = calcEAR(rEye);
          if (earL !== null && earR !== null) ear = (earL + earR) / 2;
          const mouth = result.landmarks.getMouth();
          const faceH = box.height;
          mouthOpen = calcMouthOpen(mouth, faceH);
        }} catch(e) {{}}
      }}

      if (result.expressions) {{
        expressions = result.expressions;
        smileScore = expressions.happy || null;
      }}
    }}
  }}

  const score = computeEngagement(facePresent, gazeCentered, headPose, inactivity);
  const affectState = computeAffect(score, inactivity, facePresent, expressions, roll);

  if (affectState !== lastAffectState && window.__liveWS && window.__liveWS.readyState === WebSocket.OPEN) {{
    window.__liveWS.send(JSON.stringify({{
      type: 'AFFECT_CHANGE', username: window.__cs_username || 'unknown',
      affect_state: affectState,
      expressions: expressions ? Object.fromEntries(Object.entries(expressions).map(([k,v])=>[k,Math.round(v*100)/100])) : null
    }}));
  }}
  lastAffectState = affectState;

  const simplifyEl = document.getElementById('adaptiveSimplify');
  const advancedEl = document.getElementById('adaptiveAdvanced');
  const promptEl = document.getElementById('attentionPrompt');
  if (simplifyEl) simplifyEl.style.display = score < 40 ? 'block' : 'none';
  if (advancedEl) advancedEl.style.display = score > 80 ? 'block' : 'none';
  if (promptEl) promptEl.style.display = inactivity > 120 ? 'block' : 'none';

  fetch(API + '/' + course + '/' + week + '/engagement', {{
    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{
      attemptSessionId, username: window.__cs_username || 'unknown',
      course, week, timestamp: new Date().toISOString(),
      facePresent, gazeCentered, headPose,
      inactivitySeconds: inactivity, engagementScore: score,
      focusState: score >= 70 ? 'High' : score >= 40 ? 'Medium' : 'Low',
      clickCount: pageClicks, typingCount: keypressCount,
      eyeAspectRatio: ear, mouthOpenRatio: mouthOpen, smileScore: smileScore,
      headYaw: yaw, headPitch: pitch, headRoll: roll, affectState
    }})
  }}).catch(() => {{}});
}}

const unameScript = document.querySelector('script[data-username]');
if (unameScript) window.__cs_username = unameScript.dataset.username;

setTimeout(collectSample, 5000);
setInterval(collectSample, 20000);
(function tryStart() {{
  if (!videoStream) {{
    if (window.faceapi && faceapi.nets.tinyFaceDetector.isLoaded) {{
      ensureStream().then(function(ok) {{ if (ok) renderLoop(); }});
    }} else {{
      setTimeout(tryStart, 500);
    }}
  }}
}})();
}})();
</script>
'''
