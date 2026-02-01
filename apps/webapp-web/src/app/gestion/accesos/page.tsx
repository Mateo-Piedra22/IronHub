'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { KeyRound, Loader2, Plus, RefreshCw, RotateCcw, ShieldAlert, Trash2 } from 'lucide-react';
import { Button, ConfirmModal, Input, Modal, Select, useToast } from '@/components/ui';
import { api, type AccessCredential, type AccessDevice, type AccessEvent, type Usuario, type Sucursal } from '@/lib/api';

type Tab = 'devices' | 'credentials' | 'events';

const credentialTypeOptions = [
    { value: 'fob', label: 'Llavero (fob)' },
    { value: 'card', label: 'Tarjeta' },
];

const unlockPresetOptions = [
    { value: '', label: '—' },
    { value: 'generic_http_get', label: 'Preset: Relé IP HTTP GET (genérico)' },
    { value: 'generic_http_post', label: 'Preset: Relé/PLC HTTP POST JSON (genérico)' },
    { value: 'shelly_gen1', label: 'Preset: Shelly Gen1 (GET /relay/0?turn=on)' },
    { value: 'shelly_gen2', label: 'Preset: Shelly Gen2 (RPC Switch.Set)' },
    { value: 'generic_tcp_open_nl', label: 'Preset: TCP texto "OPEN\\n" (genérico)' },
    { value: 'generic_serial_open_nl', label: 'Preset: Serial texto "OPEN\\n" (genérico)' },
];

const weekdayOptions = [
    { value: 1, label: 'Lun' },
    { value: 2, label: 'Mar' },
    { value: 3, label: 'Mié' },
    { value: 4, label: 'Jue' },
    { value: 5, label: 'Vie' },
    { value: 6, label: 'Sáb' },
    { value: 7, label: 'Dom' },
];

const eventTypeOptions = [
    { value: 'credential', label: 'Credencial (llavero genérico)' },
    { value: 'fob', label: 'Llavero (fob)' },
    { value: 'card', label: 'Tarjeta' },
    { value: 'dni', label: 'DNI' },
    { value: 'dni_pin', label: 'DNI + PIN' },
    { value: 'qr_token', label: 'QR / Token' },
    { value: 'manual_unlock', label: 'Apertura manual' },
    { value: 'enroll_credential', label: 'Enroll' },
];

type AllowedHoursRule = { days: number[]; start: string; end: string };

export default function AccesosPage() {
    const { success, error } = useToast();
    const [tab, setTab] = useState<Tab>('devices');

    const [loading, setLoading] = useState(true);
    const [devices, setDevices] = useState<AccessDevice[]>([]);
    const [events, setEvents] = useState<AccessEvent[]>([]);
    const [credentials, setCredentials] = useState<AccessCredential[]>([]);
    const [eventsPage, setEventsPage] = useState(1);
    const [sucursales, setSucursales] = useState<Sucursal[]>([]);
    const [deviceSucursalFilter, setDeviceSucursalFilter] = useState<string>('');
    const [accessTenant, setAccessTenant] = useState<string>('');

    const [createDeviceOpen, setCreateDeviceOpen] = useState(false);
    const [creatingDevice, setCreatingDevice] = useState(false);
    const [newDeviceName, setNewDeviceName] = useState('');
    const [newDeviceSucursalId, setNewDeviceSucursalId] = useState<string>('');
    const [newDeviceUnlockPreset, setNewDeviceUnlockPreset] = useState<string>('');
    const [newDeviceUnlockType, setNewDeviceUnlockType] = useState('http_get');
    const [newDeviceUnlockUrl, setNewDeviceUnlockUrl] = useState('');
    const [newDeviceUnlockMs, setNewDeviceUnlockMs] = useState('2500');
    const [newDeviceUnlockTcpHost, setNewDeviceUnlockTcpHost] = useState('');
    const [newDeviceUnlockTcpPort, setNewDeviceUnlockTcpPort] = useState('9100');
    const [newDeviceUnlockTcpPayload, setNewDeviceUnlockTcpPayload] = useState('');
    const [newDeviceUnlockSerialPort, setNewDeviceUnlockSerialPort] = useState('');
    const [newDeviceUnlockSerialBaud, setNewDeviceUnlockSerialBaud] = useState('9600');
    const [newDeviceUnlockSerialPayload, setNewDeviceUnlockSerialPayload] = useState('');
    const [newDeviceAllowManual, setNewDeviceAllowManual] = useState(true);
    const [newDeviceManualHotkey, setNewDeviceManualHotkey] = useState('F10');
    const [newDeviceAllowRemoteUnlock, setNewDeviceAllowRemoteUnlock] = useState(false);
    const [newDeviceStationAutoUnlock, setNewDeviceStationAutoUnlock] = useState(false);
    const [newDeviceStationUnlockMs, setNewDeviceStationUnlockMs] = useState('2500');
    const [newDeviceTimezone, setNewDeviceTimezone] = useState('America/Argentina/Buenos_Aires');
    const [newDeviceAllowedHours, setNewDeviceAllowedHours] = useState<AllowedHoursRule[]>([]);
    const [newDeviceRestrictEventTypes, setNewDeviceRestrictEventTypes] = useState(false);
    const [newDeviceAllowedEventTypes, setNewDeviceAllowedEventTypes] = useState<Record<string, boolean>>({
        credential: true,
        fob: true,
        card: true,
        dni: true,
        dni_pin: true,
        qr_token: true,
        manual_unlock: true,
        enroll_credential: true,
    });
    const [newDeviceDniRequiresPin, setNewDeviceDniRequiresPin] = useState(false);
    const [newDeviceAntiPassbackSec, setNewDeviceAntiPassbackSec] = useState('0');
    const [newDeviceMaxEventsPerMin, setNewDeviceMaxEventsPerMin] = useState('0');
    const [newDeviceRateLimitWindowSec, setNewDeviceRateLimitWindowSec] = useState('60');

    const [editDeviceOpen, setEditDeviceOpen] = useState(false);
    const [editDevice, setEditDevice] = useState<AccessDevice | null>(null);
    const [editName, setEditName] = useState('');
    const [editEnabled, setEditEnabled] = useState(true);
    const [editSucursalId, setEditSucursalId] = useState<string>('');
    const [editUnlockPreset, setEditUnlockPreset] = useState<string>('');
    const [editUnlockType, setEditUnlockType] = useState('http_get');
    const [editUnlockUrl, setEditUnlockUrl] = useState('');
    const [editUnlockMs, setEditUnlockMs] = useState('2500');
    const [editUnlockTcpHost, setEditUnlockTcpHost] = useState('');
    const [editUnlockTcpPort, setEditUnlockTcpPort] = useState('9100');
    const [editUnlockTcpPayload, setEditUnlockTcpPayload] = useState('');
    const [editUnlockSerialPort, setEditUnlockSerialPort] = useState('');
    const [editUnlockSerialBaud, setEditUnlockSerialBaud] = useState('9600');
    const [editUnlockSerialPayload, setEditUnlockSerialPayload] = useState('');
    const [editAllowManual, setEditAllowManual] = useState(true);
    const [editManualHotkey, setEditManualHotkey] = useState('F10');
    const [editAllowRemoteUnlock, setEditAllowRemoteUnlock] = useState(false);
    const [editStationAutoUnlock, setEditStationAutoUnlock] = useState(false);
    const [editStationUnlockMs, setEditStationUnlockMs] = useState('2500');
    const [editTimezone, setEditTimezone] = useState('America/Argentina/Buenos_Aires');
    const [editAllowedHours, setEditAllowedHours] = useState<AllowedHoursRule[]>([]);
    const [editRestrictEventTypes, setEditRestrictEventTypes] = useState(false);
    const [editAllowedEventTypes, setEditAllowedEventTypes] = useState<Record<string, boolean>>({
        credential: true,
        fob: true,
        card: true,
        dni: true,
        dni_pin: true,
        qr_token: true,
        manual_unlock: true,
        enroll_credential: true,
    });
    const [editDniRequiresPin, setEditDniRequiresPin] = useState(false);
    const [editAntiPassbackSec, setEditAntiPassbackSec] = useState('0');
    const [editMaxEventsPerMin, setEditMaxEventsPerMin] = useState('0');
    const [editRateLimitWindowSec, setEditRateLimitWindowSec] = useState('60');
    const [savingDevice, setSavingDevice] = useState(false);

    const [pairingInfo, setPairingInfo] = useState<{
        open: boolean;
        device_public_id?: string;
        pairing_code?: string;
        expires_at?: string;
        device_name?: string;
        sucursal_id?: number | null;
    }>({ open: false });

    const [credUserSearch, setCredUserSearch] = useState('');
    const [credUserResults, setCredUserResults] = useState<Usuario[]>([]);
    const [credSelectedUser, setCredSelectedUser] = useState<Usuario | null>(null);
    const [credValue, setCredValue] = useState('');
    const [credType, setCredType] = useState('fob');
    const [credLabel, setCredLabel] = useState('');
    const [creatingCred, setCreatingCred] = useState(false);
    const [deleteCredState, setDeleteCredState] = useState<{ open: boolean; id?: number }>({ open: false });
    const [deletingCred, setDeletingCred] = useState(false);
    const [remoteUnlockState, setRemoteUnlockState] = useState<{ open: boolean; device?: AccessDevice }>({ open: false });
    const [remoteUnlocking, setRemoteUnlocking] = useState(false);
    const [deviceCommandsState, setDeviceCommandsState] = useState<{ open: boolean; device?: AccessDevice }>({ open: false });
    const [deviceCommands, setDeviceCommands] = useState<any[]>([]);
    const [loadingDeviceCommands, setLoadingDeviceCommands] = useState(false);

    const filteredDevices = useMemo(() => {
        if (!deviceSucursalFilter) return devices;
        return devices.filter((d) => String(d.sucursal_id ?? '') === String(deviceSucursalFilter));
    }, [devices, deviceSucursalFilter]);

    const pairingBlock = useMemo(() => {
        if (!pairingInfo.device_public_id || !pairingInfo.pairing_code) return '';
        const webUrl = typeof window !== 'undefined' ? window.location.origin : '';
        const apiUrl =
            (process.env.NEXT_PUBLIC_API_URL || '').trim() ||
            `https://api.${(process.env.NEXT_PUBLIC_TENANT_DOMAIN || 'ironhub.motiona.xyz').trim()}`;
        const sid = typeof pairingInfo.sucursal_id === 'number' ? pairingInfo.sucursal_id : null;
        const sname = sid != null ? (sucursales.find((s) => Number(s.id) === Number(sid))?.nombre || '') : '';
        const sucLabel = sid != null ? `${sname ? `${sname} ` : ''}(#${sid})` : '—';
        const lines = [
            'IRONHUB · PAIRING (copiar/pegar en el Access Agent)',
            '',
            `Tenant: ${accessTenant || '—'}`,
            `Base URL API: ${apiUrl || '—'}`,
            `Web URL: ${webUrl || '—'}`,
            `Sucursal: ${sucLabel}`,
            `Device: ${pairingInfo.device_name || '—'}`,
            '',
            `Device ID: ${pairingInfo.device_public_id}`,
            `Código: ${pairingInfo.pairing_code}`,
            `Expira: ${pairingInfo.expires_at || '—'}`,
        ];
        return lines.join('\n');
    }, [pairingInfo, accessTenant, sucursales]);

    const isDeviceOnline = useCallback((d: AccessDevice) => {
        const ls = (d as any).last_seen_at ? String((d as any).last_seen_at) : '';
        if (!ls) return false;
        const t = Date.parse(ls);
        if (!Number.isFinite(t)) return false;
        return Date.now() - t < 90_000;
    }, []);

    const getEnrollMode = useCallback((d: AccessDevice) => {
        const cfg: any = (d as any).config && typeof (d as any).config === 'object' ? (d as any).config : {};
        const em = cfg?.enroll_mode && typeof cfg.enroll_mode === 'object' ? cfg.enroll_mode : null;
        return em && em.enabled ? em : null;
    }, []);

    const loadAll = useCallback(async () => {
        setLoading(true);
        try {
            const [d, c, s] = await Promise.all([api.listAccessDevices(), api.listAccessCredentials(), api.getSucursales()]);
            if (d.ok && d.data?.ok) setDevices(d.data.items || []);
            if (c.ok && c.data?.ok) setCredentials(c.data.items || []);
            if (s.ok && s.data?.ok && Array.isArray(s.data.items)) setSucursales(s.data.items || []);
            try {
                const b = await api.accessBootstrap();
                if (b.ok && b.data?.ok) setAccessTenant(String(b.data.tenant || ''));
            } catch {
            }
            const ev = await api.listAccessEvents({ page: 1, limit: 50 });
            if (ev.ok && ev.data?.ok) setEvents(ev.data.items || []);
            setEventsPage(1);
        } catch {
            error('Error cargando accesos');
        } finally {
            setLoading(false);
        }
    }, [error]);

    useEffect(() => {
        loadAll();
    }, [loadAll]);

    const loadEvents = useCallback(async (page: number) => {
        const p = Math.max(1, page);
        const res = await api.listAccessEvents({ page: p, limit: 50 });
        if (res.ok && res.data?.ok) {
            setEvents(res.data.items || []);
            setEventsPage(p);
        }
    }, []);

    useEffect(() => {
        if (tab === 'events') {
            loadEvents(eventsPage).catch(() => {});
        }
    }, [tab, eventsPage, loadEvents]);

    const createDevice = async () => {
        const name = newDeviceName.trim();
        if (!name) return;
        setCreatingDevice(true);
        try {
            const sid = newDeviceSucursalId.trim() ? Number(newDeviceSucursalId.trim()) : null;
            const payload: any = { name, sucursal_id: Number.isFinite(sid) ? sid : null };
            const ms = Number(newDeviceUnlockMs.trim());
            const stationMs = Number(newDeviceStationUnlockMs.trim());
            const tcpPort = Number(newDeviceUnlockTcpPort.trim());
            const serialBaud = Number(newDeviceUnlockSerialBaud.trim());
            const unlockType = (newDeviceUnlockType || 'http_get').trim().toLowerCase();
            let unlockProfile: any = { type: 'none' };
            if (unlockType === 'http_get' || unlockType === 'http_post_json') {
                unlockProfile = newDeviceUnlockUrl.trim() ? { type: unlockType, url: newDeviceUnlockUrl.trim() } : { type: 'none' };
            } else if (unlockType === 'tcp') {
                unlockProfile = {
                    type: 'tcp',
                    host: newDeviceUnlockTcpHost.trim(),
                    port: Number.isFinite(tcpPort) ? Math.max(1, Math.min(tcpPort, 65535)) : 9100,
                    payload: newDeviceUnlockTcpPayload,
                };
            } else if (unlockType === 'serial') {
                unlockProfile = {
                    type: 'serial',
                    serial_port: newDeviceUnlockSerialPort.trim(),
                    serial_baud: Number.isFinite(serialBaud) ? Math.max(1200, Math.min(serialBaud, 921600)) : 9600,
                    payload: newDeviceUnlockSerialPayload,
                };
            }

            const config: any = {
                allow_manual_unlock: Boolean(newDeviceAllowManual),
                manual_hotkey: newDeviceManualHotkey.trim() || 'F10',
                allow_remote_unlock: Boolean(newDeviceAllowRemoteUnlock),
                station_auto_unlock: Boolean(newDeviceStationAutoUnlock),
                station_unlock_ms: Number.isFinite(stationMs) ? Math.max(250, Math.min(stationMs, 15000)) : 2500,
                unlock_ms: Number.isFinite(ms) ? Math.max(250, Math.min(ms, 15000)) : 2500,
                unlock_profile: unlockProfile,
            };

            const tz = String(newDeviceTimezone || '').trim();
            if (tz) config.timezone = tz;

            const ah = (newDeviceAllowedHours || [])
                .map((r) => ({
                    days: Array.isArray(r.days) ? r.days.filter((d) => Number.isFinite(d) && d >= 1 && d <= 7) : [],
                    start: String(r.start || '').trim(),
                    end: String(r.end || '').trim(),
                }))
                .filter((r) => r.days.length > 0 && r.start && r.end);
            if (ah.length > 0) config.allowed_hours = ah;

            if (newDeviceRestrictEventTypes) {
                const sel = Object.entries(newDeviceAllowedEventTypes || {})
                    .filter(([, v]) => Boolean(v))
                    .map(([k]) => String(k));
                config.allowed_event_types = sel;
            }

            config.dni_requires_pin = Boolean(newDeviceDniRequiresPin);

            const apb = Number(newDeviceAntiPassbackSec.trim());
            if (Number.isFinite(apb) && apb > 0) config.anti_passback_seconds = Math.max(5, Math.min(apb, 86400));

            const maxpm = Number(newDeviceMaxEventsPerMin.trim());
            const win = Number(newDeviceRateLimitWindowSec.trim());
            if (Number.isFinite(maxpm) && maxpm > 0) {
                config.max_events_per_minute = Math.max(1, Math.min(maxpm, 600));
                config.rate_limit_window_seconds = Number.isFinite(win) && win > 0 ? Math.max(5, Math.min(win, 300)) : 60;
            }

            payload.config = config;
            const res = await api.createAccessDevice(payload);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo crear');
            success('Device creado');
            setCreateDeviceOpen(false);
            setNewDeviceName('');
            setNewDeviceSucursalId('');
            setNewDeviceUnlockPreset('');
            setNewDeviceUnlockType('http_get');
            setNewDeviceUnlockUrl('');
            setNewDeviceUnlockMs('2500');
            setNewDeviceUnlockTcpHost('');
            setNewDeviceUnlockTcpPort('9100');
            setNewDeviceUnlockTcpPayload('');
            setNewDeviceUnlockSerialPort('');
            setNewDeviceUnlockSerialBaud('9600');
            setNewDeviceUnlockSerialPayload('');
            setNewDeviceAllowManual(true);
            setNewDeviceManualHotkey('F10');
            setNewDeviceAllowRemoteUnlock(false);
            setNewDeviceStationAutoUnlock(false);
            setNewDeviceStationUnlockMs('2500');
            setNewDeviceTimezone('America/Argentina/Buenos_Aires');
            setNewDeviceAllowedHours([]);
            setNewDeviceRestrictEventTypes(false);
            setNewDeviceAllowedEventTypes({
                credential: true,
                fob: true,
                card: true,
                dni: true,
                dni_pin: true,
                qr_token: true,
                manual_unlock: true,
                enroll_credential: true,
            });
            setNewDeviceDniRequiresPin(false);
            setNewDeviceAntiPassbackSec('0');
            setNewDeviceMaxEventsPerMin('0');
            setNewDeviceRateLimitWindowSec('60');
            setPairingInfo({
                open: true,
                device_public_id: res.data.device?.device_public_id,
                pairing_code: res.data.pairing_code,
                expires_at: res.data.pairing_expires_at,
                device_name: res.data.device?.name,
                sucursal_id: typeof res.data.device?.sucursal_id === 'number' ? res.data.device.sucursal_id : null,
            });
            await loadAll();
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setCreatingDevice(false);
        }
    };

    const openEditDevice = (d: AccessDevice) => {
        const cfg: any = (d as any).config && typeof (d as any).config === 'object' ? (d as any).config : {};
        const profile = cfg.unlock_profile && typeof cfg.unlock_profile === 'object' ? cfg.unlock_profile : {};
        const ptype = String(profile.type || 'none').toLowerCase();
        setEditDevice(d);
        setEditName(String(d.name || ''));
        setEditEnabled(Boolean(d.enabled));
        setEditSucursalId(d.sucursal_id != null ? String(d.sucursal_id) : '');
        setEditUnlockPreset('');
        setEditUnlockType(ptype === 'http_post_json' || ptype === 'tcp' || ptype === 'serial' || ptype === 'none' ? ptype : 'http_get');
        setEditUnlockUrl(String(profile.url || ''));
        setEditUnlockTcpHost(String(profile.host || ''));
        setEditUnlockTcpPort(String(profile.port || 9100));
        setEditUnlockTcpPayload(String(profile.payload || ''));
        setEditUnlockSerialPort(String(profile.serial_port || ''));
        setEditUnlockSerialBaud(String(profile.serial_baud || 9600));
        setEditUnlockSerialPayload(String(profile.payload || ''));
        setEditUnlockMs(String(cfg.unlock_ms ?? 2500));
        setEditAllowManual(Boolean(cfg.allow_manual_unlock ?? true));
        setEditManualHotkey(String(cfg.manual_hotkey || 'F10'));
        setEditAllowRemoteUnlock(Boolean(cfg.allow_remote_unlock ?? false));
        setEditStationAutoUnlock(Boolean(cfg.station_auto_unlock ?? false));
        setEditStationUnlockMs(String(cfg.station_unlock_ms ?? cfg.unlock_ms ?? 2500));
        setEditTimezone(String(cfg.timezone || 'America/Argentina/Buenos_Aires'));
        const ah: AllowedHoursRule[] = Array.isArray(cfg.allowed_hours)
            ? (cfg.allowed_hours || []).map((r: any) => ({
                  days: Array.isArray(r?.days) ? (r.days as any[]).map((x) => Number(x)).filter((x) => Number.isFinite(x) && x >= 1 && x <= 7) : [],
                  start: String(r?.start || ''),
                  end: String(r?.end || ''),
              }))
            : [];
        setEditAllowedHours(ah.filter((r) => r.days.length > 0 && r.start && r.end));

        const aet: any[] = Array.isArray(cfg.allowed_event_types) ? cfg.allowed_event_types : [];
        if (Array.isArray(aet) && aet.length > 0) {
            setEditRestrictEventTypes(true);
            const map: Record<string, boolean> = {};
            for (const o of eventTypeOptions) map[o.value] = false;
            for (const x of aet) map[String(x)] = true;
            setEditAllowedEventTypes(map);
        } else {
            setEditRestrictEventTypes(false);
            const map: Record<string, boolean> = {};
            for (const o of eventTypeOptions) map[o.value] = true;
            setEditAllowedEventTypes(map);
        }

        setEditDniRequiresPin(Boolean(cfg.dni_requires_pin ?? false));
        setEditAntiPassbackSec(String(cfg.anti_passback_seconds ?? 0));
        setEditMaxEventsPerMin(String(cfg.max_events_per_minute ?? 0));
        setEditRateLimitWindowSec(String(cfg.rate_limit_window_seconds ?? 60));
        setEditDeviceOpen(true);
    };

    const saveDevice = async () => {
        if (!editDevice) return;
        setSavingDevice(true);
        try {
            const sid = editSucursalId.trim() ? Number(editSucursalId.trim()) : null;
            const ms = Number(editUnlockMs.trim());
            const stationMs = Number(editStationUnlockMs.trim());
            const tcpPort = Number(editUnlockTcpPort.trim());
            const serialBaud = Number(editUnlockSerialBaud.trim());
            const unlockType = (editUnlockType || 'http_get').trim().toLowerCase();
            let unlockProfile: any = { type: 'none' };
            if (unlockType === 'http_get' || unlockType === 'http_post_json') {
                unlockProfile = editUnlockUrl.trim() ? { type: unlockType, url: editUnlockUrl.trim() } : { type: 'none' };
            } else if (unlockType === 'tcp') {
                unlockProfile = {
                    type: 'tcp',
                    host: editUnlockTcpHost.trim(),
                    port: Number.isFinite(tcpPort) ? Math.max(1, Math.min(tcpPort, 65535)) : 9100,
                    payload: editUnlockTcpPayload,
                };
            } else if (unlockType === 'serial') {
                unlockProfile = {
                    type: 'serial',
                    serial_port: editUnlockSerialPort.trim(),
                    serial_baud: Number.isFinite(serialBaud) ? Math.max(1200, Math.min(serialBaud, 921600)) : 9600,
                    payload: editUnlockSerialPayload,
                };
            }
            const payload: any = {
                name: editName.trim() || editDevice.name,
                enabled: Boolean(editEnabled),
                sucursal_id: Number.isFinite(sid) ? sid : null,
                config: {
                    allow_manual_unlock: Boolean(editAllowManual),
                    manual_hotkey: editManualHotkey.trim() || 'F10',
                    allow_remote_unlock: Boolean(editAllowRemoteUnlock),
                    station_auto_unlock: Boolean(editStationAutoUnlock),
                    station_unlock_ms: Number.isFinite(stationMs) ? Math.max(250, Math.min(stationMs, 15000)) : 2500,
                    unlock_ms: Number.isFinite(ms) ? Math.max(250, Math.min(ms, 15000)) : 2500,
                    unlock_profile: unlockProfile,
                },
            };
            const cfg = payload.config;
            const tz = String(editTimezone || '').trim();
            if (tz) cfg.timezone = tz;

            const ah = (editAllowedHours || [])
                .map((r) => ({
                    days: Array.isArray(r.days) ? r.days.filter((d) => Number.isFinite(d) && d >= 1 && d <= 7) : [],
                    start: String(r.start || '').trim(),
                    end: String(r.end || '').trim(),
                }))
                .filter((r) => r.days.length > 0 && r.start && r.end);
            if (ah.length > 0) cfg.allowed_hours = ah;
            else delete cfg.allowed_hours;

            if (editRestrictEventTypes) {
                const sel = Object.entries(editAllowedEventTypes || {})
                    .filter(([, v]) => Boolean(v))
                    .map(([k]) => String(k));
                cfg.allowed_event_types = sel;
            } else {
                delete cfg.allowed_event_types;
            }

            cfg.dni_requires_pin = Boolean(editDniRequiresPin);

            const apb = Number(editAntiPassbackSec.trim());
            if (Number.isFinite(apb) && apb > 0) cfg.anti_passback_seconds = Math.max(5, Math.min(apb, 86400));
            else delete cfg.anti_passback_seconds;

            const maxpm = Number(editMaxEventsPerMin.trim());
            const win = Number(editRateLimitWindowSec.trim());
            if (Number.isFinite(maxpm) && maxpm > 0) {
                cfg.max_events_per_minute = Math.max(1, Math.min(maxpm, 600));
                cfg.rate_limit_window_seconds = Number.isFinite(win) && win > 0 ? Math.max(5, Math.min(win, 300)) : 60;
            } else {
                delete cfg.max_events_per_minute;
                delete cfg.rate_limit_window_seconds;
            }
            const res = await api.updateAccessDevice(editDevice.id, payload);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo guardar');
            success('Device actualizado');
            setEditDeviceOpen(false);
            setEditDevice(null);
            await loadAll();
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setSavingDevice(false);
        }
    };

    const rotatePairing = async (d: AccessDevice) => {
        try {
            const res = await api.rotateAccessDevicePairing(d.id);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo rotar');
            setPairingInfo({
                open: true,
                device_public_id: d.device_public_id,
                pairing_code: res.data.pairing_code,
                expires_at: res.data.pairing_expires_at,
                device_name: d.name,
                sucursal_id: d.sucursal_id ?? null,
            });
            success('Pairing rotado');
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        }
    };

    const revokeToken = async (deviceId: number) => {
        try {
            const res = await api.revokeAccessDeviceToken(deviceId);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo revocar');
            success('Token revocado');
            await loadAll();
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        }
    };

    const confirmRemoteUnlock = async () => {
        const d = remoteUnlockState.device;
        if (!d) return;
        setRemoteUnlocking(true);
        try {
            const cfg: any = (d as any).config && typeof (d as any).config === 'object' ? (d as any).config : {};
            const unlockMs = Number(cfg.unlock_ms ?? 2500);
            const requestId =
                typeof (globalThis as any)?.crypto?.randomUUID === 'function'
                    ? (globalThis as any).crypto.randomUUID()
                    : `${Date.now()}_${Math.random().toString(16).slice(2)}`;
            const res = await api.remoteUnlockAccessDevice(d.id, {
                unlock_ms: Number.isFinite(unlockMs) ? unlockMs : 2500,
                reason: 'gestion_remote_unlock',
                request_id: requestId,
            });
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo enviar');
            success('Unlock enviado');
            setRemoteUnlockState({ open: false });
            await loadAll();
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setRemoteUnlocking(false);
        }
    };

    const openDeviceCommands = async (d: AccessDevice) => {
        setDeviceCommandsState({ open: true, device: d });
        setLoadingDeviceCommands(true);
        try {
            const res = await api.listAccessDeviceCommands(d.id, { limit: 50 });
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudieron cargar comandos');
            setDeviceCommands(res.data.items || []);
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
            setDeviceCommands([]);
        } finally {
            setLoadingDeviceCommands(false);
        }
    };

    const cancelCommand = async (deviceId: number, commandId: number) => {
        try {
            const res = await api.cancelAccessDeviceCommand(deviceId, commandId);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo cancelar');
            success('Comando cancelado');
            const cur = deviceCommandsState.device;
            if (cur && cur.id === deviceId) {
                const r2 = await api.listAccessDeviceCommands(deviceId, { limit: 50 });
                if (r2.ok && r2.data?.ok) setDeviceCommands(r2.data.items || []);
            }
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        }
    };

    const cancelEnroll = async (deviceId: number) => {
        try {
            const res = await api.clearAccessDeviceEnrollment(deviceId);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo cancelar');
            success('Enroll cancelado');
            await loadAll();
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        }
    };

    useEffect(() => {
        const t = setTimeout(async () => {
            const q = credUserSearch.trim();
            if (q.length < 2) {
                setCredUserResults([]);
                return;
            }
            const res = await api.getUsuarios({ search: q, limit: 10 });
            if (res.ok && res.data?.usuarios) setCredUserResults(res.data.usuarios || []);
        }, 250);
        return () => clearTimeout(t);
    }, [credUserSearch]);

    const createCredential = async () => {
        if (!credSelectedUser) return;
        const value = credValue.trim();
        if (!value) return;
        setCreatingCred(true);
        try {
            const res = await api.createAccessCredential({
                usuario_id: credSelectedUser.id,
                credential_type: credType,
                value,
                label: credLabel.trim() || null,
            });
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo crear');
            success('Credencial creada');
            setCredValue('');
            setCredLabel('');
            const c = await api.listAccessCredentials();
            if (c.ok && c.data?.ok) setCredentials(c.data.items || []);
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setCreatingCred(false);
        }
    };

    const deleteCredential = async () => {
        if (!deleteCredState.id) return;
        setDeletingCred(true);
        try {
            const res = await api.deleteAccessCredential(deleteCredState.id);
            if (!res.ok || !res.data?.ok) throw new Error(res.error || 'No se pudo eliminar');
            success('Credencial eliminada');
            setDeleteCredState({ open: false });
            const c = await api.listAccessCredentials();
            if (c.ok && c.data?.ok) setCredentials(c.data.items || []);
        } catch (e) {
            error(e instanceof Error ? e.message : 'Error');
        } finally {
            setDeletingCred(false);
        }
    };

    const header = useMemo(() => {
        return (
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center">
                    <KeyRound className="w-5 h-5" />
                </div>
                <div className="flex-1">
                    <h1 className="text-xl font-semibold text-white">Accesos</h1>
                    <p className="text-sm text-slate-400">Dispositivos, credenciales y eventos de molinete/puerta.</p>
                </div>
                <Button variant="secondary" onClick={loadAll} leftIcon={<RefreshCw className="w-4 h-4" />} disabled={loading}>
                    Refrescar
                </Button>
            </div>
        );
    }, [loadAll, loading]);

    return (
        <div className="space-y-6">
            {header}

            <div className="card p-3 flex flex-wrap gap-2">
                <Button variant={tab === 'devices' ? 'primary' : 'secondary'} onClick={() => setTab('devices')}>
                    Dispositivos
                </Button>
                <Button variant={tab === 'credentials' ? 'primary' : 'secondary'} onClick={() => setTab('credentials')}>
                    Credenciales
                </Button>
                <Button variant={tab === 'events' ? 'primary' : 'secondary'} onClick={() => setTab('events')}>
                    Eventos
                </Button>
            </div>

            {loading ? (
                <div className="card p-10 flex items-center justify-center text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando…
                </div>
            ) : null}

            {!loading && tab === 'devices' ? (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="text-sm text-slate-400">
                                Devices ({filteredDevices.length}/{devices.length})
                            </div>
                            <Select
                                value={deviceSucursalFilter}
                                onChange={(e) => setDeviceSucursalFilter(e.target.value)}
                                options={[
                                    { value: '', label: 'Todas las sucursales' },
                                    ...(sucursales || []).map((s) => ({ value: String(s.id), label: `${s.nombre} (#${s.id})` })),
                                ]}
                            />
                        </div>
                        <Button onClick={() => setCreateDeviceOpen(true)} leftIcon={<Plus className="w-4 h-4" />}>
                            Nuevo device
                        </Button>
                    </div>
                    <div className="space-y-2">
                        {filteredDevices.map((d) => {
                            const online = isDeviceOnline(d);
                            const enroll = getEnrollMode(d);
                            const cfg: any = (d as any).config && typeof (d as any).config === 'object' ? (d as any).config : {};
                            const rt = cfg?.runtime_status && typeof cfg.runtime_status === 'object' ? cfg.runtime_status : null;
                            const rtAt = rt?.updated_at ? Date.parse(String(rt.updated_at)) : NaN;
                            const rtFresh = Number.isFinite(rtAt) ? Date.now() - rtAt < 20_000 : false;
                            const enrollReady = Boolean(rt?.enroll_ready) && rtFresh;
                            const lt = rt?.last_test && typeof rt.last_test === 'object' ? rt.last_test : null;
                            const ltAt = lt?.at ? String(lt.at) : '';
                            const ltLabel = lt?.kind ? String(lt.kind) : '';
                            const ltOk = lt ? Boolean(lt.ok) : false;
                            const rtInput = rt ? `${rt.input_source || ''}${rt.input_protocol ? `/${rt.input_protocol}` : ''}`.trim() : '';
                            const rtSerial = rt?.serial_port ? String(rt.serial_port) : '';
                            const rtAgent = rt?.agent_version ? String(rt.agent_version) : '';
                            const rtQ = typeof rt?.offline_queue_lines === 'number' ? Number(rt.offline_queue_lines) : NaN;
                            const rtQB = typeof rt?.offline_queue_bytes === 'number' ? Number(rt.offline_queue_bytes) : NaN;
                            const canRemoteUnlock = Boolean(cfg?.allow_remote_unlock);
                            return (
                                <div key={d.id} className="card p-4 flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="text-white font-semibold flex items-center gap-2">
                                            <span className="truncate">{d.name}</span>
                                            {online ? <span className="badge badge-success">online</span> : <span className="badge badge-danger">offline</span>}
                                            {enrollReady ? <span className="badge badge-success">ready</span> : null}
                                            {enroll ? (
                                                <span className="badge badge-warning">
                                                    ENROLL #{enroll.usuario_id} {String(enroll.credential_type || '').toUpperCase()}
                                                </span>
                                            ) : null}
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">
                                            sucursal_id {d.sucursal_id ?? '—'} • device_id {d.device_public_id} • {d.enabled ? 'enabled' : 'disabled'}
                                            {(d as any).last_seen_at ? ` • last_seen ${(d as any).last_seen_at}` : ''}
                                            {ltLabel ? ` • last_test ${ltLabel} ${ltOk ? 'ok' : 'fail'} ${ltAt ? `@ ${ltAt}` : ''}` : ''}
                                            {rtInput ? ` • input ${rtInput}` : ''}
                                            {rtSerial ? ` • serial ${rtSerial}` : ''}
                                            {rtAgent ? ` • agent v${rtAgent}` : ''}
                                            {Number.isFinite(rtQ) ? ` • offline_queue ${rtQ}${Number.isFinite(rtQB) ? ` (${rtQB} bytes)` : ''}` : ''}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {enroll ? (
                                            <Button variant="secondary" onClick={() => cancelEnroll(d.id)} leftIcon={<ShieldAlert className="w-4 h-4" />}>
                                                Cancelar enroll
                                            </Button>
                                        ) : null}
                                        {canRemoteUnlock ? (
                                            <Button
                                                onClick={() => setRemoteUnlockState({ open: true, device: d })}
                                                disabled={!online}
                                                leftIcon={<KeyRound className="w-4 h-4" />}
                                            >
                                                Abrir
                                            </Button>
                                        ) : null}
                                        <Button variant="secondary" onClick={() => openDeviceCommands(d)}>
                                            Comandos
                                        </Button>
                                        <Button variant="secondary" onClick={() => openEditDevice(d)}>
                                            Editar
                                        </Button>
                                        <Button
                                            variant="secondary"
                                            onClick={() => rotatePairing(d)}
                                            leftIcon={<RotateCcw className="w-4 h-4" />}
                                        >
                                            Pairing
                                        </Button>
                                        <Button variant="secondary" onClick={() => revokeToken(d.id)}>
                                            Revocar token
                                        </Button>
                                    </div>
                                </div>
                            );
                        })}
                        {devices.length === 0 ? <div className="card p-6 text-sm text-slate-500">No hay devices.</div> : null}
                    </div>
                </div>
            ) : null}

            {!loading && tab === 'credentials' ? (
                <div className="space-y-3">
                    <div className="card p-4">
                        <div className="text-sm text-slate-300 font-semibold">Nueva credencial</div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                            <div>
                                <div className="text-xs text-slate-500">Buscar usuario</div>
                                <Input value={credUserSearch} onChange={(e) => setCredUserSearch(e.target.value)} placeholder="Nombre o DNI…" />
                                {credUserResults.length > 0 ? (
                                    <div className="mt-2 rounded-xl border border-slate-800/60 bg-slate-900/40 overflow-hidden">
                                        {credUserResults.map((u) => (
                                            <button
                                                key={u.id}
                                                className="w-full text-left px-3 py-2 hover:bg-slate-900/60"
                                                onClick={() => {
                                                    setCredSelectedUser(u);
                                                    setCredUserResults([]);
                                                    setCredUserSearch(`${u.nombre} (#${u.id})`);
                                                }}
                                            >
                                                <div className="text-sm text-white">{u.nombre}</div>
                                                <div className="text-xs text-slate-500">#{u.id} • DNI {u.dni}</div>
                                            </button>
                                        ))}
                                    </div>
                                ) : null}
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Tipo</div>
                                <Select value={credType} onChange={(e) => setCredType(e.target.value)} options={credentialTypeOptions} />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Valor (UID / código)</div>
                                <Input value={credValue} onChange={(e) => setCredValue(e.target.value)} placeholder="Ej: 04A1B2C3D4" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Label (opcional)</div>
                                <Input value={credLabel} onChange={(e) => setCredLabel(e.target.value)} placeholder="Ej: Llavero azul" />
                            </div>
                        </div>
                        <div className="mt-3 flex justify-end">
                            <Button onClick={createCredential} disabled={!credSelectedUser || !credValue.trim() || creatingCred} leftIcon={creatingCred ? <Loader2 className="w-4 h-4 animate-spin" /> : undefined}>
                                Crear
                            </Button>
                        </div>
                    </div>
                    <div className="card p-4">
                        <div className="text-sm text-slate-300 font-semibold">Credenciales ({credentials.length})</div>
                        <div className="mt-3 space-y-2">
                            {credentials.map((c) => (
                                <div key={c.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-800/60 bg-slate-900/40 px-3 py-2">
                                    <div className="min-w-0">
                                        <div className="text-sm text-white">
                                            #{c.id} • user #{c.usuario_id} • {c.credential_type}
                                        </div>
                                        <div className="text-xs text-slate-500">{c.label || '—'}</div>
                                    </div>
                                    <Button
                                        variant="secondary"
                                        onClick={() => setDeleteCredState({ open: true, id: c.id })}
                                        leftIcon={<Trash2 className="w-4 h-4" />}
                                    >
                                        Eliminar
                                    </Button>
                                </div>
                            ))}
                            {credentials.length === 0 ? <div className="text-sm text-slate-500">No hay credenciales.</div> : null}
                        </div>
                    </div>
                </div>
            ) : null}

            {!loading && tab === 'events' ? (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="text-sm text-slate-400">Últimos eventos</div>
                        <div className="flex items-center gap-2">
                            <Button variant="secondary" disabled={eventsPage <= 1} onClick={() => loadEvents(eventsPage - 1)}>
                                Prev
                            </Button>
                            <Button variant="secondary" onClick={() => loadEvents(eventsPage + 1)}>
                                Next
                            </Button>
                        </div>
                    </div>
                    <div className="space-y-2">
                        {events.map((e) => (
                            <div key={e.id} className="card p-4 flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <div className="text-white font-semibold flex items-center gap-2">
                                        <span>{e.event_type}</span>
                                        {e.decision === 'allow' ? <span className="badge badge-success">allow</span> : <span className="badge badge-danger">deny</span>}
                                        {e.unlock ? (
                                            <span className="badge badge-warning flex items-center gap-1">
                                                <ShieldAlert className="w-3 h-3" /> unlock
                                            </span>
                                        ) : null}
                                    </div>
                                    <div className="text-xs text-slate-500 mt-1">
                                        {e.created_at} • sucursal {e.sucursal_id ?? '—'} • device {e.device_id ?? '—'} • user {e.subject_usuario_id ?? '—'} • {e.input_value_masked || ''}
                                    </div>
                                    <div className="text-sm text-slate-200 mt-2">{e.reason || '—'}</div>
                                </div>
                            </div>
                        ))}
                        {events.length === 0 ? <div className="card p-6 text-sm text-slate-500">No hay eventos.</div> : null}
                    </div>
                </div>
            ) : null}

            <ConfirmModal
                isOpen={deleteCredState.open}
                onClose={() => setDeleteCredState({ open: false })}
                title="Eliminar credencial"
                message="Esta acción no se puede deshacer."
                confirmText="Eliminar"
                cancelText="Cancelar"
                variant="danger"
                isLoading={deletingCred}
                onConfirm={deleteCredential}
            />

            <ConfirmModal
                isOpen={remoteUnlockState.open}
                onClose={() => setRemoteUnlockState({ open: false })}
                title="Abrir molinete"
                message={`Esto enviará un comando de apertura al agente${remoteUnlockState.device ? ` (${remoteUnlockState.device.name})` : ''}.`}
                confirmText="Abrir"
                cancelText="Cancelar"
                variant="info"
                isLoading={remoteUnlocking}
                onConfirm={confirmRemoteUnlock}
            />

            <Modal
                isOpen={deviceCommandsState.open}
                onClose={() => setDeviceCommandsState({ open: false })}
                title="Comandos del device"
                description={deviceCommandsState.device ? deviceCommandsState.device.name : ''}
                size="lg"
                footer={
                    <div className="flex items-center gap-2">
                        <button
                            className="btn-secondary"
                            onClick={() => {
                                const d = deviceCommandsState.device;
                                if (d) openDeviceCommands(d);
                            }}
                            disabled={loadingDeviceCommands}
                        >
                            Refrescar
                        </button>
                        <button className="btn-primary" onClick={() => setDeviceCommandsState({ open: false })}>
                            OK
                        </button>
                    </div>
                }
            >
                {loadingDeviceCommands ? (
                    <div className="p-6 text-sm text-slate-400 flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                    </div>
                ) : (
                    <div className="space-y-2">
                        {deviceCommands.map((c) => {
                            const status = String((c as any).status || '');
                            const canCancel = status === 'pending';
                            const ok = (c as any)?.result && typeof (c as any).result === 'object' ? (c as any).result.ok : undefined;
                            return (
                                <div key={(c as any).id} className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-3 flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="text-sm text-white font-semibold">
                                            #{String((c as any).id)} • {String((c as any).command_type || '')}
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">
                                            status {status || '—'}
                                            {(c as any).created_at ? ` • created ${(c as any).created_at}` : ''}
                                            {(c as any).claimed_at ? ` • claimed ${(c as any).claimed_at}` : ''}
                                            {(c as any).acked_at ? ` • acked ${(c as any).acked_at}` : ''}
                                            {(c as any).expires_at ? ` • exp ${(c as any).expires_at}` : ''}
                                            {ok === true ? ' • result ok' : ok === false ? ' • result fail' : ''}
                                        </div>
                                    </div>
                                    {deviceCommandsState.device && canCancel ? (
                                        <Button
                                            variant="secondary"
                                            onClick={() => cancelCommand(deviceCommandsState.device!.id, Number((c as any).id))}
                                        >
                                            Cancelar
                                        </Button>
                                    ) : null}
                                </div>
                            );
                        })}
                        {deviceCommands.length === 0 ? <div className="p-6 text-sm text-slate-500">No hay comandos.</div> : null}
                    </div>
                )}
            </Modal>

            <Modal
                isOpen={pairingInfo.open}
                onClose={() => setPairingInfo({ open: false })}
                title="Pairing"
                description="Copiá y pegá este bloque en el Access Agent (incluye sucursal para evitar errores)."
                size="sm"
                footer={
                    <div className="flex items-center gap-2">
                        <button
                            className="btn-secondary"
                            onClick={async () => {
                                try {
                                    if (!pairingBlock) return;
                                    await navigator.clipboard.writeText(pairingBlock);
                                    success('Copiado');
                                } catch {
                                    error('No se pudo copiar');
                                }
                            }}
                            disabled={!pairingBlock}
                        >
                            Copiar
                        </button>
                        <button className="btn-primary" onClick={() => setPairingInfo({ open: false })}>
                            OK
                        </button>
                    </div>
                }
            >
                <div className="text-sm text-slate-200 whitespace-pre-wrap">
                    {pairingBlock || '—'}
                </div>
            </Modal>

            <Modal
                isOpen={createDeviceOpen}
                onClose={() => setCreateDeviceOpen(false)}
                title="Nuevo device"
                description="Crea un device y genera un código de pairing para el agente."
                size="md"
                footer={
                    <>
                        <button className="btn-secondary" onClick={() => setCreateDeviceOpen(false)} disabled={creatingDevice}>
                            Cancelar
                        </button>
                        <button className="btn-primary" onClick={createDevice} disabled={creatingDevice || !newDeviceName.trim()}>
                            {creatingDevice ? 'Creando…' : 'Crear'}
                        </button>
                    </>
                }
            >
                <div className="space-y-2">
                    <div className="text-xs text-slate-500">Nombre</div>
                    <Input value={newDeviceName} onChange={(e) => setNewDeviceName(e.target.value)} placeholder="Entrada principal" />
                    <div className="text-xs text-slate-500">Sucursal</div>
                    <Select
                        value={newDeviceSucursalId}
                        onChange={(e) => setNewDeviceSucursalId(e.target.value)}
                        options={[
                            { value: '', label: '—' },
                            ...(sucursales || []).map((s) => ({ value: String(s.id), label: `${s.nombre} (#${s.id})` })),
                        ]}
                    />
                    <div className="text-xs text-slate-500">Preset de salida (opcional)</div>
                    <Select
                        value={newDeviceUnlockPreset}
                        onChange={(e) => {
                            const v = e.target.value;
                            setNewDeviceUnlockPreset(v);
                            if (v === 'generic_http_get') {
                                setNewDeviceUnlockType('http_get');
                                setNewDeviceUnlockUrl('http://RELAY_IP/unlock');
                            } else if (v === 'generic_http_post') {
                                setNewDeviceUnlockType('http_post_json');
                                setNewDeviceUnlockUrl('http://RELAY_IP/unlock');
                            } else if (v === 'shelly_gen1') {
                                setNewDeviceUnlockType('http_get');
                                setNewDeviceUnlockUrl('http://SHELLY_IP/relay/0?turn=on');
                            } else if (v === 'shelly_gen2') {
                                setNewDeviceUnlockType('http_get');
                                setNewDeviceUnlockUrl('http://SHELLY_IP/rpc/Switch.Set?id=0&on=true');
                            } else if (v === 'generic_tcp_open_nl') {
                                setNewDeviceUnlockType('tcp');
                                setNewDeviceUnlockTcpHost('192.168.1.50');
                                setNewDeviceUnlockTcpPort('9100');
                                setNewDeviceUnlockTcpPayload('OPEN\\n');
                            } else if (v === 'generic_serial_open_nl') {
                                setNewDeviceUnlockType('serial');
                                setNewDeviceUnlockSerialPort('COM3');
                                setNewDeviceUnlockSerialBaud('9600');
                                setNewDeviceUnlockSerialPayload('OPEN\\n');
                            }
                        }}
                        options={unlockPresetOptions}
                    />
                    <div className="text-xs text-slate-500">Salida (unlock)</div>
                    <Select
                        value={newDeviceUnlockType}
                        onChange={(e) => setNewDeviceUnlockType(e.target.value)}
                        options={[
                            { value: 'none', label: 'Sin salida (solo validar/registrar)' },
                            { value: 'http_get', label: 'HTTP GET (relé IP)' },
                            { value: 'http_post_json', label: 'HTTP POST JSON (relé/PLC)' },
                            { value: 'tcp', label: 'TCP (payload bytes)' },
                            { value: 'serial', label: 'Serial (payload bytes)' },
                        ]}
                    />
                    {newDeviceUnlockType === 'http_get' || newDeviceUnlockType === 'http_post_json' ? (
                        <>
                            <div className="text-xs text-slate-500">URL</div>
                            <Input value={newDeviceUnlockUrl} onChange={(e) => setNewDeviceUnlockUrl(e.target.value)} placeholder="http://relay.local/unlock" />
                        </>
                    ) : null}
                    {newDeviceUnlockType === 'tcp' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            <div>
                                <div className="text-xs text-slate-500">TCP host</div>
                                <Input value={newDeviceUnlockTcpHost} onChange={(e) => setNewDeviceUnlockTcpHost(e.target.value)} placeholder="192.168.1.50" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">TCP port</div>
                                <Input value={newDeviceUnlockTcpPort} onChange={(e) => setNewDeviceUnlockTcpPort(e.target.value)} placeholder="9100" />
                            </div>
                            <div className="md:col-span-2">
                                <div className="text-xs text-slate-500">TCP payload</div>
                                <Input value={newDeviceUnlockTcpPayload} onChange={(e) => setNewDeviceUnlockTcpPayload(e.target.value)} placeholder="0xA0 0x01 0x01 (o texto plano)" />
                            </div>
                        </div>
                    ) : null}
                    {newDeviceUnlockType === 'serial' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            <div>
                                <div className="text-xs text-slate-500">Serial port</div>
                                <Input value={newDeviceUnlockSerialPort} onChange={(e) => setNewDeviceUnlockSerialPort(e.target.value)} placeholder="COM3" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Serial baud</div>
                                <Input value={newDeviceUnlockSerialBaud} onChange={(e) => setNewDeviceUnlockSerialBaud(e.target.value)} placeholder="9600" />
                            </div>
                            <div className="md:col-span-2">
                                <div className="text-xs text-slate-500">Serial payload</div>
                                <Input value={newDeviceUnlockSerialPayload} onChange={(e) => setNewDeviceUnlockSerialPayload(e.target.value)} placeholder="OPEN\\n o 0xA0 0x01 0x01 o DTR_PULSE:500" />
                            </div>
                        </div>
                    ) : null}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <div>
                            <div className="text-xs text-slate-500">Unlock ms</div>
                            <Input value={newDeviceUnlockMs} onChange={(e) => setNewDeviceUnlockMs(e.target.value)} placeholder="2500" />
                        </div>
                        <div>
                            <div className="text-xs text-slate-500">Hotkey manual</div>
                            <Input value={newDeviceManualHotkey} onChange={(e) => setNewDeviceManualHotkey(e.target.value)} placeholder="F10" />
                        </div>
                    </div>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={newDeviceAllowManual} onChange={(e) => setNewDeviceAllowManual(e.target.checked)} />
                        Permitir apertura manual (sin asistencia)
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={newDeviceAllowRemoteUnlock} onChange={(e) => setNewDeviceAllowRemoteUnlock(e.target.checked)} />
                        Permitir unlock remoto (web/móvil)
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={newDeviceStationAutoUnlock} onChange={(e) => setNewDeviceStationAutoUnlock(e.target.checked)} />
                        Auto abrir al check-in (Station QR / checkin)
                    </label>
                    {newDeviceStationAutoUnlock ? (
                        <div>
                            <div className="text-xs text-slate-500">Station unlock ms</div>
                            <Input value={newDeviceStationUnlockMs} onChange={(e) => setNewDeviceStationUnlockMs(e.target.value)} placeholder="2500" />
                        </div>
                    ) : null}
                    <div className="pt-3 mt-2 border-t border-slate-800/60">
                        <div className="text-sm text-slate-300 font-semibold">Reglas</div>

                        <div className="text-xs text-slate-500 mt-2">Timezone</div>
                        <Input value={newDeviceTimezone} onChange={(e) => setNewDeviceTimezone(e.target.value)} placeholder="America/Argentina/Buenos_Aires" />

                        <label className="flex items-center gap-2 text-sm text-slate-300 mt-2">
                            <input type="checkbox" checked={newDeviceDniRequiresPin} onChange={(e) => setNewDeviceDniRequiresPin(e.target.checked)} />
                            DNI requiere PIN (usa evento DNI#PIN)
                        </label>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                            <div>
                                <div className="text-xs text-slate-500">Anti-passback (segundos)</div>
                                <Input value={newDeviceAntiPassbackSec} onChange={(e) => setNewDeviceAntiPassbackSec(e.target.value)} placeholder="0" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Max eventos / minuto (0 desactiva)</div>
                                <Input value={newDeviceMaxEventsPerMin} onChange={(e) => setNewDeviceMaxEventsPerMin(e.target.value)} placeholder="0" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Ventana rate limit (segundos)</div>
                                <Input value={newDeviceRateLimitWindowSec} onChange={(e) => setNewDeviceRateLimitWindowSec(e.target.value)} placeholder="60" />
                            </div>
                        </div>

                        <label className="flex items-center gap-2 text-sm text-slate-300 mt-3">
                            <input type="checkbox" checked={newDeviceRestrictEventTypes} onChange={(e) => setNewDeviceRestrictEventTypes(e.target.checked)} />
                            Restringir tipos de lectura permitidos
                        </label>
                        {newDeviceRestrictEventTypes ? (
                            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                                {eventTypeOptions.map((o) => (
                                    <label key={o.value} className="flex items-center gap-2 text-sm text-slate-300">
                                        <input
                                            type="checkbox"
                                            checked={Boolean(newDeviceAllowedEventTypes[o.value])}
                                            onChange={(e) =>
                                                setNewDeviceAllowedEventTypes((cur) => ({
                                                    ...(cur || {}),
                                                    [o.value]: e.target.checked,
                                                }))
                                            }
                                        />
                                        {o.label}
                                    </label>
                                ))}
                            </div>
                        ) : null}

                        <div className="text-xs text-slate-500 mt-3">Horarios permitidos (opcional)</div>
                        <div className="text-xs text-slate-600">Si no configurás nada, se permite 24/7.</div>
                        <div className="mt-2 space-y-2">
                            {newDeviceAllowedHours.map((r, idx) => (
                                <div key={idx} className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-3 space-y-2">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                                        <div>
                                            <div className="text-xs text-slate-500">Start (HH:MM)</div>
                                            <Input
                                                value={r.start}
                                                onChange={(e) =>
                                                    setNewDeviceAllowedHours((cur) => cur.map((x, i) => (i === idx ? { ...x, start: e.target.value } : x)))
                                                }
                                                placeholder="08:00"
                                            />
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500">End (HH:MM)</div>
                                            <Input
                                                value={r.end}
                                                onChange={(e) =>
                                                    setNewDeviceAllowedHours((cur) => cur.map((x, i) => (i === idx ? { ...x, end: e.target.value } : x)))
                                                }
                                                placeholder="22:00"
                                            />
                                        </div>
                                        <div className="flex items-end">
                                            <Button variant="secondary" onClick={() => setNewDeviceAllowedHours((cur) => cur.filter((_, i) => i !== idx))}>
                                                Quitar
                                            </Button>
                                        </div>
                                    </div>
                                    <div className="flex flex-wrap gap-3">
                                        {weekdayOptions.map((d) => (
                                            <label key={d.value} className="flex items-center gap-2 text-sm text-slate-300">
                                                <input
                                                    type="checkbox"
                                                    checked={Array.isArray(r.days) && r.days.includes(d.value)}
                                                    onChange={(e) => {
                                                        const checked = e.target.checked;
                                                        setNewDeviceAllowedHours((cur) =>
                                                            cur.map((x, i) => {
                                                                if (i !== idx) return x;
                                                                const days = Array.isArray(x.days) ? [...x.days] : [];
                                                                const has = days.includes(d.value);
                                                                if (checked && !has) days.push(d.value);
                                                                if (!checked && has) days.splice(days.indexOf(d.value), 1);
                                                                return { ...x, days: days.sort((a, b) => a - b) };
                                                            })
                                                        );
                                                    }}
                                                />
                                                {d.label}
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            ))}
                            <Button
                                variant="secondary"
                                onClick={() => setNewDeviceAllowedHours((cur) => [...(cur || []), { days: [1, 2, 3, 4, 5], start: '08:00', end: '22:00' }])}
                            >
                                Agregar regla horaria
                            </Button>
                        </div>
                    </div>
                </div>
            </Modal>

            <Modal
                isOpen={editDeviceOpen}
                onClose={() => {
                    setEditDeviceOpen(false);
                    setEditDevice(null);
                }}
                title="Editar device"
                description="Configura reglas y comportamiento del Access Agent."
                size="md"
                footer={
                    <>
                        <button
                            className="btn-secondary"
                            onClick={() => {
                                setEditDeviceOpen(false);
                                setEditDevice(null);
                            }}
                            disabled={savingDevice}
                        >
                            Cancelar
                        </button>
                        <button className="btn-primary" onClick={saveDevice} disabled={savingDevice || !editDevice}>
                            {savingDevice ? 'Guardando…' : 'Guardar'}
                        </button>
                    </>
                }
            >
                <div className="space-y-2">
                    <div className="text-xs text-slate-500">Nombre</div>
                    <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
                    <div className="text-xs text-slate-500">Sucursal</div>
                    <Select
                        value={editSucursalId}
                        onChange={(e) => setEditSucursalId(e.target.value)}
                        options={[
                            { value: '', label: '—' },
                            ...(sucursales || []).map((s) => ({ value: String(s.id), label: `${s.nombre} (#${s.id})` })),
                        ]}
                    />
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={editEnabled} onChange={(e) => setEditEnabled(e.target.checked)} />
                        Device habilitado
                    </label>
                    <div className="text-xs text-slate-500">Preset de salida (opcional)</div>
                    <Select
                        value={editUnlockPreset}
                        onChange={(e) => {
                            const v = e.target.value;
                            setEditUnlockPreset(v);
                            if (v === 'generic_http_get') {
                                setEditUnlockType('http_get');
                                setEditUnlockUrl('http://RELAY_IP/unlock');
                            } else if (v === 'generic_http_post') {
                                setEditUnlockType('http_post_json');
                                setEditUnlockUrl('http://RELAY_IP/unlock');
                            } else if (v === 'shelly_gen1') {
                                setEditUnlockType('http_get');
                                setEditUnlockUrl('http://SHELLY_IP/relay/0?turn=on');
                            } else if (v === 'shelly_gen2') {
                                setEditUnlockType('http_get');
                                setEditUnlockUrl('http://SHELLY_IP/rpc/Switch.Set?id=0&on=true');
                            } else if (v === 'generic_tcp_open_nl') {
                                setEditUnlockType('tcp');
                                setEditUnlockTcpHost('192.168.1.50');
                                setEditUnlockTcpPort('9100');
                                setEditUnlockTcpPayload('OPEN\\n');
                            } else if (v === 'generic_serial_open_nl') {
                                setEditUnlockType('serial');
                                setEditUnlockSerialPort('COM3');
                                setEditUnlockSerialBaud('9600');
                                setEditUnlockSerialPayload('OPEN\\n');
                            }
                        }}
                        options={unlockPresetOptions}
                    />
                    <div className="text-xs text-slate-500">Salida (unlock)</div>
                    <Select
                        value={editUnlockType}
                        onChange={(e) => setEditUnlockType(e.target.value)}
                        options={[
                            { value: 'none', label: 'Sin salida (solo validar/registrar)' },
                            { value: 'http_get', label: 'HTTP GET (relé IP)' },
                            { value: 'http_post_json', label: 'HTTP POST JSON (relé/PLC)' },
                            { value: 'tcp', label: 'TCP (payload bytes)' },
                            { value: 'serial', label: 'Serial (payload bytes)' },
                        ]}
                    />
                    {editUnlockType === 'http_get' || editUnlockType === 'http_post_json' ? (
                        <>
                            <div className="text-xs text-slate-500">URL</div>
                            <Input value={editUnlockUrl} onChange={(e) => setEditUnlockUrl(e.target.value)} placeholder="http://relay.local/unlock" />
                        </>
                    ) : null}
                    {editUnlockType === 'tcp' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            <div>
                                <div className="text-xs text-slate-500">TCP host</div>
                                <Input value={editUnlockTcpHost} onChange={(e) => setEditUnlockTcpHost(e.target.value)} placeholder="192.168.1.50" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">TCP port</div>
                                <Input value={editUnlockTcpPort} onChange={(e) => setEditUnlockTcpPort(e.target.value)} placeholder="9100" />
                            </div>
                            <div className="md:col-span-2">
                                <div className="text-xs text-slate-500">TCP payload</div>
                                <Input value={editUnlockTcpPayload} onChange={(e) => setEditUnlockTcpPayload(e.target.value)} placeholder="0xA0 0x01 0x01 (o texto plano)" />
                            </div>
                        </div>
                    ) : null}
                    {editUnlockType === 'serial' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            <div>
                                <div className="text-xs text-slate-500">Serial port</div>
                                <Input value={editUnlockSerialPort} onChange={(e) => setEditUnlockSerialPort(e.target.value)} placeholder="COM3" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Serial baud</div>
                                <Input value={editUnlockSerialBaud} onChange={(e) => setEditUnlockSerialBaud(e.target.value)} placeholder="9600" />
                            </div>
                            <div className="md:col-span-2">
                                <div className="text-xs text-slate-500">Serial payload</div>
                                <Input value={editUnlockSerialPayload} onChange={(e) => setEditUnlockSerialPayload(e.target.value)} placeholder="OPEN\\n o 0xA0 0x01 0x01 o DTR_PULSE:500" />
                            </div>
                        </div>
                    ) : null}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <div>
                            <div className="text-xs text-slate-500">Unlock ms</div>
                            <Input value={editUnlockMs} onChange={(e) => setEditUnlockMs(e.target.value)} placeholder="2500" />
                        </div>
                        <div>
                            <div className="text-xs text-slate-500">Hotkey manual</div>
                            <Input value={editManualHotkey} onChange={(e) => setEditManualHotkey(e.target.value)} placeholder="F10" />
                        </div>
                    </div>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={editAllowManual} onChange={(e) => setEditAllowManual(e.target.checked)} />
                        Permitir apertura manual (sin asistencia)
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={editAllowRemoteUnlock} onChange={(e) => setEditAllowRemoteUnlock(e.target.checked)} />
                        Permitir unlock remoto (web/móvil)
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input type="checkbox" checked={editStationAutoUnlock} onChange={(e) => setEditStationAutoUnlock(e.target.checked)} />
                        Auto abrir al check-in (Station QR / checkin)
                    </label>
                    {editStationAutoUnlock ? (
                        <div>
                            <div className="text-xs text-slate-500">Station unlock ms</div>
                            <Input value={editStationUnlockMs} onChange={(e) => setEditStationUnlockMs(e.target.value)} placeholder="2500" />
                        </div>
                    ) : null}
                    <div className="pt-3 mt-2 border-t border-slate-800/60">
                        <div className="text-sm text-slate-300 font-semibold">Reglas</div>

                        <div className="text-xs text-slate-500 mt-2">Timezone</div>
                        <Input value={editTimezone} onChange={(e) => setEditTimezone(e.target.value)} placeholder="America/Argentina/Buenos_Aires" />

                        <label className="flex items-center gap-2 text-sm text-slate-300 mt-2">
                            <input type="checkbox" checked={editDniRequiresPin} onChange={(e) => setEditDniRequiresPin(e.target.checked)} />
                            DNI requiere PIN (usa evento DNI#PIN)
                        </label>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                            <div>
                                <div className="text-xs text-slate-500">Anti-passback (segundos)</div>
                                <Input value={editAntiPassbackSec} onChange={(e) => setEditAntiPassbackSec(e.target.value)} placeholder="0" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Max eventos / minuto (0 desactiva)</div>
                                <Input value={editMaxEventsPerMin} onChange={(e) => setEditMaxEventsPerMin(e.target.value)} placeholder="0" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500">Ventana rate limit (segundos)</div>
                                <Input value={editRateLimitWindowSec} onChange={(e) => setEditRateLimitWindowSec(e.target.value)} placeholder="60" />
                            </div>
                        </div>

                        <label className="flex items-center gap-2 text-sm text-slate-300 mt-3">
                            <input type="checkbox" checked={editRestrictEventTypes} onChange={(e) => setEditRestrictEventTypes(e.target.checked)} />
                            Restringir tipos de lectura permitidos
                        </label>
                        {editRestrictEventTypes ? (
                            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                                {eventTypeOptions.map((o) => (
                                    <label key={o.value} className="flex items-center gap-2 text-sm text-slate-300">
                                        <input
                                            type="checkbox"
                                            checked={Boolean(editAllowedEventTypes[o.value])}
                                            onChange={(e) =>
                                                setEditAllowedEventTypes((cur) => ({
                                                    ...(cur || {}),
                                                    [o.value]: e.target.checked,
                                                }))
                                            }
                                        />
                                        {o.label}
                                    </label>
                                ))}
                            </div>
                        ) : null}

                        <div className="text-xs text-slate-500 mt-3">Horarios permitidos (opcional)</div>
                        <div className="text-xs text-slate-600">Si no configurás nada, se permite 24/7.</div>
                        <div className="mt-2 space-y-2">
                            {editAllowedHours.map((r, idx) => (
                                <div key={idx} className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-3 space-y-2">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                                        <div>
                                            <div className="text-xs text-slate-500">Start (HH:MM)</div>
                                            <Input
                                                value={r.start}
                                                onChange={(e) => setEditAllowedHours((cur) => cur.map((x, i) => (i === idx ? { ...x, start: e.target.value } : x)))}
                                                placeholder="08:00"
                                            />
                                        </div>
                                        <div>
                                            <div className="text-xs text-slate-500">End (HH:MM)</div>
                                            <Input
                                                value={r.end}
                                                onChange={(e) => setEditAllowedHours((cur) => cur.map((x, i) => (i === idx ? { ...x, end: e.target.value } : x)))}
                                                placeholder="22:00"
                                            />
                                        </div>
                                        <div className="flex items-end">
                                            <Button variant="secondary" onClick={() => setEditAllowedHours((cur) => cur.filter((_, i) => i !== idx))}>
                                                Quitar
                                            </Button>
                                        </div>
                                    </div>
                                    <div className="flex flex-wrap gap-3">
                                        {weekdayOptions.map((d) => (
                                            <label key={d.value} className="flex items-center gap-2 text-sm text-slate-300">
                                                <input
                                                    type="checkbox"
                                                    checked={Array.isArray(r.days) && r.days.includes(d.value)}
                                                    onChange={(e) => {
                                                        const checked = e.target.checked;
                                                        setEditAllowedHours((cur) =>
                                                            cur.map((x, i) => {
                                                                if (i !== idx) return x;
                                                                const days = Array.isArray(x.days) ? [...x.days] : [];
                                                                const has = days.includes(d.value);
                                                                if (checked && !has) days.push(d.value);
                                                                if (!checked && has) days.splice(days.indexOf(d.value), 1);
                                                                return { ...x, days: days.sort((a, b) => a - b) };
                                                            })
                                                        );
                                                    }}
                                                />
                                                {d.label}
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            ))}
                            <Button
                                variant="secondary"
                                onClick={() => setEditAllowedHours((cur) => [...(cur || []), { days: [1, 2, 3, 4, 5], start: '08:00', end: '22:00' }])}
                            >
                                Agregar regla horaria
                            </Button>
                        </div>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
