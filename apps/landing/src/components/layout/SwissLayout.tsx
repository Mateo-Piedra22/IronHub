import React from 'react';
import Link from 'next/link';
import { UnifiedShell } from './UnifiedShell';

interface SwissLayoutProps {
  children: React.ReactNode;
  leftPanel?: React.ReactNode;
  rightPanel?: React.ReactNode;
  hideNavigation?: boolean;
}

export default function SwissLayout({
  children,
  leftPanel,
  rightPanel,
  hideNavigation = false,
}: SwissLayoutProps) {
  const defaultLeftPanel = (
    <div className="flex flex-col flex-1 pb-safe">
      <div className="hidden lg:block">
        <span className="font-mono text-[10px] uppercase tracking-widest opacity-60 mb-4 block before:content-['['] before:mr-1 after:content-[']'] after:ml-1">Sistema</span>
        <div className="mb-10 flex items-center gap-3">
          {/* System Logo */}
          <img
            src="/IronHub.png"
            alt="IronHub"
            className="w-12 h-12 object-contain border border-black bg-white"
          />
          <div className="flex flex-col justify-center">
            <span className="font-bold text-2xl tracking-tighter leading-none uppercase text-black">IronHub</span>
            <span className="font-mono text-[10px] tracking-widest opacity-60 text-black">OPERATING SYSTEM</span>
          </div>
        </div>

        <div className="w-full border-t border-[var(--line-color,#000)] my-4" />
      </div>

      {!hideNavigation && (
        <nav className="flex flex-col gap-3 flex-1 mt-4 lg:mt-0 text-black">
          <Link href="/" className="group flex items-center gap-2 text-sm">
            <span className="w-2 h-2 bg-black opacity-0 group-hover:opacity-100 transition-opacity"></span>
            <span className="group-hover:translate-x-1 transition-transform font-bold text-black border-transparent">00. HOME</span>
          </Link>
          <Link href="/features" className="group flex items-center gap-2 text-sm">
            <span className="w-2 h-2 bg-black opacity-0 group-hover:opacity-100 transition-opacity"></span>
            <span className="group-hover:translate-x-1 transition-transform font-bold text-black">01. PLATAFORMA</span>
          </Link>
          <Link href="/pricing" className="group flex items-center gap-2 text-sm">
            <span className="w-2 h-2 bg-black opacity-0 group-hover:opacity-100 transition-opacity"></span>
            <span className="group-hover:translate-x-1 transition-transform font-bold text-black">02. PLANES</span>
          </Link>
          <Link href="/security" className="group flex items-center gap-2 text-sm">
            <span className="w-2 h-2 bg-black opacity-0 group-hover:opacity-100 transition-opacity"></span>
            <span className="group-hover:translate-x-1 transition-transform font-bold text-black">03. SEGURIDAD</span>
          </Link>
          <Link href="/docs" className="group flex items-center gap-2 text-sm">
            <span className="w-2 h-2 bg-black opacity-0 group-hover:opacity-100 transition-opacity"></span>
            <span className="group-hover:translate-x-1 transition-transform font-bold text-black border-transparent">04. DOCUMENTACIÓN</span>
          </Link>
          <Link href="/contact" className="group flex items-center gap-2 text-sm">
            <span className="w-2 h-2 bg-black opacity-0 group-hover:opacity-100 transition-opacity"></span>
            <span className="group-hover:translate-x-1 transition-transform font-bold text-black border-transparent">05. CONTACTO</span>
          </Link>
        </nav>
      )}

      <div className="hidden lg:block">
        {!hideNavigation && (
          <>
            <div className="w-full border-t border-[var(--line-color,#000)] my-4" />
            <div className="grid gap-2 text-sm opacity-80 text-black">
              <div className="font-mono text-xs uppercase tracking-wider opacity-60">SYSTEM ID: LNX-88</div>
              <div className="font-mono text-xs uppercase tracking-wider opacity-60">ACCESS: PUBLIC</div>
            </div>
          </>
        )}
      </div>

      <div className="pt-8 border-t border-[var(--line-color,#000)] mt-8">
        <span className="font-mono text-[10px] uppercase tracking-widest opacity-60 mb-4 block before:content-['['] before:mr-1 after:content-[']'] after:ml-1">Powered By</span>
        <a
          href="https://motiona.xyz"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 group opacity-70 hover:opacity-100 transition-opacity"
        >
          <img src="/motiona.png" alt="MotionA" className="w-8 h-8 object-contain" />
          <span className="font-bold uppercase tracking-wider text-sm group-hover:underline text-black">MotionA</span>
        </a>
      </div>
    </div>
  );

  const defaultRightPanel = (
    <>
      <span className="font-mono text-[10px] uppercase tracking-widest opacity-60 mb-4 block before:content-['['] before:mr-1 after:content-[']'] after:ml-1">Metadatos</span>
      <div className="font-mono text-xs leading-relaxed text-black">
        STATUS: OPERATIONAL<br />
        VERSION: 2.4.0<br />
        UPTIME: 99.9%<br />
        REGION: LATAM-SOUTH
      </div>
    </>
  );

  return (
    <UnifiedShell
      brandName="IronHub"
      brandLogo="/IronHub.png"
      leftPanelContent={leftPanel || defaultLeftPanel}
      rightPanelContent={rightPanel || defaultRightPanel}
    >
      {children}
    </UnifiedShell>
  );
}

