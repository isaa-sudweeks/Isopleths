# Rocky Flats North raw AQS downloads

Site: **08-059-0006**, Rocky Flats North, Jefferson County, Colorado.
Initial requested period: **January 1, 2024 through December 31, 2025**, inclusive.

## Acquisition

Run from the repository root:

```bash
python3 data_processing/download_colorado_aqs.py
```

Set `AQS_EMAIL` and `AQS_KEY` in the environment or the ignored local `.env`
file. Credentials and authenticated URLs are not saved in the dataset or logs.
The downloader uses Python's standard library, submits requests sequentially,
and pauses at least six seconds between requests. Failed requests are retried.
Completed chunks can be resumed after their hashes are checked.

The selection intersects EPA's VOC parameter class with the site's recent
monitor inventory and adds two monitored organic species absent from that class:
n-dodecane (`43141`) and 1-hexene (`43245`). It additionally requests NO (`42601`), NO2 (`42602`),
NOy (`42600`), NOy minus NO (`42612`), ozone (`44201`), and solar radiation
(`63301`). The checked-in inventory selection records its source and date.

Outputs are compressed raw CSV batches in
`data/colorado/aqs/080590006/raw/`, with request metadata, per-parameter record
counts and date ranges, and SHA-256 hashes in `manifest.json`. AQS response
headers are omitted because they can contain authenticated URLs. All sample
durations, POCs, methods, units, missing measurements, and qualifiers are
retained. No VOC sum, NOx derivation, smoke classification, or model fitting
is performed at download time.

Total NMOC is retained as a separate measurement, not added to individual
species. Any later VOC sum must explicitly select compatible species and units.

## GitHub data snapshot

The active acquisition job has a completion worker that validates the complete
request selection, CSV row counts, gzip contents, and SHA-256 hashes, then
packages one archive per year. It uploads the yearly ZIPs, a provenance JSON,
and a checksum file to the release tag `colorado-aqs-2024-2025-v1`. Uploaded
asset sizes and GitHub SHA-256 digests must match before the draft is published.

Local job status is recorded in `outputs/colorado_aqs/status.json`; the
completion worker logs to `outputs/colorado_aqs/publish.log`. The release is
available only after the status becomes `published`:

[Colorado AQS raw data release](https://github.com/isaa-sudweeks/Isopleths/releases/tag/colorado-aqs-2024-2025-v1)

To package a completed local download manually:

```bash
python3 data_processing/package_colorado_aqs.py
```

For an end-to-end acquisition and GitHub publication run (requires an
authenticated GitHub CLI), use:

```bash
python3 -u data_processing/run_colorado_aqs_pipeline.py
```

This command publishes the release after validation; use the download-only
command above when publication is not wanted. It can also take the PID of an
already running downloader to wait for that process before packaging.

The packaging step refuses incomplete request selections, changed files, and
row-count mismatches. The yearly archives include their request manifests,
parameter catalogs, and selection metadata. Raw CSVs and archives remain in
the ignored `data/` directory rather than Git history.

Inventory endpoints do not guarantee complete coverage. Check the actual
download manifest and sample timestamps before deciding which periods and
species can be compared. A direct NOx (`42603`) monitor is not listed in the
site inventory. Deriving NOx from NO and NO2 requires subsequent checks of
units, instrument methods, and simultaneous valid observations.

## Nearby PM2.5 monitor search

The nearest recent hourly PM2.5 candidate is **Boulder CU–Athens,
08-013-1001, parameter 88101, POC 3**. Its EPA coordinates are
40.012969, -105.267212, approximately **13.00 km northwest** of Rocky Flats
North (39.912795, -105.188575), using great-circle distance.

| Station | AQS site | Continuous PM2.5 POC | Distance from Rocky Flats |
| --- | --- | --- | ---: |
| Boulder CU–Athens | 08-013-1001 | 3 | 13.00 km |
| La Casa | 08-031-0026 | 3 | 21.56 km |
| Welby | 08-001-3001 | 3, 4 | 22.00 km |
| Globeville | 08-031-0028 | 3 | 22.13 km |
| Birch Street | 08-001-0010 | 3 | 23.49 km |

EPA's inventory lists Boulder POC 3 data starting in 2023 and extending through
April 30, 2026. CDPHE lists hourly PM2.5 reporting and documents this POC's
operation beginning in August 2023; its 2025 network plan reports a 2024 annual
mean, confirming actual 2024 measurements exist. Hourly completeness during
2024–2025 still needs to be audited. This is a nearby proxy, not a co-located
measurement. Do not automatically combine continuous and 24-hour POCs.

Sources:

- [EPA monitor inventory](https://aqs.epa.gov/aqsweb/airdata/aqs_monitors.zip)
- [CDPHE station descriptions](https://apcd.state.co.us/site_description.aspx)
- [CDPHE 2025 network plan, Appendix A and Table 6.4](https://apcd.state.co.us/aqidev/tech_doc_repository.aspx?action=open&file=2025AnnualNetworkPlan.pdf)
- [EPA AQS API documentation and request limits](https://aqs.epa.gov/aqsweb/documents/data_api.html)
