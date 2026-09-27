---
title: "L17 · Multimodal"
weight: 17
date: 2026-09-01
updated: 2026-09-16
course: "CS336"
topics: ["CS336", "multimodal", "vision-language", "vlm", "omni-model"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture17/
---

前 16 讲一直围绕 language model 展开：输入 token，输出 token。Lecture 17 把问题扩展到现实世界的图像、视频和其他模态：**怎样把非文本信息送进 Transformer，又怎样让模型生成非文本信息？**

最终目标是 omni model：

$$
\text{任意模态组合输入}
\longrightarrow
\text{统一模型}
\longrightarrow
\text{任意模态组合输出}
$$

多模态的核心并不是给 Transformer 额外接一个摄像头，而是决定什么可以被称为一个 token、如何保留空间和时间结构，以及理解任务与生成任务是否需要同一种表示。

![现实世界的多模态输入与输出](/learning/cs336/lectures/l17-multimodality.png)

## 1. Transformer 只会处理 token：视觉 token 从哪里来

文本经过 tokenizer 后得到离散 token，Transformer 接收的是 embedding 序列：

$$
X=(x_1,\ldots,x_T),\qquad x_i\in\mathbb{R}^d
$$

Transformer 并不知道向量原来来自文字。只要能把图片 \(I\in\mathbb{R}^{H\times W\times3}\) 变成：

$$
V=(v_1,\ldots,v_M),\qquad v_i\in\mathbb{R}^d
$$

就可以把它和文本 embedding 拼起来：

$$
[\text{text tokens},\text{visual tokens},\text{text tokens}]
$$

因此，视觉建模的第一步是把连续的像素或 patch 映射到 Transformer 能处理的 token-like representation。文本 tokenization 主要解决词和子词的离散化，视觉 tokenization 还要同时保留空间布局、局部细节、物体关系和分辨率信息。

## 2. ViT：把图片切成 patch 再做序列建模

Vision Transformer 的基本做法是把图片切成固定大小的 patch，把每个 patch flatten 后用一个 linear projection 映射到模型维度。以 \(224\times224\) 图片和 \(14\times14\) patch 为例：

$$
\frac{224}{14}=16,\qquad
M=16\times16=256
$$

每个 RGB patch 的原始维度是：

$$
14\times14\times3=588
$$

所以一张图片可以被表示成 256 个视觉 token，每个 token 由一个 \(588\to d\) 的线性层得到。之后加入二维位置编码，再送进标准 Transformer。

![ViT 将图片 patch 化为序列](/learning/cs336/lectures/l17-vit.png)

ViT 的关键抽象是：图片不再必须由卷积网络逐层处理，而可以像文本一样交给一个 sequence model。代价是 patch size 与分辨率直接决定 token 数：分辨率提高一倍，二维 patch 数量大约提高四倍，后续 attention、显存和上下文长度都会受到影响。

## 3. CLIP：先学图文对齐，再把视觉表示接到语言模型

CLIP 的问题是：能否利用海量 image-caption pair，而不是依赖每张图片的人工类别标签？它对一个 batch 中的图片和文本分别编码，然后要求正确配对的图文相似度高于其他错配组合。

若 batch 中有 \(B\) 个图文对，图像编码为 \(v_i\)，文本编码为 \(t_j\)，相似度矩阵可以写成：

$$
S_{ij}=\\frac{v_i^\top t_j}{\\|v_i\\|\\,\\|t_j\\|}
$$

训练时同时做 image-to-text 和 text-to-image 的对比分类：第 \(i\) 张图片应该匹配第 \(i\) 段文本，第 \(j\) 段文本也应该匹配第 \(j\) 张图片。

![CLIP 的图文对比学习](/learning/cs336/lectures/l17-clip.png)

原始 CLIP 使用约 4 亿 image-text pairs，典型 batch 可以达到 32768。图像侧尝试了 ResNet 和 ViT，最佳配置包括 ViT-L/14@336px；文本侧使用 GPT-2 风格 Transformer，约 63M 参数、12 层，并取 EOS 位置的高层表示。

CLIP 的 headline result 是 zero-shot ImageNet：不再为 ImageNet 类别训练一个专用 classifier，而是把类别名称写成文本，与图片 embedding 做相似度比较，也能达到接近甚至超过专门监督训练的 ResNet-50。

它的训练目标与“让模型描述图片”不同。直接 image-to-text prediction 要生成完整 caption，目标更细、计算也更贵；CLIP 只要求正确配对排序，因此用大量 noisy caption 学到稳定的语义对齐。

![CLIP 对比目标与 caption 目标的效率差异](/learning/cs336/lectures/l17-clip-efficiency.png)

但 CLIP 的表示主要被 image classification 目标塑形，偏向全局语义，不一定保留 OCR、细粒度空间关系和可生成细节。它解决了“图片如何进入语义空间”，没有解决“模型如何看图对话或生成图片”。

## 4. SigLIP：把全 batch 分类改成 pairwise sigmoid

CLIP 的 loss 把一个 batch 变成 \(B\)-way classification：每张图片要在所有文本中找正确项，loss 和全 batch 的负样本耦合，通常需要大 batch 与 full-batch softmax。

SigLIP 改成对每一个图文 pair 做二分类：这个 pair 是 aligned 还是 not aligned？目标可以抽象成：

$$
y_{ij}\in\{-1,+1\},\qquad
\ell_{ij}=\log\left(1+\exp(-y_{ij}s_{ij})\right)
$$

![SigLIP 的 pairwise sigmoid loss](/learning/cs336/lectures/l17-siglip-code.png)

这样不再要求全局归一化，batch size 与 loss 的耦合被解除，更适合分布式训练。SigLIP 使用 WebLI 的十亿量级图文数据，加入 OCR、质量筛选，并覆盖约 100 种语言。课程给出的效率对比是：CLIP 约用 256 个 TPUv3 训练 10 天，SigLIP 约用 32 个 TPUv4 训练 5 天，硬件 FLOP/s 还更低但整体更快。

SigLIP 在小于 16K 的 batch 上通常优于 CLIP；可以扩展到 1M batch，但实验显示约 32K 已经足够。这说明 loss 设计不只是数学形式变化，也会改变通信需求、有效负样本数量和可扩展性。

![SigLIP 的分布式训练方式](/learning/cs336/lectures/l17-siglip-parallelism.png)

## 5. LLaVA：视觉 encoder + projector + language model

CLIP/SigLIP 给出了视觉表示，但还需要把它注入能对话的语言模型。LLaVA 的结构非常直接：

$$
\text{image}
\xrightarrow{\text{CLIP}}
\text{visual features}
\xrightarrow{\text{projector}}
\text{LM embedding space}
\xrightarrow{\text{Vicuna}}
\text{text response}
$$

它使用 CLIP 作为 vision encoder，使用经过对话微调的 Vicuna 作为 text decoder，中间只放一个线性 projector \(W\)。projector 把视觉特征的维度映射到语言模型 embedding 维度。

![LLaVA 的视觉到语言架构](/learning/cs336/lectures/l17-llava-architecture.png)

数据是关键部分：先从 MS COCO 的图片、caption、bounding box 等信息出发，提示 GPT-4 生成问题、答案和对话，再把生成的文本与原图配对，得到约 158K examples。它说明 VLM 的能力不只来自 architecture，任务化、合成化的数据同样决定模型会不会解释图像。

训练分两阶段：

1. **Alignment**：冻结 vision encoder 和 language model，只训练 projector，让视觉表示进入 LM 的 embedding space。
2. **Fine-tuning**：继续冻结 vision encoder，训练 projector 与 language model，使模型学会视觉指令跟随和回答。

这个结构的好处是简单、可复用；限制是视觉 token 数、分辨率和视觉 encoder 的表示上限会直接传递到语言模型。

## 6. LLaVA-OneVision：高分辨率、多图和视频的统一接口

固定把任意图片 resize 到 \(336\times336\) 会损失小字体、表格、图表和 OCR 细节。AnyRes 的做法是把高分辨率图片切成多个与 vision encoder 匹配的 tile，分别编码后拼接；如果 token 太多，再用 bilinear interpolation 做压缩。

![AnyRes 将高清图片切成多个视觉区域](/learning/cs336/lectures/l17-llava-onevision-anyres.png)

OneVision 使用 SigLIP 视觉 encoder、Qwen2-72B 文本 decoder 和两层 MLP projector，并统一处理三类输入：

| 输入 | 主要策略 | 原因 |
| --- | --- | --- |
| 单图 | 使用更高分辨率 | 需要保留 OCR 和细节 |
| 多图 | 每张图使用 base resolution | 避免图片数量让 token 数爆炸 |
| 视频 | 每帧使用更低分辨率 | 帧数多，时间维度本身已经很长 |

![单图、多图和视频的视觉 token 预算](/learning/cs336/lectures/l17-llava-onevision-modalities.png)

它的训练哲学是 quality over quantity、easy to hard：先用容易稳定对齐的数据，再逐步加入更复杂的指令和交互任务。更有意思的是跨模态 transfer：单图 diagram/chart 数据可以迁移到多图 relational reasoning；单图 OCR 和多图关系数据可以帮助 GUI agent；单图 visual prompting 还可能迁移到视频。

这里的结论很 CS336：VLM 的主要工作往往不是再发明一个复杂模块，而是设计数据、控制视觉 token budget，并让不同 modality 的序列长度和任务难度处在可训练范围。

## 7. Qwen-VL：把视觉定位和多阶段训练纳入语言序列

Qwen-VL 仍然遵循 vision encoder + adaptor + language model 的模板，但更强调视觉定位和空间信息。它使用 OpenCLIP ViT-bigC，adaptor 是带二维位置编码的一层 cross-attention，并把视觉表示压到固定的 256 个 visual tokens。

特殊 token 让文本序列可以表达图像、引用和 bounding box 等对象。这样模型不仅回答“图中有什么”，还可以指出“它在哪里”，把 grounding 变成语言模型能够学习的序列任务。

Qwen-VL 的训练分三阶段：

1. 大规模、相对低质量的图文数据，冻结 LM，训练视觉 encoder 与 adaptor；
2. 更高质量、任务相关且分辨率更高的数据，训练全部参数；
3. instruction tuning，冻结视觉 encoder，训练 adaptor 与 LM。

![Qwen-VL 的三阶段训练](/learning/cs336/lectures/l17-qwen-vl-stages.png)

这套流程与前面课程中的 data curriculum、mid-training、post-training 同构：先学稳定的跨模态表示，再提高数据质量与任务 specificity，最后让模型适应真实交互。

## 8. Qwen2-VL：Dynamic Resolution 与 MRoPE

固定视觉 token 数简单，但会在低分辨率图片上浪费预算，在高分辨率图片上丢失细节。Qwen2-VL 使用更大的 675M vision encoder 和 dynamic resolution，根据输入图片尺寸分配视觉 token。

一个 \(224\times224\) 区域先以 ViT/14 编码，再每 \(2\times2\) 个视觉位置压缩成一个 token，得到约 66 tokens 的压缩表示。视频可以按约 2 frames/sec 采样，并设置最大约 16384 visual tokens 的预算。

二维视觉位置不能简单当成一条一维文本序列。Multimodal Rotary Position Embedding（MRoPE）将位置拆成 temporal、height、width 三个轴，让模型知道两个 patch 是相邻、上下关系，还是来自不同时间。

![Qwen2-VL 的 MRoPE 位置结构](/learning/cs336/lectures/l17-qwen2-vl-mrope.png)

Qwen2-VL 的启示是：dynamic resolution 本质上是视觉版 variable-length tokenization；MRoPE 则是把空间和时间结构显式写进 Transformer 的位置系统。两者共同解决“不同图片和视频应该占用多少序列长度、位置信息如何表达”的问题。

## 9. Qwen3-VL：把时间、损失和多层视觉注入一起建模

Qwen3-VL 将语言模型扩展到 Qwen3 dense 与 MoE 系列，最大模型达到 235B-A22B，并支持约 256K 长上下文。视觉侧采用 SigLIP-2，并继续沿用动态分辨率与 MRoPE。

它的几个重要升级是：

- **Interleaved MRoPE**：把 temporal、width、height 轴交错分配到不同频率，而不是先放完时间再放宽高，使长序列中的三种位置变化更均衡。
- **Explicit timestamps**：视频时间戳直接作为文本 token 输入，让模型在语言空间中学习时间对齐，而不只依赖位置编码。
- **DeepStack**：把视觉信息从 adapter 注入多个 Transformer layer，而不是只在输入端注入一次，帮助后续层保留细粒度视觉信息。
- **Visual token budget**：部署时限制每张图片或视频的 visual-token 数，直接控制上下文、延迟和成本。
- **Square-root-normalized per-token loss**：平衡文本与多模态数据，避免视频样本因为序列特别长而支配总 loss。

Qwen3-VL 的预训练也分阶段推进：先训练 adapter，再在 8K、32K、256K 长度上逐步训练更多参数；post-training 则加入长 CoT SFT、knowledge distillation 和 RL。

![Qwen3-VL 的多阶段预训练](/learning/cs336/lectures/l17-qwen3-vl-pretraining.png)

这把前面课程的多个主题重新串起来：长上下文要控制 token budget，MoE 与视觉 encoder 需要系统并行，数据 mixture 需要重视视频长度，RL 又需要可靠的多模态 evaluation。

## 10. 理解与生成需要不同的视觉表示

到目前为止，CLIP、SigLIP、LLaVA 和 Qwen-VL 都主要解决“看懂并回答”。它们的视觉 encoder 输出连续 representation，再交给语言模型生成文本。这样的表示适合语义理解，却不一定适合生成像素级细节。

可以把目标拆成两类：

| 目标 | 更关注什么 | 适合的表示 |
| --- | --- | --- |
| Comprehension | 语义、对象、关系、OCR、时间与空间 | 连续视觉特征 + LM |
| Generation | 纹理、布局、细节、像素一致性 | 连续 latent + diffusion 或专用 decoder |

这解释了为什么现代 omni model 常见的路线是 continuous encoder + Transformer + diffusion decoder：Transformer 负责跨模态语义与规划，diffusion 或其他生成器负责把语义还原成细粒度视觉或音频信号。

如果强行让同一个 representation 同时承担语义压缩和像素重建，就会遇到一个基本 trade-off：压得越紧，语言模型越容易处理，但细节损失越大；保留越多，生成质量可能更高，但上下文、计算和训练稳定性成本也更高。

## 11. Chameleon：把图像也离散成 token

Chameleon 选择另一条更统一的路线：既然文本是 discrete token，就把图片也离散化，再用同一个 autoregressive Transformer 建模和生成。

它使用 VQ-VAE 把图片映射到离散 codebook：

$$
\text{image}
\xrightarrow{\text{encoder}}
\text{code indices}
\xrightarrow{\text{decoder}}
\widehat{\text{image}}
$$

VQ-VAE 通过重建损失和 codebook 学习，让 \(512\times512\) 图片被编码成约 1024 个离散视觉 token，codebook 大小约为 8192；之后再训练新的 BPE tokenizer，让文本和视觉离散 token 能进入同一个序列模型。

![Chameleon 的 mixed-modal early fusion](/learning/cs336/lectures/l17-chameleon.png)

![VQ-VAE 将图片映射为离散 codebook token](/learning/cs336/lectures/l17-vq-vae.png)

它的优势是统一：同一个 autoregressive model 可以理解 text/image 混合序列，也可以生成图片 token。缺点是 quantization 会造成 information loss，尤其是 OCR、细线条和精细空间关系；而且文本 token 的 entropy 通常低于图像 token，多模态混合训练容易出现 norm growth 和 logit drift。

Chameleon 的稳定化方法包括 QK norm 和 z-loss regularization。训练数据也分阶段：第一阶段约占 80%，混合 2.9T text tokens、1.5T text/image tokens 和 400B interleaved tokens；第二阶段约占 20%，一半沿用阶段一数据，一半加入高质量数据。

因此 Chameleon 很优雅，但未必是最强的实际路线：统一的 discrete token 让生成变得自然，却把视觉细节损失和多模态 entropy 差异直接暴露给 autoregressive training。

## 12. 把 Lecture 17 串回 CS336 的主线

可以用三层 mental model 总结视觉语言模型：

$$
\text{Modality Encoder}
\rightarrow
\text{Projector / Adapter}
\rightarrow
\text{Language Model}
$$

第一层负责把图片、视频或音频压缩成连续或离散表示；第二层负责维度、空间、时间和 token budget 对齐；第三层负责跨模态推理、指令跟随和长上下文建模。若要生成非文本，后面还需要 diffusion 或其他 modality decoder。

Lecture 12 的 evaluation 决定要测 OCR、chart reasoning、grounding、视频时间关系还是生成质量；Lecture 13–14 的 data pipeline 决定多模态样本如何抓取、清洗、合成、去重和配比；Lecture 15–16 的 post-training 与 RL 决定模型是否能把这些能力转成交互行为。

所以多模态不是“在语言模型旁边加一个视觉模块”，而是一次完整的系统设计：

$$
\text{representation}
\rightarrow
\text{alignment}
\rightarrow
\text{data curriculum}
\rightarrow
\text{token budget}
\rightarrow
\text{evaluation}
\rightarrow
\text{generation}
$$

## 面试复盘

1. **为什么 Transformer 可以处理图像？** 因为它真正需要的是向量序列；只要把 patch 或视觉特征映射成 token-like embedding，就可以和文本序列一起建模。

2. **ViT 如何把图片变成 token？** 按固定 patch size 切图，每个 patch flatten 后线性投影并加入位置编码；\(224/14=16\)，因此得到 \(16\times16=256\) 个 patch。

3. **CLIP 与 image captioning 的目标有什么区别？** CLIP 做图文 pairwise ranking，只要求正确配对相似度高；captioning 要生成完整文本，目标更细但计算效率更低。

4. **SigLIP 为什么更容易扩展？** 它把 batch-level multiclass softmax 改成每个 pair 的 sigmoid binary loss，解除 loss 对全 batch 的依赖，更适合分布式训练。

5. **LLaVA 的三组件是什么？** Vision encoder 提取图像特征，projector 把维度映射到 LM embedding space，language model 负责跨模态对话与生成。

6. **为什么 LLaVA 要分两阶段训练？** 第一阶段只对齐视觉和语言空间，第二阶段再训练语言模型适应视觉指令，避免一开始就破坏已有语言能力。

7. **AnyRes 解决什么问题？** 固定 \(336\times336\) 会损失 OCR 和细节；AnyRes 把高清图切成多个 tile 编码，再根据 token budget 压缩。

8. **Qwen2-VL 的 dynamic resolution 与 MRoPE 分别解决什么问题？** 前者动态分配视觉 token，后者显式表达时间、高度和宽度的多维位置关系。

9. **为什么 Qwen3-VL 需要 loss weighting 和 visual token budget？** 视频样本长，容易在 token 数和 loss 上支配文本；token budget 与归一化 loss 可以控制训练稳定性、上下文和部署成本。

10. **Chameleon 为什么更统一但未必更强？** 它把文本和图像都离散成 token，可用一个 autoregressive Transformer 理解和生成；但 VQ quantization 会损失视觉信息，不同 modality 的 entropy 也会带来训练稳定性问题。

如果只能记住一句话，那就是：**多模态建模的核心不是把图片塞进语言模型，而是设计一种既能保留语义、空间和时间结构，又能在训练与部署预算内稳定处理的 token 表示。**
