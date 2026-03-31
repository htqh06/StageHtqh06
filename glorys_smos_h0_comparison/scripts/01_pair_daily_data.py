from __future__ import annotations

import argparse
from pathlib import Path

from pipeline_lib import default_paths, pair_daily_data, resolve_pilot_dates


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily GLORYS/ESA CCI paired files for the H0 pipeline.")
    parser.add_argument("--pilot-days", type=int, default=30, help="Number of valid overlapping days to pair when end-date is not provided.")
    parser.add_argument("--start-date", type=str, default=None, help="Optional start date, e.g. 2010-01-09.")
    parser.add_argument("--end-date", type=str, default=None, help="Optional end date, e.g. 2010-02-07.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_paths().comparison_root / "results" / "pilot_pairs" / "pairs",
        help="Output directory for daily pair NetCDF files.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing pair files.")
    args = parser.parse_args()

    paths = default_paths()
    dates = resolve_pilot_dates(paths, pilot_days=args.pilot_days, start_date=args.start_date, end_date=args.end_date)
    manifest = pair_daily_data(paths, dates, args.output_dir, overwrite=args.overwrite)
    print(f"Paired {len(manifest)} days into {args.output_dir}")


if __name__ == "__main__":
    main()