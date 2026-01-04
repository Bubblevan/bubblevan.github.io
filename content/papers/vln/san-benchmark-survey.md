---
title: "A short methodological review on social robot navigation benchmarking"
---

与其他研究领域不同，科学界尚未就如何对**社交机器人导航**进行基准测试达成共识。这一点尤为重要，因为缺乏一个事实上的**社交机器人导航基准测试标准**可能会阻碍该领域的发展，并可能导致相互矛盾的结论。鉴于这一差距，这篇简短综述，专门聚焦 **2020 年 1 月至 2025 年 7 月**期间的基准测试趋势。通过 **IEEE Xplore** 检索到 **130 篇论文**，对其中符合综述标准的 **85 篇**进行了分析。本综述探讨了文献中用于基准测试的**指标**、此类基准测试中使用的**算法**、**人类调查**在基准测试中的应用，以及在适用情况下如何从基准测试结果中得出结论。

这篇文章组织方式和一般综述还不太一样。有点类似那种工作笔记的样子，没有对每一篇文章像隔壁 [A Survey on Socially Aware Robot Navigation: Taxonomy and Future Challenges](./san-taxonomy-survey) 那样细，我只能说通过它的 **3 个 RQ** 来组织语言：

> 它的 **Introduction** 部分讲的是它是怎么筛文献从 **130** 筛到 **85** 的，所以直接看结果就行。

![](/paper/san-benchmark-survey-sankey-diagram.png)

## RQ1：What metrics and algorithms are used?

在回顾的 **85 篇论文**中，**53 篇（62.4%）** 提供了与第三方算法进行比较的量化指标，**17 篇（20%）** 使用指标报告了量化结果但未与其他算法进行比较，**15 篇（17.6%）** 未提供任何关于导航性能的量化结果（其中一些依赖于人类调查）。总体而言，**66 篇论文（77.6%）** 使用了**非社交指标**，**46 篇（54.1%）** 报告了**社交指标**，**40 篇（47.1%）** 同时使用了这两种类型的指标。

- **77.6%（66/85）** 的研究使用**非社交指标**（如成功率、导航时间）
- **54.1%（46/85）** 的研究使用**社交指标**（如人际距离、空间符合度）
- **47.1%（40/85）** 的研究同时使用两类指标
- **17.6%（15/85）** 的研究未提供任何定量导航结果（部分依赖人类调查）

| Short | Definition | Variable | Paper |
| --- | --- | --- | --- |
| C | Collision. | collision | [146] Akira Shiba et al. "Look Further: Socially-Compliant Navigation System in Residential Buildings" |
| CD | Clearing Distance from the robot to the closest object. | collision | [94] Xiaojun Lu et al. "Group-Aware Robot Navigation in Crowds Using Spatio-Temporal Graph Attention Network With Deep Reinforcement Learning" |
| CE | Collision Energy. | collision | [183] Kai Zhu, Tao Xue, and Tao Zhang. "Confidence-Aware Robust Dynamical Distance Constrained Reinforcement Learning for Social Robot Navigation" |
| CHC | Cumulative Heading Changes. | legibility |  |
| C risk | Estimated risk of collision. | collision | [75] Hasan Kivrak et al. "A multilevel mapping based pedestrian model for social robot navigation tasks in unknown human environments" |
| DA | Deviation angle. | deviation |  |
| DE | Error between the target and actual trajectory. | deviation |  |
| DH min | Minimum Distance to Humans. | comfort | [37] Anthony Francis et al. "Principles and Guidelines for Evaluating Social Robot Navigation Algorithms" |
| ED | End Displacement over a threshold. | deviation |  |
| FDE FL | Final Displacement Error. Instances where a robot follows a group of pedestrians. | comfort | [94] Xiaojun Lu et al. "Group-Aware Robot Navigation in Crowds Using Spatio-Temporal Graph Attention Network With Deep Reinforcement Learning" |
| FR | Freezing Robot. | deviation | [132] Roya Salek Shahrezaie et al. "Advancing Socially-Aware Navigation for Public Spaces" |
| FSC | Full Space Compliance over a trajectory. | success | [183] Kai Zhu, Tao Xue, and Tao Zhang. "Confidence-Aware Robust Dynamical Distance Constrained Reinforcement Learning for Social Robot Navigation" |
| HC | Human Collisions. | comfort | [123] Claudia Perez-D’Arpino et al. "Robot Navigation in Constrained Pedestrian Environments using Reinforcement Learning" |
| IS | Robot’s speed when breaking Space Compliance. | comfort | [43] Mahsa Golchoubian et al. "Uncertainty-Aware DRL for Autonomous Vehicle Crowd Navigation in Shared Space" |
| J | The average change in acceleration per unit time. | legibility | [4] Junaid Ahmed Ansari et al. "Exploring Social Motion Latent Space and Human Awareness for Effective Robot Navigation in Crowded Environments" |
| LV | Linear Velocity. | collision | [69] Kapil Katyal et al. "Learning a Group-Aware Policy for Robot Navigation" |
| ND | Number of Discomfort instances. | speed | [105] Carlos Medina-Sánchez et al. "Human-Aware Navigation in Crowded Environments Using Adaptive Proxemic Area and Group Detection" |
| NPL | Normalised Path Length — ratio between the path’s length and the distance between the start and goal locations. | comfort | [132] Roya Salek Shahrezaie et al. "Advancing Socially-Aware Navigation for Public Spaces" |
| NT | Navigation Time. | time | [123] Claudia Perez-D’Arpino et al. "Robot Navigation in Constrained Pedestrian Environments using Reinforcement Learning" |
| OT | Number of instances where a robot overtakes a group of pedestrians. | comfort | [94] Xiaojun Lu et al. "Group-Aware Robot Navigation in Crowds Using Spatio-Temporal Graph Attention Network With Deep Reinforcement Learning" |
| PA | Average angular deviation between the pedestrians and their direct vector to their goal. | comfort |  |
| PC PIF | Personal Space Cost. Passes in Front of a moving human. | path | [75] Hasan Kivrak et al. "A multilevel mapping based pedestrian model for social robot navigation tasks in unknown human environments"; [17] Yuhang Che, Allison M. Okamura, and Dorsa Sadigh. "Efficient and Trustworthy Social Navigation via Explicit and Implicit Robot-Human Communication" |
| PL | Path Length. | objects | [37] Anthony Francis et al. "Principles and Guidelines for Evaluating Social Robot Navigation Algorithms" |
| PT | Planning Time. | group | [142] Abdulaziz Shamsah et al. "Real-time Model Predictive Control with Zonotope-Based Neural Networks for Bipedal Social Navigation" |
| S | Success. | path | [183] Kai Zhu, Tao Xue, and Tao Zhang. "Confidence-Aware Robust Dynamical Distance Constrained Reinforcement Learning for Social Robot Navigation" |
| SC | Ratio of a trajectory in Space Compliance. | group | [37] Anthony Francis et al. "Principles and Guidelines for Evaluating Social Robot Navigation Algorithms" |
| SPL | Success Weighted using normalised inverse path Length. | obtrusion | [37] Anthony Francis et al. "Principles and Guidelines for Evaluating Social Robot Navigation Algorithms" |
| STL | Success Weighted by Time. |  | [111] Ingrid Navarro et al. "SoRTS: Learned Tree Search for Long Horizon Social Robot Navigation" |
| TO | Timeouts. |  | [123] Claudia Perez-D’Arpino et al. "Robot Navigation in Constrained Pedestrian Environments using Reinforcement Learning" |
| TSC | Time in adhering to Space Compliance. |  | [43] Mahsa Golchoubian et al. "Uncertainty-Aware DRL for Autonomous Vehicle Crowd Navigation in Shared Space" |
| TTC | Estimated Minimum Time to Collision if agents’ speeds remain constant. |  | [11] Kemal Bektas¸ and H Is¸ıl Bozma. "Apf-rl: Safe mapless navigation in unknown environments" |

### 指标分类说明

#### 碰撞相关（安全维度）

- **C（Collision）**：机器人是否发生碰撞（最基础安全指标）
- **C<sub>risk</sub>（Estimated risk of collision）**：预估碰撞风险（提前判断安全隐患）
- **TTC（Estimated Minimum Time to Collision）**：最小碰撞时间（若速度不变，机器人与障碍物/人类碰撞前的时间）
- **HC（Human Collisions）**：机器人与人类的碰撞次数

#### 舒适度相关（社交维度）

- **DH<sub>min</sub>（Minimum Distance to Humans）**：机器人与人类的最小距离（距离越近舒适度越低）
- **SC（Ratio of a trajectory in Space Compliance）**：轨迹符合社交空间规范的比例（如不侵入人类个人空间）
- **PC（Personal Space Cost）**：侵入人类个人空间的量化成本（侵入越久/越近，成本越高）
- **TSC（Time in adhering to Space Compliance）**：符合社交空间规范的时长占比

#### 效率与成功相关（任务维度）

- **S（Success）**：导航任务成功率（如是否到达目标点）
- **NT（Navigation Time）**：导航总耗时（效率核心指标）
- **PL（Path Length）**：实际路径长度（与起点-终点直线距离的比值，越小越高效）
- **SPL（Success Weighted using normalised inverse path Length）**：成功率加权指标（结合"成功"与"路径效率"）

#### 其他关键维度

- **FR（Freezing Robot）**：机器人"冻结"次数（无运动响应的故障指标）
- **NPL（Normalised Path Length）**：归一化路径长度（路径效率的标准化指标）
- **TO（Timeouts）**：导航超时次数（任务失败的一种情况）

### 主要发现

#### 指标使用情况

**85 篇论文**中，有 **38 篇**没有使用任何**社交导航指标**。我猜它们都是直接上实机部署去了。

**4 个最常见的社交指标**是 **DH<sub>min</sub>**、**SC**、**PC** 和 **C<sub>risk</sub>**。**4 个最受欢迎的非社交指标**是 **S**、**T**、**C** 和 **PL**。作者在做出选择时，经常提到这些指标很受欢迎，或者能很好地涵盖各种属性，不过有 **52.2%** 的作者没有给出理由。

大多数论文选择如 **PL** 或 **T** 这样的**单一指标**，而非 **SPL** 或 **STL** 等**加权指标**，这与我们的预期相悖。这种"重形式轻本质"的指标偏好可能导致算法"偏科"（如成功率高但舒适度低）。

#### 算法基准使用情况

**基准测试中最常用的基线算法**是 **ORCA**[163]、**DWA**[36]、**SFM**[50]、**CADRL**[21]、**SARL**[19]、**CrowdNav**[89] 和 **LSTM-RL**[31]。其中仅 **CrowdNav** 是 **2020 年后**提出的新基准，而其他算法多为 **2017 年前**提出（如 **ORCA**、**SFM**）。作者在说明选择这些算法的原因时，经常提到它们的普及性、最先进的地位以及这些基线是他们正在改进的方法——不过有 **35.8%** 的论文没有给出任何说明。

### 启示与未来方向

#### 1. 算法基准需"更新迭代"与"统一化"

领域算法基准更新滞后，常用算法多为 **2017 年前**提出，**2020 后**仅 **CrowdNav** 成为新基准，导致不同研究的对比缺乏时效性。**未来研究应**：

- 推动新算法（如基于 **Transformer**、强化学习的模型）成为基准
- 建立"核心基准算法库"，明确版本与配置参数（如 **DWA** 的避障阈值），减少对比偏差

#### 2. 研究透明度需显著提升

超过 **1/3** 的研究未说明算法选择理由，指标选择的主观性强，导致结果难以复现与横向对比。**未来研究应**遵循"明确化报告原则"：

- 标注指标定义、算法参数，而非仅提及"**ROS** 导航栈"等模糊框架
- 明确说明指标选择逻辑（如"平衡安全与效率"）

#### 3. 避免"重形式轻本质"的指标偏好

多数研究选择单一指标而非加权指标，可能导致算法"偏科"。**未来研究应**：

- 优先采用"**社交 + 非社交**"组合指标并明确说明选择逻辑
- 鼓励使用加权指标（如 **SPL** 结合成功率与路径效率），更能反映 **SocNav** 的复杂性
- 公开权重确定依据（如通过人类调查校准）

## RQ2：How frequent are surveys involving human raters?

### 调查应用情况

在 **85 篇论文**中，有 **16 篇（18.9%）** 开展了**基于人类的现场调查**（让人类被试评估机器人导航表现，如舒适度、安全性），剩余 **81.1%** 的研究未采用任何人类主观评估，仅依赖定量指标（如碰撞次数、导航时间）。

在 **16 篇**开展调查的论文中，仅有 **6 篇（占总论文数的 7.1%）** 在调查中纳入了**第三方基准算法**（如 **ORCA**、**CrowdNav**）进行对比[94, 172, 115, 126, 52, 150]，其余 **10 篇**仅评估自身提出的算法，无法客观验证自身算法的"社交接受度优势"。

| 问题类型 | 论文 |
| --- | --- |
| **Abruptness of the robot movement**（机器人运动的突兀感） | [108] Margot M.E. Neggers et al. "Effect of Robot Gazing Behavior on Human Comfort and Robot Predictability in Navigation" |
| **Anxiety caused by the robot**（机器人带来的焦虑感） | [83] Alexis Linard et al. "Real-Time RRT* with Signal Temporal Logic Preferences" |
| **Comfort or compliance**（舒适度/合规性） | [37] Anthony Francis et al. "Principles and Guidelines for Evaluating Social Robot Navigation Algorithms" |
| **Adequacy of the perceived robot distance**（感知距离的合理性） | [83] Alexis Linard et al. "Real-Time RRT* with Signal Temporal Logic Preferences" |
| **Awareness and movement adequacy w.r.t. groups**（对人群的关注程度） | [94] Xiaojun Lu et al. "Group-Aware Robot Navigation in Crowds Using Spatio-Temporal Graph Attention Network With Deep Reinforcement Learning" |
| **Overall understanding of the robot's goals**（机器人目标的可理解性） | [152] Ada V. Taylor, Ellie Mamantov, and Henny Admoni. "Observer-Aware Legibility for Social Navigation" |
| **Likeability and friendliness**（友好度） | [74] Ryo Kitagawa, Yuyi Liu, and Takayuki Kanda. "Human-inspired Motion Planning for Omnidirectional Social Robots" |
| **Naturalness and smoothness**（自然度和流畅度） | [78] Thibault Kruse et al. "Human-aware robot navigation: A survey" |
| **Overall navigation skills**（整体导航技能评价） | [108] Margot M.E. Neggers et al. "Effect of Robot Gazing Behavior on Human Comfort and Robot Predictability in Navigation" |
| **A robot's movement is easy to predict**（运动的可预测性） | [108] Margot M.E. Neggers et al. "Effect of Robot Gazing Behavior on Human Comfort and Robot Predictability in Navigation" |
| **Perception of safety and risk**（安全与风险感知） | [37] Anthony Francis et al. "Principles and Guidelines for Evaluating Social Robot Navigation Algorithms" |
| **Adequacy of the robot's speed**（机器人速度的合理性） | [83] Alexis Linard et al. "Real-Time RRT* with Signal Temporal Logic Preferences" |
| **Politeness and care about pedestrians**（礼貌性） | [37] Anthony Francis et al. "Principles and Guidelines for Evaluating Social Robot Navigation Algorithms" |
| **The user's trust in the robot**（对机器人的信任度） | [17] Yuhang Che, Allison M. Okamura, and Dorsa Sadigh. "Efficient and Trustworthy Social Navigation via Explicit and Implicit Robot-Human Communication" |
| **Unobtrusiveness**（无干扰性/不打扰程度） | [52] Noriaki Hirose et al. "SACSoN: Scalable Autonomous Control for Social Navigation" |

### 调查核心关注变量

人类调查的核心问题集中在 **15 类变量**，高频项包括：

- **舒适度/社交合规性**（Comfort or compliance）
- **安全性/风险感知**（Perception of safety and risk）
- **运动自然度/平滑度**（Naturalness and smoothness）
- **对机器人的信任度**（The user's trust in the robot）
- **目标可理解性**（Overall understanding of the robot's goals）
- **速度合理性**（Adequacy of the robot's speed）
- **礼貌性**（Politeness and care about pedestrians）

#### 问题分类

- **感受类**：机器人运动的突兀感、带来的焦虑感、舒适度/合规性、友好度
- **认知类**：机器人目标的可理解性、运动的可预测性、整体导航技能评价
- **社交类**：感知距离的合理性、对人群的关注程度（礼貌性）、不打扰程度（无干扰性）
- **信任类**：对机器人的信任度、安全与风险感知

### 启示与未来方向

#### 1. 主观评估应回归 SocNav 核心定位

现状中仅 **18.9%** 的研究采用人类调查，反映出领域"重定量、轻主观"的倾向，但 **SocNav** 的核心是"在人类环境中保障安全与舒适"，人类的真实感受（如是否觉得"突兀""可信任"）无法通过定量指标完全替代。

**未来研究应**：

- 将人类主观评估作为"必选项"而非"可选项"
- 尤其针对服务机器人、医疗机器人等直接与人交互的场景，需将"人类接受度"与"效率指标"并重

#### 2. 调查设计需强化"对比性"与"标准化"

仅 **7.1%** 的调查纳入第三方算法，导致"自身算法更友好"的结论缺乏说服力（如无对比则无法证明优于主流基准）。

**未来研究应**：

- 制定"人类调查基准流程"，要求调查需至少包含 **2-3 个**主流算法（如 **ORCA**、**CrowdNav**）作为对照
- 统一评估量表（如采用 **1-7 分**量表衡量舒适度），减少"不同研究量表不同导致结果不可比"的问题

#### 3. 降低实地调查成本，扩大样本覆盖

实地调查的高时间/运营成本是其使用率低的关键原因。

**未来研究应**：

- 结合虚拟仿真工具（如 **SocialGym**、**HuNavSim**）开展"虚拟人类调查"——让被试在仿真环境中观察不同算法的机器人导航表现并评分
- 既降低成本，又能快速扩大样本量（如覆盖不同年龄、职业的被试），提升评估的普适性

#### 4. 聚焦"关键社交变量"，避免调查冗余

现有调查变量虽多，但核心集中在"舒适度、安全性、信任度、可预测性"四类。

**未来研究应**：

- 优先围绕这四类核心变量设计调查问题，减少冗余（如无需重复询问"运动是否自然"与"是否突兀"）
- 增加"场景特异性变量"（如拥挤环境下的"不打扰程度"、狭窄空间的"礼貌避让感受"），让评估更贴合实际应用场景

## RQ3：How are benchmarking results interpreted?

### 性能声称与证据匹配度

在 **85 篇论文**中，**26 篇**声称"性能优于基准算法"，但证据支持不足：

- **22 篇（84.6%）** 仅使用 **≤2 个指标**或 **≤2 个对比算法**，其中 **3 篇（11.5%）** 仅依赖 **1 个指标**（如仅用"成功率"判定最优）
- **5 篇（19.2%）** 采用"单算法 + 多指标"的合理验证方式（可证明优于特定算法，但无法等同于 **SOTA**）
- **3 篇（11.5%）** 的性能声称无任何证据支持（如指标冲突却未解释）

### 声称类型分布

- **26 篇（30.6%）** 声称"性能优于基准算法"
- **14 篇（16.5%）** 声称"部分优势"，即性能依赖具体指标或场景（如低人群密度下高效，高密度下舒适度一般）
- **3 篇（3.5%）** 声称"与 **SOTA** 相当"（未超越但无明显劣势）
- **10 篇（11.8%）** 未做任何性能优势声称，仅提供定性描述（如"算法在复杂场景下表现稳定"）

### 指标平衡的共识

**32.7%（28/85）** 的论文直接或间接承认"难以在所有指标上达到最优"，多数论文选择"聚焦部分指标"得出结论，部分研究明确提出"社交指标（如舒适度）比效率指标（如导航时间 **T**）更重要"，优先保障人机交互的友好性。

### 启示与未来方向

#### 1. 结果解读需坚持"多维度验证"，避免单一维度偏见

现状中 **84.6%** 的优势声称依赖少量指标/算法，导致结论片面（如"成功率高但舒适度差"却宣称最优）。

**未来研究应**：

- 采用"多指标 + 多算法 + 多场景"的验证框架
- 至少包含 **2 类核心指标**（社交 + 非社交）、**3 个主流基准算法**（如 **ORCA**、**CrowdNav**、**CADRL**）
- 覆盖不同人群密度、空间大小等场景，避免"以偏概全"

#### 2. 强化结果解读的"透明化与严谨性"

**3 篇论文**存在"无证据声称"，反映出部分研究缺乏学术严谨性。

**未来研究应**：

- 建立"结果解读报告规范"——明确说明"每个性能结论对应的指标/算法/场景"
- 公开原始数据（如各指标具体数值、算法对比细节）
- 若指标冲突（如效率高但社交合规性低），需解释决策优先级（如"针对服务机器人场景，优先保障舒适度"）

#### 3. 明确指标优先级，避免"全优陷阱"

**32.7%** 的论文承认"无法平衡所有指标"，但多数未明确优先级。

**未来研究应**：

- 提前根据应用场景定义指标权重——例如医疗机器人优先"安全性（**C<sub>risk</sub>**）+ 舒适度（**DH<sub>min</sub>**）"，物流机器人优先"效率（**T**）+ 成功率（**S**）"
- 在论文中说明权重确定依据（如基于人类调查或场景需求分析），而非模糊宣称"整体最优"

#### 4. 重视"社交指标"在解读中的权重

部分研究因"社交指标难以量化"而侧重效率指标，导致算法"高效但不友好"。

**未来研究应**：

- 解读结果时需将"社交属性"作为核心维度
- 即使效率指标（如导航时间）略逊于基准，若社交指标（如空间符合度 **SC**、个人空间成本 **PC**）显著更优，仍可判定为"场景适配性更优"
- 尤其针对服务机器人、公共空间导航等核心应用场景

