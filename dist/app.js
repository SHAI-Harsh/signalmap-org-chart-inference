'use strict';
const $=s=>document.querySelector(s);
const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=n=>`${(n*100).toFixed(1)}%`;
const confidencePct=n=>n<1&&n>=0.9995?'99.9%':pct(n);
const nfmt=n=>Number(n).toLocaleString('en-US');
const state={companies:[],company:null,people:[],evaluation:null,selected:null,view:'explorer',expanded:new Map(),showUnresolved:false};
const initials=name=>(name||'?').split(/\s+/).slice(0,2).map(s=>s[0]||'').join('').toUpperCase();
const avatar=(p,extra='')=>`<span class="avatar c${p.id.charCodeAt(p.id.length-1)%4} ${extra}">${escapeHTML(initials(p.name))}</span>`;
const personTitle=p=>p.title||'Title unavailable';
function setView(view){
  state.view=view;
  $('.nav-item.active')?.classList.remove('active');document.querySelector(`[data-view="${view}"]`)?.classList.add('active');
  $('#breadcrumb').textContent={explorer:'Org explorer',people:'People directory',evaluation:'Evaluation',method:'Methodology'}[view];
  $('#workspace-view').classList.toggle('hidden',!['explorer','people'].includes(view));
  $('#explorer-panel').classList.toggle('hidden',view!=='explorer');$('#people-panel').classList.toggle('hidden',view!=='people');
  $('#evaluation-view').classList.toggle('hidden',view!=='evaluation');$('#method-view').classList.toggle('hidden',view!=='method');
  if(view==='people')renderDirectory();if(view==='evaluation')renderEvaluation();if(view==='method')renderMethod();
}
function companyOptions(query=''){
  const list=state.companies.filter(c=>`${c.name} ${c.industry}`.toLowerCase().includes(query.toLowerCase()));
  $('#company-options').innerHTML=list.length?list.map(c=>`<button role="option" aria-selected="${c.id===state.company?.id}" class="company-option ${c.id===state.company?.id?'selected':''}" data-company="${escapeHTML(c.id)}">${escapeHTML(c.name)}<small>${escapeHTML(c.industry)} · ${nfmt(c.employee_count)} people</small></button>`).join(''):'<div class="empty">No companies found.</div>';
}
async function selectCompany(id){
  $('#company-popover').classList.add('hidden');$('#company-picker').setAttribute('aria-expanded','false');
  $('#company-name').textContent='Loading…';$('#chart').innerHTML='<div class="empty">Loading the chart…</div>';
  try{
    const response=await fetch(`./data/companies/${encodeURIComponent(id)}.json`);if(!response.ok)throw new Error('Could not load company data');
    const data=await response.json();state.company=data.company;state.people=data.people;state.selected=null;state.expanded.clear();state.showUnresolved=false;
    $('#people-search').value='';$('#directory-search').value='';$('#confidence-filter').value='0.85';
    $('#company-name').textContent=state.company.name;$('#company-avatar').textContent=state.company.name[0];
    $('#company-meta').innerHTML=`${escapeHTML(state.company.industry)} <span class="dot-sep">•</span> ${escapeHTML(state.company.location)} <span class="dot-sep">•</span> Synthetic company`;
    renderStats();renderChart();renderDetail();renderDirectory();companyOptions($('#company-search').value);
  }catch(e){$('#chart').innerHTML=`<div class="error">${escapeHTML(e.message)}. Please try another company.</div>`;}
}
function renderStats(){
  const threshold=Number($('#confidence-filter').value);
  const linked=state.people.filter(p=>p.manager_id&&p.confidence>=threshold).length;
  const unresolved=state.people.filter(p=>(!p.manager_id||p.confidence<threshold)&&p.state!=='root').length;
  const test=state.evaluation?.test;
  const cards=[['People in dataset',nfmt(state.people.length),'observed','◫'],['Inferred lines',nfmt(linked),`at ≥${Math.round(threshold*100)}%`,'⌁'],['Manager unknown',nfmt(unresolved),'left unresolved','◇'],['Held-out precision',test?pct(test.precision):'—','synthetic test','▥']];
  $('#stats').innerHTML=cards.map(([label,value,note,icon])=>`<div class="stat"><div class="stat-label">${label}<span class="stat-icon">${icon}</span></div><div class="stat-value">${value}<span class="stat-note">${note}</span></div></div>`).join('');
}
function graph(){
  const threshold=Number($('#confidence-filter').value);const byId=new Map(state.people.map(p=>[p.id,p]));const children=new Map();
  const parent=new Map();
  for(const p of state.people){if(p.manager_id && p.confidence>=threshold && byId.has(p.manager_id)){parent.set(p.id,p.manager_id);if(!children.has(p.manager_id))children.set(p.manager_id,[]);children.get(p.manager_id).push(p);}}
  const sorter=(a,b)=>a.name.localeCompare(b.name)||a.id.localeCompare(b.id);
  for(const a of children.values())a.sort(sorter);
  const roots=state.people.filter(p=>!parent.has(p.id));roots.sort((a,b)=>(b.state==='root')-(a.state==='root')||((children.get(b.id)?.length||0)-(children.get(a.id)?.length||0))||sorter(a,b));
  return {byId,children,parent,roots};
}
function renderChart(){
  const g=graph();const query=$('#people-search').value.trim().toLowerCase();const matches=new Set();
  for(const p of state.people){if(!query||`${p.name} ${p.title} ${p.function}`.toLowerCase().includes(query)){let id=p.id;while(id&&!matches.has(id)){matches.add(id);id=g.parent.get(id);}}}
  const matchCount=query?state.people.filter(p=>`${p.name} ${p.title} ${p.function}`.toLowerCase().includes(query)).length:state.people.length;
  $('#chart-count').textContent=`${nfmt(matchCount)} ${query?'matches':'people'}`;
  function node(p,depth){
    if(!matches.has(p.id))return '';
    const kids=(g.children.get(p.id)||[]).filter(x=>matches.has(x.id));const hasKids=kids.length>0;
    const isOpen=query?true:(state.expanded.has(p.id)?state.expanded.get(p.id):depth<2);
    const isRoot=!g.parent.has(p.id);let pill='';
    if(!isRoot)pill=`<span class="confidence">${confidencePct(p.confidence)}</span>`;
    else if(p.state!=='root')pill='<span class="unknown-badge">Manager unknown</span>';
    const btn=hasKids?`<button class="toggle" data-toggle="${escapeHTML(p.id)}" aria-expanded="${isOpen}" aria-label="${isOpen?'Collapse':'Expand'} ${escapeHTML(p.name)} reports">${isOpen?'−':'+'}</button>`:'<span class="toggle placeholder"></span>';
    return `<li class="branch"><div class="branch-row">${btn}<button class="person-button ${state.selected===p.id?'selected':''}" data-person="${escapeHTML(p.id)}">${avatar(p)}<span class="person-text"><span class="person-name">${escapeHTML(p.name)}</span><span class="person-title">${escapeHTML(personTitle(p))}</span></span>${pill}</button></div>${hasKids&&isOpen?`<ul>${kids.map(x=>node(x,depth+1)).join('')}</ul>`:''}</li>`;
  }
  const connected=g.roots.filter(p=>g.children.has(p.id)&&matches.has(p.id));const lone=g.roots.filter(p=>!g.children.has(p.id)&&matches.has(p.id));
  let html='';
  if(connected.length)html=`<div class="forest-label">CONNECTED REPORTING LINES <span></span></div><ul class="branch-list">${connected.map(p=>node(p,0)).join('')}</ul>`;
  if(lone.length){const show=state.showUnresolved||!!query;html+=`<button class="unresolved-toggle" id="show-unresolved" aria-expanded="${show}">People with no visible connection (${lone.length}) <span>${show?'−':'+'}</span></button>${show?`<ul class="branch-list">${lone.map(p=>node(p,0)).join('')}</ul>`:''}`;}
  $('#chart').innerHTML=html||'<div class="empty">No people match your search.</div>';
  renderDetail();
}
function renderDetail(){
  const p=state.people.find(p=>p.id===state.selected);if(!p){$('#person-detail').innerHTML='<div class="detail-empty"><div class="detail-spark">✳</div><strong>Get the full picture</strong><p>Select a person to see the evidence behind their reporting line.</p></div>';return;}
  const g=graph(),manager=g.byId.get(g.parent.get(p.id));const reports=g.children.get(p.id)||[];let status='';
  if(manager){status=`<button class="detail-person" data-person="${escapeHTML(manager.id)}">${escapeHTML(manager.name)} ↗<br><span style="font-weight:400;color:#75927d">${escapeHTML(personTitle(manager))}</span></button><p>${escapeHTML(p.reason)}.</p><div class="detail-confidence">${confidencePct(p.confidence)} <small>calibrated confidence</small></div>`;}
  else if(p.manager_id)status=`<span class="detail-tag">Below selected filter</span><p>A line exists at ${confidencePct(p.confidence)}, but is hidden by your confidence filter.</p>`;
  else status=`<span class="detail-tag">${p.state==='root'?'Top executive':'No manager inferred'}</span><p>${escapeHTML(p.reason)}</p>`;
  let path=[];let id=g.parent.get(p.id);const seen=new Set([p.id]);while(id&&!seen.has(id)){seen.add(id);let m=g.byId.get(id);if(!m)break;path.push(m);id=g.parent.get(id)}
  $('#person-detail').innerHTML=`<div class="detail-label">PERSON PROFILE</div><div class="detail-top">${avatar(p)}<h3>${escapeHTML(p.name)}</h3><p>${escapeHTML(personTitle(p))}</p></div><div class="detail-block"><h4>INFERRED MANAGER</h4>${status}</div><div class="detail-block"><h4>REPORTING CONTEXT</h4><p>${reports.length} inferred direct ${reports.length===1?'report':'reports'} at this filter.</p>${path.length?`<p>Up the chain: ${path.map(x=>escapeHTML(x.name)).join(' → ')}</p>`:''}<p>Function: ${escapeHTML(p.function||'Unknown')}<br>Location: ${escapeHTML(p.location||'Not provided')}</p></div><div class="detail-block"><p>Confidence is calibrated on held-out synthetic companies; it is not a guarantee for real organizations.</p></div>`;
}
function renderDirectory(){
 if(!state.company)return;const q=$('#directory-search').value.trim().toLowerCase();const rows=state.people.filter(p=>`${p.name} ${p.title} ${p.function}`.toLowerCase().includes(q));const byId=new Map(state.people.map(p=>[p.id,p]));
 $('#directory-count').textContent=nfmt(rows.length);$('#directory').innerHTML=`<div class="directory-row directory-head"><span>NAME</span><span>TITLE</span><span>FUNCTION</span><span>INFERRED MANAGER</span></div>${rows.map(p=>`<div class="directory-row"><button data-person="${escapeHTML(p.id)}">${escapeHTML(p.name)}</button><span>${escapeHTML(personTitle(p))}</span><span class="subtle">${escapeHTML(p.function)}</span><span class="subtle">${escapeHTML(byId.get(p.manager_id)?.name||'Unknown')}</span></div>`).join('')||'<div class="empty">No people match your search.</div>'}`;
}
function renderEvaluation(){
 const r=state.evaluation;if(!r)return;const m=r.test,b=r.baseline;
 const thresholds=['0.5','0.8','0.85','0.9','0.95'];
 $('#evaluation-view').innerHTML=`<div class="page-intro"><div><div class="eyebrow"><span></span> MEASURED, NOT ASSUMED</div><h1>Honest about the gaps<span class="period">.</span></h1><p>Results on ${r.dataset.test_companies} companies held out from confidence calibration.</p></div></div><div class="info-grid"><div class="info-card"><div class="micro">EDGE PRECISION</div><div class="info-big">${pct(m.precision)}</div><p>${nfmt(m.correct)} correct of ${nfmt(m.emitted)} emitted lines.</p></div><div class="info-card"><div class="micro">COVERAGE</div><div class="info-big">${pct(m.coverage)}</div><p>Share of employees with a true manager who received a prediction.</p></div><div class="info-card"><div class="micro">EDGE RECALL</div><div class="info-big">${pct(m.recall)}</div><p>Correct predictions divided by all employees with a true manager.</p></div></div><div class="info-section"><h2>The precision–coverage tradeoff</h2><p>The chart starts at 85% calibrated confidence. Increasing the threshold shows fewer lines. Coverage includes employees whose true managers are absent from the roster.</p><table class="metrics-table"><thead><tr><th>MIN. CONFIDENCE</th><th>PRECISION</th><th>COVERAGE</th><th>CORRECT / EMITTED</th></tr></thead><tbody>${thresholds.map(t=>{let x=r.threshold_curve[t];return `<tr><td class="${t==='0.85'?'highlight':''}">${Math.round(Number(t)*100)}% ${t==='0.85'?'· default':''}</td><td>${pct(x.precision)}</td><td>${pct(x.coverage)}</td><td>${nfmt(x.correct)} / ${nfmt(x.emitted)}</td></tr>`}).join('')}</tbody></table></div><div class="info-section"><h2>Against a simple baseline</h2><p>The baseline chooses the nearest higher seniority in the same inferred function and breaks ties by ID; it does not abstain for competing managers.</p><table class="metrics-table"><thead><tr><th>METHOD</th><th>PRECISION</th><th>COVERAGE</th><th>EDGE RECALL</th></tr></thead><tbody><tr><td class="highlight">Conservative inference</td><td>${pct(m.precision)}</td><td>${pct(m.coverage)}</td><td>${pct(m.recall)}</td></tr><tr><td>Nearest-seniority baseline</td><td>${pct(b.precision)}</td><td>${pct(b.coverage)}</td><td>${pct(b.recall)}</td></tr></tbody></table><h3>What this does and does not prove</h3><p>The test set contains ${nfmt(m.eligible)} employees with a true manager; ${nfmt(r.test_missing_managers)} have a manager missing from the observed roster. All results measure recovery of this synthetic generator—not accuracy on real company data. The generator and inference rules share structural assumptions, so real-world performance may be lower. See the repository for methodology, splits and reproduction instructions.</p></div>`;
}
function renderMethod(){
 const r=state.evaluation;if(!r)return;
 $('#method-view').innerHTML=`<div class="page-intro"><div><div class="eyebrow"><span></span> HOW THE MAP IS MADE</div><h1>Every line has a reason<span class="period">.</span></h1><p>Conservative inference from noisy titles, with uncertainty built in.</p></div></div><div class="info-grid"><div class="info-card"><div class="micro">01 / GENERATE</div><h3>Create truth first</h3><p>Generate private hierarchies, then hide managers and corrupt observed fields to create a realistic flat roster.</p></div><div class="info-card"><div class="micro">02 / INFER</div><h3>Find plausible managers</h3><p>Normalize titles into function and seniority, then compare candidates within the same company.</p></div><div class="info-card"><div class="micro">03 / ABSTAIN</div><h3>Prefer a blank</h3><p>Missing data, ties and low calibrated confidence leave the manager unresolved.</p></div></div><div class="info-section"><h2>A reproducible decision pipeline</h2><ol><li>Generate ${nfmt(r.dataset.companies)} fictional companies and ${nfmt(r.dataset.employees)} observed employees, with title variations, missing fields and some absent managers.</li><li>Split by company: 300 for development, 100 for confidence calibration, and 100 held out for evaluation. Candidate generation never reads truth.</li><li>Extract title-based function, specialty and seniority. Match only more senior candidates within allowed function/role boundaries; use location as weak supporting evidence.</li><li>Abstain on competing equal candidates, ambiguous titles, no suitable observed candidate and scores below the threshold. An absent true manager can still lead to an incorrect match. A predicted manager always has a higher inferred seniority, preventing cycles.</li><li>Calibrate raw scores using monotone pooled-adjacent-violators on the calibration companies. Show an explanation and confidence beside each accepted line.</li></ol><h3>Why not infer every manager?</h3><p>Two people may share the same manager title; a leader may report to the CTO in one company and the COO in another. A missing edge is more useful than a confident-looking guess.</p><h3>Limits of the demo</h3><p>These are structured rules, not a production-trained AI model. The generated reporting patterns share assumptions with the inference rules. Confidence applies to this synthetic distribution only; it must be revalidated against independently labeled real-world orgs before use in production. The development process used AI assistance; no external model is called at runtime.</p></div>`;
}
$('#company-picker').addEventListener('click',()=>{const pop=$('#company-popover');pop.classList.toggle('hidden');const open=!pop.classList.contains('hidden');$('#company-picker').setAttribute('aria-expanded',String(open));if(open){companyOptions($('#company-search').value);$('#company-search').focus()}});
$('#company-search').addEventListener('input',e=>companyOptions(e.target.value));
$('#company-options').addEventListener('click',e=>{const b=e.target.closest('[data-company]');if(b)selectCompany(b.dataset.company)});
document.addEventListener('click',e=>{if(!e.target.closest('.company-picker-wrap')){$('#company-popover').classList.add('hidden');$('#company-picker').setAttribute('aria-expanded','false')}});
document.querySelectorAll('.nav-item').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
$('#about-link').addEventListener('click',()=>setView('method'));
$('#people-search').addEventListener('input',renderChart);$('#confidence-filter').addEventListener('change',()=>{renderStats();renderChart()});$('#directory-search').addEventListener('input',renderDirectory);
$('#chart').addEventListener('click',e=>{let toggle=e.target.closest('[data-toggle]');if(toggle){const id=toggle.dataset.toggle;state.expanded.set(id,toggle.getAttribute('aria-expanded')!=='true');renderChart();return;}if(e.target.closest('#show-unresolved')){state.showUnresolved=!state.showUnresolved;renderChart();return;}const person=e.target.closest('[data-person]');if(person){state.selected=person.dataset.person;renderChart()}});
$('#person-detail').addEventListener('click',e=>{const b=e.target.closest('[data-person]');if(b){state.selected=b.dataset.person;renderChart()}});
$('#directory').addEventListener('click',e=>{const b=e.target.closest('[data-person]');if(!b)return;state.selected=b.dataset.person;state.showUnresolved=true;let g=graph(),id=g.parent.get(state.selected);while(id){state.expanded.set(id,true);id=g.parent.get(id)};setView('explorer');renderChart();document.querySelector(`.person-button[data-person="${CSS.escape(state.selected)}"]`)?.scrollIntoView({block:'nearest',behavior:'smooth'});});
(async()=>{try{const [a,b]=await Promise.all([fetch('./data/index.json'),fetch('./data/evaluation.json')]);if(!a.ok||!b.ok)throw Error('Data could not be loaded');state.companies=await a.json();state.evaluation=await b.json();companyOptions();await selectCompany(state.companies[0].id)}catch(e){$('#company-name').textContent='Unable to load';$('#chart').innerHTML=`<div class="error">${escapeHTML(e.message)}. Reload the page and try again.</div>`}})();
