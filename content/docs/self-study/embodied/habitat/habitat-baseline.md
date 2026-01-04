---
title: "Habitat-Baseline"
weight: 5
---

## Tutorials 和示例

### Python Notebooks

由于 **VNC** 与无头的缘故，`/root/autodl-tmp/habitat-lab/examples/tutorials/notebooks` 中的内容无法直接查看，所以直接看 `/root/autodl-tmp/habitat-lab/examples/tutorials/nb_python`，这里只有两个值得看：

- `/root/autodl-tmp/habitat-lab/examples/tutorials/nb_python/Habitat_Lab_TopdownMap_Visualization.py`
- `/root/autodl-tmp/habitat-lab/examples/tutorials/nb_python/Habitat_Lab.py`

### Human-in-the-loop (HITL) 应用

`/root/autodl-tmp/habitat-lab/examples/hitl` 目录包含以下 **Human-in-the-loop（HITL）** 应用：

| 应用名称 | 描述 | 特点/适合场景 |
| --- | --- | --- |
| **basic_viewer** - 基础查看器 | 用于实时查看 **Habitat** 环境、**episode** 和智能体策略评估，提供用户控制的自由相机 | • 检查环境与 **episode**<br>• 实时查看策略评估<br>• 调试与可视化 |
| **minimal** - 最小化示例 | 最小化应用，加载并运行 **Habitat** 环境，使用固定的俯视相机 | • 学习 **HITL** 框架基础<br>• 作为开发自定义应用的起点<br>• 理解 **HITL** 应用的基本结构 |
| **pick_throw_vr** - 拾取投掷 VR 应用 | 支持用户通过鼠标/键盘或 **VR** 头显控制人类化身与场景交互，同时有一个策略驱动的 **Spot** 机器人与场景交互 | • 支持桌面（鼠标/键盘）和 **VR** 两种模式<br>• 用户控制人类化身，机器人由策略控制<br>• 可作为构建 **VR** 应用的参考 |
| **rearrange** - 协作重排应用 | 用户控制的人类与策略控制的机器人协作完成重排任务 | • 用于 **Habitat 3.0** 论文中评估策略与真实人类协作<br>• 可保存会话数据（如 `my_session.0.json.gz`）<br>• 支持数据收集用于评估和训练 |
| **rearrange_v2** - 实验性重排应用（v2） | 实验性应用，使用 **partnr-planner** 评估重排实验 | • 支持单用户、多用户和用户-智能体设置<br>• 仍在开发中 |

---

## Habitat 3.0 新 Baseline

和我没关系，我主要是感兴趣的 **Habitat 3.0** 推出的新 **baseline**：

- **社交导航**：机器人学习跟随人类并保持安全距离
- **社交重排**：人机协作重新整理房间物品，如清理客厅

**Social Rearrangement** 我们不关心，我们先来看看 **Social Navigation（社交导航）**

### 配置文件位置

```
habitat-baselines/habitat_baselines/config/social_nav/social_nav.yaml
```

### 运行训练

```bash
vglrun -d :1 python -u -m habitat_baselines.run \
    --config-name=social_nav/social_nav.yaml \
    benchmark/multi_agent=hssd_spot_human_social_nav \
    habitat_baselines.evaluate=False
```

### 运行评估

```bash
vglrun -d :1 python -u -m habitat_baselines.run \
    --config-name=social_nav/social_nav.yaml \
    benchmark/multi_agent=hssd_spot_human_social_nav \
    habitat_baselines.evaluate=True \
    habitat_baselines.eval_ckpt_path_dir=checkpoints_social_nav/social_nav_latest.pth
```

## Pipeline 结构

### 1. 统一入口
所有任务都从同一个入口进入：
```python
python -u -m habitat-baselines.habitat_baselines.run --config-name=social_nav_v2/<config_file>.yaml
```

### 2. 配置文件层级结构

配置文件使用 Hydra 的 `defaults` 机制组合不同模块：

```yaml
defaults:
  # 1. 任务配置（决定数据集和任务类型）
  - /benchmark/nav/socialnav_v2: falcon_mp3d_task  # 或 astar_mp3d_task, orca_mp3d_task
  
  # 2. 基线配置（RL训练的基础配置）
  - /habitat_baselines: habitat_baselines_rl_config_base
  
  # 3. 传感器配置
  - /habitat/simulator/sim_sensors@...: third_rgb_sensor
  
  # 4. 策略配置（多智能体的固定策略）
  - /habitat_baselines/rl/policy@...agent_1: single_fixed
  
  # 5. 动作配置（智能体的动作空间）
  - /habitat/task/actions@...agent_0_discrete_stop: discrete_stop
  
  # 6. 传感器配置
  - /habitat/task/lab_sensors@...: pointgoal_with_gps_compass_sensor
```

### 3. 配置文件的作用

配置文件决定：

| 配置项 | 作用 | 示例 |
|--------|------|------|
| **任务配置** | 选择数据集（HM3D/MP3D）和任务类型 | `falcon_mp3d_task` vs `falcon_hm3d_task` |
| **算法** | 决定使用哪个算法 | `falcon_*.yaml` (RL) vs `astar_*.yaml` (规则) vs `orca_*.yaml` (规则) |
| **模式** | 训练/评估 | `falcon_hm3d_train.yaml` vs `falcon_hm3d.yaml` |
| **传感器** | 观察空间配置 | RGB、深度、GPS等 |
| **模型参数** | 网络结构、超参数等 | backbone、hidden_size等 |

### 4. 执行流程

```
命令行
  ↓
run.py (统一入口)
  ↓
Hydra加载配置文件
  ↓
组合所有defaults中的配置模块
  ↓
创建Trainer (根据trainer_name)
  ↓
执行 train() 或 eval()
```

### 5. 不同算法的区别

- RL方法（Falcon）：需要 `trainer_name: "ddppo"`，有模型权重
- 规则方法（Astar/ORCA）：不需要训练器，直接运行算法

所有差异都通过配置文件管理，代码入口统一。






根据代码和 README，`socialnav-map` 属于零样本（Zero-Shot）方法，与 Falcon 不同。

## SocialNav-Map 方法类型

### 1. 方法分类
零样本方法（Zero-Shot），无需训练，直接运行。

### 2. 与 Falcon 的区别

| 特性 | Falcon (Falcon目录) | SocialNav-Map (socialnav-map目录) |
|------|---------------------|-----------------------------------|
| 入口 | `habitat-baselines.habitat_baselines.run` | 独立脚本 `socialmap_hm3d.py` |
| 方法类型 | RL方法（需要训练） | 零样本方法（无需训练） |
| 训练需求 | 需要2000+ GPU小时训练 | 无需训练，直接运行 |
| 核心组件 | 神经网络策略 | 规则算法 + 预测器 |
| 配置文件 | 使用Habitat的Hydra配置系统 | 使用自己的配置系统 |

### 3. SocialNav-Map 的核心组件

从代码看，它包含：

1. 语义建图（Semantic Mapping）
   - 构建占用地图
   - 语义分割

2. 人类轨迹预测（HumanTrajectoryPredictor）
   - 历史轨迹预测
   - 方向预测
   - 融合预测

3. 动态障碍物处理
   - 将预测的人类轨迹作为动态障碍物加入地图
   - `apply_predicted_obstacles_to_map()`

4. 路径规划（FMM Planner）
   - Fast Marching Method 路径规划器
   - 在包含动态障碍物的地图上规划路径

### 4. 执行方式

```bash
# SocialNav-Map 的执行方式（独立脚本）
cd socialnav-map
python socialmap_hm3d.py --split val --eval 1 ...

# Falcon 的执行方式（通过habitat-baselines框架）
python -u -m habitat-baselines.habitat_baselines.run \
  --config-name=social_nav_v2/falcon_hm3d.yaml
```

### 总结

`socialnav-map` 是零样本方法，不通过 `habitat-baselines.habitat_baselines.run` 入口，而是使用独立脚本。它结合了：
- 规则算法（FMM路径规划）
- 预测算法（人类轨迹预测）
- 建图算法（语义占用地图）

因此，它更像 Astar/ORCA 这类规则方法的增强版，加入了预测和动态建图能力，但不需要训练。


---

预训练模型说明
根据 summary.txt，有 4 个预训练模型：
falcon_noaux_25.pth (48M) - 当前使用的模型
完整版 Falcon，无辅助任务
可直接用于推理，无需微调
适合评估
falcon_pretrained_25.pth (133M)
完整版 Falcon（带辅助任务）
用于进一步训练/微调，不直接用于推理
pretrained_habitat3.pth (48M)
HM3D 点导航基础模型（仅深度输入）
Falcon 的基础模型
pretrained_mini.pth (15M)
轻量版 Falcon，无辅助任务
适合快速部署

1. 训练数据
训练只在 HM3D 上进行
MP3D 结果是零样本推理，用于验证泛化能力(https://github.com/Zeying-Gong/Falcon/issues/5)
这解释了为什么 MP3D 配置可能更复杂
pretrained_habitat3.pth (48M)
  ↓ 微调（RL + 辅助任务）
falcon_pretrained_25.pth (133M) - 带辅助任务
falcon_noaux_25.pth (48M) - 不带辅助任务（用于评估）
3. 模型输入
所有模型都只使用深度输入（1通道），不是RGB+深度
这解释了维度不匹配问题
4. 训练配置
使用标准 habitat-baselines，无自定义训练代码
训练配置：falcon_hm3d_train.yaml（包含辅助任务）
评估配置：falcon_hm3d.yaml（可能不需要辅助任务）