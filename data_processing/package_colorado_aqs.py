"""Validate a completed Colorado download and build yearly release archives."""

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(raw, output):
    manifest = json.loads((raw / "manifest.json").read_text())
    selection = json.loads((raw / "selection.json").read_text())
    if not manifest.get("complete"):
        raise ValueError("Download is incomplete; refusing to package it")
    codes = set(selection["voc_parameters"]) | set(selection["additional_parameters"]) | set(selection["supplemental_organic_parameters"])
    for year in manifest["years"]:
        requested = [code for chunk in manifest["chunks"] if chunk["query"]["bdate"] == f"{year}0101" for code in chunk["query"]["param"].split(",")]
        if set(requested) != codes or len(requested) != len(codes):
            raise ValueError(f"Parameter selection is incomplete or duplicated for {year}")
    counts = {}
    for chunk in manifest["chunks"]:
        path = raw / chunk["filename"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != chunk["sha256"]:
            raise ValueError(f"Hash mismatch: {path.name}")
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            count = sum(1 for _ in csv.DictReader(stream))
        if count != chunk["rows"]:
            raise ValueError(f"Row count mismatch: {path.name}")
        year = int(chunk["query"]["bdate"][:4])
        counts[year] = counts.get(year, 0) + count
    output.mkdir(parents=True, exist_ok=True)
    files = []
    for year in manifest["years"]:
        name = f"colorado_080590006_aqs_{year}_raw.zip"
        path = output / name
        temporary = path.with_suffix(".zip.part")
        chunks = [chunk for chunk in manifest["chunks"] if int(chunk["query"]["bdate"][:4]) == year]
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("manifest.json", json.dumps({**manifest, "years": [year], "chunks": chunks, "total_rows": counts[year]}, indent=2) + "\n")
            for filename in ("selection.json", "voc_parameter_catalog.json"):
                archive.write(raw / filename, filename)
            for chunk in chunks:
                archive.write(raw / chunk["filename"], chunk["filename"])
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"Archive integrity check failed: {name}")
        temporary.replace(path)
        files.append({"filename": name, "year": year, "rows": counts[year], "size_bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        print(f"Packaged {name}: {counts[year]:,} rows; {path.stat().st_size:,} bytes", flush=True)
    provenance = {"site": manifest["site"], "years": manifest["years"], "source_endpoint": manifest["endpoint"], "total_rows": sum(counts.values()), "files": files, "note": "Raw sample records, all sample durations and POCs retained. No VOC sum or NOx derivation. Complete means all selected requests completed, not complete measurement coverage."}
    (output / "colorado_aqs_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (output / "colorado_aqs_SHA256SUMS.txt").write_text("".join(f"{item['sha256']}  {item['filename']}\n" for item in files))
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/colorado/aqs/080590006/raw")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/colorado/aqs/080590006/release")
    args = parser.parse_args()
    package(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
