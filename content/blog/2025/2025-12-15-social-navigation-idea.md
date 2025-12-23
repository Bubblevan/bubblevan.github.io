---
date: 2025-12-15
title: Social Navigation Idea
authors: [bubblevan]
tags: [navigation, falcon, vlm, survey]
---

## 自问自答

在接触 LOVON 这类开放词汇物体导航工作时，发现它们对语义的理解停留在 YOLO 层面，追目标时避障效果很差。当时考虑过用边走边建图的 3D 重建方式，但看到 social navigation 后就搁置了。这里有两个问题值得深入思考。

### 问题一：Social Navigation 需要 3D 重建吗？

在 Social Navigation 领域，做显式 3D 重建是一条歧路。这个结论需要从 ObjectNav 和 SocialNav 的本质区别说起。

ObjectNav 的核心难点是记忆。机器人需要记住"我去过厨房没？那个杯子在哪？"这类问题。这里用 3D 建图（如语义地图）是有用的，因为它解决的是静态环境的探索与回溯。LOVON 避障差，通常是因为它是模块化的（YOLO 指方向，然后 Planner 走），尽管利用了 LLM 进行 NER 分解，这也算是一种传统 Planner，对近距离动态避障很弱。

但 SocialNav 的核心难点是动态性。人是会动的。如果做 3D 重建（TSDF Fusion、NeRF-SLAM 等），会面临严重的鬼影问题。一个人从左走到右，3D 地图上会留下一串残影，不仅不能辅助导航，反而会变成一堆不存在的障碍物墙，把路堵死。

Falcon、Rank 1、Rank 2 的成功证明了：处理动态环境，需要的是第一视角感知（Egocentric Perception）加上时序记忆（RNN/Transformer），而不是全局静态地图。

关于"避障不行"的问题，之前遇到的 YOLO 检测到了但还是撞上去的情况，正是端到端强化学习（SocialNav）试图解决的。关键是把"识别"和"运动控制"分开。SocialNav 的方法（如 Falcon）是把深度/RGB 直接映射到动作。如果智能体撞了，它会直接受到惩罚。这比"YOLO 告诉 Planner 有人，Planner 计算路径"的链路反应更快，且更能处理复杂交互。

### 问题二：Depth Anything V3 是合适的"新锤子"吗？

用目标驱动研究的标准来评估这个"锤子"，会发现两种截然不同的使用方式。

**工程思维（不推荐）**：把 Falcon 输入端的深度传感器换成 Depth Anything V3 生成的深度。问题在于，在仿真器（如 Habitat）里，已经有了完美深度（Ground Truth Depth）。Depth Anything V3 生成的深度再好，也不可能比仿真器自带的完美深度更好。结果可能是性能下降（因为引入了推理延迟和误差），且没有任何创新性。

**科研思维（推荐）**：Depth Anything V3 的真正价值在于"仿真到现实的鸿沟"或"语义感知"。

第一个方向是鲁棒性/仿真到现实。SocialNav 在仿真里跑得好，是因为仿真里的深度是完美的。真实世界的深度传感器（Realsense/LiDAR）有噪声、有盲区（玻璃、强光）。Depth Anything V3 是一个鲁棒感知探针，它是从大量真实图片训练出来的，对真实世界的噪声有极强的鲁棒性。可以提出一个框架，证明在仿真里使用 Depth Anything V3 提取的特征（而非原始深度），能够让智能体在零样本迁移到真实世界时表现得更好，因为它学到的是通用的深度特征，而不是仿真特定的几何特征。

第二个方向是隐式语义引导（更高级的）。Depth Anything 不仅仅是深度，它其实是基础模型。为了估计深度，它必须"理解"物体是什么（比如理解这块平滑的像素是墙而不是空洞）。利用 Depth Anything V3 的编码器特征作为 SocialNav 的额外输入，它的特征里不仅包含距离，还隐式包含了物体语义。这可能解决 Falcon"把人当圆柱体"的问题，让智能体能区分"人"和"人形雕塑"，或者区分"柔软的窗帘"和"坚硬的墙"。

Falcon（基线）和 Rank 2 都依赖几何信息（位置、速度、距离）来判断风险。但有些情况仅靠深度和坐标无法区分：一个人站着不动是在玩手机（不会突然动），还是在等人（可能会突然拥抱）？一个人跑过来是冲着我来的（攻击性），还是只是路过（中性）？

科学的做法是：不要用 Depth Anything V3 做深度，用它（或者 VLM 如 CLIP/SigLIP）做视觉语义特征提取。参考 Rank 2 的架构，加一个辅助模块，但不是预测"风险分数"，而是预测"社会意图"或"语义状态"。

为什么这样做有效？Rank 1 证明了数据重要，可以利用基础模型里的海量数据。Rank 2 证明了显式预测隐变量重要，可以预测比风险更高级的意图。


## Literature Review

在 Google Scholar 里检索引用了 Falcon 的工作，整理如下：

| 序号 | 论文标题 | 中稿状态 | 主要功能 | 核心内容 |
|------|---------|---------|---------|---------|
| 1 | Seeground: See and ground for zero-shot open-vocabulary 3d visual grounding | 已中稿 CVPR 2025 | 解决零样本开放词汇的 3D 视觉定位问题，即根据自然语言描述在 3D 场景中找到特定物体 | 提出 SeeGround 方法，无需针对 3D 数据进行专门训练。核心思想是将 3D 场景转化为 2D VLM 可理解的格式，通过渲染 3D 场景图像并使用视觉提示技术建立 2D 图像与 3D 空间信息的对应关系，利用预训练的 2D VLM 理解场景并定位物体 |
| 2 | Team Xiaomi EV-AD VLA: Caption-Guided Retrieval System for Cross-Modal Drone Navigation | IROS 2025 RoboSense Challenge (Track 4) 技术报告，Top-2 | 解决跨模态无人机导航中的图像检索问题，即根据自然语言描述从大规模数据库中检索对应的无人机视角图像 | 提出 CGRS 两阶段检索增强框架：第一阶段使用基线模型进行粗略排序；第二阶段利用 VLM 为候选图像生成详细描述，计算查询文本与生成描述的相似度进行精细重排序，显著提高检索精度 |
| 3 | Zero-Shot 3D Visual Grounding from Vision-Language Models | arXiv Preprint (arXiv:2505.22429) | 零样本 3D 视觉定位 | 从作者和题目看，极大概率是 Seeground (CVPR 2025) 的预印本或其前身，内容与 Seeground 一致，探讨如何利用 VLM 实现零样本 3D 视觉定位 |
| 4 | Learning to Navigate Socially Through Proactive Risk Perception | IROS 2025 RoboSense Challenge (Social Navigation Track) 技术报告，第 2 名 | 解决社会导航问题，让机器人在人群密集的动态环境中安全、合乎社会规范地导航 | 基于 Falcon 模型改进，增加主动风险感知模块，能够预测周围行人的基于距离的碰撞风险分数，让机器人具备更强的空间感知能力，主动采取避障行为并保持合适的社交距离 |
| 5 | Stairway to Success: Zero-Shot Floor-Aware Object-Goal Navigation via LLM-Driven Coarse-to-Fine Exploration | arXiv Preprint | 解决多楼层环境下的零样本物体目标导航 | 提出 ASCENT 框架，结合多楼层空间抽象和基于 LLM 的由粗到细的边界探索，利用 LLM 的常识推理能力（如"瑜伽垫可能在健身房，而健身房在楼下"）指导机器人跨楼层搜索 |
| 6 | SocialNav-Map: Dynamic Mapping with Human Trajectory Prediction for Zero-Shot Social Navigation | arXiv Preprint | 零样本社会导航 | 提出 SocialNav-Map 框架，结合动态人类轨迹预测和占据栅格地图。不需要针对特定环境训练，使用两种互补方法预测人类轨迹（基于历史路径和基于朝向），将预测结果作为动态障碍物整合进地图，使机器人能预见人的移动并提前规划路径 |
| 7 | View-on-Graph: Zero-shot 3D Visual Grounding via Vision-Language Reasoning on Scene Graphs | arXiv Preprint | 零样本 3D 视觉定位 | 提出 VoG 方法，不同于直接把图像喂给模型，该方法将 3D 场景构建为多模态、多层级的场景图。VLM 被设计为主动代理，在图上进行遍历和推理，逐步搜索并定位目标物体，这种结构化方式降低了推理难度，提高了可解释性 |
| 8 | RLSLM: A Hybrid Reinforcement Learning Framework Aligning Rule-Based Social Locomotion Model with Human Social Norms | arXiv Preprint | 社会导航，强调符合人类社会规范的舒适度 | 提出 RLSLM 混合强化学习框架，将心理学实验推导出的规则基社会运动模型整合到 RL 的奖励函数中，让 RL 智能体在学习导航策略时天生倾向于遵守人类的社交舒适区，实现规则可解释性与 RL 适应性的结合 |
| 9 | Comfort-Aware Trajectory Optimization for Immersive Human-Robot Interaction | 已发表于 IEEE Open Journal on Immersive Displays (2025) | 针对沉浸式环境（如 VR）中的人机交互，优化机器人运动轨迹 | 提出轨迹预测与优化框架，专门针对舒适度和路径合理性进行优化。在 VR 环境中进行用户研究，证明该方法生成的轨迹比传统方法更自然、更让用户感到舒适 |
| 10 | Where to Fuse in the VLM Era: A Survey on Integrating Knowledge into Object Goal Navigation | Workshop Paper，发表于 HEAI Workshop | 综述 | 探讨在物体目标导航任务中应该在"哪里"融合 VLM/LLM 的知识。借鉴自动驾驶的感知-预测-规划范式，将现有工作分类为在感知层融合、在预测层融合或在规划层融合，并分析各类优缺点 |
| 11 | Layout-Robust LiDAR 3D Object Detection via Multi-Representation Fusion | IROS 2025 RoboSense Challenge (Track 5) 技术报告/预印本 | 解决跨不同车辆平台的 LiDAR 3D 目标检测问题 | 针对不同车辆上 LiDAR 传感器布局（位置、数量、角度）不同导致模型泛化能力差的问题，提出统一表示框架，包含多视图融合模块（通过点-体素注意力机制学习统一视图不变表示）和运动引导的时空融合模块 |
| 12 | Enhancing Multi-View Driving VLMs via Pseudo-Label Pretraining and Long-Tail Balancing | IROS 2025 RoboSense Challenge (Track 1) 技术报告/预印本 | 提升视觉语言模型在自动驾驶场景中的理解能力（感知、预测、规划） | 基于 InternVL3-8B 模型提出两阶段优化框架：第一阶段利用伪标签预训练，结合思维链推理，将多视角图像按固定序列拼接；第二阶段针对长尾数据进行平衡处理，结合官方数据与合成数据进行混合微调，通过模型集成提升鲁棒性 |
| 13 | Robust 3D Object Detection under Sensor Placement Variability | IROS 2025 RoboSense Challenge (Track 5) 技术报告/预印本 | 增强 3D 目标检测模型对传感器安装位置变化的鲁棒性 | 针对不同车型 LiDAR 安装位置差异大导致模型失效的问题，提出三种策略集成：时序增强（聚合连续 LiDAR 扫描帧以丰富几何信息）、混合位置训练（在训练中模拟多种传感器配置）、推理时增强。在 Track 5 基准测试中表现出色 |
| 14 | Enhancing VLMs for Autonomous Driving through Task-Specific Prompting and Spatial Reasoning | IROS 2025 RoboSense Challenge (Track 1) 技术报告 | 解决 VLM 在自动驾驶中空间推理弱和多任务干扰的问题 | 提出系统解决方案，核心是任务特定的提示。Prompt Routing：根据问题类型（感知、预测、规划等）将问题路由到专门的 expert prompt。空间推理增强：显式定义多视图坐标系和领域约束（如"后视摄像头的物体一定在车后"），帮助 VLM 理解空间关系。在 Track 1 的 Phase-1 和 Phase-2 中均取得很高准确率（70%+） |
| 15 | Towards Socially Compliant Navigation: Hybrid Parameter Optimization for Falcon in Dynamic Environments | IROS 2025 RoboSense Challenge (Social Navigation Track) 技术报告/预印本 | 优化社会导航模型 Falcon 的参数，使其更符合社会规范 | 针对 Falcon 模型在平衡"任务效率"和"遵守社会规范"之间的矛盾，提出混合参数优化策略，结合比例约束的参数耦合和网格搜索，解决奖励函数参数过多导致的维度爆炸问题，更有效地找到让机器人既跑得快又懂礼貌的参数组合 |
| 16 | HCCM: Hierarchical Cross-Granularity Contrastive and Matching Learning for Cross-Modal Drone Navigation | IROS 2025 RoboSense Challenge (Track 4) 技术报告/预印本 | 解决无人机跨模态导航中的定位匹配问题 | 针对无人机视角（俯视、广角）与文本描述之间的巨大差异，提出 HCCM 框架，核心在于分层和跨粒度。不仅做整体图像匹配，还将图像和文本分解为不同层级（如全局场景 vs. 局部地标），在不同粒度上进行对比学习和匹配，提高在大范围航拍图像中定位具体目标的准确性 |
| 17 | Unsupervised Domain Adaptation for 3D Object Detection via Adversarial Learning | IROS 2025 RoboSense Challenge (Track 5) 技术报告 | 解决跨平台 3D 目标检测的域适应问题 | 针对源域和目标域 LiDAR 配置不同导致的数据分布差异，采用无监督域适应方法，核心引入对抗学习。通过训练域判别器区分特征来自哪个平台，同时强制特征提取器欺骗判别器，提取平台无关特征，使模型能泛化到新车型上 |
| 18 | Towards Cross-Platform Generalization: Domain Adaptive 3D Detection with Augmentation and Pseudo-Labeling | IROS 2025 RoboSense Challenge (Track 5) 获奖方案 | 高效的跨平台 3D 检测 | 基于强力的 PVRCNN++ 基线模型，使用两项关键技术弥补域差异：强数据增强（在数据层面模拟不同传感器噪声和几何变换）和伪标签（使用模型在未标注目标域数据上生成的置信度高的预测结果作为伪标签进行自我训练，逐步适应新环境） |
| 19 | Task Aware Prompt Routing and CoT Augmented Fine Tuning for Driving VQA | IROS 2025 RoboSense Challenge (Track 1) 技术报告 | 提升自动驾驶 VLM 处理复杂问答（感知、预测、规划）的能力 | 提出任务感知提示路由：不使用通用提示，先判断问题属于哪类任务（如"前方有车吗？"属感知，"它会左转吗？"属预测），然后路由到专门优化的 Prompt 模板。思维链增强微调：在微调过程中加入推理步骤，强迫模型在给出结论前先生成推理过程，显著提升复杂逻辑问题的回答准确率 |
| 20 | Driving Robustly through Corruptions: Multi-Source LoRA Fine-Tuning of Driving VLMs for Multi-View Reasoning | IROS 2025 RoboSense Challenge (Track 1) 技术报告 | 增强 VLM 对图像腐蚀/干扰的鲁棒性 | 针对雨雪雾、传感器噪声等恶劣视觉条件，采用 Multi-Source LoRA 微调策略。在训练时故意引入多种类型的图像腐蚀数据作为多源输入，通过轻量级 LoRA 模块让大模型快速适应这些低质量输入，保证在视觉条件退化时仍能安全推理 |
| 21 | SegSy3D: Segmentation-Guided Self-Training and Model Synergy for Cross-Platform 3D Detection | IROS 2025 RoboSense Challenge (Track 5) 技术报告 | 利用语义信息辅助跨平台 3D 检测 | 分割引导：认为仅仅做检测不够，利用点云的语义分割任务作为辅助，帮助模型更好地理解物体形状和背景，从而提升检测器的特征质量。模型协同：涉及多个模型（如分割模型和检测模型）之间的互助学习或集成，以克服单一模型的偏差 |
| 22 | Towards Generalizable 3D Object Detection Across Sensor Placements | IROS 2025 RoboSense Challenge (Track 5) 技术报告 | 解决 LiDAR 安装位置变化带来的检测失效问题 | 重点研究当 LiDAR 安装高度、俯仰角发生变化时点云分布的改变，提出通用检测框架，可能包含几何校正模块，或在特征空间进行视角对齐，确保无论雷达装在车顶还是车头，提取出的车辆特征是一致的 |
| 23 | PlaceRecover: A Transformer-based Point Cloud Recovery Network with Implicit Neural Representations for Robust LiDAR Placement Adaptation | IROS 2025 RoboSense Challenge (Track 5) 技术报告 | 通过重建/恢复点云来解决传感器位置差异问题 | 独特思路：不同于调整检测器，试图直接调整数据。PlaceRecover 是基于 Transformer 的网络，结合隐式神经表示，目标是将不同位置采集的畸变点云恢复/重构为标准视角下的点云，这样后续检测模型不需要修改，直接在恢复后的标准点云上运行即可 |
| 24 | A Parameter-Efficient MoE Framework for Cross-Modal Drone Navigation | IROS 2025 RoboSense Challenge (Track 4) 冠军方案 | 高效、高精度的无人机跨模态检索与导航 | 引入混合专家模型架构，MoE 允许模型拥有巨大参数量但推理计算量很小（每次只激活部分专家）。在无人机导航任务中，不同专家可能分别负责处理文本理解、视觉特征提取或地理空间推理。参数高效通常意味着使用 Adapter 或 LoRA 等技术，使模型在有限算力下快速适应新任务 |
| 25 | Robust 3D Object Detection via Physical-Aware Augmentation and Class-Specific Model Ensembling | IROS 2025 RoboSense Challenge (Track 5) 技术报告 | 通过物理感知增强和集成学习提升检测鲁棒性 | 物理感知增强：传统复制粘贴增强可能把车放在天上或穿墙，该方法设计符合物理规律的增强策略（如贴地、防碰撞），生成更逼真的训练样本。类别特定模型集成：针对不同类别（如车、人、骑行者）训练专门检测器，最后进行集成，利用不同模型在不同类别上的优势，最大化整体分数 |

除了上述文献，RoboSense 2025 Track 2 的两篇冠亚军方案也值得关注。它们的改进思路截然不同：一个改了模型架构，另一个改了训练策略。这种对比很有意思，展现了同一个问题可以从不同角度切入。


亚军方案来自小米的工作，核心思路是**"预知不够，还需要风险评估"**。这个洞察很有意思。

Falcon 虽然能预测人类未来的轨迹，但它对危险的感知是滞后的。Falcon 主要靠碰撞后的惩罚来学习，这导致智能体知道人要去哪，但不知道**"离得近有多危险"**。就像一个人能预测另一个人会走到哪里，但不知道保持多远的距离才安全。

为了解决这个问题，研究者在 Falcon 的架构上增加了一个**主动风险感知模块**。这是一个轻量级的神经网络，利用共享的隐层状态，显式地预测周围每个人类的碰撞风险分数。它把风险分成了三个等级：**Safe、Warning、Danger**。

这个模块的贡献在于将**隐式的避障逻辑变成了显式的风险监督信号**。智能体在还没撞上之前，就学会了"这种距离是不舒服的"，从而更早地进行微调。这种从隐式到显式的转变，让模型的行为更加可解释，也更容易调试。
---

冠军方案来自 Zhang 等人的 PER-Falcon，核心思路是**"模型不需要动，是数据利用效率太低"**。这个角度很独特，大多数工作都在改模型，但这个方法选择改训练策略。

在强化学习训练社会导航时，大部分回合都是失败的，要么撞人，要么超时。成功的回合非常稀缺且珍贵，包含了完美的绕行和避让操作。Falcon 在训练时对所有数据一视同仁，导致智能体学了一堆"怎么死"，却没学够"怎么活"。

PER-Falcon 引入了**正样本回放机制**。这是一种数据为中心的方法：把那些回报大于 10 的回合（即成功到达且避障良好）存到一个专门的缓冲区里。每隔一段时间，把这些"满分作业"拿出来让智能体再复习一遍，通过辅助的 PPO 更新来强化这些好的行为。

这个方法的贡献在于证明了在社会导航中，**强化好的行为比单纯修补坏的行为更有效**。这其实是一个训练技巧，但效果极好，提升了 7 个百分点。有时候，简单的方法反而最有效，关键是要找到问题的本质。

| 特征 | Rank 2 (Risk Perception) | Rank 1 (PER-Falcon) |
|------|-------------------------|---------------------|
| **改进维度** | Perception / Loss Design (感知/损失函数) | Data Efficiency / Optimization (数据效率/优化) |
| **核心逻辑** | 把"危险"显式量化，作为辅助监督信号 | 把"成功经验"加权，避免被噪音数据淹没 |
| **新增参数量** | 极小 (两层 MLP) | 0 (仅改变训练流程) |
| **性能** | SR 0.656, H-Coll 0.33 | SR 0.660, H-Coll 0.32 |
| **借鉴点** | 引入 Dense Signal 辅助 RL 训练 | 在 World Model 训练中进行数据筛选 (Data Curation) |

### Paper List

基于上述分析，可以梳理出两类值得深入阅读的论文。第一类是直接处理社会导航核心问题的论文，第二类是可以作为方法论迁移的"新锤子"。

**直接相关的必读论文**主要解决如何在人群中导航的核心问题。**SocialNav-Map** 是一个很好的基线或对比对象，它尝试把"预测"显式地画在地图上（Occupancy Map），而 Falcon 是隐式编码在特征里。对比这两者的优劣是很好的讨论点。

**RLSLM** 试图将基于规则的社会力模型的可解释性融合进强化学习。这直接关联到 Falcon 缺乏显式社会规范的问题。

**Towards Socially Compliant Navigation** 是针对 Falcon 的超参数调优。虽然技术含量可能不高，但它揭示了奖励函数设计的敏感性。

**Comfort-Aware Trajectory Optimization** 关注"舒适度"指标。如果目标是 Level 5（社会智能导航），这篇论文定义的指标可能比单纯的成功率更有用。

**方法论迁移的选读论文**虽然不在 SocialNav 领域，但其中的技术（VLM、Visual Grounding）正是需要的"新锤子"。

**Seeground / Zero-Shot 3D Visual Grounding** 是极其重要的"新锤子"来源。如果想做语义社会导航，需要这篇论文的方法：如何把 3D 场景转化为 2D VLM 能理解的 Prompt。可以把它的"物体定位"任务替换为"社会规范定位"任务。

**Where to Fuse in the VLM Era** 是一本"操作手册"。当决定引入 VLM 时，这篇综述告诉应该把它放在感知层（用来理解人）、预测层（用来预测意图）还是规划层（用来写代码）。

**Enhancing VLMs for Autonomous Driving** 虽然是自动驾驶（室外），但它处理思维链（Chain of Thought）和空间推理的 Prompt Engineering 技巧，完全可以迁移到室内 SocialNav。例如："那个人在看手机 -> 所以他不会让路 -> 我应该从左边绕"。



Top 2 的方法依然在**几何空间（距离、坐标）**和**RL 优化（Loss、Replay）**里打转。它们都没有解决**语义理解（Semantic Understanding）**和**显式博弈（Explicit Negotiation）**。这正是未来研究的机会所在。

### After

读完这 7 篇论文后，可以清晰地看到当前社会导航领域的图景。目前正在见证一场**"分裂"**：一边在优化几何强化学习范式（从深度传感器和 PPO 中榨取性能），另一边则倡导结构化/混合方法（地图、规则和 VLM）来绕过纯强化学习的低效。

这个文献图谱的中心节点是 **Falcon**，它通过将范式从反应式避障转向预测式轨迹规划，建立了一个强基线。

**Falcon（基础）**提出了"未来感知"框架。它不再仅仅对当前人类位置做出反应，而是使用辅助任务显式预测人类轨迹（未来 $H$ 步），并惩罚机器人阻塞这些未来路径。关键指标是在 Social-HM3D 上达到了 55% 的成功率。但它的弱点是依赖"盲目"的端到端强化学习，需要大量训练（约 2400 GPU 小时），并且将人类视为简单的移动障碍物，缺乏语义上下文。

有三篇论文接受 Falcon 的架构，但认为其训练方法有缺陷。它们旨在解决样本效率和奖励稀疏性问题。

**数据效率（"好学生"方法）**：PER-Falcon（Rank 1）发现 Falcon 通过平等对待所有训练回合而浪费数据。它引入了正样本回放（PER）机制，缓存"高价值"回合（成功导航）并定期回放给策略网络。结果是在成功率上比基线提升了约 12%，证明了课程/数据质量比模型大小更重要。

**信号密度（"直觉"方法）**：主动风险感知（Rank 2）认为 Falcon 的碰撞惩罚太"稀疏"（只有在撞到人时才受到惩罚）。它添加了一个模块来基于距离预测连续的风险分数，让机器人在碰撞发生前很久就能"感知危险"。结果获得了第 2 名，证明了密集监督有助于强化学习收敛。

**超参数调优（"暴力"方法）**：混合参数优化认为 Falcon 的奖励权重（平衡效率与社会合规性）不是最优的。它使用网格搜索和耦合调优来找到参数的"帕累托前沿"。结果仅通过调参就实现了 15% 的成功率提升，凸显了强化学习基线的脆弱性。


有两篇论文挑战端到端强化学习的主导地位，认为结构和心理学是比试错更好的老师。

**"零样本"反叛**：SocialNav-Map 是一个关键的挑战者。它认为强化学习"不透明"且"难以泛化"。它实时构建动态占据地图，预测人类轨迹（使用历史+朝向）并将其"绘制"到地图上作为临时障碍物，然后使用经典路径规划器（快速行进方法）。洞察是它在没有训练的情况下击败了基于强化学习的 Falcon（后者需要 2396 GPU 小时训练），这表明显式世界建模可能优于隐式强化学习记忆。

**"以人为中心"的混合**：RLSLM 认为机器人不应该只是"猜测"社会规范。它将从心理学实验推导出的社会运动模型（SLM）直接整合到奖励函数中，创建了一个"非对称舒适场"（人类讨厌从前方接近，而不是从后方）。验证是通过 VR 让人类评价机器人，证明它比标准基于规则的方法"更有礼貌"。


最后两篇论文虽然不严格属于"社会导航"论文，但它们提供了解决社会导航中"语义鸿沟"的"新锤子"（技术）。

**SeeGround** 解决了 3D 视觉定位（通过文本找到物体）而无需 3D 训练数据。技术是使用"视角适应模块"（模拟相机看向物体）从 3D 场景渲染 2D 图像，并将其输入到 2D VLM。相关性在于它证明了如果正确格式化数据（渲染图像+空间提示），可以使用冻结的 2D VLM 来理解 3D 空间。

**Where to Fuse** 是一篇综述，分类了如何将 VLM/LLM 知识注入导航。框架将融合分为感知（识别物体）、预测（猜测关系）和规划（边界选择）。相关性在于它明确将"社会交互导航"称为未来，指出当前方法"将人类简化为移动障碍物"。

基于这些论文，可以绘制出研究路线图。

**Novelty Tree（技术演进）**：

- **Level 1：几何反应（过去）** → ORCA、Social Force
- **Level 2：几何预测（Falcon 时代）** → Falcon、PER-Falcon（预测轨迹）
- **Level 3：结构化混合（当前 SOTA）** → SocialNav-Map（显式映射动态风险）
- **Level 4：语义社会智能（空白）** → 理解上下文（例如："那两个人正在交谈，不要从中间走过"，或"那个人在赶路，让路"）

**Challenge-Insight Tree（工具箱）**：

| 社会导航中的挑战 | 当前解决方案（"旧"方法） | 提出的洞察（使用文献） |
|----------------|----------------------|---------------------|
| **数据效率** | 训练 1000 万步（Falcon） | 回放缓冲区：优先"正样本回合" |
| **奖励稀疏性** | 稀疏碰撞惩罚 | 密集风险：预测连续"风险分数" |
| **泛化性** | 在新地图上微调 | 零样本映射：使用动态占据地图 |
| **社会规范** | 希望强化学习"学会"它们 | 显式建模：注入心理学规则（SLM） |
| **语义盲区** | 仅深度输入（看不到"活动"） | VLM 注入：使用 SeeGround 的"视角渲染"来分类社会情境 |

文献清楚地表明，**几何问题已经解决**（SocialNav-Map 证明了可以零样本完成）。下一个前沿是**语义**。

**机会："语义社会地图"**

空白：Falcon 和 SocialNav-Map 将人类视为动态圆柱体。RLSLM 将它们视为磁场。它们都不知道人类在做什么。

新锤子：SeeGround 证明了可以使用 VLM 来"看"特定的 3D 坐标并理解它。

**提出的想法："VLM 驱动的社会可供性地图"**

- **感知**：使用 VLM（如 SeeGround）分析来自 RGB 相机的人类裁剪图像。分类它们的状态："交互中"、"等待中"、"看手机"、"匆忙"。
- **映射**：不仅仅是"占据地图"（如 SocialNav-Map），而是构建"社会规范地图"。
  - 示例：如果两个人正在"交互"，在它们之间创建"禁止通行区"。
  - 示例：如果一个人正在"看手机"，扩大其风险半径（他们分心了）。
- **规划**：在这个新的语义地图上使用 SocialNav-Map 规划器（FMM）。

这结合了 SocialNav-Map 的结构和 SeeGround 的语义能力，解决了 Where to Fuse 中识别的局限性。

Google Search 验证建议：你可以搜一下 "Foundation model for social navigation" 或 "Language-guided social navigation"，看看Level 4/5目前是否已经有人在用VLM/DepthAnything的Feature做SocialNav了。如果没有，这就是Blue Ocean。

