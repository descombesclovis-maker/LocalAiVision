const assert=require('node:assert/strict');
const {chooseStyleWorkflow:choose}=require('../local_app/web/styles.js');
const styles=require('../local_app/web/styles.json');
const rows=[
 {id:'Text to image flux.json',kind:'image',ready:false},
 {id:'text to image sdxl.json',kind:'image',ready:true},
 {id:'Reserved Companion Anime.json',kind:'image',ready:true},
 {id:'Video Wan texte.json',kind:'video',ready:true},
 {id:'Reserved Companion Anime Video.json',kind:'video',ready:true},
 {id:'Image to video wan.json',kind:'video',ready:true},
 {id:'Video Motion VACE 1.3B.json',kind:'motion',ready:true},
 {id:'Retouche SDXL masque.json',kind:'retouch',ready:true}
];
assert.equal(choose('image',rows,null,styles[0],false,null,'portrait photo réaliste').id,'text to image sdxl.json');
assert.equal(choose('image',rows,'Reserved Companion Anime.json',styles[0],false,null,'photo réaliste').id,'Reserved Companion Anime.json');
assert.equal(choose('image',rows,null,styles[0],false,null,'personnage anime manga').id,'Reserved Companion Anime.json');
assert.equal(choose('video',rows,null,styles[0],false,null,'une vidéo de forêt').id,'Video Wan texte.json');
assert.equal(choose('video',rows,null,styles[0],true,null,'anime ce dessin').id,'Image to video wan.json');
assert.equal(choose('video',rows,null,styles[0],false,null,'animation anime manga').id,'Reserved Companion Anime Video.json');
assert.equal(choose('motion',rows,null,styles[0],true,null,'reprends ce mouvement',true).id,'Video Motion VACE 1.3B.json');
assert.equal(choose('retouch',rows,null,styles[0],true,null,'retouche').id,'Retouche SDXL masque.json');
assert.equal(choose('image',rows,null,styles[0],false,{workflow:'Text to image flux.json'},'').id,'Text to image flux.json');
const allReady=rows.map(r=>({...r,ready:true}));
assert.equal(choose('image',allReady,null,styles[3],false,null,'photo de ville').id,'text to image sdxl.json');
console.log('10 tests de choix automatique / manuel de workflow réussis.');
