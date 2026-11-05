const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx={window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('local_app/web/studio-progress.js','utf8'),ctx);
const state=ctx.window.StudioProgress.state;
test('sampler 100 is never a completed output',()=>{assert.equal(state({percent:100,state:'running'}).percent,99);assert.equal(state({percent:100,state:'running'}).complete,false)});
test('null progress stays unknown',()=>{assert.equal(state({percent:null}).percent,null);assert.equal(state({}).estimated,false)});
test('web phases are estimates',()=>{const s=state({phase:'building'},true);assert.equal(s.estimated,true);assert.ok(s.percent>0&&s.percent<100)});
test('only an explicitly verified output reaches 100',()=>{assert.equal(state({state:'done',percent:100}).percent,99);assert.equal(state({state:'done',output_verified:true}).percent,100)});
