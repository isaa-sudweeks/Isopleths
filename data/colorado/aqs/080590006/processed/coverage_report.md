# Colorado hourly data and coverage report

Rocky Flats North, AQS **08-059-0006**, requested local-standard-time years **2024–2025**.

The hourly analysis table retains **6,003 hours** with at least one numeric VOC species, including reported zero. **11,541 hours** with no numeric VOC species are dropped. **5,045 retained hours** also have matched NO + NO₂, ozone, and solar radiation. VOC is the sum of whichever individual species are observed in that hour; missing species are not imputed. These are availability counts, not a declaration that every row is ready for modeling. No radiation, smoke, season, weekend, or clearing-index filter has been applied.

## Coverage

All percentages below use every calendar hour in the indicated local-standard-time year (**17,544 hours total**), including hours dropped from the analysis table. Days without scheduled or reported VOC measurements remain in that denominator. This is calendar coverage, not monitor compliance or scheduled-sample completeness.

| Year | Calendar hours | Any VOC | Complete VOC | All inputs (any VOC coverage) | All inputs, no review flags | All inputs / calendar (%) |
| --- | --- | --- | --- | --- | --- | --- |
| 2024 | 8784 | 2302 | 1780 | 1891 | 0 | 21.53 |
| 2025 | 8760 | 3701 | 1515 | 3154 | 2451 | 36.00 |

### Monthly counts

| Year | Month | Any VOC | Complete VOC | All inputs (any VOC coverage) | Matched weekday | Matched weekend |
| --- | --- | --- | --- | --- | --- | --- |
| 2024 | 1 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 2 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 3 | 522 | 0 | 466 | 312 | 154 |
| 2024 | 4 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 5 | 539 | 539 | 467 | 362 | 105 |
| 2024 | 6 | 626 | 626 | 472 | 310 | 162 |
| 2024 | 7 | 615 | 615 | 486 | 393 | 93 |
| 2024 | 8 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 9 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 10 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 11 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 12 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 1 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 2 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 3 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 4 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 5 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 6 | 600 | 0 | 478 | 363 | 115 |
| 2025 | 7 | 633 | 226 | 566 | 421 | 145 |
| 2025 | 8 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 9 | 591 | 14 | 521 | 373 | 148 |
| 2025 | 10 | 663 | 61 | 541 | 412 | 129 |
| 2025 | 11 | 630 | 630 | 569 | 384 | 185 |
| 2025 | 12 | 584 | 584 | 479 | 366 | 113 |

### Unequal temporal coverage

- 2024: numeric VOC observations from 2024-03-01 02:00:00 through 2024-07-31 23:00:00 MST.
- 2025: numeric VOC observations from 2025-06-01 00:00:00 through 2025-12-31 23:00:00 MST.

The two years do not have matching VOC observation periods. Compare shared months and report losses before pooling years or comparing seasonal surfaces. The first/last dates above do not imply uninterrupted measurements between them. Consult monthly counts and per-species coverage.

### Species-panel and quality-screen sensitivity

| Year | All inputs (any VOC coverage) | All inputs (complete 59 species) | All inputs (complete 57 species) | All inputs, no review flags |
| --- | --- | --- | --- | --- |
| 2024 | 1891 | 1425 | 1425 | 0 |
| 2025 | 3154 | 1322 | 2492 | 2451 |

The main selection now accepts any numeric VOC coverage. The complete 59-species and complete 57-species selections remain as sensitivity comparisons, not requirements for inclusion. The 57-species base panel excludes n-dodecane and 1-hexene. It is not a claim of an EPA-standard panel or a panel harmonized with Utah. Because the main sum can use different species in different hours, use species counts and individual columns when assessing concentration differences between partitions.

The provisional review screen leaves no matched 2024 hours. All matched 2024 hours have at least one LK or LL qualifier (possible high or low bias); these numeric values remain in the main table. Applying that screen without investigating the flags would remove an entire year. The 2025 matched inputs include LB (lab blank) and EH (above-range estimate) flags. `matched_input_qualifier_audit.csv` gives the counts for the main inputs on matched hours, while `qualifier_audit.csv` covers all raw rows. The report's no-review result is a sensitivity result, not the default modeling selection.

### VOC species with the fewest numeric measurements

| year | parameter | numeric_values | null_values | first_numeric | last_numeric |
| --- | --- | --- | --- | --- | --- |
| 2024 | n-Hexane | 1780 | 1172 | 2024-05-06 18:00:00 | 2024-07-31 23:00:00 |
| 2024 | n-Dodecane | 2302 | 650 | 2024-03-01 02:00:00 | 2024-07-31 23:00:00 |
| 2024 | Ethane | 2302 | 650 | 2024-03-01 02:00:00 | 2024-07-31 23:00:00 |
| 2024 | Ethylene | 2302 | 650 | 2024-03-01 02:00:00 | 2024-07-31 23:00:00 |
| 2024 | Propane | 2302 | 650 | 2024-03-01 02:00:00 | 2024-07-31 23:00:00 |
| 2024 | Propylene | 2302 | 650 | 2024-03-01 02:00:00 | 2024-07-31 23:00:00 |
| 2024 | Acetylene | 2302 | 650 | 2024-03-01 02:00:00 | 2024-07-31 23:00:00 |
| 2024 | n-Butane | 2302 | 650 | 2024-03-01 02:00:00 | 2024-07-31 23:00:00 |
| 2025 | n-Dodecane | 2115 | 2277 | 2025-06-01 00:00:00 | 2025-12-31 23:00:00 |
| 2025 | n-Hexane | 3100 | 1292 | 2025-07-01 02:00:00 | 2025-12-31 23:00:00 |
| 2025 | m/p Xylene | 3100 | 1292 | 2025-07-01 02:00:00 | 2025-12-31 23:00:00 |
| 2025 | m-Ethyltoluene | 3100 | 1292 | 2025-07-01 02:00:00 | 2025-12-31 23:00:00 |
| 2025 | Styrene | 3100 | 1292 | 2025-07-01 02:00:00 | 2025-12-31 23:00:00 |
| 2025 | 1,2,3-Trimethylbenzene | 3100 | 1292 | 2025-07-01 02:00:00 | 2025-12-31 23:00:00 |
| 2025 | 1-Hexene | 3101 | 1291 | 2025-07-01 02:00:00 | 2025-12-31 23:00:00 |
| 2025 | Acetylene | 3491 | 901 | 2025-06-01 00:00:00 | 2025-12-31 23:00:00 |

## Table definitions and quality findings

- `dt` is AQS sample begin time in fixed **MST (UTC−07:00)**, without daylight saving adjustment. `dt_utc` is timezone-aware UTC from the same hour. Every raw row was checked against the seven-hour offset. Do not localize `dt` directly as DST-observing `America/Denver`. [EPA timestamp documentation](https://aqs.epa.gov/aqsweb/documents/about_aqs_data.html).
- `VOC` (ppbC) sums the available numeric values from the **59-species hourly panel**. At least one observed species is sufficient; a numeric zero counts as observed. If all species are missing, the sum is missing and the hour is dropped from the analysis table. `VOC_partial_ppbc` is retained as an alias of this observed-species sum. `VOC_complete_ppbc` holds a sum only when every species is observed. `voc_available`, `voc_complete`, `voc_species_present`, `voc_species_expected`, and `voc_species_fraction` expose availability and completeness. Individual NaNs remain NaN. No imputation, substitution at the detection limit, or zero-filling is used.
- `VOC_base_panel_ppbc` is a separately complete **57-species** sum excluding the two supplemental species, n-dodecane and 1-hexene. It is a sensitivity alternative and is not substituted into `VOC`. The explicit lists and names are in `voc_panel.csv`.
- **Total NMOC is excluded from every VOC sum** and retained separately as `total_nmoc_ppbc`. The **368 eight-hour formaldehyde/acetaldehyde records** are exported to `nonhourly_samples.csv`; they are not assigned to individual hours or mixed into the hourly sum.
- `NOx = NO + NO2`, in ppb, only when both are numeric at the same hour. NOy and NOy−NO are retained separately and never substituted for NOx.
- `Ozone` is converted from ppm to ppb by multiplying by 1000. `solar_radiation_w_m2` equals source Langleys/minute × 41840/60 (**697.333333333**). Source radiation is also retained. [NIST unit conversion](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8).
- No duplicate hourly timestamp/parameter records were found (**0**). The builder fails on duplicates, unexpected units, inconsistent site identity, nonnumeric nonempty values, input hash changes, or time-offset changes. It never averages multiple POCs silently. `parameter_coverage.csv` records methods, POCs, units, and durations by year and parameter.
- Numeric measurements are preserved, and qualifiers for the main VOC/NOx/ozone/radiation inputs are retained alongside them. Estimated, below-MDL, biased, wildfire, and other qualified numeric values are not automatically discarded. `qualifier_audit.csv` distinguishes qualified numeric measurements from null rows. Per-species qualifiers accompany every VOC value in the table; the unchanged raw files retain every source field.
- `any_review_qualifier` marks numeric measurements with codes **3, 5, EH, LB, LK, LL, QX** among the inputs to the main table. `all_inputs_no_review` is a conservative sensitivity screen excluding those hours. This is an explicit local review policy, not an EPA validity determination. LJ, MD, SQ, IT, and XS remain eligible; inspect qualifier meanings before adopting a modeling exclusion policy.
- Across the full requested calendar, negative NO occurs in **7,575 hours**, and derived NOx is negative in **98 hours** (**9 among matched available inputs**). Values are preserved without clipping. `negative_NO`, `any_negative_core`, and `all_inputs_nonnegative` expose this issue; availability alone does not resolve its scientific interpretation.
- Radiation reaches **1101.8 W/m²**. A conservative diagnostic flags radiation above 50 W/m² between 22:00–03:59 MST: **0 hours**. This clock-based check is not a full solar-position validation or a daylight selection rule.

## Files and use

- `colorado_080590006_2024_2025_hourly.csv`: hours with any numeric VOC coverage, main inputs, completeness and quality flags, individual VOC values and qualifiers. Other missing inputs remain missing; `all_inputs_available` identifies the subset with VOC, NOx, ozone, and radiation together.
- `coverage_monthly.csv`, `coverage_yearly.csv`, `coverage_seasonal.csv`: availability counts, matched-day counts, weekday/weekend counts, and calendar denominators. Winter is grouped by calendar year, not a December-to-February winter season-year.
- `parameter_coverage.csv`, `qualifier_audit.csv`, `matched_input_qualifier_audit.csv`, `voc_panel.csv`, `nonhourly_samples.csv`: supporting audit tables.
- `provenance.json`, `SHA256SUMS.json`: raw source hashes, transformations, versions, validation counts, and output hashes.

For the next filtering step, start with `all_inputs_available == True`, review the quality sensitivity flags, and decide the Colorado radiation and smoke rules. Do not treat missing HMS classification as non-smoke. Do not use the Utah clearing-index defaults for this site.

## Reproduce

From the repository root:

```bash
.venv/bin/python -m data_processing.colorado_hourly
```

Raw inputs are read from `data/colorado/aqs/080590006/raw/`, checked against the frozen download manifest, and preserved unchanged. Outputs are written to `data/colorado/aqs/080590006/processed/`. Optional `--raw-dir` and `--output-dir` arguments support separate rebuilds. The script runs reconciliation assertions on table keys, missingness, NOx derivation, and coverage totals. Raw snapshots are the evidence for this report; no fresh measurements were downloaded.
