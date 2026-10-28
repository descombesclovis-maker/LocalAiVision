/* Google Maps Platform map mode. Uses the official JS Maps API and billable
   Places (New) requests ONLY if the user provided both API credentials.
   Not a scraper and not an unrestricted extraction of all Google businesses. */
window.LocalAiWebGoogleMap={
 async start(config, showCompany, setStatus, api) {
   if(!config?.enabled||!config.browser_key) return false;
   const load=()=>new Promise((resolve,reject)=>{
     if(window.google?.maps){resolve();return}
     const callback='localAiWebGoogleMapsReady';
     let finished=false;
     const finish=(err)=>{
       if(finished)return;finished=true;
       clearTimeout(timer);
       delete window[callback];
       err?reject(err):resolve();
     };
     const timer=setTimeout(()=>finish(Error('Google Maps inaccessible')),16000);
     window[callback]=()=>finish();
     const script=document.createElement('script');
     script.src='https://maps.googleapis.com/maps/api/js?'+
       new URLSearchParams({key:config.browser_key,loading:'async',callback,
         v:'weekly',language:'fr',region:'FR'});
     script.onerror=()=>finish(Error('Chargement Google Maps impossible'));
     document.head.appendChild(script);
   });
   await load();
   const map=new google.maps.Map(document.getElementById('businessMap'),{
     center:{lat:46.60,lng:2.28},zoom:6,
     minZoom:5,maxZoom:19,
     fullscreenControl:false,streetViewControl:false,mapTypeControl:false,
     clickableIcons:false,gestureHandling:'greedy',
     // Keep roads and city names but suppress Google POI pins,
     // allowing our own clickable business-only markers.
     styles:[
       {featureType:'poi',stylers:[{visibility:'off'}]},
       {featureType:'transit.station',stylers:[{visibility:'off'}]}
     ]
   });
   let selected=[],rendered=[],infoWindow=null,loading=false,lastKey='',lastAt=0,refreshTimer;
   const businesses=new Map();
   const markers=new Map();
   const GREEN='#35c774';
   const svg=(count=1)=>{
     const circle=count===1
       ?'<circle cx="16" cy="16" r="5" fill="'+GREEN+'" stroke="#fff" stroke-width="1.4"/>'
       :'<circle cx="16" cy="16" r="14" fill="'+GREEN+'" stroke="#fff" stroke-width="2"/>'+
        '<text x="16" y="20" font-size="11" font-family="Arial" font-weight="700" text-anchor="middle" fill="#123421">'+count+'</text>';
     return 'data:image/svg+xml;charset=UTF-8,'+
       encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'+circle+'</svg>');
   };
   const launch=(item)=>showCompany(item);
   async function selectItem(item){
     if(item.google_place_id){
       setStatus('Récupération de la fiche officielle de '+item.name+'…');
       try{
         const data=await api('/api/web/map/google/place?place_id='+
           encodeURIComponent(item.google_place_id));
         launch(data.business);
       }catch(e){
         setStatus('Détails Google indisponibles : '+e.message);
         launch(item);
       }
     }else launch(item);
   }
   function clear(){
     for(const marker of markers.values())marker.setMap(null);
     markers.clear();
   }
   function draw(){
     clear();
     const bounds=map.getBounds();
     if(!bounds)return;
     const zoom=map.getZoom()||6;
     const cell=zoom<8?44:zoom<12?36:27;
     const projection=map.getProjection();
     if(!projection)return;
     // Google Maps world coordinates * current pixels per world.
     const scale=256*Math.pow(2,zoom);
     const groups=new Map();
     for(const item of businesses.values()){
       const point={lat:item.lat,lng:item.lon};
       if(!bounds.contains(point))continue;
       const world=projection.fromLatLngToPoint(new google.maps.LatLng(point));
       const key=Math.floor(world.x*scale/cell)+':'+Math.floor(world.y*scale/cell);
       if(!groups.has(key))groups.set(key,[]);
       groups.get(key).push(item);
     }
     for(const [key,group] of groups){
       const item=group[0],count=group.length;
       const marker=new google.maps.Marker({
         map,position:{lat:item.lat,lng:item.lon},
         title:count>1?count+' entreprises à sélectionner':item.name,
         icon:{url:svg(count),scaledSize:new google.maps.Size(32,32),
           anchor:new google.maps.Point(16,16)},
         clickable:true,optimized:true,zIndex:count>1?5:1,
       });
       marker.addListener('click',()=>{
         if(count===1){void selectItem(item);return}
         const content=document.createElement('div');
         content.className='place-picker';
         const title=document.createElement('strong');
         title.textContent=count+' entreprises · choisis une fiche';
         content.append(title);
         const box=document.createElement('div');box.className='place-picker-list';
         for(const company of group.slice(0,35)){
           const button=document.createElement('button');
           button.type='button';button.className='place-picker-option';
           button.textContent=company.name;
           button.addEventListener('click',()=>{infoWindow?.close();void selectItem(company)});
           box.append(button);
         }
         content.append(box);
         if(infoWindow)infoWindow.close();
         infoWindow=new google.maps.InfoWindow({content,maxWidth:315,position:marker.getPosition()});
         infoWindow.open({map,anchor:marker});
       });
       markers.set(key,marker);
     }
     document.getElementById('loadedCount').textContent=businesses.size.toLocaleString('fr-FR');
   }
   function add(items){
     for(const item of items||[]){
       if(!item?.name||!item.id||!Number.isFinite(item.lat)||!Number.isFinite(item.lon))
         continue;
       if(businesses.size>=3200)break;
       businesses.set(item.id,item);
     }
     draw();
   }
   async function nationalOverview(){
     let count=0;
     for(let batch=0;batch<8;batch++){
       try{
         const data=await api('/api/web/map/no-website/france?batch='+batch);
         add(data.results);
         count+=data.results?.length||0;
         setStatus(count+' entreprises françaises chargées · zoome sur une ville pour Google Places.');
       }catch{
         if(count===0)setStatus('Google Maps disponible. Zoome sur une ville pour découvrir les commerces.');
         break;
       }
       await new Promise(resolve=>setTimeout(resolve,2100));
     }
   }
   async function localBusinesses(){
     const zoom=map.getZoom()||6,center=map.getCenter();
     if(zoom<9){
       setStatus('Carte Google Maps · rapproche une ville pour afficher ses commerces.');
       return;
     }
     const lat=center.lat(),lon=center.lng(),key=[
       lat.toFixed(3),lon.toFixed(3),zoom].join(':');
     if(key===lastKey||loading)return;
     if(Date.now()-lastAt<2500){
       clearTimeout(refreshTimer);
       refreshTimer=setTimeout(localBusinesses,2700);
       return;
     }
     lastKey=key;lastAt=Date.now();loading=true;
     let fetched=0,errors=[];
     try{
       // Three distinct local-shop categories, not just the most popular
       // twenty chains. Each official request can incur a Google Places charge.
       for(let segment=0;segment<3;segment++){
         if(segment)await new Promise(resolve=>setTimeout(resolve,850));
         try{
           const query=new URLSearchParams({
             lat:String(lat),lon:String(lon),zoom:String(zoom),segment:String(segment)});
           const data=await api('/api/web/map/google/local-shops?'+query);
           fetched+=data.results?.length||0;
           add(data.results);
         }catch(e){errors.push(e.message)}
       }
       setStatus(fetched+' commerces locaux trouvés via Google Places · '+
         businesses.size+' entreprises visibles dans cette session.'+
         (errors.length?' Requêtes limitées : '+errors[0]:''));
     }finally{loading=false}
   }
   map.addListener('idle',()=>{
     draw();
     clearTimeout(refreshTimer);
     refreshTimer=setTimeout(localBusinesses,750);
   });
   window.addEventListener('resize',()=>draw());
   document.getElementById('mapReload')?.addEventListener('click',()=>{
     lastKey='';lastAt=0;void localBusinesses();
   });
   setStatus('Carte Google Maps activée · données professionnelles chargées depuis Google Places.');
   void nationalOverview();
   return true;
 }
};
