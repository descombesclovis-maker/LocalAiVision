/* FORMA sales tool: estimates only until legal/customer data confirmed. */
(()=>{
 const $=id=>document.getElementById(id);
 const params=new URLSearchParams(location.search),projectId=params.get('id')||'';
 if(!/^web-[0-9a-f]{12}$/.test(projectId)){
  $('projectLabel').textContent='Identifiant de projet manquant. Reviens à la bibliothèque.';
  return;
 }
 const studioOrigin=location.hostname==='ventes.localhost'?location.protocol+'//127.0.0.1:'+location.port:location.origin;
 $('clientRecord').href=studioOrigin+'/localaiweb/clients';
 $('returnEditor').href=studioOrigin+'/localaiweb/editor?id='+encodeURIComponent(projectId);
 const currency=value=>Number(value||0).toLocaleString('fr-FR',{
   style:'currency',currency:'EUR',minimumFractionDigits:2});
 const selected=new Map();
 let estimate=null;
 async function api(url,body){
  const resp=await fetch(url,body===undefined?{cache:'no-store'}:{
    method:'POST',headers:{'Content-Type':'application/json','X-LocalAI-Sales':'1'},
    body:JSON.stringify(body)});
  let result={};try{result=await resp.json()}catch{}
  if(!resp.ok||result.error)throw Error(result.error||'HTTP '+resp.status);
  return result;
 }
 function update(){
   const total=[...selected.values()].reduce((sum,item)=>sum+Number(item.subtotal_eur),0);
   $('estimatedTotal').textContent=currency(total);
   $('margin').textContent=desk?.cost_ht==null?'Marge non calculée : renseigner le coût interne.':'Marge estimée sur la création : '+currency(total-Number(desk.cost_ht))+' HT'+(total?' ('+Math.round((total-Number(desk.cost_ht))*100/total)+' %)':'');
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
 $('discountPct').oninput=()=>{
   if(!estimate || !$('discountPct').checkValidity() || $('discountPct').value==='')return;
   const pct=Number($('discountPct').value);
   const checked=new Set(selected.keys());selected.clear();$('lineItems').replaceChildren();
   for(const base of estimate.items){
     const item={...base,discount_pct:pct,subtotal_eur:(Number(base.market_eur)*(1-pct/100)).toFixed(2)};
     const el=line(item);el.querySelector('input').checked=checked.has(item.id);
     if(checked.has(item.id))selected.set(item.id,item);
     $('lineItems').append(el);
   }
   update();
 };
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
 function showStep(){
   const links=[...document.querySelectorAll('.sales-steps a')];
   const active=links.find(a=>a.hash===location.hash)||links[0];
   for(const link of links){if(link===active)link.setAttribute('aria-current','step');else link.removeAttribute('aria-current')}
   for(const panel of document.querySelectorAll('[data-step]'))panel.hidden=panel.dataset.step!==active.hash.slice(1);
 }
 for(const link of document.querySelectorAll('.sales-steps a')){
   link.addEventListener('click',event=>{
     if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
     event.preventDefault();history.pushState(null,'',link.hash);showStep();window.scrollTo(0,0);
   });
 }
 window.addEventListener('hashchange',showStep);showStep();
 let desk=null;
 const titles={awaiting_site:'Génération à terminer',draft_site_ready:'Maquette prête à présenter',presentation_ready:'Présentation préparée',contacted:'Échange enregistré',quote_prepared:'Devis préparé'};
 function renderDesk(data){
   desk=data;$('salesState').textContent=titles[data.stage]||({accepted:'Accord vérifié',payment_pending:'Paiement en attente',paid:'Règlement vérifié',published:'Publication enregistrée',handover_complete:'Remise vérifiée',domain_pending:'Commande de domaine en cours',domain_completed:'Domaine enregistré'}[data.stage]||data.stage);
   $('overallStage').textContent=$('salesState').textContent;
   $('costHT').value=data.cost_ht??'';update();
   if(data.client_id)$('clientRecord').href=studioOrigin+'/localaiweb/clients?client='+encodeURIComponent(data.client_id);
   if(data.delivery)$('releaseStatus').textContent='Remise vérifiée : '+data.delivery.url;
   const pages=data.pages.length;
   $('pitch').textContent=data.ready?'Feuille de '+data.business+(data.city?' · '+data.city:'')+' · '+pages+' page(s) dans la maquette privée.':'Le dossier sera disponible après une génération réussie.';

   $('callSheet').hidden=!data.call_sheet.length;
   $('printScript').href='/api/web/sales/call-sheet.pdf?id='+projectId;
   $('scriptSections').replaceChildren(...data.call_sheet.map(([title,lines],i)=>{
     const block=document.createElement('details'),head=document.createElement('summary');
     block.open=i===1;head.textContent=title;block.append(head);
     for(const line of lines){const p=document.createElement('p');p.textContent=line;block.append(p)}
     return block;
   }));
   if(data.opposed)$('pitch').textContent='Opposition enregistrée. Ce contact ne doit plus être sollicité.';
   $('registryResult').textContent=data.registry?.matched?'Registre : '+data.registry.legal_name+' · '+data.registry.siren:(data.registry?.message||'Aucun rapprochement officiel confirmé.');
   $('factList').replaceChildren(...data.facts.map(f=>{
     const row=document.createElement('p'),remove=document.createElement('button');
     row.textContent=f.category+' · '+f.value+' ('+f.source+', '+f.day+') ';
     remove.type='button';remove.textContent='Retirer';
     remove.onclick=()=>action('withdraw_fact',{category:f.category});
     row.append(remove);return row;
   }));
   $('aiPitch').disabled=!data.ready;
   $('salesSummary').textContent=data.summary||'Montre les pages de la maquette, puis demande au client quel parcours compte le plus pour son activité.';
   $('salesSource').textContent='Origine de la fiche : '+data.source+(data.source_date?' · dossier créé le '+new Date(data.source_date*1000).toLocaleDateString('fr-FR'):'');
   $('demoSite').hidden=!data.ready;$('demoSite').href=studioOrigin+'/web-preview/'+projectId+'/index.html';
   $('prepareSale').disabled=!data.ready;$('verifyPhone').disabled=!data.ready||!data.phone||data.opposed;
   $('dial').hidden=!data.call_allowed;$('dial').removeAttribute('href');
   if(data.call_allowed)$('dial').href='tel:'+data.phone;
   $('salesPhone').textContent=data.opposed?'Opposition enregistrée · aucune relance':data.phone||'Numéro professionnel non renseigné';
   $('oppose').disabled=!data.ready||data.opposed||!data.client_id;
   $('callLog').querySelector('button').disabled=!data.call_allowed;
   document.querySelectorAll('.checkgrid input').forEach((el,i)=>el.checked=Boolean(data.checks?.[i]));
   $('serviceNeeds').textContent=data.service_needs.join(' · ');
   if(data.registration)$('offerDisplay').textContent=data.registration.domain+' · '+data.registration.state;
   $('salesHistory').replaceChildren(...data.events.slice(-3).reverse().map(e=>{
     const p=document.createElement('p');p.textContent=new Date(e.at*1000).toLocaleDateString('fr-FR')+' · '+(e.outcome||({oppose:'Opposition',prepare:'Présentation préparée',verify_phone:'Numéro vérifié'}[e.action]||e.action))+(e.note?' · '+e.note:'')+(e.due?' · rappel '+e.due:'');return p;
   }));
   $('providerMode').textContent=data.provider_mode==='live'?'Prestataires en mode réel':'Prestataires en mode test · aucune recette réelle';
   const chosen=$('providerQuote').value;
   const invoice=$('invoiceQuote').value;
   $('invoiceQuote').replaceChildren(new Option('Sans devis associé',''),...data.quotes.map(q=>new Option(q.number+' · '+q.customer+' · '+currency(q.total),q.number)));
   $('invoiceQuote').value=invoice;
   $('providerQuote').replaceChildren(...data.quotes.map(q=>new Option(q.number+' · '+currency(q.total),q.number)));
   if(data.quotes.some(q=>q.number===chosen))$('providerQuote').value=chosen;
   $('checkoutLinks').replaceChildren(...data.orders.map(row=>{
     const line=document.createElement('p');line.textContent=row.quote+' · accord vérifié · '+({unpaid:'non réglé',pending:'paiement en attente',paid:'réglé',failed:'paiement échoué',refunded:'remboursé',partially_refunded:'remboursement partiel'}[row.payment]||row.payment);
     if(row.checkout && row.payment==='pending'){const a=document.createElement('a');a.href=row.checkout;a.target='_blank';a.rel='noopener';a.textContent='Ouvrir le paiement hébergé';line.append(' · ',a)}
     return line;
   }));
   $('deskQuotes').replaceChildren(...data.quotes.map(q=>{const a=document.createElement('a');a.href='/api/web/crm/quote/file?number='+encodeURIComponent(q.number);a.textContent=q.number+' · '+currency(q.total)+' TTC · valable jusqu’au '+q.until;a.target='_blank';a.rel='noopener';return a}));
 }
 let offer=null;
 async function domainAction(route){
   const quote=$('providerQuote').value,approval=$('operatorCode').value;
   if(!quote||!approval)throw Error('Choisis un devis et saisis le code opérateur dans Accord & paiement.');
   return api('/api/web/sales/domain-'+route,{id:projectId,quote,approval,offer:offer?.approval,recovery:$('recoveryRef').value.trim(),confirmed:true});
 }
 let migration=null;
 for(const [id,route] of [['dbLink','db-link'],['dbPlan','db-plan'],['dbApply','db-apply']]){
   $(id).onclick=async()=>{
     const reference=$('dbRef').value.trim(),approval=$('operatorCode').value;
     if(!approval){$('dbStatus').textContent='Saisis le code opérateur dans Accord et paiement.';return}
     if(!confirm(route==='db-apply'?'Appliquer les migrations affichées à '+reference+' après vérification de la sauvegarde et des règles RLS ?':'Confirmer '+$(id).textContent.toLowerCase()+' pour '+reference+' ?'))return;
     const digest=migration?.digest;migration=null;$('dbApply').disabled=true;
     try{
       const r=await api('/api/web/sales/'+route,{id:projectId,reference,approval,digest,confirmed:true});
       if(route==='db-plan'){migration=r;$('dbApply').disabled=false}
       $('dbStatus').textContent=route==='db-plan'?'Simulation réussie : '+r.files.join(', '):route==='db-apply'?'Application confirmée par Supabase CLI. Les permissions et parcours utilisateur restent à tester.':'Projet lié.';
     }catch(e){$('dbStatus').textContent=e.message}
   };
 }
 $('domainOffer').onclick=async()=>{
   offer=null;$('domainBuy').disabled=true;
   try{
     offer=await domainAction('offer');
     $('offerDisplay').textContent=offer.domain+' · titulaire '+offer.holder+' · '+offer.total+' USD TTC · '+offer.years+' an(s) · renouvellement '+offer.renewal+' USD, automatique désactivé · équipe '+offer.team;
     $('domainBuy').disabled=false;
   }catch(e){$('offerDisplay').textContent=e.message}
 };
 $('domainBuy').onclick=async()=>{
   if(!offer||!confirm('Autoriser maintenant la dépense de '+offer.total+' USD pour '+offer.domain+' au nom de '+offer.holder+' ?'))return;
   $('domainBuy').disabled=true;
   try{const d=await domainAction('buy');$('offerDisplay').textContent='Commande '+d.order_id+' · '+d.state}
   catch(e){$('offerDisplay').textContent=e.message}finally{offer=null;$('operatorCode').value=''}
 };
 $('domainPoll').onclick=async()=>{
   try{const r=await domainAction('status');$('offerDisplay').textContent=r.domain?r.domain+' · '+r.state+' · '+(r.order_id||'référence à rapprocher chez Vercel'):'Aucune commande.'}
   catch(e){$('offerDisplay').textContent=e.message}
 };
 $('saveReview').onclick=()=>action('review',{revision:desk.revision,checks:Array.from(document.querySelectorAll('.checkgrid input'),el=>el.checked)});
 async function loadDesk(){renderDesk(await api('/api/web/sales/dossier?id='+projectId))}
 async function action(name,fields={}){
   try{renderDesk(await api('/api/web/sales/action',{id:projectId,action:name,...fields}));$('deskFeedback').textContent='Dossier enregistré.'}
   catch(e){$('deskFeedback').textContent=e.message}
 }
 $('aiPitch').onclick=async()=>{const b=$('aiPitch');b.disabled=true;$('deskFeedback').textContent='Codex prépare l’ordre de démonstration…';try{await action('generate_pitch')}finally{b.disabled=!desk?.ready}};
 for(const [button,route,description] of [['requestSign','sign','Envoyer maintenant le devis par Dropbox Sign au courriel de facturation enregistré'],['verifySign','verify','Consulter l’accord chez Dropbox Sign'],['checkout','checkout','Créer le lien Stripe de règlement intégral du devis signé']]){
   $(button).onclick=async()=>{
     const quote=$('providerQuote').value, approval=$('operatorCode').value;
     const record=desk.quotes.find(q=>q.number===quote);
     if(!record||!approval){$('orderStatus').textContent='Choisis un devis et saisis ton code opérateur.';return}
     if(!confirm(description+' · '+record.recipient+' · '+quote+' · '+currency(record.total)+' TTC · mode '+desk.provider_mode+' ?'))return;
     $(button).disabled=true;$('operatorCode').value='';
     try{renderDesk(await api('/api/web/sales/'+route,{id:projectId,quote,approval,recovery:$('recoveryRef').value.trim(),confirmed:true}));$('orderStatus').textContent='Réponse du prestataire enregistrée.'}
     catch(err){$('orderStatus').textContent=err.message}finally{$(button).disabled=false}
   };
 }
 $('refreshOrders').onclick=()=>loadDesk().catch(e=>$('orderStatus').textContent=e.message);
 $('factDay').valueAsDate=new Date();
 $('clientFact').onsubmit=e=>{
   e.preventDefault();
   if(confirm('Confirmer que cette information professionnelle, sa source et sa date sont exactes ?'))
     action('confirm_fact',{category:$('factType').value,value:$('factValue').value,day:$('factDay').value,source:$('factSource').value,confirmed:true});
 };
 $('registryCheck').onclick=()=>action('refresh_registry');
 $('saveBudget').onclick=()=>action('budget',{cost:$('costHT').value});
 $('prepareSale').onclick=()=>action('prepare');
 $('verifyPhone').onclick=()=>{if(confirm('As-tu vérifié que '+desk.phone+' est un numéro professionnel et que cet appel concerne son activité ?'))action('verify_phone',{confirmed:true})};
 $('oppose').onclick=()=>{if(confirm('Inscrire ce contact sur la liste d’opposition et supprimer ses rappels ?'))action('oppose')};
 $('callLog').onsubmit=e=>{e.preventDefault();action('call',{outcome:$('outcome').value,due:$('due').value,note:$('callNote').value})};
 $('domainLookup').onsubmit=async e=>{
   e.preventDefault();const n=$('registrarResult');n.textContent='Consultation de Vercel…';
   try{const r=await api('/api/web/sales/domain-search',{id:projectId,domain:$('candidate').value});
     n.textContent=r.available?r.domain+' · disponible · '+(r.price??'inconnu')+' USD pour '+(r.years??'?')+' an(s) · renouvellement '+(r.renewal??'inconnu')+' USD. Taxes à vérifier avant toute commande.':r.domain+' · indisponible ou disponibilité non confirmée.';
   }catch(err){n.textContent='Disponibilité inconnue : '+err.message}
 };
 $('deliveryZip').href='/api/web/export?id='+projectId;
 async function preflight(){
   const r=await api('/api/web/preflight?id='+projectId);
   $('releaseStatus').textContent=r.ok?'Contrôles techniques réussis. Vérifie également le parcours métier et les autorisations.':(r.blockers||[]).map(x=>x.label).join(', ')||'Contrôles à reprendre.';
   return r.ok;
 }
 $('finishDelivery').onclick=async()=>{
   if(confirm('Vérifier le déploiement, le domaine et HTTPS puis enregistrer que tu as remis le site au client ?'))await action('handover',{confirmed:true,approval:$('operatorCode').value});
 };
 $('runPreflight').onclick=()=>preflight().catch(e=>$('releaseStatus').textContent=e.message);
 $('publishApproved').onclick=async()=>{
   const b=$('publishApproved');b.disabled=true;
   try{
     if(!desk?.ready)throw Error('Maquette non prête.');
     if(!Array.from(document.querySelectorAll('.checkgrid input')).slice(0,7).every(el=>el.checked))throw Error('Complète la recette et confirme le mandat client.');
     if(!await preflight())return;
     if(!confirm('Confirmer que le client a validé cette version et t’a donné mandat pour publier officiellement '+desk.name+' sur Vercel maintenant ?'))return;
     await api('/api/web/sales/action',{id:projectId,action:'review',revision:desk.revision,checks:Array.from(document.querySelectorAll('.checkgrid input'),el=>el.checked)});
     if(desk.kind==='pro')await api('/api/web/project/pro/authorize',{id:projectId,confirmed:true});
     const r=await api('/api/web/vercel/publish',{id:projectId,production:true,publication_confirmed:true,revision:desk.revision,quote_number:$('providerQuote').value,approval:$('operatorCode').value});
     $('releaseStatus').textContent=r.deployment_result?.url?'URL renvoyée par Vercel : '+r.deployment_result.url:'Publication non confirmée.';
   }catch(err){$('releaseStatus').textContent=err.message}finally{b.disabled=false}
 };
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
       discount_pct:Number($('discountPct').value),scope:$('scope').value,recurring:$('recurring').value,
       valid_days:Number($('quoteValidDays').value),confirmed:true});
     area.replaceChildren();
     const strong=document.createElement('strong');strong.textContent='Devis '+result.quote_number+' enregistré · '+currency(result.total_eur);
     const link=document.createElement('a');link.href=result.download;link.target='_blank';link.rel='noopener noreferrer';
     link.textContent='Ouvrir le devis PDF ↗';
     area.append(strong,document.createElement('br'),link);await loadDesk();
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
   const proposal=desk?.quotes.find(q=>q.number===$('invoiceQuote').value);
   if(!window.confirm('Émettre une FACTURE définitive et numérotée pour '+(proposal?.customer||customer.name)+
     ' ?\n'+(proposal?proposal.number+' · TTC '+currency(proposal.total):'Montant HT : '+amount)+
     '\nUne facture émise ne peut pas être supprimée ou renumérotée.'))return;
   const result=await api('/api/web/invoice/issue',{
    id:projectId,seller,customer,items:[...selected.keys()],discount_pct:Number($('discountPct').value),
    quote_number:$('invoiceQuote').value||null,service_date:$('serviceDate').value,due_days:Number($('dueDays').value),
    accepted:true
   });
   area.replaceChildren();
   const header=document.createElement('strong');
   header.textContent='Facture '+result.invoice_number+' émise · '+currency(result.total_eur);
   const space=document.createElement('br');
   const link=document.createElement('a');link.href=result.download;
   link.textContent='Ouvrir / enregistrer la facture PDF FORMA ↗';
   link.target='_blank';link.rel='noopener';
   const structured=document.createElement('a');structured.href=result.download+'&format=json';structured.target='_blank';structured.rel='noopener';structured.textContent='Export comptable JSON';
   area.append(header,space,link,document.createElement('br'),structured);
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
       vercel_project:$('vercelProject').value.trim(),approval:$('operatorCode').value});
     node.replaceChildren();
     const msg=document.createElement('p');msg.textContent=result.notice;node.append(msg);
     const pre=document.createElement('pre');pre.textContent=result.dns_instructions||
       'Consulte la configuration DNS du projet dans Vercel.';
     pre.style.whiteSpace='pre-wrap';pre.style.fontSize='11px';
     node.append(pre);
   }catch(err){node.textContent='Domaine non rattaché : '+err.message}
   finally{btn.disabled=false}
 });
 load();loadDesk().catch(e=>$('deskFeedback').textContent=e.message);
})();
