/* LocalAiVision: four true workspaces; existing media generation stays in app.js. */
(()=>{
 'use strict';
 const byId=id=>document.getElementById(id);
 const prompt=byId('prompt'),welcome=byId('welcome'),messages=byId('messages');
 const navEntries=['navChat','navCreations','navPhoto','navVideo','navNsfw','studioAdOpen'];
 // Keep the original Studio landing intact: dedicated modes only replace its
 // *presentation*, never the saved conversation or media library.
 const originalWelcome=[...welcome.childNodes].map(node=>node.cloneNode(true));
 const modeCopy={
   image:{title:'Création de photographies',message:'Décris la photo que tu souhaites créer. Précise le sujet, l’environnement, l’éclairage ou le style recherché pour obtenir le résultat que tu imagines.',placeholder:'Décris ta photo…',nav:'navPhoto'},
   video:{title:'Création de vidéos',message:'Décris la vidéo que tu souhaites réaliser. Précise les personnages, les mouvements, le décor ou les mouvements de caméra pour donner vie à ton idée.',placeholder:'Décris ta vidéo…',nav:'navVideo'},
   advert:{title:'Création de publicités',message:'Décris la publicité que tu souhaites créer. Je t’aiderai à préciser la marque, le produit, le format et le style pour réaliser une publicité adaptée à ton projet. Pour commencer, quelle marque ou entreprise souhaites-tu promouvoir ?',placeholder:'Décris ta publicité…',nav:'studioAdOpen'},
   nsfw:{title:'Espace NSFW',message:'Bienvenue dans votre espace de création privé. Décrivez le contenu que vous souhaitez réaliser et personnalisez vos paramètres de génération selon vos préférences.',placeholder:'Décris ta création…',nav:'navNsfw'}
 };
 // A dedicated mode is an empty canvas. A completed chat is never erased:
 // createBlankConversation saves a new thread and previous ones stay in History.
 function clearModeCanvas(mode,{preserveConversation=false,message}={}){
   if(!preserveConversation){
     const current=activeConversationId?conversations[activeConversationId]:null;
     if(!current||current.profile==='nsfw'||(current.messages||[]).length){createBlankConversation('auto')}
     else openConversation(activeConversationId); // removes a previous gallery DOM
   }else if(activeConversationId){
     openConversation(activeConversationId); // NSFW gate already created private thread
   }
   if(activeGalleryPoll){clearInterval(activeGalleryPoll);activeGalleryPoll=null}
   const copy=modeCopy[mode];if(!copy)return;
   document.body.dataset.visionMode=mode;
   const panel=document.createElement('div');panel.className='vision-mode-intro';
   panel.dataset.mode=mode;
   const glyph=document.querySelector('#'+copy.nav+' .nav-glyph svg')?.cloneNode(true);
   if(glyph){glyph.classList.add('vision-mode-intro-icon');glyph.setAttribute('aria-hidden','true');panel.append(glyph)}
   const heading=document.createElement('h2');heading.textContent=copy.title;
   const description=document.createElement('p');description.textContent=message||copy.message;
   panel.append(heading,description);
   welcome.replaceChildren(panel);
   welcome.classList.add('vision-onboarding');
   welcome.classList.remove('hidden','welcome-exiting');
   messages.replaceChildren();
   darkMode(); // dedicated mode uses the dark/cyan workspace, NOT the landing
   prompt.value='';prompt.placeholder=copy.placeholder;
   prompt.style.height='';
   document.getElementById('chat').scrollTop=0;
   activeNav(copy.nav);
   hideSidebar();
 }
 window.LocalAiVisionSelectMode=clearModeCanvas;

 let pendingAsset=null;
 let activeGalleryPoll=null;
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
   document.body.dataset.visionMode='home';
   welcome.replaceChildren(...originalWelcome.map(node=>node.cloneNode(true)));
   welcome.classList.remove('vision-onboarding');
   window.StudioAds?.cancelChat?.();
   // Opening a new empty thread never discards existing saved conversations.
   const current=activeConversationId?conversations[activeConversationId]:null;
   if(!current || current.profile==='nsfw' || (current.messages||[]).length) {
     createBlankConversation('auto');
   } else {
     openConversation(activeConversationId);
   }
   // The landing is always a neutral chat. Never inherit NSFW mode or a
   // forced video workflow from a prior dedicated creation session.
   byId('taskMode').value='chat';
   updateCreationModeGuide();
   welcome.classList.remove('hidden');
   messages.replaceChildren();
   document.body.classList.remove('is-chatting','show-diagnostics');
   document.body.classList.add('is-landing');
   prompt.value='';prompt.placeholder='Écris ton message…';prompt.blur();
   byId('generationSettings')?.classList.add('hidden');
   byId('settingsBtn')?.classList.remove('active');
   activeNav('navChat');
   hideSidebar();
 }
 function startMode(mode){
   window.StudioAds?.cancelChat?.();
   if(mode==='nsfw'){
     enterNsfwWorkspace(); // Preserves the existing PIN gate and all private settings.
     const current=activeConversationId?conversations[activeConversationId]:null;
     if(current?.profile!=='nsfw')return; // The locked gate will signal after authorization.
     clearModeCanvas('nsfw',{preserveConversation:true});
     return;
   }
   clearModeCanvas(mode);
   byId('taskMode').value=mode;
   updateSettingsVisibility();
   updateCreationModeGuide();
   prompt.placeholder=modeCopy[mode].placeholder;
   prompt.focus();
 }
 function gallery(){
   window.StudioAds?.cancelChat?.();
   if(activeGalleryPoll){window.clearInterval(activeGalleryPoll);activeGalleryPoll=null}
   document.body.dataset.visionMode='creations';
   darkMode();welcome.classList.add('hidden');
   activeNav('navCreations');hideSidebar();prompt.placeholder='Écris ton message…';
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
   const activeBox=document.createElement('section');
   activeBox.id='visionActiveGenerations';
   activeBox.className='vision-active-generations';
   activeBox.hidden=true;
   root.append(bar,activeBox,grid);
   messages.replaceChildren(root);
   byId('chat').scrollTop=0;
   let refreshing=false;
   async function refreshActiveMedia(){
     if(refreshing||!root.isConnected||document.hidden)return;
     refreshing=true;
     try{
       const response=await fetch('/api/studio/media/jobs',{cache:'no-store'});
       if(!response.ok)throw Error('ComfyUI ne répond pas');
       const data=await response.json();
       const jobs=Array.isArray(data.jobs)?data.jobs:[];
       activeBox.hidden=!jobs.length;
       activeBox.replaceChildren();
       if(jobs.length){
         const title=document.createElement('h3');
         title.textContent='Créations en cours · '+jobs.length;
         activeBox.append(title);
       }
       for(const job of jobs){
         const card=document.createElement('article');card.className='vision-active-card';
         const preview=document.createElement('div');preview.className='vision-active-preview';
         if(job.preview_ready){
           const image=document.createElement('img');
           image.src='/api/studio/media/preview?id='+encodeURIComponent(job.prompt_id)+'&t='+Date.now();
           image.alt='Aperçu ComfyUI flouté pendant le calcul';
           image.loading='lazy';
           preview.append(image);
         }
         const ring=document.createElement('div');ring.className='vision-progress-circle';
         window.StudioProgress?.render(ring,job);preview.append(ring);
         const details=document.createElement('div');details.className='vision-active-info';
         const name=document.createElement('strong');
         name.textContent=job.state==='preparing'?'Préparation '+(job.kind==='video'?'de la vidéo':'de l’image'):job.kind==='video'?'Vidéo en cours':'Image en cours';
         const state=document.createElement('p');
         state.textContent=job.phase||'ComfyUI prépare le modèle…';
         details.append(name,state);
         if(Number.isFinite(Number(job.started_at))){
           const elapsed=Math.max(0,Math.floor(Date.now()/1000-Number(job.started_at)));
           const duration=document.createElement('small');
           duration.textContent='Temps écoulé : '+Math.floor(elapsed/60)+' min '+String(elapsed%60).padStart(2,'0')+' s';
           details.append(duration);
           if(elapsed>300){
             const hint=document.createElement('small');
             hint.textContent='Rendu long : vérifie la file et l’usage GPU. Pour le prochain essai, les réglages « Vidéo rapide · 12 Go » réduisent le nombre d’images.';
             details.append(hint);
           }
         }
         if(Number.isInteger(job.percent)&&job.max_steps>0){
           const label=document.createElement('label');
           label.textContent='Étape de calcul : '+job.step+' / '+job.max_steps+' · '+job.percent+' %';
           const bar=document.createElement('progress');bar.value=job.step;bar.max=job.max_steps;
           bar.setAttribute('aria-label','Progression réelle de l’étape ComfyUI');
           details.append(label,bar);
         }else{
           const pending=document.createElement('small');
           pending.textContent='Progression chiffrée disponible dès que ComfyUI transmet ses étapes.';
           details.append(pending);
         }
         const cancel=document.createElement('button');
         cancel.type='button';cancel.className='vision-cancel-job';cancel.textContent='Annuler la génération';
         cancel.addEventListener('click',async()=>{
           cancel.disabled=true;cancel.textContent='Annulation…';
           try{
             const result=await fetch('/api/studio/media/cancel',{
               method:'POST',headers:{'Content-Type':'application/json','X-LocalAI-Media':'1'},
               body:JSON.stringify(job.request_ticket?{request_ticket:job.request_ticket}:{prompt_id:job.prompt_id}),credentials:'same-origin'
             });
             const reply=await result.json();
             if(!result.ok||!reply.ok)throw Error(reply.error||'Arrêt impossible');
             cancel.textContent='✓ Annulée';
             void refreshActiveMedia();
           }catch(error){cancel.disabled=false;cancel.textContent='Réessayer · '+error.message}
         });
         details.append(cancel);card.append(preview,details);activeBox.append(card);
       }
     }catch(error){
       // A connection loss is not proof that the generation has stopped.
       if(activeBox.childElementCount) {
         const note=document.createElement('p');note.textContent='Suivi temporairement indisponible : '+error.message;
         activeBox.append(note);
       }
     }finally{refreshing=false}
   }
   void refreshActiveMedia();
   activeGalleryPoll=window.setInterval(()=>{
     if(root.isConnected)void refreshActiveMedia();
     else{window.clearInterval(activeGalleryPoll);activeGalleryPoll=null}
   },1800);
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
         subfolder:pendingAsset.subfolder||'',type:pendingAsset.ad_url?'advert':(pendingAsset.type||'output')
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
 document.addEventListener('localai:nsfw-entered',()=>{
   // Called only after successful authorization; never expose a private welcome
   // or touch the NSFW generation pipelines while locked.
   clearModeCanvas('nsfw',{preserveConversation:true});
 });
 byId('navChat')?.addEventListener('click',home);
 byId('navCreations')?.addEventListener('click',gallery);
 byId('navPhoto')?.addEventListener('click',()=>startMode('image'));
 byId('navVideo')?.addEventListener('click',()=>startMode('video'));
 byId('navNsfw')?.addEventListener('click',()=>startMode('nsfw'));
 byId('visionAdvancedToggle')?.addEventListener('click',()=>{
   // Preserve historical LoRA controls without exposing a maze of settings
   // for each new generation: the natural-language prompt is authoritative.
   const panel=byId('generationSettings');
   panel?.classList.toggle('hidden');
   document.body.classList.toggle('vision-expert',!!panel&&!panel.classList.contains('hidden'));
   byId('accordionLoras')?.setAttribute('open','');
   if(!byId('generationSettings')?.classList.contains('hidden'))
     byId('generationSettings')?.scrollIntoView({block:'nearest',behavior:'instant'});
   hideSidebar();
 });
 byId('homeBtn')?.addEventListener('click',home);
 byId('newConversation')?.addEventListener('click',()=>{
   // Legacy handler creates the conversation; do not register a second one.
   const mode=document.body.dataset.visionMode;
   window.setTimeout(()=>{
     if(mode==='image'||mode==='video'){
       clearModeCanvas(mode,{preserveConversation:true});
       byId('taskMode').value=mode;
       updateCreationModeGuide();
     }else if(mode==='advert'){
       window.StudioAds?.startChat?.({reuseConversation:true});
     }else if(mode==='nsfw'){
       clearModeCanvas('nsfw',{preserveConversation:true});
     }else{
       home();
     }
     prompt.focus();
   },0);
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
   if(document.body.dataset.visionMode==='home' && !welcome.classList.contains('hidden') && !welcome.classList.contains('welcome-exiting')) {
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
       document.body.dataset.visionMode='history';
       welcome.replaceChildren(...originalWelcome.map(node=>node.cloneNode(true)));
       welcome.classList.remove('vision-onboarding');
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
 const requestedCreations=new URLSearchParams(window.location.search).get('view')==='creations';
 // Set a safe conversation mode immediately, before any engine/network probe settles.
 if(!requestedCreations)home();
 window.LocalAiVisionOpenCreations=gallery;
 window.localAiVisionInitialRefresh?.then(()=>{
   if(!userInteracted){if(requestedCreations)gallery();else home()}
 }).catch(()=>{
   if(!userInteracted){if(requestedCreations)gallery();else home()}
 });
 // Media services already start on demand when the first message is sent.
 // Do not display a Qwen health banner or require a window.confirm before
 // every photo request. Explicit repair is still available in Diagnostics.
 const recovery=byId('engineRecovery');
 if(recovery){recovery.hidden=true;recovery.setAttribute('aria-hidden','true')}
 if(!welcome.classList.contains('hidden'))document.body.classList.add('is-landing');
})();
