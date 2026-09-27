---
title: "L07 · Parallelism"
weight: 7
date: 2026-08-28
updated: 2026-09-16
course: "CS336"
topics: ["CS336", "distributed-training", "parallelism", "ddp", "tensor-parallel"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture7/
---

Lecture 6 讨论的是一张 GPU 内部的 kernel 如何分 block、读写 HBM 和利用 shared memory。Lecture 7 把同一个问题扩大到多张 GPU：计算单元和数据分开以后，怎样安排复制、切分与通信，才能让更多 GPU 真正参与训练。

这一讲的统一主题是：**计算离数据越远，搬运越贵。** 单 GPU 内部有 register、shared memory、L2 和 HBM；多 GPU 之间有 NVLink/NVSwitch；跨节点还要经过 InfiniBand 或 Ethernet。并行训练做的事情，就是在这些层级之间安排数据的复制和分片。

## 1. 从单 GPU 到数据中心：并行的对象变了

多 GPU 的需求通常来自两个原因：

1. parameters、gradients、optimizer states 或 activations 放不进一张 GPU。
2. 模型能放下，但希望利用更多 GPU 的 FLOPs 缩短训练时间。

上一个阶段的优化是 fusion、tiling 和 recomputation，尽量减少一张 GPU 内部的 memory traffic；这一讲要减少的是 GPU 与 GPU、节点与节点之间的 communication traffic。

可以把训练系统的层级写成：

```text
single GPU：register / shared memory / L2 / HBM
    ↓
single node：NVLink / NVSwitch
    ↓
multi-node：InfiniBand / Ethernet
```

![多 GPU 节点中的 GPU、HBM、NVLink、NVSwitch 与跨节点网络](/learning/cs336/lectures/l7-gpu-node-overview.png)

不同链路的带宽和延迟不同，决定了不同 parallelism 的放置位置：每层都要同步的 Tensor Parallelism 更适合留在节点内；跨层传递 activation 的 Pipeline Parallelism 可以使用较慢的跨节点链路；Data Parallelism 的梯度同步可以通过 bucket 和 overlap 尽量隐藏；MoE 的 token dispatch 则需要专门处理 all-to-all。

所以“多 GPU”不等于“一张更大的 GPU”。每张卡仍有独立的 HBM 和执行队列，跨卡的数据需要通过明确的通信 primitive 移动。

## 2. Collective Communication：先掌握 rank 和通信原语

一个分布式进程对应一个 rank，所有 rank 的数量叫 world size。例如 4 张 GPU 可以写成 rank 0、1、2、3，world size 为 4。

![4 个 rank 的分布式进程布局](/learning/cs336/lectures/l7-ranks.png)

Collective operation 不是手动管理每一对 GPU 的 `send()`/`recv()`，而是声明一个跨多个设备的通信模式。这样通信库可以根据拓扑选择更合适的路径，也更容易使用 ring、tree 或分层算法。

基础原语可以用 4 个 rank 的小向量记忆：

| 原语 | 输入 | 输出 | 典型用途 |
| --- | --- | --- | --- |
| Broadcast | root 有一份 | 所有 rank 得到同一份 | 广播 checkpoint 或配置 |
| Scatter | root 有完整向量 | 每个 rank 得到一片 | 分发 batch 或数据片 |
| Gather | 每个 rank 有一片 | root 得到完整向量 | 收集结果 |
| Reduce | 每个 rank 有一份 | root 得到 sum/min/max | 汇总局部结果 |
| All-Gather | 每个 rank 有一片 | 所有 rank 得到完整向量 | 收集参数分片 |
| Reduce-Scatter | 每个 rank 有完整贡献 | 每个 rank 得到归约结果的一片 | 分片梯度 |
| All-Reduce | 每个 rank 有局部贡献 | 所有 rank 得到完整归约结果 | DDP 同步梯度 |
| All-to-All | 每个 rank 给每个 rank 发一片 | 每个 rank 收到目标片 | MoE token routing |

最容易混淆的是 Gather、All-Gather、Reduce-Scatter 和 All-Reduce：

- Gather 只把所有片段送到 root，All-Gather 让每个 rank 都得到完整结果。
- Reduce 不只是拼接，还会执行 sum、min 或 max 等结合运算。
- Reduce-Scatter 先对各 rank 的贡献做归约，再把不同结果片段分给不同 rank。
- All-Reduce 可以理解成 Reduce-Scatter 加 All-Gather。

以 4 个 rank 的输入为例，Reduce-Scatter 会把每个位置的和分给对应 rank；All-Gather 再把这些结果片段传播回所有 rank，于是每张卡都拿到完整的归约向量。这个分解正是 ZeRO/FSDP 能够保持 gradient 或 parameter sharded 的基础。

All-to-All 的模式不同：rank 0 可能把第 0 片发给自己、第 1 片发给 rank 1、第 2 片发给 rank 2、第 3 片发给 rank 3，其他 rank 同样拆分。完成后，每个 rank 收到来自所有 rank 的对应片段；在均衡输入时，它看起来很像一次矩阵转置。MoE 中不同 GPU 保存不同 experts，router 就需要用 all-to-all 把 token 送到正确的 expert。

## 3. NVLink、NVSwitch、InfiniBand、RDMA 与 NCCL

现代 GPU 节点通常是多张 GPU 通过 NVLink 接入 NVSwitch，再由节点上的网络设备连接到其他节点。Lecture 7 用 B200 的量级说明层级差异：节点内 NVLink 约为 TB/s 级，HBM 带宽还要更高；跨节点 InfiniBand 明显更慢，Ethernet 通常又是另一层更慢的路径。具体数字会随硬件代际变化，稳定的结论是：**TP 需要高速互联，PP 可以容忍慢一些的网络，但要处理 bubble。**

普通网络通信可能经过 CPU 和 kernel socket buffer，数据需要在 GPU、CPU、NIC 之间多次复制。RDMA（Remote Direct Memory Access）允许一台设备直接读写远端设备的 memory，减少 CPU 参与；InfiniBand 原生支持 RDMA，RoCE 则让部分 Ethernet 网络也可以采用类似的 CPU-bypass 思路。

NCCL 位于硬件和 PyTorch 之间，主要做三件事：

- 检测 GPU、PCIe、NVLink、NVSwitch、节点和交换机组成的 topology；
- 为 all-reduce、all-gather 等 collective 选择通信路径和算法；
- 启动负责搬运数据的 GPU kernels，让通信尽量利用 GPU 之间的链路。

PyTorch 的 `torch.distributed` 提供了更高层的调用接口，例如 `all_reduce`、`reduce_scatter_tensor` 和 `all_gather_into_tensor`；GPU 上通常使用 NCCL backend，CPU 上可以使用 Gloo。Lecture 7 先直接调用这些 primitives，是为了让 DDP、FSDP 和更高层封装背后的通信动作可见。

## 4. Distributed Benchmark：测通信有效带宽，而不是只测时间

通信 benchmark 和 Lecture 6 的 GPU kernel benchmark 有同样的纪律：warmup、同步、重复测量，并明确数据量到底怎么算。一个简单的 all-reduce 测试可以是：

```python
dist.all_reduce(data, op=dist.ReduceOp.SUM)
torch.cuda.synchronize()
dist.barrier()

start = time.time()
dist.all_reduce(data, op=dist.ReduceOp.SUM)
torch.cuda.synchronize()
dist.barrier()
elapsed = time.time() - start
```

如果 tensor 大小是 `size_bytes`，world size 是 \(W\)，all-reduce 的发送和接收量可以粗略按：

$$
\text{sent bytes}
\approx
2\times\text{size\_bytes}\times(W-1).
$$

Reduce-Scatter 的输入是每个 rank 的一整片贡献，输出只保留结果的一片，理想情况下通信量约为 all-reduce 的一半；All-Gather 再补回另一半。因此 all-reduce 可以拆成 reduce-scatter 和 all-gather，两个阶段合起来的时间和数据移动量与 all-reduce 对应。

实际有效带宽不是“理论链路带宽”，还会受消息大小、world size、拓扑、NCCL 算法、同步等待和 kernel launch 影响。benchmark 的意义不是背一个固定 GB/s，而是判断某个 collective 是否接近当前拓扑能给出的上限，以及改动后通信是否真的变少。

## 5. Data Parallelism：切 batch，用 All-Reduce 保持参数一致

Data Parallelism 沿 batch 维度切数据。每张 GPU 保存完整模型，rank (r) 只处理本地 batch slice：

![Data Parallelism 沿 batch 维度切数据，每个 rank 保留完整层](/learning/cs336/lectures/l7-data-parallelism.png)

```text
每个 rank：完整 parameters + 自己的 batch slice
        ↓
本地 forward / backward
        ↓
All-Reduce gradients
        ↓
各 rank 用相同 gradient 更新参数
```

局部数据不同，所以每张 GPU 计算出的 local loss 可以不同；但在 backward 后，gradient 会通过 all-reduce 求平均或求和，所有 rank 得到相同的 gradient。只要 optimizer step 的规则和初始参数相同，下一步的 parameters 就仍然一致。

一个教学版 DDP 的关键区别只有一处：

```python
loss.backward()

for param in params:
    dist.all_reduce(param.grad, op=dist.ReduceOp.AVG)

optimizer.step()
```

Data Parallelism 的优点是实现简单，计算可以随 local batch 分摊，通信模式也规则。它的缺点是每张 GPU 都复制 parameters、gradients 和 optimizer states，模型状态的单卡内存没有随 GPU 数量下降；当 global batch 已经不能继续增大时，继续扩大 DP 还会遇到通信和泛化收益递减的问题。

## 6. Tensor Parallelism：切一层的宽度，换取每层通信

如果单个 layer 的权重矩阵就放不进一张 GPU，或者希望让一个 layer 使用多张 GPU 的计算单元，可以沿 hidden/width 维度切参数。假设一个矩阵的输出维度被切成 4 片，每个 rank 保存 (1/4) 的参数；同一个输入会被送到各 rank，rank 先计算 local activation，再用 all-gather 拼回完整 hidden。

![Tensor Parallelism 沿 layer 的 width 维度切分参数](/learning/cs336/lectures/l7-tensor-parallelism.png)

教学版 forward 可以写成：

```text
每个 rank：输入 x + 一片 W_r
        ↓
local x @ W_r
        ↓
all-gather local activations
        ↓
concat 得到完整 hidden
```

更完整的 Transformer TP 会结合 column-wise 和 row-wise 分片，让中间 activation 尽可能保持 sharded，并在必要处执行 all-reduce。常见的映射是：QKV projection 和 MLP up-projection 做 column-wise，attention output projection 和 MLP down-projection 做 row-wise；norm、router 等操作则需要根据 layout 决定是否 replicated 或配合 Sequence Parallelism。

TP 的优点是没有 Pipeline 的 bubble，单层计算可以同时使用多张 GPU；缺点是每个 layer 都可能产生 activation-sized collective。通信发生在训练的 critical path 上，且随着 TP degree 增大，单个矩阵 tile 变小，Tensor Core 利用率也可能下降。因此 TP 通常放在同一个 NVLink/NVSwitch 节点内，而不是随意跨节点扩展。

## 7. Pipeline Parallelism：切深度，用 micro-batch 填补空闲

Pipeline Parallelism 不切一层内部的矩阵，而是把连续的 layers 分给不同 rank：

![Pipeline Parallelism 沿模型深度切 layer stages](/learning/cs336/lectures/l7-pipeline-parallelism.png)

```text
rank 0：layer 0 ... layer k
        ↓ activation
rank 1：layer k+1 ... layer 2k
        ↓ activation
rank 2：...
```

它的通信是相邻 stage 之间的 activation point-to-point transfer。相比 TP 的每层 collective，PP 通信频率低，单次消息通常与 micro-batch activation 大小 \(b\times s\times h\) 同阶，更适合跨节点网络。

最朴素的 layer-wise training 会让 rank 0 做完 forward 后等待其他 rank 的 backward，很多 GPU 长时间空闲。Micro-batching 把一个 batch 切成多个 micro-batch：前一个 micro-batch 的 activation 送到下一 stage 后，当前 stage 可以立刻处理下一个。

当有 \(p\) 个 pipeline stages、\(m\) 个 micro-batches 时，理想化的 warm-up/flush bubble 比例约为：

$$
\frac{p-1}{m}.
$$

micro-batch 越多，bubble 相对越小，但 activation buffer 和调度复杂度会增加；global batch 太小或 stage 太多时，PP 可能比预期更慢。1F1B（one-forward-one-backward）等 schedule 会在 warm-up 后交错 forward/backward，减少 buffer 和等待，但不能消灭启动与排空阶段的 bubble。

Lecture 7 的教学实现主要展示 forward 和 micro-batch 的通信，真实系统还要处理 backward、gradient accumulation、通信/计算 overlap、重排 schedule 和异常恢复。这里的重点是理解切分维度和 bubble 来源，而不是把教学版代码当成工业 pipeline 的完整实现。

## 8. 用“切哪个 tensor dimension”统一理解并行策略

很多并行名词可以统一成“沿哪个维度切 tensor”：

| 策略 | 主要切分维度 | 每个 rank 主要拥有 | 需要同步或交换 |
| --- | --- | --- | --- |
| Data Parallel | batch | 完整模型、batch 分片 | gradients all-reduce |
| Tensor Parallel | hidden/width | 每层参数和 activation 分片 | layer 内 activation collective |
| Pipeline Parallel | depth/layers | 连续 layer stage | stage 间 activation |
| Sequence Parallel | sequence | pointwise activation 的 sequence 分片 | all-gather / reduce-scatter |
| Expert Parallel | experts/tokens | expert 子集 | token all-to-all |
| Context Parallel | long sequence/KV | 上下文片段 | KV/sequence exchange |

这张表也能解释 FSDP/ZeRO 的位置：它更像是在 parameter、gradient 和 optimizer-state 维度上做 sharding，通过 All-Gather 和 Reduce-Scatter 把需要的值临时取来，再及时释放。

FSDP 的核心不是让所有 rank 永久看到完整参数，而是让参数跟着计算图流动：

```text
parameter shard 常驻
        ↓ all-gather
当前 block 得到完整参数
        ↓ forward / backward
释放临时完整参数
        ↓ reduce-scatter gradient
gradient shard 常驻
```

对一个中间 activation，系统通常有三种选择：

1. 留在本地 memory，换取更多显存。
2. 不保存，之后 recompute，换取更多 FLOPs。
3. 存在另一张 GPU，需要时通过通信取回，换取通信带宽和延迟。

这些选择可以组合到 DDP、TP、PP、FSDP 和 activation checkpointing 中，真正的目标是让 memory、compute 和 communication 三者的瓶颈尽量错开。

## 9. Hybrid Parallelism：为什么超大模型不能只选一种策略

大模型训练通常是 hybrid parallelism。一个常见的组合是：

```text
节点内：TP / EP
跨节点：PP
更外层：DP 或 ZeRO
长上下文：SP / CP
MoE：EP + TP/CP + DP/PP
```

选择顺序可以按约束排查：

1. **模型状态放不进一张 GPU，但一层还能放下：** 先考虑 FSDP/ZeRO-3、PP 或二者组合。
2. **单独一层就太大：** 需要 TP，或 MoE 场景下使用 EP；TP 尽量限制在高速互联域内。
3. **模型很深、希望跨慢网络扩展：** PP 把 layer stages 分开，再通过足够 micro-batches 降低 bubble。
4. **activation memory 占主导：** 加入 SP、CP、FlashAttention、activation recomputation 或更合理的 micro-batch。
5. **MoE experts 很多：** 让 EP 负责 expert 维度，注意 token dispatch 的 all-to-all、capacity factor 和负载均衡。
6. **单个 replica 已经能训练：** 用 DP 扩展 replicas，但先确认 global batch 和 gradient synchronization 仍然值得。

通信/计算 overlap 是所有这些方案能否真正扩展的关键。参数 All-Gather 可以和当前 block 的计算重叠，gradient Reduce-Scatter 可以和后续 backward 重叠，pipeline 的 point-to-point 通信也可以与其他 micro-batch 的计算交错。Gradient bucketing 的作用，就是把已经准备好的多个小 gradient 聚成较大的通信包，减少 launch 次数，并尽早启动通信。

TP 比 DP 更难隐藏通信：DP 一般在一轮 backward 后同步 gradient，计算阶段可以保持相对独立；TP 的 collective 经常出现在每个 layer 的 forward/backward 中，容易直接落在 critical path 上。PP 的通信频率低一些，但需要用 schedule 解决 bubble；EP 的 all-to-all 则需要额外处理负载不均。

## 10. Lecture 6、Lecture 7 与 A2 的连接

Lecture 6 关注一张 GPU 内部的 `program_id`、tile、mask、load/store、reduction 和 `tl.dot`；Lecture 7 关注多个 GPU 之间的 rank、collective、process group、NCCL 和通信 benchmark。

两者的共同问题仍然是数据移动：

| 层级 | 主要问题 | 典型优化 |
| --- | --- | --- |
| 单 GPU | HBM 与 SM 之间移动太多 | fusion、tiling、coalescing、recomputation |
| 节点内多 GPU | layer 内同步太频繁 | TP、SP、NVLink/NVSwitch、overlap |
| 跨节点 | activation 或参数通信太慢 | PP、分层 DP、RDMA、bucket、schedule |
| MoE | token 要路由到不同 experts | EP、all-to-all、capacity/负载均衡 |

A2 让这些概念从教学版 MLP 走向 optimized Transformer 和 distributed training：你需要先确认数学结果正确，再确认参数/activation 的 shard mapping，最后用 benchmark 和 profiler 判断实际 step time、通信占比、显存和 tokens/s。只会调用 DDP 或只会写 Triton kernel，都还不足以解释一个完整训练 step 为什么快或慢。

## 面试复盘

1. **All-Gather 和 All-Reduce 有什么区别？** All-Gather 只是把各 rank 的分片拼起来并让所有 rank 得到完整结果；All-Reduce 还会先对各 rank 的输入执行 sum/min/max 等归约。

2. **为什么 All-Reduce 可以理解成 Reduce-Scatter + All-Gather？** Reduce-Scatter 先把全局归约结果分成不同片段交给各 rank，All-Gather 再让每个 rank 收集所有片段。

3. **DDP 为什么 local loss 可以不同，但最终参数仍然一致？** 每个 rank 的 batch slice 不同，所以 local loss 和未同步 gradient 可以不同；gradient all-reduce 后相同，optimizer step 又使用相同参数和相同梯度，因此参数保持一致。

4. **DDP 为什么不能解决模型放不下单卡？** DDP 复制完整 parameters、gradients 和 optimizer states，只切 batch，不降低单卡模型状态内存。

5. **FSDP/ZeRO 如何省显存？** 让 parameters、gradients 和 optimizer states 在 rank 间 sharded，计算某个 block 时临时 All-Gather，完成后释放并通过 Reduce-Scatter 保持分片。

6. **TP 为什么需要高速 NVLink？** TP 的通信通常出现在每个 layer 的 forward/backward，频率高且容易位于 critical path；低带宽跨节点链路会直接拖慢每层计算。

7. **PP 为什么可以容忍慢一点的网络？** 它主要在相邻 stages 之间传 activation，通信频率低于 TP；但需要足够 micro-batches 和合适 schedule 来降低 pipeline bubble。

8. **Pipeline micro-batching 解决什么问题？** 它让不同 stage 同时处理不同 micro-batch，提高设备利用率；bubble 比例大致随 \((p-1)/m\) 下降。

9. **MoE 为什么自然对应 All-to-All？** 每个 rank 保存一部分 experts，router 产生的 token 需要送到拥有对应 expert 的 rank，结果再返回原 token 所属的 rank。

10. **为什么 1024 张 GPU 的训练通常不会只选一种 parallelism？** batch、width、depth、sequence 和 experts 是不同的切分维度，且通信链路也有层级；混合 DP、TP、PP、SP/CP、EP 和 FSDP 才能同时满足内存、计算和通信约束。

Lecture 7 最应该留下的判断是：分布式训练不是简单地复制模型或把 GPU 数量加上去，而是为每种 tensor 选择合适的拥有者、通信原语和网络层级。数据留在哪里、什么时候复制、什么时候分片，以及通信能否被计算覆盖，才决定了多 GPU 训练是否真的有效。
