"""
Compare canister-measured VOCs against hourly VOCs on matched sample windows.

The default input is the Utah raw HW dataset:

    data/utah/raw_data/HW_data.csv

For each canister sample window, this script:
- sums the canister VOC parameters measured in that window
- sums all hourly VOC parameters at each hour inside the same window
- averages those hourly sums over canister-duration windows with enough
  usable hourly VOC records
  - an hourly VOC record is usable when at least one individual VOC has a
    measured value; missing individual VOCs in that hour are treated as zero
- reports the canister VOC share of total VOCs split by sample duration

AQS sample timestamps are sample begin times. The comparison therefore treats
the canister ``dt`` value as the window start unless explicitly overridden.

The script also writes matched-window outputs so the underlying 8-hour and
24-hour canister records can be audited, including a wide file with one column
per hourly VOC parameter averaged over each canister sample window and one
prefixed column per canister VOC parameter measured in that window.

Example:
    python -m data_processing.canister_analysis.canister_voc_comparison
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd


DEFAULT_INPUT = Path("/Users/isaacsudweeks/Desktop/Work/Improved_Isopleths/data/utah/data_up_to_2025/raw/HW_data_raw_2026-05-23.csv")
DEFAULT_OUTPUT_DIR = Path("/Users/isaacsudweeks/Desktop/Work/Improved_Isopleths/data/utah/data_up_to_2025/new_canister_breakout_2026_06_23")
DEFAULT_MIN_HOUR_COVERAGE = 0.875
OZONE_PARAMETER = "Ozone"
OZONE_OUTPUT_COLUMN = "Ozone"
SUPPLEMENTAL_HOURLY_PARAMETERS = {
    OZONE_PARAMETER: OZONE_OUTPUT_COLUMN,
    "Oxides of nitrogen (NOx)": "NOx",
    "Nitric oxide (NO)": "NO",
    "Nitrogen dioxide (NO2)": "NO2",
}

# Parameters that should not be counted as individual VOCs in the comparison.
EXCLUDED_PARAMETERS = {
    OZONE_PARAMETER,
    "Oxides of nitrogen (NOx)",
    "Nitric oxide (NO)",
    "Nitrogen dioxide (NO2)",
    "PM2.5 - Local Conditions",
    "Sum of PAMS target compounds",
    "Total NMOC (non-methane organic compound)",
}

SAMPLE_DURATION_GROUPS = {
    8.0: "summer_8_hour",
    24.0: "non_summer_24_hour",
}

SEASON_MONTHS: Dict[str, Iterable[int]] = {
    "winter": (12, 1, 2),
    "spring": (3, 4, 5),
    "summer": (6, 7, 8),
    "fall": (9, 10, 11),
}


def parse_duration_hours(value: object) -> float:
    """Convert AQS sample_duration values such as '1 HOUR' or '24 HOUR' to hours."""
    text = str(value).strip().upper()
    if not text or text == "NAN":
        return float("nan")

    parts = text.replace("-", " ").split()
    for part in parts:
        try:
            return float(part)
        except ValueError:
            continue
    return float("nan")


def normalize_text_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def load_raw_data(path: Path) -> pd.DataFrame:
    """Load only the columns needed for the canister comparison."""
    cols = [
        "parameter",
        "dt",
        "sample_measurement",
        "units_of_measure",
        "sample_duration",
        "sample_frequency",
    ]
    data = pd.read_csv(path, usecols=cols, parse_dates=["dt"])
    data["sample_measurement"] = pd.to_numeric(
        data["sample_measurement"], errors="coerce"
    )
    data["parameter"] = normalize_text_series(data["parameter"])
    data["units_of_measure"] = normalize_text_series(data["units_of_measure"])
    data["sample_duration"] = normalize_text_series(data["sample_duration"])
    data["sample_frequency"] = normalize_text_series(data["sample_frequency"])
    data["duration_hours"] = data["sample_duration"].map(parse_duration_hours)
    return data.dropna(subset=["dt"])


def voc_mask(data: pd.DataFrame, excluded_parameters: Iterable[str]) -> pd.Series:
    """Return rows that are VOC-like individual measurements in ppbC units."""
    excluded = set(excluded_parameters)
    return (
        data["units_of_measure"].str.casefold().eq("parts per billion carbon")
        & ~data["parameter"].isin(excluded)
    )


def build_hourly_voc(data: pd.DataFrame) -> pd.DataFrame:
    """Sum individual hourly VOC parameters at each timestamp.

    If an hour has at least one measured VOC, missing VOC measurements within
    that hour are interpreted as zero. Hours where every VOC measurement is
    missing are excluded so matched windows can still be dropped for no hourly
    VOC data.
    """
    hourly = data[
        voc_mask(data, EXCLUDED_PARAMETERS)
        & data["sample_duration"].str.upper().eq("1 HOUR")
    ].copy()
    hourly["usable_hour"] = hourly.groupby("dt")["sample_measurement"].transform(
        lambda x: x.notna().any()
    )
    hourly = hourly[hourly["usable_hour"]].copy()
    hourly["sample_measurement_filled"] = hourly["sample_measurement"].fillna(0)

    hourly_voc = (
        hourly.groupby("dt", as_index=True)
        .agg(
            hourly_voc=("sample_measurement_filled", "sum"),
            hourly_parameter_count=("parameter", "nunique"),
            hourly_measurement_count=("sample_measurement", "count"),
        )
        .sort_index()
    )
    hourly_voc.index = pd.to_datetime(hourly_voc.index)
    return hourly_voc


def build_hourly_voc_by_parameter(data: pd.DataFrame) -> pd.DataFrame:
    """Build hourly VOC measurements with one column per individual parameter."""
    hourly = data[
        voc_mask(data, EXCLUDED_PARAMETERS)
        & data["sample_duration"].str.upper().eq("1 HOUR")
    ].copy()
    hourly["usable_hour"] = hourly.groupby("dt")["sample_measurement"].transform(
        lambda x: x.notna().any()
    )
    hourly = hourly[hourly["usable_hour"]].copy()
    hourly["sample_measurement_filled"] = hourly["sample_measurement"].fillna(0)

    hourly_by_parameter = (
        hourly.groupby(["dt", "parameter"], as_index=False)["sample_measurement_filled"]
        .sum()
        .pivot(index="dt", columns="parameter", values="sample_measurement_filled")
        .sort_index()
    )
    hourly_by_parameter.index = pd.to_datetime(hourly_by_parameter.index)
    hourly_by_parameter.columns.name = None
    return hourly_by_parameter


def build_hourly_supplemental_parameters(data: pd.DataFrame) -> pd.DataFrame:
    """Build output-only hourly Ozone and NOx species measurements in ppb."""
    hourly = data[
        data["parameter"].isin(SUPPLEMENTAL_HOURLY_PARAMETERS)
        & data["sample_duration"].str.upper().eq("1 HOUR")
    ].copy()
    hourly = hourly.dropna(subset=["sample_measurement"])
    if hourly.empty:
        return pd.DataFrame(
            index=pd.DatetimeIndex([]),
            columns=SUPPLEMENTAL_HOURLY_PARAMETERS.values(),
            dtype=float,
        )

    unit = hourly["units_of_measure"].str.casefold()
    hourly["supplemental_ppb"] = hourly["sample_measurement"].where(
        ~unit.eq("parts per million"),
        hourly["sample_measurement"] * 1000,
    )
    hourly["output_parameter"] = hourly["parameter"].map(SUPPLEMENTAL_HOURLY_PARAMETERS)

    supplemental = (
        hourly.groupby(["dt", "output_parameter"])["supplemental_ppb"]
        .mean()
        .unstack()
        .sort_index()
    )
    supplemental.index = pd.to_datetime(supplemental.index)
    supplemental.columns.name = None
    return supplemental.reindex(columns=SUPPLEMENTAL_HOURLY_PARAMETERS.values())


def build_canister_events(
    data: pd.DataFrame, canister_timestamp: str = "start"
) -> pd.DataFrame:
    """Sum canister VOC parameters by matching timestamp and sample duration.

    Missing individual canister VOC measurements are interpreted as zero when
    at least one VOC in that canister group was measured. Groups where all
    canister VOC measurements are missing retain ``NA`` totals and are dropped
    from valid summaries by the existing result filters.
    """
    canister = data[
        voc_mask(data, EXCLUDED_PARAMETERS)
        & ~data["sample_duration"].str.upper().eq("1 HOUR")
        & data["duration_hours"].notna()
    ].copy()
    group_cols = ["dt", "sample_duration", "duration_hours"]
    canister["usable_canister_group"] = canister.groupby(group_cols)[
        "sample_measurement"
    ].transform(lambda x: x.notna().any())
    canister["sample_measurement_filled"] = canister["sample_measurement"].fillna(0)

    events = (
        canister.groupby(group_cols, as_index=False)
        .agg(
            canister_voc=("sample_measurement_filled", "sum"),
            canister_has_measurement=("usable_canister_group", "any"),
            canister_parameter_count=("parameter", "nunique"),
            canister_measurement_count=("sample_measurement", "count"),
            canister_parameters=("parameter", lambda x: "; ".join(sorted(set(x)))),
            sample_frequency=("sample_frequency", lambda x: "; ".join(sorted(set(x)))),
        )
        .sort_values(["dt", "duration_hours"])
    )
    events.loc[~events["canister_has_measurement"], "canister_voc"] = pd.NA
    canister_dt = pd.to_datetime(events["dt"])
    duration = pd.to_timedelta(events["duration_hours"], unit="h")
    if canister_timestamp == "start":
        events["window_start"] = canister_dt
        events["window_end"] = canister_dt + duration
    elif canister_timestamp == "end":
        events["window_start"] = canister_dt - duration
        events["window_end"] = canister_dt
    else:
        raise ValueError("canister_timestamp must be 'start' or 'end'")
    events["comparison_group"] = events["duration_hours"].map(
        lambda hours: SAMPLE_DURATION_GROUPS.get(float(hours), f"{hours:g}_hour")
    )
    events["canister_timestamp"] = canister_timestamp
    events["canister_sample_day"] = canister_dt.dt.date
    return events


def build_canister_voc_by_parameter(data: pd.DataFrame) -> pd.DataFrame:
    """Build canister VOC measurements with one prefixed column per parameter."""
    canister = data[
        voc_mask(data, EXCLUDED_PARAMETERS)
        & ~data["sample_duration"].str.upper().eq("1 HOUR")
        & data["duration_hours"].notna()
    ].copy()
    group_cols = ["dt", "sample_duration", "duration_hours"]
    canister["usable_canister_group"] = canister.groupby(group_cols)[
        "sample_measurement"
    ].transform(lambda x: x.notna().any())
    canister = canister[canister["usable_canister_group"]].copy()
    if canister.empty:
        return pd.DataFrame(columns=group_cols)
    canister["sample_measurement_filled"] = canister["sample_measurement"].fillna(0)

    canister_by_parameter = (
        canister.groupby([*group_cols, "parameter"], as_index=False)[
            "sample_measurement_filled"
        ]
        .sum()
        .pivot(
            index=group_cols,
            columns="parameter",
            values="sample_measurement_filled",
        )
        .sort_index()
        .reset_index()
    )
    canister_by_parameter.columns.name = None
    return canister_by_parameter.rename(
        columns={
            column: f"canister_{column}"
            for column in canister_by_parameter.columns
            if column not in group_cols
        }
    )


def attach_hourly_window_averages(
    events: pd.DataFrame,
    hourly_voc: pd.DataFrame,
    min_hour_coverage: float,
) -> pd.DataFrame:
    """Attach averaged hourly VOC values for each canister sample window."""
    rows = []
    for event in events.itertuples(index=False):
        window = hourly_voc.loc[
            (hourly_voc.index >= event.window_start)
            & (hourly_voc.index < event.window_end)
        ]
        expected_hours = max(int(round(float(event.duration_hours))), 1)
        min_hours = math.ceil(expected_hours * min_hour_coverage)
        usable = len(window) >= min_hours
        canister_usable = pd.notna(event.canister_voc)

        hourly_sum = window["hourly_voc"].sum() if usable else pd.NA
        hourly_divisor = len(window) if usable else pd.NA
        hourly_average = hourly_sum / hourly_divisor if usable else pd.NA
        total_voc = (
            event.canister_voc + hourly_average
            if usable and canister_usable
            else pd.NA
        )
        rows.append(
            {
                "window_start": event.window_start,
                "window_end": event.window_end,
                "canister_timestamp": event.canister_timestamp,
                "canister_sample_day": event.canister_sample_day,
                "comparison_group": event.comparison_group,
                "sample_duration": event.sample_duration,
                "duration_hours": event.duration_hours,
                "sample_frequency": event.sample_frequency,
                "canister_voc": event.canister_voc,
                "hourly_voc_sum": hourly_sum,
                "hourly_averaging_divisor_hours": hourly_divisor,
                "hourly_voc_average": hourly_average,
                "total_voc": total_voc,
                "canister_percent_of_total": (
                    event.canister_voc / total_voc * 100
                    if pd.notna(total_voc) and total_voc > 0
                    else pd.NA
                ),
                "hourly_hours_found": len(window),
                "hourly_hours_expected": expected_hours,
                "hourly_min_hours_required": min_hours,
                "canister_parameter_count": event.canister_parameter_count,
                "canister_measurement_count": event.canister_measurement_count,
                "canister_parameters": event.canister_parameters,
            }
        )

    return pd.DataFrame(rows)


def build_canister_days(events: pd.DataFrame) -> pd.DataFrame:
    """Combine canister windows into one duration-weighted row per sample day."""
    day_windows = (
        events.assign(sample_day=events["canister_sample_day"])
        .groupby("sample_day", as_index=False)
        .agg(
            window_start=("window_start", "min"),
            window_end=("window_end", "max"),
            canister_timestamp=("canister_timestamp", lambda x: "; ".join(sorted(set(x)))),
            sample_duration=("sample_duration", lambda x: "; ".join(sorted(set(x)))),
            sample_frequency=("sample_frequency", lambda x: "; ".join(sorted(set(x)))),
            canister_parameters=(
                "canister_parameters",
                lambda x: "; ".join(sorted(set("; ".join(x).split("; ")))),
            ),
        )
    )
    day_windows["duration_hours"] = (
        day_windows["window_end"] - day_windows["window_start"]
    ).dt.total_seconds() / 3600
    return day_windows


def build_daily_canister_values(data: pd.DataFrame) -> pd.DataFrame:
    """Compute duration-weighted daily canister VOC totals by parameter."""
    canister = data[
        voc_mask(data, EXCLUDED_PARAMETERS)
        & ~data["sample_duration"].str.upper().eq("1 HOUR")
        & data["duration_hours"].notna()
    ].copy()
    group_cols = ["dt", "sample_duration", "duration_hours"]
    canister["usable_canister_group"] = canister.groupby(group_cols)[
        "sample_measurement"
    ].transform(lambda x: x.notna().any())
    canister = canister[canister["usable_canister_group"]].copy()
    canister["sample_measurement_filled"] = canister["sample_measurement"].fillna(0)
    canister["sample_day"] = canister["dt"].dt.date
    canister["weighted_measurement"] = (
        canister["sample_measurement_filled"] * canister["duration_hours"]
    )

    by_parameter = (
        canister.groupby(["sample_day", "parameter"], as_index=False)
        .agg(
            weighted_measurement=("weighted_measurement", "sum"),
            covered_hours=("duration_hours", "sum"),
        )
    )
    by_parameter["daily_parameter_average"] = (
        by_parameter["weighted_measurement"] / by_parameter["covered_hours"]
    )

    daily = (
        by_parameter.groupby("sample_day", as_index=False)
        .agg(
            canister_voc=("daily_parameter_average", "sum"),
            canister_parameter_count=("parameter", "nunique"),
            canister_measurement_count=("covered_hours", "count"),
            canister_parameters=("parameter", lambda x: "; ".join(sorted(set(x)))),
        )
        .sort_values("sample_day")
    )
    return daily


def attach_hourly_day_averages(
    day_windows: pd.DataFrame,
    daily_canister: pd.DataFrame,
    hourly_voc: pd.DataFrame,
    min_hour_coverage: float,
) -> pd.DataFrame:
    """Attach averaged hourly VOC values to each canister sample day."""
    rows = []
    daily_lookup = daily_canister.set_index("sample_day")
    for day in day_windows.itertuples(index=False):
        window = hourly_voc.loc[
            (hourly_voc.index >= day.window_start) & (hourly_voc.index < day.window_end)
        ]
        expected_hours = max(int(round(float(day.duration_hours))), 1)
        min_hours = math.ceil(expected_hours * min_hour_coverage)
        usable = len(window) >= min_hours
        canister = (
            daily_lookup.loc[day.sample_day]
            if day.sample_day in daily_lookup.index
            else pd.Series(
                {
                    "canister_voc": pd.NA,
                    "canister_parameter_count": pd.NA,
                    "canister_measurement_count": pd.NA,
                    "canister_parameters": day.canister_parameters,
                }
            )
        )
        canister_usable = pd.notna(canister["canister_voc"])
        hourly_divisor = len(window) if usable else pd.NA
        hourly_average = window["hourly_voc"].sum() / hourly_divisor if usable else pd.NA
        total_voc = (
            canister["canister_voc"] + hourly_average
            if usable and canister_usable
            else pd.NA
        )

        rows.append(
            {
                "sample_day": day.sample_day,
                "window_start": day.window_start,
                "window_end": day.window_end,
                "canister_timestamp": day.canister_timestamp,
                "sample_duration": day.sample_duration,
                "duration_hours": day.duration_hours,
                "sample_frequency": day.sample_frequency,
                "canister_voc": canister["canister_voc"],
                "hourly_averaging_divisor_hours": hourly_divisor,
                "hourly_voc_average": hourly_average,
                "total_voc": total_voc,
                "canister_percent_of_total": (
                    canister["canister_voc"] / total_voc * 100
                    if pd.notna(total_voc) and total_voc > 0
                    else pd.NA
                ),
                "hourly_hours_found": len(window),
                "hourly_hours_expected": expected_hours,
                "hourly_min_hours_required": min_hours,
                "canister_parameter_count": canister["canister_parameter_count"],
                "canister_measurement_count": canister["canister_measurement_count"],
                "canister_parameters": canister["canister_parameters"],
            }
        )
    return pd.DataFrame(rows)


def build_matched_day_parameter_averages(
    day_windows: pd.DataFrame,
    hourly_by_parameter: pd.DataFrame,
    hourly_supplemental: pd.DataFrame,
    min_hour_coverage: float,
) -> pd.DataFrame:
    """Average each hourly VOC parameter over canister-matched sample days."""
    rows = []
    parameter_columns = list(hourly_by_parameter.columns)
    supplemental_columns = list(hourly_supplemental.columns)

    for day in day_windows.itertuples(index=False):
        window = hourly_by_parameter.loc[
            (hourly_by_parameter.index >= day.window_start)
            & (hourly_by_parameter.index < day.window_end)
        ]
        supplemental_window = hourly_supplemental.loc[
            (hourly_supplemental.index >= day.window_start)
            & (hourly_supplemental.index < day.window_end)
        ]
        expected_hours = max(int(round(float(day.duration_hours))), 1)
        min_hours = math.ceil(expected_hours * min_hour_coverage)
        hourly_hours_found = len(window)
        supplemental_hours_found = supplemental_window.count()

        row = {
            "sample_day": day.sample_day,
            "window_start": day.window_start,
            "window_end": day.window_end,
            "canister_timestamp": day.canister_timestamp,
            "sample_duration": day.sample_duration,
            "duration_hours": day.duration_hours,
            "sample_frequency": day.sample_frequency,
            "hourly_hours_found": hourly_hours_found,
            "hourly_hours_expected": expected_hours,
            "hourly_min_hours_required": min_hours,
        }
        row.update(
            {
                f"{column}_hours_found": supplemental_hours_found.get(column, 0)
                for column in supplemental_columns
            }
        )

        if hourly_hours_found >= min_hours:
            parameter_averages = (
                window[parameter_columns].fillna(0).sum() / hourly_hours_found
            )
        else:
            parameter_averages = pd.Series(pd.NA, index=parameter_columns)
        row.update(parameter_averages.to_dict())
        for column in supplemental_columns:
            row[column] = (
                supplemental_window[column].mean()
                if supplemental_hours_found.get(column, 0) >= min_hours
                else pd.NA
            )
        rows.append(row)

    return pd.DataFrame(rows)


def build_matched_window_parameter_averages(
    events: pd.DataFrame,
    hourly_by_parameter: pd.DataFrame,
    hourly_supplemental: pd.DataFrame,
    canister_by_parameter: pd.DataFrame,
    min_hour_coverage: float,
) -> pd.DataFrame:
    """Average hourly VOCs and attach canister VOC values for each sample window."""
    rows = []
    parameter_columns = list(hourly_by_parameter.columns)
    supplemental_columns = list(hourly_supplemental.columns)
    canister_group_cols = ["dt", "sample_duration", "duration_hours"]
    canister_parameter_columns = [
        column
        for column in canister_by_parameter.columns
        if column not in canister_group_cols
    ]
    canister_lookup = canister_by_parameter.set_index(canister_group_cols)

    for event in events.itertuples(index=False):
        window = hourly_by_parameter.loc[
            (hourly_by_parameter.index >= event.window_start)
            & (hourly_by_parameter.index < event.window_end)
        ]
        supplemental_window = hourly_supplemental.loc[
            (hourly_supplemental.index >= event.window_start)
            & (hourly_supplemental.index < event.window_end)
        ]
        expected_hours = max(int(round(float(event.duration_hours))), 1)
        min_hours = math.ceil(expected_hours * min_hour_coverage)
        hourly_hours_found = len(window)
        supplemental_hours_found = supplemental_window.count()

        row = {
            "window_start": event.window_start,
            "window_end": event.window_end,
            "canister_timestamp": event.canister_timestamp,
            "canister_sample_day": event.canister_sample_day,
            "comparison_group": event.comparison_group,
            "sample_duration": event.sample_duration,
            "duration_hours": event.duration_hours,
            "sample_frequency": event.sample_frequency,
            "canister_voc": event.canister_voc,
            "hourly_hours_found": hourly_hours_found,
            "hourly_hours_expected": expected_hours,
            "hourly_min_hours_required": min_hours,
            "canister_parameter_count": event.canister_parameter_count,
            "canister_measurement_count": event.canister_measurement_count,
            "canister_parameters": event.canister_parameters,
        }
        row.update(
            {
                f"{column}_hours_found": supplemental_hours_found.get(column, 0)
                for column in supplemental_columns
            }
        )
        canister_key = (event.dt, event.sample_duration, event.duration_hours)
        if canister_key in canister_lookup.index:
            row.update(canister_lookup.loc[canister_key, canister_parameter_columns])
        else:
            row.update({column: pd.NA for column in canister_parameter_columns})

        if hourly_hours_found >= min_hours:
            parameter_averages = (
                window[parameter_columns].fillna(0).sum() / hourly_hours_found
            )
        else:
            parameter_averages = pd.Series(pd.NA, index=parameter_columns)
        row.update(parameter_averages.to_dict())
        for column in supplemental_columns:
            row[column] = (
                supplemental_window[column].mean()
                if supplemental_hours_found.get(column, 0) >= min_hours
                else pd.NA
            )
        rows.append(row)

    return pd.DataFrame(rows)


def split_by_season(data: pd.DataFrame, date_column: str) -> Dict[str, pd.DataFrame]:
    """Return copies of the input dataframe filtered for each season."""
    dated = pd.to_datetime(data[date_column])
    seasonal: Dict[str, pd.DataFrame] = {}
    for season, season_months in SEASON_MONTHS.items():
        seasonal[season] = data.loc[dated.dt.month.isin(season_months)].copy()
    return seasonal


def write_seasonal_csvs(
    data: pd.DataFrame,
    output_dir: Path,
    basename: str,
    date_column: str,
) -> Dict[str, Path]:
    """Write month-based seasonal CSVs using the process_data.py season groups."""
    outputs: Dict[str, Path] = {}
    for season, frame in split_by_season(data, date_column).items():
        season_path = output_dir / f"{basename}_{season}.csv"
        frame.to_csv(season_path, index=False)
        outputs[season] = season_path
    return outputs


def filter_hourly_matched_rows(results: pd.DataFrame) -> pd.DataFrame:
    """Return rows with enough hourly VOC records for the requested coverage."""
    return results.loc[
        results["hourly_hours_found"] >= results["hourly_min_hours_required"]
    ].copy()


def filter_valid_matched_rows(results: pd.DataFrame) -> pd.DataFrame:
    """Return matched rows that are usable for canister/hourly comparisons."""
    return filter_hourly_matched_rows(results).dropna(subset=["canister_voc"]).copy()


def summarize_results(event_results: pd.DataFrame, unit_name: str) -> pd.DataFrame:
    """Build a compact summary table for the matched comparison."""
    valid = event_results.dropna(subset=["hourly_voc_average", "canister_voc"]).copy()
    canister_mean = valid["canister_voc"].mean()
    hourly_mean = valid["hourly_voc_average"].mean()
    mean_total = canister_mean + hourly_mean
    percent_from_means = (
        canister_mean / mean_total * 100
        if len(valid) and pd.notna(mean_total) and mean_total > 0
        else pd.NA
    )

    return pd.DataFrame(
        [
            {
                f"matched_{unit_name}": len(valid),
                f"dropped_{unit_name}": len(event_results) - len(valid),
                "mean_canister_voc": canister_mean,
                "mean_hourly_voc_average": hourly_mean,
                "mean_total_voc": mean_total,
                "canister_percent_of_total_from_means": percent_from_means,
                "mean_of_window_percentages": valid[
                    "canister_percent_of_total"
                ].mean(),
            }
        ]
    )


def summarize_by_comparison_group(event_results: pd.DataFrame) -> pd.DataFrame:
    """Summarize the window-level comparison separately for 8-hour and 24-hour samples."""
    rows = []
    for group_name, group in event_results.groupby("comparison_group", sort=True):
        valid = group.dropna(subset=["hourly_voc_average", "canister_voc"]).copy()
        canister_mean = valid["canister_voc"].mean()
        hourly_mean = valid["hourly_voc_average"].mean()
        mean_total = canister_mean + hourly_mean
        valid_divisors = valid["hourly_averaging_divisor_hours"].dropna().unique()
        rows.append(
            {
                "comparison_group": group_name,
                "sample_duration": "; ".join(sorted(group["sample_duration"].unique())),
                "duration_hours": "; ".join(
                    str(int(hours)) for hours in sorted(group["duration_hours"].unique())
                ),
                "matched_windows": len(valid),
                "dropped_windows": len(group) - len(valid),
                "mean_canister_voc": canister_mean,
                "mean_hourly_voc_average": hourly_mean,
                "mean_total_voc": mean_total,
                "canister_percent_of_total_from_means": (
                    canister_mean / mean_total * 100
                    if len(valid) and pd.notna(mean_total) and mean_total > 0
                    else pd.NA
                ),
                "mean_of_window_percentages": valid[
                    "canister_percent_of_total"
                ].mean(),
                "hourly_averaging_divisor_hours": "; ".join(
                    str(int(hours))
                    for hours in sorted(valid_divisors)
                ),
            }
        )
    return pd.DataFrame(rows)


def write_parameter_summary(data: pd.DataFrame, output_path: Path) -> None:
    canister = data[
        voc_mask(data, EXCLUDED_PARAMETERS)
        & ~data["sample_duration"].str.upper().eq("1 HOUR")
    ].copy()
    summary = (
        canister.groupby("parameter", as_index=False)
        .agg(
            sample_duration=("sample_duration", lambda x: "; ".join(sorted(set(x)))),
            sample_frequency=("sample_frequency", lambda x: "; ".join(sorted(set(x)))),
            record_count=("parameter", "size"),
            measurement_count=("sample_measurement", "count"),
            measurement_mean=("sample_measurement", "mean"),
        )
        .sort_values("parameter")
    )
    summary.to_csv(output_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate canister VOC percent of total VOCs using matched hourly windows."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Raw AQS-style input CSV. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for output CSVs. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--min-hour-coverage",
        type=float,
        default=DEFAULT_MIN_HOUR_COVERAGE,
        help=(
            "Minimum fraction of expected hourly timestamps required in a canister "
            f"window. Default: {DEFAULT_MIN_HOUR_COVERAGE}."
        ),
    )
    parser.add_argument(
        "--canister-timestamp",
        choices=["start", "end"],
        default="start",
        help=(
            "Interpret the canister dt as the sample window start or end. "
            "AQS raw sample timestamps are begin times, so the default is start."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {args.input_csv}")
    if not 0 < args.min_hour_coverage <= 1:
        raise ValueError("--min-hour-coverage must be greater than 0 and no more than 1")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = load_raw_data(args.input_csv)
    hourly_voc = build_hourly_voc(data)
    hourly_by_parameter = build_hourly_voc_by_parameter(data)
    hourly_supplemental = build_hourly_supplemental_parameters(data)
    canister_events = build_canister_events(data, args.canister_timestamp)
    if canister_events.empty:
        raise ValueError("No non-hourly VOC canister-style measurements found.")
    canister_by_parameter = build_canister_voc_by_parameter(data)

    event_results = attach_hourly_window_averages(
        canister_events, hourly_voc, args.min_hour_coverage
    )
    window_parameter_results = build_matched_window_parameter_averages(
        canister_events,
        hourly_by_parameter,
        hourly_supplemental,
        canister_by_parameter,
        args.min_hour_coverage,
    )
    day_windows = build_canister_days(canister_events)
    daily_canister = build_daily_canister_values(data)
    day_results = attach_hourly_day_averages(
        day_windows, daily_canister, hourly_voc, args.min_hour_coverage
    )
    day_parameter_results = build_matched_day_parameter_averages(
        day_windows, hourly_by_parameter, hourly_supplemental, args.min_hour_coverage
    )
    summary = summarize_results(day_results, "days")
    window_summary = summarize_results(event_results, "windows")
    duration_summary = summarize_by_comparison_group(event_results)
    valid_event_results = filter_valid_matched_rows(event_results)
    valid_window_parameter_results = filter_valid_matched_rows(window_parameter_results)
    valid_day_results = filter_valid_matched_rows(day_results)
    valid_day_parameter_results = filter_hourly_matched_rows(day_parameter_results)

    event_path = args.output_dir / "canister_voc_matched_windows.csv"
    window_parameter_path = args.output_dir / "canister_voc_matched_windows_by_voc.csv"
    day_path = args.output_dir / "canister_voc_matched_days.csv"
    day_parameter_path = args.output_dir / "canister_voc_matched_days_by_voc.csv"
    summary_path = args.output_dir / "canister_voc_summary.csv"
    window_summary_path = args.output_dir / "canister_voc_window_summary.csv"
    duration_summary_path = args.output_dir / "canister_voc_by_duration_summary.csv"
    parameter_path = args.output_dir / "canister_voc_parameters.csv"

    valid_event_results.to_csv(event_path, index=False)
    valid_window_parameter_results.to_csv(window_parameter_path, index=False)
    seasonal_window_parameter_paths = write_seasonal_csvs(
        valid_window_parameter_results,
        args.output_dir,
        "canister_voc_matched_windows_by_voc",
        "canister_sample_day",
    )
    valid_day_results.to_csv(day_path, index=False)
    valid_day_parameter_results.to_csv(day_parameter_path, index=False)
    summary.to_csv(summary_path, index=False)
    window_summary.to_csv(window_summary_path, index=False)
    duration_summary.to_csv(duration_summary_path, index=False)
    write_parameter_summary(data, parameter_path)

    print(f"Input: {args.input_csv}")
    print(f"Canister timestamp interpreted as: {args.canister_timestamp}")
    for row in duration_summary.itertuples(index=False):
        percent = (
            f"{row.canister_percent_of_total_from_means:.3f}% canister VOC"
            if pd.notna(row.canister_percent_of_total_from_means)
            else "no valid matched windows"
        )
        print(
            f"{row.comparison_group}: "
            f"{int(row.matched_windows)} matched windows, "
            f"{int(row.dropped_windows)} dropped, "
            f"{percent}"
        )
        if pd.notna(row.mean_canister_voc):
            print(
                "  "
                f"mean canister={row.mean_canister_voc:.6g}, "
                f"mean hourly average={row.mean_hourly_voc_average:.6g}, "
                f"hourly divisor={row.hourly_averaging_divisor_hours}"
            )
    print(f"Wrote: {day_path}")
    print(f"Wrote: {day_parameter_path}")
    print(f"Wrote: {event_path}")
    print(f"Wrote: {window_parameter_path}")
    for season_path in seasonal_window_parameter_paths.values():
        print(f"Wrote: {season_path}")
    print(f"Wrote: {duration_summary_path}")
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {window_summary_path}")
    print(f"Wrote: {parameter_path}")


if __name__ == "__main__":
    main()
