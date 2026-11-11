import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiGet, apiPost, apiPut } from "@/lib/api";
import { errMsg } from "@/lib/hooks";
import type { ProjectSummary } from "@/lib/types";
import type {
  ComfySettings, ComfyTest, EnginePresets, ImageModelStatus, ImageLora, VideoEngineStatus, CompanyDetail, CompanyOverview, CompanyPoint, CompanySiteRequest, GeoResult, LocalEngine, LocalEngineTest, Sector, QueueState, WebCheckItem, WebStatus, Diagnostic, KitInfo,
} from "@/lib/companyTypes";

export const useSectors = () =>
  useQuery({ queryKey: ["sectors"], queryFn: () => apiGet<Sector[]>("/companies/sectors"), staleTime: Infinity });

export const useOverview = () =>
  useQuery({
    queryKey: ["companies-overview"],
    queryFn: () => apiGet<CompanyOverview>("/companies/overview"),
    refetchInterval: (q) => (q.state.data && q.state.data.departments_ready >= q.state.data.departments_total ? false : 5000),
  });

export interface NearArgs { lat: number; lng: number; radius: number; section: string }
export const useNear = (a: NearArgs | null) =>
  useQuery({
    queryKey: ["companies-near", a],
    queryFn: () =>
      apiGet<CompanyPoint[]>(`/companies/near?lat=${a!.lat}&lng=${a!.lng}&radius=${a!.radius}&section=${a!.section}&pages=4`),
    enabled: !!a,
    staleTime: 10 * 60 * 1000,
    placeholderData: (prev) => prev,
  });

export const useGeocode = (q: string) =>
  useQuery({
    queryKey: ["geocode", q],
    queryFn: () => apiGet<GeoResult[]>(`/companies/geocode?q=${encodeURIComponent(q)}`),
    enabled: q.trim().length >= 3,
    staleTime: Infinity,
  });

export const useCompany = (siren: string | null) =>
  useQuery({ queryKey: ["company", siren], queryFn: () => apiGet<CompanyDetail>(`/companies/${siren}`), enabled: !!siren, staleTime: 30 * 60 * 1000 });

export function useCreateCompanySite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ siren, body }: { siren: string; body: CompanySiteRequest }) => apiPost<ProjectSummary>(`/companies/${siren}/site`, body),
    onSuccess: () => ["projects", "activity"].forEach((k) => qc.invalidateQueries({ queryKey: [k] })),
    onError: (e) => toast.error(errMsg(e)),
  });
}

export const useLocalEngine = () =>
  useQuery({ queryKey: ["local-engine"], queryFn: () => apiGet<LocalEngine>("/settings/local-engine") });

export const useLocalEngineStatus = (cfg: LocalEngine | undefined) =>
  useQuery({
    queryKey: ["local-engine-status", cfg],
    queryFn: () => apiPost<LocalEngineTest>("/settings/local-engine/test", cfg),
    enabled: !!cfg,
    staleTime: 30 * 1000,
  });

export function useSaveLocalEngine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: LocalEngine) => apiPut<LocalEngine>("/settings/local-engine", b),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["local-engine"] });
      toast.success("Moteur local enregistré");
    },
    onError: (e) => toast.error(errMsg(e)),
  });
}

export function useTestLocalEngine() {
  return useMutation({ mutationFn: (b: LocalEngine) => apiPost<LocalEngineTest>("/settings/local-engine/test", b) });
}

export const useComfy = () => useQuery({ queryKey: ["comfy"], queryFn: () => apiGet<ComfySettings>("/settings/comfyui") });
export const useComfyPresets = () =>
  useQuery({ queryKey: ["comfy-presets"], queryFn: () => apiGet<EnginePresets>("/settings/comfyui/presets"), staleTime: Infinity });
export const useVideoEngineStatus = () =>
  useQuery({ queryKey: ["comfy-video-models"], queryFn: () => apiGet<VideoEngineStatus>("/settings/comfyui/video-models"), staleTime: 30_000 });
export const useComfyStatus = (cfg: ComfySettings | undefined) =>
  useQuery({ queryKey: ["comfy-status", cfg], queryFn: () => apiPost<ComfyTest>("/settings/comfyui/test", cfg), enabled: !!cfg, staleTime: 30 * 1000 });
export function useSaveComfy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: ComfySettings) => apiPut<ComfySettings>("/settings/comfyui", b),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["comfy"] });
      toast.success("ComfyUI enregistré");
    },
    onError: (e) => toast.error(errMsg(e)),
  });
}
export const useTestComfy = () => useMutation({ mutationFn: (b: ComfySettings) => apiPost<ComfyTest>("/settings/comfyui/test", b) });

export const useWebStatus = (items: WebCheckItem[]) =>
  useQuery({
    queryKey: ["web-status", items.map((i) => i.siret).join(",")],
    queryFn: () => apiPost<WebStatus[]>("/companies/web-status", { items }),
    enabled: items.length > 0,
    placeholderData: (prev) => prev,
    refetchInterval: (q) => (q.state.data?.some((s) => s.status === "pending") ? 3000 : false),
  });

export const useGpuQueue = () =>
  useQuery({
    queryKey: ["gpu-queue"],
    queryFn: () => apiGet<QueueState>("/queue"),
    refetchInterval: (q) => (q.state.data?.items.length ? 2000 : 8000),
  });

export function useQueueAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: "prioritize" | "cancel" }) => apiPost<QueueState>(`/queue/${id}/${action}`),
    onSuccess: (data) => {
      qc.setQueryData(["gpu-queue"], data);
      ["media", "projects", "activity"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    },
    onError: (e) => toast.error(errMsg(e)),
  });
}

export const useDiagnostic = () =>
  useQuery({ queryKey: ["diagnostic"], queryFn: () => apiGet<Diagnostic>("/diagnostic"), staleTime: 0 });

export const useKitInfo = () => useQuery({ queryKey: ["kit-info"], queryFn: () => apiGet<KitInfo>("/kit/info") });

export const useImageModels = () =>
  useQuery({ queryKey: ["comfy-image-models"], queryFn: () => apiGet<ImageModelStatus[]>("/settings/comfyui/image-models"), staleTime: 15_000 });
export const useImageLoras = (preset?: string | null) =>
  useQuery({ queryKey: ["comfy-image-loras", preset], queryFn: () => apiGet<ImageLora[]>(`/settings/comfyui/loras${preset ? `?preset=${encodeURIComponent(preset)}` : ""}`), staleTime: 30_000 });
