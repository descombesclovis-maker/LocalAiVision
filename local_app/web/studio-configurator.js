/* LocalAI Studio — user-configurable visual design system.
   Scope deliberately additive: never changes model, project or account data. */
(()=>{'use strict';
 const KEY='localai_studio_design_v1';
 const $=id=>document.getElementById(id);
 const root=document.body;
 const dialog=$('studioConfigDialog');
 if(!dialog)return;
 let schema=null,chosen={},applied={},active='structure',saveMode='manual';
 const allowedKeys=new Set();
 const safeValue=(key,value)=>{
   const q=schema?.questions.find(row=>row.key===key);
   return q?.options.some(o=>o.value===value)?value:null;
 };
 const defaults=()=>{
   const d={};for(const q of schema.questions)d[q.key]=q.options[
     ['layout','order','palette','motion'].includes(q.key)?0:
     ['spacing','height','contrast','speed','mobile'].includes(q.key)?1:0
   ].value;
   Object.assign(d,{layout:'split',order:'web',width:'center',height:'balanced',
     heading:'center',nav:'top',cards:'rounded',spacing:'balanced',labels:'top',
     buttons:'bottom',buttonAlign:'left',icons:'top',descriptions:'full',footer:'visible',
     palette:'aurora',mood:'cinema',contrast:'balanced',type:'geometric',titleSize:'bold',
     background:'gradient',lighting:'diffuse',glass:'frost',shadow:'deep',
     art:'3d',logos:'normal',stroke:'thin',motion:'balanced',tilt:'soft',
     transition:'cinema',buttonMotion:'glow',cardMotion:'float',effects:'halo',
     speed:'normal',reveal:'fade',iconMotion:'rotate',ambient:'normal',
     activity:'active',shortcuts:'brands',accessibility:'system',remember:'manual',
     preview:'full',expert:'demand',mobile:'balanced',notifications:'bottom',
     confirm:'preview',scope:'home'});
   return d;
 };
 const clean=(input)=>{
   const values=defaults();
   if(input&&typeof input==='object'&&!Array.isArray(input)){
     for(const [k,v] of Object.entries(input))if(allowedKeys.has(k)&&safeValue(k,v)!==null)values[k]=v;
   }
   return values;
 };
 const assign=(options)=>{
   for(const q of schema.questions){
     const key=q.key;
     const v=options[key];
     root.dataset['studio'+key[0].toUpperCase()+key.slice(1)]=v;
   }
   const reduce=options.accessibility==='reduced'||matchMedia('(prefers-reduced-motion: reduce)').matches;
   root.classList.toggle('studio-motion-reduced',reduce||options.motion==='none');
   root.style.setProperty('--studio-duration',options.speed==='fast'?'0.24s':options.speed==='slow'?'0.85s':'0.44s');
   root.style.setProperty('--studio-gap',options.spacing==='airy'?'34px':options.spacing==='dense'?'12px':'21px');
   const cards=document.querySelector('.universe-choices');
   if(cards)cards.style.setProperty('--studio-custom-gap','var(--studio-gap)');
   const activity=document.querySelector('.studio-activity-pill, .studio-active-pill, #studioActivityPill');
   if(activity)activity.hidden=options.activity==='hidden';
   const brands=document.querySelector('.studio-hub-tools .universe-help-link:not(.studio-config-trigger)');
   if(brands)brands.hidden=options.shortcuts==='none';
 };
 const persist=()=>{
   try{localStorage.setItem(KEY,JSON.stringify({version:1,values:chosen,updatedAt:new Date().toISOString()}))}
   catch{status('Enregistrement impossible : stockage local non accessible.')}
 };
 const status=text=>{$('studioConfigFeedback').textContent=text};
 const renderTabs=()=>{
   const nav=$('studioConfigTabs');nav.replaceChildren();
   const names={structure:'01 · Disposition',visual:'02 · Identité',motion:'03 · Animations',workflow:'04 · Expérience'};
   for(const id of schema.groups){
     const b=document.createElement('button');b.type='button';b.textContent=names[id]||id;
     b.className='studio-config-tab'+(id===active?' is-active':'');
     b.setAttribute('aria-pressed',String(id===active));
     b.addEventListener('click',()=>{active=id;renderTabs();renderQuestions()});nav.append(b);
   }
 };
 const renderQuestions=()=>{
   const list=$('studioConfigQuestions');list.replaceChildren();
   let index=schema.questions.findIndex(q=>q.group===active);
   for(const q of schema.questions.filter(q=>q.group===active)){
     const field=document.createElement('fieldset');field.className='studio-config-field';
     const legend=document.createElement('legend');legend.textContent=(++index).toString().padStart(2,'0')+' · '+q.label;field.append(legend);
     const variants=document.createElement('div');variants.className='studio-config-options';
     for(const option of q.options){
       const label=document.createElement('label');label.className='studio-config-choice';
       const input=document.createElement('input');input.type='radio';input.name=q.key;input.value=option.value;input.checked=chosen[q.key]===option.value;
       const caption=document.createElement('span');caption.textContent=option.title;
       label.append(input,caption);
       input.addEventListener('change',()=>{
         chosen[q.key]=option.value;assign(chosen);
         updateProgress();if(chosen.remember==='auto'){applied={...chosen};persist()}
         status('Aperçu mis à jour. '+(chosen.remember==='auto'?'Choix enregistré.':'Valide pour conserver tes choix.'));
       });
       variants.append(label);
     }
     field.append(variants);list.append(field);
   }
 };
 const updateProgress=()=>{
   $('studioConfigProgress').value=Object.keys(chosen).filter(key=>allowedKeys.has(key)).length;
   $('studioConfigCount').textContent=schema.questions.length+' réglages';
 };
 const download=()=>{
   const blob=new Blob([JSON.stringify({app:'LocalAIStudio',version:1,values:chosen},null,2)],{type:'application/json'});
   const url=URL.createObjectURL(blob),anchor=document.createElement('a');
   anchor.href=url;anchor.download='LocalAIStudio-design.json';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
 const loadImport=async file=>{
   if(!file)return;if(file.size>200000){status('Fichier trop volumineux.');return}
   try{
     const data=JSON.parse(await file.text());
     if(data.app!=='LocalAIStudio'||data.version!==1)throw Error('Fichier de configuration incompatible.');
     chosen=clean(data.values);assign(chosen);renderTabs();renderQuestions();updateProgress();
     status('Configuration importée dans l’aperçu. Clique sur Appliquer pour l’enregistrer.');
   }catch(error){status('Import impossible : '+error.message)}
 };
 $('studioCustomize').addEventListener('click',()=>{
   chosen={...applied};assign(chosen);renderTabs();renderQuestions();
   updateProgress();dialog.showModal();$('studioConfigClose').focus();
 });
 $('studioConfigClose').addEventListener('click',()=>dialog.close());
 dialog.addEventListener('cancel',()=>{
   if(chosen.remember!=='auto'){chosen={...applied};assign(chosen)}
 });
 dialog.addEventListener('close',()=>{
   if(chosen.remember!=='auto'){chosen={...applied};assign(chosen)}
 });
 $('studioConfigForm').addEventListener('submit',event=>{
   event.preventDefault();applied={...chosen};persist();status('Configuration enregistrée.');dialog.close();
 });
 $('studioConfigReset').addEventListener('click',()=>{chosen=defaults();assign(chosen);renderQuestions();status('Valeurs par défaut affichées : applique pour sauvegarder.')});
 $('studioConfigExport').addEventListener('click',download);
 $('studioConfigImport').addEventListener('change',event=>{void loadImport(event.target.files?.[0]);event.target.value=''});
 fetch('/assets/studio-design-schema.json',{cache:'force-cache'})
   .then(r=>{if(!r.ok)throw Error('Questionnaire inaccessible.');return r.json()})
   .then(json=>{
     if(json.version!==1||!Array.isArray(json.questions)||json.questions.length<40)throw Error('Questionnaire incomplet.');
     const unique=new Set();
     for(const row of json.questions){
       if(!/^[a-zA-Z]+$/.test(row.key)||unique.has(row.key)||!Array.isArray(row.options)||row.options.length<2)throw Error('Questionnaire invalide.');
       unique.add(row.key);
     }
     schema=json;for(const row of schema.questions)allowedKeys.add(row.key);
     let stored={};try{stored=JSON.parse(localStorage.getItem(KEY)||'{}').values||{}}catch{}
     applied=clean(stored);chosen={...applied};assign(chosen);updateProgress();renderTabs();
   })
   .catch(error=>{$('studioCustomize').disabled=true;$('studioCustomize').title=error.message});
})();
