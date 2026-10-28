/* Client, project, quotation and invoice cockpit: local operations only. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const clientFields={name:'crmName',stage:'crmStage',email:'crmEmail',
 phone:'crmPhone',address:'crmAddress',siret:'crmSiret',
 contact_name:'crmContact',notes:'crmNotes',next_contact:'crmNextContact'};
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
const formatDate=value=>{
  const date=String(value||'').split('-');
  return date.length===3?date[2]+'/'+date[1]+'/'+date[0]:String(value||'');
};
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
 const due=record.next_contact?node('small','due-tag','Prochaine relance · '+formatDate(record.next_contact)):null;
 const controls=node('div','card-actions');
 const edit=node('button','','Modifier');edit.type='button';edit.onclick=()=>open(record);
 controls.append(edit);
 for(const p of record.projects||[]){
  const link=node('a','',p.name||'Ouvrir le site');link.href='/localaiweb/editor?id='+encodeURIComponent(p.id);
  controls.append(link);
  const audit=node('button','','Audit du site');
  audit.type='button';audit.title='Vérifier automatiquement la qualité technique du site';
  audit.addEventListener('click',()=>showAudit(p.id,p.name));
  controls.append(audit);
  const sale=node('a','','Devis / facture');
  sale.href='/localaiweb/vente?id='+encodeURIComponent(p.id);controls.append(sale);
 }
 card.append(tag,name,addr,number);
 if(due)card.append(due);
 card.append(controls);
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
function renderFollowups(){
 const box=$('followupsGrid');box.replaceChildren();
 const due=state.followups_due||[],upcoming=state.followups_upcoming||[];
 $('metricDue').textContent=due.length;
 const all=[...due.map(x=>({...x,priority:true})),...upcoming.map(x=>({...x,priority:false}))];
 if(!all.length){
   box.append(node('div','empty','Aucune relance à effectuer. Ajoute une date de relance à une fiche client pour organiser ton suivi.'));
   return;
 }
 for(const task of all){
   const row=node('div','followup-row'+(task.priority?' overdue':''));
   const detail=node('div','followup-detail');
   detail.append(node('strong','',task.name));
   detail.append(node('small','',(task.priority?'À contacter · ':'À venir · ')+formatDate(task.due)));
   const button=node('button','','Ouvrir la fiche ↗');button.type='button';
   const record=state.clients.find(c=>c.id===task.id);
   button.onclick=()=>{if(record)open(record)};
   row.append(detail,button);box.append(row);
 }
}
async function showAudit(projectId,projectName){
 const modal=$('auditDialog');
 $('auditTitle').textContent='Audit · '+(projectName||'Site');
 $('auditScore').textContent='—';$('auditVerdict').textContent='Analyse en cours';
 $('auditFeedback').textContent='Analyse du code, des liens et des critères de base…';
 $('auditChecks').replaceChildren();
 $('auditEditor').href='/localaiweb/editor?id='+encodeURIComponent(projectId);
 modal.showModal();
 try{
   const report=await api('/api/web/preflight?id='+encodeURIComponent(projectId));
   $('auditScore').textContent=String(report.score??'—')+' / 100';
   const status=report.ok?'Contrôles automatiques réussis':'Corrections nécessaires avant publication';
   $('auditVerdict').textContent=status;
   const count=(report.checks||[]).filter(check=>check.ok).length;
   $('auditFeedback').textContent=count+'/'+(report.checks||[]).length+' vérifications validées · '+(report.file_count||0)+' fichiers';
   for(const check of report.checks||[]){
     const row=node('div','audit-check'+(check.ok?' passed':' failed'));
     const title=node('strong','',(check.ok?'✓ ':'! ')+check.label);
     row.append(title);
     if(check.note)row.append(node('small','',check.note));
     $('auditChecks').append(row);
   }
   if(!(report.checks||[]).length)$('auditChecks').append(node('div','empty','Aucun contrôle automatique disponible.'));
 }catch(error){
   $('auditFeedback').textContent='Impossible de vérifier ce projet : '+error.message;
   $('auditVerdict').textContent='Audit non exécuté';
 }
}
$('auditClose').addEventListener('click',()=>$('auditDialog').close());
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
 renderClients();renderUnlinked();renderFollowups();
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
function exportClients(){
 const rows=state.clients||[];
 if(!rows.length){status('Aucune fiche client à exporter.');return}
 const columns=[["name","Entreprise"],["contact_name","Contact"],["stage","Étape"],
  ["next_contact","Prochaine relance"],["email","Courriel"],["phone","Téléphone"],
  ["address","Adresse"],["siret","SIRET"],["notes","Notes internes"]];
 const safe=value=>{
   let str=String(value??'').replace(/\r\n?/g,'\n');
   // Prevent spreadsheet formula injection in external spreadsheet software.
   if(/^[\s]*[=+@-]/.test(str)||str.startsWith('\t'))str="'"+str;
   return '"'+str.replace(/"/g,'""')+'"';
 };
 const lines=[columns.map(([,label])=>safe(label)).join(';')];
 for(const client of rows)lines.push(columns.map(([key])=>safe(client[key])).join(';'));
 const csv='\ufeff'+lines.join('\r\n')+'\r\n';
 const href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
 const anchor=document.createElement('a');anchor.href=href;
 anchor.download='LocalAiWeb-clients-'+new Date().toISOString().slice(0,10)+'.csv';
 document.body.append(anchor);anchor.click();anchor.remove();
 setTimeout(()=>URL.revokeObjectURL(href),2000);
 status(rows.length+' fiche(s) exportée(s) en CSV sur ton ordinateur. Aucun envoi réseau.');
}
$('exportClients').addEventListener('click',exportClients);
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
