import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Cpu, Crosshair, Globe2, Loader2, MapPinned, Search, Target } from "lucide-react";
import L from "@/lib/leaflet";
import "leaflet.markercluster";
import { AppShell } from "@/components/AppShell";
import { CompanyPanel } from "@/components/CompanyPanel";
import { LocalEngineDialog } from "@/components/LocalEngineDialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useGeocode, useNear, useOverview, useSectors, useWebStatus, type NearArgs } from "@/lib/companyHooks";
import type { CompanyPoint, WebCheckItem, WebStatus } from "@/lib/companyTypes";

const DETAIL_ZOOM = 13;
const FRANCE: L.LatLngTuple = [46.6, 2.4];

function useDebounced<T>(v: T, ms: number): T {
  const [d, setD] = useState(v);
  useEffect(() => {
    const t = window.setTimeout(() => setD(v), ms);
    return () => window.clearTimeout(t);
  }, [v, ms]);
  return d;
}

const CHECK_LIMIT = 120;
const dotIcon = (selected: boolean, web?: WebStatus["status"]) =>
  L.divIcon({ className: "", html: `<span class="co-dot${web ? ` is-${web}` : ""}${selected ? " is-selected" : ""}"></span>`, iconSize: [14, 14], iconAnchor: [7, 7] });

export default function CompanyMap() {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const cluster = useRef<L.MarkerClusterGroup | null>(null);
  const [view, setView] = useState<{ lat: number; lng: number; zoom: number; radius: number }>({ lat: FRANCE[0], lng: FRANCE[1], zoom: 6, radius: 50 });
  const [section, setSection] = useState("all");
  const [selected, setSelected] = useState<CompanyPoint | null>(null);
  const [engineOpen, setEngineOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [showGeo, setShowGeo] = useState(false);
  const [onlyNoSite, setOnlyNoSite] = useState(false);
  const debouncedQuery = useDebounced(query, 350);

  const { data: sectors } = useSectors();
  const { data: overview } = useOverview();
  const sec = section === "all" ? "" : section;
  const nearArgs: NearArgs | null = view.zoom >= DETAIL_ZOOM ? { lat: +view.lat.toFixed(3), lng: +view.lng.toFixed(3), radius: view.radius, section: sec } : null;
  const near = useNear(nearArgs);
  const geo = useGeocode(debouncedQuery);

  const points = useMemo(() => {
    const all = new Map<string, CompanyPoint>();
    for (const p of overview?.points ?? []) if (!sec || p.section === sec) all.set(p.siret, p);
    if (nearArgs) for (const p of near.data ?? []) if (!sec || p.section === sec) all.set(p.siret, p);
    return [...all.values()];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overview, near.data, sec, view.zoom >= DETAIL_ZOOM]);

  // Website presence: checked for the companies closest to the map centre (detail zoom only)
  const checkItems = useMemo<WebCheckItem[]>(() => {
    if (view.zoom < DETAIL_ZOOM) return [];
    const d = (p: CompanyPoint) => (p.lat - view.lat) ** 2 + ((p.lng - view.lng) * Math.cos((view.lat * Math.PI) / 180)) ** 2;
    return [...points].sort((a, b) => d(a) - d(b)).slice(0, CHECK_LIMIT).map((p) => ({ siret: p.siret, name: p.name, city: p.city, lat: p.lat, lng: p.lng }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, view.zoom >= DETAIL_ZOOM ? `${view.lat.toFixed(3)},${view.lng.toFixed(3)}` : ""]);
  const web = useWebStatus(checkItems);
  const webMap = useMemo(() => new Map((web.data ?? []).map((w) => [w.siret, w])), [web.data]);
  const counts = useMemo(() => {
    const c = { none: 0, found: 0, pending: 0 };
    for (const w of web.data ?? []) c[w.status]++;
    return c;
  }, [web.data]);
  const shown = useMemo(() => (onlyNoSite ? points.filter((p) => webMap.get(p.siret)?.status === "none") : points), [points, onlyNoSite, webMap]);
  const prospects = useMemo(() => points.filter((p) => webMap.get(p.siret)?.status === "none").slice(0, 5), [points, webMap]);

  // Map bootstrap (once)
  useEffect(() => {
    if (!host.current || map.current) return;
    const m = L.map(host.current, { center: FRANCE, zoom: 6, minZoom: 5, maxZoom: 19, zoomControl: false, preferCanvas: true });
    L.control.zoom({ position: "bottomleft" }).addTo(m);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · Données SIRENE (INSEE)',
      maxZoom: 19,
    }).addTo(m);
    const cg = L.markerClusterGroup({
      chunkedLoading: true,
      showCoverageOnHover: false,
      maxClusterRadius: 48,
      spiderfyOnMaxZoom: true,
      iconCreateFunction: (c) => {
        const n = c.getChildCount();
        const size = n < 10 ? 34 : n < 100 ? 42 : 52;
        return L.divIcon({ html: `<div class="co-cluster"><span>${n}</span></div>`, className: "", iconSize: [size, size] });
      },
    });
    m.addLayer(cg);
    const sync = () => {
      const c = m.getCenter();
      const radius = Math.min(50, Math.max(0.3, c.distanceTo(m.getBounds().getNorthEast()) / 1000));
      setView({ lat: c.lat, lng: c.lng, zoom: m.getZoom(), radius: +radius.toFixed(1) });
    };
    m.on("moveend", sync);
    map.current = m;
    cluster.current = cg;
    return () => {
      m.remove();
      map.current = null;
    };
  }, []);

  // Render markers when the point set changes
  useEffect(() => {
    const cg = cluster.current;
    if (!cg) return;
    cg.clearLayers();
    cg.addLayers(
      shown.map((p) =>
        L.marker([p.lat, p.lng], { icon: dotIcon(selected?.siret === p.siret, webMap.get(p.siret)?.status), title: p.name, zIndexOffset: webMap.get(p.siret)?.status === "none" ? 1000 : 0 })
          .bindTooltip(`<strong>${p.name.replace(/</g, "&lt;")}</strong><br/><span>${p.city.replace(/</g, "&lt;")}</span>`, { direction: "top", offset: [0, -6], className: "co-tip" })
          .on("click", () => {
            setSelected(p);
            map.current?.panTo([p.lat, p.lng], { animate: true });
          }),
      ),
    );
  }, [shown, webMap, selected?.siret]);

  const flyTo = (lat: number, lng: number, zoom = 15) => {
    map.current?.flyTo([lat, lng], zoom, { duration: 1.4 });
    setShowGeo(false);
  };

  const locate = () => navigator.geolocation?.getCurrentPosition((pos) => flyTo(pos.coords.latitude, pos.coords.longitude, 15));
  const loading = near.isFetching || (overview && overview.departments_ready < overview.departments_total);

  return (
    <AppShell tone="web" full>
      <div className="relative h-[calc(100dvh-104px)] md:h-[calc(100dvh-64px)]">
        <div ref={host} data-testid="company-map" className="co-map absolute inset-0" />

        {/* Command panel */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="absolute left-3 top-3 z-[500] w-[calc(100%-24px)] max-w-[380px] rounded-3xl border border-white/10 bg-panel/80 p-4 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.9)] backdrop-blur-2xl md:left-4 md:top-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="eyebrow flex items-center gap-1.5 text-violet-300"><MapPinned className="size-3.5" /> Prospection</p>
              <h1 className="mt-1 font-heading text-xl font-semibold text-white">Carte des entreprises</h1>
            </div>
            <button type="button" data-testid="map-engine-settings" onClick={() => setEngineOpen(true)} className="inline-flex h-9 items-center gap-1.5 rounded-full border border-white/10 px-3 text-xs text-slate-300 transition-[border-color,color] duration-200 hover:border-violet-400/50 hover:text-white">
              <Cpu className="size-3.5" /> Moteur local
            </button>
          </div>

          <div className="relative mt-3">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
            <Input
              data-testid="map-search-input"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setShowGeo(true); }}
              onFocus={() => setShowGeo(true)}
              placeholder="Ville, code postal ou adresse…"
              className="border-white/10 bg-black/40 pl-9"
            />
            <AnimatePresence>
              {showGeo && geo.data && geo.data.length > 0 && (
                <motion.ul initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="absolute inset-x-0 top-full z-10 mt-1 overflow-hidden rounded-xl border border-white/10 bg-panel/95 backdrop-blur-xl" data-testid="map-search-results">
                  {geo.data.map((g, i) => (
                    <li key={`${g.label}-${i}`}>
                      <button type="button" data-testid={`map-search-result-${i}`} onClick={() => { setQuery(g.label); flyTo(g.lat, g.lng, g.type === "municipality" ? 14 : 17); }} className="block w-full px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:bg-violet-500/15">
                        {g.label}
                      </button>
                    </li>
                  ))}
                </motion.ul>
              )}
            </AnimatePresence>
          </div>

          <div className="mt-2 flex gap-2">
            <Select value={section} onValueChange={(v: string) => setSection(v)}>
              <SelectTrigger data-testid="map-sector-select" className="w-full min-w-0 border-white/10 bg-black/40 text-xs">
                <SelectValue>{(v) => (v === "all" ? "Tous les secteurs" : sectors?.find((s) => s.code === v)?.label ?? v)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les secteurs</SelectItem>
                {sectors?.map((s) => <SelectItem key={s.code} value={s.code}>{s.label}</SelectItem>)}
              </SelectContent>
            </Select>
            <button type="button" data-testid="map-locate" onClick={locate} title="Me localiser" className="inline-flex size-9 shrink-0 items-center justify-center rounded-md border border-white/10 bg-black/40 text-slate-300 transition-colors hover:text-white">
              <Crosshair className="size-4" />
            </button>
          </div>

          <div className="mt-3 flex items-center justify-between text-[11px]">
            <span data-testid="map-points-count" className="font-mono text-slate-300">{shown.length.toLocaleString("fr-FR")} entreprises affichées</span>
            {loading ? <span className="flex items-center gap-1 text-violet-300" data-testid="map-loading"><Loader2 className="size-3 animate-spin" /> chargement</span> : null}
          </div>
          <div className="mt-3 rounded-2xl border border-white/[0.07] bg-black/30 p-3">
            <label className="flex items-center justify-between gap-3 text-xs text-slate-200">
              <span className="flex items-center gap-1.5"><Target className="size-3.5 text-rose-300" /> Seulement les entreprises sans site web</span>
              <Switch data-testid="map-filter-nosite" checked={onlyNoSite} onCheckedChange={(v: boolean) => setOnlyNoSite(v)} />
            </label>
            {view.zoom >= DETAIL_ZOOM ? (
              <p data-testid="map-web-counts" className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[10px] text-slate-400">
                <span className="text-rose-300">● {counts.none} sans site</span>
                <span className="text-emerald-300">● {counts.found} avec site</span>
                {counts.pending > 0 && <span className="flex items-center gap-1"><Loader2 className="size-3 animate-spin" />{counts.pending} en vérification</span>}
              </p>
            ) : (
              <p className="mt-2 text-[10px] text-slate-500">Zoomez sur une ville : les {CHECK_LIMIT} entreprises les plus proches du centre sont vérifiées (domaines probables + contenu de la page).</p>
            )}
            {prospects.length > 0 && (
              <ul className="mt-2 space-y-1" data-testid="map-prospects">
                {prospects.map((p) => (
                  <li key={p.siret}>
                    <button type="button" data-testid={`map-prospect-${p.siret}`} onClick={() => { setSelected(p); map.current?.panTo([p.lat, p.lng]); }} className="flex w-full items-center gap-2 rounded-lg px-2 py-1 text-left text-[11px] text-slate-300 transition-colors hover:bg-rose-500/10 hover:text-white">
                      <Globe2 className="size-3 shrink-0 text-rose-300" /><span className="truncate">{p.name}</span><span className="ml-auto shrink-0 text-slate-500">{p.city}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <p data-testid="map-hint" className="mt-1 text-[11px] leading-relaxed text-slate-500">
            {view.zoom >= DETAIL_ZOOM
              ? "Toutes les entreprises actives de la zone sont chargées depuis le registre officiel SIRENE."
              : overview && overview.departments_ready < overview.departments_total
                ? `Exploration de la France : ${overview.departments_ready}/${overview.departments_total} départements…`
                : "Zoomez sur une ville pour afficher toutes ses entreprises."}
          </p>
        </motion.div>

        <AnimatePresence>
          {selected && <CompanyPanel key={selected.siret} point={selected} web={webMap.get(selected.siret)} onClose={() => setSelected(null)} onOpenEngine={() => setEngineOpen(true)} />}
        </AnimatePresence>
        <LocalEngineDialog open={engineOpen} onOpenChange={setEngineOpen} />
      </div>
    </AppShell>
  );
}
