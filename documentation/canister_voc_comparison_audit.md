# Canister VOC Comparison Audit

This audit covers `data_processing/canister_analysis/canister_voc_comparison.py` and the HW raw
data file:

`data/utah/data_up_to_2025/raw/HW_data_raw_2026-05-23.csv`

## Comparison basis

The fair comparison is restricted to matched sample windows. Canister samples
are collected every third day, so unsampled days are not filled or treated as
zero canister VOC.

AQS sample timestamps are begin times according to EPA's AQS documentation.
EPA's About AQS page says the timestamp on sample data is always the sample
begin time, and the AQS Data Dictionary says sample begin time plus sample
duration indicates the end time. For a canister row with `dt = T` and
`sample_duration = 8 HOUR`, the matched hourly window is `[T, T + 8 hours)`.
For `sample_duration = 24 HOUR`, the matched hourly window is
`[T, T + 24 hours)`.

The canister contribution is computed on the same average-concentration basis
as the hourly VOC total:

`canister_percent = canister_voc / (canister_voc + hourly_voc_average) * 100`

where:

`hourly_voc_average = sum(hourly_voc inside matched window) / hourly_hours_found`

The current default requires 100% of expected hourly timestamps in a window.
That means 8-hour canister windows require 8 hourly VOC records, and 24-hour
canister windows require 24 hourly VOC records. This avoids treating missing
hourly data as zero concentration or estimating across gaps.

## Parameters included

The canister-only contribution consists of four DNPH/HPLC carbonyl parameters:

- Acetaldehyde
- Acetone
- Formaldehyde
- Methyl ethyl ketone

The hourly denominator consists of the hourly `Parts per billion Carbon`
individual VOC parameters, excluding aggregate or non-VOC parameters listed in
`EXCLUDED_PARAMETERS`.

## Checked results

Using the AQS begin-time interpretation and 100% hourly coverage:

| Group | Matched windows | Dropped windows | Canister % from means | Mean of window % |
|---|---:|---:|---:|---:|
| 8-hour summer canister windows | 203 | 451 | 29.141% | 31.079% |
| 24-hour winter canister windows | 0 | 570 | N/A | N/A |

Day-level combined result:

| Matched days | Dropped days | Canister % from means | Mean of day/window % |
|---:|---:|---:|---:|
| 1 | 786 | 33.814% | 33.814% |

The window-level summary is the primary result for duration-specific canister
contribution. The day-level summary combines all non-hourly canister windows on
a sample day into a single day/window, so the strict 100% hourly coverage rule
leaves only one valid day.

## Validation checks

The script was rerun with the project virtual environment:

`./.venv/bin/python -m data_processing.canister_analysis.canister_voc_comparison`

Local checks found:

- No duplicate hourly `dt + parameter` VOC groups, so hourly VOC summing does
  not double-count repeated rows.
- No duplicate canister `dt + sample_duration + parameter` VOC groups, so the
  canister sum is one value per canister analyte per window.
- Non-hourly ppbC canister rows are only the four DNPH/HPLC carbonyl
  parameters listed above.
- The 24-hour group has 570 windows, but the best hourly coverage is 23 of 24
  hours, so no 24-hour window passes the default 100% coverage threshold.

## Sensitivity checks

Interpreting canister timestamps as end times does not match AQS timestamp
semantics and should not be used for the primary result.

Requiring 100% hourly timestamp coverage leaves no matched 24-hour winter
windows in this dataset. The 24-hour window closest to complete coverage has
23 of 24 hourly VOC records.

The script now reports zero-match duration groups explicitly instead of omitting
them from `canister_voc_by_duration_summary.csv`.
