/* France-first, no-search, no-filters OpenStreetMap business discovery.
   Green dot = no recorded website; red dot = website recorded. This is not a verified web audit.
   At country scale a single cached, distributed sample is displayed;
   detail loads progressively as the map is zoomed into a town. */
(()=>{
 const $=id=>document.getElementById(id);
 const info=$('mapFeedback'),panel=$('mapSelection'),btn=$('mapCreate');
 let map,selected=null,profileNonce=0,creating=false,loading=false;
 let previousArea='',lastLoad=0,pending=null,known=new Map(),markers=new Map();
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
   $('selectionNotice').textContent=recorded
     ?'Un site internet est renseigné dans OpenStreetMap. Le lien et son fonctionnement restent à vérifier.'
     :'Aucun site n’est renseigné dans OpenStreetMap : cela ne prouve pas que l’entreprise n’en possède pas.';
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
   registry.hidden=!(item.source||'').startsWith('OpenStreetMap');
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
     const color=business.website_recorded?'#e14959':'#27bd72';
     const marker=L.circleMarker([business.lat,business.lon],{
       radius:3.1,color,weight:0,stroke:false,
       fill:true,fillColor:color,fillOpacity:0.96,
     }).addTo(map);
     marker.bindTooltip(business.name,{direction:'top',opacity:0.96});
     marker.on('click',()=>details(business));
     markers.set(business.id,marker);
     added++;
   }
   return added;
 }
 async function overview(){
   if(loading)return;
   loading=true;
   setStatus('Chargement d’un aperçu partiel des entreprises en France…');
   try{
     const response=await api('/api/web/map/no-website/france');
     const added=insert(response.results);
     const red=[...known.values()].filter(p=>p.website_recorded).length;
     setStatus(known.size+' établissements affichés ('+red+' rouges avec site indiqué, '+
       (known.size-red)+' verts sans site renseigné). Aperçu partiel : zoome sur une ville.');
   }catch(err){
     setStatus('La carte reste utilisable. Données d’entreprises momentanément indisponibles : '+err.message);
   }finally{
     loading=false;lastLoad=Date.now();
   }
 }
 async function nearby(){
   if(!map||loading||map.getZoom()<10)return;
   const center=map.getCenter();
   const key=center.lat.toFixed(3)+'/'+center.lng.toFixed(3)+'/'+map.getZoom();
   if(key===previousArea)return;
   const remaining=29000-(Date.now()-lastLoad);
   if(remaining>0){
     setStatus('Points chargés progressivement. La prochaine zone pourra être consultée dans '+
       Math.ceil(remaining/1000)+' s.');
     return;
   }
   loading=true;previousArea=key;
   setStatus('Recherche d’établissements dans cette zone…');
   try{
     const query=new URLSearchParams({lat:String(center.lat),lon:String(center.lng),
                                    zoom:String(map.getZoom())});
     const response=await api('/api/web/map/no-website/nearby?'+query.toString());
     const count=insert(response.results);
     const red=[...known.values()].filter(p=>p.website_recorded).length;
     setStatus(count+' nouveaux établissements dans cette zone · '+red+' rouges, '+
       (known.size-red)+' verts au total. Présence de site à vérifier.');
   }catch(err){
     previousArea='';
     setStatus('Recherche temporairement indisponible : '+err.message);
   }finally{loading=false;lastLoad=Date.now();}
 }
 function scheduleNearby(){
   if(map.getZoom()<10){
     setStatus(known.size+' établissements affichés · aperçu partiel. Zoome sur une ville pour approfondir.');
     return;
   }
   window.clearTimeout(pending);
   pending=window.setTimeout(nearby,1300);
 }
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
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
   attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>',
   maxZoom:18,maxNativeZoom:18
 }).addTo(map);
 map.on('moveend',scheduleNearby);
 overview();
})();
