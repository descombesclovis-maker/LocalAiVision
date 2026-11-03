const {chromium}=require('playwright-core');const assert=require('node:assert/strict');const fs=require('fs');const path=require('path');
const base=process.env.QA_BASE||'http://127.0.0.1:3000';const out=process.env.QA_OUTPUT||'docs/qa-extra';
(async()=>{const b=await chromium.launch(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH,args:['--no-sandbox','--disable-gpu']}:{channel:'msedge'});const p=await b.newPage();fs.mkdirSync(out,{recursive:true});try{
for(const [width,height] of [[390,844],[1365,768],[1920,1080],[3840,2160]]){
 await p.setViewportSize({width,height});
 for(const route of ['/localaiweb','/localaiweb/clients','/studio/brands']){
  await p.goto(base+route);await p.waitForTimeout(200);
  assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),route+' '+width);
 }
 await p.goto(base+'/localaivision');await p.waitForSelector('.qcm-vision-modes');
 await p.locator('#openSidebar').click();await p.locator('#visionAdvancedToggle').click();await p.locator('#generationSettings:not(.hidden)').waitFor();await p.waitForTimeout(400);
 await p.screenshot({path:path.join(out,'settings-'+width+'.jpg')});
 assert.ok(await p.locator('#generationSettings').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'settings panel overflow '+width);
 const clipped=await p.locator('#generationSettings').evaluate(panel=>[...panel.querySelectorAll('button,.lora-upload,input:not([type=file]),select')].filter(el=>{
  const rect=el.getBoundingClientRect();if(!rect.width||!rect.height)return false;
  if(el.matches('button,.lora-upload')&&el.scrollWidth>el.clientWidth+2)return true;
  for(let parent=el.parentElement;parent;parent=parent.parentElement){
   if(['hidden','auto','scroll','clip'].includes(getComputedStyle(parent).overflowX)){
    const area=parent.getBoundingClientRect();if(rect.left<area.left-2||rect.right>area.right+2)return true;
   }
   if(parent===panel)break;
  }
  return false;
 }).map(el=>el.id||el.textContent.trim()));
 assert.deepEqual(clipped,[],'clipped settings controls '+width);
 assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'settings '+width);
 await p.keyboard.press('Escape');
 await p.goto(base+'/localaivision');await p.waitForSelector('.qcm-vision-modes');
 await p.locator('.qcm-vision-modes [data-qcm-target="navCreations"]').click();
 await p.locator('.library-view').waitFor();
 await p.screenshot({path:path.join(out,'library-'+width+'.jpg')});
 assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'library '+width);
}
console.log('Extra UI: projects, CRM, brands, settings and empty public media library passed at four resolutions.');
}finally{await p.close();await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
