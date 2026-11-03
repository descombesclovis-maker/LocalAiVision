/* Vision QCM V1 — real, search-first media library in public workspace only.
   The existing saved file records, delete buttons and image/video URLs remain source of truth.
   Never inspect, mirror or restyle the reserved adult library.
*/
(()=>{'use strict';
const container=document.getElementById('messages');if(!container)return;
const isAdult=()=>document.body.classList.contains('nsfw-active');
const viewer=document.createElement('dialog');viewer.className='qcm-library-dialog';
viewer.setAttribute('aria-label','Aperçu de la création sélectionnée');
viewer.innerHTML='<header><strong>Ma création</strong><button type="button" aria-label="Fermer l’aperçu">×</button></header><div class="qcm-library-dialog-stage"></div><footer><a id="qcmLibraryDownload" download>↓ Télécharger le fichier</a><button id="qcmLibraryClose" type="button">Fermer</button></footer>';
document.body.append(viewer);
const stage=viewer.querySelector('.qcm-library-dialog-stage');
const download=viewer.querySelector('#qcmLibraryDownload');
const close=()=>{viewer.close();stage.replaceChildren();download.removeAttribute('href')};
viewer.querySelector('header button').addEventListener('click',close);
viewer.querySelector('#qcmLibraryClose').addEventListener('click',close);
viewer.addEventListener('close',()=>{stage.replaceChildren();download.removeAttribute('href')});
const validSrc=source=>{
 try{const u=new URL(source,location.href);return u.origin===location.origin?u.href:null}catch{return null}
};
function activate(){
 if(isAdult()){if(viewer.open)close();return}
 const library=container.querySelector('.library-view'),grid=library?.querySelector('.library-grid');
 if(!library||!grid||library.dataset.qcmReady==='1')return;
 library.dataset.qcmReady='1';
 const tools=document.createElement('div');tools.className='qcm-library-tools';
 const label=document.createElement('label');label.className='qcm-library-search';label.textContent='Rechercher dans cette bibliothèque';
 const input=document.createElement('input');input.type='search';input.placeholder='Rechercher une création ou un prompt…';input.setAttribute('aria-label','Rechercher une création');
 label.append(input);
 const toggle=document.createElement('button');toggle.type='button';toggle.setAttribute('aria-pressed','false');toggle.textContent='☷ Liste';
 const result=document.createElement('span');result.className='qcm-library-count';result.setAttribute('aria-live','polite');
 tools.append(label,toggle,result);
 grid.before(tools);
 const cards=[...grid.querySelectorAll('.library-card')];
 const filter=()=>{const q=input.value.trim().toLocaleLowerCase('fr');let count=0;
   for(const card of cards){const text=card.querySelector('.meta')?.textContent||'';
     const matched=text.toLocaleLowerCase('fr').includes(q);card.hidden=!matched;if(matched)count++;
   }
   result.textContent=count+' / '+cards.length+' créations';
 };
 input.addEventListener('input',filter);filter();
 toggle.addEventListener('click',()=>{
   const list=grid.classList.toggle('qcm-library-list');
   toggle.textContent=list?'▦ Grille':'☷ Liste';
   toggle.setAttribute('aria-pressed',String(list));
 });
 for(const card of cards){
   const media=card.querySelector('img,video');if(!media)continue;
   const preview=document.createElement('button');preview.type='button';preview.className='qcm-library-preview';
   preview.textContent='↗ Voir en grand';preview.title='Ouvrir la véritable création';
   preview.addEventListener('click',()=>{
     if(isAdult())return;
     const href=validSrc(media.getAttribute('src')||'');if(!href)return;
     const node=document.createElement(media.tagName.toLowerCase()==='video'?'video':'img');
     node.src=href;node.className='qcm-library-fullmedia';
     if(node.tagName==='VIDEO'){node.controls=true;node.playsInline=true;node.preload='metadata'}else node.alt='Création sélectionnée';
     stage.replaceChildren(node);
     download.href=href;download.download='creation-localaivision';
     viewer.showModal();
   });
   card.append(preview);
 }
}
new MutationObserver(activate).observe(container,{subtree:true,childList:true});
new MutationObserver(()=>{if(isAdult()&&viewer.open)close()}).observe(document.body,{attributes:true,attributeFilter:['class']});
activate();
})();
