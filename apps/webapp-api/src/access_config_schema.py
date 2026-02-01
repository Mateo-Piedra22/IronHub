from __future__ import annotations

from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field, ValidationError, field_validator


class UnlockProfile(BaseModel):
    type: str = Field(default="none", max_length=32)
    url: Optional[str] = Field(default=None, max_length=500)
    host: Optional[str] = Field(default=None, max_length=200)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    payload: Optional[str] = Field(default=None, max_length=2000)
    serial_port: Optional[str] = Field(default=None, max_length=64)
    serial_baud: Optional[int] = Field(default=None, ge=1200, le=921600)

    @field_validator("type")
    @classmethod
    def _v_type(cls, v: str) -> str:
        s = str(v or "").strip().lower()
        if s not in ("none", "http_get", "http_post_json", "tcp", "serial"):
            return "none"
        return s

    @field_validator("url")
    @classmethod
    def _v_url(cls, v: Optional[str]) -> Optional[str]:
        s = str(v or "").strip()
        return s or None

    @field_validator("host")
    @classmethod
    def _v_host(cls, v: Optional[str]) -> Optional[str]:
        s = str(v or "").strip()
        return s or None

    @field_validator("payload")
    @classmethod
    def _v_payload(cls, v: Optional[str]) -> Optional[str]:
        s = str(v or "").strip()
        return s or None

    @field_validator("serial_port")
    @classmethod
    def _v_serial_port(cls, v: Optional[str]) -> Optional[str]:
        s = str(v or "").strip()
        return s or None


class AccessDeviceConfig(BaseModel):
    config_version: int = Field(default=1, ge=1, le=50)
    mode: str = Field(default="validate_and_command", max_length=40)

    unlock_ms: int = Field(default=2500, ge=250, le=15000)
    allow_manual_unlock: bool = Field(default=True)
    manual_hotkey: str = Field(default="F10", max_length=32)
    unlock_profile: UnlockProfile = Field(default_factory=UnlockProfile)
    allow_remote_unlock: bool = Field(default=False)
    station_auto_unlock: bool = Field(default=False)
    station_unlock_ms: int = Field(default=2500, ge=250, le=15000)

    input_source: str = Field(default="keyboard", max_length=32)
    input_protocol: str = Field(default="raw", max_length=32)
    input_regex: str = Field(default="", max_length=500)
    serial_port: str = Field(default="", max_length=32)
    serial_baud: int = Field(default=9600, ge=1200, le=921600)

    uid_format: str = Field(default="auto", max_length=16)
    uid_endian: str = Field(default="auto", max_length=16)
    uid_bits: int = Field(default=40, ge=16, le=128)

    max_events_per_minute: int = Field(default=120, ge=0, le=5000)
    rate_limit_window_seconds: int = Field(default=60, ge=5, le=300)
    anti_passback_seconds: int = Field(default=0, ge=0, le=86400)
    allowed_event_types: Optional[List[str]] = None

    @field_validator("mode")
    @classmethod
    def _v_mode(cls, v: str) -> str:
        s = str(v or "").strip().lower()
        if s not in ("validate_and_command", "observe_only"):
            return "validate_and_command"
        return s

    @field_validator("input_source")
    @classmethod
    def _v_input_source(cls, v: str) -> str:
        s = str(v or "").strip().lower()
        if s not in ("keyboard", "serial"):
            return "keyboard"
        return s

    @field_validator("input_protocol")
    @classmethod
    def _v_input_protocol(cls, v: str) -> str:
        s = str(v or "").strip().lower()
        if s not in ("raw", "data", "drt", "str", "regex", "em4100"):
            return "raw"
        return s

    @field_validator("manual_hotkey")
    @classmethod
    def _v_hotkey(cls, v: str) -> str:
        s = str(v or "").strip()
        return s or "F10"

    @field_validator("uid_format")
    @classmethod
    def _v_uid_format(cls, v: str) -> str:
        s = str(v or "").strip().lower()
        if s not in ("auto", "hex", "dec"):
            return "auto"
        return s

    @field_validator("uid_endian")
    @classmethod
    def _v_uid_endian(cls, v: str) -> str:
        s = str(v or "").strip().lower()
        if s not in ("auto", "be", "le"):
            return "auto"
        return s

    @field_validator("allowed_event_types")
    @classmethod
    def _v_allowed_event_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        allowed = {"dni", "dni_pin", "qr_token", "credential", "fob", "card", "manual_unlock", "enroll_credential"}
        out: List[str] = []
        for it in v:
            s = str(it or "").strip().lower()
            if s in allowed and s not in out:
                out.append(s)
        return out[:20] if out else None


def normalize_access_device_config(raw: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}

    base.pop("runtime_status", None)
    base.pop("enroll_mode", None)

    try:
        cfg = AccessDeviceConfig.model_validate(base)
        normalized = cfg.model_dump()
    except ValidationError:
        cfg = AccessDeviceConfig()
        normalized = cfg.model_dump()

    out = dict(base)
    out.update(normalized)
    out.pop("runtime_status", None)
    out.pop("enroll_mode", None)
    return out
