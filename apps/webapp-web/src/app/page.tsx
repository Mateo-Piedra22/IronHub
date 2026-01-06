'use client';

import { useState, useEffect } from 'react';
import HomeSelector from '@/components/HomeSelector';
import { Loader2 } from 'lucide-react';

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
                // Fetch gym branding data
                const gymRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/gym/data`, {
                    headers: { Accept: 'application/json' },
                    credentials: 'include',
                });
                if (gymRes.ok) {
                    const data = await gymRes.json();
                    setGymData(data);
                }
            } catch {
                // Fallback to defaults
            }

            try {
                // Check maintenance status
                const maintRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/maintenance_status`, {
                    credentials: 'include',
                });
                if (maintRes.ok) {
                    const data = await maintRes.json();
                    if (data.active) {
                        setMaintenanceMsg(data.message || 'Mantenimiento en curso');
                        setShowMaintenance(true);
                    }
                }
            } catch {
                // Ignore
            }

            try {
                // Check suspension status
                const suspRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/suspension_status`, {
                    credentials: 'include',
                });
                if (suspRes.ok) {
                    const data = await suspRes.json();
                    if (data.suspended) {
                        setSuspensionData({
                            reason: data.reason || 'Servicio suspendido',
                            until: data.until || '',
                        });
                        setShowSuspension(true);
                    }
                }
            } catch {
                // Ignore
            }

            setLoading(false);
        }

        loadData();
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-iron-400" />
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
                    <div className="glass-card p-6 max-w-md w-full">
                        <h3 className="text-lg font-bold text-white mb-2">Mantenimiento</h3>
                        <p className="text-neutral-400 mb-4">{maintenanceMsg}</p>
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
                    <div className="glass-card p-6 max-w-md w-full border border-danger-500/30">
                        <h3 className="text-lg font-bold text-danger-400 mb-2">Servicio suspendido</h3>
                        <p className="text-neutral-400">
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
