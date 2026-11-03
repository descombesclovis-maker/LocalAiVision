/* Motion is purely progressive enhancement: links work before JS and without JS. */
(()=>{'use strict';
 const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
 const pointer=window.matchMedia('(hover: hover) and (pointer: fine)');
 const cards=[...document.querySelectorAll('.universe-card')];
 const wash=document.createElement('div');
 wash.className='studio-transition-wash';
 wash.setAttribute('aria-hidden','true');
 document.body.appendChild(wash);
 let navigating=false;
 for(const card of cards){
   card.addEventListener('click',event=>{
     if(navigating||document.body.classList.contains('qcm-reduce-motion')||motion.matches||document.body.classList.contains('studio-motion-reduced')||document.body.dataset.studioTransition==='instant'||!pointer.matches||event.defaultPrevented ||
       event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||event.button!==0)return;
     const target=card.getAttribute('href');
     if(!target||!target.startsWith('/'))return;
     event.preventDefault();navigating=true;
     const rect=card.getBoundingClientRect();
     wash.style.setProperty('--transition-x',Math.round((rect.left+rect.width/2)/innerWidth*100)+'%');
     wash.style.setProperty('--transition-y',Math.round((rect.top+rect.height/2)/innerHeight*100)+'%');
     card.classList.add('studio-selected');
     document.body.classList.add('studio-entering');
     // Keep transitions short and deterministic; never trap navigation.
     window.setTimeout(()=>window.location.assign(target),190);
   });
 }
 window.addEventListener('pageshow',()=>{
   navigating=false;
   document.body.classList.remove('studio-entering');
   cards.forEach(card=>card.classList.remove('studio-selected'));
 });
})();
