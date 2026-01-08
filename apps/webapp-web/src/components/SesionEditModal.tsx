"use client";

import { useState, useEffect, useMemo } from "react";
import { Clock, Calculator, AlertTriangle } from "lucide-react";
import { Modal, Button, Input, Select, Checkbox, useToast } from "@/components/ui";

interface Sesion {
    id: number;
    profesor_id: number;
    fecha: string;
    inicio: string;
    fin: string;
    tipo?: string;
    minutos?: number;
    notas?: string;
}

interface SesionEditModalProps {
    isOpen: boolean;
    onClose: () => void;
    sesion: Sesion | null;
    profesorId: number;
    onSuccess: () => void;
}

const TIPOS_SESION = [
    { value: "Auto", label: "Automático (según horario)" },
    { value: "En horario", label: "En horario" },
    { value: "Horas extra", label: "Horas extra" },
    { value: "Trabajo", label: "Trabajo" },
];

export function SesionEditModal({ isOpen, onClose, sesion, profesorId, onSuccess }: SesionEditModalProps) {
    const [fecha, setFecha] = useState("");
    const [inicio, setInicio] = useState("");
    const [fin, setFin] = useState("");
    const [tipo, setTipo] = useState("Auto");
    const [autoCalc, setAutoCalc] = useState(true);
    const [minutos, setMinutos] = useState("");
    const [loading, setLoading] = useState(false);
    const { success, error } = useToast();

    // Initialize form when modal opens
    useEffect(() => {
        if (isOpen && sesion) {
            setFecha(sesion.fecha?.split("T")[0] || "");
            setInicio(sesion.inicio || "");
            setFin(sesion.fin || "");
            setTipo(sesion.tipo || "Auto");
            setMinutos(sesion.minutos?.toString() || "");
            setAutoCalc(!sesion.minutos);
        } else if (isOpen) {
            // New session defaults
            const now = new Date();
            setFecha(now.toISOString().split("T")[0]);
            setInicio("");
            setFin("");
            setTipo("Auto");
            setMinutos("");
            setAutoCalc(true);
        }
    }, [isOpen, sesion]);

    // Calculate minutes automatically
    const calculatedMinutes = useMemo(() => {
        if (!inicio || !fin) return 0;
        try {
            const [startH, startM] = inicio.split(":").map(Number);
            const [endH, endM] = fin.split(":").map(Number);
            const startMinutes = startH * 60 + startM;
            const endMinutes = endH * 60 + endM;
            return Math.max(0, endMinutes - startMinutes);
        } catch {
            return 0;
        }
    }, [inicio, fin]);

    // Auto-update minutos when autoCalc is enabled
    useEffect(() => {
        if (autoCalc) {
            setMinutos(calculatedMinutes.toString());
        }
    }, [autoCalc, calculatedMinutes]);

    // Get day name
    const dayName = useMemo(() => {
        if (!fecha) return "";
        try {
            const date = new Date(fecha + "T12:00:00");
            return date.toLocaleDateString("es-AR", { weekday: "long" });
        } catch {
            return "";
        }
    }, [fecha]);

    // Format hours display
    const hoursDisplay = useMemo(() => {
        const mins = autoCalc ? calculatedMinutes : parseInt(minutos) || 0;
        const h = Math.floor(mins / 60);
        const m = mins % 60;
        return `${h}h ${m}m`;
    }, [autoCalc, calculatedMinutes, minutos]);

    // Type suggestion based on calculated minutes
    const suggestedType = useMemo(() => {
        // This would normally compare against profesor's scheduled hours
        // For now, we provide a simple heuristic
        if (calculatedMinutes > 480) return "Horas extra";
        return "En horario";
    }, [calculatedMinutes]);

    // Warning if manual type doesn't match suggestion
    const typeWarning = tipo === "En horario" && suggestedType === "Horas extra";

    const handleSubmit = async () => {
        if (!fecha || !inicio || !fin) {
            error("Fecha, inicio y fin son requeridos");
            return;
        }

        setLoading(true);
        try {
            const data = {
                profesor_id: profesorId,
                fecha,
                inicio,
                fin,
                tipo: tipo === "Auto" ? suggestedType : tipo,
                minutos: autoCalc ? calculatedMinutes : parseInt(minutos) || 0,
            };

            const url = sesion
                ? `/api/profesores/${profesorId}/sesiones/${sesion.id}`
                : `/api/profesores/${profesorId}/sesiones`;

            const res = await fetch(url, {
                method: sesion ? "PUT" : "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });

            if (res.ok) {
                success(sesion ? "Sesión actualizada" : "Sesión creada");
                onSuccess();
                onClose();
            } else {
                const responseData = await res.json().catch(() => ({}));
                error(responseData.detail || "Error al guardar sesión");
            }
        } catch {
            error("Error de conexión");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={sesion ? "Editar sesión" : "Nueva sesión"}
            size="md"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        Guardar
                    </Button>
                </>
            }
        >
            <div className="space-y-4">
                {/* Date and time row */}
                <div className="grid grid-cols-3 gap-3">
                    <div>
                        <Input
                            label="Fecha"
                            type="date"
                            value={fecha}
                            onChange={(e) => setFecha(e.target.value)}
                        />
                        {dayName && <div className="text-xs text-slate-500 mt-1 capitalize">{dayName}</div>}
                    </div>
                    <Input
                        label="Inicio"
                        type="time"
                        value={inicio}
                        onChange={(e) => setInicio(e.target.value)}
                    />
                    <Input
                        label="Fin"
                        type="time"
                        value={fin}
                        onChange={(e) => setFin(e.target.value)}
                    />
                </div>

                {/* Type */}
                <div>
                    <Select
                        label="Tipo"
                        value={tipo}
                        onChange={(e) => setTipo(e.target.value)}
                        options={TIPOS_SESION}
                    />
                    <div className="text-xs text-slate-500 mt-1">
                        Sugerencia según horarios: <span className="text-slate-300">{suggestedType}</span>
                    </div>
                    {typeWarning && (
                        <div className="mt-2 p-2 rounded-lg bg-warning-500/10 border border-warning-500/20 text-xs text-warning-400 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4" />
                            La selección "En horario" no coincide con el cálculo y se corregirá al guardar.
                        </div>
                    )}
                </div>

                {/* Minutes */}
                <div className="flex items-end gap-3">
                    <div className="flex-1">
                        <Input
                            label="Minutos"
                            type="number"
                            min={0}
                            value={minutos}
                            onChange={(e) => setMinutos(e.target.value)}
                            disabled={autoCalc}
                        />
                    </div>
                    <div className="pb-2">
                        <Checkbox
                            label="Cálculo automático"
                            checked={autoCalc}
                            onChange={(e) => setAutoCalc(e.target.checked)}
                        />
                    </div>
                </div>

                {/* Summary */}
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1 text-sm">
                    <div className="flex items-center gap-2 text-slate-400">
                        <Calculator className="w-4 h-4" />
                        <span>Minutos calculados:</span>
                        <span className="text-white font-medium">{calculatedMinutes}</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-400">
                        <Clock className="w-4 h-4" />
                        <span>Horas:</span>
                        <span className="text-white font-medium">{hoursDisplay}</span>
                    </div>
                </div>
            </div>
        </Modal>
    );
}

export default SesionEditModal;

