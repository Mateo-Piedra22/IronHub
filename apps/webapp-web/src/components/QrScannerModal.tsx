'use client';

import { useEffect, useRef, useState } from 'react';
import { Html5QrcodeScanner, Html5QrcodeSupportedFormats } from 'html5-qrcode';
import { X, Camera } from 'lucide-react';
import { Modal } from '@/components/ui';

interface QrScannerModalProps {
    isOpen: boolean;
    onClose: () => void;
    onScan: (decodedText: string) => void;
    title?: string;
    description?: string;
}

export function QrScannerModal({ isOpen, onClose, onScan, title = "Escanear QR", description }: QrScannerModalProps) {
    const scannerRef = useRef<Html5QrcodeScanner | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && !scannerRef.current) {
            // Give the modal animation time to finish and DOM to be ready
            const timer = setTimeout(() => {
                try {
                    const scanner = new Html5QrcodeScanner(
                        "qr-reader",
                        {
                            fps: 10,
                            qrbox: { width: 250, height: 250 },
                            formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
                            rememberLastUsedCamera: true
                        },
                        /* verbose= */ false
                    );

                    scanner.render(
                        (decodedText) => {
                            // On success
                            onScan(decodedText);
                            // Cleanup automatically on success? Or let parent close?
                            // Let's stop scanning to prevent duplicate triggers
                            scanner.clear().catch(console.error);
                            scannerRef.current = null;
                        },
                        (errorMessage) => {
                            // Ignore scan errors, they happen every frame no QR is found
                        }
                    );
                    scannerRef.current = scanner;
                } catch (e) {
                    console.error("Error initializing scanner:", e);
                    setError("No se pudo iniciar la cámara. Verificá los permisos.");
                }
            }, 300); // 300ms delay

            return () => clearTimeout(timer);
        }

        // Cleanup function
        return () => {
            if (scannerRef.current) {
                scannerRef.current.clear().catch(console.error);
                scannerRef.current = null;
            }
        };
    }, [isOpen, onScan]);

    // Handle close specifically to cleanup
    const handleClose = () => {
        if (scannerRef.current) {
            scannerRef.current.clear().catch(console.error);
            scannerRef.current = null;
        }
        onClose();
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={handleClose}
            title={title}
            size="md"
        >
            <div className="space-y-4">
                {description && (
                    <p className="text-slate-400 text-sm">{description}</p>
                )}

                <div className="bg-black rounded-lg overflow-hidden relative min-h-[300px] flex items-center justify-center">
                    <div id="qr-reader" className="w-full"></div>
                    {error && (
                        <div className="absolute inset-0 flex items-center justify-center p-4 text-center">
                            <p className="text-red-400">{error}</p>
                        </div>
                    )}
                </div>

                <style jsx global>{`
                    #qr-reader__scan_region {
                        background: transparent !important;
                    }
                    #qr-reader__dashboard_section_csr span {
                        color: white !important;
                    }
                `}</style>
            </div>
        </Modal>
    );
}

