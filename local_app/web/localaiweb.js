/* LocalAiWeb — one conversation, full-site preview, three device modes.
 * All mutations are initiated by natural language. No hidden side-panel state.
 */
const $ = s => document.querySelector(s);
const api = async(url,body) => {
  const options=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
  const response=await fetch(url,options);
  let result={};try{result=await response.json()}catch{}
  if(!response.ok||result.error)throw Error(result.error||'Erreur HTTP '+response.status);
  return result;
};
let project=null,busy=false,viewport='desktop',stage='welcome';
const chat=$('#lawChat'),prompt=$('#lawPrompt'),button=$('#lawGenerate');
function scrollBottom(){chat.scrollTop=chat.scrollHeight;}
// Action menu is attached only to messages written by the user.
// Last means the most recently SENT user message (not the last assistant reply).
function isLastUserMessage(item){
 const sent=chat.querySelectorAll('.message.user');
 return sent.length>0 && sent[sent.length-1]===item;
}
async function copySentMessage(text){
 try{
  if(navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
  else{
   const temporary=document.createElement('textarea');
   temporary.value=text;temporary.setAttribute('readonly','');
   temporary.style.position='fixed';temporary.style.opacity='0';
   document.body.appendChild(temporary);temporary.select();
   const copied=document.execCommand('copy');temporary.remove();
   if(!copied)throw Error('Clipboard unavailable');
  }
  $('#lawChatStatus').textContent='Prompt copié.';
 }catch{
  $('#lawChatStatus').textContent='Copie indisponible : sélectionne le texte du message.';
 }
}
function sentMessageActions(item, text){
 const actions=document.createElement('div');
 actions.className='message-actions';actions.hidden=true;
 function makeAction(label,handler){
  const control=document.createElement('button');
  control.type='button';control.className='message-action';
  control.textContent=label;
  control.addEventListener('click',event=>{event.stopPropagation();handler();});
  actions.appendChild(control);
 }
 function toggle(){
  const wasOpen=!actions.hidden;
  chat.querySelectorAll('.message-actions').forEach(menu=>{menu.hidden=true;});
  if(wasOpen)return;
  actions.replaceChildren();
  makeAction('Copier',()=>copySentMessage(text));
  makeAction('Renvoyer',()=>{
   if(busy)return;
   actions.hidden=true;
   // A resend is a new instruction; keep any unsent draft in the composer.
   sendText(text,{preserveDraft:true});
  });
  if(isLastUserMessage(item)){
   makeAction('Modifier',()=>{
    if(busy||!isLastUserMessage(item))return;
    actions.hidden=true;
    prompt.value=text;prompt.focus();
    prompt.setSelectionRange(prompt.value.length,prompt.value.length);
    $('#lawChatStatus').textContent='Modifie ton dernier prompt, puis renvoie-le.';
   });
  }
  actions.hidden=false;
 }
 item.tabIndex=0;
 item.title='Cliquer pour copier ou renvoyer ce prompt';
 item.setAttribute('aria-label','Prompt envoyé. Cliquer pour les actions');
 item.addEventListener('click',event=>{
  if(event.target.closest('.message-actions'))return;
  toggle();
 });
 item.addEventListener('keydown',event=>{
  if(event.target!==item)return;
  if(event.key==='Enter'||event.key===' '){
   event.preventDefault();toggle();
  }
 });
 item.appendChild(actions);
}
function message(text,role='assistant'){
 // The studio chat is deliberately empty until the user speaks. Agent
 // progress and errors belong to the small status line, never chat bubbles.
 if(role!=='user'){
   if(/^(Erreur|Impossible|Création interrompue|Connexion|Publication)/i.test(String(text||'')))
     $('#lawChatStatus').textContent=String(text).slice(0,230);
   return null;
 }
 const item=document.createElement('article');item.className='message '+(role==='user'?'user':'assistant');
 if(role!=='user'){const name=document.createElement('div');name.className='message-author';name.textContent='LocalAiWeb';item.appendChild(name);}
 const textNode=document.createElement('p');textNode.textContent=String(text||'');item.appendChild(textNode);
 if(role==='user')sentMessageActions(item,String(text||''));
 chat.appendChild(item);scrollBottom();return item;
}
function setBusy(flag,text){busy=flag;button.disabled=flag;prompt.disabled=flag;$('#lawChatStatus').textContent=text||(flag?'Je travaille sur ton site…':'Prêt à créer ton site');button.textContent=flag?'Création…':'Envoyer ↑';}
function preview(){
 if(!project)return;
 $('#lawPreviewTitle').textContent=project.project.name||'Ton site';
 const id=encodeURIComponent(project.project.id);
 const url='/web-preview/'+id+'/index.html?refresh='+Date.now();
 $('#lawPreview').src=url;
}
function view(mode){
 if(!['desktop','tablet','mobile'].includes(mode))return;
 viewport=mode;$('#lawPreviewStage').className='preview-stage '+mode;
 document.querySelectorAll('[data-view]').forEach(button=>{const active=button.dataset.view===mode;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
}
function detectIntent(text){
 const t=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 if(/^(?:nouveau site|nouveau projet|creer un nouveau site|recommencer un projet|creer un autre site)[.! ]*$/.test(t))return 'new';
 if(/^(?:mes projets|liste des projets|voir mes projets)[.! ]*$/.test(t))return 'projects';
 if(/^(?:publier(?: le site)?|mettre en ligne(?: le site)?|deployer(?: le site)?)[.! ]*$/.test(t))return 'publish';
 if(/^(?:exporter(?: le site)?|telecharger(?: le site)?|telecharger le code|exporter en zip)[.! ]*$/.test(t))return 'export';
 if(/^(?:aide|comment ca marche|comment utiliser localaiweb)[.! ?]*$/.test(t))return 'help';
 if(/^(?:annuler|retour en arriere|restaurer la version precedente)[.! ]*$/.test(t))return 'restore';
 return '';
}
async function ensureProject(){
 if(project)return;
 // The project must be explicitly chosen on the hub. Never open the newest one
 // or create a project merely because the editor was refreshed.
 const id=new URLSearchParams(window.location.search).get('id')||'';
 if(!/^web-[a-f0-9]{12}$/.test(id)){
   window.location.replace('/localaiweb');
   throw Error('Choisis d’abord un projet dans la bibliothèque.');
 }
 project=await api('/api/web/project?id='+encodeURIComponent(id));
 preview();
}
async function showProjects(){
 window.location.assign('/localaiweb');
}
async function handleProjectOpen(text){
 window.location.assign('/localaiweb');
 return true;
}
function projectBrief(){return '';}
let activeGeneration=null;
let lastLivePreviewVersion='';
function updateLivePreview(status,id){
 if(!status.preview_ready || !status.preview_version)return;
 if(status.preview_version!==lastLivePreviewVersion){
   lastLivePreviewVersion=status.preview_version;
   const url='/web-preview/'+encodeURIComponent(id)+'/index.html?refresh='+encodeURIComponent(status.preview_version);
   $('#lawPreview').src=url;
   $('#lawPreviewTitle').textContent=(project?.project?.name||'Ton site')+' · aperçu en cours';
 }
}
function generationFeedback(result){
 const report=result.quality;
 const visuals=result.visuals||{};
 const mediaNote=visuals.generated?.length
  ?'\\nVisuels créés : '+visuals.generated.length+' photo(s).'
  :visuals.notes?.length?'\\nVisuels : '+visuals.notes[0]:'';
 const checked=report && report.ok;
 message((result.summary||'Le site a été enregistré.')+mediaNote+
  '\\n\\nTu peux maintenant consulter le site à droite et demander des modifications ciblées.'+
  (report&&!checked?'\\nDes points de qualité restent à corriger.':'')+
  '\\nLes devis sont disponibles depuis le dossier commercial et doivent être vérifiés avant émission.',
  'assistant');
}
async function watchGeneration(id){
 if(activeGeneration===id)return;
 activeGeneration=id;
 setBusy(true,'Génération en cours : le site apparaîtra dès sa première compilation…');
 let reading=false;
 const started=Date.now();
 await new Promise(resolve=>{
   const stop=()=>{clearInterval(timer);activeGeneration=null;resolve()};
   const tick=async()=>{
     if(reading)return;reading=true;
     try{
       const status=await api('/api/web/generation/status?id='+encodeURIComponent(id));
       if(status.state==='running'){
         updateLivePreview(status,id);
         const elapsed=Math.floor((Date.now()-started)/1000);
         const time=elapsed>=60?' · '+Math.floor(elapsed/60)+' min écoulée(s)':'';
         $('#lawChatStatus').textContent=(status.detail||'Codex prépare le site…')+time;
       }else if(status.state==='done'){
         project=await api('/api/web/project?id='+encodeURIComponent(id));
         preview();
         $('#lawPreviewTitle').textContent=project.project.name||'Ton site';
         stage='ready';
         const salesLink=document.getElementById('lawSalesBtn');
         if(salesLink)salesLink.href='/localaiweb/vente?id='+encodeURIComponent(id);
         generationFeedback(status);
         stop();
       }else if(status.state==='error'){
         message('Création interrompue : '+(status.error||status.detail||'Cause inconnue')+
          '\\nLe projet et ses fichiers existants sont conservés. Vérifie la connexion Codex puis relance la maquette.',
          'assistant');
         stage='ready';stop();
       }else{
         message('Aucune génération active. Après un redémarrage du logiciel, relance la maquette pour terminer le travail.');
         stage='ready';stop();
       }
     }catch(error){
       // Transient localhost error does not mean Codex failed. Warn after
       // sustained disconnection instead of silently spinning forever.
       if(Date.now()-started>30000)
         $('#lawChatStatus').textContent='Connexion au serveur perdue : '+error.message+
           '. Le travail continue si LocalAiWeb reste ouvert.';
     }finally{reading=false}
   };
   const timer=setInterval(tick,2400);
   tick();
 });
 setBusy(false);
}
async function generate(text){
 await ensureProject();
 if(activeGeneration){message('Une création est déjà en cours pour ce site. Son avancement apparaît sous le champ de saisie.');return}
 setBusy(true,'Vérification de la connexion Codex et préparation du site…');
 const id=project.project.id;
 const existingBrief=projectBrief();
 const instructions=existingBrief
  ?'BRIEF UTILISATEUR :\\n'+existingBrief+'\\n\\nDERNIÈRE DEMANDE :\\n'+text
  :text;
 try{
  const result=await api('/api/web/generate/start',{id,prompt:instructions});
  if(!result.already_running){
   message('Première maquette lancée. Je construis les vrais fichiers du site. '+
    'La prévisualisation sera affichée dès la première compilation, sans attendre les finitions.');
  }else{
   message('La génération précédente continue. Je rétablis son suivi sans relancer Codex.');
  }
  await watchGeneration(id);
 }catch(error){
  message('Impossible de démarrer la génération : '+error.message+
   '\\nVérifie « Codex connecté » dans l’en-tête. Les fichiers déjà créés sont conservés.');
 }finally{setBusy(false)}
}
async function publish(){
 await ensureProject();
 if(project.project?.project_kind==='pro' && !project.project?.business_authorized){
   const okay=window.confirm('Projet Pro : « '+project.project.name+
     ' »\n\nConfirme que tu représentes cette entreprise ou disposes de son autorisation '+
     'explicite pour publier un site en son nom. Vérifie aussi les informations de la carte '+
     'et remplace les maquettes/illustrations non officielles.\n\nAutoriser la publication ?');
   if(!okay){message('Publication annulée : le site reste une maquette privée.');return;}
   try{
     project=await api('/api/web/project/pro/authorize',{
       id:project.project.id,confirmed:true});
   }catch(err){message('Autorisation non enregistrée : '+err.message);return;}
 }
 message('Je vérifie le site avant publication. La publication nécessite que Vercel soit installé et connecté sur cet ordinateur.');
 setBusy(true,'Vérification et mise en ligne…');
 try{
  await api('/api/web/build',{id:project.project.id});
  const report=await api('/api/web/preflight?id='+encodeURIComponent(project.project.id));
  if(!report.ok){
   message('Publication suspendue : '+(report.blockers||[]).map(c=>c.label).join(', ')+'.\nÉcris « corrige les problèmes de publication » et je modifierai le site avant de réessayer.');return;
  }
  const result=await api('/api/web/vercel/publish',{id:project.project.id,production:true});
  project=result;
  const deployed=result.deployment_result?.url||result.project?.deployment?.production_url;
  if(deployed)message('Site publié : '+deployed+'\nTu peux ouvrir ce lien dans ton navigateur.');
  else message('La commande de publication est terminée, mais aucune URL publique n’a été confirmée. Vérifie la connexion Vercel.');
 }catch(error){message('Publication non effectuée : '+error.message+'\nTon site local reste disponible dans la prévisualisation.');}
 finally{setBusy(false);}
}
async function exportSite(){
 await ensureProject();
 try{
  const url='/api/web/export?id='+encodeURIComponent(project.project.id);
  const a=document.createElement('a');a.href=url;a.download='LocalAiWeb-'+project.project.id+'.zip';
  document.body.appendChild(a);a.click();a.remove();
  message('J’ai lancé le téléchargement du ZIP de ton site. Il contient les fichiers du projet, pas les secrets ni les données des services externes.');
 }catch(error){message('Export impossible : '+error.message);}
}
async function restoreLast(){
 await ensureProject();
 const versions=project.versions||[];
 if(!versions.length){message('Il n’existe pas encore de version précédente à restaurer.');return;}
 const d=await api('/api/web/version/restore',{id:project.project.id,version_id:versions[0].id});
 project=d;preview();message('J’ai restauré une version précédente. Regarde le site à droite.');
}
async function startProDraft(retry=false){
 if(!project || project.project?.project_kind!=='pro')return false;
 const claim=await api('/api/web/project/auto-claim',{id:project.project.id,retry});
 if(!claim.ready || !claim.prompt)return false;
 stage='ready';
 message('Je construis maintenant une première maquette indépendante pour « '+
   project.project.name+' ». Elle restera modifiable dans cette conversation. '+
   'Les informations de la carte devront être vérifiées avant publication.');
 await generate(claim.prompt);
 return true;
}
async function sendText(value,{preserveDraft=false}={}){
 const text=String(value||prompt.value||'').trim();if(!text||busy)return;
 if(!preserveDraft)prompt.value='';message(text,'user');setBusy(true,'Je comprends ta demande…');
 try{
  const intent=detectIntent(text);
  if(text.toLowerCase().trim()==='relancer la maquette' && project?.project?.project_kind==='pro'){
    const launched=await startProDraft(true);
    if(!launched)message('Cette maquette a déjà été lancée. Attends le résultat ou décris une modification dans le chat.');
    return;
  }
  if(intent==='new'){
   window.location.assign('/localaiweb');return;
  }
  if(intent==='projects'){await showProjects();return;}
  if(/^ouvrir\s+/i.test(text)&&await handleProjectOpen(text))return;

  if(intent==='publish'){await publish();return;}
  if(intent==='export'){await exportSite();return;}
  if(intent==='restore'){await restoreLast();return;}
  // Natural-language instructions go straight to the selected coding agent.
  // No questionnaire, mandatory style guide, canned suggestions or QCM.
  await generate(text);
 }catch(error){message('Erreur : '+error.message);}
 finally{setBusy(false);}
}
$('#lawComposer').addEventListener('submit',event=>{event.preventDefault();sendText(prompt.value);});
prompt.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendText(prompt.value);}});
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>view(button.dataset.view)));
async function initialize(){
 try{
  await ensureProject();
  const id=project.project.id;
  const salesLink=document.getElementById('lawSalesBtn');
  if(salesLink)salesLink.href='/localaiweb/vente?id='+encodeURIComponent(id);
  chat.replaceChildren();
  for(const row of project.chat||[]){
   if(row.role==='user')message(row.text,'user');
  }
  stage='ready';
  const generation=await api('/api/web/generation/status?id='+encodeURIComponent(id));
  if(generation.state==='running'){
   updateLivePreview(generation,id);
   await watchGeneration(id);
   return;
  }
  const first=project.project?.initial_generation||{};
  if(project.project?.project_kind==='pro' && !generation.preview_ready &&
     (first.status==='pending'||first.status==='failed')){
    const dialog=$('#lawDesignDialog');
    if(dialog&&!dialog.open)dialog.showModal();
  }
 }catch(error){
  $('#lawChatStatus').textContent='Chargement impossible : '+error.message;
 }
}
const designDialog=$('#lawDesignDialog');
const designForm=$('#lawDesignForm');
$('#lawDesignCancel')?.addEventListener('click',()=>{
 designDialog.close();prompt.focus();
});
designForm?.addEventListener('submit',async event=>{
 event.preventDefault();
 if(busy||!project)return;
 const submit=$('#lawDesignCreate');
 const error=$('#lawDesignError');
 error.textContent='';submit.disabled=true;
 try{
  const form=new FormData(designForm);
  const choices={};
  for(const [key] of form.entries()){
    if(key==='include_notes')continue;
    if(key==='notes'){
      choices.notes=form.has('include_notes')?String(form.get('notes')||''):'';
    }else{
      const enabled=form.getAll(key);
      choices[key]=enabled.length===1?enabled[0]:enabled;
    }
  }
  project=await api('/api/web/project/design-profile',{
   id:project.project.id,profile:choices});
  designDialog.close();
  // This single explicit action creates the first business site.
  const initial=project.project.initial_generation||{};
  if(initial.status==='pending'||initial.status==='failed'){
   await startProDraft(initial.status==='failed');
  }
 }catch(e){
  error.textContent='Impossible de lancer la maquette : '+e.message;
  $('#lawChatStatus').textContent=e.message;
 }finally{submit.disabled=false}
});
initialize();
