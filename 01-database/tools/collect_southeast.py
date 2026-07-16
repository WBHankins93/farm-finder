#!/usr/bin/env python3
"""Collect Southeast farm candidates through one governed state pipeline.

Source adapters are state-specific because public directories differ, while
retention, reconciliation, geography, QA, evidence, and output rules are shared.
The collector writes detailed evidence only under data/source-releases/work/.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import html
import io
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from collect_alabama import (
    Node,
    Observation,
    clean_text,
    clean_url,
    dom,
    fetch,
    fetch_bytes,
    first_descendant,
    link_values,
    now_iso,
)
from state_policy import classify_candidate
from state_release_urls import classify_public_urls


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_FARMS = ROOT / "03-app" / "site" / "app" / "data" / "farms.json"
TODAY = date.today().isoformat()
LOCALHARVEST_BASE = "https://www.localharvest.org"
FCC_AREA_URL = "https://geo.fcc.gov/api/census/area"
CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
CENSUS_COUNTIES_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query?"
)
CENSUS_PLACE_COUNTY_URL = (
    "https://www2.census.gov/geo/docs/reference/codes2020/national_place_by_county2020.txt"
)
GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

STATE_CONFIG: dict[str, dict[str, Any]] = {
    "LA": {
        "name": "Louisiana",
        "fips": "22",
        "county_count": 64,
        "county_label": "parish",
        "official_fmnp": "https://www.ldaf.la.gov/fmnp",
        "lsu_farm_food_pdf": "https://www.lsuagcenter.com/~/media/system/9/1/9/e/919ed83cfbd8ff0bd98b317a65f0604f/directory%20-%20la%20farm%20food%20during%20covidpdfpdf.pdf",
        "agritourism_pdf": "https://assets.ctfassets.net/pc5e1rlgfrov/7B8yMZqsUPa8lLZSUToUtw/19d3206a6070dea80e63683408b1552e/agritourism-directory-2023.pdf",
        "crawfish_suppliers": "https://crawfish.org/producers",
        "strawberry_growers": "https://www.louisianastrawberries.com/find-louisiana-strawberries/",
        "sweet_potato_shippers": "https://www.sweetpotato.org/shippers",
        "nursery_growers_pdf": "https://assets.ctfassets.net/pc5e1rlgfrov/6bRblalD03I36YRFk7xtGP/a3c8fc82041cb934b92123a77c11cf9a/Hort_Nursery_Certificate_List.pdf",
        "hemp_growers_pdf": "https://assets.ctfassets.net/pc5e1rlgfrov/3th6qHxDCGxZ3AtLR9rr5A/1001d3efbe240465b2bb67276f3fc2bf/Hemp_grower_List20260309.pdf",
        "apiary_register_pdf": "https://assets.ctfassets.net/pc5e1rlgfrov/7muuQp3Pj6scacLq7VhlHK/0af35d52af4d67654efe11e87bfbde7d/Hort_Apiary_List.pdf",
        "eatwild": "https://www.eatwild.com/products/louisiana.html",
        "pyo_index": "https://www.pickyourown.org/LA.htm",
        "pyo_discover_regions": True,
        "census_place_gap_search": True,
        "census_place_full_search": True,
        "report_passes": [
            "the 2026 LDAF Farmers' Market Nutrition Program roadside-stand directory and the LSU AgCenter statewide farm-food directory",
            "the LDAF certified agritourism directory and EatWild",
            "the live PickYourOwn region index plus targeted LocalHarvest parish-gap searches",
        ],
    },
    "MS": {
        "name": "Mississippi",
        "fips": "28",
        "county_count": 82,
        "county_label": "county",
        "genuine_archives": {
            "Genuine MS — Grown": "https://genuinems.com/members/grown/",
            "Genuine MS — Raised": "https://genuinems.com/members/raised/",
        },
        "mdac_vendor_list": "https://agnet.mdac.ms.gov/Website/vendorlist",
        "mdac_marketplace": "https://agnet.mdac.ms.gov/MarketPortal/MarketPortal",
        "mdac_agritourism": "https://agnet.mdac.ms.gov/website/AgTourism/Venues",
        "christmas_tree_farms": "https://mschristmastrees.com/locations/",
        "certified_nurseries_pdf": "https://agnet.mdac.ms.gov/agManage/uploads/1415.pdf",
        "eatwild": "https://www.eatwild.com/products/mississippi.html",
        "pyo_index": "https://www.pickyourown.org/MS.htm",
        "pyo_regions": {
            "North Mississippi": "https://www.pickyourown.org/MSnorth.htm",
            "Jackson and west-central Mississippi": "https://www.pickyourown.org/MSjackson.htm",
            "East-central Mississippi": "https://www.pickyourown.org/MSeast.htm",
            "Southeast Mississippi": "https://www.pickyourown.org/MSse.htm",
            "Southwest Mississippi": "https://www.pickyourown.org/MSsw.htm",
        },
        "census_place_gap_search": True,
        "census_place_full_search": True,
        "report_passes": [
            "Genuine MS Grown and Raised archives with current producer profiles",
            "MDAC farmers-market vendors, Farm Marketplace, agritourism venues, and EatWild",
            "all five PickYourOwn regions plus targeted LocalHarvest county-gap searches",
        ],
    },
    "AR": {
        "name": "Arkansas",
        "fips": "05",
        "county_count": 75,
        "official_directory": "https://arkansasgrown.org/arkansas-grown/members/?category=arkansas-grown&sort=latest",
        "official_root": "https://arkansasgrown.org",
        "extension_farms": "https://farmandfoodsystem.uada.edu/farms/",
        "eatwild": "https://www.eatwild.com/products/arkansas.html",
        "pyo_index": "https://www.pickyourown.org/AR.htm",
        "pyo_regions": {
            "Central Arkansas": "https://www.pickyourown.org/ARlittlerock.htm",
            "Southwest Arkansas": "https://www.pickyourown.org/ARsw.htm",
            "Southeast Arkansas": "https://www.pickyourown.org/ARse.htm",
            "Northwest Arkansas": "https://www.pickyourown.org/ARnw.htm",
            "Northeast Arkansas": "https://www.pickyourown.org/ARne.htm",
        },
        "county_seats": "https://www.arcounties.org/site/assets/files/3779/countyseats.pdf",
        "report_passes": [
            "the Arkansas Department of Agriculture Arkansas Grown directory",
            "University of Arkansas direct-sale farms and EatWild",
            "five PickYourOwn regions plus LocalHarvest searches anchored to all county seats",
        ],
    },
    "TN": {
        "name": "Tennessee",
        "fips": "47",
        "county_count": 95,
        "official_directory": "https://www.picktnproducts.org/members/search-for-a-member.html",
        "official_root": "https://www.picktnproducts.org",
        "official_aggregate_name": "Tennessee Department of Agriculture — Pick Tennessee Products directory",
        "century_farms": "https://www.tncenturyfarms.org/farms/",
        "agritourism": "https://tennesseeagritourism.org/find-a-farm",
        "eatwild": "https://www.eatwild.com/products/tennessee.html",
        "pyo_index": "https://www.pickyourown.org/TN.htm",
        "pyo_regions": {
            "Clarksville area": "https://www.pickyourown.org/TNclarksville.htm",
            "Columbia area": "https://www.pickyourown.org/TNcolumbia.htm",
            "Eastern Tennessee": "https://www.pickyourown.org/TNeast.htm",
            "Knoxville area": "https://www.pickyourown.org/TNknoxville.htm",
            "Middle Tennessee": "https://www.pickyourown.org/TNmiddle.htm",
            "North-central Tennessee": "https://www.pickyourown.org/TNnc.htm",
            "Northeastern Tennessee": "https://www.pickyourown.org/TNne.htm",
            "Northwestern Tennessee": "https://www.pickyourown.org/TNnw.htm",
            "Southwestern-central Tennessee": "https://www.pickyourown.org/TNswc.htm",
            "Western Tennessee": "https://www.pickyourown.org/TNwest.htm",
        },
        "report_passes": [
            "the Tennessee Department of Agriculture Pick Tennessee Products directory",
            "Tennessee Century Farms, Tennessee Agritourism, and EatWild",
            "ten PickYourOwn regions",
        ],
    },
    "GA": {
        "name": "Georgia",
        "fips": "13",
        "county_count": 159,
        "official_directory": "https://georgiagrown.com/membership/member-directory/",
        "official_root": "https://georgiagrown.com",
        "official_aggregate_name": "Georgia Department of Agriculture — Georgia Grown member directory",
        "farm_markets": "https://www.gfb.org/connect/farm-markets/tag/All%20CFMs",
        "eatwild": "https://www.eatwild.com/products/georgia.html",
        "pyo_index": "https://www.pickyourown.org/GA.htm",
        "pyo_regions": {
            "North Georgia": "https://www.pickyourown.org/GAnorth.htm",
            "Macon area": "https://www.pickyourown.org/GAmacon.htm",
            "Augusta area": "https://www.pickyourown.org/GAaugusta.htm",
            "Coastal and southeastern Georgia": "https://www.pickyourown.org/GAcoastal.htm",
            "Southwestern Georgia": "https://www.pickyourown.org/GAsouthwest.htm",
        },
        "report_passes": [
            "the Georgia Department of Agriculture Georgia Grown member directory",
            "Georgia Farm Bureau Certified Farm Markets and EatWild",
            "five PickYourOwn regions plus targeted LocalHarvest searches for counties with no retained candidate",
        ],
        "census_place_gap_search": True,
    },
    "FL": {
        "name": "Florida",
        "fips": "12",
        "county_count": 67,
        "official_directory": "https://flfarmtoyou.com/producer/",
        "official_root": "https://flfarmtoyou.com",
        "official_aggregate_name": "Florida Department of Agriculture and Consumer Services — Florida Farm to You producer directory",
        "fdacs_upick": "https://www.fdacs.gov/Consumer-Resources/Buy-Fresh-From-Florida/U-Pick-Farms",
        "fdacs_csa": "https://www.fdacs.gov/Consumer-Resources/Buy-Fresh-From-Florida/Community-Supported-Agriculture-CSAs",
        "us_farm_trail": "https://www.usfarmtrail.com/states/florida",
        "us_farm_trail_geojson": "https://www.usfarmtrail.com/api/v1/farms/geojson?state=florida",
        "eatwild": "https://www.eatwild.com/products/florida.html",
        "pyo_index": "https://www.pickyourown.org/FL.htm",
        "pyo_discover_regions": True,
        "report_passes": [
            "the FDACS-created Florida Farm to You producer directory",
            "FDACS U-pick and CSA lists plus EatWild",
            "US Farm Trail, 39 PickYourOwn regions, and targeted LocalHarvest county-gap searches",
        ],
        "census_place_gap_search": True,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, choices=sorted(STATE_CONFIG))
    return parser.parse_args()


def normalized_name(value: str) -> str:
    value = clean_text(value).casefold().replace("&", " and ").replace("’", "").replace("'", "")
    tokens = re.sub(r"[^a-z0-9]+", " ", value).strip().split()
    while len(tokens) > 2 and tokens[-1] in {"llc", "inc", "incorporated", "company", "co"}:
        tokens.pop()
    return " ".join(tokens)


def canonical_alias_key(value: str) -> str:
    tokens = normalized_name(value).split()
    aliases = {
        "assoc": "association",
        "assn": "association",
        "gardens": "garden",
        "fruits": "fruit",
        "vegetables": "vegetable",
    }
    drop = {"the", "farm", "farms", "llc", "inc", "company", "co", "csa", "stand"}
    return " ".join(aliases.get(token, token) for token in tokens if token not in drop)


def normalized_county(value: str) -> str:
    county = re.sub(r"\s+(?:County|Parish)$", "", clean_text(value), flags=re.I).strip().title()
    if county.startswith("Mc") and len(county) > 2:
        county = "Mc" + county[2].upper() + county[3:]
    return {
        "Dekalb": "DeKalb",
        "Desoto": "DeSoto",
        "Lasalle": "LaSalle",
        "E. Baton Rouge": "East Baton Rouge",
        "E. Feliciana": "East Feliciana",
        "W. Carroll": "West Carroll",
        "W. Feliciana": "West Feliciana",
        "Jeff Davis": "Jefferson Davis",
        "St John The Baptist": "St. John the Baptist",
        "St. John The Baptist": "St. John the Baptist",
    }.get(county, county)


def normalized_city(value: str) -> str:
    return clean_text(value).title()


def sanitized_phone(value: str) -> str:
    phone = clean_text(value)
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7 and not (len(digits) >= 6 and re.search(r"[A-Za-z]", phone)):
        return ""
    local = digits[-10:] if len(digits) >= 10 else digits
    if len(local) == 10 and (local[:3] == "000" or len(set(local)) == 1):
        return ""
    return phone


def sanitized_email(value: str) -> str:
    email_value = clean_text(value).removeprefix("mailto:").strip(".,;:()[]<>")
    return email_value if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email_value) else ""


def strip_tags(value: str) -> str:
    value = html.unescape(value)
    return clean_text(re.sub(r"<[^>]+>", " ", value))


def make_observation_id(state: str, source_name: str, source_record_id: str, farm_name: str) -> str:
    raw = f"{state}|{source_name}|{source_record_id}|{farm_name}".encode()
    return f"{state.lower()}obs_{hashlib.sha256(raw).hexdigest()[:20]}"


def empty_observation(
    state: str,
    source_name: str,
    source_record_id: str,
    farm_name: str,
    source_url: str,
    source_pass: int,
    grade: str,
) -> dict[str, Any]:
    return {
        "observation_id": make_observation_id(state, source_name, source_record_id, farm_name),
        "candidate_key": normalized_name(farm_name),
        "identity_review_status": "source_unique_name",
        "current_release_name_collision": "",
        "farm_name": clean_text(farm_name),
        "entity_type_source": "",
        "entity_type_review": "needs_review",
        "state": state,
        "county": "",
        "county_fips": "",
        "county_source": "",
        "city": "",
        "postal_code": "",
        "address": "",
        "latitude": None,
        "longitude": None,
        "location_precision": "",
        "address_visibility": "internal_source_value",
        "contact_name": "",
        "phone": "",
        "email": "",
        "contact_visibility": "internal_source_value",
        "products": "",
        "business_types": "",
        "website_url": "",
        "facebook_url": "",
        "instagram_url": "",
        "tiktok_url": "",
        "on_farm_sales": None,
        "farmers_market_sales": None,
        "online_sales": None,
        "local_delivery": None,
        "u_pick": None,
        "wholesale": None,
        "farm_to_school": None,
        "retail_sales": None,
        "restaurant_sales": None,
        "hours_or_season": "",
        "source_pass": source_pass,
        "source_name": source_name,
        "source_url": source_url,
        "source_record_id": source_record_id,
        "evidence_grade": grade,
        "retrieved_date": TODAY,
        "promotion_status": "staged_pending_rules",
        "notes": "",
    }


def logged(log: dict[str, Any], pass_number: int, name: str, records: int, decision: str, note: str = "") -> dict[str, Any]:
    return {
        **log,
        "pass": pass_number,
        "source_name": name,
        "records_parsed": records,
        "retrieved_at": now_iso(),
        "source_decision": decision,
        "note": note,
    }


def split_public_links(values: list[str], source_host: str) -> tuple[str, str, str, str]:
    website = facebook = instagram = tiktok = ""
    for raw in values:
        url = clean_url(raw)
        if not url:
            continue
        host = (urllib.parse.urlparse(url).hostname or "").casefold().removeprefix("www.")
        if source_host in host or "google.com" in host:
            continue
        if "facebook.com" in host and not facebook:
            facebook = url
        elif "instagram.com" in host and not instagram:
            instagram = url
        elif "tiktok.com" in host and not tiktok:
            tiktok = url
        elif not website:
            website = url
    return website, facebook, instagram, tiktok


def producer_signal(name: str, description: str, products: str) -> bool:
    text = f"{name} {description} {products}"
    return bool(re.search(
        r"\b(?:farm|farms|ranch|orchard|apiary|beekeeper|vineyard|grower|grown|growing|"
        r"raise|raising|pasture|livestock|cattle|poultry|produce|vegetables?|fruit|berries|"
        r"mushrooms?|eggs?|honey|dairy|goats?|pigs?|pork|beef|flowers?)\b",
        text,
        re.I,
    ))


def parse_local_business(body: str) -> tuple[dict[str, Any], dict[str, Any]]:
    blocks = re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', body, re.I | re.S)
    business: dict[str, Any] = {}
    page: dict[str, Any] = {}
    for raw in blocks:
        try:
            value = json.loads(html.unescape(raw))
        except json.JSONDecodeError:
            continue
        if value.get("@type") == "LocalBusiness":
            business = value
        for item in value.get("@graph", []) if isinstance(value, dict) else []:
            if item.get("@type") == "WebPage":
                page = item
    return business, page


LA_PARISHES = {
    "Acadia", "Allen", "Ascension", "Assumption", "Avoyelles", "Beauregard",
    "Bienville", "Bossier", "Caddo", "Calcasieu", "Caldwell", "Cameron",
    "Catahoula", "Claiborne", "Concordia", "De Soto", "East Baton Rouge",
    "East Carroll", "East Feliciana", "Evangeline", "Franklin", "Grant",
    "Iberia", "Iberville", "Jackson", "Jefferson", "Jefferson Davis",
    "Lafayette", "Lafourche", "LaSalle", "Lincoln", "Livingston", "Madison",
    "Morehouse", "Natchitoches", "Orleans", "Ouachita", "Plaquemines",
    "Pointe Coupee", "Rapides", "Red River", "Richland", "Sabine",
    "St. Bernard", "St. Charles", "St. Helena", "St. James",
    "St. John the Baptist", "St. Landry", "St. Martin", "St. Mary",
    "St. Tammany", "Tangipahoa", "Tensas", "Terrebonne", "Union",
    "Vermilion", "Vernon", "Washington", "Webster", "West Baton Rouge",
    "West Carroll", "West Feliciana", "Winn",
}


def extract_pdf_text(url: str) -> tuple[str, dict[str, Any]]:
    raw, request_log = fetch_bytes(url)
    if not raw:
        return "", request_log
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-", "-"],
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return result.stdout.decode("utf-8", "replace"), request_log
    except (OSError, subprocess.CalledProcessError) as exc:
        request_log["error"] = f"PDF extraction failed: {exc}"
        return "", request_log


def pdf_links(text: str) -> tuple[str, str, str, str]:
    values = re.findall(r"(?:https?://|www\.)[^\s<>]+", text, re.I)
    return split_public_links(values, "")


def louisiana_fmnp_stands(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "LDAF 2026 FMNP roadside-stand directory"
    text, request_log = extract_pdf_text(config["official_fmnp"])
    observations: list[Observation] = []
    records: list[dict[str, Any]] = []
    parish = ""
    for raw_block in re.split(r"\n\s*\n", text.replace("\f", "\n\n")):
        lines = [clean_text(line) for line in raw_block.splitlines() if clean_text(line) and not clean_text(line).isdigit()]
        if not lines:
            continue
        for line in lines:
            parish_match = re.fullmatch(r"(.+?)\s+PARISH", line, re.I)
            if parish_match:
                parish = normalized_county(parish_match.group(1))
        marker = next((index for index, line in enumerate(lines) if "roadside stand" in line.casefold()), None)
        if marker is None:
            continue
        city_index = next((
            index for index, line in enumerate(lines[:marker + 1])
            if re.fullmatch(r"[A-Z][A-Z .'-]+", line) and not line.endswith(" PARISH")
        ), None)
        city = normalized_city(lines[city_index]) if city_index is not None else ""
        start = (city_index + 1) if city_index is not None else 0
        name_text = " ".join(lines[start:marker + 1])
        name = re.sub(r"-?Roadside Stand(?:-Location\s*#?\d+)?", "", name_text, flags=re.I).strip(" ,-–")
        if not name or len(name) > 140:
            continue
        block_text = " | ".join(lines)
        phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", block_text)
        address = next((line for line in lines[marker + 1:] if re.match(r"^(?:\d+|Corner\b|Hwy\b|Highway\b)", line, re.I)), "")
        website, facebook, instagram, tiktok = pdf_links(block_text)
        row = empty_observation(state, source_name, f"{parish}|{city}|{name}", name, config["official_fmnp"], 1, "B")
        market_named = bool(re.search(r"farmers? market", name, re.I))
        row.update({
            "entity_type_source": "LDAF-approved roadside stand",
            "entity_type_review": "needs_review_market_named_roadside_stand" if market_named else "farm_activity_confirmed_by_current_ldaf_roadside_stand_directory",
            "county": parish,
            "county_source": config["official_fmnp"],
            "city": city,
            "address": address,
            "location_precision": "public_directory_address_or_city",
            "phone": phone.group(0) if phone else "",
            "products": "Farm products sold through an LDAF-approved roadside stand",
            "business_types": "Roadside stand; direct-to-consumer",
            "website_url": website,
            "facebook_url": facebook,
            "instagram_url": instagram,
            "tiktok_url": tiktok,
            "on_farm_sales": True,
            "notes": block_text[:1500],
        })
        observations.append(Observation(**row))
        records.append({"name": name, "parish": parish, "city": city, "text": block_text})
    note = "Only entries explicitly labeled roadside stands became farm candidates; farmers markets remain in raw evidence but were not misclassified as farms."
    return observations, [logged(request_log, 1, source_name, len(records), "observations_retained", note)], {"ldaf_fmnp_roadside_stands": records}


def louisiana_lsu_farm_food(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "LSU AgCenter statewide farm-food directory"
    text, request_log = extract_pdf_text(config["lsu_farm_food_pdf"])
    lines = [clean_text(line) for line in text.splitlines()]
    parish = ""
    candidates: list[tuple[int, str, str]] = []
    channel = re.compile(r"^(?:Pre-order|On[- ]farm|Off[- ]farm|Home Delivery|Curbside|Farm Stand|U-Pick|CSA|Farmers Market)", re.I)
    for index, line in enumerate(lines[:-1]):
        normalized = normalized_county(line)
        if normalized in LA_PARISHES:
            parish = normalized
            continue
        if not line or not line[0].isalnum() or not line[0].isupper() or not channel.search(lines[index + 1]):
            continue
        if len(line.split()) > 12:
            continue
        if re.search(r"food hub|distributor|co-op", line, re.I):
            continue
        if re.search(r"\bmarket\b", line, re.I) and not farm_operation_signal(line, "", ""):
            continue
        if 2 < len(line) <= 130:
            candidates.append((index, line, parish))

    observations: list[Observation] = []
    records: list[dict[str, Any]] = []
    for position, (index, name, candidate_parish) in enumerate(candidates):
        end = candidates[position + 1][0] if position + 1 < len(candidates) else min(len(lines), index + 18)
        block_lines = [value for value in lines[index:end] if value]
        block_text = " | ".join(block_lines)
        address_line = next((value for value in block_lines[2:] if re.match(r"^\d+\s", value)), "")
        city_match = re.search(r",\s*([A-Za-z][A-Za-z .'-]{1,40})$", address_line)
        phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", block_text)
        products = next((
            value for value in reversed(block_lines)
            if re.search(r"\b(?:vegetables?|fruit|meat|beef|pork|eggs?|dairy|milk|honey|seafood|mushrooms?|nuts?|flowers?)\b", value, re.I)
            and not re.search(r"certified|association", value, re.I)
        ), "Farm products; see LSU directory")
        seasonal_closed = bool(re.search(r"closed for the season", block_text, re.I))
        row = empty_observation(state, source_name, f"{candidate_parish}|{name}", name, config["lsu_farm_food_pdf"], 1, "E")
        row.update({
            "entity_type_source": "Direct-to-consumer farm or producer",
            "entity_type_review": "farm_activity_confirmed_by_lsu_direct_consumer_directory",
            "county": candidate_parish,
            "county_source": config["lsu_farm_food_pdf"],
            "city": normalized_city(city_match.group(1)) if city_match else "",
            "address": address_line,
            "location_precision": "public_directory_address_or_city",
            "phone": phone.group(0) if phone else "",
            "products": products,
            "business_types": "Direct-to-consumer farm; historical statewide directory",
            "on_farm_sales": bool(re.search(r"on[- ]farm", block_text, re.I)),
            "farmers_market_sales": bool(re.search(r"farmers market", block_text, re.I)),
            "local_delivery": bool(re.search(r"home delivery", block_text, re.I)),
            "u_pick": bool(re.search(r"u-pick", block_text, re.I)),
            "promotion_status": "staged_seasonal_status_review" if seasonal_closed else "staged_pending_rules",
            "notes": "Historical 2020 source requires current corroboration. " + block_text[:1400],
        })
        observations.append(Observation(**row))
        records.append({"name": name, "parish": candidate_parish, "text": block_text})
    note = "Historical statewide directory retained as grade-E evidence; markets and distributors were not treated as farm entities."
    return observations, [logged(request_log, 1, source_name, len(records), "observations_retained", note)], {"lsu_farm_food_records": records}


def display_name_from_upper(value: str) -> str:
    value = clean_text(value).title()
    replacements = {" Llc": " LLC", " Dba ": " DBA ", " Inc.": " Inc.", " R&P ": " R&P ", " B&B": " B&B"}
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"([A-Za-z])'S\b", r"\1's", value)
    return re.sub(r"([A-Za-z])’S\b", r"\1’s", value)


def louisiana_agritourism(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "LDAF certified agritourism operations"
    text, request_log = extract_pdf_text(config["agritourism_pdf"])
    ignored = {"LOUISIANA", "AGRITOURISM", "DIRECTORY", "CERTIFIED AGRITOURISM OPERATIONS"}
    headings = []
    for match in re.finditer(r"(?m)^\s*([A-Z][A-Z0-9 &’'().,\-/]{3,})\s*$", text):
        value = clean_text(match.group(1))
        compact = re.sub(r"[^A-Z]", "", value)
        if value in ignored or any(word in value for word in ("DEPARTMENT OF", "COMMISSIONER", "REVISED:")) or "LOUISIANADEPARTMENTOF" in compact or "AGRICULTUREFORESTRY" in compact:
            continue
        headings.append([match.start(), match.end(), value])
    grouped: list[dict[str, Any]] = []
    for start, end, value in headings:
        if grouped and not clean_text(text[grouped[-1]["end"]:start]):
            grouped[-1]["name"] += " " + value
            grouped[-1]["end"] = end
        else:
            grouped.append({"start": start, "end": end, "name": value})

    observations: list[Observation] = []
    records: list[dict[str, Any]] = []
    for index, heading in enumerate(grouped):
        end = grouped[index + 1]["start"] if index + 1 < len(grouped) else len(text)
        raw_body = text[heading["end"]:end]
        body = clean_text(raw_body)
        if not re.search(r"\b(?:LA|La|Louisiana)\s+\d{5}\b", body) and not producer_signal(heading["name"], body, body):
            continue
        name = display_name_from_upper(heading["name"])
        city_zip = re.search(r"(?m)^\s*([A-Za-z][A-Za-z .'-]{1,40}),\s*(?:LA|La|Louisiana)\s+(\d{5})\b", raw_body)
        phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", body)
        email = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", body, re.I)
        website_match = re.search(r"(?:Web(?:site| Page)?\s*:\s*)?((?:https?://|www\.)[^\s|]+)", body, re.I)
        website = clean_url(website_match.group(1)) if website_match else ""
        confirmed = farm_entity_confirmation(name, body, "Agritourism and farm activities")
        address = ""
        if city_zip:
            prior_lines = [clean_text(value) for value in raw_body[:city_zip.start()].splitlines() if clean_text(value)]
            address = prior_lines[-1] if prior_lines else ""
        row = empty_observation(state, source_name, f"{heading['start']}|{heading['name']}", name, config["agritourism_pdf"], 2, "B")
        row.update({
            "entity_type_source": "Certified agritourism operation",
            "entity_type_review": "farm_activity_confirmed_by_ldaf_agritourism_certification" if confirmed else "certified_agritourism_entity_requires_farm_operation_review",
            "city": normalized_city(city_zip.group(1)) if city_zip else "",
            "postal_code": city_zip.group(2) if city_zip else "",
            "address": clean_text(address),
            "location_precision": "public_directory_address_or_city",
            "phone": phone.group(0) if phone else "",
            "email": email.group(0) if email else "",
            "products": "Agritourism and farm activities; see LDAF certified operation description",
            "business_types": "Certified agritourism",
            "website_url": website,
            "on_farm_sales": bool(re.search(r"sell|sales|store|market", body, re.I)),
            "u_pick": bool(re.search(r"u-pick|pick your own|pumpkin patch", body, re.I)),
            "notes": body[:1500],
        })
        observations.append(Observation(**row))
        records.append({"name": name, "text": body})
    return observations, [logged(request_log, 2, source_name, len(records), "observations_retained")], {"ldaf_agritourism_records": records}


def louisiana_crawfish_suppliers(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "Louisiana Crawfish Promotion and Research Board — suppliers"
    body, request_log = fetch(config["crawfish_suppliers"])
    observations: list[Observation] = []
    records: list[dict[str, Any]] = []
    for article in re.findall(r"<article\b.*?</article>", body, re.I | re.S):
        name_match = re.search(r'post_title[^>]*>\s*<a\s+href="([^"]+)">(.*?)</a>', article, re.I | re.S)
        if not name_match:
            continue
        profile_url, name_html = name_match.groups()
        name = strip_tags(name_html)
        values: dict[str, str] = {}
        for key, css_class in {
            "location": "userprofile-location", "phone": "userprofile-phone",
            "email": "userprofile-email", "website": "userprofilewebsite-url",
        }.items():
            match = re.search(rf'{css_class}.*?<span\s+class="w-post-elm-value">(.*?)</span>', article, re.I | re.S)
            values[key] = strip_tags(match.group(1)) if match else ""
        location = values["location"]
        zip_match = re.search(r"\b(\d{5})\b", location)
        links = [values["website"]] if values["website"] else []
        website, facebook, instagram, tiktok = split_public_links(links, "crawfish.org")
        confirmed = farm_entity_confirmation(name, "Louisiana Crawfish Board farmer or fisherman supplier", "Crawfish")
        row = empty_observation(state, source_name, profile_url.rstrip("/").rsplit("/", 1)[-1], name, profile_url, 1, "B")
        row.update({
            "entity_type_source": "Louisiana Crawfish Board farmer or fisherman supplier",
            "entity_type_review": "farm_activity_confirmed_by_current_official_producer_board" if confirmed else "official_crawfish_supplier_requires_primary_producer_review",
            "city": "",
            "postal_code": zip_match.group(1) if zip_match else "",
            "address": location,
            "location_precision": "public_directory_address_or_city",
            "phone": values["phone"], "email": values["email"],
            "products": "Louisiana crawfish", "business_types": "Crawfish farmer or fisherman supplier",
            "website_url": website, "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
            "on_farm_sales": True,
            "notes": "Current Louisiana Crawfish Promotion and Research Board supplier profile.",
        })
        observations.append(Observation(**row))
        records.append({"name": name, "profile_url": profile_url, **values})
    return observations, [logged(request_log, 1, source_name, len(records), "observations_retained")], {"louisiana_crawfish_board_suppliers": records}


def louisiana_strawberry_growers(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "Louisiana Strawberry Marketing Board — growers"
    body, request_log = fetch(config["strawberry_growers"])
    section_match = re.search(
        r"<h2[^>]*>.*?Louisiana Growers.*?</h2>(.*?)(?:U-Pick Farms|Louisiana U-Pick Farms)",
        body,
        re.I | re.S,
    )
    section = section_match.group(1) if section_match else body
    observations: list[Observation] = []
    records: list[dict[str, Any]] = []
    for index, block in enumerate(re.findall(r"<p>(.*?)</p>", section, re.I | re.S)):
        strong = re.search(r"<strong>(.*?)</strong>", block, re.I | re.S)
        if not strong:
            continue
        heading = strip_tags(strong.group(1))
        if " - " in heading:
            name, city = [clean_text(value) for value in heading.rsplit(" - ", 1)]
        else:
            name, city = heading, ""
        if not name:
            continue
        text = strip_tags(block)
        phones = re.findall(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", text)
        email = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
        links = [html.unescape(value) for value in re.findall(r'<a\s+href="([^"]+)"', block, re.I)]
        website, facebook, instagram, tiktok = split_public_links(links, "louisianastrawberries.com")
        row = empty_observation(state, source_name, f"grower-{index}-{name}", name, config["strawberry_growers"], 1, "B")
        row.update({
            "entity_type_source": "Louisiana strawberry grower",
            "entity_type_review": "farm_activity_confirmed_by_current_official_producer_board",
            "city": normalized_city(city), "location_precision": "public_directory_city",
            "phone": phones[0] if phones else "", "email": email.group(0) if email else "",
            "products": "Louisiana-grown strawberries", "business_types": "Strawberry grower",
            "website_url": website, "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
            "on_farm_sales": bool(re.search(r"u-pick|farm", text, re.I)),
            "notes": text[:1200],
        })
        observations.append(Observation(**row))
        records.append({"name": name, "city": city, "text": text, "links": links})
    return observations, [logged(request_log, 1, source_name, len(records), "observations_retained")], {"louisiana_strawberry_board_growers": records}


def louisiana_sweet_potato_shippers(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "Louisiana Sweet Potato Commission — shippers and processors"
    body, request_log = fetch(config["sweet_potato_shippers"])
    observations: list[Observation] = []
    records: list[dict[str, Any]] = []
    blocks = re.findall(r"<h2\b[^>]*>(.*?)</h2>", body, re.I | re.S)
    for index, block in enumerate(blocks):
        name_match = re.search(r"<strong>(.*?)</strong>", block, re.I | re.S)
        if not name_match:
            continue
        name = strip_tags(name_match.group(1))
        if not name or name.casefold() in {"shippers of louisiana yams", "processors of louisiana yams"}:
            continue
        text = strip_tags(block)
        city_match = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40}),\s*LA\b", text, re.I)
        phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", text)
        links = [html.unescape(value) for value in re.findall(r'<a\s+href="([^"]+)"', block, re.I)]
        website, facebook, instagram, tiktok = split_public_links(links, "sweetpotato.org")
        confirmed = bool(re.search(r"\bfarms?\b", name, re.I))
        row = empty_observation(state, source_name, f"shipper-{index}-{name}", name, config["sweet_potato_shippers"], 2, "C")
        row.update({
            "entity_type_source": "Louisiana sweet-potato shipper or processor",
            "entity_type_review": "farm_activity_confirmed_by_official_commission_farm_name" if confirmed else "official_shipper_or_processor_requires_primary_producer_review",
            "city": normalized_city(city_match.group(1)) if city_match else "", "location_precision": "public_directory_city",
            "phone": phone.group(0) if phone else "", "products": "Louisiana sweet potatoes",
            "business_types": "Sweet-potato shipper or processor", "website_url": website,
            "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
            "notes": "Current public commission page has an undated shipper/processor list; primary production requires review.",
        })
        observations.append(Observation(**row))
        records.append({"name": name, "text": text, "links": links})
    return observations, [logged(request_log, 2, source_name, len(records), "observations_retained")], {"louisiana_sweet_potato_shippers_processors": records}


def louisiana_nursery_growers(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "LDAF June 2026 nursery certificate holders"
    text, request_log = extract_pdf_text(config["nursery_growers_pdf"])
    records: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 6 or parts[0].title() not in LA_PARISHES or not re.fullmatch(r"NC[12]", parts[-1]):
            continue
        phone = next((value for value in parts[2:-4] if re.search(r"\d{3}.*\d{3}.*\d{4}", value)), "")
        records.append({
            "parish": parts[0].title(), "name": display_name_from_upper(parts[1]),
            "contact": parts[2] if len(parts) > 6 else "", "phone": phone,
            "address": parts[-4], "city": parts[-3], "postal_code": parts[-2], "permit": parts[-1],
        })
    observations: list[Observation] = []
    for index, record in enumerate(records):
        row = empty_observation(state, source_name, f"nursery-{index}-{record['name']}", record["name"], config["nursery_growers_pdf"], 1, "A")
        row.update({
            "entity_type_source": "LDAF nursery grower permit holder",
            "entity_type_review": "farm_activity_confirmed_by_current_official_grower_permit",
            "county": normalized_county(record["parish"]), "county_source": config["nursery_growers_pdf"],
            "city": normalized_city(record["city"]), "postal_code": record["postal_code"],
            "address": record["address"], "location_precision": "public_permit_address",
            "phone": record["phone"], "products": "Nursery stock, cut flowers, or bulbs grown by the permit holder",
            "business_types": f"Licensed nursery grower; {record['permit']}",
            "on_farm_sales": True,
            "notes": "LDAF states the nursery certificate permit authorizes a grower to sell nursery stock, cut flowers, and bulbs that the permit holder grows.",
        })
        observations.append(Observation(**row))
    return observations, [logged(request_log, 1, source_name, len(records), "observations_retained")], {"ldaf_nursery_certificate_growers": records}


def louisiana_hemp_growers(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "LDAF March 2026 licensed hemp growers"
    text, request_log = extract_pdf_text(config["hemp_growers_pdf"])
    records: list[dict[str, str]] = []
    for line in text.splitlines()[2:]:
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) not in {5, 6} or not re.fullmatch(r"\d{2}_\d+", parts[-1]):
            continue
        if len(parts) == 6:
            licensee, business, parish, phone, email, license_number = parts
        else:
            licensee, parish, phone, email, license_number = parts
            business = ""
        records.append({
            "licensee": display_name_from_upper(licensee),
            "name": display_name_from_upper(business or licensee),
            "parish": normalized_county(parish), "phone": phone, "email": email,
            "license_number": license_number,
        })
    observations: list[Observation] = []
    for record in records:
        row = empty_observation(state, source_name, record["license_number"], record["name"], config["hemp_growers_pdf"], 1, "A")
        row.update({
            "entity_type_source": "LDAF licensed industrial-hemp grower",
            "entity_type_review": "farm_activity_confirmed_by_current_official_grower_license",
            "county": record["parish"], "county_source": config["hemp_growers_pdf"],
            "phone": record["phone"], "email": record["email"],
            "products": "Industrial hemp", "business_types": "Licensed industrial-hemp grower",
            "notes": f"LDAF March 2026 grower license {record['license_number']}; licensee {record['licensee']}.",
        })
        observations.append(Observation(**row))
    return observations, [logged(request_log, 1, source_name, len(records), "observations_retained")], {"ldaf_hemp_growers": records}


def louisiana_registered_apiary_businesses(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "LDAF June 2026 registered apiary businesses"
    text, request_log = extract_pdf_text(config["apiary_register_pdf"])
    business_signal = re.compile(r"\b(?:farm|farms|ranch|honey|apiar|bee|beez|acres|homestead|orchard)\b", re.I)
    all_records: list[dict[str, str]] = []
    retained: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 3 or parts[0].title() not in LA_PARISHES:
            continue
        record = {
            "parish": parts[0].title(), "name": display_name_from_upper(parts[1].strip(" ,")),
            "address": parts[2], "phone": parts[3] if len(parts) > 3 else "",
        }
        all_records.append(record)
        if business_signal.search(record["name"]):
            retained.append(record)
    observations: list[Observation] = []
    for index, record in enumerate(retained):
        city_zip = re.search(r"(?:,\s*)?([A-Za-z][A-Za-z .'-]{1,40}),\s*LA\s+(\d{5})", record["address"], re.I)
        row = empty_observation(state, source_name, f"apiary-{index}-{record['name']}", record["name"], config["apiary_register_pdf"], 1, "A")
        row.update({
            "entity_type_source": "LDAF registered apiary business",
            "entity_type_review": "farm_activity_confirmed_by_current_official_apiary_registration",
            "county": normalized_county(record["parish"]), "county_source": config["apiary_register_pdf"],
            "city": normalized_city(city_zip.group(1)) if city_zip else "",
            "postal_code": city_zip.group(2) if city_zip else "", "address": record["address"],
            "location_precision": "public_registration_address", "phone": record["phone"],
            "products": "Registered apiary or beekeeping operation; public sales require separate verification",
            "business_types": "Registered apiary business",
            "notes": "The public registration confirms a controlled apiary. Personal-name-only registrations remain in raw evidence and were not assumed to be public farm businesses.",
        })
        observations.append(Observation(**row))
    note = f"Reviewed {len(all_records)} public registrations; retained {len(retained)} names with an explicit farm, ranch, honey-business, bee-company, or apiary signal."
    return observations, [logged(request_log, 1, source_name, len(retained), "observations_retained", note)], {"ldaf_registered_apiary_businesses": retained, "ldaf_personal_name_apiary_registrations_reviewed": len(all_records) - len(retained)}


def mississippi_genuine(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    observations: list[Observation] = []
    logs: list[dict[str, Any]] = []
    cards: list[dict[str, str]] = []
    for source_name, source_url in config["genuine_archives"].items():
        body, request_log = fetch(source_url)
        parsed: list[dict[str, str]] = []
        for article in re.findall(r"<article\b.*?</article>", body, flags=re.I | re.S):
            match = re.search(
                r"<h5>(.*?)</h5>.*?<a\s+href=[\"']([^\"']*/directory/[^\"']+)[\"'][^>]*>\s*<h3>(.*?)</h3>",
                article,
                flags=re.I | re.S,
            )
            if not match:
                continue
            location, profile_url, farm_name = map(clean_text, match.groups())
            parsed.append({
                "source_name": source_name, "profile_url": profile_url, "farm_name": farm_name,
                "location": location, "archive_description": strip_tags(article),
            })
        cards.extend(parsed)
        logs.append(logged(request_log, 1, source_name, len(parsed), "observations_retained"))

    raw_profiles: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, card["profile_url"]): card for card in cards}
        for future in as_completed(futures):
            card = futures[future]
            body, request_log = future.result()
            profile_url = card["profile_url"]
            city = re.sub(r",?\s*(?:MS|Mississippi)\s*$", "", card["location"], flags=re.I).strip(" ,")
            contact_match = re.search(r'<span\s+class="member-contact">(.*?)</span>', body, flags=re.I | re.S)
            contact = clean_text(contact_match.group(1)) if contact_match else ""
            city_match = re.search(r",\s*([^,|]+),\s*(?:MS|Mississippi)\s+(\d{5})", contact, flags=re.I)
            phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", contact)
            email_match = re.search(r'<li\s+class="prov-email".*?<a\s+href="mailto:([^"?]+)', body, re.I | re.S)
            links: list[str] = []
            for css_class in ("prov-web", "prov-facebook", "prov-instagram"):
                match = re.search(rf'<li\s+class="{css_class}".*?<a\s+href="([^"]+)', body, re.I | re.S)
                if match:
                    links.append(html.unescape(match.group(1)))
            website, facebook, instagram, tiktok = split_public_links(links, "genuinems.com")
            products = [strip_tags(value) for value in re.findall(r'<li\s+class="product-item">(.*?)</li>', body, re.I | re.S)]
            description = meta_value(body, "description") or card.get("archive_description", "")
            product_text = "; ".join(value for value in products if value) or "Mississippi-grown or -raised farm products"
            confirmed = farm_entity_confirmation(card["farm_name"], description, product_text)
            row = empty_observation(state, card["source_name"], profile_url.rsplit("/", 2)[-2], card["farm_name"], profile_url, 1, "B")
            row.update({
                "entity_type_source": "Genuine MS Grown/Raised member",
                "entity_type_review": "farm_activity_confirmed_by_official_grown_or_raised_classification" if confirmed else "official_grown_or_raised_member_requires_farm_operation_review",
                "city": normalized_city(city_match.group(1) if city_match else city),
                "postal_code": city_match.group(2) if city_match else "",
                "address": contact.split(" | ", 1)[0] if contact else "",
                "location_precision": "public_directory_address_or_city",
                "phone": phone.group(0) if phone else "",
                "email": email_match.group(1).strip() if email_match else "",
                "products": product_text,
                "business_types": card["source_name"].replace("Genuine MS — ", "Genuine MS "),
                "website_url": website,
                "facebook_url": facebook,
                "instagram_url": instagram,
                "tiktok_url": tiktok,
                "on_farm_sales": bool(re.search(r"direct|farm stand|on[- ]farm|pick[- ]?up", description, re.I)),
                "notes": description[:1400],
            })
            observations.append(Observation(**row))
            raw_profiles.append({**card, "contact": contact, "products": products, "description": description})
            logs.append(logged(request_log, 1, "Genuine MS profile request", int(bool(body)), "request_component"))
    return observations, logs, {"genuine_ms_profiles": raw_profiles}


def mississippi_mdac_market_channels(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    observations: list[Observation] = []
    logs: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    source_name = "MDAC Mississippi Farmers Market agricultural vendors"
    body, request_log = fetch(config["mdac_vendor_list"])
    vendor_cards: list[dict[str, str]] = []
    pattern = re.compile(
        r'<tr[^>]*>\s*<td[^>]*>.*?<a\s+href="([^"]*FarmerMarket_VendorView[^\"]*)"[^>]*>.*?<font[^>]*>(.*?)</font>.*?</a>.*?</td>\s*<td[^>]*>(.*?)</td>',
        re.I | re.S,
    )
    for href, name, product_type in pattern.findall(body):
        farm_name = strip_tags(name)
        products = strip_tags(product_type)
        if products not in {"Fruit and Vegetables", "Dairy", "Meat", "Nursery"} and not producer_signal(farm_name, "", products):
            continue
        vendor_cards.append({"name": farm_name, "products": products, "url": urllib.parse.urljoin(config["mdac_vendor_list"], html.unescape(href))})
    logs.append(logged(request_log, 2, source_name, len(vendor_cards), "observations_retained", "Arts, crafts, baked goods, and other non-producer categories were retained only in raw source evidence."))
    vendor_records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch, card["url"]): card for card in vendor_cards}
        for future in as_completed(futures):
            card = futures[future]
            profile, profile_log = future.result()
            values = {}
            for field_name, element_id in {
                "address": "MainContent_Label_Address",
                "email": "MainContent_Label_Email",
                "phone": "MainContent_Label_BusPhone",
                "products": "MainContent_Label_AgProducts",
            }.items():
                match = re.search(rf'<span\s+id="{element_id}">(.*?)</span>', profile, re.I | re.S)
                values[field_name] = strip_tags(match.group(1)) if match else ""
            city_zip = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40}),\s*MS\s+(\d{5})\b", values["address"], re.I)
            confirmed = farm_entity_confirmation(card["name"], "MDAC agricultural farmers-market vendor", values["products"] or card["products"])
            row = empty_observation(state, source_name, card["url"].rsplit("=", 1)[-1], card["name"], card["url"], 2, "B")
            row.update({
                "entity_type_source": "Agricultural farmers-market vendor",
                "entity_type_review": "farm_activity_confirmed_by_mdac_agricultural_vendor_category" if confirmed else "mdac_agricultural_vendor_requires_farm_operation_review",
                "city": normalized_city(city_zip.group(1)) if city_zip else "",
                "postal_code": city_zip.group(2) if city_zip else "",
                "address": values["address"],
                "location_precision": "public_directory_address_or_city",
                "phone": values["phone"],
                "email": values["email"],
                "products": values["products"] or card["products"],
                "business_types": "Mississippi Farmers Market agricultural vendor",
                "farmers_market_sales": True,
                "notes": "MDAC vendor category: " + card["products"],
            })
            observations.append(Observation(**row))
            vendor_records.append({**card, **values})
            logs.append(logged(profile_log, 2, "MDAC vendor profile request", int(bool(profile)), "request_component"))
    raw["mdac_agricultural_vendors"] = vendor_records

    marketplace_name = "MDAC Mississippi Farm Marketplace"
    marketplace_body, marketplace_log = fetch(config["mdac_marketplace"])
    marketplace_records: list[dict[str, Any]] = []
    blocks = re.findall(r'<p\s+style="width:99%;text-align:justify">(.*?)</p>', marketplace_body, re.I | re.S)
    for block in blocks:
        match = re.search(
            r'<a\s+href="(/MarketPortal/MarketPortal\?farm=[^"]+)">(.*?)</a>\s+in\s+([^<(]+)\s*\(<mark[^>]*>(.*?)</mark>\s+county\)',
            block,
            re.I | re.S,
        )
        if not match:
            continue
        href, farm_name, city, county = match.groups()
        source_url = urllib.parse.urljoin(config["mdac_marketplace"], html.unescape(href))
        product_pairs = re.findall(r'>\s*Providing\s+([^<\r\n]+)</a>|MarketPortal_Single\?id=\d+">\s*([^<]+)</a>', block, re.I)
        flattened = [strip_tags(value) for pair in product_pairs for value in pair if value]
        phones = re.findall(r'href="tel:([^"]+)"', block, re.I)
        emails = re.findall(r'href="mailto:\s*([^"]+)"', block, re.I)
        external = [html.unescape(value) for value in re.findall(r'<a\s+target="_blank"\s+href="([^"]+)"', block, re.I)]
        website, facebook, instagram, tiktok = split_public_links(external, "mdac.ms.gov")
        marketplace_name_value = strip_tags(farm_name)
        product_text = "; ".join(dict.fromkeys(flattened)) or "Farm commodities listed for sale"
        confirmed = farm_entity_confirmation(marketplace_name_value, strip_tags(block), product_text)
        row = empty_observation(state, marketplace_name, href.rsplit("=", 1)[-1], marketplace_name_value, source_url, 2, "B")
        row.update({
            "entity_type_source": "Active farm marketplace seller",
            "entity_type_review": "farm_activity_confirmed_by_mdac_farm_marketplace" if confirmed else "mdac_farm_marketplace_seller_requires_farm_operation_review",
            "county": normalized_county(strip_tags(county)),
            "county_source": source_url,
            "city": normalized_city(strip_tags(city)),
            "phone": phones[0].strip() if phones else "",
            "email": emails[0].strip() if emails else "",
            "products": product_text,
            "business_types": "Farm Marketplace; direct-to-consumer",
            "website_url": website,
            "facebook_url": facebook,
            "instagram_url": instagram,
            "tiktok_url": tiktok,
            "on_farm_sales": True,
            "notes": strip_tags(block)[:1200],
        })
        observations.append(Observation(**row))
        marketplace_records.append({"name": strip_tags(farm_name), "city": strip_tags(city), "county": strip_tags(county), "products": flattened})
    logs.append(logged(marketplace_log, 2, marketplace_name, len(marketplace_records), "observations_retained"))
    raw["mdac_farm_marketplace"] = marketplace_records
    return observations, logs, raw


def mississippi_agritourism(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "MDAC registered agritourism venues"
    body, request_log = fetch(config["mdac_agritourism"])
    observations: list[Observation] = []
    records: list[dict[str, Any]] = []
    pattern = re.compile(
        r'<a\s+href="Venues_Single\?id=(\d+)"[^>]*>(.*?)</a><span[^>]*>(.*?)\s+COUNTY</span>(.*?<hr>)',
        re.I | re.S,
    )
    for record_id, name_html, county_html, segment in pattern.findall(body):
        name = strip_tags(name_html)
        county = normalized_county(strip_tags(county_html))
        text = strip_tags(segment)
        city_zip = re.search(r"<br\s*/?>\s*([A-Za-z][A-Za-z .'-]{1,40}),\s*MS(?:&nbsp;|\s)+(\d{5})", segment, re.I)
        phone = re.search(r"Phone:\s*((?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4})", text, re.I)
        if not phone:
            phone = re.search(r"Cell:\s*((?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4})", text, re.I)
        email = re.search(r"mailto:([^\s>\"']+)", segment, re.I)
        website_match = re.search(r"Website:\s*<a\s+href=([^\s>]+)", segment, re.I)
        facebook_match = re.search(r"Facebook:\s*<a\s+href=([^\s>]+)", segment, re.I)
        source_url = urllib.parse.urljoin(config["mdac_agritourism"], f"Venues_Single?id={record_id}")
        confirmed = farm_entity_confirmation(name, text, "Agritourism and farm activities")
        row = empty_observation(state, source_name, record_id, name, source_url, 2, "B")
        row.update({
            "entity_type_source": "Registered agritourism operation",
            "entity_type_review": "farm_activity_confirmed_by_mdac_agritourism_registration" if confirmed else "registered_agritourism_entity_requires_farm_operation_review",
            "county": county,
            "county_source": source_url,
            "city": normalized_city(city_zip.group(1)) if city_zip else "",
            "postal_code": city_zip.group(2) if city_zip else "",
            "address": "",
            "location_precision": "public_directory_address_or_city",
            "phone": phone.group(1) if phone else "",
            "email": email.group(1).strip() if email else "",
            "products": "Agritourism and farm activities; see MDAC venue description",
            "business_types": "Registered agritourism",
            "website_url": clean_url(html.unescape(website_match.group(1))) if website_match else "",
            "facebook_url": clean_url(html.unescape(facebook_match.group(1))) if facebook_match else "",
            "on_farm_sales": bool(re.search(r"on[- ]farm sales|farm stand|sell|market", text, re.I)),
            "u_pick": bool(re.search(r"u-pick|pick your own|pumpkin patch|christmas tree", text, re.I)),
            "notes": text[:1500],
        })
        observations.append(Observation(**row))
        records.append({"id": record_id, "name": name, "county": county, "text": text})
    return observations, [logged(request_log, 2, source_name, len(records), "observations_retained")], {"mdac_agritourism_venues": records}


def mississippi_christmas_tree_farms(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "MDAC-linked Mississippi Christmas Tree Farms"
    body, request_log = fetch(config["christmas_tree_farms"])
    observations: list[Observation] = []
    records: list[dict[str, Any]] = []
    headings = list(re.finditer(r"<h5[^>]*>(.*?)</h5>", body, re.I | re.S))
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        segment = body[match.end():end]
        raw_name = strip_tags(match.group(1))
        name = re.sub(r"\s*\([^)]*(?:2025|2026|trees may be sourced)[^)]*\)\s*$", "", raw_name, flags=re.I).strip()
        if not name:
            continue
        text = strip_tags(segment)
        city_zip = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40}),\s*MS\s+(\d{5})\b", text, re.I)
        phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", text)
        email = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
        links = [html.unescape(value) for value in re.findall(r'<a\s+href="([^"]+)"', segment, re.I)]
        website, facebook, instagram, tiktok = split_public_links(links, "mschristmastrees.com")
        row = empty_observation(state, source_name, f"tree-{index}-{name}", name, config["christmas_tree_farms"], 1, "B")
        row.update({
            "entity_type_source": "Mississippi Christmas tree farm",
            "entity_type_review": "farm_activity_confirmed_by_current_official_farm_directory",
            "city": normalized_city(city_zip.group(1)) if city_zip else "",
            "postal_code": city_zip.group(2) if city_zip else "",
            "address": text.split("Contact:", 1)[0].strip(), "location_precision": "public_directory_address_or_city",
            "phone": phone.group(0) if phone else "", "email": email.group(0) if email else "",
            "products": "Mississippi-grown Christmas trees", "business_types": "Christmas tree farm",
            "website_url": website, "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
            "on_farm_sales": True,
            "notes": raw_name + ". " + text[:1100],
        })
        observations.append(Observation(**row))
        records.append({"name": name, "raw_name": raw_name, "text": text, "links": links})
    return observations, [logged(request_log, 1, source_name, len(records), "observations_retained")], {"mississippi_christmas_tree_farms": records}


def nursery_page_columns(page: str) -> list[list[str]]:
    lines = page.splitlines()
    positions = [
        match.start()
        for line in lines
        for match in re.finditer(r"Physical Address:", line)
        if match.start() > 55
    ]
    if not positions:
        return []
    split = min(positions)
    return [
        [line[start:end].rstrip() for line in lines]
        for start, end in ((0, split), (split, None))
    ]


def nursery_column_records(lines: list[str]) -> list[dict[str, str]]:
    starts = [
        index for index, line in enumerate(lines[:-1])
        if line.strip() and line.strip() == line.strip().upper()
        and "County:" in lines[index + 1]
        and not line.strip().startswith("PAGE ")
    ]
    records: list[dict[str, str]] = []
    stock_terms = (
        "BEDDING", "DAYLILIES OR BULBS", "FOLIAGE", "FRUITING", "GROUND COVER",
        "NATIVE", "ORNAMENTALS", "OTHER", "VEGETABLE", "SOD ONLY",
    )
    for position, start in enumerate(starts):
        block = lines[start:(starts[position + 1] if position + 1 < len(starts) else len(lines))]
        name = block[0].strip()
        if start and lines[start - 1].strip() and lines[start - 1].strip() == lines[start - 1].strip().upper() and "County:" not in lines[start - 1]:
            name = clean_text(lines[start - 1] + " " + name)
        owner_county = block[1]
        owner, county = owner_county.split("County:", 1)
        def field(label: str) -> str:
            return next((line.split(label, 1)[1].strip() for line in block if label in line), "")
        physical_index = next((i for i, line in enumerate(block) if line.strip().startswith("Physical Address:")), -1)
        address_parts = []
        if physical_index >= 0:
            for line in block[physical_index + 1:physical_index + 3]:
                value = line[:42].strip()
                if value:
                    address_parts.append(value)
        address = ", ".join(address_parts)
        city_zip = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40})\s*,\s*MS\s+(\d{5})", address, re.I)
        phones = re.findall(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", " ".join(block))
        website = clean_url(field("Website:"))
        products = "; ".join(term.title() for term in stock_terms if re.search(rf"\b{re.escape(term)}\b", " ".join(block), re.I))
        records.append({
            "name": display_name_from_upper(name), "owner": clean_text(owner),
            "county": normalized_county(county), "classification": field("Classification:"),
            "sales_structure": field("Sales Structure:"), "address": address,
            "city": normalized_city(city_zip.group(1)) if city_zip else "",
            "postal_code": city_zip.group(2) if city_zip else "",
            "phone": phones[0] if phones else "", "website": website,
            "products": products or "Nursery stock grown by the certified operation",
        })
    return records


def mississippi_certified_nurseries(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "MDAC 2025–2026 certified nursery growers"
    text, request_log = extract_pdf_text(config["certified_nurseries_pdf"])
    parsed: list[dict[str, str]] = []
    pages = text.split("\f")
    dealer_start = next((index for index, page in enumerate(pages) if page.lstrip().startswith("Nursery Dealers")), len(pages))
    for page in pages[3:dealer_start]:
        for column in nursery_page_columns(page):
            parsed.extend(nursery_column_records(column))
    growers = [row for row in parsed if row["classification"] in {"Commercial", "Non-Commercial"}]
    observations: list[Observation] = []
    for index, record in enumerate(growers):
        website, facebook, instagram, tiktok = split_public_links([record["website"]] if record["website"] else [], "mdac.ms.gov")
        row = empty_observation(state, source_name, f"nursery-{index}-{record['name']}", record["name"], config["certified_nurseries_pdf"], 1, "B")
        row.update({
            "entity_type_source": f"MDAC certified {record['classification'].lower()} nursery grower",
            "entity_type_review": "farm_activity_confirmed_by_recent_official_grower_certification",
            "county": record["county"], "county_source": config["certified_nurseries_pdf"],
            "city": record["city"], "postal_code": record["postal_code"], "address": record["address"],
            "location_precision": "public_certification_address", "phone": record["phone"],
            "products": record["products"],
            "business_types": f"Nursery grower; {record['classification']}; {record['sales_structure']}",
            "website_url": website, "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
            "on_farm_sales": "Retail" in record["sales_structure"], "wholesale": "Wholesale" in record["sales_structure"],
            "notes": "MDAC nursery certificate period July 1, 2025 through June 30, 2026; outlets and records without an explicit grower classification were not treated as farm candidates.",
        })
        observations.append(Observation(**row))
    note = f"Parsed {len(parsed)} certified-nursery entries; retained {len(growers)} explicit commercial/non-commercial growers and did not treat outlets or unclassified entries as farms."
    return observations, [logged(request_log, 1, source_name, len(growers), "observations_retained", note)], {"mdac_certified_nursery_growers": growers}


def arkansas_directory(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "Arkansas Department of Agriculture — Arkansas Grown directory"
    landing, landing_log = fetch(config["official_directory"])
    nonce_match = re.search(r'ajax_nonce":"([^"]+)', landing)
    if not nonce_match:
        return [], [logged(landing_log, 1, source_name, 0, "unreachable_after_3_attempts", "Public search nonce missing")], {}
    nonce = nonce_match.group(1)
    profile_urls: dict[str, dict[str, Any]] = {}
    logs: list[dict[str, Any]] = []
    pages = 1
    advertised_results = 0
    for page in range(20):
        form = {
            "page": str(page), "preserve_page": "false", "search_keywords": "",
            "category": "arkansas-grown", "search_location": "", "lat": "false", "lng": "false",
            "proximity": "20", "region": "", "tags": "", "sort": "latest",
        }
        params = [(f"form_data[{key}]", value) for key, value in form.items()]
        params += [("listing_type", "place"), ("listing_wrap", "col-md-4 col-sm-6 grid-item"), ("proximity_units", "mi")]
        url = f"{config['official_root']}/?mylisting-ajax=1&action=get_listings&security={nonce}&{urllib.parse.urlencode(params)}"
        response, request_log = fetch(url)
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            payload = {}
        result_html = payload.get("html", "")
        advertised_results = int(payload.get("found_posts") or advertised_results)
        card_links = list(re.finditer(r'<a href="(https://arkansasgrown\.org/listing/[^"]+/)">', result_html, re.I))
        for card_link in card_links:
            profile_url = card_link.group(1)
            after = result_html[card_link.end():card_link.end() + 2500]
            before = result_html[max(0, card_link.start() - 2000):card_link.start()]
            title_match = re.search(r'listing-preview-title[^>]*>(.*?)</h4>', after, re.I | re.S)
            description_match = re.search(r'<h6>(.*?)</h6>', after, re.I | re.S)
            phone_match = re.search(r'icon-phone[^<]*</i>\s*([^<]+)', after, re.I | re.S)
            location_matches = re.findall(r'data-locations="([^"]+)"', before, re.I)
            locations: list[dict[str, Any]] = []
            if location_matches:
                try:
                    locations = json.loads(html.unescape(location_matches[-1]))
                except json.JSONDecodeError:
                    locations = []
            profile_urls.setdefault(profile_url, {
                "url": profile_url,
                "name": strip_tags(title_match.group(1)) if title_match else "",
                "description": strip_tags(description_match.group(1)) if description_match else "",
                "phone": clean_text(phone_match.group(1)) if phone_match else "",
                "locations": locations,
            })
        pages = int(payload.get("max_num_pages") or pages)
        logs.append(logged(request_log, 1, f"{source_name} — search page", len(card_links), "request_component", f"Page {page + 1} of {pages}"))
        if page + 1 >= pages:
            break

    profiles: list[dict[str, Any]] = []
    observations: list[Observation] = []
    profile_logs: list[dict[str, Any]] = []
    failed_urls: list[str] = []

    def retain_profile(url: str, body: str) -> bool:
        business, page_data = parse_local_business(body) if body else ({}, {})
        name = clean_text(business.get("name"))
        if not name:
            return False
        description = strip_tags(business.get("description", ""))
        products_match = re.search(
            r'Arkansas Grown Products</h5>.*?<div class="pf-body">(.*?)</div>', body, re.I | re.S
        )
        products = strip_tags(products_match.group(1)) if products_match else ""
        address_data = business.get("address") if isinstance(business.get("address"), dict) else {}
        address = clean_text(address_data.get("address"))
        city_zip = re.search(r",\s*([^,]+),\s*(?:AR|Arkansas)\s+(\d{5})(?:-\d{4})?", address, re.I)
        same_as = business.get("sameAs") if isinstance(business.get("sameAs"), list) else []
        links = same_as + re.findall(r'href="(https?://[^"]+)"', body, re.I)
        website, facebook, instagram, tiktok = split_public_links(links, "arkansasgrown.org")
        lat = address_data.get("lat") or (business.get("geo") or {}).get("latitude")
        lng = address_data.get("lng") or (business.get("geo") or {}).get("longitude")
        confirmed = producer_signal(name, description, products)
        record_id = url.rstrip("/").rsplit("/", 1)[-1]
        row = empty_observation(state, source_name, record_id, name, url, 1, "B")
        row.update({
            "entity_type_source": "Arkansas Grown member",
            "entity_type_review": "farm_activity_confirmed_by_current_official_profile" if confirmed else "official_agriculture_member_requires_farm_operation_review",
            "city": normalized_city(city_zip.group(1)) if city_zip else "",
            "postal_code": city_zip.group(2) if city_zip else "",
            "address": address,
            "latitude": float(lat) if lat not in {None, ""} else None,
            "longitude": float(lng) if lng not in {None, ""} else None,
            "location_precision": "official_directory_public_business_address" if address else "official_profile_no_public_location",
            "phone": clean_text(business.get("telephone")),
            "email": clean_text(business.get("email")),
            "products": products or (description[:700] if confirmed else ""),
            "business_types": "Arkansas Grown member",
            "website_url": website,
            "facebook_url": facebook,
            "instagram_url": instagram,
            "tiktok_url": tiktok,
            "on_farm_sales": bool(re.search(r"on[- ]farm|farm stand|u-pick|pick your own", description, re.I)),
            "online_sales": bool(website and re.search(r"shop|order|shipping|online", description, re.I)),
            "u_pick": bool(re.search(r"u-pick|pick your own", description, re.I)),
            "retrieved_date": TODAY,
            "notes": f"Official profile modified {clean_text(page_data.get('dateModified'))}. {description}"[:1500],
        })
        observations.append(Observation(**row))
        profiles.append({"url": url, "business": business, "page": page_data, "products": products})
        if len(profiles) % 50 == 0:
            print(f"{state} official profiles retained: {len(profiles)}/{len(profile_urls)}", flush=True)
        return True

    def retain_search_card(url: str) -> bool:
        card = profile_urls[url]
        name = clean_text(card.get("name"))
        if not name:
            return False
        description = clean_text(card.get("description"))
        locations = card.get("locations") if isinstance(card.get("locations"), list) else []
        location = locations[0] if locations and isinstance(locations[0], dict) else {}
        address = clean_text(location.get("address"))
        confirmed = producer_signal(name, description, description)
        record_id = url.rstrip("/").rsplit("/", 1)[-1]
        row = empty_observation(state, source_name, record_id, name, url, 1, "B")
        row.update({
            "entity_type_source": "Arkansas Grown member",
            "entity_type_review": "farm_activity_confirmed_by_current_official_search_card" if confirmed else "official_agriculture_member_requires_farm_operation_review",
            "address": address,
            "latitude": float(location["lat"]) if location.get("lat") not in {None, ""} else None,
            "longitude": float(location["lng"]) if location.get("lng") not in {None, ""} else None,
            "location_precision": "official_directory_search_card_location" if address else "official_search_card_no_public_location",
            "phone": clean_text(card.get("phone")),
            "products": description if confirmed else "",
            "business_types": "Arkansas Grown member",
            "retrieved_date": TODAY,
            "notes": f"Official profile unavailable after retries; retained from current official search card. {description}"[:1500],
        })
        observations.append(Observation(**row))
        profiles.append({"url": url, "profile_unavailable": True, "official_search_card": card})
        return True

    # The state directory throttles large connection bursts. Eight workers with
    # a bounded timeout completes more reliably than opening hundreds of queued
    # sockets against the public WordPress host.
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch, url, 3, 25): url for url in profile_urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                body, request_log = future.result()
            except Exception as exc:
                body, request_log = "", {"url": url, "error": str(exc), "attempts_used": 0}
            retained = retain_profile(url, body)
            profile_logs.append(logged(request_log, 1, f"{source_name} — profile request", int(retained), "request_component"))
            if not retained:
                failed_urls.append(url)

    # A small number of profiles can time out under the concurrent pass. Retry
    # only those URLs sequentially so a transient 504 cannot create a partial
    # official-directory release.
    for url in failed_urls:
        body, request_log = fetch(url, 5, 45)
        retained = retain_profile(url, body)
        profile_logs.append(logged(request_log, 1, f"{source_name} — sequential profile retry", int(retained), "request_component"))
        if not retained:
            retained = retain_search_card(url)
            profile_logs.append({
                "url": url, "attempts_used": 0, "http_status": 0, "bytes": 0, "sha256": "",
                "elapsed_seconds": 0, "error": "", "pass": 1,
                "source_name": f"{source_name} — official search-card fallback",
                "records_parsed": int(retained), "retrieved_at": now_iso(),
                "source_decision": "request_component",
                "note": "Named candidate retained because the official profile remained unavailable; missing fields stay in QA.",
            })
    logs.extend(profile_logs)
    aggregate = logged(
        landing_log,
        1,
        source_name,
        len(observations),
        "observations_retained",
        f"Public directory reported {len(profile_urls)} Arkansas Grown profiles across {pages} pages; every named profile was retained.",
    )
    if advertised_results != len(profile_urls) or len(observations) != len(profile_urls):
        aggregate["error"] = (
            f"Directory advertised {advertised_results} results; captured {len(profile_urls)} profile URLs "
            f"and parsed {len(observations)} named profiles"
        )
    logs.append(aggregate)
    return observations, logs, {"directory_profiles": profiles}


def post_json(url: str, payload: dict[str, Any], token: str, attempts: int = 3) -> tuple[dict[str, Any], dict[str, Any]]:
    encoded = json.dumps(payload, separators=(",", ":")).encode()
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            request = urllib.request.Request(
                url,
                data=encoded,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "User-Agent": "FarmFinderDataAudit/1.0",
                },
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read()
                return json.loads(raw), {
                    "url": url, "attempts_used": attempt, "http_status": response.status,
                    "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                    "elapsed_seconds": round(time.monotonic() - started, 3), "error": "",
                }
        except Exception as exc:
            errors.append(f"attempt {attempt}: {exc}")
            if attempt < attempts:
                time.sleep(attempt)
    return {}, {
        "url": url, "attempts_used": attempts, "http_status": 0, "bytes": 0,
        "sha256": "", "elapsed_seconds": 0, "error": " | ".join(errors),
    }


def meta_value(body: str, key: str, attribute: str = "name") -> str:
    match = re.search(
        rf'<meta\s+[^>]*{attribute}=["\']{re.escape(key)}["\'][^>]*content=["\']([^"\']*)',
        body,
        re.I,
    )
    return clean_text(match.group(1)) if match else ""


def farm_operation_signal(name: str, description: str, products: str) -> bool:
    if re.search(
        r"\b(?:farm|farms|farmstead|ranch|orchard|apiary|vineyard|dairy|creamery|cattle|"
        r"greenhouse|nursery|grower|homestead|pasture|livestock)\b",
        name,
        re.I,
    ):
        return True
    if re.search(
        r"\b(?:we|our family|family[- ]owned)\s+(?:grow|grows|raise|raises|farm|produce|harvest)|"
        r"\bour farm\b|\bfarm[- ]raised\b|\bgrown (?:here|on[- ]site|on our)\b",
        description,
        re.I,
    ):
        return True
    return bool(re.search(r"\b(?:you pick|pick your own|farm tours?|pumpkin patch|hay rides?|csa)\b", products, re.I))


def farm_entity_confirmation(name: str, description: str, products: str) -> bool:
    """Require farm-operation evidence and route obvious adjacent entities to QA."""
    if re.search(
        r"\b(?:processing|processor|farm supply|peanut supply|farmers? association|coalition|museum|market and grill|wholesale)\b",
        name,
        re.I,
    ):
        return False
    # A producer may sell exclusively through a farmers market.  An official
    # agricultural-vendor classification is therefore positive scope evidence;
    # the market venue itself is not the farm entity, but the named vendor is.
    if re.search(r"\bagricultural\s+farmers?-market\s+vendor\b", description, re.I):
        return True
    if farm_operation_signal(name, description, products):
        return True
    return bool(re.search(
        r"\b(?:produce|vegetables?|fruit|berries|melons?|cattle|beef|pork|poultry|eggs?|milk|dairy|"
        r"honey|pecans?|nursery plants?|flowers?|christmas trees?|pumpkin patch|agritourism|"
        r"crawfish|seafood|shrimp|oysters?|fish)\b",
        f"{description} {products}",
        re.I,
    ))


def georgia_grown_cards(body: str) -> list[dict[str, str]]:
    """Parse the ten-or-fewer cards exposed on one Georgia Grown page."""
    headings = list(re.finditer(r'<h3 class="titleSmall">(.*?)</h3>', body, re.I | re.S))
    cards: list[dict[str, str]] = []
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else min(len(body), match.end() + 3500)
        segment = body[match.end():end]
        url_match = re.search(r'href="(https://georgiagrown\.com/member/[^"?]+/)"', segment, re.I)
        if not url_match:
            continue
        description_match = re.search(r'<p class="paragraph">(.*?)</p>', segment, re.I | re.S)
        phone_match = re.search(r'<p class="phone-number">.*?</strong>\s*(.*?)</p>', segment, re.I | re.S)
        email_match = re.search(r'<p class="email-address">.*?</strong>\s*(.*?)</p>', segment, re.I | re.S)
        categories_match = re.search(r'<strong>Business Categories:</strong>\s*(.*?)</p>', segment, re.I | re.S)
        cards.append({
            "name": strip_tags(match.group(1)),
            "url": clean_url(url_match.group(1)),
            "description": strip_tags(description_match.group(1)) if description_match else "",
            "phone": strip_tags(phone_match.group(1)) if phone_match else "",
            "email": strip_tags(email_match.group(1)) if email_match else "",
            "categories": strip_tags(categories_match.group(1)) if categories_match else "",
        })
    return cards


def georgia_grown_profile(
    state: str,
    config: dict[str, Any],
    card: dict[str, str],
    body: str,
) -> tuple[Observation, dict[str, Any]]:
    source_name = config["official_aggregate_name"]
    profile_match = re.search(r'<section class="bg-white primary">(.*?)</section>', body, re.I | re.S)
    profile = profile_match.group(1) if profile_match else body
    name_match = re.search(r'<h1 class="title">(.*?)</h1>', profile, re.I | re.S)
    name = strip_tags(name_match.group(1)) if name_match else clean_text(card.get("name"))
    description_match = re.search(
        r'gg_member_profile_single--description--company--info.*?<p class="paragraph">(.*?)</p>',
        profile,
        re.I | re.S,
    )
    description = strip_tags(description_match.group(1)) if description_match else clean_text(card.get("description"))
    products_match = re.search(r'Products or Services Offered</h3>(.*?)<!-- RELATED', profile, re.I | re.S)
    products_html = products_match.group(1) if products_match else ""
    product_values = [
        strip_tags(value)
        for value in re.findall(r'<(?:p class="cardTitle"|li)>(.*?)</(?:p|li)>', products_html, re.I | re.S)
    ]
    products = "; ".join(dict.fromkeys(value for value in product_values if value))
    location_match = re.search(
        r'<h3 class="largeLabel">Primary Location</h3>.*?<p class="paragraphSmall">(.*?)</p>',
        profile,
        re.I | re.S,
    )
    location_html = location_match.group(1) if location_match else ""
    location_lines = [
        strip_tags(value)
        for value in re.split(r'<br\s*/?>|</br>', location_html, flags=re.I)
        if strip_tags(value)
    ]
    city = postal = ""
    city_index = -1
    for index, value in enumerate(location_lines):
        city_match = re.search(r'([^,]+),\s*GA\s+(\d{5})(?:-\d{4})?\b', value, re.I)
        if city_match:
            city, postal, city_index = normalized_city(city_match.group(1)), city_match.group(2), index
            break
    address_lines = location_lines[:city_index] if city_index >= 0 else location_lines
    if address_lines and normalized_name(address_lines[0]) == normalized_name(name):
        address_lines = address_lines[1:]
    address = ", ".join(address_lines)
    contact_match = re.search(
        r'<h3 class="largeLabel">Contact</h3>(.*?)(?:<h3 class="largeLabel">Primary Location</h3>|</div>)',
        profile,
        re.I | re.S,
    )
    contact_html = contact_match.group(1) if contact_match else profile
    phone_match = re.search(r'(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-./ ]\d{3}[-./ ]\d{4}(?!\d)', strip_tags(contact_html))
    email_match = re.search(r'href="mailto:([^"?]+)', contact_html, re.I)
    website_match = re.search(r'<a href="(https?://[^"]+)" class="btn"[^>]*>Visit Website</a>', profile, re.I)
    links = re.findall(r'href="(https?://[^" ]+)"', profile, re.I)
    website, facebook, instagram, tiktok = split_public_links(links, "georgiagrown.com")
    if website_match:
        website = clean_url(website_match.group(1))
    confirmed = farm_operation_signal(name, description, products)
    url = card["url"]
    record_id = url.rstrip("/").rsplit("/", 1)[-1]
    row = empty_observation(state, source_name, record_id, name, url, 1, "B")
    row.update({
        "entity_type_source": "Georgia Grown member",
        "entity_type_review": "farm_activity_confirmed_by_current_official_profile" if confirmed else "official_agriculture_member_requires_farm_operation_review",
        "city": city,
        "postal_code": postal,
        "address": address,
        "location_precision": "official_directory_public_business_address_or_city" if (address or city) else "official_profile_no_public_location",
        "phone": phone_match.group(0) if phone_match else clean_text(card.get("phone")),
        "email": clean_text(email_match.group(1)) if email_match else clean_text(card.get("email")),
        "products": products or (description[:700] if confirmed else ""),
        "business_types": clean_text(card.get("categories")) or "Georgia Grown member",
        "website_url": website,
        "facebook_url": facebook,
        "instagram_url": instagram,
        "tiktok_url": tiktok,
        "on_farm_sales": bool(re.search(r"direct to consumer|farm stand|u-pick|pick your own", f"{products} {description}", re.I)),
        "online_sales": bool(website and re.search(r"online|shipping|shop", description, re.I)),
        "u_pick": bool(re.search(r"u-pick|pick your own", f"{products} {description}", re.I)),
        "notes": description[:1500],
    })
    return Observation(**row), {
        "url": url,
        "name": name,
        "description": description,
        "products": products,
        "address": address,
        "city": city,
        "postal_code": postal,
        "profile_available": bool(name_match),
    }


def georgia_grown(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = config["official_aggregate_name"]
    first_body, first_log = fetch(config["official_directory"])
    logs: list[dict[str, Any]] = []
    page_bodies: dict[int, str] = {1: first_body}
    page_logs: dict[int, dict[str, Any]] = {1: first_log}

    def load_page(page: int) -> str:
        if page not in page_bodies:
            url = config["official_directory"] if page == 1 else f"{config['official_directory']}page/{page}/"
            page_bodies[page], page_logs[page] = fetch(url)
        return page_bodies[page]

    # WordPress exposes only next-page links. Probe exponentially, then binary
    # search the final nonempty page so the traversal does not hard-code a count.
    lower, upper = 1, 2
    while georgia_grown_cards(load_page(upper)):
        lower, upper = upper, upper * 2
    while lower + 1 < upper:
        middle = (lower + upper) // 2
        if georgia_grown_cards(load_page(middle)):
            lower = middle
        else:
            upper = middle
    last_page = lower
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(fetch, f"{config['official_directory']}page/{page}/"): page
            for page in range(2, last_page + 1)
            if page not in page_bodies
        }
        for future in as_completed(futures):
            page = futures[future]
            try:
                page_bodies[page], page_logs[page] = future.result()
            except Exception as exc:
                page_bodies[page] = ""
                page_logs[page] = {"url": f"{config['official_directory']}page/{page}/", "error": str(exc), "attempts_used": 0}

    cards_by_url: dict[str, dict[str, str]] = {}
    page_counts: dict[int, int] = {}
    for page in range(1, last_page + 1):
        cards = georgia_grown_cards(page_bodies.get(page, ""))
        page_counts[page] = len(cards)
        for card in cards:
            cards_by_url.setdefault(card["url"], card)
        logs.append(logged(page_logs[page], 1, f"{source_name} — directory page", len(cards), "request_component", f"Page {page} of {last_page}"))
    for page in sorted(set(page_bodies) - set(range(1, last_page + 1))):
        logs.append(logged(page_logs[page], 1, f"{source_name} — boundary probe", len(georgia_grown_cards(page_bodies[page])), "request_component"))

    observations: list[Observation] = []
    profiles: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    profile_logs: list[dict[str, Any]] = []

    def retain(card: dict[str, str], body: str) -> bool:
        observation, profile = georgia_grown_profile(state, config, card, body)
        if not observation.farm_name:
            return False
        observations.append(observation)
        profiles.append(profile)
        if len(observations) % 100 == 0:
            print(f"{state} official profiles retained: {len(observations)}/{len(cards_by_url)}", flush=True)
        return True

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, url, 3, 35): card for url, card in cards_by_url.items()}
        for future in as_completed(futures):
            card = futures[future]
            try:
                body, request_log = future.result()
            except Exception as exc:
                body, request_log = "", {"url": card["url"], "error": str(exc), "attempts_used": 0}
            kept = retain(card, body)
            profile_logs.append(logged(request_log, 1, f"{source_name} — profile request", int(kept), "request_component"))
            if not kept or not body:
                failed.append(card)

    # Named search cards are durable fallback evidence. A profile outage must
    # create missing fields and QA, never an omitted farm/member name.
    for card in failed:
        if any(item.source_url == card["url"] for item in observations):
            continue
        observation, profile = georgia_grown_profile(state, config, card, "")
        observation.notes = f"Official profile unavailable after retries; retained from current official directory card. {observation.notes}"[:1500]
        observations.append(observation)
        profiles.append({**profile, "official_card_fallback": True})
    logs.extend(profile_logs)
    aggregate = logged(
        first_log,
        1,
        source_name,
        len(observations),
        "observations_retained",
        f"Traversed {last_page} live pages and retained every one of {len(cards_by_url)} unique named member profiles; nonfarm member types remain QA candidates.",
    )
    incomplete = [page for page in range(1, last_page) if page_counts.get(page) != 10]
    final_count = page_counts.get(last_page, 0)
    if incomplete or not 1 <= final_count <= 10 or len(observations) != len(cards_by_url):
        aggregate["error"] = (
            f"Directory pages expected 10 records before final; incomplete pages {incomplete}; "
            f"final page {final_count}; unique URLs {len(cards_by_url)}; retained {len(observations)}"
        )
    logs.append(aggregate)
    return observations, logs, {"georgia_grown_profiles": profiles, "georgia_grown_page_counts": page_counts}


def georgia_farm_markets(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "Georgia Farm Bureau — Certified Farm Markets"
    body, landing_log = fetch(config["farm_markets"])
    marker_matches = re.finditer(
        r'lat:\s*([-0-9.]+),\s*lon:\s*([-0-9.]+),.*?labelURL:\s*"([^"]+)"',
        body,
        re.I | re.S,
    )
    indexed: dict[str, tuple[float, float]] = {}
    for match in marker_matches:
        url = urllib.parse.urljoin("https://www.gfb.org", match.group(3))
        indexed[url] = (float(match.group(1)), float(match.group(2)))
    observations: list[Observation] = []
    profiles: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, url): (url, coords) for url, coords in indexed.items()}
        for future in as_completed(futures):
            url, coords = futures[future]
            try:
                profile, request_log = future.result()
            except Exception as exc:
                profile, request_log = "", {"url": url, "error": str(exc), "attempts_used": 0}
            main_match = re.search(r'<section class="col-md-8 col-lg-9">(.*?)</section>', profile, re.I | re.S)
            main = main_match.group(1) if main_match else profile
            name_match = re.search(r'<h1>(.*?)</h1>', main, re.I | re.S)
            name = strip_tags(name_match.group(1)) if name_match else url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()
            address_match = re.search(r'<address>(.*?)</address>', main, re.I | re.S)
            address_html = address_match.group(1) if address_match else ""
            address_lines = [strip_tags(value) for value in re.split(r'<br\s*/?>', address_html, flags=re.I) if strip_tags(value)]
            city = postal = ""
            city_index = -1
            for index, value in enumerate(address_lines):
                city_match = re.search(r'([^,]+),\s*GA\b', value, re.I)
                zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', value)
                if city_match:
                    city, city_index = normalized_city(city_match.group(1)), index
                if zip_match:
                    postal = zip_match.group(1)
            address = ", ".join(address_lines[:city_index] if city_index >= 0 else address_lines)
            if not postal:
                zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', strip_tags(address_html))
                postal = zip_match.group(1) if zip_match else ""
            phone_match = re.search(r'href="tel:([^"]+)', main, re.I)
            email_match = re.search(r'href="mailto:([^"?]+)', main, re.I)
            links = re.findall(r'href="(https?://[^" ]+)"', main, re.I)
            website, facebook, instagram, tiktok = split_public_links(links, "gfb.org")
            tags = [
                strip_tags(value) for value in re.findall(r'/connect/farm-markets/tag/[^"?]+">(.*?)</a>', main, re.I | re.S)
            ]
            tags = [value for value in tags if value not in {"All CFMs", "North Georgia", "Middle Georgia", "South Georgia"}]
            info_match = re.search(r'<h3>Market Info</h3>.*?<div class="bg-light p-3 border">(.*?)</div>', main, re.I | re.S)
            description = strip_tags(info_match.group(1)) if info_match else ""
            row = empty_observation(state, source_name, url.rstrip("/").rsplit("/", 1)[-1], name, url, 2, "C")
            row.update({
                "entity_type_source": "Certified Farm Market",
                "entity_type_review": "farm_activity_confirmed_by_current_farm_bureau_certification",
                "city": city,
                "postal_code": postal,
                "address": address,
                "latitude": coords[0],
                "longitude": coords[1],
                "location_precision": "association_directory_public_business_location",
                "phone": clean_text(phone_match.group(1)) if phone_match else "",
                "email": clean_text(email_match.group(1)) if email_match else "",
                "products": "; ".join(dict.fromkeys(tags)) or description or "Farm products sold direct to consumers",
                "business_types": "Georgia Farm Bureau Certified Farm Market",
                "website_url": website,
                "facebook_url": facebook,
                "instagram_url": instagram,
                "tiktok_url": tiktok,
                "on_farm_sales": True,
                "online_sales": any("Online Store" == value for value in tags),
                "u_pick": any("U-Pick" == value for value in tags),
                "notes": description[:1500],
            })
            observations.append(Observation(**row))
            profiles.append({"url": url, "name": name, "address": address_lines, "tags": tags, "description": description})
            logs.append(logged(request_log, 2, f"{source_name} — profile request", int(bool(profile)), "request_component"))
    aggregate = logged(
        landing_log,
        2,
        source_name,
        len(observations),
        "observations_retained",
        f"The All CFMs map exposed {len(indexed)} unique certified market detail pages; each named market was retained.",
    )
    if len(observations) != len(indexed):
        aggregate["error"] = f"Certified market index exposed {len(indexed)} detail URLs; retained {len(observations)}"
    logs.append(aggregate)
    return observations, logs, {"georgia_farm_bureau_certified_markets": profiles}


def next_page_data(body: str) -> dict[str, Any]:
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', body, re.I | re.S)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
        return value.get("props", {}).get("pageProps", {})
    except (json.JSONDecodeError, TypeError):
        return {}


def florida_producer_cards(body: str) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for article in re.findall(r'<article class="card:producer">(.*?)</article>', body, re.I | re.S):
        match = re.search(
            r'<h3 class="card:producer::heading">\s*<a href="(https://flfarmtoyou\.com/producer/[^"?]+/)">(.*?)</a>',
            article,
            re.I | re.S,
        )
        if not match:
            continue
        cards.append({"url": clean_url(match.group(1)), "name": strip_tags(match.group(2))})
    return cards


def florida_farm_to_you_profile(
    state: str,
    config: dict[str, Any],
    card: dict[str, str],
    body: str,
) -> tuple[Observation, dict[str, Any]]:
    source_name = config["official_aggregate_name"]
    main_match = re.search(r'<main class="view:producer@single">(.*?)</main>', body, re.I | re.S)
    main = main_match.group(1) if main_match else body
    name_match = re.search(r'<h2 class="block:producer::heading">(.*?)</h2>', main, re.I | re.S)
    name = strip_tags(name_match.group(1)) if name_match else card["name"]
    description_match = re.search(r'<div class="block:producer::content">(.*?)</div>', main, re.I | re.S)
    description = strip_tags(description_match.group(1)) if description_match else ""
    service_match = re.search(r'<section class="block:services">(.*?)</section>', main, re.I | re.S)
    service_html = service_match.group(1) if service_match else ""
    product_values = [strip_tags(value) for value in re.findall(r'<strong>(.*?)</strong>', service_html, re.I | re.S)]
    if not product_values:
        product_values = [strip_tags(value) for value in re.findall(r'<h4 class="card:service::heading">(.*?)</h4>', service_html, re.I | re.S)]
    products = "; ".join(dict.fromkeys(value for value in product_values if value))
    address_match = re.search(r'<address class="card:producer@location::address">(.*?)</address>', main, re.I | re.S)
    address_html = address_match.group(1) if address_match else ""
    address_lines = [strip_tags(value) for value in re.split(r'<br\s*/?>', address_html, flags=re.I) if strip_tags(value)]
    city = postal = ""
    city_index = -1
    for index, value in enumerate(address_lines):
        city_match = re.search(r'([^,]+),\s*FL\s+(\d{5})(?:-\d{4})?\b', value, re.I)
        if city_match:
            city, postal, city_index = normalized_city(city_match.group(1)), city_match.group(2), index
            break
    address = ", ".join(address_lines[:city_index] if city_index >= 0 else address_lines)
    phone_match = re.search(r'href="tel:([^"]+)', main, re.I)
    email_match = re.search(r'href="(?:mailto?|mail):([^"?]+)', main, re.I)
    action_match = re.search(r'<div class="block:producer::actions">(.*?)</div>', main, re.I | re.S)
    action_html = action_match.group(1) if action_match else ""
    links = re.findall(r'href="(https?://[^" ]+)"', action_html, re.I)
    website, facebook, instagram, tiktok = split_public_links(links, "flfarmtoyou.com")
    confirmed = farm_operation_signal(name, description, products)
    url = card["url"]
    row = empty_observation(state, source_name, url.rstrip("/").rsplit("/", 1)[-1], name, url, 1, "B")
    row.update({
        "entity_type_source": "Florida Farm to You producer",
        "entity_type_review": "farm_activity_confirmed_by_current_official_profile" if confirmed else "official_producer_profile_requires_farm_operation_review",
        "city": city,
        "postal_code": postal,
        "address": address,
        "location_precision": "official_directory_public_business_address_or_city" if (address or city) else "official_profile_no_public_location",
        "phone": clean_text(phone_match.group(1)) if phone_match else "",
        "email": clean_text(email_match.group(1)) if email_match else "",
        "products": products or (description[:700] if confirmed else ""),
        "business_types": "Florida producer profile",
        "website_url": website,
        "facebook_url": facebook,
        "instagram_url": instagram,
        "tiktok_url": tiktok,
        "on_farm_sales": bool(re.search(r"direct to consumer|farm stand|u-pick|pick your own", f"{service_html} {description}", re.I)),
        "online_sales": bool(action_html),
        "u_pick": bool(re.search(r"u-pick|pick your own", f"{products} {description}", re.I)),
        "notes": description[:1500],
    })
    return Observation(**row), {
        "url": url,
        "name": name,
        "description": description,
        "products": products,
        "address": address,
        "city": city,
        "postal_code": postal,
        "profile_available": bool(name_match),
    }


def florida_farm_to_you(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = config["official_aggregate_name"]
    first_body, first_log = fetch(config["official_directory"])
    pages = max([1] + [int(value) for value in re.findall(r'/producer/page/(\d+)/', first_body)])
    page_bodies: dict[int, str] = {1: first_body}
    page_logs: dict[int, dict[str, Any]] = {1: first_log}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(fetch, f"{config['official_directory']}page/{page}/"): page
            for page in range(2, pages + 1)
        }
        for future in as_completed(futures):
            page = futures[future]
            try:
                page_bodies[page], page_logs[page] = future.result()
            except Exception as exc:
                page_bodies[page], page_logs[page] = "", {"url": config["official_directory"], "error": str(exc), "attempts_used": 0}
    cards: dict[str, dict[str, str]] = {}
    logs: list[dict[str, Any]] = []
    page_counts: dict[int, int] = {}
    for page in range(1, pages + 1):
        found = florida_producer_cards(page_bodies.get(page, ""))
        page_counts[page] = len(found)
        for card in found:
            cards.setdefault(card["url"], card)
        logs.append(logged(page_logs[page], 1, f"{source_name} — directory page", len(found), "request_component", f"Page {page} of {pages}"))
    observations: list[Observation] = []
    profiles: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, url): card for url, card in cards.items()}
        for future in as_completed(futures):
            card = futures[future]
            try:
                body, request_log = future.result()
            except Exception as exc:
                body, request_log = "", {"url": card["url"], "error": str(exc), "attempts_used": 0}
            observation, profile = florida_farm_to_you_profile(state, config, card, body)
            if not body:
                observation.notes = "Official profile unavailable after retries; named archive card retained with missing fields in QA."
                profile["official_card_fallback"] = True
            observations.append(observation); profiles.append(profile)
            logs.append(logged(request_log, 1, f"{source_name} — profile request", int(bool(body)), "request_component"))
    aggregate = logged(
        first_log,
        1,
        source_name,
        len(observations),
        "observations_retained",
        f"Traversed {pages} live archive pages and retained {len(cards)} unique named producer profiles.",
    )
    nonfinal = [page for page in range(1, pages) if page_counts.get(page) != 9]
    if nonfinal or not 1 <= page_counts.get(pages, 0) <= 9 or len(observations) != len(cards):
        aggregate["error"] = (
            f"Expected nine records on nonfinal pages; incomplete {nonfinal}; final {page_counts.get(pages, 0)}; "
            f"unique profiles {len(cards)}; retained {len(observations)}"
        )
    logs.append(aggregate)
    return observations, logs, {"florida_farm_to_you_profiles": profiles, "florida_farm_to_you_page_counts": page_counts}


def florida_fdacs_lists(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    observations: list[Observation] = []
    logs: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}

    upick_name = "Florida Department of Agriculture and Consumer Services — U-pick farm locator"
    upick_body, upick_log = fetch(config["fdacs_upick"])
    upick_data = next_page_data(upick_body)
    children = upick_data.get("childrenInfos") if isinstance(upick_data.get("childrenInfos"), list) else []
    cards = {
        clean_url(item.get("props", {}).get("url")): {
            "url": clean_url(item.get("props", {}).get("url")),
            "name": clean_text(item.get("props", {}).get("name")),
            "content_id": clean_text(item.get("contentId")),
        }
        for item in children
        if clean_url(item.get("props", {}).get("url")) and clean_text(item.get("props", {}).get("name"))
    }
    upick_profiles: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, url): card for url, card in cards.items()}
        for future in as_completed(futures):
            card = futures[future]
            try:
                body, request_log = future.result()
            except Exception as exc:
                body, request_log = "", {"url": card["url"], "error": str(exc), "attempts_used": 0}
            page = next_page_data(body).get("pageData", {}) if body else {}
            name = clean_text(page.get("locationName") or page.get("_name") or card["name"])
            website, facebook, instagram, tiktok = split_public_links([clean_text(page.get("website"))], "fdacs.gov")
            row = empty_observation(state, upick_name, card["content_id"] or card["url"], name, card["url"], 2, "B")
            row.update({
                "entity_type_source": "FDACS-listed U-pick farm",
                "entity_type_review": "farm_activity_confirmed_by_current_official_u_pick_list",
                "county": normalized_county(page.get("county", "")),
                "county_source": card["url"] if page.get("county") else "",
                "city": normalized_city(page.get("city", "")),
                "postal_code": clean_text(page.get("zip")),
                "address": clean_text(page.get("address")),
                "latitude": page.get("geolocation", {}).get("latitude") if isinstance(page.get("geolocation"), dict) else None,
                "longitude": page.get("geolocation", {}).get("longitude") if isinstance(page.get("geolocation"), dict) else None,
                "location_precision": "official_directory_public_business_address_or_city",
                "phone": clean_text(page.get("phone")),
                "email": clean_text(page.get("email")),
                "products": "U-pick crops; agritourism",
                "business_types": "FDACS U-pick farm",
                "website_url": website,
                "facebook_url": facebook,
                "instagram_url": instagram,
                "tiktok_url": tiktok,
                "on_farm_sales": True,
                "u_pick": True,
                "notes": strip_tags(page.get("additionalInformation", {}).get("html5", ""))[:1500] if isinstance(page.get("additionalInformation"), dict) else "",
            })
            observations.append(Observation(**row))
            upick_profiles.append({"url": card["url"], "name": name, "page_data": page})
            logs.append(logged(request_log, 2, f"{upick_name} — profile request", int(bool(page)), "request_component"))
    upick_aggregate = logged(
        upick_log,
        2,
        upick_name,
        len(cards),
        "observations_retained",
        f"The live FDACS page exposed {len(children)} child profiles; every unique named profile was retained.",
    )
    if len(children) != len(cards) or sum(item.source_name == upick_name for item in observations) != len(cards):
        upick_aggregate["error"] = f"FDACS children {len(children)}; unique named profiles {len(cards)}; retained {sum(item.source_name == upick_name for item in observations)}"
    logs.append(upick_aggregate); raw["fdacs_u_pick_profiles"] = upick_profiles

    csa_name = "Florida Department of Agriculture and Consumer Services — CSA locator"
    csa_body, csa_log = fetch(config["fdacs_csa"])
    csa_page = next_page_data(csa_body).get("pageData", {})
    description = csa_page.get("description", {}).get("html5", "") if isinstance(csa_page.get("description"), dict) else ""
    headings = list(re.finditer(r'<h3[^>]*>(.*?)</h3>\s*<ul[^>]*>(.*?)</ul>', description, re.I | re.S))
    csa_records: list[dict[str, Any]] = []
    for heading in headings:
        county = normalized_county(strip_tags(heading.group(1)))
        for item_html in re.findall(r'<li[^>]*>(.*?)</li>', heading.group(2), re.I | re.S):
            text_value = strip_tags(item_html)
            link_match = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', item_html, re.I | re.S)
            name = strip_tags(link_match.group(2)) if link_match else text_value.split(",", 1)[0]
            rest = text_value[len(name):].lstrip(" ,")
            phone_match = re.search(r'(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-./ ]\d{3}[-./ ]\d{4}(?!\d)', text_value)
            city = rest.split(",", 1)[0].strip() if rest else ""
            link = clean_url(link_match.group(1)) if link_match else ""
            website, facebook, instagram, tiktok = split_public_links([link], "fdacs.gov")
            row = empty_observation(state, csa_name, f"{slug(county)}-{len(csa_records) + 1}", name, config["fdacs_csa"], 2, "B")
            row.update({
                "entity_type_source": "FDACS-listed community-supported agriculture operation",
                "entity_type_review": "farm_activity_confirmed_by_current_official_csa_list",
                "county": county,
                "county_source": config["fdacs_csa"],
                "city": normalized_city(city),
                "location_precision": "official_directory_county_and_city",
                "phone": phone_match.group(0) if phone_match else "",
                "products": "Community-supported agriculture farm share",
                "business_types": "CSA; direct-to-consumer farm",
                "website_url": website,
                "facebook_url": facebook,
                "instagram_url": instagram,
                "tiktok_url": tiktok,
                "on_farm_sales": True,
                "notes": text_value[:1500],
            })
            observations.append(Observation(**row)); csa_records.append({"name": name, "county": county, "city": city, "text": text_value, "link": link})
    logs.append(logged(csa_log, 2, csa_name, len(csa_records), "observations_retained", "Every named row under the live county headings was retained."))
    raw["fdacs_csa_records"] = csa_records
    return observations, logs, raw


def us_farm_trail_records(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = f"US Farm Trail — {config['name']} discovery export"
    state_body, state_log = fetch(config["us_farm_trail"])
    geo_body, geo_log = fetch(config["us_farm_trail_geojson"])
    advertised_match = re.search(r'([\d,]+) farms selling direct to consumers', strip_tags(state_body), re.I)
    advertised = int(advertised_match.group(1).replace(",", "")) if advertised_match else 0
    try:
        features = json.loads(geo_body).get("features", [])
    except json.JSONDecodeError:
        features = []
    rows: dict[str, dict[str, Any]] = {}
    for feature in features:
        props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else {}
        slug_value = clean_text(props.get("slug"))
        if slug_value and clean_text(props.get("name")):
            rows[slug_value] = {"properties": props, "coordinates": geometry.get("coordinates", [])}
    # The public state card list can expose named records without coordinates,
    # which the map GeoJSON omits. Preserve those names as missing-location QA.
    for match in re.finditer(r'<a[^>]*href="/farms/([^"?#]+)"[^>]*>\s*<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>', state_body, re.I | re.S):
        slug_value, name, city = match.group(1), strip_tags(match.group(2)), strip_tags(match.group(3))
        rows.setdefault(slug_value, {"properties": {"id": slug_value, "slug": slug_value, "name": name, "city": city, "types": "", "verified": False}, "coordinates": []})
    confirmed_types = {
        "produce", "farm-stand", "organic", "u-pick", "csa", "honey", "meat", "livestock",
        "nursery", "pumpkin-patch", "poultry", "eggs", "orchard", "dairy", "corn-maze", "christmas-trees",
    }
    observations: list[Observation] = []
    raw_rows: list[dict[str, Any]] = []
    for slug_value, value in sorted(rows.items()):
        props = value["properties"]; coordinates = value["coordinates"]
        types = {clean_text(item) for item in clean_text(props.get("types")).split(",") if clean_text(item)}
        name = clean_text(props.get("name")); city = normalized_city(props.get("city", ""))
        confirmed = bool(types & confirmed_types) or farm_operation_signal(name, "", "; ".join(types))
        url = f"https://www.usfarmtrail.com/farms/{slug_value}"
        row = empty_observation(state, source_name, clean_text(props.get("id")) or slug_value, name, url, 3, "C" if props.get("verified") else "E")
        row.update({
            "entity_type_source": "US Farm Trail directory record",
            "entity_type_review": "farm_activity_confirmed_by_directory_type" if confirmed else "discovery_directory_record_requires_farm_operation_review",
            "city": city,
            "latitude": float(coordinates[1]) if isinstance(coordinates, list) and len(coordinates) >= 2 else None,
            "longitude": float(coordinates[0]) if isinstance(coordinates, list) and len(coordinates) >= 2 else None,
            "location_precision": "directory_coordinate_and_city" if len(coordinates) >= 2 else "directory_city_or_missing_location",
            "products": "; ".join(sorted(types)),
            "business_types": "US Farm Trail discovery record",
            "on_farm_sales": "farm-stand" in types,
            "u_pick": "u-pick" in types,
            "notes": "Directory states that most listings are compiled from public sources; unverified records require corroboration." if not props.get("verified") else "Directory record is marked verified by the listing manager.",
        })
        observations.append(Observation(**row)); raw_rows.append({"slug": slug_value, **value})
    aggregate = logged(
        geo_log,
        3,
        source_name,
        len(observations),
        "observations_retained",
        f"State headline advertised {advertised}; GeoJSON exposed {len(features)} coordinate-bearing records and visible state cards added {len(rows) - len(features)} name-only records. One headline-count record was not publicly enumerable and remains a documented source limitation.",
    )
    if not features or len(observations) < len(features):
        aggregate["error"] = f"GeoJSON features {len(features)}; retained {len(observations)}"
    return observations, [logged(state_log, 3, f"{source_name} — state index", advertised, "request_component"), aggregate], {"us_farm_trail_records": raw_rows, "us_farm_trail_advertised": advertised}


def picktn_profile_observation(
    state: str,
    config: dict[str, Any],
    indexed: dict[str, Any],
    body: str,
) -> tuple[Observation, dict[str, Any]]:
    raw = indexed.get("raw") if isinstance(indexed.get("raw"), dict) else {}
    url = clean_text(indexed.get("uri") or raw.get("uri"))
    name = meta_value(body, "businessName") or clean_text(indexed.get("title"))
    county = normalized_county(meta_value(body, "county") or raw.get("tn_county", ""))
    city = normalized_city(meta_value(body, "city") or raw.get("tn_city", ""))
    postal = meta_value(body, "zipCode")
    product_text = meta_value(body, "productList") or clean_text(raw.get("tn_product_list"))
    products = "; ".join(dict.fromkeys(clean_text(value) for value in product_text.split("|") if clean_text(value)))
    description_match = re.search(
        r"<!-- Additional Information -->\s*<p>(.*?)</p>", body, re.I | re.S
    )
    description = strip_tags(description_match.group(1)) if description_match else ""
    location_match = re.search(
        r'detailsTitle">Location\(s\)</p>.*?<td>\s*<p>(.*?)</p>', body, re.I | re.S
    )
    location_html = location_match.group(1) if location_match else ""
    street = strip_tags(re.split(r"<br\s*/?>", location_html, maxsplit=1, flags=re.I)[0]) if location_html else ""
    phone_match = re.search(r'href="tel:([^"]+)"', body, re.I)
    email_match = re.search(r'href="mailto:([^"]+)"', body, re.I)
    title_start = body.find('<div class="tn-pagetitle')
    profile_end = body.find("</table>", title_start)
    profile_html = body[title_start:profile_end] if title_start >= 0 and profile_end > title_start else ""
    links = re.findall(r'href="(https?://[^" ]+)"', profile_html, re.I)
    website, facebook, instagram, tiktok = split_public_links(links, "picktnproducts.org")
    confirmed = farm_operation_signal(name, description, products)
    record_match = re.search(r"picktn-listing\.(\d+)\.html", url)
    record_id = record_match.group(1) if record_match else clean_text(raw.get("permanentid")) or url
    row = empty_observation(
        state, config["official_aggregate_name"], record_id, name, url,
        1, "B",
    )
    method_match = re.search(
        r'detailsTitle">Method of Sale</p>.*?<td>(.*?)</td>', body, re.I | re.S
    )
    methods = strip_tags(method_match.group(1)) if method_match else ""
    row.update({
        "entity_type_source": "Pick Tennessee Products member",
        "entity_type_review": "farm_activity_confirmed_by_current_official_profile" if confirmed else "official_agriculture_member_requires_farm_operation_review",
        "county": county, "county_source": url, "city": city, "postal_code": postal,
        "address": street, "location_precision": "official_directory_public_business_address_or_city",
        "contact_name": meta_value(body, "contactName"),
        "phone": clean_text(phone_match.group(1)) if phone_match else "",
        "email": clean_text(email_match.group(1)) if email_match else "",
        "products": products, "business_types": "Pick Tennessee Products member",
        "website_url": website, "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
        "on_farm_sales": bool(re.search(r"on farm sale|farm stand|pick your own", methods, re.I)),
        "farmers_market_sales": bool(re.search(r"farmers market", methods, re.I)),
        "online_sales": bool(re.search(r"online|shipping", methods, re.I)),
        "local_delivery": bool(re.search(r"deliver", methods, re.I)),
        "u_pick": bool(re.search(r"pick your own|you pick", f"{methods} {products}", re.I)),
        "wholesale": bool(re.search(r"wholesale", methods, re.I)),
        "retail_sales": bool(re.search(r"retail", methods, re.I)),
        "restaurant_sales": bool(re.search(r"restaurant", methods, re.I)),
        "notes": (description or "Official index record retained; profile detail was unavailable.")[:1500],
    })
    summary = {
        "url": url, "name": name, "county": county, "city": city, "postal_code": postal,
        "products": products, "description": description, "methods": methods,
        "profile_available": bool(body),
    }
    return Observation(**row), summary


def tennessee_picktn(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = config["official_aggregate_name"]
    landing, landing_log = fetch(config["official_directory"])
    token_match = re.search(r'accessToken:\s*"([^"]+)', landing)
    org_match = re.search(r'organizationId:\s*"([^"]+)', landing)
    if not token_match or not org_match:
        return [], [logged(landing_log, 1, source_name, 0, "unreachable_after_3_attempts", "Coveo public search credentials missing")], {}
    token, organization = token_match.group(1), org_match.group(1)
    endpoint = f"https://platform.cloud.coveo.com/rest/search/v2?organizationId={organization}"
    indexed_by_url: dict[str, dict[str, Any]] = {}
    logs: list[dict[str, Any]] = []
    facet_payload = {
        "q": "", "aq": "@uri=*picktn-producers*", "searchHub": "PickTN",
        "numberOfResults": 0,
        "facets": [{
            "facetId": "tn_county", "field": "tn_county", "type": "specific",
            "numberOfValues": 100, "sortCriteria": "alphanumeric",
        }],
    }
    facet_response, facet_log = post_json(endpoint, facet_payload, token)
    advertised_index_results = int(facet_response.get("totalCount") or 0)
    facets = facet_response.get("facets") if isinstance(facet_response.get("facets"), list) else []
    county_values = facets[0].get("values", []) if facets and isinstance(facets[0].get("values"), list) else []
    logs.append(logged(facet_log, 1, f"{source_name} — county partition index", len(county_values), "request_component", f"Advertised total {advertised_index_results}"))
    result_occurrences = 0
    expected_profiles = sum(int(value.get("numberOfResults") or 0) for value in county_values)
    partition_errors: list[str] = []
    for county_value in county_values:
        county = clean_text(county_value.get("value"))
        advertised_count = int(county_value.get("numberOfResults") or 0)
        escaped_county = county.replace('"', '\\"')
        payload = {
            "q": "", "aq": f'@uri=*picktn-producers* AND @tn_county=="{escaped_county}"',
            "searchHub": "PickTN", "numberOfResults": max(1, advertised_count), "firstResult": 0,
        }
        response, request_log = post_json(endpoint, payload, token)
        results = response.get("results") if isinstance(response.get("results"), list) else []
        result_occurrences += len(results)
        logs.append(logged(request_log, 1, f"{source_name} — county index partition", len(results), "request_component", f"{county} County; advertised {advertised_count}"))
        if len(results) != advertised_count:
            partition_errors.append(f"{county}: advertised {advertised_count}, received {len(results)}")
        for result in results:
            url = clean_text(result.get("uri"))
            if url:
                indexed_by_url[url] = result

    unassigned_payload = {
        "q": "", "aq": '@uri=*picktn-producers* AND @tn_county==""',
        "searchHub": "PickTN", "numberOfResults": 100, "firstResult": 0,
    }
    unassigned_response, unassigned_log = post_json(endpoint, unassigned_payload, token)
    unassigned_results = unassigned_response.get("results") if isinstance(unassigned_response.get("results"), list) else []
    valid_unassigned = [
        result for result in unassigned_results
        if re.search(r"/picktn-producers/picktn-listing\.\d+\.html$", clean_text(result.get("uri")))
    ]
    non_profile_results = len(unassigned_results) - len(valid_unassigned)
    expected_profiles += len(valid_unassigned)
    result_occurrences += len(valid_unassigned)
    logs.append(logged(
        unassigned_log, 1, f"{source_name} — unassigned-county index partition",
        len(valid_unassigned), "request_component",
        f"{non_profile_results} non-profile index pages ignored; named profile records retained.",
    ))
    for result in valid_unassigned:
        indexed_by_url[clean_text(result.get("uri"))] = result

    observations: list[Observation] = []
    profiles: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = {executor.submit(fetch, url, 3, 35): indexed for url, indexed in indexed_by_url.items()}
        for future in as_completed(futures):
            indexed = futures[future]
            url = clean_text(indexed.get("uri"))
            try:
                body, request_log = future.result()
            except Exception as exc:
                body, request_log = "", {"url": url, "error": str(exc), "attempts_used": 0}
            observation, profile = picktn_profile_observation(state, config, indexed, body)
            observations.append(observation); profiles.append(profile)
            logs.append(logged(request_log, 1, f"{source_name} — profile request", int(bool(body)), "request_component"))
            if len(observations) % 250 == 0:
                print(f"{state} Pick Tennessee profiles retained: {len(observations)}/{len(indexed_by_url)}", flush=True)

    aggregate = logged(
        landing_log, 1, source_name, len(observations), "observations_retained",
        f"Public index advertised {advertised_index_results} results: {expected_profiles} producer profiles and "
        f"{non_profile_results} non-profile pages. {result_occurrences} profile results were traversed across "
        f"{len(county_values)} county partitions plus the unassigned-county partition.",
    )
    if advertised_index_results != expected_profiles + non_profile_results or expected_profiles != result_occurrences or result_occurrences != len(indexed_by_url) or len(observations) != len(indexed_by_url) or partition_errors:
        aggregate["error"] = (
            f"Pick Tennessee index advertised {advertised_index_results}; expected {expected_profiles} profiles plus "
            f"{non_profile_results} non-profile pages; traversed {result_occurrences} profile occurrences, "
            f"captured {len(indexed_by_url)} unique profile URLs, retained {len(observations)} observations, "
            f"partition errors: {partition_errors}"
        )
    logs.append(aggregate)
    return observations, logs, {
        "pick_tennessee_index": list(indexed_by_url.values()),
        "pick_tennessee_index_summary": {
            "advertised_index_results": advertised_index_results,
            "expected_profile_results": expected_profiles,
            "traversed_result_occurrences": result_occurrences,
            "unique_profile_urls": len(indexed_by_url),
            "county_partitions": len(county_values),
            "non_profile_index_pages": non_profile_results,
            "duplicate_index_entries": result_occurrences - len(indexed_by_url),
        },
        "pick_tennessee_profiles": profiles,
    }


def century_farm_rows(body: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for row_html in re.findall(r"<tr>(.*?)</tr>", body, re.I | re.S):
        values: dict[str, str] = {}
        for field in ("farm_name", "county", "date_founded", "special_recognition"):
            match = re.search(rf'<td class="{field}-field">(.*?)</td>', row_html, re.I | re.S)
            values[field] = strip_tags(match.group(1)) if match else ""
        if values["farm_name"]:
            records.append(values)
    return records


def tennessee_century_farms(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "Middle Tennessee State University — Tennessee Century Farms registry"
    first_url = f"{config['century_farms']}?listpage=1&instance=1"
    first_body, first_log = fetch(first_url)
    last_match = re.search(r'class="lastpage".*?listpage=(\d+)', first_body, re.I | re.S)
    pages = int(last_match.group(1)) if last_match else 1
    page_bodies: dict[int, str] = {1: first_body}
    logs = [logged(first_log, 2, f"{source_name} — registry page", len(century_farm_rows(first_body)), "request_component", f"Page 1 of {pages}")]
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(fetch, f"{config['century_farms']}?listpage={page}&instance=1"): page
            for page in range(2, pages + 1)
        }
        for future in as_completed(futures):
            page = futures[future]
            try:
                body, request_log = future.result()
            except Exception as exc:
                body, request_log = "", {"url": config["century_farms"], "error": str(exc), "attempts_used": 0}
            page_bodies[page] = body
            logs.append(logged(request_log, 2, f"{source_name} — registry page", len(century_farm_rows(body)), "request_component", f"Page {page} of {pages}"))
    records: list[dict[str, str]] = []
    page_counts: dict[int, int] = {}
    for page in sorted(page_bodies):
        page_rows = century_farm_rows(page_bodies[page])
        page_counts[page] = len(page_rows)
        records.extend(page_rows)
    expected = (pages - 1) * 10 + page_counts.get(pages, 0)
    observations: list[Observation] = []
    for index, record in enumerate(records, start=1):
        row = empty_observation(state, source_name, f"century-{index}", record["farm_name"], config["century_farms"], 2, "B")
        row.update({
            "entity_type_source": "Certified Tennessee Century Farm",
            "entity_type_review": "farm_identity_confirmed_by_current_university_registry",
            "county": normalized_county(record["county"]), "county_source": config["century_farms"],
            "business_types": "Century Farm; current sales and products require research",
            "notes": f"Certified historic farm founded {record['date_founded'] or 'date not exposed'}. {record['special_recognition']}".strip(),
        })
        observations.append(Observation(**row))
    aggregate = logged(
        first_log, 2, source_name, len(observations), "observations_retained",
        f"Registry advertised {expected} records across {pages} pages; all named rows retained without inventing current products or sale channels.",
    )
    incomplete_pages = [page for page in range(1, pages) if page_counts.get(page) != 10]
    if expected != len(observations) or incomplete_pages or not 1 <= page_counts.get(pages, 0) <= 10:
        aggregate["error"] = (
            f"Century Farms live pagination expected {expected}; parsed {len(observations)}; "
            f"incomplete non-final pages: {incomplete_pages}; final-page rows: {page_counts.get(pages, 0)}"
        )
    logs.append(aggregate)
    return observations, logs, {"tennessee_century_farms": records}


def tennessee_agritourism(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "Tennessee Agritourism Association — active farm members"
    body, landing_log = fetch(config["agritourism"])
    matches = list(re.finditer(r'<p class="elementor-heading-title[^>]*><a href="([^"]+)">(.*?)</a></p>', body, re.I | re.S))
    cards: dict[str, dict[str, str]] = {}
    for index, match in enumerate(matches):
        url = clean_url(match.group(1)); name = strip_tags(match.group(2))
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(body), match.end() + 2500)
        segment = body[match.end():end]
        city_match = re.search(r"([A-Za-z][A-Za-z .'-]{1,50}),\s*TN\b", strip_tags(segment), re.I)
        if url and name:
            cards[url] = {"url": url, "name": name, "city": normalized_city(city_match.group(1)) if city_match else ""}
    observations: list[Observation] = []
    profiles: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, url): card for url, card in cards.items()}
        for future in as_completed(futures):
            card = futures[future]
            try:
                profile_body, request_log = future.result()
            except Exception as exc:
                profile_body, request_log = "", {"url": card["url"], "error": str(exc), "attempts_used": 0}
            schema_match = re.search(r'<script type="application/ld\+json" class="yoast-schema-graph">(.*?)</script>', profile_body, re.I | re.S)
            article: dict[str, Any] = {}
            if schema_match:
                try:
                    graph = json.loads(html.unescape(schema_match.group(1))).get("@graph", [])
                    article = next((item for item in graph if item.get("@type") == "Article"), {})
                except (json.JSONDecodeError, TypeError):
                    article = {}
            description = meta_value(profile_body, "og:description", "property")
            categories = [clean_text(value) for value in article.get("articleSection", [])] if isinstance(article.get("articleSection"), list) else []
            links = re.findall(r'href="(https?://[^" ]+)"', profile_body, re.I)
            website, facebook, instagram, tiktok = split_public_links(links, "tennesseeagritourism.org")
            record_id = card["url"].rstrip("/").rsplit("/", 1)[-1]
            row = empty_observation(state, source_name, record_id, card["name"], card["url"], 2, "C")
            row.update({
                "entity_type_source": "Active agritourism farm member",
                "entity_type_review": "farm_activity_confirmed_by_current_association_member_profile",
                "city": card["city"], "products": "; ".join(categories) or description,
                "business_types": "Agritourism farm", "website_url": website,
                "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
                "on_farm_sales": True, "u_pick": any("pick-your-own" in value.casefold() for value in categories),
                "notes": description[:1500],
            })
            observations.append(Observation(**row))
            profiles.append({"url": card["url"], "name": card["name"], "city": card["city"], "categories": categories, "description": description})
            logs.append(logged(request_log, 2, f"{source_name} — profile request", int(bool(profile_body)), "request_component"))
    logs.append(logged(landing_log, 2, source_name, len(observations), "observations_retained", "Only active members were retained; associate members were not treated as Tennessee farm evidence."))
    return observations, logs, {"tennessee_agritourism_active_members": profiles}


def arkansas_extension_farms(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = "University of Arkansas Center for Arkansas Farms and Food — direct-sale farms"
    body, request_log = fetch(config["extension_farms"])
    headings = list(re.finditer(r'<h[2-5][^>]*>(.*?)</h[2-5]>', body, re.I | re.S))
    records: list[dict[str, str]] = []
    observations: list[Observation] = []
    stop_names = {"menu", "contact"}
    for index, match in enumerate(headings):
        name = strip_tags(match.group(1))
        if not name or name.casefold() in stop_names:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else min(len(body), match.end() + 5000)
        segment = body[match.end():end]
        description = strip_tags(segment)[:1400]
        links = re.findall(r'href=["\'](https?://[^"\']+)', segment, re.I)
        website, facebook, instagram, tiktok = split_public_links(links, "uada.edu")
        row = empty_observation(state, source_name, str(len(records) + 1), name, config["extension_farms"], 2, "B")
        row.update({
            "entity_type_source": "Direct-sale farm",
            "entity_type_review": "farm_activity_confirmed_by_university_direct_sale_farm_list",
            "products": description or "Farm products; see university listing",
            "business_types": "Direct-sale farm; Northwest Arkansas",
            "website_url": website,
            "facebook_url": facebook,
            "instagram_url": instagram,
            "tiktok_url": tiktok,
            "on_farm_sales": True,
            "notes": description,
        })
        observations.append(Observation(**row))
        records.append({"name": name, "description": description, "links": links})
    return observations, [logged(request_log, 2, source_name, len(records), "observations_retained")], {"extension_direct_sale_farms": records}


def eatwild_records(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    source_name = f"EatWild {config['name']} directory"
    body, request_log = fetch(config["eatwild"])
    observations: list[Observation] = []
    raw: list[dict[str, Any]] = []
    blocks = re.split(r"<hr\b[^>]*>", body, flags=re.I)
    for block in blocks:
        text = strip_tags(block)
        state_zip = re.search(
            rf"(?:{re.escape(state)}|{re.escape(config['name'])})\s+(\d{{5}})\b",
            text, re.I,
        )
        if not state_zip:
            continue
        links = re.findall(r'href=["\'](.*?)["\']', block, re.I)
        website, facebook, instagram, tiktok = split_public_links(links, "eatwild.com")
        email_match = re.search(r'href=["\']mailto:([^"\']+)', block, re.I)
        email = clean_text(email_match.group(1)) if email_match else ""
        phone_match = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-./ ]\d{3}[-./ ]\d{4}(?!\d)", text)
        contact_signals = (phone_match, email, website, facebook, instagram, tiktok)
        if not any(contact_signals):
            continue
        strong_values = [strip_tags(value) for value in re.findall(r"<strong[^>]*>(.*?)</strong>", block, re.I | re.S)]
        name = strong_values[0] if strong_values else ""
        if not name:
            contact_paragraphs = [strip_tags(value) for value in re.findall(r'<p[^>]*class=["\'][^"\']*bodyMargin[^"\']*["\'][^>]*>(.*?)</p>', block, re.I | re.S)]
            contact_line = next((value for value in reversed(contact_paragraphs) if state_zip.group(0) in value), "")
            name = contact_line.split(",", 1)[0].strip()
        if not 3 <= len(name) <= 100:
            continue
        address_link = next(
            (strip_tags(value) for value in re.findall(r'<a[^>]*>(.*?)</a>', block, re.I | re.S) if re.search(rf"\b(?:{re.escape(state)}|{re.escape(config['name'])})\s+\d{{5}}\b", strip_tags(value), re.I)),
            "",
        )
        city_match = re.search(
            rf",\s*([A-Za-z][A-Za-z .'-]{{1,40}}),\s*(?:{re.escape(state)}|{re.escape(config['name'])})\s+\d{{5}}\b",
            address_link or text, re.I,
        )
        row = empty_observation(state, source_name, str(len(raw) + 1), name, config["eatwild"], 2, "D")
        row.update({
            "entity_type_source": "Pastured-product farm",
            "entity_type_review": "farm_activity_confirmed_by_directory_farm_list",
            "city": normalized_city(city_match.group(1)) if city_match else "", "postal_code": state_zip.group(1),
            "address": address_link,
            "location_precision": "public_directory_address_or_city",
            "phone": phone_match.group(0) if phone_match else "", "email": email,
            "products": "Pastured livestock and/or farm products; see source listing",
            "business_types": "Pastured-product farm; direct sales",
            "website_url": website, "facebook_url": facebook, "instagram_url": instagram,
            "tiktok_url": tiktok,
            "on_farm_sales": True, "notes": clean_text(text)[:1200],
        })
        observations.append(Observation(**row)); raw.append({"name": name, "text": clean_text(text)})
    return observations, [logged(request_log, 2, source_name, len(raw), "observations_retained")], {"eatwild_records": raw}


def pyo_records(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    observations: list[Observation] = []
    logs: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    regions = config.get("pyo_regions", {})
    if config.get("pyo_discover_regions"):
        index_body, index_log = fetch(config["pyo_index"])
        section_match = re.search(
            rf'{re.escape(config["name"])} U-Pick Farms and Orchards</h2>(.*?)(?:<h2\b|<area\b)',
            index_body,
            re.I | re.S,
        )
        section = section_match.group(1) if section_match else ""
        discovered: dict[str, str] = {}
        for href, label in re.findall(
            rf'<a\s+href\s*=\s*["\']?((?:https://www\.pickyourown\.org/)?{state}[^"\' >]+\.htm)["\']?[^>]*>(.*?)</a>',
            section,
            re.I | re.S,
        ):
            url = urllib.parse.urljoin(config["pyo_index"], html.unescape(href))
            name = strip_tags(label) or url.rsplit("/", 1)[-1].removesuffix(".htm")
            discovered[name] = url
        regions = discovered
        logs.append(logged(
            index_log,
            3,
            f"PickYourOwn — {config['name']} region index",
            len(regions),
            "request_component",
            "Region pages were discovered from the live state index rather than hard-coded.",
        ))
        raw["region_index"] = [{"region": name, "url": url} for name, url in regions.items()]
    for region, url in regions.items():
        body, request_log = fetch(url)
        active = False
        closed_section = False
        county = ""
        records: list[dict[str, Any]] = []
        searched: list[str] = []

        def walk(node: Node) -> None:
            nonlocal active, closed_section, county
            if node.tag == "h2" and "U-Pick Farms and Orchards" in node.text():
                active = True
                closed_section = False
            elif active and node.tag == "h2":
                active = False; closed_section = False; county = ""
            elif active and node.tag == "h3":
                heading = node.text()
                if heading.startswith("ZZZ -"):
                    closed_section = True; county = ""
                elif heading.casefold().endswith(" county"):
                    closed_section = False
                    county = normalized_county(heading)
                    if county not in searched: searched.append(county)
                else:
                    closed_section = False; county = ""
            elif active and node.tag in {"li", "p"} and (county or closed_section):
                farm_node = first_descendant(node, lambda item: item.has_class("farm"))
                if not farm_node:
                    farm_node = next((item for item in node.children if isinstance(item, Node) and item.tag in {"b", "strong"}), None)
                name = farm_node.text().strip(" -:") if farm_node else ""
                text = node.text()
                if name and len(name) <= 110 and re.search(rf"^{re.escape(name)}\b|\b{re.escape(name)}\s*-", text, re.I):
                    explicit_closed = bool(re.search(r"permanently closed|assumed permanently closed|ceased operation", text, re.I))
                    if closed_section and not explicit_closed:
                        return
                    city_zip = re.search(
                        rf"\b([A-Za-z][A-Za-z .'-]{{1,40}}),\s*(?:{re.escape(state)}|{re.escape(config['name'])})\s+(\d{{5}})\b",
                        text,
                        re.I,
                    )
                    phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", text)
                    website, facebook, instagram, email = link_values(node)
                    row = empty_observation(state, f"PickYourOwn — {region}", str(len(records) + 1), name, url, 3, "E")
                    row.update({
                        "entity_type_source": "U-pick operation",
                        "entity_type_review": "farm_activity_confirmed_by_u_pick_directory",
                        "county": county, "county_source": url,
                        "city": normalized_city(city_zip.group(1)) if city_zip else "",
                        "postal_code": city_zip.group(2) if city_zip else "",
                        "location_precision": "county_or_public_directory_city",
                        "phone": phone.group(0) if phone else "", "email": email,
                        "products": "U-pick crops; agritourism",
                        "business_types": "U-pick; agritourism",
                        "website_url": website, "facebook_url": facebook, "instagram_url": instagram,
                        "on_farm_sales": True, "u_pick": True,
                        "promotion_status": "staged_closure_review" if explicit_closed else "staged_pending_rules",
                        "notes": ("Source explicitly reports closure; retain pending affirmative curator decision. " if explicit_closed else "") + clean_text(text)[:1100],
                    })
                    observations.append(Observation(**row)); records.append({"name": name, "county": county, "text": clean_text(text), "closed_report": explicit_closed})
                    return
            for child in node.children:
                if isinstance(child, Node): walk(child)

        if body: walk(dom(body))
        raw[region] = {"url": url, "searched_counties": searched, "records": records}
        logs.append(logged(request_log, 3, f"PickYourOwn — {region}", len(records), "observations_retained", f"County sections searched: {len(searched)}; closure claims retained for review."))
    return observations, logs, {"pickyourown_regions": raw}


def county_denominator(state: str, config: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    params = urllib.parse.urlencode({
        "where": f"STATE='{config['fips']}'", "outFields": "NAME,GEOID,STATE,COUNTY",
        "returnGeometry": "false", "f": "json",
    })
    url = CENSUS_COUNTIES_URL + params
    body, request_log = fetch(url)
    counties = []
    try:
        for feature in json.loads(body).get("features", []):
            attrs = feature.get("attributes", {})
            counties.append({"county": normalized_county(attrs.get("NAME", "")), "county_fips": clean_text(attrs.get("GEOID"))})
    except json.JSONDecodeError:
        pass
    return counties, logged(request_log, 1, "U.S. Census Bureau — county denominator", len(counties), "coverage_denominator")


def place_county_reference(
    state: str,
    config: dict[str, Any],
) -> tuple[dict[str, tuple[str, str, str]], list[dict[str, str]], dict[str, Any]]:
    """Return Census places that fall wholly within one county.

    Multi-county places are intentionally absent so a city name alone can never
    silently assign an ambiguous county.
    """
    body, request_log = fetch(CENSUS_PLACE_COUNTY_URL)
    try:
        rows = list(csv.DictReader(io.StringIO(body.lstrip("\ufeff")), delimiter="|"))
    except csv.Error:
        rows = []
    state_rows = [
        row for row in rows
        if row.get("STATEFP") == config["fips"] and clean_text(row.get("PLACENAME", ""))
    ]
    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in state_rows:
        display = re.sub(r"\s+(?:city|town|village|CDP)\s*$", "", row["PLACENAME"], flags=re.I)
        grouped[normalized_name(display)].append(row)
    mapping: dict[str, tuple[str, str, str]] = {}
    for key, matches in grouped.items():
        counties = {row.get("COUNTYFP", ""): row for row in matches}
        if len(counties) != 1:
            continue
        row = next(iter(counties.values()))
        display = re.sub(r"\s+(?:city|town|village|CDP)\s*$", "", row["PLACENAME"], flags=re.I)
        mapping[key] = (
            clean_text(display),
            normalized_county(row.get("COUNTYNAME", "")),
            f"{config['fips']}{row.get('COUNTYFP', '')}",
        )
    log = logged(
        request_log,
        1,
        "U.S. Census Bureau — place-by-county reference",
        len(state_rows),
        "county_enrichment",
        f"{len(mapping)} unambiguous {config['name']} place names retained; multi-county places withheld.",
    )
    return mapping, state_rows, log


def apply_place_reference(
    state: str,
    config: dict[str, Any],
    observations: list[Observation],
    places: dict[str, tuple[str, str, str]],
) -> None:
    """Derive only state-confirmed city/postal values from public addresses."""
    state_marker = re.compile(rf"\b(?:{re.escape(state)}|{re.escape(config['name'])})\b", re.I)
    place_keys = sorted(places, key=lambda value: (-len(value.split()), -len(value), value))
    for item in observations:
        address = clean_text(item.address)
        marker = state_marker.search(address)
        if address and marker:
            if not item.postal_code:
                postal = re.search(r"\b(\d{5})(?:-\d{4})?\b", address)
                if postal:
                    item.postal_code = postal.group(1)
            if not item.city:
                before_state = address[:marker.start()].strip(" ,")
                comma_candidate = before_state.rsplit(",", 1)[-1].strip()
                comma_key = normalized_name(comma_candidate)
                if "," in before_state and comma_key in places:
                    item.city = places[comma_key][0]
                else:
                    normalized_prefix = normalized_name(before_state)
                    matched = next(
                        (key for key in place_keys if normalized_prefix == key or normalized_prefix.endswith(" " + key)),
                        "",
                    )
                    if matched:
                        item.city = places[matched][0]
        city_key = normalized_name(item.city)
        if city_key in places and (
            not item.county
            or (
                item.county != places[city_key][1]
                and "pickyourown.org" in item.county_source.casefold()
            )
        ):
            _, county, county_fips = places[city_key]
            if item.county and item.county != county:
                item.notes = (
                    f"Census place reference corrected broad PickYourOwn region county "
                    f"from {item.county} to {county}. {item.notes}"
                )[:1500]
            item.county = county
            item.county_fips = county_fips
            item.county_source = CENSUS_PLACE_COUNTY_URL


def county_seats(state: str, config: dict[str, Any]) -> tuple[list[tuple[str, str]], dict[str, Any], str]:
    raw, request_log = fetch_bytes(config["county_seats"])
    text = ""
    if raw:
        try:
            result = subprocess.run(["pdftotext", "-layout", "-", "-"], input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            text = result.stdout.decode("utf-8", "replace")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        for cell in re.split(r"\s{2,}", line.strip()):
            if " - " not in cell and " – " not in cell:
                continue
            parts = re.split(r"\s+[–-]\s+", cell, maxsplit=1)
            if len(parts) != 2:
                continue
            county, seats = parts
            seat = re.split(r"/", seats)[0].strip()
            if county and seat and not county.casefold().startswith("where there are"):
                pairs.append((normalized_county(county), seat))
    pairs = list(dict.fromkeys(pairs))
    return pairs, logged(request_log, 3, "Association of Arkansas Counties — county-seat anchors", len(pairs), "gap_search_anchors"), text


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def localharvest_cards(body: str, state_name: str, searched_county: str, search_url: str) -> list[dict[str, str]]:
    matches = list(re.finditer(r'<a href="(/[^"]+-M\d+)" class="mt-0">(.*?)</a>', body, re.I | re.S))
    records = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(body), match.end() + 4000)
        segment = body[match.end():end]
        location = re.search(rf'>([A-Za-z][A-Za-z .\'-]{{1,50}}),\s*{re.escape(state_name)}</a>', segment, re.I)
        summary = re.search(r'<p class="d-none d-sm-inline mb-1">(.*?)</p>', segment, re.I | re.S)
        records.append({
            "url": LOCALHARVEST_BASE + match.group(1), "name": strip_tags(match.group(2)),
            "city": normalized_city(location.group(1)) if location else "",
            "summary": strip_tags(summary.group(1)) if summary else "",
            "searched_county": searched_county, "search_url": search_url,
        })
    return records


def localharvest_profile(state: str, config: dict[str, Any], card: dict[str, str], body: str) -> Observation:
    location = re.search(
        r'<strong>Location:</strong><br\s*/?>\s*(.*?)\s*<br\s*/?>\s*([A-Za-z][A-Za-z .\'-]{1,45}),\s*([A-Z]{2})\s+(\d{5})',
        body, re.I | re.S,
    )
    outside_jurisdiction = bool(location and location.group(3).upper() != state)
    updated = re.search(r"Listing last updated on\s*<span[^>]*>\s*([^<]+)", body, re.I)
    grade = "E"
    if updated:
        for fmt in ("%B %d, %Y", "%b %d, %Y"):
            try:
                if datetime.strptime(clean_text(updated.group(1)), fmt).date().year >= date.today().year - 2:
                    grade = "D"
                break
            except ValueError:
                continue
    description = re.search(r'<div id="descDiv"[^>]*>(.*?)</div>', body, re.I | re.S)
    desc = strip_tags(description.group(1)) if description else card["summary"]
    contact_start = body.find('id="contact-block"'); contact_end = body.find("Coming Events", contact_start)
    contact = body[contact_start:contact_end] if contact_start >= 0 and contact_end > contact_start else ""
    links = re.findall(r'href="(https?://[^" ]+)"', contact, re.I)
    website, facebook, instagram, tiktok = split_public_links(links, "localharvest.org")
    phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-./ ]\d{3}[-./ ]\d{4}(?!\d)", strip_tags(contact))
    products_area = re.search(r"Products and Crops(.*?)(?:Contact Information|RIGHT BAR)", body, re.I | re.S)
    products = [strip_tags(item) for item in re.findall(r'<li><a[^>]*>(.*?)</a></li>', products_area.group(1), re.I | re.S)] if products_area else []
    record_match = re.search(r"-M(\d+)$", card["url"])
    row = empty_observation(state, f"LocalHarvest — {config['name']} county-seat gap search", record_match.group(1) if record_match else card["url"], card["name"], card["url"], 3, grade)
    row.update({
        "entity_type_source": "Family Farm", "entity_type_review": "farm_activity_confirmed_by_directory_farm_search",
        "city": normalized_city(location.group(2)) if location else card["city"], "postal_code": location.group(4) if location else "",
        "address": strip_tags(location.group(1)) if location else "", "location_precision": "public_directory_address_or_city",
        "phone": phone.group(0) if phone else "", "products": "; ".join(dict.fromkeys(products)) or desc[:700] or "Farm products; see source profile",
        "business_types": "LocalHarvest Family Farm", "website_url": website, "facebook_url": facebook,
        "instagram_url": instagram, "tiktok_url": tiktok, "on_farm_sales": True,
        "promotion_status": "excluded_outside_jurisdiction" if outside_jurisdiction else "staged_pending_rules",
        "notes": (
            (f"Source location is {location.group(3).upper()}, outside {state}; retained as exclusion evidence. " if outside_jurisdiction else "")
            + f"Discovered through {card['searched_county']} County seat search ({card['search_url']}). "
            + (f"Listing last updated {clean_text(updated.group(1))}. " if updated else "Update date not exposed. ")
            + desc[:1100]
        ),
    })
    return Observation(**row)


def localharvest_gap_search(state: str, config: dict[str, Any], seats: list[tuple[str, str]]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any], set[str]]:
    request_logs: list[dict[str, Any]] = []
    cards: dict[str, dict[str, str]] = {}
    searched_ok: set[str] = set()
    failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {}
        for county, seat in seats:
            url = f"{LOCALHARVEST_BASE}/{slug(seat)}-{state.casefold()}/farms"
            futures[executor.submit(fetch, url)] = (county, seat, url)
        for future in as_completed(futures):
            county, seat, url = futures[future]
            try: body, request_log = future.result()
            except Exception as exc: body, request_log = "", {"url": url, "error": str(exc), "attempts_used": 0}
            found = localharvest_cards(body, config["name"], county, url) if body else []
            request_logs.append(logged(request_log, 3, "LocalHarvest — county-seat search request", len(found), "request_component", f"{county} County; seat {seat}"))
            if request_log.get("error"):
                failures.append({"county": county, "seat": seat, "error": request_log["error"]})
            else:
                searched_ok.add(county)
            for card in found: cards.setdefault(card["url"], card)

    observations: list[Observation] = []
    profile_failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(fetch, card["url"]): card for card in cards.values()}
        for future in as_completed(futures):
            card = futures[future]
            try: body, request_log = future.result()
            except Exception as exc: body, request_log = "", {"url": card["url"], "error": str(exc), "attempts_used": 0}
            request_logs.append(logged(request_log, 3, "LocalHarvest — farm profile request", int(bool(body)), "request_component"))
            if body:
                observations.append(localharvest_profile(state, config, card, body))
            else:
                profile_failures.append({"url": card["url"], "error": request_log.get("error", "empty response")})
                row = empty_observation(
                    state,
                    f"LocalHarvest — {config['name']} county-seat gap search",
                    card["url"].rstrip("/").rsplit("-M", 1)[-1],
                    card["name"],
                    card["url"],
                    3,
                    "E",
                )
                row.update({
                    "entity_type_source": "Family Farm",
                    "entity_type_review": "farm_activity_confirmed_by_directory_farm_search_card",
                    "city": card["city"],
                    "location_precision": "public_directory_search_card_city",
                    "products": card["summary"][:700] or "Farm products; profile unavailable",
                    "business_types": "LocalHarvest Family Farm",
                    "on_farm_sales": True,
                    "notes": (
                        f"Named official search result retained after profile request failed; missing fields remain QA. "
                        f"Discovered through {card['searched_county']} County search ({card['search_url']}). "
                        f"{card['summary']}"
                    )[:1500],
                })
                observations.append(Observation(**row))
    aggregate_log = {
        "url": LOCALHARVEST_BASE, "attempts_used": 1, "http_status": 200, "bytes": 0, "sha256": "",
        "elapsed_seconds": 0, "error": "", "pass": 3,
        "source_name": f"LocalHarvest — {config['name']} county-seat gap search",
        "records_parsed": len(observations), "retrieved_at": now_iso(), "source_decision": "observations_retained",
        "note": f"Searched {len(seats)} county-seat anchors; deduplicated {len(cards)} profile URLs. Failures remain explicit.",
    }
    request_logs.append(aggregate_log)
    raw = {"cards": list(cards.values()), "county_search_failures": failures, "profile_failures": profile_failures}
    return observations, request_logs, {"localharvest_gap_search": raw}, searched_ok


def census_place_gap_anchors(place_rows: list[dict[str, str]], gaps: set[str]) -> list[tuple[str, str]]:
    """Choose one Census-recognized community as a deterministic county anchor."""
    candidates: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in place_rows:
        county = normalized_county(row.get("COUNTYNAME", ""))
        if county not in gaps:
            continue
        raw = clean_text(row.get("PLACENAME", ""))
        place = re.sub(
            r"\s+(?:city|town|village|CDP|consolidated government|unified government)\s*$",
            "",
            raw,
            flags=re.I,
        )
        # Incorporated cities/towns are more reliable location slugs than CDPs
        # or countywide consolidated-government labels.
        rank = 0 if re.search(r"\s+(?:city|town|village)$", raw, re.I) else 1 if raw.endswith(" CDP") else 2
        if place:
            candidates[county].append((rank, place))
    return [
        (county, sorted(candidates[county], key=lambda item: (item[0], item[1].casefold()))[0][1])
        for county in sorted(gaps)
        if candidates[county]
    ]


def fcc_county(state: str, config: dict[str, Any], item: Observation) -> tuple[str, str, str, dict[str, Any]]:
    url = f"{FCC_AREA_URL}?{urllib.parse.urlencode({'lat': item.latitude, 'lon': item.longitude, 'format': 'json'})}"
    body, request_log = fetch(url)
    county = fips = ""; error = request_log.get("error", "")
    try:
        result = (json.loads(body).get("results") or [None])[0]
        if result and clean_text(result.get("state_fips")) == config["fips"]:
            county = normalized_county(result.get("county_name", "")); fips = clean_text(result.get("county_fips"))
        elif result:
            item.promotion_status = "excluded_outside_jurisdiction"
            error = f"Coordinates resolve outside {config['name']}"
            item.notes = f"FCC Census geography confirms the source coordinates resolve outside {state}; retained as exclusion evidence. {item.notes}"[:1500]
        elif not error: error = f"No {config['name']} county returned"
    except (json.JSONDecodeError, TypeError):
        if not error: error = "Invalid FCC response"
    return county, fips, url, logged(request_log, 1, "FCC Census Area API", int(bool(county)), "county_enrichment", error)


def census_address_county(state: str, config: dict[str, Any], item: Observation) -> tuple[str, str, str, dict[str, Any]]:
    one_line = ", ".join(value for value in [item.address, item.city, state, item.postal_code] if clean_text(value))
    params = {"address": one_line, "benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json"}
    url = f"{CENSUS_GEOCODER_URL}?{urllib.parse.urlencode(params)}"
    body, request_log = fetch(url)
    county = fips = ""; error = request_log.get("error", "")
    try:
        matches = json.loads(body).get("result", {}).get("addressMatches", [])
        counties = matches[0].get("geographies", {}).get("Counties", []) if matches else []
        if counties and clean_text(counties[0].get("STATE")) == config["fips"]:
            county = normalized_county(counties[0].get("NAME", "")); fips = f"{config['fips']}{counties[0].get('COUNTY', '')}"
        elif not error: error = f"No {config['name']} Census address match returned"
    except (json.JSONDecodeError, TypeError, IndexError):
        if not error: error = "Invalid Census geocoder response"
    return county, fips, url, logged(request_log, 2, "U.S. Census Geocoder", int(bool(county)), "county_enrichment", error)


def enrich_geography(state: str, config: dict[str, Any], observations: list[Observation]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    logs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    targets = [
        item for item in observations
        if item.promotion_status != "excluded_outside_jurisdiction"
        and not item.county and item.latitude is not None and item.longitude is not None
    ]
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(fcc_county, state, config, item): item for item in targets}
        for future in as_completed(futures):
            item = futures[future]
            county, fips, url, request_log = future.result(); logs.append(request_log)
            if county: item.county, item.county_fips, item.county_source = county, fips, url
            else: errors.append({"observation_id": item.observation_id, "farm_name": item.farm_name, "error": request_log.get("error", "County not returned")})
    address_targets = [
        item for item in observations
        if item.promotion_status != "excluded_outside_jurisdiction"
        and not item.county and item.address and item.city and item.postal_code
    ]
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(census_address_county, state, config, item): item for item in address_targets}
        for future in as_completed(futures):
            item = futures[future]
            county, fips, url, request_log = future.result(); logs.append(request_log)
            if county: item.county, item.county_fips, item.county_source = county, fips, url
            else: errors.append({"observation_id": item.observation_id, "farm_name": item.farm_name, "error": request_log.get("error", "County not returned")})
    return logs, errors


def read_current_rows(state: str) -> list[dict[str, Any]]:
    if not PUBLIC_FARMS.exists():
        return []
    return [row for row in json.loads(PUBLIC_FARMS.read_text(encoding="utf-8")) if row.get("state") == state]


def canonical_baseline_observations(state: str, rows: list[dict[str, Any]]) -> list[Observation]:
    observations: list[Observation] = []
    source_name = "FarmFinder current canonical baseline — identity anchor only"
    for record in rows:
        name = clean_text(record.get("name"))
        if not name:
            continue
        raw_county = clean_text(record.get("parish"))
        county = "" if raw_county.casefold() == "varies" or "/" in raw_county or "+" in raw_county else normalized_county(raw_county)
        verification_urls = [clean_url(value) for value in clean_text(record.get("verificationSource")).split(" | ")]
        source_url = next((value for value in verification_urls if value), "")
        contact = clean_text(record.get("contact"))
        phone = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", contact)
        email = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", contact, re.I)
        products = clean_text(record.get("productsText")) or "; ".join(record.get("products", []))
        description = " ".join(filter(None, [clean_text(record.get("description")), clean_text(record.get("notes")), clean_text(record.get("category"))]))
        confirmed = farm_entity_confirmation(name, description, products)
        row = empty_observation(
            state,
            source_name,
            clean_text(record.get("recordId")) or clean_text(record.get("id")),
            name,
            source_url,
            0,
            "C" if record.get("lastVerified") else "E",
        )
        row.update({
            "identity_review_status": "canonical_identity_anchor",
            "current_release_name_collision": name,
            "entity_type_source": "Canonical FarmFinder farm listing",
            "entity_type_review": "farm_activity_confirmed_by_current_canonical_review" if confirmed else "canonical_listing_requires_farm_scope_review",
            "county": county,
            "county_source": source_url or "FarmFinder canonical baseline",
            "city": normalized_city(record.get("city", "")),
            "latitude": record.get("latitude"),
            "longitude": record.get("longitude"),
            "location_precision": clean_text(record.get("geoPrecision")),
            "phone": phone.group(0) if phone else "",
            "email": email.group(0) if email else "",
            "products": products,
            "business_types": clean_text(record.get("category")),
            "website_url": clean_url(record.get("website", "")),
            "facebook_url": clean_url(record.get("facebookUrl", "")),
            "instagram_url": clean_url(record.get("instagramUrl", "")),
            "on_farm_sales": record.get("onFarm") is True,
            "farmers_market_sales": record.get("farmersMarket") is True,
            "online_sales": record.get("onlineStore") is True,
            "local_delivery": record.get("ships") is True,
            "promotion_status": "canonical_identity_anchor",
            "notes": f"Canonical record {clean_text(record.get('recordId'))}; retained as an identity anchor and not counted as a current collection pass.",
        })
        observations.append(Observation(**row))
    return observations


def align_current_observations_to_canon(observations: list[Observation], canonical_rows: list[dict[str, Any]]) -> None:
    exact = {normalized_name(row.get("name", "")): row for row in canonical_rows}
    token_index: defaultdict[str, set[str]] = defaultdict(set)
    for key, row in exact.items():
        contact = clean_text(row.get("contact"))
        phones = re.findall(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)", contact)
        emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", contact, re.I)
        values = [row.get("website"), row.get("facebookUrl"), row.get("instagramUrl"), *phones, *emails]
        for value in values:
            token = re.sub(r"[^a-z0-9]", "", clean_text(value).casefold())
            if len(token) >= 7:
                token_index[token].add(key)
    for item in observations:
        if item.source_pass == 0:
            continue
        if item.candidate_key in exact:
            item.current_release_name_collision = clean_text(exact[item.candidate_key].get("name"))
            item.identity_review_status = "exact_canonical_name_match"
            continue
        matches: set[str] = set()
        for token in identity_tokens(item):
            matches.update(token_index.get(token, set()))
        if len(matches) == 1:
            canonical_key = next(iter(matches))
            item.candidate_key = canonical_key
            item.current_release_name_collision = clean_text(exact[canonical_key].get("name"))
            item.identity_review_status = "unique_canonical_contact_or_url_match"


def canonical_reconciliation_rows(
    state: str,
    canonical_rows: list[dict[str, Any]],
    observations: list[Observation],
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    current_by_key: defaultdict[str, list[Observation]] = defaultdict(list)
    for item in observations:
        if item.source_pass > 0:
            current_by_key[item.candidate_key].append(item)
    entity_by_key: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for entity in entities:
        entity_by_key[entity["normalized_name"]].append(entity)
    current_entities = [row for row in entities if row.get("canonical_match_status") != "canonical_baseline_only"]
    result: list[dict[str, Any]] = []
    for record in canonical_rows:
        key = normalized_name(record.get("name", ""))
        exact_current = current_by_key.get(key, [])
        status = "rediscovered_current_source" if exact_current else "canonical_baseline_only"
        possible_entity = ""
        possible_name = ""
        possible_score = 0.0
        possible_alias_exact = False
        if not exact_current:
            county = normalized_county(record.get("parish", ""))
            city = normalized_city(record.get("city", ""))
            canonical_alias = canonical_alias_key(record.get("name", ""))
            for entity in current_entities:
                score = difflib.SequenceMatcher(None, key, entity["normalized_name"]).ratio()
                same_geo = bool(
                    (county and entity.get("county") == county)
                    or (city and normalized_city(entity.get("city", "")) == city)
                )
                alias_exact = bool(canonical_alias and canonical_alias == canonical_alias_key(entity["farm_name"]))
                rank = score + (0.2 if alias_exact else 0) + (0.03 if same_geo else 0)
                current_rank = possible_score + (0.2 if possible_alias_exact else 0)
                if rank > current_rank:
                    possible_score = score
                    possible_alias_exact = alias_exact
                    possible_entity = entity["entity_id"]
                    possible_name = entity["farm_name"]
            if possible_alias_exact or possible_score >= 0.90:
                status = "possible_alias_review"
        exact_entities = entity_by_key.get(key, [])
        result.append({
            "record_id": clean_text(record.get("recordId")),
            "canonical_name": clean_text(record.get("name")),
            "state": state,
            "canonical_county_equivalent": normalized_county(record.get("parish", "")),
            "canonical_city": normalized_city(record.get("city", "")),
            "reconciliation_status": status,
            "matched_entity_ids": " | ".join(row["entity_id"] for row in exact_entities),
            "current_source_names": " | ".join(dict.fromkeys(item.source_name for item in exact_current)),
            "possible_alias_entity_id": possible_entity if status == "possible_alias_review" else "",
            "possible_alias_name": possible_name if status == "possible_alias_review" else "",
            "possible_alias_score": f"{possible_score:.3f}" if status == "possible_alias_review" else "",
        })
    return result


def choose(items: list[Observation], field: str) -> Any:
    ordered = sorted(items, key=lambda item: (GRADE_RANK.get(item.evidence_grade, 9), -len(clean_text(getattr(item, field)))))
    return next((getattr(item, field) for item in ordered if getattr(item, field) not in {None, ""}), "")


def choose_county(items: list[Observation]) -> str:
    located = [item for item in items if item.county]
    def geography_rank(item: Observation) -> int:
        source = item.county_source.casefold()
        if "geo.fcc.gov" in source or "census.gov/geocoder" in source:
            return 0
        if "census.gov/" in source:
            return 1
        return 2
    ordered = sorted(
        located,
        key=lambda item: (
            geography_rank(item),
            GRADE_RANK.get(item.evidence_grade, 9),
            -len(item.county),
        ),
    )
    return ordered[0].county if ordered else ""


def unique_values(items: list[Observation], field: str) -> str:
    values: list[str] = []
    for item in items:
        for value in clean_text(getattr(item, field)).split(";"):
            value = value.strip()
            if value and value not in values: values.append(value)
    return "; ".join(values)


def identity_tokens(item: Observation) -> set[str]:
    values = [item.phone, item.email, item.website_url, item.facebook_url, item.instagram_url]
    return {re.sub(r"[^a-z0-9]", "", clean_text(value).casefold()) for value in values if clean_text(value)}


def reconcile(state: str, observations: list[Observation]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    groups: defaultdict[str, list[Observation]] = defaultdict(list)
    for item in observations:
        if item.candidate_key: groups[item.candidate_key].append(item)
    entities: list[dict[str, Any]] = []; reviews: list[dict[str, Any]] = []; qa: list[dict[str, Any]] = []
    for key, all_items in sorted(groups.items()):
        counties = sorted({item.county for item in all_items if item.county})
        conflict = len(counties) > 1
        shared_identity = any(identity_tokens(left) & identity_tokens(right) for index, left in enumerate(all_items) for right in all_items[index + 1:])
        same_city = len({item.city.casefold() for item in all_items if item.city}) == 1 and sum(bool(item.city) for item in all_items) > 1
        merge_cross = conflict and (shared_identity or same_city)
        county_groups: defaultdict[str, list[Observation]] = defaultdict(list)
        if conflict and not merge_cross:
            for item in all_items: county_groups[item.county or f"unknown-{item.observation_id}"].append(item)
        else:
            preferred = choose_county(all_items)
            county_groups[preferred or "unknown"].extend(all_items)
        if len(all_items) > 1:
            reviews.append({
                "candidate_key": key, "observation_count": len(all_items),
                "farm_names": " | ".join(dict.fromkeys(item.farm_name for item in all_items)),
                "source_names": " | ".join(dict.fromkeys(item.source_name for item in all_items)),
                "cities": " | ".join(dict.fromkeys(item.city for item in all_items if item.city)),
                "counties": " | ".join(counties),
                "review_status": "merged_cross_county_shared_identity" if merge_cross else "split_county_conflict" if conflict else "merged_exact_name",
                "observation_ids": " | ".join(item.observation_id for item in all_items),
            })
        for group_county, items in county_groups.items():
            county = "" if group_county.startswith("unknown") else group_county
            name = choose(items, "farm_name")
            products = unique_values(items, "products")
            city = choose(items, "city")
            grades = sorted(set(item.evidence_grade for item in items), key=lambda grade: GRADE_RANK[grade])
            type_confirmed = any("farm_activity_confirmed" in item.entity_type_review for item in items)
            canonical_items = [item for item in items if item.source_pass == 0]
            current_items = [item for item in items if item.source_pass > 0]
            blockers: list[str] = []
            if conflict and not merge_cross: blockers.append("same normalized name appears in multiple counties")
            if not county: blockers.append("county missing")
            if not city: blockers.append("city or safe public service area missing")
            if not products: blockers.append("products or farm activity missing")
            if grades == ["E"]: blockers.append("single grade-E discovery listing needs corroboration")
            if not type_confirmed: blockers.append("directory candidate needs independent farm-operation evidence")
            if canonical_items and not current_items: blockers.append("canonical baseline farm not rediscovered in current three-pass sources")
            if any(item.promotion_status == "staged_closure_review" for item in items): blockers.append("source reports closure and requires affirmative curator decision")
            entity_id = state + "-" + hashlib.sha256(f"{key}|{county}|{items[0].observation_id if conflict else ''}".encode()).hexdigest()[:10].upper()
            website, facebook, instagram, tiktok = classify_public_urls(
                choose(items, "website_url"), choose(items, "facebook_url"), choose(items, "instagram_url"), choose(items, "tiktok_url")
            )
            disposition = classify_candidate(name, blockers)
            entity = {
                "entity_id": entity_id, "farm_name": name, "normalized_name": key,
                "entity_type": "farm" if type_confirmed else "producer_requires_type_review",
                "identity_decision": "merged_cross_county_identity_reviewed" if merge_cross else "split_due_county_conflict" if conflict else "merged_exact_name_reviewed" if len(items) > 1 else "unique_source_name_reviewed",
                "state": state, "county": county, "city": city, "postal_code": choose(items, "postal_code"),
                "address_internal": choose(items, "address"), "public_location_classification": "public_business_address_reviewed_for_future_reduced_precision",
                "latitude": choose(items, "latitude"), "longitude": choose(items, "longitude"),
                "products": products, "business_types": unique_values(items, "business_types"),
                "phone_internal": choose(items, "phone"), "email_internal": choose(items, "email"),
                "contact_visibility": "internal_until_public_use_review",
                "website_url": website, "facebook_url": facebook, "instagram_url": instagram, "tiktok_url": tiktok,
                "on_farm_sales": any(item.on_farm_sales is True for item in items),
                "farmers_market_sales": any(item.farmers_market_sales is True for item in items),
                "online_sales": any(item.online_sales is True for item in items),
                "local_delivery": any(item.local_delivery is True for item in items),
                "u_pick": any(item.u_pick is True for item in items), "wholesale": any(item.wholesale is True for item in items),
                "farm_to_school": any(item.farm_to_school is True for item in items),
                "source_observation_count": len(items), "source_observation_ids": " | ".join(item.observation_id for item in items),
                "source_names": " | ".join(dict.fromkeys(item.source_name for item in items)),
                "source_urls": " | ".join(dict.fromkeys(item.source_url for item in items)),
                "evidence_grades": "; ".join(grades), "last_retrieved": TODAY,
                "canonical_record_ids": " | ".join(item.source_record_id for item in canonical_items),
                "canonical_match_status": "rediscovered_current_source" if canonical_items and current_items else "canonical_baseline_only" if canonical_items else "new_state_candidate",
                "promotion_status": disposition.status, "promotion_blockers": "; ".join(blockers),
                "notes": "Fields selected by evidence grade; every source observation remains separately auditable.",
            }
            entities.append(entity)
            if blockers:
                qa.append({"entity_id": entity_id, "farm_name": name, "county": county, "issue_type": "promotion_blocker", "issue_detail": "; ".join(blockers), "recommended_action": "Verify with a farm-owned or current official source; never delete for missing data.", "status": "open"})
    entities.sort(key=lambda row: (row["county"], row["farm_name"].casefold(), row["entity_id"]))
    return entities, reviews, qa


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fieldnames or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        if fields: writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args(); state = args.state; config = STATE_CONFIG[state]
    output = ROOT / "data" / "source-releases" / "work" / state
    output.mkdir(parents=True, exist_ok=True)
    observations: list[Observation] = []; logs: list[dict[str, Any]] = []; raw_sources: dict[str, Any] = {}; critical: list[str] = []

    counties, county_log = county_denominator(state, config); logs.append(county_log)
    if len(counties) != config["county_count"]: critical.append(f"County denominator expected {config['county_count']}, received {len(counties)}")
    county_fips = {row["county"]: row["county_fips"] for row in counties}
    places, place_rows, place_log = place_county_reference(state, config); logs.append(place_log)
    raw_sources["census_place_by_county_reference"] = place_rows
    if not places: critical.append(f"No unambiguous {config['name']} place reference rows were available")

    adapters: list[Callable[..., tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]]]
    if state == "LA":
        adapters = [
            louisiana_fmnp_stands, louisiana_nursery_growers, louisiana_hemp_growers,
            louisiana_registered_apiary_businesses, louisiana_crawfish_suppliers, louisiana_strawberry_growers,
            louisiana_lsu_farm_food, louisiana_sweet_potato_shippers, louisiana_agritourism,
            eatwild_records, pyo_records,
        ]
    elif state == "MS":
        adapters = [
            mississippi_genuine, mississippi_mdac_market_channels, mississippi_christmas_tree_farms,
            mississippi_certified_nurseries, mississippi_agritourism, eatwild_records, pyo_records,
        ]
    elif state == "AR":
        adapters = [arkansas_directory, arkansas_extension_farms, eatwild_records, pyo_records]
    elif state == "TN":
        adapters = [tennessee_picktn, tennessee_century_farms, tennessee_agritourism, eatwild_records, pyo_records]
    elif state == "GA":
        adapters = [georgia_grown, georgia_farm_markets, eatwild_records, pyo_records]
    else:
        adapters = [florida_farm_to_you, florida_fdacs_lists, eatwild_records, us_farm_trail_records, pyo_records]
    for adapter in adapters:
        found, source_logs, raw = adapter(state, config)
        observations.extend(found); logs.extend(source_logs); raw_sources.update(raw)

    apply_place_reference(state, config, observations, places)
    geography_logs, geography_errors = enrich_geography(state, config, observations); logs.extend(geography_logs)

    searched_ok: set[str] = set()
    if config.get("county_seats"):
        seats, seats_log, seats_text = county_seats(state, config); logs.append(seats_log); raw_sources["county_seat_anchor_text"] = seats_text
        if len(seats) != config["county_count"]: critical.append(f"County-seat anchors expected {config['county_count']}, received {len(seats)}")
        found, source_logs, raw, searched_ok = localharvest_gap_search(state, config, seats)
        observations.extend(found); logs.extend(source_logs); raw_sources.update(raw)
    elif config.get("census_place_gap_search"):
        found_counties = {
            item.county for item in observations
            if item.county and item.promotion_status != "excluded_outside_jurisdiction"
        }
        gaps = (
            {row["county"] for row in counties}
            if config.get("census_place_full_search")
            else {row["county"] for row in counties} - found_counties
        )
        anchors = census_place_gap_anchors(place_rows, gaps)
        raw_sources["census_place_gap_anchors"] = [
            {"county": county, "place": place} for county, place in anchors
        ]
        if len(anchors) != len(gaps):
            missing_anchors = sorted(gaps - {county for county, _ in anchors})
            critical.append(f"Census place gap anchors missing: {', '.join(missing_anchors)}")
        found, source_logs, raw, searched_ok = localharvest_gap_search(state, config, anchors)
        observations.extend(found); logs.extend(source_logs); raw_sources.update(raw)

    apply_place_reference(state, config, observations, places)
    more_geography_logs, more_geography_errors = enrich_geography(state, config, observations)
    logs.extend(more_geography_logs); geography_errors.extend(more_geography_errors)
    for item in observations:
        item.phone = sanitized_phone(item.phone)
        item.email = sanitized_email(item.email)
    for source_log in logs:
        if source_log.get("source_decision") == "observations_retained" and source_log.get("error"):
            critical.append(f"{source_log.get('source_name')}: {source_log['error']}")
    canonical_rows = read_current_rows(state)
    align_current_observations_to_canon(observations, canonical_rows)
    baseline_observations = canonical_baseline_observations(state, canonical_rows)
    apply_place_reference(state, config, baseline_observations, places)
    observations.extend(baseline_observations)
    raw_sources["canonical_identity_baseline"] = [
        {
            "record_id": clean_text(row.get("recordId")),
            "name": clean_text(row.get("name")),
            "county_equivalent": clean_text(row.get("parish")),
            "city": clean_text(row.get("city")),
            "last_verified": clean_text(row.get("lastVerified")),
        }
        for row in canonical_rows
    ]
    for item in observations:
        if item.county and not item.county_fips: item.county_fips = county_fips.get(item.county, "")
    retained_observations = [item for item in observations if item.promotion_status != "excluded_outside_jurisdiction"]
    excluded_observations = [item for item in observations if item.promotion_status == "excluded_outside_jurisdiction"]
    name_counts = Counter(item.candidate_key for item in retained_observations if item.candidate_key)
    for item in retained_observations:
        if name_counts[item.candidate_key] > 1: item.identity_review_status = "exact_normalized_name_group_requires_reconciliation"
    observations.sort(key=lambda item: (item.candidate_key, item.source_name, item.source_record_id))
    retained_observations.sort(key=lambda item: (item.candidate_key, item.source_name, item.source_record_id))
    excluded_observations.sort(key=lambda item: (item.candidate_key, item.source_name, item.source_record_id))
    entities, identity_review, qa = reconcile(state, retained_observations)
    canonical_reconciliation = canonical_reconciliation_rows(state, canonical_rows, retained_observations, entities)
    missing_canonical = [row for row in canonical_reconciliation if not row["matched_entity_ids"]]
    if missing_canonical:
        critical.append(f"Canonical identity anchors missing from reconciled entities: {len(missing_canonical)}")
    eligible = [row for row in entities if row["promotion_status"] == "promotion_eligible_reviewed"]
    entity_counts = Counter(row["county"] for row in entities if row["county"])
    current_entity_counts = Counter(
        row["county"] for row in entities
        if row["county"] and row.get("canonical_match_status") != "canonical_baseline_only"
    )
    eligible_counts = Counter(row["county"] for row in eligible if row["county"])
    pass_counts: Counter[tuple[str, int]] = Counter()
    for item in retained_observations:
        if item.county: pass_counts[(item.county, item.source_pass)] += 1
    coverage = []
    for row in sorted(counties, key=lambda item: item["county"]):
        county = row["county"]; count = entity_counts[county]
        status = "candidates_found" if current_entity_counts[county] else "searched_none_found" if county in searched_ok else "source_blocked"
        coverage.append({
            "county": county, "county_fips": row["county_fips"],
            "pass_1_observations": pass_counts[(county, 1)], "pass_2_observations": pass_counts[(county, 2)], "pass_3_observations": pass_counts[(county, 3)],
            "candidate_entities": count, "current_source_candidate_entities": current_entity_counts[county], "promotion_eligible_entities": eligible_counts[county], "status": status,
            "coverage_note": "Official statewide directory plus market-channel sources and county/parish discovery search reviewed; canonical baseline-only entities do not satisfy current rediscovery coverage.",
        })
    unresolved_counties = [row["county"] for row in coverage if row["status"] == "source_blocked"]
    if unresolved_counties: critical.append(f"County gap searches blocked: {', '.join(unresolved_counties)}")

    source_observations = len(observations)
    summary = {
        "status": "coverage_reviewed" if not critical else "blocked_validation_errors",
        "release_id": f"{state.casefold()}-coverage-reviewed-v1-{TODAY}", "generated_at": now_iso(),
        "scope": f"{config['name']} three-pass private state release; canonical LA/MS remains unchanged.",
        "completion_definition": "All qualifying named candidates found under documented sources and county gap searches as of the release date; not every undiscoverable farm.",
        "collection_passes_started": [1, 2, 3], "collection_passes_completed": [1, 2, 3] if not critical else [],
        "source_datasets_evaluated": sum(log.get("source_decision") not in {"request_component", "county_enrichment"} for log in logs),
        "source_observations": source_observations, "source_observations_by_source": dict(sorted(Counter(item.source_name for item in observations).items())),
        "excluded_or_grade_f_observations": len(excluded_observations), "proposed_entities": len(entities), "manual_verification_decisions": 0,
        "promotion_eligible_entities": len(eligible), "research_or_qa_entities": len(entities) - len(eligible),
        "identity_review_groups": len(identity_review), "current_la_ms_name_collisions": sum(bool(item.current_release_name_collision) for item in retained_observations if item.source_pass > 0),
        "canonical_baseline_observations": len(baseline_observations),
        "current_source_observations": sum(item.source_pass > 0 for item in observations),
        "canonical_rows_rediscovered": sum(row["reconciliation_status"] == "rediscovered_current_source" for row in canonical_reconciliation),
        "canonical_rows_possible_alias": sum(row["reconciliation_status"] == "possible_alias_review" for row in canonical_reconciliation),
        "canonical_rows_baseline_only": sum(row["reconciliation_status"] == "canonical_baseline_only" for row in canonical_reconciliation),
        "counties_total": len(counties), "counties_with_candidates": sum(bool(row["candidate_entities"]) for row in coverage),
        "counties_with_current_candidates": sum(bool(row["current_source_candidate_entities"]) for row in coverage),
        "counties_without_candidates": [row["county"] for row in coverage if not row["candidate_entities"]],
        "counties_with_promotion_eligible_entities": sum(bool(row["promotion_eligible_entities"]) for row in coverage),
        "website_entities": sum(bool(row["website_url"]) for row in entities),
        "social_entities": sum(bool(row["facebook_url"] or row["instagram_url"] or row["tiktok_url"]) for row in entities),
        "direct_contact_entities": sum(bool(row["phone_internal"] or row["email_internal"]) for row in entities),
        "open_qa_items": len(qa), "unresolved_county_observations": sum(not item.county for item in retained_observations),
        "critical_errors": critical,
        "promotion_note": "Coverage-reviewed is not record-verified, approved, promotion-ready, or canonical.",
    }
    blocker_counts = Counter(
        blocker
        for row in qa
        for blocker in clean_text(row.get("issue_detail", "")).split("; ")
        if blocker
    )
    source_rows = "\n".join(
        f"| {name} | {count:,} |"
        for name, count in sorted(summary["source_observations_by_source"].items())
    )
    blocker_rows = "\n".join(
        f"| {blocker} | {count:,} |"
        for blocker, count in blocker_counts.most_common()
    )
    searched_none = [row["county"] for row in coverage if row["status"] == "searched_none_found"]
    report = f"""# {config['name']} state review report

> Release: `{summary['release_id']}`
>
> Contract: national state contract v2
>
> Lifecycle: `{summary['status']}` — not approved and not canonical

## Outcome

The three documented collection passes retained **{len(entities):,} named candidates** from
**{source_observations:,} immutable observations**. **{len(eligible):,}** currently meet staged
field and evidence gates; **{len(qa):,}** remain in explicit research/QA. Missing data never
caused deletion or exclusion. The observation total includes **{len(baseline_observations):,}**
canonical identity anchors that preserve the existing cleaned {state} canon without counting it
as a current collection pass.

## Reconciliation

| Measure | Count |
|---|---:|
| Immutable source observations | {source_observations:,} |
| Retained candidate entities | {len(entities):,} |
| Promotion-eligible reviewed entities | {len(eligible):,} |
| Research/QA entities | {len(qa):,} |
| Affirmatively excluded observations | {len(excluded_observations):,} |
| Identity review groups | {len(identity_review):,} |
| Counties reviewed | {len(coverage)} of {config['county_count']} |
| Counties with retained candidates | {sum(bool(row['candidate_entities']) for row in coverage)} |
| Counties with current-source candidates | {sum(bool(row['current_source_candidate_entities']) for row in coverage)} |
| Counties with eligible candidates | {sum(bool(row['promotion_eligible_entities']) for row in coverage)} |

## Canonical reconciliation

| Canonical outcome | Count |
|---|---:|
| Current canonical identity anchors | {len(canonical_rows):,} |
| Rediscovered by a current source | {summary['canonical_rows_rediscovered']:,} |
| Possible alias requiring identity review | {summary['canonical_rows_possible_alias']:,} |
| Baseline only; current source not rediscovered | {summary['canonical_rows_baseline_only']:,} |

Every cleaned canonical identity remains represented. A baseline-only identity is retained but
cannot be promotion-eligible until current evidence is found; possible aliases are never merged
silently.

## Source reconciliation

| Source | Immutable observations |
|---|---:|
{source_rows}

The source total above reconciles exactly to **{source_observations:,}** observations and all
observation IDs are required to be unique. The statewide coverage denominator contains
**{len(coverage)}** county equivalents. **{sum(row['status'] == 'candidates_found' for row in coverage)}**
have retained candidates; **{len(searched_none)}** were searched without a retained result
({', '.join(searched_none) if searched_none else 'none'}).

## Open QA blockers

Blocker counts overlap because one retained entity can require more than one follow-up.

| Blocker | Entities |
|---|---:|
{blocker_rows or '| None | 0 |'}

## Source passes

1. Official pass: {config['report_passes'][0]}.
2. Corroboration pass: {config['report_passes'][1]}.
3. Discovery pass: {config['report_passes'][2]}.

## Quality boundaries

- The official marketing directory includes producers, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as {config['name']} entities.
- Detailed observations, request logs, and raw source records remain outside Git in the evidence bundle.

## Promotion blockers

1. Resolve the {len(qa):,} QA candidates through current farm-owned or authoritative evidence.
2. Copy the immutable evidence objects to managed versioned storage.
3. Record approval against the resulting release fingerprint.
4. Promote {config['name']} atomically in a separate canonical-release change.
"""

    observation_rows = [asdict(item) for item in observations]
    write_csv(output / "observations.csv", observation_rows)
    write_csv(output / "entities.csv", entities)
    write_csv(output / "identity-review.csv", identity_review)
    write_csv(output / "qa-queue.csv", qa)
    write_csv(output / "county-coverage.csv", coverage)
    write_csv(output / "canonical-reconciliation.csv", canonical_reconciliation)
    exclusions = [{
        "observation_id": item.observation_id,
        "farm_name": item.farm_name,
        "exclusion_reason": "outside_jurisdiction",
        "source_url": item.source_url,
    } for item in excluded_observations]
    write_csv(output / "exclusions.csv", exclusions, ["observation_id", "farm_name", "exclusion_reason", "source_url"])
    write_csv(output / "geography-errors.csv", geography_errors)
    (output / "request-log.json").write_text(json.dumps(logs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "raw-source-records.json").write_text(json.dumps(raw_sources, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "completion-report.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2)); return 0 if not critical else 1


if __name__ == "__main__":
    raise SystemExit(main())
