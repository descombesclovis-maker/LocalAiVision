/* Motion is purely progressive enhancement: links work before JS and without JS. */
(()=>{'use strict';
 const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
 const pointer=window.matchMedia('(hover: hover) and (pointer: fine)');
 const cards=[...document.querySelectorAll('.universe-card')];
 if(!pointer.matches||motion.matches)return;
 const frame=new WeakMap();
 for(const card of cards){
   let lastEvent=null;
   card.addEventListener('pointermove',event=>{
     lastEvent=event;
     if(frame.get(card))return;
     const tick=requestAnimationFrame(()=>{
       frame.delete(card);
       if(!lastEvent||motion.matches)return;
       const bounds=card.getBoundingClientRect();
       const x=(lastEvent.clientX-bounds.left)/bounds.width;
       const y=(lastEvent.clientY-bounds.top)/bounds.height;
       card.style.setProperty('--pointer-x',(x*100).toFixed(1)+'%');
       card.style.setProperty('--pointer-y',(y*100).toFixed(1)+'%');
       card.style.transform='perspective(1400px) rotateX('+((.5-y)*2).toFixed(2)+'deg) rotateY('+((x-.5)*2).toFixed(2)+'deg) translateY(-4px)';
     });
     frame.set(card,tick);
   },{passive:true});
   const reset=()=>{
     const tick=frame.get(card);if(tick)cancelAnimationFrame(tick);
     frame.delete(card);lastEvent=null;
     card.style.transform='';
     card.style.removeProperty('--pointer-x');
     card.style.removeProperty('--pointer-y');
   };
   card.addEventListener('pointerleave',reset);
   card.addEventListener('blur',reset);
   motion.addEventListener('change',reset);
 }
})();
