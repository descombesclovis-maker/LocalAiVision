/* Brand assignment for LocalAiWeb. Customer-provided logo is copied to site assets. */
(()=>{
 'use strict';
 const select=document.getElementById('lawBrandPicker');
 if(!select)return;
 const projectId=new URLSearchParams(location.search).get('id');
 if(!/^web-[a-f0-9]{12}$/.test(projectId||''))return;
 let writing=false;
 async function request(url,body){
   const response=await fetch(url,body===undefined?{cache:'no-store'}:{
     method:'POST',headers:{'Content-Type':'application/json','X-LocalAI-Brand':'1'},
     body:JSON.stringify(body),credentials:'same-origin'});
   let data={};try{data=await response.json()}catch{}
   if(!response.ok||data.error)throw Error(data.error||'Erreur de connexion.');
   return data;
 }
 async function load(){
   try{
     const [all,projectResult]=await Promise.all([
       request('/api/studio/brands'),
       request('/api/web/project?id='+encodeURIComponent(projectId))
     ]);
     select.replaceChildren();
     const none=new Option('Aucune marque associée','');
     select.append(none);
     for(const brand of all.brands||[])select.append(new Option(brand.name,brand.id));
     select.value=projectResult.project?.brand_id||'';
     if(select.selectedIndex===-1)select.value='';
   }catch(error){
     select.replaceChildren(new Option('Marques indisponibles',''));
     select.disabled=true;
     console.warn('Marque du projet :',error.message);
   }
 }
 select.addEventListener('change',async()=>{
   if(writing)return;
   const previous=project?.project?.brand_id||'';
   if(busy){
     select.value=previous;
     document.getElementById('lawChatStatus').textContent='Termine la génération avant de changer de marque.';
     return;
   }
   const chosen=select.value;
   writing=true;select.disabled=true;
   try{
     const updated=await request('/api/web/project/brand',{id:projectId,brand_id:chosen});
     if(updated.project){
       project=updated;
       document.getElementById('lawChatStatus').textContent=
         chosen?'Identité de marque liée. Elle sera utilisée à la prochaine génération.':
                'Identité de marque retirée du projet.';
     }
   }catch(error){
     select.value=previous;
     document.getElementById('lawChatStatus').textContent=
       'Impossible de lier cette marque : '+error.message;
   }finally{writing=false;select.disabled=false}
 });
 void load();
})();