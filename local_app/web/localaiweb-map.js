/* Search is intentionally only triggered by a deliberate user action.
   No autocomplete, map-move fetches or background bulk gathering. */
(() => {
 const $=id=>document.getElementById(id);
 const results=$('mapResults'),feedback=$('mapFeedback'),selectedCard=$('mapSelection');
 let map=null, selected=null, points=[], markers=[], creating=false, busy=false;
 function text(id,value){$(id).textContent=String(value||'')}
 async function api(url,body){
   const options=body===undefined?{cache:'no-store'}:{
     method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
   const response=await fetch(url,options);
   let result={};try{result=await response.json()}catch{}
   if(!response.ok||result.error)throw Error(result.error||('Erreur HTTP '+response.status));
   return result;
 }
 function button(isBusy){
   busy=isBusy;$('mapSearchBtn').disabled=isBusy;$('mapNearby').disabled=isBusy;
   if(isBusy)feedback.textContent='Recherche des établissements…';
 }
 function createElement(tag,cls,label){
   const el=document.createElement(tag);if(cls)el.className=cls;
   if(label!==undefined)el.textContent=label;return el;
 }
 function selection(item,index){
   if(item.kind==='location'){
     map.flyTo([item.lat,item.lon],Math.max(map.getZoom(),14));
     selected=null;selectedCard.hidden=true;
     feedback.textContent='Carte centrée sur '+item.name+'. Clique sur « Afficher les établissements dans cette zone ».';
     return;
   }
   selected=item;
   text('selectionTitle',item.name);
   text('selectionAddress',item.address||'Adresse à vérifier avec l’établissement');
   text('selectionCategory',(item.category||'Activité non précisée')+' · '+item.source);
   text('mapCreateError','');
   selectedCard.hidden=false;
   for(const el of results.querySelectorAll('.result'))el.classList.toggle('selected',Number(el.dataset.index)===index);
   map.panTo([item.lat,item.lon]);
   selectedCard.scrollIntoView({behavior:'smooth',block:'nearest'});
 }
 function render(items){
   points=items.filter(x=>Number.isFinite(x.lat)&&Number.isFinite(x.lon)&&x.name);
   text('mapResultsCount',points.length ? points.length+' établissement(s) / lieu(x)' : '0');
   results.replaceChildren();
   selected=null;selectedCard.hidden=true;
   for(const marker of markers)marker.remove();
   markers=[];
   if(!points.length){
     feedback.textContent='Aucun résultat dans cette recherche. Essaye un nom plus précis ou déplace la carte.';
     return;
   }
   const bounds=[];
   points.forEach((item,index)=>{
     const btn=createElement('button','result');
     btn.type='button';btn.dataset.index=String(index);
     const name=createElement('strong','',item.name);
     const address=createElement('small','',item.address || 'Localisation cartographique');
     const pill=createElement('span','pill',
       item.kind==='location'?'📍 Ville ou lieu — centrer la carte':(item.category||'Établissement'));
     btn.append(name,address,pill);
     btn.addEventListener('click',()=>selection(item,index));
     results.append(btn);
     const marker=L.circleMarker([item.lat,item.lon],{
       radius:item.kind==='location'?7:9,color:item.kind==='location'?'#5975c3':'#8551b9',
       weight:2,fillColor:item.kind==='location'?'#d0d8fd':'#d5acff',fillOpacity:.9
     }).addTo(map);
     marker.on('click',()=>selection(item,index));
     marker.bindTooltip(item.name);
     markers.push(marker);
     bounds.push([item.lat,item.lon]);
   });
   if(bounds.length===1)map.flyTo(bounds[0],Math.max(map.getZoom(),14));
   else if(bounds.length)map.fitBounds(bounds,{padding:[36,36],maxZoom:15});
   feedback.textContent=points.length+' résultat(s) trouvés. Sélectionne une entreprise dans la liste ou sur la carte.';
 }
 async function search(q){
   if(busy)return;
   button(true);try{
     const response=await api('/api/web/map/search?q='+encodeURIComponent(q));
     render(response.results||[]);
   }catch(err){feedback.textContent='Recherche indisponible : '+err.message;}
   finally{button(false);if(!points.length && !feedback.textContent)feedback.textContent='Aucun établissement trouvé.';}
 }
 async function nearby(){
   if(busy||!map)return;
   if(map.getZoom()<12){
     feedback.textContent='Zoome sur un quartier ou une ville avant de chercher les entreprises.';
     return;
   }
   button(true);
   try{
     const center=map.getCenter();
     const radius=Math.max(350,Math.min(2200,Math.round(42000/Math.pow(2,map.getZoom()-10))));
     const query=new URLSearchParams({
       lat:String(center.lat),lon:String(center.lng),radius:String(radius)});
     const response=await api('/api/web/map/nearby?'+query.toString());
     render(response.results||[]);
   }catch(err){feedback.textContent='Recherche de proximité indisponible : '+err.message;}
   finally{button(false);}
 }
 $('mapSearchForm').addEventListener('submit',event=>{
   event.preventDefault();
   const q=$('mapQuery').value.trim();
   if(q.length<3){feedback.textContent='Saisis au moins trois caractères.';return;}
   search(q);
 });
 $('mapNearby').addEventListener('click',nearby);
 $('mapCreate').addEventListener('click',async()=>{
   if(!selected||!selected.selection_token||creating)return;
   creating=true;$('mapCreate').disabled=true;
   text('mapCreateError','');
   $('mapCreate').textContent='Création du projet Pro…';
   try{
     const response=await api('/api/web/project/create-from-map',{
       selection_token:selected.selection_token});
     const pid=response.project?.id;
     if(!/^web-[a-f0-9]{12}$/.test(pid||''))throw Error('Projet non enregistré.');
     window.location.assign('/localaiweb/editor?id='+encodeURIComponent(pid));
   }catch(err){text('mapCreateError',err.message);
     $('mapCreate').textContent='✦ Créer la première maquette ↗';}
   finally{creating=false;$('mapCreate').disabled=false;}
 });
 if(typeof L==='undefined'){
   $('mapUnavailable').hidden=false;
   feedback.textContent="La carte est indisponible sans connexion. Vérifie l'accès Internet.";
   return;
 }
 map=L.map('businessMap',{zoomControl:true}).setView([46.6,2.3],6);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
    attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">contributeurs OpenStreetMap</a>',
    maxZoom:18,maxNativeZoom:18
 }).addTo(map);
})();