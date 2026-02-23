export default function PrivacyPage() {
    return (
        <>
            <header className="border-b border-current/20 pb-6">
                <div className="text-[10px] opacity-40 tracking-[0.3em] mb-3">━━━ POLÍTICA DE PRIVACIDAD ━━━</div>
                <h1 className="text-4xl font-bold tracking-tight">PRIVACIDAD</h1>
                <p className="mt-2 opacity-70 leading-relaxed">
                    Esta política describe cómo IronHub (desarrollado por MotionA) recopila, utiliza y protege la información.
                </p>
            </header>

            <div className="space-y-6">
                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">1. ALCANCE</h2>
                    <p className="opacity-80 leading-relaxed">
                        IronHub es una plataforma de gestión para gimnasios. Cada gimnasio opera su propio entorno (multi-tenant) y administra los datos de
                        sus socios y operaciones.
                    </p>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">2. DATOS QUE SE PROCESAN</h2>
                    <p className="opacity-80 leading-relaxed mb-3">Dependiendo del uso del sistema, se pueden procesar:</p>
                    <ul className="space-y-2 opacity-80">
                        <li className="flex gap-2"><span className="text-[10px] opacity-50">•</span>Datos de cuenta y acceso (usuarios, roles, registros de auditoría).</li>
                        <li className="flex gap-2"><span className="text-[10px] opacity-50">•</span>Datos operativos del gimnasio (clases, asistencias, rutinas).</li>
                        <li className="flex gap-2"><span className="text-[10px] opacity-50">•</span>Datos de facturación (pagos, períodos, estados).</li>
                        <li className="flex gap-2"><span className="text-[10px] opacity-50">•</span>Datos de mensajería (por ejemplo, logs de WhatsApp: tipo, fecha, estado).</li>
                    </ul>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">3. WHATSAPP / META</h2>
                    <p className="opacity-80 leading-relaxed">
                        Si el gimnasio conecta WhatsApp Cloud API, IronHub puede almacenar identificadores técnicos como <span className="font-bold">WABA ID</span> y{' '}
                        <span className="font-bold">Phone Number ID</span>. Los tokens de acceso se almacenan de forma cifrada cuando el entorno está configurado para ello.
                    </p>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">4. SEGURIDAD</h2>
                    <p className="opacity-80 leading-relaxed">
                        Se aplican medidas razonables de seguridad técnica y organizativa para proteger la información. Aun así, ningún sistema es 100% infalible.
                    </p>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">5. RETENCIÓN</h2>
                    <p className="opacity-80 leading-relaxed">
                        Los datos se conservan mientras el gimnasio utilice el servicio y/o según obligaciones legales o necesidades operativas del gimnasio.
                    </p>
                </section>

                <section className="border border-current/20 p-6 bg-[#f5f1e8]">
                    <h2 className="text-xl font-bold mb-3">6. CONTACTO</h2>
                    <p className="opacity-80 leading-relaxed">
                        Para consultas sobre privacidad o solicitudes relacionadas, escribinos a{' '}
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

