/* France-first, no-search, no-filters OpenStreetMap business discovery.
   Tiny violet dot = no website recorded in OSM, not a verified website audit.
   A distributed overview and bounded, rate-limited viewport requests prevent
   attempting to download every company in the world. */
(()=>{
 const $=id=>document.getElementById(id);
 const info=$('mapFeedbackText'),reload=$('mapReload'),panel=$('mapSelection'),btn=$('mapCreate');
 let map,selected=null,profileNonce=0,creating=false,loading=false;
 let previousArea='',lastLoad=0,pending=null,overviewTimer=null,nextOverviewBatch=0;
 let known=new Map(),markers=new Map();
 const setStatus=message=>info.textContent=message;
 function element(tag,cls,label){
   const item=document.createElement(tag);if(cls)item.className=cls;
   if(label!==undefined)item.textContent=label;return item;
 }
 async function api(url,body){
   const options=body===undefined?{cache:'no-store'}:
     {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
   const response=await fetch(url,options);
   let data={};try{data=await response.json()}catch{}
   if(!response.ok||data.error)throw Error(data.error||('Erreur HTTP '+response.status));
   return data;
 }
 function details(item){
   profileNonce++;
   selected=item;
   panel.hidden=false;
   $('selectionTitle').textContent=item.name;
   $('selectionCategory').textContent=item.category||'Établissement';
   $('selectionAddress').textContent=item.address||'Adresse non renseignée';
   $('mapCreateError').textContent='';
   const recorded=!!item.website_recorded;
   const registryUnknown=item.website_status==='inconnu_registre';
   $('selectionNotice').textContent=recorded
     ?'Un site est renseigné dans OpenStreetMap. Son fonctionnement reste à vérifier.'
     :registryUnknown
       ?'Donnée issue de l’annuaire officiel français. L’annuaire ne contient pas le statut du site Web : absence NON vérifiée.'
       :'Site non renseigné dans OpenStreetMap. Absence NON confirmée. Vérifie avant toute démarche.'; 
   const verify=$('verifyWebPresence');
   verify.hidden=true;verify.removeAttribute('href');
   // User-initiated search only: no scraping or automatic publication assertions.
   if(item.name){
     verify.href='https://www.google.com/search?'+new URLSearchParams({
       q:[item.name,item.city||item.address||'', 'site officiel'].filter(Boolean).join(' ')
     });
     verify.hidden=false;
   }
   const siteLink=$('companyWebsite');
   siteLink.hidden=true;siteLink.removeAttribute('href');
   if(recorded && item.website){
     try{
       const url=new URL(item.website);
       if(['https:','http:'].includes(url.protocol) && !url.username && !url.password){
         siteLink.href=url.href;
         siteLink.hidden=false;
         siteLink.textContent='↗ Consulter le site existant : '+url.hostname;
       }
     }catch{}
   }
   const facts=$('selectionPublicInfo');facts.replaceChildren();
   const rows=[
     ['Téléphone',item.phone],['Courriel professionnel',item.email],
     ['Horaires déclarés',item.opening_hours],['Description publique',item.description],
     ['Exploitant',item.operator]
   ];
   for(const [title,value] of rows){
     if(!value)continue;
     const line=element('p','');
     line.append(element('strong','',title+' : '),document.createTextNode(String(value).slice(0,230)));
     facts.append(line);
   }
   $('professionalProfile').replaceChildren();
   const registry=$('mapRegistry');
   registry.hidden=!((item.source||'').startsWith('OpenStreetMap') ||
                          (item.source||'').includes("data.gouv.fr"));
   registry.disabled=false;
   if(item.official_registry?.matched)showRegistry(item.official_registry);
 }
 function showRegistry(data){
   const box=$('professionalProfile');box.replaceChildren();
   if(!data?.matched){
     box.append(element('p','',data?.message||'Aucune correspondance certaine avec le registre.'));return;
   }
   box.append(element('p','',data.legal_name+' · SIREN '+data.siren+
     (data.naf?' · NAF '+data.naf:'')));
   for(const officer of data.officers||[])
     box.append(element('p','',officer.name+' — '+officer.role));
   box.append(element('small','',
     'Dirigeants déclarés : pas nécessairement propriétaires. Informations professionnelles à vérifier.'));
   if(data.source){
     const link=element('a','', 'Source officielle ↗');
     link.href=data.source;link.target='_blank';link.rel='noopener noreferrer';box.append(link);
   }
 }
 function insert(records){
   let added=0;
   for(const business of records||[]){
     if(!business||!business.id||!Number.isFinite(business.lat)||!Number.isFinite(business.lon))continue;
     if(business.kind==='location')continue;
     if(markers.has(business.id))continue;
     if(markers.size>=2600)break;
     known.set(business.id,business);
     const color=business.website_recorded?'#ef535e':'#36d77f';
     const marker=L.circleMarker([business.lat,business.lon],{
       radius:3.0,color,weight:0,stroke:false,
       fill:true,fillColor:color,fillOpacity:0.92,
     }).addTo(map);
     // OSM names are untrusted user-contributed text: never parse as HTML.
     marker.bindTooltip(element('span','',business.name),{direction:'top',opacity:0.96});
     marker.on('click',()=>details(business));
     markers.set(business.id,marker);
     added++;
   }
   return added;
 }
 function pruneOffscreen(){
   // Retain a generous cache while preventing a long prospecting session from
   // reaching a permanent marker cap (which would hide new destinations).
   if(markers.size<=1500)return;
   const area=map.getBounds().pad(0.8);
   for(const [id,marker] of markers){
     if(markers.size<=950)break;
     if(!area.contains(marker.getLatLng()) && (!selected || selected.id!==id)){
       map.removeLayer(marker);markers.delete(id);known.delete(id);
     }
   }
 }
 async function overview(batch=0){
   window.clearTimeout(overviewTimer);
   if(loading){
     overviewTimer=window.setTimeout(()=>overview(batch),1800);
     return;
   }
   loading=true;reload.hidden=true;nextOverviewBatch=batch;
   setStatus('Chargement des entreprises françaises · lot '+(batch+1)+' · '+known.size+' points déjà visibles…');
   try{
     const response=await api('/api/web/map/no-website/france?batch='+encodeURIComponent(batch));
     insert(response.results);
     const total=Math.max(1,Number(response.total_batches)||1);
     nextOverviewBatch=response.next_batch;
     if(known.size===0 && response.next_batch===null){
       setStatus('Aucun établissement reçu. La source de données ne couvre pas cette recherche. Réessaie ou zoome.');
       reload.hidden=false;
     }else{
       const red=[...known.values()].filter(x=>x.website_recorded).length;
       const source=response.fallback?'Annuaire français officiel': 'OpenStreetMap';
       setStatus(known.size+' entreprises chargées · '+(known.size-red)+' vertes / '+red+' rouges · lot '+(batch+1)+'/'+total+
         (response.offline?' · données locales en cache':' · source '+source)+'. Statut du site à vérifier.');
     }
     if(response.next_batch!==null && response.next_batch!==undefined){
       // The public OSM service is best-effort. Small batches avoid the
       // previous 90-city timeout and progressively fill the France view.
       const next=response.next_batch;
       overviewTimer=window.setTimeout(()=>overview(next),14500);
     }
   }catch(err){
     nextOverviewBatch=batch;
     reload.hidden=false;
     setStatus('Sources d’entreprises indisponibles (OSM et annuaire français) : '+
        err.message+' · Réessaie lorsque ta connexion sera rétablie.');
   }finally{
     loading=false;lastLoad=Date.now();
     if(map.getZoom()>=10)scheduleNearby();
   }
 }
 async function nearby(){
   if(!map||loading||map.getZoom()<10)return;
   const center=map.getCenter();
   const bounds=map.getBounds(),sw=bounds.getSouthWest(),ne=bounds.getNorthEast();
   const viewport=map.getZoom()>=13 && ne.lat-sw.lat<=0.10 && ne.lng-sw.lng<=0.10 &&
     sw.lng>=-180 && ne.lng<=180;
   const key=viewport
     ?[sw.lat,sw.lng,ne.lat,ne.lng].map(n=>n.toFixed(4)).join('/') 
     :center.lat.toFixed(3)+'/'+center.lng.toFixed(3)+'/'+map.getZoom();
   if(key===previousArea)return;
   const remaining=15000-(Date.now()-lastLoad);
   if(remaining>0){
     setStatus('Chargement progressif pour respecter OpenStreetMap · prochaine zone dans '+
       Math.ceil(remaining/1000)+' s.');
     window.clearTimeout(pending);
     pending=window.setTimeout(nearby,remaining+300);
     return;
   }
   loading=true;previousArea=key;
   setStatus('Recherche d’établissements dans cette zone…');
   try{
     const query=viewport
       ?new URLSearchParams({south:String(sw.lat),west:String(sw.lng),
          north:String(ne.lat),east:String(ne.lng),zoom:String(map.getZoom())})
       :new URLSearchParams({lat:String(center.lat),lon:String(center.lng),
          zoom:String(map.getZoom())});
     const endpoint=viewport?'/api/web/map/no-website/viewport':'/api/web/map/no-website/nearby';
     const response=await api(endpoint+'?'+query.toString());
     pruneOffscreen();
     const count=insert(response.results);
     const red=[...known.values()].filter(x=>x.website_recorded).length;
     setStatus(count+' nouveaux établissements · '+(known.size-red)+' verts / '+red+' rouges. '+
       (response.fallback?'Annuaire officiel français':'OpenStreetMap')+
       ' : données partielles, existence réelle du site non vérifiée.');
   }catch(err){
     previousArea='';
     setStatus('Recherche temporairement indisponible : '+err.message);
   }finally{loading=false;lastLoad=Date.now();}
 }
 function scheduleNearby(){
   pruneOffscreen();
   window.clearTimeout(pending);
   if(map.getZoom()<10){
     // An initial Leaflet moveend must not overwrite a loading error or hide
     // the empty-state diagnosis, as it did in the screenshot.
     return;
   }
   pending=window.setTimeout(nearby,1300);
 }
 reload.addEventListener('click',()=>{
   if(loading)return;
   reload.hidden=true;
   overview(Number.isInteger(nextOverviewBatch)?nextOverviewBatch:0);
 });
 $('mapClose').addEventListener('click',()=>{panel.hidden=true;selected=null;profileNonce++});
 $('mapRegistry').addEventListener('click',async()=>{
   if(!selected?.selection_token)return;
   const token=selected.selection_token,nonce=profileNonce;
   const button=$('mapRegistry');button.disabled=true;
   $('professionalProfile').textContent='Vérification des informations professionnelles publiques…';
   try{
     const result=await api('/api/web/map/profile?selection_token='+encodeURIComponent(token));
     if(nonce===profileNonce){
       showRegistry(result.profile);
       if(result.profile?.matched)selected.official_registry=result.profile;
     }
   }catch(err){
     if(nonce===profileNonce)$('professionalProfile').textContent='Registre indisponible : '+err.message;
   }finally{button.disabled=false;}
 });
 btn.addEventListener('click',async()=>{
   if(creating||!selected?.selection_token)return;
   creating=true;btn.disabled=true;
   $('mapCreateError').textContent='';btn.textContent='Création du projet Pro…';
   try{
     const response=await api('/api/web/project/create-from-map',{
       selection_token:selected.selection_token});
     const projectId=response.project?.id;
     if(!/^web-[a-f0-9]{12}$/.test(projectId||''))throw Error('Projet non créé.');
     window.location.assign('/localaiweb/editor?id='+encodeURIComponent(projectId));
   }catch(err){
     $('mapCreateError').textContent='Création impossible : '+err.message;
     btn.textContent='✦ Générer une première maquette ↗';
   }finally{creating=false;btn.disabled=false;}
 });
 if(typeof L==='undefined'){
   $('mapUnavailable').hidden=false;
   setStatus('La carte nécessite Internet pour charger les données OpenStreetMap.');
   return;
 }
 map=L.map('businessMap',{zoomControl:true,worldCopyJump:true,preferCanvas:true})
      .setView([46.60,2.28],6);
 // WebView2 can measure the map before its native window has its final size.
 // Recalculate the viewport after layout, then center on ALL of France.
 const franceBounds=[[41.3,-5.8],[51.4,9.8]];
 const showFrance=()=>{
   map.invalidateSize({pan:false});
   map.fitBounds(franceBounds,{padding:[25,30],maxZoom:6,animate:false});
 };
 window.setTimeout(showFrance,300);
 window.addEventListener('resize',()=>map.invalidateSize({pan:false}));
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
   attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>',
   maxZoom:18,maxNativeZoom:18
 }).addTo(map);
 map.on('moveend',scheduleNearby);
 overview();
})();
