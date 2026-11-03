/* Isolated preview messages are data only. Editing still requires the user's submit. */
(()=>{
const frame=document.getElementById('lawPreview'),toggle=document.getElementById('lawInspectBtn');
const pop=document.getElementById('lawInspectorPopover'),input=document.getElementById('lawInspectorPrompt');
let active=false,selection=null,channel=crypto.randomUUID();
function configure(){frame.contentWindow?.postMessage({type:'law-inspect',active,channel},'*')}
frame.addEventListener('load',()=>{selection=null;pop.hidden=true;channel=crypto.randomUUID();configure()});
toggle.onclick=()=>{if(!project||busy)return;active=!active;toggle.setAttribute('aria-pressed',String(active));toggle.classList.toggle('active',active);configure()};
addEventListener('message',event=>{
 const d=event.data;
 if(event.source!==frame.contentWindow||event.origin!=='http://preview-'+project?.project?.id+'.localhost:'+location.port||!active||!d||d.type!=='law-selection'||d.channel!==channel||
    !Array.isArray(d.items)||!d.items.length||d.items.length>24||typeof d.page!=='string')return;
 if(d.items.some(x=>!x||typeof x.tag!=='string'||typeof x.selector!=='string'||typeof x.label!=='string'||x.selector.length>1000||x.label.length>130))return;
 selection=d;pop.style.left='12px';pop.style.top='12px';pop.hidden=false;input.focus();
});
document.getElementById('lawInspectorCancel').onclick=()=>{pop.hidden=true;selection=null};
document.getElementById('lawInspectorSubmit').onclick=async()=>{
 if(!selection||busy||!input.value.trim())return;
 const text='MODIFICATION CIBLÉE — '+project.project.name+'\nPage : '+selection.page.slice(0,500)+'\n'+selection.items.map(x=>x.tag+' | '+x.selector+' | '+x.label).join('\n')+'\nDemande : '+input.value.trim();
 selection=null;pop.hidden=true;active=false;configure();await sendText(text);
};
document.getElementById('lawBrowserBtn').onclick=()=>{if(project)window.open('/web-preview/'+project.project.id+'/index.html','_blank','noopener,noreferrer')};
document.getElementById('lawZipBtn').onclick=()=>exportSite();
setInterval(async()=>{if(!project)return;try{const s=await api('/api/web/preview/status?id='+project.project.id);document.getElementById('lawSiteTools').hidden=!s.ready}catch{}},2400);
})();
