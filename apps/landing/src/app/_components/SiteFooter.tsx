import Link from 'next/link';
import Image from 'next/image';

export default function SiteFooter() {
    return (
        <footer className="rail-footer">
            <div className="rail-block">
                <div className="flex items-center gap-3">
                    <Image src="/images/logo-ironhub.png" alt="IronHub" width={32} height={32} className="logo-box" />
                    <span className="brand-text text-base">
                        Iron<span className="brand-accent">Hub</span>
                    </span>
                </div>
            </div>

            <div className="rail-block">
                <span className="spec-label">Desarrollado por</span>
                <a
                    href="https://motiona.xyz"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2"
                >
                    <Image src="/images/logo-motiona.png" alt="MotionA" width={32} height={32} className="logo-box" />
                    <span className="brand-text text-base">MotionA</span>
                </a>
            </div>

            <div className="rail-block">
                <span className="spec-label">Legal</span>
                <div className="flex flex-col gap-2">
                    <Link href="/terms" className="nav-item">
                        Términos
                    </Link>
                    <Link href="/privacy" className="nav-item">
                        Privacidad
                    </Link>
                    <Link href="/data-deletion" className="nav-item">
                        Eliminación de datos
                    </Link>
                </div>
                <p className="meta-text">© {new Date().getFullYear()} MotionA. Todos los derechos reservados.</p>
            </div>
        </footer>
    );
}
