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
课程表把 Lecture 2 定义为 **“PyTorch (einops), resource accounting (FLOPs, memory, arithmetic intensity)”**，由 Percy Liang 主讲。它真正想教你的不是几个 PyTorch API，而是一种贯穿整个 CS336 的 **Systems 思维：任何模型设计都要先算账**
## 先抓住 Lecture 2 的灵魂

Percy 在开头直接说：

> 给定固定的 compute 和 memory，能训练出的最好模型是什么？

于是问题从“Transformer 数学上怎么写”变成：

$$
\boxed{\text{模型效果最大化}\quad \text{s.t.}\quad \text{显存预算、计算预算有限}}
$$

因此你以后看到任何 LLM，都应该本能地问四件事：

$$
\text{Memory?}\qquad
\text{FLOPs?}\qquad
\text{Bandwidth?}\qquad
\text{Utilization?}
$$

官方甚至明确说，这一讲的 mechanics 很简单，重点是形成 **resource accounting mindset**。
# 一、Tensor：所有资源消耗的载体

PyTorch 里你看到的模型，本质上最终全是 tensor。

参数是 tensor，gradient 是 tensor，activation 是 tensor，optimizer state 是 tensor，输入数据也是 tensor。Lecture 2 就是从这个非常朴素的事实开始的。Transformer 中甚至很常见 rank-4 tensor，比如

$$
X\in\mathbb R^{B\times S\times H\times D}
$$

其中 \(B\) 是 batch size，\(S\) 是 sequence length，\(H\) 是 attention heads，\(D\) 是每个 head 的维度。

这句话看起来没什么，但它意味着：

> **显存问题最终都可以退化成：有多少个数字 × 每个数字多少 byte。**
$$
\boxed{
\text{memory}
=
\text{numel}
\times
\text{bytes per element}
}
$$

例如一个 `float32` tensor：

```python
x = torch.zeros(4, 8)
```

里面有 \(4\times8=32\) 个元素，每个 fp32 是 4 bytes：

$$
32\times4=128\text{ bytes}
$$

官方随后举了 GPT-3 FFN 的一个矩阵：一个 \(12288\times(4\times12288)\) 的 fp32 矩阵单独就约 **2.3 GB**。这就是为什么你不能看到“一个 Linear layer”就觉得它只是几行 Python。

# 二、为什么现在训练模型疯狂折腾 bf16、fp8、fp4？

因为：

$$
\text{显存} \propto \text{每个元素的 bit 数}
$$

最容易理解：

$$
FP32=4B,\qquad FP16=2B,\qquad BF16=2B
$$

于是 70B 参数模型，仅仅存参数：

$$
70\times10^9\times4
=
280GB
$$

如果换 bf16：

$$
70\times10^9\times2
=
140GB
$$

直接砍半。

但这里出现一个非常重要的问题：**精度不是只有“小数点后几位”的问题，还有 dynamic range。**

`torch.tensor([1e-8], dtype=torch.float16)` 会 underflow 成 0，而 bf16 不会。原因是 bf16 保留了和 fp32 类似的 exponent 范围，只牺牲 mantissa precision，所以：

$$
\boxed{\text{bf16：范围大，精度粗}}
$$

而普通 fp16：

$$
\boxed{\text{fp16：精度相对细，但范围小}}
$$

这也是为什么现代 LLM 训练如此偏爱 bf16。

2026 版讲义还特别增加了 FP8 和 NVIDIA NVFP4。Lecture 2 提到 H100 支持两种 FP8 格式 E4M3 / E5M2，也介绍了只有 4 bit/value 的 NVFP4，并用 block-wise scaling 扩展实际可表示范围。

但现在别陷进量化细节。Lecture 2 真正要你记的是：

$$
\boxed{\text{dtype 同时影响显存、数值稳定性、吞吐}}
$$

# 三、Mixed Precision 到底在“混”什么？

一种朴素想法是 bf16 省显存，那所有东西全部 bf16 不就完了？

这当然是不行的。优化器里的 running statistics，例如 Adam 的一阶矩、二阶矩，是 **跨成千上万个 step 累积的状态**。如果精度太低，长期累积误差可能严重。

所以 Lecture 2 给出的典型 mixed precision 思路是：

$$
\begin{aligned}
\text{parameters} &: BF16\\
\text{activations} &: BF16\\
\text{gradients} &: BF16\\
\text{optimizer states} &: FP32
\end{aligned}
$$

PyTorch AMP 则自动判断哪些算子适合低精度，例如 matmul，哪些算子需要更谨慎。

# 四、einops

Transformer 最大的工程 bug 来源之一就是：

> **你不知道自己正在乘哪个维度。**

传统 PyTorch：

```python
z = x @ y.transpose(-2, -1)
```

你看到 `-2, -1`，脑子里必须自己维护 shape。

而 einops：

```python
z = einsum(
    x, y,
    "batch seq1 hidden, batch seq2 hidden -> batch seq1 seq2"
)
```

数学意义直接暴露出来：

$$
z_{b,i,j}
=
\sum_d x_{b,i,d}y_{b,j,d}
$$

其中 `hidden` 没出现在输出中，因此它被 sum 掉。

这就是 attention：

$$
QK^\top
$$

最自然的写法。

你以后看到：

```python
einsum(q, k,
       "batch seq_q head dim, batch seq_k head dim
       -> batch head seq_q seq_k")
```

脑中应该直接翻译成：

$$
A_{b,h,i,j}
=
\sum_d Q_{b,i,h,d}K_{b,j,h,d}
$$

**einops 的意义不是代码短，而是让 tensor shape 变成类型系统一样的东西。**

---

# 五、FLOPs

注意这里有两个极容易搞混的词。

$$
\text{FLOPs}
=
\text{做了多少 floating-point operations}
$$

而：

$$
\text{FLOP/s}
=
\text{每秒能做多少 floating-point operations}
$$

前者是“工作量”，后者是“速度”。Lecture 2 特意强调了这个区别。

例如：

$$
X\in\mathbb R^{B\times D},
\qquad
W\in\mathbb R^{D\times K}
$$

计算：

$$
Y=XW
$$

每个输出：

$$
Y_{ik}=\sum_{j=1}^D X_{ij}W_{jk}
$$

大约需要 \(D\) 次乘法和 \(D\) 次加法，因此：

$$
\boxed{
\text{FLOPs}\approx2BDK
}
$$

官方代码正是：

```python
actual_num_flops = 2 * B * D * K
```

这条公式以后你会看到一万遍：

$$
\boxed{\text{MatMul FLOPs}\approx2MNK}
$$

必须熟到不用想。

---

# 六、为什么训练 Transformer 经常出现那个神秘公式 \(6ND\)？

Lecture 2 从一个普通 Linear layer 推出来。

假设：

$$
H_2=H_1W
$$

forward 需要一次矩阵乘法：

$$
\text{forward}\approx2BD^2
$$

但 backward 要算两个东西：

$$
\frac{\partial L}{\partial H_1}
$$

和：

$$
\frac{\partial L}{\partial W}
$$

这两个又分别是一次矩阵乘法。

所以：

$$
\text{backward}\approx4BD^2
$$

于是：

$$
\text{forward}+\text{backward}
\approx
6BD^2
$$

推广整个网络：

$$
\boxed{
\text{training FLOPs}
\approx
6\times
(\text{data points})
\times
(\text{parameters})
}
$$

Lecture 2 说明，它对 MLP 是直接推出来的，而对于上下文不是特别长的 Transformer，也是一个很好用的近似。([GitHub][2])

换成 LLM 最常见的记号：

$$
\boxed{
C\approx6ND
}
$$

这里：

$$
N=\text{model parameters}
$$

$$
D=\text{training tokens}
$$

这条式子非常重要。以后 Scaling Laws、训练预算估计、Chinchilla、模型训练成本，基本全都会围绕它转。

---

# 七、现在可以回答课堂开头那个 70B 问题了

Lecture 2 一开头问：

> 70B model，训练 15T tokens，用 1024 张 H100，需要多久？

先算总 FLOPs：

$$
C=6ND
$$

因此：

$$
C
=
6
\times70\times10^9
\times15\times10^{12}
$$

得到：

$$
\boxed{6.3\times10^{24}\text{ FLOPs}}
$$

Lecture 2 对 H100 使用约

$$
989.5\text{ TFLOP/s}
$$

的 dense peak，并假设：

$$
MFU=0.5
$$

于是 1024 H100 每天真正贡献大约：

$$
4.38\times10^{22}\text{ FLOPs/day}
$$

最后：

$$
\boxed{\approx144\text{ days}}
$$

这不是为了让你记住 144 天，而是训练你的“餐巾纸估算能力”：老板突然说“我们训练个 70B 吧”，你应该能在几十秒内意识到这是几个月还是几天的工程，而不是先打开 PyTorch。Lecture 2 明确把这种计算称为 back-of-the-envelope / napkin math。([GitHub][2])

---

# 八、但 FLOPs 多，并不意味着 GPU 就一定忙

这就进入整讲最容易卡住、但最有价值的部分：

# Arithmetic Intensity

GPU 做计算时，可以粗略想象成：

$$
\text{HBM}
\rightarrow
\text{GPU compute units}
\rightarrow
\text{HBM}
$$

因此有两个速度限制。

一个是：

$$
\text{compute throughput}
\quad[\text{FLOP/s}]
$$

另一个是：

$$
\text{memory bandwidth}
\quad[\text{byte/s}]
$$

Lecture 2 对 H100 使用约：

$$
989.5\times10^{12}\text{ FLOP/s}
$$

和：

$$
3.35\times10^{12}\text{ byte/s}
$$

所以 GPU 自身的“算力/带宽比”约是：

$$
\frac{989.5}{3.35}
\approx
\boxed{295\text{ FLOP/byte}}
$$

([GitHub][2])

什么意思？

GPU 每从 HBM 搬 1 byte 数据过来，它理论上能趁这个时间干差不多 **295 个 floating-point operations**。

现在定义 workload 的：

$$
\boxed{
AI=
\frac{\text{FLOPs}}{\text{bytes transferred}}
}
$$

这就是 Arithmetic Intensity。

于是有了极其重要的判断：

$$
AI < 295
\Rightarrow
\text{memory-bound}
$$

$$
AI > 295
\Rightarrow
\text{compute-bound}
$$

([GitHub][2])

---

# 九、为什么 ReLU 很“便宜”，却不一定很快？

假设：

```python
y = relu(x)
```

bf16 一个元素 2 bytes。

每个元素：

读取 \(x\)：2 bytes；

写出 \(y\)：2 bytes。

所以约：

$$
4\text{ bytes}
$$

而只做大约 1 次 operation。

因此：

$$
AI_{\text{ReLU}}
\approx
\frac14
=
0.25
$$

而 H100 需要大约：

$$
295
$$

才能把 compute units 喂满。

差了 **三个数量级**。

所以：

$$
\boxed{\text{ReLU strongly memory-bound}}
$$

GPU 根本不是在“算 ReLU”，而是在：

> 等数据从显存搬过来，再把结果搬回去。

Lecture 2 甚至给了一个很反直觉的结论：孤立来看，GELU 虽然比 ReLU 做更多数学运算，但两者依然都可能处于 memory-bound 区域，因此 **ReLU 未必因为 FLOPs 少很多就快很多**。([GitHub][2])

这就是系统优化里一个极其重要的转变：

$$
\boxed{\text{少算 FLOPs}\neq\text{一定更快}}
$$

---

# 十、为什么 Matrix Multiplication 是 GPU 的“甜点”？

先看 dot product：

$$
x^\top w
$$

读取两个长度 \(n\) 的 vector，需要约：

$$
4n\text{ bytes}
$$

做约：

$$
2n\text{ FLOPs}
$$

所以：

$$
AI\approx\frac12
$$

还是 memory-bound。

Matrix-vector：

$$
xW
$$

最大的问题是整个矩阵 \(W\) 搬进来，通常每个 weight 只用一次，所以：

$$
AI\approx1
$$

依然非常低。([GitHub][2])

但是 matrix-matrix：

$$
XW
$$

假设都是：

$$
n\times n
$$

FLOPs：

$$
\approx2n^3
$$

memory：

$$
\approx6n^2\text{ bytes}
$$

所以：

$$
AI
\approx
\frac{2n^3}{6n^2}
=
\boxed{\frac n3}
$$

如果：

$$
n=1024
$$

那么：

$$
AI\approx341
$$

已经超过 H100 这里约 295 FLOP/byte 的临界点：

$$
\boxed{\text{compute-bound}}
$$

Lecture 2 因此总结：**大矩阵乘法可以把 accelerator 吃满，而 elementwise operation 往往 memory-bound。**([GitHub][2])

这就是为什么现代 GPU、Tensor Core、Transformer 如此“天作之合”。

---

# 十一、这也解释了训练和推理为什么差异巨大

这是 Lecture 2 一个特别漂亮的伏笔。

训练时通常是：

$$
[B,S,D]\times[D,K]
$$

其中：

$$
B\times S
$$

往往很大。

于是本质上是：

$$
\text{big matrix}\times\text{big matrix}
$$

同一个 weight 会被大量 token 重复使用。

因此 arithmetic intensity 很高。

但 autoregressive decode，特别是 batch 很小时，每一步只有少数 token：

$$
[1,D]\times[D,K]
$$

就更接近 matrix-vector multiplication。

整个模型几十 GB 的 weights 每生成一个 token 都可能需要大量搬运，但每个 weight 做的运算却不多。

所以 decode 很容易：

$$
\boxed{\text{memory-bandwidth bound}}
$$

Lecture 2 简写成“matrix-vector product is what happens during inference, which is why inference is memory-bound”。更精确地理解应该是：**这是低 batch、逐 token decode 的典型情形；prefill 或 sufficiently large batch 又可能重新变得更加 compute-bound。**([GitHub][2])

这条以后理解 vLLM、continuous batching、KV cache、FlashAttention、speculative decoding，全有用。

---

# 十二、Roofline Model 到底在画什么？

现在我们有：

$$
x=\text{Arithmetic Intensity}
$$

$$
y=\text{achieved FLOP/s}
$$

理论性能上限可以写成：

$$
\boxed{
P
=
\min(
P_{\text{compute}},
AI\times BW
)
}
$$

这就是 Roofline。

左边 AI 小：

$$
P=AI\times BW
$$

所以性能随着 AI 上升，是一条斜线——**memory-bound 区域**。

右边 AI 足够大：

$$
P=P_{\text{compute}}
$$

碰到 GPU 算力天花板，于是变成横线——**compute-bound 区域**。

拐点：

$$
AI^\star
=
\frac{P_{\text{compute}}}{BW}
$$

就是刚才算出的 accelerator intensity。Lecture 2 用 roofline 图把这个关系可视化。([GitHub][2])

如果 Lecture 2 最后你只真正理解了一张图，我希望就是这张。

---

# 十三、MFU 又是什么？

假设 H100 理论能：

$$
1000\text{ TFLOP/s}
$$

你的训练实际只有：

$$
500\text{ TFLOP/s}
$$

那么：

$$
\boxed{
MFU
=
\frac{\text{actual FLOP/s}}
{\text{peak FLOP/s}}
=
50\%
}
$$

Lecture 2 说，在这个简化语境下 **MFU ≥ 0.5 已经相当不错**。([GitHub][2])

所以看到论文写：

> 47% MFU

不要理解为：

> GPU 利用率只有 47%，好垃圾。

而应该理解成：

> 考虑到 memory traffic、kernel overhead、communication、non-matmul operations 等，已经吃到了理论 dense FLOP/s 的很大一部分。

Roofline 进一步给出了一个非常漂亮的简化关系：

$$
MFU
\approx
\min
\left(
1,
\frac{\text{Arithmetic Intensity}}
{\text{Accelerator Intensity}}
\right)
$$

([GitHub][2])

---

# 十四、训练时显存到底被谁吃掉了？

这又是 Lecture 2 的另一个重点。

不要再把：

$$
\text{model size}
$$

等同于：

$$
\text{training VRAM}
$$

训练至少要考虑：

$$
\boxed{
M=
M_{\text{params}}
+
M_{\text{grad}}
+
M_{\text{optimizer}}
+
M_{\text{activations}}
}
$$

Lecture 2 的 mixed-precision 示例里：

$$
\text{parameter}:2\text{ B/param}
$$

$$
\text{gradient}:2\text{ B/param}
$$

而 optimizer state 通常用 fp32。AdaGrad 是：

$$
4\text{ B/param}
$$

Adam 有两个 state：

$$
m,\quad v
$$

因此：

$$
8\text{ B/param}
$$

([GitHub][2])

于是一个很经典的粗算：

$$
\text{Adam training}
\approx
2+2+8
=
\boxed{12\text{ bytes/parameter}}
$$

还没算 activations。

所以 Lecture 2 开头问：

> 8 × 80GB H100 最多训练多少参数？

纯按这 12 bytes/parameter：

$$
\frac{8\times80GB}{12}
\approx
\boxed{53.3B}
$$

但官方立刻提醒：**这是 upper bound，因为还没算 activation。**([GitHub][2])

于是你现在应该明白为什么：

> “80GB H100 能放一个 40B bf16 模型”

和

> “80GB H100 能训练一个 40B 模型”

完全不是一回事。

---

# 十五、Gradient Accumulation 到底解决什么问题？

假设我想要：

$$
B=64
$$

但一次放 64 个样本，activation OOM。

那我拆成：

$$
4\times16
$$

第一次 micro-batch：

```text
forward
backward
```

但**先不 optimizer.step()，也不要清 gradient**。

第二次继续。

第三次继续。

第四次继续。

最后：

```python
optimizer.step()
optimizer.zero_grad()
```

于是数学上大致相当于一个 batch 64 的 gradient。

Lecture 2 把它总结成：

> 用 micro-batch 计算梯度并累积，每达到目标 effective batch size 才更新参数。([GitHub][2])

所以要把两个概念分开：

$$
\boxed{\text{micro batch size}}
$$

决定单次 forward/backward 的 activation memory。

而：

$$
\boxed{\text{effective batch size}}
$$

决定一次 optimizer update 看了多少数据。

Gradient accumulation 的本质就是：

$$
\boxed{\text{用时间换显存}}
$$

---

# 十六、Activation Checkpointing 更狠：连 activation 都不存

为什么 backward 需要大量显存？

因为链式法则需要 forward 时的中间结果。

正常：

$$
x
\rightarrow h_1
\rightarrow h_2
\rightarrow h_3
\rightarrow h_4
$$

forward 时得把很多 \(h_i\) 保存下来，等 backward 使用。

但 checkpointing 说：

> 我不保存，反正 backward 时重新算一遍就是。

于是：

$$
\boxed{\text{memory}\downarrow,\quad \text{compute}\uparrow}
$$

这又是 resource accounting。

Lecture 2 还讲了更一般的 tradeoff。对于 \(L\) 层网络：

全部存：

$$
Memory=O(L)
$$

不重算。

完全不存：

$$
Memory=O(1)
$$

但可能导致：

$$
Compute=O(L^2)
$$

如果每隔：

$$
\sqrt L
$$

层 checkpoint 一次：

$$
Memory=O(\sqrt L)
$$

同时额外 recomputation 仍可保持：

$$
O(L)
$$

([GitHub][2])

PyTorch 对应就是：

```python
torch.utils.checkpoint.checkpoint(layer, x)
```

Lecture 2 也指出它还有几个名字：

$$
\text{activation checkpointing}
=
\text{gradient checkpointing}
=
\text{rematerialization}
$$

([GitHub][2])

---

# 十七、所以整堂 Lecture 2 可以压成这一张“脑图”

只记这一套推理链：

```text
Tensor
   ↓
shape × dtype
   ↓
Memory accounting
   ↓
operation shapes
   ↓
FLOP accounting
   ↓
FLOPs / bytes
   ↓
Arithmetic Intensity
   ↓
compare with hardware FLOPs / bandwidth
   ↓
memory-bound or compute-bound
   ↓
decide optimization
```

如果是 **memory-bound**：

重点不是减少一点数学运算，而是减少 HBM traffic，例如 fusion、FlashAttention、减少 intermediate tensor。

如果是 **compute-bound**：

才更关注 Tensor Core 利用率、矩阵尺寸、低精度 throughput、并行计算效率。

如果是 **OOM**：

再问究竟是 params、optimizer states、gradients 还是 activations，然后决定 gradient accumulation、checkpointing，后续课程还会进入 sharding / distributed parallelism。

这正是 Lecture 2 最后一页总结的几件事：tensor 是一切的载体；用 einops 理清维度；训练约 \(6\times\text{data}\times\text{parameters}\) FLOPs；用 arithmetic intensity / roofline 判断瓶颈；大矩阵乘法倾向 compute-bound，elementwise operation 倾向 memory-bound；gradient accumulation 和 activation checkpointing 用于降低显存压力。([GitHub][2])

---

## 最后，我作为老师会要求你真正会这 6 道题

1. 一个 \(4096\times4096\) bf16 权重矩阵占多少显存？
2. \(X:[B,S,D]\)，\(W:[D,4D]\)，算 `X @ W` 的 FLOPs。
3. 为什么 `ReLU` FLOPs 极少，却可能没有你想象中快？
4. 为什么 LLM training 常近似成 \(6ND\) FLOPs？
5. 为什么 batch=1 的 decode 更容易 memory-bound，而 training 更容易 compute-bound？
6. 为什么 gradient accumulation 和 activation checkpointing 都能救 OOM，但原理完全不同？

如果这六题你能**从头推出来而不是背答案**，Lecture 2 基本就真的学会了。

而且从 CS336 整体结构看，这堂课其实是个枢纽：**A1 让你造 Transformer，Lecture 2 教你给 Transformer 算账；Lecture 5/6 开始讲 GPU 和 kernel；A2 再要求你 profile、benchmark，并自己实现 Triton FlashAttention2。**所以 arithmetic intensity / roofline 绝对不是旁枝，它是在给后面的系统部分埋地基。
