/* Same verified Windows update endpoints as the LocalAiVision main sidebar.
   Never touches individual LocalAiWeb projects or model folders. */
(function(){
 const btn=document.getElementById('lawUpdateBtn');
 if(!btn)return;
 const label='↻ Mettre à jour';
 async function request(url, options){
  const res=await fetch(url,options);
  let data={};
  try{data=await res.json()}catch{}
  if(!res.ok||data.error)throw Error(data.error||'HTTP '+res.status);
  return data;
 }
 async function update(){
  if(btn.disabled)return;
  btn.disabled=true;btn.textContent='Vérification…';
  try{
   const state=await request('/api/update/check');
   if(!state.available){
    btn.textContent='✓ À jour';
    window.setTimeout(()=>{btn.disabled=false;btn.textContent=label;},2500);
    return;
   }
   const labelNew=state.latest_build||state.latest_version||'une nouvelle version';
   const mb=state.size>0?' ('+Math.round(state.size/1024/1024)+' Mo)':'';
   if(!window.confirm('Mise à jour disponible : '+labelNew+mb+
       '\n\nTélécharger, remplacer le logiciel et le redémarrer ?\nLes projets et les modèles sont conservés.')){
    btn.disabled=false;btn.textContent=label;return;
   }
   btn.textContent='Téléchargement…';
   const installed=await request('/api/update/install',{
     method:'POST',headers:{'Content-Type':'application/json'},body:'{}'
   });
   if(installed.updated){
    btn.textContent='Redémarrage…';
    btn.title='La mise à jour a été téléchargée. Le logiciel va redémarrer.';
   }else{
    btn.textContent='✓ À jour';
    window.setTimeout(()=>{btn.disabled=false;btn.textContent=label;},2500);
   }
  }catch(error){
   btn.disabled=false;btn.textContent=label;
   const diag=await request('/api/update/diagnostics').catch(()=>null);
   const detail=diag?.state==='failed'?'\nDernier échec : '+diag.message:'';
   window.alert('Mise à jour impossible : '+error.message+detail+
      '\nJournal de diagnostic : %LOCALAPPDATA%\\LocalVisionAI\\logs\\update.log');
  }
 }
 btn.addEventListener('click',update);
 // A failed update rolls back and reopens the prior app. Make that failure
 // visible instead of implying the button succeeded silently.
 request('/api/update/diagnostics').then(diag=>{
   if(diag.state==='failed'){
     btn.title='Dernière mise à jour échouée : '+diag.message+
       '. Consulte %LOCALAPPDATA%\\LocalVisionAI\\logs\\update.log';
     btn.setAttribute('aria-label','Mise à jour précédente échouée. '+diag.message);
   }
 }).catch(()=>{});
})();
