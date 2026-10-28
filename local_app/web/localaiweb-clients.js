/* Client, project, quotation and invoice cockpit: local operations only. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const clientFields={name:'crmName',stage:'crmStage',email:'crmEmail',
 phone:'crmPhone',address:'crmAddress',siret:'crmSiret',
 contact_name:'crmContact',notes:'crmNotes'};
const dialog=$('clientDialog'),grid=$('clientGrid');
let state={clients:[],quotes:[],invoices:[],unlinked_pro_projects:[],projects_count:0},projects=[];
let editing=null,saving=false;
const status=t=>{$('crmFeedback').textContent=t};
const api=async(url,body)=>{
 const res=await fetch(url,body===undefined?{cache:'no-store'}:{
  method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 let data={};try{data=await res.json()}catch{}
 if(!res.ok||data.error)throw Error(data.error||'Erreur HTTP '+res.status);
 return data;
};
const euro=x=>Number(x||0).toLocaleString('fr-FR',{style:'currency',currency:'EUR'});
const node=(tag,cls,text)=>{
 const el=document.createElement(tag);if(cls)el.className=cls;
 if(text!==undefined)el.textContent=text;return el;
};
function setValues(record={}){
 for(const [key,id] of Object.entries(clientFields))$(id).value=record[key]||'';
 $('crmProject').replaceChildren(new Option('Aucun projet associé',''));
 for(const project of projects){
  $('crmProject').add(new Option(project.name||'Projet',project.id));
 }
 $('crmProject').value=(record.project_ids||[])[0]||record.project_id||'';
 $('clientError').textContent='';
}
function open(record={},projectId=''){
 editing=record.id||null;
 setValues({...record,project_id:projectId||record.project_id});
 $('clientDialogTitle').textContent=editing?'Modifier la fiche client':'Nouvelle fiche client';
 dialog.showModal();$('crmName').focus();
}
function makeCard(record){
 const card=node('article','client-card');
 const tag=node('span','tag',state.stage_labels?.[record.stage]||record.stage||'Prospect');
 const name=node('strong','',record.name);
 const addr=node('p','',record.address||'Coordonnées à renseigner');
 const projectCount=(record.projects||[]).length;
 const number=node('small','',projectCount+' projet'+(projectCount>1?'s':'')+' associé'+(projectCount>1?'s':''));
 const controls=node('div','card-actions');
 const edit=node('button','','Modifier');edit.type='button';edit.onclick=()=>open(record);
 controls.append(edit);
 for(const p of record.projects||[]){
  const link=node('a','',p.name||'Ouvrir le site');link.href='/localaiweb/editor?id='+encodeURIComponent(p.id);
  controls.append(link);
  const sale=node('a','','Devis / facture');
  sale.href='/localaiweb/vente?id='+encodeURIComponent(p.id);controls.append(sale);
 }
 card.append(tag,name,addr,number,controls);
 return card;
}
function renderClients(){
 const q=$('clientSearch').value.toLocaleLowerCase('fr').trim();
 const rows=state.clients.filter(c=>
  [c.name,c.address,c.email,c.siret,c.contact_name].some(v=>String(v||'').toLocaleLowerCase('fr').includes(q)));
 grid.replaceChildren();
 if(!rows.length){
  grid.append(node('div','empty',q?'Aucun client pour cette recherche.':'Aucun client. Crée une fiche ou sélectionne une entreprise sur la carte.'));
  return;
 }
 for(const record of rows)grid.append(makeCard(record));
}
function renderUnlinked(){
 const box=$('unlinkedGrid');box.replaceChildren();
 const rows=state.unlinked_pro_projects||[];
 if(!rows.length){box.append(node('div','empty','Tous les projets Pro existants sont rattachés à une fiche client.'));return}
 for(const project of rows){
  const row=node('div','unlinked-row');
  row.append(node('strong','',project.name));
  const btn=node('button','','Rattacher à un client');btn.type='button';
  btn.onclick=()=>open({name:project.business?.name||project.name,
                        address:project.business?.address||'',email:project.business?.email||'',
                        phone:project.business?.phone||''},project.id);
  row.append(btn);box.append(row);
 }
}
function renderDocuments(box,rows,kind){
 box.replaceChildren();
 if(!rows.length){box.append(node('div','empty',kind==='quote'?'Aucun devis enregistré. Crée un devis depuis le projet.':'Aucune facture émise depuis ce nouvel espace.'));return}
 for(const row of rows){
  const element=node('div','document-row');
  const label=node('div','');
  const number=row.quote_number||row.invoice_number;
  label.append(node('strong','',number+' · '+euro(row.total_eur)));
  label.append(node('small','',kind==='quote'?(row.status==='issued_proposal'?'Proposition à faire accepter':'Statut à vérifier'):(row.status==='issued_unpaid'?'Émise · paiement non confirmé':'Émise')));
  const link=node('a','','PDF ↗');link.href=row.download||('/api/web/crm/quote/file?number='+encodeURIComponent(number));link.target='_blank';link.rel='noopener noreferrer';
  element.append(label,link);box.append(element);
 }
}
function render(){
 $('metricClients').textContent=state.clients.length;
 $('metricQuotes').textContent=state.quotes.length;
 $('metricInvoices').textContent=state.invoices.length;
 $('metricProjects').textContent=state.projects_count;
 renderClients();renderUnlinked();
 renderDocuments($('quoteRows'),state.quotes,'quote');
 renderDocuments($('invoiceRows'),state.invoices,'invoice');
}
async function load(){
 status('Chargement de ton activité commerciale…');
 try{
  const [result,projectResult]=await Promise.all([
   api('/api/web/crm/overview'),api('/api/web/projects')]);
  state=result;projects=projectResult.projects||[];
  render();status('Registre privé à jour · aucun envoi automatique.');
 }catch(e){status('Impossible de charger les données commerciales : '+e.message)}
}
$('newClient').onclick=()=>open();
$('clientSearch').addEventListener('input',renderClients);
$('closeClientDialog').onclick=()=>dialog.close();
$('cancelClient').onclick=()=>dialog.close();
$('clientForm').addEventListener('submit',async event=>{
 event.preventDefault();if(saving)return;
 const body={};
 if(editing)body.id=editing;
 for(const [key,id] of Object.entries(clientFields))body[key]=$(id).value.trim();
 if($('crmProject').value)body.project_id=$('crmProject').value;
 if(!body.name){$('clientError').textContent="Le nom de l'entreprise est obligatoire.";return}
 saving=true;$('saveClient').disabled=true;$('saveClient').textContent='Enregistrement…';
 try{
  await api('/api/web/crm/client/upsert',body);
  dialog.close();await load();
 }catch(e){$('clientError').textContent='Fiche non enregistrée : '+e.message}
 finally{saving=false;$('saveClient').disabled=false;$('saveClient').textContent='Enregistrer la fiche'}
});
load();
})();
