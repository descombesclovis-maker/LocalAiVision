/* FORMA sales tool: estimates only until legal/customer data confirmed. */
(()=>{
 const $=id=>document.getElementById(id);
 const params=new URLSearchParams(location.search),projectId=params.get('id')||'';
 if(!/^web-[0-9a-f]{12}$/.test(projectId)){
  $('projectLabel').textContent='Identifiant de projet manquant. Reviens à la bibliothèque.';
  return;
 }
 $('returnEditor').href='/localaiweb/editor?id='+encodeURIComponent(projectId);
 const currency=value=>Number(value||0).toLocaleString('fr-FR',{
   style:'currency',currency:'EUR',minimumFractionDigits:2});
 const selected=new Map();
 let estimate=null;
 async function api(url,body){
  const resp=await fetch(url,body===undefined?{cache:'no-store'}:{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)});
  let result={};try{result=await resp.json()}catch{}
  if(!resp.ok||result.error)throw Error(result.error||'HTTP '+resp.status);
  return result;
 }
 function update(){
   const total=[...selected.values()].reduce((sum,item)=>sum+Number(item.subtotal_eur),0);
   $('estimatedTotal').textContent=currency(total);
 }
 function line(item){
  const row=document.createElement('label');row.className='line';
  const check=document.createElement('input');check.type='checkbox';check.checked=true;
  check.addEventListener('change',()=>{
    if(check.checked)selected.set(item.id,item);else selected.delete(item.id);
    update();
  });
  const body=document.createElement('span');body.textContent=item.label;
  const small=document.createElement('small');
  small.textContent='Base indicative : '+currency(item.market_eur)+' · Remise : '+item.discount_pct+' %';
  body.append(small);
  const price=document.createElement('strong');price.textContent=currency(item.subtotal_eur);
  row.append(check,body,price);
  return row;
 }
 async function load(){
  try{
   const [data,project]=await Promise.all([
     api('/api/web/sales/estimate?id='+encodeURIComponent(projectId)),
     api('/api/web/project?id='+encodeURIComponent(projectId))]);
   estimate=data;
   const meta=project.project||{};
   $('projectLabel').textContent='Projet « '+(meta.name||'Sans nom')+' » · '+(meta.project_kind==='pro'?'Pro':'Libre');
   const business=meta.business||{};
   $('customerName').value=business.name||'';
   $('customerAddress').value=business.address||'';
   $('customerSiret').value=business.official_registry?.siret||'';
   if(meta.deployment?.custom_domain)$('domainName').value=meta.deployment.custom_domain;
   if(meta.deployment?.vercel_target)$('vercelProject').value=meta.deployment.vercel_target;
   $('lineItems').replaceChildren();
   for(const item of data.items){
     selected.set(item.id,item);
     $('lineItems').append(line(item));
   }
   update();
   $('quoteNotice').textContent=data.notice;
  }catch(err){
   $('projectLabel').textContent='Impossible de charger le projet : '+err.message;
  }
 }
 function sellerData(){
   return {name:$('sellerName').value.trim(),siret:$('sellerSiret').value.trim(),
     address:$('sellerAddress').value.trim(),legal_form:$('legalForm').value,
     capital:$('sellerCapital').value.trim(),vat_mode:$('vatMode').value,
     vat_number:$('sellerVat').value.trim(),payment_details:$('paymentDetails').value.trim(),
     late_penalty_rate:$('latePenaltyRate').value.trim()};
 }
 function customerData(){
   return {name:$('customerName').value.trim(),address:$('customerAddress').value.trim(),
     siret:$('customerSiret').value.trim(),email:$('customerEmail').value.trim(),
     type:$('customerType').value};
 }
 $('issueQuote').addEventListener('click',async()=>{
   const button=$('issueQuote'),area=$('quoteFeedback');
   if(!estimate||!selected.size){area.textContent='Aucune prestation identifiée. Génère d’abord le site.';return}
   button.disabled=true;area.textContent='Préparation du devis…';
   try{
     const seller=sellerData(),customer=customerData();
     if(!seller.name||!seller.siret||!customer.name||!customer.address){
       throw Error('Renseigne les identités réelles du prestataire et du client avant de créer le devis.');
     }
     const total=currency([...selected.values()].reduce((sum,item)=>sum+Number(item.subtotal_eur),0));
     if(!window.confirm('Créer un devis commercial numéroté pour '+customer.name+
         ' ?\\nMontant HT estimé : '+total+
         '\\nLe client devra accepter le devis. Aucun paiement ou envoi ne sera déclenché.'))return;
     const result=await api('/api/web/crm/quote/create',{
       project_id:projectId,seller,customer,items:[...selected.keys()],
       valid_days:Number($('quoteValidDays').value),confirmed:true});
     area.replaceChildren();
     const strong=document.createElement('strong');strong.textContent='Devis '+result.quote_number+' enregistré · '+currency(result.total_eur);
     const link=document.createElement('a');link.href=result.download;link.target='_blank';link.rel='noopener noreferrer';
     link.textContent='Ouvrir le devis PDF ↗';
     area.append(strong,document.createElement('br'),link);
   }catch(err){area.textContent='Devis non créé : '+err.message}
   finally{button.disabled=false}
 });
 $('invoiceForm').addEventListener('submit',async event=>{
  event.preventDefault();
  if(!estimate || !selected.size)return;
  const btn=$('issueInvoice'),area=$('invoiceFeedback');
  btn.disabled=true;area.textContent='Préparation de la facture définitive…';
  try{
   const seller={
    name:$('sellerName').value.trim(),siret:$('sellerSiret').value.trim(),
    address:$('sellerAddress').value.trim(),legal_form:$('legalForm').value,
    capital:$('sellerCapital').value.trim(),vat_mode:$('vatMode').value,
    vat_number:$('sellerVat').value.trim(),payment_details:$('paymentDetails').value.trim(),
    late_penalty_rate:$('latePenaltyRate').value.trim()
   };
   const customer={
    name:$('customerName').value.trim(),address:$('customerAddress').value.trim(),
    siret:$('customerSiret').value.trim(),email:$('customerEmail').value.trim(),
    type:$('customerType').value
   };
   if(!$('invoiceApproval').checked)throw Error('Validation des mentions et de la prestation requise.');
   const amount=currency([...selected.values()].reduce((sum,x)=>sum+Number(x.subtotal_eur),0));
   if(!window.confirm('Émettre une FACTURE définitive et numérotée pour '+customer.name+
     ' ?\nMontant HT : '+amount+
     '\nUne facture émise ne peut pas être supprimée ou renumérotée.'))return;
   const result=await api('/api/web/invoice/issue',{
    id:projectId,seller,customer,items:[...selected.keys()],
    service_date:$('serviceDate').value,due_days:Number($('dueDays').value),
    accepted:true
   });
   area.replaceChildren();
   const header=document.createElement('strong');
   header.textContent='Facture '+result.invoice_number+' émise · '+currency(result.total_eur);
   const space=document.createElement('br');
   const link=document.createElement('a');link.href=result.download;
   link.textContent='Ouvrir / enregistrer la facture PDF FORMA ↗';
   link.target='_blank';link.rel='noopener';
   area.append(header,space,link);
   $('invoiceApproval').checked=false;
  }catch(err){area.textContent='Émission impossible : '+err.message}
  finally{btn.disabled=false}
 });
 $('domainForm').addEventListener('submit',async event=>{
   event.preventDefault();
   const node=$('domainFeedback'),btn=event.currentTarget.querySelector('button');
   btn.disabled=true;node.textContent='Rattachement du domaine à Vercel…';
   try{
     if(!window.confirm('Confirmer la propriété ou le droit d’administration de ce domaine ?'))return;
     const result=await api('/api/web/domain/attach',{
       id:projectId,domain:$('domainName').value.trim(),
       vercel_project:$('vercelProject').value.trim()});
     node.replaceChildren();
     const msg=document.createElement('p');msg.textContent=result.notice;node.append(msg);
     const pre=document.createElement('pre');pre.textContent=result.dns_instructions||
       'Consulte la configuration DNS du projet dans Vercel.';
     pre.style.whiteSpace='pre-wrap';pre.style.fontSize='11px';
     node.append(pre);
   }catch(err){node.textContent='Domaine non rattaché : '+err.message}
   finally{btn.disabled=false}
 });
 load();
})();
