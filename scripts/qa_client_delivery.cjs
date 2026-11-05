/* Real local HTTP/PDF/ZIP flow using fictional identities. No provider transaction. */
const {chromium}=require('playwright'),{spawn}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),output=path.resolve(process.env.UI_OUTPUT||'build/qa315/client-delivery');fs.mkdirSync(output,{recursive:true});
const data=fs.mkdtempSync(path.join(os.tmpdir(),'studio-delivery-'));
const server=spawn(process.env.PYTHON||'python',['-m','local_app.server'],{cwd:root,env:{...process.env,LOCALVISIONAI_DATA:data,LOCALVISIONAI_SKIP_SETUP:'1',LOCALVISIONAI_DISABLE_AUTO_UPDATE:'1'},stdio:['ignore','pipe','pipe']});
const log=fs.createWriteStream(path.join(output,'server.log'));server.stdout.pipe(log);server.stderr.pipe(log);
const base='http://127.0.0.1:3000',deliveryBase='http://ventes.localhost:3000',wait=ms=>new Promise(r=>setTimeout(r,ms));
const result={checks:[],limitations:['Fictional local identities and manually declared test receipts. No actual bank, Stripe, hosting or database account operation.']};let browser;
async function api(route,body,delivery=false){
 const headers={'Content-Type':'application/json',...(delivery?{'Host':'ventes.localhost:3000','Origin':deliveryBase,'X-LocalAI-Delivery':'1'}:{})};
 if(body)headers['Content-Length']=Buffer.byteLength(JSON.stringify(body));
 // node:http preserves the explicit virtual Host; Node's fetch ignores it.
 return new Promise((resolve,reject)=>{
  const request=require('node:http').request(base+route,{method:body?'POST':'GET',headers},response=>{const chunks=[];response.on('data',x=>chunks.push(x));response.on('end',()=>{try{const d=JSON.parse(Buffer.concat(chunks).toString());if(response.statusCode>=400)reject(Error(d.error||response.statusCode));else resolve(d)}catch(e){reject(e)}})});
  request.on('error',reject);if(body)request.write(JSON.stringify(body));request.end();
 });
}
async function check(name,fn){await fn();result.checks.push({name,passed:true})}
(async()=>{try{
 for(let n=0;n<100;n++){try{await api('/api/web/projects');break}catch(e){if(n===99)throw e;await wait(150)}}
 const project=await api('/api/web/project/create',{name:'ATELIER DÉMO — RECETTE'}),id=project.project.id;
 fs.writeFileSync(path.join(data,'localaiweb','projects',id,'site','index.html'),'<!doctype html><html lang="fr"><title>Site fictif</title><body><h1>Site fictif pour recette</h1></body></html>');
 browser=await chromium.launch({headless:true,...(process.env.UI_BROWSER_CHANNEL?{channel:process.env.UI_BROWSER_CHANNEL}:{}),args:['--no-sandbox']});
 const page=await browser.newPage({reducedMotion:'reduce',serviceWorkers:'block'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await check('Web viewport-wide header, preserved editor and menu on desktop, tablet and mobile',async()=>{
  for(const [name,width,height] of [['desktop',1440,1000],['tablet',820,1180],['mobile',390,844]]){
   await page.setViewportSize({width,height});await page.goto(base+'/localaiweb/editor?id='+id);await page.locator('#qcmEditorSplitter').waitFor({state:'attached'});await wait(500);
   const header=await page.locator('.law-global-header').boundingBox(),logo=await page.locator('.law-global-header .chat-brand').boundingBox(),menu=await page.locator('#lawMobileMenuToggle').boundingBox();
   assert.ok(Math.abs(header.x)<1&&Math.abs(header.width-width)<1,'full width '+name);
   assert.ok(Math.abs(logo.x+logo.width/2-width/2)<1,'centered logo '+name);assert.ok(menu.x<=20,'far-left menu '+name);
   assert.equal(await page.locator('#webStudioReturn').isVisible(),true);assert.equal(await page.locator('#lawPublishBtn').count(),1);assert.equal(await page.locator('#lawPreview').count(),1);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.locator('#lawMobileMenuToggle').click();assert.equal(await page.locator('#connectAgent').isVisible(),true);assert.equal(await page.locator('#lawAgentSelect').isVisible(),true);
   await page.keyboard.press('Escape');assert.equal(await page.locator('#lawMobileTools').isVisible(),false);
   if(width>780){const split=page.locator('#qcmEditorSplitter');await split.focus();await page.keyboard.press('ArrowRight');assert.ok(Number(await split.getAttribute('aria-valuenow'))>32)}
   else{await page.locator('[data-mobile-panel="preview"]').click();assert.equal(await page.locator('.law-global-header').isVisible(),true);await page.locator('[data-mobile-panel="chat"]').click();assert.equal(await page.locator('#lawPrompt').isVisible(),true)}
   await page.screenshot({path:path.join(output,'web-header-'+name+'.png')});
  }
 });
 await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/localaiweb/livraisons?id='+id);await page.waitForURL(deliveryBase+'/localaiweb/livraisons?id='+id);await page.locator('#dossier').waitFor();
 await check('Free quote, accepted declaration, partial then full receipt, immutable invoice',async()=>{
  const values={'seller.name':'Atelier Fictif','seller.siret':'53784237900027','seller.address':'10 rue du Test, Paris','seller.payment_details':'Virement bancaire','seller.late_penalty_rate':'Taux contractuel','customer.name':'Client Démonstration','customer.address':'12 rue des Tests, Lyon','customer.siren':'123456789','service_date':new Date().toLocaleDateString('en-CA',{timeZone:'Europe/Paris'})};
  for(const [name,value] of Object.entries(values))await page.locator('[name="'+name+'"]').fill(value);
  await page.locator('[name="seller.legal_form"]').selectOption('EI');await page.locator('[name="seller.vat_mode"]').selectOption('franchise');await page.locator('[data-field="unit_eur"]').fill('100');
  page.once('dialog',d=>d.accept());await page.locator('#createQuote').click();await page.locator('#documentList a').first().waitFor();
  let d=await api('/api/web/delivery/dossier?id='+id,null,true);assert.ok(d.quote);assert.equal(d.invoice,null);
  const quoteResponse=await page.evaluate(async url=>{const r=await fetch(url);return {status:r.status,data:Array.from(new Uint8Array(await r.arrayBuffer()))}},'/api/web/delivery/document?id='+id+'&number='+d.quote);assert.equal(quoteResponse.status,200);const quote=Buffer.from(quoteResponse.data);assert.ok(quote.subarray(0,5).equals(Buffer.from('%PDF-')));fs.writeFileSync(path.join(output,'Devis-fictif.pdf'),quote);
  await page.locator('[data-tab="payment"]').click();page.once('dialog',x=>x.accept());await page.locator('#acceptQuote').click();await page.waitForFunction(()=>document.querySelector('#acceptQuote').disabled);
  for(const [amount,reference] of [['40','fixture-receipt-1'],['60','fixture-receipt-2']]){
   await page.locator('#paymentAmount').fill(amount);await page.locator('#paymentReference').fill(reference);page.once('dialog',x=>x.accept());await page.locator('#recordPayment').click();await page.waitForFunction(ref=>document.querySelector('#paymentHistory').textContent.includes(ref),reference);
   d=await api('/api/web/delivery/dossier?id='+id,null,true);assert.ok(d.invoice);assert.equal(d.assessment.payment.status,amount==='40'?'partial':'received');
  }
  const invoice=await page.evaluate(async url=>{const r=await fetch(url);return {status:r.status,data:Array.from(new Uint8Array(await r.arrayBuffer()))}},'/api/web/delivery/document?id='+id+'&number='+d.invoice);assert.equal(invoice.status,200);fs.writeFileSync(path.join(output,'Facture-fictive.pdf'),Buffer.from(invoice.data));
 });
 await check('Checklist, package preview, actual ZIP download and persisted dossier',async()=>{
  await page.locator('[data-tab="technical"]').click();for(const name of ['design','pages','functions','rights'])await page.locator('[name="check.'+name+'"]').check();await page.locator('#technicalForm button[type="submit"]').click();await page.waitForFunction(()=>!document.querySelector('#preparePackage').disabled);
  await page.locator('[data-tab="package"]').click();await page.locator('#preparePackage').click();await page.locator('#downloadPackage').waitFor();
  assert.match(await page.locator('#packagePreview').innerText(),/02_Documents\/Facture.pdf/);
  const dl=page.waitForEvent('download');await page.locator('#downloadPackage').click();const file=await dl;await file.saveAs(path.join(output,'Livraison-fictive.zip'));
  page.once('dialog',d=>d.accept());await page.locator('#markDelivered').click();await page.waitForFunction(()=>document.querySelector('#deliverySummary').textContent.includes('Effectuée'));
  await page.reload();await page.locator('#dossier').waitFor();assert.match(await page.locator('#deliverySummary').innerText(),/Effectuée/);
  for(const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
   await page.setViewportSize({width,height});await page.locator('[data-tab="package"]').click();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(output,'delivery-'+name+'.png'),fullPage:true});
  }
 });
 await check('Dedicated delivery origin rejects forged declarations from editor and preview',async()=>{
  const r=await fetch(base+'/api/web/delivery/action',{method:'POST',headers:{'Content-Type':'application/json','X-LocalAI-Delivery':'1'},body:JSON.stringify({id,action:'payment',amount:'100',confirmed:true})});assert.equal(r.status,403);
 });
 assert.deepEqual(errors,[]);
 }catch(e){result.error=e.stack;process.exitCode=1}
 finally{if(browser)await browser.close();server.kill();log.end();fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2))}
})();
