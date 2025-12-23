---
title: "Habitat-Lab"
weight: 4
---

本指南将帮助你通过实际代码学习 Habitat-Lab。假设你已经阅读了[habitat-sim](./habitat_sim.md)并通过 `learn_habitat_sim_basic.py` 和 `learn_habitat_sim_navmesh.py` 了解了 habitat-sim 的基础设定。

## 学习路径

### 第一步：理解 Habitat-Lab 与 Habitat-Sim 的区别

这一点我们在最开始就已经有所论述。

### 第二步：从最简单的例子开始

运行基础学习示例：

```bash
python examples/learn_habitat_lab_basic.py
```

这个示例展示了：
1. 如何使用 `habitat.Env` 创建环境
2. 如何通过配置文件初始化环境
3. 如何执行动作并获取观察
4. 如何理解观察空间和动作空间

### 第三步：理解核心架构

Habitat-Lab 的核心架构包含以下关键组件：

#### 1. Env (环境)

`habitat.core.env.Env` 是核心环境类，它连接了三个主要组件：

```python
# 查看代码: habitat-lab/habitat/core/env.py
env = habitat.Env(config=config)

# Env 包含：
# - env.sim: Simulator (habitat-sim 的封装)
# - env.task: EmbodiedTask (任务定义)
# - env.episodes: Dataset (任务实例数据)
```

**关键方法：**
- `env.reset()`: 重置环境，开始新的 episode
- `env.step(action)`: 执行动作，返回观察
- `env.get_metrics()`: 获取任务度量标准

#### 2. Simulator (模拟器)

`habitat.sims.habitat_simulator.HabitatSim` 是 habitat-sim 的轻量级封装：

```python
# 查看代码: habitat-lab/habitat/sims/habitat_simulator/habitat_simulator.py
# 访问模拟器
sim = env.sim

# 获取 Agent 状态
agent_state = sim.get_agent_state()
position = agent_state.position
rotation = agent_state.rotation

# 执行动作（底层）
observations = sim.step(action)
```

#### 3. EmbodiedTask (任务)

`habitat.core.embodied_task.EmbodiedTask` 定义了任务：

```python
# 查看代码: habitat-lab/habitat/core/embodied_task.py
task = env.task

# 任务包含：
# - task.action_space: 动作空间
# - task.sensor_suite: 任务特定的传感器
# - task.measurements: 度量标准
```

**常见任务类型：**
- `PointNavTask`: 点目标导航
- `ObjectNavTask`: 物体导航
- `RearrangeTask`: 重排任务

#### 4. Dataset (数据集)

`habitat.core.dataset.Dataset` 包含任务实例数据：

```python
# 查看代码: habitat-lab/habitat/core/dataset.py
dataset = env.episodes

# Episode 包含：
# - episode.scene_id: 场景 ID
# - episode.start_position: 起始位置
# - episode.goals: 目标列表
```

### 第四步：理解配置系统

Habitat-Lab 使用 Hydra 进行配置管理：

```python
# 获取配置
config = habitat.get_config(
    config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"
)

# 修改配置
from habitat.config import read_write

with read_write(config):
    config.habitat.environment.max_episode_steps = 1000
    config.habitat.dataset.split = "val"
```

**配置文件位置：** `habitat-lab/habitat/config/`

**关键配置项：**
- `habitat.simulator`: 模拟器配置（场景、传感器等）
- `habitat.task`: 任务配置（动作空间、度量等）
- `habitat.dataset`: 数据集配置（数据路径、分割等）
- `habitat.environment`: 环境配置（最大步数等）

### 第五步：理解观察和动作

#### 观察空间

观察空间包含两类传感器：

1. **Simulator 传感器**（来自 habitat-sim）：
   - `rgb`: RGB 图像
   - `depth`: 深度图像
   - `semantic`: 语义分割图像

2. **Task 传感器**（任务特定的）：
   - `pointgoal_with_gps_compass`: 点目标导航信息（距离、角度）
   - `objectgoal`: 物体目标信息

```python
observations = env.reset()

# 访问观察
rgb_image = observations["rgb"]
depth_image = observations["depth"]
pointgoal = observations["pointgoal_with_gps_compass"]
distance = pointgoal[0]  # 距离
theta = pointgoal[1]     # 角度（弧度）
```

#### 动作空间

动作空间由任务定义：

```python
from habitat.sims.habitat_simulator.actions import HabitatSimActions

# 常见动作
action = {"action": HabitatSimActions.move_forward}
action = {"action": HabitatSimActions.turn_left}
action = {"action": HabitatSimActions.turn_right}
action = {"action": HabitatSimActions.stop}
```

### 第六步：使用 RLEnv 进行强化学习

`habitat.core.env.RLEnv` 扩展了 `Env`，添加了强化学习所需的组件：

```python
class MyRLEnv(habitat.RLEnv):
    def get_reward_range(self):
        return [-1, 1]
    
    def get_reward(self, observations):
        # 计算奖励
        metrics = self.habitat_env.get_metrics()
        # ... 基于度量计算奖励
        return reward
    
    def get_done(self, observations):
        return self.habitat_env.episode_over
    
    def get_info(self, observations):
        return self.habitat_env.get_metrics()
```

### 第七步：理解度量标准

度量标准用于评估智能体的性能：

```python
metrics = env.get_metrics()

# 常见度量：
# - distance_to_goal: 到目标的距离
# - success: 是否成功（0 或 1）
# - spl: Success weighted by Path Length
# - num_steps: 步数
```

**查看代码：** `habitat-lab/habitat/tasks/nav/nav.py` 了解如何定义度量标准

### 第八步：进阶学习

运行进阶学习示例：

```bash
python examples/learn_habitat_lab_advanced.py
```

这个示例展示了：
1. 如何使用 RLEnv
2. 如何使用 ShortestPathFollower
3. 如何深入理解架构
4. 如何自定义配置

## 关键代码文件路径

### 核心模块

- `habitat-lab/habitat/core/env.py`: Env 和 RLEnv 类
- `habitat-lab/habitat/core/embodied_task.py`: EmbodiedTask 基类
- `habitat-lab/habitat/core/dataset.py`: Dataset 和 Episode 类
- `habitat-lab/habitat/core/simulator.py`: Simulator 抽象类

### 任务实现

- `habitat-lab/habitat/tasks/nav/nav.py`: 导航任务基类
- `habitat-lab/habitat/tasks/nav/pointnav_task.py`: PointNav 任务
- `habitat-lab/habitat/tasks/nav/shortest_path_follower.py`: 最短路径跟随器

### 模拟器

- `habitat-lab/habitat/sims/habitat_simulator/habitat_simulator.py`: HabitatSim 实现

### 配置

- `habitat-lab/habitat/config/benchmark/nav/pointnav/`: PointNav 配置文件
- `habitat-lab/habitat/config/habitat/task/`: 任务配置文件

## 学习建议

1. **从示例代码开始**：运行 `learn_habitat_lab_basic.py` 和 `learn_habitat_lab_advanced.py`

2. **阅读核心代码**：按照上面的路径，逐步阅读核心模块的代码

3. **修改示例代码**：尝试修改示例代码，理解每个参数的作用

4. **查看配置文件**：理解配置文件的结构，尝试修改配置

5. **阅读文档**：查看 [Habitat-Lab 官方文档](https://aihabitat.org/docs/habitat-lab/)

6. **探索其他示例**：
   - `examples/shortest_path_follower_example.py`: 最短路径跟随
   - `examples/example.py`: 基础示例
   - `examples/register_new_sensors_and_measures.py`: 扩展示例

## 常见问题

### Q: Env 和 RLEnv 的区别是什么？

A: `Env` 是基础环境类，用于定义任务和获取观察。`RLEnv` 扩展了 `Env`，添加了强化学习所需的奖励、终止条件和信息字典。

### Q: 如何自定义任务？

A: 参考 `habitat-lab/habitat/tasks/nav/pointnav_task.py` 的实现，创建新的任务类继承 `EmbodiedTask`。

### Q: 如何添加新的传感器？

A: 参考 `examples/register_new_sensors_and_measures.py`，了解如何从外部注册新的传感器。

### Q: 如何训练智能体？

A: 查看 `habitat-baselines` 目录，了解如何使用 PPO 等算法训练智能体。

## 下一步

完成基础学习后，你可以：

1. 探索 `habitat-baselines` 了解如何训练智能体
2. 查看 `habitat-lab/habitat/tasks/` 了解其他任务类型
3. 阅读论文了解 Habitat 的设计理念
4. 尝试实现自己的任务或传感器
