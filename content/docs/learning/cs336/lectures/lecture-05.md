---
title: "L05 · GPU"
weight: 5
date: 2026-08-28
updated: 2026-09-16
course: "CS336"
topics: ["CS336", "gpu", "distributed-training"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture5/
---

Lecture 5 讨论的是一个很具体的问题：同样的数学公式，为什么换一种写法，GPU 上的速度可能差一个数量级？答案通常不在 FLOPs 本身，而在数据怎样从 HBM 进入计算单元、一个数据能被复用多少次，以及中间结果是否被反复写回显存。

前几讲的关系可以先这样记：Lecture 2 估算模型需要多少计算和内存，Lecture 3 解释 Transformer 的数学结构，Lecture 4 讨论怎样修改模型或 attention 结构来少算一些；Lecture 5 则追问这些计算如何落到真实的 GPU 上。后面的 Lecture 6 和 Assignment 2 会把这里的直觉落实成 Triton kernel、benchmark 和 profile。

## 1. GPU 的执行模型：用吞吐量换取大规模并行

CPU 和 GPU 的目标不同。CPU 关注的是单个线程的 latency：一个任务能不能尽快结束。因此它愿意花较多芯片面积放置复杂控制逻辑、branch prediction、out-of-order execution 和大 cache，再配少量但很强的核心。GPU 关注的是 throughput：单位时间内总共处理多少数据，因此把芯片面积更多地用于大量较小的计算单元，并接受单个线程不一定很快。

![CPU 和 GPU 分别针对 latency 与 throughput 设计](/learning/cs336/lectures/l5-slide-08-08.png)

例如，下面的一百万个元素互相独立，GPU 很适合把它们分给大量线程：

```python
for i in range(1_000_000):
    y[i] = x[i] * 2
```

相反，下面这种每一步都依赖前一步结果、并且有很多分支的流程，就不容易充分利用 GPU：

```text
做 A
看结果
if ...
做 B
又看结果
if ...
做 C
```

NVIDIA GPU 的硬件层级可以用四个词串起来：

- **SM（Streaming Multiprocessor）**：一块可以独立承接计算工作的执行岛，内部有 warp scheduler、普通算术单元、Tensor Core、register file 和 shared memory/L1。
- **Block**：一组线程。一个 block 会被调度到某个 SM 上，同一 block 内的线程可以使用 shared memory 做协作。
- **Warp**：硬件调度和执行线程的重要单位，NVIDIA GPU 上通常包含 32 个连续编号的线程。
- **Thread**：逻辑上的最小工作者，例如让 thread `i` 负责计算 `y[i]`。

启动一个包含 1000 个 block、每个 block 有 256 个线程的 kernel，逻辑上会产生 256000 个线程；每个 block 再被拆成 8 个 warp。block 是资源和协作边界，warp 是同步执行边界，SM 是实际承接 block 的硬件位置。

![Thread、Block、Warp、SM 在 GPU 执行模型中的关系](/learning/cs336/lectures/l5-slide-11-11.png)

GPU 采用 SIMT（Single Instruction, Multiple Threads）模型。同一个 warp 中的 32 个线程通常执行同一条指令，只是读写不同的输入。例如 `y[i] = x[i] * 2` 可以让 thread 0 访问 `x[0]`，thread 1 访问 `x[1]`，依此类推。

这也解释了 control divergence。假设一个 warp 的前 16 个线程进入分支 A，后 16 个线程进入分支 B：

```text
先执行 A：前 16 个线程工作，后 16 个线程闲置
再执行 B：前 16 个线程闲置，后 16 个线程工作
```

硬件仍然可以完成这段代码，但两个分支往往要分开执行，warp 内的并行度就被打折。这里的问题不是分支“算错了”，而是同一个 warp 不能同时高效执行两条不同的控制路径。

## 2. 内存层级、Arithmetic Intensity 与 Roofline

GPU 的计算单元并不直接面对一种统一的 memory。粗略的速度和容量层级是：

```text
register
    ↓
shared memory / L1
    ↓
L2 cache
    ↓
HBM / global memory
```

越靠近 SM 的存储通常越小、越快，也越难分配；HBM 容量较大，但把数据搬到计算单元的代价仍然很高。一个 block 内的线程可以共享 shared memory，而跨 block 的数据通常要通过 global memory 读写。优化 GPU kernel 时，真正要追踪的是每个值在哪一级存储，以及它是否被不必要地搬回 HBM。

这就是 Lecture 2 的 arithmetic intensity 在硬件上的落地。设一个操作需要完成 \(F\) 个 FLOPs，并从显存传输 \(B\) 个 bytes，则：

$$
AI = \frac{F}{B}.
$$

Roofline 模型把可达到的性能近似写成：

$$
P = \min(P_{\mathrm{peak}},\ BW \times AI).
$$

当 \(BW\times AI\) 小于峰值算力时，kernel 是 memory-bound；继续增加 Tensor Core 只会让计算单元更多地等待数据。当 \(AI\) 足够高，性能才可能进入 compute-bound 区域，此时提高峰值 FLOP/s 才有直接收益。

一个简单的例子是对 bf16 向量执行 `y = x + 1`。每个元素至少要读 2 bytes、写 2 bytes，而计算只有一次加法，因此大约只有 \(1/4\) FLOP/byte。GPU 大部分时间花在搬运 `x` 和 `y`，而不是执行 `+1`。这种 elementwise 操作即使 GPU 利用率没有达到宣传的峰值，也可能已经接近自己的 Roofline 上限。

矩阵乘法更容易提高 arithmetic intensity。对于：

$$
C = AB,
\qquad
A\in\mathbb R^{M\times K},
\qquad
B\in\mathbb R^{K\times N},
$$

计算量约为 \(2MKN\) FLOPs。一个 \(A_{ik}\) 会参与多个 \(C_{ij}\)，一个 \(B_{kj}\) 也会被多个输出复用。只要把一小块 A、B 从 HBM 搬进 shared memory 或 register，就可以让同一份数据参与很多次乘加，单位数据带来的计算量就会上升。

现代 GPU 还为这种工作负载提供了专门的 Tensor Core，用来高吞吐地执行小块矩阵乘加：

$$
D = AB + C.
$$

大的 GEMM 会被拆成许多小 tile，再交给 Tensor Core。于是 FP32 的普通标量运算、BF16/FP16 的 Tensor Core 运算和 FP8 的低精度运算，吞吐量并不在同一个量级。硬件并不会对所有数学运算一视同仁，它明显偏爱规则的矩阵乘法。

TPU 的高层直觉也类似：轻量控制、强矩阵乘法单元、片上快速存储和 HBM。GPU 更通用，拥有 threads、warps 和 blocks；TPU 则把更多硬件资源直接押在矩阵乘法上。两者共同说明了现代 ML accelerator 的基本方向：让 fast matrix multiply 尽量从 fast local memory 得到数据。

计算吞吐增长快于内存带宽增长，就会出现 memory wall：

$$
\frac{\text{peak FLOP/s}}{\text{memory bandwidth}}
\uparrow
\quad\Rightarrow\quad
\text{每个 byte 必须支撑更多计算}.
$$

所以 GPU 越新，数据复用和内存访问顺序往往越重要。

## 3. 六个 GPU 优化开关：少搬数据，让数据留在片上

课程把常见优化浓缩成六类。control divergence 主要影响执行效率，其余几类大多直接减少内存流量、增加复用，或用更便宜的计算替代昂贵的数据读写。

![GPU workload 的六类常见优化：分支、低精度、融合、重算、合并访问和 tiling](/learning/cs336/lectures/l5-slide-22-22.png)

**低精度计算。** 对同一个 tensor，FP32、BF16、FP8 分别占 4、2、1 bytes。降低精度同时减少显存容量和带宽需求，现代 Tensor Core 对低精度矩阵乘法通常也有更高吞吐。以一个逐元素 ReLU 为例，FP32 读写一个元素需要约 8 bytes，若只计算一次比较和一次写回，强度约为 8 bytes/FLOP；换成 FP16 后，读写约 4 bytes，强度和带宽压力都减半。实际训练常采用低精度输入、高精度累加的混合方案，以控制数值误差。讲义还提到 FP8 的 MXFP8、MXFP4 等格式：不同 block 使用 scaling factor，格式设计会直接影响转置、缩放和 kernel 实现。

**Operator fusion。** 下面的计算在数学上很简单：

```python
a = x * x
b = torch.sin(a)
c = b + 1
```

如果每一步都启动一个 kernel，中间的 `a`、`b` 会反复经历 `HBM -> SM -> HBM`。融合后的 kernel 可以在加载 `x` 后连续完成平方、正弦和加法，只在最后写出 `c`：

```text
load x
  ↓
x * x → sin → +1
  ↓
store c
```

中间值停留在 register 或 shared memory，减少了 kernel launch 和 HBM intermediate traffic。`torch.compile` 能自动发现一部分这类融合，但 RMSNorm 这种 `square -> mean -> rsqrt -> multiply` 的组合是否高效，最终仍取决于生成的 kernel 是否把中间结果留在片上。

**Recomputation。** 假设 \(z=f(x)\) 很便宜，但保存 \(z\) 要写入 HBM，之后又要读回来。与其保存，不如在需要时重新计算：

```text
方案 A：算 z → 写 HBM → 之后再从 HBM 读回
方案 B：丢掉 z → 需要时重新计算
```

如果节省的内存访问超过新增计算的代价，FLOPs 增加也可能让总耗时下降。讲义用多层 sigmoid 的例子说明，重新计算可以把内存访问减少到原来的约 \(5/8\)。FlashAttention 的 backward 也采用同样的取舍：不保存完整的 attention probability matrix，需要时按 tile 重算局部结果。

**Memory coalescing。** 一个 warp 的 32 个线程如果访问连续地址，例如 `x[0]` 到 `x[31]`，硬件可以把请求合并成较少的 memory transactions；如果它们访问 `x[0]、x[1024]、x[2048]...`，就可能需要大量独立请求，带宽利用率会下降。正确的理解方式不是“行访问永远快、列访问永远慢”，而是：warp 内线程要结合 tensor 的 layout 和 stride，尽量访问连续或相邻地址。

**Tiling。** 对矩阵乘法，如果每个输出元素都从 HBM 读取整行 A 和整列 B，同一份输入会被反复读。Tiling 把输出切成小块，计算一个输出 tile 时，把对应的 A tile、B tile 加载到 shared memory，再在多个乘加中复用它们：

![Tiling 将输入 tile 加载到 shared memory 并分阶段复用](/learning/cs336/lectures/l5-slide-41-41.png)

这五类优化最终都在回答同一个问题：搬进来的数据能不能多用几次，或者根本不用写回 HBM。

## 4. Tiling、对齐与 Wave Quantization：为什么 shape 会改变速度

设 tile 边长为 \(T\)。一个 A tile 和一个 B tile 各有 \(T^2\) 个元素，加载后可以完成约 \(T^3\) 级别的乘加，因此粗略地有：

$$
AI \propto \frac{T^3}{T^2} = T.
$$

tile 变大通常能提高复用，但 shared memory 和 register 是有限的，tile 太大又会减少并发 block 数、增加寄存器压力，甚至降低 occupancy。实际 tile size 要同时考虑 coalesced access、片上存储容量、Tensor Core shape 和矩阵维度是否整除。

矩阵尺寸只差一个元素，也可能多出一整排 tile。比如 \(1024\times1024\) 可以整齐地切成 \(128\times128\) 的 tile；换成 \(1025\times1025\) 后，最后一排和最后一列都需要 mask，很多线程只是在处理 padding。内存 burst 的对齐也会造成类似影响，所以 \(1024\) 有时会比 FLOPs 更少的 \(1000\) 跑得快。

另一个现象是 wave quantization。讲义用 A100 的 108 个 SM 举例：tile size 为 \(256\times128\) 时，矩阵边长 1792 需要：

$$
\frac{1792}{256}\times\frac{1792}{128}
= 7\times14 = 98
$$

个 tile；边长变成 1793 后，需要：

$$
8\times15 = 120
$$

个 tile。98 个 tile 可以在一个 wave 内完成，而 120 个 tile 会让第二个 wave 只剩一部分 SM 工作，尾部利用率明显下降。

![1792 到 1793 的 shape 变化导致 tile 数从 98 增加到 120](/learning/cs336/lectures/l5-slide-48-48.png)

因此 benchmark 中的锯齿曲线并不一定是噪声。矩阵大小、tile 可整除性、memory alignment、Tensor Core 支持的 shape 和 wave 数量共同决定了实际吞吐。分析 kernel 时，不能只比较理论 FLOPs，还要看这些 FLOPs 如何映射到 block、warp 和 SM。

## 5. FlashAttention：不改数学公式，先解决 \(N\times N\) 中间结果

标准 attention 可以写成：

$$
S = QK^\top,
\qquad
P = \operatorname{softmax}(S),
\qquad
O = PV.
$$

朴素实现会依次计算 \(QK^\top\)、softmax 和 \(PV\)，并把 \(S\)、\(P\) 这样的 \(N\times N\) 中间矩阵写入 HBM，再在下一阶段读回来：

```text
Q, K
  ↓
QKᵀ → write S to HBM
  ↓
read S → softmax → write P to HBM
  ↓
read P, V → PV → O
```

问题不在于 attention 的公式多算了一个 Big-O，而在于两个巨大的中间矩阵带来了大量 HBM traffic。FlashAttention 保持：

$$
\operatorname{softmax}\left(\frac{QK^\top}{\sqrt d}\right)V
$$

在数值误差范围内的结果，但改变计算顺序：固定一个 Q tile，依次加载 K/V tile，在 SRAM 中完成局部乘法、指数、softmax 更新和输出累加，不把完整 \(S\) 或 \(P\) materialize 到 HBM。

![FlashAttention 的 forward pass：tile-wise matmul、融合指数运算和 online softmax](/learning/cs336/lectures/l5-slide-54-54.png)

这也是 FlashAttention 和 Lecture 4 中 Linear Attention 的分界：

| 方法 | 改变的对象 | 复杂度直觉 |
| --- | --- | --- |
| Linear Attention | 修改 attention 的数学结构 | 可能把二次交互改成线性形式，但不再是标准 softmax attention |
| FlashAttention | 保留 attention 数学结构，改变执行顺序和内存访问 | 仍然是 \(O(N^2d)\) 的计算，但显著减少中间矩阵的 IO |

## 6. Online Softmax：在分块计算中保持正确的归一化

FlashAttention 的难点是 softmax 需要整行的最大值和归一化因子，而 tile 算法一次只看到一部分 score。对一行 score \(x_i\)，数值稳定的 softmax 是：

$$
p_i = \frac{e^{x_i-m}}{\sum_j e^{x_j-m}},
\qquad
m = \max_j x_j.
$$

假设已经处理过旧 tile，维护：

$$
m_{\mathrm{old}} = \max(\text{old scores}),
$$

$$
\ell_{\mathrm{old}}
= \sum_{\mathrm{old}} e^{x_i-m_{\mathrm{old}}}.
$$

新 tile 到来后，先计算它自己的最大值 \(m_{\mathrm{tile}}\)，再更新全局最大值：

$$
m_{\mathrm{new}}
= \max(m_{\mathrm{old}},m_{\mathrm{tile}}).
$$

旧 tile 的指数和只需要乘一个 correction factor，再加上新 tile 的贡献：

$$
\ell_{\mathrm{new}}
= e^{m_{\mathrm{old}}-m_{\mathrm{new}}}\ell_{\mathrm{old}}
+ \sum_{\mathrm{tile}}e^{x_i-m_{\mathrm{new}}}.
$$

这个修正来自：

$$
e^{x_i-m_{\mathrm{new}}}
= e^{x_i-m_{\mathrm{old}}}e^{m_{\mathrm{old}}-m_{\mathrm{new}}}.
$$

因此旧 tile 不必重新扫描。

输出也可以在线累加。维护：

$$
o_{\mathrm{old}}
= \sum_{\mathrm{old}}e^{x_i-m_{\mathrm{old}}}v_i,
$$

新 tile 到来时：

$$
o_{\mathrm{new}}
= e^{m_{\mathrm{old}}-m_{\mathrm{new}}}o_{\mathrm{old}}
+ \sum_{\mathrm{tile}}e^{x_i-m_{\mathrm{new}}}v_i.
$$

处理完所有 K/V tile 后，最终输出为：

$$
O = \frac{o}{\ell}.
$$

整个过程中只维护 \(m\)、\(\ell\) 和 \(o\)，完整 attention matrix 从未写入 HBM。这一步是 FlashAttention 把“softmax 必须看完整行”转化为“可以沿 tile 在线更新”的关键。

## 7. FlashAttention 的三种组合：Tiling、Fusion 与 Recomputation

FlashAttention 的加速不是一个单独技巧，而是前面几种优化在 attention 上的组合。

第一步是 **tiling**：把 \(QK^\top\) 和 \(PV\) 的计算拆成小块，避免生成完整 \(N\times N\) 矩阵。第二步是 **fusion**：在加载 score tile 后，直接完成 scale、mask、指数、online softmax 和乘以 V tile，减少阶段之间的中间写回。第三步是 **recomputation**：backward 需要 attention probability 时，不保存完整 \(P\)，而是从 Q、K 和局部统计量重新计算。

因此它的计算量仍然是 attention 的二次量级：

$$
\text{standard attention}: O(N^2d),
\qquad
\text{FlashAttention}: O(N^2d).
$$

FlashAttention 的收益来自 IO complexity 和 activation memory，而不是把标准 attention 变成了线性 attention。它把一个可复用的系统优化模式讲得很完整：用一些便宜的计算，换掉昂贵的 HBM 读写；用片上存储保存短生命周期的中间值；用稳定的在线更新避免 materialize 巨大矩阵。

## 8. 从 Lecture 5 到 Assignment 2：理论必须落到 profile

Lecture 5 后的 Assignment 2 不是“额外学一点 CUDA”，而是要求把这里的判断流程真正跑一遍：先对 A1 模型做 profile 和 benchmark，再优化 attention，自己实现 Triton FlashAttention 风格的 kernel，并处理 memory-efficient distributed training。

可以把四层知识对应起来：

```text
数学：softmax(QKᵀ)V
算法：online softmax，按 tile 增量更新
硬件：HBM、shared memory、register、Tensor Core
kernel：tiling、fusion、coalescing、recomputation
```

这也是为什么“能调用 `nn.MultiheadAttention`”和“能解释 FlashAttention 为什么快”是两种不同能力。前者知道接口，后者能从中间 tensor、内存层级和 kernel 调度解释实际性能。

## 9. 用 Roofline 诊断一个慢 kernel

以后遇到一段 PyTorch 或 Triton 代码变慢，先按下面的顺序问：

1. **它是什么 workload？** 是 elementwise、reduction、GEMM 还是 attention？
2. **它做了多少计算？** 估算 FLOPs，确认主要成本来自矩阵乘法还是逐元素操作。
3. **它搬了多少数据？** 统计 HBM/global memory 的读写，以及中间 tensor 是否被反复 materialize。
4. **Arithmetic intensity 是多少？**

   $$
   AI=\frac{\text{FLOPs}}{\text{bytes transferred}}.
   $$

5. **它位于 Roofline 的哪一侧？** memory-bound 和 compute-bound 的优化方向不同。
6. **如果是 memory-bound，能否 fusion、tiling、coalescing、lower precision 或 recomputation？**
7. **如果利用率仍然异常，检查 tile shape、alignment、occupancy、warp divergence 和 wave quantization。**
8. **最后用 benchmark 和 profiler 验证，不凭直觉判断。**

两个数学等价的程序可以说明这套判断：

```python
# Version A：多个 kernel 和多个中间 tensor
a = x * x
b = torch.exp(a)
c = b / b.sum(dim=-1, keepdim=True)
y = c * v
```

```text
# Version B：一个融合的 kernel
load x, v
  ↓
square → exp → online reduction → normalize → multiply v
  ↓
store y
```

两者 FLOPs 可能几乎一样，但 Version B 少了 kernel launch 和 HBM 中间读写，能让中间值停留在 register/shared memory，因此可能明显更快。

反过来，只比较两个 kernel 的 FLOPs 也不能判断谁更快：

| Kernel | FLOPs | HBM traffic | Arithmetic intensity |
| --- | ---: | ---: | ---: |
| A | 100 GFLOPs | 1 TB | 0.1 FLOP/B |
| B | 150 GFLOPs | 10 GB | 15 FLOP/B |

Kernel B 多算 50%，但更可能接近 compute-bound；Kernel A 可能一直在等待内存。`算法 FLOPs 最少` 和 `运行时间最短` 在现代 GPU 上不是同一个命题。

## 10. 课程串联与学习边界

Lecture 2 的 Roofline 给出理论上的 FLOPs/bytes；Lecture 5 把 bytes 具体化成：

```text
HBM → L2 → shared memory → register → Tensor Core
```

Lecture 3 解释标准 attention 的 \(\operatorname{softmax}(QK^\top)V\)；Lecture 4 可以通过 Linear Attention、Mamba、Gated DeltaNet 或 Sparse Attention 改变 interaction structure；Lecture 5 保持标准 attention 的数学答案，用 FlashAttention 改善执行顺序和 IO。这里要区分：

$$
\text{算法复杂度优化}
\neq
\text{硬件执行优化}.
$$

必须掌握的基础包括 CPU latency 与 GPU throughput、SM/block/warp/thread、register/shared memory/HBM、compute-bound 与 memory-bound、fusion、tiling，以及 FlashAttention 为什么减少 IO。做 A2 时需要真正内化 coalescing、control divergence、occupancy、wave quantization、tile size selection、online softmax 和 recomputation。Tensor Core 微架构、TMA、async copy、warp specialization、shared-memory bank swizzling、WGMMA 和 Blackwell 指令细节，则可以在实际 kernel engineering 时再深入。

## 面试复盘

1. **为什么 Transformer 适合 GPU？** 因为它包含大量规则的数据并行和 GEMM；GPU 用 throughput、SIMT 和大规模计算单元处理这些工作，而不是因为“核心多”这么简单。

2. **Thread、Warp、Block、SM 是什么关系？** Thread 是逻辑工作单元，32 个 thread 通常组成一个 warp；多个 warp 组成 block；block 被调度到某个 SM，并使用该 SM 的 shared memory。

3. **为什么 HBM 叫 High Bandwidth Memory，仍然可能成为瓶颈？** 因为计算吞吐增长得更快；当 \(AI\) 不够高时，性能上限由 \(BW\times AI\) 决定，计算单元会等待数据。

4. **为什么 fusion 不减少 FLOPs 也能加速？** 它减少 kernel launch 和中间 tensor 的 HBM write/read，让数据在 register 或 shared memory 中连续完成多个操作。

5. **为什么 recomputation 增加 FLOPs 反而可能更快？** 当重算很便宜、HBM 读写很贵时，用计算替代数据搬运能降低总耗时和 activation memory。

6. **为什么 \(1024\times1024\) 可能比 \(1000\times1000\) 快？** 前者更容易整除 tile，更容易匹配 Tensor Core shape 和 memory alignment，也可能减少尾部 mask 与额外 wave。

7. **FlashAttention 为什么快？** 它保持标准 attention 的数学结果，通过 tiling、online softmax、fusion 和 recomputation 避免把完整 \(N\times N\) 的中间矩阵反复写入 HBM。

8. **FlashAttention 和 Linear Attention 的区别是什么？** FlashAttention 保留 \(O(N^2d)\) 的标准 attention 计算，主要优化 IO；Linear Attention 修改数学结构，目标是降低交互复杂度。

9. **看到 GPU utilization 只有 10%，能不能直接说 kernel 写得差？** 不能。先确认它是否 memory-bound，再用 Roofline 和 profiler 判断它是否已经接近带宽上限；只有明确瓶颈后，才选择 fusion、tiling、coalescing、低精度或重算。

Lecture 5 最应该留下的判断是：GPU 优化的重点通常不是让公式少写几行，而是让昂贵的数据尽可能少移动，让已经搬进来的每个 byte 尽可能多参与计算。Tiling、fusion、recomputation 和 FlashAttention 看起来是不同知识点，实际都在围绕这个约束做工程取舍。
