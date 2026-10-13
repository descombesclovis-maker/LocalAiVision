const $=s=>document.querySelector(s);
let current=null,selectedFile='index.html',selectMode=false,selectedElement=null;
let undoStack=[],redoStack=[],codeSaveTimer=null,integrationState={};
const api=async(url,opt)=>{const r=await fetch(url,opt);let d={};try{d=await r.json()}catch{}if(!r.ok||d.error)throw new Error(d.error||('Erreur HTTP '+r.status));return d};
const post=(url,data)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(t){const e=$('#lawToast');e.textContent=t;e.classList.add('show');setTimeout(()=>e.classList.remove('show'),2600)}
function snapshotClient(){if(current?.files){undoStack.push(JSON.parse(JSON.stringify(current.files)));if(undoStack.length>20)undoStack.shift();redoStack=[]}}
async function replaceFiles(files){const d=await post('/api/web/project/replace',{id:current.project.id,files});current.files=d.files;current.versions=d.versions||current.versions;renderProject();refreshPreview()}
async function undo(){if(!undoStack.length)return toast('Rien à annuler.');redoStack.push(JSON.parse(JSON.stringify(current.files)));await replaceFiles(undoStack.pop())}
async function redo(){if(!redoStack.length)return toast('Rien à rétablir.');undoStack.push(JSON.parse(JSON.stringify(current.files)));const f=redoStack.pop();await replaceFiles(f)}
function refreshPreview(){if(!current)return;const frame=$('#lawPreview');frame.src='/web-preview/'+encodeURIComponent(current.project.id)+'/index.html?t='+Date.now();$('#lawPreviewTitle').textContent=current.project.name}
async function renameProject(){
 if(!current)return;const name=prompt('Nouveau nom du projet',current.project.name||'');if(!name)return;
 current=await post('/api/web/project/rename',{id:current.project.id,name});await loadProjects(current.project.id);toast('Projet renommé.');
}
async function duplicateProject(){
 if(!current)return;const name=prompt('Nom de la copie',(current.project.name||'Projet')+' — copie');if(!name)return;
 const copy=await post('/api/web/project/duplicate',{id:current.project.id,name});await loadProjects(copy.project.id);toast('Projet dupliqué.');
}
async function deleteProject(){
 if(!current)return;if(!confirm('Supprimer définitivement ce projet LocalAiWeb ?'))return;
 await post('/api/web/project/delete',{id:current.project.id});current=null;await loadProjects();toast('Projet supprimé.');
}
async function loadProjects(selectId){const d=await api('/api/web/projects');const s=$('#lawProjects');s.innerHTML='';for(const p of d.projects){const o=document.createElement('option');o.value=p.id;o.textContent=p.name;s.appendChild(o)}if(!d.projects.length){const n=await post('/api/web/project/create',{name:'Mon premier site'});await loadProjects(n.project.id);return}const id=selectId||d.projects[0].id;s.value=id;await loadProject(id)}
async function loadProject(id){current=await api('/api/web/project?id='+encodeURIComponent(id));selectedFile=current.files['index.html']?'index.html':Object.keys(current.files)[0];undoStack=[];redoStack=[];renderProject();renderSettings();renderDeployment();renderChatHistory();refreshPreview();runQuality(false).catch(()=>{})}
function renderProject(){if(!current)return;
 const ft=$('#lawFileTree');ft.innerHTML='';Object.keys(current.files).sort().forEach(path=>{const b=document.createElement('button');b.className='file-item'+(path===selectedFile?' active':'');b.textContent=path;b.onclick=()=>openCode(path);ft.appendChild(b)});
 const assets=$('#lawAssets');assets.innerHTML='';(current.assets||[]).forEach(a=>{const d=document.createElement('div');d.className='asset-card';const isImage=/\.(png|jpe?g|webp|gif|svg)$/i.test(a.path);d.innerHTML=(isImage?'<img src="/web-preview/'+encodeURIComponent(current.project.id)+'/'+a.path.split('/').map(encodeURIComponent).join('/')+'" alt="">':'')+'<div><b>'+esc(a.path)+'</b><span>'+Math.round(a.size/1024)+' Ko</span></div>';assets.appendChild(d)});if(!(current.assets||[]).length)assets.innerHTML='<div class="asset-card">Aucun asset. Ajoute logos, captures, photos ou exports Figma.</div>';
 const versions=$('#lawVersions');versions.innerHTML='';(current.versions||[]).forEach(v=>{const d=document.createElement('div');d.className='version-card';d.innerHTML='<b>'+esc(v.label||'Version')+'</b><span>'+new Date((v.created_at||0)*1000).toLocaleString()+'</span><button>Restaurer</button>';d.querySelector('button').onclick=()=>restoreVersion(v.id);versions.appendChild(d)});if(!(current.versions||[]).length)versions.innerHTML='<div class="version-card">Les versions apparaîtront après la première modification.</div>';
}
function showPanel(name){document.querySelectorAll('.rail-tab').forEach(b=>b.classList.toggle('active',b.dataset.panel===name));for(const n of ['files','assets','versions','services'])$('#law'+n[0].toUpperCase()+n.slice(1)+'Panel').classList.toggle('hidden',n!==name)}
async function createFile(){
 if(!current)return;const path=prompt('Chemin du nouveau fichier','components/section.js');if(!path)return;
 snapshotClient();
 try{const d=await post('/api/web/file/save',{id:current.project.id,path,content:''});current.files=d.files;current.versions=d.versions||[];selectedFile=path;renderProject();openCode(path);toast('Fichier créé.')}catch(e){toast(e.message)}
}
async function renameFile(){
 if(!current||!selectedFile)return;const next=prompt('Nouveau chemin',selectedFile);if(!next||next===selectedFile)return;
 try{current=await post('/api/web/file/rename',{id:current.project.id,old_path:selectedFile,new_path:next});selectedFile=next;renderProject();toast('Fichier renommé.')}catch(e){toast(e.message)}
}
async function deleteFile(){
 if(!current||!selectedFile)return;if(!confirm('Supprimer '+selectedFile+' ?'))return;
 try{current=await post('/api/web/file/delete',{id:current.project.id,path:selectedFile});selectedFile=current.files['index.html']?'index.html':Object.keys(current.files)[0]||'';renderProject();$('#lawCodePanel').classList.add('hidden');refreshPreview();toast('Fichier supprimé.')}catch(e){toast(e.message)}
}
function openCode(path){selectedFile=path;$('#lawCodePath').textContent=path;$('#lawCode').value=current.files[path]||'';$('#lawCodeState').textContent='Enregistré';$('#lawCodePanel').classList.remove('hidden');renderProject()}
async function autosaveCode(){
 if(!current||$('#lawCodePanel').classList.contains('hidden')||!selectedFile)return;
 const state=$('#lawCodeState');if(state)state.textContent='Enregistrement…';
 try{const d=await post('/api/web/file/save',{id:current.project.id,path:selectedFile,content:$('#lawCode').value,snapshot:false});current.files=d.files;current.versions=d.versions||current.versions;if(state)state.textContent='Enregistré';refreshPreview()}catch(e){if(state)state.textContent='Erreur';toast('Autosave : '+e.message)}
}
async function saveCode(){snapshotClient();const d=await post('/api/web/file/save',{id:current.project.id,path:selectedFile,content:$('#lawCode').value});current.files=d.files;current.versions=d.versions||[];$('#lawCodePanel').classList.add('hidden');renderProject();refreshPreview();toast('Fichier enregistré.')}
function addChat(text,role='agent'){const d=document.createElement('div');d.className='agent-message'+(role==='user'?' user':'');d.textContent=text;$('#lawChat').appendChild(d);$('#lawChat').scrollTop=$('#lawChat').scrollHeight}
function renderChatHistory(){
 const box=$('#lawChat');box.innerHTML='';
 const rows=current?.chat||[];
 if(!rows.length){box.innerHTML='<div class="agent-message"><b>Que veux-tu construire ?</b><p>Décris un site, une app ou une modification. Je travaille directement dans les fichiers et l’aperçu se met à jour.</p></div>';return}
 rows.forEach(x=>addChat(x.text,x.role==='user'?'user':'agent'));
}

async function generate(){const p=$('#lawPrompt'),text=p.value.trim();if(!text||!current)return;p.value='';addChat(text,'user');const btn=$('#lawGenerate');btn.disabled=true;btn.textContent='Construction…';snapshotClient();try{const d=await post('/api/web/generate',{id:current.project.id,prompt:text});current.files=d.files;current.project=d.project;current.versions=d.versions||[];current.assets=d.assets||current.assets||[];current.chat=d.chat||current.chat||[];addChat((d.provider==='codex'?'Codex · ':'Local · ')+(d.summary||'Modification terminée.'));renderProject();refreshPreview();toast('Projet mis à jour.')}catch(e){addChat('Erreur : '+e.message);toast(e.message)}finally{btn.disabled=false;btn.innerHTML='Construire <span>↑</span>'}}
async function restoreVersion(id){if(!confirm('Restaurer cette version ?'))return;snapshotClient();current=await post('/api/web/version/restore',{id:current.project.id,version_id:id});renderProject();refreshPreview();toast('Version restaurée.')}
function setViewport(v){$('#lawPreviewStage').className='preview-stage '+v;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===v))}
function setupVisualEditing(){const frame=$('#lawPreview');frame.addEventListener('load',()=>{const dot=$('#lawRuntimeDot'),txt=$('#lawRuntimeText');if(dot)dot.classList.remove('error');if(txt)txt.textContent='runtime OK';try{frame.contentWindow.addEventListener('error',e=>{if(dot)dot.classList.add('error');if(txt)txt.textContent='erreur JS';toast('Erreur dans l’aperçu : '+(e.message||'JavaScript'))});frame.contentWindow.addEventListener('unhandledrejection',()=>{if(dot)dot.classList.add('error');if(txt)txt.textContent='promesse rejetée'})}catch{}if(selectMode)wireFrame()})}
function wireFrame(){const doc=$('#lawPreview').contentDocument;if(!doc)return;doc.querySelectorAll('body *').forEach(el=>{el.addEventListener('click',visualPick,true)})}
function visualPick(e){if(!selectMode)return;e.preventDefault();e.stopPropagation();if(selectedElement)selectedElement.style.outline='';selectedElement=e.currentTarget;selectedElement.style.outline='2px solid #8b5cf6';$('#lawSelectedTag').textContent=selectedElement.tagName.toLowerCase();$('#lawElementText').value=selectedElement.children.length?'':(selectedElement.textContent||'');const cs=getComputedStyle(selectedElement);$('#lawElementColor').value=rgbToHex(cs.color);$('#lawElementBg').value=rgbToHex(cs.backgroundColor);$('#lawElementSize').value=parseInt(cs.fontSize)||16;$('#lawElementWeight').value=parseInt(cs.fontWeight)||400;$('#lawElementAlign').value=['left','center','right','justify'].includes(cs.textAlign)?cs.textAlign:'';$('#lawElementPadding').value=cs.padding||'';$('#lawElementMargin').value=cs.margin||'';$('#lawElementRadius').value=parseInt(cs.borderRadius)||0;$('#lawElementOpacity').value=parseFloat(cs.opacity)||1;$('#lawInspector').classList.remove('hidden')}
function rgbToHex(v){const m=String(v).match(/\d+/g);if(!m||m.length<3)return'#000000';return'#'+m.slice(0,3).map(x=>Number(x).toString(16).padStart(2,'0')).join('')}
async function applyVisual(){if(!selectedElement)return;const t=$('#lawElementText').value;if(t&&!selectedElement.children.length)selectedElement.textContent=t;selectedElement.style.color=$('#lawElementColor').value;selectedElement.style.backgroundColor=$('#lawElementBg').value;selectedElement.style.fontSize=$('#lawElementSize').value+'px';selectedElement.style.fontWeight=$('#lawElementWeight').value||'';selectedElement.style.textAlign=$('#lawElementAlign').value||'';selectedElement.style.padding=$('#lawElementPadding').value.trim();selectedElement.style.margin=$('#lawElementMargin').value.trim();selectedElement.style.borderRadius=$('#lawElementRadius').value+'px';selectedElement.style.opacity=$('#lawElementOpacity').value||'1';selectedElement.style.outline='';snapshotClient();const doc=$('#lawPreview').contentDocument;const html='<!doctype html>\n'+doc.documentElement.outerHTML;const d=await post('/api/web/file/save',{id:current.project.id,path:'index.html',content:html});current.files=d.files;current.versions=d.versions||[];$('#lawInspector').classList.add('hidden');selectedElement=null;renderProject();refreshPreview();toast('Modification visuelle enregistrée.')}
function toggleVisual(){selectMode=!selectMode;$('#lawSelectMode').classList.toggle('active',selectMode);$('#lawSelectMode').textContent=selectMode?'● Édition active':'◎ Édition visuelle';if(selectMode)wireFrame();else{$('#lawInspector').classList.add('hidden');selectedElement=null}}
async function generateAsset(){
 if(!current)return;const prompt=$('#lawAssetPrompt').value.trim();if(!prompt)return toast('Décris l’image à générer.');
 const btn=$('#lawGenerateAsset');btn.disabled=true;btn.textContent='Génération…';
 try{const d=await post('/api/web/asset/generate',{id:current.project.id,prompt});$('#lawAssetPrompt').value='';current=await api('/api/web/project?id='+encodeURIComponent(current.project.id));renderProject();toast('Asset généré : '+d.path)}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='✦ Générer'}
}
async function addAsset(file){if(!file||!current)return;const r=new FileReader();r.onload=async()=>{try{await post('/api/web/asset',{id:current.project.id,name:file.name,data:r.result});current=await api('/api/web/project?id='+encodeURIComponent(current.project.id));renderProject();toast('Asset ajouté : '+file.name)}catch(e){toast(e.message)}};r.readAsDataURL(file)}
function integration(name){
 const prompts={
  database:"Ajoute un backend Supabase professionnel à ce projet : schéma SQL versionné dans supabase/migrations, tables nécessaires, contraintes, index, politiques RLS sécurisées et accès côté client uniquement avec les variables publiques. Ne mets aucun secret dans le code client.",
  auth:"Ajoute Supabase Auth avec inscription, connexion, déconnexion, récupération de mot de passe, états de chargement/erreur, routes ou écrans protégés et rôles si le projet le nécessite. Utilise des politiques RLS cohérentes.",
  payments:"Ajoute Stripe de manière production-ready. Les clés secrètes doivent rester exclusivement côté serveur ou dans les variables d’environnement du déploiement. Ajoute checkout, états succès/annulation et webhook serveur si nécessaire, sans secret côté navigateur.",
  api:"Ajoute les endpoints API nécessaires au projet avec validation des entrées, réponses d’erreur propres, séparation client/serveur et variables d’environnement pour les secrets.",
  storage:"Ajoute une gestion de fichiers avec Supabase Storage : upload, validation des types et tailles, aperçu, suppression, permissions et politiques adaptées.",
  realtime:"Ajoute Supabase Realtime uniquement là où cela améliore réellement l’application, avec abonnement/désabonnement propre et état de reconnexion.",
  analytics:"Ajoute une couche analytics respectueuse de la vie privée, compatible avec le déploiement Vercel, sans casser les performances ni le consentement requis.",
  ai:"Ajoute les fonctionnalités IA demandées en réutilisant l’architecture du projet et en gardant les secrets côté serveur. Prévois états loading, erreurs, quotas et fallback.",
  integrations:"Prépare une architecture d’intégrations tierces robuste : modules séparés, variables d’environnement documentées dans .env.example, erreurs explicites et webhooks idempotents.",
  domains:"Prépare ce site pour un domaine personnalisé : URLs canoniques, meta Open Graph, favicon, robots.txt, sitemap.xml et liens absolus configurables par variable publique."
 };
 if(prompts[name]){$('#lawPrompt').value=prompts[name];$('#lawPrompt').focus();toast('Instruction '+name+' préparée dans le chat.');return}
 toast('Service inconnu.')
}
async function connectIntegration(provider){
 try{const d=await post('/api/web/integrations/connect',{provider,id:current?.project?.id||null});toast(d.message||('Connexion '+provider+' ouverte.'));setTimeout(()=>refreshIntegrations(),2500)}catch(e){toast(e.message)}
}
async function refreshIntegrations(){
 try{
  const d=await post('/api/web/integrations/status',{});integrationState=d.integrations||{};
  const box=$('#lawIntegrationStatus');box.innerHTML='';
  const order=['github','vercel','supabase','codex','git','node','npm'];
  for(const name of order){const s=d.integrations?.[name];if(!s)continue;const row=document.createElement('div');row.className='integration-row '+(s.ready?'ready':'off');row.innerHTML='<span></span><b>'+name+'</b><small>'+(s.ready?'prêt':(s.installed?'installé, connexion requise':'non installé'))+'</small>';box.appendChild(row)}
  const state=$('#lawPublishState');if(state&&!current?.project?.deployment?.production_url)state.textContent=integrationState.vercel?.ready?'Vercel':'connexion requise';
 }catch(e){toast('Intégrations : '+e.message)}
}
function renderDeployment(){
 if(!current)return;const d=current.project.deployment||{};
 $('#lawGithubRepo').value=d.github_repo||'';$('#lawGithubBranch').value=d.github_branch||'main';$('#lawGithubPrivate').checked=d.github_private!==false;$('#lawSupabaseRef').value=d.supabase_ref||'';$('#lawDomain').value=d.custom_domain||'';
 const live=$('#lawOpenLive'),state=$('#lawPublishState');if(live){live.classList.toggle('hidden',!d.production_url);live.dataset.url=d.production_url||''}if(state)state.textContent=d.production_url?'mettre à jour':'Vercel';
}
async function persistDeployment(){
 if(!current)return;
 const d={github_repo:$('#lawGithubRepo').value.trim(),github_branch:$('#lawGithubBranch').value.trim()||'main',github_private:$('#lawGithubPrivate').checked,supabase_ref:$('#lawSupabaseRef').value.trim(),vercel_target:'production'};
 current=await post('/api/web/deployment',{id:current.project.id,deployment:d});return d;
}
async function publishGithub(){
 if(!current)return;if(!integrationState.github?.ready){showPanel('services');toast('Connecte GitHub avant la synchronisation.');return}await persistDeployment();const repo=$('#lawGithubRepo').value.trim();if(!repo)return toast('Indique le dépôt GitHub au format utilisateur/dépôt.');
 const btn=$('#lawPublishGithub');btn.disabled=true;btn.textContent='Synchronisation…';
 try{const d=await post('/api/web/github/publish',{id:current.project.id,repo,branch:$('#lawGithubBranch').value.trim()||'main',private:$('#lawGithubPrivate').checked});toast('GitHub synchronisé : '+d.repo);if(d.url)window.open(d.url,'_blank')}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Synchroniser sur GitHub'}
}
async function pullGithub(){
 if(!current)return;const btn=$('#lawPullGithub');btn.disabled=true;btn.textContent='Récupération…';
 try{const d=await post('/api/web/github/pull',{id:current.project.id,branch:$('#lawGithubBranch').value.trim()||'main'});current=d;renderProject();renderDeployment();refreshPreview();toast('Projet synchronisé depuis GitHub.')}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Récupérer depuis GitHub'}
}
async function addDomain(){
 if(!current)return;const domain=$('#lawDomain').value.trim();if(!domain)return toast('Indique un nom de domaine.');
 const btn=$('#lawAddDomain');btn.disabled=true;btn.textContent='Ajout du domaine…';
 try{const d=await post('/api/web/vercel/domain',{id:current.project.id,domain});current=d;renderDeployment();toast('Domaine transmis à Vercel : '+domain)}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Ajouter le domaine via Vercel'}
}
async function initSupabase(){
 if(!current)return;const btn=$('#lawInitSupabase');btn.disabled=true;btn.textContent='Initialisation…';
 try{await post('/api/web/supabase/init',{id:current.project.id});toast('Supabase initialisé dans le projet.')}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Initialiser Supabase'}
}
async function linkSupabase(){
 if(!current)return;if(!integrationState.supabase?.ready){showPanel('services');toast('Connecte Supabase avant de lier le projet.');return}await persistDeployment();const ref=$('#lawSupabaseRef').value.trim();if(!ref)return toast('Indique la Project Ref Supabase.');
 const btn=$('#lawLinkSupabase');btn.disabled=true;btn.textContent='Liaison…';
 try{await post('/api/web/supabase/link',{id:current.project.id,project_ref:ref});toast('Projet Supabase lié.')}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Lier le projet Supabase'}
}
async function pushSupabase(){
 if(!current)return;const btn=$('#lawPushSupabase');btn.disabled=true;btn.textContent='Migration…';
 try{await post('/api/web/supabase/push',{id:current.project.id});toast('Migrations Supabase appliquées.')}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Pousser les migrations DB'}
}
async function deployPreview(){
 if(!current)return;if(!integrationState.vercel?.ready){showPanel('services');toast('Connecte Vercel avant de créer un aperçu.');return}await persistDeployment();
 const btn=$('#lawDeployPreview');btn.disabled=true;btn.textContent='Création de l’aperçu…';
 try{const d=await post('/api/web/vercel/publish',{id:current.project.id,production:false});current=d;renderDeployment();const url=d.deployment_result?.url||d.project?.deployment?.preview_url||'';toast(url?'Aperçu Vercel prêt : '+url:'Aperçu Vercel créé.');if(url)window.open(url,'_blank')}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Créer un aperçu Vercel'}
}
async function deployVercel(){
 if(!current)return;if(!integrationState.vercel?.ready){showPanel('services');toast('Connecte Vercel avant de publier.');return}await persistDeployment();const quality=await runQuality(false);if(quality&&!quality.ok&&!confirm('Le Quality Gate n’est pas encore au vert. Déployer quand même ?'))return;
 const btn=$('#lawDeployVercel'),top=$('#lawPublish');btn.disabled=true;top.disabled=true;btn.textContent='Déploiement…';
 try{const d=await post('/api/web/vercel/publish',{id:current.project.id,production:true});current=d;renderProject();renderDeployment();const url=d.deployment_result?.url||d.project?.deployment?.production_url||'';toast(url?'Déployé : '+url:'Déploiement Vercel terminé.');if(url)window.open(url,'_blank')}catch(e){toast(e.message)}finally{btn.disabled=false;top.disabled=false;btn.textContent='Déployer sur Vercel'}
}
async function applyCodex(){
 if(!current)return;if(!integrationState.codex?.ready){showPanel('services');toast('Connecte ChatGPT / Codex avant d’utiliser ce moteur.');return}const text=$('#lawPrompt').value.trim();if(!text)return toast('Écris d’abord la modification à confier à Codex.');
 const btn=$('#lawUseCodex');btn.disabled=true;btn.textContent='Codex travaille…';snapshotClient();
 try{const d=await post('/api/web/codex/apply',{id:current.project.id,prompt:text});current=d;$('#lawPrompt').value='';renderProject();refreshPreview();addChat(d.codex?.summary||'Modification Codex terminée.');toast('Projet mis à jour avec Codex.')}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Appliquer la prochaine demande avec Codex'}
}
function renderSettings(){if(!current)return;const s=current.project.settings||{};$('#lawSettingQuality').value=s.quality||'premium';$('#lawSettingLanguage').value=s.language||'fr';$('#lawSettingAiProvider').value=s.ai_provider||'auto';$('#lawSettingResponsive').checked=s.responsive!==false;$('#lawSettingAccessibility').checked=s.accessibility!==false;$('#lawSettingSeo').checked=s.seo!==false;$('#lawSettingPerformance').checked=s.performance!==false;$('#lawSettingMicro').checked=s.micro_interactions!==false;$('#lawSettingMotion').checked=s.reduced_motion!==false;$('#lawSettingSemantic').checked=s.semantic_html!==false}
function projectSettings(){return{quality:$('#lawSettingQuality').value,language:$('#lawSettingLanguage').value.trim()||'fr',ai_provider:$('#lawSettingAiProvider').value,responsive:$('#lawSettingResponsive').checked,accessibility:$('#lawSettingAccessibility').checked,seo:$('#lawSettingSeo').checked,performance:$('#lawSettingPerformance').checked,micro_interactions:$('#lawSettingMicro').checked,reduced_motion:$('#lawSettingMotion').checked,semantic_html:$('#lawSettingSemantic').checked}}
async function saveSettings(){if(!current)return;current=await post('/api/web/settings',{id:current.project.id,settings:projectSettings()});renderSettings();$('#lawSettingsModal').classList.add('hidden');toast('Réglages enregistrés.');runQuality(false).catch(()=>{})}
async function runQuality(show=true){if(!current)return null;const d=await api('/api/web/preflight?id='+encodeURIComponent(current.project.id));$('#lawQualityScore').textContent=d.score+'/100';$('#lawQuality').classList.toggle('quality-ok',!!d.ok);$('#lawQuality').classList.toggle('quality-bad',!d.ok);const box=$('#lawQualityReport');box.innerHTML='<div class="quality-score"><b>'+d.score+'/100</b><span>'+(d.ok?'Prêt pour publication':'Corrections recommandées')+'</span></div>'+d.checks.map(x=>'<div class="quality-line '+(x.ok?'ok':'bad')+'"><span>'+(x.ok?'✓':'!')+'</span><b>'+esc(x.label)+'</b></div>').join('');if(show){box.classList.remove('hidden');$('#lawSettingsModal').classList.remove('hidden')}return d}
function handleAssetPaste(e){
 const items=[...(e.clipboardData?.items||[])];const img=items.find(x=>x.kind==='file'&&x.type.startsWith('image/'));
 if(!img)return;const file=img.getAsFile();if(file){e.preventDefault();addAsset(file);toast('Image collée dans les assets.')}
}
function handleAssetDrop(e){
 e.preventDefault();const file=[...(e.dataTransfer?.files||[])].find(x=>x.type.startsWith('image/'));
 if(file)addAsset(file);
}
function startVoice(){
 const Ctor=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!Ctor)return toast('La reconnaissance vocale n’est pas disponible dans ce moteur WebView.');
 const rec=new Ctor();rec.lang='fr-FR';rec.interimResults=false;rec.maxAlternatives=1;
 const btn=$('#lawMic');btn.disabled=true;btn.textContent='Écoute…';
 rec.onresult=e=>{const text=e.results?.[0]?.[0]?.transcript||'';if(text)$('#lawPrompt').value=($('#lawPrompt').value.trim()+' '+text).trim()};
 rec.onerror=()=>toast('La dictée vocale a échoué.');
 rec.onend=()=>{btn.disabled=false;btn.textContent='◉ Voix'};
 rec.start();
}
function setup(){
 $('#lawBack').onclick=()=>location.href='/';$('#lawSettings').onclick=()=>{$('#lawSettingsModal').classList.remove('hidden');renderSettings()};$('#lawRefreshIntegrations').onclick=refreshIntegrations;document.querySelectorAll('[data-connect]').forEach(b=>b.onclick=()=>connectIntegration(b.dataset.connect));$('#lawPublishGithub').onclick=publishGithub;$('#lawPullGithub').onclick=pullGithub;$('#lawInitSupabase').onclick=initSupabase;$('#lawLinkSupabase').onclick=linkSupabase;$('#lawPushSupabase').onclick=pushSupabase;$('#lawDeployPreview').onclick=deployPreview;$('#lawDeployVercel').onclick=deployVercel;$('#lawAddDomain').onclick=addDomain;$('#lawUseCodex').onclick=applyCodex;$('#lawCloseSettings').onclick=()=>$('#lawSettingsModal').classList.add('hidden');$('#lawSaveSettings').onclick=saveSettings;$('#lawRunQuality').onclick=()=>runQuality(true);$('#lawQuality').onclick=()=>runQuality(true);
 $('#lawNewProject').onclick=async()=>{const name=prompt('Nom du projet','Nouveau site');if(!name)return;const d=await post('/api/web/project/create',{name});await loadProjects(d.project.id)};$('#lawRenameProject').onclick=renameProject;$('#lawDuplicateProject').onclick=duplicateProject;$('#lawDeleteProject').onclick=deleteProject;
 $('#lawProjects').onchange=e=>loadProject(e.target.value);$('#lawNewFile').onclick=createFile;$('#lawRenameFile').onclick=renameFile;$('#lawDeleteFile').onclick=deleteFile;
 document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setViewport(b.dataset.view));
 document.querySelectorAll('.rail-tab').forEach(b=>b.onclick=()=>showPanel(b.dataset.panel));
 document.querySelectorAll('[data-service]').forEach(b=>b.onclick=()=>integration(b.dataset.service));
 document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>{$('#lawPrompt').value=b.dataset.prompt;generate()});
 $('#lawGenerate').onclick=generate;$('#lawMic').onclick=startVoice;
 $('#lawPrompt').onkeydown=e=>{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();generate()}};$('#lawPrompt').addEventListener('paste',handleAssetPaste);const composer=$('.agent-composer');composer.addEventListener('dragover',e=>{e.preventDefault();composer.classList.add('drop-ready')});composer.addEventListener('dragleave',()=>composer.classList.remove('drop-ready'));composer.addEventListener('drop',e=>{composer.classList.remove('drop-ready');handleAssetDrop(e)});
 $('#lawRefresh').onclick=refreshPreview;
 $('#lawOpenPreview').onclick=()=>window.open('/web-preview/'+current.project.id+'/index.html','_blank');
 $('#lawSelectMode').onclick=toggleVisual;
 $('#lawApplyVisual').onclick=applyVisual;
 $('#lawSaveCode').onclick=saveCode;$('#lawCode').addEventListener('input',()=>{const s=$('#lawCodeState');if(s)s.textContent='Modifié';clearTimeout(codeSaveTimer);codeSaveTimer=setTimeout(autosaveCode,1200)});
 $('#lawCloseCode').onclick=()=>$('#lawCodePanel').classList.add('hidden');
 $('#lawUndo').onclick=undo;$('#lawRedo').onclick=redo;
 $('#lawExport').onclick=()=>{if(current)location.href='/api/web/export?id='+encodeURIComponent(current.project.id)};
 $('#lawGithub').onclick=()=>{showPanel('services');$('#lawGithubRepo')?.focus()};$('#lawPublish').onclick=deployVercel;$('#lawOpenLive').onclick=()=>{const u=$('#lawOpenLive').dataset.url;if(u)window.open(u,'_blank')};
 $('#lawAssetAdd').onclick=()=>$('#lawAssetInput').click();$('#lawAttach').onclick=()=>$('#lawAssetInput').click();$('#lawGenerateAsset').onclick=generateAsset;
 $('#lawAssetInput').onchange=e=>{const f=e.target.files?.[0];if(f)addAsset(f);e.target.value=''};
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();if(!$('#lawCodePanel').classList.contains('hidden'))saveCode()}if(e.key==='Escape'){$('#lawSettingsModal').classList.add('hidden');$('#lawInspector').classList.add('hidden')}});
 setupVisualEditing();refreshIntegrations();loadProjects().catch(e=>toast(e.message));
}
setup();