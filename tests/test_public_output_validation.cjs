const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function validator(mode='good'){
 const nodes=[];
 const document={createElement:kind=>{
  const listeners=new Map();
  const node={naturalWidth:16,naturalHeight:8,videoWidth:32,videoHeight:24,duration:1.5,readyState:2,cleaned:false,
   addEventListener:(name,fn)=>listeners.set(name,fn),removeEventListener:name=>listeners.delete(name),
   pause:()=>{},load:()=>{},removeAttribute:()=>{},remove(){this.cleaned=true},decode:async()=>{if(mode==='decode-error')throw Error('broken')},
   set src(value){this.url=value;if(mode==='hang')return;queueMicrotask(()=>{if(mode==='invalid-duration')this.duration=NaN;if(mode==='empty')this.naturalWidth=0;listeners.get(mode==='error'?'error':kind==='video'?'loadeddata':'load')?.()})}
  };nodes.push(node);return node;
 }};
 const ctx={window:{},document,location:{href:'http://127.0.0.1:3000/localaivision',origin:'http://127.0.0.1:3000'},URL,setTimeout,clearTimeout,Date};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('local_app/web/studio-media-validation.js','utf8'),ctx);
 return {verify:ctx.window.StudioMediaValidation.verify,nodes};
}
test('public image is decoded and the probe is released',async()=>{const v=validator();const r=await v.verify('/api/view?filename=test.png','image');assert.equal(r.verified,true);assert.equal(r.scope,'browser_image_decode');assert.equal(r.width,16);assert.equal(v.nodes[0].cleaned,true);assert.match(v.nodes[0].url,/validation=/)});
test('video receipt covers first frame and metadata, never all frames or artistic quality',async()=>{const v=validator();const r=await v.verify('/api/view?filename=test.mp4','video');assert.equal(r.duration_seconds,1.5);assert.equal(r.scope,'browser_first_frame_and_metadata');assert.equal(r.full_video_decode,false);assert.equal(r.visual_quality,'not_reviewed');assert.equal(v.nodes[0].cleaned,true)});
for(const mode of ['error','decode-error','empty'])test('unreadable image is refused: '+mode,async()=>{const v=validator(mode);await assert.rejects(v.verify('/api/view?filename=test.png','image'));assert.equal(v.nodes[0].cleaned,true)});
test('invalid video duration cannot be accepted',async()=>{const v=validator('invalid-duration');await assert.rejects(v.verify('/api/view?filename=test.mp4','video'));assert.equal(v.nodes[0].cleaned,true)});
test('timeout remains recoverable and releases the probe',async()=>{const v=validator('hang');await assert.rejects(v.verify('/api/view?filename=test.png','image',{timeoutMs:1}),/revérifier/);assert.equal(v.nodes[0].cleaned,true)});
test('foreign output URLs are rejected before loading a resource',async()=>{const v=validator();await assert.rejects(v.verify('https://example.com/output.png','image'),/invalide/);assert.equal(v.nodes.length,0)});

const source=fs.readFileSync('local_app/web/app.js','utf8');
function appContext(){
 const messages=[],library=[],conversation={profile:'auto',messages};let submissions=0,valid=false;
 const ctx={window:{StudioMediaValidation:{verify:async()=>{if(!valid)throw Error('fixture unreadable');return {verified:true,scope:'browser_image_decode'}}}},
  resultUrl:f=>'/api/view?filename='+f.filename,addMessage:(_id,m)=>messages.push(m),conversationFor:()=>conversation,
  resultKindForModel:()=> 'image',library,addLibrary:f=>library.push(f),save:()=>{},openConversation:()=>{},activeConversationId:'other',
  setTimeout:fn=>fn(),removeLoading:()=>{},clearIrrelevantChatWarningsAfterMedia:()=>{},
  api:async(url)=>{assert.ok(url.startsWith('/api/history/'));submissions++;return {'job':{status:{completed:true},outputs:{out:{images:[{filename:'fixture.png'}]}}}}}
 };
 vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('const publicOutputChecks='),source.indexOf('\nwindow.onStudioAdvert=')),ctx);
 return {ctx,messages,library,setValid:()=>{valid=true},submissions:()=>submissions};
}
test('invalid engine output is retained for retry and never added as a successful result',async()=>{const a=appContext();await a.ctx.waitResults(['job'],'conv',{id:'fixture',kind:'image'},'original prompt','image');assert.equal(a.library.length,0);assert.equal(a.messages.filter(m=>m.result).length,0);assert.equal(a.messages[0].unverifiedOutput.file.filename,'fixture.png');assert.equal(a.messages[0].unverifiedOutput.prompt,'original prompt');assert.equal(a.messages[0].unverifiedOutput.file.technical_validation.verified,false)});
test('retry validates the same output without another engine submission or duplicate',async()=>{const a=appContext();await a.ctx.waitResults(['job'],'conv',{id:'fixture',kind:'image'},'original prompt','image');a.setValid();await a.ctx.retryPublicOutput('conv',a.messages[0]);assert.equal(a.library.length,1);assert.equal(a.messages[0].result.filename,'fixture.png');assert.equal(a.messages[0].result.technical_validation.verified,true);assert.equal(a.messages[0].unverifiedOutput,undefined);await a.ctx.retryPublicOutput('conv',a.messages[0]);assert.equal(a.library.length,1);assert.equal(a.submissions(),1)});
test('private output routing bypasses the new public decoder gate',async()=>{const a=appContext();a.ctx.conversationFor=()=>({profile:'nsfw'});await a.ctx.waitResults(['job'],'conv',{id:'fixture',kind:'image'},'private prompt','image');assert.equal(a.library.length,1);assert.equal(a.messages[0].result.filename,'fixture.png')});
