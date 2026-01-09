"""
B2 Storage Service for IronHub
Handles file uploads to Backblaze B2 with Cloudflare CDN integration
"""

import os
import hashlib
import logging
from typing import Optional, Tuple
from pathlib import Path

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
B2_KEY_ID = os.getenv("B2_KEY_ID", "")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY", "")
B2_ENDPOINT_URL = os.getenv("B2_ENDPOINT_URL", "s3.us-east-005.backblazeb2.com")
B2_MEDIA_PREFIX = os.getenv("B2_MEDIA_PREFIX", "assets")
B2_PUBLIC_BASE_URL = os.getenv("B2_PUBLIC_BASE_URL", "https://f005.backblazeb2.com")
CDN_CUSTOM_DOMAIN = os.getenv("CDN_CUSTOM_DOMAIN", "")


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
        return boto3.client(
            's3',
            endpoint_url=f"https://{B2_ENDPOINT_URL}",
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APPLICATION_KEY,
            config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            )
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
    if CDN_CUSTOM_DOMAIN:
        return f"https://{CDN_CUSTOM_DOMAIN}/{file_path}"
    else:
        return f"{B2_PUBLIC_BASE_URL}/file/{B2_BUCKET_NAME}/{file_path}"


def upload_file(
    file_content: bytes,
    filename: str,
    tenant: str,
    folder: str = "uploads",
    content_type: str = "application/octet-stream"
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
    
    # Generate unique filename with hash to avoid collisions
    file_hash = hashlib.md5(file_content).hexdigest()[:8]
    safe_filename = filename.replace(" ", "_").lower()
    ext = Path(filename).suffix.lower()
    
    # Build the full path: assets/{tenant}/{folder}/{hash}_{filename}
    file_key = f"{B2_MEDIA_PREFIX}/{tenant}/{folder}/{file_hash}_{safe_filename}"
    
    try:
        client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=file_key,
            Body=file_content,
            ContentType=content_type,
            # Make file publicly readable
            ACL='public-read'
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
        client.delete_object(Bucket=B2_BUCKET_NAME, Key=file_key)
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
    
    prefix = f"{B2_MEDIA_PREFIX}/{tenant}/"
    if folder:
        prefix += f"{folder}/"
    
    try:
        response = client.list_objects_v2(Bucket=B2_BUCKET_NAME, Prefix=prefix)
        files = []
        for obj in response.get('Contents', []):
            files.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
                'url': get_cdn_url(obj['Key'])
            })
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
    if ext in ['.jpg', '.jpeg']:
        content_type = "image/jpeg"
    elif ext == '.webp':
        content_type = "image/webp"
    elif ext == '.svg':
        content_type = "image/svg+xml"
    
    success, url, _ = upload_file(file_content, filename, tenant, "logos", content_type)
    return success, url


def upload_exercise_video(file_content: bytes, filename: str, tenant: str) -> Tuple[bool, str]:
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
    if ext == '.webm':
        content_type = "video/webm"
    elif ext == '.mov':
        content_type = "video/quicktime"
    
    success, url, _ = upload_file(file_content, filename, tenant, "videos", content_type)
    return success, url


# ============================================================================
# Compatibility Layer (for code using old StorageService interface)
# ============================================================================

def simple_upload(
    file_data: bytes,
    file_name: str,
    content_type: str,
    subfolder: str = ""
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
    
    # Already a URL
    if file_path.startswith("http") or file_path.startswith("/"):
        return file_path
    
    return get_cdn_url(file_path)

