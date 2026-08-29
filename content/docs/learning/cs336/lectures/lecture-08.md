---
title: "L08 · Distributed Systems"
weight: 8
date: 2026-08-28
updated: 2026-08-28
course: "CS336"
topics: ["CS336", "parallelism", "distributed-training"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture8/
---

2026 官方课程表里，Lecture 8 是 4 月 22 日 Tatsunori Hashimoto 主讲的第二讲 **Parallelism**；官方材料是 `lecture_08.pdf`。相比 Lecture 7 用代码建立 collective、DP/TP/PP 的基本概念，Lecture 8 是一份约 73 页的系统化课件，真正讨论：**ZeRO/FSDP 为什么成立、Pipeline/Tensor/Sequence/Context/Expert Parallelism 各自切什么、通信成本怎么算，以及真实的 Llama 3 / DeepSeek 等训练为什么必须把它们组合起来。**

如果让我先用一句话概括 Lecture 8：

[
\boxed{
\textbf{大模型训练不是“把模型平均分到很多 GPU”，
而是在 Compute、Memory、Communication 三者之间设计一个最合适的分解。}
}
]

---

# 0. Lecture 7 和 Lecture 8 到底有什么区别？

Lecture 7 更像：

> 给你一盒乐高积木。

你学了：

[
\text{AllReduce},\quad
\text{AllGather},\quad
\text{ReduceScatter},\quad
\text{AllToAll}
]

以及：

[
\text{DP},\quad
\text{TP},\quad
\text{PP}.
]

Lecture 8 则问：

> **拿这些积木，真要训练一个 100B、400B、1T 模型，到底应该怎么搭？**

整堂课的结构大致是：

```text
硬件网络/topology
        ↓
DDP → ZeRO-1 → ZeRO-2 → ZeRO-3/FSDP
        ↓
Pipeline Parallelism
        ↓
Tensor Parallelism
        ↓
Activation Memory
        ↓
Sequence Parallelism
        ↓
Expert Parallelism
        ↓
Context Parallelism / Ring Attention
        ↓
3D / 4D Parallelism
        ↓
Llama / DeepSeek / Mixtral 等真实训练配置
```

官方 Lecture 8 的三个目标也正是：理解巨型模型训练的系统复杂性、掌握不同 parallelization paradigms、理解真实 large-scale training run 是怎样组织的。([Yulong Ge][2])

---

# 一、这一讲最重要的第一个升级：数据中心本身就是“计算机”

Lecture 5 时你的世界是：

[
\boxed{\text{一张 GPU}}
]

里面有：

```text
Tensor Core
↕
register
↕
shared memory
↕
HBM
```

Lecture 8 把 memory hierarchy 再往外延伸：

```text
GPU Core
   ↓
HBM
   ↓
NVLink / NVSwitch
   ↓
InfiniBand
   ↓
跨机网络
```

所以现在“load 一份 tensor”可能不再是：

[
HBM\rightarrow SM
]

而可能是：

[
\boxed{
\text{GPU 37 的 HBM}
\rightarrow
\text{network}
\rightarrow
\text{GPU 248 的 HBM}
}
]

这比单 GPU 内的数据移动贵得多。

因此你应该把 Lecture 5 的原则：

[
\boxed{\text{尽量减少 HBM traffic}}
]

升级成：

[
\boxed{\text{尽量减少跨设备 communication}}
]

官方课件特别强调 NVLink/NVSwitch 和跨节点 InfiniBand 的带宽存在明显层级，所以后面“TP 为什么应该放机内、PP/DP 为什么可以跨机”不是经验玄学，而直接来自 topology。([Yulong Ge][2])

---

# 二、为什么网络拓扑会直接决定模型架构怎么切？

想象两种通信。

第一种：

```text
GPU0 ↔ GPU1
GPU0 ↔ GPU2
GPU0 ↔ GPU3
...
```

需要大量随机的 all-to-all communication。

另一种：

```text
GPU0 → GPU1 → GPU2 → GPU3
```

只要相邻传数据。

这两种 workload 喜欢的网络完全不同。

Lecture 8 特别比较 TPU 的 mesh/torus 网络和 GPU 的 switch/all-to-all 风格网络：规整的 collective 可以非常适合 mesh；MoE 那种 token 随机路由到 experts 的 all-to-all 则更依赖高 bisection bandwidth 的交换网络。换句话说：

[
\boxed{
\text{不存在脱离 communication pattern 的“最好网络”。}
}
]

([Yulong Ge][2])

这个思想后面特别重要。

因为：

[
\text{TP}\rightarrow\text{高频 collective}
]

[
\text{PP}\rightarrow\text{较少 point-to-point}
]

[
\text{EP}\rightarrow\text{All-to-All}
]

不同并行方式天然要求不同网络。

---

# 三、Lecture 8 再讲 All-Reduce，是为了让你算“通信账”

Lecture 7 已经告诉你：

[
\text{AllReduce}
================

\text{ReduceScatter}
+
\text{AllGather}.
]

Lecture 8 更进一步问：

> 到底搬多少数据？

假设每个 GPU 上有长度：

[
M
]

的 tensor。

有：

[
N
]

张 GPU。

Ring Reduce-Scatter 中，每张 GPU 大约发送：

[
\frac{N-1}{N}M.
]

All-Gather 再来一次：

[
\frac{N-1}{N}M.
]

所以总通信量约：

[
\boxed{
2\frac{N-1}{N}M
}
]

当：

[
N\gg1
]

时：

[
\boxed{\approx2M}.
]

这条结论非常重要，因为后面 DDP、ZeRO 的通信账几乎全部围绕：

[
\boxed{M,\ 2M,\ 3M}
]

展开。([Yulong Ge][2])

---

# 四、现在重新算一次训练显存：为什么 DDP 根本救不了“大模型装不下”？

Lecture 8 使用一种典型 mixed-precision Adam accounting。

每个 parameter 大约需要：

| 状态                     |               大致字节 |
| ---------------------- | -----------------: |
| FP16/BF16 parameter    |                  2 |
| FP16 gradient          |                  2 |
| FP32 master parameter  |                  4 |
| Adam first moment (m)  |                  4 |
| Adam second moment (v) |                  4 |
| **总计**                 | **16 B/parameter** |

所以：

[
\boxed{M_{\rm train}\approx16N_{\rm params}\text{ bytes}}
]

这是 Lecture 8 采用的账法。([Yulong Ge][2])

于是 7B：

[
7\times10^9\times16
===================

112GB.
]

还**完全没算 activation**。

所以 80GB GPU：

[
\boxed{\text{7B 都已经可能放不下传统 mixed-precision Adam training state}}
]

175B：

[
175B\times16
============

2.8TB.
]

---

# 五、那我有 64 张 GPU，DDP 不就好了？

不是。

DDP：

```text
GPU0: 完整 112GB
GPU1: 完整 112GB
GPU2: 完整 112GB
...
```

而不是：

```text
112GB / 64
```

因为 Data Parallelism 只 shard：

[
\boxed{\text{batch}}
]

并没有 shard：

[
\text{parameters},
\text{gradients},
\text{optimizer states}.
]

所以 DDP 可以让：

[
\boxed{\text{throughput}\uparrow}
]

但：

[
\boxed{\text{model-state memory per GPU 基本不下降}}
]

这就是 ZeRO 出现的原因。([Yulong Ge][2])

---

# 六、ZeRO 是 Lecture 8 第一大核心

ZeRO 的名字：

[
\boxed{\text{Zero Redundancy Optimizer}}
]

它问了一个极其朴素的问题：

> DDP 中，每张 GPU 为什么必须保存完全一样的 optimizer state？

例如 Adam：

```text
GPU0:
m 全部
v 全部

GPU1:
m 全部
v 全部

GPU2:
m 全部
v 全部
```

但每次更新 parameter：

[
\theta_i
]

其实只需要：

[
m_i,v_i.
]

那完全可以：

```text
GPU0 管 parameter shard 0 对应的 optimizer state
GPU1 管 shard 1
GPU2 管 shard 2
...
```

这就是：

[
\boxed{\text{ZeRO Stage 1}}
]

---

# 七、ZeRO-1：先切 optimizer states

原来：

[
m,v,\text{master weights}
]

每张 GPU 都有完整副本。

现在：

[
\boxed{\text{optimizer states shard across DP ranks}}
]

假设：

[
P=8.
]

optimizer state memory 从：

[
12N
]

bytes/parameter-equivalent scale，

变成：

[
\frac{12N}{8}.
]

但是 parameter 和 gradient 仍然 full replicated。

于是每 rank memory 大约变成：

[
\boxed{
4N+\frac{12N}{P}
}
]

这里的 (4N) 对应计算参数 + gradient 的低精度副本。

关键在于：optimizer update 本身也可以利用刚才：

[
\boxed{\text{AllReduce = ReduceScatter + AllGather}}
]

这个结构。

Reduce-Scatter 后：

```text
GPU0 得到 gradient shard 0
GPU1 得到 gradient shard 1
...
```

每 GPU 更新自己的 parameter shard。

然后 All-Gather 更新后的 parameter shards。

所以：

> **通信并没有因为 optimizer state sharding 而本质增加很多，却白赚了巨量显存。**

这就是 ZeRO-1 特别漂亮的地方。([Yulong Ge][2])

---

# 八、ZeRO-2：gradient 也没必要复制

Stage 1 后：

```text
optimizer states: sharded
gradient: replicated
parameter: replicated
```

那再问：

> 每张 GPU 为什么都要永久保存完整 gradient？

Reduce-Scatter 得到：

```text
GPU0 → gradient shard 0
GPU1 → gradient shard 1
...
```

直接留这个 shard 不就好了？

于是：

[
\boxed{\text{ZeRO Stage 2 = optimizer state + gradient sharding}}
]

而且 gradient 可以 backward 一边产生、一边 reduce-scatter，一边释放。

这又带来两个好处：

[
\boxed{\text{gradient peak memory}\downarrow}
]

和：

[
\boxed{\text{communication/computation overlap}}
]

Lecture 8 把这一点和现代 gradient bucketing/FSDP 的 overlap 联系起来。([Yulong Ge][2])

---

# 九、ZeRO-3：那 parameters 为什么还复制？

现在：

```text
optimizer: sharded
gradient: sharded
parameter: full
```

最后自然问：

> parameter 为什么还要全复制？

于是：

[
\boxed{\text{ZeRO Stage 3 = parameters 也 shard}}
]

最终：

```text
GPU0:
θ shard0
g shard0
optimizer shard0

GPU1:
θ shard1
g shard1
optimizer shard1
...
```

于是 steady-state training state：

[
\boxed{
M_{\rm rank}
\sim
\frac{16N}{P}
}
]

真正实现：

[
\boxed{\text{linear memory scaling}}
]

也就是说：

[
P\rightarrow2P
]

理论上可容纳的 parameter state 大约也：

[
\rightarrow2\times.
]

Lecture 8 直接把 PyTorch FSDP 与 ZeRO Stage 3 联系起来。([Yulong Ge][2])

---

# 十、但是突然出现一个问题：parameter 不完整，怎么做 Linear？

假设：

[
W
]

被 8 张 GPU 分走。

GPU 0 只有：

[
W_0.
]

但传统 forward：

[
XW
]

需要完整：

[
W.
]

怎么办？

答案：

[
\boxed{\text{All-Gather}}
]

FSDP 的核心模式可以理解为：

```text
平时：

GPU0: W0
GPU1: W1
GPU2: W2
GPU3: W3

计算某一层之前：

       All-Gather

每 GPU 暂时：
W0 W1 W2 W3

       ↓
     Forward

计算完：
释放 full W
重新只留 shard
```

这就是 FSDP 真正的含义：

[
\boxed{\text{Fully Sharded Data Parallel}}
]

不是“模型永远不完整”，而是：

> **不需要的时候保持 sharded；计算某层时 temporarily materialize。**

---

# 十一、Backward 怎么办？

Forward：

[
\boxed{\text{AllGather parameter}}
]

Backward 时又需要 parameter 来计算：

[
\frac{\partial L}{\partial x}.
]

所以又：

[
\boxed{\text{AllGather}}
]

gradient 算出来以后：

[
\boxed{\text{ReduceScatter gradient}}
]

因此最朴素 ZeRO-3/FSDP 每 step 通信量近似：

[
M_{\rm forward\ AG}
+
M_{\rm backward\ AG}
+
M_{\rm gradient\ RS}.
]

也就是：

[
\boxed{\approx3M}.
]

而 DDP AllReduce 大约：

[
\boxed{\approx2M}.
]

所以：

[
\boxed{
\text{FSDP 用更多 communication 换更少 memory}
}
]

这是 Lecture 8 必须真正理解的 trade-off。([Yulong Ge][2])

---

# 十二、那 FSDP 为什么实际还能很快？

因为你不必：

```text
AllGather layer1
wait
compute layer1
AllGather layer2
wait
compute layer2
...
```

可以：

```text
compute layer1
██████████

同时 prefetch layer2
      ███████

compute layer2
          ██████████

同时 prefetch layer3
                ███████
```

于是：

[
\boxed{\text{communication hidden behind computation}}
]

理想情况下：

[
T_{\rm step}
]

更接近：

[
\max(T_{\rm compute},T_{\rm communication})
]

而不是：

[
T_{\rm compute}+T_{\rm communication}.
]

这就是：

[
\boxed{\text{communication/computation overlap}}
]

工业 FSDP/ZeRO-3 的巨大工程价值就在这里。([Yulong Ge][2])

---

# 十三、但是这也解释了为什么 FSDP 不会无限 scale

如果每层 compute 很多：

```text
compute █████████████████
comm       ███
```

通信可以藏住。

但是 GPU 越加越多，每 GPU 负责的数据越来越少：

```text
compute ███
comm    ███████
```

这时候 communication 藏不住。

于是 FSDP 从：

[
\boxed{\text{compute-bound}}
]

逐渐变成：

[
\boxed{\text{communication-bound}}
]

这正是为什么：

> “1000 张卡全做 FSDP 不就好了？”

并不是超大训练的普适解。

Lecture 8 后面用实际 scaling experiment 说明，纯 ZeRO-3 在非常大规模时每 GPU throughput 会明显下降，而合理的 TP+PP+DP 组合能保持更平坦的 per-GPU throughput。([Yulong Ge][2])

---

# 十四、所以必须进入 Model Parallelism

Data parallel family：

[
\boxed{\text{同一个模型，切数据}}
]

即使 FSDP 把 state shard 了，计算时一层仍需要 materialize。

Model parallelism 则直接说：

> **这个模型运算本身就不要在一张 GPU 上完成。**

两个主要方向：

[
\boxed{\text{Pipeline Parallelism：沿 depth}}
]

和：

[
\boxed{\text{Tensor Parallelism：沿 width}}
]

---

# 十五、Pipeline Parallelism：最适合解决“模型太深”

假设有 32 层。

4 GPUs：

```text
GPU0: layer  0–7
GPU1: layer  8–15
GPU2: layer 16–23
GPU3: layer 24–31
```

所以 parameter memory：

[
\approx\frac14.
]

forward：

```text
GPU0
 ↓ activation
GPU1
 ↓ activation
GPU2
 ↓ activation
GPU3
```

通信只发生 stage boundary。

传的是：

[
\boxed{[b_{\rm micro},s,h]\text{ activation}}
]

而不是整个 parameter set。([Yulong Ge][2])

---

# 十六、PP 最大敌人：Bubble

如果只有一个 microbatch：

```text
time →

GPU0 ████
GPU1     ████
GPU2         ████
GPU3             ████
```

大量设备空闲。

把 batch 切成：

[
m
]

个 microbatches：

```text
GPU0 A B C D E F
GPU1   A B C D E F
GPU2     A B C D E F
GPU3       A B C D E F
```

pipeline utilization 大幅提高。

对于 (p) 个 stages、(m) 个 micro-batches，一个常见简化 bubble fraction 是：

[
\boxed{
\frac{p-1}{m+p-1}
}
]

所以：

[
m\gg p
]

时 bubble 才小。

这就是为什么：

[
\boxed{\text{Pipeline Parallelism 很依赖足够多的 microbatches}}
]

([Yulong Ge][2])

---

# 十七、1F1B 到底优化什么？

最简单 pipeline：

```text
Forward all
↓
Backward all
```

会留下很多 activation：

[
\boxed{\text{activation memory 很大}}
]

1F1B：

[
\boxed{\text{one forward, one backward}}
]

steady state 中：

```text
F
B
F
B
F
B
```

尽快 backward 已完成的 microbatch，于是之前保存的 activation 可以释放。

所以：

[
\boxed{\text{1F1B 主要降低 pipeline activation memory}}
]

而不是神奇地把通信消灭。Lecture 8 进一步讨论 interleaved schedules 和 Zero-Bubble Pipeline。([Yulong Ge][2])

---

# 十八、Zero-Bubble 最漂亮的洞察：Backward 其实可以拆成两件事

考虑：

[
z=Wx.
]

Backward：

[
\boxed{
\frac{\partial L}{\partial x}
=============================

W^\top
\frac{\partial L}{\partial z}
}
]

和：

[
\boxed{
\frac{\partial L}{\partial W}
=============================

\frac{\partial L}{\partial z}x^\top
}
]

第一项必须赶紧算。

为什么？

因为：

[
\frac{\partial L}{\partial x}
]

要传给前一层。

但是第二项：

[
\frac{\partial L}{\partial W}
]

并不影响上一层继续 backward。

所以可以：

> **先传播 activation gradient，weight gradient 晚点算。**

然后把这些 weight-gradient computation 塞进原本 pipeline bubble。

这就是 Zero-Bubble Pipeline 的核心调度直觉：

[
\boxed{\text{通过重新安排依赖较弱的计算来填 bubble}}
]

([Yulong Ge][2])

---

# 十九、Tensor Parallelism 则完全不一样：一层本身切开

假设：

[
Y=XW.
]

将：

[
W
]

沿列切：

[
W=
[W_1,W_2,\ldots,W_p].
]

于是：

[
Y_i=XW_i.
]

每个 GPU 只计算 output features 的一部分。

这就是：

[
\boxed{\text{Column Parallel}}
]

下一层再沿另一方向切：

[
W=
\begin{bmatrix}
W_1\
W_2\
\vdots
\end{bmatrix}.
]

每个 GPU：

[
Z_i=Y_iW_i.
]

最终：

[
Z=\sum_i Z_i.
]

因此需要：

[
\boxed{\text{AllReduce}}
]

这就是经典 Megatron-LM 的 column-parallel + row-parallel 配对思想。

---

# 二十、为什么这种切法特别漂亮？

考虑 MLP：

[
X
\xrightarrow{W_1}
H
\xrightarrow{\phi}
Y
\xrightarrow{W_2}
O.
]

如果 (W_1) column-shard：

```text
GPU0: H0
GPU1: H1
GPU2: H2
GPU3: H3
```

activation：

[
\phi
]

是 elementwise 的。

所以每张 GPU 直接：

[
\phi(H_i)
]

即可。

**完全不用先 AllGather H。**

然后 (W_2) 使用 row-shard，最后产生 partial outputs：

[
O_0,O_1,\ldots
]

只需：

[
\boxed{\text{一次 AllReduce}}
]

得到完整：

[
O=\sum_iO_i.
]

所以 MLP 的两个 Linear 可以巧妙配对，让中间 hidden state 始终保持 sharded。

这就是 Megatron Tensor Parallel 的核心设计。

---

# 二十一、Lecture 8 里的 (f) 和 (g) 是什么意思？

Megatron 常把通信行为抽象成两个共轭算子。

一个算子：

[
f
]

forward：

[
\boxed{\text{identity}}
]

backward：

[
\boxed{\text{AllReduce}}
]

另一个：

[
g
]

forward：

[
\boxed{\text{AllReduce}}
]

backward：

[
\boxed{\text{identity}}.
]

为什么？

因为线性层不同切分方式决定：

> 到底是 forward 的 partial results 要合并，还是 backward 的 partial gradients 要合并。

Lecture 8 希望你真正看到：

[
\boxed{\text{TP 不只是“把矩阵切一下”，还要考虑 forward/backward 双向数据依赖}}
]

([Yulong Ge][2])

---

# 二十二、TP 最大的问题：通信频率太高

Pipeline：

```text
8 layers on GPU0
↓
send activation
↓
8 layers on GPU1
```

Tensor Parallel：

```text
layer 1
↓ collective
layer 2
↓ collective
layer 3
↓ collective
...
```

Lecture 8 的通信分析指出，一个 Transformer 层内 TP 会产生多次 activation-sized collectives；因此通信频率大致随 layer count：

[
\mathcal O(L)
]

增长。([Yulong Ge][2])

所以：

[
\boxed{\text{TP 必须用非常快的网络}}
]

实践中就意味着：

[
\boxed{\text{优先限制在 NVLink/NVSwitch domain 内}}
]

这就是那个你以后会看到无数遍的经验：

[
\boxed{\text{TP degree 经常 ≤ 单节点 GPU 数}}
]

例如传统 8-GPU node：

[
TP\le8.
]

不是数字 8 有什么神秘意义，而是 hardware topology 决定的。

---

# 二十三、到这里还没完：Parameter memory 解决了，Activation memory 又爆了

这是 Lecture 8 一个非常重要的转折。

很多人在算大模型显存时只会：

[
\text{parameters}
+
\text{Adam}
+
\text{gradient}.
]

但 Transformer 训练时：

[
\boxed{\text{activation 很可能才是峰值显存的大头}}
]

尤其：

[
s=\text{sequence length}
]

很长时。

Lecture 8 引用了 Megatron sequence-parallelism 工作，对标准 Transformer 每层 backward 所需 activation 做了详细 accounting，并强调 attention 的某些激活项甚至含：

[
s^2.
]

因此：

[
\boxed{\text{长上下文训练首先会撞 activation wall}}
]

([Yulong Ge][2])

---

# 二十四、为什么 TP 也不能把 Activation 全切掉？

假设 hidden dimension：

[
h
]

被 TP 切：

[
h/t.
]

那么 QKV/MLP 等很多 activation 自然也：

[
\frac1t.
]

但有一类 operation 并不沿 hidden dimension 工作，例如：

```text
LayerNorm
Dropout
Residual
```

它们是：

[
\boxed{\text{逐 token operation}}
]

完整 activation：

[
[B,S,H]
]

仍可能在每个 TP rank 上 replicated。

所以 TP 后还存在一部分：

[
\boxed{\text{无法通过 hidden-width sharding 消掉的 activation}}
]

这正是 Sequence Parallelism 要解决的问题。([Yulong Ge][2])

---

# 二十五、Sequence Parallelism：既然 hidden 切不了，那切 sequence

假设：

[
X:[B,S,H].
]

TP：

[
H\rightarrow H/t.
]

SP：

[
\boxed{S\rightarrow S/t}.
]

于是：

```text
GPU0: tokens 0...S/t
GPU1: tokens S/t...2S/t
...
```

对于：

```text
LayerNorm
Dropout
Residual
```

这些逐 token operation：

> 每个 token 本来就可以独立算。

所以完全不需要所有 GPU 都保存完整：

[
S.
]

这就是：

[
\boxed{\text{Sequence Parallelism}}
]

---

# 二十六、但 Sequence Parallelism 和 Context Parallelism 不是一回事

这个区别非常重要。

SP 通常针对：

[
\boxed{\text{逐 token operations}}
]

例如：

```text
Norm
Dropout
Residual
```

因为每个 token 独立。

但 Attention：

[
\operatorname{softmax}(QK^\top)V
]

第一个 token 可能需要和：

[
\boxed{\text{所有其他历史 token}}
]

交互。

你不能简单：

```text
GPU0 只看 sequence chunk 0
GPU1 只看 chunk 1
```

否则 attention 语义就变了。

于是需要另一种东西：

[
\boxed{\text{Context Parallelism}}
]

---

# 二十七、Context Parallel / Ring Attention 是怎么回事？

假设超长 context：

[
S=1M.
]

4 GPUs。

每个 GPU 保存：

[
S/4
]

的 Q/K/V：

```text
GPU0: tokens 0–249k
GPU1: 250k–499k
GPU2: 500k–749k
GPU3: 750k–999k
```

对于 GPU0 的 Q：

它最终还需要看 GPU1/2/3 的 K,V。

所以让 K,V block 沿 ring：

```text
Step 1
GPU0 uses KV0
GPU1 uses KV1
...

Step 2
KV blocks rotate
GPU0 uses KV3
GPU1 uses KV0
...

Step 3
rotate again
```

每次只计算一个：

[
Q_{\rm local}K_{\rm block}^\top
]

并利用类似 FlashAttention 的 online softmax，把分块结果精确合并。

最终仍然得到：

[
\boxed{\text{exact full attention}}
]

但每 GPU 只需存：

[
\boxed{\frac1P\text{ 的 sequence-side state}}
]

这就是 Ring Attention / Context Parallelism 的核心。([Yulong Ge][2])

---

# 二十八、看到没有？Lecture 5 的 FlashAttention 又回来了

FlashAttention：

```text
一张 GPU 内

K/V tiles
↓
依次经过片上 memory
↓
online softmax
```

Ring Attention：

```text
很多 GPU 间

K/V tiles
↓
依次经过各 GPU
↓
online softmax
```

所以可以用一个非常漂亮的 mental model：

[
\boxed{
\text{Ring Attention = distributed tiling of attention}
}
]

并不是严格定义，但极其好理解。

Lecture 5：

> tile 在 HBM ↔ SRAM 之间流。

Lecture 8：

> tile 在 GPU ↔ GPU 之间流。

---

# 二十九、Expert Parallelism：MoE 又提供了一个天然维度

Lecture 4：

[
E_1,E_2,\ldots,E_{64}
]

这些 experts 不需要每张 GPU 都拥有。

可以：

```text
GPU0: Expert 0
GPU1: Expert 1
...
```

token 经过 router：

```text
token A → expert 7
token B → expert 13
token C → expert 1
```

于是：

[
\boxed{\text{All-to-All Dispatch}}
]

把 token 发给对应 expert。

expert 算：

[
FFN(x)
]

之后：

[
\boxed{\text{All-to-All Combine}}
]

再把结果发回原 token 所属 GPU。([Yulong Ge][2])

这就是：

[
\boxed{\text{Expert Parallelism}}
]

---

# 三十、为什么 MoE Expert 层优先 EP，而不是继续 TP？

假设每个 expert 已经不大。

如果再 TP：

```text
一个小 expert
↓
再切成 8 块
↓
8 个更小 GEMM
```

GPU 可能：

[
\boxed{\text{吃不满}}
]

EP 则：

```text
GPU0 完整算 Expert0
GPU1 完整算 Expert1
...
```

每个 expert GEMM 保持较大。

同时 communication：

TP：

[
\boxed{\text{多次 collective}}
]

EP：

[
\boxed{\text{dispatch + combine 两次 All-to-All}}
]

因此 Lecture 8 总结出的一个现代 MoE guideline 是：

[
\boxed{\text{Expert layer 优先 EP，而不是 TP}}
]

特别是 experts 很细粒度时。([Yulong Ge][2])

---

# 三十一、现在所有 parallelism 都齐了

我们可以重新看 Transformer 的坐标轴：

[
X:[B,S,H]
]

模型有：

[
L
]

层，以及：

[
E
]

experts。

于是：

| Parallelism | 切哪个轴               |
| ----------- | ------------------ |
| DP          | (B)：batch          |
| TP          | (H)：hidden / width |
| SP/CP       | (S)：sequence       |
| PP          | (L)：layers / depth |
| EP          | (E)：experts        |

再加 ZeRO/FSDP：

[
\boxed{\text{对 training states 做 sharding}}
]

所以所谓：

[
\boxed{\text{3D/4D/5D parallelism}}
]

没有什么神秘。

本质就是：

> **同时沿多个彼此相对独立的轴切。**

---

# 三十二、为什么不能“所有维度都开到最大”？

因为每一种 parallelism 都不是免费的。

DP：

[
\boxed{\text{gradient communication}}
]

FSDP：

[
\boxed{\text{parameter gather}}
]

TP：

[
\boxed{\text{per-layer activation collectives}}
]

PP：

[
\boxed{\text{bubble + activation transfer}}
]

CP：

[
\boxed{\text{KV movement}}
]

EP：

[
\boxed{\text{All-to-All + load balancing}}
]

所以问题不是：

> “有多少 GPU？”

而是：

[
\boxed{
\text{哪些 GPU 应该组成 TP group？
哪些组成 PP group？
哪些组成 DP group？}
}
]

这就进入 Lecture 8 真正最重要的 Part 3。

---

# 三十三、并行组合最重要的原则：最频繁的通信放最快的网络

这是整讲我认为最值得记住的一条。

按照 communication sensitivity：

[
\boxed{
TP
\rightarrow
\text{非常频繁、latency sensitive}
}
]

所以放：

[
\boxed{\text{NVLink/NVSwitch domain}}
]

接着 CP / EP 视模型和网络情况处理。

PP：

[
\boxed{\text{较少的 point-to-point activation transfer}}
]

可以跨 node。

DP/ZeRO：

[
\boxed{\text{每 step/gradient bucket 较粗粒度 communication}}
]

而且很容易 overlap，所以最适合做最外层。Lecture 8 的经验规则正是“TP 封在高速域，PP 向外扩展，剩余 GPU 用 DP；长序列加 CP，MoE 加 EP”。([Yulong Ge][2])

---

# 三十四、所以经典 3D Parallelism 长这样

假设：

[
1024\text{ GPUs}.
]

一种示意：

[
TP=8
]

[
PP=16
]

那么一个 model replica：

[
8\times16=128\text{ GPUs}.
]

剩下：

[
DP=
1024/128
========

8.

]

所以：

[
\boxed{
8_{\rm TP}
\times
16_{\rm PP}
\times
8_{\rm DP}
==========

1024
}
]

拓扑：

```text
DP replica 0
├── PP stage 0
│    └── TP GPUs × 8
├── PP stage 1
│    └── TP GPUs × 8
...
└── PP stage 15

DP replica 1
...
```

这就是经典：

[
\boxed{\text{PTD-P}}
]

Pipeline + Tensor + Data Parallelism。

---

# 三十五、为什么经验上经常“TP 先扩到 8，然后停”？

Lecture 8 引用 Megatron 大规模实验：模型从十几亿一路增长到约 1T 时，TP degree 先从 1、2、4 增长到 8；之后模型再大，也倾向保持 TP=8，而增加 Pipeline degree。([Yulong Ge][2])

原因就是：

```text
8 GPUs
↓
一个高速 NVLink domain
```

如果：

[
TP=16,\ 32,\ 64
]

TP collective 开始跨较慢网络。

于是：

[
\boxed{\text{communication cost 暴涨}}
]

所以不是：

[
8=\text{Transformer 神圣数字}.
]

而是：

[
\boxed{8=\text{当时那套 node topology 的自然边界}}
]

新硬件 domain size 变化，这个数字当然也会变化。

---

# 三十六、那为什么不用纯 Pipeline？

PP degree 越大：

[
p\uparrow
]

bubble：

[
\frac{p-1}{m+p-1}
]

也上升。

也就是说：

```text
TP 太大
→ network 爆

PP 太大
→ bubble 爆
```

所以存在 sweet spot。

Lecture 8 引用的 162B 模型实验里，不同 PP/TP 组合比较，类似：

[
(2,32),(4,16),(8,8),(16,4),(32,2)
]

中间：

[
\boxed{TP=8,\ PP=8}
]

附近达到最好 throughput；两侧分别被 TP communication 和 PP bubble 拖累。([Yulong Ge][2])

这就是 systems optimization 的味道：

[
\boxed{\text{没有单调的“越多越好”。}}
]

---

# 三十七、为什么 Data Parallelism 一般最后再扩？

因为 DP 最大的优点：

[
\boxed{\text{对模型计算图侵入最小}}
]

并且：

[
\boxed{\text{communication frequency 相对较低}}
]

所以模型先通过：

[
TP/PP/EP/CP
]

确保：

[
\boxed{\text{单个 model replica 能装得下}}
]

然后还有 GPU：

> 拿来复制更多 model replicas，扩大 DP。

这正是 Lecture 8 给出的经验法则之一：

[
\boxed{\text{Minimize model parallelism, maximize data parallelism}}
]

当然这里有一个前提：

[
\boxed{\text{global batch 不能无限增加}}
]

这也正好给 Lecture 9 Scaling Laws 埋下伏笔。([Yulong Ge][2])

---

# 三十八、为什么 Batch Size 成了 Parallelism 的隐藏核心变量？

这是 Lecture 8 很容易被忽视的一点。

DP 越大：

[
\boxed{\text{global batch}\uparrow}
]

PP 要减少 bubbles：

[
\boxed{\text{microbatches}\uparrow}
]

EP 希望每 expert GEMM 大：

[
\boxed{\text{tokens per expert}\uparrow}
]

也需要更大的 token batch。

所以 parallel efficiency 和 optimization/statistics 之间会产生冲突：

系统工程师：

> batch 越大越好，GPU 越满。

优化理论：

> batch 超过 critical batch size 后，sample efficiency 可能下降。

这就是为什么 Lecture 8 后面紧跟：

[
\boxed{\text{Lecture 9 Scaling Laws}}
]

非常自然。

---

# 三十九、Activation Recomputation 在 Lecture 8 又出现了一次，而且意义升级了

以前你学 checkpointing：

[
\boxed{\text{compute}\uparrow,\ memory\downarrow}
]

感觉它就是一个性能税。

但 Lecture 8 展示了一个更系统的视角。

没有 recomputation：

```text
显存满
↓
batch 最大只能很小
↓
GEMM 小
↓
GPU utilization 差
```

开启 recomputation：

```text
多做一些 FLOPs
↓
activation memory 大降
↓
batch 可以大很多
↓
GEMM 更大
↓
GPU utilization 上升
```

最终可能出现：

[
\boxed{
\text{FLOPs 更多}
\quad\text{但}\quad
\text{total throughput 更高}
}
]

Lecture 8 引用的大规模实验就展示了这种情况。([Yulong Ge][2])

又一次证明 CS336 的老主题：

[
\boxed{\text{减少 FLOPs 从来不等价于跑得更快。}}
]

---

# 四十、Llama 3 405B 是 Lecture 8 一个非常漂亮的真实案例

Lecture 8 用 Llama 3 405B 的公开配置说明这些理论不是纸上谈兵。

主训练阶段采用类似：

[
TP=8,\quad PP=16
]

再用大量 DP 扩展到上万 GPU。

而长上下文阶段从约：

[
8K
]

扩展到：

[
128K
]

时，DP degree 会下降，改拿部分并行维度去做：

[
\boxed{CP=16}
]

也就是说：

> GPU 总数不变，但从“复制更多 batch”变成“共同处理更长 sequence”。

这完美说明：

[
\boxed{\text{parallel axes 本质上是在争夺同一批 GPU。}}
]

([Yulong Ge][2])

---

# 四十一、DeepSeek-V3 又体现了 MoE 世界的另一套取舍

Lecture 8 还用 DeepSeek 类系统展示：

Dense Transformer 常见：

[
TP+PP+DP.
]

MoE 则会出现：

[
\boxed{EP}
]

成为非常重要的维度。

DeepSeek-V3 公开配置中采用很高的 Expert Parallel degree，并通过专门的 all-to-all communication overlap 去隐藏 EP 通信。Lecture 8 用它说明：

> **当模型结构变成 MoE，最优 parallelism 也会随 architecture 一起变化。**

([Yulong Ge][2])

所以 Architecture 与 Systems 再一次完全纠缠在一起。

---

# 四十二、到这里应该形成“选并行方案”的真正方法论

以后有人给你：

```text
Model:
120B
80 layers
hidden 12288
sequence 32K
MoE 64 experts

Hardware:
512 H100
8 GPUs/node
NVLink inside node
InfiniBand across nodes
```

不要第一反应：

> “用 FSDP。”

也不要：

> “Megatron TP8。”

你应该先问三件事：

[
\boxed{\text{第一：到底是哪堵 memory wall？}}
]

parameter state？

activation？

KV/context？

experts？

然后：

[
\boxed{\text{第二：这种 parallelism 的通信模式是什么？}}
]

AllReduce？

AllGather？

AllToAll？

P2P？

Ring？

最后：

[
\boxed{\text{第三：它应该放在哪一级网络？}}
]

NVLink domain？

同 rack？

跨 node？

这才是 Lecture 8 真正培养的能力。([Yulong Ge][2])

---

# 四十三、我建议你真正记住这张总表

| 方法            | 切什么                        | 解决什么                   | 主要代价                  |
| ------------- | -------------------------- | ---------------------- | --------------------- |
| DDP           | Batch                      | 加 throughput           | Gradient AllReduce    |
| ZeRO-1        | Optimizer states           | optimizer memory       | RS + AG               |
| ZeRO-2        | + Gradients                | gradient memory        | ReduceScatter         |
| FSDP / ZeRO-3 | + Parameters               | parameter-state memory | Parameter AllGather   |
| TP            | Hidden width               | 单层太大                   | 高频 collectives        |
| PP            | Layers                     | 模型太深/太大                | bubbles + P2P         |
| SP            | Sequence for tokenwise ops | activation memory      | 和 TP 配套 collectives   |
| CP            | Full context               | 长序列 Attention          | KV/ring communication |
| EP            | Experts                    | MoE parameter capacity | All-to-All            |

这张表就是 Lecture 8 的骨架。官方课件的总结也正是从每 rank 参数内存、activation/KV memory、communication pattern 等维度比较这些方案。([Yulong Ge][2])

---

# 四十四、Lecture 7 和 8 最核心的认知升级是什么？

Lecture 7 你可能会觉得：

> DP、TP、PP 是几个不同算法。

Lecture 8 之后应该变成：

[
\boxed{
\text{它们是不同 tensor/state dimensions 的 sharding choices。}
}
]

而任何一个 choice 都可以从三张账表分析：

[
\boxed{\text{Memory}}
]

每 GPU 存多少？

[
\boxed{\text{Compute}}
]

每 GPU 做多少 FLOPs？

[
\boxed{\text{Communication}}
]

每 step 跨设备搬多少 bytes？

所以真正的 parallelism design 就是：

[
\boxed{
\min T_{\rm step}
\quad
\text{s.t.}
\quad
M_{\rm GPU}<M_{\rm available}
}
]

其中：

[
T_{\rm step}
]

又由：

[
T_{\rm compute},
T_{\rm communication},
T_{\rm bubble}
]

共同决定。

这已经是一个 optimization problem 了。

---

# 四十五、这也是为什么大模型 Infra 会越来越像“编译器问题”

因为 parallel strategy 实在太复杂：

```text
DP degree?
TP degree?
PP degree?
EP degree?
CP degree?

microbatch?
checkpoint placement?
FSDP unit size?
prefetch?
communication overlap?
rank topology?
```

靠人手挑越来越不现实。

Lecture 7 已经提到 JAX/GSPMD 这类系统：

> 用户描述 tensor axis 和 sharding strategy，compiler 负责生成 communication。

Lecture 8 更进一步让你理解：

[
\boxed{\text{自动 parallelization 的目标就是搜索这种巨大组合空间。}}
]

这也是 modern compiler / ML systems 非常核心的问题。

---

# 四十六、如果你只是学 CS336，而不是准备做分布式系统研究，哪些必须真的掌握？

我认为必须内化的是这几个推导，而不是 API 名字：

[
\boxed{\text{AllReduce = ReduceScatter + AllGather}}
]

并理解为什么通信约：

[
2M.
]

理解：

[
\boxed{\text{ZeRO-1 → optimizer}}
]

[
\boxed{\text{ZeRO-2 → + gradient}}
]

[
\boxed{\text{ZeRO-3/FSDP → + parameter}}
]

以及：

[
\boxed{\text{FSDP 用 communication 换 memory}}
]

再理解：

[
\boxed{\text{TP = width}}
]

[
\boxed{\text{PP = depth}}
]

[
\boxed{\text{SP/CP = sequence}}
]

[
\boxed{\text{EP = experts}}
]

最后掌握：

[
\boxed{\text{高频通信放快网络，低频通信放外层}}
]

这一条。

做到这里，你以后读 DeepSeek、Llama、Megatron 技术报告的 training infrastructure 部分已经不会再像看天书。

---

# 四十七、我最推荐你自己推的 10 道题

这讲很适合用“做题”检验是否真的懂了：

1. 为什么 ring AllReduce 每 rank 通信量近似 (2M)，而不是随着 GPU 数线性增长？
2. mixed-precision Adam 为什么 Lecture 8 粗算成约 16 bytes/parameter？
3. ZeRO-1/2/3 分别 shard 什么？
4. 为什么 FSDP 通信近似从 DDP 的 (2M) 变成约 (3M)？
5. 为什么 FSDP 能省显存，但 scale 到太多 GPU 时可能越来越慢？
6. 为什么 TP 常限制在 NVLink domain，而 PP 可以跨机？
7. 为什么 PP 需要 microbatches？推导 bubble fraction。
8. 为什么 TP 之后还需要 SP？
9. 为什么 SP 和 CP 不是同一种 parallelism？
10. 给你 GPU 总数 (G)，以及 (TP,PP,CP,EP)，能否算出剩余 DP degree？

最后一题的基本思想就是：

[
\boxed{
G
=

DP\times TP\times PP\times CP\times\cdots
}
]

当然实际 EP/DP group 的组织不一定简单独立相乘，但作为第一层 mental model 很有用。

---

# 最后，把 Lecture 8 压缩成一张“教师黑板”

你现在从 Lecture 2 到 Lecture 8，其实已经走完了一条非常完整的 Systems 路线：

[
\boxed{\text{Lecture 2：给模型算资源账}}
]

↓

[
\boxed{\text{Lecture 5：理解一张 GPU 的 memory/compute hierarchy}}
]

↓

[
\boxed{\text{Lecture 6：用 tiling/fusion 控制 GPU 内的数据流}}
]

↓

[
\boxed{\text{Lecture 7：学习跨 GPU communication primitives}}
]

↓

[
\boxed{\text{Lecture 8：用 sharding + topology 设计整个训练集群}}
]

而 Lecture 8 最核心的一张“总公式”其实不是某篇论文的式子，而是：

[
\boxed{
\textbf{Training System}
========================

\textbf{Compute}
+
\textbf{Memory}
+
\textbf{Communication}
}
]

你无法单独优化其中一个。

FSDP：

[
Memory\downarrow,\ Communication\uparrow
]

Checkpointing：

[
Memory\downarrow,\ Compute\uparrow
]

TP：

[
Memory\downarrow,\ Communication\uparrow
]

PP：

[
Memory\downarrow,\ Bubble\uparrow
]

EP：

[
Parameter\ capacity\uparrow,\ AllToAll\uparrow
]

CP：

[
Context\ capacity\uparrow,\ KV\ communication\uparrow
]

**所有现代大模型系统设计，本质都是在这些账之间做交换。**

而这也解释了为什么 Lecture 9 马上转向 Scaling Laws：到 Lecture 8 为止，我们已经学会“给定一个模型，如何尽可能高效地训练”；下一步自然就是问：

[
\boxed{
\text{如果我的总 compute budget 固定，
模型应该做多大、数据应该给多少，才最划算？}
}
]

那就是 Scaling Laws 真正要解决的问题。
