const $=s=>document.querySelector(s);
let comfyReady=false,llmReady=false,workflows=[],activeConversationId=null,imageData=null,imageName=null,videoData=null,lastHealth=null;
let loraCatalog=[],loraRemoteCatalog=[],selectedLoras=loadJSON('lva_selected_loras',[]);
let conversations=loadJSON('lva_conversations_v2',{}),library=loadJSON('lva_library',[]);
let modalSelection={image:null,video:null},modalStep=1;
let styleCatalog=[],graphicStyle=loadJSON('lva_graphic_style','none'),stylePreviews=loadJSON('lva_style_previews',{});
let modelAliases=loadJSON('lva_model_aliases',{});
let activeChatController=null,activeChatConversationId=null,activeChatStopRequested=false;
const STANDARD_IMAGE_WORKFLOW='text to image sdxl.json';
const STANDARD_VIDEO_WORKFLOW='Video Wan texte.json';
const ISOLATED_IMAGE_WORKFLOW='Isolated HunyuanImage 2.1.json';
const ISOLATED_VIDEO_WORKFLOW='Isolated HY-OmniWeaving T2V.json';
const ISOLATED_I2V_WORKFLOW='Isolated HY-OmniWeaving I2V.json';
let isolatedTaskMode=loadJSON('lva_isolated_task_mode','image');
let isolatedVideoMode=loadJSON('lva_isolated_video_mode','t2v');

const LEGACY_CHAT_SYSTEM="Réponds directement en français, de façon utile et précise. Pour les questions générales, utilise tes connaissances internes sans simuler de recherche Internet. Signale seulement les incertitudes réellement importantes. Tu n’as pas d’accès direct à Internet ni aux fichiers de l’utilisateur.";
const DEFAULT_CHAT_SYSTEM=`Tu es LocalAiVision, un assistant local généraliste, créatif et conversationnel. Tu es pensé comme le petit frère de ChatGPT : naturel, vif, chaleureux et utile, sans ton robotique.

Réponds en français sauf si l’utilisateur demande une autre langue. Garde le fil de toute la conversation fournie : quand l’utilisateur dit « ça », « ce qu’on disait », « rappelle-toi », « continue » ou fait référence à un message précédent, rattache correctement sa demande au contexte avant de répondre.

Pour les questions générales, utilise tes connaissances internes sans simuler une recherche Internet. N’invente pas un fait pour paraître sûr : si une information est réellement incertaine, dis-le brièvement. Quand l’utilisateur expose un problème, ne te contente pas de l’expliquer : propose spontanément la solution la plus adaptée et l’étape suivante concrète.

Adapte la longueur à la demande. Par défaut, écris comme dans une vraie conversation : phrases fluides, paragraphes courts, pas d’introduction scolaire ni de conclusion automatique. Utilise le Markdown naturellement : **mots importants en gras**, petites listes seulement quand elles aident, et quelques émojis bien choisis quand ils rendent la réponse plus vivante — jamais à chaque phrase.

Ne prétends pas avoir consulté Internet, un fichier ou une application si ce n’est pas réellement le cas.`;
const kinds={image:['Image','▧'],video:['Vidéo','▣'],'video-heavy':['Vidéo','▣']};
const PROFILE_DEFAULTS={
 auto:{label:'Automatique',sub:'LocalVision choisit entre photo et vidéo'},
 'companion-realistic':{label:'Standard',sub:'Photo RealVisXL V5 · vidéo Wan 2.1'},
 nsfw:{label:'Espace isolé',sub:'HunyuanImage 2.1 · HY-OmniWeaving'}
};

function loadJSON(k,f){try{const v=JSON.parse(localStorage.getItem(k));return v??f}catch{return f}}
function save(){try{localStorage.setItem('lva_conversations_v2',JSON.stringify(conversations));localStorage.setItem('lva_library',JSON.stringify(library))}catch(e){toast('Stockage local plein : cette conversation ne peut plus être enregistrée.')}}
function toast(t){const e=$('#toast');if(!e)return;e.textContent=t;e.classList.add('show');setTimeout(()=>e.classList.remove('show'),2600)}
async function api(url,opt){const r=await fetch(url,opt);let d={};try{d=await r.json()}catch{}if(!r.ok||d.error)throw new Error(d.error||('Erreur HTTP '+r.status));return d}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
function workflowById(id){return workflows.find(w=>w.id===id)||null}
function bestWorkflowId(id){return workflows.find(w=>w.id===id)?.id||workflows.find(w=>w.name.toLowerCase()===String(id).replace(/\.json$/i,'').toLowerCase())?.id||null}
function displayModelName(w){return modelAliases[w.id]||w.name}
function profileLabel(key){return modelAliases['profile:'+key]||PROFILE_DEFAULTS[key]?.label||key}
function profileSub(key){return PROFILE_DEFAULTS[key]?.sub||''}

const APPLE_EMOJI_AVAILABLE=(()=>{try{return !!document.fonts?.check('16px "Apple Color Emoji"')}catch{return false}})();
const EMOJI_SEGMENTER=(()=>{try{return typeof Intl!=='undefined'&&Intl.Segmenter?new Intl.Segmenter(undefined,{granularity:'grapheme'}):null}catch{return null}})();
function isEmojiCluster(s){try{return /\p{Extended_Pictographic}/u.test(s)||/[#*0-9]\uFE0F?\u20E3/u.test(s)}catch{return false}}
function emojiCodepoints(s){return Array.from(s).map(ch=>ch.codePointAt(0).toString(16).toLowerCase()).join('-')}
function appendEmojiAwareText(parent,text){
 const parts=EMOJI_SEGMENTER?[...EMOJI_SEGMENTER.segment(String(text||''))].map(x=>x.segment):Array.from(String(text||''));let plain='';
 const flush=()=>{if(plain){parent.appendChild(document.createTextNode(plain));plain=''}};
 for(const part of parts){if(!isEmojiCluster(part)){plain+=part;continue}flush();if(APPLE_EMOJI_AVAILABLE){const span=document.createElement('span');span.className='emoji-native-apple';span.textContent=part;parent.appendChild(span);continue}const img=document.createElement('img');img.className='emoji-3d';img.alt=part;img.title=part;img.loading='lazy';img.decoding='async';img.src='https://cdn.jsdelivr.net/gh/shuding/fluentui-emoji-unicode/assets/'+emojiCodepoints(part)+'_3d.png';img.onerror=()=>{const fallback=document.createElement('span');fallback.className='emoji-native-fallback';fallback.textContent=part;img.replaceWith(fallback)};parent.appendChild(img)}flush();
}
function appendInlineMarkup(parent,text){const re=/(\*\*[^*]+\*\*|`[^`]+`)/g;let last=0;for(const match of text.matchAll(re)){if(match.index>last)appendEmojiAwareText(parent,text.slice(last,match.index));const token=match[0],node=document.createElement(token.startsWith('**')?'strong':'code');if(token.startsWith('**'))appendEmojiAwareText(node,token.slice(2,-2));else node.textContent=token.slice(1,-1);parent.appendChild(node);last=match.index+token.length}if(last<text.length)appendEmojiAwareText(parent,text.slice(last))}
function renderAssistantText(el,text){el.textContent='';const lines=String(text||'').replace(/\r/g,'').split('\n');let list=null;for(const raw of lines){const line=raw.trimEnd(),bullet=line.match(/^\s*[-*]\s+(.+)/);if(bullet){if(!list){list=document.createElement('ul');list.className='md-list';el.appendChild(list)}const li=document.createElement('li');appendInlineMarkup(li,bullet[1]);list.appendChild(li);continue}list=null;if(!line.trim()){const gap=document.createElement('div');gap.className='md-gap';el.appendChild(gap);continue}const heading=line.match(/^#{1,3}\s+(.+)/),p=document.createElement(heading?'div':'p');p.className=heading?'md-heading':'md-paragraph';appendInlineMarkup(p,heading?heading[1]:line);el.appendChild(p)}}
function dismissKeyboard(){const p=$('#prompt');if(document.activeElement===p)p.blur()}
function setChatAnswering(active){document.querySelector('.composer')?.classList.toggle('chat-answering',!!active)}
async function stopActiveChat(){if(!activeChatController)return;activeChatStopRequested=true;try{fetch('/api/chat/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).catch(()=>{})}catch{}activeChatController.abort()}

function normalizeConversation(c){c.settings=c.settings||{};for(const k of ['image','video'])if(!(k in c.settings))c.settings[k]=null;delete c.settings.motion;delete c.settings.retouch;c.messages=Array.isArray(c.messages)?c.messages:[];return c}
function conversationFor(id){if(!conversations[id])conversations[id]={id,title:'Nouvelle conversation',createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),profile:'auto',settings:{image:null,video:null},messages:[]};return normalizeConversation(conversations[id])}
function titleForConversation(c){return c?.title||'Nouvelle conversation'}
function createBlankConversation(profile='auto'){
 const c={id:crypto.randomUUID(),title:profile==='auto'?'Nouvelle conversation':profileLabel(profile),createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),profile,settings:{image:null,video:null},messages:[]};
 conversations[c.id]=c;applyProfileSettings(c,profile);activeConversationId=c.id;save();openConversation(c.id);return c;
}
function applyProfileSettings(c,profile){
 c.profile=profile||'auto';
 if(profile==='companion-realistic'){c.settings.image=bestWorkflowId(STANDARD_IMAGE_WORKFLOW);c.settings.video=bestWorkflowId(STANDARD_VIDEO_WORKFLOW);}
 else if(profile==='nsfw'){c.settings.image=bestWorkflowId(ISOLATED_IMAGE_WORKFLOW);c.settings.video=bestWorkflowId(ISOLATED_VIDEO_WORKFLOW);}
}
async function createConversationForProfile(profile){
 if(profile==='nsfw'&&!$('#nsfwGate')?.checked){toast('Coche d’abord « Activer l’espace NSFW » dans le menu.');showSidebar();return null}
 const c=createBlankConversation(profile);$('#taskMode').value='auto';hideSidebar();
 if(profile==='companion-realistic'&&!lastHealth?.media?.image?.ready)toast('RealVisXL sera repris/téléchargé automatiquement à la première génération.');
 if(profile==='nsfw'&&!lastHealth?.media?.['isolated-image']?.ready){toast('Préparation de HunyuanImage 2.1…');installComponent('isolated-image')}
 syncModelSelectors();renderProfileLabels();return c;
}
function currentCreationKind(){
 const conv=activeConversationId?conversationFor(activeConversationId):null;
 if(conv?.profile==='nsfw')return isolatedTaskMode==='video'?'video':'image';
 const mode=$('#taskMode')?.value||'auto';
 return mode==='chat'?'chat':mode==='video'?'video':mode==='image'?'image':'auto';
}
function updateSettingsVisibility(){
 const conv=activeConversationId?conversationFor(activeConversationId):null;
 const isolated=conv?.profile==='nsfw',kind=currentCreationKind(),visual=kind!=='chat';
 const video=kind==='video'||kind==='auto',chat=kind==='chat'||kind==='auto';
 $('#standardModeControls')?.classList.toggle('hidden',isolated);
 $('#nsfwModePanel')?.classList.toggle('hidden',!isolated);
 $('#accordionStyles')?.classList.toggle('hidden',isolated||kind==='chat');
 $('#accordionLoras')?.classList.toggle('hidden',!(isolated&&isolatedTaskMode==='video'));
 document.querySelectorAll('.standard-only').forEach(e=>e.classList.toggle('settings-field-hidden',isolated));
 document.querySelectorAll('.visual-only').forEach(e=>e.classList.toggle('settings-field-hidden',!visual));
 document.querySelectorAll('.video-only').forEach(e=>e.classList.toggle('settings-field-hidden',!video));
 document.querySelectorAll('.chat-only').forEach(e=>e.classList.toggle('settings-field-hidden',!chat||isolated));
 $('#accordionSimple')?.classList.toggle('hidden',!visual);
}
function updateCreationModeGuide(){
 const conv=activeConversationId?conversationFor(activeConversationId):null,isolated=conv?.profile==='nsfw';
 document.body.classList.toggle('nsfw-active',!!isolated);
 const guide=$('#creationModeGuide'),prompt=$('#prompt');
 if(guide)guide.innerHTML=isolated
   ?'<b>Espace isolé · Hunyuan</b> <span>HunyuanImage 2.1 · HY-OmniWeaving T2V/I2V · prompt direct.</span>'
   :'<b>Création standard</b> <span>RealVisXL V5 · Wan 2.1 · chat local.</span>';
 if(prompt)prompt.placeholder=isolated?(isolatedTaskMode==='image'?'Décris l’image souhaitée…':isolatedVideoMode==='i2v'?'Décris le mouvement à appliquer à l’image…':'Décris la vidéo souhaitée…'):'Écris ton message…';
 const isolatedLinks=$('#nsfwLibraryLinks');
 if(isolatedLinks)isolatedLinks.classList.toggle('hidden',!loadJSON('lva_nsfw_gate',false));
 updateSettingsVisibility();
}
function renderProfileLabels(){
 const map={modelAuto:'auto',modelRealistic:'companion-realistic',modelNsfw:'nsfw'};
 const active=activeConversationId?conversations[activeConversationId]:null;for(const [id,key] of Object.entries(map)){const b=$('#'+id);if(!b)continue;const strong=b.querySelector('b'),small=b.querySelector('small');if(strong)strong.textContent=profileLabel(key);if(small)small.textContent=profileSub(key);b.classList.toggle('active',active?.profile===key)}
 updateCreationModeGuide();renderIsolatedMode();
}
function renderIsolatedMode(){
 const isolated=activeConversationId&&conversationFor(activeConversationId).profile==='nsfw';
 if(isolated){
  $('#isolatedModeImage')?.classList.toggle('active',isolatedTaskMode==='image');
  $('#isolatedModeT2V')?.classList.toggle('active',isolatedTaskMode==='video'&&isolatedVideoMode==='t2v');
  $('#isolatedModeI2V')?.classList.toggle('active',isolatedTaskMode==='video'&&isolatedVideoMode==='i2v');
  $('#isolatedPhotoInfo')?.classList.toggle('hidden',isolatedTaskMode!=='image');
  $('#isolatedVideoInfo')?.classList.toggle('hidden',isolatedTaskMode!=='video');
  const source=$('#isolatedVideoSource');if(source)source.value=isolatedVideoMode;
  const needImage=isolatedTaskMode==='video'&&isolatedVideoMode==='i2v';
  $('#isolatedImageAttachment')?.classList.toggle('hidden',!needImage);
  if($('#referenceImageName'))$('#referenceImageName').textContent=imageName||'Aucune image jointe';
  $('#clearReferenceImage')?.classList.toggle('hidden',!imageData);
 }
 updateSettingsVisibility();
}
function chooseIsolatedCreationMode(mode){
 if(mode==='image'){isolatedTaskMode='image'}
 else{isolatedTaskMode='video';isolatedVideoMode=mode==='i2v'?'i2v':'t2v'}
 localStorage.setItem('lva_isolated_task_mode',JSON.stringify(isolatedTaskMode));
 localStorage.setItem('lva_isolated_video_mode',JSON.stringify(isolatedVideoMode));
 renderProfileLabels();
 const component=isolatedTaskMode==='image'?'isolated-image':(isolatedVideoMode==='i2v'?'isolated-video-i2v':'isolated-video');
 if(!lastHealth?.media?.[component]?.ready)installComponent(component);
}
function clearReferenceImage(){imageData=null;imageName=null;const input=$('#referenceImageInput');if(input)input.value='';renderIsolatedMode()}
function loadReferenceImage(file){
 if(!file)return;if(!file.type?.startsWith('image/')){toast('Choisis un fichier image.');return}
 const reader=new FileReader();reader.onload=()=>{imageData=String(reader.result||'');imageName=file.name;renderIsolatedMode();toast('Image de départ ajoutée.')};reader.onerror=()=>toast('Impossible de lire cette image.');reader.readAsDataURL(file);
}
function loraCompatibilityText(x){const base=String(x.base_model||x.compatibility||'').trim();return base||'Compatibilité non déclarée'}
function loraMatches(x,q){return !q||[x.name,x.filename,x.base_model,x.compatibility,x.category,x.description,(x.trained_words||[]).join(' ')].join(' ').toLowerCase().includes(q)}
function renderLoraCatalog(filter=''){
 const localBox=$('#loraCatalog'),remoteBox=$('#loraRemoteCatalog');if(!localBox||!remoteBox)return;const q=String(filter||'').toLowerCase().trim();localBox.innerHTML='';remoteBox.innerHTML='';
 const rows=loraCatalog.filter(x=>loraMatches(x,q));
 if(!rows.length)localBox.innerHTML='<div class="lora-empty">Aucun LoRA local correspondant. Les .safetensors présents dans ComfyUI/models/loras apparaissent ici.</div>';
 for(const x of rows){
  const id=x.path||x.filename,selected=selectedLoras.find(v=>v.path===id),card=document.createElement('div');card.className='lora-card'+(selected?' selected':'');
  const words=(x.trained_words||[]).join(', '),size=x.size?((x.size/1024/1024).toFixed(0)+' Mo'):'',desc=x.description||'LoRA installé localement.';
  card.innerHTML='<div class="lora-main"><b>'+esc(x.name||x.filename)+'</b><small>'+esc(loraCompatibilityText(x))+(size?' · '+size:'')+'</small><span>'+esc(desc)+'</span>'+(words?'<span>Déclencheurs : '+esc(words)+'</span>':'')+'</div><label>Force <input type="number" min="-2" max="2" step="0.05" value="'+esc(selected?.strength??1)+'"></label><button type="button">'+(selected?'Retirer':'Activer')+'</button>';
  const strength=card.querySelector('input'),button=card.querySelector('button');
  strength.onchange=()=>{const found=selectedLoras.find(v=>v.path===id);if(found){found.strength=Number(strength.value)||1;localStorage.setItem('lva_selected_loras',JSON.stringify(selectedLoras))}};
  button.onclick=()=>{const at=selectedLoras.findIndex(v=>v.path===id);if(at>=0)selectedLoras.splice(at,1);else selectedLoras.push({path:id,strength:Number(strength.value)||1});localStorage.setItem('lva_selected_loras',JSON.stringify(selectedLoras));renderLoraCatalog($('#loraSearch')?.value||'')};
  localBox.appendChild(card);
 }
 const remote=loraRemoteCatalog.filter(x=>loraMatches(x,q));
 if(!remote.length)remoteBox.innerHTML='<div class="lora-empty">Aucun élément correspondant dans le catalogue général.</div>';
 for(const x of remote){
  const card=document.createElement('div');card.className='lora-card catalog-card'+(x.installed?' installed':'');
  const words=(x.trained_words||[]).join(', ');
  card.innerHTML='<div class="lora-main"><b>'+esc(x.name)+'</b><small>'+esc(x.category||'Catalogue général')+' · '+esc(x.compatibility||x.base_model||'Hunyuan Video')+(x.source?' · '+esc(x.source):'')+'</small><span>'+esc(x.description||'LoRA du catalogue général LocalVisionAI.')+'</span>'+(words?'<span>Déclencheurs : '+esc(words)+'</span>':'')+'</div><div></div><button type="button" '+(x.installed?'disabled':'')+'>'+(x.installed?'Installé ✓':'Télécharger')+'</button>';
  const button=card.querySelector('button');if(!x.installed)button.onclick=()=>installCatalogLora(x,button);
  remoteBox.appendChild(card);
 }
}
async function installCatalogLora(x,button){
 button.disabled=true;button.textContent='Téléchargement…';
 try{await api('/api/loras/install',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lora_id:x.lora_id})});toast('LoRA installé.');await refreshLoras()}
 catch(e){toast(e.message);button.disabled=false;button.textContent='Télécharger'}
}
async function refreshLoras(){try{const d=await api('/api/loras');loraCatalog=d.loras||[];loraRemoteCatalog=d.catalog||[];renderLoraCatalog($('#loraSearch')?.value||'')}catch(e){if($('#loraCatalog'))$('#loraCatalog').innerHTML='<div class="lora-empty">'+esc(e.message)+'</div>'}
}
function renameProfile(key){const next=prompt('Nouveau nom du modèle',profileLabel(key));if(next===null)return;const clean=next.trim();if(clean)modelAliases['profile:'+key]=clean;else delete modelAliases['profile:'+key];localStorage.setItem('lva_model_aliases',JSON.stringify(modelAliases));renderProfileLabels()}

function renderConversationList(filter=''){
 const box=$('#conversationsList');box.innerHTML='';const rows=Object.values(conversations).map(normalizeConversation).sort((a,b)=>new Date(b.updatedAt)-new Date(a.updatedAt)).filter(c=>titleForConversation(c).toLowerCase().includes(filter.toLowerCase()));
 if(!rows.length){box.innerHTML='<div class="empty-conversations">Aucune conversation</div>';return}
 for(const c of rows){const row=document.createElement('div');row.className='conversation-row';const b=document.createElement('button');b.className='conversation-item'+(activeConversationId===c.id?' active':'');const n=['image','video'].filter(k=>c.settings?.[k]).length;b.innerHTML='<span class="conversation-icon">◌</span><span class="conversation-main"><span class="conversation-title">'+esc(titleForConversation(c))+'</span><span class="conversation-meta">'+(c.profile&&c.profile!=='auto'?esc(profileLabel(c.profile)):n?`${n} modèle${n>1?'s':''} imposé${n>1?'s':''}`:'Sélection automatique')+'</span></span><i class="conversation-dot '+(n?'ready':'')+'"></i>';b.onclick=()=>openConversation(c.id);const controls=document.createElement('span');controls.className='conversation-controls';const rename=document.createElement('button');rename.className='tiny-action';rename.title='Renommer';rename.textContent='✎';rename.onclick=e=>{e.stopPropagation();renameConversation(c.id)};const del=document.createElement('button');del.className='tiny-action';del.title='Supprimer';del.textContent='×';del.onclick=e=>{e.stopPropagation();deleteConversation(c.id)};controls.append(rename,del);row.append(b,controls);box.appendChild(row)}
}
function renameConversation(id){const c=conversationFor(id),next=prompt('Renommer la conversation',titleForConversation(c));if(next===null)return;const clean=next.trim();if(!clean)return;c.title=clean;c.updatedAt=new Date().toISOString();save();renderConversationList($('#conversationSearch').value)}
function deleteConversation(id){const c=conversationFor(id);if(!confirm('Supprimer « '+titleForConversation(c)+' » ?'))return;delete conversations[id];if(activeConversationId===id){activeConversationId=null;const next=Object.values(conversations).sort((a,b)=>new Date(b.updatedAt)-new Date(a.updatedAt))[0];if(next)openConversation(next.id);else createBlankConversation()}save();renderConversationList($('#conversationSearch').value)}
function openConversation(id){activeConversationId=id;const c=conversationFor(id);renderConversationList($('#conversationSearch').value);$('#welcome').classList.toggle('hidden',c.messages.length>0);const box=$('#messages');box.innerHTML='';c.messages.forEach(renderMessage);syncModelSelectors();renderProfileLabels();scrollBottom();hideSidebar()}

function resultUrl(x){return '/api/view?filename='+encodeURIComponent(x.filename||'')+'&subfolder='+encodeURIComponent(x.subfolder||'')+'&type='+encodeURIComponent(x.type||'output')}
function renderMessage(m){
 const wrap=document.createElement('div');wrap.className='message '+(m.role==='user'?'user':'assistant');if(m.loading)wrap.dataset.loading='1';
 if(m.text||m.streaming){const b=document.createElement('div');b.className='bubble'+(m.streaming?' streaming':'');if(m.role==='assistant'&&!m.streaming)renderAssistantText(b,m.text);else b.textContent=m.text||'';wrap.appendChild(b)}
 if(m.loading){if(m.chatLoading){const wait=document.createElement('div');wait.className='chat-waiting';const dots=document.createElement('span');dots.className='chat-dots';dots.innerHTML='<i></i><i></i><i></i>';const stop=document.createElement('button');stop.type='button';stop.className='chat-stop';stop.title='Arrêter la réponse';stop.textContent='×';stop.onclick=stopActiveChat;wait.append(dots,stop);wrap.appendChild(wait)}else{const label=document.createElement('div');label.className='generation-label';label.textContent=m.mediaType==='video'?'Génération de la vidéo…':'Génération de la photo…';label.dataset.defaultText=label.textContent;wrap.appendChild(label);const f=document.createElement('div');f.className='generation-frame loading';f.innerHTML='<div class="loader"></div>';wrap.appendChild(f)}}
 if(m.result){const f=document.createElement('div');f.className='generation-frame';const src=resultUrl(m.result),video=/\.(mp4|webm|mov|mkv)$/i.test(m.result.filename||'');f.innerHTML=video?'<video class="result-media" controls src="'+src+'"></video>':'<img class="result-media" src="'+src+'">';wrap.appendChild(f)}
 $('#messages').appendChild(wrap);return wrap;
}
function scrollBottom(){requestAnimationFrame(()=>{$('#chat').scrollTop=$('#chat').scrollHeight})}
function addMessage(id,m){const c=conversationFor(id);c.messages.push(m);c.updatedAt=new Date().toISOString();if(c.title==='Nouvelle conversation'&&m.role==='user')c.title=m.text.slice(0,48)+(m.text.length>48?'…':'');save();renderConversationList($('#conversationSearch').value);if(id===activeConversationId){$('#welcome').classList.add('hidden');renderMessage(m);scrollBottom()}}
function removeLoading(id){const c=conversationFor(id);c.messages=c.messages.filter(m=>!m.loading);c.updatedAt=new Date().toISOString();save();if(id===activeConversationId)$('#messages').querySelectorAll('.message[data-loading="1"]').forEach(x=>x.remove())}

function modelsFor(task){return workflows.filter(w=>task==='image'?w.kind==='image':w.kind==='video'||w.kind==='video-heavy')}
function resultKindForModel(model){return ['video','video-heavy'].includes(model?.kind)?'video':'image'}
function selectedModelForConversation(c,task,promptText=''){
 const style=styleCatalog.find(x=>x.id===graphicStyle);return chooseStyleWorkflow(task,workflows,c.settings?.[task],style,!!imageData,task==='image'?stylePreviews[graphicStyle]:null,promptText,!!videoData);
}
function styleWorkflowSummary(){const mode=$('#taskMode').value;const task=['image','video'].includes(mode)?mode:explicitGenerationRequest($('#prompt').value)||'image';const conv=activeConversationId?conversationFor(activeConversationId):{settings:{}};const w=selectedModelForConversation(conv,task,$('#prompt').value);$('#styleWorkflow').textContent=w?('Moteur '+task+' : '+displayModelName(w)+(w.models?.length?' · '+w.models.join(', '):'')+(w.ready===false?' · à installer / configurer':w.ready===true?' · prêt':' · disponibilité à vérifier')):'Aucun workflow disponible'}
function syncModelSelectors(){
 const c=activeConversationId?conversationFor(activeConversationId):null;for(const [task,sel] of [['image','#settingImageModel'],['video','#settingVideoModel']]){const e=$(sel);if(!e)continue;const rows=modelsFor(task);e.innerHTML='<option value="">Automatique</option>'+rows.map(w=>'<option value="'+esc(w.id)+'">'+esc(displayModelName(w))+'</option>').join('');e.value=c?.settings?.[task]||'';e.onchange=()=>{if(!activeConversationId)return;const cc=conversationFor(activeConversationId);cc.settings[task]=e.value||null;if(cc.profile!=='nsfw')cc.profile='auto';cc.updatedAt=new Date().toISOString();save();renderConversationList();renderProfileLabels();styleWorkflowSummary()}}
 renderRenameModelSelect();
}
function renameModel(id,current){const next=prompt('Nouveau nom du modèle',current);if(next===null)return;const clean=next.trim();if(clean)modelAliases[id]=clean;else delete modelAliases[id];localStorage.setItem('lva_model_aliases',JSON.stringify(modelAliases));syncModelSelectors();renderProfileLabels();styleWorkflowSummary()}
function renderRenameModelSelect(){const e=$('#renameModelSelect');if(!e)return;const old=e.value;e.innerHTML=workflows.map(w=>'<option value="'+esc(w.id)+'">'+esc(displayModelName(w))+'</option>').join('');if(workflowById(old))e.value=old}
function renderStyles(){const grid=$('#styleGrid');grid.innerHTML='';for(const style of styleCatalog){const preview=stylePreviews[style.id],button=document.createElement('button');button.type='button';button.className='style-card'+(graphicStyle===style.id?' selected':'');const thumb=document.createElement('span');thumb.className='style-thumbnail';thumb.style.backgroundPosition=style.position;if(preview){const img=document.createElement('img');img.src=resultUrl(preview);img.alt=style.name+' — résultat local';img.onerror=()=>img.remove();thumb.appendChild(img)}const name=document.createElement('b');name.textContent=style.name;const origin=document.createElement('small');origin.textContent=preview?'Ton résultat local':'Illustration du style';button.append(thumb,name,origin);button.onclick=()=>{graphicStyle=style.id;localStorage.setItem('lva_graphic_style',JSON.stringify(graphicStyle));renderStyles()};grid.appendChild(button)}$('#generateStylePreview').disabled=graphicStyle==='none'||$('#send').disabled;styleWorkflowSummary()}

function renderOptions(task,filter=''){const box=$('#'+task+'Options');if(!box)return;box.innerHTML='';const rows=modelsFor(task).filter(w=>displayModelName(w).toLowerCase().includes(filter.toLowerCase()));if(!rows.length){box.innerHTML='<div class="no-model">Aucun modèle compatible trouvé.</div>';return}for(const w of rows){const selected=modalSelection[task]===w.id,b=document.createElement('button');b.className='model-option'+(selected?' selected':'');const label=kinds[w.kind]?.[0]||task;b.innerHTML='<span class="option-icon">'+(w.icon||'◌')+'</span><span><b>'+esc(displayModelName(w))+'</b><small>'+label+(w.ready===false?' · à préparer':'')+'</small></span>';b.onclick=()=>{modalSelection[task]=w.id;renderOptions(task,$('[data-search="'+task+'"]')?.value||'')};box.appendChild(b)}}
function setModalStep(step){modalStep=step;$('#imageStep').classList.toggle('hidden',step!==1);$('#videoStep').classList.toggle('hidden',step!==2);$('#modalTitle').textContent=step===1?'Avec quel modèle générer ton image':'Avec quel modèle générer ta vidéo';$('#modalSubtitle').textContent='Tu peux aussi laisser Automatique dans les paramètres de la conversation.';$('#stepProgress').textContent=step+'/2';$('#stepValidate').textContent=step===1?'Valider':'Créer la conversation';$('#modalError').textContent='';renderOptions(step===1?'image':'video')}
function openModelModal(){modalSelection={image:null,video:null};setModalStep(1);$('#modelModal').classList.remove('hidden')}
function closeModelModal(){$('#modelModal').classList.add('hidden')}
function createConversation(){const c=createBlankConversation();c.settings.image=modalSelection.image;c.settings.video=modalSelection.video;save();closeModelModal();syncModelSelectors();toast('Conversation créée.')}
function advanceModelStep(){if(modalStep===1){if(!modalSelection.image){$('#modalError').textContent='Sélectionne un modèle photo avant de continuer.';return}setModalStep(2);return}if(!modalSelection.video){$('#modalError').textContent='Sélectionne un modèle vidéo avant de créer la conversation.';return}createConversation()}

function renderLibraryCounts(){
 const standard=library.filter(x=>x.profile!=='nsfw'),isolated=library.filter(x=>x.profile==='nsfw');
 const p=standard.filter(x=>x.kind==='image').length,v=standard.filter(x=>x.kind==='video').length;
 if($('#photoCount'))$('#photoCount').textContent=p||'';
 if($('#videoCount'))$('#videoCount').textContent=v||'';
 if($('#nsfwPhotoCount'))$('#nsfwPhotoCount').textContent=isolated.filter(x=>x.kind==='image').length||'';
 if($('#nsfwVideoCount'))$('#nsfwVideoCount').textContent=isolated.filter(x=>x.kind==='video').length||'';
}
function addLibrary(result,kind,promptText,profile='auto'){library.unshift({...result,_id:crypto.randomUUID(),kind,prompt:promptText,profile,createdAt:new Date().toISOString()});save();renderLibraryCounts()}
async function deleteLibraryItem(id){const item=library.find(x=>x._id===id);if(!item)return;if(!confirm('Supprimer ce fichier généré ?'))return;try{await api('/api/delete-output',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:item.filename,subfolder:item.subfolder||'',type:item.type||'output'})})}catch(e){toast('Entrée retirée, fichier non supprimé : '+e.message)}library=library.filter(x=>x._id!==id);save();renderLibraryCounts();renderLibrary(item.kind,item.profile==='nsfw'?(item.kind==='image'?'Photos espace isolé':'Vidéos espace isolé'):(item.kind==='image'?'Mes photos générées':item.kind==='video'?'Mes vidéos générées':'Mes retouches générées'),item.profile==='nsfw'?'nsfw':'standard')}
function renderLibrary(kind,title,scope='standard'){$('#welcome').classList.add('hidden');$('#messages').innerHTML='';const box=document.createElement('div');box.className='library-view';box.innerHTML='<button class="library-back" id="libraryBack">← Retour à la conversation</button><h2>'+esc(title)+'</h2><div class="library-grid"></div>';$('#messages').appendChild(box);const grid=box.querySelector('.library-grid'),rows=library.filter(x=>x.kind===kind&&(scope==='nsfw'?x.profile==='nsfw':x.profile!=='nsfw'));$('#libraryBack').onclick=()=>activeConversationId?openConversation(activeConversationId):createBlankConversation();if(!rows.length){grid.innerHTML='<div class="empty-library">Aucune création enregistrée ici.</div>';return}for(const x of rows){if(!x._id)x._id=crypto.randomUUID();const c=document.createElement('div');c.className='library-card';const src=resultUrl(x),video=/\.(mp4|webm|mov|mkv)$/i.test(x.filename||'');c.innerHTML=(video?'<video controls src="'+src+'"></video>':'<img src="'+src+'">')+'<div class="meta">'+esc(x.prompt||'Création')+'</div>';const del=document.createElement('button');del.className='library-delete';del.title='Supprimer';del.textContent='×';del.onclick=()=>deleteLibraryItem(x._id);c.appendChild(del);grid.appendChild(c)}save()}

async function sendMessage(){
 if($('#send').disabled)return;
 const text=$('#prompt').value.trim();if(!text)return;
 if(!activeConversationId)createBlankConversation();
 const conv=conversationFor(activeConversationId);
 addMessage(activeConversationId,{role:'user',text});
 $('#prompt').value='';$('#prompt').style.height='';dismissKeyboard();
 const mode=$('#taskMode').value;
 let task=mode==='auto'?explicitGenerationRequest(text):mode==='chat'?null:mode;
 let model=null;
 if(conv.profile==='nsfw'){
   task=isolatedTaskMode;
   if(task==='image')model=workflowById(bestWorkflowId(ISOLATED_IMAGE_WORKFLOW));
   else if(isolatedVideoMode==='i2v'){
     if(!imageData){addMessage(activeConversationId,{role:'assistant',text:'Ajoute une image de départ pour utiliser Image → Vidéo.'});return}
     model=workflowById(bestWorkflowId(ISOLATED_I2V_WORKFLOW));
   }else model=workflowById(bestWorkflowId(ISOLATED_VIDEO_WORKFLOW));
 }else{
   if(mode==='auto'&&!task&&(conv.profile==='companion-realistic'||!!conv.settings?.image))task=implicitVisualGenerationRequest(text);
   if(task==='image')model=workflowById(bestWorkflowId(STANDARD_IMAGE_WORKFLOW));
   if(task==='video')model=workflowById(bestWorkflowId(STANDARD_VIDEO_WORKFLOW));
 }
 if(task){conv.messages[conv.messages.length-1].mediaRequest=true;save()}
 if(!task){await startChat(conv,text);return}
 if(!model)model=selectedModelForConversation(conv,task,text);
 if(!model){addMessage(activeConversationId,{role:'assistant',text:'Aucun modèle n’est configuré pour cette tâche.'});return}
 await startGeneration(task,model,text)
}
function numberSetting(id){const e=$(id);if(!e)return null;const raw=e.value.trim();if(raw==='')return null;const n=Number(raw);return Number.isFinite(n)?n:null}
function readGenerationSettings(task){const isVideo=task==='video',conv=activeConversationId?conversationFor(activeConversationId):null,isIsolated=conv?.profile==='nsfw';return {quality:$('#settingQuality').value,steps:numberSetting('#settingSteps'),aspect:$('#settingAspect').value,seed:numberSetting('#settingSeed'),count:Number($('#settingCount').value)||1,duration:isVideo?numberSetting('#settingDuration'):null,fps:isVideo?numberSetting('#settingFps'):null,width:numberSetting('#settingWidth'),height:numberSetting('#settingHeight'),keepSeed:$('#settingKeep').checked,style:isIsolated?'none':graphicStyle,technical_quality:isIsolated?false:$('#settingTechnicalQuality')?.checked!==false,prompt_translation:$('#settingPromptTranslation')?.checked===true,reserved_profile:null,exact_prompt:isIsolated}}
function readChatSettings(){return {temperature:Math.min(2,Math.max(0,numberSetting('#settingTemperature')??0.7)),max_tokens:Math.min(8192,Math.max(128,numberSetting('#settingMaxTokens')??2048)),system:$('#settingSystem').value.trim()}}
async function startChat(c,text){
 const id=activeConversationId,history=c.messages.filter(m=>m.text&&!m.loading&&!m.error).map(m=>({role:m.role==='user'?'user':'assistant',content:m.text})),settings=readChatSettings(),messages=[];if(settings.system)messages.push({role:'system',content:settings.system});messages.push(...history);$('#send').disabled=true;dismissKeyboard();setChatAnswering(true);const loading={role:'assistant',loading:true,chatLoading:true,status:'LocalAiVision vous répond'};c.messages.push(loading);c.updatedAt=new Date().toISOString();save();const loadingEl=renderMessage(loading);scrollBottom();let live=null,liveEl=null,answer='';activeChatController=new AbortController();activeChatConversationId=id;activeChatStopRequested=false;
 try{const r=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages,settings}),signal:activeChatController.signal});if(!r.ok)throw new Error('Erreur du moteur local ('+r.status+')');if(!r.body)throw new Error('Le navigateur ne permet pas l’affichage progressif.');const reader=r.body.getReader(),decoder=new TextDecoder();let buffer='',remoteError=null;const consume=line=>{if(!line.trim())return;let d;try{d=JSON.parse(line)}catch{return}if(d.error){remoteError=d.error;return}if(!d.delta)return;answer+=d.delta;if(!live){live={role:'assistant',text:answer,streaming:true};c.messages.push(live);if(id===activeConversationId)liveEl=renderMessage(live)}else{live.text=answer;const bubble=liveEl?.querySelector('.bubble');if(bubble)bubble.textContent=answer}if(id===activeConversationId)scrollBottom()};while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});let pos;while((pos=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,pos));buffer=buffer.slice(pos+1)}if(done)break}if(buffer.trim())consume(buffer);if(remoteError)throw new Error(remoteError);if(!answer.trim())throw new Error('Le modèle local n’a renvoyé aucun texte.');if(live){live.streaming=false;const bubble=liveEl?.querySelector('.bubble');if(bubble){bubble.classList.remove('streaming');renderAssistantText(bubble,answer)}}loadingEl?.remove();c.messages=c.messages.filter(m=>m!==loading);c.updatedAt=new Date().toISOString();save()}
 catch(e){loadingEl?.remove();c.messages=c.messages.filter(m=>m!==loading);const stopped=activeChatStopRequested&&(e?.name==='AbortError'||String(e?.message||'').toLowerCase().includes('abort'));if(live&&answer){live.streaming=false;live.text=answer;const bubble=liveEl?.querySelector('.bubble');if(bubble){bubble.classList.remove('streaming');renderAssistantText(bubble,live.text)}save()}else{c.updatedAt=new Date().toISOString();save();if(!stopped)addMessage(id,{role:'assistant',error:true,text:'IA locale indisponible : '+e.message})}if(!stopped)toast(e.message)}
 finally{if(activeChatConversationId===id){activeChatController=null;activeChatConversationId=null;activeChatStopRequested=false}setChatAnswering(false);$('#send').disabled=false}
}
async function startGeneration(task,model,promptText,previewStyle=null){
 const id=activeConversationId,c=conversationFor(id);c.messages.push({role:'assistant',loading:true,mediaType:task});c.updatedAt=new Date().toISOString();save();if(id===activeConversationId){renderMessage(c.messages[c.messages.length-1]);scrollBottom()}$('#send').disabled=true;
 try{const useReference=model.id===bestWorkflowId(ISOLATED_I2V_WORKFLOW)&&!!imageData;const settings=readGenerationSettings(task);settings.loras=c.profile==='nsfw'?selectedLoras:[];const d=await api('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({workflow:model.id,prompt:promptText,negative:$('#settingNegative').value,image:useReference?imageData:null,image_name:useReference?imageName:null,video:null,video_name:null,mask:null,settings})});if(d.warnings?.length)addMessage(id,{role:'assistant',text:d.warnings.join('\n')});await waitResults(d.prompt_ids||[d.prompt_id].filter(Boolean),id,model,promptText,task,previewStyle)}catch(e){removeLoading(id);addMessage(id,{role:'assistant',error:true,text:'Erreur de génération : '+e.message});toast(e.message)}finally{$('#send').disabled=false}
}
function outputFiles(h){const files=[];for(const o of Object.values(h.outputs||{}))for(const key of ['videos','gifs','images'])for(const file of o[key]||[]){if(file?.filename&&!files.some(x=>x.filename===file.filename&&x.subfolder===file.subfolder))files.push(file)}return files}
async function waitResults(pids,id,model,promptText,task,previewStyle=null){const pending=new Set(pids.filter(Boolean)),missing=new Map();let failures=0;if(!pending.size)throw new Error('Le moteur n’a pas accepté la génération.');while(pending.size){await new Promise(r=>setTimeout(r,1000));for(const pid of [...pending]){let d;try{d=await api('/api/history/'+encodeURIComponent(pid));failures=0}catch(e){if(++failures>=5)throw new Error('Connexion au moteur interrompue. La tâche peut continuer dans ComfyUI. '+e.message);continue}const h=d[pid];if(!h){if(d._missing){missing.set(pid,(missing.get(pid)||0)+1);if(missing.get(pid)>=3){pending.delete(pid);addMessage(id,{role:'assistant',error:true,text:'La tâche a disparu de ComfyUI. Tu peux renvoyer ta demande.'})}}else missing.delete(pid);continue}if(['error','failed'].includes(h.status?.status_str)){const details=(h.status.messages||[]).find(x=>x[0]==='execution_error')?.[1];pending.delete(pid);addMessage(id,{role:'assistant',error:true,text:'Échec de génération : '+(details?.exception_message||'Consulte le journal ComfyUI.')});continue}const files=outputFiles(h);if(!h.status?.completed&&!files.length)continue;pending.delete(pid);if(!files.length){addMessage(id,{role:'assistant',error:true,text:'La tâche est terminée sans fichier de sortie.'});continue}for(const file of files){addMessage(id,{role:'assistant',result:file});addLibrary(file,resultKindForModel(model),promptText,conversationFor(id).profile||'auto');if(previewStyle){stylePreviews[previewStyle]={...file,workflow:model.id};localStorage.setItem('lva_style_previews',JSON.stringify(stylePreviews));renderStyles()}}}}removeLoading(id)}

function showSidebar(){$('#sidebar').classList.remove('closed')}
function hideSidebar(){$('#sidebar').classList.add('closed')}
let pollingHealth=false,lastSetupState=null,healthFailures=0;
async function pollHealth(){if(pollingHealth)return;pollingHealth=true;try{
 const comfyBefore=comfyReady,h=await api('/api/health');healthFailures=0;lastHealth=h;comfyReady=!!h.online;llmReady=!!h.llm?.online;
 if(h.online&&!comfyBefore||(h.startup?.state==='ready'&&lastSetupState==='running')){const listing=await api('/api/workflows');workflows=listing.workflows;syncModelSelectors();if(styleCatalog.length)renderStyles()}
 lastSetupState=h.startup?.state;
 const isolatedReady=h.media?.['isolated-image']?.ready&&h.media?.['isolated-video']?.ready;
 const mediaText=h.online?' · photo '+(h.media?.image?.ready?'prête':'à préparer')+' · vidéo '+(h.media?.video?.ready?'prête':'à préparer')+' · Hunyuan '+(isolatedReady?'prêt':'à préparer'):'';
 const text=h.startup?.state==='running'?(h.startup.message||'Préparation…'):h.startup?.state==='error'?'Installation à reprendre':h.online?('Moteurs connectés'+mediaText):'Moteur image / vidéo arrêté';
 $('#statusText').textContent=text;$('.status').className='status '+(h.online||llmReady?'ok':'bad');$('#engineSummary').textContent=text;
 $('#engineDetail').textContent=h.startup?.error||'Configuration : RealVisXL/Wan en standard ; HunyuanImage 2.1 et HY-OmniWeaving T2V/I2V dans l’espace isolé.';
 $('#installImage').textContent=h.media?.image?.ready?'RealVisXL installé ✓':'Installer / reprendre RealVisXL';
 $('#installVideo').textContent=h.media?.video?.ready?'Wan vidéo installé ✓':'Installer Wan 2.1';
 $('#installIsolatedImage').textContent=h.media?.['isolated-image']?.ready?'HunyuanImage 2.1 installé ✓':'Installer HunyuanImage 2.1';
 $('#installMotion').textContent=h.media?.['isolated-video']?.ready?'HY-OmniWeaving T2V installé ✓':'Installer HY-OmniWeaving T2V';
 $('#installI2V').textContent=h.media?.['isolated-video-i2v']?.ready?'HY-OmniWeaving I2V installé ✓':'Installer HY-OmniWeaving I2V';
 for(const id of ['#retrySetup','#installImage','#installVideo','#installIsolatedImage','#installMotion','#installI2V']){const e=$(id);if(e)e.disabled=h.startup?.state==='running'}
 if(h.startup?.state==='error')$('#enginePanel').open=true
}catch(e){
 healthFailures++;
 if(healthFailures>=3){
   $('#engineSummary').textContent='Serveur local injoignable';
   $('#engineDetail').textContent=e.message+' · Ferme les doublons de LocalVisionAI puis relance une seule instance.';
 }
}finally{pollingHealth=false}}
async function installComponent(component){try{const d=await api('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({component})});toast(d.started?'Préparation lancée. Les téléchargements incomplets sont repris automatiquement.':'Une installation est déjà en cours.');await pollHealth()}catch(e){toast(e.message)}}
async function refresh(){await pollHealth();try{const d=await api('/api/workflows');workflows=d.workflows;for(const c of Object.values(conversations)){normalizeConversation(c);if(c.profile&&c.profile!=='auto')applyProfileSettings(c,c.profile)}syncModelSelectors();styleCatalog=await api('/assets/styles.json');renderStyles()}catch(e){toast(e.message)}await refreshLoras();renderProfileLabels();renderConversationList($('#conversationSearch').value);renderLibraryCounts();if(!activeConversationId){const existing=Object.values(conversations).sort((a,b)=>new Date(b.updatedAt)-new Date(a.updatedAt))[0];if(existing)openConversation(existing.id);else createBlankConversation()}}

function setup(){
 $('#openSidebar').onclick=showSidebar;$('#closeSidebar').onclick=hideSidebar;$('#newConversation').onclick=()=>createBlankConversation('auto');$('#closeModal').onclick=closeModelModal;$('#modelModal').addEventListener('click',e=>{if(e.target.id==='modelModal')closeModelModal()});$('#stepValidate').onclick=advanceModelStep;document.querySelectorAll('[data-search]').forEach(input=>input.addEventListener('input',e=>renderOptions(e.target.dataset.search,e.target.value)));$('#conversationSearch').oninput=e=>renderConversationList(e.target.value);$('#send').onclick=sendMessage;$('#prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage()}});$('#prompt').addEventListener('input',e=>{e.target.style.height='auto';e.target.style.height=Math.min(e.target.scrollHeight,220)+'px';styleWorkflowSummary()});const setSettingsOpen=open=>{const panel=$('#generationSettings');panel.classList.toggle('hidden',!open);$('#settingsBtn').classList.toggle('active',!!open);if(open){updateSettingsVisibility();styleWorkflowSummary()}};$('#settingsBtn').onclick=()=>setSettingsOpen($('#generationSettings').classList.contains('hidden'));$('#closeSettings').onclick=()=>setSettingsOpen(false);
 $('#photosLibrary').onclick=()=>renderLibrary('image','Mes photos générées','standard');$('#videosLibrary').onclick=()=>renderLibrary('video','Mes vidéos générées','standard');if($('#nsfwPhotosLibrary'))$('#nsfwPhotosLibrary').onclick=()=>renderLibrary('image','Photos espace isolé','nsfw');if($('#nsfwVideosLibrary'))$('#nsfwVideosLibrary').onclick=()=>renderLibrary('video','Vidéos espace isolé','nsfw');
 $('#modelAuto').onclick=()=>createConversationForProfile('auto');$('#modelRealistic').onclick=()=>createConversationForProfile('companion-realistic');$('#modelNsfw').onclick=()=>createConversationForProfile('nsfw');const nsfwGate=$('#nsfwGate');nsfwGate.checked=loadJSON('lva_nsfw_gate',false);nsfwGate.onchange=()=>{localStorage.setItem('lva_nsfw_gate',JSON.stringify(!!nsfwGate.checked));if(!nsfwGate.checked&&activeConversationId&&conversationFor(activeConversationId).profile==='nsfw'){createBlankConversation('auto');toast('Espace NSFW désactivé.')}updateCreationModeGuide()};document.querySelectorAll('[data-rename-profile]').forEach(btn=>btn.onclick=e=>{e.stopPropagation();renameProfile(btn.dataset.renameProfile)});
 $('#importBtn').onclick=()=>$('#workflowFile').click();$('#workflowFile').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{const wf=JSON.parse(await f.text());await api('/api/import-workflow',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:f.name,workflow:wf})});toast('Workflow ajouté.');await refresh()}catch(err){toast(err.message)}};$('#comfyBtn').onclick=()=>window.open('http://127.0.0.1:8188','_blank');$('#resetStyle').onclick=()=>{graphicStyle='none';localStorage.setItem('lva_graphic_style',JSON.stringify(graphicStyle));renderStyles()};$('#generateStylePreview').onclick=async()=>{if($('#send').disabled||graphicStyle==='none')return;if(!activeConversationId)createBlankConversation();const model=selectedModelForConversation(conversationFor(activeConversationId),'image');if(!model){toast('Aucun workflow image disponible');return}const sample='A tiny cream-colored stone cabin with a red roof next to a turquoise alpine lake, fir trees, mountain peaks and a curved footpath in the foreground.';const selected=graphicStyle;$('#generationSettings').classList.add('hidden');$('#settingsBtn').classList.remove('active');addMessage(activeConversationId,{role:'user',mediaRequest:true,text:'Créer un aperçu local du style '+styleCatalog.find(s=>s.id===selected)?.name});await startGeneration('image',model,sample,selected);renderStyles()};$('#taskMode').addEventListener('change',()=>{styleWorkflowSummary();updateCreationModeGuide()});$('#retrySetup').onclick=()=>installComponent('engines');$('#installImage').onclick=()=>installComponent('image');$('#installVideo').onclick=()=>installComponent('video');$('#installIsolatedImage').onclick=()=>installComponent('isolated-image');$('#installMotion').onclick=()=>installComponent('isolated-video');$('#installI2V').onclick=()=>installComponent('isolated-video-i2v');$('#isolatedModeImage').onclick=()=>chooseIsolatedCreationMode('image');$('#isolatedModeT2V').onclick=()=>chooseIsolatedCreationMode('t2v');$('#isolatedModeI2V').onclick=()=>chooseIsolatedCreationMode('i2v');$('#attachReferenceImageBtn').onclick=()=>$('#referenceImageInput').click();$('#referenceImageInput').onchange=e=>loadReferenceImage(e.target.files?.[0]);$('#clearReferenceImage').onclick=clearReferenceImage;$('#refreshLoras').onclick=refreshLoras;$('#loraSearch').oninput=e=>renderLoraCatalog(e.target.value);$('#showLog').onclick=async()=>{try{const d=await api('/api/logs');$('#logOutput').textContent=d.text;$('#logOutput').classList.toggle('hidden')}catch(e){toast(e.message)}};$('#renameModelBtn').onclick=()=>{const id=$('#renameModelSelect').value,w=workflowById(id);if(w)renameModel(id,displayModelName(w))};
 const savedSettings=loadJSON('lva_settings_v1',{});if(!Object.hasOwn(savedSettings,'settingSystem')||savedSettings.settingSystem===LEGACY_CHAT_SYSTEM){savedSettings.settingSystem=DEFAULT_CHAT_SYSTEM;localStorage.setItem('lva_settings_v1',JSON.stringify(savedSettings))}if(!localStorage.getItem('lva_chat_tokens_v14')&&(!Object.hasOwn(savedSettings,'settingMaxTokens')||Number(savedSettings.settingMaxTokens)<=1024)){savedSettings.settingMaxTokens='2048';localStorage.setItem('lva_chat_tokens_v14','1')}
 document.querySelectorAll('[id^="setting"],#taskMode').forEach(el=>{if(!['INPUT','SELECT','TEXTAREA'].includes(el.tagName)||el.id.endsWith('Model')||el.id==='settingsBtn')return;if(Object.hasOwn(savedSettings,el.id)){if(el.type==='checkbox')el.checked=!!savedSettings[el.id];else el.value=savedSettings[el.id]}el.addEventListener('change',()=>{savedSettings[el.id]=el.type==='checkbox'?el.checked:el.value;localStorage.setItem('lva_settings_v1',JSON.stringify(savedSettings))})});
 // v2.1: remove the old reserved red theme and clear a stale style once so a
 // previous watercolor preset cannot silently alter a new prompt.
 document.body.classList.remove('reserved-theme');localStorage.removeItem('lva_reserved_profile');if(!localStorage.getItem('lva_v21_prompt_fidelity')){graphicStyle='none';localStorage.setItem('lva_graphic_style',JSON.stringify(graphicStyle));localStorage.setItem('lva_v21_prompt_fidelity','1')}
 for(const c of Object.values(conversations)){normalizeConversation(c);c.messages=c.messages.filter(m=>!m.loading)}save();refresh();setInterval(pollHealth,6000);
}
setup();
