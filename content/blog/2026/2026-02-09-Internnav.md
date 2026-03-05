---
title: "InternNav复现"
---

### 配置环境
在L40环境下重新安装：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆仓库（保持不变，--recursive 拉取子模块）
git clone https://github.com/InternRobotics/InternNav.git --recursive
cd InternNav

conda create -n internnav python=3.10 libxcb=1.14
conda activate internnav

# install PyTorch (CUDA 11.8)
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cu118

# install InternNav with model dependencies
pip install setuptools_scm wheel setuptools --upgrade
# 先装 flash_attn 构建期会 import / 用到的依赖
pip install -U "setuptools>=70.1" wheel ninja psutil
# 记得先给远程服务器装 rsync
apt update && apt install -y rsync
# 然后本机直接传过去
rsync -avz -e "ssh -p 30229" ./flash_attn-2.7.2.post1+cu11torch2.5cxx11abiFALSE-cp310-cp310-linux_x86_64.whl root@120.209.70.195:/root/

pip install flash_attn-2.7.2.post1+cu11torch2.5cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
# 再装 InternNav
pip install -e .[model] --no-build-isolation
```

先直接复用gpufree平台的Habitat镜像，可以看到官方文档的要求是：
- Python 3.9
- Pytorch 2.6.0
- CUDA 12.4
- GPU: NVIDIA A100 or higher (optional for VLA training)
- Habitat-sim & Habitat-lab 0.2.4
```bash
(habitat) root@gpufree-container:~/gpufree-data/InternNav# python --version
Python 3.9.23
(habitat) root@gpufree-container:~/gpufree-data/InternNav# python -c "import habitat_sim; print('habitat-sim 版本:', habitat_sim.__version__)"
habitat-sim 版本: 0.2.5
(habitat) root@gpufree-container:~/gpufree-data/InternNav# python -c "import habitat; print('habitat-lab 版本:', habitat.__version__)"
Gym has been unmaintained since 2022 and does not support NumPy 2.0 amongst other critical functionality.
Please upgrade to Gymnasium, the maintained drop-in replacement of Gym, or contact the authors of your software and request that they upgrade.
See the migration guide at https://gymnasium.farama.org/introduction/migration_guide/ for additional information.
habitat-lab 版本: 0.2.5
(habitat) root@gpufree-container:~/gpufree-data/InternNav# python -c "import torch; print('PyTorch版本:', torch.__version__)"
PyTorch版本: 2.8.0+cu128
(habitat) root@gpufree-container:~/gpufree-data/InternNav# python -c "import torch; print('CUDA是否可用:', torch.cuda.is_available()); print('PyTorch绑定的CUDA版本:', torch.version.cuda)"
CUDA是否可用: True
PyTorch绑定的CUDA版本: 12.8
```

### 测试Habitat r2r
先下载数据集，这里我们就先用Habitat，并选用最轻量的v0.1-mini分支（因为更大的分支就要超过200GB我就要花钱买存储了）：
| 数据类别 | 仓库 | 必要分量 | 大小 | 用途 |
| --- | --- | --- | --- | --- |
| 轨迹数据 | InternRobotics/InternData-N1 | vln_ce/** | ~23.6 GB | Habitat 上的 VLN-CE 任务（含 System2 评估） |
| 场景资产 | InternRobotics/Scene-N1 | mp3d_ce.tar.gz | ~16 GB | Habitat 仿真场景（Matterport3D） |
| 模型权重 | InternRobotics/InternVLA-N1-w-NavDP（或相关） | 全部 | ~16 GB | 双系统模型（System2+System1） |

```bash
export HF_ENDPOINT=https://hf-mirror.com
./hfd.sh InternRobotics/Scene-N1 \
    --dataset \
    --include "mp3d_ce.tar.gz" \
    --hf_username "your_username" \
    --hf_token "hf_xxxxxxxxxxxxxxxxxx" \
    --local-dir ./Scene-N1
./hfd.sh InternRobotics/InternData-N1 \
    --dataset \
    --revision v0.1-mini \
    --include "vln_ce/**" \
    --local-dir ./InternData-N1 \
    --hf_username your_username \
    --hf_token your_token
# 解压场景数据集
tar -zxvf mp3d_ce.tar.gz

```
可以看到，v0.1-mini的分支只包含r2r。

试了一下Habitat环境还是得重新装一遍：
```bash
conda create -n hab python=3.9
conda activate hab
conda install habitat-sim==0.2.4 withbullet headless -c conda-forge -c aihabitat
git clone --branch v0.2.4 https://github.com/facebookresearch/habitat-lab.git
cd habitat-lab
pip install -e habitat-lab  # install habitat_lab
pip install -e habitat-baselines # install habitat_baselines
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
cd ../InternNav
pip install ./flash_attn-2.7.4.post1+cu12torch2.6cxx11abiFALSE-cp39-cp39-linux_x86_64.whl
pip install -e .[habitat] --no-build-isolation
```

现在可以跑了，这里我们使用[InternVLA-N1-DualVLN](https://huggingface.co/InternRobotics/InternVLA-N1-DualVLN)的权重在r2r上进行双系统评估
```bash
python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_cfg.py
```
L40上大概单卡跑25h38min，显存占用24000MB以内。
```bash
Eval Epoch 0 Rank 0:  67%|████████████████████████████████████████████████████████████████████████████████████████▉                                            | 1230/1839 [14:20:01<3:57:09, 23.37s/it][12:56:34.541086] scene_episode Z6MFQCViBuw_1659 success: 1.0, spl: 0.915552915929419, os: 1.0, ne: 0.06489334255456924
[12:56:36.474658] episode start Go down the path on the left towards the large dining room. Enter and go down the red carpet on the right side of the room, stopping at the door leading into another room. 
[12:56:36.700972] step_id: 0 output text: ↓
[12:56:36.701063] actions [5]
[12:56:36.701105] step_id 0 action 5
[12:56:37.242942] step_id: 0 output text: 303 186
[12:56:37.935475] predicted goal [186, 303]
[12:56:37.935538] step_id 0 action 3
[12:56:38.039915] step_id 1 action 3
[12:56:38.147404] step_id 2 action 3
[12:56:38.259146] step_id 3 action 1
[12:56:38.624357] local_actions [1, 1, 2, 1]
[12:56:38.624416] step_id 4 action 1
[12:56:38.726116] step_id 5 action 1
[12:56:38.838516] step_id 6 action 2
[12:56:38.954433] step_id 7 action 1
[12:56:39.327402] local_actions [2, 1, 1, 2]
[12:56:40.001080] step_id: 9 output text: ←←
[12:56:40.001175] actions [2, 2]
[12:56:40.001218] step_id 9 action 2
[12:56:40.113763] step_id 10 action 2
[12:56:41.012306] step_id: 11 output text: ↓
[12:56:41.012415] actions [5]
[12:56:41.012456] step_id 11 action 5
[12:56:42.518175] step_id: 11 output text: 190 188
[12:56:43.615070] predicted goal [188, 190]
[12:56:43.615151] step_id 11 action 1
[12:56:43.727561] step_id 12 action 2
[12:56:43.843558] step_id 13 action 1
[12:56:43.957890] step_id 14 action 1
[12:56:44.295122] local_actions [1, 1, 2, 1]
[12:56:44.295199] step_id 15 action 1
[12:56:44.407580] step_id 16 action 1
[12:56:44.525595] step_id 17 action 2
[12:56:44.644094] step_id 18 action 1
[12:56:45.008275] local_actions [1, 1, 1, 1]
[12:56:45.794590] step_id: 20 output text: ↓
[12:56:45.794689] actions [5]
[12:56:45.794732] step_id 20 action 5
[12:56:47.261735] step_id: 20 output text: 340 178
[12:56:48.264287] predicted goal [178, 340]
[12:56:48.264363] step_id 20 action 1
[12:56:48.380687] step_id 21 action 1
[12:56:48.497173] step_id 22 action 3
[12:56:48.613465] step_id 23 action 1
[12:56:48.947505] local_actions [1, 1, 2, 1]
[12:56:48.947570] step_id 24 action 1
[12:56:49.053366] step_id 25 action 1
[12:56:49.161661] step_id 26 action 2
[12:56:49.277904] step_id 27 action 1
[12:56:49.640776] local_actions [1, 1, 1, 1]
[12:56:50.549755] step_id: 29 output text: ↓
[12:56:50.549844] actions [5]
[12:56:50.549884] step_id 29 action 5
[12:56:51.814697] step_id: 29 output text: 326 170
[12:56:52.895622] predicted goal [170, 326]
[12:56:52.895699] step_id 29 action 1
[12:56:53.013051] step_id 30 action 1
[12:56:53.130480] step_id 31 action 1
[12:56:53.240816] step_id 32 action 1
[12:56:53.564363] local_actions [1, 1, 1, 1]
[12:56:53.564429] step_id 33 action 1
[12:56:53.668916] step_id 34 action 1
[12:56:53.771155] step_id 35 action 1
[12:56:53.878551] step_id 36 action 1
[12:56:54.252163] local_actions [1, 1, 1, 1]
[12:56:55.200071] step_id: 38 output text: ↓
[12:56:55.200173] actions [5]
[12:56:55.200216] step_id 38 action 5
[12:56:56.362000] step_id: 38 output text: 461 192
[12:56:57.602518] predicted goal [192, 461]
[12:56:57.602590] step_id 38 action 1
[12:56:57.720162] step_id 39 action 1
[12:56:57.838709] step_id 40 action 1
[12:56:57.951833] step_id 41 action 3
[12:56:58.288404] local_actions [1, 1, 3, 1]
[12:56:58.288465] step_id 42 action 1
[12:56:58.392835] step_id 43 action 1
[12:56:58.496285] step_id 44 action 3
[12:56:58.599396] step_id 45 action 1
[12:56:58.964277] local_actions [1, 1, 1, 1]
[12:56:59.750044] step_id: 47 output text: ↓
[12:56:59.750138] actions [5]
[12:56:59.750180] step_id 47 action 5
[12:57:01.110274] step_id: 47 output text: 378 182
[12:57:02.199320] predicted goal [182, 378]
[12:57:02.199384] step_id 47 action 1
[12:57:02.300812] step_id 48 action 3
[12:57:02.400004] step_id 49 action 1
[12:57:02.500297] step_id 50 action 1
[12:57:02.817614] local_actions [1, 1, 1, 1]
[12:57:02.817672] step_id 51 action 1
[12:57:02.917863] step_id 52 action 1
[12:57:03.017076] step_id 53 action 1
[12:57:03.116799] step_id 54 action 1
[12:57:03.433189] local_actions [1, 1, 2, 1]
[12:57:04.056655] step_id: 56 output text: ↓
[12:57:04.056751] actions [5]
[12:57:04.056791] step_id 56 action 5
[12:57:05.104714] step_id: 56 output text: 153 200
[12:57:06.171620] predicted goal [200, 153]
[12:57:06.171693] step_id 56 action 1
[12:57:06.277197] step_id 57 action 1
[12:57:06.389925] step_id 58 action 1
[12:57:06.506230] step_id 59 action 2
[12:57:06.850964] local_actions [1, 2, 1, 1]
[12:57:06.851045] step_id 60 action 1
[12:57:06.964593] step_id 61 action 2
[12:57:07.079851] step_id 62 action 1
[12:57:07.198388] step_id 63 action 1
[12:57:07.567827] local_actions [1, 1, 1, 1]
[12:57:08.303806] step_id: 65 output text: ↓
[12:57:08.303896] actions [5]
[12:57:08.303940] step_id 65 action 5
[12:57:09.710926] step_id: 65 output text: 258 167
[12:57:10.791876] predicted goal [167, 258]
[12:57:10.791951] step_id 65 action 1
[12:57:10.909473] step_id 66 action 1
[12:57:11.023748] step_id 67 action 2
[12:57:11.130843] step_id 68 action 1
[12:57:11.481141] local_actions [1, 1, 1, 3]
[12:57:11.481203] step_id 69 action 1
[12:57:11.598766] step_id 70 action 1
[12:57:11.712944] step_id 71 action 1
[12:57:11.826639] step_id 72 action 3
[12:57:12.156299] local_actions [1, 1, 2, 1]
[12:57:12.925022] step_id: 74 output text: ↓
[12:57:12.925116] actions [5]
[12:57:12.925158] step_id 74 action 5
[12:57:14.435768] step_id: 74 output text: 273 158
[12:57:15.453423] predicted goal [158, 273]
[12:57:15.453499] step_id 74 action 1
[12:57:15.565128] step_id 75 action 1
[12:57:15.681188] step_id 76 action 1
[12:57:15.797470] step_id 77 action 2
[12:57:16.131290] local_actions [1, 1, 1, 3]
[12:57:16.131362] step_id 78 action 1
[12:57:16.246393] step_id 79 action 1
[12:57:16.362671] step_id 80 action 1
[12:57:16.476910] step_id 81 action 3
[12:57:16.841838] local_actions [1, 2, 1, 3]
[12:57:17.504574] step_id: 83 output text: ↓
[12:57:17.504670] actions [5]
[12:57:17.504711] step_id 83 action 5
[12:57:19.062974] step_id: 83 output text: 270 180
[12:57:20.139053] predicted goal [180, 270]
[12:57:20.139135] step_id 83 action 1
[12:57:20.250935] step_id 84 action 1
[12:57:20.369112] step_id 85 action 2
[12:57:20.485345] step_id 86 action 1
[12:57:20.814544] local_actions [1, 1, 3, 1]
[12:57:20.814600] step_id 87 action 1
[12:57:20.915530] step_id 88 action 1
[12:57:21.014032] step_id 89 action 3
[12:57:21.114450] step_id 90 action 1
[12:57:21.430977] local_actions [1, 2, 1, 3]
[12:57:22.052870] step_id: 92 output text: STOP
[12:57:22.052962] actions [0]
[12:57:22.053003] step_id 92 action 0
...
[00:14:27.035234] {'sucs_all': 0.6432843804359436, 'spls_all': 0.5849772584175172, 'oss_all': 0.7020119428634644, 'nes_all': 4.159605979919434, 'length': 1839}
```
> 可惜的是没有保存r2r的视频，不过我可以拿NaVILA已经跑过的视频来做，反正最终的纸质论文没法放视频只有答辩PPT能放

当然与此同时也可以看一看[System2](https://huggingface.co/InternRobotics/InternVLA-N1-System2)的单系统评估，他们说只在Habitat上能评估。
```bash
python scripts/eval/eval.py --config scripts/eval/configs/habitat_s2_cfg.py
```

```bash
Eval Epoch 0 Rank 0:   0%|                                                                                                                                          | 1/1839 [00:51<26:06:24, 51.13s/it][12:57:02.209476] scene_episode 2azQ1b91cZZ_0010 success: 0.0, spl: 0.0, os: 0.0, ne: 7.522266387939453
[12:57:04.391371] episode start Walk across the floor and wait the archway. 
[12:57:04.962178] step_id: 0 output text: ←←←←
[12:57:04.962280] actions [2, 2, 2, 2]
[12:57:04.962319] step_id 0 action 2
[12:57:05.005421] step_id 1 action 2
[12:57:05.046796] step_id 2 action 2
[12:57:05.087511] step_id 3 action 2
[12:57:05.993363] step_id: 4 output text: ←←←←
[12:57:05.993457] actions [2, 2, 2, 2]
[12:57:05.993497] step_id 4 action 2
[12:57:06.034692] step_id 5 action 2
[12:57:06.074602] step_id 6 action 2
[12:57:06.114007] step_id 7 action 2
[12:57:06.707244] step_id: 8 output text: ↓
[12:57:06.707332] actions [5]
[12:57:06.707372] step_id 8 action 5
[12:57:07.629644] step_id: 8 output text: 256 443
[12:57:07.655972] depth:  1.4581169
[12:57:07:656188]:[Scene] SceneGraph.h(85)::createDrawableGroup : Created DrawableGroup: 
[12:57:07.657698] predicted goal [443, 256] [15.84575826  0.12711     9.61763945]
[12:57:07.659354] step_id 8 action 2
[12:57:07.701546] step_id 9 action 1
[12:57:07.741870] step_id 10 action 1
[12:57:07.782021] step_id 11 action 1
[12:57:08.901476] step_id: 13 output text: →→→→
[12:57:08.901590] actions [3, 3, 3, 3]
[12:57:08.901632] step_id 13 action 3
[12:57:08.946134] step_id 14 action 3
[12:57:08.989732] step_id 15 action 3
[12:57:09.031993] step_id 16 action 3
[12:57:10.177588] step_id: 17 output text: →→→→
[12:57:10.177696] actions [3, 3, 3, 3]
[12:57:10.177741] step_id 17 action 3
[12:57:10.219636] step_id 18 action 3
[12:57:10.261334] step_id 19 action 3
[12:57:10.303717] step_id 20 action 3
[12:57:11.072758] step_id: 21 output text: ↓
[12:57:11.072877] actions [5]
[12:57:11.072952] step_id 21 action 5
[12:57:12.015256] step_id: 21 output text: 475 178
[12:57:12.040446] depth:  3.7984524
[12:57:12.042191] predicted goal [178, 475] [16.49921615  0.12711     5.63920579]
[12:57:12.043906] step_id 21 action 3
[12:57:12.084968] step_id 22 action 1
[12:57:12.126217] step_id 23 action 3
[12:57:12.165142] step_id 24 action 1
[12:57:12.204855] step_id 25 action 1
[12:57:12.244786] step_id 26 action 1
[12:57:12.286734] step_id 27 action 1
[12:57:12.328357] step_id 28 action 1
[12:57:13.302557] step_id: 30 output text: ↓
[12:57:13.302677] actions [5]
[12:57:13.302729] step_id 30 action 5
[12:57:14.937414] step_id: 30 output text: 250 170
[12:57:14.967908] depth:  3.9814386
[12:57:14.969725] predicted goal [170, 250] [16.57842393  0.12711     4.18441698]
[12:57:14.971493] step_id 30 action 2
[12:57:15.014726] step_id 31 action 1
[12:57:15.056536] step_id 32 action 1
[12:57:15.099899] step_id 33 action 1
[12:57:15.141585] step_id 34 action 1
[12:57:15.184480] step_id 35 action 1
[12:57:15.227440] step_id 36 action 1
[12:57:15.269636] step_id 37 action 1
[12:57:15.884857] step_id: 39 output text: ↓
[12:57:15.884958] actions [5]
[12:57:15.884998] step_id 39 action 5
[12:57:16.844002] step_id: 39 output text: 348 168
[12:57:16.868899] depth:  4.024705
[12:57:16.869345] predicted goal [168, 348] [16.57777728  0.12711     2.43756448]
[12:57:16.869770] step_id 39 action 1
[12:57:16.909839] step_id 40 action 1
[12:57:16.950076] step_id 41 action 1
[12:57:16.989873] step_id 42 action 1
[12:57:17.030111] step_id 43 action 1
[12:57:17.070731] step_id 44 action 1
[12:57:17.110957] step_id 45 action 1
[12:57:17.153010] step_id 46 action 1
[12:57:18.059398] step_id: 48 output text: ↓
[12:57:18.059499] actions [5]
[12:57:18.059540] step_id 48 action 5
[12:57:19.635234] step_id: 48 output text: 358 221
[12:57:19.665696] depth:  2.9823809
[12:57:19.666126] predicted goal [221, 358] [16.57808004  0.12711     1.63982851]
[12:57:19.666537] step_id 48 action 1
[12:57:19.708280] step_id 49 action 1
[12:57:19.751385] step_id 50 action 1
[12:57:19.793424] step_id 51 action 1
[12:57:19.836259] step_id 52 action 3
[12:57:19.878232] step_id 53 action 1
[12:57:19.920425] step_id 54 action 1
[12:57:19.961720] step_id 55 action 1
[12:57:20.579567] step_id: 57 output text: STOP
[12:57:20.579670] actions [0]
[12:57:20.579712] step_id 57 action 0
...
Eval Epoch 0 Rank 0: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1839/1839 [14:33:21<00:00, 28.49s/it]
[03:29:32.511116] {'sucs_all': 0.5976073741912842, 'spls_all': 0.5427737638377405, 'oss_all': 0.6780859231948853, 'nes_all': 4.314399719238281, 'length': 1839}
```
还有NavDP，即System1的评估，不知为何貌似只有Isaac（InternUtopia）可以，基线为Vision Navigation（无Language）的任务。


在这之后，我们下载用于SFT的InternData数据：
```
./../../gpufree-data/hfd.sh InternRobotics/InternData-N1 --dataset --revision v0.1-full --include "vln_ce/traj_data/r2r_v1-3/*" --local-dir . --hf_username your_username --hf_token your_token
```
这个比较小，只有 23.6 GB。拉下来的 `vln_ce/traj_data/r2r_v1-3/*` 本质上是“示范轨迹数据”（LeRobot 格式 episode），用于训练/微调（SFT/IL）导航模型，而不是从零开始预训练一个大模型。在 InternNav 的训练脚本里，System2 默认是从通用 VLM（`Qwen/Qwen2.5-VL-7B-Instruct`）起步再用这些轨迹做训练；Dual-System 阶段再用轨迹去训 System1（或联合微调）。
但是我比较担心，因为 2025/12/31 更新的 VLN-CE 新增 depth、robot pose、pixel-goal 标注、多视角观测来支持 DualVLN 训练，后面跑双系统训练/微调时可能遇到 “找不到 pose / 字段缺失” 之类问题，查看v0.1-mini分支的数据后果然Depth为空，遂还是从 334GB的 main 分支随机挑选几个数据下载下来。

在此基础之上，构建我们自己的数据集：

| 类别 | 数据集 | 核心来源/场景 | 在 NaVILA 中的用途 | 在 InternData-N1 中的对标/体现 |
|------|--------|----------------|---------------------|----------------------------------|
| 交集 | R2R | 经典室内模拟导航（离散指令） | 核心导航任务训练数据 | VLN-CE 子集的基础。InternData-N1 包含 R2R 数据，并将其转化为连续环境版本 (VLN-CE)，格式也更规范。 |
| 交集 | RxR | R2R 的多语言增强版 | 核心导航任务训练数据 | VLN-CE 子集的一部分。InternData-N1 同样包含对 RxR 数据的支持。 |
| 差集 | EnvDrop | R2R 的数据增强版本（模拟环境） | 提升模型在模拟环境中的鲁棒性 | 无直接对应。InternData-N1 通过其 VLN-CE (v1.3) 直接集成了最新的 R2R 官方数据，可能替代了 EnvDrop 的定位。 |
| (NaVILA 特有) | ScanQA | 三维视觉问答（3D VQA） | 增强模型的视觉语义理解和常识推理 | 无直接对应。InternData-N1 主要专注于导航轨迹数据，不包含此类的问答数据集。 |
| (NaVILA 特有) | Human | YouTube 真人导览视频 | 引入真实世界的复杂性和多样性，提升泛化能力 | 无直接对应。InternData-N1 主要通过模拟生成数据，但其 VLN-PE 子集引入了物理仿真和多种机器人形态，旨在缩小仿真到现实的差距。 |
| 差集 | VLN-PE | InternData-N1 自研，物理增强环境 | - | InternData-N1 的特有子集。在具有物理属性的仿真环境中评估导航，更接近真实机器人部署。 |
| (InternData 特有) | VLN-N1 | InternData-N1 自研，大规模合成数据 | - | 包含 4.94 TB 的 traj_data（3dfront/gibson/hm3d/hssd/matterport3d/replica 等场景的 d435i/zed 数据）。构建过程：① 基于多种开源场景通过运控合成轨迹；② 利用大模型生成/改写指令；③ 质量筛选（过滤约23%低质量数据）。最终包含超 5000 万帧图像、总里程 4839 公里。主要用于系统1 预训练，也用于双系统联合微调以增强泛化性。 |

接下来下载真实世界互联网第一视角视频，这里我们先下NaVILA的：
```bash
(habitat) root@gpufree-container:~/gpufree-share# ./../gpufree-data/hfd.sh a8cheng/NaVILA-Dataset --dataset --revision main --include "Human/*" --local-dir .
Fetching repo metadata...
Generating file list...
Starting download with aria2c to ....
 *** Download Progress Summary as of Mon Feb 23 15:24:35 2026 ***             
==============================================================================
[#29e52b 346MiB/403MiB(85%) CN:4 DL:7.2MiB ETA:7s]
FILE: Human/annotations.json
------------------------------------------------------------------------------

[#29e52b 401MiB/403MiB(99%) CN:2 DL:8.2MiB]                                   
Download Results:
gid   |stat|avg speed  |path/URI
======+====+===========+=======================================================
4dc595|OK  |    21KiB/s|Human/video_ids.txt
29e52b|OK  |   6.7MiB/s|Human/annotations.json

Status Legend:
(OK):download completed.
(habitat) root@gpufree-container:~/gpufree-share# sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:--  0:00:02 --:--:--     0
  0     0    0     0    0     0      0      0 --:--:--  0:00:02 --:--:--     0
100 3128k  100 3128k    0     0  16709      0  0:03:11  0:03:11 --:--:-- 24155
(habitat) root@gpufree-container:~/gpufree-share# sudo chmod a+rx /usr/local/bin/yt-dlp
```
注意yt-dlp需要大于python=3.10才能使用，然而遇到网络问题，遂查阅[代理配置指南](https://github.com/softdownloads/youtube-downloader/blob/main/%E4%BB%A3%E7%90%86%E9%85%8D%E7%BD%AE%E6%8C%87%E5%8D%97.md)，直接在服务器上装[代理](https://github.com/MetaCubeX/mihomo/releases)了:
```bash
wget https://github.com/MetaCubeX/mihomo/releases/download/v1.19.20/mihomo-linux-amd64-v1.19.20.gz
gunzip mihomo-linux-amd64-v1.19.20.gz
chmod +x mihomo-linux-amd64-v1.19.20
sudo mv mihomo-linux-amd64-v1.19.20 /usr/local/bin/mihomo
mihomo -v
mkdir -p /root/mihomo
touch /root/mihomo/config.yaml
# 粘贴进去订阅配置
mihomo -d /root/mihomo
# 启动!
```
然后在另一个终端：

```bash
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890
(hab) root@gpufree-container:~/gpufree-data/SocialNavSUB# curl -I https://www.google.com
HTTP/1.1 200 Connection established

HTTP/2 200 
content-type: text/html; charset=ISO-8859-1
content-security-policy-report-only: object-src 'none';base-uri 'self';script-src 'nonce-bKDnpy493TjQm_Lj-nLhKQ' 'strict-dynamic' 'report-sample' 'unsafe-eval' 'unsafe-inline' https: http:;report-uri https://csp.withgoogle.com/csp/gws/other-hp
reporting-endpoints: default="//www.google.com/httpservice/retry/jserror?ei=1hScaYfxEIzNkPIP8f_oyQ0&cad=crash&error=Page%20Crash&jsel=1&bver=2383&dpf=GSYMMWeul_Mry6hHReSwil5El0Y8lfPF8i3IwR7iVrw"
accept-ch: Sec-CH-Prefers-Color-Scheme
p3p: CP="This is not a P3P policy! See g.co/p3phelp for more info."
date: Mon, 23 Feb 2026 08:50:30 GMT
server: gws
x-xss-protection: 0
x-frame-options: SAMEORIGIN
expires: Mon, 23 Feb 2026 08:50:30 GMT
cache-control: private
set-cookie: AEC=AaJma5tq2hFy1j7xkHop3bOshoqR6xiU_8oL1rhoXvDNuiOd_qQ1mMm7Xg; expires=Sat, 22-Aug-2026 08:50:30 GMT; path=/; domain=.google.com; Secure; HttpOnly; SameSite=lax
set-cookie: NID=529=IHkh-swQdUUXRx0NLLDCHxENBUmigjjEUeV1r9vpLOrA_fpTxvsI3AJqbkY9j1WbI33WfqZeryq31nkWodtf-ZPC7rAKv-9gWnG8IXYOwidGTu7eS3CDWlwoxMRNVhOG3Vg3-GfojzEnADyLpEimAGJKlp9qh9m1QCzz_RUGOV1ESn8jhIjEe1N-g9S1zZ9p1-3YRL3wxlgsv3mFdfmB9jGhrh0ceQ; expires=Tue, 25-Aug-2026 08:50:30 GMT; path=/; domain=.google.com; HttpOnly
set-cookie: __Secure-BUCKET=CL8C; expires=Sat, 22-Aug-2026 08:50:30 GMT; path=/; domain=.google.com; Secure; HttpOnly
alt-svc: h3=":443"; ma=2592000,h3-29=":443"; ma=2592000
```
没问题。接下来试着下载一个YouTube：
```bash
(internnav) root@gpufree-container:~/gpufree-share# yt-dlp "https://www.youtube.com/watch?v=OaL6JVa9aJk"
[youtube] Extracting URL: https://www.youtube.com/watch?v=OaL6JVa9aJk
[youtube] OaL6JVa9aJk: Downloading webpage
WARNING: [youtube] No supported JavaScript runtime could be found. Only deno is enabled by default; to use another runtime add  --js-runtimes RUNTIME[:PATH]  to your command/config. YouTube extraction without a JS runtime has been deprecated, and some formats may be missing. See  https://github.com/yt-dlp/yt-dlp/wiki/EJS  for details on installing one
[youtube] OaL6JVa9aJk: Downloading android vr player API JSON
[info] OaL6JVa9aJk: Downloading 1 format(s): 299+251
[download] Destination: 4 Southam St, Ajax - Open House Video Tour [OaL6JVa9aJk].f299.mp4
[download] 100% of  266.27MiB in 00:00:27 at 9.81MiB/s
[download] Destination: 4 Southam St, Ajax - Open House Video Tour [OaL6JVa9aJk].f251.webm
[download] 100% of    9.02MiB in 00:00:01 at 8.50MiB/s
[Merger] Merging formats into "4 Southam St, Ajax - Open House Video Tour [OaL6JVa9aJk].mkv"
Deleting original file 4 Southam St, Ajax - Open House Video Tour [OaL6JVa9aJk].f251.webm (pass -k to keep)
Deleting original file 4 Southam St, Ajax - Open House Video Tour [OaL6JVa9aJk].f299.mp4 (pass -k to keep)
(internnav) root@gpufree-container:~/gpufree-share# ls -lh '4 Southam St, Ajax - Open House Video Tour [OaL6JVa9aJk].mkv'
-rw-r--r-- 1 root root 276M  2月 23 16:55 '4 Southam St, Ajax - Open House Video Tour [OaL6JVa9aJk].mkv'
```
这是一个 MKV 格式的视频文件，内容是 YouTube 上一个关于加拿大安大略省阿贾克斯市（Ajax）某处房产的 “开放日”导览视频。yt-dlp 先分别下载了视频部分（.f299.mp4，约 266MB）和音频部分（.f251.webm，约 9MB），然后调用 ffmpeg 将它们合并成一个完整的 MKV 文件。合并成功后自动删除了临时的视频和音频文件，只保留最终的 MKV。但是我们不需要音频文件，只保留 mp4 即可。
```bash
yt-dlp -f "bestvideo[ext=mp4]" --no-audio "https://www.youtube.com/watch?v=OaL6JVa9aJk" -o "%(id)s.mp4"
```

### 最小SFT测试
先迁移系统盘到数据盘，然后我们整个克隆数据盘到A100实例上，因为Training好像L40多卡也会OOM，而且文档也说最小也得A100：
```bash
(habitat) root@gpufree-container:~/gpufree-data/conda# conda config --add envs_dirs /root/gpufree-data/conda/envs
(habitat) root@gpufree-container:~/gpufree-data/conda# conda config --add pkgs_dirs /root/gpufree-data/conda/pkgs
(habitat) root@gpufree-container:~/gpufree-data/conda# conda config --show envs_dirs
envs_dirs:
  - /root/gpufree-data/conda/envs
  - /opt/conda/envs
  - /root/.conda/envs
(habitat) root@gpufree-container:~/gpufree-data/conda# conda create --prefix /root/gpufree-data/conda/envs/hab --clone hab
Retrieving notices: done
Source:      /opt/conda/envs/hab
Destination: /root/gpufree-data/conda/envs/hab
Packages: 107
Files: 45599

Downloading and Extracting Packages:
...
# 同理internnav环境
conda create --prefix /root/gpufree-data/conda/envs/internnav --clone internnav
# 然后删除老环境：
conda remove -p /opt/conda/envs/hab --all
conda remove -p /opt/conda/envs/internnav --all
```
在新A100实例里也加入一下：
```bash
conda config --add envs_dirs /root/gpufree-data/conda/envs
conda config --add envs_dirs /root/gpufree-data/conda/pkgs
```

### SocialNav-SUB上的测试
先前我已经完成了最轻量级的gpt5-nano和gemini，效果都出来了不太好，然而换成高级模型就表现很好，但是成本又高、延时又长。下面是对本地模型部署的实验：
直接跑DualVLN果然不行：
```bash
Warning: ('←←←←',) not in [('moving ahead',), ('turning left',), ('turning right',), ('moving ahead', 'turning left'), ('moving ahead', 'turning right'), ('turning left', 'turning right'), ('moving ahead', 'turning left', 'turning right')], will be marked as incorrect.
  2%|▊                                          | 1/51 [00:12<10:24, 12.49s/it]Warning: ←←←← not in ['ahead of', 'to the left of', 'to the right of', 'behind'], will be marked as incorrect.
  4%|█▋                                         | 2/51 [00:24<09:58, 12.21s/it]Warning: ←←←← not in ['ahead of', 'to the left of', 'to the right of', 'behind'], will be marked as incorrect.
  6%|██▌                                        | 3/51 [00:36<09:37, 12.02s/it]Warning: ←←←← not in ['closer to', 'further away from', 'about the same distance to'], will be marked as incorrect.
  8%|███▎                                       | 4/51 [00:48<09:23, 11.99s/it]Warning: ←←←← not in ['ahead of', 'to the left of', 'to the right of', 'behind'], will be marked as incorrect.
```
切换成System2也是一样。

#### NaVILA
```bash
python socialnavsub/evaluate_vlm.py --cfg_path config_navila.yaml
python socialnavsub/postprocess_results.py --cfg_path config_navila.yaml --experiment_folder experiment_6_navila_independent
```

```csv
baseline_model,method,prompt_image_type,Question/Category,VLM Probability of Agreement,VLM Probability of Agreement Std Error,VLM Weighted Probability of Agreement,VLM Weighted Probability of Agreement Std Error,Human Probability of Agreement,Human Probability of Agreement Std Error,Human Weighted Probability of Agreement,Human Weighted Probability of Agreement Std Error,Human Oracle Probability of Agreement,Human Oracle Probability of Agreement Std Error,Human Oracle Weighted Probability of Agreement,Human Oracle Weighted Probability of Agreement Std Error,Number of Samples,Experiment Folder
navila,independent,img_with_bev,All,0.34,0.0,0.5,0.01,0.6,0.0,0.8,0.0,0.74,0.0,1.0,0.0,4968,experiment_6_navila_independent
navila,independent,img_with_bev,Spatial reasoning,0.37,0.01,0.56,0.01,0.56,0.01,0.79,0.0,0.71,0.0,1.0,0.0,1317,experiment_6_navila_independent
navila,independent,img_with_bev,Spatiotemporal reasoning,0.34,0.01,0.52,0.01,0.59,0.01,0.8,0.0,0.73,0.01,1.0,0.0,858,experiment_6_navila_independent
navila,independent,img_with_bev,Social reasoning,0.32,0.01,0.47,0.01,0.62,0.0,0.81,0.0,0.76,0.0,1.0,0.0,2793,experiment_6_navila_independent
navila,independent,img_with_bev,q_robot_moving_direction,0.06,0.03,0.08,0.03,0.52,0.03,0.74,0.02,0.69,0.03,1.0,0.0,60,experiment_6_navila_independent
navila,independent,img_with_bev,q_person_spatial_position_begin,0.5,0.01,0.79,0.01,0.46,0.01,0.73,0.0,0.64,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_person_spatial_position_end,0.32,0.01,0.52,0.02,0.43,0.01,0.71,0.01,0.61,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_person_distance_change,0.47,0.01,0.75,0.02,0.46,0.01,0.74,0.0,0.63,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_goal_position_begin,0.75,0.03,0.94,0.02,0.68,0.03,0.85,0.01,0.8,0.02,1.0,0.0,60,experiment_6_navila_independent
navila,independent,img_with_bev,q_goal_position_end,0.69,0.03,0.9,0.03,0.62,0.02,0.82,0.01,0.77,0.02,1.0,0.0,60,experiment_6_navila_independent
navila,independent,img_with_bev,q_obstructing_path,0.26,0.01,0.36,0.02,0.73,0.01,0.88,0.0,0.83,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_obstructing_end_position,0.2,0.01,0.26,0.02,0.77,0.01,0.89,0.0,0.86,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_robot_affected,0.25,0.01,0.35,0.02,0.72,0.01,0.87,0.0,0.82,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_robot_action,0.6,0.01,0.88,0.01,0.5,0.01,0.74,0.01,0.67,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_person_affected,0.21,0.01,0.3,0.02,0.74,0.01,0.88,0.0,0.84,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_person_action,0.67,0.01,0.93,0.01,0.56,0.01,0.77,0.01,0.72,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_robot_suggested_affected,0.21,0.01,0.3,0.02,0.73,0.01,0.88,0.0,0.84,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_robot_suggested_action,0.15,0.01,0.26,0.01,0.53,0.01,0.75,0.01,0.7,0.01,1.0,0.0,399,experiment_6_navila_independent
navila,independent,img_with_bev,q_human_future_action_prediction,0.15,0.01,0.25,0.01,0.54,0.01,0.76,0.01,0.71,0.01,1.0,0.0,399,experiment_6_navila_independent
```
**表1：NaVILA 在 Socialnav-SUB 上的总体与分类表现**
| 问题/类别 | NaVILA 一致性 (加权) | 人类 一致性 (加权) | 样本数 | 表现分析 |
| :--- | :--- | :--- | :--- | :--- |
| **所有问题 (All)** | 0.50 | 0.80 | 4968 | **总体表现落后于人类**，加权后仍有0.30的差距。 |
| **空间推理 (Spatial)** | 0.56 | 0.79 | 1317 | 表现尚可，是三个推理类别中最好的，但仍低于人类。 |
| **时空推理 (Spatiotemporal)** | 0.52 | 0.80 | 858 | 表现中等，与人类差距明显。 |
| **社会推理 (Social)** | 0.47 | 0.81 | 2793 | **表现最弱**，是NaVILA的主要短板，与人类差距最大。 |

**表2：NaVILA 在具体问题上的表现分析**

| 问题类型 (Question/Category) | NaVILA 一致性 (加权) | 人类 一致性 (加权) | 样本数 | 表现分析 |
| :--- | :--- | :--- | :--- | :--- |
| **✅ 表现较好 (强于或接近人类)** | | | | |
| q_goal_position_begin | 0.94 | 0.85 | 60 | **远优于人类**，能精准识别目标起点位置。 |
| q_goal_position_end | 0.90 | 0.82 | 60 | **远优于人类**，能精准识别目标终点位置。 |
| q_person_action | 0.93 | 0.77 | 399 | **远优于人类**，非常擅长识别当前的人物动作。 |
| q_robot_action | 0.88 | 0.74 | 399 | **远优于人类**，非常擅长识别当前的机器人动作。 |
| q_person_distance_change | 0.75 | 0.74 | 399 | **与人类持平**，能准确判断人与机器人的距离变化。 |
| q_person_spatial_position_begin | 0.79 | 0.73 | 399 | **略优于人类**，对人物初始空间位置的判断较准。 |
| **❌ 表现较差 (远低于人类)** | | | | |
| q_robot_moving_direction | 0.08 | 0.74 | 60 | **极差**，几乎完全无法判断机器人的移动方向。 |
| q_obstructing_path | 0.36 | 0.88 | 399 | **很差**，难以理解机器人是否阻碍了行人路径。 |
| q_obstructing_end_position | 0.26 | 0.89 | 399 | **很差**，难以判断机器人是否阻碍了行人到达终点。 |
| q_robot_affected | 0.35 | 0.87 | 399 | **很差**，对机器人是否受行人影响的因果关系理解不足。 |
| q_person_affected | 0.30 | 0.88 | 399 | **很差**，对行人是否受机器人影响的因果关系理解不足。 |
| q_robot_suggested_affected | 0.30 | 0.88 | 399 | **很差**，无法推理建议动作带来的影响。 |
| q_robot_suggested_action | 0.26 | 0.75 | 399 | **很差**，难以给出合适的建议动作。 |
| q_human_future_action_prediction | 0.25 | 0.76 | 399 | **很差**，预测人类未来动作的能力非常弱。 |
| **⚠️ 表现中等** | | | | |
| q_person_spatial_position_end | 0.52 | 0.71 | 399 | **明显低于人类**，对人物终点位置的判断不如起点准确。 |

- **核心优势**：NaVILA在**静态空间感知**（如识别目标位置）和**明确的动作分类**（如“人/机器人在做什么”）上表现优异，甚至远超普通人类评估者。这与其设计目标——通过VLA模型进行中级空间推理——高度契合。
- **主要短板**：模型在**动态社交交互**、**因果关系推断**（谁影响了谁）、**路径阻碍判断**以及**未来动作预测**等复杂社会推理任务上显著落后于人类。这明确指向了当前VLA模型在社会智能和反事实推理方面的不足。
- **总体结论**：NaVILA的两级框架在将语言指令转化为具体的、基于空间理解的导航动作方面非常成功，但其**社会推理能力是其向更高级、更自然的社交导航发展的主要瓶颈**。未来的工作可能需要专门针对社会交互数据进行训练，或在模型中引入更强的因果推理和心智理论模块。


#### Qwen3-VL-8B-Instruct
```bash
python socialnavsub/evaluate_vlm.py --cfg_path config_qwen3vl.yaml
python socialnavsub/postprocess_results.py --cfg_path config_qwen3vl.yaml --experiment_folder experiment_8_qwen3vl_independent
```
Debug环境过程：
```bash
ValueError: The checkpoint you are trying to load has model type `qwen3_vl` but Transformers does not recognize this architecture. This could be because of an issue with the checkpoint, or because your version of Transformers is out of date.
(hab) root@gpufree-container:~/gpufree-data/SocialNavSUB# pip show transformers
Name: transformers
Version: 4.51.0
Summary: State-of-the-art Machine Learning for JAX, PyTorch and TensorFlow
Home-page: https://github.com/huggingface/transformers
Author: The Hugging Face team (past and future) with the help of all our contributors (https://github.com/huggingface/transformers/graphs/contributors)
Author-email: transformers@huggingface.co
License: Apache 2.0 License
Location: /opt/conda/envs/hab/lib/python3.9/site-packages
Requires: filelock, huggingface-hub, numpy, packaging, pyyaml, regex, requests, safetensors, tokenizers, tqdm
Required-by: 
# 先记录一下再升级，毕竟hab这个环境是用来跑r2r的Habitat仿真的。
pip install --upgrade transformers
```
依旧每个样本两个半小时。

#### GPT5-nano
**gpt-5-nano** 采用 **chain-of-thought (CoT)** 推理方法，输入图像包含鸟瞰图（BEV）。评估对比了模型与人类评估者在各类社交导航问题上的回答一致性（使用归一化概率作为加权指标，以反映人类判断的多样性）。

- **所有问题 (All)**：gpt-5-nano 加权一致性为 **0.697**，人类加权一致性为 **0.801**，模型略低于人类，但差距较 NaVILA 模型（0.50）有所缩小。
- 模型在部分任务上表现优异，甚至超越人类，但在社会推理相关问题上显著落后。

**表1：按推理类型划分的表现**

| 推理类型 | gpt-5-nano 加权一致性 | 人类加权一致性 | 样本数 |
| :--- | :--- | :--- | :--- |
| **所有问题 (All)** | 0.697 | 0.801 | 4968 |
| **空间推理 (Spatial)** | 0.763 | 0.803 | 1317 |
| **时空推理 (Spatiotemporal)** | 0.804 | 0.785 | 858 |
| **社会推理 (Social)** | 0.605 | 0.807 | 2793 |

- **时空推理**是模型的强项，表现甚至超过人类（0.804 > 0.785）。
- **空间推理**与人类接近（0.763 vs 0.803）。
- **社会推理**是主要短板，与人类差距明显（0.605 vs 0.807）。

**表2：按具体问题划分的表现**

| 问题类型 | gpt-5-nano 加权一致性 | 人类加权一致性 | 样本数 | 表现分析 |
| :--- | :--- | :--- | :--- | :--- |
| **✅ 表现优异 (超过或接近人类)** | | | | |
| q_robot_moving_direction | 0.853 | 0.742 | 60 | **显著优于人类**，精准判断机器人移动方向。 |
| q_goal_position_begin | 0.855 | 0.849 | 60 | **略优于人类**，精准识别目标起点位置。 |
| q_goal_position_end | 0.793 | 0.819 | 60 | 略低于人类，但差距微小（0.026）。 |
| q_person_spatial_position_begin | 0.750 | 0.735 | 399 | **略优于人类**，对人物初始空间位置判断准确。 |
| q_obstructing_end_position | 0.889 | 0.894 | 399 | 非常接近人类（差0.005）。 |
| q_obstructing_path | 0.848 | 0.878 | 399 | 略低于人类，但差距不大（0.03）。 |
| q_person_distance_change | 0.710 | 0.735 | 399 | 略低于人类，差距0.025。 |
| **❌ 表现较差 (显著低于人类)** | | | | |
| q_person_spatial_position_end | 0.529 | 0.715 | 399 | **大幅落后**，难以判断人物终点位置。 |
| q_robot_affected | 0.753 | 0.872 | 399 | 明显低于人类，对机器人是否受影响判断不足。 |
| q_robot_action | 0.609 | 0.736 | 399 | 显著落后，难以识别机器人当前动作。 |
| q_person_affected | 0.662 | 0.881 | 399 | **大幅落后**，对行人是否受影响理解差。 |
| q_person_action | 0.532 | 0.771 | 399 | **大幅落后**，难以识别行人当前动作。 |
| q_robot_suggested_affected | 0.689 | 0.879 | 399 | **显著落后**，无法推理建议动作带来的影响。 |
| q_robot_suggested_action | 0.528 | 0.748 | 399 | **大幅落后**，难以给出合适的建议动作。 |
| q_human_future_action_prediction | 0.460 | 0.759 | 399 | **最弱项**，预测人类未来动作的能力极差。 |

- **核心优势**：gpt-5-nano 在 **动态时空推理** 任务上表现突出，尤其擅长判断**机器人移动方向**和**目标位置**，这可能得益于 CoT 方法对时序信息的逐步推理能力。在部分静态空间感知任务上也接近或超过人类。
- **主要短板**：模型在 **社会交互理解** 方面存在系统性缺陷，包括：
  - 难以判断**谁影响了谁**（affected 类问题）。
  - 对**人物动作**的识别能力弱。
  - 无法准确**预测人类未来动作**。
  - 在**建议机器人应采取的行动**时表现不佳。
- **总体结论**：gpt-5-nano 在需要**时序动态推理**的任务上表现优异，但**社会智能**仍是其向高级社交导航发展的关键瓶颈。未来可通过引入社会交互数据、因果推理模块或结合专门的社会信号预训练来改进。

#### gemini-2.5-flash-lite
**gemini-2.5-flash-lite** 同样采用 CoT 推理，输入图像包含 BEV。

- **所有问题 (All)**：gemini 加权一致性为 **0.521**，人类加权一致性为 **0.743**，差距为 0.222。模型表现介于 NaVILA（0.50）和 gpt-5-nano（0.697）之间，但仍显著落后于人类。
- 模型在静态空间定位任务上表现优异，但在动态时空推理和社会交互理解上存在严重短板。

**表1：按推理类型划分的表现（样本数加权平均）**

| 推理类型 | gemini 加权一致性 | 人类加权一致性 | 样本数 |
| :--- | :--- | :--- | :--- |
| **所有问题 (All)** | 0.521 | 0.743 | 4968 |
| **空间推理 (Spatial)** | 0.605 | 0.712 | 1317 |
| **时空推理 (Spatiotemporal)** | 0.467 | 0.728 | 858 |
| **社会推理 (Social)** | 0.359 | 0.758 | 2793 |

- **空间推理**相对较好，但仍低于人类（差距 0.107）。
- **时空推理**显著落后于人类（差距 0.261），模型难以处理动态变化（如距离变化、路径阻碍）。
- **社会推理**是主要短板，与人类差距最大（差距 0.399），甚至低于 NaVILA 的社会推理分数（0.47）。

**表2：按具体问题划分的表现**

| 问题类型 | gemini 加权一致性 | 人类加权一致性 | 样本数 | 表现分析 |
| :--- | :--- | :--- | :--- | :--- |
| **✅ 表现优异（超过人类）** | | | | |
| q_goal_position_begin | 0.932 | 0.798 | 60 | **远超人类**，精准识别目标起点位置。 |
| q_goal_position_end | 0.912 | 0.769 | 60 | **远超人类**，精准识别目标终点位置。 |
| q_robot_moving_direction | 0.866 | 0.690 | 60 | **远超人类**，准确判断机器人移动方向。 |
| q_person_spatial_position_begin | 0.776 | 0.639 | 399 | **明显优于人类**，对人物初始空间位置判断准确。 |
| **⚠️ 表现中等（略低于人类）** | | | | |
| q_person_spatial_position_end | 0.534 | 0.613 | 399 | 略低于人类，判断人物终点位置能力较弱。 |
| q_person_distance_change | 0.470 | 0.633 | 399 | 明显低于人类，难以判断距离变化。 |
| **❌ 表现极差（远低于人类）** | | | | |
| q_obstructing_path | 0.404 | 0.829 | 399 | **极差**，无法理解机器人是否阻碍行人路径。 |
| q_obstructing_end_position | 0.408 | 0.863 | 399 | **极差**，难以判断机器人是否阻碍行人到达终点。 |
| q_robot_affected | 0.377 | 0.823 | 399 | **极差**，对机器人是否受行人影响的因果关系理解不足。 |
| q_robot_action | 0.320 | 0.675 | 399 | **极差**，难以识别机器人当前动作。 |
| q_person_affected | 0.460 | 0.837 | 399 | **极差**，对行人是否受机器人影响判断严重不足。 |
| q_person_action | 0.426 | 0.719 | 399 | **极差**，难以识别行人当前动作。 |
| q_robot_suggested_affected | 0.327 | 0.835 | 399 | **极差**，无法推理建议动作带来的影响。 |
| q_robot_suggested_action | 0.226 | 0.702 | 399 | **极差**，给出合适建议动作的能力非常弱。 |
| q_human_future_action_prediction | 0.379 | 0.712 | 399 | **极差**，预测人类未来动作的能力几乎为零。 |

- **核心优势**：gemini 在**静态空间定位**（如目标位置、人物起始位置、机器人移动方向）上表现卓越，远超普通人类评估者，表明其对空间布局和基本运动方向有很强的感知能力。
- **主要短板**：模型在**动态时空推理**（距离变化、路径阻碍）和**社会交互理解**（因果关系、意图预测、动作识别、建议生成）上存在系统性缺陷，所有涉及社会推理的问题得分均低于 0.46，与人类差距巨大。这反映模型缺乏对社交导航中隐含的社会规则、相互影响和未来行为的建模能力。
- **总体结论**：gemini-2.5-flash-lite 在基础空间感知任务上表现突出，但**社会智能是其向高级社交导航发展的致命瓶颈**。未来需通过引入专门的社会交互数据、因果推理模块或结合心智理论来显著提升模型在复杂社交场景下的表现。

### 真实世界实验计划
大概就这样分4类情况：
| 实验场景 | 场景描述与挑战 | 关键分析 |
| --- | --- | --- |
| 1. 狭窄通道 | 机器人需要穿过一条狭窄通道，而此时正好有人从对面走来。这需要机器人理解“礼让”或“靠右行”的社交规则。 | VLM能理解“狭窄”和“相向而行”的语境，做出靠边或等待的决策，而基线方法（尤其是DWA）可能会与人争夺路权或导致不安全交互。 |
| 2. 人群区域 | 机器人需要穿过一个有人聚集、聊天或走动的开放区域（例如休息区）。挑战在于找到一条不打扰人群的路径。 | VLM可以通过感知人群密度和分布，选择从人群边缘绕过，而不是从中间生硬穿过。 |
| 3. 跟随与引导 | 机器人可能需要跟随一个特定的人，或者在有人引导时跟随其后。这需要识别和理解“跟随”这一社交意图。 | VLM能够理解“跟随”的指令和人的行为，保持适当距离，而不是紧紧贴着人或跟丢。 |
| 4. 门廊交互 | 机器人需要经过一扇门，而此时有人正在开门、关门或准备通过。这需要理解对门的“使用权”和等待的社交礼仪。 | VLM能识别“门”和人的动作（如开门），判断出应该等待他人通过后再行动，而不是直接冲过去。 |

我觉得确实没有仿真也没关系，工作量放在造数据上就行。主要一个问题是怎么选择基线。Unitree Go2上的，可以运行的基线：
[Nav2 + DWB（DWA系）](https://docs.nav2.org/configuration/packages/configuring-dwb-controller.html?utm_source=chatgpt.com)、[LLM-Navigation（LLM + ROS2 导航）](https://yuzhong-chen.github.io/LLM-Navigation/)，如果可以的话加一个NaVILA，然后InternNav本身应该也是要进行的，到时候看情况指标。

最小4类指标应该包括：
- 成功率：是否完成任务（到达、穿门、跟随持续 T 秒等）
- 时间/路径长度：从开始到结束的时间、里程
- 最小人机距离 & 违规时长：例如 d < 0.8m 的时间占比（阈值你按场地/实验伦理定）
- 近碰/碰撞事件：用激光/深度点云的“极近距离持续触发”做事件检测，然后只对触发片段看视频确认（省非常多工）
跟随专属指标（强烈建议全自动）
- 距离误差：|d(t) - d_ref| 的均值/分位数
- 掉队率：目标丢失（tracking lost）次数、丢失总时长占比
- 跟随稳定性：速度/角速度变化率（jerk proxy），以及“频繁急停/急转”次数
- 重识别/切错人次数（如果你做“跟随特定的人”）：这个可以通过 target ID 是否切换来自动统计；不行的话再抽样视频标注
> 上面这些都不需要通看视频：关键是要记录/发布 目标人位姿（或相对位姿）。

也即
Success rate（Nav2 action）
Collision / near-collision rate（自动检测 + 抽查）
Time-to-goal、Path length（rosbag 自动算）
Min human distance + Proxemics violation time（基于人轨迹自动算）
用户主观评分

补充材料展示（最好每种方法每个场景挑 2–3 条“代表性片段”）
主观评分：舒适度、可预测性、安全感（给参与者看随机顺序的视频片段打分（Likert量表），并记录偏好排序——舒适/自然/可预测/安全感）视频在这里是实验材料，不是计数工具
> 最好能把Unitree Go2 EDU那玩意从峰达创意园带回来，连同充电设备一起。