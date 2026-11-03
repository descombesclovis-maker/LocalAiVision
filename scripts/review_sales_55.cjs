const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright-core');
const out=process.env.QA_OUTPUT||'docs/qa55';
const base=process.env.SALES_TEST_URL;
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch(process.env.CHROME_PATH?
  {executablePath:process.env.CHROME_PATH,args:['--no-sandbox','--disable-gpu']}:{channel:'msedge'});
 const p=await browser.newPage({viewport:{width:1365,height:768},serviceWorkers:'block',
  ...(process.env.SALES_VIDEO?{recordVideo:{dir:process.env.SALES_VIDEO,size:{width:960,height:540}}}:{})});
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 try{
  const post=async(url,data)=>{
   const r=await p.request.post(base+url,{data});assert.ok(r.ok(),await r.text());return r.json();
  };
  const pro=(await post('/api/web/project/create-from-map',{selection_token:process.env.TEST_SELECTION})).project.id;
  const editor=base+'/localaiweb/editor?id='+pro;
  const libre=(await post('/api/web/project/create',{name:'Libre de recette'})).project.id;
  await p.goto(base+'/localaiweb/editor?id='+libre);
  assert.match(await p.locator('#lawPublishBtn').innerText(),/Publier/);
  const r=await post('/api/web/generate/start',{id:pro,prompt:'Préparer une vitrine pour le commerce sélectionné.'});
  assert.equal(r.state,'running');
  await p.goto(editor);
  await p.locator('#lawSaleDesk').waitFor({state:'visible'});
  assert.ok((await (await p.request.get(base+'/api/web/sales/ready?id='+pro)).json()).ready);
  await p.screenshot({path:path.join(out,'editeur.jpg'),quality:80});
  await p.click('#lawSaleDesk');await p.waitForSelector('#pitch');
  assert.equal(new URL(p.url()).hostname,'ventes.localhost');
  assert.equal(await p.evaluate(id=>fetch('/web-preview/'+id+'/index.html').then(r=>r.status),pro),403);
  await p.waitForSelector('#scriptSections details');
  assert.match(await p.locator('#scriptSections').innerText(),/Ouverture/);
  p.on('dialog',dialog=>dialog.accept());
  const facts=p.getByText('Vérifier ou compléter les informations de ce client',{exact:true});
  await facts.click();await p.selectOption('#factType','priorité');
  await p.fill('#factValue','Présenter les bouquets de saison');
  await p.click('#clientFact button');await p.waitForFunction(()=>document.querySelector('#scriptSections').textContent.includes('bouquets de saison'));
  await facts.click();
  await p.locator('#callSheet').scrollIntoViewIfNeeded();
  await p.screenshot({path:path.join(out,'feuille-ciblee.jpg'),quality:82});
  const scriptPdf=await p.evaluate(async()=>{
   const r=await fetch(document.querySelector('#printScript').href);
   return Array.from(new Uint8Array(await r.arrayBuffer()));
  });
  assert.equal(Buffer.from(scriptPdf).subarray(0,4).toString(),'%PDF');
  fs.writeFileSync(path.join(out,'feuille-appel-exemple.pdf'),Buffer.from(scriptPdf));
  await p.click('#prepareSale');await p.waitForFunction(()=>document.querySelector('#overallStage').textContent==='Présentation préparée');
  assert.equal(await p.locator('#dial').getAttribute('href'),null);

  await p.click('#verifyPhone');await p.waitForSelector('#dial[href^="tel:"]');
  await p.selectOption('#outcome','rappel');await p.fill('#due','2099-01-01');await p.fill('#callNote','Présenter la page des bouquets.');
  await p.click('#callLog button');await p.waitForFunction(()=>document.querySelector('#salesHistory').textContent.includes('bouquets'));
  for(const [w,h] of [[390,844],[1365,768],[1920,1080],[3840,2160]]){
   await p.setViewportSize({width:w,height:h});await p.evaluate(()=>scrollTo(0,0));
   assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await p.screenshot({path:path.join(out,'presentation-'+w+'.jpg'),quality:80});
  }
  await p.setViewportSize({width:1365,height:768});
  await p.click('.sales-steps [href="#quoteTitle"]');
  for(const [id,value] of Object.entries({sellerName:'Prestataire de recette',sellerSiret:'53784237900027',sellerAddress:'Adresse de recette',
   paymentDetails:'À convenir',latePenaltyRate:'Selon contrat',customerName:'Client démo',customerAddress:'Adresse de recette',
   customerEmail:'client@example.org',scope:'Vitrine de deux pages',recurring:'Hébergement et domaine exclus.'}))await p.fill('#'+id,value);
  await p.selectOption('#legalForm','EI');await p.selectOption('#vatMode','franchise');
  await p.click('#issueQuote');const pdf=p.locator('#quoteFeedback a');await pdf.waitFor();
  const doc=await p.request.get(new URL(await pdf.getAttribute('href'),base).href);
  assert.equal((await doc.body()).subarray(0,4).toString(),'%PDF');
  await p.click('.sales-steps [href="#agreement"]');
  await p.locator('#agreement:not([hidden])').waitFor();
  await p.waitForTimeout(300);
  await p.screenshot({path:path.join(out,'devis-avant-publication.jpg'),quality:80});
  await p.reload();await p.waitForSelector('#deskQuotes a');
  const d=await p.evaluate(id=>fetch('/api/web/sales/dossier?id='+id).then(r=>r.json()),pro);
  assert.equal(d.stage,'quote_prepared');assert.equal(d.orders.length,0);
  assert.deepEqual(errors,[]);
  console.log('LocalAiWeb #55 : Pro, Libre, CTA, rappel, reprise, PDF et quatre dimensions validés.');
 }finally{
  await p.close();
  if(process.env.SALES_VIDEO)await p.video().saveAs(path.join(out,'parcours.webm'));
  await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1});
