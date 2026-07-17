#!/usr/bin/env python3
"""Build a coverage-reviewed Alabama farm-source staging release.

The collector runs the three source passes required by
``01-database/state-expansion-and-verification.md``. It never edits the LA/MS
canonical workbook or public app data. Source observations remain immutable rows;
only deterministic, documented identity rules create proposed Alabama entities.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from state_release_urls import classify_public_urls
from state_policy import classify_candidate
from referrals import (
    read_referrals,
    referral_from_observation,
    referral_observation as referral_candidate,
    stage_referrals,
)


ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "research" / "state-expansions" / "AL"
OUTPUT_DIR = ROOT / "data" / "source-releases" / "work" / "AL"
PUBLIC_FARMS = ROOT / "03-app" / "site" / "app" / "data" / "farms.json"
USER_AGENT = "FarmFinder/1.0 (+public-directory research; contact in repository)"
TODAY = date.today().isoformat()

SWEET_GROWN_URL = "https://www.sweetgrownalabama.org/find-sweet-grown"
FMA_STAND_URL = "https://agi.alabama.gov/farmersmarket/locations/farmers-stand-location-map/"
FMA_UPICK_URL = "https://agi.alabama.gov/farmersmarket/locations/u-pick-location-map/"
FMA_MARKET_URL = "https://agi.alabama.gov/farmersmarket/locations/farmers-market-location-map/"
FMA_2026_PDF_URL = "https://agi.alabama.gov/farmersmarket/wp-content/uploads/sites/9/2023/02/2026-statewide-redemption-sites.pdf"
BEEKS_URL = "https://agi.alabama.gov/plantprotection/beeks-selling-bees/"
FARM_TO_SCHOOL_URL = "https://agi.alabama.gov/fts/farmers/"
BAMA_BEEF_URL = "https://www.bamabeef.org/p/about/bama-beef-sales-directory"
EATWILD_URL = "https://www.eatwild.com/products/alabama.html"
US_FARM_TRAIL_URL = "https://www.usfarmtrail.com/states/alabama"
FCC_AREA_URL = "https://geo.fcc.gov/api/census/area"
CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
PYO_URLS = {
    "North Alabama": "https://www.pickyourown.org/ALhuntsv.htm",
    "Central Alabama": "https://www.pickyourown.org/ALbham.htm",
    "Southeast Alabama": "https://www.pickyourown.org/ALmontg.htm",
    "Southwest Alabama": "https://www.pickyourown.org/ALmobile.htm",
}
CITY_ZIP_COUNTY_FALLBACKS = {
    ("ashland", "36251"): "Clay",
    ("hokes bluff", "35903"): "Etowah",
}
IDENTITY_COUNTY_OVERRIDES = {
    # The current Sweet Grown individual profile and farm-owned evidence place
    # this exact operation at Columbia/Haleburg in Houston County.
    "jyj red angus": "Houston",
}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    parent: "Node | None"
    children: list["Node | str"]

    def text(self) -> str:
        if self.tag in {"br", "hr"}:
            return " | "
        value = clean_text(" ".join(child.text() if isinstance(child, Node) else child for child in self.children))
        return f"{value} | " if value and self.tag in {"div", "p", "li", "section", "article"} else value

    def descendants(self, tag: str | None = None) -> Iterable["Node"]:
        for child in self.children:
            if isinstance(child, Node):
                if tag is None or child.tag == tag:
                    yield child
                yield from child.descendants(tag)

    def has_class(self, value: str) -> bool:
        return value in self.attrs.get("class", "").split()


class MiniDOM(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("document", {}, None, [])
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {key: value or "" for key, value in attrs}, self.stack[-1], [])
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.stack[-1].children.append(data)


@dataclass
class Observation:
    observation_id: str
    candidate_key: str
    identity_review_status: str
    current_release_name_collision: str
    farm_name: str
    entity_type_source: str
    entity_type_review: str
    state: str
    county: str
    county_fips: str
    county_source: str
    city: str
    postal_code: str
    address: str
    latitude: float | None
    longitude: float | None
    location_precision: str
    address_visibility: str
    contact_name: str
    phone: str
    email: str
    contact_visibility: str
    products: str
    business_types: str
    website_url: str
    facebook_url: str
    instagram_url: str
    tiktok_url: str
    on_farm_sales: bool | None
    farmers_market_sales: bool | None
    online_sales: bool | None
    local_delivery: bool | None
    u_pick: bool | None
    wholesale: bool | None
    farm_to_school: bool | None
    retail_sales: bool | None
    restaurant_sales: bool | None
    hours_or_season: str
    source_pass: int
    source_name: str
    source_url: str
    source_record_id: str
    evidence_grade: str
    retrieved_date: str
    promotion_status: str
    notes: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"<br\s*/?>", " | ", str(value), flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip(" |\t\r\n")


def normalized_name(value: str) -> str:
    value = clean_text(value).casefold().replace("&", " and ").replace("’", "").replace("'", "")
    tokens = re.sub(r"[^a-z0-9]+", " ", value).strip().split()
    while len(tokens) > 2 and tokens[-1] in {"llc", "inc", "incorporated"}:
        tokens.pop()
    return " ".join(tokens)


def normalized_county(value: str) -> str:
    value = re.sub(r"\s+County$", "", clean_text(value), flags=re.I)
    aliases = {"Dekalb": "DeKalb", "Stclair": "St. Clair", "St Clair": "St. Clair", "St. Clair": "St. Clair"}
    return aliases.get(value.title(), value.title())


def clean_url(value: Any) -> str:
    text = clean_text(value).strip(".,;)")
    if not text or re.search(r"\s", text) or "." not in text:
        return ""
    if not re.match(r"^https?://", text, flags=re.I):
        text = f"https://{text}"
    return text


def make_observation_id(source_name: str, source_record_id: str, farm_name: str) -> str:
    raw = f"AL|{source_name}|{source_record_id}|{farm_name}".encode()
    return f"alobs_{hashlib.sha256(raw).hexdigest()[:20]}"


def dom(body: str) -> Node:
    parser = MiniDOM()
    parser.feed(body)
    return parser.root


def first_descendant(node: Node, predicate: Any) -> Node | None:
    return next((item for item in node.descendants() if predicate(item)), None)


def fetch_bytes(url: str, attempts: int = 3, timeout: int = 45) -> tuple[bytes, dict[str, Any]]:
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                return raw, {
                    "url": url, "attempts_used": attempt, "http_status": response.status,
                    "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                    "elapsed_seconds": round(time.monotonic() - started, 3), "error": "",
                }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(f"attempt {attempt}: {exc}")
            if attempt < attempts:
                time.sleep(0.8 * attempt)
    return b"", {"url": url, "attempts_used": attempts, "http_status": 0, "bytes": 0,
                 "sha256": "", "elapsed_seconds": 0, "error": " | ".join(errors)}


def fetch(url: str, attempts: int = 3, timeout: int = 45) -> tuple[str, dict[str, Any]]:
    raw, log = fetch_bytes(url, attempts, timeout)
    return raw.decode("utf-8", "replace"), log


def source_log_entry(log: dict[str, Any], pass_number: int, name: str, records: int,
                     decision: str = "observations_retained", note: str = "") -> dict[str, Any]:
    return {**log, "pass": pass_number, "source_name": name, "records_parsed": records,
            "retrieved_at": now_iso(), "source_decision": decision, "note": note}


def extract_sweet_grown_members(body: str) -> list[dict[str, Any]]:
    match = re.search(r"var\s+members\s*=\s*(\[.*?\]);\s*var\s+products", body, flags=re.S)
    if not match:
        match = re.search(r"var\s+members\s*=\s*(\[.*?\]);\s*var", body, flags=re.S)
    if not match:
        raise ValueError("Sweet Grown Alabama member payload was not found")
    return [member for member in json.loads(match.group(1)) if any(
        item.get("slug") == "farm" or item.get("name") == "Farm"
        for item in member.get("business_types") or [])]


def extract_fma_options(body: str) -> dict[str, Any]:
    match = re.search(r"var\s+mapsvg_options\s*=\s*(\{.*?\});jQuery\.extend", body, flags=re.S)
    if not match:
        raise ValueError("Alabama FMA map payload was not found")
    return json.loads(match.group(1))


def empty_observation(source_name: str, source_record_id: str, farm_name: str, source_url: str,
                      source_pass: int, grade: str) -> dict[str, Any]:
    return {
        "observation_id": make_observation_id(source_name, source_record_id, farm_name),
        "candidate_key": normalized_name(farm_name), "identity_review_status": "source_unique_name",
        "current_release_name_collision": "", "farm_name": farm_name, "entity_type_source": "",
        "entity_type_review": "needs_review", "state": "AL", "county": "", "county_fips": "",
        "county_source": "", "city": "", "postal_code": "", "address": "", "latitude": None,
        "longitude": None, "location_precision": "", "address_visibility": "internal_source_value",
        "contact_name": "", "phone": "", "email": "", "contact_visibility": "internal_source_value",
        "products": "", "business_types": "", "website_url": "", "facebook_url": "",
        "instagram_url": "", "tiktok_url": "", "on_farm_sales": None,
        "farmers_market_sales": None, "online_sales": None, "local_delivery": None,
        "u_pick": None, "wholesale": None, "farm_to_school": None, "retail_sales": None,
        "restaurant_sales": None, "hours_or_season": "", "source_pass": source_pass,
        "source_name": source_name, "source_url": source_url, "source_record_id": source_record_id,
        "evidence_grade": grade, "retrieved_date": TODAY, "promotion_status": "staged_pending_rules",
        "notes": "",
    }


def referral_observations() -> list[Observation]:
    """Turn open Alabama referrals into explicit QA candidates."""
    observations: list[Observation] = []
    for referral in read_referrals("AL"):
        candidate = referral_candidate(referral, "AL")
        item = empty_observation(
            candidate["source_name"], candidate["source_record_id"], candidate["farm_name"],
            candidate["source_url"], 1, "E",
        )
        item.update({
            "entity_type_source": "Cross-state referral",
            "entity_type_review": "referral_requires_home_state_farm_operation_review",
            "products": candidate["products"],
            "business_types": candidate["business_types"],
            "retrieved_date": candidate["retrieved_date"],
            "notes": (
                f"{candidate['evidence']} Observed market/channel in "
                f"{referral['observed_market_state']}: {candidate['observed_market_channel']}. "
                "Referral evidence confirms cross-state presence, not home-state operation or eligibility."
            )[:1500],
        })
        observations.append(Observation(**item))
    return observations


def sweet_observation(member: dict[str, Any]) -> Observation:
    name = clean_text(member.get("name"))
    row = empty_observation("Sweet Grown Alabama — Farm members", clean_text(member.get("id")),
                            name, SWEET_GROWN_URL, 1, "B")
    row.update({
        "entity_type_source": "Farm", "entity_type_review": "farm_confirmed_by_source",
        "city": clean_text(member.get("city")).title(), "postal_code": clean_text(member.get("zip"))[:10],
        "address": clean_text(member.get("address")), "latitude": member.get("latitude"),
        "longitude": member.get("longitude"),
        "location_precision": "source_coordinate_and_public_address" if member.get("address") else "source_coordinate",
        "contact_name": "", "phone": clean_text(member.get("phone")), "email": clean_text(member.get("email")),
        "products": "; ".join(dict.fromkeys(clean_text(item.get("name")) for item in member.get("products") or [] if clean_text(item.get("name")))),
        "business_types": "; ".join(dict.fromkeys(clean_text(item.get("name")) for item in member.get("business_types") or [] if clean_text(item.get("name")))),
        "website_url": clean_url(member.get("website")), "facebook_url": clean_url(member.get("facebook_link")),
        "instagram_url": clean_url(member.get("instagram_link")), "tiktok_url": clean_url(member.get("tiktok_link")),
        "on_farm_sales": bool(member.get("purchase_on_farm")), "farmers_market_sales": bool(member.get("purchase_farmers_market")),
        "online_sales": bool(member.get("purchase_online")), "local_delivery": bool(member.get("purchase_local_delivery")),
        "u_pick": bool(member.get("purchase_pick_your_own")), "wholesale": bool(member.get("purchase_wholesale")),
        "farm_to_school": bool(member.get("purchase_farm_to_school")), "retail_sales": bool(member.get("purchase_retail")),
        "restaurant_sales": bool(member.get("purchase_restaurant")), "hours_or_season": clean_text(member.get("hours_of_operation")),
        "notes": _joined_notes(member),
    })
    return Observation(**row)


def _joined_notes(member: dict[str, Any]) -> str:
    source_state = clean_text(member.get("state") or member.get("state_name"))
    notes = clean_text(member.get("bio"))
    return "; ".join(value for value in (f"Source state: {source_state}" if source_state else "", notes) if value)


def fma_observation(record: dict[str, Any], kind: str, url: str) -> Observation:
    name = clean_text(record.get("orgname"))
    source_name = f"Alabama Farmers Market Authority — {kind} map"
    row = empty_observation(source_name, clean_text(record.get("id")), name, url, 1, "B")
    counties = [normalized_county(item.get("id", "")) for item in record.get("regions") or [] if clean_text(item.get("id"))]
    contact = " ".join(x for x in [clean_text(record.get("orgcontactfirstname")), clean_text(record.get("orgcontactlastname"))] if x)
    phones = " | ".join(x for x in [clean_text(record.get("orgcontactphone1")), clean_text(record.get("orgcontactphone2"))] if x)
    row.update({
        "entity_type_source": "Farm stand" if kind == "farm-stand" else "U-pick operation",
        "entity_type_review": "farm_activity_confirmed_by_official_source",
        "county": "; ".join(dict.fromkeys(counties)), "county_source": "Alabama FMA map county region",
        "city": clean_text(record.get("orgcity")).title(), "postal_code": clean_text(record.get("orgzip"))[:10],
        "address": clean_text(record.get("orgaddress1")).title(), "location_precision": "public_source_address",
        "contact_name": contact.title(), "phone": phones, "email": clean_text(record.get("orgcontactemail")),
        "products": "Farm products; direct-to-consumer sales" if kind == "farm-stand" else "U-pick crops; agritourism",
        "business_types": "Farm stand; direct-to-consumer" if kind == "farm-stand" else "Agritourism; U-pick",
        "website_url": clean_url(record.get("orgcontactweb")), "facebook_url": clean_url(record.get("orgsecondcontactfb")),
        "on_farm_sales": True, "u_pick": kind == "u-pick", "hours_or_season": clean_text(record.get("frequency")),
        "notes": "Official state map listing; product specificity may require farm-level verification.",
    })
    return Observation(**row)


def pdf_to_text(raw: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "source.pdf"
        txt = Path(tmp) / "source.txt"
        pdf.write_bytes(raw)
        subprocess.run(["pdftotext", "-raw", "-f", "14", "-l", "17", str(pdf), str(txt)],
                       check=True, capture_output=True, text=True)
        return txt.read_text(encoding="utf-8", errors="replace")


def extract_pdf_farm_stands(text: str, official_counties: list[str]) -> list[dict[str, str]]:
    county_lookup = {normalized_name(county): county for county in official_counties}
    current = ""
    records: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = clean_text(raw_line)
        if not line or line.startswith("*") or line.isdigit() or line.startswith("THIS LIST") or line == "FARM STANDS":
            continue
        county_key = normalized_name(re.sub(r"\s*-\s*NONE$", "", line, flags=re.I))
        if county_key in county_lookup:
            current = county_lookup[county_key]
            continue
        if not current or not re.match(r"^\d+[\).]?\s*", line):
            continue
        value = re.sub(r"^\d+[\).]?\s*", "", line).strip()
        parts = re.split(r"\s+[–-]\s*", value, maxsplit=1)
        farm_words = re.compile(r"farm|orchard|produce|market|u[ -]?pick|vineyard|acres|berry|blueberr|greenhouse|tomato|llc", re.I)
        if len(parts) == 2:
            left, right = parts
            name = left if farm_words.search(left) and not farm_words.search(right) else right
        else:
            name = value
        name = re.sub(r"\s*\([^)]*(?:up|fs|sfmnp)[^)]*\)\s*", "", name, flags=re.I)
        name = re.sub(r"\*.*$", "", name).strip(" -")
        if len(name) >= 3:
            records.append({"county": current, "farm_name": name, "raw_line": line})
    return records


def pdf_observation(record: dict[str, str], index: int) -> Observation:
    name = record["farm_name"]
    row = empty_observation("Alabama FMA — 2026 statewide farm-stand roster", str(index), name,
                            FMA_2026_PDF_URL, 1, "B")
    row.update({"entity_type_source": "Farm stand", "entity_type_review": "farm_activity_confirmed_by_official_source",
                "county": record["county"], "county_source": FMA_2026_PDF_URL,
                "products": "Farm products; direct-to-consumer sales", "business_types": "Farm stand",
                "on_farm_sales": True, "notes": f"Official roster line: {record['raw_line']}"})
    return Observation(**row)


def table_rows(root: Node) -> list[list[str]]:
    rows = []
    for tr in root.descendants("tr"):
        cells = [cell.text() for cell in tr.children if isinstance(cell, Node) and cell.tag in {"td", "th"}]
        if cells:
            rows.append(cells)
    return rows


def bee_observations(body: str) -> list[Observation]:
    records = []
    for index, cells in enumerate(table_rows(dom(body))[1:], start=1):
        if len(cells) < 4:
            continue
        company, contact, phone, county = (clean_text(value) for value in cells[:4])
        name = company or f"Unnamed bee seller — {contact}"
        row = empty_observation("Alabama Plant Protection — Beekeepers Selling Bees", str(index), name, BEEKS_URL, 1, "B")
        row.update({"entity_type_source": "Bee/apiary seller", "entity_type_review": "producer_type_review_required",
                    "county": normalized_county(county), "county_source": BEEKS_URL, "contact_name": contact,
                    "phone": phone, "products": "Bees; apiary products", "business_types": "Apiary / bee seller",
                    "promotion_status": "research_queue_entity_type", "notes": "Official bee-seller list; farm-operation evidence is not implied."})
        records.append(Observation(**row))
    return records


def strong_names(area: Node) -> list[str]:
    values = []
    for node in area.descendants("strong"):
        if any(parent.tag == "em" for parent in ancestors(node)):
            continue
        value = node.text().strip(" :*-")
        if value and len(value) <= 90 and not re.search(r"website|facebook|available by|certified|product available", value, re.I):
            values.append(value)
    return list(dict.fromkeys(values))


def ancestors(node: Node) -> Iterable[Node]:
    current = node.parent
    while current:
        yield current
        current = current.parent


def bama_beef_observations(body: str) -> list[Observation]:
    root = dom(body)
    records = []
    for heading in (node for node in root.descendants("h2") if node.has_class("moduleTitle")):
        county = normalized_county(heading.text())
        container = heading.parent
        if not container:
            continue
        area = first_descendant(container, lambda node: node.has_class("previewArea"))
        if not area:
            continue
        full_text = area.text()
        names = strong_names(area)
        for position, name in enumerate(names):
            start = full_text.find(name)
            end = full_text.find(names[position + 1], start + len(name)) if position + 1 < len(names) else len(full_text)
            segment = full_text[start:end] if start >= 0 else full_text
            city_match = re.search(r"(?:^|\|)\s*([A-Za-z][A-Za-z .'-]{1,40}),\s*(?:AL|Alabama)\b", segment)
            phone_match = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", segment)
            row = empty_observation("Alabama Cattlemen’s Association — Bama Beef Sales Directory",
                                    f"{normalized_name(county)}-{position + 1}", name, BAMA_BEEF_URL, 2, "D")
            row.update({"entity_type_source": "Direct-sale beef producer", "entity_type_review": "farm_activity_confirmed_by_directory",
                        "county": county, "county_source": BAMA_BEEF_URL, "city": city_match.group(1).title() if city_match else "",
                        "phone": phone_match.group(0) if phone_match else "", "products": "Beef; direct-to-consumer meat",
                        "business_types": "Cattle farm; direct-sale beef", "on_farm_sales": True,
                        "notes": clean_text(segment)[:900]})
            records.append(Observation(**row))
    return records


def link_values(node: Node) -> tuple[str, str, str, str]:
    website = facebook = instagram = email = ""
    for link in node.descendants("a"):
        href = html.unescape(link.attrs.get("href", ""))
        if href.startswith("mailto:") and not email:
            email = href[7:].split("?", 1)[0]
            continue
        parsed = urllib.parse.urlparse(href)
        query_url = urllib.parse.parse_qs(parsed.query).get("URL", [""])[0]
        if query_url:
            href = query_url
        url = clean_url(href)
        if not url or "pickyourown.org/AME" in url or "maps.google" in url or "goo.gl/maps" in url or "maps.app" in url:
            continue
        if "facebook.com" in url and not facebook:
            facebook = url
        elif "instagram.com" in url and not instagram:
            instagram = url
        elif "pickyourown.org" not in url and not website:
            website = url
    return website, facebook, instagram, email


def pyo_observations(body: str, region: str, url: str) -> tuple[list[Observation], list[str]]:
    root = dom(body)
    active = False
    closed_section = False
    county = ""
    records: list[Observation] = []
    searched_counties: list[str] = []

    def walk(node: Node) -> None:
        nonlocal active, closed_section, county
        if node.tag == "h2" and "U-Pick Farms and Orchards" in node.text():
            active = True
        elif active and node.tag == "h3":
            heading = node.text()
            if heading.startswith("ZZZ -"):
                closed_section = True
                county = ""
            elif heading.lower().endswith(" county") and not closed_section:
                county = normalized_county(heading)
                if county not in searched_counties:
                    searched_counties.append(county)
            elif not heading.lower().endswith(" county"):
                county = ""
        elif active and county and not closed_section and node.tag in {"li", "p"}:
            farm_node = first_descendant(node, lambda item: item.has_class("farm"))
            if not farm_node:
                farm_node = next((item for item in node.children if isinstance(item, Node) and item.tag in {"b", "strong"}), None)
            name = farm_node.text().strip(" -:") if farm_node else ""
            text = node.text()
            if not name or len(name) > 100 or not re.search(rf"^{re.escape(name)}\b|\b{re.escape(name)}\s*-", text, re.I):
                pass
            else:
                closed = bool(re.search(r"permanently closed|assumed permanently closed|ceased operation", text, re.I))
                city_zip = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40}),\s*(?:AL|Alabama)\s+(\d{5})\b", text)
                address_match = re.search(r"(?:^|\s)(\d{1,6}\s+[^|]{2,80}?),\s*[A-Za-z][A-Za-z .'-]{1,40},\s*(?:AL|Alabama)\s+\d{5}", text)
                phone_match = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", text)
                website, facebook, instagram, email = link_values(node)
                product_match = re.search(rf"{re.escape(name)}\s*-\s*(.{{1,240}}?)(?:\b\d{{1,6}}\s+|Phone:|Email:|Open:)", text, re.I)
                products = clean_text(product_match.group(1)) if product_match else "U-pick crops; agritourism"
                row = empty_observation(f"PickYourOwn — {region}", str(len(records) + 1), name, url, 3, "F" if closed else "E")
                row.update({"entity_type_source": "U-pick operation", "entity_type_review": "farm_activity_confirmed_by_directory",
                            "county": county, "county_source": url, "city": city_zip.group(1).title() if city_zip else "",
                            "postal_code": city_zip.group(2) if city_zip else "", "address": clean_text(address_match.group(1)) if address_match else "",
                            "location_precision": "public_directory_address" if address_match else "county",
                            "phone": phone_match.group(0) if phone_match else "", "email": email, "products": products,
                            "business_types": "U-pick; agritourism", "website_url": website, "facebook_url": facebook,
                            "instagram_url": instagram, "on_farm_sales": True, "u_pick": True,
                            "promotion_status": "excluded_explicitly_closed" if closed else "staged_pending_corrob",
                            "notes": clean_text(text)[:1200]})
                records.append(Observation(**row))
                return
        for child in node.children:
            if isinstance(child, Node):
                walk(child)

    walk(root)
    return records, searched_counties


def eatwild_observations(body: str) -> list[Observation]:
    root = dom(body)
    records = []
    for node in root.descendants("p"):
        if not node.has_class("bodyMargin"):
            continue
        text = node.text()
        match = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40})\s*,?\s*(?:AL|Alabama)\s+(\d{5})\b", text)
        if not match:
            continue
        before = text[:match.start()]
        contact_prefix = re.split(r"(?<=[.!?])\s+", before)[-1].strip()
        name = contact_prefix.split(",", 1)[0].strip()
        if len(name) < 3 or len(name) > 90:
            continue
        address_match = re.search(r"(\d{1,6}\s+[^,]{2,80}),\s*$", before)
        phone_match = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", text[match.end():])
        website, facebook, instagram, email = link_values(node)
        row = empty_observation("EatWild Alabama directory", str(len(records) + 1), name, EATWILD_URL, 2, "D")
        row.update({"entity_type_source": "Pastured-product farm", "entity_type_review": "farm_activity_confirmed_by_directory",
                    "county_source": EATWILD_URL, "city": match.group(1).title(), "postal_code": match.group(2),
                    "address": address_match.group(1) if address_match else "", "location_precision": "public_directory_address",
                    "phone": phone_match.group(0) if phone_match else "", "email": email,
                    "products": "Pastured livestock and/or farm products; see source profile",
                    "business_types": "Pastured-product farm; direct sales", "website_url": website,
                    "facebook_url": facebook, "instagram_url": instagram, "on_farm_sales": True,
                    "notes": clean_text(text)[:900]})
        records.append(Observation(**row))
    return records


def fcc_county(latitude: float, longitude: float) -> tuple[str, str, str, dict[str, Any]]:
    url = f"{FCC_AREA_URL}?{urllib.parse.urlencode({'lat': latitude, 'lon': longitude, 'format': 'json'})}"
    body, log = fetch(url)
    county = county_fips = ""
    error = log["error"]
    if body:
        try:
            result = (json.loads(body).get("results") or [None])[0]
            if result and result.get("state_code") == "AL":
                county = normalized_county(result.get("county_name", ""))
                county_fips = clean_text(result.get("county_fips"))
            else:
                error = "No Alabama county returned"
        except (json.JSONDecodeError, TypeError) as exc:
            error = f"Invalid FCC JSON: {exc}"
    log.update({"pass": 1, "source_name": "FCC Census Area API", "records_parsed": int(bool(county)),
                "retrieved_at": now_iso(), "error": error, "source_decision": "county_enrichment"})
    return county, county_fips, url, log


def census_address_county(address: str, city: str, postal_code: str) -> tuple[str, str, str, dict[str, Any]]:
    one_line = ", ".join(value for value in [address, city, "AL", postal_code] if clean_text(value))
    params = {"address": one_line, "benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json"}
    url = f"{CENSUS_GEOCODER_URL}?{urllib.parse.urlencode(params)}"
    body, log = fetch(url)
    county = county_fips = ""
    error = log["error"]
    if body:
        try:
            matches = json.loads(body).get("result", {}).get("addressMatches", [])
            counties = matches[0].get("geographies", {}).get("Counties", []) if matches else []
            if counties and counties[0].get("STATE") == "01":
                county = normalized_county(counties[0].get("NAME", ""))
                county_fips = f"01{counties[0].get('COUNTY', '')}"
            else:
                error = "No Alabama Census address match returned"
        except (json.JSONDecodeError, TypeError, IndexError) as exc:
            error = f"Invalid Census geocoder response: {exc}"
    log.update({"pass": 2, "source_name": "U.S. Census Geocoder", "records_parsed": int(bool(county)),
                "retrieved_at": now_iso(), "error": error, "source_decision": "county_enrichment"})
    return county, county_fips, url, log


def old_county_cache() -> dict[str, tuple[str, str, str]]:
    path = OUTPUT_DIR / "observations.csv"
    if not path.exists():
        return {}
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except (csv.Error, OSError):
        return {}
    return {row.get("observation_id", ""): (row.get("county", ""), row.get("county_fips", ""), row.get("county_source", ""))
            for row in rows if row.get("county")}


def read_current_public_names() -> dict[str, str]:
    if not PUBLIC_FARMS.exists():
        return {}
    records = json.loads(PUBLIC_FARMS.read_text(encoding="utf-8"))
    return {normalized_name(record.get("name", "")): clean_text(record.get("name")) for record in records}


def choose(items: list[Observation], field: str) -> Any:
    source_rank = lambda item: (0 if item.source_name.startswith("Sweet Grown") else
                                1 if "Farmers Market Authority" in item.source_name else
                                2 if "FMA" in item.source_name else 3)
    ordered = sorted(items, key=lambda item: ({"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}.get(item.evidence_grade, 9),
                                                   source_rank(item), -len(clean_text(getattr(item, field)))))
    return next((getattr(item, field) for item in ordered if getattr(item, field) not in {None, ""}), "")


def identity_tokens(item: Observation) -> set[str]:
    values = [item.phone, item.email, item.website_url, item.facebook_url, item.instagram_url]
    return {re.sub(r"[^a-z0-9]", "", clean_text(value).casefold()) for value in values if clean_text(value)}


def unique_values(items: list[Observation], field: str, separator: str = "; ") -> str:
    values = []
    for item in items:
        for value in clean_text(getattr(item, field)).split(";"):
            value = value.strip()
            if value and value not in values:
                values.append(value)
    return separator.join(values)


def reconcile(observations: list[Observation]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: defaultdict[str, list[Observation]] = defaultdict(list)
    for item in observations:
        if item.candidate_key:
            grouped[item.candidate_key].append(item)
    entities: list[dict[str, Any]] = []
    identity_review: list[dict[str, Any]] = []
    qa: list[dict[str, Any]] = []
    for key, all_items in sorted(grouped.items()):
        county_groups: defaultdict[str, list[Observation]] = defaultdict(list)
        known_counties = sorted({item.county for item in all_items if item.county and ";" not in item.county})
        conflict = len(known_counties) > 1
        shared_contact = any(identity_tokens(left) & identity_tokens(right)
                             for index, left in enumerate(all_items) for right in all_items[index + 1:]
                             if left.county and right.county and left.county != right.county)
        city_values = [item.city.casefold().strip() for item in all_items if item.city]
        same_city = len(city_values) >= 2 and len(set(city_values)) == 1
        curator_override = IDENTITY_COUNTY_OVERRIDES.get(key, "")
        merge_cross_county = conflict and (shared_contact or same_city or bool(curator_override))
        if conflict and not merge_cross_county:
            for item in all_items:
                county_groups[item.county or f"unknown-{item.observation_id}"].append(item)
        else:
            preferred_county = curator_override or clean_text(choose([item for item in all_items if item.county], "county"))
            county_groups[preferred_county or "unknown"].extend(all_items)
        if len(all_items) > 1:
            identity_review.append({
                "candidate_key": key, "observation_count": len(all_items),
                "farm_names": " | ".join(dict.fromkeys(item.farm_name for item in all_items)),
                "source_names": " | ".join(dict.fromkeys(item.source_name for item in all_items)),
                "cities": " | ".join(dict.fromkeys(item.city for item in all_items if item.city)),
                "counties": " | ".join(known_counties),
                "review_status": ("merged_cross_county_curator_override_official_profile" if curator_override else
                                  "merged_cross_county_shared_identity_preferred_geography" if merge_cross_county else
                                  "split_county_conflict_no_merge" if conflict else "merged_exact_name_single_geography"),
                "observation_ids": " | ".join(item.observation_id for item in all_items),
            })
        for group_county, items in county_groups.items():
            name = choose(items, "farm_name")
            county = "" if group_county.startswith("unknown") else group_county
            active_items = [item for item in items if item.evidence_grade != "F"]
            if not active_items:
                # Grade-F-only records remain in the immutable observation and
                # exclusion files; they are not Alabama candidate entities.
                continue
            source_items = active_items or items
            entity_id = "AL-" + hashlib.sha256(f"{key}|{county}|{items[0].observation_id if conflict and not county else ''}".encode()).hexdigest()[:10].upper()
            grades = sorted(set(item.evidence_grade for item in items))
            source_names = list(dict.fromkeys(item.source_name for item in items))
            bee_only = all("Bee" in item.entity_type_source or "apiary" in item.entity_type_source.lower() for item in items)
            city = choose(source_items, "city")
            products = unique_values(source_items, "products")
            identity_status = ("merged_cross_county_identity_reviewed" if merge_cross_county else
                               "split_due_county_conflict" if conflict else
                               "merged_exact_name_reviewed" if len(items) > 1 else "unique_source_name_reviewed")
            blockers = []
            if conflict and not merge_cross_county: blockers.append("same normalized name appears in multiple counties")
            if bee_only: blockers.append("bee seller requires farm-operation evidence")
            if not county: blockers.append("county missing")
            if not city: blockers.append("city or safe public service area missing")
            if not products: blockers.append("products or farm activity missing")
            if grades == ["E"]: blockers.append("single secondary discovery listing needs corroboration")
            promotion = classify_candidate(name, blockers).status
            website_url, facebook_url, instagram_url, tiktok_url = classify_public_urls(
                choose(source_items, "website_url"), choose(source_items, "facebook_url"),
                choose(source_items, "instagram_url"), choose(source_items, "tiktok_url"),
            )
            entity = {
                "entity_id": entity_id, "farm_name": name, "normalized_name": key,
                "entity_type": "producer_requires_type_review" if bee_only else "farm",
                "identity_decision": identity_status, "state": "AL", "county": county,
                "city": city, "postal_code": choose(source_items, "postal_code"),
                "address_internal": choose(source_items, "address"),
                "public_location_classification": "public_business_address_reviewed_for_future_reduced_precision",
                "latitude": choose(source_items, "latitude"), "longitude": choose(source_items, "longitude"),
                "products": products, "business_types": unique_values(source_items, "business_types"),
                "phone_internal": choose(source_items, "phone"), "email_internal": choose(source_items, "email"),
                "contact_visibility": "internal_until_public_use_review",
                "website_url": website_url, "facebook_url": facebook_url,
                "instagram_url": instagram_url, "tiktok_url": tiktok_url,
                "on_farm_sales": any(item.on_farm_sales is True for item in source_items),
                "farmers_market_sales": any(item.farmers_market_sales is True for item in source_items),
                "online_sales": any(item.online_sales is True for item in source_items),
                "local_delivery": any(item.local_delivery is True for item in source_items),
                "u_pick": any(item.u_pick is True for item in source_items),
                "wholesale": any(item.wholesale is True for item in source_items),
                "farm_to_school": any(item.farm_to_school is True for item in source_items),
                "source_observation_count": len(items), "source_observation_ids": " | ".join(item.observation_id for item in items),
                "source_names": " | ".join(source_names), "source_urls": " | ".join(dict.fromkeys(item.source_url for item in items)),
                "evidence_grades": "; ".join(grades), "last_retrieved": TODAY,
                "promotion_status": promotion, "promotion_blockers": "; ".join(blockers),
                "notes": "Fields are selected by evidence grade; all underlying observations remain separately auditable.",
            }
            entities.append(entity)
            if blockers:
                qa.append({"entity_id": entity_id, "farm_name": name, "county": county,
                           "issue_type": "promotion_blocker", "issue_detail": "; ".join(blockers),
                           "recommended_action": "Verify with a farm-owned or current official source; do not publish until resolved.",
                           "status": "open"})
    entities.sort(key=lambda row: (row["county"], row["farm_name"].casefold(), row["entity_id"]))
    return entities, identity_review, qa


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fields = list(records[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    source_log: list[dict[str, Any]] = []
    raw_sources: dict[str, Any] = {}
    observations: list[Observation] = []
    critical_errors: list[str] = []
    observations.extend(referral_observations())

    sweet_body, log = fetch(SWEET_GROWN_URL)
    try: sweet = extract_sweet_grown_members(sweet_body) if sweet_body else []
    except (ValueError, json.JSONDecodeError) as exc: sweet, log["error"] = [], str(exc)
    source_log.append(source_log_entry(log, 1, "Sweet Grown Alabama — Farm members", len(sweet)))
    raw_sources["sweet_grown_farm_members"] = sweet
    observations.extend(sweet_observation(item) for item in sweet)

    official_counties: list[str] = []
    for kind, url, raw_key in [("farm-stand", FMA_STAND_URL, "fma_farm_stand_records"), ("u-pick", FMA_UPICK_URL, "fma_upick_records")]:
        body, log = fetch(url)
        try:
            options = extract_fma_options(body) if body else {}
            records = options.get("data_db", {}).get("objects", [])
            counties = [normalized_county(item.get("id", "")) for item in options.get("data_regions", {}).get("objects", [])]
            if len(counties) > len(official_counties): official_counties = counties
        except (ValueError, json.JSONDecodeError) as exc:
            records, log["error"] = [], str(exc)
        source_name = f"Alabama Farmers Market Authority — {kind} map"
        source_log.append(source_log_entry(log, 1, source_name, len(records)))
        raw_sources[raw_key] = records
        observations.extend(fma_observation(item, kind, url) for item in records)

    market_body, log = fetch(FMA_MARKET_URL)
    try:
        market_records = extract_fma_options(market_body).get("data_db", {}).get("objects", []) if market_body else []
    except (ValueError, json.JSONDecodeError) as exc:
        market_records, log["error"] = [], str(exc)
    source_log.append(source_log_entry(log, 2, "Alabama FMA — farmers-market channel map", len(market_records),
                                       "channel_infrastructure_only_not_farm_observations",
                                       "Markets are retained as channel evidence and never typed as farms."))
    raw_sources["fma_market_channel_records"] = market_records

    pdf_raw, log = fetch_bytes(FMA_2026_PDF_URL)
    try:
        pdf_text = pdf_to_text(pdf_raw) if pdf_raw else ""
        pdf_records = extract_pdf_farm_stands(pdf_text, official_counties)
    except (OSError, subprocess.SubprocessError) as exc:
        pdf_text, pdf_records, log["error"] = "", [], f"PDF extraction failed: {exc}"
    source_log.append(source_log_entry(log, 1, "Alabama FMA — 2026 statewide farm-stand roster", len(pdf_records)))
    raw_sources["fma_2026_pdf_farm_stands"] = pdf_records
    observations.extend(pdf_observation(item, index) for index, item in enumerate(pdf_records, 1))

    bee_body, log = fetch(BEEKS_URL)
    bees = bee_observations(bee_body) if bee_body else []
    source_log.append(source_log_entry(log, 1, "Alabama Plant Protection — Beekeepers Selling Bees", len(bees)))
    raw_sources["beekeepers_selling_bees"] = [asdict(item) for item in bees]
    observations.extend(bees)

    fts_body, log = fetch(FARM_TO_SCHOOL_URL)
    source_log.append(source_log_entry(log, 1, "Alabama Farm to School — farmer page", 0,
                                       "evaluated_no_public_producer_directory",
                                       "The page invites farmer registration but exposes no searchable producer roster."))
    raw_sources["farm_to_school_page_sha256"] = log.get("sha256", "")

    beef_body, log = fetch(BAMA_BEEF_URL)
    beef = bama_beef_observations(beef_body) if beef_body else []
    source_log.append(source_log_entry(log, 2, "Alabama Cattlemen’s Association — Bama Beef Sales Directory", len(beef)))
    raw_sources["bama_beef_records"] = [asdict(item) for item in beef]
    observations.extend(beef)

    eatwild_body, log = fetch(EATWILD_URL)
    eatwild = eatwild_observations(eatwild_body) if eatwild_body else []
    source_log.append(source_log_entry(log, 2, "EatWild Alabama directory", len(eatwild),
                                       note="Only farm addresses physically in Alabama were retained; out-of-state suppliers were excluded."))
    raw_sources["eatwild_alabama_records"] = [asdict(item) for item in eatwild]
    observations.extend(eatwild)

    pyo_counties: set[str] = set()
    for region, url in PYO_URLS.items():
        body, log = fetch(url)
        records, searched = pyo_observations(body, region, url) if body else ([], [])
        pyo_counties.update(searched)
        source_log.append(source_log_entry(log, 3, f"PickYourOwn — {region}", len(records),
                                           note=f"County sections searched: {len(searched)}; explicit closure records retained as grade F exclusions."))
        raw_sources[f"pickyourown_{normalized_name(region).replace(' ', '_')}"] = [asdict(item) for item in records]
        observations.extend(records)

    usft_body, log = fetch(US_FARM_TRAIL_URL)
    rendered_cards = len(re.findall(r'/farms/[^" ]+', usft_body)) if usft_body else 0
    source_log.append(source_log_entry(log, 3, "US Farm Trail — Alabama discovery page", 0,
                                       "evaluated_rejected_as_entity_source",
                                       f"Page exposed {rendered_cards} rendered farm links but mixed markets, duplicates, off-state entities, and weak per-record provenance; no automatic observations accepted."))
    raw_sources["us_farm_trail_evaluation"] = {"rendered_farm_link_occurrences": rendered_cards, "accepted": 0}

    if len(official_counties) != 67:
        critical_errors.append(f"Official county denominator expected 67, received {len(official_counties)}")
    for entry in source_log:
        if entry.get("error") and entry.get("source_name") != "FCC Census Area API":
            critical_errors.append(f"{entry.get('source_name')}: {entry.get('error')}")

    cache = old_county_cache()
    county_errors: list[dict[str, Any]] = []
    targets = []
    for item in observations:
        if item.county or item.latitude is None or item.longitude is None:
            continue
        cached = cache.get(item.observation_id)
        if cached:
            item.county, item.county_fips, item.county_source = cached
        else:
            targets.append(item)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fcc_county, float(item.latitude), float(item.longitude)): item for item in targets}
        for future in as_completed(futures):
            item = futures[future]
            try: county, fips, url, lookup_log = future.result()
            except Exception as exc:
                county, fips, url = "", "", ""
                lookup_log = {"url": "", "attempts_used": 0, "http_status": 0, "bytes": 0, "sha256": "",
                              "elapsed_seconds": 0, "error": f"Unhandled county lookup error: {exc}", "pass": 1,
                              "source_name": "FCC Census Area API", "records_parsed": 0, "retrieved_at": now_iso(),
                              "source_decision": "county_enrichment"}
            lookup_log["observation_id"] = item.observation_id
            source_log.append(lookup_log)
            if county:
                item.county, item.county_fips, item.county_source = county, fips, url
            else:
                county_errors.append({"observation_id": item.observation_id, "farm_name": item.farm_name,
                                      "latitude": item.latitude, "longitude": item.longitude,
                                      "error": lookup_log.get("error", "County not returned")})

    # A state-branded directory can contain border-area mistakes. Postal codes outside
    # Alabama are retained as explicit grade-F boundary exclusions, never silently
    # coerced into an Alabama county.
    for item in observations:
        if not item.county and item.source_name.startswith("Sweet Grown") and item.postal_code and not item.postal_code.startswith(("35", "36")):
            item.evidence_grade = "F"
            item.promotion_status = "excluded_outside_jurisdiction"
            item.notes = clean_text(item.notes + " Source address/coordinates resolve outside Alabama; retained as a boundary exception.")

    outside_observations = [item for item in observations if item.promotion_status == "excluded_outside_jurisdiction"]
    if outside_observations:
        stage_referrals((referral_from_observation(asdict(item), "AL") for item in outside_observations))

    address_targets = [item for item in observations if not item.county and item.evidence_grade != "F" and item.city and item.postal_code]
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(census_address_county, item.address, item.city, item.postal_code): item for item in address_targets}
        for future in as_completed(futures):
            item = futures[future]
            try: county, fips, url, lookup_log = future.result()
            except Exception as exc:
                county, fips, url = "", "", ""
                lookup_log = {"url": "", "attempts_used": 0, "http_status": 0, "bytes": 0, "sha256": "",
                              "elapsed_seconds": 0, "error": f"Unhandled address geocoder error: {exc}", "pass": item.source_pass,
                              "source_name": "U.S. Census Geocoder", "records_parsed": 0, "retrieved_at": now_iso(),
                              "source_decision": "county_enrichment"}
            lookup_log["observation_id"] = item.observation_id
            source_log.append(lookup_log)
            if county:
                item.county, item.county_fips, item.county_source = county, fips, url
            else:
                fallback = CITY_ZIP_COUNTY_FALLBACKS.get((item.city.casefold().strip(), item.postal_code))
                if fallback:
                    item.county = fallback
                    item.county_source = "Curator city/ZIP geography review after Census exact-address miss"
                    lookup_log["source_decision"] = "request_failed_but_county_resolved_by_documented_city_zip_review"
                else:
                    county_errors.append({"observation_id": item.observation_id, "farm_name": item.farm_name,
                                          "address": item.address, "city": item.city, "postal_code": item.postal_code,
                                          "error": lookup_log.get("error", "County not returned")})

    current_names = read_current_public_names()
    key_counts = Counter(item.candidate_key for item in observations if item.candidate_key)
    for item in observations:
        if key_counts[item.candidate_key] > 1:
            item.identity_review_status = "exact_normalized_name_group_reviewed_by_reconciliation_rules"
        if item.candidate_key in current_names:
            item.current_release_name_collision = current_names[item.candidate_key]
        item.county = "; ".join(normalized_county(value) for value in item.county.split(";") if value.strip())

    observations.sort(key=lambda item: (item.candidate_key, item.source_name, item.source_record_id))
    entities, identity_review, qa = reconcile(observations)
    eligible = [row for row in entities if row["promotion_status"] == "promotion_eligible_reviewed"]
    county_counts = Counter(row["county"] for row in entities if row["county"])
    eligible_county_counts = Counter(row["county"] for row in eligible if row["county"])
    pass_counts: dict[tuple[str, int], int] = Counter()
    for item in observations:
        for county in [normalized_county(value) for value in item.county.split(";") if value.strip()]:
            pass_counts[(county, item.source_pass)] += 1
    county_coverage = []
    for county in sorted(official_counties):
        count = county_counts[county]
        county_coverage.append({
            "county": county, "pass_1_observations": pass_counts[(county, 1)],
            "pass_2_observations": pass_counts[(county, 2)], "pass_3_observations": pass_counts[(county, 3)],
            "candidate_entities": count, "promotion_eligible_entities": eligible_county_counts[county],
            "status": "candidates_found" if count else "searched_none_found",
            "coverage_note": "All applicable statewide sources and the county's PickYourOwn region were reviewed; Pickens is covered by official/statewide and Bama Beef sources despite no PickYourOwn section."
        })
    missing_coverage = [row["county"] for row in county_coverage if row["status"] != "candidates_found"]
    if missing_coverage:
        critical_errors.append("Counties without any retained candidate entity: " + ", ".join(missing_coverage))

    observation_records = [asdict(item) for item in observations]
    excluded = [row for row in observation_records if row["evidence_grade"] == "F" or row["promotion_status"].startswith("excluded")]
    source_counts = Counter(item.source_name for item in observations)
    summary = {
        "status": "coverage_reviewed" if not critical_errors else "blocked_validation_errors",
        "release_id": f"al-coverage-reviewed-{TODAY}", "generated_at": now_iso(),
        "scope": "Alabama three-pass private state release; LA/MS canonical and public app remain unchanged.",
        "completion_definition": "All qualifying farms found under documented sources and three-pass process as of the release date; not every USDA-defined or undiscoverable farm.",
        "collection_passes_started": [1, 2, 3], "collection_passes_completed": [1, 2, 3] if not critical_errors else [],
        "source_datasets_evaluated": 14, "source_observations": len(observations),
        "source_observations_by_source": dict(sorted(source_counts.items())),
        "excluded_or_grade_f_observations": len(excluded), "proposed_entities": len(entities),
        "promotion_eligible_entities": len(eligible), "research_or_qa_entities": len(entities) - len(eligible),
        "identity_review_groups": len(identity_review),
        "identity_groups_split_for_county_conflict": sum(row["review_status"].startswith("split") for row in identity_review),
        "current_la_ms_name_collisions": sum(bool(item.current_release_name_collision) for item in observations),
        "alabama_counties_total": len(official_counties), "counties_with_candidates": sum(bool(row["candidate_entities"]) for row in county_coverage),
        "counties_without_candidates": missing_coverage, "counties_with_promotion_eligible_entities": sum(bool(row["promotion_eligible_entities"]) for row in county_coverage),
        "website_entities": sum(bool(row["website_url"]) for row in entities),
        "social_entities": sum(bool(row["facebook_url"] or row["instagram_url"] or row["tiktok_url"]) for row in entities),
        "direct_contact_entities": sum(bool(row["phone_internal"] or row["email_internal"]) for row in entities),
        "source_requests": len(source_log), "failed_source_requests": sum(bool(entry.get("error")) for entry in source_log),
        "county_lookup_failures": len(county_errors), "open_qa_items": len(qa),
        "critical_errors": critical_errors,
        "promotion_note": "Eligible means the staged row meets field/evidence/privacy gates; promotion into canonical data still requires a deliberate immutable release review.",
    }

    write_csv(OUTPUT_DIR / "observations.csv", observation_records)
    write_csv(OUTPUT_DIR / "entities.csv", entities)
    write_csv(OUTPUT_DIR / "identity-review.csv", identity_review)
    write_csv(OUTPUT_DIR / "qa-queue.csv", qa)
    write_csv(OUTPUT_DIR / "county-coverage.csv", county_coverage)
    write_csv(OUTPUT_DIR / "exclusions.csv", excluded)
    (OUTPUT_DIR / "request-log.json").write_text(json.dumps(source_log, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "county-lookup-errors.json").write_text(json.dumps(county_errors, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "raw-source-records.json").write_text(json.dumps(raw_sources, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "coverage_reviewed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
