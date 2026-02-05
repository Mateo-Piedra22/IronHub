'use client';

import { useState, useEffect } from 'react';
import HomeSelector from '@/components/HomeSelector';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface GymData {
    gym_name?: string;
    logo_url?: string;
    suspended?: boolean;
    reason?: string;
    until?: string;
    maintenance?: boolean;
    maintenance_message?: string;
}

export default function HomePage() {
    const [gymData, setGymData] = useState<GymData | null>(null);
    const [loading, setLoading] = useState(true);
    const [showMaintenance, setShowMaintenance] = useState(false);
    const [maintenanceMsg, setMaintenanceMsg] = useState('');
    const [showSuspension, setShowSuspension] = useState(false);
    const [suspensionData, setSuspensionData] = useState<{ reason: string; until: string } | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                const res = await api.getBootstrap('auto');
                if (res.ok && res.data) {
                    const flags = res.data.flags || {};
                    const suspended = Boolean(flags.suspended);
                    const reason = typeof flags.reason === 'string' ? flags.reason : '';
                    const until = typeof flags.until === 'string' ? flags.until : '';
                    const maintenance = Boolean(flags.maintenance);
                    const maintenanceMessage = typeof flags.maintenance_message === 'string' ? flags.maintenance_message : '';
                    setGymData({
                        gym_name: res.data.gym?.gym_name,
                        logo_url: res.data.gym?.logo_url,
                        suspended,
                        reason,
                        until,
                        maintenance,
                        maintenance_message: maintenanceMessage,
                    });
                    if (maintenance) {
                        setMaintenanceMsg(maintenanceMessage || 'Mantenimiento en curso');
                        setShowMaintenance(true);
                    }
                    if (suspended) {
                        setSuspensionData({
                            reason: reason || 'Servicio suspendido',
                            until,
                        });
                        setShowSuspension(true);
                    }
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
            />

            {/* Maintenance Modal */}
            {showMaintenance && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
                    <div className="card p-6 max-w-md w-full">
                        <h3 className="text-lg font-bold text-white mb-2">Mantenimiento</h3>
                        <p className="text-slate-400 mb-4">{maintenanceMsg}</p>
                        <button
                            onClick={() => setShowMaintenance(false)}
                            className="btn-secondary w-full"
                        >
                            Cerrar
                        </button>
                    </div>
                </div>
            )}

            {/* Suspension Modal (non-dismissible) */}
            {showSuspension && suspensionData && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
                    <div className="card p-6 max-w-md w-full border border-danger-500/30">
                        <h3 className="text-lg font-bold text-danger-400 mb-2">Servicio suspendido</h3>
                        <p className="text-slate-400">
                            {suspensionData.reason}
                            {suspensionData.until && (
                                <span className="block mt-2 text-sm">
                                    Hasta: {suspensionData.until}
                                </span>
                            )}
                        </p>
                    </div>
                </div>
            )}
        </>
    );
}

