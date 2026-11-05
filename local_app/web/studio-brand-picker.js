/* Explicit brand choices. Global selection never rewrites a saved project. */
(()=>{'use strict';
const key='localai_studio_brand_id';
const selected=()=>{try{return localStorage.getItem(key)||''}catch{return ''}};
async function all(){const r=await fetch('/api/studio/brands',{cache:'no-store'});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||'Marques indisponibles');return d.brands||[]}
function activate(brand){try{localStorage.setItem(key,brand.id)}catch{}document.dispatchEvent(new CustomEvent('studio:brand-active',{detail:brand}))}
async function choose(current=''){
 const dialog=document.createElement('dialog');dialog.className='studio-brand-dialog';dialog.setAttribute('aria-label','Choisir une identité de marque');
 dialog.innerHTML='<header><h2>Renseigner ma marque</h2><button type="button" aria-label="Fermer">×</button></header><p>Cette sélection s’applique à ce projet. Vos autres projets conservent leur marque.</p><div class="studio-brand-options" aria-label="Marques enregistrées"></div><p class="studio-brand-status" role="status">Chargement des marques…</p>';
 document.body.append(dialog);dialog.showModal();
 return new Promise(resolve=>{
  let value=null;
  dialog.querySelector('header button').onclick=()=>dialog.close();
  dialog.addEventListener('close',()=>{dialog.remove();resolve(value)},{once:true});
  all().then(brands=>{
   if(!dialog.open)return;
   dialog.querySelector('.studio-brand-status').textContent=brands.length?'':'Aucune marque enregistrée. Créez votre marque depuis la carte Identités de marque de l’accueil Studio.';
   for(const brand of brands){
    const button=document.createElement('button');button.type='button';button.className='studio-brand-option';
    button.setAttribute('aria-label','Choisir '+brand.name+(brand.id===current?' · marque actuelle':''));
    if(brand.logo_url){const img=document.createElement('img');img.src=brand.logo_url;img.alt='';button.append(img)}
    const text=document.createElement('span');text.textContent=brand.name;
    const info=document.createElement('small');info.textContent=brand.sector||'Identité enregistrée';text.append(info);button.append(text);
    button.onclick=()=>{value=brand;dialog.close()};dialog.querySelector('.studio-brand-options').append(button);
   }
  }).catch(e=>{if(dialog.open)dialog.querySelector('.studio-brand-status').textContent=e.message});
 });
}
function label(button,brand){
 button.replaceChildren();
 if(brand?.logo_url){const img=document.createElement('img');img.src=brand.logo_url;img.alt='';button.append(img)}
 const text=document.createElement('span');text.className='studio-brand-label';text.textContent=brand?'Marque : '+brand.name:'Renseigner ma marque';button.append(text);
 button.title=brand?'Changer la marque du projet : '+brand.name:'Renseigner ma marque';
}
window.StudioBrandPicker={all,choose,activate,selected,label};
})();
