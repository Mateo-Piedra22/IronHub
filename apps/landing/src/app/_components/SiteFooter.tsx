import Link from 'next/link';

export default function SiteFooter() {
    return (
        <footer className="py-12 border-t border-slate-800/50">
            <div className="max-w-7xl mx-auto px-6">
                <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                        <img src="/images/logo-ironhub.png" alt="IronHub" className="w-8 h-8 rounded-lg" />
                        <span className="font-display font-bold text-white">IronHub</span>
                    </div>

                    <div className="flex flex-col items-center gap-2">
                        <span className="text-slate-500 text-xs">Desarrollado por</span>
                        <a
                            href="https://motiona.xyz"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 group hover:opacity-80 transition-opacity"
                        >
                            <img src="/images/logo-motiona.png" alt="MotionA" className="w-8 h-8 rounded-lg" />
                            <span className="text-white font-semibold group-hover:text-primary-400 transition-colors">MotionA</span>
                        </a>
                    </div>

                    <div className="flex flex-col items-end gap-2">
                        <div className="flex items-center gap-6">
                            <Link href="/terms" className="text-slate-500 hover:text-white text-sm transition-colors">
                                Términos
                            </Link>
                            <Link href="/privacy" className="text-slate-500 hover:text-white text-sm transition-colors">
                                Privacidad
                            </Link>
                            <Link href="/data-deletion" className="text-slate-500 hover:text-white text-sm transition-colors">
                                Eliminación de datos
                            </Link>
                        </div>
                        <p className="text-slate-500 text-sm">© {new Date().getFullYear()} MotionA. Todos los derechos reservados.</p>
                    </div>
                </div>
            </div>
        </footer>
    );
}

