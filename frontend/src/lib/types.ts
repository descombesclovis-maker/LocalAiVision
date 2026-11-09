// Hand-written mirrors of backend/models/schemas.py — keep in sync.
export type StepStatus = "pending" | "running" | "done" | "error" | "waiting";
export interface Step { key: string; label: string; status: StepStatus; detail: string }
export interface PageInfo { file: string; title: string }
export interface FileItem { path: string; content: string }
export interface ChatMessage { role: "user" | "assistant" | "system"; content: string; created_at: string }
export interface StyleOptions { mood: string; colors: string; fonts: string; references: string }
export type ProjectStatus = "queued" | "generating" | "editing" | "ready" | "error" | "needs_input";
export type Mode = "libre" | "pro";
export type Llm = "local" | "claude" | "gpt" | "gemini";

export interface ProjectSummary {
  id: string;
  name: string;
  prompt: string;
  mode: Mode;
  llm: Llm;
  engine: string;
  hero_video: boolean;
  brand_id: string | null;
  status: ProjectStatus;
  site_type: string;
  thumbnail_url: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}
export interface Project extends ProjectSummary {
  style: StyleOptions | null;
  steps: Step[];
  question: string | null;
  pages: PageInfo[];
  files: FileItem[];
  messages: ChatMessage[];
  asset_ids: string[];
  error: string | null;
  qa_report: string[];
}
export type SiteEngine = "premium" | "code";
export interface ProjectCreate { prompt: string; name: string; mode: Mode; llm: Llm; engine: SiteEngine; hero_video: boolean; brand_id: string | null; style: StyleOptions | null }
export interface Selection { page: string; selector: string; html: string }
export interface ChatRequest { message: string; page: string; selection: Selection | null; media_ids: string[] }
export interface Version { id: string; project_id: string; number: number; label: string; created_at: string }

export interface Brand { id: string; name: string; slogan: string; colors: string[]; logo_media_id: string | null; created_at: string }
export interface BrandCreate { name: string; slogan: string; colors: string[]; logo_media_id: string | null }

export type MediaStatus = "pending" | "running" | "done" | "error" | "cancelled";
export interface Media {
  id: string;
  kind: "image" | "video";
  source: string;
  prompt: string;
  model: string;
  status: MediaStatus;
  progress_label: string;
  url: string | null;
  mime: string | null;
  aspect_ratio: string | null;
  duration: string | null;
  project_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}
export interface ImageRequest { prompt: string; model: "comfy" | "nano-banana" | "nano-banana-pro"; aspect_ratio: "1:1" | "16:9" | "9:16" | "4:5"; ref_media_id: string | null }
export interface VideoRequest { prompt: string; model: "comfy" | "veo" | "kling" | "minimax"; mode: "text" | "image"; duration: string; aspect_ratio: string; ref_media_id: string | null }
export interface UploadRequest { data_url: string; source: "upload" | "ad" | "logo"; prompt: string }
export interface VideoModel { key: "comfy" | "veo" | "kling" | "minimax"; label: string; tagline: string; durations: string[]; aspects: string[]; audio: boolean }
export interface ActivityItem { id: string; kind: "site" | "image" | "video"; name: string; status: string; label: string }
export interface Activity { count: number; items: ActivityItem[] }

export const mediaFileUrl = (id: string) => `/api/media/${id}/file`;
export const SITE_TYPES: Record<string, string> = {
  boutique: "Boutique",
  restaurant: "Restaurant",
  services: "Services",
  immobilier: "Immobilier",
  autre: "Site vitrine",
  "": "En analyse",
};
export const STATUS_LABELS: Record<ProjectStatus, string> = {
  queued: "En file",
  generating: "Génération",
  editing: "Modification",
  ready: "Prêt",
  error: "Erreur",
  needs_input: "Question",
};
