import base64
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union

from .pdf_engine import PDFEngine


class PreviewFormat(Enum):
    PDF = "pdf"
    IMAGE = "image"
    THUMBNAIL = "thumbnail"
    HTML = "html"
    JSON = "json"


class PreviewQuality(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class PreviewConfig:
    format: PreviewFormat = PreviewFormat.PDF
    quality: PreviewQuality = PreviewQuality.MEDIUM
    page_number: int = 1
    dpi: int = 150
    use_cache: bool = True
    cache_ttl: int = 3600
    generate_sample_data: bool = True


@dataclass
class PreviewResult:
    success: bool
    data: Union[bytes, str, Dict[str, Any]]
    format: PreviewFormat
    size_bytes: int
    generation_time: float
    cache_hit: bool
    error_message: Optional[str] = None


class PreviewEngine:
    _MAX_CACHE = 200

    def __init__(self):
        self.pdf_engine = PDFEngine()
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def generate_preview(
        self,
        template_config: Dict[str, Any],
        config: PreviewConfig,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> PreviewResult:
        start = time.time()
        cache_hit = False

        data = custom_data
        if not data and config.generate_sample_data:
            data = self._generate_sample_data(template_config)

        cache_key = None
        if config.use_cache:
            cache_key = self._cache_key(template_config, config, data)
            cached = self._get_cached(cache_key)
            if cached is not None:
                cache_hit = True
                return PreviewResult(
                    success=True,
                    data=cached["data"],
                    format=config.format,
                    size_bytes=int(cached["size_bytes"]),
                    generation_time=time.time() - start,
                    cache_hit=True,
                )

        ok, errors = self.pdf_engine.validate_template_structure(template_config)
        if not ok:
            return PreviewResult(
                success=False,
                data="",
                format=config.format,
                size_bytes=0,
                generation_time=time.time() - start,
                cache_hit=cache_hit,
                error_message="; ".join(errors),
            )

        try:
            if config.format == PreviewFormat.PDF:
                pdf_bytes = self.pdf_engine.generate_pdf(template_config, data or {}, output_path=None)
                if isinstance(pdf_bytes, str):
                    return PreviewResult(
                        success=False,
                        data="",
                        format=config.format,
                        size_bytes=0,
                        generation_time=time.time() - start,
                        cache_hit=cache_hit,
                        error_message="Unexpected output_path result",
                    )
                result = PreviewResult(
                    success=True,
                    data=pdf_bytes,
                    format=config.format,
                    size_bytes=len(pdf_bytes),
                    generation_time=time.time() - start,
                    cache_hit=cache_hit,
                )
            elif config.format in (PreviewFormat.IMAGE, PreviewFormat.THUMBNAIL):
                pdf_bytes = self.pdf_engine.generate_pdf(template_config, data or {}, output_path=None)
                if isinstance(pdf_bytes, str):
                    raise RuntimeError("Unexpected output_path result")
                png = self._pdf_to_png(pdf_bytes, page_number=max(1, int(config.page_number or 1)), dpi=int(config.dpi or 150))
                result = PreviewResult(
                    success=True,
                    data=png,
                    format=config.format,
                    size_bytes=len(png),
                    generation_time=time.time() - start,
                    cache_hit=cache_hit,
                )
            elif config.format == PreviewFormat.HTML:
                result = PreviewResult(
                    success=True,
                    data="<html><body>Preview no implementado</body></html>",
                    format=config.format,
                    size_bytes=0,
                    generation_time=time.time() - start,
                    cache_hit=cache_hit,
                )
            elif config.format == PreviewFormat.JSON:
                result = PreviewResult(
                    success=True,
                    data={"template": template_config, "data": data or {}},
                    format=config.format,
                    size_bytes=0,
                    generation_time=time.time() - start,
                    cache_hit=cache_hit,
                )
            else:
                result = PreviewResult(
                    success=False,
                    data="",
                    format=config.format,
                    size_bytes=0,
                    generation_time=time.time() - start,
                    cache_hit=cache_hit,
                    error_message="Formato no soportado",
                )

            if result.success and config.use_cache and cache_key:
                self._set_cached(cache_key, result.data, result.size_bytes, ttl=int(config.cache_ttl or 3600))

            return result
        except Exception as e:
            return PreviewResult(
                success=False,
                data="",
                format=config.format,
                size_bytes=0,
                generation_time=time.time() - start,
                cache_hit=cache_hit,
                error_message=str(e),
            )

    def build_data_uri(self, result: PreviewResult) -> Optional[str]:
        if not result.success:
            return None
        if result.format == PreviewFormat.PDF and isinstance(result.data, (bytes, bytearray)):
            return f"data:application/pdf;base64,{base64.b64encode(bytes(result.data)).decode()}"
        if result.format in (PreviewFormat.IMAGE, PreviewFormat.THUMBNAIL) and isinstance(result.data, (bytes, bytearray)):
            return f"data:image/png;base64,{base64.b64encode(bytes(result.data)).decode()}"
        if result.format == PreviewFormat.HTML and isinstance(result.data, str):
            return f"data:text/html;base64,{base64.b64encode(result.data.encode('utf-8')).decode()}"
        if result.format == PreviewFormat.JSON:
            raw = json.dumps(result.data, ensure_ascii=False).encode("utf-8") if not isinstance(result.data, (bytes, bytearray, str)) else None
            if raw is None:
                return None
            return f"data:application/json;base64,{base64.b64encode(raw).decode()}"
        return None

    def _cache_key(self, template_config: Dict[str, Any], cfg: PreviewConfig, data: Optional[Dict[str, Any]]) -> str:
        raw = json.dumps({"template": template_config, "cfg": cfg.__dict__, "data": data or {}}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        item = self._cache.get(key)
        if not item:
            return None
        if item["expires_at"] < time.time():
            try:
                del self._cache[key]
            except Exception:
                pass
            return None
        self._cache.move_to_end(key)
        return item

    def _set_cached(self, key: str, data: Union[bytes, str, Dict[str, Any]], size_bytes: int, ttl: int) -> None:
        self._cache[key] = {"data": data, "size_bytes": size_bytes, "expires_at": time.time() + max(1, ttl)}
        self._cache.move_to_end(key)
        while len(self._cache) > self._MAX_CACHE:
            self._cache.popitem(last=False)

    def _pdf_to_png(self, pdf_bytes: bytes, page_number: int, dpi: int) -> bytes:
        try:
            import pypdfium2 as pdfium  # type: ignore
        except Exception as e:
            raise RuntimeError("pypdfium2 no está disponible para convertir PDF a imagen") from e
        pdf = pdfium.PdfDocument(pdf_bytes)
        page_index = max(0, min(len(pdf) - 1, page_number - 1))
        page = pdf[page_index]
        scale = max(0.5, min(4.0, float(dpi) / 72.0))
        pil_image = page.render(scale=scale).to_pil()
        out = base64.b64decode(base64.b64encode(b""))  # keep type stable
        import io

        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        out = buf.getvalue()
        try:
            page.close()
        except Exception:
            pass
        try:
            pdf.close()
        except Exception:
            pass
        return out

    def _generate_sample_data(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        dias_semana = None
        try:
            dias_semana = int(template_config.get("dias_semana") or template_config.get("metadata", {}).get("dias_semana") or 0) or None
        except Exception:
            dias_semana = None
        if not dias_semana:
            dias_semana = 3

        dias = []
        for i in range(1, dias_semana + 1):
            dias.append(
                {
                    "numero": i,
                    "nombre": "",
                    "ejercicios": [
                        {"nombre": "Sentadilla", "series": 3, "repeticiones": "8-10", "descanso": "90s"},
                        {"nombre": "Press banca", "series": 3, "repeticiones": "8-10", "descanso": "90s"},
                        {"nombre": "Remo", "series": 3, "repeticiones": "10-12", "descanso": "60s"},
                    ],
                }
            )

        return {
            "gym_name": "Gimnasio",
            "nombre_rutina": "Rutina de Ejemplo",
            "usuario_nombre": "Juan Pérez",
            "routine": {"uuid": "demo-uuid"},
            "dias": dias,
        }

