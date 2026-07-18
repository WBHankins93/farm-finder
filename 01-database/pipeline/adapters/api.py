"""Adapter for producer directories exposed as JSON or REST APIs."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import date
from typing import Any, Iterable

from collect import CollectContext, adapter
from model import Contact, Farm, Geo, Provenance, slugify


_SPACE_RE = re.compile(r"\s+")
_TRUE_VALUES = {"true", "t", "yes", "y", "1"}
_FALSE_VALUES = {"", "false", "f", "no", "n", "0", "none", "null"}

_STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}
_STATE_FIPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}

_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id", "farm id", "producer id", "business id", "object id", "objectid"),
    "name": (
        "name", "farm", "farm name", "producer", "producer name", "business",
        "business name", "company", "company name", "operation", "operation name",
        "title", "title rendered",
    ),
    "state": ("state", "state code", "state abbreviation", "state_code", "us state"),
    "region": ("region",),
    "county": ("county", "county name", "parish", "parish name"),
    "city": ("city", "town", "municipality"),
    "category": ("category", "type", "business type"),
    "products": ("products", "product", "product list", "products offered", "offerings"),
    "products_text": ("products text", "product description", "products description"),
    "website": ("website", "web site", "website url", "web address", "url", "link"),
    "facebook_url": ("facebook", "facebook url", "facebook page"),
    "instagram_url": ("instagram", "instagram url", "instagram page"),
    "on_farm": ("on farm", "on farm sales", "farm stand", "farmstand"),
    "farmers_market": ("farmers market", "farmers markets", "market", "market sales"),
    "csa": ("csa", "community supported agriculture"),
    "online_store": ("online store", "online ordering", "online sales"),
    "ships": ("ships", "shipping", "delivery", "delivers"),
    "u_pick": ("u pick", "upick", "u pick sales", "pick your own"),
    "phone": ("phone", "telephone", "tel", "business phone", "mobile phone", "phone number"),
    "email": ("email", "e mail", "email address"),
    "address": ("address", "street address", "mailing address", "physical address"),
    "public": ("public", "public contact", "contact public"),
    "latitude": ("latitude", "lat", "geo latitude", "geo lat"),
    "longitude": ("longitude", "lon", "lng", "long", "geo longitude", "geo lng"),
    "precision": ("precision", "geo precision", "geographic precision"),
    "notes": ("notes", "description", "comments", "comment"),
    "eligible": ("eligible",),
    "qa_reason": ("qa reason", "qa_reason", "quality assurance reason"),
}


def _normalized(value: object) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _clean(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(_clean(item) for item in value if _clean(item))
    if isinstance(value, dict):
        return ""
    return _SPACE_RE.sub(" ", str("" if value is None else value)).strip()


_ALIAS_TO_FIELD: dict[str, str] = {}
for _field, _aliases in _ALIASES.items():
    _ALIAS_TO_FIELD[_normalized(_field)] = _field
    for _alias in _aliases:
        _ALIAS_TO_FIELD[_normalized(_alias)] = _field


def _field_name(value: object) -> str | None:
    normalized = _normalized(value)
    parts = normalized.split()
    for start in range(len(parts)):
        suffix = " ".join(parts[start:])
        field = _ALIAS_TO_FIELD.get(suffix)
        if field:
            return field
    return None


def _as_columns(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value if _clean(item)]
    return [_normalized(value)] if _clean(value) else []


def _explicit_fields(source: dict) -> dict[str, str]:
    mapping: dict[str, str] = {}
    field_map = source.get("field_map", {}) or {}
    if not isinstance(field_map, dict):
        raise TypeError("source field_map must be a dict")
    for key, value in field_map.items():
        key_text = _normalized(key)
        columns = _as_columns(value)
        if not key_text or not columns:
            continue
        right_field = _field_name(value) if isinstance(value, str) else None
        if isinstance(value, str) and right_field and _normalized(value) == _normalized(right_field):
            mapping[key_text] = right_field
            continue
        left_field = _field_name(key)
        if left_field:
            for column in columns:
                mapping[column] = left_field
        elif right_field:
            mapping[key_text] = right_field
        else:
            raise ValueError(f"field_map entry does not name a Farm field: {key!r}: {value!r}")
    return mapping


def _flatten(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix} {key}".strip()
            yield from _flatten(child, path)
    elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        return
    else:
        yield prefix, value


def _field_values(record: dict[str, Any], source: dict) -> dict[str, list[Any]]:
    explicit = _explicit_fields(source)
    values: dict[str, list[Any]] = {}
    for path, raw_value in _flatten(record):
        normalized_path = _normalized(path)
        field = explicit.get(normalized_path) or _field_name(path)
        if field is None:
            field = _field_name(path.split()[-1])
        if field is not None:
            values.setdefault(field, []).append(raw_value)
    return values


def _first(values: dict[str, list[Any]], field: str) -> Any:
    for value in values.get(field, []):
        if value not in (None, "", [], {}):
            return value
    return ""


def _text(values: dict[str, list[Any]], field: str) -> str:
    return _clean(_first(values, field))


def _combined(values: dict[str, list[Any]], field: str) -> str:
    return "; ".join(_clean(value) for value in values.get(field, []) if _clean(value))


def _boolean(value: Any) -> bool:
    normalized = _clean(value).casefold()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return bool(normalized)


def _products(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[,;\n]", _clean(value))
    result: list[str] = []
    for item in items:
        text = _clean(item).strip(" .;")
        if text and text.casefold() not in {existing.casefold() for existing in result}:
            result.append(text)
    return result


def _number(value: Any) -> float | None:
    if value in (None, "", []):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _state_code(value: Any) -> str:
    text = _clean(value).casefold()
    return _STATE_CODES.get(text, _STATE_FIPS.get(text.zfill(2), text.upper()))


def _matches_state(values: dict[str, list[Any]], ctx: CollectContext) -> bool:
    expected = _state_code(getattr(ctx, "state", ""))
    candidates = [_state_code(value) for value in values.get("state", []) if _clean(value)]
    return not candidates or any(candidate == expected for candidate in candidates)


def _coordinates(record: dict[str, Any]) -> tuple[float | None, float | None]:
    containers: list[Any] = [record]
    for key in ("geometry", "location", "coordinates"):
        value = record.get(key)
        if value is not None:
            containers.append(value)
    for container in containers:
        coordinates = container.get("coordinates") if isinstance(container, dict) else container
        if isinstance(coordinates, list) and len(coordinates) >= 2:
            longitude, latitude = _number(coordinates[0]), _number(coordinates[1])
            if latitude is not None and longitude is not None:
                return latitude, longitude
    return None, None


def _record(item: Any, source: dict, ctx: CollectContext) -> Farm | None:
    if not isinstance(item, dict):
        return None
    values = _field_values(item, source)
    if not _matches_state(values, ctx):
        return None
    name = _text(values, "name")
    if not name:
        return None

    state_value = _first(values, "state")
    state = _state_code(state_value) if state_value else _clean(getattr(ctx, "state", ""))
    product_values = _combined(values, "products")
    products_text = _text(values, "products_text") or product_values
    latitude = _number(_first(values, "latitude"))
    longitude = _number(_first(values, "longitude"))
    if latitude is None or longitude is None:
        coordinate_latitude, coordinate_longitude = _coordinates(item)
        latitude = latitude if latitude is not None else coordinate_latitude
        longitude = longitude if longitude is not None else coordinate_longitude
    precision = _text(values, "precision") or ("point" if latitude is not None and longitude is not None else "ungeocoded")

    farm_id = _clean(_first(values, "id")) or f"{slugify(name)}-{state.casefold()}"
    return Farm(
        id=farm_id,
        name=name,
        state=state,
        region=_text(values, "region") or _clean(getattr(ctx, "region", "")),
        county=_text(values, "county"),
        city=_text(values, "city"),
        category=_text(values, "category") or "Mixed",
        products=_products(_first(values, "products") or products_text),
        products_text=products_text,
        website=_text(values, "website"),
        facebook_url=_text(values, "facebook_url"),
        instagram_url=_text(values, "instagram_url"),
        on_farm=_boolean(_first(values, "on_farm")),
        farmers_market=_boolean(_first(values, "farmers_market")),
        csa=_boolean(_first(values, "csa")),
        online_store=_boolean(_first(values, "online_store")),
        ships=_boolean(_first(values, "ships")),
        u_pick=_boolean(_first(values, "u_pick")),
        contact=Contact(
            phone=_text(values, "phone"),
            email=_text(values, "email"),
            address=_text(values, "address"),
            public=_boolean(_first(values, "public")),
        ),
        geo=Geo(latitude=latitude, longitude=longitude, precision=precision),
        notes=_text(values, "notes"),
        provenance=Provenance(
            source=str(source.get("name", "")),
            source_url=str(source.get("url", "")),
            retrieved=date.today().isoformat(),
        ),
        eligible=_boolean(_first(values, "eligible")),
        qa_reason=_text(values, "qa_reason"),
    )


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "data", "items", "records", "farms", "members", "entries", "features"):
        if key in payload:
            nested = _items(payload[key])
            if nested:
                return nested
            if isinstance(payload[key], list):
                return []
    if any(_field_name(key) == "name" for key in payload):
        return [payload]
    return []


def _page_url(url: str, page_param: str, page: int) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = [(key, value) for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True) if key != page_param]
    query.append((page_param, str(page)))
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))


def _decode(payload: bytes, response: object) -> str:
    headers = getattr(response, "headers", None)
    get_charset = getattr(headers, "get_content_charset", None)
    encoding = get_charset() if get_charset else None
    return payload.decode(encoding or "utf-8-sig", errors="replace")


def _fetch(url: str) -> Any:
    response = urllib.request.urlopen(url, timeout=30)
    try:
        return json.loads(_decode(response.read(), response))
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def _unique(records: Iterable[Farm]) -> Iterable[Farm]:
    seen: dict[str, int] = {}
    for record in records:
        base_id = record.id
        count = seen.get(base_id, 0) + 1
        seen[base_id] = count
        if count > 1:
            record.id = f"{base_id}-{count}"
        yield record


@adapter("api")
def api(source: dict, ctx: CollectContext) -> Iterable[Farm]:
    """Fetch a JSON/REST directory and yield raw producer records."""
    page_param = source.get("page_param")
    pages = [source["url"]] if not page_param else []
    page = int(source.get("page_start", 1))
    records: list[Farm] = []
    seen_payloads: set[str] = set()

    while True:
        url = pages[0] if pages else _page_url(source["url"], str(page_param), page)
        payload = _fetch(url)
        signature = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        if page_param and signature in seen_payloads:
            break
        seen_payloads.add(signature)
        items = _items(payload)
        if not items:
            break
        for item in items:
            record = _record(item, source, ctx)
            if record is not None:
                records.append(record)
        if not page_param:
            break
        page += 1
        pages.clear()

    return _unique(records)
