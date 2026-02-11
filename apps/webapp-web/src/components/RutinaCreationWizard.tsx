'use client';

import { useState, useEffect, type ComponentType } from 'react';
import { FileText, Plus, Search, ChevronRight, Users, Loader2 } from 'lucide-react';
import { Modal, Button } from '@/components/ui';
import { api, type Usuario, type Rutina } from '@/lib/api';
import { cn } from '@/lib/utils';

interface RutinaCreationWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onProceed: (data: { usuario_id: number; usuario_nombre?: string | null; template_id?: number | null }) => void;
}

export function RutinaCreationWizard({ isOpen, onClose, onProceed }: RutinaCreationWizardProps) {
    const [step, setStep] = useState<'user_search' | 'source_choice' | 'template_search'>('user_search');
    const [loading, setLoading] = useState(false);
    const [selectedUser, setSelectedUser] = useState<Usuario | null>(null);

    // Search states
    const [searchQuery, setSearchQuery] = useState('');
    const [userResults, setUserResults] = useState<Usuario[]>([]);
    const [templateResults, setTemplateResults] = useState<Rutina[]>([]);

    // Reset on open
    useEffect(() => {
        if (isOpen) {
            setStep('user_search');
            setSearchQuery('');
            setUserResults([]);
            setTemplateResults([]);
            setSelectedUser(null);
        }
    }, [isOpen]);

    // Handle search
    useEffect(() => {
        const timeout = setTimeout(async () => {
            if (!searchQuery.trim()) {
                setUserResults([]);
                setTemplateResults([]);
                return;
            }

            setLoading(true);
            try {
                if (step === 'user_search') {
                    const res = await api.getUsuarios({ search: searchQuery, page: 1, limit: 5 });
                    if (res.ok && res.data) setUserResults(res.data.usuarios);
                    else setUserResults([]);
                    setTemplateResults([]);
                } else if (step === 'template_search') {
                    const res = await api.getRutinas({ search: searchQuery, plantillas: true });
                    if (res.ok && res.data) {
                        setTemplateResults(res.data.rutinas || []);
                    } else {
                        setTemplateResults([]);
                    }
                    setUserResults([]);
                }
            } catch {
            } finally {
                setLoading(false);
            }
        }, 500);
        return () => clearTimeout(timeout);
    }, [searchQuery, step]);

    const handleSelectUser = (user: Usuario) => {
        setSelectedUser(user);
        setStep('source_choice');
        setSearchQuery('');
        setUserResults([]);
    };

    const handleSelectTemplate = (template: Rutina) => {
        if (!selectedUser) return;
        onProceed({ usuario_id: selectedUser.id, usuario_nombre: selectedUser.nombre, template_id: template.id });
        onClose();
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Crear Nueva Rutina"
            size="lg"
        >
            <div className="min-h-[400px]">
                {step === 'user_search' && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-4">
                            <h3 className="font-semibold text-lg">Seleccionar Usuario</h3>
                        </div>

                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                placeholder="Buscar por nombre, DNI o email..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-9 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-xl focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                autoFocus
                            />
                        </div>

                        <div className="space-y-2 mt-4 max-h-[300px] overflow-y-auto">
                            {loading && <div className="p-4 text-center text-slate-500"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>}

                        {!loading && userResults.length === 0 && searchQuery && (
                                <div className="p-4 text-center text-slate-500">No se encontraron usuarios</div>
                            )}

                        {userResults.map((user) => (
                                <div
                                    key={user.id}
                                    onClick={() => handleSelectUser(user)}
                                    className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 hover:bg-slate-800 hover:border-slate-700 cursor-pointer transition-all flex items-center justify-between group"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 font-medium">
                                            {user.nombre.substring(0, 2).toUpperCase()}
                                        </div>
                                        <div>
                                            <div className="font-medium text-white group-hover:text-primary-400 transition-colors">
                                                {user.nombre}
                                            </div>
                                            <div className="text-xs text-slate-500">
                                                {user.email || user.dni || 'Sin datos de contacto'}
                                            </div>
                                        </div>
                                    </div>
                                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-white" />
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {step === 'source_choice' && selectedUser && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-4">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    setSelectedUser(null);
                                    setStep('user_search');
                                    setSearchQuery('');
                                    setTemplateResults([]);
                                }}
                            >
                                ← Cambiar usuario
                            </Button>
                            <div className="min-w-0">
                                <h3 className="font-semibold text-lg">Nueva rutina para</h3>
                                <div className="text-sm text-slate-400 truncate">{selectedUser.nombre}</div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                            <ChoiceCard
                                icon={Plus}
                                title="Rutina vacía"
                                description="Crear una rutina nueva y configurarla."
                                onClick={() => {
                                    onProceed({ usuario_id: selectedUser.id, usuario_nombre: selectedUser.nombre });
                                    onClose();
                                }}
                                color="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:border-emerald-500"
                            />
                            <ChoiceCard
                                icon={FileText}
                                title="Desde plantilla"
                                description="Asignar una plantilla existente y ajustarla."
                                onClick={() => {
                                    setStep('template_search');
                                    setSearchQuery('');
                                    setTemplateResults([]);
                                }}
                                color="bg-purple-500/10 text-purple-500 border-purple-500/20 hover:border-purple-500"
                            />
                        </div>
                    </div>
                )}

                {step === 'template_search' && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-4">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    setStep('source_choice');
                                    setSearchQuery('');
                                    setTemplateResults([]);
                                }}
                            >
                                ← Volver
                            </Button>
                            <h3 className="font-semibold text-lg">Seleccionar Plantilla</h3>
                        </div>

                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                placeholder="Buscar plantilla..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-9 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-xl focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                                autoFocus
                            />
                        </div>

                        <div className="space-y-2 mt-4 max-h-[300px] overflow-y-auto">
                            {loading && <div className="p-4 text-center text-slate-500"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>}

                        {!loading && templateResults.length === 0 && searchQuery && (
                                <div className="p-4 text-center text-slate-500">No se encontraron plantillas</div>
                            )}

                        {templateResults.map((template) => (
                                <div
                                    key={template.id}
                                    onClick={() => handleSelectTemplate(template)}
                                    className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 hover:bg-slate-800 hover:border-slate-700 cursor-pointer transition-all flex items-center justify-between group"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400">
                                            <FileText className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <div className="font-medium text-white group-hover:text-primary-400 transition-colors">
                                                {template.nombre}
                                            </div>
                                            <div className="text-xs text-slate-500">
                                                {template.categoria || 'General'} • {template.dias?.length || 0} días
                                            </div>
                                        </div>
                                    </div>
                                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-white" />
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </Modal>
    );
}

type ChoiceCardProps = {
    icon: ComponentType<{ className?: string }>;
    title: string;
    description: string;
    onClick: () => void;
    color: string;
};

function ChoiceCard({ icon: Icon, title, description, onClick, color }: ChoiceCardProps) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "flex flex-col items-start p-6 rounded-2xl border transition-all h-full text-left group",
                color
            )}
        >
            <div className="p-3 rounded-xl bg-white/5 mb-4 group-hover:scale-110 transition-transform">
                <Icon className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold mb-2">{title}</h3>
            <p className="text-sm opacity-80 leading-relaxed">
                {description}
            </p>
        </button>
    );
}

export default RutinaCreationWizard;

