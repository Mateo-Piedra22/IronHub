import { useEffect, useRef, useState } from 'react';
import { Html5QrcodeScanner } from 'html5-qrcode';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface QRScannerModalProps {
    isOpen: boolean;
    onClose: () => void;
    onScan: (decodedText: string) => void;
    description?: string;
}

export function QRScannerModal({ isOpen, onClose, onScan, description }: QRScannerModalProps) {
    const scannerRef = useRef<Html5QrcodeScanner | null>(null);

    useEffect(() => {
        if (isOpen && !scannerRef.current) {
            // Give DOM time to render the 'reader' element
            setTimeout(() => {
                const scanner = new Html5QrcodeScanner(
                    "reader",
                    { fps: 10, qrbox: { width: 250, height: 250 } },
                    /* verbose= */ false
                );

                scanner.render(
                    (decodedText) => {
                        onScan(decodedText);
                        // Optional: Close on success? Let parent handle it.
                        // But we should stop scanning to avoid repeated calls.
                        scanner.clear().catch(console.error);
                        onClose();
                    },
                    (errorMessage) => {
                        // console.log(errorMessage); // Ignore parse errors
                    }
                );
                scannerRef.current = scanner;
            }, 100);
        }

        return () => {
            if (scannerRef.current) {
                scannerRef.current.clear().catch(console.error);
                scannerRef.current = null;
            }
        };
    }, [isOpen, onScan, onClose]);

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            >
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="bg-slate-900 rounded-2xl w-full max-w-md overflow-hidden border border-slate-800"
                >
                    <div className="p-4 border-b border-slate-800 flex justify-between items-center">
                        <h3 className="font-semibold text-white">Escanear Rutina</h3>
                        <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white">
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    <div className="p-4 bg-black">
                        <div id="reader" className="w-full rounded-xl overflow-hidden"></div>
                        <p className="text-center text-slate-400 mt-4 text-sm">
                            Apunta tu cámara al código QR de la rutina
                        </p>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
