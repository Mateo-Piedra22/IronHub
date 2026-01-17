export default function TermsPage() {
    return (
        <div className="max-w-4xl mx-auto px-6 pt-32 pb-16">
            <h1 className="text-3xl md:text-4xl font-display font-black text-white mb-4">Términos y Condiciones</h1>
            <p className="text-slate-400 mb-10">
                Estos términos regulan el uso de IronHub (desarrollado por MotionA). El uso del servicio implica aceptación de estas condiciones.
            </p>

            <div className="space-y-8 text-slate-300 leading-relaxed">
                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">1. Prestación del servicio</h2>
                    <p>
                        IronHub provee funcionalidades de gestión para gimnasios. El alcance puede variar según el plan o configuración del gimnasio.
                    </p>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">2. Responsabilidad por datos</h2>
                    <p>
                        El gimnasio es responsable por la veracidad y legitimidad de los datos que carga, así como por contar con los consentimientos necesarios
                        para comunicarse con sus socios.
                    </p>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">3. Uso de WhatsApp</h2>
                    <p>
                        El uso de WhatsApp Cloud API está sujeto a políticas de Meta/WhatsApp. El gimnasio debe cumplir dichas políticas y obtener opt-in cuando
                        corresponda.
                    </p>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">4. Disponibilidad</h2>
                    <p>
                        Se realizan esfuerzos razonables para mantener el servicio disponible. Pueden existir interrupciones por mantenimiento, incidentes o
                        dependencias externas.
                    </p>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">5. Contacto</h2>
                    <p>
                        Si necesitás ayuda, escribinos a{' '}
                        <a className="text-primary-400 hover:text-primary-300" href="mailto:soporte@motiona.xyz">
                            soporte@motiona.xyz
                        </a>
                        .
                    </p>
                </section>
            </div>
        </div>
    );
}

