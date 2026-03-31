# FWHM 30/40/50/60 km comparison

Common period: 2010-01-09 to 2023-12-30.
Common sample size: 5088 daily files for each FWHM.

| FWHM (km) | Days | Mean abs bias | Mean RMSE | Mean corr | Mean SSIM | Mean grad q90 | Mean grad q95 | Mean grad q99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 | 5088 | 0.074553 | 0.454308 | 0.948903 | 0.693320 | 1.267493 | 1.801558 | 3.037775 |
| 40 | 5088 | 0.074443 | 0.440967 | 0.951748 | 0.703210 | 1.210640 | 1.696030 | 2.791023 |
| 50 | 5088 | 0.074299 | 0.427743 | 0.954496 | 0.713120 | 1.158401 | 1.603085 | 2.584369 |
| 60 | 5088 | 0.074123 | 0.415325 | 0.957010 | 0.722482 | 1.114808 | 1.528542 | 2.426100 |

Interpretation:

- On the current common-date comparison, the ranking is monotonic: 60 km > 50 km > 40 km > 30 km.
- Relative to 50 km, 60 km lowers mean RMSE by 0.012418 (about 2.90%), raises mean correlation by 0.002514, raises mean SSIM by 0.009362, and lowers mean gradient-mismatch q95 by 0.074543 (about 4.65%).
- Mean absolute bias remains nearly unchanged across all four settings, so the gain still comes mainly from better spatial-scale matching rather than mean-bias correction.
- The improvement from 50 km to 60 km means the effective observation footprint in this setup is likely broader than 50 km as well.
- Since the trend is still improving at 60 km, the current evidence suggests that testing 70 km or 80 km would be the next logical step if the goal is to locate the optimum footprint scale rather than just improve over the 40 km baseline.