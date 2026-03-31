from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from pipeline_lib import (
    default_paths,
    ensure_dir,
    metrics_and_plots_from_h0,
    pair_daily_data,
    resolve_pilot_dates,
    build_h0_from_pairs,
)


def save_fwhm_summary_plot(summary_df: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    axes[0, 0].plot(summary_df["fwhm_km"], summary_df["mean_rmse"], marker="o")
    axes[0, 0].set_title("Mean RMSE")
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(summary_df["fwhm_km"], summary_df["mean_abs_bias"], marker="o")
    axes[0, 1].set_title("Mean |Bias|")
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].plot(summary_df["fwhm_km"], summary_df["mean_corr"], marker="o")
    axes[1, 0].set_title("Mean Correlation")
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].plot(summary_df["fwhm_km"], summary_df["mean_grad_q95"], marker="o")
    axes[1, 1].set_title("Mean Gradient q95")
    axes[1, 1].grid(True, alpha=0.3)

    for ax in axes.flat:
        ax.set_xlabel("FWHM (km)")

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 30-day H0 pilot and scan FWHM values.")
    parser.add_argument("--pilot-days", type=int, default=30, help="Number of valid overlapping days to run.")
    parser.add_argument("--start-date", type=str, default=None, help="Optional pilot start date.")
    parser.add_argument("--end-date", type=str, default=None, help="Optional pilot end date.")
    parser.add_argument("--run-name", type=str, default=None, help="Optional name for the result folder.")
    parser.add_argument("--fwhm-km", type=float, nargs="+", default=[40.0, 50.0, 60.0], help="FWHM scan in km.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing intermediate and analysis files.")
    parser.add_argument("--skip-daily-panels", action="store_true", help="Compute metrics without saving daily panel images.")
    parser.add_argument("--panel-every", type=int, default=1, help="Save one daily panel every N days when panels are enabled.")
    args = parser.parse_args()

    paths = default_paths()
    dates = resolve_pilot_dates(paths, pilot_days=args.pilot_days, start_date=args.start_date, end_date=args.end_date)
    run_name = args.run_name or f"pilot_{dates[0]:%Y%m%d}_{dates[-1]:%Y%m%d}"
    run_dir = paths.comparison_root / "results" / run_name
    pair_dir = run_dir / "pairs"

    ensure_dir(run_dir)
    print(f"[run] result directory: {run_dir}")
    print(f"[run] selected days: {len(dates)} from {dates[0]:%Y-%m-%d} to {dates[-1]:%Y-%m-%d}")
    pair_manifest = pair_daily_data(paths, dates, pair_dir, overwrite=args.overwrite)

    summary_rows: list[dict[str, float]] = []
    for fwhm_km in args.fwhm_km:
        fwhm_label = int(fwhm_km)
        h0_dir = run_dir / f"h0_fwhm_{fwhm_label}km"
        analysis_dir = run_dir / f"analysis_fwhm_{fwhm_label}km"
        print(f"[run] building H0 for FWHM={fwhm_label} km")
        build_h0_from_pairs(paths, pair_dir, h0_dir, fwhm_km, overwrite=args.overwrite)
        print(f"[run] analyzing H0 for FWHM={fwhm_label} km")
        metrics_df = metrics_and_plots_from_h0(
            h0_dir,
            analysis_dir,
            overwrite_plots=args.overwrite,
            save_daily_panels=not args.skip_daily_panels,
            panel_every=max(1, args.panel_every),
        )
        if metrics_df.empty:
            continue
        summary_rows.append(
            {
                "fwhm_km": float(fwhm_km),
                "n_days": float(len(metrics_df)),
                "mean_bias": float(metrics_df["bias"].mean()),
                "mean_abs_bias": float(metrics_df["bias"].abs().mean()),
                "mean_rmse": float(metrics_df["rmse"].mean()),
                "mean_corr": float(metrics_df["corr"].mean()),
                "mean_ssim": float(metrics_df["ssim"].mean()),
                "mean_grad_q90": float(metrics_df["grad_q90"].mean()),
                "mean_grad_q95": float(metrics_df["grad_q95"].mean()),
                "mean_grad_q99": float(metrics_df["grad_q99"].mean()),
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values("fwhm_km").reset_index(drop=True)
    summary_df.to_csv(run_dir / "fwhm_summary.csv", index=False)
    if not summary_df.empty:
        save_fwhm_summary_plot(summary_df, run_dir / "fwhm_summary.png")

    print(f"Pilot run directory: {run_dir}")
    print(f"Paired days: {len(pair_manifest)}")
    if not summary_df.empty:
        print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()