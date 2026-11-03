/* QCM V1 map: working France recenter control, never fake map readiness. */
(()=>{'use strict';
const area=document.querySelector('.map-area');if(!area)return;
const button=document.createElement('button');
button.type='button';button.className='qcm-map-recenter';button.textContent='⌖ France';
button.setAttribute('aria-label','Recentrer la carte sur la France');
button.title='Revenir à la vue France';button.disabled=typeof window.StudioMapRecenter!=='function';
button.addEventListener('click',()=>{if(typeof window.StudioMapRecenter==='function')window.StudioMapRecenter()});
area.append(button);
window.addEventListener('studio-map-ready',()=>{button.disabled=false});
})();