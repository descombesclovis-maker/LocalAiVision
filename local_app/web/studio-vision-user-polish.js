/* Build 316: focused public Vision usability enhancements. No private workspace changes. */
(()=>{
 'use strict';
 if(document.body.dataset.studioPage!=='vision')return;
 const isPrivate=()=>document.body.classList.contains('nsfw-active');
 const $=s=>document.querySelector(s);
 // Only crisp cyan vectors belong in the hamburger drawer. Native emoji remain in the side rails.
 function makeIcon(d){
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');
  const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);
  svg.append(path);return svg;
 }
 // Premium dual-stroke drawings replace coarse single-line SVG pictograms.
 const navPaths={
  navChat:['M5.1 6.3a8.7 8.7 0 0 1 13.8 10.4A8.6 8.6 0 0 1 9.9 19l-5.8 2 1.3-5A8.7 8.7 0 0 1 5.1 6.3z','M8 10.2h8M8 13.8h5.7'],
  navCreations:['M4 4.2h6.4v6.4H4zM13.6 4.2H20v6.4h-6.4zM4 13.6h6.4V20H4zM13.6 13.6H20V20h-6.4z','M15.4 16.7l1.35-1.5 1.1 1.05'],
  navPhoto:['M3.7 7.3h4.4l1.5-2.6h4.8l1.5 2.6h4.4c.6 0 1 .5 1 1.1v10.2c0 .7-.5 1.2-1.1 1.2H3.8c-.7 0-1.1-.5-1.1-1.2V8.5c0-.7.4-1.2 1-1.2zM16.2 13.3a4.2 4.2 0 1 1-8.4 0 4.2 4.2 0 1 1 8.4 0z','M17.9 9.9h.2M10.6 13.4h2.8'],
  navVideo:['M4 5h12.6c.8 0 1.4.6 1.4 1.4v11.3c0 .8-.6 1.3-1.4 1.3H4c-.8 0-1.4-.5-1.4-1.3V6.4C2.6 5.6 3.2 5 4 5zM18 9.1l3.2-2.2v10.3L18 15','M8.4 9.1l5.3 3.2-5.3 3.2zM6 7.2h.2'],
  navNsfw:['M12 2.4 4.1 6.3v5.6c0 4.8 3 8.1 7.9 9.7 4.9-1.6 7.9-4.9 7.9-9.7V6.3L12 2.4zM9.1 11.3h5.8v5.2H9.1zM10 11.3V9.6a2 2 0 0 1 4 0v1.7','M12 13.5v1.1'],
  studioAdOpen:['M3.2 9.6 14.7 5v14L3.2 14.4zM14.7 8.6h3.2a2.5 2.5 0 0 1 0 5h-3.2M6.1 15.6l1.6 4h3.6l-1.5-3.6','M19 4l.8-1.5M21 8l1.4-.4']
 };
 function makePremiumIcon(id){
  const paths=navPaths[id]||[];
  const icon=makeIcon(paths[0]||'');
  icon.classList.add('vision-premium-icon');
  if(paths[1]){
   const accent=document.createElementNS(icon.namespaceURI,'path');
   accent.classList.add('vision-nav-accent');
   accent.setAttribute('d',paths[1]);icon.append(accent);
  }
  return icon;
 }
 function enhanceNavigation(){
  for(const id of Object.keys(navPaths)){
   const node=document.getElementById(id);
   if(!node)continue;
   // Remove only emoji accidentally inserted into this hamburger menu.
   node.querySelectorAll('.vision-nav-emoji,.public-mode-icon').forEach(icon=>icon.remove());
   const glyph=node.querySelector('.nav-glyph');
   if(glyph&&!glyph.dataset.vectorPolished){glyph.replaceChildren(makePremiumIcon(id));glyph.dataset.vectorPolished='true'}
  }
  // All creation destinations receive a motion chevron. LoRA is a settings action, never a mode.
  for(const id of ['navChat','navCreations','navPhoto','navVideo','navNsfw','studioAdOpen']){
   const node=document.getElementById(id);
   if(!node||node.querySelector('.vision-menu-chevron'))continue;
   const arrow=document.createElement('span');arrow.className='vision-menu-chevron';
   arrow.setAttribute('aria-hidden','true');
   arrow.append(makeIcon('M8.5 5.5 15 12l-6.5 6.5'));
   node.append(arrow);
  }
  const history=$('#historyBtn');
  if(history){
   history.querySelectorAll('.vision-nav-emoji').forEach(icon=>icon.remove());
   if(!history.dataset.visionIconReady){
    history.dataset.visionIconReady='1';
    const first=[...history.childNodes].find(n=>n.nodeType===3);
    if(first)first.remove();
    const glyph=document.createElement('span');glyph.className='nav-glyph history-glyph';
    glyph.append(makeIcon('M12 4a8 8 0 1 1-7.65 10.32M4 4v5h5M12 7v5l3 2'));
    history.prepend(glyph);
   }
  }
 }

 enhanceNavigation();

 // LoRA quick access is a true cyan desktop settings panel, without altering model state.
 const loraButton=document.getElementById('visionAdvancedToggle');
 const loraDialog=document.getElementById('generationSettings');
 function updateLoraDialogState(){
  const active=!isPrivate()&&document.body.classList.contains('vision-lora-dialog')&&loraDialog&&!loraDialog.classList.contains('hidden');
  if(!active)document.body.classList.remove('vision-lora-dialog');
 }
 loraButton?.addEventListener('click',()=>{
  if(isPrivate())return;
  requestAnimationFrame(()=>{
   if(!loraDialog?.classList.contains('hidden')){
    document.body.classList.add('vision-lora-dialog');
    loraDialog.setAttribute('aria-modal','true');
    loraDialog.setAttribute('aria-label','LoRA et modèles · LocalAiVision');
    loraDialog.querySelector('#loraSearch')?.focus({preventScroll:true});
   }else{
    document.body.classList.remove('vision-lora-dialog');
    loraDialog?.removeAttribute('aria-modal');
   }
  });
 });
 if(loraDialog)new MutationObserver(updateLoraDialogState).observe(loraDialog,{attributes:true,attributeFilter:['class']});
 document.getElementById('closeSettings')?.addEventListener('click',()=>document.body.classList.remove('vision-lora-dialog'));
 document.getElementById('settingsBtn')?.addEventListener('click',()=>document.body.classList.remove('vision-lora-dialog'));
 document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&document.body.classList.contains('vision-lora-dialog')){
   document.body.classList.remove('vision-lora-dialog');
   loraDialog?.classList.add('hidden');loraDialog?.removeAttribute('aria-modal');
   loraButton?.focus({preventScroll:true});
  }
 });


 const viewer=document.createElement('dialog');
 viewer.className='vision-gallery-modal';viewer.setAttribute('aria-label','Création en grand');
 viewer.innerHTML='<header><strong>Ma création</strong><button type="button" class="vision-dialog-close" aria-label="Fermer">×</button></header><div class="vision-gallery-stage"></div><footer><a class="vision-gallery-download" download>Télécharger</a><button type="button" class="vision-dialog-close">Fermer</button></footer>';
 document.body.append(viewer);
 const previewStage=viewer.querySelector('.vision-gallery-stage');
 function closePreview(){if(viewer.open)viewer.close();previewStage.replaceChildren()}
 viewer.querySelectorAll('.vision-dialog-close').forEach(b=>b.addEventListener('click',closePreview));
 viewer.addEventListener('click',e=>{if(e.target===viewer)closePreview()});
 viewer.addEventListener('close',()=>previewStage.replaceChildren());

 function safeUrl(raw){
  try{const u=new URL(raw,location.href);return u.origin===location.origin&&['http:','https:'].includes(u.protocol)?u.href:null}
  catch{return null}
 }
 function showPreview(raw,kind){
  if(isPrivate())return;
  const url=safeUrl(raw);if(!url)return;
  const node=document.createElement(kind==='video'?'video':'img');
  node.src=url;node.className='vision-gallery-fullmedia';
  if(kind==='video'){node.controls=true;node.playsInline=true;node.preload='metadata'}
  else node.alt='Création sélectionnée en taille réelle';
  previewStage.replaceChildren(node);
  const a=viewer.querySelector('.vision-gallery-download');a.href=url;
  const name=new URL(url).searchParams.get('filename')||'creation-localaivision';
  a.download=name.replace(/[\/\\]/g,'_');
  if(!viewer.open)viewer.showModal();
 }

 window.LocalAiVisionPreviewMedia=showPreview;

 const editor=document.createElement('dialog');editor.className='vision-image-editor';
 editor.setAttribute('aria-label',"Modifier l'image sans toucher à l'original");
 editor.innerHTML='<header><strong>Modifier la photo</strong><button type="button" class="vision-editor-close" aria-label="Fermer">×</button></header><div class="vision-editor-stage"><canvas aria-label="Aperçu de la photo modifiée"></canvas></div><div class="vision-editor-controls"><label>Luminosité <input id="visionEditBrightness" type="range" min="50" max="150" value="100"><output>100 %</output></label><label>Contraste <input id="visionEditContrast" type="range" min="50" max="150" value="100"><output>100 %</output></label><label>Saturation <input id="visionEditSaturation" type="range" min="0" max="200" value="100"><output>100 %</output></label></div><footer><button type="button" id="visionEditorRotate">↻ Pivoter</button><button type="button" id="visionEditorReset">Réinitialiser</button><button type="button" id="visionEditorSave">Enregistrer une copie PNG</button></footer><p class="vision-editor-status" role="status" aria-live="polite">La photo d’origine reste intacte.</p>';
 document.body.append(editor);
 const canvas=editor.querySelector('canvas'),ctx=canvas.getContext('2d');
 const sliders=[...editor.querySelectorAll('.vision-editor-controls input')];
 const editorStatus=editor.querySelector('.vision-editor-status');
 let sourceImage=null,turn=0,sourceName='creation';
 function closeEditor(){if(editor.open)editor.close();sourceImage=null}
 editor.querySelector('.vision-editor-close').addEventListener('click',closeEditor);
 editor.addEventListener('click',e=>{if(e.target===editor)closeEditor()});
 editor.addEventListener('close',()=>{sourceImage=null});
 function draw(){
  if(!sourceImage||!ctx)return;
  const originalW=sourceImage.naturalWidth,originalH=sourceImage.naturalHeight;
  // Cap editing resolution to avoid exhausting RAM on large 4K images.
  const scale=Math.min(1,4096/Math.max(originalW,originalH));
  const w=Math.max(1,Math.round(originalW*scale)),h=Math.max(1,Math.round(originalH*scale));
  canvas.width=turn%2?h:w;canvas.height=turn%2?w:h;
  const [brightness,contrast,saturation]=sliders.map(x=>Number(x.value));
  ctx.save();ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.translate(canvas.width/2,canvas.height/2);ctx.rotate(turn*Math.PI/2);
  ctx.filter='brightness('+brightness+'%) contrast('+contrast+'%) saturate('+saturation+'%)';
  ctx.drawImage(sourceImage,-w/2,-h/2,w,h);ctx.restore();
  for(const slider of sliders)slider.nextElementSibling.textContent=slider.value+' %';
 }
 sliders.forEach(x=>x.addEventListener('input',draw));
 editor.querySelector('#visionEditorRotate').addEventListener('click',()=>{turn=(turn+1)%4;draw()});
 editor.querySelector('#visionEditorReset').addEventListener('click',()=>{
  turn=0;for(const x of sliders)x.value='100';draw();
 });
 editor.querySelector('#visionEditorSave').addEventListener('click',()=>{
  if(!sourceImage)return;
  canvas.toBlob(blob=>{
   if(!blob){editorStatus.textContent='Enregistrement impossible.';return}
   const url=URL.createObjectURL(blob),a=document.createElement('a');
   a.href=url;a.download=sourceName.replace(/\.[^.]+$/,'')+'-modifiee.png';a.click();
   setTimeout(()=>URL.revokeObjectURL(url),60000);
   editorStatus.textContent='Copie PNG enregistrée ; original préservé.';
  },'image/png');
 });
 async function editImage(raw,name){
  if(isPrivate())return;
  const url=safeUrl(raw);if(!url)return;
  try{
   const response=await fetch(url,{credentials:'same-origin',cache:'no-store'});
   if(!response.ok)throw Error('Fichier indisponible');
   const blob=await response.blob();
   if(!blob.type.startsWith('image/'))throw Error('Ce fichier n’est pas une image');
   if(blob.size>48*1024*1024)throw Error('Image trop volumineuse');
   const objectUrl=URL.createObjectURL(blob);
   const image=new Image();image.src=objectUrl;
   await image.decode();URL.revokeObjectURL(objectUrl);
   sourceName=name||'creation';sourceImage=image;turn=0;
   for(const slider of sliders)slider.value='100';
   draw();editorStatus.textContent='Modifications locales, sans IA. L’original reste intact.';
   if(!editor.open)editor.showModal();
  }catch(error){editorStatus.textContent='Ouverture impossible : '+error.message;alert('Retouche indisponible : '+error.message)}
 }

 async function reuseInPrompt(entry,raw,kind){
  if(isPrivate())return;
  if(kind!=='image'){
   $('#navVideo')?.click();$('#prompt').value=entry?.prompt||'';
   $('#prompt').focus();return;
  }
  const url=safeUrl(raw);if(!url)return;
  try{
   const response=await fetch(url,{credentials:'same-origin'});
   if(!response.ok)throw Error('Fichier indisponible');
   const blob=await response.blob();
   if(!blob.type.startsWith('image/'))throw Error('Image illisible');
   if(blob.size>16*1024*1024)throw Error('Image trop volumineuse pour une référence (16 Mo max)');
   const file=new File([blob],entry?.filename||'creation.png',{type:blob.type});
   $('#navVideo')?.click();
   $('#taskMode').value='i2v';updateCreationModeGuide();
   loadReferenceImage(file);
   $('#prompt').value='Anime cette image : ';
   $('#prompt').focus();
  }catch(error){alert('Impossible de réutiliser cette création : '+error.message)}
 }

 let activeMenu=null;
 function closeMenu(){
  if(!activeMenu)return;
  activeMenu.hidden=true;
  activeMenu.parentElement?.querySelector('.vision-gallery-more')?.setAttribute('aria-expanded','false');
  activeMenu=null;
 }
 document.addEventListener('pointerdown',event=>{if(activeMenu&&!activeMenu.parentElement.contains(event.target))closeMenu()});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&activeMenu){closeMenu();event.stopPropagation()}});

 function enhanceCard(card){
  if(card.dataset.visionCardEnhanced||isPrivate())return;
  const media=card.querySelector('img,video');
  if(!media)return;
  const raw=media.getAttribute('src');
  if(!safeUrl(raw))return;
  card.dataset.visionCardEnhanced='1';
  const kind=media.tagName==='VIDEO'?'video':'image';
  const resolved=typeof library!=='undefined'
   ?library.find(x=>x.profile!=='nsfw'&&x._id===card.dataset.entryId)
     ||library.find(x=>x.profile!=='nsfw'&&resultUrl(x)===raw)
   :null;
  const item=resolved||{filename:'creation.png',prompt:''};
  // The gallery thumbnail always opens an enlarged media viewer.
  if(media.tagName==='VIDEO')media.controls=false;
  media.tabIndex=0;media.setAttribute('role','button');
  media.setAttribute('aria-label','Ouvrir la création en grand');
  media.addEventListener('click',()=>showPreview(raw,kind));
  media.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();showPreview(raw,kind)}});
  const more=document.createElement('button');more.type='button';more.className='vision-gallery-more';
  more.textContent='⋯';more.title='Options de la création';more.setAttribute('aria-label','Options de la création');
  more.setAttribute('aria-haspopup','menu');more.setAttribute('aria-expanded','false');
  const options=document.createElement('div');options.className='vision-gallery-options';options.role='menu';options.hidden=true;
  function option(label,fn,kind=''){
   const b=document.createElement('button');b.type='button';b.role='menuitem';b.textContent=label;
   if(kind)b.className=kind;
   b.addEventListener('click',async e=>{e.stopPropagation();closeMenu();await fn()});options.append(b);
   return b;
  }
  const existingRemove=card.querySelector('.gallery-actions button[title="Supprimer cette création"],.library-delete');
  option('Réutiliser dans un prompt',()=>reuseInPrompt(item,raw,kind));
  if(kind==='image')option('Modifier la photo',()=>editImage(raw,item.filename));
  else option('Modifier la vidéo',()=>alert('La retouche vidéo directe n’est pas encore disponible. La vidéo originale est conservée.'));
  option('Supprimer de la galerie',()=>{if(existingRemove)existingRemove.click();else if(item._id)deleteLibraryItem(item._id)},'danger');
  more.addEventListener('click',e=>{
   e.stopPropagation();if(activeMenu===options){closeMenu();return}
   closeMenu();options.hidden=false;more.setAttribute('aria-expanded','true');activeMenu=options;
   options.querySelector('button')?.focus();
  });
  card.append(more,options);
  // Preserve the existing Add to Web action; open/delete are replaced by preview/menu.
  card.querySelector('.gallery-actions a')?.classList.add('vision-gallery-legacy-open');
  if(existingRemove)existingRemove.classList.add('vision-gallery-legacy-delete');
  card.querySelector('.qcm-library-preview')?.classList.add('vision-gallery-legacy-open');
 }
 function enhance(){
  if(isPrivate()){closeMenu();if(viewer.open)closePreview();if(editor.open)closeEditor();return}
  enhanceNavigation();
  document.querySelectorAll('#messages .gallery-card,#messages .library-card').forEach(enhanceCard);
 }
 new MutationObserver(enhance).observe(document.getElementById('messages'),{childList:true,subtree:true});
 new MutationObserver(enhance).observe(document.body,{attributes:true,attributeFilter:['class']});
 enhance();
})();