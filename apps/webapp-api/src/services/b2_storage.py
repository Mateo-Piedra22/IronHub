"""
B2 Storage Service for IronHub
Handles file uploads to Backblaze B2 with Cloudflare CDN integration
"""

import os
import hashlib
import logging
from typing import Optional, Tuple
from pathlib import Path
import re
import urllib.parse

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

logger = logging.getLogger(__name__)

# Configuration from environment
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "motiona-assets")
B2_KEY_ID = (
    os.getenv("B2_KEY_ID", "")
    or os.getenv("B2_ACCOUNT_ID", "")
    or os.getenv("B2_MASTER_KEY_ID", "")
)
B2_APPLICATION_KEY = (
    os.getenv("B2_APPLICATION_KEY", "")
    or os.getenv("B2_APP_KEY", "")
    or os.getenv("B2_MASTER_APPLICATION_KEY", "")
)
B2_ENDPOINT_URL = os.getenv("B2_ENDPOINT_URL", "s3.us-east-005.backblazeb2.com")
B2_MEDIA_PREFIX = os.getenv("B2_MEDIA_PREFIX", "assets")
B2_PUBLIC_BASE_URL = os.getenv("B2_PUBLIC_BASE_URL", "https://f005.backblazeb2.com")

MAX_B2_UPLOAD_BYTES = int(os.getenv("MAX_B2_UPLOAD_BYTES", str(60 * 1024 * 1024)))


def _get_direct_public_base() -> str:
    """Return a direct Backblaze public base URL (never a CDN domain)."""
    # 1) Prefer explicit public base, but only if it is a Backblaze host
    try:
        base = str(B2_PUBLIC_BASE_URL or "").strip().rstrip("/")
    except Exception:
        base = ""

    if base and not (base.startswith("http://") or base.startswith("https://")):
        base = f"https://{base.lstrip('/')}"

    if base.endswith("/file"):
        base = base[:-5]

    if base and "backblazeb2.com" in base.lower():
        return base

    # 2) Derive from S3 endpoint region (e.g. s3.us-east-005.backblazeb2.com -> f005.backblazeb2.com)
    try:
        ep = str(B2_ENDPOINT_URL or "").strip().lower()
        ep = ep.replace("https://", "").replace("http://", "")
        m = re.search(r"-(\d{3})\.backblazeb2\.com", ep)
        if m:
            return f"https://f{m.group(1)}.backblazeb2.com"
    except Exception:
        pass

    # 3) Safe fallback (may still be wrong for some regions but avoids CDN)
    return "https://f000.backblazeb2.com"


def _normalize_key_layout(key: str) -> str:
    """Normalize legacy keys to the current tenant-assets layout.

    Current layout: assets/<tenant>-assets/<folder>/...
    Legacy layout:  assets/<tenant>/<folder>/...
    """
    try:
        s = str(key or "").lstrip("/")
        if not s or ".." in s:
            return s
        prefix = f"{B2_MEDIA_PREFIX}/"
        if not s.startswith(prefix):
            return s
        rest = s[len(prefix) :]
        parts = rest.split("/", 2)
        if len(parts) < 2:
            return s
        tenant_part = parts[0]
        folder_part = parts[1]
        if tenant_part.endswith("-assets"):
            return s
        if folder_part not in ("logos", "videos", "exercises", "uploads", "support", "changelog"):
            return s
        # Rewrite tenant folder
        return f"{prefix}{tenant_part}-assets/{rest.split('/', 1)[1]}"
    except Exception:
        return str(key or "")


def get_s3_client():
    """
    Get a boto3 S3 client configured for Backblaze B2.
    Returns None if boto3 is not installed or credentials are missing.
    """
    if not HAS_BOTO3:
        logger.warning("boto3 not installed, B2 uploads disabled")
        return None

    if not B2_KEY_ID or not B2_APPLICATION_KEY:
        logger.warning("B2 credentials not configured")
        return None

    try:
        endpoint = str(B2_ENDPOINT_URL or "").strip()
        if endpoint and not (
            endpoint.startswith("http://") or endpoint.startswith("https://")
        ):
            endpoint = f"https://{endpoint}"
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APPLICATION_KEY,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    except Exception as e:
        logger.error(f"Failed to create B2 client: {e}")
        return None


def get_cdn_url(file_path: str) -> str:
    """
    Get the CDN URL for a file stored in B2.
    Uses Cloudflare CDN if configured, otherwise falls back to B2 direct URL.

    Args:
        file_path: The path of the file in B2 (relative to bucket root)

    Returns:
        Full URL to access the file
    """
    try:
        p = _normalize_key_layout(str(file_path or "")).lstrip("/")
        if not p or ".." in p:
            return ""
    except Exception:
        return ""

    base = _get_direct_public_base()
    return f"{base}/file/{B2_BUCKET_NAME}/{p}"


def _sanitize_tenant(tenant: str) -> str:
    try:
        t = re.sub(r"[^a-z0-9-]", "-", str(tenant or "common").strip().lower())[:63]
        return t or "common"
    except Exception:
        return "common"


def _sanitize_folder(folder: str) -> str:
    try:
        f = re.sub(r"[^a-z0-9/_-]", "", str(folder or "uploads").strip().lower())
        f = f.strip("/")
        if ".." in f:
            return "uploads"
        return f or "uploads"
    except Exception:
        return "uploads"


def upload_file(
    file_content: bytes,
    filename: str,
    tenant: str,
    folder: str = "uploads",
    content_type: str = "application/octet-stream",
) -> Tuple[bool, str, Optional[str]]:
    """
    Upload a file to B2 storage.

    Args:
        file_content: The file content as bytes
        filename: Original filename
        tenant: The gym/tenant subdomain for folder organization
        folder: Subfolder within tenant (uploads, logos, videos, etc.)
        content_type: MIME type of the file

    Returns:
        Tuple of (success, cdn_url or error_message, file_key)
    """
    client = get_s3_client()
    if not client:
        return False, "B2 client not available", None

    try:
        if file_content is None or len(file_content) <= 0:
            return False, "Empty file", None
        if MAX_B2_UPLOAD_BYTES and len(file_content) > MAX_B2_UPLOAD_BYTES:
            return False, "File too large", None
    except Exception:
        return False, "Invalid file", None

    # Generate unique filename with hash to avoid collisions
    file_hash = hashlib.sha256(file_content).hexdigest()[:10]
    tenant_safe = _sanitize_tenant(tenant)
    folder_safe = _sanitize_folder(folder)

    raw_name = os.path.basename(str(filename or "file"))
    raw_name = raw_name.replace(" ", "_")
    raw_name = re.sub(r"[^A-Za-z0-9._-]", "_", raw_name)
    # Keep extension but avoid extremely long names
    ext = Path(raw_name).suffix.lower()
    stem = Path(raw_name).stem
    stem = stem[:80] if stem else "file"
    safe_filename = f"{stem}{ext}".lower()

    # Build the full path: assets/{tenant}-assets/{folder}/{hash}_{filename}
    tenant_folder = f"{tenant_safe}-assets"
    file_key = (
        f"{B2_MEDIA_PREFIX}/{tenant_folder}/{folder_safe}/{file_hash}_{safe_filename}"
    )

    try:
        client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=file_key,
            Body=file_content,
            ContentType=content_type,
            # Make file publicly readable and cacheable
            ACL="public-read",
            CacheControl="max-age=31536000",
        )

        cdn_url = get_cdn_url(file_key)
        logger.info(f"Uploaded file to B2: {file_key}")
        return True, cdn_url, file_key

    except ClientError as e:
        error_msg = str(e)
        logger.error(f"B2 upload failed: {error_msg}")
        return False, error_msg, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error uploading to B2: {error_msg}")
        return False, error_msg, None


def delete_file(file_key: str) -> Tuple[bool, str]:
    """
    Delete a file from B2 storage.

    Args:
        file_key: The full path of the file in B2

    Returns:
        Tuple of (success, message)
    """
    client = get_s3_client()
    if not client:
        return False, "B2 client not available"

    try:
        key = str(file_key or "").lstrip("/")
        if not key or ".." in key:
            return False, "Invalid key"
        if not key.startswith(f"{B2_MEDIA_PREFIX}/"):
            return False, "Invalid key"
    except Exception:
        return False, "Invalid key"

    try:
        client.delete_object(Bucket=B2_BUCKET_NAME, Key=key)
        logger.info(f"Deleted file from B2: {file_key}")
        return True, "File deleted successfully"
    except ClientError as e:
        error_msg = str(e)
        logger.error(f"B2 delete failed: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error deleting from B2: {error_msg}")
        return False, error_msg


def list_tenant_files(tenant: str, folder: str = "") -> list:
    """
    List all files for a tenant in B2.

    Args:
        tenant: The gym subdomain
        folder: Optional subfolder to filter

    Returns:
        List of file objects with key, size, last_modified
    """
    client = get_s3_client()
    if not client:
        return []

    tenant_safe = _sanitize_tenant(tenant)
    tenant_folder = f"{tenant_safe}-assets"
    prefix = f"{B2_MEDIA_PREFIX}/{tenant_folder}/"
    if folder:
        folder_safe = _sanitize_folder(folder)
        prefix += f"{folder_safe}/"

    try:
        files = []
        token = None
        while True:
            if token:
                response = client.list_objects_v2(
                    Bucket=B2_BUCKET_NAME, Prefix=prefix, ContinuationToken=token
                )
            else:
                response = client.list_objects_v2(Bucket=B2_BUCKET_NAME, Prefix=prefix)
            for obj in response.get("Contents", []):
                files.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "url": get_cdn_url(obj["Key"]),
                    }
                )
            if response.get("IsTruncated"):
                token = response.get("NextContinuationToken")
                if not token:
                    break
            else:
                break
        return files
    except Exception as e:
        logger.error(f"Error listing B2 files: {e}")
        return []


def upload_logo(file_content: bytes, filename: str, tenant: str) -> Tuple[bool, str]:
    """
    Upload a gym logo.

    Args:
        file_content: Image bytes
        filename: Original filename
        tenant: Gym subdomain

    Returns:
        Tuple of (success, cdn_url or error_message)
    """
    content_type = "image/png"
    ext = Path(filename).suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        content_type = "image/jpeg"
    elif ext == ".webp":
        content_type = "image/webp"
    elif ext == ".svg":
        content_type = "image/svg+xml"

    success, url, _ = upload_file(file_content, filename, tenant, "logos", content_type)
    return success, url


def upload_exercise_video(
    file_content: bytes, filename: str, tenant: str
) -> Tuple[bool, str]:
    """
    Upload an exercise video.

    Args:
        file_content: Video bytes
        filename: Original filename
        tenant: Gym subdomain

    Returns:
        Tuple of (success, cdn_url or error_message)
    """
    content_type = "video/mp4"
    ext = Path(filename).suffix.lower()
    if ext == ".webm":
        content_type = "video/webm"
    elif ext == ".mov":
        content_type = "video/quicktime"

    success, url, _ = upload_file(
        file_content, filename, tenant, "videos", content_type
    )
    return success, url


# ============================================================================
# Compatibility Layer (for code using old StorageService interface)
# ============================================================================


def simple_upload(
    file_data: bytes, file_name: str, content_type: str, subfolder: str = ""
) -> Optional[str]:
    """
    Simple upload function compatible with old StorageService.upload_file() interface.

    Args:
        file_data: File content as bytes
        file_name: Original filename
        content_type: MIME type
        subfolder: Path like "exercises/tenant" or "logos/tenant"

    Returns:
        CDN URL if successful, None if failed
    """
    # Parse tenant and folder from subfolder (e.g., "exercises/mygym" -> tenant="mygym", folder="exercises")
    parts = subfolder.strip("/").split("/", 1)
    if len(parts) == 2:
        folder, tenant = parts[0], parts[1]
    elif len(parts) == 1:
        folder = parts[0]
        tenant = "common"
    else:
        folder = "uploads"
        tenant = "common"

    success, url, _ = upload_file(file_data, file_name, tenant, folder, content_type)
    return url if success else None


def get_file_url(file_path: str) -> str:
    """
    Get public URL for a file. Compatible with old StorageService.get_file_url().

    If the path is already a full URL, returns it unchanged.
    Otherwise, constructs CDN URL.
    """
    if not file_path:
        return ""

    # Local/static paths
    if file_path.startswith("/"):
        return file_path

    # Full URL
    if file_path.startswith("http://") or file_path.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(file_path)
            path = parsed.path or ""
            host = str(parsed.netloc or "").lower()

            # Any host: if URL contains /file/<bucket>/<key>, rewrite to direct B2
            marker = f"/file/{B2_BUCKET_NAME}/"
            if marker in path:
                key = path.split(marker, 1)[1].lstrip("/")
                if key and ".." not in key:
                    return get_cdn_url(_normalize_key_layout(key))

            # Backblaze S3-style URLs:
            # - https://<bucket>.s3.backblazeb2.com/<key>
            # - https://s3.<region>.backblazeb2.com/<bucket>/<key>
            try:
                if "backblazeb2.com" in host and "/file/" not in path:
                    p = path.lstrip("/")
                    if p and ".." not in p:
                        if host.endswith(".s3.backblazeb2.com") and host.count(".") >= 3:
                            return get_cdn_url(_normalize_key_layout(p))
                        if host.startswith("s3.") and host.endswith(".backblazeb2.com"):
                            parts = p.split("/", 1)
                            if len(parts) == 2 and parts[0] == str(B2_BUCKET_NAME):
                                return get_cdn_url(_normalize_key_layout(parts[1]))
            except Exception:
                pass

            # Legacy CDN mapping directly to keys (e.g. https://<cdn>/<assets/...>)
            try:
                key2 = path.lstrip("/")
                if key2.startswith(f"{B2_MEDIA_PREFIX}/") and ".." not in key2:
                    # Be conservative: only rewrite if it looks like our media layout
                    if any(
                        seg in key2.split("/")
                        for seg in ("logos", "videos", "exercises", "uploads")
                    ):
                        return get_cdn_url(_normalize_key_layout(key2))
            except Exception:
                pass

            # CDN/custom-domain URLs that map directly to a B2 key (admin assets):
            # e.g. https://<domain>/<subdominio>-assets/<file>
            try:
                key3 = path.lstrip("/")
                first = key3.split("/", 1)[0] if key3 else ""
                if key3 and ".." not in key3 and first.endswith("-assets"):
                    return get_cdn_url(_normalize_key_layout(key3))
            except Exception:
                pass

            return file_path
        except Exception:
            return file_path

    # Key/path stored in DB
    return get_cdn_url(_normalize_key_layout(file_path))


def extract_file_key(file_url_or_key: str) -> Optional[str]:
    """Best-effort extraction of B2 object key from a stored URL or key.

    Returns a key only if it looks like an object under the configured
    `B2_MEDIA_PREFIX` (default: "assets"). This prevents accidental deletion
    of external URLs.
    """
    try:
        s = str(file_url_or_key or "").strip()
        if not s:
            return None

        # Local/static or absolute paths are not B2 keys
        if s.startswith("/"):
            return None

        prefix = f"{B2_MEDIA_PREFIX}/"

        # If already looks like a key
        if not s.startswith("http://") and not s.startswith("https://"):
            if s.startswith(prefix) and ".." not in s:
                return _normalize_key_layout(s)
            return None

        parsed = urllib.parse.urlparse(s)
        path = parsed.path or ""

        # Case 1: Direct B2 URL pattern
        # https://<host>/file/<bucket>/<key>
        marker = f"/file/{B2_BUCKET_NAME}/"
        if marker in path:
            key = path.split(marker, 1)[1].lstrip("/")
            if key.startswith(prefix) and ".." not in key:
                return _normalize_key_layout(key)
            return None

        # Case 2: URLs that map directly to keys: https://<host>/<assets/...>
        try:
            key2 = path.lstrip("/")
            if key2.startswith(prefix) and ".." not in key2:
                if any(
                    seg in key2.split("/")
                    for seg in ("logos", "videos", "exercises", "uploads")
                ):
                    return _normalize_key_layout(key2)
        except Exception:
            pass

        # Unknown URL
        return None
    except Exception:
        return None
