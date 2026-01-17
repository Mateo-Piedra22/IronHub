import Link from 'next/link';

export default function DataDeletionPage() {
    return (
        <div className="max-w-4xl mx-auto px-6 pt-32 pb-16">
            <h1 className="text-3xl md:text-4xl font-display font-black text-white mb-4">Eliminación de datos</h1>
            <p className="text-slate-400 mb-10">
                Si querés solicitar la eliminación de datos asociados a tu cuenta, seguí las instrucciones a continuación.
            </p>

            <div className="space-y-6 text-slate-300 leading-relaxed">
                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">1. Solicitud por correo</h2>
                    <p>
                        Enviá un correo a{' '}
                        <a className="text-primary-400 hover:text-primary-300" href="mailto:soporte@motiona.xyz">
                            soporte@motiona.xyz
                        </a>{' '}
                        indicando:
                    </p>
                    <ul className="list-disc pl-5 space-y-1">
                        <li>Nombre del gimnasio</li>
                        <li>Usuario/Email de acceso</li>
                        <li>Detalle de la solicitud (qué datos querés eliminar)</li>
                    </ul>
                </section>

                <section className="space-y-2">
                    <h2 className="text-xl font-semibold text-white">2. Si la solicitud proviene de Meta</h2>
                    <p>
                        Para integraciones de Meta (Facebook Login/WhatsApp), Meta puede enviarnos una solicitud de eliminación. En ese caso, se entregará un
                        código de confirmación y una URL de estado.
                    </p>
                    <p>
                        Si recibiste un código, podés verificar el estado en{' '}
                        <Link className="text-primary-400 hover:text-primary-300" href="/data-deletion/status">
                            /data-deletion/status
                        </Link>
                        .
                    </p>
                </section>
            </div>
        </div>
    );
}

