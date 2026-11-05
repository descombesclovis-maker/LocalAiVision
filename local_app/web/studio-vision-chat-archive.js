/* Reversible public media archive: tied to saved conversation, not the gallery index. */
(()=>{
 'use strict';
 if(document.body.dataset.studioPage!=='vision')return;
 const chat=document.getElementById('chat'),messages=document.getElementById('messages');
 if(!chat||!messages)return;
 const root=document.createElement('section');root.id='visionChatArchive';root.className='vision-chat-archive';root.hidden=true;
 const pull=document.createElement('button');pull.type='button';pull.className='vision-archive-pull';
 pull.setAttribute('aria-expanded','false');pull.setAttribute('aria-controls','visionArchivePanel');
 const panel=document.createElement('div');panel.id='visionArchivePanel';panel.className='vision-archive-panel';panel.hidden=true;
 const conversationSwitch=document.createElement('button');conversationSwitch.type='button';
 conversationSwitch.className='vision-archive-conversations';
 conversationSwitch.textContent='Mes discussions sauvegardées';
 conversationSwitch.addEventListener('click',()=>document.getElementById('historyBtn')?.click());
 panel.append(conversationSwitch);
 const grid=document.createElement('div');grid.className='vision-archive-grid';panel.append(grid);
 root.append(pull,panel);chat.insertBefore(root,messages);
 let owner='',expanded=false,timer=null;
 const privateMode=()=>document.body.classList.contains('nsfw-active');
 const data=()=>typeof activeConversationId==='string'?conversations[activeConversationId]:null;
 function mediaKind(file){return /\.(mp4|webm|mov|mkv)$/i.test(file.filename||'')?'video':'image'}
 function collect(conv){
  const found=new Map();let lastPrompt='';
  for(const m of conv?.messages||[]){
   if(m.role==='user'&&m.text)lastPrompt=m.text;
   if(m.result?.filename||m.result?.ad_url){
    const key=window.VisionPublicArchive?.identity(m.result)||
      JSON.stringify([m.result.filename,m.result.subfolder,m.result.type]);
    if(!found.has(key))found.set(key,{result:m.result,prompt:lastPrompt,kind:mediaKind(m.result),key});
   }
  }
  return [...found.values()].reverse();
 }
 function update(){
  const conv=data();
  if(privateMode()||!conv||conv.profile==='nsfw'||document.body.dataset.visionMode==='creations'||(!(conv.messages||[]).length&&!Object.values(conversations).some(c=>c.id!==conv.id&&c.profile!=='nsfw'&&(c.messages||[]).length))){
   root.hidden=true;return;
  }
  if(owner!==conv.id){owner=conv.id;expanded=false}
  const entries=collect(conv);
  root.hidden=false;
  pull.textContent=(expanded?'⌃':'⌄')+'  Anciennes créations de cette discussion  ('+entries.length+')';
  pull.setAttribute('aria-expanded',String(expanded));
  panel.hidden=!expanded;
  if(!expanded)return;
  grid.replaceChildren();
  if(!entries.length){
   const empty=document.createElement('p');empty.className='vision-archive-empty';
   empty.textContent='Aucun média généré dans cette conversation pour le moment. Les échanges restent disponibles via « Mes discussions sauvegardées ».';
   grid.append(empty);return;
  }
  const store=typeof library==='undefined'?[]:library;
  for(const entry of entries){
   const card=document.createElement('article');card.className='vision-archive-item';
   const raw=resultUrl(entry.result);
   const media=document.createElement(entry.kind==='video'?'video':'img');media.src=raw;media.loading='lazy';
   if(entry.kind==='video'){media.preload='metadata';media.muted=true;media.playsInline=true}
   else media.alt=entry.prompt||'Image enregistrée';
   const view=document.createElement('button');view.type='button';view.className='vision-archive-view';
   view.title='Ouvrir en grand';view.setAttribute('aria-label','Ouvrir cette création en grand');
   view.append(media);view.onclick=()=>window.LocalAiVisionPreviewMedia?.(raw,entry.kind);
   const caption=document.createElement('p');caption.textContent=entry.prompt||'Création enregistrée';
   const actions=document.createElement('div');actions.className='vision-archive-actions';
   const stored=store.find(x=>x.profile!=='nsfw'&&window.VisionPublicArchive?.identity(x)===entry.key);
   const restore=document.createElement('button');restore.type='button';
   restore.textContent=!stored||stored.galleryHidden?'Restaurer dans Mes créations':'Retirer de la galerie';
   restore.onclick=async()=>{
    if(!stored||stored.galleryHidden)window.VisionPublicArchive?.restore(entry.result,entry.kind,entry.prompt);
    else await deleteLibraryItem(stored._id);
    schedule();
   };
   const permanent=document.createElement('button');permanent.type='button';permanent.className='vision-archive-danger';
   permanent.textContent='Supprimer définitivement';
   permanent.onclick=async()=>{
    const deleted=await window.VisionPublicArchive?.permanentDelete(entry.result);
    if(deleted){expanded=true;schedule()}
   };
   actions.append(restore,permanent);card.append(view,caption,actions);grid.append(card);
  }
 }
 function schedule(){clearTimeout(timer);timer=setTimeout(update,90)}
 pull.addEventListener('click',()=>{expanded=!expanded;update()});
 new MutationObserver(schedule).observe(messages,{subtree:true,childList:true});
 new MutationObserver(schedule).observe(document.body,{attributes:true,attributeFilter:['class','data-vision-mode']});
 document.addEventListener('studio:library-changed',schedule);
 document.addEventListener('studio:conversation-restored',schedule);
 update();
})();