/* LocalAiWeb QCM V1 — contextual Pages / Médias / Versions rail.
   No simulated asset: every row comes from the existing project API.
   Restore always confirms; backend creates a safety snapshot before replacement.
*/
(()=>{'use strict';
const root=document.querySelector('body[data-studio-page="editor"] .preview-pane');
if(!root)return;
const id=new URLSearchParams(location.search).get('id')||'';
if(!/^web-[a-f0-9]{12}$/.test(id))return;
const controls=root.querySelector('.preview-controls');
if(!controls)return;
const drawer=document.createElement('aside');drawer.className='qcm-editor-drawer';drawer.hidden=true;
drawer.setAttribute('aria-label','Détails du projet');
drawer.innerHTML='<header><strong id="qcmDrawerTitle">Pages du site</strong><button id="qcmDrawerClose" type="button" aria-label="Fermer les détails">×</button></header><div id="qcmDrawerContent" class="qcm-drawer-body" aria-live="polite"></div><footer><button type="button" id="qcmDrawerRefresh">↻ Actualiser</button><span id="qcmDrawerStatus" role="status" aria-live="polite"></span></footer>';
root.append(drawer);
const nav=document.createElement('div');nav.className='qcm-editor-rail';nav.setAttribute('role','group');nav.setAttribute('aria-label','Panneaux du projet');
const tabs=[['pages','Pages'],['assets','Médias'],['versions','Versions']];
const buttons=new Map();
for(const [key,label] of tabs){
 const b=document.createElement('button');b.type='button';b.dataset.qcmPanel=key;b.textContent=label;
 b.setAttribute('aria-pressed','false');b.title='Afficher '+label.toLowerCase();
 b.addEventListener('click',()=>{if(!drawer.hidden&&active===key)close();else open(key)});
 nav.append(b);buttons.set(key,b);
}
const topbar=root.querySelector('.preview-header');
topbar?.append(nav);
const content=drawer.querySelector('#qcmDrawerContent'),status=drawer.querySelector('#qcmDrawerStatus');
let active='pages',seq=0;
function close(){
 drawer.hidden=true;
 for(const b of buttons.values())b.setAttribute('aria-pressed','false');
}
function row(title,detail){
 const box=document.createElement('div');box.className='qcm-drawer-row';
 const name=document.createElement('strong');name.textContent=title;box.append(name);
 if(detail){const info=document.createElement('small');info.textContent=detail;box.append(info)}
 return box;
}
function fmt(value){return new Intl.NumberFormat('fr-FR').format(value)}
function date(t){return Number.isFinite(Number(t))?new Intl.DateTimeFormat('fr-FR',{dateStyle:'short',timeStyle:'short'}).format(new Date(Number(t)*1000)):'Date indisponible'}
function validateSource(name){return typeof name==='string'&&!name.startsWith('.')&&!name.includes('..')&&name.length<160}
async function render(){
 const current=++seq;
 content.replaceChildren();status.textContent='Chargement des informations réelles…';
 try{
   const r=await fetch('/api/web/project?id='+encodeURIComponent(id),{cache:'no-store'});
   const data=await r.json();
   if(current!==seq||drawer.hidden)return;
   if(!r.ok||data.error)throw Error(data.error||'Projet introuvable');
   status.textContent='';
   if(active==='pages'){
     const html=Object.keys(data.files||{}).filter(name=>validateSource(name)&&/\.html?$/i.test(name));
     if(!html.length){content.append(row('Aucune page HTML','Les pages apparaîtront ici dès leur création.'));return}
     for(const name of html.sort((a,b)=>a==='index.html'?-1:b==='index.html'?1:a.localeCompare(b))){
       const card=row(name,name==='index.html'?'Page d’accueil':'Page existante du projet');
       card.classList.add('is-page');
       const action=document.createElement('button');action.type='button';action.textContent='Voir le code ↗';action.title='Ouvrir le code source réel de '+name;
       action.addEventListener('click',()=>{close();const b=controls.querySelector('.qcm-code-button');
         if(b){b.click();document.dispatchEvent(new CustomEvent('qcm-select-source',{detail:{name}}))}
       });
       card.append(action);content.append(card);
     }
   }else if(active==='assets'){
     const assets=(Array.isArray(data.assets)?data.assets:[]).filter(x=>x&&validateSource(x.path));
     if(!assets.length){content.append(row('Aucun média enregistré','Les images, modèles 3D et autres fichiers intégrés au site apparaîtront ici.'));return}
     for(const asset of assets.slice(0,150)){
       const amount=Number(asset.size)||0;content.append(row(asset.path,amount>1048576?(amount/1048576).toFixed(1)+' Mo':fmt(Math.round(amount/1024))+' Ko'));
     }
   }else{
     const versions=Array.isArray(data.versions)?data.versions:[];
     if(!versions.length){content.append(row('Aucune version précédente','Les snapshots disponibles apparaîtront après la première modification.'));return}
     for(const item of versions.slice(0,70)){
       const box=row(item.label||'Version du site',date(item.created_at));
       const restore=document.createElement('button');restore.type='button';restore.textContent='Restaurer';restore.title='Rétablir cette version après confirmation';
       restore.addEventListener('click',async()=>{
         if(!confirm('Restaurer la version « '+String(item.label||item.id).slice(0,100)+' » ? Le site actuel sera sauvegardé automatiquement avant restauration.'))return;
         restore.disabled=true;status.textContent='Restauration de la version sélectionnée…';
         try{
           const response=await fetch('/api/web/version/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,version_id:item.id})});
           const data=await response.json();
           if(!response.ok||data.error)throw Error(data.error||'Restauration impossible');
           location.reload();
         }catch(error){restore.disabled=false;status.textContent='Restauration impossible : '+error.message}
       });
       box.append(restore);content.append(box);
     }
   }
 }catch(error){if(current===seq)status.textContent='Chargement impossible : '+error.message}
}
function open(key){
 active=key;drawer.hidden=false;
 drawer.querySelector('#qcmDrawerTitle').textContent=buttons.get(key).textContent+' du projet';
 for(const [name,b] of buttons)b.setAttribute('aria-pressed',String(name===key));
 void render();
}
drawer.querySelector('#qcmDrawerClose').addEventListener('click',close);
drawer.querySelector('#qcmDrawerRefresh').addEventListener('click',()=>void render());
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!drawer.hidden)close()});
})();
