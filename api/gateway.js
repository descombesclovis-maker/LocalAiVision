// Deliberate non-functional API until a secured, authenticated GPU backend is configured.
// Never forward LocalAiVision's powerful local code/admin/filesystem endpoints publicly.
export default function handler(req, res) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.statusCode = 503;
  res.end(JSON.stringify({
    online: false,
    llm: { online: false },
    error: 'GPU_BACKEND_NOT_CONNECTED',
    message: 'Interface cloud uniquement. ComfyUI, Qwen, projets et agents nécessitent un serveur GPU privé authentifié. Le PC Windows ne peut pas fonctionner dans Vercel Functions.'
  }));
}
