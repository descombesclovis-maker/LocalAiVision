/* Existing independent-directory suggestions, moved out of the Google map.
   Loaded only on demand. Never presented as native Google business cards. */
(()=>{'use strict';
 const open=document.getElementById('openProspects'),dialog=document.getElementById('prospectsDialog');
 if(!open||!dialog)return;
 const status=document.getElementById('prospectsStatus'),list=document.getElementById('prospectsList');
 const json=async(url,body)=>{
  const r=await fetch(url,{cache:'no-store',...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});
  const data=await r.json();if(!r.ok||data.error)throw Error(data.error||'Service indisponible');return data;
 };
 document.getElementById('closeProspects').addEventListener('click',()=>dialog.close());
 open.addEventListener('click',async()=>{
  open.closest('details.studio-menu').open=false;dialog.showModal();list.replaceChildren();status.textContent='Lecture des suggestions existantes…';
  try{
   const data=await json('/api/web/map/prospects/today');
   const rows=Array.isArray(data.results)?data.results:[];
   status.textContent=rows.length?'Suggestions issues de l’annuaire public indépendant. Coordonnées et présence d’un site à vérifier.':'Aucune suggestion disponible dans l’annuaire local. Vous pouvez choisir une entreprise directement sur la carte Google.';
   for(const item of rows.slice(0,5)){
    if(!item.id||!item.name)continue;
    const row=document.createElement('article');row.className='prospect-row';
    const heading=document.createElement('strong');heading.textContent=item.name;
    const info=document.createElement('p');info.textContent=[item.city||item.postcode,item.category,item.reason].filter(Boolean).join(' · ');
    const button=document.createElement('button');button.type='button';button.textContent='Créer le projet professionnel';
    button.addEventListener('click',async()=>{
     button.disabled=true;
     try{
      const fresh=await json('/api/web/map/selection/refresh?id='+encodeURIComponent(item.id));
      if(!fresh.business?.selection_token)throw Error('Sélection indisponible');
      const created=await json('/api/web/project/create-from-map',{selection_token:fresh.business.selection_token});
      if(!/^web-[a-f0-9]{12}$/.test(created.project?.id||''))throw Error('Projet non confirmé');
      location.assign('/localaiweb/editor?id='+encodeURIComponent(created.project.id));
     }catch(error){status.textContent='Création impossible : '+error.message;button.disabled=false}
    });
    row.append(heading,info,button);list.append(row);
   }
  }catch(error){status.textContent='Suggestions indisponibles : '+error.message}
 });
})();
