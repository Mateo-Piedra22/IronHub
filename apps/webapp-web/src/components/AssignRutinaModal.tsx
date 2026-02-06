'use client';

import React, { useState, useEffect } from 'react';
import { Search, Loader2, UserPlus } from 'lucide-react';
import { Modal } from '@/components/ui';
import { api, type Usuario, type Rutina } from '@/lib/api';

interface AssignRutinaModalProps {
    isOpen: boolean;
    onClose: () => void;
    rutina: Rutina | null;
    onAssign: (rutina: Rutina, user: Usuario) => void;
}

export function AssignRutinaModal({ isOpen, onClose, rutina, onAssign }: AssignRutinaModalProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<Usuario[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setSearchQuery('');
            setSearchResults([]);
        }
    }, [isOpen]);

    useEffect(() => {
        const timeout = setTimeout(async () => {
            if (!searchQuery.trim()) {
                setSearchResults([]);
                return;
            }

            setLoading(true);
            try {
                const res = await api.getUsuarios({ search: searchQuery, page: 1, limit: 5 });
                if (res.ok && res.data) setSearchResults(res.data.usuarios);
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }, 500);
        return () => clearTimeout(timeout);
    }, [searchQuery]);

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Asignar "${rutina?.nombre}" a Usuario`}
            size="md"
        >
            <div className="space-y-4">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Buscar usuario..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-xl focus:ring-2 focus:ring-primary-500 outline-none transition-all text-white"
                        autoFocus
                    />
                </div>

                <div className="space-y-2 mt-4 max-h-[300px] overflow-y-auto">
                    {loading && <div className="p-4 text-center text-slate-500"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>}

                    {!loading && searchResults.length === 0 && searchQuery && (
                        <div className="p-4 text-center text-slate-500">No se encontraron usuarios</div>
                    )}

                    {searchResults.map((user) => (
                        <div
                            key={user.id}
                            onClick={() => onAssign(rutina!, user)}
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
                                        {user.email || 'Sin email'}
                                    </div>
                                </div>
                            </div>
                            <UserPlus className="w-4 h-4 text-slate-600 group-hover:text-primary-400" />
                        </div>
                    ))}
                </div>
            </div>
        </Modal>
    );
}

