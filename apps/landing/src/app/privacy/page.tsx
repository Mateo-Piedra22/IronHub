export default function PrivacyPage() {
    return (
        <div className="max-w-4xl mx-auto px-6 pt-32 pb-16">
            <h1 className="text-3xl md:text-4xl font-display font-black text-white mb-4">Política de Privacidad</h1>
            <p className="text-slate-400 mb-10">
                Esta política describe cómo IronHub (desarrollado por MotionA) recopila, utiliza y protege la información.
            </p>

            <div className="space-y-8 text-slate-300 leading-relaxed">
                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">1. Alcance</h2>
                    <p>
                        IronHub es una plataforma de gestión para gimnasios. Cada gimnasio opera su propio entorno (multi-tenant) y administra los datos de
                        sus socios y operaciones.
                    </p>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">2. Datos que se procesan</h2>
                    <p>Dependiendo del uso del sistema, se pueden procesar:</p>
                    <ul className="list-disc pl-5 space-y-1">
                        <li>Datos de cuenta y acceso (usuarios, roles, registros de auditoría).</li>
                        <li>Datos operativos del gimnasio (clases, asistencias, rutinas).</li>
                        <li>Datos de facturación (pagos, períodos, estados).</li>
                        <li>Datos de mensajería (por ejemplo, logs de WhatsApp: tipo, fecha, estado).</li>
                    </ul>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">3. WhatsApp / Meta</h2>
                    <p>
                        Si el gimnasio conecta WhatsApp Cloud API, IronHub puede almacenar identificadores técnicos como <span className="text-white">WABA ID</span> y{' '}
                        <span className="text-white">Phone Number ID</span>. Los tokens de acceso se almacenan de forma cifrada cuando el entorno está configurado para ello.
                    </p>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">4. Seguridad</h2>
                    <p>
                        Se aplican medidas razonables de seguridad técnica y organizativa para proteger la información. Aun así, ningún sistema es 100% infalible.
                    </p>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">5. Retención</h2>
                    <p>
                        Los datos se conservan mientras el gimnasio utilice el servicio y/o según obligaciones legales o necesidades operativas del gimnasio.
                    </p>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">6. Contacto</h2>
                    <p>
                        Para consultas sobre privacidad o solicitudes relacionadas, escribinos a{' '}
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

