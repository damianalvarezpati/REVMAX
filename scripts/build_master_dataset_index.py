#!/usr/bin/env python3
"""
Build a professional master dataset catalog for RevMax.

Outputs:
- data/datasets/MASTER_DATASET_INDEX.json
- data/datasets/MASTER_DATASET_INDEX.md
- data/datasets/CANONICAL_SCHEMA_REVMAX.md
- data/datasets/DATASET_MAPPINGS.md
- data/datasets/domains/<domain>/DATASETS.md
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import gzip
from zipfile import ZipFile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DATASETS_ROOT = ROOT / "data" / "datasets"
PUBLIC_ROOT = ROOT / "data" / "public_datasets"


@dataclass
class DatasetMeta:
    name: str
    path: str
    domain: str
    source_type: str
    utility: str
    priority: str
    status: str
    demand_relevant: bool
    pricing_relevant: bool
    compset_relevant: bool
    reputation_relevant: bool
    events_relevant: bool
    forecasting_relevant: bool
    city: Optional[str] = None
    country: Optional[str] = None
    rows: Optional[int] = None
    columns: Optional[int] = None
    schema: Optional[List[str]] = None
    size_bytes: Optional[int] = None
    duplicate: bool = False
    duplicate_of: Optional[str] = None


def hbytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    for u in units:
        if v < 1024 or u == units[-1]:
            return f"{v:.2f} {u}" if u != "B" else f"{int(v)} {u}"
        v /= 1024
    return f"{n} B"


def read_csv_schema(path: Path, gz: bool = False) -> Tuple[Optional[int], Optional[int], List[str]]:
    opener = gzip.open if gz else open
    with opener(path, "rt", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r, [])
        rows = 0
        for _ in r:
            rows += 1
    return rows, len(header), header[:50]


def xlsx_first_sheet_header(path: Path) -> List[str]:
    ns = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    with ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        first_sheet = wb.find("a:sheets/a:sheet", ns)
        if first_sheet is None:
            return []
        rid = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            r.attrib.get("Id"): r.attrib.get("Target")
            for r in rels.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        }
        target = rel_map.get(rid, "")
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in ss.findall("a:si", ns):
                shared.append("".join(t.text or "" for t in si.findall(".//a:t", ns)))
        ws = ET.fromstring(z.read(target))
        row1 = ws.find('.//a:sheetData/a:row[@r="1"]', ns)
        out = []
        if row1 is None:
            return out
        for c in row1.findall("a:c", ns):
            t = c.attrib.get("t")
            v = c.find("a:v", ns)
            if v is None:
                out.append("")
            elif t == "s":
                idx = int(v.text)
                out.append(shared[idx] if idx < len(shared) else v.text or "")
            else:
                out.append(v.text or "")
        return out[:50]


def profile_file(path: Path) -> Tuple[Optional[int], Optional[int], List[str]]:
    low = path.name.lower()
    try:
        if low.endswith(".csv"):
            return read_csv_schema(path, gz=False)
        if low.endswith(".csv.gz"):
            return read_csv_schema(path, gz=True)
        if low.endswith(".xlsx"):
            header = xlsx_first_sheet_header(path)
            return None, len(header), header
        if low.endswith(".json"):
            obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(obj, dict):
                keys = list(obj.keys())[:50]
                return None, len(keys), keys
            return None, None, [type(obj).__name__]
    except Exception:
        return None, None, []
    return None, None, []


def all_data_files() -> List[Path]:
    files = []
    for base in [DATASETS_ROOT, PUBLIC_ROOT]:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".csv", ".gz", ".xlsx", ".json"}:
                if p.name.lower() in {"import_manifest.json", "import_summary.json"}:
                    continue
                files.append(p)
    return files


def infer_domain(path: Path) -> str:
    s = str(path).lower()
    if "airbnb" in s:
        return "airbnb"
    if "weekdays.csv" in s or "weekends.csv" in s:
        return "airbnb"
    if "expedia" in s or "travel.csv" in s:
        return "ota"
    if "airline" in s or "flight_" in s or "schedule data" in s:
        return "airline"
    if "review" in s and "hotel_booking" not in s:
        return "reviews"
    if "hotel_booking" in s or "reservations" in s or "hotel reservations" in s:
        return "hotel_core"
    return "other"


def infer_tags(path: Path) -> Dict[str, bool]:
    s = str(path).lower()
    city_week = "weekdays.csv" in s or "weekends.csv" in s
    return {
        "demand_relevant": any(k in s for k in ["booking", "reservation", "lead_time", "hotel_bookings", "travel"]),
        "pricing_relevant": city_week or any(k in s for k in ["price", "adr", "rate", "revenue", "realsum", "airbnb"]),
        "compset_relevant": city_week or any(k in s for k in ["airbnb", "expedia", "travel", "inside_airbnb", "hotels_netherlands"]),
        "reputation_relevant": "review" in s or "tripadvisor" in s,
        "events_relevant": "gdelt" in s or "event" in s,
        "forecasting_relevant": city_week or any(k in s for k in ["prediction", "revenue", "booking", "calendar", "travel"]),
    }


def infer_priority(path: Path) -> str:
    s = str(path).lower()
    if "inside_airbnb_official" in s or "travel.csv" in s:
        return "essential"
    if "weekdays.csv" in s or "weekends.csv" in s:
        return "high-value"
    if "hotel_booking" in s or "expedia" in s or "airbnb_data.csv" in s:
        return "high-value"
    if "review" in s or "revenue" in s or "schedule data" in s:
        return "useful"
    if "eurostat" in s or "gdelt" in s:
        return "secondary"
    return "useful"


def infer_utility(path: Path, domain: str) -> str:
    if domain == "airbnb":
        return "Compset proxy and pricing/listings pressure by city and date."
    if domain == "ota":
        return "OTA behavior, conversion context, and demand proxy signals."
    if domain == "airline":
        return "Forecasting workflow practice and temporal revenue/booking modeling."
    if domain == "reviews":
        return "Reputation/sentiment extraction for confidence and guardrails."
    if domain == "hotel_core":
        return "Core booking demand and reservation behavior signals."
    return "Auxiliary context dataset."


def infer_source_type(path: Path) -> str:
    s = str(path).lower()
    if "public_datasets" in s and "kaggle" in s:
        return "kaggle"
    if "public_datasets/inside_airbnb" in s:
        return "inside_airbnb"
    if "zenodo" in s:
        return "zenodo"
    if "eurostat" in s:
        return "eurostat_api"
    if "gdelt" in s:
        return "gdelt"
    if "desktop_ingest" in s:
        return "desktop_import"
    return "local_archive"


def infer_city_country(path: Path) -> Tuple[Optional[str], Optional[str]]:
    s = str(path).lower()
    city_map = {
        "berlin": ("Berlin", "Germany"),
        "barcelona": ("Barcelona", "Spain"),
        "madrid": ("Madrid", "Spain"),
        "lisbon": ("Lisbon", "Portugal"),
        "prague": ("Prague", "Czech Republic"),
        "london": ("London", "United Kingdom"),
        "paris": ("Paris", "France"),
        "rome": ("Rome", "Italy"),
        "vienna": ("Vienna", "Austria"),
        "amsterdam": ("Amsterdam", "Netherlands"),
        "athens": ("Athens", "Greece"),
        "budapest": ("Budapest", "Hungary"),
    }
    for k, v in city_map.items():
        if k in s:
            return v
    return None, None


def canonical_schema_md() -> str:
    fields = [
        "source_dataset",
        "source_type",
        "domain",
        "city",
        "country",
        "neighbourhood",
        "date",
        "price",
        "currency",
        "rating",
        "review_score",
        "room_type",
        "property_type",
        "availability",
        "demand_proxy",
        "lead_time",
        "booking_channel",
        "latitude",
        "longitude",
    ]
    lines = [
        "# RevMax Canonical Dataset Schema",
        "",
        "This canonical schema is the target contract for normalized feature views across all dataset domains.",
        "",
        "| field | description |",
        "|---|---|",
    ]
    desc = {
        "source_dataset": "Original dataset id or filename.",
        "source_type": "Kaggle / Inside Airbnb / Zenodo / API / local import.",
        "domain": "hotel_core / airbnb / ota / airline / reviews / other.",
        "city": "City identifier when available.",
        "country": "Country identifier when available.",
        "neighbourhood": "Neighborhood/zone label when available.",
        "date": "Observation date (booking/search/review/calendar).",
        "price": "Comparable price/rate measure.",
        "currency": "Currency code or symbol source.",
        "rating": "Rating value (property/experience).",
        "review_score": "Review-specific score when separate from rating.",
        "room_type": "Room/accommodation class.",
        "property_type": "Property category (hotel/apartment/etc).",
        "availability": "Availability indicator/count/proxy.",
        "demand_proxy": "Demand-related proxy metric.",
        "lead_time": "Days between booking and stay when available.",
        "booking_channel": "OTA/channel/distribution source.",
        "latitude": "Geo latitude.",
        "longitude": "Geo longitude.",
    }
    for f in fields:
        lines.append(f"| `{f}` | {desc[f]} |")
    return "\n".join(lines) + "\n"


def build() -> None:
    files = all_data_files()
    metas: List[DatasetMeta] = []

    # duplicate detection by name+size first
    seen: Dict[Tuple[str, int], str] = {}
    for p in sorted(files):
        rel = str(p.relative_to(ROOT))
        size = p.stat().st_size
        key = (p.name, size)
        dup = key in seen
        dup_of = seen.get(key)
        if not dup:
            seen[key] = rel

        rows, cols, schema = profile_file(p)
        domain = infer_domain(p)
        tags = infer_tags(p)
        city, country = infer_city_country(p)
        meta = DatasetMeta(
            name=p.name,
            path=rel,
            domain=domain,
            source_type=infer_source_type(p),
            utility=infer_utility(p, domain),
            priority=infer_priority(p),
            status="ready" if p.exists() else "missing",
            demand_relevant=tags["demand_relevant"],
            pricing_relevant=tags["pricing_relevant"],
            compset_relevant=tags["compset_relevant"],
            reputation_relevant=tags["reputation_relevant"],
            events_relevant=tags["events_relevant"],
            forecasting_relevant=tags["forecasting_relevant"],
            city=city,
            country=country,
            rows=rows,
            columns=cols,
            schema=schema,
            size_bytes=size,
            duplicate=dup,
            duplicate_of=dup_of,
        )
        metas.append(meta)

    # json output
    payload = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "total_datasets": len(metas),
        "domains": sorted({m.domain for m in metas}),
        "datasets": [m.__dict__ for m in metas],
    }
    (DATASETS_ROOT / "MASTER_DATASET_INDEX.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # markdown output
    md = [
        "# RevMax Master Dataset Index",
        "",
        f"_Generated at {payload['generated_at']}_",
        "",
        "| dataset | domain | source_type | size | rows | cols | priority | status | duplicate | relevance | path |",
        "|---|---|---|---:|---:|---:|---|---|---|---|---|",
    ]
    for m in metas:
        rel = ",".join(
            [
                "D" if m.demand_relevant else "-",
                "P" if m.pricing_relevant else "-",
                "C" if m.compset_relevant else "-",
                "R" if m.reputation_relevant else "-",
                "E" if m.events_relevant else "-",
                "F" if m.forecasting_relevant else "-",
            ]
        )
        md.append(
            f"| `{m.name}` | `{m.domain}` | `{m.source_type}` | {hbytes(m.size_bytes or 0)} | {m.rows if m.rows is not None else '-'} | {m.columns if m.columns is not None else '-'} | `{m.priority}` | `{m.status}` | `{m.duplicate}` | `{rel}` | `{m.path}` |"
        )
    (DATASETS_ROOT / "MASTER_DATASET_INDEX.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # canonical schema doc
    (DATASETS_ROOT / "CANONICAL_SCHEMA_REVMAX.md").write_text(canonical_schema_md(), encoding="utf-8")

    # mapping doc (important datasets only)
    mappings = [
        (
            "inside_airbnb_official/*/listings.csv.gz",
            "airbnb",
            [
                "id -> source_dataset_record_id",
                "last_scraped -> date",
                "neighbourhood_cleansed -> neighbourhood",
                "latitude/longitude -> latitude/longitude",
                "property_type -> property_type",
                "room_type -> room_type",
                "price -> price",
                "review_scores_rating -> review_score",
            ],
            ["currency often implicit", "booking_channel missing", "lead_time missing"],
        ),
        (
            "inside_airbnb_official/*/calendar.csv.gz",
            "airbnb",
            [
                "date -> date",
                "price -> price",
                "available -> availability",
                "listing_id -> source_dataset",
            ],
            ["city from folder", "country from folder", "channel missing"],
        ),
        (
            "desktop_ingest_2026_03_20/travel.csv",
            "ota",
            [
                "date_time -> date",
                "price_usd -> price",
                "srch_destination_id -> neighbourhood/market proxy",
                "orig_destination_distance -> demand/compset context proxy",
                "is_mobile -> booking_channel context",
            ],
            ["currency for all rows may vary", "review fields sparse"],
        ),
        (
            "kaggle_vijeetnigam26_expedia_hotel/train.csv",
            "ota",
            [
                "date_time -> date",
                "site_name/posa_continent -> booking_channel/source geo",
                "orig_destination_distance -> demand/compset proxy",
                "price_usd -> price",
                "srch_booking_window -> lead_time",
            ],
            ["no direct neighbourhood", "no direct review text"],
        ),
        (
            "public_datasets/hotel_booking_demand/hotel_bookings.csv",
            "hotel_core",
            [
                "arrival_date_* -> date",
                "adr -> price",
                "lead_time -> lead_time",
                "distribution_channel -> booking_channel",
                "market_segment -> demand_proxy segment",
            ],
            ["no lat/long", "no explicit compset"],
        ),
        (
            "public_datasets/hotel_reviews_europe_515k/Hotel_Reviews.csv",
            "reviews",
            [
                "Review_Date -> date",
                "Average_Score -> rating",
                "Reviewer_Score -> review_score",
                "lat/lng -> latitude/longitude",
                "Hotel_Address -> neighbourhood/city parsing candidate",
            ],
            ["price missing", "booking_channel missing"],
        ),
        (
            "desktop_ingest_2026_03_20/Airbnb_Data.csv",
            "airbnb",
            [
                "log_price -> price (exp transform needed)",
                "city -> city",
                "property_type -> property_type",
                "room_type -> room_type",
                "review_scores_rating -> review_score",
                "latitude/longitude -> latitude/longitude",
            ],
            ["currency implicit", "availability not explicit"],
        ),
    ]
    map_md = [
        "# RevMax Dataset-to-Canonical Mapping",
        "",
        "This document maps key datasets to the RevMax canonical schema and highlights gaps.",
    ]
    for ds, dom, cols, gaps in mappings:
        map_md += [
            "",
            f"## `{ds}`",
            f"- domain: `{dom}`",
            "- mapping:",
        ]
        for c in cols:
            map_md.append(f"  - {c}")
        map_md.append("- gaps / not-applicable:")
        for g in gaps:
            map_md.append(f"  - {g}")
    (DATASETS_ROOT / "DATASET_MAPPINGS.md").write_text("\n".join(map_md) + "\n", encoding="utf-8")

    pipeline_md = [
        "# RevMax Pipeline Feed Map",
        "",
        "| pipeline | primary datasets | notes |",
        "|---|---|---|",
        "| demand pipeline | `hotel_bookings.csv`, `Hotel Reservations.csv`, `travel.csv`, `12month_flight_booking.csv` | Lead-time, booking intensity, channel/context demand proxies. |",
        "| reputation pipeline | `Hotel_Reviews.csv`, `tripadvisor_hotel_reviews.csv`, `booking_hotel.csv`, `tripadvisor_room.csv` | Sentiment/review-score features and confidence guardrails. |",
        "| compset/proxy pipeline | `inside_airbnb_official/*`, `Airbnb_Data.csv`, `Airbnb_Open_Data.csv`, `travel.csv`, `expedia train/test` | Competitive price/availability proxy in city/time windows. |",
        "| pricing context | `inside_airbnb_official/calendar.csv.gz`, `hotel_bookings*.csv`, `hotels_netherlands`, `hotel_rates_reviews_amenities` | Relative price posture and local market pressure. |",
        "| dojo case generation | `travel.csv`, `inside_airbnb_official/*`, `hotel_bookings.csv`, `Hotel_Reviews.csv`, airline prediction sets | Build realistic multi-signal scenarios for deterministic engine validation. |",
    ]
    (DATASETS_ROOT / "PIPELINE_FEED_MAP.md").write_text("\n".join(pipeline_md) + "\n", encoding="utf-8")

    # domain folders with dataset views
    domains = ["hotel_core", "airbnb", "ota", "airline", "reviews", "other"]
    for d in domains:
        dd = DATASETS_ROOT / "domains" / d
        dd.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Domain: {d}",
            "",
            "| dataset | size | rows | cols | priority | path |",
            "|---|---:|---:|---:|---|---|",
        ]
        for m in metas:
            if m.domain != d:
                continue
            lines.append(
                f"| `{m.name}` | {hbytes(m.size_bytes or 0)} | {m.rows if m.rows is not None else '-'} | {m.columns if m.columns is not None else '-'} | `{m.priority}` | `{m.path}` |"
            )
        (dd / "DATASETS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()

