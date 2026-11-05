/* Build 315.3 — brief advertisements in the existing Vision conversation.
 * No popup, no automatically invented claims; successful media remains the
 * real ComfyUI output. Registered brands keep the original logo compositor.
 */
(()=>{'use strict';
 const $=id=>document.getElementById(id);
 const headers={'Content-Type':'application/json','X-LocalAI-Brand':'1'};
 let brands=[],draft=null,campaign=null,exportQueue=Promise.resolve();
 const brandButton=document.createElement('button');brandButton.id='visionBrandButton';brandButton.type='button';brandButton.className='studio-brand-button';brandButton.textContent='Renseigner ma marque';
 $('composerImageBtn')?.after(brandButton);
 brandButton.addEventListener('click',async()=>{
   const brand=await window.StudioBrandPicker.choose(draft?.brand?.id||'');
   if(!brand)return;
   if(!draft)startChat({brand,reuseConversation:true});
   else{draft.brand=brand;draft.brandName=brand.name;if(draft.step==='brand')draft.step='type'}
   if(activeConversationId){const c=conversationFor(activeConversationId);c.brand_id=brand.id;c.brand_snapshot={...brand};save()}
   window.StudioBrandPicker.label(brandButton,brand);
   reply('Marque **'+brand.name+'** associée à cette publicité. '+(draft.step==='type'?'Souhaites-tu une photo ou une vidéo ?':'Le brief en cours est conservé.'));
 });
 const reply=text=>{
   if(!activeConversationId)createBlankConversation('auto');
   addMessage(activeConversationId,{role:'assistant',text});
 };
 async function getBrands(){
   const response=await fetch('/api/studio/brands',{cache:'no-store'});
   const data=await response.json();
   if(!response.ok||data.error)throw Error(data.error||'Bibliothèque de marques indisponible.');
   brands=Array.isArray(data.brands)?data.brands:[];
   return brands;
 }
 function startChat(prefill={}){
   // Use the same clean onboarding surface as Photo and Video. No assistant
   // bubble is inserted before the first user message and no modal appears.
   if(!prefill.reuseConversation){
     if(window.LocalAiVisionSelectMode)window.LocalAiVisionSelectMode('advert',{
       message:prefill.brand
         ?'Publicité pour '+prefill.brand.name+'. Souhaites-tu créer une photo ou une vidéo publicitaire ?'
         :undefined
     });
     else createBlankConversation('auto');
   }else window.LocalAiVisionSelectMode?.('advert',{preserveConversation:true});
   const task=$('taskMode');if(task){task.value='auto';task.dispatchEvent(new Event('change',{bubbles:true}))}
   document.body.classList.add('vision-ad-guided');
   $('prompt').placeholder='Décris ta publicité…';
   $('prompt').value='';
   draft={step:'brand',brand:null,brandName:'',type:'image',format:'portrait',goal:'presentation',idea:'',projectContext:prefill.projectContext||''};
   if(prefill.brand){draft.brand=prefill.brand;draft.brandName=prefill.brand.name;draft.step='type'}
   const conv=activeConversationId?conversationFor(activeConversationId):null;
   const saved=conv?.brand_snapshot;
   if(!prefill.brand&&saved?.id){draft.brand=saved;draft.brandName=saved.name;draft.step='type'}
   if(prefill.brand&&conv){conv.brand_id=prefill.brand.id;conv.brand_snapshot={...prefill.brand};save()}
   window.StudioBrandPicker?.label(brandButton,draft.brand);
   // Stored brands will be available for name/number matching once loaded.
   // Failure does not block a free-form advertisement brief.
   void getBrands().catch(()=>{brands=[]});
   $('prompt').focus();
 }
 const matchBrand=value=>{
   const input=value.trim();
   const n=Number(input);
   if(Number.isInteger(n)&&n>=1&&n<=brands.length)return brands[n-1];
   return brands.find(b=>b.name?.trim().toLocaleLowerCase('fr')===input.toLocaleLowerCase('fr'))||null;
 };
 function handleDraftMessage(value){
   if(!draft||document.body.classList.contains('nsfw-active'))return false;
   const text=String(value||'').trim();if(!text)return true;
   if(!activeConversationId)createBlankConversation('auto');
   addMessage(activeConversationId,{role:'user',text});
   $('prompt').value='';$('prompt').style.height='';
   const normalized=text.toLocaleLowerCase('fr');
   if(/^(annuler|stop|quitter)$/i.test(normalized)){
     draft=null;document.body.classList.remove('vision-ad-guided');$('prompt').placeholder='Écris ton message…';
     reply('Préparation de publicité annulée. Aucune génération ni publication n’a été lancée.');return true;
   }
   switch(draft.step){
     case 'brand': {
       draft.brand=matchBrand(text);draft.brandName=draft.brand?.name||text.slice(0,90);
       draft.step='type';
       reply('Très bien : **'+draft.brandName+'**.'+(draft.brand?' Le logo enregistré pourra être ajouté après génération.':' Cette marque n’est pas associée à un logo enregistré.')+' Souhaites-tu une **photo** ou une **vidéo** publicitaire ?');
       break;
     }
     case 'type': {
       if(/\b(vid[ée]o|film|reel|clip|animation)\b/i.test(text))draft.type='video';
       else if(/\b(photo|image|visuel|affiche|banni[èe]re)\b/i.test(text))draft.type='image';
       else{reply('Précise simplement **photo** ou **vidéo**.');break}
       draft.step='format';
       reply('Quel **format** veux-tu : **vertical (9:16)**, **carré (1:1)** ou **horizontal (16:9)** ?');
       break;
     }
     case 'format': {
       if(/vertical|portrait|9:16|story|reel|tiktok/i.test(text))draft.format='portrait';
       else if(/carr[ée]|1:1|square/i.test(text))draft.format='square';
       else if(/horizontal|paysage|16:9|youtube/i.test(text))draft.format='landscape';
       else{reply('Choisis **vertical**, **carré** ou **horizontal**.');break}
       draft.step='goal';
       reply('Quel est l’**objectif** : **présenter la marque**, **mettre en valeur un produit**, **encourager les réservations** ou **présenter une offre** ?');
       break;
     }
     case 'goal': {
       if(/produit|service/i.test(text))draft.goal='product';
       else if(/r[ée]serv|rendez.vous/i.test(text))draft.goal='booking';
       else if(/offre|promo/i.test(text))draft.goal='offer';
       else if(/pr[ée]sent|entreprise|marque/i.test(text))draft.goal='presentation';
       else{reply('Précise **marque**, **produit**, **réservations** ou **offre**.');break}
       draft.step='idea';
       reply('**Décris ta publicité** : ambiance, sujet, lumière, décor, message à faire passer et éléments indispensables. Les informations commerciales doivent être exactes.');
       break;
     }
     case 'idea': {
       if(text.length<8){reply('Ajoute quelques détails pour que la publicité corresponde bien à ton idée.');break}
       draft.idea=text;draft.step='confirm';
       reply('Récapitulatif : **'+draft.brandName+'** · **'+(draft.type==='video'?'vidéo':'photo')+'** · **'+({portrait:'9:16',square:'1:1',landscape:'16:9'}[draft.format])+'**.\n\n'+draft.idea+'\n\nÉcris **générer** pour lancer la création, ou **annuler**.');
       break;
     }
     case 'confirm': {
       if(!/^(g[ée]n[ée]rer|lancer|oui|valider|cr[ée]er)$/i.test(text)){
         reply('Écris **générer** pour confirmer, ou **annuler**.');break;
       }
       const ready=draft;draft=null;document.body.classList.remove('vision-ad-guided');
       campaign={brand:ready.brand,brand_id:ready.brand?.id||null,type:ready.type,format:ready.format,goal:ready.goal,idea:ready.idea};
       if(ready.brand){const c=conversationFor(activeConversationId);c.brand_id=ready.brand.id;c.brand_snapshot={...ready.brand};save()}
       const mode=$('taskMode');if(mode){mode.value=ready.type;mode.dispatchEvent(new Event('change',{bubbles:true}))}
       const aspect=$('settingAspect');if(aspect)aspect.value={portrait:'9:16',landscape:'16:9',square:'1:1'}[ready.format];
       const goal={product:'présenter un produit/service',booking:'encourager les réservations',offer:'présenter une offre sans inventer de prix',presentation:'présenter l’entreprise'}[ready.goal];
       const creative='Crée une '+(ready.type==='video'?'vidéo':'image')+' publicitaire professionnelle pour '+ready.brandName+'. Objectif : '+goal+'. '+ready.idea+'. '+ready.projectContext+' Respecte uniquement les informations vérifiables, sans inventer prix, avis ni promotions.';
       $('prompt').placeholder='Décris ta publicité…';$('prompt').value=creative;
       reply('Brief confirmé. La génération va utiliser les moteurs photo/vidéo existants.');
       // The confirmation is an explicit user action. Let the original media
       // handler submit the prepared prompt, with no modal or duplicate submit.
       queueMicrotask(()=>$('send')?.click());
       break;
     }
   }
   return true;
 }
 async function request(path,body){
   const response=await fetch(path,{method:'POST',headers,body:JSON.stringify(body),credentials:'same-origin'});
   let data={};try{data=await response.json()}catch{}
   if(!response.ok||data.error)throw Error(data.error||'Impossible de créer l’export.');
   return data;
 }
 function enhancePrompt(raw,type){
   if(!campaign||campaign.type!==type)return raw;
   const b=campaign.brand||{};
   return [raw,'DIRECTION ARTISTIQUE PUBLICITAIRE : qualité commerciale élevée, composition précise, lumière étudiée, mouvements crédibles, textures réalistes, image nette, hiérarchie visuelle premium, cohérence entre les plans.','Activité : '+(b.sector||'non renseignée')+'.','Identité colorimétrique : '+(b.primary_color||'')+' et '+(b.secondary_color||'')+'.','Public visé : '+(b.audience||'')+'.','Positionnement : '+(b.description||'')+'.','Respecte les faits fournis ; aucun prix, avis, résultat ou promotion inventé. Ne dessine pas de faux logo ni de texte promotionnel : le vrai logo et les textes seront ajoutés précisément au moment de l’export.'].join(' ');
 }
 function finishMedia(file,model,task,id,originalPrompt){
   if(!campaign?.brand_id||task!==campaign.type||!file?.filename)return Promise.resolve();
   const selected={...campaign};
   exportQueue=exportQueue.catch(()=>{}).then(async()=>{
     try{
       const result=await request('/api/studio/advert/render',{
         brand_id:selected.brand_id,format:selected.format,
         filename:file.filename,subfolder:file.subfolder||'',type:file.type||'output'});
       if(result.url&&window.onStudioAdvert)window.onStudioAdvert(result,id,originalPrompt);
     }catch(error){
       if(window.onStudioAdvertError)window.onStudioAdvertError('Création originale prête, export avec logo indisponible : '+error.message,id);
     }
   });
   return exportQueue;
 }
 function activeAspect(task){return campaign?.type===task?{square:'1:1',portrait:'9:16',landscape:'16:9'}[campaign.format]:null}
 function endGeneration(task){if(campaign?.type===task)campaign=null}
 function cancelChat(){draft=null;document.body.classList.remove('vision-ad-guided')}
 window.StudioAds={enhancePrompt,finishMedia,getBrands,activeAspect,endGeneration,handleDraftMessage,startChat,cancelChat};
 $('studioAdOpen')?.addEventListener('click',()=>startChat());
 const related=new URLSearchParams(location.search).get('campaign_project')||'';
 if(/^web-[a-f0-9]{12}$/.test(related)){
   queueMicrotask(async()=>{
     try{
       const res=await fetch('/api/web/project?id='+encodeURIComponent(related),{cache:'no-store'});
       const data=await res.json();if(!res.ok||data.error)throw Error(data.error||'Site introuvable.');
       const project=data.project||{};
       if(!project.deployment?.production_url)throw Error('Publie d’abord ce site avant de créer sa campagne associée.');
       await getBrands();
       const brand=brands.find(b=>b.id===project.brand_id);
       startChat({brand,projectContext:'Site associé : '+(project.name||'')+' ('+project.deployment.production_url+').'});
     }catch(error){startChat();reply('Liaison avec le projet Web : '+error.message)}
   });
 }
})();
