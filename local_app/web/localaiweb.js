const $=s=>document.querySelector(s);
let current=null,selectedFile='index.html',selectMode=false,selectedElement=null;
let undoStack=[],redoStack=[];
const api=async(url,opt)=>{const r=await fetch(url,opt);let d={};try{d=await r.json()}catch{}if(!r.ok||d.error)throw new Error(d.error||('Erreur HTTP '+r.status));return d};
const post=(url,data)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(t){const e=$('#lawToast');e.textContent=t;e.classList.add('show');setTimeout(()=>e.classList.remove('show'),2600)}
function snapshotClient(){if(current?.files){undoStack.push(JSON.parse(JSON.stringify(current.files)));if(undoStack.length>20)undoStack.shift();redoStack=[]}}
async function replaceFiles(files){const d=await post('/api/web/project/replace',{id:current.project.id,files});current.files=d.files;current.versions=d.versions||current.versions;renderProject();refreshPreview()}
async function undo(){if(!undoStack.length)return toast('Rien à annuler.');redoStack.push(JSON.parse(JSON.stringify(current.files)));await replaceFiles(undoStack.pop())}
async function redo(){if(!redoStack.length)return toast('Rien à rétablir.');undoStack.push(JSON.parse(JSON.stringify(current.files)));const f=redoStack.pop();await replaceFiles(f)}
function refreshPreview(){if(!current)return;const frame=$('#lawPreview');frame.src='/web-preview/'+encodeURIComponent(current.project.id)+'/index.html?t='+Date.now();$('#lawPreviewTitle').textContent=current.project.name}
async function loadProjects(selectId){const d=await api('/api/web/projects');const s=$('#lawProjects');s.innerHTML='';for(const p of d.projects){const o=document.createElement('option');o.value=p.id;o.textContent=p.name;s.appendChild(o)}if(!d.projects.length){const n=await post('/api/web/project/create',{name:'Mon premier site'});await loadProjects(n.project.id);return}const id=selectId||d.projects[0].id;s.value=id;await loadProject(id)}
async function loadProject(id){current=await api('/api/web/project?id='+encodeURIComponent(id));selectedFile=current.files['index.html']?'index.html':Object.keys(current.files)[0];undoStack=[];redoStack=[];renderProject();refreshPreview()}
function renderProject(){if(!current)return;
 const ft=$('#lawFileTree');ft.innerHTML='';Object.keys(current.files).sort().forEach(path=>{const b=document.createElement('button');b.className='file-item'+(path===selectedFile?' active':'');b.textContent=path;b.onclick=()=>openCode(path);ft.appendChild(b)});
 const assets=$('#lawAssets');assets.innerHTML='';(current.assets||[]).forEach(a=>{const d=document.createElement('div');d.className='asset-card';d.innerHTML='<b>'+esc(a.path)+'</b><span>'+Math.round(a.size/1024)+' Ko</span>';assets.appendChild(d)});if(!(current.assets||[]).length)assets.innerHTML='<div class="asset-card">Aucun asset. Ajoute logos, captures, photos ou exports Figma.</div>';
 const versions=$('#lawVersions');versions.innerHTML='';(current.versions||[]).forEach(v=>{const d=document.createElement('div');d.className='version-card';d.innerHTML='<b>'+esc(v.label||'Version')+'</b><span>'+new Date((v.created_at||0)*1000).toLocaleString()+'</span><button>Restaurer</button>';d.querySelector('button').onclick=()=>restoreVersion(v.id);versions.appendChild(d)});if(!(current.versions||[]).length)versions.innerHTML='<div class="version-card">Les versions apparaîtront après la première modification.</div>';
}
function showPanel(name){document.querySelectorAll('.rail-tab').forEach(b=>b.classList.toggle('active',b.dataset.panel===name));for(const n of ['files','assets','versions','services'])$('#law'+n[0].toUpperCase()+n.slice(1)+'Panel').classList.toggle('hidden',n!==name)}
function openCode(path){selectedFile=path;$('#lawCodePath').textContent=path;$('#lawCode').value=current.files[path]||'';$('#lawCodePanel').classList.remove('hidden');renderProject()}
async function saveCode(){snapshotClient();const d=await post('/api/web/file/save',{id:current.project.id,path:selectedFile,content:$('#lawCode').value});current.files=d.files;current.versions=d.versions||[];$('#lawCodePanel').classList.add('hidden');renderProject();refreshPreview();toast('Fichier enregistré.')}
function addChat(text,role='agent'){const d=document.createElement('div');d.className='agent-message'+(role==='user'?' user':'');d.textContent=text;$('#lawChat').appendChild(d);$('#lawChat').scrollTop=$('#lawChat').scrollHeight}
async function generate(){const p=$('#lawPrompt'),text=p.value.trim();if(!text||!current)return;p.value='';addChat(text,'user');const btn=$('#lawGenerate');btn.disabled=true;btn.textContent='Construction…';snapshotClient();try{const d=await post('/api/web/generate',{id:current.project.id,prompt:text});current.files=d.files;current.project=d.project;current.versions=d.versions||[];addChat(d.summary||'Modification terminée.');renderProject();refreshPreview();toast('Projet mis à jour.')}catch(e){addChat('Erreur : '+e.message);toast(e.message)}finally{btn.disabled=false;btn.innerHTML='Construire <span>↑</span>'}}
async function restoreVersion(id){if(!confirm('Restaurer cette version ?'))return;snapshotClient();current=await post('/api/web/version/restore',{id:current.project.id,version_id:id});renderProject();refreshPreview();toast('Version restaurée.')}
function setViewport(v){$('#lawPreviewStage').className='preview-stage '+v;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===v))}
function setupVisualEditing(){const frame=$('#lawPreview');frame.addEventListener('load',()=>{if(selectMode)wireFrame()})}
function wireFrame(){const doc=$('#lawPreview').contentDocument;if(!doc)return;doc.querySelectorAll('body *').forEach(el=>{el.addEventListener('click',visualPick,true)})}
function visualPick(e){if(!selectMode)return;e.preventDefault();e.stopPropagation();if(selectedElement)selectedElement.style.outline='';selectedElement=e.currentTarget;selectedElement.style.outline='2px solid #8b5cf6';$('#lawSelectedTag').textContent=selectedElement.tagName.toLowerCase();$('#lawElementText').value=selectedElement.children.length?'':(selectedElement.textContent||'');const cs=getComputedStyle(selectedElement);$('#lawElementColor').value=rgbToHex(cs.color);$('#lawElementBg').value=rgbToHex(cs.backgroundColor);$('#lawElementSize').value=parseInt(cs.fontSize)||16;$('#lawElementRadius').value=parseInt(cs.borderRadius)||0;$('#lawInspector').classList.remove('hidden')}
function rgbToHex(v){const m=String(v).match(/\d+/g);if(!m||m.length<3)return'#000000';return'#'+m.slice(0,3).map(x=>Number(x).toString(16).padStart(2,'0')).join('')}
async function applyVisual(){if(!selectedElement)return;const t=$('#lawElementText').value;if(t&&!selectedElement.children.length)selectedElement.textContent=t;selectedElement.style.color=$('#lawElementColor').value;selectedElement.style.backgroundColor=$('#lawElementBg').value;selectedElement.style.fontSize=$('#lawElementSize').value+'px';selectedElement.style.borderRadius=$('#lawElementRadius').value+'px';selectedElement.style.outline='';snapshotClient();const doc=$('#lawPreview').contentDocument;const html='<!doctype html>\n'+doc.documentElement.outerHTML;const d=await post('/api/web/file/save',{id:current.project.id,path:'index.html',content:html});current.files=d.files;current.versions=d.versions||[];$('#lawInspector').classList.add('hidden');selectedElement=null;renderProject();refreshPreview();toast('Modification visuelle enregistrée.')}
function toggleVisual(){selectMode=!selectMode;$('#lawSelectMode').classList.toggle('active',selectMode);$('#lawSelectMode').textContent=selectMode?'● Édition active':'◎ Édition visuelle';if(selectMode)wireFrame();else{$('#lawInspector').classList.add('hidden');selectedElement=null}}
async function addAsset(file){if(!file||!current)return;const r=new FileReader();r.onload=async()=>{try{await post('/api/web/asset',{id:current.project.id,name:file.name,data:r.result});current=await api('/api/web/project?id='+encodeURIComponent(current.project.id));renderProject();toast('Asset ajouté : '+file.name)}catch(e){toast(e.message)}};r.readAsDataURL(file)}
function integration(name){const labels={database:'Database SQL',auth:'Authentification & rôles',payments:'Stripe',api:'APIs & webhooks',storage:'Stockage fichiers',realtime:'Realtime',ai:'IA LocalAiVision',integrations:'Intégrations externes',analytics:'Analytics',domains:'Domaines & SSL'};if(name==='storage')return toast('Le stockage local des assets est déjà actif.');if(name==='ai')return toast('L’agent LocalAiWeb utilise déjà le LLM local de LocalAiVision.');toast((labels[name]||name)+' : connecteur prévu, pas encore configuré.')}
function setup(){
 $('#lawBack').onclick=()=>location.href='/';
 $('#lawNewProject').onclick=async()=>{const name=prompt('Nom du projet','Nouveau site');if(!name)return;const d=await post('/api/web/project/create',{name});await loadProjects(d.project.id)};
 $('#lawProjects').onchange=e=>loadProject(e.target.value);
 document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setViewport(b.dataset.view));
 document.querySelectorAll('.rail-tab').forEach(b=>b.onclick=()=>showPanel(b.dataset.panel));
 document.querySelectorAll('[data-service]').forEach(b=>b.onclick=()=>integration(b.dataset.service));
 document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>{$('#lawPrompt').value=b.dataset.prompt;generate()});
 $('#lawGenerate').onclick=generate;
 $('#lawPrompt').onkeydown=e=>{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();generate()}};
 $('#lawRefresh').onclick=refreshPreview;
 $('#lawOpenPreview').onclick=()=>window.open('/web-preview/'+current.project.id+'/index.html','_blank');
 $('#lawSelectMode').onclick=toggleVisual;
 $('#lawApplyVisual').onclick=applyVisual;
 $('#lawSaveCode').onclick=saveCode;
 $('#lawCloseCode').onclick=()=>$('#lawCodePanel').classList.add('hidden');
 $('#lawUndo').onclick=undo;$('#lawRedo').onclick=redo;
 $('#lawExport').onclick=()=>{if(current)location.href='/api/web/export?id='+encodeURIComponent(current.project.id)};
 $('#lawGithub').onclick=()=>integration('integrations');$('#lawPublish').onclick=()=>integration('domains');
 $('#lawAssetAdd').onclick=()=>$('#lawAssetInput').click();$('#lawAttach').onclick=()=>$('#lawAssetInput').click();
 $('#lawAssetInput').onchange=e=>{const f=e.target.files?.[0];if(f)addAsset(f);e.target.value=''};
 setupVisualEditing();loadProjects().catch(e=>toast(e.message));
}
setup();