/* iPhone-first studio: a native-feeling bottom tab bar without recreating the
   project, refreshing the iframe or interrupting an AI generation. */
(()=>{
 'use strict';
 const nav=document.getElementById('lawMobileTabs');
 if(!nav)return;
 const mobile=window.matchMedia('(max-width:700px), (max-width:1000px) and (pointer:coarse)');
 const buttons=[...nav.querySelectorAll('[data-mobile-panel]')];
 const menu=document.getElementById('lawMobileTools');
 const toggle=document.getElementById('lawMobileMenuToggle');
 const header=document.querySelector('.studio .chat-header');
 const agent=header?.querySelector('.agent-workspace');
 const brand=header?.querySelector('.law-brand-workspace');
 const version=header?.querySelector('#lawUpdateBtn');
 const slot=document.getElementById('lawMobileAgentSlot');
 const brandSlot=document.getElementById('lawMobileBrandSlot');
 const versionSlot=document.getElementById('lawMobileVersionSlot');
 const agentAnchor=document.createComment('restore agent controls');
 const brandAnchor=document.createComment('restore brand controls');
 const versionAnchor=document.createComment('restore update indicator');
 if(agent)agent.before(agentAnchor);
 if(brand)brand.before(brandAnchor);
 if(version)version.before(versionAnchor);
 const closeMenu=()=>{
   if(!menu||!toggle)return;
   menu.hidden=true;toggle.setAttribute('aria-expanded','false');
 };
 if(toggle&&menu){
   toggle.addEventListener('click',()=>{
     const open=menu.hidden;
     menu.hidden=!open;
     toggle.setAttribute('aria-expanded',String(open));
   });
   document.addEventListener('pointerdown',event=>{
     if(!menu.hidden&&!menu.contains(event.target)&&!toggle.contains(event.target))
       closeMenu();
   });
   document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu()});
 }

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
 document.getElementById('lawMobileToolsTab')?.addEventListener('click',()=>{
   show('chat');
   if(menu.hidden)toggle.click();
   toggle.focus({preventScroll:true});
 });
 function resize(){
   nav.hidden=!mobile.matches;
   closeMenu();
   if(mobile.matches){
     if(agent&&slot&&agent.parentElement!==slot)slot.append(agent);
     if(brand&&brandSlot&&brand.parentElement!==brandSlot)brandSlot.append(brand);
     if(version&&versionSlot&&version.parentElement!==versionSlot)versionSlot.append(version);
     show(active);
     // Show the genuine responsive phone rendering first. Desktop/tablet
     // preview modes remain one tap away and do not alter generated files.
     if(!document.body.dataset.lawMobileInitialized){
       document.body.dataset.lawMobileInitialized='1';
       document.querySelector('[data-view="mobile"]')?.click();
     }
   }else{
     delete document.body.dataset.lawPanel;
     if(agent&&agentAnchor.parentNode)agentAnchor.after(agent);
     if(brand&&brandAnchor.parentNode)brandAnchor.after(brand);
     if(version&&versionAnchor.parentNode)versionAnchor.after(version);
   }
 }
 mobile.addEventListener?.('change',resize);
 resize();
 // Avoid keeping the preview in memory until requested on slow mobile pages:
 // the server still computes and persists the actual web project.
})();
