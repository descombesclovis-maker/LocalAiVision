/* Actual UI and backend interactions. Chat/GPU/agent events are labelled test fixtures. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const root=path.resolve(process.env.UI_SOURCE||path.join(__dirname,'..')),output=path.resolve(process.env.UI_OUTPUT||'build/qa315/human-audit-1');
fs.mkdirSync(output,{recursive:true});
const data=fs.mkdtempSync(path.join(os.tmpdir(),'studio-human-audit-'));
const env={...process.env,LOCALVISIONAI_DATA:data,LOCALVISIONAI_SKIP_SETUP:'1',LOCALVISIONAI_DISABLE_AUTO_UPDATE:'1'};
const server=spawn(process.env.PYTHON||'python',['-m','local_app.server'],{cwd:root,env,stdio:['ignore','pipe','pipe']});
const log=fs.createWriteStream(path.join(output,'server.log'));server.stdout.pipe(log);server.stderr.pipe(log);
const base='http://127.0.0.1:3000',wait=ms=>new Promise(r=>setTimeout(r,ms));
const results={checks:[],limitations:['AI replies and progress events below are fixtures, not actual render or authentication evidence. No RTX 3060 is available in CI.']};
let browser;
async function api(route,body){const r=await fetch(base+route,body?{method:'POST',headers:{'Content-Type':'application/json','X-LocalAI-Brand':'1'},body:JSON.stringify(body)}:undefined);const d=await r.json();if(!r.ok||d.error)throw Error(d.error||r.status);return d}
async function check(name,fn){await fn();results.checks.push({name,passed:true})}
(async()=>{try{
 for(let i=0;i<100;i++){try{await api('/api/web/projects');break}catch(e){if(i===99)throw e;await wait(150)}}
 browser=await chromium.launch({headless:true,...(process.env.UI_BROWSER_CHANNEL?{channel:process.env.UI_BROWSER_CHANNEL}:{}),args:['--no-sandbox']});
 const page=await browser.newPage({reducedMotion:'reduce',serviceWorkers:'block'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const [name,width,height] of [['desktop',1440,1000],['tablet',820,1180],['mobile',390,844]]){
  await page.setViewportSize({width,height});await page.goto(base+'/localaivision');await wait(1200);
  await page.screenshot({path:path.join(output,'vision-'+name+'.png')});
  if(process.env.UI_BASELINE!=='1'){
   await check('Chat welcome and centered header '+name,async()=>{
    assert.equal(await page.locator('#taskMode').inputValue(),'chat');
    assert.match(await page.locator('#welcome').innerText(),/Vous êtes dans le chat/);
    const box=await page.locator('#homeBtn').boundingBox();assert.ok(Math.abs(box.x+box.width/2-width/2)<2,'Logo not centered');
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.locator('#openSidebar').click();await page.locator('#navCreations').click();
    await page.locator('#openSidebar').click();await page.locator('#navChat').click();
    assert.equal(await page.locator('#messages .library-view').count(),0);
    assert.equal(await page.locator('#prompt').getAttribute('placeholder'),'Écris ton message…');
   });
  }
 }
 if(process.env.UI_BASELINE==='1')return;
 await page.setViewportSize({width:1440,height:1000});
 await check('Photo, Video and Chat keep separate modes without erasing history',async()=>{
  let chats=0,generations=0;
  await page.route('**/api/chat/stream',async route=>{chats++;await route.fulfill({contentType:'application/x-ndjson',body:JSON.stringify({delta:'Réponse simulée pour la recette du routage.'})+'\n'})});
  await page.route('**/api/studio/media/start',async route=>{generations++;await route.fulfill({status:503,json:{error:'Interception de recette, aucun rendu GPU.'}})});
  await page.locator('#prompt').fill('Génère une photo et explique comment créer une vidéo.');await page.locator('#send').click();
  await page.waitForFunction(()=>!document.getElementById('send').disabled);
  assert.equal(chats,1);assert.equal(generations,0);
  for(const [id,mode,placeholder] of [['navPhoto','image','Décris ta photo…'],['navVideo','video','Décris ta vidéo…'],['navChat','chat','Écris ton message…']]){
   await page.locator('#openSidebar').click();await page.locator('#'+id).click();
   assert.equal(await page.locator('#taskMode').inputValue(),mode);assert.equal(await page.locator('#prompt').getAttribute('placeholder'),placeholder);
  }
  assert.ok(await page.evaluate(()=>Object.values(JSON.parse(localStorage.getItem('lva_conversations_v2'))).some(c=>c.messages.some(m=>m.text?.includes('explique comment')))));
 });
 const brand=(await api('/api/studio/brand/save',{name:'MARQUE DE RECETTE',sector:'Données fictives pour test',primary_color:'#8B5CF6',secondary_color:'#22D3EE',description:'Services de démonstration, sans offre commerciale réelle.'})).brand;
 await check('Global brand selection persists on Studio home',async()=>{
  await page.goto(base+'/studio');await page.locator('#homeBrandChoose').click();await page.getByRole('button',{name:'Choisir MARQUE DE RECETTE',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('homeBrandName').textContent==='MARQUE DE RECETTE');
  await page.reload();await page.waitForFunction(()=>document.getElementById('homeBrandName').textContent==='MARQUE DE RECETTE');
  await page.screenshot({path:path.join(output,'studio-brand-desktop.png'),fullPage:true});
 });
 await check('Advertisement brand association is saved without resetting the draft',async()=>{
  await page.goto(base+'/localaivision');await wait(600);await page.locator('#openSidebar').click();await page.locator('#studioAdOpen').click();
  await page.locator('#visionBrandButton').click();await page.getByRole('button',{name:'Choisir MARQUE DE RECETTE',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('visionBrandButton').textContent.includes('MARQUE DE RECETTE'));
  assert.match(await page.locator('#visionBrandButton').innerText(),/MARQUE DE RECETTE/);
  assert.equal(await page.evaluate(()=>conversationFor(activeConversationId).brand_id),brand.id);
  await page.screenshot({path:path.join(output,'advert-brand-desktop.png')});
 });
 await check('Web project brand saves through the actual backend; global changes do not change it',async()=>{
  const project=await api('/api/web/project/create',{name:'PROJET DE RECETTE'}),id=project.project.id;
  await page.goto(base+'/localaiweb/editor?id='+id);await page.locator('#lawBrandButton').click();await page.getByRole('button',{name:'Choisir MARQUE DE RECETTE',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('lawBrandButton').textContent.includes('MARQUE DE RECETTE'));
  assert.equal((await api('/api/web/project?id='+id)).project.brand_id,brand.id);
  await page.evaluate(()=>localStorage.removeItem('localai_studio_brand_id'));await page.reload();
  assert.equal((await api('/api/web/project?id='+id)).project.brand_id,brand.id);
  await page.screenshot({path:path.join(output,'web-brand-desktop.png')});
  await page.evaluate(()=>{showSiteEditing(true);updateEditMilestones({phase:'building',detail:'Fixture de recette : écriture du code.'})});
  assert.equal(await page.locator('.law-generation-ring .studio-progress-hint').innerText(),'estimé');
  await page.screenshot({path:path.join(output,'web-progress-desktop.png')});
  await page.locator('#lawKeepPreview').click();assert.equal(await page.locator('#lawEditOverlay').isVisible(),false);
 });
 await check('Real browser decoder refuses corrupt files and recovers after reload without submitting a render',async()=>{
  let readable=false,renderSubmissions=0,historyIntercepts=0;
  const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAABAAAAAICAIAAAB/FOjAAAAAFklEQVR4nGNk2HKJgRTARJLqUQ1EAgBfOAGWhX/nswAAAABJRU5ErkJggg==','base64');
  const video=fs.readFileSync(path.join(__dirname,'../tests/fixtures/public-decoder-check.webm'));
  await page.route('**/api/studio/media/start',async route=>{renderSubmissions++;await route.fulfill({status:503,json:{error:'Fixture only; GPU render forbidden in this check.'}})});
  await page.route('**/api/history/qa-decoder',async route=>{historyIntercepts++;await route.fulfill({json:{'qa-decoder':{status:{completed:true,status_str:'success'},outputs:{one:{images:[{filename:'qa-decoder.png',type:'output'}]}}}}})});
  await page.route('**/api/view?**',async route=>{
   const name=new URL(route.request().url()).searchParams.get('filename');
   if(name==='qa-decoder.png')return route.fulfill({contentType:'image/png',headers:{'Cache-Control':'no-store'},body:readable?png:Buffer.from('Unreadable fixture, not an AI render.')});
   if(name==='qa-decoder.webm')return route.fulfill({contentType:'video/webm',body:video});
   return route.continue();
  });
  await page.goto(base+'/localaivision');
  await page.waitForFunction(()=>Boolean(window.StudioMediaValidation));
  const id=await page.evaluate(async()=>{const c=createBlankConversation('auto');await waitResults(['qa-decoder'],c.id,{id:'qa-decoder',kind:'image'},'RECETTE TECHNIQUE — pixels de test, aucune génération IA','image');return c.id});
  assert.ok(historyIntercepts>0,'The history fixture must be intercepted, never sent to live ComfyUI.');
  assert.equal(await page.evaluate(()=>library.filter(x=>x.filename==='qa-decoder.png').length),0);
  await page.locator('.output-verification-retry').waitFor();
  await page.screenshot({path:path.join(output,'public-output-unreadable-fixture.png')});
  await page.reload();await page.waitForFunction(()=>Boolean(window.StudioMediaValidation));
  await page.evaluate(id=>openConversation(id),id);
  await page.locator('.output-verification-retry').waitFor();readable=true;
  await page.locator('.output-verification-retry').click();
  await page.waitForFunction(()=>library.some(x=>x.filename==='qa-decoder.png'&&x.technical_validation?.verified===true));
  assert.equal(renderSubmissions,0);
  assert.equal(await page.locator('.output-verification-retry').count(),0);
  const receipt=await page.evaluate(()=>StudioMediaValidation.verify('/api/view?filename=qa-decoder.webm','video'));
  assert.equal(receipt.scope,'browser_first_frame_and_metadata');assert.equal(receipt.full_video_decode,false);assert.equal(receipt.width,16);assert.ok(receipt.duration_seconds>0);
 });
 await check('Vision public gallery thumbnail, three-dot menu and fullscreen viewer',async()=>{
  await page.locator('#openSidebar').click();
  await page.locator('#navCreations').click();
  const card=page.locator('#messages .gallery-card').first();
  await card.waitFor();
  const media=card.locator('img,video').first();
  await media.click();
  assert.equal(await page.locator('dialog.vision-gallery-modal').evaluate(node=>node.open),true);
  await page.locator('.vision-gallery-modal .vision-dialog-close').first().click();
  await card.locator('.vision-gallery-more').click();
  const menu=card.locator('.vision-gallery-options');
  assert.equal(await menu.getAttribute('role'),'menu');
  assert.equal(await menu.locator('[role="menuitem"]').count(),3);
  assert.equal(await card.locator('.vision-gallery-more').getAttribute('aria-expanded'),'true');
  await page.screenshot({path:path.join(output,'gallery-menu-desktop.png')});
  await page.keyboard.press('Escape');
  assert.equal(await menu.isVisible(),false);
 });
 await check('Vision top-right Studio return, vector-only drawer and public rail emoji',async()=>{
  await page.goto(base+'/localaivision');await page.setViewportSize({width:1440,height:1000});
  const link=page.locator('#visionStudioReturn');
  assert.equal(await link.isVisible(),true);
  assert.equal(await link.getAttribute('href'),'/studio');
  await page.locator('#openSidebar').click();
  assert.equal(await page.locator('#sidebar .studio-navigation .vision-nav-emoji').count(),0);
  assert.equal(await page.locator('#navPhoto .nav-glyph svg').count(),1);
  assert.equal(await page.locator('#sidebar #newConversation').isVisible(),false);
  assert.ok(await page.locator('#qcmDock .qcm-emoji-vision').count()>0);
  await page.keyboard.press('Escape');
 });
 await check('Vision mode menu alignment, six cyan arrows, keyboard and reduced motion on desktop and mobile',async()=>{
  const ids=['navChat','navCreations','navPhoto','navVideo','navNsfw','studioAdOpen'];
  for(const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
   await page.setViewportSize({width,height});await page.goto(base+'/localaivision');
   const link=page.locator('#visionStudioReturn');
   assert.equal((await link.innerText()).trim(),'LocalAiStudio');
   assert.equal(await link.locator('svg,.studio-return-arrow').count(),0);
   const box=await link.boundingBox();assert.ok(box.x+box.width<=width && box.x>width/2);
   await page.locator('#openSidebar').click();
   const rows=await page.evaluate(ids=>ids.map(id=>{
    const el=document.getElementById(id),arrow=el.querySelector('.vision-menu-chevron'),svg=arrow?.querySelector('svg');
    const rect=el.getBoundingClientRect(),a=arrow?.getBoundingClientRect();
    return {id,width:rect.width,height:rect.height,align:getComputedStyle(el).textAlign,groupCenter:(()=>{const kids=[...el.children].filter(n=>n.getBoundingClientRect().width>0);const left=Math.min(...kids.map(n=>n.getBoundingClientRect().left)),right=Math.max(...kids.map(n=>n.getBoundingClientRect().right));return (left+right)/2})(),rowCenter:rect.x+rect.width/2,
     arrows:el.querySelectorAll('.vision-menu-chevron').length,stroke:svg&&getComputedStyle(svg).stroke,
     right:a?.right,cy:a&&a.y+a.height/2,rowCy:rect.y+rect.height/2};
   }),ids);
   for(const row of rows){
    assert.equal(row.arrows,1,row.id);assert.equal(row.align,'center',row.id);assert.ok(Math.abs(row.groupCenter-row.rowCenter)<3,row.id+' centered group');
    const rgb=row.stroke.match(/\d+/g).map(Number);assert.ok(rgb[1]>rgb[0]+60&&rgb[2]>rgb[0]+60,row.id+' cyan stroke');
    assert.ok(Math.abs(row.width-rows[0].width)<1 && Math.abs(row.height-rows[0].height)<1,row.id+' dimensions');
    assert.ok(Math.abs(row.cy-row.rowCy)<1,row.id+' arrow vertical alignment');
   }
   assert.equal(await page.locator('#visionAdvancedToggle .vision-menu-chevron').count(),0);
   await page.screenshot({path:path.join(output,'vision-mode-menu-'+name+'.png')});
  }
  await page.emulateMedia({reducedMotion:'no-preference'});
  const arrow=page.locator('#navPhoto .vision-menu-chevron');
  const transform=()=>arrow.evaluate(el=>getComputedStyle(el).transform);
  await page.locator('#navPhoto').hover();await wait(300);
  assert.equal(await transform(),'matrix(1, 0, 0, 1, 4, 0)');
  await page.mouse.move(380,800);await page.locator('#navChat').focus();await page.keyboard.press('Tab');
  assert.equal(await page.locator('#navCreations').evaluate(el=>el.matches(':focus-visible')),true);
  await wait(300);
  assert.equal(await page.locator('#navCreations .vision-menu-chevron').evaluate(el=>getComputedStyle(el).transform),'matrix(1, 0, 0, 1, 4, 0)');
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await page.locator('#navCreations .vision-menu-chevron').evaluate(el=>getComputedStyle(el).transform),'none');
  await page.keyboard.press('Escape');await page.locator('#visionStudioReturn').click();
  await page.waitForURL(base+'/studio');
  await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/localaivision');
 });
 await check('Photo chat retains media when removed from gallery and restores through pull drawer',async()=>{
  await page.locator('#openSidebar').click();
  await page.locator('#navPhoto').click();
  await page.evaluate(()=>{
    const c=conversationFor(activeConversationId);
    addMessage(c.id,{role:'user',text:'PHOTO FICTIVE de recette, aucune génération GPU'});
    const file={filename:'qa-conversation-archive.png',subfolder:'',type:'output'};
    addMessage(c.id,{role:'assistant',result:file});
    addLibrary(file,'image','PHOTO FICTIVE de recette','auto');
  });
  const pull=page.locator('#visionChatArchive .vision-archive-pull');
  await pull.waitFor({state:'visible'});
  await pull.click();
  assert.equal(await page.locator('#visionArchivePanel .vision-archive-item').count(),1);
  assert.equal(await page.evaluate(()=>conversationFor(activeConversationId).studioMode),'image');
  page.once('dialog',d=>d.accept());
  await page.getByRole('button',{name:'Retirer de la galerie'}).click();
  assert.equal(await page.evaluate(()=>library.find(x=>x.filename==='qa-conversation-archive.png').galleryHidden),true);
  assert.equal(await page.evaluate(()=>conversationFor(activeConversationId).messages.some(m=>m.result?.filename==='qa-conversation-archive.png')),true);
  await page.getByRole('button',{name:'Restaurer dans Mes créations'}).click();
  assert.equal(await page.evaluate(()=>library.find(x=>x.filename==='qa-conversation-archive.png').galleryHidden),false);
  page.once('dialog',d=>d.dismiss());
  await page.getByRole('button',{name:'Supprimer définitivement'}).click();
  assert.equal(await page.evaluate(()=>conversationFor(activeConversationId).messages.some(m=>m.result?.filename==='qa-conversation-archive.png')),true);
  await page.screenshot({path:path.join(output,'conversation-archive-recovery.png')});
 });
 assert.deepEqual(errors,[]);
 }catch(e){results.error=e.stack;process.exitCode=1}
 finally{if(browser)await browser.close();server.kill();log.end();fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2))}
})();
