---
title: "L06 · Triton"
weight: 6
date: 2026-08-28
updated: 2026-08-28
course: "CS336"
topics: ["CS336", "triton", "kernels"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture6/
---

Lecture 6 是前五讲里第一次真正从“我知道 GPU 为什么快”进入：

$$
\boxed{\text{那我到底怎么亲手写一个快的 GPU kernel？}}
$$

Stanford CS336 Spring 2026 官方课程表把 Lecture 6 定义为 **“Kernels, Triton [Percy]”**，时间是 4 月 15 日；同一天 A1 截止、A2 Systems 发布。([GitHub][1])

而官方 `lecture_06.py` 一开头就把目标写得非常明确：

> 上一讲：GPU 和性能的高层概览；这一讲：**benchmarking / profiling + writing kernels**。

整讲依次做四个 Triton kernel：

$$
\boxed{
\text{GeLU}
\rightarrow
\text{Softmax}
\rightarrow
\text{Row Sum}
\rightarrow
\text{MatMul + ReLU}
}
$$

分别对应：

```text
elementwise
   ↓
reduction
   ↓
reduction + tiling
   ↓
2D tiling + matrix multiply + fusion
```

而且准确地说，**Lecture 6 本身还没有直接手写 FlashAttention**；它是在给 A2 的 FlashAttention/Triton 实现铺地基。官方总结也明确列出了这四个例子。

---

# 一、先抓住 Lecture 6 的核心思想

Lecture 5 告诉你：

$$
\boxed{\text{尽量少搬数据}}
$$

Lecture 6 告诉你怎么把这句话写成代码：

$$
\boxed{
\text{HBM}
\rightarrow
\text{load 一个 tile}
\rightarrow
\text{片上做尽可能多的事情}
\rightarrow
\text{store 回 HBM}
}
$$

官方最后甚至直接把 Triton 的思维总结成：

> think in terms of thread blocks: read to shared memory, do stuff (fusion), write back HBM. 

所以你学 Triton 时千万不要形成：

> “这是另一种 Python 语法。”

正确理解是：

> **Triton 是让你显式决定“一块数据怎么从显存搬进来、在 GPU 上怎么一起计算、什么时候再写回去”的语言。**

---

# 二、Lecture 6 先复习 GPU，但重点跟 Lecture 5 不一样

Lecture 5 是：

> GPU 有哪些部件？

Lecture 6 是：

> **这些部件会怎样限制我写的 kernel？**

官方给出了一个非常漂亮的三级对应关系：

$$
\boxed{
\text{Grid / HBM}
\rightarrow
\text{Thread Block / Shared Memory}
\rightarrow
\text{Thread / Registers}
}
$$



粗略理解：

```text
整个任务 Grid
│
├── Block 0 ───── 某个 SM
│      ├── thread
│      ├── thread
│      └── thread
│
├── Block 1 ───── 另一个 SM
│
└── ...
```

为什么需要 block？

对于：

```python
y[i] = gelu(x[i])
```

每个元素互不相关，一个 thread 干一个元素就够了。

但 softmax：

$$
y_i
===

\frac{e^{x_i}}
{\sum_j e^{x_j}}
$$

第 (i) 个输出必须知道整行：

$$
\sum_j e^{x_j}.
$$

不同线程必须**交流**。

而从 HBM 交流太慢，于是：

$$
\boxed{\text{同一个 block 的 threads 共享片上 shared memory}}
$$

因此一个 block 必须调度到同一个 SM。官方 Lecture 6 正是这样解释 thread block 存在的意义。

---

# 三、写 kernel 前，你需要知道四种“性能陷阱”

这部分就是 Lecture 5 的硬件知识真正开始有用了。

## 1. Warp divergence

一个 warp：

$$
32\text{ threads}
$$

一起执行。

如果：

```python
if condition:
    A()
else:
    B()
```

其中一半 thread 走 A，一半走 B，GPU 往往必须：

```text
先跑 A
一部分线程闲着

再跑 B
另一部分线程闲着
```

所以：

$$
\boxed{\text{warp 内控制流越一致越好}}
$$

官方讲义明确把这称为 control divergence。

---

# 四、Occupancy 不是“越高越好”

这是 Lecture 6 一个很值得纠正直觉的点。

假设每个 thread 用：

$$
160\text{ registers}.
$$

一个 block 有：

$$
128\text{ threads}.
$$

那么一个 block 消耗：

$$
128\times160=20480
$$

个 registers。

如果一个 SM 总共只有：

$$
65536
$$

registers，那么同一时间最多只能放：

$$
\left\lfloor
\frac{65536}{20480}
\right\rfloor
=============

3
$$

个 blocks。

register 用得越多：

$$
\boxed{\text{同时 resident 的 warps 越少}}
$$

也就是 occupancy 下降。

但官方特别提醒：

> **low occupancy isn't necessarily bad if each thread is doing more work.**



这句话很重要。

不能变成：

$$
\text{Occupancy}=100%
\Rightarrow
\text{性能最好}.
$$

如果每个 thread 多用一些 registers，却减少 HBM 访问、增加 reuse，也可能整体更快。

所以：

$$
\boxed{
\text{occupancy 是手段，不是目标}
}
$$

---

# 五、Bank Conflict 和 Memory Coalescing 别混

这两个一个发生在：

$$
\boxed{\text{shared memory}}
$$

一个发生在：

$$
\boxed{\text{HBM/global memory}}
$$

---

## Bank conflict

Lecture 6 简化地把 shared memory 想成 32 个 banks。

如果 warp 的 32 threads：

```text
T0 → bank 0
T1 → bank 1
...
T31 → bank 31
```

很好，可以并行。

但如果：

```text
T0  → bank 0
T1  → bank 0
T2  → bank 0
...
```

而又不是访问完全同一个地址，那么这些访问可能被串行化：

$$
\boxed{\text{bank conflict}}
$$

官方还提到 swizzling：

> 重新排列 shared-memory layout，例如利用 row xor col，减少 bank conflicts。

现在先知道概念即可，A2 深入优化时再研究 swizzle。

---

## Memory coalescing

发生在 HBM。

一个 warp 的 32 threads 如果访问：

```text
x[0]
x[1]
x[2]
...
x[31]
```

假设每个元素 4 bytes，刚好：

$$
32\times4=128B.
$$

GPU 可以把它们合并成很少的 memory transaction。

这叫：

$$
\boxed{\text{coalesced access}}
$$

官方 Lecture 6 用的理想例子也是 32 threads × 4 bytes = 128-byte cache line。

所以以后写 Triton pointer arithmetic，你脑中不能只有：

> 地址算对了吗？

还应该有：

> **邻近 lanes 最后是不是在读邻近地址？**

---

# 六、Block occupancy：你还要把整个 GPU 填满

假设 B200：

$$
148\text{ SMs}.
$$

你 launch：

$$
160\text{ blocks}.
$$

第一波：

```text
148 blocks
↓
148 SMs 全满
```

剩下：

$$
12\text{ blocks}.
$$

第二波：

```text
12 SM 工作
136 SM 闲着
```

所以尾巴利用率极差。

这就是 Lecture 6 再次强调的：

$$
\boxed{\text{wave quantization}}
$$



这也解释为什么 GPU 性能有时随着 tensor shape 呈现非常奇怪的锯齿，而不是数学 FLOPs 对应的一条平滑线。

---

# 七、然后 Lecture 6 做了一件非常重要的事：先 Benchmark，再谈优化

Percy 给出的 recipe 非常简单：

$$
\boxed{
1.\ Benchmark/Profile
\rightarrow
2.\ Modify
\rightarrow
3.\ Benchmark/Profile\ again
}
$$



这是 systems 里非常重要的方法论。

不要：

```text
“我觉得这样应该比较快”
```

而是：

```text
measure
↓
find bottleneck
↓
change
↓
measure again
```

---

# 八、Benchmark 和 Profile 是两件不同的事

## Benchmark

回答：

$$
\boxed{\text{到底花了多久？}}
$$

比如：

```text
matmul 1024 → 0.05 ms
matmul 2048 → 0.20 ms
matmul 4096 → 1.50 ms
```

它适合比较：

```text
implementation A vs B
```

或者看：

$$
\text{runtime 随 shape 怎样 scaling}.
$$

官方讲义就是这样定义 benchmarking 的。

---

## Profiling

回答：

$$
\boxed{\text{时间到底花在哪？}}
$$

例如：

```text
aten::xxx
cuda kernel A
cuda kernel B
CUTLASS GEMM
...
```

你甚至可以看到 PyTorch 对不同 matrix shape 调用了完全不同的 CUDA kernels；官方例子还拆解了类似：

```text
cutlass3x_sm100_simt_sgemm_...
```

其中：

* CUTLASS：NVIDIA linear algebra library；
* `sm100`：Blackwell；
* `f32`：dtype；
* `64x64x16`：tile shape。

所以：

$$
\boxed{
\text{benchmark = 多快}
}
$$

$$
\boxed{
\text{profile = 为什么是这个速度}
}
$$

---

# 九、GPU Benchmark 有一个巨坑：CUDA 是异步的

假设：

```python
start = time.time()
y = x @ x
end = time.time()
```

你以为：

$$
end-start
$$

是 matmul 时间？

不一定。

CPU 可能只是告诉 GPU：

> “你之后帮我算这个。”

然后 CPU 就继续跑了。

所以必须：

$$
\boxed{\texttt{torch.cuda.synchronize()}}
$$

等待 GPU 真正完成。

官方 benchmark 还使用 CUDA Events：

```python
start_event.record()
run()
end_event.record()

torch.cuda.synchronize()

elapsed = start_event.elapsed_time(end_event)
```

并且先做 warmup，因为第一次执行可能包含编译等额外开销。

这是你以后做任何 GPU benchmark 都必须牢记的东西：

$$
\boxed{
\text{不 synchronize 的 timing 很可能测的是 launch，而不是 computation}
}
$$

---

# 十、Lecture 6 的第一个漂亮案例：为什么“数学一样”的 GeLU 差这么多？

GeLU 的 tanh approximation：

$$
\operatorname{GELU}(x)
\approx
\frac12x
\left[
1+
\tanh
\left(
\sqrt{\frac2\pi}
(x+0.044715x^3)
\right)
\right].
$$

你可以非常自然地用 PyTorch 写：

```python
0.5 * x * (
    1 + torch.tanh(
        0.79788456 * (x + 0.044715 * x*x*x)
    )
)
```

数学完全正确。

但 PyTorch eager 可能把它拆成多个 operations：

```text
x*x
 ↓
kernel

*x
 ↓
kernel

add
 ↓
kernel

multiply
 ↓
kernel

tanh
 ↓
kernel

...
```

于是：

```text
HBM → kernel → HBM
HBM → kernel → HBM
HBM → kernel → HBM
...
```

官方 profile 发现 naive 版本对应多个 kernels，而 built-in 和 `torch.compile` 版本可以融合成单 kernel；讲义还明确指出 compiled kernel 是 Triton kernel。

这就是：

$$
\boxed{\text{kernel fusion}}
$$

---

# 十一、所以 `torch.compile` 为什么经常变快？

你可以把一个重要场景粗略理解成：

```python
PyTorch graph
     ↓
compiler 看见多个 operations
     ↓
发现可以 fusion
     ↓
生成一个 Triton kernel
```

于是：

```text
读 x 一次
↓
x³
↓
linear combination
↓
exp/tanh
↓
multiply
↓
最后写 y 一次
```

中间值尽可能不 materialize 到 HBM。

所以从：

$$
\text{many HBM round-trips}
$$

变成：

$$
\boxed{
1\times read
+
1\times write
}
$$

Lecture 6 正是用 GeLU 把 Lecture 5 的 fusion 从概念变成 profiler 里真的能看到的东西。

---

# 十二、现在终于正式进入 Triton

这是整讲的分水岭。

官方给出的 CUDA vs Triton 区别非常简洁：

### CUDA

你主要告诉系统：

$$
\boxed{\text{每个 thread 做什么}}
$$

优点：

> 控制极细。

缺点：

> shared memory 等大量细节自己管。

### Triton

Lecture 6 的教学抽象是：

$$
\boxed{\text{告诉系统一个 thread block / program instance 做什么}}
$$

然后编译器帮你映射到底层线程。

更贴近 Triton 的说法是：

> 你写的是一个 **program instance 对一个 block/tile 的向量化计算**，而不是手动写 1024 个 CUDA thread 各自的代码。

这个认知非常重要。

---

# 十三、Triton 最重要的几个语法先搞懂

假设：

```python
@triton.jit
def kernel(...):
    ...
```

这是一个 GPU kernel。

---

## `tl.program_id`

```python
pid = tl.program_id(0)
```

意思是：

> **我现在是 grid 中的第几个 program/block？**

比如：

```text
program 0 → elements 0..1023
program 1 → elements 1024..2047
program 2 → elements 2048..3071
```

---

## `tl.arange`

```python
offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
```

比如：

$$
BLOCK_SIZE=8,\quad pid=2
$$

那么：

$$
offsets=
[16,17,18,19,20,21,22,23].
$$

这一个 Triton program 同时操作一整块数据。

---

## `tl.load`

```python
x = tl.load(x_ptr + offsets)
```

把对应位置读进来。

概念上：

$$
\boxed{\text{HBM → on-chip values}}
$$

---

## `tl.store`

```python
tl.store(y_ptr + offsets, y)
```

概念上：

$$
\boxed{\text{on-chip values → HBM}}
$$

---

# 十四、Mask 是 Triton 初学者必须马上理解的东西

假设 tensor 有：

$$
N=1000
$$

个元素。

而：

$$
BLOCK_SIZE=256.
$$

需要：

$$
\lceil1000/256\rceil=4
$$

个 blocks。

最后一个 block：

```text
768 ... 999       ← 有效
1000 ... 1023     ← 越界
```

所以：

```python
mask = offsets < num_elements

x = tl.load(
    x_ptr + offsets,
    mask=mask
)

tl.store(
    y_ptr + offsets,
    y,
    mask=mask
)
```

也就是说：

$$
\boxed{\text{让规则 tile 覆盖不规则 tensor 边界}}
$$

官方 GeLU kernel 正是这么写的。

这也是 GPU kernel 常见哲学：

> 与其为尾巴写特殊控制逻辑，不如把任务 padding/tiling 成规则 shape，再用 mask 屏蔽无效 lane。

---

# 十五、第一个 Triton Kernel：GeLU

官方 kernel 核心其实非常短：

```python
pid = tl.program_id(0)

offsets = (
    pid * BLOCK_SIZE
    + tl.arange(0, BLOCK_SIZE)
)

mask = offsets < N

x = tl.load(
    x_ptr + offsets,
    mask=mask
)

# whole GeLU math here

tl.store(
    y_ptr + offsets,
    y,
    mask=mask
)
```



注意和普通 PyTorch 的最大区别：

PyTorch：

```text
我在描述数学运算
```

Triton：

```text
我同时在描述

数学运算
+
数据分块
+
内存访问
+
并行任务划分
```

这就是 systems programming。

---

# 十六、Triton 最终会编译到 PTX

Lecture 6 甚至让学生看生成的 PTX。

官方指出可以观察：

```text
ld.global.*
st.global.*
```

这些就是 global memory load/store。

还会看到：

```text
%ctaid.x
%tid.x
```

分别对应 block/thread 层面的索引，以及浮点/整数 registers。

你现在不用学会写 PTX。

重点是认识这个层级：

```text
PyTorch / Triton source
        ↓
compiler
        ↓
PTX
        ↓
GPU execution
```

所以 Triton 并不是模拟 GPU：

$$
\boxed{\text{它最后真的生成 GPU machine-level work}}
$$

---

# 十七、第二个例子 Softmax：第一次遇到 Reduction

GeLU：

$$
y_i=f(x_i)
$$

每个元素互不依赖。

Softmax：

$$
y_i
===

\frac{e^{x_i-m}}
{\sum_j e^{x_j-m}}
$$

其中：

$$
m=\max_jx_j.
$$

每个 output 都依赖整行。

这是：

$$
\boxed{\text{reduction}}
$$

于是 thread/block abstraction 开始真正体现价值。

---

# 十八、Naive Softmax 为什么这么浪费 HBM？

官方把 memory traffic 算得非常细。

输入：

$$
X\in\mathbb R^{M\times N}.
$$

### Step 1：max

读取：

$$
MN
$$

写：

$$
M.
$$

### Step 2：减 max

读取：

$$
MN+M
$$

写：

$$
MN.
$$

### Step 3：exp

读取：

$$
MN
$$

写：

$$
MN.
$$

### Step 4：sum

读取：

$$
MN
$$

写：

$$
M.
$$

### Step 5：normalize

读取：

$$
MN+M
$$

写：

$$
MN.
$$

最终官方统计：

$$
\boxed{5MN+M\text{ reads}}
$$

和：

$$
\boxed{3MN+2M\text{ writes}}
$$



但理论上呢？

每个输入其实：

$$
\boxed{\text{读一次就够了}}
$$

每个输出：

$$
\boxed{\text{写一次就够了}}
$$

所以理想：

$$
MN\text{ reads}+MN\text{ writes}.
$$

这就是 fusion 的巨大空间。

---

# 十九、Fused Softmax 的 Triton 思维

如果一整行能放进一个 block：

```text
Row 0 → Program 0
Row 1 → Program 1
Row 2 → Program 2
...
```

每个 program：

```text
load 整行
↓
max
↓
subtract
↓
exp
↓
sum
↓
divide
↓
store 整行
```

中间：

$$
x_{\max},e^x,\sum e^x
$$

都不需要写回 HBM。

官方 kernel 就是：

```python
row_idx = tl.program_id(0)

x_row = tl.load(...)

x_row -= tl.max(x_row)
numerator = tl.exp(x_row)
denominator = tl.sum(numerator)

y_row = numerator / denominator

tl.store(...)
```



这几行已经非常接近数学公式了。

但它同时实现了：

$$
\boxed{\text{整个 softmax fusion}}
$$

---

# 二十、为什么 `next_power_of_2(N)`？

官方做：

```python
BLOCK_SIZE = triton.next_power_of_2(N)
```

例如：

$$
N=1000
$$

就选：

$$
1024.
$$

原因还是 GPU 喜欢规则块。

然后对于：

$$
1000\ldots1023
$$

这些无效位置，load：

$$
-\infty.
$$

为什么是：

$$
-\infty
$$

而不是 0？

因为 softmax：

$$
e^{-\infty}=0.
$$

所以 padding 不会影响：

$$
\max
$$

或：

$$
\sum e^x.
$$

这就是一个非常漂亮的：

$$
\boxed{\text{数学语义 + mask implementation}}
$$

组合。官方 kernel 正是 `other=float("-inf")`。

---

# 二十一、但如果一整行根本塞不进一个 block 呢？

这就是第三个例子：

$$
\boxed{\text{Row Sum}}
$$

Lecture 6 故意先不做更复杂的 softmax，而换成简单：

$$
y_i=\sum_jx_{ij}
$$

来解释 tiling。

例如：

$$
N=4096
$$

但是：

$$
BLOCK_SIZE=1024.
$$

那么一行：

```text
tile 0 | tile 1 | tile 2 | tile 3
```

---

# 二十二、Baby Tiling：每个 thread 处理多个元素

例如简化成：

```text
N = 12
BLOCK_SIZE = 4
```

可以理解成：

```text
tile 0:
x0 x1 x2 x3

tile 1:
x4 x5 x6 x7

tile 2:
x8 x9 x10 x11
```

4 个逻辑 lane：

```text
lane 0:
x0 + x4 + x8

lane 1:
x1 + x5 + x9

lane 2:
x2 + x6 + x10

lane 3:
x3 + x7 + x11
```

得到 accumulator：

$$
[a_0,a_1,a_2,a_3].
$$

然后最后：

$$
a_0+a_1+a_2+a_3.
$$

官方代码：

```python
acc = tl.zeros(
    [BLOCK_SIZE],
    dtype=tl.float32
)

for start in range(
    0, N, BLOCK_SIZE
):
    cols = start + tl.arange(
        0, BLOCK_SIZE
    )
    x = tl.load(...)
    acc += x

result = tl.sum(acc)
```



这就是第一个真正的：

$$
\boxed{\text{tile loop}}
$$

---

# 二十三、这里顺便出现 Thread Coarsening

最朴素想法：

> 一个 thread = 一个 element。

但 row sum 中：

> 一个逻辑 lane/thread 连续处理多个 elements。

这就是：

$$
\boxed{\text{thread coarsening}}
$$

为什么可能有好处？

因为：

```text
更少 threads
+
每个 thread 做更多工作
+
更多数据留在 registers
```

代价：

$$
\text{register pressure}\uparrow
$$

可能导致：

$$
\text{occupancy}\downarrow.
$$

这就是为什么 Lecture 6 前面特意告诉你：

> low occupancy 不一定就是坏事。

整堂课这些知识不是散的。

---

# 二十四、第四个例子：MatMul，真正进入高性能 kernel 的核心

现在考虑：

$$
C=AB
$$

其中：

$$
A\in\mathbb R^{M\times K}
$$

$$
B\in\mathbb R^{K\times N}.
$$

Naive 方法：

对于每个：

$$
C_{mn}
$$

循环：

$$
k=1,\dots,K
$$

不断：

```text
read A[m,k]
read B[k,n]
multiply
accumulate
```

于是大约需要：

$$
MKN
$$

级别 HBM reads。

Arithmetic intensity：

$$
O(1).
$$

官方正是这么分析 naive matmul。

---

# 二十五、为什么这是巨大的浪费？

计算：

$$
C_{m,n}
$$

需要：

$$
A_{m,:}.
$$

计算：

$$
C_{m,n+1}
$$

也需要：

$$
A_{m,:}.
$$

如果每次都重新从 HBM 加载：

$$
A_{m,:}
$$

实在太蠢。

理想情况：

> 把 A/B 全塞 shared memory，再一直复用。

那 HBM reads 可以从：

$$
O(MKN)
$$

变成：

$$
O(MK+KN).
$$

但是：

$$
A,B
$$

通常太大。

于是唯一自然的答案就是：

$$
\boxed{\text{Tiling}}
$$

---

# 二十六、MatMul Tiling 一定要在脑子里真正画出来

把 C 切成：

$$
BLOCK_M\times BLOCK_N
$$

的小块。

例如：

$$
64\times64.
$$

一个 program instance 负责：

```text
C tile

rows m ... m+63
cols n ... n+63
```

但为了计算它，需要沿 K 方向不断扫：

```text
A tile 1 × B tile 1
        ↓
     accumulate

A tile 2 × B tile 2
        ↓
     accumulate

...

A tile r × B tile r
        ↓
     accumulate
```

于是：

$$
\boxed{
C_{\text{tile}}
===============

\sum_k
A_{\text{tile},k}
B_{k,\text{tile}}
}
$$

---

# 二十七、官方 kernel 的三个 block size 到底分别是什么？

Lecture 6：

$$
BLOCK_M=64
$$

$$
BLOCK_N=64
$$

$$
BLOCK_K=32.
$$



所以每次 load：

$$
A_{\rm tile}:
64\times32
$$

以及：

$$
B_{\rm tile}:
32\times64.
$$

做：

$$
[64,32][32,64]
\rightarrow
[64,64].
$$

然后：

$$
acc
$$

始终是：

$$
64\times64.
$$

接着 K 向前推进 32：

```text
K = 0..31
↓
K = 32..63
↓
K = 64..95
...
```

不断累加。

---

# 二十八、这段 `tl.dot` 就是 Tensor Core 世界的入口

官方：

```python
acc += tl.dot(a, b)
```

其中：

$$
a:
[BLOCK_M,BLOCK_K]
$$

$$
b:
[BLOCK_K,BLOCK_N].
$$

Triton/compiler 会负责把它进一步映射到适合硬件的 matrix multiply 路径。

你终于不用自己写：

```python
for i:
    for j:
        for k:
```

但你仍然显式控制：

$$
\boxed{
\text{tile shape}
+
\text{memory access}
+
\text{accumulation}
}
$$

这就是 Triton 最漂亮的抽象层级。

---

# 二十九、为什么 accumulator 用 FP32？

官方：

```python
acc = tl.zeros(
    [BLOCK_M, BLOCK_N],
    dtype=tl.float32
)
```



原因和前面 mixed precision 完全接上。

matmul 是：

$$
\sum_{k=1}^K a_kb_k.
$$

可能累加很多项。

即使输入是较低精度，让 accumulator 保持更高精度通常有利于：

$$
\boxed{\text{numerical accuracy/stability}}
$$

所以：

```text
low precision multiply
+
higher precision accumulation
```

是现代矩阵计算中非常常见的模式。

---

# 三十、MatMul + ReLU 为什么是 Lecture 6 最漂亮的结尾？

因为算完：

$$
AB
$$

之后，官方直接：

```python
acc = tl.maximum(acc, 0.0)
```

然后才 store。

也就是说：

### Naive

```text
matmul
↓
C 写 HBM

C 读回来
↓
ReLU
↓
Y 写 HBM
```

### Fused

```text
matmul accumulator
仍在片上
↓
ReLU
↓
只写一次
```

所以：

$$
\boxed{
\operatorname{ReLU}(AB)
}
$$

只需一次最终输出写回。

这把前面所有知识统一起来了：

$$
\boxed{
\text{tiling}
+
\text{data reuse}
+
\text{fusion}
}
$$

---

# 三十一、Stride 又为什么突然出现？

因为真实 tensor 并不一定就是：

$$
\text{address}=row\times N+col.
$$

一般：

$$
\boxed{
\text{address}
==============

row\times stride_{row}
+
col\times stride_{col}
}
$$

Lecture 6 先用 PyTorch：

```python
x.stride()
```

演示二维 tensor 如何 linearize，再在 matmul kernel 中显式传：

```text
stride_am
stride_ak

stride_bk
stride_bn

stride_cm
stride_cn
```



这一步非常重要，因为你开始离开：

> tensor 是抽象二维表格。

进入：

> **tensor 本质上是一段 linear memory + shape + stride。**

这是真正做 kernel 必须掌握的 mental model。

---

# 三十二、现在可以总结四个例子到底在递进什么了

## GeLU

教：

$$
\boxed{\text{elementwise + fusion}}
$$

```text
one block → 一串 elements
load once
compute whole formula
store once
```

---

## Softmax

教：

$$
\boxed{\text{reduction + fusion}}
$$

```text
one block → one row
max
exp
sum
normalize
```

全在片上完成。

---

## Row Sum

教：

$$
\boxed{\text{当数据放不进一个 block 时怎么办}}
$$

答案：

$$
\boxed{\text{tiling + accumulation}}
$$

---

## MatMul + ReLU

教：

$$
\boxed{\text{2D tiling + reuse + dot + fusion}}
$$

这是现代 deep learning kernel 最重要的模式。

官方 Lecture 6 的总结就是这个四级递进。

---

# 三十三、所以 Triton kernel 可以抽象成一个非常通用的模板

以后看大多数 kernel，可以先尝试套：

```python
@triton.jit
def kernel(...):

    # 1. 我负责哪个 tile？
    pid = tl.program_id(...)

    # 2. 这个 tile 对应哪些 indices？
    offsets = ...

    # 3. 从 HBM load
    x = tl.load(...)

    # 4. 尽可能在片上做大量计算
    ...
    ...

    # 5. 最终 store
    tl.store(...)
```

复杂 kernel 无非是在第 4 步越来越复杂。

例如 FlashAttention：

```text
我负责哪个 Q tile？
↓
load Q
↓
循环 K/V tiles
↓
QKᵀ
↓
online softmax
↓
×V
↓
accumulate O
↓
store O
```

所以学完 Lecture 6，再看 FlashAttention，不应该感觉它是另一门技术。

它只是：

$$
\boxed{\text{MatMul tiling + Reduction + Fusion 的组合升级版}}
$$

---

# 三十四、为什么 FlashAttention 正好把 Lecture 6 的所有例子全用上？

看看它：

$$
O=\operatorname{softmax}(QK^\top)V.
$$

需要：

### MatMul

$$
QK^\top.
$$

→ Lecture 6 的 matmul tiling。

### Row max

$$
m_i=\max_jS_{ij}.
$$

→ reduction。

### exp / scaling

→ elementwise fusion。

### Row sum

$$
\ell_i=\sum_j e^{S_{ij}-m_i}.
$$

→ reduction。

### 再 matmul

$$
PV.
$$

→ tiled matmul。

于是：

$$
\boxed{
\text{FlashAttention}
=====================

\text{Lecture 6 四个例子的综合题}
}
$$

A2 2026 的 changelog 也明确记录了 FlashAttention2，以及后来把 backward 更新成 FA3-style 两遍设计；同时 A2 使用更详细的 Nsight profiling。([GitHub][2])

---

# 三十五、`torch.compile` 和手写 Triton，那我为什么还要学 Triton？

这是一个非常现实的问题。

既然：

```python
torch.compile(naive_gelu)
```

都能自动 fusion，为什么还手写？

因为 compiler 只能优化它识别并能安全转换的模式。

对于：

```text
普通 elementwise chains
```

它往往很强。

但是 FlashAttention、特殊 normalization、稀疏 kernel、特殊 layout 等场景：

> 你可能知道一个更好的算法和数据流，而 compiler 不一定能自己发明出来。

于是有三个层级：

```text
PyTorch eager
↓
torch.compile
↓
custom Triton kernel
↓
必要时 CUDA / 更底层
```

并不是：

> Triton 比 PyTorch 高级，所以全部重写。

正确策略是：

$$
\boxed{\text{能让 compiler 做就让 compiler 做；热点 kernel 值得手工优化时再下沉。}}
$$

---

# 三十六、Lecture 6 真正希望你形成的不是“Triton 语法记忆”

官方最后给出三个层次：

> programming model 给 correctness；hardware knowledge 决定 performance；benchmark/profile 验证实际效果。

我会把它重新写成：

$$
\boxed{
\text{Correctness}
\rightarrow
\text{Mapping}
\rightarrow
\text{Measurement}
}
$$

---

## 1. Correctness

先问：

$$
\boxed{\text{数学结果对不对？}}
$$

和 PyTorch reference：

```python
torch.allclose(...)
```

比较。

---

## 2. Mapping

然后问：

```text
block 怎么分？
tile 多大？
load 是否连续？
register 用多少？
shared memory 怎么复用？
是否能 fusion？
是否产生 bank conflict？
```

---

## 3. Measurement

最后：

```text
benchmark
profile
benchmark
profile
```

绝对不能反过来靠感觉。

---

# 三十七、你以后写 Triton 时，我建议固定问自己这八个问题

### ① 一个 program instance 负责什么？

一个：

```text
element block?
row?
matrix tile?
Q tile?
```

必须说清。

### ② 从 HBM 读什么？

明确：

$$
\boxed{\text{loads}}
$$

### ③ 写回什么？

明确：

$$
\boxed{\text{stores}}
$$

### ④ 哪些中间结果根本没必要回 HBM？

这些就是 fusion 候选。

### ⑤ 数据能不能复用？

不能就可能 memory-bound。

### ⑥ 如果放不下怎么办？

$$
\boxed{\text{tile}}
$$

### ⑦ tile 大小选多少？

考虑：

```text
register pressure
shared memory
occupancy
tensor core shapes
wave utilization
```

### ⑧ 最后到底快了吗？

$$
\boxed{\text{benchmark/profile}}
$$

---

# 三十八、我最希望你能手推的三个 kernel

如果真的准备学 A2，不需要现在从零写 FlashAttention。

先做到：

## 第一关：Fused GeLU

你应该能自己写出：

```text
pid
offsets
mask
load
GeLU
store
```

理解：

$$
\boxed{\text{elementwise fusion}}
$$

---

## 第二关：Fused Softmax

你应该真正理解：

```text
one program = one row
```

以及：

$$
\boxed{
load
\rightarrow
max
\rightarrow
exp
\rightarrow
sum
\rightarrow
normalize
\rightarrow
store
}
$$

为什么能把多个 HBM round trips 消掉。

---

## 第三关：Tiled MatMul

这是最重要的。

一定要能在纸上画：

$$
BLOCK_M\times BLOCK_K
$$

的 A tile，

$$
BLOCK_K\times BLOCK_N
$$

的 B tile，

如何累计为：

$$
BLOCK_M\times BLOCK_N
$$

的 C tile。

只要这个真的理解了：

$$
\boxed{\text{FlashAttention 的 tiling 才有可能理解。}}
$$

---

# 三十九、Lecture 5 和 Lecture 6 的区别可以这样记

Lecture 5：

$$
\boxed{\text{为什么这样会快？}}
$$

讲：

```text
HBM
shared memory
register
Tensor Core
fusion
tiling
```

Lecture 6：

$$
\boxed{\text{怎么真正写出来？}}
$$

讲：

```text
program_id
grid
offsets
mask
load/store
reduction
stride
tl.dot
```

因此：

$$
\boxed{
\text{Lecture 5 = hardware intuition}
}
$$

$$
\boxed{
\text{Lecture 6 = kernel programming intuition}
}
$$

---

# 四十、而 Lecture 6 → A2 的连接非常直接

2026 A2 是当天发布的 Systems assignment。官方 repo 说明，你要从 A1 的语言模型实现出发，在 `cs336_systems` 中做优化和分布式训练；2026 changelog 进一步明确包含 Triton/FlashAttention、Nsight profiling、activation checkpointing、FSDP，以及两张 B200 上的完整 forward/backward 优化。([GitHub][3])

甚至 2026 leaderboard 的目标已经不是一个孤立 kernel，而是：

$$
\boxed{\text{两张 B200 上 8B 模型的完整 training step wall-clock time}}
$$

naive baseline 为 10 秒左右，并鼓励学生继续优化 tile sizes、Triton、fused AdamW、LM-head + cross-entropy fusion、FlashAttention backward、TMA 等。([GitHub][4])

所以 Lecture 6 的最终目的并不是：

> 会写一个 `tl.load()`。

而是：

> **开始拥有“从 PyTorch graph 一直往下追到 GPU kernel”的能力。**

---

# 最后，我给你 8 道 Lecture 6 自测题

如果你都能不看答案解释出来，这讲就算真正学懂了。

1. **Benchmark 和 profiling 有什么区别？**

   $$
   benchmark=\text{多快}
   $$

   $$
   profile=\text{时间花在哪}
   $$

2. **为什么 GPU timing 必须考虑 CUDA asynchronous execution？**

3. **为什么 naive GeLU 和 fused GeLU 数学完全一样，速度可以明显不同？**

4. **`program_id`、`tl.arange`、mask 分别在干什么？**

5. **为什么 softmax 特别适合一个 block 负责一行？如果行塞不进去怎么办？**

6. **什么是 tiling？为什么 tiled matmul 的 arithmetic intensity 比 naive matmul 高？**

7. **为什么 `ReLU(A @ B)` 最好把 ReLU 直接 fuse 到 matmul kernel，而不是生成 C 后再调用 ReLU？**

8. **为什么 Triton 不等于“CUDA 的 Python 语法糖”？**

   因为真正关键的抽象变化是：

   $$
   \boxed{\text{CUDA 更偏 per-thread，Triton 更偏 per-tile/program}}
   $$

   让你以 tile 和数据流为中心思考 GPU 运算。

---

如果把 Lecture 6 压成一句话，我认为是：

$$
\boxed{
\textbf{一个高性能 kernel 的核心任务，是选择一个好的 tile，
只从 HBM 读必要的数据，在片上把它榨干，
最后尽量只写回一次。}
}
$$

所以从 Lecture 2 到 Lecture 6，其实一直在不断重复同一个主题，只是逐渐下沉：

$$
\boxed{
\text{Lecture 2：算数据移动值不值得}
}
$$

$$
\boxed{
\text{Lecture 5：数据到底在哪里移动}
}
$$

$$
\boxed{
\text{Lecture 6：由你亲自决定它怎么移动}
}
$$

这就是为什么 CS336 的 Systems 部分看起来突然从 Transformer 跳到了 Triton，实际上逻辑一点都没断。
