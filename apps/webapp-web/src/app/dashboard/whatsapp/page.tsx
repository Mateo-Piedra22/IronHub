'use client';

import { MessageSquare } from 'lucide-react';
import WhatsAppPage from '@/app/gestion/whatsapp/page';

export default function DashboardWhatsAppPage() {
    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <MessageSquare className="w-5 h-5" />
                </div>
                <div>
                    <h1 className="text-xl font-semibold text-white">WhatsApp</h1>
                    <p className="text-sm text-slate-400">Administración, salud y automatizaciones.</p>
                </div>
            </div>

            <div className="rounded-2xl border border-slate-800/60 bg-slate-900/20">
                <WhatsAppPage />
            </div>
        </div>
    );
}

