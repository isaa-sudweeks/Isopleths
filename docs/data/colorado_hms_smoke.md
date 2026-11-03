# Colorado HMS smoke polygon inputs

The [Colorado smoke data release](https://github.com/isaa-sudweeks/Isopleths/releases/tag/colorado-hms-smoke-2024-2025-v1)
preserves the original NOAA HMS annual ZIP archives downloaded for the Colorado
analysis on November 2, 2026. These contain North American smoke polygons,
including Colorado; they have not been clipped or otherwise modified.

| Year | Archive | Polygon records |
| --- | --- | ---: |
| 2024 | `hms_smoke2024.zip` | 12,527 |
| 2025 | `hms_smoke2025.zip` | 24,238 |

Each archive includes `.shp`, `.shx`, `.dbf`, and `.prj` components for one
annual layer. Attributes include `Satellite`, `Start`, `End`, and `Density`.
Density categories are Light, Medium, and Heavy. Polygon counts do not establish
complete daily coverage or surface-level smoke exposure.

## Restore the preserved snapshot

Run from the repository root with the GitHub CLI installed and authenticated
if the repository requires it:

```bash
mkdir -p data/colorado/smoke/hms
gh release download colorado-hms-smoke-2024-2025-v1 \
  --repo isaa-sudweeks/Isopleths \
  --pattern 'hms_smoke*.zip' \
  --dir data/colorado/smoke/hms \
  --skip-existing
(cd data/colorado/smoke/hms && shasum -a 256 -c ../../../../docs/data/colorado_hms_SHA256SUMS.txt)
```

The release also attaches the provenance JSON and checksum file. Source URLs,
byte sizes, and hashes are recorded in [the provenance manifest](colorado_hms_provenance.json).
The ZIPs remain in the ignored `data/` directory rather than Git history.

## Download from NOAA

The downloader uses only Python's standard library:

```bash
python3 data_processing/download_hms_smoke.py --years 2024 2025
```

Use `--output-dir PATH` to choose another destination or `--years` to request
other annual bundles. Existing archives are checked and reused. New downloads
are checked for ZIP integrity and shapefile content before being saved.
NOAA can revise its archives; use the release and checksums above to restore
this exact snapshot.

NOAA sources: [annual bundles](https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS/Smoke_Polygons/Shapefile/Annual_Bundles/)
and [HMS product information](https://www.ospo.noaa.gov/products/land/hms.html).

## Analysis integration

The Utah smoke notebook expects separate daily shapefiles. These annual layers
still need a Colorado adapter that selects polygon dates and tests overlap with
the Rocky Flats North monitor or Jefferson County. Preserve missing-data states
and handle NOAA observation times and AQS local dates explicitly. This download
does not yet classify Colorado observations as smoke or no-smoke.
