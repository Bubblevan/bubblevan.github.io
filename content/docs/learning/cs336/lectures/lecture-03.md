---
title: "L03 · Transformer"
weight: 3
date: 2026-08-16
updated: 2026-08-16
course: "CS336"
topics: ["CS336", "transformer", "inference"]
aliases:
  - /blog/2026/2026-08-16-cs336-lecture3/
---

# 0. 先建立 Lecture 3 的总框架

如果 Lecture 2 的问题是这个模型要花多少钱，那么 Lecture 3 的问题就是 **在预算固定的情况下，模型究竟应该怎么设计**？

2017 年原始 Transformer 和今天 decoder-only LLM 的“标准配方”已经明显不同了。我们可以粗略把现代 dense LLM block 想成：

```python
x = x + Attention(RMSNorm(x))
x = x + SwiGLU(RMSNorm(x))
```

Attention 内部：

```text
Q = X Wq
K = X Wk
V = X Wv

Q = RoPE(Q)
K = RoPE(K)

A = softmax(Q K^T / sqrt(d_head) + causal_mask)

Y = A V
Y = Y Wo
```

重复 (L) 次之后：

```text
RMSNorm
   ↓
LM Head
   ↓
logits over vocabulary
```

而 **CS336 A1 reference interface 恰恰就是这个体系**：pre-norm Transformer block、RMSNorm、SwiGLU、RoPE，而且 RoPE 的维度明确是 `d_model // num_heads`。

那么问题来了，为什么现代模型逐渐收敛到了这一套设计？

---

# 1. Transformer Architecture 其实是在设计一条信息高速公路

我们先忘掉 Attention。

假设一个 block 只是：

$$
x_{l+1}=x_l+F(x_l)
$$

这就是 residual connection。

为什么它这么重要？

因为如果有 40、80、100 层网络，信息需要连续经过很多非线性变换：

$$
x_0
\to F_1
\to F_2
\to \cdots
\to F_{100}.
$$

那么梯度也必须反向穿过：

$$
J_{F_{100}}J_{F_{99}}\cdots J_{F_1}.
$$

这些 Jacobian 连乘非常容易爆炸或者消失。

但 residual：

$$
x_{l+1}=x_l+F(x_l)
$$

求导：

$$
\frac{\partial x_{l+1}}{\partial x_l}
=====================================

I+J_F.
$$

注意那个：

$$
\boxed{I}
$$

它意味着：

> 就算 (F) 那条路训练得很糟，至少还有一条 identity path。

因此你可以把整个 Transformer 想成：

```text
=============================== residual stream ======================>
      │                  │                    │
      ↓                  ↓                    ↓
   Attention            MLP                Attention
      │                  │                    │
      └──── add ─────────┘                    │
```

**residual stream 才是 Transformer 的主干。**

Attention 和 MLP 更像不断往这条信息流里面“写东西”的插件。

这个理解非常重要，因为马上就能解释为什么现代 LLM 喜欢 **pre-norm**。

---

# 2. Post-Norm 和 Pre-Norm 到底差在哪？

原始 Transformer 常见形式是：

$$
y=\operatorname{Norm}(x+F(x)).
$$

也就是：

```text
x
│
├──────────────┐
│              ↓
│              F
│              │
└──── + ───────┘
       │
      Norm
       ↓
       y
```

这是 **post-norm**。

问题在哪？

求导：

$$
\frac{\partial y}{\partial x}
=============================

J_{\text{Norm}}
(I+J_F).
$$

看到问题了吗？

本来 residual 给我们留了一条漂亮的：

$$
I
$$

但现在连这条 identity path 也必须经过：

$$
J_{\text{Norm}}.
$$

---

现代 LLM 常见的 pre-norm 则是：

$$
y=x+F(\operatorname{Norm}(x)).
$$

结构：

```text
x ───────────────────────────────┐
│                                │
↓                                │
Norm                             │
│                                │
F                                │
│                                │
└────────────────────── + ───────┘
                           ↓
                           y
```

求导：

$$
\frac{\partial y}{\partial x}
=============================

I+
J_FJ_{\text{Norm}}.
$$

这一次，真正出现了一个**完全不受其他操作影响的 (I)**。

所以你可以这样记：

> **Pre-norm 最大的直觉，就是保护 residual stream 的 identity highway。**

这也是为什么 CS336 A1 的官方实现接口明确要求 **pre-norm Transformer block**。([GitHub][2])

注意，不要因此记成“post-norm 是错误设计”。现代模型仍然存在各种 pre/post 双重 normalization 的方案；例如 Gemma 2 就在 sublayer 输入和输出都使用 RMSNorm。真正要理解的是：**norm 放在哪里，会改变 residual path 和优化稳定性。** ([arXiv][3])

---

# 3. 为什么从 LayerNorm 换成 RMSNorm？

LayerNorm 你应该见过：

$$
\mu=\frac1d\sum_i x_i
$$

$$
\sigma^2
========

\frac1d\sum_i(x_i-\mu)^2
$$

然后：

$$
\operatorname{LN}(x)
====================

\gamma
\frac{x-\mu}{\sqrt{\sigma^2+\epsilon}}
+\beta.
$$

它做了两件事：

**re-centering：**

$$
x\rightarrow x-\mu
$$

以及 **re-scaling：**

$$
x\rightarrow
\frac{x}{\text{scale}}.
$$

RMSNorm 的问题意识非常简单：

> 我真的需要减均值吗？

于是 RMSNorm 直接定义：

$$
\operatorname{RMS}(x)
=====================

\sqrt{
\frac1d
\sum_i x_i^2+\epsilon
}
$$

然后：

$$
\boxed{
\operatorname{RMSNorm}(x)
=========================

\gamma\odot
\frac{x}{\operatorname{RMS}(x)}
}
$$

没了。

没有：

$$
x-\mu.
$$

RMSNorm 原论文的核心论点就是：去掉 re-centering，只保留 re-scaling，仍然可以获得与 LayerNorm 相当的效果，同时简化计算。([arXiv][4])

这时候你应该把 Lecture 2 联系起来：

> “少几个 FLOPs 有什么了不起？”

确实，Norm 的 FLOPs 相对于 GEMM 微不足道。

但是它是一个典型的 elementwise/reduction kernel：

```text
read x
→ reduce
→ normalize
→ scale
→ write x
```

这种东西可能更受 **memory traffic / kernel overhead** 影响。

所以现代 architecture 的简化不仅是数学审美，也会和 systems cost 联系起来。

---

# 4. Attention 到底是在干什么？

假设 hidden states：

$$
X\in\mathbb R^{B\times T\times d}.
$$

先做三个 projection：

$$
Q=XW_Q,
\qquad
K=XW_K,
\qquad
V=XW_V.
$$

直观解释：

* (Q)：我这个 token **想找什么？**
* (K)：我这个 token **能被别人根据什么找到？**
* (V)：如果别人关注我，我**提供什么信息？**

比如句子：

> Alice gave Bob her book because **she** was leaving.

当处理 `she` 时：

```text
Query(she):
    “我要找一个可能对应当前代词的人”
```

而 Alice：

```text
Key(Alice):
    “我是一个可能被代词指代的人”
Value(Alice):
    “Alice 相关的语义信息”
```

于是：

$$
QK^\top
$$

实际上就是在算：

$$
\boxed{\text{每个 query 与每个 key 的匹配程度}}
$$

再：

$$
A=
\operatorname{softmax}
\left(
\frac{QK^\top}{\sqrt{d_k}}
\right)
$$

得到 attention probability：

$$
A_{ij}
======

\text{token i 对 token j 的关注程度}.
$$

最后：

$$
AV
$$

就是根据这些概率，把其他 token 的 value 加权读取回来。

---

# 5. 为什么要除以 (\sqrt{d_k})？

这个问题一定要会推。

假设：

$$
q_i,k_i
$$

都是均值 0、方差 1 的随机变量。

dot product：

$$
q^\top k
========

\sum_{i=1}^{d_k}q_i k_i.
$$

每一项方差大概是 1，因此：

$$
\operatorname{Var}(q^\top k)
\approx d_k.
$$

所以标准差：

$$
\operatorname{Std}(q^\top k)
\approx \sqrt{d_k}.
$$

如果 (d_k=128)，dot product 自然尺度已经大约是：

$$
\sqrt{128}\approx11.3.
$$

直接扔进 softmax：

$$
\operatorname{softmax}(11,-5,-3,\dots)
$$

就很容易非常尖锐。

于是除以：

$$
\sqrt{d_k}
$$

让 logits 的初始尺度保持在 (O(1))。

所以：

$$
\boxed{
\operatorname{Attention}
========================

\operatorname{softmax}
\left(
\frac{QK^\top}{\sqrt{d_k}}
\right)V
}
$$

里的 scaling 不是魔法常数，而是**方差控制**。

---

# 6. Multi-Head Attention 为什么不是“多做几遍 Attention”？

假设：

$$
d_{\text{model}}=768,
\qquad H=12.
$$

那么：

$$
d_{\text{head}}
===============

# \frac{768}{12}

64.

$$

我们 reshape：

$$
[B,T,768]
\rightarrow
[B,T,12,64].
$$

每个 head 在一个不同的 64 维子空间里面做 attention。

你可以理解成：

```text
Head 1：可能偏局部语法
Head 2：可能偏实体关系
Head 3：可能偏长距离依赖
...
```

当然这只是帮助理解，真实 head 不保证有这么漂亮的人类语义分工。

关键是：

$$
H\times d_{\text{head}}
=======================

d_{\text{model}}.
$$

如果保持 (d_{\text{model}}) 不变，只改变 head 数，Q/K/V projection 本身通常仍然是：

$$
d\times d
$$

所以**参数量不会因为 head 数增加就线性增加**。

这就是一个典型 Lecture 3 思维：

> hyperparameter 不是孤立数字；先问它改变什么 tensor shape，然后问参数、FLOPs、表达能力分别发生什么变化。

A1 的官方接口也要求 `d_model` 能被 `num_heads` 整除。([GitHub][2])

---

# 7. 可是 Attention 根本不知道“第几个 token”

这里开始进入 RoPE。

假设：

```text
A B C
```

和：

```text
C B A
```

如果没有 positional information，self-attention 本身对排列具有相应的 permutation equivariance。

也就是说：

> Attention 能看到“有哪些 token”，却不知道它们处于什么位置。

原始 Transformer 使用 additive sinusoidal positional encoding，大概：

$$
X_i
\leftarrow
X_i+P_i.
$$

现代 decoder-only LLM 一个非常常见的选择则是：

$$
\boxed{\text{RoPE}}
$$

CS336 A1 也明确要求你实现它。([GitHub][2])

---

# 8. RoPE 不要背公式，先把它想成“旋转”

考虑二维向量：

$$
q=
\begin{bmatrix}
q_1\q_2
\end{bmatrix}.
$$

位置 (m) 对它做旋转：

$$
R(m\theta)
==========

\begin{bmatrix}
\cos m\theta&-\sin m\theta\
\sin m\theta&\cos m\theta
\end{bmatrix}.
$$

那么：

$$
q_m=R(m\theta)q.
$$

key 也一样：

$$
k_n=R(n\theta)k.
$$

现在计算 attention dot product：

$$
q_m^\top k_n.
$$

代进去：

$$
q^\top R(m\theta)^\top R(n\theta)k.
$$

旋转矩阵有一个漂亮性质：

$$
R(m\theta)^\top R(n\theta)
==========================

R((n-m)\theta).
$$

于是：

$$
\boxed{
q_m^\top k_n
============

q^\top
R((n-m)\theta)
k
}
$$

看到了吗？

虽然我们分别给 Q 和 K 编码的是：

$$
m,\quad n
$$

但它们做 dot product 后自然变成：

$$
\boxed{n-m}.
$$

也就是**相对位置**。

这就是 RoPE 最漂亮的数学直觉：用旋转编码绝对位置，同时让 attention score 自然表现出相对位置依赖。RoPE 原论文正是利用这种旋转结构编码位置；CS336 A1 则要求把 RoPE 施加在每个 attention head 的 Q/K 上，而不是 V 上。([arXiv][5])

---

# 9. 那高维 (d_{\text{head}}=64) 怎么旋转？

不是拿一个 64×64 巨型旋转矩阵硬乘。

而是把维度两两配对：

$$
(x_0,x_1),
(x_2,x_3),
\dots
$$

每一对形成二维平面：

$$
\begin{bmatrix}
x_{2i}'\
x_{2i+1}'
\end{bmatrix}
=============

R(m\theta_i)
\begin{bmatrix}
x_{2i}\
x_{2i+1}
\end{bmatrix}.
$$

而不同 pair 使用不同 frequency：

$$
\theta_i
========

\Theta^{-2i/d}.
$$

所以一些维度旋转得快：

```text
高频 → 对近距离位置变化敏感
```

另一些旋转得慢：

```text
低频 → 能覆盖更长尺度
```

可以把它想成：

> 给每个 token 戴了一组不同转速的钟表。

位置改变时，各个钟表同时旋转。

这一思想后来也直接影响长上下文扩展时对 RoPE base / frequency 的调整；例如 Gemma 3 在 global attention 层增大了 RoPE base frequency 配置来支持更长上下文。([arXiv][6])

---

# 10. Attention 负责“token 之间通信”，FFN 在干嘛？

这是很多初学者最容易忽略的东西。

一个 Transformer block 里：

$$
\text{Attention}
$$

负责：

$$
\boxed{\text{不同 token 之间交换信息}}
$$

而 FFN：

$$
\boxed{\text{每个 token 独立地做 feature transformation}}
$$

普通 FFN：

$$
\operatorname{FFN}(x)
=====================

W_2\phi(W_1x).
$$

注意：

$$
[B,T,d]
\rightarrow
[B,T,d_{ff}]
\rightarrow
[B,T,d].
$$

对于每个 token 都执行同一套 MLP。

因此：

```text
Attention:
token ↔ token communication

FFN:
feature → feature computation
```

这是非常值得记住的一对概念。

---

# 11. 为什么原来的 ReLU/GELU 后来变成 SwiGLU？

普通 Transformer FFN：

$$
y=W_2\phi(W_1x).
$$

SwiGLU 则多了一条 projection：

$$
a=W_1x
$$

$$
b=W_3x
$$

然后：

$$
\boxed{
y=
W_2
\left[
\operatorname{SiLU}(a)\odot b
\right]
}
$$

其中：

$$
\operatorname{SiLU}(x)
======================

x\sigma(x).
$$

所以代码几乎就是：

```python
a = W1(x)
b = W3(x)

gate = silu(a)

h = gate * b

out = W2(h)
```

A1 官方接口也正好给了三个矩阵：

```text
W1: d_model → d_ff
W3: d_model → d_ff
W2: d_ff    → d_model
```

([GitHub][2])

---

## 关键不是 SiLU，而是那个乘法

普通 FFN：

$$
\phi(W_1x).
$$

SwiGLU：

$$
\operatorname{SiLU}(W_1x)
\odot
W_3x.
$$

你可以把：

$$
\operatorname{SiLU}(W_1x)
$$

理解成：

> **gate：哪些 feature 应该打开？打开多少？**

而：

$$
W_3x
$$

是：

> **content：真正被传输的 feature 是什么？**

于是：

$$
\text{output}
=============

\text{gate}
\times
\text{content}.
$$

这给网络引入了一种 multiplicative interaction。

GLU 系列论文系统比较了 GLU、ReGLU、GEGLU、SwiGLU 等变体，并发现若干 gated FFN 变体相对于传统 ReLU/GELU FFN 能带来质量提升。([arXiv][7])

---

# 12. 为什么 SwiGLU 的 (d_{ff}) 经常不是 (4d)？

这里正是 Lecture 3 的 **hyperparameter accounting**。

传统 FFN 如果：

$$
d_{ff}=4d
$$

那么两个矩阵：

$$
W_1:d\rightarrow4d
$$

$$
W_2:4d\rightarrow d.
$$

参数量：

$$
4d^2+4d^2
=========

\boxed{8d^2}.
$$

但 SwiGLU 有三个矩阵。

设 hidden width 为 (m)：

$$
W_1:d\rightarrow m
$$

$$
W_3:d\rightarrow m
$$

$$
W_2:m\rightarrow d.
$$

所以：

$$
N_{\text{SwiGLU}}
=================

# dm+dm+md

3dm.
$$

如果希望它和传统 (4d) FFN 参数量差不多：

$$
3dm=8d^2.
$$

所以：

$$
\boxed{
m=\frac83d
}
$$

也就是：

$$
d_{ff}
\approx
2.67d.
$$

这就是为什么你看到一些现代 LLM：

```text
d_model = 4096
d_ff ≈ 11008
```

而不是简单的：

```text
16384
```

不要背 11008。

你要会自己从：

$$
\boxed{3d,d_{ff}\approx8d^2}
$$

推出来。

这才叫真的理解 architecture。

---

# 13. 一个 Transformer Layer 到底多少参数？

现在可以自己估算。

假设 hidden size：

$$
d.
$$

Attention 有：

$$
W_Q,W_K,W_V,W_O.
$$

如果都是：

$$
d\times d
$$

那么：

$$
N_{\text{attn}}
\approx4d^2.
$$

SwiGLU：

$$
N_{\text{ffn}}
==============

3dd_{ff}.
$$

如果：

$$
d_{ff}\approx\frac83d,
$$

那么：

$$
N_{\text{ffn}}
\approx8d^2.
$$

所以一个 Transformer block：

$$
\boxed{
N_{\text{layer}}
\approx12d^2
}
$$

忽略 norm 等小参数。

于是 (L) 层：

$$
\boxed{
N_{\text{blocks}}
\approx12Ld^2
}
$$

然后别忘了 embedding：

$$
Vd
$$

以及 LM head：

$$
Vd
$$

如果 weight tying，则可能共享。

所以一个很有用的 napkin formula 是：

$$
\boxed{
N
\approx
12Ld^2+Vd
}
$$

或者 untied 情况：

$$
12Ld^2+2Vd.
$$

你现在就能看到 Lecture 2 和 Lecture 3 连起来了：

Lecture 2：

$$
C_{\text{train}}\approx6ND.
$$

Lecture 3：

$$
N\approx12Ld^2+\cdots.
$$

于是 architecture choice 最终直接变成 **训练 FLOPs**。

---

# 14. Hyperparameter 不是一个“调参表”，而是一组 trade-off

假设参数预算大约固定。

你可以造：

```text
更深、更窄
```

也可以：

```text
更浅、更宽
```

因为：

$$
N\sim Ld^2.
$$

如果：

$$
d\rightarrow2d
$$

参数大约：

$$
\rightarrow4\times.
$$

而：

$$
L\rightarrow2L
$$

参数只是：

$$
\rightarrow2\times.
$$

所以 width 非常昂贵。

但是 depth 也不是免费午餐。

100 层意味着：

```text
layer1
 ↓
layer2
 ↓
layer3
 ...
 ↓
layer100
```

有更长的 sequential dependency。

即使每层 GPU 很快：

> 下一层仍然必须等待上一层。

而宽模型的大 GEMM 往往更容易把 accelerator 喂饱。

于是所谓：

> “多少层最好？”

不存在脱离硬件、参数预算和训练规模的神圣答案。

这正是 Lecture 3 所谓 architectures **and hyperparameters** 的核心思想，而不是给你一张万能参数表。官方课程本身也把 Lecture 3 放在 resource accounting 后、GPU/kernels 前，就是要把模型结构和系统代价串起来看。([Stanford CS336][1])

---

# 15. Vocabulary size 也是 architecture hyperparameter

假设：

$$
V=32,000,\quad d=4096.
$$

Embedding 参数：

$$
Vd
\approx131M.
$$

如果：

$$
V=250,000,
$$

则：

$$
Vd
\approx1.024B.
$$

光 embedding 就十亿参数。

但大 vocabulary 的好处是：

> 同一句话可能被切成更少 token。

因此：

$$
V\uparrow
$$

可能让：

$$
T\downarrow.
$$

这又会影响：

$$
\text{attention FLOPs},
\quad
\text{KV cache},
\quad
\text{训练 tokens},
\quad
\text{多语言覆盖}.
$$

所以 tokenizer 绝对不是模型外部的“文本预处理工具”。

Lecture 1 的 BPE 和 Lecture 3 的 architecture 在这里重新连接起来。

现实模型也确实会做完全不同的取舍；例如 Gemma 2/3 使用了 256K vocabulary，并明确指出较大的 vocabulary 与多语言覆盖相关，同时 embedding 参数本身已经成为不可忽视的一部分。([arXiv][3])

---

# 16. Lecture 3 后半为什么突然开始讲“训练稳定性”？

因为 architecture 不只是：

> 最终 validation loss 能不能低。

还有一个更加现实的问题：

$$
\boxed{\text{这个模型能不能稳定训练完？}}
$$

如果你训练一个 1000 GPU、两个月的任务：

```text
step 10
step 1000
step 100000
step 500000
   ↓
loss explode
NaN
```

那是灾难。

于是现代 LLM architecture 出现了一系列看起来像“小补丁”的东西：

```text
RMSNorm
pre/post norm arrangement
QK-Norm
z-loss
logit soft-capping
gradient clipping
...
```

它们共同解决的是：

$$
\boxed{\text{控制 activation / attention / logits 的尺度}}
$$

---

# 17. z-loss 到底解决什么？

cross entropy 的 logits：

$$
z_1,z_2,\ldots,z_V.
$$

softmax：

$$
p_i=
\frac{e^{z_i}}
{\sum_j e^{z_j}}.
$$

有个非常特殊的性质。

如果所有 logits 同时加：

$$
c,
$$

那么：

$$
\frac{e^{z_i+c}}
{\sum_j e^{z_j+c}}
==================

\frac{e^ce^{z_i}}
{e^c\sum_j e^{z_j}}
===================

p_i.
$$

所以：

$$
\boxed{
\operatorname{softmax}(z+c)=\operatorname{softmax}(z)
}
$$

这意味着 cross entropy 根本不关心 logits 的共同 offset。

因此模型理论上可能学出：

```text
10001
9998
10004
10000
...
```

和：

```text
1
-2
4
0
...
```

softmax 完全一样。

但前者数值上危险得多。

于是定义：

$$
Z=\sum_i e^{z_i}
$$

加一个 auxiliary loss：

$$
\boxed{
L_z=
\alpha(\log Z)^2
}
$$

就是告诉模型：

> 概率排序你自己学，但不要让整个 logits scale/offset 无限制漂走。

PaLM 就使用过这种 z-loss，并报告其目的是把 softmax normalizer (\log Z) 拉近 0，从而改善训练稳定性。([ar5iv][8])

---

# 18. QK-Norm 为什么比 (1/\sqrt{d}) 更进一步？

刚才我们说：

$$
\frac{QK^\top}{\sqrt d}
$$

能控制初始化时 dot product 的典型尺度。

关键词是：

> **初始化时。**

训练十万 step 后呢？

模型可能学出：

$$
|q|\rightarrow100
$$

$$
|k|\rightarrow200.
$$

那么：

$$
q^\top k
$$

依然可以巨大。

除：

$$
\sqrt d
$$

并不能阻止 learned norm 增长。

QK-Norm 的想法：

$$
q\rightarrow
\frac{q}{|q|}
$$

$$
k\rightarrow
\frac{k}{|k|}
$$

再进行 attention。

这样：

$$
q^\top k
$$

主要表示的是：

$$
\boxed{\text{direction similarity}}
$$

而不是让模型靠无限增加 vector norm 把 softmax 推进饱和区。

原始 QK-Norm 工作就是在 head dimension 上对 query/key 做归一化，再使用可学习尺度代替传统的固定 (1/\sqrt d)。([arXiv][9])

而这并不是历史上的冷门技巧：Gemma 3 明确报告，它从 Gemma 2 的 attention logit soft-capping 转向了 QK-Norm。([arXiv][6])

---

# 19. Logit soft-capping 又是什么？

更暴力。

假设 attention logits 是：

$$
z.
$$

直接：

$$
\boxed{
\tilde z
========

c\tanh(z/c)
}
$$

因为：

$$
-1<\tanh(x)<1,
$$

所以：

$$
-c<\tilde z<c.
$$

无论网络想产生：

$$
10^2,\quad10^4,\quad10^{10},
$$

最后都被压到：

$$
[-c,c].
$$

所以 soft-cap 就像：

> 给 logits 装一个保险杠。

Gemma 2 就在 attention logits 和最终 logits 上使用了这种 `soft_cap * tanh(logits / soft_cap)` 机制；Gemma 3 后来在 architecture 中改用了 QK-Norm。([arXiv][3])

这里别得出“QK-Norm 比 soft-cap 高级”这种结论。

Lecture 3 真正希望你看到的是：

$$
\boxed{\text{architecture evolution 很大一部分是在驯服数值尺度}}
$$

---

# 20. 接着视角从“怎么训练”转向“怎么推理”

这是 Lecture 3 特别值得你注意的一层。

训练时我们喜欢：

$$
\text{MHA}
$$

但 autoregressive inference：

```text
token 1
→ token 2
→ token 3
→ ...
```

每一步如果重新计算之前所有 token 的 K/V：

$$
O(T^2)
$$

非常浪费。

所以会缓存历史：

$$
K_1,V_1,
K_2,V_2,
\dots,
K_T,V_T.
$$

这就是：

$$
\boxed{\text{KV cache}}
$$

大致显存：

$$
M_{\text{KV}}
\approx
2
\times
B
\times
T
\times
L
\times
H_{KV}
\times
d_h
\times
\text{bytes}.
$$

这个公式你一定要会看。

其中那个：

$$
2
$$

来自：

$$
K+V.
$$

---

# 21. MHA → MQA → GQA 的动机一下就明白了

普通 Multi-Head Attention：

```text
32 Query heads
32 Key heads
32 Value heads
```

那么：

$$
H_{KV}=32.
$$

Multi-Query Attention：

```text
32 Query heads
 1 Key head
 1 Value head
```

于是 KV cache：

$$
\boxed{\approx\frac1{32}}
$$

当然 quality 可能受到影响。

Grouped-Query Attention 取中间：

```text
32 Query heads
 8 KV heads
```

例如每 4 个 query heads 共用一套 K/V：

```text
Q0 Q1 Q2 Q3  ─→ KV0
Q4 Q5 Q6 Q7  ─→ KV1
...
```

那么 KV cache 相比普通 32-head MHA 大约：

$$
\frac8{32}
==========

\boxed{\frac14}.
$$

GQA 原论文的定义正是：KV head 数大于 1、但少于 query heads；论文报告它能在接近 MHA 质量的同时获得接近 MQA 的推理速度收益。([arXiv][10])

看到 Lecture 2 回来了吗？

autoregressive decode 很容易：

$$
\boxed{\text{memory bandwidth bound}}.
$$

因此减少：

$$
\text{KV cache bytes transferred}
$$

可能比少几个 FLOPs 更重要。

**Lecture 2 的 arithmetic intensity，到了 Lecture 3 就变成 architecture choice。**

---

# 22. 为什么还有 Sliding-Window Attention？

full attention：

$$
T\times T.
$$

complexity：

$$
O(T^2).
$$

如果每个 token 只看最近：

$$
w
$$

个 token：

$$
O(Tw).
$$

假设：

$$
T=128K,\quad w=4K,
$$

差异就非常巨大。

但如果所有层都是 local：

```text
token 100000
```

无法直接读取：

```text
token 1
```

的信息。

所以一种现代设计是：

```text
local
local
local
local
local
global
local
local
...
```

用很多廉价 local attention，偶尔插 global attention。

例如 Gemma 3 就采用了 5 个 local layer 对 1 个 global layer 的设计，明确把这样做与长上下文下的 KV-cache memory cost 联系起来。([arXiv][6])

所以：

$$
\boxed{\text{“Attention architecture” 同时是模型能力问题和 serving cost 问题。}}
$$

---

# 23. 现在把 Lecture 3 和 A1 对起来

A1 官方要求不是随手凑出来的一套 Transformer。

它基本是在让你亲手实现一套现代 decoder-only dense LM 的核心骨架：

```text
token ids
     │
     ↓
Embedding
     │
     ↓
┌───────────────────────────────┐
│ RMSNorm                       │
│    ↓                          │
│ Q/K/V projections            │
│    ↓                          │
│ RoPE(Q), RoPE(K)              │
│    ↓                          │
│ causal multi-head attention   │
│    ↓                          │
│ residual add                  │
│                               │
│ RMSNorm                       │
│    ↓                          │
│ SwiGLU                        │
│    ↓                          │
│ residual add                  │
└───────────────────────────────┘ × L
     │
     ↓
RMSNorm
     │
     ↓
LM Head
     │
     ↓
[B, T, V] logits
```

官方 adapters 明确包含 `run_rmsnorm`、`run_swiglu`、`run_rope`、带 RoPE 的 MHA、pre-norm Transformer block 和完整 Transformer LM。([GitHub][2])

因此你写 A1 时千万不要形成这种思维：

```python
class RMSNorm(...)
class SwiGLU(...)
class RoPE(...)
```

“测试过了，下一题。”

正确方式应该是：

```text
RMSNorm
→ 控制 residual stream 尺度

Pre-Norm
→ 保留干净 identity gradient path

RoPE
→ 给 Q/K 注入相对位置结构

MHA
→ token 间通信

SwiGLU
→ 每个 token 内部的 gated feature computation

Residual
→ 信息与梯度高速公路
```

一旦这些关系建立起来，你以后看 Llama、Qwen、DeepSeek、Gemma 的 architecture table，就不会觉得它是一堆莫名其妙的配置项。

---

# 24. 最值得你自己推一次的完整 shape flow

假设：

$$
B=2,\quad T=1024,
$$

$$
d=768,\quad H=12,
$$

所以：

$$
d_h=64.
$$

进入 block：

$$
X:[2,1024,768].
$$

RMSNorm：

$$
[2,1024,768].
$$

QKV projection：

$$
Q,K,V:
[2,1024,768].
$$

reshape：

$$
[2,1024,12,64].
$$

通常为了 attention 改成：

$$
[2,12,1024,64].
$$

RoPE：

$$
Q,K:
[2,12,1024,64].
$$

Attention scores：

$$
QK^\top:
[2,12,1024,1024].
$$

softmax 后乘 V：

$$
[2,12,1024,1024]
\times
[2,12,1024,64]
$$

得到：

$$
[2,12,1024,64].
$$

merge heads：

$$
[2,1024,768].
$$

output projection：

$$
[2,1024,768].
$$

residual：

$$
[2,1024,768].
$$

SwiGLU 假设：

$$
d_{ff}=2048:
$$

则：

$$
W_1X,W_3X:
[2,1024,2048].
$$

elementwise gate：

$$
[2,1024,2048].
$$

(W_2) down projection：

$$
[2,1024,768].
$$

residual 再加回来：

$$
\boxed{[2,1024,768]}.
$$

于是整个 block 有一个非常漂亮的不变量：

$$
\boxed{\text{输入 shape = 输出 shape}}
$$

这就是 residual 能一层层堆起来的前提。

---

# 25. 我希望你学完 Lecture 3 后，形成一个新的“读模型配置”能力

以后看到：

```yaml
hidden_size: 4096
num_hidden_layers: 32
num_attention_heads: 32
num_key_value_heads: 8
intermediate_size: 11008
hidden_act: silu
rms_norm_eps: 1e-5
rope_theta: 10000
vocab_size: 128256
```

你不能只是说：

> 哦，这是一堆超参数。

你应该瞬间展开：

```text
d = 4096
L = 32

head_dim = 4096 / 32 = 128

32 query heads
8 KV heads
→ GQA
→ KV cache ≈ MHA 的 1/4

intermediate ≈ 2.69 d
→ 很像 parameter-matched gated FFN

SiLU + 三 projection
→ SwiGLU-style FFN

RMSNorm
→ modern normalization recipe

RoPE
→ position goes into Q/K

Vocab 128k
→ embedding/lm-head 参数很可观
```

然后进一步：

$$
N_{\text{blocks}}
\approx
L(4d^2+3dd_{ff})
$$

开始自己估参数。

**这才是 Lecture 3 真正想培养的能力。**

---

## 最后给你一套“Lecture 3 是否真的学会了”的自测题

你现在最好能不看答案独立推出下面这些：

1. **为什么 pre-norm 的 residual gradient path 比 post-norm 更干净？**写出两个 Jacobian。
2. **为什么 RMSNorm 可以不减 mean？**写出 LayerNorm 和 RMSNorm 的公式，并解释它保留/删除了什么。
3. **为什么 attention 要除 (\sqrt{d_k})？**从 dot-product variance 推导。
4. **为什么 RoPE 会自然得到 relative position (n-m)？**从 (R_m^\top R_n=R_{n-m}) 推导。
5. **为什么普通 FFN 的 (4d) 换成 SwiGLU 后常变成约 (8d/3)？**从参数量 (8d^2=3dd_{ff}) 推导。
6. **为什么 GQA 能显著降低 decode 成本？**自己写出 KV-cache memory 公式。
7. **为什么 QK-Norm 和 (1/\sqrt{d}) 不是一回事？**一个控制初始化理论尺度，一个直接约束训练后 Q/K norm。
8. **给你 (L,d,d_{ff},V)，能不能在纸上估整个模型参数量，再结合 Lecture 2 的 (6ND) 算训练 FLOPs？**

其中 **1～5 是你做 A1 前必须真正掌握的**；6～8 则把 Lecture 2、Lecture 3 和后面的 inference/systems 连起来。

如果把前三讲串成一句话，现在其实非常清楚：

$$
\boxed{
\text{Lecture 1：文本怎样变成 token}
}
$$

$$
\boxed{
\text{Lecture 2：模型怎样消耗 compute / memory}
}
$$

$$
\boxed{
\text{Lecture 3：在这些约束下，现代 Transformer 为什么长成今天这样}
}
$$

而且到这里，A1 里 **Linear / Embedding → RMSNorm → SwiGLU → Attention → RoPE → TransformerBlock → TransformerLM** 这条实现链，理论上已经全部接起来了。
