/* Global real-time activity chip: real server state, never synthetic progress. */
(()=>{
 'use strict';
 if(!document.body)return;
 let chip=null,panel=null,previous=new Map(),requesting=false,expanded=false;
 const safeId=id=>/^web-[a-f0-9]{12}$/.test(id||'');
 const dest=id=>'/localaiweb/editor?id='+encodeURIComponent(id);
 function setup(){
   if(chip)return;
   chip=document.createElement('div');
   chip.id='studioActivity';chip.className='studio-activity';
   chip.hidden=true;
   chip.innerHTML='<button id="studioActivityToggle" class="studio-activity-toggle" type="button" aria-expanded="false" aria-controls="studioActivityPanel"><span class="studio-activity-spinner" aria-hidden="true"></span><span class="studio-activity-copy">Création d’un site…</span><span class="studio-activity-count"></span></button><div id="studioActivityPanel" class="studio-activity-panel" hidden></div>';
   document.body.append(chip);
   panel=chip.querySelector('#studioActivityPanel');
   chip.querySelector('#studioActivityToggle').addEventListener('click',()=>{
     expanded=!expanded;panel.hidden=!expanded;chip.querySelector('#studioActivityToggle').setAttribute('aria-expanded',String(expanded));
   });
   document.addEventListener('pointerdown',event=>{
     if(expanded&&!chip.contains(event.target)){
       expanded=false;panel.hidden=true;chip.querySelector('#studioActivityToggle').setAttribute('aria-expanded','false');
     }
   });
 }
 function duration(seconds){
   const sec=Math.max(0,Math.trunc(Number(seconds)||0));
   return sec<60?sec+' s':Math.floor(sec/60)+' min '+String(sec%60).padStart(2,'0')+' s';
 }
 function paint(data){
   const jobs=Array.isArray(data?.jobs)?data.jobs.filter(x=>safeId(x.id)):[],
      media=data?.media||{},mediaCount=Number(media.count)||0,
      toggle=chip.querySelector('#studioActivityToggle'),copy=chip.querySelector('.studio-activity-copy'),
      count=chip.querySelector('.studio-activity-count');
   chip.classList.toggle('has-media',mediaCount>0);
   if(!jobs.length&&!mediaCount){
     if(previous.size){
       copy.textContent=media.unavailable?'État du moteur indisponible':previous.has('vision')?'Génération terminée':'Création terminée · Voir le projet';
       count.textContent='✓';
       chip.hidden=false;
       const first=Array.from(previous.values())[0];
       if(safeId(first?.id))toggle.onclick=()=>{window.location.assign(dest(first.id));};
       else if(first?.id==='vision')toggle.onclick=()=>{window.location.assign('/localaivision?view=creations')};
       setTimeout(()=>{if(!previous.size)chip.hidden=true;toggle.onclick=null},9000);
     }else chip.hidden=true;
     previous.clear();panel.replaceChildren();expanded=false;panel.hidden=true;
     toggle.setAttribute('aria-expanded','false');
     return;
   }
   toggle.onclick=null;
   chip.hidden=false;
   previous=new Map(jobs.map(job=>[job.id,job]));
   if(mediaCount)previous.set('vision',{id:'vision'});
   copy.textContent=mediaCount&&!jobs.length?'Génération photo / vidéo en cours…':
     jobs.length===1&&!mediaCount?'Création du site « '+jobs[0].name+' »…':
     (jobs.length+mediaCount)+' créations en cours…';
   count.textContent=jobs.length+mediaCount>1?String(jobs.length+mediaCount):'';
   panel.replaceChildren();
   const title=document.createElement('strong');title.textContent='Créations en cours';
   panel.append(title);
   for(const job of jobs){
     const link=document.createElement('a');link.href=dest(job.id);
     const name=document.createElement('b');name.textContent=job.name||'Site en création';
     const detail=document.createElement('span');detail.textContent=(job.detail||'Création du site…')+' · '+duration(job.elapsed_seconds);
     link.append(name,detail);panel.append(link);
   }
   if(mediaCount){
     const link=document.createElement('a');link.href='/localaivision?view=creations';
     const title=document.createElement('b');title.textContent='LocalAiVision · Photo / Vidéo';
     const detail=document.createElement('span');
     detail.textContent=media.running?'Rendu ComfyUI en cours'+(media.queued?' · '+media.queued+' en attente':''):
       media.queued+' rendu(s) en attente';
     link.append(title,detail);panel.append(link);
   }
 }
 async function update(){
   if(document.hidden||requesting)return;
   requesting=true;
   try{
     const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
     try{
       const response=await fetch('/api/studio/activity',{cache:'no-store',signal:controller.signal});
       if(response.ok)paint(await response.json());
     }finally{clearTimeout(timeout)}
   }catch{}finally{requesting=false}
 }
 setup();
 void update();
 window.setInterval(update,4200);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)void update()});
 window.addEventListener('pageshow',()=>{void update()});
 window.StudioActivity={refresh:update};
})();