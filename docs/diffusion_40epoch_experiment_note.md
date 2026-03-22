# Diffusion 40-Epoch Experiment Note

## 1. 实验目的

本次实验的目标是：

- 复现 `Code/Diffusion_model` 下的三变量 diffusion pipeline
- 先训练到 `20` 个 epoch，确认训练是否正常
- 继续训练到 `40` 个 epoch，判断是否仍有明显收益
- 对比 `epoch 19` 和 `epoch 39` 的 guided sampling 实际效果，而不是只看 loss


## 2. 相关文件

- 训练脚本：`Code/Diffusion_model/diff_3var_fast64.py`
- 数据集定义：`Code/Diffusion_model/Dataset_3var.py`
- 曲线绘图脚本：`Code/Diffusion_model/plot_losses.py`
- checkpoint 对比脚本：`Code/Diffusion_model/compare_checkpoints.py`
- 训练曲线：`Code/Diffusion_model/Save/loss_curves_40_clean.png`
- 指标表：`Code/Diffusion_model/Save/checkpoint_comparison_metrics.csv`
- checkpoint 对比图：`Code/Diffusion_model/Save/checkpoint_comparison_2020-02-12.png`


## 3. 数据与训练设置

### 3.1 数据

训练数据来自：

- `data/Copernicus_processed_data/so_*`
- `data/Copernicus_processed_data/thetao_*`
- `data/Copernicus_processed_data/zos_*`

当前 diffusion 实际使用的训练集配置为：

- `n_files = 37`
- `l_files = 256`
- 总训练样本数：`37 * 256 = 9472`

单个样本为三通道 patch：

- channel 0: `so` (SSS)
- channel 1: `thetao` (SST)
- channel 2: `zos` (SSH)

patch 尺寸为：

- `64 x 64`


### 3.2 模型与训练超参数

本次训练使用的关键配置：

- 模型：`UNet2DModel`
- `sample_size = 64`
- `in_channels = 3`
- `out_channels = 3`
- `n_ch = 128`
- `batch size = 8`
- `accumulate_grad_batches = 8`
- `precision = 16-mixed`

损失定义：

- 训练损失：`L1(pred_noise, noise)`
- 验证损失：`MSE(pred_noise, noise)`

注意：

- `train loss` 和 `val loss` 不是同一种指标
- 因此两条曲线的绝对数值不能直接比较高低


## 4. 验证集协议调整

在训练到 `20` epoch 之后，对验证逻辑做了两个修正：

1. 将验证集从“单个随机 crop”改为“固定 5 个 crop”
2. 关闭 Lightning 的 `sanity validation`

新的 5 个验证窗口为：

- 左上：`(0, 0)`
- 右上：`(0, 67)`
- 左下：`(60, 0)`
- 右下：`(60, 67)`
- 中心：`(30, 33)`

这意味着：

- `epoch 1-20` 的验证结果，和 `epoch 21-40` 的验证结果，不是完全同一个验证协议
- 因此整条 `val` 曲线可以看趋势，但不适合做严格的绝对值横向比较


## 5. 训练结果概览

### 5.1 1 到 40 epoch 的总体表现

`train loss` 关键节点：

- epoch 1: `0.2026108950`
- epoch 5: `0.0985844433`
- epoch 10: `0.0928392112`
- epoch 20: `0.0902656168`
- epoch 40: `0.0871940404`

`val loss` 关键节点：

- epoch 1: `0.0665637255`
- epoch 5: `0.0378291234`
- epoch 10: `0.0322727114`
- epoch 20: `0.0288102869`
- epoch 40: `0.0210281778`


### 5.2 降幅分析

`train loss` 降幅：

- epoch `1 -> 5`：`0.104026`
- epoch `1 -> 10`：`0.109772`
- epoch `1 -> 20`：`0.112345`
- epoch `20 -> 40`：`0.003072`

结论：

- 前 `5` 个 epoch 学到的大头最多
- `10-20` epoch 仍有收益，但明显变慢
- `20-40` epoch 已经进入平台期，只剩小幅微调


## 6. 是否存在“过早收敛”

综合 loss 和实际采样结果，本次实验的判断是：

- 训练过程本身是正常的
- 没有出现明显发散
- 没有出现典型的 train 持续下降、val 持续恶化的过拟合形态

但同时：

- 模型确实比较早进入有效收敛区间
- 从 loss 角度看，`20` epoch 之后边际收益已经明显变小

因此更准确的说法不是“5 个 epoch 就完全收敛”，而是：

- `1-5` epoch：快速学习主要模式
- `5-20` epoch：继续优化
- `20` epoch 之后：进入平台期


## 7. Checkpoint 实际效果对比

### 7.1 对比对象

- `epoch19`: `Code/Diffusion_model/Save/lightning_logs/version_2/checkpoints/epoch=19-step=2960.ckpt`
- `epoch39`: `Code/Diffusion_model/Save/lightning_logs/version_4/checkpoints/epoch=39-step=5920.ckpt`


### 7.2 测试样本说明

本次对比主要可视化样本为：

- `test index 42`

由于 test 集对应 `2020` 全年，且索引从 `0` 开始，因此：

- `test index 42 = 2020-02-12`

可视化图像文件：

- `Code/Diffusion_model/Save/checkpoint_comparison_2020-02-12.png`

本次 guided sampling 对比中固定使用：

- crop: `(r1, r2) = (30, 33)`
- `num_timesteps = 50`


### 7.3 单次对比结果

对 3 个测试样本做单 seed 对比后的平均结果：

| Checkpoint | Overall MSE | SSS MSE | SST MSE | SSH MSE | SSS low-res MSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| epoch19 | `0.0005625` | `0.0014779` | `0.0001406` | `0.0000691` | `0.0000601` |
| epoch39 | `0.0006174` | `0.0016536` | `0.0001337` | `0.0000649` | `0.0000603` |

解读：

- `epoch39` 在 `SST` 和 `SSH` 上略好
- `epoch19` 在 `SSS` 和 overall MSE 上更好
- 对真正更关键的 `SSS` 高频恢复，`epoch39` 没有体现出稳定优势


### 7.4 多 seed 稳定性结果

又对 `3` 个测试样本、`3` 组随机 seed 做了更稳的统计：

`epoch19`：

- overall MSE mean: `0.0007147`
- SSS MSE mean: `0.0019253`
- SST MSE mean: `0.0001468`
- SSH MSE mean: `0.0000721`

`epoch39`：

- overall MSE mean: `0.0011835`
- SSS MSE mean: `0.0033416`
- SST MSE mean: `0.0001414`
- SSH MSE mean: `0.0000675`

解读：

- `epoch39` 在 `SST/SSH` 上仍然略优
- 但在 `SSS` 上明显更差，而且波动更大
- 说明继续训练到 `40` epoch 后，模型在 guided sampling 中对 `SSS` 的先验约束并没有更稳


## 8. 最终结论

本次实验的结论可以概括为：

1. diffusion 训练是正常的
2. 模型收敛较快，但不是异常快
3. `20` epoch 左右已经进入比较有效的收敛区间
4. 从 `20 -> 40` epoch，loss 仍有小幅改进，但 guided sampling 实际收益不稳定
5. 对当前任务来说，继续单纯增加 epoch 不一定是最优方向

因此，现阶段更推荐把：

- `epoch19` 作为一个强基线 checkpoint

后续优化优先级建议为：

1. 继续完善验证协议
2. 统一记录 train/val 的同口径指标
3. 调整 guided sampling 中的 guidance 强度与策略
4. 再考虑是否需要继续增加训练 epoch


## 9. 建议后续工作

建议优先做以下几件事：

1. 增加 `train_mse` 和 `val_l1` 记录，避免只看异构 loss
2. 对比 `epoch19` 和 `epoch39` 的误差图，而不是只看数值
3. 调整 `guided_sampling_3var.py` 中 guidance 超参数，尤其关注 `SSS` 高频恢复
4. 如果要继续长期训练，建议先明确“loss 更低”和“最终重建更好”是否真的一致
