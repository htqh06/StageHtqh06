import argparse
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
SAVE_DIR = SCRIPT_DIR / "Save"
TEST_YEAR = 2020


def test_index_to_date(index, year=TEST_YEAR):
    return date(year, 1, 1) + timedelta(days=index)


def read_rows(path):
    with open(path, "r", newline="") as file:
        return list(csv.DictReader(file))


def group_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["mode"]].append(
            {
                "index": int(row["index"]),
                "date": test_index_to_date(int(row["index"])),
                "rmse": float(row["rmse"]),
                "ssim": float(row["ssim"]),
            }
        )

    for mode in grouped:
        grouped[mode] = sorted(grouped[mode], key=lambda item: item["index"])
    return grouped


def plot_metrics(grouped, output_path):
    figure, axes = plt.subplots(1, 3, figsize=(15, 4.8), width_ratios=[1.3, 1.3, 1.0])
    mode_names = list(grouped.keys())
    colors = {
        "DIFF-SST-SSH": "#0f766e",
        "DIFF-SST-SSH-GE": "#b45309",
    }

    legend_handles = []

    for mode in mode_names:
        entries = grouped[mode]
        x_labels = [entry["date"].isoformat() for entry in entries]
        rmse_values = [entry["rmse"] for entry in entries]
        ssim_values = [entry["ssim"] for entry in entries]
        color = colors.get(mode, None)

        axes[0].plot(x_labels, rmse_values, marker="o", linewidth=2, label=mode, color=color)
        axes[1].plot(x_labels, ssim_values, marker="o", linewidth=2, label=mode, color=color)
        legend_handles.append(Line2D([0], [0], color=color, marker="o", linewidth=2, label=mode))

    axes[0].set_title("RMSE by Test Date")
    axes[0].set_ylabel("RMSE")
    axes[0].tick_params(axis="x", rotation=20)
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(handles=legend_handles, loc="upper left", frameon=True)

    axes[1].set_title("SSIM by Test Date")
    axes[1].set_ylabel("SSIM")
    axes[1].tick_params(axis="x", rotation=20)
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(handles=legend_handles, loc="lower left", frameon=True)

    mean_rmse = [np.mean([entry["rmse"] for entry in grouped[mode]]) for mode in mode_names]
    mean_ssim = [np.mean([entry["ssim"] for entry in grouped[mode]]) for mode in mode_names]
    x = np.arange(len(mode_names))
    width = 0.35

    axes[2].bar(x - width / 2, mean_rmse, width=width, label="Mean RMSE", color="#2563eb")
    axes[2].bar(x + width / 2, mean_ssim, width=width, label="Mean SSIM", color="#dc2626")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(mode_names, rotation=15)
    axes[2].set_title("Mean Metrics")
    axes[2].grid(True, axis="y", alpha=0.25)
    axes[2].legend()

    figure.suptitle("Subset Test Metrics on 2020 Test Days", fontsize=15)
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description="Plot RMSE/SSIM from a subset diffusion test CSV.")
    parser.add_argument(
        "--input",
        default=str(SAVE_DIR / "subset_test_metrics_epoch39_3days.csv"),
        help="Input CSV path produced by evaluate_diffusion_subset.py",
    )
    parser.add_argument(
        "--output",
        default=str(SAVE_DIR / "subset_test_metrics_epoch39_3days.png"),
        help="Output PNG path",
    )
    args = parser.parse_args()

    rows = read_rows(args.input)
    grouped = group_rows(rows)
    plot_metrics(grouped, Path(args.output))
    print(f"Saved plot to {args.output}")


if __name__ == "__main__":
    main()
