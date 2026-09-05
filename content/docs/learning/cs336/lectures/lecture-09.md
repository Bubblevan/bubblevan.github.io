---
title: "L09 · Scaling Laws"
weight: 9
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "scaling-laws"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture9/
---

Lecture 9 是 CS336 从 **“怎么高效地训练一个模型”** 转向 **“到底应该训练什么模型”** 的关键转折。

2026 官方课程表中，Lecture 9 是 4 月 27 日 Tatsu 主讲的 **Scaling laws**；官方 `lecture_09.pdf` 是一套 57 页的 “Scaling Laws – Basics” 讲义。Lecture 11 还会再上一讲更偏实践的 Scaling Laws，所以 Lecture 9 的重点是先建立完整的理论与实验直觉：**数据、模型规模、算力、batch size、学习率之间为什么会出现可预测规律，以及如何利用小实验决定千万美元级的大训练。** ([GitHub][1])

我认为这堂课真正应该记住的不是：

> Chinchilla = 20 tokens / parameter。

而是：

$$
\boxed{
\textbf{Scaling Law 是一种“小规模实验 → 拟合 → 外推 → 大规模决策”的工程方法。}
}
$$

---

# 0. 为什么突然需要 Scaling Laws？

假设现在给你：

$$
10{,}000\text{ 张 B200}
$$

一个月。

前八讲已经告诉你怎么：

```text
造 tokenizer
↓
造 Transformer
↓
写 kernel
↓
FlashAttention
↓
并行训练
```

现在老板问：

> 好，那我们到底训练哪个模型？

你马上遇到几十个自由度：

$$
N=\text{参数量}
$$

$$
D=\text{训练 token 数}
$$

还有：

```text
depth
width
heads
d_ff
batch size
learning rate
optimizer
data mixture
training length
...
```

如果目标 run 要几千万美元，你不能这样：

```text
试 70B
不好

试 100B
不好

试 150B
再看看
```

Scaling Law 的目标就是：

> **用几百万、几千万参数的小实验，预测几十亿、几百亿参数模型会发生什么。**

Stanford 的 Lecture 1 其实已经提前给过这个定义：不是在目标规模直接做 hyperparameter search，而是构造一个 **scaling recipe：FLOPs → hyperparameters**，在小规模上测量并拟合，再外推到目标规模。([GitHub][2])

---

# 1. Scaling Law 到底是什么？

最经典形式：

$$
\boxed{
L(R)=L_\infty+A R^{-\alpha}
}
$$

这里：

* (R)：某种资源；
* 可以是 data (D)；
* model parameters (N)；
* compute (C)；
* (L)：validation/test loss；
* (L_\infty)：即使资源无限仍存在的不可约 loss；
* (A)：尺度常数；
* (\alpha)：scaling exponent。

例如：

$$
L(D)
====

L_\infty+A D^{-0.1}.
$$

意思是：

> 数据越多，loss 越低，但 marginal gain 越来越小。

Lecture 9 把 scaling law 定义成一种经验可预测关系，而不是自然界的“定律”；课程还特别强调，很多时候它本质上就是 carefully designed curve fitting。([Yulong Ge][3])

---

# 2. 为什么大家都爱画 log-log 图？

因为：

$$
L-L_\infty
==========

A R^{-\alpha}.
$$

两边取 log：

$$
\log(L-L_\infty)
================

\log A-\alpha\log R.
$$

于是：

$$
\boxed{
y=b-\alpha x
}
$$

变成直线。

所以你以后看到 scaling-law paper：

```text
log(loss - irreducible loss)
              |
              |\
              | \
              |  \
              |   \
              |____\____________
                   log(compute)
```

斜率：

$$
\boxed{-\alpha}
$$

就是 scaling exponent。

这就是为什么论文中“跨六七个数量级仍然是一条直线”会如此令人震撼：意味着相同经验关系可能从 10M 模型一路延伸到 100B。Kaplan 等人的 2020 工作就报告了 loss 相对于参数、数据和 compute 的 power-law 行为，部分跨越七个以上数量级。([arXiv][4])

---

# 3. Power Law 一个很重要的性质：Scale Free

假设：

$$
L-L_\infty
==========

A R^{-\alpha}.
$$

现在把资源扩大：

$$
R\rightarrow\lambda R.
$$

那么：

$$
L(\lambda R)-L_\infty
=====================

\lambda^{-\alpha}
[L(R)-L_\infty].
$$

所以 improvement 只跟：

$$
\boxed{\text{资源扩大多少倍}}
$$

有关，而不是：

> 你现在是在 1M 还是 1B 参数。

因此：

```text
10M → 100M
```

和：

```text
10B → 100B
```

如果仍处于同一 scaling regime，理论上对应相同的 multiplicative improvement。

这就是为什么它有外推价值。([Yulong Ge][3])

---

# 4. 但是 power law 并不是从 (0) 到 (\infty) 全程成立

Lecture 9 很强调这个。

典型学习曲线其实可以想象成：

```text
error
 ^
 |────────── random / insufficient-data regime
 |          \
 |           \
 |            \      power-law regime
 |             \
 |              \______
 |                     ─── irreducible floor
 +-----------------------------> data
```

三个区域：

### 区域 1：数据太少

模型还根本没学起来。

performance 接近：

$$
\text{random baseline}.
$$

---

### 区域 2：Power-law regime

这里：

$$
L-L_\infty
\propto
D^{-\alpha}.
$$

log-log 上很漂亮。

---

### 区域 3：Saturation

开始逼近：

$$
L_\infty.
$$

曲线弯平。

Lecture 9 回顾 Hestness 等 2017 的经典三区域图来说明这一点。([Yulong Ge][3])

所以 scaling study 最大的坑之一就是：

> 只测一个很窄的小区间，看上去像直线，就开始外推 1000×。

局部区域：

$$
e^{-x},\quad x^{-0.1},\quad\log x
$$

都可能看起来差不多。

---

# 5. 为什么神经网络的数据 scaling exponent 那么小？

这是这一讲一个挺深的问题。

例如 Kaplan 的数据拟合之一约为：

$$
L(D)
\propto
D^{-0.095}.
$$

([Yulong Ge][3])

也就是：

$$
\alpha\approx0.1.
$$

这意味着数据扩大：

$$
10\times
$$

loss 的 reducible 部分只有大约：

$$
10^{-0.095}
\approx0.80
$$

也就是下降约 20%。

想减少一半：

$$
D_{\rm new}
===========

2^{1/0.095}D
$$

大约：

$$
\boxed{1500\times}
$$

数据。

很残酷。

---

# 6. 为什么这个结果很奇怪？

考虑最简单的 mean estimation。

你估计：

$$
\mu=\mathbb E[X].
$$

有 (n) 个 independent samples。

标准误差：

$$
\operatorname{SE}
\sim
\frac{1}{\sqrt n}.
$$

也就是：

$$
\boxed{\alpha=0.5}.
$$

有些更强条件甚至会出现接近：

$$
1/n.
$$

但 deep learning：

$$
\boxed{\alpha\sim0.1}.
$$

慢得多。

为什么？

目前并没有一个让所有人满意的完整理论解释。

可能涉及：

```text
effective dimension
distribution complexity
function smoothness
representation learning
optimization
noise
```

Lecture 9 特别把这一点保留为开放问题：Scaling Laws 工程上非常好用，但理论上为什么出现这些指数仍然没有完全搞明白。([Yulong Ge][3])

---

# 7. 所以 Scaling Laws 是“理论”还是“经验科学”？

答案：

$$
\boxed{\text{目前更多是经验科学}}
$$

这也是 Lecture 9 的核心态度。

我们确实有：

```text
statistical learning theory
sample complexity
non-parametric convergence
```

提供一些：

$$
n^{-\alpha}
$$

形式的理论直觉。

但经典理论往往给的是：

$$
\boxed{\text{upper bound}}
$$

例如：

> 误差最多有多坏。

而 modern scaling law 在预测：

$$
\boxed{\text{真实训练以后 loss 到底是多少}}
$$

这两个完全不是一回事。Lecture 9 专门从经典 sample complexity 和 1990 年代 learning curves 的历史一路讲到 Kaplan/Chinchilla，就是为了说明这种区别。([Yulong Ge][3])

---

# 8. 于是出现 Scaling Law 最重要的工程价值：预测

假设我训练：

```text
30M
100M
300M
1B
```

模型。

得到：

| Model | Loss |
| ----- | ---: |
| 30M   |  3.6 |
| 100M  |  3.2 |
| 300M  |  2.9 |
| 1B    | 2.65 |

然后拟合：

$$
L(N)
====

L_\infty+A N^{-\alpha}.
$$

那么可以问：

> 70B 大概会是多少？

而不是：

> 先花几百万美元训一遍再知道。

所以 Scaling Law 的价值不是单纯解释世界。

而是：

$$
\boxed{\text{forecasting}}
$$

这也是为什么大模型公司如此重视 scaling experiments。

---

# 9. 更进一步：Scaling Law 可以拿来选 Architecture

假设：

```text
Architecture A
Architecture B
```

小规模实验：

```text
loss
 ^
 | A \
 |    \
 | B   \
 |  \   \
 |   \   \
 +-----------------> compute
```

可能 A 在小规模好：

$$
L_A(C_1)<L_B(C_1).
$$

但如果：

$$
\alpha_B>\alpha_A
$$

曲线可能在更大规模 crossover：

$$
L_B(C_2)<L_A(C_2).
$$

所以不能只问：

> 100M 模型谁好？

要问：

$$
\boxed{\text{整条 scaling curve 谁好？}}
$$

这就是 Lecture 9 在 architecture/optimizer 部分强调的：

> 比较截距和斜率，而不是单个模型上的 winner。([Yulong Ge][3])

---

# 10. 一个很反直觉的经验：Depth/Width 往往没有你想象那么敏感

Kaplan 等人的经典结果之一：

> 在相当宽的合理 architecture range 内，width/depth ratio 对最终 scaling 并没有巨大影响。([arXiv][4])

这意味着例如参数量差不多的：

```text
48 layers × narrow
```

和：

```text
24 layers × wider
```

可能在合理范围内落在很接近的 scaling curve 上。

当然不是说 architecture 不重要。

而是：

$$
\boxed{
\text{很多 architecture hyperparameter 有一个很宽的“够好区间”}
}
$$

真正灾难性的设计会掉队，但没必要迷信某个精确：

```text
d_ff = 2.6875 d
depth/width = 0.123...
```

是宇宙最优常数。

---

# 11. Optimizer 也经常表现成“改变截距”

假设：

```text
AdamW
Muon
FancyOptimizer
```

得到：

$$
L_A(C)
======

a_AC^{-\alpha}
$$

和：

$$
L_B(C)
======

a_BC^{-\alpha}.
$$

如果：

$$
\alpha_A\approx\alpha_B
$$

那么新 optimizer 主要让曲线整体下移：

```text
loss
 ^
 | Adam  \
 |        \
 | Muon    \
 |  \       \
 |   \       \
 +----------------
```

这表示：

> 它相当于给你一个 constant-factor compute improvement。

如果：

$$
a_B<a_A
$$

那么达到同样 loss：

$$
B
$$

可能少用一部分 compute。

但它没有改变 scaling exponent。

Lecture 9 的一个反复出现的经验就是：

$$
\boxed{\text{很多 intervention 改变 intercept，多于改变 slope}}
$$

([Yulong Ge][3])

---

# 12. 现在进入另一个很实用的问题：Batch Size

为什么 batch 不是越大越好？

假设 batch：

$$
B.
$$

梯度估计：

$$
g_B
===

\frac1B\sum_{i=1}^{B}g_i.
$$

gradient noise variance 大致：

$$
\operatorname{Var}(g_B)
\propto
\frac1B.
$$

所以一开始：

$$
B\rightarrow2B
$$

梯度更准。

并且可以做更多 data parallelism。

于是：

$$
\boxed{\text{steps-to-target}\downarrow}
$$

---

# 13. 但是存在 Critical Batch Size

当：

$$
B
$$

已经很大，梯度噪声已经非常小。

继续：

$$
B\rightarrow2B
$$

并不会再让：

$$
\text{optimizer steps}
$$

减半。

于是出现：

```text
steps to target
 ^
 |\
 | \
 |  \
 |   \________
 |            \
 +--------------------> batch size
          ^
          B_crit
```

Lecture 9 使用 McCandlish 风格的效率关系：

$$
\frac{S}{S_{\min}}-1
====================

\left(
\frac{E}{E_{\min}}-1
\right)^{-1}
$$

并定义一个典型折中：

$$
\boxed{
B_{\mathrm{crit}}
=================

\frac{E_{\min}}{S_{\min}}
}
$$

这里：

* (S)：达到目标 loss 所需 steps；
* (E)：消耗的 examples/tokens。([Yulong Ge][3])

---

# 14. Critical Batch Size 的真正含义

你在 trade：

$$
\boxed{\text{wall-clock efficiency}}
$$

和：

$$
\boxed{\text{sample efficiency}}
$$

小 batch：

```text
samples 很省
但 step 很多
```

大 batch：

```text
steps 很少
但 samples 浪费
```

(B_{\rm crit}) 是中间比较自然的拐点。

而且：

$$
\boxed{B_{\rm crit}\text{ 不是常数}}
$$

Lecture 9 展示的经验规律表明，它会随着训练推进、loss 降低而增大。([Yulong Ge][3])

这其实解释了一个很实际的 recipe：

```text
training start
↓
small batch

training progresses
↓
larger batch
```

即：

$$
\boxed{\text{batch size warmup/ramp-up}}
$$

---

# 15. Learning Rate 也会随 scale 漂移

假设普通 parameterization。

小模型：

$$
\eta^*=10^{-3}.
$$

模型变宽以后，可能：

$$
\eta^*=3\times10^{-4}.
$$

再大：

$$
10^{-4}.
$$

因此你不能：

> 在 20M 上调好 LR，直接原封不动扔给 70B。

传统办法：

$$
\boxed{\text{对 optimal LR 本身再做 scaling law}}
$$

比如拟合：

$$
\eta_{\mathrm{opt}}
\propto
N^{-\gamma}.
$$

---

# 16. μP 是另一种非常漂亮的哲学

与其：

> “预测 learning rate 怎么漂。”

不如：

> **重新 parameterize 网络，让 optimum 根本不漂。**

这就是：

$$
\boxed{\mu P}
$$

Maximal Update Parametrization。

目标是让：

```text
small model
medium model
huge model
```

的最佳 hyperparameters 尽可能稳定。

于是可以：

```text
在 40M 上 tune LR
             ↓
zero-shot transfer
             ↓
6.7B
```

Tensor Programs V 的实验正是展示了这种 hyperparameter transfer：在 μP parameterization 下，多种 optimal hyperparameters 随宽度保持稳定。([arXiv][5])

Lecture 9 这里只把 μP 当重要思想介绍；Lecture 11 会再深入。

---

# 17. 现在终于进入这堂课的核心问题

假设给你固定 compute：

$$
\boxed C
$$

应该：

> 训练一个很大的模型，只看少量数据？

还是：

> 小一点的模型，看很多很多数据？

这就是：

$$
\boxed{\text{Compute-optimal scaling}}
$$

---

# 18. 先把 Lecture 2 的神公式拿回来

dense Transformer training：

$$
\boxed{
C
\approx
6ND
}
$$

其中：

$$
N=\text{parameters}
$$

$$
D=\text{training tokens}.
$$

所以固定：

$$
C
$$

意味着：

$$
ND=\text{constant}.
$$

这就是一条 hyperbola：

```text
D
^
|\
| \
|  \
|   \
|    \
+-----------> N
```

参数变大：

$$
N\uparrow
$$

那 tokens 必须：

$$
D\downarrow.
$$

反之亦然。([Yulong Ge][3])

---

# 19. 两个极端都很糟

### 极端 A：模型超级小

$$
N\downarrow
$$

于是可以给巨量：

$$
D.
$$

但模型容量不够。

最终：

```text
data ↑↑↑
loss _________
```

再喂数据也吃不进去。

---

### 极端 B：模型超级大

$$
N\uparrow.
$$

但固定 compute 迫使：

$$
D\downarrow.
$$

模型可能只训练很短。

大量 parameters 根本没有学充分。

---

于是固定 compute 下 loss 随模型大小通常有一个：

$$
\boxed{\text{U-shaped optimum}}
$$

```text
loss
 ^
 | \         /
 |  \       /
 |   \_____/
 |
 +----------------> model size
          ^
       optimum
```

这就是 IsoFLOP analysis 的核心图。

---

# 20. 可以直接从 Joint Scaling Law 推出 optimum

假设：

$$
\boxed{
L(N,D)
======

E
+
A N^{-\alpha}
+
B D^{-\beta}
}
$$

其中：

$$
E
$$

是 irreducible loss。

模型太小时：

$$
A N^{-\alpha}
$$

大。

数据太少时：

$$
B D^{-\beta}
$$

大。

现在固定：

$$
C=kND.
$$

所以：

$$
D=\frac{C}{kN}.
$$

代进去：

$$
L(N)
====

E
+
A N^{-\alpha}
+
B\left(\frac{kN}{C}\right)^\beta.
$$

([Yulong Ge][3])

---

# 21. 真正把这个最优点推出来

求导：

$$
\frac{dL}{dN}
=============

-\alpha A N^{-\alpha-1}
+
\beta B
\left(
\frac{k}{C}
\right)^\beta
N^{\beta-1}.
$$

令：

$$
\frac{dL}{dN}=0.
$$

得到：

$$
N^{\alpha+\beta}
\propto
C^\beta.
$$

所以：

$$
\boxed{
N_{\mathrm{opt}}
\propto
C^{\frac{\beta}{\alpha+\beta}}
}
$$

同理：

$$
\boxed{
D_{\mathrm{opt}}
\propto
C^{\frac{\alpha}{\alpha+\beta}}
}
$$

([Yulong Ge][3])

这两个式子我建议你真的自己推一遍。

这是 Lecture 9 最重要的数学之一。

---

# 22. 为什么这个推导很漂亮？

定义：

$$
N_{\mathrm{opt}}\propto C^a
$$

$$
D_{\mathrm{opt}}\propto C^b.
$$

那么：

$$
a
=

\frac{\beta}{\alpha+\beta}
$$

$$
b
=

\frac{\alpha}{\alpha+\beta}.
$$

所以：

$$
\boxed{a+b=1}
$$

正好和：

$$
C\propto ND
$$

吻合。

---

# 23. tokens per parameter 会发生什么？

看：

$$
\frac DN.
$$

因为：

$$
N\propto C^a
$$

$$
D\propto C^b
$$

所以：

$$
\boxed{
\frac DN
\propto
C^{b-a}
}
$$

如果：

$$
a=b=0.5
$$

那么：

$$
\boxed{\frac DN=\text{constant}}
$$

也就是说模型扩大 2×：

$$
N\rightarrow2N
$$

token 也扩大：

$$
D\rightarrow2D.
$$

这就是 Chinchilla 的经典结论方向。

---

# 24. Kaplan 2020 得到了什么？

Kaplan 等的 compute-optimal 结果近似：

$$
\boxed{
N_{\mathrm{opt}}
\propto
C^{0.73}
}
$$

$$
\boxed{
D_{\mathrm{opt}}
\propto
C^{0.27}
}
$$

所以：

$$
\frac DN
\propto
C^{-0.46}.
$$

也就是说：

> 算力越多，越应该优先把钱花在**更大的模型**，而不是更多数据。

([Yulong Ge][3])

这套思路直接影响了 GPT-3 那一代。

GPT-3：

$$
175B
$$

但只训练约：

$$
300B\text{ tokens}.
$$

所以大约：

$$
\sim2\text{ tokens/parameter}.
$$

---

# 25. 然后 Chinchilla 2022 说：不对

DeepMind 做了 400 多个 training runs，模型从约：

$$
70M\rightarrow16B+
$$

数据从：

$$
5B\rightarrow500B
$$

tokens。

他们发现 compute optimal 更接近：

$$
\boxed{
N\propto C^{0.5}
}
$$

$$
\boxed{
D\propto C^{0.5}
}
$$

即：

$$
\boxed{\text{参数和数据近似同步扩大}}
$$

([arXiv][6])

---

# 26. 这直接产生了 Chinchilla 70B

当时 Gopher：

$$
280B
$$

参数。

Chinchilla：

$$
70B
$$

只有：

$$
1/4
$$

那么大。

但是数据约：

$$
4\times.
$$

所以总训练 FLOPs 大致一样：

$$
ND
$$

相近。

结果：

$$
\boxed{\text{Chinchilla 更好}}
$$

这说明 Gopher 等当时的大模型：

$$
\boxed{\text{undertrained}}
$$

参数太多，tokens 太少。([arXiv][6])

---

# 27. “20 tokens per parameter”是怎么来的？

Chinchilla 的经验 optimum 大约对应：

$$
\boxed{
D\approx20N
}
$$

所以：

| Model | Chinchilla-ish tokens |
| ----: | --------------------: |
|    1B |                   20B |
|    7B |                  140B |
|   70B |                  1.4T |
|  175B |                  3.5T |

这就是那个著名的：

$$
\boxed{20:1}
$$

但是 Lecture 9 对此非常强调：

$$
\boxed{\textbf{20 不是宇宙常数。}}
$$

它依赖：

```text
dataset
tokenizer
architecture
optimizer
parameter definition
training objective
```

Chinchilla 最重要的是：

$$
\boxed{a\approx b\approx0.5}
$$

而不是：

> 所有模型永远 20 tokens/param。([Yulong Ge][3])

---

# 28. Chinchilla 到底怎么测出来的？Lecture 9 讲了三个方法

这一部分非常适合你以后做 A3。

## Method 1：Lower Envelope

训练很多不同大小模型：

```text
70M
100M
300M
1B
3B
10B
```

每一个都留完整 training curve。

然后对于每一个 FLOP budget：

> 找所有训练曲线里 loss 最低的那个点。

```text
loss
 ^
 |   model A \
 | model B    \
 |      \      \
 |       \ model C
 |--------\------------- lower envelope
 +------------------------> FLOPs
```

这些 optimum points 组成：

$$
\boxed{\text{lower envelope}}
$$

然后看看 optimum model size：

$$
N^*(C)
$$

随 compute 怎么变化。

Chinchilla 方法一得到大约：

$$
a\approx0.50.
$$

([Yulong Ge][3])

---

# 29. Method 2：IsoFLOP

我认为这是 Lecture 9 最值得学的实验设计。

先固定：

$$
C=C_1.
$$

然后试：

```text
small N + huge D
medium N + medium D
huge N + small D
```

因为：

$$
D=\frac{C}{6N}.
$$

得到 U 曲线：

```text
loss
 ^
 | \       /
 |  \_____/
 +---------------> N
```

找谷底：

$$
N^*(C_1).
$$

再换：

$$
C_2,C_3,C_4...
$$

重复。

最后：

```text
log N*
 ^
 |        *
 |      *
 |    *
 |  *
 +--------------> log C
```

斜率就是：

$$
a.
$$

Chinchilla 方法二得到：

$$
a\approx0.49,\qquad
b\approx0.51.
$$

Lecture 9 里 Tatsu 明确把 IsoFLOP 当作特别干净、稳健的默认方法，因为它对全局函数形式依赖较少。([Yulong Ge][3])

---

# 30. Method 3：直接拟合二维 Loss Surface

假设：

$$
L(N,D)
======

E+\frac A{N^\alpha}
+\frac B{D^\beta}.
$$

你训练：

```text
        Data
      1B  3B  10B 30B
N 100M •   •   •
  300M •   •   •
  1B   •   •
  3B   •
```

然后直接拟合整个二维 surface：

$$
(N,D)\rightarrow L.
$$

再在：

$$
C=6ND
$$

约束下寻找 optimum。

优点：

> 所有实验点都利用上。

缺点：

> **非常依赖你假设的函数形式。**

Chinchilla 原方法三得到：

$$
a\approx0.46,\qquad
b\approx0.54.
$$

后来对这部分的重新分析认为它的拟合存在问题；重新拟合后会更接近方法一、二及近似恒定 tokens/parameter 的结果。Lecture 9 专门用这个案例说明：

$$
\boxed{\text{漂亮的拟合曲面 ≠ 可靠的外推}}
$$

([Yulong Ge][3])

---

# 31. 那 Kaplan 和 Chinchilla 为什么差这么多？

这个问题 Lecture 9 花了很大篇幅。

表面：

$$
Kaplan:
\quad
a=0.73
$$

$$
Chinchilla:
\quad
a\approx0.5.
$$

一度看起来像：

> 两篇 scaling law 有一篇错了。

但后来发现很多“小工程细节”都会系统性改变 scaling slope。

---

# 32. 第一个坑：Parameter Count 到底怎么算？

你说：

$$
N=1B
$$

到底包括：

```text
embedding?
LM head?
tied embedding?
all parameters?
non-embedding?
active MoE parameters?
total MoE parameters?
```

对于巨大模型：

$$
Vd
$$

可能相对不大。

但小 scaling model：

$$
Vd
$$

可能占参数很大比例。

所以如果小模型和大模型的：

$$
\text{parameter counting convention}
$$

不一致，log-log slope 会被系统性扭曲。Lecture 9 引用后续复现工作说明，参数/计算口径的修改本身就能显著把 Kaplan 风格 exponent 拉向 Chinchilla 区间。([Yulong Ge][3])

---

# 33. 第二个坑：Warmup

假设所有模型：

```text
warmup = 2000 steps
```

大型 run：

$$
100000\text{ steps}
$$

warmup 占：

$$
2%.
$$

小 run：

$$
3000\text{ steps}
$$

warmup 占：

$$
67%.
$$

那小模型几乎整个实验都：

> 还没进入正常 learning rate。

于是你会错误得到：

$$
\boxed{\text{小模型看起来特别差}}
$$

然后 scaling law 会错误地告诉你：

> 大模型非常划算。

Lecture 9 用后续 Kaplan/Chinchilla discrepancy 的复现实验专门展示了这一类 recipe mismatch。([Yulong Ge][3])

---

# 34. 第三个坑：Batch Size

如果你所有 scale 都用：

$$
B=4M\text{ tokens}.
$$

对于大型模型可能：

$$
B<B_{\rm crit}.
$$

很好。

但对于 tiny model：

$$
B\gg B_{\rm crit}.
$$

大量 compute 浪费。

于是：

$$
\boxed{\text{你不是在测“模型规模效应”，而是在测“错误 batch size 的惩罚”。}}
$$

Scaling law 最危险的一点就是：

> 它会非常忠实地 extrapolate 你的坏 recipe。

---

# 35. 这就是 Lecture 9 最关键的方法论之一

Scaling Law 预测的是：

$$
\boxed{\text{当前 training recipe 放大以后会怎么样}}
$$

不是：

$$
\boxed{\text{整个机器学习世界能做到的理论最优}}
$$

如果：

```text
small model optimizer 很差
warmup 不合理
batch 不合理
data pipeline 不合理
```

你拟合出的 scaling law：

> 完全可以非常漂亮。

但它只是在准确预测：

> **这个糟糕方法扩大以后仍然有多糟。**

Lecture 9 明确提醒不能把 scaling law 当作不可突破的物理 lower bound。([Yulong Ge][3])

---

# 36. 这也是为什么“Predictability ≥ Optimality”非常重要

一个稍微差一点、但 scaling 非常稳定的 architecture：

```text
loss
 ^
 |\
 | \
 |  \
 |   \
 +------------>
```

可能比一个：

```text
今天特别强
明天突然崩
不同规模 optimum 全乱
```

的 architecture 更适合 billion-dollar hero run。

因为最大风险不是：

$$
0.5%\text{ loss difference}.
$$

而是：

> 你做的 100M pilot 根本不能预测 100B。

Stanford 课程在 overview 对 scaling recipe 的总结就直接说：

$$
\boxed{\text{Predictability is at least as important as optimality}}
$$

([GitHub][2])

---

# 37. Data Scaling 也不只是“token 越多越好”

Lecture 9 2026 版还有一个很值得注意的扩展：

$$
\boxed{\text{data composition}}
$$

也有 scaling behavior。

例如：

```text
50% web
30% books
10% code
10% math
```

和另一种 mixture。

有时会看到：

$$
L_1(D)
======

A_1D^{-\alpha}
$$

$$
L_2(D)
======

A_2D^{-\alpha}.
$$

斜率：

$$
\alpha
$$

差不多。

只是：

$$
A_1\neq A_2.
$$

也就是 log-log 图：

```text
loss
 ^
 | mixture A \
 |            \
 | mixture B   \
 |              \
 +------------------>
```

两条近似平行线。

这意味着：

> 小模型上哪个 mixture 更好，有可能在大模型上仍然更好。

但 Lecture 9 同时强调这只是常见经验，不是普适定理。([Yulong Ge][3])

---

# 38. 数据重复（epochs）也不是“重复一次就完全没用”

假设只有：

$$
U_D
$$

unique tokens。

但你训练：

$$
10\text{ epochs}.
$$

实际看到：

$$
10U_D
$$

tokens。

这些当然不能完全等价于：

$$
10U_D
$$

unique data。

但是也不是：

> 第二遍开始价值 = 0。

Lecture 9 引入 data-constrained scaling 的思想：

$$
D'
==

U_D
+
U_D R_D^*
\left(
1-e^{-R_D/R_D^*}
\right)
$$

作为 effective data。([Yulong Ge][3])

---

# 39. 这个公式直觉非常简单

重复很少：

$$
R_D\ll R_D^*
$$

则：

$$
1-e^{-R_D/R_D^*}
\approx
\frac{R_D}{R_D^*}.
$$

所以：

$$
D'
\approx
U_D(1+R_D).
$$

也就是说：

$$
\boxed{\text{前几个 epoch 价值接近新数据}}
$$

但重复非常多：

$$
R_D\rightarrow\infty
$$

则：

$$
D'
\rightarrow
U_D(1+R_D^*).
$$

饱和。

所以：

$$
\boxed{\text{重复数据边际价值越来越低}}
$$

这对今天数据逐渐成为瓶颈的世界特别重要。

---

# 40. 这还会改变 Data Filtering 的最优策略

假设你有 10T raw tokens。

质量过滤：

```text
top 10%
→ 1T very good data

top 50%
→ 5T medium-good data
```

训练预算只要：

$$
100B
$$

tokens。

那当然：

> 严格过滤。

但是预算：

$$
15T.
$$

如果仍只留那：

$$
1T
$$

高质量数据，就得重复 15 epochs。

这时也许：

> 放宽过滤，增加 unique data

更划算。

所以 Lecture 9 一个非常现代的观点是：

$$
\boxed{
\text{最佳 data filter 不是固定 threshold，
而会随 compute budget 改变。}
}
$$

([Yulong Ge][3])

这其实给后面的 Data Lectures 提前埋了伏笔。

---

# 41. 最后一个很重要的纠正：Chinchilla-optimal 不一定是 Production-optimal

Chinchilla 优化的目标是：

$$
\boxed{
\min L
\quad
\text{s.t. fixed training FLOPs}
}
$$

但是现实公司真正付钱的是：

$$
\boxed{
C_{\mathrm{life}}
=================

C_{\mathrm{R&D}}
+
C_{\mathrm{train}}
+
C_{\mathrm{inference}}
}
$$

如果模型上线后要生成：

$$
10^{15}\text{ tokens}
$$

那么 inference cost 可能远超 training。

Lecture 9 把这一点写成类似：

$$
C_{\rm life}
============

C_{\rm R&D}
+
C_{\rm train}
+
Q,C_{\rm serve}(N).
$$

([Yulong Ge][3])

---

# 42. 那么最优方案会往哪个方向偏？

Inference cost 大致随着：

$$
N
$$

增长。

所以你可能愿意：

$$
\boxed{\text{训练更小的模型，但训练更久}}
$$

例如：

```text
方案 A
100B model
2T tokens

方案 B
20B model
10T tokens
```

训练 FLOPs：

$$
ND
$$

可能类似。

但 inference：

$$
20B
$$

便宜大约很多。

所以生产模型普遍出现所谓：

$$
\boxed{\text{overtraining relative to Chinchilla}}
$$

注意这里的 overtraining **不是过拟合**。

意思只是：

> 比“单次训练 compute-optimal”看更多 tokens。

Lecture 9 给出的历史趋势中，后来的 Mistral、Llama 3 等模型的 tokens/parameter 已明显高于经典 Chinchilla 20:1。([Yulong Ge][3])

---

# 43. 所以“Chinchilla 20:1 已经过时”这个说法其实不准确

更准确的是：

$$
\boxed{
\text{20:1 是特定目标函数下的 training-compute optimum 经验值。}
}
$$

如果你的目标是：

$$
\min(\text{train compute})
$$

它依然是很重要的 baseline。

但如果目标是：

$$
\min(
\text{train}
+
\text{serve}
)
$$

那 optimum 很自然会向：

$$
\boxed{\text{smaller N + larger D}}
$$

移动。

这就是现代小模型“训练得特别久”的经济学。

---

# 44. Lecture 9 为什么如此喜欢 IsoFLOP？

因为它是一种非常通用的实验方法。

不要先相信：

$$
L(N,D)=E+A/N^\alpha+B/D^\beta.
$$

先：

$$
\boxed{\text{固定真实成本}}
$$

然后扫描自由度。

例如：

## Dense LM

固定 FLOPs：

$$
N\times D.
$$

扫描：

$$
N.
$$

---

## MoE

固定 FLOPs。

扫描：

```text
total experts
active experts
model width
```

---

## Diffusion

固定 compute。

扫描 model size。

只要能看到：

$$
\boxed{\text{U-shaped valley}}
$$

就能直接找 optimum，再研究 optimum 如何随 compute 移动。

Lecture 9 因此把 IsoFLOP 总结为非常好用的默认 scaling experiment：明确成本、扫描自由度、确保覆盖谷底、多预算重复、最后留一个更大的 scale 做真正外推验证。([Yulong Ge][3])

---

# 45. 这和 CS336 A3 的关系非常直接

官方 2026 课程安排是：

```text
Lecture 9: Scaling Laws
↓
Lecture 10: Inference
↓
Assignment 3: Scaling out
```

A3 的官方仓库提供一个 hosted training API；学生提交有限 FLOP budget 的 training runs、收集数据，再拟合 scaling law，最后提交目标规模的 hyperparameters 和 loss prediction。([GitHub][1])

换句话说，A3 不是：

> “实现一个公式”。

而是让你模拟真正 frontier lab 的工作：

```text
总 experiment budget 有限
↓
我该把钱花在哪些 pilot runs？
↓
得到哪些点最 informative？
↓
怎么拟合？
↓
怎么预测 hidden target scale？
```

这也是为什么 A3 看起来“不训练真正的大模型”，实际上学的是大模型研发里非常真实的一项能力。

---

# 46. 你可以把 A3/Scaling Study 理解成实验设计问题

假设你只允许：

$$
20
$$

个 runs。

一个很糟的做法：

```text
全部都在 100M 附近
```

你完全看不到 slope。

另一个很糟：

```text
只训练 1 个 10M
1 个 10B
```

variance 太大。

更合理：

```text
多个 compute budgets

C1:
 N1 N2 N3 N4 N5

C2:
 N1 N2 N3 N4 N5

C3:
 N1 N2 N3 N4 N5
```

每条 IsoFLOP 覆盖 U 型谷底。

然后：

$$
N^*(C_1),N^*(C_2),N^*(C_3)
$$

拟合：

$$
N^*(C)\propto C^a.
$$

这才是真正的 scaling experiment。

---

# 47. Scaling Law 最适合预测什么？

最容易：

$$
\boxed{\text{Cross-entropy / validation loss}}
$$

因为它：

```text
连续
低噪声
每个 token 都贡献信号
```

而：

```text
MMLU accuracy
SWE-bench
GSM8K
```

可能有：

```text
threshold
discreteness
contamination
high variance
```

所以：

$$
\boxed{\text{pretraining loss predictable}}
$$

并不意味着：

$$
\boxed{\text{所有 downstream ability 同样 predictable}}
$$

Lecture 9 特别提醒过，不同模型在 pretraining loss 上的漂亮 scaling 排序并不自动保证下游 benchmark 也保持相同排序。([Yulong Ge][3])

---

# 48. 这也重新解释所谓 Emergent Abilities

假设某个能力要求内部连续量：

$$
q
$$

超过 threshold：

$$
q>0.8.
$$

而模型 quality 随 compute 平滑：

$$
q(C)
$$

增长。

那么 accuracy：

```text
q < 0.8 → 0%
q > 0.8 → 100%
```

就会看起来：

```text
ability
 ^
 |        ______
 |       |
 |       |
 |_______|
 +-------------> scale
```

像突然“涌现”。

但 underlying loss/competence：

```text
 ^
 |       /
 |      /
 |     /
 |____/________
```

可能一直连续。

Lecture 9 回顾早期 neural scaling 工作时也指出，accuracy cliffs 有时来自指标阈值，而不意味着学习过程本身真的发生物理相变。([Yulong Ge][3])

---

# 49. 所以 Lecture 9 最深的地方其实不是 Chinchilla

我认为是这句话：

$$
\boxed{
\textbf{不要直接 scale 一个模型；
要 scale 一个 recipe。}
}
$$

一个完整 recipe 包括：

```text
architecture
parameterization
optimizer
learning rate
batch size
warmup
schedule
data mixture
data filtering
tokenizer
training length
```

Scaling law：

$$
\boxed{
\text{只对这个 recipe 有条件成立}
}
$$

recipe 改了：

> scaling law 也应该重新验证。

这就是为什么直接把：

$$
D=20N
$$

套在 2026 年任何 architecture 上是不严谨的。

---

# 50. 我希望你读完 Lecture 9 后能形成一个标准工作流

以后如果自己设计一个 mini LLM experiment，不应该：

> “Llama 用 32 层，所以我也 32 层。”

而应该：

### Step 1：定义目标资源

例如：

$$
C=10^{20}\text{ FLOPs}.
$$

---

### Step 2：选小尺度 budgets

例如：

$$
10^{17},
10^{18},
10^{19}.
$$

---

### Step 3：每个 budget 做 IsoFLOP sweep

根据：

$$
D=\frac C{6N}
$$

试不同：

$$
N.
$$

---

### Step 4：得到 optimum

$$
N^*(C)
$$

和：

$$
D^*(C).
$$

---

### Step 5：log-log 拟合

$$
N^*=aC^\alpha
$$

$$
D^*=bC^\beta.
$$

---

### Step 6：外推

预测：

$$
C=10^{20}.
$$

---

### Step 7：留一个 target-ish run 验证

千万不要：

> 所有点都拿去 fit。

必须有：

$$
\boxed{\text{held-out extrapolation test}}
$$

这才是在测“预测能力”。

Lecture 9 最后的 checklist 也基本就是这个思想：定义目标和横轴、保持 recipe 公平、覆盖足够动态范围、检查函数极限、报告不确定性，并留下更大尺度做真正的外推验证。([Yulong Ge][3])

---

# 51. 现在把 Lecture 2 和 Lecture 9 接起来

Lecture 2 给：

$$
\boxed{C\approx6ND}
$$

当时只是：

> 算一个模型多贵。

Lecture 9 现在说：

> 既然它这么贵，那我们反过来利用这条 constraint：

$$
ND=\frac C6
$$

在这条曲线上寻找：

$$
\boxed{
\arg\min_{N,D}L(N,D)
}
$$

于是 Lecture 2 的 resource accounting：

$$
\text{FLOPs}
$$

突然变成了 Lecture 9 的 optimization constraint。

这就是 CS336 整个课程设计很漂亮的地方。

---

# 52. Lecture 8 和 Lecture 9 也有非常关键的联系

Lecture 8：

> 给定一个模型，怎么在 10,000 GPUs 上最快训练？

优化：

$$
\boxed{\text{wall-clock / utilization}}
$$

Lecture 9：

> 给定这些 10,000 GPUs 一个月，我到底应该训练什么？

优化：

$$
\boxed{\text{final loss / quality}}
$$

所以：

$$
\boxed{\text{Systems efficiency}}
$$

会反过来影响：

$$
\boxed{\text{compute-optimal recipe}}
$$

比如某 architecture 理论 FLOPs 少，但 GPU utilization 很差：

$$
\text{real compute cost}\neq6ND.
$$

这也是 Lecture 9 提醒：

$$
C\approx6ND
$$

只是 experiment-level approximation，不等于 wall-clock cost；长 context、MoE、communication、hardware utilization 都会改变常数甚至结构。([Yulong Ge][3])

---

# 53. 给你一个非常实用的“Scaling Law 阅读防骗表”

以后论文说：

> “We discovered scaling law (X).”

你第一反应检查：

**① 横轴到底是什么？**

```text
total params?
non-embedding params?
active params?
training FLOPs?
wall-clock FLOPs?
tokens?
```

**② loss 到底是什么？**

```text
train?
validation?
which distribution?
perplexity?
downstream score?
```

**③ recipe 是否 across-scale fair？**

```text
learning rate
batch
warmup
schedule
```

**④ fitting range 多大？**

```text
1.5×？
10×？
1000×？
```

**⑤ 是否有 asymptote？**

$$
L_\infty
$$

怎么处理？

**⑥ 外推测试了吗？**

还是：

> fit 自己，再报告 (R^2=0.999)。

**⑦ 有没有 IsoFLOP valley？**

如果所有点都在谷底一侧，根本不知道 optimum 在哪。

**⑧ 参数和 compute 定义一致吗？**

Kaplan–Chinchilla 的争论已经告诉你，这类细节足以大幅移动 exponent。([Yulong Ge][3])

---

# 54. 我最希望你真正会推的 8 道题

### 1.

如果：

$$
L(D)-L_\infty=AD^{-0.1}
$$

数据扩大 100 倍，reducible loss 变多少？

$$
100^{-0.1}
==========

10^{-0.2}
\approx0.63.
$$

即只下降约：

$$
37%.
$$

---

### 2.

为什么 power law 在 log-log 图是直线？

自己推：

$$
\log(L-L_\infty)
================

\log A-\alpha\log D.
$$

---

### 3.

固定：

$$
C=6ND
$$

为什么 (N) 和 (D) 不能同时增大？

因为：

$$
D=C/(6N).
$$

---

### 4.

从：

$$
L
=

E+AN^{-\alpha}+BD^{-\beta}
$$

推：

$$
N_{\mathrm{opt}}
\propto
C^{\beta/(\alpha+\beta)}.
$$

这是本讲最重要的数学题。

---

### 5.

如果：

$$
\alpha=\beta
$$

证明：

$$
N_{\mathrm{opt}}
\propto
C^{1/2},
\quad
D_{\mathrm{opt}}
\propto
C^{1/2}.
$$

所以：

$$
D/N=\text{constant}.
$$

---

### 6.

Kaplan：

$$
N\propto C^{0.73}
$$

$$
D\propto C^{0.27}.
$$

那么：

$$
D/N
\propto
C^{-0.46}.
$$

解释它是什么意思：

> 算力越大，recipe 越偏向模型规模。

---

### 7.

为什么 IsoFLOP 比只拟合：

$$
L(N,D)
$$

更稳健？

因为 optimum 是：

$$
\boxed{\text{直接观察到的 valley}}
$$

而不是强依赖整个二维函数的假设形式。

---

### 8.

为什么 Llama 3 可以远远超过 Chinchilla 的 tokens/parameter，却不意味着 Chinchilla 被“推翻”？

因为优化目标不同：

$$
\boxed{\text{training-compute optimal}}
$$

vs

$$
\boxed{\text{training + inference lifecycle optimal}}.
$$

---

# 最后，把 Lecture 9 压成一块黑板

如果我上完这堂课，只允许留下五行，我会写：

$$
\boxed{
L(R)
====

L_\infty+AR^{-\alpha}
}
$$

资源与 loss 经常呈 power law。

---

$$
\boxed{
C\approx6ND
}
$$

训练 compute 将 model 和 data 绑在一起。

---

$$
\boxed{
L(N,D)
======

E+\frac A{N^\alpha}
+\frac B{D^\beta}
}
$$

model limitation + data limitation。

---

$$
\boxed{
N^*
\propto
C^{\beta/(\alpha+\beta)},
\qquad
D^*
\propto
C^{\alpha/(\alpha+\beta)}
}
$$

从 scaling surface 得到 compute-optimal recipe。

---

最后再写一句最大号的：

$$
\boxed{
\textbf{Scaling laws predict recipes, not laws of nature.}
}
$$

真正的方法论是：

```text
cheap pilot runs
        ↓
careful measurement
        ↓
scaling curve
        ↓
held-out extrapolation
        ↓
expensive decision
```

这就是为什么 **Lecture 9 是 CS336 里非常重要的一讲**：前八讲是在教你“怎样把大模型造出来”；从这一讲开始，是在教你像真正的 frontier-model team 一样回答——

$$
\boxed{
\textbf{有限的十万、百万 GPU-hours，
究竟应该花在哪里？}
}
$$

而 Lecture 11 会再回来回答更实践的问题：**真实团队到底如何选择 architecture scaling、batch/LR、μP、WSD，并复现/改造 Chinchilla scaling recipe。**
