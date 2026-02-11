'use client';

import { useState, useEffect } from 'react';
import HomeSelector from '@/components/HomeSelector';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface GymData {
    gym_name?: string;
    logo_url?: string;
    portal?: {
        tagline?: string | null;
        enable_checkin?: boolean;
        enable_member?: boolean;
        enable_staff?: boolean;
        enable_owner?: boolean;
    };
    support?: {
        whatsapp_enabled?: boolean;
        whatsapp?: string | null;
    };
    footer?: {
        text?: string | null;
        show_powered_by?: boolean;
    };
    suspended?: boolean;
    reason?: string;
    until?: string;
    maintenance?: boolean;
    maintenance_message?: string;
}

export default function HomePage() {
    const [gymData, setGymData] = useState<GymData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            try {
                const res = await api.getBootstrap('auto');
                if (res.ok && res.data) {
                    setGymData({
                        gym_name: res.data.gym?.gym_name,
                        logo_url: res.data.gym?.logo_url,
                        portal: res.data.gym?.portal,
                        support: res.data.gym?.support,
                        footer: res.data.gym?.footer,
                    });
                }
            } catch {
                // ignore
            }

            setLoading(false);
        }

        loadData();
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    return (
        <>
            <HomeSelector
                gymName={gymData?.gym_name || 'IronHub'}
                logoUrl={gymData?.logo_url || ''}
                portalTagline={gymData?.portal?.tagline || null}
                footerText={gymData?.footer?.text || null}
                showPoweredBy={gymData?.footer?.show_powered_by}
                supportWhatsAppEnabled={gymData?.support?.whatsapp_enabled}
                supportWhatsApp={gymData?.support?.whatsapp || null}
                portalEnableCheckin={gymData?.portal?.enable_checkin}
                portalEnableMember={gymData?.portal?.enable_member}
                portalEnableStaff={gymData?.portal?.enable_staff}
                portalEnableOwner={gymData?.portal?.enable_owner}
            />
        </>
    );
}

