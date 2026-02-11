"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Loader2, Plus, Trash2 } from "lucide-react";
import { api, type Gym, type TenantRoutineTemplate, type TenantRoutineTemplateAssignment } from "@/lib/api";

export default function GymRutinasPage({ params }: { params: { id: string } }) {
  const gymId = useMemo(() => Number(params.id) || 0, [params.id]);
  const [gym, setGym] = useState<Gym | null>(null);
  const [loading, setLoading] = useState(true);

  const [catalog, setCatalog] = useState<TenantRoutineTemplate[]>([]);
  const [assignments, setAssignments] = useState<TenantRoutineTemplateAssignment[]>([]);
  const [busy, setBusy] = useState(false);

  const [assignTemplateId, setAssignTemplateId] = useState<number>(0);
  const [assignTemplatePriority, setAssignTemplatePriority] = useState<number>(0);
  const [assignTemplateNotes, setAssignTemplateNotes] = useState<string>("");
  const [assignTemplateActive, setAssignTemplateActive] = useState<boolean>(true);

  const reload = useCallback(async () => {
    if (!gymId) return;
    setBusy(true);
    try {
      const [catRes, asgRes] = await Promise.all([
        api.getGymRoutineTemplateCatalog(gymId),
        api.getGymRoutineTemplateAssignments(gymId),
      ]);
      if (catRes.ok && catRes.data?.ok) setCatalog(catRes.data.templates || []);
      if (asgRes.ok && asgRes.data?.ok) setAssignments(asgRes.data.assignments || []);
    } finally {
      setBusy(false);
    }
  }, [gymId]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!gymId) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const gymRes = await api.getGym(gymId);
        if (mounted && gymRes.ok && gymRes.data) setGym(gymRes.data);
        await reload();
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [gymId, reload]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
      </div>
    );
  }

  if (!gymId || !gym) {
    return (
      <div className="text-center py-16">
        <p className="text-slate-500">Gimnasio no encontrado</p>
        <Link href="/dashboard/gyms" className="text-primary-400 hover:text-primary-300 mt-2 inline-block">
          Volver a gimnasios
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/dashboard/gyms/${gymId}`} className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="page-title">Rutinas / Templates</h1>
          <p className="text-slate-400">
            {gym.nombre} · ID: {gym.id}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => {
              try {
                window.localStorage.setItem("ironhub_admin_selected_gym_id", String(gymId));
              } catch {
              }
              window.location.href = "/dashboard/templates";
            }}
            className="btn-secondary"
          >
            Administrar templates
          </button>
          <button onClick={() => void reload()} disabled={busy} className="btn-secondary flex items-center gap-2">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Actualizar"}
          </button>
        </div>
      </div>

      <div className="card p-6 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-3">
            <div className="text-white font-medium">Asignar template al gimnasio</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label className="label">Template</label>
                <select
                  className="input"
                  value={assignTemplateId ? String(assignTemplateId) : ""}
                  onChange={(e) => setAssignTemplateId(Number(e.target.value) || 0)}
                >
                  <option value="">Seleccionar…</option>
                  {catalog.map((t) => (
                    <option key={t.id} value={String(t.id)}>
                      {t.nombre} {t.dias_semana ? `(${t.dias_semana} días)` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Prioridad</label>
                <input
                  className="input"
                  type="number"
                  value={String(assignTemplatePriority)}
                  onChange={(e) => setAssignTemplatePriority(Number(e.target.value) || 0)}
                />
              </div>
            </div>
            <div>
              <label className="label">Notas</label>
              <input
                className="input"
                value={assignTemplateNotes}
                onChange={(e) => setAssignTemplateNotes(e.target.value)}
                placeholder="Opcional"
              />
            </div>
            <div className="flex items-center justify-between gap-3">
              <label className="flex items-center gap-2 text-slate-300 text-sm">
                <input
                  type="checkbox"
                  checked={assignTemplateActive}
                  onChange={(e) => setAssignTemplateActive(Boolean(e.target.checked))}
                />
                Activo
              </label>
              <button
                className="btn-primary flex items-center gap-2"
                disabled={busy || !assignTemplateId}
                onClick={async () => {
                  if (!assignTemplateId) return;
                  setBusy(true);
                  try {
                    const res = await api.assignGymRoutineTemplate(gymId, {
                      template_id: assignTemplateId,
                      activa: assignTemplateActive,
                      prioridad: assignTemplatePriority,
                      notas: assignTemplateNotes ? assignTemplateNotes : null,
                    });
                    if (res.ok && res.data?.ok) {
                      setAssignTemplateId(0);
                      setAssignTemplatePriority(0);
                      setAssignTemplateNotes("");
                      setAssignTemplateActive(true);
                      await reload();
                    }
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <Plus className="w-4 h-4" />
                Asignar
              </button>
            </div>
            <div className="text-xs text-slate-500">
              Estos templates son el formato del PDF/export. Se consumen desde Gestión al crear rutinas o plantillas.
            </div>
          </div>

          <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-3">
            <div className="text-white font-medium">Asignaciones actuales</div>
            {busy ? (
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                Cargando…
              </div>
            ) : assignments.length ? (
              <div className="space-y-2">
                {assignments.map((a) => (
                  <div key={a.assignment_id} className="p-3 rounded-lg bg-slate-900/40 border border-slate-800">
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-white font-medium truncate">{a.nombre}</div>
                        <div className="text-xs text-slate-500">
                          {a.categoria || "general"}
                          {a.dias_semana ? ` • ${a.dias_semana} días` : ""}
                          {a.publica ? " • público" : ""}
                        </div>
                      </div>
                      <button
                        className="btn-secondary flex items-center gap-2"
                        onClick={async () => {
                          if (!confirm("Quitar asignación?")) return;
                          setBusy(true);
                          try {
                            await api.deleteGymRoutineTemplateAssignment(gymId, a.assignment_id);
                            await reload();
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
                      <label className="flex items-center gap-2 text-slate-300 text-sm">
                        <input
                          type="checkbox"
                          checked={Boolean(a.activa)}
                          onChange={(e) => {
                            const v = Boolean(e.target.checked);
                            setAssignments((prev) => prev.map((x) => (x.assignment_id === a.assignment_id ? { ...x, activa: v } : x)));
                          }}
                        />
                        Activo
                      </label>
                      <div>
                        <label className="label">Prioridad</label>
                        <input
                          className="input"
                          type="number"
                          value={String(a.prioridad || 0)}
                          onChange={(e) => {
                            const v = Number(e.target.value) || 0;
                            setAssignments((prev) => prev.map((x) => (x.assignment_id === a.assignment_id ? { ...x, prioridad: v } : x)));
                          }}
                        />
                      </div>
                      <div>
                        <label className="label">Notas</label>
                        <input
                          className="input"
                          value={String(a.notas || "")}
                          onChange={(e) => {
                            const v = e.target.value;
                            setAssignments((prev) => prev.map((x) => (x.assignment_id === a.assignment_id ? { ...x, notas: v } : x)));
                          }}
                        />
                      </div>
                    </div>

                    <div className="flex justify-end mt-3">
                      <button
                        className="btn-primary"
                        disabled={busy}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            const cur = assignments.find((x) => x.assignment_id === a.assignment_id);
                            if (!cur) return;
                            await api.updateGymRoutineTemplateAssignment(gymId, cur.assignment_id, {
                              activa: Boolean(cur.activa),
                              prioridad: Number(cur.prioridad || 0),
                              notas: cur.notas ?? null,
                            });
                            await reload();
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Guardar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-400 text-sm">Sin asignaciones</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
