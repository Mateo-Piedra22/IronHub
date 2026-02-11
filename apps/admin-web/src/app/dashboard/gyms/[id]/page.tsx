'use client';

import { useState, useEffect, use, useMemo, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Loader2, ArrowLeft, MessageSquare, Wrench, Palette, CreditCard,
    Key, Activity, FileText, Save, Send, Check, X, AlertCircle, Upload, Trash2, MapPin, Plus, Pencil, ListChecks
} from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { api, type Gym, type WhatsAppConfig, type Payment, type WhatsAppTemplateCatalogItem, type FeatureFlags, type GymBranch, type GymTipoClaseItem, type GymTipoCuotaItem, type TipoCuotaEntitlementsUpdate, type GymBranchCreateInput, type GymBranchUpdateInput, type GymOnboardingStatus, type TenantMigrationStatus, type TenantRoutineTemplate, type TenantRoutineTemplateAssignment } from '@/lib/api';

type Section = 'onboarding' | 'subscription' | 'branches' | 'payments' | 'whatsapp' | 'maintenance' | 'attendance' | 'modules' | 'routine_templates' | 'entitlements' | 'branding' | 'health' | 'password';

const BRANCH_CODE_RE = /^[a-z0-9][a-z0-9_-]{1,39}$/;
const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;

interface BrandingConfig {
    nombre_publico: string;
    direccion: string;
    logo_url: string;
    color_primario: string;
    color_secundario: string;
    color_fondo: string;
    color_texto: string;
    portal_tagline: string;
    footer_text: string;
    show_powered_by: boolean;
    support_whatsapp_enabled: boolean;
    support_whatsapp: string;
    support_email_enabled: boolean;
    support_email: string;
    support_url_enabled: boolean;
    support_url: string;
    portal_enable_checkin: boolean;
    portal_enable_member: boolean;
    portal_enable_staff: boolean;
    portal_enable_owner: boolean;
}

interface AdminPlan {
    id: number;
    name: string;
    amount: number;
    currency?: string;
    period_days?: number;
}

type AuditItem = Record<string, unknown>;

export default function GymDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params);
    const gymId = Number(resolvedParams.id);

    const [gym, setGym] = useState<Gym | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeSection, setActiveSection] = useState<Section>('onboarding');
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [onboarding, setOnboarding] = useState<GymOnboardingStatus | null>(null);
    const [onboardingLoading, setOnboardingLoading] = useState(false);
    const [prodReadySaving, setProdReadySaving] = useState(false);
    const [tenantMigration, setTenantMigration] = useState<TenantMigrationStatus | null>(null);
    const [tenantMigrationLoading, setTenantMigrationLoading] = useState(false);
    const [tenantProvisioning, setTenantProvisioning] = useState(false);
    const [routineTemplatesLoading, setRoutineTemplatesLoading] = useState(false);
    const [routineTemplatesCatalog, setRoutineTemplatesCatalog] = useState<TenantRoutineTemplate[]>([]);
    const [routineTemplateAssignments, setRoutineTemplateAssignments] = useState<TenantRoutineTemplateAssignment[]>([]);
    const [assignTemplateId, setAssignTemplateId] = useState<number>(0);
    const [assignTemplatePriority, setAssignTemplatePriority] = useState<number>(0);
    const [assignTemplateNotes, setAssignTemplateNotes] = useState<string>('');
    const [assignTemplateActive, setAssignTemplateActive] = useState<boolean>(true);
    const normalizeBranchCode = (v: string) =>
        String(v || '')
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9_-]/g, '')
            .slice(0, 40);

    // Plans & Subscription Manual Assignment
    const [plans, setPlans] = useState<AdminPlan[]>([]);
    const [assignSubOpen, setAssignSubOpen] = useState(false);
    const [assignSubParams, setAssignSubParams] = useState({ plan_id: 0, start_date: '', end_date: '' });
    const [assignSubLoading, setAssignSubLoading] = useState(false);

    // WhatsApp form
    const [waConfig, setWaConfig] = useState<WhatsAppConfig>({});

    // Password form
    const [newPassword, setNewPassword] = useState('');

    // Maintenance form
    const [maintMessage, setMaintMessage] = useState('');
    const [maintUntil, setMaintUntil] = useState('');

    // Reminder
    const [reminderMessage, setReminderMessage] = useState('');
    const [webappReminderMessage, setWebappReminderMessage] = useState('');
    const [attendanceAllowMultiple, setAttendanceAllowMultiple] = useState(false);
    const [attendancePolicyLoading, setAttendancePolicyLoading] = useState(false);
    const [attendancePolicySaving, setAttendancePolicySaving] = useState(false);
    const [auditItems, setAuditItems] = useState<AuditItem[]>([]);
    const [auditLoading, setAuditLoading] = useState(false);

    const [branches, setBranches] = useState<GymBranch[]>([]);
    const [branchSaving, setBranchSaving] = useState(false);
    const [branchCreateOpen, setBranchCreateOpen] = useState(false);
    const [branchEditOpen, setBranchEditOpen] = useState(false);
    const [branchBulkOpen, setBranchBulkOpen] = useState(false);
    const [branchConfirm, setBranchConfirm] = useState<GymBranch | null>(null);
    const [branchSyncing, setBranchSyncing] = useState(false);
    const [bulkText, setBulkText] = useState('');
    const [bulkItems, setBulkItems] = useState<GymBranchCreateInput[]>([]);
    const [bulkSubmitting, setBulkSubmitting] = useState(false);
    const [branchDraft, setBranchDraft] = useState<GymBranchCreateInput>({
        name: '',
        code: '',
        address: '',
        timezone: '',
    });
    const [editingBranchId, setEditingBranchId] = useState<number>(0);
    const [editBranchDraft, setEditBranchDraft] = useState<GymBranchUpdateInput>({
        name: '',
        code: '',
        address: '',
        timezone: '',
        status: 'active',
    });
    const branchDraftCodeNorm = useMemo(
        () => normalizeBranchCode(String(branchDraft.code || '')),
        [branchDraft.code]
    );
    const branchDraftCodeError = useMemo(() => {
        const nameOk = String(branchDraft.name || '').trim().length > 0;
        const codeRaw = String(branchDraft.code || '').trim();
        if (!nameOk || !codeRaw) return '';
        if (!BRANCH_CODE_RE.test(branchDraftCodeNorm)) return 'Formato inválido (2-40, minúsculas, números, _ o -)';
        const exists = branches.some(
            (b) => String(b.code || '').toLowerCase() === branchDraftCodeNorm.toLowerCase()
        );
        if (exists) return 'El código ya existe';
        return '';
    }, [branchDraft.name, branchDraft.code, branchDraftCodeNorm, branches]);
    const [featureFlagsScope, setFeatureFlagsScope] = useState<'gym' | 'branch'>('gym');
    const [featureFlagsBranchId, setFeatureFlagsBranchId] = useState<number>(0);
    const [featureFlags, setFeatureFlags] = useState<FeatureFlags>({ modules: {} });
    const [featureFlagsLoading, setFeatureFlagsLoading] = useState(false);
    const [featureFlagsSaving, setFeatureFlagsSaving] = useState(false);

    const [entTiposCuota, setEntTiposCuota] = useState<GymTipoCuotaItem[]>([]);
    const [entTiposClases, setEntTiposClases] = useState<GymTipoClaseItem[]>([]);
    const [entTipoCuotaId, setEntTipoCuotaId] = useState<number>(0);
    const [entLoading, setEntLoading] = useState(false);
    const [entSaving, setEntSaving] = useState(false);
    const [entAllSucursales, setEntAllSucursales] = useState(true);
    const [entSelectedSucursales, setEntSelectedSucursales] = useState<number[]>([]);
    const [entScopeKey, setEntScopeKey] = useState<string>('0');
    const [entRulesByScope, setEntRulesByScope] = useState<Record<string, number[]>>({});

    // WhatsApp test
    const [waTestPhone, setWaTestPhone] = useState('');
    const [waTestMessage, setWaTestMessage] = useState('Mensaje de prueba');
    const [provisioningTemplates, setProvisioningTemplates] = useState(false);
    const [provisionTemplatesMsg, setProvisionTemplatesMsg] = useState('');
    const [waHealthLoading, setWaHealthLoading] = useState(false);
    const [waHealthMsg, setWaHealthMsg] = useState('');
    const [waActionsLoading, setWaActionsLoading] = useState(false);
    const [waActions, setWaActions] = useState<
        Array<{
            action_key: string;
            enabled: boolean;
            template_name: string;
            required_params: number;
            default_enabled?: boolean;
            default_template_name?: string;
        }>
    >([]);
    const [waCatalog, setWaCatalog] = useState<WhatsAppTemplateCatalogItem[]>([]);
    const [waMetaTemplates, setWaMetaTemplates] = useState<Array<{ name: string; status: string; category: string; language: string }>>([]);
    const [savingWaAction, setSavingWaAction] = useState<string>('');
    const [savingAllWaActions, setSavingAllWaActions] = useState(false);
    const [waEventsLoading, setWaEventsLoading] = useState(false);
    const [waEvents, setWaEvents] = useState<Array<{ event_type: string; severity: string; message: string; details: unknown; created_at: string }>>([]);

    // Payment form
    const [paymentAmount, setPaymentAmount] = useState('');
    const [paymentPlanId, setPaymentPlanId] = useState<number | ''>(''); // Changed to planId
    const [paymentPlanName, setPaymentPlanName] = useState(''); // Keep name for custom or fallback
    const [paymentValidUntil, setPaymentValidUntil] = useState('');

    // Payments
    const [payments, setPayments] = useState<Payment[]>([]);

    // Branding
    const [branding, setBranding] = useState<BrandingConfig>({
        nombre_publico: '',
        direccion: '',
        logo_url: '',
        color_primario: '#6366f1',
        color_secundario: '#22c55e',
        color_fondo: '#0a0a0a',
        color_texto: '#ffffff',
        portal_tagline: '',
        footer_text: '',
        show_powered_by: true,
        support_whatsapp_enabled: false,
        support_whatsapp: '',
        support_email_enabled: false,
        support_email: '',
        support_url_enabled: false,
        support_url: '',
        portal_enable_checkin: true,
        portal_enable_member: true,
        portal_enable_staff: true,
        portal_enable_owner: true,
    });
    const [uploading, setUploading] = useState(false);
    const logoInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        async function load() {
            setLoading(true);
            try {
                // Fetch Plans
                try {
                    const pRes = await api.getAdminPlans();
                    if (pRes.ok && pRes.data?.plans) {
                        setPlans(pRes.data.plans as AdminPlan[]);
                    }
                } catch { }

                const res = await api.getGym(gymId);
                if (res.ok && res.data) {
                    setGym(res.data);
                    setWaConfig({
                        phone_id: res.data.whatsapp_phone_id || '',
                        access_token: res.data.whatsapp_access_token || '',
                        business_account_id: res.data.whatsapp_business_account_id || '',
                        verify_token: res.data.whatsapp_verify_token || '',
                        app_secret: res.data.whatsapp_app_secret || '',
                        nonblocking: Boolean(res.data.whatsapp_nonblocking || false),
                        send_timeout_seconds: res.data.whatsapp_send_timeout_seconds ? Number(res.data.whatsapp_send_timeout_seconds) : 25,
                    });
                    if (res.data.status === 'maintenance') {
                        setMaintMessage(String(res.data.suspended_reason || ''));
                        setMaintUntil(res.data.suspended_until ? String(res.data.suspended_until).slice(0, 16) : '');
                    }
                }
                setTenantMigrationLoading(true);
                try {
                    const ms = await api.getGymTenantMigrationStatus(gymId);
                    if (ms.ok && ms.data) setTenantMigration(ms.data);
                } finally {
                    setTenantMigrationLoading(false);
                }
                const payRes = await api.getGymPayments(gymId);
                if (payRes.ok && payRes.data) {
                    setPayments(payRes.data.payments || []);
                }
                const reminderRes = await api.getGymReminderMessage(gymId);
                if (reminderRes.ok && reminderRes.data) {
                    setWebappReminderMessage(reminderRes.data.message || '');
                }
                const policyRes = await api.getGymAttendancePolicy(gymId);
                if (policyRes.ok && policyRes.data?.ok) {
                    setAttendanceAllowMultiple(Boolean(policyRes.data.attendance_allow_multiple_per_day));
                }
                const auditRes = await api.getGymAudit(gymId, 80);
                if (auditRes.ok && auditRes.data?.ok) {
                    setAuditItems((auditRes.data.items || []) as AuditItem[]);
                }
                const brRes = await api.listGymBranches(gymId);
                if (brRes.ok && brRes.data?.ok) {
                    setBranches(brRes.data.items || []);
                }
                try {
                    const obRes = await api.getGymOnboardingStatus(gymId);
                    if (obRes.ok && obRes.data?.ok) {
                        setOnboarding(obRes.data);
                    }
                } catch {
                }
                setFeatureFlagsLoading(true);
                try {
                    const ffRes = await api.getGymFeatureFlags(gymId, { scope: 'gym' });
                    if (ffRes.ok && ffRes.data?.ok && ffRes.data.flags) {
                        setFeatureFlags(ffRes.data.flags);
                        setFeatureFlagsScope('gym');
                        setFeatureFlagsBranchId(0);
                    }
                } finally {
                    setFeatureFlagsLoading(false);
                }
                const tcRes = await api.listGymTiposCuota(gymId);
                if (tcRes.ok && tcRes.data?.ok) {
                    const items = (tcRes.data.items || []) as GymTipoCuotaItem[];
                    setEntTiposCuota(items);
                    const first = items.find((x) => x && (x as GymTipoCuotaItem).activo)?.id || items[0]?.id || 0;
                    if (first) setEntTipoCuotaId(Number(first));
                }
                const tclRes = await api.listGymTiposClases(gymId);
                if (tclRes.ok && tclRes.data?.ok) {
                    setEntTiposClases((tclRes.data.items || []) as GymTipoClaseItem[]);
                }
                // Load branding
                const brandRes = await api.getGymBranding(gymId);
                if (brandRes.ok && brandRes.data?.branding) {
                    setBranding(prev => ({
                        ...prev,
                        ...brandRes.data!.branding
                    }));
                }
                const tplRes = await api.getWhatsAppTemplateCatalog(false);
                if (tplRes.ok && tplRes.data) {
                    setWaCatalog(tplRes.data.templates || []);
                }
                setWaEventsLoading(true);
                const evRes = await api.getGymWhatsAppOnboardingEvents(gymId, 20);
                if (evRes.ok && evRes.data) {
                    setWaEvents(evRes.data.events || []);
                }
                setWaActionsLoading(true);
                const actRes = await api.getGymWhatsAppActions(gymId);
                if (actRes.ok && actRes.data) {
                    setWaActions(actRes.data.actions || []);
                }
                try {
                    const hRes = await api.getGymWhatsAppHealth(gymId);
                    if (hRes.ok && isRecord(hRes.data) && Array.isArray(hRes.data.templates_list)) {
                        const mapped = hRes.data.templates_list
                            .map((t) => {
                                if (!isRecord(t)) return null;
                                const name = String(t.name || '').trim();
                                if (!name) return null;
                                return {
                                    name,
                                    status: String(t.status || ''),
                                    category: String(t.category || ''),
                                    language: String(t.language || ''),
                                };
                            })
                            .filter(Boolean) as Array<{ name: string; status: string; category: string; language: string }>;
                        setWaMetaTemplates(mapped);
                    }
                } catch {
                    // Ignore
                }
            } catch {
                // Ignore
            } finally {
                setWaEventsLoading(false);
                setWaActionsLoading(false);
                setLoading(false);
            }
        }
        load();
    }, [gymId]);

    async function refreshTenantMigration() {
        setTenantMigrationLoading(true);
        try {
            const ms = await api.getGymTenantMigrationStatus(gymId);
            if (ms.ok && ms.data) setTenantMigration(ms.data);
        } finally {
            setTenantMigrationLoading(false);
        }
    }

    async function provisionTenantNow() {
        setTenantProvisioning(true);
        try {
            const pr = await api.provisionGymTenantMigrations(gymId);
            if (pr.ok && pr.data?.ok) {
                const st = pr.data.status;
                if (st) setTenantMigration(st);
                setMessage('Migraciones aplicadas');
                setTimeout(() => setMessage(''), 3000);
            } else {
                setMessage(`Error al migrar: ${pr.error || pr.data?.error || 'unknown'}`);
                setTimeout(() => setMessage(''), 5000);
            }
        } finally {
            setTenantProvisioning(false);
        }
    }

    const refresh = async () => {
        setLoading(true);
        try {
            const res = await api.getGym(gymId);
            if (res.ok && res.data) {
                setGym(res.data);
            }
            const payRes = await api.getGymPayments(gymId);
            if (payRes.ok && payRes.data) {
                setPayments(payRes.data.payments || []);
            }
            try {
                await reloadBranches();
            } catch {
            }
            try {
                await reloadOnboarding();
            } catch {
            }
        } catch {
            // Ignore
        } finally {
            setLoading(false);
        }
    };

    const handleSaveWebappReminder = async () => {
        setSaving(true);
        try {
            const res = await api.setGymReminderMessage(gymId, webappReminderMessage);
            if (res.ok) {
                showMessage('Recordatorio guardado');
            } else {
                showMessage(res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const showMessage = (msg: string) => {
        setMessage(msg);
        setTimeout(() => setMessage(''), 3000);
    };

    const reloadOnboarding = async () => {
        setOnboardingLoading(true);
        try {
            const res = await api.getGymOnboardingStatus(gymId);
            if (res.ok && res.data?.ok) {
                setOnboarding(res.data);
            }
        } catch {
        } finally {
            setOnboardingLoading(false);
        }
    };

    const reloadRoutineTemplates = useCallback(async () => {
        setRoutineTemplatesLoading(true);
        try {
            const [catRes, asgRes] = await Promise.all([
                api.getGymRoutineTemplateCatalog(gymId),
                api.getGymRoutineTemplateAssignments(gymId),
            ]);
            if (catRes.ok && catRes.data?.ok) {
                setRoutineTemplatesCatalog(catRes.data.templates || []);
            }
            if (asgRes.ok && asgRes.data?.ok) {
                setRoutineTemplateAssignments(asgRes.data.assignments || []);
            }
        } finally {
            setRoutineTemplatesLoading(false);
        }
    }, [gymId]);

    const setProductionReady = async (ready: boolean) => {
        setProdReadySaving(true);
        try {
            const res = await api.setGymProductionReady(gymId, ready);
            if (res.ok && res.data?.ok) {
                showMessage(ready ? 'Marcado como listo para producción' : 'Desmarcado');
                await reloadOnboarding();
            } else {
                showMessage(res.data?.error || res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setProdReadySaving(false);
        }
    };

    const reloadBranches = async () => {
        try {
            const brRes = await api.listGymBranches(gymId);
            if (brRes.ok && brRes.data?.ok) {
                setBranches(brRes.data.items || []);
            }
        } catch {
        }
    };

    const startEditBranch = (b: GymBranch) => {
        setEditingBranchId(Number(b.id) || 0);
        setEditBranchDraft({
            name: String(b.name || ''),
            code: String(b.code || ''),
            address: b.address ?? '',
            timezone: b.timezone ?? '',
            status: (String(b.status || '').toLowerCase() === 'inactive') ? 'inactive' : 'active',
        });
        setBranchEditOpen(true);
    };

    const cancelEditBranch = () => {
        setEditingBranchId(0);
        setEditBranchDraft({
            name: '',
            code: '',
            address: '',
            timezone: '',
            status: 'active',
        });
        setBranchEditOpen(false);
    };

    const openCreateBranch = () => {
        setBranchDraft({
            name: '',
            code: '',
            address: '',
            timezone: 'America/Argentina/Buenos_Aires',
        });
        setBranchCreateOpen(true);
    };

    const createBranch = async () => {
        setBranchSaving(true);
        try {
            const codeNorm = normalizeBranchCode(String(branchDraft.code || ''));
            if (!BRANCH_CODE_RE.test(codeNorm)) {
                showMessage('Código inválido (min 2, max 40; minúsculas/números/_/-)');
                return;
            }
            if (branches.some((b) => String(b.code || '').toLowerCase() === codeNorm.toLowerCase())) {
                showMessage('El código ya existe');
                return;
            }
            const payload: GymBranchCreateInput = {
                name: String(branchDraft.name || '').trim(),
                code: codeNorm,
                address: String(branchDraft.address || '').trim() ? String(branchDraft.address || '').trim() : null,
                timezone: String(branchDraft.timezone || '').trim() ? String(branchDraft.timezone || '').trim() : null,
            };
            const res = await api.createGymBranch(gymId, payload);
            if (res.ok && res.data?.ok) {
                showMessage('Sucursal creada');
                setBranchDraft({ name: '', code: '', address: '', timezone: '' });
                setBranchCreateOpen(false);
                await reloadBranches();
            } else {
                const err = res.data?.error || res.error || 'Error al crear sucursal';
                showMessage(err === 'code_already_exists' ? 'El código ya existe' : err);
            }
        } finally {
            setBranchSaving(false);
        }
    };

    const updateBranch = async () => {
        if (!editingBranchId) return;
        setBranchSaving(true);
        try {
            const payload: GymBranchUpdateInput = {
                name: editBranchDraft.name ? String(editBranchDraft.name).trim() : undefined,
                code: editBranchDraft.code ? String(editBranchDraft.code).trim() : undefined,
                address: editBranchDraft.address === null ? null : (String(editBranchDraft.address || '').trim() ? String(editBranchDraft.address || '').trim() : null),
                timezone: editBranchDraft.timezone === null ? null : (String(editBranchDraft.timezone || '').trim() ? String(editBranchDraft.timezone || '').trim() : null),
                status: editBranchDraft.status,
            };
            const res = await api.updateGymBranch(gymId, editingBranchId, payload);
            if (res.ok && res.data?.ok) {
                showMessage('Sucursal actualizada');
                cancelEditBranch();
                await reloadBranches();
            } else {
                const err = res.data?.error || res.error || 'Error al actualizar sucursal';
                if (err === 'cannot_delete_last_branch') {
                    showMessage('No se puede desactivar la última sucursal activa');
                } else {
                    showMessage(err === 'code_already_exists' ? 'El código ya existe' : err);
                }
            }
        } finally {
            setBranchSaving(false);
        }
    };

    const toggleBranchStatus = async (b: GymBranch) => {
        const next = String(b.status || '').toLowerCase() === 'inactive' ? 'active' : 'inactive';
        setBranchSaving(true);
        try {
            const res = await api.updateGymBranch(gymId, Number(b.id), { status: next as GymBranchUpdateInput['status'] });
            if (res.ok && res.data?.ok) {
                showMessage(next === 'active' ? 'Sucursal activada' : 'Sucursal desactivada');
                await reloadBranches();
            } else {
                const err = res.data?.error || res.error || 'Error';
                if (err === 'cannot_delete_last_branch') {
                    showMessage('No se puede desactivar la última sucursal activa');
                } else {
                    showMessage(err);
                }
            }
        } finally {
            setBranchSaving(false);
        }
    };

    const deleteBranch = async (b: GymBranch) => {
        setBranchConfirm(b);
    };

    const confirmDeleteBranch = async () => {
        if (!branchConfirm) return;
        setBranchSaving(true);
        try {
            const res = await api.deleteGymBranch(gymId, Number(branchConfirm.id));
            if (res.ok && res.data?.ok) {
                showMessage('Sucursal desactivada');
                setBranchConfirm(null);
                await reloadBranches();
            } else {
                const err = res.data?.error || res.error || 'Error';
                if (err === 'cannot_delete_last_branch') {
                    showMessage('No se puede desactivar la última sucursal activa');
                } else {
                    showMessage(err);
                }
            }
        } finally {
            setBranchSaving(false);
        }
    };

    const parseBulk = (raw: string) => {
        const lines = String(raw || '')
            .split(/\r?\n/g)
            .map((l) => l.trim())
            .filter((l) => l && !l.startsWith('#'));
        const items: GymBranchCreateInput[] = [];
        for (const line of lines) {
            const delim = line.includes('\t') ? '\t' : (line.includes(';') ? ';' : ',');
            const parts = line.split(delim).map((p) => p.trim());
            const name = parts[0] || '';
            const code = (parts[1] || '').toLowerCase().replace(/[^a-z0-9_-]/g, '');
            const timezone = parts[2] || '';
            const address = parts.slice(3).join(delim).trim();
            if (!name || !code) continue;
            items.push({
                name,
                code,
                timezone: timezone ? timezone : null,
                address: address ? address : null,
            });
        }
        setBulkItems(items);
    };

    const submitBulk = async () => {
        if (!bulkItems.length) return;
        setBulkSubmitting(true);
        try {
            const res = await api.bulkCreateGymBranches(gymId, bulkItems);
            if (res.ok && res.data?.ok) {
                showMessage(`Sucursales creadas: ${res.data.created} · Fallidas: ${res.data.failed}`);
                setBranchBulkOpen(false);
                setBulkText('');
                setBulkItems([]);
                await reloadBranches();
            } else {
                showMessage(res.data?.error || res.error || 'Error');
            }
        } finally {
            setBulkSubmitting(false);
        }
    };

    const syncBranches = async () => {
        setBranchSyncing(true);
        try {
            const res = await api.syncGymBranches(gymId);
            if (res.ok && res.data?.ok && Array.isArray(res.data.items)) {
                setBranches(res.data.items as GymBranch[]);
                showMessage('Sucursales sincronizadas');
            } else {
                showMessage(res.data?.error || res.error || 'Error');
            }
        } finally {
            setBranchSyncing(false);
        }
    };

    const loadFeatureFlags = async (scope: 'gym' | 'branch', branchId: number) => {
        setFeatureFlagsLoading(true);
        try {
            const res = await api.getGymFeatureFlags(gymId, { scope, branch_id: scope === 'branch' ? branchId : undefined });
            if (res.ok && res.data?.ok && res.data.flags) {
                setFeatureFlags(res.data.flags);
            }
        } finally {
            setFeatureFlagsLoading(false);
        }
    };

    const saveFeatureFlags = async () => {
        setFeatureFlagsSaving(true);
        try {
            const res = await api.setGymFeatureFlags(gymId, featureFlags, {
                scope: featureFlagsScope,
                branch_id: featureFlagsScope === 'branch' ? featureFlagsBranchId : undefined,
            });
            if (res.ok && res.data?.ok && res.data.flags) {
                setFeatureFlags(res.data.flags);
                showMessage('Módulos guardados');
            } else {
                showMessage(res.error || 'Error al guardar');
            }
        } finally {
            setFeatureFlagsSaving(false);
        }
    };

    const loadTipoCuotaEntitlements = useCallback(async (tipoCuotaId: number) => {
        if (!tipoCuotaId) return;
        setEntLoading(true);
        try {
            const res = await api.getGymTipoCuotaEntitlements(gymId, tipoCuotaId);
            if (res.ok && res.data?.ok && res.data.tipo_cuota) {
                setEntAllSucursales(Boolean(res.data.tipo_cuota.all_sucursales));
                setEntSelectedSucursales(Array.isArray(res.data.sucursal_ids) ? res.data.sucursal_ids : []);
                const map: Record<string, number[]> = {};
                const rules = Array.isArray(res.data.class_rules) ? res.data.class_rules : [];
                rules
                    .filter((r) => String(r.target_type || '').toLowerCase() === 'tipo_clase' && Boolean(r.allow))
                    .forEach((r) => {
                        const k = r.sucursal_id ? String(r.sucursal_id) : '0';
                        const arr = map[k] || [];
                        arr.push(Number(r.target_id));
                        map[k] = arr;
                    });
                Object.keys(map).forEach((k) => {
                    map[k] = Array.from(new Set(map[k].filter((x) => Number.isFinite(x)))).sort((a, b) => a - b);
                });
                setEntRulesByScope(map);
                setEntScopeKey('0');
            } else {
                setEntAllSucursales(true);
                setEntSelectedSucursales([]);
                setEntRulesByScope({});
                setEntScopeKey('0');
            }
        } finally {
            setEntLoading(false);
        }
    }, [gymId]);

    useEffect(() => {
        if (activeSection !== 'entitlements') return;
        if (!entTipoCuotaId) return;
        void loadTipoCuotaEntitlements(entTipoCuotaId);
    }, [activeSection, entTipoCuotaId, loadTipoCuotaEntitlements]);

    useEffect(() => {
        if (activeSection !== 'routine_templates') return;
        void reloadRoutineTemplates();
    }, [activeSection, reloadRoutineTemplates]);

    const saveTipoCuotaEntitlements = async () => {
        if (!entTipoCuotaId) return;
        setEntSaving(true);
        try {
            const class_rules: TipoCuotaEntitlementsUpdate['class_rules'] = [];
            Object.entries(entRulesByScope || {}).forEach(([k, ids]) => {
                const sidRaw = k === '0' ? null : Number(k);
                const sid = sidRaw !== null && Number.isFinite(sidRaw) ? sidRaw : null;
                (ids || []).forEach((id) => {
                    class_rules.push({ sucursal_id: sid, target_type: 'tipo_clase', target_id: Number(id), allow: true });
                });
            });
            const payload: TipoCuotaEntitlementsUpdate = {
                all_sucursales: Boolean(entAllSucursales),
                sucursal_ids: entAllSucursales ? [] : entSelectedSucursales,
                class_rules,
            };
            const res = await api.setGymTipoCuotaEntitlements(gymId, entTipoCuotaId, payload);
            if (res.ok && res.data?.ok) {
                showMessage('Accesos guardados');
                void loadTipoCuotaEntitlements(entTipoCuotaId);
            } else {
                showMessage(res.error || 'Error al guardar accesos');
            }
        } finally {
            setEntSaving(false);
        }
    };

    const countMetaParams = (bodyText: string) => {
        const matches = String(bodyText || '').match(/\{\{(\d+)\}\}/g) || [];
        const nums = matches
            .map((m) => {
                const n = m.replace(/[^\d]/g, '');
                return Number(n);
            })
            .filter((n) => Number.isFinite(n) && n > 0);
        return nums.length ? Math.max(...nums) : 0;
    };

    const splitTemplateVersion = (templateName: string) => {
        const s = String(templateName || '').trim();
        const m = s.match(/^(.+)_v(\d+)$/);
        if (!m || !m[1]) return { base: s, v: null as number | null };
        const base = String(m[1]);
        const vRaw = m[2];
        const v = vRaw ? Number(vRaw) : NaN;
        return { base, v: Number.isFinite(v) ? v : null };
    };

    const waMetaByName = useMemo(() => {
        const m = new Map<string, { name: string; status: string; category: string; language: string }>();
        for (const t of waMetaTemplates) {
            const n = String(t?.name || '').trim();
            if (!n) continue;
            m.set(n, {
                name: n,
                status: String(t?.status || ''),
                category: String(t?.category || ''),
                language: String(t?.language || ''),
            });
        }
        return m;
    }, [waMetaTemplates]);

    const waCatalogActiveByName = useMemo(() => {
        const m = new Map<string, WhatsAppTemplateCatalogItem>();
        for (const t of waCatalog || []) {
            const n = String(t?.template_name || '').trim();
            if (!n) continue;
            if (t?.active) {
                m.set(n, t);
            }
        }
        return m;
    }, [waCatalog]);

    const buildActionTemplateOptions = (action: { required_params: number; template_name: string; default_template_name?: string }) => {
        const required = Number(action?.required_params || 0);
        const catalogCandidates = (waCatalog || [])
            .filter((t) => Boolean(t?.active))
            .filter((t) => countMetaParams(String(t?.body_text || '')) === required)
            .map((t) => String(t?.template_name || '').trim())
            .filter(Boolean);

        const bases = new Set<string>();
        for (const n of catalogCandidates) {
            bases.add(splitTemplateVersion(n).base);
        }

        const metaCandidates = (waMetaTemplates || [])
            .map((t) => String(t?.name || '').trim())
            .filter(Boolean)
            .filter((n) => bases.has(splitTemplateVersion(n).base));

        const current = String(action?.template_name || '').trim();
        const fallback = String(action?.default_template_name || '').trim();

        const names = Array.from(new Set<string>([...catalogCandidates, ...metaCandidates, current, fallback].filter(Boolean)));

        const scored = names.map((name) => {
            const meta = waMetaByName.get(name);
            const status = String(meta?.status || '').toUpperCase();
            const inCatalog = waCatalogActiveByName.has(name);
            const isApproved = !status ? true : status === 'APPROVED';
            const disabled = !inCatalog || !isApproved;
            const notes = [
                !inCatalog ? 'NO_CATÁLOGO' : null,
                status && status !== 'APPROVED' ? `NO_APROBADO:${status}` : null,
            ]
                .filter(Boolean)
                .join(' · ');
            const extra = [
                status ? status : null,
                meta?.category ? String(meta.category).toUpperCase() : null,
                meta?.language ? String(meta.language) : null,
                notes ? notes : null,
            ]
                .filter(Boolean)
                .join(' · ');
            const label = extra ? `${name} — ${extra}` : name;
            const { base, v } = splitTemplateVersion(name);
            return { name, label, disabled, base, v: v ?? 0, status, inCatalog };
        });

        scored.sort((a, b) => {
            if (a.base !== b.base) return a.base.localeCompare(b.base);
            if (a.v !== b.v) return b.v - a.v;
            if (a.status !== b.status) {
                if (a.status === 'APPROVED') return -1;
                if (b.status === 'APPROVED') return 1;
            }
            return a.name.localeCompare(b.name);
        });

        return scored;
    };

    const actionLabel: Record<string, string> = {
        welcome: 'Bienvenida',
        payment: 'Confirmación de pago',
        membership_due_today: 'Cuota vence hoy',
        membership_due_soon: 'Cuota vence pronto',
        overdue: 'Cuota vencida',
        deactivation: 'Desactivación',
        membership_reactivated: 'Reactivación',
        class_booking_confirmed: 'Reserva confirmada',
        class_booking_cancelled: 'Reserva cancelada',
        class_reminder: 'Recordatorio de clase',
        waitlist: 'Cupo disponible (waitlist)',
        waitlist_confirmed: 'Confirmación waitlist',
        schedule_change: 'Cambio de horario',
        marketing_promo: 'Marketing promo',
        marketing_new_class: 'Marketing nueva clase',
    };

    const saveWaAction = async (actionKey: string) => {
        const item = waActions.find((a) => a.action_key === actionKey);
        if (!item) return;
        setSavingWaAction(actionKey);
        try {
            const res = await api.setGymWhatsAppAction(gymId, actionKey, Boolean(item.enabled), String(item.template_name || ''));
            if (res.ok) {
                showMessage('Acción WhatsApp guardada');
            } else {
                showMessage(res.error || 'Error');
            }
        } finally {
            setSavingWaAction('');
            try {
                setWaEventsLoading(true);
                const evRes = await api.getGymWhatsAppOnboardingEvents(gymId, 20);
                if (evRes.ok && evRes.data) {
                    setWaEvents(evRes.data.events || []);
                }
            } finally {
                setWaEventsLoading(false);
            }
        }
    };

    const autoPickWaActionTemplates = () => {
        setWaActions((prev) =>
            prev.map((a) => {
                const opts = buildActionTemplateOptions(a);
                const baseWanted = splitTemplateVersion(String(a.default_template_name || a.template_name || '')).base;
                const preferred = opts.filter((o) => !o.disabled && o.base === baseWanted);
                const fallback = opts.filter((o) => !o.disabled);
                const chosen = (preferred[0] || fallback[0])?.name;
                if (!chosen) return a;
                if (String(a.template_name || '').trim() === chosen) return a;
                return { ...a, template_name: chosen };
            })
        );
        showMessage('Auto-selección aplicada (solo APPROVED + activo en catálogo)');
    };

    const saveAllWaActions = async () => {
        if (savingAllWaActions) return;
        setSavingAllWaActions(true);
        const failed: Array<{ action_key: string; error: string }> = [];
        let saved = 0;
        try {
            for (const a of waActions) {
                try {
                    const res = await api.setGymWhatsAppAction(gymId, a.action_key, Boolean(a.enabled), String(a.template_name || ''));
                    if (res.ok) {
                        saved += 1;
                    } else {
                        failed.push({ action_key: a.action_key, error: res.error || 'Error' });
                    }
                } catch (e: unknown) {
                    const msg =
                        typeof e === 'object' && e !== null && 'message' in e
                            ? String((e as Record<string, unknown>).message || 'Error')
                            : 'Error';
                    failed.push({ action_key: a.action_key, error: msg });
                }
            }
        } finally {
            setSavingAllWaActions(false);
        }
        if (failed.length) {
            showMessage(`Guardado parcial: ok=${saved}, fallidos=${failed.length}`);
        } else {
            showMessage(`Guardado OK: ${saved} acciones`);
        }
        try {
            setWaEventsLoading(true);
            const evRes = await api.getGymWhatsAppOnboardingEvents(gymId, 20);
            if (evRes.ok && evRes.data) {
                setWaEvents(evRes.data.events || []);
            }
        } finally {
            setWaEventsLoading(false);
        }
    };

    const handleSaveWhatsApp = async () => {
        setSaving(true);
        try {
            const res = await api.updateGymWhatsApp(gymId, waConfig);
            if (res.ok) {
                showMessage('Configuración de WhatsApp guardada');
            }
        } catch {
            showMessage('Error al guardar');
        } finally {
            setSaving(false);
        }
    };

    const handleClearWhatsApp = async () => {
        if (!confirm('¿Borrar la configuración de WhatsApp de este gimnasio?')) return;
        setSaving(true);
        try {
            const res = await api.clearGymWhatsApp(gymId);
            if (res.ok) {
                setWaConfig({});
                showMessage('Configuración de WhatsApp borrada');
            } else {
                showMessage(res.error || 'Error al borrar');
            }
        } catch {
            showMessage('Error al borrar');
        } finally {
            setSaving(false);
        }
    };

    const handleSaveBranding = async () => {
        setSaving(true);
        try {
            const res = await api.saveGymBranding(gymId, branding);
            if (res.ok) {
                showMessage('Branding guardado correctamente');
            } else {
                showMessage(res.error || 'Error al guardar branding');
            }
        } catch {
            showMessage('Error al guardar branding');
        } finally {
            setSaving(false);
        }
    };

    const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        try {
            const res = await api.uploadGymLogo(gymId, file);
            if (res.ok && res.data?.url) {
                setBranding(prev => ({ ...prev, logo_url: res.data!.url }));
                showMessage('Logo subido correctamente');
            } else {
                showMessage(res.error || 'Error al subir logo');
            }
        } catch {
            showMessage('Error al subir logo');
        } finally {
            setUploading(false);
        }
    };

    const handleChangePassword = async () => {
        if (!newPassword || newPassword.length < 6) {
            showMessage('La contraseña debe tener al menos 6 caracteres');
            return;
        }
        setSaving(true);
        try {
            const res = await api.setGymOwnerPassword(gymId, newPassword);
            if (res.ok) {
                showMessage('Contraseña actualizada');
                setNewPassword('');
            } else {
                showMessage(res.error || 'Error al cambiar contraseña');
            }
        } catch {
            showMessage('Error al cambiar contraseña');
        } finally {
            setSaving(false);
        }
    };

    const handleActivateMaintenance = async () => {
        setSaving(true);
        try {
            if (maintUntil) {
                await api.sendMaintenanceNoticeUntil([gymId], maintMessage, maintUntil);
            } else {
                await api.sendMaintenanceNotice([gymId], maintMessage);
            }
            showMessage('Mantenimiento activado');
            await refresh();
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleDeactivateMaintenance = async () => {
        setSaving(true);
        try {
            await api.clearMaintenance([gymId]);
            showMessage('Mantenimiento desactivado');
            setMaintMessage('');
            setMaintUntil('');
            await refresh();
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleSendReminder = async () => {
        if (!reminderMessage.trim()) return;
        setSaving(true);
        try {
            const res = await api.sendReminder([gymId], reminderMessage.trim());
            if (res.ok) {
                showMessage('Recordatorio enviado');
                setReminderMessage('');
            } else {
                showMessage(res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleRegisterPayment = async () => {
        if (!paymentAmount) return;
        setSaving(true);
        try {
            const res = await api.registerPayment(gymId, {
                amount: Number(paymentAmount),
                plan: paymentPlanName || undefined,
                plan_id: typeof paymentPlanId === 'number' ? paymentPlanId : undefined,
                valid_until: paymentValidUntil || undefined,
            });
            if (res.ok) {
                showMessage('Pago registrado');
                setPaymentAmount('');
                setPaymentPlanId('');
                setPaymentPlanName('');
                setPaymentValidUntil('');
                await refresh();
            } else {
                showMessage(res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleAssignSubscription = async () => {
        if (!assignSubParams.plan_id) return;

        if (assignSubParams.start_date && assignSubParams.end_date) {
            if (new Date(assignSubParams.end_date) <= new Date(assignSubParams.start_date)) {
                showMessage('La fecha de vencimiento debe ser posterior al inicio');
                return;
            }
        }

        setAssignSubLoading(true);
        try {
            const res = await api.assignGymSubscriptionManual(gymId, {
                plan_id: assignSubParams.plan_id,
                start_date: assignSubParams.start_date || undefined,
                end_date: assignSubParams.end_date || undefined
            });
            if (res.ok) {
                showMessage('Suscripción asignada');
                setAssignSubOpen(false);
                setAssignSubParams({ plan_id: 0, start_date: '', end_date: '' });
                await refresh();
            } else {
                showMessage(res.error || 'Error asignando suscripción');
            }
        } catch {
            showMessage('Error');
        } finally {
            setAssignSubLoading(false);
        }
    };

    const handleSendWhatsAppTest = async () => {
        if (!waTestPhone.trim()) return;
        setSaving(true);
        try {
            const res = await api.sendWhatsAppTest(gymId, waTestPhone.trim(), waTestMessage);
            if (res.ok && res.data?.ok) {
                showMessage(res.data.message || 'Mensaje enviado');
            } else {
                showMessage(res.data?.error || res.error || 'Error');
            }
        } catch {
            showMessage('Error');
        } finally {
            setSaving(false);
        }
    };

    const handleProvisionTemplates = async () => {
        setProvisioningTemplates(true);
        setProvisionTemplatesMsg('');
        try {
            await api.syncWhatsAppTemplateDefaults(true);
            const res = await api.provisionGymWhatsAppTemplates(gymId);
            if (res.ok && res.data) {
                const failed = (res.data.failed || []).length;
                const bumped = (res.data.created_bumped || []).length;
                setProvisionTemplatesMsg(`OK: created=${(res.data.created || []).length}, bumped=${bumped}, failed=${failed}, existing=${res.data.existing_count}`);
            } else {
                setProvisionTemplatesMsg(res.error || 'Error provisionando plantillas');
            }
        } finally {
            setProvisioningTemplates(false);
            try {
                const tplRes = await api.getWhatsAppTemplateCatalog(false);
                if (tplRes.ok && tplRes.data) {
                    setWaCatalog(tplRes.data.templates || []);
                }
                setWaActionsLoading(true);
                const actRes = await api.getGymWhatsAppActions(gymId);
                if (actRes.ok && actRes.data) {
                    setWaActions(actRes.data.actions || []);
                }
                const hRes = await api.getGymWhatsAppHealth(gymId);
                if (hRes.ok && isRecord(hRes.data) && Array.isArray(hRes.data.templates_list)) {
                    const mapped = hRes.data.templates_list
                        .map((t) => {
                            if (!isRecord(t)) return null;
                            const name = String(t.name || '').trim();
                            if (!name) return null;
                            return {
                                name,
                                status: String(t.status || ''),
                                category: String(t.category || ''),
                                language: String(t.language || ''),
                            };
                        })
                        .filter(Boolean) as Array<{ name: string; status: string; category: string; language: string }>;
                    setWaMetaTemplates(mapped);
                }
            } catch {
                // Ignore
            } finally {
                setWaActionsLoading(false);
            }
            try {
                setWaEventsLoading(true);
                const evRes = await api.getGymWhatsAppOnboardingEvents(gymId, 20);
                if (evRes.ok && evRes.data) {
                    setWaEvents(evRes.data.events || []);
                }
            } finally {
                setWaEventsLoading(false);
            }
        }
    };

    const handleWhatsAppHealthCheck = async () => {
        setWaHealthLoading(true);
        setWaHealthMsg('');
        try {
            const res = await api.getGymWhatsAppHealth(gymId);
            const data = res.data;
            const d = isRecord(data) ? data : {};
            const templates = isRecord(d.templates) ? d.templates : {};
            const phone = isRecord(d.phone) ? d.phone : {};
            const sub = isRecord(d.subscribed_apps) ? d.subscribed_apps : {};
            const templatesList = Array.isArray(d.templates_list) ? d.templates_list : null;

            if (templatesList) {
                const mapped = templatesList
                    .map((t) => {
                        if (!isRecord(t)) return null;
                        const name = String(t.name || '').trim();
                        if (!name) return null;
                        return {
                            name,
                            status: String(t.status || ''),
                            category: String(t.category || ''),
                            language: String(t.language || ''),
                        };
                    })
                    .filter(Boolean) as Array<{ name: string; status: string; category: string; language: string }>;
                setWaMetaTemplates(mapped);
            }

            if (res.ok && d.ok === true) {
                setWaHealthMsg(
                    `OK: phone=${String(phone.display_phone_number || '—')} quality=${String(phone.quality_rating || '—')} templates=${Number(templates.count || 0)} approved=${Number(templates.approved || 0)} pending=${Number(templates.pending || 0)} subscribed=${String(sub.subscribed)}`
                );
            } else {
                const err = d.error ? String(d.error) : res.error || 'Error en health-check';
                setWaHealthMsg(err);
            }
        } finally {
            setWaHealthLoading(false);
            try {
                setWaEventsLoading(true);
                const evRes = await api.getGymWhatsAppOnboardingEvents(gymId, 20);
                if (evRes.ok && evRes.data) {
                    setWaEvents(evRes.data.events || []);
                }
            } finally {
                setWaEventsLoading(false);
            }
        }
    };

    const moduleDefaults: Record<string, boolean> = {
        usuarios: true,
        pagos: true,
        profesores: true,
        empleados: true,
        rutinas: true,
        ejercicios: true,
        clases: true,
        asistencias: true,
        whatsapp: true,
        configuracion: true,
        reportes: true,
        entitlements_v2: false,
        bulk_actions: false,
        soporte: true,
        novedades: true,
        accesos: false,
    };

    const moduleOptions: Array<{ key: string; label: string }> = [
        { key: 'usuarios', label: 'Usuarios' },
        { key: 'pagos', label: 'Pagos' },
        { key: 'profesores', label: 'Profesores' },
        { key: 'empleados', label: 'Empleados' },
        { key: 'rutinas', label: 'Rutinas' },
        { key: 'ejercicios', label: 'Ejercicios' },
        { key: 'clases', label: 'Clases' },
        { key: 'asistencias', label: 'Asistencias' },
        { key: 'whatsapp', label: 'WhatsApp' },
        { key: 'bulk_actions', label: 'Acciones masivas (danger zone)' },
        { key: 'soporte', label: 'Soporte' },
        { key: 'novedades', label: 'Novedades' },
        { key: 'accesos', label: 'Accesos (molinete/puerta)' },
        { key: 'configuracion', label: 'Configuración' },
        { key: 'reportes', label: 'Reportes' },
        { key: 'entitlements_v2', label: 'Accesos avanzados (multi-sucursal y clases)' },
    ];

    const sections: { id: Section; name: string; icon: React.ComponentType<{ className?: string }> }[] = [
        { id: 'onboarding', name: 'Primeros pasos', icon: ListChecks },
        { id: 'subscription', name: 'Suscripción', icon: CreditCard },
        { id: 'branches', name: 'Sucursales', icon: MapPin },
        { id: 'payments', name: 'Pagos', icon: CreditCard },
        { id: 'whatsapp', name: 'WhatsApp', icon: MessageSquare },
        { id: 'maintenance', name: 'Mantenimiento', icon: Wrench },
        { id: 'attendance', name: 'Asistencias', icon: Activity },
        { id: 'modules', name: 'Módulos', icon: Activity },
        { id: 'routine_templates', name: 'Rutinas / Templates', icon: FileText },
        { id: 'entitlements', name: 'Accesos', icon: Key },
        { id: 'branding', name: 'Branding', icon: Palette },
        { id: 'health', name: 'Salud', icon: FileText },
        { id: 'password', name: 'Contraseña dueño', icon: Key },
    ];

    if (loading) {
        return (
            <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        );
    }

    if (!gym) {
        return (
            <div className="text-center py-16">
                <p className="text-slate-500">Gimnasio no encontrado</p>
                <Link href="/dashboard/gyms" className="text-primary-400 hover:text-primary-300 mt-2 inline-block">
                    Volver a gimnasios
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/dashboard/gyms" className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="page-title">{gym.nombre}</h1>
                    <p className="text-slate-400">{gym.subdominio} · ID: {gym.id}</p>
                </div>
                <span
                    className={`ml-auto badge ${gym.status === 'active' ? 'badge-success' : gym.status === 'maintenance' ? 'badge-warning' : 'badge-danger'
                        }`}
                >
                    {gym.status === 'active' ? 'Activo' : gym.status === 'maintenance' ? 'Mantenimiento' : 'Suspendido'}
                </span>
            </div>

            {/* Section Tabs */}
            <div className="flex gap-2 flex-wrap">
                {sections.map((sec) => (
                    <button
                        key={sec.id}
                        onClick={() => setActiveSection(sec.id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${activeSection === sec.id
                            ? 'bg-primary-500/20 text-primary-400'
                            : 'bg-slate-800/50 text-slate-400 hover:text-white'
                            }`}
                    >
                        <sec.icon className="w-4 h-4" />
                        {sec.name}
                    </button>
                ))}
            </div>

            {/* Message */}
            {message && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card p-3 flex items-center gap-2 text-primary-400"
                >
                    <Check className="w-4 h-4" />
                    {message}
                </motion.div>
            )}

            {/* Content */}
            <div className="card p-6">
                {activeSection === 'onboarding' && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between gap-3">
                            <h2 className="text-lg font-semibold text-white">Primeros pasos</h2>
                            <button onClick={reloadOnboarding} disabled={onboardingLoading} className="btn-secondary flex items-center gap-2">
                                {onboardingLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Actualizar'}
                            </button>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-2">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="text-white font-medium">Estado del gimnasio</div>
                                    {String(onboarding?.gym_status || gym.status) === 'active' ? (
                                        <div className="flex items-center gap-2 text-success-400">
                                            <Check className="w-4 h-4" />
                                            Activo
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-warning-400">
                                            <AlertCircle className="w-4 h-4" />
                                            {String(onboarding?.gym_status || gym.status)}
                                        </div>
                                    )}
                                </div>
                                <div className="text-xs text-slate-500">
                                    Para producción: estado activo y suscripción al día.
                                </div>
                                <div className="flex justify-end">
                                    <button onClick={() => setActiveSection('maintenance')} className="btn-secondary">
                                        Ver mantenimiento
                                    </button>
                                </div>
                            </div>

                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-2">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="text-white font-medium">URL del tenant</div>
                                    {onboarding?.tenant_url ? (
                                        <a className="text-primary-400 hover:text-primary-300 text-sm" href={String(onboarding.tenant_url)} target="_blank" rel="noreferrer">
                                            Abrir
                                        </a>
                                    ) : null}
                                </div>
                                <div className="text-sm text-slate-300 break-all">
                                    {String(onboarding?.tenant_url || `https://${gym.subdominio}.${process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz'}`)}
                                </div>
                                <div className="text-xs text-slate-500">
                                    Verificá que el DNS/certificado del subdominio esté listo.
                                </div>
                            </div>

                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-2">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="text-white font-medium">Listo para producción</div>
                                    {Boolean(onboarding?.production_ready) ? (
                                        <div className="flex items-center gap-2 text-success-400">
                                            <Check className="w-4 h-4" />
                                            Sí
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <AlertCircle className="w-4 h-4" />
                                            No
                                        </div>
                                    )}
                                </div>
                                {onboarding?.production_ready_at ? (
                                    <div className="text-xs text-slate-500">
                                        Marcado: {String(onboarding.production_ready_at).slice(0, 19).replace('T', ' ')}
                                    </div>
                                ) : (
                                    <div className="text-xs text-slate-500">
                                        Marcá cuando el gimnasio esté “apto prod” (sucursales, owner, pagos/plan, WhatsApp si aplica).
                                    </div>
                                )}
                                <div className="flex justify-end">
                                    <button
                                        onClick={() => setProductionReady(!Boolean(onboarding?.production_ready))}
                                        disabled={prodReadySaving}
                                        className={Boolean(onboarding?.production_ready) ? 'btn-secondary' : 'btn-primary'}
                                    >
                                        {prodReadySaving ? <Loader2 className="w-4 h-4 animate-spin" /> : (Boolean(onboarding?.production_ready) ? 'Desmarcar' : 'Marcar listo')}
                                    </button>
                                </div>
                            </div>

                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-2">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="text-white font-medium">Sucursales</div>
                                    {Number(onboarding?.branches_active ?? 0) > 0 ? (
                                        <div className="flex items-center gap-2 text-success-400">
                                            <Check className="w-4 h-4" />
                                            OK
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-danger-400">
                                            <X className="w-4 h-4" />
                                            Falta
                                        </div>
                                    )}
                                </div>
                                <div className="text-sm text-slate-300">
                                    Activas: <span className="text-white font-medium">{Number(onboarding?.branches_active ?? branches.filter((b) => String(b.status || '').toLowerCase() !== 'inactive').length)}</span>
                                    {' · '}
                                    Total: <span className="text-white font-medium">{Number(onboarding?.branches_total ?? branches.length)}</span>
                                </div>
                                <div className="text-xs text-slate-500">
                                    No se puede dejar al gimnasio sin sucursales activas.
                                </div>
                                <div className="flex justify-end">
                                    <button onClick={() => setActiveSection('branches')} className="btn-secondary">
                                        Gestionar sucursales
                                    </button>
                                </div>
                            </div>

                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-2">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="text-white font-medium">Contraseña Owner</div>
                                    {Boolean(onboarding?.owner_password_set) ? (
                                        <div className="flex items-center gap-2 text-success-400">
                                            <Check className="w-4 h-4" />
                                            Seteada
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-danger-400">
                                            <X className="w-4 h-4" />
                                            Pendiente
                                        </div>
                                    )}
                                </div>
                                <div className="text-xs text-slate-500">
                                    Recomendación: rotar credenciales cuando el cliente tome control.
                                </div>
                                <div className="flex justify-end">
                                    <button onClick={() => setActiveSection('password')} className="btn-secondary">
                                        Gestionar contraseña
                                    </button>
                                </div>
                            </div>

                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-2">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="text-white font-medium">WhatsApp</div>
                                    {Boolean(onboarding?.whatsapp_configured) ? (
                                        <div className="flex items-center gap-2 text-success-400">
                                            <Check className="w-4 h-4" />
                                            Configurado
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-slate-400">
                                            <AlertCircle className="w-4 h-4" />
                                            Opcional
                                        </div>
                                    )}
                                </div>
                                <div className="text-xs text-slate-500">
                                    Si lo usás: configurar credenciales, provisionar templates y hacer health-check.
                                </div>
                                <div className="flex justify-end">
                                    <button onClick={() => setActiveSection('whatsapp')} className="btn-secondary">
                                        Abrir WhatsApp
                                    </button>
                                </div>
                            </div>

                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-2">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="text-white font-medium">Módulos y accesos</div>
                                    <div className="flex items-center gap-2 text-slate-300">
                                        <ListChecks className="w-4 h-4" />
                                        Revisar
                                    </div>
                                </div>
                                <div className="text-xs text-slate-500">
                                    Ajustar módulos y accesos por sucursal/plan si aplica.
                                </div>
                                <div className="flex justify-end gap-2">
                                    <button onClick={() => setActiveSection('modules')} className="btn-secondary">
                                        Módulos
                                    </button>
                                    <button onClick={() => setActiveSection('entitlements')} className="btn-secondary">
                                        Accesos
                                    </button>
                                </div>
                            </div>

                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-3">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="text-white font-medium">Migraciones (DB tenant)</div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={refreshTenantMigration}
                                            disabled={tenantMigrationLoading || tenantProvisioning}
                                            className="btn-secondary"
                                        >
                                            {tenantMigrationLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Revisar'}
                                        </button>
                                        <button
                                            onClick={provisionTenantNow}
                                            disabled={
                                                tenantProvisioning ||
                                                tenantMigrationLoading ||
                                                !tenantMigration ||
                                                tenantMigration.status === 'up_to_date'
                                            }
                                            className="btn-primary flex items-center gap-2"
                                        >
                                            {tenantProvisioning ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Migrar ahora'}
                                        </button>
                                    </div>
                                </div>

                                <div className="text-sm text-slate-300">
                                    {!tenantMigration && 'Sin datos'}
                                    {tenantMigration && !tenantMigration.ok && `Error: ${tenantMigration.error || 'unknown'}`}
                                    {tenantMigration && tenantMigration.ok && (
                                        <div className="space-y-1">
                                            <div className="flex items-center gap-2">
                                                {tenantMigration.status === 'up_to_date' && <Check className="w-4 h-4 text-success-400" />}
                                                {tenantMigration.status === 'outdated' && <AlertCircle className="w-4 h-4 text-warning-400" />}
                                                {tenantMigration.status === 'uninitialized' && <AlertCircle className="w-4 h-4 text-warning-400" />}
                                                {tenantMigration.status === 'unknown' && <AlertCircle className="w-4 h-4 text-slate-400" />}
                                                <span className="font-medium">
                                                    {tenantMigration.status === 'up_to_date'
                                                        ? 'Al día'
                                                        : tenantMigration.status === 'db_missing'
                                                            ? 'DB no existe'
                                                        : tenantMigration.status === 'outdated'
                                                            ? 'Desactualizado'
                                                            : tenantMigration.status === 'uninitialized'
                                                                ? 'Sin inicializar'
                                                                : 'Desconocido'}
                                                </span>
                                            </div>
                                            <div className="text-xs text-slate-400">
                                                head: {tenantMigration.head || '—'} · current: {tenantMigration.current || '—'}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'subscription' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Suscripción</h2>
                        <div className="grid grid-cols-2 gap-4 max-w-md">
                            <div>
                                <div className="text-sm text-slate-500">Estado</div>
                                <div className="text-white font-medium">{gym.status}</div>
                            </div>
                            <div>
                                <div className="text-sm text-slate-500">Creado</div>
                                <div className="text-white">{gym.created_at?.slice(0, 10) || '—'}</div>
                            </div>
                            <div>
                                <div className="text-sm text-slate-500">Plan Actual</div>
                                <div className="text-white font-medium">{gym.subscription_plan_name || '—'}</div>
                            </div>
                            <div>
                                <div className="text-sm text-slate-500">Vencimiento</div>
                                <div className={`${gym.subscription_status === 'active' ? 'text-success-400' : 'text-slate-400'}`}>
                                    {gym.subscription_next_due_date ? gym.subscription_next_due_date.slice(0, 10) : '—'}
                                </div>
                            </div>
                        </div>

                        {/* Manual Assignment Section */}
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Gestión Manual</h3>
                            {!assignSubOpen ? (
                                <button onClick={() => setAssignSubOpen(true)} className="btn-secondary flex items-center gap-2">
                                    <CreditCard className="w-4 h-4" />
                                    Asignar Suscripción Manual
                                </button>
                            ) : (
                                <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-3">
                                    <h4 className="text-sm font-medium text-slate-300">Asignar Plan (Sin Pago)</h4>
                                    <div className="space-y-3">
                                        <div>
                                            <label className="text-xs text-slate-400 block mb-1">Plan</label>
                                            <select
                                                className="input w-full"
                                                value={assignSubParams.plan_id}
                                                onChange={(e) => setAssignSubParams({ ...assignSubParams, plan_id: Number(e.target.value) })}
                                            >
                                                <option value={0}>Seleccionar Plan...</option>
                                                {plans.map(p => (
                                                    <option key={p.id} value={p.id}>{p.name} ({p.period_days} días)</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-3">
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Fecha de Inicio</label>
                                                <input
                                                    type="date"
                                                    className="input w-full"
                                                    value={assignSubParams.start_date}
                                                    onChange={(e) => setAssignSubParams({ ...assignSubParams, start_date: e.target.value })}
                                                    title="Fecha de inicio de la suscripción (hoy por defecto)"
                                                />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Fecha de Vencimiento (Opcional)</label>
                                                <input
                                                    type="date"
                                                    className="input w-full"
                                                    value={assignSubParams.end_date}
                                                    onChange={(e) => setAssignSubParams({ ...assignSubParams, end_date: e.target.value })}
                                                    title="Si se deja vacío, se calcula automáticamente según el plan"
                                                />
                                            </div>
                                        </div>
                                        <p className="text-xs text-slate-500 italic">
                                            * Si no defines la fecha de vencimiento, se calculará sumando la duración del plan a la fecha de inicio.
                                        </p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button onClick={handleAssignSubscription} disabled={assignSubLoading || !assignSubParams.plan_id} className="btn-primary">
                                            {assignSubLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                                        </button>
                                        <button onClick={() => setAssignSubOpen(false)} className="btn-secondary">Cancelar</button>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Enviar recordatorio</h3>
                            <div className="flex gap-3">
                                <input
                                    type="text"
                                    className="input flex-1"
                                    placeholder="Mensaje de recordatorio"
                                    value={reminderMessage}
                                    onChange={(e) => setReminderMessage(e.target.value)}
                                />
                                <button onClick={handleSendReminder} disabled={saving || !reminderMessage.trim()} className="btn-primary flex items-center gap-2">
                                    <Send className="w-4 h-4" />
                                    Enviar
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'branches' && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between gap-3">
                            <h2 className="text-lg font-semibold text-white">Sucursales</h2>
                            <div className="flex flex-wrap items-center gap-2">
                                <button onClick={openCreateBranch} disabled={branchSaving} className="btn-primary flex items-center gap-2">
                                    {branchSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                                    Nueva
                                </button>
                                <button onClick={() => { setBulkText(''); setBulkItems([]); setBranchBulkOpen(true); }} disabled={branchSaving} className="btn-secondary flex items-center gap-2">
                                    <Upload className="w-4 h-4" />
                                    Carga masiva
                                </button>
                                <button onClick={syncBranches} disabled={branchSaving || branchSyncing} className="btn-secondary">
                                    {branchSyncing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sincronizar'}
                                </button>
                                <button onClick={reloadBranches} disabled={branchSaving} className="btn-secondary">
                                    Recargar
                                </button>
                            </div>
                        </div>

                        {branches.length === 0 ? (
                            <p className="text-slate-500">Sin sucursales</p>
                        ) : (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Nombre</th>
                                        <th>Código</th>
                                        <th>Estado</th>
                                        <th>Timezone</th>
                                        <th>Dirección</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {branches.map((b) => {
                                        const st = String(b.status || 'active').toLowerCase() === 'inactive' ? 'inactive' : 'active';
                                        return (
                                            <tr key={b.id}>
                                                <td>{b.id}</td>
                                                <td className="text-white">{b.name}</td>
                                                <td>{b.code}</td>
                                                <td>
                                                    <span className={`badge ${st === 'active' ? 'badge-success' : 'badge-danger'}`}>
                                                        {st}
                                                    </span>
                                                </td>
                                                <td>{b.timezone || '—'}</td>
                                                <td className="max-w-[320px] truncate" title={b.address || ''}>{b.address || '—'}</td>
                                                <td className="text-right">
                                                    <div className="flex justify-end gap-2">
                                                        <button
                                                            onClick={() => startEditBranch(b)}
                                                            className="btn-secondary flex items-center gap-2"
                                                            disabled={branchSaving}
                                                            title="Editar"
                                                        >
                                                            <Pencil className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => toggleBranchStatus(b)}
                                                            className="btn-secondary"
                                                            disabled={branchSaving}
                                                        >
                                                            {st === 'active' ? 'Desactivar' : 'Activar'}
                                                        </button>
                                                        <button
                                                            onClick={() => deleteBranch(b)}
                                                            className="btn-danger flex items-center gap-2"
                                                            disabled={branchSaving}
                                                            title="Eliminar/Desactivar"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        )}

                        <AnimatePresence>
                            {branchCreateOpen && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 overflow-y-auto"
                                    onClick={() => setBranchCreateOpen(false)}
                                >
                                    <motion.div
                                        initial={{ scale: 0.95, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        exit={{ scale: 0.95, opacity: 0 }}
                                        onClick={(e) => e.stopPropagation()}
                                        className="card w-full max-w-lg p-6 my-8"
                                    >
                                        <h3 className="text-lg font-semibold text-white mb-4">Nueva sucursal</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Nombre</label>
                                                <input className="input w-full" value={String(branchDraft.name || '')} onChange={(e) => setBranchDraft({ ...branchDraft, name: e.target.value })} />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Código</label>
                                                <input className="input w-full" value={String(branchDraft.code || '')} onChange={(e) => setBranchDraft({ ...branchDraft, code: e.target.value })} />
                                                <div className="text-[11px] text-slate-500 mt-1">Minúsculas, sin espacios. Ej: principal, centro, sede-norte</div>
                                                {!!branchDraftCodeError && <div className="text-[11px] text-danger-400 mt-1">{branchDraftCodeError}</div>}
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Timezone</label>
                                                <input className="input w-full" placeholder="America/Argentina/Buenos_Aires" value={String(branchDraft.timezone || '')} onChange={(e) => setBranchDraft({ ...branchDraft, timezone: e.target.value })} />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Dirección</label>
                                                <input className="input w-full" value={String(branchDraft.address || '')} onChange={(e) => setBranchDraft({ ...branchDraft, address: e.target.value })} />
                                            </div>
                                        </div>
                                        <div className="flex items-center justify-end gap-2 pt-5">
                                            <button onClick={() => setBranchCreateOpen(false)} disabled={branchSaving} className="btn-secondary">Cancelar</button>
                                            <button onClick={createBranch} disabled={branchSaving || !String(branchDraft.name || '').trim() || !String(branchDraft.code || '').trim() || !!branchDraftCodeError} className="btn-primary flex items-center gap-2">
                                                {branchSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                                                Crear
                                            </button>
                                        </div>
                                    </motion.div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <AnimatePresence>
                            {branchEditOpen && editingBranchId ? (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 overflow-y-auto"
                                    onClick={cancelEditBranch}
                                >
                                    <motion.div
                                        initial={{ scale: 0.95, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        exit={{ scale: 0.95, opacity: 0 }}
                                        onClick={(e) => e.stopPropagation()}
                                        className="card w-full max-w-lg p-6 my-8"
                                    >
                                        <h3 className="text-lg font-semibold text-white mb-4">Editar sucursal #{editingBranchId}</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Nombre</label>
                                                <input className="input w-full" value={String(editBranchDraft.name || '')} onChange={(e) => setEditBranchDraft({ ...editBranchDraft, name: e.target.value })} />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Código</label>
                                                <input className="input w-full" value={String(editBranchDraft.code || '')} onChange={(e) => setEditBranchDraft({ ...editBranchDraft, code: e.target.value })} />
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Estado</label>
                                                <select className="input w-full" value={String(editBranchDraft.status || 'active')} onChange={(e) => setEditBranchDraft({ ...editBranchDraft, status: e.target.value as GymBranchUpdateInput['status'] })}>
                                                    <option value="active">active</option>
                                                    <option value="inactive">inactive</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-xs text-slate-400 block mb-1">Timezone</label>
                                                <input className="input w-full" value={String(editBranchDraft.timezone || '')} onChange={(e) => setEditBranchDraft({ ...editBranchDraft, timezone: e.target.value })} />
                                            </div>
                                            <div className="md:col-span-2">
                                                <label className="text-xs text-slate-400 block mb-1">Dirección</label>
                                                <input className="input w-full" value={String(editBranchDraft.address || '')} onChange={(e) => setEditBranchDraft({ ...editBranchDraft, address: e.target.value })} />
                                            </div>
                                        </div>
                                        <div className="flex items-center justify-end gap-2 pt-5">
                                            <button onClick={cancelEditBranch} disabled={branchSaving} className="btn-secondary flex items-center gap-2">
                                                <X className="w-4 h-4" />
                                                Cancelar
                                            </button>
                                            <button onClick={updateBranch} disabled={branchSaving} className="btn-primary flex items-center gap-2">
                                                {branchSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                                Guardar
                                            </button>
                                        </div>
                                    </motion.div>
                                </motion.div>
                            ) : null}
                        </AnimatePresence>

                        <AnimatePresence>
                            {branchBulkOpen && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 overflow-y-auto"
                                    onClick={() => setBranchBulkOpen(false)}
                                >
                                    <motion.div
                                        initial={{ scale: 0.95, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        exit={{ scale: 0.95, opacity: 0 }}
                                        onClick={(e) => e.stopPropagation()}
                                        className="card w-full max-w-2xl p-6 my-8"
                                    >
                                        <h3 className="text-lg font-semibold text-white mb-2">Carga masiva de sucursales</h3>
                                        <div className="text-xs text-slate-500 mb-3">
                                            Formato: nombre;codigo;timezone;direccion (una por línea). Separador recomendado: ; o tab. El código debe ser único y en minúsculas.
                                        </div>
                                        <textarea
                                            className="input w-full min-h-[160px] font-mono text-sm"
                                            value={bulkText}
                                            onChange={(e) => {
                                                const v = e.target.value;
                                                setBulkText(v);
                                                parseBulk(v);
                                            }}
                                            placeholder={"Principal;principal;America/Argentina/Buenos_Aires;Calle 123\nCentro;centro;America/Argentina/Buenos_Aires;Av. Siempre Viva 742"}
                                        />
                                        <div className="mt-3 text-sm text-slate-300">
                                            Items detectados: <span className="text-white font-medium">{bulkItems.length}</span>
                                        </div>
                                        {bulkItems.length ? (
                                            <div className="mt-3 border border-slate-800 rounded-xl overflow-hidden">
                                                <table className="w-full text-sm">
                                                    <thead className="bg-slate-900/60">
                                                        <tr className="text-left text-slate-400">
                                                            <th className="p-2">Nombre</th>
                                                            <th className="p-2">Código</th>
                                                            <th className="p-2">Timezone</th>
                                                            <th className="p-2">Dirección</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {bulkItems.slice(0, 6).map((it, idx) => (
                                                            <tr key={idx} className="border-t border-slate-800">
                                                                <td className="p-2 text-white">{it.name}</td>
                                                                <td className="p-2">{it.code}</td>
                                                                <td className="p-2">{it.timezone || '—'}</td>
                                                                <td className="p-2">{it.address || '—'}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        ) : null}
                                        <div className="flex items-center justify-end gap-2 pt-5">
                                            <button onClick={() => setBranchBulkOpen(false)} disabled={bulkSubmitting} className="btn-secondary">Cancelar</button>
                                            <button onClick={submitBulk} disabled={bulkSubmitting || !bulkItems.length} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                                                {bulkSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                                                Importar
                                            </button>
                                        </div>
                                    </motion.div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <AnimatePresence>
                            {branchConfirm && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
                                    onClick={() => setBranchConfirm(null)}
                                >
                                    <motion.div
                                        initial={{ scale: 0.95, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        exit={{ scale: 0.95, opacity: 0 }}
                                        onClick={(e) => e.stopPropagation()}
                                        className="card w-full max-w-sm p-6"
                                    >
                                        <h3 className="text-lg font-semibold text-white mb-2">Desactivar sucursal</h3>
                                        <p className="text-slate-400 mb-4">
                                            ¿Desactivar <span className="text-white font-medium">{branchConfirm.name}</span>? No se elimina físicamente.
                                        </p>
                                        <div className="flex items-center justify-end gap-2">
                                            <button onClick={() => setBranchConfirm(null)} disabled={branchSaving} className="btn-secondary">Cancelar</button>
                                            <button onClick={confirmDeleteBranch} disabled={branchSaving} className="btn-danger flex items-center gap-2">
                                                {branchSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                                Desactivar
                                            </button>
                                        </div>
                                    </motion.div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                )}

                {activeSection === 'payments' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Historial de Pagos</h2>
                        {payments.length === 0 ? (
                            <p className="text-slate-500">Sin pagos registrados</p>
                        ) : (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Monto</th>
                                        <th>Estado</th>
                                        <th>Válido hasta</th>
                                        <th>Fecha</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {payments.map((p) => (
                                        <tr key={p.id}>
                                            <td>{p.id}</td>
                                            <td className="text-success-400">${p.amount}</td>
                                            <td><span className="badge badge-success">{p.status}</span></td>
                                            <td>{p.valid_until || '—'}</td>
                                            <td>{p.created_at?.slice(0, 10)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Registrar pago</h3>
                            <form className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <input type="number" className="input" placeholder="Monto" value={paymentAmount} onChange={(e) => setPaymentAmount(e.target.value)} />
                                <div className="space-y-1">
                                    <select
                                        className="input w-full"
                                        value={paymentPlanId}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            if (val === '') {
                                                setPaymentPlanId('');
                                                setPaymentPlanName('');
                                            } else {
                                                const pid = Number(val);
                                                setPaymentPlanId(pid);
                                                const p = plans.find(x => x.id === pid);
                                                if (p) {
                                                    setPaymentPlanName(p.name);
                                                    setPaymentAmount(String(p.amount));

                                                    // Calculate valid_until based on plan period from TODAY
                                                    const d = new Date();
                                                    d.setDate(d.getDate() + (p.period_days || 30));
                                                    setPaymentValidUntil(d.toISOString().slice(0, 10));
                                                }
                                            }
                                        }}
                                    >
                                        <option value="">-- Sin plan / Solo pago --</option>
                                        {plans.map(p => (
                                            <option key={p.id} value={p.id}>{p.name} ({p.amount} {p.currency})</option>
                                        ))}
                                    </select>
                                    <p className="text-[10px] text-slate-500">* Seleccionar un plan autocompletará el monto y fecha.</p>
                                </div>
                                <div className="space-y-1">
                                    <input
                                        type="date"
                                        className="input w-full"
                                        value={paymentValidUntil}
                                        onChange={(e) => setPaymentValidUntil(e.target.value)}
                                        title="Fecha hasta la cual es válido el pago (vencimiento de suscripción)"
                                    />
                                    <p className="text-[10px] text-slate-500">* Válido hasta: Nueva fecha de vencimiento estimado.</p>
                                </div>
                                <button type="button" onClick={handleRegisterPayment} disabled={saving || !paymentAmount} className="btn-primary">Registrar</button>
                            </form>
                        </div>
                    </div>
                )}

                {activeSection === 'whatsapp' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Configuración de WhatsApp</h2>
                        <div className="card p-4 border border-slate-800 bg-slate-950/40 max-w-2xl">
                            <div className="text-sm text-slate-400 mb-2">Estado actual (guardado en el tenant)</div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                                <div>
                                    <div className="text-slate-500">Phone ID</div>
                                    <div className="text-white break-all">{gym?.tenant_whatsapp_phone_id || '—'}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">WABA ID</div>
                                    <div className="text-white break-all">{gym?.tenant_whatsapp_waba_id || '—'}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">Token</div>
                                    <div className="text-white">{gym?.tenant_whatsapp_access_token_present ? 'presente' : '—'}</div>
                                </div>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                            <div>
                                <label className="label">Phone ID</label>
                                <input
                                    type="text"
                                    value={waConfig.phone_id || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, phone_id: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">Access Token</label>
                                <input
                                    type="text"
                                    value={waConfig.access_token || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, access_token: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">WABA ID</label>
                                <input
                                    type="text"
                                    value={waConfig.business_account_id || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, business_account_id: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">Verify Token</label>
                                <input
                                    type="text"
                                    value={waConfig.verify_token || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, verify_token: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">App Secret</label>
                                <input
                                    type="text"
                                    value={waConfig.app_secret || ''}
                                    onChange={(e) => setWaConfig({ ...waConfig, app_secret: e.target.value })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="label">Timeout (segundos)</label>
                                <input
                                    type="number"
                                    value={waConfig.send_timeout_seconds || 25}
                                    onChange={(e) => setWaConfig({ ...waConfig, send_timeout_seconds: Number(e.target.value) })}
                                    className="input"
                                    min={1}
                                    max={120}
                                />
                            </div>
                            <label className="flex items-center gap-2 md:col-span-2">
                                <input
                                    type="checkbox"
                                    checked={waConfig.nonblocking || false}
                                    onChange={(e) => setWaConfig({ ...waConfig, nonblocking: e.target.checked })}
                                />
                                <span className="text-slate-300">Envío no bloqueante</span>
                            </label>
                        </div>
                        <div className="flex flex-wrap gap-3">
                            <button onClick={handleSaveWhatsApp} disabled={saving} className="btn-primary flex items-center gap-2">
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                Guardar
                            </button>
                            <button onClick={handleClearWhatsApp} disabled={saving} className="btn-danger flex items-center gap-2">
                                <Trash2 className="w-4 h-4" />
                                Borrar configuración
                            </button>
                            <button onClick={handleProvisionTemplates} disabled={provisioningTemplates} className="btn-secondary flex items-center gap-2">
                                {provisioningTemplates ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageSquare className="w-4 h-4" />}
                                Provisionar plantillas estándar
                            </button>
                            <button onClick={handleWhatsAppHealthCheck} disabled={waHealthLoading} className="btn-secondary flex items-center gap-2">
                                {waHealthLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                                Health check
                            </button>
                        </div>
                        {provisionTemplatesMsg ? (
                            <div className="text-sm text-slate-300">{provisionTemplatesMsg}</div>
                        ) : null}
                        {waHealthMsg ? (
                            <div className="text-sm text-slate-300">{waHealthMsg}</div>
                        ) : null}
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Eventos de onboarding</h3>
                            {waEventsLoading ? (
                                <div className="text-slate-400 flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                                </div>
                            ) : waEvents.length ? (
                                <div className="space-y-2 max-w-3xl">
                                    {waEvents.slice(0, 12).map((ev, idx) => (
                                        <div key={`${ev.created_at}-${idx}`} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="text-slate-200 text-sm">
                                                    <div className="text-slate-500 text-xs">{String(ev.created_at || '').replace('T', ' ').slice(0, 19)}</div>
                                                    <div className="mt-1">
                                                        <span className="text-slate-400">{ev.event_type}</span> — {ev.message}
                                                    </div>
                                                </div>
                                                <span
                                                    className={`badge ${String(ev.severity || '').toLowerCase() === 'error'
                                                        ? 'badge-danger'
                                                        : String(ev.severity || '').toLowerCase() === 'warning'
                                                            ? 'badge-warning'
                                                            : 'badge-success'
                                                        }`}
                                                >
                                                    {String(ev.severity || 'info')}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-slate-400 text-sm">—</div>
                            )}
                        </div>
                        <div className="pt-4 border-t border-slate-800">
                            <div className="flex items-center justify-between gap-3 mb-3">
                                <h3 className="font-medium text-white">Acciones y versiones (por gimnasio)</h3>
                                <div className="flex items-center gap-2">
                                    <button onClick={autoPickWaActionTemplates} disabled={waActionsLoading || savingAllWaActions} className="btn-secondary">
                                        Auto (mejor APPROVED)
                                    </button>
                                    <button onClick={saveAllWaActions} disabled={waActionsLoading || savingAllWaActions} className="btn-primary">
                                        {savingAllWaActions ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar todo'}
                                    </button>
                                </div>
                            </div>
                            {waActionsLoading ? (
                                <div className="text-slate-400 flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                                </div>
                            ) : (
                                <div className="space-y-3 max-w-3xl">
                                    {waActions.map((a) => (
                                        <div key={a.action_key} className="flex flex-col md:flex-row md:items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                                            <div className="min-w-44 text-slate-200">{actionLabel[a.action_key] || a.action_key}</div>
                                            <label className="flex items-center gap-2 text-slate-300">
                                                <input
                                                    type="checkbox"
                                                    checked={Boolean(a.enabled)}
                                                    onChange={(e) =>
                                                        setWaActions((prev) => prev.map((x) => (x.action_key === a.action_key ? { ...x, enabled: e.target.checked } : x)))
                                                    }
                                                />
                                                Habilitado
                                            </label>
                                            <select
                                                className="input flex-1"
                                                value={a.template_name || ''}
                                                onChange={(e) =>
                                                    setWaActions((prev) =>
                                                        prev.map((x) => (x.action_key === a.action_key ? { ...x, template_name: e.target.value } : x))
                                                    )
                                                }
                                            >
                                                {(() => {
                                                    const opts = buildActionTemplateOptions(a);
                                                    if (!opts.length) {
                                                        return (
                                                            <option value="" disabled>
                                                                No hay templates compatibles en el catálogo
                                                            </option>
                                                        );
                                                    }
                                                    return opts.map((opt) => (
                                                        <option key={opt.name} value={opt.name} disabled={opt.disabled}>
                                                            {opt.label}
                                                        </option>
                                                    ));
                                                })()}
                                            </select>
                                            <button
                                                className="btn-primary"
                                                disabled={savingWaAction === a.action_key}
                                                onClick={() => saveWaAction(a.action_key)}
                                            >
                                                {savingWaAction === a.action_key ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Guardar'}
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Prueba de WhatsApp</h3>
                            <div className="flex gap-3">
                                <input type="text" className="input w-48" placeholder="+5493411234567" value={waTestPhone} onChange={(e) => setWaTestPhone(e.target.value)} />
                                <input type="text" className="input flex-1" value={waTestMessage} onChange={(e) => setWaTestMessage(e.target.value)} />
                                <button onClick={handleSendWhatsAppTest} disabled={saving || !waTestPhone.trim()} className="btn-secondary flex items-center gap-2">
                                    <Send className="w-4 h-4" />
                                    Enviar test
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'maintenance' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Modo Mantenimiento</h2>
                        <div className="max-w-lg space-y-4">
                            <div>
                                <label className="label">Mensaje para usuarios</label>
                                <textarea
                                    value={maintMessage}
                                    onChange={(e) => setMaintMessage(e.target.value)}
                                    className="input h-24 resize-none"
                                    placeholder="Estamos en mantenimiento, volvemos pronto..."
                                />
                            </div>
                            <div>
                                <label className="label">Hasta</label>
                                <input
                                    type="datetime-local"
                                    value={maintUntil}
                                    onChange={(e) => setMaintUntil(e.target.value)}
                                    className="input"
                                />
                            </div>
                            <div className="flex gap-3">
                                <button onClick={handleActivateMaintenance} disabled={saving} className="btn-warning flex items-center gap-2">
                                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wrench className="w-4 h-4" />}
                                    Activar mantenimiento
                                </button>
                                <button onClick={handleDeactivateMaintenance} disabled={saving} className="btn-secondary">Desactivar</button>
                            </div>
                        </div>
                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="font-medium text-white mb-3">Recordatorio en WebApp</h3>
                            <div className="flex gap-3">
                                <input
                                    type="text"
                                    className="input flex-1"
                                    placeholder="Mensaje de recordatorio"
                                    value={webappReminderMessage}
                                    onChange={(e) => setWebappReminderMessage(e.target.value)}
                                />
                                <button onClick={handleSaveWebappReminder} disabled={saving} className="btn-primary">Guardar recordatorio</button>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'branding' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Branding</h2>

                        {/* Logo Upload */}
                        <div className="flex items-start gap-6">
                            <div className="flex-shrink-0">
                                {branding.logo_url ? (
                                    <Image
                                        src={branding.logo_url}
                                        alt="Logo"
                                        width={96}
                                        height={96}
                                        unoptimized
                                        className="w-24 h-24 rounded-xl object-cover border border-slate-700"
                                    />
                                ) : (
                                    <div className="w-24 h-24 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-500">
                                        <Palette className="w-8 h-8" />
                                    </div>
                                )}
                            </div>
                            <div className="space-y-2">
                                <label className="label">Logo del gimnasio</label>
                                <input
                                    ref={logoInputRef}
                                    type="file"
                                    accept="image/*"
                                    onChange={handleLogoUpload}
                                    className="hidden"
                                />
                                <button
                                    onClick={() => logoInputRef.current?.click()}
                                    disabled={uploading}
                                    className="btn-secondary flex items-center gap-2"
                                >
                                    {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                                    {uploading ? 'Subiendo...' : 'Subir logo'}
                                </button>
                                <p className="text-xs text-slate-500">PNG, JPG, GIF, WebP. Máx. 5MB</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
                            <div>
                                <label className="label">Nombre público</label>
                                <input
                                    type="text"
                                    className="input"
                                    value={branding.nombre_publico || gym.nombre}
                                    onChange={(e) => setBranding(prev => ({ ...prev, nombre_publico: e.target.value }))}
                                />
                            </div>
                            <div>
                                <label className="label">Dirección</label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="Calle, número, ciudad"
                                    value={branding.direccion}
                                    onChange={(e) => setBranding(prev => ({ ...prev, direccion: e.target.value }))}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="label">Logo URL (o sube uno arriba)</label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="https://..."
                                    value={branding.logo_url}
                                    onChange={(e) => setBranding(prev => ({ ...prev, logo_url: e.target.value }))}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="label">Tagline del portal</label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="Ej: Portal de acceso para clientes y equipo."
                                    value={branding.portal_tagline}
                                    onChange={(e) => setBranding(prev => ({ ...prev, portal_tagline: e.target.value }))}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <h3 className="text-sm font-medium text-slate-300 mb-2">Colores</h3>
                                <div className="grid grid-cols-4 gap-3">
                                    <div>
                                        <label className="label text-xs">Primario</label>
                                        <input
                                            type="color"
                                            className="w-full h-10 rounded border-0 cursor-pointer"
                                            value={branding.color_primario}
                                            onChange={(e) => setBranding(prev => ({ ...prev, color_primario: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Secundario</label>
                                        <input
                                            type="color"
                                            className="w-full h-10 rounded border-0 cursor-pointer"
                                            value={branding.color_secundario}
                                            onChange={(e) => setBranding(prev => ({ ...prev, color_secundario: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Fondo</label>
                                        <input
                                            type="color"
                                            className="w-full h-10 rounded border-0 cursor-pointer"
                                            value={branding.color_fondo}
                                            onChange={(e) => setBranding(prev => ({ ...prev, color_fondo: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="label text-xs">Texto</label>
                                        <input
                                            type="color"
                                            className="w-full h-10 rounded border-0 cursor-pointer"
                                            value={branding.color_texto}
                                            onChange={(e) => setBranding(prev => ({ ...prev, color_texto: e.target.value }))}
                                        />
                                    </div>
                                </div>
                            </div>
                            <div className="md:col-span-2">
                                <h3 className="text-sm font-medium text-slate-300 mb-2">Accesos del portal</h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            checked={branding.portal_enable_checkin}
                                            onChange={(e) => setBranding(prev => ({ ...prev, portal_enable_checkin: e.target.checked }))}
                                        />
                                        <span className="text-slate-300 text-sm">Check-in</span>
                                    </label>
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            checked={branding.portal_enable_member}
                                            onChange={(e) => setBranding(prev => ({ ...prev, portal_enable_member: e.target.checked }))}
                                        />
                                        <span className="text-slate-300 text-sm">Usuarios (socio)</span>
                                    </label>
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            checked={branding.portal_enable_staff}
                                            onChange={(e) => setBranding(prev => ({ ...prev, portal_enable_staff: e.target.checked }))}
                                        />
                                        <span className="text-slate-300 text-sm">Gestión (staff)</span>
                                    </label>
                                    <label className="flex items-center gap-2">
                                        <input
                                            type="checkbox"
                                            checked={branding.portal_enable_owner}
                                            onChange={(e) => setBranding(prev => ({ ...prev, portal_enable_owner: e.target.checked }))}
                                        />
                                        <span className="text-slate-300 text-sm">Dashboard (dueño)</span>
                                    </label>
                                </div>
                            </div>
                            <div className="md:col-span-2">
                                <h3 className="text-sm font-medium text-slate-300 mb-2">Soporte</h3>
                                <div className="space-y-3">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                                        <label className="flex items-center gap-2 md:col-span-1">
                                            <input
                                                type="checkbox"
                                                checked={branding.support_whatsapp_enabled}
                                                onChange={(e) => setBranding(prev => ({ ...prev, support_whatsapp_enabled: e.target.checked }))}
                                            />
                                            <span className="text-slate-300 text-sm">WhatsApp</span>
                                        </label>
                                        <div className="md:col-span-2">
                                            <input
                                                type="text"
                                                className="input"
                                                placeholder="Ej: 54911XXXXXXXX"
                                                value={branding.support_whatsapp}
                                                onChange={(e) => setBranding(prev => ({ ...prev, support_whatsapp: e.target.value }))}
                                            />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                                        <label className="flex items-center gap-2 md:col-span-1">
                                            <input
                                                type="checkbox"
                                                checked={branding.support_email_enabled}
                                                onChange={(e) => setBranding(prev => ({ ...prev, support_email_enabled: e.target.checked }))}
                                            />
                                            <span className="text-slate-300 text-sm">Email</span>
                                        </label>
                                        <div className="md:col-span-2">
                                            <input
                                                type="email"
                                                className="input"
                                                placeholder="soporte@tugym.com"
                                                value={branding.support_email}
                                                onChange={(e) => setBranding(prev => ({ ...prev, support_email: e.target.value }))}
                                            />
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                                        <label className="flex items-center gap-2 md:col-span-1">
                                            <input
                                                type="checkbox"
                                                checked={branding.support_url_enabled}
                                                onChange={(e) => setBranding(prev => ({ ...prev, support_url_enabled: e.target.checked }))}
                                            />
                                            <span className="text-slate-300 text-sm">URL</span>
                                        </label>
                                        <div className="md:col-span-2">
                                            <input
                                                type="text"
                                                className="input"
                                                placeholder="https://..."
                                                value={branding.support_url}
                                                onChange={(e) => setBranding(prev => ({ ...prev, support_url: e.target.value }))}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="md:col-span-2">
                                <h3 className="text-sm font-medium text-slate-300 mb-2">Footer</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-end">
                                    <div className="md:col-span-2">
                                        <label className="label">Texto del footer</label>
                                        <input
                                            type="text"
                                            className="input"
                                            placeholder="Ej: © {año} Tu Gimnasio. Todos los derechos reservados."
                                            value={branding.footer_text}
                                            onChange={(e) => setBranding(prev => ({ ...prev, footer_text: e.target.value }))}
                                        />
                                    </div>
                                    <label className="flex items-center gap-2 md:col-span-2">
                                        <input
                                            type="checkbox"
                                            checked={branding.show_powered_by}
                                            onChange={(e) => setBranding(prev => ({ ...prev, show_powered_by: e.target.checked }))}
                                        />
                                        <span className="text-slate-300 text-sm">Mostrar Powered by IronHub</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                        <button onClick={handleSaveBranding} disabled={saving} className="btn-primary flex items-center gap-2">
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            Guardar branding
                        </button>
                    </div>
                )}

                {activeSection === 'attendance' && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between gap-3">
                            <h2 className="text-lg font-semibold text-white">Política de asistencias</h2>
                            <button
                                className="btn-secondary flex items-center gap-2"
                                onClick={async () => {
                                    setAttendancePolicyLoading(true);
                                    try {
                                        const res = await api.getGymAttendancePolicy(gymId);
                                        if (res.ok && res.data?.ok) {
                                            setAttendanceAllowMultiple(Boolean(res.data.attendance_allow_multiple_per_day));
                                        }
                                    } finally {
                                        setAttendancePolicyLoading(false);
                                    }
                                }}
                                disabled={attendancePolicyLoading || attendancePolicySaving}
                            >
                                {attendancePolicyLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                Recargar
                            </button>
                        </div>

                        <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700 space-y-3">
                            <div className="text-sm text-slate-200">
                                Múltiples asistencias por día por usuario
                            </div>
                            <div className="flex items-center justify-between gap-3">
                                <div className="text-xs text-slate-400">
                                    Si está activado, el gym puede registrar múltiples check-ins en el mismo día (útil para salidas/entradas). Si está desactivado, queda limitado a 1/día.
                                </div>
                                <span className={`badge ${attendanceAllowMultiple ? 'badge-success' : 'badge-warning'}`}>
                                    {attendanceAllowMultiple ? 'Activado' : 'Desactivado'}
                                </span>
                            </div>
                            <button
                                className={`btn-primary w-full flex items-center justify-center gap-2 ${attendanceAllowMultiple ? 'bg-danger-600 hover:bg-danger-500' : ''}`}
                                disabled={attendancePolicySaving}
                                onClick={async () => {
                                    const next = !attendanceAllowMultiple;
                                    const ok = window.confirm(
                                        next
                                            ? 'Habilitar múltiples asistencias por día: impacta gestión/QR/estación. ¿Confirmar?'
                                            : 'Limitar a 1 asistencia por día: los check-ins extra del día quedarán “ya registrado”. ¿Confirmar?'
                                    );
                                    if (!ok) return;
                                    setAttendancePolicySaving(true);
                                    try {
                                        const res = await api.setGymAttendancePolicy(gymId, next);
                                        if (res.ok && res.data?.ok) {
                                            setAttendanceAllowMultiple(Boolean(res.data.attendance_allow_multiple_per_day));
                                            showMessage('Política actualizada');
                                        } else {
                                            showMessage(res.error || res.data?.error || 'Error al actualizar');
                                        }
                                    } finally {
                                        setAttendancePolicySaving(false);
                                    }
                                }}
                            >
                                {attendancePolicySaving ? <Loader2 className="w-4 h-4 animate-spin" /> : attendanceAllowMultiple ? <X className="w-4 h-4" /> : <Check className="w-4 h-4" />}
                                {attendanceAllowMultiple ? 'Desactivar' : 'Activar'}
                            </button>
                        </div>

                        <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700 space-y-3">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <div className="text-sm text-slate-200">Auditoría</div>
                                    <div className="text-xs text-slate-400">Cambios recientes (admin/owner) para este gym.</div>
                                </div>
                                <button
                                    className="btn-secondary flex items-center gap-2"
                                    onClick={async () => {
                                        setAuditLoading(true);
                                        try {
                                            const res = await api.getGymAudit(gymId, 200);
                                            if (res.ok && res.data?.ok) {
                                                setAuditItems((res.data.items || []) as AuditItem[]);
                                            }
                                        } finally {
                                            setAuditLoading(false);
                                        }
                                    }}
                                    disabled={auditLoading}
                                >
                                    {auditLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                                    Recargar
                                </button>
                            </div>

                            <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/40">
                                <table className="min-w-full text-sm">
                                    <thead className="bg-slate-900/60">
                                        <tr className="text-left text-slate-400">
                                            <th className="px-4 py-3">Fecha</th>
                                            <th className="px-4 py-3">Actor</th>
                                            <th className="px-4 py-3">Acción</th>
                                            <th className="px-4 py-3">Detalles</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {auditItems.length === 0 ? (
                                            <tr>
                                                <td className="px-4 py-6 text-slate-400" colSpan={4}>
                                                    Sin eventos.
                                                </td>
                                            </tr>
                                        ) : (
                                            auditItems.slice(0, 50).map((it) => (
                                                <tr key={String(it.id)} className="text-slate-200">
                                                    <td className="px-4 py-3 text-slate-300">{String(it.created_at || '').slice(0, 19).replace('T', ' ')}</td>
                                                    <td className="px-4 py-3">{String(it.actor_username || '—')}</td>
                                                    <td className="px-4 py-3">{String(it.action || '—')}</td>
                                                    <td className="px-4 py-3 text-slate-400 max-w-xl truncate">{String(it.details || '—')}</td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'modules' && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between gap-3">
                            <h2 className="text-lg font-semibold text-white">Módulos / Feature Flags</h2>
                            <button
                                onClick={saveFeatureFlags}
                                disabled={featureFlagsSaving || featureFlagsLoading}
                                className="btn-primary flex items-center gap-2"
                            >
                                {featureFlagsSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                Guardar
                            </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div>
                                <label className="label">Ámbito</label>
                                <select
                                    className="input"
                                    value={featureFlagsScope}
                                    onChange={(e) => {
                                        const v = e.target.value === 'branch' ? 'branch' : 'gym';
                                        setFeatureFlagsScope(v);
                                        if (v === 'gym') {
                                            setFeatureFlagsBranchId(0);
                                            void loadFeatureFlags('gym', 0);
                                        } else {
                                            const first = branches && branches.length ? Number(branches[0].id) : 0;
                                            setFeatureFlagsBranchId(first);
                                            if (first) void loadFeatureFlags('branch', first);
                                        }
                                    }}
                                >
                                    <option value="gym">Gimnasio</option>
                                    <option value="branch">Sucursal</option>
                                </select>
                            </div>
                            <div className="md:col-span-2">
                                <label className="label">Sucursal</label>
                                <select
                                    className="input"
                                    disabled={featureFlagsScope !== 'branch'}
                                    value={featureFlagsBranchId ? String(featureFlagsBranchId) : ''}
                                    onChange={(e) => {
                                        const bid = Number(e.target.value);
                                        setFeatureFlagsBranchId(bid);
                                        if (bid && featureFlagsScope === 'branch') void loadFeatureFlags('branch', bid);
                                    }}
                                >
                                    <option value="">Seleccionar…</option>
                                    {branches.map((b) => (
                                        <option key={b.id} value={String(b.id)}>
                                            {b.name} ({b.code})
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {featureFlagsLoading ? (
                            <div className="flex items-center gap-2 text-slate-400">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Cargando…
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {moduleOptions.map((m) => {
                                    const v = featureFlags.modules ? (featureFlags.modules as Record<string, unknown>)[m.key] : undefined;
                                    const checked = typeof v === 'boolean' ? v : Boolean(moduleDefaults[m.key]);
                                    return (
                                        <label key={m.key} className="flex items-center justify-between gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-700">
                                            <span className="text-sm text-slate-200">{m.label}</span>
                                            <input
                                                type="checkbox"
                                                checked={checked}
                                                onChange={(e) => {
                                                    const next = { ...(featureFlags.modules || {}) } as Record<string, boolean>;
                                                    next[m.key] = Boolean(e.target.checked);
                                                    setFeatureFlags({ ...(featureFlags || { modules: {} }), modules: next });
                                                }}
                                            />
                                        </label>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}

                {activeSection === 'routine_templates' && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between gap-3">
                            <h2 className="text-lg font-semibold text-white">Rutinas / Templates</h2>
                            <button
                                onClick={() => void reloadRoutineTemplates()}
                                disabled={routineTemplatesLoading}
                                className="btn-secondary flex items-center gap-2"
                            >
                                {routineTemplatesLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Actualizar'}
                            </button>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-3">
                                <div className="text-white font-medium">Asignar template al gimnasio</div>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    <div className="md:col-span-2">
                                        <label className="label">Template</label>
                                        <select
                                            className="input"
                                            value={assignTemplateId ? String(assignTemplateId) : ''}
                                            onChange={(e) => setAssignTemplateId(Number(e.target.value) || 0)}
                                        >
                                            <option value="">Seleccionar…</option>
                                            {routineTemplatesCatalog.map((t) => (
                                                <option key={t.id} value={String(t.id)}>
                                                    {t.nombre} {t.dias_semana ? `(${t.dias_semana} días)` : ''}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="label">Prioridad</label>
                                        <input
                                            className="input"
                                            type="number"
                                            value={String(assignTemplatePriority)}
                                            onChange={(e) => setAssignTemplatePriority(Number(e.target.value) || 0)}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="label">Notas</label>
                                    <input
                                        className="input"
                                        value={assignTemplateNotes}
                                        onChange={(e) => setAssignTemplateNotes(e.target.value)}
                                        placeholder="Opcional"
                                    />
                                </div>
                                <div className="flex items-center justify-between gap-3">
                                    <label className="flex items-center gap-2 text-slate-300 text-sm">
                                        <input
                                            type="checkbox"
                                            checked={assignTemplateActive}
                                            onChange={(e) => setAssignTemplateActive(Boolean(e.target.checked))}
                                        />
                                        Activo
                                    </label>
                                    <button
                                        className="btn-primary flex items-center gap-2"
                                        disabled={routineTemplatesLoading || !assignTemplateId}
                                        onClick={async () => {
                                            if (!assignTemplateId) return;
                                            setRoutineTemplatesLoading(true);
                                            try {
                                                const res = await api.assignGymRoutineTemplate(gymId, {
                                                    template_id: assignTemplateId,
                                                    activa: assignTemplateActive,
                                                    prioridad: assignTemplatePriority,
                                                    notas: assignTemplateNotes ? assignTemplateNotes : null,
                                                });
                                                if (res.ok && res.data?.ok) {
                                                    showMessage('Template asignado');
                                                    setAssignTemplateId(0);
                                                    setAssignTemplatePriority(0);
                                                    setAssignTemplateNotes('');
                                                    setAssignTemplateActive(true);
                                                    await reloadRoutineTemplates();
                                                } else {
                                                    showMessage(res.data?.error || res.error || 'Error');
                                                }
                                            } catch {
                                                showMessage('Error');
                                            } finally {
                                                setRoutineTemplatesLoading(false);
                                            }
                                        }}
                                    >
                                        <Plus className="w-4 h-4" />
                                        Asignar
                                    </button>
                                </div>
                                <div className="text-xs text-slate-500">
                                    Estos templates son la estructura del PDF/export y se eligen desde Gestión al crear rutinas o plantillas.
                                </div>
                            </div>

                            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-3">
                                <div className="text-white font-medium">Asignaciones actuales</div>
                                {routineTemplatesLoading ? (
                                    <div className="flex items-center gap-2 text-slate-400">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Cargando…
                                    </div>
                                ) : routineTemplateAssignments.length ? (
                                    <div className="space-y-2">
                                        {routineTemplateAssignments.map((a) => (
                                            <div key={a.assignment_id} className="p-3 rounded-lg bg-slate-900/40 border border-slate-800">
                                                <div className="flex items-center justify-between gap-3">
                                                    <div className="min-w-0">
                                                        <div className="text-white font-medium truncate">{a.nombre}</div>
                                                        <div className="text-xs text-slate-500">
                                                            {a.categoria || 'general'}
                                                            {a.dias_semana ? ` • ${a.dias_semana} días` : ''}
                                                            {a.publica ? ' • pública' : ''}
                                                        </div>
                                                    </div>
                                                    <button
                                                        className="btn-secondary flex items-center gap-2"
                                                        onClick={async () => {
                                                            if (!confirm('Quitar asignación?')) return;
                                                            setRoutineTemplatesLoading(true);
                                                            try {
                                                                const res = await api.deleteGymRoutineTemplateAssignment(gymId, a.assignment_id);
                                                                if (res.ok && res.data?.ok) {
                                                                    showMessage('Asignación eliminada');
                                                                    await reloadRoutineTemplates();
                                                                } else {
                                                                    showMessage(res.data?.error || res.error || 'Error');
                                                                }
                                                            } finally {
                                                                setRoutineTemplatesLoading(false);
                                                            }
                                                        }}
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>

                                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
                                                    <label className="flex items-center gap-2 text-slate-300 text-sm">
                                                        <input
                                                            type="checkbox"
                                                            checked={Boolean(a.activa)}
                                                            onChange={(e) => {
                                                                const v = Boolean(e.target.checked);
                                                                setRoutineTemplateAssignments((prev) =>
                                                                    prev.map((x) => (x.assignment_id === a.assignment_id ? { ...x, activa: v } : x))
                                                                );
                                                            }}
                                                        />
                                                        Activo
                                                    </label>
                                                    <div>
                                                        <label className="label">Prioridad</label>
                                                        <input
                                                            className="input"
                                                            type="number"
                                                            value={String(a.prioridad || 0)}
                                                            onChange={(e) => {
                                                                const v = Number(e.target.value) || 0;
                                                                setRoutineTemplateAssignments((prev) =>
                                                                    prev.map((x) => (x.assignment_id === a.assignment_id ? { ...x, prioridad: v } : x))
                                                                );
                                                            }}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="label">Notas</label>
                                                        <input
                                                            className="input"
                                                            value={String(a.notas || '')}
                                                            onChange={(e) => {
                                                                const v = e.target.value;
                                                                setRoutineTemplateAssignments((prev) =>
                                                                    prev.map((x) => (x.assignment_id === a.assignment_id ? { ...x, notas: v } : x))
                                                                );
                                                            }}
                                                        />
                                                    </div>
                                                </div>

                                                <div className="flex justify-end mt-3">
                                                    <button
                                                        className="btn-primary flex items-center gap-2"
                                                        disabled={routineTemplatesLoading}
                                                        onClick={async () => {
                                                            setRoutineTemplatesLoading(true);
                                                            try {
                                                                const cur = routineTemplateAssignments.find((x) => x.assignment_id === a.assignment_id);
                                                                if (!cur) return;
                                                                const res = await api.updateGymRoutineTemplateAssignment(gymId, cur.assignment_id, {
                                                                    activa: Boolean(cur.activa),
                                                                    prioridad: Number(cur.prioridad || 0),
                                                                    notas: cur.notas ?? null,
                                                                });
                                                                if (res.ok && res.data?.ok) {
                                                                    showMessage('Asignación actualizada');
                                                                    await reloadRoutineTemplates();
                                                                } else {
                                                                    showMessage(res.data?.error || res.error || 'Error');
                                                                }
                                                            } finally {
                                                                setRoutineTemplatesLoading(false);
                                                            }
                                                        }}
                                                    >
                                                        <Save className="w-4 h-4" />
                                                        Guardar
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-slate-500 text-sm">Sin asignaciones.</div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'entitlements' && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between gap-3">
                            <h2 className="text-lg font-semibold text-white">Accesos por tipo de cuota</h2>
                            <button
                                onClick={saveTipoCuotaEntitlements}
                                disabled={entSaving || entLoading || !entTipoCuotaId}
                                className="btn-primary flex items-center gap-2"
                            >
                                {entSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                Guardar
                            </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                                <label className="label">Tipo de cuota</label>
                                <select
                                    className="input"
                                    value={entTipoCuotaId ? String(entTipoCuotaId) : ''}
                                    onChange={(e) => {
                                        const id = Number(e.target.value);
                                        setEntTipoCuotaId(id);
                                        if (id) void loadTipoCuotaEntitlements(id);
                                    }}
                                >
                                    <option value="">Seleccionar…</option>
                                    {entTiposCuota.map((t) => (
                                        <option key={t.id} value={String(t.id)}>
                                            {t.nombre}{t.activo ? '' : ' (inactiva)'}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex items-end">
                                <label className="flex items-center gap-2 text-sm text-slate-300">
                                    <input
                                        type="checkbox"
                                        checked={entAllSucursales}
                                        onChange={(e) => {
                                            const checked = e.target.checked;
                                            setEntAllSucursales(checked);
                                            if (checked) setEntSelectedSucursales([]);
                                        }}
                                    />
                                    Todas las sucursales
                                </label>
                            </div>
                        </div>

                        {!entAllSucursales ? (
                            <div className="space-y-2">
                                <div className="text-xs text-slate-500">Sucursales habilitadas</div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                    {branches.map((b) => {
                                        const checked = entSelectedSucursales.includes(b.id);
                                        return (
                                            <label key={b.id} className="flex items-center justify-between gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-700">
                                                <span className="text-sm text-slate-200">{b.name}</span>
                                                <input
                                                    type="checkbox"
                                                    checked={checked}
                                                    onChange={(e) => {
                                                        const next = e.target.checked
                                                            ? Array.from(new Set([...entSelectedSucursales, b.id]))
                                                            : entSelectedSucursales.filter((x) => x !== b.id);
                                                        setEntSelectedSucursales(next.sort((a, c) => a - c));
                                                    }}
                                                />
                                            </label>
                                        );
                                    })}
                                </div>
                            </div>
                        ) : null}

                        <div className="space-y-3">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <div className="text-sm font-medium text-white">Permisos de clases (tipo de clase)</div>
                                    <div className="text-xs text-slate-500">Allowlist global o por sucursal.</div>
                                </div>
                                <select
                                    className="input max-w-xs"
                                    value={entScopeKey}
                                    onChange={(e) => setEntScopeKey(e.target.value)}
                                >
                                    <option value="0">Todas las sucursales</option>
                                    {branches.map((b) => (
                                        <option key={b.id} value={String(b.id)}>
                                            {b.name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {entLoading ? (
                                <div className="flex items-center gap-2 text-slate-400">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Cargando…
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                    {entTiposClases.filter((t) => t.activo).map((t) => {
                                        const selected = (entRulesByScope[entScopeKey] || []).includes(t.id);
                                        return (
                                            <label key={t.id} className="flex items-center justify-between gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-700">
                                                <span className="text-sm text-slate-200">{t.nombre}</span>
                                                <input
                                                    type="checkbox"
                                                    checked={selected}
                                                    onChange={() => {
                                                        setEntRulesByScope((prev) => {
                                                            const current = new Set(prev[entScopeKey] || []);
                                                            if (current.has(t.id)) current.delete(t.id);
                                                            else current.add(t.id);
                                                            return { ...prev, [entScopeKey]: Array.from(current).sort((a, c) => a - c) };
                                                        });
                                                    }}
                                                />
                                            </label>
                                        );
                                    })}
                                    {entTiposClases.filter((t) => t.activo).length === 0 ? (
                                        <div className="text-sm text-slate-500">No hay tipos de clase activos.</div>
                                    ) : null}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {activeSection === 'health' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Salud del Gimnasio</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-3 h-3 rounded-full bg-success-400" />
                                    <div>
                                        <div className="font-medium text-white">Base de datos</div>
                                        <div className="text-xs text-slate-500">{gym.db_name}</div>
                                    </div>
                                </div>
                                <span className="text-success-400 text-sm">OK</span>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className={`w-3 h-3 rounded-full ${gym.wa_configured ? 'bg-success-400' : 'bg-warning-400'}`} />
                                    <div>
                                        <div className="font-medium text-white">WhatsApp</div>
                                        <div className="text-xs text-slate-500">{gym.wa_configured ? 'Configurado' : 'Sin configurar'}</div>
                                    </div>
                                </div>
                                <span className={gym.wa_configured ? 'text-success-400 text-sm' : 'text-warning-400 text-sm'}>
                                    {gym.wa_configured ? 'OK' : 'Pendiente'}
                                </span>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className={`w-3 h-3 rounded-full ${gym.status === 'active' ? 'bg-success-400' : 'bg-danger-400'}`} />
                                    <div>
                                        <div className="font-medium text-white">Estado</div>
                                        <div className="text-xs text-slate-500">{gym.status}</div>
                                    </div>
                                </div>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-3 h-3 rounded-full bg-primary-400" />
                                    <div>
                                        <div className="font-medium text-white">WebApp URL</div>
                                        <a
                                            href={`https://${gym.subdominio}.${process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz'}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-primary-400 hover:text-primary-300"
                                        >
                                            {gym.subdominio}.{process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz'}
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <button onClick={refresh} disabled={loading} className="btn-secondary">Actualizar estado</button>
                    </div>
                )}

                {activeSection === 'password' && (
                    <div className="space-y-6">
                        <h2 className="text-lg font-semibold text-white">Cambiar Contraseña del Dueño</h2>
                        <div className="max-w-md space-y-4">
                            <div>
                                <label className="label">Nueva contraseña</label>
                                <input
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="input"
                                    placeholder="Mínimo 6 caracteres"
                                    minLength={6}
                                />
                            </div>
                            <button onClick={handleChangePassword} disabled={saving} className="btn-primary flex items-center gap-2">
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                                Actualizar contraseña
                            </button>
                        </div>
                        <div className="p-4 rounded-lg bg-warning-500/10 border border-warning-500/30 flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 text-warning-400 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-warning-400">
                                <p className="font-medium">Atención</p>
                                <p>Esta acción cambiará la contraseña de acceso del dueño al dashboard del gimnasio. El dueño deberá usar la nueva contraseña para ingresar.</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
