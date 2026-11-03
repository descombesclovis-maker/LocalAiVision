/* Export from actual vector paths, with side-by-side master comparisons. */
const sharp=require('sharp'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/brand314');
(async()=>{
 const metrics={};
 for(const n of ['Studio','Web','Vision']){
  const stem='localai-'+n.toLowerCase();
  const svg=path.join(out,stem+'-static.svg');
  await sharp(svg,{limitInputPixels:false}).resize(4096,4096).png().toFile(path.join(out,stem+'-vector-4096.png'));
  const master=path.join(root,'local_app/web/assets/brand-reference/LocalAI'+n+'_Official_Original.png');
  const a=await sharp(master).resize(724,724).removeAlpha().raw().toBuffer();
  const b=await sharp(svg).resize(724,724).removeAlpha().raw().toBuffer();
  let mae=0,square=0;for(let i=0;i<a.length;i++){let d=a[i]-b[i];mae+=Math.abs(d);square+=d*d}
  metrics[n]={mean_absolute_channel_error:mae/a.length,psnr:10*Math.log10(255**2/(square/a.length)),pixel_identical:false};
  const left=await sharp(master).resize(500,500).png().toBuffer();
  const right=await sharp(svg).resize(500,500).png().toBuffer();
  const label=Buffer.from('<svg width="1020" height="50"><rect width="1020" height="50" fill="#0d101b"/><text x="16" y="30" fill="#fff" font-size="16">Original PNG</text><text x="530" y="30" fill="#fff" font-size="16">Vector trace — gradients approximated</text></svg>');
  await sharp({create:{width:1020,height:560,channels:3,background:'#0d101b'}}).composite([{input:label,left:0,top:0},{input:left,left:0,top:50},{input:right,left:520,top:50}]).png().toFile(path.join(out,stem+'-comparison.png'));
 }
 fs.writeFileSync(path.join(out,'vector-comparison-metrics.json'),JSON.stringify(metrics,null,2));
 console.log(metrics);
})().catch(e=>{console.error(e);process.exitCode=1});
