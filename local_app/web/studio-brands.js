/* Shared brand kits: same origin, user-owned logos, no automatic claims. */
(()=>{
 'use strict';
 const $=id=>document.getElementById(id);
 const dialog=$('brandDialog'),form=$('brandForm'),list=$('brandList');
 const columns={
   name:'brandName',sector:'brandSector',audience:'brandAudience',
   slogan:'brandSlogan',description:'brandDescription',cta:'brandCTA',website:'brandWebsite',
   primary_color:'brandPrimaryColor',secondary_color:'brandSecondaryColor'
 };
 let brands=[],active=null,sending=false,encodedLogo=null;
 async function api(path,body){
   const response=await fetch(path,body===undefined?{cache:'no-store'}:{
      method:'POST',credentials:'same-origin',headers:{
        'Content-Type':'application/json','X-LocalAI-Brand':'1'},
      body:JSON.stringify(body)
   });
   let data={};try{data=await response.json()}catch{}
   if(!response.ok||data.error)throw Error(data.error||'Erreur de connexion');
   return data;
 }
 function setError(text){$('brandError').textContent=text||''}
 function open(item=null){
   active=item;encodedLogo=null;form.reset();$('brandSaveStatus').textContent='';
   $('brandLogo').value='';$('brandLogoPreview').hidden=true;
   for(const [field,id] of Object.entries(columns)){
     const fallback=field==='primary_color'?'#9b71e8':field==='secondary_color'?'#15202e':'';
     $(id).value=item?.[field]||fallback;
   }
   if(item?.logo_url){$('brandLogoPreview').src=item.logo_url+'&v='+Date.now();
     $('brandLogoPreview').hidden=false;}
   dialog.showModal();$('brandName').focus();
 }
 function card(item){
   const button=document.createElement('button');button.type='button';button.className='brand-card';
   button.setAttribute('aria-label','Modifier l’identité de '+item.name);
   const picture=item.logo_url?document.createElement('img'):document.createElement('div');
   if(item.logo_url){picture.src=item.logo_url;picture.alt='Logo '+item.name;picture.loading='lazy'}
   else{picture.className='brand-placeholder';picture.style.background=item.primary_color||'#664e88';
     picture.textContent=(item.name||'?').trim().slice(0,1).toLocaleUpperCase('fr')}
   const title=document.createElement('strong');title.textContent=item.name;
   const sector=document.createElement('small');sector.textContent=item.sector||'Identité personnalisée';
   const colors=document.createElement('span');colors.className='brand-colors';
   for(const key of ['primary_color','secondary_color']){
     const swatch=document.createElement('i');swatch.style.backgroundColor=item[key]||'#8b5dc7';
     colors.append(swatch);
   }
   button.append(picture,title,sector,colors);
   button.addEventListener('click',()=>open(item));
   return button;
 }
 function render(){
   list.replaceChildren();$('brandsCount').textContent=brands.length+' marque'+(brands.length===1?'':'s');
   if(!brands.length){
     const box=document.createElement('div');box.className='brands-empty';
     const title=document.createElement('strong');title.textContent='Votre première marque';
     const desc=document.createElement('span');desc.textContent='Enregistrez l’identité d’un client pour créer des publicités et sites cohérents.';
     box.append(title,desc);list.append(box);return;
   }
   brands.forEach(item=>list.append(card(item)));
 }
 async function reload(){
   setError('');
   try{
     const data=await api('/api/studio/brands');
     brands=Array.isArray(data.brands)?data.brands:[];
     render();
     const urlBrand=new URLSearchParams(location.search).get('brand');
     if(urlBrand&&/^[a-f0-9]{32}$/.test(urlBrand)){
       const found=brands.find(x=>x.id===urlBrand);
       if(found)open(found);
     }
   }catch(error){setError('Impossible de charger les marques : '+error.message)}
 }
 $('newBrand').addEventListener('click',()=>open());
 $('brandClose').addEventListener('click',()=>dialog.close());
 $('brandCancel').addEventListener('click',()=>dialog.close());
 $('brandLogo').addEventListener('change',async event=>{
   const file=event.target.files?.[0];
   encodedLogo=null;
   if(!file)return;
   if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>3_000_000){
     $('brandSaveStatus').textContent='Logo accepté : PNG, JPEG ou WebP de 3 Mo maximum.';
     $('brandLogo').value='';return;
   }
   try{
     encodedLogo=await new Promise((resolve,reject)=>{
       const reader=new FileReader();
       reader.onload=()=>resolve(String(reader.result||''));
       reader.onerror=()=>reject(Error('Impossible de lire ce logo.'));
       reader.readAsDataURL(file);
     });
     $('brandLogoPreview').src=encodedLogo;
     $('brandLogoPreview').hidden=false;$('brandSaveStatus').textContent='';
   }catch(error){$('brandSaveStatus').textContent=error.message}
 });
 form.addEventListener('submit',async event=>{
   event.preventDefault();if(sending)return;
   sending=true;$('brandSave').disabled=true;$('brandSaveStatus').textContent='Enregistrement…';
   const body={};for(const [field,id] of Object.entries(columns))body[field]=$(id).value;
   if(active)body.id=active.id;
   if(encodedLogo)body.logo_data=encodedLogo;
   try{
     const saved=await api('/api/studio/brand/save',body);
     if(!saved.brand?.id)throw Error('Marque non enregistrée.');
     localStorage.setItem('localai_studio_brand_id',saved.brand.id);
     dialog.close();await reload();
     $('brandsCount').textContent=brands.length+' marque'+(brands.length===1?'':'s')+' · identité enregistrée';
   }catch(error){$('brandSaveStatus').textContent=error.message}
   finally{sending=false;$('brandSave').disabled=false}
 });
 void reload();
})();