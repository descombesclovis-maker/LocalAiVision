// Run against a disposable LocalAI Studio server with engine setup disabled.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');
const base = 'http://127.0.0.1:3000';
const out = process.env.QA_OUTPUT || 'docs/qa296';
fs.mkdirSync(out, { recursive: true });
const report = { platform: process.platform, dpi: [] };
const snap = (page, name) => page.screenshot({path:path.join(out,name+'.jpg'),quality:82});
const box = locator => locator.boundingBox();

async function home(browser) {
  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  for (const [width,height] of [[1365,768],[1920,1080],[3840,2160],[1280,720],[390,844]]) {
    await page.setViewportSize({width,height});
    await page.goto(base+'/studio');
    await page.waitForTimeout(1100);
    const cards = page.locator('.universe-card');
    if (width===3840) {
      const row=await box(page.locator('.universe-choices'));
      assert.ok(row.width>width*.75);
      const layer=page.locator('.scene-front').first();
      const transform=()=>layer.evaluate(el=>getComputedStyle(el).transform);
      const start=await transform();
      await page.waitForTimeout(350);
      assert.notEqual(await transform(),start);
      report.animation=await page.evaluate(async()=>{
        const samples=[];
        const front=document.querySelector('.scene-front');
        await new Promise(resolve=>{
          function frame(t){
            samples.push({ms:t,matrix:getComputedStyle(front).transform});
            if(samples.length===90)resolve();else requestAnimationFrame(frame);
          }
          requestAnimationFrame(frame);
        });
        const elapsed=samples.at(-1).ms-samples[0].ms;
        return { viewport:[innerWidth,innerHeight], rafPerSecond:89*1000/elapsed, samples };
      });
      await snap(page,'motion-active');
      await page.locator('.qcm-home-tools summary').click();
      await page.locator('#qcmMotionToggle').click();
      await page.locator('.qcm-home-tools summary').click();
      assert.equal(await page.locator('.studio-scene').first().evaluate(el=>el.getAnimations({subtree:true}).length),0);
      await snap(page,'motion-reduced');
      await page.reload();
      assert.equal(await page.locator('#qcmMotionToggle').getAttribute('aria-pressed'),'true');
      await page.locator('.qcm-home-tools summary').click();
      await page.locator('#qcmMotionToggle').click();
      await page.locator('.qcm-home-tools summary').click();
      await page.emulateMedia({reducedMotion:'reduce'});
      assert.equal(await layer.evaluate(el=>getComputedStyle(el).animationName),'none');
      await page.emulateMedia({reducedMotion:'no-preference'});
      await page.waitForTimeout(1200);
    }
    await snap(page,'apres-'+width);
    for (const card of await cards.all()) {
      const title=await box(card.locator('.studio-card-title'));
      const scene=await box(card.locator('.studio-scene'));
      const cta=card.locator('.studio-card-cta');
      const action=await box(cta);
      assert.ok(title.y+title.height<=scene.y+1 && scene.y+scene.height<=action.y+1);
      if(width===390){
        await cta.scrollIntoViewIfNeeded();
        const a=await box(cta), dock=await box(page.locator('#qcmDock'));
        assert.ok(a.y>=0 && a.y+a.height<=dock.y);
        assert.ok(await cta.evaluate(el=>{const r=el.getBoundingClientRect();return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}));
        await card.focus();
        assert.ok(await card.evaluate(el=>document.activeElement===el));
      }
    }
    if(width===390)await snap(page,'mobile-vision-scroll');
  }
  await page.close();
  for(const scale of [1,1.25,1.5]){
    const p=await browser.newPage({viewport:{width:1365,height:768},deviceScaleFactor:scale});
    await p.goto(base+'/studio');await p.waitForTimeout(1100);
    const title=await box(p.locator('h1')), cta=await box(p.locator('.studio-card-cta').first()), dock=await box(p.locator('#qcmDock'));
    assert.ok(title.y>=0 && cta.y+cta.height<=dock.y);
    await p.evaluate(()=>document.documentElement.style.zoom='125%');
    const overflow=await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
    assert.equal(overflow,false);
    report.dpi.push({deviceScaleFactor:scale,dpr:await p.evaluate(()=>devicePixelRatio),title,cta,dock});
    await p.close();
  }
}

async function vision(browser){
  const p=await browser.newPage({viewport:{width:1365,height:768}});
  await p.goto(base+'/localaivision');await p.waitForSelector('.qcm-vision-modes');
  await snap(p,'vision');
  report.icons=await p.locator('#qcmDock a > span,.qcm-vision-modes button > span').evaluateAll(els=>els.map(el=>el.querySelector('svg')?'SVG':el.textContent));
  await p.locator('#openSidebar').click();
  await p.keyboard.press('Escape');
  assert.equal(await p.locator('#openSidebar').getAttribute('aria-expanded'),'false');
  assert.ok(await p.locator('#openSidebar').evaluate(el=>el===document.activeElement));
  for(const [id,mode] of [['navPhoto','image'],['navVideo','video']]){
    await p.click('#openSidebar');await p.click('#'+id);
    assert.equal(await p.locator('#taskMode').inputValue(),mode);
  }
  const chooser=p.waitForEvent('filechooser');
  await p.click('#composerImageBtn');
  await (await chooser).setFiles({name:'reference.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j4woAAAAASUVORK5CYII=','base64')});
  await p.waitForSelector('#composerImageBtn.attached');
  assert.equal(await p.locator('#taskMode').inputValue(),'i2v');
  await p.click('#openSidebar');
  const cancellation=p.waitForEvent('dialog').then(dialog=>dialog.dismiss());
  await Promise.all([cancellation,p.click('#navNsfw')]);
  assert.equal(await p.evaluate(()=>document.body.classList.contains('nsfw-active')),false);
  await p.keyboard.press('Escape');
  // Layout-state regression only. No private workspace is unlocked or populated.
  await p.evaluate(()=>document.body.classList.add('nsfw-active'));
  await p.waitForSelector('.topbar-actions #newConversation',{state:'attached'});
  assert.equal(await p.locator('#qcmVisionViewer').isVisible(),false);
  await p.evaluate(()=>document.body.classList.remove('nsfw-active'));
  await p.waitForSelector('.studio-navigation #newConversation',{state:'attached'});
  assert.equal(await p.locator('#newConversation').count(),1);
  await p.close();
}

const tileCache=new Map();
async function visibleTile(route){
  const url=route.request().url();
  if(!tileCache.has(url)){
    tileCache.set(url,fetch(url,{headers:{'User-Agent':'LocalAiStudio-Review/54 (interactive viewport QA)'},signal:AbortSignal.timeout(8000)}).then(async r=>{
      if(!r.ok)throw Error('Tile '+r.status);
      return Buffer.from(await r.arrayBuffer());
    }));
  }
  try {await route.fulfill({contentType:'image/png',body:await tileCache.get(url)})}
  catch {await route.abort()}
}
async function map(browser,width,height){
  const p=await browser.newPage({viewport:{width,height},serviceWorkers:'block'});
  const points=[[48.86,2.35],[45.76,4.84],[44.84,-.58],[47.22,-1.55],[43.30,5.37],[48.58,7.75]];
  const rows=points.map(([lat,lon],i)=>({id:'node/'+(800+i),name:['Atelier démo','Librairie démo','Café démo','Fleuriste démo','Salon démo','Boutique démo'][i],source:'Jeu de recette #54',city:['Paris','Lyon','Bordeaux','Nantes','Marseille','Strasbourg'][i],lat,lon,website:i===5?'https://example.org':''}));
  await p.route('**/leaflet@1.9.4/dist/leaflet.*',r=>{
    const css=r.request().url().endsWith('.css');
    return r.fulfill({path:require.resolve('leaflet/dist/leaflet.'+(css?'css':'js')),headers:{'access-control-allow-origin':'*','content-type':css?'text/css':'text/javascript'}});
  });
  await p.route('https://tile.openstreetmap.org/**',visibleTile);
  await p.route('https://basemaps.cartocdn.com/**',visibleTile);
  await p.route('**/api/web/map/**',r=>{
    const url=new URL(r.request().url());
    const body=url.pathname.endsWith('/config')?{enabled:false}:url.pathname.endsWith('/today')?{date:'fixture',pool:5,results:rows.slice(0,5)}:url.pathname.endsWith('/index')?{count:6,results:rows}:url.pathname.endsWith('/refresh')?{business:rows.find(x=>x.id===url.searchParams.get('id'))}:{results:[],next_batch:null};
    return r.fulfill({json:body});
  });
  await p.goto(base+'/localaiweb/map',{waitUntil:'domcontentloaded'});
  await p.waitForSelector('.company-marker-hit');
  await p.waitForFunction(()=>typeof window.StudioMapRecenter==='function');
  await p.evaluate(()=>window.StudioMapRecenter());
  await p.waitForTimeout(800);
  await p.waitForSelector('.leaflet-tile-loaded',{timeout:12000}).catch(()=>{});
  const drawer=p.locator('#dailyProspectsToggle');
  if(await drawer.getAttribute('aria-expanded')==='false')await drawer.click();
  assert.equal(await p.locator('.daily-prospect').count(),5);
  const d=await box(p.locator('#dailyProspects')),dock=await box(p.locator('#qcmDock'));
  assert.ok(d.y+d.height<=dock.y+1);
  for(const [value,count] of [['all',6],['missing',5],['recorded',1]]){
    await p.selectOption('#qcmWebsiteFilter',value);
    await p.waitForFunction(n=>document.querySelector('#loadedCount').textContent===String(n),count);
    assert.equal(await p.locator('.company-marker-single').count()+await p.locator('.company-marker-group').evaluateAll(nodes=>nodes.reduce((sum,n)=>sum+Number(n.textContent),0)),count);
    await p.waitForTimeout(250);
    await snap(p,'map-'+width+'-'+value);
  }
  await p.locator('.company-marker-hit').first().click();
  await p.waitForSelector('#mapSelection:not([hidden])');
  assert.equal(await p.locator('#selectionTitle').innerText(),'Boutique démo');
  if(width===390){
    const target=await box(p.locator('#mapCreate'));
    assert.ok(target.y+target.height<=dock.y);
  }
  await snap(p,'map-'+width+'-fiche');
  await p.click('#mapClose');
  await p.locator('.leaflet-control-zoom-in').click();
  await p.waitForTimeout(500);
  await snap(p,'map-'+width+'-zoom');
  await p.close();
}

async function nativeMapContract(browser){
  const p=await browser.newPage({serviceWorkers:'block'});
  // Exercise our adapter boundary only. Do not request Places, render fictitious
  // Google POIs, or represent this scenario as a live Google integration test.
  await p.route('**/assets/localaiweb-google-map.js',route=>route.fulfill({
    contentType:'application/javascript',body:'window.LocalAiWebGoogleMap={start:async()=>true}'
  }));
  await p.route('**/api/web/map/config',route=>route.fulfill({json:{enabled:true,places_enabled:true}}));
  await p.route('**/leaflet@1.9.4/dist/*',route=>route.abort());
  await p.goto(base+'/localaiweb/map',{waitUntil:'domcontentloaded'});
  await p.waitForFunction(()=>document.querySelector('#qcmWebsiteFilter').disabled);
  assert.match(await p.locator('#qcmWebsiteFilterNote').innerText(),/filtrage global indisponible/);
  await p.close();
}

(async()=>{
  const browser=await chromium.launch(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH,args:['--no-sandbox','--disable-gpu']}:{channel:'msedge'});
  try{
    report.browser=browser.version();
    await home(browser);await vision(browser);
    await map(browser,1365,768);await map(browser,390,844);
    await nativeMapContract(browser);
    fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2));
    console.log('Recette #54 OK',report.platform,report.browser,report.icons,report.animation.rafPerSecond);
  }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
