/* Application shell only. Never cache APIs, generated files, uploaded media or project content. */
const CACHE='localai-shell-20261028-brand-v2';
const STATIC=new Set(['/assets/style.css','/assets/app.js','/assets/intent.js','/assets/styles.js',
 '/assets/localaiweb.css','/assets/localaiweb.js','/assets/localaiweb-map.css',
 '/assets/localaiweb-map.js','/assets/studio-redesign.css','/assets/studio-redesign.js','/assets/localaiweb-projects.css','/assets/localaiweb-projects.js',
 '/assets/app-icon.svg','/assets/brand-vision.svg','/assets/brand-web.svg',
 '/assets/brand-identity.svg','/assets/manifest.webmanifest','/assets/pwa-install.js']);
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll([...STATIC])).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('localai-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
 const req=event.request;
 if(req.method!=='GET'||new URL(req.url).origin!==self.location.origin)return;
 const url=new URL(req.url);
 if(!STATIC.has(url.pathname))return; // intentionally network-only for projects and user information
 event.respondWith(fetch(req).then(response=>{
   if(response.ok){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(req,copy)));}
   return response;
 }).catch(()=>caches.match(req)));
});
