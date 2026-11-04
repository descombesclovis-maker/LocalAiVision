const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('local_app/web/app.js','utf8');
const start=source.indexOf('function publicPhotoFaithfulness(');
const end=source.indexOf('\nasync function startGeneration',start);
const ctx=vm.createContext({});vm.runInContext(source.slice(start,end),ctx);
for(const prompt of ['Un chien seul dans un jardin','Un chien dans un jardin, sans personne','Un chien sans mains humaines','Un chien sans aucune personne','A dog without human hands','A cat, no people','Un chien, ni personne ni mains']){
 test(prompt,()=>{const out=ctx.publicPhotoFaithfulness(prompt,'blur','image','auto');assert.equal(out.exactPrompt,true);assert.ok(out.prompt.startsWith(prompt));assert.ok(out.negative.startsWith('blur'));});
}
for(const prompt of ['Un chien avec une femme','Un chien sans mains, mais avec une personne','A dog and a woman','Un homme et son chien','Un portrait de femme']){
 test('positive subject: '+prompt,()=>{const out=ctx.publicPhotoFaithfulness(prompt,'blur','image','auto');assert.equal(out.prompt,prompt);assert.equal(out.exactPrompt,false);});
}
test('private and video requests are unchanged',()=>{
 for(const [task,profile] of [['image','nsfw'],['video','auto'],['video','nsfw']]){
  const out=ctx.publicPhotoFaithfulness('Un chien sans personne','original negative',task,profile);
  assert.equal(out.prompt,'Un chien sans personne');assert.equal(out.negative,'original negative');assert.equal(out.exactPrompt,false);
 }
});
