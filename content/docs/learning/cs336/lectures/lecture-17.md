---
title: "L17 · Multimodal"
weight: 17
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "multimodal"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture17/
---
Lecture 17 是 2026 CS336 正课的最后一讲之一，而且它和前面的 Lecture 1–16 很不一样：课程表把它叫 **“Alignment - multimodality [Percy]”**，但官方 `lecture_17.py` 的标题更直接——**“multimodal models”**。它不是继续 Lecture 15/16 的 RLHF、GRPO，而是在问：

[
\boxed{\textbf{我们已经从零造出了一个 Language Model，怎样把它扩展成一个能看、能听、最终也能生成其他模态的 Omni Model？}}
]

官方给出的终极目标就是：

[
\boxed{\text{Omni model}}
]

能够接受任意组合的 text / image / video / audio 等输入，并生成任意组合的模态输出。2026 Lecture 17 的实际主线是：

[
\boxed{
\text{CLIP}
\rightarrow
\text{SigLIP}
\rightarrow
\text{LLaVA}
\rightarrow
\text{LLaVA-OneVision}
\rightarrow
\text{Qwen-VL系列}
\rightarrow
\text{Chameleon}
}
]

官方课程表确认 Lecture 17 是 5 月 27 日的多模态课，而讲义源码明确把核心问题写成：“怎样输入非文本数据？”以及“怎样输出非文本数据？” ([GitHub][1])

我认为这堂课真正的主线不是记这些模型名字，而是理解一句话：

[
\boxed{
\textbf{Transformer 只会处理 token；
Multimodality 的核心问题，就是怎样把现实世界变成合适的 token。}
}
]

---

# 一、为什么 Transformer 可以突然拿去“看图”？

前面 CS336 一直在做：

[
\text{text}
\rightarrow
\text{token IDs}
\rightarrow
\text{embeddings}
\rightarrow
\text{Transformer}.
]

例如：

> The cat sits.

Tokenizer：

[
[464,;3797,;10718,\dots]
]

Embedding 后：

[
X\in\mathbb R^{T\times d}.
]

Transformer 根本不知道这些向量曾经来自“文字”。

它真正要求的只是：

[
\boxed{
X=(x_1,\ldots,x_T),
\qquad
x_i\in\mathbb R^d.
}
]

那如果我能把一张图片：

[
I\in\mathbb R^{H\times W\times3}
]

也变成：

[
V=(v_1,\ldots,v_M),
\qquad
v_i\in\mathbb R^d,
]

理论上 Transformer 完全可以吃：

[
[\text{text tokens},\text{visual tokens},\text{text tokens}].
]

所以 Lecture 17 开头说得非常漂亮：

> Transformers work really well, so we gotta use them. Transformers speak tokens; therefore, everything must somehow be converted into tokens. ([GitHub][2])

这和 Lecture 1 的 BPE 是同一个问题，只不过难度升级了：

[
\boxed{
\text{text tokenization}
\rightarrow
\text{visual tokenization}
\rightarrow
\text{audio/video tokenization}.
}
]

---

# 二、第一步：一张图片到底怎么变成 Transformer token？

最经典答案是：

[
\boxed{\text{Vision Transformer, ViT}}
]

假设一张图片：

[
I\in\mathbb R^{224\times224\times3}.
]

patch size：

[
P=14.
]

那么横向：

[
224/14=16
]

块，纵向也是 16。

总 patch 数：

[
\boxed{16\times16=256}.
]

每个 patch 原始维度：

[
14\times14\times3=588.
]

把每个 patch flatten：

[
p_i\in\mathbb R^{588},
]

再做 Linear：

[
v_i=p_iW_E,
\qquad
W_E\in\mathbb R^{588\times d}.
]

得到：

[
V\in\mathbb R^{256\times d}.
]

突然之间：

> 一张二维图片变成了 256 个“视觉词”。

从此以后可以像文本一样做：

[
Q=VW_Q,\quad K=VW_K,\quad V'=VW_V.
]

所以 ViT 最伟大的地方之一，就是：

[
\boxed{
\text{image}
\rightarrow
\text{sequence}
}
]

让视觉问题进入了 Transformer 世界。

Lecture 17 的 CLIP 部分就使用 ViT，并以 ViT-L/14@336px 作为重要配置。([GitHub][2])

---

# 三、但是 ViT 只解决“图片内部怎么编码”，没有解决“图片和语言怎么对齐”

例如图片：

🐶

Vision Encoder 输出：

[
v_{\rm image}.
]

文本：

> “a photo of a dog”

Text Encoder 输出：

[
v_{\rm text}.
]

如果两个 embedding space 各玩各的：

[
v_{\rm image}
]

和：

[
v_{\rm text}
]

没有任何对应关系。

那么 LLM 根本不知道：

> 这个视觉向量代表 dog。

所以第一代关键技术：

[
\boxed{\text{CLIP}}
]

就是解决：

[
\boxed{\text{Vision ↔ Language representation alignment}}.
]

---

# 四、CLIP：不要让模型“描述图片”，只让它认出正确配对

这是 Lecture 17 第一块真正需要推公式的内容。

假设 batch size：

[
N.
]

有：

[
(I_1,T_1),\ldots,(I_N,T_N)
]

共 (N) 对 image-caption。

分别编码：

[
u_i=f_{\rm image}(I_i)
]

和：

[
v_j=f_{\rm text}(T_j).
]

一般先 normalize：

[
\hat u_i=\frac{u_i}{|u_i|},
\qquad
\hat v_j=\frac{v_j}{|v_j|}.
]

计算所有：

[
N\times N
]

pair 的 similarity：

[
\boxed{
s_{ij}
======

\frac{
\hat u_i^\top\hat v_j
}{
\tau
}
}
]

其中 (\tau) 是 temperature。

因此得到矩阵：

[
S=
\begin{bmatrix}
s_{11}&s_{12}&\cdots&s_{1N}\
s_{21}&s_{22}&\cdots&s_{2N}\
\vdots&&&\vdots\
s_{N1}&\cdots&&s_{NN}
\end{bmatrix}.
]

正确配对在：

[
\boxed{\text{diagonal}}
]

上。

所以对于 image (I_i)，做：

[
P(T_j|I_i)
==========

\frac{e^{s_{ij}}}
{\sum_k e^{s_{ik}}}.
]

希望：

[
j=i.
]

同时反过来也做：

[
P(I_j|T_i).
]

最终：

[
\boxed{
L_{\rm CLIP}
============

\frac12
(
L_{\rm image\rightarrow text}
+
L_{\rm text\rightarrow image}
)
}
]

这就是对比学习。

CLIP 使用大规模互联网 image-text pair 做这种任务；原论文训练数据约 4 亿 image-text pairs。([arXiv][3])

---

# 五、为什么这个目标比“看图写 Caption”高效得多？

一种更直觉的方法是：

[
I
\rightarrow
\text{“A dog running through grass...”}
]

做 autoregressive caption generation。

那每张图要生成：

[
T
]

个 tokens。

每 token 都要跑 decoder。

CLIP 则把问题改成：

> 这张图片对应 batch 中哪一句文字？

所以它可以把：

[
N
]

对数据一次组成：

[
N^2
]

个正负 pairing comparisons。

官方 Lecture 17 特别展示了 CLIP 的 ablation：直接 image-to-text prediction 在相同目标上比 contrastive ranking 更低效；CLIP 原工作也报告 contrastive objective 在小中规模实验上明显提升了 compute efficiency。([GitHub][2])

这里其实和 Lecture 16 的 Generation–Verification Gap 有一种很有意思的呼应：

[
\boxed{\text{生成完整 caption 比判断 image/text 是否匹配难。}}
]

CLIP 选择了那个更便宜的学习信号。

---

# 六、CLIP 最终到底学到了什么？

这是理解后面所有 VLM 的关键。

训练完后：

```text
dog image
      ↓
 image encoder
      ↓
 semantic vector
      ↑
 text encoder
      ↑
"a photo of a dog"
```

它们被拉到相近位置。

于是你甚至可以做 zero-shot classification。

假设分类：

[
{\text{dog},\text{cat},\text{car}}.
]

先构造：

[
t_{\rm dog}
===========

f_T(\text{"a photo of a dog"})
]

等等。

新图片：

[
v=f_I(I).
]

算：

[
v^\top t_{\rm dog},
\quad
v^\top t_{\rm cat},
\quad
v^\top t_{\rm car}.
]

谁最大就预测谁。

这就是 CLIP 为什么可以 zero-shot ImageNet classification。CLIP 原论文发现 zero-shot 模型可以达到与原始 supervised ResNet-50 相当的 ImageNet 表现。([arXiv][3])

但是这里埋下了一个巨大问题：

[
\boxed{\text{CLIP 学的是 semantic representation，不是 pixel-perfect representation。}}
]

这个问题会一直追到 Chameleon。

---

# 七、CLIP 的第一个系统问题：Loss 和整个 Batch 耦合了

回到：

[
P(T_j|I_i)
==========

\frac{e^{s_{ij}}}
{\sum_{k=1}^{N}e^{s_{ik}}}.
]

注意 denominator：

[
\boxed{\text{需要 batch 中所有 text}}
]

。

所以在多设备训练时：

> 每张 accelerator 上的 image embedding 需要知道其他 accelerator 上的 text embeddings。

也就是说：

[
\boxed{\text{global softmax}}
]

产生 communication coupling。

同时，contrastive learning 很依赖大量 negative examples，因此 CLIP 很喜欢超大 batch。Stanford 讲义总结 CLIP 的技术限制之一就是 large batch 与 full-batch softmax。([GitHub][2])

这就自然引出：

[
\boxed{\text{SigLIP}}
]

。

---

# 八、SigLIP：为什么不把它当 N-way classification？

CLIP 对每个 image 问：

> N 个 captions 中哪个是真的？

SigLIP 改成更简单的问题：

> 这一对 image-text 到底匹不匹配？

定义：

[
z_{ij}
======

\begin{cases}
+1,&i=j\
-1,&i\neq j
\end{cases}
]

以及 similarity：

[
s_{ij}=u_i^\top v_j.
]

对每个 pair 做 logistic loss：

[
\boxed{
\ell_{ij}
=========

\log
\left(
1+\exp(-z_{ij}s_{ij})
\right)
}
]

或者等价写成 sigmoid BCE。

重点不是具体符号，而是：

[
\boxed{\text{每一个 pair 可以独立算。}}
]

不再需要：

[
\boxed{
\frac{e^{s_{ij}}}
{\sum_ke^{s_{ik}}}
}
]

这个全 batch normalization。

SigLIP 原论文明确指出，这种 pairwise sigmoid objective 不需要获取全局 pairwise similarities 做 normalization，因此把 batch size 和 loss 解耦，也更适合分布式训练；论文还发现 batch 放到 1M 并没有持续巨大收益，约 32K 已经足够。([arXiv][4])

所以可以把两者压缩成：

[
\boxed{
\text{CLIP}
===========

\text{“哪一个是正确配对？”}
}
]

而：

[
\boxed{
\text{SigLIP}
=============

\text{“这一对配不配？”}
}
]

---

# 九、但是 CLIP/SigLIP 还不是 ChatGPT 能“看图”

因为目前只有：

[
I
\xrightarrow{\text{vision encoder}}
V.
]

以及：

[
T
\xrightarrow{\text{text encoder}}
U.
]

这是：

[
\boxed{\text{representation model}}
]

不是：

[
\boxed{\text{generative LLM}}
]

。

我们真正想要：

```text
<Image>
What is unusual about this image?

Assistant:
...
```

所以必须把：

[
\boxed{\text{visual representation}}
]

塞进：

[
\boxed{\text{autoregressive language model}}
]

。

这就是 LLaVA。

---

# 十、LLaVA 的结构简单到有点离谱

这是 Lecture 17 非常重要的 lesson。

你可能以为 multimodal LLM 必须发明全新 Transformer。

LLaVA 基本就是：

[
\boxed{
\text{CLIP Vision Encoder}
+
\text{Linear Projector}
+
\text{Vicuna/LLaMA}
}
]

。([arXiv][5])

假设 CLIP 输出 patch features：

[
V
\in
\mathbb R^{N_v\times d_v}.
]

而 LLM hidden dimension：

[
d_{\rm LM}.
]

视觉 encoder 可能：

[
d_v=1024.
]

LLM：

[
d_{\rm LM}=4096.
]

那只需要：

[
W
\in
\mathbb R^{1024\times4096}
]

做：

[
\boxed{
Z=VW
}
]

于是：

[
Z
\in
\mathbb R^{N_v\times4096}.
]

现在这些视觉 embedding 与文本 embedding 的维度完全相同。

于是输入可以直接变成：

[
[
e_{\rm text1},
e_{\rm text2},
z_1,z_2,\dots,z_{N_v},
e_{\rm text3},\dots
].
]

LLM 根本不需要知道：

> “这些 token 原来是图片。”

它只看到：

[
\boxed{\text{一串 }d_{\rm LM}\text{ 维 vectors}}
]

。

---

# 十一、为什么一个 Linear Projector 居然够用？

这其实是 CLIP 的功劳。

如果 vision encoder 输出只是：

[
\text{pixel-level arbitrary representation},
]

那一个 Linear：

[
W
]

很难把视觉世界翻译成语言世界。

但 CLIP 已经利用 image-caption supervision 学到了：

[
\boxed{\text{semantic visual representation}}.
]

所以 projector 主要是在做：

[
\boxed{
\text{coordinate-system alignment}
}
]

而不是从零学：

> “猫是什么。”

这就是 modular foundation model 一个很漂亮的思想：

[
\boxed{
\text{预训练好的 vision system}
+
\text{预训练好的 language system}
+
\text{小 adapter}
}
]

就能组合。

---

# 十二、LLaVA 为什么要分两阶段训练？

官方 Lecture 17 给的 LLaVA recipe 是：

第一阶段冻结 vision encoder 和 LLM，只训练 projector (W)；第二阶段仍冻结 vision encoder，但训练 projector + LM。([GitHub][2])

为什么？

刚开始：

[
W
]

是随机的。

所以送进 LLM 的视觉 vectors 基本是：

[
\boxed{\text{garbage embeddings}}.
]

如果直接把整个 LLM 一起训练：

> 巨大的语言能力可能被这个陌生 distribution 搅乱。

所以 Stage 1 先解决：

[
\boxed{\text{modality alignment}}
]

即：

> “怎样把 CLIP space 翻译进 LLM embedding space？”

然后 Stage 2 才教：

[
\boxed{\text{multimodal instruction following}}.
]

这其实和 Lecture 15 的 SFT 完全相连。

---

# 十三、LLaVA 的另一个妙处其实是 Data，而不是 Architecture

原始 LLaVA 没有海量真正的：

```text
Image
+
Human multimodal conversation
```

怎么办？

Lecture 14 已经给你答案：

[
\boxed{\text{Synthetic Data}}
]

。

LLaVA 从 COCO 图像获得：

```text
caption
bounding boxes / detected objects
```

然后把这些文字描述给 GPT-4，让它生成：

```text
questions
detailed descriptions
multimodal conversations
```

再把这些生成结果重新配回原图片。

最终得到约：

[
158K
]

instruction examples。([arXiv][5])

你有没有发现：

[
\boxed{
\text{Lecture 14 Synthetic Data}
+
\text{Lecture 15 SFT}
+
\text{Lecture 17 Vision}
}
]

三讲在这里完全合流了。

---

# 十四、LLaVA 之后最大的现实问题：336×336 太小了

CLIP 的典型预处理会 resize + crop。

例如：

[
336\times336.
]

看普通狗猫：

> 没什么问题。

但假设输入是一张：

[
2000\times3000
]

的论文截图。

里面字体可能只有：

[
12\text{ pixels}.
]

你硬缩到：

[
336\times336
]

以后：

[
\boxed{\text{字直接糊了}}
]

。

对于：

```text
OCR
documents
charts
GUI screenshots
medical images
```

尤其致命。

所以多模态模型开始进入一个很关键的问题：

[
\boxed{\text{Resolution ↔ Visual token budget}}
]

。

---

# 十五、AnyRes：不要把高清图一次缩小，切成 tiles

LLaVA-OneVision 的思路很直觉。

假设图片：

[
1344\times672.
]

如果 vision encoder base resolution：

[
336\times336,
]

可以切成：

[
4\times2
]

个 tiles。

每个：

[
336\times336.
]

各自经过 vision encoder。

然后：

[
\boxed{\text{concatenate visual tokens}}
]

。

于是你保住了局部细节。

Lecture 17 对 OneVision 的总结就是：高分辨率对 OCR 等任务很重要，所以通过 AnyRes 把图片拆成多个适合 vision encoder 的区域；如果 resulting token 数过大，再进行压缩。([GitHub][2])

---

# 十六、可是分辨率提高以后，另一个灾难来了：Token 爆炸

还记得 Attention：

[
O(T^2).
]

如果一张图原来：

[
576
]

visual tokens。

切成 8 个 tiles：

[
8\times576
==========

4608.

]

仅 attention pair 数就从：

[
576^2
]

变成：

[
4608^2
======

64\times576^2.
]

所以：

[
\boxed{
\text{Higher Resolution}
\Rightarrow
\text{Better perception}
\Rightarrow
\text{More visual tokens}
\Rightarrow
\text{Higher compute/memory}
}
]

。

这就是现代 VLM 一个非常核心的 resource trade-off。

---

# 十七、OneVision 为什么单图、多图、视频不能一视同仁？

假设：

单图：

[
1\times1000\text{ tokens}.
]

还好。

多图：

[
20\times1000
============

20K.
]

视频：

[
300\text{ frames}\times1000
===========================

300K.
]

马上爆炸。

于是 OneVision 的设计哲学是：

[
\boxed{\text{不同 modality 使用不同 token budget}}
]

。

官方课件明确说，目标是让各种 modality 产生大致可控的 sequence length：单图可以保留较高分辨率，多图每图使用基础分辨率，而视频每帧更低分辨率。([GitHub][2])

为什么这么做合理？

因为视频相邻帧：

[
\boxed{\text{高度冗余}}
]

。

一分钟视频可能：

[
1800
]

帧，但相邻：

[
t,\quad t+1
]

画面绝大部分相同。

所以：

[
\boxed{
\text{raw pixel count}
\neq
\text{information content}
}
]

。

这其实又回到了 Lecture 14：

[
\boxed{\text{token budget 应该按 information value 分配。}}
]

---

# 十八、OneVision 最值得注意的结论反而是：跨模态能力会 Transfer

OneVision 同时处理：

[
\text{single image},
\quad
\text{multi-image},
\quad
\text{video}.
]

实验发现很多能力可以 cross-scenario transfer。

例如单图上的 diagram/chart reasoning，可以泛化到 multi-image；单图 OCR 加多图 relational reasoning，可以迁移到 GUI agent；单图 visual prompting 甚至能泛化到视频。官方 Lecture 17 特意花篇幅展示这些 transfer examples。([GitHub][2])

这说明：

[
\boxed{
\text{图片、多图、视频并不是三个完全不同的问题。}
}
]

如果它们最后都进入：

[
\boxed{\text{共享 representation + shared LM}}
]

很多 abstract skill 是可以迁移的。

这就是“Omni Model”为什么有吸引力。

---

# 十九、Percy 对 OneVision 的总结其实特别重要

官方最后总结的是：

[
\boxed{
\text{Vision Encoder}
+
\text{Projector}
+
\text{LM}
}
]

已经成为标准 VLM template。

而且他直接说：

> Most work goes into data curation, heavily synthesized and task-specific data. ([GitHub][2])

这句话非常值得你划重点。

现代 VLM 论文看 architecture 图：

```text
ViT
 ↓
MLP
 ↓
LLM
```

经常觉得：

> “就这？”

真正巨大的工程可能在：

```text
OCR data
chart data
diagram data
video QA
GUI data
grounding data
synthetic conversations
reasoning data
```

。

所以 Lecture 13/14 的结论在多模态时代完全没失效：

[
\boxed{\textbf{Data is still architecture.}}
]

---

# 二十、Qwen-VL：开始把“视觉定位”也编码进语言序列

原始 LLaVA 更像：

[
\text{image}
\rightarrow
\text{natural-language answer}.
]

但真实视觉任务还需要：

> “图里这个东西在哪？”

所以 Qwen-VL 加入 special tokens：

[
\boxed{
\texttt{<img>},
\texttt{<box>},
\texttt{<ref>}
}
]

并支持 grounding。

架构上：

[
\text{OpenCLIP ViT}
\rightarrow
\text{cross-attention adapter}
\rightarrow
\text{Qwen LM}.
]

它的 adapter 使用二维位置信息，并把 visual representation 映射到固定数量的视觉 tokens。([GitHub][2])

最值得关注的仍然是训练阶段。

---

# 二十一、Qwen-VL 的三阶段训练其实和整个 CS336 都同构

Stage 1：

[
\boxed{\text{大量、质量较低的数据}}
]

冻结 LM，训练 visual encoder + adapter。

目标：

[
\boxed{\text{建立基本视觉语言 alignment}}.
]

Stage 2：

[
\boxed{\text{更高质量、task-specific 数据}}
]

提高 resolution，训练全部参数。

目标：

[
\boxed{\text{真正建立视觉能力}}.
]

Stage 3：

[
\boxed{\text{instruction tuning}}
]

冻结视觉 encoder，训练 adapter + LM。

目标：

[
\boxed{\text{变成好用 assistant}}.
]

官方 Lecture 17 就是这样概括 Qwen-VL 的训练流程。([GitHub][2])

你应该立刻联想到：

[
\boxed{
\text{Pretraining}
\rightarrow
\text{Midtraining}
\rightarrow
\text{Post-training}
}
]

。

多模态没有发明另一套机器学习。

它只是把我们前 16 讲学的东西搬进了 multimodal world。

---

# 二十二、Qwen2-VL 最大的升级：不要固定图片 token 数

早期 VLM 很喜欢：

> 每张图片统一 resize 成固定 resolution。

那么：

[
\boxed{\text{每张图都有固定 visual token count}}.
]

但一张手机小图：

[
500\times500
]

和一个：

[
4000\times3000
]

的复杂 PDF 页面，信息量显然不一样。

Qwen2-VL 引入：

[
\boxed{\text{Naive Dynamic Resolution}}
]

核心就是：

[
\boxed{
\text{图片分辨率越高}
\Rightarrow
\text{更多 visual tokens}
}
]

而不是一刀切成固定长度。

Qwen2-VL 原论文明确把 dynamic resolution 和 M-RoPE 作为两项核心改进。([arXiv][6])

---

# 二十三、Dynamic Resolution 其实是在做“视觉版 Variable-Length Tokenization”

文本：

> “cat”

很短。

一篇论文：

> 8000 tokens。

我们从来不会说：

> 所有文本统一压成 256 tokens。

因为信息量不同。

那图片为什么必须：

[
\boxed{\text{每张 256 visual tokens？}}
]

Dynamic Resolution 的哲学就是：

[
\boxed{
\text{视觉输入也应该允许 variable-length representation。}
}
]

这其实是非常自然的。

代价还是：

[
\boxed{\text{compute budget 不再固定}}
]

。

因此部署 Qwen3-VL 时甚至会直接让用户限制每张图/视频的 visual-token budget，官方实现明确暴露这些参数。([GitHub][7])

---

# 二十四、然后出现一个很有意思的问题：二维图片的位置怎么用 RoPE 表示？

普通文本只有：

[
\boxed{\text{position }t}.
]

所以：

[
\theta_t.
]

图片则有：

[
\boxed{(h,w)}
]

两个 coordinate。

视频甚至是：

[
\boxed{(t,h,w)}.
]

所以 Qwen2-VL 引入：

[
\boxed{\text{Multimodal RoPE, M-RoPE}}
]

。([arXiv][6])

你可以把普通 RoPE 想成：

[
R(p)
]

编码一个位置 (p)。

那么 Multimodal RoPE 就需要表达：

[
\boxed{
R(t,h,w)
}
]

。

---

# 二十五、为什么必须显式区分时间、高度、宽度？

假设视频两个 patch：

[
A=(t=1,h=5,w=7)
]

和：

[
B=(t=2,h=5,w=7).
]

它们是：

> 同一空间位置，下一帧。

另一个：

[
C=(t=1,h=5,w=8)
]

是：

> 同一时间，相邻横向 patch。

如果把所有东西简单 flatten：

[
p=1,2,3,\ldots
]

模型很难直接知道：

[
\boxed{
B-A=\text{temporal move}
}
]

而：

[
\boxed{
C-A=\text{spatial move}.
}
]

MRoPE 将 position structure 明确编码进 representation。

这就是：

[
\boxed{\text{从 1D language sequence 到 3D spatiotemporal sequence}}
]

最自然的扩展。

---

# 二十六、Qwen3-VL 又对 MRoPE 做了什么？

Qwen3-VL 使用 **Interleaved MRoPE**。

上一代大致会让某些 RoPE dimensions 负责：

[
t
]

某些负责：

[
h
]

某些负责：

[
w.
]

例如概念上：

[
[t,t,t,t,w,w,w,w,h,h,h,h].
]

Qwen3-VL 改成类似：

[
\boxed{
[t,w,h,t,w,h,t,w,h,\ldots]
}
]

。官方 Lecture 17 就用这两个 sequence 对比来解释。([GitHub][2])

为什么可能更好？

RoPE 的不同 dimensions 对应不同 frequency：

[
\omega_1,\omega_2,\ldots.
]

如果：

[
t
]

只占据一整块频率区间，它可能只获得偏高或偏低频率。

交错以后：

[
t,h,w
]

各自都能获得：

[
\boxed{\text{多尺度 frequency information}}
]

。

非常像 Fourier features：

> 每个 coordinate 都应该同时拥有粗粒度和细粒度位置表达。

---

# 二十七、Qwen3-VL 为什么还把 Video Timestamp 直接写成文字？

这也很聪明。

仅靠 positional embedding：

模型知道：

[
\text{frame A before frame B}.
]

但用户问：

> “第 37 秒发生了什么？”

“37 秒”是：

[
\boxed{\text{semantic time}}
]

不只是 sequence position。

所以 Qwen3-VL 把 timestamp 作为显式 textual tokens，而不是只塞在位置编码里。官方技术报告和 Lecture 17 都把 text-based time alignment 作为升级点。([arXiv][8])

于是：

```text
<00:37>
[visual tokens...]
```

模型可以真正建立：

[
\boxed{
\text{language concept “37 seconds”}
\leftrightarrow
\text{video location}
}
]

。

这非常适合：

```text
video grounding
temporal QA
长视频 retrieval
```

。

---

# 二十八、Qwen3-VL 还有一个非常容易被忽略、但很 CS336 的问题：Loss Weighting

假设一个 batch：

短文本：

[
L_1=128.
]

单图：

[
L_2=2048.
]

长视频：

[
L_3=16384.
]

如果你直接：

[
L
=

\sum_t\ell_t,
]

那么一条长视频的 gradient weight 大概是短文本的：

[
16384/128
=========

128
]

倍。

于是：

[
\boxed{\text{video data 会主宰 training objective}}.
]

但你如果对每个 example 完全平均：

[
L_e
===

\frac1{n_e}
\sum_t\ell_t,
]

又可能太狠地压低长样本贡献。

所以 Qwen3-VL 使用 square-root-style normalization，直觉可以写成：

[
\boxed{
L_e
\propto
\frac1{\sqrt{n_e}}
\sum_{t=1}^{n_e}\ell_t
}
]

。

那么一个长度为 (n) 的样本总 weight 从：

[
n
]

降成大约：

[
\sqrt n.
]

例如长度差：

[
100\times.
]

普通 token sum：

[
100\times
]

影响力。

sqrt normalization：

[
10\times.
]

这就是在：

[
\boxed{
\text{不让视频统治训练}
}
]

和：

[
\boxed{
\text{又不彻底抹掉长视频信息}
}
]

之间折中。Lecture 17 明确把这一技巧解释成 balancing text and multimodal data，因为视频样本往往特别长。([GitHub][9])

你应该立刻联想到 Lecture 14：

[
\boxed{\text{Data mixture weights}}
]

。

这其实就是 **token-level mixture weighting**。

---

# 二十九、Qwen3-VL 的 DeepStack 又在解决什么？

LLaVA 是：

[
\boxed{
\text{视觉信息在 input 层注入一次}
}
]

。

即：

[
V
\rightarrow
\text{projector}
\rightarrow
\text{LLM layer 1}
\rightarrow
\cdots
]

。

问题是 Vision Transformer 不同层学到的东西不一样。

粗略：

早层：

[
\boxed{\text{edges, textures, fine details}}
]

高层：

[
\boxed{\text{semantics}}
]

。

如果你只把最后一层视觉 feature 注入 LLM：

[
\boxed{\text{可能丢掉部分低层细节。}}
]

DeepStack 的思路是：

[
\boxed{\text{在多个 LLM 层注入 multi-level vision features}}
]

而不是只在最开头注入一次。

Qwen3-VL 技术报告把 DeepStack integration 列为主要 architecture upgrade 之一。([arXiv][8])

这尤其适合：

```text
OCR
fine-grained visual details
GUI
spatial localization
```

。

---

# 三十、然后 Qwen3-VL 的 Training Recipe 又把前 16 讲全串起来了

官方 Lecture 17 的概括是：

先 train adapter 做 alignment，然后 full multimodal pretraining，并逐渐把 context 扩到：

[
8K
\rightarrow
32K
\rightarrow
256K.
]

Post-training：

[
\boxed{
\text{Long-CoT SFT}
+
\text{Knowledge Distillation}
+
\text{RL}
}
]

。([GitHub][2])

也就是说：

Lecture 3：

[
\text{Transformer architecture}
]

Lecture 7–8：

[
\text{distributed training}
]

Lecture 9–11：

[
\text{scaling}
]

Lecture 13–14：

[
\text{data}
]

Lecture 15：

[
\text{SFT}
]

Lecture 16：

[
\text{RL}
]

全部原封不动进入：

[
\boxed{\text{Multimodal training}}
]

。

所以 Lecture 17 其实像一堂课程“大综合”。

---

# 三十一、到这里，所有模型还有一个巨大缺陷：只能“看”，不能真正“画”

CLIP/SigLIP representation 擅长：

[
\boxed{\text{understanding}}
]

。

例如：

> “这是一只狗。”

但如果现在让模型：

> “生成这只狗的图片。”

CLIP embedding 不够。

为什么？

因为 contrastive learning 的目标就是忽略很多细节。

两张图片：

```text
同一只狗
背景稍微变化
亮度不同
像素纹理不同
```

只要 caption 都是：

> “a dog”

CLIP 很可能希望它们：

[
\boxed{\text{embedding 很接近}}.
]

也就是说，CLIP 主动学了：

[
\boxed{\text{invariance}}.
]

这对于 semantic understanding 很棒。

对于 reconstruction：

[
\boxed{\text{很糟}}.
]

---

# 三十二、这就是 Lecture 17 最深的一组矛盾

[
\boxed{
\text{Understanding wants invariance}
}
]

而：

[
\boxed{
\text{Generation wants details}
}
]

。

你问：

> “图里有没有猫？”

只需要：

[
\boxed{\text{semantic information}}.
]

但你让我重建图片：

> 猫左耳具体哪几根毛是什么颜色？

这些所谓“无关细节”突然全重要了。

官方 Lecture 17 最后的总结就明确指出：

> comprehension 与 generation 对 representation 的要求可能不同：前者更关注 semantics，后者需要 finer-grained details。([GitHub][2])

这就是 Omni Model 真正困难的地方。

---

# 三十三、Chameleon：既然文本是 discrete tokens，那把图片也离散化好了

这是一条非常优雅的路线。

文本：

[
\boxed{
\text{hello}
\rightarrow
[15339]
}
]

。

图片也：

[
\boxed{
I
\rightarrow
[z_1,z_2,\ldots,z_M]
}
]

其中：

[
z_i\in{1,\ldots,K}.
]

于是整个世界：

```text
Text token
Image token
Image token
Text token
Image token
...
```

全部放进一个统一 vocabulary。

然后训练：

[
\boxed{
p(z_t|z_{<t})
}
]

。

这就是 Chameleon 的 **mixed-modal early-fusion** 思路：文本和图片都表示成离散 token，由同一个 autoregressive Transformer 建模，因此既能理解，也能生成。([arXiv][10])

---

# 三十四、图片怎么变成离散 token？VQ-VAE

核心结构：

[
\boxed{
\text{Image}
\xrightarrow{\text{encoder}}
Z
\xrightarrow{\text{quantize}}
z_1,\ldots,z_M
\xrightarrow{\text{decoder}}
\hat I
}
]

。

假设 codebook：

[
E=
{e_1,\ldots,e_K}.
]

Encoder 对某个 image patch 得到：

[
h_i.
]

找最近的 code：

[
\boxed{
k_i
===

\arg\min_k
|h_i-e_k|^2
}
]

。

于是这个 patch 直接变成整数：

[
\boxed{k_i}.
]

这和 BPE token ID 完全一样。

Chameleon 使用的图像 tokenizer 可以把：

[
512\times512
]

图片编码成约：

[
1024
]

image tokens，codebook size 为：

[
8192.
]

([GitHub][2])

突然之间：

[
\boxed{
\text{image generation}
=======================

\text{next-token prediction}
}
]

。

这在概念上极其漂亮。

---

# 三十五、那 Chameleon 为什么没有直接统一天下？

因为：

[
\boxed{\text{discretization loses information}}.
]

假设原 encoder representation：

[
h=(0.217,0.812,\ldots).
]

你必须硬选：

[
e_{1739}.
]

所有落在这个 Voronoi cell 中的细微区别：

[
\boxed{\text{全部消失}}.
]

所以：

[
I
\rightarrow
z
\rightarrow
\hat I
]

总会有 reconstruction error。

特别是：

```text
small text
OCR
fine texture
tiny symbols
```

非常怕 quantization。

官方 Lecture 17 对 Chameleon 的评价就非常明确：**非常优雅——统一 autoregressive discrete-token modeling；但是效果不如 continuous-representation 路线，其中一个核心原因就是 discretization information loss，例如 OCR。** ([GitHub][2])

---

# 三十六、而且多模态 Token 的 entropy 根本不一样

这是 Chameleon 一个特别值得从 CS336 角度理解的问题。

文本 next token distribution：

> “The capital of France is ___”

可能：

[
P(\text{Paris})\approx0.9.
]

entropy 很低。

图片 token：

> 下一个纹理 patch 是哪一个 code？

可能：

[
\boxed{\text{uncertainty 高得多}}.
]

也就是说：

[
H(\text{image tokens})

>

H(\text{text tokens}).
]

现在让同一个 Transformer、同一个 output head 同时建模：

[
\boxed{\text{两种统计性质非常不同的 token distributions}}
]

。

训练很容易出现：

```text
norm growth
logit drift
instability
```

。

Chameleon 为此使用了诸如：

[
\boxed{\text{QK Norm}}
]

和：

[
\boxed{\text{z-loss}}
]

之类的稳定化技术。([GitHub][2])

有没有发现？

这又绕回 Lecture 3！

当时你学 QK Norm、z-loss 可能觉得：

> “一些现代 Transformer 稳定技巧。”

到这里终于看到：

> **当不同 modality 的统计分布完全不同，这些稳定化技术可能变成训练能否跑起来的必要条件。**

---

# 三十七、所以现代 Omni Model 最终更倾向哪条路？

Lecture 17 的总结其实已经给出了 Percy 的判断：

[
\boxed{
\text{Continuous encoders}
+
\text{Transformer}
+
\text{Diffusion models for generation}
}
]

是目前非常自然的一条路线。([GitHub][2])

也就是说，与其强迫所有东西都变成同一种 discrete token：

理解阶段：

[
\boxed{
\text{Image}
\rightarrow
\text{continuous visual encoder}
\rightarrow
\text{LLM}
}
]

生成阶段：

[
\boxed{
\text{LLM semantic representation}
\rightarrow
\text{diffusion decoder}
\rightarrow
\text{pixels}
}
]

。

这样可以：

[
\boxed{\text{让不同组件做自己擅长的事情}}.
]

Transformer：

[
\text{semantic reasoning}
]

Diffusion：

[
\text{high-dimensional continuous generation}
]

Vision Encoder：

[
\text{perception}
]

。

所以“Omni”并不一定意味着：

[
\boxed{\text{一切必须一个 tokenizer、一个 loss、一个 decoder}}
]

。

它也可以是：

[
\boxed{\text{统一 latent reasoning core + modality-specific interfaces}}.
]

---

# 三十八、现在可以把 Lecture 17 的两条路线真正区分清楚

| 路线                   | 输入视觉表示                         | LLM             | 图片生成                           | 优点           | 缺点                                |
| -------------------- | ------------------------------ | --------------- | ------------------------------ | ------------ | --------------------------------- |
| **LLaVA/Qwen-VL 路线** | continuous ViT/SigLIP features | Transformer     | 通常需 diffusion/decoder          | 理解能力强，保留更多细节 | 系统不完全统一                           |
| **Chameleon 路线**     | discrete image tokens          | 同一个 Transformer | 直接 autoregressive image tokens | 极其统一、优雅      | quantization loss、训练难、图像 token 很长 |

这张表基本就是 Lecture 17 最核心的 architecture trade-off。

---

# 三十九、为什么 Lecture 17 明明叫 “Alignment - multimodality”？

现在这个标题也可以真正理解了。

这里的 Alignment 不只是 Lecture 15 的：

[
\boxed{\text{human preference alignment}}
]

。

而是另一个意义：

[
\boxed{
\text{Representation alignment across modalities}
}
]

。

CLIP：

[
\boxed{
\text{image space}
\leftrightarrow
\text{text space}
}
]

。

LLaVA：

[
\boxed{
\text{vision encoder space}
\rightarrow
\text{LLM embedding space}
}
]

。

Instruction tuning：

[
\boxed{
\text{multimodal model}
\rightarrow
\text{human interaction distribution}
}
]

。

所以这讲其实包含两种 alignment：

[
\boxed{
\text{modality alignment}
+
\text{behavior alignment}
}
]

。

---

# 四十、把 Lecture 1–17 串起来，会发现课程设计非常漂亮

Lecture 1 的 Tokenizer 问：

[
\boxed{\text{怎样把文字变成 token？}}
]

Lecture 3 的 Transformer 问：

[
\boxed{\text{怎样建模 token sequence？}}
]

Lecture 13–14 问：

[
\boxed{\text{哪些 token 值得训练？}}
]

Lecture 15–16 问：

[
\boxed{\text{怎样让输出 token 符合目标？}}
]

Lecture 17 最后把问题扩大：

[
\boxed{
\textbf{如果整个现实世界都可以变成 token，
那么同一套 Transformer machinery 能走多远？}
}
]

这就是为什么 Lecture 17 不需要再发明一个完全陌生的数学体系。

它只是把前 16 讲全部重新应用一次。

---

# 四十一、你真正应该形成的 VLM Mental Model

以后看到一个陌生的 multimodal model，不要先被论文里的模型名吓到。

直接问五个问题：

[
\boxed{\text{1. Modality 怎么 token/encode？}}
]

图片是 ViT continuous embeddings？

还是 VQ discrete tokens？

视频怎么 sample？

---

[
\boxed{\text{2. 怎么接进 LLM？}}
]

Linear projector？

MLP？

Cross-attention？

Q-Former？

多层 fusion？

---

[
\boxed{\text{3. Position 怎么编码？}}
]

1D？

2D？

[
(t,h,w)
]

MRoPE？

---

[
\boxed{\text{4. Token budget 怎么控制？}}
]

fixed resolution？

AnyRes？

dynamic resolution？

video sampling？

---

[
\boxed{\text{5. Training data / stages 是什么？}}
]

alignment？

multimodal pretraining？

instruction tuning？

CoT？

distillation？

RL？

只要这五个问题能答出来，绝大多数 VLM architecture 图已经拆完 80%。

---

# 四十二、最后给你 10 道 Lecture 17 自测题

1. **证明为什么 CLIP 的 similarity matrix 是 (N\times N)**，并解释 diagonal 为什么是 positive pairs；再写出 image→text 的 softmax cross-entropy。

2. **CLIP 与 SigLIP 的核心数学区别是什么？** 不要回答“一个更快”，而要回答：CLIP 做 batch-level multiclass normalization；SigLIP 对 image-text pairs 做独立 binary sigmoid classification。为什么后者更容易 distributed？

3. **ViT-L/14 输入 (336\times336) 图片时有多少 spatial patches？**
   [
   336/14=24,\qquad 24^2=576.
   ]
   如果每个 patch feature 是 1024 维，而 LLM hidden size 4096，LLaVA projector 的 weight shape 是什么？
   [
   [1024,4096].
   ]

4. **为什么 LLaVA 一个 Linear Projector 就可能工作？** 关键不是 Linear 很神，而是 CLIP visual features 已经是 semantic representations，projector 主要完成 coordinate-space alignment。

5. **为什么 OCR 逼迫 VLM 使用 AnyRes / dynamic resolution？** 因为 resize 到固定低 resolution 会永久丢掉小文字；但请同时说明提高 resolution 为什么会导致 visual tokens 与 attention cost 激增。

6. **为什么 video 不能简单“每帧按高清图片处理”？** 如果 10 分钟视频 2 fps，共 1200 frames，每帧 576 visual tokens，就已经：
   [
   1200\times576=691{,}200
   ]
   visual tokens，更不用说 full self-attention。

7. **MRoPE 相比普通 RoPE 在表达什么额外结构？** 普通文本位置 (p) 是一维；图片需要 ((h,w))，视频需要 ((t,h,w))。为什么 flatten 成单一 token index 会丢掉显式 spatial-temporal inductive bias？

8. **Qwen3-VL 为什么需要 square-root loss normalization？** 如果短文本 100 tokens，视频 10,000 tokens，普通 token-sum 让视频权重约高 100 倍；平方根归一后总贡献量级约只高：
   [
   \sqrt{100}=10
   ]
   倍。这其实在修改什么？答案是训练 mixture 的有效权重。

9. **为什么 CLIP-style representation 很适合理解，却不一定适合生成？** 因为 contrastive objective 鼓励 semantic invariance，会主动丢掉 caption 不关心的细粒度信息；而图像 reconstruction/generation 恰恰需要这些细节。

10. **Chameleon 为什么“更统一但未必更强”？** 它把 text/image 都离散成 token，可以用一个 autoregressive Transformer 同时理解和生成；但 VQ quantization 有 information loss，不同 modality token entropy 又造成训练稳定性问题。([GitHub][2])

---

# 最后，把 Lecture 17 压缩成一块黑板

第一行写：

[
\boxed{
\text{Transformer speaks tokens.}
}
]

所以：

[
\boxed{
\text{Multimodality}
====================

\text{turn the world into tokens/representations}
}
]

。

然后：

[
\boxed{
\text{CLIP/SigLIP}
==================

\text{learn visual semantics from language supervision}
}
]

再写：

[
\boxed{
\text{LLaVA/Qwen-VL}
====================

\text{Vision Encoder}
+
\text{Adapter}
+
\text{LLM}
}
]

再写：

[
\boxed{
\text{AnyRes/Dynamic Resolution/MRoPE}
======================================

\text{make visual tokens preserve space, time and detail}
}
]

然后：

[
\boxed{
\text{Chameleon}
================

\text{make images discrete tokens too}
}
]

最后写最大的一句话：

[
\boxed{
\textbf{Understanding wants semantic compression;
generation wants information preservation.}
}
]

这其实是 Lecture 17 最深的矛盾。

CLIP 告诉我们：

> 把 irrelevant pixel details 扔掉，可以获得极强 semantic representation。

Chameleon 又告诉我们：

> 但如果以后还想把图片生回来，那些“irrelevant details”突然就不 irrelevant 了。

所以真正的 Omni Model 问题并不是简单：

[
\boxed{\text{“怎么把图片塞进 LLM？”}}
]

而是：

[
\boxed{
\textbf{怎样找到一种表示，
既足够压缩，让 Transformer 能高效 reasoning；
又保留足够信息，让模型能够感知和生成真实世界的细节。}
}
]

而官方 Lecture 17 最后的判断也正落在这里：frontier model 正在走向 native multimodal/omni；输入编码仍是根本问题，理解和生成可能需要不同表示；图片和视频的信息密度、token budget 与文本差异巨大，而现实系统很可能继续采用 **continuous modality encoders + Transformer reasoning core + diffusion-style generation** 的组合，而不是强迫所有模态完全采用同一种 tokenization。
