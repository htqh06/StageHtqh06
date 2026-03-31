# GLORYS x SMOS/ESA CCI H0 Comparison

This directory contains a standalone comparison project for the H0 pipeline described in `cci_glorys_pipeline.pdf`.

The comparison is not performed between raw GLORYS and raw ESA CCI SSS directly. Instead, GLORYS is transformed into observation space through:

$$
H_0(X) = M\left(R\left(K\left(T(X)\right)\right)\right)
$$

where:

- `X`: GLORYS daily `sss`
- `T`: 7-day temporal smoothing
- `K`: normalized Gaussian spatial smoothing
- `R`: area-weighted regridding from the GLORYS grid to the ESA CCI 0.25 degree grid
- `M`: observation mask derived from `sss_qc` with `q=0`

In this repository context, “SMOS” refers to the ESA CCI SSS observation product stored under the raw source directory.

## Layout

```text
glorys_smos_h0_comparison/
├─ README.md
├─ scripts/
│  ├─ pipeline_lib.py
│  ├─ 01_pair_daily_data.py
│  ├─ 02_build_h0.py
│  ├─ 03_metrics_and_plots.py
│  └─ run_pilot.py
└─ results/
```

## Scripts

### `01_pair_daily_data.py`

Builds paired daily inputs:

- GLORYS 7-day windows around each comparison day
- ESA CCI `sss`
- ESA CCI `sss_qc`
- observation mask `M = (q == 0)`

### `02_build_h0.py`

Builds the H0 fields for one FWHM value:

- `X_T`: 7-day temporal mean
- `X_K`: normalized Gaussian blur on the GLORYS grid
- `Z`: area-weighted regridded field on the CCI grid
- `H0`: masked observation-space field

### `03_metrics_and_plots.py`

Computes observation-space metrics and saves plots:

- `bias`, `rmse`, `corr`, `ssim`
- gradient quantiles
- daily 6-panel figures
- metric time series
- aggregate gradient histograms

### `run_pilot.py`

Runs a 30-day pilot by default, then scans `FWHM = 40 / 50 / 60 km`.

## Run

From the repository root:

```powershell
E:/Anaconda/envs/ml_env/python.exe glorys_smos_h0_comparison/scripts/run_pilot.py
```

This creates a dated run folder under `glorys_smos_h0_comparison/results/` containing:

- `pairs/`
- `h0_fwhm_40km/`, `h0_fwhm_50km/`, `h0_fwhm_60km/`
- `analysis_fwhm_40km/`, `analysis_fwhm_50km/`, `analysis_fwhm_60km/`
- `fwhm_summary.csv`
- `fwhm_summary.png`

## Notes

- The GLORYS land-sea mask is read from `GLORYS12V1_PRODUCT_001_030-extra/glorys12v1_mask_mod_product_001_030.nc`.
- The regridding step is implemented as area-weighted overlap on the regular rectilinear grids present in this repository.
- The pilot defaults to the first 30 valid overlapping dates in the CCI period.