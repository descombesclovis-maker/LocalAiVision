/* LocalAI Studio QCM V1 — shared, unobtrusive navigation.
 * Every control is a working route or an existing action. No fake progress.
 * NSFW interface intentionally excluded from all shell enhancements.
 */
(()=>{'use strict';
const $=s=>document.querySelector(s);
if(!document.body||document.body.dataset.studioShell==='off')return;
const page=document.body.dataset.studioPage||'home';
const isAdult=()=>document.body.classList.contains('nsfw-active');
// Prefer a native colour glyph. On systems without colour emoji use line art.
const iconPaths={
 '🗒️':'M5 3h14v18H5z M8 8h8 M8 12h8 M8 16h5',
 '🏠':'M3 11 12 3l9 8 M5 10v11h5v-7h4v7h5V10',
 '🌐':'M3 8h18v12H3z M8 8V5h8v3 M3 12q9 5 18 0',
 '🗺️':'M2 6l7-3 6 3 7-3v15l-7 3-6-3-7 3z M9 3v15m6-12v15',
 '👁️':'M2 12q10-15 20 0-10 15-20 0z M15 12a3 3 0 1 1-6 0 3 3 0 1 1 6 0',
 '📷':'M3 7h5l2-3h4l2 3h5v13H3z M16 13a4 4 0 1 1-8 0 4 4 0 1 1 8 0',
 '🎬':'M3 10h18v11H3z M3 6l17-4 1 4-17 4z M8 5l3 3m3-5 3 3',
 '📽️':'M12 2l3 7 8 1-6 5 2 8-7-4-7 4 2-8-6-5 8-1z',
 '🎨':'M12 3a9 9 0 1 0 0 18c4 0 0-4 3-5 8 0 8-13-3-13z M7 10h1m3-3h1m4 2h1'
};
const nativeEmoji=new Map();
function iconMarkup(glyph){
 if(!iconPaths[glyph])return glyph;
  if(page==='vision'&&!isAdult())return '<span class="qcm-emoji-vision" aria-hidden="true">'+glyph+'</span>';
 if(!nativeEmoji.has(glyph)){
   const canvas=document.createElement('canvas');canvas.width=canvas.height=40;
   const ctx=canvas.getContext('2d',{willReadFrequently:true});
   let colour=false;
   if(ctx){
     ctx.font='28px "Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif';
     ctx.fillText(glyph,2,30);
     const pixels=ctx.getImageData(0,0,40,40).data;
     for(let i=0;i<pixels.length;i+=4){
       if(pixels[i+3]>128&&Math.max(...pixels.subarray(i,i+3))-Math.min(...pixels.subarray(i,i+3))>24){colour=true;break}
     }
   }
   nativeEmoji.set(glyph,colour);
 }
 return nativeEmoji.get(glyph)?glyph:'<svg class="studio-icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24"><path d="'+iconPaths[glyph]+'"/></svg>';
}
window.studioIconMarkup=iconMarkup;
const links=[
 {id:'home',text:'Studio',symbol:'🏠',path:'/studio',keys:['accueil','studio']},
 {id:'web',text:'Web',symbol:'🌐',path:'/localaiweb',keys:['projets','web','site','creer']},
 {id:'map',text:'Carte',symbol:'🗺️',path:'/localaiweb/map',keys:['commerces','carte','maps','prospection']},
 {id:'vision',text:'Vision',symbol:'👁️',path:'/localaivision',keys:['image','photo','video','vision']},
 {id:'clients',text:'Livraison client',symbol:'🗒️',path:'/localaiweb/livraisons',keys:['livraison','paquet','devis','factures']},
];
// Commercial actions use an isolated origin. Navigation returns to the Studio
// origin without widening its API or generated-preview allowlist.
if(location.hostname==='ventes.localhost')for(const item of links)item.path=location.protocol+'//127.0.0.1:'+location.port+item.path;
const dock=document.createElement('nav');dock.className='qcm-dock';dock.setAttribute('aria-label','Navigation principale');dock.id='qcmDock';
dock.innerHTML=links.filter(x=>x.id!=='brands').map(x=>'<a class="qcm-dock-link" href="'+x.path+'" data-qcm-link="'+x.id+'" title="'+x.text+'"><span aria-hidden="true">'+iconMarkup(x.symbol)+'</span><small>'+x.text+'</small></a>').join('');
dock.querySelector('[data-qcm-link="'+(page==='delivery'?'clients':['editor','sales'].includes(page)?'web':page)+'"]')?.setAttribute('aria-current','page');
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
   const icon=document.createElement('b');icon.innerHTML=iconMarkup(item.symbol);
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
document.addEventListener('keydown',event=>{if(event.key==='Escape')for(const menu of document.querySelectorAll('details.studio-menu[open]')){menu.open=false;menu.querySelector('summary')?.focus()}});
document.addEventListener('pointerdown',event=>{for(const menu of document.querySelectorAll('details.studio-menu[open]'))if(!menu.contains(event.target))menu.open=false});
const hideForAdult=()=>{dock.hidden=isAdult();if(isAdult())close()};
hideForAdult();
if(page==='vision'){
 new MutationObserver(hideForAdult).observe(document.body,{attributes:true,attributeFilter:['class']});
}
})();

