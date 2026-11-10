// Hand-written mirrors of backend/models/companies.py — keep in sync.
export interface CompanyPoint {
  siren: string;
  siret: string;
  name: string;
  lat: number;
  lng: number;
  naf: string;
  section: string;
  address: string;
  city: string;
  effectif: string;
  is_siege: boolean;
}
export interface CompanyOverview { points: CompanyPoint[]; departments_ready: number; departments_total: number }
export interface Sector { code: string; label: string }
export interface GeoResult { label: string; lat: number; lng: number; type: string }
export interface CompanyDetail {
  siren: string;
  siret: string;
  name: string;
  legal_name: string;
  naf: string;
  section: string;
  section_label: string;
  address: string;
  city: string;
  postal_code: string;
  lat: number | null;
  lng: number | null;
  created: string;
  legal_form: string;
  category: string;
  effectif: string;
  establishments: number;
  directors: string[];
  revenue: number | null;
  net_result: number | null;
  finance_year: string | null;
  strengths: string[];
  site_type: string;
  active: boolean;
}
export type SiteEngine = "local" | "claude" | "gpt" | "gemini";
export interface CompanySiteRequest { llm: SiteEngine; mode: "libre" | "pro" }
export interface LocalEngine { kind: "ollama" | "openai"; base_url: string; model: string; num_ctx: number }
export interface LocalEngineTest { ok: boolean; models: string[]; message: string }

// Mirrors backend/models/engines.py
export interface ComfySettings {
  base_url: string;
  image_preset: "flux-dev" | "flux-schnell" | "sdxl";
  image_checkpoint: string;
  video_preset: "wan22" | "wan21_t2v" | "wan21_fun_camera" | "ltxv";
  video_model: string;
  video_text_encoder: string;
  video_vae: string;
  custom_image_workflow: string;
  custom_video_workflow: string;
}
export interface ComfyTest { ok: boolean; message: string; gpu: string; checkpoints: string[]; diffusion_models: string[]; text_encoders: string[] }
export interface EnginePreset { key: string; label: string; files: Record<string, string> }
export interface EnginePresets { image: EnginePreset[]; video: EnginePreset[] }
export interface VideoPresetStatus { key: "wan22" | "wan21_t2v" | "wan21_fun_camera" | "ltxv"; label: string; model: string; files: string[]; installed: boolean | null }
export interface VideoEngineStatus { presets: VideoPresetStatus[]; camera_poses: string[] }
export interface WebCheckItem { siret: string; name: string; city: string; lat: number; lng: number }
export interface WebCheckRequest { items: WebCheckItem[] }
export interface WebStatus { siret: string; status: "pending" | "found" | "none"; url: string | null; source: string }
export interface QueueItem {
  id: string;
  kind: "photo" | "video" | "site" | "edit";
  engine: string;
  label: string;
  ref: "media" | "project";
  status: "running" | "waiting";
  position: number;
  elapsed_s: number;
  eta_s: number;
  start_in_s: number;
  typical_s: number;
  samples: number;
}
export interface QueueState { items: QueueItem[]; total_eta_s: number }
export interface DiagCheck { key: string; label: string; status: "ok" | "warn" | "error" | "info"; detail: string; fix: string; cmd: string }
export interface Diagnostic { checks: DiagCheck[]; ok: number; warn: number; error: number; online: boolean; checked_at: string }
export interface KitInfo { installer_available: boolean; installer_size_mb: number }

export interface ImageModelStatus { key: string; label: string; checkpoint: string; installed: boolean | null }
