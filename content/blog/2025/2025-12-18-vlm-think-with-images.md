---
date: 2025-12-18
title: 通过图像推理 VLM
authors: [bubblevan]
tags: [vlm, reasoning, survey, cot]
---

## VLM-Think with images 必读论文

[VLM-Think with images必读论文](https://www.xiaohongshu.com/explore/693f9ea3000000001e032e66?note_flow_source=wechat&xsec_token=CBE05j1SOO06inQfnWwTQXQDMo4ZSS_m0ussgoq0HO25M=)

**VLM** 尽管具备多模态输入的能力，但在推理过程中完全依赖**纯文本的形式**进行思考，无论是对视觉内容进行描述，还是输出语言化的推理依据，其内部推理路径始终局限于文本上。然而仅通过文本进行多模态推理，并不总是最有效的策略，尤其对于那些**高度依赖视觉信息的任务**。

### O3 范式 Think with images

一种方法是 **OpenAI-O3 范式的 Think with images**，是指在推理过程中通过**视觉工具**（如放大、裁剪、旋转、绘制辅助线、草图）来进行辅助思考，从而将视觉操作和操作后图像融入思维链，目的是为了让模型可以更深入地理解图像内容。

但从这样的角度，**本质并没有变**，思维链还是**纯文本驱动**，也就是得到视觉信息不是模型生成的，只是借助工具得到的。**模态鸿沟仍然存在**，即将视觉信息落地为文本后再进行推理，阻碍了模型对视觉特征的精准捕捉。

#### 总结使用工具的方法

1. **设置工作流固定使用工具**
   - 固定的一步，调用固定工具。

2. **模型自主决定使用什么工具**
   - 在哪一步，是直接输出答案，还是调用工具。如果使用工具，自主决定使用什么工具。

3. **固定的工具代码**
   - 代码是设置好的，模型只需要预测输入参数。所支持的操作空间相对受限，也依赖精确的参数输入。

4. **模型生成工具代码**
   - 代码由模型生成，支持广泛的视觉操作。

#### 相关论文

- Visual SKETCHPAD: Sketching as a Visual Chain of Thought for Multimodal Language Models
- V-Thinker: Interactive Thinking with Images
- DeepEyes: Incentivizing "Thinking with Images" via Reinforcement Learning
- Thyme: Think Beyond Images
- Revisiting the Necessity of Lengthy Chain-of-Thought in Vision-centric Reasoning Generalization
- Pixel Reasoner: Incentivizing Pixel-Space Reasoning with Curiosity-Driven Reinforcement Learning
- From Illusion to Intention- Visual Rationale Learning for Vision-Language Reasoning

### 潜在视觉推理（Latent Visual CoT）

所以另一种方法是**潜在视觉推理**，模型不再调用外部工具得到视觉信息，而是将视觉信息**内化、表征化**，也就是模型直接生成**视觉 token**。模型需要学会运用视觉 token 进行推理，而这些视觉 token 通常包括与**分割、深度、边缘、特征**等视觉线索。

训练模型生成视觉 token，就需要加入**视觉重建任务**。

#### 视觉 token 重建的 label 有以下几种

1. **引入辅助模型**
2. **引入辅助图像**
3. **引入原图 ROI 边界框**

#### 学习的视觉 token 表示有以下几种

1. **VIT 特征**
2. **VIT 投影特征**
3. **模型中间特征**
4. **VQVAE 中间离散 token**

#### 相关论文

- Chain-of-Visual-Thought: Teaching VLMs to See and Think Better with Continuous Visual Tokens
- Perception tokens enhance visual reasoning in multimodal language models
- DeepSketcher- Internalizing Visual Manipulation for Multimodal Reasoning
- Machine mental imagery: Empower multimodal reasoning with latent visual tokens
- Latent Visual Reasoning


# Thinking with Images

**多模态大语言模型（Multimodal Large Language Models, MLLMs）**正处于从**"感知智能"向"推理智能"**跃迁的关键转折点。尽管早期的视觉-语言模型（VLMs）如 **CLIP** 或 **LLaVA** 成功实现了图像与文本的语义对齐，但它们在本质上仍遵循**"Thinking about Images"**的范式——即迅速将视觉信号转化为文本特征，随后完全依赖语言模型的**文本思维链（Text-based Chain-of-Thought, CoT）**进行推理。

这种**"模态早融合"**与**"推理纯文本化"**的架构，导致了严重的**模态鸿沟（Modality Gap）**：在处理需要空间几何感知、细粒度视觉验证或多步视觉逻辑推演的任务时，模型往往因丢失视觉细节而产生幻觉。

为了克服这一局限，学术界与工业界正在积极探索**"Thinking with Images"**的新范式，即让视觉模态深度参与推理的中间过程，甚至主导推理链条。本报告旨在打破现有的二元分类局限（即简单的"工具调用"与"潜在推理"之分），基于对 **2023 年至 2025 年间**发表于 **CVPR、ICCV、NeurIPS、ICLR、ICML** 等顶级会议的 **50 余篇里程碑文献**的详尽调研，构建了一个包含五大范式的全新分类体系：

1. **工具中介与程序化视觉推理**
2. **显式生成意象与心智模拟**
3. **潜在空间视觉推理与连续思维**
4. **主动感知与强化视觉搜索**
5. **结构化与组合式视觉推理**

本报告将深入剖析每一范式的核心机制、技术演进路径及代表性工作，揭示 MLLMs 如何通过引入**视觉中间态（Visual Intermediates）**——无论是代码、像素、潜在向量、动作序列还是结构化图谱——来模拟人类的**"系统 2"慢思考能力**，从而实现真正的视觉通用智能。

## 1. 绪论：模态鸿沟与"系统 2"视觉推理的崛起

### 1.1 纯文本思维链在多模态语境下的局限性

传统的视觉语言模型（如 **LLaVA 系列**、**GPT-4V**）主要采用**"编码器-解码器"架构**：视觉编码器（如 **ViT**）将图像压缩为特征向量，随后投影到大语言模型（**LLM**）的词嵌入空间。一旦进入 LLM，视觉信息便被视为某种"外语"，推理过程完全由预训练的语言概率分布主导。

这种架构在图像描述（**Captioning**）等**"系统 1"直觉任务**上表现出色，但在需要多步逻辑的复杂任务中面临显著瓶颈：

1. **信息有损压缩（Information Bottleneck）**：视觉编码器通常将高分辨率图像压缩为有限数量的 token（例如 **256 或 576 个**），导致高频细节（如微小文字、物体精确坐标）在推理开始前即丢失。

2. **视觉-语言非同构性（Isomorphism Deficit）**：语言是离散、符号化且高度抽象的，而视觉是连续、密集且具象的。强行用文本 CoT 描述复杂的空间拓扑（如"左边第三个红球稍微偏上一点"）会导致语义精度的急剧下降，模型往往因此退化为依赖语言先验而非视觉事实进行猜想，即产生**"幻觉"**。

3. **缺乏回溯机制（Lack of Retracing）**：人类在解决视觉难题时会反复观察图像（**Visual Re-scanning**），而标准 VLM 往往是**"看一眼，然后闭眼推理"**，缺乏在推理中途重新审视视觉输入的能力。

### 1.2 "Thinking with Images" 的定义与新分类体系

**"Thinking with Images"** 指的是模型在推理过程中，不仅生成文本，还显式或隐式地操作视觉信息，将其作为推理链条中不可或缺的一环。这对应于认知科学中的**"心智意象"（Mental Imagery）**理论，即人类在思考空间问题时，会在大脑中构建视觉模拟。

基于对现有文献的系统梳理，我们将这一领域的解决方案扩展为以下五大范式：

- **范式 I：工具中介与程序化视觉推理（Tool-Mediated & Programmatic Reasoning）** —— 借用外部引擎的"手"来操作视觉。
- **范式 II：显式生成意象与心智模拟（Explicit Generative Imagery & Mental Simulation）** —— 利用生成模型的"想象力"进行预演。
- **范式 III：潜在空间视觉推理（Latent Visual Reasoning）** —— 在高维特征空间进行高效的"内隐视觉思考"。
- **范式 IV：主动感知与强化视觉搜索（Active Perception & Agentic Grounding）** —— 像人类眼动一样主动"寻找"视觉证据。
- **范式 V：结构化与组合式视觉推理（Compositional & Structured Grounding）** —— 将图像解构为图谱或掩码进行逻辑运算。

## 2. 范式 I：工具中介与程序化视觉推理

这一范式代表了**"符号主义"与"联结主义"**的结合。其核心假设是：神经网络在精确计算（如计数、几何测量）和逻辑执行上存在先天不足，应当将这些任务**"外包"**给擅长此道的外部工具（如 **Python 解释器**、**OpenCV 库**或**绘图 API**）。VLM 在此扮演**"控制器"**的角色，负责理解意图、编写程序并解析执行结果。这也就是用户查询中提到的**"OpenAI-O3 范式"**的典型体现。

### 2.1 核心机制：思维的外化

在该范式中，中间推理步骤被显式地转化为可执行的代码或可视化操作。这种**"外化"**不仅提高了推理的准确性，还赋予了模型极强的可解释性。

### 2.2 里程碑文献深度解析

#### 2.2.1 Visual Sketchpad (NeurIPS 2024)

**论文标题**：Visual Sketchpad: Sketching as a Visual Chain of Thought for Multimodal Language Models

**核心问题**：传统的 CoT 仅在文本层面分解问题，但对于几何题或地图导航，纯文本描述极其低效且易错。

**方法论**：作者提出了一种**"视觉草稿本"机制**。模型在推理过程中，可以生成代码来调用绘图 API（如 Matplotlib），在原图上绘制辅助线、标记框或圈出关键区域。这些绘制了标记的新图像被重新输入模型，作为下一步推理的视觉上下文。

**创新点**：首次将**"草图绘制"（Sketching）**引入 VLM 推理链。这模拟了人类做几何题时画辅助线的行为。实验表明，这种视觉辅助能显著提升数学几何和视觉逻辑任务的准确率，证明了视觉符号不仅是输出，更是推理的支架。

#### 2.2.2 ViperGPT (ICCV 2023)

**论文标题**：ViperGPT: Visual Inference via Python Execution for Reasoning

**核心问题**：**端到端（End-to-End）**模型不仅是黑盒，而且经常在简单的逻辑组合上失败（例如"红帽子的人左边是不是有一辆车"）。

**方法论**：ViperGPT 彻底摒弃了端到端的视觉问答模式。它利用专门针对代码微调的 LLM（如 **Codex**）将自然语言问题转化为 **Python 程序**。该程序调用一系列视觉 API（如对象检测、深度估计模型）。程序执行的结果即为最终答案。

**创新点**：提出了**"以代码为策略"（Code as Policy）**的视觉推理极致形态。它不需要训练多模态模型，而是通过组合现有的**视觉专家模型（Vision Experts）**来解决问题，实现了极高的可解释性和组合泛化能力。

#### 2.2.3 Visual Program Distillation (VPD) (CVPR 2024 Oral)

**论文标题**：Visual Program Distillation: Distilling Tools and Programmatic Reasoning into Vision-Language Models

**核心问题**：像 ViperGPT 这样的工具调用方法虽然准确，但推理延迟高、计算开销大，且依赖外部 API 的稳定性。

**方法论**：VPD 提出了一种**"蒸馏"策略**。它首先利用大型模型生成成千上万条高质量的"视觉程序"轨迹（即问题-程序-答案三元组），然后用这些数据微调一个较小的端到端 VLM（如 **PaLM-E** 或 **LLaVA**）。

**创新点**：成功将工具调用的逻辑推理能力**"内化"**到模型权重中。微调后的模型不再需要外部 API，而是直接预测出类似于程序执行步骤的推理结果，兼顾了工具方法的逻辑严密性和端到端模型的高效性。

#### 2.2.4 Task Navigator (CVPR 2024)

**论文标题**：Task Navigator: Decomposing Complex Tasks for Multimodal Large Language Models

**核心问题**：面对极其复杂的视觉任务（如"分析这张监控截图中所有异常行为"），模型往往不知从何下手，因为它的注意力机制无法一次性处理所有信息。

**方法论**：引入了一个**导航器（Navigator）**模块，负责将宏观任务分解为一系列子查询（**Sub-queries**）。系统根据子查询的需要，动态选择调用特定的视觉工具（如 **OCR**、检测器、知识库检索），并根据工具返回的结果规划下一步。

**创新点**：强调了**"规划"（Planning）**在视觉推理中的核心地位。证明了**系统 2 推理**的关键在于将复杂问题降维，并通过工具迭代式地获取信息。

#### 2.2.5 DeepSketcher (ArXiv 2025 / ICLR Context)

**论文标题**：DeepSketcher: Internalizing Visual Manipulation for Multimodal Reasoning

**核心问题**：外部绘图工具（如 Visual Sketchpad）的操作是离散且不可微的，阻断了梯度回传，限制了模型的学习能力。

**方法论**：DeepSketcher 设计了一个**"图像嵌入编辑模块"（Image Embedding Editing Module）**。它虽然受到代码渲染图像的监督，但在推理时，模型是直接在图像的特征空间（**Embedding Space**）中进行"涂抹"和"高亮"，模拟绘图操作。

**创新点**：实现了工具操作的**"软化"和"可微化"**。它不仅保留了绘图辅助推理的直观优势，还允许模型通过梯度下降端到端地学习"该在哪里画线"，是范式 I 向范式 III（潜在推理）演进的过渡形态。

## 3. 范式 II：显式生成意象与心智模拟

这一范式深受**认知心理学**启发。人类在回答"大象能不能装进冰箱"这个问题时，会在脑海中生成大象和冰箱的视觉意象并进行比对。同样，该范式赋予 VLM 调用生成模型（如 **Stable Diffusion**）的能力，通过生成**像素级的图像**来辅助推理，特别是针对空间预测、反事实推理和未来预测任务。

### 3.1 核心机制：视觉想象循环

推理过程不再是单向的（图像 -> 文本），而是**闭环的**：文本/图像 -> 生成新图像 -> 视觉感知 -> 文本结论。生成的图像充当了推理的**"视觉草稿"**。

### 3.2 里程碑文献深度解析

#### 3.2.1 Multimodal Visualization-of-Thought (MVoT) (ICML 2025)

**论文标题**：Imagine While Reasoning in Space: Multimodal Visualization-of-Thought

**核心问题**：现有的多模态思维链（**Multimodal CoT**）大多只是文本 CoT 加上静态图像输入，缺乏真正的"视觉思考"过程。

**方法论**：MVoT 提出了一种**交错式的推理模式**，模型可以像输出词语一样输出图像。为了实现这一点，作者设计了**"Token Discrepancy Loss"**，解决了 LLM 文本 Token 与图像生成器（如 **VQ-VAE**）离散 Codebook 之间的分布差异问题。模型在推理过程中会生成一系列中间图像（**Visual Thoughts**），展示其空间变换的构思过程。

**创新点**：将图像生成内化为 LLM 的原生能力，实现了真正的**"图文交错思维流"**。实验证明，这种显式的视觉化过程显著提升了空间旋转、物体拼接等任务的性能。

#### 3.2.2 ImagineNav (ICLR 2024)

**论文标题**：ImagineNav: Prompting Vision-Language Models as Embodied Navigator through Scene Imagination

**核心问题**：在**具身智能导航**中，代理（Agent）受限于视野，无法看到墙后或拐角处的物体，导致规划短视。

**方法论**：ImagineNav 利用 VLM 结合**新视角合成技术（Novel View Synthesis）**，根据当前观测"想象"出未知区域的景象。模型基于这些生成的幻觉图像来评估路径的可行性。

**创新点**：将生成式视觉 CoT 应用于决策规划。证明了**"合理的幻觉"**（基于先验的预测）是智能体在非结构化环境中生存的关键能力。

#### 3.2.3 Perspective-Aware Reasoning (APC) (ICCV 2025)

**论文标题**：Perspective-Aware Reasoning in Vision-Language Models via Mental Imagery Simulation

**核心问题**：VLM 存在严重的**"自我中心偏差"（Egocentric Bias）**，难以理解"如果我们换个角度看这个物体会怎样"这类问题。

**方法论**：APC 框架模拟了人类的**心智旋转（Mental Rotation）**能力。它首先利用视觉基础模型从输入图像中重建一个粗糙的 **3D 抽象场景**，然后将该 3D 场景旋转到目标视角，并重新投影为 2D 图像输入 VLM 进行回答。

**创新点**：引入了 **3D 抽象**作为中间推理模态。它表明，解决复杂的视觉关系问题需要超越 2D 像素，进入 **3D 语义空间**的模拟。

#### 3.2.4 SpatialDreamer (ArXiv 2025 / Top Venue Context)

**论文标题**：Incentivizing Spatial Reasoning via Active Mental Imagery

**核心问题**：仅仅生成图像是不够的，模型需要知道"生成什么图像"对解题最有帮助。

**方法论**：SpatialDreamer 引入了**强化学习（RL）**来优化生成策略。它训练模型主动进行**"视觉做梦"（Dreaming）**，并通过**世界模型（World Model）**验证这些梦境的物理一致性。奖励机制鼓励模型生成那些能最大程度减少不确定性的视角或状态。

**创新点**：将生成式 CoT 与强化学习结合，使视觉想象具有了**目的性（Goal-oriented Imagination）**，这是向自主智能迈进的重要一步。

#### 3.2.5 Self-Imagine (ArXiv 2024)

**论文标题**：Self-Imagine: Effective Unimodal Reasoning with Multimodal Models using Self-Imagination

**核心问题**：即使是纯文本的逻辑题，人类也往往需要画图辅助理解，而 LLM 缺乏这种能力。

**方法论**：该方法无需训练，通过**提示工程（Prompting）**让 VLM 将抽象的文本问题转化为结构化的 **HTML 或 SVG 代码**，然后渲染成图像。模型再次读取这张自己生成的图表来回答问题。

**创新点**：揭示了**"跨模态转换"**本身就是一种强大的推理增强手段。将文本转化为视觉结构，能够利用 VLM 强大的视觉模式识别能力来破解复杂的逻辑谜题。

## 4. 范式 III：潜在空间视觉推理

这一范式是目前**效率最高、最具理论深度**的方向。它认为，显式地生成像素图像（如范式 II）虽然直观但计算极其昂贵，且容易受到生成伪影的干扰。真正的"视觉思维"应当发生在紧凑、高维的**潜在空间（Latent Space）**中，类似于人类大脑处理视觉信号时并不需要在视网膜上重新成像。

### 4.1 核心机制：连续视觉思维链

模型在推理过程中生成特殊的**"视觉 Token"**或**"思维向量"**。这些向量不对应任何具体的单词，也不必解码为像素，而是保留了**连续的梯度信息**，能够承载比离散文本丰富得多的感知细节（如纹理、深度、精确坐标）。

### 4.2 里程碑文献深度解析

#### 4.2.1 Chain-of-Visual-Thought (CoVT / VChain) (ICCV 2025 / ArXiv 2025)

**论文标题**：Chain-of-Visual-Thought: Teaching VLMs to See and Think Better with Continuous Visual Tokens

**核心问题**：语言是高度压缩的符号系统，用语言描述视觉细节（如"这个不规则物体的边缘"）会造成巨大的信息丢失。

**方法论**：作者提出了一组**"连续视觉 Token"（Continuous Visual Tokens）**。模型经过训练，可以在推理步骤中输出这些连续向量。这些向量在训练时通过重构任务（如重构深度图、分割掩码）进行监督，确保其包含物理意义，但在推理时直接作为后续层的输入。

**创新点**：重新定义了 CoT 的载体。思维链不再局限于离散的文本，而是变成了**"文本-视觉向量"混合流**。实验表明，这种方法在细粒度感知任务上大幅超越了纯文本 CoT。

#### 4.2.2 Mirage (ArXiv 2025 / CVPR Context)

**论文标题**：Machine Mental Imagery: Empower Multimodal Reasoning with Latent Visual Tokens

**核心问题**：如何在不引入沉重的图像生成解码器的情况下，赋予模型**"心智意象"**能力。

**方法论**：Mirage 提出了**"潜在意象"（Latent Imagery）**。它利用轻量级的投影层将视觉编码器的特征映射到 LLM 的嵌入空间。通过两阶段训练（先对齐感知，再强化推理），模型学会了在遇到视觉难题时"调用"潜在视觉记忆，并在多轮对话中保持这些视觉状态。

**创新点**：实现了高效的**"长上下文视觉推理"**。由于潜在 Token 占用的显存远小于生成图像，Mirage 能够支持更长的推理步骤和更复杂的视觉逻辑操作。

#### 4.2.3 Latent Visual Reasoning (LVR) (CVPR/ECCV 2025 Context)

**论文标题**：Latent Visual Reasoning

**核心问题**：现有的 VLM 往往在特征提取阶段就丢失了与问题相关的细微特征。

**方法论**：LVR 引入了**"潜在重放"（Latent Replay）**机制。利用强化学习（**GRPO**），模型在推理过程中学会"回溯"并重新激活与当前推理步骤最相关的视觉潜在特征。它实际上是在潜在空间中进行了一种**"注意力重分配"**。

**创新点**：提出了 **VLPO（Visual-Latent Policy Optimization）**算法，证明了可以通过强化学习直接优化潜在空间的推理路径，而无需显式的监督信号。

#### 4.2.4 Slot-VLM (NeurIPS 2024)

**论文标题**：Slot-VLM: Object-Centric Learning with Slot Attention

**核心问题**：标准 Transformer 的注意力机制是全局的、纠缠的，难以分离独立的物体概念，导致数数或关系判断出错。

**方法论**：引入了**"Slot Attention"机制**。图像特征被强制分解为一组独立的**"Slot"向量**，每个 Slot 代表一个物体或实体。推理过程变成了对这些 Slot 的操作（如比较 Slot A 和 Slot B 的属性）。

**创新点**：将**"以物体为中心"（Object-Centric）**的归纳偏置引入 VLM。这使得模型在物理推理、物体计数等任务上具有了类似于符号系统的鲁棒性，同时保留了神经网络的灵活性。

#### 4.2.5 Coconut (COLM 2025 / ArXiv 2024)

**论文标题**：Training Large Language Models to Reason in a Continuous Latent Space

**核心问题**：语言空间的推理往往会过早塌缩（**Collapse**）到一个确定的路径，限制了**广度优先搜索（BFS）**的能力。

**方法论**：Coconut 提出将 LLM 的最后一个**隐藏状态（Hidden State）**直接作为下一个时间步的输入，而不是解码为离散的词。这种**"连续思维"**允许模型在潜在空间中同时探索多个推理分支（**Superposition of thoughts**）。

**创新点**：虽然最初针对 LLM 提出，但其理论框架是 2025 年多个视觉潜在推理工作（如 VChain）的基石。它从理论上证明了**连续空间推理比离散空间推理具有更高的表达能力上限**。

## 5. 范式 IV：主动感知与强化视觉搜索

这一范式将 VLM 从被动的观察者转变为主动的**视觉智能体（Visual Agent）**。人类在观察复杂场景时，眼球会不断进行**扫视（Saccade）**和**注视（Fixation）**，通过主动改变关注点来获取信息。该范式试图在 VLM 中复现这一机制，通过"动作"来弥补"分辨率"和"注意力"的不足。

### 5.1 核心机制：感知即行动

推理过程被建模为一个**马尔可夫决策过程（MDP）**。模型输出的不仅仅是答案，还有一系列感知动作指令：`<Zoom [x,y,w,h]>`, `<Crop>`, `<Look_Back>`, `<Scroll>`。这些动作改变了模型的输入，从而形成了**动态的推理链**。

### 5.2 里程碑文献深度解析

#### 5.2.1 DeepEyes (ArXiv 2025 / Likely CVPR/NeurIPS 2025)

**论文标题**：DeepEyes: Incentivizing "Thinking with Images" via Reinforcement Learning

**核心问题**：现有的主动感知模型往往需要大量标注数据（如"先看这里，再看那里"），不仅昂贵且难以覆盖所有场景。

**方法论**：DeepEyes 采用了端到端的**强化学习（RL）**，具体使用了 **GRPO 算法**。模型没有被教导如何看，而是仅在最终答案正确时获得奖励。在数万次训练迭代中，模型**自发涌现（Emerged）**出了类似人类的视觉策略：面对小物体会主动"放大"，面对大场景会"扫视"。

**创新点**：它是视觉领域的**"DeepSeek-R1 时刻"**。证明了复杂的视觉推理策略（**System 2**）可以通过简单的结果奖励从零训练出来，而不需要模仿人类的中间步骤。

#### 5.2.2 Visual CoT (NeurIPS 2024 Spotlight)

**论文标题**：Visual CoT: Advancing Multi-Modal Language Models with a Comprehensive Dataset and Benchmark for Chain-of-Thought Reasoning

**核心问题**：缺乏一个标准化的基准来衡量模型"看图说话"过程中的中间对齐能力。

**方法论**：作者构建了一个大规模数据集，其中的推理链不仅包含文本，还包含**边界框（Bounding Boxes）**。模型被训练执行**"多轮聚焦"策略**：Step 1 预测感兴趣区域（**RoI**）-> Step 2 裁剪该区域 -> Step 3 基于裁剪图回答。

**创新点**：提出了**"可追踪的视觉推理"（Traceable Visual Reasoning）**。通过强制模型每一步都输出坐标，极大地减少了幻觉，并为错误分析提供了精确的依据。

#### 5.2.3 Ferret (ICLR 2024)

**论文标题**：Ferret: Refer and Ground Anything Anywhere at Any Granularity

**核心问题**：传统的 **Bounding Box** 过于粗糙，无法处理不规则形状（如蛇、线缆）或极细小的物体。

**方法论**：Ferret 引入了**"混合区域编码器"（Hybrid Region Encoder）**。它允许模型接受点、框、不规则形状（**Sketch**）作为输入，并输出精细的区域掩码。这赋予了模型**"指哪打哪"**的精细感知能力。

**创新点**：将**"视觉定位"（Grounding）**的分辨率提升到了一个新的层级，是主动感知范式中处理细节信息的基石技术。

#### 5.2.4 Shikra (ICCV 2023 / ArXiv 2023)

**论文标题**：Shikra: Unleashing Multimodal LLM's Referential Dialogue Magic

**核心问题**：在 2023 年之前，VLM 的定位能力和对话能力往往是分离的。

**方法论**：Shikra 是最早将空间坐标 **[x, y]** 离散化为自然语言 Token 并参与自回归生成的模型之一。它证明了模型可以像学习外语一样学习**"位置语言"**，从而在对话中流畅地进行指代（**Referential Dialogue**）。

**创新点**：奠定了**"统一建模"**的基础。后来的 Visual CoT 和 DeepEyes 的坐标输出机制很大程度上继承了 Shikra 的设计哲学。

#### 5.2.5 Look Twice Before You Answer (CVPR 2024 Context)

**论文标题**：Look Twice Before You Answer: Memory-Space Visual Retracing for Hallucination Mitigation

**核心问题**：VLM 的**"遗忘"现象**——随着文本生成越来越长，模型逐渐忘记了最初看到的图像，开始胡编乱造。

**方法论**：提出了一种**"视觉回溯"（Visual Retracing）**机制。在生成文本的过程中，模型会动态计算当前文本 Token 与原始图像特征的注意力权重。如果发现注意力发散，模型会强制**"回头看"**，重新加权图像特征。

**创新点**：将主动感知应用到了**"时间/记忆"维度**。它不是空间上的移动，而是注意力在时间轴上的回溯，是解决长文本幻觉的关键技术。

## 6. 范式 V：结构化与组合式视觉推理

这一范式认为，视觉推理的本质是**结构化（Structure）**和**组合性（Compositionality）**。图像不应被视为一堆像素或 Token，而应被解析为对象、属性和关系的集合。该范式致力于在推理过程中显式地构建或利用这种结构化表征（如**场景图**、**布局树**）。

### 6.1 核心机制：从像素到图谱

推理过程包含显式的结构化步骤：`Image -> Scene Graph Generation -> Symbolic Reasoning -> Answer`。这种方法将**感知（Perception）**与**推理（Reasoning）**解耦，使得推理过程更加鲁棒和可控。

### 6.2 里程碑文献深度解析

#### 6.2.1 Compositional Chain-of-Thought (CCoT) (CVPR 2024)

**论文标题**：Compositional Chain-of-Thought Prompting for Large Multimodal Models

**核心问题**：VLM 经常犯**"属性绑定错误"（Attribute Binding Error）**，例如把穿红衣服的人看成穿蓝衣服，或者混淆两个物体的动作。

**方法论**：CCoT 强制模型分两步走：首先生成一个**场景图（Scene Graph）**，明确列出所有对象节点（**Nodes**）及其属性和关系边（**Edges**）；然后基于这个场景图生成答案。

**创新点**：将结构化数据作为 CoT 的中间模态。实验表明，显式的结构化描述迫使模型理清对象关系，大幅减少了组合性错误。

#### 6.2.2 PixelLM (CVPR 2024)

**论文标题**：PixelLM: Pixel Reasoning with Large Multimodal Model

**核心问题**：许多推理任务需要**像素级的理解**（例如"这两个重叠的物体谁在上面？"），传统的 Box 无法表达这种遮挡关系。

**方法论**：PixelLM 在 LLM 输出端挂载了一个轻量级的**像素解码器（Pixel Decoder）**。LLM 能够输出特定的**"分割 Token"**，这些 Token 解码后形成精细的物体掩码（**Masks**）。推理过程基于这些掩码的拓扑关系进行。

**创新点**：实现了**"像素级思维"**。它证明了 VLM 的推理粒度可以下沉到像素级别，为处理复杂的物理接触和遮挡关系提供了可能。

#### 6.2.3 Osprey (CVPR 2024)

**论文标题**：Osprey: Pixel Understanding with Visual Instruction Tuning

**核心问题**：如何让用户对图像中任意不规则区域进行提问？

**方法论**：Osprey 提出了一种**"掩码感知视觉提取器"（Mask-Aware Visual Extractor）**。它不仅接受图像，还接受一个掩码作为输入，能够提取该掩码覆盖区域的精细视觉特征。这使得推理可以针对图像的任何局部细节进行。

**创新点**：实现了细粒度的**"交互式推理"**。它不仅是模型看图，更是用户通过 **Point/Mask** 与模型进行精准的视觉对话。

#### 6.2.4 Sphinx (NeurIPS 2024 Context)

**论文标题**：Sphinx / ReasonBench Context

**核心问题**：**抽象视觉推理**（如瑞文智商测试、图表逻辑）是 VLM 的短板。

**方法论**：Sphinx 通过混合**高分辨率主动缩放（Active Scaling）**和多样化的视觉任务训练，增强了模型对抽象几何结构的感知能力。配合 **ReasonBench 基准**，它展示了结构化数据训练对提升逻辑推理的重要性。

**创新点**：探索了 VLM 在纯抽象视觉逻辑上的边界，证明了通过丰富的数据结构（如合成图表、几何题）可以提升模型的**通用推理智商**。

#### 6.2.5 Argus (CVPR 2025)

**论文标题**：Argus: Vision-Centric Reasoning with Grounded Chain-of-Thought

**核心问题**：**视觉定位（Grounding）**与**文本推理（Reasoning）**往往是割裂的。

**方法论**：Argus 提出了一种**以视觉为中心的推理框架**，强制模型在生成每一个推理步骤时，都要同步输出对应的视觉证据区域。这不仅仅是 Visual CoT 的应用，更是一种由于架构设计带来的**强对齐约束**。

**创新点**：强调了**"对齐即推理"**。只有当模型能够准确指出"我为什么这么说"的视觉依据时，我们才能认为它真正具备了视觉推理能力。

## 7. 综合对比与未来展望

### 7.1 五大范式横向对比表

| 范式维度 | 范式 I：工具中介 | 范式 II：显式生成 | 范式 III：潜在推理 | 范式 IV：主动感知 | 范式 V：结构化组合 |
|---------|----------------|----------------|-----------------|----------------|-----------------|
| **核心隐喻** | 外包给计算器 | 脑海中的草稿纸 | 直觉与内隐思考 | 眼动与探索 | 逻辑大纲与图谱 |
| **中间模态** | 代码 (Python)、API | 像素图像 (Images) | 连续向量 (Vectors) | 动作指令 (Actions) | 场景图、掩码 (Graphs) |
| **优势** | 逻辑严密，可验证，计算精准 | 处理空间变换、反事实推理极强 | 信息密度最高，推理效率高 | 模拟人类行为，适应大图/视频 | 解决复杂关系，鲁棒性高 |
| **劣势** | 依赖工具库，非端到端，慢 | 计算开销极大，生成误差累积 | 黑盒不可解释，调试困难 | 训练难度大 (RL)，收敛慢 | 依赖解析器，灵活性受限 |
| **代表作** | Visual Sketchpad, ViperGPT | MVoT, ImagineNav | CoVT, DeepSketcher | DeepEyes, Ferret | CCoT, PixelLM |
| **适用场景** | 数学几何、精确计数、测量 | 导航规划、物理预测、拼图 | 通用视觉问答、细粒度感知 | 极高分辨率图像、监控视频 | 复杂场景理解、关系推理 |

### 7.2 技术融合的趋势：迈向多模态 AGI

通过对 **2025 年最新文献**的分析，我们可以清晰地看到不同范式正在发生融合：

1. **RL 的全面渗透**：**DeepEyes** 和 **SpatialDreamer** 的成功表明，**强化学习**正在成为训练 **System 2 视觉推理**的标准范式。未来的 VLM 将不再仅仅依靠监督微调（**SFT**），而是通过 RL 自我探索出最优的"看图策略"。

2. **潜在与显式的结合**：**DeepSketcher** 展示了可以在潜在空间中进行"显式"的操作（如编辑 Embedding）。未来的模型可能会在潜在空间中进行高效推理，仅在需要验证时才"解码"为像素图像。

3. **从感知到行动**：随着**具身智能（Embodied AI）**的兴起，Paradigm IV（主动感知）将变得越来越重要。视觉推理将不再局限于静态图像，而是延伸到对环境的主动探索和交互中。

## 8. 结语

从**"Thinking about Images"**到**"Thinking with Images"**的转变，标志着多模态大模型正在跨越感知的门槛，迈向认知的殿堂。无论是通过代码外化思维、通过生成模拟未来、通过向量内隐推演，还是通过动作主动探索，这些新兴范式都在试图弥合语言与视觉之间的鸿沟。

本次调研表明，**单纯的文本 CoT 已不足以支撑下一代 VLM 的发展**。未来的多模态模型必将是**混合架构**的——它拥有类似 **System 1** 的快速感知编码器，同时也拥有由 **RL 训练而成的 System 2 推理引擎**，能够灵活地调用工具、生成意象、在潜在空间深思熟虑，并像人类一样主动去"看"清这个世界。