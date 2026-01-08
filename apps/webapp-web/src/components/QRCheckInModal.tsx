"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { QrCode, Clock, Check, X, RefreshCw } from "lucide-react";
import { Modal, Button, useToast } from "@/components/ui";

interface QRCheckInModalProps {
    isOpen: boolean;
    onClose: () => void;
    userId: number;
    userName: string;
}

export function QRCheckInModal({ isOpen, onClose, userId, userName }: QRCheckInModalProps) {
    const [token, setToken] = useState<string | null>(null);
    const [expiresAt, setExpiresAt] = useState<Date | null>(null);
    const [timeLeft, setTimeLeft] = useState(0);
    const [status, setStatus] = useState<"generating" | "waiting" | "confirmed" | "expired">("generating");
    const [loading, setLoading] = useState(false);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const pollingRef = useRef<NodeJS.Timeout | null>(null);
    const countdownRef = useRef<NodeJS.Timeout | null>(null);
    const { success, error } = useToast();

    // Generate QR token
    const generateToken = useCallback(async () => {
        setLoading(true);
        setStatus("generating");
        try {
            const res = await fetch(`/api/usuarios/${userId}/qr`, {
                method: "POST",
                credentials: "include"
            });
            if (res.ok) {
                const data = await res.json();
                setToken(data.token || data.qr_token);
                const expires = new Date(data.expires_at || Date.now() + 5 * 60 * 1000);
                setExpiresAt(expires);
                setStatus("waiting");
                // Draw QR code
                if (canvasRef.current && data.token) {
                    drawQRCode(canvasRef.current, data.token);
                }
            } else {
                error("Error al generar QR");
                setStatus("expired");
            }
        } catch {
            error("Error de conexión");
            setStatus("expired");
        } finally {
            setLoading(false);
        }
    }, [userId, error]);

    // Simple QR code drawing (placeholder - in production use a library like qrcode)
    const drawQRCode = (canvas: HTMLCanvasElement, tokenData: string) => {
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Clear canvas
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw placeholder pattern (in production, use proper QR generation)
        ctx.fillStyle = "#000";
        const size = canvas.width;
        const cellSize = Math.floor(size / 25);

        // Generate simple visual pattern from token
        const hash = tokenData.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
        for (let y = 0; y < 25; y++) {
            for (let x = 0; x < 25; x++) {
                // Border patterns
                const isBorder = x < 7 && y < 7 || x >= 18 && y < 7 || x < 7 && y >= 18;
                const isInnerBorder = (x >= 2 && x <= 4 && y >= 2 && y <= 4) ||
                    (x >= 20 && x <= 22 && y >= 2 && y <= 4) ||
                    (x >= 2 && x <= 4 && y >= 20 && y <= 22);

                if (isBorder) {
                    const edge = x === 0 || x === 6 || y === 0 || y === 6 ||
                        x === 18 || x === 24 || y === 18 || y === 24;
                    if (edge || isInnerBorder) {
                        ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
                    }
                } else {
                    // Data pattern based on hash
                    const fill = ((hash * (x + 1) * (y + 1)) % 3) === 0;
                    if (fill) {
                        ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
                    }
                }
            }
        }

        // Draw center text
        ctx.fillStyle = "#333";
        ctx.font = "10px monospace";
        ctx.textAlign = "center";
        ctx.fillText(tokenData.slice(0, 8) + "...", size / 2, size / 2);
    };

    // Countdown timer
    useEffect(() => {
        if (!isOpen || !expiresAt) return;

        const updateCountdown = () => {
            const now = Date.now();
            const remaining = Math.max(0, expiresAt.getTime() - now);
            setTimeLeft(Math.ceil(remaining / 1000));

            if (remaining <= 0) {
                setStatus("expired");
            }
        };

        updateCountdown();
        countdownRef.current = setInterval(updateCountdown, 1000);

        return () => {
            if (countdownRef.current) clearInterval(countdownRef.current);
        };
    }, [isOpen, expiresAt]);

    // Polling for confirmation
    useEffect(() => {
        if (!isOpen || status !== "waiting" || !token) return;

        const poll = async () => {
            try {
                const res = await fetch(`/api/checkin/verify?token=${token}`, {
                    credentials: "include"
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.verified || data.success) {
                        setStatus("confirmed");
                        success("¡Check-in confirmado!");
                        setTimeout(onClose, 2000);
                    }
                }
            } catch {
                // Ignore polling errors
            }
        };

        pollingRef.current = setInterval(poll, 3000);

        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, [isOpen, status, token, success, onClose]);

    // Initial generation
    useEffect(() => {
        if (isOpen) {
            generateToken();
        }
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
            if (countdownRef.current) clearInterval(countdownRef.current);
        };
    }, [isOpen, generateToken]);

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s.toString().padStart(2, "0")}`;
    };

    const progress = expiresAt
        ? Math.max(0, Math.min(100, ((expiresAt.getTime() - Date.now()) / (5 * 60 * 1000)) * 100))
        : 0;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="QR de Check-in"
            size="sm"
        >
            <div className="flex flex-col items-center gap-4 py-4">
                {/* User name */}
                <div className="text-lg font-semibold text-white">{userName}</div>

                {/* QR Canvas */}
                <div className="relative p-4 bg-white rounded-xl shadow-lg">
                    <canvas
                        ref={canvasRef}
                        width={200}
                        height={200}
                        className="rounded-lg"
                    />
                    {status === "confirmed" && (
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="absolute inset-0 flex items-center justify-center bg-success-500/90 rounded-xl"
                        >
                            <Check className="w-16 h-16 text-white" />
                        </motion.div>
                    )}
                    {status === "expired" && (
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="absolute inset-0 flex items-center justify-center bg-danger-500/90 rounded-xl"
                        >
                            <X className="w-16 h-16 text-white" />
                        </motion.div>
                    )}
                </div>

                {/* Token (masked) */}
                {token && (
                    <div className="font-mono text-sm text-slate-500">
                        Token: {token.slice(0, 4)}****{token.slice(-4)}
                    </div>
                )}

                {/* Countdown */}
                <div className="w-full space-y-2">
                    <div className="flex items-center justify-center gap-2">
                        <Clock className="w-4 h-4 text-slate-400" />
                        <span className="font-medium">
                            {status === "waiting" && `Tiempo restante: ${formatTime(timeLeft)}`}
                            {status === "confirmed" && "¡Confirmado!"}
                            {status === "expired" && "Expirado"}
                            {status === "generating" && "Generando..."}
                        </span>
                    </div>

                    {/* Progress bar */}
                    <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                        <motion.div
                            className={`h-full rounded-full ${status === "confirmed" ? "bg-success-500" :
                                    status === "expired" ? "bg-danger-500" :
                                        "bg-primary-500"
                                }`}
                            initial={{ width: "100%" }}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 1, ease: "linear" }}
                        />
                    </div>
                </div>

                {/* Status message */}
                <div className="text-sm text-slate-400 text-center">
                    {status === "waiting" && "Escanea el código para registrar asistencia"}
                    {status === "confirmed" && "Asistencia registrada exitosamente"}
                    {status === "expired" && "El código ha expirado"}
                    {status === "generating" && "Generando código QR..."}
                </div>

                {/* Actions */}
                {status === "expired" && (
                    <Button
                        leftIcon={<RefreshCw className="w-4 h-4" />}
                        onClick={generateToken}
                        isLoading={loading}
                    >
                        Generar nuevo
                    </Button>
                )}
            </div>
        </Modal>
    );
}

export default QRCheckInModal;

