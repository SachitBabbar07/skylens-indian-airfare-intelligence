"""Score recorded SkyLens market responses against independent, verified quote-store outcomes offline."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import sqrt
from pathlib import Path
from statistics import mean, median
from urllib.parse import urlsplit

from backend.app.flight_fares import DOMESTIC_AIRLINES, IST, FlightSearch, LiveQuote
from backend.app.hybrid_estimator import EstimateResponse, select_estimate
from skylens.quotes import ROOT, Quote, aware, digest, encoded, local_file, resolved_records, summary, temporal_split, utc_now


# These are evaluation strata, never inputs to pricing or a provider lookup.
METROS = {"BLR", "BOM", "CCU", "DEL", "HYD", "MAA"}
MAX_QUOTE_GAP = timedelta(minutes=15)
MIN_BANDS = 20


def route_group(origin: str, destination: str) -> str:
    return "_to_".join("metro" if point in METROS else "regional" for point in (origin, destination))


def norm(name: str) -> str:
    return "".join(c for c in name.casefold() if c.isalnum())


@dataclass
class Capture:
    captured: datetime
    computed: datetime
    request: FlightSearch
    quotes: list[LiveQuote]
    response: EstimateResponse

    @classmethod
    def read(cls, data: dict):
        captured, computed = (aware(datetime.fromisoformat(data[k])) for k in ("captured_at", "computed_at"))
        request = FlightSearch.model_validate(data["request"], context={"as_of_date": captured.astimezone(IST).date()})
        quotes = [LiveQuote.model_validate(q) for q in data["quotes"]]
        response = EstimateResponse.model_validate(data["response"])
        if computed < captured or computed > utc_now() or any(q.retrieved_at > captured for q in quotes):
            raise ValueError("Capture, offer and computation timestamps are inconsistent.")
        # Recompute the production market selection without querying a provider.
        # A changed algorithm must be identified as a new computation.
        if response.estimation_method == "market_reference":
            replay = select_estimate(request, None, quotes, coverage_status=response.coverage_status,
                                     market_status=response.source_status.market,
                                     model_status=response.source_status.model).response
            if replay != response:
                raise ValueError("Archived market response disagrees with the recorded offers and estimator.")
        return cls(captured, computed, request, quotes, response)


def matches(c: Capture, label: Quote, allowed: set[tuple[str, str]]) -> bool:
    request, response = c.request, c.response
    if (response.estimation_method != "market_reference" or response.price_scope != "party_total"
            or request.travellers.total != label.number_of_passengers
            or not label.passenger_composition
            or any(label.passenger_composition.get(k, 0) != v for k, v in request.travellers.model_dump().items())
            or (request.origin, request.destination, request.departure_date, request.return_date, request.journey)
            != (label.origin_airport, label.destination_airport, label.departure_date, label.return_date, label.journey_type)
            or norm(request.cabin) != norm(label.cabin_class or "")
            or label.currency != response.currency or label.currency != "INR"
            or label.taxes_status != response.taxes or label.fees_status != response.fees
            or (response.taxes, response.fees) != ("included", "included")
            or label.total_price_scope not in {"per_passenger", "complete_booking"}
            or (label.total_price_scope == "per_passenger" and label.number_of_passengers != 1)
            or label.availability_status != "selectable" or label.displayed_total is None
            or label.collected_at_utc < c.computed or label.collected_at_utc > c.computed + MAX_QUOTE_GAP):
        return False
    # Even an alias or a downstream reseller needs an explicit lineage review.
    source_ids = {norm(label.source_id), norm(label.source_name), norm(urlsplit(label.source_url).hostname or "")}
    sources = {q.source_name for q in c.quotes}
    if not sources or any((name, label.source_id) not in allowed or norm(name) in source_ids for name in sources):
        return False
    # The adapter currently retains only leg-level timings. Connections cannot
    # be positively matched to every intermediate segment from those fields.
    segments = label.itinerary_segments
    if not segments or label.stops not in {None, 0} or norm(label.airline or "") != norm(segments[0].marketing_airline):
        return False
    if not response.stop_profile or any(stop != 0 for stop in response.stop_profile):
        return False
    expected_legs = ["outbound"] if request.journey == "one_way" else ["outbound", "inbound"]
    if [s.leg for s in segments] != expected_legs or any(not s.flight_number for s in segments):
        return False
    airline = DOMESTIC_AIRLINES.get(request.airline)
    for offer in c.quotes:
        if (offer.journey != request.journey or offer.cabin != request.cabin or offer.travellers != request.travellers
                or (offer.fare.currency, offer.fare.basis, offer.fare.taxes, offer.fare.fees)
                != (response.currency, response.price_scope, response.taxes, response.fees)
                or offer.baggage != label.baggage_details or offer.conditions != label.refundability or label.fare_family
                or len(offer.legs) != len(segments)):
            continue
        if all(leg.stops == 0 and (leg.origin, leg.destination, leg.departure, leg.arrival) ==
               (s.origin, s.destination, s.departure, s.arrival)
               and [norm(v) for v in leg.airlines] == [norm(s.marketing_airline)]
               and [norm(v) for v in leg.flight_numbers] == [norm(s.flight_number)]
               and norm(s.cabin_class or "") == norm(request.cabin)
               and (airline is None or norm(airline) == norm(s.marketing_airline))
               for leg, s in zip(offer.legs, segments)):
            # A complete matching offer still has to pass production checks
            # (e.g. the provider's stated duration against its timestamps).
            return select_estimate(request, None, [offer], coverage_status="unsupported",
                                   market_status="available").response.estimation_method == "market_reference"
    return False


def metrics(rows):
    errors = [prediction - price for prediction, price, _ in rows]
    absolute = list(map(abs, errors))
    hits = [hit for _, _, hit in rows if hit is not None]
    return {
        "n": len(rows), "mae_inr": mean(absolute) if rows else None,
        "rmse_inr": sqrt(mean(e * e for e in errors)) if rows else None,
        "bias_inr": mean(errors) if rows else None, "median_absolute_error_inr": median(absolute) if rows else None,
        "mape_percent": mean(100 * abs(p - y) / y for p, y, _ in rows) if rows else None,
        "band_n": len(hits), "band_hits": sum(hits), "band_coverage": mean(hits) if len(hits) >= MIN_BANDS else None,
    }


def evaluate(captures: list[dict], targets: list[Quote], allowed: set[tuple[str, str]], test_start: datetime | None):
    """Pair already admitted test targets with captures. No source fits or calibrates a parameter here."""
    unique = {}
    skipped = Counter()
    for data in captures:
        capture = Capture.read(data)
        key = capture.captured, encoded(capture.request.model_dump(mode="json"))
        if key in unique:
            if capture != unique[key]:
                raise ValueError("Conflicting market captures for one search and timestamp.")
            skipped["duplicate_capture"] += 1
        else:
            unique[key] = capture
    groups = defaultdict(list)
    by_query = defaultdict(list)
    for label in sorted(targets, key=lambda q: (q.collected_at_utc, q.quote_id)):
        by_query[label.origin_airport, label.destination_airport, label.departure_date].append(label)

    # Block shared physical legs from earlier captured experiments even when a
    # target quote itself appears only once in the private store.
    prior_legs = [leg for c in unique.values() if test_start is not None and c.captured < test_start
                  for q in c.quotes for leg in q.legs]
    used = {(leg.origin, leg.destination, leg.departure) for leg in prior_legs}
    # Collapsed connection records cannot reveal which intermediate segment
    # was shared. Exclude targets inside those earlier leg windows.
    prior_connections = [leg for leg in prior_legs if leg.stops != 0]
    capture_counts = Counter(route_group(c.request.origin, c.request.destination) for c in unique.values())
    overall = []
    for _, c in sorted(unique.items(), key=lambda item: (item[1].computed, item[0])):
        r = c.response
        if r.estimation_method != "market_reference":
            skipped["no_market_estimate"] += 1
            continue
        if (r.currency, r.taxes, r.fees) != ("INR", "included", "included"):
            skipped["incompatible_target_terms"] += 1
            continue
        if test_start is None:
            skipped["no_frozen_targets"] += 1
            continue
        oldest_input = min(q.retrieved_at for q in c.quotes)
        if oldest_input < test_start:
            skipped["outside_frozen_holdout"] += 1
            continue
        labels = by_query[c.request.origin, c.request.destination, c.request.departure_date]
        for label in labels:
            # Keep the oldest input and newest outcome within the same predeclared window.
            if label.collected_at_utc - oldest_input > MAX_QUOTE_GAP:
                continue
            legs = {(s.origin, s.destination, s.departure) for s in label.itinerary_segments}
            blocked = any(leg.departure <= s.departure and s.arrival <= leg.arrival
                          for s in label.itinerary_segments for leg in prior_connections)
            if legs & used or blocked or not matches(c, label, allowed):
                continue
            used.update(legs)
            truth = float(label.displayed_total)
            band = (r.estimated_low <= label.displayed_total <= r.estimated_high
                    if r.range_kind == "interquartile" else None)
            row = (float(r.estimated_median), truth, band)
            overall.append(row)
            groups[route_group(c.request.origin, c.request.destination)].append(row)
            break  # One independent outcome per search, in collection order.
        else:
            skipped["no_distinct_independent_comparable_outcome"] += 1
    strata = [f"{left}_to_{right}" for left in ("metro", "regional") for right in ("metro", "regional")]
    return {"captures": len(captures), "unique_captures": len(unique), "test_targets": len(targets),
            "overall": metrics(overall), "route_groups": {g: {"capture_n": capture_counts[g], **metrics(groups[g])}
                                                        for g in strata}, "skipped": dict(skipped)}


def evaluate_store(store: Path, captures: list[dict], manifest: Path | None, allowed: set[tuple[str, str]]) -> dict:
    records, _ = resolved_records(store)
    quality = summary(store)
    verified = [r for r in records if r["status"] == "verified_target"]
    if len(verified) != quality["verified_targets"]:
        raise ValueError("Quote evidence or permission retention has changed.")
    targets, start = [], None
    if verified or manifest:
        if not manifest:
            raise ValueError("A frozen chronological split is required for scoring admitted targets.")
        frozen = json.loads(manifest.read_text(encoding="utf-8"))
        boundaries = [aware(datetime.fromisoformat(v)) for v in frozen["boundaries_utc"]]
        split = temporal_split(records, boundaries)
        if frozen.get("dataset_sha256") != digest(encoded(records)) or frozen.get("assignments") != split["assignments"]:
            raise ValueError("Frozen split does not match quote-store contents and shared-flight assignments.")
        test_ids = set(split["assignments"]["test"])
        targets = [Quote.model_validate(r["quote"]) for r in verified if r["quote"]["quote_id"] in test_ids]
        start = boundaries[-1]
    return {**evaluate(captures, targets, allowed, start), "verified_targets": len(verified),
            "test_start_utc": start.isoformat() if start else None, "quote_store_quality": quality}


def load_pairs(path: Path | None) -> set[tuple[str, str]]:
    if path is None:
        return set()
    pairs = set()
    for row in json.loads(path.read_text(encoding="utf-8")):
        if (not row["reviewed_by"].strip() or not row["provider"].strip() or not row["independent_source_id"].strip()
                or digest(local_file(path.parent, row["evidence_reference"]).read_bytes()) != row["evidence_sha256"]):
            raise ValueError("Independent acquisition review or its evidence is missing.")
        pairs.add((row["provider"], row["independent_source_id"]))
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=ROOT / "data/quotes")
    parser.add_argument("--captures", type=Path, help="Authorized private capture JSONL")
    parser.add_argument("--split", type=Path, help="Frozen quote-store split manifest")
    parser.add_argument("--independent-pairs", type=Path, help="Private reviewed source-pair evidence manifest")
    args = parser.parse_args()
    captures = [] if args.captures is None else [
        json.loads(line) for line in args.captures.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    result = evaluate_store(args.store, captures, args.split, load_pairs(args.independent_pairs))
    if args.captures:
        result["captures_sha256"] = digest(args.captures.read_bytes())
    if args.split:
        result["split_sha256"] = digest(args.split.read_bytes())
    if args.independent_pairs:
        result["independent_pairs_sha256"] = digest(args.independent_pairs.read_bytes())
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
