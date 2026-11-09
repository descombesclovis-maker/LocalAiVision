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
async function bootstrap() {
  try {
    await fetch("/api/auth/init", { method: "POST" });
  } catch {
    // Non-fatal: queries will retry; user sees errors if auth truly fails.
  }
  createRoot(document.getElementById('root')!).render(
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
