/* Shared progressive-web-app affordance. Never opens a public listener on the PC. */
(()=>{'use strict';
 const secure=location.protocol==='https:'||['localhost','127.0.0.1'].includes(location.hostname);
 if(secure&&'serviceWorker' in navigator)navigator.serviceWorker.register('/service-worker.js',{scope:'/'}).catch(()=>{});
 const host=document.querySelector('.main-topbar,.chat-header,.top-actions,.map-topbar');
 if(!host)return;
 const btn=document.createElement('button');
 btn.type='button';btn.id='installLocalAi';btn.textContent='◫ Installer';btn.title="Installer l'application sur téléphone";
 btn.setAttribute('aria-label',"Installer LocalAiVision sur le téléphone");
 Object.assign(btn.style,{background:'#292039',color:'#f6eeff',border:'1px solid #70519d',borderRadius:'11px',
  padding:'9px 10px',font:'600 11px system-ui,sans-serif',cursor:'pointer',flexShrink:'0'});
 host.appendChild(btn);
 let installPrompt=null;
 window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;});
 const message=()=>{if(!secure)return "L'installation complète nécessite une adresse HTTPS (ou localhost sur ce même appareil). Le serveur PC est privé par défaut. Utilise une connexion privée sécurisée avant d'ouvrir l'application sur ton téléphone.";
  if(/iPhone|iPad|iPod/.test(navigator.userAgent))return "Sur iPhone : ouvre cette adresse dans Safari, touche Partager, puis Sur l’écran d’accueil. Le moteur de génération reste sur ton PC et doit être allumé et accessible par une connexion privée sécurisée.";
  return "Dans le navigateur du téléphone, utilise son menu puis Installer l'application ou Ajouter à l'écran d'accueil. Le PC doit rester accessible pour créer du contenu."};
 btn.addEventListener('click',async()=>{
  if(installPrompt){const prompt=installPrompt;installPrompt=null;try{await prompt.prompt();await prompt.userChoice;}catch{}}
  else window.alert(message());
 });
 window.addEventListener('appinstalled',()=>{btn.textContent='✓ Installée';btn.disabled=true;});
})();
