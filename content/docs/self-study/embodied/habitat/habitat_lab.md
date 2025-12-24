---
title: "Habitat-Lab"
weight: 4
---


## Why Habitat-Lab？

在 Habitat-Sim 里，我们只是在手动控制机器人。但在强化学习（RL）中，我们需要：

- **Episode（回合）**：从哪儿开始？到哪儿结束？
- **Task（任务）**：目标是什么？（比如 PointNav：去坐标 [x, y]）
- **Metrics（度量）**：走得好不好？（成功率、路径效率 SPL）

Habitat-Lab 正是为了解决这些问题而生的。它是 Habitat-Sim 的高级封装，提供了完整的强化学习环境接口。

## 核心概念：Env、Task、Simulator

Habitat-Lab 的核心架构可以总结为三个层次：

1. **Env（环境）**：高层抽象，封装了任务执行所需的所有组件
2. **Task（任务）**：定义了具体的任务目标、观察空间、奖励函数
3. **Simulator（模拟器）**：底层的 Habitat-Sim，负责场景渲染和物理仿真

## 完整流程示例

这个示例展示了如何通过实际代码学习 Habitat-Lab 的核心概念：

1. 使用 `habitat.Env` 创建环境
2. 理解配置系统（Config）
3. 执行动作并获取观察结果
4. 理解 Episode、Task、Simulator 的关系

### 步骤 1: 导入必要的库

首先，我们需要导入所有必要的库和模块：

```python
import os
import sys
import time
import numpy as np 
import cv2

# 尝试导入 imageio 用于视频保存（可选功能）
try:
    import imageio
    HAS_IMAGEIO = True 
except ImportError:
    HAS_IMAGEIO = False 
    print("警告：未安装 imageio，视频保存功能将不可用。安装方法：pip install imageio imageio-ffmpeg")

# 导入 habitat-lab 核心模块
import habitat  # Habitat-Lab 核心库，提供高级环境接口
from habitat.config import read_write  # 配置读写上下文管理器，用于修改配置
from habitat.sims.habitat_simulator.actions import HabitatSimActions  # Habitat-Sim 动作类型枚举
```

### 步骤 2: 配置数据路径

在实际使用中，我们需要指定场景数据集和任务数据集的路径：

```python
# 数据路径配置（根据实际情况修改这些路径）
SCENE_DATASETS_PATH = "/root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes"  # 场景数据集根目录路径
POINTNAV_DATASET_PATH = "/root/autodl-tmp/SocialNav-Map/Falcon/data/datasets/pointnav/habitat-test-scenes"  # PointNav 任务数据集路径

def setup_data_paths(config):
    """
    设置数据路径
    
    这个函数用于将配置文件中的数据路径替换为用户指定的实际路径
    
    参数:
        config: Habitat 配置对象，需要修改其中的路径设置
    返回:
        config: 修改后的配置对象
    """
    with read_write(config):  # 使用 read_write 上下文管理器，允许修改配置对象
        # 设置场景数据集路径（scenes_dir）
        # 对于 pointnav，场景路径通常通过 scenes_dir 设置
        scenes_dir = os.path.dirname(SCENE_DATASETS_PATH)  # 获取场景数据集的父目录路径
        if hasattr(config.habitat.dataset, 'scenes_dir'):  # 检查配置对象是否有 scenes_dir 属性
            config.habitat.dataset.scenes_dir = scenes_dir  # 设置场景数据集目录路径
        # 也可以通过 simulator 的 scene_dataset 设置
        if hasattr(config.habitat.simulator, 'scene_dataset'):  # 检查配置对象是否有 scene_dataset 属性
            # scene_dataset 通常设置为 "default" 或场景数据集名称
            pass  # 这里不做额外处理，保持默认值
        
        # 设置数据集路径
        original_data_path = config.habitat.dataset.data_path  # 获取原始数据集路径
        # 检查是否需要替换路径（匹配任何包含 habitat-test-scenes 的路径）
        if "habitat-test-scenes" in original_data_path:  # 如果原始路径包含 habitat-test-scenes
            # 提取 split 部分（如 "train", "val"）
            split = config.habitat.dataset.split  # 获取数据集分割类型（train/val/test）
            # 构建完整的数据集路径（使用绝对路径）
            new_data_path = os.path.join(  # 拼接路径组件
                POINTNAV_DATASET_PATH,  # PointNav 数据集根目录
                "v1",  # 数据集版本号
                split,  # 数据集分割（train/val/test）
                f"{split}.json.gz"  # 数据集文件名（如 train.json.gz）
            )
            # 检查文件是否存在，如果不存在，尝试其他可能的路径
            if not os.path.exists(new_data_path):  # 如果新路径的文件不存在
                # 尝试直接使用数据集目录下的文件
                alt_path = os.path.join(POINTNAV_DATASET_PATH, f"{split}.json.gz")  # 构建备用路径
                if os.path.exists(alt_path):  # 如果备用路径存在
                    new_data_path = alt_path  # 使用备用路径
                else:  # 如果备用路径也不存在
                    print(f"警告: 数据集文件不存在: {new_data_path}")  # 打印警告信息
                    print(f"      尝试使用原始路径: {original_data_path}")  # 提示使用原始路径
            else:  # 如果新路径的文件存在
                # 路径设置成功，打印调试信息
                print(f"数据集路径已设置: {new_data_path}")  # 打印成功消息
            # 使用绝对路径
            config.habitat.dataset.data_path = os.path.abspath(new_data_path)  # 设置配置中的数据集路径为绝对路径
    
    return config  # 返回修改后的配置对象
```

### 步骤 3: 基本环境使用

这是最基础的示例，展示了如何创建和使用 Habitat-Lab 环境：

```python
def example_1_basic_env_usage():
    """
    示例 1: 最基本的 Habitat-Lab 环境使用
    
    这个示例展示了：
    - 如何使用配置文件创建环境
    - 如何重置环境并获取初始观察
    - 如何执行动作并获取新的观察
    """
    print("=" * 60)  # 打印分隔线（60 个等号）
    print("示例 1: 基本环境使用")  # 打印示例标题
    print("=" * 60)  # 打印分隔线
    
    # 步骤 1: 获取配置
    # habitat.get_config 使用 Hydra 配置管理系统
    # 配置文件路径相对于 habitat-lab/habitat/config/
    config = habitat.get_config(  # 获取 Habitat-Lab 配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"  # 配置文件路径（PointNav 任务的测试配置）
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 调用函数设置实际的数据路径
    
    print(f"\n配置信息:")  # 打印配置信息标题
    print(f"  - 任务类型: {config.habitat.task.type}")  # 打印任务类型
    print(f"  - 模拟器类型: {config.habitat.simulator.type}")  # 打印模拟器类型
    print(f"  - 数据集类型: {config.habitat.dataset.type}")  # 打印数据集类型
    print(f"  - 最大步数: {config.habitat.environment.max_episode_steps}")  # 打印每个 Episode 的最大步数
    
    # 步骤 2: 创建环境
    # Env 类抽象了处理 embodied task 所需的所有信息：
    # - dataset (episodes): 任务实例数据
    # - simulator (sim): 底层模拟器
    # - embodied_task (task): 任务定义
    env = habitat.Env(config=config)  # 使用配置创建 Habitat-Lab 环境对象
    
    print(f"\n环境创建成功!")  # 打印成功消息
    print(f"  - 观察空间: {list(env.observation_space.spaces.keys())}")  # 打印观察空间中的所有传感器名称
    print(f"  - 动作空间: {list(env.action_space.spaces.keys())}")  # 打印动作空间中所有可用的动作名称
    
    # 步骤 3: 重置环境，开始新的 episode
    observations = env.reset()  # 重置环境，开始新的 Episode，返回初始观察结果字典
    
    print(f"\nEpisode 开始:")  # 打印 Episode 开始提示
    print(f"  - 当前 Episode ID: {env.current_episode.episode_id}")  # 打印当前 Episode 的唯一标识符
    print(f"  - 场景: {env.current_episode.scene_id}")  # 打印当前 Episode 使用的场景 ID
    print(f"  - 起始位置: {env.current_episode.start_position}")  # 打印 Agent 的起始位置坐标 [x, y, z]
    print(f"  - 目标位置: {env.current_episode.goals[0].position}")  # 打印第一个目标的位置坐标（PointNav 任务只有一个目标）
    
    # 步骤 4: 执行一些动作
    print(f"\n执行动作...")  # 打印动作执行提示
    step_count = 0  # 初始化步数计数器
    max_steps = 5000  # 设置最大步数限制（防止无限循环）
    min_duration = 10.0  # 设置最小运行时间（秒），确保示例运行足够长时间
    start_time = time.time()  # 记录开始时间
    
    while not env.episode_over and step_count < max_steps:  # 循环条件：Episode 未结束且未超过最大步数
        elapsed_time = time.time() - start_time  # 计算已运行的时间（秒）
        if elapsed_time >= min_duration:  # 如果已达到最小运行时间
            break  # 退出循环
        # 获取观察结果中的导航信息
        if "pointgoal_with_gps_compass" in observations:  # 如果观察结果中包含点目标导航信息
            distance = observations["pointgoal_with_gps_compass"][0]  # 提取到目标的距离（米）
            theta = observations["pointgoal_with_gps_compass"][1]  # 提取到目标的角度（弧度）
            print(f"  步数 {step_count}: 距离目标 {distance:.2f}m, 角度 {np.degrees(theta):.1f}°")  # 打印导航信息
        
        # 执行动作（这里使用随机动作作为示例）
        # 在实际应用中，这里应该是你的策略/模型输出的动作
        action = env.action_space.sample()  # 从动作空间中随机采样一个动作
        observations = env.step(action)  # 执行动作，更新环境状态，返回新的观察结果字典
        step_count += 1  # 步数计数器加 1
        
        # 每 20 步显示一次进度
        if step_count % 20 == 0:  # 如果步数是 20 的倍数
            elapsed = time.time() - start_time  # 计算已运行时间
            print(f"  已运行 {step_count} 步，耗时 {elapsed:.1f} 秒...")  # 打印进度信息
    
    total_time = time.time() - start_time  # 计算总运行时间
    print(f"\nEpisode 结束 (步数: {step_count}, 耗时: {total_time:.1f} 秒)")  # 打印 Episode 结束信息
    
    # 步骤 5: 获取任务度量
    metrics = env.get_metrics()  # 获取当前 Episode 的任务度量结果（成功率、SPL 等）
    print(f"\n任务度量:")  # 打印度量标题
    for key, value in metrics.items():  # 遍历所有度量项
        print(f"  - {key}: {value}")  # 打印度量名称和值
    
    env.close()  # 关闭环境，释放资源
```

### 步骤 4: 修改配置

这个示例展示了如何修改配置参数：

```python
def example_2_config_modification():
    """
    示例 2: 修改配置
    
    这个示例展示了如何使用 read_write 上下文管理器来修改配置
    """
    print("\n" + "=" * 60)  # 打印分隔线（换行 + 60 个等号）
    print("示例 2: 配置修改")  # 打印示例标题
    print("=" * 60)  # 打印分隔线
    
    # 获取默认配置
    config = habitat.get_config(  # 获取默认配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"  # 配置文件路径
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 设置实际的数据路径
    
    print(f"\n默认配置:")  # 打印默认配置标题
    print(f"  - 最大步数: {config.habitat.environment.max_episode_steps}")  # 打印默认的最大步数
    print(f"  - 数据集分割: {config.habitat.dataset.split}")  # 打印默认的数据集分割（train/val/test）
    
    # 使用 read_write 上下文管理器修改配置
    with read_write(config):  # 进入配置读写上下文，允许修改配置
        config.habitat.environment.max_episode_steps = 100  # 将最大步数修改为 100
        config.habitat.dataset.split = "val"  # 将数据集分割修改为验证集
    
    print(f"\n修改后的配置:")  # 打印修改后的配置标题
    print(f"  - 最大步数: {config.habitat.environment.max_episode_steps}")  # 打印修改后的最大步数
    print(f"  - 数据集分割: {config.habitat.dataset.split}")  # 打印修改后的数据集分割
    
    # 使用修改后的配置创建环境
    env = habitat.Env(config=config)  # 使用修改后的配置创建环境
    print(f"\n使用修改后的配置创建环境成功")  # 打印成功消息
    env.close()  # 关闭环境
```

### 步骤 5: 深入理解观察和动作

这个示例展示了如何详细查看和使用观察结果和动作：

```python
def example_3_observations_and_actions():
    """
    示例 3: 深入理解观察和动作
    
    这个示例展示了：
    - 观察空间的结构
    - 如何访问不同类型的观察
    - 动作空间的结构
    - 如何执行特定动作
    """
    print("\n" + "=" * 60)  # 打印分隔线
    print("示例 3: 观察和动作详解")  # 打印示例标题
    print("=" * 60)  # 打印分隔线
    
    config = habitat.get_config(  # 获取配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"  # 配置文件路径
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 设置实际的数据路径
    
    env = habitat.Env(config=config)  # 创建环境对象
    
    observations = env.reset()  # 重置环境，获取初始观察
    
    print(f"\n观察空间详情:")  # 打印观察空间详情标题
    for sensor_name, space in env.observation_space.spaces.items():  # 遍历所有观察空间
        print(f"  - {sensor_name}: {space}")  # 打印传感器名称和对应的空间定义
    
    print(f"\n动作空间详情:")  # 打印动作空间详情标题
    print(f"  - {env.action_space}")  # 打印动作空间的完整信息
    
    print(f"\n可用的动作:")  # 打印可用动作标题
    # HabitatSimActions 包含了所有可用的动作类型
    # 直接使用 __iter__ 方法获取动作名称（避免 dir() 触发 __getattr__ 的问题）
    for action_name in HabitatSimActions:  # 遍历 HabitatSimActions 枚举中的所有动作
        action_value = HabitatSimActions[action_name]  # 获取动作的数值
        print(f"  - {action_name}: {action_value}")  # 打印动作名称和对应的数值
    
    print(f"\n执行特定动作...")  # 打印动作执行提示
    print(f"将运行至少 10 秒...")  # 提示运行时间
    step_count = 0  # 初始化步数计数器
    max_steps = 500  # 设置最大步数限制
    min_duration = 10.0  # 设置最小运行时间（秒）
    start_time = time.time()  # 记录开始时间
    
    # 执行前进动作
    action = {"action": HabitatSimActions.move_forward}  # 创建前进动作字典（动作类型为 move_forward）
    observations = env.step(action)  # 执行前进动作，获取新的观察结果
    step_count += 1  # 步数加 1
    
    if "rgb" in observations:  # 如果观察结果中包含 RGB 图像
        rgb_image = observations["rgb"]  # 提取 RGB 图像（numpy 数组）
        print(f"  步数 {step_count}: RGB 图像形状 {rgb_image.shape}")  # 打印 RGB 图像的形状（height, width, channels）
    
    if "depth" in observations:  # 如果观察结果中包含深度图
        depth_image = observations["depth"]  # 提取深度图（numpy 数组）
        print(f"  步数 {step_count}: 深度图像形状 {depth_image.shape}")  # 打印深度图的形状（height, width）
    
    # 继续执行动作直到达到最小运行时间
    while not env.episode_over and step_count < max_steps:  # 循环条件：Episode 未结束且未超过最大步数
        elapsed_time = time.time() - start_time  # 计算已运行时间
        if elapsed_time >= min_duration:  # 如果已达到最小运行时间
            break  # 退出循环
        
        # 执行转向动作
        action = {"action": HabitatSimActions.turn_left}  # 创建左转动作字典
        observations = env.step(action)  # 执行左转动作，获取新的观察结果
        step_count += 1  # 步数加 1
        
        if step_count % 10 == 0:  # 每 10 步打印一次进度
            print(f"  步数 {step_count}: 已运行 {elapsed_time:.1f} 秒")  # 打印进度信息
    
    env.close()  # 关闭环境
```

### 步骤 6: 保存观察结果为视频

这个示例展示了如何将 RGB 和深度图像保存为视频文件：

```python
def example_4_visualization():
    """
    示例 4: 保存观察结果为视频
    
    这个示例展示了如何将 RGB 和深度图像保存为 mp4 视频文件
    """
    print("\n" + "=" * 60)  # 打印分隔线
    print("示例 4: 保存观察结果为视频")  # 打印示例标题
    print("=" * 60)  # 打印分隔线
    
    if not HAS_IMAGEIO:  # 如果 imageio 不可用
        print("\n错误: 需要安装 imageio 来保存视频")  # 打印错误消息
        print("安装方法: pip install imageio imageio-ffmpeg")  # 打印安装方法
        return  # 提前返回，不执行后续代码
    
    config = habitat.get_config(  # 获取配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"  # 配置文件路径
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 设置实际的数据路径
    
    env = habitat.Env(config=config)  # 创建环境对象
    
    observations = env.reset()  # 重置环境，获取初始观察
    
    print(f"\n开始收集观察结果...")  # 打印开始提示
    print(f"将保存为 mp4 视频文件")  # 说明保存格式
    
    # 创建输出目录
    output_dir = os.path.join("examples", "videos_lab_basic")  # 构建输出目录路径
    os.makedirs(output_dir, exist_ok=True)  # 创建输出目录（如果不存在），exist_ok=True 表示目录已存在时不报错
    
    # 存储所有帧
    rgb_frames = []  # 初始化 RGB 帧列表
    depth_frames = []  # 初始化深度帧列表
    combined_frames = []  # 初始化组合帧列表（RGB 和深度并排显示）
    
    step_count = 0  # 初始化步数计数器
    max_steps = 50  # 设置最大步数（用于生成视频的帧数）
    
    while not env.episode_over and step_count < max_steps:  # 循环条件：Episode 未结束且未超过最大步数
        frame_data = {}  # 初始化当前帧的数据字典
        
        # 收集 RGB 图像
        if "rgb" in observations:  # 如果观察结果中包含 RGB 图像
            rgb_image = observations["rgb"]  # 提取 RGB 图像（numpy 数组，BGR 格式）
            # Habitat 返回的 RGB 图像是 BGR 格式，需要转换为 RGB
            rgb_rgb = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)  # 使用 OpenCV 将 BGR 格式转换为 RGB 格式
            rgb_frames.append(rgb_rgb)  # 将转换后的 RGB 图像添加到帧列表
            frame_data["rgb"] = rgb_rgb  # 将 RGB 图像保存到帧数据字典
        
        # 收集深度图像
        if "depth" in observations:  # 如果观察结果中包含深度图
            depth_image = observations["depth"]  # 提取深度图（numpy 数组，单通道，值范围通常在 [0, 1]）
            # 深度图像是单通道的，需要转换为 3 通道用于显示
            depth_vis = (depth_image * 255).astype(np.uint8)  # 将深度值缩放到 [0, 255] 并转换为 uint8 类型
            depth_vis = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)  # 应用 JET 色彩映射（将单通道深度图转换为彩色图像）
            # 转换为 RGB 格式
            depth_rgb = cv2.cvtColor(depth_vis, cv2.COLOR_BGR2RGB)  # 将 BGR 格式转换为 RGB 格式
            depth_frames.append(depth_rgb)  # 将转换后的深度图像添加到帧列表
            frame_data["depth"] = depth_rgb  # 将深度图像保存到帧数据字典
        
        # 创建组合图像（RGB 和深度并排显示）
        if "rgb" in frame_data and "depth" in frame_data:  # 如果同时有 RGB 和深度图像
            # 确保两个图像大小相同
            rgb_img = frame_data["rgb"]  # 获取 RGB 图像
            depth_img = frame_data["depth"]  # 获取深度图像
            
            # 调整深度图像大小以匹配 RGB 图像
            if rgb_img.shape[:2] != depth_img.shape[:2]:  # 如果两个图像的高度和宽度不同
                depth_img = cv2.resize(depth_img, (rgb_img.shape[1], rgb_img.shape[0]))  # 调整深度图像大小以匹配 RGB 图像
            
            # 水平拼接
            combined = np.hstack([rgb_img, depth_img])  # 使用 NumPy 的 hstack 函数水平拼接两个图像
            combined_frames.append(combined)  # 将组合图像添加到帧列表
        
        # 执行随机动作
        action = env.action_space.sample()  # 从动作空间中随机采样一个动作
        observations = env.step(action)  # 执行动作，获取新的观察结果
        step_count += 1  # 步数加 1
        
        if step_count % 10 == 0:  # 每 10 步打印一次进度
            print(f"  已收集 {step_count} 帧...")  # 打印进度信息
    
    print(f"\n收集完成，共 {step_count} 帧")  # 打印收集完成信息
    print(f"开始保存视频...")  # 打印保存提示
    
    # 保存视频
    if rgb_frames:  # 如果有 RGB 帧
        rgb_video_path = os.path.join(output_dir, "rgb_observations.mp4")  # 构建 RGB 视频文件路径
        imageio.mimwrite(rgb_video_path, rgb_frames, fps=5, codec='libx264', quality=8)  # 使用 imageio 将 RGB 帧保存为 MP4 视频（帧率 5 fps，使用 libx264 编码器，质量 8）
        print(f"  RGB 视频已保存: {rgb_video_path}")  # 打印保存成功消息
    
    if depth_frames:  # 如果有深度帧
        depth_video_path = os.path.join(output_dir, "depth_observations.mp4")  # 构建深度视频文件路径
        imageio.mimwrite(depth_video_path, depth_frames, fps=5, codec='libx264', quality=8)  # 使用 imageio 将深度帧保存为 MP4 视频
        print(f"  深度视频已保存: {depth_video_path}")  # 打印保存成功消息
    
    if combined_frames:  # 如果有组合帧
        combined_video_path = os.path.join(output_dir, "combined_observations.mp4")  # 构建组合视频文件路径
        imageio.mimwrite(combined_video_path, combined_frames, fps=5, codec='libx264', quality=8)  # 使用 imageio 将组合帧保存为 MP4 视频
        print(f"  组合视频已保存: {combined_video_path}")  # 打印保存成功消息
    
    print(f"\n视频保存完成！")  # 打印完成消息
    print(f"视频文件保存在: {output_dir}")  # 打印保存目录
    env.close()  # 关闭环境
```

### 步骤 7: 理解核心组件

这个示例展示了如何访问和理解 Habitat-Lab 的核心组件：

```python
def example_5_understanding_components():
    """
    示例 5: 理解 Habitat-Lab 的核心组件
    
    这个示例展示了如何访问和理解：
    - Simulator: 底层模拟器
    - EmbodiedTask: 任务定义
    - Dataset: 数据集和 Episodes
    """
    print("\n" + "=" * 60)  # 打印分隔线
    print("示例 5: 理解核心组件")  # 打印示例标题
    print("=" * 60)  # 打印分隔线
    
    config = habitat.get_config(  # 获取配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"  # 配置文件路径
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 设置实际的数据路径
    
    env = habitat.Env(config=config)  # 创建环境对象
    
    print(f"\n1. Simulator (模拟器):")  # 打印模拟器标题
    print(f"  - 类型: {type(env.sim).__name__}")  # 打印模拟器类的名称
    # 注意：需要先 reset 才能获取场景信息
    observations = env.reset()  # 重置环境，加载场景
    print(f"  - 场景 ID: {env.current_episode.scene_id}")  # 打印当前场景的唯一标识符
    print(f"  - Agent 位置: {env.sim.get_agent_state().position}")  # 打印 Agent 的当前位置坐标 [x, y, z]
    print(f"  - Agent 旋转: {env.sim.get_agent_state().rotation}")  # 打印 Agent 的当前旋转（四元数）
    
    print(f"\n2. EmbodiedTask (任务):")  # 打印任务标题
    print(f"  - 类型: {type(env.task).__name__}")  # 打印任务类的名称
    print(f"  - 任务传感器: {list(env.task.sensor_suite.observation_spaces.spaces.keys())}")  # 打印任务定义的所有传感器名称
    print(f"  - 任务度量: {list(env.task.measurements.measures.keys())}")  # 打印任务定义的所有度量指标名称
    
    print(f"\n3. Dataset (数据集):")  # 打印数据集标题
    print(f"  - Episode 总数: {len(env.episodes)}")  # 打印数据集中的 Episode 总数
    print(f"  - 当前 Episode: {env.current_episode.episode_id}")  # 打印当前 Episode 的唯一标识符
    
    print(f"\n4. 执行一步后的度量:")  # 打印度量标题
    metrics = env.get_metrics()  # 获取当前 Episode 的任务度量结果
    for key, value in metrics.items():  # 遍历所有度量项
        print(f"  - {key}: {value}")  # 打印度量名称和值
    
    env.close()  # 关闭环境
```

### 主函数：运行所有示例

最后，我们创建一个主函数来运行所有示例：

```python
def main():
    """运行所有示例"""
    print("\n" + "=" * 60)  # 打印分隔线
    print("Habitat-Lab 基础学习教程")  # 打印教程标题
    print("=" * 60)  # 打印分隔线
    print("\n本教程将通过实际代码示例帮助你理解 Habitat-Lab 的核心概念")  # 打印说明文字
    print("建议按顺序运行每个示例，逐步深入理解")  # 打印建议文字
    
    try:  # 尝试执行代码，捕获可能的异常
        # 运行各个示例
        example_1_basic_env_usage()  # 运行示例 1：基本环境使用
        example_2_config_modification()  # 运行示例 2：配置修改
        
        # 可视化示例需要用户交互，可以选择性运行
        print("\n" + "=" * 60)  # 打印分隔线
        print("提示: 示例 4 (可视化) 需要用户交互")  # 打印提示信息
        print("使用 vglrun -d :1 运行时支持图形显示")  # 打印使用说明
        print("=" * 60)  # 打印分隔线
        
        # 运行可视化示例（使用 vglrun 时支持显示）
        example_4_visualization()  # 运行示例 4：保存观察结果为视频
        
        example_5_understanding_components()  # 运行示例 5：理解核心组件
        
        print("\n" + "=" * 60)  # 打印分隔线
        print("所有示例运行完成！")  # 打印完成消息
        print("=" * 60)  # 打印分隔线
        print("\n下一步学习建议:")  # 打印学习建议标题
        print("1. 查看 shortest_path_follower_example.py 了解如何使用路径跟随")  # 打印建议 1
        print("2. 查看 habitat-lab/habitat/core/env.py 了解 Env 类的实现")  # 打印建议 2
        print("3. 查看 habitat-lab/habitat/core/embodied_task.py 了解任务定义")  # 打印建议 3
        print("4. 查看配置文件了解如何自定义任务和传感器")  # 打印建议 4
        
    except Exception as e:  # 捕获所有异常
        print(f"\n错误: {e}")  # 打印错误信息
        import traceback  # 导入 traceback 模块用于打印详细的错误堆栈
        traceback.print_exc()  # 打印完整的错误堆栈信息
        sys.exit(1)  # 退出程序，返回错误代码 1

if __name__ == "__main__":  # 如果脚本被直接运行（而不是被导入为模块）
    main()  # 调用主函数
```

## 关键概念总结

### 1. Env（环境）

`habitat.Env` 是 Habitat-Lab 的最高层抽象，它封装了：
- **Dataset**：提供 Episode 数据（起始位置、目标位置等）
- **Simulator**：底层场景渲染和物理仿真
- **Task**：任务定义（观察空间、动作空间、奖励函数、度量指标）

### 2. Episode（回合）

每个 Episode 代表一个完整的任务实例：
- 有明确的起始位置和目标位置
- 有最大步数限制
- 可以通过 `env.episode_over` 检查是否结束

### 3. 观察和动作

- **观察（Observations）**：一个字典，包含所有传感器的输出（RGB、深度、导航信息等）
- **动作（Actions）**：一个字典，格式为 `{"action": action_type}`，其中 `action_type` 是 `HabitatSimActions` 枚举值

### 4. 配置系统

Habitat-Lab 使用 Hydra 配置管理系统：
- 使用 `habitat.get_config()` 加载配置
- 使用 `read_write()` 上下文管理器修改配置
- 配置包括任务、模拟器、数据集等所有参数



---


在掌握了 Habitat-Lab 的基础使用后，我们需要深入了解：

1. **RLEnv**：如何将环境与强化学习算法集成
2. **架构组件**：理解 Habitat 的内部结构和各组件的关系
3. **自定义功能**：如何扩展 Habitat-Lab，添加自定义的 Measure 和 Sensor
4. **导航策略**：使用 ShortestPathFollower 等启发式方法

## 完整流程示例

### 步骤 1: 导入必要的库

```python
import os
import sys
import numpy as np
# 导入 habitat-lab 核心模块
import habitat  # Habitat-Lab 核心库，提供高级环境接口
from habitat.config import read_write  # 配置读写上下文管理器，用于修改配置
from habitat.sims.habitat_simulator.actions import HabitatSimActions  # Habitat-Sim 动作类型枚举
from habitat.tasks.nav.shortest_path_follower import ShortestPathFollower  # 最短路径跟随器，用于启发式导航
```

### 步骤 2: 配置数据路径

与基础教程相同，我们需要配置数据路径：

```python
# 数据路径配置（根据实际情况修改这些路径）
SCENE_DATASETS_PATH = "/root/autodl-tmp/SocialNav-Map/Falcon/data/scene_datasets/habitat-test-scenes"  # 场景数据集根目录路径
POINTNAV_DATASET_PATH = "/root/autodl-tmp/SocialNav-Map/Falcon/data/datasets/pointnav/habitat-test-scenes"  # PointNav 任务数据集路径

def setup_data_paths(config):
    """
    设置数据路径
    
    这个函数用于将配置文件中的数据路径替换为用户指定的实际路径
    
    参数:
        config: Habitat 配置对象，需要修改其中的路径设置
    返回:
        config: 修改后的配置对象
    """
    with read_write(config):  # 使用 read_write 上下文管理器，允许修改配置对象
        # 设置场景数据集路径（scenes_dir）
        # 对于 pointnav，场景路径通常通过 scenes_dir 设置
        scenes_dir = os.path.dirname(SCENE_DATASETS_PATH)  # 获取场景数据集的父目录路径
        if hasattr(config.habitat.dataset, 'scenes_dir'):  # 检查配置对象是否有 scenes_dir 属性
            config.habitat.dataset.scenes_dir = scenes_dir  # 设置场景数据集目录路径
        # 也可以通过 simulator 的 scene_dataset 设置
        if hasattr(config.habitat.simulator, 'scene_dataset'):  # 检查配置对象是否有 scene_dataset 属性
            # scene_dataset 通常设置为 "default" 或场景数据集名称
            pass  # 这里不做额外处理，保持默认值
        
        # 设置数据集路径
        # 替换默认路径为用户指定的路径
        original_data_path = config.habitat.dataset.data_path  # 获取原始数据集路径
        # 检查是否需要替换路径（匹配任何包含 habitat-test-scenes 的路径）
        if "habitat-test-scenes" in original_data_path:  # 如果原始路径包含 habitat-test-scenes
            # 提取 split 部分（如 "train", "val"）
            split = config.habitat.dataset.split  # 获取数据集分割类型（train/val/test）
            # 构建完整的数据集路径（使用绝对路径）
            new_data_path = os.path.join(  # 拼接路径组件
                POINTNAV_DATASET_PATH,  # PointNav 数据集根目录
                "v1",  # 数据集版本号
                split,  # 数据集分割（train/val/test）
                f"{split}.json.gz"  # 数据集文件名（如 train.json.gz）
            )
            # 检查文件是否存在，如果不存在，尝试其他可能的路径
            if not os.path.exists(new_data_path):  # 如果新路径的文件不存在
                # 尝试直接使用数据集目录下的文件
                alt_path = os.path.join(POINTNAV_DATASET_PATH, f"{split}.json.gz")  # 构建备用路径
                if os.path.exists(alt_path):  # 如果备用路径存在
                    new_data_path = alt_path  # 使用备用路径
                else:  # 如果备用路径也不存在
                    print(f"警告: 数据集文件不存在: {new_data_path}")  # 打印警告信息
                    print(f"      尝试使用原始路径: {original_data_path}")  # 提示使用原始路径
            else:  # 如果新路径的文件存在
                # 路径设置成功，打印调试信息
                print(f"数据集路径已设置: {new_data_path}")  # 打印成功消息
            # 使用绝对路径
            config.habitat.dataset.data_path = os.path.abspath(new_data_path)  # 设置配置中的数据集路径为绝对路径
    
    return config  # 返回修改后的配置对象
```

### 步骤 3: 使用 RLEnv 进行强化学习

`RLEnv` 扩展了 `Env` 类，添加了强化学习所需的组件。这个示例展示了如何创建和使用 `RLEnv`：

```python
def example_1_rlenv_usage():
    """
    示例 1: 使用 RLEnv 进行强化学习
    
    RLEnv 扩展了 Env 类，添加了强化学习所需的组件：
    - 奖励函数 (get_reward)
    - 终止条件 (get_done)
    - 信息字典 (get_info)
    """
    print("=" * 60)  # 打印分隔线（60 个等号）
    print("示例 1: RLEnv 使用")  # 打印示例标题
    print("=" * 60)  # 打印分隔线
    
    # 定义自定义的 RLEnv
    class SimpleRLEnv(habitat.RLEnv):  # 继承 habitat.RLEnv 类，创建自定义的 RL 环境
        """简单的 RLEnv 实现"""
        
        def get_reward_range(self):  # 实现 get_reward_range 方法，定义奖励的范围
            """返回奖励范围"""
            return [-1, 1]  # 返回奖励的最小值和最大值（元组），用于归一化奖励
        
        def get_reward(self, observations):  # 实现 get_reward 方法，计算当前步骤的奖励
            """
            计算奖励
            
            在 PointNav 任务中，奖励通常基于：
            - 距离目标的减少
            - 是否到达目标
            - 时间惩罚
            """
            # 获取当前度量
            metrics = self.habitat_env.get_metrics()  # 从底层的 habitat.Env 获取当前 Episode 的度量结果
            
            # 简单的奖励：基于距离目标的减少
            if "distance_to_goal" in metrics:  # 如果度量结果中包含到目标的距离
                distance = metrics["distance_to_goal"]  # 提取到目标的距离（米）
                # 奖励与距离成反比（需要根据具体情况调整）
                reward = -distance * 0.01  # 计算奖励：距离越远，奖励越小（乘以负号），乘以 0.01 是缩放因子
            else:  # 如果没有距离信息
                reward = 0.0  # 默认奖励为 0
            
            # 如果到达目标，给予大奖励
            if self.habitat_env.episode_over:  # 检查 Episode 是否结束
                if metrics.get("success", 0) > 0:  # 如果成功到达目标（success > 0）
                    reward += 1.0  # 给予额外的成功奖励（+1.0）
            
            return reward  # 返回计算得到的奖励值
        
        def get_done(self, observations):  # 实现 get_done 方法，判断 Episode 是否结束
            """判断 episode 是否结束"""
            return self.habitat_env.episode_over  # 返回底层环境的 episode_over 状态（布尔值）
        
        def get_info(self, observations):  # 实现 get_info 方法，返回额外的信息字典
            """返回额外的信息"""
            return self.habitat_env.get_metrics()  # 返回底层环境的所有度量结果作为信息字典
    
    # 创建配置
    config = habitat.get_config(  # 获取 Habitat-Lab 配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml",  # 配置文件路径
        overrides=[  # 配置覆盖列表，用于动态添加或修改配置项
            "+habitat/task/measurements@habitat.task.measurements.distance_to_goal=distance_to_goal"  # 添加 distance_to_goal 度量（+ 表示添加新配置）
        ]
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 调用函数设置实际的数据路径
    
    # 创建 RLEnv
    env = SimpleRLEnv(config=config)  # 使用配置创建自定义的 RLEnv 实例
    
    print(f"\nRLEnv 创建成功")  # 打印成功消息
    print(f"  - 奖励范围: {env.get_reward_range()}")  # 打印奖励的范围
    
    # 重置环境
    observations = env.reset()  # 重置环境，开始新的 Episode，返回初始观察结果
    
    print(f"\n开始 Episode...")  # 打印 Episode 开始提示
    step_count = 0  # 初始化步数计数器
    total_reward = 0  # 初始化累计奖励
    max_steps = 20  # 设置最大步数限制
    
    while not env.get_done(observations) and step_count < max_steps:  # 循环条件：Episode 未结束且未超过最大步数
        # 执行随机动作
        action = env.action_space.sample()  # 从动作空间中随机采样一个动作
        observations, reward, done, info = env.step(action)  # 执行动作，返回 (观察, 奖励, 完成标志, 信息字典)
        
        total_reward += reward  # 累加奖励
        step_count += 1  # 步数加 1
        
        if step_count % 5 == 0:  # 每 5 步打印一次进度
            print(f"  步数 {step_count}: 奖励 {reward:.4f}, 总奖励 {total_reward:.4f}")  # 打印当前步数和奖励信息
            if "distance_to_goal" in info:  # 如果信息中包含到目标的距离
                print(f"    距离目标: {info['distance_to_goal']:.2f}m")  # 打印到目标的距离
    
    print(f"\nEpisode 结束:")  # 打印 Episode 结束提示
    print(f"  - 总步数: {step_count}")  # 打印总步数
    print(f"  - 总奖励: {total_reward:.4f}")  # 打印累计奖励
    print(f"  - 最终度量: {info}")  # 打印最终的信息字典（包含所有度量）
    
    env.close()  # 关闭环境，释放资源
```

### 步骤 4: 使用 ShortestPathFollower

`ShortestPathFollower` 是一个启发式导航策略，它使用 NavMesh 计算到目标的最短路径：

```python
def example_2_shortest_path_follower():
    """
    示例 2: 使用 ShortestPathFollower
    
    ShortestPathFollower 是一个启发式导航策略，
    它使用 NavMesh 计算到目标的最短路径
    """
    print("\n" + "=" * 60)  # 打印分隔线（换行 + 60 个等号）
    print("示例 2: ShortestPathFollower 使用")  # 打印示例标题
    print("=" * 60)  # 打印分隔线
    
    config = habitat.get_config(  # 获取配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"  # 配置文件路径
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 设置实际的数据路径
    
    env = habitat.Env(config=config)  # 创建环境对象
    observations = env.reset()  # 重置环境，开始新的 Episode
    
    # 创建 ShortestPathFollower
    # goal_radius: 到达目标的半径（距离目标多近算到达）
    goal_radius = env.episodes[0].goals[0].radius  # 从第一个 Episode 的第一个目标获取目标半径
    if goal_radius is None:  # 如果目标半径未定义
        goal_radius = config.habitat.simulator.forward_step_size  # 使用配置中的前进步长作为目标半径
    
    follower = ShortestPathFollower(  # 创建最短路径跟随器对象
        env.sim,  # 传入模拟器对象（用于路径查找）
        goal_radius,  # 传入目标半径
        return_one_hot=False  # 返回动作索引而不是 one-hot 向量（False 表示返回整数索引）
    )
    
    print(f"\nShortestPathFollower 创建成功")  # 打印成功消息
    print(f"  - 目标半径: {goal_radius}")  # 打印目标半径
    
    # 获取目标位置
    goal_position = env.current_episode.goals[0].position  # 获取当前 Episode 的第一个目标的位置坐标 [x, y, z]
    print(f"  - 目标位置: {goal_position}")  # 打印目标位置
    
    print(f"\n开始导航...")  # 打印导航开始提示
    step_count = 0  # 初始化步数计数器
    max_steps = 500  # 设置最大步数限制
    
    while not env.episode_over and step_count < max_steps:  # 循环条件：Episode 未结束且未超过最大步数
        # 获取下一个动作
        best_action = follower.get_next_action(goal_position)  # 调用跟随器的方法，根据当前 Agent 位置和目标位置计算下一个最优动作
        
        if best_action is None:  # 如果无法找到路径（返回 None）
            print(f"  无法找到路径到目标")  # 打印错误信息
            break  # 退出循环
        
        # 执行动作
        observations = env.step({"action": best_action})  # 执行计算得到的最优动作，返回新的观察结果
        step_count += 1  # 步数加 1
        
        # 获取度量
        metrics = env.get_metrics()  # 获取当前 Episode 的度量结果
        
        if step_count % 10 == 0:  # 每 10 步打印一次进度
            if "distance_to_goal" in metrics:  # 如果度量中包含到目标的距离
                print(f"  步数 {step_count}: 距离目标 {metrics['distance_to_goal']:.2f}m")  # 打印步数和距离
        
        # 检查是否到达目标
        if env.episode_over:  # 如果 Episode 结束（到达目标或超过最大步数）
            print(f"\n到达目标！")  # 打印成功消息
            print(f"  - 总步数: {step_count}")  # 打印总步数
            print(f"  - 最终度量: {metrics}")  # 打印最终度量结果
            break  # 退出循环
    
    if not env.episode_over:  # 如果 Episode 未结束（未能在最大步数内到达）
        print(f"\n未能在 {max_steps} 步内到达目标")  # 打印提示信息
    
    env.close()  # 关闭环境
```

### 步骤 5: 深入理解 Habitat 架构

这个示例展示了 Habitat 架构中的关键组件及其关系：

```python
def example_3_architecture_understanding():
    """
    示例 3: 深入理解 Habitat 架构
    
    这个示例展示了 Habitat 架构中的关键组件及其关系：
    - Env: 环境抽象
    - Simulator: 模拟器
    - EmbodiedTask: 任务定义
    - Dataset: 数据集
    - Measure: 度量标准
    """
    
    config = habitat.get_config(  # 获取配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"  # 配置文件路径
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 设置实际的数据路径
    
    env = habitat.Env(config=config)  # 创建环境对象
    
    print(f"\n=== Habitat 架构组件 ===")  # 打印架构组件标题
    
    print(f"\n1. Env (环境)")  # 打印 Env 组件标题
    print(f"  - 类型: {type(env).__name__}")  # 打印 Env 类的名称
    print(f"  - 作用: 连接 Dataset、Simulator 和 EmbodiedTask")  # 说明 Env 的作用
    print(f"  - 观察空间: {len(env.observation_space.spaces)} 个传感器")  # 打印观察空间中传感器的数量
    print(f"  - 动作空间: {len(env.action_space.spaces)} 个动作")  # 打印动作空间中动作的数量
    
    print(f"\n2. Simulator (模拟器)")  # 打印 Simulator 组件标题
    print(f"  - 类型: {type(env.sim).__name__}")  # 打印 Simulator 类的名称
    print(f"  - 作用: 提供物理模拟和渲染")  # 说明 Simulator 的作用
    # 注意：需要先 reset 才能获取场景信息
    observations = env.reset()  # 重置环境，加载场景和 Episode
    print(f"  - 场景 ID: {env.current_episode.scene_id}")  # 打印当前场景的唯一标识符
    print(f"  - 传感器: {list(env.sim.sensor_suite.sensors.keys())}")  # 打印模拟器中所有传感器的名称列表
    
    # 获取 Agent 状态
    agent_state = env.sim.get_agent_state()  # 从模拟器获取 Agent 的当前状态（位置和旋转）
    print(f"  - Agent 位置: {agent_state.position}")  # 打印 Agent 的位置坐标 [x, y, z]
    print(f"  - Agent 旋转: {agent_state.rotation}")  # 打印 Agent 的旋转（四元数）
    
    print(f"\n3. EmbodiedTask (任务)")  # 打印 EmbodiedTask 组件标题
    print(f"  - 类型: {type(env.task).__name__}")  # 打印 EmbodiedTask 类的名称
    print(f"  - 作用: 定义任务的动作空间、观察空间、度量标准")  # 说明 EmbodiedTask 的作用
    print(f"  - 任务传感器: {list(env.task.sensor_suite.observation_spaces.spaces.keys())}")  # 打印任务定义的所有传感器名称
    print(f"  - 任务度量: {list(env.task.measurements.measures.keys())}")  # 打印任务定义的所有度量指标名称
    
    # 查看任务的动作空间
    print(f"  - 动作空间: {env.task.action_space}")  # 打印任务的动作空间定义
    
    print(f"\n4. Dataset (数据集)")  # 打印 Dataset 组件标题
    print(f"  - Episode 总数: {len(env.episodes)}")  # 打印数据集中的 Episode 总数
    print(f"  - 当前 Episode ID: {env.current_episode.episode_id}")  # 打印当前 Episode 的唯一标识符
    print(f"  - 场景 ID: {env.current_episode.scene_id}")  # 打印当前 Episode 使用的场景 ID
    print(f"  - 起始位置: {env.current_episode.start_position}")  # 打印 Agent 的起始位置
    print(f"  - 目标数量: {len(env.current_episode.goals)}")  # 打印目标的数量
    
    print(f"\n5. Measure (度量标准)")  # 打印 Measure 组件标题
    print(f"  任务定义的度量标准:")  # 打印说明文字
    for measure_name, measure in env.task.measurements.measures.items():  # 遍历所有度量标准
        print(f"    - {measure_name}: {type(measure).__name__}")  # 打印度量名称和对应的类名
    
    # 执行一步并查看度量
    observations = env.reset()  # 重置环境（重新开始新的 Episode）
    observations = env.step(env.action_space.sample())  # 执行一个随机动作，获取新的观察
    metrics = env.get_metrics()  # 获取执行动作后的度量结果
    
    print(f"\n6. 执行一步后的度量值:")  # 打印度量值标题
    for key, value in metrics.items():  # 遍历所有度量项
        if isinstance(value, (int, float)):  # 如果度量值是数值类型
            print(f"    - {key}: {value:.4f}")  # 打印度量名称和值（保留 4 位小数）
        else:  # 如果度量值不是数值类型
            print(f"    - {key}: {value}")  # 打印度量名称和值（直接打印）
    
    print(f"\n=== 组件关系 ===")  # 打印组件关系标题
    print(f"""
    Dataset (Episodes)  # 数据集提供 Episode 数据（起始位置、目标位置等）
         |
         v
    Env <---> Simulator (habitat-sim)  # Env 连接 Dataset 和 Simulator，Simulator 提供场景渲染和物理仿真
         |
         v
    EmbodiedTask  # EmbodiedTask 定义任务的具体内容
         |
         +---> Action Space  # 动作空间：定义 Agent 可以执行的动作
         +---> Observation Space (Task Sensors)  # 观察空间：定义任务相关的传感器
         +---> Measurements (Measures)  # 度量标准：定义如何评估任务表现
    """)  # 打印组件关系图（ASCII 艺术）
    
    env.close()  # 关闭环境
```

### 步骤 6: 自定义配置

这个示例展示了如何通过代码动态修改配置，而不是使用配置文件：

```python
def example_4_custom_config():
    """
    示例 4: 自定义配置
    
    这个示例展示了如何通过代码动态修改配置，
    而不是使用配置文件
    """
    print("\n" + "=" * 60)  # 打印分隔线
    print("示例 4: 自定义配置")  # 打印示例标题
    print("=" * 60)  # 打印分隔线
    
    # 获取基础配置
    config = habitat.get_config(  # 获取默认配置对象
        config_path="benchmark/nav/pointnav/pointnav_habitat_test.yaml"  # 配置文件路径
    )
    
    # 设置数据路径
    config = setup_data_paths(config)  # 设置实际的数据路径
    
    print(f"\n原始配置:")  # 打印原始配置标题
    print(f"  - RGB 传感器分辨率: {config.habitat.simulator.agents.main_agent.sim_sensors.rgb_sensor.width}x{config.habitat.simulator.agents.main_agent.sim_sensors.rgb_sensor.height}")  # 打印 RGB 传感器的宽度和高度
    print(f"  - 最大步数: {config.habitat.environment.max_episode_steps}")  # 打印最大步数
    
    # 使用 read_write 修改配置
    with read_write(config):  # 进入配置读写上下文，允许修改配置
        # 修改传感器分辨率
        config.habitat.simulator.agents.main_agent.sim_sensors.rgb_sensor.width = 512  # 将 RGB 传感器宽度设置为 512 像素
        config.habitat.simulator.agents.main_agent.sim_sensors.rgb_sensor.height = 512  # 将 RGB 传感器高度设置为 512 像素
        config.habitat.simulator.agents.main_agent.sim_sensors.depth_sensor.width = 512  # 将深度传感器宽度设置为 512 像素
        config.habitat.simulator.agents.main_agent.sim_sensors.depth_sensor.height = 512  # 将深度传感器高度设置为 512 像素
        
        # 修改最大步数
        config.habitat.environment.max_episode_steps = 1000  # 将每个 Episode 的最大步数设置为 1000
        
        # 修改数据集分割
        config.habitat.dataset.split = "val"  # 将数据集分割设置为验证集（val）
    
    print(f"\n修改后的配置:")  # 打印修改后的配置标题
    print(f"  - RGB 传感器分辨率: {config.habitat.simulator.agents.main_agent.sim_sensors.rgb_sensor.width}x{config.habitat.simulator.agents.main_agent.sim_sensors.rgb_sensor.height}")  # 打印修改后的 RGB 传感器分辨率
    print(f"  - 最大步数: {config.habitat.environment.max_episode_steps}")  # 打印修改后的最大步数
    print(f"  - 数据集分割: {config.habitat.dataset.split}")  # 打印修改后的数据集分割
    
    # 使用修改后的配置创建环境
    env = habitat.Env(config=config)  # 使用修改后的配置创建环境对象
    observations = env.reset()  # 重置环境，获取初始观察
    
    print(f"\n使用自定义配置创建环境成功")  # 打印成功消息
    print(f"  - RGB 图像形状: {observations['rgb'].shape}")  # 打印 RGB 图像的实际形状（验证分辨率是否修改成功）
    
    env.close()  # 关闭环境
```

### 完整示例：主函数
```python
def main():
    """运行所有进阶示例"""
    print("\n" + "=" * 60)  # 打印分隔线
    print("Habitat-Lab 进阶学习教程")  # 打印教程标题
    print("=" * 60)  # 打印分隔线
    print("\n本教程将帮助你深入理解 Habitat-Lab 的进阶概念")  # 打印说明文字
    
    try:  # 尝试执行代码，捕获可能的异常
        example_1_rlenv_usage()  # 运行示例 1：RLEnv 使用
        example_2_shortest_path_follower()  # 运行示例 2：ShortestPathFollower 使用
        example_3_architecture_understanding()  # 运行示例 3：架构理解
        example_4_custom_config()  # 运行示例 4：自定义配置
        
        print("\n" + "=" * 60)  # 打印分隔线
        print("所有进阶示例运行完成！")  # 打印完成消息
        print("=" * 60)  # 打印分隔线
        print("\n下一步学习建议:")  # 打印学习建议标题
        print("1. 查看 habitat-lab/habitat/core/embodied_task.py 了解如何定义新任务")  # 打印建议 1
        print("2. 查看 habitat-lab/habitat/tasks/nav/ 了解导航任务的实现")  # 打印建议 2
        print("3. 查看 habitat-baselines 了解如何训练强化学习智能体")  # 打印建议 3
        print("4. 查看 examples/register_new_sensors_and_measures.py 了解如何扩展 Habitat-Lab")  # 打印建议 4
        
    except Exception as e:
        print(f"\n错误: {e}")  # 打印错误信息
        import traceback  # 导入 traceback 模块用于打印详细的错误堆栈
        traceback.print_exc()  # 打印完整的错误堆栈信息
        sys.exit(1)

if __name__ == "__main__":  # 如果脚本被直接运行（而不是被导入为模块）
    main()
```

## 关键概念总结

### 1. RLEnv（强化学习环境）

`habitat.RLEnv` 是 `habitat.Env` 的扩展，专门为强化学习设计：

- **get_reward()**：计算当前步骤的奖励值
- **get_done()**：判断 Episode 是否结束
- **get_info()**：返回额外的信息字典（通常包含度量结果）
- **get_reward_range()**：定义奖励的范围，用于归一化

### 2. ShortestPathFollower（最短路径跟随器）

`ShortestPathFollower` 是一个启发式导航策略：

- 使用 NavMesh 计算到目标的最短路径
- 根据当前 Agent 位置和目标位置选择最优动作
- 常用于基线方法或评估环境性能

### 3. Habitat 架构组件

Habitat-Lab 的架构可以理解为三层结构：

- **Env（环境层）**：连接 Dataset 和 Simulator 的高层接口
- **Simulator（模拟器层）**：提供场景渲染和物理仿真（Habitat-Sim）
- **EmbodiedTask（任务层）**：定义任务的动作空间、观察空间和度量标准

### 4. 配置系统

Habitat-Lab 使用 Hydra 配置管理系统：

- 使用 `read_write()` 上下文管理器修改配置
- 可以动态修改传感器分辨率、最大步数等参数
- 配置修改是临时的，只在当前上下文中有效


## 后续学习

1. 查看官方示例：`habitat-lab/examples/` 目录下有更多高级示例
2. 阅读源码：深入理解 `Env`、`Task`、`Simulator` 的实现
3. 自定义任务：创建自己的任务定义和传感器
4. 强化学习集成：将环境与 RL 算法（如 PPO、DD-PPO）集成

1. **自定义 Measure**：创建自己的度量标准来评估任务表现
2. **自定义 Sensor**：添加新的传感器来获取不同类型的观察
3. **自定义 Task**：定义新的任务类型（不仅仅是导航任务）
4. **强化学习训练**：使用 habitat-baselines 训练 RL 智能体
5. **多智能体环境**：了解如何创建和运行多智能体环境
