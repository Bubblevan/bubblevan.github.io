---
schema: bubblevan/v1
id: blog-20261020-aims5710-attention-transformer
content_kind: blog
title: "AIMS5710 Lecture 6：Attention、线性记忆与 Quiz 1 复习"
date: 2026-10-20
updated: 2026-10-20
status: draft
visibility: public
summary: "串起 10 月 20 日前后两段课堂转写：从 Seq2Seq、Self-Attention 和 causal mask，继续到线性注意力的递归状态、DeltaNet 的记忆更新，以及 Quiz 1 对 softmax、反向传播、CNN、RNN 和优化的复习。"
topics: [AIMS5710, Attention, Transformer, Self-Attention, Linear Attention, DeltaNet, Quiz 1]
projects: []
aliases: []
authors: [bubblevan]
---

这节课从机器翻译里的序列对齐开始。Seq2Seq 要把源句的信息带到目标句生成过程里；如果所有信息只能挤进一个固定长度的向量，句子一长就容易形成瓶颈。Attention 的做法是保留编码器各位置的表示，让解码器在生成每个词时重新选择当前最相关的部分。Self-Attention 再把这套“按需读取”的机制搬到同一条序列内部，得到 Transformer 的基本运算。

课堂内容分在两份 10 月 20 日转写里。前一段从 Seq2Seq 讲到 Self-Attention 和 causal mask；后一段（20:35–21:31）接着把 attention 改写成线性递归状态，再讨论如何用 DeltaNet 更新记忆，之后老师按 Quiz 1 范围回顾 softmax、网络反向传播、CNN、RNN 和优化。之前的笔记只拿到前一段，所以看起来在 causal mask 处戛然而止；现在按两段转写的先后合并。公式以 `attention_transformer.pdf` 和板书照片核对，`ViT.pptx` 超出课堂简要引入的部分仍标作课件延伸；`detection.pdf` 没有出现在今天可确认的讲解中。

## 1. Quiz 1 与作业安排

老师开场确认 Homework 2 于 **10 月 20 日**截止，答案计划次日发布，之后不再有 grace period。Quiz 1 安排在 **10 月 27 日（周二）**，多数同学考试时间为 18:30–21:30，共三小时；闭卷、不能用计算器，允许一张双面 cheat sheet，可打印或手写。题目共三题，手写作答，不考写代码；范围是 Lectures 1–6，到 RNN 为止，重点是概念和简单计算。Homework 3 已发布。

这也解释了为什么课堂后段的板书会回到 RNN、CNN、softmax 与交叉熵：它们是 Quiz 1 的复习线索，不是 Attention 本身的组成部分。

## 2. 固定长度句向量为什么会成为瓶颈

在 Seq2Seq 里，编码器读入源序列，解码器再逐步生成目标序列。最简单的设计把源句压成一个固定维度的句向量，再把它交给解码器。无论源句是短是长，传递给解码器的通道大小都不变；句子里的信息越多，编码器越需要在同一向量里挤进更多内容。

RNN 的隐藏状态确实会沿时间更新，但单一状态向量仍然是有限容量的摘要。长序列中的早期细节可能在多次递推后变弱。机器翻译还要处理源词与目标词之间并非一一对应的关系：词序会变，短语长度也会变，解码器需要在生成每个目标词时找到源句中相关的位置。

所以问题可以改写为：生成目标位置 $t$ 时，能否不只依赖一个压缩后的句向量，而是回头读取编码器保留的整串隐藏状态？Attention 就是这个动态读取步骤。

## 3. Attention：每次生成都重新对齐

设编码器对源序列得到隐藏状态 $h_1,\ldots,h_{T_x}$，解码器当前状态为 $s_{t-1}$。先计算目标位置 $t$ 与每个源位置 $i$ 的匹配分数：

$$
e_{t,i}=a(s_{t-1},h_i).
$$

再沿源序列做 softmax，把分数归一化为注意力权重：

$$
\alpha_{t,i}=\frac{\exp(e_{t,i})}{\sum_{j=1}^{T_x}\exp(e_{t,j})},\qquad
\sum_{i=1}^{T_x}\alpha_{t,i}=1.
$$

最后用这些权重对编码器状态求加权和，得到本步的上下文向量：

$$
c_t=\sum_{i=1}^{T_x}\alpha_{t,i}h_i.
$$

这里的 $s_{t-1}$ 是当前查询，$h_i$ 是可以被读取的源端信息；每个 $\alpha_{t,i}$ 表示此时从源位置 $i$ 取多少信息。下一个目标词生成时，解码器状态变了，权重也会重算。因此同一句源文本可以在不同生成步骤被不同方式读取，不必提前塞成一个固定摘要。

打分函数 $a(\cdot,\cdot)$ 有多种选择。课件从 cosine similarity、拼接后经 MLP 的 additive attention、一般双线性形式，到 dot product 与 scaled dot product 逐步推广。它们的共同作用是把“当前 query 与候选 key 有多匹配”变成一个可比较的标量；softmax 再把一组分数变成权重。这里的权重是模型学出的软对齐，不等于人工标注的精确词对齐。

老师还用图像描述说明 Attention 可以跨模态工作：解码器生成某个词时，可以对 CNN 提取的图像区域表示分配权重。课堂讨论中老师特别保留了一个疑问：模型为什么能从前面已生成的词学到对当前图像区域的关注，训练动态并不简单；展示出来的 attention map 也只是定性线索，不应直接当成精确目标分割或因果解释。

## 4. 从跨序列对齐到 Self-Attention 的 Q、K、V

机器翻译的 Attention 有两组不同来源：query 来自解码器，keys 和 values 来自编码器。Self-Attention 则让同一序列同时提供 query、key 和 value。输入矩阵记作 $X\in\mathbb{R}^{d\times T}$，按课堂板书的 column-major 约定，每一列是一处 token 表示。通过三组可学习线性投影得到：

$$
Q=W_QX,\qquad K=W_KX,\qquad V=W_VX.
$$

Q（query）表达当前位置要找什么，K（key）表达每个位置可用什么线索来匹配，V（value）则是匹配后实际汇入输出的信息。它们都由同一个 $X$ 变换而来，但使用不同参数矩阵，所以不能把三者理解成同一份向量的三个名字。

对每个 query 与全部 keys 做点积，得到位置间的相似度。列向量约定下可写为：

$$
A=\operatorname{softmax}\!\left(\frac{K^\top Q}{\sqrt{d_k}}\right),\qquad
Y=VA.
$$

这里 $A\in\mathbb{R}^{T\times T}$，每列对应一个 query 对所有 key 的权重分布；softmax 沿候选 key 的维度归一化。常见的 row-major 写法会转置矩阵，写成 $\operatorname{softmax}(QK^\top/\sqrt{d_k})V$，两者只是布局约定不同。

为什么除以 $\sqrt{d_k}$？若 query 和 key 的各维分量尺度相近，点积的方差会随维度增大；logit 过大时 softmax 容易集中到少数位置，梯度也会变得不理想。按维度平方根缩放，能让分数尺度更稳定。这不是把相似度“变正确”，而是避免维度变大时数值尺度跟着失控。

![10 月 20 日板书：Q/K/V 投影、自注意力矩阵与线性注意力补充](/blog/2026/10-20/aims5710-attention-and-linear-attention-board.jpg)

## 5. 因果遮罩：让注意力符合自回归生成

如果每个位置都能读取序列中所有位置，训练语言模型时位置 $t$ 就可能直接看到未来 token。这样模型会利用答案本身，而不是学会根据前文预测下一个 token。

Causal mask 在 softmax 之前把不允许读取的位置分数设为 $-\infty$。若 $i$ 表示 key 的位置、$t$ 表示 query 的位置，只允许 $i\leq t$：

$$
e_{t,i}^{\mathrm{masked}}=
\begin{cases}
e_{t,i}, & i\leq t,\\
-\infty, & i>t.
\end{cases}
$$

softmax 后未来位置的权重就是 0。这样各位置可以在训练时并行计算，同时保持从左到右预测所需的可见范围。第一段转写在老师刚开始写 mask 的位置结束，第二段从另一个问题接上：如果不使用 softmax，而采用更容易重排求和的线性注意力，因果前缀又能不能写成递归状态？

## 6. 课件延伸：Transformer block、Multi-Head 与 ViT

下面这些内容在 `attention_transformer.pdf` 与 `ViT.pptx` 中有明确材料，但当前转写没有覆盖到全部讲解顺序，故作为课件阅读提纲，而不是逐字确认的课堂进度。

Transformer block 把 Self-Attention 和 position-wise feed-forward network（FFN）组合起来，并通过 residual connection 与 layer normalization 稳定深层计算。LayerNorm 按单个样本的特征维归一化；BatchNorm 则依赖 batch 维统计量。Multi-Head Attention 用多组不同的 $W_Q,W_K,W_V$ 并行计算，让各头从不同表示子空间学习关系，最后拼接并投影。位置编码则补上注意力运算本身不包含的顺序信息。

在 encoder–decoder Transformer 里，decoder 的 masked self-attention 只能读取已生成前缀；cross-attention 再用 decoder 表示作 query，读取 encoder 输出的 keys 和 values。ViT 把图像切成固定大小 patch，将每个 patch 展平并映射成 token，加入位置表示和 class token 后交给 Transformer encoder 做分类。老师在录音中说本次只会引入 ViT 基本概念，细节和应用留到 Quiz 后的下次课；`ViT.pptx` 中更广的 DeiT、Swin、PVT、MLP-Mixer、DETR、SETR 等属于课件延伸，不能据此写成今天已经讲完。

## 7. 线性注意力：把前缀读取改写成递归状态

老师先把普通 self-attention 抽象成“相似度权重乘 value，再对历史位置求和”。标准形式在相似度上使用 softmax；如果将它换成可分解的线性相似度，例如 $q_t^\top k_s$，自回归位置 $t$ 的输出可以写为：

$$
y_t=\sum_{s\le t}v_s(k_s^\top q_t)
=\left(\sum_{s\le t}v_sk_s^\top\right)q_t.
$$

关键一步是把与历史位置 $s$ 无关的当前 query $q_t$ 移到求和之外。令括号里的矩阵为记忆状态 $S_t$，就得到：

$$
S_t=\sum_{s\le t}v_sk_s^\top
=S_{t-1}+v_tk_t^\top,
\qquad y_t=S_tq_t.
$$

若 $v_t\in\mathbb{R}^{d_v}$、$k_t,q_t\in\mathbb{R}^{d_k}$，则 $S_t\in\mathbb{R}^{d_v\times d_k}$。每一步把新的 key–value 外积写入状态，再用 query 读取。实现时不必保存并比较所有 $T$ 个位置组成的 $T\times T$ 注意力矩阵；在特征维固定时，按序列逐步更新的计算随长度近似线性增长。代价是这里的线性相似度不等于 softmax attention，表达能力和归一化行为也会不同。

这就是老师把线性注意力和 RNN、state-space model 联系起来的方式：历史被压进一个可递推的状态，当前输出由状态和当前输入共同决定。它不是说标准 softmax attention 与 RNN 完全相同；递归形式来自特定的线性相似度以及对求和次序的重排。课堂还提到，这类方法适合特别长的序列或文档，因为减少了显式构造两两位置关系的开销；使用时仍要权衡速度与准确性。

![10 月 20 日板书：Q/K/V 投影、attention map、线性状态与 DeltaNet](/blog/2026/10-20/aims5710-attention-and-linear-attention-board.jpg)

### DeltaNet 怎样改写记忆

只把每个新外积加进 $S_t$，旧信息会一直留在状态里。老师用联想记忆解释更新问题：先用旧状态按当前 key 读出已有值，再比较它和新目标值，针对差异修正对应地址。板书和转写给出的步骤是：

$$
\hat v_t=S_{t-1}k_t,
\qquad
S_t=S_{t-1}+\beta_t(v_t-\hat v_t)k_t^\top.
$$

$\hat v_t$ 是旧记忆对当前 key 的读取结果；$v_t-\hat v_t$ 是写入误差，外积 $(v_t-\hat v_t)k_t^\top$ 把修正施加到与 $k_t$ 相关的状态方向，$\beta_t$ 控制更新幅度。老师说明 $\beta_t$ 可以随时间变化，需要由模型学习。展开后也可写成

$$
S_t=S_{t-1}(I-\beta_tk_tk_t^\top)+\beta_tv_tk_t^\top.
$$

老师把这个过程口头概括为“遗忘”：新信息覆盖旧记忆中与当前地址冲突的部分。更精确地说，公式直接规定的是按预测误差进行写入；$\beta_t$ 越大，修正越激进，但其实际效果还取决于 key 的尺度，不能把它理解为对整份记忆统一乘上一个遗忘系数。这个更新比单纯追加外积更能处理覆盖，且保留递归状态的计算形式。

## 8. Quiz 1 复习：老师要求会推导的基础

课前通知把 Quiz 1 范围定为 Lectures 1–6、截至 RNN，三小时、三道手写题、闭卷、无计算器，可带一张双面 cheat sheet。后半段的复习不是只重复 RNN；老师把此前讲过的分类、神经网络、CNN、RNN 和优化内容都带了一遍，并强调重点是理解基本概念、简单计算和梯度推导，不需要死背 LSTM、GRU 或优化器的每一条公式。

![Quiz 1 复习板书：RNN、CNN、感受野、softmax 与交叉熵](/blog/2026/10-20/aims5710-quiz-review-board.jpg)

### Softmax 与 cross-entropy

给定分类 logits $z_1,\ldots,z_C$，softmax 把它们转成概率：

$$
p_i=\frac{e^{z_i}}{\sum_{j=1}^{C}e^{z_j}}.
$$

对 one-hot 标签 $y$，交叉熵为 $L=-\sum_i y_i\log p_i$。利用 $\sum_i y_i=1$，可以把它改写为

$$
L(z,y)=-\sum_i y_i z_i+\log\sum_{j=1}^{C}e^{z_j},
\qquad
\frac{\partial L}{\partial z_i}=p_i-y_i.
$$

先对概率求导，有 $\partial L/\partial p_i=-y_i/p_i$；再把 softmax 代回去，可将损失改写为上面的 logits 形式。推导时，第一项对 $z_i$ 的导数是 $-y_i$，log-sum-exp 项的导数是 softmax 概率 $p_i$，因此 $\partial L/\partial z_i=p_i-y_i$。老师明确说要会计算 $p$、$L$ 以及它们对 $p$、$z$ 的梯度，并建议自己把这个结果重新推一遍。

![Softmax、交叉熵与神经网络反向传播板书](/blog/2026/10-20/aims5710-softmax-cross-entropy-board.jpg)

### 全连接层的反向传播与深层网络问题

一层线性变换加激活函数可以记作 $z=Wx+b$、$y=\sigma(z)$。若 $\delta=\partial L/\partial z$，矩阵微分直接给出：

$$
\frac{\partial L}{\partial W}=\delta x^\top,
\qquad
\frac{\partial L}{\partial b}=\delta,
\qquad
\frac{\partial L}{\partial x}=W^\top\delta.
$$

若把传入的梯度定义在激活输出 $y$ 上，还要先乘上激活函数的导数，才能得到这里的 $\delta$。多层网络反向传播时，$W^\top\delta$ 把梯度送回前一层，激活导数则按链式法则逐层参与计算。老师建议记住权重梯度是误差与输入的外积；这比逐元素展开更容易检查维度，也更便于做手算。

激活函数要能比较适用情形：sigmoid 把输出压到 $(0,1)$，但大幅度输入时容易饱和；tanh 输出以零为中心，也有饱和区；ReLU 计算简单，正半轴梯度不衰减，但负半轴可能长期没有梯度。网络表达能力强也更容易过拟合，课件提到 dropout；深层反传还可能出现梯度消失或爆炸。老师复习了两种处理思路：BatchNorm 调整一批样本的中间激活，残差连接 $\hat y(x)=x+g(x)$ 则给梯度留一条直接的 identity 路径。

BatchNorm 训练时用当前 mini-batch 的均值与标准差标准化；推理时通常改用训练阶段累计的 running statistics。课堂特别问了推理时只有单个样本、无法组成 batch 时怎么办，答案是用指数移动平均维护的均值和方差，而不是拿单个样本临时估计整批统计量。复习时应同时说清楚训练和推理统计量的区别，以及归一化为何有助于梯度传播。

### CNN 的归纳偏置与感受野

CNN 的局部连接和共享卷积核把“邻近像素更相关”这类结构先验写进网络，也减少了相较全连接层所需的参数。严格区分术语时，卷积对平移主要表现为 equivariance（输入平移会使特征图相应平移）；池化或后续汇聚才可能带来一定程度的 invariance。局部计算的代价是单层卷积难以利用远处的全局上下文。

扩大有效感受野可以让更深层的特征整合更大范围的信息。白板列出 striding、pooling 和 dilation；它们的取舍不同：stride 与 pooling 会降低空间分辨率，dilation 扩大采样间隔但保留特征图尺寸。老师要求回顾卷积定义与梯度，并能解释这些操作怎样改变感受野、信息分辨率和计算量。

### RNN、BPTT 与门控

Quiz 范围写到 recurrent neural network。复习时要会写递归状态的定义，解释 Backpropagation Through Time 为什么把同一组递归计算沿时间展开，以及梯度在长路径上反复相乘后可能变得很小或很大。LSTM 和 GRU 用门控调节信息保留与更新；老师说重点是理解为什么需要 gating mechanisms，不要求背下整套门控公式。

线性注意力这一段也回扣了这部分内容：RNN 显式递推一个状态，线性注意力在特定相似度下同样能把历史前缀累积成可递推的记忆矩阵。两者的状态结构和表达能力不同，但都说明了序列模型可以通过更新有限状态来携带历史。

### 优化器与参数初始化

老师把优化方法分为一阶和二阶。GD/SGD 根据梯度更新参数；Momentum 累积历史方向，减少随机梯度的抖动，并帮助在曲率不同的方向上更稳定地前进。AdaGrad 会按累计梯度平方调整各参数步长，Adam 则结合梯度与梯度平方的指数移动平均。复习重点是这些缩放和动量分别在解决什么问题，不是背出每个符号。

Newton's method 属于二阶方法，利用 Hessian 描述局部曲率，因此需要比一阶梯度更多的计算和矩阵运算。初始化方面，课堂点名 Xavier 与 Kaiming/He：它们按层的 fan-in/fan-out 设定权重尺度，目标是让前向激活和反向梯度的方差在层间不要迅速放大或缩小。Xavier 常配合 sigmoid 或 tanh 一类激活；He 初始化则考虑了 ReLU 会截断一部分激活。老师要求理解为什么要这样设定，并能说明公式如何由方差保持条件得到。

复习 RNN 时可与 [10 月 13 日的 RNN 与 BPTT 笔记](/blog/2026/2026-10-13-aims5710-rnn/) 对读。10 月 20 日这两段课堂内容现在连成一条完整路线：先从序列对齐推到按内容读取，再把线性注意力重写为递归记忆；随后回顾 Quiz 1 需要掌握的分类损失、反向传播、CNN、RNN 和优化基础。Transformer block、Multi-Head 及 ViT 的详细结构仍按课件阅读范围处理，不把课件中的全部内容误写成今天课堂逐项讲完。
