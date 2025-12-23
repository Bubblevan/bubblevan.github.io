# Habitat-Sim 基础概念

## 为什么选择 Habitat-Sim？

在具身智能（Embodied AI）的研究中，我们面临一个巨大的挑战：你不能直接在客厅里训练一个昂贵的实体机器人。它可能会撞坏家具，而且训练速度慢得令人抓狂。

这时候，我们需要一个"数字孪生"世界。Habitat-Sim 正是这个世界的"物理底座"。它最大的特点就是快——在单 GPU 上能达到每秒上万帧的渲染速度。

这里有人可能提到大名鼎鼎的 Isaac。诚然 NVIDIA 的 **Isaac Sim** 和 **Isaac Lab** 也是非常优秀的仿真平台，但 Habitat-Sim 在特定场景下有其独特优势：

| 对比维度 | Habitat-Sim | Isaac Sim / Isaac Lab |
|---------|------------|----------------------|
| **渲染速度** | 极快（单 GPU 上万帧/秒） | 较慢（物理仿真更精确但更耗时） |
| **适用任务** | 导航、视觉导航、场景理解 | 机器人操作、抓取、复杂物理交互 |
| **物理仿真** | 轻量级（NavMesh 导航为主） | 高精度（基于 PhysX，支持复杂物理） |
| **学习曲线** | 相对简单，Python API 友好 | 较陡峭，需要理解 USD 场景格式 |
| **资源消耗** | 轻量，适合大规模并行训练 | 较重，需要更多 GPU 资源 |
| **社区生态** | Meta 支持，学术研究广泛使用 | NVIDIA 支持，工业应用较多 |
| **场景数据** | 专注于真实室内场景（HM3D, Matterport3D） | 支持自定义场景，更灵活但需要自己构建 |
| **开源程度** | 完全开源 | 部分开源（Isaac Lab 开源，Isaac Sim 有商业版） |

可能对于**导航和视觉任务**，Habitat-Sim/Lab 是更好的选择；对于**机器人操作和复杂物理交互**，Isaac Sim/Lab 更合适。

## 具身三要素

想要在虚拟世界里运行一个机器人，逻辑上只需要回答三个问题：

1. **舞台在哪里？** (Simulator)
2. **主角是谁？** (Agent)
3. **它怎么感知？** (Sensor)

其基础运行流程可以总结为：配置并启动 simulator，加载 scene，配置带有 sensor 的 agent，执行 action，获取 sensor 观察结果（RGB、semantic、depth 等）。

## 完整流程
首先需要导入必要的库：

```python
import os
import sys
import numpy as np
import quaternion  # 四元数库，用于表示 Agent 的旋转
import habitat_sim # Habitat-Sim 核心库，提供仿真功能
```

> BTW 这如果是一个`ipynb`文件的话可读性应该高很多，不过你也可以去看官方`habitat-lab`下`/examples`下面的`/tutorials`有一堆

### 步骤 1: 创建 Simulator 配置

首先，我们要定义"上帝视角"下的世界规律：加载哪张场景地图？要不要物理引擎？用哪块 GPU 渲染？

```python
def create_simulator_config():
    """创建 Simulator 配置对象"""
    sim_cfg = habitat_sim.SimulatorConfiguration()  # 创建 Simulator 配置对象
    sim_cfg.scene_id = "data/scene_datasets/habitat-test-scenes/skokloster-castle.glb"  # 设置场景文件路径，别设错了
    sim_cfg.enable_physics = False  # 禁用物理引擎（基础示例不需要物理仿真）
    sim_cfg.gpu_device_id = 0  # 指定使用第 0 号 GPU 设备
    return sim_cfg
```

### 步骤 2: 创建传感器配置

机器人不是靠“开挂”获取全局坐标的，它必须像生物一样拥有“传感器”。我们可以为它装上 RGB 相机（看颜色）和深度相机（看远近）。

注意代码中的 `position`，它定义了相机相对于机器人中心的偏移（通常是安装在头部高度，如 `[0.0, 1.5, 0.0]` 表示在机器人上方 1.5 米）。

```python
def create_sensor_specs():
    """创建传感器配置列表"""
    sensor_specs = []  # 初始化传感器规格列表
    
    # 配置 RGB 相机传感器
    rgb_sensor_spec = habitat_sim.CameraSensorSpec()  # 创建相机传感器规格对象
    rgb_sensor_spec.uuid = "color_sensor"  # 设置传感器唯一标识符
    rgb_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR  # 设置传感器类型为 RGB 颜色
    rgb_sensor_spec.resolution = [480, 640]  # 设置图像分辨率：[高度, 宽度]，单位像素
    rgb_sensor_spec.position = [0.0, 1.5, 0.0]  # 设置传感器相对于 Agent 的位置：[x, y, z]，y=1.5 表示在 Agent 上方 1.5 米
    rgb_sensor_spec.hfov = 90.0  # 设置水平视场角为 90 度
    sensor_specs.append(rgb_sensor_spec)  # 将 RGB 传感器规格添加到列表
    
    # 配置深度传感器
    depth_sensor_spec = habitat_sim.CameraSensorSpec()  # 创建深度传感器规格对象
    depth_sensor_spec.uuid = "depth_sensor"  # 设置深度传感器唯一标识符
    depth_sensor_spec.sensor_type = habitat_sim.SensorType.DEPTH  # 设置传感器类型为深度
    depth_sensor_spec.resolution = [480, 640]  # 设置深度图分辨率：[高度, 宽度]
    depth_sensor_spec.position = [0.0, 1.5, 0.0]  # 设置深度传感器位置，与 RGB 相机相同位置
    depth_sensor_spec.hfov = 90.0  # 设置水平视场角为 90 度
    sensor_specs.append(depth_sensor_spec)  # 将深度传感器规格添加到列表
    
    return sensor_specs  # 返回传感器规格列表
```

### 步骤 3: 创建 Agent 配置

Agent 是场景中的智能体，需要将传感器附加到它身上：

```python
def create_agent_config(sensor_specs):
    """
    步骤 3: 创建 AgentConfiguration
    
    Agent 是场景中的智能体，可以：
    - 在场景中移动
    - 通过传感器观察环境
    - 执行动作
    """
    agent_cfg = habitat_sim.agent.AgentConfiguration()  # 创建 Agent 配置对象
    agent_cfg.sensor_specifications = sensor_specs  # 将传感器规格列表附加到 Agent
    agent_cfg.height = 1.5  # 设置 Agent 高度为 1.5 米（用于碰撞检测）
    agent_cfg.radius = 0.18  # 设置 Agent 半径为 0.18 米（Agent 被视为圆柱体）
    
    # 定义动作空间：指定 Agent 可以执行的所有动作
    agent_cfg.action_space = {
        "move_forward": habitat_sim.agent.ActionSpec(  # 定义"前进"动作
            "move_forward",
            habitat_sim.agent.ActuationSpec(amount=0.25)  # 动作参数：每次移动 0.25 米（Habitat 预定义的动作类型）
        ),
        "turn_left": habitat_sim.agent.ActionSpec(  # 定义"左转"动作
            "turn_left",
            habitat_sim.agent.ActuationSpec(amount=10.0)  # 动作参数：每次左转 10 度
        ),
        "turn_right": habitat_sim.agent.ActionSpec(  # 定义"右转"动作
            "turn_right",
            habitat_sim.agent.ActuationSpec(amount=10.0)  # 动作参数：每次右转 10 度
        ),
    }
    return agent_cfg
```

### 步骤 4: 初始化 Simulator

最后，我们将这些配置打包给 `habitat_sim.Simulator`：

```python
# 步骤 1: 创建 Simulator 配置
sim_cfg = create_simulator_config()  # 调用函数创建 Simulator 配置对象

# 步骤 2: 创建传感器配置
sensor_specs = create_sensor_specs()  # 调用函数创建传感器规格列表

# 步骤 3: 创建 Agent 配置（需要传入传感器规格）
agent_cfg = create_agent_config(sensor_specs)  # 调用函数创建 Agent 配置对象

# 步骤 4: 将所有配置组合并初始化 Simulator
hab_cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])  # 创建总配置对象，包含 Simulator 配置和 Agent 配置列表
sim = habitat_sim.Simulator(hab_cfg)  # 使用配置对象创建并初始化 Simulator 实例

# 步骤 5: 如果场景文件存在，尝试加载 NavMesh（导航网格）
scene_path = "data/scene_datasets/habitat-test-scenes/skokloster-castle.glb"  # 场景文件路径
if os.path.exists(scene_path):  # 检查场景文件是否存在
    navmesh_path = scene_path.replace(".glb", ".navmesh")  # 将 .glb 扩展名替换为 .navmesh，得到 NavMesh 文件路径
    if os.path.exists(navmesh_path):  # 检查 NavMesh 文件是否存在
        sim.pathfinder.load_nav_mesh(navmesh_path)  # 加载 NavMesh 文件到路径查找器
        if sim.pathfinder.is_loaded:  # 检查 NavMesh 是否成功加载
            print("✓ NavMesh 加载成功")  # 打印成功消息
```

舞台已经搭建完毕（无端）！
> 好吧其实还有语义信息啥的

### 步骤 5: 初始化 Agent

设置 Agent 的初始位置和朝向：

```python
# 初始化 Agent（参数 0 表示第一个 Agent，Simulator 可以支持多个 Agent）
agent = sim.initialize_agent(0)  # 从 Simulator 中初始化并获取 Agent 对象

# 创建 Agent 状态对象，用于设置 Agent 的位置和旋转
agent_state = habitat_sim.AgentState()  # 创建空的 Agent 状态对象

# 如果场景有 NavMesh，获取一个随机可导航点作为起始位置
if sim.pathfinder.is_loaded:
    agent_state.position = sim.pathfinder.get_random_navigable_point()  # 从 NavMesh 中随机获取一个可导航点作为起始位置
else:  # 如果没有 NavMesh
    agent_state.position = np.array([0.0, 0.0, 0.0])  # 使用原点 [0, 0, 0] 作为默认起始位置

# 设置初始朝向（使用四元数表示旋转）
import quaternion  # 导入四元数库（如果之前未导入）
# from_euler_angles(roll, pitch, yaw): 从欧拉角创建四元数
# 参数：roll=0（绕 x 轴旋转），pitch=π/2（绕 y 轴旋转 90 度），yaw=0（绕 z 轴旋转）
agent_state.rotation = quaternion.from_euler_angles(0, np.pi / 2, 0)  # 设置 Agent 的初始旋转

# 将状态应用到 Agent
agent.set_state(agent_state)  # 使用 set_state 方法将位置和旋转应用到 Agent
```


## 动作空间

正如前面所提到的，在 Habitat-Sim 中，机器人的动作不是随意发生的，而是被严格定义在**动作空间（Action Space）**里的。

### 1. 定义动作：ActionSpace 与 ActuationSpec

我们需要告诉模拟器：这个机器人能做什么？每次动多远？

在 `create_agent_config()` 函数中，我们为 Agent 绑定了一个字典，定义了三个基础动作。这里的 `amount` 参数非常关键，它决定了机器人步子的大小和转弯的幅度。

```python
# 在 create_agent_config() 中定义动作空间
agent_cfg.action_space = {  # 创建一个字典，键是动作名称，值是动作规格
    "move_forward": habitat_sim.agent.ActionSpec(  # 定义"前进"动作的规格
        "move_forward",  # 动作名称字符串
        habitat_sim.agent.ActuationSpec(amount=0.25)  # 动作执行参数：每次移动 0.25 米
    ),
    "turn_left": habitat_sim.agent.ActionSpec(  # 定义"左转"动作的规格
        "turn_left",  # 动作名称字符串
        habitat_sim.agent.ActuationSpec(amount=10.0)  # 动作执行参数：每次左转 10 度
    ),
    "turn_right": habitat_sim.agent.ActionSpec(  # 定义"右转"动作的规格
        "turn_right",  # 动作名称字符串
        habitat_sim.agent.ActuationSpec(amount=10.0)  # 动作执行参数：每次右转 10 度
    ),
}
```

**关键参数说明：**

- `amount=0.25`：每次 `move_forward` 移动 0.25 米
- `amount=10.0`：每次 `turn_left` 或 `turn_right` 旋转 10 度
- 可以根据任务需求调整这些参数，例如更小的步长适合精细导航

### 2. 执行动作：核心指令 `sim.step()`

定义完动作后，如何驱动它呢？Habitat-Sim 提供了一个非常简洁的接口：`sim.step(action_name)`。

当你调用这个函数时，模拟器内部会发生三件事：

1. **物理更新**：根据动作改变 Agent 的位置或朝向
2. **状态同步**：更新 Agent 的内部坐标
3. **重新渲染**：所有传感器（RGB、深度等）重新生成当前位置的观察结果

```python
# 执行动作并获取观察
# sim.step() 是核心方法：执行指定动作，更新 Agent 状态，重新渲染所有传感器，返回观察结果
observations = sim.step("move_forward")  # 执行"前进"动作，返回包含所有传感器观察的字典

# 从观察字典中获取不同传感器的观察结果
rgb_obs = observations["color_sensor"]  # 获取 RGB 颜色传感器的观察结果（numpy 数组，形状为 [height, width, 3]）
depth_obs = observations["depth_sensor"]  # 获取深度传感器的观察结果（numpy 数组，形状为 [height, width]）

# 执行旋转动作
observations = sim.step("turn_left")  # 执行"左转"动作，Agent 会旋转 10 度，返回新的观察结果

# 查看 Agent 当前状态（位置和旋转）
agent_state = agent.get_state()  # 获取 Agent 的当前状态对象
print(f"位置: {agent_state.position}")  # 打印 Agent 的当前位置坐标 [x, y, z]
print(f"旋转: {agent_state.rotation}")  # 打印 Agent 的当前旋转（四元数表示）
```

### 3. 动作序列示例

在实际应用中，我们通常需要执行一系列动作：

```python
# 定义动作序列：按顺序执行的一系列动作
action_sequence = [  # 创建一个动作名称列表
    "move_forward",  # 第 1 步：前进
    "move_forward",  # 第 2 步：继续前进
    "turn_left",  # 第 3 步：左转
    "move_forward",  # 第 4 步：前进
    "turn_right",  # 第 5 步：右转
    "move_forward",  # 第 6 步：前进
]

# 执行动作序列并收集观察
for i, action in enumerate(action_sequence):  # 遍历动作序列，i 是索引，action 是动作名称
    observations = sim.step(action)  # 执行当前动作，获取观察结果
    rgb_obs = observations["color_sensor"]  # 从观察结果中提取 RGB 图像
    
    # 可以在这里保存图像、记录状态等
    print(f"步骤 {i+1}: 执行 {action}")  # 打印当前执行的步骤编号和动作名称
    print(f"  位置: {agent.get_state().position}")  # 打印 Agent 执行动作后的位置
```

**注意事项：**

- 动作名称必须与 `action_space` 中定义的键完全匹配
- 如果动作导致碰撞，Agent 可能不会移动（取决于配置）
- 每次 `step()` 都会返回所有传感器的观察结果


## NavMesh 导航网格

现在的机器人虽然能动了，但它就像一个蒙着眼睛在紫金港里乱跑的孩子，根本不知道哪里是墙，哪里是空地。要让它学会"看路"，我们需要引入具身智能中极其核心的概念：**NavMesh（导航网格）**。

NavMesh 定义了场景中的可导航区域，让 Agent 知道哪些地方可以走，哪些地方是障碍物。

### NavMesh 基础操作

```python
def demonstrate_navmesh_operations(sim):
    """演示 NavMesh 操作"""
    if not sim.pathfinder.is_loaded:  # 检查 NavMesh 是否已加载
        print("NavMesh 未加载，跳过导航演示")  # 如果未加载，打印提示信息
        return  # 提前返回，不执行后续操作
    
    # 操作 1: 获取随机可导航点
    random_point = sim.pathfinder.get_random_navigable_point()  # 从 NavMesh 中随机选择一个可导航点
    print(f"随机可导航点: {random_point}")  # 打印随机点的坐标 [x, y, z]
    
    # 操作 2: 检查点是否可导航
    is_nav = sim.pathfinder.is_navigable(random_point)  # 检查指定点是否在可导航区域内
    print(f"该点是否可导航: {is_nav}")  # 打印检查结果（True 或 False）
    
    # 操作 3: 将任意点吸附到最近的导航点
    test_point = np.array([1.0, 0.5, 1.0])  # 创建一个测试点（可能不在 NavMesh 上）
    snapped_point = sim.pathfinder.snap_point(test_point)  # 将测试点吸附到最近的 NavMesh 点
    print(f"测试点 {test_point} 被吸附到: {snapped_point}")  # 打印吸附后的点坐标
    
    # 操作 4: 计算到最近障碍物的距离
    distance = sim.pathfinder.distance_to_closest_obstacle(  # 计算指定点到最近障碍物的距离
        random_point,  # 查询点坐标
        max_search_radius=2.0  # 最大搜索半径（米），在此范围内查找障碍物
    )
    print(f"到最近障碍物的距离: {distance:.3f} 米")  # 打印距离（保留 3 位小数）
    
    # 操作 5: 查找两点之间的最短路径
    start_point = sim.pathfinder.get_random_navigable_point()  # 随机选择起点
    end_point = sim.pathfinder.get_random_navigable_point()  # 随机选择终点
    
    path = habitat_sim.ShortestPath()  # 创建最短路径对象
    path.requested_start = start_point  # 设置路径的起始点
    path.requested_end = end_point  # 设置路径的终点
    
    found_path = sim.pathfinder.find_path(path)  # 在 NavMesh 上查找从起点到终点的最短路径
    if found_path:  # 如果找到路径
        print(f"找到路径，长度: {len(path.points)} 个点")  # 打印路径包含的点的数量
        print(f"路径距离: {path.geodesic_distance:.3f} 米")  # 打印路径的测地距离（保留 3 位小数）
    else:  # 如果未找到路径
        print("未找到路径（两点可能不在同一连通区域）")  # 打印提示信息
```

## 完整示例：主函数

下面是一个完整的示例，展示了从配置到运行的完整流程：

```python
def main():
    """主函数：演示完整的 Habitat-Sim 使用流程"""
    # 步骤 1: 创建 Simulator 配置
    print("\n[步骤 1] 创建 Simulator 配置...")  # 打印步骤提示
    sim_cfg = create_simulator_config()  # 调用函数创建 Simulator 配置
    
    # 步骤 2: 创建传感器配置
    print("[步骤 2] 创建传感器配置...")  # 打印步骤提示
    sensor_specs = create_sensor_specs()  # 调用函数创建传感器规格列表
    print(f"  配置了 {len(sensor_specs)} 个传感器")  # 打印传感器数量
    
    # 步骤 3: 创建 Agent 配置
    print("[步骤 3] 创建 Agent 配置...")  # 打印步骤提示
    agent_cfg = create_agent_config(sensor_specs)  # 调用函数创建 Agent 配置（传入传感器规格）
    
    # 步骤 4: 创建 Configuration 并初始化 Simulator
    print("[步骤 4] 初始化 Simulator...")  # 打印步骤提示
    hab_cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])  # 创建总配置对象，包含 Simulator 和 Agent 配置
    sim = habitat_sim.Simulator(hab_cfg)  # 使用配置创建并初始化 Simulator
    print("  Simulator 初始化成功！")  # 打印成功消息
    
    # 如果场景文件存在，尝试加载 NavMesh
    scene_path = "data/scene_datasets/habitat-test-scenes/skokloster-castle.glb"  # 场景文件路径
    if os.path.exists(scene_path):  # 检查场景文件是否存在
        navmesh_path = scene_path.replace(".glb", ".navmesh")  # 将扩展名替换为 .navmesh
        if os.path.exists(navmesh_path):  # 检查 NavMesh 文件是否存在
            print(f"  加载 NavMesh: {navmesh_path}")  # 打印加载信息
            sim.pathfinder.load_nav_mesh(navmesh_path)  # 加载 NavMesh 文件
            if sim.pathfinder.is_loaded:  # 检查是否加载成功
                print("  ✓ NavMesh 加载成功")  # 打印成功消息
            else:  # 如果加载失败
                print("  ✗ NavMesh 加载失败")  # 打印失败消息
    
    # 步骤 5: 初始化 Agent
    print("[步骤 5] 初始化 Agent...")  # 打印步骤提示
    agent = sim.initialize_agent(0)  # 初始化第一个 Agent（索引为 0）
    agent_state = habitat_sim.AgentState()  # 创建 Agent 状态对象
    if sim.pathfinder.is_loaded:  # 如果 NavMesh 已加载
        agent_state.position = sim.pathfinder.get_random_navigable_point()  # 从 NavMesh 获取随机可导航点
    else:  # 如果没有 NavMesh
        agent_state.position = np.array([0.0, 0.0, 0.0])  # 使用原点作为起始位置
    agent_state.rotation = quaternion.from_euler_angles(0, np.pi / 2, 0)  # 设置初始旋转（绕 y 轴转 90 度）
    agent.set_state(agent_state)  # 将状态应用到 Agent
    print("  Agent 初始化成功！")  # 打印成功消息
    
    # 步骤 6: 演示 NavMesh 操作
    print("\n[步骤 6] NavMesh 操作演示...")  # 打印步骤提示
    demonstrate_navmesh_operations(sim)  # 调用函数演示 NavMesh 的各种操作
    
    # 步骤 7: 演示动作和观察
    print("\n[步骤 7] 动作执行和观察获取演示...")  # 打印步骤提示
    action_sequence = [  # 定义动作序列
        "move_forward",  # 前进
        "move_forward",  # 继续前进
        "turn_left",  # 左转
        "move_forward",  # 前进
        "turn_right",  # 右转
        "move_forward",  # 前进
    ]
    
    for i, action in enumerate(action_sequence):  # 遍历动作序列
        observations = sim.step(action)  # 执行动作，获取观察结果
        rgb_obs = observations["color_sensor"]  # 提取 RGB 图像观察
        depth_obs = observations["depth_sensor"]  # 提取深度图观察
        
        agent_state = agent.get_state()  # 获取 Agent 当前状态
        print(f"步骤 {i+1}: 执行 {action}")  # 打印执行的步骤和动作
        print(f"  位置: {agent_state.position}")  # 打印 Agent 的位置
    
    # 清理资源
    print("\n[清理] 关闭 Simulator...")  # 打印清理提示
    sim.close()  # 关闭 Simulator，释放资源
    print("  完成！")  # 打印完成消息
    
    print("\n" + "=" * 60)  # 打印分隔线
    print("示例运行完成！")  # 打印完成消息
    print("=" * 60)  # 打印分隔线

if __name__ == "__main__":  # 如果脚本被直接运行（而不是被导入）
    main()  # 调用主函数
```

## 运行效果
```
(falcon) root@autodl-container-1421458302-28c491f1:~/autodl-tmp/habitat-lab# vglrun -d :1 python examples/learn_habitat_sim_basic.py 
[W interface.cpp:47] Warning: Loading nvfuser library failed with: Error in dlopen: libnvfuser_codegen.so: cannot open shared object file: No such file or directory (function LoadingNvfuserLibrary)
找到场景文件：/root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes/skokloster-castle.glb
============================================================
Habitat-Sim 基础学习示例
============================================================

[步骤 1] 创建 Simulator 配置...
找到 NavMesh 文件：/root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes/skokloster-castle.navmesh
[步骤 2] 创建传感器配置...
  配置了 3 个传感器
[步骤 3] 创建 Agent 配置...
[步骤 4] 初始化 Simulator...
Renderer: NVIDIA GeForce RTX 4090/PCIe/SSE2 by NVIDIA Corporation
OpenGL version: 4.6.0 NVIDIA 580.76.05
Using optional features:
    GL_ARB_vertex_array_object
    GL_ARB_separate_shader_objects
    GL_ARB_robustness
    GL_ARB_texture_storage
    GL_ARB_texture_view
    GL_ARB_framebuffer_no_attachments
    GL_ARB_invalidate_subdata
    GL_ARB_texture_storage_multisample
    GL_ARB_multi_bind
    GL_ARB_direct_state_access
    GL_ARB_get_texture_sub_image
    GL_ARB_texture_filter_anisotropic
    GL_KHR_debug
    GL_KHR_parallel_shader_compile
    GL_NV_depth_buffer_float
Using driver workarounds:
    no-forward-compatible-core-context
    nv-egl-incorrect-gl11-function-pointers
    no-layout-qualifiers-on-old-glsl
    nv-zero-context-profile-mask
    nv-implementation-color-read-format-dsa-broken
    nv-cubemap-inconsistent-compressed-image-size
    nv-cubemap-broken-full-compressed-image-query
    nv-compressed-block-size-in-bits
[21:39:25:443574]:[Warning]:[Metadata] SceneDatasetAttributes.cpp(107)::addNewSceneInstanceToDataset : Dataset : 'default' : Lighting Layout Attributes 'no_lights' specified in Scene Attributes but does not exist in dataset, so creating default.
[21:39:25:444546]:[Warning]:[Scene] SemanticScene.h(331)::checkFileExists : ::loadSemanticSceneDescriptor: File `/root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes/skokloster-castle.scn` does not exist.  Aborting load.
[21:39:25:444809]:[Warning]:[Scene] SemanticScene.cpp(123)::loadSemanticSceneDescriptor : SSD File Naming Issue! Neither SemanticAttributes-provided name : `/root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes/skokloster-castle.scn` nor constructed filename : `/root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes/info_semantic.json` exist on disk.
[21:39:25:444823]:[Error]:[Scene] SemanticScene.cpp(139)::loadSemanticSceneDescriptor : SSD Load Failure! File with SemanticAttributes-provided name `/root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes/skokloster-castle.scn` exists but failed to load.
[21:39:26:677340]:[Warning]:[Sim] Simulator.cpp(595)::instanceStageForSceneAttributes : The active scene does not contain semantic annotations : activeSemanticSceneID_ = 0
  Simulator 初始化成功！
  加载 NavMesh: /root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes/skokloster-castle.navmesh
  ✓ NavMesh 加载成功
[步骤 5] 初始化 Agent...
Agent 初始位置（可导航点）: Vector(-3.01339, 0.0462302, 7.30645)
  Agent 初始化成功！

[步骤 6] NavMesh 操作演示...

=== NavMesh 操作演示 ===
随机可导航点: Vector(1.36624, 0.163874, 11.2628)
该点是否可导航: True
测试点 [1.  0.5 1. ] 被吸附到: Vector(nan, nan, nan)
到最近障碍物的距离: 1.900 米
找到路径，长度: 2 个点
路径距离: 6.084 米

[步骤 7] 动作执行和观察获取演示（单个示例）...

=== 动作执行和观察获取演示 ===
  序列类型: explore, 长度: medium
  动作数量: 30
  视频将保存到: examples/videos/habitat_sim_basic_demo.mp4
  执行动作 1/30: move_forward
  执行动作 6/30: move_forward
    位置: [-4.501998    0.04775214  7.4366913 ]
  执行动作 11/30: move_forward
  执行动作 16/30: move_forward
    位置: [-5.994402    0.02788228  7.5235157 ]
  执行动作 21/30: move_forward
  执行动作 26/30: move_forward
  执行动作 30/30: move_forward
    位置: [-7.483008    0.06496137  7.653751  ]

✓ 视频已保存：examples/videos/habitat_sim_basic_demo.mp4
  总帧数: 30
  视频时长: 3.0 秒（按 10 FPS 计算）

[步骤 8] 生成多个动作序列视频（不同参数配置）...

============================================================
生成多个动作序列视频（不同参数配置）
============================================================

--- 配置 1/6: 探索序列（短） ---
  序列类型: explore
  序列长度: short
  起始位置: Vector(-4.11908, 0.0274962, 24.0097)

=== 动作执行和观察获取演示 ===
  序列类型: explore, 长度: short
  动作数量: 15
  视频将保存到: examples/videos/habitat_sim_basic_demo_explore_short.mp4
  执行动作 1/15: move_forward
  执行动作 6/15: move_forward
    位置: [-5.6076851e+00  9.9186003e-03  2.4154087e+01]
  执行动作 11/15: move_forward
  执行动作 15/15: move_forward

✓ 视频已保存：examples/videos/habitat_sim_basic_demo_explore_short.mp4
  总帧数: 15
  视频时长: 1.5 秒（按 10 FPS 计算）

--- 配置 2/6: 探索序列（中） ---
  序列类型: explore
  序列长度: medium
  起始位置: Vector(-1.89325, 0.0399331, 7.11335)

=== 动作执行和观察获取演示 ===
  序列类型: explore, 长度: medium
  动作数量: 30
  视频将保存到: examples/videos/habitat_sim_basic_demo_explore_medium.mp4
  执行动作 1/30: move_forward
  执行动作 6/30: move_forward
    位置: [-3.3818605   0.05504228  7.2435856 ]
  执行动作 11/30: move_forward
  执行动作 16/30: move_forward
    位置: [-4.8742642  0.0366052  7.33041  ]
  执行动作 21/30: move_forward
  执行动作 26/30: move_forward
  执行动作 30/30: move_forward
    位置: [-6.36287     0.01889712  7.460645  ]

✓ 视频已保存：examples/videos/habitat_sim_basic_demo_explore_medium.mp4
  总帧数: 30
  视频时长: 3.0 秒（按 10 FPS 计算）

--- 配置 3/6: 探索序列（长） ---
  序列类型: explore
  序列长度: long
  起始位置: Vector(5.61447, 0.209919, 8.58094)

=== 动作执行和观察获取演示 ===
  序列类型: explore, 长度: long
  动作数量: 45
  视频将保存到: examples/videos/habitat_sim_basic_demo_explore_long.mp4
  执行动作 1/45: move_forward
  执行动作 6/45: move_forward
    位置: [4.1258607  0.15786768 8.711177  ]
  执行动作 11/45: move_forward
  执行动作 16/45: move_forward
    位置: [2.6334567  0.11300281 8.798001  ]
  执行动作 21/45: move_forward
  执行动作 26/45: move_forward
    位置: [1.1448507  0.09321284 8.928238  ]
  执行动作 31/45: move_forward
  执行动作 36/45: move_forward
    位置: [-0.34375522  0.0987659   9.058475  ]
  执行动作 41/45: move_forward
  执行动作 45/45: move_forward

✓ 视频已保存：examples/videos/habitat_sim_basic_demo_explore_long.mp4
  总帧数: 45
  视频时长: 4.5 秒（按 10 FPS 计算）

--- 配置 4/6: 直线移动序列 ---
  序列类型: straight
  序列长度: medium
  起始位置: Vector(0.854421, 0.205727, 20.1616)

=== 动作执行和观察获取演示 ===
  序列类型: straight, 长度: medium
  动作数量: 18
  视频将保存到: examples/videos/habitat_sim_basic_demo_straight_medium.mp4
  执行动作 1/18: move_forward
  执行动作 6/18: move_forward
    位置: [-1.6455785   0.07717022 20.161594  ]
  执行动作 11/18: move_forward
  执行动作 16/18: move_forward
  执行动作 18/18: move_forward

✓ 视频已保存：examples/videos/habitat_sim_basic_demo_straight_medium.mp4
  总帧数: 18
  视频时长: 1.8 秒（按 10 FPS 计算）

--- 配置 5/6: 螺旋移动序列 ---
  序列类型: spiral
  序列长度: long
  起始位置: Vector(6.36006, 0.209919, 12.2694)

=== 动作执行和观察获取演示 ===
  序列类型: spiral, 长度: long
  动作数量: 45
  视频将保存到: examples/videos/habitat_sim_basic_demo_spiral_long.mp4
  执行动作 1/45: move_forward
  执行动作 6/45: turn_left
    位置: [ 5.220917    0.20991862 12.5738535 ]
  执行动作 11/45: move_forward
  执行动作 16/45: move_forward
    位置: [ 4.622362    0.20991862 13.624757  ]
  执行动作 21/45: turn_left
  执行动作 26/45: move_forward
    位置: [ 5.0408373   0.20991862 14.67469   ]
  执行动作 31/45: move_forward
  执行动作 36/45: turn_left
    位置: [ 5.0408373   0.20991862 15.089305  ]
  执行动作 41/45: move_forward
  执行动作 45/45: move_forward

✓ 视频已保存：examples/videos/habitat_sim_basic_demo_spiral_long.mp4
  总帧数: 45
  视频时长: 4.5 秒（按 10 FPS 计算）

--- 配置 6/6: 随机移动序列（超长） ---
  序列类型: random
  序列长度: very_long
  起始位置: Vector(2.71929, 0.0847474, 21.7149)

=== 动作执行和观察获取演示 ===
  序列类型: random, 长度: very_long
  动作数量: 75
  视频将保存到: examples/videos/habitat_sim_basic_demo_random_very_long.mp4
  执行动作 1/75: move_forward
  执行动作 6/75: turn_right
    位置: [ 1.4768887   0.19570619 21.628056  ]
  执行动作 11/75: move_forward
  执行动作 16/75: move_forward
    位置: [7.1575046e-03 1.0214768e-01 2.1368906e+01]
  执行动作 21/75: turn_right
  执行动作 26/75: move_forward
    位置: [-1.190016    0.05557493 21.02557   ]
  执行动作 31/75: move_forward
  执行动作 36/75: turn_right
    位置: [-2.3277984   0.10618767 20.519056  ]
  执行动作 41/75: move_forward
  执行动作 46/75: move_forward
    位置: [-3.6202586   0.22896682 19.772856  ]
  执行动作 51/75: turn_right
  执行动作 56/75: move_forward
    位置: [-4.6278048  0.2668427 19.040768 ]
  执行动作 61/75: move_forward
  执行动作 66/75: turn_right
    位置: [-5.523732    0.26123795 18.175657  ]
  执行动作 71/75: move_forward
  执行动作 75/75: move_forward

✓ 视频已保存：examples/videos/habitat_sim_basic_demo_random_very_long.mp4
  总帧数: 75
  视频时长: 7.5 秒（按 10 FPS 计算）

============================================================
多动作序列生成完成
============================================================
成功生成 6 个动作序列视频：
  - explore_short: 1.5秒 (探索序列（短）)
  - explore_medium: 3.0秒 (探索序列（中）)
  - explore_long: 4.5秒 (探索序列（长）)
  - straight_medium: 1.8秒 (直线移动序列)
  - spiral_long: 4.5秒 (螺旋移动序列)
  - random_very_long: 7.5秒 (随机移动序列（超长）)

[清理] 关闭 Simulator...
  完成！

============================================================
示例运行完成！
============================================================

输出文件：
  - 动作序列视频：examples/videos/habitat_sim_basic_demo_*.mp4
```

## 后续学习

