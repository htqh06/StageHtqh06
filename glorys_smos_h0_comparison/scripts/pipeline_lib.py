from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from scipy.ndimage import gaussian_filter
from skimage.metrics import structural_similarity


COMPARISON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CCI_ROOT = (
    REPO_ROOT
    / "data"
    / "data_source"
    / "ESACCI_LON-64-52-LAT+33+44_ResacEFArtPlus"
    / "Sea_Surface_Salinity"
    / "v5.5"
    / "7days"
)
DEFAULT_GLORYS_ROOT = (
    REPO_ROOT
    / "data"
    / "data_source"
    / "OutputData-ResacEFArtPlus"
    / "data_LON-64-52-LAT+33+44"
    / "GLORYS12V1_PRODUCT_001_030"
)
DEFAULT_GLORYS_EXTRA_ROOT = (
    REPO_ROOT
    / "data"
    / "data_source"
    / "OutputData-ResacEFArtPlus"
    / "data_LON-64-52-LAT+33+44"
    / "GLORYS12V1_PRODUCT_001_030-extra"
)

PROGRESS_EVERY = 25


@dataclass(frozen=True)
class PathConfig:
    repo_root: Path
    comparison_root: Path
    cci_root: Path
    glorys_root: Path
    glorys_extra_root: Path


@dataclass(frozen=True)
class H0Geometry:
    lat_weights: np.ndarray
    lon_weights: np.ndarray
    sigma_pixels: tuple[float, float]


class MonthlyDatasetCache:
    def __init__(self) -> None:
        self._cci: dict[tuple[int, int], xr.Dataset] = {}
        self._glorys: dict[tuple[int, int], xr.Dataset] = {}

    def cci_month(self, paths: PathConfig, year: int, month: int) -> xr.Dataset:
        key = (year, month)
        if key not in self._cci:
            path = cci_month_path(paths, year, month)
            self._cci[key] = xr.open_dataset(path, engine="netcdf4")[["sss", "sss_qc"]].load()
        return self._cci[key]

    def glorys_month(self, paths: PathConfig, year: int, month: int) -> xr.Dataset:
        key = (year, month)
        if key not in self._glorys:
            path = glorys_month_path(paths, year, month)
            self._glorys[key] = xr.open_dataset(path, engine="netcdf4")[["sss"]].load()
        return self._glorys[key]


def default_paths() -> PathConfig:
    return PathConfig(
        repo_root=REPO_ROOT,
        comparison_root=COMPARISON_ROOT,
        cci_root=DEFAULT_CCI_ROOT,
        glorys_root=DEFAULT_GLORYS_ROOT,
        glorys_extra_root=DEFAULT_GLORYS_EXTRA_ROOT,
    )


def cci_month_path(paths: PathConfig, year: int, month: int) -> Path:
    return paths.cci_root / f"{year}" / (
        f"esacci-seasurfacesalinity-l4-sss-global-merged_oi_7day_runningmean_daily_0.25deg-"
        f"{year}-{month:02d}-fv5.5-kr1.0.nc"
    )


def glorys_month_path(paths: PathConfig, year: int, month: int) -> Path:
    return paths.glorys_root / f"glorys12v1_mod_product_001_030_{year}-{month:02d}.nc"


def glorys_mask_path(paths: PathConfig) -> Path:
    return paths.glorys_extra_root / "glorys12v1_mask_mod_product_001_030.nc"


def glorys_mdt_path(paths: PathConfig) -> Path:
    return paths.glorys_extra_root / "glorys12v1_mdt_mod_product_001_030.nc"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_dataset_atomic(ds: xr.Dataset, output_path: Path) -> None:
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    try:
        ds.to_netcdf(tmp_path)
        tmp_path.replace(output_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def day_stamp(value: pd.Timestamp | np.datetime64 | str) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def month_key_iter(start: pd.Timestamp, end: pd.Timestamp) -> Iterable[tuple[int, int]]:
    current = pd.Timestamp(year=start.year, month=start.month, day=1)
    last = pd.Timestamp(year=end.year, month=end.month, day=1)
    while current <= last:
        yield current.year, current.month
        current += pd.offsets.MonthBegin(1)


def sorted_pair_files(pair_dir: Path) -> list[Path]:
    return sorted(pair_dir.glob("pair_*.nc"))


def sorted_h0_files(h0_dir: Path) -> list[Path]:
    return sorted(h0_dir.glob("h0_*.nc"))


def pair_output_path(output_dir: Path, date: pd.Timestamp) -> Path:
    return output_dir / f"pair_{date:%Y%m%d}.nc"


def h0_output_path(output_dir: Path, date: pd.Timestamp, fwhm_km: float) -> Path:
    return output_dir / f"h0_{date:%Y%m%d}_fwhm_{int(fwhm_km):02d}km.nc"


def date_from_pair_file(pair_file: Path) -> pd.Timestamp:
    return pd.Timestamp(pair_file.stem.removeprefix("pair_")).normalize()


def collect_cci_dates(
    paths: PathConfig,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[pd.Timestamp]:
    start_ts = day_stamp(start_date) if start_date else None
    end_ts = day_stamp(end_date) if end_date else None
    dates: list[pd.Timestamp] = []

    year_dirs = sorted(path for path in paths.cci_root.iterdir() if path.is_dir())
    for year_dir in year_dirs:
        for nc_path in sorted(year_dir.glob("*.nc")):
            ds = xr.open_dataset(nc_path, engine="netcdf4")[["time"]]
            month_dates = [day_stamp(value) for value in ds.time.values]
            ds.close()
            for date in month_dates:
                if start_ts is not None and date < start_ts:
                    continue
                if end_ts is not None and date > end_ts:
                    continue
                dates.append(date)

    return sorted(dates)


def load_cci_day(paths: PathConfig, cache: MonthlyDatasetCache, date: pd.Timestamp) -> tuple[xr.DataArray, xr.DataArray]:
    ds = cache.cci_month(paths, date.year, date.month)
    ts = np.datetime64(date.to_datetime64())
    y = ds["sss"].sel(time=ts).load()
    q = ds["sss_qc"].sel(time=ts).load()
    return y, q


def load_glorys_window(paths: PathConfig, cache: MonthlyDatasetCache, date: pd.Timestamp, radius_days: int = 3) -> xr.DataArray:
    start = date - pd.Timedelta(days=radius_days)
    end = date + pd.Timedelta(days=radius_days)
    pieces: list[xr.DataArray] = []
    for year, month in month_key_iter(start, end):
        ds = cache.glorys_month(paths, year, month)
        subset = ds["sss"].sel(time=slice(start.to_datetime64(), end.to_datetime64()))
        if subset.sizes.get("time", 0) > 0:
            pieces.append(subset)

    if not pieces:
        raise FileNotFoundError(f"No GLORYS data found for window centered on {date.date()}")

    window = xr.concat(pieces, dim="time").sortby("time")
    time_values = pd.to_datetime(window.time.values).normalize()
    unique_dates = pd.Index(time_values).unique().sort_values()
    if len(unique_dates) != 2 * radius_days + 1:
        raise ValueError(
            f"Expected {2 * radius_days + 1} GLORYS daily slices around {date.date()}, found {len(unique_dates)}"
        )
    return window.load()


def resolve_pilot_dates(
    paths: PathConfig,
    pilot_days: int = 30,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[pd.Timestamp]:
    cache = MonthlyDatasetCache()
    dates = collect_cci_dates(paths, start_date=start_date, end_date=end_date)
    selected: list[pd.Timestamp] = []

    for date in dates:
        try:
            load_glorys_window(paths, cache, date)
        except Exception:
            continue
        selected.append(date)
        if end_date is None and len(selected) >= pilot_days:
            break

    if not selected:
        raise RuntimeError("No overlapping pilot dates were found between CCI and GLORYS.")

    if end_date is None and len(selected) < pilot_days:
        raise RuntimeError(f"Requested {pilot_days} pilot days but only found {len(selected)} valid overlapping days.")

    return selected


def build_pair_dataset(paths: PathConfig, cache: MonthlyDatasetCache, date: pd.Timestamp) -> xr.Dataset:
    glorys_window = load_glorys_window(paths, cache, date)
    glorys_center = glorys_window.sel(time=np.datetime64(date.to_datetime64()))
    cci_sss, cci_qc = load_cci_day(paths, cache, date)
    obs_mask = (cci_qc == 0).astype(np.int8)

    glorys_window = glorys_window.rename(
        {"time": "window_time", "latitude": "glorys_latitude", "longitude": "glorys_longitude"}
    )
    glorys_center = glorys_center.rename({"latitude": "glorys_latitude", "longitude": "glorys_longitude"})
    cci_sss = cci_sss.rename({"lat": "cci_latitude", "lon": "cci_longitude"})
    cci_qc = cci_qc.rename({"lat": "cci_latitude", "lon": "cci_longitude"}).astype(np.int8)
    obs_mask = obs_mask.rename({"lat": "cci_latitude", "lon": "cci_longitude"})

    return xr.Dataset(
        data_vars={
            "glorys_window": glorys_window.astype(np.float32),
            "glorys_center": glorys_center.astype(np.float32),
            "cci_sss": cci_sss.astype(np.float32),
            "cci_qc": cci_qc,
            "obs_mask": obs_mask,
        },
        attrs={
            "date": date.strftime("%Y-%m-%d"),
            "description": "Daily paired GLORYS/ESA CCI data for H0 comparison.",
            "formula": "H0(X)=M(R(K(T(X))))",
        },
    )


def pair_daily_data(paths: PathConfig, dates: Sequence[pd.Timestamp], output_dir: Path, overwrite: bool = False) -> pd.DataFrame:
    ensure_dir(output_dir)
    cache = MonthlyDatasetCache()
    rows: list[dict[str, object]] = []
    total = len(dates)

    for index, date in enumerate(dates, start=1):
        output_path = pair_output_path(output_dir, date)
        if overwrite or not output_path.exists():
            ds = build_pair_dataset(paths, cache, date)
            write_dataset_atomic(ds, output_path)

        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "pair_file": output_path.name,
            }
        )

        if index == 1 or index == total or index % PROGRESS_EVERY == 0:
            print(f"[pair] {index}/{total} {date:%Y-%m-%d} -> {output_path.name}")

    manifest = pd.DataFrame(rows)
    manifest.to_csv(output_dir / "manifest.csv", index=False)
    return manifest


def load_glorys_sea_mask(paths: PathConfig) -> xr.DataArray:
    ds = xr.open_dataset(glorys_mask_path(paths), engine="netcdf4")[["mask"]].load()
    return ds["mask"].rename({"latitude": "glorys_latitude", "longitude": "glorys_longitude"}).astype(np.float64)


def cell_bounds_from_centers(centers: np.ndarray) -> np.ndarray:
    centers = np.asarray(centers, dtype=np.float64)
    bounds = np.empty(centers.size + 1, dtype=np.float64)
    bounds[1:-1] = 0.5 * (centers[:-1] + centers[1:])
    bounds[0] = centers[0] - 0.5 * (centers[1] - centers[0])
    bounds[-1] = centers[-1] + 0.5 * (centers[-1] - centers[-2])
    return bounds


def build_overlap_weights(src_centers: np.ndarray, dst_centers: np.ndarray, is_latitude: bool) -> np.ndarray:
    src_bounds = cell_bounds_from_centers(src_centers)
    dst_bounds = cell_bounds_from_centers(dst_centers)
    weights = np.zeros((dst_centers.size, src_centers.size), dtype=np.float64)

    for dst_index in range(dst_centers.size):
        dst_low = dst_bounds[dst_index]
        dst_high = dst_bounds[dst_index + 1]
        for src_index in range(src_centers.size):
            overlap_low = max(dst_low, src_bounds[src_index])
            overlap_high = min(dst_high, src_bounds[src_index + 1])
            if overlap_high <= overlap_low:
                continue
            if is_latitude:
                weights[dst_index, src_index] = (
                    math.sin(math.radians(overlap_high)) - math.sin(math.radians(overlap_low))
                )
            else:
                weights[dst_index, src_index] = math.radians(overlap_high - overlap_low)

    return weights


def fwhm_to_sigma_pixels(fwhm_km: float, latitudes: np.ndarray, longitudes: np.ndarray) -> tuple[float, float]:
    sigma_km = fwhm_km / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    lat_step_deg = float(np.median(np.diff(latitudes)))
    lon_step_deg = float(np.median(np.diff(longitudes)))
    mean_lat = float(np.mean(latitudes))
    km_per_lat_pixel = 111.32 * lat_step_deg
    km_per_lon_pixel = 111.32 * math.cos(math.radians(mean_lat)) * lon_step_deg
    return sigma_km / km_per_lat_pixel, sigma_km / km_per_lon_pixel


def normalized_gaussian_blur(field: np.ndarray, mask: np.ndarray, sigma_pixels: tuple[float, float]) -> np.ndarray:
    valid_mask = np.isfinite(field) & (mask > 0)
    weighted_field = np.where(valid_mask, field, 0.0)
    weighted_mask = valid_mask.astype(np.float64)
    numerator = gaussian_filter(weighted_field, sigma=sigma_pixels, mode="nearest")
    denominator = gaussian_filter(weighted_mask, sigma=sigma_pixels, mode="nearest")
    return np.divide(
        numerator,
        denominator,
        out=np.full_like(numerator, np.nan, dtype=np.float64),
        where=denominator > 0,
    )


def area_weighted_regrid(
    field: np.ndarray,
    source_mask: np.ndarray,
    lat_weights: np.ndarray,
    lon_weights: np.ndarray,
) -> np.ndarray:
    valid_mask = np.isfinite(field) & (source_mask > 0)
    masked_field = np.where(valid_mask, field, 0.0)
    normalization_mask = valid_mask.astype(np.float64)
    numerator = lat_weights @ masked_field @ lon_weights.T
    denominator = lat_weights @ normalization_mask @ lon_weights.T
    return np.divide(
        numerator,
        denominator,
        out=np.full((lat_weights.shape[0], lon_weights.shape[0]), np.nan, dtype=np.float64),
        where=denominator > 0,
    )


def build_h0_geometry(pair_ds: xr.Dataset, fwhm_km: float) -> H0Geometry:
    glorys_lat = pair_ds.glorys_latitude.values
    glorys_lon = pair_ds.glorys_longitude.values
    cci_lat = pair_ds.cci_latitude.values
    cci_lon = pair_ds.cci_longitude.values

    lat_weights = build_overlap_weights(glorys_lat, cci_lat, is_latitude=True)
    lon_weights = build_overlap_weights(glorys_lon, cci_lon, is_latitude=False)
    sigma_lat_px, sigma_lon_px = fwhm_to_sigma_pixels(fwhm_km, glorys_lat, glorys_lon)

    return H0Geometry(
        lat_weights=lat_weights,
        lon_weights=lon_weights,
        sigma_pixels=(sigma_lat_px, sigma_lon_px),
    )


def build_h0_dataset(pair_ds: xr.Dataset, source_mask: np.ndarray, fwhm_km: float, geometry: H0Geometry) -> xr.Dataset:
    sigma_lat_px, sigma_lon_px = geometry.sigma_pixels

    x_window = pair_ds["glorys_window"].values.astype(np.float64)
    x_center = pair_ds["glorys_center"].values.astype(np.float64)
    y = pair_ds["cci_sss"].values.astype(np.float64)
    q = pair_ds["cci_qc"].values.astype(np.int8)
    obs_mask = pair_ds["obs_mask"].values.astype(bool)

    x_t = np.nanmean(x_window, axis=0)
    x_k = normalized_gaussian_blur(x_t, source_mask, geometry.sigma_pixels)
    z = area_weighted_regrid(x_k, source_mask, geometry.lat_weights, geometry.lon_weights)
    h0 = np.where(obs_mask, z, np.nan)

    return xr.Dataset(
        data_vars={
            "glorys_center": pair_ds["glorys_center"].astype(np.float32),
            "x_t": (("glorys_latitude", "glorys_longitude"), x_t.astype(np.float32)),
            "x_k": (("glorys_latitude", "glorys_longitude"), x_k.astype(np.float32)),
            "z": (("cci_latitude", "cci_longitude"), z.astype(np.float32)),
            "h0": (("cci_latitude", "cci_longitude"), h0.astype(np.float32)),
            "cci_sss": pair_ds["cci_sss"].astype(np.float32),
            "cci_qc": (("cci_latitude", "cci_longitude"), q.astype(np.int8)),
            "obs_mask": (("cci_latitude", "cci_longitude"), obs_mask.astype(np.int8)),
        },
        coords={
            "glorys_latitude": pair_ds.glorys_latitude.values,
            "glorys_longitude": pair_ds.glorys_longitude.values,
            "cci_latitude": pair_ds.cci_latitude.values,
            "cci_longitude": pair_ds.cci_longitude.values,
        },
        attrs={
            "date": pair_ds.attrs["date"],
            "fwhm_km": float(fwhm_km),
            "sigma_lat_px": float(sigma_lat_px),
            "sigma_lon_px": float(sigma_lon_px),
            "description": "H0 observation-space GLORYS field for ESA CCI/SMOS comparison.",
        },
    )


def build_h0_from_pairs(
    paths: PathConfig,
    pair_dir: Path,
    output_dir: Path,
    fwhm_km: float,
    overwrite: bool = False,
) -> pd.DataFrame:
    ensure_dir(output_dir)
    pair_files = sorted_pair_files(pair_dir)
    if not pair_files:
        raise FileNotFoundError(f"No pair files were found in {pair_dir}")

    source_mask = load_glorys_sea_mask(paths).values
    rows: list[dict[str, object]] = []
    total = len(pair_files)
    geometry: H0Geometry | None = None

    for index, pair_file in enumerate(pair_files, start=1):
        date = date_from_pair_file(pair_file)
        output_path = h0_output_path(output_dir, date, fwhm_km)
        if overwrite or not output_path.exists():
            with xr.open_dataset(pair_file, engine="netcdf4") as opened:
                pair_ds = opened.load()
            if geometry is None:
                geometry = build_h0_geometry(pair_ds, fwhm_km)
            h0_ds = build_h0_dataset(pair_ds, source_mask, fwhm_km, geometry)
            write_dataset_atomic(h0_ds, output_path)

        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "fwhm_km": float(fwhm_km),
                "h0_file": output_path.name,
            }
        )

        if index == 1 or index == total or index % PROGRESS_EVERY == 0:
            print(f"[h0 {int(fwhm_km)}km] {index}/{total} {date:%Y-%m-%d} -> {output_path.name}")

    manifest = pd.DataFrame(rows)
    manifest.to_csv(output_dir / "manifest.csv", index=False)
    return manifest


def bounding_box(mask: np.ndarray) -> tuple[int, int, int, int]:
    rows, cols = np.where(mask)
    return rows.min(), rows.max(), cols.min(), cols.max()


def compute_gradient_magnitude(field: np.ndarray, latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
    dlat, dlon = np.gradient(field, latitudes, longitudes, edge_order=1)
    return np.sqrt(np.square(dlat) + np.square(dlon))


def masked_correlation(left: np.ndarray, right: np.ndarray, valid_mask: np.ndarray) -> float:
    if int(valid_mask.sum()) < 2:
        return float("nan")
    left_values = left[valid_mask].astype(np.float64)
    right_values = right[valid_mask].astype(np.float64)
    if np.allclose(left_values.std(), 0.0) or np.allclose(right_values.std(), 0.0):
        return float("nan")
    return float(np.corrcoef(left_values, right_values)[0, 1])


def masked_ssim(left: np.ndarray, right: np.ndarray, valid_mask: np.ndarray) -> float:
    if int(valid_mask.sum()) < 49:
        return float("nan")

    row_start, row_stop, col_start, col_stop = bounding_box(valid_mask)
    left_crop = left[row_start : row_stop + 1, col_start : col_stop + 1]
    right_crop = right[row_start : row_stop + 1, col_start : col_stop + 1]
    valid_crop = valid_mask[row_start : row_stop + 1, col_start : col_stop + 1]

    if min(left_crop.shape) < 7:
        return float("nan")

    fill_value = float(np.nanmean(np.concatenate([left[valid_mask], right[valid_mask]])))
    left_filled = np.where(valid_crop, left_crop, fill_value)
    right_filled = np.where(valid_crop, right_crop, fill_value)
    data_range = float(max(np.nanmax(left[valid_mask]), np.nanmax(right[valid_mask])) - min(np.nanmin(left[valid_mask]), np.nanmin(right[valid_mask])))
    if data_range == 0:
        data_range = 1.0
    return float(structural_similarity(left_filled, right_filled, data_range=data_range))


def save_field_panel(ax: plt.Axes, lon: np.ndarray, lat: np.ndarray, data: np.ndarray, title: str, cmap: str) -> None:
    mesh = ax.pcolormesh(lon, lat, data, shading="auto", cmap=cmap)
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.colorbar(mesh, ax=ax, shrink=0.85)


def save_daily_panel(ds: xr.Dataset, output_path: Path) -> None:
    obs_mask = ds["obs_mask"].values.astype(bool)
    y = ds["cci_sss"].values.astype(np.float64)
    h0 = ds["h0"].values.astype(np.float64)
    x_center = ds["glorys_center"].values.astype(np.float64)

    masked_y = np.where(obs_mask, y, np.nan)
    masked_h0 = np.where(obs_mask, h0, np.nan)
    diff = masked_h0 - masked_y
    grad_y = compute_gradient_magnitude(masked_y, ds.cci_latitude.values, ds.cci_longitude.values)
    grad_h = compute_gradient_magnitude(masked_h0, ds.cci_latitude.values, ds.cci_longitude.values)

    cci_vmin = np.nanmin([np.nanmin(masked_y), np.nanmin(masked_h0)])
    cci_vmax = np.nanmax([np.nanmax(masked_y), np.nanmax(masked_h0)])
    diff_lim = np.nanmax(np.abs(diff))
    grad_vmax = np.nanmax([np.nanmax(grad_y), np.nanmax(grad_h)])

    fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
    save_field_panel(axes[0, 0], ds.cci_longitude.values, ds.cci_latitude.values, masked_y, "Y (CCI q=0)", "viridis")
    axes[0, 0].collections[0].set_clim(cci_vmin, cci_vmax)

    save_field_panel(
        axes[0, 1],
        ds.glorys_longitude.values,
        ds.glorys_latitude.values,
        x_center,
        "X (raw GLORYS daily)",
        "viridis",
    )

    save_field_panel(axes[0, 2], ds.cci_longitude.values, ds.cci_latitude.values, masked_h0, "H0(X)", "viridis")
    axes[0, 2].collections[0].set_clim(cci_vmin, cci_vmax)

    save_field_panel(axes[1, 0], ds.cci_longitude.values, ds.cci_latitude.values, diff, "H0(X) - Y", "coolwarm")
    axes[1, 0].collections[0].set_clim(-diff_lim, diff_lim)

    save_field_panel(axes[1, 1], ds.cci_longitude.values, ds.cci_latitude.values, grad_y, "Gradient(Y)", "magma")
    axes[1, 1].collections[0].set_clim(0.0, grad_vmax)

    save_field_panel(axes[1, 2], ds.cci_longitude.values, ds.cci_latitude.values, grad_h, "Gradient(H0)", "magma")
    axes[1, 2].collections[0].set_clim(0.0, grad_vmax)

    fig.suptitle(f"{ds.attrs['date']} | FWHM = {int(ds.attrs['fwhm_km'])} km", fontsize=14)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_metric_timeseries(df: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True, constrained_layout=True)
    axes[0].plot(df["date"], df["bias"], marker="o")
    axes[0].set_ylabel("Bias")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(df["date"], df["rmse"], marker="o")
    axes[1].set_ylabel("RMSE")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(df["date"], df["corr"], marker="o")
    axes[2].set_ylabel("Corr")
    axes[2].grid(True, alpha=0.3)

    axes[3].plot(df["date"], df["ssim"], marker="o")
    axes[3].set_ylabel("SSIM")
    axes[3].grid(True, alpha=0.3)
    axes[3].set_xlabel("Date")

    fig.autofmt_xdate(rotation=45)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_gradient_quantiles(df: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4.5), constrained_layout=True)
    ax.plot(df["date"], df["grad_q90"], marker="o", label="|G_H-G_Y| q90")
    ax.plot(df["date"], df["grad_q95"], marker="o", label="|G_H-G_Y| q95")
    ax.plot(df["date"], df["grad_q99"], marker="o", label="|G_H-G_Y| q99")
    ax.set_ylabel("Gradient mismatch")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.autofmt_xdate(rotation=45)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def save_gradient_histogram(grad_y_values: np.ndarray, grad_h_values: np.ndarray, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.hist(grad_y_values, bins=60, density=True, alpha=0.5, label="Gradient(Y)")
    ax.hist(grad_h_values, bins=60, density=True, alpha=0.5, label="Gradient(H0)")
    ax.set_xlabel("Gradient magnitude")
    ax.set_ylabel("Density")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def metrics_and_plots_from_h0(
    h0_dir: Path,
    output_dir: Path,
    overwrite_plots: bool = False,
    save_daily_panels: bool = True,
    panel_every: int = 1,
) -> pd.DataFrame:
    ensure_dir(output_dir)
    panel_dir = output_dir / "daily_panels"
    if save_daily_panels:
        ensure_dir(panel_dir)

    rows: list[dict[str, object]] = []
    gradient_y_values: list[np.ndarray] = []
    gradient_h_values: list[np.ndarray] = []
    h0_files = sorted_h0_files(h0_dir)
    total = len(h0_files)

    for index, h0_file in enumerate(h0_files, start=1):
        with xr.open_dataset(h0_file, engine="netcdf4") as opened:
            ds = opened.load()
        date = day_stamp(ds.attrs["date"])
        y = ds["cci_sss"].values.astype(np.float64)
        h0 = ds["h0"].values.astype(np.float64)
        obs_mask = ds["obs_mask"].values.astype(bool)
        valid = obs_mask & np.isfinite(y) & np.isfinite(h0)
        if not np.any(valid):
            continue

        diff = h0 - y
        bias = float(np.nanmean(diff[valid]))
        rmse = float(np.sqrt(np.nanmean(np.square(diff[valid]))))
        corr = masked_correlation(h0, y, valid)
        ssim = masked_ssim(y, h0, valid)

        grad_y = compute_gradient_magnitude(np.where(valid, y, np.nan), ds.cci_latitude.values, ds.cci_longitude.values)
        grad_h = compute_gradient_magnitude(np.where(valid, h0, np.nan), ds.cci_latitude.values, ds.cci_longitude.values)
        grad_valid = valid & np.isfinite(grad_y) & np.isfinite(grad_h)
        abs_grad_diff = np.abs(grad_h - grad_y)

        gradient_y_values.append(grad_y[grad_valid])
        gradient_h_values.append(grad_h[grad_valid])

        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "fwhm_km": float(ds.attrs["fwhm_km"]),
                "valid_count": int(valid.sum()),
                "bias": bias,
                "rmse": rmse,
                "corr": corr,
                "ssim": ssim,
                "grad_q90": float(np.nanquantile(abs_grad_diff[grad_valid], 0.90)),
                "grad_q95": float(np.nanquantile(abs_grad_diff[grad_valid], 0.95)),
                "grad_q99": float(np.nanquantile(abs_grad_diff[grad_valid], 0.99)),
                "grad_y_q90": float(np.nanquantile(grad_y[grad_valid], 0.90)),
                "grad_y_q95": float(np.nanquantile(grad_y[grad_valid], 0.95)),
                "grad_y_q99": float(np.nanquantile(grad_y[grad_valid], 0.99)),
                "grad_h0_q90": float(np.nanquantile(grad_h[grad_valid], 0.90)),
                "grad_h0_q95": float(np.nanquantile(grad_h[grad_valid], 0.95)),
                "grad_h0_q99": float(np.nanquantile(grad_h[grad_valid], 0.99)),
            }
        )

        if save_daily_panels and ((index - 1) % panel_every == 0):
            panel_path = panel_dir / f"panel_{date:%Y%m%d}.png"
            if overwrite_plots or not panel_path.exists():
                save_daily_panel(ds, panel_path)

        if index == 1 or index == total or index % PROGRESS_EVERY == 0:
            print(
                f"[analysis {int(ds.attrs['fwhm_km'])}km] {index}/{total} {date:%Y-%m-%d} "
                f"rmse={rmse:.4f} corr={corr:.4f}"
            )

    metrics_df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    metrics_df.to_csv(output_dir / "metrics.csv", index=False)

    if not metrics_df.empty:
        save_metric_timeseries(metrics_df, output_dir / "metrics_timeseries.png")
        save_gradient_quantiles(metrics_df, output_dir / "gradient_quantiles.png")
        save_gradient_histogram(
            np.concatenate(gradient_y_values),
            np.concatenate(gradient_h_values),
            output_dir / "gradient_histogram.png",
        )

    return metrics_df