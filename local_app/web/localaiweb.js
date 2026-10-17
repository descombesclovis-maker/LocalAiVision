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
function message(text,role='assistant',choices=[]){
 const item=document.createElement('article');item.className='message '+(role==='user'?'user':'assistant');
 if(role!=='user'){const name=document.createElement('div');name.className='message-author';name.textContent='LocalAiWeb';item.appendChild(name);}
 const textNode=document.createElement('p');textNode.textContent=String(text||'');item.appendChild(textNode);
 if(role==='user')sentMessageActions(item,String(text||''));
 if(choices.length){
  const area=document.createElement('div');area.className='choices';
  choices.forEach(value=>{const b=document.createElement('button');b.type='button';b.textContent=value;b.onclick=()=>sendText(value);area.appendChild(b);});
  item.appendChild(area);
 }
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
 if(/^(?:lancer le questionnaire|commencer le questionnaire|questionnaire|guide-moi|pose-moi des questions)[.! ]*$/.test(t))return 'guide';
 if(/^(?:terminer le questionnaire|construis avec ces reponses|creer maintenant|genere maintenant)[.! ]*$/.test(t))return 'build';
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
async function generate(text){
 await ensureProject();
 // The agent edits THIS project's files, including real 3D if requested.
 // Never secretly create a second project and abandon its saved name/history.
 setBusy(true,'Je crée ton site et prépare l’aperçu…');
 const id=project.project.id;
 const existingBrief=projectBrief();
 const instructions=existingBrief
  ?'BRIEF UTILISATEUR :\n'+existingBrief+'\n\nDERNIÈRE DEMANDE :\n'+text
  :text;
 message('Je prends en compte ta demande et construis le site complet. Je conserverai les fonctionnalités déjà créées et je te proposerai ensuite des améliorations ciblées.');
 const progressTimer=setInterval(async()=>{
   try{
     const status=await api('/api/web/progress?id='+encodeURIComponent(id));
     if(status.detail && busy)$('#lawChatStatus').textContent=status.detail;
   }catch{/* The site can still be built if progress polling is unavailable. */}
 },1700);
 try{
  const result=await api('/api/web/generate',{id,prompt:instructions});
  project=result;preview();
  stage='ready';
  const report=result.quality;
  const validated=report && report.ok;
  const visuals=result.visuals||{};
  const mediaNote=visuals.generated?.length
    ?'\nVisuels créés automatiquement : '+visuals.generated.length+' photo(s) de présentation.'
    :visuals.notes?.length
      ?'\nPhotos : '+visuals.notes[0]
      :'';
  message((result.summary||'La version du site a été créée.')+mediaNote+
    '\n\nRegarde le résultat à droite. Tu peux maintenant demander une modification précise : couleur, texte, typographie, page, navigation, produit, animation, 3D, réservation ou autre fonctionnalité.'+
    (report&&!validated?'\nLe contrôle de qualité signale encore des points à corriger ; demande-moi de les améliorer.':''),
    'assistant',['Améliore le rendu visuel','Optimise téléphone et tablette','Ajoute des fonctionnalités','Publier le site']);
 }catch(error){message('Je n’ai pas pu appliquer cette modification : '+error.message+'\nLe projet existant est conservé. Précise la demande ou vérifie que le moteur IA est disponible.');}
 finally{clearInterval(progressTimer);setBusy(false);}
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
function renderBriefQuestion(result){
 if(!result?.question)return;
 stage='specification';
 const q=result.question;
 const step=(result.plan?.index||0)+1,total=(result.plan?.questions||[]).length;
 message('Pour que ton site corresponde exactement à ta demande, il me manque une précision.\n'
   +'Question '+step+' / '+total+' : '+q.question
   +'\nRéponds librement ou choisis une proposition. Je ne génère pas le site avant d’avoir tes réponses.',
   'assistant',q.choices||[]);
}
async function beginSpecification(text){
 await ensureProject();
 const result=await api('/api/web/brief/begin',{id:project.project.id,prompt:text});
 if(result.ready){
   stage='ready';
   return generate(text);
 }
 renderBriefQuestion(result);
}
async function answerSpecification(text){
 const result=await api('/api/web/brief/answer',{id:project.project.id,answer:text});
 if(result.ready){
   stage='ready';
   message('Merci, toutes les précisions nécessaires sont réunies. Je passe à la réalisation du site. Les couleurs, les catégories et les fonctions demandées sont prioritaires.');
   return generate(result.prompt);
 }
 renderBriefQuestion(result);
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
  if(intent==='help'){
   message('Décris ton site ici et observe le résultat complet à droite. Pour revenir à la bibliothèque, clique sur la flèche près de LocalAiWeb ou écris « mes projets ». Pour modifier, continue simplement à discuter.');return;
  }
  if(intent==='guide'){
   stage='welcome';message('Décris ton site en quelques phrases. Je te poserai ensuite, si besoin, une ou deux questions sur son style et ses couleurs.');return;
  }
  if(intent==='publish'){await publish();return;}
  if(intent==='export'){await exportSite();return;}
  if(intent==='restore'){await restoreLast();return;}
  if(stage==='specification'){
   await answerSpecification(text);return;
  }
  if(stage==='welcome'){
   await beginSpecification(text);return;
  }
  if(intent==='build'){await generate('Crée maintenant un site complet et cohérent suivant mes réponses. Produis toutes les pages et interactions réelles nécessaires, un design soigné, une navigation fluide, un responsive impeccable et un contenu utile.');return;}
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
  const rows=project.chat||[];
  const initial=project.project?.initial_generation||{};
  if(project.project?.project_kind==='pro' && initial.status==='pending'){
   chat.innerHTML='';
   message('Entreprise sélectionnée : '+project.project.name+
     '. Je lance automatiquement la première proposition de site.','assistant');
   await startProDraft(false);
  }else if(project.project?.project_kind==='pro' &&
           ['failed','claimed'].includes(initial.status)){
   chat.innerHTML='';
   rows.forEach(row=>message(row.text,row.role==='user'?'user':'assistant'));
   message(initial.status==='failed'
      ?'La création automatique a rencontré un problème : '+(initial.error||'moteur indisponible')+
       '\nLe projet Pro est enregistré. Tu peux relancer la première maquette.'
      :'La première génération a déjà été demandée. Si elle semble interrompue, '+
       'rouvre le projet après quelques minutes ou demande à relancer la maquette.',
      'assistant',['Relancer la maquette']);
   stage='ready';
  }else if(rows.length){
   chat.innerHTML='';
   rows.forEach(row=>message(row.text,row.role==='user'?'user':'assistant'));
   message('Je suis prêt à continuer ce projet. Décris la prochaine modification ou écris « questionnaire » pour clarifier tes attentes.','assistant',['Améliore le rendu','Questionnaire','Publier le site']);
   stage='ready';
  }else{
   chat.innerHTML='';
   message('Bonjour ! Décris-moi le site que tu imagines. Je peux créer aussi bien un site simple qu’une expérience 3D premium avec un véritable site complet à droite.\n\nJe peux te guider avec un questionnaire précis. Veux-tu commencer par quelques questions, ou préfères-tu décrire directement ton idée ?','assistant',['Commencer le questionnaire','Créer un site vitrine simple','Créer un site 3D cinématique']);
   stage='welcome';
  }
  const unfinished=project.project?.generation_plan;
  if(unfinished && !unfinished.ready && unfinished.questions?.length){
   renderBriefQuestion({plan:unfinished,question:unfinished.questions[unfinished.index]});
  }
 }catch(error){message('Impossible de charger tes projets : '+error.message);}
}
initialize();
