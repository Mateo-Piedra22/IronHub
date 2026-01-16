'use client';

import { useState, useEffect } from 'react';
import { Loader2, MessageSquare, Send, Check, X, ExternalLink, Save, Trash2, RefreshCw } from 'lucide-react';
import { api, type Gym, type WhatsAppTemplateCatalogItem } from '@/lib/api';

export default function WhatsAppPage() {
    const [gyms, setGyms] = useState<Gym[]>([]);
    const [loading, setLoading] = useState(true);
    const [testNumber, setTestNumber] = useState('');
    const [testMessage, setTestMessage] = useState('Mensaje de prueba');
    const [testGymId, setTestGymId] = useState<number | null>(null);
    const [sending, setSending] = useState(false);

    const [templates, setTemplates] = useState<WhatsAppTemplateCatalogItem[]>([]);
    const [templatesLoading, setTemplatesLoading] = useState(true);
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

    useEffect(() => {
        async function load() {
            setLoading(true);
            try {
                const res = await api.getGyms({ page_size: 100 });
                if (res.ok && res.data) {
                    setGyms(res.data.gyms || []);
                }
            } catch {
                // Ignore
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

    useEffect(() => {
        loadTemplates();
    }, []);

    const configuredGyms = gyms.filter((g) => g.wa_configured);
    const notConfiguredGyms = gyms.filter((g) => !g.wa_configured);

    const handleSendTest = async () => {
        if (!testGymId || !testNumber.trim()) return;
        setSending(true);
        try {
            const res = await api.sendWhatsAppTest(testGymId, testNumber, testMessage);
            if (res.ok && res.data) {
                if (res.data.ok) {
                    alert(`✅ ${res.data.message || 'Mensaje enviado correctamente'}`);
                } else {
                    alert(`❌ Error: ${res.data.error || 'Error desconocido'}`);
                }
            } else {
                alert(`❌ Error: ${res.error || 'Error de conexión'}`);
            }
        } catch (e) {
            alert(`❌ Error: ${String(e)}`);
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
                alert(res.error || 'Error guardando plantilla');
                return;
            }
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
            alert(res.error || 'Error eliminando plantilla');
            return;
        }
        await loadTemplates();
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="page-title">WhatsApp</h1>
                <p className="text-slate-400 mt-1">Estado de configuración de WhatsApp por gimnasio</p>
            </div>

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

            {/* Test Section */}
            <div className="card p-4">
                <h3 className="font-semibold text-white mb-3">Prueba de WhatsApp</h3>
                <div className="flex flex-wrap items-end gap-3">
                    <div>
                        <label className="label">Gimnasio</label>
                        <select
                            value={testGymId || ''}
                            onChange={(e) => setTestGymId(Number(e.target.value) || null)}
                            className="input w-48"
                        >
                            <option value="">Seleccionar...</option>
                            {configuredGyms.map((g) => (
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
                            {gyms.map((gym) => (
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
                                        <a
                                            href={`/dashboard/gyms/${gym.id}`}
                                            className="flex items-center gap-1 text-primary-400 hover:text-primary-300 text-sm"
                                        >
                                            Configurar
                                            <ExternalLink className="w-3 h-3" />
                                        </a>
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
                    <button onClick={loadTemplates} className="btn-secondary flex items-center gap-2" disabled={templatesLoading}>
                        <RefreshCw className="w-4 h-4" />
                        Refrescar
                    </button>
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

