---
title: "多模态论文精读（一）VILA + NVILA系列"
---

## VILA: On Pre-training for Visual Language Models
> https://arxiv.org/abs/2312.07533

## 一、VLM的发展现状与研究缺口
### 1. 开篇核心定位
> “Visual language models (VLMs) rapidly progressed with the recent success of large language models.”  
- 解读：视觉语言模型（VLM）的快速发展，本质是依托于**大语言模型（LLM）的技术突破**（如LLaMA、GPT系列的指令跟随、零样本泛化能力）。VLM的核心是给LLM“加装视觉输入模块”，让模型同时理解图像和文本，从而处理图文联合任务（如图像问答、图文生成）。

### 2. 现有研究的局限
> “There have been growing efforts on visual instruction tuning to extend the LLM with visual inputs, but lacks an in-depth study of the visual language pre-training process, where the model learns to perform joint modeling on both modalities.”  
- 关键对比：  
  - 现有热点：多数研究聚焦于**视觉指令微调（Visual Instruction Tuning）**，即通过SFT（监督微调）、RLHF（基于人类反馈的强化学习）等方式，让已具备视觉输入能力的模型适配下游任务（如“描述这张图”“回答图中问题”）。  
  - 核心缺口：**缺乏对“视觉语言预训练阶段”的深入研究**——而这一阶段是VLM的“根基”：模型需要在该阶段学习“如何将视觉模态（图像）和语言模态（文本）进行联合建模”，实现两种独立预训练模型（LLM与视觉编码器）的“模态对齐”。


## 二、本文的三大核心研究发现
这是论文的核心贡献，通过“可控对比实验”（逐步调整预训练设计变量）得出，直接指导了后续VILA模型的构建：

### 发现1：LLM的“冻结/解冻”决定上下文学习能力
> “freezing LLMs during pre-training can achieve decent zero-shot performance, but lack in-context learning capability, which requires unfreezing the LLM”  
- 术语解释：  
  - 冻结LLM（Freezing LLM）：预训练时只训练“视觉-文本连接模块”（投影器），不更新LLM参数；  
  - 零样本性能（Zero-shot）：模型未见过某任务的训练数据，直接处理该任务的能力；  
  - 上下文学习（In-context Learning, ICL）：模型通过“少量示例（如4个样本）”快速适配新任务的能力（LLM的核心优势之一）。  
- 实验结论：  
  - 冻结LLM的优势：能获得“还不错的零样本性能”（因为投影器已初步对齐图文嵌入）；  
  - 冻结LLM的致命缺陷：**完全丢失上下文学习能力**（无法通过少量示例提升任务精度）；  
  - 解决方案：必须“解冻LLM”（预训练时同步更新LLM参数）——这能促进“视觉嵌入与文本嵌入的深层对齐”（论文后续通过余弦相似度验证：解冻后深层模态相似度更高），而深层对齐是上下文学习的关键。


### 发现2：交错图文数据是预训练的“最优数据格式”
> “interleaved pre-training data is beneficial whereas image-text pairs alone are not optimal”  
- 术语解释：  
  - 交错图文数据（Interleaved Data）：文本段落中穿插图像的格式（如“介绍番茄种植的文字→番茄图片→继续介绍黄瓜种植的文字→黄瓜图片”，示例来自论文的MMC4数据集）；  
  - 纯图文对（Image-text Pairs）：单张图像对应一句短描述的格式（如“猫的图片→‘一只黑色的猫’”，示例来自COYO数据集）。  
- 实验结论：  
  - 纯图文对的问题：仅用纯图文对预训练会导致“灾难性遗忘”——LLM原有的文本能力（如MMLU知识问答）大幅下降（准确率跌17.2%），且VLM任务的“4样本性能甚至低于零样本”（无上下文学习能力）；  
  - 交错数据的优势：  
    1. 文本能力保留更好（MMLU仅下降5.3%），因为其文本分布与LLM预训练数据（如C4 corpus）更接近；  
    2. VLM任务性能更强（零样本68.7%、4样本70.9%），且“数据结构比文本长度更关键”（即使将交错数据拆成纯图文对，性能也会暴跌）；  
  - 最优方案：混合“交错数据+纯图文对”，兼顾数据多样性与文本能力保留。


### 发现3：联合SFT修复文本性能，同时提升VLM精度
> “re-blending text-only instruction data to image-text data during instruction fine-tuning not only remedies the degradation of text-only tasks, but also boosts VLM task accuracy”  
- 术语解释：  
  - 联合SFT（Joint SFT）：在“视觉指令微调数据”（如图像问答数据）中，混入纯文本指令数据（如FLAN数据集的“总结这段文字”“解答数学题”）；  
  - 文本性能降解（Text Degradation）：即使使用交错数据预训练，LLM的纯文本任务精度仍会小幅下降（如MMLU降5.3%）。  
- 实验结论：  
  - 修复文本能力：混入1M纯文本指令后，VLM的MMLU准确率完全恢复（甚至13B模型略有提升），与纯文本LLM的SFT效果持平；  
  - 提升VLM性能：联合SFT后，VLM的4样本平均性能从71.3%提升至73.6%——因为纯文本指令增强了模型的“指令跟随能力”，而这对视觉任务同样重要。


## 三、本文的核心贡献（VILA模型）
> “With an enhanced pre-training recipe we build VILA, a Visual Language model family that consistently outperforms the state-of-the-art models, e.g., LLaVA-1.5, across main benchmarks without bells and whistles. Multi-modal pre-training also helps unveil appealing properties of VILA, including multi-image reasoning, enhanced in-context learning, and better world knowledge. VILA is also deployable on Jetson Orin for on-device VLM.”  
- 关键信息：  
  - 性能优势：基于上述“解冻LLM+交错数据+联合SFT”的预训练方案，VILA模型在12个视觉语言基准（如VQAv2、TextVQA、MM-Vet）上**持续超越当时的SOTA模型LLaVA-1.5**（如图1所示，VILA的VisWiz准确率60.6% vs LLaVA-1.5的53.6%，TextVQA准确率66.6% vs 61.3%）；  
  - 额外能力：预训练解锁了LLaVA-1.5没有的能力：  
    1. 多图像推理（即使SFT仅用单图数据，也能对比多图差异、找共性）；  
    2. 更强的上下文学习（OCR、艺术风格分类等任务中ICL准确率更高）；  
    3. 更优的世界知识（地标识别准确率100% vs LLaVA-1.5的50%）；  
  - 部署优势：可在边缘设备（如Jetson Orin）上运行，兼顾性能与实用性。


## 四、背景补充：VLM的架构与训练阶段
为理解上述发现，论文在“Background”部分铺垫了核心技术细节，是解读发现的基础：

### 1. 模型架构（聚焦自回归型VLM）
> “Multi-modal LLMs can be generally categorized into two settings: cross-attention-based and auto-regressive-based... auto-regressive VLMs consists of three components: a visual encoder, an LLM, and a projector... treat visual input as a foreign language.”  
- 架构分类：  
  - 交叉注意力型：冻结LLM，通过交叉注意力将视觉信息注入LLM中间层（如BLIP-2）；  
  - 自回归型（本文选择）：将图像通过“视觉编码器”（如CLIP-L）转化为“视觉token”，与文本token拼接后直接输入LLM（视为“外语token”），支持任意交错图文输入（如“文本→图像→文本”），灵活性更高。  
- 核心组件：  
  - 视觉编码器：将图像转化为视觉嵌入（如CLIP的ViT-L）；  
  - 投影器：连接视觉嵌入与LLM的文本嵌入（可选简单线性层或复杂Transformer块，论文发现“线性层效果更好”，因迫使LLM主动学习视觉处理）；  
  - LLM：核心文本理解与生成模块（如LLaMA-2）。

### 2. 三阶段训练流程
> “The training can be categorized into three stages: 0. Projector initialization; 1. Visual language pre-training; 2. Visual instruction-tuning.”  
| 阶段 | 核心目标 | 关键操作 |
|------|----------|----------|
| 0. 投影器初始化 | 初步对齐图文嵌入 | 冻结LLM和视觉编码器，仅用纯图文对（如COYO）训练投影器 |
| 1. 视觉语言预训练 | 深度模态联合建模 | 解冻LLM，用“交错数据+纯图文对”训练LLM+投影器（本文核心研究阶段） |
| 2. 视觉指令微调 | 适配下游任务 | 将视觉数据集转化为FLAN风格指令（如“问题：图中有几只猫？答案：2只”），进行SFT；本文在此阶段加入“联合SFT”（混入纯文本指令） |

### 3. 评估指标
> “We evaluate the fine-tuned model on 4 visual language tasks: accuracy for OKVQA and TextVQA, and CIDEr score for COCO and Flickr. We evaluate both 0-shot and 4-shot performance.”  
- 任务选择：覆盖“视觉问答”（OKVQA需外部知识、TextVQA需OCR）和“图像 caption生成”（COCO、Flickr）；  
- 性能维度：零样本（反映泛化能力）、4样本（反映上下文学习能力），两者结合能全面衡量VLM的实用性。

