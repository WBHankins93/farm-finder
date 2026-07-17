#!/usr/bin/env python3
"""Build and consume FarmFinder cross-state referral inputs.

Referral inputs are deliberately outside ``research/state-expansions/<ST>/``.
The state release remains the four-file contract; a referral is an additive
collection input for the farm's home state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
COLLECTION_INPUT_ROOT = ROOT / "research" / "collection-inputs"

STATE_NAMES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}
STATE_CODES = frozenset(STATE_NAMES)
STATE_NAME_TO_CODE = {name.casefold(): code for code, name in STATE_NAMES.items()}

REFERRAL_FIELDS = [
    "referral_id",
    "farm_name",
    "normalized_name",
    "home_state",
    "collecting_state",
    "observed_market_state",
    "observed_market_channel",
    "products",
    "business_types",
    "evidence",
    "source_url",
    "retrieval_date",
    "source_record_id",
    "source_decision_id",
    "evidence_grade",
    "entity_type",
    "status",
]
REQUIRED_REFERRAL_FIELDS = frozenset({
    "referral_id", "farm_name", "home_state", "collecting_state",
    "observed_market_state", "observed_market_channel", "evidence",
    "source_url", "retrieval_date", "status",
})
VALID_REFERRAL_STATUSES = frozenset({"open", "consumed"})


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_state(value: str) -> str:
    normalized = clean(value).upper()
    if normalized in STATE_CODES:
        return normalized
    code = STATE_NAME_TO_CODE.get(clean(value).casefold())
    if code:
        return code
    raise ValueError(f"unknown state {value!r}")


def normalize_name(value: str) -> str:
    value = clean(value).casefold().replace("&", " and ").replace("’", "").replace("'", "")
    tokens = re.sub(r"[^a-z0-9]+", " ", value).strip().split()
    while len(tokens) > 2 and tokens[-1] in {"llc", "inc", "incorporated"}:
        tokens.pop()
    return " ".join(tokens)


def _state_mentions(text: str) -> list[tuple[int, str]]:
    text = clean(text)
    found: list[tuple[int, str]] = []
    for code, name in STATE_NAMES.items():
        for match in re.finditer(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", text, re.I):
            found.append((match.start(), code))
    for match in re.finditer(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])", text):
        code = match.group(1)
        if code in STATE_CODES:
            found.append((match.start(), code))
    return sorted(found)


def infer_home_state(*texts: str, collecting_state: str = "") -> str:
    """Infer the operation's home state from cited location evidence.

    The collecting state is discarded so phrases such as “outside Texas ...
    Louisiana” resolve to Louisiana.  Ambiguous or absent evidence is an error;
    a referral without a home state cannot be routed safely.
    """
    collecting = normalize_state(collecting_state) if collecting_state else ""
    candidates = [(position, code) for text in texts for position, code in _state_mentions(text)
                  if code != collecting]
    if not candidates:
        excerpt = " ".join(clean(text) for text in texts if clean(text))[:240]
        raise ValueError(f"could not infer home state from outside-jurisdiction evidence: {excerpt!r}")
    return sorted(candidates, key=lambda item: item[0])[-1][1]


def state_name(code: str) -> str:
    return STATE_NAMES[normalize_state(code)]


def referral_input_path(home_state: str, *, root: Path = ROOT) -> Path:
    return root / "research" / "collection-inputs" / normalize_state(home_state) / "referrals.csv"


def _valid_source_url(value: str) -> bool:
    parsed = urlparse(clean(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _referral_id(home_state: str, collecting_state: str, farm_name: str, source_id: str) -> str:
    payload = "|".join((home_state, collecting_state, normalize_name(farm_name), source_id))
    return "ref_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _joined(*values: str) -> str:
    return "; ".join(dict.fromkeys(clean(value) for value in values if clean(value)))


def _base_referral(
    *,
    farm_name: str,
    home_state: str,
    collecting_state: str,
    observed_market_channel: str,
    evidence: str,
    source_url: str,
    retrieval_date: str,
    source_record_id: str = "",
    source_decision_id: str = "",
    evidence_grade: str = "",
    entity_type: str = "",
    products: str = "",
    business_types: str = "",
) -> dict[str, str]:
    home = normalize_state(home_state)
    collecting = normalize_state(collecting_state)
    if home == collecting:
        raise ValueError(f"referral for {farm_name!r} cannot point back to collecting state {collecting}")
    if not clean(farm_name):
        raise ValueError("referral requires a farm name")
    if not clean(evidence):
        raise ValueError(f"referral for {farm_name!r} requires evidence")
    if not _valid_source_url(source_url):
        raise ValueError(f"referral for {farm_name!r} requires a valid source URL")
    try:
        date.fromisoformat(clean(retrieval_date))
    except ValueError as exc:
        raise ValueError(f"referral for {farm_name!r} has invalid retrieval date {retrieval_date!r}") from exc
    record_id = clean(source_record_id) or clean(source_decision_id)
    if not record_id:
        raise ValueError(f"referral for {farm_name!r} requires a source record or decision ID")
    return {
        "referral_id": _referral_id(home, collecting, farm_name, record_id),
        "farm_name": clean(farm_name),
        "normalized_name": normalize_name(farm_name),
        "home_state": home,
        "collecting_state": collecting,
        "observed_market_state": collecting,
        "observed_market_channel": clean(observed_market_channel),
        "products": clean(products),
        "business_types": clean(business_types),
        "evidence": clean(evidence),
        "source_url": clean(source_url),
        "retrieval_date": clean(retrieval_date),
        "source_record_id": clean(source_record_id),
        "source_decision_id": clean(source_decision_id),
        "evidence_grade": clean(evidence_grade),
        "entity_type": clean(entity_type),
        "status": "open",
    }


def referral_from_decision(decision: Mapping[str, Any], collecting_state: str) -> dict[str, str]:
    """Convert an outside-jurisdiction QA decision into a home-state input."""
    if clean(decision.get("exclusion_reason")) != "outside_jurisdiction":
        raise ValueError("only outside_jurisdiction decisions can create referrals")
    collecting = normalize_state(collecting_state)
    evidence = _joined(decision.get("decision_basis", ""), decision.get("notes", ""))
    home = infer_home_state(evidence, decision.get("city", ""), collecting_state=collecting)
    channel = _joined(
        f"{state_name(collecting)} collection source",
        decision.get("business_types", ""),
    )
    source_url = clean(decision.get("source_url")) or clean(decision.get("website_url"))
    return _base_referral(
        farm_name=clean(decision.get("farm_name")),
        home_state=home,
        collecting_state=collecting,
        observed_market_channel=channel,
        products=clean(decision.get("products")),
        business_types=clean(decision.get("business_types")),
        evidence=evidence,
        source_url=source_url,
        retrieval_date=clean(decision.get("retrieved_date")),
        source_decision_id=clean(decision.get("review_id")),
        evidence_grade=clean(decision.get("evidence_grade")),
        entity_type=clean(decision.get("verified_entity_type")),
    )


def referral_from_observation(observation: Mapping[str, Any], collecting_state: str) -> dict[str, str]:
    """Convert a collector's outside-jurisdiction observation into a referral."""
    collecting = normalize_state(collecting_state)
    evidence = _joined(
        observation.get("notes", ""),
        f"Observed by {clean(observation.get('source_name'))} in {state_name(collecting)} collection.",
    )
    home = clean(observation.get("home_state")) or clean(observation.get("source_state"))
    if not home:
        home = infer_home_state(evidence, collecting_state=collecting)
    channel = _joined(clean(observation.get("source_name")), observation.get("business_types", ""))
    return _base_referral(
        farm_name=clean(observation.get("farm_name")),
        home_state=home,
        collecting_state=collecting,
        observed_market_channel=channel or f"{state_name(collecting)} collection source",
        products=clean(observation.get("products")),
        business_types=clean(observation.get("business_types")),
        evidence=evidence,
        source_url=clean(observation.get("source_url")),
        retrieval_date=clean(observation.get("retrieved_date")),
        source_record_id=clean(observation.get("observation_id")),
        evidence_grade=clean(observation.get("evidence_grade")),
        entity_type=clean(observation.get("entity_type_source")),
    )


def read_referrals(home_state: str, *, root: Path = ROOT, open_only: bool = True) -> list[dict[str, str]]:
    path = referral_input_path(home_state, root=root)
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REFERRAL_FIELDS:
            raise ValueError(f"{path}: referral header must be {REFERRAL_FIELDS}")
        rows = list(reader)
    expected_home = normalize_state(home_state)
    for row in rows:
        errors = _validate_referral_row(row, expected_home=expected_home)
        if errors:
            raise ValueError(f"{path}: referral {row.get('referral_id')!r}: {'; '.join(errors)}")
    if open_only:
        rows = [row for row in rows if row["status"] == "open"]
    return rows


def _validate_referral_row(row: Mapping[str, Any], *, expected_home: str = "") -> list[str]:
    errors = [f"missing {field}" for field in sorted(REQUIRED_REFERRAL_FIELDS) if not clean(row.get(field))]
    try:
        home = normalize_state(clean(row.get("home_state")))
        collecting = normalize_state(clean(row.get("collecting_state")))
        if expected_home and home != expected_home:
            errors.append(f"home_state must be {expected_home}")
        if home == collecting:
            errors.append("home_state and collecting_state must differ")
    except ValueError as exc:
        errors.append(str(exc))
    if clean(row.get("status")) not in VALID_REFERRAL_STATUSES:
        errors.append("status must be open or consumed")
    if clean(row.get("source_url")) and not _valid_source_url(clean(row.get("source_url"))):
        errors.append("source_url must be an http(s) URL")
    try:
        if clean(row.get("retrieval_date")):
            date.fromisoformat(clean(row.get("retrieval_date")))
    except ValueError:
        errors.append("retrieval_date must be ISO YYYY-MM-DD")
    return errors


def validate_referral_inputs(*, root: Path = ROOT) -> dict[str, Any]:
    """Validate every staged referral without treating it as a state release."""
    input_root = root / "research" / "collection-inputs"
    errors: list[str] = []
    files = 0
    referrals = 0
    if not input_root.exists():
        return {"status": "passed", "files": 0, "referrals": 0, "errors": []}
    for state_dir in sorted(path for path in input_root.iterdir() if path.is_dir()):
        if not re.fullmatch(r"[A-Z]{2}", state_dir.name):
            errors.append(f"invalid collection-input state directory: {state_dir.name}")
            continue
        for path in sorted(state_dir.iterdir()):
            if path.name != "referrals.csv":
                errors.append(f"unexpected collection input file: {path.relative_to(root)}")
                continue
            files += 1
            try:
                with path.open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    if reader.fieldnames != REFERRAL_FIELDS:
                        errors.append(f"{path}: referral header must be {REFERRAL_FIELDS}")
                        continue
                    rows = list(reader)
            except (OSError, csv.Error) as exc:
                errors.append(f"{path}: {exc}")
                continue
            ids: set[str] = set()
            for row in rows:
                referrals += 1
                errors.extend(
                    f"{path}: referral {row.get('referral_id')!r}: {error}"
                    for error in _validate_referral_row(row, expected_home=state_dir.name)
                )
                referral_id = clean(row.get("referral_id"))
                if referral_id in ids:
                    errors.append(f"{path}: duplicate referral_id {referral_id}")
                ids.add(referral_id)
    return {"status": "passed" if not errors else "failed", "files": files, "referrals": referrals, "errors": errors}


def stage_referrals(referrals: Iterable[Mapping[str, Any]], *, root: Path = ROOT) -> list[Path]:
    """Merge new referrals into per-home-state CSV inputs idempotently."""
    grouped: dict[str, dict[str, dict[str, str]]] = {}
    for referral in referrals:
        row = {field: clean(referral.get(field)) for field in REFERRAL_FIELDS}
        errors = _validate_referral_row(row)
        if errors:
            raise ValueError(f"invalid referral {row.get('referral_id')!r}: {'; '.join(errors)}")
        home = normalize_state(row["home_state"])
        grouped.setdefault(home, {})[row["referral_id"]] = row
    written: list[Path] = []
    for home, incoming in sorted(grouped.items()):
        path = referral_input_path(home, root=root)
        existing: dict[str, dict[str, str]] = {}
        if path.is_file():
            for row in read_referrals(home, root=root, open_only=False):
                existing[row["referral_id"]] = row
        for referral_id, row in incoming.items():
            prior = existing.get(referral_id)
            if prior and prior != row:
                raise ValueError(f"referral {referral_id} changed; referrals are append-only")
            existing[referral_id] = row
        rows = sorted(existing.values(), key=lambda row: (row["retrieval_date"], row["referral_id"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REFERRAL_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        written.append(path)
    return written


def referrals_from_committed_decisions(*, root: Path = ROOT) -> list[dict[str, str]]:
    """Read every committed state decision and build outside-state referrals."""
    referrals: list[dict[str, str]] = []
    state_root = root / "research" / "state-expansions"
    for state_dir in sorted(path for path in state_root.iterdir() if path.is_dir()):
        decisions_path = state_dir / "decisions.csv"
        if not decisions_path.is_file():
            continue
        with decisions_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if clean(row.get("exclusion_reason")) == "outside_jurisdiction":
                    referrals.append(referral_from_decision(row, state_dir.name))
    return referrals


def referral_observation(row: Mapping[str, Any], collecting_state: str) -> dict[str, Any]:
    """Return a neutral QA candidate shape for a collector to wrap in Observation."""
    collecting = normalize_state(collecting_state)
    return {
        "farm_name": clean(row.get("farm_name")),
        "source_name": f"Cross-state referral queue — {state_name(collecting)} market presence",
        "source_url": clean(row.get("source_url")),
        "source_record_id": clean(row.get("referral_id")),
        "retrieved_date": clean(row.get("retrieval_date")),
        "products": clean(row.get("products")),
        "business_types": clean(row.get("business_types")) or clean(row.get("observed_market_channel")),
        "evidence": clean(row.get("evidence")),
        "observed_market_channel": clean(row.get("observed_market_channel")),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    referrals = referrals_from_committed_decisions(root=args.root)
    written = stage_referrals(referrals, root=args.root)
    result = validate_referral_inputs(root=args.root)
    result.update({"generated": len(referrals), "written": [str(path.relative_to(args.root)) for path in written]})
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
