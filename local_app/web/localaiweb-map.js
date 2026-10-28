/* Search is intentionally only triggered by a deliberate user action.
   No autocomplete, map-move fetches or background bulk gathering. */
(() => {
 const $=id=>document.getElementById(id);
 const results=$('mapResults'),feedback=$('mapFeedback'),selectedCard=$('mapSelection');
 let map=null, selected=null, points=[], markers=[], creating=false, busy=false;
 let provider='osm',googleMap=null,googleMarkers=[],googleConfig=null;
 let categories=[],categorySearch='',selectionNonce=0;
 const industry=$('industryFilter'),industrySearch=$('industrySearch');
 function resetBusinessProfile(item){
   selectionNonce++;
   const details=[
      ['Activité',item.category],['Site web',item.website],
      ['Téléphone professionnel',item.phone],['Courriel professionnel',item.email],
      ['Horaires déclarés',item.opening_hours],['Description',item.description],
      ['Exploitant indiqué',item.operator]
   ].filter(pair=>pair[1]);
   const info=$('selectionPublicInfo');info.replaceChildren();
   for(const [name,value] of details){
     const row=createElement('p','business-fact');
     const label=createElement('strong','',name+' : ');
     row.append(label,document.createTextNode(String(value).slice(0,210)));
     info.append(row);
   }
   const profile=$('professionalProfile');profile.replaceChildren();
   const registryBtn=$('mapRegistry');
   registryBtn.hidden=!(item.source||'').startsWith('OpenStreetMap');
   registryBtn.disabled=false;
   if(item.official_registry?.matched)showRegistry(item.official_registry);
 }
 function showRegistry(registry){
   const area=$('professionalProfile');area.replaceChildren();
   const paragraph=createElement('p','',registry.matched
     ?'Registre public : '+registry.legal_name+' · SIREN '+registry.siren+
       (registry.naf?' · NAF '+registry.naf:'')
     : (registry.message||'Aucun renseignement légal confirmé.'));
   area.append(paragraph);
   if(registry.matched){
     for(const officer of registry.officers||[]){
       const title=createElement('p','',officer.name+' — '+officer.role);
       area.append(title);
     }
     const disclaimer=createElement('small','',
       'Dirigeants déclarés : pas nécessairement propriétaires. Données professionnelles à vérifier.');
     area.append(disclaimer);
     if(registry.source){
       const a=createElement('a','', 'Consulter la source officielle ↗');
       a.href=registry.source;a.target='_blank';a.rel='noopener noreferrer';area.append(a);
     }
   }
 }
 function filteredBusinesses(list, key){
   if(!key||key==='all'||provider==='google')return list;
   const category=categories.find(x=>x.id===key);
   if(!category)return list;
   return list.filter(item=>item.osm_category===category.value ||
     (item.category||'').toLowerCase()===category.name.toLowerCase());
 }
 function listCategories(query=''){
   const needle=query.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
   const selection=industry.value||'all';
   industry.replaceChildren();
   const matching=categories.filter(x=>!needle || x.id==='all' ||
     x.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(needle) ||
     x.group.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(needle));
   for(const item of matching){
     const opt=createElement('option','',item.name);
     opt.value=item.id;
     if(item.id===selection)opt.selected=true;
     industry.append(opt);
   }
   if(!matching.some(x=>x.id===selection))industry.value='all';
   if(matching.length)industry.disabled=false;
 }
 async function loadCategories(){
   try{
     const data=await api('/api/web/map/categories');
     categories=(data.groups||[]).flatMap(group=>(group.items||[]).map(x=>({...x,group:group.label})));
     $('industryTotal').textContent='('+data.count+' métiers)';
     listCategories();
   }catch(e){
     $('industryTotal').textContent='(catégories indisponibles)';
   }
 }
 industrySearch.addEventListener('input',()=>listCategories(industrySearch.value));
 industry.addEventListener('change',()=>{
   if(provider==='google'){
     feedback.textContent='Le filtre des métiers est disponible sur OpenStreetMap. La recherche Google conserve sa propre recherche.';
     return;
   }
   // Filter current results immediately without another network request.
   // A new zone fetch also applies the selected category on the server.
   if(points.length){
     const matches=filteredBusinesses(points,industry.value);
     for(const row of results.querySelectorAll('.result')){
       const entry=points[Number(row.dataset.index)];
       row.hidden=!matches.includes(entry);
     }
     feedback.textContent=matches.length+' établissement(s) correspondant au métier choisi dans les résultats actuels.';
   }
 });
 $('mapRegistry').addEventListener('click',async()=>{
   if(!selected?.selection_token)return;
   const token=selected.selection_token, nonce=selectionNonce;
   const btn=$('mapRegistry');btn.disabled=true;
   $('professionalProfile').textContent='Recherche des données professionnelles publiques…';
   try{
     const response=await api('/api/web/map/profile?selection_token='+encodeURIComponent(token));
     if(nonce!==selectionNonce)return;
     showRegistry(response.profile);
     if(response.profile?.matched)selected.official_registry=response.profile;
   }catch(err){
     if(nonce===selectionNonce)$('professionalProfile').textContent='Registre indisponible : '+err.message;
   }finally{btn.disabled=false;}
 });

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
   resetBusinessProfile(item);
   text('selectionTitle',item.name);
   text('selectionAddress',item.address||'Adresse à vérifier avec l’établissement');
   text('selectionCategory',(item.category||'Activité non précisée')+' · '+item.source);
   text('mapCreateError','');
   selectedCard.hidden=false;
   for(const el of results.querySelectorAll('.result'))el.classList.toggle('selected',Number(el.dataset.index)===index);
   if(provider==='google'&&googleMap)googleMap.panTo({lat:item.lat,lng:item.lon});
   else map.panTo([item.lat,item.lon]);
   selectedCard.scrollIntoView({behavior:'smooth',block:'nearest'});
 }
 function render(items){
   points=filteredBusinesses(items.filter(x=>Number.isFinite(x.lat)&&Number.isFinite(x.lon)&&x.name),industry.value);
   text('mapResultsCount',points.length ? points.length+' établissement(s) / lieu(x)' : '0');
   results.replaceChildren();
   selected=null;selectedCard.hidden=true;
   for(const marker of markers)marker.remove();
   markers=[];
   for(const marker of googleMarkers)marker.setMap(null);
   googleMarkers=[];
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
     if(provider==='google'&&googleMap){
       const marker=new google.maps.Marker({map:googleMap,position:{lat:item.lat,lng:item.lon},title:item.name});
       marker.addListener('click',()=>selection(item,index));
       googleMarkers.push(marker);
     }else{
       const marker=L.circleMarker([item.lat,item.lon],{
         radius:item.kind==='location'?7:9,color:item.kind==='location'?'#5975c3':'#8551b9',
         weight:2,fillColor:item.kind==='location'?'#d0d8fd':'#d5acff',fillOpacity:.9
       }).addTo(map);
       marker.on('click',()=>selection(item,index));
       marker.bindTooltip(item.name);
       markers.push(marker);
     }
     bounds.push([item.lat,item.lon]);
   });
   if(provider==='google'&&googleMap){
     if(bounds.length===1){googleMap.panTo({lat:bounds[0][0],lng:bounds[0][1]});googleMap.setZoom(16);}
     else if(bounds.length){
       const b=new google.maps.LatLngBounds();
       bounds.forEach(x=>b.extend({lat:x[0],lng:x[1]}));
       googleMap.fitBounds(b,60);
     }
   }else{
     if(bounds.length===1)map.flyTo(bounds[0],Math.max(map.getZoom(),14));
     else if(bounds.length)map.fitBounds(bounds,{padding:[36,36],maxZoom:15});
   }
   feedback.textContent=points.length+' résultat(s) trouvés. Sélectionne une entreprise dans la liste ou sur la carte.';
 }
 async function search(q){
   if(busy)return;
   button(true);try{
     const endpoint=provider==='google'?'/api/web/map/google/search':'/api/web/map/search';
     const response=await api(endpoint+'?q='+encodeURIComponent(q));
     render(response.results||[]);
   }catch(err){feedback.textContent='Recherche indisponible : '+err.message;}
   finally{button(false);if(!points.length && !feedback.textContent)feedback.textContent='Aucun établissement trouvé.';}
 }
 async function nearby(){
   if(busy||!map)return;
   if(provider==='google'){
     feedback.textContent='Sur Google Maps, clique directement sur le nom ou le repère d’une entreprise pour la sélectionner. Tu peux également utiliser la recherche ci-dessus.';
     return;
   }
   if(map.getZoom()<12){
     feedback.textContent='Zoome sur un quartier ou une ville avant de chercher les entreprises.';
     return;
   }
   button(true);
   try{
     const center=map.getCenter();
     const radius=Math.max(350,Math.min(2200,Math.round(42000/Math.pow(2,map.getZoom()-10))));
     const query=new URLSearchParams({
       lat:String(center.lat),lon:String(center.lng),radius:String(radius),
       industry:industry.value||'all'});
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
 map=L.map('businessMap',{zoomControl:true,worldCopyJump:true}).setView([20,4],2);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
    attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">contributeurs OpenStreetMap</a>',
    maxZoom:18,maxNativeZoom:18
 }).addTo(map);
 const picker=$('mapProvider');
 async function setupGoogle(){
   if(googleMap)return;
   if(!googleConfig?.enabled)throw Error('Configure les clés officielles Google Maps et Google Places sur le PC.');
   await new Promise((resolve,reject)=>{
     const callback='__localAiWebGoogleReady';
     window[callback]=()=>{
       try{
         const center=map.getCenter();
         googleMap=new google.maps.Map($('googleBusinessMap'),{
           center:{lat:center.lat,lng:center.lng},zoom:Math.max(6,map.getZoom()),
           clickableIcons:true,fullscreenControl:false,streetViewControl:false
         });
         googleMap.addListener('click',async event=>{
           if(!event.placeId)return;
           if(typeof event.stop==='function')event.stop();
           if(busy)return;
           button(true);
           try{
             const response=await api('/api/web/map/google/place?place_id='+encodeURIComponent(event.placeId));
             if(!response.business)throw Error("Aucune entreprise Google reconnue.");
             render([response.business]);
             selection(response.business,0);
           }catch(err){feedback.textContent='Impossible de sélectionner cette fiche : '+err.message;}
           finally{button(false);}
         });
         delete window[callback];resolve();
       }catch(err){reject(err);}
     };
     const script=document.createElement('script');
     script.async=true;
     script.onerror=()=>reject(Error('Chargement Google Maps indisponible.'));
     script.src='https://maps.googleapis.com/maps/api/js?loading=async&key='+encodeURIComponent(googleConfig.browser_key)+'&callback='+callback;
     document.head.appendChild(script);
   });
 }
 picker.addEventListener('change',async()=>{
   if(picker.value==='google'){
     button(true);
     try{await setupGoogle();provider='google';
       $('businessMap').hidden=true;$('googleBusinessMap').hidden=false;
       $('mapProviderInfo').textContent='Google Maps / Places : API officielle, facturation Google possible';
       feedback.textContent='Clique directement sur une entreprise de Google Maps, ou utilise la recherche.';
       render([]);
     }catch(err){picker.value='osm';feedback.textContent=err.message;}
     finally{button(false);}
   }else{
     provider='osm';$('googleBusinessMap').hidden=true;$('businessMap').hidden=false;
     $('mapProviderInfo').innerHTML='Données © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">contributeurs OpenStreetMap — licence ODbL</a>';
     map.invalidateSize();render([]);
     feedback.textContent='Carte gratuite : recherche une entreprise ou explore la zone.';
   }
 });
 loadCategories();
 api('/api/web/map/config').then(config=>{
   googleConfig=config;
   if(config.enabled){
     const option=picker.querySelector('option[value="google"]');
     option.disabled=false;option.textContent='Google Maps · API officielle';
   }
 }).catch(()=>{});
})();