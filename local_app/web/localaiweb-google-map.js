/* Google Maps Platform map mode. Uses the official JS Maps API as a map background; commercial
   records come only from independent French registry/OSM datasets.
   Never scrape, harvest or build prospecting dossiers from Google listings. */
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
   let infoWindow=null,loading=false,lastKey='',lastAt=0,refreshTimer;
   const businesses=new Map();
   const markers=new Map();
   this.focus=item=>{
     if(item&&Number.isFinite(item.lat)&&Number.isFinite(item.lon)){
       map.setCenter({lat:item.lat,lng:item.lon});
       map.setZoom(Math.max(map.getZoom()||6,11));
     }
   };
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
     // Prospection, CRM and Codex use only independently licensed
     // public French registry / OpenStreetMap records. Google supplies the
     // base map, not extracted commercial leads.
     launch(item);
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
       if(businesses.size>=30000)break;
       businesses.set(item.id,item);
     }
     draw();
   }
   async function nationalOverview(){
     let count=0;
     for(let batch=0;batch<20;batch++){
       try{
         const data=await api('/api/web/map/no-website/france?batch='+batch);
         add(data.results);
         count+=data.results?.length||0;
         setStatus(count+' commerces français réels chargés · déplace-toi pour explorer les villes.');
       }catch{
         if(count===0)setStatus('Google Maps disponible. Zoome sur une ville pour découvrir les commerces.');
         break;
       }
       if(data.next_batch===null||data.next_batch===undefined)break;
       await new Promise(resolve=>setTimeout(resolve,2600));
     }
   }
   async function localBusinesses(){
     const zoom=map.getZoom()||6,center=map.getCenter();
     if(zoom<8){
       setStatus('Carte Google Maps · zoome sur une ville pour afficher davantage de petits commerces publics.');
       return;
     }
     const lat=center.lat(),lon=center.lng(),key=[
       lat.toFixed(3),lon.toFixed(3),zoom].join(':');
     if(key===lastKey||loading)return;
     if(Date.now()-lastAt<2700){
       clearTimeout(refreshTimer);
       refreshTimer=setTimeout(localBusinesses,2800);
       return;
     }
     lastKey=key;lastAt=Date.now();loading=true;
     try{
       const args=new URLSearchParams({lat:String(lat),lon:String(lon),zoom:String(zoom)});
       // Three pages of real independently licensed French firms, with
       // priority for retail, small trades and local services.
       const data=await api('/api/web/map/registry/city?'+args);
       const before=businesses.size;
       add(data.results);
       setStatus((businesses.size-before)+' petits commerces et établissements ajoutés · '+
         businesses.size+' fiches professionnelles publiques, fond Google Maps.');
     }catch(error){
       lastKey='';
       setStatus('Entreprises publiques momentanément indisponibles : '+error.message);
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
   setStatus('Fond Google Maps activé · établissements publics français indépendants.');
   try{
     const existing=await api('/api/web/map/index?limit=12000');
     add(existing.results);
     setStatus((existing.count||0)+' entreprises déjà indexées sur ce PC.');
   }catch{}
   void nationalOverview();
   return true;
 }
};
