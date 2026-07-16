#!/usr/bin/env python3
"""Collect Southeast farm candidates through one governed state pipeline.

Source adapters are state-specific because public directories differ, while
retention, reconciliation, geography, QA, evidence, and output rules are shared.
The collector writes detailed evidence only under data/source-releases/work/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import subprocess
import urllib.parse
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


def normalized_county(value: str) -> str:
    return re.sub(r"\s+County$", "", clean_text(value), flags=re.I).strip().title()


def normalized_city(value: str) -> str:
    return clean_text(value).title()


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
    for node in dom(body).descendants("p"):
        if not node.has_class("bodyMargin"):
            continue
        text = node.text()
        location = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40})\s*,?\s*(?:AR|Arkansas)\s+(\d{5})\b", text, re.I)
        if not location:
            continue
        before = text[:location.start()]
        name = re.split(r"(?<=[.!?])\s+", before)[-1].split(",", 1)[0].strip()
        if not 3 <= len(name) <= 100:
            continue
        address_match = re.search(r"(\d{1,6}\s+[^,]{2,80}),\s*$", before)
        phone_match = re.search(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-./ ]\d{3}[-./ ]\d{4}(?!\d)", text[location.end():])
        website, facebook, instagram, email = link_values(node)
        row = empty_observation(state, source_name, str(len(raw) + 1), name, config["eatwild"], 2, "D")
        row.update({
            "entity_type_source": "Pastured-product farm",
            "entity_type_review": "farm_activity_confirmed_by_directory_farm_list",
            "city": normalized_city(location.group(1)), "postal_code": location.group(2),
            "address": address_match.group(1) if address_match else "",
            "location_precision": "public_directory_address_or_city",
            "phone": phone_match.group(0) if phone_match else "", "email": email,
            "products": "Pastured livestock and/or farm products; see source listing",
            "business_types": "Pastured-product farm; direct sales",
            "website_url": website, "facebook_url": facebook, "instagram_url": instagram,
            "on_farm_sales": True, "notes": clean_text(text)[:1200],
        })
        observations.append(Observation(**row)); raw.append({"name": name, "text": clean_text(text)})
    return observations, [logged(request_log, 2, source_name, len(raw), "observations_retained")], {"eatwild_records": raw}


def pyo_records(state: str, config: dict[str, Any]) -> tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]:
    observations: list[Observation] = []
    logs: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    for region, url in config["pyo_regions"].items():
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
                    city_zip = re.search(r"\b([A-Za-z][A-Za-z .'-]{1,40}),\s*(?:AR|Arkansas)\s+(\d{5})\b", text, re.I)
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
        if city_key in places and not item.county:
            _, county, county_fips = places[city_key]
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
    targets = [item for item in observations if not item.county and item.latitude is not None and item.longitude is not None]
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(fcc_county, state, config, item): item for item in targets}
        for future in as_completed(futures):
            item = futures[future]
            county, fips, url, request_log = future.result(); logs.append(request_log)
            if county: item.county, item.county_fips, item.county_source = county, fips, url
            else: errors.append({"observation_id": item.observation_id, "farm_name": item.farm_name, "error": request_log.get("error", "County not returned")})
    address_targets = [item for item in observations if not item.county and item.address and item.city and item.postal_code]
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(census_address_county, state, config, item): item for item in address_targets}
        for future in as_completed(futures):
            item = futures[future]
            county, fips, url, request_log = future.result(); logs.append(request_log)
            if county: item.county, item.county_fips, item.county_source = county, fips, url
            else: errors.append({"observation_id": item.observation_id, "farm_name": item.farm_name, "error": request_log.get("error", "County not returned")})
    return logs, errors


def read_current_names() -> dict[str, str]:
    if not PUBLIC_FARMS.exists(): return {}
    return {normalized_name(row.get("name", "")): clean_text(row.get("name")) for row in json.loads(PUBLIC_FARMS.read_text(encoding="utf-8"))}


def choose(items: list[Observation], field: str) -> Any:
    ordered = sorted(items, key=lambda item: (GRADE_RANK.get(item.evidence_grade, 9), -len(clean_text(getattr(item, field)))))
    return next((getattr(item, field) for item in ordered if getattr(item, field) not in {None, ""}), "")


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
            preferred = choose([item for item in all_items if item.county], "county") if any(item.county for item in all_items) else ""
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
            blockers: list[str] = []
            if conflict and not merge_cross: blockers.append("same normalized name appears in multiple counties")
            if not county: blockers.append("county missing")
            if not city: blockers.append("city or safe public service area missing")
            if not products: blockers.append("products or farm activity missing")
            if grades == ["E"]: blockers.append("single grade-E discovery listing needs corroboration")
            if not type_confirmed: blockers.append("directory candidate needs independent farm-operation evidence")
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

    adapters: list[Callable[..., tuple[list[Observation], list[dict[str, Any]], dict[str, Any]]]] = [
        arkansas_directory, arkansas_extension_farms, eatwild_records, pyo_records,
    ]
    for adapter in adapters:
        found, source_logs, raw = adapter(state, config)
        observations.extend(found); logs.extend(source_logs); raw_sources.update(raw)
    official_aggregate = next((log for log in logs if log.get("source_name") == "Arkansas Department of Agriculture — Arkansas Grown directory"), {})
    if official_aggregate.get("error"):
        critical.append(str(official_aggregate["error"]))

    seats, seats_log, seats_text = county_seats(state, config); logs.append(seats_log); raw_sources["county_seat_anchor_text"] = seats_text
    if len(seats) != config["county_count"]: critical.append(f"County-seat anchors expected {config['county_count']}, received {len(seats)}")
    found, source_logs, raw, searched_ok = localharvest_gap_search(state, config, seats)
    observations.extend(found); logs.extend(source_logs); raw_sources.update(raw)

    apply_place_reference(state, config, observations, places)
    geography_logs, geography_errors = enrich_geography(state, config, observations); logs.extend(geography_logs)
    for item in observations:
        if item.county and not item.county_fips: item.county_fips = county_fips.get(item.county, "")
    retained_observations = [item for item in observations if item.promotion_status != "excluded_outside_jurisdiction"]
    excluded_observations = [item for item in observations if item.promotion_status == "excluded_outside_jurisdiction"]
    current_names = read_current_names(); name_counts = Counter(item.candidate_key for item in retained_observations if item.candidate_key)
    for item in retained_observations:
        if name_counts[item.candidate_key] > 1: item.identity_review_status = "exact_normalized_name_group_requires_reconciliation"
        if item.candidate_key in current_names: item.current_release_name_collision = current_names[item.candidate_key]
    observations.sort(key=lambda item: (item.candidate_key, item.source_name, item.source_record_id))
    retained_observations.sort(key=lambda item: (item.candidate_key, item.source_name, item.source_record_id))
    excluded_observations.sort(key=lambda item: (item.candidate_key, item.source_name, item.source_record_id))
    entities, identity_review, qa = reconcile(state, retained_observations)
    eligible = [row for row in entities if row["promotion_status"] == "promotion_eligible_reviewed"]
    entity_counts = Counter(row["county"] for row in entities if row["county"])
    eligible_counts = Counter(row["county"] for row in eligible if row["county"])
    pass_counts: Counter[tuple[str, int]] = Counter()
    for item in retained_observations:
        if item.county: pass_counts[(item.county, item.source_pass)] += 1
    coverage = []
    for row in sorted(counties, key=lambda item: item["county"]):
        county = row["county"]; count = entity_counts[county]
        status = "candidates_found" if count else "searched_none_found" if county in searched_ok else "source_blocked"
        coverage.append({
            "county": county, "county_fips": row["county_fips"],
            "pass_1_observations": pass_counts[(county, 1)], "pass_2_observations": pass_counts[(county, 2)], "pass_3_observations": pass_counts[(county, 3)],
            "candidate_entities": count, "promotion_eligible_entities": eligible_counts[county], "status": status,
            "coverage_note": "Official statewide directory plus market-channel sources and county-seat discovery search reviewed.",
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
        "identity_review_groups": len(identity_review), "current_la_ms_name_collisions": sum(bool(item.current_release_name_collision) for item in retained_observations),
        "counties_total": len(counties), "counties_with_candidates": sum(bool(row["candidate_entities"]) for row in coverage),
        "counties_without_candidates": [row["county"] for row in coverage if not row["candidate_entities"]],
        "counties_with_promotion_eligible_entities": sum(bool(row["promotion_eligible_entities"]) for row in coverage),
        "website_entities": sum(bool(row["website_url"]) for row in entities),
        "social_entities": sum(bool(row["facebook_url"] or row["instagram_url"] or row["tiktok_url"]) for row in entities),
        "direct_contact_entities": sum(bool(row["phone_internal"] or row["email_internal"]) for row in entities),
        "open_qa_items": len(qa), "unresolved_county_observations": sum(not item.county for item in retained_observations),
        "critical_errors": critical,
        "promotion_note": "Coverage-reviewed is not record-verified, approved, promotion-ready, or canonical.",
    }
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
caused deletion or exclusion.

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
| Counties with eligible candidates | {sum(bool(row['promotion_eligible_entities']) for row in coverage)} |

## Source passes

1. Official pass: the Arkansas Department of Agriculture Arkansas Grown directory.
2. Market-channel pass: University of Arkansas direct-sale farms and EatWild.
3. Discovery pass: five PickYourOwn regions plus LocalHarvest searches anchored to all county seats.

## Quality boundaries

- Arkansas Grown includes markets, processors, retailers, and value-added businesses. Named
  profiles without explicit farm-operation evidence remain QA candidates rather than being discarded.
- PickYourOwn closure claims remain retained pending an affirmative append-only curator decision.
- County and city-or-safe-service-area gaps remain explicit blockers in `entities.csv`.
- Outside-state radius results remain in immutable observations and `exclusions.csv`, never as Arkansas entities.
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
