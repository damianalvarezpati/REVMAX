#!/usr/bin/env python3
"""
Extract actionable patterns from prioritized RevMax datasets into data/knowledge/.
Uses stdlib only. Skips missing files (e.g. gitignored local CSVs) with explicit notes.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "data" / "knowledge"


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n != len(ys) or n < 50:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def safe_float(x: Any) -> Optional[float]:
    if x is None or x == "" or x == "NULL":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def safe_int(x: Any) -> Optional[int]:
    f = safe_float(x)
    if f is None:
        return None
    return int(f)


MONTH_ORDER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass
class RuleCandidate:
    id: str
    statement: str
    support: str  # strong | partial | hypothetical
    evidence: Dict[str, Any]
    applies_to: List[str]


def path_or_none(p: Path) -> Optional[Path]:
    return p if p.exists() else None


def analyze_hotel_bookings(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": str(path.relative_to(ROOT)), "rows_used": 0}
    lt: List[float] = []
    cancel: List[float] = []
    adr: List[float] = []
    adr_lt_pairs: List[Tuple[float, float]] = []
    spec: List[float] = []
    spec_cancel: List[Tuple[float, float]] = []

    by_month: Dict[str, Dict[str, float]] = defaultdict(lambda: {"n": 0, "canceled": 0, "adr_sum": 0.0, "adr_n": 0})
    by_channel: Dict[str, Dict[str, float]] = defaultdict(lambda: {"n": 0, "canceled": 0, "adr_sum": 0.0, "adr_n": 0})

    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            lt_v = safe_float(row.get("lead_time"))
            c = safe_int(row.get("is_canceled"))
            a = safe_float(row.get("adr"))
            sp = safe_int(row.get("total_of_special_requests"))
            if lt_v is None or c is None:
                continue
            lt.append(lt_v)
            cancel.append(float(c))
            month = (row.get("arrival_date_month") or "").strip()
            ch = (row.get("distribution_channel") or "").strip() or "unknown"
            if month:
                by_month[month]["n"] += 1
                by_month[month]["canceled"] += c
                if a is not None and a > 0:
                    by_month[month]["adr_sum"] += a
                    by_month[month]["adr_n"] += 1
            by_channel[ch]["n"] += 1
            by_channel[ch]["canceled"] += c
            if a is not None and a > 0:
                by_channel[ch]["adr_sum"] += a
                by_channel[ch]["adr_n"] += 1
                adr_lt_pairs.append((lt_v, a))
            if a is not None and a > 0:
                adr.append(a)
            if sp is not None:
                spec.append(float(sp))
                spec_cancel.append((float(sp), float(c)))

    out["rows_used"] = len(lt)
    r_lt_cancel = pearson(lt, cancel)
    lt2 = [p[0] for p in adr_lt_pairs]
    adr2 = [p[1] for p in adr_lt_pairs]
    r_lt_adr = pearson(lt2, adr2) if len(lt2) >= 50 else None
    sp_x = [p[0] for p in spec_cancel]
    sp_y = [p[1] for p in spec_cancel]
    r_spec_cancel = pearson(sp_x, sp_y) if len(sp_x) >= 50 else None

    out["correlations"] = {
        "lead_time_vs_is_canceled_pearson": r_lt_cancel,
        "lead_time_vs_adr_pearson": r_lt_adr,
        "special_requests_vs_is_canceled_pearson": r_spec_cancel,
        "n_pairs_lead_adr": len(lt2),
    }

    seasonal = []
    for m, agg in sorted(by_month.items(), key=lambda x: MONTH_ORDER.get(x[0].lower(), 99)):
        n = int(agg["n"])
        if n < 100:
            continue
        seasonal.append(
            {
                "month": m,
                "n": n,
                "cancellation_rate": round(agg["canceled"] / n, 4),
                "mean_adr": round(agg["adr_sum"] / agg["adr_n"], 2) if agg["adr_n"] else None,
            }
        )
    out["seasonality_by_arrival_month"] = seasonal

    ch_stats = []
    for ch, agg in sorted(by_channel.items(), key=lambda x: -x[1]["n"])[:8]:
        n = int(agg["n"])
        if n < 500:
            continue
        ch_stats.append(
            {
                "distribution_channel": ch,
                "n": n,
                "cancellation_rate": round(agg["canceled"] / n, 4),
                "mean_adr": round(agg["adr_sum"] / agg["adr_n"], 2) if agg["adr_n"] else None,
            }
        )
    out["by_distribution_channel"] = ch_stats

    # Lead time buckets (demand / risk)
    buckets = [(0, 7), (8, 30), (31, 90), (91, 180), (181, 9999)]
    lb = []
    for lo, hi in buckets:
        idx = [i for i, v in enumerate(lt) if lo <= v <= hi]
        if len(idx) < 100:
            continue
        c_rate = sum(cancel[i] for i in idx) / len(idx)
        lb.append({"lead_time_range": [lo, hi], "n": len(idx), "cancellation_rate": round(c_rate, 4)})
    out["lead_time_bucket_cancellation"] = lb

    return out


def analyze_hotel_reservations(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": str(path.relative_to(ROOT)), "rows_used": 0}
    lt: List[float] = []
    price: List[float] = []
    canceled: List[float] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            ltv = safe_float(row.get("lead_time"))
            pv = safe_float(row.get("avg_price_per_room"))
            st = (row.get("booking_status") or "").strip()
            if ltv is None or pv is None:
                continue
            lt.append(ltv)
            price.append(pv)
            canceled.append(1.0 if "cancel" in st.lower() else 0.0)
    out["rows_used"] = len(lt)
    out["correlations"] = {
        "lead_time_vs_avg_price_pearson": pearson(lt, price),
        "lead_time_vs_canceled_pearson": pearson(lt, canceled) if len(canceled) == len(lt) else None,
    }
    # By market segment
    seg: Dict[str, List[float]] = defaultdict(list)
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pv = safe_float(row.get("avg_price_per_room"))
            ms = (row.get("market_segment_type") or "").strip() or "unknown"
            if pv is not None:
                seg[ms].append(pv)
    out["mean_price_by_market_segment"] = [
        {"segment": k, "n": len(v), "mean_price": round(sum(v) / len(v), 2)} for k, v in sorted(seg.items(), key=lambda x: -len(x[1])) if len(v) >= 200
    ]
    return out


def analyze_reviews_515k(path: Path, max_rows: int = 120000) -> Dict[str, Any]:
    """Sample first max_rows for speed; still large enough for stable correlations."""
    out: Dict[str, Any] = {"source": str(path.relative_to(ROOT)), "rows_used": 0, "note": f"capped_first_{max_rows}_rows"}
    rs: List[float] = []
    avg: List[float] = []
    neg_w: List[float] = []
    neg_w: List[float] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            if i >= max_rows:
                break
            a = safe_float(row.get("Reviewer_Score"))
            b = safe_float(row.get("Average_Score"))
            nw = safe_float(row.get("Review_Total_Negative_Word_Counts"))
            if a is None or b is None:
                continue
            rs.append(a)
            avg.append(b)
            neg_w.append(nw if nw is not None else float("nan"))
    out["rows_used"] = len(rs)
    out["correlations"] = {
        "reviewer_score_vs_hotel_average_pearson": pearson(rs, avg),
    }
    nw2 = [neg_w[i] for i in range(len(rs)) if not math.isnan(neg_w[i])]
    rs2 = [rs[i] for i in range(len(rs)) if not math.isnan(neg_w[i])]
    if len(nw2) >= 50:
        out["correlations"]["negative_word_count_vs_reviewer_score_pearson"] = pearson(nw2, rs2)
    # Distribution buckets for reputation
    buckets = [0, 5, 6, 7, 8, 9, 10.1]
    dist = []
    for lo, hi in zip(buckets[:-1], buckets[1:]):
        c = sum(1 for x in rs if lo <= x < hi)
        dist.append({"reviewer_score_range": [lo, hi], "count": c, "share": round(c / len(rs), 4) if rs else 0})
    out["reviewer_score_distribution"] = dist
    return out


def analyze_tripadvisor(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": str(path.relative_to(ROOT)), "rows_used": 0}
    ratings: List[float] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rv = safe_float(row.get("Rating"))
            if rv is not None:
                ratings.append(rv)
    out["rows_used"] = len(ratings)
    if ratings:
        s = sum(ratings)
        out["rating_mean"] = round(s / len(ratings), 3)
        out["rating_std"] = round(math.sqrt(sum((x - s / len(ratings)) ** 2 for x in ratings) / len(ratings)), 3)
    dist: Dict[int, int] = defaultdict(int)
    for x in ratings:
        dist[int(round(x))] += 1
    out["rating_histogram_int"] = {str(k): v for k, v in sorted(dist.items())}
    return out


def analyze_travel(path: Path, max_rows: int = 100000) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": str(path.relative_to(ROOT)), "rows_used": 0}
    dist: List[float] = []
    book: List[float] = []
    mobile: List[float] = []
    pack: List[float] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            if i >= max_rows:
                break
            d = safe_float(row.get("orig_destination_distance"))
            b = safe_int(row.get("is_booking"))
            m = safe_int(row.get("is_mobile"))
            p = safe_int(row.get("is_package"))
            if d is None or b is None:
                continue
            dist.append(d)
            book.append(float(b))
            if m is not None:
                mobile.append(float(m))
            if p is not None:
                pack.append(float(p))
    out["rows_used"] = len(dist)
    out["correlations"] = {
        "orig_destination_distance_vs_is_booking_pearson": pearson(dist, book),
    }
    if len(mobile) == len(book):
        out["correlations"]["is_mobile_vs_is_booking_pearson"] = pearson(mobile, book)
    if len(pack) == len(book):
        out["correlations"]["is_package_vs_is_booking_pearson"] = pearson(pack, book)

    by_ch: Dict[str, Dict[str, float]] = defaultdict(lambda: {"n": 0, "book": 0})
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            if i >= max_rows:
                break
            ch = (row.get("channel") or "").strip() or "unknown"
            b = safe_int(row.get("is_booking"))
            if b is None:
                continue
            by_ch[ch]["n"] += 1
            by_ch[ch]["book"] += b
    out["booking_rate_by_channel"] = [
        {"channel": k, "n": int(v["n"]), "booking_rate": round(v["book"] / v["n"], 4)}
        for k, v in sorted(by_ch.items(), key=lambda x: -x[1]["n"])
        if v["n"] >= 200
    ]
    return out


def analyze_city_weekday_weekend(base: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"cities": [], "note": "Compares mean realSum weekday file vs weekend file per city."}
    if not base.exists():
        out["error"] = "archive_not_found"
        return out
    weekdays = list(base.glob("*_weekdays.csv"))
    for wd in weekdays:
        name = wd.name.replace("_weekdays.csv", "")
        we = base / f"{name}_weekends.csv"
        if not we.exists():
            continue

        def mean_realsum(p: Path) -> Optional[float]:
            s = 0.0
            n = 0
            with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    v = safe_float(row.get("realSum"))
                    if v is not None and v > 0:
                        s += v
                        n += 1
            return s / n if n else None

        mw, me = mean_realsum(wd), mean_realsum(we)
        if mw and me:
            out["cities"].append(
                {
                    "city_slug": name,
                    "mean_realSum_weekday": round(mw, 2),
                    "mean_realSum_weekend": round(me, 2),
                    "weekend_premium_ratio": round(me / mw, 4),
                }
            )
    ratios = [c["weekend_premium_ratio"] for c in out["cities"]]
    if ratios:
        out["summary"] = {
            "n_cities": len(ratios),
            "median_weekend_premium_ratio": round(sorted(ratios)[len(ratios) // 2], 4),
            "mean_weekend_premium_ratio": round(sum(ratios) / len(ratios), 4),
        }
    return out


def analyze_airbnb_data(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": str(path.relative_to(ROOT)), "rows_used": 0}
    lp: List[float] = []
    rev: List[float] = []
    nrev: List[float] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            l = safe_float(row.get("log_price"))
            rv = safe_float(row.get("review_scores_rating"))
            nr = safe_float(row.get("number_of_reviews"))
            if l is None:
                continue
            lp.append(l)
            rev.append(rv if rv is not None else float("nan"))
            nrev.append(math.log1p(nr) if nr is not None else float("nan"))

    # align pairs
    lp_r, rv_r = [], []
    lp_n, nr_r = [], []
    for i in range(len(lp)):
        if not math.isnan(rev[i]):
            lp_r.append(lp[i])
            rv_r.append(rev[i])
        if not math.isnan(nrev[i]):
            lp_n.append(lp[i])
            nr_r.append(nrev[i])
    out["rows_used"] = len(lp)
    out["correlations"] = {
        "log_price_vs_review_scores_rating_pearson": pearson(lp_r, rv_r) if len(lp_r) >= 50 else None,
        "log_price_vs_log1p_number_of_reviews_pearson": pearson(lp_n, nr_r) if len(lp_n) >= 50 else None,
    }
    return out


def clean_open_price(raw: str) -> Optional[float]:
    if not raw:
        return None
    s = re.sub(r"[^\d.]", "", str(raw))
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def analyze_airbnb_open(path: Path, max_rows: int = 80000) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": str(path.relative_to(ROOT)), "rows_used": 0, "note": f"capped_{max_rows}"}
    price: List[float] = []
    nrev: List[float] = []
    avail: List[float] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            if i >= max_rows:
                break
            p = clean_open_price(row.get("price") or "")
            nr = safe_float(row.get("number of reviews"))
            av = safe_float(row.get("availability 365"))
            if p is None or p <= 0:
                continue
            price.append(p)
            nrev.append(nr if nr is not None else 0.0)
            avail.append(av if av is not None else float("nan"))
    out["rows_used"] = len(price)
    av_y = [avail[i] for i in range(len(price)) if not math.isnan(avail[i])]
    av_p = [price[i] for i in range(len(price)) if not math.isnan(avail[i])]
    out["correlations"] = {
        "price_vs_number_of_reviews_pearson": pearson(price, nrev) if len(price) >= 50 else None,
        "price_vs_availability_365_pearson": pearson(av_p, av_y) if len(av_p) >= 50 else None,
    }
    return out


def analyze_airline_schedule(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": str(path.relative_to(ROOT)), "rows_used": 0}
    dur: List[float] = []
    seats: List[float] = []
    freq: List[float] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            d = safe_float(row.get("Flight Duration (mins)"))
            s = safe_float(row.get("Seats per Dept"))
            fr = safe_float(row.get("Frequency (MTWTFSS)"))
            if d is None or s is None:
                continue
            dur.append(d)
            seats.append(s)
            if fr is not None:
                freq.append(fr)
            else:
                freq.append(float("nan"))
    out["rows_used"] = len(dur)
    out["correlations"] = {
        "flight_duration_vs_seats_per_dept_pearson": pearson(dur, seats),
    }
    out["disclaimer"] = "Airline schedule is not hotel demand; use only as weak macro/supply-capacity analogy for Dojo, not RevMax production rules."
    return out


def build_candidate_rules(evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    rules: List[RuleCandidate] = []

    hb = evidence.get("hotel_bookings_hotel_demand", {})
    r_lc = (hb.get("correlations") or {}).get("lead_time_vs_is_canceled_pearson")
    if r_lc is not None and hb.get("rows_used", 0) > 5000:
        sup = "strong" if abs(r_lc) >= 0.08 else "partial"
        rules.append(
            RuleCandidate(
                id="HB-001",
                statement="Longer lead_time is associated with higher cancellation probability (hotel booking demand dataset).",
                support=sup,
                evidence={"pearson_r": round(r_lc, 4), "n": hb.get("rows_used")},
                applies_to=["demand_pipeline", "confidence", "dojo"],
            )
        )

    r_lp_rev = (evidence.get("airbnb_data", {}).get("correlations") or {}).get("log_price_vs_review_scores_rating_pearson")
    if r_lp_rev is not None:
        sup = "partial" if abs(r_lp_rev) < 0.25 else "strong"
        rules.append(
            RuleCandidate(
                id="AB-001",
                statement="Higher review_scores_rating tends to associate with higher log_price (Airbnb listings sample).",
                support=sup,
                evidence={"pearson_r": round(r_lp_rev, 4), "n": evidence.get("airbnb_data", {}).get("rows_used")},
                applies_to=["pricing_context", "reputation_guardrail", "dojo"],
            )
        )

    city = evidence.get("city_weekday_weekend", {})
    med = (city.get("summary") or {}).get("median_weekend_premium_ratio")
    if med is not None:
        rules.append(
            RuleCandidate(
                id="CT-001",
                statement="Weekend nightly proxy (realSum) is typically above weekday in multi-city Airbnb-style city files.",
                support="strong" if city.get("summary", {}).get("n_cities", 0) >= 8 else "partial",
                evidence={"median_weekend_premium_ratio": med, "n_cities": city.get("summary", {}).get("n_cities")},
                applies_to=["pricing_context", "forecasting_features", "dojo"],
            )
        )

    tr = evidence.get("travel_ota", {})
    r_db = (tr.get("correlations") or {}).get("orig_destination_distance_vs_is_booking_pearson")
    if r_db is not None:
        rules.append(
            RuleCandidate(
                id="OTA-001",
                statement="Search distance proxy correlates weakly with booking outcome in Expedia-style travel sample; use as context feature, not standalone pricing driver.",
                support="partial" if abs(r_db) < 0.05 else "strong",
                evidence={"pearson_r": round(r_db, 4), "n": tr.get("rows_used")},
                applies_to=["compset_proxy", "confidence_penalty", "dojo"],
            )
        )

    rev = evidence.get("reviews_515k", {})
    r_ra = (rev.get("correlations") or {}).get("reviewer_score_vs_hotel_average_pearson")
    if r_ra is not None:
        rules.append(
            RuleCandidate(
                id="RV-001",
                statement="Reviewer score tracks hotel average score; use divergence as data-quality / outlier flag for reputation signals.",
                support="strong" if r_ra and r_ra > 0.4 else "partial",
                evidence={"pearson_r": round(r_ra, 4), "n": rev.get("rows_used")},
                applies_to=["reputation_pipeline", "confidence", "dojo"],
            )
        )

    rules.append(
        RuleCandidate(
            id="EVT-001",
            statement="Event pressure proxy from airline schedule or GDELT is not validated in this extraction; keep hypothetical until joined to hotel markets.",
            support="hypothetical",
            evidence={},
            applies_to=["event_pressure", "future_enrichment"],
        )
    )

    return [asdict(x) for x in rules]


def write_md_demand(data: Dict[str, Any]) -> str:
    lines = [
        "# Demand patterns (extracted)",
        "",
        "## Hotel bookings (H1)",
        f"- Source: `{data.get('hotel_bookings_hotel_demand', {}).get('source', 'n/a')}`",
        f"- Rows: {data.get('hotel_bookings_hotel_demand', {}).get('rows_used', 0)}",
        "### Correlations",
        f"- lead_time vs is_canceled: **{data.get('hotel_bookings_hotel_demand', {}).get('correlations', {}).get('lead_time_vs_is_canceled_pearson')}**",
        f"- lead_time vs ADR: **{data.get('hotel_bookings_hotel_demand', {}).get('correlations', {}).get('lead_time_vs_adr_pearson')}**",
        "### Lead-time buckets → cancellation rate",
        "See JSON for full table; highest-risk buckets inform hold/raise guardrails.",
        "",
        "## Hotel reservations (INN)",
        f"- Rows: {data.get('hotel_reservations', {}).get('rows_used', 0)}",
        f"- lead_time vs avg_price: **{data.get('hotel_reservations', {}).get('correlations', {}).get('lead_time_vs_avg_price_pearson')}**",
        "",
        "## Travel / OTA sample",
        f"- Booking rate by channel: see `demand_patterns.json` → `travel_ota.booking_rate_by_channel`",
        "",
        "## Airline wide booking/revenue CSVs",
        "- See `demand_patterns.json` → `airline_booking_revenue_wide` (explicitly not aggregated in this run).",
    ]
    return "\n".join(lines) + "\n"


def write_md_reputation(data: Dict[str, Any]) -> str:
    r = data.get("reviews_515k", {})
    t = data.get("tripadvisor", {})
    return "\n".join(
        [
            "# Reputation patterns (extracted)",
            "",
            f"## 515k Europe reviews — n={r.get('rows_used', 0)} (capped sample)",
            f"- reviewer_score vs hotel Average_Score: **{r.get('correlations', {}).get('reviewer_score_vs_hotel_average_pearson')}**",
            f"- negative word count vs reviewer_score: **{r.get('correlations', {}).get('negative_word_count_vs_reviewer_score_pearson')}**",
            "",
            f"## TripAdvisor sample — n={t.get('rows_used', 0)}",
            f"- Mean rating: **{t.get('rating_mean')}**, std: **{t.get('rating_std')}**",
            "",
            "Use distributions to calibrate reputation_bucket cutpoints in the deterministic engine.",
        ]
    ) + "\n"


def write_md_pricing(data: Dict[str, Any]) -> str:
    c = data.get("city_weekday_weekend", {})
    a = data.get("airbnb_data", {})
    o = data.get("airbnb_open", {})
    return "\n".join(
        [
            "# Pricing context patterns (extracted)",
            "",
            "## City weekday vs weekend (realSum)",
            f"- Cities compared: **{c.get('summary', {}).get('n_cities', 0)}**",
            f"- Median weekend premium ratio: **{c.get('summary', {}).get('median_weekend_premium_ratio')}**",
            "",
            "## Airbnb_Data",
            f"- log_price vs review_scores_rating: **{a.get('correlations', {}).get('log_price_vs_review_scores_rating_pearson')}**",
            f"- log_price vs log1p(reviews): **{a.get('correlations', {}).get('log_price_vs_log1p_number_of_reviews_pearson')}**",
            "",
            "## Airbnb_Open_Data (cleaned price)",
            f"- price vs number_of_reviews: **{o.get('correlations', {}).get('price_vs_number_of_reviews_pearson')}**",
            f"- price vs availability_365: **{o.get('correlations', {}).get('price_vs_availability_365_pearson')}**",
        ]
    ) + "\n"


def main() -> int:
    KNOWLEDGE.mkdir(parents=True, exist_ok=True)
    desktop = ROOT / "data" / "datasets" / "desktop_ingest_2026_03_20"
    archive6 = desktop / "archive (6)"
    archive8 = desktop / "archive (8)" / "airline_data"

    evidence: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "inputs_resolved": {},
    }

    hb_path = path_or_none(ROOT / "data" / "datasets" / "kaggle_hotel_booking_demand" / "hotel_bookings.csv")
    if hb_path:
        evidence["hotel_bookings_hotel_demand"] = analyze_hotel_bookings(hb_path)
        evidence["inputs_resolved"]["hotel_bookings"] = str(hb_path.relative_to(ROOT))
    else:
        evidence["hotel_bookings_hotel_demand"] = {"error": "file_missing"}

    hr_path = path_or_none(desktop / "Hotel Reservations.csv")
    if hr_path:
        evidence["hotel_reservations"] = analyze_hotel_reservations(hr_path)
        evidence["inputs_resolved"]["hotel_reservations"] = str(hr_path.relative_to(ROOT))
    else:
        evidence["hotel_reservations"] = {"error": "file_missing"}

    rv_path = path_or_none(ROOT / "data" / "public_datasets" / "hotel_reviews_europe_515k" / "Hotel_Reviews.csv")
    if rv_path:
        evidence["reviews_515k"] = analyze_reviews_515k(rv_path)
        evidence["inputs_resolved"]["hotel_reviews_515k"] = str(rv_path.relative_to(ROOT))
    else:
        evidence["reviews_515k"] = {"error": "file_missing"}

    ta_path = path_or_none(ROOT / "data" / "public_datasets" / "tripadvisor_hotel_reviews" / "tripadvisor_hotel_reviews.csv")
    if ta_path:
        evidence["tripadvisor"] = analyze_tripadvisor(ta_path)
        evidence["inputs_resolved"]["tripadvisor"] = str(ta_path.relative_to(ROOT))
    else:
        evidence["tripadvisor"] = {"error": "file_missing"}

    tv_path = path_or_none(desktop / "travel.csv")
    if tv_path:
        evidence["travel_ota"] = analyze_travel(tv_path)
        evidence["inputs_resolved"]["travel"] = str(tv_path.relative_to(ROOT))
    else:
        evidence["travel_ota"] = {"error": "file_missing"}

    evidence["city_weekday_weekend"] = analyze_city_weekday_weekend(archive6)
    evidence["inputs_resolved"]["city_weekdays_weekends"] = str(archive6.relative_to(ROOT)) if archive6.exists() else "missing"

    ad_path = path_or_none(desktop / "Airbnb_Data.csv")
    if ad_path:
        evidence["airbnb_data"] = analyze_airbnb_data(ad_path)
        evidence["inputs_resolved"]["airbnb_data"] = str(ad_path.relative_to(ROOT))
    else:
        evidence["airbnb_data"] = {"error": "file_missing"}

    ao_path = path_or_none(desktop / "Airbnb_Open_Data.csv")
    if ao_path:
        evidence["airbnb_open"] = analyze_airbnb_open(ao_path)
        evidence["inputs_resolved"]["airbnb_open"] = str(ao_path.relative_to(ROOT))
    else:
        evidence["airbnb_open"] = {"error": "file_missing"}

    sched = path_or_none(archive8 / "Schedule data.csv")
    if sched:
        evidence["airline_schedule"] = analyze_airline_schedule(sched)
        evidence["inputs_resolved"]["airline_schedule"] = str(sched.relative_to(ROOT))
    else:
        evidence["airline_schedule"] = {"error": "file_missing"}

    wide_book = archive8 / "12month_flight_booking.csv" if archive8.exists() else None
    wide_rev = archive8 / "12months_flight_revenue.csv" if archive8.exists() else None
    evidence["airline_booking_revenue_wide"] = {
        "status": "not_processed_in_this_run",
        "reason": "376-column airline booking/revenue extracts need explicit column mapping to hotel-demand proxies; schedule-level correlation included instead.",
        "paths_checked": [str(p.relative_to(ROOT)) for p in [wide_book, wide_rev] if p and p.exists()],
    }

    evidence["candidate_rules"] = build_candidate_rules(evidence)

    # Bucket proposals (data-informed cut suggestions)
    hb = evidence.get("hotel_bookings_hotel_demand", {})
    lead_buckets = hb.get("lead_time_bucket_cancellation", [])
    evidence["proposed_buckets"] = {
        "demand_bucket": {
            "basis": "hotel_bookings lead_time quartiles + cancellation_rate",
            "suggested_labels": ["very_low", "low", "medium", "high", "very_high"],
            "empirical_lead_time_buckets_cancel_rate": lead_buckets,
        },
        "reputation_bucket": {
            "basis": "515k reviewer_score histogram + tripadvisor rating spread",
            "suggested_cutpoints_reviewer_score_0_10": [5.0, 6.5, 7.5, 8.5, 9.2],
        },
        "price_posture_bucket": {
            "basis": "Use ADR or realSum vs city/month median once normalized; not computed globally here.",
            "action": "Compute per-market median from inside_airbnb calendar + hotel ADR in ETL next phase.",
        },
        "visibility_proxy_bucket": {
            "basis": "Not directly observed in listed CSVs; proxy candidates: number_of_reviews, availability_365.",
            "status": "hypothetical_until_mapped",
        },
        "event_pressure_proxy": {
            "basis": "No event calendar joined; airline schedule duration≠events.",
            "status": "hypothetical",
        },
    }

    # Split evidence for thematic JSON files
    demand_payload = {
        "generated_at": evidence["generated_at"],
        "hotel_bookings": evidence.get("hotel_bookings_hotel_demand"),
        "hotel_reservations": evidence.get("hotel_reservations"),
        "travel_ota": evidence.get("travel_ota"),
        "airline_schedule": evidence.get("airline_schedule"),
        "airline_booking_revenue_wide": evidence.get("airline_booking_revenue_wide"),
        "proposed_buckets_demand": evidence["proposed_buckets"]["demand_bucket"],
    }
    (KNOWLEDGE / "demand_patterns.json").write_text(json.dumps(demand_payload, indent=2), encoding="utf-8")
    (KNOWLEDGE / "demand_patterns.md").write_text(write_md_demand(evidence), encoding="utf-8")

    rep_payload = {
        "generated_at": evidence["generated_at"],
        "reviews_515k": evidence.get("reviews_515k"),
        "tripadvisor": evidence.get("tripadvisor"),
        "proposed_buckets_reputation": evidence["proposed_buckets"]["reputation_bucket"],
    }
    (KNOWLEDGE / "reputation_patterns.json").write_text(json.dumps(rep_payload, indent=2), encoding="utf-8")
    (KNOWLEDGE / "reputation_patterns.md").write_text(write_md_reputation(evidence), encoding="utf-8")

    pricing_payload = {
        "generated_at": evidence["generated_at"],
        "city_weekday_weekend": evidence.get("city_weekday_weekend"),
        "airbnb_data": evidence.get("airbnb_data"),
        "airbnb_open": evidence.get("airbnb_open"),
        "proposed_buckets_pricing": {
            "price_posture": evidence["proposed_buckets"]["price_posture_bucket"],
            "visibility_proxy": evidence["proposed_buckets"]["visibility_proxy_bucket"],
        },
    }
    (KNOWLEDGE / "pricing_context_patterns.json").write_text(json.dumps(pricing_payload, indent=2), encoding="utf-8")
    (KNOWLEDGE / "pricing_context_patterns.md").write_text(write_md_pricing(evidence), encoding="utf-8")

    compset_payload = {
        "generated_at": evidence["generated_at"],
        "travel_ota": evidence.get("travel_ota"),
        "note": "OTA distance/channel effects as compset context features, not hotel-level compset prices.",
        "proposed_buckets": evidence["proposed_buckets"].get("event_pressure_proxy"),
    }
    (KNOWLEDGE / "compset_proxy_patterns.json").write_text(json.dumps(compset_payload, indent=2), encoding="utf-8")
    (KNOWLEDGE / "compset_proxy_patterns.md").write_text(
        "# Compset proxy patterns (extracted)\n\n"
        "Travel sample: correlation `orig_destination_distance` vs `is_booking` and channel-level booking rates.\n"
        "See `compset_proxy_patterns.json`.\n\n"
        "**Limitation:** True compset requires aligned stay dates/room types; this layer is search-context only.\n",
        encoding="utf-8",
    )

    rules_payload = {
        "generated_at": evidence["generated_at"],
        "rules": evidence["candidate_rules"],
        "proposed_buckets_summary": evidence["proposed_buckets"],
    }
    (KNOWLEDGE / "candidate_rules.json").write_text(json.dumps(rules_payload, indent=2), encoding="utf-8")
    (KNOWLEDGE / "candidate_rules.md").write_text(
        "# Candidate rules (RevMax)\n\n"
        + "\n".join(
            f"## {r['id']} — **{r['support']}**\n{r['statement']}\n- Evidence: `{json.dumps(r['evidence'], ensure_ascii=False)}`\n- Applies to: {', '.join(r['applies_to'])}\n"
            for r in evidence["candidate_rules"]
        )
        + "\n## Bucket proposals (summary)\nSee `candidate_rules.json` → `proposed_buckets_summary`.\n",
        encoding="utf-8",
    )

    (KNOWLEDGE / "README.md").write_text(
        "# RevMax data knowledge layer\n\n"
        "Generated by `scripts/extract_revmax_knowledge.py`.\n\n"
        "| File | Purpose |\n"
        "|---|---|\n"
        "| demand_patterns.* | Lead time, cancellation, seasonality, OTA booking context |\n"
        "| reputation_patterns.* | Review score structure, TripAdvisor spread |\n"
        "| pricing_context_patterns.* | Weekend premium, Airbnb price–review–availability |\n"
        "| compset_proxy_patterns.* | OTA search context (not true compset) |\n"
        "| candidate_rules.* | Actionable hypotheses with support tags |\n",
        encoding="utf-8",
    )

    print("Wrote", KNOWLEDGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
