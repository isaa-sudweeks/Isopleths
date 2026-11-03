"""Download resumable raw AQS records for Rocky Flats North in 2024–2025.

Credentials come from AQS_EMAIL/AQS_KEY in the environment or local .env.
All POCs, methods, durations, units, nulls, and qualifiers are retained.
"""

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shlex
import time
import urllib.parse
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = "https://aqs.epa.gov/data/api/"
EXTRA = {"42600", "42601", "42602", "42612", "44201", "63301"}


def credentials():
    values = {}
    if (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            line = line.strip().removeprefix("export ")
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                parts = shlex.split(value, comments=True)
                values[key.strip()] = parts[0] if parts else ""
    result = {key: os.environ.get(name) or values.get(name) for key, name in [("email", "AQS_EMAIL"), ("key", "AQS_KEY")]}
    if not all(result.values()):
        raise RuntimeError("Configure AQS_EMAIL and AQS_KEY in the environment or local .env")
    return result


def request(endpoint, query, auth):
    url = API + endpoint + "?" + urllib.parse.urlencode({**auth, **query})
    http_request = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(http_request, timeout=180) as response:
                raw = response.read()
                if response.headers.get("Content-Encoding", "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                payload = json.loads(raw)
            statuses = [item.get("status", "") for item in payload.get("Header", [])]
            if statuses and all(s in ("Success", "No data matched your selection") for s in statuses):
                return payload.get("Data") or []
            # Server error text could echo credentials; never log it.
            raise RuntimeError("Unsuccessful AQS response")
        except (urllib.error.URLError, OSError, json.JSONDecodeError, RuntimeError):
            if attempt == 4:
                raise RuntimeError(f"AQS request failed after 5 attempts: {endpoint} (credentials omitted)") from None
            print(f"Retrying {endpoint}: attempt {attempt + 2}/5", flush=True)
            time.sleep(min(10 * 2**attempt, 60))
        finally:
            time.sleep(6)  # Sequential calls, at most ten per minute.


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_rows(rows, query):
    for row in rows:
        site = tuple(str(row[key]).zfill(width) for key, width in [("state_code", 2), ("county_code", 3), ("site_number", 4)])
        if site != ("08", "059", "0006") or str(row["parameter_code"]) not in query["param"].split(","):
            raise ValueError("EPA returned an unexpected site or parameter")
        if not query["bdate"] <= row["date_local"].replace("-", "") <= query["edate"]:
            raise ValueError("EPA returned an unexpected date")


def download(output, years):
    output.mkdir(parents=True, exist_ok=True)
    auth = credentials()
    config = json.loads((ROOT / "docs/data/colorado_aqs_parameters.json").read_text())
    catalog_path = output / "voc_parameter_catalog.json"
    if not catalog_path.exists():
        write_json(catalog_path, request("list/parametersByClass", {"pc": "VOC"}, auth))
    voc_codes = {str(row["code"]) for row in json.loads(catalog_path.read_text())}
    monitored = config["recent_monitored_parameters"]
    selected = sorted((voc_codes & monitored.keys()) | EXTRA)
    # Some individually monitored organic species are absent from EPA's VOC
    # class. Append them so existing five-parameter cached batches stay usable.
    supplemental = sorted(code for code in monitored if code.startswith(("43", "45")) and code not in selected)
    selected.extend(supplemental)
    write_json(output / "selection.json", {"site": config["site"], "years": years, "voc_parameters": {code: monitored[code] for code in selected if code in voc_codes}, "supplemental_organic_parameters": {code: monitored[code] for code in supplemental}, "additional_parameters": {code: monitored[code] for code in sorted(EXTRA)}, "note": "All sample durations, POCs, methods, units, nulls and qualifiers retained. No aggregation or NOx derivation performed."})
    manifest = {"site": config["site"], "years": years, "endpoint": API + "sampleData/bySite", "chunks": [], "complete": False}
    for year in years:
        for start in range(0, len(selected), 5):
            codes = selected[start:start + 5]
            query = {"state": "08", "county": "059", "site": "0006", "param": ",".join(codes), "bdate": f"{year}0101", "edate": f"{year}1231"}
            name = f"aqs_080590006_{year}_{'-'.join(codes)}.csv.gz"
            path, meta_path = output / name, output / (name + ".json")
            if path.exists() and meta_path.exists():
                meta = json.loads(meta_path.read_text())
                if meta["query"] != query or meta["sha256"] != digest(path):
                    raise ValueError(f"Cached chunk does not match metadata: {name}")
                print(f"Reusing {name}: {meta['rows']:,} rows", flush=True)
            else:
                print(f"Downloading {year} parameters {','.join(codes)}", flush=True)
                rows = request("sampleData/bySite", query, auth)
                validate_rows(rows, query)
                temporary = path.with_suffix(path.suffix + ".part")
                fields = sorted({key for row in rows for key in row})
                with gzip.open(temporary, "wt", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                temporary.replace(path)
                stats = {}
                for row in rows:
                    code = str(row["parameter_code"])
                    stat = stats.setdefault(code, {"parameter": row["parameter"], "rows": 0, "first_date": row["date_local"], "last_date": row["date_local"], "null_measurements": 0, "units": set(), "durations": set(), "pocs": set(), "methods": set()})
                    stat["rows"] += 1
                    stat["first_date"] = min(stat["first_date"], row["date_local"])
                    stat["last_date"] = max(stat["last_date"], row["date_local"])
                    stat["null_measurements"] += row.get("sample_measurement") is None
                    for field, key in [("units", "units_of_measure"), ("durations", "sample_duration"), ("pocs", "poc"), ("methods", "method_code")]:
                        stat[field].add(str(row.get(key)))
                for stat in stats.values():
                    for field in ("units", "durations", "pocs", "methods"):
                        stat[field] = sorted(stat[field])
                meta = {"filename": name, "query": query, "downloaded_at_utc": datetime.now(timezone.utc).isoformat(), "rows": len(rows), "size_bytes": path.stat().st_size, "sha256": digest(path), "parameters": stats, "no_data_parameters": sorted(set(codes) - stats.keys())}
                write_json(meta_path, meta)
                print(f"Saved {name}: {len(rows):,} rows", flush=True)
            manifest["chunks"].append(meta)
            write_json(output / "manifest.json", manifest)
    manifest.update(complete=True, total_rows=sum(item["rows"] for item in manifest["chunks"]))
    write_json(output / "manifest.json", manifest)
    print(f"COMPLETE: {manifest['total_rows']:,} raw rows in {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/colorado/aqs/080590006/raw")
    args = parser.parse_args()
    if not set(args.years) <= {2024, 2025}:
        parser.error("Selection is scoped to 2024–2025; refresh the inventory for other years.")
    download(args.output_dir, sorted(set(args.years)))


if __name__ == "__main__":
    main()
