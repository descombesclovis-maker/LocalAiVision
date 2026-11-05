/* QCM V1 home: real latest Web projects, settings and update status. */
(()=>{'use strict';
 const brandButton=document.getElementById('homeBrandChoose');
 const showBrand=brand=>{
   if(!brand)return;
   document.getElementById('homeBrandName').textContent=brand.name;
   document.getElementById('homeBrandDescription').textContent=brand.sector||brand.description||'Votre identité de marque active';
   const logo=document.getElementById('homeBrandLogo');logo.src=brand.logo_url||'/assets/assets/custom-brand/studio-animated.svg';logo.alt='Logo '+brand.name;
   const card=document.querySelector('.brand-universe');
   if(/^#[0-9a-f]{6}$/i.test(brand.primary_color)&&/^#[0-9a-f]{6}$/i.test(brand.secondary_color))card.style.background='linear-gradient(115deg,'+brand.primary_color+','+brand.secondary_color+')';
   brandButton.textContent='Changer de marque';
 };
 if(brandButton){
   window.StudioBrandPicker.all().then(rows=>showBrand(rows.find(b=>b.id===window.StudioBrandPicker.selected()))).catch(()=>{});
   brandButton.addEventListener('click',async()=>{const b=await window.StudioBrandPicker.choose(window.StudioBrandPicker.selected());if(b){window.StudioBrandPicker.activate(b);showBrand(b)}});
 }
 const recent=document.getElementById('qcmHomeRecent');
 if(recent){
   fetch('/api/web/projects',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('API');return r.json()})
    .then(data=>{
      const list=Array.isArray(data.projects)?data.projects:[];
      const current=list.filter(p=>/^web-[a-f0-9]{12}$/.test(p.id||'')).slice(0,3);
      if(!current.length)return;
      const caption=document.createElement('b');caption.textContent='PROJETS RÉCENTS';recent.append(caption);
      for(const project of current){
        const a=document.createElement('a');a.href='/localaiweb/editor?id='+encodeURIComponent(project.id);
        a.textContent=(project.name||'Projet sans nom').slice(0,65);a.title='Reprendre '+a.textContent;recent.append(a);
      }
    }).catch(()=>{ /* Keep a clean welcome when the server has no project store. */ });
 }
 const motionToggle=document.getElementById('qcmMotionToggle'),MOTION_KEY='localai_studio_motion_reduced_v1';
 if(motionToggle){
   let manuallyReduced=false;
   try{manuallyReduced=localStorage.getItem(MOTION_KEY)==='1'}catch{}
   const system=matchMedia('(prefers-reduced-motion: reduce)');
   const apply=()=>{
     const reduced=manuallyReduced||system.matches;
     motionToggle.disabled=system.matches;
     document.body.classList.toggle('qcm-reduce-motion',reduced);
     motionToggle.setAttribute('aria-pressed',String(reduced));
     motionToggle.textContent=system.matches?'Animations réduites par le système':reduced?'✓ Réactiver les animations':'☾ Réduire les animations';
   };
   system.addEventListener('change',apply);
   apply();
   motionToggle.addEventListener('click',()=>{
     manuallyReduced=!manuallyReduced;
     try{localStorage.setItem(MOTION_KEY,manuallyReduced?'1':'0')}catch{}
     apply();
   });
 }
 const button=document.getElementById('qcmHomeUpdateCheck'),note=document.getElementById('qcmHomeUpdateStatus');
 button?.addEventListener('click',async()=>{
   button.disabled=true;note.textContent='Vérification de la dernière version…';
   try{
     const response=await fetch('/api/update/check',{cache:'no-store'});
     const data=await response.json();
     if(!response.ok||data.error)throw Error(data.error||'Recherche indisponible');
     const newest=data.latest_version||data.latest||data.version||data.remote_version||'';
     const current=data.local_version||data.current_version||'';
     note.textContent= data.update_available===true
       ?'Une mise à jour est disponible'+(newest?' : '+newest:'')+'.'
       :data.update_available===false?'Cette installation est à jour.':
        'Vérification effectuée'+(current?' · Version '+current:'')+'. Consulte les paramètres Vision pour installer.';
   }catch(error){note.textContent='Vérification impossible : '+error.message}
   finally{button.disabled=false}
 });
})();