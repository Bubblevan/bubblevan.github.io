---
title: "L10 · Inference"
weight: 10
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "inference"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture10/
---
Lecture 10 是前面 Systems 课程真正落到“**大模型上线以后到底怎么跑**”的一讲。

Stanford CS336 Spring 2026 官方课程表里，Lecture 10 是 4 月 29 日 Percy Liang 主讲的 **Inference**；同一天 A2 Systems 截止、A3 Scaling 发布。官方 `lecture_10.py` 的主线非常清楚：

[
\boxed{
\text{理解 inference workload}
\rightarrow
\text{减少 inference cost}
\rightarrow
\text{speculative decoding}
\rightarrow
\text{continuous batching}
\rightarrow
\text{PagedAttention}
}
]

而整堂课最核心的一句话，我会先写在黑板上：

[
\boxed{
\textbf{训练主要在想“怎么把 GPU 算满”；
推理主要在想“怎么少搬模型和 KV cache，并服务大量动态请求”。}
}
]

官方课程把推理特别强调为一种与 training **性质明显不同、通常 memory-bound 且 workload 动态**的计算。([GitHub][1])

---

# 0. 为什么 CS336 要单独花一整讲讲 Inference？

很多初学者会有一个错觉：

> 模型都训练好了，推理不就是 `model.generate()` 吗？

但现实中模型生命周期可能是：

```text
训练一次
   ↓
部署
   ↓
生成 10 亿次
   ↓
生成 1000 亿次
   ↓
甚至更多
```

所以 training 是一次性成本，而 inference 是反复发生的成本。

而且推理不仅用于聊天：

* chatbot；
* code completion；
* agents；
* batch 数据处理；
* benchmark/evaluation；
* RL 时大规模 rollout。

官方 Lecture 10 特别指出 agent workload 更有意思：用户最后只看到少量输出，但 agent 内部可能产生非常长的 reasoning/tool traces，因此 **生成 token 本身就是计算成本**。([GitHub][1])

所以 Lecture 9 讲：

[
\boxed{\text{训练什么模型最划算}}
]

Lecture 10 马上问：

[
\boxed{\text{训出来以后，怎么把它服务得最划算}}
]

这两讲是直接相连的。

---

# 1. 推理首先要区分三个“快”

官方 Lecture 10 一开始就区分三个指标。

### Time To First Token，TTFT

用户发出 prompt 到看到第一个 token：

[
\boxed{\text{TTFT}}
]

例如：

```text
User: 给我解释 Transformer
        ↓
    0.8 秒
        ↓
Assistant: Transformer...
```

这 0.8 秒很影响交互体验。

---

### Latency / inter-token latency

生成开始以后：

```text
Transformer
是
一种
...
```

token 出现得多快。

可以写成：

[
\boxed{\text{seconds/token}}
]

或其倒数 tokens/s。

---

### Throughput

整个服务器所有请求加起来：

[
\boxed{\text{tokens/sec}}
]

这两个目标并不一样。

例如一个 GPU：

```text
一次只处理 1 个用户
```

可能单用户 latency 很漂亮。

但：

```text
同时 batch 128 个用户
```

虽然每个人稍慢，却可能让 GPU 总 throughput 高得多。

所以 Lecture 10 很快就建立：

[
\boxed{
\text{latency}
\leftrightarrow
\text{throughput}
}
]

这个核心 trade-off。([GitHub][2])

---

# 2. 推理为什么和训练这么不一样？

训练 Transformer 时：

[
X:[B,S,D].
]

整段 sequence 已经知道：

```text
token 1
token 2
token 3
...
token S
```

所以可以一次：

[
[B,S,D]\times[D,F].
]

GPU 看到的是：

[
\boxed{\text{大矩阵乘大矩阵}}
]

非常舒服。

---

但是 autoregressive generation：

```text
"The capital of France is"
                ↓
             " Paris"

再有 Paris 后
                ↓
             下一个 token

再有下一个 token
                ↓
             再下一个
```

你无法提前知道：

[
x_{t+1}.
]

所以：

[
\boxed{\text{生成 token 之间存在严格 sequential dependency}}
]

这意味着 sequence dimension 上最漂亮的并行性消失了。

这就是 inference 比 training 更难把 GPU 算力完全吃满的根本原因之一。([GitHub][1])

---

# 3. 推理其实有两个完全不同的阶段

这是 Lecture 10 最重要的概念之一：

[
\boxed{\text{Prefill}}
]

和：

[
\boxed{\text{Decode / Generation}}
]

千万不要把二者混成“推理”。

---

## Prefill

用户给：

```text
"Please explain the difference between
data parallelism and tensor parallelism..."
```

假设有：

[
S=2000
]

个 tokens。

这些 token 已经全部知道，因此模型可以同时处理：

[
[B,S,D].
]

所以 prefill 很像 training forward：

[
\boxed{\text{parallel over sequence}}
]

通常容易成为：

[
\boxed{\text{compute-bound}}
]

---

## Decode

prefill 结束后：

```text
token 2001
 ↓
token 2002
 ↓
token 2003
...
```

每次只有：

[
T=1
]

个新 token。

于是很多 Linear 都变成类似：

[
[1,D][D,F].
]

本质接近 matrix-vector product。

于是：

[
\boxed{\text{Decode 往往 memory-bound}}
]

官方 Lecture 10 的整个 arithmetic-intensity 推导就是在证明这件事。([GitHub][2])

---

# 4. 如果什么都不缓存，autoregressive inference 有多蠢？

假设已经生成：

```text
token 1 ... token t
```

现在生成 token (t+1)。

最 naive 的做法：

> 把前面所有 token 再完整送进 Transformer。

于是第 1 步：

[
O(1^2)
]

第 2 步：

[
O(2^2)
]

……

第 (T) 步：

[
O(T^2).
]

所以总 attention work：

[
\sum_{t=1}^Tt^2
===============

O(T^3).
]

官方 Lecture 10 直接指出 naive inference 生成 (T) tokens 时会因为重复处理 prefix 导致这种 cubic work。([GitHub][2])

但是这里大量计算是重复的。

---

# 5. KV Cache 到底缓存了什么？

Self-attention：

[
Q_t=X_tW_Q
]

[
K_t=X_tW_K
]

[
V_t=X_tW_V.
]

当过去 token：

[
x_1,\ldots,x_{t-1}
]

已经算过：

[
K_1,V_1,\ldots,K_{t-1},V_{t-1}
]

以后，这些东西以后都不会变。

所以直接保存：

[
\boxed{
K_{\le t},V_{\le t}
}
]

下一 token 只重新算：

[
q_{t+1},k_{t+1},v_{t+1}.
]

然后 query：

[
q_{t+1}
]

去和历史 cached keys 做 attention。

这就是：

[
\boxed{\text{KV Cache}}
]

官方 Lecture 10 正是把 KV cache 作为从 naive inference 到实际 inference 的第一项关键优化。([GitHub][2])

---

# 6. KV Cache 到底有多大？这条公式必须会

假设：

* batch/request 数：(B)
* context length：(S)
* Transformer 层数：(L)
* KV heads：(K)
* 每个 head dimension：(H)
* dtype bytes：(b)

那么每个 token、每层要存：

[
K:
K\times H
]

以及：

[
V:
K\times H.
]

所以：

[
\boxed{
M_{\text{KV}}
=============

B
\times S
\times L
\times K
\times H
\times2
\times b
}
]

其中那个：

[
2
]

来自：

[
K+V.
]

官方代码就是：

[
S(KH)L\times2\times2
]

最后的 2 是 bf16 每元素 2 bytes。([GitHub][2])

---

# 7. 一个特别重要的直觉：参数内存和 KV 内存完全不同

模型参数：

[
M_{\text{weights}}
]

基本固定。

你来一个用户还是 100 个用户：

> 同一套 weights。

但 KV cache：

[
\boxed{
M_{\text{KV}}
\propto
B\times S
}
]

用户越多：

[
B\uparrow
]

context 越长：

[
S\uparrow
]

KV cache 都线性增长。

所以 serving system 会出现一个很现实的矛盾：

```text
想 batch 更多请求
↓
throughput ↑

但
↓
KV cache ↑
↓
显存爆
```

这就是为什么 KV cache 会成为整个 Lecture 10 的主角。

---

# 8. Lecture 10 用 Arithmetic Intensity 把这个问题严格算出来

还记得 Lecture 2：

[
AI
==

\frac{\text{FLOPs}}
{\text{bytes transferred}}.
]

Lecture 10 分别算 MLP 和 Attention。

---

# 9. 先看 MLP

SwiGLU MLP roughly：

[
XW_{\rm up},
\quad
XW_{\rm gate},
\quad
HW_{\rm down}.
]

官方计算得到 FLOPs：

[
\boxed{
6BTDF
}
]

而在：

[
BT\ll D,F
]

的典型情形下，memory traffic 主要是读取巨大 weights。

Arithmetic intensity 近似：

[
\boxed{AI_{\rm MLP}\approx BT}
]

([GitHub][2])

---

# 10. 这个式子非常漂亮

## Prefill

[
T=S.
]

所以：

[
AI_{\rm prefill,MLP}
\approx
BS.
]

如果：

[
S=4096,
]

哪怕：

[
B=1,
]

都有：

[
AI\approx4096.
]

非常高。

容易：

[
\boxed{\text{compute-bound}}
]

---

## Decode

[
T=1.
]

所以：

[
\boxed{
AI_{\rm decode,MLP}
\approx B
}
]

如果只有一个用户：

[
B=1.
]

那么：

[
AI\approx1.
]

GPU 每从 HBM 搬一个 weight，基本只用一次。

极其浪费。

---

# 11. 所以为什么 batching 对 decode 的 MLP 特别重要？

假设一个 weight：

[
w.
]

batch=1：

```text
从 HBM 读取 w
↓
给 User A 用一次
```

batch=64：

```text
从 HBM 读取 w
↓
User A
User B
User C
...
User 64
都用
```

于是同一个 weight：

[
\boxed{\text{被复用 }64\text{ 次}}
]

Arithmetic intensity：

[
1\rightarrow64.
]

所以 batch 能让 memory-bound MLP 越来越接近 compute-bound。

这是 serving throughput 的核心来源。

---

# 12. 但 Attention 比 MLP 更麻烦

官方在假设 FlashAttention 风格、无需 materialize 全部 attention matrix 后，得到 attention arithmetic intensity：

[
\boxed{
AI_{\rm attn}
=============

\frac{ST}{S+T}
}
]

([GitHub][2])

---

## Prefill

[
T=S
]

得到：

[
AI
==

# \frac{S^2}{2S}

\boxed{\frac S2}
]

例如：

[
S=4096
]

则：

[
AI=2048.
]

非常不错。

---

## Decode

[
T=1
]

得到：

[
AI
==

\frac S{S+1}
<1.
]

也就是：

[
\boxed{AI_{\rm decode,attn}<1}
]

惨得不能再惨。

官方因此总结：

* Prefill MLP intensity：(BS)
* Prefill attention：(S/2)
* Generation MLP：(B)
* Generation attention：(<1) ([GitHub][2])

---

# 13. 最关键的是：Batching 救不了 decode attention

为什么 MLP：

[
AI\sim B
]

而 attention 不依赖：

[
B?
]

因为 MLP weights 是共享的：

```text
User A ┐
User B ├→ 同一套 W
User C ┘
```

所以 batch 能重复利用 W。

但 KV cache 是每个用户自己的：

```text
User A → KV_A
User B → KV_B
User C → KV_C
```

User A 的 attention：

> 不能拿 User B 的 KV 来复用。

所以：

[
\boxed{
\text{batching amortizes model weights,
but not per-request KV cache}
}
]

官方 Lecture 10 特别点出了这个区别。([GitHub][2])

这句话值得你牢牢记住。

---

# 14. 所以整个 Inference 的系统画像现在已经很清楚了

[
\boxed{
\text{Prefill}
==============

# \text{大矩阵}

\text{compute-heavy}
}
]

而：

[
\boxed{
\text{Decode}
=============

# \text{每次生成 1 token}

# \text{反复读 weights + KV cache}

\text{memory-heavy}
}
]

这就是为什么同一个 Transformer：

> 训练快不快

和：

> serve 快不快

可能完全不是一回事。

---

# 15. TTFT 和 decode latency 现在也终于能区分了

TTFT 主要受：

[
\boxed{\text{prefill}}
]

影响。

prompt：

[
S\uparrow
]

TTFT 通常：

[
\uparrow.
]

而生成后每 token 延迟：

[
\boxed{\text{主要受 decode}}
]

影响。

所以一个 system 可以：

```text
TTFT 很差
但生成以后很丝滑
```

或者：

```text
TTFT 很快
但每个 token 慢吞吞
```

完全可能。

官方 Lecture 10 也直接说 TTFT essentially 是 prefill time 的函数。([GitHub][2])

---

# 16. Batch size 为什么造成 latency / throughput trade-off？

假设：

[
B=1.
]

每一个用户的 KV cache 小。

所以一次 decode：

[
\text{memory traffic}
]

比较小。

Latency 好。

但是：

> 每次辛辛苦苦把模型 weights 从 HBM 读进来，只服务一个 token。

throughput 很差。

---

把：

[
B\rightarrow64.
]

好处：

[
\boxed{\text{weights 被 64 个请求共享}}
]

所以 throughput 上升。

但：

[
M_{\rm KV}\propto B.
]

意味着：

[
\boxed{\text{要读写更多 KV}}
]

所以单 request latency 可能恶化。

官方用 Llama 2 13B + H100 做的理论例子直接展示：

[
B=1\rightarrow64\rightarrow256
]

时 throughput 上升、latency 变差，而且 batch 太大最终 KV cache 连显存都放不下。([GitHub][2])

所以：

[
\boxed{
\text{small batch}
\Rightarrow
\text{low latency / poor throughput}
}
]

[
\boxed{
\text{large batch}
\Rightarrow
\text{high throughput / worse latency}
}
]

---

# 17. 一个很有意思的 serving 策略：Prefill 和 Decode 用不同 batch

官方甚至直接建议：

Prefill 想降低：

[
\boxed{\text{TTFT}}
]

可以使用相对小 batch。

而 decode 为了提高：

[
\boxed{\text{throughput}}
]

可以使用更大的 batch。([GitHub][2])

这已经隐约导向现代 serving 系统中的：

[
\boxed{\text{prefill/decode disaggregation}}
]

虽然 Lecture 10 没把这一点作为核心展开。

---

# 18. 既然 memory 是瓶颈，第一个方向自然是：缩小 KV Cache

这就是 Lecture 10 第二大部分：

[
\boxed{\text{Taking shortcuts — lossy}}
]

“Lossy”的意思：

> 我改变模型/表示，让 inference 更便宜，但可能损失一点 accuracy。

第一类就是：

[
\boxed{\text{attention architecture}}
]

---

# 19. MHA → GQA → MQA，现在你终于知道为什么了

普通 MHA：

[
N
]

个 query heads，同时有：

[
N
]

个 K/V heads。

所以：

[
K=N.
]

---

MQA：

[
K=1.
]

所有 query heads 共用同一组 K/V。

---

GQA：

[
1<K<N.
]

例如：

[
N=40
]

query heads，

但：

[
K=8
]

KV heads。

每 5 个 Q heads 共用一个 KV head。

官方 Lecture 10 给出的核心收益：

[
\boxed{\text{KV cache 缩小 }N/K\text{ 倍}}
]

因为 inference memory-bound，所以减少 cache 就直接改善 throughput/latency，并允许更大的 batch。([GitHub][2])

---

# 20. 注意 GQA 的真正价值不是“少参数”

很多人会说：

> GQA 是参数优化。

这不是 inference 视角最重要的东西。

关键是：

[
\boxed{
M_{\rm KV}
\propto K
}
]

从：

[
K=40
]

降到：

[
K=8
]

KV cache：

[
\boxed{5\times smaller}
]

这可能让你：

```text
原来 batch 64
↓
现在 batch 256
```

直接改变 serving economics。

这就是 Architecture 和 Systems co-design。

---

# 21. MLA 更激进：K/V 根本不要直接存

普通 attention：

[
h
\rightarrow
K=W_Kh
]

[
h
\rightarrow
V=W_Vh.
]

然后 cache：

[
K,V.
]

MLA：

先：

[
\boxed{
c=W_ch
}
]

其中：

[
c
]

是低维 latent。

cache：

[
\boxed c
]

需要 K/V 时再：

[
c\rightarrow K,V.
]

Lecture 10 用 DeepSeek-V2 的例子：正常 KV representation 的维度对应 (N H=16384)，MLA 压成约 512 latent dimensions；再额外处理与 RoPE 相关的一小部分。([GitHub][2])

所以：

[
\boxed{\text{用额外计算换 KV memory}}
]

你有没有发现又是熟悉的 trade-off？

[
\boxed{
\text{compute}\uparrow
\quad
\text{memory}\downarrow
}
]

而 decode 本来就 memory-bound。

所以这是非常划算的方向。

---

# 22. CLA：不同层之间连 KV 都共享

GQA：

[
\boxed{\text{across heads sharing}}
]

Cross-Layer Attention：

[
\boxed{\text{across layers sharing}}
]

例如原来：

```text
Layer 1 → K1,V1
Layer 2 → K2,V2
Layer 3 → K3,V3
...
```

现在某些 layers：

```text
Layer 1 ┐
Layer 2 ├→ shared KV
Layer 3 ┘
```

因此：

[
M_{\rm KV}
]

又下降。

Lecture 10 把 CLA 看作另一个改善 accuracy–KV-cache Pareto frontier 的方向。([GitHub][2])

---

# 23. Sliding-Window Attention：最暴力的办法就是“别缓存那么远”

如果窗口：

[
W=4096.
]

无论 context：

[
S=100K
]

还是：

[
1M,
]

每层只保留最近：

[
4096
]

tokens。

所以：

[
M_{\rm KV}
\propto W
]

而不再直接随着总 sequence：

[
S
]

无限增长。

官方 Lecture 10 直接强调：

[
\boxed{\text{KV cache becomes independent of total sequence length}}
]

对于纯 local attention。([GitHub][2])

---

# 24. 但为什么 local attention 仍然可能拥有很大有效感受野？

假设每层窗口：

[
W.
]

Layer 1：

token (t) 看：

[
t-W\ldots t.
]

Layer 2 又能通过 Layer 1 的 representation 间接看到更前面的东西。

粗略：

[
\boxed{\text{effective receptive field}\sim L W}
]

所以随着层数增加，可间接传播很远。

但当然：

> 间接传播不等于 full attention 随时精确跳回一个百万 token 前的位置。

所以现代模型往往采用：

[
\boxed{\text{local + occasional global attention}}
]

hybrid。

Lecture 10 正是这样总结 sliding-window attention 的 trade-off。([GitHub][2])

---

# 25. 所以关于 KV Cache，整堂课给出了三类方法

可以整理成：

### 减少 head 维度

[
\boxed{\text{GQA / MQA}}
]

---

### 压缩 representation

[
\boxed{\text{MLA}}
]

---

### 跨层共享

[
\boxed{\text{CLA}}
]

---

### 少保存 token

[
\boxed{\text{Local/Sparse Attention}}
]

再极端一点：

[
\boxed{\text{Linear Attention / SSM}}
]

甚至不保存线性增长的历史 KV。

官方 Lecture 10 的总结就是：既然 inference memory-bound，就围绕降低 KV-cache dimension 或截断/稀疏化上下文来设计 architecture。([GitHub][2])

---

# 26. 第二个大招：Quantization

这次 quantization 的动机应该比 Lecture 2 更直观。

如果：

[
13B
]

模型 bf16：

[
13B\times2B
\approx26GB.
]

如果 INT8：

[
13GB.
]

INT4：

[
6.5GB.
]

不仅：

[
\boxed{\text{显存下降}}
]

更重要：

每个 decode token 要从 HBM 读 model weights。

所以 memory traffic：

[
\boxed{\text{直接按 dtype size 下降}}
]

而 decode 又 memory-bound。

因此量化可能直接加速。官方 Lecture 10 正是从“less memory → better latency/throughput”这个 inference 角度切入量化。([GitHub][2])

---

# 27. 最基本的 affine quantization 是什么？

例如：

[
x=5.2342.
]

选择：

[
scale=0.1
]

以及：

[
zero_point=4.
]

Quantize：

[
\boxed{
q=
\operatorname{round}
\left(
\frac{x}{scale}
\right)
+zero
}
]

Dequantize：

[
\boxed{
\hat x
======

(q-zero)\times scale
}
]

当然：

[
\hat x\neq x.
]

因此：

[
\boxed{\text{quantization error}}
]

不可避免。

Lecture 10 直接用这个简单例子解释 quantize/dequantize mechanics。([GitHub][2])

---

# 28. PTQ 和 QAT 的区别

### QAT：Quantization-Aware Training

训练的时候就模拟量化误差：

```text
weights
↓
quantize/dequantize
↓
forward
```

于是模型自己学会：

> 在这种精度限制下工作。

优点：

[
\boxed{\text{通常效果更好}}
]

缺点：

[
\boxed{\text{需要重新/额外训练}}
]

---

### PTQ：Post-Training Quantization

模型训完以后才量化。

先拿 calibration data：

```text
跑一些样本
↓
找每层 scale / range
↓
量化
```

优点：

[
\boxed{\text{便宜}}
]

缺点：

> 极低精度时更难保 accuracy。

Lecture 10 也提到 GPTQ、AWQ 等代表方法。([GitHub][2])

---

# 29. AWQ 的直觉特别值得记

AWQ 的观察：

> 并不是所有 weight 同样重要。

某些 activation channels 特别大。

与这些 activation 相乘的 weights：

[
\boxed{\text{量化误差影响更大}}
]

所以不要平均地给所有 weights 一样 precision。

而是：

> 少数重要权重保护得更好。

Lecture 10 给出的概念就是从 activation 判断重要 weights，让少量 weight 获得更好的量化保护。([GitHub][2])

这背后是一个更普适的原则：

[
\boxed{
\text{有限 bit budget 应该花在最敏感的地方}
}
]

---

# 30. 第三个 lossy shortcut：Pruning + Distillation

量化是：

> 参数还在，只是精度低。

Pruning：

> 我干脆把东西删掉。

可以删：

```text
layer
attention head
hidden dimension
...
```

于是：

[
\boxed{\text{模型真的变小}}
]

但直接删通常会掉能力。

所以：

```text
大模型
 ↓
identify unimportant components
 ↓
prune
 ↓
小模型变差
 ↓
用原模型蒸馏/repair
```

Lecture 10 引用的 pruning recipe 就是先通过 calibration data 判断重要 layer/head/hidden dimensions，然后删除，再使用 teacher model distill 修复。([GitHub][2])

---

# 31. 这里出现一个特别重要的分类：From Scratch vs Distillation

如果你想得到一个更快架构：

## From scratch

```text
设计更快 architecture
↓
从头训练
```

---

## Distillation

```text
设计更快 architecture
↓
利用大模型初始化/指导
↓
repair / distill
```

所以 GQA、pruning、special student architecture 等都可以从：

[
\boxed{\text{teacher → cheaper student}}
]

这个统一视角理解。

---

# 32. 接下来进入 Lecture 10 我认为最漂亮的一部分：Speculative Decoding

刚才所有方法：

```text
GQA
quantization
pruning
```

都会改变模型内部。

可能损失 accuracy。

那有没有：

[
\boxed{\text{完全保持 target model distribution}}
]

却加速 generation 的方法？

有。

[
\boxed{\text{Speculative Sampling / Decoding}}
]

---

# 33. 它利用的关键不对称是什么？

我们已经知道：

### Generation 一个 token

target model：

[
T=1
]

memory-bound。

慢。

### 检查一串已知 token

例如：

[
T=4
]

这些 token 已经给你了。

可以 parallel prefill-style 处理。

Arithmetic intensity 更高。

所以：

[
\boxed{\text{checking several tokens can be cheaper than generating them one-by-one}}
]

官方 Lecture 10 直接总结成：

> checking is faster than generation. ([GitHub][2])

这就是 speculative decoding 的整个物理基础。

---

# 34. Speculative Decoding 的基本流程

有一个小 draft model：

[
p
]

和大 target model：

[
q.
]

Draft 先便宜地产生：

```text
t1 t2 t3 t4
```

然后一次把：

[
[t_1,t_2,t_3,t_4]
]

送给 target。

Target 可以并行得到这些位置对应概率：

[
q(t_1),q(t_2),q(t_3),q(t_4).
]

如果 draft 猜得好：

> 一次 target forward 就接受多个 token。

原来：

```text
target
token1

target
token2

target
token3

target
token4
```

现在：

```text
small draft → 4 guesses
        ↓
large target → check 4 at once
```

所以 target 的昂贵 sequential decode steps 减少。

([GitHub][2])

---

# 35. 最大的惊喜：Speculative Sampling 可以是 Lossless 的

不是：

> draft 猜错一点，所以最终 distribution 近似 target。

而是经过 modified rejection sampling，可以保证：

[
\boxed{\text{最终 token 严格服从 target distribution }q}
]

官方 Lecture 10 甚至用二元 vocabulary ({A,B}) 手推了一次证明。([GitHub][2])

---

# 36. 接受概率大概是什么直觉？

draft 给候选 token (x)。

如果：

[
p(x)\le q(x)
]

说明 draft 没有“过度偏爱”它，直接接受。

如果：

[
p(x)>q(x)
]

则以类似：

[
\boxed{
\frac{q(x)}{p(x)}
}
]

的概率接受。

拒绝时，再从 correction/residual distribution 中抽 token。

这样最终恰好恢复：

[
q.
]

所以 draft 只负责：

> **建议 candidate。**

target 仍然掌握最终 statistical correctness。

---

# 37. 那什么样的 draft model 最好？

存在两个目标：

### 越小越好

因为 draft 必须：

[
\boxed{\text{便宜}}
]

否则它自己就把收益吃掉。

---

### 越接近 target 越好

因为：

[
p\approx q
]

意味着 acceptance rate 高。

所以 draft 设计本身又是一个 optimisation problem：

[
\boxed{
\text{draft cost}
\leftrightarrow
\text{acceptance rate}
}
]

Lecture 10 举出典型的大/小模型组合，也提到 Medusa、EAGLE 等进一步改进 draft 的路线。([GitHub][2])

---

# 38. Medusa / EAGLE 为什么属于同一个家族？

普通 speculative：

```text
另一个小 LM
↓
预测未来 tokens
```

Medusa：

> 在 target model 上增加多个预测 heads，一次猜未来多个 token。

EAGLE：

> draft 不只看 token，还利用 target 高层 feature。

它们共同在优化：

[
\boxed{\text{proposal quality / proposal efficiency}}
]

最终还是利用：

[
\boxed{\text{generate expensive, verify cheap}}
]

这个不对称。([GitHub][2])

---

# 39. 到这里，前半堂课优化的还是“一个请求”

但现实 serving 更麻烦：

```text
12:00:00 用户 A 来了
12:00:01 用户 B 来了
12:00:01 用户 C 来了

A 要生成 20 tokens
B 要生成 2000 tokens
C 要生成 150 tokens
```

这已经不是规则的：

[
[B,S,D]
]

tensor 了。

而是：

[
\boxed{\text{dynamic ragged workload}}
]

这就是 Lecture 10 后半突然转向 **serving systems** 的原因。([GitHub][2])

---

# 40. Static Batching 为什么很糟？

假设 batch：

```text
Request A: 10 tokens
Request B: 200 tokens
Request C: 500 tokens
```

如果静态 batch：

> 三个请求一起开始，一起结束。

那么 A：

```text
10 tokens 后其实已经完成
↓
但 slot 一直被占到 Request C 完成
```

大量 GPU capacity 被浪费。

而且新请求：

> 只能等整个 batch 完成后才能加入。

Interactive latency 会非常糟。

---

# 41. Continuous Batching 的核心只有一句话

[
\boxed{\text{每一个 decode iteration 都重新调度 batch}}
]

也叫 iteration-level scheduling。

例如：

```text
Step 1:
A B C

Step 2:
A B C

A finished

Step 3:
D B C

Step 4:
D B C

B finished

Step 5:
D E C
```

一旦请求结束：

> 立刻把新的 request 塞进来。

不需要等待整个 batch 完成。

官方 Lecture 10 正是引用 Orca 来介绍 continuous batching：逐 decode step 调度，新请求到来即可加入。([GitHub][2])

这已经是今天主流 LLM serving engine 的基本思想。

---

# 42. 不同 sequence length 怎么 batch？

又一个问题：

```text
Sequence A: [3,H]
Sequence B: [9,H]
Sequence C: [5,H]
```

传统 batch 需要：

[
[B,S,H]
]

相同 (S)。

是不是必须 padding 到 9？

```text
A: 3 real + 6 padding
B: 9 real
C: 5 real + 4 padding
```

太浪费。

Lecture 10 给出的 selective batching 思想：

### Attention

不同 sequence 的 history 不同，因此分别处理。

### 非 attention operation

例如：

```text
MLP
Norm
```

把所有 active tokens 拼：

[
[3+9+5,H]
]

一起做。

所以：

[
\boxed{\text{不同算子可以采用不同 batching strategy}}
]

这已经是一个非常 systems 的思考方式。([GitHub][2])

---

# 43. 然后出现 vLLM 最著名的 PagedAttention

现在问题变成：

> 每个 request 的 KV cache 到底怎么分配显存？

传统做法：

Request 来时：

```text
“最大可能生成 4096 tokens”
↓
提前申请一大片连续 KV memory
```

但最后可能只生成：

[
137
]

tokens。

那么剩下：

[
3959
]

token slots 全浪费。

这叫：

[
\boxed{\text{internal fragmentation}}
]

而连续块之间又可能留下各种小洞：

[
\boxed{\text{external fragmentation}}
]

官方 Lecture 10 明确用操作系统磁盘/内存 fragmentation 类比。([GitHub][2])

---

# 44. PagedAttention 的灵感真的是操作系统

操作系统早就解决过：

> 一个 process 的 virtual memory 不需要物理上连续。

可以：

```text
logical pages
↓
page table
↓
scattered physical frames
```

vLLM 直接套用：

```text
Sequence KV cache
↓
切成固定大小 blocks
↓
这些 blocks 可以散落在 GPU memory
```

所以逻辑上：

```text
KV block 0
KV block 1
KV block 2
```

物理上可能：

```text
address 500
address 90
address 1200
```

无所谓。

只要 block table 知道映射。

这就是：

[
\boxed{\text{PagedAttention}}
]

官方 Lecture 10 正是如此介绍 vLLM 的核心思想。([GitHub][2])

---

# 45. Paging 到底带来什么好处？

第一：

[
\boxed{\text{按需分配}}
]

生成多少 token，就逐步申请多少 blocks。

不用提前按最大长度 reserve。

---

第二：

[
\boxed{\text{减少 fragmentation}}
]

不用要求每条 sequence 拿一个巨大连续区间。

---

第三：

[
\boxed{\text{KV sharing}}
]

这点特别重要。

---

# 46. 为什么多个请求可以共享 KV Cache？

例如所有 ChatGPT-like 请求都有：

```text
<system>
You are a helpful assistant...
...
</system>
```

system prompt 完全一样。

为什么每个用户都重新存一份？

可以：

```text
Request A ┐
Request B ├→ same physical KV blocks
Request C ┘
```

然后各自用户 prompt 开始以后再分叉。

---

另一个典型场景：

同一个 prompt：

```text
写一道代码题的 32 个候选答案
```

前面的 prompt KV：

[
\boxed{\text{完全相同}}
]

只有生成开始以后才分叉。

所以可以使用：

[
\boxed{\text{Copy-On-Write}}
]

共享 prefix block，直到需要修改/扩展时再单独分配。

Lecture 10 明确把 system-prompt sharing 和 multiple samples per prompt 列为 PagedAttention 的重要场景。([GitHub][2])

---

# 47. 这对 Agent / RL 场景尤其重要

比如一个 agent evaluation：

```text
same system prompt
same tools definition
same task context
↓
sample 64 trajectories
```

如果全部重复计算/保存 prefix：

[
\boxed{\text{巨大浪费}}
]

所以现代 serving systems 进一步发展出了：

[
\boxed{\text{prefix caching}}
]

以及 SGLang 的 RadixAttention 等机制。

Lecture 10 开头也把 SGLang 特别列为适合 agentic workloads 的 serving system。([GitHub][1])

---

# 48. PagedAttention 并不是“Attention 数学的新算法”

这一点和 FlashAttention 类似，千万不要混。

### FlashAttention

优化：

[
\boxed{\text{一个 attention kernel 内部 IO}}
]

HBM ↔ SRAM。

---

### PagedAttention

优化：

[
\boxed{\text{不同 requests 的 KV cache memory management}}
]

类似 virtual memory paging。

---

### GQA / MLA

直接改变：

[
\boxed{\text{KV representation / architecture}}
]

所以：

```text
GQA/MLA
→ model architecture

FlashAttention
→ kernel algorithm

PagedAttention
→ serving memory manager
```

这三层完全不同。

这是 Lecture 10 非常值得你建立的分层意识。

---

# 49. Lecture 10 实际上讲了三类完全不同的优化

我建议直接这样记。

## 第一类：改变模型，允许一点质量 trade-off

[
\boxed{\text{Lossy shortcuts}}
]

例如：

```text
GQA
MLA
CLA
local/sparse attention
quantization
pruning/distillation
```

核心：

[
\boxed{\text{让模型本身更便宜}}
]

---

## 第二类：数学上仍得到 target distribution

[
\boxed{\text{Lossless shortcut}}
]

代表：

[
\boxed{\text{Speculative Sampling}}
]

核心：

> 用便宜 proposal，把多个 expensive sequential steps 合并成一次 verification。

---

## 第三类：模型不变，只把服务器组织得更聪明

[
\boxed{\text{Serving systems}}
]

例如：

```text
continuous batching
selective batching
PagedAttention
prefix sharing
CUDA graphs
better kernels
```

核心：

[
\boxed{\text{提高 hardware utilization}}
]

这正是官方 Lecture 10 的章节组织。([GitHub][1])

---

# 50. 所以 vLLM 为什么是一个如此经典的系统？

因为它没有发明新的 Transformer。

模型还是：

[
\operatorname{softmax}(QK^\top)V.
]

它解决的是：

> **真实线上流量根本不像训练 tensor 那么整齐。**

于是做：

```text
continuous batching
+
PagedAttention
+
KV block sharing
+
optimized attention kernels
+
CUDA graphs
```

Lecture 10 最后的 PagedAttention 部分还特别提到 vLLM 会融合 block read 与 attention、使用 FlashAttention/FlashDecoding 类 kernels，并借助 CUDA Graphs 降低 launch overhead。([GitHub][2])

所以 vLLM 的本质不是：

> “一个更快的 `generate()`。”

而是：

[
\boxed{\text{一个 LLM-specific operating system / scheduler}}
]

这个 mental model 非常好用。

---

# 51. 为什么 CUDA Graphs 对 inference 有用？

Decode 每一步可能：

```text
launch RMSNorm
launch matmul
launch attention
launch MLP
...
```

每个 kernel 本身越来越小。

于是 CPU：

```text
launch
launch
launch
```

的 overhead 开始不可忽略。

CUDA Graph：

> 把一串固定 GPU operations 预先记录，然后整体 replay。

因此：

[
\boxed{\text{减少 CPU/kernel-launch overhead}}
]

尤其对 decode 这种：

[
\boxed{\text{大量重复的小 step}}
]

特别有价值。

Lecture 10 最后也把它列为 vLLM 的重要工程优化之一。([GitHub][2])

---

# 52. Lecture 10 和 Lecture 5 的关系特别漂亮

Lecture 5：

[
\boxed{\text{为什么 inference memory-bound？}}
]

你学：

```text
HBM
Arithmetic Intensity
Roofline
```

Lecture 10：

> 好，那既然 memory-bound，我们应该怎样设计整个 LLM？

于是：

```text
GQA
→ 少 KV

MLA
→ 压 KV

Quantization
→ 少 bytes

PagedAttention
→ 少浪费 KV

Batching
→ weight reuse

Speculative
→ 少 target decode steps
```

Lecture 10 几乎可以说就是：

[
\boxed{\text{“memory-bound”四个字的全部工程后果}}
]

---

# 53. Lecture 4 和 Lecture 10 也形成了有趣的镜像

Lecture 4 讲 Architecture：

```text
GQA
MLA
Sparse Attention
linear attention
MoE
```

当时你会问：

> 模型质量怎么样？

Lecture 10 重新看同样一些 architecture：

> **它们到底能省多少 inference memory / bandwidth？**

例如 GQA：

Lecture 4：

[
\text{Attention architecture variant}
]

Lecture 10：

[
\boxed{\text{KV cache compression mechanism}}
]

这就是为什么真正的 LLM architecture 研究和 serving system 根本分不开。

---

# 54. Lecture 9 和 Lecture 10 连接起来，会得到一个非常现实的新优化目标

Lecture 9 的 Chinchilla 问：

[
\min L
\quad
\text{s.t. training compute fixed}.
]

Lecture 10 告诉你：

> 但部署以后模型可能被调用一亿亿次。

于是生命周期成本：

[
\boxed{
C_{\rm total}
=============

C_{\rm train}
+
C_{\rm inference}
}
]

这解释了为什么现实模型可能故意：

[
\boxed{\text{参数少一点，训练 tokens 多很多}}
]

因为：

[
\text{training}
]

只一次。

但每生成一个 token，decode 几乎都要读取整个模型参数。

所以参数数量直接决定 serving cost。

---

# 55. 为什么 “active parameters” 对 MoE 推理特别重要？

Dense 70B：

每 token：

[
\sim70B
]

参数参与。

MoE 600B total：

可能只有：

[
30B
]

active/token。

所以 compute per token 更接近：

[
30B
]

而不是：

[
600B.
]

但是：

> 那 600B total parameters 仍然必须分布在服务器的 memory 中。

所以 MoE inference 又出现：

[
\boxed{
\text{active compute}
\neq
\text{storage footprint}
}
]

并伴随 expert routing communication。

Lecture 10 没大篇幅展开 MoE serving，但你现在应该能把 Lecture 4、7、8 自己接起来了。

---

# 56. 我建议你把推理系统看成四层

这是学完 Lecture 10 后非常有用的框架。

### Layer 1：Model Architecture

```text
MHA / GQA / MLA
dense / MoE
full / sliding / sparse attention
```

决定：

[
\boxed{\text{理论 inference workload}}
]

---

### Layer 2：Numerical Representation

```text
BF16
FP8
INT8
INT4
```

决定：

[
\boxed{\text{每个 parameter/cache element 几 bytes}}
]

---

### Layer 3：Kernel

```text
FlashAttention
FlashDecoding
fused kernels
CUDA graphs
```

决定：

[
\boxed{\text{一次算子怎样高效落到 GPU}}
]

---

### Layer 4：Serving Runtime

```text
continuous batching
PagedAttention
prefix caching
scheduling
```

决定：

[
\boxed{\text{大量真实 requests 怎样共享 GPU}}
]

很多讨论 LLM inference 时会把这四层搅成一团。

Lecture 10 最有价值的地方之一，就是让它们逐渐分开。

---

# 57. 给你一个实际例子：为什么“模型 tokens/s”是个很危险的数字？

有人说：

> 我的模型能跑 500 tokens/s。

你应该立刻问：

**Batch size？**

[
B=1?
\quad
B=128?
]

**Prompt length？**

[
128?
\quad
32K?
]

**TTFT？**

**Prefill throughput 还是 decode throughput？**

**单用户 tok/s 还是 aggregate tok/s？**

**什么 GPU？**

**什么 quantization？**

**什么 KV-cache dtype？**

**是否 continuous batching？**

否则：

[
\boxed{500\text{ tok/s}}
]

几乎没有意义。

这就是 Lecture 10 建立 latency/throughput/TTFT 区分的真正价值。

---

# 58. 我最希望你真正会算的五条公式

### ① KV cache

[
\boxed{
M_{\rm KV}
==========

B S L K H
\times2
\times b
}
]

---

### ② Decode MLP intensity

[
\boxed{
AI_{\rm MLP}\approx B
}
]

说明 batching 能复用 weights。

---

### ③ Attention intensity

[
\boxed{
AI_{\rm attn}
=============

\frac{ST}{S+T}
}
]

---

### ④ Prefill attention

[
T=S
\Rightarrow
AI=\frac S2.
]

---

### ⑤ Decode attention

[
T=1
\Rightarrow
AI=\frac S{S+1}<1.
]

说明：

[
\boxed{\text{attention decode 天生 memory-bound}}
]

而且增加 request batch 并不能像 MLP 一样复用用户独有的 KV cache。([GitHub][2])

这五条式子基本就是整讲理论地基。

---

# 59. Lecture 10 的八道自测题

如果这些能自己推出来，就算真的学懂。

### 1. 为什么 inference 要分 Prefill 和 Decode？

一定要回答：

[
\boxed{\text{一个 sequence-parallel，一个 token-sequential}}
]

而不仅是“两个阶段”。

---

### 2. 为什么 KV cache 可以把 naive autoregressive computation 大幅降下来？

因为过去 tokens 的：

[
K,V
]

不会改变，不需要重新投影。

---

### 3. 为什么 decode MLP 可以靠 batching 提高 arithmetic intensity，而 decode attention 不行？

因为：

[
\boxed{\text{weights across requests shared}}
]

但：

[
\boxed{\text{KV cache per request unique}}
]

---

### 4. 为什么 GQA 同时能提升 throughput 和支持更大 batch？

因为：

[
M_{\rm KV}\propto K
]

减少 KV heads：

[
\boxed{\text{cache memory/bandwidth ↓}}
]

---

### 5. GQA、MLA、PagedAttention 三者到底分别改变什么？

GQA：

[
\boxed{\text{architecture / KV heads}}
]

MLA：

[
\boxed{\text{KV representation}}
]

PagedAttention：

[
\boxed{\text{KV memory allocation}}
]

---

### 6. 为什么 speculative decoding 可以“更快但 distribution 不变”？

因为 draft 只是 proposal，modified rejection sampling/correction 保证最终仍从 target (q) 精确采样。([GitHub][2])

---

### 7. Continuous batching 解决什么？

不是 KV cache 大小。

而是：

[
\boxed{\text{动态 request arrivals / varying completion times}}
]

造成 GPU slots 浪费。

---

### 8. PagedAttention 为什么来自 OS，而不是新的 attention 数学？

因为它解决的是：

[
\boxed{\text{physical KV memory allocation / fragmentation / sharing}}
]

不是：

[
QK^\top
]

怎么计算。

---

# 60. 最后，把 Lecture 10 压缩成一块黑板

我会先写：

[
\boxed{
\text{Prefill}
==============

\text{compute-bound}
}
]

[
\boxed{
\text{Decode}
=============

\text{memory-bound}
}
]

然后画：

```text
Inference optimization

              Memory
                │
      ┌─────────┼─────────┐
      │         │         │
   Weights     KV       Scheduling
      │         │         │
 Quantize     GQA      Continuous
 Prune        MLA       Batching
 Distill      CLA          │
              Local    PagedAttention
```

旁边再单独写：

[
\boxed{\text{Speculative Decoding}}
]

利用：

[
\boxed{\text{verification parallel，generation sequential}}
]

减少昂贵 target-model decode steps。

而这整堂 Lecture 10 最深的一句话，我认为是：

[
\boxed{
\textbf{推理性能的核心，不是“这个模型有多少 FLOPs”，
而是每生成一个 token 时，到底必须从 memory 搬多少东西，
以及这些成本能被多少请求共同摊掉。}
}
]

这也解释了为什么现代模型会如此执着于 **GQA、MLA、quantization、KV compression**，而现代 serving system 会如此执着于 **continuous batching、prefix caching、PagedAttention、speculative decoding**：它们表面上来自不同论文，实际上几乎全部是在攻击同一个瓶颈——

[
\boxed{\text{autoregressive decoding 的低 arithmetic intensity}}
]

所以从课程结构上看也非常漂亮：Lecture 2 给你 Arithmetic Intensity，Lecture 5 让你看懂 memory wall，Lecture 6 教你 kernel IO，Lecture 7–8 扩展到多 GPU，而 Lecture 10 最后告诉你——**当模型真正面对用户时，这些 systems 概念一个都没有消失，反而一起变成了 LLM serving。**
