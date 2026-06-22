---
date: 2026-06-02
title: 面向具身智能的三维空间资产交付形态
authors: [bubblevan]
tags: []
---

```
真实空间采集
→ 三维重建
→ 视觉表示
→ 几何表示
→ 语义标注
→ 物理碰撞
→ 可导航地图（对于VLN任务）
→ 仿真器可加载格式
→ 轨迹与任务数据
→ 下游训练集格式
```

一个普通 3D 重建结果，和一个具身智能可用的空间资产，中间还隔着好几层。

普通 3D 重建资产主要用于看、展示、漫游、渲染；具身智能空间资产不仅要能看，还要能被机器人理解、规划、碰撞检测、仿真执行、生成任务和训练数据。

## 一、3D 重建

不同三维重建路线，输出物不一样。

### 1. 摄影测量 / SfM / MVS 路线

输入通常是多张 RGB 图片或视频帧。输出通常包括：

```text
相机位姿：每张图片拍摄时的位置和朝向；
稀疏点云：用于估计相机和场景结构；
稠密点云：更完整的三维点集合；
mesh：由点云或深度融合得到的三角网格；
texture：贴在 mesh 表面的颜色纹理。
```

优点是流程成熟，很多工具链都支持。缺点是室内场景容易出现反光、弱纹理、遮挡、洞、漂浮物、边界粘连等问题。对于机器人来说，mesh 可能“看起来像房间”，但不一定是干净的碰撞体，也不一定适合导航。

### 2. RGB-D / LiDAR 扫描路线

输入是 RGB-D 相机、深度相机、激光雷达或者移动扫描设备。输出通常包括：

```text
点云；
TSDF / occupancy；
mesh；
相机轨迹；
有时还会有语义分割或实例分割。
```

优点是尺度和几何通常更可靠，适合构建地图。缺点是外观质量可能不如 3DGS，mesh 边界可能噪声大，物体经常和背景粘在一起。

例如 Matterport3D / HM3D 这类传统 VLN 场景，本质上更接近 scanned mesh。它能用于 Habitat 导航，但在物体边界、纹理真实性、物理碰撞精度上并不完美。

### 3. NeRF / 3DGS 路线

输入也是多视角图片或视频，输出不是传统 mesh，而是一个用于新视角渲染的场景表示。

3DGS 的输出可以理解成：

```text
一堆三维高斯点；
每个高斯有位置、大小、方向、不透明度、颜色或球谐系数；
再加相机参数；
渲染器可以从新视角实时生成照片级图像。
```

它的优点是视觉效果好、新视角一致性强、渲染速度快。
但它的核心问题是：它不是天然的物理世界模型。

3DGS 本身通常不直接提供：

```text
干净的 mesh；
对象实例 ID；
物体类别；
碰撞体；
刚体参数；
可导航区域；
门、墙、房间等结构化语义；
机器人可执行的动力学接口。
```

所以，单独的 3DGS 对机器人来说很尴尬：它很好看，但机器人不知道它能不能撞，不能可靠地判断哪里是墙，不能直接根据“去桌子旁边”定位目标，也不能直接用于物理仿真。

### 总结
三维重建会在这些原始数采数据基础上恢复空间结构。常见输出包括几类：​

第一类是点云。点云就是空间中一堆 3D 点，每个点可能有颜色、法线、置信度。它适合做几何检查、地图构建、尺度校验，但不适合直接做照片级渲染，也不适合直接做机器人碰撞仿真。​

第二类是 mesh。mesh 是由三角面片组成的三维表面。它更适合图形引擎、仿真器和几何处理，也更容易进一步做碰撞体、navmesh、房间结构提取。​

第三类是 textured mesh 或 PBR mesh。textured mesh 是带贴图的三角网格；PBR mesh 则进一步带材质参数，例如 albedo、roughness、metallic、normal 等。PBR mesh 更像游戏引擎或仿真引擎里的资产，适合编辑、重打光、导入仿真器。​

第四类是 NeRF / 3DGS 这类神经或显式辐射场表示。它们的核心优势是新视角渲染真实，尤其是 3DGS，能在较高速度下生成照片级视角。​

第五类是相机轨迹和稀疏重建结果。即便最终要输出 3DGS 或 mesh，相机位姿本身也很重要，因为后续要用它做尺度对齐、渲染视角校验、重建质量评估。

> 这里取决于技术路线，我其实不太了解所以都泛泛涉及一下

## 二、视觉表示
视觉表示解决的是“从任意机器人视角看过去，图像是否真实、稳定、连续”。

这里主要有两条路线：

第一条是传统图形学路线：textured mesh / PBR mesh。
它通过 mesh 几何加材质贴图来渲染图像。优点是兼容性好，可以进游戏引擎、仿真器、Web 3D、Omniverse；缺点是如果重建 mesh 不干净，或者贴图来自稀疏视角，新视角下可能出现拉伸、模糊、破面、接缝。

第二条是 3DGS 路线。
3DGS 可以理解成一堆带颜色、透明度、尺度和方向的三维高斯。它不是传统三角网格，而是一种更适合照片级新视角渲染的场景表示。机器人相机移动时，3DGS 可以从新的位置渲染出比较连续、真实的画面。

3DGS 对具身智能很有吸引力，因为 VLN / VLA 模型非常依赖视觉分布。如果仿真场景太假，模型在真实世界里容易失效。3DGS 的价值在于缩小视觉 sim-to-real gap，也就是让仿真视觉更接近真实视觉。隔壁群核的 SAGE-3D 的出发点就是，传统 3DGS 虽然渲染真实，但缺少两件具身智能最需要的东西：

1. 语义：不知道哪个高斯属于椅子，哪个属于桌子，哪个是门；
2. 物理：没有可靠碰撞体，机器人可能穿墙、穿桌子、穿柜子。

所以 SAGE-3D 把它升级成`3DGS + 语义层 + 物理层 = 可执行具身环境`

### SAGE-3D Data Generation Pipeline
首先是 Object-Level Semantic Grounding，也就是对象级语义对齐：
- 从高质量室内 mesh 场景出发；
- 渲染大量相机视角；
- 用 gsplat 得到 3DGS；
- 人工或半人工给对象做语义标注；
- 每个对象有类别、实例 ID、bounding box；
- 再把 3D 对象投影到地面，生成 2D semantic top-down map。

这个 semantic map 对导航非常重要。因为机器人导航和语言指令经常依赖地标：`去沙发旁边；穿过厨房；走到白色柜子对面；到餐厅中间的空桌子；去冰箱附近拿饮料。`

为了解决模型很难把语言中的“沙发、柜子、厨房、桌子旁边”落到具体空间位置的问题，第二条是 Physics-Aware Execution Jointing，也就是物理可执行对齐：
- 保留 3DGS 负责真实感渲染；
- 从 mesh 中提取每个物体的 collision body；
- 把 collision body 放进仿真器；
- 让碰撞体不可见，但负责物理接触和碰撞检测；
- 让 3DGS 可见，负责照片级视觉外观；
- 最后形成 3DGS-Mesh Hybrid Representation。

也就是：
- 3DGS 管视觉；
- mesh / collision body 管物理；
- semantic map 管语言和空间理解；
- USD / USDA 管集成和仿真承载。
## 三、几何表示
几何表示解决的是“空间到底是什么形状”。因为机器人需要知道：
- 哪里是地板；
- 哪里是墙；
- 哪里是门；
- 哪里有桌子、柜子、沙发；
- 走廊宽度够不够；
- 机器人身体能不能通过；
- 某个位置是不是在障碍物里面。

这通常需要 mesh、clean mesh、floor mesh、wall mesh、room layout、floorplan、wall structure、door structure、object geometry 等。

如果是传统扫描重建，mesh 往往会有噪声。比如桌腿和地面粘在一起，椅子和墙粘在一起，玻璃或反光物体缺失，门洞边界破碎。这类 mesh 用来“看”可能勉强可以，但用来做机器人碰撞和路径规划会很危险。

如果是 GenRecon 这类生成式三维重建，它的目标更接近生成完整、干净、可编辑、PBR-ready 的 mesh。它对具身资产的价值在于：相比纯 3DGS，mesh 更容易转成碰撞体、导航地图、房间结构和仿真资产。但当然生成式重建会“补全”被遮挡区域，因此最后还是要做几何验收。

## 四、语义标注
语义标注解决的是“空间里每个东西是什么”。比较有价值的语义交付包括：
- object instance ID；
- object category；
- 3D bounding box；
- 2D footprint mask；
- room / area label；
- door / window / wall / stair 标注；
- 物体颜色、状态、材质；
- 物体可移动性；
- 物体之间的空间关系。

这里要区分“语义分割”和“对象级语义”。
语义分割只告诉你某些区域是 chair、table、wall；对象级语义还要告诉你这是 chair_1、那是 chair_2，并且每个对象有自己的 bbox、mask、位置、属性。对于语言导航来说，对象级语义更有价值，因为指令经常要区分类似物体：
- 去靠窗的那把椅子；
- 走到白色桌子旁；
- 去冰箱对面的柜子。
> 这里 InternNav 失败了，跟作者交流下来，它们的模型在 ObjectNav 上怎么训都训不 work。

## 五、物理碰撞
物理碰撞解决的是“机器人在这个场景里走动时，会不会穿墙、穿桌子、穿柜子”。具身资产里通常需要单独的 physics layer，至少包括：
- collision mesh；
- convex collision bodies； 
- static / dynamic body 标记； 
- rigid body 参数； 
- 摩擦系数； 
- 质量； 
- 可移动 / 不可移动； 
- 关节或 articulation； 
- 接触检测配置
## 六、可导航地图
可导航地图解决的是“这个场景中哪些区域可以走，以及从 A 到 B 怎么走”。常见可导航表示包括：

| 英文 | 中文 | 定义 |
|----------|----------|----------|
| occupancy map | 占据栅格地图 | 可以理解成一张俯视图地图，通过栅格单元的状态（占据/空闲/未知）标出哪里被障碍物占据，哪里是可通行空地 |
| semantic top-down map | 语义俯视图地图 | 在基础俯视图地图的基础上，进一步将物体类别、房间功能等语义信息投影到地图上 |
| navmesh | 导航网格 | 由凸多边形组成的"机器人能走的地面网格"，用于高效计算可行走路径和避障 |
| ESDF | 欧几里得距离场<br>(Euclidean Signed Distance Field) | 存储每个位置到最近障碍物的欧几里得距离的地图，正值表示在障碍物外，负值表示在障碍物内 |
| 可通行区域 mask | 可通行区域掩码 | 二值化的地图表示，用0和1明确区分机器人可以进入和禁止进入的区域 |
| 障碍物边界 | 障碍物边界 | 地图中障碍物与可通行区域的分界线，用于精确避障和边界检测 |
| start / goal 可达性检查 | 起点/终点可达性检查 | 验证从起点到终点是否存在至少一条可行路径的算法 |
| room connectivity graph | 房间连通图 | 以房间为节点、以房间之间的连接关系为边的图结构，用于高层级的路径规划 |
| door connectivity graph | 门连通图 | 以门为节点、以门之间的可达关系为边的图结构，常用于室内环境的分层导航 |

> 隔壁 SAGE-3D 把 3D 对象投影到地面生成 2D semantic top-down map，再结合 occupancy map 生成最终导航地图，用于路径规划和指令生成

## 六、仿真器可加载格式
从真实空间被重建成数字模型开始，就已经进入了 real-to-digital；但真正进入具身意义上的 real-to-sim，是在资产被装配成仿真器可加载、可执行的场景之后。
这里最关键的格式之一是 USD / USDA / USDZ，一个完整的场景工程文件。

以 Isaac Sim USD 为例，其往往不止包括 mesh：

| 元素类别 | 具体内容 |
|----------|----------|
| 场景结构 | 场景图(Scene Graph)、物体层级关系、坐标变换(Transform)、引用的外部资产 |
| 视觉系统 | 网格(Mesh)、材质(Material)、纹理(Texture)、灯光(Light)、相机(Camera) |
| 物理系统 | 碰撞体(Collision Body)、刚体参数(Rigid Body)、关节(Joint)、物理材质、重力设置 |
| 机器人系统 | 完整机器人装配体、传感器(相机/激光雷达/IMU/力传感器)、执行器(Actuator) |
| 逻辑系统 | 脚本接口(Python/C++)、动作图(Action Graph)、自定义属性与元数据 |

下面是关于 USD 的 **术语表**：

| 英文术语 | 中文译名 | 核心定义 | 典型应用场景 |
|----------|----------|----------|--------------|
| USD | 通用场景描述格式<br>(Universal Scene Description) | Pixar开发的开源工业标准，**不是普通3D模型文件**，而是完整的可执行场景工程格式，支持分层组合与多人协作 | 机器人仿真(Isaac Sim)、影视动画、工业数字孪生、复杂3D场景开发 |
| USDA | ASCII格式通用场景描述 | USD的纯文本UTF-8变体，可直接用文本编辑器打开编辑 | 人工调试、版本控制、脚本生成、问题排查 |
| USDC | 二进制格式通用场景描述 | USD的"Crate"压缩二进制变体，支持内存映射快速访问 | 生产环境部署、大规模场景加载、几何数据存储 |
| USDZ | 打包式通用场景描述 | 基于ZIP的单文件打包格式，内含USDC文件+所有依赖资产(纹理/音频等) | 跨平台分发、AR/VR内容分享、移动端展示 |
| GLB | 二进制glTF格式 | 单个二进制文件的glTF格式，仅包含几何、材质、纹理等视觉信息 | 单个3D模型交换、Web3D展示 |
| OBJ | Wavefront对象格式 | 传统纯文本几何格式，仅支持基础网格和简单材质 | 简单3D模型导出、通用几何交换 |
| PLY | 多边形文件格式 | 支持点云、网格和自定义属性的格式 | 3D扫描数据存储、点云处理 |
| LeRobot | LeRobot数据集格式 | Hugging Face推出的具身智能数据标准，采用Parquet+MP4组合存储多模态数据 | 机器人模仿学习、强化学习训练、跨平台数据交换 |
| InternData | InternData数据集格式 | 上海人工智能实验室推出的多模态机器人数据集格式，兼容LeRobot标准 | 通用机器人技能训练、大规模数据标注 |

常见关系可以这样理解：
- USD：通用场景描述格式；
- USDA：USD 的 ASCII 文本形式，便于人工检查和调试；
- USDC：USD 的二进制形式，加载效率更高；
- USDZ：打包格式，适合分发和交换；
- GLB / OBJ / PLY：更偏单个几何或视觉资产；
- LeRobot / InternData：更偏训练样本格式。

与此同时，隔壁 Habitat 原生不支持 USD 格式，所有官方数据集（HM3D、ReplicaCAD、HSSD、Matterport3D）均使用 GLB+JSON 体系。有的第三方工具（如 InfiniteWorld）提供了从 USD 到 Habitat GLB+JSON 的转换脚本，但会丢失 USD 特有的分层、引用和脚本信息。放弃 USD 的通用性和可扩展性，主要是为了换取无与伦比的仿真速度。因此适配 Habitat 的话或许要额外交付 glb + navmesh + semantic annotations。


## 七、轨迹与任务数据
有了仿真场景后，剩下的就是生成任务和轨迹了，详见[对 Lerobot 的解释](./2026-05-30-internvlan1-datasets.md)。

轨迹与任务数据通常包括：
- start-goal pairs；
- reference trajectory；
- waypoints；
- 每帧 pose；
- 每帧 RGB / depth / semantic observation；
- action sequence；
- collision events；
- success / failure；
- language instruction；
- quality score。

任务可以有低层和高层两种。

| 任务层级 | 核心特征 | 具体示例 |
|----------|----------|----------|
| 低层任务 | 纯几何/运动指令，不需要语义理解，可直接映射为机器人关节动作 | 1. 向前走两步<br>2. 右转90度<br>3. 从A点走到B点<br>4. 从厨房走到客厅 |
| 高层任务 | 需要语义理解、环境推理和目标识别，包含多个隐含的低层子任务 | 1. 我渴了，去冰箱那里拿饮料<br>2. 找到餐厅里空的桌子<br>3. 走到白色书架旁边<br>4. 去沙发对面的柜子那里 |

轨迹生成通常需要：
- 可导航地图；
- 路径规划算法；
- 轨迹平滑；
- 碰撞检测；
- 视觉渲染；
- 语言生成或人工标注；
- 质量过滤。
如果是 VLN 数据生产，最小闭环是：
- 采样起点和终点；
- 用地图规划一条路径；
- 沿路径渲染第一人称 RGB-D；
- 记录 pose 和 action；
- 基于 semantic map 生成语言指令；
- 过滤掉画面空、地标少、路径不自然的样本。

## 八、下游训练集格式
InternData / LeRobot 主要关心的是：
- episode；
- frame；
- timestamp；
- observation；
- action；
- task；
- instruction；
- video；
- parquet；
- metadata。



## 九、总结
可以分成五层。
### 第一层：原始采集层
```text
原始 RGB 视频或图片；
如果有，原始深度、LiDAR 或 RGB-D 数据；
相机内参；
相机轨迹/外参；
时间戳；
采集设备信息；
尺度标定信息；
坐标系定义。
```

这层是可追溯性。以后如果重建结果有问题，必须能回到原始数据重新处理。

### 第二层：视觉重建层
```text
3DGS：用于照片级新视角渲染；
PBR mesh：用于编辑、重打光、仿真资产制作；
textured mesh：用于通用 3D 引擎加载；
point cloud：用于几何检查和地图构建。
```
### 第三层：几何与物理层
```text
clean mesh；
collision mesh；
convex collision bodies；
occupancy map；
navmesh 或可导航区域；
地面、墙体、门洞、障碍物边界；
物体静态/可移动属性；
如果支持交互，还要有 articulation / joint / mass / friction。
```

对导航任务来说，至少要有：

```text
地面可行走区域；
障碍物占据区域；
机器人半径/高度对应的通行约束；
门的状态；
楼梯/坡道/不可达区域；
起点终点可达性检查。
```

### 第四层：语义结构层
```text
object instance ID；
object category；
3D bounding box；
2D footprint mask；
room / area segmentation；
floorplan；
door / window / wall / stair 等结构标注；
物体属性：颜色、材质、开闭状态、可移动性；
对象之间的空间关系：next to、in front of、opposite、inside、on top of。
```

这一层决定能不能生成高质量 VLN 指令，例如：

```text
去沙发旁边；
从厨房走到客厅；
找到餐厅里空的桌子；
走到冰箱对面的柜子；
把书从茶几拿到书架。
```

如果没有语义结构层，数据就只能生成“向前走、左转、到终点”这种低级导航指令，很难服务未来的 VLA / 具身大模型训练。

### 第五层：仿真与训练导出层
```text
Isaac Sim / Omniverse：
USD / USDA / USDZ，包含视觉层、碰撞层、语义层、物理参数。

Habitat：
glb + navmesh + semantic annotations。

InternData / LeRobot：
RGB-D 视频、pose、action、instruction、episode parquet、meta JSON。

NaVILA：
视频帧或视频、annotation JSON、instruction、action/trajectory 标签。

自定义 VLN 数据：
start-goal pairs、trajectories、instructions、actions、success/fail、collision events。
```
