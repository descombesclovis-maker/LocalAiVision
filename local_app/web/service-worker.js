/* Online-only PWA: always fetch the newest application from the trusted PC.
   Older app-shell caches are deleted; private projects, APIs and previews
   must never be retained by a service worker on the phone. */
const VERSION='localai-pwa-online-20261029-v2';
self.addEventListener('install',event=>{
  event.waitUntil(self.skipWaiting());
});
self.addEventListener('activate',event=>{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k.startsWith('localai-shell-'))
        .map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});
self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET'||new URL(request.url).origin!==self.location.origin)return;
  // Browser uses network for all routes. There is no stale offline screen that
  // pretends generation, CRM or media are usable without the desktop server.
  event.respondWith(fetch(request));
});
