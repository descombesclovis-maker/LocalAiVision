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
let project=null,busy=false,viewport='desktop',stage='welcome',brief={},questionIndex=0;
const questions=[
  {key:'goal',label:'Quel est l’objectif principal de ton site ?',choices:['Présenter mon activité','Vendre des produits','Recevoir des réservations','Créer une application','Présenter mon travail','Autre projet'],hint:'Indique le type de site et le résultat attendu.'},
  {key:'audience',label:'À qui s’adresse ce site ?',choices:['Grand public','Clients professionnels','Clients locaux','Passionnés / communauté','Membres inscrits','Tous les visiteurs'],hint:'Précise ton public, sa langue et ses besoins.'},
  {key:'style',label:'Quelle direction visuelle souhaites-tu ?',choices:['Minimaliste et élégant','Premium / luxe','3D cinématique spectaculaire','Moderne et coloré','Classique professionnel','Créativité libre'],hint:'Tu peux demander un rendu très simple ou une expérience 3D digne d’une publicité.'},
  {key:'pages',label:'Quelles pages et fonctionnalités faut-il prévoir ?',choices:['Accueil + contact','Plusieurs pages complètes','Boutique + panier','Réservation en ligne','Espace client / comptes','Une page immersive'],hint:'Décris les sections, menus, interactions ou services spécifiques.'},
  {key:'brand',label:'Quel nom, quelles couleurs et quels contenus utiliser ?',choices:['J’ai déjà une marque','Je veux une identité à créer','Utilise du contenu de démonstration','Je fournirai les textes ensuite'],hint:'Écris le nom, le slogan, les couleurs, les références et les liens vers tes ressources.'},
  {key:'interactions',label:'Quelles interactions souhaites-tu proposer ?',choices:['Navigation fluide','Formulaires et contact','Panier et paiement réel','Animation au défilement','Visualisation 3D de produits','Application interactive'],hint:'Précise exactement ce que les visiteurs devront pouvoir faire.'},
  {key:'navigation',label:'Comment veux-tu organiser la navigation ?',choices:['Menu simple','Plusieurs rubriques','Parcours en une page','Défilement narratif','Catalogue filtrable','L’IA décide selon le projet'],hint:'Donne le nombre approximatif de pages et leur organisation.'},
  {key:'visuals',label:'Quels médias et références graphiques utiliser ?',choices:['Photos réalistes','Objets 3D GLB','Illustrations sur mesure','Vidéos et animations','Typographie uniquement','Un mélange de médias'],hint:'Ajoute ici des URLs de ressources et de sites servant de référence.'},
  {key:'functionality',label:'Quelles fonctions devront réellement marcher ?',choices:['Formulaire de contact','Réservation en ligne','Commande et paiement','Compte client','Carte interactive','Pas de fonctions avancées'],hint:'Explique le comportement attendu de chaque fonctionnalité. Les services externes devront être connectés.'},
  {key:'publishing',label:'As-tu déjà un domaine et un hébergement ?',choices:['Publier via Vercel','J’ai déjà un nom de domaine','Je veux choisir plus tard','Je veux d’abord tester localement'],hint:'Indique les services et comptes déjà configurés, si tu en as.'},
  {key:'priority',label:'Qu’est-ce qui compte le plus ?',choices:['Impact visuel exceptionnel','Simplicité maximale','Vitesse et SEO','Animations et 3D','Conversion et ventes','Équilibre entre tout'],hint:'Dis-moi ton niveau d’exigence, tes animations souhaitées et tes contraintes.'}
];
const chat=$('#lawChat'),prompt=$('#lawPrompt'),button=$('#lawGenerate');
function scrollBottom(){chat.scrollTop=chat.scrollHeight;}
function message(text,role='assistant',choices=[]){
 const item=document.createElement('article');item.className='message '+(role==='user'?'user':'assistant');
 if(role!=='user'){const name=document.createElement('div');name.className='message-author';name.textContent='LocalAiWeb';item.appendChild(name);}
 const textNode=document.createElement('p');textNode.textContent=String(text||'');item.appendChild(textNode);
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
function askQuestion(){
 if(questionIndex>=questions.length){stage='ready';message('Merci. J’ai de quoi construire une première version complète. Écris « créer maintenant » ou ajoute tes dernières précisions. Ensuite, je pourrai affiner absolument chaque section par tes messages.','assistant',['Créer maintenant','Ajouter des précisions']);return;}
 const q=questions[questionIndex];stage='questions';
 message('Question '+(questionIndex+1)+' / '+questions.length+' — '+q.label+'\n'+q.hint+'\nRéponds librement ou choisis une proposition. Tu peux aussi écrire « créer maintenant » à tout moment.','assistant',q.choices);
}
async function ensureProject(){
 if(project)return;
 const listing=await api('/api/web/projects');
 if(listing.projects?.length){project=await api('/api/web/project?id='+encodeURIComponent(listing.projects[0].id));}
 else{project=await api('/api/web/project/create',{name:'Mon site web'});}
 preview();
}
async function showProjects(){
 const d=await api('/api/web/projects');const projects=d.projects||[];
 if(!projects.length)return message('Aucun projet enregistré. Écris « nouveau site » pour commencer.');
 message('Tu as '+projects.length+' projet(s). Indique le nom de celui à ouvrir :\n'+projects.map((p,i)=>(i+1)+'. '+p.name).join('\n'),'assistant',projects.slice(0,8).map(x=>'Ouvrir '+x.name));
}
async function handleProjectOpen(text){
 const normalized=text.toLowerCase().replace(/^ouvrir\s+/i,'').trim();
 const d=await api('/api/web/projects');
 const match=d.projects?.find(p=>p.name.toLowerCase()===normalized);
 if(!match)return false;
 project=await api('/api/web/project?id='+encodeURIComponent(match.id));preview();
 brief={};stage='ready';message('Projet « '+project.project.name+' » ouvert. Dis-moi ce que tu veux modifier ; tu peux demander n’importe quelle page, section, animation, interaction ou fonctionnalité.');
 return true;
}
function projectBrief(){
 return questions.filter(q=>brief[q.key]).map(q=>q.label+'\n'+brief[q.key]).join('\n\n');
}
async function generate(text){
 await ensureProject();
 const needs3D=/\b(?:3d|webgl|three\.js|cin[eé]matique)\b/i.test(text+' '+(brief.style||'')+' '+(brief.visuals||''));
 if(needs3D && project.project.template!=='cinematic3d' &&
    (project.files?.['index.html']||'').includes('La prévisualisation devrait apparaitre ici.')){
   project=await api('/api/web/project/create',{name:'Mon expérience 3D',template:'cinematic3d'});
   preview();
 }
 setBusy(true,'Je crée ton site et prépare l’aperçu…');
 const id=project.project.id;
 const existingBrief=projectBrief();
 const instructions=existingBrief
  ?'BRIEF UTILISATEUR :\n'+existingBrief+'\n\nDERNIÈRE DEMANDE :\n'+text
  :text;
 message('Je prends en compte ta demande et construis le site complet. Je conserverai les fonctionnalités déjà créées et je te proposerai ensuite des améliorations ciblées.');
 try{
  const result=await api('/api/web/generate',{id,prompt:instructions});
  project=result;preview();
  stage='ready';
  const report=result.quality;
  const validated=report && report.ok;
  message((result.summary||'La version du site a été créée.')+
    '\n\nRegarde le résultat à droite. Tu peux maintenant demander une modification précise : couleur, texte, typographie, page, navigation, produit, animation, 3D, réservation ou autre fonctionnalité.'+
    (report&&!validated?'\nLe contrôle de qualité signale encore des points à corriger ; demande-moi de les améliorer.':''),
    'assistant',['Améliore le rendu visuel','Optimise téléphone et tablette','Ajoute des fonctionnalités','Publier le site']);
 }catch(error){message('Je n’ai pas pu appliquer cette modification : '+error.message+'\nLe projet existant est conservé. Précise la demande ou vérifie que le moteur IA est disponible.');}
 finally{setBusy(false);}
}
async function publish(){
 await ensureProject();
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
async function sendText(value){
 const text=String(value||prompt.value||'').trim();if(!text||busy)return;
 prompt.value='';message(text,'user');setBusy(true,'Je comprends ta demande…');
 try{
  const intent=detectIntent(text);
  if(intent==='new'){
   project=await api('/api/web/project/create',{name:'Mon nouveau site'});
   brief={};questionIndex=0;stage='welcome';preview();
   message('Nouveau projet créé. Décris ton site, même avec un seul paragraphe. Je détecterai les seules précisions manquantes avant de créer la première version.');return;
  }
  if(intent==='projects'){await showProjects();return;}
  if(/^ouvrir\s+/i.test(text)&&await handleProjectOpen(text))return;
  if(intent==='help'){
   message('Tout passe par ce chat. Décris ce que tu veux construire, réponds à mes questions et observe le site complet à droite. Tu peux modifier chaque élément par une phrase. Pour gérer tes sites, écris : « nouveau site », « mes projets », « publier le site » ou « télécharger le site ».');return;
  }
  if(intent==='guide'){brief={};questionIndex=0;askQuestion();return;}
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
  if(stage==='questions' && questionIndex<questions.length && !/^(?:modifie|remplace|corrige|ajoute|change)\b/i.test(text)){
   brief[questions[questionIndex].key]=text;questionIndex++;askQuestion();return;
  }
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
  if(rows.length){
   chat.innerHTML='';
   rows.slice(-24).forEach(row=>message(row.text,row.role==='user'?'user':'assistant'));
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
