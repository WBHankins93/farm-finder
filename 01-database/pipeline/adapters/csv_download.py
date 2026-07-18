"""Adapter for producer directories distributed as CSV downloads."""
from __future__ import annotations

import csv
import io
import re
import urllib.request
from datetime import date
from typing import Iterable

from collect import CollectContext, adapter
from model import Contact, Farm, Geo, Provenance, slugify


_SPACE_RE = re.compile(r"\s+")
_TRUE_VALUES = {"true", "t", "yes", "y", "1"}
_FALSE_VALUES = {"", "false", "f", "no", "n", "0", "none", "null"}


def _normalized(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _clean(value: object) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()


def _as_columns(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value if _clean(item)]
    return [_normalized(value)] if _clean(value) else []


# These aliases are deliberately local to this adapter.  CSV directories tend
# to use human-readable headers, while the Farm model uses stable snake_case
# names.  A source-specific field_map can add or replace any of these matches.
_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id", "farm id", "producer id", "business id"),
    "name": (
        "name", "farm", "farm name", "producer", "producer name", "business",
        "business name", "company", "company name", "operation", "operation name",
    ),
    "state": ("state", "state code", "state abbreviation"),
    "region": ("region",),
    "county": ("county", "county name", "parish", "parish name", "county parish", "parish county"),
    "city": ("city", "town", "municipality"),
    "category": ("category", "type", "business type"),
    "products": ("products", "product", "product list", "products offered", "offerings"),
    "products_text": ("products text", "product description", "products description"),
    "website": ("website", "web site", "url", "website url", "web address"),
    "facebook_url": ("facebook", "facebook url", "facebook page"),
    "instagram_url": ("instagram", "instagram url", "instagram page"),
    "on_farm": ("on farm", "on farm sales", "farm stand", "farmstand"),
    "farmers_market": ("farmers market", "farmers markets", "market", "market sales"),
    "csa": ("csa", "community supported agriculture"),
    "online_store": ("online store", "online ordering", "online sales"),
    "ships": ("ships", "shipping", "delivery", "delivers"),
    "u_pick": ("u pick", "upick", "u pick sales", "pick your own"),
    "phone": ("phone", "telephone", "tel", "business phone", "mobile phone", "phone number", "contact phone"),
    "email": ("email", "e mail", "email address", "contact email"),
    "address": ("address", "street address", "mailing address", "physical address", "contact address"),
    "public": ("public", "public contact", "contact public"),
    "latitude": ("latitude", "lat", "geo latitude", "geo lat"),
    "longitude": ("longitude", "lon", "lng", "long", "geo longitude"),
    "precision": ("precision", "geo precision", "geographic precision"),
    "notes": ("notes", "description", "comments", "comment"),
    "eligible": ("eligible",),
    "qa_reason": ("qa reason", "qa_reason", "quality assurance reason"),
}

_ALIAS_TO_FIELD: dict[str, str] = {}
for _field, _aliases in _ALIASES.items():
    _ALIAS_TO_FIELD[_normalized(_field)] = _field
    for _alias in _aliases:
        _ALIAS_TO_FIELD[_normalized(_alias)] = _field


def _field_name(value: object) -> str | None:
    """Return a Farm field for a model name or a conventional column alias."""
    return _ALIAS_TO_FIELD.get(_normalized(value))


def _explicit_columns(source: dict) -> dict[str, str]:
    """Build normalized CSV-column -> Farm-field mappings.

    Configs may naturally express a map as either ``{"name": "Farm Name"}``
    or ``{"Farm Name": "name"}``; accepting both keeps source configs clear
    without making the adapter's contract depend on one dict orientation.
    """
    mapping: dict[str, str] = {}
    field_map = source.get("field_map", {}) or {}
    if not isinstance(field_map, dict):
        raise TypeError("source field_map must be a dict")

    for key, value in field_map.items():
        key_text = _normalized(key)
        values = _as_columns(value)
        if not key_text or not values:
            continue

        # An exact model field on the right indicates source-column -> model.
        right_field = _field_name(value) if isinstance(value, str) else None
        if isinstance(value, str) and right_field and _normalized(value) == _normalized(right_field):
            mapping[key_text] = right_field
            continue

        left_field = _field_name(key)
        if left_field:
            for column in values:
                mapping[column] = left_field
        elif right_field:
            mapping[key_text] = right_field
        else:
            raise ValueError(f"field_map entry does not name a Farm field: {key!r}: {value!r}")
    return mapping


def _row_values(row: dict[str, str | None], source: dict) -> dict[str, list[str]]:
    explicit = _explicit_columns(source)
    values: dict[str, list[str]] = {}
    for column, raw_value in row.items():
        if column is None:
            continue
        field = explicit.get(_normalized(column)) or _field_name(column)
        if field is not None:
            values.setdefault(field, []).append(_clean(raw_value))
    return values


def _first(values: dict[str, list[str]], field: str) -> str:
    for value in values.get(field, []):
        if value:
            return value
    return ""


def _combined(values: dict[str, list[str]], field: str) -> str:
    return "; ".join(value for value in values.get(field, []) if value)


def _boolean(value: str) -> bool:
    normalized = value.casefold().strip()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return bool(normalized)


def _products(text: str) -> list[str]:
    seen: list[str] = []
    for item in re.split(r"[,;\n]", text):
        item = item.strip(" .;")
        if item and item.casefold() not in {value.casefold() for value in seen}:
            seen.append(item)
    return seen


def _number(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _record(row: dict[str, str | None], source: dict, ctx: CollectContext) -> Farm | None:
    values = _row_values(row, source)
    name = _first(values, "name")
    if not name:
        return None

    state = _first(values, "state") or _clean(getattr(ctx, "state", ""))
    region = _first(values, "region") or _clean(getattr(ctx, "region", ""))
    product_values = _combined(values, "products")
    products_text = _first(values, "products_text") or product_values
    latitude = _number(_first(values, "latitude"))
    longitude = _number(_first(values, "longitude"))
    precision = _first(values, "precision")
    if not precision and latitude is not None and longitude is not None:
        precision = "point"

    farm_id = _first(values, "id") or f"{slugify(name)}-{state.casefold()}"
    return Farm(
        id=farm_id,
        name=name,
        state=state,
        region=region,
        county=_first(values, "county"),
        city=_first(values, "city"),
        category=_first(values, "category") or "Mixed",
        products=_products(product_values or products_text),
        products_text=products_text,
        website=_first(values, "website"),
        facebook_url=_first(values, "facebook_url"),
        instagram_url=_first(values, "instagram_url"),
        on_farm=_boolean(_first(values, "on_farm")),
        farmers_market=_boolean(_first(values, "farmers_market")),
        csa=_boolean(_first(values, "csa")),
        online_store=_boolean(_first(values, "online_store")),
        ships=_boolean(_first(values, "ships")),
        u_pick=_boolean(_first(values, "u_pick")),
        contact=Contact(
            phone=_first(values, "phone"),
            email=_first(values, "email"),
            address=_first(values, "address"),
            public=_boolean(_first(values, "public")),
        ),
        geo=Geo(latitude=latitude, longitude=longitude, precision=precision or "ungeocoded"),
        notes=_first(values, "notes"),
        provenance=Provenance(
            source=str(source.get("name", "")),
            source_url=str(source.get("url", "")),
            retrieved=date.today().isoformat(),
        ),
        eligible=_boolean(_first(values, "eligible")),
        qa_reason=_first(values, "qa_reason"),
    )


def _unique(records: Iterable[Farm]) -> Iterable[Farm]:
    seen: dict[str, int] = {}
    for record in records:
        base_id = record.id
        count = seen.get(base_id, 0) + 1
        seen[base_id] = count
        if count > 1:
            record.id = f"{base_id}-{count}"
        yield record


def _decode(payload: bytes, response: object) -> str:
    headers = getattr(response, "headers", None)
    get_charset = getattr(headers, "get_content_charset", None)
    encoding = get_charset() if get_charset else None
    return payload.decode(encoding or "utf-8-sig", errors="replace")


@adapter("csv_download")
def csv_download(source: dict, ctx: CollectContext) -> Iterable[Farm]:
    """Fetch a configured CSV directory and yield raw producer records."""
    response = urllib.request.urlopen(source["url"], timeout=30)
    try:
        text = _decode(response.read(), response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()

    reader = csv.DictReader(io.StringIO(text, newline=""), skipinitialspace=True)
    return _unique(
        record
        for row in reader
        if (record := _record(row, source, ctx)) is not None
    )
