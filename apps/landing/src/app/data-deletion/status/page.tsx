export default async function DataDeletionStatusPage({
    searchParams,
}: {
    searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
    const sp = ((await (searchParams || Promise.resolve({}))) || {}) as Record<string, string | string[] | undefined>;
    const codeRaw = sp.code;
    const code = Array.isArray(codeRaw) ? String(codeRaw[0] || '') : String(codeRaw || '');

    return (
        <div className="max-w-4xl mx-auto px-6 pt-32 pb-16">
            <h1 className="text-3xl md:text-4xl font-display font-black text-white mb-4">Estado de eliminación</h1>
            <p className="text-slate-400 mb-10">Esta pantalla se usa como URL de estado para solicitudes de eliminación de datos.</p>

            <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-slate-300">
                <div className="text-slate-500 text-sm">Código de confirmación</div>
                <div className="text-white font-mono mt-2">{code ? String(code) : '—'}</div>
                <div className="text-slate-400 text-sm mt-4">
                    Si necesitás asistencia adicional, escribinos a{' '}
                    <a className="text-primary-400 hover:text-primary-300" href="mailto:soporte@motiona.xyz">
                        soporte@motiona.xyz
                    </a>
                    .
                </div>
            </div>
        </div>
    );
}
