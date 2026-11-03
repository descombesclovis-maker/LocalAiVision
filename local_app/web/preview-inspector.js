(()=>{
let active=false,selected=[],attached=null,start=null,channel='',parentOrigin='';
let previousTouch={time:0,target:null};
const q='h1,h2,h3,h4,p,a,button,img,video,input,textarea,select,label,li,article,section,[role="button"],div';
 function allowed(el){
  if(!el||el.nodeType!==1||['HTML','BODY','SCRIPT','STYLE'].includes(el.tagName))return false;
  if(el.closest('[data-law-selection]'))return false;
  if(['DIV','SECTION'].includes(el.tagName)&&el.querySelector('h1,h2,h3,p,a,button,img,section,article'))return false;
  const r=el.getBoundingClientRect();if(r.width<9||r.height<7)return false;
  const c=el.ownerDocument.defaultView.getComputedStyle(el);
  return c.visibility!=='hidden'&&c.display!=='none'&&Number(c.opacity)>0;
 }
 function candidate(el){for(let n=el;n;n=n.parentElement)if(allowed(n))return n;return null}
 function clear(){for(const el of selected)try{el.classList.remove('law-picked')}catch{};selected=[];}
 function choose(elements,append=false){
  if(!append)clear();
  for(const el of elements){if(allowed(el)&&!selected.includes(el)&&selected.length<24){selected.push(el);el.classList.add('law-picked')}}
  if(selected.length&&active)void 0;
 }
 function cssPath(el){
  const steps=[];for(let e=el;e&&e.tagName&&!['HTML','BODY'].includes(e.tagName)&&steps.length<10;e=e.parentElement){
   if(e.id && e.id.length<80){steps.unshift('#'+CSS.escape(e.id));break}
   const siblings=e.parentElement?Array.from(e.parentElement.children).filter(n=>n.tagName===e.tagName):[e];
   steps.unshift(e.tagName.toLowerCase()+(siblings.length>1?':nth-of-type('+(siblings.indexOf(e)+1)+')':''));
  }return steps.join(' > ');
 }
 function editAt(x,y){
  if(!active||!selected.length)return;
  parent.postMessage({type:'law-selection',channel,page:location.pathname,
   items:selected.map(el=>({tag:el.tagName.toLowerCase(),selector:cssPath(el),
     label:String(el.innerText||el.alt||'').replace(/\s+/g,' ').slice(0,130)})),x,y},parentOrigin);
 }
 function attach(d){
  if(!d||attached===d)return;
  clear();attached=d;
  const style=d.createElement('style');style.id='law-selector-css';
  style.textContent='html.law-select,html.law-select *{cursor:crosshair!important}.law-picked{outline:2px dashed #9967f9!important;outline-offset:2px!important}.law-drag{position:fixed;z-index:2147483646;pointer-events:none;border:2px dashed #8355e9;background:#8355e926;border-radius:3px}';
  (d.head||d.documentElement).append(style);
  const box=d.createElement('div');box.className='law-drag';box.dataset.lawSelection='1';box.hidden=true;box.style.display='none';d.body.append(box);
  d.documentElement.classList.toggle('law-select',active);
  d.addEventListener('pointerdown',ev=>{
   if(!active||ev.button!==0)return;start={x:ev.clientX,y:ev.clientY,shift:ev.shiftKey,drag:false};
   ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('pointermove',ev=>{
   if(!active||!start)return;
   if(Math.hypot(ev.clientX-start.x,ev.clientY-start.y)<7)return;
   start.drag=true;box.style.display='block';
   box.style.left=Math.min(ev.clientX,start.x)+'px';box.style.top=Math.min(ev.clientY,start.y)+'px';
   box.style.width=Math.abs(ev.clientX-start.x)+'px';box.style.height=Math.abs(ev.clientY-start.y)+'px';
   ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('pointerup',ev=>{
   if(!active||!start)return;
   const first=start;start=null;box.style.display='none';
   if(first.drag){
    const x1=Math.min(first.x,ev.clientX),x2=Math.max(first.x,ev.clientX);
    const y1=Math.min(first.y,ev.clientY),y2=Math.max(first.y,ev.clientY);
    const hits=Array.from(d.querySelectorAll(q)).filter(el=>{
     if(!allowed(el))return false;const r=el.getBoundingClientRect();
     return r.left<x2&&r.right>x1&&r.top<y2&&r.bottom>y1;
    }).slice(0,24);
    choose(hits,first.shift);
    if(selected.length)editAt(ev.clientX,ev.clientY);
   }else{
    const item=candidate(ev.target);
    const now=Date.now();
    const doubleTap=ev.pointerType==='touch'&&item&&
      previousTouch.target===item&&now-previousTouch.time<550;
    if(item)choose([item],first.shift);else if(!first.shift)clear();
    // One click is enough. Opening the text area synchronously with the
    // pointer event also lets touch keyboards appear on supported devices.
    if(item)editAt(ev.clientX,ev.clientY);
    previousTouch={time:now,target:item};
   }
   ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('click',ev=>{
   if(!active)return;
   if(ev.detail>=2)editAt(ev.clientX,ev.clientY);
   ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('dblclick',ev=>{
   if(!active)return;
   if(!selected.length){const el=candidate(ev.target);if(el)choose([el])}
   editAt(ev.clientX,ev.clientY);ev.preventDefault();ev.stopImmediatePropagation();
  },true);
  d.addEventListener('dragstart',ev=>{if(active){ev.preventDefault();ev.stopImmediatePropagation()}},true);
  d.addEventListener('keydown',ev=>{if(active&&ev.key==='Escape'){active=false;clear();ev.preventDefault()}},true);
 }

addEventListener('message',event=>{
 if(event.source!==parent||!event.data||event.data.type!=='law-inspect'||typeof event.data.channel!=='string')return;
 const origin=new URL(event.origin);
 if(!['127.0.0.1','localhost'].includes(origin.hostname))return;
 channel=event.data.channel;parentOrigin=event.origin;active=event.data.active===true;
 attach(document);document.documentElement.classList.toggle('law-select',active);
 if(!active)clear();
});
})();
