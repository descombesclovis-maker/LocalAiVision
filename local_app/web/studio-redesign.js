/* LocalAiVision: four true workspaces; existing media generation stays in app.js. */
(()=>{
 'use strict';
 const byId=id=>document.getElementById(id);
 const prompt=byId('prompt'),welcome=byId('welcome'),messages=byId('messages');
 const navEntries=['navCreations','navPhoto','navVideo','navNsfw'];
 let pendingAsset=null;
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
   const current=activeConversationId?conversations[activeConversationId]:null;
   if(!current || current.profile==='nsfw' || (current.messages||[]).length) {
     createBlankConversation('auto');
   } else {
     openConversation(activeConversationId);
   }
   // The landing is always a neutral chat. Never inherit NSFW mode or a
   // forced video workflow from a prior dedicated creation session.
   byId('taskMode').value='auto';
   updateCreationModeGuide();
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
       const toSite=document.createElement('button');toSite.type='button';
       toSite.textContent='Ajouter à un site ↗';
       toSite.title='Copier cette création dans les ressources d’un projet LocalAiWeb';
       toSite.addEventListener('click',()=>selectAssetForProject(entry));
       actions.append(open,toSite,remove);caption.append(name,actions);card.append(caption);grid.append(card);
     }
   }
   paint();
 }
 async function selectAssetForProject(entry){
   const dialog=byId('assetDialog'),selection=byId('assetProject'),feedback=byId('assetFeedback');
   pendingAsset=entry;selection.replaceChildren();feedback.textContent='Chargement des projets…';
   byId('assetConfirm').disabled=true;dialog.showModal();
   try{
     const result=await api('/api/web/projects');
     const projects=result.projects||[];
     if(!projects.length){
       feedback.textContent='Aucun projet existant : crée d’abord un projet dans LocalAiWeb.';
       return;
     }
     selection.add(new Option('Choisir un projet…',''));
     for(const project of projects)selection.add(new Option(project.name,project.id));
     feedback.textContent='La copie sera privée et conservera le fichier original.';
     byId('assetConfirm').disabled=false;
   }catch(error){feedback.textContent='Projets indisponibles : '+error.message}
 }
 byId('assetClose')?.addEventListener('click',()=>byId('assetDialog').close());
 byId('assetConfirm')?.addEventListener('click',async()=>{
   const btn=byId('assetConfirm'),selection=byId('assetProject'),feedback=byId('assetFeedback');
   if(!pendingAsset||!selection.value){feedback.textContent='Choisis un projet avant de continuer.';return}
   btn.disabled=true;feedback.textContent='Copie sécurisée de la ressource…';
   try{
     const response=await api('/api/web/asset/import-generation',{
       method:'POST',headers:{'Content-Type':'application/json'},
       body:JSON.stringify({
         project_id:selection.value,filename:pendingAsset.filename,
         subfolder:pendingAsset.subfolder||'',type:pendingAsset.type||'output'
       })
     });
     feedback.replaceChildren();
     feedback.append(document.createTextNode('Import terminé : '+response.path+' · '));
     const link=document.createElement('a');link.href='/localaiweb/editor?id='+encodeURIComponent(response.project_id);
     link.textContent='Ouvrir le projet ↗';link.style.color='#e9ccff';
     feedback.append(link);
   }catch(error){feedback.textContent='Import impossible : '+error.message}
   finally{btn.disabled=false}
 });
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
     darkMode();welcome.classList.add('welcome-exiting');activeNav('');
     window.setTimeout(()=>{
       if(!document.body.classList.contains('is-landing'))welcome.classList.add('hidden');
       welcome.classList.remove('welcome-exiting');
     },260);
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
   if(!welcome.classList.contains('hidden') && !welcome.classList.contains('welcome-exiting')) {
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
   const nsfwHistory=activeConversationId && conversations[activeConversationId]?.profile==='nsfw';
   const rows=Object.values(conversations)
     .filter(c=>(c.profile==='nsfw')===!!nsfwHistory)
     .filter(c=>(c.title||'').toLocaleLowerCase('fr').includes(query))
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
 // Real engine health, no fake 'connected' status. The repair action
 // delegates to the existing resumable engine installer after user consent.
 const recovery=byId('engineRecovery'),recoveryText=byId('engineRecoveryText');
 const recoveryButton=byId('engineRecoveryButton');
 async function updateEngineHealth(){
   try{
     const response=await fetch('/api/health',{cache:'no-store'});
     if(!response.ok)throw Error('Serveur local HTTP '+response.status);
     const data=await response.json();
     const ready=!!data.online && !!data.llm?.online;
     const running=data.startup?.state==='running';
     recovery.hidden=ready&&!running;
     if(running){
       recoveryText.textContent=data.startup?.message||'Préparation des moteurs en cours…';
       recoveryButton.disabled=true;recoveryButton.textContent='Installation en cours…';
     }else if(!ready){
       const missing=[!data.online?'ComfyUI photo/vidéo':'',
                     !data.llm?.online?'Qwen conversation':''].filter(Boolean);
       recoveryText.textContent=data.startup?.error
         ?'Moteurs non disponibles : '+String(data.startup.error).slice(0,110)
         :'Moteurs à démarrer : '+missing.join(' · ')+'.';
       recoveryButton.disabled=false;recoveryButton.textContent='Démarrer / réparer ↗';
     }
   }catch(error){
     recovery.hidden=false;recoveryText.textContent='Diagnostic local impossible : '+error.message;
     recoveryButton.disabled=true;
   }
 }
 recoveryButton.addEventListener('click',()=>{
   if(recoveryButton.disabled)return;
   if(window.confirm('Démarrer ou réparer les moteurs locaux ? Des modèles et dépendances peuvent être téléchargés. Les fichiers déjà présents sont conservés.')){
     byId('retrySetup')?.click();
     recoveryButton.disabled=true;recoveryText.textContent='Préparation demandée…';
     window.setTimeout(updateEngineHealth,2400);
   }
 });
 window.setInterval(()=>{if(!document.hidden)updateEngineHealth()},14000);
 updateEngineHealth();
 if(!welcome.classList.contains('hidden'))document.body.classList.add('is-landing');
})();
