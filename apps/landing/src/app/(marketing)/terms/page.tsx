export default function TermsPage() {
    return (
        <>
            <header className="border-b border-current/20 pb-6">
                <div className="text-[10px] opacity-40 tracking-[0.3em] mb-3">━━━ TÉRMINOS Y CONDICIONES ━━━</div>
                <h1 className="text-4xl font-bold tracking-tight">TÉRMINOS DE SERVICIO</h1>
                <p className="mt-2 opacity-70 leading-relaxed">
                    Estos términos regulan el uso de IronHub (desarrollado por MotionA). El uso del servicio implica aceptación de estas condiciones.
                </p>
            </header>

            <div className="space-y-6">
                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">1. PRESTACIÓN DEL SERVICIO</h2>
                    <p className="opacity-80 leading-relaxed">
                        IronHub provee funcionalidades de gestión para gimnasios. El alcance puede variar según el plan o configuración del gimnasio.
                    </p>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">2. RESPONSABILIDAD POR DATOS</h2>
                    <p className="opacity-80 leading-relaxed">
                        El gimnasio es responsable por la veracidad y legitimidad de los datos que carga, así como por contar con los consentimientos necesarios
                        para comunicarse con sus socios.
                    </p>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">3. USO DE WHATSAPP</h2>
                    <p className="opacity-80 leading-relaxed">
                        El uso de WhatsApp Cloud API está sujeto a políticas de Meta/WhatsApp. El gimnasio debe cumplir dichas políticas y obtener opt-in cuando
                        corresponda.
                    </p>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">4. DISPONIBILIDAD</h2>
                    <p className="opacity-80 leading-relaxed">
                        Se realizan esfuerzos razonables para mantener el servicio disponible. Pueden existir interrupciones por mantenimiento, incidentes o
                        dependencias externas.
                    </p>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">5. CONTACTO</h2>
                    <p className="opacity-80 leading-relaxed">
                        Si necesitás ayuda, escribinos a{' '}
                        <a className="font-bold underline hover:opacity-80" href="mailto:soporte@motiona.xyz">
                            soporte@motiona.xyz
                        </a>
                        .
                    </p>
                </section>
            </div>
        </>
    );
}

