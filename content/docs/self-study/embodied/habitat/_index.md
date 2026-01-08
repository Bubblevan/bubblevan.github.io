---
title: "Habitat"
weight: 2
---

## 参考资源

- [Habitat Tutorial](https://zhuanlan.zhihu.com/c_1852043883250323457)
- [Habitat-Sim-Usage-Chinese](https://github.com/GuoPingPan/Habitat-Sim-Usage-Chinese)
- [Meta Official](https://github.com/facebookresearch/habitat-sim)
- [Habitat 基础使用记录](https://evernorif.github.io/2025/05/07/habitat-%E5%9F%BA%E7%A1%80%E4%BD%BF%E7%94%A8%E8%AE%B0%E5%BD%95/)
- [Habitat-Lab for Navigation](https://zhuanlan.zhihu.com/p/13543813188)（隶属于上面的Habitat Tutorial知乎专栏）


## Habitat-Lab Examples

谁说官方没有给教程？注意看 `examples/` 目录下的所有文件：

```
examples/
├── __init__.py                    # Python 包初始化文件
├── example.py                     # 最基础的示例（Gym API）
├── benchmark.py                   # 基准测试示例
├── display_utils.py               # 显示工具函数
├── interactive_play.py            # 交互式控制示例
├── shortest_path_follower_example.py  # 最短路径跟随示例
├── vln_benchmark.py               # 视觉语言导航基准测试
├── vln_reference_path_follower_example.py  # VLN 参考路径跟随
├── franka_example.py              # Franka 机器人示例
├── new_actions.py                 # 新动作定义示例
├── register_new_sensors_and_measures.py  # 注册新传感器和测量示例
├── learn_habitat_sim_basic.py     # Habitat-Sim 基础学习示例（新增）
├── learn_habitat_sim_navmesh.py   # NavMesh 学习示例（新增）
├── hitl/                          # Human-in-the-Loop 相关示例
├── tutorials/                     # 教程相关文件
└── videos/                        # 视频输出目录（运行时生成）
```

---

### 根目录下的 Python 文件

#### 1. `example.py` - 最基础的入门示例

**作用**：最简单的 Habitat-Lab 使用示例，展示如何使用 Gym API。

**主要内容**：
- 使用 `gym.make("HabitatRenderPick-v0")` 创建环境
- 执行随机动作直到 episode 结束
- 适合快速验证安装是否正确

**使用场景**：
- 第一次使用 Habitat-Lab 时的测试
- 验证环境配置是否正确

---

#### 2. `benchmark.py` - 基准测试示例

**作用**：展示如何使用 Habitat-Lab 的 Benchmark 系统评估 Agent 性能。

**主要内容**：
- 实现一个简单的 `ForwardOnlyAgent`（只会向前移动）
- 使用 `habitat.Benchmark` 评估 Agent
- 输出性能指标（如 SPL、成功率等）

**使用场景**：
- 评估自定义 Agent 的性能
- 理解 Habitat-Lab 的评估系统
- 作为编写评估代码的模板

**运行方法**：
```bash
python examples/benchmark.py --task-config benchmark/nav/pointnav/pointnav_habitat_test.yaml
```

---

### 3. `interactive_play.py` - 交互式控制示例

**作用**：允许用户使用键盘手动控制机器人进行交互。

**主要内容**：
- 使用 PyGame 进行键盘输入
- 支持速度控制和 IK（逆运动学）控制
- 可以录制和回放轨迹
- 支持保存视频

**控制方式**：
- **速度控制**：1-7 增加关节，Q-U 减少关节
- **IK 控制**：W/S/A/D 移动末端执行器，E/Q 上下移动
- **基座移动**：I/J/K/L 移动机器人基座
- **相机控制**：Z 切换自由相机模式

**使用场景**：
- 手动测试机器人控制
- 收集演示数据
- 调试机器人行为

**运行方法**：
```bash
# 需要安装 pygame
pip install pygame==2.0.1
python examples/interactive_play.py

# 使用 IK 控制
python examples/interactive_play.py --add-ik

# 录制视频
python examples/interactive_play.py --save-obs
```

---

### 4. `shortest_path_follower_example.py` - 最短路径跟随示例

**作用**：展示如何使用 `ShortestPathFollower` 让 Agent 沿着最短路径导航到目标。

**主要内容**：
- 使用 `ShortestPathFollower` 计算最优动作
- 可视化导航过程（RGB + Top-down map）
- 保存导航轨迹视频

**使用场景**：
- 学习路径规划算法
- 理解导航任务
- 作为导航算法的基线

**运行方法**：
```bash
python examples/shortest_path_follower_example.py
```

---

### 5. `vln_benchmark.py` - 视觉语言导航基准测试

**作用**：视觉语言导航（Vision-and-Language Navigation）任务的基准测试。

**主要内容**：
- 评估 VLN Agent 在指令跟随任务上的性能
- 使用参考路径进行导航
- 计算 VLN 相关指标

**使用场景**：
- VLN 任务评估
- 理解指令跟随导航

**运行方法**：
```bash
python examples/vln_benchmark.py
```

---

### 6. `vln_reference_path_follower_example.py` - VLN 参考路径跟随

**作用**：展示如何让 Agent 沿着参考路径导航（用于 VLN 任务）。

**主要内容**：
- 使用 `ShortestPathFollower` 跟随参考路径
- 访问中间视点（waypoints）
- 可视化导航过程

**使用场景**：
- VLN 任务开发
- 理解参考路径导航

---

### 7. `franka_example.py` - Franka 机器人示例

**作用**：展示如何使用 Franka 机器人进行任务。

**主要内容**：
- 配置 Franka 机器人
- 控制机器人执行任务
- Franka 特定的控制示例

**使用场景**：
- 使用 Franka 机器人
- 学习机器人控制

---

### 8. `new_actions.py` - 新动作定义示例

**作用**：展示如何定义和注册新的动作类型。

**主要内容**：
- 创建自定义动作类
- 使用 `@registry.register_action` 注册动作
- 在任务中使用新动作

**使用场景**：
- 需要自定义动作空间
- 扩展 Habitat-Lab 的功能

---

### 9. `register_new_sensors_and_measures.py` - 注册新传感器和测量

**作用**：展示如何定义和注册新的传感器和测量指标。

**主要内容**：
- 创建自定义传感器类
- 创建自定义测量类
- 使用 `@registry.register_sensor` 和 `@registry.register_measure` 注册

**使用场景**：
- 需要新的传感器类型
- 需要新的评估指标
- 扩展 Habitat-Lab 的观察和测量功能

---

### 10. `display_utils.py` - 显示工具函数

**作用**：提供各种可视化工具函数。

**主要内容**：
- 图像显示函数
- 视频生成函数
- 可视化辅助函数

**使用场景**：
- 在其他示例中复用可视化功能
- 自定义可视化需求

---

## `hitl/` 目录 - Human-in-the-Loop

**HITL 是什么**：Human-in-the-Loop（人在回路中），允许人类与模拟环境进行实时交互。

### 子目录说明

#### 1. `hitl/minimal/` - 最小化 HITL 示例

**作用**：最简单的 HITL 应用示例。

**主要内容**：
- 加载 Habitat 环境
- 运行 episode 直到结束
- 固定俯视相机视角
- 按 ESC 退出

**使用场景**：
- 理解 HITL 框架的基本结构
- 作为开发 HITL 应用的起点

---

#### 2. `hitl/basic_viewer/` - 基础查看器

**作用**：提供基础的 3D 场景查看功能。

**主要内容**：
- 3D 场景渲染
- 相机控制
- 基础交互

---

#### 3. `hitl/pick_throw_vr/` - VR 抓取和投掷

**作用**：使用 VR 设备进行抓取和投掷任务的交互。

**主要内容**：
- VR 设备集成
- 抓取物体
- 投掷物体
- VR 交互控制

**使用场景**：
- VR 环境下的机器人任务
- 收集 VR 演示数据

---

#### 4. `hitl/rearrange/` - 重排任务 HITL

**作用**：重排任务（Rearrangement）的 HITL 应用。

**主要内容**：
- 重排任务交互
- 物体操作
- 任务完成评估

---

#### 5. `hitl/rearrange_v2/` - 重排任务 V2

**作用**：重排任务的升级版本，包含更多功能。

**主要内容**：
- 改进的重排任务交互
- 更丰富的 UI
- 会话管理
- 数据收集和上传
- LLM 集成（用于任务生成）

**使用场景**：
- 收集重排任务数据
- 评估重排算法
- 人类演示学习

---

## `tutorials/` 目录 - 教程文件

### 目录结构

```
tutorials/
├── nb_python/              # Jupyter Notebook 的 Python 版本
├── notebooks/              # Jupyter Notebook 文件（.ipynb）
├── articulated_agents_tutorial.ipynb  # 关节机器人教程
├── humanoids_tutorial.ipynb           # 人形机器人教程
└── polymetis_example.ipynb            # Polymetis 集成示例
```

### 说明

#### 1. `nb_python/` 和 `notebooks/` 的关系

这两个目录包含相同的内容，但格式不同：

- **`notebooks/`**：Jupyter Notebook 格式（`.ipynb`）
  - 可以在 Jupyter Lab/Notebook 中交互式运行
  - 包含代码、输出、图表等
  - 适合学习和实验

- **`nb_python/`**：Python 脚本格式（`.py`）
  - 从 Notebook 转换而来（使用 jupytext）
  - 可以直接用 Python 运行
  - 适合作为参考代码

**文件对应关系**：
- `notebooks/Habitat_Lab.ipynb` ↔ `nb_python/Habitat_Lab.py`
- `notebooks/Habitat2_Quickstart.ipynb` ↔ `nb_python/Habitat2_Quickstart.py`
- `notebooks/habitat2_gym_tutorial.ipynb` ↔ `nb_python/habitat2_gym_tutorial.py`
- `notebooks/Habitat_Lab_TopdownMap_Visualization.ipynb` ↔ `nb_python/Habitat_Lab_TopdownMap_Visualization.py`

---

#### 2. `notebooks/` 和 `nb_python/` 中的文件

##### `Habitat_Lab.ipynb` / `Habitat_Lab.py`

**作用**：Habitat-Lab 的完整教程。

**主要内容**：
- 环境设置和配置
- PointNav 任务示例
- 强化学习训练（PPO）
- 创建新任务
- 创建新传感器
- 创建新 Agent

**适合**：全面学习 Habitat-Lab 的各个方面

---

##### `Habitat2_Quickstart.ipynb` / `Habitat2_Quickstart.py`

**作用**：Habitat 2.0 的快速入门教程。

**主要内容**：
- Habitat 2.0 基础使用
- 重排任务（Rearrangement）示例
- 定义新任务
- 数据集生成
- Gym API 使用

**适合**：快速上手 Habitat 2.0 和重排任务

---

##### `habitat2_gym_tutorial.ipynb` / `habitat2_gym_tutorial.py`

**作用**：Habitat 2.0 的 Gym API 教程。

**主要内容**：
- 使用 Gym API 创建环境
- 环境交互
- 视频录制
- Gym 接口的使用

**适合**：学习如何使用 Gym API 与 Habitat 交互

---

##### `Habitat_Lab_TopdownMap_Visualization.ipynb` / `Habitat_Lab_TopdownMap_Visualization.py`

**作用**：Top-down Map（俯视图）可视化教程。

**主要内容**：
- 生成 Top-down map
- 可视化导航网格
- 在 map 上绘制 Agent 轨迹
- 可视化目标位置

**适合**：学习导航可视化和调试

---

#### 3. 根目录下的 Notebook 文件

##### `articulated_agents_tutorial.ipynb` - 关节机器人教程

**作用**：深入学习关节机器人（如 Fetch、Franka）的使用。

**主要内容**：
- 关节机器人的配置
- 关节控制
- 末端执行器控制
- 逆运动学（IK）
- 抓取操作
- 视频录制

**适合**：使用关节机器人进行研究

---

##### `humanoids_tutorial.ipynb` - 人形机器人教程

**作用**：学习如何使用人形机器人。

**主要内容**：
- 人形机器人配置
- 人形机器人控制
- 运动学
- 特定于人形机器人的功能

**适合**：人形机器人研究

---

##### `polymetis_example.ipynb` - Polymetis 集成示例

**作用**：展示如何将 Habitat 与 Polymetis（真实机器人控制库）集成。

**主要内容**：
- Polymetis 集成
- 仿真到真实的桥接
- 真实机器人控制

**适合**：需要连接真实机器人的场景

---

## 学习路径建议

### 初学者路径

1. **第一步**：`example.py` - 验证安装
2. **第二步**：`learn_habitat_sim_basic.py` - 学习 Habitat-Sim 基础
3. **第三步**：`learn_habitat_sim_navmesh.py` - 学习导航
4. **第四步**：`tutorials/notebooks/Habitat_Lab.ipynb` - 全面学习 Habitat-Lab

### 中级路径

1. `shortest_path_follower_example.py` - 路径规划
2. `interactive_play.py` - 交互控制
3. `tutorials/notebooks/Habitat2_Quickstart.ipynb` - Habitat 2.0
4. `tutorials/articulated_agents_tutorial.ipynb` - 机器人控制

### 高级路径

1. `new_actions.py` - 自定义动作
2. `register_new_sensors_and_measures.py` - 自定义传感器和测量
3. `hitl/rearrange_v2/` - HITL 应用开发
4. `benchmark.py` - 性能评估

---

## 总结

- **基础示例**：`example.py`, `learn_habitat_sim_basic.py`, `learn_habitat_sim_navmesh.py`
- **功能示例**：`shortest_path_follower_example.py`, `interactive_play.py`
- **扩展示例**：`new_actions.py`, `register_new_sensors_and_measures.py`
- **评估示例**：`benchmark.py`, `vln_benchmark.py`
- **教程**：`tutorials/` 目录下的各种教程
- **HITL**：`hitl/` 目录下的人机交互应用

每个文件都有其特定的用途，可以根据你的学习目标和研究需求选择合适的示例。
