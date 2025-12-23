---
date: 2025-12-23
title: 2025-2026 全球 Agent & Embodied AI Competition 深度调研
authors: [bubblevan]
tags: []
---

## 1. 核心综述：从"数字智能"迈向"物理实体"的范式转移

2025 年被广泛认为是人工智能从单纯的**数字空间（Digital AI）**向**物理空间（Physical AI）**迈进的关键转折点。随着**大语言模型（LLM）**与**视觉语言模型（VLM）**的成熟，**Agent（智能体）**与 **Embodied AI（具身智能）**赛道迎来了爆发式的增长。

调研显示，当前的竞赛生态呈现出鲜明的**双轨制（Dual-Track）**特征：

- **纯软件智能体（Software Agents）**：在 Kaggle 和 AIcrowd 等平台上，比赛不再局限于传统的分类或回归任务，而是转向了**通用推理（General Reasoning）**、**社会模拟（Social Simulation）**和**多模态游戏控制**。
- **具身智能实体（Embodied Agents）**：在 IROS、CVPR 等机器人顶会上，竞赛焦点从简单的仿真环境导航，转向了**Sim-to-Real（虚实迁移）**、**长程任务规划（Long-horizon Planning）**、**社交导航（Social Navigation）**以及**人形机器人（Humanoid Robots）**的复杂操作。

本报告将分章节深入剖析各大赛事的任务设定、技术难点、评估指标及获胜策略，旨在为您提供一份详尽的"参赛指南"与"技术风向标"。

## 2. Kaggle：通用推理与社会化智能体的演进场

Kaggle 作为数据科学竞赛的旗舰平台，2025 年在 Agent 赛道上推出了两个具有里程碑意义的比赛，分别代表了 AI 在"智商"（抽象推理）和"情商"（社会交互）两个维度的探索。

### 2.1 ARC Prize 2025：通用人工智能（AGI）的"终极图灵测试"

**赛事状态**：活跃 / 长期基准  
**关键时间点**：2025 年 3 月 26 日启动  
**主办方**：ARC Prize Foundation

#### 2.1.1 竞赛背景

**ARC (Abstraction and Reasoning Corpus)** 竞赛被公认为是评估 AI 系统是否具备人类水平推理能力的"北极星"。与依赖海量数据训练的深度学习任务不同，**ARC Prize 2025** 强调**少样本学习（Few-shot learning）**和**即时技能习得**。

现有的 LLM 虽然在语言任务上表现出色，但在处理需要严密逻辑闭环和抽象概括的 ARC 任务时，往往表现出惊人的脆弱性。该比赛的设立初衷，就是为了打破深度学习对"记忆"的依赖，倒逼 AI 掌握真正的"推理"。

#### 2.1.2 任务详情与数据结构

ARC 的核心任务是**网格推理**。

- **输入/输出**：每个任务包含 3 到 5 个演示用的输入/输出网格对（Train Pairs），以及一个测试输入网格（Test Input）。
- **数据格式**：网格中的每个单元格填入 0-9 的整数，可视化为不同的颜色。
- **推理过程**：参赛者的 Agent 必须观察演示对，归纳出从输入到输出的变换规则（如"去除杂色"、"物体补全"、"对称翻转"、"引力模拟"等），并将该规则应用于测试输入，生成预测网格。

**ARC-AGI-2 的新变化（2025版）**：

为了应对日益强大的算力暴力破解，2025 年引入了 **ARC-AGI-2** 版本：

- **难度分级**：数据集被重新校准，引入了更复杂的抽象逻辑，减少了可以通过简单几何变换猜中的题目。
- **抗暴力破解**：测试集的设计更加严苛，旨在挫败纯粹依赖算力搜索（Brute-force）的方案。
- **半私有与私有评估集**：为了防止数据泄露，比赛设置了包含 120 个任务文件的半私有评估集和 120 个任务文件的完全私有评估集。

#### 2.1.3 评估指标与奖金机制

**硬核指标**：ARC 采用极其严苛的**精确匹配（Exact Match）**标准。对于给定的测试输入，Agent 可以提交 2 个预测结果。只要其中任意一个与地面真值（Ground Truth）完全一致（每一个像素都对），则该任务得 1 分，否则得 0 分。没有"部分正确"的说法。这种二进制的评分机制极大地提高了比赛难度，因为微小的推理偏差都会导致零分。

**巨额奖金**：比赛设有 **$125,000** 的基础奖金。更引人注目的是，如果任何团队能够在排行榜上突破 **85%** 的准确率（被认为是人类专家的推理水平），将解锁额外的 **$600,000** 奖金。这反映了业界对于突破当前 AI 推理瓶颈的迫切渴望。

### 2.2 Agent Society Challenge：LLM 的社会学实验场

**赛事时间**：2024 年 12 月 10 日 - 2025 年 6 月 30 日  
**关联会议**：The Web Conference 2025 (WWW '25)  
**主办方**：清华大学、ETH Zurich 等机构

#### 2.2.1 竞赛目标：从"工具人"到"社会人"

如果说 ARC 考察的是 Agent 的 **IQ**，那么 **Agent Society Challenge** 考察的就是 **EQ**。该比赛旨在探索 LLM Agent 在模拟人类社会交互和信息检索（IR）系统中的潜力。这是目前少有的关注 **Agent Social Simulation** 的大型赛事。

#### 2.2.2 双赛道架构解析

比赛设计了两个互补的赛道，分别从"用户"和"系统"两个视角切入：

**用户建模赛道 (User Modeling Track)**：

- **任务**：参赛者需设计 Agent 来模拟真实用户的行为。具体来说，Agent 需要基于用户的历史行为数据（如浏览记录、购买历史），预测该用户对新物品的评分（Star Ratings）并撰写评论（Review Generation）。
- **难点**：这不仅仅是预测一个数字，而是要求 Agent 能够"理解"用户的偏好、情感倾向和语言风格。Agent 必须展现出与真实人类行为的高度对齐性（Alignment）。
- **数据支撑**：比赛使用了 **Yelp**、**Amazon**、**Goodreads** 三大开源数据集，覆盖了餐饮、电商和图书三个截然不同的领域，考验 Agent 的跨域泛化能力。

**推荐赛道 (Recommendation Track)**：

- **任务**：在这个赛道中，Agent 扮演的是"推荐系统"的角色。面对特定的用户 Agent 和候选物品列表，参赛 Agent 需要生成个性化的推荐排名。
- **创新点**：不同于传统的基于矩阵分解或深度学习的推荐算法，这里要求使用 **LLM Agent** 作为推荐核心。参赛者需要构建包含**推理（Reasoning）**、**记忆（Memory）**、**工具使用（Tool Use）**的模块化 Agent，通过多轮交互来优化推荐结果。

#### 2.2.3 评估体系

该比赛的评估不仅看准确率（如 **RMSE**），更看重 Agent 行为的拟真度。对于推荐赛道，评估指标可能包括 **NDCG** 等传统 IR 指标；而对于用户建模赛道，则会评估生成的评论与真实评论的语义相似度及情感一致性。这实际上是在测试 **Generative Agents** 在社会科学模拟中的有效性。

## 3. IROS 2025：具身智能的巅峰竞技场

**IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)** 是全球机器人领域的顶级会议。2025 年的 IROS 于 **10 月 19 日至 25 日**在**中国杭州**举行。鉴于举办地的产业优势，IROS 2025 承载了大量与具身智能（Embodied AI）紧密相关的硬核赛事。

### 3.1 RoboSense Challenge @ IROS 2025

**RoboSense（速腾聚创）挑战赛**是 IROS 2025 的重头戏之一。
**全称**：RoboSense Challenge - SocialNav Track @ IROS 2025

**关键时间节点**：

- **开始时间**：2025 年 5 月 31 日
- **注册截止**：2025 年 8 月 15 日
- **私有代码库准备截止**：2025 年 9 月 5 日（这正是您记忆中"8月左右结束"的验证阶段）
- **结束时间**：2025 年 9 月 16 日
- **决赛展示**：2025 年 10 月 IROS 会议现场

#### 3.1.1 核心任务：社交导航 (Social Navigation)

该挑战赛的核心痛点在于解决移动机器人在人类密集环境中的导航问题。

**技术背景**：传统的机器人导航算法（如 **A*** 或 **DWA**）往往把人类视为静态障碍物或简单的动态物体，这会导致机器人行为"粗鲁"（如紧贴人擦身而过）或"冻结"（在人群中不知所措）。

**赛题要求**：参赛者需要在 **Habitat 3D 模拟器**中开发导航策略。机器人不仅要从起点到达终点，还必须遵守社会规范（Social Norms），例如：

- 保持适当的社交距离（不侵犯个人空间）
- 避免在人类行进路线上突然急停或转向
- 在拥挤场景中展现出类似人类的避让逻辑

**感知挑战**：比赛强调**鲁棒感知（Robust Sensing）**。虽然是在仿真环境中，但模拟器会引入类似真实 **LiDAR** 的噪声和数据缺失，甚至模拟恶劣天气或传感器故障，要求算法具备极强的抗干扰能力。

#### 3.1.2 评估与交付

**私有代码库机制**：为了防止作弊并确保结果的可复现性，参赛者必须在 9 月 5 日前准备好私有的 GitHub 仓库，授权给官方账号 `robosense2025` 进行代码审查和复现。

**Sim-to-Real 潜力**：虽然主要基于 Habitat 仿真，但 RoboSense 作为 LiDAR 硬件厂商，其赛事设计的最终目的是为了服务于真实的具身智能产品，因此获奖算法极有可能会被要求在真实机器人平台上进行验证。

### 3.2 AgiBot World Challenge：人形机器人的"世界模型"

如果说 RoboSense 关注的是轮式机器人的"眼"和"腿"，那么 **AgiBot World Challenge** 则关注的是人形机器人的"全脑"协同。这是 IROS 2025 上最受瞩目的**人形机器人（Humanoid Robot）**赛事。

**主办方**：AgiBot（智元机器人）  
**背景**：AgiBot 是中国领先的人形机器人独角兽企业。本次比赛依托其发布的 **AgiBot World** —— 一个大规模、多智能体、高保真的机器人仿真与数据集平台。

#### 3.2.1 解决"数据饥渴"与"短视"问题

现有的机器人学习基准（Benchmark）往往存在两大缺陷：

- **数据质量低**：缺乏高质量的真实世界交互数据
- **任务短视（Short-horizon）**：大多局限于简单的"抓取-放置"，缺乏长序列规划

AgiBot World Challenge 要求参赛者利用其提供的大规模多智能体数据集，训练通用的具身智能策略。比赛鼓励参赛者使用**端到端（End-to-End）**的学习方法，直接从像素或点云输入映射到关节力矩输出，实现机器人的全身协调控制。

#### 3.2.2 获胜团队与技术风向

根据最新的比赛结果，本次挑战赛吸引了全球顶尖的高校和企业实验室参与，获奖名单揭示了当前具身智能的第一梯队：

- **冠军**：VIPL-GENUN (中国科学院计算技术研究所)
- **亚军**：HD-Robo (HiDream.ai), SHIELD-LMD (阿里云-上海交通大学)
- **季军**：Pifast (南京理工大学), RoboX (清华大学/南京理工大学/华威大学)

**技术洞察**：

- **学术界与产业界的融合**：前十名中既有纯高校队伍，也有像阿里云、智元机器人这样的企业联队。这表明具身智能的竞赛已经脱离了纯学术研究，进入了产业落地的攻坚期。
- **Sim-to-Real 是关键**：虽然比赛本身基于数据和仿真，但所有头部队伍都展现出了极强的 Sim-to-Real 迁移能力，这正是人形机器人能否走出实验室的关键。

### 3.3 Aerial Autonomy Challenge：空中机器人的极限挑战

IROS 2025 还举办了 **Aerial Autonomy Challenge**，专注于无人机在复杂受限环境下的自主飞行。

**场景设计**：模拟了极为恶劣的真实环境，包括移动障碍物、极窄的缝隙、起伏不平的表面以及风场干扰。

**核心难点**：传统的 **GPS** 导航在这些场景下完全失效，参赛者必须完全依赖**板载传感器（On-board Sensing）**进行 **SLAM（同步定位与建图）**和路径规划。这对于 Agent 的实时感知和快速反应能力提出了极高要求。

## 4. NeurIPS 2025：具身智能的理论高地

如果说 IROS 侧重于机器人系统的综合能力，那么 **NeurIPS (Conference on Neural Information Processing Systems)** 则更关注 AI 算法的底层逻辑。2025 年的 NeurIPS 举办的 **Embodied Agent Interface (EAI) Challenge** 代表了学术界对 Agent 评估体系的最深刻反思。

### 4.1 Embodied Agent Interface (EAI) Challenge

**赛事时间**：2025 年 8 月 15 日 - 12 月 7 日  
**核心理念**：拒绝"黑盒"评估，拥抱"模块化"诊断。

#### 4.1.1 痛点：成功率的欺骗性

在过去，评估一个机器人 Agent 好不好，往往只看任务成功率（Success Rate）。例如，"让机器人去倒咖啡"，如果机器人成功了就是 100 分，失败了就是 0 分。然而，这种评估方式掩盖了 LLM Agent 的真实能力——它是因为没听懂指令失败的？还是规划错了步骤？或者是手滑了没抓稳？

#### 4.1.2 解决方案：四大模块化赛道

EAI Challenge 建立了一个统一的评估框架，将具身推理拆解为四个独立的模块进行打分：

1. **目标解释 (Goal Interpretation)**
   - **任务**：将模糊的自然语言指令（如"把家里收拾干净"）转化为形式化的目标状态
   - **指标**：使用 **LTL (Linear Temporal Logic，线性时序逻辑)** 来验证目标的逻辑正确性

2. **子目标分解 (Subgoal Decomposition)**
   - **任务**：将高层目标拆解为一系列可执行的子步骤（如"先找到杯子"，"再找到咖啡机"）
   - **指标**：评估步骤的必要性和顺序的合理性

3. **动作序列生成 (Action Sequencing)**
   - **任务**：生成具体的动作指令序列
   - **指标**：轨迹的可行性（Trajectory Feasibility）

4. **转换建模 (Transition Modeling)**
   - **任务**：预测动作执行后的环境状态变化（即 **World Model** 能力）
   - **指标**：预测状态与真实模拟器状态的差异

#### 4.1.3 数据集与平台

比赛结合了 **VirtualHome**（侧重家庭活动逻辑）和 **BEHAVIOR**（侧重复杂物理交互）两大经典模拟器，提供了包含 338 个 VirtualHome 任务和 100 个 BEHAVIOR 任务的庞大测试集。

#### 4.1.4 获奖情况

- **冠军**：AxisTilted2
- **亚军**：SingaX
- **季军**：CtrlAct
- **最具创新奖**：nju-lamda12 (南京大学 LAMDA 实验室)

**技术洞察**：EAI Challenge 的举办标志着具身智能研究进入了"精细化诊断"阶段。南大 LAMDA 实验室的获奖也再次印证了中国研究团队在 Agent 推理领域的深厚积累。

## 5. CVPR 2025：视觉驱动的具身智能

计算机视觉顶会 **CVPR 2025** (2025年6月，纳什维尔) 举办了**第 6 届 Embodied AI Workshop**，这一系列赛事更加关注视觉感知（Vision）如何引导动作（Action）。

### 5.1 ManiSkill-ViTac Challenge 2025：触觉感知的觉醒

在所有的 CVPR 挑战赛中，**ManiSkill-ViTac** 是最独特的一个，因为它引入了**触觉（Tactile）**。

**背景**：在精细操作（如插钥匙孔、盲操作）中，单纯依靠视觉往往会因为遮挡或深度估计误差而失败。触觉传感器（如 **GelSight**）能提供关键的接触面信息。

**任务**：比赛设置了如"插拔连接器"、"开锁"等高精度任务。参赛者需要融合视觉图像和触觉信号来训练策略网络。

**技术趋势**：获奖方案通常采用 **Visuo-Tactile Fusion Transformer** 架构，将触觉热图与视觉 RGBD 图像进行特征对齐。这不仅是视觉比赛，更是多模态融合的极致体现。

### 5.2 其他关键赛道

- **Social Mobile Manipulation (SMM)**：不仅要导航，还要在移动中进行操作（如在行走中递送物品），且需处理多智能体交互。
- **ARNOLD Challenge**：侧重**语言引导（Language-Grounded）**的操作，特别是涉及流体（Fluids）和非刚性物体的操作，这是传统物理引擎难以模拟的难点。
- **HAZARD Challenge**：针对灾难救援场景的多物体搜救，强调意图推理。

## 6. 区域聚焦：上海与阿里云的产业级赛事

除了学术会议，2025 年中国依托强大的产业链优势，举办了多场高规格的具身智能产业赛事，实现了从"算法"到"硬件"的跨越。

### 6.1 2025 全球开发者先锋大会 (GDPS) & 国际具身智能技能大赛

**时间/地点**：2025 年 12 月 12-14 日，上海张江  
**产业背景**：上海市设立了百亿级具身智能产业基金，试图打造机器人领域的"硅谷"。本次比赛是全球少有的大规模线下真机实战。

#### 6.1.1 赛道设置与实战表现

不同于在电脑上跑模拟器，这里的比赛要求机器人真刀真枪地干活：

**工业装配赛道**：

- **Kepler Robotics（开普勒）**的人形机器人 **K2** 展示了在物流环境下的搬运与装配能力，核心挑战在于重建传统的工业物流逻辑。
- 华东理工大学的 "Huali Zhi Yu" 战队凭借此项目夺冠。

**家庭服务赛道**：

- **Humanoid Robot (Shanghai) Co Ltd** 的机器人完成了叠衣服、整理餐具等高难度柔性物体操作任务。这要求机器人具备极强的模型泛化能力，因为衣服的形态是无穷无尽的。
- **Qinglang XMAN-R1** 获得了餐厅服务项目的冠军。

**应急救援赛道**：

- **Unitree（宇树）**的 **B2-W** 四足机器人和 **G1** 人形机器人在 10x30 米的极端地形赛道上完成了搜救任务，展示了卓越的动态平衡能力。

### 6.2 天池 (Tianchi) 系列赛事

- **多模态对话意图识别挑战赛**：由**淘天集团（TaoTian）**联合 WWW 2025 举办。虽然偏向 NLP，但其目的是为了训练能够理解复杂电商场景（图像+文本）的 Agent，这对于未来的服务型机器人至关重要。
- **具身智能光学动作捕捉挑战赛**：属于 2025 RAICOM 大赛的一部分，重点考察如何利用光学动捕数据来训练**灵巧手（Dexterous Hand）**。这是目前人形机器人学习人类复杂动作（如转笔、剥蛋）的最主流路径。

## 7. 2025-2026 竞赛时间线：正在进行与即将开启

### 7.1 正在进行中 (Active) 的比赛

截止 **2025/12/23** 仍接受报名或提交。

#### 7.1.1 Orak Game Agent Challenge 2025

- **平台**：**AIcrowd**
- **截止时间**：2026年2月1日（代码提交截止）
- **核心任务**：**通才游戏智能体**。要求开发一个基于 **LLM** 的 **Agent**，能够通过视觉和文本理解，游玩 5 款机制截然不同的游戏：**Super Mario**（动作）、**Pokémon**（RPG策略）、**StarCraft II**（即时战略）、**2048**（逻辑）等
- **技术关键词**：**Multimodal LLM**、**MCP (Model Context Protocol)**、**Generalist Agent**、**Cross-game Transfer**
- **链接**：[AIcrowd Orak Challenge Page](https://www.aicrowd.com/challenges/orak-game-agent-challenge-2025)

#### 7.1.2 Global Chess Challenge 2025

- **平台**：**AIcrowd**
- **截止时间**：2026年初（Ongoing）
- **核心任务**：**多模态国际象棋智能体**。不同于传统的 **UCI** 引擎，该比赛可能侧重于通过视觉识别棋盘或模仿人类风格的决策（**Persona-based**）
- **技术关键词**：**Game AI**、**Strategic Reasoning**、**Behavioral Cloning**
- **链接**：[AIcrowd Challenges](https://www.aicrowd.com/challenges)

#### 7.1.3 Meta CRAG - MM Challenge 2025

- **平台**：**AIcrowd**
- **截止时间**：2026年初（Ongoing）
- **核心任务**：**多模态检索增强生成 (Multimodal RAG)**。虽然不是纯 **Agent** 控制，但任务要求构建能够检索图像和文本信息并进行复杂推理的系统，是构建 "**Information Seeking Agent**" 的核心模块
- **技术关键词**：**RAG**、**Multimodal Reasoning**、**Knowledge Retrieval**
- **链接**：[AIcrowd Challenges](https://www.aicrowd.com/challenges)

#### 7.1.4 Flextrack Challenge 2025

- **平台**：**AIcrowd**
- **截止时间**：2026年初（Ongoing）
- **核心任务**：**能源灵活性智能体**。设计智能体在动态环境中优化建筑能源消耗，属于 **Reinforcement Learning for Control** 的实际应用
- **技术关键词**：**RL**、**Optimization**、**Smart Grid Agent**
- **链接**：[AIcrowd Challenges](https://www.aicrowd.com/challenges)

### 7.2 即将开启 / 预告中 (Upcoming) 的比赛

重点关注 **ICRA 2026**（2026年6月举办，报名通常在 1-3月）。

#### 7.2.1 The BARN Challenge 2026 (Benchmark Autonomous Robot Navigation)

- **会议**：**ICRA 2026**
- **开启时间**：2026年1月1日（线上提交开启）
- **核心任务**：**高约束环境导航**。在极度狭窄、充满障碍的仿真环境（及随后的真机）中控制移动机器人导航。这是考察 **Agent** 在极端环境下 **Navigation Policy** 鲁棒性的经典赛事
- **技术关键词**：**Navigation**、**Obstacle Avoidance**、**Sim-to-Real**、**Reinforcement Learning**
- **链接**：[BARN Challenge 2026](https://cs.gmu.edu/~xiao/Research/BARN_Challenge/BARN_Challenge26.html)

#### 7.2.2 AgiBot World Challenge 2026

- **会议**：**ICRA 2026**
- **状态**：已接受（**Accepted Competition**），即将发布规则
- **核心任务**：**人形机器人通用操作**。依托 **AgiBot World** 仿真器，考察人形机器人在非结构化环境下的长程任务规划与全身控制（**Whole-body Control**）。包含 "**World Model**"、"**VLM+VLA**"、"**WBC**" 三个赛道
- **技术关键词**：**Humanoid Robot**、**VLA (Vision-Language-Action)**、**Embodied AI**、**Manipulation**
- **链接**：[AgiBot World](https://agibot-world.com/)（关注其ICRA 2026更新）

#### 7.2.3 LeHome Challenge 2026

- **会议**：**ICRA 2026**
- **状态**：已接受，即将发布
- **核心任务**：**家庭场景衣物操作 (Garment Manipulation)**。这是具身智能中的深水区，要求机器人处理柔性物体（**Deformable Objects**），如叠衣服、挂衣服
- **技术关键词**：**Deformable Object Manipulation**、**Policy Learning**、**Home Robotics**
- **链接**：[ICRA 2026 Competitions](https://2026.ieee-icra.org/program/competitions/)

#### 7.2.4 REAL-I: The 1st Real-world Embodied AI Learning Challenge

- **会议**：**ICRA 2026**
- **状态**：已接受
- **核心任务**：**真实世界具身学习**。强调摆脱纯仿真，直接在真实机器人或具有极高保真度的 **Sim-to-Real** 设置中评估学习算法的效率和安全性
- **技术关键词**：**Real-world RL**、**Safe Learning**、**Sample Efficiency**
- **链接**：[ICRA 2026 Competitions](https://2026.ieee-icra.org/program/competitions/)

#### 7.2.5 Amazon Nova AI Challenge 2026

- **主办方**：**Amazon Science**
- **面向群体**：大学生团队
- **核心任务**：**可信软件智能体 (Trusted Software Agents)**。分为开发者赛道（构建防御性 **Agent**）和红队赛道（攻击/测试 **Agent** 安全性）
- **技术关键词**：**AI Safety**、**Agentic Coding**、**Red Teaming**
- **链接**：[Amazon Nova AI Challenge](https://www.amazon.science/research-awards/nova-ai-challenge)

#### 7.2.6 ARC-AGI-3 (2026 Preview)

- **平台**：预计 **Kaggle** 或 **ARC** 官网
- **状态**：预告中
- **核心任务**：**交互式推理 (Interactive Reasoning)**。不同于 **ARC-AGI-1/2** 的静态网格，第3版预计将引入游戏化的交互环境，测试 **Agent** 的即时学习与适应能力
- **技术关键词**：**AGI**、**Few-shot Learning**、**Interactive Environment**
- **链接**：[ARC Prize](https://arcprize.org/)

### 7.3 近期结束但值得关注的比赛（用于参考/复现）

您提到的 **RoboSense** 属于此类，适合作为 **Project** 复现练习。

#### 7.3.1 RoboSense Challenge @ IROS 2025

- **状态**：已结束（2025年9月结束）
- **内容**：包含 "**Driving with Language**"（语言驱动驾驶）和 "**Social Navigation**"（社交导航）等赛道。虽然比赛结束，但数据集和榜单通常会开放，适合作为简历中的 **Research Project** 复现对象
- **链接**：[RoboSense Challenge 2025](https://robosense2025.github.io/)

#### 7.3.2 NeurIPS 2025 Embodied Agent Interface (EAI) Challenge

- **状态**：已结束（2025年12月7日展示）
- **内容**：评估 **LLM Agent** 在具身环境（**VirtualHome/BEHAVIOR**）中的规划与推理能力
- **链接**：[NeurIPS 2025 EAI Challenge](https://neurips25-eai.github.io/)

## 竞赛日历速览表 (2025-2026)

| 赛事名称 | 平台/会议 | 关键截止时间 | 核心技术点 |
|---------|----------|------------|-----------|
| ARC Prize 2025 | Kaggle | 长期活跃 | AGI 推理、少样本学习 |
| Agent Society Challenge | Kaggle / WWW | 2025年6月 | 用户模拟、推荐系统 Agent |
| RoboSense SocialNav | IROS 2025 | 2025年9月5日 | 社交导航、鲁棒感知 |
| EAI Challenge | NeurIPS 2025 | 2025年12月 | 模块化评估、LTL 逻辑 |
| Orak Game Agent | AIcrowd | 2026年2月 | 跨游戏通用 Agent、多模态 |
| GDPS 技能大赛 | 上海线下 | 2025年12月 | 真机实战、工业装配、家庭服务 |
| LeHome Challenge | ICRA 2026 | 2026年5月 | 衣物柔性物体操作 |
