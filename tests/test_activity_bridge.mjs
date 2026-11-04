import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../local_app/web/studio-activity.js',import.meta.url),'utf8');

async function editor(page='editor',src='/web-preview/web-012345abcdef/index.html') {
  class Element {
    constructor(){this.dataset={};this.classList={toggle(){}}}
    addEventListener(){} querySelector(){return new Element()}
    setAttribute(){} replaceChildren(){} append(){}
  }
  const messages=[],frame=new Element();
  frame.getAttribute=()=>src;
  frame.contentWindow={postMessage:(data,origin)=>messages.push({data:JSON.parse(JSON.stringify(data)),origin})};
  const document={body:new Element(),hidden:false,createElement:()=>new Element(),
    addEventListener(){},querySelector:()=>frame,getElementById:()=>frame};
  document.body.dataset.studioPage=page;
  let media={count:2,running:0,queued:2,preparing:0};
  const context={document,URL,AbortController,setTimeout:()=>0,clearTimeout(){},
    location:{href:'http://127.0.0.1:3000/localaiweb/editor',origin:'http://127.0.0.1:3000'},
    fetch:async()=>({ok:true,json:async()=>({jobs:[],media:{...media}})})};
  context.window={setInterval(){},addEventListener(){}};
  vm.runInNewContext(source,context);
  await new Promise(setImmediate);
  return {messages,async update(next){media=next;await context.window.StudioActivity.refresh()}};
}

test('editor delivers queue, active, preparation and idle states to its exact isolated preview origin',async()=>{
  const bridge=await editor();
  await bridge.update({count:1,running:1,queued:0,preparing:0});
  await bridge.update({count:1,running:0,queued:0,preparing:1});
  await bridge.update({count:0,running:0,queued:0,preparing:0});
  assert.deepEqual(bridge.messages.map(m=>m.data.mediaBusy),[false,true,true,false]);
  assert.ok(bridge.messages.every(m=>m.origin==='http://preview-web-012345abcdef.localhost:3000'));
});

test('Vision, reserved surfaces and unrelated iframe destinations receive no preview budget',async()=>{
  for(const page of ['vision','nsfw','projects'])assert.deepEqual((await editor(page)).messages,[]);
  for(const src of ['https://example.com/web-preview/web-012345abcdef/index.html','/web-preview/invalid/index.html',''])
    assert.deepEqual((await editor('editor',src)).messages,[]);
});
