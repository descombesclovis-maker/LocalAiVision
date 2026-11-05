(()=>{'use strict';
 const $=s=>document.querySelector(s);let dossier=null,prepared=null,busy=false;
 const titles={pending:'En attente',partial:'Partiel',received:'Reçu',refunded:'Remboursé',cancelled:'Annulé'};
 const serviceFields={
  hosting:{title:'Hébergement et domaine',fields:{provider:'Fournisseur',domain:'Nom de domaine',url:'URL du site',project:'Projet associé',costs:'Coûts récurrents',renewal_owner:'Responsable du renouvellement',instructions:'Instructions et transfert'}},
  vercel:{title:'Vercel',fields:{project_id:'Identifiant du projet',team_id:'Équipe propriétaire',domain:'Domaine',build_command:'Commande de compilation',output_directory:'Dossier de sortie',instructions:'Reconstruction, redéploiement et transfert'}},
  supabase:{title:'Supabase',fields:{project_ref:'Référence du projet',auth:'Configuration Auth et URL de redirection',storage:'Buckets et politiques de stockage',security:'RLS, politiques et vérifications',instructions:'Migrations, fonctions et mise en service'}},
  payment:{title:'Paiements du site',fields:{provider:'Plateforme réellement intégrée',mode:'Mode : test ou live',client_account:'Compte du client (identifiant public uniquement)',functions:'Fonctions de paiement utilisées',webhooks:'Routes de webhooks et événements à configurer',instructions:'Connexion du compte et vérifications avant ouverture'}}
 };
 function el(tag,cls,value){const node=document.createElement(tag);if(cls)node.className=cls;if(value!==undefined)node.textContent=value;return node}
 function status(message,error=false){$('#deliveryStatus').textContent=message;$('#deliveryStatus').classList.toggle('error',error)}
 function studio(path){return 'http://127.0.0.1:'+location.port+path}
 document.querySelectorAll('[data-studio-link]').forEach(a=>a.href=studio(a.dataset.studioLink));
 async function api(path,body){
  const response=await fetch('/api/web/delivery/'+path,{cache:'no-store',...(body?{method:'POST',headers:{'Content-Type':'application/json','X-LocalAI-Delivery':'1'},body:JSON.stringify(body)}:{})});
  if(!response.ok){const result=await response.json().catch(()=>({}));throw Error(result.error||'Action indisponible ('+response.status+').')}
  return response.json();
 }
 async function run(fn){if(busy)return;busy=true;document.body.setAttribute('aria-busy','true');try{await fn()}catch(error){status(error.message,true)}finally{busy=false;document.body.removeAttribute('aria-busy')}}
 function tab(name){document.querySelectorAll('[data-panel]').forEach(n=>n.hidden=n.dataset.panel!==name);document.querySelectorAll('[data-tab]').forEach(n=>n.dataset.tab===name?n.setAttribute('aria-current','step'):n.removeAttribute('aria-current'))}
 document.querySelectorAll('[data-tab]').forEach(n=>n.addEventListener('click',()=>tab(n.dataset.tab)));
 function valueField(form,name,value){const node=form.elements.namedItem(name);if(!node)return;if(node.type==='checkbox')node.checked=value===true;else node.value=value??''}
 function renderLine(item={label:'',quantity:'1',unit_eur:'0',vat_rate:'20'}){
  const row=el('div','quote-line');
  for(const [key,label] of [['label','Prestation'],['quantity','Quantité'],['unit_eur','Prix HT (€)'],['vat_rate','TVA (%)']]){
   const wrap=el('label',null,label),input=el('input');input.dataset.field=key;input.value=item[key];input.required=true;
   if(key!=='label'){input.type='number';input.min=key==='quantity'?'.01':'0';input.step='.01'}
   input.disabled=Boolean(dossier?.quote);input.addEventListener('input',draftTotal);wrap.append(input);row.append(wrap);
  }
  const remove=el('button',null,'×');remove.type='button';remove.setAttribute('aria-label','Supprimer cette prestation');remove.disabled=Boolean(dossier?.quote);remove.addEventListener('click',()=>{row.remove();draftTotal()});row.append(remove);$('#quoteLines').append(row);
 }
 function readLines(){return [...document.querySelectorAll('.quote-line')].map(row=>Object.fromEntries([...row.querySelectorAll('[data-field]')].map(n=>[n.dataset.field,n.value])))}
 function draftTotal(){const vat=$('#commercialForm').elements.namedItem('seller.vat_mode').value==='standard';const total=readLines().reduce((s,r)=>s+(Number(r.quantity)||0)*(Number(r.unit_eur)||0)*(1+(vat?(Number(r.vat_rate)||0)/100:0)),0);$('#draftTotal').textContent='Total estimé : '+total.toLocaleString('fr-FR',{style:'currency',currency:'EUR'})+' TTC'}
 $('#addLine').addEventListener('click',()=>{renderLine();draftTotal()});$('#commercialForm').elements.namedItem('seller.vat_mode').addEventListener('change',draftTotal);
 function commercialData(){
  const form=$('#commercialForm'),data={seller:{},customer:{},items:readLines()};
  for(const [key,v] of new FormData(form)){
   if(key.startsWith('seller.'))data.seller[key.slice(7)]=v;
   else if(key.startsWith('customer.'))data.customer[key.slice(9)]=v;
   else data[key]=v;
  }
  data.require_payment=form.elements.namedItem('require_payment').checked;return data;
 }
 function row(parent,title,value){const n=el('div','summary-card');n.append(el('small',null,title),el('strong',null,value));parent.append(n)}
 function docLink(number,label){const a=el('a',null,label+' · '+number);a.href='/api/web/delivery/document?id='+encodeURIComponent(dossier.id)+'&number='+encodeURIComponent(number);a.target='_blank';a.rel='noopener';return a}
 function render(){
  if(!dossier)return;prepared=null;$('#downloadPackage').hidden=true;$('#packagePreview').replaceChildren();$('#dossier').hidden=false;
  $('#projectName').textContent=dossier.name;$('#projectMeta').textContent=(dossier.customer.name||'Client à renseigner')+' · Créé le '+new Date(dossier.created_at*1000).toLocaleDateString('fr-FR');$('#editProject').href=studio('/localaiweb/editor?id='+encodeURIComponent(dossier.id));
  $('#deliverySummary').replaceChildren();row($('#deliverySummary'),'Devis',dossier.accepted_quote?'Accepté (déclaré)':dossier.quote?'Préparé':'À préparer');row($('#deliverySummary'),'Règlement',titles[dossier.assessment.payment.status]||'En attente');row($('#deliverySummary'),'Préparation',dossier.assessment.ready?'Paquet prêt':dossier.assessment.missing.length+' éléments à vérifier');row($('#deliverySummary'),'Livraison',dossier.delivered&&dossier.delivered.revision===dossier.assessment.revision?'Effectuée (déclarée)':'À effectuer');
  const form=$('#commercialForm');for(const control of form.elements)if(control.name?.includes('.')){const [party,key]=control.name.split('.');valueField(form,control.name,dossier[party]?.[key])}
  for(const key of ['service_date','valid_days','due_days','scope','maintenance','require_payment'])valueField(form,key,dossier[key]);
  for(const control of form.elements)control.disabled=Boolean(dossier.quote);$('#createQuote').disabled=Boolean(dossier.quote);
  $('#quoteLines').replaceChildren();dossier.items.forEach(renderLine);draftTotal();
  $('#reviseQuote').hidden=!dossier.quote;
  $('#documentList').replaceChildren();for(const doc of dossier.documents)$('#documentList').append(docLink(doc.number,{quote:'Devis PDF',invoice:'Facture PDF',credit:'Avoir PDF'}[doc.kind]));
  $('#legalNotice').textContent=dossier.legal_notice;$('#acceptQuote').disabled=!dossier.quote||Boolean(dossier.accepted_quote);
  $('#cancelPayment').textContent=dossier.cancelled?'Rouvrir le dossier':'Annuler le règlement en attente';$('#cancelPayment').disabled=Number(dossier.assessment.payment.paid_eur)>0;
  $('#paymentHistory').replaceChildren();const payment=dossier.assessment.payment;
  const balance=el('p',null,'Reçu : '+payment.paid_eur+' € · Reste : '+payment.remaining_eur+' €'+(Number(payment.test_eur)?' · Test (non encaissé) : '+payment.test_eur+' €':''));$('#paymentHistory').append(balance,el('p','help',payment.manual_notice));
  for(const receipt of payment.receipts){const n=el('div','receipt',receipt.amount+' € · '+receipt.at+' · '+receipt.reference);n.append(el('small',null,(receipt.source.startsWith('manual')?'Déclaration de l’utilisateur':'Vérifié auprès de Stripe')+' · '+(receipt.mode==='test'?'TEST — ne débloque pas la livraison':'Règlement réel déclaré ou vérifié')));$('#paymentHistory').append(n)}
  renderServices();$('#missingItems').replaceChildren();if(dossier.assessment.ready)$('#missingItems').append(el('p','ready-message','Les éléments requis sont réunis pour préparer le paquet.'));
  else{const list=el('ul','missing-list');dossier.assessment.missing.forEach(x=>list.append(el('li',null,x)));$('#missingItems').append(list)}
  $('#sourceInventory').replaceChildren();for(const file of dossier.assessment.files){const n=el('div','file-row',file.path);n.append(el('small',null,file.bytes+' octets'));$('#sourceInventory').append(n)}
  for(const file of dossier.assessment.excluded)$('#sourceInventory').append(el('div','file-row','Exclu : '+file));
  $('#preparePackage').disabled=!dossier.assessment.ready;$('#markDelivered').disabled=!dossier.assessment.ready;
 }
 function renderServices(){
  const container=$('#serviceForms');container.replaceChildren();
  for(const [key,def] of Object.entries(serviceFields)){
   const value=dossier.services[key]||{},detected=dossier.assessment.services.includes(key),field=el('fieldset');field.append(el('legend',null,def.title+(detected?' · détecté / configuré':'')));
   const active=el('label','checkbox'),checkbox=el('input');checkbox.type='checkbox';checkbox.name=key+'.enabled';checkbox.checked=value.enabled||detected;active.append(checkbox,document.createTextNode('Ce projet utilise ce service'));field.append(active);
   const details=el('div','service-details');
   for(const [name,label] of Object.entries(def.fields)){
    const wrap=el('label',null,label);let input;
    if(key==='payment'&&name==='mode'){input=el('select');for(const [v,t] of [['','À renseigner'],['test','Test'],['live','Production (live)']]){const o=el('option',null,t);o.value=v;input.append(o)}}
    else{input=el('textarea');input.rows=['instructions','security','webhooks'].includes(name)?3:2}
    input.name=key+'.'+name;input.value=value[name]||'';input.maxLength=2500;wrap.append(input);details.append(wrap);
   }
   const reviewed=el('label','checkbox'),check=el('input');check.type='checkbox';check.name=key+'.reviewed';check.checked=value.reviewed===true;reviewed.append(check,document.createTextNode('J’ai vérifié cette configuration et les responsabilités du client.'));details.append(reviewed);field.append(details);container.append(field);
   const show=()=>details.hidden=!checkbox.checked&&!detected;checkbox.addEventListener('change',show);show();
  }
  for(const key of ['design','pages','functions','rights'])valueField($('#technicalForm'),'check.'+key,dossier.checks[key]);
 }
 async function refreshLibrary(){const data=await api('list');$('#deliveryLibrary').replaceChildren();for(const d of data.dossiers){const button=el('button','library-card'+(d.id===dossier?.id?' active':''));button.type='button';button.append(el('strong',null,d.name),el('small',null,(d.customer_name||'Client à renseigner')+' · '+(titles[d.payment]||'En attente')),el('small',null,(d.preparation==='ready'?'Prêt à livrer':d.missing_count+' éléments à vérifier')+' · '+(d.delivered?'Livré':'À livrer')),el('small',null,new Date(d.created_at*1000).toLocaleDateString('fr-FR')));button.addEventListener('click',()=>run(()=>open(d.id)));$('#deliveryLibrary').append(button)}}
 async function legacy(){try{const data=await api('archive?id='+encodeURIComponent(dossier.id));$('#legacyDocuments').replaceChildren();for(const doc of data.documents){const a=el('a',null,doc.number+' · Archive');a.href=doc.download;a.target='_blank';a.rel='noopener';$('#legacyDocuments').append(a)}if(!data.documents.length)$('#legacyDocuments').textContent='Aucun ancien document associé à ce projet.'}catch(e){$('#legacyDocuments').textContent=e.message}}
 async function open(id){dossier=await api('dossier?id='+encodeURIComponent(id));$('#projectSelect').value=id;const url=new URL(location.href);url.searchParams.set('id',id);history.replaceState(null,'',url);render();await refreshLibrary();await legacy();status('Dossier chargé. Les modifications sont enregistrées uniquement par les actions de préparation.')}
 async function mutate(action,extra={}){dossier=await api('action',{id:dossier.id,version:dossier.version,action,...extra});render();await refreshLibrary();status('Dossier enregistré. Aucun envoi ni transaction effectué.')}
 $('#projectSelect').addEventListener('change',event=>{if(event.target.value)run(()=>open(event.target.value))});
 $('#commercialForm').addEventListener('submit',event=>{event.preventDefault();run(()=>mutate('save',commercialData()))});
 $('#createQuote').addEventListener('click',()=>run(async()=>{if(!$('#commercialForm').reportValidity())return;const data=commercialData();if(!confirm('Valider vos coordonnées et ces prestations pour créer un devis figé ? Aucun document ne sera envoyé.'))return;await mutate('save',data);await mutate('quote',{confirmed:true});status('Devis PDF créé et archivé. Vous pouvez le télécharger.')}));
 $('#reviseQuote').addEventListener('click',()=>run(async()=>{if(confirm('Préparer un nouveau devis modifiable ? Les documents précédents restent archivés. Aucun document ne sera envoyé.'))await mutate('revise',{confirmed:true})}));
 $('#acceptQuote').addEventListener('click',()=>run(async()=>{if(confirm('Le client a-t-il accepté ce devis ? Cette acceptation sera enregistrée comme votre déclaration.'))await mutate('accept',{confirmed:true})}));
 $('#cancelPayment').addEventListener('click',()=>run(async()=>{if(confirm(dossier.cancelled?'Rouvrir ce dossier ?':'Annuler le règlement en attente ? Aucun document ne sera supprimé.'))await mutate('cancel',{confirmed:true})}));
 $('#recordPayment').addEventListener('click',()=>run(async()=>{const amount=$('#paymentAmount').value,reference=$('#paymentReference').value;if(!confirm('Confirmer la réception déclarée de '+amount+' € et la génération automatique de la facture ? Aucun paiement ne sera exécuté.'))return;await mutate('payment',{amount,reference,confirmed:true});$('#paymentAmount').value='';$('#paymentReference').value=''}));
 $('#verifyStripe').addEventListener('click',()=>run(async()=>{if(confirm('Vérifier cette session auprès de Stripe et générer la facture si le règlement réel est confirmé ?'))await mutate('stripe',{reference:$('#stripeReference').value,confirmed:true})}));
 $('#recordRefund').addEventListener('click',()=>run(async()=>{const amount=prompt('Montant déjà remboursé, en euros. Aucun remboursement ne sera effectué.');if(amount===null)return;const reference=prompt('Référence unique de votre justificatif de remboursement');if(reference&&confirm('Enregistrer ce remboursement comme votre déclaration ?'))await mutate('refund',{amount,reference,confirmed:true})}));
 $('#createCredit').addEventListener('click',()=>run(async()=>{const reason=prompt('Motif de l’annulation intégrale de la facture (l’original est conservé)');if(reason&&confirm('Émettre un avoir intégral définitif ? La livraison de ce dossier sera bloquée.'))await mutate('credit',{reason,confirmed:true})}));
 $('#technicalForm').addEventListener('submit',event=>{event.preventDefault();run(async()=>{const form=$('#technicalForm'),services={},checks={};for(const [key,def] of Object.entries(serviceFields)){services[key]={enabled:form.elements.namedItem(key+'.enabled').checked,reviewed:form.elements.namedItem(key+'.reviewed').checked};for(const name of Object.keys(def.fields))services[key][name]=form.elements.namedItem(key+'.'+name).value}for(const key of ['design','pages','functions','rights'])checks[key]=form.elements.namedItem('check.'+key).checked;await mutate('technical',{services,checks})})});
 $('#preparePackage').addEventListener('click',()=>run(async()=>{prepared=await api('prepare',{id:dossier.id,revision:dossier.assessment.revision,version:dossier.version});$('#packagePreview').replaceChildren(el('h4',null,prepared.name));for(const file of prepared.files){const n=el('div','file-row',file.path);n.append(el('small',null,file.bytes+' octets'));$('#packagePreview').append(n)}$('#downloadPackage').hidden=false;status('Paquet vérifié et prêt au téléchargement. Aucun fichier transmis au client.')}));
 $('#downloadPackage').addEventListener('click',()=>run(async()=>{if(!prepared)return;const r=await fetch('/api/web/delivery/download',{method:'POST',headers:{'Content-Type':'application/json','X-LocalAI-Delivery':'1'},body:JSON.stringify({id:dossier.id,version:prepared.version,revision:prepared.revision})});if(!r.ok){const data=await r.json();throw Error(data.error)}const url=URL.createObjectURL(await r.blob()),a=el('a');a.href=url;a.download=prepared.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);status('Paquet téléchargé. Il reste à le transmettre au client par le canal de votre choix.')}));
 $('#markDelivered').addEventListener('click',()=>run(async()=>{if(confirm('Avez-vous remis le paquet au client ? Cette action enregistre votre déclaration sans envoyer de fichier.'))await mutate('delivered',{confirmed:true})}));
 run(async()=>{const response=await fetch('/api/web/projects');if(!response.ok)throw Error('Liste des projets indisponible.');const data=await response.json();for(const project of data.projects){const o=el('option',null,project.name);o.value=project.id;$('#projectSelect').append(o)}const id=new URLSearchParams(location.search).get('id');if(id)await open(id);else await refreshLibrary()});
})();
