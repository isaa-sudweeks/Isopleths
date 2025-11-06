# Clearing Index Data Workflow

## Why the AFOS archive
- The live `api.weather.gov/gridpoints/...` forecast only covers ~7 days, so historic observations never find a match.
- The Iowa Environmental Mesonet AFOS archive (`https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil=SMFSLC`) stores every Salt Lake Smoke Management Forecast (SMF), giving decades of clearing-index tables in plain text.
- AFOS requests accept start/end timestamps, so the notebook can pull exactly the window that matches the local dataset without brittle PDF parsing.

## Request window and buffering
1. The notebook localizes your observation timestamps to `America/Denver` using `ZoneInfo` and takes the min/max dates.
2. `REQUEST_BUFFER_DAYS` adds a cushion on both ends so the fetch still covers the most recent SMF issuance even if the product lagged a day.
3. The buffered range is converted to UTC and passed as `sdate`/`edate` parameters with `limit=9999` and `order=asc` to the AFOS API, keeping payloads reasonable while guaranteeing coverage.

## Parsing the AFOS response
- AFOS returns concatenated text products separated by control characters (`\x01`, `\x03`). The helper strips those, splits the text, and processes each product individually.
- The issuance timestamp (e.g., `206 AM MST Thu Nov 6 2025`) is parsed via a regex tolerant of mixed-case tokens and localized to the configured timezone.
- Each `...AIR SHED n...` block is scanned for `Clearing Index` lines underneath headings like `TODAY`, `TOMORROW`, or explicit weekdays. Headings are normalized and converted to real calendar dates relative to the issue time (weekday names roll forward to the next occurrence, `TOMORROW` adds one day, etc.).
- Parsed records carry `air_shed`, `valid_date`, `period_label`, `issue_time_local`, and the numeric clearing index (with `1000+` coerced to `1000`).

## Daily consolidation and targeting
- Multiple SMFs can exist per day, so the helper sorts by `(air_shed, valid_date, issue_time)` and keeps only the latest issuance per day.
- A lookup table lets the config accept either a numeric air shed id or its descriptive name (e.g., `"Northern Wasatch Front"` → `5`). Only rows for that shed move forward, preventing unrelated sheds from contaminating the merge.

## Merging with the dataset
1. Observation timestamps are floored to daily dates (`ci_valid_date`) and merged with the clearing-index table on that date. Hour-level precision isn’t possible because SMFs publish day-level values, so every hour of the same day inherits the same clearing index.
2. After the join, the notebook counts missing clearing-index rows and prints a warning if any dates fell outside the archive window or lacked data for the target shed.
3. Rows with `clearing_index < CLEARING_INDEX_THRESHOLD` are filtered out, and the surviving records are written to `OUTPUT_DATA_PATH`.

## Design justification
- **Archive selection:** AFOS delivers structured text with uniform formatting, unlike the DAQ PDFs. It is scriptable via URL parameters and contains the same numbers shown on weather.gov.
- **Python-only stack:** Using `requests`, `pandas`, and `ZoneInfo` keeps the workflow aligned with the repo’s existing dependencies (see `requirements.txt`) and avoids heavier PDF/HTML parsers.
- **Explicit timezone handling:** Converting both observations and SMF issue times through `ZoneInfo` avoids silent DST errors, which matter because the clearing index is defined per local day.
- **Buffered window:** Without the buffer, SMF issuances that occur the evening before (or after) your observations could be missed; padding the request ensures continuity while keeping downloads small.
- **Latest-issuance preference:** Operators usually refer to the latest SMF; taking the most recent issuance per day mirrors how the DAQ site presents the data and prevents stale forecasts from overwriting newer guidance.
