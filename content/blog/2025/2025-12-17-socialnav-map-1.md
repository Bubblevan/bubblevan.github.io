---
slug: 2025-12-17-socialnav-map-1
title: 复现 SocialNav-Map
authors: [bubblevan]
tags: [socialnav, reproduction, habitat, dataset]
---

接下来复现 **SocialNav-Map**

```bash
source /etc/network_turbo
conda install -n base -c conda-forge mamba
~/miniconda3/bin/mamba install habitat-sim=0.3.1 withbullet headless -c conda-forge -c aihabitat
cd SocialNav-Map/Falcon
pip install -e habitat-lab -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -e habitat-baselines -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

然后是麻烦的**数据这一块**，在 **autodl** 一定要放在 **autodl-fs** 里
```bash
# 在 autodl-fs 里创建一个专门存放这个项目数据的文件夹
mkdir -p /root/autodl-fs/SocialNavData

# 建立软链接：把 autodl-fs 的文件夹映射到当前目录的 data
ln -s /root/autodl-fs/SocialNavData data

# 验证一下
ls -l data
# 输出应该显示 data -> /root/autodl-fs/SocialNavData
# 现在，往 Falcon/data 里下载的任何东西，实际上都会存进那是 200GB 的 autodl-fs 里，不用担心爆盘
```
然后经典 **libEGL.so.1 缺失**，habitat-sim 启动前找不到 EGL

```python
Traceback (most recent call last):
  File "/root/miniconda3/envs/falcon/lib/python3.9/runpy.py", line 188, in _run_module_as_main
    mod_name, mod_spec, code = _get_module_details(mod_name, _Error)
  File "/root/miniconda3/envs/falcon/lib/python3.9/runpy.py", line 111, in _get_module_details
    __import__(pkg_name)
  File "/root/miniconda3/envs/falcon/lib/python3.9/site-packages/habitat_sim-0.3.1-py3.9-linux-x86_64.egg/habitat_sim/__init__.py", line 13, in <module>
    import habitat_sim._ext.habitat_sim_bindings
ImportError: libEGL.so.1: cannot open shared object file: No such file or directory
```

虽然 **nvidia-smi** 显示驱动正常（这是内核层面的），但 Python 环境或系统缺少用户空间的 **EGL 接口库 (libEGL.so.1)**。

**libEGL.so.1** 通常是一个分发器（Dispatcher）。它的工作是指挥程序去调用真正的后端驱动（在你的情况下是 NVIDIA 驱动）。如果没有这个文件，程序就不知道如何去"握手"并调用显卡。

为了避免 fallback 到纯软件渲染，我们可以通过安装与厂商无关的调度库 **(GLVND)** 来解决。这不是 Mesa 软件渲染，而是让系统能正确识别并调用 NVIDIA 硬件的标准接口。

```bash
apt update && apt-get install -y libgl1 libglvnd0 libglx0 libegl1
```

安装 **libglvnd（GL Vendor-Neutral Dispatch）** 提供 libEGL.so.1，并会自动检测并使用 NVIDIA 驱动，不会强制变为 Mesa 软件渲染。此时我们再全局查找 `find / -name "libEGL.so*" 2>/dev/null` 就有了：

```bash
/usr/lib/x86_64-linux-gnu/libEGL.so.1
/usr/lib/x86_64-linux-gnu/libEGL.so.1.1.0
```

然后用 `python -m habitat_sim.utils.datasets_download --list` 查看数据源：
```
No data-path provided, defaults to: ./data. Use '--data-path' to specify another location.
Note, ./data is a symbolic link that points to /autodl-fs/data/SocialNavData.
====================================
Currently available datasources are:
------------------------------------
hssd-hab
hab3-episodes
hssd-raw
hssd-hab_internal
hssd-hab_objectnav_dataset
ai2thor-hab
procthor-hab_objectnav_dataset
habitat_test_scenes
habitat_test_pointnav_dataset
habitat_example_objects
locobot_merged
mp3d_example_scene
coda_scene
webxr_hand_demo
replica_cad_dataset
replica_cad_baked_lighting
ycb
franka_panda
hab_spot_arm
hab_stretch
hab_fetch
habitat_humanoids
rearrange_pick_dataset_v0
rearrange_dataset_v1
hab2_bench_assets
hab3_bench_assets
hm3d_minival_glb_v0.1
hm3d_minival_glb_v0.2
hm3d_minival_habitat_v0.1
hm3d_minival_habitat_v0.2
hm3d_minival_configs_v0.1
hm3d_minival_configs_v0.2
hm3d_train_glb_v0.1
hm3d_train_glb_v0.2
hm3d_train_habitat_v0.1
hm3d_train_habitat_v0.2
hm3d_train_configs_v0.1
hm3d_train_configs_v0.2
hm3d_val_glb_v0.1
hm3d_val_glb_v0.2
hm3d_val_habitat_v0.1
hm3d_val_habitat_v0.2
hm3d_val_configs_v0.1
hm3d_val_configs_v0.2
hm3d_example_glb
hm3d_example_habitat
hm3d_example_configs
hm3d_minival_semantic_annots_v0.1
hm3d_minival_semantic_annots_v0.2
hm3d_minival_semantic_configs_v0.1
hm3d_minival_semantic_configs_v0.2
hm3d_train_semantic_annots_v0.1
hm3d_train_semantic_annots_v0.2
hm3d_train_semantic_configs_v0.1
hm3d_train_semantic_configs_v0.2
hm3d_val_semantic_annots_v0.1
hm3d_val_semantic_annots_v0.2
hm3d_val_semantic_configs_v0.1
hm3d_val_semantic_configs_v0.2
hm3d_example_semantic_annots
hm3d_example_semantic_configs
====================================
Currently available datagroups are:
------------------------------------
('ci_test_assets', ['habitat_test_scenes', 'habitat_test_pointnav_dataset', 'habitat_example_objects', 'locobot_merged', 'mp3d_example_scene', 'coda_scene', 'replica_cad_dataset', 'hab_fetch', 'hab_stretch', 'hab_spot_arm', 'hm3d_example', 'hm3d_example_habitat', 'hm3d_example_configs', 'hm3d_example_semantic_annots', 'hm3d_example_semantic_configs'])
('rearrange_task_assets', ['replica_cad_dataset', 'hab_fetch', 'ycb', 'rearrange_pick_dataset_v0', 'rearrange_dataset_v1'])
('hm3d_example', ['hm3d_example_habitat', 'hm3d_example_configs', 'hm3d_example_semantic_annots', 'hm3d_example_semantic_configs'])
('hm3d_val_v0.1', ['hm3d_val_habitat_v0.1', 'hm3d_val_configs_v0.1', 'hm3d_val_semantic_annots_v0.1', 'hm3d_val_semantic_configs_v0.1'])
('hm3d_train_v0.1', ['hm3d_train_habitat_v0.1', 'hm3d_train_configs_v0.1', 'hm3d_train_semantic_annots_v0.1', 'hm3d_train_semantic_configs_v0.1'])
('hm3d_minival_v0.1', ['hm3d_minival_habitat_v0.1', 'hm3d_minival_configs_v0.1', 'hm3d_minival_semantic_annots_v0.1', 'hm3d_minival_semantic_configs_v0.1'])
('hm3d_semantics_v0.1', ['hm3d_example_semantic_annots_v0.1', 'hm3d_example_semantic_configs_v0.1', 'hm3d_val_semantic_annots_v0.1', 'hm3d_val_semantic_configs_v0.1', 'hm3d_train_semantic_annots_v0.1', 'hm3d_train_semantic_configs_v0.1', 'hm3d_minival_semantic_annots_v0.1', 'hm3d_minival_semantic_configs_v0.1'])
('hm3d_val_v0.2', ['hm3d_val_habitat_v0.2', 'hm3d_val_configs_v0.2', 'hm3d_val_semantic_annots_v0.2', 'hm3d_val_semantic_configs_v0.2'])
('hm3d_train_v0.2', ['hm3d_train_habitat_v0.2', 'hm3d_train_configs_v0.2', 'hm3d_train_semantic_annots_v0.2', 'hm3d_train_semantic_configs_v0.2'])
('hm3d_minival_v0.2', ['hm3d_minival_habitat_v0.2', 'hm3d_minival_configs_v0.2', 'hm3d_minival_semantic_annots_v0.2', 'hm3d_minival_semantic_configs_v0.2'])
('hm3d_semantics_v0.2', ['hm3d_example_semantic_annots_v0.2', 'hm3d_example_semantic_configs_v0.2', 'hm3d_val_semantic_annots_v0.2', 'hm3d_val_semantic_configs_v0.2', 'hm3d_train_semantic_annots_v0.2', 'hm3d_train_semantic_configs_v0.2', 'hm3d_minival_semantic_annots_v0.2', 'hm3d_minival_semantic_configs_v0.2'])
('hm3d_v0.1', ['hm3d_val_habitat_v0.1', 'hm3d_val_configs_v0.1', 'hm3d_val_semantic_annots_v0.1', 'hm3d_val_semantic_configs_v0.1', 'hm3d_train_habitat_v0.1', 'hm3d_train_configs_v0.1', 'hm3d_train_semantic_annots_v0.1', 'hm3d_train_semantic_configs_v0.1', 'hm3d_minival_habitat_v0.1', 'hm3d_minival_configs_v0.1', 'hm3d_minival_semantic_annots_v0.1', 'hm3d_minival_semantic_configs_v0.1'])
('hm3d_full', ['hm3d_minival_glb_v0.2', 'hm3d_minival_habitat_v0.2', 'hm3d_minival_configs_v0.2', 'hm3d_train_glb_v0.2', 'hm3d_train_habitat_v0.2', 'hm3d_train_configs_v0.2', 'hm3d_val_glb_v0.2', 'hm3d_val_habitat_v0.2', 'hm3d_val_configs_v0.2', 'hm3d_example_glb', 'hm3d_example_habitat', 'hm3d_example_configs', 'hm3d_minival_semantic_annots_v0.2', 'hm3d_minival_semantic_configs_v0.2', 'hm3d_train_semantic_annots_v0.2', 'hm3d_train_semantic_configs_v0.2', 'hm3d_val_semantic_annots_v0.2', 'hm3d_val_semantic_configs_v0.2', 'hm3d_example_semantic_annots', 'hm3d_example_semantic_configs'])
('hm3d_train_full', ['hm3d_train_glb_v0.2', 'hm3d_train_habitat_v0.2', 'hm3d_train_configs_v0.2', 'hm3d_train_semantic_annots_v0.2', 'hm3d_train_semantic_configs_v0.2'])
('hm3d_val_full', ['hm3d_val_glb_v0.2', 'hm3d_val_habitat_v0.2', 'hm3d_val_configs_v0.2', 'hm3d_val_semantic_annots_v0.2', 'hm3d_val_semantic_configs_v0.2'])
('hm3d_minival_full', ['hm3d_minival_glb_v0.2', 'hm3d_minival_habitat_v0.2', 'hm3d_minival_configs_v0.2', 'hm3d_minival_semantic_annots_v0.2', 'hm3d_minival_semantic_configs_v0.2'])
('hm3d_example_full', ['hm3d_example_glb', 'hm3d_example_habitat', 'hm3d_example_configs', 'hm3d_example_semantic_annots', 'hm3d_example_semantic_configs'])
('hm3d', ['hm3d_val_habitat_v0.2', 'hm3d_val_configs_v0.2', 'hm3d_val_semantic_annots_v0.2', 'hm3d_val_semantic_configs_v0.2', 'hm3d_train_habitat_v0.2', 'hm3d_train_configs_v0.2', 'hm3d_train_semantic_annots_v0.2', 'hm3d_train_semantic_configs_v0.2', 'hm3d_minival_habitat_v0.2', 'hm3d_minival_configs_v0.2', 'hm3d_minival_semantic_annots_v0.2', 'hm3d_minival_semantic_configs_v0.2'])
====================================
```
列表中其实只有两种东西：**原子包（Parts）** 和 **组合包（Groups）**。

当你指定 `uid = hm3d_minival_v0.2` 时，脚本会自动帮你下载该组内的 **4 个原子包**。

## 下载 Multi-agent necessary data
```bash
sudo apt install git-lfs
python -m habitat_sim.utils.datasets_download \
  --username XXX \
  --password XXX \
  --uids hab3-episodes habitat_humanoids hab3_bench_assets hab_spot_arm
```

> 遇到 huggingface.co 443 超时的话就 `source /etc/network_turbo` 一下

## 下载 Leg animation (腿部动作数据)
```bash
mkdir -p data/robots/spot_data
# 都是在~/SocialNav-Map/Falcon路径下
wget https://github.com/facebookresearch/habitat-lab/files/12502177/spot_walking_trajectory.csv -O data/robots/spot_data/spot_walking_trajectory.csv
```

## 下载 Scene Datasets (场景数据)

### Downloading HM3D v0.2
| File Name | Data Set | Format | Link | Size |
|-----------|----------|--------|------|------|
| hm3d-minival-glb-v0.2.tar | minival | glb | https://api.matterport.com/resources/habitat/hm3d-minival-glb-v0.2.tar | 464M |
| hm3d-minival-habitat-v0.2.tar | minival | habitat | https://api.matterport.com/resources/habitat/hm3d-minival-habitat-v0.2.tar | 390M |
| hm3d-minival-semantic-annots-v0.2.tar | minival | semantic-annots | https://api.matterport.com/resources/habitat/hm3d-minival-semantic-annots-v0.2.tar | 240.6M |
| hm3d-minival-semantic-configs-v0.2.tar | minival | semantic-configs | https://api.matterport.com/resources/habitat/hm3d-minival-semantic-configs-v0.2.tar | 30K |
| hm3d-train-glb-v0.2.tar | train | glb | https://api.matterport.com/resources/habitat/hm3d-train-glb-v0.2.tar | 32G |
| hm3d-train-habitat-v0.2.tar | train | habitat | https://api.matterport.com/resources/habitat/hm3d-train-habitat-v0.2.tar | 27G |
| hm3d-train-semantic-annots-v0.2.tar | train | semantic-annots | https://api.matterport.com/resources/habitat/hm3d-train-semantic-annots-v0.2.tar | 8.1G |
| hm3d-train-semantic-configs-v0.2.tar | train | semantic-configs | https://api.matterport.com/resources/habitat/hm3d-train-semantic-configs-v0.2.tar | 50K |
| hm3d-val-glb-v0.2.tar | val | glb | https://api.matterport.com/resources/habitat/hm3d-val-glb-v0.2.tar | 4G |
| hm3d-val-habitat-v0.2.tar | val | habitat | https://api.matterport.com/resources/habitat/hm3d-val-habitat-v0.2.tar | 3.3G |
| hm3d-val-semantic-annots-v0.2.tar | val | semantic-annots | https://api.matterport.com/resources/habitat/hm3d-val-semantic-annots-v0.2.tar | 2.0G |
| hm3d-val-semantic-configs-v0.2.tar | val | semantic-configs | https://api.matterport.com/resources/habitat/hm3d-val-semantic-configs-v0.2.tar | 40K |
| hm3d-example-glb-v0.2.tar | example | glb | hm3d-example-glb-v0.2.tar | 186M |
| hm3d-example-habitat-v0.2.tar | example | habitat | hm3d-example-habitat-v0.2.tar | 154M |
| hm3d-example-semantic-annots-v0.2.tar | example | semantic-annots | hm3d-example-semantic-annots-v0.2.tar | 60M |
| hm3d-example-semantic-configs-v0.2.tar | example | semantic-configs | hm3d-example-semantic-configs-v0.2.tar | 30K |


| 类别 (Split) | 用途 | 包含场景数 | 总大小 (解压前) | 详细组成 (核心文件) |
|------------|------|-----------|----------------|-------------------|
| Minival | 代码调试/快速验证 | 20个 | ~1.1 GB | 已下载 (GLB 464M + Nav 390M + Annots 240M) |
| Val | 标准验证/评估模型 | 100个 | ~9.3 GB | GLB: 4G<br />Habitat: 3.3G<br />Semantics: 2.0G |
| Train | 大规模模型训练 | 800个 | ~67.1 GB | GLB: 32G<br />Habitat: 27G<br />Semantics: 8.1G |

**解压后加起来应该在 150GB** 那样子（按文档所说）
```bash
python -m habitat_sim.utils.datasets_download \
  --username XXX \
  --password XXX \
  --uids hm3d_minival_v0.2
```
这玩意下太慢了，对于 **val** 的话 python 单线程我得下 **5天**。而 **Autodl 的带宽**就算用了 aria2 也不够，只能先在自己电脑上下（用 Github 给的[直链](https://github.com/matterport/habitat-matterport-3dresearch)），然后传到 Autodl 上（它的**入站带宽不小**）。

这里先把 **minival** 下下来。

对于 [MP3D](https://github.com/niessner/Matterport)，我终于理解了，我向 TUM 申请的那个 `download_mp.py`（只能用 **python 2.7** 跑的）是 **entire Matterport3D dataset**，那个是 **1.3TB** 的，而针对 Habitat 仿真器的版本（即 `--task habitat`）大小就只有 **15 GB**，因为它剔除了巨大的原始 RGB-D 视频帧，只保留了重建好的 3D 模型。那个 1.3TB 的是做 **3D 重建、超分、深度估计**等底层视觉任务用的原始数据。

这里得给 **TUM 发邮件**得到他们那个 download_mp.py 才可以，这里我因为早就发过了所以就跳过了，同样也是本地下好（**3MB/s 左右**）然后再传上去。

## 下载 Episode Datasets (SocialNav 任务数据)

作者给我们的[链接](https://drive.google.com/drive/folders/1V0a8PYeMZimFcHgoJGMMTkvscLhZeKzD)有一个 **2.24GB** 的 `social-hm3d.zip`，一个 **1.96GB** 的 `social-mp3d.zip`
```bash
# 在 AutoDL 上下载 Google Drive 文件
pip install gdown
cd data
gdown --folder https://drive.google.com/drive/folders/1V0a8PYeMZimFcHgoJGMMTkvscLhZeKzD
# 这个因为 Google Drive 的文件夹抓取受到很多反爬虫限制，而且当文件夹权限设置为“仅查看”时，gdown 经常无法列出目录
# 这里以 social-mp3d.zip 为例，先拿到它的File ID：https://drive.google.com/file/d/16KGr9cae1z3ypfgeeDSd5wDnJTfu2HhK/view?usp=drive_link，即‘16KGr9cae1z3ypfgeeDSd5wDnJTfu2HhK’
gdown 16KGr9cae1z3ypfgeeDSd5wDnJTfu2HhK -O social-mp3d.zip
```
**gdown 两种方法都下不下来**，主要原因还是在于 **Permission** 本身，建议在本地电脑下载好，然后通过 **AutoDL 的 JupyterLab 网页端**或者 **FileZilla** 上传到 `data/` 目录。

接着按照 **README** 的结构解压：
```bash
# 确保目录存在
mkdir -p datasets/pointnav

# 解压 social-hm3d.zip 到目标目录
unzip social-hm3d.zip -d datasets/pointnav/

# 解压 social-mp3d.zip 到目标目录
unzip social-mp3d.zip -d datasets/pointnav/

# 验证目录结构（可选）
ls -la datasets/pointnav/
# 应该看到 social-hm3d/ 和 social-mp3d/ 两个目录

# 清理 zip 文件（可选，节省空间）
# rm social-hm3d.zip social-mp3d.zip
```


最后检查一下路径，惊觉自己居然把代码放在了**系统盘**，于是赶紧迁移到**数据盘**去：

```bash
mv ~/SocialNav-Map /root/autodl-tmp/
```

好在之前的软链接用的是**绝对路径**，移动 SocialNav-Map 文件夹时，里面的 `data` 这个"快捷方式"文件被一起移动了，但它指向的目标地址（绝对路径）是写死在它里面的不会变。

然而以**可编辑模式安装的包**仍指向旧路径，导致导入失败，所以需要重新安装：

- **habitat-lab** 已重新安装到新路径：`/root/autodl-tmp/SocialNav-Map/Falcon/habitat-lab`
- **habitat-baselines** 已重新安装到新路径：`/root/autodl-tmp/SocialNav-Map/Falcon/habitat-baselines`

**问题**：`ModuleNotFoundError: No module named 'habitat_baselines.il.data.nav_data'`

**解决**：手动把[官方库](https://github.com/facebookresearch/habitat-lab/blob/main/habitat-baselines/habitat_baselines/il/data/nav_data.py)里的 `nav_data.py` 创建过来。

这之后又来一个 `ModuleNotFoundError: No module named 'habitat_baselines.il.data.data'`，同样把[这里](https://github.com/facebookresearch/habitat-lab/blob/main/habitat-baselines/habitat_baselines/il/data/data.py)的 `data.py` 挪过来。