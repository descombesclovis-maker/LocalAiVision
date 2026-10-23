/* iPhone-specific presentation of the existing LocalAiWeb tools.
 * All project, generation, map, preview and publishing APIs remain server-owned.
 * This script cannot replace the Windows code-agent/GPU backend by itself.
 */
(()=>{'use strict';
 const standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
 document.documentElement.classList.add('law-app');
 if(standalone)document.documentElement.classList.add('law-standalone');
 const install=document.getElementById('installLocalAi');
 if(install){install.title="Installer LocalAiWeb sur l'écran d'accueil";install.setAttribute('aria-label','Installer LocalAiWeb');}
 const studio=document.querySelector('.studio');
 if(!studio)return;
 const mobile=matchMedia('(max-width: 700px)');
 const chat=document.querySelector('.chat-pane'),preview=document.querySelector('.preview-pane');
 if(!chat||!preview)return;
 const nav=document.createElement('nav');nav.className='law-mobile-nav';nav.setAttribute('aria-label','Navigation LocalAiWeb');
 const buttons=new Map();
 function tabButton(view,label){
  const b=document.createElement('button');b.type='button';b.dataset.view=view;b.textContent=label;
  b.setAttribute('role','tab');b.addEventListener('click',()=>setView(view));
  nav.appendChild(b);buttons.set(view,b);
 }
 nav.setAttribute('role','tablist');tabButton('chat','✦ Conversation');tabButton('preview','▣ Aperçu du site');
 document.body.appendChild(nav);
 let selected='chat';
 function setView(view){
  if(!buttons.has(view))return;
  selected=view;
  document.body.dataset.lawMobileView=selected;
  for(const [key,b] of buttons)b.setAttribute('aria-selected',String(key===selected));
  chat.setAttribute('aria-hidden',String(mobile.matches&&selected!=='chat'));
  preview.setAttribute('aria-hidden',String(mobile.matches&&selected!=='preview'));
 }
 function sync(){
  document.body.classList.toggle('law-editor-mobile',mobile.matches);
  if(!mobile.matches){chat.removeAttribute('aria-hidden');preview.removeAttribute('aria-hidden');}
  else setView(selected);
 }
 if(mobile.addEventListener)mobile.addEventListener('change',sync);else mobile.addListener(sync);
 sync();
 // Once a genuine project preview is loaded, bring it to the foreground on iPhone.
 const frame=document.getElementById('lawPreview');
 if(frame)frame.addEventListener('load',()=>{
  if(!mobile.matches)return;
  try{const url=new URL(frame.src,location.href);if(url.pathname.startsWith('/web-preview/'))setView('preview');}
  catch{/* Nothing to display yet. */}
 });
 // The Windows-only "open browser" API is not meaningful on an iPhone:
 // open the already generated preview in Safari instead.
 const browser=document.getElementById('lawBrowserBtn');
 if(browser)browser.addEventListener('click',event=>{
   if(!mobile.matches)return;
   event.preventDefault();event.stopImmediatePropagation();
   if(!frame||!frame.src||!new URL(frame.src,location.href).pathname.startsWith('/web-preview/'))return;
   window.open(frame.src,'_blank','noopener,noreferrer');
 },true);
})();
