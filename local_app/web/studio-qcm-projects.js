/* QCM V1 project library: functional Pro/Libre tabs and project creation tiles.
 * Existing project cards, filters, persistence and generation workers remain intact.
 */
(()=>{'use strict';
const free=document.querySelector('.library:not(.pro-library)'),pro=document.querySelector('.pro-library');
const create=document.getElementById('createProject'),fromMap=document.getElementById('createFromMap');
if(!free||!pro||!create||!fromMap)return;
const tabs=document.createElement('nav');tabs.className='qcm-project-tabs';tabs.setAttribute('aria-label','Type de projets');
const labels=[['pro','Pro · clients'],['free','Libres · personnels']];
const buttons=labels.map(([value,label])=>{
 const b=document.createElement('button');b.type='button';b.dataset.qcmFilter=value;b.textContent=label;
 b.setAttribute('aria-selected','false');tabs.append(b);return b;
});
free.before(tabs);
let selected='pro';
try{const stored=localStorage.getItem('localaiweb_qcm_project_tab');if(stored==='free'||stored==='pro')selected=stored}catch{}
function choose(value){
 if(!['free','pro'].includes(value))return;
 selected=value;document.body.dataset.qcmProjectFilter=value;
 buttons.forEach(b=>b.setAttribute('aria-selected',String(b.dataset.qcmFilter===value)));
 try{localStorage.setItem('localaiweb_qcm_project_tab',value)}catch{}
}
buttons.forEach(b=>b.addEventListener('click',()=>choose(b.dataset.qcmFilter)));
choose(selected);
function addCreationTile(id,label,handler){
 const grid=document.getElementById(id);if(!grid)return;
 const ensure=()=>{
   if(grid.querySelector('.qcm-create-tile'))return;
   const button=document.createElement('button');
   button.type='button';button.className='card qcm-create-tile';button.setAttribute('aria-label',label);
   button.innerHTML='<span aria-hidden="true" class="qcm-create-plus">＋</span><strong></strong><small></small>';
   button.querySelector('strong').textContent=label;
   button.querySelector('small').textContent=id==='projectsGrid'?'Créer depuis une idée':'Choisir un commerce réel';
   button.addEventListener('click',handler);
   grid.prepend(button);
 };
 new MutationObserver(ensure).observe(grid,{childList:true});
 ensure();
}
addCreationTile('projectsGrid','Nouveau projet libre',()=>create.click());
addCreationTile('proProjectsGrid','Projet professionnel depuis la carte',()=>fromMap.click());
})();