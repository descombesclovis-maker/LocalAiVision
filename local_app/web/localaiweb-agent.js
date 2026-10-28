/* LocalAiWeb: real agent connection and persistent, purposeful studio art mode.
   ChatGPT Plus signs in to the installed Codex CLI. Never silently purchase API
   credits, auto-install packages or label an unauthenticated agent as ready. */
(()=>{
'use strict';
const button=document.getElementById('connectAgent');
if(!button)return;
const selector=document.getElementById('lawAgentSelect');
const cinema=document.getElementById('lawCinemaMode');
const projectId=(new URLSearchParams(location.search)).get('id')||'';
const validProject=/^web-[a-f0-9]{12}$/.test(projectId);
let state={},current='codex',saving=false;

async function api(url,body){
 const response=await fetch(url,body===undefined?{cache:'no-store'}:{
  method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 let result={};try{result=await response.json()}catch{}
 if(!response.ok||result.error)throw Error(result.error||('HTTP '+response.status));
 return result;
}
function feedback(value){
 const status=document.getElementById('lawChatStatus');
 if(status)status.textContent=value;
}
function selectedProvider(){return selector?.value||current}
function render(){
 const provider=selectedProvider(),entry=state[provider]||{installed:false,ready:false};
 if(entry.ready){
  button.textContent=provider==='codex'?'● Codex connecté':'● Claude connecté';
  button.title='Agent authentifié. Cliquer pour revérifier la connexion.';
 }else if(entry.installed){
  button.textContent=provider==='codex'?'○ Connecter Codex':'○ Connecter Claude';
  button.title='Ouvrir une fenêtre d’authentification sur cet ordinateur.';
 }else{
  button.textContent=provider==='codex'?'↓ Installer Codex':'↓ Installer Claude';
  button.title='Ouvrir les instructions officielles pour installer l’agent.';
 }
 button.disabled=saving;
 if(selector)selector.disabled=saving;
 if(cinema)cinema.disabled=saving;
}
async function check(){
 if(saving)return;
 try{
  const result=await api('/api/web/capabilities');
  state=result.integrations||{};
  render();
 }catch(error){
  button.textContent='⚠ Connexion indisponible';
  button.title='Vérification impossible : '+error.message;
 }
}
async function patchSettings(patch){
 if(!validProject)throw Error('Sélectionne un projet LocalAiWeb pour modifier ses réglages.');
 return api('/api/web/project/agent-settings',{id:projectId,...patch});
}
async function setup(){
 if(!selector||!validProject){render();return}
 try{
  const result=await api('/api/web/project?id='+encodeURIComponent(projectId));
  const project=result.project||{};
  const saved=project.settings||{};
  // Older projects had Claude hard-coded without a deliberate user choice.
  // They migrate to Codex automatically unless Claude was selected manually.
  const provider=saved.ai_provider==='claude'&&project.agent_selected_by_user===true
   ?'claude':'codex';
  selector.value=provider;current=provider;
  if(cinema){
   const enabled=saved.art_direction==='spatial3d';
   cinema.classList.toggle('active',enabled);
   cinema.setAttribute('aria-pressed',String(enabled));
   cinema.title=enabled?'Désactiver la signature 3D du projet':'Activer la direction artistique 3D immersive pour les prochaines générations.';
  }
  render();
 }catch(error){feedback('Préférences de projet indisponibles : '+error.message)}
}
selector?.addEventListener('change',async()=>{
 const chosen=selector.value,previous=current;
 saving=true;render();
 try{
  await patchSettings({ai_provider:chosen});
  current=chosen;
  feedback(chosen==='codex'
   ?'Codex sélectionné. La connexion utilise ton abonnement ChatGPT Plus et ses quotas.'
   :'Claude Code sélectionné uniquement pour ce projet ; authentifie ton compte Claude.');
 }catch(error){
  selector.value=previous;
  feedback('Agent inchangé : '+error.message);
 }finally{saving=false;render()}
});
cinema?.addEventListener('click',async()=>{
 if(saving)return;
 const currentMode=cinema.getAttribute('aria-pressed')==='true',next=!currentMode;
 saving=true;render();
 try{
  await patchSettings({art_direction:next?'spatial3d':'auto'});
  cinema.classList.toggle('active',next);
  cinema.setAttribute('aria-pressed',String(next));
  feedback(next
   ?'Signature 3D activée pour ce projet : le prochain site utilisera une direction immersive, de vrais effets et des alternatives mobiles si pertinent.'
   :'Direction artistique automatique réactivée pour ce projet.');
 }catch(error){feedback('Mode 3D inchangé : '+error.message)}
 finally{saving=false;render()}
});
button.addEventListener('click',async()=>{
 if(saving)return;
 const provider=selectedProvider(),entry=state[provider]||{};
 if(entry.ready){await check();feedback('Connexion vérifiée : '+(provider==='codex'?'Codex':'Claude Code'));return}
 if(!entry.installed){
  const docs=provider==='codex'?'https://developers.openai.com/codex/cli':
                                 'https://code.claude.com/docs/en/setup';
  window.open(docs,'_blank','noopener,noreferrer');
  feedback(provider==='codex'
    ?'Installe Codex CLI via npm install -g @openai/codex, puis reviens ici pour te connecter avec ChatGPT Plus.'
    :'Installe Claude Code depuis la documentation officielle, puis authentifie ton compte.');
  return;
 }
 saving=true;render();
 try{
  await api('/api/web/integrations/connect',{provider});
  feedback('Fenêtre de connexion ouverte. Termine la procédure d’authentification, puis clique sur le statut pour revérifier.');
 }catch(error){feedback('Connexion non lancée : '+error.message)}
 finally{saving=false;render()}
});
check();setup();
document.addEventListener('visibilitychange',()=>{if(!document.hidden)check()});
window.setInterval(()=>{if(!document.hidden)check()},25000);
})();