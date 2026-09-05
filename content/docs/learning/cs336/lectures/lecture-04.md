---
title: "L04 · MoE"
weight: 4
date: 2026-08-28
updated: 2026-08-28
course: "CS336"
topics: ["CS336", "moe", "architecture"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture4/
---

可以把 Lecture 4 看成 **Lecture 3 的“高级改造课”**，为 Tatsu Hashimoto 主讲的 **“Attention alternatives and mixture of experts”**。Lecture 3 刚建立现代 Transformer 的骨架：

[
\boxed{\text{Attention}+\text{FFN}}
]

Lecture 4 就分别攻击这两个模块最贵的地方：

[
\boxed{\text{Attention：为什么每个 token 都非得看所有 token？}}
]

[
\boxed{\text{FFN：为什么每个 token 都非得经过所有参数？}}
]

前者导向 **linear attention / state-space models / sparse attention**；后者导向 **Mixture of Experts（MoE）**。

# 0. Lecture 4 的灵魂：不要让所有东西和所有东西交互

Lecture 3 的普通 Transformer 很“dense”。

Attention：

```text
token 1 ─┬─ token 1
         ├─ token 2
         ├─ token 3
         └─ ...
token 2 ─┬─ token 1
         ├─ token 2
         └─ ...
```

所有 token 两两交互。

FFN：

```text
token x
  ↓
整个 FFN 的所有参数
  ↓
output
```

每个 token 都走相同的大 FFN。

Lecture 4 问：

> 我们真正需要这么 dense 吗？

于是出现两个方向：

```text
Attention sparsity
每个 token 只保留有限状态 / 只关注少量 token

Parameter sparsity
每个 token 只激活少量 FFN experts
```

所以这堂课真正统一的主题其实是：

[
\boxed{\text{conditional / sparse computation}}
]

模型可以**拥有非常大的能力空间**，但每次 forward 不必把整个能力空间全部算一遍。官方 Lecture 4 明确将课程分为 efficient-attention alternatives 和 MoE 两大部分。

---

# 一、为什么 Attention 首先成为问题？

普通 self-attention：

[
Q,K,V\in\mathbb R^{N\times d}
]

计算：

[
A=
\operatorname{softmax}
\left(
\frac{QK^\top}{\sqrt d}
\right)
]

其中：

[
QK^\top\in\mathbb R^{N\times N}.
]

所以仅仅构造 attention scores：

[
\boxed{O(N^2d)}
]

而 attention matrix：

[
N\times N
]

也意味着非常严重的内存压力。

例如 context：

[
N=128K
]

那么单个 head 的 score matrix 理论元素数量已经：

[
(128K)^2\approx1.7\times10^{10}.
]

当然 FlashAttention 不会真的把这个完整矩阵写到 HBM，但数学上的 pairwise interaction 仍然存在。FlashAttention 的核心贡献是通过 tiling 减少 HBM↔SRAM 数据搬运，它是 **exact attention 的系统优化**，没有把 attention 的计算复杂度从 (O(N^2)) 改成 (O(N))。

这就是 Lecture 2 又回来了：

> **Big-O 和 constant factor 都重要。**

FlashAttention：

[
O(N^2)\rightarrow O(N^2)
]

但 wall-clock 可以快很多。

然而如果：

[
N=1M,\quad5M,\quad10M
]

再好的 constant factor 最终也可能扛不住平方增长。因此 Lecture 4 开始问：

[
\boxed{\text{能不能从数学结构本身消掉 }N^2?}
]

这正是 Lecture 4 前半的起点。

---

# 二、Linear Attention 最关键的一步，其实只是小学数学：结合律

先暂时把 softmax 忘掉。

普通 attention 的核心可以写成：

[
(QK^\top)V.
]

注意矩阵乘法满足结合律：

[
(AB)C=A(BC).
]

所以：

[
\boxed{
(QK^\top)V
==========

Q(K^\top V)
}
]

看起来只是括号位置变了。

但计算复杂度**完全变了**。

---

## 原来的计算顺序

先：

[
QK^\top
]

shape：

[
[N,d_k][d_k,N]
\rightarrow
[N,N].
]

计算量：

[
O(N^2d_k).
]

然后：

[
[N,N][N,d_v]
]

又是：

[
O(N^2d_v).
]

所以总体：

[
\boxed{
O(N^2(d_k+d_v))
}
]

---

# 三、重新加括号以后发生了什么？

先算：

[
K^\top V.
]

shape：

[
[d_k,N][N,d_v]
\rightarrow
[d_k,d_v].
]

复杂度：

[
O(Nd_kd_v).
]

然后：

[
Q(K^\top V)
]

复杂度还是：

[
O(Nd_kd_v).
]

所以：

[
\boxed{
O(Nd_kd_v)
}
]

如果 (d_k,d_v) 相对于 context length 是固定的，那么：

[
\boxed{
O(N^2)\rightarrow O(N)
}
]

这就是所谓 **linear attention** 最核心的数学直觉。

Lecture 4 特别强调：你不必一开始就钻进几十篇 SSM 论文，只要先真正理解这个结合律，后面的 Mamba-2、Gated DeltaNet 等结构会突然变得容易看懂很多。Mamba-2 的 SSD 工作也从理论上建立了 attention 类模型与 structured state-space model 之间的联系。

---

# 四、等一下：你是不是偷偷把 softmax 删了？

是的。

而这恰恰是整个问题的关键。

标准 attention 是：

[
\operatorname{softmax}(QK^\top)V.
]

你不能写成：

[
Q\operatorname{softmax}(K^\top V).
]

因为：

[
\operatorname{softmax}
]

是非线性函数。

也就是说：

[
\boxed{
\operatorname{softmax}(QK^\top)V
\neq
Q(K^\top V)
}
]

因此刚才的重新加括号**不是对标准 attention 的等价优化**。

这是 Lecture 4 一个非常重要的区别：

> **Linear form ↔ recurrent form 可以严格等价；但从 full softmax attention 变成 linear attention，本身已经丢掉了一部分东西。**

所以别产生一个错误理解：

> “既然结合律就能 (O(N))，那 Transformer 作者为什么这么多年没想到？”

不是没想到。

真正难的是：

[
\boxed{\text{如何拿掉 }N\times N\text{ interaction，却不显著损失表达能力？}}
]

这也是 linear attention / SSM 研究真正困难的地方。

---

# 五、Linear Attention 最漂亮的地方：它突然变成了 RNN

考虑 causal language model。

第 (t) 个 token 只能看：

[
1,\ldots,t.
]

那么：

[
y_t
===

q_t^\top
\left(
\sum_{i\le t}
k_i v_i^\top
\right).
]

定义：

[
\boxed{
S_t=
\sum_{i\le t}
k_i v_i^\top
}
]

于是：

[
S_t
===

S_{t-1}
+
k_tv_t^\top
]

以及：

[
\boxed{
y_t=q_t^\top S_t
}
]

现在看看它长什么样：

```text
token t
  │
  ├── k_t,v_t ──→ 更新 state S_t
  │
  └── q_t ──────→ 读取 state S_t
                       │
                       ↓
                      y_t
```

这已经完全像 RNN 了。

---

# 六、为什么这个 RNN 形式对推理特别爽？

普通 attention decode 时必须保存过去所有：

[
K_1,\ldots,K_t
]

和：

[
V_1,\ldots,V_t.
]

所以 KV cache 随 context length：

[
O(N)
]

增长。

但刚才这种 recurrent formulation 只保存：

[
\boxed{
S_t\in\mathbb R^{d_k\times d_v}
}
]

context 从：

```text
1K → 10K → 100K → 1M
```

这个 state 的尺寸仍然不变。

于是 autoregressive decoding：

[
\boxed{\text{fixed-size recurrent state}}
]

这是极其诱人的性质。

---

# 七、但 RNN 不是训练很慢吗？

这就是现代这批模型漂亮的地方。

**Inference 时：**

用 recurrence：

[
S_t=f(S_{t-1},x_t)
]

逐 token 算。

**Training 时：**

可以利用对应的 parallel / matrix form，在很多 token 上同时计算。

所以你不是被迫回到 2015 年：

```text
token 1
 ↓
token 2
 ↓
token 3
 ↓
token 4
```

那种 GPU 极其不友好的 serial RNN。

Mamba-2 的核心理论之一正是这种 **state-space / structured matrix duality**：同一个模型可以有适合并行训练的 matrix form 和适合 autoregressive inference 的 recurrent form。([arXiv][4])

可以把它记成：

[
\boxed{
\text{training: parallel form}
\quad\leftrightarrow\quad
\text{inference: recurrent form}
}
]

这是 Lecture 4 前半最值得带走的概念之一。

---

# 八、可是最朴素的 linear state 有一个致命问题：只会一直记

刚才：

[
S_t
===

S_{t-1}+k_tv_t^\top.
]

意味着：

> 每一步只往记忆里加东西。

没有 forget。

想象：

```text
"The capital of France is Paris."

之后 500000 tokens...

"The user explicitly says:
ignore the previous fictional document..."
```

state 里旧信息一直累积。

你会立刻联想到 LSTM：

> 那给它一个 forget gate 不就好了？

对。

这就是 Lecture 4 接下来引入 Mamba-2 的直觉。

---

# 九、从 Linear Attention 到 Mamba-2：给记忆加一个“遗忘门”

Lecture 4 用一种非常直观的方式理解 Mamba-2：

[
\boxed{
S_t
===

\gamma_t S_{t-1}
+
k_tv_t^\top
}
]

这里：

[
0\le\gamma_t\le1.
]

如果：

[
\gamma_t\approx1
]

就是：

> 之前的记忆保留下来。

如果：

[
\gamma_t\approx0
]

就是：

> 忘掉旧 state。

而：

[
\gamma_t
]

由当前输入决定。

这就是非常 LSTM-like 的味道。

Mamba-2 的正式数学来自 Structured State Space Duality，比上面这个教学抽象更完整；但 Lecture 4 希望你先抓住这个思想：

[
\boxed{
\text{linear state}
+
\text{input-dependent decay}
}
]

就已经得到了一个非常强的 sequence model family。SSD 工作进一步给出了 Mamba-2，并报告其 core layer 相较原 Mamba 有显著实现效率提升。([arXiv][4])

---

# 十、Gated DeltaNet：不仅要会“忘”，还应该会“改”

现在再问：

假设 state 里已经记录：

```text
key = "Bubble's city"
value = "Hangzhou"
```

后来输入说：

```text
Bubble moved to Hong Kong.
```

最笨的更新方式：

```text
旧信息还在
+
新信息再写一份
```

理想情况应该是：

> 沿着这个 key 对应的方向，把旧 value 擦掉，再写新的。

这就是 **delta rule** 的直觉。

---

## 用 associative memory 来理解

假设 state (S) 是一个 key→value 映射。

对于：

[
k_t
]

state 当前预测：

[
\hat v_t=S_{t-1}k_t.
]

实际希望写入：

[
v_t.
]

那么 prediction error：

[
e_t=v_t-\hat v_t.
]

Delta update：

[
\boxed{
S_t
===

S_{t-1}
+
\beta_t e_tk_t^\top
}
]

也就是：

[
S_t
===

S_{t-1}
+
\beta_t
(v_t-S_{t-1}k_t)k_t^\top.
]

展开：

[
S_t
===

## S_{t-1}

\beta_tS_{t-1}k_tk_t^\top
+
\beta_tv_tk_t^\top.
]

中间这项：

[
-\beta_tS_{t-1}k_tk_t^\top
]

你可以粗略理解为：

> **把当前 key 方向上的旧记忆擦掉。**

后面的：

[
+\beta_tv_tk_t^\top
]

则是：

> **写入新记忆。**

具体论文采用的矩阵朝向/归一化记号略有不同，但核心就是这种 targeted erase-and-write。Gated DeltaNet 将 gating 的快速遗忘能力和 delta rule 的精确更新结合起来，并设计了适合现代硬件的并行训练算法。([arXiv][5])

---

# 十一、于是你会发现：现代“Attention alternatives”怎么越来越像 LSTM？

这恰恰是 Lecture 4 一个很有意思的观察。

我们最开始说：

> Transformer 好，因为不要 RNN。

结果一路：

```text
Attention
 ↓
Linear Attention
 ↓
Recurrent state
 ↓
forget gate
 ↓
write gate
 ↓
erase / update rule
```

最后：

> 怎么又长得像 LSTM 了？

但现在和传统 LSTM 最大的差别之一是：

[
\boxed{\text{这些 recurrence 往往有对应的高效 parallel form}}
]

所以：

```text
RNN-like inference
+
Transformer-like parallel training
```

可以同时实现。

这也是为什么 Mamba-2、Gated DeltaNet 等不是简单的“历史倒退”。([arXiv][4])

---

# 十二、既然这么好，为什么不把所有 Attention 都换掉？

因为你压缩信息了。

Full attention：

第 (t) 个 token 原则上可以直接读取：

[
k_1,v_1,\ldots,k_t,v_t.
]

也就是所有历史 token 仍然独立存在。

而 recurrent state：

[
S_t
]

必须把：

[
x_1,\ldots,x_t
]

全部压缩进一个**固定尺寸 state**。

所以本质上：

[
\boxed{
\text{full attention}
=====================

\text{保留整个历史}
}
]

而：

[
\boxed{
\text{recurrent model}
======================

\text{把历史压缩成有限状态}
}
]

如果 context 里藏了一把针：

```text
第 127,392 个 token：
secret_key = XQ7F9...
```

过了几十万 token 后突然问：

```text
secret_key 是什么？
```

full attention 理论上还能直接跳回去看。

finite recurrent state 必须保证那个信息一直没有被压缩掉。

所以：

[
\boxed{
\text{efficiency}
\leftrightarrow
\text{information preservation}
}
]

存在真正的 trade-off。

---

# 十三、所以实践里一个非常自然的答案叫 Hybrid Architecture

不要：

```text
100% full attention
```

也不要：

```text
100% linear / recurrent
```

而是：

```text
Linear
Linear
Linear
Full Attention
Linear
Linear
Linear
Full Attention
...
```

Lecture 4 展示的经验趋势就是：少量 full-attention 层与大量 linear/recurrent 层混合时，可以在效率和能力之间得到相当好的折中；而一路走到 pure recurrent architecture，某些长上下文和 QA 类任务往往开始出现更明显损失。Mamba-2 和 Gated DeltaNet 的相关工作也都研究了 hybrid designs。([arXiv][5])

这是一条很值得记住的现代 architecture philosophy：

[
\boxed{\text{昂贵模块少量使用，便宜模块大量使用}}
]

后面你会发现 MoE 也是同一种思想。

---

# 十四、另一条完全不同的路线：我为什么一定要“压缩”历史？

Linear attention 的思路：

> 把所有历史压进一个 state。

Sparse Attention 则说：

> 我不压缩。我还是保留历史 token，但我每次只去找最重要的几个。

这就进入 Lecture 4 讲到的 **DeepSeek Sparse Attention（DSA）**。

DeepSeek-V3.2 的 DSA 核心思想就是先通过一个轻量的 **indexer** 为 query 找出少量重要位置，再只在这些位置上执行更昂贵的 attention。DeepSeek 报告它主要是为了降低长上下文训练和推理成本。([arXiv][6])

---

# 十五、DSA 可以理解成“Attention 版 RAG”

不是数学等价，只是帮助你形成直觉。

普通 attention：

```text
query
  ↓
跟全部 1,000,000 tokens 做昂贵 attention
```

Sparse attention：

```text
query
  ↓
cheap indexer
  ↓
挑出 top-k relevant tokens
  ↓
只对这些 token 做真正 attention
```

例如：

[
N=1,000,000
]

但：

[
k=2048.
]

昂贵 attention 不再直接面对一百万位置，而只面对被选中的少量位置。

---

# 十六、但 Lecture 4 特别提醒：DSA 不是严格意义上的 linear-time attention

为什么？

因为 indexer 得知道：

> 哪些 token 重要？

它还是必须进行很广泛的 query-key matching。

可以粗略写：

[
\text{indexing cost}
\sim
O(N^2d_{\text{index}})
]

但：

[
d_{\text{index}}\ll d_{\text{attention}}
]

而且 indexer 可以采用更低精度、低维表示等手段。

真正昂贵的 full attention 则只在：

[
k\ll N
]

的位置执行。

因此 DSA 的思想不是：

[
O(N^2)\rightarrow O(N)
]

而更像：

[
\boxed{
\text{让 }O(N^2)\text{ 那部分极其便宜，
再把昂贵计算变 sparse}
}
]

这正好再次验证 Lecture 2：

> **不要只盯 Big-O，constant factor 真的非常重要。**

DeepSeek-V3.2 的技术报告把 DSA 描述为用 sparse attention 大幅降低长上下文计算复杂度，同时尽量保持模型质量。([arXiv][6])

---

# 十七、到这里，Attention alternatives 其实形成了三种完全不同的哲学

你可以这样整理：

| 方法               | 核心想法 | 历史信息怎么处理            |
| ---------------- | ---- | ------------------- |
| Full Attention   | 全看   | 所有 token 独立保留       |
| Linear/SSM       | 压缩   | 压进 fixed-size state |
| Sparse Attention | 筛选   | 保留 token，但只访问少数     |

所以以后看到一个新“长上下文架构”，先问：

[
\boxed{\text{它到底是在压缩、筛选，还是纯粹优化执行？}}
]

FlashAttention：

[
\boxed{\text{执行优化}}
]

Mamba/Gated DeltaNet：

[
\boxed{\text{状态压缩}}
]

DSA：

[
\boxed{\text{稀疏筛选}}
]

这比死记几十个模型名有用得多。([arXiv][3])

---

# 十八、现在进入 Lecture 4 后半：Mixture of Experts

接下来我们不碰 Attention 了。

回忆 Lecture 3：

```text
x
│
├─ Attention
│
└─ FFN / SwiGLU
```

Dense Transformer 中，每个 token 都跑：

[
\operatorname{FFN}(x).
]

假设 FFN 有 1B 参数。

每个 token：

```text
token A → 这 1B 参数
token B → 这 1B 参数
token C → 这 1B 参数
...
```

MoE 问：

> 为什么所有 token 必须使用同一个 FFN？

---

# 十九、最简单的 MoE：复制很多 FFN，但每次只选一个

假设原来：

```text
FFN
```

现在变成：

```text
Expert 1
Expert 2
Expert 3
Expert 4
```

再加 router：

```text
          ┌─ Expert 1
token ─Router─ Expert 2
          ├─ Expert 3
          └─ Expert 4
```

对于某个 token：

```text
router → Expert 3
```

于是只计算：

[
E_3(x).
]

现在有 4 个 FFN 的参数：

[
\boxed{\text{total parameters}=4P}
]

但这个 token 只跑一个：

[
\boxed{\text{active expert parameters}=P}
]

这就是 MoE 最重要的一句话：

[
\boxed{
\text{增加模型参数容量，而不同比例增加每 token FLOPs}
}
]

Switch Transformer 的核心目标正是 sparse activation：不同输入选择不同参数，使模型总参数规模可以大幅增加，而单个样本只激活其中一小部分。([arXiv][7])

---

# 二十、所以看 MoE 模型千万别只看“总参数”

假设模型写：

```text
Total parameters: 200B
Active parameters: 20B
```

它不是一个普通的 200B dense model。

也不能简单把它叫 20B。

两件事分别代表：

[
\boxed{
200B
====

\text{需要存储的模型容量}
}
]

而：

[
\boxed{
20B
\approx
\text{每 token 实际参与计算的参数规模}
}
]

比如 DeepSeek-V2 官方报告：

[
236B\text{ total}
]

但每 token 激活：

[
21B.
]

DeepSeek-V3 则报告：

[
671B\text{ total},
\qquad
37B\text{ activated/token}.
]

所以 MoE 同时造成一个很有意思的分离：

[
\boxed{
\text{memory capacity}
\neq
\text{compute per token}
}
]

([arXiv][8])

---

# 二十一、Router 到底有多神秘？

其实通常一点都不神秘。

假设 hidden state：

[
x\in\mathbb R^d.
]

有 (E) 个 experts。

router 就可以是一层：

[
r=W_rx
]

得到：

[
r\in\mathbb R^E.
]

也就是说：

```text
x
 ↓
Linear(d → E)
 ↓
[r1,r2,...,rE]
```

然后：

[
p=\operatorname{softmax}(r)
]

再取：

[
\operatorname{TopK}(p).
]

假设：

[
E=64,\quad K=2.
]

那么这个 token 可能选择：

```text
Expert 7
Expert 41
```

最后：

[
\boxed{
y
=

p_7E_7(x)
+
p_{41}E_{41}(x)
}
]

实际实现会对选中 expert 的权重做相应归一化。

---

# 二十二、这叫 Token Choice

存在两个方向。

### Token Choice

token 说：

> 我最喜欢 Expert 7 和 Expert 41。

```text
token → experts
```

### Expert Choice

expert 说：

> 这一批 token 里，我最想处理这些。

```text
expert → tokens
```

Lecture 4 指出，现代大规模 MoE 最常见的 recipe 是 **token-choice top-k routing**；Switch Transformer 的简化版本甚至采用 top-1 routing。([arXiv][7])

---

# 二十三、为什么这个问题看起来其实有点像 RL / Bandit？

因为 router 做了：

[
\operatorname{TopK}.
]

例如：

```text
Expert 1 score = 0.4
Expert 2 score = 0.3
Expert 3 score = 0.2
Expert 4 score = 0.1
```

如果：

[
K=1
]

只运行：

```text
Expert 1
```

那么你并不知道：

> 如果当时选 Expert 2 会不会更好？

这非常像：

[
\boxed{\text{counterfactual feedback 不可见}}
]

或者 multi-armed bandit：

```text
选一个 arm
↓
只观察那个 arm 的 reward
```

而且 TopK 本身是离散操作。

所以初看 MoE，你可能会觉得：

> 这路由器不得用 RL？

Lecture 4 专门讨论了这个方向，但结论非常“深度学习”：

> 实践中反而通常不用复杂 RL router，一堆相对简单的 heuristic + auxiliary loss 就能工作得很好。

这也是这堂课很有意思的一部分。([YouTube][2])

---

# 二十四、MoE 最大灾难：Expert Collapse

假设一开始：

```text
Expert 1
```

恰好比其他 expert 好一点。

于是 router：

```text
更多 token → Expert 1
```

Expert 1 获得更多 training signal：

```text
Expert 1 → 学得更快
```

然后：

```text
Expert 1 更好
 ↓
更多 token 选择它
 ↓
更多 gradient
 ↓
Expert 1 更强
 ↓
更多 token...
```

形成：

[
\boxed{\text{rich get richer}}
]

最终：

```text
Expert 1: ███████████████████
Expert 2:
Expert 3:
Expert 4:
...
```

你买了 64 个 experts，却只用 2 个。

那剩下几十个专家等于白存了。

这就是：

[
\boxed{\text{expert collapse / starvation}}
]

Switch Transformer 之类的工作因此非常重视 load balancing。([arXiv][7])

---

# 二十五、Load Balancing Loss 是 Lecture 4 最值得真正理解的 MoE 公式

Switch Transformer 使用一种形式：

[
\boxed{
L_{\text{balance}}
==================

\alpha E
\sum_{i=1}^{E}
f_iP_i
}
]

其中：

[
f_i
===

\text{真正被发送到 expert i 的 token 比例}
]

而：

[
P_i
===

\text{router 分给 expert i 的平均 probability mass}.
]

如果完美均衡：

[
f_i=P_i=\frac1E.
]

于是：

[
\sum_i f_iP_i
=============

# E\frac1{E^2}

\frac1E.
]

乘上 (E)：

[
L_{\text{balance}}\approx\alpha.
]

但假如所有 token 都塌缩到 expert 1：

[
f_1=P_1=1
]

则：

[
L_{\text{balance}}
==================

\alpha E.
]

随着 expert 数增加，惩罚大得多。这个辅助目标正是为了避免 router 把所有 token 推给少数 experts。([arXiv][7])

---

# 二十六、比背公式更重要的是看它的梯度

对：

[
P_i
]

求导：

[
\frac{\partial L}{\partial P_i}
===============================

\alpha E f_i.
]

于是：

如果 expert (i) 已经收到很多 token：

[
f_i\uparrow
]

那么：

[
\frac{\partial L}{\partial P_i}\uparrow.
]

优化时就会更强地推动：

[
P_i\downarrow.
]

换句话说：

> **越热门的 expert，load-balancing loss 越努力把 router probability 从它身上赶走。**

这个理解比背：

[
E\sum f_iP_i
]

有价值得多。

因为你以后看到新的 balancing objective，第一件事情就应该做：

[
\boxed{\text{别只看公式，先问 gradient 在推动什么？}}
]

---

# 二十七、现在 DeepSeek 对 MoE 做的一个重要改造就很好理解了：Fine-Grained Experts

传统做法：

```text
Expert 1 = 很大的 FFN
Expert 2 = 很大的 FFN
...
```

DeepSeekMoE 的想法之一：

> 把大 expert 切成更多、更小的 experts。

例如原来：

```text
8 experts
select 2
```

可以改成更细粒度：

```text
64 small experts
select 16
```

并调整尺寸，使激活计算预算保持相近。

为什么可能更好？

因为组合空间一下子大了。

原来：

[
\binom82=28
]

种 expert combination。

现在：

[
\binom{64}{16}
]

组合空间巨大。

于是不同 token 可以获得更加精细的 expert mixture。DeepSeekMoE 的原始工作明确提出了 **fine-grained expert segmentation**，在保持计算成本的同时增加可组合的细粒度 experts。([arXiv][9])

---

# 二十八、Shared Expert 又是在解决什么？

想象有一些东西：

```text
基本语言建模
标点处理
常见句法
通用 feature transformation
```

几乎每个 token 都需要。

如果每个 routed expert 都自己重新学习：

```text
Expert 1: 学一次通用能力
Expert 2: 又学一次
Expert 3: 又学一次
...
```

很浪费。

所以 DeepSeekMoE：

```text
                 ┌→ Routed Expert 7
token ───────────┼→ Routed Expert 31
  │
  └──────────────→ Shared Expert
```

Shared Expert：

[
\boxed{\text{永远激活}}
]

Routed Experts：

[
\boxed{\text{条件激活}}
]

希望形成：

```text
Shared Expert
→ 通用知识

Routed Experts
→ 更专门的知识
```

DeepSeekMoE 原论文将这一策略称为 **shared expert isolation**，目标正是让 shared experts 捕获 common knowledge，并减少 routed experts 之间的冗余。([arXiv][9])

---

# 二十九、这下你应该真正看懂 DeepSeekMoE 了

核心不是什么神秘“专家 AI”。

它实际上就是：

```text
                  shared FFN
                 ↗
hidden state → router → top-k small FFNs
                 ↘
                 weighted sum
```

本质仍然：

[
\boxed{\text{FFN}}
]

只是 FFN 变成了**条件计算图**。

所以 Tatsu 在 Lecture 4 给出的一个非常好的 mental model 就是：

> MoE 可以先理解成一种更高效的 MLP。

它没有把 Transformer 的宏观骨架推翻。

仍然：

```text
Attention
   ↓
MoE
```

只是把：

```text
Dense SwiGLU
```

换成：

```text
Sparse SwiGLU experts
```

([YouTube][2])

---

# 三十、MoE 绝对不是“免费参数”

这是最容易被营销数字误导的地方。

假设：

[
100B\text{ total}
]

但：

[
10B\text{ active}.
]

你确实可能只支付接近较小 active model 的 FFN FLOPs。

但那 100B 参数：

[
\boxed{\text{仍然必须存在哪里}}
]

所以：

```text
compute cost ↓
```

不意味着：

```text
memory cost ↓ 到 active parameter 那么低
```

而且 router 可能把 token 发到不同 GPU：

```text
GPU 0:
Expert 0,1

GPU 1:
Expert 2,3

GPU 2:
Expert 4,5
```

如果当前 token 被路由到 Expert 5：

```text
GPU 0 activation
        │
        │ network
        ↓
GPU 2 Expert 5
```

于是又产生：

[
\boxed{\text{communication}}
]

Switch Transformer 就把 communication cost 和 training instability 列为稀疏 MoE 的主要实际难点；Lecture 4 也因此把 expert parallelism 作为 MoE 的重要系统问题。([arXiv][7])

---

# 三十一、于是 MoE 又和 Lecture 2 连起来了

Dense model：

```text
参数少一些
→ 每次都算全部
→ dense GEMM
```

MoE：

```text
参数超级多
→ 每次只算少数
→ sparse / routed computation
→ communication
```

因此不能只比较：

[
\text{FLOPs}.
]

还必须算：

[
\boxed{
\text{memory}
+
\text{bandwidth}
+
\text{communication}
+
\text{load balance}
+
\text{kernel efficiency}
}
]

这就是 CS336 很核心的一种风格：

> Architecture 和 Systems 根本不是两门独立学科。

一个架构如果理论上 FLOPs 少 50%，但它：

```text
产生大量 tiny GEMMs
+
大量 all-to-all communication
+
GPU load imbalance
```

实际可能并不好跑。

---

# 三十二、为什么 Expert Parallelism 又成为新的并行维度？

Dense model 可以：

```text
Data Parallel
Tensor Parallel
Pipeline Parallel
...
```

MoE 多出来：

[
\boxed{\text{Expert Parallelism}}
]

例如：

```text
GPU 0: Expert 0–7
GPU 1: Expert 8–15
GPU 2: Expert 16–23
GPU 3: Expert 24–31
```

router 完成之后：

```text
tokens
 ↓
all-to-all
 ↓
对应 expert 所在 GPU
 ↓
expert FFN
 ↓
all-to-all
 ↓
原位置
```

这种天然的 expert 切分为大模型再提供了一条并行轴，但代价就是 collective communication。Lecture 4 明确把这个 trade-off 铺垫给后面的 Parallelism lectures。([YouTube][2])

---

# 三十三、还有一个很实际的问题：每个 Expert 收到的 token 数不一样

假设：

```text
GPU0 / Expert1: 2000 tokens
GPU1 / Expert2: 100 tokens
GPU2 / Expert3: 130 tokens
GPU3 / Expert4: 90 tokens
```

那整个 step 的速度由谁决定？

当然是：

```text
Expert1 / GPU0
```

其他 GPU：

```text
算完了
↓
等着
↓
等着
↓
等着
```

所以 load balancing 不仅是：

> “所有 expert 都学习到东西。”

还是：

[
\boxed{\text{systems utilization 问题}}
]

Lecture 4 因此还讨论了 **device-level balancing**：有时不仅要求 experts 比较均衡，还希望不同设备上的总 token / communication workload 比较均衡。DeepSeek-V2 本身就是一个非常典型的 architecture-systems co-design 案例。([arXiv][8])

---

# 三十四、Router 自己还有数值稳定性问题

你应该还记得 Lecture 3：

> softmax 是数值稳定性的危险区。

MoE 又增加一个：

```text
router logits
 ↓
softmax
 ↓
top-k
```

因此 MoE router 也是敏感区域。

实践中会看到类似：

```text
router 用更高精度
router z-loss
```

等技巧。

Switch Transformer 的工作专门处理了 MoE 的 training instability，并使稀疏模型能够更稳定地使用较低精度训练；Lecture 4 也重新把上一讲的 z-loss 概念连接到了 router stability。([arXiv][7])

这又体现一个 CS336 很喜欢的思维：

```text
一个小小的 softmax
```

看起来只是：

```python
torch.softmax(...)
```

但大规模训练时：

[
\boxed{\text{它可能成为数值稳定性的关键边界}}
]

---

# 三十五、DeepSeek-V3 为什么又开始减少 auxiliary balancing loss？

传统：

[
L
=

L_{\text{LM}}
+
\lambda L_{\text{balance}}.
]

问题是：

> balancing 只是为了让系统跑得好，它未必和语言建模目标完全一致。

如果：

[
\lambda
]

太大，模型可能为了“平均分配专家”而牺牲真正有意义的 specialization。

所以 DeepSeek-V3 做了一个很有意思的改进：使用动态 expert-selection bias 来实现主要的 load balancing，而不是完全依赖传统 auxiliary loss；同时仍保留很弱的辅助 balancing 项来避免极端失衡。其技术报告把这称为 **auxiliary-loss-free load balancing strategy**。([arXiv][10])

这背后的设计原则值得记：

[
\boxed{
\text{最好让系统约束少污染模型真正的学习目标}
}
]

---

# 三十六、MoE Fine-tuning 为什么反而容易麻烦？

假设 dense 7B：

[
7B\text{ parameters}.
]

MoE：

[
200B\text{ total},
\quad20B\text{ active}.
]

推理时你很高兴：

> 每 token 不需要算 200B。

但 fine-tuning 时模型实际上有非常大的**总容量**。

而你下游数据可能只有：

```text
10K
100K
```

examples。

就更容易出现：

[
\boxed{\text{overfitting}}
]

Lecture 4 因此还讨论了只微调 attention、non-MoE 部分等策略，以及“大量数据自然能够缓解问题”的朴素答案。([YouTube][2])

这也是为什么：

[
\boxed{\text{active parameter 很小}}
]

绝不等价于：

[
\boxed{\text{模型统计容量真的很小}}
]

---

# 三十七、Upcycling 是个非常漂亮的 MoE 实验思想

假设你已经辛辛苦苦训练好了 dense：

```text
Dense FFN
```

是不是只能扔掉，重新训练 MoE？

不一定。

可以复制：

```text
Dense FFN
 ├── Expert 1
 ├── Expert 2
 ├── Expert 3
 └── Expert 4
```

初始时：

[
E_1=E_2=E_3=E_4.
]

然后随机初始化 router。

继续训练之后：

不同 token 被分给不同 expert：

```text
Expert 1 → 梯度 A
Expert 2 → 梯度 B
Expert 3 → 梯度 C
```

慢慢：

[
E_1\neq E_2\neq E_3.
]

expert 自动分化。

这叫：

[
\boxed{\text{MoE upcycling}}
]

Lecture 4 把它作为历史上很漂亮的一条“从 dense checkpoint 变 MoE”的路线来介绍，同时指出如今大规模 hero run 更常直接从 MoE 开始训练。([YouTube][2])

---

# 三十八、最后 Tatsu 为什么花时间讲 DeepSeek V1 → V2 → V3？

因为这是一个特别好的 **architecture evolution case study**。

你可以粗略整理成：

### DeepSeekMoE

核心：

```text
fine-grained routed experts
+
shared experts
+
top-k routing
+
load balancing
```

([arXiv][9])

### DeepSeek-V2

继续扩大 MoE，同时加入：

[
\boxed{\text{MLA}}
]

Multi-head Latent Attention。

它解决另一个完全不同的问题：

[
\boxed{\text{KV cache 太大}}
]

DeepSeek-V2 报告通过 low-rank latent representation 压缩 KV cache；官方报告给出的 236B total / 21B active 模型也同时使用 DeepSeekMoE 和 MLA。([arXiv][8])

### DeepSeek-V3

继续使用：

```text
DeepSeekMoE
+
MLA
```

并加入：

```text
auxiliary-loss-free load balancing
+
MTP
```

Multi-Token Prediction。

V3 官方报告给出的规模是：

[
671B\text{ total},
\qquad37B\text{ active/token}.
]

([arXiv][10])

---

# 三十九、MLA 可以先只抓住一个直觉

普通：

```text
hidden
  ↓
K
V
  ↓
KV cache
```

MLA：

```text
hidden
  ↓
small latent c
  ↓
K / V information
```

推理时重点缓存：

[
\boxed{c}
]

而不是完整的大 K/V 表示。

于是：

[
\boxed{\text{KV cache memory ↓}}
]

DeepSeek-V2 报告 MLA 使用 low-rank key-value joint compression，并给出了显著 KV-cache reduction。([arXiv][8])

你现在应该发现一个非常漂亮的趋势：

```text
Linear Attention
→ 压缩整个 history

MLA
→ 压缩 KV representation

DSA
→ 筛掉大部分 history

MoE
→ 筛掉大部分 FFN parameters
```

**整个 Lecture 4 都在做“别把所有东西全算了”。**

---

# 四十、所以 Lecture 2、3、4 终于形成了一条完整链条

我会这样给你串：

## Lecture 2

问：

[
\boxed{\text{计算到底贵在哪里？}}
]

得到：

```text
FLOPs
Memory
Bandwidth
Arithmetic intensity
```

---

## Lecture 3

问：

[
\boxed{\text{标准现代 Transformer 应该怎么造？}}
]

得到：

```text
RMSNorm
RoPE
Attention
SwiGLU
Residual
...
```

---

## Lecture 4

问：

[
\boxed{\text{这个标准 Transformer 还有哪些东西太 dense？}}
]

得到：

```text
Attention
│
├── FlashAttention：同样的数学，更好的执行
├── Linear / SSM：把 history 压成 state
├── Hybrid：少量 full attention
└── Sparse Attention：只选择少数 token

FFN
│
└── MoE
     ├── router
     ├── top-k experts
     ├── shared experts
     ├── fine-grained experts
     ├── load balancing
     └── expert parallelism
```

这就是前三讲之后最重要的一次知识升级。([Stanford CS336][1])

---

# 四十一、对你做 A1 来说，Lecture 4 哪些必须掌握？

这里要特别区分。

**如果目标只是完成标准 A1：**

Lecture 4 不是实现 baseline Transformer 的核心必需品。A1 官方要求是实现 tokenizer、标准 Transformer architecture、optimizer 并训练一个 minimal LM；并不要求你实现 Mamba、DSA 或 MoE。([Stanford CS336][1])

所以现在不要突然跑去：

```text
先写 Gated DeltaNet！
先写 DeepSeekMoE！
```

反而把：

```text
MHA
RoPE
RMSNorm
SwiGLU
TransformerBlock
AdamW
training loop
```

搞乱。

---

但如果你的目标是把 A1 baseline 做完之后，再自己造一些 **mini-DeepSeek / mini-Qwen / 现代 architecture variants**，Lecture 4 就一下子非常重要。

我会建议你把扩展实验分成三级：

### Level 1：很适合自己改

```text
MHA → GQA
普通 FFN → MoE
Dense FFN → shared + routed experts
```

这些比较容易控制变量。

### Level 2：开始真正有研究味道

```text
Full Attention
→ hybrid Full + Linear Attention

Full Attention
→ Gated DeltaNet hybrid
```

需要额外 kernel / scan / recurrent implementation 思维。

### Level 3：系统复杂度明显上升

```text
MLA
DSA
Expert Parallel
distributed MoE
```

这已经会和 Lecture 5–8 的 GPU、kernel、parallelism 强烈耦合。

---

# 四十二、我最希望你真正做会这 8 道题

### 1. 为什么

[
(QK^\top)V
]

可以变成：

[
Q(K^\top V)
]

并从 (O(N^2)) 变成对 (N) 线性？

你必须自己写 shape 和复杂度。

---

### 2. 为什么这个技巧不能直接用于标准 softmax attention？

必须回答：

[
\operatorname{softmax}
]

破坏了结合律重新排序。

---

### 3. 推导 causal linear attention 的 recurrence

从：

[
y_t=
q_t^\top
\sum_{i\le t}k_iv_i^\top
]

推出：

[
S_t=S_{t-1}+k_tv_t^\top
]

和：

[
y_t=q_t^\top S_t.
]

---

### 4. Linear/SSM 为什么有可能丢失 full attention 的能力？

不能只说：

> “表达能力低。”

要说：

[
\boxed{\text{整个历史必须被压缩进 fixed-size state}}
]

而 full attention 保留所有 token。

---

### 5. 100 experts、top-2，每个 expert 100M 参数

expert 总参数：

[
100\times100M=10B.
]

每 token 激活 expert 参数：

[
2\times100M=200M.
]

为什么不能直接说：

> “这是一个 200M 模型？”

因为：

[
\text{storage/statistical capacity}=10B
]

而：

[
\text{active compute}=200M.
]

---

### 6. 为什么 MoE 会 expert collapse？

必须说出：

[
\boxed{
\text{selected}
\rightarrow
\text{more gradient}
\rightarrow
\text{better}
\rightarrow
\text{more likely selected}
}
]

这个 positive feedback loop。

---

### 7. 给你

[
L_{\text{bal}}
==============

\alpha E\sum_i f_iP_i
]

解释它为什么能负反馈热门 expert。

最好自己求：

[
\frac{\partial L}{\partial P_i}.
]

---

### 8. MoE 为什么 theoretical FLOPs 很漂亮，却可能实际速度没那么漂亮？

必须想到：

```text
all-to-all communication
load imbalance
tiny / irregular GEMMs
memory for all parameters
router overhead
```

这道题就是 Lecture 2 + Lecture 4 的合体。

---

# 最后给 Lecture 4 压成两个公式

如果让我在黑板上只留两个东西，我会留：

### Attention alternatives

[
\boxed{
(QK^\top)V
\quad\Rightarrow\quad
Q(K^\top V)
\quad\Rightarrow\quad
S_t
}
]

代表：

[
\boxed{\text{all-to-all interaction → compressed recurrent state}}
]

### MoE

[
\boxed{
y(x)
====

\sum_{i\in\operatorname{TopK}(r(x))}
p_i(x)E_i(x)
}
]

代表：

[
\boxed{\text{all parameters → conditionally selected parameters}}
]

所以整堂 Lecture 4 最深的一句话其实可以是：

[
\boxed{
\textbf{不要问模型一共有多少信息/参数；
要问一次计算究竟需要访问其中多少。}
}
]

这正好把 CS336 的 **architecture、FLOPs、memory、inference、parallelism** 开始真正揉到了一起。下一讲 Lecture 5 转向 GPU/TPU 时，你会发现 Tatsu 突然开始讲硬件并不突兀：**Lecture 4 已经不断在问“这种架构到底能不能在真实硬件上跑得划算？”**
