/* Optional PWA support stays available through the browser's own menu.
   No confusing "Installer" button is injected into either professional studio. */
(()=>{
 'use strict';
 const secure=location.protocol==='https:'||['localhost','127.0.0.1'].includes(location.hostname);
 if(secure && 'serviceWorker' in navigator) {
   navigator.serviceWorker.register('/service-worker.js',{scope:'/'}).catch(()=>{});
 }
})();
