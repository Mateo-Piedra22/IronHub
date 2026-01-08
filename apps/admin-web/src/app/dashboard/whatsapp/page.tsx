'use client';

import { useState, useEffect } from 'react';
import { Loader2, MessageSquare, Send, Check, X, ExternalLink } from 'lucide-react';
import { api, type Gym } from '@/lib/api';

export default function WhatsAppPage() {
    const [gyms, setGyms] = useState<Gym[]>([]);
    const [loading, setLoading] = useState(true);
    const [testNumber, setTestNumber] = useState('');
    const [testMessage, setTestMessage] = useState('Mensaje de prueba');
    const [testGymId, setTestGymId] = useState<number | null>(null);
    const [sending, setSending] = useState(false);

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

    const configuredGyms = gyms.filter((g) => g.wa_configured);
    const notConfiguredGyms = gyms.filter((g) => !g.wa_configured);

    const handleSendTest = async () => {
        if (!testGymId || !testNumber.trim()) return;
        setSending(true);
        try {
            // This would call an API endpoint for WhatsApp test
            await new Promise((r) => setTimeout(r, 1000));
            alert('Mensaje de prueba enviado (simulado)');
        } catch {
            alert('Error al enviar');
        } finally {
            setSending(false);
        }
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
        </div>
    );
}

