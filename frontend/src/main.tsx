import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { queryClient } from './lib/queryClient'

// Secure session initialization (V1-B.2): the Vite proxy injects the one-time
// bootstrap token (X-Boot-Token) on this request only.  The backend validates it,
// sets an httpOnly SameSite=Strict session cookie, and invalidates the token.
// No secret is embedded in the frontend bundle.
// Only an explicit refusal (401/403) blocks the app. A network error or a 404 (for example the
// online preview, which has no /api/auth/init) keeps the previous behaviour.
function SessionRequired() {
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#0b0f17", color: "#e2e8f0", fontFamily: "system-ui, sans-serif", padding: 24 }}>
      <div style={{ maxWidth: 520, textAlign: "center", lineHeight: 1.5 }} data-testid="session-required">
        <h1 style={{ fontSize: 20, marginBottom: 12 }}>Session non ouverte</h1>
        <p>Ce navigateur n'a pas de session LocalAiStudio. Le jeton de connexion est à usage unique : relancez LocalAiStudio depuis son lanceur, puis ouvrez l'application depuis ce navigateur. Aucune donnée n'a été modifiée.</p>
      </div>
    </div>
  );
}

async function bootstrap() {
  let denied = false;
  try {
    const res = await fetch("/api/auth/init", { method: "POST" });
    denied = res.status === 401 || res.status === 403;
  } catch {
    // Non-fatal: queries will retry; user sees errors if auth truly fails.
  }
  const root = createRoot(document.getElementById('root')!);
  if (denied) {
    root.render(<SessionRequired />);
    return;
  }
  root.render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  );
}

bootstrap();
