/* Shared rendering of observed progress. Sampling completion is not file completion. */
(()=>{'use strict';
const phases={planning:14,images:30,assets:34,building:58,implementation:58,verification:74,repair:76,localization:82,preview:88,visual:92,design:94,finalizing:96};
function state(job={},web=false){
 const raw=job.progress_percent??job.percent;
 const exact=raw!==null&&raw!==undefined&&Number.isFinite(Number(raw));
 const complete=job.state==='done'&&job.output_verified===true;
 const percent=complete?100:exact?Math.max(0,Math.min(99,Math.round(Number(raw)))):web?(phases[job.phase]??8):null;
 return {percent,estimated:!exact&&web,complete,label:job.detail||job.phase||'Préparation du moteur'};
}
function render(host,job={},options={}){
 if(!host)return;
 const value=state(job,options.web);
 host.classList.add('studio-progress');
 host.dataset.unknown=String(value.percent===null);
 host.setAttribute('role','progressbar');host.setAttribute('aria-valuemin','0');host.setAttribute('aria-valuemax','100');
 if(value.percent===null)host.removeAttribute('aria-valuenow');else host.setAttribute('aria-valuenow',String(value.percent));
 host.setAttribute('aria-valuetext',(value.percent===null?'Progression indisponible':value.percent+' %'+(value.estimated?' estimé':' · étape du moteur'))+' · '+value.label);
 if(!host.querySelector('.studio-progress-meter')){
  host.replaceChildren();
  host.innerHTML='<svg class="studio-progress-meter" viewBox="0 0 100 100" aria-hidden="true"><circle class="studio-progress-track" cx="50" cy="50" r="43"/><circle class="studio-progress-arc" cx="50" cy="50" r="43" pathLength="100"/></svg><span class="studio-progress-value"></span><small class="studio-progress-hint"></small>';
 }
 host.querySelector('.studio-progress-arc').style.strokeDashoffset=String(100-(value.percent??24));
 host.querySelector('.studio-progress-value').textContent=value.percent===null?'…':value.percent+' %';
 host.querySelector('.studio-progress-hint').textContent=value.estimated?'estimé':value.percent===null?'en cours':value.complete?'terminé':'étape moteur';
 return value;
}
const selectJob=(jobs,ids)=>jobs.find(job=>ids.includes(job.prompt_id))||null;
window.StudioProgress={state,render,selectJob};
})();
