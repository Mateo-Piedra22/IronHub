"use client";

/**
 * Landing Page - RECIBO TÉRMICO THEME
 * IronHub - Gestión de Gimnasios
 */

import Link from "next/link";
import { ArrowRight, Dumbbell, Users, CreditCard, BarChart3 } from "lucide-react";

function HeroSection() {
    return (
        <section className="border-b border-current/10 py-20 lg:py-32">
            <div className="max-w-4xl mx-auto px-6 font-mono">
                <div className="text-center space-y-8">
                    <div className="text-[10px] opacity-40 tracking-[0.3em]">
                        ━━━ GESTIÓN DE GIMNASIOS ━━━
                    </div>
                    
                    <h1 className="text-4xl lg:text-6xl font-bold tracking-tight leading-none">
                        IRONHUB
                        <span className="block text-2xl lg:text-3xl mt-4 opacity-60">
                            Socios · Pagos · Asistencias
                        </span>
                    </h1>

                    <div className="max-w-2xl mx-auto text-sm lg:text-base opacity-80 leading-relaxed">
                        Plataforma profesional de gestión integral. Control total de socios, pagos automáticos, 
                        check-in QR, rutinas personalizadas y reportes en tiempo real.
                    </div>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center pt-6">
                        <Link
                            href="https://admin.ironhub.motiona.xyz"
                            className="group bg-[#1a1a2e] text-[#f5f1e8] px-8 py-4 font-bold hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                        >
                            ACCESO ADMINISTRADOR
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </Link>
                        <Link
                            href="#features"
                            className="border-2 border-[#1a1a2e] px-8 py-4 font-bold hover:bg-[#1a1a2e]/5 transition-colors"
                        >
                            VER CARACTERÍSTICAS
                        </Link>
                    </div>

                    <div className="flex flex-wrap justify-center gap-6 pt-8 text-xs opacity-60">
                        <span>✓ MULTI-SUCURSAL</span>
                        <span>━</span>
                        <span>✓ API WHATSAPP</span>
                        <span>━</span>
                        <span>✓ CHECK-IN QR</span>
                    </div>
                </div>
            </div>
        </section>
    );
}

function FeaturesSection() {
    const features = [
        {
            code: "F001",
            icon: Users,
            title: "Gestión de Socios",
            desc: "Control completo de membresías, estados, y datos de contacto. Segmentación y etiquetas personalizadas.",
        },
        {
            code: "F002",
            icon: CreditCard,
            title: "Pagos Automáticos",
            desc: "Integración con Mercado Pago. Cobros automáticos, recordatorios y gestión de deudas.",
        },
        {
            code: "F003",
            icon: Dumbbell,
            title: "Rutinas y Clases",
            desc: "Motor de rutinas dinámico. Crea plantillas, asigna a socios y programa clases grupales.",
        },
        {
            code: "F004",
            icon: BarChart3,
            title: "Analytics en Tiempo Real",
            desc: "Dashboard con métricas clave: ingresos, asistencias, renovaciones y crecimiento.",
        },
    ];

    return (
        <section id="features" className="py-20 lg:py-32 border-b border-current/10">
            <div className="max-w-6xl mx-auto px-6">
                <div className="text-center mb-16 font-mono">
                    <div className="text-[10px] opacity-40 tracking-[0.3em] mb-4">
                        ━━━ CARACTERÍSTICAS ━━━
                    </div>
                    <h2 className="text-3xl lg:text-5xl font-bold">
                        TODO LO QUE NECESITAS
                    </h2>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                    {features.map((feature) => (
                        <div 
                            key={feature.code}
                            className="border border-current/20 p-6 hover:border-current/40 transition-all group"
                        >
                            <div className="font-mono">
                                <div className="flex items-center gap-3 mb-4">
                                    <feature.icon className="w-6 h-6 opacity-60" />
                                    <div className="text-[10px] opacity-40">[{feature.code}]</div>
                                </div>
                                <h3 className="text-lg font-bold mb-3">{feature.title}</h3>
                                <p className="text-sm opacity-70 leading-relaxed">{feature.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}

function GymsSection() {
    return (
        <section id="gyms" className="py-20 lg:py-32 border-b border-current/10">
            <div className="max-w-6xl mx-auto px-6">
                <div className="text-center mb-16 font-mono">
                    <div className="text-[10px] opacity-40 tracking-[0.3em] mb-4">
                        ━━━ GIMNASIOS ━━━
                    </div>
                    <h2 className="text-3xl lg:text-5xl font-bold mb-4">
                        GIMNASIOS ACTIVOS
                    </h2>
                    <p className="text-sm opacity-70 max-w-2xl mx-auto">
                        IronHub potencia gimnasios en toda Argentina.
                    </p>
                </div>

                <div className="border border-current/20 p-8 text-center font-mono">
                    <div className="text-4xl font-bold mb-2">PRÓXIMAMENTE</div>
                    <div className="text-sm opacity-60">Directorio público de gimnasios usando IronHub</div>
                </div>
            </div>
        </section>
    );
}

function AboutSection() {
    return (
        <section id="about" className="py-20 lg:py-32 border-b border-current/10">
            <div className="max-w-4xl mx-auto px-6 font-mono">
                <div className="text-center mb-12">
                    <div className="text-[10px] opacity-40 tracking-[0.3em] mb-4">
                        ━━━ SOBRE NOSOTROS ━━━
                    </div>
                    <h2 className="text-3xl lg:text-5xl font-bold">
                        DESARROLLADO POR MOTIONA
                    </h2>
                </div>

                <div className="space-y-6 text-sm leading-relaxed opacity-80">
                    <p>
                        IronHub es una plataforma profesional de gestión de gimnasios desarrollada 
                        por <strong>MotionA</strong>, con sede en Santa Fe, Argentina.
                    </p>
                    <p>
                        Nuestro objetivo es simplificar la administración diaria de gimnasios, 
                        permitiendo a los dueños enfocarse en lo que realmente importa: 
                        brindar la mejor experiencia a sus socios.
                    </p>
                    <p>
                        Con tecnología de punta, diseño intuitivo y soporte dedicado, 
                        IronHub transforma la manera en que los gimnasios operan.
                    </p>
                </div>

                <div className="mt-12 text-center">
                    <Link
                        href="https://motiona.xyz"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 border-2 border-[#1a1a2e] px-8 py-3 font-bold hover:bg-[#1a1a2e]/5 transition-colors text-sm"
                    >
                        CONOCER MOTIONA
                        <ArrowRight className="w-4 h-4" />
                    </Link>
                </div>
            </div>
        </section>
    );
}

function CTASection() {
    return (
        <section className="py-20 lg:py-32">
            <div className="max-w-4xl mx-auto px-6 text-center font-mono">
                <h2 className="text-3xl lg:text-5xl font-bold mb-6">
                    ¿ADMINISTRAS UN GIMNASIO?
                </h2>
                <p className="text-sm opacity-70 mb-8 max-w-2xl mx-auto">
                    Contactanos para implementar IronHub en tu gimnasio.
                </p>
                <Link
                    href="mailto:soporte@motiona.xyz"
                    className="inline-flex items-center gap-3 bg-[#1a1a2e] text-[#f5f1e8] px-10 py-5 font-bold text-lg hover:opacity-90 transition-opacity"
                >
                    CONTACTAR A MOTIONA
                    <ArrowRight className="w-5 h-5" />
                </Link>
            </div>
        </section>
    );
}

export default function LandingPage() {
    return (
        <>
            <HeroSection />
            <FeaturesSection />
            <GymsSection />
            <AboutSection />
            <CTASection />
        </>
    );
}
