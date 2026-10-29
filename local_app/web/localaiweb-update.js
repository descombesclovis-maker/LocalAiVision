/* Same verified Windows update endpoints as the LocalAiVision main sidebar.
   Never touches individual LocalAiWeb projects or model folders. */
(function(){
 const btn=document.getElementById('lawUpdateBtn');
 if(!btn)return;
 // On the phone only the web interface refreshes. Never remotely install or
 // restart the Windows executable while the user is editing from mobile.
 if(/iPhone|iPad|iPod|Android/i.test(navigator.userAgent)){
   // Refreshing the phone fetches *the currently installed PC build*.
   // It does not update a frozen Windows executable from GitHub.
   btn.textContent='↻ Mettre à jour le PC';
   btn.title='Demander la mise à jour sécurisée du programme Windows depuis cet iPhone';
   btn.setAttribute('aria-label','Mettre à jour LocalAiVision sur le PC depuis le téléphone');
   btn.disabled=false;
   btn.addEventListener('click',async()=>{
     btn.disabled=true;btn.textContent='Vérification du PC…';
     try{
       const result=await window.localAiWebPcUpdate?.check();
       btn.textContent=result?.deferred?'Reportée · création active':
         result?.updated?'Redémarrage du PC…':'✓ Vérification terminée';
     }catch(error){btn.textContent='Erreur : '+error.message}
     finally{window.setTimeout(()=>{btn.disabled=false;btn.textContent='↻ Mettre à jour le PC'},6500)}
   });
   const status=document.getElementById('lawMobileBuildStatus');
   if(status){
     status.hidden=false;
     status.textContent='Vérification de la version installée sur le PC…';
     fetch('/api/ping',{cache:'no-store'}).then(r=>r.json()).then(async data=>{
       if(data.app!=='LocalVisionAI')throw Error('Le logiciel PC ne répond pas correctement.');
       const current=String(data.build_tag||data.version||'inconnue');
       status.textContent='Version installée sur le PC : '+current+'.';
       try{
         const response=await fetch('/api/update/check',{cache:'no-store'});
         if(!response.ok)return;
         const release=await response.json();
         const state=release.automatic||{};
         const suffix=state.enabled?' · Surveillance automatique active':
           ' · Surveillance automatique désactivée sur ce PC';
         if(release.available){
           status.textContent='PC : '+current+' · Nouvelle version : '+
             (release.latest_build||'disponible')+
             '. Mise à jour du PC en préparation'+suffix+'.';
         }else status.textContent='PC : '+current+' · version publiée actuelle'+suffix+'.';
       }catch{
         // Still report the exact server build if GitHub is unreachable.
       }
     }).catch(error=>{
       status.textContent='Connexion au logiciel PC indisponible : '+error.message;
     });
   }
   return;
 }
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
     method:'POST',headers:{'Content-Type':'application/json','X-LocalAiVision-Update':'1'},body:'{}'
   });
   if(installed.deferred){
    btn.textContent='Mise à jour différée';
    window.alert(installed.message||'Une génération en cours doit se terminer avant la mise à jour.');
    window.setTimeout(()=>{btn.disabled=false;btn.textContent=label},3500);
   }else if(installed.updated){
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
