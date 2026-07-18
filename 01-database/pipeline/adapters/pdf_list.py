"""Adapter for producer lists distributed as PDFs.

The pipeline deliberately has no third-party dependencies.  This module therefore
contains the small part of PDF extraction it needs: common stream filters and the
positioned text operators used by ordinary certificate and directory PDFs.  It is
not intended to be a general PDF renderer.
"""
from __future__ import annotations

import base64
import binascii
import re
import urllib.request

import httpget
import zlib
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable

from collect import CollectContext, adapter
from model import Contact, Farm, Provenance, slugify


_STREAM_START_RE = re.compile(rb"(?<![A-Za-z])stream[ \t]*(?:\r\n|\r|\n)")
_PHONE_RE = re.compile(r"(?:\+?1[ .-]*)?(?:\(?\d{3}\)?[ .-]*)\d{3}[ .-]*\d{4}")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_CITY_STATE_ZIP_RE = re.compile(
    r"(?P<city>[A-Za-z][A-Za-z .'-]*?),\s*(?P<state>[A-Za-z]{2})\.?\s+"
    r"(?P<zip>\d{5}(?:-\d{4})?)\b"
)
_CITY_ZIP_RE = re.compile(
    r"(?P<city>[A-Za-z][A-Za-z .'-]*?)\s+(?P<state>[A-Za-z]{2})\.?\s+"
    r"(?P<zip>\d{5}(?:-\d{4})?)\b"
)
_ADDRESS_LINE_RE = re.compile(r"^(?:P\.?\s*O\.?\s*Box|\d{1,6}(?:\s|$))", re.I)
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class _TextItem:
    text: str
    x: float
    y: float


@dataclass
class _TextRow:
    y: float
    items: list[_TextItem]


@dataclass
class _Layout:
    columns: dict[str, float]
    header_y: float
    anchor_x: float


def _filter_names(dictionary: bytes) -> list[bytes]:
    match = re.search(rb"/Filter\s*(?:\[(.*?)\]|(\/\S+))", dictionary, re.DOTALL)
    if not match:
        return []
    values = match.group(1) or match.group(2) or b""
    return re.findall(rb"/(FlateDecode|ASCIIHexDecode|ASCII85Decode|RunLengthDecode)", values)


def _decode_stream(dictionary: bytes, payload: bytes) -> bytes:
    """Decode the filters used by the public PDFs in the source configs."""
    value = payload.rstrip(b"\r\n")
    for name in _filter_names(dictionary):
        if name == b"FlateDecode":
            value = zlib.decompress(value)
        elif name == b"ASCIIHexDecode":
            hex_value = re.sub(rb"\s+|>$", b"", value)
            if len(hex_value) % 2:
                hex_value += b"0"
            value = binascii.unhexlify(hex_value)
        elif name == b"ASCII85Decode":
            try:
                value = base64.a85decode(value, adobe=True)
            except ValueError:
                value = base64.a85decode(value)
        elif name == b"RunLengthDecode":
            out = bytearray()
            i = 0
            while i < len(value):
                length = value[i]
                i += 1
                if length == 128:
                    break
                if length < 128:
                    out.extend(value[i : i + length + 1])
                    i += length + 1
                elif i < len(value):
                    out.extend(value[i : i + 1] * (257 - length))
                    i += 1
            value = bytes(out)
        else:
            raise ValueError(f"unsupported PDF stream filter: {name.decode('ascii', 'replace')}")
    return value


def _literal_string(data: bytes, start: int) -> tuple[bytes, int]:
    out = bytearray()
    depth = 1
    i = start + 1
    escapes = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
    while i < len(data):
        char = data[i]
        if char == ord("\\"):
            i += 1
            if i >= len(data):
                break
            if data[i] in b"\r\n":
                if data[i] == ord("\r") and i + 1 < len(data) and data[i + 1] == ord("\n"):
                    i += 1
                i += 1
                continue
            if data[i] in escapes:
                out.append(escapes[data[i]])
            elif data[i] in b"()\\":
                out.append(data[i])
            elif 48 <= data[i] <= 55:
                digits = [data[i]]
                while len(digits) < 3 and i + 1 < len(data) and 48 <= data[i + 1] <= 55:
                    i += 1
                    digits.append(data[i])
                out.append(int(bytes(digits), 8))
            else:
                out.append(data[i])
        elif char == ord("("):
            depth += 1
            out.append(char)
        elif char == ord(")"):
            depth -= 1
            if depth == 0:
                return bytes(out), i + 1
            out.append(char)
        else:
            out.append(char)
        i += 1
    return bytes(out), i


def _tokenize(data: bytes, start: int = 0, stop: int | None = None) -> tuple[list[Any], int]:
    """Tokenize just enough PDF content syntax for text-showing operators."""
    tokens: list[Any] = []
    i = start
    end = len(data) if stop is None else stop
    whitespace = b" \t\r\n\x00\f"
    delimiters = b"()<>[]{}/%"
    while i < end:
        if data[i] in whitespace:
            i += 1
            continue
        if data[i] == ord("%"):
            newline = data.find(b"\n", i + 1, end)
            i = end if newline < 0 else newline + 1
            continue
        if data[i] == ord("("):
            value, i = _literal_string(data, i)
            tokens.append(("string", value))
            continue
        if data[i : i + 2] == b"<<":
            close = data.find(b">>", i + 2, end)
            i = end if close < 0 else close + 2
            tokens.append("dictionary")
            continue
        if data[i] == ord("<") and (i + 1 >= end or data[i + 1] != ord("<")):
            close = data.find(b">", i + 1, end)
            if close < 0:
                close = end
            value = re.sub(rb"\s", b"", data[i + 1 : close])
            if len(value) % 2:
                value += b"0"
            try:
                decoded = binascii.unhexlify(value or b"")
            except binascii.Error:
                decoded = b""
            tokens.append(("string", decoded))
            i = min(close + 1, end)
            continue
        if data[i] == ord("["):
            array, i = _tokenize(data, i + 1, end)
            tokens.append(("array", array))
            continue
        if data[i] == ord("]"):
            return tokens, i + 1
        j = i + 1
        while j < end and data[j] not in whitespace and data[j] not in delimiters:
            j += 1
        raw = data[i:j]
        try:
            tokens.append(float(raw))
        except ValueError:
            tokens.append(raw.decode("latin-1"))
        i = j
    return tokens, i


def _show_text(value: Any) -> str:
    if isinstance(value, tuple) and value and value[0] == "string":
        return value[1].decode("latin-1", "replace")
    if isinstance(value, tuple) and value and value[0] == "array":
        return "".join(_show_text(item) for item in value[1])
    return ""


def _text_items(content: bytes) -> list[_TextItem]:
    items: list[_TextItem] = []
    for block in re.findall(rb"\bBT\b(.*?)\bET\b", content, re.DOTALL):
        tokens, _ = _tokenize(block)
        operands: list[Any] = []
        x = y = line_x = line_y = 0.0
        leading = 0.0
        for token in tokens:
            if not isinstance(token, str):
                operands.append(token)
                continue
            op = token
            if op in {"Td", "TD"} and len(operands) >= 2:
                line_x += float(operands[-2])
                line_y += float(operands[-1])
                x, y = line_x, line_y
                if op == "TD":
                    leading = -float(operands[-1])
                operands = []
            elif op == "Tm" and len(operands) >= 6:
                x, y = float(operands[-2]), float(operands[-1])
                line_x, line_y = x, y
                operands = []
            elif op == "TL" and operands:
                leading = float(operands[-1])
                operands = []
            elif op == "Tj" and operands:
                text = _show_text(operands[-1]).strip()
                if text:
                    items.append(_TextItem(text, x, y))
                operands = []
            elif op == "TJ" and operands:
                text = _show_text(operands[-1]).strip()
                if text:
                    items.append(_TextItem(text, x, y))
                operands = []
            elif op == "'" and operands:
                line_y -= leading
                x, y = line_x, line_y
                text = _show_text(operands[-1]).strip()
                if text:
                    items.append(_TextItem(text, x, y))
                operands = []
            elif op == '"' and operands:
                line_y -= leading
                x, y = line_x, line_y
                text = _show_text(operands[-1]).strip()
                if text:
                    items.append(_TextItem(text, x, y))
                operands = []
            elif op == "T*":
                line_y -= leading
                x, y = line_x, line_y
                operands = []
            else:
                operands = []
    return items


def _pdf_pages(payload: bytes) -> list[list[_TextItem]]:
    if not payload.lstrip().startswith(b"%PDF-"):
        raise ValueError("source does not contain a PDF document")
    pages: list[list[_TextItem]] = []
    for match in _STREAM_START_RE.finditer(payload):
        end = payload.find(b"endstream", match.end())
        if end < 0:
            break
        object_start = payload.rfind(b"obj", 0, match.start())
        dictionary = payload[object_start + 3 : match.start()] if object_start >= 0 else b""
        stream = payload[match.end() : end]
        try:
            decoded = _decode_stream(dictionary, stream)
        except (binascii.Error, ValueError, zlib.error):
            continue
        items = _text_items(decoded)
        if items:
            pages.append(items)
    return pages


def _rows(items: list[_TextItem]) -> list[_TextRow]:
    rows: list[_TextRow] = []
    for item in sorted(items, key=lambda value: (-value.y, value.x)):
        if rows and abs(rows[-1].y - item.y) <= 2.0:
            rows[-1].items.append(item)
        else:
            rows.append(_TextRow(item.y, [item]))
    return rows


def _flat(row: _TextRow) -> str:
    return _SPACE_RE.sub(" ", " ".join(item.text for item in sorted(row.items, key=lambda value: value.x))).strip()


def _field_name(text: str) -> str | None:
    key = re.sub(r"[^a-z]+", " ", text.lower()).strip()
    if key in {"parish", "county", "parish county"}:
        return "county"
    if key in {"name", "farm name", "producer", "producer name"}:
        return "name"
    if key in {"business name", "company name"}:
        return "business_name"
    if key in {"licensee name", "licensed name"}:
        return "licensee_name"
    if key in {"address", "street address"}:
        return "address"
    if key == "city":
        return "city"
    if key in {"zip", "zip code", "postal code"}:
        return "zip"
    if key in {"phone", "telephone", "business phone", "mobile phone"}:
        return "phone"
    if key == "email":
        return "email"
    if key in {"products", "products offered", "product"}:
        return "products"
    if key.startswith("license") or key in {"permit", "permit number", "per", "mit"}:
        return "license"
    return None


def _layout_for(rows: list[_TextRow]) -> _Layout | None:
    for row in rows:
        values = {_field_name(item.text) for item in row.items}
        values.discard(None)
        text = _flat(row).lower()
        if "name" not in values and "business_name" not in values and "licensee_name" not in values:
            continue
        if not ({"county", "address", "city", "phone", "email", "license"} & values):
            continue
        columns: dict[str, float] = {}
        for item in row.items:
            field = _field_name(item.text)
            if field and field not in columns:
                columns[field] = item.x
        if "business_name" in columns and "licensee_name" in columns:
            # The business name is the producer identity when present; retain
            # the licensee as a fallback for rows with no business name.
            columns["name"] = columns["business_name"]
        elif "name" not in columns and "licensee_name" in columns:
            columns["name"] = columns["licensee_name"]
        if "name" not in columns:
            continue
        anchor = min(columns.get("county", columns["name"]), columns["name"])
        return _Layout(columns, row.y, anchor)
    return None


def _logical_rows(rows: list[_TextRow], layout: _Layout, header_y: float | None) -> list[_TextRow]:
    result: list[_TextRow] = []
    current: _TextRow | None = None
    base_y = 0.0
    name_x = layout.columns["name"]
    for row in rows:
        if header_y is not None and row.y >= header_y - 2.0:
            continue
        text = _flat(row)
        if not text or re.search(r"\bpage\s+\d+\b", text, re.I):
            continue
        has_name_column = any(abs(item.x - name_x) <= 18 for item in row.items)
        has_anchor = any(abs(item.x - layout.anchor_x) <= 18 for item in row.items)
        if current is None or has_anchor or row.y < base_y - 13.0:
            if current is not None:
                result.append(current)
            current = _TextRow(row.y, list(row.items))
            base_y = row.y
        elif row.y >= base_y - 13.0:
            # Wrapped name/address/contact lines have no first-column value and
            # sit about ten points below the row's baseline in these PDFs.
            current.items.extend(row.items)
        elif has_name_column:
            result.append(current)
            current = _TextRow(row.y, list(row.items))
            base_y = row.y
    if current is not None:
        result.append(current)
    return result


def _cells(row: _TextRow, layout: _Layout) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    columns = list(layout.columns.items())
    for item in row.items:
        field = min(columns, key=lambda pair: abs(pair[1] - item.x))[0]
        fields.setdefault(field, []).append(item.text)
    return {field: _SPACE_RE.sub(" ", " ".join(values)).strip() for field, values in fields.items()}


def _clean_name(value: str) -> str:
    value = re.sub(r"[\x00-\x1f\x7f-\x9f]+", " ", value)
    value = _SPACE_RE.sub(" ", value).strip(" .,:;-")
    value = re.sub(r"\s+\(.*?\)$", "", value).strip()
    return value


def _location(address: str, city: str, zip_code: str) -> tuple[str, str]:
    address = _SPACE_RE.sub(" ", address).strip()
    city = _SPACE_RE.sub(" ", city).strip(" ,")
    if not city:
        match = _CITY_STATE_ZIP_RE.search(address) or _CITY_ZIP_RE.search(address)
        if match:
            city = match.group("city").strip()
            address = address[: match.start()].strip(" ,")
            zip_code = zip_code or match.group("zip")
    if city and zip_code and zip_code not in address:
        address = f"{address}, {city}, {zip_code}".strip(" ,")
    return address, city


def _record_from_cells(cells: dict[str, str], source: dict, ctx: CollectContext) -> Farm | None:
    name = _clean_name(cells.get("name", "") or cells.get("business_name", "") or cells.get("licensee_name", ""))
    if not name:
        return None
    haystack = " ".join(cells.values())
    if re.search(r"\b(?:farmers? market|marketplace|page \d+)\b", name, re.I):
        return None
    address, city = _location(cells.get("address", ""), cells.get("city", ""), cells.get("zip", ""))
    phone_match = _PHONE_RE.search(cells.get("phone", "") or haystack)
    email_match = _EMAIL_RE.search(cells.get("email", "") or haystack)
    state = getattr(ctx, "state", "")
    region = getattr(ctx, "region", "")
    return Farm(
        id=f"{slugify(name)}-{state.lower()}",
        name=name,
        state=state,
        region=region,
        county=cells.get("county", "").strip(),
        city=city,
        products_text=cells.get("products", "").strip(),
        contact=Contact(
            phone=phone_match.group(0).strip() if phone_match else "",
            email=email_match.group(0).strip() if email_match else "",
            address=address,
        ),
        provenance=Provenance(
            source=str(source.get("name", "")),
            source_url=str(source.get("url", "")),
            retrieved=date.today().isoformat(),
        ),
    )


def _table_records(pages: list[list[_TextItem]], source: dict, ctx: CollectContext) -> list[Farm]:
    layouts = [_layout_for(_rows(items)) for items in pages]
    layout = next((value for value in layouts if value is not None), None)
    if layout is None:
        return []
    records: list[Farm] = []
    for items, page_layout in zip(pages, layouts):
        active = page_layout or layout
        page_rows = _rows(items)
        header_y = page_layout.header_y if page_layout else None
        for row in _logical_rows(page_rows, active, header_y):
            cells = _cells(row, active)
            record = _record_from_cells(cells, source, ctx)
            if record is not None:
                records.append(record)
    return records


def _fallback_records(pages: list[list[_TextItem]], source: dict, ctx: CollectContext) -> list[Farm]:
    """Parse narrative directory entries that have a named operation and a
    full city/state/ZIP address, while avoiding market-only PDF lists."""
    source_name = str(source.get("name", "")).lower()
    if not any(term in source_name for term in ("directory", "agritourism", "farm food")):
        return []
    lines = [_flat(row) for items in pages for row in _rows(items)]
    records: list[Farm] = []
    for index, line in enumerate(lines):
        location = _CITY_STATE_ZIP_RE.search(line) or _CITY_ZIP_RE.search(line)
        if not location:
            continue
        address_parts = [line[: location.end()].strip()]
        address_index = index - 1
        while address_index >= max(0, index - 3) and _ADDRESS_LINE_RE.search(lines[address_index]):
            address_parts.insert(0, lines[address_index])
            address_index -= 1
        address = ", ".join(address_parts)
        candidates: list[str] = []
        for previous in reversed(lines[max(0, index - 4) : index]):
            if previous and not _PHONE_RE.search(previous) and not _EMAIL_RE.search(previous):
                if _ADDRESS_LINE_RE.search(previous):
                    continue
                if not re.search(r"^(?:phone|business|mobile|email|website|web page|revised)\b", previous, re.I):
                    candidates.append(previous)
        candidate = ""
        if candidates:
            business_like = [
                value
                for value in candidates
                if sum(char.isupper() for char in value) >= max(3, sum(char.isalpha() for char in value) // 2)
                or re.search(r"\b(?:farm|orchard|ranch|garden|agri|plant|cattle|rice|produce)\b", value, re.I)
            ]
            candidate = (business_like or candidates)[0]
        candidate = _clean_name(candidate)
        if not candidate or re.search(r"\b(?:farmers? market|marketplace)\b", candidate, re.I):
            continue
        following = " ".join(lines[index + 1 : index + 7])
        cells = {
            "name": candidate,
            "address": address,
            "city": location.group("city"),
            "phone": _PHONE_RE.search(following).group(0) if _PHONE_RE.search(following) else "",
            "email": _EMAIL_RE.search(following).group(0) if _EMAIL_RE.search(following) else "",
        }
        record = _record_from_cells(cells, source, ctx)
        if record is not None:
            records.append(record)
    return records


def _unique(records: Iterable[Farm]) -> Iterable[Farm]:
    seen: dict[str, int] = {}
    for record in records:
        base = record.id
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count > 1:
            record.id = f"{base}-{count}"
        yield record


@adapter("pdf_list")
def pdf_list(source: dict, ctx: CollectContext) -> Iterable[Farm]:
    """Fetch a configured PDF list and yield raw producer records."""
    response = httpget.urlopen(source["url"], timeout=30)
    try:
        payload = response.read()
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    pages = _pdf_pages(payload)
    records = _table_records(pages, source, ctx)
    if not records:
        records = _fallback_records(pages, source, ctx)
    return _unique(records)
