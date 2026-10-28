/* Explicit Claude Code auth flow; never pretend an agent is online. */
(()=>{
 'use strict';
 const button=document.getElementById('connectClaude');
 if(!button)return;
 let busy=false,state=null;
 async function request(url,body){
   const response=await fetch(url,body===undefined?{cache:'no-store'}:{
     method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
   let data={};try{data=await response.json()}catch{}
   if(!response.ok||data.error)throw Error(data.error||'Erreur '+response.status);
   return data;
 }
 const set=(label,title)=>{
   button.textContent=label;button.title=title;button.disabled=busy;
 };
 async function check(){
   if(busy)return;
   try{
     const data=await request('/api/web/capabilities');
     state=data.integrations?.claude||{installed:false,ready:false};
     if(state.ready)set('● Claude connecté','Claude Code authentifié et disponible. Cliquer pour revérifier.');
     else if(state.installed)set('○ Connecter Claude Code','Cliquer pour ouvrir la connexion Claude Code sur cet ordinateur.');
     else set('○ Installer Claude Code','Claude Code absent. Cliquer pour ouvrir les instructions officielles d’installation.');
   }catch(error){set('⚠ Agent indisponible','Diagnostic : '+error.message)}
 }
 button.addEventListener('click',async()=>{
   if(busy)return;
   if(state?.ready){await check();return}
   if(!state?.installed){
     window.open('https://code.claude.com/docs/en/setup','_blank','noopener,noreferrer');
     return;
   }
   busy=true;set('Connexion en cours…','Une fenêtre de terminal Claude Code va s’ouvrir.');
   try{
     await request('/api/web/integrations/connect',{provider:'claude'});
     set('Connexion ouverte · vérifier','Authentifie Claude Code dans la fenêtre ouverte. Cliquer pour revérifier après connexion.');
   }catch(error){set('⚠ Connexion impossible',String(error.message))}
   finally{busy=false;button.disabled=false}
 });
 check();
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)check()});
 window.setInterval(()=>{if(!document.hidden)check()},25000);
})();