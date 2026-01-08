'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, FileText, Plus, Search, ChevronRight, Users, Loader2 } from 'lucide-react';
import { Modal, Button, Input } from '@/components/ui';
import { api, type Usuario, type Rutina } from '@/lib/api';
import { cn } from '@/lib/utils';

interface RutinaCreationWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onProceed: (rutinaData: Partial<Rutina>) => void;
}

export function RutinaCreationWizard({ isOpen, onClose, onProceed }: RutinaCreationWizardProps) {
    const [step, setStep] = useState<'choice' | 'user_search' | 'template_search'>('choice');
    const [loading, setLoading] = useState(false);

    // Search states
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);

    // Selection
    const [selectedUser, setSelectedUser] = useState<Usuario | null>(null);

    // Reset on open
    useEffect(() => {
        if (isOpen) {
            setStep('choice');
            setSearchQuery('');
            setSearchResults([]);
            setSelectedUser(null);
        }
    }, [isOpen]);

    // Handle search
    useEffect(() => {
        const timeout = setTimeout(async () => {
            if (!searchQuery.trim()) {
                setSearchResults([]);
                return;
            }

            setLoading(true);
            try {
                if (step === 'user_search') {
                    const res = await api.getUsuarios({ search: searchQuery, page: 1, limit: 5 });
                    if (res.ok && res.data) setSearchResults(res.data.usuarios);
                } else if (step === 'template_search') {
                    const res = await api.getRutinas({ search: searchQuery, plantillas: true });
                    if (res.ok && res.data) {
                        // Handle both array format and object format
                        const items = Array.isArray(res.data) ? res.data : (res.data as any).rutinas || [];
                        setSearchResults(items);
                    }
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }, 500);
        return () => clearTimeout(timeout);
    }, [searchQuery, step]);

    const handleOptionUser = () => {
        setStep('user_search');
        setSearchQuery('');
        setSearchResults([]);
    };

    const handleOptionTemplate = () => {
        setStep('template_search');
        setSearchQuery('');
        setSearchResults([]);
    };

    const handleOptionScratch = () => {
        onProceed({});
        onClose();
    };

    const handleSelectUser = (user: Usuario) => {
        onProceed({
            usuario_id: user.id,
            usuario_nombre: user.nombre
        });
        onClose();
    };

    const handleSelectTemplate = async (template: Rutina) => {
        setLoading(true);
        try {
            // Fetch full details of the template (including exercises)
            // Assuming getRutina returns full details or we pass what we have
            const res = await api.getRutina(template.id);
            // If getRutina gives full exercise details, use that. 
            // If not, we rely on what we have or need to fetch details.
            // Given previous tasks, getRutina SHOULD return full details including exercises.

            if (res.ok && res.data) {
                const fullTemplate = res.data;
                onProceed({
                    ...fullTemplate,
                    id: undefined, // Clear ID to create new
                    es_plantilla: false, // It's a routine now
                    nombre: `${fullTemplate.nombre} (Copia)`,
                    activa: true,
                    fecha_creacion: undefined,
                    usuario_id: undefined // Unless we want to combine user selection? Legacy didn't combine I think.
                });
                onClose();
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Crear Nueva Rutina"
            size="lg"
        >
            <div className="min-h-[400px]">
                {step === 'choice' && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
                        <ChoiceCard
                            icon={Users}
                            title="Asignar a Usuario"
                            description="Crear una rutina vacía vinculada a un alumno específico."
                            onClick={handleOptionUser}
                            color="bg-blue-500/10 text-blue-500 border-blue-500/20 hover:border-blue-500"
                        />
                        <ChoiceCard
                            icon={FileText}
                            title="Desde Plantilla"
                            description="Copiar una plantilla existente y modificarla."
                            onClick={handleOptionTemplate}
                            color="bg-purple-500/10 text-purple-500 border-purple-500/20 hover:border-purple-500"
                        />
                        <ChoiceCard
                            icon={Plus}
                            title="Desde Cero"
                            description="Crear una rutina completamente vacía sin asignar."
                            onClick={handleOptionScratch}
                            color="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 hover:border-emerald-500"
                        />
                    </div>
                )}

                {step === 'user_search' && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-4">
                            <Button variant="ghost" size="sm" onClick={() => setStep('choice')}>
                                ← Volver
                            </Button>
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

                            {!loading && searchResults.length === 0 && searchQuery && (
                                <div className="p-4 text-center text-slate-500">No se encontraron usuarios</div>
                            )}

                            {searchResults.map((user: Usuario) => (
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

                {step === 'template_search' && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-4">
                            <Button variant="ghost" size="sm" onClick={() => setStep('choice')}>
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

                            {!loading && searchResults.length === 0 && searchQuery && (
                                <div className="p-4 text-center text-slate-500">No se encontraron plantillas</div>
                            )}

                            {searchResults.map((template: Rutina) => (
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

function ChoiceCard({ icon: Icon, title, description, onClick, color }: any) {
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

