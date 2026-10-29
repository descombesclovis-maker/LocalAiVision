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
      toggle=chip.querySelector('#studioActivityToggle'),copy=chip.querySelector('.studio-activity-copy'),
      count=chip.querySelector('.studio-activity-count');
   if(!jobs.length){
     if(previous.size){
       copy.textContent='Création terminée · Voir les projets';
       count.textContent='✓';
       chip.hidden=false;
       const first=Array.from(previous.values())[0];
       if(safeId(first?.id))toggle.onclick=()=>{window.location.assign(dest(first.id));};
       setTimeout(()=>{if(!previous.size)chip.hidden=true;toggle.onclick=null},9000);
     }else chip.hidden=true;
     previous.clear();panel.replaceChildren();expanded=false;panel.hidden=true;
     toggle.setAttribute('aria-expanded','false');
     return;
   }
   toggle.onclick=null;
   chip.hidden=false;
   previous=new Map(jobs.map(job=>[job.id,job]));
   copy.textContent=jobs.length===1?'Création du site « '+jobs[0].name+' »…':jobs.length+' sites en création…';
   count.textContent=jobs.length>1?String(jobs.length):'';
   panel.replaceChildren();
   const title=document.createElement('strong');title.textContent='Créations en cours';
   panel.append(title);
   for(const job of jobs){
     const link=document.createElement('a');link.href=dest(job.id);
     const name=document.createElement('b');name.textContent=job.name||'Site en création';
     const detail=document.createElement('span');detail.textContent=(job.detail||'Création du site…')+' · '+duration(job.elapsed_seconds);
     link.append(name,detail);panel.append(link);
   }
 }
 async function update(){
   if(document.hidden||requesting)return;
   requesting=true;
   try{
     const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
     try{
       const response=await fetch('/api/web/generations/active',{cache:'no-store',signal:controller.signal});
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