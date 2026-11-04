"""Build the Rocky Flats North hourly table and coverage audit from frozen AQS files.

Run from the repository root:
    .venv/bin/python -m data_processing.colorado_hourly

No downloads, imputation, smoke classification, or meteorological filters are applied.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "data/colorado/aqs/080590006/raw"
SR_FACTOR = 41840 / 60  # NIST: 1 langley = 41840 J/m².
# A sensitivity screen, not an EPA invalidation rule. Estimates and MDL flags stay.
REVIEW_CODES = {"3", "5", "EH", "LB", "LK", "LL", "QX"}
CARBONYLS = {"43502", "43503"}
SOURCES = {
    "timestamps": "https://aqs.epa.gov/aqsweb/documents/about_aqs_data.html",
    "langley_conversion": "https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def markdown_table(frame):
    """Avoid requiring tabulate for the Markdown report."""
    def value(v):
        if pd.isna(v):
            return "—"
        if isinstance(v, (float, np.floating)):
            return f"{v:.2f}"
        return str(v).replace("|", "/")
    return "\n".join([
        "| " + " | ".join(map(str, frame.columns)) + " |",
        "| " + " | ".join("---" for _ in frame.columns) + " |",
        *["| " + " | ".join(value(v) for v in row) + " |"
          for row in frame.itertuples(index=False, name=None)],
    ])


def load_raw(raw_dir):
    selection = json.loads((raw_dir / "selection.json").read_text())
    manifest = json.loads((raw_dir / "manifest.json").read_text())
    sources, frames = [], []
    for chunk in manifest["chunks"]:
        path = raw_dir / chunk["filename"]
        digest = sha256(path)
        if digest != chunk["sha256"]:
            raise ValueError(f"Input hash mismatch: {path}")
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        if len(frame) != chunk["rows"]:
            raise ValueError(f"Input row count mismatch: {path}")
        frame["source_file"] = path.name
        frames.append(frame)
        sources.append({"filename": path.name, "sha256": digest, "rows": len(frame)})
    raw = pd.concat(frames, ignore_index=True)
    actual_site = raw.state_code + raw.county_code + raw.site_number
    if not actual_site.eq(selection["site"].replace("-", "")).all():
        raise ValueError("Multiple or unexpected sites in raw data")
    raw["dt_utc"] = pd.to_datetime(raw.date_gmt + " " + raw.time_gmt, utc=True)
    raw["dt"] = pd.to_datetime(raw.date_local + " " + raw.time_local)
    if not (raw.dt_utc.dt.tz_localize(None) - raw.dt).eq(pd.Timedelta(hours=7)).all():
        raise ValueError("Unexpected AQS UTC/local-standard-time offset")
    raw["value"] = pd.to_numeric(raw.sample_measurement, errors="coerce")
    malformed = raw.sample_measurement.ne("") & raw.value.isna()
    if malformed.any() or np.isinf(raw.value).any():
        raise ValueError("Nonempty nonnumeric or infinite measurement")
    raw["qualifier_code"] = raw.qualifier.str.split(" - ", n=1).str[0]
    raw["review"] = raw.qualifier_code.isin(REVIEW_CODES) & raw.value.notna()
    return raw, selection, sources


def build_table(raw, selection):
    hourly = raw.loc[raw.sample_duration.eq("1 HOUR")].copy()
    # Fail rather than silently averaging different POCs/methods or repeated records.
    if hourly.duplicated(["dt_utc", "parameter_code"]).any():
        raise ValueError("Duplicate hourly timestamp/parameter: explicit monitor selection required")
    species = {**selection["voc_parameters"], **selection["supplemental_organic_parameters"]}
    species = {k: v for k, v in species.items() if k not in {"43102", *CARBONYLS}}
    panel = sorted(species)
    base_panel = sorted(set(panel) - set(selection["supplemental_organic_parameters"]))
    expected_units = {code: "Parts per billion Carbon" for code in [*panel, "43102"]}
    expected_units.update({k: "Parts per billion" for k in ["42600", "42601", "42602", "42612"]})
    expected_units.update({"44201": "Parts per million", "63301": "Langleys/minute"})
    for code, group in hourly.groupby("parameter_code"):
        if code not in expected_units or not group.units_of_measure.eq(expected_units[code]).all():
            raise ValueError(f"Unexpected units or hourly parameter: {code}")
    years = sorted(selection["years"])
    index = pd.DatetimeIndex(np.concatenate([
        pd.date_range(f"{year}-01-01", f"{year+1}-01-01", freq="h", inclusive="left").values
        for year in years
    ]), name="dt")
    if not hourly.dt.isin(index).all():
        raise ValueError("Hourly records outside requested local-standard-time years")
    wide = hourly.pivot(index="dt", columns="parameter_code", values="value").reindex(index)
    wide = wide.reindex(columns=sorted(expected_units))
    flags = hourly.pivot(index="dt", columns="parameter_code", values="qualifier").reindex(index)
    flags = flags.reindex(columns=sorted(expected_units)).fillna("")
    review = hourly.pivot(index="dt", columns="parameter_code", values="review").reindex(index)
    review = review.reindex(columns=sorted(expected_units)).eq(True)
    table = pd.DataFrame(index=index)
    table["dt_utc"] = index.tz_localize(timezone(pd.Timedelta(hours=-7))).tz_convert("UTC")
    table["site_id"] = selection["site"]
    table["year"] = index.year
    table["month"] = index.month
    table["season"] = pd.Series(index.month, index=index).map({
        12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
        6: "summer", 7: "summer", 8: "summer", 9: "fall", 10: "fall", 11: "fall",
    })
    table["is_weekend"] = index.dayofweek >= 5
    for code, name in {"42601": "NO", "42602": "NO2", "42600": "NOy", "42612": "NOy_minus_NO"}.items():
        table[name] = wide[code]
    table["NOx"] = table.NO + table.NO2
    table["Ozone"] = wide["44201"] * 1000
    table["solar_radiation_langley_min"] = wide["63301"]
    table["solar_radiation_w_m2"] = wide["63301"] * SR_FACTOR
    table["total_nmoc_ppbc"] = wide["43102"]
    table["voc_species_expected"] = len(panel)
    table["voc_species_present"] = wide[panel].notna().sum(axis=1)
    table["voc_species_fraction"] = table.voc_species_present / len(panel)
    table["VOC_partial_ppbc"] = wide[panel].sum(axis=1, min_count=1)
    table["voc_complete"] = table.voc_species_present.eq(len(panel))
    table["voc_available"] = table.voc_species_present.gt(0)
    table["VOC"] = table.VOC_partial_ppbc
    table["VOC_complete_ppbc"] = table.VOC.where(table.voc_complete)
    table["VOC_base_panel_ppbc"] = wide[base_panel].sum(axis=1, min_count=len(base_panel))
    table["voc_review_species_count"] = review[panel].sum(axis=1)
    table["voc_qualified_species_count"] = (flags[panel].ne("") & wide[panel].notna()).sum(axis=1)
    for code, name in {"42601": "NO", "42602": "NO2", "44201": "Ozone", "63301": "solar_radiation"}.items():
        table[f"{name}_qualifier"] = flags[code]
    table["core_available"] = table[["VOC", "NOx", "Ozone"]].notna().all(axis=1)
    table["all_inputs_available"] = table.core_available & table.solar_radiation_w_m2.notna()
    table["complete_panel_all_inputs_available"] = table.all_inputs_available & table.voc_complete
    table["base_panel_all_inputs_available"] = table[[
        "VOC_base_panel_ppbc", "NOx", "Ozone", "solar_radiation_w_m2"
    ]].notna().all(axis=1)
    main_codes = [*panel, "42601", "42602", "44201", "63301"]
    table["any_review_qualifier"] = review[main_codes].any(axis=1)
    table["all_inputs_no_review"] = table.all_inputs_available & ~table.any_review_qualifier
    table["any_negative_core"] = table[["VOC", "NOx", "Ozone"]].lt(0).any(axis=1)
    table["negative_NO"] = table.NO.lt(0)
    table["all_inputs_nonnegative"] = table.all_inputs_available & ~table.any_negative_core
    # A conservative clock-based diagnostic, not a solar-position/daylight filter.
    table["deep_night_radiation_flag"] = ((index.hour >= 22) | (index.hour <= 3)) & table.solar_radiation_w_m2.gt(50)
    for code in panel:
        table[f"voc_{code}_ppbc"] = wide[code]
        table[f"voc_{code}_qualifier"] = flags[code]
    return table, panel, base_panel, species, hourly


def coverage(table, keys):
    rows = []
    for labels, group in table.groupby(keys, sort=True):
        labels = labels if isinstance(labels, tuple) else (labels,)
        row = dict(zip(keys, labels))
        row["expected_hours"] = len(group)
        row["hours_any_voc"] = int(group.voc_species_present.gt(0).sum())
        row["hours_voc_ge_90pct"] = int(group.voc_species_fraction.ge(.9).sum())
        row["hours_voc_complete"] = int(group.voc_complete.sum())
        row["hours_base_panel_complete"] = int(group.VOC_base_panel_ppbc.notna().sum())
        for col in ["NO", "NO2", "NOx", "Ozone", "solar_radiation_w_m2"]:
            row[f"hours_{col}"] = int(group[col].notna().sum())
        for col in ["core_available", "all_inputs_available", "complete_panel_all_inputs_available", "base_panel_all_inputs_available", "all_inputs_no_review", "all_inputs_nonnegative"]:
            row[f"hours_{col}"] = int(group[col].sum())
        row["hours_all_inputs_weekday"] = int((group.all_inputs_available & ~group.is_weekend).sum())
        row["hours_all_inputs_weekend"] = int((group.all_inputs_available & group.is_weekend).sum())
        row["days_all_inputs"] = int(group.loc[group.all_inputs_available].index.normalize().nunique())
        row["all_inputs_percent_calendar"] = row["hours_all_inputs_available"] / len(group) * 100
        rows.append(row)
    return pd.DataFrame(rows)


def write_outputs(raw_dir, output_dir):
    raw, selection, sources = load_raw(raw_dir)
    table, panel, base_panel, species, hourly = build_table(raw, selection)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "colorado_080590006_2024_2025"
    # Keep the full calendar in memory for unbiased coverage denominators, but
    # drop hours with no numeric VOC species from the delivered analysis table.
    table.loc[table.voc_available].to_csv(output_dir / f"{stem}_hourly.csv", float_format="%.10g")
    for name, keys in [("monthly", ["year", "month"]), ("yearly", ["year"]), ("seasonal", ["year", "season"])]:
        coverage(table, keys).to_csv(output_dir / f"coverage_{name}.csv", index=False)
    profiles = []
    for (year, code), group in raw.groupby([raw.dt.dt.year, "parameter_code"]):
        valid = group.loc[group.value.notna()]
        profiles.append({
            "year": year, "parameter_code": code, "parameter": group.parameter.iloc[0],
            "in_hourly_voc_panel": code in panel, "rows": len(group), "numeric_values": len(valid),
            "null_values": int(group.value.isna().sum()), "negative_values": int(group.value.lt(0).sum()),
            "qualified_numeric_values": int((group.value.notna() & group.qualifier.ne("")).sum()),
            "review_numeric_values": int(group.review.sum()),
            "first_record": group.dt.min(), "last_record": group.dt.max(),
            "first_numeric": valid.dt.min(), "last_numeric": valid.dt.max(),
            "units": ";".join(sorted(group.units_of_measure.unique())),
            "durations": ";".join(sorted(group.sample_duration.unique())),
            "pocs": ";".join(sorted(group.poc.unique())),
            "methods": ";".join(sorted(group.method_code.unique())),
        })
    profiles = pd.DataFrame(profiles)
    profiles.to_csv(output_dir / "parameter_coverage.csv", index=False)
    raw.groupby([raw.dt.dt.year.rename("year"), "parameter_code", "qualifier"], dropna=False).agg(
        rows=("value", "size"), numeric_values=("value", "count")
    ).reset_index().to_csv(output_dir / "qualifier_audit.csv", index=False)
    matched = hourly.loc[hourly.dt.isin(table.index[table.all_inputs_available])]
    main_codes = [*panel, "42601", "42602", "44201", "63301"]
    matched.loc[matched.parameter_code.isin(main_codes)].groupby([
        matched.dt.dt.year.rename("year"), "qualifier"
    ]).agg(rows=("value", "size"), numeric_values=("value", "count")).reset_index().to_csv(
        output_dir / "matched_input_qualifier_audit.csv", index=False
    )
    nonhourly = raw.loc[~raw.sample_duration.eq("1 HOUR")]
    nonhourly.to_csv(output_dir / "nonhourly_samples.csv", index=False)
    dictionary = []
    for code, name in sorted(species.items()):
        dictionary.append({"parameter_code": code, "parameter": name,
                           "value_column": f"voc_{code}_ppbc", "qualifier_column": f"voc_{code}_qualifier",
                           "units": "ppbC", "base_panel": code in base_panel})
    pd.DataFrame(dictionary).to_csv(output_dir / "voc_panel.csv", index=False)
    core = table.loc[table.all_inputs_available]
    checks = {
        "raw_records": len(raw), "hourly_records": len(hourly), "nonhourly_records": len(nonhourly),
        "calendar_hours": len(table), "duplicate_hourly_timestamp_parameter": int(hourly.duplicated(["dt_utc", "parameter_code"]).sum()),
        "duplicate_table_timestamps": int(table.index.duplicated().sum()),
        "any_voc_hours": int(table.voc_species_present.gt(0).sum()),
        "dropped_no_voc_hours": int((~table.voc_available).sum()),
        "complete_voc_hours": int(table.voc_complete.sum()), "all_inputs_hours": len(core),
        "complete_panel_all_inputs_hours": int(table.complete_panel_all_inputs_available.sum()),
        "all_inputs_no_review_hours": int(table.all_inputs_no_review.sum()),
        "negative_NO_hours": int(table.negative_NO.sum()), "negative_NOx_hours": int(table.NOx.lt(0).sum()),
        "negative_NOx_among_all_inputs": int(core.NOx.lt(0).sum()),
        "deep_night_radiation_flags": int(table.deep_night_radiation_flag.sum()),
        "max_solar_radiation_w_m2": float(table.solar_radiation_w_m2.max()),
    }
    # Reconciliation assertions guard the scientific meaning of the saved table.
    assert len(raw) == len(hourly) + len(nonhourly)
    assert table.index.is_unique and table.dt_utc.is_unique
    assert table.VOC.notna().equals(table.voc_available)
    assert table.VOC_complete_ppbc.notna().equals(table.voc_complete)
    assert table.NOx.notna().equals(table.NO.notna() & table.NO2.notna())
    assert core.voc_species_present.gt(0).all()
    yearly = coverage(table, ["year"])
    monthly = coverage(table, ["year", "month"])
    assert yearly.hours_all_inputs_available.sum() == len(core)
    assert monthly.expected_hours.sum() == len(table)
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "site": selection["site"],
        "years": selection["years"], "raw_dir": str(raw_dir.resolve()),
        "script_sha256": sha256(Path(__file__)), "selection_sha256": sha256(raw_dir / "selection.json"),
        "manifest_sha256": sha256(raw_dir / "manifest.json"),
        "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
        "voc_panel": {code: species[code] for code in panel}, "base_panel": base_panel,
        "voc_policy": {"minimum_numeric_species": 1, "zero_counts_as_observed": True,
                       "sum_observed_species_only": True, "drop_hours_with_no_numeric_species": True,
                       "coverage_denominator": "full requested local-standard-time calendar"},
        "review_qualifier_codes": sorted(REVIEW_CODES), "solar_conversion_factor": SR_FACTOR,
        "sources": SOURCES, "inputs": sources, "checks": checks,
    }
    (output_dir / "provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    write_report(output_dir, table, profiles, yearly, monthly, checks, panel, base_panel, stem)
    outputs = {p.name: sha256(p) for p in sorted(output_dir.iterdir())
               if p.is_file() and p.name != "SHA256SUMS.json"}
    (output_dir / "SHA256SUMS.json").write_text(json.dumps(outputs, indent=2) + "\n")
    print(json.dumps(checks, indent=2))
    print(f"Outputs: {output_dir}")


def write_report(out, table, profiles, yearly, monthly, checks, panel, base_panel, stem):
    summary_cols = ["year", "expected_hours", "hours_any_voc", "hours_voc_complete", "hours_all_inputs_available", "hours_all_inputs_no_review", "all_inputs_percent_calendar"]
    month_cols = ["year", "month", "hours_any_voc", "hours_voc_complete", "hours_all_inputs_available", "hours_all_inputs_weekday", "hours_all_inputs_weekend"]
    limiting = profiles.loc[profiles.in_hourly_voc_panel].sort_values(["year", "numeric_values"]).groupby("year").head(8)
    labels = {
        "year": "Year", "month": "Month", "expected_hours": "Calendar hours",
        "hours_any_voc": "Any VOC", "hours_voc_complete": "Complete VOC",
        "hours_all_inputs_available": "All inputs (any VOC coverage)",
        "hours_complete_panel_all_inputs_available": "All inputs (complete 59 species)",
        "hours_base_panel_all_inputs_available": "All inputs (complete 57 species)",
        "hours_all_inputs_no_review": "All inputs, no review flags",
        "all_inputs_percent_calendar": "All inputs / calendar (%)",
        "hours_all_inputs_weekday": "Matched weekday", "hours_all_inputs_weekend": "Matched weekend",
    }
    active = table.loc[table.voc_species_present.gt(0)]
    ranges = []
    for year, group in active.groupby("year"):
        ranges.append(f"- {year}: numeric VOC observations from {group.index.min()} through {group.index.max()} MST.")
    text = f"""# Colorado hourly data and coverage report

Rocky Flats North, AQS **08-059-0006**, requested local-standard-time years **2024–2025**.

The hourly analysis table retains **{checks['any_voc_hours']:,} hours** with at least one numeric VOC species, including reported zero. **{checks['dropped_no_voc_hours']:,} hours** with no numeric VOC species are dropped. **{checks['all_inputs_hours']:,} retained hours** also have matched NO + NO₂, ozone, and solar radiation. VOC is the sum of whichever individual species are observed in that hour; missing species are not imputed. These are availability counts, not a declaration that every row is ready for modeling. No radiation, smoke, season, weekend, or clearing-index filter has been applied.

## Coverage

All percentages below use every calendar hour in the indicated local-standard-time year (**{len(table):,} hours total**), including hours dropped from the analysis table. Days without scheduled or reported VOC measurements remain in that denominator. This is calendar coverage, not monitor compliance or scheduled-sample completeness.

{markdown_table(yearly[summary_cols].rename(columns=labels))}

### Monthly counts

{markdown_table(monthly[month_cols].rename(columns=labels))}

### Unequal temporal coverage

{chr(10).join(ranges)}

The two years do not have matching VOC observation periods. Compare shared months and report losses before pooling years or comparing seasonal surfaces. The first/last dates above do not imply uninterrupted measurements between them. Consult monthly counts and per-species coverage.

### Species-panel and quality-screen sensitivity

{markdown_table(yearly[['year', 'hours_all_inputs_available', 'hours_complete_panel_all_inputs_available', 'hours_base_panel_all_inputs_available', 'hours_all_inputs_no_review']].rename(columns=labels))}

The main selection now accepts any numeric VOC coverage. The complete 59-species and complete 57-species selections remain as sensitivity comparisons, not requirements for inclusion. The 57-species base panel excludes n-dodecane and 1-hexene. It is not a claim of an EPA-standard panel or a panel harmonized with Utah. Because the main sum can use different species in different hours, use species counts and individual columns when assessing concentration differences between partitions.

The provisional review screen leaves no matched 2024 hours. All matched 2024 hours have at least one LK or LL qualifier (possible high or low bias); these numeric values remain in the main table. Applying that screen without investigating the flags would remove an entire year. The 2025 matched inputs include LB (lab blank) and EH (above-range estimate) flags. `matched_input_qualifier_audit.csv` gives the counts for the main inputs on matched hours, while `qualifier_audit.csv` covers all raw rows. The report's no-review result is a sensitivity result, not the default modeling selection.

### VOC species with the fewest numeric measurements

{markdown_table(limiting[['year', 'parameter', 'numeric_values', 'null_values', 'first_numeric', 'last_numeric']])}

## Table definitions and quality findings

- `dt` is AQS sample begin time in fixed **MST (UTC−07:00)**, without daylight saving adjustment. `dt_utc` is timezone-aware UTC from the same hour. Every raw row was checked against the seven-hour offset. Do not localize `dt` directly as DST-observing `America/Denver`. [EPA timestamp documentation]({SOURCES['timestamps']}).
- `VOC` (ppbC) sums the available numeric values from the **{len(panel)}-species hourly panel**. At least one observed species is sufficient; a numeric zero counts as observed. If all species are missing, the sum is missing and the hour is dropped from the analysis table. `VOC_partial_ppbc` is retained as an alias of this observed-species sum. `VOC_complete_ppbc` holds a sum only when every species is observed. `voc_available`, `voc_complete`, `voc_species_present`, `voc_species_expected`, and `voc_species_fraction` expose availability and completeness. Individual NaNs remain NaN. No imputation, substitution at the detection limit, or zero-filling is used.
- `VOC_base_panel_ppbc` is a separately complete **{len(base_panel)}-species** sum excluding the two supplemental species, n-dodecane and 1-hexene. It is a sensitivity alternative and is not substituted into `VOC`. The explicit lists and names are in `voc_panel.csv`.
- **Total NMOC is excluded from every VOC sum** and retained separately as `total_nmoc_ppbc`. The **{checks['nonhourly_records']:,} eight-hour formaldehyde/acetaldehyde records** are exported to `nonhourly_samples.csv`; they are not assigned to individual hours or mixed into the hourly sum.
- `NOx = NO + NO2`, in ppb, only when both are numeric at the same hour. NOy and NOy−NO are retained separately and never substituted for NOx.
- `Ozone` is converted from ppm to ppb by multiplying by 1000. `solar_radiation_w_m2` equals source Langleys/minute × 41840/60 (**{SR_FACTOR:.9f}**). Source radiation is also retained. [NIST unit conversion]({SOURCES['langley_conversion']}).
- No duplicate hourly timestamp/parameter records were found (**{checks['duplicate_hourly_timestamp_parameter']}**). The builder fails on duplicates, unexpected units, inconsistent site identity, nonnumeric nonempty values, input hash changes, or time-offset changes. It never averages multiple POCs silently. `parameter_coverage.csv` records methods, POCs, units, and durations by year and parameter.
- Numeric measurements are preserved, and qualifiers for the main VOC/NOx/ozone/radiation inputs are retained alongside them. Estimated, below-MDL, biased, wildfire, and other qualified numeric values are not automatically discarded. `qualifier_audit.csv` distinguishes qualified numeric measurements from null rows. Per-species qualifiers accompany every VOC value in the table; the unchanged raw files retain every source field.
- `any_review_qualifier` marks numeric measurements with codes **{', '.join(sorted(REVIEW_CODES))}** among the inputs to the main table. `all_inputs_no_review` is a conservative sensitivity screen excluding those hours. This is an explicit local review policy, not an EPA validity determination. LJ, MD, SQ, IT, and XS remain eligible; inspect qualifier meanings before adopting a modeling exclusion policy.
- Across the full requested calendar, negative NO occurs in **{checks['negative_NO_hours']:,} hours**, and derived NOx is negative in **{checks['negative_NOx_hours']:,} hours** (**{checks['negative_NOx_among_all_inputs']:,} among matched available inputs**). Values are preserved without clipping. `negative_NO`, `any_negative_core`, and `all_inputs_nonnegative` expose this issue; availability alone does not resolve its scientific interpretation.
- Radiation reaches **{checks['max_solar_radiation_w_m2']:.1f} W/m²**. A conservative diagnostic flags radiation above 50 W/m² between 22:00–03:59 MST: **{checks['deep_night_radiation_flags']} hours**. This clock-based check is not a full solar-position validation or a daylight selection rule.

## Files and use

- `{stem}_hourly.csv`: hours with any numeric VOC coverage, main inputs, completeness and quality flags, individual VOC values and qualifiers. Other missing inputs remain missing; `all_inputs_available` identifies the subset with VOC, NOx, ozone, and radiation together.
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
"""
    (out / "coverage_report.md").write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    write_outputs(args.raw_dir, args.output_dir or args.raw_dir.parent / "processed")


if __name__ == "__main__":
    main()
