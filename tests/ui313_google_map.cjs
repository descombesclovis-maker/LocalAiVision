/* Deterministic adapter tests. Synthetic IDs never appear in product data or
   screenshots. No network call, key, billing activation or Google DOM access. */
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const callbacks={},widgetEvents={},docEvents={},pending=[];
const request={place:null,removeAttribute(){this.place=null}};
const widget={querySelector(){return request},addEventListener(name,fn){widgetEvents[name]=fn}};
const panel={hidden:true};
const elements={mapSelection:panel,googlePlaceDetails:widget,businessMap:{},mapClose:{addEventListener(name,fn){callbacks.close=fn}}};
const selections=[],statuses=[];
let mapCallback;
const window={dispatchEvent(){}};
const context={window,Event:class{},URLSearchParams,setTimeout,clearTimeout,customElements:{get(){return true}},
 document:{getElementById(id){return elements[id]},addEventListener(name,fn){docEvents[name]=fn}},
 google:{maps:{importLibrary:async()=>{},Map:class{constructor(element,options){assert.equal(options.center.lat,46.60);assert.equal(options.zoom,6)}addListener(name,fn){mapCallback=fn}setCenter(){}setZoom(){}}}};
window.google=context.google;
vm.runInNewContext(fs.readFileSync('local_app/web/localaiweb-google-map.js','utf8'),context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const api=url=>new Promise(resolve=>pending.push({id:new URLSearchParams(url.split('?')[1]).get('place_id'),resolve}));
const select=placeId=>mapCallback({placeId,stop(){}});
const result=(id,token)=>({business:{google_place_id:id,selection_token:token,name:'Synthetic test fixture'}});
(async()=>{
 const adapter=window.LocalAiWebGoogleMap;
 assert.equal(await adapter.start({},()=>{},()=>{},api),false);
 await adapter.start({enabled:true,browser_key:'test-only',places_enabled:true},x=>selections.push(x),(x,e)=>statuses.push({x,e}),api);
 select('PLACE_A');select('PLACE_B');
 assert.equal(selections.at(-1),null);assert.equal(request.place,'PLACE_B');
 pending[1].resolve(result('PLACE_B','token-b'));await tick();assert.equal(selections.at(-1).selection_token,'token-b');
 pending[0].resolve(result('PLACE_A','token-a'));await tick();assert.equal(selections.at(-1).selection_token,'token-b');
 select('PLACE_C');callbacks.close();pending[2].resolve(result('PLACE_C','token-c'));await tick();
 assert.equal(panel.hidden,true);assert.equal(selections.at(-1),null);
 select('PLACE_D');pending[3].resolve(result('WRONG_PLACE','wrong-token'));await tick();
 assert.equal(selections.at(-1),null);assert.equal(statuses.at(-1).e,true);
 select('PLACE_E');widgetEvents['gmp-error']();pending[4].resolve(result('PLACE_E','token-e'));await tick();
 assert.equal(selections.at(-1),null);assert.equal(statuses.at(-1).e,true);
 console.log('PASS: stale responses, close, wrong place and widget errors cannot enable the wrong project action.');
})().catch(error=>{console.error(error);process.exitCode=1});
