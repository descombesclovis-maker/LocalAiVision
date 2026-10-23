// Builds a Vercel-hostable copy of the existing LocalAiVision / LocalAiWeb UI.
// Does not change the desktop source or expose the local Python/ComfyUI server.
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const source = join(root, 'local_app', 'web');
const dist = join(root, 'dist');

if (!existsSync(join(source, 'index.html'))) {
  throw new Error('LocalAiVision web sources are missing.');
}
rmSync(dist, { recursive: true, force: true });
mkdirSync(join(dist, 'assets'), { recursive: true });
for (const entry of readdirSync(source, { withFileTypes: true })) {
  if (entry.isFile() && !entry.name.endsWith('.html') && entry.name !== 'service-worker.js') {
    cpSync(join(source, entry.name), join(dist, 'assets', entry.name));
  } else if (entry.isDirectory()) {
    cpSync(join(source, entry.name), join(dist, 'assets', entry.name), { recursive: true });
  }
}
cpSync(join(source, 'service-worker.js'), join(dist, 'service-worker.js'));
const pages = [
  ['index.html', 'index.html'],
  ['localaiweb-projects.html', 'localaiweb/index.html'],
  ['localaiweb.html', 'localaiweb/editor/index.html'],
  ['localaiweb-map.html', 'localaiweb/map/index.html'],
];
for (const [sourceName, outputName] of pages) {
  const file = join(dist, outputName);
  mkdirSync(resolve(file, '..'), { recursive: true });
  let html = readFileSync(join(source, sourceName), 'utf8');
  html = html.replace('</head>', '  <script defer src="/assets/cloud-status.js"></script>\n</head>');
  writeFileSync(file, html, 'utf8');
}
writeFileSync(join(dist, 'assets', 'cloud-status.js'), `
(() => {
  'use strict';
  const render = () => {
    if (document.getElementById('localai-cloud-state')) return;
    const bar = document.createElement('aside');
    bar.id = 'localai-cloud-state';
    bar.setAttribute('role', 'status');
    bar.setAttribute('aria-live', 'polite');
    Object.assign(bar.style, {
      position: 'relative', zIndex: '9999', width: '100%', boxSizing: 'border-box',
      background: '#242037', color: '#f5f2ff', padding: '12px 20px',
      borderBottom: '1px solid #665b91', font: '500 13px/1.6 system-ui, sans-serif',
      textAlign: 'center', overflowWrap: 'anywhere'
    });
    bar.textContent = 'Mode web Vercel : interfaces disponibles. Le moteur GPU, les générations, les projets et les agents ne sont pas encore connectés. Aucun calcul ne s’exécute ici.';
    document.body.prepend(bar);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render, {once:true});
  else render();
})();
`, 'utf8');
console.log('Vercel UI output prepared:', pages.map(([a,b])=>b).join(', '));
