/* LocalAiWeb: non-destructive visual selection, scoped text requests. */
(()=>{
 const frame=document.getElementById('lawPreview'),stage=document.getElementById('lawPreviewStage');
 const toolbar=document.getElementById('lawSiteTools'),toggle=document.getElementById('lawInspectBtn');
 const pop=document.getElementById('lawInspectorPopover'),input=document.getElementById('lawInspectorPrompt');
 let active=false,selected=[],attached=null,start=null;
 let previousTouch={time:0,target:null};
 const q='h1,h2,h3,h4,p,a,button,img,video,input,textarea,select,label,li,article,section,[role="button"],div';
 function doc(){try{const d=frame.contentDocument;return d&&frame.contentWindow.location.origin===location.origin?d:null}catch{return null}}
 function allowed(el){
  if(!el||el.nodeType!==1||['HTML','BODY','SCRIPT','STYLE'].includes(el.tagName))return false;
  if(el.closest('[data-law-selection]'))return false;
  if(['DIV','SECTION'].includes(el.tagName)&&el.querySelector('h1,h2,h3,p,a,button,img,section,article'))return false;
  const r=el.getBoundingClientRect();if(r.width<9||r.height<7)return false;
  const c=el.ownerDocument.defaultView.getComputedStyle(el);
  return c.visibility!=='hidden'&&c.display!=='none'&&Number(c.opacity)>0;
 }
 function candidate(el){for(let n=el;n;n=n.parentElement)if(allowed(n))return n;return null}
 function clear(){for(const el of selected)try{el.classList.remove('law-picked')}catch{};selected=[];pop.hidden=true}
 function choose(elements,append=false){
  if(!append)clear();
  for(const el of elements){if(allowed(el)&&!selected.includes(el)&&selected.length<24){selected.push(el);el.classList.add('law-picked')}}
  if(selected.length&&active)document.getElementById('lawChatStatus').textContent=selected.length+' élément(s) sélectionné(s) — écris la modification dans le champ affiché';
 }
 function cssPath(el){
  const steps=[];for(let e=el;e&&e.tagName&&!['HTML','BODY'].includes(e.tagName)&&steps.length<10;e=e.parentElement){
   if(e.id && e.id.length<80){steps.unshift('#'+CSS.escape(e.id));break}
   const siblings=e.parentElement?Array.from(e.parentElement.children).filter(n=>n.tagName===e.tagName):[e];
   steps.unshift(e.tagName.toLowerCase()+(siblings.length>1?':nth-of-type('+(siblings.indexOf(e)+1)+')':''));
  }return steps.join(' > ');
 }
 function editAt(x,y){
  if(!active||!selected.length)return;
  const r=frame.getBoundingClientRect(),outer=stage.getBoundingClientRect();
  pop.style.left=Math.max(8,Math.min(r.left+x-outer.left+12,stage.clientWidth-320))+'px';
  pop.style.top=Math.max(8,Math.min(r.top+y-outer.top+12,stage.clientHeight-180))+'px';
  input.value='';pop.hidden=false;input.focus({preventScroll:true});
 }
 function attach(d){
  if(!d||attached===d)return;
  clear();attached=d;
  const style=d.createElement('style');style.id='law-selector-css';
  style.textContent='html.law-select,html.law-select *{cursor:crosshair!important}.law-picked{outline:2px dashed #9967f9!important;outline-offset:2px!important}.law-drag{position:fixed;z-index:2147483646;pointer-events:none;border:2px dashed #8355e9;background:#8355e926;border-radius:3px}';
  (d.head||d.documentElement).append(style);
  const box=d.createElement('div');box.className='law-drag';box.dataset.lawSelection='1';box.hidden=true;box.style.display='none';d.body.append(box);
  d.documentElement.classList.toggle('law-select',active);
  d.addEventListener('pointerdown',ev=>{
   if(!active||ev.button!==0)return;start={x:ev.clientX,y:ev.clientY,shift:ev.shiftKey,drag:false};
   ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('pointermove',ev=>{
   if(!active||!start)return;
   if(Math.hypot(ev.clientX-start.x,ev.clientY-start.y)<7)return;
   start.drag=true;box.style.display='block';
   box.style.left=Math.min(ev.clientX,start.x)+'px';box.style.top=Math.min(ev.clientY,start.y)+'px';
   box.style.width=Math.abs(ev.clientX-start.x)+'px';box.style.height=Math.abs(ev.clientY-start.y)+'px';
   ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('pointerup',ev=>{
   if(!active||!start)return;
   const first=start;start=null;box.style.display='none';
   if(first.drag){
    const x1=Math.min(first.x,ev.clientX),x2=Math.max(first.x,ev.clientX);
    const y1=Math.min(first.y,ev.clientY),y2=Math.max(first.y,ev.clientY);
    const hits=Array.from(d.querySelectorAll(q)).filter(el=>{
     if(!allowed(el))return false;const r=el.getBoundingClientRect();
     return r.left<x2&&r.right>x1&&r.top<y2&&r.bottom>y1;
    }).slice(0,24);
    choose(hits,first.shift);
    if(selected.length)editAt(ev.clientX,ev.clientY);
   }else{
    const item=candidate(ev.target);
    const now=Date.now();
    const doubleTap=ev.pointerType==='touch'&&item&&
      previousTouch.target===item&&now-previousTouch.time<550;
    if(item)choose([item],first.shift);else if(!first.shift)clear();
    // One click is enough. Opening the text area synchronously with the
    // pointer event also lets touch keyboards appear on supported devices.
    if(item)editAt(ev.clientX,ev.clientY);
    previousTouch={time:now,target:item};
   }
   ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('click',ev=>{
   if(!active)return;
   if(ev.detail>=2)editAt(ev.clientX,ev.clientY);
   ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('dblclick',ev=>{
   if(!active)return;
   if(!selected.length){const el=candidate(ev.target);if(el)choose([el])}
   editAt(ev.clientX,ev.clientY);ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('dragstart',ev=>{if(active){ev.preventDefault();ev.stopImmediatePropagation()}},true);
  d.addEventListener('keydown',ev=>{if(active&&ev.key==='Escape'){disable();ev.preventDefault()}},true);
 }
 function disable(){
  active=false;start=null;previousTouch={time:0,target:null};clear();toggle.classList.remove('active');toggle.setAttribute('aria-pressed','false');
  const d=doc();if(d)d.documentElement.classList.remove('law-select');
  if(!busy)document.getElementById('lawChatStatus').textContent='Prêt à créer ton site';
 }
 toggle.addEventListener('click',()=>{
  if(!project||busy)return;
  if(active){disable();return}
  const d=doc();if(!d){alert('Prévisualisation locale indisponible.');return}
  active=true;toggle.classList.add('active');toggle.setAttribute('aria-pressed','true');
  attach(d);d.documentElement.classList.add('law-select');
  document.getElementById('lawChatStatus').textContent=
   'Clique sur un élément ou encadre une zone : le champ de modification apparaît immédiatement.';
 });
 document.getElementById('lawInspectorCancel').addEventListener('click',()=>{pop.hidden=true;input.value=''});
 async function submit(){
  if(!project||busy||!selected.length||!input.value.trim())return;
  let page='/';try{page=frame.contentWindow.location.pathname+frame.contentWindow.location.hash}catch{}
  const items=selected.map((el,i)=>{
   const label=String(el.innerText||el.alt||el.value||el.getAttribute('aria-label')||'').replace(/\s+/g,' ').trim().slice(0,130);
   return (i+1)+'. '+el.tagName.toLowerCase()+' | '+cssPath(el)+(label?' | texte : « '+label+' »':'');
  }).join('\n');
  const text='MODIFICATION CIBLÉE DE LA PRÉVISUALISATION — '+project.project.name+
   '\nPage : '+page+'\nÉléments sélectionnés :\n'+items+
   '\n\nDemande : '+input.value.trim()+
   '\n\nTrouve ces éléments grâce aux sélecteurs et aux textes dans les fichiers de cette page. '+
   'Modifie ces éléments précisément en préservant toutes les autres pages, la navigation, '+
   'les fonctionnalités et le français.';
  disable();await sendText(text);
 }
 document.getElementById('lawInspectorSubmit').addEventListener('click',submit);
 input.addEventListener('keydown',ev=>{
  if(ev.key==='Enter'&&(ev.ctrlKey||ev.metaKey)){ev.preventDefault();submit()}
  if(ev.key==='Escape'){pop.hidden=true;input.value=''}
 });
 document.getElementById('lawBrowserBtn').addEventListener('click',async()=>{
  if(!project?.project?.id)return;
  if(/iPhone|iPad|Android/i.test(navigator.userAgent)){
   // Open the generated site on this phone, not in the PC's browser.
   window.open('/web-preview/'+encodeURIComponent(project.project.id)+'/index.html',
      '_blank','noopener,noreferrer');
   return;
  }
  try{await api('/api/web/open-browser',{id:project.project.id})}
  catch(err){alert('Impossible d’ouvrir le navigateur : '+err.message)}
 });
 document.getElementById('lawZipBtn').addEventListener('click',()=>exportSite());
 async function refresh(){
  if(!project)return;
  try{
   const v=await api('/api/web/preview/status?id='+encodeURIComponent(project.project.id));
   toolbar.hidden=!v.ready;if(!v.ready)disable();else if(active)attach(doc());
  }catch{toolbar.hidden=true;disable()}
 }
 frame.addEventListener('load',()=>{attach(doc());refresh()});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
 refresh();
})();
