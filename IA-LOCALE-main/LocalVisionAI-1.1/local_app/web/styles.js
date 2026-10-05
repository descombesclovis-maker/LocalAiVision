function chooseStyleWorkflow(task,rows,manualId,style,hasImage,preview,promptText='',hasVideo=false){
 const eligible=rows.filter(w=>task==='video'?['video','video-heavy'].includes(w.kind):task==='motion'?w.kind==='motion':w.kind===task);
 const manual=eligible.find(w=>w.id===manualId);if(manual)return manual;
 const recorded=eligible.find(w=>w.id===preview?.workflow);if(recorded)return recorded;
 const text=String(promptText||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const wantsAnime=/\b(anime|manga|cel[- ]?shad|japan(?:ese)? animation|animagine)\b/.test(text);
 const wantsPhoto=/\b(photo|photoreal|realiste|realistic|photographie|portrait|camera|objectif|lens)\b/.test(text);
 let preferred=[];
 if(task==='image'){
   if(wantsAnime)preferred=['Reserved Companion Anime.json','text to image sdxl.json','Text to image flux.json'];
   else if(wantsPhoto)preferred=['text to image sdxl.json','Text to image flux.json','Reserved Companion Anime.json'];
   else preferred=[...(style?.preferred||[]),'text to image sdxl.json','Reserved Companion Anime.json','Text to image flux.json'];
 }else if(task==='retouch')preferred=['Retouche SDXL masque.json'];
 else if(task==='motion'||hasVideo)preferred=['Video Motion VACE 1.3B.json'];
 else if(hasImage)preferred=['Image to video wan.json','Video Wan texte.json','Reserved Companion Anime Video.json'];
 else if(wantsAnime)preferred=['Reserved Companion Anime Video.json','Video Wan texte.json'];
 else preferred=['Video Wan texte.json','Reserved Companion Anime Video.json'];
 const ranked=preferred.map(id=>eligible.find(w=>w.id===id)).filter(Boolean);
 return ranked.find(w=>w.ready===true)||eligible.find(w=>w.ready===true)||ranked[0]||eligible[0]||null;
}
if(typeof module!=='undefined')module.exports={chooseStyleWorkflow};
