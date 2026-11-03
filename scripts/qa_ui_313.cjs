/* Real local HTTP server + Chromium. No mocked generation or business results.
   UI_BASELINE=1 captures the base without applying new acceptance assertions. */
const {chromium}=require('playwright');
const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const assert=require('node:assert/strict');
const root=path.resolve(process.env.UI_SOURCE||path.join(__dirname,'..'));
const output=path.resolve(process.env.UI_OUTPUT||path.join(root,'docs/qa313/after'));
fs.mkdirSync(output,{recursive:true});
const data=fs.mkdtempSync(path.join(os.tmpdir(),'studio-ui-313-'));
const server=spawn(process.env.PYTHON||'python',['-m','local_app.server'],{
 cwd:root,env:{...process.env,LOCALVISIONAI_DATA:data,LOCALVISIONAI_SKIP_SETUP:'1',LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY:'',LOCALAIWEB_GOOGLE_PLACES_API_KEY:''},stdio:['ignore','pipe','pipe']});
const log=fs.createWriteStream(path.join(output,'server.log'));server.stdout.pipe(log);server.stderr.pipe(log);
const results={baseline:!!process.env.UI_BASELINE,resolutions:[],checks:[],limitations:[
 'Google live map requires configured browser/server keys and authorized API usage.',
 'Codex generation, ComfyUI media, payment/signature/publication and Windows WebView2/DPI are not certified by this UI test.'
]};
let browser;
const base='http://127.0.0.1:3000';
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function api(url,body){const r=await fetch(base+url,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||r.status);return d}
async function check(name,fn){try{await fn();results.checks.push({name,ok:true})}catch(error){results.checks.push({name,ok:false,error:error.message});throw error}}
function fixture(project){
 const run=spawnSync(process.env.PYTHON||'python',['-m','scripts.qa_ui_fixture',data,project],{cwd:root,env:{...process.env,LOCALVISIONAI_DATA:data},encoding:'utf8'});
 if(run.status!==0)throw Error(run.stderr||'Fixture creation failed');
 return JSON.parse(run.stdout);
}
(async()=>{
 try{
  for(let i=0;i<100;i++){try{await api('/api/web/projects');break}catch(error){if(i===99)throw error;await wait(150)}}
  browser=await chromium.launch({headless:true,...(process.env.UI_BROWSER_CHANNEL?{channel:process.env.UI_BROWSER_CHANNEL}:{}),...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
  const project=await api('/api/web/project/create',{name:'Recette interface · projet vide',template:'default'});
  const id=project.project.id;
  const pages=[['studio','/studio'],['projects-pro','/localaiweb'],['projects-free','/localaiweb'],['editor','/localaiweb/editor?id='+id],['map','/localaiweb/map'],['clients','/localaiweb/clients'],['sales','/localaiweb/vente?id='+id],['vision','/localaivision'],['brands','/studio/brands']];
  for(const [width,height] of [[3840,2160],[2560,1440],[1920,1080],[1365,768],[1280,720],[390,844]]){
   const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1,reducedMotion:'reduce'});
   const page=await context.newPage();
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   for(const [name,route] of pages){
    await page.goto(base+route,{waitUntil:'domcontentloaded'});await wait(800);
    if(name==='projects-free')await page.locator('[data-qcm-filter="free"]').click();
    await page.screenshot({path:path.join(output,`${name}-${width}x${height}.png`),fullPage:true});
    const geometry=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,bodyScroll:document.body.scrollWidth}));
    results.resolutions.push({page:name,width,height,geometry,errors:[...errors]});errors.length=0;
    if(!results.baseline){
     assert.ok(geometry.scroll<=width+1,`${name} horizontal overflow at ${width}: ${geometry.scroll}`);
     if(name==='studio'){
      assert.equal(await page.locator('#qcmDock').count(),0);
      const boxes=await page.locator('.universe-card').evaluateAll(items=>items.map(x=>{const r=x.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}));
      assert.ok(Math.abs(boxes[0].w-boxes[1].w)<1);
      if(width>700)assert.ok(Math.abs(boxes[0].y-boxes[1].y)<1);
     }
     if(name==='editor'){
      assert.equal(await page.locator('#lawDesignDialog').evaluate(x=>x.open),false);
      assert.equal(await page.locator('[data-view] svg').count(),3);
      assert.equal(await page.locator('.preview-controls').evaluate(x=>x.lastElementChild.id),'lawPublishBtn');
      if(width>780){
       const composer=await page.locator('#lawComposer').boundingBox();assert.ok(composer.y+composer.height<=height+1);
      }
     }
     assert.equal(results.resolutions.at(-1).errors.length,0,`${name} has a browser error`);
     if(name==='map'){
      assert.equal(await page.locator('#mapUnavailable').isVisible(),true);
      assert.equal(await page.locator('.leaflet-container').count(),0);
     }
    }
   }
   await context.close();
  }
  if(!results.baseline){
   const context=await browser.newContext({viewport:{width:1365,height:768},recordVideo:{dir:path.join(output,'video'),size:{width:1365,height:768}}});
   const page=await context.newPage();
   const video=page.video();
   // Demonstrate actual screens and their transitions, without claiming any
   // connected AI, Google or financial operation has been performed.
   for(const [name,route] of pages){await page.goto(base+route,{waitUntil:'domcontentloaded'});await wait(1200)}
   await check('Native menu keyboard open, Escape close, focus restored',async()=>{
    await page.goto(base+'/localaiweb');const summary=page.locator('#webProjectMenu>summary');await summary.focus();await page.keyboard.press('Enter');
    assert.equal(await page.locator('#webProjectMenu').evaluate(x=>x.open),true);
    await page.screenshot({path:path.join(output,'project-menu-detail.png')});
    await page.keyboard.press('Escape');assert.equal(await page.locator('#webProjectMenu').evaluate(x=>x.open),false);
    assert.equal(await summary.evaluate(x=>x===document.activeElement),true);
   });
   await check('Libre creation via actual form and server, persisted and renamed',async()=>{
    await page.locator('#createProject').click();await page.locator('#projectName').fill('Projet réel de recette');await page.locator('#confirmProject').click();
    await page.waitForURL(/editor\?id=web-/);await wait(600);
    const pid=new URL(page.url()).searchParams.get('id');assert.ok((await api('/api/web/projects')).projects.some(x=>x.id===pid));
    await page.locator('#lawPreviewTitle').dblclick();await page.locator('.qcm-project-title-input').fill('Projet recette renommé');await page.keyboard.press('Enter');
    await wait(300);assert.equal((await api('/api/web/project?id='+pid)).project.name,'Projet recette renommé');
   });
   await check('Viewport handlers and splitter keyboard preserve live components',async()=>{
    for(const mode of ['tablet','mobile','desktop']){await page.locator('[data-view="'+mode+'"]').click();assert.ok(await page.locator('#lawPreviewStage').evaluate((x,m)=>x.classList.contains(m),mode))}
    const splitter=page.locator('#qcmEditorSplitter');await splitter.focus();await page.keyboard.press('ArrowRight');assert.equal(await splitter.getAttribute('aria-valuenow'),'34');
    await page.screenshot({path:path.join(output,'editor-buttons-detail.png')});
   });
   await check('Actual static preview, source files, versions and ZIP export using labelled test site',async()=>{
    const pid=new URL(page.url()).searchParams.get('id');fixture(pid);await page.reload();await wait(500);
    await page.locator('#lawPreview').waitFor({state:'visible'});
    await page.frameLocator('#lawPreview').locator('h1').waitFor();
    assert.match(await page.frameLocator('#lawPreview').locator('main').innerText(),/ne provient pas d’une génération IA/);
    await page.locator('.qcm-code-button').click();await page.locator('.qcm-code-files button').filter({hasText:/^index\.html$/}).click();assert.match(await page.locator('.qcm-code-content').innerText(),/RECETTE TECHNIQUE/);await page.keyboard.press('Escape');
    await page.locator('[data-qcm-panel="versions"]').click();await page.locator('.qcm-drawer-row').first().waitFor();assert.match(await page.locator('#qcmDrawerContent').innerText(),/Version de recette/);await page.locator('#qcmDrawerClose').click();
    await page.locator('.qcm-editor-more summary').click();const download=page.waitForEvent('download');await page.locator('#lawZipBtn').click();await (await download).saveAs(path.join(output,'fixture-export.zip'));
    await page.screenshot({path:path.join(output,'editor-real-preview-fixture.png')});
   });
   await check('Pro reference opens its own sales dossier without a forced questionnaire',async()=>{
    const {id:pid}=fixture('pro');await page.goto(base+'/localaiweb/editor?id='+pid);await wait(500);
    assert.equal(await page.locator('#lawDesignDialog').evaluate(x=>x.open),false);
    assert.match(await page.locator('#lawChatStatus').innerText(),/informations confirmées/);
    assert.match(await page.locator('#lawPublishBtn').innerText(),/Vendre & livrer/);
    await page.locator('#lawPublishBtn').click();await page.waitForURL(/ventes\.localhost.*\/localaiweb\/vente/);
    assert.equal(new URL(page.url()).searchParams.get('id'),pid);
    assert.equal(await page.locator('#qcmDock').count(),1);
    assert.match(await page.locator('[data-qcm-link="clients"]').getAttribute('href'),/127\.0\.0\.1/);
   });
   await check('Commercial navigation points to the actual existing CRM',async()=>{
    await page.locator('#qcmDock a[data-qcm-link="clients"]').click();await page.waitForURL(/\/localaiweb\/clients/);await page.locator('#newClient').click();assert.equal(await page.locator('#clientDialog').evaluate(x=>x.open),true);await page.keyboard.press('Escape');
   });
   await check('Public image import opens genuine file chooser; plus geometry centered',async()=>{
    await page.goto(base+'/localaivision');await wait(600);
    const button=page.locator('#composerImageBtn');
    const [chooser]=await Promise.all([page.waitForEvent('filechooser'),button.click()]);assert.ok(chooser);
    const delta=await button.evaluate(x=>{const a=x.getBoundingClientRect(),b=x.querySelector('.studio-public-plus').getBoundingClientRect();return {x:Math.abs(a.x+a.width/2-b.x-b.width/2),y:Math.abs(a.y+a.height/2-b.y-b.height/2)}});
    assert.ok(delta.x<1&&delta.y<1,JSON.stringify(delta));
    await button.screenshot({path:path.join(output,'vision-import-detail.png')});
   });
   await check('Reserved session excludes public plus and shared UI padding',async()=>{
    const actual=await page.evaluate(()=>{document.body.classList.add('nsfw-active');const plus=document.querySelector('.studio-public-plus');return {display:getComputedStyle(plus).display,padding:getComputedStyle(document.body).paddingLeft}});
    assert.equal(actual.display,'none');assert.equal(actual.padding,'0px');
    // This tests CSS exclusion only. It does not unlock or alter reserved data.
   });
   await context.close();
   await video.saveAs(path.join(output,'parcours-interface.webm'));
  }
 }catch(error){results.error=error.stack;process.exitCode=1}
 finally{
  fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2));
  if(browser)await browser.close();server.kill('SIGTERM');log.end();
  console.log(JSON.stringify({screenshots:results.resolutions.length,checks:results.checks,error:results.error||null},null,2));
 }
})();
