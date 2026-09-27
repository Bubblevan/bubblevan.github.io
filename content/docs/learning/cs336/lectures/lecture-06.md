---
title: "L06 · Triton"
weight: 6
date: 2026-08-28
updated: 2026-09-16
course: "CS336"
topics: ["CS336", "triton", "kernels"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture6/
---

Lecture 5 解释了 GPU 为什么偏爱大规模并行、数据复用和规则的内存访问。Lecture 6 往下走一步：如何亲手写出一个 kernel，并用测量结果判断它是否真的更快。

原始讲义的四个例子有明确的递进关系：

$$
\text{GeLU}
\rightarrow
\text{Softmax}
\rightarrow
\text{Row Sum}
\rightarrow
\text{MatMul + ReLU}
$$

它们分别对应 elementwise、row-wise reduction、带 tile loop 的 reduction，以及二维 tiling 加矩阵乘法和 fusion。Lecture 6 还没有直接实现 FlashAttention，但它已经把 FlashAttention 所需的 program mapping、在线归约、tiling 和 fused output 都拆成了可以单独验证的小问题。

## 1. Triton 的抽象：从 GPU 硬件映射到一个 tile

Lecture 5 讨论 GPU 的硬件组成，Lecture 6 更关心这些资源如何限制 kernel。可以先记住三层对应关系：

$$
\text{Grid / HBM}
\rightarrow
\text{Thread Block / Shared Memory}
\rightarrow
\text{Thread / Registers}.
$$

整个任务是一个 grid，grid 由多个 thread block 组成；block 会被调度到某个 SM，并共享该 SM 上的 shared memory；block 内的线程再使用自己的 registers。对于 `y[i] = gelu(x[i])` 这样的逐元素操作，一个线程处理一个元素很自然；softmax 和矩阵乘法需要多个线程交换中间结果，因此必须把相关工作放进同一个 block。

![Lecture 6 使用的 GPU 硬件层级：SM、L1/shared memory、L2 和 HBM](/learning/cs336/lectures/l6-gpu-hardware.png)

同一个 warp 的 32 个线程仍然以 lockstep 方式执行。如果一半线程走分支 A、另一半走分支 B，硬件通常要先执行 A、再执行 B，未走当前分支的线程保持闲置，这就是 control divergence。

Occupancy 也需要重新理解。假设一个 block 有 128 个线程，每个线程使用 160 个 registers，那么一个 block 消耗：

$$
128\times160=20480
$$

个 registers。若一个 SM 只有 65536 个 registers，最多可以同时放置：

$$
\left\lfloor\frac{65536}{20480}\right\rfloor=3
$$

个 block。register 用得越多，resident warps 可能越少，occupancy 也会下降。但低 occupancy 不一定意味着性能差：如果每个线程因此能多做一些工作、少访问 HBM，整体可能更快。occupancy 是资源约束下的一个指标，不是需要盲目最大化的目标。

还要区分两种访问问题。shared memory 被划分为 32 个 bank；如果一个 warp 的线程同时访问不同 bank，访问可以并行，如果多个线程访问同一个 bank 的不同地址，就会发生 bank conflict，访问可能被串行化。常见的解决方向是调整 shared-memory layout，例如对行列索引做 swizzling。

HBM/global memory 的问题叫 memory coalescing。若 32 个线程连续访问 `x[0]` 到 `x[31]`，每个元素 4 bytes，恰好可以覆盖一个 128-byte cache line；若线程访问跨度很大的地址，硬件就需要更多 memory transactions。一个发生在 shared memory，一个发生在 HBM，名字和优化方式不能混用。

block 还会按 wave 被调度到所有 SM。以 B200 的 148 个 SM 为例，启动 160 个 block 时，第一波可以填满 148 个 SM，第二波只剩 12 个 block，尾部会有 136 个 SM 空闲。这种 wave quantization 会让某些 shape 的吞吐出现锯齿。

CUDA 和 Triton 的差别可以这样概括：CUDA 更接近“每个 thread 做什么”，需要程序员管理更多线程和 shared memory 细节；Triton 更接近“一个 program instance 负责哪个 block/tile，以及这个 tile 如何 load、计算、store”。Triton 不是另一种普通的 Python 数组语法，而是一个让数据分块和内存流动显式化的 GPU kernel DSL。

## 2. 先 Benchmark，再 Profile，再改代码

Lecture 6 给出的工作循环很简单：

```text
benchmark / profile
        ↓
修改实现
        ↓
benchmark / profile again
```

Benchmark 回答“总共花了多久”，适合比较 implementation A 和 B，或者观察 runtime 随矩阵维度如何 scaling。Profile 回答“时间花在哪里”，可以告诉你实际调用了哪些 CUDA kernel、每个 kernel 花了多久，以及不同 shape 是否触发了不同实现。

这两个概念不能互相替代。一个实现可能总时间更短，但某个 kernel 的占比更高；也可能 GPU utilization 看起来不高，却已经接近 memory bandwidth 上限。没有 profile，很难知道下一步应该优化 fusion、tile shape 还是内存访问。

GPU timing 还有一个常见陷阱：CUDA kernel launch 通常是异步的。下面的 CPU wall-clock 计时不一定覆盖真正的 matmul：

```python
start = time.time()
y = x @ x
end = time.time()
```

CPU 可能在 GPU 完成之前就继续执行了。可靠的计时至少要在测量前后同步：

```python
torch.cuda.synchronize()
start = time.time()
y = x @ x
torch.cuda.synchronize()
elapsed = time.time() - start
```

更适合 GPU 的方法是 CUDA Events：

```python
for _ in range(num_warmups):
    run()
torch.cuda.synchronize()

start_event = torch.cuda.Event(enable_timing=True)
end_event = torch.cuda.Event(enable_timing=True)
start_event.record()
run()
end_event.record()
torch.cuda.synchronize()
elapsed_ms = start_event.elapsed_time(end_event)
```

warmup 用来排除第一次执行中的编译、缓存和初始化开销；多次 trial 用来观察方差。Benchmark 可以使用 `torch.utils.benchmark`，也可以像原始讲义一样自己封装 CUDA Events，以便看清楚计时边界。

Profile 则可以看到类似 `cutlass...sm100...f32...64x64x16...` 的 kernel 名称。这里的字符串包含实现库、架构、dtype 和 tile shape 等线索：它告诉你 PyTorch 不是抽象地“做了一个 matmul”，而是选择了一个具体的 kernel。Lecture 6 的方法论可以压缩为：先测端到端时间，再看具体 kernel，改动后两者都重新测。

## 3. GeLU：第一个 kernel 先解决 Fusion

GeLU 的 tanh approximation 可以写成：

$$
\operatorname{GELU}(x)
\approx
\frac12x
\left[1+\tanh\left(\sqrt{\frac2\pi}\left(x+0.044715x^3\right)\right)\right].
$$

直接用 PyTorch 表达时，数学是正确的：

```python
0.5 * x * (
    1 + torch.tanh(
        0.79788456 * (x + 0.044715 * x * x * x)
    )
)
```

但 eager 模式可能把平方、立方、乘法、加法和 `tanh` 拆成多个 kernel。每个中间 tensor 都可能经历一次 `HBM -> SM -> HBM`，单个元素的计算量很小，数据搬运和 kernel launch 反而占主要成本。

内置 GeLU 和 `torch.compile` 版本可以把这些逐元素操作融合成一个 kernel，理想的数据流是：

```text
读 x 一次
  ↓
x³ → 线性组合 → tanh → 乘法
  ↓
写 y 一次
```

它们和 naive 实现应当通过 `torch.allclose` 检查数值一致，再用 benchmark 比较时间。profile 通常能看到 naive 版本有多个 kernel，而 fused 或 compiled 版本更接近一次读、一次写。`torch.compile` 生成的 compiled kernel 也可能是 Triton kernel。

这个例子把 Lecture 5 的 fusion 从概念变成了可观察的实验：数学 FLOPs 没有明显减少，速度却因为中间值不再反复写回 HBM 而改变。

## 4. Triton 的基本语言：`program_id`、offset、load、store 和 mask

一个最小的 Triton kernel 会用 `@triton.jit` 声明，并让一个 program instance 处理一段连续元素：

```python
@triton.jit
def gelu_kernel(x_ptr, y_ptr, num_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < num_elements

    x = tl.load(x_ptr + offsets, mask=mask)
    y = gelu_formula(x)
    tl.store(y_ptr + offsets, y, mask=mask)
```

`tl.program_id(0)` 表示当前 program 在 grid 中的编号；`tl.arange(0, BLOCK_SIZE)` 生成这个 block 负责的 lane offsets；`tl.load` 把对应 tile 从 global memory 读进片上值；`tl.store` 把结果写回。

mask 用来处理不规则边界。若 \(N=1000\)、`BLOCK_SIZE=256`，需要 4 个 block，最后一个 block 的有效范围是 768 到 999，1000 到 1023 都越界。统一使用规则 tile，再通过 `offsets < N` 屏蔽尾部，比为最后一个 block 写一套特殊控制流更适合 GPU。

这个思路也贯穿 Softmax：padding 位置读作 \(-\infty\)，因为：

$$
e^{-\infty}=0,
$$

所以它们不会影响 row max 和归一化求和；store 时再用同一个 mask 阻止越界写入。

Triton 最终会编译到 PTX。GeLU 例子里可以看到 `ld.global.*`、`st.global.*` 这样的 global memory load/store，以及 block/thread 索引和浮点、整数 register。此时不需要手写 PTX，但要理解这条链：

```text
PyTorch / Triton source
        ↓
compiler
        ↓
PTX
        ↓
GPU execution
```

## 5. Softmax：一个 program 负责一行，把 reduction 融合起来

GeLU 是 elementwise：

$$
y_i=f(x_i).
$$

Softmax 则要先对整行做 max 和 sum：

$$
y_i=\frac{e^{x_i-m}}{\sum_j e^{x_j-m}},
\qquad
m=\max_j x_j.
$$

每个输出都依赖同一行的其他元素，这就是 reduction。若矩阵 \(X\in\mathbb R^{M\times N}\) 用多个 PyTorch 操作实现，内存流量大致是：

| 阶段 | 读取 | 写入 |
| --- | ---: | ---: |
| row max | \(MN\) | \(M\) |
| 减 max | \(MN+M\) | \(MN\) |
| exp | \(MN\) | \(MN\) |
| row sum | \(MN\) | \(M\) |
| normalize | \(MN+M\) | \(MN\) |

总计约为：

$$
5MN+M\ \text{reads},
\qquad
3MN+2M\ \text{writes}.
$$

而如果一整行可以放进一个 block，理想的数据流只需要读入一次、写回一次。原始讲义使用的例子是两行输入：

```text
[5, 5, 5]       → [1/3, 1/3, 1/3]
[0, 0, 100]     → [0, 0, 1]
```

Triton 可以让一个 program instance 对应一行：

```text
row 0 → program 0
row 1 → program 1
row 2 → program 2
```

每个 program 完成：

```text
load row
  ↓
subtract max
  ↓
exp + sum
  ↓
normalize
  ↓
store row
```

![Triton fused softmax：一个 program instance 负责一整行](/learning/cs336/lectures/l6-triton-softmax.png)

当列数不是方便的 block size 时，讲义使用 `triton.next_power_of_2(N)`。例如 \(N=1000\) 时选择 1024，多出来的位置通过 mask 读取为 `-inf`，不会改变 softmax 的数学结果。这个选择同时满足了两个条件：硬件获得规则的 tile，padding 又不会污染 reduction。

## 6. Row Sum：一行放不进一个 block 时做 Baby Tiling

如果一行有 4096 列，但一个 block 只处理 1024 个元素，就不能让一个 program 一次性加载整行。Lecture 6 先把 softmax 简化成 row sum：

$$
y_i=\sum_j x_{ij}.
$$

然后把一行切成多个 tile。以 \(N=12\)、`BLOCK_SIZE=4` 为例：

```text
tile 0: x0  x1  x2  x3
tile 1: x4  x5  x6  x7
tile 2: x8  x9  x10 x11
```

4 个逻辑 lane 分别维护自己的 accumulator：

```text
lane 0: x0 + x4 + x8
lane 1: x1 + x5 + x9
lane 2: x2 + x6 + x10
lane 3: x3 + x7 + x11
```

最后再对 4 个 accumulator 做一次 reduction。Triton 形式大致是：

```python
acc = tl.zeros([BLOCK_SIZE], dtype=tl.float32)

for start in range(0, N, BLOCK_SIZE):
    cols = start + tl.arange(0, BLOCK_SIZE)
    mask = cols < N
    x = tl.load(x_ptr + row * N + cols, mask=mask, other=0.0)
    acc += x

result = tl.sum(acc, axis=0)
tl.store(out_ptr + row, result)
```

![Triton row sum：每个线程跨多个 tile 累加，再做最终 reduction](/learning/cs336/lectures/l6-triton-row-sum.png)

这里出现了 thread coarsening：一个线程或逻辑 lane 不只处理一个元素，而是跨多个 tile 处理多个元素。好处是可以减少线程数量，并把更多中间值留在 registers；代价是 register pressure 上升，occupancy 可能下降。这正好和前面的硬件讨论接上：更高 occupancy 并不总是更好，关键是每个线程多做的工作是否值得。

## 7. MatMul + ReLU：二维 Tiling、`tl.dot` 和融合输出

现在进入深度学习 kernel 最核心的模式。设：

$$
C=AB,
\qquad
A\in\mathbb R^{M\times K},
\qquad
B\in\mathbb R^{K\times N}.
$$

naive 方法对每个 \(C_{mn}\) 遍历 \(k\)，不断从 HBM 读取 \(A_{mk}\) 和 \(B_{kn}\)。这样会产生约 \(MKN\) 级别的输入读取，arithmetic intensity 接近 \(O(1)\)。而 \(C_{m,n}\) 和 \(C_{m,n+1}\) 都需要同一行 A，反复从 HBM 读取显然浪费。

理想情况下可以把整个 A、B 放进 shared memory，再重复利用，但矩阵通常太大。实际做法是把 C 切成输出 tile；一个 program instance 负责一个 \(BLOCK_M\times BLOCK_N\) 的 C tile，并沿 K 方向循环加载：

```text
A tile 0 × B tile 0 → partial C
A tile 1 × B tile 1 → accumulate
A tile 2 × B tile 2 → accumulate
...
```

![GEMM tiled kernel：A、B 的 tile 沿 K 方向累加成 C tile](/learning/cs336/lectures/l6-gemm-tiled.png)

原始讲义中的实现使用：

$$
BLOCK_M=64,
\qquad
BLOCK_N=64,
\qquad
BLOCK_K=32.
$$

每一轮加载一个 \(64\times32\) 的 A tile 和一个 \(32\times64\) 的 B tile，得到一个 \(64\times64\) 的局部矩阵乘法：

$$
[64,32]\,[32,64]\rightarrow[64,64].
$$

K 方向每推进 32，就把新的 partial result 加到同一个 accumulator。Triton 中的核心操作是：

```python
acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

for k in range(0, K, BLOCK_K):
    a = tl.load(a_ptrs, mask=a_mask, other=0.0)
    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
    acc += tl.dot(a, b)
```

`tl.dot` 是进入 Tensor Core 友好矩阵乘法路径的入口。输入可以使用较低精度，但 accumulator 使用 FP32：

$$
\sum_{k=1}^K a_kb_k
$$

累加项很多时，较高精度的 accumulator 可以减少数值误差。这就是常见的 `low precision multiply + higher precision accumulation`。

算完矩阵乘法后，原始讲义没有立刻 store，而是在片上的 accumulator 上直接做 ReLU：

```python
acc = tl.maximum(acc, 0.0)
tl.store(c_ptrs, acc, mask=output_mask)
```

这避免了：

```text
matmul → C 写 HBM → 读 C → ReLU → 写 Y
```

而变成：

```text
matmul accumulator → ReLU → 只写一次 Y
```

这就是二维 tiling、数据复用和 operator fusion 在一个 kernel 中的组合。

真实 tensor 还不能假设是紧密的二维数组。元素地址通常由 shape 和 stride 决定：

$$
\text{address}
=
\text{row}\times\text{stride}_{\mathrm{row}}
+
\text{col}\times\text{stride}_{\mathrm{col}}.
$$

因此 MatMul kernel 需要显式接收 `stride_am`、`stride_ak`、`stride_bk`、`stride_bn`、`stride_cm` 和 `stride_cn`。这代表思维从“一个二维表格”转向“带 shape 和 stride 的线性内存”。

## 8. 四个案例如何组成 FlashAttention 的基础

四个例子可以用一张表概括：

| 案例 | 主要问题 | 得到的 kernel 思维 |
| --- | --- | --- |
| GeLU | 逐元素操作被拆成多个 kernel | fusion，读一次、写一次 |
| Softmax | 一行内需要 max 和 sum | 一个 program 负责一行，片上 reduction |
| Row Sum | 一行放不进一个 block | tile loop、accumulator、thread coarsening |
| MatMul + ReLU | 二维数据需要复用和矩阵乘法 | 2D tiling、`tl.dot`、FP32 accumulator、融合输出 |

FlashAttention 只是把这四种模式组合到一起：

$$
O=\operatorname{softmax}(QK^\top)V.
$$

其中 \(QK^\top\) 和 \(PV\) 是 tiled matmul，row max 和 row sum 是 reduction，scale、mask 和 exp 是 elementwise fusion，在线维护的输出 accumulator 则避免把完整 attention matrix 写回 HBM。理解了 GeLU、Softmax、Row Sum 和 MatMul + ReLU，再去看 FlashAttention，面对的是组合问题，而不是完全陌生的 API。

`torch.compile` 和手写 Triton 的关系也可以放在这里理解：

```text
PyTorch eager
    ↓
torch.compile：自动发现一部分融合和布局优化
    ↓
custom Triton：手动决定 program、tile、loads、stores 和数据流
    ↓
CUDA / 更底层实现：需要更细的硬件控制时再下沉
```

普通 elementwise chain 让 compiler 做通常更省事；FlashAttention、特殊 normalization、稀疏结构和特殊 layout 等场景，算法和数据流本身就需要人工设计，手写 Triton 才有意义。

## 9. 写 Triton 时的固定检查清单

Lecture 6 最终想建立的不是一套语法记忆，而是三层检查：

1. **Correctness**：和 PyTorch reference 比较，使用 `torch.allclose` 或等价测试确认数学结果。
2. **Mapping**：明确一个 program instance 负责 element block、row、matrix tile 还是 Q tile；明确 load、store、mask、stride、tile size、register 和 shared-memory 使用方式。
3. **Measurement**：用同步正确的 benchmark 测端到端时间，再用 profiler 找到真正的 kernel 和瓶颈；改完后重新测。

以后写一个 Triton kernel，可以固定问自己：

1. 一个 program instance 负责什么范围？
2. 它要从 HBM 读取哪些数据？
3. 哪些中间结果会留在 register 或 shared memory？
4. 哪些中间 tensor 本来就不需要写回 HBM？
5. 数据能否在一个 tile 内复用？
6. 一行或一个矩阵如果放不进 block，tile loop 怎样设计？
7. tile size 是否平衡了 register pressure、shared memory、Tensor Core shape 和 wave utilization？
8. 结果是否正确，改完后是否真的更快？

这套问题比背 `tl.load` 和 `tl.store` 的参数更重要，因为它可以迁移到 reduction、GEMM、FlashAttention 和其他自定义 kernel。

Lecture 5 和 Lecture 6 可以这样区分：

$$
\boxed{\text{Lecture 5 = hardware intuition}}
$$

$$
\boxed{\text{Lecture 6 = kernel programming intuition}}
$$

Lecture 5 解释 HBM、shared memory、register、Tensor Core、fusion 和 tiling 为什么影响速度；Lecture 6 让你用 `program_id`、offsets、mask、load/store、reduction、stride 和 `tl.dot` 把这些判断写出来。

## 面试复盘

1. **Benchmark 和 profiling 有什么区别？** Benchmark 测端到端的 wall-clock time，回答“多快”；profiling 展示 kernel、算子和调用的时间分布，回答“时间花在哪里”。

2. **为什么 GPU timing 必须考虑 CUDA asynchronous execution？** kernel launch 往往异步返回 CPU，直接用 CPU 时钟包住调用可能只测到 launch；需要 `torch.cuda.synchronize()` 或 CUDA Events，并先 warmup。

3. **为什么 naive GeLU 和 fused GeLU 数学相同，速度却不同？** naive eager 可能产生多个 kernel 和多次 HBM 中间读写，fused 版本可以一次读、片上完成整段公式、一次写。

4. **`program_id`、`tl.arange`、mask 分别做什么？** `program_id` 找到当前 block，`tl.arange` 生成该 block 的 lane offsets，mask 让规则 tile 安全覆盖不规则边界。

5. **为什么 Softmax 适合一个 block 负责一行？行放不进去怎么办？** 一行内需要 max 和 sum，放进一个 block 可以在片上完成 reduction；放不进去时，把行切成多个 tile，让线程维护 accumulator，最后再归约。

6. **什么是 tiling？为什么 tiled matmul 的 arithmetic intensity 更高？** 把输出切成小块，把对应的 A/B tile 加载到片上并复用，减少同一输入从 HBM 的重复读取。

7. **为什么 `ReLU(A @ B)` 应该融合到 matmul kernel？** ReLU 可以直接作用在片上的 FP32 accumulator 上，避免先写出 C、再读回执行 ReLU，只需要最终写一次。

8. **Triton 为什么不只是 CUDA 的 Python 语法糖？** CUDA 更接近 per-thread 编程，Triton 更偏 per-program/per-tile 编程；它让你以 block、tile 和数据流为中心描述 kernel，再由编译器生成 PTX。

Lecture 6 的核心可以压缩成一句话：一个高性能 kernel 要选择合适的 tile，只从 HBM 读取必要数据，在片上完成尽可能多的计算，最后尽量只写回一次。Lecture 2 让你估算数据移动，Lecture 5 让你理解数据经过哪些硬件层级，Lecture 6 则开始由你亲自决定这些数据如何移动。
