/* Public outputs: real browser decoding, never aesthetic/GPU certification. */
(()=>{'use strict';
function verify(source,kind,{timeoutMs=45000}={}){
 return new Promise((resolve,reject)=>{
  let url;
  try{url=new URL(source,location.href);if(url.origin!==location.origin||!/^https?:$/.test(url.protocol))throw Error('origin')}
  catch{reject(Error('Adresse de résultat invalide.'));return}
  const video=kind==='video',node=document.createElement(video?'video':'img');
  let settled=false;
  const cleanup=()=>{
   clearTimeout(timer);node.removeEventListener(video?'loadeddata':'load',loaded);node.removeEventListener('error',failed);
   if(video)node.pause();node.removeAttribute('src');if(video)node.load();node.remove();
  };
  const finish=(error,receipt)=>{if(settled)return;settled=true;cleanup();if(error)reject(error);else resolve(receipt)};
  const failed=()=>finish(Error('Le fichier est absent, illisible ou son format n’est pas décodable par ce navigateur.'));
  const loaded=async()=>{
   try{
    if(!video&&typeof node.decode==='function')await node.decode();
    const width=video?node.videoWidth:node.naturalWidth,height=video?node.videoHeight:node.naturalHeight;
    if(!(width>0&&height>0))throw Error('Dimensions invalides.');
    if(video&&(!(node.readyState>=2)||!Number.isFinite(node.duration)||node.duration<=0))throw Error('Première image ou durée vidéo indisponible.');
    finish(null,{verified:true,kind,width,height,duration_seconds:video?node.duration:null,
      scope:video?'browser_first_frame_and_metadata':'browser_image_decode',full_video_decode:false,
      visual_quality:'not_reviewed',checked_at:new Date().toISOString()});
   }catch{failed()}
  };
  const timer=setTimeout(()=>finish(Error('Vérification du fichier trop longue. Le rendu est conservé ; tu peux revérifier sans le régénérer.')),Math.max(1,Math.min(120000,Number(timeoutMs)||45000)));
  node.addEventListener(video?'loadeddata':'load',loaded);node.addEventListener('error',failed);
  if(video){node.muted=true;node.playsInline=true;node.preload='auto'}
  url.searchParams.set('validation',String(Date.now()));
  node.src=url.href;if(video)node.load();
 });
}
window.StudioMediaValidation={verify};
})();
