"""Offline, permission-gated quote intake. Never called by training or serving.

No scraper, network client, currency conversion, imputation or model fitting is
provided here. Verification records a human evidence review, not an authenticity
guarantee made by software. Raw batches and evidence are content addressed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator

ROOT = Path(__file__).resolve().parents[2]
IST = ZoneInfo("Asia/Kolkata")
UNKNOWN = Literal["included", "excluded", "unknown"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return value.astimezone(timezone.utc)


def web_url(value: str) -> str:
    url = urlsplit(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("use an HTTPS public page URL without credentials, query or fragment")
    return value


def local_file(root: Path, reference: str) -> Path:
    path = (root / reference).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("evidence must be an existing file inside the evidence directory")
    return path


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Segment(StrictModel):
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure: datetime
    arrival: datetime
    marketing_airline: str = Field(min_length=1)
    operating_airline: str | None = None
    flight_number: str | None = None
    cabin_class: str | None = None
    leg: Literal["outbound", "inbound", "other"] = "outbound"

    @model_validator(mode="after")
    def chronology(self):
        if self.origin == self.destination or aware(self.arrival) <= aware(self.departure):
            raise ValueError("segment endpoints and chronological times must be valid")
        return self


class Quote(StrictModel):
    quote_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    source_id: str = Field(pattern=r"^[a-z0-9_-]{1,80}$")
    source_name: str = Field(min_length=1)
    source_url: str
    source_record_id: str | None = None
    acquisition_method: Literal["manual", "authorized_api"] = "manual"
    environment: Literal["live", "historical", "test", "unknown"] = "unknown"
    collected_at_utc: datetime
    collected_at_local: datetime | None = None
    origin_airport: str = Field(pattern=r"^[A-Z]{3}$")
    destination_airport: str = Field(pattern=r"^[A-Z]{3}$")
    departure_date: date
    return_date: date | None = None
    journey_type: Literal["one_way", "round_trip", "multi_city", "unknown"] = "unknown"
    airline: str | None = None
    operating_airline: str | None = None
    cabin_class: str | None = None
    fare_family: str | None = None
    number_of_passengers: int | None = Field(default=None, strict=True, ge=1, le=9)
    passenger_composition: dict[str, StrictInt] | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    base_fare: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    taxes: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    fees: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    displayed_total: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    total_price_scope: Literal["per_passenger", "complete_booking", "per_segment", "unknown"] = "unknown"
    taxes_status: UNKNOWN = "unknown"
    fees_status: UNKNOWN = "unknown"
    price_per_passenger: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    stops: int | None = Field(default=None, strict=True, ge=0, le=8)
    itinerary_segments: list[Segment] = Field(default_factory=list)
    duration_minutes: int | None = Field(default=None, strict=True, gt=0)
    baggage_details: str | None = None
    refundability: str | None = None
    availability_status: Literal["selectable", "unavailable", "indicative", "unknown"] = "unknown"
    evidence_reference: str | None = None
    evidence_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_terms_reference: str
    reviewed_by: str | None = None
    reviewed_at_utc: datetime | None = None
    # Field -> location in the bound evidence. Do not put inferred assertions here.
    semantic_evidence: dict[str, str] = Field(default_factory=dict)
    original_values: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def coherent(self):
        web_url(self.source_url)
        web_url(self.source_terms_reference)
        collected = aware(self.collected_at_utc)
        if self.collected_at_utc.utcoffset() != timedelta(0):
            raise ValueError("collected_at_utc must have zero offset")
        if collected > utc_now() + timedelta(minutes=5):
            raise ValueError("collection timestamp is in the future")
        if self.collected_at_local is not None:
            if (aware(self.collected_at_local) != collected
                    or self.collected_at_local.utcoffset() != timedelta(hours=5, minutes=30)):
                raise ValueError("local timestamp must be the same instant in India (+05:30)")
        if self.origin_airport == self.destination_airport:
            raise ValueError("origin and destination must differ")
        if self.departure_date < collected.astimezone(IST).date():
            raise ValueError("departure precedes collection date")
        if self.journey_type == "one_way" and self.return_date is not None:
            raise ValueError("one-way quote cannot have a return date")
        if self.journey_type == "round_trip" and self.return_date is None:
            raise ValueError("round-trip requires its actual return date")
        if self.return_date is not None and self.return_date < self.departure_date:
            raise ValueError("return precedes departure")
        if self.passenger_composition is not None:
            if (set(self.passenger_composition) - {"adults", "children", "infants"}
                    or any(type(v) is not int or v < 0 for v in self.passenger_composition.values())
                    or self.number_of_passengers is None
                    or sum(self.passenger_composition.values()) != self.number_of_passengers):
                raise ValueError("passenger composition must match the passenger count")
        if self.price_per_passenger is not None:
            # No implicit division of mixed-passenger or multiple-passenger totals.
            if (self.displayed_total is None or self.total_price_scope != "per_passenger"
                    and self.number_of_passengers != 1
                    or self.total_price_scope not in {"per_passenger", "complete_booking"}
                    or self.price_per_passenger != self.displayed_total):
                raise ValueError("per-passenger price must be explicitly comparable with the total")
        if (self.taxes_status == self.fees_status == "included"
                and all(v is not None for v in [self.base_fare, self.taxes, self.fees, self.displayed_total])
                and abs(self.base_fare + self.taxes + self.fees - self.displayed_total) > Decimal("0.01")):
            raise ValueError("same-scope base, taxes and fees do not sum to the total")
        if self.reviewed_at_utc is not None:
            if aware(self.reviewed_at_utc) < collected or aware(self.reviewed_at_utc) > utc_now() + timedelta(minutes=5):
                raise ValueError("evidence review timestamp is inconsistent")
        self._segments_coherent()
        return self

    def _segments_coherent(self):
        segments = self.itinerary_segments
        if not segments:
            return
        for i, segment in enumerate(segments):
            if aware(segment.departure) < aware(self.collected_at_utc):
                raise ValueError("segment departs before the quote was collected")
            if i and (segments[i - 1].destination != segment.origin
                      or aware(segments[i - 1].arrival) > aware(segment.departure)):
                raise ValueError("segments must form a chronological connected itinerary")
        outbound = [s for s in segments if s.leg == "outbound"]
        inbound = [s for s in segments if s.leg == "inbound"]
        if (segments[0].origin != self.origin_airport
                or aware(segments[0].departure).astimezone(IST).date() != self.departure_date):
            raise ValueError("segments disagree with departure date or origin")
        if self.journey_type in {"one_way", "round_trip"}:
            if not outbound or outbound[-1].destination != self.destination_airport:
                raise ValueError("outbound must reach the quoted destination")
            if any(s.leg == "other" for s in segments) or segments != outbound + inbound:
                raise ValueError("outbound segments must precede inbound segments")
        if self.journey_type == "one_way" and (inbound or segments[-1].destination != self.destination_airport):
            raise ValueError("one-way segments must contain only the outbound journey")
        if self.journey_type == "round_trip":
            if (not inbound or inbound[0].origin != self.destination_airport
                    or inbound[-1].destination != self.origin_airport
                    or aware(inbound[0].departure).astimezone(IST).date() != self.return_date):
                raise ValueError("return booking must include its connected return itinerary")
        expected_stops = max(0, len(outbound) - 1) + max(0, len(inbound) - 1)
        if self.stops is not None and self.journey_type in {"one_way", "round_trip"} and self.stops != expected_stops:
            raise ValueError("stops is total connections across the supplied outbound and inbound")
        if self.duration_minutes is not None and self.journey_type == "one_way":
            elapsed = (aware(segments[-1].arrival) - aware(segments[0].departure)).total_seconds() / 60
            if abs(elapsed - self.duration_minutes) > 1:
                raise ValueError("duration disagrees with one-way segment elapsed time")

    def identities(self):
        physical = [{"origin": s.origin, "destination": s.destination,
                     "departure": aware(s.departure).isoformat()} for s in self.itinerary_segments]
        # Incomplete observations are conservatively grouped by route/travel dates.
        if not physical:
            physical = [{"origin": self.origin_airport, "destination": self.destination_airport,
                         "departure": str(self.departure_date), "return": str(self.return_date)}]
        itinerary = {"segments": physical, "journey_type": self.journey_type,
                     "airline": self.airline, "cabin_class": self.cabin_class,
                     "fare_family": self.fare_family, "baggage": self.baggage_details,
                     "refundability": self.refundability, "currency": self.currency,
                     "scope": self.total_price_scope, "passengers": self.passenger_composition}
        return digest(encoded(itinerary)), [digest(encoded(s)) for s in physical]


class SourceGrant(StrictModel):
    source_id: str
    hosts: list[str]
    methods: list[Literal["manual", "authorized_api"]]
    collection_allowed: bool = Field(default=False, strict=True)
    storage_allowed: bool = Field(default=False, strict=True)
    ml_use_allowed: bool = Field(default=False, strict=True)
    no_cost_confirmed: bool = Field(default=False, strict=True)
    valid_from: datetime
    valid_until: datetime
    retention_until: datetime
    daily_observation_limit: int = Field(strict=True, gt=0)
    terms_url: str
    reviewed_by: str = Field(min_length=1)
    reviewed_at_utc: datetime
    permission_reference: str
    permission_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid(self):
        web_url(self.terms_url)
        if not self.hosts or not self.methods:
            raise ValueError("source domains and authorized methods must be explicit")
        if not (aware(self.reviewed_at_utc) <= utc_now()
                and aware(self.valid_from) < aware(self.valid_until)
                and aware(self.retention_until) >= aware(self.valid_until)):
            raise ValueError("permission review, access and retention dates must be valid")
        return self


def load_grants(path: Path, evidence_root: Path) -> dict[str, SourceGrant]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if set(obj) != {"sources"}:
        raise ValueError("permission file must contain only sources")
    result = {}
    for row in obj["sources"]:
        grant = SourceGrant.model_validate(row)
        if grant.source_id in result:
            raise ValueError("duplicate source permission")
        evidence = local_file(evidence_root, grant.permission_reference).read_bytes()
        if digest(evidence) != grant.permission_sha256:
            raise ValueError("permission evidence checksum mismatch")
        result[grant.source_id] = grant
    return result


REQUIRED_EVIDENCE = {"currency", "taxes_status", "fees_status", "total_price_scope",
                     "passenger_composition", "availability_status", "journey_type",
                     "cabin_class", "itinerary_segments", "collected_at_utc", "departure_date",
                     "displayed_total"}


def target_issues(quote: Quote, grant: SourceGrant, evidence_root: Path, airport_codes: set[str]) -> list[str]:
    issues = []
    if not grant.ml_use_allowed:
        issues.append("ml_permission_not_established")
    if quote.environment not in {"live", "historical"}:
        issues.append("non_genuine_or_unknown_environment")
    if quote.currency != "INR":
        issues.append("verified_inr_required_no_fx_conversion")
    if quote.displayed_total is not None and quote.displayed_total != quote.displayed_total.quantize(Decimal("0.01")):
        issues.append("total_has_fractional_paise")
    if quote.taxes_status != "included" or quote.fees_status != "included":
        issues.append("all_in_total_not_established")
    if (quote.number_of_passengers != 1 or quote.passenger_composition != {"adults": 1}
            or quote.total_price_scope not in {"per_passenger", "complete_booking"}):
        issues.append("single_adult_total_required")
    if quote.displayed_total is None or quote.availability_status != "selectable":
        issues.append("selectable_total_missing")
    if quote.journey_type not in {"one_way", "round_trip"}:
        issues.append("journey_type_outside_initial_target")
    if not quote.airline or not quote.cabin_class or not quote.itinerary_segments:
        issues.append("itinerary_airline_or_cabin_missing")
    if any(not s.flight_number or not s.cabin_class or s.cabin_class != quote.cabin_class
           for s in quote.itinerary_segments):
        issues.append("flight_number_or_uniform_segment_cabin_missing")
    if quote.itinerary_segments and quote.airline != quote.itinerary_segments[0].marketing_airline:
        issues.append("airline_disagrees_with_first_marketing_carrier")
    endpoints = {quote.origin_airport, quote.destination_airport}
    endpoints.update(s.origin for s in quote.itinerary_segments)
    endpoints.update(s.destination for s in quote.itinerary_segments)
    if not endpoints <= airport_codes:
        issues.append("airport_not_in_reviewed_indian_iata_directory")
    needed = REQUIRED_EVIDENCE | ({"return_date"} if quote.journey_type == "round_trip" else set())
    if not needed <= {key for key, value in quote.semantic_evidence.items() if value.strip()}:
        issues.append("semantic_evidence_locations_missing")
    if not quote.reviewed_by or quote.reviewed_at_utc is None:
        issues.append("human_evidence_review_missing")
    if not quote.evidence_reference or not quote.evidence_sha256:
        issues.append("bound_quote_evidence_missing")
    else:
        try:
            if digest(local_file(evidence_root, quote.evidence_reference).read_bytes()) != quote.evidence_sha256:
                issues.append("quote_evidence_checksum_mismatch")
        except ValueError:
            issues.append("quote_evidence_unavailable")
    return issues


JSON_FIELDS = {"passenger_composition", "itinerary_segments", "semantic_evidence", "original_values"}
INT_FIELDS = {"number_of_passengers", "stops", "duration_minutes"}


def parse_row(row: dict) -> Quote:
    value = {}
    for key, text in row.items():
        if key is None:
            raise ValueError("extra CSV values without headers")
        if text is None or text.strip() == "":
            continue
        if key in JSON_FIELDS:
            value[key] = json.loads(text)
        elif key in INT_FIELDS:
            value[key] = int(text)
        else:
            value[key] = text
    return Quote.model_validate(value)


def write_once(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as out:
            out.write(content)
    except FileExistsError:
        if path.read_bytes() != content:
            raise ValueError("immutable file checksum conflict")


@contextmanager
def locked(store: Path):
    store.mkdir(parents=True, exist_ok=True)
    lock = store / ".ingest.lock"
    try:
        with lock.open("x", encoding="utf-8") as out:
            out.write("Intake in progress. Remove only after confirming the owner process ended.")
    except FileExistsError as error:
        raise RuntimeError("another intake owns the store lock") from error
    try:
        yield
    finally:
        lock.unlink()


def read_records(store: Path) -> list[dict]:
    records = []
    for path in sorted((store / "batches").glob("*.json")):
        raw = path.read_bytes()
        if digest(raw) != path.stem:
            raise ValueError("immutable batch was modified")
        batch = json.loads(raw)
        raw_path = store / "raw" / (batch["raw_sha256"] + ".csv")
        if digest(raw_path.read_bytes()) != batch["raw_sha256"]:
            raise ValueError("immutable raw intake was modified")
        permission_path = store / "permissions" / (batch["permission_sha256"] + ".json")
        if digest(permission_path.read_bytes()) != batch["permission_sha256"]:
            raise ValueError("immutable permission snapshot was modified")
        records.extend(batch["records"])
    return records


def resolved_records(store: Path) -> tuple[list[dict], dict]:
    records = read_records(store)
    by_id, by_snapshot = {}, {}
    for row in records:
        if row["status"] == "quarantine":
            continue
        quote = Quote.model_validate(row["quote"])
        value = quote.model_dump(mode="json", exclude={"quote_id", "source_record_id", "evidence_reference",
                    "evidence_sha256", "reviewed_by", "reviewed_at_utc", "semantic_evidence", "original_values", "collected_at_local"})
        fingerprint = digest(encoded(value))
        row["fingerprint"] = fingerprint
        by_id.setdefault(quote.quote_id, set()).add(fingerprint)
        snapshot = (quote.source_id, row["itinerary_id"], aware(quote.collected_at_utc).isoformat())
        row["snapshot_key"] = snapshot
        by_snapshot.setdefault(snapshot, set()).add(fingerprint)
    conflicts = {key for key, values in by_id.items() if len(values) > 1}
    conflicts.update(r["quote_id"] for r in records if r["status"] == "quarantine" and r.get("quote_id") in by_id)
    bad_snapshots = {key for key, values in by_snapshot.items() if len(values) > 1}
    clean, seen = [], set()
    duplicate_count, conflict_count, quarantined = 0, 0, 0
    for row in records:
        if row["status"] == "quarantine":
            quarantined += 1
        elif row["quote"]["quote_id"] in conflicts or row["snapshot_key"] in bad_snapshots:
            conflict_count += 1
        elif row["fingerprint"] in seen:
            duplicate_count += 1
        else:
            seen.add(row["fingerprint"])
            clean.append(row)
    return clean, {"raw_rows": len(records), "malformed_rows": quarantined,
                   "duplicate_snapshots": duplicate_count, "conflicted_rows_excluded": conflict_count}


def intake(csv_path: Path, permissions: Path, evidence_root: Path, store: Path,
           airport_codes: set[str], commit: bool = False) -> dict:
    raw = csv_path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    headers = reader.fieldnames or []
    if (len(set(headers)) != len(headers) or set(headers) - set(Quote.model_fields)
            or not {"quote_id", "source_id", "source_url", "source_terms_reference"} <= set(headers)):
        raise ValueError("missing, duplicate or unknown CSV headers")
    rows = list(reader)
    grants = load_grants(permissions, evidence_root)
    now = utc_now()
    parsed, evidence_blobs = [], {}
    existing = read_records(store)
    # A denied source aborts before preserving any of its payload, including raw CSV.
    for line, row in enumerate(rows, 2):
        grant = grants.get(row.get("source_id", ""))
        if (grant is None or not grant.collection_allowed or not grant.storage_allowed
                or not grant.no_cost_confirmed or now > aware(grant.retention_until)):
            raise PermissionError(f"row {line}: collection/storage/no-cost permission unavailable")
        if (row.get("acquisition_method") or "manual") not in grant.methods:
            raise PermissionError(f"row {line}: acquisition method not authorized")
        if row.get("source_terms_reference") != grant.terms_url or urlsplit(row.get("source_url", "")).hostname not in grant.hosts:
            raise PermissionError(f"row {line}: source URL or terms outside permission")
        try:
            collection_time = aware(datetime.fromisoformat(row.get("collected_at_utc", "").replace("Z", "+00:00")))
        except (TypeError, ValueError) as error:
            raise PermissionError(f"row {line}: cannot bind collection time to permission") from error
        if not aware(grant.valid_from) <= collection_time < aware(grant.valid_until):
            raise PermissionError(f"row {line}: quote collection outside permitted period")
        try:
            quote = parse_row(row)
        except (ValueError, ValidationError, TypeError) as error:
            parsed.append({"line": line, "status": "quarantine", "issues": ["malformed_quote_schema"],
                           "source_id": grant.source_id, "quote_id": row.get("quote_id"),
                           "invalid_fields": [".".join(str(v) for v in e["loc"]) for e in error.errors()] if isinstance(error, ValidationError) else ["CSV_or_JSON"],
                           "collection_day_ist": collection_time.astimezone(IST).date().isoformat()})
            continue
        if not aware(grant.valid_from) <= aware(quote.collected_at_utc) < aware(grant.valid_until):
            raise PermissionError(f"row {line}: quote collection outside permitted period")
        issues = target_issues(quote, grant, evidence_root, airport_codes)
        itinerary_id, leg_keys = quote.identities()
        record = {"line": line, "status": "research_only" if issues else "verified_target",
                  "issues": issues, "quote": quote.model_dump(mode="json"),
                  "itinerary_id": itinerary_id, "leg_keys": leg_keys,
                  "collection_day_ist": aware(quote.collected_at_utc).astimezone(IST).date().isoformat(),
                  "permission": grant.model_dump(mode="json")}
        parsed.append(record)
        if quote.evidence_reference and quote.evidence_sha256 and "quote_evidence_checksum_mismatch" not in issues:
            try:
                blob = local_file(evidence_root, quote.evidence_reference).read_bytes()
                if digest(blob) == quote.evidence_sha256:
                    evidence_blobs[quote.evidence_sha256] = blob
            except ValueError:
                pass
    # Count every new raw observation against permission limits, not just targets.
    counts = {}
    for record in existing + parsed:
        source_id = record["quote"]["source_id"] if "quote" in record else record.get("source_id")
        if source_id:
            key = (source_id, record["collection_day_ist"])
            counts[key] = counts.get(key, 0) + 1
    # Exact raw/config replay is idempotent, including quotas.
    request_hash = digest(raw + permissions.read_bytes())
    replay = store / "receipts" / (request_hash + ".json")
    if replay.exists():
        return {**json.loads(replay.read_text()), "replayed": True}
    # Recover an interrupted commit that wrote the immutable batch but not its
    # convenience receipt. Do not count the same acquisition twice against quota.
    for path in (store / "batches").glob("*.json"):
        prior = json.loads(path.read_bytes())
        if prior.get("request_hash") == request_hash:
            if commit:
                write_once(replay, encoded(prior["receipt"]))
            return {**prior["receipt"], "replayed": True}
    if any(count > grants[key[0]].daily_observation_limit for key, count in counts.items() if key[0] in grants):
        raise PermissionError("daily observation permission limit exceeded")
    result = {"raw_sha256": digest(raw), "rows": len(rows), "verified_targets": sum(r["status"] == "verified_target" for r in parsed),
              "research_only": sum(r["status"] == "research_only" for r in parsed),
              "quarantined": sum(r["status"] == "quarantine" for r in parsed), "committed": commit,
              "note": "provisional counts; summary removes all conflicted/duplicate snapshots"}
    if commit:
        batch = {"raw_sha256": digest(raw), "permission_sha256": digest(permissions.read_bytes()),
                 "request_hash": request_hash, "receipt": result, "records": parsed}
        payload = encoded(batch)
        write_once(store / "raw" / (digest(raw) + ".csv"), raw)
        write_once(store / "permissions" / (digest(permissions.read_bytes()) + ".json"), permissions.read_bytes())
        for grant in grants.values():
            blob = local_file(evidence_root, grant.permission_reference).read_bytes()
            write_once(store / "evidence" / (digest(blob) + ".bin"), blob)
        for sha, blob in evidence_blobs.items():
            write_once(store / "evidence" / (sha + ".bin"), blob)
        write_once(store / "batches" / (digest(payload) + ".json"), payload)
        write_once(replay, encoded(result))
    return result


def summary(store: Path) -> dict:
    clean, quality = resolved_records(store)
    now = utc_now()
    usable = []
    for row in clean:
        if row["status"] != "verified_target" or now > aware(datetime.fromisoformat(row["permission"]["retention_until"])):
            continue
        quote = row["quote"]
        hashes = [quote["evidence_sha256"], row["permission"]["permission_sha256"]]
        if all((store / "evidence" / (sha + ".bin")).is_file()
               and digest((store / "evidence" / (sha + ".bin")).read_bytes()) == sha for sha in hashes):
            usable.append(row)
    return {**quality, "retained_unique_snapshots": len(clean), "verified_targets": len(usable),
            "research_only_or_unusable": len(clean) - len(usable),
            "unique_itineraries": len({r["itinerary_id"] for r in usable}),
            "collection_days_ist": len({r["collection_day_ist"] for r in usable}),
            "itinerary_days": len({(r["itinerary_id"], r["collection_day_ist"]) for r in usable}),
            "genuine_round_trip_targets": sum(r["quote"]["journey_type"] == "round_trip" for r in usable),
            "training_automatically_enabled": False}


def temporal_split(records: list[dict], boundaries: list[datetime]) -> dict:
    cuts = [aware(v) for v in boundaries]
    if len(cuts) != 3 or cuts != sorted(set(cuts)):
        raise ValueError("supply three distinct increasing UTC boundaries")
    rows = [r for r in records if r["status"] == "verified_target"]
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    legs = {}
    for i, row in enumerate(rows):
        for leg in row["leg_keys"]:
            if leg in legs:
                parent[find(i)] = find(legs[leg])
            legs[leg] = i
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(find(i), []).append(row)
    result = {key: [] for key in ["train", "validation", "calibration", "test", "purged_cross_boundary"]}
    for group in groups.values():
        positions = {sum(aware(datetime.fromisoformat(r["quote"]["collected_at_utc"])) >= cut for cut in cuts) for r in group}
        label = list(result)[next(iter(positions))] if len(positions) == 1 else "purged_cross_boundary"
        result[label].extend(r["quote"]["quote_id"] for r in group)
    return {"boundaries_utc": [c.isoformat() for c in cuts], "assignments": result,
            "ready_for_experiment_review": all(bool(result[k]) for k in ["train", "validation", "calibration", "test"]),
            "policy": "Shared segment components stay together; crossing components are purged. Readiness is structural only, not statistical approval."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["template", "schema", "validate", "ingest", "summary", "freeze-split"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--permissions", type=Path, default=ROOT / "config/quote_permissions.example.json")
    parser.add_argument("--evidence-root", type=Path, default=ROOT / "data/quotes/evidence_incoming")
    parser.add_argument("--store", type=Path, default=ROOT / "data/quotes")
    parser.add_argument("--boundary", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.command in {"template", "schema"}:
            if args.output is None:
                parser.error("--output is required")
            if args.command == "schema":
                write_once(args.output, encoded({"quote": Quote.model_json_schema(), "source_grant": SourceGrant.model_json_schema()}))
            else:
                buffer = io.StringIO(newline="")
                csv.writer(buffer).writerow(Quote.model_fields)
                write_once(args.output, buffer.getvalue().encode("utf-8"))
            result = {"created": str(args.output), "sample_observations": 0}
        elif args.command == "summary":
            result = summary(args.store)
        elif args.command == "freeze-split":
            if args.output is None or not args.output.resolve().is_relative_to(args.store.resolve()):
                parser.error("split manifests must be written inside the private store")
            with locked(args.store):
                records, _ = resolved_records(args.store)
                if summary(args.store)["verified_targets"] != sum(r["status"] == "verified_target" for r in records):
                    raise ValueError("evidence or permission retention invalid; review before freezing")
                result = temporal_split(records, [datetime.fromisoformat(v) for v in args.boundary])
                result["dataset_sha256"] = digest(encoded(records))
                write_once(args.output, encoded(result))
        else:
            if args.input is None:
                parser.error("--input is required")
            with (ROOT / "reports/india_airport_master.csv").open(encoding="utf-8", newline="") as inp:
                codes = {r["iata_code"] for r in csv.DictReader(inp) if r["iata_code"]}
            with locked(args.store):
                result = intake(args.input, args.permissions, args.evidence_root, args.store, codes, args.command == "ingest")
        print(json.dumps(result, indent=2))
    except (ValueError, PermissionError, RuntimeError, OSError) as error:
        # Never echo raw payloads, URLs with tokens, evidence or Pydantic input values.
        args.store.mkdir(parents=True, exist_ok=True)
        with (args.store / "failures.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps({"at_utc": utc_now().isoformat(), "command": args.command,
                                  "error_type": type(error).__name__}) + "\n")
        print(json.dumps({"error": type(error).__name__, "message": "Intake stopped. Check source permission, schema, evidence hashes and private store integrity; no model changed."}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
