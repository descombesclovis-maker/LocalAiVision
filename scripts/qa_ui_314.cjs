/* Real local server, isolated data and actual Chromium/Edge interaction.
   Fixtures are labelled; no AI, map, publication or commercial claim is made. */
const {chromium}=require('playwright');
const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),output=path.resolve(process.env.UI_OUTPUT||'build/qa314');
fs.mkdirSync(output,{recursive:true});
const data=fs.mkdtempSync(path.join(os.tmpdir(),'studio-ui-314-'));
const env={...process.env,LOCALVISIONAI_DATA:data,LOCALVISIONAI_SKIP_SETUP:'1',LOCALVISIONAI_DISABLE_AUTO_UPDATE:'1'};
const fixture=spawnSync(process.env.PYTHON||'python',['-m','scripts.qa_ui_fixture_314',data],{cwd:root,env,encoding:'utf8'});
if(fixture.status!==0)throw Error(fixture.stderr);
const ids=JSON.parse(fixture.stdout),base='http://127.0.0.1:3000';
// Chromium on Windows normalises clipboard newlines to CRLF. The persisted
// original is independently checked without any normalisation.
const normaliseClipboardLines=s=>String(s).replace(/\r\n?/g,'\n');
const server=spawn(process.env.PYTHON||'python',['-m','local_app.server'],{cwd:root,env,stdio:['ignore','pipe','pipe']});
const log=fs.createWriteStream(path.join(output,'server.log'));server.stdout.pipe(log);server.stderr.pipe(log);
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const results={channel:process.env.UI_BROWSER_CHANNEL||'chromium',checks:[],limits:['Labelled QA projects only. AI/GPU engines, live Google Maps and commercial operations were not exercised.']};
let browser;
async function api(route){const r=await fetch(base+route);if(!r.ok)throw Error(route+': '+r.status);return r.json()}
async function check(name,fn){await fn();results.checks.push({name,passed:true})}
(async()=>{
 try{
  for(let n=0;n<100;n++){try{await api('/api/web/projects');break}catch(e){if(n===99)throw e;await wait(150)}}
  browser=await chromium.launch({headless:true,...(process.env.UI_BROWSER_CHANNEL?{channel:process.env.UI_BROWSER_CHANNEL}:{}),...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
  const context=await browser.newContext({viewport:{width:1365,height:768},permissions:['clipboard-read','clipboard-write'],recordVideo:{dir:path.join(output,'video'),size:{width:1365,height:768}}});
  const page=await context.newPage(),video=page.video();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await check('Vision top-layer menu hides rail, blocks background input and restores focus',async()=>{
   await page.goto(base+'/localaivision');await page.locator('#qcmDock').waitFor();await page.locator('#openSidebar').click();
   const sidebar=page.locator('#sidebar');
   await page.waitForFunction(()=>document.getElementById('sidebar').getBoundingClientRect().left>=-1);
   assert.ok((await sidebar.boundingBox()).x>=-1);
   assert.equal(await sidebar.evaluate(x=>x.matches(':popover-open')),true);
   assert.equal(await page.locator('.main').evaluate(x=>x.inert),true);
   assert.equal(await page.locator('#qcmDock').evaluate(x=>x.inert),true);
   assert.equal(await sidebar.locator('#updateBtn,.studio-universe-link').count(),0);
   assert.equal(await sidebar.evaluate(x=>getComputedStyle(x).backgroundColor),'rgb(9, 44, 56)');
   // Pictograms must now be visible on ordinary menu actions, unlike the two special controls.
   assert.equal(await sidebar.locator('#navPhoto .nav-glyph').evaluate(e=>getComputedStyle(e).display!=='none'),true);
   const geometry=await sidebar.locator('.studio-navigation>button').evaluateAll(xs=>xs.map(x=>{let r=x.getBoundingClientRect();return {x:r.x,w:r.width,h:r.height}}));
   assert.ok(geometry.every(r=>Math.abs(r.x-geometry[0].x)<1&&Math.abs(r.w-geometry[0].w)<1&&Math.abs(r.h-geometry[0].h)<1));
   assert.equal(await page.evaluate(()=>document.querySelector('#sidebar').contains(document.elementFromPoint(35,300))),true);
   await check('Navigation icons restored except for distinct LoRA and New discussion actions',async()=>{
    for(const id of ['navCreations','navPhoto','navVideo','studioAdOpen','navNsfw']){
     const icon=sidebar.locator('#'+id+' .nav-glyph');
     assert.equal(await icon.evaluate(e=>getComputedStyle(e).display!=='none'),true,id+' icon hidden');
    }
    const lora=sidebar.locator('#visionAdvancedToggle');
    const fresh=sidebar.locator('#newConversation');
    assert.equal(await lora.locator('.nav-glyph').evaluate(e=>getComputedStyle(e).display),'none');
    assert.equal(await fresh.locator('.nav-glyph,svg,img').count(),0);
    const generic=await sidebar.locator('#navPhoto').evaluate(e=>getComputedStyle(e).backgroundColor);
    for(const special of [lora,fresh]){
     assert.notEqual(await special.evaluate(e=>getComputedStyle(e).backgroundColor),generic);
    }
   });
   await page.screenshot({path:path.join(output,'vision-menu-desktop.png')});
   await page.keyboard.press('Escape');assert.equal(await page.locator('.main').evaluate(x=>x.inert),false);
   assert.equal(await page.locator('#openSidebar').evaluate(x=>x===document.activeElement),true);
   await page.locator('#openSidebar').click();await page.mouse.click(700,400);
   assert.equal(await sidebar.evaluate(x=>x.matches(':popover-open')),false);
  });
  await page.goto(base+'/localaiweb');await page.locator('[data-qcm-filter="free"]').click();
  const card=name=>page.locator('article.card').filter({has:page.getByRole('button',{name:'Ouvrir le projet '+name,exact:true})});
  const first=card('Recette 314 — prompt exact'),second=card('Recette 314 — à conserver'),legacy=card('Recette 314 — ancien projet');
  await check('Exact first prompt is copied; missing historical prompt is honestly reported',async()=>{
   await first.locator('summary').click();await first.getByRole('button',{name:"Copier le prompt d'origine"}).click();
   await page.waitForFunction(()=>document.getElementById('libraryStatus').textContent.includes('copié'));
   const raw=(await api('/api/web/project?id='+encodeURIComponent(ids.first))).project.original_prompt;
   assert.equal(raw,ids.prompt,'The persisted original must remain unchanged');
   assert.equal(normaliseClipboardLines(await page.evaluate(()=>navigator.clipboard.readText())),
     normaliseClipboardLines(ids.prompt),'Clipboard content differs beyond Windows line endings');
   await legacy.locator('summary').click();await legacy.getByRole('button',{name:"Copier le prompt d'origine"}).click();
   await page.waitForFunction(()=>document.getElementById('libraryStatus').textContent.includes('n’a pas été conservé'));
   assert.equal(new URL(page.url()).pathname,'/localaiweb');
  });
  await check('Photograph fallback is a labelled local image',async()=>{
   const img=second.locator('.project-illustration');await img.scrollIntoViewIfNeeded();
   assert.equal(await img.evaluate(x=>x.complete&&x.naturalWidth>0),true);
   assert.match(await second.locator('.art-caption').innerText(),/illustrative/);
   await page.screenshot({path:path.join(output,'project-context-and-photos.png')});
  });
  await check('Named confirmation, cancellation and deletion target only the selected identifier',async()=>{
   await first.locator('summary').click();await first.getByRole('button',{name:'Supprimer le projet',exact:true}).click();
   assert.equal(await page.locator('#deleteProjectName').innerText(),'Recette 314 — prompt exact');
   assert.equal(await page.locator('#cancelDeleteProject').evaluate(x=>x===document.activeElement),true);
   await page.screenshot({path:path.join(output,'delete-confirmation.png')});
   await page.locator('#cancelDeleteProject').click();assert.ok((await api('/api/web/projects')).projects.some(p=>p.id===ids.first));
   await first.locator('summary').click();await first.getByRole('button',{name:'Supprimer le projet',exact:true}).click();
   await page.locator('#confirmDeleteProject').click();await page.waitForFunction(()=>document.getElementById('libraryStatus').textContent==='Projet supprimé.');
   const saved=(await api('/api/web/projects')).projects;
   assert.ok(!saved.some(p=>p.id===ids.first));assert.ok(saved.some(p=>p.id===ids.second));assert.ok(saved.some(p=>p.id===ids.legacy));
  });
  await check('Reduced motion, hidden-window and GPU pause gates act on decorative animations',async()=>{
   await page.emulateMedia({reducedMotion:'reduce'});
   assert.equal(await page.evaluate(()=>getComputedStyle(document.body,'::before').animationName),'none');
   await page.emulateMedia({reducedMotion:'no-preference'});
   const states=await page.evaluate(()=>{
    document.body.dataset.gpuBusy='true';const gpu=getComputedStyle(document.body,'::before').animationPlayState;
    delete document.body.dataset.gpuBusy;document.body.dataset.motionPaused='true';const hidden=getComputedStyle(document.body,'::before').animationPlayState;
    delete document.body.dataset.motionPaused;return {gpu,hidden};
   });assert.deepEqual(states,{gpu:'paused',hidden:'paused'});
  });
  await check('Home photographs and controls remain usable on mobile',async()=>{
   await page.setViewportSize({width:390,height:844});await page.goto(base+'/studio');
   assert.equal(await page.locator('.studio-photo').count(),2);
   assert.equal(await page.locator('.studio-photo').evaluateAll(xs=>xs.every(x=>x.complete&&x.naturalWidth>0)),true);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.screenshot({path:path.join(output,'home-mobile.png'),fullPage:true});
   await page.goto(base+'/localaivision');await page.locator('#openSidebar').click();
   await page.waitForFunction(()=>document.getElementById('sidebar').getBoundingClientRect().left>=-1);
   // Mobile topbar CSS must not hide labels after those controls move to the menu.
   for(const [id,label] of [['historyBtn','Historique'],['newConversation','Nouvelle discussion']]){
    const name=page.locator('#sidebar #'+id+' > span');
    assert.equal(await name.isVisible(),true,id+' label hidden on mobile');
    assert.equal((await name.innerText()).trim(),label);
    const box=await name.boundingBox();assert.ok(box&&box.width>60,id+' label is too narrow');
   }
   assert.equal(await page.locator('#sidebar #newConversation svg,#sidebar #newConversation img,#sidebar #newConversation .nav-glyph').count(),0);
   await page.screenshot({path:path.join(output,'vision-menu-mobile.png')});await page.keyboard.press('Escape');
  });
  assert.deepEqual(errors,[]);
  await context.close();await video.saveAs(path.join(output,'build314-interactions.webm'));
 }catch(e){results.error=e.stack;process.exitCode=1}
 finally{if(browser)await browser.close();server.kill();log.end();fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2))}
})();
