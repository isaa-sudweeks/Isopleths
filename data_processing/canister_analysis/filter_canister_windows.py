"""Filter canister VOC windows by solar radiation and clearing index.

Solar radiation follows ``Filter_Isopleth_By_SR.ipynb``: a window passes when
at least one observation in ``[window_start, window_end)`` is at or above the
threshold. Clearing index follows ``Filter_By_Clearing_Index.ipynb``: values at
or below the threshold pass, so a window is excluded when any date touched by
the window has a value above the threshold.

By default, every CSV directly inside the canister window directory is read and
SR-only, CI-only, and combined outputs are written under
``canister_exp/canister_analysis_filtered``.

Example:
    python -m data_processing.canister_analysis.filter_canister_windows
"""

from __future__ import annotations

import argparse
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = (
    PROJECT_ROOT
    / "data/utah/data_up_to_2025/canister_exp/canister_voc_windows"
)
DEFAULT_SR_PATH = PROJECT_ROOT / "data/SR_Data/SR_Data_HW.csv"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/utah/data_up_to_2025/canister_exp/canister_analysis_filtered"
)
DEFAULT_SR_THRESHOLD = 710.0
DEFAULT_CI_THRESHOLD = 1000
DEFAULT_AIRSHED = "Northern Wasatch Front"
DEFAULT_TIMEZONE = "America/Denver"
REQUEST_BUFFER_DAYS = 2

IEM_AFOS_ENDPOINT = "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py"
SMF_PIL = "SMFSLC"
REQUEST_HEADERS = {"User-Agent": "Improved-Isopleths-canister-window-filter"}

AIRSHED_LOOKUP: Dict[int, str] = {
    1: "Northwest Desert",
    2: "Southwest Desert",
    3: "Virgin River",
    4: "Cache",
    5: "Northern Wasatch Front",
    6: "Wasatch Back",
    7: "Northern Slopes",
    8: "Southern Wasatch Front",
    9: "Uinta Basin",
    10: "San Pete River",
    11: "Book Cliffs",
    12: "Upper Colorado River",
    13: "Sevier River",
    14: "Lower Colorado River",
    15: "San Juan River",
    16: "Areas Above 6500 feet",
}

SAME_DAY_LABELS = {
    "TODAY",
    "TONIGHT",
    "THIS MORNING",
    "THIS AFTERNOON",
    "THIS EVENING",
    "REST OF TONIGHT",
}
NEXT_DAY_LABELS = {"TOMORROW", "TOMORROW NIGHT"}
WEEKDAY_TO_INT = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}
ISSUE_LINE_PATTERN = re.compile(
    r"\d{3,4}\s+[AP]M\s+[A-Za-z]{3}\s+[A-Za-z]{3}\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{4}",
    re.IGNORECASE,
)
AIRSHED_BLOCK_PATTERN = re.compile(
    r"\.\.\.AIR SHED\s+(\d+)\.\.\.[\s\S]*?(?=(?:\.\.\.AIR SHED|\$\$))",
    re.MULTILINE,
)


def resolve_air_shed_id(target: int | str) -> int:
    """Resolve either an air-shed number or its forecast name."""
    try:
        numeric_target = int(target)
    except (TypeError, ValueError):
        numeric_target = None
    if numeric_target in AIRSHED_LOOKUP:
        return numeric_target

    cleaned = str(target).strip().casefold()
    for air_id, name in AIRSHED_LOOKUP.items():
        if name.casefold() == cleaned:
            return air_id
    raise ValueError(f"Unknown air shed: {target}")


def fetch_smoke_management_text(start: datetime, end: datetime) -> str:
    """Fetch archived Salt Lake City smoke-management forecasts."""
    response = requests.get(
        IEM_AFOS_ENDPOINT,
        params={
            "pil": SMF_PIL,
            "fmt": "text",
            "sdate": start.strftime("%Y-%m-%dT%H:%MZ"),
            "edate": end.strftime("%Y-%m-%dT%H:%MZ"),
            "limit": 9999,
            "order": "asc",
        },
        headers=REQUEST_HEADERS,
        timeout=60,
    )
    response.raise_for_status()
    return "" if "NO PRODUCTS FOUND" in response.text.upper() else response.text


def split_products(raw_text: str) -> Iterable[str]:
    for chunk in raw_text.split("\x03"):
        cleaned = chunk.lstrip("\x01\n\r").strip()
        if cleaned:
            yield cleaned


def parse_issue_time(product_text: str, timezone: str) -> datetime:
    for line in product_text.splitlines():
        match = ISSUE_LINE_PATTERN.search(line)
        if match:
            parts = match.group(0).split()
            issue_naive = datetime.strptime(
                f"{' '.join(parts[3:])} {parts[0]} {parts[1]}",
                "%a %b %d %Y %I%M %p",
            )
            return issue_naive.replace(tzinfo=ZoneInfo(timezone))
    raise ValueError("Unable to parse issue time for smoke-management product")


def normalize_period_label(label: str) -> str:
    return re.sub(r"[^A-Z ]", "", label.upper()).strip()


def resolve_valid_date(issue_dt: datetime, label: str) -> Optional[date]:
    normalized = normalize_period_label(label)
    if normalized in SAME_DAY_LABELS:
        offset = 0
    elif normalized in NEXT_DAY_LABELS:
        offset = 1
    else:
        target_weekday = next(
            (WEEKDAY_TO_INT[word] for word in normalized.split() if word in WEEKDAY_TO_INT),
            None,
        )
        if target_weekday is None:
            return None
        offset = (target_weekday - issue_dt.weekday()) % 7 or 7
    return (issue_dt + timedelta(days=offset)).date()


def parse_product(product_text: str, timezone: str) -> List[Dict[str, object]]:
    issue_time = parse_issue_time(product_text, timezone)
    records: List[Dict[str, object]] = []
    for match in AIRSHED_BLOCK_PATTERN.finditer(product_text):
        period_label: Optional[str] = None
        for line in match.group(0).splitlines():
            stripped = line.strip()
            if stripped.endswith("..."):
                period_label = stripped.rstrip(".").strip()
            elif stripped.startswith("Clearing Index") and period_label:
                value_text = stripped.split()[-1].replace("+", "").strip()
                valid_date = resolve_valid_date(issue_time, period_label)
                if value_text.isdigit() and valid_date is not None:
                    records.append(
                        {
                            "air_shed": int(match.group(1)),
                            "issue_time_local": issue_time,
                            "valid_date": valid_date,
                            "period_label": period_label,
                            "clearing_index": int(value_text),
                        }
                    )
    return records


def build_clearing_index_history(
    start: datetime, end: datetime, timezone: str
) -> pd.DataFrame:
    """Return the latest issued clearing index for each air shed and valid date."""
    raw_text = fetch_smoke_management_text(start, end)
    entries: List[Dict[str, object]] = []
    for product in split_products(raw_text):
        try:
            entries.extend(parse_product(product, timezone))
        except ValueError:
            continue
    if not entries:
        return pd.DataFrame(
            columns=[
                "air_shed",
                "issue_time_local",
                "valid_date",
                "period_label",
                "clearing_index",
            ]
        )
    history = pd.DataFrame(entries).sort_values(
        ["air_shed", "valid_date", "issue_time_local"]
    )
    return (
        history.groupby(["air_shed", "valid_date"], as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )


def load_windows(paths: List[Path]) -> Dict[Path, pd.DataFrame]:
    """Load window files and validate their half-open time intervals."""
    loaded: Dict[Path, pd.DataFrame] = {}
    for path in paths:
        frame = pd.read_csv(path)
        missing = {"window_start", "window_end"} - set(frame.columns)
        if missing:
            raise KeyError(f"{path} is missing columns: {', '.join(sorted(missing))}")
        frame["window_start"] = pd.to_datetime(frame["window_start"], errors="coerce")
        frame["window_end"] = pd.to_datetime(frame["window_end"], errors="coerce")
        invalid = (
            frame["window_start"].isna()
            | frame["window_end"].isna()
            | frame["window_end"].le(frame["window_start"])
        )
        if invalid.any():
            raise ValueError(f"{path} has {int(invalid.sum())} invalid window intervals")
        loaded[path] = frame
    return loaded


def load_solar_radiation(path: Path) -> pd.Series:
    """Load the notebook-format hourly SR file as a datetime-indexed series."""
    sr = pd.read_csv(path, index_col=0, parse_dates=True)
    if "solar_radiation_w_m2" not in sr.columns:
        raise KeyError(f"solar_radiation_w_m2 was not found in {path}")
    values = pd.to_numeric(sr["solar_radiation_w_m2"], errors="coerce").dropna()
    values.index = pd.to_datetime(values.index)
    return values.sort_index()


def dates_in_window(start: pd.Timestamp, end: pd.Timestamp) -> List[date]:
    """List local calendar dates touched by a half-open window."""
    last_instant = end - pd.Timedelta(nanoseconds=1)
    return list(pd.date_range(start.normalize(), last_instant.normalize(), freq="D").date)


def attach_filter_audit(
    windows: pd.DataFrame,
    sr: pd.Series,
    ci_by_date: pd.Series,
    sr_threshold: float,
    ci_threshold: int,
) -> pd.DataFrame:
    """Attach SR/CI window statistics and pass flags without averaging."""
    rows = []
    for window in windows.itertuples(index=False):
        sr_values = sr.loc[(sr.index >= window.window_start) & (sr.index < window.window_end)]
        window_dates = dates_in_window(window.window_start, window.window_end)
        ci_values = ci_by_date.reindex(window_dates)

        sr_max = sr_values.max() if not sr_values.empty else pd.NA
        sr_pass = bool(not sr_values.empty and sr_values.ge(sr_threshold).any())
        ci_complete = bool(ci_values.notna().all())
        ci_exceeded = bool(ci_values.dropna().gt(ci_threshold).any())
        ci_pass = ci_complete and not ci_exceeded
        rows.append(
            {
                "sr_observations_in_window": len(sr_values),
                "sr_max_w_m2": sr_max,
                "sr_threshold_w_m2": sr_threshold,
                "sr_threshold_reached": sr_pass,
                "ci_dates_in_window": len(window_dates),
                "ci_dates_found": int(ci_values.notna().sum()),
                "ci_min": ci_values.min() if ci_values.notna().any() else pd.NA,
                "ci_max": ci_values.max() if ci_values.notna().any() else pd.NA,
                "ci_threshold": ci_threshold,
                "ci_threshold_exceeded": ci_exceeded,
                "sr_filter_pass": sr_pass,
                "ci_filter_pass": ci_pass,
                "sr_ci_filter_pass": sr_pass and ci_pass,
            }
        )
    return pd.concat([windows.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def get_ci_history(
    windows: Dict[Path, pd.DataFrame],
    cache_path: Path,
    timezone: str,
    refresh: bool,
) -> pd.DataFrame:
    """Load cached CI history or fetch enough history for all input windows."""
    if cache_path.exists() and not refresh:
        history = pd.read_csv(
            cache_path, parse_dates=["issue_time_local", "valid_date"]
        )
        history["valid_date"] = history["valid_date"].dt.date
        return history

    earliest = min(frame["window_start"].min() for frame in windows.values())
    latest = max(frame["window_end"].max() for frame in windows.values())
    local_zone = ZoneInfo(timezone)
    start_local = earliest.to_pydatetime().replace(tzinfo=local_zone) - timedelta(
        days=REQUEST_BUFFER_DAYS
    )
    end_local = latest.to_pydatetime().replace(tzinfo=local_zone) + timedelta(
        days=REQUEST_BUFFER_DAYS
    )
    history = build_clearing_index_history(
        start_local.astimezone(ZoneInfo("UTC")),
        end_local.astimezone(ZoneInfo("UTC")),
        timezone,
    )
    if history.empty:
        raise RuntimeError("No clearing-index records were returned")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(cache_path, index=False)
    return history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--input-glob", default="*.csv")
    parser.add_argument("--sr-path", type=Path, default=DEFAULT_SR_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sr-threshold", type=float, default=DEFAULT_SR_THRESHOLD)
    parser.add_argument("--ci-threshold", type=int, default=DEFAULT_CI_THRESHOLD)
    parser.add_argument("--air-shed", default=DEFAULT_AIRSHED)
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument(
        "--ci-cache",
        type=Path,
        default=None,
        help="Clearing-index history CSV; defaults inside --output-dir.",
    )
    parser.add_argument(
        "--refresh-ci",
        action="store_true",
        help="Fetch clearing-index history even when the cache exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = sorted(args.input_dir.glob(args.input_glob))
    if not paths:
        raise FileNotFoundError(f"No files matched {args.input_dir / args.input_glob}")
    if not args.sr_path.exists():
        raise FileNotFoundError(f"SR input not found: {args.sr_path}")

    windows = load_windows(paths)
    sr = load_solar_radiation(args.sr_path)
    ci_cache = args.ci_cache or args.output_dir / "clearing_index_history.csv"
    ci_history = get_ci_history(windows, ci_cache, args.timezone, args.refresh_ci)
    air_shed_id = resolve_air_shed_id(args.air_shed)
    selected_ci = ci_history.loc[ci_history["air_shed"].eq(air_shed_id)].copy()
    if selected_ci.empty:
        raise RuntimeError(f"No clearing-index records found for air shed {air_shed_id}")
    selected_ci["valid_date"] = pd.to_datetime(selected_ci["valid_date"]).dt.date
    ci_by_date = (
        selected_ci.sort_values("issue_time_local")
        .drop_duplicates("valid_date", keep="last")
        .set_index("valid_date")["clearing_index"]
    )

    output_specs = {
        "SR_filtered": "sr_filter_pass",
        "CI_filtered": "ci_filter_pass",
        "SR_CI_filtered": "sr_ci_filter_pass",
    }
    totals = {name: 0 for name in output_specs}
    input_rows = 0
    for path, frame in windows.items():
        audited = attach_filter_audit(
            frame, sr, ci_by_date, args.sr_threshold, args.ci_threshold
        )
        input_rows += len(audited)
        for directory, flag in output_specs.items():
            output_path = args.output_dir / directory / path.name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            filtered = audited.loc[audited[flag]].copy()
            filtered.to_csv(output_path, index=False)
            totals[directory] += len(filtered)
            print(f"{path.name}: {flag} retained {len(filtered)} of {len(audited)}")

    print(f"Air shed: {air_shed_id} ({AIRSHED_LOOKUP[air_shed_id]})")
    print(f"SR threshold: >= {args.sr_threshold:g} W/m^2 at any time in the window")
    print(f"CI threshold: exclude when > {args.ci_threshold} on any date in the window")
    for directory, retained in totals.items():
        print(f"{directory}: retained {retained} of {input_rows} rows across all files")
    print(f"Wrote outputs under: {args.output_dir}")


if __name__ == "__main__":
    main()
