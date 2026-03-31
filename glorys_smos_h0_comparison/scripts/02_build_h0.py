from __future__ import annotations

import argparse
from pathlib import Path

from pipeline_lib import build_h0_from_pairs, default_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Build H0(X)=M(R(K(T(X)))) daily fields from paired inputs.")
    parser.add_argument(
        "--pair-dir",
        type=Path,
        required=True,
        help="Directory created by 01_pair_daily_data.py.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where H0 daily NetCDF files will be written.",
    )
    parser.add_argument("--fwhm-km", type=float, default=50.0, help="Gaussian blur full width at half maximum in km.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing H0 files.")
    args = parser.parse_args()

    manifest = build_h0_from_pairs(default_paths(), args.pair_dir, args.output_dir, args.fwhm_km, overwrite=args.overwrite)
    print(f"Built {len(manifest)} H0 daily files into {args.output_dir}")


if __name__ == "__main__":
    main()