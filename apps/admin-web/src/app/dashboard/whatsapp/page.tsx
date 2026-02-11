'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Loader2, Send, Check, X, ExternalLink, Save, Trash2, RefreshCw, ArrowUpRight } from 'lucide-react';
import { api, type Gym, type WhatsAppTemplateCatalogItem } from '@/lib/api';
import Link from 'next/link';

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;

export default function WhatsAppPage() {
    const [gyms, setGyms] = useState<Gym[]>([]);
    const [loading, setLoading] = useState(true);
    const [gymSearch, setGymSearch] = useState('');
    const [uiMsg, setUiMsg] = useState<{ type: 'ok' | 'error' | 'info'; text: string } | null>(null);
    const [testNumber, setTestNumber] = useState('');
    const [testMessage, setTestMessage] = useState('Mensaje de prueba');
    const [testGymId, setTestGymId] = useState<number | null>(null);
    const [sending, setSending] = useState(false);

    const [templates, setTemplates] = useState<WhatsAppTemplateCatalogItem[]>([]);
    const [templatesLoading, setTemplatesLoading] = useState(true);
    const [bindings, setBindings] = useState<Record<string, string>>({});
    const [bindingsLoading, setBindingsLoading] = useState(true);
    const [savingBindingKey, setSavingBindingKey] = useState<string>('');
    const [editing, setEditing] = useState<Partial<WhatsAppTemplateCatalogItem>>({
        template_name: '',
        category: 'UTILITY',
        language: 'es_AR',
        body_text: '',
        active: true,
        version: 1,
        example_params: [],
    });
    const [savingTemplate, setSavingTemplate] = useState(false);
    const [syncingDefaults, setSyncingDefaults] = useState(false);
    const [actionSpecs, setActionSpecs] = useState<
        Array<{ action_key: string; label: string; required_params: number; default_enabled?: boolean; default_template_name?: string }>
    >([]);
    const [actionSpecsLoading, setActionSpecsLoading] = useState(true);
    const [selectedGymId, setSelectedGymId] = useState<number | null>(null);
    const [gymHealth, setGymHealth] = useState<unknown>(null);
    const [gymActions, setGymActions] = useState<
        Array<{
            action_key: string;
            enabled: boolean;
            template_name: string;
            required_params: number;
            default_enabled?: boolean;
            default_template_name?: string;
        }>
    >([]);
    const [gymEvents, setGymEvents] = useState<Array<{ event_type: string; severity: string; message: string; details: unknown; created_at: string }>>([]);
    const [gymLoading, setGymLoading] = useState(false);
    const [provisioning, setProvisioning] = useState(false);
    const [savingGymAction, setSavingGymAction] = useState('');
    const [savingAllGymActions, setSavingAllGymActions] = useState(false);

    useEffect(() => {
        async function load() {
            setLoading(true);
            try {
                const res = await api.getGyms({ page_size: 100 });
                if (res.ok && res.data) {
                    setGyms(res.data.gyms || []);
                }
            } catch {
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    const loadTemplates = async () => {
        setTemplatesLoading(true);
        try {
            const res = await api.getWhatsAppTemplateCatalog(false);
            if (res.ok && res.data) {
                setTemplates(res.data.templates || []);
            }
        } finally {
            setTemplatesLoading(false);
        }
    };

    const loadBindings = async () => {
        setBindingsLoading(true);
        try {
            const res = await api.getWhatsAppTemplateBindings();
            if (res.ok && res.data) {
                setBindings(res.data.bindings || {});
            }
        } finally {
            setBindingsLoading(false);
        }
    };

    const loadActionSpecs = async () => {
        setActionSpecsLoading(true);
        try {
            const res = await api.getWhatsAppActionSpecs();
            if (res.ok && res.data) {
                setActionSpecs(res.data.items || []);
            }
        } finally {
            setActionSpecsLoading(false);
        }
    };

    const handleSyncDefaults = async () => {
        setSyncingDefaults(true);
        try {
            const res = await api.syncWhatsAppTemplateDefaults(true);
            if (!res.ok || !res.data) {
                setUiMsg({ type: 'error', text: res.error || 'Error sincronizando defaults' });
                return;
            }
            if ((res.data.failed || []).length > 0) {
                setUiMsg({ type: 'error', text: `Sincronizado con fallas: ${(res.data.failed || []).length}` });
            } else {
                setUiMsg({ type: 'ok', text: `Sincronizado: created=${res.data.created}, updated=${res.data.updated}` });
            }
            await loadTemplates();
            await loadBindings();
        } finally {
            setSyncingDefaults(false);
        }
    };

    useEffect(() => {
        loadTemplates();
        loadBindings();
        loadActionSpecs();
    }, []);

    const handleBumpVersion = async (templateName: string) => {
        const name = String(templateName || '').trim();
        if (!name) return;
        if (!confirm(`Crear nueva versión a partir de ${name}?`)) return;
        const res = await api.bumpWhatsAppTemplateVersion(name);
        if (!res.ok || !res.data) {
            setUiMsg({ type: 'error', text: res.error || 'Error bumping version' });
            return;
        }
        setUiMsg({ type: 'ok', text: `Nueva versión creada: ${res.data.new_template_name}` });
        await loadTemplates();
        await loadBindings();
    };

    const handleSaveBinding = async (bindingKey: string, templateName: string) => {
        const k = String(bindingKey || '').trim();
        const t = String(templateName || '').trim();
        if (!k || !t) return;
        setSavingBindingKey(k);
        try {
            const res = await api.upsertWhatsAppTemplateBinding(k, t);
            if (!res.ok) {
                setUiMsg({ type: 'error', text: res.error || 'Error guardando binding' });
                return;
            }
            setUiMsg({ type: 'ok', text: `Binding guardado: ${k} → ${t}` });
            await loadBindings();
        } finally {
            setSavingBindingKey('');
        }
    };

    const countMetaParams = (bodyText: string) => {
        const matches = String(bodyText || '').match(/\{\{(\d+)\}\}/g) || [];
        const nums = matches
            .map((m) => {
                const n = m.replace(/[^\d]/g, '');
                return Number(n);
            })
            .filter((n) => Number.isFinite(n) && n > 0);
        return nums.length ? Math.max(...nums) : 0;
    };

    const splitTemplateVersion = (templateName: string) => {
        const s = String(templateName || '').trim();
        const m = s.match(/^(.+)_v(\d+)$/);
        if (!m || !m[1]) return { base: s, v: null as number | null };
        const base = String(m[1]);
        const vRaw = m[2];
        const v = vRaw ? Number(vRaw) : NaN;
        return { base, v: Number.isFinite(v) ? v : null };
    };

    const activeCatalogByName = useMemo(() => {
        const m = new Map<string, WhatsAppTemplateCatalogItem>();
        for (const t of templates || []) {
            const name = String(t?.template_name || '').trim();
            if (!name) continue;
            if (t?.active) m.set(name, t);
        }
        return m;
    }, [templates]);

    const gymMetaTemplates = useMemo(() => {
        const rec = isRecord(gymHealth) ? gymHealth : {};
        const list = rec.templates_list;
        return Array.isArray(list) ? list : [];
    }, [gymHealth]);

    const gymMetaByName = useMemo(() => {
        const m = new Map<string, { name: string; status: string; category: string; language: string }>();
        for (const t of gymMetaTemplates) {
            const rec = isRecord(t) ? t : {};
            const n = String(rec.name || '').trim();
            if (!n) continue;
            m.set(n, {
                name: n,
                status: String(rec.status || ''),
                category: String(rec.category || ''),
                language: String(rec.language || ''),
            });
        }
        return m;
    }, [gymMetaTemplates]);

    const buildActionTemplateOptions = useCallback(
        (action: { required_params: number; template_name: string; default_template_name?: string }) => {
            const required = Number(action?.required_params || 0);
            const catalogCandidates = (templates || [])
                .filter((t) => Boolean(t?.active))
                .filter((t) => countMetaParams(String(t?.body_text || '')) === required)
                .map((t) => String(t?.template_name || '').trim())
                .filter(Boolean);

            const bases = new Set<string>();
            for (const n of catalogCandidates) {
                bases.add(splitTemplateVersion(n).base);
            }

            const metaCandidates = (gymMetaTemplates || [])
                .map((t) => (isRecord(t) ? String(t.name || '').trim() : ''))
                .filter(Boolean)
                .filter((n) => bases.has(splitTemplateVersion(n).base));

            const current = String(action?.template_name || '').trim();
            const fallback = String(action?.default_template_name || '').trim();

            const names = Array.from(new Set<string>([...catalogCandidates, ...metaCandidates, current, fallback].filter(Boolean)));

            const scored = names.map((name) => {
                const meta = gymMetaByName.get(name);
                const status = String(meta?.status || '').toUpperCase();
                const inCatalog = activeCatalogByName.has(name);
                const isApproved = !status ? true : status === 'APPROVED';
                const disabled = !inCatalog || !isApproved;
                const notes = [
                    !inCatalog ? 'NO_CATÁLOGO' : null,
                    status && status !== 'APPROVED' ? `NO_APROBADO:${status}` : null,
                ]
                    .filter(Boolean)
                    .join(' · ');
                const extra = [
                    status ? status : null,
                    meta?.category ? String(meta.category).toUpperCase() : null,
                    meta?.language ? String(meta.language) : null,
                    notes ? notes : null,
                ]
                    .filter(Boolean)
                    .join(' · ');
                const label = extra ? `${name} — ${extra}` : name;
                const { base, v } = splitTemplateVersion(name);
                return { name, label, disabled, base, v: v ?? 0, status, inCatalog };
            });

            scored.sort((a, b) => {
                if (a.base !== b.base) return a.base.localeCompare(b.base);
                if (a.v !== b.v) return b.v - a.v;
                if (a.status !== b.status) {
                    if (a.status === 'APPROVED') return -1;
                    if (b.status === 'APPROVED') return 1;
                }
                return a.name.localeCompare(b.name);
            });

            return scored;
        },
        [templates, gymMetaTemplates, gymMetaByName, activeCatalogByName]
    );

    const buildBindingTemplateOptions = useCallback(
        (spec: { action_key: string; required_params: number; default_template_name?: string }) => {
            const required = Number(spec?.required_params || 0);
            const current = String(bindings?.[spec.action_key] || '').trim();
            const fallback = String(spec?.default_template_name || '').trim();

            const catalogCandidates = (templates || [])
                .filter((t) => Boolean(t?.active))
                .filter((t) => countMetaParams(String(t?.body_text || '')) === required)
                .map((t) => String(t?.template_name || '').trim())
                .filter(Boolean);

            const names = Array.from(new Set<string>([...catalogCandidates, current, fallback].filter(Boolean)));

            const scored = names.map((name) => {
                const cat = activeCatalogByName.get(name);
                const inCatalog = Boolean(cat);
                const paramsOk = inCatalog ? countMetaParams(String(cat?.body_text || '')) === required : false;
                const disabled = !inCatalog || !paramsOk;
                const notes = [
                    !inCatalog ? 'NO_CATÁLOGO' : null,
                    inCatalog && !paramsOk ? 'PARAMS_NO_COMPATIBLES' : null,
                ]
                    .filter(Boolean)
                    .join(' · ');
                const label = notes ? `${name} — ${notes}` : name;
                return { name, label, disabled };
            });

            scored.sort((a, b) => a.name.localeCompare(b.name));
            return scored;
        },
        [bindings, templates, activeCatalogByName]
    );

    const loadSelectedGymData = useCallback(
        async (gymId: number) => {
            setGymLoading(true);
            try {
                const [aRes, hRes, eRes] = await Promise.all([
                    api.getGymWhatsAppActions(gymId),
                    api.getGymWhatsAppHealth(gymId),
                    api.getGymWhatsAppOnboardingEvents(gymId, 50),
                ]);

                if (aRes.ok && aRes.data?.ok) {
                    setGymActions(aRes.data.actions || []);
                } else {
                    setGymActions([]);
                    setUiMsg({ type: 'error', text: aRes.error || 'Error cargando acciones' });
                }

                if (hRes.ok && hRes.data) {
                    setGymHealth(hRes.data);
                    if (isRecord(hRes.data) && hRes.data.ok === false) {
                        setUiMsg({ type: 'error', text: String(hRes.data.error || 'Health check falló') });
                    }
                } else {
                    setGymHealth(null);
                }

                if (eRes.ok && eRes.data?.ok) {
                    setGymEvents(eRes.data.events || []);
                } else {
                    setGymEvents([]);
                }
            } finally {
                setGymLoading(false);
            }
        },
        []
    );

    useEffect(() => {
        if (!selectedGymId) {
            setGymHealth(null);
            setGymActions([]);
            setGymEvents([]);
            return;
        }
        loadSelectedGymData(selectedGymId);
    }, [selectedGymId, loadSelectedGymData]);

    const autoPickGymActionTemplates = () => {
        setGymActions((prev) =>
            prev.map((a) => {
                const opts = buildActionTemplateOptions(a);
                const baseWanted = splitTemplateVersion(String(a.default_template_name || a.template_name || '')).base;
                const preferred = opts.filter((o) => !o.disabled && o.base === baseWanted);
                const fallback = opts.filter((o) => !o.disabled);
                const chosen = (preferred[0] || fallback[0])?.name;
                if (!chosen) return a;
                if (String(a.template_name || '').trim() === chosen) return a;
                return { ...a, template_name: chosen };
            })
        );
        setUiMsg({ type: 'ok', text: 'Auto-selección aplicada (solo APPROVED + activo en catálogo)' });
    };

    const saveGymAction = async (actionKey: string) => {
        if (!selectedGymId) return;
        const item = gymActions.find((a) => a.action_key === actionKey);
        if (!item) return;
        setSavingGymAction(actionKey);
        try {
            const res = await api.setGymWhatsAppAction(selectedGymId, actionKey, Boolean(item.enabled), String(item.template_name || ''));
            if (res.ok) {
                setUiMsg({ type: 'ok', text: 'Acción guardada' });
            } else {
                setUiMsg({ type: 'error', text: res.error || 'Error' });
            }
        } finally {
            setSavingGymAction('');
            try {
                await loadSelectedGymData(selectedGymId);
            } catch {
            }
        }
    };

    const saveAllGymActions = async () => {
        if (!selectedGymId || savingAllGymActions) return;
        setSavingAllGymActions(true);
        const failed: Array<{ action_key: string; error: string }> = [];
        let saved = 0;
        try {
            for (const a of gymActions) {
                try {
                    const res = await api.setGymWhatsAppAction(selectedGymId, a.action_key, Boolean(a.enabled), String(a.template_name || ''));
                    if (res.ok) {
                        saved += 1;
                    } else {
                        failed.push({ action_key: a.action_key, error: res.error || 'Error' });
                    }
                } catch (e: unknown) {
                    const msg =
                        typeof e === 'object' && e !== null && 'message' in e
                            ? String((e as Record<string, unknown>).message || 'Error')
                            : 'Error';
                    failed.push({ action_key: a.action_key, error: msg });
                }
            }
        } finally {
            setSavingAllGymActions(false);
        }
        if (failed.length) {
            setUiMsg({ type: 'error', text: `Guardado parcial: ok=${saved}, fallidos=${failed.length}` });
        } else {
            setUiMsg({ type: 'ok', text: `Guardado OK: ${saved} acciones` });
        }
        await loadSelectedGymData(selectedGymId);
    };

    const handleProvisionTemplatesSelectedGym = async () => {
        if (!selectedGymId) return;
        setProvisioning(true);
        try {
            const res = await api.provisionGymWhatsAppTemplates(selectedGymId);
            if (!res.ok || !res.data) {
                setUiMsg({ type: 'error', text: res.error || 'Error provisionando templates' });
                return;
            }
            const failed = res.data.failed || [];
            if (Array.isArray(failed) && failed.length) {
                setUiMsg({ type: 'error', text: `Provisionado con fallas: ${failed.length}` });
            } else {
                setUiMsg({ type: 'ok', text: `Provisionado OK: created=${(res.data.created || []).length}` });
            }
            await loadTemplates();
            await loadBindings();
            await loadSelectedGymData(selectedGymId);
        } finally {
            setProvisioning(false);
        }
    };

    const configuredGyms = gyms.filter((g) => g.wa_configured);
    const notConfiguredGyms = gyms.filter((g) => !g.wa_configured);
    const filteredGyms = gyms.filter((g) => {
        const q = String(gymSearch || '').trim().toLowerCase();
        if (!q) return true;
        const name = String(g.nombre || '').toLowerCase();
        const sub = String(g.subdominio || '').toLowerCase();
        return name.includes(q) || sub.includes(q);
    });
    const configuredGymsFiltered = configuredGyms.filter((g) => filteredGyms.some((x) => x.id === g.id));
    const actionLabelByKey = useMemo(() => {
        const out: Record<string, string> = {};
        for (const s of actionSpecs) {
            const k = String(s?.action_key || '').trim();
            if (!k) continue;
            out[k] = String(s?.label || k);
        }
        return out;
    }, [actionSpecs]);

    const gymHealthInfo = useMemo(() => {
        const rec = isRecord(gymHealth) ? gymHealth : {};
        const ok = Boolean(rec.ok);
        const templatesRec = isRecord(rec.templates) ? rec.templates : {};
        const templatesCount = Number(templatesRec.count ?? rec.templates_count ?? gymMetaTemplates.length) || 0;
        const approved = Number(templatesRec.approved ?? 0) || 0;
        const err = rec.error ? String(rec.error) : null;
        return { ok, templatesCount, approved, error: err };
    }, [gymHealth, gymMetaTemplates.length]);

    const handleSendTest = async () => {
        if (!testGymId || !testNumber.trim()) return;
        setSending(true);
        try {
            const res = await api.sendWhatsAppTest(testGymId, testNumber, testMessage);
            if (res.ok && res.data) {
                if (res.data.ok) {
                    setUiMsg({ type: 'ok', text: res.data.message || 'Mensaje enviado correctamente' });
                } else {
                    setUiMsg({ type: 'error', text: res.data.error || 'Error desconocido' });
                }
            } else {
                setUiMsg({ type: 'error', text: res.error || 'Error de conexión' });
            }
        } catch (e) {
            setUiMsg({ type: 'error', text: String(e) });
        } finally {
            setSending(false);
        }
    };

    const parseExamples = (raw: string) => {
        const parts = raw.split(',').map((x) => x.trim()).filter(Boolean);
        return parts;
    };

    const handleSaveTemplate = async () => {
        const name = String(editing.template_name || '').trim();
        if (!name) return;
        if (!String(editing.body_text || '').trim()) return;
        setSavingTemplate(true);
        try {
            const res = await api.upsertWhatsAppTemplateCatalog(name, {
                category: editing.category || 'UTILITY',
                language: editing.language || 'es_AR',
                body_text: editing.body_text || '',
                active: Boolean(editing.active),
                version: Number(editing.version || 1),
                example_params: editing.example_params || [],
            });
            if (!res.ok) {
                setUiMsg({ type: 'error', text: res.error || 'Error guardando plantilla' });
                return;
            }
            setUiMsg({ type: 'ok', text: `Plantilla guardada: ${name}` });
            setEditing({
                template_name: '',
                category: 'UTILITY',
                language: 'es_AR',
                body_text: '',
                active: true,
                version: 1,
                example_params: [],
            });
            await loadTemplates();
        } finally {
            setSavingTemplate(false);
        }
    };

    const handleDeleteTemplate = async (name: string) => {
        if (!confirm(`¿Eliminar la plantilla "${name}"?`)) return;
        const res = await api.deleteWhatsAppTemplateCatalog(name);
        if (!res.ok) {
            setUiMsg({ type: 'error', text: res.error || 'Error eliminando plantilla' });
            return;
        }
        setUiMsg({ type: 'ok', text: `Plantilla eliminada: ${name}` });
        await loadTemplates();
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="page-title">WhatsApp</h1>
                <p className="text-slate-400 mt-1">Estado de configuración de WhatsApp por gimnasio</p>
            </div>

            <div className="card p-4">
                <div className="text-white font-semibold">Guía rápida</div>
                <div className="text-sm text-slate-400 mt-1">
                    Este panel es para administración: catálogo/bindings globales y monitoreo por gimnasio. El dueño opera desde /gestion/whatsapp.
                </div>
                <div className="text-xs text-slate-500 mt-2">
                    Flujo recomendado: sincronizar defaults → provisionar templates por gimnasio → esperar APPROVED → provisionar nuevamente para auto-setear versiones por acción.
                </div>
            </div>

            {uiMsg ? (
                <div
                    className={[
                        'rounded-lg border p-3 text-sm',
                        uiMsg.type === 'ok' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : '',
                        uiMsg.type === 'error' ? 'border-red-500/30 bg-red-500/10 text-red-200' : '',
                        uiMsg.type === 'info' ? 'border-slate-700 bg-slate-900/40 text-slate-200' : '',
                    ].join(' ')}
                >
                    <div className="flex items-center justify-between gap-3">
                        <div>{uiMsg.text}</div>
                        <button className="text-slate-300 hover:text-white" onClick={() => setUiMsg(null)}>
                            Cerrar
                        </button>
                    </div>
                </div>
            ) : null}

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="card p-4">
                    <div className="text-sm text-slate-500">Total gimnasios</div>
                    <div className="text-2xl font-bold text-white">{gyms.length}</div>
                </div>
                <div className="card p-4">
                    <div className="text-sm text-slate-500">Configurados</div>
                    <div className="text-2xl font-bold text-success-400">{configuredGyms.length}</div>
                </div>
                <div className="card p-4">
                    <div className="text-sm text-slate-500">Sin configurar</div>
                    <div className="text-2xl font-bold text-warning-400">{notConfiguredGyms.length}</div>
                </div>
            </div>

            <div className="card p-4">
                <div className="flex items-center justify-between gap-3 mb-3">
                    <div>
                        <h3 className="font-semibold text-white">Operación por gimnasio (dinámico)</h3>
                        <p className="text-slate-400 text-sm mt-1">
                            Cruza catálogo (admin) + templates reales en Meta (WABA) + acciones efectivas del tenant. Sin listas estáticas.
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => (selectedGymId ? loadSelectedGymData(selectedGymId) : null)}
                            className="btn-secondary flex items-center gap-2"
                            disabled={!selectedGymId || gymLoading}
                        >
                            {gymLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                            Refrescar
                        </button>
                        <button
                            onClick={handleProvisionTemplatesSelectedGym}
                            className="btn-primary flex items-center gap-2"
                            disabled={!selectedGymId || provisioning}
                        >
                            {provisioning ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowUpRight className="w-4 h-4" />}
                            Provisionar
                        </button>
                        {selectedGymId ? (
                            <Link href={`/dashboard/gyms/${selectedGymId}`} className="btn-secondary">
                                Abrir gym
                            </Link>
                        ) : null}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label className="label">Gimnasio</label>
                        <select
                            value={selectedGymId || ''}
                            onChange={(e) => {
                                const v = Number(e.target.value) || null;
                                setSelectedGymId(v);
                                setTestGymId(v);
                            }}
                            className="input w-full"
                        >
                            <option value="">Seleccionar...</option>
                            {configuredGymsFiltered.map((g) => (
                                <option key={g.id} value={g.id}>
                                    {g.nombre}
                                </option>
                            ))}
                        </select>
                        <div className="text-xs text-slate-500 mt-1">
                            Si no aparece, el gym todavía no tiene Phone ID sincronizado al admin.
                        </div>
                    </div>
                    <div>
                        <label className="label">Estado (Meta)</label>
                        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-sm text-slate-300">
                            {!selectedGymId ? (
                                <span className="text-slate-500">Seleccioná un gimnasio para ver salud y templates reales.</span>
                            ) : gymLoading ? (
                                <span className="flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                                </span>
                            ) : gymHealth ? (
                                <div className="flex flex-wrap items-center gap-3">
                                    <span className={gymHealthInfo.ok ? 'text-emerald-300' : 'text-red-300'}>
                                        {gymHealthInfo.ok ? 'OK' : 'ERROR'}
                                    </span>
                                    <span className="text-slate-400">
                                        templates={gymHealthInfo.templatesCount}
                                    </span>
                                    <span className="text-slate-400">
                                        approved={gymHealthInfo.approved}
                                    </span>
                                    {gymHealthInfo.error ? (
                                        <span className="text-red-200">{gymHealthInfo.error}</span>
                                    ) : null}
                                </div>
                            ) : (
                                <span className="text-slate-500">Sin datos</span>
                            )}
                        </div>
                    </div>
                </div>

                {selectedGymId ? (
                    <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <div className="font-medium text-white">Acciones (envíos por template)</div>
                                <div className="text-slate-400 text-sm mt-1">
                                    Selector dinámico por acción: catálogo compatible por params + templates reales en Meta.
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button className="btn-secondary" onClick={autoPickGymActionTemplates} disabled={!gymActions.length || gymLoading}>
                                    Auto (mejor APPROVED)
                                </button>
                                <button className="btn-primary" onClick={saveAllGymActions} disabled={!gymActions.length || savingAllGymActions}>
                                    {savingAllGymActions ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar todo'}
                                </button>
                            </div>
                        </div>

                        {gymActions.length ? (
                            <div className="mt-4 space-y-2">
                                {gymActions.map((a) => {
                                    const opts = buildActionTemplateOptions(a);
                                    const currentOpt = opts.find((o) => o.name === String(a.template_name || '').trim());
                                    return (
                                        <div key={a.action_key} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                            <div className="flex flex-col lg:flex-row lg:items-center gap-3">
                                                <div className="flex-1 min-w-[220px]">
                                                    <div className="text-white font-medium">
                                                        {actionLabelByKey[a.action_key] || a.action_key}
                                                    </div>
                                                    <div className="text-xs text-slate-500 mt-0.5">
                                                        key={a.action_key} · params={a.required_params}
                                                    </div>
                                                </div>
                                                <label className="flex items-center gap-2 text-sm text-slate-300">
                                                    <input
                                                        type="checkbox"
                                                        checked={Boolean(a.enabled)}
                                                        onChange={(e) =>
                                                            setGymActions((prev) =>
                                                                prev.map((x) =>
                                                                    x.action_key === a.action_key ? { ...x, enabled: e.target.checked } : x
                                                                )
                                                            )
                                                        }
                                                    />
                                                    Habilitado
                                                </label>
                                                <div className="flex-1 min-w-[320px]">
                                                    <select
                                                        className="input w-full"
                                                        value={String(a.template_name || '')}
                                                        onChange={(e) =>
                                                            setGymActions((prev) =>
                                                                prev.map((x) =>
                                                                    x.action_key === a.action_key ? { ...x, template_name: e.target.value } : x
                                                                )
                                                            )
                                                        }
                                                    >
                                                        {opts.map((o) => (
                                                            <option key={o.name} value={o.name} disabled={o.disabled}>
                                                                {o.label}
                                                            </option>
                                                        ))}
                                                    </select>
                                                    {currentOpt?.disabled ? (
                                                        <div className="text-xs text-red-200 mt-1">
                                                            Este valor no es guardable (no está en catálogo activo y/o no está APPROVED en Meta).
                                                        </div>
                                                    ) : null}
                                                </div>
                                                <button
                                                    className="btn-secondary"
                                                    onClick={() => saveGymAction(a.action_key)}
                                                    disabled={savingGymAction === a.action_key || gymLoading}
                                                >
                                                    {savingGymAction === a.action_key ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="mt-3 text-sm text-slate-400">No hay acciones cargadas.</div>
                        )}
                    </div>
                ) : null}

                {selectedGymId ? (
                    <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <div className="font-medium text-white">Eventos / Diagnóstico</div>
                                <div className="text-slate-400 text-sm mt-1">Últimos eventos registrados durante onboarding y operaciones</div>
                            </div>
                            <div className="text-xs text-slate-500">{gymEvents.length} eventos</div>
                        </div>
                        {gymEvents.length ? (
                            <div className="mt-3 space-y-2">
                                {gymEvents.slice(0, 15).map((ev, idx) => (
                                    <div key={`${idx}-${String(ev.event_type || '')}`} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="text-sm text-white">{String(ev.event_type || 'event')}</div>
                                            <div className="text-xs text-slate-500">{String(ev.created_at || '')}</div>
                                        </div>
                                        <div className="text-xs mt-1">
                                            <span className="text-slate-400">{String(ev.severity || '')}</span>
                                            {ev.message ? <span className="text-slate-300"> · {String(ev.message)}</span> : null}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="mt-3 text-sm text-slate-400">Sin eventos.</div>
                        )}
                    </div>
                ) : null}
            </div>

            {/* Test Section */}
            <div className="card p-4">
                <h3 className="font-semibold text-white mb-3">Prueba de WhatsApp</h3>
                <div className="flex flex-wrap items-end gap-3">
                    <div>
                        <label className="label">Gimnasio</label>
                        <select
                            value={testGymId || ''}
                            onChange={(e) => {
                                const v = Number(e.target.value) || null;
                                setTestGymId(v);
                                setSelectedGymId(v);
                            }}
                            className="input w-48"
                        >
                            <option value="">Seleccionar...</option>
                            {configuredGymsFiltered.map((g) => (
                                <option key={g.id} value={g.id}>
                                    {g.nombre}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="label">Número destino</label>
                        <input
                            type="text"
                            value={testNumber}
                            onChange={(e) => setTestNumber(e.target.value)}
                            className="input w-48"
                            placeholder="+5493411234567"
                        />
                    </div>
                    <div>
                        <label className="label">Mensaje</label>
                        <input
                            type="text"
                            value={testMessage}
                            onChange={(e) => setTestMessage(e.target.value)}
                            className="input w-64"
                        />
                    </div>
                    <button
                        onClick={handleSendTest}
                        disabled={sending || !testGymId || !testNumber.trim()}
                        className="btn-primary flex items-center gap-2"
                    >
                        {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        Enviar test
                    </button>
                </div>
            </div>

            {/* Gyms List */}
            <div className="card overflow-hidden">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between gap-3">
                    <div className="text-white font-semibold">Gimnasios</div>
                    <input
                        className="input w-64"
                        placeholder="Buscar por nombre o subdominio..."
                        value={gymSearch}
                        onChange={(e) => setGymSearch(e.target.value)}
                    />
                </div>
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Gimnasio</th>
                                <th>Subdominio</th>
                                <th>WhatsApp</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredGyms.map((gym) => (
                                <tr key={gym.id}>
                                    <td className="font-medium text-white">{gym.nombre}</td>
                                    <td className="text-slate-400">{gym.subdominio}</td>
                                    <td>
                                        {gym.wa_configured ? (
                                            <span className="flex items-center gap-1 text-success-400">
                                                <Check className="w-4 h-4" />
                                                Configurado
                                            </span>
                                        ) : (
                                            <span className="flex items-center gap-1 text-slate-500">
                                                <X className="w-4 h-4" />
                                                Sin configurar
                                            </span>
                                        )}
                                    </td>
                                    <td>
                                        <Link href={`/dashboard/gyms/${gym.id}`} className="flex items-center gap-1 text-primary-400 hover:text-primary-300 text-sm">
                                            Configurar
                                            <ExternalLink className="w-3 h-3" />
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            <div className="card p-4">
                <div className="flex items-center justify-between gap-3">
                    <div>
                        <h3 className="font-semibold text-white">Catálogo estándar de plantillas (Meta)</h3>
                        <p className="text-slate-400 text-sm mt-1">Fuente central para provisionar templates en la WABA de cada gimnasio</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button onClick={handleSyncDefaults} className="btn-secondary flex items-center gap-2" disabled={syncingDefaults}>
                            {syncingDefaults ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            Sincronizar defaults
                        </button>
                        <button onClick={loadTemplates} className="btn-secondary flex items-center gap-2" disabled={templatesLoading}>
                            <RefreshCw className="w-4 h-4" />
                            Refrescar
                        </button>
                    </div>
                </div>

                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <div className="font-medium text-white">Bindings (acciones → template)</div>
                            <div className="text-slate-400 text-sm mt-1">Define qué versión se usa al enviar cada tipo de mensaje</div>
                        </div>
                        <button
                            onClick={async () => {
                                const res = await api.syncWhatsAppTemplateBindings(true);
                                if (!res.ok) {
                                    setUiMsg({ type: 'error', text: res.error || 'Error sincronizando bindings' });
                                    return;
                                }
                                setUiMsg({ type: 'ok', text: 'Bindings reseteados a defaults' });
                                await loadBindings();
                            }}
                            className="btn-secondary flex items-center gap-2"
                            disabled={bindingsLoading}
                        >
                            <RefreshCw className="w-4 h-4" />
                            Reset defaults
                        </button>
                    </div>
                    {bindingsLoading || templatesLoading || actionSpecsLoading ? (
                        <div className="mt-3 flex items-center gap-2 text-slate-400">
                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                        </div>
                    ) : (
                        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                            {(actionSpecs.length ? actionSpecs : Object.entries(bindings).map(([k]) => ({ action_key: k, label: k, required_params: 0 }))).map(
                                (s) => {
                                    const k = String(s?.action_key || '').trim();
                                    const v = String(bindings?.[k] || '').trim();
                                    const opts = buildBindingTemplateOptions(s);
                                    return (
                                        <div key={k} className="flex items-center gap-2">
                                            <div className="w-52 text-sm text-slate-300">
                                                <div className="text-white">{String(s?.label || k)}</div>
                                                <div className="text-xs text-slate-500">key={k} · params={Number(s?.required_params || 0)}</div>
                                            </div>
                                            <select
                                                className="input flex-1"
                                                value={v || ''}
                                                onChange={(e) => setBindings((p) => ({ ...p, [k]: e.target.value }))}
                                            >
                                                {opts.map((o) => (
                                                    <option key={o.name} value={o.name} disabled={o.disabled}>
                                                        {o.label}
                                                    </option>
                                                ))}
                                            </select>
                                            <button
                                                className="btn-primary"
                                                disabled={savingBindingKey === k || !String(bindings?.[k] || '').trim()}
                                                onClick={() => handleSaveBinding(k, String(bindings?.[k] || ''))}
                                            >
                                                {savingBindingKey === k ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                                            </button>
                                        </div>
                                    );
                                }
                            )}
                        </div>
                    )}
                </div>

                <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="space-y-3">
                        <div>
                            <label className="label">Template name</label>
                            <input
                                className="input w-full"
                                value={editing.template_name || ''}
                                onChange={(e) => setEditing((p) => ({ ...p, template_name: e.target.value }))}
                                placeholder="ih_payment_confirmed_v1"
                            />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                                <label className="label">Category</label>
                                <select
                                    className="input w-full"
                                    value={String(editing.category || 'UTILITY')}
                                    onChange={(e) => setEditing((p) => ({ ...p, category: e.target.value }))}
                                >
                                    <option value="UTILITY">UTILITY</option>
                                    <option value="AUTHENTICATION">AUTHENTICATION</option>
                                    <option value="MARKETING">MARKETING</option>
                                </select>
                            </div>
                            <div>
                                <label className="label">Language</label>
                                <input
                                    className="input w-full"
                                    value={editing.language || 'es_AR'}
                                    onChange={(e) => setEditing((p) => ({ ...p, language: e.target.value }))}
                                    placeholder="es_AR"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="label">Body</label>
                            <textarea
                                className="input w-full min-h-[140px]"
                                value={editing.body_text || ''}
                                onChange={(e) => setEditing((p) => ({ ...p, body_text: e.target.value }))}
                                placeholder="Hola {{1}} ..."
                            />
                        </div>
                        <div>
                            <label className="label">Ejemplos (CSV)</label>
                            <input
                                className="input w-full"
                                value={Array.isArray(editing.example_params) ? editing.example_params.join(', ') : ''}
                                onChange={(e) => setEditing((p) => ({ ...p, example_params: parseExamples(e.target.value) }))}
                                placeholder="Mateo, 25000, 01/2026"
                            />
                        </div>
                        <div className="flex items-center justify-between gap-3">
                            <label className="flex items-center gap-2 text-sm text-slate-300">
                                <input
                                    type="checkbox"
                                    checked={Boolean(editing.active)}
                                    onChange={(e) => setEditing((p) => ({ ...p, active: e.target.checked }))}
                                />
                                Activa
                            </label>
                            <button
                                onClick={handleSaveTemplate}
                                className="btn-primary flex items-center gap-2"
                                disabled={savingTemplate || !String(editing.template_name || '').trim() || !String(editing.body_text || '').trim()}
                            >
                                {savingTemplate ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                Guardar
                            </button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        {templatesLoading ? (
                            <div className="flex items-center gap-2 text-slate-400">
                                <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                            </div>
                        ) : templates.length === 0 ? (
                            <div className="text-slate-400 text-sm">No hay plantillas en el catálogo.</div>
                        ) : (
                            templates.map((t) => (
                                <div key={t.template_name} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <div className="font-medium text-white">{t.template_name}</div>
                                            <div className="text-xs text-slate-500 mt-1">
                                                {t.category} · {t.language} · v{t.version} · {t.active ? 'activa' : 'inactiva'}
                                            </div>
                                            <div className="text-sm text-slate-300 mt-2 truncate">{t.body_text}</div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                className="btn-secondary text-sm flex items-center gap-1"
                                                onClick={() => handleBumpVersion(t.template_name)}
                                            >
                                                <ArrowUpRight className="w-3 h-3" />
                                                Bump
                                            </button>
                                            <button
                                                className="btn-secondary text-sm"
                                                onClick={() => setEditing({ ...t, example_params: Array.isArray(t.example_params) ? t.example_params : [] })}
                                            >
                                                Editar
                                            </button>
                                            <button className="btn-danger flex items-center gap-1" onClick={() => handleDeleteTemplate(t.template_name)}>
                                                <Trash2 className="w-4 h-4" />
                                                Borrar
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
