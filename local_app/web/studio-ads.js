/* Real campaign workflow: models create footage, server composites authentic logo. */
(()=>{
 'use strict';
 const $=id=>document.getElementById(id);
 const dialog=$('studioAdDialog'),select=$('studioAdBrand');
 if(!dialog||!select)return;
 let brands=[],campaign=null,exportQueue=Promise.resolve();
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
 function finishMedia(file,model,task,id,originalPrompt){
   if(!campaign||task!==campaign.type||!file?.filename)return Promise.resolve();
   const selected={...campaign};
   // Queue multiple images/videos without dropping results. Original outputs
   // appear immediately; only their derivative ads are rendered in sequence.
   exportQueue=exportQueue.catch(()=>{}).then(async()=>{
     try{
       const result=await request('/api/studio/advert/render',{
         brand_id:selected.brand_id,format:selected.format,
         filename:file.filename,subfolder:file.subfolder||'',type:file.type||'output'
       });
       if(result.url&&window.onStudioAdvert)
         window.onStudioAdvert(result,id,originalPrompt);
     }catch(error){
       if(window.onStudioAdvertError)window.onStudioAdvertError(
         'Création originale prête, export avec logo indisponible : '+error.message,id);
     }
   });
   return exportQueue;
 }
 window.StudioAds={enhancePrompt,finishMedia,getBrands};
 // Publication-first flow: arrive with the *actual* site context and brand,
 // not a blank ad tool. The operator still explicitly approves generation.
 const related=new URLSearchParams(window.location.search).get('campaign_project')||'';
 if(/^web-[a-f0-9]{12}$/.test(related)){
   queueMicrotask(async()=>{
     try{
       const reply=await fetch('/api/web/project?id='+encodeURIComponent(related),{cache:'no-store'});
       const data=await reply.json();
       if(!reply.ok||data.error)throw Error(data.error||'Site introuvable.');
       const project=data.project||{};
       if(!project.deployment?.production_url)throw Error('Publie d’abord ce site avant de créer sa campagne associée.');
       $('studioAdOpen').click();
       await getBrands();
       if(project.brand_id&&brands.some(brand=>brand.id===project.brand_id)){
         select.value=project.brand_id;
       }else{
         $('studioAdError').textContent='Pour une publicité fidèle, associe d’abord une identité de marque à ce projet depuis la bibliothèque de marques.';
       }
       $('studioAdIdea').value='Campagne pour le site '+(project.name||'de l’entreprise')+
         ' ('+project.deployment.production_url+'). Créer un visuel fidèle aux prestations réellement proposées sur le site, sans inventer de tarifs ni de témoignages.';
       $('studioAdIdea').focus();
     }catch(error){
       // Keep an actionable visible error, do not simulate a linked campaign.
       if(!dialog.open)$('studioAdOpen').click();
       $('studioAdError').textContent='Liaison avec le site indisponible : '+error.message;
     }
   });
 }
})();