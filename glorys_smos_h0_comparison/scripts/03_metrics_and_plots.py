from __future__ import annotations

import argparse
from pathlib import Path

from pipeline_lib import metrics_and_plots_from_h0


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute observation-space metrics and plots from H0 daily files.")
    parser.add_argument("--h0-dir", type=Path, required=True, help="Directory created by 02_build_h0.py.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory where metrics and plots will be written.")
    parser.add_argument("--overwrite-plots", action="store_true", help="Overwrite existing daily panel plots.")
    parser.add_argument("--skip-daily-panels", action="store_true", help="Compute metrics without saving daily panel images.")
    parser.add_argument("--panel-every", type=int, default=1, help="Save one daily panel every N days when panels are enabled.")
    args = parser.parse_args()

    metrics = metrics_and_plots_from_h0(
        args.h0_dir,
        args.output_dir,
        overwrite_plots=args.overwrite_plots,
        save_daily_panels=not args.skip_daily_panels,
        panel_every=max(1, args.panel_every),
    )
    print(f"Computed metrics for {len(metrics)} daily files into {args.output_dir}")


if __name__ == "__main__":
    main()