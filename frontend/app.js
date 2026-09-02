const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const session='hb-'+Math.random().toString(36).slice(2)+Date.now();
const messages=$('#messages');
const langNames={en:'English',hi:'Hindi',pa:'Punjabi',bn:'Bengali',ta:'Tamil',te:'Telugu',mr:'Marathi',gu:'Gujarati'};

function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

function md(s){
  return esc(s)
    .replace(/^### (.+)$/gm,'<h4>$1</h4>')
    .replace(/^## (.+)$/gm,'<h3>$1</h3>')
    .replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')
    .replace(/_(.*?)_/g,'<em>$1</em>')
    .replace(/^- (.+)$/gm,'<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g,'<ul>$&</ul>')
    .replace(/^\d+\. (.+)$/gm,'<li>$1</li>')
    .replace(/\n{2,}/g,'</p><p>')
    .replace(/\n/g,'<br>');
}

function add(role,text,meta=''){
  const d=document.createElement('div');
  d.className='msg '+role;
  d.innerHTML=`<div class="bubble">${md(text)}</div>${meta?`<div class="meta">${esc(meta)}</div>`:''}`;
  messages.appendChild(d);
  messages.scrollTop=messages.scrollHeight;
}

function welcome(){
  add('ai','### Welcome to HealthBridge\nAsk me about prevention, vaccination, pregnancy/child health, mental wellbeing, medicines, symptoms, or finding care.\n\n- Use **📋 Health Assessment** for a full guided intake\n- Use the **Symptom Check** panel for a quick urgency check\n- Ask any health question below','Safety-first public health guide');
}

async function send(text){
  if(!text.trim())return;
  add('user',text);
  $('#input').value='';
  const lang=$('#lang').value;
  add('ai','Checking safety → finding relevant evidence → composing a simple answer…','9-agent pipeline');
  const pending=messages.lastElementChild;
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,language:lang,session_id:session})});
    const d=await r.json();
    pending.remove();
    add('ai',d.answer,`${d.provider} · ${d.intent} · ${langNames[lang]||lang}`);
    updatePipeline(d);
  }catch(e){
    pending.remove();
    add('ai','The server could not be reached. Make sure FastAPI is running on port 8000.','Connection error');
  }
}

function updatePipeline(d){
  $('#mode').textContent=d.provider==='ibm-bob'?'IBM Bob connected':d.provider==='ibm-watsonx'?'IBM watsonx connected':d.provider==='safe-fallback'?'Safe fallback':'Local safe mode';
  $('#riskBadge').textContent=d.urgency.toUpperCase();
  $('#riskBadge').className=d.urgency;
  $('#nextStep').textContent=d.safety?.instruction||'Use a qualified professional when needed.';
  const pct={routine:18,moderate:52,high:78,emergency:100}[d.urgency]||18;
  $('#riskFill').style.width=pct+'%';
  $('#riskFill').className='risk-fill '+d.urgency;
  $('#trace').innerHTML=d.agent_trace.map(x=>`<div><i></i><span>${esc(x.agent)}<small>${esc(x.detail)}</small></span><b>${esc(x.result)}</b></div>`).join('');
  $('#sources').innerHTML=d.sources.length?d.sources.map(x=>`<a href="${x.url}" target="_blank" rel="noopener">${esc(x.title)} ↗</a>`).join(''):'<span>No matched source notes.</span>';
}

$('#chatForm').addEventListener('submit',e=>{e.preventDefault();send($('#input').value)});
$$('[data-q]').forEach(b=>b.onclick=()=>send(b.dataset.q));
$('#clearBtn').onclick=()=>{messages.innerHTML='';welcome();};
$('#sourcesBtn').onclick=()=>{$('#sources').classList.toggle('expanded');$('#sourcesBtn').textContent=$('#sources').classList.contains('expanded')?'Collapse':'Expand';};
$('#startCheck').onclick=()=>document.querySelector('.feature-section').scrollIntoView({behavior:'smooth'});

// ---- Prevention plans ----
$$('[data-goal]').forEach(b=>b.onclick=()=>plan(b.dataset.goal));
async function plan(goal){
  const r=await fetch('/api/prevention-plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({goal,language:$('#lang').value,age_group:$('#ageGroup').value})});
  const d=await r.json();
  $('#plan').classList.remove('hidden');
  $('#plan').innerHTML=`<div class="plan-head"><div><b>${esc(d.goal)}</b><span>${esc(d.age_group)}</span></div><button id="savePlan">Save locally</button></div><ol>${d.steps.map(x=>`<li>${esc(x)}</li>`).join('')}</ol><p>${esc(d.note)}</p>`;
  $('#savePlan').onclick=()=>{localStorage.setItem('healthbridge-plan',JSON.stringify(d));$('#savePlan').textContent='✓ Saved';};
}

// ---- Triage ----
$('#triageSeverity').oninput=e=>$('#severityValue').textContent=e.target.value+'/5';
$('#runTriage').onclick=async()=>{
  const flags=$$('.checks input:checked').map(x=>x.value);
  const body={symptoms:$('#triageSymptoms').value,duration:$('#triageDuration').value,severity:+$('#triageSeverity').value,age_group:$('#ageGroup').value,pregnancy:$('#ageGroup').value==='pregnant',red_flags:flags,language:$('#lang').value};
  if(!body.symptoms.trim())return $('#triageResult').innerHTML='<h3>Add your symptoms</h3><p>Describe what you are experiencing first.</p>';
  const r=await fetch('/api/triage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const d=await r.json();
  const emergency=d.urgency==='emergency';
  $('#triageResult').innerHTML=`<div class="result-level ${d.urgency}">${emergency?'🚨':'🧭'} ${d.urgency.toUpperCase()}</div><h3>${esc(d.action)}</h3><ul>${d.reasons.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><p>${esc(d.disclaimer)}</p>${emergency?'<a class="call112" href="tel:112">☎ Call 112</a>':''}`;
};

// ---- Care navigator ----
$('#findCare').onclick=async()=>{
  const city=$('#city').value.trim(),state=$('#state').value.trim(),service=$('#service').value;
  const r=await fetch(`/api/resources?city=${encodeURIComponent(city)}&state=${encodeURIComponent(state)}&service=${encodeURIComponent(service)}`);
  const d=await r.json();
  renderResources(d);
};
function renderResources(d){
  $('#resourceCards').innerHTML=d.map(x=>`<article><span>${esc(x.type)}</span><h3>${esc(x.name)}</h3><p>${esc(x.description)}</p><a href="${x.url}" target="_blank" rel="noopener">${esc(x.action||'Open pathway')} ↗</a></article>`).join('');
}

// ---- Topics grid ----
async function loadTopics(){
  const t=await fetch('/api/topics').then(r=>r.json());
  $('#topicGrid').innerHTML=t.map(x=>`<button class="topic-card${x.id==='assessment'?' topic-card--featured':''}" data-id="${esc(x.id)}" data-prompt="${esc(x.prompt)}"><span>${x.icon}</span><div><b>${esc(x.title)}</b><small>${esc(x.desc)}</small></div><i>→</i></button>`).join('');
  $$('.topic-card').forEach(b=>b.onclick=()=>{
    if(b.dataset.prompt==='__assessment__'||b.dataset.id==='assessment'){openAssessment();return;}
    if(b.dataset.prompt.includes('symptoms'))document.querySelector('.feature-section').scrollIntoView({behavior:'smooth'});
    else send(b.dataset.prompt);
  });
}

// ---- Knowledge library ----
let knowledge=[];
async function loadKnowledge(){knowledge=await fetch('/api/knowledge').then(r=>r.json());renderKnowledge(knowledge);}
function renderKnowledge(list){$('#knowledgeGrid').innerHTML=list.map(x=>`<article><span class="kb-cat">${esc(x.category)}</span><h3>${esc(x.title)}</h3><p>${esc(x.summary)}</p><a href="${x.url}" target="_blank" rel="noopener">Trusted source ↗</a></article>`).join('');}
$('#knowledgeSearch').oninput=e=>{const q=e.target.value.toLowerCase();renderKnowledge(knowledge.filter(x=>(x.title+' '+x.summary+' '+x.category).toLowerCase().includes(q)));};

// ---- Theme ----
$('#themeBtn').onclick=()=>{document.body.classList.toggle('dark');localStorage.setItem('hb-theme',document.body.classList.contains('dark')?'dark':'light');};
if(localStorage.getItem('hb-theme')==='dark')document.body.classList.add('dark');

// ---- Voice ----
const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
if(!SpeechRecognition){$('#voiceBtn').title='Voice input is not supported in this browser';}
$('#voiceBtn').onclick=()=>{
  if(!SpeechRecognition){add('ai','Voice input is not supported in this browser. Try Chrome or Edge.');return;}
  const rec=new SpeechRecognition();
  const l=$('#lang').value;
  rec.lang=l==='hi'?'hi-IN':l==='pa'?'pa-IN':l==='bn'?'bn-BD':l==='ta'?'ta-IN':l==='te'?'te-IN':l==='mr'?'mr-IN':l==='gu'?'gu-IN':'en-IN';
  rec.interimResults=false;
  rec.onstart=()=>$('#voiceBtn').textContent='🔴 Listening…';
  rec.onresult=e=>{$('#input').value=e.results[0][0].transcript;$('#voiceBtn').textContent='🎙 Voice question';$('#input').focus();};
  rec.onerror=()=>$('#voiceBtn').textContent='🎙 Voice question';
  rec.onend=()=>$('#voiceBtn').textContent='🎙 Voice question';
  rec.start();
};

// ============================================================
// ASSESSMENT WIZARD
// ============================================================
const WIZARD_STEPS=['Symptom Intake','Context & Severity','Red-Flag Check','Your Care Plan'];
let wiz={step:0,data:{}};

function openAssessment(){
  wiz={step:0,data:{language:$('#lang').value,session_id:session}};
  renderWizard();
  $('#wizardOverlay').classList.add('open');
  document.body.style.overflow='hidden';
}
function closeAssessment(){
  $('#wizardOverlay').classList.remove('open');
  document.body.style.overflow='';
}

$('#wizardOverlay').addEventListener('click',e=>{if(e.target===$('#wizardOverlay'))closeAssessment();});
$('#wizardClose').onclick=closeAssessment;
$('#openAssessmentBtn').onclick=openAssessment;

function renderWizard(){
  // Progress bar
  const pct=Math.round((wiz.step/(WIZARD_STEPS.length-1))*100);
  $('#wizProgress').style.width=pct+'%';
  $('#wizStepLabel').textContent=`Step ${wiz.step+1} of ${WIZARD_STEPS.length} — ${WIZARD_STEPS[wiz.step]}`;

  // Step indicators
  $('#wizSteps').innerHTML=WIZARD_STEPS.map((s,i)=>`<div class="wiz-step-dot ${i<wiz.step?'done':i===wiz.step?'active':''}"><span>${i+1}</span><small>${s}</small></div>`).join('');

  const body=$('#wizBody');
  body.innerHTML='';

  if(wiz.step===0){
    body.innerHTML=`
      <div class="wiz-field">
        <label for="wSym">What symptoms or health concerns do you have?</label>
        <textarea id="wSym" rows="3" placeholder="Describe what you are experiencing, e.g. fever, cough, headache for 2 days…">${esc(wiz.data.symptoms||'')}</textarea>
      </div>
      <div class="wiz-field">
        <label for="wSys">Which body system does it mainly affect?</label>
        <select id="wSys">
          <option value="general" ${wiz.data.body_system==='general'?'selected':''}>General / Not sure</option>
          <option value="respiratory" ${wiz.data.body_system==='respiratory'?'selected':''}>Respiratory (breathing, cough, throat)</option>
          <option value="cardiac" ${wiz.data.body_system==='cardiac'?'selected':''}>Cardiac (chest, heart)</option>
          <option value="digestive" ${wiz.data.body_system==='digestive'?'selected':''}>Digestive (stomach, bowel)</option>
          <option value="neurological" ${wiz.data.body_system==='neurological'?'selected':''}>Neurological (head, brain, vision)</option>
          <option value="musculoskeletal" ${wiz.data.body_system==='musculoskeletal'?'selected':''}>Musculoskeletal (joints, muscles, bones)</option>
          <option value="skin" ${wiz.data.body_system==='skin'?'selected':''}>Skin</option>
          <option value="mental" ${wiz.data.body_system==='mental'?'selected':''}>Mental / Emotional wellbeing</option>
        </select>
      </div>
      <div class="wiz-nav">
        <span></span>
        <button class="primary" id="wizNext0">Next →</button>
      </div>`;
    $('#wizNext0').onclick=()=>{
      const sym=$('#wSym').value.trim();
      if(!sym){$('#wSym').focus();$('#wSym').style.borderColor='var(--red)';return;}
      wiz.data.symptoms=sym;
      wiz.data.body_system=$('#wSys').value;
      wiz.step=1;renderWizard();
    };

  }else if(wiz.step===1){
    const sev=wiz.data.severity||3;
    body.innerHTML=`
      <div class="wiz-field">
        <label for="wDur">How long have you had these symptoms?</label>
        <select id="wDur">
          <option value="today" ${wiz.data.duration==='today'?'selected':''}>Today</option>
          <option value="1-2 days" ${wiz.data.duration==='1-2 days'?'selected':''}>1–2 days</option>
          <option value="3-7 days" ${wiz.data.duration==='3-7 days'?'selected':''}>3–7 days</option>
          <option value="more than 1 week" ${wiz.data.duration==='more than 1 week'?'selected':''}>More than 1 week</option>
        </select>
      </div>
      <div class="wiz-field">
        <label>How severe are the symptoms? <b id="wSevVal">${sev}/5</b></label>
        <input id="wSev" type="range" min="1" max="5" value="${sev}" class="wiz-slider">
        <div class="sev-labels"><span>Mild</span><span>Moderate</span><span>Severe</span></div>
      </div>
      <div class="wiz-field">
        <label for="wAge">Age group</label>
        <select id="wAge">
          <option value="adult" ${wiz.data.age_group==='adult'?'selected':''}>Adult (18–60)</option>
          <option value="child" ${wiz.data.age_group==='child'?'selected':''}>Child (under 18)</option>
          <option value="older adult" ${wiz.data.age_group==='older adult'?'selected':''}>Older adult (60+)</option>
          <option value="pregnant" ${wiz.data.age_group==='pregnant'?'selected':''}>Pregnant</option>
        </select>
      </div>
      <div class="wiz-field wiz-location">
        <label>Location (optional — for local care resources)</label>
        <div class="loc-row">
          <input id="wCity" placeholder="City" value="${esc(wiz.data.city||'')}">
          <input id="wState" placeholder="State" value="${esc(wiz.data.state||'')}">
        </div>
      </div>
      <div class="wiz-nav">
        <button class="secondary" id="wizBack1">← Back</button>
        <button class="primary" id="wizNext1">Next →</button>
      </div>`;
    $('#wSev').oninput=e=>$('#wSevVal').textContent=e.target.value+'/5';
    $('#wizBack1').onclick=()=>{wiz.step=0;renderWizard();};
    $('#wizNext1').onclick=()=>{
      wiz.data.duration=$('#wDur').value;
      wiz.data.severity=+$('#wSev').value;
      wiz.data.age_group=$('#wAge').value;
      wiz.data.city=$('#wCity').value.trim();
      wiz.data.state=$('#wState').value.trim();
      wiz.step=2;renderWizard();
    };

  }else if(wiz.step===2){
    const rf=wiz.data.red_flags||[];
    const FLAGS=[
      {v:'breathing difficulty',l:'Severe breathing difficulty'},
      {v:'unconsciousness',l:'Unconscious / not responding'},
      {v:'severe chest pain',l:'Severe chest pain'},
      {v:'heavy bleeding',l:'Heavy bleeding'},
      {v:'seizure',l:'Seizure or convulsion'},
      {v:'stroke signs',l:'Stroke signs (face drooping, arm weakness, slurred speech)'},
      {v:'self-harm',l:'Thoughts of self-harm or suicide'}
    ];
    body.innerHTML=`
      <p class="wiz-intro">Check any warning signs that apply. If you select one, you will receive emergency guidance immediately.</p>
      <div class="wiz-flags">
        ${FLAGS.map(f=>`<label class="flag-check ${rf.includes(f.v)?'checked':''}"><input type="checkbox" value="${esc(f.v)}" ${rf.includes(f.v)?'checked':''}><span>${esc(f.l)}</span></label>`).join('')}
      </div>
      <div class="wiz-nav">
        <button class="secondary" id="wizBack2">← Back</button>
        <button class="primary" id="wizNext2" id="wizNext2">Run Assessment →</button>
      </div>`;
    $$('.flag-check input').forEach(cb=>{
      cb.onchange=()=>cb.closest('.flag-check').classList.toggle('checked',cb.checked);
    });
    $('#wizBack2').onclick=()=>{wiz.step=1;renderWizard();};
    $('#wizNext2').onclick=async()=>{
      wiz.data.red_flags=$$('.flag-check input:checked').map(x=>x.value);
      wiz.data.language=$('#lang').value;
      await runAssessment();
    };

  }else if(wiz.step===3){
    renderAssessmentResult();
  }
}

async function runAssessment(){
  const body=$('#wizBody');
  body.innerHTML='<div class="wiz-loading"><div class="wiz-spinner"></div><p>Running safety check → building care plan…</p></div>';
  try{
    const r=await fetch('/api/assessment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(wiz.data)});
    if(!r.ok)throw new Error('Server error '+r.status);
    wiz.result=await r.json();
    wiz.step=3;
    renderWizard();
  }catch(e){
    body.innerHTML=`<div class="wiz-error"><p>⚠️ Could not complete the assessment. Please check your connection and try again.</p><button class="secondary" onclick="wiz.step=2;renderWizard()">← Back</button></div>`;
  }
}

function renderAssessmentResult(){
  const d=wiz.result;
  const body=$('#wizBody');
  const urgencyIcon={emergency:'🚨',high:'⚠️',moderate:'🔶',routine:'✅'}[d.urgency]||'🧭';
  const urgencyColor={emergency:'emergency',high:'high',moderate:'moderate',routine:'routine'}[d.urgency];

  const summaryHtml=md(d.summary||'');
  const tipsHtml=d.tips?d.tips.map(t=>`<li>${esc(t)}</li>`).join(''):'';
  const planHtml=d.prevention?.steps?d.prevention.steps.map(s=>`<li>${esc(s)}</li>`).join(''):'';
  const sourcesHtml=d.sources?.length?d.sources.map(s=>`<a href="${s.url}" target="_blank" rel="noopener">${esc(s.title)} ↗</a>`).join(''):'';

  body.innerHTML=`
    <div class="assess-result">
      <div class="assess-urgency ${urgencyColor}">
        <span>${urgencyIcon} ${d.urgency.toUpperCase()}</span>
        <b>${esc(d.triage?.action||'')}</b>
      </div>

      ${d.urgency==='emergency'?`<a class="call112-big" href="tel:112">☎ Call 112 Now</a>`:''}

      <div class="assess-summary">${summaryHtml}</div>

      ${tipsHtml?`<div class="assess-block">
        <h5>🩺 Body-system tips (${esc(d.body_system)})</h5>
        <ul>${tipsHtml}</ul>
      </div>`:''}

      ${planHtml?`<div class="assess-block">
        <h5>🌱 Prevention checklist — ${esc(d.prevention.goal)}</h5>
        <ol>${planHtml}</ol>
        <p class="assess-note">${esc(d.prevention.note||'')}</p>
      </div>`:''}

      ${d.resources?.length?`<div class="assess-block">
        <h5>📍 Care resources</h5>
        <div class="assess-resources">
          ${d.resources.slice(0,4).map(r=>`<a class="res-pill" href="${r.url}" target="_blank" rel="noopener"><b>${esc(r.type)}</b>${esc(r.name)} ↗</a>`).join('')}
        </div>
      </div>`:''}

      ${sourcesHtml?`<div class="assess-block assess-sources">
        <h5>📚 Trusted sources</h5>
        ${sourcesHtml}
      </div>`:''}

      <p class="assess-disclaimer">${esc(d.disclaimer)}</p>

      <div class="wiz-nav">
        <button class="secondary" id="wizRestart">Start new assessment</button>
        <button class="primary" id="wizSend">Send to chat</button>
      </div>
    </div>`;

  $('#wizRestart').onclick=()=>{wiz={step:0,data:{language:$('#lang').value,session_id:session}};renderWizard();};
  $('#wizSend').onclick=()=>{
    closeAssessment();
    setTimeout(()=>{
      send(`I just completed a health assessment. My symptoms: ${wiz.data.symptoms}. Urgency: ${d.urgency}. Body system: ${d.body_system}. Can you give me more information?`);
    },300);
  };
}

// ---- Boot ----
async function boot(){
  try{
    const h=await fetch('/api/health').then(r=>r.json());
    $('#mode').textContent=h.provider==='bob'?'IBM Bob ready':h.provider==='watsonx'?'IBM watsonx ready':'Local safe mode';
  }catch(e){$('#mode').textContent='Offline';}
  welcome();
  loadTopics();
  loadKnowledge();
  $('#findCare').click();
  if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
}
boot();
