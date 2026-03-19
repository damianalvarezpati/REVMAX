#!/usr/bin/env python3
"""
RevMax public datasets bootstrapper.

Creates:
- data/public_datasets/<dataset_slug>/
- per-dataset README.md
- data/public_datasets/DATASETS_INDEX.md
- data/public_datasets/download_log.md

This script never claims "downloaded" unless files exist on disk.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import shutil
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import urllib.request


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATASETS_DIR = ROOT / "data" / "public_datasets"


STAT_DOWNLOADED = "downloaded"
STAT_MANUAL = "manual-download-required"
STAT_LOGIN = "login-required"
STAT_API = "api-based"
STAT_UNAVAILABLE = "unavailable"


@dataclass
class DatasetSpec:
    slug: str
    name: str
    category: str
    utility: str
    links: List[str]
    downloader: Optional[Callable[[Path], Dict]] = None
    default_status: str = STAT_MANUAL
    notes: str = ""


@dataclass
class DatasetResult:
    slug: str
    status: str
    files: List[Path] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def total_bytes(self) -> int:
        size = 0
        for f in self.files:
            try:
                size += f.stat().st_size
            except FileNotFoundError:
                pass
        return size


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    for u in units:
        if v < 1024 or u == units[-1]:
            if u == "B":
                return f"{int(v)} {u}"
            return f"{v:.2f} {u}"
        v /= 1024
    return f"{n} B"


def list_files_recursive(folder: Path) -> List[Path]:
    out: List[Path] = []
    for p in folder.rglob("*"):
        if p.is_file():
            out.append(p)
    return sorted(out)


def copy_file(src: Path, dst: Path) -> Path:
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return dst


def download_url_to_file(url: str, dst: Path, timeout: int = 120) -> Path:
    ensure_dir(dst.parent)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = r.read()
    dst.write_bytes(data)
    return dst


def try_import_kagglehub():
    try:
        import kagglehub  # type: ignore

        return kagglehub
    except Exception:
        return None


def kaggle_cli_available() -> bool:
    try:
        p = subprocess.run(
            ["kaggle", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return p.returncode == 0
    except FileNotFoundError:
        return False


def kaggle_credentials_available() -> bool:
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    cfg = Path.home() / ".kaggle" / "kaggle.json"
    if not cfg.exists():
        return False
    try:
        payload = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(payload.get("username") and payload.get("key"))


def kaggle_env_notes() -> List[str]:
    notes = []
    if kaggle_cli_available():
        notes.append("kaggle CLI detected.")
    else:
        notes.append("kaggle CLI NOT detected. Install with: python3 -m pip install kaggle")
    if kaggle_credentials_available():
        notes.append("Kaggle credentials detected.")
    else:
        notes.append(
            "Kaggle credentials NOT detected. Configure ~/.kaggle/kaggle.json or env vars KAGGLE_USERNAME/KAGGLE_KEY."
        )
    return notes


def kaggle_manual_commands_md() -> str:
    return """## Manual Commands (if Kaggle CLI is not configured)

```bash
# 1) Install Kaggle CLI and kagglehub
python3 -m pip install --upgrade kaggle kagglehub

# 2) Create Kaggle credentials folder/file
mkdir -p ~/.kaggle
cat > ~/.kaggle/kaggle.json <<'EOF'
{
  "username": "YOUR_KAGGLE_USERNAME",
  "key": "YOUR_KAGGLE_KEY"
}
EOF
chmod 600 ~/.kaggle/kaggle.json

# 3) Verify authentication
kaggle datasets list -s hotel-booking-demand | head

# 4) Download dataset examples
kaggle datasets download -d jessemostipak/hotel-booking-demand -p "./data/public_datasets/hotel_booking_demand" --unzip
kaggle datasets download -d jiashenliu/515k-hotel-reviews-data-in-europe -p "./data/public_datasets/hotel_reviews_europe_515k" --unzip
kaggle datasets download -d andrewmvd/trip-advisor-hotel-reviews -p "./data/public_datasets/tripadvisor_hotel_reviews" --unzip

# 5) Competition datasets (requires accepting rules in browser first)
open "https://www.kaggle.com/competitions/expedia-hotel-recommendations/rules"
open "https://www.kaggle.com/competitions/expedia-personalized-sort/rules"
kaggle competitions download -c expedia-hotel-recommendations -p "./data/public_datasets/expedia_hotel_recommendations"
kaggle competitions download -c expedia-personalized-sort -p "./data/public_datasets/expedia_personalized_sort"
```
"""


def downloader_kaggle_dataset(dataset_handle: str) -> Callable[[Path], Dict]:
    def _run(target_dir: Path) -> Dict:
        env_notes = kaggle_env_notes()
        kagglehub = try_import_kagglehub()
        if kagglehub is None:
            return {
                "status": STAT_MANUAL,
                "notes": env_notes
                + [
                    "kagglehub not installed. Run: python3 -m pip install kagglehub",
                    f"Then download manually from {dataset_handle}",
                ],
                "files": [],
            }
        cache_path = Path(kagglehub.dataset_download(dataset_handle))
        files = [p for p in cache_path.iterdir() if p.is_file()]
        copied: List[Path] = []
        for f in files:
            copied.append(copy_file(f, target_dir / f.name))
        status = STAT_DOWNLOADED if copied else STAT_UNAVAILABLE
        notes = env_notes + [f"kagglehub cache source: {cache_path}"]
        return {"status": status, "files": copied, "notes": notes}

    return _run


def downloader_kaggle_competition(comp_handle: str) -> Callable[[Path], Dict]:
    def _run(target_dir: Path) -> Dict:
        env_notes = kaggle_env_notes()
        kagglehub = try_import_kagglehub()
        if kagglehub is None:
            return {
                "status": STAT_MANUAL,
                "notes": env_notes
                + [
                    "kagglehub not installed. Run: python3 -m pip install kagglehub",
                    f"Competition manual URL: https://www.kaggle.com/c/{comp_handle}/data",
                ],
                "files": [],
            }
        try:
            cache_path = Path(kagglehub.competition_download(comp_handle))
        except Exception as e:
            msg = str(e)
            if "accepted the competition rules" in msg.lower():
                return {
                    "status": STAT_LOGIN,
                    "notes": env_notes
                    + [
                        "Competition requires login and rule acceptance.",
                        f"Open and accept rules: https://www.kaggle.com/competitions/{comp_handle}/rules",
                    ],
                    "files": [],
                    "error": msg,
                }
            return {
                "status": STAT_LOGIN,
                "notes": env_notes
                + [
                    "Kaggle competition download failed. Check credentials (KAGGLE_USERNAME/KAGGLE_KEY or ~/.kaggle/kaggle.json).",
                    f"Competition URL: https://www.kaggle.com/c/{comp_handle}/data",
                ],
                "files": [],
                "error": msg,
            }

        files = [p for p in cache_path.iterdir() if p.is_file()]
        copied: List[Path] = []
        for f in files:
            copied.append(copy_file(f, target_dir / f.name))
        status = STAT_DOWNLOADED if copied else STAT_UNAVAILABLE
        return {"status": status, "files": copied, "notes": env_notes + [f"kagglehub cache source: {cache_path}"]}

    return _run


def downloader_uci_hotel_booking(target_dir: Path) -> Dict:
    """
    Tries UCI direct file endpoints.
    """
    candidates = [
        # Common UCI legacy static hosting patterns
        "https://archive.ics.uci.edu/static/public/495/hotel+booking+demand.zip",
        "https://archive.ics.uci.edu/ml/machine-learning-databases/00483/hotel_bookings.csv",
    ]
    errors: List[str] = []
    downloaded: List[Path] = []
    for url in candidates:
        try:
            filename = url.split("/")[-1] or "uci_file"
            out = download_url_to_file(url, target_dir / filename, timeout=120)
            downloaded.append(out)
        except Exception as e:
            errors.append(f"{url} -> {e}")
    if downloaded:
        return {
            "status": STAT_DOWNLOADED,
            "files": downloaded,
            "notes": ["Downloaded from UCI endpoints."],
        }
    return {
        "status": STAT_MANUAL,
        "files": [],
        "notes": [
            "Could not fetch directly from UCI candidate URLs.",
            "Download manually from UCI page and place files in this folder.",
        ]
        + errors,
    }


def downloader_inside_airbnb(target_dir: Path) -> Dict:
    # insideairbnb provides city-specific snapshots via web selection.
    return {
        "status": STAT_MANUAL,
        "files": [],
        "notes": [
            "Inside Airbnb requires choosing city + snapshot manually from get-the-data page.",
            "Recommended: download listings.csv, calendar.csv, reviews.csv for selected markets.",
            "Source: https://insideairbnb.com/get-the-data/",
        ],
    }


def downloader_eurostat(target_dir: Path) -> Dict:
    # Provide API-based starter by downloading metadata/table descriptors.
    urls = [
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tour_occ_ninat?geo=ES&unit=NR&time=2023",
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tour_occ_ninc?geo=ES&unit=NR&time=2023",
    ]
    downloaded: List[Path] = []
    notes: List[str] = []
    for i, url in enumerate(urls, start=1):
        try:
            out = download_url_to_file(url, target_dir / f"eurostat_sample_{i}.json", timeout=120)
            downloaded.append(out)
        except Exception as e:
            notes.append(f"{url} -> {e}")
    if downloaded:
        return {
            "status": STAT_API,
            "files": downloaded,
            "notes": ["Eurostat API sample JSON downloaded.", "Use API/bulk for full extracts."] + notes,
        }
    return {
        "status": STAT_API,
        "files": [],
        "notes": ["Eurostat API endpoint unreachable in this run. Keep as api-based/manual."] + notes,
    }


def downloader_gdelt(target_dir: Path) -> Dict:
    urls = [
        "http://data.gdeltproject.org/gdeltv2/lastupdate.txt",
        "https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf",
    ]
    downloaded: List[Path] = []
    notes: List[str] = []
    for url in urls:
        try:
            filename = url.split("/")[-1]
            out = download_url_to_file(url, target_dir / filename, timeout=120)
            downloaded.append(out)
        except Exception as e:
            notes.append(f"{url} -> {e}")
    if downloaded:
        return {
            "status": STAT_API,
            "files": downloaded,
            "notes": ["Downloaded GDELT reference/sample files."] + notes,
        }
    return {
        "status": STAT_API,
        "files": [],
        "notes": ["Could not fetch GDELT files in this run."] + notes,
    }


DATASETS: List[DatasetSpec] = [
    DatasetSpec(
        slug="hotel_booking_demand",
        name="Hotel Booking Demand Dataset",
        category="demanda hotelera / comportamiento de reserva",
        utility="Base para demanda, cancelaciones, lead time, segmentación.",
        links=[
            "https://archive.ics.uci.edu/dataset/495/hotel+booking+demand",
            "https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand",
        ],
        downloader=downloader_kaggle_dataset("jessemostipak/hotel-booking-demand"),
        default_status=STAT_DOWNLOADED,
        notes="UCI + Kaggle variants available.",
    ),
    DatasetSpec(
        slug="expedia_hotel_recommendations",
        name="Expedia Hotel Recommendations",
        category="recomendación / ranking / conversión",
        utility="Aprendizaje de elección de hotel y señales de comportamiento de reserva.",
        links=["https://www.kaggle.com/c/expedia-hotel-recommendations/data"],
        downloader=downloader_kaggle_competition("expedia-hotel-recommendations"),
        default_status=STAT_LOGIN,
    ),
    DatasetSpec(
        slug="expedia_personalized_sort",
        name="Expedia Personalized Sort",
        category="ranking / personalización / pricing relativo",
        utility="Modelado de ordenación y sensibilidad a señales de precio/atributos.",
        links=["https://www.kaggle.com/c/expedia-personalized-sort/data"],
        downloader=downloader_kaggle_competition("expedia-personalized-sort"),
        default_status=STAT_LOGIN,
    ),
    DatasetSpec(
        slug="inside_airbnb",
        name="Inside Airbnb",
        category="oferta alternativa / contexto de mercado",
        utility="Presión competitiva de alquileres de corta estancia por ciudad/zona.",
        links=[
            "https://insideairbnb.com/get-the-data/",
            "https://insideairbnb.com/explore/",
            "https://insideairbnb.com/data-assumptions",
        ],
        downloader=downloader_inside_airbnb,
        default_status=STAT_MANUAL,
    ),
    DatasetSpec(
        slug="eurostat_tourism",
        name="Eurostat Tourism",
        category="macro turístico / ocupación",
        utility="Contexto macro de ocupación y pernoctaciones por región/periodo.",
        links=[
            "https://ec.europa.eu/eurostat/web/tourism/database",
            "https://ec.europa.eu/eurostat/databrowser/view/TOUR_OCC_MNOR/",
            "https://ec.europa.eu/eurostat/databrowser/view/tour_occ_ninat/default/table?lang=en",
            "https://ec.europa.eu/eurostat/databrowser/view/tour_occ_ninc/default/table?lang=en",
        ],
        downloader=downloader_eurostat,
        default_status=STAT_API,
    ),
    DatasetSpec(
        slug="gdelt",
        name="GDELT",
        category="eventos / contexto geopolítico",
        utility="Señales de eventos para event-pressure y shocks de demanda.",
        links=[
            "https://www.gdeltproject.org/",
            "https://www.gdeltproject.org/data.html",
            "https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf",
        ],
        downloader=downloader_gdelt,
        default_status=STAT_API,
    ),
    DatasetSpec(
        slug="hotel_reviews_europe_515k",
        name="515K Hotel Reviews Data in Europe",
        category="reputación / NLP reviews",
        utility="Entrenamiento de extracción de sentiment y price-perception.",
        links=["https://www.kaggle.com/datasets/jiashenliu/515k-hotel-reviews-data-in-europe"],
        downloader=downloader_kaggle_dataset("jiashenliu/515k-hotel-reviews-data-in-europe"),
        default_status=STAT_LOGIN,
    ),
    DatasetSpec(
        slug="tripadvisor_hotel_reviews",
        name="TripAdvisor Hotel Reviews",
        category="reputación / NLP reviews",
        utility="Clasificación de sentimiento y tópicos de reputación hotelera.",
        links=[
            "https://www.kaggle.com/datasets/joebeachcapital/hotel-reviews",
            "https://www.kaggle.com/datasets/andrewmvd/trip-advisor-hotel-reviews",
        ],
        downloader=downloader_kaggle_dataset("andrewmvd/trip-advisor-hotel-reviews"),
        default_status=STAT_LOGIN,
        notes="Primary attempt uses andrewmvd/trip-advisor-hotel-reviews.",
    ),
]


def build_dataset_readme(spec: DatasetSpec, result: DatasetResult) -> str:
    lines = [
        f"# {spec.name}",
        "",
        f"- **slug**: `{spec.slug}`",
        f"- **category**: {spec.category}",
        f"- **utility_for_revmax**: {spec.utility}",
        f"- **status**: `{result.status}`",
        "",
        "## Source Links",
    ]
    for link in spec.links:
        lines.append(f"- {link}")

    lines += [
        "",
        "## Files in this folder",
    ]
    if result.files:
        for f in result.files:
            rel = f.relative_to(ROOT)
            lines.append(f"- `{rel}` ({human_bytes(f.stat().st_size)})")
    else:
        lines.append("- No files downloaded in this run.")

    lines += [
        "",
        "## Format",
        "- Mostly CSV/JSON/ZIP depending on source.",
        "",
        "## Next Recommended Steps",
        "- Validate schema and row counts.",
        "- Add data dictionary for model features.",
        "- Build ingestion/normalization notebook or script before training.",
        "",
        "## Notes",
    ]
    if spec.notes:
        lines.append(f"- {spec.notes}")
    for n in result.notes:
        lines.append(f"- {n}")
    if result.error:
        lines.append(f"- Error: {result.error}")
    body = "\n".join(lines) + "\n"

    kaggle_link = any("kaggle.com" in link for link in spec.links)
    if kaggle_link and result.status in {STAT_LOGIN, STAT_MANUAL, STAT_UNAVAILABLE}:
        body += "\n" + kaggle_manual_commands_md() + "\n"
    return body


def build_index_md(results: List[DatasetResult], specs: Dict[str, DatasetSpec]) -> str:
    lines = [
        "# Public Datasets Index",
        "",
        f"_Generated at {dt.datetime.utcnow().isoformat()}Z_",
        "",
        "| dataset | category | utility for RevMax | link | status | approx size | notes |",
        "|---|---|---|---|---|---:|---|",
    ]
    for r in results:
        s = specs[r.slug]
        size = human_bytes(r.total_bytes) if r.total_bytes > 0 else "-"
        link = s.links[0] if s.links else "-"
        note = (r.notes[0] if r.notes else s.notes) or "-"
        note = note.replace("|", "/")
        lines.append(
            f"| `{s.slug}` | {s.category} | {s.utility} | {link} | `{r.status}` | {size} | {note} |"
        )
    return "\n".join(lines) + "\n"


def build_log_md(results: List[DatasetResult], specs: Dict[str, DatasetSpec]) -> str:
    ts = dt.datetime.utcnow().isoformat() + "Z"
    lines = [
        "# Download Log",
        "",
        f"- run_at: `{ts}`",
        "",
        "| dataset | success | status | detail |",
        "|---|---|---|---|",
    ]
    for r in results:
        success = "yes" if r.status == STAT_DOWNLOADED else "no"
        detail = "; ".join(r.notes[:2]) if r.notes else "-"
        if r.error:
            detail = f"{detail}; error={r.error[:240]}"
        detail = detail.replace("|", "/")
        lines.append(f"| `{r.slug}` | {success} | `{r.status}` | {detail} |")
    return "\n".join(lines) + "\n"


def build_local_assets_manifest(results: List[DatasetResult], specs: Dict[str, DatasetSpec]) -> str:
    lines = [
        "# Local Assets Manifest (Not Tracked in Git)",
        "",
        "This file documents local raw dataset files that may exist on disk but are intentionally ignored by git.",
        "",
        f"_Generated at {dt.datetime.utcnow().isoformat()}Z_",
        "",
        "| dataset | local file | size_bytes | approx size | sha256 | reconstruction hint |",
        "|---|---|---:|---:|---|---|",
    ]
    rows = 0
    for r in results:
        spec = specs[r.slug]
        for f in r.files:
            if not f.exists():
                continue
            rel = f.relative_to(ROOT)
            size = f.stat().st_size
            # Calculate digest with bounded memory.
            import hashlib

            h = hashlib.sha256()
            with f.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
            hint = spec.links[0] if spec.links else "-"
            lines.append(
                f"| `{r.slug}` | `{rel}` | {size} | {human_bytes(size)} | `{digest}` | {hint} |"
            )
            rows += 1
    if rows == 0:
        lines.append("| - | - | - | - | - | No local raw files detected in this run. |")
    return "\n".join(lines) + "\n"


def run_dataset(spec: DatasetSpec) -> DatasetResult:
    folder = PUBLIC_DATASETS_DIR / spec.slug
    ensure_dir(folder)

    if spec.downloader is None:
        return DatasetResult(
            slug=spec.slug,
            status=spec.default_status,
            files=[],
            notes=["No automatic downloader configured."],
        )

    try:
        payload = spec.downloader(folder)
        status = payload.get("status", spec.default_status)
        files = payload.get("files", []) or []
        notes = payload.get("notes", []) or []
        error = payload.get("error")
        return DatasetResult(
            slug=spec.slug,
            status=status,
            files=[Path(f) for f in files],
            notes=[str(n) for n in notes],
            error=str(error) if error else None,
        )
    except Exception as e:
        return DatasetResult(
            slug=spec.slug,
            status=STAT_UNAVAILABLE,
            files=[],
            notes=["Unhandled exception in downloader."],
            error=f"{e}\n{traceback.format_exc()}",
        )


def main() -> int:
    ensure_dir(PUBLIC_DATASETS_DIR)
    specs = {s.slug: s for s in DATASETS}

    results: List[DatasetResult] = []
    for spec in DATASETS:
        result = run_dataset(spec)
        results.append(result)

        readme = build_dataset_readme(spec, result)
        write_text(PUBLIC_DATASETS_DIR / spec.slug / "README.md", readme)

    write_text(PUBLIC_DATASETS_DIR / "DATASETS_INDEX.md", build_index_md(results, specs))
    write_text(PUBLIC_DATASETS_DIR / "download_log.md", build_log_md(results, specs))
    write_text(PUBLIC_DATASETS_DIR / "KAGGLE_MANUAL_SETUP.md", kaggle_manual_commands_md())
    write_text(PUBLIC_DATASETS_DIR / "LOCAL_ASSETS_MANIFEST.md", build_local_assets_manifest(results, specs))

    print("Public datasets bootstrap completed.")
    for r in results:
        print(f"- {r.slug}: {r.status} (files={len(r.files)} size={human_bytes(r.total_bytes)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

