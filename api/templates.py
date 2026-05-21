from .config import SERVER_BASE_URL


def generate_question_catsoop(q: dict) -> str:
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


def generate_quiz_template(course_id: str, week_id: str) -> str:
    return f'''<python>
import os
cs_content_type = 'text/html'
cs_content_header = "Interactive Quiz"
role = cs_user_info["role"]
username = cs_username
print(f'<script>var userRole = "{{role}}";</script>')
print(f'<script>var userName = "{{username}}";</script>')
</python>

<style>
.panel{{flex:1;padding:20px;border:1px solid #ddd;border-radius:5px;background:#f9f9f9;}}
h1,h2,h3{{color:#2c3e50;}}
button{{background:#4CAF50;color:white;padding:10px 15px;border:none;border-radius:4px;cursor:pointer;margin:5px 0;font-size:14px;}}
button:hover{{background:#45a049;}}
button:disabled{{background:#ccc;cursor:not-allowed;}}
input[type="text"],textarea,select{{width:100%;padding:8px;margin:5px 0;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;}}
.option-input{{display:flex;margin-bottom:5px;}}
.option-input input[type="text"]{{flex-grow:1;margin-right:10px;}}
.question-block{{border:1px solid #ddd;padding:15px;margin-bottom:15px;border-radius:5px;background:white;}}
.feedback{{margin-top:10px;padding:10px;border-radius:4px;display:none;}}
.correct{{background:#d4edda;color:#155724;}}
.incorrect{{background:#f8d7da;color:#721c24;}}
.tab{{overflow:hidden;border:1px solid #ccc;background:#f1f1f1;border-radius:5px 5px 0 0;}}
.tab button{{background:inherit;float:left;border:none;outline:none;cursor:pointer;padding:14px 16px;transition:0.3s;color:#333;}}
.tab button:hover{{background:#ddd;}}
.tab button.active{{background:#4CAF50;color:white;}}
.tabcontent{{display:none;padding:20px;border:1px solid #ccc;border-top:none;border-radius:0 0 5px 5px;}}
.results-container{{margin-top:20px;padding:15px;border:1px solid #ddd;border-radius:5px;background:#f0f7ff;}}
#performanceTable{{width:100%;border-collapse:collapse;text-align:center;}}
#performanceTable th,#performanceTable td{{padding:10px;text-align:center;}}
.hint-btn{{background:#f59e0b;color:white;padding:6px 12px;border:none;border-radius:4px;cursor:pointer;font-size:12px;margin-top:6px;}}
.hint-btn:hover{{background:#d97706;}}
.hint-btn:disabled{{background:#ccc;cursor:not-allowed;}}
.hint-container{{margin-top:8px;padding:10px;border-radius:4px;background:#fffbeb;border:1px solid #fde68a;}}
.hint-item{{margin-bottom:6px;font-size:13px;color:#92400e;}}
.hint-item b{{color:#b45309;}}
.next-hint-btn{{background:#f59e0b;color:white;padding:4px 10px;border:none;border-radius:4px;cursor:pointer;font-size:11px;margin-top:4px;}}
.hint-section{{margin-top:10px;padding:12px;border:1px solid #eee;border-radius:4px;background:#fafafa;}}
.hint-section summary{{cursor:pointer;color:#f59e0b;font-weight:600;}}
.hint-textarea{{width:100%;padding:6px;margin:4px 0;border:1px solid #ddd;border-radius:3px;font-size:0.9em;}}
.hint-badge{{display:inline-block;background:#f59e0b;color:white;padding:1px 7px;border-radius:10px;font-size:0.75em;margin-left:6px;cursor:pointer;vertical-align:middle;}}
.ie-section{{margin-bottom:24px;padding:16px;border:1px solid #ddd;border-radius:5px;background:#f9f9f9;}}
.ie-status{{margin-top:10px;font-size:0.9em;color:#555;}}
.ie-preview{{margin-top:10px;padding:12px;border:1px solid #eee;border-radius:4px;background:#fff;font-size:0.88em;}}
.ie-preview table{{width:100%;border-collapse:collapse;margin:6px 0;}}
.ie-preview td, .ie-preview th{{padding:4px 8px;border:1px solid #eee;text-align:left;font-size:0.95em;}}
.progress-bar{{width:100%;height:8px;background:#e0e0e0;border-radius:4px;margin:8px 0;overflow:hidden;}}
.progress-fill{{height:100%;background:#4CAF50;transition:width 0.3s;}}
.import-btn{{display:none;}}
</style>

<div class="tab">
  <button class="tablinks active" onclick="openTab(event,'createTab')">Create Questions</button>
  <button class="tablinks" onclick="openTab(event,'takeTab')">Take Quiz</button>
  <button class="tablinks" onclick="openTab(event,'importExportTab')">Import/Export</button>
  <button class="tablinks" onclick="openTab(event,'performanceTab')">Student Performance</button>
</div>

<div id="createTab" class="tabcontent" style="display:block;">
  <h2>Create Quiz Questions</h2>
  <textarea id="questionText" rows="3" placeholder="Question text"></textarea>
  <select id="questionType" onchange="handleQuestionTypeChange()">
    <option value="multiple-choice">Multiple Choice</option>
    <option value="checkbox">Multiple Select</option>
    <option value="short-answer">Short Answer</option>
  </select>
  <div id="options-container">
    <div id="optionsGroup">
      <div class="option-input"><input type="text" placeholder="Option 1" class="option-text"><input type="radio" name="correctOption" class="correctOption" checked><label>Correct</label></div>
      <div class="option-input"><input type="text" placeholder="Option 2" class="option-text"><input type="radio" name="correctOption" class="correctOption"><label>Correct</label></div>
    </div>
    <button type="button" onclick="addOption()">Add Option</button>
  </div>
  <div id="short-answer-container" style="display:none;">
    <input type="text" id="shortAnswer" placeholder="Correct answer">
  </div>
  <details class="hint-section">
    <summary>Hints (optional)</summary>
    <div id="hints-form-container"></div>
    <button type="button" onclick="addHintField()" style="font-size:0.85em;background:#f59e0b;margin-top:4px;">+ Add Hint</button>
  </details>
  <button type="button" onclick="addQuestion(event)">Add Question</button>
  <button type="button" onclick="clearForm()">Clear</button>
  <div id="questionsDisplay"><p>No questions yet.</p></div>
</div>

<div id="takeTab" class="tabcontent">
  <div id="quizContainer"><p>No questions available.</p></div>
  <button id="submitQuizBtn" onclick="submitQuiz()" style="display:none;">Submit Quiz</button>
  <div id="attentionPrompt" style="display:none;margin-top:10px;padding:10px;border:1px solid #f59e0b;background:#fffbeb;color:#92400e;border-radius:4px;font-size:0.9em;">👋 Are you still there? Resume when ready.</div>
  <div id="adaptiveSimplify" style="display:none;margin-top:10px;padding:10px;border:1px solid #60a5fa;background:#eff6ff;color:#1e3a8a;border-radius:4px;font-size:0.9em;">Simplified explanation available. Focus on the core idea first.</div>
  <div id="adaptiveAdvanced" style="display:none;margin-top:10px;padding:10px;border:1px solid #10b981;background:#ecfdf5;color:#065f46;border-radius:4px;font-size:0.9em;">Ready for a challenge? Try the advanced extension after you finish.</div>
  <div id="resultsContainer" class="results-container" style="display:none;">
    <h3>Results</h3><p id="scoreDisplay"></p>
    <div id="resultsDetails"></div>
  </div>
</div>

<div id="importExportTab" class="tabcontent">
  <div class="ie-section">
    <h3>Export Quiz</h3>
    <p style="color:#666;font-size:0.9em;">Download all questions and hints as a JSON file.</p>
    <button onclick="exportQuiz()">Export as JSON</button>
    <div id="export-status" class="ie-status"></div>
  </div>
  <div class="ie-section">
    <h3>Import Quiz</h3>
    <p style="color:#666;font-size:0.9em;">Upload a previously exported quiz JSON file.</p>
    <input type="file" id="importFile" accept=".json" onchange="previewImport()">
    <div id="import-preview" class="ie-preview" style="display:none;"></div>
    <div class="import-controls" style="margin-top:10px;display:none;">
      <label style="display:flex;align-items:center;gap:6px;font-size:0.9em;">
        <input type="checkbox" id="import-clear-existing"> Clear existing questions first
      </label>
      <button id="import-confirm-btn" class="import-btn" onclick="confirmImport()">Import Questions</button>
    </div>
    <div id="import-status" class="ie-status"></div>
    <div id="import-progress" style="display:none;">
      <div class="progress-bar"><div id="import-progress-fill" class="progress-fill" style="width:0%;"></div></div>
      <span id="import-progress-text" style="font-size:0.85em;color:#666;"></span>
    </div>
  </div>
</div>

<div id="performanceTab" class="tabcontent">
  <h2>Student Performance</h2>
  <table id="performanceTable" border="1" cellpadding="8">
    <thead><tr><th>Student</th><th>Score</th><th>Date</th><th>Total</th><th>%</th><th>Time</th><th>Clicks</th><th>Hints</th></tr></thead>
    <tbody id="otbody"><tr><td colspan="8">No data yet.</td></tr></tbody>
  </table>
</div>

<script>
var course='{course_id}', week='{week_id}';
const serverIp='{SERVER_BASE_URL}';
const apiBase=serverIp+'/'+course+'/'+week+'/example_questions';
const hintsApi=serverIp+'/admin/hints/';
const attemptUrl=serverIp+'/'+course+'/'+week+'/submit_attempt';
const bulkImportUrl=serverIp+'/admin/questions-with-hints';
const deleteAllUrl=serverIp+'/admin/questions/'+course+'/'+week;
const socket=new WebSocket('ws://'+serverIp.replace('http://','').replace('https://','')+'/ws');
socket.onmessage=(e)=>{{const d=JSON.parse(e.data);if(d.type==='NEW_SUBMISSION'&&userRole!=='Student')loadPerformance();}};
let totalActiveSeconds=0,pageClicks=0,lastInteractionTime=Date.now();
document.addEventListener('click',()=>{{pageClicks++;lastInteractionTime=Date.now();}});
let keypressCount=0;
document.addEventListener('keydown',()=>{{keypressCount++;lastInteractionTime=Date.now();}});
setInterval(()=>{{if(!document.hidden&&(Date.now()-lastInteractionTime)<60000)totalActiveSeconds+=1;}},1000);
let activeQuestions=[];
const hintCache={{}};
const hintLevel={{}};
let pendingImportData=null;
const attemptSessionId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + '-' + Math.random().toString(36).slice(2);
let engagementTimer=null;
let lastEngagementSent=0;
let lastTriggerState={{ simplify:false, advanced:false, prompt:false }};
let faceModelLoaded=false;
let engagementVideoStream=null;
let engagementVideoEl=null;

async function loadFaceModel(){{
  if(faceModelLoaded) return true;
  if(!window.faceDetection) return false;
  try{{
    const model = faceDetection.SupportedModels.MediaPipeFaceDetector;
    const detectorConfig = {{ runtime: 'tfjs', maxFaces: 1 }};
    window._faceDetector = await faceDetection.createDetector(model, detectorConfig);
    faceModelLoaded = true;
    return true;
  }}catch(e){{
    return false;
  }}
}}

async function ensureEngagementStream(){{
  if(engagementVideoStream) return true;
  try{{
    engagementVideoStream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
    engagementVideoEl = document.createElement('video');
    engagementVideoEl.srcObject = engagementVideoStream;
    engagementVideoEl.setAttribute('playsinline','true');
    await engagementVideoEl.play();
    return true;
  }}catch(e){{
    return false;
  }}
}}

function computeEngagementScore(facePresent, gazeCentered, headPose, inactivitySeconds){{
  let score = 100;
  if(!facePresent) score -= 45;
  if(!gazeCentered) score -= 20;
  if(headPose === 'down') score -= 15;
  if(headPose === 'left' || headPose === 'right') score -= 10;
  if(inactivitySeconds > 120) score -= 25;
  if(inactivitySeconds > 60 && inactivitySeconds <= 120) score -= 10;
  score = Math.max(0, Math.min(100, score));
  return score;
}}

function focusStateFromScore(score){{
  if(score >= 80) return 'High';
  if(score >= 50) return 'Medium';
  return 'Low';
}}

function triggerAdaptive(score, inactivitySeconds){{
  const simplify = score < 40;
  const advanced = score > 80;
  const prompt = inactivitySeconds > 120;
  if(simplify !== lastTriggerState.simplify){{
    document.getElementById('adaptiveSimplify').style.display = simplify ? 'block' : 'none';
    lastTriggerState.simplify = simplify;
  }}
  if(advanced !== lastTriggerState.advanced){{
    document.getElementById('adaptiveAdvanced').style.display = advanced ? 'block' : 'none';
    lastTriggerState.advanced = advanced;
  }}
  if(prompt !== lastTriggerState.prompt){{
    document.getElementById('attentionPrompt').style.display = prompt ? 'block' : 'none';
    lastTriggerState.prompt = prompt;
  }}
}}

function estimateHeadPose(face){{
  if(!face || !face.keypoints) return 'center';
  const nose = face.keypoints.find(k => k.name === 'noseTip' || k.name === 'nose') || face.keypoints[0];
  const leftEye = face.keypoints.find(k => k.name === 'leftEye') || face.keypoints[1];
  const rightEye = face.keypoints.find(k => k.name === 'rightEye') || face.keypoints[2];
  if(!nose || !leftEye || !rightEye) return 'center';
  const eyeMidX = (leftEye.x + rightEye.x) / 2;
  const eyeMidY = (leftEye.y + rightEye.y) / 2;
  const dx = nose.x - eyeMidX;
  const dy = nose.y - eyeMidY;
  if(dy > 12) return 'down';
  if(dx > 12) return 'right';
  if(dx < -12) return 'left';
  return 'center';
}}

function estimateGazeCentered(face){{
  if(!face || !face.keypoints) return false;
  const leftEye = face.keypoints.find(k => k.name === 'leftEye');
  const rightEye = face.keypoints.find(k => k.name === 'rightEye');
  if(!leftEye || !rightEye) return false;
  const dx = Math.abs(leftEye.x - rightEye.x);
  return dx > 20;
}}

async function collectEngagementSample(){{
  if(document.hidden || userRole === 'Instructor') return;
  const now = Date.now();
  if(now - lastEngagementSent < 20000) return;
  lastEngagementSent = now;
  const inactivitySeconds = Math.floor((now - lastInteractionTime) / 1000);
  let facePresent = false;
  let gazeCentered = false;
  let headPose = 'center';
  if(await ensureEngagementStream() && await loadFaceModel()){{
    try{{
      const faces = await window._faceDetector.estimateFaces(engagementVideoEl);
      if(faces && faces.length){{
        facePresent = true;
        headPose = estimateHeadPose(faces[0]);
        gazeCentered = estimateGazeCentered(faces[0]);
      }}
    }}catch(e){{}}
  }}
  const score = computeEngagementScore(facePresent, gazeCentered, headPose, inactivitySeconds);
  const focusState = focusStateFromScore(score);
  triggerAdaptive(score, inactivitySeconds);
  try{{
    await fetch(serverIp + '/' + course + '/' + week + '/engagement', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{
        attemptSessionId,
        username: userName || 'unknown',
        course,
        week,
        timestamp: new Date().toISOString(),
        facePresent,
        gazeCentered,
        headPose,
        inactivitySeconds,
        engagementScore: score,
        focusState,
        clickCount: pageClicks,
        typingCount: keypressCount,
      }})
    }});
  }}catch(e){{}}
}}

async function getHint(qid){{
  if(!hintCache[qid]){{
    try{{
      const r=await fetch(serverIp+'/admin/hints/'+qid);
      if(!r.ok) throw new Error();
      const d=await r.json();
      hintCache[qid]=d.hints||[];
    }}catch{{hintCache[qid]=[];}}
  }}
  const hints=hintCache[qid];
  if(!hints.length){{
    const el=document.getElementById('hint-'+qid);
    el.style.display='block';
    el.innerHTML='<div class="hint-item">No hints available for this question.</div>';
    const btn=document.getElementById('hintbtn-'+qid);
    btn.disabled=true;btn.textContent='No hints';
    return;
  }}
  if(!hintLevel[qid]) hintLevel[qid]=0;
  if(hintLevel[qid]>=hints.length)return;
  hintLevel[qid]++;
  const el=document.getElementById('hint-'+qid);
  el.style.display='block';
  const hint=hints[hintLevel[qid]-1];
  const div=document.createElement('div');
  div.className='hint-item';
  div.innerHTML='<b>Hint '+hintLevel[qid]+' of '+hints.length+':</b> '+hint;
  el.appendChild(div);
  const btn=document.getElementById('hintbtn-'+qid);
  if(hintLevel[qid]<hints.length){{
    btn.textContent='Next Hint ('+hintLevel[qid]+'/'+hints.length+')';
  }} else {{
    btn.disabled=true;btn.textContent='No more hints';
  }}
}}

function handleQuestionTypeChange(){{const t=document.getElementById('questionType').value;document.getElementById('options-container').style.display=t==='short-answer'?'none':'block';document.getElementById('short-answer-container').style.display=t==='short-answer'?'block':'none';document.querySelectorAll('.correctOption').forEach(el=>{{el.type=t==='checkbox'?'checkbox':'radio';}});}}
function addOption(){{const div=document.createElement('div');div.className='option-input';div.innerHTML='<input type="text" placeholder="Option" class="option-text"><input type="radio" name="correctOption" class="correctOption"><label>Correct</label>';document.getElementById('optionsGroup').appendChild(div);}}
function clearForm(){{document.getElementById('questionText').value='';document.getElementById('shortAnswer').value='';const hc=document.getElementById('hints-form-container');if(hc)hc.innerHTML='';}}
function addHintField(){{const c=document.getElementById('hints-form-container');if(!c)return;const idx=c.children.length+1;const ta=document.createElement('textarea');ta.className='hint-textarea';ta.placeholder='Hint '+idx;ta.rows=2;c.appendChild(ta);}}
function getHints(){{const c=document.getElementById('hints-form-container');if(!c)return[];const hints=[];c.querySelectorAll('.hint-textarea').forEach(t=>{{if(t.value.trim())hints.push(t.value.trim());}});return hints;}}
async function addQuestion(e){{if(e)e.preventDefault();const text=document.getElementById('questionText').value;const type=document.getElementById('questionType').value;let options=[],correctAnswers=[];if(type==='short-answer'){{correctAnswers=[document.getElementById('shortAnswer').value];}}else{{document.querySelectorAll('.option-input').forEach((div,i)=>{{const val=div.querySelector('.option-text').value;if(val){{options.push(val);if(div.querySelector('.correctOption').checked)correctAnswers.push(i);}}}});}}const hints=getHints();const payload={{username:userName,text,type,options,correctAnswers}};if(hints.length)payload.hints=hints;const resp=await fetch(apiBase,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});if(resp.ok){{alert('Saved!'+(hints.length?' ('+hints.length+' hints added)':''));clearForm();updateQuestionsDisplay();}}}}
async function updateQuestionsDisplay(){{const c=document.getElementById('questionsDisplay');try{{const r=await fetch(apiBase);const q=await r.json();if(!Array.isArray(q)){{c.innerHTML='<p style="color:red">Error</p>';return;}}c.innerHTML=q.map((q,i)=>'<div class="question-block"><b>'+(i+1)+'. '+q.text+'</b> ('+q.qtype+') <button onclick="deleteQ('+q.id+')">Delete</button> <span id="delete-status-'+q.id+'" style="font-size:0.8em;color:#888;margin-left:6px;"></span></div>').join('');}}catch{{c.innerHTML='No questions or server offline.';}}}}
async function deleteQ(id){{if(!confirm('Delete this question?'))return;const status=document.getElementById('delete-status-'+id);try{{const resp=await fetch(apiBase+'/'+id,{{method:'DELETE'}});if(resp.ok){{status.textContent='Deleted';status.style.color='green';setTimeout(()=>{{status.textContent='';}},1500);updateQuestionsDisplay();}}else{{const e=await resp.json();status.textContent=e.detail||'Delete failed';status.style.color='red';}}}}catch(err){{status.textContent='Network error';status.style.color='red';}}}}
async function renderQuiz(){{const c=document.getElementById('quizContainer');const r=await fetch(apiBase);activeQuestions=await r.json();if(!activeQuestions.length){{c.innerHTML='No questions.';return;}}c.innerHTML=activeQuestions.map((q,i)=>{{let h='';if(q.qtype==='short-answer')h='<input type="text" id="ans-'+q.id+'" class="quiz-ans">';else h=q.options.map((o,oi)=>'<div><input type="'+(q.qtype==='checkbox'?'checkbox':'radio')+'" name="q-'+q.id+'" value="'+oi+'"> '+o+'</div>').join('');return'<div class="question-block"><b>'+(i+1)+'. '+q.text+'</b><br>'+h+'<div id="feed-'+q.id+'" class="feedback"></div><button class="hint-btn" id="hintbtn-'+q.id+'" onclick="getHint('+q.id+')">💡 Get Hint</button><div id="hint-'+q.id+'" class="hint-container" style="display:none;"></div></div>';}}).join('');document.getElementById('submitQuizBtn').style.display='block';}}
async function submitQuiz(){{let score=0;const results=[];activeQuestions.forEach(q=>{{let ok=false,uv='';if(q.qtype==='short-answer'){{uv=document.getElementById('ans-'+q.id).value.trim();ok=uv.toLowerCase()===q.correct_answers[0].toLowerCase();}}else{{const sel=Array.from(document.querySelectorAll('input[name="q-'+q.id+'"]:checked')).map(el=>parseInt(el.value));ok=JSON.stringify(sel.sort())===JSON.stringify(q.correct_answers.sort());uv=sel.map(i=>q.options[i]).join(', ');}}if(ok)score++;const f=document.getElementById('feed-'+q.id);f.style.display='block';f.innerHTML=ok?'✅ Correct':'❌ Incorrect';f.className='feedback '+(ok?'correct':'incorrect');results.push({{question:q.text,userAnswer:uv,isCorrect:ok,hintsUsed:hintLevel[q.id]||0}});}});const totalHints=Object.values(hintLevel).reduce((a,b)=>a+b,0);await fetch(attemptUrl,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{username:userName,score,total:activeQuestions.length,course,week,results,metrics:{{secondsSpent:totalActiveSeconds,clickCount:pageClicks,exitTime:new Date().toISOString(),hintCount:totalHints}},attemptSessionId}})}});document.getElementById('resultsContainer').style.display='block';document.getElementById('scoreDisplay').innerText='You scored '+score+' / '+activeQuestions.length;let details='<h4 style="margin-top:16px;">Question Details</h4>';results.forEach((r,i)=>{{details+='<div style="margin:6px 0;padding:6px;border-left:3px solid '+(r.isCorrect?'#22c55e':'#ef4444')+';font-size:0.9em;">'+(i+1)+'. '+r.question.substring(0,60)+(r.question.length>60?'...':'')+' — '+(r.isCorrect?'✅':'❌')+(r.hintsUsed?' (hints used: '+r.hintsUsed+')':'')+'</div>';}});document.getElementById('resultsDetails').innerHTML=details;}}
async function exportQuiz(){{const st=document.getElementById('export-status');st.textContent='Fetching questions...';try{{const r=await fetch(apiBase);const questions=await r.json();if(!questions.length){{st.textContent='No questions to export.';return;}}st.textContent='Fetching hints...';const exportData=questions.map(q=>({{id:q.id,text:q.text,type:q.qtype,options:q.options||[],correct_answers:q.correct_answers||[]}}));for(const q of exportData){{try{{const hr=await fetch(hintsApi+q.id);if(hr.ok){{const hd=await hr.json();q.hints=hd.hints.map(h=>h.text).filter(Boolean);}}}}catch{{q.hints=[];}}}}st.textContent='Exporting '+exportData.length+' questions...';const a=document.createElement('a');a.href='data:text/json;charset=utf-8,'+encodeURIComponent(JSON.stringify(exportData,null,2));a.download=course+'_'+week+'_quiz.json';document.body.appendChild(a);a.click();a.remove();st.textContent='Exported '+exportData.length+' questions successfully.';}}catch(e){{st.textContent='Export failed: '+e.message;}}}}
function previewImport(){{const fi=document.getElementById('importFile');if(!fi.files.length)return;const st=document.getElementById('import-status');st.textContent='';try{{const reader=new FileReader();reader.onload=(e)=>{{try{{const data=JSON.parse(e.target.result);let qs=Array.isArray(data)?data:(data.questions||[]);pendingImportData=qs;const typeCounts={{}};qs.forEach(q=>{{const t=q.type||q.qtype||'unknown';typeCounts[t]=(typeCounts[t]||0)+1;}});let html='<b>'+qs.length+' questions found</b><table><tr><th>#</th><th>Type</th><th>Question</th><th>Hints</th></tr>';qs.forEach((q,i)=>{{const t=q.type||q.qtype||'?';const txt=(q.text||'').substring(0,60);const h=(q.hints||[]).length;html+='<tr><td>'+(i+1)+'</td><td>'+t+'</td><td>'+txt+'</td><td>'+(h?h+' 💡':'—')+'</td></tr>';}});html+='</table>';document.getElementById('import-preview').innerHTML=html;document.getElementById('import-preview').style.display='block';document.querySelector('.import-controls').style.display='block';}}catch(err){{st.textContent='Invalid JSON file: '+err.message;pendingImportData=null;document.getElementById('import-preview').style.display='none';document.querySelector('.import-controls').style.display='none';}};reader.readAsText(fi.files[0]);}}catch(err){{st.textContent='Error reading file: '+err.message;}}}}
async function confirmImport(){{if(!pendingImportData||!pendingImportData.length)return;const st=document.getElementById('import-status');const pg=document.getElementById('import-progress');const pgFill=document.getElementById('import-progress-fill');const pgText=document.getElementById('import-progress-text');const clearExisting=document.getElementById('import-clear-existing').checked;if(clearExisting){{st.textContent='Clearing existing questions...';try{{await fetch(deleteAllUrl,{{method:'DELETE'}});}}catch(e){{st.textContent='Failed to clear existing questions.';return;}}}}st.textContent='';pg.style.display='block';const total=pendingImportData.length;let done=0,failed=0;for(let i=0;i<total;i++){{const q=pendingImportData[i];const payload={{username:userName,text:q.text,type:q.type||q.qtype,options:q.options||[],correctAnswers:q.correct_answers||[]}};if(q.hints&&q.hints.length)payload.hints=q.hints;try{{const r=await fetch(apiBase,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});if(r.ok)done++;else failed++;}}catch{{failed++;}}done++;pgFill.style.width=((done/total)*100)+'%';pgText.textContent='Importing '+done+'/'+total+'...';}}pg.style.display='none';st.textContent='Imported '+done+' questions.'+(failed?' ('+failed+' failed)':'');updateQuestionsDisplay();document.getElementById('import-preview').style.display='none';document.querySelector('.import-controls').style.display='none';}}
async function loadPerformance(){{const tb=document.getElementById('otbody');try{{const r=await fetch(serverIp+'/'+course+'/'+week+'/all_attempts');const d=await r.json();if(!d.attempts||!d.attempts.length){{tb.innerHTML='<tr><td colspan="8">No data.</td></tr>';return;}}tb.innerHTML=d.attempts.map(a=>{{const p=Math.round((a.score/a.total)*100);const m=Math.floor((a.seconds_spent||0)/60),s=(a.seconds_spent||0)%60;return'<tr><td>'+(a.username||'?')+'</td><td>'+a.score+'/'+a.total+'</td><td>'+new Date(a.submitted_at).toLocaleString()+'</td><td>'+a.total+'</td><td>'+p+'%</td><td>'+m+'m '+s+'s</td><td>'+(a.click_count||0)+'</td><td>'+(a.hint_count||0)+'</td></tr>';}}).join('');}}catch{{tb.innerHTML='<tr><td colspan="8">Error.</td></tr>';}}}}
function openTab(evt,n){{document.querySelectorAll('.tabcontent').forEach(t=>t.style.display='none');document.querySelectorAll('.tablinks').forEach(t=>t.classList.remove('active'));document.getElementById(n).style.display='block';if(evt)evt.currentTarget.classList.add('active');if(n==='takeTab')renderQuiz();if(n==='performanceTab')loadPerformance();}}
window.onload=()=>{{
  updateQuestionsDisplay();
  if(userRole==='Student'){{
    document.getElementById('createTab').style.display='none';
    document.querySelector('[onclick*="createTab"]').style.display='none';
    document.querySelector('[onclick*="importExportTab"]').style.display='none';
    document.querySelector('[onclick*="performanceTab"]').style.display='none';
    openTab(null,'takeTab');
  }}
  if(!window.faceDetection){{
    const s=document.createElement('script');
    s.src='https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js';
    document.head.appendChild(s);
    const s2=document.createElement('script');
    s2.src='https://cdn.jsdelivr.net/npm/@tensorflow-models/face-detection@1.0.3/dist/face-detection.min.js';
    document.head.appendChild(s2);
  }}
  engagementTimer = setInterval(collectEngagementSample, 20000);
}};
</script>
'''


def generate_live_file_panel() -> str:
    return '''
<div id="live-file-panel" style="display:none;margin:20px 0;padding:16px;border:1px solid #ddd;border-radius:6px;background:#f9f9f9;">
  <strong>Live File</strong>
  <div id="live-file-content" style="margin-top:8px;color:#555;"></div>
</div>
<script>
(function(){
  const parts = window.location.pathname.split('/').filter(Boolean);
  const apiBase = '__API_BASE__';
  let course = '', week = '';
  if(parts.length >= 3 && parts[0] === 'courses'){
    course = parts[1];
    week = parts[2];
  } else if(parts.length >= 2 && parts[0] !== 'courses'){
    course = parts[0];
    week = parts[1];
  } else {
    return;
  }
  course = course.trim();
  week = week.trim();
  if(!course || !week) return;
  const panel = document.getElementById('live-file-panel');
  const content = document.getElementById('live-file-content');
    function renderFile(meta){
    if(!meta){
      panel.style.display = 'none';
      return;
    }
    const url = apiBase + '/live-file/' + course + '/' + week;
    const dlUrl = url + '?download=1';
    const type = meta.content_type || '';
    const safeName = meta.filename || 'file';
    let html = '<div><a href="' + dlUrl + '" style="color:#2572F5;text-decoration:underline;cursor:pointer;">Download ' + safeName + '</a></div>';
    if(type.startsWith('image/')){
      fetch(url).then(r=>r.blob()).then(b=>{
        const el = document.getElementById('live-file-img');
        if(el) el.src = URL.createObjectURL(b);
      });
      html += '<div style="margin-top:10px;"><img id="live-file-img" src="" alt="' + safeName + '" style="max-width:100%;height:auto;border:1px solid #ddd;border-radius:4px;"/></div>';
    } else if(type === 'application/pdf'){
      fetch(url).then(r=>r.blob()).then(b=>{
        const el = document.getElementById('live-file-iframe');
        if(el) el.src = URL.createObjectURL(b);
      });
      html += '<div style="margin-top:10px;"><iframe id="live-file-iframe" src="" style="width:100%;height:480px;border:1px solid #ddd;border-radius:4px;"></iframe></div>';
    } else if(type.startsWith('text/')){
      fetch(url).then(r=>r.blob()).then(b=>{
        const el = document.getElementById('live-file-iframe');
        if(el) el.src = URL.createObjectURL(b);
      });
      html += '<div style="margin-top:10px;"><iframe id="live-file-iframe" src="" style="width:100%;height:320px;border:1px solid #ddd;border-radius:4px;background:#fff;"></iframe></div>';
    }
    content.innerHTML = html;
    panel.style.display = 'block';
  }
  async function load(){
    try{
      const r = await fetch(apiBase + '/admin/live-file/' + course + '/' + week);
      if(!r.ok){renderFile(null);return;}
      const d = await r.json();
      renderFile(d || null);
    }catch{
      renderFile(null);
    }
  }
  load();
  setInterval(load, 15000);
})();
</script>
'''.replace('__API_BASE__', SERVER_BASE_URL)


def generate_lecture_template(title: str, content: str) -> str:
    return f'''<python>
cs_content_header = "{title}"
</python>
<style>
h1,h2,h3{{color:#333;}}
h1{{border-bottom:3px solid #2572F5;padding-bottom:10px;}}
h2{{color:#2572F5;margin-top:30px;}}
.highlight{{background:#e7f3ff;border-left:4px solid #2572F5;padding:15px;margin:20px 0;border-radius:5px;}}
table{{width:100%;border-collapse:collapse;margin:20px 0;}}
th,td{{border:1px solid #ddd;padding:12px;text-align:left;}}
th{{background:#2572F5;color:white;}}
tr:nth-child(even){{background:#f2f2f2;}}
code{{background:#f4f4f4;padding:2px 6px;border-radius:3px;color:#d63384;}}
</style>
{content}
'''


def generate_native_quiz(course_id: str, week_id: str, questions: list) -> str:
    """
    Generate a .catsoop file with native <question> tags from SQLite questions.
    Uses CAT-SOOP's default handler for rendering, grading, and logging.
    Includes hint integration JS that works with the engine's question divs.
    """
    qtype_map = {
        "multiple-choice": "multiplechoice",
        "checkbox": "multiplechoice",
        "short-answer": "smallbox",
        "true_false": "multiplechoice",
        "short_answer": "smallbox",
        "multiple_choice": "multiplechoice",
        "numerical": "numerical",
        "symbolic": "expression",
        "pythoncode": "pythoncode",
    }

    import html as html_mod

    def esc(text):
        return html_mod.escape(str(text))

    hint_list = []
    question_tags = []

    for i, q in enumerate(questions):
        qid = q.id if hasattr(q, 'id') else q.get('id', i)
        name = f"q_{qid}"
        raw_type = q.question_type if hasattr(q, 'question_type') else q.get('type', 'short-answer')
        text = q.question_text if hasattr(q, 'question_text') else q.get('text', '')
        options = q.options if hasattr(q, 'options') else q.get('options', [])
        correct = q.correct_answers if hasattr(q, 'correct_answers') else q.get('correctAnswers', [])

        catsoop_type = qtype_map.get(raw_type, "shortanswer")

        hint_list.append(qid)

        if catsoop_type == "multiplechoice":
            is_checkbox = raw_type in ("checkbox", "multiple_select")
            renderer = "checkbox" if is_checkbox else "radio"
            _opts = [str(o) for o in (options or [])]
            if is_checkbox:
                _soln = [str(i) in correct or i in correct for i in range(len(_opts))]
                soln_mode_line = ""
            else:
                correct_idx = next((i for i in range(len(_opts)) if str(i) in correct or i in correct), 0)
                _soln = _opts[correct_idx] if _opts else ""
                soln_mode_line = 'csq_soln_mode = "value"'

            tag = f'''<question multiplechoice>
csq_prompt = {repr(text)}
csq_options = {_opts!r}
csq_soln = {_soln!r}
csq_renderer = {renderer!r}
csq_name = {name!r}
csq_npoints = 1
{soln_mode_line}
</question>'''
            question_tags.append(tag)

        elif catsoop_type == "smallbox":
            answer = str(correct[0]) if correct else ""
            tag = f'''<question smallbox>
csq_prompt = {repr(text)}
csq_soln = {repr(answer)}
csq_name = {name!r}
csq_npoints = 1
csq_size = 30
</question>'''
            question_tags.append(tag)

        elif catsoop_type == "numerical":
            answer = str(correct[0]) if correct else "0"
            tag = f'''<question expression>
csq_prompt = {repr(text)}
csq_soln = [{repr(answer)}]
csq_name = {name!r}
csq_npoints = 1
</question>'''
            question_tags.append(tag)

        elif catsoop_type == "expression":
            answer = str(correct[0]) if correct else ""
            tag = f'''<question expression>
csq_prompt = {repr(text)}
csq_soln = [{repr(answer)}]
csq_name = {name!r}
csq_npoints = 1
</question>'''
            question_tags.append(tag)

        elif catsoop_type == "pythoncode":
            test_code = "assert solution() is not None"
            tag = f'''<question pythoncode>
csq_prompt = {repr(text)}
csq_initial = {repr("# Write your solution here\ndef solution():\n    pass")}
csq_soln = {repr(str(correct[0]) if correct else "")}
csq_tests = {repr([{"code": test_code, "name": "Test"}])}
csq_name = {name!r}
csq_npoints = 1
</question>'''
            question_tags.append(tag)

        else:
            answer = str(correct[0]) if correct else ""
            tag = f'''<question smallbox>
csq_prompt = {repr(text)}
csq_soln = {repr(answer)}
csq_name = {name!r}
csq_npoints = 1
csq_size = 30
</question>'''
            question_tags.append(tag)

    # Build the full .catsoop content
    import json as json_mod
    hint_map_json = json_mod.dumps(hint_list)

    header = f'''<python>
cs_content_header = "Quiz: {esc(course_id)} - {esc(week_id)}"
cs_show_due = True
cs_update_questions_cache = True
import json
# Pass user info and question IDs to client JS
print(f'<script data-username="{{cs_username}}">')
print(f'window.__cs_username = "{{cs_username}}";')
print(f'window.__cs_user_role = "{{cs_user_info.get("role", "Student")}}";')
print(f'window.__quizQuestionIds = {hint_map_json};')
print(f'window.__course = "{esc(course_id)}";')
print(f'window.__week = "{esc(week_id)}";')
print('</script>')
</python>

<style>
.question {{ margin-bottom: 1.5em; }}
.hint-btn-container {{ margin-top: 8px; }}
</style>

'''

    question_count = len(question_tags)
    body = "\n\n".join(question_tags)

    if question_count > 0:
        body = f'''<div id="quiz-start-screen" style="text-align:center;padding:40px 20px;">
  <h2 style="color:#2c3e50;margin-bottom:16px;">Quiz: {esc(week_id)}</h2>
  <p style="font-size:1.1em;color:#555;margin-bottom:8px;">This quiz contains <strong>{question_count}</strong> question{"s" if question_count != 1 else ""}.</p>
  <p style="font-size:0.95em;color:#777;margin-bottom:24px;">You can check and submit your answers when ready.</p>
  <button onclick="document.getElementById('quiz-start-screen').style.display='none';document.getElementById('quiz-questions').style.display='block';window.__quizStarted=true;" style="background:#4CAF50;color:white;padding:14px 36px;border:none;border-radius:6px;cursor:pointer;font-size:1.1em;">Start Quiz</button>
</div>
<div id="quiz-questions" style="display:none;">
{body}
</div>'''
    else:
        body = '<p style="text-align:center;padding:40px;color:#888;">No questions available yet.</p>'

    # Hint injection script: adds hint buttons to native engine question divs
    hint_script = f'''
<script>
(function() {{
    const apiBase = '{course_id}';
    const hintCache = {{}};
    const hintLevel = {{}};

    async function fetchHints(qid) {{
        if (hintCache[qid]) return hintCache[qid];
        try {{
            const r = await fetch('/admin/hints/' + qid);
            if (!r.ok) throw new Error();
            const d = await r.json();
            hintCache[qid] = d.hints || [];
        }} catch {{
            hintCache[qid] = [];
        }}
        return hintCache[qid];
    }}

    function addHintButton(qid, container) {{
        const btn = document.createElement('button');
        btn.textContent = '💡 Hint';
        btn.className = 'hint-btn';
        btn.style.cssText = 'background:#f59e0b;color:white;padding:6px 12px;border:none;border-radius:4px;cursor:pointer;font-size:12px;margin-top:8px;';

        const hintBox = document.createElement('div');
        hintBox.className = 'hint-container';
        hintBox.style.cssText = 'display:none;margin-top:6px;padding:10px;border-radius:4px;background:#fffbeb;border:1px solid #fde68a;';

        btn.onclick = async function() {{
            const hints = await fetchHints(qid);
            if (!hints.length) {{
                hintBox.style.display = 'block';
                hintBox.innerHTML = '<div style="font-size:13px;color:#92400e;">No hints available.</div>';
                btn.disabled = true;
                btn.textContent = 'No hints';
                return;
            }}
            if (!hintLevel[qid]) hintLevel[qid] = 0;
            if (hintLevel[qid] >= hints.length) return;
            hintLevel[qid]++;
            hintBox.style.display = 'block';
            const div = document.createElement('div');
            div.style.cssText = 'margin-bottom:6px;font-size:13px;color:#92400e;';
            div.innerHTML = '<b>Hint ' + hintLevel[qid] + ' of ' + hints.length + ':</b> ' + hints[hintLevel[qid]-1].text;
            hintBox.appendChild(div);
            if (hintLevel[qid] >= hints.length) {{
                btn.textContent = 'No more hints';
                btn.disabled = true;
            }} else {{
                btn.textContent = 'Next Hint (' + hintLevel[qid] + '/' + hints.length + ')';
            }}
        }};

        container.appendChild(btn);
        container.appendChild(hintBox);
    }}

    function initHints() {{
        const qids = window.__quizQuestionIds || [];
        qids.forEach(function(qid) {{
            const name = 'q_' + qid;
            const div = document.getElementById('cs_qdiv_' + name);
            if (div) {{
                const container = document.createElement('div');
                container.className = 'hint-btn-container';
                container.style.cssText = 'margin-top:8px;';
                div.appendChild(container);
                addHintButton(qid, container);
            }}
        }});
    }}

    function initWS() {{
        if (window.__liveWS) return;
        const room = (window.__course || 'unknown') + '/' + (window.__week || 'unknown');
        const username = window.__cs_username || 'anon';
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname + (window.location.port ? ':' + window.location.port : '');
        try {{
            const ws = new WebSocket(proto + '//' + host + '/ws');
            ws.onopen = function() {{
                ws.send(JSON.stringify({{ type: 'JOIN', username: username, room: room }}));
                window.__liveWS = ws;
            }};
            ws.onmessage = function(e) {{
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
            ws.onclose = function() {{ window.__liveWS = null; }};
        }} catch {{}}
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', function() {{ initHints(); initWS(); }});
    }} else {{
        initHints();
        initWS();
    }}
}})();
</script>
'''

    affect_script = generate_affect_script("")
    return header + body + hint_script + affect_script


def generate_affect_script(server_base_url: str = "") -> str:
    """Standalone affect detection JS injected into engine pages.
    Uses FaceLandmarker for richer features: EAR, head pose (6 DOF), mouth ratio.
    Maps to affect states: focused / confused / disengaged / distracted / fatigued.
    """
    return f'''
<script>
(function() {{
if (window.__affectInjected) return;
window.__affectInjected = true;

const API = '{server_base_url}';
const attemptSessionId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + '-' + Math.random().toString(36).slice(2);
let engagementTimer = null;
let videoStream = null;
let videoEl = null;
let faceDetector = null;
let faceModelLoaded = false;
let lastInteractionTime = Date.now();
let lastEngagementSent = 0;
let pageClicks = 0;
let keypressCount = 0;
let totalActiveSeconds = 0;
let lastAffectState = null;

document.addEventListener('click', () => {{ pageClicks++; lastInteractionTime = Date.now(); }});
document.addEventListener('keydown', () => {{ keypressCount++; lastInteractionTime = Date.now(); }});

const pathParts = window.location.pathname.split('/').filter(Boolean);
let course = '', week = '';
if (pathParts.length >= 2 && pathParts[0] !== 'courses') {{ course = pathParts[0]; week = pathParts[1]; }}
else if (pathParts.length >= 3 && pathParts[0] === 'courses') {{ course = pathParts[1]; week = pathParts[2]; }}
if (!course) course = 'unknown';
if (!week) week = 'unknown';

async function loadTFJS() {{
  if (window.tf) return true;
  return new Promise(resolve => {{
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js';
    s.onload = () => {{
      const s2 = document.createElement('script');
      s2.src = 'https://cdn.jsdelivr.net/npm/@tensorflow-models/face-detection@1.0.3/dist/face-detection.min.js';
      s2.onload = () => resolve(true);
      s2.onerror = () => resolve(false);
      document.head.appendChild(s2);
    }};
    s.onerror = () => resolve(false);
    document.head.appendChild(s);
  }});
}}

async function ensureStream() {{
  if (videoStream) return true;
  try {{
    videoStream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
    videoEl = document.createElement('video');
    videoEl.srcObject = videoStream;
    videoEl.setAttribute('playsinline', 'true');
    await videoEl.play();
    return true;
  }} catch {{ return false; }}
}}

async function loadDetector() {{
  if (faceModelLoaded) return true;
  if (!window.faceDetection) return false;
  try {{
    faceDetector = await faceDetection.createDetector(
      faceDetection.SupportedModels.MediaPipeFaceDetector,
      {{ runtime: 'tfjs', maxFaces: 1 }}
    );
    faceModelLoaded = true;
    return true;
  }} catch {{ return false; }}
}}

function computeEAR(eye) {{
  if (!eye || eye.length < 6) return 0.35;
  const v1 = Math.hypot(eye[1].x - eye[5].x, eye[1].y - eye[5].y);
  const v2 = Math.hypot(eye[2].x - eye[4].x, eye[2].y - eye[4].y);
  const h = Math.hypot(eye[0].x - eye[3].x, eye[0].y - eye[3].y);
  return h > 0 ? (v1 + v2) / (2 * h) : 0.35;
}}

function computeMouthRatio(face) {{
  if (!face || !face.keypoints) return 0;
  const upper = face.keypoints.find(k => k.name === 'upperLipTop' || k.name === 'lipsUpperOuter');
  const lower = face.keypoints.find(k => k.name === 'lowerLipBottom' || k.name === 'lipsLowerOuter');
  const left = face.keypoints.find(k => k.name === 'mouthLeft' || k.name === 'lipsLeftOuter');
  const right = face.keypoints.find(k => k.name === 'mouthRight' || k.name === 'lipsRightOuter');
  if (!upper || !lower || !left || !right) return 0;
  const mh = Math.hypot(upper.x - lower.x, upper.y - lower.y);
  const mw = Math.hypot(left.x - right.x, left.y - right.y);
  return mw > 0 ? mh / mw : 0;
}}

function estimateHeadPose(face) {{
  if (!face || !face.keypoints) return {{ pose: 'center', yaw: 0, pitch: 0, roll: 0 }};
  const nose = face.keypoints.find(k => k.name === 'noseTip') || face.keypoints[0];
  const lEye = face.keypoints.find(k => k.name === 'leftEye') || face.keypoints[1];
  const rEye = face.keypoints.find(k => k.name === 'rightEye') || face.keypoints[2];
  if (!nose || !lEye || !rEye) return {{ pose: 'center', yaw: 0, pitch: 0, roll: 0 }};
  const eyeMidX = (lEye.x + rEye.x) / 2;
  const eyeMidY = (lEye.y + rEye.y) / 2;
  const dx = nose.x - eyeMidX;
  const dy = nose.y - eyeMidY;
  let pose = 'center';
  if (dy > 12) pose = 'down';
  else if (dx > 12) pose = 'right';
  else if (dx < -12) pose = 'left';
  return {{ pose, yaw: dx, pitch: dy, roll: 0 }};
}}

function computeEngagement(faceData, inactivity) {{
  let score = 100;
  if (!faceData.present) score -= 45;
  if (!faceData.gaze) score -= 20;
  if (faceData.headPose === 'down') score -= 15;
  else if (faceData.headPose === 'left' || faceData.headPose === 'right') score -= 10;
  if (inactivity > 120) score -= 30;
  else if (inactivity > 60) score -= 15;
  score = Math.max(0, Math.min(100, score));
  return score;
}}

function computeAffectState(score, ear, mouthRatio, inactivity) {{
  if (inactivity > 120) return 'distracted';
  if (score < 30) return 'disengaged';
  if (score < 50 && ear < 0.2) return 'fatigued';
  if (score >= 40 && score < 70 && mouthRatio > 0.15) return 'confused';
  if (score >= 70) return 'focused';
  if (score >= 50) return 'focused';
  return 'disengaged';
}}

async function collectSample() {{
  const now = Date.now();
  if (now - lastEngagementSent < 20000) return;
  lastEngagementSent = now;

  const inactivity = Math.floor((now - lastInteractionTime) / 1000);
  let facePresent = false, gazeCentered = false, headPose = 'center';
  let ear = null, mouthRatio = null, yaw = null, pitch = null, roll = null;
  let affectState = null;

  if (await loadTFJS() && await ensureStream() && await loadDetector()) {{
    try {{
      const faces = await faceDetector.estimateFaces(videoEl);
      if (faces && faces.length) {{
        facePresent = true;
        const f = faces[0];
        const hp = estimateHeadPose(f);
        headPose = hp.pose; yaw = hp.yaw; pitch = hp.pitch; roll = hp.roll;
        if (f.keypoints) {{
          const leftEye = f.keypoints.filter(k => k.name && k.name.includes('leftEye'));
          const rightEye = f.keypoints.filter(k => k.name && k.name.includes('rightEye'));
          if (leftEye.length >= 6 && rightEye.length >= 6) {{
            ear = (computeEAR(leftEye) + computeEAR(rightEye)) / 2;
          }}
        }}
        gazeCentered = headPose === 'center';
        mouthRatio = computeMouthRatio(f);
      }}
    }} catch {{}}
  }}

  const score = computeEngagement({{ present: facePresent, gaze: gazeCentered, headPose }}, inactivity);
  affectState = computeAffectState(score, ear || 0.35, mouthRatio || 0, inactivity);

  // Notify live dashboard on affect state change
  if (affectState !== lastAffectState && window.__liveWS && window.__liveWS.readyState === WebSocket.OPEN) {{
    window.__liveWS.send(JSON.stringify({{
      type: 'AFFECT_CHANGE',
      username: window.__cs_username || 'unknown',
      affect_state: affectState,
    }}));
  }}
  lastAffectState = affectState;

  // Adaptive UI triggers
  const simplifyEl = document.getElementById('adaptiveSimplify');
  const advancedEl = document.getElementById('adaptiveAdvanced');
  const promptEl = document.getElementById('attentionPrompt');
  if (simplifyEl) simplifyEl.style.display = score < 40 ? 'block' : 'none';
  if (advancedEl) advancedEl.style.display = score > 80 ? 'block' : 'none';
  if (promptEl) promptEl.style.display = inactivity > 120 ? 'block' : 'none';

  fetch(API + '/' + course + '/' + week + '/engagement', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{
      attemptSessionId, username: window.__cs_username || 'unknown',
      course, week, timestamp: new Date().toISOString(),
      facePresent, gazeCentered, headPose,
      inactivitySeconds: inactivity, engagementScore: score,
      focusState: score >= 70 ? 'High' : score >= 40 ? 'Medium' : 'Low',
      clickCount: pageClicks, typingCount: keypressCount,
      eyeAspectRatio: ear, mouthOpenRatio: mouthRatio,
      smileScore: null, headYaw: yaw, headPitch: pitch, headRoll: roll,
      affectState
    }})
  }}).catch(() => {{}});
}}

// Inject username from server-side if available
const unameScript = document.querySelector('script[data-username]');
if (unameScript) window.__cs_username = unameScript.dataset.username;

engagementTimer = setInterval(collectSample, 20000);
}})();
</script>
'''


def generate_problems_template(title: str, problems: list) -> str:
    questions_content = ""
    for p in problems:
        questions_content += generate_question_catsoop(p) + "\n"

    if not questions_content:
        questions_content = '''<p>No practice problems yet.</p>
'''
    return f'''<python>
cs_content_header = "{title}"
</python>

{questions_content}
'''
