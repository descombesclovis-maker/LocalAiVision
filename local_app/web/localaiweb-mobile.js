/* iPhone-first studio: a native-feeling bottom tab bar without recreating the
   project, refreshing the iframe or interrupting an AI generation. */
(()=>{
 'use strict';
 const nav=document.getElementById('lawMobileTabs');
 if(!nav)return;
 const mobile=window.matchMedia('(max-width:700px)');
 const buttons=[...nav.querySelectorAll('[data-mobile-panel]')];
 let active='chat';
 const show=next=>{
   if(!['chat','preview'].includes(next))return;
   active=next;
   document.body.dataset.lawPanel=next;
   for(const btn of buttons){
     const selected=btn.dataset.mobilePanel===next;
     btn.setAttribute('aria-selected',String(selected));
   }
   // Keep the preview iframe intact across switches: no repeated 3D loads.
   if(next==='preview'){
     const frame=document.getElementById('lawPreview');
     if(frame)frame.title='Prévisualisation du site — affichage mobile';
   }
 };
 for(const button of buttons){
   button.addEventListener('click',()=>show(button.dataset.mobilePanel));
 }
 function resize(){
   nav.hidden=!mobile.matches;
   if(mobile.matches)show(active);
   else delete document.body.dataset.lawPanel;
 }
 mobile.addEventListener?.('change',resize);
 resize();
 // Avoid keeping the preview in memory until requested on slow mobile pages:
 // the server still computes and persists the actual web project.
})();
