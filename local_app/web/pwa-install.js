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
 window.setInterval(()=>{if(!document.hidden)void checkLatest()},120000);
 void checkLatest();
})();
