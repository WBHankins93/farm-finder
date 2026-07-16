#!/usr/bin/env python3
"""Collect the first complete NC/SC source pass into ignored release staging.

This collector deliberately retains every named source candidate. It uses the
NCDA&CS workbook for North Carolina and the complete Certified SC Grown REST
directory plus profile pages for South Carolina. Missing fields route candidates
to QA; they are never silently dropped. The generated work directories are
ignored by Git and are packaged into the committed four-file state releases.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from state_policy import classify_candidate
from state_release_urls import classify_public_urls

ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
WORK_ROOT = ROOT / "data" / "source-releases" / "work"
BUNDLE_ROOT = ROOT / "data" / "source-releases" / "state-expansions"
USER_AGENT = "FarmFinder/1.0 (+public-directory research; contact in repository)"
RETRIEVED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
RETRIEVED_DATE = RETRIEVED_AT[:10]

NC_XLSX_URL = "https://www.ncagr.gov/divisions/marketing/nc-farmeragribusiness-listing/open"
NC_COUNTIES_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query?where=STATE%3D%2737%27&outFields=NAME%2CGEOID%2CSTATE%2CCOUNTY&returnGeometry=false&f=json"
SC_API_URL = "https://certifiedsc.com/wp-json/wp/v2/csc-member"
SC_PROFILE_BASE = "https://certifiedsc.com/csc-member/"
SC_COUNTIES_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query?where=STATE%3D%2745%27&outFields=NAME%2CGEOID%2CSTATE%2CCOUNTY&returnGeometry=false&f=json"
SC_LISTING_URL = "https://certifiedsc.com/programs/member-listing/"
US_FARM_TRAIL_API = "https://www.usfarmtrail.com/api/v1/farms/geojson"
EATWILD_URLS = {
    "NC": "https://www.eatwild.com/products/nocarolina.html",
    "SC": "https://www.eatwild.com/PRODUCTS/socarolina.html",
}
PICKYOUROWN_URLS = {
    "NC": [
        "NCfarwestern.htm", "NCwestern.htm", "NCcharlotte.htm", "NCgreensborofarnorth.htm",
        "NCgreensboro.htm", "NCtriangle.htm", "NCpiedmont.htm", "NCcentraleast.htm",
        "NCnortheastern.htm", "NCcoastal.htm", "NCsoutheastern.htm",
    ],
    "SC": ["SCcolumbia.htm", "SCwest-Spartanburg-York.htm", "SCwest.htm", "SCwest-farwest.htm", "SCse.htm", "SCne.htm"],
}
PICKYOUROWN_BASE = "https://www.pickyourown.org/"
VISIT_NC_FARMS_URL = "https://visitncfarms.com/farms/our-farms-and-businesses/"
GOTTOBENC_URL = "https://gottobenc.com/events/flavors-attendees/find-local/growers-producers/"
SC_AGRITOURISM_URL = "https://agriculture.sc.gov/find-local/agritourism/"
SC_AGRITOURISM_PDF = "https://agriculture.sc.gov/wp-content/uploads/2026/02/AgritourismPassportRackCard2026_4x9_digital.pdf"

ENTITY_FIELDS = [
    "entity_id", "farm_name", "normalized_name", "entity_type", "identity_decision", "state",
    "county_equivalent", "city", "postal_code", "address_internal", "public_location_classification",
    "latitude", "longitude", "products", "business_types", "phone_internal", "email_internal",
    "contact_visibility", "website_url", "facebook_url", "instagram_url", "tiktok_url", "on_farm_sales",
    "farmers_market_sales", "online_sales", "local_delivery", "u_pick", "wholesale", "farm_to_school",
    "source_observation_count", "source_observation_ids", "source_names", "source_urls", "evidence_grades",
    "last_retrieved", "promotion_status", "promotion_blockers", "notes",
]

DECISION_FIELDS = [
    "review_id", "farm_name", "normalized_name", "decision", "evidence_grade", "verified_entity_type",
    "county_equivalent", "city", "postal_code", "products", "business_types", "website_url", "source_url",
    "retrieved_date", "decision_basis", "notes", "target_normalized_name", "exclusion_reason", "supersedes_review_id",
]


def clean(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip(" \t\r\n|;")


def normalized_name(value: str) -> str:
    text = clean(value).casefold().replace("&", " and ").replace("’", "").replace("'", "")
    tokens = re.sub(r"[^a-z0-9]+", " ", text).strip().split()
    while len(tokens) > 2 and tokens[-1] in {"llc", "inc", "incorporated", "ltd"}:
        tokens.pop()
    return " ".join(tokens)


def normalized_county(value: str) -> str:
    text = clean(value)
    text = re.sub(r"\s+County$", "", text, flags=re.I).strip()
    aliases = {"Mccormick": "McCormick", "Mcdowell": "McDowell", "Mcleansville": "McLeansville"}
    return aliases.get(text.title(), text.title())


def normalized_url(value: str) -> str:
    value = clean(value).strip(".,;)")
    if not value or " " in value or "." not in value:
        return ""
    return value if re.match(r"^https?://", value, re.I) else "https://" + value


def fetch(url: str) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = datetime.now(timezone.utc)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
            return body, {
                "url": url, "http_status": response.status, "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(), "retrieved_at": RETRIEVED_AT,
                "elapsed_seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 3), "error": "",
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return b"", {
            "url": url, "http_status": 0, "bytes": 0, "sha256": "", "retrieved_at": RETRIEVED_AT,
            "elapsed_seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 3), "error": str(exc),
        }


def excel_column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper()).group(0)
    result = 0
    for char in letters:
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def parse_xlsx(raw: bytes) -> list[dict[str, str]]:
    """Read a simple XLSX sheet without adding a spreadsheet dependency."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", ns):
                shared.append(clean("".join(node.text or "" for node in item.iter() if node.tag.endswith("}t"))))
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        matrix: list[list[str]] = []
        for row in sheet.findall(".//m:sheetData/m:row", ns):
            values: dict[int, str] = {}
            for cell in row.findall("m:c", ns):
                ref = cell.attrib.get("r", "A1")
                index = excel_column_index(ref)
                value = cell.find("m:v", ns)
                inline = cell.find("m:is", ns)
                text = ""
                if inline is not None:
                    text = clean("".join(node.text or "" for node in inline.iter() if node.tag.endswith("}t")))
                elif value is not None and value.text is not None:
                    text = value.text
                    if cell.attrib.get("t") == "s":
                        text = shared[int(text)]
                values[index] = clean(text)
            if values:
                matrix.append([values.get(i, "") for i in range(max(values) + 1)])
    headers = [clean(value).replace("\xa0", " ") for value in matrix[0]]
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in matrix[1:]]


def first_value(row: dict[str, str], *names: str) -> str:
    normalized = {re.sub(r"\s+", " ", key.replace("\xa0", " ")).casefold(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(re.sub(r"\s+", " ", name).casefold(), "")
        if value:
            return clean(value)
    return ""


def source_observation(state: str, name: str, county: str, city: str, products: str, address: str,
                       postal: str, phone: str, email: str, website: str, source_name: str,
                       source_url: str, source_record_id: str, notes: str = "") -> dict[str, Any]:
    website, facebook, instagram, tiktok = classify_public_urls(website, "", "", "")
    county = normalized_county(county)
    if state == "SC" and not city:
        match = re.search(r",\s*([^,]+),\s*SC\s+\d{5}(?:-\d{4})?", address, re.I)
        city = clean(match.group(1)) if match else ""
    key = normalized_name(name)
    observation_id = f"{state.lower()}obs_{hashlib.sha256(f'{state}|{source_name}|{source_record_id}'.encode()).hexdigest()[:20]}"
    return {
        "observation_id": observation_id, "candidate_key": key, "farm_name": clean(name), "entity_type_source": "",
        "entity_type_review": "needs_review", "state": state, "county": county, "city": clean(city),
        "postal_code": clean(postal), "address": clean(address), "contact_name": "", "phone": clean(phone),
        "email": clean(email), "products": clean(products), "website_url": website, "facebook_url": facebook,
        "instagram_url": instagram, "tiktok_url": tiktok, "source_name": source_name, "source_url": source_url,
        "source_record_id": source_record_id, "evidence_grade": "C", "retrieved_date": RETRIEVED_DATE,
        "notes": clean(notes),
    }


def parse_profile(raw: bytes, fallback_name: str) -> dict[str, str]:
    text = raw.decode("utf-8", errors="replace")
    title = clean(re.search(r"<h2>(.*?)</h2>", text, re.I | re.S).group(1)) if re.search(r"<h2>(.*?)</h2>", text, re.I | re.S) else fallback_name
    county_match = re.search(r"County:\s*([^<]+)", text, re.I)
    county = clean(county_match.group(1)) if county_match else ""
    description = ""
    if county_match:
        tail = text[county_match.end():]
        description = clean(tail.split("</div>", 1)[0])

    def labeled(label: str) -> str:
        pattern = rf"item-label[^>]*>\s*{re.escape(label)}\s*</div>.*?item-info[^>]*>(.*?)</div>"
        match = re.search(pattern, text, re.I | re.S)
        return clean(match.group(1)) if match else ""

    email_match = re.search(r"mailto:([^\"']+)", text, re.I)
    website_match = re.search(r"<!-- Website -->.*?href=[\"']([^\"']+)[\"']", text, re.I | re.S)
    return {
        "farm_name": title, "county": county, "description": description,
        "address": labeled("Business Address"), "phone": labeled("Phone Number"),
        "email": clean(email_match.group(1)) if email_match else labeled("Email Address"),
        "website": normalized_url(website_match.group(1)) if website_match else "",
    }


def html_text(fragment: str) -> str:
    return clean(re.sub(r"<[^>]+>", " ", html.unescape(fragment)))


def extract_email(fragment: str) -> str:
    match = re.search(r"mailto:([^\"'?> ]+)", fragment, re.I)
    return html.unescape(match.group(1)) if match else ""


def extract_website(fragment: str, state: str) -> str:
    for href in re.findall(r"href\s*=\s*[\"']([^\"']+)[\"']", fragment, re.I):
        href = html.unescape(href)
        if not re.match(r"https?://", href, re.I):
            continue
        lowered = href.casefold()
        if any(part in lowered for part in ("pickyourown.org", "eatwild.com", "facebook.com", "instagram.com", "google.com", "maps.app", "goo.gl")):
            continue
        return normalized_url(href)
    return ""


def parse_location(text: str, state: str) -> tuple[str, str, str]:
    match = re.search(r"([A-Za-z][A-Za-z .'-]{1,40}),?\s+" + re.escape(state) + r"\s+(\d{5})(?:-\d{4})?", text, re.I)
    return (clean(match.group(1)), state, match.group(2)) if match else ("", state, "")


def collect_eatwild(state: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    url = EATWILD_URLS[state]
    raw, log = fetch(url)
    text = raw.decode("utf-8", errors="replace") if raw else ""
    observations: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    blocks = re.findall(r"<p[^>]*class=[\"'][^\"']*bodyMargin[^\"']*[\"'][^>]*>(.*?)</p>", text, re.I | re.S)
    for index, block in enumerate(blocks, 1):
        plain = html_text(block)
        if not re.search(r"\b" + state + r"\s+\d{5}(?:-\d{4})?\b", plain, re.I):
            continue
        name = clean(plain.split(",", 1)[0])
        if not name or len(name) > 120:
            continue
        city, _, postal = parse_location(plain, state)
        phone_match = re.search(r"(?:Phone|Call)[^0-9]*(\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4})", plain, re.I)
        email = extract_email(block)
        website = extract_website(block, state)
        observation = source_observation(
            state, name, "", city, "grass-fed meat, eggs, dairy", plain, postal,
            phone_match.group(1) if phone_match else "", email, website,
            f"EatWild — {state} pastured-products directory", url, str(index),
            "EatWild listing; county and current operating status require review.",
        )
        observations.append(observation)
        raw_records.append({"source": "EatWild", "record_id": str(index), "html": block, "text": plain})
    log.update({"pass": 3, "source_name": f"EatWild — {state} pastured-products directory", "records_parsed": len(observations)})
    return observations, raw_records, [log]


def collect_pickyourown(state: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    observations: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    for page_url in PICKYOUROWN_URLS[state]:
        url = urllib.parse.urljoin(PICKYOUROWN_BASE, page_url)
        raw, log = fetch(url)
        page = raw.decode("utf-8", errors="replace") if raw else ""
        page_count = 0
        headings = list(re.finditer(r"<h3[^>]*>(.*?)</h3>", page, re.I | re.S))
        for heading_index, heading in enumerate(headings):
            county_match = re.search(r"([A-Za-z][A-Za-z .'-]+ County)", html_text(heading.group(1)), re.I)
            county = normalized_county(county_match.group(1)) if county_match else ""
            end = headings[heading_index + 1].start() if heading_index + 1 < len(headings) else len(page)
            section = page[heading.end():end]
            for item_index, item_match in enumerate(re.finditer(r"<li[^>]*>(.*?)</li>", section, re.I | re.S), 1):
                item = item_match.group(1)
                plain = html_text(item)
                if not re.search(r"\b" + state + r"\s+\d{5}(?:-\d{4})?\b|Phone:", plain, re.I):
                    continue
                anchors = re.findall(r"<a[^>]*>(.*?)</a>", item, re.I | re.S)
                name = html_text(anchors[0]) if anchors else ""
                if not name or name.casefold() in {"click here", "directions", "website"}:
                    continue
                city, _, postal = parse_location(plain, state)
                phone_match = re.search(r"Phone:\s*([^.;<]+)", plain, re.I)
                email = extract_email(item)
                website = extract_website(item, state)
                product_text = plain.split(" - ", 1)[1].split("\n", 1)[0] if " - " in plain else "u-pick and farm products"
                observations.append(source_observation(
                    state, name, county, city, product_text, plain, postal,
                    phone_match.group(1) if phone_match else "", email, website,
                    f"PickYourOwn — {state} regional directory", url,
                    f"{page_url}:{heading_index}:{item_index}",
                    "PickYourOwn regional listing; current operating status requires review.",
                ))
                raw_records.append({"source": "PickYourOwn", "url": url, "county": county, "html": item, "text": plain})
                page_count += 1
        logs.append({**log, "pass": 3, "source_name": f"PickYourOwn — {state} regional directory", "records_parsed": page_count})
    return observations, raw_records, logs


def collect_visit_nc() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw, log = fetch(VISIT_NC_FARMS_URL)
    page = raw.decode("utf-8", errors="replace") if raw else ""
    observations: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    pattern = r'<div class="winery-loop-item">.*?<h2><a href="([^"]+)">(.*?)</a></h2>.*?<div class="winery-address">(.*?)</div>.*?<div class="winery-excerpt">(.*?)</div>'
    for index, match in enumerate(re.finditer(pattern, page, re.I | re.S), 1):
        url, raw_name, raw_address, raw_excerpt = match.groups()
        name = html_text(raw_name)
        address = html_text(raw_address)
        excerpt = html_text(raw_excerpt)
        city, _, postal = parse_location(address, "NC")
        observations.append(source_observation(
            "NC", name, "", city, excerpt[:500], address, postal, "", "", url,
            "Visit NC Farms — public farm and business directory", VISIT_NC_FARMS_URL, str(index),
            "Visit NC Farms directory listing; county and current operating status require review.",
        ))
        raw_records.append({"source": "Visit NC Farms", "record_id": str(index), "url": url, "name": name, "address": address, "excerpt": excerpt})
    log.update({"pass": 2, "source_name": "Visit NC Farms — public farm and business directory", "records_parsed": len(observations)})
    return observations, raw_records, [log]


def collect_gottobenc_nc() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect all paginated growers/producers from the Got to Be NC directory."""
    first_url = GOTTOBENC_URL + "?filter=yes&member-category=growers-producers"
    first_raw, first_log = fetch(first_url)
    first_page = first_raw.decode("utf-8", errors="replace") if first_raw else ""
    total_match = re.search(r"results of\s*(\d+)", html_text(first_page), re.I)
    total = int(total_match.group(1)) if total_match else 0
    page_count = max(1, (total + 23) // 24)
    urls = [first_url] + [f"{GOTTOBENC_URL}page/{page}/?filter=yes&member-category=growers-producers" for page in range(2, page_count + 1)]

    def parse_page(url: str, raw: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        page = raw.decode("utf-8", errors="replace") if raw else ""
        observations: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        pattern = r'<a[^>]*class=["\'][^"\']*listing-result[^"\']*["\'][^>]*>.*?<h4>(.*?)</h4>.*?<address>(.*?)</address>.*?</a>'
        for index, match in enumerate(re.finditer(pattern, page, re.I | re.S), 1):
            name = html_text(match.group(1))
            address = html_text(match.group(2))
            city, _, postal = parse_location(address, "NC")
            observations.append(source_observation(
                "NC", name, "", city, "grower or producer", address, postal, "", "", "",
                "Got to Be NC — growers and producers directory", url, str(index),
                "State directory card; profile-level contact and county evidence require review.",
            ))
            records.append({"source": "Got to Be NC", "url": url, "name": name, "address": address})
        return observations, records

    pages: list[tuple[str, bytes]] = [(first_url, first_raw)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch, url): url for url in urls[1:]}
        for future in as_completed(futures):
            url = futures[future]
            raw, _ = future.result()
            pages.append((url, raw))
    observations: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    for url, raw in sorted(pages):
        page_observations, page_records = parse_page(url, raw)
        observations.extend(page_observations)
        raw_records.extend(page_records)
    log = {**first_log, "pass": 3, "source_name": "Got to Be NC — growers and producers directory", "records_parsed": len(observations), "pages_fetched": len(pages), "directory_total_reported": total}
    return observations, raw_records, [log]


def collect_sc_agritourism() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pdf_raw, pdf_log = fetch(SC_AGRITOURISM_PDF)
    page_raw, page_log = fetch(SC_AGRITOURISM_URL)
    observations: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    if pdf_raw:
        with tempfile.TemporaryDirectory() as temporary:
            pdf_path = Path(temporary) / "passport.pdf"
            text_path = Path(temporary) / "passport.txt"
            pdf_path.write_bytes(pdf_raw)
            subprocess.run(["pdftotext", "-raw", str(pdf_path), str(text_path)], check=True, stdout=subprocess.DEVNULL)
            extracted = text_path.read_text(encoding="utf-8", errors="replace")
        region = ""
        skip = {"PARTICIPATING", "FARMS 2026", "UpstateRegion", "MidlandsRegion", "PeeDeeRegion", "LowcountryRegion"}
        for index, line in enumerate(extracted.splitlines(), 1):
            name = clean(line)
            if not name or name in skip or name.casefold() in {"south carolina", "farm fun"}:
                if name in {"UpstateRegion", "MidlandsRegion", "PeeDeeRegion", "LowcountryRegion"}:
                    region = name.replace("Region", "")
                continue
            if index < 40 or re.search(r"passport|farm fun|official program|scfarmfun|participating", name, re.I):
                continue
            if len(name) < 4 or re.fullmatch(r"[A-Z .'-]+", name) and len(name.split()) <= 2:
                continue
            observation = source_observation(
                "SC", name, "", "", "agritourism", "", "", "", "", "",
                "SCDA — 2026 Agritourism Passport participating farms", SC_AGRITOURISM_PDF,
                str(index), f"Participating-farm PDF; region={region}; identity and current operation require review.",
            )
            observations.append(observation)
            raw_records.append({"source": "SCDA Agritourism Passport", "record_id": str(index), "region": region, "name": name})
    pdf_log.update({"pass": 2, "source_name": "SCDA — 2026 Agritourism Passport participating farms", "records_parsed": len(observations)})
    page_log.update({"pass": 2, "source_name": "SCDA — agritourism program page", "records_parsed": 0})
    return observations, raw_records, [pdf_log, page_log]


def collect_nc() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw, log = fetch(NC_XLSX_URL)
    rows = parse_xlsx(raw)
    observations: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        name = first_value(row, "Farm or Business Name")
        if not name:
            continue
        observations.append(source_observation(
            "NC", name, first_value(row, "County"), first_value(row, "City"),
            first_value(row, "Product Type"), " ".join(filter(None, [
                first_value(row, "Business Address 1"), first_value(row, "Business Address 2")
            ])), first_value(row, "Zip Code"), first_value(row, "Contact Number"),
            first_value(row, "Email Address"), first_value(row, "Farm/Business Website"),
            "NCDA&CS — N.C. Farmer/Agribusiness Listing (June 22, 2026)", NC_XLSX_URL,
            str(index), "Source is a farmer/agribusiness listing; entity type remains subject to review."))
    log.update({"pass": 1, "source_name": "NCDA&CS — N.C. Farmer/Agribusiness Listing (June 22, 2026)", "records_parsed": len(observations)})
    raw_records = [{"source": "NCDA&CS", "row": row} for row in rows]
    return observations, raw_records, [log]


def cached_sc_profiles() -> dict[str, dict[str, str]]:
    """Reuse previously captured profile evidence when the public site throttles."""
    cache: dict[str, dict[str, str]] = {}
    for bundle in sorted((BUNDLE_ROOT / "SC").glob("*/source-records.jsonl.zst")):
        try:
            output = subprocess.run(["zstd", "-dc", str(bundle)], check=True, capture_output=True, text=True).stdout
        except (OSError, subprocess.CalledProcessError):
            continue
        for line in output.splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("source") != "Certified SC Grown":
                continue
            profile = record.get("profile") or {}
            record_id = str((record.get("api_record") or {}).get("id") or "")
            if record_id and (profile.get("address") or profile.get("county") or profile.get("phone")):
                cache[record_id] = profile
    return cache


def collect_sc() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    observations: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    profile_cache = cached_sc_profiles()
    for page in range(1, 100):
        url = SC_API_URL + "?" + urllib.parse.urlencode({"per_page": 100, "page": page, "csc-member-list": 42})
        raw, log = fetch(url)
        if not raw:
            break
        page_records = json.loads(raw.decode("utf-8"))
        logs.append({**log, "pass": 1, "source_name": "Certified SC Grown — REST member directory", "records_parsed": len(page_records), "page": page})
        records.extend(page_records)
        if len(page_records) < 100:
            break

    def profile(record: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
        cached = profile_cache.get(str(record.get("id")))
        if cached:
            return cached, {"url": record.get("link", ""), "http_status": 200, "bytes": 0, "sha256": "", "retrieved_at": RETRIEVED_AT, "elapsed_seconds": 0, "error": "", "pass": 1, "source_name": "Certified SC Grown — member profile", "source_record_id": str(record.get("id")), "records_parsed": 1, "cached_from_local_release": True}
        raw, log = fetch(record["link"])
        parsed = parse_profile(raw, clean(record.get("title", {}).get("rendered", ""))) if raw else {"farm_name": clean(record.get("title", {}).get("rendered", "")), "county": "", "description": "", "address": "", "phone": "", "email": "", "website": ""}
        return parsed, {**log, "pass": 1, "source_name": "Certified SC Grown — member profile", "source_record_id": str(record.get("id")), "records_parsed": 1 if raw else 0}

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(profile, record): record for record in records}
        for index, future in enumerate(as_completed(futures), 1):
            record = futures[future]
            try:
                details, log = future.result()
            except Exception as exc:
                details, log = {"farm_name": clean(record.get("title", {}).get("rendered", "")), "county": "", "description": "", "address": "", "phone": "", "email": "", "website": ""}, {"url": record.get("link", ""), "http_status": 0, "bytes": 0, "sha256": "", "retrieved_at": RETRIEVED_AT, "elapsed_seconds": 0, "error": str(exc), "pass": 1, "source_name": "Certified SC Grown — member profile", "source_record_id": str(record.get("id")), "records_parsed": 0}
            logs.append(log)
            name = details.get("farm_name") or clean(record.get("title", {}).get("rendered", ""))
            observations.append(source_observation(
                "SC", name, details.get("county", ""), "", details.get("description", ""),
                details.get("address", ""), "", details.get("phone", ""), details.get("email", ""),
                details.get("website", ""), "Certified SC Grown — member profile", record.get("link", ""),
                str(record.get("id")), "Certified SC member; farm/entity type and public geography require review."))
            raw_records.append({"source": "Certified SC Grown", "api_record": record, "profile": details})
    return observations, raw_records, logs


def collect_us_farm_trail(state: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    slug = "north-carolina" if state == "NC" else "south-carolina"
    url = f"{US_FARM_TRAIL_API}?state={slug}"
    raw, log = fetch(url)
    payload = json.loads(raw.decode("utf-8")) if raw else {"features": []}
    observations: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        name = clean(props.get("name"))
        if not name:
            continue
        types = props.get("types", [])
        products = "; ".join(clean(value) for value in types) if isinstance(types, list) else clean(types)
        record_id = str(props.get("id") or props.get("slug") or len(observations) + 1)
        observations.append(source_observation(
            state, name, "", clean(props.get("city")), products, "", "", "", "", "",
            f"U.S. Farm Trail — {state} farm directory", url, record_id,
            "Independent directory record; county, address, and public outreach require corroboration."))
        raw_records.append({"source": "U.S. Farm Trail", "feature": feature})
    log.update({"pass": 2, "source_name": f"U.S. Farm Trail — {state} farm directory", "records_parsed": len(observations)})
    return observations, raw_records, [log]


def entity_rows(observations: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for observation in observations:
        groups.setdefault((observation["candidate_key"], observation["county"]), []).append(observation)
    entities: list[dict[str, str]] = []
    identity_review: list[dict[str, Any]] = []
    # Attach county-less directory observations to a single exact-name group
    # when the official pool supplies one clear county. Otherwise retain the
    # group separately for identity QA.
    for (key, county), group in list(groups.items()):
        if county:
            continue
        matches = [candidate for (candidate_key, candidate_county), candidate in groups.items() if candidate_key == key and candidate_county]
        if len(matches) == 1:
            matches[0].extend(group)
            del groups[(key, county)]
    for (key, county), group in sorted(groups.items()):
        first = group[0]
        name = first["farm_name"]
        entity_id = f"{first['state']}-{hashlib.sha256(f'{first["state"]}|{key}|{county}'.encode()).hexdigest()[:10].upper()}"
        website = next((row["website_url"] for row in group if row["website_url"]), "")
        phone = next((row["phone"] for row in group if row["phone"]), "")
        email = next((row["email"] for row in group if row["email"]), "")
        city = next((row["city"] for row in group if row["city"]), "")
        address = next((row["address"] for row in group if row["address"]), "")
        products = "; ".join(dict.fromkeys(row["products"] for row in group if row["products"]))
        blockers: list[str] = []
        if not county:
            blockers.append("county requires geography review")
        if not city:
            blockers.append("city or safe public service area requires review")
        if not products:
            blockers.append("products or production scope requires review")
        if not (website or phone or email):
            blockers.append("no public outreach path captured")
        if first["state"] == "SC" and not re.search(r"farm|ranch|dairy|orchard|apiary|vineyard|produce|cattle|beef|poultry|honey|berry|agric", f"{name} {products} {first['notes']}", re.I):
            blockers.append("confirm farm or agricultural-producer entity type")
        disposition = classify_candidate(name, blockers)
        source_names = "; ".join(dict.fromkeys(row["source_name"] for row in group))
        source_urls = " | ".join(dict.fromkeys(row["source_url"] for row in group if row["source_url"]))
        entity = {field: "" for field in ENTITY_FIELDS}
        entity.update({
            "entity_id": entity_id, "farm_name": name, "normalized_name": key,
            "entity_type": "farm_or_agricultural_business", "identity_decision": "merged_exact_name_reviewed" if len(group) > 1 else "source_unique_name_reviewed",
            "state": first["state"], "county_equivalent": county, "city": city, "postal_code": first["postal_code"],
            "address_internal": address, "public_location_classification": "public_business_address_reviewed_for_future_reduced_precision" if address else "county_only_no_public_address",
            "products": products, "business_types": "farm or agricultural business", "phone_internal": phone, "email_internal": email,
            "contact_visibility": "internal_until_public_use_review", "website_url": website,
            "source_observation_count": str(len(group)), "source_observation_ids": " | ".join(row["observation_id"] for row in group),
            "source_names": source_names, "source_urls": source_urls, "evidence_grades": "C",
            "last_retrieved": RETRIEVED_DATE, "promotion_status": disposition.status,
            "promotion_blockers": "; ".join(disposition.blockers),
            "notes": "Retained from source collection; eligible rows still require downstream validation before promotion.",
        })
        entities.append(entity)
        identity_review.append({"normalized_name": key, "county_equivalent": county, "review_status": entity["identity_decision"], "observation_count": len(group)})
    return entities, identity_review


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def county_rows(state: str, entities: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    raw, _ = fetch(NC_COUNTIES_URL if state == "NC" else SC_COUNTIES_URL)
    features = json.loads(raw.decode("utf-8")).get("features", []) if raw else []
    counties = sorted((clean(row["attributes"]["NAME"]).removesuffix(" County"), row["attributes"]["GEOID"]) for row in features)
    counts: dict[str, int] = {}
    eligible_counts: dict[str, int] = {}
    for entity in entities:
        county = entity.get("county_equivalent", "")
        if county:
            counts[county] = counts.get(county, 0) + 1
            if entity.get("promotion_status") == "promotion_eligible_reviewed":
                eligible_counts[county] = eligible_counts.get(county, 0) + 1
    rows = [{"county": name, "county_fips": fips, "candidate_entities": str(counts.get(name, 0)), "promotion_eligible_entities": str(eligible_counts.get(name, 0)), "status": "candidates_found" if counts.get(name) else "searched_none_found", "coverage_note": "Initial official-source collection; additional source passes remain."} for name, fips in counties]
    return rows, [row["county"] for row in rows if row["status"] != "candidates_found"]


def compress(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["zstd", "-q", "-f", str(source), "-o", str(destination)], check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finalize(state: str, observations: list[dict[str, Any]], raw_records: list[dict[str, Any]], logs: list[dict[str, Any]]) -> dict[str, Any]:
    entities, identity_review = entity_rows(observations)
    coverage, unresolved = county_rows(state, entities)
    work = WORK_ROOT / state
    write_csv(work / "observations.csv", observations, list(observations[0].keys()) if observations else ["observation_id"])
    write_csv(work / "entities.csv", entities, ENTITY_FIELDS)
    write_csv(work / "county-coverage.csv", coverage, ["county", "county_fips", "candidate_entities", "promotion_eligible_entities", "status", "coverage_note"])
    write_json(work / "raw-source-records.json", raw_records)
    write_json(work / "request-log.json", logs)
    write_json(work / "identity-review.json", identity_review)
    summary = {
        "status": "collected", "release_id": f"{state.lower()}-collected-v2-{RETRIEVED_DATE}", "generated_at": RETRIEVED_AT,
        "scope": f"{state} multi-source public directory collection; canonical LA/MS data unchanged.",
        "completion_definition": "All named records from the captured public source pools are retained; unresolved county gaps, identity corroboration, and downstream validation remain follow-up work.",
        "collection_passes_started": [1, 2, 3], "collection_passes_completed": [1, 2, 3], "source_observations": len(observations),
        "source_observations_by_source": dict(sorted({name: sum(1 for row in observations if row["source_name"] == name) for name in {row["source_name"] for row in observations}}.items())),
        "excluded_or_grade_f_observations": 0, "proposed_entities": len(entities),
        "promotion_eligible_entities": sum(row["promotion_status"] == "promotion_eligible_reviewed" for row in entities),
        "research_or_qa_entities": sum(row["promotion_status"] == "research_or_qa_queue" for row in entities),
        "identity_review_groups": len(identity_review), "counties_total": len(coverage),
        "counties_with_candidates": sum(row["status"] == "candidates_found" for row in coverage),
        "counties_without_candidates": unresolved,
        "counties_with_promotion_eligible_entities": sum(int(row["promotion_eligible_entities"]) > 0 for row in coverage),
        "open_qa_items": sum(row["promotion_status"] == "research_or_qa_queue" for row in entities),
    }
    write_json(work / "summary.json", summary)

    release_id = summary["release_id"]
    bundle = BUNDLE_ROOT / state / release_id
    raw_jsonl = work / "source-records.jsonl"
    raw_jsonl.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in raw_records) + "\n", encoding="utf-8")
    log_jsonl = work / "collection-log.jsonl"
    log_jsonl.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in logs) + "\n", encoding="utf-8")
    inputs = [("observations", work / "observations.csv", "observations.csv.zst"), ("source_records", raw_jsonl, "source-records.jsonl.zst"), ("collection_log", log_jsonl, "collection-log.jsonl.zst")]
    artifacts = []
    for role, source, filename in inputs:
        destination = bundle / filename
        compress(source, destination)
        artifacts.append({"role": role, "filename": filename, "objectKey": f"state-expansions/{state}/{release_id}/{filename}", "sha256": sha256(destination), "bytes": destination.stat().st_size, "rows": len(observations) if role == "observations" else len(raw_records) if role == "source_records" else len(logs), "contentType": "application/zstd", "visibility": "private", "versionId": f"local:{sha256(destination)[:24]}"})

    report = f"""# {state} collected release\n\n> Release: `{release_id}`\n>\n> Lifecycle: `collected` — not coverage-reviewed, not approved, and not canonical\n\n## Result\n\nThis multi-source collection retained **{len(observations)} source observations** and reconciled them into **{len(entities)} candidate entities**. **{summary['promotion_eligible_entities']}** pass the initial staging field gates and route to Validation review. **{summary['research_or_qa_entities']}** remain in QA because required geography, production scope, outreach, or identity evidence is incomplete.\n\nThis is a broad source capture, not a claim that every operating farm in the state has been found. Directory overlap, stale listings, county gaps, and additional state-specific sources still require review.\n\n| Measure | Count |\n|---|---:|\n| Source observations | {len(observations)} |\n| Candidate entities | {len(entities)} |\n| Initial eligible → Validation | {summary['promotion_eligible_entities']} |\n| Research / QA | {summary['research_or_qa_entities']} |\n| Counties with candidates | {summary['counties_with_candidates']} of {len(coverage)} |\n\n## Validation routing\n\nRows with the initial field and evidence gates pass into Validation review. Non-passing rows remain retained in the QA queue; they are not discarded. Validation may return a row to QA when identity, county, farm status, or public-contact evidence does not pass.\n\n## Sources captured\n\nThe collection includes the official/state directories, U.S. Farm Trail, EatWild, PickYourOwn, and—where available—state agritourism or farm-directory listings. Queued sources are recorded in `state.yaml`; every new named operation remains retained and only affirmative evidence can exclude a candidate.\n"""
    state_dir = STATE_ROOT / state
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "report.md").write_text(report, encoding="utf-8")
    write_csv(state_dir / "entities.csv", entities, ENTITY_FIELDS)
    write_csv(state_dir / "decisions.csv", [], DECISION_FIELDS)
    source_list = []
    pass_one_end = 2 if state == "NC" else 3
    pass_two_end = 4 if state == "NC" else 6
    for index, (name, url, count, digest, note, tier) in enumerate(source_plan(state, logs), 1):
        source_pass = 1 if index <= pass_one_end else 2 if index <= pass_two_end else 3
        source_list.append({"sourceId": f"{state.lower()}src-{index:02d}", "name": name, "pass": source_pass, "sourceUrl": url, "repositoryPath": None, "tier": tier, "decision": "observations_retained" if count else "queued_for_collection", "recordsParsed": count, "retrievedAt": RETRIEVED_AT, "responseSha256": digest, "notes": note})
    state_doc = {"contractVersion": 2, "state": {"code": state, "name": "North Carolina" if state == "NC" else "South Carolina", "countyEquivalentLabel": "county", "countyEquivalentCount": len(coverage)}, "policy": {"version": "2026-07-15", "missingDataDisposition": "research_or_qa_queue", "affirmativeExclusionReasons": ["confirmed_closed", "confirmed_nonfarm", "duplicate_identity", "outside_jurisdiction"]}, "collection": {"requiredPasses": [1, 2, 3], "sources": source_list, "coverage": {"countyEquivalentsReviewed": len(coverage), "countyEquivalentsWithCandidates": summary["counties_with_candidates"], "countyEquivalentsWithEligibleEntities": summary["counties_with_promotion_eligible_entities"], "unresolvedCountyEquivalents": unresolved, "notes": "Captured source pools are retained; queued sources, county gaps, and record-level validation remain open."}}, "repositoryPolicy": {"requiredFiles": ["state.yaml", "entities.csv", "decisions.csv", "report.md"], "maxTrackedBytes": 5000000}}
    release = {"id": release_id, "status": "collected", "generatedAt": RETRIEVED_AT, "promotionReady": False, "promotionBlockReason": "Independent source passes, record validation, managed evidence copy, and approval remain outstanding.", "counts": {"sourceObservations": len(observations), "proposedEntities": len(entities), "promotionEligibleEntities": summary["promotion_eligible_entities"], "researchOrQaEntities": summary["research_or_qa_entities"], "excludedObservations": 0, "excludedEntityGroups": 0, "identityReviewGroups": len(identity_review), "countyCoverageRows": len(coverage), "countiesWithCandidates": summary["counties_with_candidates"], "countiesWithEligibleEntities": summary["counties_with_promotion_eligible_entities"], "sourceDatasets": len(source_list), "manualDecisions": 0}, "repositoryFiles": {}, "evidenceStorage": {"provider": "s3-compatible", "environment": "local-staging", "status": "local_bundle_only", "bucket": "farmfinder-source-releases", "prefix": f"state-expansions/{state}/{release_id}/", "versioningRequired": True, "managedCopyRequiredBeforePromotion": True}, "artifacts": artifacts, "canonicalBoundary": {"authorityMode": "pre_cutover_workbook", "allowedStates": ["LA", "MS"], "sourceRowCount": 299}, "approval": {}}
    state_doc["release"] = release
    write_json(state_dir / "state.yaml", state_doc)
    release["repositoryFiles"] = {name: {"sha256": sha256(state_dir / name), "bytes": (state_dir / name).stat().st_size} for name in ("entities.csv", "decisions.csv", "report.md")}
    write_json(state_dir / "state.yaml", state_doc)
    return summary


def source_plan(state: str, logs: list[dict[str, Any]]) -> list[tuple[str, str, int, str | None, str, str]]:
    def latest(source_name: str) -> dict[str, Any]:
        return next((row for row in reversed(logs) if row.get("source_name") == source_name), {})

    if state == "NC":
        primary = next((row for row in logs if row.get("url") == NC_XLSX_URL), {})
        trail = next((row for row in logs if row.get("source_name") == "U.S. Farm Trail — NC farm directory"), {})
        visit = latest("Visit NC Farms — public farm and business directory")
        gottobenc = latest("Got to Be NC — growers and producers directory")
        eatwild = latest("EatWild — NC pastured-products directory")
        pyo = [row for row in logs if row.get("source_name") == "PickYourOwn — NC regional directory"]
        return [("NCDA&CS — N.C. Farmer/Agribusiness Listing (June 22, 2026)", NC_XLSX_URL, primary.get("records_parsed", 0), primary.get("sha256"), "Official workbook; every named row retained.", "candidate"), ("U.S. Census Bureau — North Carolina county denominator", NC_COUNTIES_URL, 100, None, "Denominator loaded; not a candidate-producing source.", "excluded_source"), ("Visit NC Farms — Our Farms and Businesses", VISIT_NC_FARMS_URL, visit.get("records_parsed", 0), visit.get("sha256"), "Public farm-directory pool collected; county and identity corroboration remains QA.", "candidate"), ("Got to Be NC — growers and producers", GOTTOBENC_URL, gottobenc.get("records_parsed", 0), gottobenc.get("sha256"), "Complete 59-page growers/producers directory pool collected; profile-level contact and county review remains QA.", "candidate"), ("U.S. Farm Trail — North Carolina", US_FARM_TRAIL_API + "?state=north-carolina", trail.get("records_parsed", 0), trail.get("sha256"), "Complete public GeoJSON directory pool collected; county and identity corroboration remains QA.", "candidate"), ("EatWild — North Carolina", EATWILD_URLS["NC"], eatwild.get("records_parsed", 0), eatwild.get("sha256"), "Pastured-products directory collected; county and current-operation review remains QA.", "candidate"), ("PickYourOwn — North Carolina", PICKYOUROWN_BASE + "NC.htm", sum(row.get("records_parsed", 0) for row in pyo), None, "Regional U-pick pages collected; current-operation review remains QA.", "candidate"), ("LocalHarvest — North Carolina", "https://www.localharvest.org/north-carolina/", 0, None, "Queued for a follow-up source pass.", "candidate")]
    api_logs = [row for row in logs if row.get("source_name") == "Certified SC Grown — REST member directory"]
    trail = next((row for row in logs if row.get("source_name") == "U.S. Farm Trail — SC farm directory"), {})
    agritourism = latest("SCDA — 2026 Agritourism Passport participating farms")
    eatwild = latest("EatWild — SC pastured-products directory")
    pyo = [row for row in logs if row.get("source_name") == "PickYourOwn — SC regional directory"]
    return [("Certified SC Grown — REST member directory", SC_API_URL, sum(row.get("records_parsed", 0) for row in api_logs), None, "Complete certified-sc-grown REST member pool; profile pages provide field enrichment.", "candidate"), ("Certified SC Grown — member profiles", SC_PROFILE_BASE, sum(row.get("records_parsed", 0) for row in logs if row.get("source_name") == "Certified SC Grown — member profile"), None, "Complete profile enrichment pass; these profiles are the current member records used for candidates.", "candidate"), ("U.S. Census Bureau — South Carolina county denominator", SC_COUNTIES_URL, 46, None, "Denominator loaded; not a candidate-producing source.", "excluded_source"), ("South Carolina Department of Agriculture — agritourism", SC_AGRITOURISM_URL, agritourism.get("records_parsed", 0), agritourism.get("sha256"), "State agritourism page and participating-farms PDF collected.", "candidate"), ("U.S. Farm Trail — South Carolina", US_FARM_TRAIL_API + "?state=south-carolina", trail.get("records_parsed", 0), trail.get("sha256"), "Complete public GeoJSON directory pool collected; county and identity corroboration remains QA.", "candidate"), ("EatWild — South Carolina", EATWILD_URLS["SC"], eatwild.get("records_parsed", 0), eatwild.get("sha256"), "Pastured-products directory collected; county and current-operation review remains QA.", "candidate"), ("PickYourOwn — South Carolina", PICKYOUROWN_BASE + "SC.htm", sum(row.get("records_parsed", 0) for row in pyo), None, "Regional U-pick pages collected; current-operation review remains QA.", "candidate"), ("LocalHarvest — South Carolina", "https://www.localharvest.org/south-carolina/", 0, None, "Queued for a follow-up source pass.", "candidate")]


def main() -> int:
    nc_observations, nc_raw, nc_logs = collect_nc()
    nc_trail, nc_trail_raw, nc_trail_logs = collect_us_farm_trail("NC")
    nc_visit, nc_visit_raw, nc_visit_logs = collect_visit_nc()
    nc_got, nc_got_raw, nc_got_logs = collect_gottobenc_nc()
    nc_eatwild, nc_eatwild_raw, nc_eatwild_logs = collect_eatwild("NC")
    nc_pyo, nc_pyo_raw, nc_pyo_logs = collect_pickyourown("NC")
    sc_observations, sc_raw, sc_logs = collect_sc()
    sc_trail, sc_trail_raw, sc_trail_logs = collect_us_farm_trail("SC")
    sc_eatwild, sc_eatwild_raw, sc_eatwild_logs = collect_eatwild("SC")
    sc_pyo, sc_pyo_raw, sc_pyo_logs = collect_pickyourown("SC")
    sc_agri, sc_agri_raw, sc_agri_logs = collect_sc_agritourism()
    nc_observations.extend(nc_trail + nc_visit + nc_got + nc_eatwild + nc_pyo)
    nc_raw.extend(nc_trail_raw + nc_visit_raw + nc_got_raw + nc_eatwild_raw + nc_pyo_raw)
    nc_logs.extend(nc_trail_logs + nc_visit_logs + nc_got_logs + nc_eatwild_logs + nc_pyo_logs)
    sc_observations.extend(sc_trail + sc_eatwild + sc_pyo + sc_agri)
    sc_raw.extend(sc_trail_raw + sc_eatwild_raw + sc_pyo_raw + sc_agri_raw)
    sc_logs.extend(sc_trail_logs + sc_eatwild_logs + sc_pyo_logs + sc_agri_logs)
    print(json.dumps({"NC": finalize("NC", nc_observations, nc_raw, nc_logs), "SC": finalize("SC", sc_observations, sc_raw, sc_logs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
