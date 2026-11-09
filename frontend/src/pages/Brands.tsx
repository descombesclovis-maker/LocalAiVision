import { useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Loader2, Pencil, Plus, Stamp, Trash2, Upload, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { FxButton } from "@/components/FxButton";
import { TiltCard } from "@/components/TiltCard";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fileToDataUrl, useBrandActions, useBrands, useMediaActions } from "@/lib/hooks";
import type { Brand, BrandCreate } from "@/lib/types";
import { mediaFileUrl } from "@/lib/types";

const EMPTY: BrandCreate = { name: "", slogan: "", colors: ["#8B5CF6", "#06B6D4"], logo_media_id: null };

export default function Brands() {
  const { data, isError } = useBrands();
  const { create, update, remove } = useBrandActions();
  const { upload } = useMediaActions();
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Brand | null>(null);
  const [form, setForm] = useState<BrandCreate>(EMPTY);
  const fileRef = useRef<HTMLInputElement>(null);

  const start = (b: Brand | null) => {
    setEdit(b);
    setForm(b ? { name: b.name, slogan: b.slogan, colors: b.colors, logo_media_id: b.logo_media_id } : EMPTY);
    setOpen(true);
  };
  const submit = () => {
    const done = { onSuccess: () => setOpen(false) };
    if (edit) update.mutate({ id: edit.id, ...form }, done);
    else create.mutate(form, done);
  };

  return (
    <AppShell>
      <section className="mx-auto max-w-[1440px] px-4 pb-24 pt-12 md:px-6">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="eyebrow text-slate-400">Partagées entre LocalAiWeb et LocalAiVision</p>
            <h1 className="mt-3 text-4xl font-semibold md:text-6xl"><span className="text-gradient-duo">Identités</span> de marque</h1>
            <p className="mt-3 max-w-lg text-slate-400">Nom, logo, couleurs et slogan, réutilisés par le générateur de sites et l'atelier publicité.</p>
          </div>
          <FxButton size="lg" data-testid="brand-new" onClick={() => start(null)}><Plus className="size-4" /> Nouvelle marque</FxButton>
        </div>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence>
            {data?.map((b, i) => (
              <motion.div key={b.id} layout initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ delay: i * 0.05 }}>
                <TiltCard className="rounded-3xl" data-testid={`brand-card-${b.id}`}>
                  <div className="glass relative overflow-hidden rounded-3xl p-6">
                    <div className="absolute inset-x-0 top-0 h-28 opacity-60" style={{ background: `linear-gradient(120deg, ${b.colors[0] ?? "#8B5CF6"}55, ${b.colors[1] ?? "#06B6D4"}33, transparent)` }} />
                    <div className="relative flex items-start gap-4">
                      <div className="flex size-16 items-center justify-center overflow-hidden rounded-2xl border border-white/15 bg-black/40">
                        {b.logo_media_id ? <img src={mediaFileUrl(b.logo_media_id)} alt={b.name} className="size-full object-contain p-1.5" /> : <Stamp className="size-6 text-slate-400" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate font-heading text-xl font-semibold">{b.name}</h3>
                        <p className="mt-1 text-sm italic text-slate-300">{b.slogan || "Sans slogan"}</p>
                      </div>
                    </div>
                    <div className="relative mt-6 flex items-center gap-2">
                      {b.colors.map((c) => <span key={c} title={c} className="size-8 rounded-full border border-white/20 shadow-lg transition-transform hover:scale-125" style={{ background: c }} />)}
                      <div className="ml-auto flex gap-1">
                        <button type="button" data-testid={`brand-edit-${b.id}`} onClick={() => start(b)} className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Modifier"><Pencil className="size-4" /></button>
                        <button type="button" data-testid={`brand-delete-${b.id}`} onClick={() => { if (window.confirm(`Supprimer ${b.name} ?`)) remove.mutate(b.id); }} className="rounded-lg p-2 text-slate-400 hover:bg-red-500/10 hover:text-red-300" aria-label="Supprimer"><Trash2 className="size-4" /></button>
                      </div>
                    </div>
                  </div>
                </TiltCard>
              </motion.div>
            ))}
          </AnimatePresence>
          {!data?.length && <div className="glass col-span-full flex min-h-48 items-center justify-center rounded-3xl text-sm text-slate-400" data-testid="brands-empty">{isError ? "Marques momentanément indisponibles." : "Aucune marque. Créez la première !"}</div>}
        </div>
      </section>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="border-white/10 bg-panel/95 backdrop-blur-2xl" data-testid="brand-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">{edit ? "Modifier la marque" : "Nouvelle marque"}</DialogTitle>
            <DialogDescription>Le logo est utilisé tel quel dans les sites et les publicités.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <button type="button" data-testid="brand-logo-upload" onClick={() => fileRef.current?.click()} className="flex size-20 items-center justify-center overflow-hidden rounded-2xl border border-dashed border-white/20 bg-black/30 transition-colors hover:border-violet-300">
                {upload.isPending ? <Loader2 className="size-5 animate-spin" /> : form.logo_media_id ? <img src={mediaFileUrl(form.logo_media_id)} alt="" className="size-full object-contain p-1" /> : <Upload className="size-5 text-slate-400" />}
              </button>
              <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={async (e) => {
                const f = e.target.files?.[0];
                if (f) upload.mutate({ data_url: await fileToDataUrl(f), source: "logo", prompt: `Logo ${form.name}` }, { onSuccess: (m) => setForm((s) => ({ ...s, logo_media_id: m.id })) });
              }} />
              <p className="text-xs text-slate-400">Logo PNG transparent recommandé.</p>
            </div>
            <div className="space-y-1.5"><Label className="text-xs text-slate-400">Nom</Label><Input data-testid="brand-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="border-white/10 bg-black/30" /></div>
            <div className="space-y-1.5"><Label className="text-xs text-slate-400">Slogan</Label><Input data-testid="brand-slogan" value={form.slogan} onChange={(e) => setForm({ ...form, slogan: e.target.value })} className="border-white/10 bg-black/30" /></div>
            <div className="space-y-1.5">
              <Label className="text-xs text-slate-400">Couleurs</Label>
              <div className="flex flex-wrap items-center gap-2">
                {form.colors.map((c, i) => (
                  <div key={i} className="relative">
                    <input type="color" data-testid={`brand-color-${i}`} value={c} onChange={(e) => setForm({ ...form, colors: form.colors.map((x, k) => (k === i ? e.target.value : x)) })} className="size-10 cursor-pointer rounded-full border border-white/20 bg-transparent" />
                    <button type="button" onClick={() => setForm({ ...form, colors: form.colors.filter((_, k) => k !== i) })} className="absolute -right-1 -top-1 rounded-full bg-panel p-0.5 text-slate-400 hover:text-white" aria-label="Retirer"><X className="size-3" /></button>
                  </div>
                ))}
                {form.colors.length < 5 && <button type="button" data-testid="brand-color-add" onClick={() => setForm({ ...form, colors: [...form.colors, "#ffffff"] })} className="flex size-10 items-center justify-center rounded-full border border-dashed border-white/20 text-slate-400 hover:text-white"><Plus className="size-4" /></button>}
              </div>
            </div>
            <FxButton className="w-full" data-testid="brand-submit" disabled={!form.name.trim() || create.isPending || update.isPending} onClick={submit}>{edit ? "Enregistrer" : "Créer la marque"}</FxButton>
          </div>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
