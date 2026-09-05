---
title: "L05 · GPU"
weight: 5
date: 2026-08-28
updated: 2026-08-28
course: "CS336"
topics: ["CS336", "gpu", "distributed-training"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture5/
---

Lecture 5 是 CS336 从“会写 Transformer”真正迈进 **ML Systems** 的一讲。

课程表把它定义为 **“GPUs, TPUs [Tatsu]”**，紧接 Lecture 4，下一讲就是 Kernels/Triton；而 2026 Assignment 2 随后要求你 profile/benchmark A1 模型、自己写 Triton FlashAttention，并做分布式和显存优化。也就是说，Lecture 5 不是硬件科普，而是在回答：

$$
\boxed{\text{为什么同样的数学公式，写法不同能快十倍甚至更多？}}
$$

---

# 0. 先抓整堂 Lecture 5 的主线

前面几讲其实形成了：

```text
Lecture 2
模型需要多少 FLOPs / memory？
        ↓
Lecture 3
现代 Transformer 怎么设计？
        ↓
Lecture 4
能不能少算一些 token / parameters？
        ↓
Lecture 5
这些计算到底怎么落在真实 GPU 上？
```

Lecture 5 的核心问题可以压缩成一句：

$$
\boxed{
\text{GPU 很快，但前提是你得用 GPU 喜欢的方式喂它。}
}
$$

GPU 喜欢：

* 大量相同的并行计算；
* 大矩阵乘法；
* 数据重复利用；
* 连续、规则的内存访问；
* 数据尽量留在片上快速存储。

GPU 不喜欢：

* 一堆小操作；
* 到处读写 HBM；
* 不规则访问；
* warp 内大量分支；
* 很小或奇怪 shape 的 GEMM；
* kernel 一个接一个产生临时 tensor。

官方 Lecture 5 的内容顺序就是 GPU architecture → execution/memory model → TPU → matmul/Tensor Core → memory wall/roofline → precision/fusion/recomputation/coalescing/tiling → FlashAttention。([GitHub][2])

---

# 1. CPU 和 GPU 根本不是“一个快，一个慢”

先纠正一个最容易形成的错误认识：

> GPU = 更强的 CPU。

不是。

CPU 和 GPU 的设计目标不同。

CPU 更在乎：

$$
\boxed{\text{latency}}
$$

也就是：

> 一个任务什么时候完成？

所以 CPU 会花大量芯片面积在：

```text
复杂控制逻辑
branch prediction
out-of-order execution
大 cache
少量但很强的 cores
```

GPU 更在乎：

$$
\boxed{\text{throughput}}
$$

也就是：

> 同一秒钟总共能处理多少工作？

所以它更像：

```text
较简单控制
       ↓
大量计算单元
       ↓
同时跑海量 threads
```

可以粗略想象：

```text
CPU

[ BIG CORE ] [ BIG CORE ] [ BIG CORE ] [ BIG CORE ]
       ↑
复杂控制 + 大缓存


GPU

[compute][compute][compute][compute]...
[compute][compute][compute][compute]...
[compute][compute][compute][compute]...
```

所以：

```python
for i in range(1_000_000):
    y[i] = x[i] * 2
```

这种“一百万份互相独立的相同工作”，GPU 非常喜欢。

而：

```text
做 A
看结果
if ...
做 B
又看结果
if ...
做 C
```

这种复杂控制流未必是 GPU 的强项。

这就是 Lecture 5 理解 GPU 的第一原则：

$$
\boxed{\text{GPU 用大量并行性换 throughput。}}
$$

([GitHub][3])

---

# 2. GPU 里最重要的单位：SM

NVIDIA GPU 不是一个“大计算器”。

它由很多：

$$
\boxed{\text{SM = Streaming Multiprocessor}}
$$

组成。

你可以把一张 GPU 粗略理解成：

```text
GPU
├── SM 0
├── SM 1
├── SM 2
├── ...
└── SM N
```

每个 SM 里面又有：

```text
控制逻辑
warp schedulers
普通算术单元
Tensor Cores
register file
shared memory / L1
```

不同 GPU 的具体数量和布局不同，但 mental model 一致：

> **SM 是能够独立承接计算工作的一块基本执行岛。**

这很重要，因为等会你会看到：

```text
thread block
     ↓
被调度到
     ↓
某一个 SM
```

而 block 内共享数据，就是利用那个 SM 上的 shared memory。

([GitHub][3])

---

# 3. Thread、Block、Warp 到底是什么关系？

这几个词初学 CUDA 最容易混。

先记层级：

```text
Grid
  ↓
Blocks
  ↓
Threads
```

比如你启动：

```text
1000 blocks
每个 block 256 threads
```

逻辑上就是：

$$
256000
$$

个 threads。

---

## Thread

最小的“逻辑工作者”。

比如：

```python
y[i] = x[i] * 2
```

可以让：

```text
thread 0 → i=0
thread 1 → i=1
thread 2 → i=2
...
```

---

## Block

一群 threads。

关键能力：

$$
\boxed{\text{同一个 block 的 threads 可以共享 shared memory}}
$$

所以：

```text
Thread 0 ┐
Thread 1 ├─ Block 0 ─ shared memory
Thread 2 │
...      ┘
```

一个 block 会在某个 SM 上执行。

---

## Warp

这是硬件真正执行 threads 时的重要单位。

在 NVIDIA GPU 上，一个 warp 通常：

$$
\boxed{32\text{ threads}}
$$

所以：

```text
Block with 256 threads
        ↓
8 warps
```

这 32 个线程通常以 lockstep/SIMT 方式执行。

([GitHub][3])

---

# 4. SIMT 到底是什么？

GPU 经常说：

$$
\boxed{\text{SIMT = Single Instruction, Multiple Threads}}
$$

比如 warp 里的 32 个 threads 都执行：

```python
y[i] = x[i] * 2
```

只是：

```text
thread 0: x[0]
thread 1: x[1]
...
thread 31: x[31]
```

于是同一条 instruction 可以同时作用于很多数据。

这也是为什么神经网络这么适合 GPU：

$$
\boxed{\text{大量规则、重复、数据并行的数值计算}}
$$

---

# 5. 这立刻解释了 Control Divergence

考虑：

```python
if x[i] > 0:
    y[i] = expensive_A(x[i])
else:
    y[i] = expensive_B(x[i])
```

一个 warp 里：

```text
threads 0-15 → A
threads 16-31 → B
```

问题是 warp 想一起执行相同 instruction。

于是硬件可能不得不：

```text
先执行 A 路线
threads 0-15: work
threads 16-31: inactive

然后执行 B 路线
threads 0-15: inactive
threads 16-31: work
```

本来以为：

$$
32
$$

个线程并行。

实际上两个 branch 串行跑了。

这就是：

$$
\boxed{\text{warp divergence}}
$$

所以 GPU 不喜欢同一个 warp 内非常不规则的 control flow。

Lecture 6 会更系统地再次讲这个概念。([GitHub][4])

---

# 6. 但是 GPU 最大的问题甚至不是计算——是“搬数据”

这是 Lecture 5 的灵魂。

GPU memory 不是一种东西。

粗略层级：

```text
最快 / 最小
     ↓
Registers
     ↓
Shared Memory / L1
     ↓
L2 Cache
     ↓
HBM / Global Memory
     ↓
最慢 / 最大
```

不要死背具体 latency 数字，因为 GPU 世代不同会变。

真正要理解的是：

$$
\boxed{
\text{越靠近计算单元}
\Rightarrow
\text{越小、越快}
}
$$

而 HBM：

```text
容量大
带宽很高
但是离计算单元远
```

相对于 register/shared memory 依然昂贵。

([GitHub][3])

---

# 7. 为什么 Lecture 2 一直念叨 arithmetic intensity？

现在终于落地了。

假设你做：

```python
y = x + 1
```

对于一个 bf16：

读取：

$$
x:2B
$$

写：

$$
y:2B
$$

只做：

$$
1\text{ FLOP 左右}
$$

于是：

$$
AI\approx\frac14\text{ FLOP/byte}.
$$

GPU：

```text
HBM → SM → 做 +1 → HBM
```

绝大多数时间不是在：

```text
+1
```

而是在：

```text
搬 x
搬 y
```

这就是：

$$
\boxed{\text{memory-bound}}
$$

Lecture 5 实际就是把 Lecture 2 那张 Roofline 从抽象公式变成：

> **HBM、shared memory、register、Tensor Core 到底是什么东西。**

([GitHub][3])

---

# 8. 为什么 GPU 特别爱 Matrix Multiplication？

考虑：

$$
C=AB.
$$

其中：

$$
A\in\mathbb R^{M\times K},
\qquad
B\in\mathbb R^{K\times N}.
$$

计算量：

$$
\boxed{2MKN\text{ FLOPs}}
$$

好处是什么？

同一个：

$$
A_{ik}
$$

可以被很多：

$$
C_{ij}
$$

重复使用。

同一个：

$$
B_{kj}
$$

也可以被很多：

$$
C_{ij}
$$

重复使用。

也就是说：

$$
\boxed{\text{data reuse 很高}}
$$

如果我们能把一块 A/B 从 HBM 搬进快速 memory：

```text
HBM
 ↓
shared memory/registers
 ↓
用很多很多次
```

那每搬一个 byte，就能做很多 FLOPs。

于是：

$$
\text{Arithmetic Intensity}\uparrow.
$$

这就是 GEMM 能接近 compute-bound 的根本原因。

---

# 9. Tensor Core 是什么？

普通 GPU 当然能做：

```text
a*b+c
```

但现代机器学习太依赖：

$$
\text{matrix multiply-accumulate}
$$

所以 NVIDIA 干脆造了专门硬件：

$$
\boxed{\text{Tensor Core}}
$$

用于非常高吞吐地进行小块矩阵：

$$
D=A B+C.
$$

然后大矩阵乘法被切成很多小 tile：

```text
large GEMM
   ↓
many small matrix multiply-accumulate tiles
   ↓
Tensor Cores
```

这就是为什么：

```text
FP32 general scalar math
```

和：

```text
BF16/FP16/FP8 Tensor Core matmul
```

吞吐量可以差巨大。

Lecture 5 这里非常重要的一点是：

> **硬件不是对所有数学运算一视同仁。**

现代 ML accelerator 本质上明确偏爱矩阵乘法。([GitHub][3])

---

# 10. 那 TPU 到底是什么？

Lecture 5 中 TPU 是一个 side thread，但很值得理解。

不要把 TPU 想成“Google 的 GPU”。

它是专门为 ML workload 设计的 ASIC。

高层结构其实和 GPU 很像：

```text
控制
+
向量运算
+
非常强的矩阵乘法单元
+
片上快速 memory
+
HBM
```

TPU 里的 MXU：

$$
\boxed{\text{Matrix Multiply Unit}}
$$

扮演极其核心的角色。

GPU 更 general：

```text
warps
threads
blocks
各种计算
```

TPU 则更加：

> “我们知道你主要就是来做矩阵乘法的，那直接为这个 workload 定制硬件。”

Lecture 5 的目的并不是教 TPU 编程，而是让你发现：

$$
\boxed{
\text{现代 ML accelerator 的共同核心：
fast matrix multiply + fast local memory}
}
$$

([GitHub][3])

---

# 11. 为什么 GPU 算力越来越可怕，程序却越来越 memory-bound？

这就是所谓：

$$
\boxed{\text{memory wall}}
$$

历史上 matrix compute throughput 的增长非常猛烈。

但：

$$
\text{HBM bandwidth}
$$

没有以同样倍数增长。

于是：

$$
\frac{\text{peak FLOP/s}}
{\text{memory bandwidth}}
$$

越来越大。

还记得这个量吗？

$$
\boxed{\text{accelerator arithmetic intensity}}
$$

这意味着：

> 为了把最新 GPU 喂饱，你必须让每个从 HBM 搬来的 byte 做越来越多的计算。

所以 GPU 越先进：

$$
\boxed{\text{数据复用反而越重要}}
$$

这是一个很反直觉的趋势。

---

# 12. Roofline 现在应该重新理解一次

性能：

$$
P
=

\min
(P_{\rm peak},\ BW\times AI).
$$

画出来：

```text
performance
   ^
   |                  ───────── peak compute
   |               /
   |             /
   |           /
   |         /
   |_______/____________________> arithmetic intensity
       memory     compute
       bound      bound
```

左边：

$$
P=BW\times AI
$$

你再买更多 Tensor Core 也没用。

因为它们都在：

> 等数据。

右边：

$$
P=P_{\rm peak}.
$$

这时候才真的：

> 算力不够。

所以以后看到一个 kernel：

```text
只跑到 GPU peak 的 10%
```

不能立刻说：

> 实现垃圾。

如果它是低 arithmetic-intensity 的 memory-bound operation，它可能已经接近自己的 Roofline 上限了。

这就是 Lecture 5 开始培养你的**性能诊断思维**。([GitHub][3])

---

# 13. 第一种优化：Low Precision

Lecture 2 已经讲过 bf16/fp8。

Lecture 5 重新讲它，但视角变了。

假设：

$$
FP32=4B,
\qquad
BF16=2B,
\qquad
FP8=1B.
$$

同一个 tensor：

```text
FP32 → 搬 4 GB
BF16 → 搬 2 GB
FP8  → 搬 1 GB
```

所以 precision 下降不仅减少：

$$
\text{memory capacity}
$$

还减少：

$$
\boxed{\text{memory bandwidth demand}}
$$

同时 Tensor Core 的低精度矩阵吞吐通常也更高。

因此：

$$
\boxed{
\text{low precision}
====================

\text{memory win}
+
\text{compute win}
}
$$

当然代价是数值稳定性，因此现代系统常做：

```text
low-precision inputs
+
higher-precision accumulation
```

Lecture 5 的 2026 slides 还涉及 MXFP8/MXFP4 等较新的低精度格式。([GitHub][2])

---

# 14. 第二种优化：Operator Fusion

这特别重要。

假设 PyTorch 写：

```python
a = x * x
b = torch.sin(a)
c = b + 1
```

朴素情况可能是：

```text
Kernel 1:
HBM → x
compute x*x
a → HBM

Kernel 2:
HBM → a
sin
b → HBM

Kernel 3:
HBM → b
+1
c → HBM
```

注意：

$$
a,b
$$

只是中间结果。

可是我们反复：

$$
\boxed{\text{write HBM → read HBM}}
$$

极其浪费。

---

如果 fuse：

```text
HBM → x
        ↓
      x*x
        ↓
       sin
        ↓
       +1
        ↓
      output → HBM
```

中间：

$$
a,b
$$

留在：

```text
register
或 shared memory
```

于是大量 HBM traffic 消失。

这就是：

$$
\boxed{\text{kernel fusion}}
$$

它也是为什么：

```python
torch.compile(model)
```

有时能明显加速。

不是数学变少了，而是：

$$
\boxed{\text{少搬数据、少 launch kernels}}
$$

Lecture 5 明确把 fusion 作为 GPU 优化核心技巧之一。([GitHub][3])

---

# 15. 这时候你应该重新理解 RMSNorm

Lecture 3：

> RMSNorm 是一个 normalization operation。

Lecture 5：

> RMSNorm 其实是一连串 reduction + elementwise operations。

如果写成：

```text
square
↓
mean
↓
rsqrt
↓
multiply
```

每一步都单独读写 HBM，非常亏。

所以现实高性能实现往往：

$$
\boxed{\text{fused RMSNorm kernel}}
$$

这就是为什么“我用 PyTorch 写出了正确公式”和“我写出了高性能 kernel”完全是两个问题。

这也是 Lecture 6 / A2 要你真正学习 Triton 的原因。

---

# 16. 第三种优化居然是 Recomputation：多算反而更快？

看起来很违反直觉。

假设中间结果：

$$
z=f(x)
$$

之后会用。

方案 A：

```text
算 z
↓
写进 HBM
...
从 HBM 读回来
```

方案 B：

```text
不要保存
...
需要的时候重新算 z
```

如果：

$$
f
$$

很便宜，而 HBM traffic 很昂贵，那么：

$$
\boxed{\text{重新计算反而更快}}
$$

所以：

$$
\text{FLOPs}\uparrow
$$

却可能：

$$
\text{runtime}\downarrow.
$$

这就是 Lecture 2 那句话的更高级版本：

$$
\boxed{\text{少 FLOPs 不等于快}}
$$

FlashAttention backward 就大量利用这个思想：

> 不存完整 attention matrix，backward 需要时重新计算局部结果。

([GitHub][3])

---

# 17. 第四种：Memory Coalescing

这里必须真正理解，不能背“行快列慢”。

假设 memory 是：

```text
x[0] x[1] x[2] x[3] ... x[31]
```

warp 里 32 个 threads：

```text
thread 0 → x[0]
thread 1 → x[1]
thread 2 → x[2]
...
thread31 → x[31]
```

这些地址连续。

GPU 可以把它们合并成少量 memory transactions。

这叫：

$$
\boxed{\text{coalesced memory access}}
$$

---

如果变成：

```text
thread 0 → x[0]
thread 1 → x[1024]
thread 2 → x[2048]
...
```

每个 thread 访问相隔很远的地址。

硬件可能需要大量独立 memory transactions。

于是：

$$
\boxed{\text{bandwidth utilization 暴跌}}
$$

所以正确结论不是：

> row access 永远快。

而是：

$$
\boxed{\text{warp 内 threads 最好访问连续/邻近地址}}
$$

至于是行还是列，取决于 tensor 的 memory layout / stride。

这是你以后写 Triton/CUDA 必须形成的直觉。

([GitHub][4])

---

# 18. 第五种，也是 Lecture 5 最重要的技巧：Tiling

假设：

$$
C=AB.
$$

最蠢实现：

对每个 (C_{ij})：

```text
从 HBM 读取整行 A_i
从 HBM 读取整列 B_j
做 dot product
```

问题：

同一个：

$$
A_{ik}
$$

会为：

$$
C_{i1},C_{i2},C_{i3},\ldots
$$

反复从 HBM 读取。

非常浪费。

---

## Tiling 怎么做？

把：

$$
C
$$

切成小块：

```text
C:

┌────┬────┬────┐
│tile│tile│tile│
├────┼────┼────┤
│tile│tile│tile│
├────┼────┼────┤
│tile│tile│tile│
└────┴────┴────┘
```

计算一个 C tile 时：

```text
A tile          B tile
  ↓               ↓
HBM             HBM
  ↓               ↓
shared memory / registers
        ↓
重复利用很多次
        ↓
     C tile
        ↓
       HBM
```

核心思想：

$$
\boxed{\text{load once, reuse many times}}
$$

---

# 19. Tiling 为什么会提高 Arithmetic Intensity？

假设 tile 大小：

$$
T\times T.
$$

A tile：

$$
T^2
$$

元素。

B tile：

$$
T^2
$$

元素。

加载一次后可以做：

$$
T^3
$$

级别 multiply-add 工作。

所以大致：

$$
AI
\propto
\frac{T^3}{T^2}
===============

\boxed{T}.
$$

tile 越大：

$$
\text{reuse}\uparrow
$$

$$
AI\uparrow.
$$

但是不能无限大。

因为 shared memory/register 是有限的。

所以：

$$
\boxed{
\text{tile size 是 reuse 与 hardware resource 的 trade-off}
}
$$

这正是高性能 GEMM kernel tuning 的核心之一。([GitHub][3])

---

# 20. 为什么矩阵尺寸只差一点，速度可能突然掉很多？

这就是 Lecture 5 开头展示的那种：

> GEMM throughput 随 matrix size 并不是平滑曲线。

原因之一就是：

$$
\boxed{\text{tile divisibility}}
$$

假设 kernel tile：

$$
128\times128.
$$

你的矩阵：

$$
1024\times1024
$$

正好：

$$
8\times8
$$

tiles。

很好。

但：

$$
1025\times1025
$$

就需要：

$$
9\times9
$$

tiles。

最后一排/列 tile：

```text
大量 threads 只处理 padding / mask
```

所以多 1 个元素，却可能产生一个新的完整 tile。

---

# 21. 还有一个特别漂亮的概念：Wave Quantization

假设 GPU：

$$
148\text{ SMs}
$$

有：

$$
148
$$

个 blocks：

```text
第一波：
148 SM 全满
```

非常漂亮。

如果有：

$$
160
$$

blocks：

```text
第一波：
148 blocks
→ 148 SM 满

第二波：
12 blocks
→ 只有 12 个 SM 工作
→ 136 个 SM 空闲
```

于是最后一波 utilization 很差。

这叫：

$$
\boxed{\text{wave quantization}}
$$

所以：

```text
matrix slightly larger
```

可能突然多出一个 execution wave。

performance 就会：

```text
啪
↓
掉下来
```

这解释了很多 GPU benchmark 中看似“玄学”的锯齿曲线。Lecture 6 也继续解释 block occupancy。([GitHub][4])

---

# 22. 这就是为什么“padding 后反而更快”并不奇怪

例如：

```text
dimension = 1000
```

理论 FLOPs 少。

而：

```text
dimension = 1024
```

FLOPs 更多。

但是 1024：

```text
更符合 tile
更符合 Tensor Core shape
memory alignment 更漂亮
block scheduling 更规整
```

于是：

$$
\boxed{
1024\text{ 可能反而比 }1000\text{ 更快}
}
$$

这对于第一次做 systems benchmark 的人特别违反直觉。

你需要开始从：

> 算了多少数学运算？

转变到：

> 这些数学运算怎样映射到硬件？

---

# 23. 到这里终于可以理解为什么 FlashAttention 是神作

先写普通 attention：

$$
S=QK^\top
$$

$$
P=\operatorname{softmax}(S)
$$

$$
O=PV.
$$

最朴素实现逻辑：

```text
Q,K
 ↓
QKᵀ
 ↓
S 写 HBM

S 从 HBM 读
 ↓
softmax
 ↓
P 写 HBM

P 从 HBM 读
 ↓
PV
 ↓
O
```

最大的灾难不是：

$$
QK^\top
$$

做了很多 FLOPs。

真正麻烦的是：

$$
S,P\in\mathbb R^{N\times N}
$$

巨大。

它们反复：

$$
\boxed{\text{HBM write/read}}
$$

Lecture 5 就是在这里把前面所有内容汇合起来。([GitHub][3])

---

# 24. FlashAttention 没有改变 Attention 的数学答案

这是必须强调的。

FlashAttention 不是：

```text
approximate attention
```

也不是：

```text
linear attention
```

它仍然计算：

$$
\boxed{
\operatorname{softmax}
\left(
\frac{QK^\top}{\sqrt d}
\right)V
}
$$

结果在数值误差范围内和 standard attention 一致。

它改变的是：

$$
\boxed{\text{计算顺序和内存访问}}
$$

这就是 **IO-aware algorithm** 的典型代表。

---

# 25. FlashAttention 第一招：Attention 也 Tiling

不要一次：

$$
QK^\top
\rightarrow
N\times N.
$$

而是：

```text
Q tile
  ×
K tile
  ↓
small S tile
```

这个小 tile：

```text
直接留在 SRAM/register
```

做 softmax 和乘 V。

然后：

```text
下一个 K/V tile
```

不断累计结果。

于是：

$$
\boxed{\text{不需要 materialize 整个 }N\times N\text{ matrix}}
$$

---

# 26. 可是 Softmax 有个麻烦

对于一整行：

$$
p_i=
\frac{e^{x_i}}
{\sum_j e^{x_j}}.
$$

数值稳定版本：

$$
p_i
===

\frac{e^{x_i-m}}
{\sum_j e^{x_j-m}}
$$

其中：

$$
m=\max_jx_j.
$$

问题来了：

> 如果我一次只看到一个 tile，我怎么知道全行最大值？

例如：

```text
tile 1:
[2, 3, 1]

tile 2:
[100, 4, 5]
```

处理 tile 1 时：

$$
m=3.
$$

后来才发现：

$$
m=100.
$$

难道 tile 1 得重新处理？

---

# 27. Online Softmax 就解决这个问题

这是 Lecture 5 最值得亲手推一遍的公式。

假设目前已经处理旧数据。

维护：

$$
m_{\rm old}
===========

\max(\text{old scores})
$$

和：

$$
\ell_{\rm old}
==============

\sum_{\rm old}
e^{x_i-m_{\rm old}}.
$$

现在来一个新 tile。

它自己的最大值：

$$
m_{\rm tile}.
$$

新的全局最大值：

$$
\boxed{
m_{\rm new}
===========

\max(m_{\rm old},m_{\rm tile})
}
$$

那么旧 sum 要重新 rescale：

$$
\boxed{
\ell_{\rm new}
==============

e^{m_{\rm old}-m_{\rm new}}
\ell_{\rm old}
+
\sum_{\rm tile}
e^{x_i-m_{\rm new}}
}
$$

为什么？

因为：

$$
e^{x_i-m_{\rm new}}
===================

e^{x_i-m_{\rm old}}
e^{m_{\rm old}-m_{\rm new}}.
$$

所以旧结果不用重算所有元素。

只需要乘一个 correction factor：

$$
e^{m_{\rm old}-m_{\rm new}}.
$$

---

# 28. Output accumulator 也能同样 online 更新

Attention 不只需要：

$$
\sum e^{x_i}
$$

还需要：

$$
\sum_i e^{x_i}v_i.
$$

所以维护一个：

$$
o
=

\sum_i
e^{x_i-m}v_i.
$$

新 tile 来了：

$$
\boxed{
o_{\rm new}
===========

e^{m_{\rm old}-m_{\rm new}}
o_{\rm old}
+
\sum_{\rm tile}
e^{x_i-m_{\rm new}}v_i
}
$$

最后：

$$
\boxed{
O=\frac{o}{\ell}
}
$$

完成。

因此：

```text
Q tile fixed

K/V tile 1
 ↓
update (m, l, o)

K/V tile 2
 ↓
update (m, l, o)

K/V tile 3
 ↓
update (m, l, o)

...

final o/l
```

整个过程中：

$$
\boxed{\text{完整 attention matrix 从来没有写进 HBM}}
$$

这就是 FlashAttention 的核心数学技巧之一。([GitHub][3])

---

# 29. FlashAttention 第二招：Fusion

普通：

```text
matmul
 ↓
softmax
 ↓
matmul
```

三个阶段之间产生巨大中间 tensor。

FlashAttention：

```text
QK tile
 ↓
scale/mask
 ↓
online softmax
 ↓
× V tile
 ↓
accumulate
```

尽可能在一个紧凑的 kernel 流程里完成。

所以：

$$
\boxed{\text{fusion}}
$$

---

# 30. 第三招：Recomputation

Backward 需要 attention probabilities。

传统：

> forward 存下来。

但：

$$
P:[B,H,T,T]
$$

太大。

FlashAttention：

> 不存。

backward：

$$
\boxed{\text{重新从 Q/K 局部计算}}
$$

虽然 FLOPs 增加：

$$
\text{compute}\uparrow
$$

但是 HBM traffic 和 activation memory 大幅下降：

$$
\text{memory traffic}\downarrow.
$$

在 GPU 上反而：

$$
\boxed{\text{更快}}
$$

这正是 Lecture 5 前面所有理论的高潮：

> **用便宜的计算换昂贵的数据移动。**

---

# 31. 所以 FlashAttention 真正“Flash”的地方不是减少 FLOPs

Standard attention：

$$
O(N^2d)
$$

FlashAttention：

$$
O(N^2d)
$$

Big-O 并没有变。

但是 IO complexity 大幅改善。

这跟 Lecture 4 的 Linear Attention 完全不同：

### Linear Attention

修改数学模型：

$$
O(N^2)\rightarrow O(N)
$$

但不再是标准 softmax attention。

### FlashAttention

保持数学模型：

$$
O(N^2)\rightarrow O(N^2)
$$

但：

$$
\boxed{\text{HBM traffic 显著下降}}
$$

所以可以记：

$$
\boxed{
\text{Lecture 4：algorithm/model change}
}
$$

$$
\boxed{
\text{Lecture 5：systems/execution change}
}
$$

---

# 32. 为什么 FlashAttention 是整个 CS336 特别典型的案例？

因为它把四层知识全部串起来：

### 数学

$$
\operatorname{softmax}(QK^\top)V
$$

### 算法

online softmax。

### GPU architecture

```text
HBM
shared memory
register
Tensor Core
```

### Kernel engineering

```text
tiling
fusion
recomputation
coalescing
```

最后得到：

$$
\boxed{\text{相同模型，更快、更省显存}}
$$

这恰恰就是 CS336 所谓：

> Language Modeling **from Scratch**

里的“scratch”真正厉害的地方：不是让你只会 `nn.MultiheadAttention`，而是一路追问到这个操作为什么在 GPU 上这样执行。

---

# 33. Lecture 5 和 A2 是直接连着的

Stanford 2026 官方课程安排是：

```text
Lecture 5: GPUs, TPUs
        ↓
Lecture 6: Kernels, Triton
        ↓
Assignment 2: Systems
```

A2 官方说明明确要求：

* profile / benchmark A1 model；
* 优化 attention；
* 自己实现 Triton FlashAttention2；
* 构建 memory-efficient distributed training。([GitHub][5])

甚至 2026 A2 的 changelog 还说明当年的 handout 已经从 H100 特定描述切换到 **B200/TMA**，说明课程确实在追当前 GPU 硬件。([GitHub][6])

所以如果你之前觉得：

> A2 好像只是在搞 CUDA，学了没啥用？

Lecture 5 给出的答案其实是：

> **你不一定以后天天写 CUDA，但如果完全不知道这一层，你很难判断一个 LLM 架构为什么快、为什么慢。**

---

# 34. 对你来说，Lecture 5 哪些需要真的掌握，哪些可以以后再学？

我会分三层。

## 第一层：必须掌握

不管你以后做 model、agent、inference 还是 infra，都应该会：

$$
\boxed{\text{CPU latency vs GPU throughput}}
$$

$$
\boxed{\text{SM / block / warp / thread}}
$$

$$
\boxed{\text{register/shared memory/HBM hierarchy}}
$$

$$
\boxed{\text{compute-bound vs memory-bound}}
$$

$$
\boxed{\text{fusion}}
$$

$$
\boxed{\text{tiling}}
$$

$$
\boxed{\text{FlashAttention 为什么快}}
$$

这些属于 ML engineer 的基本硬件常识。

---

## 第二层：做 A2 时真正内化

```text
coalescing
control divergence
occupancy
wave quantization
tile size selection
online softmax
recomputation
```

因为光看概念很难真正掌握。

你需要：

```text
写 kernel
↓
benchmark
↓
发现怎么这么慢
↓
改 tile
↓
突然快 3×
```

才能形成肌肉记忆。

---

## 第三层：暂时不用深钻

比如：

```text
Tensor Core microarchitecture
TMA pipeline
async copy
warp specialization
shared-memory bank swizzling
WGMMA
Blackwell instruction details
```

这些更适合 Lecture 6 / A2 / 真正 kernel engineering 时再补。

别因为 Lecture 5 看到了 GPU 芯片结构图就觉得：

> “完了我要先学数字电路。”

完全没必要。

---

# 35. 我希望你学完后能自己解释这个经典例子

假设两个 PyTorch 程序数学完全等价。

### Version A

```python
a = x * x
b = torch.exp(a)
c = b / b.sum(dim=-1, keepdim=True)
y = c * v
```

每个操作单独 kernel。

---

### Version B

写一个 fused kernel：

```text
load x,v
↓
square
↓
exp
↓
online reduction
↓
normalize
↓
multiply v
↓
store y
```

即使：

$$
\boxed{\text{FLOPs 完全差不多}}
$$

Version B 也可能快很多。

为什么？

正确答案不能是：

> GPU 并行比较快。

而应该说：

$$
\boxed{
\text{B 减少 kernel launches 和 HBM intermediate traffic，
中间值停留在 register/shared memory，
因此 arithmetic intensity 更高。}
}
$$

能回答到这里，Lecture 5 就开始学懂了。

---

# 36. 再给你一道非常 CS336 的题

假设一个 kernel 理论：

$$
100\text{ GFLOPs}
$$

另一个：

$$
150\text{ GFLOPs}.
$$

哪个快？

**不能判断。**

还必须知道：

$$
\text{bytes transferred}
$$

例如：

### Kernel A

$$
100G\text{ FLOPs}
$$

但需要：

$$
1TB
$$

HBM traffic。

$$
AI=0.1\text{ FLOP/B}.
$$

### Kernel B

$$
150G\text{ FLOPs}
$$

却只需要：

$$
10GB
$$

traffic。

$$
AI=15\text{ FLOP/B}.
$$

B 虽然“多算 50%”，却很可能更快。

所以 Lecture 5 真正想拆掉的是这种思维：

$$
\boxed{\text{算法 FLOPs 最少 = 运行最快}}
$$

现实硬件世界完全不是这么简单。

---

# 37. Lecture 2 和 Lecture 5 的区别，现在应该特别清楚

Lecture 2：

给你一个 operation，问：

$$
\boxed{\text{理论 FLOPs / bytes 是多少？}}
$$

例如 matmul：

$$
2MNK.
$$

---

Lecture 5：

继续问：

> 那 bytes 到底是从哪里来的？

于是：

```text
HBM
↓
L2
↓
shared memory
↓
register
↓
Tensor Core
```

再问：

> 能不能让一个 byte 被复用 32 次？

于是：

$$
\boxed{\text{tiling}}
$$

再问：

> 中间结果能不能不回 HBM？

于是：

$$
\boxed{\text{fusion}}
$$

再问：

> 与其存下来，能不能重算？

于是：

$$
\boxed{\text{recomputation}}
$$

Lecture 5 就是把 Roofline **具象化**。

---

# 38. Lecture 3–5 也能形成一条特别漂亮的 Attention 演化线

### Lecture 3

数学是什么：

$$
\boxed{\operatorname{softmax}(QK^\top)V}
$$

### Lecture 4

模型层面怎么少算：

```text
Linear Attention
Mamba
Gated DeltaNet
Sparse Attention
```

改变 interaction structure。

### Lecture 5

数学不变，怎么在 GPU 上跑得快：

$$
\boxed{\text{FlashAttention}}
$$

```text
tiling
online softmax
fusion
recomputation
```

这两个方向千万不要混：

$$
\boxed{\text{算法复杂度优化}}
\neq
\boxed{\text{硬件执行优化}}
$$

---

# 39. 最后，Lecture 5 真正要你形成的是这套“性能排查顺序”

以后遇到：

> 为什么这段 PyTorch 慢？

不要直接：

```text
换 GPU！
```

先问：

### ① 它是什么 workload？

$$
\text{elementwise? reduction? GEMM? attention?}
$$

### ② 算多少？

$$
\text{FLOPs}
$$

### ③ 搬多少？

$$
\text{HBM bytes}
$$

### ④ Arithmetic intensity？

$$
AI=\frac{FLOPs}{bytes}
$$

### ⑤ memory-bound 还是 compute-bound？

Roofline。

### ⑥ memory-bound 怎么办？

```text
fusion
tiling
coalescing
lower precision
recomputation
```

### ⑦ GPU utilization 为什么还有异常？

```text
warp divergence
tile shape
occupancy
wave quantization
alignment
```

### ⑧ 最后：

$$
\boxed{\text{benchmark + profile}}
$$

而不是凭感觉优化。

这实际上就是 Lecture 6 接下来要正式进入的世界。

---

# 40. 我给你八道 Lecture 5 自测题

如果这八题能从头解释，基本就是真懂了：

1. **为什么 GPU 比 CPU 更适合 Transformer？**
   不准只回答“核心多”，要讲 throughput、SIMT、GEMM。

2. **thread、warp、block、SM 分别是什么关系？**

3. **为什么 HBM 明明叫 High Bandwidth Memory，还是 GPU 性能瓶颈？**
   因为 compute throughput 增长更快，而且片上 memory 更快。

4. **为什么 fusion 不减少数学 FLOPs，却能快很多？**

5. **为什么 recomputation 有时候增加 FLOPs 反而提升速度？**

6. **为什么 (1024\times1024) 的矩阵可能比 (1000\times1000) 跑得更舒服？**
   tile/Tensor Core/alignment/wave utilization。

7. **为什么 FlashAttention 是 exact attention，却比 naive attention 快很多？**
   一定要说 tiling + online softmax + 少 materialize (N^2) intermediate + recomputation。

8. **FlashAttention 和 Linear Attention 的区别是什么？**

   $$
   \boxed{\text{FA：同样的数学，更好的 IO}}
   $$

   $$
   \boxed{\text{Linear Attention：修改数学结构，降低复杂度}}
   $$

---

如果把 Lecture 5 压成一句我希望你以后永远记得的话，就是：

$$
\boxed{
\textbf{GPU programming 的核心不是让 GPU 少做计算，
而是让昂贵的数据尽可能少移动，
让搬进来的每个 byte 尽可能多做计算。}
}
$$

这就是为什么 **tiling、fusion、recomputation 和 FlashAttention** 看似是四个知识点，其实全部在做同一件事。

而下一讲 Lecture 6 的 Triton，本质上就是：

> **好，现在这些道理你都懂了，我们真的写一个 kernel，把这些 hardware intuition 变成代码。**

官方 2026 A2 也正是顺着这条路让你从 benchmark/profile 一路做到自己的 FlashAttention。
