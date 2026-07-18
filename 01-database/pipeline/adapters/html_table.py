"""Adapter for producer directories published as HTML tables."""
from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin

from collect import CollectContext, adapter
from model import Contact, Farm, Provenance, slugify


_SPACE_RE = re.compile(r"\s+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?1[ .-]*)?(?:\(?\d{3}\)?[ .-]*)\d{3}[ .-]*\d{4}")
_CITY_STATE_ZIP_RE = re.compile(
    r"(?P<city>[A-Za-z][A-Za-z .'-]*?),\s*(?:[A-Za-z]{2})\.?\s+"
    r"(?P<zip>\d{5}(?:-\d{4})?)\b"
)


@dataclass
class _Cell:
    kind: str
    text: list[str] = field(default_factory=list)
    hrefs: list[str] = field(default_factory=list)
    rowspan: int = 1
    colspan: int = 1

    def value(self) -> str:
        return _clean_text(" ".join(self.text))


@dataclass
class _Table:
    rows: list[list[_Cell]] = field(default_factory=list)


class _TableParser(HTMLParser):
    """Collect the text and links of each top-level HTML table."""

    _BREAK_TAGS = {"br", "div", "li", "p"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[_Table] = []
        self._table: _Table | None = None
        self._row: list[_Cell] | None = None
        self._cell: _Cell | None = None
        self._nested_tables = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            if self._table is None:
                self._table = _Table()
            else:
                self._nested_tables += 1
            return
        if self._table is None or self._nested_tables:
            return
        if tag == "tr":
            self._finish_cell()
            if self._row is not None:
                self._finish_row()
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._finish_cell()
            attributes = dict(attrs)
            self._cell = _Cell(
                kind=tag,
                rowspan=_positive_int(attributes.get("rowspan")),
                colspan=_positive_int(attributes.get("colspan")),
            )
            self._row.append(self._cell)
        elif tag == "a" and self._cell is not None:
            href = dict(attrs).get("href")
            if href:
                self._cell.hrefs.append(href.strip())
        elif tag in self._BREAK_TAGS and self._cell is not None:
            self._cell.text.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._table is not None and not self._nested_tables and self._cell is not None:
            self._cell.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "table":
            if self._nested_tables:
                self._nested_tables -= 1
                return
            self._finish_cell()
            self._finish_row()
            if self._table is not None:
                self.tables.append(self._table)
            self._table = None
            self._row = None
            return
        if self._table is None or self._nested_tables:
            return
        if tag in {"th", "td"}:
            self._finish_cell()
        elif tag == "tr":
            self._finish_cell()
            self._finish_row()

    def close(self) -> None:
        super().close()
        self._finish_cell()
        self._finish_row()
        if self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def _finish_cell(self) -> None:
        self._cell = None

    def _finish_row(self) -> None:
        if self._table is not None and self._row:
            self._table.rows.append(self._row)
        self._row = None


def _positive_int(value: str | None) -> int:
    try:
        return max(1, int(value or "1"))
    except ValueError:
        return 1


def _clean_text(value: str) -> str:
    return _SPACE_RE.sub(" ", value).strip(" \t\r\n.,;:")


def _field_name(value: str) -> str | None:
    key = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    aliases = {
        "name": "name",
        "farm": "name",
        "farm name": "name",
        "producer": "name",
        "producer name": "name",
        "business": "name",
        "business name": "name",
        "company": "name",
        "company name": "name",
        "member": "name",
        "member name": "name",
        "operation": "name",
        "operation name": "name",
        "farm producer": "name",
        "producer farm": "name",
        "county": "county",
        "parish": "county",
        "county parish": "county",
        "parish county": "county",
        "city": "city",
        "town": "city",
        "address": "address",
        "street address": "address",
        "mailing address": "address",
        "zip": "zip",
        "zip code": "zip",
        "postal code": "zip",
        "phone": "phone",
        "telephone": "phone",
        "tel": "phone",
        "business phone": "phone",
        "mobile phone": "phone",
        "email": "email",
        "e mail": "email",
        "website": "website",
        "web site": "website",
        "url": "website",
        "facebook": "facebook_url",
        "facebook url": "facebook_url",
        "instagram": "instagram_url",
        "instagram url": "instagram_url",
        "products": "products",
        "product": "products",
        "products offered": "products",
        "offerings": "products",
        "description": "notes",
        "notes": "notes",
        "farmers market": "farmers_market",
        "farmers markets": "farmers_market",
        "market": "farmers_market",
        "csa": "csa",
        "community supported agriculture": "csa",
        "on farm": "on_farm",
        "farm stand": "on_farm",
        "farmstand": "on_farm",
        "online store": "online_store",
        "online ordering": "online_store",
        "delivery": "ships",
        "ships": "ships",
        "u pick": "u_pick",
        "upick": "u_pick",
        "u pick": "u_pick",
    }
    return aliases.get(key)


def _expanded_rows(rows: list[list[_Cell]]) -> list[list[_Cell]]:
    """Expand HTML row/column spans into a rectangular list of cells."""
    spans: dict[int, tuple[_Cell, int]] = {}
    expanded: list[list[_Cell]] = []
    for raw_row in rows:
        row: list[_Cell] = []
        column = 0
        raw_index = 0
        while raw_index < len(raw_row) or column in spans:
            if column in spans:
                cell, remaining = spans[column]
                row.append(cell)
                if remaining == 1:
                    del spans[column]
                else:
                    spans[column] = (cell, remaining - 1)
                column += 1
                continue
            cell = raw_row[raw_index]
            raw_index += 1
            for offset in range(cell.colspan):
                row.append(cell)
                if cell.rowspan > 1:
                    spans[column + offset] = (cell, cell.rowspan - 1)
            column += cell.colspan
        expanded.append(row)
    return expanded


def _header_for(rows: list[list[_Cell]]) -> tuple[int, list[str | None]] | None:
    for index, row in enumerate(rows):
        fields = [_field_name(cell.value()) for cell in row]
        recognized = {field for field in fields if field is not None}
        if "name" in recognized and len(recognized) >= 2:
            return index, fields
    return None


def _cells_by_field(row: list[_Cell], fields: list[str | None]) -> dict[str, list[_Cell]]:
    values: dict[str, list[_Cell]] = {}
    for cell, field_name in zip(row, fields):
        if field_name is not None:
            values.setdefault(field_name, []).append(cell)
    return values


def _text(values: dict[str, list[_Cell]], field_name: str) -> str:
    return _clean_text(" ".join(cell.value() for cell in values.get(field_name, [])))


def _links(values: dict[str, list[_Cell]], field_name: str, base_url: str) -> list[str]:
    links: list[str] = []
    for cell in values.get(field_name, []):
        for href in cell.hrefs:
            absolute = urljoin(base_url, href)
            if absolute.startswith(("http://", "https://")) and absolute not in links:
                links.append(absolute)
    return links


def _location(address: str, city: str, zip_code: str) -> tuple[str, str]:
    address = _clean_text(address)
    city = _clean_text(city)
    if not city:
        match = _CITY_STATE_ZIP_RE.search(address)
        if match:
            city = match.group("city").strip()
            address = address[: match.start()].strip(" ,")
            zip_code = zip_code or match.group("zip")
    if city and zip_code and zip_code not in address:
        address = f"{address}, {city}, {zip_code}".strip(" ,")
    return address, city


def _email(values: dict[str, list[_Cell]]) -> str:
    for cell in values.get("email", []):
        for href in cell.hrefs:
            match = _EMAIL_RE.search(href.removeprefix("mailto:"))
            if match:
                return match.group(0)
        match = _EMAIL_RE.search(cell.value())
        if match:
            return match.group(0)
    return ""


def _phone(values: dict[str, list[_Cell]]) -> str:
    for cell in values.get("phone", []):
        for candidate in [cell.value(), *cell.hrefs]:
            match = _PHONE_RE.search(candidate)
            if match:
                return match.group(0).strip()
    return ""


def _channel(values: dict[str, list[_Cell]], field_name: str) -> bool:
    cells = values.get(field_name, [])
    if not cells:
        return False
    text = " ".join(cell.value() for cell in cells).casefold()
    return not text.strip(" -–—") in {"", "no", "n", "false", "0", "none"}


def _record(row: list[_Cell], fields: list[str | None], source: dict, ctx: CollectContext, base_url: str) -> Farm | None:
    values = _cells_by_field(row, fields)
    name = _text(values, "name")
    if not name or name.casefold() in {"name", "farm name", "producer", "producer name"}:
        return None

    address, city = _location(_text(values, "address"), _text(values, "city"), _text(values, "zip"))
    name_links = _links(values, "name", base_url)
    website_links = _links(values, "website", base_url)
    facebook_links = _links(values, "facebook_url", base_url)
    instagram_links = _links(values, "instagram_url", base_url)
    website = website_links[0] if website_links else ""
    if not website:
        website_match = re.search(r"https?://\S+", _text(values, "website"))
        website = website_match.group(0).rstrip(".,);") if website_match else ""
    if not website and name_links:
        website = name_links[0]

    state = str(getattr(ctx, "state", ""))
    return Farm(
        id=f"{slugify(name)}-{state.lower()}",
        name=name,
        state=state,
        region=str(getattr(ctx, "region", "")),
        county=_text(values, "county"),
        city=city,
        products_text=_text(values, "products"),
        website=website,
        facebook_url=facebook_links[0] if facebook_links else "",
        instagram_url=instagram_links[0] if instagram_links else "",
        on_farm=_channel(values, "on_farm"),
        farmers_market=_channel(values, "farmers_market"),
        csa=_channel(values, "csa"),
        online_store=_channel(values, "online_store"),
        ships=_channel(values, "ships"),
        u_pick=_channel(values, "u_pick"),
        contact=Contact(phone=_phone(values), email=_email(values), address=address),
        notes=_text(values, "notes"),
        provenance=Provenance(
            source=str(source.get("name", "")),
            source_url=str(source.get("url", "")),
            retrieved=date.today().isoformat(),
        ),
    )


def _unique(records: Iterable[Farm]) -> Iterable[Farm]:
    seen: dict[str, int] = {}
    for record in records:
        count = seen.get(record.id, 0) + 1
        seen[record.id] = count
        if count > 1:
            record.id = f"{record.id}-{count}"
        yield record


def _decode(payload: bytes, response: object) -> str:
    encoding = ""
    headers = getattr(response, "headers", None)
    get_charset = getattr(headers, "get_content_charset", None)
    if get_charset:
        encoding = get_charset() or ""
    return payload.decode(encoding or "utf-8", errors="replace")


@adapter("html_table")
def html_table(source: dict, ctx: CollectContext) -> Iterable[Farm]:
    """Fetch a configured HTML table and yield raw producer records."""
    response = urllib.request.urlopen(source["url"], timeout=30)
    try:
        payload = response.read()
        html = _decode(payload, response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()

    parser = _TableParser()
    parser.feed(html)
    parser.close()
    records: list[Farm] = []
    for table in parser.tables:
        rows = _expanded_rows(table.rows)
        header = _header_for(rows)
        if header is None:
            continue
        header_index, fields = header
        for row in rows[header_index + 1 :]:
            record = _record(row, fields, source, ctx, source["url"])
            if record is not None:
                records.append(record)
    return _unique(records)
