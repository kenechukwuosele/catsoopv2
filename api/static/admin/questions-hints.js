// Problem builder, question CRUD, hint CRUD, AI hint generation

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
