export default async function DataDeletionStatusPage({
    searchParams,
}: {
    searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
    const sp = ((await (searchParams || Promise.resolve({}))) || {}) as Record<string, string | string[] | undefined>;
    const codeRaw = sp.code;
    const code = Array.isArray(codeRaw) ? String(codeRaw[0] || '') : String(codeRaw || '');

    return (
        <div className="main-shell">
            <div className="max-w-3xl">
                <h1 className="section-heading mb-4">Estado de eliminación</h1>
                <p className="hero-subtitle mb-10">Esta pantalla se usa como URL de estado para solicitudes de eliminación de datos.</p>

                <div className="panel-note p-6">
                    <div className="text-sm meta-text">Código de confirmación</div>
                    <div className="font-mono mt-2">{code ? String(code) : '—'}</div>
                    <div className="text-sm meta-text mt-4">
                        Si necesitás asistencia adicional, escribinos a{' '}
                        <a className="text-[var(--accent)]" href="mailto:soporte@motiona.xyz">
                            soporte@motiona.xyz
                        </a>
                        .
                    </div>
                </div>
            </div>
        </div>
    );
}
