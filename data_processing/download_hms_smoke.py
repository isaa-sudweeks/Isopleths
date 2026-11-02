"""Download NOAA HMS annual smoke polygons (North America, including Colorado).

Usage: python3 data_processing/download_hms_smoke.py --years 2024 2025
Archives stay zipped; extract a copy before using the existing smoke notebook.
"""

import argparse
from pathlib import Path
import urllib.request
import zipfile


BASE_URL = (
    "https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS/"
    "Smoke_Polygons/Shapefile/Annual_Bundles"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data/colorado/smoke/hms"


def validate_archive(path):
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"Corrupt ZIP member: {bad_member}")
        names = archive.namelist()
        if not any(name.lower().endswith(".shp") for name in names):
            raise ValueError(f"No smoke shapefiles in {path}")
        return sum(name.lower().endswith(".shp") for name in names)


def download_year(year, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"hms_smoke{year}.zip"
    if destination.exists():
        count = validate_archive(destination)
        print(f"Reusing {destination} ({count} shapefiles)", flush=True)
        return
    url = f"{BASE_URL}/{destination.name}"
    temporary = destination.with_suffix(".zip.part")
    print(f"Downloading {url}", flush=True)
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            with temporary.open("wb") as stream:
                while chunk := response.read(256 * 1024):
                    stream.write(chunk)
        count = validate_archive(temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(
        f"Saved {destination} ({destination.stat().st_size:,} bytes; "
        f"{count} shapefiles)", flush=True
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    for year in dict.fromkeys(args.years):
        if year < 2005 or year > 9999:
            parser.error("Annual bundle years must be between 2005 and 9999.")
        download_year(year, args.output_dir)


if __name__ == "__main__":
    main()
