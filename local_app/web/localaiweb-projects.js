/* Reliable LocalAiWeb project library: saved projects + real generation state. */
const grid=document.getElementById('projectsGrid');
const status=document.getElementById('libraryStatus');
const search=document.getElementById('projectSearch');
const dialog=document.getElementById('createDialog');
let projects=[],loading=false,projectFetching=false,activeJobs=new Map(),previousActive=new Set();
const shortDate=t=>{if(!t)return 'Non modifié';try{return new Intl.DateTimeFormat('fr-FR',{day:'numeric',month:'short',year:'numeric'}).format(new Date(Number(t)*1000))}catch{return 'Date indisponible'}};
const validProject=id=>/^web-[a-f0-9]{12}$/.test(id||'');
const openProject=id=>{
 if(!validProject(id)){status.textContent='Ce projet possède un identifiant invalide. Il n’a pas été ouvert.';return}
 // Direct, stable deep link; browser Back always returns to this library.
 window.location.assign('/localaiweb/editor?id='+encodeURIComponent(id));
};
async function json(url,body,timeoutMs=12000){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
 try{
  const options=body===undefined?{cache:'no-store'}:{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
  };
  const res=await fetch(url,{...options,signal:controller.signal});
  let data={};try{data=await res.json()}catch{}
  if(!res.ok||data.error)throw Error(data.error||'Erreur HTTP '+res.status);
  return data;
 }catch(error){
  if(error.name==='AbortError')throw Error('Le serveur ne répond pas. Vérifie LocalAI Studio et réessaie.');
  throw error;
 }finally{clearTimeout(timer)}
}
function card(p,index){
 const wrapper=document.createElement('article');wrapper.className='card';
 const button=document.createElement('button');button.type='button';button.className='card-open';
 button.setAttribute('aria-label','Ouvrir le projet '+String(p.name||'Sans nom'));
 button.title='Ouvrir le projet et reprendre son historique';
 const cover=document.createElement('div');cover.className='card-art';
 const shape=document.createElement('img');shape.className='project-illustration';
 shape.src='/assets/presentation/web-1600.webp';shape.alt='Photographie illustrative d’un espace de création numérique';shape.loading='lazy';
 const ring=document.createElement('div');ring.className='art-ring';
 const caption=document.createElement('span');caption.className='art-caption';
 caption.textContent='Photographie illustrative';
 const thumbnail=document.createElement('img');thumbnail.className='project-thumbnail';thumbnail.alt='';
 thumbnail.loading='lazy';thumbnail.src='/api/web/project/thumbnail?id='+encodeURIComponent(p.id)+'&v='+encodeURIComponent(p.updated_at||0);
 thumbnail.onload=()=>{cover.classList.add('has-thumbnail');shape.hidden=true;caption.textContent='Aperçu du projet'};
 thumbnail.onerror=()=>thumbnail.remove();
 cover.append(shape,ring,thumbnail,caption);
 const body=document.createElement('div');body.className='card-body';
 const name=document.createElement('span');name.className='card-name';name.textContent=p.name||'Sans nom';
 const meta=document.createElement('div');meta.className='card-meta';
 const live=activeJobs.get(p.id);
 const state=document.createElement('span');state.className='card-state';
 state.textContent=live?'◌ Création en cours':p.status==='published'?'● Publié':'● Projet enregistré';
 if(live){state.classList.add('is-generating');button.classList.add('is-generating')}
 const date=document.createElement('span');date.textContent=live?String(live.detail||'Codex crée le site…').slice(0,58):
  'Modifié le '+shortDate(p.updated_at);
 meta.append(state,date);body.append(name,meta);
 button.append(cover,body);
 button.addEventListener('click',()=>{
  if(!validProject(p.id)){status.textContent='Impossible d’ouvrir ce projet : identifiant invalide.';return}
  button.classList.add('opening');button.setAttribute('aria-busy','true');
  openProject(p.id);
 });
 const menu=document.createElement('details');menu.className='project-context';
 const summary=document.createElement('summary');summary.textContent='…';
 summary.setAttribute('aria-label','Actions du projet '+String(p.name||'Sans nom'));
 const panel=document.createElement('div');panel.className='project-context-panel';
 const copy=document.createElement('button');copy.type='button';copy.textContent="Copier le prompt d'origine";
 copy.addEventListener('click',async()=>{
  try{
   const {project}=await json('/api/web/project?id='+encodeURIComponent(p.id));
   if(typeof project.original_prompt!=='string'||!project.original_prompt){
    status.textContent="Le prompt d’origine de ce projet n’a pas été conservé.";return;
   }
   await navigator.clipboard.writeText(project.original_prompt);
   status.textContent="Prompt d’origine copié.";menu.open=false;summary.focus();
  }catch(error){status.textContent='Copie impossible : '+error.message}
 });
 const remove=document.createElement('button');remove.type='button';remove.textContent='Supprimer le projet';
 remove.addEventListener('click',()=>{
  menu.open=false;pendingDeletion={id:p.id,name:p.name||'Sans nom',focus:summary};
  deleteName.textContent=pendingDeletion.name;deleteError.textContent='';
  deleteDialog.showModal();document.getElementById('cancelDeleteProject').focus();
 });
 panel.append(copy,remove);menu.append(summary,panel);wrapper.append(button,menu);
 return wrapper;
}
function emptyCard(kind,query){
 const empty=document.createElement('div');empty.className='empty';
 const title=document.createElement('strong');
 title.textContent=query?'Aucun résultat dans cette catégorie':
  kind==='pro'?'Aucun site client pour le moment':'Votre première création vous attend';
 const detail=document.createElement('span');
 detail.textContent=query?'Essaie une recherche plus courte.':
  kind==='pro'?'Crée un projet depuis la carte pour démarrer.':
  'Choisissez « Partir de votre idée » pour créer un site.';
 empty.append(title,detail);return empty;
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
 for(const [target,items,kind] of [[grid,libre,'libre'],[proGrid,pro,'pro']]){
  target.replaceChildren();
  if(!items.length)target.append(emptyCard(kind,q));
  else items.forEach((p,i)=>target.append(card(p,i)));
 }
}
function showRetry(message){
 status.replaceChildren();
 const text=document.createElement('span');text.textContent=message+' ';
 const button=document.createElement('button');button.id='retryProjects';
 button.type='button';button.textContent='Réessayer le chargement';
 button.addEventListener('click',()=>{void loadProjects()});
 status.append(text,button);
}
async function loadProjects(){
 if(projectFetching)return;
 projectFetching=true;
 status.textContent='Chargement de vos projets enregistrés…';
 try{
  const data=await json('/api/web/projects');
  if(!Array.isArray(data.projects))throw Error('Format de bibliothèque invalide.');
  projects=data.projects.filter(x=>x&&validProject(x.id));
  projects.sort((a,b)=>Number(b.updated_at||0)-Number(a.updated_at||0));
  status.textContent='';render();
 }catch(error){showRetry('Impossible de charger les projets : '+error.message)}
 finally{projectFetching=false}
}
async function refreshActive(){
 if(document.hidden)return;
 try{
  const data=await json('/api/web/generations/active',undefined,8000);
  const rows=Array.isArray(data.jobs)?data.jobs:[];
  const next=new Map(rows.filter(j=>validProject(j.id)).map(j=>[j.id,j]));
  const done=Array.from(previousActive).some(id=>!next.has(id));
  const changed=next.size!==activeJobs.size||
    Array.from(next).some(([id,job])=>activeJobs.get(id)?.detail!==job.detail);
  activeJobs=next;previousActive=new Set(next.keys());
  if(done)await loadProjects();
  else if(changed&&!document.querySelector('.project-context[open]')&&!deleteDialog.open)render();
 }catch{} // Temporary server error never erases saved library.
}
document.getElementById('createProject').addEventListener('click',()=>{
 document.getElementById('createError').textContent='';
 document.getElementById('projectName').value='';
 dialog.showModal();document.getElementById('projectName').focus();
});
document.getElementById('cancelProject').addEventListener('click',()=>dialog.close());
document.getElementById('createForm').addEventListener('submit',async event=>{
 event.preventDefault();if(loading)return;
 const name=document.getElementById('projectName').value.trim();
 if(!name){document.getElementById('createError').textContent='Donne un nom au projet.';return}
 loading=true;
 const button=document.getElementById('confirmProject');button.disabled=true;button.textContent='Création…';
 try{
  const result=await json('/api/web/project/create',{name,template:'default'},25000);
  if(!validProject(result.project?.id))throw Error('Le projet a été créé sans identifiant valide.');
  openProject(result.project.id);
 }catch(error){document.getElementById('createError').textContent=error.message}
 finally{loading=false;button.disabled=false;button.textContent='Créer mon projet'}
});
search.addEventListener('input',render);
document.addEventListener('keydown',event=>{
 if(event.key==='/'&&!event.ctrlKey&&!event.metaKey&&
    !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)){
   event.preventDefault();search.focus();
 }
});
document.getElementById('refreshProjects')?.addEventListener('click',()=>{void loadProjects()});
document.addEventListener('visibilitychange',()=>{if(!document.hidden){void loadProjects();void refreshActive()}});
window.addEventListener('pageshow',event=>{if(event.persisted){void loadProjects();void refreshActive()}});
void loadProjects();void refreshActive();
window.setInterval(()=>{void refreshActive()},5000);


// Separate modal and card button prevent card navigation from triggering deletion.
const deleteDialog=document.getElementById('deleteProjectDialog');
const deleteName=document.getElementById('deleteProjectName'),deleteError=document.getElementById('deleteProjectError');
let pendingDeletion=null,deleting=false;
document.getElementById('cancelDeleteProject').addEventListener('click',()=>deleteDialog.close());
deleteDialog.addEventListener('close',()=>{pendingDeletion?.focus?.focus();pendingDeletion=null});
document.getElementById('confirmDeleteProject').addEventListener('click',async()=>{
 if(deleting||!pendingDeletion||!validProject(pendingDeletion.id))return;
 const selected=pendingDeletion.id;deleting=true;
 const confirm=document.getElementById('confirmDeleteProject');confirm.disabled=true;
 try{
  await json('/api/web/project/delete',{id:selected});deleteDialog.close();
  await loadProjects();status.textContent='Projet supprimé.';
 }catch(error){deleteError.textContent=error.message}
 finally{deleting=false;confirm.disabled=false}
});
document.addEventListener('pointerdown',event=>{
 for(const menu of document.querySelectorAll('.project-context[open]'))if(!menu.contains(event.target))menu.open=false;
});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape')for(const menu of document.querySelectorAll('.project-context[open]')){menu.open=false;menu.querySelector('summary').focus()}
});
