/* Project selection screen: no implicit project creation or destructive actions. */
const grid=document.getElementById('projectsGrid');
const status=document.getElementById('libraryStatus');
const search=document.getElementById('projectSearch');
const dialog=document.getElementById('createDialog');
let projects=[], loading=false;
const shortDate=t=>{if(!t)return 'Non modifié';try{return new Intl.DateTimeFormat('fr-FR',{day:'numeric',month:'short',year:'numeric'}).format(new Date(Number(t)*1000))}catch{return 'Date indisponible'}};
const openProject=id=>{if(!/^web-[a-f0-9]{12}$/.test(id))return;window.location.assign('/localaiweb/editor?id='+encodeURIComponent(id))};
function card(p,index){
 const button=document.createElement('button');button.type='button';button.className='card';button.setAttribute('aria-label','Ouvrir le projet '+String(p.name||'Sans nom'));
 const cover=document.createElement('div');cover.className='card-art';
 const shape=document.createElement('div');shape.className='art-shape';
 const ring=document.createElement('div');ring.className='art-ring';
 const caption=document.createElement('span');caption.className='art-caption';caption.textContent=p.project_kind==='pro'?'ENTREPRISE · PRO':p.template==='cinematic3d'?'EXPÉRIENCE 3D':'PROJET LIBRE';
 const thumbnail=document.createElement('img');
 thumbnail.className='project-thumbnail';
 thumbnail.alt='';
 thumbnail.loading='lazy';
 thumbnail.src='/api/web/project/thumbnail?id='+encodeURIComponent(p.id);
 thumbnail.onload=()=>cover.classList.add('has-thumbnail');
 thumbnail.onerror=()=>thumbnail.remove();
 cover.append(shape,ring,thumbnail,caption);
 const body=document.createElement('div');body.className='card-body';
 const name=document.createElement('span');name.className='card-name';name.textContent=p.name||'Sans nom';
 const meta=document.createElement('div');meta.className='card-meta';
 const state=document.createElement('span');state.className='card-state';state.textContent=p.status==='published'?'● Publié':'● Projet local';
 const date=document.createElement('span');date.textContent='Modifié le '+shortDate(p.updated_at);
 meta.append(state,date);body.append(name,meta);
 button.append(cover,body);button.addEventListener('click',()=>openProject(p.id));return button;
}
function render(){
 const q=search.value.toLocaleLowerCase('fr').trim();
 const matching=projects.filter(p=>(p.name||'').toLocaleLowerCase('fr').includes(q));
 const libre=matching.filter(p=>p.project_kind!=='pro');
 const pro=matching.filter(p=>p.project_kind==='pro');
 const libreAll=projects.filter(p=>p.project_kind!=='pro').length;
 const proAll=projects.filter(p=>p.project_kind==='pro').length;
 document.getElementById('projectsCount').textContent='('+libreAll+')';
 document.getElementById('proProjectsCount').textContent='('+proAll+')';
 const proGrid=document.getElementById('proProjectsGrid');
 for(const [target,items,kind,total] of [[grid,libre,'libre',libreAll],[proGrid,pro,'pro',proAll]]){
   target.replaceChildren();
   if(!items.length){
     const empty=document.createElement('div');empty.className='empty';
     const title=document.createElement('strong');
     title.textContent=q?'Aucun résultat dans cette catégorie':
       kind==='pro'?'Aucun projet Pro pour le moment':'Votre première création vous attend';
     const detail=document.createElement('span');
     detail.textContent=q?'Essayez une autre recherche.':
       kind==='pro'?'Utilise « Créer depuis une carte » pour démarrer.':
       'Clique sur « Nouveau projet » pour commencer.';
     empty.append(title,detail);target.append(empty);
   }else items.forEach((p,i)=>target.append(card(p,i)));
 }
}
async function loadProjects(){
 status.textContent='Chargement de vos projets…';
 try{
  const res=await fetch('/api/web/projects',{cache:'no-store'}),data=await res.json();
  if(!res.ok||data.error)throw Error(data.error||'Liste inaccessible');
  projects=Array.isArray(data.projects)?data.projects:[];
  projects.sort((a,b)=>Number(b.updated_at||0)-Number(a.updated_at||0));
  status.textContent='';render();
 }catch(e){status.textContent='Impossible de charger les projets : '+e.message;}
}
document.getElementById('createProject').addEventListener('click',()=>{
 document.getElementById('createError').textContent='';
 document.getElementById('projectName').value='';
 dialog.showModal();document.getElementById('projectName').focus();
});
document.getElementById('cancelProject').addEventListener('click',()=>dialog.close());
document.getElementById('createForm').addEventListener('submit',async e=>{
 e.preventDefault();if(loading)return;
 const name=document.getElementById('projectName').value.trim();
 if(!name){document.getElementById('createError').textContent='Donnez un nom au projet.';return;}
 loading=true;const button=document.getElementById('confirmProject');button.disabled=true;button.textContent='Création…';
 try{
   const res=await fetch('/api/web/project/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,template:'default'})});
   const result=await res.json();
   if(!res.ok||result.error||!result.project?.id)throw Error(result.error||'Création impossible');
   openProject(result.project.id);
 }catch(error){document.getElementById('createError').textContent=error.message;}
 finally{loading=false;button.disabled=false;button.textContent='Créer mon projet ↗';}
});
search.addEventListener('input',render);
loadProjects();