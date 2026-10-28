/* France-first company directory with one uniform green pin style.
   Source records are real, partial and may not supply an official website.
   At low zoom, a click on a grouped pin opens an accessible company picker;
   no need to zoom to individual street level. */
(()=>{
 'use strict';
 const $=id=>document.getElementById(id);
 const info=$('mapFeedbackText'),reload=$('mapReload'),panel=$('mapSelection'),btn=$('mapCreate');
 let map,selected=null,creating=false,loading=false;
 let previousArea='',lastLoad=0,pending=null,overviewTimer=null,nextOverviewBatch=0;
 const businesses=new Map(),pins=new Map(),MAX_STORED=12500;
 const setStatus=message=>{info.textContent=message};
 const element=(tag,cls,value)=>{
   const item=document.createElement(tag);
   if(cls)item.className=cls;
   if(value!==undefined)item.textContent=String(value);
   return item;
 };
 async function api(url,body){
   const response=await fetch(url,body===undefined?{cache:'no-store'}:{
     method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
   let data={};try{data=await response.json()}catch{}
   if(!response.ok||data.error)throw Error(data.error||('Erreur HTTP '+response.status));
   return data;
 }
 function setValue(id,value){
   const target=$(id);
   target.replaceChildren();
   const clean=String(value||'').trim();
   target.textContent=clean||'Non renseigné';
   return target;
 }
 function appendSafeLink(node,raw,protocol,label){
   const source=String(raw||'').trim();
   if(!source)return false;
   try{
     const url=new URL(source);
     if(protocol==='https:'){
       if(!['https:','http:'].includes(url.protocol)||url.username||url.password)return false;
       if(!/\./.test(url.hostname)||url.hostname==='localhost')return false;
     }else if(url.protocol!==protocol)return false;
     const link=element('a','place-link',label||source);
     link.href=url.href;
     if(protocol==='https:'){link.target='_blank';link.rel='noopener noreferrer nofollow';link.referrerPolicy='no-referrer'}
     node.replaceChildren(link);
     return true;
   }catch{return false}
 }
 function details(item){
   selected=item;
   panel.hidden=false;
   $('selectionTitle').textContent=item.name||'Établissement';
   $('selectionCategory').textContent=item.category||'Entreprise';
   setValue('selectionAddress',item.address||[item.postcode,item.city].filter(Boolean).join(' '));
   setValue('selectionSiret',item.siret);
   const phone=setValue('selectionPhone',item.phone);
   if(item.phone&&/^[+()\d.\-\s]{5,30}$/.test(item.phone))
     appendSafeLink(phone,'tel:'+item.phone.replace(/[\s.()-]/g,''),'tel:',item.phone);
   const email=setValue('selectionEmail',item.email);
   if(item.email&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(item.email))
     appendSafeLink(email,'mailto:'+item.email,'mailto:',item.email);
   setValue('selectionHours',item.opening_hours||'Non renseignés');
   setValue('selectionActivity',item.category||item.osm_category);
   setValue('selectionDescription',item.description||item.operator);
   const website=$('selectionWebsite');website.replaceChildren();
   const webSource=String(item.website||'').trim();
   if(item.website_recorded||webSource){
     website.append(element('strong','web-fact','Oui, renseigné'));
     if(webSource){
       website.append(document.createTextNode(' · '));
       if(!appendSafeLinkInto(website,webSource))
         website.append(document.createTextNode('Lien non disponible'));
     }
   }else{
     website.append(element('strong','web-fact','Non renseigné'));
     website.append(document.createTextNode(' — absence non vérifiée'));
   }
   $('selectionNotice').textContent=
     'Données publiques : '+(item.source||'source non précisée')+
     '. Horaires, coordonnées et site internet peuvent être incomplets ou périmés.';
   $('mapCreateError').textContent='';
   btn.disabled=!item.selection_token;
   btn.textContent='Créer un site pour cette entreprise ↗';
 }
 function appendSafeLinkInto(parent,raw){
   try{
     const url=new URL(raw);
     if(!['https:','http:'].includes(url.protocol)||url.username||url.password||
        url.hostname==='localhost'||!url.hostname.includes('.'))return false;
     const link=element('a','place-link',url.hostname);
     link.href=url.href;link.target='_blank';link.rel='noopener noreferrer nofollow';
     link.referrerPolicy='no-referrer';parent.append(link);return true;
   }catch{return false}
 }
 function removePins(){
   for(const pin of pins.values())map.removeLayer(pin);
   pins.clear();
 }
 function groupedPopup(entries){
   const outer=element('section','place-picker');
   outer.append(element('strong','place-picker-title',
     entries.length+' entreprises à cet emplacement de la carte'));
   outer.append(element('p','place-picker-note','Choisis une entreprise sans zoomer davantage.'));
   const list=element('div','place-picker-list');
   for(const business of entries.slice(0,30)){
     const button=element('button','place-picker-option',business.name);
     button.type='button';
     button.append(element('small','',business.category||business.city||''));
     button.addEventListener('click',()=>{
       map.closePopup();details(business);
     });
     list.append(button);
   }
   outer.append(list);
   if(entries.length>30)outer.append(element('small','',
     'Affichage limité aux 30 premières entreprises : rapproche la carte pour voir les autres.'));
   return outer;
 }
 function markerFor(entry){
   const representative=entry[0];
   const count=entry.length;
   // 30px transparent hit region for every 6px visible dot.
   const html=count===1
     ?'<span class="company-marker-single" aria-hidden="true"></span>'
     :'<span class="company-marker-group" aria-hidden="true">'+count+'</span>';
   const icon=L.divIcon({html,className:'company-marker-hit',
     iconSize:[32,32],iconAnchor:[16,16]});
   const pin=L.marker([representative.lat,representative.lon],{icon,keyboard:true}).addTo(map);
   if(count===1){
     pin.bindTooltip(element('span','',representative.name),{direction:'top',opacity:.96});
     pin.on('click',()=>details(representative));
   }else{
     pin.bindTooltip(element('span','',count+' entreprises : cliquer pour choisir'),
       {direction:'top',opacity:.96});
     pin.on('click',()=>{
       const popup=L.popup({maxWidth:310,minWidth:220,autoPan:true,closeButton:true})
          .setLatLng(pin.getLatLng()).setContent(groupedPopup(entry));
       popup.openOn(map);
     });
   }
   return pin;
 }
 let rendering=false;
 function redraw(){
   if(!map||rendering)return;
   rendering=true;
   // Projection grid avoids stacking unclickable points at France-level zoom.
   const cell=map.getZoom()<=7?38:map.getZoom()<=10?33:25;
   const groups=new Map();
   const bounds=map.getBounds().pad(.12);
   for(const item of businesses.values()){
     if(!bounds.contains([item.lat,item.lon]))continue;
     const pt=map.latLngToContainerPoint([item.lat,item.lon]);
     const key=Math.floor(pt.x/cell)+':'+Math.floor(pt.y/cell);
     if(!groups.has(key))groups.set(key,[]);
     groups.get(key).push(item);
   }
   removePins();
   for(const [key,group] of groups){
     pins.set(key,markerFor(group));
   }
   $('loadedCount').textContent=businesses.size.toLocaleString('fr-FR');
   rendering=false;
 }
 let redrawTimeout;
 function scheduleRedraw(){
   clearTimeout(redrawTimeout);
   redrawTimeout=setTimeout(redraw,110);
 }
 function insert(records){
   let count=0;
   for(const item of records||[]){
     if(!item||item.kind==='location'||!item.id||
        !Number.isFinite(item.lat)||!Number.isFinite(item.lon))continue;
     if(businesses.has(item.id))continue;
     if(businesses.size>=MAX_STORED)break;
     businesses.set(item.id,item);count++;
   }
   if(count)scheduleRedraw();
   return count;
 }
 function compactOnMove(){
   if(businesses.size<9500)return;
   const bounds=map.getBounds().pad(2);
   for(const [id,item] of businesses){
     if(businesses.size<6500)break;
     if((!selected||id!==selected.id)&&!bounds.contains([item.lat,item.lon]))
       businesses.delete(id);
   }
 }
 function countLabel(){
   const n=businesses.size;
   return n+' entreprises réelles chargées · données publiques partielles (pas un registre national complet).';
 }
 async function overview(batch=0){
   clearTimeout(overviewTimer);
   if(loading){overviewTimer=setTimeout(()=>overview(batch),700);return}
   loading=true;reload.hidden=true;nextOverviewBatch=batch;
   setStatus('Chargement de la France · zone '+(batch+1)+' · '+countLabel());
   try{
     const response=await api('/api/web/map/no-website/france?batch='+encodeURIComponent(batch));
     insert(response.results);
     nextOverviewBatch=response.next_batch;
     setStatus(countLabel()+' · Zone '+(batch+1)+'/'+Math.max(1,response.total_batches||1));
     if(response.next_batch!==null&&response.next_batch!==undefined){
       // Respect the official directory's fair-use limits; datasets are cached.
       overviewTimer=setTimeout(()=>overview(response.next_batch),3600);
     }else if(businesses.size===0){
       reload.hidden=false;
       setStatus('Aucune entreprise disponible pour le moment. Réessaie avec une connexion Internet.');
     }
   }catch(err){
     reload.hidden=false;nextOverviewBatch=batch;
     setStatus('Annuaire des entreprises temporairement indisponible : '+
       err.message+'. Tu peux réessayer ou consulter les points déjà chargés.');
   }finally{
     loading=false;lastLoad=Date.now();
     if(map.getZoom()>=8)scheduleNearby();
   }
 }
 async function nearby(){
   if(!map||loading||map.getZoom()<8)return;
   const center=map.getCenter(),bounds=map.getBounds(),sw=bounds.getSouthWest(),ne=bounds.getNorthEast();
   const viewport=map.getZoom()>=13 && ne.lat-sw.lat<=.10&&ne.lng-sw.lng<=.10;
   const key=viewport?[sw.lat,sw.lng,ne.lat,ne.lng].map(v=>v.toFixed(4)).join('/')
     :[center.lat,center.lng,map.getZoom()].map(v=>v.toFixed(3)).join('/');
   if(key===previousArea)return;
   const remaining=2800-(Date.now()-lastLoad);
   if(remaining>0){clearTimeout(pending);pending=setTimeout(nearby,remaining+120);return}
   previousArea=key;loading=true;
   setStatus('Recherche d’établissements publics dans cette zone…');
   try{
     const query=viewport
       ?new URLSearchParams({south:String(sw.lat),west:String(sw.lng),
          north:String(ne.lat),east:String(ne.lng),zoom:String(map.getZoom())})
       :new URLSearchParams({lat:String(center.lat),lon:String(center.lng),zoom:String(map.getZoom())});
     const result=await api((viewport
       ?'/api/web/map/no-website/viewport':'/api/web/map/no-website/nearby')+'?'+query);
     compactOnMove();const count=insert(result.results);
     setStatus(count+' entreprises supplémentaires · '+countLabel());
   }catch(err){
     previousArea='';
     setStatus('Recherche locale indisponible : '+err.message+' · Les points déjà chargés restent accessibles.');
   }finally{loading=false;lastLoad=Date.now()}
 }
 function scheduleNearby(){
   scheduleRedraw();
   clearTimeout(pending);
   if(map.getZoom()>=8)pending=setTimeout(nearby,750);
 }
 reload.addEventListener('click',()=>{
   if(!loading)overview(Number.isInteger(nextOverviewBatch)?nextOverviewBatch:0)
 });
 $('mapClose').addEventListener('click',()=>{panel.hidden=true;selected=null});
 btn.addEventListener('click',async()=>{
   if(creating||!selected?.selection_token)return;
   creating=true;btn.disabled=true;
   $('mapCreateError').textContent='';
   btn.textContent='Recherche des informations et création du dossier…';
   try{
     // The server enriches ONLY publicly available professional facts on
     // user-initiated creation, never hidden/private demographic profiles.
     const response=await api('/api/web/project/create-from-map',{
       selection_token:selected.selection_token});
     const id=response.project?.id;
     if(!/^web-[a-f0-9]{12}$/.test(id||''))throw Error('Aucun projet créé.');
     location.assign('/localaiweb/editor?id='+encodeURIComponent(id));
   }catch(err){
     $('mapCreateError').textContent='Création impossible : '+err.message;
     btn.textContent='Créer un site pour cette entreprise ↗';
   }finally{creating=false;btn.disabled=false}
 });
 async function startMap(){
   try{
     const config=await api('/api/web/map/config');
     if(config.enabled && window.LocalAiWebGoogleMap){
       const started=await window.LocalAiWebGoogleMap.start(config,details,setStatus,api);
       if(started)return;
     }
     if(!config.enabled){
       // Never claim official Google Maps when the user has not configured
       // a Google Cloud billing account and two appropriate API keys.
       setStatus('Carte publique disponible. Pour la carte officielle Google Maps et ses commerces, configure Google Maps Platform.');
     }
   }catch(error){
     setStatus('Google Maps indisponible : '+error.message+'. Carte publique de secours chargée.');
   }
   startPublicMap();
 }
 function startPublicMap(){
 if(typeof L==='undefined'){
   $('mapUnavailable').hidden=false;
   setStatus('Impossible de charger la carte. Une connexion Internet est nécessaire.');
   return;
 }
 map=L.map('businessMap',{zoomControl:true,worldCopyJump:true,preferCanvas:true})
      .setView([46.60,2.28],6);
 const franceBounds=[[41.3,-5.8],[51.4,9.8]];
 const showFrance=()=>{
   map.invalidateSize({pan:false});
   map.fitBounds(franceBounds,{padding:[25,30],maxZoom:6,animate:false});
 };
 setTimeout(showFrance,300);
 window.addEventListener('resize',()=>{map.invalidateSize({pan:false});scheduleRedraw()});
 // Independent base-tile fallback, separate from the company directory.
 // If the standard OSM tile endpoint is unreachable, public CARTO tiles
 // can still show roads while official French directory pins load.
 const osm=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
   attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>',
   maxZoom:18,maxNativeZoom:18
 }).addTo(map);
 let fallbackUsed=false,tileFailures=0;
 osm.on('tileerror',()=>{
   tileFailures++;
   if(tileFailures<3||fallbackUsed)return;
   fallbackUsed=true;
   map.removeLayer(osm);
   L.tileLayer('https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',{
     maxZoom:18,maxNativeZoom:18,
     attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> · © CARTO'
   }).addTo(map);
   setStatus('Carte de fond alternative activée. '+countLabel());
 });
 map.on('moveend',scheduleNearby);
 map.on('zoomend',scheduleRedraw);
 overview();
 }
 void startMap();
})();