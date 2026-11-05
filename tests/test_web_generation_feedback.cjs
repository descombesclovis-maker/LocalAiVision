const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('local_app/web/localaiweb.js','utf8');
function context(){
 const elements={};
 for(const name of ['lawEditPhase','lawEditPercent','lawEditTrack'])elements['#'+name]={textContent:'',parentElement:{hidden:false},style:{}};
 const ctx=vm.createContext({window:{StudioProgress:{render:()=>{}}},editOverlay:{hidden:true,querySelector:()=>null},$:name=>elements[name]});
 vm.runInContext(source.slice(source.indexOf('function showSiteEditing('),source.indexOf('function codexRecovery(')),ctx);
 return {ctx,elements};
}
test('Web generation displays actual phases without fabricated percentages',()=>{
 const {ctx,elements}=context();
 ctx.showSiteEditing(true);
 for(const phase of ['planning','verification','repair','preview','visual','design','unknown','done']){
  ctx.updateEditMilestones({phase,detail:'État moteur réel'});
  assert.equal(elements['#lawEditPhase'].textContent,'État moteur réel');
  assert.ok(!elements['#lawEditPercent'].textContent.includes('%'));
  assert.equal(elements['#lawEditTrack'].parentElement.hidden,true);
 }
 assert.equal(elements['#lawEditPercent'].textContent,'Étape en cours : terminée');
});
test('Hidden edit feedback is left unchanged and engine detail is bounded',()=>{
 const {ctx,elements}=context();
 ctx.updateEditMilestones({phase:'design',detail:'hidden'});
 assert.equal(elements['#lawEditPhase'].textContent,'');
 ctx.showSiteEditing(true);
 ctx.updateEditMilestones({phase:'repair',detail:'x'.repeat(1000)});
 assert.equal(elements['#lawEditPhase'].textContent.length,150);
 ctx.showSiteEditing(false);
 assert.equal(ctx.editOverlay.hidden,true);
});
test('Generation feedback contains readable line breaks and preserves its summary',()=>{
 const messages=[];
 const ctx=vm.createContext({message:(...args)=>messages.push(args)});
 vm.runInContext(source.slice(source.indexOf('function generationFeedback('),source.indexOf('async function watchGeneration(')),ctx);
 ctx.generationFeedback({summary:'Site enregistré',quality:{ok:true},generation_metrics:{total_seconds:62,quality_seconds:2,repairs:1},visuals:{generated:['image']}});
 assert.ok(messages[0][0].startsWith('Site enregistré\nVisuels créés : 1 photo(s).'));
 assert.ok(messages[0][0].includes('\nGénération : 1 min 2 s'));
 assert.ok(!messages[0][0].includes('\\n'));
});

test('Media results wait for engine completion even when an intermediate image already exists',async()=>{
 const source=fs.readFileSync('local_app/web/app.js','utf8');
 const messages=[],library=[];let polls=0;
 const ctx=vm.createContext({
  setTimeout:fn=>{fn()},
  api:async()=>{
   ++polls;
   if(polls===2){assert.equal(messages.length,0);assert.equal(library.length,0)}
   return {'render-id':{status:{completed:polls>=2},outputs:{one:{images:[{filename:'output.png'}]}}}};
  },
  addMessage:(_id,message)=>messages.push(message),
  addLibrary:file=>library.push(file),
  conversationFor:()=>({profile:'auto'}),resultKindForModel:()=> 'image',
  clearIrrelevantChatWarningsAfterMedia:()=>{},removeLoading:()=>{},verifyPublicOutput:async(file,id)=>{messages.push({role:'assistant',result:file});library.push(file);return true},window:{}
 });
 vm.runInContext(source.slice(source.indexOf('function outputFiles('),source.indexOf('\nwindow.onStudioAdvert=')),ctx);
 await ctx.waitResults(['render-id'],'conversation',{},'prompt','image');
 assert.equal(polls,2);assert.equal(library.length,1);assert.equal(messages.length,1);
});
