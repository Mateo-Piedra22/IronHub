'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Send, FileText, Activity, Copy, MessageSquareText } from 'lucide-react';
import { Button, Input, useToast } from '@/components/ui';

type ApiResult<T> = { ok: boolean; data?: T; error?: string };

async function apiRequest<T>(url: string, opts: RequestInit = {}): Promise<ApiResult<T>> {
    try {
        const res = await fetch(url, {
            ...opts,
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...(opts.headers || {}),
            },
        });
        const data = (await res.json().catch(() => null)) as any;
        if (!res.ok) {
            return { ok: false, error: data?.error || data?.detail || data?.mensaje || 'Error' };
        }
        return { ok: true, data };
    } catch {
        return { ok: false, error: 'Error de conexión' };
    }
}

export default function MetaReviewPage() {
    const { success, error } = useToast();
    const [sending, setSending] = useState(false);
    const [creating, setCreating] = useState(false);
    const [checking, setChecking] = useState(false);

    const [to, setTo] = useState('');
    const [message, setMessage] = useState('Mensaje de prueba desde IronHub (Meta review)');
    const [sendTplName, setSendTplName] = useState('ih_meta_review_demo_v1');
    const [sendTplLanguage, setSendTplLanguage] = useState('es_AR');
    const [sendTplParams, setSendTplParams] = useState('Mateo');

    const [tplName, setTplName] = useState('ih_meta_review_demo_v1');
    const [tplBody, setTplBody] = useState('Hola {{1}}. Esto es una demo de IronHub para revisión de Meta.');
    const [tplLanguage, setTplLanguage] = useState('es_AR');
    const [tplCategory, setTplCategory] = useState<'UTILITY' | 'AUTHENTICATION' | 'MARKETING'>('UTILITY');
    const [tplExamples, setTplExamples] = useState('Mateo');

    const [lastOutput, setLastOutput] = useState<any>(null);

    const endpoints = useMemo(
        () => ({
            health: '/api/meta-review/whatsapp/health',
            send: '/api/meta-review/whatsapp/send-text',
            sendTemplate: '/api/meta-review/whatsapp/send-template',
            createTemplate: '/api/meta-review/whatsapp/create-template',
        }),
        []
    );

    const copy = async (value: string) => {
        try {
            await navigator.clipboard.writeText(value);
            success('Copiado');
        } catch {
            error('No se pudo copiar');
        }
    };

    const runHealth = async () => {
        setChecking(true);
        setLastOutput(null);
        const res = await apiRequest<any>(endpoints.health, { method: 'GET' });
        setChecking(false);
        if (!res.ok) {
            error(res.error || 'Error');
            return;
        }
        setLastOutput(res.data);
    };

    const runSend = async () => {
        if (!to.trim() || !message.trim()) {
            error('Completar número y mensaje');
            return;
        }
        setSending(true);
        setLastOutput(null);
        const res = await apiRequest<any>(endpoints.send, {
            method: 'POST',
            body: JSON.stringify({ to: to.trim(), body: message.trim() }),
        });
        setSending(false);
        if (!res.ok) {
            error(res.error || 'Error');
            return;
        }
        setLastOutput(res.data);
        success('Solicitud enviada');
    };

    const runSendTemplate = async () => {
        if (!to.trim() || !sendTplName.trim()) {
            error('Completar número y template');
            return;
        }
        setSending(true);
        setLastOutput(null);
        const params = sendTplParams
            .split(',')
            .map((x) => x.trim())
            .filter(Boolean);
        const res = await apiRequest<any>(endpoints.sendTemplate, {
            method: 'POST',
            body: JSON.stringify({
                to: to.trim(),
                template_name: sendTplName.trim(),
                language: sendTplLanguage.trim(),
                params,
            }),
        });
        setSending(false);
        if (!res.ok) {
            error(res.error || 'Error');
            return;
        }
        setLastOutput(res.data);
        success('Template enviado');
    };

    const runCreateTemplate = async () => {
        if (!tplName.trim() || !tplBody.trim()) {
            error('Completar nombre y cuerpo');
            return;
        }
        setCreating(true);
        setLastOutput(null);
        const examples = tplExamples
            .split(',')
            .map((x) => x.trim())
            .filter(Boolean);
        const res = await apiRequest<any>(endpoints.createTemplate, {
            method: 'POST',
            body: JSON.stringify({
                name: tplName.trim(),
                body_text: tplBody.trim(),
                language: tplLanguage.trim(),
                category: tplCategory,
                examples,
            }),
        });
        setCreating(false);
        if (!res.ok) {
            error(res.error || 'Error');
            return;
        }
        setLastOutput(res.data);
        success('Plantilla enviada a Meta');
    };

    useEffect(() => {
        void runHealth();
    }, []);

    return (
        <div className="space-y-6">
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Meta Review</h1>
                    <p className="text-slate-400 mt-1">
                        Herramientas para grabar los 2 videos de revisión: envío de mensaje y creación de plantilla.
                    </p>
                </div>
                <Button variant="secondary" leftIcon={<Activity className="w-4 h-4" />} onClick={runHealth} isLoading={checking}>
                    Health
                </Button>
            </motion.div>

            <div className="card p-4 space-y-4">
                <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-white">Video 1: whatsapp_business_messaging</div>
                    <Button variant="ghost" leftIcon={<Copy className="w-4 h-4" />} onClick={() => copy('Video 1: Enviar mensaje desde IronHub y mostrar recepción en WhatsApp.')}>
                        Copiar guion
                    </Button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input label="Número destino (E164)" value={to} onChange={(e) => setTo(e.target.value)} placeholder="+5493411234567" />
                    <Input label="Mensaje" value={message} onChange={(e) => setMessage(e.target.value)} />
                </div>
                <div className="flex flex-wrap gap-3">
                    <Button leftIcon={sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} onClick={runSend} disabled={sending}>
                        Enviar texto (real)
                    </Button>
                    <Button
                        variant="secondary"
                        leftIcon={sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquareText className="w-4 h-4" />}
                        onClick={runSendTemplate}
                        disabled={sending}
                    >
                        Enviar plantilla (real)
                    </Button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Input label="Template name" value={sendTplName} onChange={(e) => setSendTplName(e.target.value)} placeholder="ih_meta_review_demo_v1" />
                    <Input label="Language" value={sendTplLanguage} onChange={(e) => setSendTplLanguage(e.target.value)} placeholder="es_AR" />
                    <Input label="Params (CSV)" value={sendTplParams} onChange={(e) => setSendTplParams(e.target.value)} placeholder="Mateo, 25000, 01/2026" />
                </div>
            </div>

            <div className="card p-4 space-y-4">
                <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-white">Video 2: whatsapp_business_management</div>
                    <Button variant="ghost" leftIcon={<Copy className="w-4 h-4" />} onClick={() => copy('Video 2: Crear plantilla desde IronHub y mostrarla listada/estado en Health.')}>
                        Copiar guion
                    </Button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input label="Template name" value={tplName} onChange={(e) => setTplName(e.target.value)} placeholder="ih_meta_review_demo_v1" />
                    <div>
                        <label className="block text-sm text-slate-300 mb-1">Category</label>
                        <select className="input w-full" value={tplCategory} onChange={(e) => setTplCategory(e.target.value as any)}>
                            <option value="UTILITY">UTILITY</option>
                            <option value="AUTHENTICATION">AUTHENTICATION</option>
                            <option value="MARKETING">MARKETING</option>
                        </select>
                    </div>
                    <Input label="Language" value={tplLanguage} onChange={(e) => setTplLanguage(e.target.value)} placeholder="es_AR" />
                    <Input label="Ejemplos (CSV)" value={tplExamples} onChange={(e) => setTplExamples(e.target.value)} placeholder="Mateo, 25000, 01/2026" />
                </div>
                <div>
                    <label className="block text-sm text-slate-300 mb-1">Body</label>
                    <textarea className="input w-full min-h-[120px]" value={tplBody} onChange={(e) => setTplBody(e.target.value)} />
                </div>
                <Button
                    variant="secondary"
                    leftIcon={creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                    onClick={runCreateTemplate}
                    disabled={creating}
                >
                    Crear plantilla (real)
                </Button>
            </div>

            <div className="card p-4">
                <div className="text-sm text-slate-400 mb-2">Salida</div>
                <pre className="text-xs text-slate-200 whitespace-pre-wrap break-words">{lastOutput ? JSON.stringify(lastOutput, null, 2) : '—'}</pre>
            </div>
        </div>
    );
}
