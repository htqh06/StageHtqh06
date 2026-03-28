# StageTH: Ocean Downscaling with RESAC and Diffusion

## 中文简介
本项目面向海洋表层变量的超分辨率/下采样重建，包含两条主要路线：

1. `RESAC` 多尺度 CNN 方案（`Code/RESAC_train`）
2. 三变量 `Diffusion` 方案（`Code/Diffusion_model`）

当前仓库主要保存代码与说明文档。为便于跨地点（家里/办公室）同步，已默认忽略大体积数据和训练产物（见 `.gitignore`）。

## English Overview
This project focuses on ocean surface variable super-resolution/downscaling with two main pipelines:

1. `RESAC` multi-scale CNN pipeline (`Code/RESAC_train`)
2. 3-variable `Diffusion` pipeline (`Code/Diffusion_model`)

This repository is code-first. Large datasets and training artifacts are ignored by default (see `.gitignore`) for easier sync across locations.

## 项目结构 | Repository Layout
```text
StageTH/
├─ Code/
│  ├─ Diffusion_model/
│  │  ├─ diff_3var_fast64.py       # Diffusion training entry
│  │  ├─ Dataset_3var.py           # Diffusion dataset (3-channel patches)
│  │  ├─ guided_sampling_3var.py   # Guided sampling/inference
│  │  └─ obs_operator_3var.py      # Observation operator for guidance
│  ├─ RESAC_train/
│  │  ├─ main_SSS_SST-RESAC.py     # RESAC training/testing entry
│  │  ├─ Dataloader_SSS_SST.py     # RESAC dataloader (multi-scale)
│  │  └─ archi_SSS_SST.py          # RESAC model architecture
│  ├─ Dataprocess.py               # Data preprocessing script (extended)
│  └─ data_process.py              # Data preprocessing script (legacy)
├─ data/
│  ├─ data_source/                 # Raw source products (Copernicus/ESA etc.)
│  └─ Copernicus_processed_data/   # Processed .npy tensors for training
└─ walkthrough.md                  # Chinese technical walkthrough
```

## 数据说明 | Data Notes
处理后数据目录：`data/Copernicus_processed_data`

数据目录的来源映射、GLORYS 与 SMOS/ESA CCI 的对应关系，见：`data/README.md`

变量与命名：
- `so_*` (salinity / SSS)
- `thetao_*` (temperature / SST)
- `zos_*` (sea surface height / SSH)
- `uo_*`, `vo_*` (velocity components)

当前数据形状（本地实测）：
- `so/thetao/uo/vo`: train chunk `(256, 1, 124, 131)`, val `(365, 1, 124, 131)`, test `(366, 1, 124, 131)`
- `zos`: train chunk `(256, 124, 131)`, val `(365, 124, 131)`, test `(366, 124, 131)`

Diffusion 训练中，每个样本会从整图随机裁剪 `64x64` patch，并拼成 3 通道：
- channel 0 = `so`
- channel 1 = `thetao`
- channel 2 = `zos`

## 环境准备 | Environment
### 推荐（与你当前环境一致）
Windows + Conda:
- Python: `3.10`
- Env path: `E:\Anaconda\envs\ml_env\python.exe`

验证命令：
```powershell
E:\Anaconda\envs\ml_env\python.exe -c "import torch, diffusers, lightning; print(torch.__version__)"
```

### 可选：新建环境（示例）
```powershell
conda create -n ml_env python=3.10 -y
conda activate ml_env
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install lightning diffusers numpy tqdm matplotlib pandas xarray scikit-learn scikit-image netcdf4
```

## 运行方式 | How to Run
以下命令默认在仓库根目录 `StageTH/` 执行。

### 1) Diffusion 训练 | Diffusion Training
```powershell
E:\Anaconda\envs\ml_env\python.exe Code\Diffusion_model\diff_3var_fast64.py
```

说明：
- 默认超参在脚本顶部（如 `n_epochs=1`, `bsize=8`）。
- 训练输出默认写入 `Code/Diffusion_model/Save/`。
- `diff_3var_fast64.py` 里数据路径是绝对路径；若你将仓库放到其他盘符，需要同步修改 `data_path` 和 `checkpoint_dir`。

### 2) Diffusion 引导采样 | Guided Sampling
可在 Python 中调用 `guidance_3var(...)`：
```python
from Code.Diffusion_model.guided_sampling_3var import guidance_3var

final_image, true_sss, true_sst, true_ssh, obs_sss_clean, obs_sss = guidance_3var(
    checkpoint="f:/StageTH/Code/Diffusion_model/Save/lightning_logs/version_0/checkpoints/epoch=0-step=148.ckpt",
    fname_sss="f:/StageTH/data/Copernicus_processed_data/so_test.npy",
    fname_sst="f:/StageTH/data/Copernicus_processed_data/thetao_test.npy",
    fname_ssh="f:/StageTH/data/Copernicus_processed_data/zos_test.npy",
    index=0,
    r1=10,
    r2=20,
    num_timesteps=50
)
```

### 3) RESAC 训练 | RESAC Training
```powershell
Set-Location Code\RESAC_train
E:\Anaconda\envs\ml_env\python.exe main_SSS_SST-RESAC.py
```

说明：
- 脚本默认 `train_flag=True`, `test_flag=False`。
- 默认数据路径为 `../data/Copernicus_processed_data`（相对 `Code/RESAC_train`）。

### 4) 预处理脚本 | Preprocessing
```powershell
E:\Anaconda\envs\ml_env\python.exe Code\data_process.py
E:\Anaconda\envs\ml_env\python.exe Code\Dataprocess.py
```

提示：
- 两个脚本来源不同，路径与输出格式（多为 `.pt`）依赖脚本内部配置。
- 若你想统一成当前 `.npy` 训练格式，建议先备份再修改。

## 已有结果 | Existing Outputs in Repo
Diffusion 目录已有一次训练产物示例：
- checkpoint: `Code/Diffusion_model/Save/lightning_logs/version_0/checkpoints/epoch=0-step=148.ckpt`
- loss csv: `Code/Diffusion_model/Save/training_losses.csv`, `validation_losses.csv`

## Git 与协作 | Git Workflow
基础同步：
```powershell
git pull
git add .
git commit -m "your message"
git push
```

当前远程仓库：
- `https://github.com/htqh06/StageHtqh06.git`

## Notes
- 数据、模型权重、日志默认被忽略，不会自动推送到 GitHub。
- 若需共享训练数据，请使用网盘/对象存储，并在 README 中补充下载说明。
