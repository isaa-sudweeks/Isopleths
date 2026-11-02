"""Compare hourly PM2.5 during smoke and no-smoke isopleth observations."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data/utah/data_up_to_2025/raw/HW_data_raw_2026-05-23.csv"
SMOKE_PATH = ROOT / "data/utah/data_up_to_2025/summed/SR_CI_filtered/Smoke/2025_summed_smoke_all.csv"
NO_SMOKE_PATH = ROOT / "data/utah/data_up_to_2025/summed/SR_CI_filtered/No_Smoke/2025_summed_no_smoke_all.csv"
OUTPUT_PATH = ROOT / "plots/utah/pm25_smoke_vs_no_smoke_isopleth_hours.png"


def load_hourly_pm25() -> pd.DataFrame:
    columns = ["parameter_code", "poc", "dt", "sample_measurement", "sample_duration"]
    parts = []
    for chunk in pd.read_csv(RAW_PATH, usecols=columns, chunksize=250_000):
        selected = chunk[
            (chunk["parameter_code"] == 88101)
            & (chunk["sample_duration"] == "1 HOUR")
            & chunk["poc"].isin([2, 4])
        ]
        if not selected.empty:
            parts.append(selected)

    pm25 = pd.concat(parts, ignore_index=True)
    pm25["dt_key"] = pm25["dt"].astype(str).str[:19]
    pm25["sample_measurement"] = pd.to_numeric(pm25["sample_measurement"], errors="coerce")
    hourly = pm25.pivot_table(
        index="dt_key", columns="poc", values="sample_measurement", aggfunc="mean"
    ).rename(columns={2: "pm25_poc2", 4: "pm25_poc4"})
    hourly["pm25"] = hourly[["pm25_poc2", "pm25_poc4"]].mean(axis=1)
    return hourly


def match_group(path: Path, group: str, hourly_pm25: pd.DataFrame) -> pd.DataFrame:
    observations = pd.read_csv(path)
    observations["dt_key"] = observations["dt"].astype(str).str[:19]
    observations["date"] = observations["dt"].astype(str).str[:10]
    matched = observations.merge(hourly_pm25[["pm25"]], left_on="dt_key", right_index=True, how="left")
    matched["group"] = group
    return matched.dropna(subset=["pm25"])


def bootstrap_mean_interval(frame: pd.DataFrame, seed: int = 42) -> tuple[float, float]:
    """Bootstrap dates, retaining every matched hour within each sampled date."""
    rng = np.random.default_rng(seed)
    date_groups = [group["pm25"].to_numpy() for _, group in frame.groupby("date")]
    bootstrap_means = np.empty(10_000)
    for index in range(len(bootstrap_means)):
        sampled_indices = rng.integers(0, len(date_groups), size=len(date_groups))
        bootstrap_means[index] = np.concatenate(
            [date_groups[group_index] for group_index in sampled_indices]
        ).mean()
    return tuple(np.percentile(bootstrap_means, [2.5, 97.5]))


def main() -> None:
    hourly_pm25 = load_hourly_pm25()
    smoke = match_group(SMOKE_PATH, "Smoke", hourly_pm25)
    no_smoke = match_group(NO_SMOKE_PATH, "No smoke", hourly_pm25)
    groups = [no_smoke["pm25"].to_numpy(), smoke["pm25"].to_numpy()]
    labels = ["No smoke", "Smoke"]
    colors = ["#5B7FA3", "#D97941"]

    means = np.array([values.mean() for values in groups])
    medians = np.array([np.median(values) for values in groups])
    intervals = np.array([bootstrap_mean_interval(frame) for frame in [no_smoke, smoke]])

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8), gridspec_kw={"width_ratios": [1.35, 1]})

    violin = axes[0].violinplot(groups, positions=[1, 2], widths=0.75, showextrema=False)
    for body, color in zip(violin["bodies"], colors):
        body.set_facecolor(color)
        body.set_edgecolor("#263238")
        body.set_alpha(0.45)
        body.set_linewidth(1)
    box = axes[0].boxplot(
        groups,
        positions=[1, 2],
        widths=0.24,
        patch_artist=True,
        showfliers=True,
        medianprops={"color": "#111111", "linewidth": 2},
        whiskerprops={"color": "#37474F"},
        capprops={"color": "#37474F"},
        flierprops={"marker": ".", "markersize": 2.5, "alpha": 0.25, "markerfacecolor": "#37474F"},
    )
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    axes[0].scatter([1, 2], means, marker="D", s=48, color="#111111", label="Mean", zorder=5)
    axes[0].set_xticks([1, 2], [f"{label}\n(n={len(values):,})" for label, values in zip(labels, groups)])
    axes[0].set_ylabel("Hourly PM$_{2.5}$ (µg/m³)")
    axes[0].set_title("Matched hourly distributions")
    axes[0].legend(frameon=False, loc="upper right")

    axes[1].bar([1, 2], means, color=colors, edgecolor="#263238", linewidth=1, width=0.65)
    yerr = np.vstack([means - intervals[:, 0], intervals[:, 1] - means])
    axes[1].errorbar([1, 2], means, yerr=yerr, fmt="none", color="#111111", capsize=6, linewidth=1.6)
    axes[1].scatter([1, 2], medians, marker="o", s=45, facecolor="white", edgecolor="#111111", zorder=5)
    axes[1].set_xticks([1, 2], labels)
    axes[1].set_ylabel("Mean hourly PM$_{2.5}$ (µg/m³)")
    axes[1].set_title("Means with date-bootstrap 95% intervals")
    axes[1].set_ylim(0, max(intervals[:, 1]) * 1.28)
    for x, mean, median, high in zip([1, 2], means, medians, intervals[:, 1]):
        axes[1].text(x, high + 0.25, f"Mean {mean:.2f}\nMedian {median:.2f}", ha="center", va="bottom", fontsize=9)

    for axis in axes:
        axis.grid(axis="y", color="#DDE2E5", linewidth=0.8)
        axis.set_axisbelow(True)
        axis.spines[["top", "right"]].set_visible(False)

    fig.suptitle("PM$_{2.5}$ during smoke and no-smoke isopleth observations", fontsize=15, fontweight="bold")
    fig.text(
        0.5,
        0.01,
        "Hourly POCs 2 and 4 averaged when both were available; timestamps matched to SR/CI-filtered all-time isopleth inputs.",
        ha="center",
        fontsize=9,
        color="#455A64",
    )
    fig.tight_layout(rect=[0, 0.045, 1, 0.94])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=220, bbox_inches="tight", facecolor="white")

    print(f"No smoke: n={len(groups[0])}, mean={means[0]:.4f}, median={medians[0]:.4f}, CI={intervals[0]}")
    print(f"Smoke: n={len(groups[1])}, mean={means[1]:.4f}, median={medians[1]:.4f}, CI={intervals[1]}")
    print(f"Difference (smoke - no smoke): {means[1] - means[0]:.4f}")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
