# data 目录说明

这个目录主要分成两类数据：

1. 当前模型训练直接使用的处理后数据
2. 作为来源保存的原始或半原始数据产品

## 数据对应表

| 目录 | 数据类型 | 对应产品/来源 | 主要变量 | 是否当前训练直接使用 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `Copernicus_processed_data/` | 处理后训练数据 | Copernicus / GLORYS12V1 处理结果 | `so`, `thetao`, `zos`, `uo`, `vo` | 是 | 当前 `Diffusion` 与 `RESAC` 代码默认读取这里的 `.npy` 文件 |
| `data_source/OutputData-ResacEFArtPlus/data_LON-64-52-LAT+33+44/GLORYS12V1_PRODUCT_001_030/` | 原始模型数据 | MERCATOR GLORYS12V1 assimilated model | SSS, SST, SSH, `uo`, `vo`, `sla` 等 | 否 | 这是 GLORYS 模型原始来源目录 |
| `data_source/OutputData-ResacEFArtPlus/data_LON-64-52-LAT+33+44/SST_PRODUCT_010_024/` | 原始卫星数据 | Copernicus Satellite SST | SST | 否 | 卫星海表温度产品 |
| `data_source/OutputData-ResacEFArtPlus/data_LON-64-52-LAT+33+44/SSH_PRODUCT_008_047/` | 原始卫星数据 | Copernicus Satellite SSH | SLA, ADT, geostrophic velocity 等 | 否 | 卫星海表高度产品 |
| `data_source/ESACCI_LON-64-52-LAT+33+44_ResacEFArtPlus/Sea_Surface_Salinity/v5.5/7days/` | 原始海表盐度数据 | ESA CCI Sea Surface Salinity v5.5 | SSS | 否 | 这一套可视为当前仓库里对应 SMOS/ESA CCI 的海表盐度数据来源 |
| `data_source/Info/` | 说明文档 | 项目数据说明 | 文本、图片、文档 | 否 | 包含数据产品介绍和背景材料 |
| `data_sargasse/` | 区域数据文件 | `copernicus_1993_2021.nc` | 需按文件内容进一步确认 | 否 | 看起来是马尾藻海区域裁剪后的整合数据文件 |

## 哪个是 GLORYS，哪个是 SMOS

- **GLORYS 模型数据**：
  - 原始来源目录是 `data_source/OutputData-ResacEFArtPlus/.../GLORYS12V1_PRODUCT_001_030/`
  - 当前训练直接使用的是由它处理得到的 `Copernicus_processed_data/`

- **SMOS 对应的海表盐度数据**：
  - 当前仓库里对应的是 `data_source/ESACCI_LON-64-52-LAT+33+44_ResacEFArtPlus/Sea_Surface_Salinity/v5.5/7days/`
  - 说明文件中将它写为 `ESA SMOS SSS`，同时又注明产品名为 `ESA CCI Sea Surface Salinity`
  - 因此更准确的说法是：这是 **ESA CCI 的海表盐度产品**，在本项目语境里可作为 **SMOS 相关 SSS 数据来源** 来理解

## 当前代码默认使用的数据

当前仓库中的训练脚本默认读取：

- `Copernicus_processed_data/so_*.npy`
- `Copernicus_processed_data/thetao_*.npy`
- `Copernicus_processed_data/zos_*.npy`

其中：

- `so` 对应 SSS
- `thetao` 对应 SST
- `zos` 对应 SSH

也就是说，当前 `Diffusion` 与 `RESAC` 训练默认并不是直接读取 `SMOS/ESACCI` 原始目录，而是读取已经整理好的 `Copernicus_processed_data/`。

## 备注

- 如果后续要把 `SMOS/ESACCI` 的海表盐度数据真正接入训练流程，需要额外确认：
  - 文件格式
  - 时间范围是否与当前训练集对齐
  - 空间分辨率与网格是否需要重采样
  - 是否已经做过标准化和训练/验证/测试切分
