/* LocalAI Studio QCM V1 — shared, unobtrusive navigation.
 * Every control is a working route or an existing action. No fake progress.
 * NSFW interface intentionally excluded from all shell enhancements.
 */
(()=>{'use strict';
const $=s=>document.querySelector(s);
if(!document.body||document.body.dataset.studioShell==='off')return;
const page=document.body.dataset.studioPage||'home';
const isAdult=()=>document.body.classList.contains('nsfw-active');
const links=[
 {id:'home',text:'Studio',symbol:'🏠',path:'/studio',keys:['accueil','studio']},
 {id:'web',text:'Projets',symbol:'💼',path:'/localaiweb',keys:['projets','web','site','creer']},
 {id:'map',text:'Carte',symbol:'🗺️',path:'/localaiweb/map',keys:['commerces','carte','maps','prospection']},
 {id:'vision',text:'Vision',symbol:'👁️',path:'/localaivision',keys:['image','photo','video','vision']},
 {id:'brands',text:'Marques',symbol:'◇',path:'/studio/brands',keys:['identite','marque','branding']},
];
const dock=document.createElement('nav');dock.className='qcm-dock';dock.setAttribute('aria-label','Navigation principale');dock.id='qcmDock';
dock.innerHTML=links.slice(0,4).map(x=>'<a class="qcm-dock-link" href="'+x.path+'" data-qcm-link="'+x.id+'" title="'+x.text+'"><span aria-hidden="true">'+x.symbol+'</span><small>'+x.text+'</small></a>').join('');
dock.querySelector('[data-qcm-link="'+page+'"]')?.setAttribute('aria-current','page');
document.body.append(dock);
const dialog=document.createElement('dialog');dialog.className='qcm-palette';dialog.setAttribute('aria-label','Palette de commandes');
dialog.innerHTML='<div class="qcm-command-box"><div class="qcm-command-header"><span aria-hidden="true">⌕</span><input type="search" id="qcmCommandSearch" placeholder="Ouvrir une page ou un outil…" autocomplete="off" aria-label="Rechercher une commande"><button type="button" id="qcmCloseCommands" aria-label="Fermer">×</button></div><div class="qcm-command-list" id="qcmCommandList"></div><p>↑ ↓ pour parcourir · Entrée pour ouvrir · Échap pour fermer</p></div>';
document.body.append(dialog);
const input=dialog.querySelector('#qcmCommandSearch'),list=dialog.querySelector('#qcmCommandList');
let active=0,visible=[];
const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function render(){
 const q=normalize(input.value);
 visible=links.filter(x=>normalize(x.text+' '+x.keys.join(' ')).includes(q));
 list.replaceChildren();
 for(const [index,item] of visible.entries()){
   const a=document.createElement('a');a.href=item.path;a.className='qcm-command-item'+(index===active?' active':'');
   const icon=document.createElement('b');icon.textContent=item.symbol;
   const text=document.createElement('span');text.textContent=item.text;
   const arrow=document.createElement('span');arrow.textContent='↗';arrow.setAttribute('aria-hidden','true');
   a.append(icon,text,arrow);a.addEventListener('mouseenter',()=>{active=index;highlight()});list.append(a);
 }
 if(!visible.length)list.textContent='Aucune commande correspondante.';
}
function highlight(){[...list.children].forEach((a,i)=>a.classList.toggle('active',i===active))}
function open(){if(isAdult())return;active=0;input.value='';render();dialog.showModal();input.focus()}
function close(){if(dialog.open)dialog.close()}

dialog.querySelector('#qcmCloseCommands').addEventListener('click',close);
input.addEventListener('input',()=>{active=0;render()});
input.addEventListener('keydown',e=>{
 if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();active=Math.max(0,Math.min(visible.length-1,active+(e.key==='ArrowDown'?1:-1)));highlight()}
 if(e.key==='Enter'&&visible[active]){e.preventDefault();location.assign(visible[active].path)}
});
document.addEventListener('keydown',e=>{
 if(isAdult())return;
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();dialog.open?close():open()}
},{passive:false});
const hideForAdult=()=>{dock.hidden=isAdult();if(isAdult())close()};
hideForAdult();
if(page==='vision'){
 new MutationObserver(hideForAdult).observe(document.body,{attributes:true,attributeFilter:['class']});
}
})();
