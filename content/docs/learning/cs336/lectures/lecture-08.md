---
title: "L08 · Parallelism"
weight: 8
date: 2026-08-28
updated: 2026-09-16
course: "CS336"
topics: ["CS336", "distributed-training", "parallelism", "fsdp"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture8/
---

Lecture 8 讨论的是：当模型已经放不进一张 GPU，或者一张 GPU 的计算吞吐已经不够时，应该怎样把训练拆到多张 GPU、多个节点上。这里的难点不只是“多买几张卡”，还包括参数、梯度、optimizer state、activation 和通信路径分别怎么分布。

前面的课程已经给出几块拼图：Lecture 2 估算参数与 activation 的内存，Lecture 5 解释 GPU 内存层级和通信代价，Lecture 6 让 kernel 尽量减少数据搬运。Lecture 8 把这些问题扩大到数据中心：哪些数据留在本地 GPU，哪些数据走 NVLink/NVSwitch，哪些数据必须跨节点走 InfiniBand，训练吞吐才不会被通信拖垮。

## 1. 数据中心才是大模型训练的计算单元

单卡 scaling 有两个直接限制。第一，模型的计算量会超过单卡可接受的训练时间；第二，参数、梯度、optimizer state 和 activation 的总内存会超过单卡容量。多 GPU、多节点并行的目标，是让可用内存和计算资源随 GPU 数量增长，同时把通信控制在可接受的范围内。

可以先把一个 GPU 节点想成四层结构：每张 GPU 有自己的 register、L1/shared memory、L2 和 HBM，GPU 之间通过 NVLink 接入 NVSwitch，节点再通过 InfiniBand 或 Ethernet 与其他节点连接。

![GPU 节点中的 SM、HBM、NVLink、NVSwitch 与跨节点网络](/learning/cs336/lectures/l8-slide-07-07.png)

这些链路的带宽和延迟不同，因此并行策略不能只看“需要多少 GPU”，还要看“哪一种数据需要频繁通信”：

- 高频、同步、activation-sized 的通信适合放在同一节点的高速互联域内，典型是 Tensor Parallelism。
- 跨层传递的 activation 是点对点通信，Pipeline Parallelism 可以把它放在较慢的跨节点链路上。
- 数据并行主要同步 gradients，通信频率高但结构规则，通常放在更外层并通过 bucketing、overlap 或 gradient accumulation 隐藏开销。
- MoE 的 token dispatch 是 all-to-all，Expert Parallelism 需要根据网络拓扑和 expert 负载单独设计。

训练系统因此需要同时追求两件事：参数和计算能分摊到更多设备，collective communication 又不能成为每一层的同步栅栏。

## 2. Collective Communication：先把通信账算清楚

Lecture 8 先复习几个 collective primitive：

| 操作 | 输入状态 | 输出状态 | 常见用途 |
| --- | --- | --- | --- |
| All-Reduce | 每个 rank 都有一份局部向量 | 每个 rank 都得到求和结果 | DDP 同步 gradients |
| Reduce | 多个 rank 提供输入 | 一个 root 得到求和结果 | 汇总到指定设备 |
| Broadcast | root 有输入 | 所有 rank 得到同一份数据 | 发布参数或控制信息 |
| All-Gather | 每个 rank 有一片 | 所有 rank 得到完整拼接结果 | 收集参数分片 |
| Reduce-Scatter | 每个 rank 有完整输入的一部分贡献 | 每个 rank 得到结果的一片 | ZeRO/FSDP 梯度分片 |

All-Reduce 可以理解成 Reduce-Scatter 加 All-Gather：先把求和结果分片，再把每一片传播给所有 rank。在带宽受限的理想情况下，这种分解接近最有效的通信方式；它也是 ZeRO/FSDP 能把“同步完整梯度”改写成“每个 rank 只保留一片”的基础。

通信拓扑会改变这些 primitive 的成本。GPU 内部和节点内通常有高带宽的 NVLink/NVSwitch；跨节点则更多依赖 InfiniBand。规则的 mesh 或环形结构适合结构化的 collective，tree 或更灵活的 all-to-all 网络则更适合专家路由等不规则通信。并行策略的选择，本质上是在计算图、数据分片和网络拓扑之间做匹配。

## 3. Naive Data Parallelism：计算容易扩展，模型内存没有扩展

最简单的数据并行是让每张 GPU 保存完整模型，然后把一个 global batch 切成 \(M\) 份，每张 GPU 处理自己的 micro-batch：

```text
每张 GPU：完整参数 + 一份 batch 分片
        ↓
本地 forward / backward
        ↓
All-Reduce gradients
        ↓
每张 GPU 用相同 gradients 更新完整模型
```

计算方面，单步工作量大约可以随着 GPU 数量分摊；通信方面，每一步都需要同步梯度。理想情况下，梯度通信量和参数量同阶，global batch 也需要足够大，才能让每张 GPU 的计算覆盖通信。

![Naive data parallelism：每张设备保存完整层，只切分输入数据](/learning/cs336/lectures/l8-slide-17-17.png)

真正的问题是内存。以混合精度 Adam 训练为例，每个参数可能同时需要：

- 2 bytes 的 FP16/BF16 model parameter；
- 2 bytes 的 FP16/BF16 gradient；
- 4 bytes 的 FP32 master weight；
- 4 或 2 bytes 的 Adam first moment；
- 4 或 2 bytes 的 Adam second moment。

常见的粗略账法是每个参数约 16 bytes，或者在更节省的 BF16 配置下约 12 bytes。关键在于，naive DDP 在每个 rank 上复制了这些状态，所以 GPU 数量增加并不会降低单卡 parameter memory。

## 4. ZeRO-1、ZeRO-2、ZeRO-3：逐步切分状态、梯度和参数

ZeRO 的核心思路是：既然不同 rank 最后只需要负责更新不同的参数分片，就不必让每个 rank 永久保存所有训练状态。计算图仍然可以局部执行，通信则在“需要使用完整值”和“完成局部更新”之间插入。

**ZeRO-1：只切 optimizer states。** 每个 rank 仍保存完整 parameters 和 gradients，但只保存自己负责的 optimizer state 分片。一步训练可以写成：

1. 每个 rank 用自己的 batch 分片计算完整 gradient。
2. Reduce-Scatter gradients，把每个参数的更新责任分给对应 rank。
3. 每个 rank 只用自己的 gradient 分片和 optimizer state 更新参数分片。
4. All-Gather 更新后的参数，让下一轮 forward 每个 rank 又能看到完整参数。

相较于 naive DDP，通信形式从一次 all-reduce 变为 reduce-scatter 加 all-gather，带宽受限时通信量仍大致是 \(2\times\#\text{params}\)，但 optimizer memory 按 GPU 数量分摊。

**ZeRO-2：同时切 gradients。** backward 计算某一层的 gradient 后，立即把它 reduce-scatter 到负责对应参数的 rank，并释放本 rank 不再需要的完整 gradient。这样不会长期实例化完整 gradient vector，但每个 rank 仍然需要在计算当下产生局部梯度。

**ZeRO-3 / FSDP：连 parameters 也切分。** 每个 rank 只常驻自己负责的参数、梯度和 optimizer state；forward 或 backward 走到某个 FSDP block 时，临时 All-Gather 该 block 的参数，计算完成后释放；backward 产生的梯度再 Reduce-Scatter 回各 rank。参数不再全程复制，而是按计算图的需要流动。

![ZeRO-3 / FSDP 将 parameters、gradients 和 optimizer states 全部分片](/learning/cs336/lectures/l8-slide-24-24.png)

ZeRO-3 的代价是通信量从 DDP/ZeRO-1、2 的约 \(2\times\#\text{params}\) 增加到约 \(3\times\#\text{params}\)：forward/backward 需要参数 All-Gather，梯度需要 Reduce-Scatter。它能显著降低单卡参数内存，但必须依赖通信计算 overlap、prefetch 和合适的 bucket，才能避免 GPU 等待参数。

以 8 张 A100 80GB、纯 BF16 训练的讲义估算为例，最大可容纳的参数规模大致从 baseline 的 6.66B，提升到 ZeRO-1 的 16B、ZeRO-2 的 24.62B 和 ZeRO-3 的 53.33B。具体数字依赖 master weight、optimizer dtype、activation 和临时 buffer；这个表真正要说明的是分片状态如何改变每参数内存，而不是给所有模型一个固定上限。

## 5. FSDP 的关键：让通信和计算重叠，而不是等待完整模型

FSDP 的“分片参数”并不意味着每一层计算前都停下来等待一次完整通信。实际系统会把模型包成 FSDP block，并在当前 block 计算时提前 All-Gather 后续 block 的参数；当前 block 的 backward 产生梯度后，也可以把 Reduce-Scatter 与其他计算重叠。

可以把一个两层结构的执行想成：

```text
prefetch W1 ──→ forward W1 ──→ free W1
                    │
                    └── prefetch W2 ──→ forward W2

backward W2 ──→ reduce-scatter grad(W2)
backward W1 ──→ reduce-scatter grad(W1)
```

通信和计算只有在流水化、bucket 化之后才有机会重叠；如果参数太小、网络太慢、bucket 切得不合适，All-Gather latency 就会暴露出来。FSDP 的实际性能因此取决于参数分片方式、wrap 粒度、prefetch、通信 stream 和 activation checkpointing，不是只打开一个 wrapper 就能获得理想 scaling。

ZeRO-3 仍然不能解决所有内存问题。它主要切分 parameter、gradient 和 optimizer state；activation memory 仍然会随 batch size、sequence length 和 hidden size 增长。模型继续变大后，必须引入 model parallelism，把计算图本身拆到不同 GPU。

## 6. Pipeline Parallelism：沿深度切模型，但要付 Bubble 代价

Layer-wise parallelism 把连续的网络层分给不同 GPU。它能降低每张 GPU 的 parameter memory，但如果一次只处理一个 batch，前面的 GPU 做完 forward 后就会等待后面的 GPU 完成 backward，大部分时间处于空闲状态。

Pipeline Parallelism 用 micro-batches 填充流水线：第一个 stage 处理 micro-batch 0 后，把 activation 发给下一个 stage，同时开始处理 micro-batch 1。不同 stage 可以并行处理不同 micro-batch，通信是相邻 stage 之间的 activation point-to-point transfer，规模约为 \(b\times s\times h\)，通常比每层 all-reduce 更适合跨节点链路。

![Pipeline parallelism 用多个 micro-batch 填充不同网络 stage](/learning/cs336/lectures/l8-slide-34-34.png)

Pipeline 的代价是 bubble。对 \(n_{\mathrm{stages}}\) 个 stage、\(n_{\mathrm{micro}}\) 个 micro-batch，理想化的 bubble 与有效计算比例约为：

$$
\frac{n_{\mathrm{stages}}-1}{n_{\mathrm{micro}}}.
$$

micro-batch 越少、stage 越多，空闲比例越高；因此 pipeline 通常需要足够大的 global batch，或者通过 gradient accumulation 产生更多 micro-batches。

1F1B（one-forward-one-backward）等 schedule 会在 warm-up 后交错 forward 和 backward，减少 activation buffer 和等待时间，但不会凭空消除 bubble。Interleaved schedule 可以进一步切分 virtual stages，用通信和调度复杂度换取更高利用率。

Zero-Bubble Pipeline 的关键观察是 backward 不必作为一个不可分割的操作：它可以拆成传递 activation gradient 的部分和计算 weight gradient 的部分。只要依赖关系允许，weight-gradient 计算可以填入原本的空隙，用更多调度复杂度换更少 bubble。

## 7. Tensor Parallelism：沿宽度切一层，换取高频通信

Pipeline 沿模型深度切层，Tensor Parallelism 则在一层内部切矩阵。以两块 GPU 为例，可以把线性层的权重按列或按行切分。不同 GPU 计算局部矩阵乘法，再通过 all-reduce 或 all-gather 得到完整输出。

在 Megatron 风格的线性层中，可以用两个抽象通信算子描述 forward/backward：forward 中一个算子是 identity，另一个算子执行 all-reduce；backward 时两者角色交换。这样做的好处是没有 pipeline bubble，模型层可以同步推进；代价是每个 Transformer block 都可能有 activation-sized collective。

![Tensor parallelism 将线性层的权重按子矩阵分配给不同 GPU](/learning/cs336/lectures/l8-slide-40-40.png)

Transformer 中常见的切法是：

| 模块 | 常见切分 | 原因 |
| --- | --- | --- |
| QKV projection | column-wise | 每个 GPU 计算一部分输出通道 |
| MLP up-projection | column-wise | 局部 GeLU 后可以继续保留分片 |
| Attention output projection | row-wise | 汇总各 GPU 的 partial output |
| MLP down-projection | row-wise | 对 column-wise hidden 做归并 |
| LayerNorm、router 等 | 通常 replicated 或配合其他并行 | 需要根据 shape 和通信代价决定 |

TP 适合放在同一节点内，利用 NVLink/NVSwitch 的高带宽和低延迟。讲义给出的经验是：Pipeline 每个 micro-batch 主要传相邻 stage 的 \(bsh\) activation；Tensor Parallelism 则在每层触发多次 activation-sized collective，通信更频繁。TP degree 不是越大越好，超过节点内高速互联域后，跨节点 latency 往往会迅速暴露。

## 8. Activation Parallelism：Sequence、Context 与 Expert

参数分片解决后，activation memory 会成为新的瓶颈。对 Transformer layer，attention 中的二次项可以通过 FlashAttention 或 activation recomputation 降低；但 LayerNorm、Dropout 和 attention/MLP 输入等逐 token 操作仍然会产生与 \(sbh\) 成正比的 activation。Tensor Parallelism 主要切矩阵乘法，剩下的 pointwise activation 仍可能在每个 rank 上复制。

**Sequence Parallelism。** 这些 LayerNorm、Dropout 和其他 pointwise 操作沿 sequence 维度独立，因此可以把 sequence shard 到 TP ranks。forward 中通过 all-gather 和 reduce-scatter 在 Tensor Parallel 与 Sequence Parallel 区域之间切换，backward 使用相反的通信顺序。这样既保留 TP 的矩阵切分，又让非矩阵操作的 activation 按 sequence 分片，最终让 activation memory 更接近线性随设备数下降。

![Sequence parallelism 将 pointwise 操作沿 sequence 轴切分，并与 Tensor Parallelism 交替](/learning/cs336/lectures/l8-slide-48-48.png)

Sequence Parallelism 和 Context Parallelism 不完全相同：前者主要服务于 TP 结构中 LayerNorm/Dropout 等 activation 分片；后者面向长上下文，把更长的 sequence 或 KV 工作分配到不同 GPU。

**Context Parallelism / Ring Attention。** 长序列下，一张 GPU 不需要保存完整 sequence 的所有 attention 状态。可以把 Q、K、V 或 KV cache 沿 sequence 维度切分，让 GPU 在环上交换 KV tile；每张 GPU 用本地 Q 和当前收到的 K/V tile 做局部 attention，再用 online softmax 的统计量合并结果。这里会重新用到 Lecture 5 的 FlashAttention：tile 计算和在线归一化让上下文可以分块处理，通信则按环逐步推进。

**Expert Parallelism。** MoE 的 MLP 层天然提供了另一个切分维度：不切同一个大矩阵，而是把不同 experts 放到不同 GPU，router 把 token dispatch 到对应 expert，计算完成后再把输出送回原 token 所属的 rank。EP 的通信通常是 all-to-all，但它避免了把每个 expert 的矩阵都复制到所有 GPU。

EP 特别适合 MoE 的 expert 层，因为 MoE 的 attention 部分通常仍然需要 TP/CP，而 MLP experts 可以单独按 expert 维度分片。TP 太大时会把每个矩阵切得过细，Tensor Core 利用率下降；EP 则可以保留每个 expert 较大的矩阵，代价是 token dispatch 和负载均衡。

## 9. 组合并行：把通信放在它最能承受的网络上

没有一种并行策略能同时解决 parameter memory、activation memory、compute scaling、batch scaling 和通信效率。实际训练通常组合 DP、TP、PP、SP/CP、EP 与 ZeRO：

| 维度 | 切分对象 | 主要通信 | 适合放置的位置 |
| --- | --- | --- | --- |
| DP / ZeRO | batch、optimizer/gradient/parameter state | gradient 或 parameter collective | 更外层，可跨节点 |
| TP | layer 内的矩阵 | 每层 activation collective | 节点内高速互联 |
| PP | layer depth | stage 间 activation point-to-point | 可跨节点 |
| SP | sequence-side pointwise activation | all-gather / reduce-scatter | 与 TP 绑定 |
| CP | 长 sequence / KV 工作 | sequence-side exchange | 长上下文阶段 |
| EP | MoE experts 和 token | all-to-all dispatch | 需要专门的负载均衡和网络 |

典型规则是：先用 TP 或 EP 在一台机器内把模型切到能运行，再用 PP 跨机器把模型深度切开，最后用 DP 扩展 global batch。若 batch size 不够大，可以使用 gradient accumulation 增加 micro-batch 数，换取更好的通信摊销。

![3D/4D parallelism：TP/EP 先解决单机内存，PP 跨机器，DP 扩展剩余规模](/learning/cs336/lectures/l8-slide-57-57.png)

为什么经验上经常先把 TP 扩到 8，然后停止？因为很多节点恰好有 8 张 GPU，节点内 NVLink 的带宽远高于跨节点网络；继续增大 TP 会把每层高频 all-reduce 推到慢链路上。模型继续放不下时，增加 PP stage 往往比继续扩大 TP 更稳；剩余 GPU 再用 DP 复制并行组。

Data Parallelism 通常放在最后，是因为它增加的是 replicas 和 global batch，而不是直接降低单个 replica 的层内计算。若 global batch 已经接近可接受上限，继续扩大 DP 只能增加通信和优化难度，吞吐未必继续线性增长。

## 10. 真实模型案例与选择方法

Lecture 8 的案例表显示，不同模型会根据 dense/MoE、上下文长度、batch size、网络拓扑和训练阶段选择不同组合。可以把课件中的已给出配置整理为：

| 模型/配置 | DP | TP/SP | EP | PP | CP | 观察 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Llama 3 405B | 128 | 8 | 0 | 16 | 1 | dense 模型用 TP + PP，再用较大的 DP |
| Gemma 2 | 768 | 8 | 0 | 0 | 0 | 模型规模和节点资源允许时，主要使用 TP + DP |
| Mixtral 8x22B | 2 | 4 | 8 | 4 | 1 | MoE 同时使用 EP、TP、PP 和 DP |
| Nemotron 3 120B 长上下文 | 未给出 | 2 | 64 | 未给出 | 64 | 长上下文和 MoE 分别需要 CP 与 EP |
| Qwen 3 MoE 配置 | 未给出 | 2 | 32 | 8 | 1 | expert 维度较大，PP/EP 共同扩展 |

课件还展示了 DeepSeek、Yi 等训练配置：DeepSeek 系列使用 ZeRO-1 配合 Tensor/Sequence/Pipeline Parallelism，DeepSeek-V3 的 EP 规模很大并需要 all-to-all overlap；Yi 则展示了在不同阶段用 TP 或 EP 替换的取舍。表中的 `??` 不是需要补猜的数字，而是提醒你：公开案例经常只披露部分并行度，选择并行方案还需要结合 batch、sequence length、网络和实现细节。

实际设计时可以按这个顺序排查：

1. **模型能否在单个 parallel replica 中放下？** 先算 parameters、gradients、optimizer states 和 activation memory。
2. **哪一种 memory 占主导？** parameter memory 优先考虑 ZeRO/FSDP、TP、PP 或 EP；activation memory 则看 SP、CP、checkpointing 和 sequence length。
3. **通信最频繁的对象是什么？** 每层 activation collective 倾向 TP，跨层 activation 倾向 PP，gradients/replica 同步倾向 DP，token dispatch 倾向 EP。
4. **通信会走哪条链路？** 高频同步尽量留在 NVLink/NVSwitch；跨节点尽量用 PP 或可 overlap 的 DP/EP 通信。
5. **global batch 是否足以填满 pipeline？** 如果 micro-batch 太少，PP bubble 会抵消并行收益。
6. **矩阵 tile 是否仍然足够大？** TP/EP 过度切分后可能让 Tensor Core 利用率下降。
7. **改动后是否真的测过？** 需要同时看 step time、tokens/s、每 GPU utilization、通信占比和峰值显存。

Activation recomputation 在这里再次出现：重算会增加 FLOPs，但如果它释放的显存让 global batch 或 micro-batch 数变大，就可能减少 pipeline bubble、提高通信摊销，最终提升整体 throughput。单独看一个 layer 的计算时间，无法判断这个 trade-off 是否划算。

## 面试复盘

1. **为什么 naive DDP 不能解决大模型内存问题？** 每张 GPU 都复制 parameters、gradients 和 optimizer states；GPU 数量增加只分摊 batch，不分摊单卡模型状态。

2. **ZeRO-1、ZeRO-2、ZeRO-3 分别切什么？** ZeRO-1 切 optimizer states，ZeRO-2 再切 gradients，ZeRO-3/FSDP 连 parameters 也切；后者需要按计算图临时 All-Gather 参数。

3. **ZeRO-3 为什么通信更多却仍然有价值？** 它用约 \(3\times\#\text{params}\) 的参数/梯度通信换取 parameters、gradients 和 optimizer states 的单卡分片，关键在于通信与计算 overlap。

4. **Pipeline Parallelism 的 bubble 从哪里来？** 流水线启动和排空时，不同 stage 还没有足够 micro-batch 可以同时工作；理想化 bubble 比例约为 \((n_{\mathrm{stages}}-1)/n_{\mathrm{micro}}\)。

5. **为什么 TP 通常放在节点内？** TP 每层都需要 activation-sized collective，通信频繁且同步；NVLink/NVSwitch 的带宽和延迟更适合这种模式，跨节点后成本会迅速上升。

6. **Sequence Parallelism 和 Context Parallelism 的区别是什么？** SP 主要把 TP 结构中的 LayerNorm/Dropout 等 pointwise activation 沿 sequence 切分；CP 面向长上下文，把 sequence 或 KV 计算跨 GPU 交换。

7. **为什么 MoE 更适合 Expert Parallelism？** experts 本身提供天然分片维度；把 token 路由到 expert 可以避免每张 GPU 复制所有 expert 矩阵，但要承担 all-to-all dispatch 和负载均衡。

8. **如何组合 DP、TP、PP、EP？** 高频、同步的 TP/EP 通信放高速域内，PP 跨节点切深度，DP 最后扩展 replica 和 global batch；具体组合要由 memory、batch、shape 和网络共同决定。

9. **为什么 activation recomputation 可能提高 throughput？** 它用额外 FLOPs 换显存，释放出的显存可以增加 micro-batch 或 global batch，减少 pipeline bubble 并改善通信摊销。

10. **看到 GPU 数量增加但 tokens/s 不再线性增长，先查什么？** 查通信是否跨出高速互联域、TP collective 是否成为同步瓶颈、PP bubble 是否变大、DP batch 是否已经达到上限，以及每个 rank 的实际矩阵 shape 和负载是否均衡。

Lecture 8 最核心的判断是：并行策略不是把所有维度都开到最大，而是把参数、activation、batch 和通信分别放到合适的切分维度，再让最频繁的通信留在最快的网络里。
