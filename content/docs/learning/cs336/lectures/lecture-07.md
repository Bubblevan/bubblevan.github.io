---
title: "L07 · Parallelism"
weight: 7
date: 2026-08-28
updated: 2026-08-28
course: "CS336"
topics: ["CS336", "parallelism", "distributed-training"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture7/
---

Lecture 7 是 CS336 从 **单卡 Systems** 正式进入 **分布式训练** 的第一讲，而且 2026 年课程特意连续安排了两讲 Parallelism：Lecture 7 由 Percy Liang 在 4 月 20 日讲基础，Lecture 8 再由 Tatsu Hashimoto 继续深入。

如果说 Lecture 5–6 一直在研究：

$$
\boxed{\text{怎样减少 GPU 内部的数据搬运？}}
$$

那么 Lecture 7 只是把同一个思想放大：

$$
\boxed{\text{怎样减少 GPU 与 GPU 之间的数据搬运？}}
$$

官方开场也正是这么说的：上一周研究单 GPU 内的 parallelism，这一周研究多 GPU；统一主题始终是 **orchestrate computation to avoid data-transfer bottlenecks**。

---

# 0. 先抓住 Lecture 7 的整条主线

这一讲实际上分成两半。

第一半先建立分布式世界的“指令集”：

```text
Rank / World Size
      ↓
Collective Operations
      ↓
Broadcast / Scatter / Gather / Reduce
      ↓
All-Gather / Reduce-Scatter / All-Reduce / All-to-All
      ↓
NVLink / InfiniBand / Ethernet
      ↓
NCCL
      ↓
torch.distributed
```

第二半才真正问：

> 一个大模型究竟沿哪个维度切？

官方用一个简单深层 MLP 演示三种核心方案：

$$
\boxed{\text{Data Parallelism：沿 batch 切}}
$$

$$
\boxed{\text{Tensor Parallelism：沿 width 切}}
$$

$$
\boxed{\text{Pipeline Parallelism：沿 depth 切}}
$$

并在总结里补上 sequence/expert parallelism 等其他维度。([GitHub][2])

所以我希望你先形成一个总图：

```text
一个训练 tensor / model

Batch dimension ─────→ Data Parallelism
Hidden width ────────→ Tensor Parallelism
Layer depth ─────────→ Pipeline Parallelism
Sequence length ─────→ Sequence Parallelism
Experts ─────────────→ Expert Parallelism
```

**所谓“各种并行”，本质就是在问：到底沿哪个维度 shard。**

---

# 1. 为什么一张 GPU 不够以后，事情突然难很多？

有两个原因。

第一种：

$$
\boxed{\text{模型根本放不下}}
$$

训练显存还记得 Lecture 2 吧：

$$
M
=

M_{\rm params}
+
M_{\rm gradients}
+
M_{\rm optimizer}
+
M_{\rm activations}.
$$

即便模型参数本身能放下，Adam state + gradient + activation 也可能把显存撑爆。

第二种：

$$
\boxed{\text{一张 GPU 太慢}}
$$

如果：

$$
C_{\rm train}\approx6ND
$$

特别巨大，那你自然想：

```text
1 GPU → 8 GPUs → 64 GPUs → 1024 GPUs
```

理论 FLOP/s 不断增加。

Lecture 7 官方开场明确给的理由就是这两个：**放不下**，或者**想利用更多 GPU FLOPs 加速训练**。([GitHub][2])

但问题来了：

> GPU 数量翻 8 倍，训练速度会翻 8 倍吗？

不一定。

因为你增加的不只是：

$$
\boxed{\text{compute}}
$$

也增加了：

$$
\boxed{\text{communication}}
$$

这就是整堂课真正的矛盾。

---

# 2. Lecture 5 的 Memory Hierarchy，现在被扩展成 Communication Hierarchy

单 GPU 时：

```text
Register
   ↓
Shared Memory / L1
   ↓
L2
   ↓
HBM
```

Lecture 7 把这套层级扩大：

```text
L1/shared memory
      ↓
HBM
      ↓
NVLink / NVSwitch
      ↓
InfiniBand
      ↓
Ethernet
```

越往下：

$$
\boxed{\text{距离越远，数据移动通常越贵}}
$$

官方讲义明确列出：

* 单 GPU 片上 L1/shared memory：最快；
* 单 GPU HBM；
* 单节点多 GPU：NVLink/NVSwitch；
* 多节点：InfiniBand/Ethernet，更慢。([GitHub][2])

于是你应该发现：

## Lecture 5

想办法：

$$
\boxed{\text{别老从 HBM 读}}
$$

于是有：

```text
fusion
tiling
recomputation
```

## Lecture 7

想办法：

$$
\boxed{\text{别老跨 GPU 搬}}
$$

于是有：

```text
replication
sharding
collectives
communication overlap
```

完全是同一种 Systems 思维。

---

# 3. Rank 和 World Size 是什么？

分布式 PyTorch 里，这两个词会出现一万次。

假设有 4 张 GPU：

```text
GPU 0
GPU 1
GPU 2
GPU 3
```

通常每张 GPU 对应一个 process。

那么：

$$
\boxed{\text{rank}=这个 process/GPU 的编号}
$$

比如：

```text
rank = 0
rank = 1
rank = 2
rank = 3
```

而：

$$
\boxed{\text{world size}=参与通信的总进程数}}
$$

这里：

$$
world_size=4.
$$

官方 Lecture 7 就用 4 ranks 的例子建立后面所有 collective。([GitHub][2])

以后你看到：

```python
dist.init_process_group(
    "nccl",
    rank=rank,
    world_size=world_size,
)
```

就不要再觉得玄学了。

它只是告诉系统：

> “我是整个分布式团队里的第几号，一共有多少人。”

---

# 4. 为什么不让 GPU 自己 `send()`、`recv()` 就完了？

当然可以。

Lecture 7 pipeline parallelism 后面就会直接使用：

```python
dist.send(...)
dist.recv(...)
```

但大规模训练里，很多通信模式不断重复，例如：

> “每张卡都把一部分结果加起来，然后让大家都拿到完整结果。”

如果让程序员自己写：

```text
GPU0 send GPU1
GPU1 send GPU2
GPU2 send GPU3
...
```

很麻烦，而且你很难针对 NVLink、PCIe、InfiniBand topology 做最优规划。

于是分布式系统抽象出：

$$
\boxed{\text{Collective Operations}}
$$

你只描述：

> “我要 all-reduce。”

具体：

```text
谁先发谁
走哪根链路
ring 还是 tree
怎样分 chunk
```

让 NCCL 处理。

Lecture 7 把 collectives 称为 distributed programming 的 conceptual primitives。([GitHub][2])

---

# 5. Broadcast：一份东西复制给所有人

假设：

```text
rank 0: [0,1,2,3]
rank 1: ?
rank 2: ?
rank 3: ?
```

broadcast(rank 0)：

```text
rank 0: [0,1,2,3]
rank 1: [0,1,2,3]
rank 2: [0,1,2,3]
rank 3: [0,1,2,3]
```

所以：

$$
\boxed{\text{Broadcast = one → all}}
$$

一个典型用途：

> rank 0 加载 checkpoint，然后广播给其他 ranks。

这正是官方给的示例。([GitHub][2])

---

# 6. Scatter 和 Gather：拆开与拼回来

假设 rank 0：

$$
[0,1,2,3].
$$

Scatter：

```text
rank0 → [0]
rank1 → [1]
rank2 → [2]
rank3 → [3]
```

所以：

$$
\boxed{\text{Scatter = 一份大数据拆给各 rank}}
$$

Gather 刚好反过来：

```text
rank0: [0]
rank1: [1]
rank2: [2]
rank3: [3]

↓ gather to rank0

rank0: [0,1,2,3]
```

所以：

$$
\boxed{\text{Gather = 各 rank 的 shard 拼到一个 rank}}
$$

官方特别强调：

* scatter 是理解 reduce-scatter 的台阶；
* gather 是理解 all-gather 的台阶。([GitHub][2])

这一点很重要，因为后面真正的大模型系统其实主要都在使用它们的 **all/reduce 组合版本**。

---

# 7. Reduce：不仅拼数据，还要做“合并”

假设四张卡分别有：

$$
0,\quad1,\quad2,\quad3.
$$

如果：

$$
op=\text{SUM}
$$

那么 reduce 到 rank 0：

$$
0+1+2+3=6.
$$

最后：

```text
rank0: 6
```

所以：

$$
\boxed{\text{Reduce = 跨 rank 做 associative reduction}}
$$

常见操作：

$$
\text{SUM},\quad\text{AVG},\quad\text{MAX},\quad\text{MIN}.
$$

训练里最重要的当然是：

$$
\boxed{\text{sum / average gradients}}
$$

---

# 8. All-Gather：每个人都有一块，最后每个人都拿到全部

假设：

```text
GPU0: shard A
GPU1: shard B
GPU2: shard C
GPU3: shard D
```

All-Gather 后：

```text
GPU0: A B C D
GPU1: A B C D
GPU2: A B C D
GPU3: A B C D
```

所以：

$$
\boxed{
\text{All-Gather}
=================

\text{sharded}
\rightarrow
\text{replicated}
}
$$

这个 mental model 一定要记住。

因为它直接解释 FSDP：

```text
平时：
GPU0 参数 1/4
GPU1 参数 1/4
GPU2 参数 1/4
GPU3 参数 1/4

需要某层 forward：
        ↓
     all-gather
        ↓
每张 GPU 暂时得到完整 layer
```

Lecture 7 也明确把“每张 rank 持 parameter shard，forward 前拿回完整参数”作为 all-gather 的典型用途。([GitHub][2])

---

# 9. Reduce-Scatter：这个特别重要

假设每张 GPU 都算出完整 gradient：

$$
g^{(0)},g^{(1)},g^{(2)},g^{(3)}.
$$

首先你想把它们加起来：

$$
g
=

g^{(0)}
+
g^{(1)}
+
g^{(2)}
+
g^{(3)}.
$$

普通 reduce 可以让某一个 GPU 得到完整 (g)。

但如果最终我们希望：

```text
GPU0 只存 g 的第 1/4
GPU1 只存 g 的第 2/4
GPU2 只存 g 的第 3/4
GPU3 只存 g 的第 4/4
```

那就是：

$$
\boxed{\text{Reduce-Scatter}}
$$

即：

```text
先 reduce
   ↓
再 scatter
```

最终：

$$
\boxed{
\text{每张 GPU 只持有 reduce 后结果的一部分}
}
$$

官方给的主要用途：

> backward 后汇总不同 data shards 的梯度，同时让 gradient storage 保持 sharded。([GitHub][2])

这就是 ZeRO/FSDP 的核心原语之一。

---

# 10. All-Reduce 是整堂课最重要的 collective

官方直接给：

$$
\boxed{
\text{All-Reduce}
=================

\text{Reduce-Scatter}
+
\text{All-Gather}
}
$$

([GitHub][2])

这句话一定真正理解。

假设每张 GPU：

```text
GPU0: local gradient g0
GPU1: local gradient g1
GPU2: local gradient g2
GPU3: local gradient g3
```

最后希望所有 GPU 都得到：

$$
g=
g_0+g_1+g_2+g_3.
$$

那就：

### Phase 1：Reduce-Scatter

先把总 gradient 分块：

```text
GPU0: g_total[chunk0]
GPU1: g_total[chunk1]
GPU2: g_total[chunk2]
GPU3: g_total[chunk3]
```

### Phase 2：All-Gather

然后大家交换 chunk：

```text
GPU0: full g_total
GPU1: full g_total
GPU2: full g_total
GPU3: full g_total
```

于是：

$$
\boxed{\text{所有 rank 都拥有相同的 reduced tensor}}
$$

这就是 DDP 同步梯度的基础。

---

# 11. All-to-All 为什么专门和 MoE 连起来？

Lecture 4 的 MoE：

```text
GPU0 上有 Expert 0,1
GPU1 上有 Expert 2,3
GPU2 上有 Expert 4,5
...
```

但是 GPU0 的某个 token 可能被 router 分到：

```text
Expert 5
```

那它必须：

$$
GPU0\rightarrow GPU2.
$$

同时 GPU2 的 token 又可能发往 GPU1……

于是每张 GPU 都可能向**每张其他 GPU**发送不同 token：

$$
\boxed{\text{All-to-All}}
$$

官方用一个非常漂亮的例子：

```text
输入：
rank0: 0  1  2  3
rank1: 4  5  6  7
rank2: 8  9 10 11
rank3:12 13 14 15
```

all-to-all 以后：

```text
rank0: 0 4  8 12
rank1: 1 5  9 13
rank2: 2 6 10 14
rank3: 3 7 11 15
```

像一次矩阵 transpose。Lecture 7 明确指出这正是 MoE expert routing 的典型通信模式。([GitHub][2])

所以：

$$
\boxed{\text{DDP → All-Reduce}}
$$

$$
\boxed{\text{FSDP → All-Gather + Reduce-Scatter}}
$$

$$
\boxed{\text{MoE → All-to-All}}
$$

这三个关系最好背熟。

---

# 12. 现在才能真正理解为什么“多 GPU”并不等于“一块更大的 GPU”

单 GPU 内：

$$
HBM\ bandwidth
$$

非常高。

Lecture 7 以 B200 为例，把不同层级放在同一张图景里：同节点内 GPU 用 NVLink/NVSwitch，跨节点通常通过 InfiniBand；官方举例 B200 NVLink 5.0 约 1.8 TB/s，而同一 GPU 的 HBM bandwidth 仍显著更高，跨节点 InfiniBand 又更低。具体硬件数字会随系统变化，但层级关系才是重点。([GitHub][2])

可以粗略理解成：

```text
GPU 内部搬数据
████████████████████

同 node GPU ↔ GPU
██████

跨 node
██
```

因此：

> **多卡通信一定要有足够多的 computation 来 amortize。**

这正是为什么后面：

* Tensor Parallel 特别喜欢 NVLink；
* Pipeline Parallel 可以承受更慢的 interconnect；
* Data Parallel 更适合跨 node。

Lecture 7 的总结也明确指出 TP 需要很快的 interconnect，而 PP 可以容忍较慢通信，但要处理 pipeline bubbles。([GitHub][2])

---

# 13. NVLink、NVSwitch、InfiniBand 分别是什么角色？

先不用研究协议细节。

## NVLink

高速 GPU↔GPU interconnect。

目的：

$$
\boxed{\text{让同节点 GPU 更像一个紧密耦合系统}}
$$

---

## NVSwitch

如果很多 GPU：

```text
GPU0
GPU1
GPU2
...
```

不可能简单一根根全互联。

NVSwitch 就像 GPU 高速交换机。

所以：

```text
GPU
 ↓
NVLink
 ↓
NVSwitch
 ↓
NVLink
 ↓
another GPU
```

---

## InfiniBand

主要解决：

$$
\boxed{\text{跨机器/node 高速通信}}
$$

一个 node 里可能 8 张 GPU。

一个 pod 可能几百 nodes。

跨节点就需要高速 network fabric。

Lecture 7 的数据中心示意正是：

```text
8 GPUs / node
↓ NVLink/NVSwitch

many nodes
↓ InfiniBand

larger cluster
↓ Ethernet
```

([GitHub][2])

---

# 14. RDMA 为什么重要？

传统网络通信可能长这样：

```text
GPU
 ↓
CPU memory
 ↓
OS kernel
 ↓
network stack
 ↓
NIC
 ↓
network
```

中间 CPU 干了一堆事情。

这对于训练集群非常浪费。

RDMA：

$$
\boxed{\text{Remote Direct Memory Access}}
$$

目标就是让远端设备直接访问另一侧内存，绕开很多 CPU/OS 软件路径。

Lecture 7 明确说 InfiniBand 支持 RDMA，并提到 RoCE 让 Ethernet 也可以使用类似的 CPU-bypass 思路。([GitHub][2])

所以分布式 ML 的演进方向和 Lecture 5 很像：

> **少走弯路，少复制，数据尽可能直接到需要它的计算设备。**

---

# 15. NCCL 到底是什么？

这个一定要有清楚的层次感。

你在 PyTorch 写：

```python
dist.all_reduce(...)
```

PyTorch 不会自己去手搓：

```text
NVLink packet
InfiniBand packet
ring schedule
tree schedule
```

中间有：

$$
\boxed{\text{NCCL = NVIDIA Collective Communication Library}}
$$

Lecture 7 解释得非常直接：NCCL 检测硬件 topology，决定 GPU 之间数据走什么路径，并启动负责发送/接收的 GPU kernels。([GitHub][2])

所以软件栈可以粗略看成：

```text
Your training code

torch.distributed
        ↓
       NCCL
        ↓
NVLink / PCIe / InfiniBand
        ↓
      GPUs
```

这就是为什么你写：

```python
dist.all_reduce(...)
```

只有一行，却可以跑在：

```text
2 GPUs
8 GPUs
256 GPUs
1024 GPUs
```

不同 topology 上。

---

# 16. `torch.distributed` 又是什么？

PyTorch 给 collective operations 提供统一接口。

比如：

```python
dist.all_reduce(...)
dist.reduce_scatter_tensor(...)
dist.all_gather_into_tensor(...)
dist.send(...)
dist.recv(...)
```

backend 可以不同：

```text
CPU → Gloo
GPU → NCCL
```

官方 Lecture 7 就是直接用最底层的 `torch.distributed` primitives 演示，而不是先把 DDP/FSDP 当黑盒调用。([GitHub][2])

这很符合 CS336 的哲学：

> 不先教你“调用 FSDP”，而是先让你知道 FSDP 本质到底是什么 collectives 拼出来的。

---

# 17. Distributed Benchmark 跟 GPU Kernel Benchmark 一模一样，也得同步

Lecture 6 你刚学过：

```python
torch.cuda.synchronize()
```

因为 CUDA 是异步的。

现在还要加：

```python
dist.barrier()
```

因为除了单 GPU 异步：

> 不同 ranks 进度也不一样。

所以 Lecture 7 benchmark：

```text
warmup

cuda synchronize
distributed barrier

start
collective
cuda synchronize
distributed barrier
end
```

官方 all-reduce/reduce-scatter benchmark 就是这么做的。([GitHub][2])

所以：

$$
\boxed{
\text{单 GPU benchmark：同步 GPU}
}
$$

$$
\boxed{
\text{多 GPU benchmark：还得同步 ranks}
}
$$

---

# 18. 为什么讲义花时间计算 Effective Bandwidth？

假设一块 tensor 大小：

$$
S\text{ bytes}.
$$

你测得 all-reduce：

$$
T\text{ seconds}.
$$

只报告：

```text
all_reduce = 7 ms
```

信息其实很少。

因为：

```text
1 MB → 7ms
```

和：

```text
10 GB → 7ms
```

完全不是一回事。

所以更有意义的是：

$$
\boxed{
BW_{\rm effective}
==================

\frac{\text{有效数据量}}
{\text{通信时间}}
}
$$

Lecture 7 的 benchmark 专门按 collective 实际搬运的数据量估算有效 GB/s，并指出 all-reduce 可以理解成 reduce-scatter + all-gather，因此通信量/时间之间有对应关系。([GitHub][2])

这就是 Lecture 2 的 Roofline 又换了一个新版本：

## 单 GPU

瓶颈：

$$
\boxed{\text{HBM bandwidth}}
$$

## 多 GPU

瓶颈：

$$
\boxed{\text{network/interconnect bandwidth}}
$$

---

# 19. 终于进入 Data Parallelism：最简单、最重要的并行

假设 global batch：

$$
B=128.
$$

4 张 GPU。

最自然的做法：

```text
GPU0: samples 0–31
GPU1: samples 32–63
GPU2: samples 64–95
GPU3: samples 96–127
```

所以：

$$
\boxed{
B_{\rm local}
=============

\frac{B}{P}
}
$$

其中：

$$
P=\text{world size}.
$$

但是注意：

$$
\boxed{\text{每张 GPU 都保存完整 model}}
$$

官方 Lecture 7 的 Data Parallelism 正是“each rank gets a slice of the data”，而每个 rank 初始化全部层参数以及自己的 optimizer state。([GitHub][2])

---

# 20. 为什么每张 GPU 算出的 loss 可以不一样？

因为数据不同。

GPU 0：

$$
L_0
$$

GPU 1：

$$
L_1
$$

GPU 2：

$$
L_2
$$

GPU 3：

$$
L_3.
$$

于是 local gradients：

$$
g_0=\nabla L_0
$$

等等。

它们当然不同。

但单卡 global batch 的正确 gradient 应该：

$$
g
=

\frac1P
\sum_{r=0}^{P-1}
g_r.
$$

所以 backward 完后：

$$
\boxed{\text{All-Reduce gradients}}
$$

使用 AVG：

```python
dist.all_reduce(
    param.grad,
    op=dist.ReduceOp.AVG
)
```

Lecture 7 的裸实现几乎就是这么简单。([GitHub][2])

---

# 21. 为什么同步完 gradient 后，所有 GPU 参数始终一致？

开始：

$$
\theta_0=\theta_1=\theta_2=\theta_3.
$$

虽然 local gradient 不同，但 all-reduce 以后：

$$
g_0=g_1=g_2=g_3=g.
$$

然后每张 GPU 都执行：

$$
\theta
\leftarrow
\theta-\eta g.
$$

所以：

$$
\boxed{
\theta_0'
=========

# \theta_1'

# \theta_2'

\theta_3'
}
$$

下一 step 又继续一致。

所以 DDP 的核心不是：

> “每张卡训练一个模型，然后最后 ensemble。”

而是：

$$
\boxed{
\text{复制相同模型}
+
\text{切数据}
+
\text{每 step 同步 gradient}
}
$$

Lecture 7 官方总结也是：loss 不同、gradients all-reduced 相同，因此 parameters 保持相同。([GitHub][2])

---

# 22. Data Parallelism 为什么如此流行？

因为 communication/computation ratio 很漂亮。

一个 Transformer step：

每张 GPU 都能独立完成：

```text
full forward
+
full backward
```

直到 backward 产生 gradient 后才需要同步。

所以大量计算：

$$
\boxed{\text{完全 local}}
$$

而通信主要与：

$$
\boxed{\text{parameter/gradient size}}
$$

有关。

随着 local batch 增加：

$$
\text{compute}\uparrow
$$

但 gradient 大小：

$$
\text{基本不变}.
$$

所以较大的 local batch 可以很好地 amortize all-reduce。

这是 DP 能很好 scaling 的原因之一。

---

# 23. 但是 DDP 有一个巨大缺点：显存一点没省

如果模型训练状态需要：

$$
100GB,
$$

你有：

```text
GPU0 80GB
GPU1 80GB
GPU2 80GB
GPU3 80GB
```

DDP 是：

```text
GPU0: 完整 100GB ❌
GPU1: 完整 100GB ❌
...
```

加 GPU 没用。

因为它只 shard：

$$
\boxed{\text{data}}
$$

不 shard：

$$
\boxed{\text{model states}}
$$

所以：

$$
\boxed{\text{DDP 主要解决 throughput，不解决 model-state fit}}
$$

这就是为什么 Lecture 7 马上预告：

$$
\boxed{\text{FSDP / ZeRO}}
$$

通过 all-gather + reduce-scatter 来避免每张卡永久保存全部参数。([GitHub][2])

这是 Lecture 8 会继续深化的内容。

---

# 24. Tensor Parallelism：如果一层本身都太大，就把“一层”切掉

考虑：

$$
Y=XW
$$

其中：

$$
W\in\mathbb R^{d\times d}.
$$

假设 4 GPUs。

可以沿输出宽度切：

$$
W=
[
W_0\quad
W_1\quad
W_2\quad
W_3
].
$$

每块：

$$
W_i\in
\mathbb R^{d\times d/4}.
$$

所以每张 GPU 只存：

$$
\boxed{\frac14 W}
$$

这就是：

$$
\boxed{\text{Tensor Parallelism}}
$$

Lecture 7 官方把它描述为“each rank gets part of each layer”，即**沿 width dimension shard**。([GitHub][2])

---

# 25. TP 的 forward 怎么算？

所有 GPU 都拿到完整 input：

$$
X.
$$

GPU 0：

$$
Y_0=XW_0
$$

GPU 1：

$$
Y_1=XW_1
$$

GPU 2：

$$
Y_2=XW_2
$$

GPU 3：

$$
Y_3=XW_3.
$$

其中：

$$
Y_i:
[B,d/4].
$$

然后：

$$
Y=
[Y_0,Y_1,Y_2,Y_3].
$$

所以需要：

$$
\boxed{\text{All-Gather activations}}
$$

Lecture 7 的教学版 TP 正是每层计算 local activations，然后 all-gather，再沿 hidden dimension concat 成完整 activation。([GitHub][2])

---

# 26. TP 最大的问题也一下暴露了：每层都可能通信

DP：

```text
GPU0
整个 forward
整个 backward
   ↓
gradient sync
```

TP：

```text
Layer 1 local compute
↓
communication

Layer 2 local compute
↓
communication

Layer 3
↓
communication
...
```

也就是说，communication 处在模型 critical path 上，而且频率非常高。

所以 Lecture 7 明确总结：

$$
\boxed{\text{Tensor Parallelism requires very fast interconnects}}
$$

比如：

$$
\boxed{\text{NVLink}}
$$

([GitHub][2])

这解释一个非常实用的部署原则：

> **TP 通常优先放在一个高速 NVLink domain 内。**

不要轻易跨机做巨大 TP degree，因为 InfiniBand latency/bandwidth 更差。

---

# 27. Lecture 7 的 TP 是教学简化版，不要误解成工业实现全部如此

官方代码为了说明：

$$
\boxed{\text{width sharding}}
$$

每一层都：

```text
local matmul
↓
all-gather full activation
```

现实 Megatron-style tensor parallelism 会更聪明。

例如 MLP：

$$
XW_1
\rightarrow
\phi
\rightarrow
W_2
$$

可以把第一层 column-parallel，第二层 row-parallel，让中间 activation 保持 sharded，从而减少不必要的 collective。

所以你现在只需先掌握：

$$
\boxed{
\text{TP 的本质不是 all-gather，
而是沿 model width shard computation/parameters。
}
}
$$

具体怎么安排 reduce/all-gather，是下一层优化。

---

# 28. Pipeline Parallelism：宽度不切，直接把层切给不同 GPU

假设：

```text
Layer 1
Layer 2
Layer 3
Layer 4
```

两张 GPU：

```text
GPU0:
Layer 1
Layer 2

GPU1:
Layer 3
Layer 4
```

于是：

$$
\boxed{\text{Pipeline Parallelism = 沿 depth 切}}
$$

Lecture 7 官方正是“each rank gets subset of layers”。([GitHub][2])

Forward：

```text
Input
 ↓
GPU0: L1 → L2
 ↓ send activation
GPU1: L3 → L4
 ↓
Output
```

---

# 29. PP 的好处：通信量没有 TP 那么频繁

TP 每一层内部：

$$
GPU\leftrightarrow GPU
$$

频繁通信。

PP：

GPU0 算完它负责的一整段层后，只需要把 boundary activation：

$$
X_{\rm boundary}
$$

发给下一个 stage。

所以 communication frequency 小很多。

因此 Lecture 7 总结：

$$
\boxed{\text{Pipeline Parallelism can work with slower interconnects}}
$$

([GitHub][2])

这就是为什么大规模集群经常：

```text
节点内部高速 NVLink
→ Tensor Parallel

节点之间 InfiniBand
→ Pipeline / Data Parallel
```

这类 topology-aware mapping。

---

# 30. 但是最朴素 Pipeline 有个极大的问题：GPU 都在闲着

假设 2 stages：

```text
GPU0: Layer1-2
GPU1: Layer3-4
```

一个 batch：

```text
time →

GPU0: [ COMPUTE ] [ idle      ]
GPU1: [ idle    ] [ COMPUTE   ]
```

整个过程中总有一张 GPU 闲着。

这叫：

$$
\boxed{\text{pipeline bubble}}
$$

如果有 8 stages：

```text
GPU0 work
GPU1 wait
GPU2 wait
GPU3 wait
...
```

一开始 bubble 更惨。

---

# 31. Micro-batching 是怎么减少 Bubble 的？

把一个 batch：

$$
B
$$

切成：

$$
m
$$

个 micro-batches：

$$
B_1,B_2,\ldots,B_m.
$$

那么：

```text
time →

GPU0: B1  B2  B3  B4  ...
GPU1:     B1  B2  B3  B4 ...
```

GPU0 把 (B_1) 发给 GPU1 后：

> 不需要等 GPU1 完成。

直接开始算：

$$
B_2.
$$

于是 pipeline 被填起来。

Lecture 7 的 pipeline demo 就把 batch 切成多个 micro-batches 来减少 bubble。([GitHub][2])

---

# 32. Pipeline Bubble 可以定量理解

假设：

$$
P=\text{pipeline stages}
$$

$$
M=\text{micro-batches}.
$$

只看一个简化 forward pipeline，填充和排空造成大约：

$$
P-1
$$

个 bubble slots。

理想 utilization 大致：

$$
\boxed{
\frac{M}{M+P-1}
}
$$

例如：

$$
P=4,\quad M=1
$$

则：

$$
\frac1{1+3}=25%.
$$

惨。

如果：

$$
M=16
$$

则：

$$
\frac{16}{19}
\approx84%.
$$

所以：

$$
\boxed{\text{micro-batches 越多，bubble 比例越低}}
$$

当然 microbatch 太小以后，GEMM 本身又可能变得不够高效。

又一个 trade-off。

---

# 33. Forward + Backward 后，Pipeline 调度会更复杂

Lecture 7 的裸实现为了教学，只展示 forward，并明确说没有处理 communication/computation overlap，也把 backward 留作练习。([GitHub][2])

现实训练你还得安排：

```text
Forward microbatch 1
Forward microbatch 2
Backward microbatch 1
Forward microbatch 3
Backward microbatch 2
...
```

于是出现：

```text
GPipe
1F1B
interleaved schedules
zero-bubble pipeline
...
```

这些属于 Lecture 7 没有完全深入的下一层话题。

所以千万别把 Lecture 7 的 pipeline demo 当成完整工业 pipeline engine。

它主要是在教：

$$
\boxed{\text{depth sharding + point-to-point activation transfer}}
$$

---

# 34. 到这里可以做一张最重要的比较表

| 方法                | 切什么                  |         每 GPU 模型 |                每 GPU 数据 | 主要通信                        |
| ----------------- | -------------------- | ---------------: | ----------------------: | --------------------------- |
| DDP               | Batch                |               完整 |                   (1/P) | gradient all-reduce         |
| FSDP/ZeRO         | Model states + Batch |            shard |                   (1/P) | all-gather + reduce-scatter |
| Tensor Parallel   | Width                |      layer shard |               通常完整/组内相同 | frequent collectives        |
| Pipeline Parallel | Depth                | subset of layers | micro-batches 流过 stages | send/recv activations       |
| Expert Parallel   | Experts              |    expert subset |           routed tokens | all-to-all                  |
| Sequence Parallel | Sequence             |   sequence shard |         sequence subset | 取决于算子                       |

Lecture 7 自己深入实现的是前三个基础方向中的 DDP、TP、PP，并把 FSDP/ZeRO、sequence/expert 等作为总结和下一步。([GitHub][2])

---

# 35. 一个特别重要的统一视角：切的是“哪个 tensor dimension”

假设 activation：

$$
X\in\mathbb R^{B\times T\times D}
$$

模型有：

$$
L
$$

层。

那么：

## Data Parallel

切：

$$
B.
$$

```text
[B/P, T, D]
```

---

## Sequence Parallel

切：

$$
T.
$$

```text
[B, T/P, D]
```

---

## Tensor Parallel

切：

$$
D.
$$

```text
[B, T, D/P]
```

---

## Pipeline Parallel

切：

$$
L.
$$

每张卡拿：

$$
L/P
$$

层。

这就是最干净的理解。

所以所谓：

$$
\boxed{\text{3D parallelism}}
$$

一般就是同时沿多个模型/数据维度 shard，而不是某种神秘的新算法。

---

# 36. 为什么实际超大模型一定是 Hybrid Parallelism？

假设你有：

$$
1024\text{ GPUs}.
$$

你不会简单：

> “1024-way Tensor Parallel！”

因为那意味着：

$$
\boxed{\text{每一层都让 1024 GPU 高频通信}}
$$

网络直接炸掉。

更自然：

```text
8-way Tensor Parallel
×
8-way Pipeline Parallel
×
16-way Data Parallel

= 1024 GPUs
```

这只是一个示意。

于是：

## TP group

尽量在高速：

$$
NVLink/NVSwitch
$$

里面。

## PP

跨相对较慢连接也还能工作。

## DP

跨更多 nodes，用较粗粒度 gradient sync。

这就是：

$$
\boxed{\text{parallel strategy 必须匹配 hardware topology}}
$$

而不是只看数学。

---

# 37. 这和 Lecture 4 的 MoE 又重新接上了

Lecture 4 你已经学过：

$$
\boxed{\text{Expert Parallelism}}
$$

如果 64 experts 分布在 8 GPUs：

```text
GPU0: E0-E7
GPU1: E8-E15
...
```

router 后 token 要去 expert 所在 GPU。

于是：

$$
\boxed{\text{All-to-All}}
$$

Lecture 7 正式把这个通信 primitive 补上了。([GitHub][2])

所以前面：

> “MoE 通信很贵。”

现在你终于知道具体贵在哪里：

```text
router
 ↓
token permutation
 ↓
all-to-all
 ↓
expert compute
 ↓
all-to-all
 ↓
unpermute
```

而且如果 token distribution 不均匀：

```text
GPU0: 2000 tokens
GPU1: 100 tokens
```

整个 collective 还会受到 straggler/load imbalance 影响。

---

# 38. FSDP 为什么可以理解成“用通信换显存”？

这也是 Lecture 7 最值得提前建立的直觉。

DDP：

每张 GPU 永久存完整：

$$
\theta,\quad g,\quad optimizer\ states.
$$

FSDP：

平时只存：

$$
\boxed{\frac1P}
$$

份。

某一层需要 forward 时：

$$
\boxed{\text{All-Gather params}}
$$

算完以后：

> 可以重新 shard / free full parameters。

backward 得到 gradient：

$$
\boxed{\text{Reduce-Scatter gradients}}
$$

结果：

每张 GPU 又只保留自己的 shard。

于是：

$$
\boxed{
\text{memory}\downarrow
\quad\text{but}\quad
\text{communication}\uparrow
}
$$

这正是 Lecture 7 总结里的：

> 可以选择 recompute、留在 memory，或者放在另一个 GPU 的 memory 再通过 communication 获取。([GitHub][2])

你会发现 CS336 从 Lecture 2 开始所有优化本质都是：

$$
\boxed{\text{资源之间做交换}}
$$

---

# 39. 这三个选择特别值得记

假设有一个中间结果 (X)，之后还要用。

你可以：

### 方案 A：自己存

$$
\boxed{\text{memory}}
$$

例如 activation caching。

---

### 方案 B：不存，之后重新算

$$
\boxed{\text{compute}}
$$

例如 activation checkpointing / FlashAttention recomputation。

---

### 方案 C：存在别的 GPU，需要时拿过来

$$
\boxed{\text{communication}}
$$

例如 distributed sharding。

于是整个 ML Systems 可以浓缩成：

$$
\boxed{
\text{Compute}
\leftrightarrow
\text{Memory}
\leftrightarrow
\text{Communication}
}
$$

Lecture 7 的总结恰恰明确写出了这三种选择。([GitHub][2])

这其实是这一讲最深的一句话。

---

# 40. 为什么 Communication/Computation Overlap 如此重要？

Lecture 7 明确说它的 toy implementations 还没有处理：

$$
\boxed{\text{communication/computation overlap}}
$$

([GitHub][2])

假设：

```text
compute layer
  ↓
communicate
  ↓
compute next layer
  ↓
communicate
```

GPU 时间：

```text
COMPUTE ███████
COMM           ████
COMPUTE            ███████
```

通信期间 Tensor Cores 在闲着。

如果能：

```text
compute next thing
██████████████

communication previous thing
       ███████
```

那么：

$$
T_{\rm step}
$$

不再近似：

$$
T_{\rm compute}
+
T_{\rm communication}
$$

而可以接近：

$$
\boxed{
\max(
T_{\rm compute},
T_{\rm communication}
)
}
$$

这就是 overlap 的目标。

现代 DDP 会在某些 gradients ready 后就异步 all-reduce，而不是等完整 backward 全结束才一次性同步，这就是典型的 overlap。

---

# 41. 这也解释了为什么 Gradient Bucketing 存在

Transformer backward：

```text
Layer L gradient ready
↓
Layer L-1
↓
Layer L-2
...
```

如果等所有 gradient 算完：

```text
backward done
↓
all-reduce EVERYTHING
```

通信完全在 critical path。

更聪明：

```text
gradient bucket 1 ready
↓
async all-reduce bucket 1

与此同时
↓
继续 backward bucket 2
```

所以：

$$
\boxed{\text{communication 被 backward compute 隐藏}}
$$

Lecture 7 没有详细实现这一层，但它明确把 communication/computation overlap 列为当前裸实现缺失的重要内容。([GitHub][2])

这就是你以后看 PyTorch DDP bucket size 参数时真正应该想到的东西。

---

# 42. 为什么 TP 比 DP 更难 hide communication？

DP 的 all-reduce 通常发生在 backward，且可以和其他层 backward overlap。

TP 通常：

```text
matmul
↓
collective
↓
下一部分 matmul
```

communication 位于：

$$
\boxed{\text{forward/backward dependency critical path}}
$$

下一步必须等通信结果。

因此：

$$
\boxed{\text{TP communication latency 更敏感}}
$$

这就是为什么：

> TP degree 不是越大越好。

GPU 越多：

$$
\text{每 GPU compute}\downarrow
$$

但：

$$
\text{collective overhead proportion}\uparrow.
$$

最终 scaling efficiency 会下降。

---

# 43. 那什么时候优先用哪一种并行？

可以先用这个非常实用的判断。

## 模型能放进一张 GPU，只是想加速

先考虑：

$$
\boxed{\text{Data Parallel}}
$$

简单、扩展自然。

---

## 模型状态放不进去，但单层还能放

优先考虑：

$$
\boxed{\text{FSDP/ZeRO}}
$$

把 model states shard 掉。

---

## 单独一层就巨大

比如超大 FFN：

$$
W:[32768,131072]
$$

一层就很大。

考虑：

$$
\boxed{\text{Tensor Parallel}}
$$

---

## 模型非常深，希望切 layer stages

考虑：

$$
\boxed{\text{Pipeline Parallel}}
$$

---

## MoE experts 很多

考虑：

$$
\boxed{\text{Expert Parallel}}
$$

---

现实 hero training：

$$
\boxed{\text{全部组合}}
$$

---

# 44. Lecture 7 和 Lecture 6 的关系，其实特别漂亮

## Lecture 6

一个大 matmul：

$$
C=AB
$$

如果一张 GPU 内太大：

```text
切成 tiles
```

每个 tile 在不同 program/block 里处理。

---

## Lecture 7

一个大训练任务：

```text
模型 + batch
```

如果一张 GPU 不够：

```text
切成 shards
```

每个 shard 在不同 GPU/rank 里处理。

所以：

$$
\boxed{
\text{Tiling 是单 GPU 的 sharding}
}
$$

而：

$$
\boxed{
\text{Distributed parallelism 是跨 GPU 的 tiling}
}
$$

这不是官方术语，但作为 mental model 非常好。

两者核心都是：

> 切任务，然后处理“切块之后必要的数据交换”。

---

# 45. A2 为什么要你亲手做 distributed training？

2026 A2 README 明确要求你在 `cs336_systems` 里实现 optimized Transformer，并实现 distributed training/optimization。([GitHub][3])

这和 Lecture 7 完全对上。

如果只是调用：

```python
model = DistributedDataParallel(model)
```

你可能永远不知道：

> DDP 到底干了什么？

Lecture 7 给出的答案其实简单得令人吃惊：

```python
# 每张 GPU 用不同数据
loss.backward()

# 同步梯度
for p in params:
    dist.all_reduce(
        p.grad,
        op=AVG,
    )

optimizer.step()
```

([GitHub][2])

这就是最原始的 DDP。

工业 PyTorch DDP 在此基础上增加：

```text
bucketing
async collectives
overlap
autograd hooks
topology optimization
...
```

但底层思想没变。

---

# 46. 我特别希望你别把 DDP / FSDP / TP 三个概念混起来

可以只记一句：

## DDP

$$
\boxed{\text{模型 replicated，数据 sharded}}
$$

---

## FSDP

$$
\boxed{\text{数据 sharded，模型 states 也 sharded}}
$$

但计算某层时暂时 gather。

---

## TP

$$
\boxed{\text{一个算子本身就是 distributed}}
$$

例如：

$$
XW
$$

这个 matmul 的 (W) 就分布在多张卡上。

这三个区别极其重要。

---

# 47. 从“谁拥有完整 activation”也可以区分

## DDP

每个 rank：

```text
只处理自己 batch 的完整 hidden dimension
```

---

## TP

很多时候：

```text
同一个 batch
但 hidden/features 被多 GPU 分担
```

---

## PP

```text
同一 microbatch
在不同时间经过不同 GPU 的 layer ranges
```

这其实就是：

$$
\boxed{\text{不同 parallelism 改变了 tensor 的 ownership}}
$$

---

# 48. Lecture 7 自己没有深入哪些内容？

官方非常坦率地在结尾列出来了：

* communication/computation overlap；
* 完整 Transformer/attention；
* sequence parallelism；
* expert parallelism；
* 多种 parallelism 的组合；
* 更高级的 compiler-managed sharding。([GitHub][2])

所以 Lecture 7 的目标不是让你学完“大模型分布式训练所有知识”。

而是让你先真正掌握：

$$
\boxed{\text{collective primitives}}
$$

以及：

$$
\boxed{\text{batch / width / depth 三种基本切法}}
$$

下一讲才继续高级并行。

---

# 49. 我建议你把整个 Lecture 7 压成这张图

```text
                  一个超大训练任务
                         │
          ┌──────────────┼──────────────┐
          │              │              │
       batch           width          depth
          │              │              │
          ↓              ↓              ↓
         DP             TP             PP
          │              │              │
     all-reduce      collectives      send/recv
          │              │              │
          ↓              ↓              ↓
   throughput ↑      model fit ↑    model fit ↑


如果连 model state
也不想 replicate：

         DP
          ↓
      FSDP / ZeRO
          ↓
all-gather + reduce-scatter


如果是 MoE：

       Experts
          ↓
   Expert Parallel
          ↓
      all-to-all
```

这就是整堂课。

---

# 50. 最后给你 10 道 Lecture 7 自测题

如果这些你能独立解释，Lecture 7 基本就真懂了。

### 1. All-Gather 和 All-Reduce 有什么区别？

All-Gather：

$$
\boxed{\text{收集不同 shards，不做 reduction}}
$$

All-Reduce：

$$
\boxed{\text{先 reduce，再让每个 rank 拿到完整结果}}
$$

---

### 2. 为什么说：

$$
\boxed{
\text{All-Reduce}
=================

\text{Reduce-Scatter}
+
\text{All-Gather}
}
$$

最好亲手用 4 个 vectors 模拟一遍。官方也明确用这一关系连接 DDP 与 FSDP。([GitHub][2])

---

### 3. DDP 为什么 local loss 不同，最终参数却保持相同？

因为：

$$
g_r\text{ 不同}
$$

但：

$$
allreduce(g_r)=g
$$

之后每张 GPU 用相同 (g) update。

---

### 4. DDP 为什么不能解决“模型放不下单卡”？

因为：

$$
\boxed{\text{每张卡仍保存完整 model/optimizer states}}
$$

---

### 5. FSDP 为什么比 DDP 省显存？

因为：

$$
\boxed{\text{parameter / gradient / optimizer states shard}}
$$

需要完整参数时再 all-gather。

---

### 6. TP 为什么通常要求高速 NVLink？

因为 collective 发生频繁，往往位于每层 computation critical path。官方总结也明确强调这一点。([GitHub][2])

---

### 7. PP 为什么可以容忍慢一点的网络？

因为通常只在 stage boundary 传 activations，而不是每层内部频繁 collective。

---

### 8. Pipeline micro-batching 是解决什么问题？

$$
\boxed{\text{pipeline bubbles / idle GPUs}}
$$

---

### 9. MoE 为什么自然对应 All-to-All？

因为每个 GPU 的 token 可能被 route 到任何 GPU 上的 expert。

---

### 10. 一个 1024-GPU 训练任务为什么通常不会只选一种 parallelism？

因为：

$$
\boxed{
\text{不同 sharding dimensions 对 compute、memory、communication 的 trade-off 不同}
}
$$

需要根据硬件 topology 组合：

$$
DP\times TP\times PP\times EP\dots
$$

---

如果只让我在黑板上给 Lecture 7 留一句话，我会写：

$$
\boxed{
\textbf{Distributed training 的本质不是“多用几张 GPU”，
而是决定数据和模型分别放在哪里，
以及什么时候值得为它们支付通信代价。}
}
$$

而且从 Lecture 2 到 Lecture 7，现在其实已经形成了一条非常完整的 CS336 Systems 主线：

$$
\text{Lecture 2：}
\boxed{\text{Compute vs Memory}}
$$

$$
\text{Lecture 5：}
\boxed{\text{GPU 内数据怎么移动}}
$$

$$
\text{Lecture 6：}
\boxed{\text{通过 tiling/fusion 控制单 GPU 数据移动}}
$$

$$
\text{Lecture 7：}
\boxed{\text{通过 sharding/replication/collectives 控制跨 GPU 数据移动}}
$$

所以下一讲 Lecture 8 不再需要花大量时间解释“什么叫 all-reduce”，而可以直接进入真正的大模型训练问题：**ZeRO/FSDP、tensor/pipeline/sequence parallel 如何做得更精细，以及多种并行怎么组合才划算。**
