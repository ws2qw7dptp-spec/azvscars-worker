"""
cloudflare_storage.py
Handles:
  - Cloudflare R2  (S3-compatible object storage) → stores all images
  - Cloudflare KV  (key-value store)             → stores all session metadata
No local filesystem persistence needed.  Render can restart/spin-down freely.
"""
import os
import json
import time
import requests
import boto3
from botocore.config import Config


# ─── Env vars (set in Render → Environment) ────────────────────────────────────
CF_ACCOUNT_ID    = os.environ.get("CF_ACCOUNT_ID",    "")
CF_API_TOKEN     = os.environ.get("CF_API_TOKEN",     "")
CF_KV_NS_ID      = os.environ.get("CF_KV_NAMESPACE_ID", "")   # filled after KV namespace created
R2_ACCESS_KEY    = os.environ.get("R2_ACCESS_KEY_ID",  "")
R2_SECRET_KEY    = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET        = os.environ.get("R2_BUCKET_NAME",   "azvscars-slides")
# Public URL for R2 bucket (enable in R2 → bucket → Settings → Public access)
R2_PUBLIC_URL    = os.environ.get("R2_PUBLIC_URL",    "").rstrip("/")

# ─── R2 Client ─────────────────────────────────────────────────────────────────

def _r2_client():
    missing = [
        name for name, value in {
            "CF_ACCOUNT_ID": CF_ACCOUNT_ID,
            "R2_ACCESS_KEY_ID": R2_ACCESS_KEY,
            "R2_SECRET_ACCESS_KEY": R2_SECRET_KEY,
            "R2_BUCKET_NAME": R2_BUCKET,
        }.items() if not value
    ]
    if missing:
        raise RuntimeError(f"Missing R2 configuration: {', '.join(missing)}")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{CF_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )

def r2_upload_file(local_path: str, key: str, content_type: str = "image/png") -> str:
    """Upload a local file to R2. Returns a presigned public URL valid for 7 days."""
    s3_client = _r2_client()
    with open(local_path, "rb") as f:
        s3_client.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=f.read(),
            ContentType=content_type,
        )
    # Generate a presigned URL so images work in the dashboard and Meta API without public bucket access
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': R2_BUCKET, 'Key': key},
        ExpiresIn=604800  # 7 days
    )

def r2_download_to(key: str, local_path: str):
    """Download a file from R2 to a local path."""
    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
    _r2_client().download_file(R2_BUCKET, key, local_path)

def r2_public_url(key: str) -> str:
    return f"{R2_PUBLIC_URL}/{key}"

def r2_delete_folder(prefix: str):
    """Delete all objects with a given prefix (e.g. sid/)."""
    s3_client = _r2_client()
    try:
        objs = s3_client.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        if 'Contents' in objs:
            objects_to_delete = [{'Key': obj['Key']} for obj in objs['Contents']]
            s3_client.delete_objects(Bucket=R2_BUCKET, Delete={'Objects': objects_to_delete})
    except Exception as e:
        print(f"R2 delete error: {e}")

# ─── KV Helpers ────────────────────────────────────────────────────────────────

def _kv_headers():
    return {"Authorization": f"Bearer {CF_API_TOKEN}",
            "Content-Type": "application/json"}

def kv_put(key: str, value, ttl_seconds: int = None):
    """Write any JSON-serialisable value to Cloudflare KV."""
    if not CF_KV_NS_ID or not CF_ACCOUNT_ID or not CF_API_TOKEN:
        return   # KV not configured yet — skip silently
    url    = (f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
              f"/storage/kv/namespaces/{CF_KV_NS_ID}/values/{key}")
    params = {}
    if ttl_seconds:
        params["expiration_ttl"] = ttl_seconds
    resp = requests.put(url, headers=_kv_headers(),
                        data=json.dumps(value, ensure_ascii=False),
                        params=params)
    resp.raise_for_status()

def kv_get(key: str):
    """Read a JSON value from Cloudflare KV. Returns None if not found."""
    if not CF_KV_NS_ID or not CF_ACCOUNT_ID or not CF_API_TOKEN:
        return None
    url  = (f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
            f"/storage/kv/namespaces/{CF_KV_NS_ID}/values/{key}")
    resp = requests.get(url, headers={"Authorization": f"Bearer {CF_API_TOKEN}"})
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return resp.text

def kv_delete(key: str):
    """Delete a key from Cloudflare KV."""
    if not CF_KV_NS_ID or not CF_ACCOUNT_ID or not CF_API_TOKEN:
        return
    url = (f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
           f"/storage/kv/namespaces/{CF_KV_NS_ID}/values/{key}")
    resp = requests.delete(url, headers={"Authorization": f"Bearer {CF_API_TOKEN}"})
    if resp.status_code != 404:
        resp.raise_for_status()

def kv_list_keys(prefix: str = "", limit: int = 100) -> list:
    """List all keys in the KV namespace, optionally filtered by prefix."""
    if not CF_KV_NS_ID or not CF_ACCOUNT_ID or not CF_API_TOKEN:
        return []
    url    = (f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
              f"/storage/kv/namespaces/{CF_KV_NS_ID}/keys")
    params = {"limit": limit}
    if prefix:
        params["prefix"] = prefix
    resp   = requests.get(url, headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
                          params=params)
    resp.raise_for_status()
    return [item["name"] for item in resp.json().get("result", [])]

# ─── Session helpers ────────────────────────────────────────────────────────────

SESSION_PREFIX = "session:"
INDEX_KEY      = "sessions:index"

def session_save(sid: str, meta: dict):
    """Save session metadata to KV."""
    kv_put(f"{SESSION_PREFIX}{sid}", meta)
    # Update global index (lightweight: just id + names + date + is_published)
    index = kv_get(INDEX_KEY)
    if not isinstance(index, list):
        index = []
    # Remove duplicate if re-saving
    index = [s for s in index if s.get("sid") != sid]
    index.append({
        "sid":          sid,
        "post_type":    meta.get("post_type", ""),
        "story_slot":   meta.get("story_slot", ""),
        "car1":         meta.get("car1_name", ""),
        "car2":         meta.get("car2_name", ""),
        "alt_text":     meta.get("alt_text", "") or meta.get("data", {}).get("alt_text", ""),
        "image_description": meta.get("image_description", "") or meta.get("data", {}).get("image_description", ""),
        "publish_strategy": meta.get("publish_strategy", {}),
        "created_at":   meta.get("created_at", ""),
        "is_published": meta.get("is_published", False),
        "published":    meta.get("published", {}),
    })
    # Sort descending by created_at
    index.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    kv_put(INDEX_KEY, index[:500])   # keep last 500 efficiently

def session_delete(sid: str):
    """Delete a session entirely from KV and R2."""
    kv_delete(f"{SESSION_PREFIX}{sid}")
    # Update index
    index = kv_get(INDEX_KEY)
    if isinstance(index, list):
        index = [s for s in index if s.get("sid") != sid]
        kv_put(INDEX_KEY, index)
    # Delete from R2
    r2_delete_folder(f"{sid}/")

def session_load(sid: str) -> dict:
    """Load session metadata from KV."""
    return kv_get(f"{SESSION_PREFIX}{sid}")

def sessions_index() -> list:
    """Return the recent sessions index list."""
    return kv_get(INDEX_KEY) or []
