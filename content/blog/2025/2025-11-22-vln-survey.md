---
slug: 2025-11-22-vln-survey
title: VLN 综述以及后续文献
authors: [bubblevan]
tags: [vln, survey, navigation, vision-language, foundation-model, embodied-ai, world-model, human-model, agent]
---

# VLN 系列

从 Poing Navigation 到 Object Navigation，这也太难了，找Idea真的太难了。

然后秋冬学期的一半，也就是大四上的一半已经过去了，马上就要寒假了，寒假做什么，实习还是论文？真能憋出论文吗？

## Survey
研发能够与人类及其周边环境进行交互的**具身智能体**（embodied agents），是**人工智能**（AI）领域长期以来的核心目标之一。这类 AI 系统在现实世界中具有巨大的应用潜力，可作为日常生活中的多功能助手，例如**家用机器人**、**自动驾驶汽车**以及**个人助手**。推动这一研究方向的一个正式问题设定是**视觉-语言导航**（Vision-and-Language Navigation, **VLN**）—— 这是一项多模态协作任务，要求智能体遵循人类指令、探索**三维**（3D）环境，并在存在各类歧义的场景下开展情境化通信。多年来，研究者已在**照片级真实感模拟器**和**真实环境**中对 VLN 展开探索，由此形成了一系列**基准数据集**，每个数据集的问题表述略有不同。

![](/blog/2025/law-Challenge.png)

- **人类**（Human）：给出指令 "穿过客厅区域进入走廊。右转，然后再右转并进入房间"；在智能体询问 "左边的房间还是前面的房间？" 时回复 "左边"。
- **物理环境**（Physical Environment）：智能体感知的视觉场景。
- **VLN 智能体**（VLN Agent）：接收指令后进行 **"接地与推理"**（Grounding & Reasoning）、**"规划"**（Planning）、**"对话"**（Dialogue），执行 **"导航动作"**（Navigation Execution），并生成**语言响应**（Language Response）；过程中可能产生疑问，如 "…… 进入房间。左边？右边？""左边的房间还是前面的房间？"。
- **核心模块**：**世界模型**（World Model）、**人类模型**（Human Model），分别支撑智能体的环境理解与人类意图解读。

其[仓库](https://github.com/zhangyuejoslin/VLN-Survey-with-Foundation-Models)提到了一些工作内容，但是不全。

### 背景与任务基础
人类及其他具备导航能力的动物，很早就展现出对环境导航的理解与策略。例如，加利斯特尔（Gallistel）提出了两种基础机制：其一为**引导法**（piloting），即利用环境地标计算距离与角度；其二为**路径积分**（path integration），即通过自运动感知计算位移与方向变化。理解空间导航的核心是**认知地图假说**（cognitive map hypothesis）—— 该假说认为，大脑会形成统一的空间表征，以支持记忆存储并指导导航行为。例如，托尔曼（Tolman）观察到，当熟悉的路径被阻断且地标消失时，大鼠仍能选择正确的新路径。神经科学家还发现了**海马体位置细胞**（hippocampal place cells），这表明存在一种以**异中心视角**（allocentrically）编码地标与目标的空间坐标系。

传统上，**"遵循自然语言导航指令"**的任务多采用地图等**符号化世界表征**（symbolic world representations）进行建模。然而，本综述聚焦于采用视觉环境的模型，重点探讨**多模态理解与接地**（grounding）的相关挑战。与此相对，关于**视觉导航**和**移动机器人导航**的综述文献已十分丰富，这类综述主要关注视觉感知与物理具身性，但若涉及 **"语言在导航任务中的作用"**，则讨论较为简略，建议读者参考这些文献以获取相关背景。

> 接地（Grounding）指将抽象的语言符号与具体的物理世界或感知数据建立对应关系的过程。在 VLN 中，接地是将自然语言指令映射到视觉场景中的具体位置、物体或动作。

尽管在讨论 VLN 时，我们难免会将范围拓展到导航之外的领域（如移动操作、对话），但本综述的核心焦点仍是**导航任务**，并将针对该任务提供详细的文献梳理。此外，以往的 VLN 综述多采用 **"自下而上"** 的总结方式，聚焦于基准数据集与建模创新；而本综述则采用 **"自上而下"** 的视角，并以**基础模型**的角色为核心，将现有研究成果从 **"世界模型"**、**"人类模型"**、**"VLN 智能体"** 三个维度，归类为**三大核心挑战**。

典型的 **VLN 智能体**会在指定位置接收人类指令者给出的（一系列）**语言指令**。该智能体以**自我为中心的视觉视角**（egocentric visual perspective）在环境中导航，其核心任务是遵循指令生成**轨迹** —— 轨迹可基于一系列离散视角，也可基于低层级动作与控制指令（例如 "前进 0.25 米"），最终抵达**目标终点**。若智能体最终位置与目标终点的距离在指定范围内（例如 3 米），则判定为**导航成功**。此外，智能体在导航过程中可与指令者交互：既可以请求帮助，也可进行自由形式的语言沟通。近年来，研究者对 VLN 智能体的期望进一步提升，要求其在导航的同时整合附加任务，例如**操作任务**与**目标检测任务**。

![vln-benchmark-2024](/blog/2025/vln-benchmark-2024.png)

如上表，现有（2024）VLN **基准数据集**可分为以下四类：
1. **导航发生的 "世界"**：包括领域（室内或室外）与具体环境（如模拟器或真实场景）
2. **人类交互类型**：包括交互轮次（单轮或多轮）、通信格式（自由对话、受限对话或多指令）、语言粒度（动作导向或目标导向）
3. **VLN 智能体属性**：包括智能体类型（如家用机器人、自动驾驶车辆、自主无人机）、动作空间（图基、离散或连续）、附加任务（操作与目标检测）
4. **数据集收集方式**：包括文本收集（人类生成或模板生成）与路线演示（人类执行或规划器生成）

研究者主要采用三类指标评估 VLN 智能体的**导航寻路性能**：
1. **导航误差**（Navigation Error, **NE**）：智能体最终位置与目标终点之间最短路径距离的平均值
2. **成功率**（Success Rate, **SR**）：最终位置足够接近目标终点的任务占比
3. **路径长度加权成功率**（Success Rate Weighted Path Length, **SPL**）：通过轨迹长度对成功率进行归一化，平衡 **"抵达正确终点的成功率"** 与 **"路径效率"** 两大指标

此外，还有一类指标用于衡量 **"指令遵循的忠实度"** 与 **"预测轨迹和真实轨迹的一致性"**，例如：
4. **长度加权覆盖得分**（Coverage Weighted by Length Score, **CLS**）：衡量智能体轨迹与参考路径的贴合程度，通过 **"参考路径覆盖范围"** 与 **"轨迹长度效率"** 两个维度平衡智能体性能
5. **归一化动态时间规整**（Normalized Dynamic Time Warping, **nDTW**）：对偏离真实轨迹的行为进行惩罚
6. **成功率加权归一化动态时间规整**（Normalized Dynamic Time Warping Weighted by Success Rate, **sDTW**）：在惩罚轨迹偏离的同时，还会结合导航成功率综合评估

![vln-challenges-and-soluions](/blog/2025/vln-challenges-and-soluions.png)

该图反映的是：

- **核心模块关联**：**世界模型**中讨论 **"历史与记忆"**，**人类模型**中讨论 **"模糊指令"**，两者均涉及 **"泛化能力"**；**VLN 智能体**中讨论 **"接地与推理"**、**"规划"**、**"基础模型适配为智能体"** 三大方法

- **基础模型角色**：根据基础模型承担的功能，将方法分为四类 —— **数据与知识处理**（预处理 / 增强 / 合成数据、利用预训练常识）、**表征学习**（通用文本 / 视觉表征、历史记忆处理）、**决策制定**（导航规划器、信息寻求对话管理器、通用决策智能体）、**任务学习**（具身推理、语言接地、少样本 / 上下文 / 微调学习具身任务）

- **交互示例**：人类给出指令 "穿过客厅区域进入走廊。右转，然后再右转并进入房间""去卫生间"；智能体通过提问（"走廊在哪里？""哪个房间？"）寻求信息，人类回复（"左边的房间还是前面的房间？""左边"）后，智能体执行动作（"前进""左转"）并生成轨迹

- **挑战与未来方向**：**基准数据集**（数据与任务局限）、**世界模型**（从 2D 世界到 3D 世界）、**人类模型**（从指令到对话）、**智能体模型**（LLM 与 VLM 适配）、**部署**（从仿真到真实机器人）


### 三大解决方案

#### World Model: Learning and Representing the Visual Environments
**世界模型**能够帮助 VLN 智能体理解周边环境、预测自身动作对世界状态的改变，并使自身感知与动作与语言指令对齐。现有研究中，学习世界模型主要面临两大挑战：一是将当前任务段内的**视觉观测历史**编码为**记忆**，二是实现对未见过环境的**泛化**。

##### History and Memory
与**视觉问答**（Visual Question Answering, **VQA**）、**视觉蕴含**（Visual Entailment）等其他视觉-语言任务不同，VLN 智能体需将过去动作与观测的**历史信息**融入当前步骤的输入中以决策动作，而非仅依赖单一步骤的图像与文本。在 VLN 中应用基础模型之前，研究者通常采用 **LSTM 隐藏状态**作为支持智能体导航决策的隐式记忆，并进一步设计不同的**注意力机制**或**辅助任务**，以提升编码历史与指令的对齐程度。

目前已有多种基于基础模型的**导航历史编码技术**，核心可分为两类：

**（1）基于令牌更新或序列建模的编码**

- **多模态 Transformer 初始化**：以基于域内指令-轨迹数据预训练的模型（如 **Prevalent**）为基础，构建**多模态 Transformer**，将编码后的指令与导航历史作为输入以实现决策。

- **循环状态令牌编码**：部分方法通过循环更新的**状态令牌**编码导航历史。例如，利用上一步的单个 **[CLS] 令牌**编码历史信息；或设计**变长记忆框架**，将过去步骤的多个动作激活值存储在记忆库中，作为历史编码。但这类方法需逐步骤更新令牌，难以高效检索导航轨迹中任意步骤的历史编码，限制了预训练的可扩展性。

- **全景与历史分层编码**：另一类方法直接通过多模态 Transformer 将导航历史编码为序列。例如，对轨迹中每一步的单视角图像进行编码；或进一步提出 **"全景编码器 + 历史编码器"** 的分层设计 —— **全景编码器**处理每一时间步的全景视觉观测，**历史编码器**则编码所有过往观测。这种设计可分离全景视图中的空间关系与导航历史中跨全景的时间动态性，且无需依赖循环更新的状态令牌，便于基于指令-路径对进行高效、大规模的预训练。后续研究分别用 **"图像均值池化"** 或 **"前视图像编码"** 替代全景编码器，均保持了良好的导航性能。

**（2）基于 LLM 的文本化历史编码**

随着基于 **LLM** 的导航智能体兴起，**"将视觉环境转换为文本描述"** 成为主流趋势。此时导航历史被编码为 **"图像描述序列 + 相对空间信息"**（如朝向、高度、距离）的组合。例如，**HELPER** 设计了 **"语言-程序对"** 的外部记忆，通过检索增强的 LLM 提示，将人类与机器人的自由形式对话解析为动作程序。

另一类研究通过融入**图信息**增强导航历史建模，核心思路是利用**结构化图表征**环境几何与空间关系：

- **拓扑图与结构化编码**：部分方法采用**结构化 Transformer 编码器**捕捉环境中的几何线索。除编码中使用的**拓扑图**外，许多研究还将**俯视图信息**（如**网格图**、**语义图**、**局部度量图**）与**局部邻域图**纳入导航过程中的观测历史建模。

- **LLM 与图的结合**：近期基于 LLM 的导航智能体在记忆构建中引入了创新性的图应用。例如，提出一种基于**地图引导的 GPT 智能体**，利用语言化形式的地图存储和管理拓扑图信息；**MC-GPT** 则将拓扑图作为记忆结构，记录视角、物体及其空间关系的信息。

##### 跨环境泛化
VLN 的核心挑战之一是：如何从有限的可用环境中学习，并泛化到新的、未见过的环境中。现有研究表明，以下方法可提升智能体对未见过环境的泛化性能：**学习语义分割特征**、**利用训练过程中环境的 dropout 信息**、**最大化不同环境中语义对齐图像对的相似度**。

| 类别 | 方法 | 描述 |
|------|------|------|
| **3.2.1 预训练视觉表征** | **传统视觉编码器** | 多数研究采用在 ImageNet 上预训练的 **ResNet** 提取视觉表征 |
| | **基于 VL 基础模型的表征** | 用 **CLIP 视觉编码器**替代 ResNet——CLIP 通过图文对的对比损失预训练，可自然实现图像与指令的更好对齐，显著提升 VLN 性能 |
| | **视频预训练表征** | 探索将从视频数据中学习的视觉表征迁移到 VLN 任务中，证实视频中的**时间信息**对导航至关重要 |
| **3.2.2 环境增强** | **静态环境修改** | **EnvEdit**、**EnvMix**、**KED** 与 **FDA** 通过修改 Matterport3D 中的现有环境生成合成数据，具体手段包括混合不同环境的房间、改变环境外观与风格、对环境高频特征进行插值 |
| | **动态环境合成** | **Pathdreamer** 与 **SE3DS** 进一步实现 **"基于当前观测合成未来步骤环境"**，并探索将合成视图作为 VLN 训练的增强数据 |
| **3.2.3 学习范式的转变** | **前基础模型时代** | 多数研究直接用自动收集的新环境增强训练环境，并微调基于 LSTM 的 VLN 智能体 |
| | **基础模型时代** | **预训练**被证实对基础模型至关重要，因此 **"在预训练阶段从收集的环境中学习"** 成为 VLN 的标准做法。基于增强域内数据的**大规模预训练**，已成为缩小智能体与人类性能差距的关键；且域内预训练的多模态 Transformer，被证实比从 VLMs（如 **Oscar**、**LXMERT**）初始化的多模态 Transformer 更有效 |

#### Human Model: Interpreting and Communicating with Humans
除学习和建模世界外，VLN 智能体还需一个 **"人类模型"** —— 该模型能根据具体场景理解人类提供的自然语言指令，从而完成导航任务。这一过程主要面临两大挑战：一是解决**指令的模糊性**，二是实现 **"接地指令"** 在不同视觉环境中的**泛化**。

##### 模糊指令
**模糊指令**主要出现在**单轮导航场景**中：智能体仅遵循初始指令执行任务，无法通过进一步人类交互获取澄清。这类指令缺乏灵活性，难以训练智能体根据动态环境调整自身的**语言理解**与**视觉感知能力**。例如，指令中可能包含 **"当前视角不可见的地标"**，或 **"从多个视角观察均难以区分的地标"**。

在基础模型应用于 VLN 之前，模糊指令问题几乎未得到有效解决。尽管 **LEO 模型**尝试通过整合 **"从不同视角描述同一轨迹的多条指令"** 来缓解该问题，但仍依赖人工标注的指令。而基础模型所具备的 **"全面感知上下文"** 与 **"常识知识"**，使智能体既能利用外部知识解读模糊指令，也能向其他 **"人类模型"** 寻求协助。

**CLIP** 等大规模跨模态预训练模型具备**视觉语义与文本的匹配能力**，这使得 VLN 智能体可利用 **"当前感知到的视觉物体及其状态"** 来解决指令模糊性问题，在单轮导航场景中尤为有效。具体案例包括：

- **VLN-Trans 模型**：通过 CLIP 提取 **"可见且具有辨识度的物体"**，构建易于遵循的子指令；并预训练一个 **"转换器"**（Translator），将原始模糊指令转换为易于理解的子指令表征。

- **LANA+ 模型**：利用 CLIP，以视觉全景观测为输入，查询 **"地标语义标签文本列表"**，并选取排名靠前的检索文本线索作为 **"待跟随显著地标的表征"**。

- **KERM 模型**：提出一种 **"知识增强推理模型"**，可检索 **"以语言描述形式存储的导航视角相关知识事实"**。

- **NavHint 方法**：构建一个提示数据集，提供详细的视觉描述，帮助 VLN 智能体全面理解视觉环境，而非仅聚焦于指令中提及的物体。

另一方面，**LLM** 的**常识推理能力**可用于 **"澄清或修正指令中的模糊地标"**，并将指令拆解为可执行步骤。例如：

- 利用 LLM 提供 **"开放世界中地标共现的常识"**，并结合 CLIP 实现地标探测。

- **SayCan 方法**：将指令拆解为 **"预定义可执行动作的排序列表"**，并结合一个 **"效用函数"** —— 该函数对当前场景中出现的物体赋予更高权重。

尽管可通过**视觉感知**与**场景上下文**解决模糊指令问题，但更直接的方法是向 **"通信伙伴"**（即生成指令的人类）寻求帮助。这类研究主要面临三大核心挑战：

1. 判断 **"何时请求帮助"**
2. 生成 **"信息寻求问题"**（如询问下一步动作、物体位置、方向等）
3. 设计 **"信息提供方"**（oracle）—— 可为真实人类、规则与模板或神经模型

**LLM** 与 **VLM** 在该框架中可承担两种角色：一是 **"信息寻求模型"**，二是 **"人类助手的代理"** 或 **"信息提供模型"**。已有初步研究探索将 LLM 用作信息寻求模型，解决 **"何时问"** 与 **"问什么"** 的问题 —— 这需借助 **"保形预测"**（conformal prediction, **CP**）或 **"上下文学习"**（in-context learning, **ICL**）等技术实现。

对于 **"信息提供"** 角色，基础模型需扮演 **"掌握信息提供方专属信息的助手"** —— 例如知晓目标位置、环境地图等任务执行者无法获取的信息。近期相关研究包括：

- **VLN-Copilot 方法**：使智能体在遇到困惑时主动寻求协助，其中 LLM 扮演 **"副驾驶"** 角色，为导航提供支持。

- 证实 **GPT-3** 可逐步拆解训练数据中的真实响应，这有助于利用预训练的 **SwinBert** 视频-语言模型训练信息提供方模型；同时，**mPLUG-Owl** 等大型视觉-语言模型可作为 **"现成的强零样本信息提供方"**。

- **自驱动通信智能体**：通过学习 **"信息提供方给出肯定答案的置信度"** 实现，可采用 **"自我问答"** 模式，在推理阶段无需依赖信息提供方。

##### 接地指令的泛化
导航数据在规模与多样性上的局限，是影响 VLN 智能体 **"理解多样语言表达、有效遵循指令"** 的另一重要问题 —— 在未见过的导航环境中该问题尤为突出。尽管**语言风格**本身在 **"见过与未见过的环境"** 中具备良好泛化能力，但受限于训练指令的规模，**"如何将指令与未见过的环境进行接地"** 仍是一项难题。基础模型通过 **"预训练表征"** 与 **"指令生成数据增强"** 两种方式，为解决这些问题提供了支持。

在基础模型出现前，多数研究依赖 **LSTM** 等文本编码器表征文本指令。而基础模型通过**预训练表征**，显著提升了 VLN 智能体的**语言泛化能力**，具体案例包括：

- **PRESS 方法**：对预训练语言模型 **BERT** 进行微调，获得对 **"未见过指令"** 泛化性更强的文本表征。

- **多模态 Transformer**：为 **VLN-BERT**、**PREVALENT** 等方法提供支撑 —— 这些方法通过在 **"从网络收集的大规模图文对"** 上预训练，获得更通用的**视觉-语言表征**。

- **Airbert 模型**：训练一个类 **ViLBERT** 架构，从 **"互联网收集的图像-标题对"** 中学习文本表征。

- **CLEAR 方法**：学习 **"跨语言语言表征"**，捕捉指令背后的**视觉概念**。

- **ProbES 方法**：通过采样轨迹实现**环境自探索**，并利用 CLIP 检测到的 **"动作与物体短语"** 填充指令模板，自动构建对应指令；同时借助 **"基于提示的学习"**，实现**语言嵌入**的快速适配。

- **NavGPT-2 模型**：探索利用 **"预训练 VLMs"**（如结合 **Flan-T5** 或 **Vicuna** 的 **InstructBLIP**）的**视觉-语言表征**，提升**导航策略学习**与**导航推理能力**。

提升智能体泛化能力的另一方法是 **"合成更多指令"**。相关研究可分为两类：

**（1）离线指令生成**

早期研究采用 **"说话者-跟随者（Speaker-Follower）框架"**：利用人工标注的 **"指令-轨迹对"** 训练一个 **"离线说话者（指令生成器）"**，再让其基于 **"给定轨迹上的全景序列"** 生成新指令。但发现这类方法生成的指令质量较低，在人类寻路评估中表现不佳。

后续改进方法包括：

- **Marky 模型**：采用 **"多语言 T5 模型的多模态扩展版本"**，结合 **"文本对齐的视觉地标对应关系"**，在未见过环境的 R2R 风格路径上生成 **"接近人类质量"** 的指令。

- **PASTS 模型**：引入 **"进度感知的时空 Transformer 说话者"**，更好地利用 **"有序的多视觉与动作特征"**。

- **SAS 方法**：利用环境的 **"语义与结构线索"**，生成包含丰富**空间信息**的指令。

- **SRDF 方法**：通过 **"迭代自训练"** 构建一个性能强劲的指令生成器。

**（2）导航中实时指令生成**

部分近期研究不再训练离线指令生成器，而是在**导航过程中实时生成指令**。例如，**LANA 模型**提出一种 **"具备语言能力的导航智能体"** —— 该智能体不仅能执行导航指令，还可生成路线描述。


#### VLN Agent: Learning an Embodied Agent for Reasoning and Planning
尽管**世界模型**与**人类模型**为智能体赋予了**视觉与语言理解能力**，但 VLN 智能体仍需培养**具身推理**（embodied reasoning）与**规划能力**，以支撑自身决策。从这一角度出发，我们将探讨两大挑战：**接地与推理**、**规划**；同时还将研究 **"直接以基础模型作为 VLN 智能体核心骨干"** 的方法。

##### 接地与推理
视觉-语言领域的其他任务（如**视觉问答**（**VQA**）、**图像描述生成**）主要聚焦于 **"图像与对应文本描述之间的静态对齐"**，而 VLN 智能体则需基于自身动作，对 **"指令与环境中的时空动态信息"** 进行推理。具体而言，智能体需考虑**过往动作**、识别**待执行的子指令片段**，并将文本与视觉环境进行**接地**（grounding），从而执行相应动作。

传统方法主要通过 **"显式语义建模"** 或 **"辅助任务设计"** 获取上述能力；但随着基础模型的兴起，**"基于特定设计任务的预训练"** 已成为主流方案。

传统研究通过 **"视觉与语言模态的显式语义建模"** 提升智能体的**显式接地能力**，具体方向包括：

- **建模动作与地标**
- **利用指令中的句法信息**
- **建模空间关系**

目前，**"基于基础模型实现 VLN 智能体显式接地"** 的研究仍较少。例如，提出 **"动作原子概念学习"**，并将视觉观测映射为**多模态对齐特征**，以辅助接地。

除显式语义建模外，传统研究还通过 **"辅助推理任务"** 提升智能体的接地能力。但在基于基础模型的 VLN 智能体中，这类方法较少被探索 —— 因为基础模型的预训练过程已使其在导航前就具备了对 **"时空语义"** 的通用理解。

现有研究通过设计**特定预训练任务**，进一步提升智能体的接地能力，代表性工作包括：

- 设计专门针对 **"场景与物体接地"** 的预训练任务

- **LOViS**：提出两项专项预训练任务，分别增强智能体的 **"方向感知"** 与 **"视觉信息理解"**

- **HOP**：提出 **"历史与顺序感知预训练范式"**，重点强调**历史信息**与**轨迹顺序**

- 证实 **"增强智能体的未来视角语义预测能力"** 有助于提升其在**长路径导航**中的性能

- 设计 **"掩码路径建模目标"** —— 给定随机掩码的子路径，重建原始完整路径

- 提出 **"实体感知预训练"**，通过预测**接地实体**并将其与文本对齐实现接地能力提升

##### 规划
**动态规划**能让 VLN 智能体实时适应环境变化、优化导航策略。目前，规划方法主要分为两类：一类是 **"利用全局图信息增强局部动作空间"** 的**图基规划器**；另一类是随基础模型（尤其是 **LLM**）兴起的 **LLM 基规划器** —— 这类规划器借助 LLM 的**海量常识**与**先进推理能力**，生成动态规划方案，提升决策效果。

近期 VLN 研究的核心方向之一，是通过 **"全局图信息"** 增强导航智能体的规划能力，代表性工作包括：

- 利用 **"已访问节点的图边界"** 中的**全局动作步骤**，增强**局部导航动作空间**，以实现更优**全局规划**

- 通过 **"高层规划（区域选择）+ 低层规划（节点选择）"** 的**分层策略**，进一步优化导航决策

- 在 **"基于图边界的全局与局部动作空间"** 中融入 **"网格级动作"**，提升**动作预测精度**

在**连续环境**中，规划方法进一步演进：

- 采用**分层规划思路** —— 通过 **"从预测的局部可导航性图中选择局部航点"**，用**高层动作空间**替代**低层动作空间**

- **CM2**：通过 **"在局部地图中实现指令接地"**，辅助**轨迹规划**

- 拓展上述策略，构建**全局拓扑图**或**网格图**，支持 **"基于地图的全局规划"**

- 利用 **"视频预测模型"** 或 **"神经辐射表征模型"** 预测多个**未来航点**，并基于 **"预测候选航点的长期影响"** 规划最优动作

与此同时，部分研究借助 LLM 的**常识知识**生成 **"基于文本的规划方案"**，代表性工作包括：

- **LLM-Planner**：生成由 **"子目标"** 构成的详细规划，并根据**预定义程序模式**整合检测到的物体，实时动态调整规划

- **Mic** 与 **A²Nav**：专注于将导航任务拆解为详细文本指令 —— Mic 从**静态与动态双视角**生成分步规划，A²Nav 则利用 **GPT-3** 将指令解析为可执行子任务

- **ThinkBot**：采用 **"思维链推理"**（Chain-of-Thought Reasoning），生成 **"与交互物体相关的缺失动作"**

- **VL-Map**：基于 **"代码化 LLM"**（遵循 **Code-as-Policy** 框架），将导航指令拆解为 **"代码格式的时序化目标相关函数"**，并利用 **"动态构建的可查询地图"** 指导目标执行

- **SayNav**：构建 **"已探索环境的 3D 场景图"**，将其作为 LLM 输入，为导航器生成 **"可行且符合上下文的高层规划"**

##### 作为 VLN 智能体的基础模型
主流方案以 **"单流 VL 模型"** 作为 VLN 智能体的核心结构：这类模型在每个时间步同时处理 **"语言、视觉、历史令牌（token）"** 输入，通过对**跨模态令牌**的自注意力运算捕捉 **"文本-视觉对应关系"**，进而推断动作概率。

在**零样本 VLN** 场景中，**CLIP-NAV** 利用 CLIP 获取 **"描述目标物体的自然语言指称表达式"**，实现**序贯导航决策**。

此外，**VLN-CE**（连续环境 VLN）智能体与 **VLN-DE**（离散环境 VLN）智能体的核心差异在于**动作空间**：前者在连续环境中执行**低层控制**，而非后者 **"基于图的高层视角选择动作"**。尽管早期研究采用 **LSTM** 推断低层动作，但 **"航点预测器"**（waypoint predictor）的引入实现了 **"从 DE 到 CE 的方法迁移"** —— 所有这些方法均通过航点预测器获取 **"局部可导航性图"**，使 DE 场景中的基础模型能适配连续环境。具体而言，航点检测过程主要通过 **"视觉观测"**（如全景 RGBD 图像），从智能体当前位置预测 **"可导航的相邻候选航点"** 作为潜在目标，再由智能体选择其一作为当前目的地。

**LLM** 具备强大的**推理能力**与**世界语义抽象能力**，且在 **"未知大规模环境"** 中表现出优异的**泛化性** —— 因此，近期 VLN 研究开始直接将 LLM 作为智能体执行导航任务。其核心流程为：将**视觉观测**转换为**文本描述**，与指令一同输入 LLM，由 LLM 完成**动作预测**。

代表性创新方案包括：

- **NavGPT** 与 **MapGPT**：验证了**零样本导航**的可行性 —— NavGPT 利用 **GPT-4** 自主生成动作，MapGPT 将**拓扑图**转换为**全局探索提示**

- **DiscussNav**：拓展上述思路，部署 **"多领域专用 VLN 专家"**（包括**指令分析专家**、**视觉感知专家**、**完成度估计专家**、**决策测试专家**），减少导航任务中的人工参与：通过将任务分配给专用智能体，减轻单一模型负担，实现 **"任务专属优化处理"**，并借助**多大型模型的协同优势**提升**鲁棒性**、**透明度**与**整体性能**

- **MC-GPT**：利用 **"记忆拓扑图"** 与 **"人类导航示例"** 丰富**策略多样性**

- **InstructNav**：将导航拆解为**子任务**，并结合 **"多源价值图"** 实现高效执行

与 **"零样本使用"** 不同，部分研究通过 **"微调 LLM"**，使其能更有效地处理**具身导航任务**。另有研究融入 **"思维链"**（Chain-of-Thought, **CoT**）推理机制提升推理过程，例如 **Nav-CoT** 将 LLM 转化为 **"世界模型与导航推理智能体"**，通过模拟未来环境简化决策 —— 这一方案证实了 **"微调语言模型"** 在仿真与真实场景中的**灵活性**与**实用潜力**，较传统应用实现了显著突破。
### 挑战与未来方向
尽管基础模型为**视觉-语言导航**（**VLN**）提供了创新性解决方案，但仍有若干局限尚未得到充分探索，同时新的挑战也随之出现。在本节中，我们将从**基准数据集**、**世界模型**、**人类模型**、**智能体模型**及**真实机器人部署**五个维度，梳理 VLN 领域的挑战与未来研究方向。

#### 基准数据集：数据与任务的局限
当前 **VLN 数据集**在**质量**、**多样性**、**偏差**及**可扩展性**方面存在明显局限。例如，在 **R2R** 数据集中，**"指令-轨迹对"** 偏向于**最短路径**，无法准确反映现实世界的导航场景。下文将探讨 VLN 基准数据集的改进趋势与建议方向：

**统一且贴近现实的任务与平台**：构建可靠的基准数据集并确保结果可复现，是评估真实场景下 VLN 性能的关键。现实世界的复杂性要求基准数据集需全面覆盖各类导航挑战，因此需要一个通用的 **"仿真到现实"** 评估平台（如 **OVMM**），以实现仿真与真实场景下的标准化测试。此外，任务与活动设计需贴近现实且源于人类需求，例如 **BEHAVIOR-1K** 基准数据集，在虚拟、交互式且具生态性的环境中构建**日常家庭活动场景**，以满足对 **"多样性"** 与 **"真实性"** 的需求。

**动态环境**：现实世界环境本质上具有**复杂性**与**动态性** —— **移动物体**、**行人**，以及**光照**、**天气**等环境变化，均可能引发**突发情况**。这些因素会干扰导航系统的**视觉感知**，使其难以维持稳定性能。近期部分研究（如 **HAZARD**、**Habitat 3.0**、**HA-VLN**）已开始关注**动态环境**，为后续研究提供了良好起点。

**从室内到室外**：适用于室外环境的 VLN 智能体（如**自动驾驶车辆**、**无人机**）正逐渐获得更多关注，相关**语言引导数据集**也已陆续开发。早期研究尝试将 LLM 融入**室外 VLN 任务**，具体方式包括**提示工程**，或通过**微调 LLM** 实现 **"预测下一步动作"** 与 **"规划未来轨迹"**。为使现成的 VLN 模型适配**室外导航场景**，研究者利用**真实驾驶视频**、**仿真驾驶数据**或两者结合进行**指令微调**，使基础模型能够学习预测未来的**油门与转向角度**。此外，研究者还在基于基础模型的驾驶智能体中集成了额外的**推理与规划模块**。关于室外 VLN 的详细综述，建议读者参考相关综述文献与立场论文。
#### 世界模型：从二维（2D）到三维（3D）
构建有效的**世界表征**是**具身感知**、**推理**与**规划**领域的核心研究主题。VLN 本质上是一项 **3D 任务** —— 智能体需以 3D 形式感知真实世界环境。尽管当前研究已能通过强大的通用 **2D 表征**描述世界，但这类表征无法充分支持 3D 场景下的**空间语言理解**。

以往研究已提出多种显式 **3D 表征方式**，包括各类**语义同步定位与地图构建**（semantic **SLAM**）、**体素表征**、**深度信息**、**鸟瞰图**（Bird's-Eye-View）表征（如**网格图**）及**局部度量图**。但这些表征存在局限：它们将物体集合限定为 **"封闭集合"**，无法适配自然语言对应的 **"开放词汇场景"**。

部分研究尝试构建 **"可查询的地图/场景表征"**，例如将 CLIP 提取的**多视角图像特征**整合到 **3D 体素网格**或**俯视特征图**中，或利用**场景图**表征**空间关系**。然而，**"如何将大规模数据中学习到的 3D 表征适配于 VLN 智能体，以提升其 3D 环境感知能力"** 仍是待探索的问题。近期兴起的 **3D 基础模型** —— 包括 **3D 重建模型** 与 **3D 多模态表征模型** —— 有望为 VLN 领域提供关键支撑。

#### 人类模型：从指令到对话
以往研究多采用 **"说话者-倾听者范式"** 或 **"受限问答对话"** —— 这类方式仅允许智能体主动请求帮助。近年来，涌现出一批以 **"开放式对话指令"** 为核心的新基准数据集，支持智能体在模糊或困惑场景下进行完全**自由形式的通信**，包括**提问**、**提议**、**解释**、**建议**、**澄清**与**协商**。

然而，当前方法仍依赖 **"基于规则的对话模板"** 应对上述复杂场景，即便部分方法包含基础模型组件，也未充分发挥其能力。通过 **"人类对话数据 + 仿真导航视频"** 对**视频-语言模型**进行**对话调优**，使模型在导航过程中具备更强的**对话生成能力**。未来研究需重点关注两方面：一是将基础模型融入 **"情境化任务导向对话管理"**；二是探索现有基础模型在 **"任务导向对话"** 中的应用潜力。

#### 智能体模型：基础模型在 VLN 中的适配
尽管基础模型具有强大的**泛化能力**，但将其融入导航任务仍面临挑战：**LLM** 本质上缺乏对真实环境的**视觉感知能力**，且易产生 **"幻觉"**；下文还将探讨 LLM 在规划与推理方面的能力局限。

**缺乏具身经验**：这一局限可能导致 LLM 在任务规划与推理中仅依赖**预设常识**，无法满足真实场景的特定需求。部分研究通过 **"将视觉观测转换为文本描述，作为 LLM 的提示"** 解决该问题，但这种方式可能丢失关键**视觉语义**。与 LLM 相比，**VLM**（视觉-语言模型）智能体虽展现出 **"感知视觉世界与规划"** 的潜力，但其训练数据主要源于互联网，缺乏**具身经验**，需通过**微调**实现稳健的智能体决策。未来需进一步研究 **"如何将基础模型智能体中的常识知识迁移到具身场景中"**。近期提出的 **"具身基础模型"**（如 **EmbodieGPT**、**PaLM-E**、**Octopus**）为解决该问题提供了可行方向：这些模型通过在多类具身任务上微调基础模型，缩小智能体在 **"视觉-语言-具身动作"** 理解上的差距，提升其基于多模态输入的理解与执行能力。

**幻觉问题**：LLM 与 VLM 可能生成 **"不存在的物体"**，导致**信息失真**。例如，LLM 在任务规划时可能生成 **"向前走并在沙发处左转"** 的指令，即便房间内并无沙发。这种偏差可能导致智能体执行错误或无法完成的动作。

**LLM 在规划与推理中的能力局限**：已有文献针对 LLM 的**零样本推理与规划能力**展开评估（尤其是结合 **PlanBench** 与 **CogEval**），结果表明 LLM 在**复杂规划任务**中存在明显局限。这些研究在 **"规划生成、最优性、稳健性、推理"** 等挑战性场景下评估 LLM，发现其不仅易产生幻觉，还可能无法理解复杂规划问题背后的**关系结构**。

在 VLN 场景中，由于室内环境固定且导航动作集合有限，**动作空间**与**规划需求**相对受限。这种 **"有界场景"** 使 LLM 能够生成 **"粗粒度方向的分步指令"** —— 已有研究证实该方式的有效性。需强调的是，在 VLN 任务中，LLM 并非主导整个规划过程，而是通过 **"结构化拆解指令"** 提供辅助；智能体的实际决策仍主要依赖**感知**、**运动控制**等其他组件。因此，LLM 的规划功能更多是 **"补充性指导"**，而非唯一决策依据。

#### 部署：从仿真到真实机器人
仿真环境往往缺乏真实世界的**复杂性**与**多样性**，且低质量渲染图像会进一步加剧这一问题。具体而言，当前部署面临三大瓶颈：

**感知差距**：仿真与真实场景的**视觉差异**导致智能体性能与精度下降，因此需构建更稳健的感知系统。例如，尝试利用**语义地图**与 **3D 特征场**为单目机器人提供**全景感知**，显著提升了性能。

**具身差距与数据稀缺**：仿真环境的**物理规则**与真实机器人的**具身特性**不匹配，且真实场景下 VLN 数据收集成本高、规模有限。

**数据规模化解决方案**：**机器人远程操控**的兴起为解决数据稀缺提供了新思路 —— 通过人类远程控制机器人，可在真实人机交互场景中规模化收集 VLN 数据，为基础模型训练提供支撑。

### 仓库论文链接

> **说明**：本表格按分类和子分类组织所有 VLN 相关论文，便于浏览和筛选。分类包括：Survey（综述）、World Model（世界模型）、Human Model（人类模型）、VLN Agent（VLN 智能体）、Behavior Analysis（行为分析）。

| 分类 | 子分类 | 标题 | 会议 | 年份 | 代码 |
|:------|:------:|:-----|:----:|:----:|:----:|
| **Survey** | - | [Vision-and-Language Navigation: A Survey of Tasks, Methods, and Future Directions](https://arxiv.org/abs/2203.12667) | ACL | 2022 | [Github](https://github.com/eric-ai-lab/awesome-vision-language-navigation) |
| | - | [Visual language navigation: A survey and open challenges](https://link.springer.com/article/10.1007/s10462-022-10174-9) | - | 2023 | - |
| | - | [Vision-Language Navigation: A Survey and Taxonomy](https://arxiv.org/abs/2108.11544) | - | 2021 | - |
| **World Model** | - | [MapNav: A Novel Memory Representation via Annotated Semantic Maps for VLM-based Vision-and-Language Navigation](https://arxiv.org/pdf/2502.13451) | ACL | 2025 | - |
| | - | [VLN-Video: Utilizing Driving Videos for Outdoor Vision-and-Language Navigation](https://arxiv.org/abs/2402.03561) | AAAI | 2024 | - |
| | - | [Volumetric Environment Representation for Vision-Language Navigation](https://arxiv.org/pdf/2403.14158) | CVPR | 2024 | [Github](https://github.com/DefaultRui/VLN-VER) |
| | - | [Vision Language Navigation with Knowledge-driven Environmental Dreamer](https://www.ijcai.org/proceedings/2023/0204.pdf) | IJCAI | 2023 | - |
| | - | [Frequency-Enhanced Data Augmentation for Vision-and-Language Navigation](https://proceedings.neurips.cc/paper_files/paper/2023/file/0d9e08f247ca7fbbfd5e50b7ff9cf357-Paper-Conference.pdf) | NeurIPS | 2023 | [Github](https://github.com/hekj/FDA) |
| | - | [Panogen: Text-conditioned panoramic environment generation for vision-and-language navigation](https://arxiv.org/abs/2305.19195) | NeurIPS | 2023 | [Github](https://github.com/jialuli-luka/PanoGen) |
| | - | [Simple and Effective Synthesis of Indoor 3D Scenes](https://arxiv.org/pdf/2204.02960) | AAAI | 2023 | [Github](https://github.com/google-research/se3ds) |
| | - | [Learning Navigational Visual Representations with Semantic Map Supervision](https://openaccess.thecvf.com/content/ICCV2023/papers/Hong_Learning_Navigational_Visual_Representations_with_Semantic_Map_Supervision_ICCV_2023_paper.pdf) | ICCV | 2023 | - |
| | - | [Learning vision-and-language navigation from youtube videos](https://arxiv.org/abs/2307.11984) | ICCV | 2023 | [Github](https://github.com/JeremyLinky/YouTube-VLN) |
| | - | [GridMM: Grid Memory Map for Vision-and-Language Navigation](https://arxiv.org/abs/2307.12907) | ICCV | 2023 | [Github](https://github.com/MrZihan/GridMM) |
| | - | [BEVBert: Multimodal Map Pre-training for Language-guided Navigation](https://arxiv.org/abs/2212.04385) | ICCV | 2023 | [Github](https://github.com/MarSaKi/VLN-BEVBert) |
| | - | [Scaling Data Generation in Vision-and-Language Navigation](https://arxiv.org/abs/2307.15644) | ICCV | 2023 | [Github](https://github.com/wz0919/ScaleVLN/tree/main?tab=readme-ov-file) |
| | - | [A New Path: Scaling Vision-and-Language Navigation with Synthetic Instructions and Imitation Learning](https://arxiv.org/abs/2210.03112) | CVPR | 2023 | [Github](https://github.com/clin1223/MTVM) |
| | - | [EnvEdit: Environment Editing for Vision-and-Language Navigation](https://arxiv.org/abs/2203.15685) | CVPR | 2022 | [Github](https://github.com/jialuli-luka/VLN-SIG) |
| | - | [Multimodal Transformer with Variable-length Memory for Vision-and-Language Navigation](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136960375.pdf) | ECCV | 2022 | [Github](https://github.com/jialuli-luka/VLN-SIG) |
| | - | [How Much Can CLIP Benefit Vision-and-Language Tasks?](https://arxiv.org/abs/2107.06383) | ICLR | 2022 | [Github](https://github.com/clip-vil/CLIP-ViL) |
| | - | [Think Global, Act Local: Dual-scale Graph Transformer for Vision-and-Language Navigation](https://arxiv.org/abs/2202.11742) | CVPR | 2022 | [Github](https://github.com/cshizhe/VLN-DUET) |
| | - | [History Aware Multimodal Transformer for Vision-and-Language Navigation](https://arxiv.org/abs/2110.13309) | NeurIPS | 2021 | [Github](https://cshizhe.github.io/projects/vln_hamt.html) |
| | - | [Pathdreamer: A World Model for Indoor Navigation](https://arxiv.org/abs/2105.08756) | ICCV | 2021 | - |
| | - | [Episodic Transformer for Vision-and-Language Navigation](https://openaccess.thecvf.com/content/ICCV2021/papers/Pashevich_Episodic_Transformer_for_Vision-and-Language_Navigation_ICCV_2021_paper.pdf) | ICCV | 2021 | - |
| | - | [Airbert: In-domain Pretraining for Vision-and-Language Navigation](https://arxiv.org/abs/2108.09105) | ICCV | 2021 | [Github](https://airbert-vln.github.io/) |
| | - | [Vision-Language Navigation with Random Environmental Mixup](https://arxiv.org/abs/2106.07876) | ICCV | 2021 | [Github](https://github.com/LCFractal/VLNREM) |
| **Human Model** | - | [Scene Map-based Prompt Tuning for Navigation Instruction Generation](https://openaccess.thecvf.com/content/CVPR2025/papers/Fan_Scene_Map-based_Prompt_Tuning_for_Navigation_Instruction_Generation_CVPR_2025_paper.pdf) | CVPR | 2025 | - |
| | - | [NavRAG: Generating User Demand Instructions for Embodied Navigation through Retrieval-Augmented LLM](https://arxiv.org/pdf/2502.11142) | ACL | 2025 | [Github](https://github.com/MrZihan/NavRAG) |
| | - | [Bootstrapping Language-Guided Navigation Learning with Self-Refining Data Flywheel](https://arxiv.org/abs/2412.08467) | ICLR | 2025 | [Github](https://github.com/wz0919/VLN-SRDF) |
| | - | [Navigation Instruction Generation with BEV Perception and Large Language Models](https://arxiv.org/pdf/2407.15087) | ECCV | 2024 | [Github](https://github.com/FanScy/BEVInstructor) |
| | - | [Controllable Navigation Instruction Generation with Chain of Thought Prompting](https://arxiv.org/pdf/2407.07433) | ECCV | 2024 | [Github](https://github.com/refkxh/C-Instructor) |
| | - | [Spatially-Aware Speaker for Vision-and-Language Navigation Instruction Generation](https://aclanthology.org/2024.acl-long.734.pdf) | ACL | 2024 | [Github](https://github.com/gmuraleekrishna/SAS) |
| | - | [Correctable Landmark Discovery via Large Models for Vision-Language Navigation](https://arxiv.org/abs/2405.18721) | TPAMI | 2024 | [Github](https://github.com/expectorlin/CONSOLE) |
| | - | [NavHint: Vision and Language Navigation Agent with a Hint Generator](https://arxiv.org/pdf/2402.02559) | EACL | 2024 | [Github](https://github.com/HLR/NavHint) |
| | - | [Learning to Follow and Generate Instructions for Language-Capable Navigation](https://ieeexplore.ieee.org/document/10359152) | TPAMI | 2023 | - |
| | - | [Lana: A Language-Capable Navigator for Instruction Following and Generation](https://arxiv.org/abs/2303.08409) | CVPR | 2023 | [Github](https://github.com/wxh1996/LANA-VLN) |
| | - | [KERM: Knowledge Enhanced Reasoning for Vision-and-Language Navigation](https://openaccess.thecvf.com/content/CVPR2023/papers/Li_KERM_Knowledge_Enhanced_Reasoning_for_Vision-and-Language_Navigation_CVPR_2023_paper.pdf) | CVPR | 2023 | [Github](https://github.com/xiangyangli-cn/KERM) |
| | - | [PASTS: Progress-Aware Spatio-Temporal Transformer Speaker For Vision-and-Language Navigation](https://arxiv.org/pdf/2305.11918) | MM | 2023 | - |
| | - | [CrossMap Transformer: A Crossmodal Masked Path Transformer Using Double Back-Translation for Vision-and-Language Navigation](https://arxiv.org/abs/2103.00852) | - | 2023 | - |
| | - | [VLN-Trans: Translator for the Vision and Language Navigation Agent](https://arxiv.org/pdf/2302.09230) | ACL | 2023 | [Github](https://github.com/HLR/VLN-trans) |
| | - | [Visual-Language Navigation Pretraining via Prompt-based Environmental Self-exploration](https://arxiv.org/pdf/2203.04006) | ACL | 2022 | [Github](https://github.com/liangcici/Probes-VLN) |
| | - | [Less is More: Generating Grounded Navigation Instructions from Landmarks](https://arxiv.org/pdf/2004.14973) | CVPR | 2022 | [Github](https://github.com/google-research-datasets/RxR/tree/main/marky-mT5) |
| | - | [On the Evaluation of Vision-and-Language Navigation Instructions](https://arxiv.org/abs/2101.10504) | EACL | 2021 | - |
| | - | [Do As I Can, Not As I Say:Grounding Language in Robotic Affordances](https://say-can.github.io/assets/palm_saycan.pdf) | - | - | [Github](https://say-can.github.io/) |
| **VLN Agent** | - | [SAME: Learning Generic Language-Guided Visual Navigation with State-Adaptive Mixture of Experts](https://arxiv.org/pdf/2412.05552) | ICCV | 2025 | [Github](https://github.com/GengzeZhou/SAME) |
| | - | [MiniVLN: Efficient Vision-and-Language Navigation byProgressive Knowledge Distillation](https://arxiv.org/pdf/2409.18800) | ICRA | 2024 | - |
| | - | [Actional Atomic-Concept Learning for Demystifying Vision-Language Navigation](https://arxiv.org/pdf/2302.06072) | AAAI | 2023 | - |
| | - | [Grounded Entity-Landmark Adaptive Pre-training for Vision-and-Language Navigation](https://arxiv.org/abs/2308.12587) | ICCV | 2023 | [Github](https://github.com/CSir1996/VLN-GELA) |
| | - | [Adaptive Zone-aware Hierarchical Planner for Vision-Language Navigation](https://openaccess.thecvf.com/content/CVPR2023/papers/Gao_Adaptive_Zone-Aware_Hierarchical_Planner_for_Vision-Language_Navigation_CVPR_2023_paper.pdf) | ICCV | 2023 | [Github](https://github.com/chengaopro/AZHP) |
| | - | [Bird's-Eye-View Scene Graph for Vision-Language Navigation](https://arxiv.org/abs/2308.04758) | ICCV | 2023 | - |
| | - | [Masked Path Modeling for Vision-and-Language Navigation](https://arxiv.org/abs/2305.14268) | EMNLP Findings | 2023 | - |
| | - | [Improving Vision-and-Language Navigation by Generating Future-View Image Semantics](https://arxiv.org/pdf/2304.04907) | CVPR | 2023 | [Github](https://github.com/jialuli-luka/VLN-SIG) |
| | - | [HOP+: History-Enhanced and Order-Aware Pre-Training for Vision-and-Language Navigation](https://ieeexplore.ieee.org/document/10006384) | TPAMI | 2023 | - |
| | - | [Target-Driven Structured Transformer Planner for Vision-Language Navigation](https://arxiv.org/pdf/2207.11201) | MM | 2022 | [Github](https://github.com/YushengZhao/TD-STP) |
| | - | [HOP: History-and-Order Aware Pre-training for Vision-and-Language Navigation](https://ieeexplore.ieee.org/document/9880046) | CVPR | 2022 | [Github](https://github.com/YanyuanQiao/HOP-VLN) |
| | - | [LOViS: Learning Orientation and Visual Signals for Vision and Language Navigation](https://aclanthology.org/2022.coling-1.505.pdf) | COLING | 2022 | [Github](https://github.com/HLR/LOViS) |
| | - | [Scene-Intuitive Agent for Remote Embodied Visual Grounding](https://arxiv.org/pdf/2103.12944) | CVPR | 2021 | - |
| | - | [SOAT: A Scene- and Object-Aware Transformer for Vision-and-Language Navigation](https://arxiv.org/abs/2110.14143) | NeurIPS | 2021 | - |
| | - | [The Road to Know-Where: An Object-and-Room Informed Sequential BERT for Indoor Vision-Language Navigation](https://openaccess.thecvf.com/content/ICCV2021/papers/Qi_The_Road_To_Know-Where_An_Object-and-Room_Informed_Sequential_BERT_for_ICCV_2021_paper.pdf) | ICCV | 2021 | [Github](https://github.com/YuankaiQi/ORIST) |
| | - | [VLN BERT: A Recurrent Vision-and-Language BERT for Navigation](https://openaccess.thecvf.com/content/CVPR2021/papers/Hong_VLN_BERT_A_Recurrent_Vision-and-Language_BERT_for_Navigation_CVPR_2021_paper.pdf) | CVPR | 2021 | [Github](https://github.com/YicongHong/Recurrent-VLN-BERT) |
| | - | [Towards Learning a Generic Agent for Vision-and-Language Navigation via Pre-training](https://arxiv.org/abs/2002.10638) | CVPR | 2020 | [Github](https://github.com/weituo12321/PREVALENT) |
| | VLN-CE | [MonoDream: Monocular Vision-Language Navigation with Panoramic Dreaming](https://arxiv.org/pdf/2508.02549) | ICCV | 2025 | - |
| | | [JanusVLN: Decoupling Semantics and Spatiality with Dual Implicit Memory for Vision-Language Navigation](https://arxiv.org/pdf/2509.22548) | Arxiv | 2025 | [Github](https://miv-xjtu.github.io/JanusVLN.github.io/) |
| | | [NavMorph: A Self-Evolving World Model for Vision-and-Language Navigation in Continuous Environments](https://arxiv.org/pdf/2506.23468) | ICCV | 2025 | [Github](https://github.com/Feliciaxyao/NavMorph) |
| | | [Affordances-Oriented Planning using Foundation Models for Continuous Vision-Language Navigation](https://arxiv.org/abs/2407.05890) | AAAI | 2025 | - |
| | | [Lookahead Exploration with Neural Radiance Representation for Continuous Vision-Language Navigation](https://arxiv.org/pdf/2404.01943) | CVPR | 2024 | [Github](https://github.com/MrZihan/HNR-VLN) |
| | | [ETPNav: Evolving Topological Planning for Vision-Language Navigation in Continuous Environments](https://arxiv.org/abs/2304.03047v2) | PAMI | 2024 | [Github](https://github.com/MarSaKi/ETPNav?tab=readme-ov-file) |
| | | [Narrowing the Gap between Vision and Action in Navigation](https://www.arxiv.org/abs/2408.10388) | MM | 2024 | - |
| | | [Bridging the Gap Between Learning in Discrete and Continuous Environments for Vision-and-Language Navigation](https://arxiv.org/abs/2203.02764) | CVPR | 2022 | [Github](https://github.com/YicongHong/Discrete-Continuous-VLN) |
| | | [Beyond the Nav-Graph: Vision-and-Language Navigation in Continuous Environments](https://arxiv.org/abs/2004.02857) | ECCV | 2020 | [Github](https://github.com/jacobkrantz/VLN-CE) |
| | LLM/VLM (Zero-shot) | [LLM as Copilot for Coarse-grained Vision-and-Language Navigation](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/00833.pdf) | ECCV | 2024 | - |
| | | [Discuss Before Moving: Visual Language Navigation via Multi-expert Discussions](https://ieeexplore.ieee.org/abstract/document/10611565) | ICRA | 2024 | [Github](https://github.com/LYX0501/DiscussNav) |
| | | [MapGPT: Map-Guided Prompting with Adaptive Path Planning for Vision-and-Language Navigation](https://arxiv.org/abs/2401.07314) | ACL | 2024 | [Github](https://chen-judge.github.io/MapGPT/) |
| | | [MC-GPT: Empowering Vision-and-LanguageNavigation with Memory Map and Reasoning Chains](https://arxiv.org/pdf/2405.10620) | - | 2024 | - |
| | | [InstructNav: Zero-shot System for Generic Instruction Navigation in Unexplored Environment](https://arxiv.org/pdf/2406.04882) | - | 2024 | [Github](https://github.com/LYX0501/InstructNav) |
| | | [NavGPT: Explicit Reasoning in Vision-and-Language Navigation with Large Language Models](https://arxiv.org/abs/2305.16986) | AAAI | 2024 | [Github](https://github.com/GengzeZhou/NavGPT) |
| | | [March in Chat: Interactive Prompting for Remote Embodied Referring Expression](https://openaccess.thecvf.com//content/ICCV2023/papers/Qiao_March_in_Chat_Interactive_Prompting_for_Remote_Embodied_Referring_Expression_ICCV_2023_paper.pdf) | ICCV | 2023 | [Github](https://github.com/YanyuanQiao/MiC) |
| | | [Vision and Language Navigation in the Real World via Online Visual Language Mapping](https://arxiv.org/pdf/2310.10822) | - | 2023 | - |
| | | [A2Nav: Action-Aware Zero-Shot Robot Navigation by Exploiting Vision-and-Language Ability of Foundation Models](https://peihaochen.github.io/files/publications/A2Nav.pdf) | NeurIPS Workshop | 2023 | - |
| | | [CLIP-Nav: Using CLIP for Zero-Shot Vision-and-Language Navigation](https://arxiv.org/pdf/2211.16649) | - | 2022 | - |
| | LLM/VLM (Fine-tuning) | [EvolveNav: Self-Improving Embodied Reasoning for LLM-Based Vision-Language Navigation](https://arxiv.org/pdf/2506.01551) | Arxiv | 2025 | [Github](https://github.com/expectorlin/EvolveNav) |
| | | [LangNav: Language as a Perceptual Representation for Navigation](https://aclanthology.org/2024.findings-naacl.60.pdf) | NACCL Findings | 2024 | [Github](https://github.com/pbw-Berwin/LangNav) |
| | | [NavCoT: Boosting LLM-Based Vision-and-Language Navigation via Learning Disentangled Reasoning](https://arxiv.org/abs/2403.07376) | - | 2024 | [Github](https://github.com/expectorlin/NavCoT) |
| | | [Towards Learning a Generalist Model for Embodied Navigation](https://arxiv.org/abs/2312.02010) | CVPR | 2024 | [Github](https://github.com/LaVi-Lab/NaviLLM) |
| | | [NavGPT-2: Unleashing Navigational Reasoning Capability for Large Vision-Language Models](https://www.arxiv.org/abs/2407.12366) | ECCV | 2024 | [Github](https://github.com/GengzeZhou/NavGPT-2) |
| | | [NaVid: Video-based VLM Plans the Next Step for Vision-and-Language Navigation](https://arxiv.org/pdf/2402.15852) | RSS | 2024 | [Github](https://github.com/GengzeZhou/NavGPT-2) |
| **Behavior Analysis** | - | [Do Visual Imaginations Improve Vision-and-Language Navigation Agents?](https://arxiv.org/pdf/2503.16394) | CVPR | 2025 | - |
| | | [Navigating the Nuances: A Fine-grained Evaluation of Vision-Language Navigation](https://arxiv.org/pdf/2409.17313) | EMNLP Findings | 2024 | [Github](https://github.com/zehao-wang/navnuances) |
| | | [Behavioral Analysis of Vision-and-Language Navigation Agents](https://yoark.github.io/assets/pdf/vln-behave/vln-behave.pdf) | CVPR | 2023 | [Github](https://github.com/Yoark/vln-behave) |
| | | [Diagnosing Vision-and-Language Navigation: What Really Matters](https://aclanthology.org/2022.naacl-main.438.pdf) | NACCL | 2022 | [Github](https://github.com/VegB/Diagnose_VLN) |



## 后续工作

这里夸奖一下Gemini3和qwen的deep Research，真的救我狗命。

重点精读部分就看下面Gemini3提供的一份经过深度调研、严格筛选的 **2023–2025** 年间顶会（CVPR, ICCV, ECCV, ICLR, NeurIPS, CoRL, RSS, ICRA, IROS）**已接收 (Accepted)** 且 **已公开代码** 的 VLN / ObjectNav / Zero-Shot / LLM-assisted Navigation 相关论文列表。

| 会议 | 年份 | 标题 | 简介 | 代码 | 关键词 |
|:-----|:----:|:-----|:-----|:----:|:------|
| **CVPR** | 2025 | **UniGoal: Towards Universal Zero-shot Goal-oriented Navigation** | 提出了基于场景图（Scene Graph）和 LLM 的通用导航框架，统一了 Object, Image, Text 三种目标导航任务，解决 Zero-Shot 问题 | [GitHub](https://github.com/bagh2178/UniGoal) | Zero-Shot, Scene Graph, LLM, Universal Goal |
| | 2025 | **RoboSpatial: Teaching Spatial Understanding to 2D and 3D Vision-Language Models for Robotics** | 专注于提升 VLM 的空间理解能力，通过构建空间感知的指令微调数据集，大幅提升了机器人在 3D 环境中的导航和操作能力 | [GitHub](https://www.google.com/search?q=https://github.com/RoboSpatial/RoboSpatial) | Spatial Reasoning, VLM, Robotics |
| | 2024 | **Vision-and-Language Navigation via Causal Learning (VLN-GOAT)** | 引入因果推断（Causal Inference）消除数据偏差，提升 VLN 模型的泛化性 | [GitHub](https://github.com/CrystalSixone/VLN-GOAT) | Causal Learning, Deconfounding |
| | 2024 | **NaVid: Video-based VLM Plans the Next Step for Vision-and-Language Navigation** | 首个基于视频的大模型（Video-based VLM）端到端导航器，无需构建显式地图，直接从视频流规划动作 | [GitHub](https://github.com/jzhzhang/NaVid-VLN-CE) | Video VLM, Mapless, End-to-End |
| | 2024 | **AIGeN: An Adversarial Approach for Instruction Generation in VLN** | 利用对抗生成网络生成高质量的导航指令，用于数据增强 | [GitHub](https://www.google.com/search?q=https://github.com/jialuli-luka/AIGeN) | - |
| | 2023 | **Iterative Vision-and-Language Navigation (IVLN)** | 提出了"迭代式导航"新基准，要求机器人在同一环境中持续执行多条指令，考察记忆能力 | [GitHub](https://www.google.com/search?q=https://github.com/JacobKrantz/IVLN) | Continuous Navigation, Memory |
| | 2023 | **Improving Vision-and-Language Navigation by Generating Future-View Image Semantics (VLN-SIG)** | 通过生成未来视角的语义图像来辅助当前决策 | [GitHub](https://jialuli-luka.github.io/VLN-SIG) | - |
| **ICCV** | 2025 | **CogNav: Cognitive Process Modeling for Object Goal Navigation with LLMs** | 模拟人类认知过程（感知-推理-决策），利用 LLM 进行常识推理和空间推理，解决 ObjectNav 问题 | [Project Page & Code](https://yhancao.github.io/CogNav/) | Cognitive Modeling, LLM, ObjectNav |
| | 2023 | **Learning Vision-and-Language Navigation from YouTube Videos (YouTube-VLN)** | 利用大规模 YouTube 房屋导览视频进行预训练，学习真实世界先验 | [GitHub](https://github.com/JeremyLinky/YouTube-VLN) | - |
| | 2023 | **DREAMWALKER: Mental Planning for Continuous Vision-Language Navigation** | 引入"心理规划"机制，在执行前在潜在空间预演路径 | [GitHub](https://www.google.com/search?q=https://github.com/HanqingWangAI/DreamWalker) | - |
| **ECCV** | 2024 | **VLN-Copilot: LLM as Copilot for Coarse-grained Vision-and-Language Navigation** | 提出"副驾驶"概念，当导航智能体困惑时，LLM 提供详细的指导和推理辅助 | [GitHub](https://www.google.com/search?q=https://github.com/Zun-Wang/VLN-Copilot) | LLM Agent, Coarse-grained VLN |
| | 2024 | **NavGPT-2: Unleashing Navigational Reasoning Capability for Large Vision-Language Models** | 通过微调适配，激发通用多模态大模型（VLM）的导航推理能力 | [GitHub](https://www.google.com/search?q=https://github.com/WZMIAOMIAO/NavGPT-2) | - |
| **NeurIPS** | 2025 | **Vision-Language Navigation with Energy-Based Policy (ENP)** | 提出基于能量的模型（Energy-Based Model）来建模导航策略，更好地模拟专家轨迹分布 | [NeurIPS Page/GitHub](https://www.google.com/search?q=https://neurips.cc/virtual/2025/poster/93232) | - |
| | 2024 | **SG-Nav: Online 3D Scene Graph Prompting for LLM-based Zero-shot Object Navigation** | 构建在线 3D 场景图作为 Prompt，实现无需训练的 Zero-Shot 导航 | [GitHub](https://github.com/bagh2178/SG-Nav) | - |
| | 2024 | **InstructNav: Zero-shot Vision-and-Language Navigation with Instruction Tuning** | 这是一个通用的导航大模型框架，统一了 VLN 和 ObjectNav | (查看作者 Hao Dong 的 GitHub 或 Project Page) | - |
| | 2023 | **PanoGen: Text-Conditioned Panoramic Environment Generation for VLN** | 使用生成式模型根据文本生成全景环境，用于 VLN 的数据增强和训练 | [GitHub](https://github.com/jialuli-luka/PanoGen) | - |
| **CoRL** | 2025 | **GC-VLN: Graph-Constrained Vision-and-Language Navigation** | *UniGoal* 团队新作，将导航建模为图约束优化问题，无需训练即可在连续环境中导航 | [GitHub](https://github.com/bagh2178/UniGoal) | Training-free, Graph Constraints |
| | 2024 | **LeLaN: Learning a Language-Conditioned Navigation Policy from In-the-Wild Video** | 直接从野外（In-the-Wild）视频数据中学习语言条件的导航策略 | [Project Page](https://www.google.com/search?q=https://lelan-video.github.io/) | - |
| | 2024 | **OpenVLA: An Open-Source Vision-Language-Action Model** | 虽然主要针对操作（Manipulation），但其架构和预训练模型被大量用于导航任务的底座 | [GitHub](https://github.com/openvla/openvla) | - |
| | 2024 | **VLM-Grounder: A VLM Agent for Zero-Shot 3D Visual Grounding** | 利用 VLM 进行零样本 3D 视觉定位，是导航的关键前置任务 | [GitHub](https://www.google.com/search?q=https://github.com/desdemonawang/VLM-Grounder) | - |
| | 2023 | **OVSG: Context-Aware Entity Grounding with Open-Vocabulary 3D Scene Graphs** | 基于开放词汇 3D 场景图的实体定位与导航 | [GitHub](https://www.google.com/search?q=https://github.com/ovsg-code/ovsg) | - |
| **ICRA** | 2025 | **Open-Nav: Exploring Zero-Shot Vision-and-Language Navigation with Open-Source LLMs** | 探索使用 Llama 等开源模型替代 GPT-4 进行 Zero-Shot 导航，提出时空思维链 | [GitHub](https://github.com/YanyuanQiao/Open-Nav) | - |
| | 2025 | **MonoTransmotion** | 涉及单目视觉下的运动规划与导航 | [GitHub](https://github.com/vita-epfl/MonoTransmotion) | - |
| | 2024 | **VLFM: Vision-Language Frontier Maps for Zero-Shot Semantic Navigation** | 结合 CLIP 和前沿点（Frontier）地图，指导机器人探索语义目标 | [GitHub](https://github.com/bdaiinstitute/vlfm) | - |
| | 2023 | **VLMaps: Visual Language Maps for Robot Navigation** | 将 VLM 特征融合进 3D 地图，允许使用自然语言索引地图位置 | [GitHub](https://github.com/vlmaps/vlmaps) | - |
| **IROS** | 2024 | **LLM3: Large Language Model-based Task and Motion Planning** | 结合 LLM 进行任务和运动规划，虽然偏 TAMP，但也包含导航组件 | [GitHub](https://www.google.com/search?q=https://github.com/Zju-Robotics-Lab/LLM3) | - |
| **RSS** | 2025 | **Unified Video Action Model** | 统一的视频动作模型，涵盖导航和操作 | [Project Page/Code](https://github.com/jonyzhang2023/awesome-embodied-vla-va-vln) | - |
| | 2024 | **Consistency Policy: Accelerated Visuomotor Policies via Consistency Distillation** | 雖然偏向操作，但其 Policy 蒸馏方法正被用于加速导航策略 | [GitHub](https://www.google.com/search?q=https://github.com/DLR-RM/Consistency-Policy) | - |
| **ICLR** | 2024 | **AgentTrek: Agent Trajectory Synthesis via Guiding Replay with Web Tutorials** | 利用 Web 教程合成智能体轨迹，辅助导航和任务执行 | [GitHub](https://www.google.com/search?q=https://github.com/xduan7/AgentTrek) | - |
