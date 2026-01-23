'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
    UserPlus,
    Filter,
    Download,
    MoreVertical,
    Edit,
    Trash2,
    CheckCircle2,
    XCircle,
    RefreshCw,
    Phone,
    Mail,
} from 'lucide-react';
import {
    Button,
    SearchInput,
    DataTable,
    Modal,
    ConfirmModal,
    useToast,
    Input,
    Select,
    Checkbox,
    Textarea,
    type Column,
} from '@/components/ui';
import UserSidebar from '@/components/UserSidebar';
import { api, type Usuario, type UsuarioCreateInput, type TipoCuota } from '@/lib/api';
import { formatDate, formatDateRelative, getInitials, getWhatsAppLink, cn } from '@/lib/utils';

// Usuario form modal
interface UsuarioFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    usuario?: Usuario | null;
    tiposCuota: TipoCuota[];
    onSuccess: () => void;
}

function UsuarioFormModal({ isOpen, onClose, usuario, tiposCuota, onSuccess }: UsuarioFormModalProps) {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<UsuarioCreateInput>({
        nombre: '',
        dni: '',
        telefono: '',
        email: '',
        tipo_cuota_id: undefined,
        activo: true,
        notas: '',
    });
    const { success, error } = useToast();

    // Reset form when opening/closing
    useEffect(() => {
        if (isOpen) {
            if (usuario) {
                setFormData({
                    nombre: usuario.nombre || '',
                    dni: usuario.dni || '',
                    telefono: usuario.telefono || '',
                    email: usuario.email || '',
                    tipo_cuota_id: usuario.tipo_cuota_id,
                    activo: usuario.activo ?? true,
                    notas: usuario.notas || '',
                });
            } else {
                setFormData({
                    nombre: '',
                    dni: '',
                    telefono: '',
                    email: '',
                    tipo_cuota_id: undefined,
                    activo: true,
                    notas: '',
                });
            }
        }
    }, [isOpen, usuario]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.nombre.trim()) {
            error('El nombre es requerido');
            return;
        }

        setLoading(true);
        try {
            // Validate DNI uniqueness before submitting
            if (formData.dni?.trim()) {
                const dniCheck = await api.checkDniAvailable(
                    formData.dni.trim(),
                    usuario?.id // Exclude current user when editing
                );
                if (dniCheck.ok && dniCheck.data && !dniCheck.data.available) {
                    error(`El DNI ya está en uso por: ${dniCheck.data.user_name || 'otro usuario'}`);
                    setLoading(false);
                    return;
                }
            }

            if (usuario) {
                const res = await api.updateUsuario(usuario.id, formData);
                if (res.ok) {
                    success('Usuario actualizado');
                    onSuccess();
                    onClose();
                } else {
                    error(res.error || 'Error al actualizar');
                }
            } else {
                const res = await api.createUsuario(formData);
                if (res.ok) {
                    success('Usuario creado');
                    onSuccess();
                    onClose();
                } else {
                    error(res.error || 'Error al crear');
                }
            }
        } catch {
            error('Error de conexión');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={usuario ? 'Editar Usuario' : 'Nuevo Usuario'}
            size="lg"
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSubmit} isLoading={loading}>
                        {usuario ? 'Guardar Cambios' : 'Crear Usuario'}
                    </Button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                        label="Nombre completo"
                        value={formData.nombre}
                        onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                        placeholder="Juan Pérez"
                        required
                    />
                    <Input
                        label="DNI"
                        value={formData.dni || ''}
                        onChange={(e) => setFormData({ ...formData, dni: e.target.value })}
                        placeholder="12345678"
                    />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                        label="Teléfono"
                        value={formData.telefono || ''}
                        onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                        placeholder="3434567890"
                        leftIcon={<Phone className="w-4 h-4" />}
                    />
                    <Input
                        label="Email"
                        type="email"
                        value={formData.email || ''}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        placeholder="juan@email.com"
                        leftIcon={<Mail className="w-4 h-4" />}
                    />
                </div>
                <Select
                    label="Tipo de Cuota"
                    value={formData.tipo_cuota_id?.toString() || ''}
                    onChange={(e) => setFormData({ ...formData, tipo_cuota_id: e.target.value ? Number(e.target.value) : undefined })}
                    placeholder="Seleccionar tipo de cuota"
                    options={tiposCuota.map((tc) => ({
                        value: tc.id.toString(),
                        label: tc.nombre,
                    }))}
                />
                <Textarea
                    label="Notas"
                    value={formData.notas || ''}
                    onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                    placeholder="Notas adicionales sobre el usuario..."
                />
                <Checkbox
                    label="Usuario activo"
                    checked={formData.activo}
                    onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                />
            </form>
        </Modal>
    );
}

export default function UsuariosPage() {
    const router = useRouter();
    const { success, error } = useToast();

    // State
    const [usuarios, setUsuarios] = useState<Usuario[]>([]);
    const [loading, setLoading] = useState(true);
    const [asistenciasHoyIds, setAsistenciasHoyIds] = useState<Set<number>>(new Set());
    const [search, setSearch] = useState('');
    const [filterActivo, setFilterActivo] = useState<boolean | undefined>(undefined);
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const pageSize = 25;

    // Modals
    const [formModalOpen, setFormModalOpen] = useState(false);
    const [selectedUsuario, setSelectedUsuario] = useState<Usuario | null>(null);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [usuarioToDelete, setUsuarioToDelete] = useState<Usuario | null>(null);
    const [toggleModalOpen, setToggleModalOpen] = useState(false);
    const [usuarioToToggle, setUsuarioToToggle] = useState<Usuario | null>(null);

    // Config data
    const [tiposCuota, setTiposCuota] = useState<TipoCuota[]>([]);

    // Sidebar
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [sidebarUsuario, setSidebarUsuario] = useState<Usuario | null>(null);

    // Load usuarios
    const loadUsuarios = useCallback(async () => {
        setLoading(true);
        try {
            const [res, hoyRes] = await Promise.all([
                api.getUsuarios({
                    search: search || undefined,
                    activo: filterActivo,
                    page,
                    limit: pageSize,
                }),
                api.getAsistenciasHoyIds().catch(() => ({ ok: false } as any)),
            ]);
            if (res.ok && res.data) {
                setUsuarios(res.data.usuarios);
                setTotal(res.data.total);
            }
            if (hoyRes && (hoyRes as any).ok && Array.isArray((hoyRes as any).data)) {
                setAsistenciasHoyIds(new Set<number>((hoyRes as any).data as number[]));
            }
        } catch {
            error('Error al cargar usuarios');
        } finally {
            setLoading(false);
        }
    }, [search, filterActivo, page, error]);

    // Load config
    useEffect(() => {
        (async () => {
            const res = await api.getTiposCuota();
            if (res.ok && res.data) {
                setTiposCuota(res.data.tipos);
            }
        })();
    }, []);

    // Reload on filters change
    useEffect(() => {
        loadUsuarios();
    }, [loadUsuarios]);

    // Handle delete
    const handleDelete = async () => {
        if (!usuarioToDelete) return;
        try {
            const res = await api.deleteUsuario(usuarioToDelete.id);
            if (res.ok) {
                success('Usuario eliminado');
                loadUsuarios();
            } else {
                error(res.error || 'Error al eliminar');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setDeleteModalOpen(false);
            setUsuarioToDelete(null);
        }
    };

    // Handle toggle activo - now with confirmation modal
    const confirmToggleActivo = (usuario: Usuario) => {
        setUsuarioToToggle(usuario);
        setToggleModalOpen(true);
    };

    const handleToggleActivo = async () => {
        if (!usuarioToToggle) return;
        try {
            const res = await api.toggleUsuarioActivo(usuarioToToggle.id);
            if (res.ok) {
                success(`Usuario ${res.data?.activo ? 'activado' : 'desactivado'}`);
                loadUsuarios();
            } else {
                error(res.error || 'Error al cambiar estado');
            }
        } catch {
            error('Error de conexión');
        } finally {
            setToggleModalOpen(false);
            setUsuarioToToggle(null);
        }
    };

    // Table columns
    const columns: Column<Usuario>[] = [
        {
            key: 'nombre',
            header: 'Usuario',
            sortable: true,
            render: (row) => (
                <div className="flex items-center gap-3">
                    <div
                        className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium"
                        style={{ backgroundColor: `hsl(${row.id * 37 % 360}, 60%, 35%)` }}
                    >
                        {getInitials(row.nombre)}
                    </div>
                    <div>
                        <div className="font-medium text-white flex items-center gap-2">
                            <span className="truncate">{row.nombre}</span>
                            {asistenciasHoyIds.has(row.id) && (
                                <span
                                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-success-500/15 text-success-300 border border-success-500/20"
                                    title="Asistió hoy"
                                >
                                    <CheckCircle2 className="w-3 h-3" />
                                    Hoy
                                </span>
                            )}
                        </div>
                        {row.dni && <div className="text-xs text-slate-500">DNI: {row.dni}</div>}
                    </div>
                </div>
            ),
        },
        {
            key: 'telefono',
            header: 'Contacto',
            render: (row) => (
                <div className="space-y-1">
                    {row.telefono && (
                        <a
                            href={getWhatsAppLink(row.telefono)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-sm text-primary-400 hover:text-primary-300"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <Phone className="w-3 h-3" />
                            {row.telefono}
                        </a>
                    )}
                    {row.email && (
                        <a
                            href={`mailto:${row.email}`}
                            className="flex items-center gap-1 text-sm text-slate-400 hover:text-white"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <Mail className="w-3 h-3" />
                            {row.email}
                        </a>
                    )}
                    {!row.telefono && !row.email && <span className="text-slate-600">-</span>}
                </div>
            ),
        },
        {
            key: 'tipo_cuota_nombre',
            header: 'Cuota',
            sortable: true,
            render: (row) => (
                <span className="text-sm">
                    {row.tipo_cuota_nombre || <span className="text-slate-600">Sin asignar</span>}
                </span>
            ),
        },
        {
            key: 'fecha_proximo_vencimiento',
            header: 'Vencimiento',
            sortable: true,
            render: (row) => {
                if (!row.fecha_proximo_vencimiento) {
                    return <span className="text-slate-600">-</span>;
                }
                const days = row.dias_restantes ?? 0;
                const isExpired = days <= 0;
                const isExpiringSoon = days > 0 && days <= 7;

                return (
                    <div>
                        <div className={cn(
                            'text-sm font-medium',
                            isExpired ? 'text-danger-400' : isExpiringSoon ? 'text-warning-400' : 'text-success-400'
                        )}>
                            {formatDateRelative(row.fecha_proximo_vencimiento)}
                        </div>
                        <div className="text-xs text-slate-500">
                            {formatDate(row.fecha_proximo_vencimiento)}
                        </div>
                    </div>
                );
            },
        },
        {
            key: 'activo',
            header: 'Estado',
            sortable: true,
            render: (row) => (
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        confirmToggleActivo(row);
                    }}
                    className={cn(
                        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors',
                        row.activo
                            ? 'bg-success-500/20 text-success-400 hover:bg-success-500/30'
                            : 'bg-danger-500/20 text-danger-400 hover:bg-danger-500/30'
                    )}
                >
                    {row.activo ? (
                        <>
                            <CheckCircle2 className="w-3 h-3" />
                            Activo
                        </>
                    ) : (
                        <>
                            <XCircle className="w-3 h-3" />
                            Inactivo
                        </>
                    )}
                </button>
            ),
        },
        {
            key: 'actions',
            header: '',
            width: '100px',
            align: 'right',
            render: (row) => (
                <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                        onClick={() => {
                            setSelectedUsuario(row);
                            setFormModalOpen(true);
                        }}
                        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                        title="Editar"
                    >
                        <Edit className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => {
                            setUsuarioToDelete(row);
                            setDeleteModalOpen(true);
                        }}
                        className="p-2 rounded-lg text-slate-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors"
                        title="Eliminar"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            ),
        },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
            >
                <div>
                    <h1 className="text-2xl font-display font-bold text-white">Usuarios</h1>
                    <p className="text-slate-400 mt-1">
                        Gestiona los socios del gimnasio
                    </p>
                </div>
                <Button
                    leftIcon={<UserPlus className="w-4 h-4" />}
                    onClick={() => {
                        setSelectedUsuario(null);
                        setFormModalOpen(true);
                    }}
                >
                    Nuevo Usuario
                </Button>
            </motion.div>

            {/* Filters */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="card p-4"
            >
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
                    <div className="flex-1">
                        <SearchInput
                            placeholder="Buscar por nombre, DNI, teléfono..."
                            value={search}
                            onChange={(e) => {
                                setSearch(e.target.value);
                                setPage(1);
                            }}
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <Select
                            value={filterActivo === undefined ? '' : filterActivo ? 'true' : 'false'}
                            onChange={(e) => {
                                setFilterActivo(e.target.value === '' ? undefined : e.target.value === 'true');
                                setPage(1);
                            }}
                            options={[
                                { value: '', label: 'Todos los estados' },
                                { value: 'true', label: 'Solo activos' },
                                { value: 'false', label: 'Solo inactivos' },
                            ]}
                        />
                        <Button
                            variant="ghost"
                            onClick={loadUsuarios}
                            title="Recargar"
                        >
                            <RefreshCw className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </motion.div>

            {/* Table */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
            >
                <DataTable
                    data={usuarios}
                    columns={columns}
                    loading={loading}
                    emptyMessage="No se encontraron usuarios"
                    onRowClick={async (row) => {
                        try {
                            const full = await api.getUsuario(row.id);
                            setSidebarUsuario((full.ok && full.data) ? full.data : row);
                        } catch {
                            setSidebarUsuario(row);
                        }
                        setSidebarOpen(true);
                    }}
                    pagination={{
                        page,
                        pageSize,
                        total,
                        onPageChange: setPage,
                    }}
                />
            </motion.div>

            {/* Form Modal */}
            <UsuarioFormModal
                isOpen={formModalOpen}
                onClose={() => {
                    setFormModalOpen(false);
                    setSelectedUsuario(null);
                }}
                usuario={selectedUsuario}
                tiposCuota={tiposCuota}
                onSuccess={loadUsuarios}
            />

            {/* Delete Confirm Modal */}
            <ConfirmModal
                isOpen={deleteModalOpen}
                onClose={() => {
                    setDeleteModalOpen(false);
                    setUsuarioToDelete(null);
                }}
                onConfirm={handleDelete}
                title="Eliminar Usuario"
                message={`¿Estás seguro de eliminar a "${usuarioToDelete?.nombre}"? Esta acción no se puede deshacer.`}
                confirmText="Eliminar"
                variant="danger"
            />

            {/* Toggle Active Confirm Modal */}
            <ConfirmModal
                isOpen={toggleModalOpen}
                onClose={() => {
                    setToggleModalOpen(false);
                    setUsuarioToToggle(null);
                }}
                onConfirm={handleToggleActivo}
                title={usuarioToToggle?.activo ? "Desactivar Usuario" : "Activar Usuario"}
                message={usuarioToToggle?.activo
                    ? `¿Estás seguro de desactivar a "${usuarioToToggle?.nombre}"? No podrá acceder al sistema ni registrar check-ins.`
                    : `¿Activar a "${usuarioToToggle?.nombre}"? Podrá acceder al sistema y registrar check-ins.`
                }
                confirmText={usuarioToToggle?.activo ? "Desactivar" : "Activar"}
                variant={usuarioToToggle?.activo ? "danger" : "info"}
            />

            {/* User Sidebar */}
            <AnimatePresence>
                {sidebarOpen && (
                    <UserSidebar
                        usuario={sidebarUsuario}
                        isOpen={sidebarOpen}
                        onClose={() => {
                            setSidebarOpen(false);
                            setSidebarUsuario(null);
                        }}
                        onEdit={(u) => {
                            setSelectedUsuario(u);
                            setFormModalOpen(true);
                            setSidebarOpen(false);
                        }}
                        onDelete={(u) => {
                            setUsuarioToDelete(u);
                            setDeleteModalOpen(true);
                            setSidebarOpen(false);
                        }}
                        onToggleActivo={(u) => {
                            confirmToggleActivo(u);
                        }}
                        onRefresh={loadUsuarios}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}


