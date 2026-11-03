/* One official map, one official place card, one project creation action. */
(()=>{'use strict';
 const button=document.getElementById('mapCreate');
 const status=document.getElementById('mapStatus');
 const failure=document.getElementById('mapUnavailable');
 const errorBox=document.getElementById('mapCreateError');
 let selected=null,creating=false;
 function setStatus(text,error=false){status.textContent=text;status.dataset.error=String(error)}
 async function api(url,body){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),28000);
  try{
   const response=await fetch(url,{signal:controller.signal,cache:'no-store',...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
   let data={};try{data=await response.json()}catch{}
   if(!response.ok||data.error)throw Error(data.error||'Service indisponible (HTTP '+response.status+').');
   return data;
  }catch(error){if(error.name==='AbortError')throw Error('Délai dépassé. Réessayez la sélection.');throw error}
  finally{clearTimeout(timer)}
 }
 function select(item){
  selected=item;button.disabled=creating||!item?.selection_token;
  button.textContent='Créer un site pour cette entreprise';
  errorBox.textContent='';
  if(item)button.setAttribute('aria-label','Créer un site pour '+item.name);
  else button.setAttribute('aria-label','Créer un site pour cette entreprise — sélection en attente');
 }
 button.addEventListener('click',async()=>{
  if(creating||!selected?.selection_token)return;
  const token=selected.selection_token;creating=true;button.disabled=true;
  button.textContent='Création du projet…';errorBox.textContent='';
  try{
   const result=await api('/api/web/project/create-from-map',{selection_token:token});
   if(!/^web-[a-f0-9]{12}$/.test(result.project?.id||''))throw Error('Le serveur n’a pas confirmé la création du projet.');
   location.assign('/localaiweb/editor?id='+encodeURIComponent(result.project.id));
  }catch(error){errorBox.textContent='Création impossible : '+error.message}
  finally{creating=false;button.disabled=!selected?.selection_token;button.textContent='Créer un site pour cette entreprise'}
 });
 document.getElementById('mapRetry').addEventListener('click',()=>location.reload());
 async function start(){
  try{
   const config=await api('/api/web/map/config');
   if(!config.enabled||!config.browser_key)throw Error('Google Maps non configuré. Renseignez LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY dans les paramètres de votre installation. Aucune carte de remplacement n’est affichée.');
   const started=await window.LocalAiWebGoogleMap.start(config,select,setStatus,api);
   if(!started)throw Error('Configuration Google Maps incomplète.');
  }catch(error){
   failure.hidden=false;document.getElementById('mapFailureReason').textContent=error.message;
   setStatus('La carte Google Maps n’est pas disponible.',true);
  }
 }
 void start();
})();
