---
title: "From Cognition to Precognition: A Future Framework For Social Navigation"
---

我怎么没想到？一拍大腿。这就是一个把 Human Trajectory Prediction 融入到 Social Navigation 任务的工作啊！
后者的主流范式是将“视觉感知”（从图像中识别出行人坐标）和“路径预测”（根据坐标预测未来轨迹）解耦，这就更好做 A+B 了！

## Introduction

### 研究目标

机器人在拥挤空间导航需同时感知环境当前状态与预测人类未来运动，实现安全与效率平衡。

### 核心问题

- **传统 RL 方法**：短视避障，无法应对动态人类环境 [5][6]
- **分层方法**：依赖环境先验，不适用于真实场景 [8]
- **现有基准**：场景简化（忽略环境复杂性 [16][17][18]）、假设全局信息（如完整地图 [8]）
- **轨迹预测**：多应用于户外，室内场景因空间有限碰撞风险更高 [7]

### 核心创新预告

- **提出 Falcon 框架**：整合轨迹预测与社交惩罚
- **构建 SocialNav 基准**：含两个真实数据集

## Related Works

| 类别 | 核心研究内容 | 本文区别 |
| --- | --- | --- |
| **社交导航（SocialNav）** | 起源于 iGibson 挑战 [19]，研究多 Agent 避碰 [23][24][25]、时空图建模交互 [28][31] | **Falcon** 在辅助任务中显式整合人类轨迹预测，而非仅感知当前状态 |
| **导航辅助任务** | 自监督任务提升样本效率 [35]，现有 SocialNav 辅助任务用特权信息（如人机距离 [8]） | 辅助任务不仅感知当前人类位置，还预测未来轨迹，降低碰撞风险 |
| **人类轨迹预测** | 分物理模型 [28][42]、历史学习 [45]、规划推理 [48] 三类，支撑自主系统安全行为 [40] | 将轨迹预测与社交感知信息融合到导航策略，适配室内动态场景 |

> **值得看的其实是后两个，辅助任务和人类轨迹预测**

## Methodology

### Problem Formulation

机器人 $a$ 在含 $N$ 个动态人类的环境中，从初始配置 $q_a \in Q$ 生成路径 $\tau_a$ 至目标 $g_a \in Q$。

#### 目标函数

$$\tau_a = \arg\min_{\tau \in \mathcal{T}} \left(c_a(\tau) + \lambda_a c_a^s(\tau, \tau_{1:N})\right)$$

其中：
- $c_a$：目标引导成本
- $c_a^s$：社会规范成本
- $\lambda_a$：权重系数

#### 约束条件

1. **不碰静态障碍**：$A_a(\tau_a) \notin C_{\text{obs}}$
2. **不碰人类**：$A_a(\tau_a) \cap A_i(\tau_i) = \emptyset$
3. **路径起点 / 终点匹配**：
   - $\tau_a(0) = q_a$（起点匹配）
   - $\tau_a(T) = g_a$（终点匹配）

其中 $T$ 为 episode 结束时间。

### Main Policy Network

![](/paper/falcon-overview.png)

**核心作用**：基于环境观测输出导航动作，同时通过社交惩罚确保行为合规。

主策略网络有两个关键组件：从观测中提取视觉和时序特征的状态编码器，以及鼓励社交合规的社交认知惩罚。

#### 状态编码器：提取环境特征

在每个时间步，状态编码器处理以下输入：

- **点目标（导航终点）**：通过线性编码器处理
- **深度图像（环境视觉信息）**：通过 **ResNet-50** 视觉编码器处理
- **时序特征**：2 层 **LSTM** 提取时序特征，然后输入到：
  - **动作头（Actor Head）**：生成动作
  - **价值头（Value Head）**：预测奖励
  - **潜在变量 $\delta R$**：连接辅助任务模块（见下一节）

#### 奖励函数

##### PointNav 奖励函数

在训练过程中，策略由鼓励到达目标行为的奖励函数引导。在每个时间步 $t$ 使用经典的 **PointNav** 奖励函数 [53]：

$$R_{\text{pointnav}}^t = -\beta_d \Delta d - r_{\text{slack}} + \beta_{\text{succ}} \cdot I_{\text{succ}}$$

其中：
- $\Delta d$：到目标的地测距离变化
- $r_{\text{slack}}$：步长惩罚，防止不必要的动作
- $I_{\text{succ}}$：成功导航的指示变量
- $\beta_d$ 和 $\beta_{\text{succ}}$：权重项

##### 社交认知惩罚（SCP）

**社交认知惩罚（SCP）**：修正奖励以符合社交规范

**PointNav** 的奖励函数对于 **SocialNav** 是不充分的，因为它忽略了动态环境和社交互动。为了解决这个问题，我们引入了**社交认知惩罚（SCP）**，这是一组旨在促进遵守社交规范的惩罚。

###### 1. 障碍碰撞惩罚（Obstacle Collision Penalty）

碰静态障碍或人类时触发惩罚：

$$r_{\text{coll}} = \beta_s \cdot I_{s,\text{coll}} + \beta_h \cdot I_{h,\text{coll}}$$

其中 $I_{s,\text{coll}}$ 和 $I_{h,\text{coll}}$ 是分别表示与静态障碍物和人类碰撞的指示变量，$\beta_s$ 和 $\beta_h$ 是对应的惩罚权重。

###### 2. 人类距离惩罚（Human Proximity Penalty）

这个惩罚确保智能体与人类保持安全距离：

$$r_{\text{prox}} = \sum_{i=1}^{N} \begin{cases} \beta_{\text{prox}} \cdot \exp(-d_i^t) & \text{if } d_i^t < 2.0 \text{ m} \\ 0 & \text{if } d_i^t \geq 2.0 \text{ m} \end{cases}$$

其中 $d_i^t = \|\tau_a(t) - \tau_i(t)\|$ 是机器人在时间步 $t$ 到第 $i$ 个人的距离。随着 $d_i$ 减小，惩罚呈指数增长，促使智能体避开人类。当机器人距离目标 2.0 米以内时，惩罚被移除。

###### 3. 轨迹阻碍惩罚（Trajectory Obstruction Penalty）

这个惩罚阻止机器人阻碍未来 $H$ 步的人类轨迹。它通过考虑当前和未来位置来预测潜在的阻碍，越早的重叠惩罚越重：

$$r_{\text{traj}} = \sum_{k=t+1}^{t+H} \sum_{i=1}^{N} \begin{cases} \beta_{\text{traj}} \cdot \frac{1}{k-t+1} & \text{if } d_{\text{traj},i}^k < 0.05 \text{ m} \\ 0 & \text{if } d_{\text{traj},i}^k \geq 0.05 \text{ m} \end{cases}$$

其中 $d_{\text{traj},i}^k = \|\tau_a(k) - \tilde{\tau}_i(k)\|$ 是机器人和人类在第 $k$ 个时间步的未来轨迹之间的距离。当机器人接近目标 2.0 米以内时，此惩罚也被取消。

##### 总奖励函数

总奖励函数是目标导向奖励 $R_{\text{pointnav}}^t$ 和 **SCP** 惩罚 $R_{\text{scp}}^t$ 的组合：

$$R_{\text{socialnav}}^t = R_{\text{pointnav}}^t - R_{\text{scp}}^t$$

其中 $R_{\text{scp}}^t$ 定义为：

$$R_{\text{scp}}^t = r_{\text{coll}} + r_{\text{prox}} + r_{\text{traj}}$$

#### 训练

主策略网络使用 **DD-PPO** [53] 训练，优化 **PPO** 损失 $L_{\text{main}}$。


### Spatial-Temporal Precognition Module

**核心作用**：通过 3 个社交感知辅助任务，提升主网络对"人类动态"的理解，间接优化导航决策。

该模块利用三个社交感知辅助任务来增强机器人对时空动态的把握。如图 2 所示，每个辅助任务使用类似的网络结构，包含 **LSTM** 编码器和自注意力块。

**共性设计**：每个任务均含「**LSTM** + 自注意力机制」，输入均包含主网络的潜在变量 $\delta R$（实现主网络与辅助任务的信息联动）。

#### 三个辅助任务（按"感知维度"递进）

##### 1. 人类数量估计（Human Count Estimation）

预测场景中 0-6 人（$M=6$）的概率分布，用交叉熵损失优化，帮助机器人判断环境拥挤程度。

该任务旨在估计人类的总数，输出是 0 到 $M$（在我们的实验中 $M=6$）之间的离散值。**LSTM** 以主策略网络的潜在变量 $\delta R$ 作为输入，输出编码 $\Phi_R$，然后用于自注意力层 [54]，其中 $Q = K = V = \Phi_R$。

分类器 $\phi_{\text{count}}$ 使用时间步 $t$ 的注意力输出 $A_t$ 预测人类数量的概率：

$$\hat{n}_k = \phi_{\text{count}}(A_t) \quad \text{for } k \in \{0, 1, ..., M\}$$

损失使用交叉熵计算：

$$L_{\text{count}} = -\sum_{k=0}^{M} n_k \log(\hat{n}_k)$$

其中 $n_k$ 是真实数量的指示变量，$\hat{n}_k$ 是预测 $k$ 个人的概率。

##### 2. 当前位置跟踪（Current Position Tracking）

基于已知人类数量 $N$，预测人类相对机器人的 2D 位置，用 **MSE** 损失优化，精准定位人类当前位置。

该任务跟踪人类相对于机器人的 2D 位置。输入是 $\delta R$ 和场景中人类智能体的真实数量 $N$。**LSTM** 输出 $\Phi_{R;N}$ 在自注意力层中用作 $Q = K = V = \Phi_{R;N}$。

回归器 $\phi_{\text{pos}}$ 预测每个人类在时间 $t$ 的位置 $\hat{P}_i^t$：

$$\hat{P}_i^t = \phi_{\text{pos}}(A_t)$$

我们使用预测位置和真实位置之间的**均方误差（MSE）**，使用掩码 $M$ 来处理场景中人类数量少于 $M$ 的情况：

$$L_{\text{pos}} = \frac{1}{|M|} \sum_{i \in M} \|\hat{P}_i^t - P_i^t\|^2$$

##### 3. 未来轨迹预测（Future Trajectory Forecasting）

用双向 **LSTM**（处理时序复杂性），基于当前人类位置，预测未来 $H$ 步轨迹，用 **MSE** 损失优化，提前预判人类移动方向。

该任务预测多个时间步的人类轨迹。由于复杂性，它使用双向堆叠 **LSTM**。输入包括 $\delta R$、$N$ 和当前人类位置 $P_i^t$。**LSTM** 输出 $\Phi_{R;N;P}$ 在注意力层中用作 $Q = K = V = \Phi_{R;N;P}$。

回归器 $\phi_{\text{traj}}$ 预测未来 $H$ 步的轨迹：

$$\hat{P}_i^{t+1:t+H} = \phi_{\text{traj}}(A_t)$$

类似地，使用掩码 $M$ 应用 **MSE**：

$$L_{\text{traj}} = \frac{1}{|M|} \sum_{i \in M} \|\hat{P}_i^{t+1:t+H} - P_i^{t+1:t+H}\|^2$$

#### 损失与优化

**辅助损失**定义为：

$$L_{\text{aux}} = L_{\text{count}} + L_{\text{pos}} + L_{\text{traj}}$$

在训练过程中，主策略网络和这些辅助任务一起优化。总损失函数是主策略损失 $L_{\text{main}}$ 和辅助损失 $L_{\text{aux}}$ 的加权和：

$$L_{\text{total}} = \beta_{\text{main}} L_{\text{main}} + \beta_{\text{aux}} L_{\text{aux}}$$

其中 $\beta_{\text{main}}$ 和 $\beta_{\text{aux}}$ 是它们各自的损失权重。

**训练逻辑**：主网络（决策）与 **SPM**（感知增强）同步优化，让机器人"既会走，又懂让"。

## Experiment

### 数据集构建

#### 现有数据集的三大缺陷

- **场景类型单一**：如 **iGibson-SN** 仅 15 个住宅场景，缺乏办公、健身房等真实场景
- **人类密度失衡**：如 **HabiCrowd** 最大 40 人过度拥挤，**HM3D-S** 仅 3 人交互不足
- **运动模式不自然**：要么是随机游走（**iGibson-SN**）、要么无动画（**HabiCrowd**），不符合人类真实行为

#### 数据集对比

| Dataset | Num. Scenes | Scene Type | Max Num. Humans | Natural Motions |
| --- | --- | --- | --- | --- |
| iGibson-SN [55] | 15 | residence | 3 | ✗ |
| Isaac Sim [56] | 7 | residence, office, depot, etc. | 7 | ✓ |
| HabiCrowd [34] | 480 | residence, office, gym, etc. | 40 | ✗ |
| HM3D-S [8] | 900 | residence, office, shop, etc. | 3 | ✗ |
| **Social-HM3D** | **844** | residence, office, shop, etc. | **6** | **✓** |
| **Social-MP3D** | **72** | residence, office, gym, etc. | **6** | **✓** |

**表格说明**：

- **Num. Scenes**：场景数量（新数据集总量 916 个，远多于 **iGibson-SN** 的 15 个、**Isaac Sim** 的 7 个）
- **Scene Type**：场景类型（新数据集覆盖住宅、办公室、商店、健身房等，解决部分数据集类型单一问题）
- **Max Num. Humans**：最大人类数（新数据集设为 6，避免 **HabiCrowd** 的 40 人过度拥挤，也比 **HM3D-S** 的 3 人更易产生人机交互）
- **Natural Motions**：自然运动（新数据集标注 ✓，区别于 **iGibson-SN**、**HabiCrowd** 等无自然运动的数据集）

**核心结论**：新数据集同时具备「场景多样性」和「真实交互设计」，弥补了现有数据集"场景少"或"人类行为假"的短板。

#### 新数据集的四大核心设计（解决上述缺陷）

1. **真实智能体轨迹**：人类有明确目标（每个分配 2 个目标），不是随机乱走，运动更合理，增加人机交互概率

2. **自然人类行为**：
   - **速度**：0.8-1.2 倍机器人速度（模拟人类快慢差异）
   - **交互**：用 **ORCA** 算法实现人类间避碰（不会互相撞）
   - **状态**：运动和休息交替，任务完成后停止（符合人类习惯）

3. **合理人类密度**：按场景面积分组（对应 Fig. 3），避免拥挤或无交互

4. **多样性与扩展性**：
   - 场景多（844+72 个），类型全
   - 不仅支持社交导航（**SocialNav**），还能扩展到"社交目标 / 图像导航"等任务

![](/paper/falcon-dataset-human-distribution.png)

**可视化新数据集的「人类密度合理性」**：

- **横轴**：场景面积分组（<20㎡、20-40㎡、40-80㎡、>80㎡）
- **纵轴**：占比（训练集 / 测试集分开统计）
- **核心逻辑**：面积越小人类越少（<20㎡设 0 人，避免拥挤），面积越大人类越多（>80㎡设 6 人，保证交互），既不会让机器人"没机会练社交"，也不会"堵到动不了"，平衡了交互需求和移动可行性

### Metrics

#### 任务完成度（看"能不能到目标"）

- **成功率（Suc., Success Rate）**：最直接，机器人成功抵达目标的比例
- **路径长度加权成功率（SPL, Success weighted by Path Length）**：成功的前提下，路径越短分数越高（避免绕远路）
- **时间长度加权成功率（STL, Success weighted by Time Length）**：成功的前提下，耗时越短分数越高（避免慢吞吞）

#### 社交规范（看"会不会懂规矩"）

- **人机碰撞率（H-coll, Human Collision Rate）**：机器人和人类碰撞的比例，越低越好
- **个人空间合规性（PSC, Personal Space Compliance）**：机器人与人类距离 ≥ 1.0 米的比例，越高越好（设定依据：人类碰撞半径 0.3m + 机器人 0.25m，加 0.45m 安全余量，确保不冒犯）

### Baseline

#### 规则型算法（按固定逻辑走）

- **A***：经典路径规划，提前算好固定路线，不会变通（动态人类环境易撞）
- **ORCA** [23]：能实时调整路线，但需要"先知"人类的位置和速度（现实中难实现，且易忽略静态障碍）

#### RL 型算法（靠学习优化）

- **Proximity-Aware** [8]：**Falcon** 之前最先进的社交导航方法，只关注"人类当前的距离和方向"，不会预测未来（短期调整易失败）
- **Falcon**：既学决策，又预测人类未来轨迹，兼顾任务和社交

#### 实验设置

- **训练算法**：用 **DD-PPO**，所有 **RL** 模型超参数一致
- **稳定性验证**：每种算法跑 3 次（不同随机种子），结果取均值 + 标准差
- **模型初始化**：用 **PointNav** 预训练权重（先学好基础导航，再练社交），微调 1000 万步
- **硬件配置**：4 块 Nvidia RTX 3090 GPU，8 个并行环境（加速训练）
- **测试方案**：训练集（**Social-HM3D**）→ 测试集（**Social-HM3D** + **Social-MP3D**），后者测"零样本泛化"（没学过的场景也能应对）

### 实验结果

#### （1）定性对比

<div style="display: flex; gap: 10px; justify-content: center;">
  <img src="/paper/falcon-fig4-a.png" alt="Falcon定性对比场景1" style="flex: 1; max-width: 33%;">
  <img src="/paper/falcon-fig4-b.png" alt="Falcon定性对比场景2" style="flex: 1; max-width: 33%;">
  <img src="/paper/falcon-fig4-c.png" alt="Falcon定性对比场景3" style="flex: 1; max-width: 33%;">
</div>

3 个经典场景都赢了：

- **人员跟随**：**A*** 不等人撞了，**Falcon** 安全跟随
- **交叉路口**：**ORCA** 避人却撞静态障碍，**Falcon** 安全通过
- **正面接近**：**Proximity-Aware** 直接横穿撞了，**Falcon** 预判人类路径避开

（颜色含义：绿 = 安全，橙 = 危险，红 = 碰撞）

#### （2）定量对比

| Dataset | Method Type | Method | Suc. ↑ | SPL ↑ | STL ↑ | PSC ↑ | H-Coll ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Social-HM3D** | Rule-Based | A* [60] | 46.14 ± 0.7 | 46.14 ± 0.7 | 46.12 ± 0.7 | 90.56 ± 0.2 | 53.50 ± 0.9 |
| | | ORCA [23] | 38.91 ± 0.1 | 38.91 ± 0.1 | 38.44 ± 0.1 | 90.55 ± 0.4 | 47.52 ± 1.7 |
| | RL | Proximity-Aware [8] | 20.11 ± 1.3 | 18.57 ± 1.9 | 19.51 ± 1.5 | 92.91 ± 0.5 | 33.99 ± 0.7 |
| | | **Falcon** | **55.15 ± 0.6** | **55.15 ± 0.7** | **54.94 ± 0.7** | **89.56 ± 1.4** | **42.96 ± 1.1** |
| **Social-MP3D** | Rule-Based | A* [60] | 43.85 ± 0.3 | 43.85 ± 0.3 | 43.85 ± 0.3 | 86.74 ± 3.4 | 57.94 ± 1.5 |
| | | ORCA [23] | 40.38 ± 0.3 | 40.38 ± 0.3 | 39.51 ± 0.2 | 91.76 ± 0.4 | 47.16 ± 0.2 |
| | RL | Proximity-Aware [8] | 18.45 ± 1.4 | 17.09 ± 2.8 | 16.41 ± 1.5 | 93.37 ± 0.9 | 32.18 ± 3.3 |
| | | **Falcon** | **55.05 ± 0.7** | **55.04 ± 0.6** | **54.80 ± 1.0** | **90.01 ± 1.2** | **42.19 ± 0.9** |

**结果分析**：

- **任务完成**：**Falcon** 在两个数据集上成功率都是 55% 左右（远超其他算法，**A*** 约 43%，**Proximity-Aware** 仅 18%-20%）
- **社交合规**：**PSC** 约 90%（和其他算法接近），**H-coll** 约 42%（比 **A***/**ORCA** 低，仅比 **Proximity-Aware** 略高，但 **Proximity-Aware** 成功率极低）
- **泛化能力**：**Social-MP3D**（未训练过的场景）成功率 55.05%，和 **Social-HM3D** 差不多（说明适配新环境）

#### （3）消融实验

| SPM. Count | SPM. Pos | SPM. Traj | SCP | Suc. ↑ | SPL ↑ | STL ↑ | PSC ↑ | H-Coll ↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PointNav (w/o Aux. Task) | | | | 40.94 | 34.14 | 11.50 | 90.82 | 53.54 |
| ✓ | | | | 51.43 | 51.42 | 51.16 | 90.53 | 46.46 |
| | ✓ | | | 53.17 | 53.17 | 52.95 | 90.06 | 44.07 |
| | | ✓ | | 54.00 | 53.99 | 53.92 | 89.46 | 43.88 |
| | | | ✓ | 51.24 | 51.24 | 51.08 | 90.41 | 48.11 |
| ✓ | ✓ | ✓ | | 53.63 | 53.63 | 53.40 | 89.33 | 44.89 |
| ✓ | ✓ | ✓ | ✓ | **55.15** | **55.15** | **54.94** | **89.56** | **42.96** |

**目的**：搞清楚 **SCP** 和 **SPM** 的重要性

- **baseline（无辅助任务）**：成功率仅 40.94%
- **单独加辅助任务**：轨迹预测（**SPM.Traj**）提升最明显（成功率 54.00%），比人数估计、位置跟踪更有用
- **SPM+SCP 协同**：一起用成功率达 55.15%（最高），且训练收敛更快（图 5：1400K 步前就追上甚至超过单独组件）

#### （4）三大核心发现

1. **未来感知（Falcon）**比静态（**A***）、情境感知（**ORCA**/**Proximity-Aware**）更高效安全
2. 辅助任务里，"未来轨迹预测"是提升性能的关键
3. **SCP** 和 **SPM** 是互补的：**SPM** 让机器人"懂环境"，**SCP** 让机器人"守规矩"，一起用效果才最好

## Limitations
Falcon can achieves high success, while Proximity-Aware, despite low success (∼20%), excels in avoiding collisions. This reveals a limitation in existing metrics, which may prioritize social comfort over task success in crowded environments. Also, our current benchmark does not involve higher-level human behaviors like yielding.
