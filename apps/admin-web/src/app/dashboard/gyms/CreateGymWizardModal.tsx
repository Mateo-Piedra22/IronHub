'use client';

import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, Check, Copy, Loader2, Plus, Trash2, Wand2, X } from 'lucide-react';
import { api, type GymBranchCreateInput, type GymCreateV2Input } from '@/lib/api';

type Step = 1 | 2 | 3 | 4;

export function CreateGymWizardModal({
    open,
    onClose,
    tenantDomain,
    onCreated,
}: {
    open: boolean;
    onClose: () => void;
    tenantDomain: string;
    onCreated: (gymId: number) => void;
}) {
    const [step, setStep] = useState<Step>(1);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    const [nombre, setNombre] = useState('');
    const [subdominio, setSubdominio] = useState('');
    const [ownerPhone, setOwnerPhone] = useState('');

    const [useCustomPassword, setUseCustomPassword] = useState(false);
    const [ownerPassword, setOwnerPassword] = useState('');

    const [branches, setBranches] = useState<GymBranchCreateInput[]>([
        { name: 'Principal', code: 'principal', address: '', timezone: 'America/Argentina/Buenos_Aires' },
    ]);

    const [waAdvanced, setWaAdvanced] = useState(false);
    const [waConfig, setWaConfig] = useState({
        whatsapp_phone_id: '',
        whatsapp_access_token: '',
        whatsapp_business_account_id: '',
        whatsapp_verify_token: '',
        whatsapp_app_secret: '',
        whatsapp_nonblocking: false,
        whatsapp_send_timeout_seconds: 25,
    });

    const [success, setSuccess] = useState<{
        gymId: number;
        tenantUrl?: string | null;
        ownerPassword?: string;
    } | null>(null);

    const normalizedSubdomain = useMemo(() => {
        const raw = String(subdominio || '').trim().toLowerCase();
        return raw.replace(/[^a-z0-9-]/g, '').slice(0, 40);
    }, [subdominio]);

    const canNext = useMemo(() => {
        if (step === 1) return nombre.trim().length >= 2;
        if (step === 2) {
            const filtered = branches.filter((b) => String(b.name || '').trim() && String(b.code || '').trim());
            return filtered.length > 0;
        }
        if (step === 3) {
            if (!useCustomPassword) return true;
            return ownerPassword.trim().length >= 8;
        }
        return true;
    }, [step, nombre, branches, useCustomPassword, ownerPassword]);

    const resetAll = () => {
        setStep(1);
        setSubmitting(false);
        setError('');
        setNombre('');
        setSubdominio('');
        setOwnerPhone('');
        setUseCustomPassword(false);
        setOwnerPassword('');
        setBranches([{ name: 'Principal', code: 'principal', address: '', timezone: 'America/Argentina/Buenos_Aires' }]);
        setWaAdvanced(false);
        setWaConfig({
            whatsapp_phone_id: '',
            whatsapp_access_token: '',
            whatsapp_business_account_id: '',
            whatsapp_verify_token: '',
            whatsapp_app_secret: '',
            whatsapp_nonblocking: false,
            whatsapp_send_timeout_seconds: 25,
        });
        setSuccess(null);
    };

    const close = () => {
        onClose();
        setTimeout(() => resetAll(), 150);
    };

    const suggestSubdomain = async () => {
        setError('');
        try {
            const res = await api.suggestSubdomain(nombre);
            if (res.ok && res.data?.suggested) setSubdominio(res.data.suggested);
        } catch {
        }
    };

    const checkSubdomain = async () => {
        setError('');
        const sub = normalizedSubdomain;
        if (!sub) return;
        try {
            const res = await api.checkSubdomain(sub);
            if (res.ok && res.data) {
                if (!res.data.available) setError('El subdominio no está disponible');
            }
        } catch {
        }
    };

    const addBranch = () => {
        setBranches((prev) => [...prev, { name: '', code: '', address: '', timezone: 'America/Argentina/Buenos_Aires' }]);
    };

    const removeBranch = (idx: number) => {
        setBranches((prev) => prev.filter((_, i) => i !== idx));
    };

    const updateBranch = (idx: number, patch: Partial<GymBranchCreateInput>) => {
        setBranches((prev) =>
            prev.map((b, i) => (i === idx ? { ...b, ...patch } : b))
        );
    };

    const copy = async (value: string) => {
        try {
            await navigator.clipboard.writeText(value);
        } catch {
        }
    };

    const submit = async () => {
        setSubmitting(true);
        setError('');
        try {
            const cleanedBranches = branches
                .map((b) => ({
                    name: String(b.name || '').trim(),
                    code: String(b.code || '').trim().toLowerCase().replace(/[^a-z0-9_-]/g, '').slice(0, 40),
                    address: String(b.address || '').trim() ? String(b.address || '').trim() : null,
                    timezone: String(b.timezone || '').trim() ? String(b.timezone || '').trim() : null,
                }))
                .filter((b) => b.name && b.code);

            const payload: GymCreateV2Input = {
                nombre: nombre.trim(),
                subdominio: normalizedSubdomain || undefined,
                owner_phone: ownerPhone.trim() || undefined,
                owner_password: useCustomPassword ? ownerPassword.trim() : undefined,
                whatsapp_phone_id: waAdvanced ? waConfig.whatsapp_phone_id.trim() || undefined : undefined,
                whatsapp_access_token: waAdvanced ? waConfig.whatsapp_access_token.trim() || undefined : undefined,
                whatsapp_business_account_id: waAdvanced ? waConfig.whatsapp_business_account_id.trim() || undefined : undefined,
                whatsapp_verify_token: waAdvanced ? waConfig.whatsapp_verify_token.trim() || undefined : undefined,
                whatsapp_app_secret: waAdvanced ? waConfig.whatsapp_app_secret.trim() || undefined : undefined,
                whatsapp_nonblocking: waAdvanced ? Boolean(waConfig.whatsapp_nonblocking) : undefined,
                whatsapp_send_timeout_seconds: waAdvanced ? Number(waConfig.whatsapp_send_timeout_seconds || 25) : undefined,
                branches: cleanedBranches.length ? cleanedBranches : undefined,
            };

            const res = await api.createGymV2(payload);
            if (!res.ok || !res.data?.ok) {
                setError(res.data?.error || res.error || 'Error al crear');
                return;
            }
            const gymId = Number((res.data.gym as any)?.id || 0);
            if (!gymId) {
                setError('Creado pero sin ID válido');
                return;
            }
            setSuccess({
                gymId,
                tenantUrl: res.data.tenant_url,
                ownerPassword: res.data.owner_password || undefined,
            });
            onCreated(gymId);
            setStep(4);
        } catch {
            setError('Error de conexión');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 overflow-y-auto"
                    onClick={close}
                >
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.95, opacity: 0 }}
                        onClick={(e) => e.stopPropagation()}
                        className="card w-full max-w-2xl p-6 my-8"
                    >
                        <div className="flex items-start justify-between gap-4 mb-4">
                            <div>
                                <h2 className="text-xl font-bold text-white">Nuevo Gimnasio</h2>
                                <div className="text-xs text-slate-400 mt-1">
                                    Paso {step} de 4
                                </div>
                            </div>
                            <button onClick={close} className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white" aria-label="Cerrar">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {step === 1 && (
                            <div className="space-y-4">
                                <div>
                                    <label className="label">Nombre *</label>
                                    <input className="input" value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Iron Fitness" />
                                </div>
                                <div>
                                    <label className="label">Subdominio</label>
                                    <div className="flex items-center gap-2">
                                        <input
                                            className="input"
                                            value={subdominio}
                                            onChange={(e) => setSubdominio(e.target.value)}
                                            onBlur={checkSubdomain}
                                            placeholder="ironfitness"
                                        />
                                        <span className="text-slate-500 whitespace-nowrap">.{tenantDomain}</span>
                                        <button type="button" onClick={suggestSubdomain} className="btn-secondary flex items-center gap-2">
                                            <Wand2 className="w-4 h-4" />
                                            Sugerir
                                        </button>
                                    </div>
                                    <div className="text-xs text-slate-500 mt-1">
                                        URL final: https://{normalizedSubdomain || 'subdominio'}.{tenantDomain}
                                    </div>
                                </div>
                                <div>
                                    <label className="label">Teléfono Owner (opcional)</label>
                                    <input className="input" value={ownerPhone} onChange={(e) => setOwnerPhone(e.target.value)} placeholder="+5493411234567" />
                                </div>
                            </div>
                        )}

                        {step === 2 && (
                            <div className="space-y-4">
                                <div className="text-sm text-slate-300">
                                    Creá al menos una sucursal activa. Recomendado: una “Principal”.
                                </div>
                                <div className="space-y-3">
                                    {branches.map((b, idx) => (
                                        <div key={idx} className="border border-slate-800 rounded-xl p-3">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                <div>
                                                    <label className="text-xs text-slate-400 block mb-1">Nombre</label>
                                                    <input className="input w-full" value={String(b.name || '')} onChange={(e) => updateBranch(idx, { name: e.target.value })} />
                                                </div>
                                                <div>
                                                    <label className="text-xs text-slate-400 block mb-1">Código</label>
                                                    <input className="input w-full" value={String(b.code || '')} onChange={(e) => updateBranch(idx, { code: e.target.value })} />
                                                    <div className="text-[11px] text-slate-500 mt-1">Minúsculas, sin espacios. Ej: principal, centro, sede-norte</div>
                                                </div>
                                                <div>
                                                    <label className="text-xs text-slate-400 block mb-1">Timezone</label>
                                                    <input className="input w-full" value={String(b.timezone || '')} onChange={(e) => updateBranch(idx, { timezone: e.target.value })} placeholder="America/Argentina/Buenos_Aires" />
                                                </div>
                                                <div>
                                                    <label className="text-xs text-slate-400 block mb-1">Dirección</label>
                                                    <input className="input w-full" value={String(b.address || '')} onChange={(e) => updateBranch(idx, { address: e.target.value })} />
                                                </div>
                                            </div>
                                            <div className="mt-3 flex justify-end">
                                                <button
                                                    type="button"
                                                    onClick={() => removeBranch(idx)}
                                                    disabled={branches.length <= 1}
                                                    className="btn-secondary flex items-center gap-2 disabled:opacity-50"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                    Quitar
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <button type="button" onClick={addBranch} className="btn-secondary flex items-center gap-2">
                                    <Plus className="w-4 h-4" />
                                    Agregar sucursal
                                </button>
                            </div>
                        )}

                        {step === 3 && (
                            <div className="space-y-4">
                                <div className="text-sm text-slate-300">
                                    Se genera una contraseña segura para el Owner. Podés definir una manualmente.
                                </div>
                                <label className="flex items-center gap-2 text-sm text-slate-300">
                                    <input type="checkbox" checked={useCustomPassword} onChange={(e) => setUseCustomPassword(e.target.checked)} />
                                    Definir contraseña manual
                                </label>
                                {useCustomPassword && (
                                    <div>
                                        <label className="label">Contraseña Owner</label>
                                        <input className="input" type="text" value={ownerPassword} onChange={(e) => setOwnerPassword(e.target.value)} placeholder="mínimo 8 caracteres" />
                                    </div>
                                )}
                                <div className="border border-slate-800 rounded-xl p-3">
                                    <label className="flex items-center gap-2 text-sm text-slate-300">
                                        <input type="checkbox" checked={waAdvanced} onChange={(e) => setWaAdvanced(e.target.checked)} />
                                        Configurar WhatsApp ahora (avanzado)
                                    </label>
                                    {waAdvanced && (
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Phone ID</label>
                                                <input className="input w-full" value={waConfig.whatsapp_phone_id} onChange={(e) => setWaConfig({ ...waConfig, whatsapp_phone_id: e.target.value })} />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">WABA ID</label>
                                                <input className="input w-full" value={waConfig.whatsapp_business_account_id} onChange={(e) => setWaConfig({ ...waConfig, whatsapp_business_account_id: e.target.value })} />
                                            </div>
                                            <div className="md:col-span-2">
                                                <label className="text-xs text-slate-400 block mb-1">Access Token</label>
                                                <input className="input w-full" value={waConfig.whatsapp_access_token} onChange={(e) => setWaConfig({ ...waConfig, whatsapp_access_token: e.target.value })} />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Verify Token</label>
                                                <input className="input w-full" value={waConfig.whatsapp_verify_token} onChange={(e) => setWaConfig({ ...waConfig, whatsapp_verify_token: e.target.value })} />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">App Secret</label>
                                                <input className="input w-full" value={waConfig.whatsapp_app_secret} onChange={(e) => setWaConfig({ ...waConfig, whatsapp_app_secret: e.target.value })} />
                                            </div>
                                            <div className="md:col-span-2 flex items-center justify-between">
                                                <label className="flex items-center gap-2 text-sm text-slate-300">
                                                    <input type="checkbox" checked={waConfig.whatsapp_nonblocking} onChange={(e) => setWaConfig({ ...waConfig, whatsapp_nonblocking: e.target.checked })} />
                                                    Envío no bloqueante
                                                </label>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs text-slate-500">Timeout</span>
                                                    <input
                                                        className="input w-24"
                                                        type="number"
                                                        min={1}
                                                        max={120}
                                                        value={waConfig.whatsapp_send_timeout_seconds}
                                                        onChange={(e) => setWaConfig({ ...waConfig, whatsapp_send_timeout_seconds: Number(e.target.value) })}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {step === 4 && success && (
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 text-success-400">
                                    <Check className="w-5 h-5" />
                                    Gimnasio creado
                                </div>
                                <div className="border border-slate-800 rounded-xl p-3">
                                    <div className="text-xs text-slate-500">Tenant URL</div>
                                    <div className="flex items-center justify-between gap-3">
                                        <a className="text-primary-400 hover:text-primary-300" href={success.tenantUrl || '#'} target="_blank" rel="noreferrer">
                                            {success.tenantUrl || `https://${normalizedSubdomain}.${tenantDomain}`}
                                        </a>
                                        <button type="button" className="btn-secondary flex items-center gap-2" onClick={() => copy(success.tenantUrl || `https://${normalizedSubdomain}.${tenantDomain}`)}>
                                            <Copy className="w-4 h-4" />
                                            Copiar
                                        </button>
                                    </div>
                                </div>
                                {success.ownerPassword ? (
                                    <div className="border border-slate-800 rounded-xl p-3">
                                        <div className="text-xs text-slate-500">Contraseña Owner (se muestra una sola vez)</div>
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="text-white font-mono text-sm break-all">{success.ownerPassword}</div>
                                            <button type="button" className="btn-secondary flex items-center gap-2" onClick={() => copy(success.ownerPassword || '')}>
                                                <Copy className="w-4 h-4" />
                                                Copiar
                                            </button>
                                        </div>
                                    </div>
                                ) : null}
                                <div className="text-sm text-slate-300">
                                    Siguiente paso recomendado: entrar al detalle del gym y terminar configuración (WhatsApp, entitlements, módulos, etc.).
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="flex items-center gap-2 text-danger-400 text-sm mt-4">
                                <AlertCircle className="w-4 h-4" />
                                {error}
                            </div>
                        )}

                        <div className="flex items-center justify-between gap-3 pt-6">
                            <div className="flex items-center gap-2">
                                {step > 1 && step < 4 && (
                                    <button type="button" onClick={() => setStep((s) => (s - 1) as Step)} className="btn-secondary">
                                        Atrás
                                    </button>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                {step < 3 && (
                                    <button type="button" onClick={() => setStep((s) => (s + 1) as Step)} disabled={!canNext} className="btn-primary disabled:opacity-50">
                                        Siguiente
                                    </button>
                                )}
                                {step === 3 && (
                                    <button type="button" onClick={submit} disabled={!canNext || submitting} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                                        {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Crear'}
                                    </button>
                                )}
                                {step === 4 && (
                                    <button type="button" onClick={close} className="btn-primary">
                                        Cerrar
                                    </button>
                                )}
                            </div>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
