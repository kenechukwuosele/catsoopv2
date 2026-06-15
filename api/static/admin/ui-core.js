const Q_TYPES = {
  multiplechoice: {label:'Multiple Choice', badge:'q-type-mc'},
  truefalse: {label:'True / False', badge:'q-type-tf'},
  shortanswer: {label:'Short Answer', badge:'q-type-sa'},
  numerical: {label:'Numerical', badge:'q-type-num'},
  symbolic: {label:'Symbolic Math', badge:'q-type-sym'},
  pythoncode: {label:'Python Code', badge:'q-type-py'}
};

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
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
