'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function SiteHeader() {
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 50);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <header className={`site-header ${scrolled ? 'site-header-scrolled' : ''}`}>
            <Link href="/" className="site-brand">
                <Image
                    src="/images/logo-ironhub.png"
                    alt="IronHub"
                    width={40}
                    height={40}
                    className="logo-box"
                />
                <span className="brand-text">
                    Iron<span className="brand-accent">Hub</span>
                </span>
            </Link>

            <nav className="site-nav">
                <Link href="/#features" className="nav-item">
                    Características
                </Link>
                <Link href="/#gyms" className="nav-item">
                    Gimnasios
                </Link>
                <Link href="/#about" className="nav-item">
                    Sobre Nosotros
                </Link>
                <Link href="/#contact" className="nav-item">
                    Contacto
                </Link>
                <Link href="/privacy" className="nav-item">
                    Privacidad
                </Link>
                <Link href="/terms" className="nav-item">
                    Términos
                </Link>
            </nav>

            <Link href="https://admin.ironhub.motiona.xyz" className="btn-primary w-full text-center">
                Panel Admin
            </Link>
        </header>
    );
}
