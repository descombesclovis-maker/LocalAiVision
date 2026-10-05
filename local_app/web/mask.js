let maskPainted=false;
let maskUndo=[];
let maskDrawing=false;
let maskLast=null;
function maskCanvas(){return document.querySelector('#maskCanvas')}
async function attachImage(file){
 const raw=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file)});
 const img=await new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(new Error('Image illisible'));i.src=raw});
 const w=Math.max(8,Math.round(img.naturalWidth/8)*8),h=Math.max(8,Math.round(img.naturalHeight/8)*8);
 const source=document.createElement('canvas');source.width=w;source.height=h;source.getContext('2d').drawImage(img,0,0,w,h);
 imageData={data:source.toDataURL('image/png'),name:file.name.replace(/\.[^.]*$/,'')+'.png',width:w,height:h};
 const canvas=maskCanvas();canvas.width=w;canvas.height=h;maskPainted=false;maskUndo=[];
 document.querySelector('#maskSource').src=imageData.data;
 document.querySelector('#imageName').textContent=file.name+' · '+w+' × '+h;
 document.querySelector('#attachment').classList.remove('hidden');
 document.querySelector('#maskState').textContent='Aucune zone peinte';
 if(w!==img.naturalWidth||h!==img.naturalHeight)toast('Dimensions ajustées au multiple de 8 le plus proche pour la retouche.');
}
function exportMask(){
 if(!maskPainted)return null;
 const src=maskCanvas(), out=document.createElement('canvas');out.width=src.width;out.height=src.height;
 const ctx=out.getContext('2d');ctx.fillStyle='black';ctx.fillRect(0,0,out.width,out.height);
 const copy=document.createElement('canvas');copy.width=src.width;copy.height=src.height;const c=copy.getContext('2d');
 c.drawImage(src,0,0);c.globalCompositeOperation='source-in';c.fillStyle='white';c.fillRect(0,0,copy.width,copy.height);
 ctx.drawImage(copy,0,0);return out.toDataURL('image/png');
}
function setupMaskEditor(){
 const canvas=maskCanvas();
 document.querySelector('#editMask').onclick=()=>document.querySelector('#maskModal').classList.remove('hidden');
 document.querySelector('#closeMask').onclick=()=>document.querySelector('#maskModal').classList.add('hidden');
 document.querySelector('#clearMask').onclick=()=>{canvas.getContext('2d').clearRect(0,0,canvas.width,canvas.height);maskPainted=false;maskUndo=[];document.querySelector('#maskState').textContent='Aucune zone peinte'};
 document.querySelector('#undoMask').onclick=()=>{const prev=maskUndo.pop();if(!prev)return;canvas.getContext('2d').putImageData(prev.data,0,0);maskPainted=prev.painted;document.querySelector('#maskState').textContent=maskPainted?'Masque prêt':'Aucune zone peinte'};
 document.querySelector('#removeImage').onclick=()=>{imageData=null;maskPainted=false;maskUndo=[];document.querySelector('#imageFile').value='';document.querySelector('#attachment').classList.add('hidden')};
 const point=e=>{const r=canvas.getBoundingClientRect();return {x:(e.clientX-r.left)*canvas.width/r.width,y:(e.clientY-r.top)*canvas.height/r.height}};
 const draw=e=>{if(!maskDrawing)return;const p=point(e),ctx=canvas.getContext('2d');ctx.strokeStyle='#fa7354';ctx.fillStyle='#fa7354';ctx.lineWidth=Number(document.querySelector('#brushSize').value)*canvas.width/canvas.getBoundingClientRect().width;ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath();ctx.moveTo(maskLast.x,maskLast.y);ctx.lineTo(p.x,p.y);ctx.stroke();ctx.beginPath();ctx.arc(p.x,p.y,ctx.lineWidth/2,0,2*Math.PI);ctx.fill();maskLast=p;maskPainted=true;document.querySelector('#maskState').textContent='Masque prêt'};
 canvas.onpointerdown=e=>{if(!imageData)return;e.preventDefault();maskUndo.push({data:canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height),painted:maskPainted});if(maskUndo.length>5)maskUndo.shift();maskDrawing=true;maskLast=point(e);canvas.setPointerCapture(e.pointerId);draw(e)};
 canvas.onpointermove=draw;
 canvas.onpointerup=canvas.onpointercancel=()=>{maskDrawing=false;maskLast=null};
}
