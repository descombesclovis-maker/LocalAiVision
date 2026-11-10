import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, apiDelete, apiGet, apiPatch, apiPost, apiPut } from "@/lib/api";
import type {
  Activity, Brand, BrandCreate, ChatRequest, ImageRequest, Media, Project, ProjectCreate, ProjectSummary,
  SmartMotionRequest, SmartMotionStatus, UploadRequest, Version, VideoModel, VideoRequest,
} from "@/lib/types";

export function errMsg(e: unknown): string {
  if (e instanceof ApiError) {
    const b = e.body as { detail?: unknown } | null;
    if (b && typeof b.detail === "string") return b.detail;
    return `Erreur ${e.status}`;
  }
  return "Serveur injoignable";
}

const BUSY = new Set(["queued", "generating", "editing"]);

export const useActivity = () =>
  useQuery({ queryKey: ["activity"], queryFn: () => apiGet<Activity>("/activity"), refetchInterval: 4000 });

export const useProjects = (q: string, mode: string) =>
  useQuery({
    queryKey: ["projects", q, mode],
    queryFn: () => apiGet<ProjectSummary[]>(`/projects?q=${encodeURIComponent(q)}&mode=${mode}`),
    refetchInterval: (query) => (query.state.data?.some((p) => BUSY.has(p.status)) ? 4000 : false),
  });

export const useProject = (id: string) =>
  useQuery({
    queryKey: ["project", id],
    queryFn: () => apiGet<Project>(`/projects/${id}`),
    refetchInterval: (query) => (query.state.data && BUSY.has(query.state.data.status) ? 2500 : false),
  });

export const useVersions = (id: string, version: number) =>
  useQuery({ queryKey: ["versions", id, version], queryFn: () => apiGet<Version[]>(`/projects/${id}/versions`) });

export const useBrands = () => useQuery({ queryKey: ["brands"], queryFn: () => apiGet<Brand[]>("/brands") });

export const useMedia = (kind = "") =>
  useQuery({
    queryKey: ["media", kind],
    queryFn: () => apiGet<Media[]>(`/media?kind=${kind}`),
    refetchInterval: (query) => (query.state.data?.some((m) => m.status === "pending" || m.status === "running") ? 3000 : false),
  });

export const useVideoModels = () =>
  useQuery({ queryKey: ["video-models"], queryFn: () => apiGet<VideoModel[]>("/media/models/video"), staleTime: Infinity });

export const useSmartMotionStatus = () =>
  useQuery({ queryKey: ["smartmotion-status"], queryFn: () => apiGet<SmartMotionStatus>("/media/models/smartmotion"), staleTime: 60_000 });

function useInvalidate() {
  const qc = useQueryClient();
  return (...keys: string[]) => keys.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
}

export function useCreateProject() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (b: ProjectCreate) => apiPost<Project>("/projects", b),
    onSuccess: () => inv("projects", "activity"),
    onError: (e) => toast.error(errMsg(e)),
  });
}

export function useProjectAction(id: string) {
  const qc = useQueryClient();
  const done = (p: Project) => {
    qc.setQueryData(["project", id], p);
    qc.invalidateQueries({ queryKey: ["versions", id] });
    qc.invalidateQueries({ queryKey: ["activity"] });
    qc.invalidateQueries({ queryKey: ["projects"] });
  };
  const onError = (e: unknown) => toast.error(errMsg(e));
  return {
    chat: useMutation({ mutationFn: (b: ChatRequest) => apiPost<Project>(`/projects/${id}/chat`, b), onSuccess: done, onError }),
    retry: useMutation({ mutationFn: () => apiPost<Project>(`/projects/${id}/retry`), onSuccess: done, onError }),
    undo: useMutation({ mutationFn: () => apiPost<Project>(`/projects/${id}/undo`), onSuccess: (p) => { done(p); toast.success("Dernière modification annulée"); }, onError }),
    restore: useMutation({ mutationFn: (n: number) => apiPost<Project>(`/projects/${id}/versions/${n}/restore`), onSuccess: (p) => { done(p); toast.success("Version restaurée"); }, onError }),
    save: useMutation({ mutationFn: (b: { path: string; content: string }) => apiPut<Project>(`/projects/${id}/files`, b), onSuccess: done, onError }),
    rename: useMutation({ mutationFn: (b: { name?: string; brand_id?: string }) => apiPatch<Project>(`/projects/${id}`, b), onSuccess: done, onError }),
  };
}

export function useDeleteProject() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => apiDelete<{ ok: boolean }>(`/projects/${id}`),
    onSuccess: () => { inv("projects"); toast.success("Projet supprimé"); },
    onError: (e) => toast.error(errMsg(e)),
  });
}

export function useMediaActions() {
  const inv = useInvalidate();
  const onError = (e: unknown) => toast.error(errMsg(e));
  const ok = () => inv("media", "activity");
  return {
    image: useMutation({ mutationFn: (b: ImageRequest) => apiPost<Media>("/media/images", b), onSuccess: ok, onError }),
    video: useMutation({ mutationFn: (b: VideoRequest) => apiPost<Media>("/media/videos", b), onSuccess: ok, onError }),
    smartmotion: useMutation({ mutationFn: (b: SmartMotionRequest) => apiPost<Media>("/media/smartmotion", b), onSuccess: ok, onError }),
    upload: useMutation({ mutationFn: (b: UploadRequest) => apiPost<Media>("/media/upload", b), onSuccess: ok, onError }),
    cancel: useMutation({ mutationFn: (id: string) => apiPost<Media>(`/media/${id}/cancel`), onSuccess: () => { ok(); toast("Génération annulée"); }, onError }),
    remove: useMutation({ mutationFn: (id: string) => apiDelete<{ ok: boolean }>(`/media/${id}`), onSuccess: ok, onError }),
  };
}

export function useBrandActions() {
  const inv = useInvalidate();
  const onError = (e: unknown) => toast.error(errMsg(e));
  return {
    create: useMutation({ mutationFn: (b: BrandCreate) => apiPost<Brand>("/brands", b), onSuccess: () => { inv("brands"); toast.success("Marque créée"); }, onError }),
    update: useMutation({ mutationFn: ({ id, ...b }: BrandCreate & { id: string }) => apiPut<Brand>(`/brands/${id}`, b), onSuccess: () => { inv("brands"); toast.success("Marque mise à jour"); }, onError }),
    remove: useMutation({ mutationFn: (id: string) => apiDelete<{ ok: boolean }>(`/brands/${id}`), onSuccess: () => inv("brands"), onError }),
  };
}

export const fileToDataUrl = (f: File) =>
  new Promise<string>((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(String(r.result));
    r.onerror = rej;
    r.readAsDataURL(f);
  });
