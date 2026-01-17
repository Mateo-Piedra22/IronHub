'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function SiteHeader() {
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 50);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <header
            className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
                scrolled ? 'bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/50' : ''
            }`}
        >
            <div className="max-w-7xl mx-auto px-6 py-4">
                <nav className="flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-3 group">
                        <img
                            src="/images/logo-ironhub.png"
                            alt="IronHub"
                            className="w-10 h-10 rounded-xl shadow-sm group-hover:shadow-md transition-shadow"
                        />
                        <span className="text-xl font-display font-bold text-white">
                            Iron<span className="text-primary-400">Hub</span>
                        </span>
                    </Link>

                    <div className="hidden md:flex items-center gap-8">
                        <Link href="/#features" className="text-slate-400 hover:text-white transition-colors">
                            Características
                        </Link>
                        <Link href="/#gyms" className="text-slate-400 hover:text-white transition-colors">
                            Gimnasios
                        </Link>
                        <Link href="/#about" className="text-slate-400 hover:text-white transition-colors">
                            Sobre Nosotros
                        </Link>
                        <Link href="/#contact" className="text-slate-400 hover:text-white transition-colors">
                            Contacto
                        </Link>
                        <Link href="/privacy" className="text-slate-400 hover:text-white transition-colors">
                            Privacidad
                        </Link>
                        <Link href="/terms" className="text-slate-400 hover:text-white transition-colors">
                            Términos
                        </Link>
                    </div>

                    <Link href="https://admin.ironhub.motiona.xyz" className="btn-primary text-sm py-2 px-5">
                        Panel Admin
                    </Link>
                </nav>
            </div>
        </header>
    );
}

