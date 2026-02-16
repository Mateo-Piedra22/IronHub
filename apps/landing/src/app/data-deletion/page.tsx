import Link from 'next/link';

export default function DataDeletionPage() {
    return (
        <div className="main-shell">
            <div className="max-w-3xl">
                <h1 className="section-heading mb-4">Eliminación de datos</h1>
                <p className="hero-subtitle mb-10">
                Si querés solicitar la eliminación de datos asociados a tu cuenta, seguí las instrucciones a continuación.
                </p>

                <div className="space-y-6 leading-relaxed">
                    <section className="card p-6 space-y-2">
                        <h2 className="text-xl font-semibold">1. Solicitud por correo</h2>
                        <p>
                            Enviá un correo a{' '}
                            <a className="text-[var(--accent)]" href="mailto:soporte@motiona.xyz">
                                soporte@motiona.xyz
                            </a>{' '}
                            indicando:
                        </p>
                        <ul className="list-disc pl-5 space-y-1 meta-text">
                            <li>Nombre del gimnasio</li>
                            <li>Usuario/Email de acceso</li>
                            <li>Detalle de la solicitud (qué datos querés eliminar)</li>
                        </ul>
                    </section>

                    <section className="card p-6 space-y-2">
                        <h2 className="text-xl font-semibold">2. Si la solicitud proviene de Meta</h2>
                        <p>
                            Para integraciones de Meta (Facebook Login/WhatsApp), Meta puede enviarnos una solicitud de eliminación. En ese caso, se entregará un
                            código de confirmación y una URL de estado.
                        </p>
                        <p className="meta-text">
                            Si recibiste un código, podés verificar el estado en{' '}
                            <Link className="text-[var(--accent)]" href="/data-deletion/status">
                                /data-deletion/status
                            </Link>
                            .
                        </p>
                    </section>
                </div>
            </div>
        </div>
    );
}
