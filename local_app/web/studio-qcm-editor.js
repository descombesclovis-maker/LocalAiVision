/* Approved QCM V1 Web editor: persistent 32% chat split and direct project rename.
   Uses existing API and DOM; does not touch project files or generation logic. */
(()=>{'use strict';
const root=document.querySelector('main.studio'),heading=document.getElementById('lawPreviewTitle');
if(!root||!heading)return;
const KEY='law_qcm_chat_split_v1';
let saved=32;try{const value=Number(localStorage.getItem(KEY));if(Number.isFinite(value)&&value>=25&&value<=55)saved=value}catch{}
const setSize=value=>{
 const safe=Math.max(25,Math.min(55,Math.round(value*10)/10));
 root.style.setProperty('--qcm-chat-size',safe+'%');
 return safe;
};
setSize(saved);
const handle=document.createElement('div');handle.className='qcm-splitter';handle.id='qcmEditorSplitter';
handle.setAttribute('role','separator');handle.setAttribute('aria-label','Redimensionner discussion et aperçu');
handle.setAttribute('aria-orientation','vertical');handle.tabIndex=0;
handle.setAttribute('aria-valuemin','25');handle.setAttribute('aria-valuemax','55');handle.setAttribute('aria-valuenow',String(saved));
handle.title='Glisser pour modifier la largeur de la discussion · flèches gauche/droite au clavier';
root.append(handle);
const commit=v=>{const size=setSize(v);handle.setAttribute('aria-valuenow',String(size));try{localStorage.setItem(KEY,String(size))}catch{}};
let dragging=false;
handle.addEventListener('pointerdown',e=>{
 if(e.button!==0||window.matchMedia('(max-width:780px)').matches)return;
 dragging=true;handle.setPointerCapture?.(e.pointerId);document.body.classList.add('qcm-resizing');e.preventDefault();
});
handle.addEventListener('pointermove',e=>{
 if(!dragging)return;
 const rect=root.getBoundingClientRect();
 const fraction=(e.clientX-rect.left)/rect.width*100;
 const size=setSize(fraction);handle.setAttribute('aria-valuenow',String(size));
});
const finish=e=>{if(!dragging)return;dragging=false;document.body.classList.remove('qcm-resizing');const size=Number(handle.getAttribute('aria-valuenow'));commit(size);if(e&&handle.hasPointerCapture?.(e.pointerId))handle.releasePointerCapture(e.pointerId)};
handle.addEventListener('pointerup',finish);handle.addEventListener('pointercancel',finish);
handle.addEventListener('keydown',e=>{
 if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight'&&e.key!=='Home'&&e.key!=='End')return;
 e.preventDefault();const current=Number(handle.getAttribute('aria-valuenow'))||32;
 commit(e.key==='Home'?25:e.key==='End'?55:current+(e.key==='ArrowRight'?2:-2));
});
const params=new URLSearchParams(location.search),id=params.get('id')||'';
if(!/^web-[a-f0-9]{12}$/.test(id))return;
heading.title='Double-clique pour renommer le projet';heading.setAttribute('data-qcm-rename','');
heading.tabIndex=0;heading.setAttribute('role','button');heading.setAttribute('aria-label','Renommer le projet');
let renaming=false;
function showRename(){
 if(renaming)return;renaming=true;
 const old=heading.textContent||'Ton site',parent=heading.parentElement;
 const input=document.createElement('input');input.type='text';input.className='qcm-project-title-input';
 input.value=old;input.maxLength=80;input.setAttribute('aria-label','Nouveau nom du projet');
 heading.hidden=true;parent.insertBefore(input,heading);input.focus();input.select();
 let finished=false;
 const close=()=>{if(finished)return;finished=true;input.remove();heading.hidden=false;renaming=false};
 const save=async()=>{
   const name=input.value.trim();
   if(!name||name===old){close();return}
   input.disabled=true;
   try{
     const r=await fetch('/api/web/project/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,name})});
     const data=await r.json();
     if(!r.ok||data.error)throw Error(data.error||'Renommage impossible.');
     heading.textContent=name;close();
   }catch(error){
     input.disabled=false;
     const live=document.getElementById('lawChatStatus');if(live)live.textContent='Renommage impossible : '+error.message;
     input.focus();
   }
 };
 input.addEventListener('keydown',e=>{
   if(e.key==='Escape'){e.preventDefault();close()}
   if(e.key==='Enter'){e.preventDefault();void save()}
 });
 input.addEventListener('blur',()=>{if(!input.disabled)close()});
}
heading.addEventListener('dblclick',showRename);
heading.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();showRename()}});
// Compact device controls keep the existing data-view handlers and keyboard support.
for(const button of document.querySelectorAll('.view-modes [data-view]')){
 const key=button.dataset.view;
 const label={desktop:'Ordinateur',tablet:'Tablette',mobile:'Téléphone'}[key];
 const glyph={desktop:'▣',tablet:'▯',mobile:'▵'}[key];
 if(!label)continue;
 button.textContent=glyph;
 button.title='Aperçu '+label.toLowerCase();
 button.setAttribute('aria-label','Afficher en mode '+label.toLowerCase());
 button.classList.add('qcm-device-button');
}
// Real source-code inspection, not a pretend shortcut or a generated screenshot.
const controls=document.querySelector('.preview-controls'),siteTools=document.getElementById('lawSiteTools');
if(controls&&/^web-[a-f0-9]{12}$/.test(id)){
 const codeButton=document.createElement('button');codeButton.type='button';codeButton.className='qcm-code-button';
 codeButton.title='Voir les véritables fichiers du site';codeButton.textContent='</>';
 codeButton.setAttribute('aria-label','Consulter le code du site');
 const codeDialog=document.createElement('dialog');codeDialog.className='qcm-code-dialog';
 codeDialog.setAttribute('aria-label','Code du site enregistré');
 codeDialog.innerHTML='<div class="qcm-code-head"><strong>Fichiers du site</strong><button type="button" aria-label="Fermer le code">×</button></div><div class="qcm-code-body"><nav aria-label="Fichiers source" class="qcm-code-files"></nav><pre><code class="qcm-code-content"></code></pre></div>';
 document.body.append(codeDialog);
 const close=codeDialog.querySelector('button');close.addEventListener('click',()=>codeDialog.close());
 const list=codeDialog.querySelector('.qcm-code-files'),content=codeDialog.querySelector('.qcm-code-content');
 let requestedFile=null;
 document.addEventListener('qcm-select-source',event=>{requestedFile=String(event.detail?.name||'')});
 codeButton.addEventListener('click',async()=>{
   codeDialog.showModal();content.textContent='Chargement des fichiers enregistrés…';list.replaceChildren();
   try{
     const response=await fetch('/api/web/project?id='+encodeURIComponent(id),{cache:'no-store'});
     const data=await response.json();
     if(!response.ok||data.error)throw Error(data.error||'Sources indisponibles.');
     const files=Object.entries(data.files||{}).filter(([name,value])=>typeof value==='string'&&!name.startsWith('.'));
     if(!files.length){content.textContent='Aucun fichier texte disponible pour ce projet.';return}
     const initial=files.find(([name])=>name===requestedFile)||files[0];
     files.slice(0,70).forEach(([name,value],i)=>{
       const b=document.createElement('button');b.type='button';b.textContent=name;b.className=name===initial[0]?'selected':'';
       b.addEventListener('click',()=>{
         list.querySelectorAll('button').forEach(button=>button.classList.toggle('selected',button===b));
         content.textContent=value.slice(0,250000);
       });
       list.append(b);
     });
     content.textContent=String(initial[1]).slice(0,250000);
     requestedFile=null;
   }catch(error){content.textContent='Impossible de lire les sources : '+error.message}
 });
 // Keep publish prominent, source and viewport buttons to its right.
 if(siteTools)controls.insertBefore(codeButton,siteTools);else controls.append(codeButton);
}
})();
