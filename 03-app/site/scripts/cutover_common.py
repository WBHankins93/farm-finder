from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SITE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SITE_ROOT / "config" / "source-of-truth.json"
INFRA_ENV_PATH = SITE_ROOT / "infra" / ".env"


def load_local_env(path: Path = INFRA_ENV_PATH) -> None:
    """Load simple KEY=VALUE local settings without overriding process secrets."""
    if not path.is_file():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def workbook_path(manifest: dict[str, Any]) -> Path:
    return (SITE_ROOT / manifest["release"]["workspacePath"]).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def key_fragment(value: object) -> str:
    normalized = normalized_name(value)
    return normalized.replace(" ", "-") or "unknown"


def json_value(value: object) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def record_hash(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(record)).hexdigest()


def source_records(rows: Iterable[dict[str, object]]) -> list[dict[str, Any]]:
    """Create stable evidence keys without treating names as canonical identities."""
    prepared: list[tuple[int, str, str, dict[str, Any]]] = []
    for row in rows:
        clean_row = {str(key): json_value(value) for key, value in row.items()}
        base_key = (
            f"{key_fragment(clean_row.get('Source Tab'))}:"
            f"{key_fragment(clean_row.get('Farm Name'))}"
        )
        prepared.append((len(prepared), base_key, record_hash(clean_row), clean_row))

    # Occurrence order is not evidence identity: spreadsheet row order can change
    # between exports. Sort each name/source group by the content hash before
    # assigning a suffix, while preserving the caller's order in the returned list.
    grouped: dict[str, list[tuple[int, str, str, dict[str, Any]]]] = {}
    for item in prepared:
        grouped.setdefault(item[1], []).append(item)

    source_keys: dict[int, str] = {}
    for base_key, items in grouped.items():
        hash_occurrences: Counter[str] = Counter()
        for index, _, digest, _ in sorted(items, key=lambda item: (item[2], item[3])):
            hash_occurrences[digest] += 1
            source_keys[index] = f"{base_key}:{digest}:{hash_occurrences[digest]:02d}"

    return [
        {
            "source_record_key": source_keys[index],
            "record_hash": digest,
            "raw_data": clean_row,
        }
        for index, _, digest, clean_row in prepared
    ]


def duplicate_groups(records: Iterable[dict[str, Any]]) -> list[str]:
    names = [normalized_name(row["raw_data"].get("Farm Name")) for row in records]
    counts = Counter(names)
    return sorted(name for name, count in counts.items() if name and count > 1)


def candidate_entity_count(records: Iterable[dict[str, Any]]) -> int:
    return len(
        {
            normalized_name(row["raw_data"].get("Farm Name"))
            for row in records
            if normalized_name(row["raw_data"].get("Farm Name"))
        }
    )


@dataclass(frozen=True)
class RuntimeSettings:
    database_url: str
    object_storage_endpoint: str
    object_storage_region: str
    object_storage_access_key: str
    object_storage_secret_key: str
    source_release_bucket: str


def runtime_settings() -> RuntimeSettings:
    load_local_env()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        user = os.getenv("POSTGRES_USER", "farmfinder")
        password = os.getenv("POSTGRES_PASSWORD", "farmfinder_local")
        port = os.getenv("POSTGRES_PORT", "54329")
        database = os.getenv("POSTGRES_DB", "farmfinder")
        database_url = f"postgresql://{user}:{password}@127.0.0.1:{port}/{database}"
    return RuntimeSettings(
        database_url=database_url,
        object_storage_endpoint=os.getenv(
            "OBJECT_STORAGE_ENDPOINT", "http://127.0.0.1:9000"
        ),
        object_storage_region=os.getenv("OBJECT_STORAGE_REGION", "us-east-1"),
        object_storage_access_key=os.getenv(
            "OBJECT_STORAGE_ACCESS_KEY", "farmfinder_local"
        ),
        object_storage_secret_key=os.getenv(
            "OBJECT_STORAGE_SECRET_KEY", "farmfinder_local_secret"
        ),
        source_release_bucket=os.getenv("SOURCE_RELEASE_BUCKET", ""),
    )


def storage_client(settings: RuntimeSettings):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.object_storage_endpoint,
        region_name=settings.object_storage_region,
        aws_access_key_id=settings.object_storage_access_key,
        aws_secret_access_key=settings.object_storage_secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_versioned_bucket(client, bucket: str, region: str) -> None:
    from botocore.exceptions import ClientError

    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        kwargs: dict[str, Any] = {"Bucket": bucket}
        if region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        client.create_bucket(**kwargs)

    versioning = client.get_bucket_versioning(Bucket=bucket)
    if versioning.get("Status") != "Enabled":
        client.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        versioning = client.get_bucket_versioning(Bucket=bucket)
    if versioning.get("Status") != "Enabled":
        raise RuntimeError(f"object versioning is not enabled for bucket {bucket!r}")


def upload_immutable_release(
    client,
    *,
    bucket: str,
    object_key: str,
    path: Path,
    sha256: str,
    content_type: str,
) -> str:
    from botocore.exceptions import ClientError

    try:
        existing = client.head_object(Bucket=bucket, Key=object_key)
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code not in {"404", "NoSuchKey", "NotFound"}:
            raise
    else:
        if existing.get("Metadata", {}).get("sha256") != sha256:
            raise RuntimeError(
                "refusing to overwrite an existing release key with different bytes: "
                f"s3://{bucket}/{object_key}"
            )
        version_id = existing.get("VersionId")
        if not version_id:
            raise RuntimeError("stored release has no object version ID")
        return str(version_id)

    with path.open("rb") as source:
        response = client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=source,
            ContentLength=path.stat().st_size,
            ContentType=content_type,
            Metadata={"sha256": sha256},
        )
    version_id = response.get("VersionId")
    if not version_id:
        raise RuntimeError("object store did not return a version ID")
    return str(version_id)
