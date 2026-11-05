(function studioConnectionsBootstrap(){
 'use strict';
 const trigger=document.getElementById('studioConnectionsButton');
 if(!trigger)return;
 const root=document.createElement('dialog');
 root.id='studioConnectionsDialog';
 root.className='studio-connections-dialog';
 root.setAttribute('aria-labelledby','studioConnectionsTitle');
 root.innerHTML=`
  <div class="studio-connections-head">
   <div><small>PARAMÈTRES · LOCALAI STUDIO</small><h2 id="studioConnectionsTitle">Connexions et clés API</h2><p>Configurez vos services. Aucune dépense ni déploiement ne sont déclenchés automatiquement.</p></div>
   <button type="button" id="studioConnectionsClose" aria-label="Fermer les connexions">×</button>
  </div>
  <div class="studio-connections-content">
   <section class="studio-connect-category">
    <h3>Agents IA · création de sites</h3>
    <p>Codex et Claude utilisent les outils CLI officiels. Une connexion par navigateur ne nécessite pas de coller une clé API. L'utilisation d'une API key OpenAI est un mode de facturation distinct de ChatGPT.</p>
    <div class="studio-connect-grid">
     <article class="studio-connect-card"><header><strong>Codex</strong><span id="scCodex" class="studio-connection-status">Vérification…</span></header>
      <p>Installez Codex CLI, puis authentifiez-vous avec votre compte ChatGPT dans la fenêtre ouverte.</p>
      <div class="studio-connect-actions"><button type="button" data-connect="codex">Connecter Codex</button><a href="https://developers.openai.com/codex/cli" target="_blank" rel="noopener noreferrer">Guide officiel ↗</a></div>
      <code>npm install -g @openai/codex</code><code>codex login</code></article>
     <article class="studio-connect-card"><header><strong>Claude Code</strong><span id="scClaude" class="studio-connection-status">Vérification…</span></header>
      <p>Installez Claude Code, puis ouvrez son authentification officielle.</p>
      <div class="studio-connect-actions"><button type="button" data-connect="claude">Connecter Claude</button><a href="https://code.claude.com/docs/en/setup" target="_blank" rel="noopener noreferrer">Guide officiel ↗</a></div>
      <code>claude auth login</code></article>
    </div>
   </section>
   <section class="studio-connect-category">
    <h3>Google Maps et Places</h3>
    <p>Créez un projet Google Cloud avec facturation activée et activez <strong>Maps JavaScript API</strong> et <strong>Places API (New)</strong>. Utilisez deux clés distinctes, des restrictions adaptées et des quotas.</p>
    <div class="studio-google-key">
     <label for="studioMapsBrowserKey">Clé navigateur Google Maps <span id="scMaps" class="studio-connection-status"></span></label>
     <small>Restreindre à Maps JavaScript API, aux référents 127.0.0.1/localhost avec le port utilisé et aux origines autorisées. Cette clé est visible par le navigateur.</small>
     <div class="studio-key-input"><input id="studioMapsBrowserKey" type="password" autocomplete="off" spellcheck="false" placeholder="Saisir une clé navigateur"><button type="button" data-save="maps_browser">Enregistrer</button><button type="button" data-clear="maps_browser" class="studio-connect-danger">Effacer</button></div>
    </div>
    <div class="studio-google-key">
     <label for="studioPlacesServerKey">Clé Google Places côté serveur <span id="scPlaces" class="studio-connection-status"></span></label>
     <small>Restreindre à Places API (New). Cette clé reste côté serveur. Les appels Places peuvent être facturés.</small>
     <div class="studio-key-input"><input id="studioPlacesServerKey" type="password" autocomplete="off" spellcheck="false" placeholder="Saisir une clé serveur"><button type="button" data-save="places_server">Enregistrer</button><button type="button" data-clear="places_server" class="studio-connect-danger">Effacer</button></div>
    </div>
    <p class="studio-connect-warning">🔒 Les clés sont chiffrées par Windows DPAPI pour votre compte local. Les variables d'environnement définies manuellement restent prioritaires.</p>
    <div class="studio-connect-actions"><a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer">Créer mes clés Google ↗</a><a href="/localaiweb/map">Ouvrir la carte ↗</a><button type="button" id="studioPlacesTest">Tester Places (requête facturable)</button></div>
   </section>
   <section class="studio-connect-category">
    <h3>Publication, base de données et paiements</h3>
    <p>Connectez vos outils CLI. Les paramètres propres aux projets restent à compléter séparément et aucune donnée personnelle n'est automatiquement transférée.</p>
    <div class="studio-connect-services">
     <article><header><strong>GitHub</strong><span id="scGithub" class="studio-connection-status"></span></header><button type="button" data-connect="github">Connecter CLI</button><a href="https://cli.github.com/manual/gh_auth_login" target="_blank" rel="noopener noreferrer">Guide ↗</a></article>
     <article><header><strong>Vercel</strong><span id="scVercel" class="studio-connection-status"></span></header><button type="button" data-connect="vercel">Connecter CLI</button><a href="https://vercel.com/docs/cli" target="_blank" rel="noopener noreferrer">Guide ↗</a></article>
     <article><header><strong>Supabase</strong><span id="scSupabase" class="studio-connection-status"></span></header><button type="button" data-connect="supabase">Connecter CLI</button><a href="https://supabase.com/docs/guides/local-development/cli/getting-started" target="_blank" rel="noopener noreferrer">Guide ↗</a></article>
     <article><header><strong>Stripe</strong><span id="scStripe" class="studio-connection-status"></span></header><button type="button" data-connect="stripe">Connecter CLI</button><a href="https://docs.stripe.com/stripe-cli" target="_blank" rel="noopener noreferrer">Guide ↗</a></article>
    </div>
   </section>
   <div class="studio-connect-foot"><button type="button" id="studioConnectionsCheck">Vérifier les connexions</button><output id="studioConnectionsFeedback" role="status" aria-live="polite">Prêt.</output></div>
  </div>`;
 document.body.append(root);
 const feedback=root.querySelector('#studioConnectionsFeedback');
 const inputs={maps_browser:root.querySelector('#studioMapsBrowserKey'),places_server:root.querySelector('#studioPlacesServerKey')};
 let busy=false;
 function notice(message){feedback.textContent=String(message||'').slice(0,450)}
 async function api(path,body){
  const options={credentials:'same-origin',cache:'no-store'};
  if(body!==undefined){options.method='POST';options.headers={'Content-Type':'application/json','X-LocalAI-Settings':'1'};options.body=JSON.stringify(body)}
  const response=await fetch(path,options);let value={};
  try{value=await response.json()}catch{}
  if(!response.ok||value.error)throw Error(value.error||('HTTP '+response.status));
  return value;
 }
 function dot(id,on,description){
  const el=root.querySelector('#'+id);if(!el)return;
  el.classList.toggle('connected',!!on);el.classList.toggle('disconnected',!on);
  el.textContent=description||(on?'Configuré':'Non configuré');
 }
 async function status(){
  notice('Vérification des connexions locales…');
  try{
   const result=await api('/api/studio/settings/status');
   const map=result.maps||{},agents=result.agents||{};
   dot('scMaps',map.maps_browser?.configured,map.maps_browser?.environment_override?'Variable système':map.maps_browser?.configured?'Clé enregistrée':'Clé manquante');
   dot('scPlaces',map.places_server?.configured,map.places_server?.environment_override?'Variable système':map.places_server?.configured?'Clé enregistrée':'Clé manquante');
   for(const [provider,id] of Object.entries({codex:'scCodex',claude:'scClaude',github:'scGithub',vercel:'scVercel',supabase:'scSupabase',stripe:'scStripe'})){
    const c=agents[provider]||{};
    dot(id,c.ready,c.ready?'Connecté':c.installed?'À authentifier':'CLI à installer');
   }
   notice('Statuts actualisés. Aucune requête Google facturable n’a été effectuée.');
  }catch(error){notice('Diagnostic indisponible : '+error.message)}
 }
 async function mutate(kind,action){
  if(busy)return;const input=inputs[kind],value=action==='save'?input.value.trim():'';
  if(action==='save'&&!value){notice('Saisissez une clé, ou choisissez Effacer.');return}
  if(action==='clear'&&!confirm('Effacer cette clé enregistrée sur cet ordinateur ?'))return;
  busy=true;
  try{await api('/api/studio/settings/google',{kind,action,value});input.value='';await status();notice(action==='save'?'Clé enregistrée et protégée sur cet ordinateur.':'Clé locale effacée.')}
  catch(error){notice('Échec de configuration : '+error.message)}
  finally{busy=false}
 }
 root.querySelectorAll('[data-save]').forEach(b=>b.addEventListener('click',()=>mutate(b.dataset.save,'save')));
 root.querySelectorAll('[data-clear]').forEach(b=>b.addEventListener('click',()=>mutate(b.dataset.clear,'clear')));
 root.querySelectorAll('[data-connect]').forEach(b=>b.addEventListener('click',async()=>{
  if(busy)return;busy=true;b.disabled=true;
  try{const result=await api('/api/web/integrations/connect',{provider:b.dataset.connect});notice(result.message||'Authentification ouverte. Terminez-la dans la nouvelle fenêtre puis revérifiez.')}
  catch(error){notice('Connexion non lancée : '+error.message)}
  finally{busy=false;b.disabled=false}
 }));
 root.querySelector('#studioPlacesTest').addEventListener('click',async()=>{
  if(!confirm('Tester Places en effectuant une recherche sur Paris ? Google peut facturer cette requête.'))return;
  notice('Test Google Places en cours…');
  try{const result=await api('/api/web/map/google/search?q='+encodeURIComponent('boulangerie Paris'));notice('Google Places a répondu : '+(result.results?.length||0)+' lieu(x). Les frais et quotas dépendent de votre compte Google.')}
  catch(error){notice('Test Places refusé : '+error.message)}
 });
 root.querySelector('#studioConnectionsCheck').addEventListener('click',status);
 root.querySelector('#studioConnectionsClose').addEventListener('click',()=>root.close());
 root.addEventListener('click',event=>{if(event.target===root)root.close()});
 root.addEventListener('close',()=>{for(const input of Object.values(inputs))input.value=''});
 trigger.addEventListener('click',()=>{if(!root.open){root.showModal();void status()}});
})();