/* LocalAiVision (public workspace ONLY): real output mirrored in an immersive,
 * independently scrollable viewer, keeping generation/chat and saved media untouched.
 * NSFW stays unchanged: panel is hidden and its sources cleared immediately.
 */
(()=>{'use strict';
const area=document.querySelector('body[data-studio-page="vision"] .content');
const chat=document.getElementById('chat'),messages=document.getElementById('messages');
if(!area||!chat||!messages)return;
const importButton=document.getElementById('composerImageBtn');
if(importButton){
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');
 svg.classList.add('studio-public-plus','studio-plus-icon');
 const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d','M12 5v14M5 12h14');svg.append(path);importButton.append(svg);
}
const viewer=document.createElement('aside');viewer.className='qcm-vision-viewer';viewer.id='qcmVisionViewer';
viewer.setAttribute('aria-label','Aperçu des créations dans la discussion');
viewer.innerHTML='<header><span><i aria-hidden="true"></i> APERÇU LIVE</span><strong id="qcmVisionKind">Prêt à créer</strong></header><div class="qcm-vision-stage" id="qcmVisionStage"><div class="qcm-vision-placeholder"><span class="preview-light" aria-hidden="true"></span><strong>Votre vision, en grand.</strong><p>Les résultats de votre conversation apparaissent ici dès leur disponibilité.</p></div></div><footer id="qcmVisionActions" hidden><a id="qcmVisionOpen" target="_blank" rel="noopener noreferrer">↗ Ouvrir</a><a id="qcmVisionDownload" download>↓ Télécharger</a></footer>';
area.append(viewer);
const stage=viewer.querySelector('#qcmVisionStage'),actions=viewer.querySelector('#qcmVisionActions');
const heading=viewer.querySelector('#qcmVisionKind'),open=viewer.querySelector('#qcmVisionOpen'),download=viewer.querySelector('#qcmVisionDownload');
const empty=stage.firstElementChild;
let lastSrc='',lastType='';
const isAdult=()=>document.body.classList.contains('nsfw-active');
function clear(){lastSrc='';lastType='';stage.replaceChildren(empty);actions.hidden=true;heading.textContent='Prêt à créer';open.removeAttribute('href');download.removeAttribute('href')}
const header=document.querySelector('.topbar-actions');
const menu=document.querySelector('.studio-navigation');
const secondary=[...header.children].filter(node=>node.id!=='nsfwGalleryToggle');
const newDiscussion=document.getElementById('newConversation');
const plusText=[...newDiscussion.childNodes].find(n=>n.nodeType===3);
const originalPlus=plusText?.textContent;
function arrangeMenu(){
 if(plusText)plusText.textContent=isAdult()?originalPlus:'+ ';
 for(const logo of document.querySelectorAll('img[src*="brand-vision"],img[data-public-master]')){
  if(!logo.dataset.publicMaster){logo.dataset.previousSrc=logo.getAttribute('src');logo.dataset.publicMaster='vision'}
  logo.src=isAdult()?logo.dataset.previousSrc:'/assets/assets/brand-reference/LocalAIVision_Official_Original.png';
 }

 const adult=isAdult();
 for(const node of secondary){
  const excluded=node.id==='updateBtn'||node.classList.contains('studio-universe-link');
  const parent=adult||excluded?header:menu;
  if(node.parentElement!==parent)parent.append(node);
 }
}
function update(){
 arrangeMenu();
 if(isAdult()){viewer.hidden=true;clear();return}
 viewer.hidden=false;
 const items=[...messages.querySelectorAll('.generation-frame .result-media')];
 const item=items.at(-1);
 if(!item){if(lastSrc)clear();return}
 const url=item.getAttribute('src')||'';
 if(!url||!/^(\/|https?:\/\/)/.test(url))return;
 let resolved;try{resolved=new URL(url,location.href);if(resolved.origin!==location.origin)return}catch{return}
 const mediaType=item.tagName.toLowerCase()==='video'?'video':'image';
 if(lastSrc===resolved.href&&lastType===mediaType)return;
 lastSrc=resolved.href;lastType=mediaType;
 const node=document.createElement(mediaType==='video'?'video':'img');
 node.src=resolved.href;node.className='qcm-vision-media';
 if(mediaType==='video'){node.controls=true;node.preload='metadata';node.playsInline=true}
 else node.alt='Dernière image générée dans cette discussion';
 stage.replaceChildren(node);
 heading.textContent=mediaType==='video'?'Vidéo générée':'Image générée';
 actions.hidden=false;open.href=resolved.href;download.href=resolved.href;
 download.download=(resolved.searchParams.get('filename')||'creation-localaivision').replace(/[\/\\]/g,'_');
}
new MutationObserver(update).observe(messages,{subtree:true,childList:true,attributes:true,attributeFilter:['src']});
new MutationObserver(update).observe(document.body,{attributes:true,attributeFilter:['class']});
update();
// Public mode shortcuts point to existing application controls.
const welcome=document.getElementById('welcome');
if(welcome){
 const modes=document.createElement('div');modes.className='qcm-vision-modes';
 const items=[['Photo','navPhoto','📷'],['Vidéo','navVideo','🎬'],['Publicité','studioAdOpen','⭐'],['Mes créations','navCreations','🎨']];
 for(const [label,target,glyph] of items){
   const navGlyph=document.getElementById(target)?.querySelector('.nav-glyph');
   if(navGlyph){
     const publicIcon=document.createElement('span');publicIcon.className='public-mode-icon';
     publicIcon.innerHTML=window.studioIconMarkup(glyph);
     navGlyph.append(publicIcon);
   }
   const b=document.createElement('button');b.type='button';b.dataset.qcmTarget=target;
   b.innerHTML='<span aria-hidden="true">'+window.studioIconMarkup(glyph)+'</span><strong></strong><small>↗</small>';
   b.querySelector('strong').textContent=label;
   b.addEventListener('click',()=>{if(!isAdult())document.getElementById(target)?.click()});
   modes.append(b);
 }
 welcome.append(modes);
}
const splitter=document.createElement('div');splitter.className='qcm-vision-splitter';
splitter.tabIndex=0;splitter.setAttribute('role','separator');splitter.setAttribute('aria-label','Redimensionner la discussion et l’aperçu');
splitter.setAttribute('aria-orientation','vertical');
area.append(splitter);
let size=42;try{const x=Number(localStorage.getItem('qcm_vision_split_v1'));if(Number.isFinite(x)&&x>=30&&x<=62)size=x}catch{}
function setSize(v){size=Math.round(Math.max(30,Math.min(62,v)));area.style.setProperty('--qcm-vision-chat',size+'%');splitter.setAttribute('aria-valuenow',String(size));try{localStorage.setItem('qcm_vision_split_v1',String(size))}catch{}}
splitter.setAttribute('aria-valuemin','30');splitter.setAttribute('aria-valuemax','62');setSize(size);
let dragging=false;
splitter.addEventListener('pointerdown',e=>{if(e.button!==0||isAdult()||matchMedia('(max-width:900px)').matches)return;dragging=true;splitter.setPointerCapture?.(e.pointerId);document.body.classList.add('qcm-resizing')});
splitter.addEventListener('pointermove',e=>{if(dragging)setSize((e.clientX-area.getBoundingClientRect().left)/area.getBoundingClientRect().width*100)});
const done=e=>{dragging=false;document.body.classList.remove('qcm-resizing');if(e&&splitter.hasPointerCapture?.(e.pointerId))splitter.releasePointerCapture(e.pointerId)};
splitter.addEventListener('pointerup',done);splitter.addEventListener('pointercancel',done);
splitter.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();if(!isAdult())setSize(size+(e.key==='ArrowRight'?2:-2))});
const tabs=document.createElement('nav');tabs.className='qcm-vision-mobile-tabs';tabs.setAttribute('aria-label','Vue mobile');
tabs.innerHTML='<button type="button" data-qcm-tab="chat" aria-pressed="true">Discussion</button><button type="button" data-qcm-tab="preview" aria-pressed="false">Aperçu</button>';
area.prepend(tabs);document.body.dataset.qcmVisionTab='chat';
tabs.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{
 if(isAdult())return;
 document.body.dataset.qcmVisionTab=b.dataset.qcmTab;
 tabs.querySelectorAll('button').forEach(other=>other.setAttribute('aria-pressed',String(other===b)));
}));
})();

