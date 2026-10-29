/* Real campaign workflow: models create footage, server composites authentic logo. */
(()=>{
 'use strict';
 const $=id=>document.getElementById(id);
 const dialog=$('studioAdDialog'),select=$('studioAdBrand');
 if(!dialog||!select)return;
 let brands=[],campaign=null,working=false;
 const headers={'Content-Type':'application/json','X-LocalAI-Brand':'1'};
 async function getBrands(){
   const response=await fetch('/api/studio/brands',{cache:'no-store'});
   const data=await response.json();
   if(!response.ok||data.error)throw Error(data.error||'Bibliothèque de marques indisponible.');
   brands=Array.isArray(data.brands)?data.brands:[];
   const selected=select.value||localStorage.getItem('localai_studio_brand_id')||'';
   select.replaceChildren(new Option('Choisir une marque…',''));
   for(const brand of brands)select.append(new Option(brand.name,brand.id));
   if(brands.some(brand=>brand.id===selected))select.value=selected;
 }
 async function request(path,body){
   const response=await fetch(path,{method:'POST',headers,body:JSON.stringify(body),
     credentials:'same-origin'});
   let data={};try{data=await response.json()}catch{}
   if(!response.ok||data.error)throw Error(data.error||'Impossible de créer l’export.');
   return data;
 }
 $('studioAdOpen').addEventListener('click',async()=>{
   $('studioAdError').textContent='';
   dialog.showModal();
   try{await getBrands()}catch(error){$('studioAdError').textContent=error.message}
   $('studioAdIdea').focus();
 });
 $('studioAdClose').addEventListener('click',()=>dialog.close());
 $('studioAdCancel').addEventListener('click',()=>dialog.close());
 dialog.addEventListener('close',()=>{$('studioAdError').textContent=''});
 $('studioAdForm').addEventListener('submit',event=>{
   event.preventDefault();
   const brand=brands.find(x=>x.id===select.value);
   if(!brand){$('studioAdError').textContent='Sélectionne d’abord une marque ou crée sa fiche.';return}
   const idea=$('studioAdIdea').value.trim();
   if(idea.length<6){$('studioAdError').textContent='Décris le visuel publicitaire souhaité.';return}
   if($('send')?.disabled){$('studioAdError').textContent='Une génération est déjà en cours. Termine-la avant de relancer.';return}
   const type=$('studioAdType').value,format=$('studioAdFormat').value;
   if(!['image','video'].includes(type)||!['square','portrait','landscape'].includes(format))return;
   campaign={brand,brand_id:brand.id,format,type,goal:$('studioAdGoal').value,idea};
   localStorage.setItem('localai_studio_brand_id',brand.id);
   const mode=$('taskMode');if(mode){mode.value=type;mode.dispatchEvent(new Event('change',{bubbles:true}))}
   const aspect=$('settingAspect');if(aspect)aspect.value={
     square:'1:1',portrait:'9:16',landscape:'16:9'}[format];
   const kind=type==='video'?'vidéo':'image';
   $('prompt').value='Crée une '+kind+' publicitaire professionnelle pour '+brand.name+
     '. Objectif : '+{
       product:'présenter un produit ou service',booking:'encourager les réservations',
       offer:'présenter une offre sans inventer de prix',presentation:'présenter l’entreprise'
     }[campaign.goal]+'. '+idea;
   dialog.close();
   // Trigger the existing, real generation flow with one explicit user click.
   $('send').click();
 });
 function enhancePrompt(raw,type){
   if(!campaign||campaign.type!==type)return raw;
   const b=campaign.brand;
   return [
     raw,
     'DIRECTION ARTISTIQUE PUBLICITAIRE : qualité commerciale élevée, composition précise,',
     'lumière étudiée, mouvements crédibles, textures réalistes, image nette,',
     'hiérarchie visuelle premium, cohérence entre les plans, finition professionnelle.',
     'Activité : '+(b.sector||'non renseignée')+'.',
     'Identité colorimétrique : '+(b.primary_color||'')+' et '+(b.secondary_color||'')+'.',
     'Public visé : '+(b.audience||'')+'.',
     'Positionnement : '+(b.description||'')+'.',
     'Respecte les faits fournis ; aucun prix, avis, résultat ou promotion inventé.',
     'Ne dessine pas de faux logo ni de texte promotionnel : le vrai logo et',
     'les textes sont ajoutés précisément au moment de l’export.'
   ].join(' ');
 }
 async function finishMedia(file,model,task,id,originalPrompt){
   if(!campaign||task!==campaign.type||!file?.filename||working)return;
   const selected={...campaign};
   // The model output remains visible immediately. Branded post-processing
   // runs separately, without hiding or rewriting the original creation.
   working=true;
   try{
     const result=await request('/api/studio/advert/render',{
       brand_id:selected.brand_id,format:selected.format,
       filename:file.filename,subfolder:file.subfolder||'',type:file.type||'output'
     });
     if(result.url&&window.StudioAds?.onAdvert)
       window.StudioAds.onAdvert(result,id,originalPrompt);
   }catch(error){
     if(window.StudioAds?.onError)window.StudioAds.onError(
       'La création originale est prête, mais l’export publicitaire a échoué : '+error.message,id);
   }finally{working=false}
 }
 window.StudioAds={enhancePrompt,finishMedia,getBrands,
   onAdvert:null,onError:null};
})();