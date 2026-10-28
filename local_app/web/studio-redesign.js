/* LocalAiVision: four true workspaces; existing media generation stays in app.js. */
(()=>{
 'use strict';
 const byId=id=>document.getElementById(id);
 const prompt=byId('prompt'),welcome=byId('welcome'),messages=byId('messages');
 const navEntries=['navCreations','navPhoto','navVideo','navNsfw'];
 function activeNav(id){
   for(const name of navEntries) {
     const button=byId(name);
     button?.classList.toggle('active',name===id);
     button?.setAttribute('aria-current',name===id?'page':'false');
   }
 }
 function darkMode(){
   document.body.classList.remove('is-landing');
   document.body.classList.add('is-chatting');
 }
 function home(){
   // Opening a new empty thread never discards existing saved conversations.
   if(!activeConversationId || (conversations[activeConversationId]?.messages||[]).length) {
     createBlankConversation('auto');
   } else {
     openConversation(activeConversationId);
   }
   welcome.classList.remove('hidden');
   messages.replaceChildren();
   document.body.classList.remove('is-chatting','show-diagnostics');
   document.body.classList.add('is-landing');
   prompt.value='';prompt.blur();
   byId('generationSettings')?.classList.add('hidden');
   byId('settingsBtn')?.classList.remove('active');
   activeNav('');
   hideSidebar();
 }
 function startMode(mode){
   if(mode==='nsfw'){
     enterNsfwWorkspace();
     const current=activeConversationId?conversations[activeConversationId]:null;
     if(current?.profile!=='nsfw')return; // Locked: preserve authorization gate.
   }else{
     const current=activeConversationId?conversations[activeConversationId]:null;
     if(!current || current.profile==='nsfw')createBlankConversation('auto');
     byId('taskMode').value=mode;
     updateSettingsVisibility();
     updateCreationModeGuide();
   }
   darkMode();welcome.classList.add('hidden');
   activeNav(mode==='image'?'navPhoto':mode==='video'?'navVideo':'navNsfw');
   hideSidebar();prompt.focus();
 }
 function gallery(){
   darkMode();welcome.classList.add('hidden');
   activeNav('navCreations');hideSidebar();
   let type='all';
   const scope='standard';
   const root=document.createElement('section');root.className='studio-gallery library-view';
   const bar=document.createElement('div');bar.className='gallery-header';
   const heading=document.createElement('div');
   const title=document.createElement('h2');title.textContent='Mes créations';
   const hint=document.createElement('p');hint.textContent='Tes images et vidéos locales, prêtes à être consultées et réutilisées.';
   heading.append(title,hint);
   const controls=document.createElement('div');controls.className='gallery-controls';
   for(const [value,label] of [['all','Tout'],['image','Photos'],['video','Vidéos']]){
     const button=document.createElement('button');button.type='button';
     button.textContent=label;button.classList.toggle('active',value===type);
     button.addEventListener('click',()=>{type=value;paint()});
     button.dataset.galleryFilter=value;
     controls.append(button);
   }
   bar.append(heading,controls);
   const grid=document.createElement('div');grid.className='gallery-grid';
   root.append(bar,grid);
   messages.replaceChildren(root);
   function paint(){
     controls.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.galleryFilter===type));
     grid.replaceChildren();
     const items=library.filter(x=>(type==='all'||x.kind===type)&&x.profile!=='nsfw');
     if(!items.length){
       const empty=document.createElement('div');empty.className='empty-library';
       empty.textContent='Aucune création pour le moment. Ouvre Photo ou Vidéo pour commencer.';
       grid.append(empty);return;
     }
     for(const entry of items){
       const card=document.createElement('article');card.className='gallery-card';
       const url=resultUrl(entry),video=entry.kind==='video'||/\.(mp4|webm|mov|mkv)$/i.test(entry.filename||'');
       const media=document.createElement(video?'video':'img');media.src=url;
       if(video)media.controls=true;else media.alt=entry.prompt||'Création locale';
       media.loading='lazy';card.append(media);
       const caption=document.createElement('div');caption.className='gallery-caption';
       const name=document.createElement('p');name.textContent=entry.prompt||'Création sans titre';name.title=name.textContent;
       const actions=document.createElement('div');actions.className='gallery-actions';
       const open=document.createElement('a');open.href=url;open.target='_blank';open.rel='noopener noreferrer';open.textContent='Ouvrir ↗';
       const remove=document.createElement('button');remove.type='button';remove.textContent='Supprimer';remove.title='Supprimer cette création';
       remove.addEventListener('click',async()=>{await deleteLibraryItem(entry._id);gallery()});
       actions.append(open,remove);caption.append(name,actions);card.append(caption);grid.append(card);
     }
   }
   paint();
 }
 byId('navCreations')?.addEventListener('click',gallery);
 byId('navPhoto')?.addEventListener('click',()=>startMode('image'));
 byId('navVideo')?.addEventListener('click',()=>startMode('video'));
 byId('navNsfw')?.addEventListener('click',()=>startMode('nsfw'));
 byId('homeBtn')?.addEventListener('click',home);
 byId('newConversation')?.addEventListener('click',()=>{
   // Legacy handler creates the conversation; do not register a second one.
   window.setTimeout(()=>{darkMode();welcome.classList.add('hidden');activeNav('');prompt.focus()},0);
 });
 prompt?.addEventListener('focus',()=>{
   if(document.body.classList.contains('is-landing')){
     darkMode();welcome.classList.add('hidden');activeNav('');
   }
 });
 prompt?.addEventListener('input',()=>{if(prompt.value.trim())darkMode()});
 byId('diagnosticsAction')?.addEventListener('click',()=>{
   const panel=byId('enginePanel');
   if(!panel)return;
   document.body.classList.toggle('show-diagnostics');
   panel.open=true;
   panel.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'nearest'});
 });
 // Existing JS updates #welcome classes; keep the color scheme consistent
 // when a saved thread opens, including after the asynchronous initial refresh.
 const watch=new MutationObserver(()=>{
   if(!welcome.classList.contains('hidden')) {
     document.body.classList.add('is-landing');
     document.body.classList.remove('is-chatting');
   }else{
     darkMode();
   }
 });
 watch.observe(welcome,{attributes:true,attributeFilter:['class']});
 // A fresh launch always opens the brand-led welcome, while retaining
 // previously saved chats in the visible History dialog.
 const historyDialog=byId('historyDialog'),historySearch=byId('historySearch'),historyList=byId('historyList');
 function historyPaint(){
   historyList.replaceChildren();
   const query=historySearch.value.toLocaleLowerCase('fr');
   const rows=Object.values(conversations).filter(c=>(c.title||'').toLocaleLowerCase('fr').includes(query))
     .sort((a,b)=>String(b.updatedAt||'').localeCompare(String(a.updatedAt||'')));
   if(!rows.length){
     const empty=document.createElement('p');empty.textContent='Aucune conversation à afficher.';
     historyList.append(empty);return;
   }
   for(const chat of rows.slice(0,250)){
     const row=document.createElement('div');row.className='history-item';
     const open=document.createElement('button');open.type='button';
     open.textContent=chat.title||'Nouvelle conversation';
     open.title='Reprendre cette conversation';
     open.addEventListener('click',()=>{
       openConversation(chat.id);darkMode();welcome.classList.add('hidden');
       historyDialog.close();activeNav('');prompt.focus();
     });
     const rename=document.createElement('button');rename.type='button';rename.textContent='✎';
     rename.title='Renommer la conversation';rename.setAttribute('aria-label','Renommer '+(chat.title||'conversation'));
     rename.addEventListener('click',()=>{renameConversation(chat.id);historyPaint()});
     const remove=document.createElement('button');remove.type='button';remove.textContent='×';
     remove.title='Supprimer la conversation';remove.setAttribute('aria-label','Supprimer '+(chat.title||'conversation'));
     remove.addEventListener('click',()=>{deleteConversation(chat.id);historyPaint()});
     row.append(open,rename,remove);historyList.append(row);
   }
 }
 byId('historyBtn')?.addEventListener('click',()=>{historyPaint();historyDialog.showModal();historySearch.focus()});
 byId('historyClose')?.addEventListener('click',()=>historyDialog.close());
 historySearch?.addEventListener('input',historyPaint);
 let userInteracted=false;
 document.addEventListener('pointerdown',()=>{userInteracted=true},{once:true});
 document.addEventListener('keydown',()=>{userInteracted=true},{once:true});
 window.localAiVisionInitialRefresh?.then(()=>{
   if(!userInteracted)home();
 }).catch(()=>{
   if(!userInteracted)home();
 });
 if(!welcome.classList.contains('hidden'))document.body.classList.add('is-landing');
})();
