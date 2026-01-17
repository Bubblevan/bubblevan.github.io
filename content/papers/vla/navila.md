---
title: "VLA 论文精读（）NaVILA: Legged Robot Vision-Language-Action Model for Navigation"
---

## 研究背景
让机器人听懂人话，并自主走到指定地点，这个能力被称为**视觉语言导航**。它可以说是现代智能机器人的一项基础核心技能。为什么这么说呢？我们可以拆解一下它的三个关键点：

*   **环境条件**：机器人是在一个**没有预设地图的陌生环境**里行动的。它不能像我们用手机导航一样，提前下载好整个建筑的地图，一切都得靠实时观察和判断。
*   **输入输出**：输入是**人类最自然的语言指令**，比如“绕过沙发，走到窗户边停下”；输出则是机器人一连串的**导航动作**，比如前进、左转、停止。
*   **核心价值**：这样做的好处显而易见。对人来说，**交互门槛极低**，不需要学习任何机器人专用命令；对机器人来说，**通用性很强**，语言就像一座桥梁，能帮助它适应从家庭客厅到公司走廊等不同的场景。

NaVILA顺带cue了一波轮式机器人，选择腿式机器人（如四足机器人 Unitree Go2、人形机器人 Unitree H1）作为 VLN 的载体，balabala列了一下腿式机器人的环境适应性优势，哎呀主要是因为它是第一篇VLN+腿足的工作，所以有些保守。

目前，很多人尝试打造**端到端的视觉-语言-动作系统**，也就是直接用大语言模型或视觉语言模型来预测机器人每个关节该怎么动。但这种“一步到位”的思路存在几个明显的短板：

- 泛化性差：模型学到的动作严重依赖于特定机器人的关节参数和结构。换一台机器人，几乎等于要从头开始训练；
- 数据利用低效：训练这种模型很难利用丰富多样的人类数据（比如网上的第一视角行走视频），只能依赖机器人自己采集的、成本高昂的演示数据，效率很低；
- 实时性不足：大模型计算复杂，决策慢。而腿式机器人在快速行走中遇到突然出现的障碍时，需要毫秒级的反应来调整姿态，端到端模型很难满足这种**实时性**要求。

这些问题的**根源**在于，LLMs/VLMs 的预训练数据以 “自然语言” 为主，擅长文字推理，但直接让其输出 “非语言的低级关节指令”（如 “关节 1 角度 + 30°”），违背了模型的训练逻辑，导致推理与执行的衔接断层

> 这一点其实在前沿实践里面被广泛诟病，有些人拿那种视频去训练，就发现语言模态是多余的，打算一步到位V->A，但是这对我来说有点难了，无论是指导层面还是算力层面。

为了破解这个瓶颈，NaVILA论文提出了一个**两级解耦框架**。核心思想很清晰：**把高层决策和底层执行分开**，中间用一个“翻译层”——即**自然语言描述的中级动作**——来连接：
1. **高层（决策层）- 视觉语言动作模型**：
- 核心功能：基于视觉观测（实时画面 + 历史画面）和语言指令，输出「自然语言形式的中级动作」，而非直接控制关节。
例：不输出 “关节 1→+30°、关节 2→-15°”，而是输出 “前进 75cm”“右转 30 度”“停止”—— 这类带空间信息的语言化动作指令。
关键设计：
利用 VLMs（如 VILA 模型）的文字推理能力，避免让模型 “跨领域” 预测低级动作；
整合多样化数据训练：包括 YouTube 人类第一视角导航视频（首次实现 “人类视频直接用于连续导航训练”）、模拟环境数据（如 Habitat 模拟器）、通用视觉问答（VQA）数据，既提升导航专业性，又保留模型的通用推理能力。
2. **低层：视觉移动策略（Locomotion执行层）**
- 核心功能：将高层输出的 “中级语言指令” 转化为腿式机器人的「低级关节动作」，并实时避障。
关键设计：
传感器融合：用 LiDAR（激光雷达）生成 2.5D 高度图，解决 RGB 相机在 “强光”“透明物体” 场景下的观测盲区；
单阶段训练：直接用强化学习（PPO 算法）训练控制策略，无需传统的 “教师 - 学生蒸馏” 步骤，效率更高（RTX 4090 上达 60K FPS），还能探索新的避障策略；
指令转化：将 “前进 75cm” 这类中级指令，映射为机器人的固定速度指令（如 0.5 m/s），再通过控制腿部 12 个关节的目标位置实现运动。

优势维度	具体说明
跨机器人适配	高层 VLA 模型与低层执行策略解耦，换机器人时只需替换低层策略（如从四足 Go2 换到人形 H1，无需重新训练 VLA）
数据利用灵活	中级动作以语言形式存在，可结合人类视频、QA 数据等多样化数据训练，避免过拟合到特定机器人的关节参数
实时性与鲁棒性	双时标运行：高层 VLA（大模型）低频输出指令（无需实时），低层策略高频执行（实时避障），兼顾推理精度与安全




## 方法论
NaVILA框架的核心，就是上面提到的 **“解耦且协同”的两级系统**。下面这张图清晰地展示了它的工作流程：
![](/paper/navila-overview.png)
NaVILA is a two-level framework combining high-level visual language understanding with low-level locomotion control. Our VLA model processes single-view images to produce mid-level actions in natural language, which are then converted into precise joint movements by an advanced low-level locomotion policy. This integration allows for strong generalization and adaptability across different real-world environments, and can operate the robot in real-time.

输入层：自然语言导航指令（如 “Pass the rug and stop by the desk”）、历史视图（记忆轨迹）、当前视图（实时环境）、本体感知数据（关节位置 / 速度、机器人姿态）；
高层 VLA 模型：处理单视角图像（历史 + 当前），生成自然语言形式的中间动作指令（如 “Move forward 75 cm”“Walk forward and turn right”）；
低层移动策略（Policy π）：将中间指令转化为固定速度指令（如 “前进”→0.5 m/s），再映射为 12 个腿部关节的目标位置，最终实现实时控制；
核心协同价值：高层 VLM 负责 “推理决策”（如 “该往哪走”），低层策略负责 “安全执行”（如 “怎么走不撞墙”），两者结合实现跨环境泛化。

### 调优 VLM 以实现视觉语言导航（高层决策层）
这部分解决 “如何让 VLM 具备导航决策能力”，核心是基于VILA（图像基高效 VLM） 做四步优化，避免使用视频编码器（因缺乏高质量视频 - 文本预训练数据）。
VILA 是高层 VLA 的核心载体，优势在于泛化性强、支持多图像推理（适配 VLN 的序列帧理解需求），其结构与训练分两部分：
三大组件：
视觉编码器：将输入图像（历史 / 当前帧）转化为视觉 token；
MLP 投影器：将视觉 token“降维 + 映射” 到语言域，确保能与文本 token 融合；
LLM（大语言模型）：接收融合后的 “视觉 token + 文本指令”，自回归生成自然语言动作。
三阶段预训练（为导航任务打基础）：
冻结视觉骨干与 LLM，仅训练 “投影器”，实现视觉 - 语言对齐；
解冻投影器与 LLM，用 “文本 - 图像交织语料” 训练，提升跨模态理解；
全模块解冻，用指令微调数据（如 VQA）训练，适配生成任务。

![](/paper/navila-vla.png)
Overview of our VLA framework. We denote the purple blocks ( ) as memory tokens sampled from historical frames, and the red blocks ( ) as the current observation tokens. ?denotes trainable parameters. In our experiments, we tested configurations with 8 to 64 frames for t.

#### 导航提示
VLN 需要 “记忆轨迹（历史帧）+ 即时决策（当前帧）”，因此设计结构化提示，核心是 “用文本标签区分帧类型，不新增特殊 token”（避免干扰 LLM 预训练能力）：
帧拆分规则：
历史帧（紫色 token）：从 t-1 帧中均匀采样，必含第一帧，作用是 “跟踪进度”（如记住起点、已走过的路）；
当前帧（红色 token）：最新 1 帧，作用是 “即时决策”（如判断路口是否该右转、是否到达目标）。
提示格式示例：
“Imagine you are a robot... You have been given a video of historical observations: [历史帧视觉 token]... and current observation: [当前帧视觉 token]... Your task: [用户指令]... Decide next move (turn/forward/stop) with degree/distance.”
优势：完全基于语言域交互，最大化利用 LLM 的预训练推理能力（如理解 “历史 - 当前” 的逻辑关系）。
![](/paper/navila-video-dataset.png)
Data pipeline for transforming human touring videos in the wild into pairwise navigation data within a continuous environment. We begin by processing the videos into meaningful trajectories through entropy-based sampling [26]. Then we extract step-wise actions through metric camera pose estimation [27], and utilize VLM [13] and LLM [28] to generate instructions.
#### 从人类视频学习连续导航
这是 NaVILA 的核心创新之一，解决了 “连续导航缺乏真实动作标签” 的问题，将人类第一视角视频转化为训练数据，具体 pipeline 如下：
数据来源：2K 条 YouTube “第一视角游览视频”（如人在实验室、家庭、户外行走的画面）；
轨迹生成：用 “熵基采样” 从视频中提取 20K 条多样化轨迹（避免重复场景，确保数据覆盖性）；
动作提取：用 MASt3R（度量姿态估计模型）分析视频帧的相机运动，反推出 “每一步动作”（如前进 50cm、左转 20°）；
指令生成：先通过 VLM 为轨迹生成描述性文本（caption），再用 LLM 重写为 “机器人可理解的导航指令”（如将 “走过地毯” 优化为 “Pass the rug and stop by the desk”）；
价值：首次实现 “人类视频直接用于连续导航训练”，突破了传统依赖机器人演示数据的局限。

#### SFT数据混合
通过 “四类数据融合”，让 VLM 既 “专精导航” 又 “不丢通用能力”，避免过拟合到特定场景 / 动作，具体如下表：
数据类型	来源 / 处理方式	核心作用
1. 真实视频导航数据	上述人类视频处理后的 “轨迹 - 指令对”	适配真实世界环境（如家庭杂乱场景、户外地形）
2. 模拟导航数据	R2R-CE/RxR-CE（连续 VLN 数据集）在 Habitat 模拟器中，用 “最短路径跟随器” 生成动作序列	补充连续环境数据，解决真实数据量不足问题；合并连续动作（如 2 次 25cm→1 次 50cm），减少数据量 + 增加动作多样性，平衡 “stop 动作” 标签不平衡
3. 辅助导航数据	- EnvDrop：增强导航指令多样性；
- ScanQA：3D 场景 QA（基于真实 3D 扫描的物体问答）	提升场景理解（如识别 “桌子”“地毯”）和轨迹总结能力
4. 通用 VQA 数据	[23][33][34] 等图像 - 文本问答数据集（如 “这是门吗？”）	保留 LLM 的通用推理能力，避免因专注导航而丢失基础视觉理解

训练：以 VILA 的 “第二阶段模型” 为起点，用上述 SFT 混合数据训练 1 个 epoch，全模块（视觉编码器、投影器、LLM）解冻；
推理：用正则表达式解析 LLM 输出，提取 “动作类型”（前进 / 左转 / 右转 / 停止）和 “参数”（距离如 75cm、角度如 30°），确保指令可被低层策略识别。

### 视觉移动策略（低层执行层）
这部分解决 “如何将 VLM 的自然语言指令转化为腿式机器人的精确关节动作”，以Unitree Go2 四足机器人为实验平台，核心是 “单阶段 RL 训练 + LiDAR 高度图避障”。
1. 实验平台：Unitree Go2 机器人硬件参数
自由度（DoF）：共 18 个 —— 基座 6DoF（整体平移 / 旋转）+ 4 条腿各 3DoF（髋关节、膝关节控制）；
核心传感器：头部 LiDAR（15Hz 刷新，360°×90° 视场）—— 用于生成高度图，解决 RGB 相机在 “强光”“透明物体（玻璃）” 场景下的观测盲区（Fig.5b 可见：RGB/depth 无法识别玻璃，高度图可清晰检测）；
控制目标：仅控制 12 个腿部关节（基座 6DoF 不约束），通过关节目标位置转化为扭矩输入。
2. 高层指令解析：从 “自然语言” 到 “速度指令”
将 VLM 输出的中间指令（如 “前进 75cm”“右转 30°”）映射为固定速度指令，便于实时跟踪：
中间指令类型	对应速度指令	执行逻辑
前进	线速度 = 0.5 m/s	按此速度移动至指定距离
左转 / 右转	角速度 = ±π/6 rad/s	按此角速度旋转至指定角度
停止	线速度 = 0，角速度 = 0	立即停止所有关节运动
3. 观测空间设计：区分 Critic 与 Actor（确保真实部署可用）
采用强化学习（PPO 算法）训练，核心是 “Critic 用特权信息指导，Actor 用真实传感器数据执行”，避免 “训练时依赖不可用信息”：
Critic 观测（oc，训练辅助）：包含 “本体感知数据 + 特权环境信息”
本体感知：关节位置 / 速度、机器人姿态（角度）、当前速度指令、上一步动作；
特权信息：机器人周围的 “真实地形高度扫描”（训练时模拟器提供，帮助 Critic 学习价值函数）；
Actor 观测（oa，真实部署用）：仅包含 “可获取的传感器数据”
移除 Critic 的 “线速度”（真实场景中难精确测量），用 “历史本体感知数据” 间接推断；
核心输入：LiDAR 生成的高度图（2.5D，反映周围地形高低，用于避障）+ 本体感知数据。

LiDAR 是低层策略的 “眼睛”，高度图是其核心输出，解决了视觉传感器的痛点：
生成流程：
LiDAR 输出 360°×90° 的点云；
将点云映射为 2.5D 网格（voxel grid），每个网格取 “最低高度值”；
对近 5 帧点云应用 “最大值滤波”，平滑高度图（避免单帧噪声导致误判）；
关键作用（Fig.5 对比）：
抗强光：RGB 相机在强光下易过曝，LiDAR 不受光照影响；
识别透明物体：玻璃、透明塑料等在 RGB/depth 图中难检测，高度图可通过 “表面高度变化” 识别；
避障：高度图中的 “高值区域”（如石块、台阶）被判定为障碍，策略会调整腿部动作绕开。

![](/paper/navila-heightmap-from-pointcloud.png)
Height map reconstruction from point cloud. (a) Go2 robot follows velocity commands while avoiding obstacles in simulation. Red dots show LiDAR points raycasting from the sensor center to the terrain mesh. The right image shows a preprocessed height map with values clipped to sensor constraints; darker colors indicate higher heights. (b) Safe locomotion near glass. The top-down height map detects glass surfaces where depth and RGB images fail.

传统腿式机器人控制常用 “教师 - 学生蒸馏”（两阶段：先训教师模型用特权信息，再蒸馏到学生模型），而 NaVILA 用单阶段 PPO 训练，优势显著：
效率更高：省去蒸馏步骤，RTX 4090 上训练吞吐量达 60K FPS（帧 / 秒）；
策略更灵活：Actor 直接与环境交互，可探索 “教师模型未覆盖的避障策略”（如绕开小坑洼的新步态）；
部署更直接：无需适配教师 - 学生的差异，训练出的 Actor 可直接部署到真实机器人。

## 实验
实验的整体思路是 “从模块验证到系统落地”，每个小节对应一个核心问题，确保覆盖 “决策层 - 执行层 - 模拟 - 真实” 全场景：
实验小节	核心问题	验证目标
III-A	高层 VLA 与 SOTA 在 VLN-CE 和空间理解任务的性能对比	验证 “单视角 RGB 输入的 VLA 能否超越多模态（全景 / 深度 / 里程计）模型”
III-B	单阶段视觉移动策略与 “策略蒸馏方法” 的性能对比	验证 “单阶段 RL 训练是否比传统两阶段（ROA）更优（精度 / 避障）”
III-C	模拟器中腿式导航的评估方法，及 NaVILA 的有效性 / 灵活性	提出适配腿式机器人的新基准 VLN-CE-Isaac，验证 “视觉对腿式导航的必要性”
III-D	NaVILA 能否成功部署到真实机器人的 VLN 任务	验证 “框架在真实环境（工作区 / 家庭 / 户外）的鲁棒性，及跨机器人泛化能力”

### III-A：高层 VLA 性能验证（决策层能力）
聚焦 “VLA 的导航决策与空间理解能力”，用 2 类基准测试：VLN-CE（连续导航） 和 ScanQA（空间场景理解），核心是证明 “单视角 RGB 输入的 VLA 可超越多模态模型”。
1. 实验 1：VLN-CE 基准测试（R2R-CE/RxR-CE）
实验设置：
数据集：R2R-CE（室内房间导航）、RxR-CE（跨房间导航）的「Val-Unseen 拆分」（ unseen 场景，更考验泛化）；
对比对象：两类基线 ——① 依赖 “模拟器预训练航点预测器” 的模型（如 HNR、BEVBert）；② 不依赖航点预测器的模型（如 NaVid、RGB-Seq2Seq）；
关键指标（越低越好：NE；越高越好：OS/SR/SPL/nDTW）：
NE（Navigation Error）：导航误差（终点与目标的距离）；
OS（Oracle Success Rate）：“先知” 成功率（假设知道最优路径时的成功概率）；
SR（Success Rate）：实际成功率（机器人自主导航到目标的概率）；
SPL（Success-weighted Path Length）：成功率加权路径长度（兼顾成功与路径效率）。
核心结果（表 I / 表 II）：
突破单视角局限：NaVILA 仅用「单视角 RGB」，却超越所有 “不依赖航点预测器” 的模型（如 NaVid 的 R2R-CE SR=37%，NaVILA 达 54%）；
媲美多模态模型：即使对比用 “全景图 / 深度 / 里程计” 的模型（如 AO-Planner），NaVILA 的 SR 仍更高（54% vs 47%）；
跨数据集泛化：仅在 R2R-CE 训练，RxR-CE 零样本 SR 达 34.3%，比 NaVid（23.8%）提升 10%+（表 II）。

TABLE I: Comparison with state-of-the-art methods on the Val-Unseen split of R2R-CE [29] and RxR-CE [30]. ?indicates methods using the waypoint predictor from Hong et al. [42]. NaVILA outperforms all methods that do not rely on simulator pre-trained waypoint predictors, even when those methods leverage additional inputs such as depth, panoramic views, and odometry.
Observation R2R Val-Unseen RxR Val-Unseen
S.RGB Pano. Depth Odo. NE ? OS ? SR ? SPL ? NE ? SR ? SPL ? nDTW ?
CMA?[42] HPN+DN?[43] 6.31 6.20 40.0 52.0 36.0 41.0 34.0 36.0 8.76 26.5 - 22.1 47.0
VLN?BERT?[42] Sim2Sim?[44] ? 5.74 6.07 53.0 52.0 43.0 44.0 36.0 39.0 8.98 27.0 22.6 46.7
GridMM?[45] 5.11 61.0 49.0 41.0
Reborn?[48] DreamWalker?[47] Ego2-Map?[46] 5.54 5.40 5.53 57.0 56.0 59.0 49.0 47.0 50.0 44.0 41.0 46.0 5.98 48.6 42.0 63.3
ETPNav?[49] 4.71 65.0 57.0 49.0 5.64 54.7 44.8 61.9
HNR?[50] BEVBert?[51] 4.42 4.57 67.0 67.0 61.0 59.0 50.0 51.0 5.50 4.00 68.5 56.3 46.7 63.5 69.6
HAMT+ScaleVLN?[52] 4.80 55.0 51.0
AG-CMTP [53] 7.90 39.0 23.0 19.0
LAW [54] R2R-CMTP [53] 7.90 6.83 38.0 44.0 26.0 35.0 31.0 22.0 10.90 8.0 8.0 38.0
CM2 [55] 7.02 41.0 34.0 27.0
WS-MGMap [56] 6.28 47.0 38.0 34.0
AO-Planner [57] Seq2Seq [58] 5.55 7.77 59.0 37.0 25.0 47.0 33.0 22.0 12.10 7.06 43.3 13.9 11.9 30.5 50.1 30.8
CMA [58] 7.37 40.0 32.0 30.0
RGB-Seq2Seq [58] NaVILA RGB-CMA [58] NaVid [12] 9.55 10.10 5.47 5.22 62.5 49.0 10.0 8.0 54.0 37.0 5.0 0.0 35.0 49.0 4.0 0.0 6.77 49.3 44.0 58.8

TABLE II: Cross-dataset performance on the RxR-CE [30] ValUnseen split. All results are obtained without training on the RxRCE training set. NaVILA significantly outperforms NaVid [12], the current single-view state-of-the-art.
Observation RxR Val-Unseen
S.RGB Depth Odo. NE ?OS ?SR ?SPL ?
LAW [54] 8.0 9.2
10.87 21.0 8.0
CM2 [55] 8.98 25.3 14.4
WS-MGMap [56] 9.83 29.8 15.0 12.1
Seq2Seq [58] CMA [58] 11.7 11.8 5.02 10.7 4.41 3.51 3.43 2.47
RGB-Seq2Seq [12] 11.2 12.2 0.0 0.0
RGB-CMA [12] 9.55 14.8 0.0 0.0
A2NAV [59] 16.8 6.3
NaVid [12] NaVILA 8.41 8.78 34.5 46.8 34.3 23.8 21.2 28.2

2. 实验 2：ScanQA 空间场景理解基准（3D 问答）
实验设置：
数据集：ScanQA（基于真实 3D 扫描的场景问答，如 “桌子旁边有几把椅子？”）；
对比对象：① 2D VLA 模型（如 NaviLLM）；② 3D 多模态模型（如 LEO、Scene-LLM，需 3D 扫描 / RGBD + 相机姿态输入）；
关键指标：CIDEr（文本生成质量，越高越好）、Bleu-4、Rouge 等。
核心结果（表 III）：
超越 2D VLA：NaVILA（64 帧）的 CIDEr 达 102.7，比 NaviLLM（75.9）高 26.8 分；
优于 3D 模型：即使 3D 模型（如 LEO）需额外 3D 输入，NaVILA 的 CIDEr（102.7）仍略高于 LEO（101.4），证明 “单视角 RGB + 多帧历史” 可弥补 3D 输入的缺失。

TABLE III: Evaluation of spatial scene understanding performance on the ScanQA dataset [32] Validation split. NaVILA outperforms current state-of-the-art VLA models and demonstrates superior performance to other 3D LMMs that require additional input, such as depth or camera pose. Note that ?indicates 3D LMMs that require task-specific fine-tuning on the ScanQA dataset.
|  | ScanQA Validation | | | | |
| --- | --- | --- | --- | --- | --- |
|  | Bleu-4 ? Rouge ? Cider ? Meteor ? EM ? | | | | |
| Task-specific Specialist | | | | | |
| VoteNet+MCAN [ 63 ] | 6.2 | 29.8 | 54.7 | 11.4 | 17.3 |
| ScanRefer+MCAN [ 63 ] | 7.9 | 30.0 | 55.4 | 11.5 | 18.6 |
| ScanQA [ 32 ] | 10.1 | 33.3 | 64.9 | 13.1 | 21.0 |
| 3D-VisTA [ 64 ] | 10.4 | 35.7 | 69.6 | 13.9 | 22.4 |
| 3D Large Multi-modal Models | | | | | |
| 3D-LLM ( flamingo ) ? [ 65 ] | 7.2 | 32.3 | 59.2 | 12.2 | 20.4 |
| 3D-LLM ( BLIP 2 ? flant 5) ? [ 65 | ] 12.0 | 35.7 | 69.4 | 14.5 | 20.5 |
| LL3DA ? [ 66 ] | 13.5 | 37.3 | 76.8 | 15.9 | - |
| Chat-3Dv2 ? [ 67 ] | 14.0 | - | 87.6 | - | - |
| Scene-LLM ? [ 61 ] | 12.0 | 40.0 | 80.0 | 16.6 | 27.2 |
| LEO [ 62 ] | 13.2 | 49.2 | 101.4 | 20.0 | 24.5 |
| 2D Vision-Langauge-Action Models | | | | | |
| NaviLLM [ 60 ] | 12.0 | 38.4 | 75.9 | 15.4 | 23.0 |
| NaVILA (8 frames) | 14.8 | 46.4 | 95.1 | 18.7 | 27.0 |
| NaVILA (64 frames) | 16.9 | 49.3 | 102.7 | 20.1 | 28.6 |

### III-B：低层 RL 策略性能验证（执行层能力）
聚焦 “单阶段 RL 移动策略 vs 传统策略蒸馏方法”，核心验证 “执行精度与避障安全性”。
1. 实验设置
对比对象：ROA（Regularized Online Adaptation，传统两阶段蒸馏方法：先训 “特权编码器”，再蒸馏到 “自适应编码器”）；
评估指标（越低越好）：
线性速度误差：策略跟踪 “前进速度指令” 的偏差（如指令 0.5m/s，实际 0.434m/s 则误差 0.066）；
角速度误差：策略跟踪 “转向角速度指令” 的偏差；
碰撞率：导航过程中与障碍物碰撞的概率（%）。
2. 核心结果（表 V）
NaVILA 的单阶段 RL 策略全面超越 ROA：
方法	线性速度误差	角速度误差	碰撞率（%）
ROA（w/BCLoss）	0.189	0.152	3.25
ROA	0.161	0.152	3.09
NaVILA	0.066	0.113	0.81
关键结论：单阶段训练无需蒸馏，直接与环境交互，不仅提升 “指令跟踪精度”（速度误差降低 60%+），还大幅提升避障安全性（碰撞率从 3.09% 降至 0.81%）。
TABLE V: Low level policy performance.
|  | Linear Vel. Error ? | Angular Vel. Error ? | Collision Rate ? |
| --- | --- | --- | --- |
| ROA ( w/BCLoss ) [ 68 ] | 0.189 | 0.152 | 3.25 |
| ROA [ 68 ] | 0.161 | 0.152 | 3.09 |
| NaVILA | 0.066 | 0.113 | 0.81 |

### III-C：模拟器中的腿式导航性能（系统级模拟验证）
聚焦 “腿式机器人在模拟器中的导航评估”，核心是提出新基准 VLN-CE-Isaac（解决现有基准的缺陷），并验证 “视觉对腿式导航的必要性”。
1. 现有基准的缺陷与新基准设计
现有问题：Habitat 模拟器（VLN-CE 原基准）不考虑腿式机器人的物理限制（如允许穿 10cm 窄缝，四足机器人无法实现）；
新基准 VLN-CE-Isaac（基于 Isaac Sim）：
高保真物理模拟：还原腿式机器人的关节运动、环境交互（如台阶、窄道的物理碰撞）；
数据集：从 R2R-CE 的 1839 条轨迹中筛选 1077 条 “腿式机器人可通行” 的轨迹；
兼容性：支持多腿式机器人（四足 Unitree Go2、人形 Unitree H1）。
2. 实验设计与结果（表 IV）
对比策略：① NaVILA-Vision（用 LiDAR 高度图 + 本体感知）；② NaVILA-Blind（仅本体感知，无视觉）；③ Oracle（理想策略，假设完美执行指令）；
核心结果：
视觉是关键：Go2 中，Vision 策略的 SR（50.2%）比 Blind（36.2%）高 14%；H1 中，Vision（45.3%）比 Blind（24.4%）高 21%，证明 LiDAR 视觉对避障和路径规划的必要性；
人形机器人难度更高：H1 的 SR（45.3%）低于 Go2（50.2%），因 H1 尺寸更大，物理约束更严格；
基准的真实性：Oracle 策略的 SR（51.3%）仅比 Vision（50.2%）高 1.1%，说明新基准的物理模拟接近真实，无 “理想误差”。
TABLE IV: VLN-CE-Isaac evaluation results.
|  | Low-level Observation | | | VLN-CE-Isaac | | | |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  |  | Proprio. LiDAR Height Scan | NE ? | OS ? | SR ? | SPL ? |
| Oracle |  |  |  | 5.25 | 59.8 | 51.3 | 46.9 |
| Unitree Go2 |  |  |  |  |  |  |  |
| NaVILA-Blind | ? |  |  | 6.03 | 49.0 | 36.2 | 33.3 |
| NaVILA-Vision | ? | ? |  | 5.49 | 58.7 | 50.2 | 45.5 |
| Unitree H1 | | | | | | | |
| NaVILA-Blind | ? |  |  | 7.67 | 33.3 | 24.4 | 21.0 |
| NaVILA-Vision | ? |  | ? | 5.86 | 54.6 | 45.3 | 40.3 |
### III-D：真实世界评估（落地能力验证）
聚焦 “NaVILA 在真实环境中的鲁棒性、跨机器人泛化性，及人类视频数据的价值”。
1. 实验设置
环境：工作区、家庭、户外（3 类真实场景）；
指令：25 条（简单：1-2 步，如 “走到椅子旁停下”；复杂：≥3 步，如 “出房间→右转→进前房→停桌前”），每条重复 3 次；
对比对象：GPT-4o（通用 SOTA VLM）；
消融实验：NaVILA-?（未用人类视频训练） vs NaVILA（用人类视频）；
跨机器人验证：四足 Go2 → 人形 Booster T1（VLA 模型不重训）。
2. 核心结果（表 VI）
全面超越 GPT-4o：
工作区复杂指令：NaVILA SR=80%，GPT-4o 仅 33%；
户外复杂指令：NaVILA SR=83%，GPT-4o 仅 50%；
人类视频是关键：加入人类视频后，户外 SR 从 0%（NaVILA-?）提升至 83%，所有环境 SR 均提升；
跨机器人泛化：Booster T1（人形）用相同 VLA，复杂指令 SR=67%，比 GPT-4o（13%）高 54%，且无需调整相机高度 / 视角带来的适配问题；
拓展能力：支持语音识别（图 7），实现 “语音指令→VLA 决策→机器人执行” 的端到端控制。
TABLE VI: Real-world experiments on quadruped (Unitree Go2) and humanoid (Booster T1) conducted in different environments (Workspace, Home, and Outdoor). Simple and Complex refer to simple and complex instruction-following tasks, respectively. Note that ? indicates models trained without human touring videos.
|  | Workspace | | | | Home | | | | Outdoor | | | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Simple | | Complex | | Simple | | Complex |  | Simple | |  | Complex |
| NE ? | SR ? | NE ? | SR ? | NE ? | SR ? | NE ? | SR ? | NE ? | SR ? | NE ? | SR ? |
| Unitree Go2 | | | | | | | | | | | | |
| GPT-4o [ 28 ] |  |  |  |  |  |  | 2.01 0.67 2.38 0.33 1.49 0.53 3.00 0.00 |  | - | 0.67 | - | 0.50 |
| NaVILA ? |  |  |  |  |  |  | 2.00 0.60 1.81 0.73 2.17 0.47 2.32 0.40 |  | - | 0.00 | - | 0.00 |
| NaVILA |  |  |  |  |  |  | 1.29 1.00 1.76 0.80 1.15 1.00 1.76 0.67 |  | - | 1.00 | - | 0.83 |
| Booster T1 | | | | | | | | | | | | |
| GPT-4o [ 28 ] |  |  |  | 1.53 0.67 2.78 0.13 | - | - | - | - | - | 0.44 | - | - |
| NaVILA ? |  |  |  | 2.36 0.40 2.16 0.62 | - | - | - | - | - | 0.22 | - | - |
| NaVILA |  |  |  | 1.18 0.93 1.91 0.67 | - | - | - | - | - | 0.89 | - | - |

NaVILA 通过四层实验验证了框架的先进性：
高层决策：单视角 RGB 的 VLA 可超越多模态模型，空间理解能力媲美 3D 模型；
低层执行：单阶段 RL 策略比传统蒸馏方法更精准、更安全（碰撞率低）；
模拟适配：新基准 VLN-CE-Isaac 填补腿式机器人 VLN 评估空白，视觉是导航核心；
真实落地：在 3 类真实环境中鲁棒，支持跨机器人泛化，人类视频数据大幅提升泛化性。
最终证明：“高层 VLA 决策 + 低层视觉移动” 的两级框架，是解决腿式机器人视觉 - 语言导航的有效方案。
![](/paper/navila-real.png)
Real-world demonstration of NaVILA: Upon receiving human instructions, NaVILA uses a vision-language model to process RGB video frames and employs locomotion skills to execute the task on a robot. The robot successfully handles long-horizon navigation tasks and operates safely in challenging environments.

![](/paper/navila-real2.png)
Qualitative results from the real-world deployment of NaVILA. (a) We integrate speech recognition [70] into NaVILA, allowing a human to control the robot using voice commands that begin with "Hey Robot!". (b) The robot successfully handles long-horizon navigation tasks. Given a lengthy instruction, it moves through different areas of the house and stops at the specified goal. (c), (d), and (e) The robot demonstrates its ability to navigate through obstacles, traverse challenging terrains, and climb up and down stairs.


## 小结与局限
覆盖 4 个与 NaVILA 直接相关的研究方向：
1. 视觉导航（Visual Navigation）：从 “传统 SLAM” 到 “学习驱动”
视觉导航是机器人领域的基础课题，研究演进可分为两大阶段，NaVILA 属于 “学习驱动 + VLN 扩展” 的前沿方向：
阶段 1：传统方法（依赖地图与 SLAM）核心逻辑：先通过深度传感器（如激光雷达）或单目相机构建几何地图，再用 SLAM（同步定位与地图构建）技术确定机器人位置，最后基于地图规划路径。局限：依赖 “预建地图”，无法应对未知环境；SLAM 在动态场景（如行人走动）或弱纹理环境（如白墙）中易失效。
阶段 2：学习驱动方法（模仿学习 / 强化学习）核心突破：无需预建地图，直接从 “视觉观测→动作” 端到端学习导航策略，典型方法包括：
模仿学习（IL）：模仿人类或专家机器人的导航轨迹训练模型；
强化学习（RL）：让机器人在环境中 “试错”，通过奖励（如 “靠近目标得正奖，碰撞得负奖”）优化策略。
延伸：学习方法将视觉导航的应用从 “单一场景” 扩展到视觉 - 语言导航（VLN）（结合自然语言指令），而 NaVILA 正是这一延伸的进一步突破 —— 聚焦 “腿式机器人” 这一更复杂的载体。
2. 视觉 - 语言导航（VLN）：从 “离散节点” 到 “连续环境”
VLN 是 NaVILA 的核心研究场景，领域演进围绕 “环境连续性” 和 “控制精细度” 展开，现有方法的瓶颈直接催生了 NaVILA 的设计：
阶段 1：离散导航（模拟环境，节点 teleport）核心场景：基于 MP3D 等模拟数据集，机器人在 “预定义导航图的节点” 之间 teleport（瞬间移动），无需考虑真实运动（如转弯、避障）。优势：聚焦 “语言理解 + 高层决策”，接近人类水平的指令跟随性能；局限：完全脱离机器人物理约束，无法落地到真实腿式机器人（腿式机器人需控制关节运动，不能 “瞬间移动”）。
阶段 2：连续导航（VLN-CE 基准，真实运动）核心突破：基于 Habitat 等模拟器，机器人需执行 “连续动作”（如前进 50cm、右转 30°），而非节点 teleport，更贴近真实场景。现有瓶颈（NaVILA 的创新点来源）：
依赖 “模拟器预训练航点模型”：如 HNR、BEVBert 等方法，先在模拟器中训练 “航点预测器”（预测机器人周围的候选位置），再基于航点规划路径，但泛化性差（依赖模拟器特定数据，换真实环境或机器人需重训）；
忽视低层控制：仅关注 “往哪走” 的高层决策，不解决 “怎么安全走” 的低层问题（如腿式机器人的避障、关节控制）；
动作覆盖有限：航点仅覆盖附近区域，无法应对长距离导航或复杂地形（如台阶、碎石地）。
NaVILA 的突破：
解耦 “高层决策” 与 “低层执行”：VLA 负责 “生成语言化航点指令”（如 “前进 75cm”），低层策略负责 “将指令转化为关节动作并避障”，无需依赖模拟器航点模型；
适配腿式机器人：首次将 VLN 从 “轮式机器人” 扩展到 “腿式机器人”，解决复杂地形的运动控制问题；
提出新基准 VLN-CE-Isaac：填补 “腿式机器人连续导航评估” 的空白（现有 VLN-CE 基准不考虑腿式机器人的物理约束，如窄缝无法通过）。
3. 机器人基础模型（Robot Foundation Models）：从 “操作任务” 到 “导航任务”
机器人基础模型的目标是 “用统一框架处理多模态输入，输出通用动作”，但现有模型存在 “任务偏向性”，NaVILA 填补了 “VLN 导航” 的空白：
现有模型的局限：
聚焦 “操作任务”：如抓取、摆放物体，训练数据以 “机械手演示” 为主，无法直接用于导航；
导航任务局限：少数导航基础模型（如 LL3DA）仅支持 “目标导航”（输入为 “目标图像” 或 “简短描述”，如 “找到红色椅子”），无法处理 “复杂指令导航”（如 “出房间→右转→进前房→停桌前”）；
腿式机器人适配差：部分模型虽支持视觉 - 语言输入，但输出的是 “轮式机器人速度指令”，无法控制腿式机器人的关节运动。
NaVILA 的突破：专门为 “通用 VLN 任务” 设计 VLA 模型，支持 “复杂自然语言指令”，且通过 “两级框架” 适配腿式机器人（无需重训即可迁移到四足 / 人形机器人），填补了 “腿式机器人 VLN 基础模型” 的空白。
4. 腿式机器人运动学习（Legged Robot Locomotion Learning）：从 “本体感知” 到 “多传感器融合 + 单阶段训练”
腿式机器人的核心挑战是 “复杂地形的运动控制”，现有方法在 “感知鲁棒性” 和 “训练效率” 上存在瓶颈，NaVILA 的低层策略针对性解决了这些问题：
现有方法的瓶颈：
感知局限：
仅依赖本体感知（关节位置 / 速度）：无法避障或应对复杂地形（如坑洼）；
依赖视觉传感器（如 RGB-D 相机）：在强光、透明物体（玻璃）场景下易失效；
训练效率低：多数方法采用 “两阶段蒸馏”（先训 “教师模型” 用特权信息，再蒸馏到 “学生模型” 用真实传感器），步骤繁琐且训练耗时；
训推不一致：部分方法训练时用 “预定义地形高度” 构建高度图，部署时依赖外部工具生成，导致实际性能下降（如 Miki 等人的工作）。
NaVILA 的突破：
多传感器融合：用 LiDAR（激光雷达）生成高度图，解决强光、透明物体的感知盲区；
单阶段 RL 训练：无需蒸馏，直接让策略与环境交互学习，训练效率提升（RTX 4090 上达 60K FPS）；
训推一致：训练和部署均用 “LiDAR 实时生成高度图”，无信息偏差，鲁棒性更强。
二、结论：凝练 NaVILA 的核心价值与实验成果
结论部分的核心是 **“用最简洁的语言总结 NaVILA 的‘框架创新’与‘性能突破’”**，可拆解为 3 个关键点：
1. 框架核心：两级架构的价值
NaVILA 的本质是 **“解耦且协同” 的两级框架 **，解决了 “高层推理” 与 “低层执行” 的矛盾：
高层 VLA 模型：生成 “自然语言形式的中级指令”（如 “前进 75cm”），负责 “语言理解 + 视觉推理 + 导航决策”，保留 LLM 的泛化能力，且可直接从人类视频学习；
低层移动策略：将中级指令转化为 “关节动作”，负责 “实时避障 + 地形适应”，支持跨机器人适配（换机器人仅换低层策略）；
核心优势：避免端到端模型的 “过拟合”（不依赖特定机器人关节参数），同时兼顾 “推理精度” 与 “执行鲁棒性”。
2. 实验成果：全面超越现有方法
结论用定量结果证明 NaVILA 的先进性，覆盖 “高层决策→低层执行→模拟→真实” 全场景：
高层 VLA：在经典 VLN 基准（R2R-CE/RxR-CE）上成功率提升 17%，超越依赖多模态（全景 / 深度 / 里程计）的模型；
低层策略：比传统 “两阶段蒸馏方法”（如 ROA）碰撞率更低（0.81% vs 3.09%），指令跟踪精度更高；
模拟器验证：在新基准 VLN-CE-Isaac 上，视觉策略比 “无视觉盲策略” 成功率高 14%-21%；
真实落地：在工作区 / 家庭 / 户外 3 类场景中，复杂指令成功率达 67%-83%，跨四足（Go2）/ 人形（Booster T1）机器人泛化。
3. 定性价值：拓展 VLN 的应用边界
NaVILA 不仅是技术突破，更拓展了 VLN 的落地场景，如图 7 所示的定性成果：
语音控制：集成语音识别，支持 “Hey Robot! 前进→右转” 的自然交互；
长距离导航：处理 “跨多房间、多步骤” 的复杂指令（如 “出房间→绕楼梯→进浴室→站在浴垫上”）；
复杂地形适配：实现台阶攀爬、碎石地行走、障碍物绕行等腿式机器人特有的导航能力。
三、局限与未来方向：客观指出不足，明确研究展望
结论部分没有回避 NaVILA 的现有问题，而是针对性提出改进方向，体现研究的严谨性：
1. 现有局限
真实场景纠错能力弱：部分场景中机器人 “偏离路线后无法自主回归目标”（如错过转弯路口后，无法重新规划路径）；
计算效率低：高层 VLA 基于图像的 VLMs 构建，推理时计算密集， latency 较高（RTX 4090 上约 1 FPS），难以满足 “超实时导航” 需求（如快速动态场景）；
训练数据依赖：虽引入人类视频，但大规模真实场景（如极端天气、复杂动态环境）的训练数据仍不足，泛化性有提升空间。
2. 未来改进方向
提升泛化性：通过 “大规模真实模拟训练”（如在 Isaac Sim 中构建更多极端场景）增强机器人的纠错能力和环境适配性；
优化计算效率：结合 “长上下文 LLM” 技术，减少 VLMs 的序列处理时间，降低推理 latency；
扩展功能：融入更多交互能力（如动态目标跟踪，如 “跟随行走的人”），或支持多机器人协同导航。
