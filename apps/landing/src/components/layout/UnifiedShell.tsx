"use client";

import React, { useState, useEffect } from "react";
import { Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

interface UnifiedShellProps {
    children: React.ReactNode;
    leftPanelContent: React.ReactNode;
    rightPanelContent?: React.ReactNode;
    brandName: string;
    brandLogo: string;
}

export function UnifiedShell({
    children,
    leftPanelContent,
    rightPanelContent,
    brandName,
    brandLogo,
}: UnifiedShellProps) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    // Close mobile menu on resize to desktop
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth >= 1024) {
                setIsMobileMenuOpen(false);
            }
        };
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, []);

    return (
        <div className="min-h-screen flex flex-col lg:block font-sans" data-brand={brandName.toLowerCase()}>
            {/* MOBILE TOPBAR */}
            <header className="lg:hidden sticky top-0 z-50 flex items-center justify-between px-4 py-3 bg-[var(--sidebar-bg,#e8e8e8)] border-b border-[var(--line-color,#000)] shadow-sm">
                <Link href="/" className="flex items-center gap-3">
                    <img
                        src={brandLogo}
                        alt={brandName}
                        className="w-8 h-8 object-contain border border-black p-0.5 bg-white rounded-md"
                    />
                    <span className="font-bold text-xl tracking-tighter leading-none uppercase text-black">
                        {brandName}
                    </span>
                </Link>
                <button
                    onClick={() => setIsMobileMenuOpen(true)}
                    className="p-2 border border-black bg-white hover:bg-black hover:text-white transition-colors"
                    aria-label="Open Menu"
                >
                    <Menu className="w-5 h-5" />
                </button>
            </header>

            {/* DESKTOP GRID & MAIN LAYOUT */}
            <div className="flex-1 lg:grid lg:grid-cols-[250px_minmax(0,1fr)_300px] w-full max-w-[100vw] overflow-x-hidden">

                {/* DESKTOP LEFT SIDEBAR */}
                <aside className="hidden lg:flex col-span-1 border-r border-[var(--line-color,#000)] p-8 min-h-screen flex-col justify-between bg-[var(--sidebar-bg,#e8e8e8)] sticky top-0 h-screen overflow-y-auto custom-scrollbar">
                    {leftPanelContent}
                </aside>

                {/* MAIN CONTENT AREA */}
                <main className="col-span-1 border-r border-[var(--line-color,#000)] relative min-w-0 flex flex-col min-h-screen">
                    <div className="flex-1">
                        {children}
                    </div>
                    {/* Render Right Panel at bottom of main content on mobile */}
                    {rightPanelContent && (
                        <div className="lg:hidden p-6 md:p-8 border-t border-[var(--line-color,#000)] bg-[var(--sidebar-bg,#e8e8e8)]">
                            {rightPanelContent}
                        </div>
                    )}
                </main>

                {/* DESKTOP RIGHT SIDEBAR */}
                {rightPanelContent && (
                    <aside className="hidden lg:block col-span-1 p-8 sticky top-0 h-screen overflow-y-auto custom-scrollbar bg-[var(--right-sidebar-bg,transparent)]">
                        {rightPanelContent}
                    </aside>
                )}
            </div>

            {/* MOBILE DRAWER */}
            <AnimatePresence>
                {isMobileMenuOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 0.5 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsMobileMenuOpen(false)}
                            className="fixed inset-0 bg-black z-[60] lg:hidden"
                        />
                        <motion.aside
                            initial={{ x: "-100%" }}
                            animate={{ x: 0 }}
                            exit={{ x: "-100%" }}
                            transition={{ type: "spring", damping: 25, stiffness: 200 }}
                            className="fixed top-0 left-0 bottom-0 w-4/5 max-w-[320px] bg-[var(--sidebar-bg,#e8e8e8)] border-r border-black z-[70] flex flex-col p-6 overflow-y-auto"
                        >
                            <div className="flex justify-between items-center mb-6">
                                <Link href="/" className="flex items-center gap-3" onClick={() => setIsMobileMenuOpen(false)}>
                                    <img
                                        src={brandLogo}
                                        alt={brandName}
                                        className="w-8 h-8 object-contain border border-black p-0.5 bg-white rounded-md"
                                    />
                                    <span className="font-bold text-xl tracking-tighter leading-none uppercase text-black">
                                        {brandName}
                                    </span>
                                </Link>
                                <button
                                    onClick={() => setIsMobileMenuOpen(false)}
                                    className="p-2 border border-black bg-white hover:bg-black hover:text-white transition-colors"
                                    aria-label="Close Menu"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            <div
                                className="flex-1 flex flex-col justify-between"
                                onClick={(e) => {
                                    // If clicked a link, close menu
                                    if ((e.target as HTMLElement).tagName === 'A' || (e.target as HTMLElement).closest('a')) {
                                        setIsMobileMenuOpen(false);
                                    }
                                }}
                            >
                                {leftPanelContent}
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
