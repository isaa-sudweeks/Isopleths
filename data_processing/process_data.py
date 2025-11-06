"""
Utilities for aggregating hourly air quality data into VOC, NOx, and Ozone summaries.

The script expects CSV files with at least the following columns:
- ``dt``: timestamp of the measurement
- ``parameter``: pollutant name
- ``sample_measurement``: numeric value

Example usage:
    python -m data_processing.process_data data/utah/raw_data/HW_data.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd

# Parameters excluded from the VOC sum to avoid double counting aggregated metrics.
EXCLUDED_PARAMETERS = {
    "Ozone",
    "Oxides of nitrogen (NOx)",
    "Nitric oxide (NO)",
    "Nitrogen dioxide (NO2)",
    "PM2.5 - Local Conditions",
    "Sum of PAMS target compounds",
    "Total NMOC (non-methane organic compound)",
}

SEASON_MONTHS: Dict[str, Iterable[int]] = {
    "winter": (12, 1, 2),
    "spring": (3, 4, 5),
    "summer": (6, 7, 8),
    "fall": (9, 10, 11),
}


def load_measurements(path: Path) -> pd.DataFrame:
    """Read the raw CSV and reshape it into a wide dataframe keyed by timestamp."""
    df = pd.read_csv(
        path,
        usecols=["dt", "parameter", "sample_measurement"],
        parse_dates=["dt"],
    )
    df["sample_measurement"] = pd.to_numeric(df["sample_measurement"], errors="coerce")
    df = df.dropna(subset=["dt"])

    pivot = (
        df.groupby(["dt", "parameter"])["sample_measurement"]
        .mean()
        .unstack()
    )
    pivot.sort_index(inplace=True)
    return pivot


def aggregate_voc_nox_ozone(pivot: pd.DataFrame) -> pd.DataFrame:
    """Create a dataframe containing summed VOC alongside NOx and Ozone columns."""
    result = pd.DataFrame(index=pivot.index)

    voc_columns = [col for col in pivot.columns if col not in EXCLUDED_PARAMETERS]
    if voc_columns:
        result["VOC"] = pivot[voc_columns].sum(axis=1, min_count=1)
    else:
        result["VOC"] = pd.Series(index=pivot.index, dtype=float)

    result["NOx"] = pivot.get(
        "Oxides of nitrogen (NOx)", pd.Series(index=pivot.index, dtype=float)
    )
    ozone = pivot.get("Ozone", pd.Series(index=pivot.index, dtype=float))
    # Convert ozone measurements from ppm to ppb (EPA convention for raw files).
    result["Ozone"] = ozone * 1000

    result.index = pd.to_datetime(result.index)
    result.index.name = "dt"
    result.sort_index(inplace=True)

    result = result[result["VOC"].notna()]
    result = result[result["VOC"] > 0]
    return result[["VOC", "NOx", "Ozone"]]


def split_by_season(data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Return copies of the input dataframe filtered for each season."""
    seasonal: Dict[str, pd.DataFrame] = {}
    months = data.index.month
    for season, season_months in SEASON_MONTHS.items():
        seasonal_df = data.loc[months.isin(season_months)].copy()
        seasonal_df.index.name = "dt"
        seasonal[season] = seasonal_df
    return seasonal


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Persist the dataframe to CSV with the datetime index."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=True)


def aggregate_file(input_path: Path, output_dir: Path) -> Dict[str, Path]:
    """Aggregate the provided file and write overall and seasonal CSVs."""
    pivot = load_measurements(input_path)
    summary = aggregate_voc_nox_ozone(pivot)

    if summary.empty:
        raise ValueError(f"No VOC data available after aggregation for {input_path}")

    basename = input_path.stem
    outputs: Dict[str, Path] = {}

    all_path = output_dir / f"{basename}_all.csv"
    write_csv(summary, all_path)
    outputs["all"] = all_path

    for season, frame in split_by_season(summary).items():
        season_path = output_dir / f"{basename}_{season}.csv"
        write_csv(frame, season_path)
        outputs[season] = season_path

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate raw air quality data.")
    parser.add_argument("input_csv", type=Path, help="Path to the raw HW data CSV.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the aggregated CSVs (defaults to the input directory).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path: Path = args.input_csv
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    output_dir: Path = args.output_dir or input_path.parent
    aggregate_file(input_path, output_dir)


if __name__ == "__main__":
    main()
