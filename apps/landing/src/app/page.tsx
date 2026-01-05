'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
    Dumbbell, Users, CreditCard, BarChart3, Shield, Zap,
    ChevronRight, ExternalLink, Mail, MapPin, Phone
} from 'lucide-react';

// Animation variants
const fadeInUp = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6 }
};

const staggerContainer = {
    animate: {
        transition: {
            staggerChildren: 0.1
        }
    }
};

// Header Component
function Header() {
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 50);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-neutral-950/80 backdrop-blur-xl border-b border-neutral-800/50' : ''
            }`}>
            <div className="max-w-7xl mx-auto px-6 py-4">
                <nav className="flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-iron-500 to-iron-700 flex items-center justify-center shadow-glow-sm group-hover:shadow-glow-md transition-shadow">
                            <Dumbbell className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-xl font-display font-bold text-white">
                            Iron<span className="text-iron-400">Hub</span>
                        </span>
                    </Link>

                    <div className="hidden md:flex items-center gap-8">
                        <a href="#features" className="text-neutral-400 hover:text-white transition-colors">Características</a>
                        <a href="#gyms" className="text-neutral-400 hover:text-white transition-colors">Gimnasios</a>
                        <a href="#about" className="text-neutral-400 hover:text-white transition-colors">Sobre Nosotros</a>
                        <a href="#contact" className="text-neutral-400 hover:text-white transition-colors">Contacto</a>
                    </div>

                    <Link
                        href="https://admin.ironhub.motiona.xyz"
                        className="btn-glow text-sm py-2 px-5"
                    >
                        Panel Admin
                    </Link>
                </nav>
            </div>
        </header>
    );
}

// Hero Section
function HeroSection() {
    return (
        <section className="relative min-h-screen flex items-center justify-center pt-20 overflow-hidden">
            {/* Animated grid background */}
            <div className="absolute inset-0 bg-mesh opacity-30" />

            <div className="max-w-7xl mx-auto px-6 py-20 text-center relative z-10">
                <motion.div
                    initial="initial"
                    animate="animate"
                    variants={staggerContainer}
                    className="space-y-8"
                >
                    {/* Badge */}
                    <motion.div variants={fadeInUp}>
                        <span className="badge">
                            <Zap className="w-3 h-3 mr-1.5" />
                            Plataforma Premium de Gestión
                        </span>
                    </motion.div>

                    {/* Main Heading */}
                    <motion.h1
                        variants={fadeInUp}
                        className="text-display-xl md:text-display-2xl font-display font-black tracking-tight"
                    >
                        <span className="text-white">Gestión de Gimnasios</span>
                        <br />
                        <span className="gradient-text">del Próximo Nivel</span>
                    </motion.h1>

                    {/* Subheading */}
                    <motion.p
                        variants={fadeInUp}
                        className="max-w-2xl mx-auto text-lg md:text-xl text-neutral-400 leading-relaxed"
                    >
                        IronHub es la plataforma integral que transforma la manera en que
                        administras tu gimnasio. Control total de socios, pagos, asistencias
                        y mucho más.
                    </motion.p>

                    {/* CTA Buttons */}
                    <motion.div
                        variants={fadeInUp}
                        className="flex flex-wrap items-center justify-center gap-4 pt-4"
                    >
                        <a href="#gyms" className="btn-glow flex items-center gap-2">
                            Explorar Gimnasios
                            <ChevronRight className="w-4 h-4" />
                        </a>
                        <Link href="https://admin.ironhub.motiona.xyz" className="btn-secondary flex items-center gap-2">
                            Acceder al Admin
                            <ExternalLink className="w-4 h-4" />
                        </Link>
                    </motion.div>

                    {/* Stats */}
                    <motion.div
                        variants={fadeInUp}
                        className="grid grid-cols-3 gap-8 max-w-lg mx-auto pt-12"
                    >
                        {[
                            { value: '99.9%', label: 'Uptime' },
                            { value: '24/7', label: 'Soporte' },
                            { value: '∞', label: 'Escalabilidad' }
                        ].map((stat) => (
                            <div key={stat.label} className="text-center">
                                <div className="text-2xl md:text-3xl font-display font-bold text-white">{stat.value}</div>
                                <div className="text-sm text-neutral-500">{stat.label}</div>
                            </div>
                        ))}
                    </motion.div>
                </motion.div>
            </div>

            {/* Bottom gradient fade */}
            <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-neutral-950 to-transparent" />
        </section>
    );
}

// Features Section
function FeaturesSection() {
    const features = [
        {
            icon: Users,
            title: 'Gestión de Socios',
            description: 'Control completo de membresías, estados y datos de contacto de todos tus socios.'
        },
        {
            icon: CreditCard,
            title: 'Pagos & Facturación',
            description: 'Sistema integrado de cobros, seguimiento de morosos y reportes financieros.'
        },
        {
            icon: BarChart3,
            title: 'Analytics Avanzados',
            description: 'Dashboards en tiempo real con métricas clave para tomar mejores decisiones.'
        },
        {
            icon: Shield,
            title: 'Multi-Tenant Seguro',
            description: 'Cada gimnasio tiene su base de datos aislada con seguridad enterprise.'
        },
        {
            icon: Dumbbell,
            title: 'Rutinas & Ejercicios',
            description: 'Biblioteca de ejercicios y creación de rutinas personalizadas para socios.'
        },
        {
            icon: Zap,
            title: 'WhatsApp Integrado',
            description: 'Notificaciones automáticas y comunicación directa con tus socios.'
        }
    ];

    return (
        <section id="features" className="py-24 relative">
            <div className="max-w-7xl mx-auto px-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="text-center mb-16"
                >
                    <h2 className="section-heading mb-4">
                        Todo lo que necesitas
                    </h2>
                    <p className="text-neutral-400 text-lg max-w-2xl mx-auto">
                        Una suite completa de herramientas diseñadas para optimizar cada aspecto de tu gimnasio.
                    </p>
                </motion.div>

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {features.map((feature, index) => (
                        <motion.div
                            key={feature.title}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: index * 0.1 }}
                            className="glass-card gradient-border p-6 group"
                        >
                            <div className="w-12 h-12 rounded-xl bg-iron-500/20 flex items-center justify-center mb-4 group-hover:bg-iron-500/30 transition-colors">
                                <feature.icon className="w-6 h-6 text-iron-400" />
                            </div>
                            <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                            <p className="text-neutral-400 text-sm leading-relaxed">{feature.description}</p>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}

// Gyms Showcase Section
function GymsSection() {
    const [gyms, setGyms] = useState<Array<{
        id: number;
        nombre: string;
        subdominio: string;
        status: string;
    }>>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadGyms() {
            try {
                const { fetchPublicGyms, fallbackGyms } = await import('@/lib/api');
                const data = await fetchPublicGyms();
                setGyms(data.length > 0 ? data : fallbackGyms);
            } catch {
                // Use fallback data on error
                setGyms([
                    { id: 1, nombre: 'Iron Fitness', subdominio: 'ironfitness', status: 'active' },
                    { id: 2, nombre: 'PowerGym', subdominio: 'powergym', status: 'active' },
                    { id: 3, nombre: 'CrossFit Arena', subdominio: 'crossfitarena', status: 'active' },
                ]);
            } finally {
                setLoading(false);
            }
        }
        loadGyms();
    }, []);

    return (
        <section id="gyms" className="py-24 relative">
            <div className="max-w-7xl mx-auto px-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="text-center mb-16"
                >
                    <h2 className="section-heading mb-4">
                        Gimnasios <span className="gradient-text">Conectados</span>
                    </h2>
                    <p className="text-neutral-400 text-lg max-w-2xl mx-auto">
                        Descubre los gimnasios que confían en IronHub para su gestión diaria.
                    </p>
                </motion.div>

                {loading ? (
                    <div className="flex justify-center items-center py-12">
                        <div className="w-8 h-8 border-2 border-iron-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {gyms.map((gym, index) => (
                            <motion.a
                                key={gym.id}
                                href={`https://${gym.subdominio}.ironhub.motiona.xyz`}
                                target="_blank"
                                rel="noopener noreferrer"
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: index * 0.1 }}
                                className="gym-card group cursor-pointer"
                            >
                                {/* Gym Avatar */}
                                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-iron-500 to-gold-600 flex items-center justify-center mb-4 shadow-glow-sm group-hover:shadow-glow-md transition-all">
                                    <span className="text-2xl font-display font-bold text-white">
                                        {gym.nombre.charAt(0)}
                                    </span>
                                </div>

                                <h3 className="text-xl font-semibold text-white mb-1 group-hover:text-iron-300 transition-colors">
                                    {gym.nombre}
                                </h3>
                                <p className="text-neutral-500 text-sm mb-4">
                                    {gym.subdominio}.ironhub.motiona.xyz
                                </p>

                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Users className="w-4 h-4 text-neutral-500" />
                                        <span className="text-sm text-neutral-400">Activo</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                        <div className="w-2 h-2 rounded-full bg-success-500" />
                                        <span className="text-xs text-success-400">Online</span>
                                    </div>
                                </div>

                                {/* Hover arrow */}
                                <div className="absolute top-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <ExternalLink className="w-5 h-5 text-iron-400" />
                                </div>
                            </motion.a>
                        ))}
                    </div>
                )}
            </div>
        </section>
    );
}

// About MotionA Section
function AboutSection() {
    return (
        <section id="about" className="py-24 relative">
            <div className="max-w-7xl mx-auto px-6">
                <div className="grid lg:grid-cols-2 gap-16 items-center">
                    {/* Content */}
                    <motion.div
                        initial={{ opacity: 0, x: -30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                    >
                        <span className="badge mb-4">Sobre Nosotros</span>
                        <h2 className="section-heading mb-6">
                            Desarrollado por <span className="gradient-text">MotionA</span>
                        </h2>
                        <div className="space-y-4 text-neutral-400 leading-relaxed">
                            <p>
                                IronHub es producto de <strong className="text-white">MotionA</strong>, una empresa
                                argentina dedicada al desarrollo de software empresarial de alta calidad.
                            </p>
                            <p>
                                Nuestro equipo combina experiencia en tecnología con un profundo entendimiento
                                de las necesidades del sector fitness, creando soluciones que realmente
                                transforman la operación diaria de los gimnasios.
                            </p>
                            <p>
                                Con IronHub, llevamos la gestión de gimnasios al siguiente nivel:
                                arquitectura multi-tenant, seguridad enterprise, y una experiencia
                                de usuario impecable.
                            </p>
                        </div>

                        <div className="flex flex-wrap gap-4 mt-8">
                            <div className="glass-card px-4 py-3">
                                <div className="text-2xl font-bold text-white">2026</div>
                                <div className="text-xs text-neutral-500">Año de Fundación</div>
                            </div>
                            <div className="glass-card px-4 py-3">
                                <div className="text-2xl font-bold text-white">Argentina</div>
                                <div className="text-xs text-neutral-500">Sede Central</div>
                            </div>
                            <div className="glass-card px-4 py-3">
                                <div className="text-2xl font-bold text-white">Enterprise</div>
                                <div className="text-xs text-neutral-500">Nivel de Soluciones</div>
                            </div>
                        </div>
                    </motion.div>

                    {/* Visual */}
                    <motion.div
                        initial={{ opacity: 0, x: 30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        className="relative"
                    >
                        <div className="glass-card p-8 relative overflow-hidden">
                            {/* MotionA Logo placeholder */}
                            <div className="w-32 h-32 mx-auto rounded-3xl bg-gradient-to-br from-iron-600 via-iron-500 to-gold-500 flex items-center justify-center mb-6 shadow-glow-lg animate-float">
                                <span className="text-4xl font-display font-black text-white">M</span>
                            </div>
                            <div className="text-center">
                                <h3 className="text-2xl font-display font-bold text-white mb-2">MotionA</h3>
                                <p className="text-neutral-400">Software Solutions</p>
                            </div>

                            {/* Decorative elements */}
                            <div className="absolute -top-20 -right-20 w-40 h-40 rounded-full bg-iron-500/20 blur-3xl" />
                            <div className="absolute -bottom-20 -left-20 w-40 h-40 rounded-full bg-gold-500/10 blur-3xl" />
                        </div>
                    </motion.div>
                </div>
            </div>
        </section>
    );
}

// Contact Section
function ContactSection() {
    return (
        <section id="contact" className="py-24 relative">
            <div className="max-w-7xl mx-auto px-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="glass-card p-12 relative overflow-hidden"
                >
                    <div className="relative z-10 grid lg:grid-cols-2 gap-12">
                        <div>
                            <h2 className="section-heading mb-4">
                                ¿Listo para empezar?
                            </h2>
                            <p className="text-neutral-400 mb-8">
                                Contactanos para llevar tu gimnasio al siguiente nivel con IronHub.
                            </p>

                            <div className="space-y-4">
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-lg bg-iron-500/20 flex items-center justify-center">
                                        <Mail className="w-5 h-5 text-iron-400" />
                                    </div>
                                    <div>
                                        <div className="text-sm text-neutral-500">Email</div>
                                        <a href="mailto:contacto@motiona.xyz" className="text-white hover:text-iron-300 transition-colors">
                                            contacto@motiona.xyz
                                        </a>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-lg bg-iron-500/20 flex items-center justify-center">
                                        <MapPin className="w-5 h-5 text-iron-400" />
                                    </div>
                                    <div>
                                        <div className="text-sm text-neutral-500">Ubicación</div>
                                        <span className="text-white">Buenos Aires, Argentina</span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-lg bg-iron-500/20 flex items-center justify-center">
                                        <Phone className="w-5 h-5 text-iron-400" />
                                    </div>
                                    <div>
                                        <div className="text-sm text-neutral-500">WhatsApp</div>
                                        <span className="text-white">+54 9 11 XXXX-XXXX</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center justify-center">
                            <Link
                                href="https://admin.ironhub.motiona.xyz"
                                className="btn-glow text-lg py-5 px-10 flex items-center gap-3"
                            >
                                Ir al Panel de Admin
                                <ExternalLink className="w-5 h-5" />
                            </Link>
                        </div>
                    </div>

                    {/* Decorative */}
                    <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-iron-500/10 blur-[100px]" />
                </motion.div>
            </div>
        </section>
    );
}

// Footer
function Footer() {
    return (
        <footer className="py-12 border-t border-neutral-800/50">
            <div className="max-w-7xl mx-auto px-6">
                <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-iron-500 to-iron-700 flex items-center justify-center">
                            <Dumbbell className="w-4 h-4 text-white" />
                        </div>
                        <span className="font-display font-bold text-white">IronHub</span>
                    </div>

                    <p className="text-neutral-500 text-sm">
                        © {new Date().getFullYear()} MotionA. Todos los derechos reservados.
                    </p>

                    <div className="flex items-center gap-6">
                        <a href="#" className="text-neutral-500 hover:text-white text-sm transition-colors">Términos</a>
                        <a href="#" className="text-neutral-500 hover:text-white text-sm transition-colors">Privacidad</a>
                    </div>
                </div>
            </div>
        </footer>
    );
}

// Main Page Component
export default function LandingPage() {
    return (
        <>
            <Header />
            <main>
                <HeroSection />
                <FeaturesSection />
                <GymsSection />
                <AboutSection />
                <ContactSection />
            </main>
            <Footer />
        </>
    );
}
