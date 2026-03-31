# FWHM 30/40/50 km comparison

Common period: 2010-01-09 to 2023-12-30.
Common sample size: 5088 daily files for each FWHM.

| FWHM (km) | Days | Mean abs bias | Mean RMSE | Mean corr | Mean SSIM | Mean grad q90 | Mean grad q95 | Mean grad q99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 | 5088 | 0.074553 | 0.454308 | 0.948903 | 0.693320 | 1.267493 | 1.801558 | 3.037775 |
| 40 | 5088 | 0.074443 | 0.440967 | 0.951748 | 0.703210 | 1.210640 | 1.696030 | 2.791023 |
| 50 | 5088 | 0.074299 | 0.427743 | 0.954496 | 0.713120 | 1.158401 | 1.603085 | 2.584369 |

Interpretation:

- 50 km is the best of the tested 30/40/50 km settings on every reported metric.
- Relative to 40 km, 50 km lowers mean RMSE by 0.013224 (about 3.00%), raises mean correlation by 0.002748, raises mean SSIM by 0.009910, and lowers the mean gradient-mismatch q95 by 0.092945 (about 5.48%).
- Relative to 30 km, 50 km lowers mean RMSE by 0.026565 (about 5.85%), raises mean correlation by 0.005593, raises mean SSIM by 0.019800, and lowers the mean gradient-mismatch q95 by 0.198473 (about 11.02%).
- The trend is monotonic from 30 km to 40 km to 50 km: stronger smoothing consistently improves agreement with the CCI observation field in this setup.
- Mean absolute bias changes very little across the three settings, so the gain mainly comes from better spatial-scale matching rather than from mean-bias correction.
- Monthly mean RMSE also improves in every month when moving from 40 km to 50 km, with the largest absolute drops in January to April and again in November to December.

Working interpretation:

- In this domain and period, the effective observation footprint represented by H0 appears broader than 40 km.
- The 30 km operator is likely under-smoothed: it leaves too much small-scale structure from GLORYS in observation space, which shows up as higher RMSE, lower SSIM, and larger gradient mismatch.
- The 50 km operator closes more of the GLORYS-to-CCI scale gap without introducing a larger mean bias.
- Because the improvement from 40 km to 50 km is still systematic, 60 km remains worth testing as the next candidate, but the current evidence already favors 50 km over both 30 km and 40 km.