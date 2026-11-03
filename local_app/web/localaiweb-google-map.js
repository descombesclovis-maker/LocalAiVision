/* Official Maps + Places UI Kit. Never inspect or modify Google's shadow DOM.
   Only the selected place is requested; no harvesting or bulk lead database. */
window.LocalAiWebGoogleMap={
 async start(config,onSelection,setStatus,api){
  if(!config?.enabled||!config.browser_key)return false;
  await new Promise((resolve,reject)=>{
   if(window.google?.maps?.importLibrary){resolve();return}
   const callback='localAiWebGoogleMapsReady';
   let done=false;
   const finish=error=>{
    if(done)return;done=true;clearTimeout(timer);delete window[callback];
    error?reject(error):resolve();
   };
   const timer=setTimeout(()=>finish(Error('Chargement Google Maps trop long. Vérifiez la connexion et les API autorisées.')),16000);
   window[callback]=()=>finish();
   window.gm_authFailure=()=>finish(Error('Clé Google Maps refusée. Vérifiez ses restrictions et la facturation.'));
   const script=document.createElement('script');script.async=true;
   script.src='https://maps.googleapis.com/maps/api/js?'+new URLSearchParams({key:config.browser_key,loading:'async',callback,v:'weekly',language:'fr',region:'FR'});
   script.onerror=()=>finish(Error('Google Maps inaccessible. Vérifiez la connexion.'));
   document.head.append(script);
  });
  await google.maps.importLibrary('places');
  const panel=document.getElementById('mapSelection');
  const widget=document.getElementById('googlePlaceDetails');
  const request=widget.querySelector('gmp-place-details-place-request');
  if(!customElements.get('gmp-place-details'))throw Error('Le composant officiel Places UI Kit est indisponible pour cette configuration.');
  const map=new google.maps.Map(document.getElementById('businessMap'),{
   center:{lat:46.60,lng:2.28},zoom:6,clickableIcons:true,
   // Preserve native appearance, roads, cities, controls and attribution.
   styles:[{featureType:'poi',stylers:[{visibility:'off'}]},
    {featureType:'poi.business',stylers:[{visibility:'on'}]},
    {featureType:'transit.station',stylers:[{visibility:'off'}]}]
  });
  window.gm_authFailure=()=>{onSelection(null);setStatus('Clé Google Maps refusée. Vérifiez les restrictions, les API activées et la facturation.',true)};
  window.StudioMapRecenter=()=>{map.setCenter({lat:46.60,lng:2.28});map.setZoom(6)};
  window.dispatchEvent(new Event('studio-map-ready'));
  let revision=0;
  const close=()=>{++revision;panel.hidden=true;request.removeAttribute('place');onSelection(null)};
  document.getElementById('mapClose').addEventListener('click',close);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!panel.hidden)close()});
  widget.addEventListener('gmp-error',()=>{
   ++revision;onSelection(null);
   setStatus('La fiche Google est indisponible. Vérifiez Places UI Kit, ses autorisations et le quota Google.',true);
  });
  map.addListener('click',event=>{
   if(!event.placeId)return;
   // Google documents this suppression when displaying its official Places
   // widget, avoiding two competing native info views for the same selection.
   event.stop();
   const current=++revision,placeId=event.placeId;
   onSelection(null);panel.hidden=false;request.place=placeId;
   setStatus('Fiche Google sélectionnée. Préparation de l’action de création…');
   if(!config.places_enabled){
    setStatus('Fiche Google disponible. Configurez la clé serveur Places pour créer un projet depuis cette entreprise.',true);return;
   }
   void api('/api/web/map/google/place?'+new URLSearchParams({place_id:placeId})).then(data=>{
    if(current!==revision)return;
    if(!data.business?.selection_token||data.business.google_place_id!==placeId)throw Error('La sélection serveur ne correspond pas à la fiche Google.');
    onSelection(data.business);
    setStatus('Fiche officielle Google. L’action ci-dessous concerne uniquement cet établissement.');
   }).catch(error=>{
    if(current!==revision)return;
    onSelection(null);setStatus('Création indisponible : '+error.message,true);
   });
  });
  setStatus('Google Maps officiel · France. Zoomez puis sélectionnez une entreprise. La couverture dépend de Google.');
  return true;
 }
};
