"""
Extract per-parameter metadata from a raw HW air quality CSV.

The raw AQS-style files contain one measurement per row. This script summarizes
the metadata attached to each parameter so the output has one row per parameter
and one column per metadata item.

Example:
    python3 data_processing/extract_parameter_metadata.py \
        data/utah/data_up_to_2025/raw/HW_data_raw_2026-05-23.csv
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional


METADATA_COLUMNS = [
    "state_code",
    "county_code",
    "site_number",
    "parameter_code",
    "poc",
    "latitude",
    "longitude",
    "datum",
    "units_of_measure",
    "units_of_measure_code",
    "sample_duration",
    "sample_duration_code",
    "sample_frequency",
    "detection_limit",
    "method_type",
    "method",
    "method_code",
    "state",
    "county",
    "cbsa_code",
    "date_of_last_change",
]

DATE_COLUMNS = ["date_local", "date_gmt", "dt"]

OUTPUT_COLUMNS = [
    "parameter",
    "row_count",
    "non_null_measurement_count",
    "sample_measurement_min",
    "sample_measurement_max",
    "first_date_local",
    "last_date_local",
    "first_date_gmt",
    "last_date_gmt",
    "first_dt",
    "last_dt",
    *METADATA_COLUMNS,
    "qualifier_count",
    "qualifiers",
    "uncertainty_values",
]


@dataclass
class ParameterMetadata:
    row_count: int = 0
    non_null_measurement_count: int = 0
    sample_measurement_min: Optional[float] = None
    sample_measurement_max: Optional[float] = None
    metadata_values: Dict[str, set[str]] = field(
        default_factory=lambda: {column: set() for column in METADATA_COLUMNS}
    )
    qualifier_values: set[str] = field(default_factory=set)
    uncertainty_values: set[str] = field(default_factory=set)
    first_dates: Dict[str, str] = field(default_factory=dict)
    last_dates: Dict[str, str] = field(default_factory=dict)

    def add_row(self, row: dict[str, str]) -> None:
        self.row_count += 1

        measurement = row.get("sample_measurement", "").strip()
        if measurement:
            try:
                value = float(measurement)
            except ValueError:
                value = None
            if value is not None:
                self.non_null_measurement_count += 1
                self.sample_measurement_min = (
                    value
                    if self.sample_measurement_min is None
                    else min(self.sample_measurement_min, value)
                )
                self.sample_measurement_max = (
                    value
                    if self.sample_measurement_max is None
                    else max(self.sample_measurement_max, value)
                )

        for column in METADATA_COLUMNS:
            value = row.get(column, "").strip()
            if value:
                self.metadata_values[column].add(value)

        qualifier = row.get("qualifier", "").strip()
        if qualifier:
            self.qualifier_values.add(qualifier)

        uncertainty = row.get("uncertainty", "").strip()
        if uncertainty:
            self.uncertainty_values.add(uncertainty)

        for column in DATE_COLUMNS:
            value = row.get(column, "").strip()
            if value:
                current_first = self.first_dates.get(column)
                current_last = self.last_dates.get(column)
                if current_first is None or value < current_first:
                    self.first_dates[column] = value
                if current_last is None or value > current_last:
                    self.last_dates[column] = value


def collapse_values(values: Iterable[str], max_values: int) -> str:
    """Return a deterministic, readable representation of a set of values."""
    sorted_values = sorted(values)
    if len(sorted_values) <= max_values:
        return "; ".join(sorted_values)
    visible_values = sorted_values[:max_values]
    remaining = len(sorted_values) - max_values
    return "; ".join(visible_values + [f"... ({remaining} more)"])


def format_float(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{value:g}"


def extract_metadata(input_csv: Path) -> dict[str, ParameterMetadata]:
    summaries: dict[str, ParameterMetadata] = {}

    with input_csv.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError(f"Input CSV has no header row: {input_csv}")
        if "parameter" not in reader.fieldnames:
            raise ValueError("Input CSV must contain a 'parameter' column.")

        for row in reader:
            parameter = row.get("parameter", "").strip()
            if not parameter:
                continue
            summaries.setdefault(parameter, ParameterMetadata()).add_row(row)

    return summaries


def build_output_row(
    parameter: str,
    summary: ParameterMetadata,
    max_set_values: int,
) -> dict[str, str | int]:
    row: dict[str, str | int] = {
        "parameter": parameter,
        "row_count": summary.row_count,
        "non_null_measurement_count": summary.non_null_measurement_count,
        "sample_measurement_min": format_float(summary.sample_measurement_min),
        "sample_measurement_max": format_float(summary.sample_measurement_max),
        "first_date_local": summary.first_dates.get("date_local", ""),
        "last_date_local": summary.last_dates.get("date_local", ""),
        "first_date_gmt": summary.first_dates.get("date_gmt", ""),
        "last_date_gmt": summary.last_dates.get("date_gmt", ""),
        "first_dt": summary.first_dates.get("dt", ""),
        "last_dt": summary.last_dates.get("dt", ""),
        "qualifier_count": len(summary.qualifier_values),
        "qualifiers": collapse_values(summary.qualifier_values, max_set_values),
        "uncertainty_values": collapse_values(
            summary.uncertainty_values, max_set_values
        ),
    }

    for column in METADATA_COLUMNS:
        row[column] = collapse_values(summary.metadata_values[column], max_set_values)

    return row


def write_metadata_csv(
    summaries: dict[str, ParameterMetadata],
    output_csv: Path,
    max_set_values: int,
) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for parameter in sorted(summaries):
            writer.writerow(build_output_row(parameter, summaries[parameter], max_set_values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract one-row-per-parameter metadata from a raw HW data CSV."
    )
    parser.add_argument("input_csv", type=Path, help="Path to the raw HW data CSV.")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help=(
            "Path for the metadata CSV. Defaults to "
            "'<input stem>_parameter_metadata.csv' next to the input."
        ),
    )
    parser.add_argument(
        "--max-set-values",
        type=int,
        default=25,
        help="Maximum distinct values to write for set-like metadata columns.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_csv: Path = args.input_csv
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    output_csv = args.output_csv or input_csv.with_name(
        f"{input_csv.stem}_parameter_metadata.csv"
    )
    summaries = extract_metadata(input_csv)
    write_metadata_csv(summaries, output_csv, args.max_set_values)
    print(f"Wrote metadata for {len(summaries)} parameters to {output_csv}")


if __name__ == "__main__":
    main()
