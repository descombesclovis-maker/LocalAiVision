// Canvas regression with the actual frontend code (no browser layout assumed).
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const base=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
const {createCanvas,Image}=require(base?base+'/@napi-rs/canvas':'@napi-rs/canvas');
const main=createCanvas(256,256);main.getBoundingClientRect=()=>({left:0,top:0,width:256,height:256});main.setPointerCapture=()=>{};
const controls=new Map([['#maskCanvas',main]]);
function el(id){if(!controls.has(id))controls.set(id,{value:'20',textContent:'',classList:{add(){},remove(){}}});return controls.get(id)}
const context=vm.createContext({document:{querySelector:el,createElement:()=>createCanvas(1,1)},Image,console,toast(){},imageData:{data:'test'},maskPainted:false});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../local_app/web/mask.js'),'utf8'),context);
vm.runInContext('setupMaskEditor()',context);
main.onpointerdown({clientX:80,clientY:80,pointerId:1,preventDefault(){}});main.onpointermove({clientX:150,clientY:150});main.onpointerup();
const data=vm.runInContext('exportMask()',context);
const img=new Image();img.onload=()=>{
 const canvas=createCanvas(256,256),ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);
 assert.deepEqual([...ctx.getImageData(0,0,1,1).data],[0,0,0,255]);
 assert.deepEqual([...ctx.getImageData(110,110,1,1).data],[255,255,255,255]);
 el('#undoMask').onclick();assert.equal(vm.runInContext('exportMask()',context),null);
 main.onpointerdown({clientX:80,clientY:80,pointerId:1,preventDefault(){}});main.onpointerup();el('#clearMask').onclick();assert.equal(vm.runInContext('exportMask()',context),null);
 console.log('4 vérifications canvas réussies : zone noire, zone blanche, annulation, effacement.');
};img.onerror=e=>{throw e};img.src=Buffer.from(data.split(',')[1],'base64');
