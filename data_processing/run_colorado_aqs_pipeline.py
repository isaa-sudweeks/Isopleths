"""Download, validate, package, and publish Colorado AQS inputs to GitHub.

Requires authenticated GitHub CLI. Optional PID attaches to an existing download.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/colorado/aqs/080590006/raw"
RELEASE = RAW.parent / "release"
STATUS = ROOT / "outputs/colorado_aqs/status.json"
TAG = "colorado-aqs-2024-2025-v1"
REPO = "isaa-sudweeks/Isopleths"


def status(stage, **details):
    value = {"stage": stage, "updated_at_utc": datetime.now(timezone.utc).isoformat(), **details}
    temp = STATUS.with_suffix(".json.part")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(STATUS)
    print(json.dumps(value), flush=True)


def run(args):
    return subprocess.run(args, cwd=ROOT, text=True, check=True, capture_output=True).stdout


def gh(*args):
    return run(["gh", *args, "--repo", REPO])


def main(pid):
    while pid is not None:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        manifest_path = RAW / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        status("downloading", completed_batches=len(manifest.get("chunks", [])), expected_batches=28,
               raw_rows=sum(c["rows"] for c in manifest.get("chunks", [])))
        time.sleep(30)
    for attempt in range(3):
        manifest_path = RAW / "manifest.json"
        if manifest_path.exists() and json.loads(manifest_path.read_text()).get("complete"):
            break
        status("resuming_download", attempt=attempt + 1)
        # Capture any resumed output in a durable log; never emit credentials.
        with (STATUS.parent / "download_resume.log").open("a") as log:
            subprocess.run([sys.executable, "-u", "data_processing/download_colorado_aqs.py"], cwd=ROOT,
                           stdout=log, stderr=subprocess.STDOUT, check=False)
    status("validating_and_packaging")
    print(run([sys.executable, "data_processing/package_colorado_aqs.py"]), flush=True)
    provenance = json.loads((RELEASE / "colorado_aqs_provenance.json").read_text())
    assets = [RELEASE / item["filename"] for item in provenance["files"]]
    assets += [RELEASE / "colorado_aqs_provenance.json", RELEASE / "colorado_aqs_SHA256SUMS.txt"]
    notes = RELEASE / "release_notes.md"
    notes.write_text(f"""Raw EPA AQS sample records for Rocky Flats North, Colorado (08-059-0006).

Requested period: January 1, 2024 through December 31, 2025, inclusive.
Total raw records: {provenance['total_rows']:,}.

Includes 60 monitored VOC-class parameters plus n-dodecane and 1-hexene, and NO, NO2, NOy, NOy minus NO, ozone, and solar radiation. All selected requests completed, including any explicit no-data results. Measurement coverage may be incomplete; per-parameter counts, date ranges, units, sample durations, methods, missing measurements, and POCs are recorded in each archive's manifest.

All original sample fields are preserved. No VOC aggregation, NOx derivation, smoke labeling, or surface fitting has been performed. Total NMOC must not be added to individual VOC species.

Each yearly archive contains raw compressed CSV batches, request provenance without credentials, hashes, and the parameter selection. The attached provenance and checksum files verify the yearly archives. CSV blank sample measurements represent missing values retained from the source.

Source: https://aqs.epa.gov/aqsweb/documents/data_api.html
Downloader and documentation: https://github.com/isaa-sudweeks/Isopleths/tree/codex/colorado-hms-smoke
""")
    status("uploading", total_rows=provenance["total_rows"])
    existing = subprocess.run(["gh", "release", "view", TAG, "--repo", REPO, "--json", "isDraft,assets,url"], cwd=ROOT, text=True, capture_output=True)
    if existing.returncode != 0:
        target = run(["git", "rev-parse", "origin/codex/colorado-hms-smoke"]).strip()
        gh("release", "create", TAG, "--target", target, "--title", "Colorado AQS raw data — 2024–2025", "--notes-file", str(notes), "--draft")
        is_draft = True
    else:
        is_draft = json.loads(existing.stdout)["isDraft"]
    if is_draft:
        gh("release", "upload", TAG, *map(str, assets), "--clobber")
    uploaded = json.loads(gh("release", "view", TAG, "--json", "assets,isDraft,url"))
    by_name = {a["name"]: a for a in uploaded["assets"]}
    for path in assets:
        asset = by_name[path.name]
        expected = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if asset.get("digest") != expected or asset["size"] != path.stat().st_size or asset["state"] != "uploaded":
            raise ValueError(f"Uploaded asset failed verification: {path.name}")
    if is_draft:
        gh("release", "edit", TAG, "--draft=false", "--latest=false")
    final = json.loads(gh("release", "view", TAG, "--json", "url,isDraft"))
    if final["isDraft"]:
        raise ValueError("Release was not published")
    status("published", url=final["url"], total_rows=provenance["total_rows"], files=[p.name for p in assets])


if __name__ == "__main__":
    try:
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
    except Exception as error:
        status("failed", error_type=type(error).__name__, message="Acquisition, validation, or publication failed; inspect local logs and completed checkpoints.")
        raise
