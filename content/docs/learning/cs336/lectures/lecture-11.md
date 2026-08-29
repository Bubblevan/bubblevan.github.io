---
title: "L11 · Scaling Laws"
weight: 11
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "scaling-laws"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture11/
---

Lecture 11 是 **Lecture 9 的“落地篇”**。

Stanford 2026 官方课程表中，Lecture 11 是 5 月 4 日 Tatsu 主讲的第二讲 **Scaling laws**，材料是官方 `lecture_11.pdf`；它正好处于 A3 Scaling 期间。Lecture 9 解决的是：

[
\boxed{\text{Scaling law 是什么？}}
]

包括 power law、IsoFLOP、Kaplan vs Chinchilla、compute-optimal (N,D)。

Lecture 11 则开始问一个更加残酷的现实问题：

[
\boxed{
\textbf{你真的准备把 100M 小模型的实验结论，
拿去决定一次 100B hero run 吗？}
}
]

因为不仅模型大小 (N) 和数据量 (D) 会 scale，**learning rate、batch size、初始化、optimizer 乃至训练 schedule 本身也会随规模变化**。如果这些东西没处理好，你拟合出来的所谓 scaling law 很可能只是在预测“一个越来越差的训练 recipe”。官方课程确实把 Lecture 9、11 连续安排为两讲 Scaling Laws。([GitHub][1])

所以我认为 Lecture 11 最重要的一句话是：

[
\boxed{
\textbf{不要 scale 一个模型；
要 scale 一整套 training recipe。}
}
]

---

# 0. Lecture 9 到 Lecture 11，到底升级了什么？

Lecture 9 我们写过：

[
L(N,D)
======

E+
A N^{-\alpha}
+
B D^{-\beta}.
]

给定：

[
C\approx6ND
]

可以寻找：

[
N^*(C),\quad D^*(C).
]

看起来问题解决了。

但实际上，这里面偷偷假设了一件非常强的事情：

> **不同规模的模型都被训练得同样好。**

也就是说：

```text
100M model → optimal LR / batch / schedule
1B model   → optimal LR / batch / schedule
10B model  → optimal LR / batch / schedule
100B model → optimal LR / batch / schedule
```

可现实中，如果你所有模型都用：

```text
LR = 3e-4
batch = 4M tokens
warmup = 2000 steps
weight decay = 0.1
```

很可能：

```text
100M：训练得很差
1B：还可以
10B：很好
```

于是你观察到：

[
L(100M),L(1B),L(10B)
]

之间非常漂亮的 power law。

但这个 slope 同时包含了：

[
\boxed{\text{model scaling}}
]

和：

[
\boxed{\text{hyperparameter mismatch}}
]

两个效应。

**这就是 Lecture 11 真正要消灭的 confounder。**

---

# 1. 因此出现两种完全不同的 Scaling 哲学

这一讲可以先压缩成两条路线：

## 路线 A：让超参数“不再漂”

代表：

[
\boxed{\mu P}
]

Maximum Update Parametrization。

目标：

> 模型从 100M 放大到 10B 后，最好仍然使用差不多的 learning rate 等超参数。

也就是：

[
\eta^*_{100M}
\approx
\eta^**{1B}
\approx
\eta^**{10B}.
]

然后你就可以：

```text
tiny proxy model
↓
调超参数
↓
zero-shot transfer
↓
huge model
```

这就是：

[
\boxed{\mu\text{Transfer}}
]

Tensor Programs V 的原始工作正是证明：在 μP parameterization 下，很多最优超参数可以跨模型宽度保持稳定，因此可以在小模型上调参后直接 transfer 到大模型。([arXiv][2])

---

## 路线 B：承认超参数会漂，那就预测它

代表 Lecture 11 里的 DeepSeek、StepFun 等路线。

例如：

[
\boxed{
\eta_{\rm opt}
==============

f(N,D,C)
}
]

[
\boxed{
B_{\rm opt}
===========

g(N,D,C)
}
]

小规模上训练很多模型：

```text
LR × batch size grid
```

找到 optimum。

然后：

```text
100M optimum
300M optimum
1B optimum
...
```

自己再拟合一个 scaling law。

于是：

[
\boxed{\text{Scaling law for hyperparameters}}
]

而不只是：

[
\boxed{\text{Scaling law for loss}}
]

---

# 2. 所以 Lecture 11 的核心其实是：

[
\boxed{
\text{Stabilize hyperparameters}
\quad\text{vs}\quad
\text{Predict hyperparameters}
}
]

这两个思路非常重要。

以后你看 frontier lab 的技术报告，基本都可以先问：

> 它是怎么解决 hyperparameter drift 的？

不是：

> 它有没有引用 Chinchilla？

这才是真正进入 scaling practice。

---

# 3. MiniCPM：非常适合拿来理解“稳定化”路线

Lecture 11 用 MiniCPM 作为很重要的 case study。

MiniCPM 论文一个很特别的地方，就是它不是只告诉你：

> “我们训练了一个 2B 模型，效果很好。”

而是公开描述了大量：

[
\boxed{\text{model wind-tunnel experiments}}
]

也就是用很多小 proxy models 去决定最终模型该怎么 scale。

MiniCPM 使用 μP，并引入 **Warmup-Stable-Decay，WSD** 学习率 schedule，目的之一正是让 scaling experiments 更便宜、更容易复用。([arXiv][3])

---

# 4. 为什么 Learning Rate 是 Scaling 中特别危险的超参数？

考虑最普通的：

[
W\in\mathbb R^{n\times n}.
]

模型变宽：

[
n:
512\rightarrow1024\rightarrow4096.
]

即使：

[
\eta
]

这个 learning rate 数字保持不变：

[
10^{-3},
]

一次参数 update 对整个 hidden representation 造成的影响：

[
\Delta h
]

也不一定保持不变。

你真正应该关心的是：

[
\boxed{
\text{一次 optimizer step 让网络 function 改变多少？}
}
]

而不是：

[
\boxed{
\text{parameter element 数字改变多少？}
}
]

这就是 μP 的出发点。

---

# 5. 为什么 Standard Parameterization 会让 LR 漂？

假设：

[
h_l=W_lh_{l-1}.
]

如果 hidden width：

[
n
]

越来越大。

我们通常初始化：

[
W_{ij}
\sim
\mathcal N
\left(
0,\frac1n
\right).
]

也就是标准差：

[
\sim\frac1{\sqrt n}.
]

这样 forward activation 可以保持：

[
O(1)
]

每个 coordinate 的尺度。

很好。

可是 training 时：

[
W\rightarrow W+\Delta W.
]

那么：

[
h'
==

(W+\Delta W)h.
]

变化：

[
\boxed{
\Delta h
========

\Delta W h
}
]

如果 width 从：

[
512\rightarrow8192,
]

(\Delta W h) 中参与累加的项数也增加了。

所以同一个：

[
\eta
]

并不保证：

[
|\Delta h|
]

仍然是同样数量级。

于是你可能发现：

```text
width 256:
best LR = 1e-3

width 1024:
best LR = 3e-4

width 4096:
best LR = 1e-4
```

这不是玄学。

本质是：

[
\boxed{\text{parameterization 没有保证 function update 随 width invariant}}
]

---

# 6. μP 想守住两条不变量

Lecture 11 后半专门深入解释 μP。

最值得记的是两个条件。

## 条件 A1：初始化时 activation 不炸、不消失

单个 activation 希望：

[
h_{l,i}=\Theta(1).
]

所以整层 norm：

[
|h_l|
=====

\Theta(\sqrt{n_l}).
]

也就是说模型变宽：

> representation 维度变多，但每个 feature 本身应该仍然 (O(1))。

---

## 条件 A2：训练 update 也不能消失或爆炸

一次 gradient step：

[
W_l\rightarrow W_l+\Delta W_l
]

希望带来的 function/activation change：

[
\Delta h_l
]

仍然保持：

[
\boxed{\Theta(1)}
]

per coordinate。

否则：

### 太小

[
\Delta h\rightarrow0
]

模型越宽越学不动。

### 太大

[
\Delta h\rightarrow\infty
]

模型越宽越不稳定。

所以 μP 的灵魂其实不是：

> “一种神奇初始化”。

而是：

[
\boxed{
\textbf{让 activation scale 和 update scale
在 width → ∞ 时都有良好极限。}
}
]

---

# 7. 这就是为什么 μP 不是“把所有 LR 除以 width”

这点特别容易学错。

Transformer 里有不同类型参数：

```text
Embedding
Attention projection
MLP input matrix
MLP output matrix
LM head
Norm parameters
...
```

它们的：

[
fan_{in},fan_{out}
]

结构不同。

而且 optimizer 不同：

```text
SGD
Adam
Muon
```

update scaling 也完全不同。

所以 μP 实际要求：

[
\boxed{\text{不同 tensor role 使用不同 init / LR multipliers}}
]

Tensor Programs V 的 μTransfer 也是按 parameter type 来定义规则，而不是给整个模型乘一个统一 magic factor。([OpenReview][4])

因此如果以后真要实现 μP：

> **不要凭“LR / width”这一句话自己手搓。**

应该按照具体：

```text
parameter type
optimizer
base model shape
target model shape
```

使用完整规则。

---

# 8. μP 最神奇的结果到底是什么？

假设普通 parameterization：

```text
loss
 ^
 | width 256  \__
 | width 512     \__
 | width 2048         \__
 +--------------------------> learning rate

             minima 在漂
```

μP 希望得到：

```text
loss
 ^
 | width 256       \_/
 | width 512       \_/
 | width 2048      \_/
 +--------------------------> learning rate
                    ^
                  same LR
```

也就是说：

[
\boxed{
\eta^*(n)
\approx
\text{constant}
}
]

这样你就可以：

```text
40M model
↓
LR sweep
↓
best = 1e-3
↓
直接拿去训 7B
```

而不是在 7B 上：

```text
3e-4?
1e-4?
6e-4?
2e-4?
```

每试一次都是巨大算力。

Tensor Programs V 就报告过从 40M proxy transfer 超参数到 6.7B GPT-like 模型的实验。([arXiv][2])

这就是 μP 的经济价值。

---

# 9. 但是 LR 稳定了，Batch Size 仍然会漂

这是 Lecture 11 很漂亮的一层。

μP：

[
\boxed{\text{让 LR 更容易跨 width transfer}}
]

并不意味着：

[
\boxed{\text{batch size 也变成常数}}
]

随着训练越来越深入：

[
L\downarrow,
]

gradient signal/noise structure 会变化。

Lecture 9 已经讲过 critical batch size：

> batch 增大一开始可以减少 gradient noise 和 optimizer steps，但超过某个点以后收益越来越小。

因此最佳 batch：

[
B_{\rm opt}
]

往往会随着 target loss / 数据量发生变化。

所以一个完整 scaling recipe 不可能只有：

```text
μP → done
```

而更像：

```text
μP
→ stabilize LR

scaling law
→ choose batch
```

---

# 10. WSD：我认为是 Lecture 11 最值得真正学会的工程技巧

WSD：

[
\boxed{
\text{Warmup}
\rightarrow
\text{Stable}
\rightarrow
\text{Decay}
}
]

学习率大概长这样：

```text
LR
 ^
 |       ┌──────────────────────┐
 |      /                       │
 |     /                        │
 |    /                         │
 |___/                          └────\
 |                                   \__
 +----------------------------------------> tokens

 warmup        stable            decay
```

MiniCPM 将 WSD 用于 scalable/continued training，而后来的工作也专门分析了 WSD 的训练动力学。([arXiv][3])

---

# 11. 为什么 Cosine 对 Scaling Experiment 很麻烦？

Cosine：

[
\eta(t)
=======

\frac{\eta_{\max}}2
\left[
1+\cos\left(\frac{\pi t}{T}\right)
\right].
]

注意那个：

[
\boxed T
]

是**总训练长度**。

假设你想比较：

```text
100B tokens
200B tokens
400B tokens
800B tokens
```

如果每个实验都用 cosine：

### 100B run

在 100B 时：

[
\eta\rightarrow0.
]

### 800B run

在 100B 时：

[
\eta
]

其实还很高。

所以你不能：

> “训练一次 800B，然后把 100B checkpoint 当成 100B 模型。”

因为那个 checkpoint 根本没经历：

[
\boxed{\text{final LR decay}}
]

它不是完整结束的 100B-token training recipe。

所以 Chinchilla data sweep 可能要求：

```text
100B 从头训
200B 从头训
400B 从头训
800B 从头训
```

非常贵。

---

# 12. WSD 为什么解决了这个问题？

Stable 阶段：

[
\eta=\eta_{\max}
]

基本不依赖最终训练 horizon。

于是你可以先训练一条：

```text
warmup
↓
stable stable stable stable stable stable
        ↑       ↑       ↑       ↑
       D1      D2      D3      D4
```

保存 checkpoints。

如果想获得 (D_1) token 模型：

```text
checkpoint D1
↓
接 decay tail
```

想获得 (D_2)：

```text
checkpoint D2
↓
同样接 decay tail
```

于是：

[
\boxed{\text{一个 long stable trunk 可以分叉出多个 training horizons}}
]

这是一种极其聪明的 experiment reuse。

---

# 13. 所以 WSD 的价值不只是“模型训练得更好”

很多人看到 WSD 会把它当：

> cosine vs linear vs WSD，哪个最终 loss 更低？

Lecture 11 更重要的视角其实是：

[
\boxed{\textbf{WSD 是 scaling experiment infrastructure。}}
]

它改变了 experiment economics：

### Cosine

[
D_1+D_2+D_3+D_4
]

都重新训练。

### WSD

主体训练大约只跑：

[
D_{\max}
]

再为不同 checkpoints 追加较短 decay tails。

这会让：

[
\boxed{\text{data-scaling experiments 大幅便宜}}
]

这正是 MiniCPM 原论文强调 WSD 的一个重要原因。([arXiv][3])

---

# 14. 于是 MiniCPM 可以更便宜地做 Chinchilla-style analysis

回忆 Lecture 9：

固定 compute：

[
C.
]

利用：

[
C\approx6ND
]

扫描：

```text
small N × lots of D
medium N × medium D
large N × little D
```

找：

[
N^*(C).
]

问题是：

> 每个 (N,D) 都从头训练，太贵。

WSD 让同一个模型大小下的多个 (D)：

[
D_1,D_2,D_3
]

可以共享 stable trunk。

所以这实际上降低了 scaling-law research 本身的 compute cost。

MiniCPM 也因此得到过明显高于原始 Chinchilla 20:1 的 compute-optimal token/model ratio；真正应该学到的不是把它的新常数继续当成新“宇宙常数”，而是：

[
\boxed{\text{tokens/parameter 会随 recipe 改变}}
]

这一点。([arXiv][3])

---

# 15. DeepSeek 走的是另一条路：我不强迫 LR 不变，我直接预测它

DeepSeek LLM 的 scaling study 很适合和 μP 对照。

他们做：

[
\boxed{\text{LR}\times\text{Batch Size grid search}}
]

例如：

```text
                 Batch
             low  med  high
LR high       ●    ●    ●
LR med        ●    ★    ●
LR low        ●    ●    ●
```

每一个点都真正训练。

找到：

[
(\eta^*,B^*).
]

然后换 compute scale：

[
C_1,C_2,C_3,\dots
]

重复。

最终拟合：

[
\boxed{
\eta_{\rm opt}(C)
}
]

和：

[
\boxed{
B_{\rm opt}(C)
}
]

DeepSeek LLM 的公开拟合为：

[
\eta_{\rm opt}
==============

0.3118,C^{-0.1250}
]

[
B_{\rm opt}
===========

0.2920,C^{0.3271}.
]

数值常数依赖他们使用的 compute/batch 单位，因此不要拿数字直接套自己的训练；真正重要的是方向：

[
\boxed{
C\uparrow
\Rightarrow
\eta^*\downarrow
}
]

而：

[
\boxed{
C\uparrow
\Rightarrow
B^*\uparrow
}
]

这是 DeepSeek 原论文公开报告的结果。([arXiv][5])

---

# 16. μP 和 DeepSeek 其实是在回答同一个问题

问题：

[
\boxed{
\text{小模型找到的最佳 LR，怎么用到大模型？}
}
]

μP：

> 改 parameterization，让：

[
\eta^*(N)
\approx constant.
]

DeepSeek：

> 不改 parameterization，直接估：

[
\eta^*(N,D,C).
]

所以：

[
\boxed{
\mu P=\text{make the optimum invariant}
}
]

而：

[
\boxed{
\text{Hyperparameter scaling law}
=================================

\text{predict how the optimum moves}
}
]

这是整堂 Lecture 11 最值得形成的两分法。

---

# 17. 哪一种更高级？

没有这种简单排序。

μP 的优点：

[
\boxed{\text{proxy → target transfer 很便宜}}
]

如果真的稳定，hero run 风险很低。

但你改变：

```text
optimizer
normalization
architecture
weight decay
```

原有 μP transfer 可能不再完美。

---

直接拟合 scaling law：

优点：

[
\boxed{\text{更 empirical，少依赖理论 parameterization 假设}}
]

但代价：

> 要烧大量 grid experiments。

而且如果 LR grid：

```text
1e-3
3e-4
1e-4
3e-5
```

太稀疏，

你所谓的 optimum：

[
\eta^*
]

本身就带有很大 **grid quantization error**。

Lecture 11 也提醒过对某些 LR scaling fit 要保持怀疑态度。

所以：

[
\boxed{\text{scaling practice 不存在免费午餐}}
]

---

# 18. StepFun 把这个问题又推进了一步

如果你只说：

[
B^*=B(C),
\qquad
\eta^*=\eta(C)
]

其实默认：

[
C
]

是决定超参数的唯一变量。

但：

[
C\approx6ND.
]

相同：

[
C
]

可以来自：

```text
large N, small D
```

或者：

```text
small N, large D
```

这两种训练的 optimization dynamics 真的一样吗？

未必。

StepFun 的 Predictable Scale 工作做了非常大规模的 LR × batch search；其公开结果提出：

[
\boxed{
B^*
\text{ 主要跟 }D\text{ 有关}
}
]

而：

[
\boxed{
\eta^*
\text{ 同时跟 }N,D\text{ 有关}
}
]

例如其报告的经验形式：

[
\eta(N,D)
=========

1.79N^{-0.713}D^{0.307}
]

[
B(D)
====

0.58D^{0.571}.
]

同样，常数依赖其单位定义，不应该直接照抄；真正重要的是变量依赖关系。StepFun 报告其研究训练了数千个不同超参数/规模的 LLM，并且发现 LR–batch loss landscape 有较宽的近最优盆地。([Step Law][6])

---

# 19. 这个结果为什么很有启发性？

因为把：

[
C=6ND
]

固定。

仍可以改变：

[
\frac DN.
]

而：

[
\boxed{\frac DN}
]

恰恰就是：

> 一个 parameter 被多少 training tokens“使用”。

这会改变 optimization regime。

所以 Lecture 11 给出的一个高级认知是：

[
\boxed{
\textbf{不能只沿 “model size” 一个轴讨论 scaling。}
}
]

至少有：

[
N,\quad D,\quad B,\quad\eta
]

互相耦合。

这也是为什么 scaling study 最后越来越像：

[
\boxed{\text{一个多维 response surface estimation 问题}}
]

而不是：

> “我画条 log-log 直线。”

---

# 20. LR × Batch 的 loss landscape 其实通常不是一个针尖

这是一个很重要的工程好消息。

固定：

[
N,D
]

然后画：

[
L(\eta,B).
]

很多实验会发现类似：

```text
batch
 ^
 |        +++++
 |      ++.....++
 |     +..     ..+
 |    +.   ★     .+
 |     +..     ..+
 |      ++.....++
 +-------------------> LR
```

也就是说 optimum 附近往往有一个：

[
\boxed{\text{broad basin}}
]

而不是：

```text
LR=3.7421e-4
```

一偏 1% 就爆炸。

StepFun 的大规模 grid search 就报告了这种比较平滑、近似 convex 的 hyperparameter landscape。([Step Law][6])

所以真正的 engineering 目标很多时候不是：

[
\boxed{\text{找到数学意义上的 exact optimum}}
]

而是：

[
\boxed{\text{可靠地落入 near-optimal region}}
]

这会大幅降低 hero run 的风险。

---

# 21. 接下来 Lecture 11 为什么突然讲 Optimizer？

因为 optimizer 本身也需要 scale。

想象：

```text
100M model:
Optimizer A > AdamW
```

是不是说明：

```text
100B model:
Optimizer A > AdamW
```

完全不能保证。

你应该比较的是：

[
\boxed{\text{optimizer scaling curve}}
]

例如：

[
L_{\rm Adam}(C)
]

和：

[
L_{\rm new}(C).
]

可能：

```text
small C:
New optimizer 赢 20%

huge C:
优势缩到 2%
```

甚至反转。

所以一个在 NanoGPT speedrun 上特别强的 optimizer，不等于 frontier pretraining 上一定强。

---

# 22. Muon 为什么在 Lecture 11 很重要？

Muon 是近年的一个非常有意思的 optimizer。

Adam 的思想大体是：

[
\boxed{\text{coordinate-wise normalization}}
]

每个 parameter coordinate 根据自己的历史一二阶统计量调整。

对于一个矩阵 gradient：

[
G
]

Muon 更强调：

[
\boxed{\text{matrix geometry}}
]

粗略地，先得到 momentum matrix：

[
M.
]

做 SVD：

[
M=U\Sigma V^\top.
]

Muon 希望得到近似：

[
\boxed{
UV^\top
}
]

也就是把 singular values：

[
\sigma_i
]

都朝相近尺度归一。

但每 step 真做 SVD 太贵。

所以实践里使用：

[
\boxed{\text{Newton–Schulz iterations}}
]

用一串矩阵乘法近似这种 orthogonalization。

---

# 23. 可以怎么直觉理解 Muon？

Adam：

> 每个**坐标**走多大一步？

Muon：

> 一个 weight matrix 在不同**奇异方向**上应该走多大一步？

所以：

[
\boxed{\text{coordinate geometry}}
]

vs

[
\boxed{\text{spectral / matrix geometry}}
]

这也是为什么 Muon 主要针对：

[
\boxed{\text{2D weight matrices}}
]

而 Norm gains、biases 等其他参数通常仍由 AdamW 一类 optimizer 处理。

---

# 24. 但是 Muon 又完美展示了为什么 Scaling Study 必不可少

Moonlight 的工作专门研究：

[
\boxed{\text{Muon 能不能从小模型 scale 到真正 LLM？}}
]

它发现 scaling Muon 不能简单把小模型配置照搬，**weight decay 和 per-parameter update scale** 都很重要；其报告的 compute-optimal scaling experiments 中，Muon 相比 AdamW 达到约 2× compute efficiency，并进一步用 Muon 训练了 Moonlight MoE。([GitHub][7])

真正值得学的不是：

> “Muon = AdamW 2×，以后都换掉。”

而是：

[
\boxed{
\textbf{优化器的相对优势也必须经过 scale validation。}
}
]

---

# 25. 为什么 optimizer comparison 特别容易被骗？

假设：

Optimizer A：

```text
LR = optimal
WD = optimal
```

AdamW：

```text
LR = default
WD = default
```

结果：

[
A
]

赢 15%。

你不能得出：

> A 是更好的 optimizer。

可能只说明：

> AdamW 调参比较烂。

还有一个更隐蔽的 confounder：

[
\boxed{\frac DN}
]

如果你的实验：

```text
N 很大
D 很少
```

属于 overparameterized regime。

某 optimizer 可能特别擅长这种 regime。

但是 production model：

```text
N 更小
D 巨大
```

属于 data-rich / overtrained regime。

结论可能不再成立。

所以 optimizer scaling 必须至少考虑：

[
\boxed{C}
]

和：

[
\boxed{D/N}
]

两个方向。

---

# 26. 这也解释了为什么 Kimi K2 的 Scaling 很有意思

Kimi K2 的公开技术资料中，用 scaling-law 分析决定了 MoE 的 sparsity：在固定 activated parameters / 近似 compute 的条件下，提高 total experts 数、增加 sparsity 可以继续改善 loss，但收益递减；最终 K2 选择了 384 experts、每 token 激活 8 个，即 sparsity 48 的方案。([伯克利研发院][8])

注意这已经不是：

[
N,D
]

二维 scaling。

而是新增：

[
\boxed{S=\text{MoE sparsity}}
]

于是：

[
L
=

L(C,N,D,S,\dots).
]

这就是现代 scaling research 真正的发展方向：

> **用 scaling experiments 决定 architecture hyperparameters。**

---

# 27. 于是 Lecture 9 的 IsoFLOP 又回来了

假设比较 MoE sparsity：

[
S=8,\ 16,\ 32,\ 48.
]

不能：

```text
S=48 model 算力多 10×
↓
loss 更好
↓
宣布 sparsity 48 更好
```

必须固定：

[
\boxed{\text{training compute}}
]

或者至少固定 activated parameter FLOPs。

然后比较：

[
L(S\mid C=\text{constant}).
]

这就是：

[
\boxed{\text{IsoFLOP}}
]

为什么它不只是 Chinchilla 的一个技巧，而是一种通用实验哲学：

> **先固定你真正关心的资源预算，再比较 design choice。**

---

# 28. 现在再回来看 μP，会发现它本质上是在解决“实验可迁移性”

我们不妨把 scaling experiment 写成：

[
\boxed{
\text{small proxy}
\xrightarrow{\text{transfer}}
\text{large target}
}
]

问题就是：

[
\boxed{\text{什么东西可以 transfer？}}
]

architecture ratios？

可能。

data mixture？

有时。

learning rate？

Standard parameterization 下经常漂。

batch？

往往会漂。

μP 试图让：

[
\boxed{\eta}
]

这一类最敏感超参数变成 transferable。

于是 scaling experiment 的 sample efficiency 大幅提高。

这也解释了 μP 为什么和 Scaling Law 课程放在一起，而不是单纯放在“Optimizer Lecture”。

---

# 29. 但 μP 不是万能魔法

这是学习它必须有的警惕。

经典 μP 的推导依赖特定：

```text
parameterization
width scaling
optimizer update behavior
```

现代 Transformer 又有：

```text
RMSNorm
RoPE
SwiGLU
MoE
QK-Norm
weight decay
Muon / normalized optimizers
```

这些都会改变 scale dynamics。

所以：

[
\boxed{
\text{μP 给你原则和一套 parameterization，
不是“从此永不再调参”的许可证。}
}
]

真正做新 architecture 时，仍然应该：

[
\boxed{\text{小规模 empirical validation}}
]

检查：

```text
LR optimum 是否真的重合？
loss curves 是否真的 parallel？
activation/update statistics 是否稳定？
```

---

# 30. Lecture 11 最终是在教你怎么设计一个真正的 Scaling Recipe

我会把完整 workflow 写成：

## Step 1：先冻结模型族

例如规定：

[
d_{\rm ff}
\approx
\frac83d
]

[
n_{\rm heads}\propto d
]

[
L\propto d^{?}
]

保持合理 aspect ratio。

否则：

```text
100M = skinny deep
1B = wide shallow
10B = totally different architecture
```

你连“scale 的是什么”都不知道。

---

## Step 2：明确参数和 compute 定义

必须统一：

```text
total parameters?
non-embedding parameters?
active MoE parameters?
total MoE parameters?
```

以及：

[
C
]

到底按：

[
6ND
]

还是实际 measured FLOPs。

这是 Lecture 9 已经踩过的坑。

---

## Step 3：解决最敏感 hyperparameters

两条路线任选或混用：

### μP

[
\boxed{\text{stabilize}}
]

### LR / batch scaling laws

[
\boxed{\text{predict}}
]

不要假定常数。

---

## Step 4：在小模型上画 LR × Batch Surface

不要只试：

```text
LR = 3e-4
```

至少形成：

[
L(\eta,B)
]

的基本二维图。

你需要知道：

> optimum 在哪里？

更重要：

> near-optimal basin 有多宽？

---

## Step 5：使用 WSD 组织训练

```text
warmup
↓
long stable trunk
↓
branch checkpoints
↓
multiple decay tails
```

让 data-scaling experiment 可以复用。

---

## Step 6：做 IsoFLOP

固定：

[
C_i.
]

扫描：

[
N
]

以及对应：

[
D=\frac{C_i}{6N}.
]

得到：

[
N^*(C_i).
]

---

## Step 7：拟合 Scaling Laws

至少包括：

[
L^*(C)
]

[
N^*(C)
]

[
D^*(C)
]

以及必要时：

[
B^*(C)
]

[
\eta^*(C)
]

甚至：

[
S_{\rm MoE}^*(C).
]

---

## Step 8：一定留 Held-Out Scale

假设 experiments：

[
10^{17}
-------

10^{20}
\text{ FLOPs}.
]

别把：

[
10^{20}
]

也拿来 fitting。

可以用：

[
10^{17}-10^{19}
]

预测：

[
10^{20}
]

然后真的跑。

因为真正要验证的是：

[
\boxed{\text{Extrapolation}}
]

不是 interpolation。

---

# 31. Lecture 11 和 A3 的连接其实比 Lecture 9 更直接

A3 表面上让你：

> 用有限 experimental compute，预测更大规模模型。

很容易形成：

```text
训练几个模型
↓
拟合 log-log line
↓
交答案
```

Lecture 11 告诉你：

**真正困难的不是 curve fitting。**

真正困难的是保证：

[
\boxed{\text{每个 scale 都是公平且接近 optimal 的 recipe}}
]

否则你的：

[
L(C)
]

只是：

[
L(C,\eta_{\rm bad},B_{\rm bad},schedule_{\rm bad}).
]

真正想估计的其实是：

[
\boxed{
L^*(C)
======

\min_{\theta_{\rm recipe}}
L(C,\theta_{\rm recipe})
}
]

其中：

[
\theta_{\rm recipe}
===================

{
N,D,
\eta,B,
schedule,
architecture,
optimizer,\ldots
}.
]

这就已经从简单 regression 变成：

[
\boxed{\text{实验设计 + 优化 + 预测}}
]

了。

---

# 32. 这也是为什么 Scaling Laws 不是“做一条直线”那么简单

你可以得到：

[
R^2=0.9999.
]

仍然完全没用。

因为你可能拟合的是：

```text
小模型严重 under-tuned
中模型比较合理
大模型调得很好
```

于是直线非常漂亮。

然后外推：

[
100B.
]

直接炸。

所以 scaling study 真正最重要的是：

[
\boxed{\text{控制变量}}
]

而不是：

[
\boxed{\text{regression 技巧}}
]

---

# 33. 一个很重要的新 mental model：Scaling 不是一条曲线，而是一条“最优轨迹”

考虑整个超参数空间：

[
(N,D,\eta,B,\ldots).
]

每个 compute budget：

[
C
]

对应一张 loss landscape。

例如：

```text
C1:
        ★ optimum

C2:
             ★ optimum

C3:
                   ★ optimum
```

随着：

[
C\uparrow
]

optimum 在高维空间中不断移动。

所以你真正想找的是：

[
\boxed{
\theta^*(C)
}
]

也就是：

[
\boxed{\text{一条 optimal scaling trajectory}}
]

而不是只有：

[
L(C).
]

这就是 Lecture 11 相比 Lecture 9 最大的认知升级。

---

# 34. μP 和 Hyperparameter Scaling Law 其实就是两种“追踪轨迹”的方式

### μP

改变坐标系，让轨迹尽可能变直：

[
\eta^*(C)
\approx const.
]

---

### Scaling-law fitting

保持原坐标系：

[
\eta^*(C)
=========

aC^{-\gamma}.
]

直接追踪 optimum。

这甚至可以用一个几何类比理解：

> μP 是重新 parameterize 空间，让 optimum 不怎么移动；
> DeepSeek/StepFun 是测量 optimum 怎么移动，再预测它。

非常漂亮。

---

# 35. 为什么 WSD 也是同一个思想？

因为 training horizon：

[
D
]

也是 scaling recipe 的一个坐标。

Cosine：

[
\eta(t;D)
]

让整个 trajectory 都依赖最终 (D)。

所以不同数据规模：

[
D_1,D_2,D_3
]

无法共享轨迹。

WSD：

[
\eta(t)
]

在 stable phase 基本与 (D) 解耦。

于是：

[
\boxed{\text{不同 data horizons 共享一条训练主干}}
]

所以 μP 和 WSD 看似完全不同：

```text
μP → parameterization
WSD → LR schedule
```

但它们背后的 scaling philosophy 其实一样：

[
\boxed{\textbf{让不同规模尽可能共享相同 recipe。}}
]

---

# 36. Lecture 11 里很多公开模型案例最终都在做同一件事

不管是：

```text
MiniCPM
DeepSeek
StepFun
Qwen
Kimi
Llama
MiniMax
...
```

真正值得学习的不是：

> 谁的 token/parameter ratio 是多少？

而是它们通常都会做：

1. 小规模 model family；
2. 控制 architecture ratios；
3. LR / batch sweep；
4. 固定 compute 做 IsoFLOP；
5. 找最佳 data/model allocation；
6. 对新的 architecture 参数再做 scaling experiments；
7. 最后才决定 hero model。

这才是你应该从技术报告 architecture table 背后看到的流程。

---

# 37. 这堂课也给“复现新架构论文”一个很重要的警告

假设论文：

> NewAttention 在 300M 模型上比 Transformer 好 0.08 loss。

你不能马上说：

> NewAttention 更强。

至少要问：

[
\boxed{\text{它们 LR 都是各自 optimal 吗？}}
]

[
\boxed{\text{batch size 公平吗？}}
]

[
\boxed{\text{同 FLOPs 吗？}}
]

[
\boxed{\text{同 tokens 吗？}}
]

[
\boxed{\text{优势会随 scale 保持吗？}}
]

可能：

```text
100M：New wins
300M：New wins
1B：tie
7B：old wins
```

如果 slope 不同：

[
\boxed{\text{small-scale leaderboard 根本不能直接决定 large-scale architecture}}
]

这就是 scaling-aware research。

---

# 38. 对 Scaling Experiment 来说，“稳定”本身就是一种性能

这是一个非常值得带走的概念。

假设 Architecture A：

[
L_A=2.50
]

Architecture B：

[
L_B=2.48.
]

B 好 0.02。

但：

### A

```text
LR 范围很宽
batch 不敏感
scale 预测稳定
从来不炸
```

### B

```text
LR 必须精确
偶尔 loss spike
大模型 behavior 不可预测
```

如果目标是：

[
10^{25}\text{ FLOPs hero run},
]

你未必选 B。

因为：

[
\boxed{
\text{predictability itself has enormous economic value}
}
]

这其实正呼应 CS336 Lecture 1 一开始强调的 scaling recipe 思想：用便宜的小规模实验预测目标规模，而不是在目标规模暴力搜参。([GitHub][9])

---

# 39. 所以 Lecture 11 最终不是“Scaling Laws 2”

更准确地说，它在教：

[
\boxed{\text{Scaling Engineering}}
]

Lecture 9 更偏：

[
\boxed{
\text{统计规律：
N,D,C,L 如何关联}
}
]

Lecture 11 更偏：

[
\boxed{
\text{实验工程：
怎么让这些规律在真实训练中成立}
}
]

这两者缺一不可。

---

# 40. 我给你一张完整的 Lecture 11 总图

```text
                    Target Hero Run
                          ↑
                          │ extrapolate
                          │
               ┌──────────┴──────────┐
               │                     │
         Loss Scaling          HP Scaling
               │                     │
         L*(C), N*(C)          LR*(C), B*(C)
               │                     │
               └──────────┬──────────┘
                          │
                       IsoFLOP
                          │
                small-scale experiments
                          │
       ┌──────────────────┼─────────────────┐
       │                  │                 │
      μP                 WSD          LR × Batch sweep
       │                  │                 │
stabilize width      reuse data      find near-optimal
hyperparameters      horizons            basin
       │                  │                 │
       └──────────────────┴─────────────────┘
                          │
                    Scaling Recipe
```

这就是整堂课。

---

# 41. Lecture 9 和 Lecture 11 的区别，最后再压缩一次

## Lecture 9

问：

[
\boxed{
\text{固定 compute，
N 和 D 应该怎么分？}
}
]

核心：

[
C\approx6ND
]

和：

[
N^*(C),D^*(C).
]

---

## Lecture 11

问：

[
\boxed{
\text{你凭什么相信小规模的最优配置，
到了大规模仍然是最优的？}
}
]

于是出现：

[
\boxed{\mu P}
]

[
\boxed{\text{LR scaling}}
]

[
\boxed{\text{batch scaling}}
]

[
\boxed{\text{WSD}}
]

[
\boxed{\text{optimizer scaling}}
]

[
\boxed{\text{architecture scaling}}
]

这才是真正的 hero-run preparation。

---

# 42. 我最希望你真正会的 10 道 Lecture 11 自测题

### 1. 为什么只拟合

[
L(C)
]

可能得到错误 scaling law？

因为不同 (C) 下超参数可能离各自 optimum 距离不同。

---

### 2. μP 到底想保持什么不变？

不是参数值。

而是：

[
\boxed{\text{activation scale + update/function-change scale}}
]

随 width 稳定。

---

### 3. μTransfer 为什么能省钱？

因为：

[
\boxed{\text{在小 proxy 调 HP → 大模型直接 transfer}}
]

减少昂贵 hero-scale tuning。([arXiv][2])

---

### 4. 为什么 WSD 比 cosine 更适合 data scaling study？

因为 stable trunk 与最终 training horizon 基本解耦，可以从不同 checkpoints 分叉 decay。

---

### 5. DeepSeek 和 μP 的 scaling 哲学有什么不同？

[
\boxed{
\mu P:\ make\ HP^*\ stable
}
]

[
\boxed{
DeepSeek:\ fit\ HP^*(C)
}
]

---

### 6. 为什么 (B^*) 和 (\eta^*) 不一定只依赖 compute (C)？

因为：

[
C\sim ND
]

无法唯一决定 (N,D)；optimization dynamics 还可能依赖 (D/N) 等。

---

### 7. 为什么 hyperparameter landscape 的“宽谷底”非常重要？

因为 production 不需要 exact mathematical optimum，只要可靠进入 near-optimal basin。

---

### 8. 一个 optimizer 在小模型赢了，为什么不能直接 scale？

因为 relative advantage 也可能随：

[
C,\quad N,\quad D/N
]

变化，且 baseline tuning 是巨大 confounder。

---

### 9. Muon 和 Adam 最大的几何区别是什么？

粗略：

[
\boxed{\text{Adam：coordinate-wise normalization}}
]

[
\boxed{\text{Muon：matrix/spectral normalization}}
]

---

### 10. Scaling experiment 最重要的 held-out 是什么？

不是随机留 20% 小模型。

而应该：

[
\boxed{\text{留一个更大的 scale 做 extrapolation test}}
]

因为你真正关心的是：

> 小规模预测大规模到底准不准。

---

# 最后，如果我作为老师只允许你带走五句话

第一：

[
\boxed{
\textbf{Scaling law 不是 loss 对 compute 的一条线，
而是一整套 recipe 随 compute 的轨迹。}
}
]

第二：

[
\boxed{
\mu P
=====

\text{让最优超参数尽量不随 width 漂}
}
]

第三：

[
\boxed{
\text{DeepSeek/StepFun-style scaling}
=====================================

\text{测量并预测最优超参数怎么漂}
}
]

第四：

[
\boxed{
WSD
===

\text{让不同 token budget 共享训练主干，
从而把 scaling experiments 做便宜}
}
]

第五，也是这一讲最重要的一句：

[
\boxed{
\textbf{你在小模型上真正需要验证的，
不是“这个方法现在好不好”，
而是“这个结论能不能被可靠地带到更大的尺度”。}
}
]

所以从 Lecture 9 → 11，CS336 已经从“Scaling Law 数学”真正进入了 **frontier lab 的研发方法论**：小模型不是最终产品，而是 **wind tunnel**；真正的产品还没造出来，你先用小规模实验预测它在目标尺度会不会飞。

而下一讲 Lecture 12 就会立刻追问一个同样棘手的问题：

[
\boxed{
\text{好，就算我们能预测一个大模型的 pretraining loss，
我们究竟怎么知道它真的“更好”？}
}
]

于是课程从 **Scaling → Evaluation**，这一步同样非常关键。
