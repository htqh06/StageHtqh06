from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SMOS_ROOT = PROJECT_ROOT / "data" / "data_source" / "ESACCI_LON-64-52-LAT+33+44_ResacEFArtPlus" / "Sea_Surface_Salinity" / "v5.5" / "7days"
DEFAULT_GLORYS_ROOT = PROJECT_ROOT / "data" / "data_source" / "OutputData-ResacEFArtPlus" / "data_LON-64-52-LAT+33+44" / "GLORYS12V1_PRODUCT_001_030"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "smos_glorys_comparison"


@dataclass
class RunningStats:
    count: int = 0
    sum_x: float = 0.0
    sum_y: float = 0.0
    sum_x2: float = 0.0
    sum_y2: float = 0.0
    sum_xy: float = 0.0
    sum_diff: float = 0.0
    sum_abs_diff: float = 0.0
    sum_sq_diff: float = 0.0

    def update(self, x: np.ndarray, y: np.ndarray) -> None:
        mask = np.isfinite(x) & np.isfinite(y)
        if not np.any(mask):
            return

        xv = x[mask].astype(np.float64, copy=False)
        yv = y[mask].astype(np.float64, copy=False)
        diff = xv - yv

        self.count += int(xv.size)
        self.sum_x += float(xv.sum())
        self.sum_y += float(yv.sum())
        self.sum_x2 += float(np.square(xv).sum())
        self.sum_y2 += float(np.square(yv).sum())
        self.sum_xy += float((xv * yv).sum())
        self.sum_diff += float(diff.sum())
        self.sum_abs_diff += float(np.abs(diff).sum())
        self.sum_sq_diff += float(np.square(diff).sum())

    def as_dict(self) -> dict[str, float]:
        if self.count == 0:
            return {
                "count": 0,
                "smos_mean": np.nan,
                "glorys_mean": np.nan,
                "bias_glorys_minus_smos": np.nan,
                "mae": np.nan,
                "rmse": np.nan,
                "corr": np.nan,
            }

        mean_x = self.sum_x / self.count
        mean_y = self.sum_y / self.count
        var_x = max(self.sum_x2 / self.count - mean_x**2, 0.0)
        var_y = max(self.sum_y2 / self.count - mean_y**2, 0.0)
        cov_xy = self.sum_xy / self.count - mean_x * mean_y
        denom = math.sqrt(var_x * var_y)
        corr = cov_xy / denom if denom > 0 else np.nan

        return {
            "count": self.count,
            "smos_mean": mean_x,
            "glorys_mean": mean_y,
            "bias_glorys_minus_smos": self.sum_diff / self.count,
            "mae": self.sum_abs_diff / self.count,
            "rmse": math.sqrt(self.sum_sq_diff / self.count),
            "corr": corr,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare SMOS/ESA CCI sea surface salinity against GLORYS over their overlapping period."
    )
    parser.add_argument("--smos-root", type=Path, default=DEFAULT_SMOS_ROOT)
    parser.add_argument("--glorys-root", type=Path, default=DEFAULT_GLORYS_ROOT)
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Only write CSV summaries and do not create PNG plots.",
    )
    return parser.parse_args()


def month_iter(start_year: int, end_year: int):
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            yield year, month


def find_monthly_pair(smos_root: Path, glorys_root: Path, year: int, month: int) -> tuple[Path, Path] | None:
    smos_file = smos_root / f"{year}" / (
        f"esacci-seasurfacesalinity-l4-sss-global-merged_oi_7day_runningmean_daily_0.25deg-{year}-{month:02d}-fv5.5-kr1.0.nc"
    )
    glorys_file = glorys_root / f"glorys12v1_mod_product_001_030_{year}-{month:02d}.nc"

    if smos_file.exists() and glorys_file.exists():
        return smos_file, glorys_file
    return None


def open_smos_sss(path: Path) -> xr.DataArray:
    ds = xr.open_dataset(path, engine="netcdf4")
    da = ds["sss"].where(ds["sss_qc"] == 0)
    return da.rename({"lat": "latitude", "lon": "longitude"}).load()


def open_glorys_sss(path: Path) -> xr.DataArray:
    ds = xr.open_dataset(path, engine="netcdf4")
    var_name = "sss" if "sss" in ds.data_vars else "so"
    return ds[var_name].load()


def compare_one_month(smos_file: Path, glorys_file: Path) -> tuple[dict[str, float], xr.DataArray, xr.DataArray, xr.DataArray]:
    smos = open_smos_sss(smos_file)
    glorys = open_glorys_sss(glorys_file)

    glorys_on_smos = glorys.interp(
        latitude=smos.latitude,
        longitude=smos.longitude,
        kwargs={"fill_value": "extrapolate"},
    )
    smos_aligned, glorys_aligned = xr.align(smos, glorys_on_smos, join="inner")

    stats = RunningStats()
    stats.update(glorys_aligned.values, smos_aligned.values)
    metrics = stats.as_dict()
    metrics["n_times"] = int(smos_aligned.sizes.get("time", 0))
    metrics["start_time"] = str(pd.Timestamp(smos_aligned.time.values[0]).date()) if smos_aligned.sizes.get("time", 0) else ""
    metrics["end_time"] = str(pd.Timestamp(smos_aligned.time.values[-1]).date()) if smos_aligned.sizes.get("time", 0) else ""
    metrics["smos_file"] = smos_file.name
    metrics["glorys_file"] = glorys_file.name

    return metrics, smos_aligned, glorys_aligned, glorys_aligned - smos_aligned


def save_metric_plot(df: pd.DataFrame, metric: str, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(df["month"], df[metric], marker="o", linewidth=1.5)
    ax.set_title(f"SMOS vs GLORYS monthly {metric}")
    ax.set_xlabel("Month")
    ax.set_ylabel(metric)
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_bias_map(diff_sum: np.ndarray, diff_count: np.ndarray, latitude: np.ndarray, longitude: np.ndarray, output_path: Path) -> None:
    mean_bias = np.divide(
        diff_sum,
        diff_count,
        out=np.full_like(diff_sum, np.nan, dtype=np.float64),
        where=diff_count > 0,
    )

    fig, ax = plt.subplots(figsize=(8, 6))
    mesh = ax.pcolormesh(longitude, latitude, mean_bias, shading="auto", cmap="coolwarm")
    ax.set_title("Mean bias map (GLORYS - SMOS)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    fig.colorbar(mesh, ax=ax, label="psu")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    overall_stats = RunningStats()
    monthly_rows: list[dict[str, float]] = []
    diff_sum = None
    diff_count = None
    latitude = None
    longitude = None

    available_pairs = []
    for year, month in month_iter(args.start_year, args.end_year):
        pair = find_monthly_pair(args.smos_root, args.glorys_root, year, month)
        if pair is not None:
            available_pairs.append((year, month, *pair))

    if not available_pairs:
        raise FileNotFoundError("No overlapping monthly SMOS and GLORYS files were found.")

    for year, month, smos_file, glorys_file in available_pairs:
        metrics, smos_aligned, glorys_aligned, diff = compare_one_month(smos_file, glorys_file)
        metrics["year"] = year
        metrics["month_index"] = month
        metrics["month"] = f"{year}-{month:02d}"
        monthly_rows.append(metrics)
        overall_stats.update(glorys_aligned.values, smos_aligned.values)

        monthly_diff_sum = diff.sum(dim="time", skipna=True).values.astype(np.float64, copy=False)
        monthly_diff_count = np.isfinite(diff.values).sum(axis=0).astype(np.float64, copy=False)
        if diff_sum is None:
            diff_sum = monthly_diff_sum
            diff_count = monthly_diff_count
            latitude = diff.latitude.values
            longitude = diff.longitude.values
        else:
            diff_sum += monthly_diff_sum
            diff_count += monthly_diff_count

        print(
            f"[{year}-{month:02d}] n={metrics['count']} rmse={metrics['rmse']:.4f} "
            f"bias={metrics['bias_glorys_minus_smos']:.4f} corr={metrics['corr']:.4f}"
        )

    monthly_df = pd.DataFrame(monthly_rows).sort_values(["year", "month_index"]).reset_index(drop=True)
    monthly_df.to_csv(output_dir / "monthly_metrics.csv", index=False)

    overall_row = overall_stats.as_dict()
    overall_row["n_months"] = len(monthly_df)
    overall_row["start_year"] = args.start_year
    overall_row["end_year"] = args.end_year
    overall_df = pd.DataFrame([overall_row])
    overall_df.to_csv(output_dir / "overall_metrics.csv", index=False)

    if not args.skip_plots:
        save_metric_plot(monthly_df, "rmse", output_dir / "monthly_rmse.png")
        save_metric_plot(monthly_df, "bias_glorys_minus_smos", output_dir / "monthly_bias.png")
        save_metric_plot(monthly_df, "corr", output_dir / "monthly_corr.png")
        save_bias_map(diff_sum, diff_count, latitude, longitude, output_dir / "mean_bias_map.png")

    print("\nOverall metrics")
    for key, value in overall_row.items():
        print(f"{key}: {value}")
    print(f"\nSaved outputs to: {output_dir}")


if __name__ == "__main__":
    main()