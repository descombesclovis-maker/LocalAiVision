// DOM-free event contract for the existing chat interface; no npm packages.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

class Element{
  constructor(tag='div'){
    this.tagName=tag;this.className='';this.children=[];this.events={};
    this.hidden=false;this.attributes={};this.value='';this.style={};
  }
  appendChild(child){this.children.push(child);return child;}
  append(...children){children.forEach(child=>this.appendChild(child));}
  replaceChildren(...children){this.children=[...children];}
  setAttribute(key,value){this.attributes[key]=value;}
  addEventListener(event,callback){(this.events[event]??=[]).push(callback);}
  querySelectorAll(selector){
    if(selector==='.message.user')return this.children.filter(node=>node.className==='message user');
    if(selector==='.message-actions')return this.children.flatMap(node=>node.children.filter(el=>el.className==='message-actions'));
    return [];
  }
  closest(selector){return selector==='.message-actions'&&this.className==='message-actions'?this:null;}
  focus(){this.focused=true;}
  setSelectionRange(begin,end){this.selection=[begin,end];}
}
function boot(){
  const nodes=Object.fromEntries(['#lawChat','#lawPrompt','#lawGenerate','#lawComposer','#lawChatStatus'].map(key=>[key,new Element(key)]));
  const fakeDocument={
    querySelector:sel=>nodes[sel]??null,
    querySelectorAll:sel=>[],
    createElement:tag=>new Element(tag),
    body:new Element('body'),
  };
  const copied=[];
  const ctx=vm.createContext({
    document:fakeDocument,
    navigator:{clipboard:{writeText:async text=>{copied.push(text);}}},
    window:{location:{search:''}},
    globalThis:null, setInterval, clearInterval,
  });
  ctx.globalThis=ctx;ctx.__resends=[];
  let source=fs.readFileSync(new URL('../local_app/web/localaiweb.js',import.meta.url),'utf8');
  source=source.replace(/\binitialize\(\);\s*$/, ''); // Do not contact a live server during this unit test.
  vm.runInContext(source,ctx,{filename:'localaiweb.js'});
  return {ctx,nodes,copied};
}
function actions(message){
  return message.children.find(child=>child.className==='message-actions');
}
function click(el,target=el){
  for(const cb of el.events.click||[])cb({target,stopPropagation(){}});
}
test('click sent prompts: old messages copy/resend; latest also edit',async()=>{
  const {ctx,nodes,copied}=boot();
  vm.runInContext("message('Ancienne consigne','user'); message('Réponse','assistant'); message('Dernière consigne','user');",ctx);
  const [older,newest]=nodes['#lawChat'].querySelectorAll('.message.user');
  assert.equal(actions(older).hidden,true);
  click(older);
  assert.deepEqual(actions(older).children.map(x=>x.textContent),['Copier','Renvoyer']);
  click(newest);
  assert.equal(actions(older).hidden,true);
  assert.deepEqual(actions(newest).children.map(x=>x.textContent),['Copier','Renvoyer','Modifier']);
  click(actions(older).children[0]);
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(copied,['Ancienne consigne']);
  vm.runInContext("sendText = async (value,options) => { globalThis.__resends.push({value,options}); };",ctx);
  nodes['#lawPrompt'].value='Texte non envoyé';
  click(actions(older).children[1]);
  assert.equal(ctx.__resends.length,1);
  assert.equal(ctx.__resends[0].value,'Ancienne consigne');
  assert.equal(ctx.__resends[0].options.preserveDraft,true);
  assert.equal(nodes['#lawPrompt'].value,'Texte non envoyé');
  click(newest);
  const modify=actions(newest).children.find(x=>x.textContent==='Modifier');
  click(modify);
  assert.equal(nodes['#lawPrompt'].value,'Dernière consigne');
  assert.equal(nodes['#lawPrompt'].focused,true);
  vm.runInContext("message('Consigne encore plus récente','user');",ctx);
  click(newest);
  assert.deepEqual(actions(newest).children.map(x=>x.textContent),['Copier','Renvoyer']);
});
