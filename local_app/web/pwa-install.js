/* Private mobile installation + automatic application refresh.
   The phone never downloads or installs a Windows executable. When the PC
   application has been updated, every new browser launch fetches the newest
   HTML, JavaScript and CSS over its authenticated HTTPS Tailscale connection. */
(()=>{
 'use strict';
 const secure=location.protocol==='https:'||['localhost','127.0.0.1'].includes(location.hostname);
 if(!secure)return;
 let worker=null,knownBuild=null,checking=false,lastCheck=0,refreshQueued=false;
 let controllerExisted=Boolean(navigator.serviceWorker?.controller);
 const mobile=/iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
 let pcUpdateChecking=false,lastPcUpdateCheck=0,pcUpdatePolling=false;
 let pcUpdateNote=null;
 const updateHeaders={'Content-Type':'application/json','X-LocalAiVision-Update':'1'};
 function showPcUpdate(text){
   if(!mobile)return;
   if(!pcUpdateNote){
     pcUpdateNote=document.createElement('div');
     pcUpdateNote.id='localaiPcUpdateStatus';
     pcUpdateNote.setAttribute('role','status');
     pcUpdateNote.style.cssText='position:fixed;z-index:2147483600;left:12px;right:12px;bottom:calc(88px + env(safe-area-inset-bottom));max-width:470px;margin:auto;padding:13px 15px;background:#281a39;color:#fff;border:1px solid #ad88df;border-radius:13px;box-shadow:0 10px 38px #000a;font:13px/1.5 system-ui';
     document.body.appendChild(pcUpdateNote);
   }
   pcUpdateNote.textContent=text;
 }
 async function waitForPcBuild(target){
   if(pcUpdatePolling)return;
   pcUpdatePolling=true;
   showPcUpdate('Le PC installe '+target+'. Reconnexion automatique après redémarrage…');
   for(let i=0;i<55;i++){
     await new Promise(resolve=>setTimeout(resolve,4000));
     try{
       const response=await fetch('/api/ping',{cache:'no-store'});
       if(!response.ok)continue;
       const info=await response.json();
       if(info.app==='LocalVisionAI'&&info.build_tag===target){
         location.reload();return;
       }
     }catch{}
   }
   pcUpdatePolling=false;
   showPcUpdate('Le PC n’a pas encore confirmé la nouvelle version. Tu peux fermer puis rouvrir LocalAiWeb.');
 }
 async function updatePcFromPhone(force=false){
   if(!mobile||pcUpdateChecking||pcUpdatePolling||document.hidden)return null;
   if(!force && Date.now()-lastPcUpdateCheck<180000)return null;
   pcUpdateChecking=true;lastPcUpdateCheck=Date.now();
   try{
     if(isEditing()){
       void sendDraftHeartbeat();
       return {deferred:true,message:'Une saisie en cours est préservée.'};
     }
     const response=await fetch('/api/update/check',{cache:'no-store'});
     if(!response.ok)throw Error('Vérification GitHub indisponible.');
     const status=await response.json();
     if(!status.available)return status;
     const result=await fetch('/api/update/install',{
       method:'POST',headers:updateHeaders,body:'{}',
       credentials:'same-origin',cache:'no-store'
     });
     const data=await result.json();
     if(!result.ok||data.error)throw Error(data.error||'Installation refusée.');
     if(data.updated && data.latest_build){
       void waitForPcBuild(data.latest_build);
     }else if(data.deferred){
       showPcUpdate('Mise à jour '+(status.latest_build||'')+
         ' différée pour protéger ton travail : '+(data.message||'activité en cours')+
         '. Elle sera retentée automatiquement.');
     }
     return data;
   }catch(error){
     if(force)showPcUpdate('Mise à jour du PC : '+error.message);
     return {error:error.message};
   }finally{pcUpdateChecking=false}
 }
 async function sendDraftHeartbeat(){
   if(!mobile||document.hidden)return;
   const active=document.activeElement;
   const typed=Boolean(active?.matches?.('textarea,input:not([type=checkbox]):not([type=radio]):not([type=hidden])') &&
                       typeof active.value==='string' && active.value.trim());
   const pending=Array.from(document.querySelectorAll(
     '#lawPrompt, #prompt, #lawInspectorPrompt, #projectName'
   )).some(el=>Boolean(el.value?.trim()));
   if(!typed&&!pending)return;
   try{
     await fetch('/api/update/draft',{method:'POST',
       headers:updateHeaders,body:JSON.stringify({active:true}),
       credentials:'same-origin',keepalive:true
     });
   }catch{}
 }
 window.localAiWebPcUpdate={check:()=>updatePcFromPhone(true)};
 if(mobile){
   document.addEventListener('input',()=>{void sendDraftHeartbeat()},{passive:true});
   window.setInterval(()=>{void sendDraftHeartbeat()},18000);
   // A phone launch checks for a newer *Windows release* and can trigger the
   // existing verified updater, not merely an HTML refresh.
   window.setTimeout(()=>{void updatePcFromPhone()},2800);
 }
 const isEditing=()=>Boolean(
    document.activeElement && (
      (document.activeElement.matches?.('textarea') &&
       document.activeElement.value?.trim()) ||
      (document.activeElement.matches?.('input:not([type=checkbox]):not([type=radio]):not([type=hidden])') &&
       document.activeElement.value?.trim()) ||
      (document.activeElement.isContentEditable && document.activeElement.textContent?.trim())
    )
 );
 function showRefreshButton(){
   if(document.getElementById('localaiwebRefreshReady'))return;
   const panel=document.createElement('div');
   panel.id='localaiwebRefreshReady';
   panel.setAttribute('role','status');
   panel.style.cssText='position:fixed;z-index:2147483647;bottom:max(18px,env(safe-area-inset-bottom));left:12px;right:12px;max-width:460px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;background:#24162e;color:#fff;border:1px solid #9a6bd4;border-radius:12px;box-shadow:0 8px 28px #0009;font:13px system-ui';
   const title=document.createElement('span');
   title.textContent='Nouvelle version prête. Termine ta saisie avant de l’afficher.';
   const button=document.createElement('button');
   button.type='button';button.textContent='Actualiser';
   button.style.cssText='border:1px solid #a68cdc;border-radius:9px;background:#6c3da7;color:#fff;padding:9px 12px;cursor:pointer';
   button.addEventListener('click',()=>location.reload());
   panel.append(title,button);
   document.body.append(panel);
 }
 function requestRefresh(){
   if(refreshQueued)return;
   refreshQueued=true;
   // A draft in an active input must never disappear during an automatic refresh.
   if(isEditing()){showRefreshButton();return}
   location.reload();
 }
 async function checkLatest(){
   if(!mobile||checking||document.hidden||Date.now()-lastCheck<5000)return;
   checking=true;lastCheck=Date.now();
   try{
     const response=await fetch('/api/ping',{cache:'no-store',credentials:'same-origin'});
     if(!response.ok)return;
     const data=await response.json();
     if(data.app!=='LocalVisionAI')return;
     const build=String(data.build_tag||data.version||'').trim();
     if(!build)return;
     if(knownBuild&&build!==knownBuild){requestRefresh();return}
     knownBuild=build;
   }catch{
     // Offline means unavailable, not an invitation to serve stale private data.
   }finally{checking=false}
 }
 async function onForeground(){
   if(document.hidden)return;
   try{await worker?.update()}catch{}
   void checkLatest();
   void sendDraftHeartbeat();
   void updatePcFromPhone();
 }
 if('serviceWorker' in navigator){
   navigator.serviceWorker.addEventListener('controllerchange',()=>{
     if(controllerExisted){requestRefresh();return}
     controllerExisted=true;
   });
   navigator.serviceWorker.register('/service-worker.js',{
     scope:'/',updateViaCache:'none'
   }).then(registration=>{
     worker=registration;
     return registration.update();
   }).catch(()=>{});
 }
 window.addEventListener('pageshow',()=>{void onForeground()});
 document.addEventListener('visibilitychange',()=>{
   if(!document.hidden)void onForeground();
 });
 window.addEventListener('focus',()=>{void onForeground()});
 // Also catches a build that completes while the mobile page stays open.
 window.setInterval(()=>{if(!document.hidden){void checkLatest();void updatePcFromPhone()}},120000);
 void checkLatest();
})();
