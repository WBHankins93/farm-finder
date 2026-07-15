#!/usr/bin/env python3
"""Build a coverage-reviewed Texas farm-source staging release.

The collector keeps every source assertion as an immutable observation, applies
only documented exact-name identity rules, accounts for all 254 counties, and
does not modify the canonical Louisiana/Mississippi release.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from state_release_urls import classify_public_urls
from state_policy import classify_candidate, validate_exclusion_reason

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_alabama import (  # Reuse the tested transport and small HTML DOM.
    Observation,
    clean_text,
    clean_url,
    dom,
    fetch,
    fetch_bytes,
    first_descendant,
    link_values,
    now_iso,
    source_log_entry,
    table_rows,
)


ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "research" / "state-expansions" / "TX"
OUTPUT_DIR = ROOT / "data" / "source-releases" / "work" / "TX"
PUBLIC_FARMS = ROOT / "03-app" / "site" / "app" / "data" / "farms.json"
MANUAL_VERIFICATION_DECISIONS = STATE_DIR / "decisions.csv"
TODAY = date.today().isoformat()

GO_TEXAN_URL = "https://bridge.texasagriculture.gov/GoTexanSearch/"
GO_TEXAN_FARM_CSV_URL = GO_TEXAN_URL + "?" + urllib.parse.urlencode({
    "resultsFormat": "CommaSeparatedValues", "searchType": "Advanced",
    "pageSize": "2147483647", "businessType": "Farm And Ranch", "pageNumber": "1",
})
TDA_MARKETS_URL = "https://texasagriculture.gov/Grants-Services/Certified-Farmers-Markets"
FARM_TO_SCHOOL_URL = "https://www.squaremeals.org/Portals/8/files/NSLP/LFS/LFS%20Vendor%20Resource%20List%20Updated%20Nov%202024.pdf?ver=I7PGgvoElV78S-FFin0OiQ%3D%3D"
TEXAS_LOCAL_FOOD_URL = "https://texaslocalfood.org/directory/"
TEXAS_LOCAL_FOOD_CONTENT = "https://texaslocalfood.org/wp-json/tld-connector/v1/content"
TEXAS_LOCAL_FOOD_PROFILE = "https://texaslocalfood.org/wp-json/tld-connector/v1/partner/{id}"
EATWILD_URL = "https://www.eatwild.com/products/texas.html"
PYO_INDEX_URL = "https://www.pickyourown.org/TX.htm"
USDA_COUNTIES_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query?"
    + urllib.parse.urlencode({"where": "STATE='48'", "outFields": "NAME,GEOID,STATE,COUNTY",
                              "returnGeometry": "false", "f": "json"})
)
CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
CENSUS_ZCTA_COUNTY_URL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt"
CENSUS_PLACE_COUNTY_URL = "https://www2.census.gov/geo/docs/reference/codes2020/national_place_by_county2020.txt"
USDA_DIRECTORY_URL = "https://www.ams.usda.gov/services/local-regional/food-directories-listings"
US_FARM_TRAIL_URL = "https://www.usfarmtrail.com/states/texas"
YOU_PICK_TEXAS_URL = "https://www.youpicktexas.com/"
SHOP_TEXAS_URL = "https://shoptexasfarms.com/business-directory/"
SHOP_TEXAS_AJAX = "https://shoptexasfarms.com/wp-admin/admin-ajax.php"
TSL_COUNTY_SEATS_URL = "https://www.tsl.texas.gov/ref/abouttx/countyseats.html"
LOCALHARVEST_BASE = "https://www.localharvest.org"

PYO_URLS = {
    "Abilene": "https://www.pickyourown.org/TXabilene.htm",
    "Austin": "https://www.pickyourown.org/TXaustin.htm",
    "Corpus Christi": "https://www.pickyourown.org/TXcorpus.htm",
    "Dallas / Fort Worth": "https://www.pickyourown.org/TXdallas.htm",
    "Houston / Southeast": "https://www.pickyourown.org/TXhouston.htm",
    "Lubbock": "https://www.pickyourown.org/TXlubbock.htm",
    "Northeast": "https://www.pickyourown.org/TXnortheast.htm",
    "Panhandle": "https://www.pickyourown.org/TXpanhandle.htm",
    "San Angelo": "https://www.pickyourown.org/TXsanangelo.htm",
    "San Antonio": "https://www.pickyourown.org/TXsanantonio.htm",
    "Southern Tip": "https://www.pickyourown.org/TXsouth.htm",
    "Far West": "https://www.pickyourown.org/TXfarwest.htm",
    "Wichita Falls": "https://www.pickyourown.org/TXwichitafalls.htm",
}

GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}


def normalized_name(value: str) -> str:
    value = clean_text(value).casefold().replace("&", " and ").replace("’", "").replace("'", "")
    tokens = re.sub(r"[^a-z0-9]+", " ", value).strip().split()
    while len(tokens) > 2 and tokens[-1] in {"llc", "inc", "incorporated"}:
        tokens.pop()
    return " ".join(tokens)


def normalized_county(value: str) -> str:
    value = re.sub(r"^(?:Texas\s*/\s*)|\s+County$", "", clean_text(value), flags=re.I)
    aliases = {"Dewitt": "DeWitt", "Mcculloch": "McCulloch", "Mclennan": "McLennan",
               "Mcmullen": "McMullen", "La salle": "La Salle", "Jeff davis": "Jeff Davis"}
    return aliases.get(value.casefold().capitalize(), value.title())


def make_observation_id(source_name: str, source_record_id: str, farm_name: str) -> str:
    raw = f"TX|{source_name}|{source_record_id}|{farm_name}".encode()
    return f"txobs_{hashlib.sha256(raw).hexdigest()[:20]}"


def empty_observation(source_name: str, source_record_id: str, farm_name: str, source_url: str,
                      source_pass: int, grade: str) -> dict[str, Any]:
    return {
        "observation_id": make_observation_id(source_name, source_record_id, farm_name),
        "candidate_key": normalized_name(farm_name), "identity_review_status": "source_unique_name",
        "current_release_name_collision": "", "farm_name": farm_name, "entity_type_source": "",
        "entity_type_review": "needs_review", "state": "TX", "county": "", "county_fips": "",
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


def manual_verification_observations() -> tuple[list[Observation], set[str], list[dict[str, str]]]:
    """Load evidence-backed curator decisions without mutating source claims.

    Corroborations become additional observations. Exclusions become grade-F
    decision observations and suppress the matching normalized-name group from
    the candidate entity set while leaving every original assertion auditable.
    """
    if not MANUAL_VERIFICATION_DECISIONS.exists():
        return [], set(), []
    with MANUAL_VERIFICATION_DECISIONS.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    observations: list[Observation] = []
    excluded_keys: set[str] = set()
    seen_review_ids: set[str] = set()
    for record in records:
        review_id = clean_text(record.get("review_id"))
        farm_name = clean_text(record.get("farm_name"))
        key = clean_text(record.get("normalized_name"))
        decision = clean_text(record.get("decision")).casefold()
        if not review_id or review_id in seen_review_ids:
            raise ValueError(f"Manual verification has a missing or duplicate review_id: {review_id!r}")
        if not farm_name or key != normalized_name(farm_name):
            raise ValueError(f"Manual verification {review_id} has an invalid normalized-name target")
        if decision not in {"corroborate", "exclude"}:
            raise ValueError(f"Manual verification {review_id} has unsupported decision {decision!r}")
        if decision == "exclude":
            validate_exclusion_reason(clean_text(record.get("exclusion_reason")))
        seen_review_ids.add(review_id)
        source_url = clean_url(record.get("source_url"))
        if not source_url:
            raise ValueError(f"Manual verification {review_id} is missing a valid evidence URL")
        grade = "F" if decision == "exclude" else clean_text(record.get("evidence_grade")) or "C"
        item = empty_observation(
            "FarmFinder curator verification — farm-owned or authoritative evidence",
            review_id,
            farm_name,
            source_url,
            3,
            grade,
        )
        item.update({
            "identity_review_status": f"manual_{decision}_decision_recorded",
            "entity_type_source": clean_text(record.get("verified_entity_type")),
            "entity_type_review": "manual_review_excluded_nonfarm" if decision == "exclude" else
                                  "farm_activity_confirmed_by_farm_owned_or_authoritative_source",
            "county": normalized_county(record.get("county_equivalent") or record.get("county", "")),
            "county_source": source_url,
            "city": clean_text(record.get("city")),
            "postal_code": clean_text(record.get("postal_code")),
            "location_precision": "curator_verified_safe_service_area",
            "products": clean_text(record.get("products")),
            "business_types": clean_text(record.get("business_types")),
            "website_url": clean_url(record.get("website_url")),
            "retrieved_date": clean_text(record.get("retrieved_date")) or TODAY,
            "promotion_status": "excluded_manual_verification_nonfarm" if decision == "exclude" else
                                "staged_pending_rules",
            "notes": "; ".join(value for value in [clean_text(record.get("decision_basis")),
                                                     clean_text(record.get("notes"))] if value),
        })
        observations.append(Observation(**item))
        if decision == "exclude":
            excluded_keys.add(key)
    return observations, excluded_keys, records


def first_value(meta: dict[str, Any], key: str) -> str:
    value = meta.get(key, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return clean_text(value)


def term_names(profile: dict[str, Any], key: str) -> list[str]:
    return [clean_text(item.get("name")) for item in ((profile.get("terms") or {}).get(key) or [])
            if clean_text(item.get("name"))]


def split_links(value: str) -> tuple[str, str, str, str]:
    website = facebook = instagram = tiktok = ""
    for raw in re.split(r"[\r\n\s]+", html.unescape(value)):
        url = clean_url(raw)
        if not url:
            continue
        if "facebook.com" in url and not facebook: facebook = url
        elif "instagram.com" in url and not instagram: instagram = url
        elif "tiktok.com" in url and not tiktok: tiktok = url
        elif not website: website = url
    return website, facebook, instagram, tiktok


def go_texan_observations(body: str) -> tuple[list[Observation], list[dict[str, str]]]:
    rows = list(csv.DictReader(io.StringIO(body.lstrip("\ufeff"))))
    records = []
    for index, item in enumerate(rows, 1):
        name = clean_text(item.get("Facility"))
        if not name:
            continue
        web = clean_url(item.get("Website"))
        row = empty_observation("Texas Department of Agriculture — GO TEXAN Farm And Ranch",
                                str(index), name, GO_TEXAN_FARM_CSV_URL, 1, "B")
        row.update({
            "entity_type_source": "Farm And Ranch", "entity_type_review": "official_directory_farm_ranch_claim",
            "county": normalized_county(item.get("County", "")), "county_source": "GO TEXAN source county; independently checked when address resolves",
            "city": clean_text(item.get("City")).title(), "postal_code": clean_text(item.get("ZIP Code"))[:10],
            "address": clean_text(item.get("Address")), "location_precision": "public_official_directory_address",
            "contact_name": clean_text(item.get("Contact Name")), "phone": "" if item.get("Phone") == "N/A" else clean_text(item.get("Phone")),
            "products": "" if item.get("Products") == "N/A" else clean_text(item.get("Products")),
            "business_types": "GO TEXAN Farm And Ranch; " + clean_text(item.get("Member Type")),
            "website_url": web, "on_farm_sales": "Direct To Public" in clean_text(item.get("How Products Are Sold")),
            "retail_sales": "Retailers" in clean_text(item.get("How Products Are Sold")),
            "wholesale": "Wholesale" in clean_text(item.get("How Products Are Sold")),
            "notes": "Brands: " + clean_text(item.get("Brand Names")) + "; sales: " + clean_text(item.get("How Products Are Sold")),
        })
        records.append(Observation(**row))
    return records, rows


def farm_to_school_records(raw: bytes) -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "vendors.pdf"; text_path = Path(tmp) / "vendors.txt"
        pdf.write_bytes(raw)
        subprocess.run(["pdftotext", "-layout", str(pdf), str(text_path)], check=True, capture_output=True)
        lines = text_path.read_text(encoding="utf-8", errors="replace").splitlines()
    category = r"(?:Meat|Dairy Products|Distributor|Fruits?, Vegetables|Vegetables|Grains|Other|Fruit|Honey)"
    records = []
    for line in lines:
        if not re.match(rf"^{category}\s{{2,}}", line):
            continue
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 3:
            continue
        parts += [""] * (7 - len(parts))
        records.append(dict(zip(["category", "company", "city", "website", "address", "phone", "email"], parts[:7])))
    return records


def farm_to_school_observations(records: list[dict[str, str]]) -> list[Observation]:
    observations = []
    for index, item in enumerate(records, 1):
        name = clean_text(item["company"])
        if not name or item["category"] == "Distributor":
            continue
        row = empty_observation("Texas Department of Agriculture — Farm to School vendor resource list",
                                str(index), name, FARM_TO_SCHOOL_URL, 1, "E")
        website = "" if item["website"].casefold() in {"no website", "n/a"} else usable_website(item["website"])
        facebook = clean_url(item["website"]) if "facebook.com" in item["website"].casefold() else ""
        postal_matches = re.findall(r"\b(\d{5})(?:-\d{4})?\b", item["address"])
        postal = postal_matches[-1] if postal_matches else ""
        row.update({
            "entity_type_source": f"Farm-to-school vendor — {item['category']}",
            "entity_type_review": "official_vendor_candidate_requires_farm_operation_review",
            "city": clean_text(item["city"]).title(), "postal_code": postal, "address": clean_text(item["address"]),
            "location_precision": "official_vendor_resource_address", "phone": clean_text(item["phone"]),
            "email": "" if item["email"].casefold() in {"n/a", "email via website"} else clean_text(item["email"]),
            "products": clean_text(item["category"]), "business_types": "Farm-to-school vendor candidate",
            "website_url": website, "facebook_url": facebook, "farm_to_school": True, "wholesale": True,
            "promotion_status": "staged_pending_entity_type_and_freshness_review",
            "notes": "Official November 2024 vendor resource; inclusion does not by itself prove a current farm operation.",
        })
        observations.append(Observation(**row))
    return observations


def strip_tags(value: str) -> str:
    value = re.sub(r"[\x00-\x1f\x7f]", " ", value)
    return clean_text(re.sub(r"<[^>]+>", " ", value))


def usable_website(value: str) -> str:
    value = clean_url(value)
    if not value:
        return ""
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or not host or "." not in host or parsed.username:
        return ""
    rejected = ("facebook.com", "instagram.com", "twitter.com", "x.com", "pinterest.com",
                "mapquest.com", "google.com", "goo.gl", "g.page", "csaware.com",
                "share.imapbuilder.com", "gstatic.com", "googleapis.com")
    blocked = any(host == domain or host.endswith("." + domain) for domain in rejected) or host.startswith("lh-images.")
    return "" if blocked else value


def normalized_city(value: str) -> str:
    return re.sub(r",?\s+(?:TX|Texas)\s*$", "", clean_text(value), flags=re.I).strip(" ,").title()


def single_county_zcta_map(body: str) -> tuple[dict[str, tuple[str, str]], list[dict[str, str]]]:
    """Return only ZCTAs whose Census relationship is wholly within one TX county."""
    rows = list(csv.DictReader(io.StringIO(body.lstrip("\ufeff")), delimiter="|"))
    texas = [row for row in rows if row.get("GEOID_COUNTY_20", "").startswith("48") and row.get("GEOID_ZCTA5_20")]
    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in texas:
        grouped[row["GEOID_ZCTA5_20"]].append(row)
    mapping = {}
    for postal_code, matches in grouped.items():
        if len(matches) == 1:
            row = matches[0]
            mapping[postal_code] = (normalized_county(row["NAMELSAD_COUNTY_20"]), row["GEOID_COUNTY_20"])
    return mapping, texas


def single_county_place_map(body: str) -> tuple[dict[str, tuple[str, str]], list[dict[str, str]]]:
    rows = list(csv.DictReader(io.StringIO(body.lstrip("\ufeff")), delimiter="|"))
    texas = [row for row in rows if row.get("STATEFP") == "48" and row.get("PLACENAME")]
    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in texas:
        place = re.sub(r"\s+(?:city|town|village|CDP)\s*$", "", row["PLACENAME"], flags=re.I).casefold()
        grouped[place].append(row)
    mapping = {}
    for place, matches in grouped.items():
        counties = {row["COUNTYFP"]: row for row in matches}
        if len(counties) == 1:
            row = next(iter(counties.values()))
            mapping[place] = (normalized_county(row["COUNTYNAME"]), "48" + row["COUNTYFP"])
    return mapping, texas


def shop_texas_cards(pages: list[str]) -> list[dict[str, str]]:
    joined = "\n".join(pages)
    matches = list(re.finditer(r'<a href="(https://shoptexasfarms\.com/business-directory/entry/[^"?#]+)"[^>]*class="frm-detail-link">(.*?)</a>', joined, re.I | re.S))
    records: dict[str, dict[str, str]] = {}
    for index, match in enumerate(matches):
        url = match.group(1).rstrip("/")
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(joined), match.end() + 8000)
        segment = joined[match.end():end]
        location = re.search(r"([A-Za-z][A-Za-z .'-]{1,50}),\s*Texas\s+(\d{5})", strip_tags(segment), re.I)
        description = ""
        desc_match = re.search(r"</p>\s*<p[^>]*>(.*?)<a[^>]*>Read More", segment, re.I | re.S)
        if desc_match: description = strip_tags(desc_match.group(1))
        records[url] = {"url": url + "/", "name": strip_tags(match.group(2)),
                        "city": location.group(1).title() if location else "",
                        "postal_code": location.group(2) if location else "", "description": description}
    return list(records.values())


def shop_texas_observation(card: dict[str, str], body: str) -> Observation:
    location_block = re.search(r"<pre>\s*<svg.*?</svg>\s*(.*?)</pre>", body, re.I | re.S)
    location_text = strip_tags(location_block.group(1)) if location_block else ""
    location = None
    if location_text and card["city"]:
        location = re.match(rf"(.*?)\s*,?\s*{re.escape(card['city'])}\s*,?\s*Texas\s+(\d{{5}})\s*$",
                            location_text, re.I)
    about = card["description"]
    profile = re.search(r'id="frm_profile_\d+"[^>]*>(.*?)</div>', body, re.I | re.S)
    if profile: about = strip_tags(profile.group(1))
    profile_start = body.find('class="et_pb_text_inner"')
    profile_end = body.find('id="frm_reviews"', profile_start)
    profile_area = body[profile_start:profile_end] if profile_start >= 0 and profile_end > profile_start else body
    links = re.findall(r'href="(https?://[^" ]+)"', profile_area, re.I)
    website = facebook = instagram = ""
    for value in links:
        value = html.unescape(value)
        if "shoptexasfarms.com" in value: continue
        if "facebook.com" in value and not facebook: facebook = value
        elif "instagram.com" in value and not instagram: instagram = value
        elif not website:
            website = usable_website(value)
    row = empty_observation("Shop Texas Farms — member business directory", card["url"].rstrip("/").rsplit("/", 1)[-1],
                            card["name"], card["url"], 2, "D")
    row.update({
        "entity_type_source": "Member business", "entity_type_review": "member_directory_requires_farm_operation_review",
        "city": card["city"], "postal_code": location.group(2) if location else card["postal_code"],
        "address": location.group(1).strip(" ,") if location else "", "location_precision": "member_public_business_address_or_city",
        "products": about[:800] or "Texas farm/ranch products; see source profile", "business_types": "Shop Texas Farms member",
        "website_url": website, "facebook_url": facebook, "instagram_url": instagram,
        "on_farm_sales": True, "notes": about[:1500],
    })
    return Observation(**row)


def county_seat_pairs(body: str) -> list[tuple[str, str]]:
    pairs = []
    for cells in table_rows(dom(body)):
        if len(cells) >= 2 and clean_text(cells[0]).casefold() != "county":
            county, seat = clean_text(cells[0]), clean_text(cells[1])
            if county and seat: pairs.append((normalized_county(county), seat))
    return pairs


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def localharvest_cards(body: str, searched_county: str, search_url: str) -> list[dict[str, str]]:
    matches = list(re.finditer(r'<a href="(/[^"]+-M\d+)" class="mt-0">(.*?)</a>', body, re.I | re.S))
    records = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(body), match.end() + 4000)
        segment = body[match.end():end]
        location = re.search(r'>([A-Za-z][A-Za-z .\'-]{1,50}),\s*Texas</a>', segment, re.I)
        summary = re.search(r'<p class="d-none d-sm-inline mb-1">(.*?)</p>', segment, re.I | re.S)
        records.append({"url": LOCALHARVEST_BASE + match.group(1), "name": strip_tags(match.group(2)),
                        "city": location.group(1).title() if location else "",
                        "summary": strip_tags(summary.group(1)) if summary else "",
                        "searched_county": searched_county, "search_url": search_url})
    return records


def localharvest_observation(card: dict[str, str], body: str) -> Observation:
    location = re.search(r'<strong>Location:</strong><br\s*/?>\s*(.*?)\s*<br\s*/?>\s*([A-Za-z][A-Za-z .\'-]{1,45}),\s*TX\s+(\d{5})', body, re.I | re.S)
    updated = re.search(r"Listing last updated on\s*<span[^>]*>\s*([^<]+)", body, re.I)
    grade = "E"
    if updated:
        try:
            updated_on = datetime.strptime(clean_text(updated.group(1)), "%B %d, %Y").date()
            if 0 <= (date.today() - updated_on).days <= 180:
                grade = "D"
        except ValueError:
            pass
    description = re.search(r'<div id="descDiv"[^>]*>(.*?)</div>', body, re.I | re.S)
    desc_text = strip_tags(description.group(1)) if description else card["summary"]
    phone = ""
    contact = re.search(r'<div id="contact-block".*?<div class="mt-2 ms-2">(.*?)</div>', body, re.I | re.S)
    if contact:
        phone_match = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-./ ]\d{3}[-./ ]\d{4}(?!\d)", strip_tags(contact.group(1)))
        phone = phone_match.group(0) if phone_match else ""
    website = facebook = instagram = ""
    contact_start = body.find('id="contact-block"')
    contact_end = body.find("Coming Events", contact_start)
    contact_area = body[contact_start:contact_end] if contact_start >= 0 and contact_end > contact_start else ""
    for value in re.findall(r'href="(https?://[^" ]+)"', contact_area, re.I):
        if "localharvest.org" in value or "google.com" in value: continue
        if "facebook.com" in value and not facebook: facebook = value
        elif "instagram.com" in value and not instagram: instagram = value
        elif not website: website = usable_website(value)
    products = []
    product_area = re.search(r"Products and Crops(.*?)(?:Contact Information|RIGHT BAR)", body, re.I | re.S)
    if product_area:
        products = [strip_tags(x) for x in re.findall(r'<li><a[^>]*>(.*?)</a></li>', product_area.group(1), re.I | re.S)]
    record_id = (re.search(r"-M(\d+)$", card["url"]) or ["", card["url"]])[1]
    row = empty_observation("LocalHarvest — Texas county-seat gap search", record_id, card["name"], card["url"], 3, grade)
    row.update({
        "entity_type_source": "Family Farm", "entity_type_review": "farm_activity_confirmed_by_directory_farm_search",
        "city": location.group(2).title() if location else card["city"], "postal_code": location.group(3) if location else "",
        "address": strip_tags(location.group(1)) if location else "", "location_precision": "public_directory_address_or_city",
        "phone": phone, "products": "; ".join(dict.fromkeys(products)) or desc_text[:700] or "Farm products; see source profile",
        "business_types": "LocalHarvest Family Farm", "website_url": website, "facebook_url": facebook,
        "instagram_url": instagram, "on_farm_sales": True,
        "notes": f"Discovered through {card['searched_county']} County seat search ({card['search_url']}). "
                 + (f"Listing last updated {clean_text(updated.group(1))}. " if updated else "Update date not exposed. ") + desc_text[:1200],
    })
    return Observation(**row)


def texas_local_food_observation(profile: dict[str, Any], valid_counties: set[str]) -> Observation:
    meta = profile.get("meta") or {}
    name = clean_text(profile.get("title"))
    primary_slug = clean_text((profile.get("primary_type") or {}).get("slug"))
    website, facebook, instagram, tiktok = split_links(first_value(meta, "links"))
    website = usable_website(website)
    location_terms = term_names(profile, "locations")
    county_candidates = [first_value(meta, "partner-county"), *location_terms]
    county = next((normalized_county(value) for value in county_candidates
                   if normalized_county(value) in valid_counties), "")
    products = term_names(profile, "products")
    if not products:
        products = [first_value(meta, "products-sold") or first_value(meta, "products")]
    about = first_value(meta, "about")
    row = empty_observation("Texas Center for Local Food — Farms & Ranches",
                            str(profile.get("id")), name, clean_text(profile.get("url")), 2, "D")
    row.update({
        "entity_type_source": "; ".join(term_names(profile, "type")),
        "entity_type_review": ("mixed_directory_type_requires_farm_operation_review"
                               if primary_slug in {"distributor", "community-garden"}
                               else "farm_activity_confirmed_by_statewide_local_food_directory"),
        "county": normalized_county(county), "county_source": clean_text(profile.get("url")),
        "city": normalized_city(first_value(meta, "partner-address-city") or clean_text(profile.get("location"))),
        "postal_code": first_value(meta, "partner-address-zip")[:10], "address": first_value(meta, "partner-address-1"),
        "latitude": float(first_value(meta, "latitude")) if first_value(meta, "latitude") else None,
        "longitude": float(first_value(meta, "longitude")) if first_value(meta, "longitude") else None,
        "location_precision": "directory_public_business_address" if first_value(meta, "partner-address-1") else "city_or_county",
        "contact_name": first_value(meta, "contact-name"), "phone": first_value(meta, "contact-phone"),
        "email": first_value(meta, "contact-email"), "products": "; ".join(value for value in products if value),
        "business_types": "; ".join(term_names(profile, "type")), "website_url": website,
        "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
        "on_farm_sales": first_value(meta, "has-storefront").casefold() == "yes",
        "farmers_market_sales": "market" in first_value(meta, "what-sales-outlets-do-you-use").casefold(),
        "online_sales": any(x in (website + " " + first_value(meta, "what-sales-outlets-do-you-use")).casefold() for x in ["online", "shop"]),
        "u_pick": bool(first_value(meta, "agritourism-activities")), "farm_to_school": bool(term_names(profile, "f2s-interest")),
        "notes": about[:1500],
    })
    return Observation(**row)


def eatwild_observations(body: str) -> list[Observation]:
    root = dom(body)
    records = []
    for node in root.descendants("p"):
        if not node.has_class("bodyMargin"):
            continue
        text = node.text()
        match = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40})\s*,?\s*(?:TX|Texas)\s+(\d{5})\b", text)
        if not match:
            continue
        prefix = text[:match.start()].split("| |")[-1].strip(" ,|")
        name = prefix.split(",", 1)[0].strip()
        if len(name) < 3 or len(name) > 100:
            continue
        address_match = re.search(r"(\d{1,6}\s+[^,]{2,90}),\s*$", prefix)
        phone_match = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-./ ]\d{3}[-./ ]\d{4}(?!\d)", text[match.end():])
        website, facebook, instagram, email = link_values(node)
        website = usable_website(website)
        row = empty_observation("EatWild Texas directory", str(len(records) + 1), name, EATWILD_URL, 2, "D")
        row.update({
            "entity_type_source": "Pastured-product farm", "entity_type_review": "farm_activity_confirmed_by_directory",
            "city": match.group(1).title(), "postal_code": match.group(2),
            "address": address_match.group(1) if address_match else "", "location_precision": "public_directory_address_or_city",
            "phone": phone_match.group(0) if phone_match else "", "email": email,
            "products": "Pastured livestock and/or farm products; see source profile",
            "business_types": "Pastured-product farm; direct sales", "website_url": website,
            "facebook_url": facebook, "instagram_url": instagram, "on_farm_sales": True,
            "notes": text[:1200],
        })
        records.append(Observation(**row))
    return records


def pyo_observations(body: str, region: str, url: str) -> tuple[list[Observation], list[str]]:
    root = dom(body)
    active = False
    closed_section = False
    county = ""
    records: list[Observation] = []
    searched_counties: list[str] = []

    def walk(node: Any) -> None:
        nonlocal active, closed_section, county
        if node.tag == "h2" and "U-Pick Farms and Orchards" in node.text():
            active = True
        elif active and node.tag == "h3":
            heading = node.text()
            if heading.startswith("ZZZ -"):
                closed_section = True; county = ""
            elif heading.lower().endswith(" county") and not closed_section:
                county = normalized_county(heading)
                if county not in searched_counties: searched_counties.append(county)
            elif not heading.lower().endswith(" county"):
                county = ""
        elif active and county and not closed_section and node.tag in {"li", "p"}:
            farm_node = first_descendant(node, lambda item: item.has_class("farm"))
            if not farm_node:
                farm_node = next((item for item in node.children if hasattr(item, "tag") and item.tag in {"b", "strong"}), None)
            name = farm_node.text().strip(" -:") if farm_node else ""
            text = node.text()
            if name and len(name) <= 110 and re.search(rf"^{re.escape(name)}\b|\b{re.escape(name)}\s*-", text, re.I):
                closed = bool(re.search(r"permanently closed|assumed permanently closed|ceased operation", text, re.I))
                city_zip = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40}),\s*(?:TX|Texas)\s+(\d{5})\b", text)
                address_match = re.search(r"(?:^|\s)(\d{1,6}\s+[^|]{2,90}?),\s*[A-Za-z][A-Za-z .'-]{1,40},\s*(?:TX|Texas)\s+\d{5}", text)
                phone_match = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-./ ]\d{3}[-./ ]\d{4}(?!\d)", text)
                website, facebook, instagram, email = link_values(node)
                website = usable_website(website)
                product_match = re.search(rf"{re.escape(name)}\s*-\s*(.{{1,260}}?)(?:\b\d{{1,6}}\s+|Phone:|Email:|Open:)", text, re.I)
                products = clean_text(product_match.group(1)) if product_match else "U-pick crops; agritourism"
                row = empty_observation(f"PickYourOwn — {region}", str(len(records) + 1), name, url, 3, "F" if closed else "E")
                row.update({
                    "entity_type_source": "U-pick operation", "entity_type_review": "farm_activity_confirmed_by_directory",
                    "county": county, "county_source": url, "city": city_zip.group(1).title() if city_zip else "",
                    "postal_code": city_zip.group(2) if city_zip else "", "address": clean_text(address_match.group(1)) if address_match else "",
                    "location_precision": "public_directory_address" if address_match else "county", "phone": phone_match.group(0) if phone_match else "",
                    "email": email, "products": products, "business_types": "U-pick; agritourism",
                    "website_url": website, "facebook_url": facebook, "instagram_url": instagram,
                    "on_farm_sales": True, "u_pick": True,
                    "promotion_status": "excluded_explicitly_closed" if closed else "staged_pending_corrob",
                    "notes": text[:1400],
                })
                records.append(Observation(**row)); return
        for child in node.children:
            if hasattr(child, "tag"): walk(child)

    walk(root)
    return records, searched_counties


def census_county_list(body: str) -> list[dict[str, str]]:
    payload = json.loads(body)
    return [feature.get("attributes", {}) for feature in payload.get("features", [])]


def census_address_county(item: Observation) -> tuple[str, str, str, dict[str, Any]]:
    one_line = ", ".join(value for value in [item.address, item.city, "TX", item.postal_code] if clean_text(value))
    params = {"address": one_line, "benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json"}
    url = CENSUS_GEOCODER_URL + "?" + urllib.parse.urlencode(params)
    body, log = fetch(url)
    county = fips = ""
    error = log.get("error", "")
    if body:
        try:
            matches = json.loads(body).get("result", {}).get("addressMatches", [])
            counties = matches[0].get("geographies", {}).get("Counties", []) if matches else []
            if counties and counties[0].get("STATE") == "48":
                county = normalized_county(counties[0].get("NAME", "")); fips = "48" + counties[0].get("COUNTY", "")
            else: error = "No Texas Census address match returned"
        except (json.JSONDecodeError, TypeError, IndexError) as exc: error = f"Invalid Census response: {exc}"
    log.update({"pass": item.source_pass, "source_name": "U.S. Census Geocoder", "records_parsed": int(bool(county)),
                "retrieved_at": now_iso(), "error": error, "source_decision": "county_enrichment",
                "observation_id": item.observation_id})
    return county, fips, url, log


def old_county_cache() -> dict[str, tuple[str, str, str]]:
    path = OUTPUT_DIR / "observations.csv"
    if not path.exists(): return {}
    try:
        with path.open(newline="", encoding="utf-8") as handle: rows = list(csv.DictReader(handle))
    except (csv.Error, OSError): return {}
    return {row.get("observation_id", ""): (row.get("county", ""), row.get("county_fips", ""), row.get("county_source", ""))
            for row in rows if row.get("county") and row.get("county") != "Unknown"}


def read_current_public_names() -> dict[str, str]:
    if not PUBLIC_FARMS.exists(): return {}
    return {normalized_name(row.get("name", "")): clean_text(row.get("name"))
            for row in json.loads(PUBLIC_FARMS.read_text(encoding="utf-8"))}


def choose(items: list[Observation], field: str) -> Any:
    ordered = sorted(items, key=lambda x: (GRADE_RANK.get(x.evidence_grade, 9), -len(clean_text(getattr(x, field)))))
    return next((getattr(x, field) for x in ordered if getattr(x, field) not in {None, ""}), "")


def choose_county(items: list[Observation]) -> str:
    def rank(item: Observation) -> tuple[int, int, str]:
        source = clean_text(item.county_source)
        po_box = bool(re.search(r"\bP\.?\s*O\.?\s*Box\b", item.address, re.I))
        if source.startswith(CENSUS_GEOCODER_URL) and not po_box:
            quality = 0
        elif source and source != CENSUS_ZCTA_COUNTY_URL and not source.startswith(CENSUS_GEOCODER_URL):
            quality = 1
        elif source == CENSUS_ZCTA_COUNTY_URL:
            quality = 2
        else:
            quality = 3
        return quality, GRADE_RANK.get(item.evidence_grade, 9), item.county
    return next((item.county for item in sorted(items, key=rank) if item.county), "")


def identity_tokens(item: Observation) -> set[str]:
    tokens = {re.sub(r"[^a-z0-9]", "", clean_text(value).casefold())
              for value in [item.phone, item.email, item.website_url, item.facebook_url, item.instagram_url]
              if clean_text(value)}
    if item.address and item.postal_code:
        tokens.add("address" + re.sub(r"[^a-z0-9]", "", f"{item.address}{item.postal_code}".casefold()))
    return tokens


def unique_values(items: list[Observation], field: str) -> str:
    values = []
    for item in items:
        for value in clean_text(getattr(item, field)).split(";"):
            value = value.strip()
            if value and value not in values: values.append(value)
    return "; ".join(values)


def reconcile(observations: list[Observation], excluded_candidate_keys: set[str] | None = None
              ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    excluded_candidate_keys = excluded_candidate_keys or set()
    grouped: defaultdict[str, list[Observation]] = defaultdict(list)
    for item in observations:
        if item.candidate_key: grouped[item.candidate_key].append(item)
    entities = []; reviews = []; qa = []
    for key, all_items in sorted(grouped.items()):
        if key in excluded_candidate_keys:
            continue
        known = sorted({x.county for x in all_items if x.county})
        conflict = len(known) > 1
        shared = any(identity_tokens(a) & identity_tokens(b) for i, a in enumerate(all_items) for b in all_items[i + 1:]
                     if a.county and b.county and a.county != b.county)
        cities = [x.city.casefold().strip() for x in all_items if x.city]
        same_city = len(cities) >= 2 and len(set(cities)) == 1
        merge_cross = conflict and (shared or same_city)
        county_groups: defaultdict[str, list[Observation]] = defaultdict(list)
        if conflict and not merge_cross:
            for item in all_items: county_groups[item.county or f"unknown-{item.observation_id}"].append(item)
        else:
            preferred = clean_text(choose_county([x for x in all_items if x.county]))
            county_groups[preferred or "unknown"].extend(all_items)
        if len(all_items) > 1:
            reviews.append({"candidate_key": key, "observation_count": len(all_items),
                            "farm_names": " | ".join(dict.fromkeys(x.farm_name for x in all_items)),
                            "source_names": " | ".join(dict.fromkeys(x.source_name for x in all_items)),
                            "cities": " | ".join(dict.fromkeys(x.city for x in all_items if x.city)), "counties": " | ".join(known),
                            "review_status": "merged_cross_county_shared_identity_preferred_geography" if merge_cross else
                                             "split_county_conflict_no_merge" if conflict else "merged_exact_name_single_geography",
                            "observation_ids": " | ".join(x.observation_id for x in all_items)})
        for group_county, items in county_groups.items():
            active = [x for x in items if x.evidence_grade != "F"]
            if not active: continue
            county = "" if group_county.casefold().startswith("unknown") else group_county
            name = choose(active, "farm_name")
            grades = sorted(set(x.evidence_grade for x in items), key=lambda x: GRADE_RANK[x])
            city = choose(active, "city"); products = unique_values(active, "products")
            go_texan_only = all(x.entity_type_review == "official_directory_farm_ranch_claim" for x in active)
            unconfirmed_member_or_vendor = all("requires_farm_operation_review" in x.entity_type_review for x in active)
            blockers = []
            if conflict and not merge_cross: blockers.append("same normalized name appears in multiple counties")
            if not county: blockers.append("county missing")
            if not city: blockers.append("city or safe public service area missing")
            if not products: blockers.append("products or farm activity missing")
            if grades == ["E"]: blockers.append("single grade-E discovery listing needs corroboration")
            if unconfirmed_member_or_vendor: blockers.append("member/vendor directory candidate needs independent farm-operation evidence")
            if go_texan_only and re.search(r"coffee|candy|restaurant|bakery|brew|distill|sauce|seasoning|retail|market$", name, re.I):
                blockers.append("official Farm And Ranch category conflicts with business-name entity signals")
            entity_id = "TX-" + hashlib.sha256(f"{key}|{county}|{items[0].observation_id if conflict else ''}".encode()).hexdigest()[:10].upper()
            website_url, facebook_url, instagram_url, tiktok_url = classify_public_urls(
                choose(active, "website_url"), choose(active, "facebook_url"),
                choose(active, "instagram_url"), choose(active, "tiktok_url"),
            )
            disposition = classify_candidate(name, blockers)
            entity = {
                "entity_id": entity_id, "farm_name": name, "normalized_name": key,
                "entity_type": "producer_requires_type_review" if unconfirmed_member_or_vendor else "farm",
                "identity_decision": "merged_cross_county_identity_reviewed" if merge_cross else
                                     "split_due_county_conflict" if conflict else "merged_exact_name_reviewed" if len(items) > 1 else "unique_source_name_reviewed",
                "state": "TX", "county": county, "city": city, "postal_code": choose(active, "postal_code"),
                "address_internal": choose(active, "address"), "public_location_classification": "public_business_address_reviewed_for_future_reduced_precision",
                "latitude": choose(active, "latitude"), "longitude": choose(active, "longitude"), "products": products,
                "business_types": unique_values(active, "business_types"), "phone_internal": choose(active, "phone"),
                "email_internal": choose(active, "email"), "contact_visibility": "internal_until_public_use_review",
                "website_url": website_url, "facebook_url": facebook_url,
                "instagram_url": instagram_url, "tiktok_url": tiktok_url,
                "on_farm_sales": any(x.on_farm_sales is True for x in active), "farmers_market_sales": any(x.farmers_market_sales is True for x in active),
                "online_sales": any(x.online_sales is True for x in active), "local_delivery": any(x.local_delivery is True for x in active),
                "u_pick": any(x.u_pick is True for x in active), "wholesale": any(x.wholesale is True for x in active),
                "farm_to_school": any(x.farm_to_school is True for x in active), "source_observation_count": len(items),
                "source_observation_ids": " | ".join(x.observation_id for x in items),
                "source_names": " | ".join(dict.fromkeys(x.source_name for x in items)),
                "source_urls": " | ".join(dict.fromkeys(x.source_url for x in items)), "evidence_grades": "; ".join(grades),
                "last_retrieved": TODAY, "promotion_status": disposition.status,
                "promotion_blockers": "; ".join(blockers),
                "notes": "Fields selected by evidence grade; all underlying observations remain separately auditable.",
            }
            entities.append(entity)
            if blockers:
                qa.append({"entity_id": entity_id, "farm_name": name, "county": county, "issue_type": "promotion_blocker",
                           "issue_detail": "; ".join(blockers),
                           "recommended_action": "Verify with a farm-owned or current official source; do not publish until resolved.", "status": "open"})
    entities.sort(key=lambda x: (x["county"], x["farm_name"].casefold(), x["entity_id"]))
    return entities, reviews, qa


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8"); return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), extrasaction="ignore")
        writer.writeheader(); writer.writerows(records)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    logs = []; raw_sources: dict[str, Any] = {}; observations: list[Observation] = []; critical = []

    county_body, log = fetch(USDA_COUNTIES_URL)
    try: county_rows = census_county_list(county_body) if county_body else []
    except (ValueError, json.JSONDecodeError) as exc: county_rows, log["error"] = [], str(exc)
    counties = [normalized_county(row["NAME"]) for row in county_rows]
    county_fips = {normalized_county(row["NAME"]): row["GEOID"] for row in county_rows}
    logs.append(source_log_entry(log, 1, "U.S. Census Bureau — Texas county denominator", len(county_rows), "coverage_denominator"))
    raw_sources["texas_counties"] = county_rows

    zcta_body, log = fetch(CENSUS_ZCTA_COUNTY_URL)
    try: zcta_map, zcta_rows = single_county_zcta_map(zcta_body) if zcta_body else ({}, [])
    except (ValueError, csv.Error) as exc: zcta_map, zcta_rows, log["error"] = {}, [], str(exc)
    logs.append(source_log_entry(log, 3, "U.S. Census Bureau — 2020 ZCTA-to-county relationship",
                                 len(zcta_rows), "geography_enrichment_reference",
                                 f"Only {len(zcta_map)} Texas ZCTAs wholly contained in one county are eligible for fallback assignment."))
    raw_sources["texas_zcta_county_relationships"] = zcta_rows

    place_body, log = fetch(CENSUS_PLACE_COUNTY_URL)
    try: place_map, place_rows = single_county_place_map(place_body) if place_body else ({}, [])
    except (ValueError, csv.Error) as exc: place_map, place_rows, log["error"] = {}, [], str(exc)
    logs.append(source_log_entry(log, 3, "U.S. Census Bureau — 2020 place-by-county reference",
                                 len(place_rows), "geography_enrichment_reference",
                                 f"Only {len(place_map)} Texas places occurring in one county are eligible for locality fallback assignment."))
    raw_sources["texas_place_by_county"] = place_rows

    body, log = fetch(GO_TEXAN_FARM_CSV_URL)
    try: go_texan, go_raw = go_texan_observations(body) if body else ([], [])
    except Exception as exc: go_texan, go_raw, log["error"] = [], [], f"CSV parse failed: {exc}"
    logs.append(source_log_entry(log, 1, "Texas Department of Agriculture — GO TEXAN Farm And Ranch", len(go_texan)))
    raw_sources["go_texan_farm_and_ranch"] = go_raw; observations.extend(go_texan)

    body, log = fetch(TDA_MARKETS_URL)
    market_markers = len(re.findall(r"farmers market", body, re.I)) if body else 0
    logs.append(source_log_entry(log, 1, "Texas Department of Agriculture — 2026 Certified Farmers Markets", market_markers,
                                 "channel_infrastructure_only_not_farm_observations",
                                 "Certified market map reviewed; markets are channels, not farm entities."))
    raw_sources["tda_certified_markets_evaluation"] = {"farmers_market_text_markers": market_markers, "accepted_farm_observations": 0}

    pdf_raw, log = fetch_bytes(FARM_TO_SCHOOL_URL)
    try: fts_raw = farm_to_school_records(pdf_raw) if pdf_raw else []
    except (OSError, subprocess.SubprocessError) as exc: fts_raw, log["error"] = [], f"PDF extraction failed: {exc}"
    fts = farm_to_school_observations(fts_raw)
    logs.append(source_log_entry(log, 1, "Texas Department of Agriculture — Farm to School vendor resource list", len(fts),
                                 note=f"{len(fts_raw)} parsed vendors; distributors retained only in raw evidence, not as farm observations."))
    raw_sources["farm_to_school_vendor_resource"] = fts_raw; observations.extend(fts)

    body, log = fetch(TEXAS_LOCAL_FOOD_CONTENT)
    try:
        content = json.loads(body).get("content", []) if body else []
        farm_summaries = [x for x in content if any(t.get("slug") == "farms-ranches" for t in ((x.get("terms") or {}).get("type") or []))]
    except (json.JSONDecodeError, TypeError) as exc: content, farm_summaries, log["error"] = [], [], str(exc)
    profiles = []; profile_failures = []; profile_request_logs = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, TEXAS_LOCAL_FOOD_PROFILE.format(id=x["id"])): x for x in farm_summaries}
        for future in as_completed(futures):
            item = futures[future]
            try: profile_body, profile_log = future.result()
            except Exception as exc: profile_body, profile_log = "", {"error": str(exc), "attempts_used": 0}
            if profile_body:
                try: profiles.append(json.loads(profile_body))
                except json.JSONDecodeError as exc: profile_failures.append({"id": item["id"], "error": str(exc)})
            else: profile_failures.append({"id": item["id"], "error": profile_log.get("error", "empty response")})
            profile_log.update({"pass": 2, "source_name": "Texas Center for Local Food — profile request",
                                "records_parsed": int(bool(profile_body)), "retrieved_at": now_iso(),
                                "source_decision": "request_component", "source_record_id": str(item["id"])})
            profile_request_logs.append(profile_log)
    if profile_failures: log["error"] = f"{len(profile_failures)} individual profiles failed after retry policy"
    tlf = [texas_local_food_observation(x, set(counties)) for x in profiles]
    logs.append(source_log_entry(log, 2, "Texas Center for Local Food — Farms & Ranches", len(tlf),
                                 note=f"{len(farm_summaries)} farm-tagged summaries; {len(profiles)} detailed profiles; {len(profile_failures)} failures."))
    raw_sources["texas_local_food_profiles"] = profiles; raw_sources["texas_local_food_profile_failures"] = profile_failures
    logs.extend(profile_request_logs); observations.extend(tlf)

    body, log = fetch(EATWILD_URL)
    eatwild = eatwild_observations(body) if body else []
    logs.append(source_log_entry(log, 2, "EatWild Texas directory", len(eatwild)))
    raw_sources["eatwild_texas"] = [asdict(x) for x in eatwild]; observations.extend(eatwild)

    shop_pages = []
    for page_number in (1, 2, 3):
        url = SHOP_TEXAS_URL + ("" if page_number == 1 else f"?frm-page-1138={page_number}")
        page_body, page_log = fetch(url)
        shop_pages.append(page_body)
        page_log.update({"pass": 2, "source_name": "Shop Texas Farms — directory page request",
                         "records_parsed": len(re.findall(r"business-directory/entry/", page_body)),
                         "retrieved_at": now_iso(), "source_decision": "request_component", "page": page_number})
        logs.append(page_log)
    shop_cards = shop_texas_cards(shop_pages); shop_profiles = []; shop_failures = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, card["url"]): card for card in shop_cards}
        for future in as_completed(futures):
            card = futures[future]
            try: profile_body, request_log = future.result()
            except Exception as exc: profile_body, request_log = "", {"error": str(exc), "attempts_used": 0}
            request_log.update({"pass": 2, "source_name": "Shop Texas Farms — profile request",
                                "records_parsed": int(bool(profile_body)), "retrieved_at": now_iso(),
                                "source_decision": "request_component", "source_record_id": card["url"]})
            logs.append(request_log)
            if profile_body: shop_profiles.append(shop_texas_observation(card, profile_body))
            else: shop_failures.append({"url": card["url"], "error": request_log.get("error", "empty response")})
    logs.append({"url": SHOP_TEXAS_URL, "attempts_used": 1, "http_status": 200, "bytes": sum(len(x) for x in shop_pages),
                 "sha256": "", "elapsed_seconds": 0, "error": "" if not shop_failures else f"{len(shop_failures)} profile requests failed",
                 "pass": 2, "source_name": "Shop Texas Farms — member business directory", "records_parsed": len(shop_profiles),
                 "retrieved_at": now_iso(), "source_decision": "observations_retained",
                 "note": f"{len(shop_cards)} unique member profiles found across all three directory pages; business-type review remains explicit."})
    raw_sources["shop_texas_farms_profiles"] = [asdict(x) for x in shop_profiles]
    raw_sources["shop_texas_farms_failures"] = shop_failures; observations.extend(shop_profiles)

    body, log = fetch(PYO_INDEX_URL)
    logs.append(source_log_entry(log, 3, "PickYourOwn — Texas regional index", 13, "regional_coverage_index",
                                 "All 13 published Texas regions were collected separately."))
    pyo_searched: set[str] = set()
    for region, url in PYO_URLS.items():
        body, log = fetch(url)
        records, searched = pyo_observations(body, region, url) if body else ([], [])
        pyo_searched.update(searched); observations.extend(records)
        logs.append(source_log_entry(log, 3, f"PickYourOwn — {region}", len(records),
                                     note=f"County sections searched: {len(searched)}; explicit closures retained as grade-F exclusions."))
        raw_sources[f"pickyourown_{normalized_name(region).replace(' ', '_')}"] = [asdict(x) for x in records]

    seats_body, log = fetch(TSL_COUNTY_SEATS_URL)
    seats = county_seat_pairs(seats_body) if seats_body else []
    logs.append(source_log_entry(log, 3, "Texas State Library — county-seat search anchors", len(seats), "coverage_search_anchors"))
    local_cards: dict[str, dict[str, str]] = {}; seat_search_failures = []; seat_request_logs = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {}
        for county, seat in seats:
            search_url = f"{LOCALHARVEST_BASE}/{slug(seat)}-tx/farms"
            futures[executor.submit(fetch, search_url)] = (county, seat, search_url)
        for future in as_completed(futures):
            county, seat, search_url = futures[future]
            try: search_body, request_log = future.result()
            except Exception as exc: search_body, request_log = "", {"error": str(exc), "attempts_used": 0}
            cards = localharvest_cards(search_body, county, search_url) if search_body else []
            request_log.update({"pass": 3, "source_name": "LocalHarvest — county-seat search request",
                                "records_parsed": len(cards), "retrieved_at": now_iso(),
                                "source_decision": "request_component", "county": county, "county_seat": seat})
            seat_request_logs.append(request_log)
            if request_log.get("error"): seat_search_failures.append({"county": county, "seat": seat, "error": request_log["error"]})
            for card in cards:
                previous = local_cards.get(card["url"])
                if not previous or previous["searched_county"] != county: local_cards.setdefault(card["url"], card)
    logs.extend(seat_request_logs)
    local_profiles = []; local_profile_failures = []; local_profile_logs = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(fetch, card["url"]): card for card in local_cards.values()}
        for future in as_completed(futures):
            card = futures[future]
            try: profile_body, request_log = future.result()
            except Exception as exc: profile_body, request_log = "", {"error": str(exc), "attempts_used": 0}
            request_log.update({"pass": 3, "source_name": "LocalHarvest — farm profile request",
                                "records_parsed": int(bool(profile_body)), "retrieved_at": now_iso(),
                                "source_decision": "request_component", "source_record_id": card["url"]})
            local_profile_logs.append(request_log)
            if profile_body: local_profiles.append(localharvest_observation(card, profile_body))
            else: local_profile_failures.append({"url": card["url"], "error": request_log.get("error", "empty response")})
    logs.extend(local_profile_logs)
    logs.append({"url": LOCALHARVEST_BASE, "attempts_used": 1, "http_status": 200, "bytes": 0, "sha256": "",
                 "elapsed_seconds": 0, "error": "" if not seat_search_failures and not local_profile_failures else
                 f"{len(seat_search_failures)} county searches and {len(local_profile_failures)} profiles failed after retry policy",
                 "pass": 3, "source_name": "LocalHarvest — Texas county-seat gap search", "records_parsed": len(local_profiles),
                 "retrieved_at": now_iso(), "source_decision": "observations_retained",
                 "note": f"All {len(seats)} official county seats searched; {sum(x.get('records_parsed', 0) for x in seat_request_logs)} card observations deduplicated to {len(local_cards)} farm profiles."})
    raw_sources["localharvest_county_seat_search_failures"] = seat_search_failures
    raw_sources["localharvest_profile_failures"] = local_profile_failures
    raw_sources["localharvest_profiles"] = [asdict(x) for x in local_profiles]; observations.extend(local_profiles)

    body, log = fetch(USDA_DIRECTORY_URL)
    logs.append(source_log_entry(log, 3, "USDA AMS Local Food Directories", 0, "evaluated_interface_no_public_bulk_api",
                                 "Official page says a developer API will be available in the future; interface reviewed but not scraped as a hidden data service."))
    raw_sources["usda_local_food_directory_evaluation"] = {"accepted": 0, "reason": "No published bulk/API contract as of retrieval date."}

    body, log = fetch(US_FARM_TRAIL_URL)
    links = len(re.findall(r"/farms/[^\" ]+", body)) if body else 0
    logs.append(source_log_entry(log, 3, "US Farm Trail — Texas discovery page", 0, "evaluated_rejected_as_entity_source",
                                 f"{links} rendered farm-link occurrences; source mixes markets, duplicates, and weak-provenance records."))
    raw_sources["us_farm_trail_evaluation"] = {"rendered_farm_link_occurrences": links, "accepted": 0}

    body, log = fetch(YOU_PICK_TEXAS_URL)
    logs.append(source_log_entry(log, 3, "Texas Open Farms / YouPickTexas", 0, "evaluated_rejected_as_entity_source",
                                 "Directory displayed a fictitious 555 contact number and unsupported network branding; retained as an issue, not evidence."))
    raw_sources["youpicktexas_evaluation"] = {"accepted": 0, "reason": "Fictitious 555 contact and unclear provenance."}

    manual_observations, manual_excluded_keys, manual_records = manual_verification_observations()
    observations.extend(manual_observations)
    raw_sources["manual_verification_decisions"] = manual_records
    logs.append({"url": str(MANUAL_VERIFICATION_DECISIONS), "attempts_used": 1, "http_status": 200,
                 "bytes": MANUAL_VERIFICATION_DECISIONS.stat().st_size if MANUAL_VERIFICATION_DECISIONS.exists() else 0,
                 "sha256": hashlib.sha256(MANUAL_VERIFICATION_DECISIONS.read_bytes()).hexdigest()
                           if MANUAL_VERIFICATION_DECISIONS.exists() else "",
                 "elapsed_seconds": 0, "error": "" if MANUAL_VERIFICATION_DECISIONS.exists() else
                 "Manual verification decision file is missing", "pass": 3,
                 "source_name": "FarmFinder curator verification decisions", "records_parsed": len(manual_records),
                 "retrieved_at": now_iso(), "source_decision": "curator_decisions_applied",
                 "note": "Farm-owned or authoritative evidence reviewed manually; original source assertions remain immutable."})

    if len(counties) != 254: critical.append(f"Texas county denominator expected 254, received {len(counties)}")
    primary_logs = [x for x in logs if x.get("source_name") != "U.S. Census Geocoder" and x.get("source_decision") != "request_component"]
    required_sources = {"U.S. Census Bureau — Texas county denominator", "Texas Department of Agriculture — GO TEXAN Farm And Ranch",
                        "Texas Center for Local Food — Farms & Ranches", "PickYourOwn — Texas regional index",
                        "Texas State Library — county-seat search anchors"}
    for entry in primary_logs:
        if entry.get("error") and entry.get("source_name") in required_sources:
            critical.append(f"{entry.get('source_name')}: {entry.get('error')}")
    if len(seats) != 254: critical.append(f"Official county-seat search anchors expected 254, received {len(seats)}")

    cache = old_county_cache(); geocoder_failures = []; geography_conflicts = []
    targets = []
    for item in observations:
        cached = cache.get(item.observation_id)
        # Re-run GO TEXAN geography even when an older cache exists so the
        # official source county can be compared with an exact-address result.
        if cached and cached[0] in county_fips and not item.source_name.startswith("Texas Department of Agriculture — GO TEXAN"):
            item.county, item.county_fips, item.county_source = cached
        elif item.address and item.city and item.postal_code and (not item.county or item.source_name.startswith("Texas Department")):
            targets.append(item)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(census_address_county, item): item for item in targets}
        for future in as_completed(futures):
            item = futures[future]
            try: county, fips, url, lookup_log = future.result()
            except Exception as exc:
                county, fips, url = "", "", ""
                lookup_log = {"source_name": "U.S. Census Geocoder", "error": str(exc), "observation_id": item.observation_id,
                              "pass": item.source_pass, "source_decision": "county_enrichment", "attempts_used": 0, "records_parsed": 0}
            logs.append(lookup_log)
            if county:
                if item.county and item.county != "Unknown" and item.county != county:
                    geography_conflicts.append({"observation_id": item.observation_id, "farm_name": item.farm_name,
                                                "source_county": item.county, "census_county": county,
                                                "decision": "Census exact-address county used; source conflict retained."})
                item.county, item.county_fips, item.county_source = county, fips, url
            else:
                geocoder_failures.append({"observation_id": item.observation_id, "farm_name": item.farm_name,
                                          "address": item.address, "city": item.city, "postal_code": item.postal_code,
                                          "error": lookup_log.get("error", "County not returned")})
    for item in observations:
        # A ZCTA is not a USPS delivery ZIP, so use this fallback only where the
        # Census relationship file shows the entire ZCTA inside one TX county.
        if (not item.county or item.county == "Unknown") and item.postal_code in zcta_map:
            item.county, item.county_fips = zcta_map[item.postal_code]
            item.county_source = CENSUS_ZCTA_COUNTY_URL
            item.location_precision = (item.location_precision + "; " if item.location_precision else "") + "single-county_2020_zcta_inference"
        place_key = normalized_city(item.city).casefold()
        if (not item.county or item.county == "Unknown") and place_key in place_map:
            item.county, item.county_fips = place_map[place_key]
            item.county_source = CENSUS_PLACE_COUNTY_URL
            item.location_precision = (item.location_precision + "; " if item.location_precision else "") + "single-county_2020_census_place_inference"
        if item.county == "Unknown":
            item.county = ""
    geocoder_failure_ids = {row["observation_id"]: row for row in geocoder_failures}
    lookup_errors = []
    for item in observations:
        if (not item.county or item.county == "Unknown") and item.evidence_grade != "F" and \
                not item.promotion_status.startswith("excluded"):
            prior = geocoder_failure_ids.get(item.observation_id, {})
            lookup_errors.append({"observation_id": item.observation_id, "farm_name": item.farm_name,
                                  "address": item.address, "city": item.city, "postal_code": item.postal_code,
                                  "error": prior.get("error", "No exact-address match and no wholly single-county 2020 ZCTA fallback")})
    for item in observations:
        if item.county and not item.county_fips: item.county_fips = county_fips.get(item.county, "")

    current_names = read_current_public_names(); counts = Counter(x.candidate_key for x in observations if x.candidate_key)
    for item in observations:
        if counts[item.candidate_key] > 1: item.identity_review_status = "exact_normalized_name_group_reviewed_by_reconciliation_rules"
        if item.candidate_key in current_names: item.current_release_name_collision = current_names[item.candidate_key]
    observations.sort(key=lambda x: (x.candidate_key, x.source_name, x.source_record_id))
    entities, identity_review, qa = reconcile(observations, manual_excluded_keys)
    eligible = [x for x in entities if x["promotion_status"] == "promotion_eligible_reviewed"]
    entity_counts = Counter(x["county"] for x in entities if x["county"]); eligible_counts = Counter(x["county"] for x in eligible if x["county"])
    pass_counts: Counter[tuple[str, int]] = Counter()
    for item in observations:
        if item.county: pass_counts[(item.county, item.source_pass)] += 1
    coverage = []
    for county in sorted(counties):
        count = entity_counts[county]
        coverage.append({"county": county, "county_fips": county_fips[county],
                         "pass_1_observations": pass_counts[(county, 1)], "pass_2_observations": pass_counts[(county, 2)],
                         "pass_3_observations": pass_counts[(county, 3)], "candidate_entities": count,
                         "promotion_eligible_entities": eligible_counts[county],
                         "status": "candidates_found" if count else "searched_none_found",
                         "coverage_note": "All statewide sources and all 13 published PickYourOwn Texas regions were reviewed; zero means no qualifying public candidate was found under documented sources."})
    missing = [x["county"] for x in coverage if not x["candidate_entities"]]

    observation_records = [asdict(x) for x in observations]
    excluded = [x for x in observation_records if x["evidence_grade"] == "F" or
                x["promotion_status"].startswith("excluded") or x["candidate_key"] in manual_excluded_keys]
    summary = {
        "status": "coverage_reviewed" if not critical else "blocked_validation_errors",
        "release_id": f"tx-coverage-reviewed-{TODAY}", "generated_at": now_iso(),
        "scope": "Texas three-pass private state release; LA/MS canonical and public app remain unchanged.",
        "completion_definition": "All qualifying farms found under documented sources and three-pass process as of release date; not every USDA-defined or undiscoverable farm.",
        "collection_passes_started": [1, 2, 3], "collection_passes_completed": [1, 2, 3] if not critical else [],
        "source_datasets_evaluated": len(primary_logs), "source_observations": len(observations),
        "source_observations_by_source": dict(sorted(Counter(x.source_name for x in observations).items())),
        "excluded_or_grade_f_observations": len(excluded), "proposed_entities": len(entities),
        "manual_verification_decisions": len(manual_records),
        "manual_excluded_entity_groups": len(manual_excluded_keys),
        "promotion_eligible_entities": len(eligible), "research_or_qa_entities": len(entities) - len(eligible),
        "identity_review_groups": len(identity_review),
        "identity_groups_split_for_county_conflict": sum(x["review_status"].startswith("split") for x in identity_review),
        "current_la_ms_name_collisions": sum(bool(x.current_release_name_collision) for x in observations),
        "texas_counties_total": len(counties), "counties_with_candidates": sum(bool(x["candidate_entities"]) for x in coverage),
        "counties_without_candidates": missing, "counties_with_promotion_eligible_entities": sum(bool(x["promotion_eligible_entities"]) for x in coverage),
        "website_entities": sum(bool(x["website_url"]) for x in entities),
        "social_entities": sum(bool(x["facebook_url"] or x["instagram_url"] or x["tiktok_url"]) for x in entities),
        "direct_contact_entities": sum(bool(x["phone_internal"] or x["email_internal"]) for x in entities),
        "source_requests": sum(x.get("source_decision") != "county_enrichment" for x in logs),
        "failed_source_requests": sum(bool(x.get("error")) and x.get("source_decision") != "county_enrichment" for x in logs),
        "geography_enrichment_requests": sum(x.get("source_decision") == "county_enrichment" for x in logs),
        "geography_enrichment_request_failures": len(geocoder_failures),
        "unresolved_county_observations": len(lookup_errors), "county_lookup_failures": len(lookup_errors),
        "source_county_conflicts": len(geography_conflicts),
        "pickyourown_county_sections": len(pyo_searched), "open_qa_items": len(qa), "critical_errors": critical,
        "promotion_note": "Eligible means the staged row meets field/evidence/privacy gates; canonical promotion still requires a deliberate immutable release review.",
    }

    write_csv(OUTPUT_DIR / "observations.csv", observation_records)
    write_csv(OUTPUT_DIR / "entities.csv", entities); write_csv(OUTPUT_DIR / "identity-review.csv", identity_review)
    write_csv(OUTPUT_DIR / "qa-queue.csv", qa); write_csv(OUTPUT_DIR / "county-coverage.csv", coverage)
    write_csv(OUTPUT_DIR / "exclusions.csv", excluded); write_csv(OUTPUT_DIR / "geography-conflicts.csv", geography_conflicts)
    (OUTPUT_DIR / "request-log.json").write_text(json.dumps(logs, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "county-lookup-errors.json").write_text(json.dumps(lookup_errors, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "raw-source-records.json").write_text(json.dumps(raw_sources, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2)); return 0 if summary["status"] == "coverage_reviewed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
