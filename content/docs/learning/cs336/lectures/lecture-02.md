---
title: "L02 · PyTorch / FLOPs"
weight: 2
date: 2026-08-16
updated: 2026-08-16
course: "CS336"
topics: ["CS336", "systems", "resource-accounting"]
aliases:
  - /blog/2026/2026-08-14-cs336-lecture2/
---

Lecture 2 从一个资源问题开始：在 compute 和 memory 都有限时，怎样训练出更好的模型？课程用 PyTorch 和 `einops` 把 tensor 的 shape 说清楚，再用 FLOPs、显存、带宽和 arithmetic intensity 把一次训练或推理的账算出来。 > 给定固定的 compute 和 memory，能训练出的最好模型是什么？ 这堂课的主线可以写成：
$$
\boxed{\text{模型效果最大化}\quad\text{s.t.}\quad\text{显存预算、计算预算有限}}
$$

后面遇到一个模型或一个 kernel，先问四件事：它要读写多少数据、要做多少 FLOPs、硬件的带宽和峰值算力是多少，以及实际利用率离上限有多远。

## Tensor：先把资源单位说清楚

PyTorch 模型里的参数、gradient、activation、optimizer state 和输入，最后都落在 tensor 上。Transformer 中常见的 rank-4 tensor 可以写成：
$$
X\in\mathbb R^{B\times S\times H\times D}
$$

其中 \(B\) 是 batch size，\(S\) 是 sequence length，\(H\) 是 attention heads，\(D\) 是每个 head 的维度。显存的第一层估算很直接：
$$
\boxed{\text{memory}=\text{numel}\times\text{bytes per element}}
$$

例如：

```python
x = torch.zeros(4, 8)
```

这个 tensor 有 (4\times8=32) 个元素；如果每个元素是 fp32，就占 (32\times4=128) bytes。一个 GPT-3 FFN 的 (12288\times(4\times12288)) fp32 矩阵则约占 **2.3 GB**。`Linear` 在代码里只有几行，不代表它的权重很小。

## dtype 不只决定显存

$$
\text{显存}\propto\text{每个元素的 bit 数}
$$

最常用的对比是：
$$
FP32=4B,\qquad FP16=2B,\qquad BF16=2B
$$

70B 参数模型仅存参数时，fp32 需要：
$$
70\times10^9\times4=280\text{ GB}
$$

换成 bf16 后是 140 GB。节省了一半显存，但 dtype 还会改变可表示的数值范围和吞吐。

![bf16 的位布局：8 bit exponent 和 7 bit fraction](/learning/cs336/lectures/bf16.png)

`float16` 的范围比 `bf16` 小。例如 `torch.tensor([1e-8], dtype=torch.float16)` 可能 underflow 成 0，而 bf16 保留了和 fp32 接近的 exponent 范围，只牺牲了 mantissa precision。可以把它记成：bf16 的范围大、精度较粗；fp16 的精度相对细、范围较小。 2026 版讲义还介绍了 H100 上的 FP8（E4M3 / E5M2）和 NVIDIA NVFP4。NVFP4 每个 value 只用 4 bit，并依靠 block-wise scaling 扩展实际可表示范围。这里不需要把格式细节背下来，先记住 dtype 同时影响显存、数值稳定性和吞吐。

## Mixed precision 在混什么

不能把所有状态都改成 bf16。Adam 的一阶矩和二阶矩会跨很多 step 累积，低精度可能放大长期的舍入误差。Lecture 2 给出的典型分工是：
$$
\begin{aligned}
\text{parameters} &: BF16\\
\text{activations} &: BF16\\
\text{gradients} &: BF16\\
\text{optimizer states} &: FP32
\end{aligned}
$$

PyTorch AMP 会根据算子选择合适的精度，例如 matmul 通常适合低精度，而 `exp` 这类操作需要更谨慎。

## `einops`：把 shape 写进表达式

attention 中最容易出错的不是矩阵乘法本身，而是把错误的维度乘在一起。传统写法把这件事藏在 `-2` 和 `-1` 里：

```python
z = x @ y.transpose(-2, -1)
```

`einops` 则直接写出参与求和的维度：

```python
z = einsum(
    x, y,
    "batch seq1 hidden, batch seq2 hidden -> batch seq1 seq2"
)
```

对应的数学式是：
$$
z_{b,i,j}=\sum_d x_{b,i,d}y_{b,j,d}
$$

`hidden` 没有出现在输出中，所以它被求和消掉了。对多头 attention，同样可以写成：

```python
einsum(q, k,
       "batch seq_q head dim, batch seq_k head dim
       -> batch head seq_q seq_k")
```

这让下面的含义一眼可见：
$$
A_{b,h,i,j}=\sum_d Q_{b,i,h,d}K_{b,j,h,d}
$$

## FLOPs：工作量和速度不是一回事

FLOPs 是完成了多少 floating-point operations；FLOP/s 是每秒能完成多少 operations。对：
$$
X\in\mathbb R^{B\times D},\qquad W\in\mathbb R^{D\times K},\qquad Y=XW
$$

每个输出元素包含 (D) 次乘法和 (D) 次加法，因此：
$$
\boxed{\text{FLOPs}\approx2BDK}
$$

课程中的计算就是：

```python
actual_num_flops = 2 * B * D * K
```

矩阵乘法的通用估算可以记成 (2MNK)，但要先确认矩阵 shape。

## 从 Linear 推到训练成本：(6ND)

对一个线性层 (H_2=H_1W)，forward 需要一次矩阵乘法，约为 (2BD^2) FLOPs。backward 需要分别计算：
$$
\frac{\partial L}{\partial H_1},\qquad\frac{\partial L}{\partial W}
$$

这两个梯度各对应一次矩阵乘法，所以：
$$
\text{forward}+\text{backward}\approx2BD^2+4BD^2=6BD^2
$$

推广到整个网络，得到常用的近似：
$$
\boxed{\text{training FLOPs}\approx6\times(\text{data points})\times(\text{parameters})}
$$

LLM 里通常写作：
$$
\boxed{C\approx6ND}
$$

这里 (N) 是模型参数量，(D) 是训练 token 数。这个近似对 MLP 是直接推出来的，对上下文不太长的 Transformer 也常常够用，但它不是所有训练开销的精确清单。

## 70B 模型的粗略训练时间

课程开头的例子是：70B model 训练 15T tokens，使用 1024 张 H100，需要多久？先算总 FLOPs：
$$
C=6\times70\times10^9\times15\times10^{12}=6.3\times10^{24}\text{ FLOPs}
$$

按讲义给出的 H100 dense peak \(989.5\text{ TFLOP/s}\) 和 \(MFU=0.5\) 估算，1024 张卡每天约贡献 \(4.38\times10^{22}\) FLOPs，于是：
$$
\boxed{\approx144\text{ days}}
$$

144 天不是需要背下来的常数。这个例子训练的是 back-of-the-envelope estimation：先判断项目是几天、几个月，还是根本超出当前资源，再做更详细的规划。

## Arithmetic intensity：GPU 到底卡在哪里

FLOPs 多不等于 GPU 一定忙。一次计算同时受 compute throughput 和 memory bandwidth 限制：

![计算单元和显存之间的数据搬运](/learning/cs336/lectures/compute-memory.png)

对 H100，课程示例使用约 \(989.5\times10^{12}\text{ FLOP/s}\) 和 \(3.35\times10^{12}\text{ byte/s}\)，两者相除得到约 295 FLOP/byte：
$$
\frac{989.5}{3.35}\approx\boxed{295\text{ FLOP/byte}}
$$

工作负载的 arithmetic intensity 定义为：
$$
\boxed{AI=\frac{\text{FLOPs}}{\text{bytes transferred}}}
$$

因此，在这个简化模型下：
$$
AI<295\Rightarrow\text{memory-bound},\qquad AI>295\Rightarrow\text{compute-bound}
$$

### ReLU 为什么 FLOPs 少却不一定快

bf16 的 `relu` 每个元素读取 2 bytes、写回 2 bytes，约做 1 次 operation，因此：
$$
AI_{\text{ReLU}}\approx\frac14=0.25
$$

它和 295 FLOP/byte 相差三个数量级，瓶颈在搬数据，而不是算 `max(x, 0)`。GELU 虽然计算更多，也可能落在 memory-bound 区域，所以 ReLU 的 FLOPs 更少，并不推出它一定更快。

### 为什么大矩阵乘法更容易吃满 GPU

dot product 读取两个长度为 (n) 的 vector，约做 (2n) FLOPs、搬运 (4n) bytes，(AI\approx0.5)。matrix-vector product 通常也接近 memory-bound，因为权重矩阵搬进来后，每个 weight 的复用有限。 对两个 (n\times n) 矩阵：
$$
\text{FLOPs}\approx2n^3,\qquad\text{memory}\approx6n^2\text{ bytes}
$$

所以：
$$
AI\approx\frac{2n^3}{6n^2}=\frac n3
$$

当 (n=1024) 时，(AI\approx341)，超过这个 H100 示例的临界点，更接近 compute-bound。优化 kernel 时，要先判断瓶颈属于哪一侧：memory-bound 关注 HBM traffic、fusion 和中间 tensor；compute-bound 才主要看 Tensor Core throughput、矩阵尺寸和并行效率。

## 训练和 decode 的差异

训练通常把很多 token 一起送进矩阵乘法：
$$
[B,S,D]\times[D,K]
$$

(B\times S) 较大，weight 能被很多 token 复用，arithmetic intensity 通常较高。低 batch 的 autoregressive decode 则更接近：
$$
[1,D]\times[D,K]
$$

每生成一个 token 都要访问很大的 weight 集合，但单个 weight 做的计算较少，因此容易 memory-bound。这里的限定很重要：prefill 或足够大的 batch 仍可能重新变成 compute-bound。这个差异是后面理解 KV cache、continuous batching、PagedAttention 和 speculative decoding 的基础。

## 训练显存：参数只是其中一项

训练显存不能只看模型参数：
$$
\boxed{M=M_{\text{params}}+M_{\text{grad}}+M_{\text{optimizer}}+M_{\text{activations}}}
$$

mixed-precision 示例中，parameter 和 gradient 各按 2 B/parameter 估算；Adagrad 的 state 约 4 B/parameter，Adam 有 (m,v) 两个 fp32 state，约 8 B/parameter。因此 Adam training 的粗算是：
$$
2+2+8=\boxed{12\text{ bytes/parameter}}
$$

8 张 80GB H100 按这个上限计算：
$$
\frac{8\times80\text{ GB}}{12}\approx\boxed{53.3\text{B}}
$$

这个 53.3B 没有包含 activation，所以只是 upper bound。

### Gradient accumulation

如果目标 batch size 是 64，但一次放不下，可以拆成 (4\times16) 个 micro-batch。每个 micro-batch 都执行：

```text
y = relu(x)
```

中间不要 `optimizer.step()`，也不要清掉 gradient；累计四次后再执行：

```python
forward
backward
```

micro-batch size 决定一次 forward/backward 的 activation memory；effective batch size 决定一次参数更新看了多少数据。Gradient accumulation 用更多时间换较小的瞬时显存。

### Activation checkpointing

backward 需要 forward 的中间结果。Checkpointing 不保存全部 activation，而是在 backward 时重新计算被省掉的部分：
$$
\boxed{\text{memory}\downarrow,\qquad\text{compute}\uparrow}
$$

对 (L) 层网络，全部保存时 memory 是 (O(L))；完全不保存时可以接近 (O(1))，但朴素重算可能把 compute 推到 (O(L^2))。每隔 (\sqrt L) 层保存一次，可以把 memory 压到 (O(\sqrt L))，同时把额外 recomputation 控制在 (O(L)) 量级。 PyTorch 的调用方式是：

```python
optimizer.step()
optimizer.zero_grad()
```

`activation checkpointing`、`gradient checkpointing` 和 `rematerialization` 在这里指的是同一类 trade-off。

## 复盘检查

不要只背结论，至少要能独立推导下面六题：
1. 一个 (4096\times4096) 的 bf16 权重矩阵占多少显存？

2. (X:[B,S,D])、(W:[D,4D]) 时，`X @ W` 有多少 FLOPs？

3. 为什么 `ReLU` FLOPs 少，却可能没有想象中快？

4. 为什么 LLM training 常近似成 (6ND) FLOPs？

5. 为什么 batch=1 的 decode 更容易 memory-bound，而 training 更容易 compute-bound？

6. Gradient accumulation 和 activation checkpointing 都能缓解 OOM，但它们分别改变了什么？ 这六题覆盖了本讲的完整推理链：

```text
torch.utils.checkpoint.checkpoint(layer, x)
```

Lecture 2 连接了后面的课程：A1 负责实现 Transformer，Lecture 2 负责给它算资源账；Lecture 5/6 进入 GPU 和 kernel；A2 再把 profiling、benchmark 和 Triton FlashAttention2 变成实际作业。理解这条链，比记住某个硬件的单一峰值更能迁移到下一讲。
