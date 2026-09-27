---
schema: bubblevan/v1
id: 
content_kind: project
title: 
weight: 20
date: 2026-09-19
updated: 2026-09-19
status: draft
visibility: public
projects:
- 
summary: 
topics:

---

## 1. LLM / Transformer Fundamentals

这一章解决的是后续所有训练、RL 和 Agent 系统默认依赖的一组对象：

```text
text
  ↓ tokenizer
token ids
  ↓ embedding
hidden states
  ↓ Transformer blocks
contextual hidden states
  ↓ LM head
logits
  ↓ softmax / sampling
next token
```

后面的 SFT、PPO、GRPO、vLLM、SGLang 都不会改变这条基本链路。它们改变的是训练信号、执行方式、缓存方式或采样方式。

本章优先回答四类问题：

1. Transformer 到底计算了什么；
2. 模型从 token 到 next-token probability 的数据流是什么；
3. 长上下文和高吞吐推理为什么会出现计算、显存瓶颈；
4. tokenizer、position、normalization 这些经常被当成“实现细节”的东西为什么会直接影响训练正确性。

### 1.0 问题矩阵

| 编号   | 问题                                                | 等级 |
| ---- | ------------------------------------------------- | -- |
| 1.1  | Decoder-only Transformer 的一个 Block 到底发生了什么？       | P0 |
| 1.2  | Self-Attention 的公式是什么？Q、K、V 分别是什么？                | P0 |
| 1.3  | 为什么 Attention 要除以 \(\sqrt{d_k}\)？                 | P0 |
| 1.4  | Causal Mask 如何保证自回归生成？                            | P0 |
| 1.5  | MHA、MQA、GQA 有什么区别？                                | P0 |
| 1.6  | RoPE 是什么？为什么能够表达相对位置？                             | P0 |
| 1.7  | LayerNorm 和 RMSNorm 有什么区别？                        | P0 |
| 1.8  | FFN、GLU、SwiGLU 在 Transformer 中做什么？                | P0 |
| 1.9  | Token ID、Logit、Probability、Log Probability 到底是什么？ | P0 |
| 1.10 | Attention 的计算和显存复杂度是多少？                           | P1 |
| 1.11 | Pre-Norm 与 Post-Norm 有什么区别？                       | P1 |
| 1.12 | Residual Connection 为什么是深层 Transformer 的基础？       | P1 |
| 1.13 | Embedding 和 LM Head 为什么可以 Weight Tying？           | P1 |
| 1.14 | RoPE 为什么会遇到长度外推问题？                                | P1 |
| 1.15 | GQA 为什么显著减少 KV Cache，却不会同比减少所有计算？                 | P1 |
| 1.16 | Dense Transformer 与 MoE 有什么区别？                    | P1 |
| 1.17 | Tokenizer 为什么不是无关紧要的 preprocessing？               | P1 |
| 1.18 | FlashAttention 为什么是 exact attention，却能大幅减少显存访问？   | P2 |
| 1.19 | 长上下文模型主要有哪些扩展路线？                                  | P2 |
| 1.20 | MoE 的 routing、load balancing、expert collapse 是什么？ | P2 |
| 1.21 | Context 从 8K 扩展到 128K，训练和推理瓶颈分别怎样变化？              | P2 |

### 1.1 Decoder-only Transformer 的一个 Block 到底发生了什么？ `[P0]`

#### 30～60 秒回答

典型 decoder-only Transformer block 可以抽象为两部分：

```text
Self-Attention
+
Feed-Forward Network
```

现代模型大量采用 Pre-Norm 结构，因此一个 block 可以写成：

$$
H'
=
H+
\operatorname{Attention}(\operatorname{Norm}(H))
$$

$$
H_{\text{out}}
=
H'
+
\operatorname{FFN}(\operatorname{Norm}(H'))
$$

也就是：

```text
hidden states
     │
     ├── Norm
     │    ↓
     │  Causal Self-Attention
     │    ↓
     └── + residual
          │
          ├── Norm
          │    ↓
          │   FFN
          │    ↓
          └── + residual
                ↓
           next block
```

Self-Attention 负责让当前位置读取前文信息，FFN 对每个 token 的 hidden state 做非线性特征变换；Residual Connection 保留原始信息并改善深层网络优化。

经过 \(N\) 个 Transformer blocks 后，最终 hidden state 通过 normalization 和 LM Head 投影到 vocabulary 维度，得到 next-token logits。

#### 数据维度

假设：

```text
batch size       = B
sequence length  = T
hidden dimension = d_model
vocabulary size  = V
```

输入：

$$
X\in\mathbb R^{B\times T\times d_{\text{model}}}
$$

经过 Transformer blocks 后仍然是：

$$
H\in\mathbb R^{B\times T\times d_{\text{model}}}
$$

LM Head：

$$
Z=HW_{\text{vocab}}
$$

其中：

$$
W_{\text{vocab}}
\in
\mathbb R^{d_{\text{model}}\times V}
$$

因此：

$$
Z
\in
\mathbb R^{B\times T\times V}
$$

\(Z_{b,t,:}\) 就是第 \(b\) 个样本在位置 \(t\) 对整个 vocabulary 的 logits。

### 面试官继续问：Attention 和 FFN 谁更耗计算？

不能直接回答“Attention”。

它取决于：

```text
sequence length T
hidden dimension d
FFN intermediate dimension
```

粗略看：

Attention score 部分：

$$
O(T^2d)
$$

线性投影和 FFN：

$$
O(Td^2)
$$

短序列、大模型宽度时，FFN 和 projection FLOPs 可能非常大；随着 \(T\) 增长，\(T^2\) attention 项才越来越突出。

所以不能把：

> Transformer 的复杂度是 \(O(T^2)\)

理解成整个 Transformer 所有计算都只有 \(T^2\) 这一项。

### 易错点

**错误：**

> Attention 负责推理，FFN 负责记忆。

这种说法过度简化。

可以用它做直觉解释，但不是严格机制。模型知识分布在 embedding、attention、FFN、residual stream 等多个部分。

---

## 1.2 Self-Attention 的公式是什么？Q、K、V 分别是什么？ `[P0]`

### 30～60 秒回答

给定输入：

$$
X\in\mathbb R^{T\times d_{\text{model}}}
$$

通过三个线性投影：

$$
Q=XW_Q
$$

$$
K=XW_K
$$

$$
V=XW_V
$$

Scaled Dot-Product Attention 为：

$$
\operatorname{Attention}(Q,K,V)
=
\operatorname{softmax}
\left(
\frac{QK^\top}{\sqrt{d_k}}
+
M
\right)V
$$

其中：

* \(Q\)：当前位置想寻找什么信息；
* \(K\)：每个历史 token 提供用于匹配的信息；
* \(V\)：匹配成功后真正读取的内容；
* \(M\)：causal mask；
* \(QK^\top\)：query 与各 key 的相关性；
* softmax 后得到 attention weights；
* attention weights 加权求和 \(V\)。

### 多头情况下的形状

假设：

```text
number of heads = h
head dimension  = d_h
d_model = h × d_h
```

则：

$$
Q,K,V
\in
\mathbb R^{B\times h\times T\times d_h}
$$

Attention score：

$$
QK^\top
\in
\mathbb R^{B\times h\times T\times T}
$$

输出：

$$
O
\in
\mathbb R^{B\times h\times T\times d_h}
$$

各 head concatenate 后再通过 output projection：

$$
\operatorname{MHA}(X)
=
\operatorname{Concat}(O_1,\ldots,O_h)W_O
$$

### 最小实现

```python
import math
import torch

def attention(q, k, v, mask=None):
    # q, k, v: [B, H, T, Dh]

    scores = q @ k.transpose(-2, -1)
    scores = scores / math.sqrt(q.size(-1))

    if mask is not None:
        scores = scores.masked_fill(~mask, float("-inf"))

    probs = torch.softmax(scores, dim=-1)

    return probs @ v
```

逻辑就是：

```text
Q × K^T
   ↓
similarity scores
   ↓
scale
   ↓
causal mask
   ↓
softmax
   ↓
attention weights
   ↓
weighted sum of V
```

### 为什么 Q/K/V 要分三个投影？

如果都直接使用同一个 \(X\)，模型能够表达的匹配与读取模式受限。

通过：

$$
W_Q,\quad W_K,\quad W_V
$$

模型可以分别学习：

```text
用于提出问题的表示
用于判断匹配的表示
用于被读取的内容表示
```

### 易错点

Attention weight：

$$
A=\operatorname{softmax}(QK^\top)
$$

不是最终 attention output。

真正输出是：

$$
AV
$$

---

## 1.3 为什么 Attention 要除以 \(\sqrt{d_k}\)？ `[P0]`

### 30～60 秒回答

假设 \(q_i\) 和 \(k_i\) 各维独立、均值约为 0、方差约为 1。

Dot product：

$$
q^\top k
=
\sum_{i=1}^{d_k}q_i k_i
$$

其方差大约随 \(d_k\) 成比例：

$$
\operatorname{Var}(q^\top k)
\approx d_k
$$

因此标准差：

$$
\operatorname{Std}(q^\top k)
\approx \sqrt{d_k}
$$

如果不缩放，head dimension 越大，attention logits 的绝对值往往越大，softmax 更容易进入饱和区域：

```text
[0.1, 0.2, 0.3]
        ↓ softmax
比较平缓

[10, 20, 30]
        ↓ softmax
接近 one-hot
```

softmax 过度饱和后梯度变小，不利于优化。

所以使用：

$$
\frac{QK^\top}{\sqrt{d_k}}
$$

把 logits 的尺度控制在更稳定的范围。

### 一个简单推导

若：

$$
q_i,k_i\sim(0,1)
$$

且独立：

$$
\operatorname{Var}(q_ik_i)
\approx 1
$$

于是：

$$
\operatorname{Var}
\left(
\sum_iq_ik_i
\right)
=
\sum_i
\operatorname{Var}(q_ik_i)
\approx d_k
$$

除以 \(\sqrt{d_k}\) 后：

$$
\operatorname{Var}
\left(
\frac{q^\top k}{\sqrt{d_k}}
\right)
\approx 1
$$

### 易错点

不是因为：

> 防止 dot product 超过 1。

Dot product 本来就不要求落在 \([-1,1]\)。

这是 **scale / variance control**，不是 cosine similarity normalization。

---

## 1.4 Causal Mask 如何保证自回归生成？ `[P0]`

### 30～60 秒回答

Decoder-only LM 训练时虽然可以一次并行计算整段 sequence，但第 \(t\) 个 token 只能看到：

$$
x_{\le t}
$$

不能看到未来：

$$
x_{>t}
$$

因此 attention score 上加入 causal mask：

$$
M_{ij}
=
\begin{cases}
0,&j\le i\\
-\infty,&j>i
\end{cases}
$$

然后：

$$
A
=
\operatorname{softmax}
\left(
\frac{QK^\top}{\sqrt{d_k}}
+
M
\right)
$$

未来 token 的 score 被变成 \(-\infty\)，softmax 后概率变成 0。

例如：

```text
       key
       0   1   2   3

q0     ✓   ×   ×   ×
q1     ✓   ✓   ×   ×
q2     ✓   ✓   ✓   ×
q3     ✓   ✓   ✓   ✓
```

### PyTorch 风格

```python
T = 4

mask = torch.tril(
    torch.ones(T, T, dtype=torch.bool)
)

print(mask)
```

逻辑上得到：

```text
1 0 0 0
1 1 0 0
1 1 1 0
1 1 1 1
```

### 为什么训练可以并行？

虽然 token \(t\) 不能看到 token \(t+1\)，但所有位置的 hidden states 可以同时计算。

这是：

```text
parallel training
```

和：

```text
autoregressive dependency
```

可以同时成立的原因。

训练：

```text
x0 x1 x2 x3
↓  ↓  ↓  ↓
一次 forward
↓
预测
x1 x2 x3 x4
```

推理则不同：

```text
x0
↓
x1
↓
x2
↓
x3
```

后一个 token 必须等待前一个真正生成出来。

### 面试官追问：Padding Mask 和 Causal Mask 是一个东西吗？

不是。

Causal Mask：

> 不允许读取未来。

Padding Mask：

> 不允许读取 padding token。

在 batching 中经常需要同时存在。

### 易错点

不要回答：

> Causal mask 把未来 token 删除了。

它不是从 tensor 中删除，而是让对应 attention probability 为 0。

---

## 1.5 MHA、MQA、GQA 有什么区别？ `[P0]`

### 30～60 秒回答

区别主要在于：

> 多个 Query heads 是否共享 Key / Value heads。

设：

```text
query heads = Hq
KV heads    = Hkv
```

### Multi-Head Attention

MHA：

$$
H_{kv}=H_q
$$

每个 query head 都拥有自己的 K/V。

```text
Q1 → K1 V1
Q2 → K2 V2
Q3 → K3 V3
Q4 → K4 V4
```

表达能力强，但 KV Cache 最大。

### Multi-Query Attention

MQA：

$$
H_{kv}=1
$$

所有 query heads 共用一组 K/V：

```text
Q1 ─┐
Q2 ─┤
Q3 ─┼── K1 V1
Q4 ─┘
```

KV Cache 极小，但共享程度非常高。

### Grouped-Query Attention

GQA：

$$
1<H_{kv}<H_q
$$

例如：

```text
Q1 ─┐
Q2 ─┴── K1 V1

Q3 ─┐
Q4 ─┴── K2 V2
```

它位于 MHA 和 MQA 之间。

### 为什么现代模型常使用 GQA？

Decode 阶段每生成一个 token，都要读取历史 K/V。

KV Cache 大致与：

$$
N_{\text{layers}}
\times
T
\times
H_{kv}
\times
d_h
$$

成正比。

所以从：

$$
H_{kv}=32
$$

降到：

$$
H_{kv}=8
$$

理论上对应部分 KV 存储约降至原来的：

$$
\frac{8}{32}
=
25\%
$$

因此 GQA 对长上下文 inference 特别有价值。

### 但是为什么不用全部 MQA？

这是 trade-off：

```text
MHA
表达能力较强
KV 成本较高

        ↓

GQA
折中

        ↓

MQA
KV 成本最低
共享最强
```

实际效果依赖模型架构和训练。

### 易错点

GQA 不代表：

> Query heads 数量减少。

减少的是 **KV heads**。

---

## 1.6 RoPE 是什么？为什么能够表达相对位置？ `[P0]`

### 30～60 秒回答

RoPE，全称 Rotary Position Embedding。

它不是简单地给 token embedding 加一个 position vector，而是根据 token 位置，对 Attention 中的 \(Q\) 和 \(K\) 做二维旋转。

对二维向量：

$$
\begin{bmatrix}
x_1\\
x_2
\end{bmatrix}
$$

位置 \(m\) 对应旋转：

$$
R(m\theta)
=
\begin{bmatrix}
\cos(m\theta)&-\sin(m\theta)\\
\sin(m\theta)&\cos(m\theta)
\end{bmatrix}
$$

于是：

$$
q_m'=R_mq
$$

$$
k_n'=R_nk
$$

两者 dot product：

$$
(q_m')^\top k_n'
=
q^\top R_m^\top R_n k
$$

由于：

$$
R_m^\top R_n
=
R_{n-m}
$$

最终 attention score 与：

$$
n-m
$$

即相对位置有关。

这就是 RoPE 能在 Attention 内自然表达相对位置信息的关键。

### 实际维度

hidden dimension 会按两维一组：

```text
(x0, x1)
(x2, x3)
(x4, x5)
...
```

每组使用不同 frequency。

常见频率形式类似：

$$
\theta_i
=
10000^{-2i/d}
$$

具体实现可以不同。

### 为什么通常旋转 Q/K，不旋转 V？

位置关系主要用于：

$$
QK^\top
$$

即“谁应该关注谁”的 attention score。

Value 承载的是最终被聚合的内容，因此经典 RoPE 主要作用于 Q/K。

### 易错点

RoPE 不是：

> 在 embedding 前面加 position ID。

position ID 只是输入；真正位置编码通过旋转 Q/K 生效。

---

## 1.7 LayerNorm 和 RMSNorm 有什么区别？ `[P0]`

### 30～60 秒回答

LayerNorm 对一个 token 的 hidden vector：

$$
x=(x_1,\ldots,x_d)
$$

先计算均值：

$$
\mu
=
\frac{1}{d}
\sum_i x_i
$$

方差：

$$
\sigma^2
=
\frac{1}{d}
\sum_i(x_i-\mu)^2
$$

然后：

$$
\operatorname{LN}(x)
=
\gamma
\frac{x-\mu}
{\sqrt{\sigma^2+\epsilon}}
+\beta
$$

RMSNorm 不减均值，只根据 root mean square 缩放：

$$
\operatorname{RMS}(x)
=
\sqrt{
\frac{1}{d}
\sum_i x_i^2
+
\epsilon
}
$$

$$
\operatorname{RMSNorm}(x)
=
\gamma
\frac{x}
{\operatorname{RMS}(x)}
$$

核心区别：

```text
LayerNorm
centering + scaling

RMSNorm
scaling only
```

RMSNorm 运算更简单，因此现代 LLM 中非常常见。

### 它们到底在 normalize 什么？

对 Transformer 来说通常是：

> 每个 token 自己的 hidden dimension。

不是：

* 在 batch dimension normalize；
* 在 sequence dimension normalize。

如果：

$$
X\in\mathbb R^{B\times T\times d}
$$

通常 normalization 发生在最后的 \(d\) 上。

### 为什么需要 Normalization？

主要作用包括：

* 控制 hidden activation scale；
* 改善深层网络训练稳定性；
* 配合 residual path 保持合理数值范围。

### 易错点

不要说：

> RMSNorm 没有任何 mean 信息。

它只是 normalization 操作本身不减去 mean，不代表模型无法编码某种平均偏移信息。

---

## 1.8 FFN、GLU、SwiGLU 在 Transformer 中做什么？ `[P0]`

### 30～60 秒回答

Attention 主要进行 token 间的信息交互；FFN 对每个 token 独立执行相同的非线性变换。

经典 FFN：

$$
\operatorname{FFN}(x)
=
W_2
\sigma(W_1x+b_1)
+b_2
$$

通常：

```text
d_model
   ↓ W1
d_ff
   ↓ activation
d_ff
   ↓ W2
d_model
```

它不直接在 sequence positions 之间混合信息：

```text
token 1 ─→ FFN ─→ token 1'
token 2 ─→ FFN ─→ token 2'
token 3 ─→ FFN ─→ token 3'
```

但每个 token 输入已经经过 Attention，包含上下文信息。

### SwiGLU

现代 LLM 常见 gated FFN。

一种典型形式：

$$
\operatorname{SwiGLU}(x)
=
W_{\text{down}}
\left[
\operatorname{SiLU}(W_{\text{gate}}x)
\odot
(W_{\text{up}}x)
\right]
$$

数据流：

```text
             ┌→ W_gate → SiLU ─┐
x ───────────┤                  × → W_down
             └→ W_up ──────────┘
```

其中：

$$
\operatorname{SiLU}(x)
=
x\sigma(x)
$$

### 为什么叫 Gate？

因为：

$$
\operatorname{SiLU}(W_gx)
$$

会逐元素调节另一条分支：

$$
W_ux
$$

哪些 feature 被放大、削弱。

### Attention 与 FFN 的功能直觉

可以粗略记为：

```text
Attention
跨 token mixing

FFN
每 token channel transformation
```

但不能将其理解为绝对的功能分工。

### 易错点

不要机械背：

> FFN hidden dimension 永远等于 \(4d_{\text{model}}\)。

经典 Transformer 常见约 4 倍 expansion，但使用 gated FFN 后，为控制总参数量，intermediate dimension 往往会重新调整，并不固定为 4 倍。

---

## 1.9 Token ID、Logit、Probability、Log Probability 到底是什么？ `[P0]`

这是后续 SFT、PPO、GRPO 必须完全分清的一题。

### Token ID

Tokenizer 把文本变成离散 vocabulary index：

```text
"hello world"
       ↓
tokenizer
       ↓
[15339, 1917]
```

这里：

```text
15339
1917
```

是 token IDs。

它们不是概率，也不是 embedding。

Embedding layer 才把：

$$
\text{token id}
$$

映射为：

$$
\mathbb R^{d_{\text{model}}}
$$

中的向量。

---

### Logit

模型最终输出：

$$
z\in\mathbb R^V
$$

例如：

```text
token A:  3.2
token B:  1.8
token C: -0.2
...
```

这些未经 normalization 的数叫 logits。

logit：

* 可以为正；
* 可以为负；
* 不要求和为 1。

---

### Probability

Softmax：

$$
p_i
=
\frac{e^{z_i}}
{\sum_j e^{z_j}}
$$

得到：

$$
0\le p_i\le1
$$

且：

$$
\sum_i p_i=1
$$

---

### Log Probability

$$
\log p_i
$$

由于：

$$
0<p_i\le1
$$

因此：

$$
\log p_i\le0
$$

例如：

$$
p=0.8
\Rightarrow
\log p\approx-0.223
$$

$$
p=0.01
\Rightarrow
\log p\approx-4.605
$$

概率越低，logprob 越负。

### 为什么训练和 RL 大量使用 logprob？

第一，sequence probability 是乘法：

$$
P(x_{1:T})
=
\prod_{t=1}^{T}
P(x_t|x_{<t})
$$

容易发生数值下溢。

取 log：

$$
\log P(x_{1:T})
=
\sum_{t=1}^{T}
\log P(x_t|x_{<t})
$$

变成加法。

第二，Policy Gradient 本身就含：

$$
\nabla_\theta
\log\pi_\theta(a|s)
$$

第三，PPO ratio 也可以稳定地从 logprob difference 计算：

$$
r
=
\frac{\pi_\theta(a|s)}
{\pi_{\text{old}}(a|s)}
=
\exp
\left(
\log\pi_\theta(a|s)
-
\log\pi_{\text{old}}(a|s)
\right)
$$

这个公式后面会反复出现。

### Temperature

采样时常用：

$$
p_i
=
\operatorname{softmax}
\left(
\frac{z_i}{T}
\right)
$$

\(T<1\)：

```text
distribution sharper
```

\(T>1\)：

```text
distribution flatter
```

注意：

> Temperature 修改的是 sampling distribution。

后续做 RL 时必须清楚 old logprob 到底来自哪个实际 behavior distribution。

---

# P1

## 1.10 Attention 的计算和显存复杂度是多少？ `[P1]`

### 面试回答

对于 sequence length \(T\)、hidden dimension \(d\)，标准 dense attention 中：

$$
QK^\top
$$

需要构造：

$$
T\times T
$$

attention score matrix。

因此 attention score 相关计算约为：

$$
O(T^2d)
$$

朴素实现需要保存 \(T^2\) 级别 attention matrix，因此显存也会出现：

$$
O(T^2)
$$

项。

但整个 Transformer block 还有 projection 和 FFN：

$$
O(Td^2)
$$

所以完整复杂度应该看：

$$
O(Td^2+T^2d)
$$

而不是简单说：

> Transformer 就是 \(O(T^2)\)。

### Attention 内部

Q/K/V projection：

$$
O(Td^2)
$$

计算：

$$
QK^\top
$$

约：

$$
O(T^2d)
$$

计算：

$$
AV
$$

又约：

$$
O(T^2d)
$$

因此核心 attention：

$$
O(T^2d)
$$

量级。

### FFN

如果：

$$
d_{\text{ff}}\approx c d
$$

则：

$$
O(Tdd_{\text{ff}})
\approx
O(Td^2)
$$

### 哪一项占主导？

比较：

$$
T^2d
$$

与：

$$
Td^2
$$

比值：

$$
\frac{T^2d}{Td^2}
=
\frac{T}{d}
$$

因此它和：

$$
\frac{T}{d}
$$

密切相关。

短序列时 projection / FFN 完全可能占大量 FLOPs。

长 context 后 attention 项迅速增加。

---

## 1.11 Pre-Norm 与 Post-Norm 有什么区别？ `[P1]`

### 结构

经典 Post-Norm：

$$
x'
=
\operatorname{Norm}
(
x+\operatorname{Sublayer}(x)
)
$$

即：

```text
x
├──────────────┐
↓              │
Sublayer       │
↓              │
+ ←────────────┘
↓
Norm
```

Pre-Norm：

$$
x'
=
x+
\operatorname{Sublayer}
(
\operatorname{Norm}(x)
)
$$

即：

```text
x
├─────────────────────────┐
↓                         │
Norm                      │
↓                         │
Sublayer                  │
↓                         │
+ ←───────────────────────┘
```

### 为什么 Pre-Norm 更容易训练深层模型？

看 residual path：

$$
x_{l+1}
=
x_l+
F_l(\operatorname{Norm}(x_l))
$$

即使 \(F_l\) 路径梯度复杂，仍存在接近 identity 的 residual gradient path：

$$
\frac{\partial x_{l+1}}
{\partial x_l}
=
I+
\cdots
$$

因此梯度可以沿 residual stream 更直接地跨层传播。

Post-Norm 把 normalization 放在 residual addition 后，对这种 identity path 的梯度传播影响更直接。

### 是否意味着 Post-Norm 一定差？

不是。

不同 initialization、normalization、residual scaling 和训练 recipe 可以改变稳定性。

面试应该回答：

> Pre-Norm 通常更利于非常深的 Transformer 优化，但不是数学上规定所有 Transformer 必须采用 Pre-Norm。

---

## 1.12 Residual Connection 为什么是深层 Transformer 的基础？ `[P1]`

### 基本形式

$$
x_{l+1}
=
x_l+F_l(x_l)
$$

模型不必每一层重新构造全部表示，而只需要学习一个 residual update：

$$
\Delta x_l
=
F_l(x_l)
$$

于是：

$$
x_L
=
x_0
+
\sum_{l=0}^{L-1}
\Delta x_l
$$

从 residual-stream 角度可以理解为：

> 每层都在共享表示空间里写入一次更新。

### 梯度

$$
\frac{\partial x_{l+1}}
{\partial x_l}
=
I+
\frac{\partial F_l}
{\partial x_l}
$$

其中 identity 项：

$$
I
$$

提供了一条不完全依赖 \(F_l\) Jacobian 的梯度路径。

如果没有 residual：

$$
x_{l+1}=F_l(x_l)
$$

几十甚至上百层 Jacobian 连乘后，优化会困难得多。

### 为什么不能说 Residual 只是防止梯度消失？

因为它还改变了：

* representation update 方式；
* optimization landscape；
* information preservation；
* 各层之间的组合方式。

---

## 1.13 Embedding 和 LM Head 为什么可以 Weight Tying？ `[P1]`

### 输入 Embedding

Vocabulary：

$$
V
$$

hidden dimension：

$$
d
$$

embedding matrix：

$$
E\in\mathbb R^{V\times d}
$$

token ID \(i\) 对应：

$$
E_i
$$

### 输出 LM Head

hidden state：

$$
h\in\mathbb R^d
$$

需要得到 vocabulary logits：

$$
z\in\mathbb R^V
$$

普通 LM head：

$$
z=W_{\text{out}}h
$$

其中：

$$
W_{\text{out}}
\in
\mathbb R^{V\times d}
$$

Embedding 和 LM Head 的 shape 恰好一致。

Weight tying 设置：

$$
W_{\text{out}}=E
$$

于是：

$$
z_i
=
E_i^\top h
$$

直觉上：

> 用 token 的 embedding 作为判断当前 hidden state 与这个 token 匹配程度的输出向量。

### 好处

第一，减少参数。

原本：

$$
2Vd
$$

级别参数：

```text
input embedding
+
output projection
```

共享后只需要：

$$
Vd
$$

级别的 vocabulary matrix。

第二，输入和输出 vocabulary representation 被约束到同一个空间。

### 为什么不是所有模型都必须 tying？

因为可能存在：

* architecture-specific projection；
* embedding dimension 与 hidden dimension 不同；
* output head 有额外 transformation；
* 特殊词表或 multimodal vocabulary 设计。

所以这是常见设计，不是定律。

---

## 1.14 RoPE 为什么会遇到长度外推问题？ `[P1]`

假设模型训练最大位置：

$$
0\le m<L_{\text{train}}
$$

推理突然使用：

$$
m\gg L_{\text{train}}
$$

虽然 RoPE 数学上仍然可以计算：

$$
\cos(m\theta_i),\quad
\sin(m\theta_i)
$$

但：

> 可计算不等于模型学会了如何解释这些位置模式。

### 一个重要原因：phase distribution 改变

训练阶段模型只见过一定范围内：

$$
m\theta_i
$$

对应的 rotation pattern。

超出训练长度后，一些 frequency 上的 phase 关系进入训练时很少甚至没有覆盖的区域。

因此 attention score 分布可能偏离训练分布。

### 高频和低频维度

RoPE 使用多个 frequency：

```text
high-frequency dimensions
变化快

low-frequency dimensions
变化慢
```

长位置下，不同频率受到的 extrapolation 压力不同。

### 常见解决思路

不要求这里背所有具体方法名字，但必须理解几类思想：

#### 1. Position Interpolation

将更长的位置映射回训练过的位置范围。

例如：

$$
m'
=
m
\frac{L_{\text{train}}}
{L_{\text{target}}}
$$

不是直接使用原始 \(m\)。

#### 2. Frequency Scaling

调整不同 RoPE frequency，使长距离 phase 变化更加适合扩展。

#### 3. Long-context Continued Training

直接使用长 sequence 继续训练，让模型真正接触长位置分布。

### 易错点

长上下文不是只改：

```text
max_position_embeddings=131072
```

就结束。

至少还涉及：

```text
position representation
attention compute
KV memory
training data
optimization
inference scheduler
```

---

## 1.15 GQA 为什么显著减少 KV Cache，却不会同比减少所有计算？ `[P1]`

这是很常见的追问题。

设：

$$
H_q=32
$$

MHA：

$$
H_{kv}=32
$$

GQA：

$$
H_{kv}=8
$$

那么 KV Cache 与 KV head 数近似线性：

$$
M_{KV}
\propto H_{kv}
$$

因此 KV Cache 可近似下降为：

$$
\frac{8}{32}
=
25\%
$$

原来的 K/V head 部分。

### 但是 Query 仍然存在 32 个 heads

Attention 输出仍对应所有 query heads：

$$
H_q=32
$$

所以：

* Q projection 没有按 4 倍缩小；
* 每个 query head 仍要对历史 K 做 attention；
* output projection 没有按 4 倍缩小；
* FFN 完全没有因此缩小。

GQA 主要减少：

```text
K projection
V projection
KV cache
KV memory bandwidth
```

而不是把整个 Transformer FLOPs 同比例减少。

### Decode 为什么特别受益？

Decode 时：

```text
new query
    ↓
read all historical K/V
    ↓
attention
```

大量工作受 KV Cache bandwidth 影响。

降低 KV heads 对：

* 显存容量；
* HBM bandwidth；
* 并发 request 数；

都非常有价值。

---

## 1.16 Dense Transformer 与 MoE 有什么区别？ `[P1]`

### Dense FFN

普通 Transformer 中，每个 token 都经过同一套 FFN：

$$
y=\operatorname{FFN}(x)
$$

假设 FFN 有：

$$
P
$$

个参数，那么每个 token 都激活这套参数。

---

### MoE

Mixture-of-Experts 将 FFN 替换为多个 expert：

$$
E_1,E_2,\ldots,E_N
$$

router 根据 token hidden state 计算：

$$
p
=
\operatorname{softmax}(W_rx)
$$

然后选择 Top-\(k\) experts。

例如：

```text
token x
  ↓
router
  ↓
scores

E1  0.05
E2  0.70 ←
E3  0.10
E4  0.15 ←

Top-2:
E2 + E4
```

输出类似：

$$
y
=
\sum_{i\in\operatorname{TopK}(x)}
p_iE_i(x)
$$

### 最大特点

MoE 可以做到：

```text
Total Parameters 很大
Active Parameters 较小
```

例如很多 experts 被存储，但单个 token 只经过 Top-1 或 Top-2 experts。

因此可以在不同比例增加 per-token FLOPs 的情况下扩大模型总参数容量。

### 代价

MoE 会产生额外问题：

* router；
* load balancing；
* expert capacity；
* token dispatch；
* expert parallel；
* All-to-All communication；
* expert imbalance。

所以：

> 参数更多

不等于：

> 系统实现更轻松。

---

## 1.17 Tokenizer 为什么不是无关紧要的 preprocessing？ `[P1]`

这是后面 Agent RL 特别重要的一题。

### Tokenizer 决定模型真正看到的离散序列

模型没有直接看到：

```text
"Search for OpenAI"
```

它看到的是：

$$
[t_1,t_2,\ldots,t_n]
$$

token boundary 直接影响：

* sequence length；
* context budget；
* next-token prediction；
* logprob；
* loss mask；
* generation boundary。

### 同样的人类文本，不同 tokenizer 可能得到不同 tokenization

例如：

```text
"unbelievable"
```

可能是：

```text
["un", "believ", "able"]
```

也可能是：

```text
["unbelievable"]
```

因此 token-level loss 根本不是 tokenizer-independent quantity。

### Chat Template 更进一步

输入不是简单：

```text
user text
assistant text
```

模型实际可能看到：

```text
<bos>
<user>
...
</user>
<assistant>
...
</assistant>
```

或者另一套特殊 token。

因此：

```text
conversation
    ↓
chat template
    ↓
serialized text / special tokens
    ↓
tokenizer
    ↓
exact model input IDs
```

任何环节变化都可能改变训练输入。

### 为什么 decode → tokenize 可能无法恢复原始 generation IDs？

原始：

$$
[t_1,t_2,t_3]
$$

先：

```text
decode
```

得到字符串 \(s\)。

再：

```text
tokenize(s)
```

不能一般性保证：

$$
\operatorname{encode}
(
\operatorname{decode}
(
[t_1,t_2,t_3]
)
)
=
[t_1,t_2,t_3]
$$

原因包括：

* special tokens；
* whitespace boundary；
* normalization；
* tokenizer-specific merging；
* decode 对某些 token representation 的信息丢失。

因此真正需要 token-level provenance 时：

> 最可靠的是生成阶段直接保存 actual token IDs。

这点后面 Macro 5 会继续展开。

---

# P2

## 1.18 FlashAttention 为什么是 exact attention，却能大幅减少显存访问？ `[P2]`

### 面试回答

FlashAttention 并没有把标准 Attention 近似成另一个公式。

它仍然计算：

$$
\operatorname{softmax}
\left(
\frac{QK^\top}{\sqrt d}
\right)V
$$

因此是 exact attention，差别主要在于：

> 改变计算顺序，使用 tiling 和 online softmax，让中间的巨大 \(T\times T\) attention matrix 不必完整写回 HBM。

优化重点不是减少数学 FLOPs 的渐近复杂度，而是减少 GPU memory hierarchy 中昂贵的 HBM reads/writes。

---

### 朴素 Attention

可以粗略理解：

```text
Q, K
 ↓
QK^T
 ↓
write N×N score matrix to HBM

read score matrix
 ↓
softmax
 ↓
write N×N probability matrix to HBM

read probability matrix + V
 ↓
output
```

当 \(T\) 很大：

$$
T^2
$$

中间矩阵会产生大量 HBM traffic。

GPU 的 compute 很快，但 HBM bandwidth 是有限资源。

结果经常不是：

> 算不动。

而是：

> 数据来回搬得太慢。

---

### FlashAttention

思想是把：

```text
Q
K
V
```

切成 tiles。

小块读入更快的片上存储，例如 SRAM/register 级存储区域，计算局部 attention。

问题是：

> Softmax 的 denominator 需要整行所有元素，怎么分块？

关键是 online softmax。

---

### Online Softmax

普通 softmax：

$$
p_i
=
\frac{e^{x_i}}
{\sum_je^{x_j}}
$$

为了数值稳定：

$$
p_i
=
\frac{e^{x_i-m}}
{\sum_je^{x_j-m}}
$$

其中：

$$
m=\max_jx_j
$$

如果分块处理，可以维护当前：

```text
running maximum m
running normalization sum l
running output
```

假设旧块：

$$
m_{\text{old}}
$$

新块最大值：

$$
m_{\text{block}}
$$

新的最大值：

$$
m_{\text{new}}
=
\max(
m_{\text{old}},
m_{\text{block}}
)
$$

旧 normalization 可以重新缩放：

$$
l_{\text{new}}
=
e^{m_{\text{old}}-m_{\text{new}}}
l_{\text{old}}
+
\sum_{j\in\text{block}}
e^{x_j-m_{\text{new}}}
$$

因此不需要一次保存整行所有 logits。

---

### FlashAttention 优化的本质

传统 attention 的问题包含：

```text
arithmetic cost
+
memory IO cost
```

FlashAttention 主要攻击：

```text
memory IO
```

通过：

* tiling；
* kernel fusion；
* online softmax；
* 避免 materialize 完整 attention matrix；

显著减少 HBM traffic。

### 它有没有把 \(O(T^2)\) 变成 \(O(T)\)？

没有。

Dense attention 的 pairwise interactions 仍然存在：

$$
O(T^2)
$$

计算结构没有凭空消失。

它主要改变：

> 实际硬件上的执行效率和中间存储需求。

这是面试中特别容易答错的地方。

---

## 1.19 长上下文模型主要有哪些扩展路线？ `[P2]`

不能把长上下文问题理解成单一问题。

它至少有五层：

```text
Position
Attention compute
KV memory
Training
Information utilization
```

### 路线一：位置编码扩展

解决：

> 模型能不能表示训练长度之外的位置？

例如：

* position interpolation；
* RoPE scaling；
* frequency adjustment；
* long-context continued training。

解决的是 **position extrapolation**。

但它不自动解决 \(T^2\) attention。

---

### 路线二：优化 Exact Attention

例如 FlashAttention 类型方案。

目标：

```text
数学 attention 不变
↓
降低 memory IO
↓
提升实际 kernel efficiency
```

优势：

> 不牺牲 full attention connectivity。

但 dense pairwise complexity 仍存在。

---

### 路线三：Sparse / Local / Sliding-window Attention

限制每个 token 可见范围：

```text
full attention:

token ─────────────→ all previous tokens

sliding window:

token ─────────────→ previous W tokens
```

复杂度从：

$$
O(T^2)
$$

可以向：

$$
O(TW)
$$

变化，其中：

$$
W\ll T
$$

代价：

> 任意远距离 token 不再直接连接。

---

### 路线四：External Retrieval / Memory

不要求把所有历史信息常驻 context。

```text
large information space
       ↓ retrieval
small relevant subset
       ↓
LLM context
```

这是 RAG / Search Agent / Memory 系统的重要动机。

它解决：

> 信息量可以远大于模型 context。

但引入：

* retrieval error；
* search policy；
* tool latency；
* evidence selection；
* credit assignment。

---

### 路线五：Context Compression / Structured State

不是保留全部 raw history，而是：

```text
raw history
   ↓
summary / memory / state
   ↓
compact context
```

Long-horizon Agent 后面会反复遇到。

---

### 面试时可以画成

```text
               Long Context
                    │
       ┌────────────┼────────────┐
       │            │            │
   Position       Compute      Memory
       │            │            │
 RoPE scaling    FlashAttn    KV optimization
 interpolation   Sparse Attn  Quantization
       │            │            │
       └────────────┼────────────┘
                    │
             Information Side
                    │
          Retrieval / Compression
          Memory / Structured State
```

### 一个重要结论

下面四句话不是一回事：

```text
模型支持 128K position
模型能跑 128K
模型能高效跑 128K
模型能有效利用 128K
```

它们分别涉及：

```text
position
memory/compute
systems
model capability
```

---

## 1.20 MoE 的 routing、load balancing、expert collapse 是什么？ `[P2]`

### Router

给 token hidden state：

$$
x
$$

router 计算：

$$
z=W_rx
$$

然后：

$$
p=
\operatorname{softmax}(z)
$$

选择：

$$
\operatorname{TopK}(p)
$$

例如：

```text
Expert 0    0.02
Expert 1    0.64  ←
Expert 2    0.07
Expert 3    0.27  ←
```

Top-2 routing 就将 token 发给：

```text
Expert 1
Expert 3
```

---

### 为什么 routing 会出问题？

如果 router 自由优化，可能逐渐偏向几个当前表现比较好的 experts：

```text
所有 token
   ↓
Expert 3
Expert 3
Expert 3
Expert 3
```

导致：

```text
popular experts
overloaded

other experts
under-trained
```

这形成正反馈：

```text
某 expert 被选得多
       ↓
得到更多训练信号
       ↓
表现更好
       ↓
router 更喜欢它
       ↓
被选得更多
```

---

### Load Balancing

训练中通常需要鼓励 routing distribution 更平衡。

概念上希望：

$$
\operatorname{Load}(E_i)
\approx
\frac{1}{N}
$$

而不是：

```text
E1  80%
E2   5%
E3   5%
E4  10%
```

实际方法可能结合：

* auxiliary balancing loss；
* routing bias；
* expert capacity；
* token dropping / rerouting；
* load-aware routing。

---

### Expert Capacity

每个 expert 单 batch 能处理的 token 数有限。

如果大量 token 被路由到同一 expert：

```text
expert queue overflow
```

需要：

* drop token；
* reroute；
* increase capacity；
* improve balancing。

---

### Expert Collapse

广义理解是：

> router 或 experts 的 specialization 退化，大量 token 过度集中于少量 experts，其他 expert 利用率和学习信号不足。

不仅影响模型质量，也影响系统效率。

因为 MoE 的一个关键前提是：

```text
experts distributed across devices
```

如果 routing 极度不均：

```text
GPU 0 expert:
100% busy

GPU 1 expert:
30% busy

GPU 2 expert:
20% busy
```

整个 step 仍然必须等待最慢 worker。

因此 load imbalance 同时是：

```text
ML optimization problem
+
distributed systems problem
```

这就是后面 Expert Parallel 为什么不能脱离 MoE routing 单独理解。

---

## 1.21 Context 从 8K 扩展到 128K，训练和推理瓶颈分别怎样变化？ `[P2]`

这是非常适合作为综合系统题的一问。

假设：

$$
T:
8192
\rightarrow
131072
$$

sequence length 增长：

$$
16\times
$$

---

### 一、Attention score 数量

Dense attention：

$$
T^2
$$

因此：

$$
16^2
=
256
$$

倍。

也就是说，仅看 pairwise attention 元素：

```text
8K → 128K

×16 length
→ ×256 pair interactions
```

所以 training prefill 类 full-sequence computation 的压力会急剧增加。

注意：

> 整个 Transformer FLOPs 不一定精确增加 256 倍。

因为：

$$
Td^2
$$

这部分只增加 16 倍。

总复杂度是：

$$
O(Td^2+T^2d)
$$

---

### 二、训练显存

训练不仅要 forward，还要 backward。

需要考虑：

```text
activations
attention intermediates
Q/K/V
FFN activations
optimizer state
parameters
gradients
```

sequence 增长会显著增加 activation memory。

如果朴素 materialize attention matrix：

$$
O(T^2)
$$

显存很快不可接受。

FlashAttention 等技术通过不保存完整 attention matrix，大幅缓解这一问题，但：

> activation 与计算压力并不会因此完全消失。

---

### 三、Inference Prefill

用户给：

```text
128K prompt
```

模型首先要做 prefill。

Prefill 处理整段 prompt，因此同样面临大规模 attention 计算。

指标上直接影响：

```text
TTFT
Time To First Token
```

长 prompt 可能让 TTFT 显著变长。

---

### 四、Inference Decode

生成阶段每次只有：

```text
1 new token
```

有 KV Cache 后，不需要重新计算所有历史 token 的 K/V。

但新的 query 仍需与所有历史 keys 做 attention。

因此单个 decode step 的 attention 大致随 context length：

$$
O(Td)
$$

增长。

从 8K 到 128K：

```text
每个 decode token
需要读取约 16× 更长的历史 KV
```

这会提高：

* TPOT；
* HBM bandwidth pressure。

---

### 五、KV Cache

KV Cache 大致：

$$
M_{KV}
=
2
\times
L
\times
T
\times
H_{kv}
\times
d_h
\times
b
$$

其中：

* \(2\)：K 和 V；
* \(L\)：layers；
* \(T\)：context length；
* \(H_{kv}\)：KV heads；
* \(d_h\)：head dimension；
* \(b\)：每元素 bytes。

所以：

$$
M_{KV}\propto T
$$

8K → 128K：

$$
16\times
$$

KV Cache。

这会直接降低单 GPU 可同时容纳的 requests。

---

### 六、Position Extrapolation

即使显存足够，也还存在：

```text
RoPE / positional distribution
```

问题。

模型：

```text
能计算 128K
```

不等于：

```text
在训练分布之外仍能正确理解 128K。
```

---

### 七、信息利用问题

还有一个纯 capability 问题。

即使：

```text
position OK
compute OK
memory OK
```

模型仍可能出现：

```text
lost in the middle
distractor interference
retrieval failure
reasoning degradation
```

因此 context length 不是单纯 hardware specification。

---

### 面试综合回答

如果面试官问：

> 8K 模型改成 128K 最大的问题是什么？

不要只回答：

> Attention 是 \(O(n^2)\)。

更完整的是：

```text
训练侧
─────────────────────────
position extrapolation
attention compute
activation memory
long-context data
optimization stability

推理 prefill
─────────────────────────
attention compute
TTFT

推理 decode
─────────────────────────
KV cache capacity
KV bandwidth
TPOT

模型能力
─────────────────────────
long-context utilization
interference
retrieval / reasoning quality
```

这四层才是完整答案。

---

# 1.22 Macro 1 高频连环追问

学完本章后，至少应该能不看资料连续回答下面这一组问题：

### 第一组：Attention

```text
Self-Attention 的公式是什么？
↓
为什么除 sqrt(dk)？
↓
causal mask 加在哪里？
↓
为什么训练能并行、推理却必须自回归？
↓
MHA/MQA/GQA 怎么区别？
↓
GQA 为什么减少 KV Cache？
↓
为什么它不会把整个模型 FLOPs 同比例减少？
```

### 第二组：Representation

```text
Transformer block 有哪些部分？
↓
为什么需要 residual？
↓
Pre-Norm 为什么容易训练？
↓
LayerNorm 和 RMSNorm 区别？
↓
FFN 做什么？
↓
SwiGLU 为什么有两条 projection 分支？
```

### 第三组：Position

```text
RoPE 怎么做？
↓
为什么能表达 relative position？
↓
超出训练长度为什么可能失效？
↓
position interpolation 在做什么？
↓
把 max_position 改成 128K 为什么不等于获得 128K 能力？
```

### 第四组：Token

```text
Token ID 是什么？
↓
Embedding 是什么？
↓
Logit 是什么？
↓
Probability 是什么？
↓
Logprob 为什么总 ≤ 0？
↓
sequence probability 为什么转成 logprob sum？
↓
为什么 decode 后不能默认重新 tokenize 恢复原 token IDs？
```

### 第五组：Systems

```text
Attention 为什么是 O(T²)？
↓
整个 Transformer 为什么不能简单写成只有 O(T²)？
↓
FlashAttention 为什么还是 exact？
↓
它优化 FLOPs 还是 IO？
↓
128K context 为什么让 prefill 和 decode 遇到不同瓶颈？
```

---

# 1.23 Macro 1 自测

## Self-test 1

给定：

```text
B = 8
T = 4096
d_model = 4096
num_heads = 32
```

求：

$$
d_h
$$

答案：

$$
d_h
=
\frac{4096}{32}
=
128
$$

并说明：

$$
Q
\in
\mathbb R^{8\times32\times4096\times128}
$$

attention score：

$$
QK^\top
\in
\mathbb R^{8\times32\times4096\times4096}
$$

---

## Self-test 2

为什么下面的话不完整？

> Transformer 的复杂度是 \(O(n^2)\)。

应该补：

标准 self-attention 的 pairwise attention 部分是：

$$
O(T^2d)
$$

但 block 中 projection 和 FFN 有：

$$
O(Td^2)
$$

因此完整计算量同时依赖 \(T\) 与 \(d\)。

---

## Self-test 3

为什么：

```text
GQA KV heads:
32 → 8
```

不能推出：

```text
整个模型推理 FLOPs → 25%
```

因为只降低 K/V projection、KV cache 及相关 memory traffic，Query、Attention query heads、output projection、FFN 等仍存在。

---

## Self-test 4

解释：

$$
R_m^\top R_n=R_{n-m}
$$

为什么是 RoPE 能编码相对位置的关键。

因为经过 position-dependent rotation 后：

$$
(R_mq)^\top(R_nk)
=
q^\top R_{n-m}k
$$

attention score 中的位置关系可以写成相对位移 \(n-m\) 的函数。

---

## Self-test 5

为什么：

```text
token IDs
→ decode
→ string
→ encode
```

不应该被当成严格 identity operation？

需要从：

* tokenizer normalization；
* special tokens；
* whitespace；
* segmentation；
* decode 信息损失；

几个角度回答。

---

# 1.24 推导题

## 推导题 1：为什么需要 \(\sqrt{d_k}\)？

从：

$$
q^\top k
=
\sum_{i=1}^{d_k}q_ik_i
$$

出发，在简单独立同分布假设下说明：

$$
\operatorname{Var}(q^\top k)
\propto d_k
$$

所以除以：

$$
\sqrt{d_k}
$$

将 score scale 恢复到约 \(O(1)\)。

---

## 推导题 2：RoPE 相对位置

从：

$$
q_m=R_mq
$$

$$
k_n=R_nk
$$

推导：

$$
q_m^\top k_n
=
q^\top R_{n-m}k
$$

解释为什么 dot-product attention 可以获得相对位置信息。

---

## 推导题 3：长 Context

如果 sequence length：

$$
T\rightarrow16T
$$

分别回答：

```text
Attention score elements
→ 256×

KV Cache
→ 16×

FFN token computation
→ 16×
```

并解释为什么完整模型运行时间不能仅从其中一个数字直接推出。

---

# 1.25 Debug 题

## Debug 1

模型生成突然重复：

```text
the the the the the ...
```

可以检查：

```text
logits 是否异常
temperature
top-p / top-k
repetition control
EOS
tokenizer / special token
KV cache correctness
模型本身
```

不能直接断言是 Attention 出错。

---

## Debug 2

同一个 prompt：

```text
framework A
```

和：

```text
framework B
```

得到完全不同输出。

排查至少包括：

```text
model checkpoint
tokenizer
chat template
special tokens
system prompt
sampling params
seed
precision
backend implementation
```

不是只比较用户看到的字符串 prompt。

---

## Debug 3

模型号称支持 128K，但 80K 后性能明显下降。

至少区分：

```text
OOM / 系统无法运行
vs
能够运行但 TTFT 太长
vs
位置外推失败
vs
信息利用失败
vs
distractor interference
```

这几个问题需要完全不同的解决方法。

---

# 1.26 本章需要形成的最小知识图

最终不要把本章记成 21 个孤立答案。

应该形成：

```text
Text
 ↓
Tokenizer
 ↓
Token IDs
 ↓
Embedding
 ↓
┌─────────────────────────────┐
│ Transformer Block           │
│                             │
│ Norm                        │
│  ↓                          │
│ Q / K / V                   │
│  ↓                          │
│ RoPE                        │
│  ↓                          │
│ Causal Attention            │
│  ↓                          │
│ Residual                    │
│  ↓                          │
│ Norm                        │
│  ↓                          │
│ SwiGLU / FFN                │
│  ↓                          │
│ Residual                    │
└─────────────────────────────┘
 ↓ × N
Final Norm
 ↓
LM Head
 ↓
Logits
 ↓
Softmax / Sampling
 ↓
Token ID
 ↓
append to context
 ↓
next autoregressive step
```

与此同时，系统侧还有另一条链：

```text
Longer Context
      │
      ├── position problem
      │     └── RoPE extrapolation
      │
      ├── compute problem
      │     └── T² Attention
      │          └── FlashAttention / sparse attention
      │
      ├── memory problem
      │     └── KV Cache
      │          └── GQA / quantization / eviction
      │
      └── capability problem
            └── information utilization / interference
```

Macro 2 将从这里继续向：

```text
logits
  ↓
labels
  ↓
cross entropy
  ↓
backward
  ↓
optimizer
  ↓
SFT
```

展开。

## 2. Training / SFT / Optimization

这一章解决从：

```text
token ids
   ↓
forward
   ↓
logits
   ↓
loss
   ↓
backward
   ↓
gradients
   ↓
optimizer
   ↓
updated parameters
```

到真正可训练 LLM 的完整数据流。

后面的 RLHF、PPO、GRPO 本质上仍然依赖同一套基础设施：

```text
模型产生 logits
      ↓
定义 objective
      ↓
autograd
      ↓
gradient
      ↓
optimizer.step()
```

区别主要是：

> SFT 的学习信号来自 ground-truth token；RL 的学习信号来自 reward / advantage。

因此如果：

* causal shift；
* response mask；
* token averaging；
* optimizer state；
* mixed precision；
* gradient accumulation；

这些概念不牢，后面的 Agent RL 很容易只停留在“知道公式”。

---

## 2.0 问题矩阵

| 编号   | 问题                                                         | 等级 |
| ---- | ---------------------------------------------------------- | -- |
| 2.1  | Causal Language Model 的训练 objective 是什么？                   | P0 |
| 2.2  | Cross Entropy、NLL 和 Perplexity 是什么关系？                      | P0 |
| 2.3  | Teacher Forcing 是什么？                                       | P0 |
| 2.4  | 为什么 Causal LM 的 logits 和 labels 要 shift？                   | P0 |
| 2.5  | Attention Mask、Padding Mask、Label Mask、Loss Mask 有什么区别？    | P0 |
| 2.6  | Adam 和 AdamW 有什么区别？                                        | P0 |
| 2.7  | Batch、Micro Batch、Gradient Accumulation、Global Batch 怎么区分？ | P0 |
| 2.8  | FP32、FP16、BF16、FP8 分别是什么？                                  | P0 |
| 2.9  | SFT 到底训练什么？为什么经常只训练 assistant tokens？                      | P0 |
| 2.10 | Weight Decay 为什么不等价于 Adam 中直接加 L2？                         | P1 |
| 2.11 | Learning Rate Warmup 和 Cosine Decay 为什么常见？                 | P1 |
| 2.12 | Gradient Clipping 在防什么？                                    | P1 |
| 2.13 | Chat Template 为什么会影响训练正确性？                                 | P1 |
| 2.14 | Padding、Packing、Sequence Packing 有什么区别？                    | P1 |
| 2.15 | LoRA 的低秩假设是什么？                                             | P1 |
| 2.16 | QLoRA 为什么能显著降低显存？                                          | P1 |
| 2.17 | Activation Checkpointing 为什么用计算换显存？                        | P1 |
| 2.18 | 为什么固定 seed 也不一定完全复现？                                       | P1 |
| 2.19 | Full Fine-Tuning、LoRA、QLoRA 怎么选择？                          | P2 |
| 2.20 | 一个训练过程出现 NaN / Inf，应该怎样系统排查？                               | P2 |
| 2.21 | 怎样估算 LLM 训练显存？                                             | P2 |
| 2.22 | Sequence Packing 为什么可能产生样本污染？                              | P2 |
| 2.23 | 为什么训练 loss 下降不代表模型真的变好了？                                   | P2 |

---

# P0

## 2.1 Causal Language Model 的训练 objective 是什么？ `[P0]`

### 30～60 秒回答

给定 token sequence：

$$
x_1,x_2,\ldots,x_T
$$

自回归语言模型将联合概率分解为：

$$
p_\theta(x_{1:T})
=
\prod_{t=1}^{T}
p_\theta(x_t|x_{<t})
$$

训练目标通常是最大化 log-likelihood：

$$
\max_\theta
\sum_{t=1}^{T}
\log p_\theta(x_t|x_{<t})
$$

等价于最小化 Negative Log-Likelihood：

$$
\mathcal L
=
-\sum_{t=1}^{T}
\log p_\theta(x_t|x_{<t})
$$

实际实现通常按有效 token 平均：

$$
\mathcal L
=
-
\frac{
\sum_t m_t
\log p_\theta(x_t|x_{<t})
}{
\sum_t m_t
}
$$

其中：

$$
m_t\in\{0,1\}
$$

是 loss mask。

### 直觉

模型不断做同一件事：

```text
已有前缀
   ↓
预测下一个 token
   ↓
和真实 token 比较
   ↓
更新参数
```

例如：

```text
输入:
I like machine learning

训练目标:

I          → like
I like     → machine
I like ... → learning
```

### 为什么叫 Causal？

因为：

$$
x_t
$$

的预测只能依赖：

$$
x_{<t}
$$

不能读取未来：

$$
x_{>t}
$$

由 causal attention mask 保证。

### 易错点

不要回答：

> LLM 的训练目标就是 Cross Entropy。

Cross Entropy 是实现这个 maximum likelihood objective 的常用 loss。

更完整的因果关系是：

```text
autoregressive maximum likelihood
        ↓
negative log likelihood
        ↓
cross entropy implementation
```

---

## 2.2 Cross Entropy、NLL 和 Perplexity 是什么关系？ `[P0]`

### Cross Entropy

真实 label 是 token：

$$
y
$$

模型输出 vocabulary distribution：

$$
p_\theta(v)
$$

one-hot target 下：

$$
\mathcal L_{CE}
=
-\sum_v
y_v\log p_\theta(v)
$$

由于真实 label 只有一个位置为 1：

$$
\mathcal L_{CE}
=
-\log p_\theta(y)
$$

这就是 Negative Log-Likelihood。

所以对于标准 one-hot next-token prediction：

$$
CE=NLL
$$

在数值上等价。

---

### PyTorch 中 CrossEntropyLoss 实际吃什么？

它通常接收：

```text
raw logits
+
target class ID
```

而不是先手工 softmax。

概念上：

$$
\operatorname{CrossEntropy}(z,y)
=
-\log
\operatorname{softmax}(z)_y
$$

实现通常结合：

```text
log-softmax
+
NLL
```

以提高数值稳定性。

---

### Perplexity

如果平均 token NLL 为：

$$
\mathcal L
$$

则：

$$
PPL=e^\mathcal L
$$

例如：

$$
\mathcal L=\ln 10
$$

则：

$$
PPL=10
$$

直觉上可以粗略理解为：

> 模型在每一步面对的有效不确定性规模。

但不要机械解释成：

> 模型每一步真的只在 10 个 token 中选择。

这只是一个指数化的平均 log-loss 指标。

---

### 为什么 PPL 不能随便跨 tokenizer 比？

因为 tokenization 不同：

```text
同一段文本
↓
tokenizer A: 100 tokens
tokenizer B: 140 tokens
```

token-level likelihood 的归一化单位已经不同。

因此不同 tokenizer 的 PPL 通常不能直接横向比较。

---

## 2.3 Teacher Forcing 是什么？ `[P0]`

### 30～60 秒回答

Teacher Forcing 指训练自回归模型时，每个位置的输入前缀使用真实历史 token，而不是使用模型自己前一步采样出来的 token。

例如真实序列：

```text
A B C D
```

训练时：

```text
A       → predict B
A B     → predict C
A B C   → predict D
```

即使模型预测 B 错了，训练下一位置时仍然使用真实的：

```text
A B
```

而不是错误预测。

### 为什么这么做？

第一，可以并行训练。

通过 causal mask，一次 forward 就可以同时计算：

```text
A       → B
A B     → C
A B C   → D
```

第二，监督信号稳定。

否则模型早期预测很差，错误会不断污染后续输入。

---

### Train–Inference Mismatch

训练：

```text
history = ground truth
```

推理：

```text
history = model-generated tokens
```

因此存在 exposure bias：

> 推理时模型可能进入训练数据中很少见的错误前缀状态。

这也是为什么：

* sequence-level training；
* RL；
* on-policy rollout；

能够提供 SFT 不具备的训练信号。

---

### 和 RL 的接口

SFT：

```text
ground-truth prefix
→ predict target
```

Agent RL：

```text
model-generated action
→ environment observation
→ model-generated next action
```

后者真正经历自己的行为产生的状态分布。

---

## 2.4 为什么 Causal LM 的 logits 和 labels 要 shift？ `[P0]`

假设输入：

```text
[BOS, I, like, cats]
```

模型位置 \(t\) 的 hidden state 只能看到：

$$
x_{\le t}
$$

因此它应该预测：

$$
x_{t+1}
$$

对应：

```text
input position     target

BOS                I
I                  like
like               cats
cats               EOS
```

于是：

```python
shift_logits = logits[:, :-1, :]
shift_labels = labels[:, 1:]
```

概念上：

$$
\operatorname{logits}[t]
$$

对齐：

$$
\operatorname{label}[t+1]
$$

---

### 为什么不是 logits[t] 对 label[t]？

如果：

```text
position t
已经输入 token x_t
```

却让模型预测：

```text
x_t
```

那它已经“看到了答案”。

真正语言模型任务是：

$$
p(x_{t+1}|x_{\le t})
$$

而不是：

$$
p(x_t|x_{\le t})
$$

---

### Hugging Face 为什么有时看不到手工 shift？

有些模型实现内部会自动 shift。

所以工程上必须确认：

> shift 由谁负责？

否则最危险的情况是：

```text
caller shift 一次
+
model 内部又 shift 一次
```

造成 off-by-one。

---

### Debug 典型错误

如果 label alignment 错一位：

```text
模型仍然可能产生有限 loss
```

并不一定立即报错。

但训练目标已经完全变了。

因此：

> shape 正确不等于 semantic alignment 正确。

---

## 2.5 Attention Mask、Padding Mask、Label Mask、Loss Mask 有什么区别？ `[P0]`

这是后面 Agent RL 最容易混淆的基础之一。

---

### Attention Mask

回答：

> 当前 token 能看到哪些 context tokens？

例如 causal attention：

```text
token 3
可以看到 0,1,2,3
不能看到 4,5,...
```

它影响 forward computation。

---

### Padding Mask

batch 中不同 sequence 长度不同：

```text
sample A: A B C D
sample B: X Y PAD PAD
```

padding token 不应该参与有效 attention。

因此 padding mask 控制：

```text
哪些 positions 是真实输入
```

---

### Label Mask / Loss Mask

回答：

> 哪些 token 应该贡献训练 loss？

例如 instruction SFT：

```text
<user>
Explain PPO
</user>

<assistant>
PPO is ...
</assistant>
```

可能只让 assistant tokens：

```text
PPO is ...
```

进入 loss。

user tokens：

```text
Explain PPO
```

仍然是 context，但：

$$
m_t=0
$$

不计算 loss。

---

### 三者最关键区别

一个 token 可以：

```text
存在于 context
能被后续 token attention
但自己不贡献 loss
```

这在：

```text
prompt
tool observation
system message
```

中非常常见。

因此：

```text
attention-visible
≠
loss-bearing
```

---

### RL 中进一步会出现 Response Mask

以后会看到：

```text
response mask
```

它回答：

> 哪些 token 是当前 policy 真正生成、需要参加 policy loss 的 action tokens？

这和普通 SFT loss mask 语义相似，但来源更严格。

---

## 2.6 Adam 和 AdamW 有什么区别？ `[P0]`

### Adam

Adam 为每个参数维护一阶矩估计：

$$
m_t
=
\beta_1m_{t-1}
+
(1-\beta_1)g_t
$$

二阶矩估计：

$$
v_t
=
\beta_2v_{t-1}
+
(1-\beta_2)g_t^2
$$

bias correction：

$$
\hat m_t
=
\frac{m_t}{1-\beta_1^t}
$$

$$
\hat v_t
=
\frac{v_t}{1-\beta_2^t}
$$

更新：

$$
\theta_{t+1}
=
\theta_t
-
\eta
\frac{\hat m_t}
{\sqrt{\hat v_t}+\epsilon}
$$

Adam 的特点是：

> 不同参数根据历史 gradient scale 得到不同 adaptive step size。

---

### AdamW

AdamW 将 weight decay 与 gradient update 解耦：

$$
\theta_{t+1}
=
(1-\eta\lambda)\theta_t
-
\eta
\frac{\hat m_t}
{\sqrt{\hat v_t}+\epsilon}
$$

也就是：

```text
Adam adaptive update
+
independent parameter shrinkage
```

---

### 为什么现在大模型训练通常说 AdamW？

因为对 adaptive optimizer 来说：

> 把 \(L_2\) regularization 直接塞进 gradient

和：

> 独立做 weight decay

不再严格等价。

这在 2.10 会继续推。

---

### 实践追问

是不是所有 parameter 都 weight decay？

通常不是。

常见 recipe 会排除：

* bias；
* normalization parameters。

但具体策略依实现而定。

---

## 2.7 Batch、Micro Batch、Gradient Accumulation、Global Batch 怎么区分？ `[P0]`

### Micro Batch

单个 device 一次 forward/backward 实际处理：

$$
B_{\text{micro}}
$$

个样本。

---

### Gradient Accumulation

如果连续做：

$$
A
$$

次 micro batch backward，但不立即 optimizer.step：

```text
microbatch 1 → backward
microbatch 2 → backward
microbatch 3 → backward
microbatch 4 → backward
                  ↓
             optimizer.step
```

相当于积累更大的 effective batch。

---

### Data Parallel World Size

假设有：

$$
D
$$

个 data-parallel workers。

则常见 global batch：

$$
B_{\text{global}}
=
B_{\text{micro}}
\times
A
\times
D
$$

如果每个样本本身包含多个 sequences，还要注意框架如何定义 batch unit。

---

### 示例

```text
micro batch per GPU = 2
gradient accumulation = 8
GPUs = 16
```

则：

$$
B_{\text{global}}
=
2\times8\times16
=
256
$$

---

### 为什么 Gradient Accumulation 有用？

因为显存只能容纳：

```text
micro batch = 2
```

但优化希望近似：

```text
global batch = 256
```

于是用时间换显存。

---

### 它和真正一次 batch=256 完全一样吗？

不一定。

可能存在差异：

* BatchNorm 类操作；
* dropout RNG；
* gradient clipping 时机；
* mixed-precision scaling；
* optimizer / scheduler step 定义；
* sequence-length dynamic batching。

LLM 常用 LayerNorm/RMSNorm，所以 BatchNorm 不是主要问题，但其他差异仍然存在。

---

## 2.8 FP32、FP16、BF16、FP8 分别是什么？ `[P0]`

### FP32

通常：

```text
1 sign
8 exponent
23 mantissa
```

数值范围和精度都较高，但：

* 显存大；
* bandwidth 大；
* tensor core throughput 不一定最优。

---

### FP16

通常：

```text
1 sign
5 exponent
10 mantissa
```

精度较高，但 exponent 范围明显小于 FP32。

训练中容易：

```text
overflow
underflow
```

因此经典 FP16 training 经常需要 loss scaling。

---

### BF16

```text
1 sign
8 exponent
7 mantissa
```

它保留与 FP32 相同数量的 exponent bits，因此数值范围接近 FP32，但 mantissa 更短。

优势：

> 对深度学习训练来说，通常比 FP16 更不容易 overflow。

因此现代 LLM 训练大量采用 BF16。

---

### FP8

FP8 有不同格式，例如概念上常见：

```text
E4M3
E5M2
```

分别在：

```text
precision
vs
range
```

之间取舍。

FP8 可以进一步：

* 减少显存；
* 减少 bandwidth；
* 提高 tensor core throughput。

但需要更复杂的：

```text
scaling
amax tracking
casting policy
```

---

### 混合精度是什么意思？

不是所有东西都统一一种 dtype。

可能出现：

```text
parameters      BF16
matmul          BF16 / FP8
accumulation    FP32
optimizer state FP32
```

因此：

> BF16 training

不等于整个训练过程所有 tensor 都是 BF16。

---

## 2.9 SFT 到底训练什么？为什么经常只训练 assistant tokens？ `[P0]`

### SFT

Supervised Fine-Tuning 本质仍然是 causal LM maximum likelihood。

区别是训练数据变成 instruction / conversation：

```text
system
user
assistant
```

例如：

```text
User:
什么是 GRPO？

Assistant:
GRPO 是一种...
```

模型被训练：

> 在给定 instruction/context 后生成目标 assistant response。

---

### 为什么经常只对 assistant token 计算 loss？

因为训练目标不是：

> 让模型重新生成 user 的问题。

而是：

> 条件于 user 输入生成 assistant response。

序列：

```text
[system][user][assistant]
```

全部都会进入 context。

但 loss mask：

```text
system     0
user       0
assistant  1
```

于是：

$$
\mathcal L
=
-
\frac{
\sum_t
m_t
\log p_\theta(y_t|x_{<t})
}{
\sum_t m_t
}
$$

---

### 为什么不能把 masked token 从 input 删掉？

因为 user/system token 虽然：

```text
loss = 0
```

但仍然是生成 assistant response 的条件。

所以：

```text
not trained as target
≠
not visible as context
```

---

### Multi-turn SFT

例如：

```text
user 1
assistant 1
user 2
assistant 2
```

有两种常见设计：

#### 所有 assistant turns 都计算 loss

```text
user1       0
assistant1  1
user2       0
assistant2  1
```

#### 只训练最后一轮

```text
user1       0
assistant1  0
user2       0
assistant2  1
```

具体取决于数据和训练目标。

---

# P1

## 2.10 Weight Decay 为什么不等价于 Adam 中直接加 L2？ `[P1]`

对 SGD 来说，如果 objective 加：

$$
\frac{\lambda}{2}\|\theta\|^2
$$

gradient：

$$
g'
=
g+\lambda\theta
$$

SGD 更新：

$$
\theta'
=
\theta-\eta(g+\lambda\theta)
$$

可以整理：

$$
\theta'
=
(1-\eta\lambda)\theta-\eta g
$$

所以和 multiplicative weight decay 等价。

---

### 但 Adam 不一样

如果把：

$$
\lambda\theta
$$

加入 gradient：

$$
g'=g+\lambda\theta
$$

它还会进入：

$$
m_t
$$

和：

$$
v_t
$$

随后受到 adaptive normalization：

$$
\frac{\hat m_t}
{\sqrt{\hat v_t}+\epsilon}
$$

因此 regularization term 也被 Adam 的 adaptive scaling 改变。

这不再等价于：

$$
-\eta\lambda\theta
$$

这种独立 shrinkage。

---

### AdamW

AdamW 直接：

$$
\theta'
=
\theta
-
\eta\operatorname{AdamUpdate}(g)
-
\eta\lambda\theta
$$

把：

```text
gradient optimization
```

与：

```text
weight decay
```

分开。

---

### 面试一句话

> SGD 下 L2 regularization 与 weight decay 可以等价，但 adaptive optimizer 会重新缩放加入 gradient 的 L2 项，因此 AdamW 显式 decouple weight decay。

---

## 2.11 Learning Rate Warmup 和 Cosine Decay 为什么常见？ `[P1]`

### Warmup

训练刚开始时：

* optimizer moments 尚未稳定；
* hidden / gradient scale 还在适应；
* 大 learning rate 容易造成不稳定。

因此先从较小 LR 增长：

$$
\eta_t
=
\eta_{\max}
\frac{t}{T_{\text{warmup}}}
$$

直到达到 peak LR。

---

### 为什么大 batch 更常关注 warmup？

更大的 global batch 往往允许/要求不同 LR scaling，但训练初期如果直接给很大 LR，参数更新容易过猛。

---

### Cosine Decay

一种典型形式：

$$
\eta_t
=
\eta_{\min}
+
\frac{1}{2}
(\eta_{\max}-\eta_{\min})
\left[
1+
\cos
\left(
\pi
\frac{t-T_w}
{T-T_w}
\right)
\right]
$$

大致：

```text
LR

│     /─────────\
│    /           \
│   /             \
│  /                \
│ /                   \
└──────────────────────── step
   warmup      cosine decay
```

训练早期：

```text
较大学习率
→ 快速学习
```

训练后期：

```text
较小学习率
→ 更细致收敛
```

---

### 为什么不是必须 cosine？

不是。

还可能有：

* constant；
* linear decay；
* inverse sqrt；
* WSD 等。

关键是理解：

> scheduler 是 optimization policy，不是固定定律。

---

## 2.12 Gradient Clipping 在防什么？ `[P1]`

### Gradient Explosion

如果 gradient norm 突然非常大：

$$
\|g\|_2\gg1
$$

一次 optimizer update 可能造成巨大 parameter jump。

Gradient clipping 常用 global norm：

如果：

$$
\|g\|_2>C
$$

则：

$$
g
\leftarrow
g
\frac{C}{\|g\|_2}
$$

这样：

$$
\|g\|_2=C
$$

---

### PyTorch

```python
torch.nn.utils.clip_grad_norm_(
    model.parameters(),
    max_norm=1.0,
)
```

---

### 为什么 clip norm 比逐元素 clip 常见？

逐元素：

```text
g_i ∈ [-c, c]
```

会改变 gradient direction 更明显。

global norm clipping：

```text
整条 gradient vector 同比例缩放
```

更好地保留方向。

---

### 它是不是解决 NaN 的万能方法？

不是。

NaN 可能来自：

* overflow；
* invalid operation；
* bad logits；
* softmax instability；
* loss scaling；
* corrupted data；
* optimizer state；
* exploding activation。

Gradient clipping 只能处理其中一类：

> gradient magnitude 过大。

---

### clip 在 accumulation 前还是后？

通常希望：

```text
所有 microbatches gradient accumulate
↓
unscale
↓
clip
↓
optimizer.step
```

尤其 mixed precision 下，要确认 clipping 操作看到的是 unscaled gradient。

---

## 2.13 Chat Template 为什么会影响训练正确性？ `[P1]`

对 chat model 来说，用户看到：

```text
user: Hello
assistant: Hi
```

模型真正输入可能是：

```text
<|begin_of_text|>
<|system|>
...
<|user|>
Hello
<|assistant|>
Hi
<|eot_id|>
```

或者完全不同的序列。

---

### Chat Template 决定什么？

它决定：

* role marker；
* BOS/EOS；
* turn separator；
* assistant prefix；
* tool message formatting；
* generation prompt；
* special tokens。

因此最终：

$$
\text{conversation}
\rightarrow
\text{exact token IDs}
$$

取决于 template。

---

### Training–Inference Template Mismatch

训练：

```text
<user>hello</user>
<assistant>
```

推理：

```text
### User:
hello
### Assistant:
```

模型面对的是不同 token distribution。

可能导致：

* output quality 下降；
* role confusion；
* EOS 行为异常；
* tool calling 格式错误。

---

### Double Special Tokens

一个常见 bug：

```python
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False
)

tokens = tokenizer(
    text,
    add_special_tokens=True
)
```

如果 template 已经包含 BOS/EOS，而 tokenizer 又自动加一次：

```text
<BOS><BOS> ...
<EOS><EOS>
```

就会污染输入。

因此必须知道：

> template 与 tokenizer 各自负责哪些 special tokens。

---

### 后面 RL 为什么更敏感？

RL rollout 产生的 response IDs 必须与训练时重新构造的 prompt 完全一致。

如果：

```text
rollout template A
trainer template B
```

old logprob / current logprob 对齐就可能直接失效。

---

## 2.14 Padding、Packing、Sequence Packing 有什么区别？ `[P1]`

### Padding

样本：

```text
A length = 8
B length = 4
```

组成 batch：

```text
A: a a a a a a a a
B: b b b b PAD PAD PAD PAD
```

简单，但浪费：

```text
4 PAD tokens
```

---

### Dynamic Padding

每个 batch pad 到本 batch 最大长度，而不是全局 max length。

可以减少浪费。

---

### Packing

把多个短样本拼进一个固定长度 container：

```text
sample A: 100 tokens
sample B: 200 tokens
sample C: 300 tokens
```

可以拼成：

```text
[A][B][C][PAD...]
```

减少 padding。

---

### Sequence Packing 的真正难点

如果直接 concat：

```text
[A][B]
```

并使用普通 causal mask：

B 中 token 可以看到 A：

```text
A A A | B B B
✓ ✓ ✓   ← B 可以 attention A
```

这会造成：

> unrelated sample contamination。

正确 packing 可能需要 block-diagonal causal attention：

```text
Sample A:
✓ ✓ ✓
✓ ✓ ✓
✓ ✓ ✓

Sample B:
        ✓ ✓ ✓
        ✓ ✓ ✓
        ✓ ✓ ✓
```

即 B 不能读取 A。

---

### 为什么很多实现仍然直接 concat 文档？

因为对于 pretraining continuous text，文档 boundary 的处理策略可能不同。

但 instruction / independent examples 场景下：

> 是否允许跨样本 attention

必须明确设计，不能默认无所谓。

---

## 2.15 LoRA 的低秩假设是什么？ `[P1]`

### Full Fine-Tuning

原权重：

$$
W_0
\in
\mathbb R^{d_{out}\times d_{in}}
$$

直接训练：

$$
W
=
W_0+\Delta W
$$

其中：

$$
\Delta W
$$

和原矩阵一样大。

---

### LoRA

假设 adaptation 所需的有效更新：

$$
\Delta W
$$

可以近似为低秩：

$$
\Delta W
=
BA
$$

其中：

$$
A
\in
\mathbb R^{r\times d_{in}}
$$

$$
B
\in
\mathbb R^{d_{out}\times r}
$$

且：

$$
r\ll
\min(d_{in},d_{out})
$$

forward：

$$
y
=
W_0x
+
\frac{\alpha}{r}BAx
$$

---

### 参数量

Full update：

$$
d_{out}d_{in}
$$

LoRA：

$$
r(d_{in}+d_{out})
$$

例如：

$$
d_{in}=d_{out}=4096
$$

full matrix：

$$
4096^2
\approx16.8M
$$

LoRA \(r=16\)：

$$
16(4096+4096)
=
131072
$$

只有约：

$$
0.78\%
$$

的参数规模。

---

### LoRA 真正省什么？

主要省：

* trainable parameter gradients；
* optimizer states；
* checkpoint；
* fine-tuning storage。

但 base model forward 仍然存在，所以：

> LoRA 不会让原模型计算量凭空消失。

---

### 低秩假设是什么？

不是：

> 原权重 W 是低秩。

而是：

> 针对特定 downstream adaptation，需要学习的 parameter update \(\Delta W\) 可能具有较低 intrinsic rank。

---

## 2.16 QLoRA 为什么能显著降低显存？ `[P1]`

QLoRA 可以粗略理解：

```text
quantized frozen base model
+
trainable LoRA adapters
```

Base model 权重不再以 BF16/FP16 完整存储，而使用低 bit quantization。

例如概念上：

```text
16-bit base
↓
4-bit base
```

仅 base weight storage 理想情况下可下降约：

$$
4\times
$$

---

### Forward 怎么算？

量化权重：

```text
4-bit stored weights
      ↓
dequantize / quantized kernel
      ↓
higher precision compute
```

LoRA 参数仍通常保持更高 precision 训练。

---

### 为什么 optimizer state 也少很多？

因为 base parameters：

```text
frozen
```

没有：

* gradients；
* Adam first moment；
* Adam second moment。

只有 LoRA parameters 需要 optimizer states。

---

### QLoRA 不等于普通 INT4 inference

差别是：

```text
QLoRA
= quantized base for training
+ trainable adapters
```

不是单纯：

```text
把整个模型变 INT4 然后不训练
```

---

### 主要代价

可能包括：

* quantization error；
* dequantization overhead；
* kernel compatibility；
* adapter capacity 限制。

---

## 2.17 Activation Checkpointing 为什么用计算换显存？ `[P1]`

### 普通 Backprop

forward 过程中会保存大量 activation：

```text
layer 1 activations
layer 2 activations
layer 3 activations
...
```

backward 需要这些中间值计算 gradient。

因此深模型 activation memory 很大。

---

### Activation Checkpointing

只保存部分 checkpoint activations：

```text
Layer 0    save
Layer 1    discard
Layer 2    discard
Layer 3    save
Layer 4    discard
Layer 5    discard
Layer 6    save
```

Backward 时：

```text
从最近 checkpoint
重新执行部分 forward
↓
恢复 activation
↓
计算 gradient
```

所以：

```text
memory ↓
compute ↑
```

---

### 为什么训练特别需要？

训练显存包括：

```text
parameters
gradients
optimizer states
activations
temporary buffers
```

长 sequence / 大 batch 时 activation 可能成为主要瓶颈之一。

Checkpointing 可以换取更大的：

* sequence length；
* micro batch；
* model size。

---

### 它会影响结果吗？

理论上如果 recomputation 完全一致：

> 数学结果应相同。

但实践可能受：

* dropout RNG；
* non-deterministic kernel；
* stateful operation；

影响，因此框架需要正确管理 RNG state。

---

## 2.18 为什么固定 seed 也不一定完全复现？ `[P1]`

很多人会回答：

> 设置 `torch.manual_seed(42)` 就可以复现。

不够。

---

### Randomness 来源

至少包括：

```text
Python random
NumPy RNG
PyTorch CPU RNG
CUDA RNG
data sampler
dropout
generation sampling
distributed workers
```

---

### GPU 非确定性

某些 CUDA kernel：

* reduction order；
* atomic operations；
* parallel scheduling；

可能不是 bitwise deterministic。

浮点运算本身也不满足严格结合律：

$$
(a+b)+c
\neq
a+(b+c)
$$

在有限精度下顺序变化就可能产生小差异。

---

### Distributed Training

多个 rank：

```text
communication order
AllReduce timing
data order
worker scheduling
```

也可能导致 divergence。

小浮点差异经过数千 step 可能逐渐扩大。

---

### 真正 reproducibility 需要记录

```text
seed
model checkpoint
optimizer state
scheduler state
dataset version
sampler state
tokenizer
chat template
world size
framework version
CUDA
cuDNN
NCCL
code commit
```

所以：

> seed 是 reproducibility 的必要条件之一，不是充分条件。

---

# P2

## 2.19 Full Fine-Tuning、LoRA、QLoRA 怎么选择？ `[P2]`

这不是：

> 哪个最好？

而是 resource / adaptation / deployment trade-off。

---

### Full Fine-Tuning

训练全部参数。

#### 优点

* 最大参数自由度；
* 不受低秩 adapter 限制；
* 大规模 domain adaptation / continued pretraining 更自然。

#### 缺点

* gradients 大；
* optimizer states 大；
* checkpoint 大；
* distributed training 成本高。

适合：

```text
足够算力
大量高质量数据
需要显著改变模型能力/分布
```

---

### LoRA

冻结 base，训练 adapter。

#### 优点

* optimizer memory 很小；
* adapter checkpoint 小；
* 多任务部署方便；
* 训练门槛低。

#### 缺点

* update capacity 受 rank / target module 限制；
* base model 仍占完整 weight memory；
* 某些大幅能力迁移可能逊于 full FT。

适合：

```text
中小规模 SFT
任务 adaptation
多 adapter 管理
有限 GPU
```

---

### QLoRA

量化 frozen base + LoRA。

#### 优点

显存进一步下降。

#### 缺点

* quantization error；
* kernel constraints；
* training throughput 不一定同比提升。

适合：

```text
显存非常受限
仍希望训练较大的 base model
```

---

### 一个更完整的决策表

| 条件                          | 更倾向          |
| --------------------------- | ------------ |
| 算力充足，大量训练数据                 | Full FT      |
| 任务 adaptation，预算有限          | LoRA         |
| 显存尤其紧张                      | QLoRA        |
| 需要部署几十个任务 adapter           | LoRA         |
| 需要大规模 continued pretraining | Full FT      |
| 只有单卡消费级 GPU                 | QLoRA / LoRA |

---

### RL 是否也可以 LoRA？

可以。

但需要额外考虑：

```text
policy adapter
reference policy
rollout engine
weight sync
```

以及 rollout backend 是否支持高效 adapter reload。

这是后面 Macro 10 的问题。

---

## 2.20 一个训练过程出现 NaN / Inf，应该怎样系统排查？ `[P2]`

这是典型 Debug 题。

不要回答：

> 降低 learning rate。

应该逐层定位。

---

### Step 1：先定位 NaN 第一次出现在哪里

检查：

```text
input
↓
embedding
↓
hidden states
↓
logits
↓
loss
↓
gradients
↓
optimizer state
↓
parameters
```

目标是找到：

> first bad tensor。

而不是只看最后 loss。

---

### Step 2：检查数据

例如：

```text
invalid token id
all labels ignored
空 sequence
极端长 sequence
错误 mask
NaN reward
Inf advantage
```

虽然这是 SFT 章，但后面 RL 的 reward NaN 同样适用。

---

### Step 3：检查 Forward 数值

重点：

```text
activation max/min
logits max
softmax
normalization denominator
```

例如错误实现：

$$
e^{1000}
$$

很容易 overflow。

标准 fused log-softmax 通常会使用：

$$
z_i-\max(z)
$$

保证稳定。

---

### Step 4：Mixed Precision

FP16 特别检查：

```text
loss scale
overflow
underflow
gradient unscale
```

BF16 range 更大，但仍然不代表不会 NaN。

---

### Step 5：Gradient

记录：

$$
\|g\|_2
$$

如果：

```text
1
2
4
10
100
10000
Inf
```

很可能发生 gradient explosion。

检查：

* learning rate；
* clipping；
* data；
* initialization。

---

### Step 6：Optimizer State

Adam：

$$
m_t,\quad v_t
$$

如果：

```text
v_t NaN
```

之后所有 step 都可能污染。

resume checkpoint 也可能带入坏 optimizer state。

---

### Step 7：定位第一个坏 step

保存：

```text
step
batch id
sample IDs
learning rate
grad norm
loss
logit range
```

如果总在同一 batch 爆：

> 更可能是 data-dependent。

如果随机爆：

> 可能是 numerical / distributed / stochastic 问题。

---

### 一个可背的排查顺序

```text
NaN
 ↓
Data?
 ↓
Forward activation?
 ↓
Loss?
 ↓
Precision / scaler?
 ↓
Gradient norm?
 ↓
Optimizer state?
 ↓
Distributed communication?
 ↓
Exact offending batch?
```

---

### 不要做什么

看到 NaN 就立刻：

```text
lr /= 10
```

可能暂时掩盖真正 bug，例如：

```text
label 对齐错误
非法 mask
除 0
错误 tokenizer
```

---

## 2.21 怎样估算 LLM 训练显存？ `[P2]`

训练显存至少拆成：

$$
M_{\text{total}}
=
M_{\text{param}}
+
M_{\text{grad}}
+
M_{\text{optimizer}}
+
M_{\text{activation}}
+
M_{\text{temporary}}
$$

不能只算参数。

---

### 参数

假设：

$$
N
$$

个参数。

BF16：

$$
2N\text{ bytes}
$$

7B 模型：

$$
7\times10^9\times2
\approx14\text{ GB}
$$

仅模型权重约 14GB。

---

### Gradient

如果 BF16 gradient：

$$
2N
$$

又约：

$$
14\text{ GB}
$$

如果 FP32 gradient 则更大。

---

### Adam State

Adam 通常维护：

```text
m
v
```

如果各 FP32：

$$
4N+4N
=
8N
$$

7B：

$$
56\text{ GB}
$$

还没算 master weights。

---

### FP32 Master Weights

一些 mixed precision recipe 会维护 FP32 master copy：

$$
4N
$$

7B：

$$
28\text{ GB}
$$

---

### 一个经典粗略估算

某些训练配置可接近：

```text
parameters       2 bytes
gradients        2 bytes
master weights   4 bytes
Adam m           4 bytes
Adam v           4 bytes
─────────────────────────
≈16 bytes / parameter
```

于是：

$$
7B\times16
\approx112\text{ GB}
$$

还没有 activation。

注意：

> 16 bytes/parameter 是特定训练配置下的粗略经验，不是普适常数。

---

### Activation

Activation 与：

```text
batch
sequence length
hidden size
layers
```

高度相关。

可以粗略理解：

$$
M_{\text{act}}
\propto
B\times T\times d\times L
$$

再乘上不同 intermediate tensors。

Attention 的 naïve intermediate 还可能包含：

$$
T^2
$$

项。

---

### 为什么 ZeRO/FSDP 有用？

因为：

```text
parameters
gradients
optimizer states
```

可以跨 devices shard。

后面 Macro 10 会系统展开。

---

### 为什么 LoRA 特别省 optimizer memory？

如果只有：

$$
N_{\text{LoRA}}
\ll
N_{\text{base}}
$$

个 trainable parameters：

```text
gradients
optimizer states
```

只需要为 LoRA 保存。

Base weights 只做 forward。

---

## 2.22 Sequence Packing 为什么可能产生样本污染？ `[P2]`

假设两个完全独立样本：

```text
Sample A:
Question: Paris is in?
Answer: France

Sample B:
Question: Tokyo is in?
Answer: Japan
```

直接 concat：

```text
[A tokens][B tokens]
```

普通 causal mask 允许 B 看到前面的 A。

模型实际学习：

$$
p(B|A)
$$

而本来希望：

$$
p(B)
$$

或者：

$$
p(B_{\text{answer}}|B_{\text{prompt}})
$$

---

### 为什么这是 contamination？

因为 Sample A 并不是 Sample B 的真实 context。

如果两个数据独立，模型被人为暴露于：

```text
unrelated previous conversation
```

中。

---

### Block-Diagonal Attention

理想上：

```text
A token:
只能看 A

B token:
只能看 B
```

attention mask：

```text
AAA BBB

A:
111 000
111 000
111 000

B:
000 100
000 110
000 111
```

每个 sample 内 causal，但不能跨 sample。

---

### Position ID 怎么办？

如果 packing：

```text
A length 100
B length 200
```

B 可以：

#### 方案一

继续 position：

```text
100,101,...
```

#### 方案二

重新从 0：

```text
0,1,2,...
```

不同模型 / kernel / packing implementation 有不同要求。

如果 position 处理错：

> 即使 attention mask 正确也可能出现 distribution mismatch。

---

### Loss Mask

还需要同时正确处理：

```text
sample boundaries
assistant-only loss
padding
```

所以 packing 不是：

```python
torch.cat(samples)
```

这么简单。

---

### 为什么 Pretraining 有时允许 document concat？

在大规模 pretraining 中，工程上可能把文档串接成 token stream，提高 utilization。

此时模型会看到 document boundary。

是否允许跨文档 attention 是 recipe 的一部分。

但 instruction tuning / agent trajectory 中：

> 不同样本是否互相可见

通常需要更加严格。

---

## 2.23 为什么训练 loss 下降不代表模型真的变好了？ `[P2]`

这是算法岗非常基础但经常被忽略的实验问题。

---

### 情况一：Overfitting

```text
train loss ↓↓↓
validation loss ↑
```

模型只是记住训练数据。

---

### 情况二：Data Leakage

如果 validation/test 内容泄漏到训练：

```text
loss 很漂亮
benchmark 很漂亮
```

但结论无效。

---

### 情况三：Objective 与真实任务不一致

例如 SFT 优化：

$$
\text{token NLL}
$$

但我们真正关心：

```text
exact answer accuracy
reasoning correctness
tool use
citation quality
```

更低 token loss 不保证这些指标单调提高。

---

### 情况四：Loss Reduction 被长度分布主导

如果大量容易的长文本 token：

```text
占据 loss denominator
```

模型可能在这些 token 上提升很多，而关键困难样本没有改善。

所以需要切分：

```text
per-domain
per-length
per-difficulty
```

指标。

---

### 情况五：Formatting Shortcut

Instruction SFT 中模型可能学会：

```text
漂亮格式
高频套话
固定模板
```

token likelihood 提高，但事实能力没提高。

---

### 情况六：Catastrophic Forgetting

Fine-tuning dataset 很窄：

```text
domain task ↑
general ability ↓
```

训练 loss 仍然一直下降。

---

### 所以需要什么？

至少同时看：

```text
training objective
validation loss
task metric
held-out benchmark
behavioral eval
failure slice
```

后面 Agent RL 还会进一步加入：

```text
reward
pass@1
pass@k
tool success
search cost
trajectory quality
```

因此必须形成习惯：

> Optimization metric 不等于最终 evaluation metric。

---

# 2.24 Macro 2 高频连环追问

## 第一组：Language Modeling

```text
CLM objective 是什么？
↓
为什么等价于 NLL？
↓
CE 为什么可以直接吃 logits？
↓
为什么 logits/label 要 shift？
↓
Teacher Forcing 是什么？
↓
为什么训练能一次并行算所有 position？
↓
为什么 inference 不能这样？
```

---

## 第二组：Mask

```text
Causal mask 是什么？
↓
Padding mask 是什么？
↓
Loss mask 是什么？
↓
为什么 prompt token 能作为 context 却不计算 loss？
↓
assistant-only loss 怎么实现？
↓
tool observation 后面是否也能用相同思想 zero-loss？
```

最后一问只需要理解机制，Agent RL 的严格定义留到 Macro 5。

---

## 第三组：Optimization

```text
Adam 怎么工作？
↓
m 和 v 是什么？
↓
为什么 bias correction？
↓
AdamW 和 Adam 区别？
↓
为什么 L2 != AdamW weight decay？
↓
Warmup 为什么需要？
↓
Gradient clipping 在哪一步做？
```

---

## 第四组：Batch

```text
micro batch 是什么？
↓
gradient accumulation 是什么？
↓
global batch 怎么算？
↓
增加 global batch 为什么不只是“显存问题”？
↓
scheduler 的 step 按 microbatch 还是 optimizer step？
```

最后一题答案必须看实现。

---

## 第五组：Precision

```text
FP16 和 BF16 区别？
↓
为什么 BF16 range 更大？
↓
为什么 FP16 常需要 loss scaling？
↓
FP8 有什么 trade-off？
↓
mixed precision 为什么不是全模型一种 dtype？
```

---

## 第六组：PEFT

```text
LoRA 做什么？
↓
低秩的到底是谁？
↓
为什么省显存？
↓
为什么不同比例减少 forward FLOPs？
↓
QLoRA 又多做了什么？
↓
什么时候 full FT 更合适？
```

---

# 2.25 Self-test

## Self-test 1：Causal Shift

给：

```text
tokens:
[10, 20, 30, 40]
```

模型 logits shape：

$$
[4,V]
$$

应该用：

```text
logits[0] → target 20
logits[1] → target 30
logits[2] → target 40
```

如果还有 EOS：

```text
logits[3] → EOS
```

---

## Self-test 2：Assistant Loss Mask

序列：

```text
<SYS>
You are helpful
<USER>
2+2?
<ASSISTANT>
4
<EOS>
```

如果只训练 assistant response，概念上：

```text
SYS tokens         mask = 0
USER tokens        mask = 0
ASSISTANT "4"      mask = 1
EOS                视 recipe 决定
```

但 SYS / USER 仍然保留在 attention context。

---

## Self-test 3：Global Batch

```text
micro batch = 4
gradient accumulation = 16
data parallel workers = 8
```

则：

$$
B_{\text{global}}
=
4\times16\times8
=
512
$$

---

## Self-test 4：LoRA 参数量

假设：

$$
W\in\mathbb R^{4096\times4096}
$$

LoRA rank：

$$
r=8
$$

Full matrix：

$$
4096^2
=
16,777,216
$$

LoRA：

$$
8(4096+4096)
=
65,536
$$

仅约：

$$
0.39\%
$$

---

## Self-test 5：PPL

如果 validation average NLL：

$$
2.0
$$

则：

$$
PPL=e^2\approx7.39
$$

---

# 2.26 推导题

## 推导题 1：CE 与 NLL

从：

$$
H(q,p)
=
-\sum_iq_i\log p_i
$$

若：

$$
q_y=1
$$

其他：

$$
q_i=0
$$

推导：

$$
H(q,p)
=
-\log p_y
$$

即分类 Cross Entropy 等于真实 class 的 NLL。

---

## 推导题 2：Weight Decay

解释为什么 SGD：

$$
g+\lambda\theta
$$

可以整理成：

$$
(1-\eta\lambda)\theta-\eta g
$$

而 Adam 中：

$$
g+\lambda\theta
$$

会先进入 adaptive moments，因此不再等价于独立 shrinkage。

---

## 推导题 3：Global Batch

假设：

$$
B_\mu
$$

是每卡 micro batch，

$$
A
$$

是 accumulation，

$$
D
$$

是 DP world size。

则每 optimizer step 消耗样本：

$$
B_{\text{global}}
=
B_\mu AD
$$

如果训练总样本数：

$$
N
$$

则每 epoch optimizer step 约：

$$
\frac{N}{B_\mu AD}
$$

---

## 推导题 4：LoRA 参数量

Full matrix：

$$
d_{out}d_{in}
$$

LoRA：

$$
r(d_{in}+d_{out})
$$

参数比：

$$
\frac{
r(d_{in}+d_{out})
}{
d_{out}d_{in}
}
$$

如果：

$$
d_{in}=d_{out}=d
$$

则：

$$
\frac{2r}{d}
$$

当：

$$
r\ll d
$$

时显著减少。

---

# 2.27 Debug 题

## Debug 1：Loss 从第一步就是 NaN

优先检查：

```text
labels 是否非法
loss denominator 是否为 0
logits 是否 Inf
mixed precision overflow
input 中是否 NaN
mask 是否全部 ignore
```

而不是立即重训。

---

## Debug 2：训练 Loss 正常下降，但生成一直输出 prompt 本身

重点排查：

```text
label shift
assistant loss mask
chat template
generation prompt
special tokens
EOS
```

尤其可能是：

> 实际训练目标错误地要求复制 user tokens。

---

## Debug 3：单卡训练正常，多卡训练发散

排查：

```text
global batch 是否变化
learning rate 是否跟着错误缩放
DDP gradient synchronization
loss normalization
gradient accumulation
data duplication
sampler
mixed precision
collective communication
```

---

## Debug 4：LoRA Loss 不降

检查：

```text
LoRA parameters.requires_grad
target_modules
optimizer 是否收到 adapter parameters
rank / alpha
learning rate
loss mask
quantization compatibility
```

第一步应该打印：

```text
trainable parameter names
```

而不是先调 rank。

---

## Debug 5：用了 Packing 后 loss 明显异常下降

可能不是好事。

检查：

```text
sample B 是否能 attention sample A
label mask 是否跨 boundary
position ids 是否正确
EOS boundary
重复数据
```

可能存在跨样本 leakage。

---

# 2.28 系统设计题

## 系统设计题 1：单张 24GB GPU 微调一个放不下完整 Adam 状态的模型怎么办？

从便宜到复杂可以讨论：

```text
reduce sequence length
↓
reduce micro batch
↓
gradient accumulation
↓
activation checkpointing
↓
BF16
↓
LoRA
↓
QLoRA
↓
optimizer offload / sharding
```

不是只有：

> 换更大 GPU。

---

## 系统设计题 2：为什么模型参数明明只有 14GB，24GB GPU 却无法 Full Fine-Tune？

因为：

```text
14GB
```

只是 model weights。

还需要：

```text
gradients
optimizer m
optimizer v
possibly master weights
activations
temporary buffers
CUDA context
```

训练显存远大于 inference model weight size。

---

## 系统设计题 3：训练速度突然下降 40%，但显存没变化，怎么看？

检查：

```text
sequence length distribution
padding ratio
packing efficiency
data loader
activation checkpointing
kernel fallback
mixed precision
gradient accumulation
GPU utilization
communication
CPU/GPU synchronization
```

不要只看 VRAM。

---

# 2.29 与后续 Macro 的接口

Macro 2 建立的：

```text
token IDs
↓
logits
↓
CE / NLL
↓
loss mask
↓
backward
↓
optimizer
```

到了 Macro 3–4 会变成：

```text
actions
↓
logprob
↓
reward
↓
advantage
↓
policy loss
↓
backward
↓
optimizer
```

注意其中大量组件没有变：

```text
tokenizer
chat template
model forward
logits
logprob
mask
autograd
optimizer
precision
distributed training
```

改变的是 loss construction。

---

# 2.30 Macro 2 最小知识图

最终应该形成下面这条训练链：

```text
Raw Conversation
       ↓
Chat Template
       ↓
Tokenizer
       ↓
Token IDs
       │
       ├─────────────┐
       │             │
Attention Mask   Loss Mask
       │             │
       └──────┬──────┘
              ↓
        Transformer
              ↓
            Logits
              ↓
         Shift Labels
              ↓
      Cross Entropy / NLL
              ↓
         Token Average
              ↓
            Loss
              ↓
          Backward
              ↓
          Gradients
              │
      ┌───────┴────────┐
      │                │
Gradient Clip    Accumulation
      │                │
      └───────┬────────┘
              ↓
            AdamW
              ↓
        Updated Weights
```

显存侧则形成：

```text
Training Memory
      │
      ├── Parameters
      ├── Gradients
      ├── Optimizer States
      ├── Activations
      └── Temporary Buffers
             │
             ├── Mixed Precision
             ├── Activation Checkpointing
             ├── LoRA / QLoRA
             └── 后续：FSDP / ZeRO
```

到这里应该能够回答：

> **一个 LLM 到底是怎样从 conversation 变成 gradient，再从 gradient 变成新参数的。**

Macro 3 接下来就可以把监督学习中的：

$$
-\log p_\theta(y|x)
$$

换成真正的 RL 问题：

$$
\max_\theta
\mathbb E_{\tau\sim\pi_\theta}
[R(\tau)]
$$

并从 MDP、Return、Value、Advantage、REINFORCE、Baseline、Importance Sampling 一路推到 PPO/GRPO。

## 3. Reinforcement Learning Fundamentals

这一章解决的是从监督学习：

$$
(x,y)
\rightarrow
-\log p_\theta(y|x)
$$

走向强化学习：

$$
\tau\sim\pi_\theta
\rightarrow
R(\tau)
\rightarrow
\nabla_\theta J(\theta)
$$

时到底发生了什么。

LLM 后训练里经常直接从 PPO / GRPO 开始讲，但这些算法建立在一组更基础的对象上：

```text
State
Action
Policy
Trajectory
Reward
Return
Value
Q
Advantage
Policy Gradient
Importance Sampling
```

如果这些东西没有真正连起来，就很容易出现：

```text
会背 PPO ratio
但不知道为什么需要 ratio

会背 advantage
但不知道 baseline 为什么不引入 bias

会背 on-policy
但不知道 rollout stale 到什么程度开始成为问题

会背 GRPO
但不知道 group normalization 本质上替代了什么
```

Macro 3 的目标不是把传统 RL 教科书全搬过来，而是建立后面 LLM RL 真正需要的最小理论闭环。

---

## 3.0 问题矩阵

| 编号   | 问题                                                       | 等级   |    |
| ---- | -------------------------------------------------------- | ---- | -- |
| 3.1  | MDP 的 State、Action、Transition、Reward 分别是什么？              | P0   |    |
| 3.2  | Episode、Trajectory、Horizon、Terminal State 怎么区分？          | P0   |    |
| 3.3  | Reward 和 Return 有什么区别？Discount Factor 有什么意义？             | P0   |    |
| 3.4  | \(V(s)\)、\(Q(s,a)\)、Advantage \(A(s,a)\) 有什么区别？          | P0   |    |
| 3.5  | Policy 是什么？Deterministic / Stochastic Policy 有什么区别？      | P0   |    |
| 3.6  | REINFORCE / Policy Gradient 的核心公式是什么？                    | P0   |    |
| 3.7  | 为什么 Policy Gradient 里出现 (\log \pi_\theta(a               | s))？ | P0 |
| 3.8  | 为什么要引入 Baseline？                                         | P0   |    |
| 3.9  | On-policy 与 Off-policy 有什么区别？                            | P0   |    |
| 3.10 | 为什么 action-independent baseline 不改变 Policy Gradient 的期望？ | P1   |    |
| 3.11 | Monte Carlo、TD、Bootstrap 分别是什么？                          | P1   |    |
| 3.12 | Bias–Variance Trade-off 在 RL 中怎么理解？                      | P1   |    |
| 3.13 | Importance Sampling 为什么可以做分布修正？                          | P1   |    |
| 3.14 | Importance Weight 为什么会高方差甚至爆炸？                           | P1   |    |
| 3.15 | GAE 是什么？为什么它能调节 bias / variance？                         | P1   |    |
| 3.16 | Entropy Regularization 在 RL 中做什么？                        | P1   |    |
| 3.17 | Reward Shaping 什么时候有帮助，什么时候会改坏目标？                        | P1   |    |
| 3.18 | Contextual Bandit 与 Sequential RL 有什么区别？                 | P1   |    |
| 3.19 | Credit Assignment 为什么会随 Horizon 增长迅速变难？                  | P1   |    |
| 3.20 | Policy Gradient Theorem 的核心推导是什么？                        | P2   |    |
| 3.21 | 长 Horizon 下 trajectory-level importance ratio 为什么容易失控？   | P2   |    |
| 3.22 | Entropy-Regularized RL 的 objective 应该怎样理解？               | P2   |    |
| 3.23 | TRPO 的 Trust Region 思想与 PPO 有什么关系？                       | P2   |    |
| 3.24 | Offline RL 最核心的 Distribution Shift 问题是什么？                | P2   |    |

---

# P0

## 3.1 MDP 的 State、Action、Transition、Reward 分别是什么？ `[P0]`

### 30～60 秒回答

Markov Decision Process 通常写成：

$$
(\mathcal S,\mathcal A,P,R,\gamma)
$$

其中：

* \(\mathcal S\)：State Space；
* \(\mathcal A\)：Action Space；
* \(P(s'|s,a)\)：Transition Dynamics；
* \(R(s,a,s')\)：Reward；
* \(\gamma\)：Discount Factor。

Agent 在状态：

$$
s_t
$$

根据 policy：

$$
\pi_\theta(a_t|s_t)
$$

选择 action：

$$
a_t
$$

环境转移：

$$
s_{t+1}
\sim
P(\cdot|s_t,a_t)
$$

并产生 reward：

$$
r_t
$$

整个过程：

```text
State s_t
   ↓ policy
Action a_t
   ↓ environment
Reward r_t
+
State s_{t+1}
```

---

### Markov Property 是什么？

理论 MDP 假设：

$$
P(s_{t+1}|s_0,a_0,\ldots,s_t,a_t)
=
P(s_{t+1}|s_t,a_t)
$$

即：

> 当前 state 已经包含预测未来所需的全部相关信息。

过去历史不再额外提供 transition information。

---

### LLM Agent 里 State 是什么？

不能机械回答：

> state 就是 prompt。

更合理地说，Agent state 可能包括：

```text
system instruction
conversation history
tool observations
workspace state
environment state
remaining budget
memory
```

但一个现实 Agent 往往并不能观察真实完整环境状态，因此严格说更接近：

```text
POMDP
```

即 Partially Observable MDP。

模型实际获得的是 observation：

$$
o_t
$$

而不一定是真正的：

$$
s_t
$$

---

### 易错点

不要把：

```text
State
Observation
```

无条件当成同一个东西。

经典 MDP 中 agent 可以直接观察 state。

实际 Agent：

```text
environment state
      ↓
observation
      ↓
LLM context
```

经常是部分可观察的。

---

## 3.2 Episode、Trajectory、Horizon、Terminal State 怎么区分？ `[P0]`

### Trajectory

一次交互序列：

$$
\tau
=
(s_0,a_0,r_0,s_1,a_1,r_1,\ldots,s_T)
$$

也可以简写：

$$
\tau=(s_0,a_0,\ldots,s_T)
$$

---

### Episode

Episode 通常指：

> 从一次环境 reset 开始，到 terminal / truncated condition 结束的一整次交互。

很多情况下：

```text
one episode
≈
one trajectory
```

但工程框架里术语未必完全一致。

所以要看框架的数据模型。

---

### Horizon

Horizon 是一次决策过程允许的时间长度。

有限 horizon：

$$
T<\infty
$$

例如 Agent 最多允许：

```text
10 tool calls
```

就是某种有限 horizon。

---

### Terminal

真正任务自然结束：

```text
answer produced
goal achieved
game over
```

---

### Truncation

外部规则强行停止：

```text
max steps
timeout
budget exceeded
worker cancelled
```

它不一定代表：

> 当前状态本身是自然终止状态。

这个区别后面处理 partial trajectory 时很重要。

---

### 典型 Agent

```text
Task
 ↓
Search
 ↓
Visit
 ↓
Search
 ↓
Answer
 ↓
Terminal
```

如果在第三步因为：

```text
max_steps = 3
```

停止，则更像 truncation。

---

## 3.3 Reward 和 Return 有什么区别？Discount Factor 有什么意义？ `[P0]`

### Reward

Reward：

$$
r_t
$$

是某一步或某个时刻的局部反馈。

例如：

```text
正确最终答案      +1
错误答案          0

或者

good tool step    +0.1
bad tool step     -0.1
```

---

### Return

Return 是从当前时刻开始累计未来 reward：

$$
G_t
=
r_t
+
\gamma r_{t+1}
+
\gamma^2r_{t+2}
+\cdots
$$

即：

$$
G_t
=
\sum_{k=0}^{T-t}
\gamma^k r_{t+k}
$$

---

### Reward != Return

如果：

```text
r_0 = 0
r_1 = 0
r_2 = 1
```

那么第 0 步 reward：

$$
r_0=0
$$

但 return：

$$
G_0
=
\gamma^2
$$

所以前面的 action 仍然可以从未来 reward 获得训练信号。

---

### Discount Factor

$$
0\le\gamma\le1
$$

控制未来 reward 权重。

如果：

$$
\gamma=0
$$

只关心即时 reward。

如果：

$$
\gamma\approx1
$$

长期 reward 权重更高。

---

### 为什么需要 Discount？

理论上有几个作用：

1. 表达对近期 reward 的偏好；
2. 无限 horizon 中保证 return 收敛；
3. 控制 effective horizon；
4. 在某些任务中降低远期 reward 带来的 variance。

---

### LLM RL 中 \(\gamma\) 一定很重要吗？

不一定。

大量 reasoning / response-level RL 只有最终 outcome reward：

```text
intermediate reward = 0
final reward = R
```

而且整个 response 被视为一次 finite trajectory。

此时很多实现等价于：

$$
\gamma=1
$$

但 Agentic RL 真正出现多步环境 interaction 后：

* step reward；
* delayed reward；
* long horizon；

会重新让 discount / credit 问题变重要。

---

## 3.4 \(V(s)\)、\(Q(s,a)\)、Advantage \(A(s,a)\) 有什么区别？ `[P0]`

这是 RL 最关键的一组三个量。

---

### State Value

$$
V^\pi(s)
=
\mathbb E_\pi[G_t|s_t=s]
$$

表示：

> 在状态 \(s\) 下，之后按照 policy \(\pi\) 行动，预计能得到多少 return。

---

### Action Value

$$
Q^\pi(s,a)
=
\mathbb E_\pi[G_t|s_t=s,a_t=a]
$$

表示：

> 在状态 \(s\) 下先选择 action \(a\)，然后继续按照 \(\pi\) 行动，预计能得到多少 return。

---

### Advantage

$$
A^\pi(s,a)
=
Q^\pi(s,a)-V^\pi(s)
$$

表示：

> 这个 action 相比当前 policy 在这个 state 下的平均水平好多少。

---

### 一个简单例子

某状态：

$$
V(s)=0.6
$$

Action A：

$$
Q(s,A)=0.9
$$

则：

$$
A(s,A)=0.3
$$

应该增加它的概率。

Action B：

$$
Q(s,B)=0.2
$$

则：

$$
A(s,B)=-0.4
$$

应该降低它的概率。

---

### 为什么 Advantage 比 Q 更适合 Policy Gradient？

假设所有 action 的 return 都很高：

```text
A: 101
B: 100
C: 99
```

Q 都是正数。

如果直接用 Q：

> 三个 action 都会被强化。

但真正想知道：

> 哪些 action 比当前平均策略更好？

减掉 baseline：

$$
V(s)
$$

就得到 relative quality。

---

### 和 GRPO 的关系

后面 GRPO 会做：

```text
group reward
-
group mean reward
```

这在直觉上也是：

> 构造某种 relative advantage。

只是 baseline 不再来自 learned value network。

---

## 3.5 Policy 是什么？Deterministic / Stochastic Policy 有什么区别？ `[P0]`

### Policy

Policy 表示：

> 在 state 下应该怎样选择 action。

随机 policy：

$$
\pi_\theta(a|s)
=
P(a_t=a|s_t=s)
$$

---

### Deterministic Policy

$$
a=\mu_\theta(s)
$$

一个 state 对应固定 action。

---

### Stochastic Policy

输出 action distribution：

$$
a\sim\pi_\theta(\cdot|s)
$$

例如 LLM：

```text
context
↓
logits
↓
softmax
↓
token distribution
↓
sample token
```

本身就是 stochastic policy 的典型实现。

---

### Temperature 影响什么？

假设 logits：

$$
z
$$

temperature sampling：

$$
\pi_T(a|s)
=
\operatorname{softmax}
\left(
\frac{z}{T}
\right)
$$

因此真正 rollout 行为分布不只是：

> 模型参数 \(\theta\)。

还包含：

* temperature；
* top-p；
* top-k；
* repetition penalty；
* structured decoding；
* tool constraints。

所以 RL 中保存 behavior policy provenance 时，不能只保存 checkpoint 名字。

---

### Greedy decoding 算 stochastic policy 吗？

如果：

$$
a=\arg\max_a\pi(a|s)
$$

执行行为已经是 deterministic。

底层模型仍输出 probability distribution，但实际 behavior policy 的采样规则是确定性的。

---

## 3.6 REINFORCE / Policy Gradient 的核心公式是什么？ `[P0]`

目标：

$$
J(\theta)
=
\mathbb E_{\tau\sim\pi_\theta}
[R(\tau)]
$$

希望最大化期望 return。

REINFORCE 的基本形式：

$$
\nabla_\theta J(\theta)
=
\mathbb E_{\tau\sim\pi_\theta}
\left[
R(\tau)
\nabla_\theta
\log p_\theta(\tau)
\right]
$$

如果环境 dynamics 不依赖 \(\theta\)，trajectory probability：

$$
p_\theta(\tau)
\propto
\prod_t
\pi_\theta(a_t|s_t)
$$

于是：

$$
\log p_\theta(\tau)
=
\sum_t
\log\pi_\theta(a_t|s_t)
+\text{const}
$$

因此：

$$
\nabla_\theta J(\theta)
=
\mathbb E
\left[
\sum_t
R(\tau)
\nabla_\theta
\log\pi_\theta(a_t|s_t)
\right]
$$

更常用 reward-to-go：

$$
\nabla_\theta J(\theta)
=
\mathbb E
\left[
\sum_t
G_t
\nabla_\theta
\log\pi_\theta(a_t|s_t)
\right]
$$

---

### 直觉

如果某个 sampled action 最终 return 很高：

$$
G_t>0
$$

更新：

$$
+\nabla\log\pi_\theta(a_t|s_t)
$$

增加该 action 的 probability。

如果 advantage 为负：

$$
A_t<0
$$

则降低该 action probability。

所以可以粗略记：

```text
good sampled behavior
→ probability ↑

bad sampled behavior
→ probability ↓
```

---

### Loss 实现

优化器通常是最小化 loss，所以：

$$
\mathcal L_{PG}
=
-
A_t
\log\pi_\theta(a_t|s_t)
$$

如果：

$$
A_t>0
$$

最小化 loss 会提高：

$$
\log\pi_\theta(a_t|s_t)
$$

---

## 3.7 为什么 Policy Gradient 里出现 \(\log \pi_\theta(a|s)\)？ `[P0]`

关键是 log-derivative trick：

$$
\nabla_\theta p_\theta(x)
=
p_\theta(x)
\nabla_\theta
\log p_\theta(x)
$$

因为：

$$
\nabla_\theta\log p_\theta(x)
=
\frac{
\nabla_\theta p_\theta(x)
}{
p_\theta(x)
}
$$

所以：

$$
\nabla p
=
p\nabla\log p
$$

---

### 从期望开始

目标：

$$
J(\theta)
=
\sum_\tau
p_\theta(\tau)
R(\tau)
$$

梯度：

$$
\nabla J
=
\sum_\tau
\nabla p_\theta(\tau)
R(\tau)
$$

使用 log trick：

$$
=
\sum_\tau
p_\theta(\tau)
\nabla\log p_\theta(\tau)
R(\tau)
$$

于是：

$$
=
\mathbb E_{\tau\sim p_\theta}
[
R(\tau)
\nabla\log p_\theta(\tau)
]
$$

---

### 为什么这很重要？

我们不知道：

$$
R(\tau)
$$

对参数 \(\theta\) 的可微梯度。

比如：

```text
模型生成答案
↓
执行 Python 单测
↓
pass / fail
```

unit test reward 不需要可微。

我们只需要：

$$
\log\pi_\theta(a|s)
$$

对模型参数可微。

这就是 Policy Gradient 能处理：

* discrete token；
* external environment；
* non-differentiable reward；

的关键原因。

---

## 3.8 为什么要引入 Baseline？ `[P0]`

最原始 REINFORCE：

$$
G_t
\nabla
\log\pi_\theta(a_t|s_t)
$$

方差非常大。

例如某状态下所有 action 的 return 都在：

```text
99 ~ 101
```

只用 return：

```text
99
100
101
```

全部是很大的正权重。

但我们真正关心：

```text
-1
0
+1
```

这种相对差异。

---

### 引入 Baseline

使用：

$$
G_t-b(s_t)
$$

如果：

$$
b(s_t)\approx V^\pi(s_t)
$$

则：

$$
G_t-V(s_t)
$$

可以近似 advantage。

---

### 为什么能降低方差？

它将：

```text
absolute return
```

转成：

```text
relative performance
```

减少不同 state 自身难度造成的整体 reward scale 波动。

---

### 为什么不能随便选和 action 有关的 baseline？

action-independent baseline：

$$
b(s)
$$

不会改变 gradient expectation。

但如果：

$$
b(s,a)
$$

直接依赖当前 sampled action，就可能改变期望梯度，引入 bias。

具体推导见 3.10。

---

### PPO 与 GRPO

PPO：

```text
通常 learned critic
↓
估计 V(s)
↓
构造 advantage
```

GRPO：

```text
同一 prompt 采样 group
↓
group rewards
↓
组内相对标准化
↓
构造 advantage
```

所以 GRPO 的“critic-free”不是：

> 不需要 advantage。

而是：

> 不需要单独训练一个 value critic 来提供 baseline。

---

## 3.9 On-policy 与 Off-policy 有什么区别？ `[P0]`

### On-policy

训练数据由当前 policy：

$$
\pi_\theta
$$

或非常接近当前 policy 的 behavior policy 产生。

例如：

```text
current policy
↓
rollout
↓
reward
↓
update this policy
```

---

### Off-policy

数据可能来自另一个 behavior policy：

$$
\mu
$$

但目标是优化：

$$
\pi_\theta
$$

例如：

```text
old model trajectories
human demonstrations
replay buffer
another policy
```

---

### 为什么 distribution mismatch 是问题？

我们真正想计算：

$$
\mathbb E_{a\sim\pi_\theta}
[f(a)]
$$

但数据来自：

$$
a\sim\mu
$$

直接平均：

$$
\frac1N\sum_i f(a_i)
$$

估计的是：

$$
\mathbb E_\mu[f(a)]
$$

不是：

$$
\mathbb E_\pi[f(a)]
$$

需要某种 distribution correction。

最基本就是 importance sampling：

$$
\frac{\pi(a|s)}
{\mu(a|s)}
$$

---

### PPO 是不是完全 On-policy？

更准确说：

> PPO 是近似 on-policy。

rollout 由：

$$
\pi_{\text{old}}
$$

生成。

然后 policy 更新成：

$$
\pi_\theta
$$

训练期间：

$$
\pi_\theta\neq\pi_{\text{old}}
$$

所以 PPO 用 importance ratio：

$$
r_t
=
\frac{
\pi_\theta(a_t|s_t)
}{
\pi_{\text{old}}(a_t|s_t)
}
$$

并通过 clipping 限制偏离。

---

# P1

## 3.10 为什么 action-independent baseline 不改变 Policy Gradient 的期望？ `[P1]`

我们需要证明：

$$
\mathbb E_{a\sim\pi_\theta}
[
b(s)
\nabla_\theta
\log\pi_\theta(a|s)
]
=
0
$$

由于：

$$
b(s)
$$

与 action 无关，可以提出期望：

$$
=
b(s)
\sum_a
\pi_\theta(a|s)
\nabla_\theta
\log\pi_\theta(a|s)
$$

使用：

$$
\pi\nabla\log\pi
=
\nabla\pi
$$

得到：

$$
=
b(s)
\sum_a
\nabla_\theta
\pi_\theta(a|s)
$$

$$
=
b(s)
\nabla_\theta
\sum_a
\pi_\theta(a|s)
$$

而：

$$
\sum_a
\pi_\theta(a|s)
=
1
$$

所以：

$$
=
b(s)\nabla_\theta1
=
0
$$

因此：

$$
\mathbb E[
(G_t-b(s_t))
\nabla\log\pi
]
$$

与原始：

$$
\mathbb E[
G_t\nabla\log\pi
]
$$

拥有相同的 expectation。

---

### 为什么还能降低 variance？

因为可以选择：

$$
b(s)
$$

使：

$$
G_t-b(s)
$$

的尺度更集中。

理想情况下：

$$
b(s)=V(s)
$$

于是得到：

$$
A(s,a)
$$

---

### 面试官问：任意 baseline 都降方差吗？

不一定。

理论上：

> action-independent baseline 不改变期望。

但一个非常差的 baseline：

```text
true return ~ 1

baseline = 1,000,000
```

反而会增加方差。

所以：

> 无偏

和：

> 降低方差

是两个不同命题。

---

## 3.11 Monte Carlo、TD、Bootstrap 分别是什么？ `[P1]`

### Monte Carlo

等待完整 episode 结束，直接使用实际 return：

$$
G_t
=
r_t+\gamma r_{t+1}+\cdots
$$

估计：

$$
V(s_t)
$$

---

### 优点

如果 trajectory 是真实采样：

> 不需要依赖 learned value estimate。

---

### 缺点

需要等到 episode 结束。

而且 variance 高。

---

### Temporal Difference

TD(0) 使用：

$$
r_t+\gamma V(s_{t+1})
$$

作为 target：

$$
V(s_t)
\leftarrow
r_t+\gamma V(s_{t+1})
$$

TD error：

$$
\delta_t
=
r_t
+
\gamma V(s_{t+1})
-
V(s_t)
$$

---

### Bootstrap

Bootstrap 指：

> target 中使用当前模型自己的估计。

例如：

$$
V(s_{t+1})
$$

就是 bootstrap。

---

### Bias / Variance

Monte Carlo：

```text
真实完整 return
↓
bias 较低
variance 较高
```

TD：

```text
部分真实 reward
+
learned value
↓
variance 较低
但引入 bootstrap bias
```

---

### LLM RL 为什么很多时候不像传统 TD？

很多 reasoning RL：

```text
生成完整 response
↓
拿最终 reward
↓
更新
```

更接近 Monte Carlo episodic return。

但当 Agent horizon 很长，或者需要 turn-level value / critic 时，TD/GAE 类思想会重新变得重要。

---

## 3.12 Bias–Variance Trade-off 在 RL 中怎么理解？ `[P1]`

RL 里很多设计都在交换：

```text
bias
vs
variance
```

---

### Monte Carlo Return

$$
G_t
=
\sum_k
\gamma^k r_{t+k}
$$

使用真实 sampled future reward。

优点：

> 不依赖 value approximation。

缺点：

> future randomness 全部进入 estimator。

所以 variance 高。

---

### One-step TD

$$
r_t+\gamma V(s_{t+1})
$$

future 大部分由：

$$
V(s_{t+1})
$$

代替。

variance 下降。

但如果 critic 错：

> target 有 bias。

---

### Reward / Credit 也一样

Outcome-only：

```text
final reward
```

偏离人工 process assumptions，通常 bias 较少，但 credit variance 高。

Process judge：

```text
step-specific score
```

credit 更密集，但 judge 错误会引入 bias。

---

### GRPO 也有这个问题

group mean / std：

```text
从有限 G samples 估计 relative baseline
```

group 小：

* estimator noise 更大；
* 但 rollout 成本低。

group 大：

* relative statistic 稳定；
* 但成本更高。

后面 Macro 4 会继续。

---

## 3.13 Importance Sampling 为什么可以做分布修正？ `[P1]`

我们想求：

$$
\mathbb E_{x\sim p}[f(x)]
$$

即：

$$
\sum_xp(x)f(x)
$$

但手里 samples 来自：

$$
x\sim q
$$

乘除 \(q(x)\)：

$$
\sum_x
q(x)
\frac{p(x)}{q(x)}
f(x)
$$

所以：

$$
\mathbb E_p[f(x)]
=
\mathbb E_q
\left[
\frac{p(x)}{q(x)}
f(x)
\right]
$$

importance weight：

$$
w(x)
=
\frac{p(x)}{q(x)}
$$

---

### Policy Gradient 中

数据来自 behavior policy：

$$
\pi_{\text{old}}
$$

希望评估新 policy：

$$
\pi_\theta
$$

单步 ratio：

$$
r_t(\theta)
=
\frac{
\pi_\theta(a_t|s_t)
}{
\pi_{\text{old}}(a_t|s_t)
}
$$

LLM 中通常从 logprob 计算：

$$
r_t
=
\exp
\left[
\log\pi_\theta(a_t|s_t)
-
\log\pi_{\text{old}}(a_t|s_t)
\right]
$$

---

### 一个例子

behavior policy：

$$
q(a)=0.1
$$

target policy：

$$
p(a)=0.5
$$

那么：

$$
w=5
$$

意味着：

> 这个 action 在目标 policy 下比在采样 policy 下更常见，因此 sample 需要更大权重。

---

### 支持集条件

如果：

$$
q(x)=0
$$

但：

$$
p(x)>0
$$

则：

$$
\frac{p(x)}{q(x)}
$$

无法定义。

因此 importance sampling 要求 behavior distribution 覆盖 target distribution 所需的 support。

---

## 3.14 Importance Weight 为什么会高方差甚至爆炸？ `[P1]`

假设：

$$
p(a)=0.9
$$

但 behavior：

$$
q(a)=0.001
$$

importance weight：

$$
w=900
$$

一个极少出现的 sample 就可能主导整个 gradient。

---

### Trajectory 情况更严重

trajectory probability：

$$
P_\pi(\tau)
=
\prod_t
\pi(a_t|s_t)
$$

于是 trajectory ratio：

$$
w(\tau)
=
\prod_t
\frac{
\pi(a_t|s_t)
}{
\mu(a_t|s_t)
}
$$

假设每一步 ratio：

$$
1.1
$$

100 步：

$$
1.1^{100}
\approx13780
$$

而每步：

$$
0.9
$$

100 步：

$$
0.9^{100}
\approx2.66\times10^{-5}
$$

长 horizon 后指数级放大或衰减。

---

### Log Space

工程上通常算：

$$
\log w
=
\sum_t
(
\log\pi_t-\log\mu_t
)
$$

然后：

$$
w=e^{\log w}
$$

可以减少直接 probability product 的数值下溢，但：

> 统计方差问题仍然存在。

log-space 只能修 numeric stability，不能解决 statistical instability。

---

### 常见缓解

* clipping；
* truncated importance sampling；
* trust region；
* stale rollout filtering；
* smaller policy update；
* per-token / per-step ratio；
* V-trace 类 correction。

PPO clipping 就是下一章最重要的一个例子。

---

## 3.15 GAE 是什么？为什么它能调节 Bias / Variance？ `[P1]`

GAE：Generalized Advantage Estimation。

先定义 TD residual：

$$
\delta_t
=
r_t
+
\gamma V(s_{t+1})
-
V(s_t)
$$

GAE：

$$
\hat A_t^{GAE}
=
\sum_{l=0}^{\infty}
(\gamma\lambda)^l
\delta_{t+l}
$$

有限 trajectory：

$$
\hat A_t
=
\delta_t
+
\gamma\lambda\delta_{t+1}
+
(\gamma\lambda)^2\delta_{t+2}
+\cdots
$$

---

### \(\lambda\) 控制什么？

如果：

$$
\lambda=0
$$

则：

$$
\hat A_t=\delta_t
$$

接近 one-step TD。

特点：

```text
更依赖 critic
variance 低
bias 可能更高
```

如果：

$$
\lambda\rightarrow1
$$

会纳入更多未来 TD residual。

越来越接近 Monte Carlo-style advantage：

```text
critic bootstrap 少
variance 高
bias 低
```

---

### 为什么 GAE 常和 PPO 一起出现？

PPO 通常有：

```text
actor
+
critic
```

critic 提供：

$$
V(s_t)
$$

GAE 使用：

$$
V(s_t)
$$

构造较稳定的 advantage。

---

### GRPO 为什么没有经典 GAE？

标准 GRPO 没有单独 learned value critic。

它使用 group-relative reward statistics 构造 advantage。

所以：

> critic-free

也意味着经典 GAE 不再直接适用。

---

## 3.16 Entropy Regularization 在 RL 中做什么？ `[P1]`

Policy entropy：

$$
H(\pi(\cdot|s))
=
-
\sum_a
\pi(a|s)
\log\pi(a|s)
$$

高 entropy：

```text
distribution flatter
more exploration
```

低 entropy：

```text
distribution concentrated
more deterministic
```

---

### Entropy Bonus

Objective 可以写：

$$
J
=
J_{\text{reward}}
+
\beta
\mathbb E[H(\pi)]
$$

如果做 loss minimization：

$$
\mathcal L
=
\mathcal L_{\text{policy}}
-
\beta H
$$

鼓励 policy 不要太快 collapse。

---

### 为什么需要？

假设某个 early lucky action 得到高 reward：

```text
第一次偶然成功
↓
probability 快速上升
↓
其他行为概率下降
↓
探索减少
↓
可能锁死在 suboptimal mode
```

entropy bonus 可以减缓这种 premature collapse。

---

### LLM 中意味着什么？

可能体现为：

* response diversity；
* reasoning path diversity；
* search query diversity。

但 entropy 太高：

```text
行为随机
准确率下降
格式更不稳定
```

所以 entropy 不是越高越好。

---

### Entropy 与 Sampling Temperature 是一回事吗？

不是。

Temperature：

> rollout generation-time 修改采样分布。

Entropy regularization：

> training objective 中直接鼓励 policy 保持一定不确定性。

两者都影响 exploration，但作用层不同。

---

## 3.17 Reward Shaping 什么时候有帮助，什么时候会改坏目标？ `[P1]`

假设真正任务只有最终 reward：

```text
success +1
failure 0
```

非常 sparse。

可能几十步 action 后才知道结果。

Reward shaping 给中间步骤增加：

```text
good search      +0.1
good evidence    +0.1
invalid action   -0.2
```

希望加速学习。

---

### 好处

* denser learning signal；
* easier credit assignment；
* faster convergence；
* easier exploration。

---

### 风险：代理目标替代真实目标

比如：

```text
每次 search +0.1
```

Agent 可能学：

```text
不停 search
```

而不是完成任务。

即：

> 优化 shaped reward，不等于优化最终目标。

---

### Potential-based Reward Shaping

经典理论中有一类特殊形式：

$$
F(s,a,s')
=
\gamma\Phi(s')-\Phi(s)
$$

在某些假设下可以保持 optimal policy 不变。

但现实 LLM Agent 中：

```text
LLM Judge process reward
search utility reward
citation reward
```

通常并不天然满足这种形式。

所以必须通过实验确认 shaped reward 是否改变行为目标。

---

### 这和后面 Credit Assignment 的关系

CW-GRPO / Process Judge 之类方法的重要问题之一就是：

> Process signal 到底应该作为 reward 直接优化，还是只用来重分配 outcome advantage？

两者不是一回事。

Macro 8 会重点展开。

---

## 3.18 Contextual Bandit 与 Sequential RL 有什么区别？ `[P1]`

### Contextual Bandit

每轮：

```text
context x
↓
choose action a
↓
reward r
↓
结束
```

后续 state 不依赖当前 action。

目标：

$$
\max
\mathbb E[r(x,a)]
$$

---

### Sequential RL

当前 action 改变未来状态：

$$
s_t
\xrightarrow{a_t}
s_{t+1}
$$

而：

$$
s_{t+1}
$$

又影响之后：

$$
a_{t+1},a_{t+2},\ldots
$$

因此当前 action 不仅影响即时 reward，还影响未来 opportunity。

---

### 单轮 LLM Preference Optimization

例如：

```text
prompt
↓
response
↓
reward
```

可以近似视为 contextual bandit / one-step RL。

虽然 response 内部有多个 tokens，但外部环境没有多次 interaction。

---

### Search Agent

```text
query
↓
search observation
↓
new reasoning state
↓
next query
↓
new observation
```

是真正更明显的 sequential decision process。

第一次 query 会改变：

> 后面模型能看到什么。

因此 credit assignment 更复杂。

---

### 为什么这一区别重要？

很多适用于：

```text
one-shot response RL
```

的方法，搬到：

```text
multi-turn tool agent
```

后不一定成立。

因为 environment transition 开始成为训练问题的一部分。

---

## 3.19 Credit Assignment 为什么会随 Horizon 增长迅速变难？ `[P1]`

假设 trajectory：

```text
a1
↓
a2
↓
a3
↓
...
↓
a20
↓
final reward = 0
```

问题：

> 到底是哪一步错了？

Outcome reward 只告诉：

```text
整体失败
```

但没告诉：

```text
a3 bad?
a7 bad?
a20 bad?
```

---

### Delayed Reward

早期 action：

$$
a_t
$$

可能直到：

$$
T\gg t
$$

才看到 reward。

中间存在很多 stochastic transitions：

$$
s_{t+1},a_{t+1},\ldots
$$

因此 attribution 越来越不确定。

---

### Failure Propagation

例如 Search Agent：

```text
bad query
↓
retrieved weak evidence
↓
reasoning gets confused
↓
second query becomes worse
↓
wrong answer
```

最后一步 answer 本身可能在已有 context 下已经是“合理选择”。

真正 causal failure 发生在更早位置。

---

### Variance

REINFORCE 给每个 action 同一个 trajectory-level outcome：

$$
R(\tau)
\nabla\log\pi(a_t|s_t)
$$

随着 horizon 增长：

> 很多 action 得到同一个 noisy reward。

gradient estimator variance 会很高。

---

### 解决思路

后续会看到：

```text
value baseline
GAE
process reward
turn-level critic
fatal masking
contribution weight
counterfactual credit
```

它们都在不同方式回答：

> 最终 reward 应该怎样分配回之前的决策？

---

# P2

## 3.20 Policy Gradient Theorem 的核心推导是什么？ `[P2]`

这里不要求完整证明 discounted state occupancy 的所有技术细节，但至少要能从 expected return 推到：

$$
\nabla_\theta J
=
\mathbb E[
Q^\pi(s,a)
\nabla_\theta\log\pi_\theta(a|s)
]
$$

---

### 从 trajectory objective 出发

定义：

$$
J(\theta)
=
\mathbb E_{\tau\sim p_\theta(\tau)}
[R(\tau)]
$$

展开：

$$
J(\theta)
=
\sum_\tau
p_\theta(\tau)R(\tau)
$$

求梯度：

$$
\nabla_\theta J
=
\sum_\tau
\nabla_\theta p_\theta(\tau)
R(\tau)
$$

使用：

$$
\nabla p=p\nabla\log p
$$

得到：

$$
\nabla_\theta J
=
\sum_\tau
p_\theta(\tau)
R(\tau)
\nabla_\theta
\log p_\theta(\tau)
$$

即：

$$
=
\mathbb E_{\tau}
[
R(\tau)
\nabla_\theta
\log p_\theta(\tau)
]
$$

---

### Trajectory Probability

MDP trajectory：

$$
p_\theta(\tau)
=
\rho(s_0)
\prod_t
\pi_\theta(a_t|s_t)
P(s_{t+1}|s_t,a_t)
$$

取 log：

$$
\log p_\theta(\tau)
=
\log\rho(s_0)
+
\sum_t
\log\pi_\theta(a_t|s_t)
+
\sum_t
\log P(s_{t+1}|s_t,a_t)
$$

如果环境 dynamics：

$$
P
$$

不依赖 \(\theta\)，那么：

$$
\nabla_\theta
\log p_\theta(\tau)
=
\sum_t
\nabla_\theta
\log\pi_\theta(a_t|s_t)
$$

于是：

$$
\nabla_\theta J
=
\mathbb E
\left[
R(\tau)
\sum_t
\nabla
\log\pi_\theta(a_t|s_t)
\right]
$$

---

### Reward-to-go

早于 action \(a_t\) 的 reward：

$$
r_0,\ldots,r_{t-1}
$$

不受：

$$
a_t
$$

影响。

因此可以把完整 trajectory return 替换为：

$$
G_t
$$

减少 variance：

$$
\nabla J
=
\mathbb E
\left[
\sum_t
G_t
\nabla
\log\pi(a_t|s_t)
\right]
$$

---

### 再条件化

因为：

$$
Q^\pi(s_t,a_t)
=
\mathbb E[G_t|s_t,a_t]
$$

所以：

$$
\nabla J
=
\mathbb E_{s,a\sim\pi}
[
Q^\pi(s,a)
\nabla
\log\pi(a|s)
]
$$

再减去 action-independent baseline：

$$
V^\pi(s)
$$

得到：

$$
\nabla J
=
\mathbb E
[
A^\pi(s,a)
\nabla
\log\pi(a|s)
]
$$

这就是后面 PPO objective 的理论入口。

---

### 一条完整链

```text
Expected Return
      ↓
Likelihood-ratio trick
      ↓
Trajectory log probability
      ↓
Sum of action logprobs
      ↓
Reward-to-go
      ↓
Q(s,a)
      ↓
subtract V(s)
      ↓
Advantage
```

---

## 3.21 长 Horizon 下 Trajectory-level Importance Ratio 为什么容易失控？ `[P2]`

设 behavior policy：

$$
\mu
$$

target：

$$
\pi
$$

完整 trajectory importance ratio：

$$
W(\tau)
=
\frac{
P_\pi(\tau)
}{
P_\mu(\tau)
}
$$

在环境 dynamics 相同的情况下：

$$
W(\tau)
=
\prod_{t=0}^{T-1}
\frac{
\pi(a_t|s_t)
}{
\mu(a_t|s_t)
}
$$

定义：

$$
r_t
=
\frac{
\pi(a_t|s_t)
}{
\mu(a_t|s_t)
}
$$

则：

$$
W
=
\prod_t r_t
$$

---

### 即使每一步变化很小

假设：

$$
r_t=1.05
$$

200 步：

$$
1.05^{200}
\approx17292
$$

如果：

$$
r_t=0.95
$$

200 步：

$$
0.95^{200}
\approx3.5\times10^{-5}
$$

所以 tiny per-step mismatch 会指数累积。

---

### Log Space

$$
\log W
=
\sum_t
\log r_t
$$

如果：

$$
\log r_t
$$

有均值和方差，随着 horizon 增长：

```text
mean ∝ T
variance ∝ T
```

最终：

$$
W=e^{\log W}
$$

呈现极端 heavy-tailed behavior。

---

### 为什么 LLM 更麻烦？

一条 response：

```text
1000 tokens
```

本身就有 1000 个 action。

一个 multi-turn agent：

```text
10 turns
×
每轮 200 tokens
```

可能有数千个 token actions。

如果机械使用完整 sequence product ratio：

> 统计稳定性会非常差。

这也是为什么后续算法会认真讨论：

* token-level ratio；
* sequence-level ratio；
* clipping；
* normalization；
* stale policy；
* GSPO 等。

---

### Numerical vs Statistical Problem

必须区分：

#### Numerical

probability product underflow：

```text
10^-300
```

用 logprob 可以解决。

#### Statistical

importance weight 方差爆炸：

```text
one sample weight = 10000
others ~ 0
```

log-space **解决不了**。

这是算法问题。

---

## 3.22 Entropy-Regularized RL 的 Objective 应该怎样理解？ `[P2]`

经典 objective：

$$
J(\pi)
=
\mathbb E
\left[
\sum_t
\gamma^t r_t
\right]
$$

Entropy-Regularized RL：

$$
J(\pi)
=
\mathbb E
\left[
\sum_t
\gamma^t
(
r_t
+
\alpha H(\pi(\cdot|s_t))
)
\right]
$$

即不仅奖励任务 reward，还奖励 policy 保持随机性。

---

### 另一种写法

因为：

$$
H(\pi)
=
-\mathbb E_{a\sim\pi}
[
\log\pi(a|s)
]
$$

objective 可以写成：

$$
\mathbb E
[
r_t
-
\alpha\log\pi(a_t|s_t)
]
$$

可以理解为：

> reward 高，同时不要把概率分布过快压缩到少数 action。

---

### 为什么这不只是“加点随机”？

它改变了 optimal policy。

普通 RL：

> 只要 reward 最大，完全 deterministic policy 可能最优。

entropy regularized：

> 即使 reward 相同，也偏好更高 entropy 的 policy。

所以它对应一个新的 optimization objective，而不仅是训练 trick。

---

### 与 KL Regularization 的关系

如果目标是保持接近 reference policy：

$$
\pi_{\text{ref}}
$$

常见 objective：

$$
J
=
\mathbb E[R]
-
\beta
D_{KL}
(
\pi
\|
\pi_{\text{ref}}
)
$$

展开：

$$
D_{KL}
=
\mathbb E_\pi
[
\log\pi
-
\log\pi_{\text{ref}}
]
$$

所以：

$$
-\beta KL
=
\beta H(\pi)
+
\beta
\mathbb E_\pi[
\log\pi_{\text{ref}}
]
$$

说明：

> KL-to-reference 同时包含 entropy-like effect 和 reference preference。

因此：

```text
entropy bonus
≠
KL penalty
```

但数学上有联系。

---

### LLM 后训练为什么更常看到 KL？

因为不只是想：

> 保持探索。

还希望：

> 不要离 pretrained / SFT policy 太远。

否则可能：

* language quality 崩坏；
* reward hacking；
* mode collapse；
* alignment drift。

---

## 3.23 TRPO 的 Trust Region 思想与 PPO 有什么关系？ `[P2]`

### Policy Gradient 的问题

如果直接：

$$
\theta
\leftarrow
\theta+\eta\nabla J
$$

一步更新太大：

```text
old policy
↓
new policy very different
```

那么：

* rollout distribution 迅速过时；
* importance ratio 极端；
* performance 可能突然崩。

---

### TRPO

Trust Region Policy Optimization 希望：

> 每次 policy update 不要离旧 policy 太远。

概念形式：

$$
\max_\theta
\mathbb E
\left[
\frac{
\pi_\theta(a|s)
}{
\pi_{\text{old}}(a|s)
}
A_{\text{old}}(s,a)
\right]
$$

subject to：

$$
\mathbb E_s
[
D_{KL}
(
\pi_{\text{old}}
\|
\pi_\theta
)
]
\le
\delta
$$

即：

```text
maximize surrogate objective
subject to
policy change limited by KL
```

---

### 为什么叫 Trust Region？

在 old policy 附近：

> surrogate objective 是可信近似。

走得太远：

> 旧数据和旧 advantage 对新 policy 的预测越来越不可靠。

所以限制 optimization 只在一个“可信区域”中进行。

---

### TRPO 的工程问题

直接解决 constrained optimization 需要：

* second-order approximation；
* Fisher-vector product；
* conjugate gradient；
* line search。

工程复杂。

---

### PPO

PPO 试图用更简单的一阶优化近似 trust-region 思想。

核心：

$$
r_t
=
\frac{
\pi_\theta(a_t|s_t)
}{
\pi_{\text{old}}(a_t|s_t)
}
$$

clipped objective：

$$
L^{CLIP}
=
\mathbb E
[
\min(
r_tA_t,
\operatorname{clip}
(r_t,1-\epsilon,1+\epsilon)
A_t
)
]
$$

它不是严格 enforce：

$$
KL\le\delta
$$

而是：

> 当 probability ratio 在有利方向变化过多时，不继续奖励这种变化。

---

### 所以 PPO 是严格 Trust Region 吗？

不是。

PPO clipping 是一种：

> practical heuristic / approximation。

实际 KL 仍可能突然增大。

因此实现常额外监控：

```text
approx_kl
```

甚至达到 threshold 时 early stop。

---

### 一句话关系

```text
TRPO:
explicit constrained trust region

PPO:
simple first-order surrogate
using ratio clipping
to approximate conservative updates
```

---

## 3.24 Offline RL 最核心的 Distribution Shift 问题是什么？ `[P2]`

Offline RL：

> 只使用固定 dataset 学 policy，不再和环境在线交互。

数据来自 behavior policy：

$$
\mu
$$

目标学习：

$$
\pi
$$

---

### 核心问题

如果 learned policy 选择 dataset 中很少甚至从没出现的 action：

$$
(s,a)\notin D
$$

那么：

$$
Q(s,a)
$$

缺乏真实数据支持。

function approximator 可能给它一个错误的高值。

然后 policy：

```text
看到高 Q
↓
更偏好这个 OOD action
↓
进一步进入 dataset 外状态
```

形成 extrapolation error。

---

### Distribution Shift

训练 data distribution：

$$
d^\mu(s,a)
$$

部署 policy distribution：

$$
d^\pi(s,a)
$$

如果二者差很大：

> critic / reward model / dynamics estimate 都可能在 OOD region 失真。

---

### 为什么监督学习没有完全相同的问题？

Behavior Cloning：

$$
\pi(a|s)
$$

主要模仿 dataset actions。

但 Offline RL 要：

> 在 dataset 基础上找到比 behavior policy 更好的 action。

这意味着它必须对：

```text
dataset 中缺少的数据区域
```

做某种泛化或估值。

风险更大。

---

### 常见解决方向

* conservative value estimation；
* behavior constraint；
* policy regularization；
* uncertainty penalty；
* dataset support constraint。

核心原则都是：

> 不要让 policy 无限制相信 dataset 外 action 的乐观估计。

---

### 和 LLM 有什么关系？

例如手里只有：

```text
旧 Search Agent trajectories
```

想直接离线优化新 Search Policy。

如果新 policy 开始产生：

```text
dataset 从未覆盖的 query / action sequence
```

离线 reward / critic 可能不可靠。

所以 Agent RL 中：

> 是否真正 online rollout

是非常关键的设计区别。

---

# 3.25 Macro 3 高频连环追问

## 第一组：MDP

```text
MDP 是什么？
↓
Markov Property 是什么？
↓
State 和 Observation 一样吗？
↓
真实 Agent 为什么常更像 POMDP？
↓
Episode 和 Trajectory 区别？
↓
Terminal 和 Truncation 区别？
```

---

## 第二组：Value

```text
Reward 和 Return 区别？
↓
V(s) 是什么？
↓
Q(s,a) 是什么？
↓
A(s,a) 是什么？
↓
为什么 Advantage 比 Return 更适合做更新权重？
↓
为什么 baseline 不改变期望梯度？
```

---

## 第三组：Policy Gradient

```text
REINFORCE 是什么？
↓
为什么出现 log π？
↓
reward 不可微为什么还能训练？
↓
为什么用 reward-to-go？
↓
为什么要 baseline？
↓
为什么 vanilla REINFORCE 方差大？
```

---

## 第四组：On / Off Policy

```text
on-policy 是什么？
↓
off-policy 是什么？
↓
为什么 old rollout 不能随便重复训练？
↓
importance sampling 怎么修正？
↓
ratio 为什么容易爆？
↓
long horizon 为什么更严重？
```

---

## 第五组：GAE

```text
TD error 是什么？
↓
Monte Carlo 和 TD 区别？
↓
什么是 bootstrap？
↓
GAE 公式？
↓
λ=0 是什么？
↓
λ→1 是什么？
↓
bias / variance 怎样变化？
```

---

## 第六组：Exploration

```text
Entropy 是什么？
↓
为什么能促进 exploration？
↓
Entropy bonus 和 temperature 一样吗？
↓
Entropy bonus 和 KL penalty 一样吗？
↓
为什么 entropy 不能越大越好？
```

---

# 3.26 Self-test

## Self-test 1：Return

给：

$$
r_0=0,\quad
r_1=1,\quad
r_2=2
$$

$$
\gamma=0.9
$$

则：

$$
G_0
=
0
+
0.9\times1
+
0.9^2\times2
$$

$$
=
0.9+1.62
=
2.52
$$

---

## Self-test 2：Advantage

若：

$$
Q(s,a)=2.5
$$

$$
V(s)=3.0
$$

则：

$$
A(s,a)=-0.5
$$

表示：

> 这个 action 比当前 policy 在该 state 下的平均水平更差。

即使：

$$
Q(s,a)>0
$$

也可能：

$$
A(s,a)<0
$$

---

## Self-test 3：Policy Gradient Sign

Loss：

$$
\mathcal L
=
-A\log\pi(a|s)
$$

若：

$$
A>0
$$

gradient descent 会倾向于：

$$
\pi(a|s)\uparrow
$$

若：

$$
A<0
$$

则倾向：

$$
\pi(a|s)\downarrow
$$

---

## Self-test 4：Importance Ratio

如果：

$$
\log\pi_\theta(a|s)=-1.2
$$

$$
\log\pi_{\text{old}}(a|s)=-1.5
$$

则：

$$
r
=
\exp(-1.2+1.5)
=
e^{0.3}
\approx1.35
$$

表示该 action 在新 policy 下概率约为旧 policy 的 1.35 倍。

---

## Self-test 5：GAE

如果：

$$
\lambda=0
$$

那么：

$$
A_t^{GAE}
=
\delta_t
$$

如果：

$$
\lambda
$$

增加，则 advantage 使用更多未来 TD residual。

---

# 3.27 推导题

## 推导题 1：Log-Derivative Trick

从：

$$
\nabla_\theta\log p_\theta(x)
=
\frac{
\nabla_\theta p_\theta(x)
}{
p_\theta(x)
}
$$

推导：

$$
\nabla_\theta p_\theta(x)
=
p_\theta(x)
\nabla_\theta\log p_\theta(x)
$$

再把它代入：

$$
\nabla_\theta
\mathbb E_{x\sim p_\theta}[f(x)]
$$

得到：

$$
\mathbb E[
f(x)
\nabla_\theta
\log p_\theta(x)
]
$$

---

## 推导题 2：Baseline 无偏

证明：

$$
\mathbb E_{a\sim\pi}
[
b(s)
\nabla\log\pi(a|s)
]
=
0
$$

关键步骤：

$$
\sum_a
\pi(a|s)
\nabla\log\pi(a|s)
=
\sum_a
\nabla\pi(a|s)
=
\nabla1
=
0
$$

---

## 推导题 3：Importance Sampling

从：

$$
\mathbb E_p[f]
=
\sum_xp(x)f(x)
$$

插入：

$$
\frac{q(x)}{q(x)}
$$

推导：

$$
\mathbb E_q
\left[
\frac{p(x)}{q(x)}f(x)
\right]
$$

并说明：

$$
q(x)=0,\quad p(x)>0
$$

时为什么出问题。

---

## 推导题 4：Trajectory Ratio

给：

$$
P_\pi(\tau)
=
\rho(s_0)
\prod_t
\pi(a_t|s_t)
P(s_{t+1}|s_t,a_t)
$$

两个 policy：

$$
\pi,\mu
$$

证明相同环境下：

$$
\frac{P_\pi(\tau)}
{P_\mu(\tau)}
=
\prod_t
\frac{
\pi(a_t|s_t)
}{
\mu(a_t|s_t)
}
$$

因为：

```text
initial-state distribution
environment transition
```

全部约掉。

---

# 3.28 Debug 题

## Debug 1：Reward 在上涨，但真正任务成功率不涨

可能检查：

```text
reward hacking
reward-model bias
shaping objective mismatch
length bias
format score
easy-task mixture
train/eval mismatch
```

不能直接判断 RL 成功。

---

## Debug 2：Policy 很快变得几乎 deterministic

检查：

```text
entropy
temperature
KL
learning rate
advantage magnitude
reward scale
group diversity
sampling config
```

可能出现 policy collapse / insufficient exploration。

---

## Debug 3：Policy Loss 剧烈震荡

检查：

```text
advantage variance
reward scale
importance ratio
stale rollout
learning rate
gradient norm
batch size
policy update epochs
```

---

## Debug 4：Critic Loss 很低，但 Policy 表现不好

可能：

```text
critic 只是在当前 narrow distribution 上拟合好
advantage estimate bias
reward target 本身有问题
policy update 太激进
value clipping
distribution shift
```

Critic loss 低不代表 policy gradient 一定正确。

---

## Debug 5：Off-policy 数据加多之后训练反而更差

检查：

```text
behavior policy mismatch
importance weight variance
dataset support
staleness
reward distribution drift
old logprob correctness
```

“更多数据”不等于“更好的 RL 数据”。

---

# 3.29 系统设计题

## 系统设计题 1：只有 Final Reward，如何训练 20-step Agent？

至少可以讨论：

```text
Vanilla trajectory-level REINFORCE
↓
baseline / critic
↓
GAE
↓
process reward
↓
retrospective critic
↓
contribution weighting
↓
counterfactual credit
```

然后比较：

* bias；
* variance；
* judge cost；
* reward hacking；
* implementation complexity。

---

## 系统设计题 2：Rollout 比 Trainer 慢很多怎么办？

虽然完整 systems 留到 Macro 10，但理论层先明确：

如果 rollout 使用：

$$
\pi_{\text{old}}
$$

而 trainer 快速更新：

```text
rollout still generating
↓
trainer reaches policy v5
↓
trajectory from policy v1 returns
```

数据逐渐 off-policy。

所以系统吞吐问题最终会变成：

> statistical correctness 问题。

可以讨论：

* bounded staleness；
* policy version；
* discard threshold；
* importance correction；
* sync barrier。

---

## 系统设计题 3：Reward 非常 sparse，90% rollout 都是 0 怎么办？

可以考虑：

```text
更好的 task curriculum
larger group
exploration
process signal
reward shaping
experience reuse
synthetic data
easier-to-hard schedule
```

但不能第一反应：

> 把所有 0 reward 样本删掉。

因为失败 trajectory 本身可能携带重要负学习信号。

---

# 3.30 Macro 3 最小知识图

本章最终应该形成：

```text
                   Environment
                        │
                        ↓
State s_t ───→ Policy πθ(a|s)
                        │
                        ↓
                    Action a_t
                        │
                        ↓
               Transition P
                        │
              ┌─────────┴─────────┐
              ↓                   ↓
         Reward r_t          State s_{t+1}
              │
              ↓
        Future Rewards
              │
              ↓
          Return G_t
              │
      ┌───────┼─────────┐
      ↓       ↓         ↓
    V(s)    Q(s,a)   Advantage
      │       │         │
      └───────┴─────────┘
              ↓
      Policy Gradient
              │
              ↓
      ∇ log π(a|s) × A
              │
              ↓
         Policy Update
```

再加上 distribution 这一条：

```text
Behavior Policy μ
       ↓
    Rollout
       ↓
training sample
       │
       ├── on-policy enough
       │        ↓
       │     direct use
       │
       └── distribution mismatch
                ↓
        importance sampling
                ↓
          high variance
                ↓
     clipping / trust region
                ↓
               PPO
```

以及 credit 这一条：

```text
Long Horizon
     ↓
Delayed Reward
     ↓
Credit Ambiguity
     ↓
High Variance
     │
     ├── Baseline
     ├── Critic
     ├── GAE
     ├── Process Reward
     ├── Contribution Weight
     └── Counterfactual Credit
```

Macro 4 接下来就不再停留于“PPO / GRPO 是什么”，而是从这套地基正式推：

$$
\text{Policy Gradient}
\rightarrow
\text{Importance Ratio}
\rightarrow
\text{Trust Region}
\rightarrow
\text{PPO}
\rightarrow
\text{RLHF}
\rightarrow
\text{GRPO}
$$

同时补完整：

```text
Preference Data
Reward Model
DPO
Old Policy
Reference Policy
KL
Clipping
Group Advantage
Zero-variance Group
Length Bias
DAPO
GSPO
```

这会是前四个 Macro 里最重的一章。

## 4. RLHF / Preference Optimization / PPO / GRPO

Macro 3 建立的是：

$$
\nabla_\theta J
=
\mathbb E
[
A(s,a)\nabla_\theta\log\pi_\theta(a|s)
]
$$

但真正训练 LLM 时，还需要回答几个工程和统计问题：

```text
Reward 从哪里来？
↓
Advantage 怎么估计？
↓
rollout 来自旧 policy，当前 policy 已更新怎么办？
↓
policy 一步更新太远怎么办？
↓
为什么还要 reference model？
↓
一个 response 有几百 / 几千 token，loss 怎么归一？
↓
没有 critic 时 advantage 从哪里来？
```

于是形成：

```text
RLHF
├── Preference Data
├── Reward Model
├── Reference Policy
└── PPO
      │
      └── critic / GAE / clipped update

Preference Optimization
└── DPO
      └── preference pair → direct policy objective

RLVR / Reasoning RL
└── GRPO
      ├── group rollout
      ├── group-relative advantage
      ├── no learned critic
      └── verifiable reward
            │
            ├── DAPO
            └── GSPO
```

这一章必须明确区分三个经常被混在一起的 policy：

```text
current policy
old / behavior policy
reference policy
```

它们职责完全不同。

---

## 4.0 问题矩阵

| 编号   | 问题                                                            | 等级 |
| ---- | ------------------------------------------------------------- | -- |
| 4.1  | 经典 RLHF Pipeline 是什么？                                         | P0 |
| 4.2  | Preference Data 是什么？为什么通常用 pairwise preference？               | P0 |
| 4.3  | Reward Model 怎么训练？Bradley–Terry 假设是什么？                        | P0 |
| 4.4  | Reward Model 有哪些常见 failure？                                   | P0 |
| 4.5  | DPO 的核心思想是什么？                                                 | P0 |
| 4.6  | DPO 和 PPO-based RLHF 有什么区别？                                   | P0 |
| 4.7  | PPO 为什么需要 old policy？                                         | P0 |
| 4.8  | PPO importance ratio 到底是什么意思？                                 | P0 |
| 4.9  | PPO clipping 到底在 clip 什么？                                     | P0 |
| 4.10 | Old Policy 和 Reference Policy 有什么区别？                          | P0 |
| 4.11 | GRPO 与 PPO 最大区别是什么？                                           | P0 |
| 4.12 | GRPO group-relative advantage 怎么算？为什么会出现 zero-variance group？ | P0 |
| 4.13 | PPO clipping 对 positive / negative advantage 分别怎样作用？          | P1 |
| 4.14 | 为什么 PPO clipping 不能保证真正的 trust region？                        | P1 |
| 4.15 | KL penalty 为什么针对 reference policy，而不是 old policy？             | P1 |
| 4.16 | KL 有哪些估计方式？                                                   | P1 |
| 4.17 | DPO objective 是怎样从 KL-regularized RLHF 推出来的？                  | P1 |
| 4.18 | DPO 中 \(\beta\) 到底控制什么？                                       | P1 |
| 4.19 | Offline Preference Optimization 与 Online RL 有什么区别？            | P1 |
| 4.20 | Verifiable Reward、Reward Model、LLM Judge Reward 有什么区别？        | P1 |
| 4.21 | 多目标 Reward 为什么不能简单认为加权和就结束？                                   | P1 |
| 4.22 | GRPO 的 group size 会影响什么？                                      | P1 |
| 4.23 | Binary Reward 下 GRPO 为什么容易出现 zero advantage？                  | P1 |
| 4.24 | Token-level ratio 和 Sequence-level ratio 有什么区别？               | P1 |
| 4.25 | Per-token mean、Per-sequence mean、Global-token mean 有什么区别？     | P1 |
| 4.26 | 为什么 response length 会影响 RL loss？                              | P1 |
| 4.27 | old logprob 为什么必须对应真正 rollout 出来的 token？                      | P2 |
| 4.28 | GRPO group normalization 会引入哪些统计问题？                           | P2 |
| 4.29 | Reward scale / normalization 会怎样改变训练？                         | P2 |
| 4.30 | DAPO 在 GRPO 上改了什么？                                            | P2 |
| 4.31 | GSPO 为什么重新使用 Sequence-level Policy Ratio？                     | P2 |
| 4.32 | GRPO / DAPO / GSPO 的 token-vs-sequence trade-off 是什么？         | P2 |
| 4.33 | Off-policy / stale rollout 如何破坏 PPO / GRPO？                   | P2 |
| 4.34 | 如果 reward 上升但 pass@1 不升，应该怎样分析？                               | P2 |

---

# P0

## 4.1 经典 RLHF Pipeline 是什么？ `[P0]`

### 30～60 秒回答

经典 RLHF 可以画成：

```text
Pretrained LM
      ↓
      SFT
      ↓
SFT Policy π_SFT
      │
      ├───────────────┐
      │               │
generate responses    │
      ↓               │
human preferences     │
      ↓               │
Reward Model rφ       │
      │               │
      └───────┬───────┘
              ↓
             PPO
              ↓
       aligned policy
```

通常有三阶段：

1. **SFT**：先让模型具备基本 instruction-following；
2. **Reward Modeling**：根据 preference pairs 学一个 scalar reward；
3. **RL Optimization**：让 policy 最大化 Reward Model 分数，同时使用 KL 约束避免离 reference policy 太远。

一个典型 objective：

$$
\max_\pi
\mathbb E_{y\sim\pi(\cdot|x)}
[
r_\phi(x,y)
]
-
\beta
D_{KL}
(
\pi(\cdot|x)
\|
\pi_{\text{ref}}(\cdot|x)
)
$$

其中：

```text
rφ
= learned human-preference proxy

πref
= 通常来自 SFT policy 的固定 reference
```

### 为什么不能只有 Reward Model？

Reward Model 只会：

```text
response
↓
score
```

它本身不会修改生成 policy。

需要 PPO 等优化算法：

$$
\max_\theta
\mathbb E[r_\phi]
$$

才能把高 reward behavior 写进模型参数。

### 为什么不能只最大化 RM？

因为 policy 可能跑到 Reward Model 没见过的分布上：

```text
RM training distribution
        ↓
policy optimization
        ↓
OOD responses
        ↓
RM extrapolation error
        ↓
reward hacking
```

所以 RLHF 常加入 reference KL。

---

## 4.2 Preference Data 是什么？为什么通常用 Pairwise Preference？ `[P0]`

一个经典 preference sample：

```text
prompt x

response A
response B

human:
A > B
```

记：

$$
(x,y_w,y_l)
$$

其中：

* \(y_w\)：winner / chosen；
* \(y_l\)：loser / rejected。

---

### 为什么不用要求标注绝对分数？

让人回答：

```text
这个回答值 7.3 / 10 吗？
```

很难保持跨 annotator、一致尺度。

而：

```text
A 和 B 哪个更好？
```

通常更容易。

因此 pairwise comparison 能降低一部分标注 calibration 难度。

---

### Preference 来源不一定是人

可以来自：

```text
human label
AI judge
rule/verifier
synthetic preference
```

因此严格来说：

> Preference Optimization 不等于一定 Human Feedback。

---

### Preference Data 仍然会有噪声

例如：

```text
annotator disagreement
position bias
verbosity bias
style preference
knowledge error
safety trade-off
```

所以：

$$
y_w\succ y_l
$$

不是绝对真理，而是观测 preference label。

---

## 4.3 Reward Model 怎么训练？Bradley–Terry 假设是什么？ `[P0]`

Reward Model：

$$
r_\phi(x,y)
\rightarrow
\mathbb R
$$

给 prompt-response 一个 scalar score。

对于 preference pair：

$$
y_w\succ y_l
$$

Bradley–Terry 风格假设：

$$
P(y_w\succ y_l|x)
=
\sigma
(
r_\phi(x,y_w)
-
r_\phi(x,y_l)
)
$$

其中：

$$
\sigma(z)
=
\frac{1}{1+e^{-z}}
$$

loss：

$$
\mathcal L_{RM}
=
-
\log
\sigma
(
r_w-r_l
)
$$

---

### 为什么只看 Reward Difference？

如果：

$$
r_w=10,\quad r_l=5
$$

和：

$$
r_w=100,\quad r_l=95
$$

reward difference 都是：

$$
5
$$

在 Bradley–Terry preference likelihood 下给出相同 pairwise probability。

所以 reward absolute zero-point 本身不可辨识。

---

### 如果 \(r_w=r_l\)

则：

$$
P(y_w\succ y_l)
=
\sigma(0)
=
0.5
$$

Reward Model 完全无法区分。

---

### 训练目标

希望：

$$
r_w-r_l
$$

越来越大。

于是：

```text
preferred response
score ↑

rejected response
score ↓
```

但它学到的是：

> 训练 preference distribution 的代理函数。

不是“真实人类价值函数”。

---

## 4.4 Reward Model 有哪些常见 Failure？ `[P0]`

### 1. Reward Hacking

Policy 找到：

```text
RM 打分高
但人类并不喜欢
```

的输出。

---

### 2. Distribution Shift

RM 在：

```text
SFT-like responses
```

上训练。

RL 后 policy 生成：

```text
very different responses
```

RM 被迫 extrapolate。

---

### 3. Length Bias

如果训练数据中：

```text
长回答更经常被标 chosen
```

RM 可能学：

```text
longer = better
```

policy 最后不断变长。

---

### 4. Style Bias

例如：

```text
分条
标题
礼貌表达
“综上所述”
```

可能成为 reward shortcut。

---

### 5. Overoptimization

RL 初期：

```text
reward ↑
human quality ↑
```

继续优化：

```text
reward ↑↑
human quality ↓
```

因为 policy 已经开始 exploitation RM imperfections。

---

### 6. Preference Inconsistency

人类 preference 可能不是严格 transitive：

```text
A > B
B > C
但 C > A
```

单 scalar reward 假设可能不能完全表示这些偏好。

---

## 4.5 DPO 的核心思想是什么？ `[P0]`

经典 RLHF：

```text
Preference Data
↓
Reward Model
↓
PPO
```

DPO 尝试变成：

```text
Preference Data
↓
Direct Policy Optimization
```

不再显式训练一个 Reward Model，再跑在线 PPO。

DPO 利用 KL-regularized RLHF objective 的 closed-form relationship，把 reward difference 改写成 policy 与 reference policy 的 log-ratio。

经典 DPO loss：

$$
\mathcal L_{\text{DPO}}
=
-
\log
\sigma
\left(
\beta
\left[
\log
\frac{
\pi_\theta(y_w|x)
}{
\pi_{\text{ref}}(y_w|x)
}
-
\log
\frac{
\pi_\theta(y_l|x)
}{
\pi_{\text{ref}}(y_l|x)
}
\right]
\right)
$$

因此希望：

```text
winner relative to reference
↑

loser relative to reference
↓
```

DPO 原论文的关键贡献正是把标准 KL-regularized RLHF 问题重参数化成一个直接的 preference classification objective，从而不需要显式 RM 和在线 RL rollout。

---

### DPO 不是普通 SFT

SFT winner-only：

$$
-\log\pi(y_w|x)
$$

只告诉模型：

```text
chosen 要提高
```

DPO 同时考虑：

```text
chosen
vs
rejected
```

是相对 preference objective。

---

## 4.6 DPO 和 PPO-based RLHF 有什么区别？ `[P0]`

### PPO-based RLHF

```text
Preference Data
↓
Reward Model
↓
Online generation
↓
Reward
↓
PPO update
```

优点：

* 可以从当前 policy 在线探索；
* 可以优化任意 scalar reward；
* 更适合环境交互、tool-use、verifiable outcome。

缺点：

* 系统复杂；
* rollout 贵；
* reward model / critic / reference 都可能占资源；
* RL 稳定性难。

---

### DPO

```text
fixed preference dataset
↓
direct objective
```

优点：

* 简单；
* 不需要 rollout loop；
* 不需要显式 Reward Model；
* 类似普通 fine-tuning workflow。

缺点：

* 主要受已有 preference data 支持；
* 缺少真正 on-policy exploration；
* 对 multi-step Agent environment 没有天然 interaction loop。

---

### 为什么 Agent RL 往往还需要 PPO/GRPO 类方法？

因为 Search Agent 的关键 data 是：

```text
policy
↓
Search
↓
environment observation
↓
new policy state
↓
Search again
```

后续 state 依赖当前 action。

这不是静态：

```text
prompt + chosen/rejected
```

pair 能完整表达的过程。

---

## 4.7 PPO 为什么需要 Old Policy？ `[P0]`

rollout 是由某个固定行为 policy：

$$
\pi_{\text{old}}
$$

产生：

$$
a_t
\sim
\pi_{\text{old}}(\cdot|s_t)
$$

然后我们开始优化新参数：

$$
\pi_\theta
$$

训练时：

$$
\pi_\theta
\neq
\pi_{\text{old}}
$$

所以 sample distribution 已经和当前 policy 不同。

---

### PPO 通过 Ratio 修正

$$
r_t(\theta)
=
\frac{
\pi_\theta(a_t|s_t)
}{
\pi_{\text{old}}(a_t|s_t)
}
$$

若：

$$
r_t=1
$$

表示新旧 policy 对这个 sampled action 的 probability 一样。

若：

$$
r_t>1
$$

当前 policy 更喜欢该 action。

若：

$$
r_t<1
$$

当前 policy 更不喜欢该 action。

---

### 为什么必须冻结 Old Policy？

如果 denominator 也跟着更新：

$$
\pi_{\text{old}}
\rightarrow
\pi_\theta
$$

ratio 永远接近：

$$
1
$$

失去意义。

因此 old policy 是 rollout 的 behavior snapshot。

---

### 实现中一定要保存一整个 Old Model 吗？

不一定。

如果 rollout 阶段直接保存：

$$
\log\pi_{\text{old}}(a_t|s_t)
$$

训练时 denominator 已经存在。

所以系统可能不保留一个完整 old-policy model，而保存 exact old logprobs。

---

## 4.8 PPO Importance Ratio 到底是什么意思？ `[P0]`

定义：

$$
r_t
=
\frac{
\pi_\theta(a_t|s_t)
}{
\pi_{\text{old}}(a_t|s_t)
}
$$

LLM 中通常：

$$
r_t
=
\exp
(
\log p_{\theta,t}
-
\log p_{\text{old},t}
)
$$

---

### 例子

old：

$$
p_{\text{old}}=0.2
$$

current：

$$
p_\theta=0.3
$$

则：

$$
r=1.5
$$

当前 policy 对这个 sampled token 的 probability 增加了 50%。

---

### 为什么不是：

$$
p_\theta-p_{\text{old}}
$$

因为 importance sampling 需要概率密度比：

$$
\frac{p}{q}
$$

而不是 probability difference。

---

### Ratio 的统计意义

data 来自：

$$
\pi_{\text{old}}
$$

ratio 用来把：

$$
\mathbb E_{\pi_{\text{old}}}
$$

重新加权，近似目标：

$$
\mathbb E_{\pi_\theta}
$$

但当 ratio 偏离 1 很多时：

* 方差大；
* old rollout 对 current policy 代表性差。

这正是 clipping 的动机。

---

## 4.9 PPO Clipping 到底在 Clip 什么？ `[P0]`

PPO clipped objective：

$$
L^{CLIP}
=
\mathbb E_t
\left[
\min
\left(
r_tA_t,
\operatorname{clip}
(r_t,1-\epsilon,1+\epsilon)
A_t
\right)
\right]
$$

注意：

> clip 的是 policy probability ratio。

不是：

* gradient；
* reward；
* advantage；
* probability 本身。

---

### 直觉

如果某 action：

$$
A_t>0
$$

说明它比 baseline 好。

我们希望：

$$
\pi_\theta(a_t|s_t)
\uparrow
$$

但如果已经提高太多：

$$
r_t>1+\epsilon
$$

PPO 不再继续奖励这一变化。

---

如果：

$$
A_t<0
$$

希望：

$$
\pi_\theta(a_t|s_t)
\downarrow
$$

但如果已经降低太多：

$$
r_t<1-\epsilon
$$

也不再继续奖励。

所以 clipping 的目标是：

> 防止一次 update 把 policy 推得离 behavior policy 太远。

PPO 原论文就是用这种 clipped surrogate 来获得比 TRPO 更简单的一阶优化流程，并允许对同一批 rollout 做多个 minibatch epoch。

---

## 4.10 Old Policy 和 Reference Policy 有什么区别？ `[P0]`

这是必须秒答的一题。

### Old Policy

$$
\pi_{\text{old}}
$$

用途：

> 表示生成这批 rollout 的 behavior policy。

进入：

$$
r_t
=
\frac{
\pi_\theta
}{
\pi_{\text{old}}
}
$$

解决：

```text
policy update stability
+
distribution correction
```

通常每轮 training iteration 更新。

---

### Reference Policy

$$
\pi_{\text{ref}}
$$

用途：

> 提供长期 anchor，防止 policy 偏离初始/SFT 模型太远。

进入：

$$
D_{KL}
(
\pi_\theta
\|
\pi_{\text{ref}}
)
$$

reference 通常冻结很久，甚至整个 RL training 不变。

---

### 一张表

| Policy                         | 是否变化                | 主要用途              |
| ------------------------------ | ------------------- | ----------------- |
| Current \(\pi_\theta\)         | 持续训练                | 正在优化              |
| Old \(\pi_{\text{old}}\)       | 每轮 rollout snapshot | PPO ratio         |
| Reference \(\pi_{\text{ref}}\) | 通常长期冻结              | KL regularization |

所以：

```text
old policy
≠
reference policy
```

即使训练刚开始它们参数可能恰好相同。

---

## 4.11 GRPO 与 PPO 最大区别是什么？ `[P0]`

PPO 通常使用 learned value function：

$$
V_\psi(s)
$$

再通过 GAE 等得到：

$$
A_t
$$

因此需要：

```text
Actor
+
Critic
```

---

### GRPO

GRPO：Group Relative Policy Optimization。

对同一个 prompt：

$$
q
$$

采样一组 response：

$$
o_1,o_2,\ldots,o_G
$$

得到 rewards：

$$
R_1,R_2,\ldots,R_G
$$

使用 group 内相对表现构造 advantage，而不是训练一个独立 critic。

典型形式：

$$
\hat A_i
=
\frac{
R_i-\mu_R
}{
\sigma_R+\epsilon
}
$$

其中：

$$
\mu_R
=
\frac1G
\sum_iR_i
$$

GRPO 最初由 DeepSeekMath 引入，目的之一就是在 LLM reasoning RL 中用 group-relative baseline 取代 PPO 的额外 value model，从而降低训练资源需求。

---

### 核心区别

```text
PPO
reward
↓
critic V(s)
↓
GAE
↓
advantage

GRPO
multiple responses per prompt
↓
group rewards
↓
relative normalization
↓
advantage
```

GRPO 仍然属于 policy optimization。

不是：

> 不再需要 advantage。

而是：

> 不再依赖 learned critic 来估计 advantage。

---

## 4.12 GRPO Group-relative Advantage 怎么算？为什么会出现 Zero-variance Group？ `[P0]`

假设一个 prompt 采样：

$$
G=4
$$

得到：

$$
R=[1,0,1,0]
$$

均值：

$$
\mu=0.5
$$

population std：

$$
\sigma=0.5
$$

于是：

$$
A=[1,-1,1,-1]
$$

形成清楚的相对 ranking：

```text
成功 response
↑

失败 response
↓
```

---

### Zero-variance Group

如果：

$$
R=[1,1,1,1]
$$

则：

$$
\mu=1
$$

$$
\sigma=0
$$

所有 response 相对平均值：

$$
R_i-\mu=0
$$

没有 group-relative learning signal。

同样：

$$
R=[0,0,0,0]
$$

也是如此。

---

### Binary Reward 特别明显

如果 reward 只有：

$$
0/1
$$

对于：

* 太简单 prompt；
* 太难 prompt；

一个 group 很容易全对或全错。

因此 group rollout 花了大量算力：

```text
generate
verify
```

最后 advantage 全为 0。

这也是后面 DAPO Dynamic Sampling 重点处理的问题之一。

---

# P1

## 4.13 PPO Clipping 对 Positive / Negative Advantage 分别怎样作用？ `[P1]`

这是面试最值得手推的一题。

---

### 当 \(A>0\)

希望：

$$
r\uparrow
$$

因为 sampled action 是好 action。

Objective：

$$
\min
(
rA,
\operatorname{clip}(r,1-\epsilon,1+\epsilon)A
)
$$

如果：

$$
r\le1+\epsilon
$$

正常增加。

如果：

$$
r>1+\epsilon
$$

clip 后：

$$
(1+\epsilon)A
$$

成为上限。

因此：

> 好 action 已经被提高太多后，继续提高 probability 不再获得额外 objective 改善。

---

### 当 \(A<0\)

希望：

$$
r\downarrow
$$

即降低坏 action probability。

但是注意：

$$
A<0
$$

会反转 min 的直觉。

例如：

$$
A=-1,\quad\epsilon=0.2
$$

若：

$$
r=0.5
$$

unclipped：

$$
rA=-0.5
$$

clipped：

$$
0.8\times(-1)=-0.8
$$

取：

$$
\min(-0.5,-0.8)=-0.8
$$

因此进一步降低到 0.5 不再带来额外收益。

---

### 可以直接记四个区域

```text
A > 0:
r 太大 → clip

A < 0:
r 太小 → clip
```

另外两个方向不会因为 clipping 获得同样保护。

---

### 为什么叫 pessimistic bound？

它取：

$$
\min
$$

使 objective 选择更保守的那一支。

---

## 4.14 为什么 PPO Clipping 不能保证真正的 Trust Region？ `[P1]`

很多人会说：

> PPO 保证 policy 不会走太远。

不严格。

它只对：

```text
sampled actions
```

上的 probability ratio 施加 surrogate clipping。

并没有直接 enforce：

$$
D_{KL}
(
\pi_{\text{old}}
\|
\pi_\theta
)
\le\delta
$$

---

### 原因一：只约束采样 action

一个 vocabulary 有：

$$
V
$$

个 action。

loss 主要观察：

$$
a_t
$$

这个 sampled token。

其他 token probability 可以重新分布。

---

### 原因二：一次梯度更新影响很多状态

parameter shared across all contexts。

改变一个 batch 的参数：

> 可能影响 dataset 里没出现的 state。

---

### 原因三：多个 epoch 累积

同一 rollout batch 做：

```text
epoch 1
epoch 2
epoch 3
epoch 4
```

current policy 会不断离 old policy 更远。

---

### 实践

所以 PPO training 常监控：

$$
D_{KL}
$$

或：

```text
approx_kl
clip fraction
```

如果 KL 太大：

> 提前终止 epoch。

所以 clipping 是：

> conservative-update heuristic。

不是严格数学 trust-region constraint。

---

## 4.15 KL Penalty 为什么针对 Reference Policy，而不是 Old Policy？ `[P1]`

这两种 KL 其实都可能出现，但语义不同。

---

### Current vs Old

$$
D_{KL}
(
\pi_\theta
\|
\pi_{\text{old}}
)
$$

表示：

> 本轮 update 离 rollout behavior 多远。

主要用于：

* update-size monitoring；
* PPO stability；
* early stop。

---

### Current vs Reference

$$
D_{KL}
(
\pi_\theta
\|
\pi_{\text{ref}}
)
$$

表示：

> RL policy 累积训练后离原始 SFT / base behavior 多远。

它控制长期 drift。

---

### 为什么 PPO Clip 不能替代 Reference KL？

假设每轮只移动一点：

```text
π0
→ π1
→ π2
→ π3
→ ...
→ π100
```

每一步：

$$
D_{KL}(\pi_t,\pi_{t-1})
$$

都很小。

但是：

$$
D_{KL}(\pi_{100},\pi_0)
$$

可以很大。

所以：

```text
local step constraint
≠
global anchor
```

Reference KL 提供后者。

---

## 4.16 KL 有哪些估计方式？ `[P1]`

定义：

$$
D_{KL}(P\|Q)
=
\sum_a
P(a)
\log
\frac{P(a)}{Q(a)}
$$

对于 LLM vocabulary，如果拥有完整 logits，可以计算 token distribution 上 exact categorical KL。

但 vocabulary 大、每 token 都算 full distribution 会增加成本。

---

### Sample-based Estimate

如果：

$$
a\sim P
$$

则：

$$
D_{KL}(P\|Q)
=
\mathbb E_{a\sim P}
\left[
\log P(a)-\log Q(a)
\right]
$$

所以可以用 sampled token：

$$
\hat k
=
\log\pi_\theta(a|s)
-
\log\pi_{\text{ref}}(a|s)
$$

估计。

单 sample 值可能为负，但 expectation 是非负。

---

### 常见近似

还会见到基于 log-ratio：

$$
r=
\frac{Q(a)}{P(a)}
$$

构造的低方差 KL estimator。

不同 RL framework 的：

```text
kl_type
```

可能不同。

所以面试和读代码时必须先确认：

> 这里的 KL 到底是哪一种 estimator？

不能看到变量叫：

```text
kl
```

就自动认为它是 full-vocabulary exact KL。

---

## 4.17 DPO Objective 是怎样从 KL-regularized RLHF 推出来的？ `[P1]`

从：

$$
\max_\pi
\mathbb E_{y\sim\pi}
[r(x,y)]
-
\beta
D_{KL}
(
\pi(\cdot|x)
\|
\pi_{\text{ref}}(\cdot|x)
)
$$

开始。

对固定 prompt \(x\)，最优 policy 满足：

$$
\pi^*(y|x)
\propto
\pi_{\text{ref}}(y|x)
\exp
\left(
\frac{r(x,y)}{\beta}
\right)
$$

因此：

$$
r(x,y)
=
\beta
\log
\frac{
\pi^*(y|x)
}{
\pi_{\text{ref}}(y|x)
}
+
\beta\log Z(x)
$$

对于同 prompt 下 winner/loser 做 reward difference：

$$
r_w-r_l
$$

partition term：

$$
\beta\log Z(x)
$$

抵消。

得到：

$$
r_w-r_l
=
\beta
\left[
\log
\frac{\pi(y_w|x)}
{\pi_{\text{ref}}(y_w|x)}
-
\log
\frac{\pi(y_l|x)}
{\pi_{\text{ref}}(y_l|x)}
\right]
$$

再代回 Bradley–Terry：

$$
P(y_w\succ y_l)
=
\sigma(r_w-r_l)
$$

就得到 DPO loss。

这也是 DPO 能跳过显式 reward model 的数学入口。

---

### 面试要点

DPO 不是神奇地：

> 不需要 reward。

而是：

> 把 implicit reward 写成 policy/reference log-ratio。

所以论文才叫：

> language model is secretly a reward model。

---

## 4.18 DPO 中 \(\beta\) 到底控制什么？ `[P1]`

从隐式 reward：

$$
r_\theta(x,y)
=
\beta
\log
\frac{
\pi_\theta(y|x)
}{
\pi_{\text{ref}}(y|x)
}
$$

看：

$$
\beta
$$

与 KL regularization strength / reward scale 有关。

直觉上它控制：

> preference fitting 与 staying-close-to-reference 之间的 trade-off。

---

### 为什么 \(\beta\) 不是越大越好？

DPO 对 \(\beta\) 和 preference data quality 都敏感，后续研究专门讨论了 reference-policy 与 KL strength 对结果的影响。

如果 regularization 太强：

```text
policy
≈
reference
```

学不到 preference。

如果太弱：

```text
policy
drifts strongly
```

容易 overfit/noise amplification。

---

## 4.19 Offline Preference Optimization 与 Online RL 有什么区别？ `[P1]`

### Offline Preference Optimization

例如 DPO：

```text
fixed dataset
(x, yw, yl)
↓
train
```

训练数据分布不随当前 policy 自动变化。

---

### Online RL

```text
current policy
↓
generate fresh rollout
↓
environment/verifier
↓
reward
↓
update
↓
new rollout
```

data distribution 会跟 policy 一起演化。

---

### Offline 优点

* 简单；
* reproducible；
* 没有 expensive rollout loop；
* 可以复用已有 preference dataset。

---

### Online 优点

policy 可以：

> 在自己当前最容易犯错、最有可能探索的新区域继续收集数据。

尤其对于：

```text
Search Agent
tool interaction
reasoning RL
```

environment state 本身由 policy action 改变。

---

### 核心 trade-off

```text
Offline
stable data
but distribution fixed

Online
adaptive data
but expensive + unstable
```

---

## 4.20 Verifiable Reward、Reward Model、LLM Judge Reward 有什么区别？ `[P1]`

### Verifiable Reward

有明确程序检查：

```text
math exact answer
unit tests
compiler
formal verifier
exact match
```

例如：

$$
R=
\begin{cases}
1,&correct\\
0,&incorrect
\end{cases}
$$

优点：

* objective；
* cheap；
* deterministic 或近似 deterministic；
* 不需要 learned judge。

缺点：

> 只适合可验证任务。

---

### Reward Model

learned neural scorer：

$$
r_\phi(x,y)
$$

优点：

* 高吞吐；
* 训练后推理快；
* 可以学习复杂 preference。

问题：

* distribution shift；
* hacking；
* calibration。

---

### LLM Judge

直接让另一个 LLM：

```text
prompt + answer + rubric
↓
score / critique
```

优点：

* 灵活；
* 不需单独训练 RM；
* 能评复杂 reasoning / writing。

缺点：

* 成本高；
* stochastic；
* prompt-sensitive；
* bias；
* self-preference；
* 更难复现。

---

### 一个非常重要的顺序

如果任务能够使用可靠 rule verifier：

> 不应因为“LLM Judge 更智能”就自动换成 Judge。

验证越直接：

```text
true task signal
```

越少引入 learned evaluator bias。

---

## 4.21 多目标 Reward 为什么不能简单认为加权和就结束？ `[P1]`

假设：

$$
R
=
\lambda_1R_{\text{correct}}
+
\lambda_2R_{\text{format}}
-
\lambda_3R_{\text{cost}}
$$

数学上当然可以这样定义。

问题是不同 reward：

* scale 不同；
* variance 不同；
* sparsity 不同；
* hacking difficulty 不同。

---

### 例如

```text
correctness ∈ {0,1}

format ∈ [0,10]
```

若直接：

$$
R
=
R_{\text{correct}}
+
R_{\text{format}}
$$

format 可能完全压过 correctness。

---

### Reward Conflict

Search Agent：

```text
answer accuracy ↑
search calls ↓
```

存在真实矛盾。

如果：

```text
search cost penalty 太大
```

Agent 最优行为可能变成：

> 不搜索，直接猜。

---

### Pareto Perspective

很多系统真实目标更像：

```text
maximize accuracy

subject to

search cost ≤ B
latency ≤ L
```

而不是随意转换成：

$$
R=accuracy-0.01cost
$$

所以需要：

* normalization；
* constraint；
* lexicographic objective；
* Pareto analysis；
* ablation。

---

## 4.22 GRPO 的 Group Size 会影响什么？ `[P1]`

对每个 prompt：

$$
G
$$

个 samples。

---

### Group 越大

通常：

* reward distribution 估计更稳定；
* 更容易同时看到 success/failure；
* zero-variance group 减少；
* 可以发现更多 rare high-reward trajectory。

但是：

* rollout cost 增加；
* verifier cost 增加；
* batch memory / latency 增加。

---

### Binary Reward 下

如果单 sample success probability：

$$
p
$$

全错概率：

$$
(1-p)^G
$$

全对概率：

$$
p^G
$$

zero-variance probability：

$$
p^G+(1-p)^G
$$

所以增大 \(G\) 能降低中间难度任务的全同 reward 概率。

但如果：

$$
p\approx0
$$

例如：

$$
p=10^{-5}
$$

从：

```text
G=8
```

加到：

```text
G=16
```

仍然很可能全错。

此时真正需要：

* curriculum；
* better exploration；
* data filtering。

---

## 4.23 Binary Reward 下 GRPO 为什么容易出现 Zero Advantage？ `[P1]`

Binary reward：

$$
R_i\in\{0,1\}
$$

如果 prompt 太简单：

$$
R=[1,1,\ldots,1]
$$

如果太难：

$$
R=[0,0,\ldots,0]
$$

都满足：

$$
R_i-\bar R=0
$$

因此：

$$
A_i=0
$$

---

### 为什么不能随便人为给这些 group 非零 advantage？

因为 group-relative 信息本身告诉你的只有：

> 这些 samples 在 group 内没有可区分差异。

强行定义：

```text
全错 → 全负
```

会导致所有 sampled responses 都被 suppress。

但其中可能有：

* 接近正确的 reasoning；
* useful prefix；
* rare exploration。

所以“全错怎么学习”本质上需要更丰富 credit signal，而不只是给 GRPO normalization 打补丁。

---

## 4.24 Token-level Ratio 和 Sequence-level Ratio 有什么区别？ `[P1]`

### Token-level

response：

$$
y=(y_1,\ldots,y_T)
$$

每 token：

$$
r_t
=
\frac{
\pi_\theta(y_t|x,y_{<t})
}{
\pi_{\text{old}}(y_t|x,y_{<t})
}
$$

每 token 各有自己的 importance ratio。

这是 PPO / GRPO 常见形式。

---

### Sequence-level Probability

$$
\pi(y|x)
=
\prod_t
\pi(y_t|x,y_{<t})
$$

log：

$$
\log\pi(y|x)
=
\sum_t
\log\pi(y_t|x,y_{<t})
$$

sequence ratio：

$$
r_{\text{seq}}
=
\frac{
\pi_\theta(y|x)
}{
\pi_{\text{old}}(y|x)
}
$$

直接 product 会随长度快速极端。

因此 GSPO 使用的是基于 sequence log-likelihood 的长度归一化形式，而不是简单裸乘全部 token ratio；其核心思想是让 importance ratio、clipping 和 optimization 都转到 sequence level，更匹配 sequence-level rewards。

---

### 两种粒度的直觉

Token-level：

> 每个 token 判断 current/old policy 偏移。

Sequence-level：

> 整个 response 作为一个 action unit 判断 policy 偏移。

---

## 4.25 Per-token Mean、Per-sequence Mean、Global-token Mean 有什么区别？ `[P1]`

假设 batch 两个 response：

```text
A: 10 tokens
B: 100 tokens
```

每 token policy loss：

$$
\ell_{i,t}
$$

---

### Global Token Mean

$$
L
=
\frac{
\sum_i\sum_t\ell_{i,t}
}{
\sum_iT_i
}
$$

则：

```text
B 有 100 tokens
A 有 10 tokens
```

B 对 batch objective 贡献约 A 的 10 倍 token 权重。

---

### Per-sequence Mean

先：

$$
L_i
=
\frac1{T_i}
\sum_t\ell_{i,t}
$$

再：

$$
L=
\frac1B
\sum_iL_i
$$

每个 response 权重相同。

---

### Group-total Token Mean

还可能：

$$
L
=
\frac{
\sum_{i,t}\ell_{i,t}
}{
\sum_iT_i
}
$$

在 group 层统一 normalization。

---

### 哪个“正确”？

没有脱离 objective 的唯一答案。

你必须问：

> 我希望 optimization unit 是 token、sequence 还是 prompt-group？

这也是 DAPO、GRPO implementation 差异中很重要的一点。

---

## 4.26 为什么 Response Length 会影响 RL Loss？ `[P1]`

假设两个 response reward 都：

$$
R=1
$$

A：

```text
20 tokens
```

B：

```text
200 tokens
```

如果直接 sum token losses：

$$
L_i
=
\sum_t
-A_i\log\pi(y_t)
$$

B 拥有 10 倍 gradient terms。

因此 long response 天然获得更大总梯度。

---

### 反过来 Per-sequence Mean

如果：

$$
L_i
=
\frac1{T_i}
\sum_t
\ell_{i,t}
$$

长 response 每 token 的 contribution 会被平均得更小。

这又可能引入另一种 length bias。

---

### 为什么 reasoning RL 特别敏感？

因为 rollout 长度可能：

```text
200 tokens
到
20,000 tokens
```

长度差距巨大。

所以：

```text
loss aggregation
```

不是无关紧要的代码细节，而是 objective definition 的一部分。

---

# P2

## 4.27 Old Logprob 为什么必须对应真正 Rollout 出来的 Token？ `[P2]`

PPO ratio：

$$
r_t
=
\exp
(
\log\pi_\theta(a_t|s_t)
-
\log\pi_{\text{old}}(a_t|s_t)
)
$$

这里要求：

```text
同一个 state s_t
同一个 sampled action a_t
```

分别由 current 和 old policy 打分。

---

### 如果重新 Tokenize

真正 rollout：

$$
[a_1,a_2,a_3]
$$

decode 成：

$$
"text"
$$

再 encode 得：

$$
[a'_1,a'_2]
$$

此时：

```text
action identity changed
sequence length changed
causal prefixes changed
```

你计算的：

$$
\log\pi_\theta(a'_t|s'_t)
$$

根本不是 rollout 的 action。

---

### 为什么这是数学错误而不仅是工程误差？

Importance Sampling 要求 numerator / denominator 针对同一个随机变量：

$$
\frac{P(A=a)}{Q(A=a)}
$$

如果分母对应：

$$
a
$$

分子对应：

$$
a'
$$

ratio 已经失去 probability-ratio 意义。

---

### 同样不能随便重建 Prompt

若：

```text
chat template
special token
tool observation serialization
```

变化：

$$
s_t'
\neq s_t
$$

则 current logprob 也不是：

$$
\pi_\theta(a_t|s_t)
$$

因此 exact provenance 需要至少控制：

```text
prompt token IDs
response token IDs
response boundaries
observation boundaries
old logprob
sampling configuration
```

---

## 4.28 GRPO Group Normalization 会引入哪些统计问题？ `[P2]`

典型：

$$
A_i
=
\frac{
R_i-\bar R
}{
s_R+\epsilon
}
$$

好处是 reward scale 被自动标准化。

但它引入多个性质。

---

### 1. Advantage 是 Group-dependent

同一个 response reward：

$$
R=1
$$

在：

$$
[1,1,0,0]
$$

中是 positive advantage。

在：

$$
[1,1,1,1]
$$

中：

$$
A=0
$$

所以它的 training signal 取决于：

> 同一个 prompt 其他 samples 恰好生成了什么。

---

### 2. Group Size 影响 Estimator

小 group 的：

$$
\bar R,\quad s_R
$$

noise 较大。

---

### 3. Zero Variance

所有 reward 一样：

$$
s_R=0
$$

整个 group 没信号。

---

### 4. Difficulty Rescaling

假设容易 prompt：

```text
rewards:
[1,1,1,0]
```

困难 prompt：

```text
[1,0,0,0]
```

group normalization 后 rare success / rare failure 可能被赋予很大的标准化 magnitude。

因此 prompt difficulty 被隐式改变权重。

---

### 5. Relative 而非 Absolute Quality

如果：

```text
group A:
[100,99]

group B:
[1,0]
```

标准化后可能产生类似 advantage pattern。

absolute reward scale 信息被消掉。

---

### 所以 Group Normalization 是免费的吗？

不是。

它是：

> 用 group statistics 换掉 learned critic。

消除了 critic training cost，但引入：

* group sampling cost；
* group-statistics noise；
* zero variance；
* group-dependent weighting。

---

## 4.29 Reward Scale / Normalization 会怎样改变训练？ `[P2]`

Vanilla policy gradient：

$$
\nabla J
\propto
A
\nabla\log\pi
$$

如果：

$$
A'=cA
$$

gradient magnitude 也乘：

$$
c
$$

因此 reward scale 和 effective learning rate 存在耦合。

---

### PPO Clipping 下更复杂

虽然 ratio 被 clip，但 advantage magnitude 仍然决定：

$$
rA
$$

的梯度尺度。

所以 reward 从：

```text
0 / 1
```

变：

```text
0 / 100
```

不是完全无影响。

---

### Standardization

常见：

$$
A'
=
\frac{
A-\mu_A
}{
\sigma_A+\epsilon
}
$$

可以稳定 scale。

但也改变跨：

```text
prompt
task
batch
```

的相对 weighting。

---

### Multi-reward 更明显

假设：

```text
correctness ∈ {0,1}
judge score ∈ [0,100]
```

如果不 normalize：

> judge 几乎决定全部 gradient。

所以 reward preprocessing 必须作为 algorithm spec，而不是“实现细节”。

---

## 4.30 DAPO 在 GRPO 上改了什么？ `[P2]`

DAPO：Decoupled Clip and Dynamic sAmpling Policy Optimization。

它不是完全推翻 GRPO，而是针对大规模 long-CoT RL 中观察到的几个具体 failure 做修改。

论文/官方实现总结了四个主要技术：**Clip-Higher、Dynamic Sampling、Token-level Policy Gradient Loss、Overlong Reward Shaping**。

---

### 1. Clip-Higher

普通 PPO/GRPO 常对 ratio 对称 clip：

$$
[1-\epsilon,\;1+\epsilon]
$$

DAPO 将上下界解耦：

$$
[1-\epsilon_{\text{low}},
1+\epsilon_{\text{high}}]
$$

并允许：

$$
\epsilon_{\text{high}}
>
\epsilon_{\text{low}}
$$

直觉：

> 对 positive-advantage、当前低概率但潜在有价值的 token，允许更大的 probability increase。

用于缓解 entropy collapse、促进 exploration。

---

### 2. Dynamic Sampling

如果 group：

```text
all correct
```

或：

```text
all wrong
```

group-relative advantage 没有有效区分。

DAPO 动态 resample/filter，使训练 batch 保留具有 reward variance 的 prompts。

例如 binary reward：

$$
0<
\sum_iR_i
<
G
$$

---

### 代价

这会改变实际进入训练的 prompt distribution。

因此不能只说：

> 它消除 zero gradient，没有任何副作用。

它本身可能引入：

* sampling bias；
* difficulty reweighting；
* 更多 rollout 成本。

---

### 3. Token-level Policy Gradient Loss

DAPO特别关注 long-CoT 下不同 response length 对 loss aggregation 的影响。

其设计把 normalization 放在 group 内所有有效 token 层面，而不是简单地每条 response 先等权平均，从而改变 length weighting。

---

### 4. Overlong Reward Shaping

如果 generation 撞到最大长度：

```text
reasoning unfinished
↓
forced truncation
↓
final answer absent
↓
reward = 0
```

hard cutoff 会制造 noisy reward。

DAPO 在接近 max length 的区域加入 soft length penalty，而不是只在突然截断时产生离散跳变。

---

### 面试一句话

DAPO 不是：

> “更高级的 GRPO”。

更准确是：

> 它针对 GRPO 在 large-scale long-CoT RL 中暴露的 clipping、zero-variance sampling、length normalization 和 truncation reward noise 做了一组系统性修改。

---

## 4.31 GSPO 为什么重新使用 Sequence-level Policy Ratio？ `[P2]`

GSPO：Group Sequence Policy Optimization。

它对 GRPO 的一个关键质疑是：

> Reward 通常定义在整个 sequence 上，但 GRPO/PPO-style update 却使用 token-level importance ratio。

GSPO 改成：

```text
sequence-level likelihood
↓
sequence-level importance ratio
↓
sequence-level clipping
↓
sequence-level optimization
```

论文报告这种 formulation 尤其改善了训练稳定性，并强调其对 MoE RL 的价值。

---

### 为什么 Sequence-level 更自然？

如果 verifier：

```text
整个数学答案 correct / wrong
```

reward：

$$
R(y)
$$

本身就是 sequence-level。

GRPO 却给 sequence 内：

```text
token 1 ratio
token 2 ratio
...
```

分别 clipping。

GSPO 认为：

> optimization unit 应更接近 reward unit。

---

### 但 Sequence Probability 有爆炸问题怎么办？

裸 sequence ratio：

$$
\prod_t r_t
$$

非常不稳定。

因此 sequence likelihood 通常使用 log-space 和长度 normalization。

概念上：

$$
\log r_{\text{seq}}
=
\frac1T
\sum_t
[
\log\pi_\theta(y_t)
-
\log\pi_{\text{old}}(y_t)
]
$$

再 exponentiate。

重点是：

> 把整个 response 的 policy shift 聚合成一个 scalar。

---

## 4.32 GRPO / DAPO / GSPO 的 Token-vs-Sequence Trade-off 是什么？ `[P2]`

可以这样理解：

```text
GRPO
token-level ratio
sequence reward

DAPO
仍保留 token-level optimization
但重新设计 clip / sampling / aggregation

GSPO
直接把 optimization granularity
提升到 sequence level
```

---

### Token-level 优点

可以看到：

```text
同一个 response 中
不同 token 的 policy ratio
```

因此 policy shift 控制更细。

理论上提供 fine-grained optimization。

---

### Token-level 问题

最终 reward：

$$
R_i
$$

通常整条 sequence 共用。

于是：

```text
每个 token
获得相同 outcome advantage
但使用不同 ratio
```

可能出现 token-level clipping 与 sequence-level reward 的 granularity mismatch。

---

### Sequence-level 优点

一个 response：

```text
one reward
one advantage
one ratio
```

语义一致。

并且可以缓解极端 token ratio 对优化的干扰。

---

### Sequence-level 缺点

把：

```text
token-wise probability changes
```

压成一个 scalar。

可能失去：

* token-specific information；
* fine-grained correction。

---

### 所以这不是谁“理论上必胜”

它实际上是：

```text
fine-grained token control
vs
sequence-level statistical stability
```

之间的取舍。

2026 年也已经有工作试图同时组合 token-level 与 sequence-level ratio，正说明这一 granularity 问题仍是活跃研究方向。

---

## 4.33 Off-policy / Stale Rollout 如何破坏 PPO / GRPO？ `[P2]`

假设 rollout：

```text
Policy v1
↓
generation begins
```

与此同时 trainer：

```text
v1 → v2 → v3 → v4
```

最后：

```text
v1 trajectory
```

才返回。

此时：

$$
\pi_{\text{behavior}}
=
\pi_{v1}
$$

current：

$$
\pi_\theta
=
\pi_{v4}
$$

---

### Ratio 可能远离 1

$$
r_t
=
\frac{
\pi_{v4}
}{
\pi_{v1}
}
$$

如果 difference 很大：

* clipping fraction 极高；
* effective gradient 下降；
* importance variance 增加。

---

### GRPO 的 Group 还有额外问题

假设同一 prompt group 中 samples 来自：

```text
v1
v1
v2
v3
```

那么它们：

> 不再是同一个 behavior policy 下的同分布 samples。

group-relative advantage 的统计解释开始变复杂。

---

### 常见处理

```text
policy version tagging
bounded staleness
sync rollout
discard old trajectories
importance correction
replay limits
```

但每种都有 throughput / sample-efficiency trade-off。

---

### 为什么这是系统和算法交叉题？

因为原因可能只是：

```text
tool call 很慢
rollout workers 被卡住
```

最终却导致：

```text
RL data off-policy
```

所以 Agent RL 系统调度会直接改变算法统计性质。

---

## 4.34 如果 Reward 上升但 Pass@1 不升，应该怎样分析？ `[P2]`

这是比“loss 为什么震荡”更有价值的 RL debug 题。

不能回答：

> reward model 不好。

要逐层切。

---

### 第一层：Reward 是否等价于最终 Metric？

例如训练：

$$
R
=
R_{\text{format}}
+
R_{\text{answer}}
$$

但评估只看：

$$
Pass@1
=
answer correctness
$$

模型可能只提高 format reward。

---

### 第二层：Reward Hacking

例如 verifier：

```text
字符串规则漏洞
```

policy 找到高 reward shortcut。

检查：

```text
high-reward trajectories
```

人工 spot-check。

---

### 第三层：Train / Eval Sampling 不同

训练：

```text
temperature = 1.0
G = 16
```

评估：

```text
greedy / low temperature
```

模型可能：

> distribution tail 改善，但 mode 没改善。

表现为：

```text
pass@k ↑
pass@1 ≈
```

---

### 第四层：Reward Distribution

平均 reward 上升可能只是：

```text
easy prompts
```

变得更好。

困难 slice 不变。

必须看：

```text
per difficulty
per domain
per length
```

---

### 第五层：Length / Cost Shortcut

模型可能变得：

```text
更长
更多尝试
```

从而 sampled reward 提高，但 greedy accuracy 不提升。

---

### 第六层：Group-relative Objective

GRPO 优化的是：

> group 内 relative signal。

训练 reward metric 可能和 deployment policy metric 不完全一致。

---

### 第七层：Evaluation Noise

如果 benchmark 很小：

```text
AIME-like small test set
```

几个题就能大幅改变百分比。

需要：

* multiple seeds；
* confidence interval；
* more benchmarks。

---

### 最终 Debug Tree

```text
Reward ↑
Pass@1 ↔
   │
   ├── objective mismatch?
   │
   ├── reward hacking?
   │
   ├── sampling mismatch?
   │
   ├── pass@k improved?
   │
   ├── only easy slices improved?
   │
   ├── length changed?
   │
   ├── verifier bug?
   │
   └── evaluation variance?
```

---

# 4.35 PPO / GRPO 完整数据流

必须能脱离框架画出：

```text
Prompt x
   ↓
Behavior Policy πold
   ↓
Sample Response y
   │
   ├────────────→ old logprobs
   │
   ↓
Reward / Verifier
   ↓
R
   │
   ├── PPO:
   │      critic
   │        ↓
   │      GAE
   │        ↓
   │      A_t
   │
   └── GRPO:
          same-prompt group rewards
                   ↓
           mean / std
                   ↓
                  A_i
```

训练：

```text
same exact response tokens
        ↓
Current Policy πθ
        ↓
current logprobs
        │
        ├──────── old logprobs
        │              ↓
        │        importance ratio
        │
        └──────────────┘
                ↓
              clip
                ↓
          policy objective
                │
                ├──── optional reference logprobs
                │                ↓
                │               KL
                │
                └────────────────┘
                ↓
              loss
                ↓
             backward
                ↓
          optimizer.step
```

注意三个 logprob：

```text
current_logprob
old_logprob
reference_logprob
```

绝对不能混。

---

# 4.36 RLHF / DPO / RLVR 对照表

| 维度                      | PPO-RLHF       | DPO                        | GRPO / RLVR                 |
| ----------------------- | -------------- | -------------------------- | --------------------------- |
| 数据                      | Online rollout | Offline preference pairs   | Online/group rollout        |
| Reward                  | Learned RM     | Implicit preference reward | 常为 verifier / rule          |
| Critic                  | 通常有            | 无                          | 标准 GRPO 无                   |
| Reference               | 常有             | 有                          | 常有/依实现                      |
| Old policy              | 有              | 不以 PPO ratio 形式使用          | 有                           |
| Exploration             | Online         | 有限                         | Online                      |
| Environment interaction | 可以             | 不自然                        | 可以                          |
| 系统复杂度                   | 高              | 低                          | 中高                          |
| 典型用途                    | alignment      | preference alignment       | reasoning / RLVR / Agent RL |

---

# 4.37 高频连环追问

## 第一组：RLHF

```text
RLHF pipeline？
↓
为什么先 SFT？
↓
Preference Data 怎么来？
↓
Reward Model 怎么训？
↓
Bradley–Terry 是什么？
↓
RM 为什么会 reward hacking？
↓
为什么还需要 reference KL？
```

---

## 第二组：DPO

```text
DPO 是什么？
↓
为什么可以不要显式 Reward Model？
↓
DPO objective 写出来？
↓
reference policy 在里面干什么？
↓
β 控制什么？
↓
DPO 为什么不是普通 SFT？
↓
为什么 Agent RL 不一定适合只用 DPO？
```

---

## 第三组：PPO

```text
为什么需要 old policy？
↓
importance ratio 是什么？
↓
为什么不是 probability difference？
↓
clip 的是什么？
↓
A>0 怎么 clip？
↓
A<0 怎么 clip？
↓
为什么 clip 不等于真正 trust region？
```

---

## 第四组：Old vs Reference

```text
old policy 是谁？
↓
reference policy 是谁？
↓
为什么不能用 reference logprob 当 old logprob？
↓
为什么不能用 old policy 代替长期 reference？
↓
current / old / reference 三个 checkpoint 生命周期分别是什么？
```

---

## 第五组：GRPO

```text
GRPO 为什么不需要 critic？
↓
group advantage 怎么算？
↓
为什么 group size 重要？
↓
全对 / 全错会怎样？
↓
binary reward 为什么容易 zero variance？
↓
dynamic sampling 可以怎么处理？
```

---

## 第六组：Length

```text
200-token 和 2000-token response
谁 gradient 更大？
↓
取决于 loss aggregation
↓
token mean / sequence mean 区别？
↓
为什么会 length bias？
↓
DAPO 怎么重新考虑这个问题？
```

---

# 4.38 Self-test

## Self-test 1：PPO Ratio

给：

$$
\log p_\theta=-2
$$

$$
\log p_{\text{old}}=-2.2
$$

则：

$$
r
=
e^{0.2}
\approx1.221
$$

如果：

$$
\epsilon=0.2
$$

则 ratio 已稍微超过：

$$
1.2
$$

positive-advantage 更新会进入 upper clipping region。

---

## Self-test 2：Negative Advantage

给：

$$
A=-2
$$

$$
r=0.5
$$

$$
\epsilon=0.2
$$

unclipped：

$$
rA=-1
$$

clipped：

$$
0.8(-2)=-1.6
$$

PPO objective 取：

$$
\min(-1,-1.6)
=
-1.6
$$

所以不会继续奖励把坏 action probability 从 0.8 再降到 0.5。

---

## Self-test 3：GRPO

Rewards：

$$
[1,1,0,0]
$$

mean：

$$
0.5
$$

population std：

$$
0.5
$$

advantage：

$$
[1,1,-1,-1]
$$

---

## Self-test 4：Zero Variance

Rewards：

$$
[0.8,0.8,0.8,0.8]
$$

则：

$$
R_i-\bar R=0
$$

即使 absolute reward：

$$
0.8
$$

很高，也没有 group-relative gradient。

---

## Self-test 5：Old vs Reference

若：

```text
Reference = SFT checkpoint
Old = RL step 1000 checkpoint
Current = RL step 1005 checkpoint
```

则：

```text
current / old
→ PPO ratio

current / reference
→ KL regularization
```

不能反过来。

---

# 4.39 推导题

## 推导题 1：PPO Ratio 的 Logprob 形式

从：

$$
r
=
\frac{
\pi_\theta(a|s)
}{
\pi_{\text{old}}(a|s)
}
$$

取 log：

$$
\log r
=
\log\pi_\theta
-
\log\pi_{\text{old}}
$$

所以：

$$
r
=
\exp
(
\log\pi_\theta
-
\log\pi_{\text{old}}
)
$$

---

## 推导题 2：DPO Implicit Reward

从：

$$
\pi^*(y|x)
\propto
\pi_{\text{ref}}(y|x)
e^{r(x,y)/\beta}
$$

得到：

$$
r(x,y)
=
\beta
\log
\frac{
\pi^*(y|x)
}{
\pi_{\text{ref}}(y|x)
}
+
C(x)
$$

再对 winner / loser 相减，消除：

$$
C(x)
$$

得到 DPO pairwise log-ratio。

---

## 推导题 3：Binary GRPO Zero-variance Probability

若单 rollout success probability：

$$
p
$$

group size：

$$
G
$$

全对：

$$
p^G
$$

全错：

$$
(1-p)^G
$$

所以 zero-variance probability：

$$
P_{\text{zero}}
=
p^G+(1-p)^G
$$

解释为什么：

```text
p≈0.5
```

时 group 最有信息；

而：

```text
p≈0 或 1
```

时 group rollout 浪费严重。

---

# 4.40 Debug 题

## Debug 1：Approx KL 突然爆炸

检查：

```text
learning rate
policy epochs
clip range
advantage magnitude
old logprob correctness
token alignment
stale rollout
sampling mismatch
```

尤其：

> old logprob 错位

会直接制造假的巨大 ratio。

---

## Debug 2：所有 Ratio 几乎都等于 1

可能：

```text
policy 根本没更新
```

也可能：

```text
current logprob
和
old logprob

错误地来自同一个 forward / checkpoint
```

必须查 provenance。

---

## Debug 3：GRPO Loss 接近 0

检查：

```text
reward variance
group all correct?
group all wrong?
response mask?
advantages zero?
all ratios clipped?
```

不能看到：

```text
loss ≈ 0
```

就说收敛。

---

## Debug 4：训练后 Response 越来越长

检查：

```text
reward length bias
loss aggregation
verifier bias
truncation behavior
KL
EOS probability
overlong handling
```

不是第一反应：

> max_new_tokens 调小。

那只是截断症状。

---

## Debug 5：Training Reward 上升但 Entropy 快速下降

可能：

```text
exploration collapse
upper clipping 太保守
reward 过于尖锐
temperature mismatch
positive samples 太集中
```

需要联合看：

```text
entropy
clip fraction
reward
pass@k
response diversity
```

---

# 4.41 系统设计题

## 系统设计题 1：如果你只有 24GB GPU，为什么 GRPO 比 PPO 可能更现实？

PPO 可能需要：

```text
actor
critic
reference
rollout model
```

即使部分共享/offload，critic 仍增加参数和 optimizer state。

GRPO：

```text
actor
reference
```

并用 group rollout 替代 learned critic。

因此：

```text
critic memory ↓
但 rollout compute ↑
```

这是：

> 显存换 rollout 成本。

不是免费降成本。

---

## 系统设计题 2：如果 70% Prompt 的 Group 都是全错怎么办？

不要只增大 \(G\)。

可以分层讨论：

```text
数据：
curriculum / easier tasks

探索：
temperature / entropy / better initialization

采样：
dynamic sampling

模型：
先 SFT / bootstrap

Reward：
process signal / dense verifier

经验：
reuse successful trajectories
```

先判断：

> 模型完全不会，还是 sampling 没找到？

这是两个问题。

---

## 系统设计题 3：如果 Tool Agent 的 Reward 只有最终 EM，应该 PPO 还是 GRPO？

不能凭算法名字选。

应该问：

```text
是否有 critic/value target？
每 prompt 能否 afford 多 rollout？
reward variance 如何？
trajectory 是否很长？
environment cost 多高？
group sampling 是否昂贵？
```

如果：

```text
tool calls very expensive
```

那么 GRPO 每 prompt：

$$
G=16
$$

可能比 critic 更贵。

所以：

> critic-free 不等于 system-cost-free。

---

# 4.42 Macro 4 最小知识图

最终要形成：

```text
Human / AI Preferences
         │
         ↓
   Pairwise Dataset
         │
    ┌────┴──────────────┐
    │                   │
Reward Model           DPO
    │                   │
    ↓                   ↓
Scalar Reward      Direct Preference
    │                Objective
    ↓
   PPO
```

PPO：

```text
Rollout with πold
       ↓
response + old logprobs
       ↓
reward
       ↓
critic / GAE
       ↓
advantage
       ↓
current logprobs
       ↓
ratio πθ / πold
       ↓
clipping
       │
       ├── reference KL
       │
       ↓
policy loss
```

GRPO：

```text
Prompt
  ↓
πold samples G responses
  ↓
R1 R2 R3 ... RG
  ↓
group mean / std
  ↓
relative advantages
  ↓
current / old ratio
  ↓
clipped policy optimization
  │
  ├── optional / configured reference KL
  ↓
optimizer
```

然后是当前 reasoning-RL 的几个演化方向：

```text
GRPO
 │
 ├── zero-variance groups
 │       ↓
 │   Dynamic Sampling
 │
 ├── entropy collapse / clipping
 │       ↓
 │    Clip-Higher
 │
 ├── response length / loss aggregation
 │       ↓
 │      DAPO
 │
 └── token-level ratio
         ↓
       GSPO
         ↓
sequence-level optimization
```

其中需要记住一个原则：

> **这些算法真正的区别，不是 acronym，而是它们分别选择了什么 optimization unit、什么 behavior distribution、什么 advantage estimator、什么 normalization、什么 clipping granularity。**

能把下面这条链无停顿讲通：

$$
\text{Preference}
\rightarrow
\text{Reward}
\rightarrow
\text{Advantage}
\rightarrow
\text{Old Policy}
\rightarrow
\text{Importance Ratio}
\rightarrow
\text{Clipping}
\rightarrow
\text{Reference KL}
\rightarrow
\text{Policy Update}
$$

Macro 4 才算真正掌握。

下一章 Macro 5 会把这里默认的：

```text
prompt
→ response
→ reward
```

升级成：

```text
prompt
→ generation
→ tool action
→ observation
→ generation
→ tool action
→ observation
→ ...
→ final reward
```

也就是从 **LLM RL** 正式进入 **Agentic RL**。

## 5. Agentic RL / Trajectory / Tool-use Learning

普通 response-level RL 可以近似写成：

```text
prompt
  ↓
model response
  ↓
reward
```

但真正的 Agentic RL 是：

```text
task
 ↓
reason / action
 ↓
environment
 ↓
observation
 ↓
reason / action
 ↓
environment
 ↓
observation
 ↓
...
 ↓
final answer
 ↓
reward
```

区别不是“多调用几次模型”这么简单。

一旦存在外部环境，多出来的问题包括：

```text
哪些 token 是模型生成的？
哪些 token 是环境注入的？
一个 turn 和一个 generation 是否相同？
old logprob 应该记录在哪里？
tool observation 是否计算 policy loss？
失败的 tool call 是 policy failure 还是 environment failure？
中途 timeout 的 trajectory 要不要训练？
async rollout 返回时 policy 已经更新怎么办？
```

因此 Agentic RL 的核心不只是新的 RL loss，而是：

> **把真实多轮交互准确表示成 training-ready trajectory。**

---

## 5.0 问题矩阵

| 编号   | 问题                                                               | 等级 |
| ---- | ---------------------------------------------------------------- | -- |
| 5.1  | Episode、Trajectory、Turn、Step、Generation、Action、Observation 怎么区分？ | P0 |
| 5.2  | 单轮 LLM RL 与 Multi-turn Agent RL 的本质区别是什么？                        | P0 |
| 5.3  | Action Protocol 为什么是 Agent Runtime 和训练系统的一部分？                    | P0 |
| 5.4  | Tool Observation 为什么通常不能直接计算 Policy Loss？                        | P0 |
| 5.5  | Agent rollout 的常见 termination condition 有哪些？                     | P0 |
| 5.6  | Environment Failure 和 Policy Failure 有什么区别？                      | P0 |
| 5.7  | 为什么 Group Rollout 中失败 sample 不能随便删除？                             | P0 |
| 5.8  | 什么是 Generation / Token Provenance？                               | P0 |
| 5.9  | 为什么不能 decode 后再 tokenize 恢复 response token IDs？                  | P1 |
| 5.10 | Multi-turn Agent 为什么不能简单看成一条普通 flat sequence？                    | P1 |
| 5.11 | Tool Observation 插回 Context 后，下一轮的 causal boundary 怎么定义？         | P1 |
| 5.12 | Response Mask、Observation Mask、Step Mapping 分别解决什么？              | P1 |
| 5.13 | Per-turn Generation Record 为什么比只保存最终 Trajectory Text 更可靠？        | P1 |
| 5.14 | Sampling Seed 应该在哪些粒度记录？                                         | P1 |
| 5.15 | Behavior Policy / Policy Version 为什么在 Agent RL 中特别重要？            | P1 |
| 5.16 | Variable-horizon Trajectory 怎样 batch 和 mask？                     | P1 |
| 5.17 | Invalid Action / Parser Failure 应该怎样建模？                          | P1 |
| 5.18 | Tool Result 应该保存什么 Provenance？                                   | P1 |
| 5.19 | 多轮 Agent 的“连续 Token 语义”到底是什么？                                    | P2 |
| 5.20 | Async Rollout 怎样破坏严格 On-policy 假设？                               | P2 |
| 5.21 | Partial / Cancelled / Timeout Trajectory 应不应该进入训练？               | P2 |
| 5.22 | 怎样区分“模型不会”与“环境不给它成功机会”？                                          | P2 |
| 5.23 | Failure Propagation 为什么让 Long-horizon Credit Assignment 更难？      | P2 |
| 5.24 | Agent RL 中怎样定义 training-ready trace 的最小 invariant？               | P2 |
| 5.25 | 多个 Generation Turn 的 old logprob 应该怎样与最终 flattened sequence 对齐？  | P2 |
| 5.26 | 如果 Tool Observation 很长，Context Growth 会怎样影响训练与 rollout？          | P2 |

---

# P0

## 5.1 Episode、Trajectory、Turn、Step、Generation、Action、Observation 怎么区分？ `[P0]`

这些词不同框架可能命名不同，因此面试时不要死背类名，要讲清楚语义。

---

### Episode

一次完整任务尝试。

例如：

```text
Question:
Who founded company X and where did she study?

↓
Agent starts

Search
Visit
Search
Answer

↓
Task ends
```

从 reset 到任务结束可以叫：

$$
Episode
$$

---

### Trajectory

记录这个 episode 中实际发生的交互序列。

例如：

$$
\tau
=
(a_0,o_0,a_1,o_1,\ldots,a_T)
$$

如果保留更完整状态：

$$
\tau
=
(s_0,a_0,r_0,s_1,\ldots)
$$

工程上 trajectory 往往是 episode 的具体执行记录。

---

### Turn

一轮 Agent 决策。

例如：

```text
LLM sees context
↓
generates one action
↓
environment returns observation
```

可以视为一个 turn。

---

### Generation

一次实际模型生成调用。

例如：

```text
messages
↓
LLM.generate()
↓
<think>...</think>
<search>...</search>
```

这就是一次 generation。

一个 turn 通常对应一次 generation，但不是数学上的必然。

例如某些系统可能：

```text
planner generation
↓
executor generation
```

两个 generation 才构成一个逻辑 turn。

---

### Action

模型对环境执行的动作。

例如：

```text
Search("OpenAI founders")
Visit(document_id=12)
Answer("...")
```

Action 不一定等于整段模型输出。

模型输出可能包含：

```text
reasoning
+
structured action
```

---

### Observation

环境执行 action 后返回给 Agent 的信息。

例如：

```text
Search(...)
↓
Top-5 documents

Visit(...)
↓
document content

Python(...)
↓
stdout
```

---

### Step

最容易歧义。

某些框架：

```text
Step = Action + Observation
```

另一些：

```text
Step = one state transition
```

还有的：

```text
Step = one generation
```

所以设计数据结构时应该明确定义，而不是假设所有论文/框架相同。

---

### 推荐的概念层次

```text
Episode
└── Trajectory
    ├── Turn 0
    │   ├── Generation 0
    │   ├── Action 0
    │   └── Observation 0
    │
    ├── Turn 1
    │   ├── Generation 1
    │   ├── Action 1
    │   └── Observation 1
    │
    └── Turn 2
        ├── Generation 2
        └── Final Answer
```

---

## 5.2 单轮 LLM RL 与 Multi-turn Agent RL 的本质区别是什么？ `[P0]`

### 单轮 Response RL

```text
prompt x
↓
policy π
↓
response y
↓
reward R(x,y)
```

模型生成结束后，环境才给 reward。

中间没有新的外部 observation。

---

### Multi-turn Agent RL

```text
state s0
↓
action a0
↓
environment
↓
observation o0
↓
state s1
↓
action a1
↓
environment
↓
observation o1
...
```

当前 action 会改变未来 context。

即：

$$
a_t
\rightarrow
o_t
\rightarrow
s_{t+1}
$$

---

### 最核心差异

单轮：

> response 内 token 主要改变后续 token prefix。

Agent：

> action 不仅改变 token prefix，还改变外部环境返回的信息。

例如：

```text
Search query A
↓
retrieve document A
↓
next reasoning sees document A
```

如果第一轮 query 换成 B：

```text
Search query B
↓
retrieve document B
↓
后续 state 整体变化
```

所以环境 transition 真正进入训练问题。

---

### 这带来什么？

至少增加：

```text
environment stochasticity
tool failures
variable horizon
partial observability
delayed credit
observation masking
async execution
```

因此 Agentic RL 不能只是：

> 对长一点的 response 做 GRPO。

---

## 5.3 Action Protocol 为什么是 Agent Runtime 和训练系统的一部分？ `[P0]`

模型原始输出是文本：

```text
I should search the web for...
```

环境真正需要的是机器可执行 action：

```json
{
  "tool": "search",
  "query": "..."
}
```

因此中间需要：

```text
Model Output
↓
Parser
↓
Validated Action
↓
Tool
```

---

### Action Protocol 决定 Action Space

例如协议：

```text
<search>query</search>
<visit>doc_id</visit>
<answer>text</answer>
```

模型可以选择的 action 就受协议定义。

---

### 为什么不是纯工程细节？

如果 parser 不同：

```text
<Search>abc</Search>
```

有的 parser 接受，有的不接受。

那么同一模型输出可能：

```text
runtime A:
valid action

runtime B:
invalid action
```

Reward 和 trajectory 直接改变。

---

### 训练时还涉及 Action Identity

如果模型生成：

```text
<think>...</think>
<search>abc</search>
```

真正 environment action 只是：

```text
Search("abc")
```

但 policy-generated token 包括整个 response。

所以要区分：

```text
generation
≠
parsed action
```

---

### 常见协议形式

```text
free-form text
JSON
XML-like tags
function calling
grammar-constrained decoding
```

trade-off：

| 形式                  | 优点   | 问题                       |
| ------------------- | ---- | ------------------------ |
| Free-form           | 灵活   | 难解析                      |
| JSON                | 清晰   | 格式容易错                    |
| XML tags            | 简单   | escaping / malformed     |
| Function calling    | 结构化  | 依赖模型/backend             |
| Grammar constrained | 高合法率 | 限制 decoding / backend 复杂 |

---

## 5.4 Tool Observation 为什么通常不能直接计算 Policy Loss？ `[P0]`

这是 Agent RL 最核心的 mask 问题之一。

假设：

```text
Assistant:
<search>capital of France</search>

Tool:
Paris is the capital of France.

Assistant:
<answer>Paris</answer>
```

整条 context 中：

```text
<search>...</search>
```

是 policy 生成。

但：

```text
Paris is the capital of France.
```

是环境注入。

---

### Policy Gradient 优化的是谁？

目标：

$$
\nabla_\theta
\log\pi_\theta(a_t|s_t)
$$

只有 policy 自己选择的 action 才有：

$$
\pi_\theta(a_t|s_t)
$$

Tool observation：

$$
o_t
$$

来自环境 transition：

$$
P(o_t|s_t,a_t)
$$

不是模型 action。

---

### 因此

Observation token：

```text
应该进入未来 context
```

但：

```text
不应该作为 policy-generated response token
```

通常：

$$
mask_t=0
$$

---

### 核心区别

```text
visible to attention
≠
generated by policy
≠
eligible for policy loss
```

---

### 如果错误地训练 Observation Token 会怎样？

等价于让模型学习：

> “我应该生成搜索引擎返回的网页内容。”

这既不是实际 action，也没有对应 behavior-policy sampling probability。

PPO ratio 也失去意义。

---

## 5.5 Agent Rollout 的常见 Termination Condition 有哪些？ `[P0]`

Agent trajectory 不会无限运行。

常见结束条件：

### 1. Explicit Final Answer

模型：

```text
Answer(...)
```

任务自然结束。

---

### 2. Goal Achieved

环境检测：

```text
unit test passed
target state reached
```

直接结束。

---

### 3. Max Steps

例如：

$$
T_{\max}=10
$$

达到 budget 后强制停止。

---

### 4. Token Budget

累计：

```text
generated tokens
+
observation tokens
```

达到限制。

---

### 5. Tool Budget

例如：

```text
max_search_calls = 5
```

---

### 6. Timeout

wall-clock 超限：

```text
120 s
```

---

### 7. Fatal Invalid Action

例如连续输出：

```text
malformed JSON
```

超过 retry limit。

---

### 8. Environment Failure

例如：

```text
browser crashed
sandbox unavailable
```

系统无法继续。

---

### Terminal vs Truncation

最好区分：

```text
task naturally finished
```

与：

```text
system forced stop
```

因为训练语义不同。

---

## 5.6 Environment Failure 和 Policy Failure 有什么区别？ `[P0]`

### Policy Failure

模型本身做错决策。

例如：

```text
错误 search query
错误 tool
错误 argument
错误答案
重复搜索
```

---

### Environment Failure

模型动作合理，但外部系统没正常执行。

例如：

```text
HTTP timeout
search API 500
browser crash
network disconnect
rate limit
document service unavailable
```

---

### 为什么必须分？

假设模型做：

```text
Search("correct query")
```

但 backend timeout。

如果直接：

```text
final reward = 0
```

并把全部 negative advantage 归给 policy：

模型学到：

> 这个正确 query 是坏 action。

产生错误 credit。

---

### Semantic Failure

还有第三类：

```text
tool executed successfully
but returned misleading / stale / irrelevant information
```

这不是 execution failure。

所以最好拆：

```text
Policy failure
Execution failure
Semantic environment failure
```

---

### Training Pipeline 应该记录

例如：

```text
status = SUCCESS
status = INVALID_ACTION
status = TIMEOUT
status = NOT_FOUND
status = TRANSIENT_ERROR
```

不要所有异常统一：

```text
reward = 0
```

之后完全无法诊断。

---

## 5.7 为什么 Group Rollout 中失败 Sample 不能随便删除？ `[P0]`

假设同一 prompt：

```text
rollout 0 → success, reward 1
rollout 1 → wrong answer, reward 0
rollout 2 → timeout
rollout 3 → wrong answer, reward 0
```

如果把 timeout sample 删除：

原 group：

$$
G=4
$$

变成：

$$
G=3
$$

---

### 问题一：Group Statistics 变了

GRPO advantage：

$$
A_i
=
\frac{
R_i-\mu_G
}{
\sigma_G
}
$$

删除一个 sample 会改变：

$$
\mu_G,\sigma_G
$$

其他 sample 的 advantage 也变。

---

### 问题二：Selection Bias

如果：

> 只删除失败的 rollout

训练数据会系统性偏向：

```text
执行成功的 sample
```

甚至可能把真正困难 action 排除。

---

### 问题三：Failure 可能和 Policy 有关

timeout 可能因为：

```text
模型生成超长 query
```

或者：

```text
反复调用昂贵工具
```

这本身是 policy behavior。

如果统一删掉，就看不到这种负面行为。

---

### 那应该怎么办？

先 classify：

```text
policy-caused failure?
environment-caused failure?
infrastructure-caused failure?
```

再决定：

* reward；
* mask；
* drop；
* retry；
* preserve group slot。

不能：

```text
except Exception:
    continue
```

直接把 trajectory 从数据中消失。

---

## 5.8 什么是 Generation / Token Provenance？ `[P0]`

Generation Provenance 回答：

> 这一段 policy-generated tokens 到底是怎样被哪个模型，在什么上下文和 sampling 条件下生成出来的？

至少包括：

```text
model / checkpoint
tokenizer
chat template
prompt token IDs
response token IDs
response old logprobs
sampling params
sampling seed
finish reason
policy version
```

---

### 为什么重要？

因为训练时需要重新计算：

$$
\log\pi_\theta(a_t|s_t)
$$

并和 rollout 时：

$$
\log\pi_{\text{old}}(a_t|s_t)
$$

对齐。

如果不知道：

```text
exact prompt IDs
exact response IDs
```

无法保证是在打分同一个 action。

---

### String Provenance 不够

只保存：

```text
assistant_text
```

可能无法恢复：

* exact tokens；
* special tokens；
* generation boundary；
* old logprobs；
* tokenizer version。

因此：

```text
text trace
```

适合展示。

```text
token-level generation record
```

才适合训练。

---

# P1

## 5.9 为什么不能 Decode 后再 Tokenize 恢复 Response Token IDs？ `[P1]`

已经在 Macro 1 讲过 tokenizer 的基本问题，这里从 RL 角度再看。

假设真实 rollout：

$$
a=(101,245,999)
$$

old logprobs：

$$
(-0.1,-1.2,-0.7)
$$

decode：

```text
"some text"
```

再 encode：

$$
a'=(101,5012)
$$

---

### 问题一：Token 数不同

old logprobs 长度：

$$
3
$$

new response token length：

$$
2
$$

直接无法一一对应。

---

### 问题二：Prefix 变了

原：

$$
p(a_3|a_1,a_2)
$$

重 tokenize：

$$
p(a'_2|a'_1)
$$

是不同条件概率。

---

### 问题三：Importance Ratio 失效

真正需要：

$$
\frac{
\pi_\theta(a_t|s_t)
}{
\pi_{\text{old}}(a_t|s_t)
}
$$

但你得到：

$$
\frac{
\pi_\theta(a'_j|s'_j)
}{
\pi_{\text{old}}(a_t|s_t)
}
$$

不再是同一个随机变量。

---

### 工程原则

如果训练需要 token-level RL：

> 在 generation time 直接保存 actual token IDs。

而不是之后“尽量恢复”。

---

## 5.10 Multi-turn Agent 为什么不能简单看成一条普通 Flat Sequence？ `[P1]`

表面上可以 flatten：

```text
Prompt
Assistant Action 1
Tool Observation 1
Assistant Action 2
Tool Observation 2
Assistant Answer
```

拼成：

$$
x_{1:T}
$$

但训练语义并不统一。

---

### 类型一：Prompt Tokens

来自 task/environment：

```text
mask = 0
```

---

### 类型二：Policy-generated Tokens

例如：

```text
Assistant Action 1
Assistant Action 2
Assistant Answer
```

这些有：

$$
old\ logprob
$$

可以进入 policy loss。

---

### 类型三：Environment Observation Tokens

例如：

```text
Tool Observation 1
```

虽然后续 generation 能看到：

$$
attention-visible
$$

但没有：

$$
behavior policy logprob
$$

因此：

```text
loss mask = 0
```

---

### 类型四：Template / Separator Tokens

例如：

```text
<tool>
</tool>
<assistant>
```

它们可能：

* template 自动插入；
* model 生成；
* environment serialization 插入。

必须明确 provenance。

---

### 所以 Flat Tensor 可以存在

例如：

```text
input_ids
```

最终当然可以是一个 flat tensor。

但还必须附带：

```text
response_mask
step_ids
source/provenance
old_logprobs
```

否则“flat sequence”丢失训练语义。

---

## 5.11 Tool Observation 插回 Context 后，下一轮 Causal Boundary 怎么定义？ `[P1]`

假设：

```text
Prompt P
↓
Generation A1
↓
Observation O1
↓
Generation A2
```

第二轮 policy 实际条件是：

$$
\pi_\theta
(
A_2
|
P,A_1,O_1
)
$$

所以：

```text
O1
```

虽然不属于 policy action，

却属于：

$$
A_2
$$

的 causal context。

---

### 关键点

对于 A2 token：

```text
它应该能够 attention：
P
A1
O1
A2 prefix
```

但 loss 只作用在：

```text
A2 tokens
```

---

### 这形成一个很重要的区分

$$
\text{conditioning tokens}
\supset
\text{loss-bearing tokens}
$$

也就是说：

> loss-bearing token 是 conditioning sequence 的子集。

---

### 为什么不能把 O1 完全 mask 掉 Attention？

如果 observation 在 attention 里不可见：

> Agent 下一轮根本无法利用工具结果。

所以：

```text
attention mask = visible
loss mask = zero
```

可以同时成立。

---

## 5.12 Response Mask、Observation Mask、Step Mapping 分别解决什么？ `[P1]`

假设 flatten：

```text
[P][A1][O1][A2][O2][A3]
```

总 token 数：

$$
T
$$

---

### Response Mask

定义：

$$
m_t=
\begin{cases}
1,&\text{policy-generated}\\
0,&\text{otherwise}
\end{cases}
$$

例如：

```text
P   0000
A1  111
O1  00000
A2  1111
O2  000
A3  111
```

用于：

* policy loss；
* KL；
* old/current logprob alignment。

---

### Observation Mask

可能显式保存：

$$
o_t\in\{0,1\}
$$

标记环境注入 token。

用途：

* debug；
* provenance；
* context-cost 分析；
* future specialized weighting。

严格来说，如果 response mask 已经足够，observation mask 不一定数学上必需，但工程上很有价值。

---

### Step Mapping

例如：

```text
token position:
0 1 2 3 4 5 6 7 ...

step id:
- - 0 0 - - 1 1 ...
```

说明每个 generated token 属于哪个 turn/step。

用途：

* turn-level credit；
* fatal masking；
* step reward；
* retrospective critic；
* trajectory visualization。

---

### 没有 Step Mapping 会怎样？

如果 future algorithm 给：

```text
turn 2 weight = 0.3
```

你不知道应该乘到哪些 token。

所以：

```text
trajectory-level metadata
```

最终必须映射到：

```text
token-level objective
```

---

## 5.13 Per-turn Generation Record 为什么比只保存最终 Trajectory Text 更可靠？ `[P1]`

Multi-turn rollout 的每次 generation context 都不同。

例如：

### Turn 0

$$
P_0=P
$$

生成：

$$
A_0
$$

---

### Turn 1

$$
P_1=
P+A_0+O_0
$$

生成：

$$
A_1
$$

---

### Turn 2

$$
P_2=
P+A_0+O_0+A_1+O_1
$$

生成：

$$
A_2
$$

所以每轮真正发生的是：

```text
GenerationRecord 0:
prompt_ids_0
response_ids_0
old_logprobs_0

GenerationRecord 1:
prompt_ids_1
response_ids_1
old_logprobs_1

GenerationRecord 2:
prompt_ids_2
response_ids_2
old_logprobs_2
```

---

### 只保存最终文本有什么问题？

最终文本：

```text
P A0 O0 A1 O1 A2
```

无法直接证明：

* Turn 1 当时 exact prompt 是什么；
* chat template 当时如何 serialize；
* old logprob 是否对齐；
* observation 是否被 backend 改写；
* tool result 是否被 truncate。

---

### Per-turn Record 的价值

它是：

> execution-time ground truth。

最终 flattened training trace 可以从这些 records 派生。

而不是反过来：

> 从 flattened text 猜每轮发生过什么。

---

## 5.14 Sampling Seed 应该在哪些粒度记录？ `[P1]`

一个 Agent experiment 可能有：

```text
task seed
rollout seed
generation-turn seed
environment seed
```

---

### Dataset / Task Seed

控制：

* task sampling；
* dataset shuffle。

---

### Rollout Seed

同一 prompt 生成多个 group samples：

```text
sample 0
sample 1
sample 2
```

应该可区分。

例如：

$$
seed=f(task,rollout\_id)
$$

---

### Generation-turn Seed

同一 trajectory 多轮生成：

```text
turn 0
turn 1
turn 2
```

如果 backend 支持 per-request generator，可以进一步：

$$
seed=f(task,rollout,turn)
$$

---

### Environment Seed

simulator 可能也有随机性：

```text
retrieval tie-breaking
fault injection
environment stochasticity
```

需要独立控制。

---

### 为什么不能所有地方都 seed=42？

并行 rollout：

```text
sample 0 seed 42
sample 1 seed 42
sample 2 seed 42
```

如果 prompt 相同，可能导致：

> 多个 rollout 完全一样。

group diversity 直接消失。

---

### 推荐原则

```text
global experiment seed
        ↓
deterministically derive
        ↓
task / rollout / turn / environment sub-seeds
```

这样：

* 可复现；
* 不重复；
* 不依赖调度顺序。

---

## 5.15 Behavior Policy / Policy Version 为什么在 Agent RL 中特别重要？ `[P1]`

对每条 trajectory，需要知道：

> 它到底是哪个 policy version 生成的。

例如：

```text
trajectory #1002
policy_version = checkpoint_1200
```

训练时 current 已经：

```text
checkpoint_1237
```

那么：

$$
\pi_{\text{behavior}}
\neq
\pi_{\text{current}}
$$

---

### 为什么 Agent 特别容易 stale？

因为 trajectory latency 很长。

普通 response：

```text
5 s generation
```

Agent：

```text
LLM generation
↓
Search API 3 s
↓
LLM
↓
Browser 10 s
↓
LLM
...
```

一条 trajectory 可能几十秒甚至几分钟。

与此同时 trainer 仍可能继续更新。

---

### 所以至少要保存

```text
policy_version
checkpoint identity
old logprobs
```

才能判断：

* rollout age；
* staleness；
* behavior/current difference。

---

### Policy Version 和 Model Name 不一样

下面不够：

```text
model = Qwen-3B
```

需要更具体：

```text
policy_version = optimizer_step_4500
```

因为两个都是：

```text
Qwen-3B
```

但参数不同。

---

## 5.16 Variable-horizon Trajectory 怎样 Batch 和 Mask？ `[P1]`

假设：

```text
Trajectory A: 100 response tokens
Trajectory B: 500 response tokens
Trajectory C: 50 response tokens
```

组成 batch 时需要 pad：

```text
A: [tokens........][PAD.............]
B: [tokens..........................]
C: [tokens...][PAD..................]
```

---

### 至少有两类 Mask

#### Attention / Padding Mask

避免模型读 padding。

#### Policy / Response Mask

只对 policy-generated valid response token 计算 loss。

例如：

$$
m_{i,t}
$$

---

### Loss

per-sequence：

$$
L_i
=
\frac{
\sum_t
m_{i,t}\ell_{i,t}
}{
\sum_tm_{i,t}
}
$$

然后：

$$
L=
\frac1B
\sum_iL_i
$$

或者使用其他 token aggregation。

重点：

> padding length 和 real trajectory length 不能影响 objective。

---

### Multi-turn 还要考虑 Step Boundary

例如：

```text
Trajectory A:
step 0 = 20 tokens
step 1 = 30 tokens
step 2 = 50 tokens
```

如果需要 turn-level credit，就要保留：

```text
step_ids
```

不能只剩：

```text
length = 100
```

---

## 5.17 Invalid Action / Parser Failure 应该怎样建模？ `[P1]`

假设 protocol：

```text
<search>...</search>
<visit>...</visit>
<answer>...</answer>
```

模型输出：

```text
<serach>abc</search>
```

Parser failure。

---

### 这通常是 Policy Failure

因为模型没有产生 runtime 可执行 action。

但需要区分：

```text
model malformed output
```

和：

```text
parser bug
```

后者属于系统故障。

---

### 处理方式

可能：

#### 1. Immediate terminal

```text
invalid action
↓
reward penalty
↓
terminate
```

#### 2. Retry

```text
parser error
↓
feedback to model
↓
regenerate
```

#### 3. Repair

runtime 自动修复：

```text
"serach"
→
"search"
```

---

### 为什么 Repair 会改变训练问题？

如果 runtime silently repair：

模型实际生成错误 action：

$$
a_{\text{model}}
$$

环境执行修复后的：

$$
a_{\text{exec}}
$$

两者不同。

最终成功 reward：

```text
可能错误奖励 malformed policy behavior
```

所以 repair 必须记录 provenance。

---

### 推荐记录

```text
raw_generation
parsed_action
parse_status
repair_applied
executed_action
```

---

## 5.18 Tool Result 应该保存什么 Provenance？ `[P1]`

只保存：

```text
text = "Paris..."
```

往往不够。

至少应考虑：

```text
tool name
arguments
request ID
timestamp
status
latency
raw result
normalized observation
error type
retry count
source IDs / URLs / document IDs
```

---

### 为什么 Raw Result 和 Observation 要分？

例如 Search API 返回：

```json
{
  "title": "...",
  "snippet": "...",
  "score": 12.4,
  "metadata": {...}
}
```

runtime 可能只给模型：

```text
Title...
Snippet...
```

所以：

```text
raw tool result
≠
model observation
```

---

### 训练和 Debug 关注不同层

训练时：

```text
observation tokens
```

决定下一轮 policy context。

Debug 时：

```text
raw result
```

可以判断：

> 信息本来就没返回，还是 runtime 截断坏了？

---

# P2

## 5.19 多轮 Agent 的“连续 Token 语义”到底是什么？ `[P2]`

这是非常重要但很容易含糊的问题。

把 Agent trajectory flatten：

```text
[P][A0][O0][A1][O1][A2]
```

从 Transformer 角度：

> 它确实最终是一串 token context。

但从 policy probability 角度：

> 它不是一条全部由 policy 生成的 sequence。

---

### Policy Probability

Trajectory joint probability 可写成：

$$
P(\tau)
=
P(P)
\prod_t
\pi_\theta(A_t|H_t)
P(O_t|H_t,A_t)
$$

其中：

$$
H_t
=
P,A_0,O_0,\ldots,A_{t-1},O_{t-1}
$$

Policy 只控制：

$$
\pi_\theta(A_t|H_t)
$$

不控制：

$$
P(O_t|H_t,A_t)
$$

---

### Flatten 后不能写成

$$
\pi_\theta(
P,A_0,O_0,A_1,O_1,A_2
)
$$

并把所有 token 都作为 policy actions。

正确的是：

$$
\log P_\theta(\tau)
=
\sum_t
\log
\pi_\theta(A_t|H_t)
+
\text{environment terms}
$$

对 \(\theta\) 求梯度时：

$$
\nabla_\theta
\log P_\theta(\tau)
=
\sum_t
\nabla_\theta
\log\pi_\theta(A_t|H_t)
$$

Observation terms 不参与 policy gradient。

---

### Token 化以后

每个 action：

$$
A_t
=
(a_{t,1},\ldots,a_{t,L_t})
$$

于是：

$$
\log\pi(A_t|H_t)
=
\sum_j
\log\pi(a_{t,j}|H_t,a_{t,<j})
$$

最终 policy gradient token set 是：

```text
所有 A_t 的 tokens
```

而不是：

```text
整个 flattened context 的所有 tokens
```

---

## 5.20 Async Rollout 怎样破坏严格 On-policy 假设？ `[P2]`

同步训练：

```text
policy v10
↓
freeze
↓
generate batch
↓
train
↓
policy v11
```

所有 rollout 都来自：

$$
v10
$$

很清楚。

---

### Async

```text
Worker A:
v10 rollout starts ─────────────── returns

Trainer:
v10 → v11 → v12 → v13

Worker B:
        v11 rollout starts ─ returns
```

训练 batch 可能包含：

```text
v10
v11
v12
```

trajectory。

---

### 为什么不是严格 On-policy？

current：

$$
\pi_{v13}
$$

behavior：

$$
\pi_{v10}
$$

差距可能已经很大。

所以：

$$
d^{\pi_{\text{behavior}}}
\neq
d^{\pi_{\text{current}}}
$$

不仅 token distribution 不同，

Agent 中连：

```text
visited environment states
```

也不同。

---

### 为什么 Agent 比单轮更严重？

因为 action 改变 environment trajectory。

旧 policy：

```text
query A
→ document A
→ state A
```

current policy：

```text
query B
→ document B
→ state B
```

所以 stale trajectory 不只是：

> response token probability 有点不同。

而是整个 state distribution 可能改变。

---

### 处理方式

```text
bounded policy lag
version filter
importance correction
sync barrier
trajectory discard
replay weighting
```

但这些都会影响 throughput/sample efficiency。

---

## 5.21 Partial / Cancelled / Timeout Trajectory 应不应该进入训练？ `[P2]`

没有统一答案。

需要先区分原因。

---

### Case 1：Model-caused Failure

例如：

```text
模型反复搜索
→ 超过 max_steps
```

这通常应该作为负面行为保留。

否则 model 永远不会学到：

> 过度搜索有成本。

---

### Case 2：Infrastructure Failure

例如：

```text
GPU worker crashed
```

和 policy 无关。

如果直接 reward=0：

> 错误惩罚模型。

更合理可能：

```text
exclude from policy objective
```

但保留 system metrics。

---

### Case 3：Tool Timeout

需要判断：

```text
tool 本身偶发 timeout
```

还是：

```text
model 提交了极端昂贵请求
```

两者不同。

---

### Case 4：Trajectory Truncated by Budget

如果 max steps：

$$
T_{\max}
$$

是任务正式约束，

那么：

> 超预算本身就是任务 failure。

应该训练。

如果只是基础设施临时设置：

> 可能只是 experimental truncation。

---

### Partial Prefix 有没有训练价值？

可能有。

例如：

```text
Step 0: excellent search
Step 1: excellent evidence
Step 2: worker crashes
```

整条 trajectory 没最终 reward。

是否能使用前缀，取决于是否有：

* process reward；
* critic；
* bootstrapping；
* auxiliary objective。

Outcome-only RL 下通常很难给它可靠 advantage。

---

## 5.22 怎样区分“模型不会”与“环境不给它成功机会”？ `[P2]`

假设 success rate：

$$
5\%
$$

不能直接说：

> 模型弱。

---

### 环境上界

先问：

> 给 oracle policy，这个 environment 的最大可达成功率是多少？

如果：

```text
20% tasks
根本没有答案
```

则 agent 理论上不可能 100%。

---

### Tool Reliability

如果：

```text
10% search calls timeout
```

success rate 中混入 execution failures。

---

### Retrieval Recall Ceiling

如果正确证据：

```text
永远不出现在 Top-K
```

后面的 LLM 再聪明也不能恢复。

---

### Parser / Protocol Ceiling

模型想表达对了，但：

```text
action serialization invalid
```

这可能是 action-interface mismatch。

---

### 分层指标

建议拆：

```text
task solvability
tool execution success
retrieval recall
valid action rate
evidence acquisition rate
answer accuracy given evidence
overall success
```

---

### 一个很好的条件评估

比较：

$$
P(\text{correct answer})
$$

和：

$$
P(
\text{correct answer}
|
\text{gold evidence in context}
)
$$

如果后者很高：

> reasoning 没大问题，retrieval/environment 才是瓶颈。

---

## 5.23 Failure Propagation 为什么让 Long-horizon Credit Assignment 更难？ `[P2]`

考虑：

```text
Step 1
bad query
↓
Step 2
poor retrieval
↓
Step 3
confused reasoning
↓
Step 4
bad follow-up query
↓
Step 5
wrong final answer
```

最终：

$$
R=0
$$

---

### 哪一步是真正根因？

可能：

```text
Step 1
```

之后所有动作都是在坏 context 下做的局部合理决策。

如果给所有 token 相同 negative advantage：

```text
Step 1 negative
Step 2 negative
Step 3 negative
Step 4 negative
Step 5 negative
```

会错误惩罚后续某些合理行为。

---

### Failure Propagation

定义直觉：

> 早期错误改变后续 state distribution，使后续行为质量被历史错误污染。

因此：

$$
\text{observed failure at }t
$$

不等于：

$$
\text{causal failure originated at }t
$$

---

### Search Agent 特别严重

第一次检索决定：

```text
未来看到什么证据
```

所以 retrieval action 有强 state-shaping effect。

---

### 这为什么推动 Process / Credit 方法？

因为需要估计：

```text
哪个 turn
真正贡献了成功/失败？
```

例如：

* CW-GRPO；
* retrospective critic；
* fatal-aware masking；
* counterfactual credit。

这些都在处理 propagation。

---

## 5.24 Agent RL 中怎样定义 Training-ready Trace 的最小 Invariant？ `[P2]`

一个 trajectory 能展示，不代表能训练。

Training-ready trace 至少要满足几个 invariant。

---

### Invariant 1：Exact Action Identity

每个 policy token：

$$
a_t
$$

必须可准确恢复。

即：

```text
actual response token IDs
```

不能猜。

---

### Invariant 2：Exact Conditioning Context

对于每个 generation：

$$
\pi(a_t|s_t)
$$

必须知道 exact：

```text
prompt / context IDs
```

---

### Invariant 3：Behavior Probability

如果算法需要 PPO-style ratio：

$$
\log\pi_{\text{old}}(a_t|s_t)
$$

必须存在且与 token 对齐。

---

### Invariant 4：Source Mask

每个 token 必须知道是否：

```text
policy-generated
environment-generated
padding
template/context
```

---

### Invariant 5：Step Boundary

要能从 token 映射到：

```text
turn / action / observation
```

否则无法做 step-level credit。

---

### Invariant 6：Policy Version

知道：

```text
哪个 checkpoint
```

生成了这条 trajectory。

---

### Invariant 7：Environment Provenance

至少知道：

```text
tool result
error status
environment version / corpus version
```

否则结果不可复现。

---

### Invariant 8：Reward Provenance

不仅保存：

```text
reward = 1
```

还要知道：

```text
which verifier
which version
which rubric
component rewards
```

---

### 一句话

Training-ready trace 必须同时具备：

```text
semantic provenance
+
token provenance
+
policy provenance
+
environment provenance
+
reward provenance
```

---

## 5.25 多个 Generation Turn 的 Old Logprob 应该怎样与最终 Flattened Sequence 对齐？ `[P2]`

假设三轮：

```text
P0 → A0
P1 → A1
P2 → A2
```

对应：

$$
A_0=(a_{0,1},...,a_{0,L_0})
$$

$$
A_1=(a_{1,1},...,a_{1,L_1})
$$

$$
A_2=(a_{2,1},...,a_{2,L_2})
$$

每轮有：

$$
\ell^{old}_{t,j}
$$

---

### Flatten Training Sequence

可能变成：

```text
[P][A0][O0][A1][O1][A2]
```

此时建立：

$$
old\_logprobs
\in
\mathbb R^{T}
$$

其中：

```text
Prompt positions        dummy / masked
A0 positions            old logprobs from generation 0
O0 positions            dummy / masked
A1 positions            old logprobs from generation 1
O1 positions            dummy / masked
A2 positions            old logprobs from generation 2
```

同时：

$$
response\_mask
$$

只在 A0/A1/A2 为 1。

---

### 为什么 Observation 位置可以放任意 Placeholder？

因为：

$$
response\_mask=0
$$

这些位置不会进入 ratio/loss。

但工程上最好使用：

```text
0
```

或明确 sentinel，防止 debug 混乱。

---

### 更重要的是 State Alignment

当重新计算 A1：

必须使用：

$$
P+A_0+O_0
$$

作为它的 prefix。

不能把：

```text
O0
```

删除后直接：

$$
P+A_0
$$

打分。

否则 current logprob 和 old logprob conditional context 不同。

---

### 为什么 Per-turn Record 最稳？

因为它已经保存：

```text
prompt_ids_t
response_ids_t
response_logprobs_t
```

Flatten 只是后处理。

这样可以检查 invariant：

$$
len(response\_ids_t)
=
len(old\_logprobs_t)
$$

每轮先验证，再汇总。

---

## 5.26 如果 Tool Observation 很长，Context Growth 会怎样影响训练与 Rollout？ `[P2]`

假设每轮搜索返回：

$$
2000
$$

tokens。

10 turns：

$$
20,000
$$

observation tokens。

再加 reasoning：

$$
10,000
$$

最后 context：

$$
30,000+
$$

---

### 问题一：Prefill 重复

每次新 generation：

```text
history grows
```

如果 backend 没高效 cache，重复 prefill 成本很大。

---

### 问题二：KV Cache

Context 越长：

$$
M_{KV}\propto T
$$

并发 rollout 数下降。

---

### 问题三：Training Compute

即使 observation：

```text
loss mask = 0
```

它仍然进入 forward。

所以：

> zero-loss 不等于 zero-compute。

---

### 问题四：Context Interference

大量无关 observation：

```text
占用 context
+
改变 attention distribution
```

可能让模型反而更难找到关键 evidence。

---

### 问题五：Credit Dilution

10 次检索里：

```text
只有 2 次真正有用
```

但最终 reward 只告诉整条 trajectory 成败。

credit 更难。

---

### 处理路线

```text
retrieval filtering
top-k control
snippet compression
context refinement
structured memory
state summarization
external memory
selective observation
```

这些会在 Search Agent Macro 7–8 接着展开。

---

# 5.27 Agentic RL 完整数据流

必须能画出：

```text
Task
 ↓
Initial Context
 ↓
┌─────────────────────────────────────┐
│ Generation Turn t                   │
│                                     │
│ exact prompt IDs                    │
│        ↓                            │
│ behavior policy                     │
│        ↓                            │
│ response IDs + old logprobs         │
│        ↓                            │
│ action parser                       │
│        ↓                            │
│ validated action                    │
└──────────────┬──────────────────────┘
               ↓
         Environment / Tool
               ↓
         raw tool result
               ↓
       normalized observation
               ↓
        append to context
               ↓
       next generation turn
```

直到：

```text
final answer / terminal
         ↓
       reward
         ↓
trajectory evaluator
         ↓
training trace
```

Training trace：

```text
prompt IDs
response IDs
response mask
step IDs
old logprobs
reference logprobs
rewards
advantages
policy version
generation records
environment provenance
```

然后：

```text
Current Policy Forward
        ↓
current logprobs
        ↓
importance ratio
        ↓
policy loss
        ↓
optimizer
```

---

# 5.28 高频连环追问

## 第一组：Trajectory

```text
Episode 是什么？
↓
Trajectory 是什么？
↓
Turn / Step / Generation 区别？
↓
为什么不同框架定义不同？
↓
训练真正需要哪一层 provenance？
```

---

## 第二组：Observation

```text
Tool Observation 是什么？
↓
为什么不能计算 policy loss？
↓
为什么又必须放进 context？
↓
attention-visible 和 loss-bearing 有什么区别？
↓
下一轮 action 条件于什么？
```

---

## 第三组：Token Provenance

```text
为什么保存 response IDs？
↓
为什么不能 decode/re-tokenize？
↓
old logprob 和 token 怎么对齐？
↓
多轮 response 怎样 flatten？
↓
为什么还需要 step mapping？
```

---

## 第四组：Failure

```text
Policy failure 和 environment failure 区别？
↓
tool timeout 算哪一种？
↓
parser failure 呢？
↓
retry 会不会改变 trajectory semantics？
↓
failed sample 能不能删？
```

---

## 第五组：Async

```text
为什么 Agent rollout 容易 stale？
↓
policy version 怎么记录？
↓
async rollout 还是 on-policy 吗？
↓
staleness 怎么控制？
↓
旧 trajectory 能不能 replay？
```

---

# 5.29 Self-test

## Self-test 1：Observation Mask

序列：

```text
[P][A0][O0][A1]
```

长度：

```text
P  = 5
A0 = 3
O0 = 4
A1 = 2
```

response mask：

```text
P : 00000
A0: 111
O0: 0000
A1: 11
```

有效 policy tokens：

$$
3+2=5
$$

不是：

$$
14
$$

---

## Self-test 2：Generation Context

第二轮：

```text
P
A0
O0
A1
```

计算：

$$
\log\pi(A_1)
$$

必须条件于：

$$
P,A_0,O_0
$$

不能只用：

$$
P
$$

---

## Self-test 3：Failure Classification

情况：

```text
模型生成合法 Search action
API 返回 503
```

优先分类：

```text
environment / infrastructure failure
```

不是直接：

```text
bad policy
```

---

## Self-test 4：Parser

模型：

```text
<search>abc
```

缺 closing tag。

如果 protocol 要求严格 XML-like syntax：

```text
policy produced invalid action
```

除非后续证明：

```text
parser implementation 有 bug
```

---

## Self-test 5：Policy Version

trajectory：

```text
generated by step 1000
```

training 时 current：

```text
step 1100
```

不能简单写：

```text
same model = on-policy
```

必须考虑：

$$
\pi_{1000}
\neq
\pi_{1100}
$$

---

# 5.30 推导题

## 推导题 1：Multi-turn Trajectory Gradient

假设 trajectory：

$$
\tau
=
(A_0,O_0,A_1,O_1,A_2)
$$

概率：

$$
P_\theta(\tau)
=
\pi_\theta(A_0|H_0)
P(O_0|H_0,A_0)
\pi_\theta(A_1|H_1)
P(O_1|H_1,A_1)
\pi_\theta(A_2|H_2)
$$

若 environment dynamics 不依赖 \(\theta\)，证明：

$$
\nabla_\theta
\log P_\theta(\tau)
=
\sum_{t=0}^{2}
\nabla_\theta
\log\pi_\theta(A_t|H_t)
$$

Observation transition terms梯度为 0。

---

## 推导题 2：Action Token Decomposition

若：

$$
A_t=
(a_{t,1},...,a_{t,L_t})
$$

则：

$$
\pi(A_t|H_t)
=
\prod_j
\pi(
a_{t,j}
|
H_t,a_{t,<j}
)
$$

因此：

$$
\log\pi(A_t|H_t)
=
\sum_j
\log\pi(
a_{t,j}
|
H_t,a_{t,<j}
)
$$

这就是为什么 Agent action 最终仍能落到 token-level logprobs。

---

## 推导题 3：Flattened Response Mask

定义整个 flattened token sequence：

$$
x_{1:T}
$$

mask：

$$
m_t
$$

则 policy log-likelihood：

$$
\log\pi_\theta(\tau)
=
\sum_{t=1}^{T}
m_t
\log
p_\theta(
x_t|x_{<t}
)
$$

这里：

```text
prompt / observation:
m_t = 0

policy-generated action:
m_t = 1
```

这是多轮 trajectory 到普通 causal-LM tensor representation 的桥。

---

# 5.31 Debug 题

## Debug 1：Old Logprob Shape 对不上 Response IDs

例如：

```text
response_ids:      length 83
response_logprobs: length 82
```

必须 hard fail。

不要：

```text
truncate to min length
```

否则 token alignment silently corrupted。

检查：

```text
BOS/EOS
first-token logprob
finish token
backend API semantics
special token handling
```

---

## Debug 2：Agent 训练后越来越爱输出 Tool Observation 风格文本

检查：

```text
observation token 是否错误进入 response mask
```

如果 environment text 参与 policy loss：

模型会学：

> 模仿环境输出。

---

## Debug 3：同一个 Seed 仍然无法 Replay

检查：

```text
policy checkpoint
tokenizer
chat template
sampling backend
sampling params
tool results
environment seed
parallel scheduling
external API nondeterminism
```

Agent replay 比普通 generation replay 难，因为：

> environment 也必须 reproducible。

---

## Debug 4：Invalid Action Rate 突然升高

检查：

```text
chat template
action protocol prompt
tokenizer
structured decoding
sampling temperature
checkpoint update
parser
max tokens
truncation
```

如果 model output 是合法的，而 parser 报错：

> 不要继续调模型。

---

## Debug 5：训练成功率下降，但模型答案质量肉眼没下降

检查 execution layers：

```text
tool success rate
parser success rate
timeouts
retriever availability
corpus version
environment errors
```

整体 reward 下降可能不是 policy deterioration。

---

## Debug 6：Group Diversity 很低

检查：

```text
same rollout seed?
temperature too low?
top-p too small?
greedy generation?
backend generator reused?
duplicate response collapse?
```

如果 group：

```text
16 条完全一样
```

GRPO relative advantage 价值极低。

---

# 5.32 系统设计题

## 系统设计题 1：怎样设计一个可以后训练的 Agent Runtime？

至少拆：

```text
Task
↓
Policy
↓
Action Parser
↓
Environment
↓
Tool
↓
Observation
↓
Trajectory Recorder
↓
Evaluator
↓
Training Trace Builder
```

关键 invariant：

```text
execution trace
```

必须可以无损转换成：

```text
training trace
```

---

## 系统设计题 2：Agent Runtime 是否应该和 Trainer 强耦合？

通常希望：

```text
Agent Runtime
     ↓
framework-neutral trace
     ↓
Trainer Adapter
     ├── verl
     ├── custom trainer
     └── other backend
```

而不是：

```text
Agent code
直接写死某个 Trainer 内部 tensor
```

原因：

* evaluation 可复用；
* rollout backend 可替换；
* trainer 可替换；
* trace 可 offline inspect。

这正是后面 rLLM 类框架值得学习的原因。

---

## 系统设计题 3：如何保证 Retry 不破坏实验语义？

需要明确：

```text
retryable infrastructure error
```

与：

```text
policy invalid action
```

不能统一 retry。

建议记录：

```text
attempt_id
original action
error type
retry policy
final executed action
```

否则：

```text
trajectory 看起来成功
```

但真实执行中可能重试 5 次。

这会隐瞒系统成本和 failure rate。

---

## 系统设计题 4：Tool Observation 超长怎么办？

不能只有：

```text
truncate first N tokens
```

需要考虑：

```text
top-k
semantic filtering
snippet extraction
re-ranking
context refinement
structured state
memory
```

并记录：

> 模型实际看到的是 raw result 的哪一部分。

---

# 5.33 Agentic RL 常见错误认知

## 错误一

> Agent trajectory 只是一个更长的 response。

错误。

因为中间包含 environment-generated observations。

---

## 错误二

> Observation 不算 loss，所以可以训练时删掉。

错误。

后续 action 条件于 observation。

---

## 错误三

> 只要最终保存文本就可以后训练。

错误。

PPO/GRPO 需要 exact token / logprob provenance。

---

## 错误四

> Timeout 都应该 reward=0。

错误。

必须区分 policy-caused 和 environment-caused timeout。

---

## 错误五

> Async rollout 只是系统吞吐优化。

错误。

它会改变 behavior/current policy gap，进而改变 RL 数据分布。

---

## 错误六

> Multi-turn trajectory flatten 后就可以像普通 SFT 一样全 token 计算 loss。

错误。

只应对 policy-generated token 计算 policy objective。

---

# 5.34 与 Search Agent 的接口

进入 Macro 6 之后：

```text
Action
```

不再是抽象 action，而会具体变成：

```text
Search(query)
Visit(document)
Answer(text)
```

于是本章问题会具体化：

```text
Action Protocol
↓
Search / Visit / Answer protocol

Observation
↓
search result / document content

Environment Failure
↓
retriever timeout / stale index

Credit Assignment
↓
哪次 query 真正贡献了最终答案

Context Growth
↓
检索文档不断累积

Variable Horizon
↓
到底搜几轮才停
```

所以 Search Agent 不是另一套完全独立的理论。

它是：

> Agentic RL 在 retrieval/search environment 上的一个具体实例。

---

# 5.35 Macro 5 最小知识图

最终应该形成：

```text
                         Task
                          │
                          ↓
                    Initial Context
                          │
                          ↓
                 Behavior Policy
                          │
                 Generation Record
            ┌─────────────┼─────────────┐
            │             │             │
       Prompt IDs    Response IDs   Old Logprobs
            │             │             │
            └─────────────┼─────────────┘
                          ↓
                     Raw Output
                          ↓
                    Action Parser
                          ↓
                   Validated Action
                          ↓
                      Environment
                          ↓
                     Tool Execution
                          ↓
                    Tool Result
                          ↓
                 Observation Tokens
                          │
                          └─────────────┐
                                        ↓
                                  Next Context
                                        ↓
                                Next Generation
                                        ↓
                                      ...
                                        ↓
                                   Final Answer
                                        ↓
                                      Reward
```

然后转换：

```text
Execution Trajectory
        ↓
Training Trace
        │
        ├── policy-generated token IDs
        ├── observation token IDs
        ├── response mask
        ├── step mapping
        ├── old logprobs
        ├── policy version
        ├── reward
        └── provenance
        ↓
Current Policy Forward
        ↓
Current Logprobs
        ↓
PPO / GRPO / future credit objective
```

需要真正记住的核心 invariant 是：

```text
Context token
≠
Policy action token
≠
Loss-bearing token
```

以及：

```text
Human-readable trajectory
≠
Training-ready trajectory
```

当能够解释：

> **为什么一个 Search Agent 成功执行完任务，还不代表这条 trajectory 已经具备可用于 PPO/GRPO 的训练语义**

Macro 5 才算真正掌握。

Macro 6 接下来就可以正式进入 Search Agent 本体，从：

```text
RAG
→ Agentic RAG
→ Search Agent
→ Search-o1
→ Search-R1
→ WebThinker
→ DeepResearcher
→ DR-Tulu
```

开始，不再只讲 generic Agent。

## 6. Search Agent Foundations & Paper Lineage

前五个 Macro 已经建立：

```text
LLM
 ↓
Training
 ↓
RL
 ↓
PPO / GRPO
 ↓
Agentic RL
```

从这一章开始，环境不再是抽象的：

```text
Tool(...)
```

而是具体的 Search Environment：

```text
Reason
  ↓
Search(query)
  ↓
Search Results
  ↓
Read / Visit
  ↓
Evidence
  ↓
Reason
  ↓
Search again?
  ↓
Answer
```

Search Agent 真正研究的问题也不是：

> “给 LLM 接一个搜索 API。”

而是让 policy 学会一组 sequential decisions：

```text
Should I search?
What should I search?
Which result should I inspect?
What information should I keep?
Should I reformulate the query?
Should I search again?
When do I have enough evidence?
When should I stop?
How should I synthesize the answer?
```

因此 Search Agent 横跨：

```text
Retrieval
Reasoning
Tool Use
Sequential Decision Making
RL
Credit Assignment
Context Management
Environment Design
```

本章先解决两个问题。

第一：

> Search Agent 与传统 RAG / Agentic RAG / Deep Research 到底有什么区别？

第二：

> 2025 以后这条论文路线到底是怎样一步一步演化的？

重点不是背论文年份，而是建立：

```text
Previous Failure
      ↓
New Formulation
      ↓
Action / Environment
      ↓
Training Signal
      ↓
New Capability
      ↓
New Bottleneck
```

这种纵向理解。

---

## 6.0 问题矩阵

| 编号   | 问题                                                                  | 等级 |
| ---- | ------------------------------------------------------------------- | -- |
| 6.1  | RAG 的基本 Pipeline 是什么？                                               | P0 |
| 6.2  | RAG、Agentic RAG、Search Agent 有什么区别？                                 | P0 |
| 6.3  | ReAct 为什么是理解 Search Agent 的重要前置？                                    | P0 |
| 6.4  | Search Agent 的核心决策变量有哪些？                                            | P0 |
| 6.5  | Search-o1 解决了什么问题？Reason-in-Documents 为什么存在？                        | P0 |
| 6.6  | Search-R1 相比 Search-o1 的关键变化是什么？                                    | P0 |
| 6.7  | Search-R1 为什么要对 Retrieved Tokens 做 Mask？                            | P0 |
| 6.8  | WebThinker 相比 Search-R1 扩展了什么？                                      | P0 |
| 6.9  | DeepResearcher / DR Tulu 为什么意味着从 Search QA 进入 Deep Research？        | P0 |
| 6.10 | Retrieval-Augmented Reasoning 与真正 Learned Search Policy 有什么区别？      | P1 |
| 6.11 | Search-o1 的 Reason-in-Documents 本质上在解决什么？                           | P1 |
| 6.12 | 为什么把完整检索文档直接塞进 Reasoning Context 会有问题？                              | P1 |
| 6.13 | Search-R1 为什么仅用 Outcome Reward 也可能学出搜索行为？                           | P1 |
| 6.14 | Search-R1 的 Search / Retrieval Environment 如何决定可学到的 Policy？         | P1 |
| 6.15 | Query Reformulation 为什么是 Search Agent 的核心能力？                        | P1 |
| 6.16 | Retrieve-once 为什么必须成为 Search Agent Baseline？                        | P1 |
| 6.17 | Search Depth / Search Budget 应怎样理解？                                 | P1 |
| 6.18 | Agent 应怎样决定 Stop Searching？                                         | P1 |
| 6.19 | WebThinker 的 Think–Search–and–Draft 与普通 Search Agent 有什么区别？         | P1 |
| 6.20 | Real Web Environment 相比 Static Corpus 多了哪些训练变量？                     | P1 |
| 6.21 | 为什么 Short-form QA Reward 不足以训练 Long-form Deep Research？             | P1 |
| 6.22 | DR Tulu 的 Evolving Rubrics 为什么需要随 Policy 演化？                        | P1 |
| 6.23 | Search Agent 的 Learning Unit 到底应该是 Query、Turn、Trajectory 还是 Report？ | P2 |
| 6.24 | Prompted Search Agent 与 RL-trained Search Agent 应怎样公平比较？            | P2 |
| 6.25 | Open-Web RL 中“On-policy”应该怎样理解？                                     | P2 |
| 6.26 | Deep Search 与 Deep Research 应该怎样分别设计 Environment 和 Evaluator？       | P2 |
| 6.27 | 如果重新设计 Search-R1 类 Baseline，哪些部分应该保留，哪些部分必须扩展？                      | P2 |
| 6.28 | Search Agent 论文应该怎样纵向比较，而不是逐篇背摘要？                                   | P2 |

---

# 6A. Search Agent 基础

## 6.1 RAG 的基本 Pipeline 是什么？ `[P0]`

### 30～60 秒回答

经典 Retrieval-Augmented Generation 可以抽象为：

```text
User Query q
     ↓
Retriever
     ↓
Top-K Documents
     ↓
Context Construction
     ↓
LLM
     ↓
Answer
```

形式上：

$$
D_q
=
\operatorname{Retrieve}(q)
$$

然后：

$$
y
\sim
p_\theta(
y
|
q,D_q
)
$$

Retriever 可以是：

```text
BM25
Dense Retriever
Hybrid Retriever
Search Engine
```

核心思想：

> 不要求模型把所有事实都存储在参数里，而是在 inference 时把相关外部知识放进 context。

---

### RAG 主要解决什么？

两个典型问题。

#### Knowledge Freshness

模型 pretraining knowledge 有 cutoff。

外部 retrieval 可以拿到：

```text
new documents
updated facts
private knowledge base
```

---

#### Parametric Knowledge Limitation

模型可能：

```text
不知道
记错
无法稳定 recall
```

retrieval 提供 explicit evidence。

---

### 经典 RAG 中谁决定 Query？

通常就是：

```text
原始 user query
```

最多先做固定 query rewrite。

之后：

```text
retrieve once
→ generate once
```

没有真正 sequential policy。

---

### 这就是与 Search Agent 的第一个边界

RAG：

```text
query
↓
retrieve
↓
answer
```

Search Agent：

```text
reason
↓
decide whether to search
↓
generate query
↓
observe
↓
reason again
↓
possibly search again
↓
...
```

后者显然是 sequential decision process。

---

## 6.2 RAG、Agentic RAG、Search Agent 有什么区别？ `[P0]`

这三个词在行业里经常混用，因此面试时最好先说明：

> 没有完全统一的命名标准，我按 control loop 区分。

---

### RAG

通常：

```text
Retrieve Once
↓
Generate
```

retrieval pipeline 相对固定。

例如：

```text
query
↓
BM25
↓
Top-5 chunks
↓
LLM
```

---

### Agentic RAG

加入了一些 LLM-controlled decisions，例如：

```text
rewrite query?
rerank?
retrieve again?
which corpus?
```

但整体仍以：

> 增强生成质量的 retrieval pipeline

为中心。

例如：

```text
Question
↓
LLM query rewrite
↓
Retriever
↓
LLM judges evidence quality
↓
if bad:
    retrieve again
↓
Answer
```

---

### Search Agent

Search 本身成为 action space。

Policy 必须学习：

$$
\pi(
a_t
|
s_t
)
$$

其中 action 可能：

```text
Search(query)
Visit(doc)
Lookup(term)
Answer(...)
```

也就是说：

> Retrieval 不再只是 generation 前的 preprocessing，而是 Agent trajectory 中的行动。

---

### 一个更实用的判断方法

问：

> 如果第一次检索结果不好，模型能否根据结果自主决定下一次 query？

如果：

```text
不能
```

更接近传统 RAG。

如果：

```text
可以，而且 search decision 本身属于模型 policy
```

更接近 Search Agent。

---

### Agentic RAG 与 Search Agent 是否一定有清晰边界？

没有。

现实中它们有连续谱：

```text
Fixed RAG
    ↓
Query Rewriting
    ↓
Conditional Retrieval
    ↓
Iterative Retrieval
    ↓
Tool-using Search Agent
    ↓
Deep Research Agent
```

所以面试中不要执着：

> 某系统到底算不算 Agentic RAG。

应该讨论：

```text
谁控制 search？
是否多轮？
是否有 state transition？
是否训练 search policy？
```

---

## 6.3 ReAct 为什么是理解 Search Agent 的重要前置？ `[P0]`

ReAct 将：

```text
Reasoning
```

和：

```text
Acting
```

交替组织。

典型轨迹：

```text
Thought:
I need to find X.

Action:
Search[X]

Observation:
...

Thought:
The result mentions Y. I need Y's birthplace.

Action:
Search[Y birthplace]

Observation:
...

Thought:
Now I can answer.

Action:
Finish[...]
```

ReAct 在知识密集任务中就使用过：

```text
search
lookup
finish
```

这样的 Wikipedia action space，并展示 reasoning 如何指导下一次 retrieval。

---

### ReAct 的关键贡献不是“Thought 字段”

更重要的是：

$$
Reason
\rightarrow
Action
\rightarrow
Observation
\rightarrow
Reason
$$

形成闭环。

也就是：

> 环境 observation 可以改变后续 reasoning 和 action。

---

### 与 Search-R1 类方法的区别

ReAct 最初主要依靠：

```text
prompting / few-shot trajectories
```

来激活这种行为。

之后 Search Agent RL 的关键问题变成：

> 能不能不用人工写死好的 search trajectory，而让模型通过 reward 自己学会如何搜索？

于是就自然走向：

```text
prompted tool use
↓
learned tool use
↓
RL-trained search policy
```

---

## 6.4 Search Agent 的核心决策变量有哪些？ `[P0]`

至少可以拆成八个。

---

### 1. Should I Search?

当前 parametric knowledge 是否足够？

```text
直接答
vs
搜索
```

---

### 2. What Should I Search?

生成 query：

$$
q_t
$$

---

### 3. Where Should I Search?

如果有多个工具：

```text
Web
Wikipedia
Internal KB
Academic Search
Code Search
Image Search
```

需要 route。

---

### 4. Which Result Should I Read?

Search result 返回：

```text
doc1
doc2
doc3
...
```

是否全部读？

还是：

```text
Visit(doc2)
```

---

### 5. What Evidence Should I Keep?

Observation 很长。

需要判断：

```text
relevant
irrelevant
conflicting
duplicate
```

---

### 6. Should I Reformulate?

当前 query：

```text
没有找到答案
```

模型要不要改变方向？

---

### 7. Should I Search Again?

已有 evidence 是否足够？

---

### 8. When Should I Stop?

继续搜索：

```text
可能提高答案
```

但也增加：

```text
token
latency
cost
context noise
```

所以 stopping 本身是一个 policy decision。

---

### 可以画成

```text
Current Knowledge State
         │
         ↓
   Search needed?
     /        \
   No          Yes
   │            │
 Answer      Query
                ↓
             Search
                ↓
           Observation
                ↓
         Evidence enough?
            /      \
          Yes       No
           │         │
        Answer    Reformulate
                     │
                     └────→ Search again
```

---

## 6.5 Search-o1 解决了什么问题？Reason-in-Documents 为什么存在？ `[P0]`

Search-o1 的出发点是：

> Large Reasoning Models 有较强长链推理，但在 reasoning 中遇到知识缺口时，内部知识不足会导致不确定和错误。

它因此把 agentic retrieval 嵌入 reasoning process，使模型在遇到知识缺口时动态检索。

---

### 核心 Pipeline

可以理解成：

```text
Reasoning
   ↓
knowledge gap?
   ↓ yes
Search
   ↓
Retrieved Documents
   ↓
Reason-in-Documents
   ↓
Refined information
   ↓
Back to reasoning
```

---

### 为什么需要 Reason-in-Documents？

搜索结果往往：

```text
长
冗余
噪声多
与原问题只有局部相关
```

如果直接把整篇文档塞回 reasoning：

```text
original reasoning
+
huge retrieved document
```

容易：

* context 膨胀；
* reasoning continuity 被打断；
* distractor 增加。

因此 Search-o1 单独设计 Reason-in-Documents 模块，在将检索内容重新注入主 reasoning chain 前先分析和提炼。

---

### Search-o1 的意义

它可以看成从：

```text
Reasoning Model
```

向：

```text
Search-augmented Reasoning Model
```

的重要过渡。

但它还没有完全回答：

> 搜索策略能否通过 end-to-end RL 自己学出来？

这正是 Search-R1 推进的方向。

---

## 6.6 Search-R1 相比 Search-o1 的关键变化是什么？ `[P0]`

Search-R1 的核心变化可以概括为：

> **从 inference-time agentic search workflow，推进到 RL-trained multi-turn search policy。**

Search-R1明确指出，仅在 inference 时 prompt reasoning model 使用搜索，并不能让模型真正学习如何最优地与搜索引擎交互；它因此让模型通过 RL 学习在 step-by-step reasoning 中自主生成多次 search query。

---

### Search-o1

更偏：

```text
Reasoning Model
+
designed agentic retrieval mechanism
```

---

### Search-R1

更偏：

```text
Policy
↓
multi-turn search interaction
↓
outcome reward
↓
RL update
```

---

### Search-R1 重要的几个设计

#### 1. Multi-turn Search

不是：

```text
retrieve once
```

而是：

```text
reason
search
reason
search
...
answer
```

---

#### 2. RL

search behavior 本身进入 policy learning。

---

#### 3. Outcome-based Reward

不要求人工标每一步：

```text
这个 query 好不好
这个 retrieval 是否必要
```

而主要依赖最终 outcome。

---

#### 4. Retrieved-token Masking

环境返回的 retrieved text 不应该作为模型生成 token 参与 policy loss。

这与 Macro 5 的：

```text
Context token
≠
Policy action token
```

完全对应。

---

### 一句话纵向关系

```text
Search-o1
让 reasoning model 在需要时搜索

        ↓

Search-R1
让 reasoning model 通过 RL 学会如何搜索
```

---

## 6.7 Search-R1 为什么要对 Retrieved Tokens 做 Mask？ `[P0]`

Search-R1 的 retrieved tokens 来自搜索环境，不是 policy 生成。论文明确使用 retrieved-token masking 来稳定 RL training。

假设：

```text
Assistant:
<search>Who founded X?</search>

Environment:
Search result: X was founded by A...

Assistant:
<answer>A</answer>
```

policy-generated：

```text
<search>...</search>
<answer>...</answer>
```

environment-generated：

```text
Search result...
```

---

### 如果不 Mask

会把 retrieval content 当成：

$$
a_t\sim\pi_\theta
$$

然后计算：

$$
\log\pi_\theta(
\text{retrieved tokens}
|
context
)
$$

这在 policy gradient 语义上不成立。

---

### 正确做法

整个 sequence 都进入 Transformer context：

```text
Prompt
Action
Observation
Action
```

但 policy loss：

```text
Prompt       0
Action       1
Observation  0
Action       1
```

---

### 为什么叫“Masking retrieved tokens”，而不是把它们删掉？

因为下一轮 action 需要依赖 retrieval content。

删除 observation 后：

$$
\pi(a_{t+1}|history)
$$

的 condition 就错了。

---

### 这实际上是 Agentic RL 的一般原则

Search-R1 中是：

```text
retrieved token mask
```

换成 Coding Agent：

```text
compiler output mask
```

Browser Agent：

```text
page observation mask
```

Python Agent：

```text
stdout mask
```

原则完全相同。

---

## 6.8 WebThinker 相比 Search-R1 扩展了什么？ `[P0]`

Search-R1 的核心任务更接近：

```text
multi-turn search
+
reasoning
+
short-form QA
```

WebThinker进一步进入：

```text
Web Search
+
Web Navigation
+
Information Extraction
+
Long-form Drafting
```

WebThinker 提出 Deep Web Explorer，使模型可以搜索、浏览页面并从网页结构中提取信息；同时使用 Autonomous Think-Search-and-Draft，把 reasoning、information gathering 和 report drafting 交错进行。

---

### Search-R1

可以粗略画成：

```text
Think
 ↓
Search
 ↓
Observe
 ↓
Think
 ↓
Answer
```

---

### WebThinker

变成：

```text
Think
 ↓
Search
 ↓
Navigate
 ↓
Read
 ↓
Think
 ↓
Draft Section
 ↓
Search More
 ↓
Edit Draft
 ↓
...
```

---

### Action Space 扩张

Search-R1 更强调 search engine interaction。

WebThinker 的 agent environment 开始包括：

```text
search
navigate pages
extract
draft
inspect report
edit
```

其项目实现也明确描述了针对 report generation 的 drafting、checking 和 editing tools。

---

### Training 也不同

WebThinker使用 iterative online DPO 来改善 tool utilization，而不是简单照搬 Search-R1 的 GRPO-style outcome RL。

---

### 它意味着什么？

Search Agent 不再只是：

> “为了回答一个 QA，搜索几次。”

开始变成：

> “模型自主执行一个 research workflow。”

---

## 6.9 DeepResearcher / DR Tulu 为什么意味着从 Search QA 进入 Deep Research？ `[P0]`

### DeepResearcher

DeepResearcher明确指出，两类已有方法都有明显限制：

```text
prompt-engineered search
→ brittle

RL in controlled RAG environment
→ environment too clean
```

它将 end-to-end RL 推到真实 Web interaction，处理 open Web 的 noisy、unstructured、dynamic 特性。

---

### 关键变化

从：

```text
fixed retrieval corpus
```

到：

```text
real-world web environment
```

意味着：

* 页面结构不统一；
* 内容动态变化；
* noise 更多；
* navigation 更复杂；
* 搜索结果不稳定；
* latency/error 成为真实环境组成部分。

DeepResearcher报告其 RL agent出现了 planning、cross-validation、self-reflection 等行为，但这些是论文实验观察，不应抽象成所有 Web RL 都必然出现。

---

### DR Tulu

更进一步的问题是：

> 如果任务不是有唯一短答案的 QA，而是要求写一份长篇研究报告，reward 怎么定义？

DR Tulu 指出，大量开放 deep-research 模型仍主要在易验证 short-form QA 上使用 RLVR，这种 reward 不能直接覆盖真实 long-form research。它提出 Reinforcement Learning with Evolving Rubrics，让 rubric 随 policy 的探索而更新，以提供更有区分度的 on-policy feedback。

---

### 因此纵向演化可以看成

```text
Search QA
   │
   │ final answer 可 EM / verifier
   ↓
Multi-turn Search RL
   │
   ↓
Web Navigation
   │
   ↓
Real-Web Research
   │
   ↓
Long-form Research
   │
   ↓
Reward 不能再只靠 EM
```

这一步开始逼迫研究重点从：

```text
怎么搜？
```

扩展为：

```text
怎么评估一整份 research artifact？
```

---

# P1

## 6.10 Retrieval-Augmented Reasoning 与真正 Learned Search Policy 有什么区别？ `[P1]`

假设两个系统都能：

```text
reason
search
reason
answer
```

表面上很像。

真正区别要看：

> Search decision 是否在训练中被优化。

---

### Prompted / Programmed Search

例如：

```python
if model_says_search:
    result = search(query)
```

模型行为主要来自：

* prompt；
* few-shot；
* SFT；

但 search action 没有经过 task-outcome RL。

---

### Learned Search Policy

把 action：

$$
a_t=\operatorname{Search}(q_t)
$$

视为 policy action。

最终 reward：

$$
R(\tau)
$$

通过 policy gradient 回传：

$$
R
\nabla
\log
\pi_\theta(
a_t|s_t
)
$$

因此模型可以学习：

* 什么时候搜；
* query 怎么写；
* 搜几次；
* 什么时候停止。

---

### 关键区别不是“用了 RL”

如果只对最终 answer tokens 做 RL，

search action token 被：

```text
mask = 0
```

那么 search policy 本身没有真正优化。

所以需要问：

```text
search action tokens
是否属于 policy loss？
```

---

### 评价也应不同

Prompted Search Agent：

> inference workflow 是否有效？

RL-trained Search Agent：

> policy 是否真的从 reward 中学到新的 search behavior？

最好看：

```text
search frequency
query quality
search depth
stop behavior
answer accuracy
cost
```

而不是只看 final EM。

---

## 6.11 Search-o1 的 Reason-in-Documents 本质上在解决什么？ `[P1]`

表面看：

> 它是在总结检索文档。

更准确：

> 它在解决 retrieval observation 与 main reasoning chain 之间的信息接口问题。

---

### 原问题

Search：

```text
query
```

返回：

```text
document 1: 2000 tokens
document 2: 3000 tokens
document 3: 2500 tokens
```

但真正与当前 reasoning subproblem 相关的可能只有：

```text
100 tokens
```

---

### 直接拼接的问题

```text
reasoning prefix
+
7500 retrieved tokens
+
continue reasoning
```

会带来：

* context length；
* attention cost；
* irrelevant evidence；
* reasoning interruption。

Search-o1 因此通过 Reason-in-Documents 模块先处理检索内容，再把提炼信息提供给主 reasoning。

---

### 可以理解成两级 reasoning

```text
Main Reasoning
      │
      ↓
   Search
      ↓
Document-local Reasoning
      ↓
Relevant information
      ↓
Main Reasoning resumes
```

---

### 为什么这很重要？

因为 Search Agent 后续一直会遇到同一问题：

```text
Environment can return much more information
than policy should keep in active context
```

后来会发展为：

* context refiner；
* memory；
* structured state；
* table state。

所以 Reason-in-Documents 可以看作 context management 这条线的早期形态之一。

---

## 6.12 为什么把完整检索文档直接塞进 Reasoning Context 会有问题？ `[P1]`

至少五类问题。

---

### 1. Context Cost

每轮：

$$
K
$$

篇文档，

每篇：

$$
L
$$

tokens。

搜索：

$$
T
$$

轮。

粗略 observation 增长：

$$
O(TKL)
$$

---

### 2. Prefill / KV Cost

即使 retrieved tokens：

```text
loss mask = 0
```

也仍参与 Transformer forward。

所以：

```text
zero-loss
≠
zero-compute
```

---

### 3. Distractor Interference

例如问题要找：

```text
作者出生地
```

搜索结果里同时出现：

```text
出版年份
书名
评论
其他同名作者
```

更多 context 不一定提高答案质量。

---

### 4. Contradiction

不同网页：

```text
source A: 1990
source B: 1991
```

直接 concat 不等于解决 conflict。

---

### 5. Context Position

关键证据可能被埋在大量噪声中。

模型读取能力并不是：

```text
context length = N
```

就意味着：

```text
N 个 token 都能同样稳定利用
```

---

### 所以后续研究会自然走向

```text
retrieval
↓
selection
↓
compression
↓
memory
↓
structured state
```

而不是无限：

```text
append raw observation
```

---

## 6.13 Search-R1 为什么仅用 Outcome Reward 也可能学出搜索行为？ `[P1]`

假设 reward 只看最终答案：

$$
R=
\begin{cases}
1,&correct\\
0,&wrong
\end{cases}
$$

search action 没有显式：

```text
good query +0.1
```

---

### 为什么仍然可能学习？

Policy gradient：

$$
\nabla J
=
\mathbb E
\left[
R(\tau)
\sum_t
\nabla
\log
\pi(a_t|s_t)
\right]
$$

如果成功 trajectory 经常包含某类 query：

```text
good search behavior
```

那么这些 action 在高 reward trajectory 中被强化。

所以：

> 不需要显式 step reward，final outcome 也能给早期 action credit。

Search-R1 正是使用简单 outcome-based reward 来优化包含 multi-turn search 的 rollout。

---

### 但为什么仍然会有问题？

因为 credit 很粗。

成功 trajectory：

```text
search 1 good
search 2 useless
search 3 good
answer correct
```

三次 search 都得到相同 outcome advantage。

失败 trajectory：

```text
search 1 excellent
search 2 excellent
answer careless mistake
```

前面好 search 也被负更新。

---

### 所以 Outcome-only 是一个很好的 Baseline

优势：

```text
simple
cheap
low judge bias
```

但 long horizon 后 naturally 推动：

```text
process reward
credit assignment
contribution weighting
critic
```

也就是 Macro 8 的主线。

---

## 6.14 Search-R1 的 Search / Retrieval Environment 如何决定可学到的 Policy？ `[P1]`

Agent policy 不会脱离 environment 独立存在。

假设 action space：

```text
Search(query)
Answer(text)
```

模型就无法学习：

```text
Visit(doc)
```

因为根本不存在这个 action。

---

### Retriever 决定 Observation Distribution

如果 Search：

```text
BM25 Top-5
```

则 observation 来源于：

$$
P(O|q,\text{BM25})
$$

换成 dense retriever：

$$
P(O|q,\text{Dense})
$$

整个 Agent 的 transition dynamics 都变了。

---

### Search Result Granularity

如果 Search 直接返回：

```text
完整文档
```

和：

```text
标题 + snippet
```

会导致完全不同的 policy。

前者可能：

> Search 一次就够。

后者可能需要：

```text
Search
↓
Visit
```

---

### Search Corpus 也定义 Task Ceiling

如果 gold evidence：

```text
不在 corpus
```

模型无法通过 search 找到。

---

### Environment Alignment

因此一个 Search Agent 的“能力”实际上是：

$$
\text{Policy}
\times
\text{Retriever}
\times
\text{Corpus}
\times
\text{Tool Protocol}
$$

的结果。

不能把：

```text
Search-R1 + Retriever A
```

和：

```text
Baseline + Retriever B
```

直接比较后说 policy 更强。

---

## 6.15 Query Reformulation 为什么是 Search Agent 的核心能力？ `[P1]`

一次 query 失败并不意味着：

> 搜索工具没用。

可能只是 query 不好。

---

### 原问题

例如：

```text
Which university did the founder of X attend?
```

模型直接搜索整句：

```text
"Which university did founder of X attend"
```

可能结果很差。

---

### 更合理分解

```text
Search 1:
founder of X
↓
observation:
founder = Alice Smith

Search 2:
Alice Smith education university
↓
answer
```

---

### Multi-hop Search 的本质

当前 query：

$$
q_t
$$

取决于之前 observation：

$$
q_{t+1}
=
f(
q,
o_0,\ldots,o_t
)
$$

因此 query generation 是一个 sequential policy。

---

### Reformulation 类型

```text
entity expansion
query narrowing
query broadening
synonym replacement
temporal constraint
source constraint
sub-question decomposition
```

---

### 为什么传统 Retriever 不解决这个？

Retriever 只回答：

$$
D=\operatorname{Retrieve}(q)
$$

它不负责：

> 下一次应该搜什么。

Search Agent 的价值就在：

$$
q_{t+1}
$$

由 reasoning state 决定。

---

## 6.16 Retrieve-once 为什么必须成为 Search Agent Baseline？ `[P1]`

假设你的 Agent：

```text
Search
Search
Search
Answer
```

准确率 70%。

普通 retrieve-once：

```text
Retrieve Top-20
Answer
```

准确率 69%。

那么：

> 复杂 Agent 是否真的值得？

并不明显。

---

### Search Agent 增加的成本

包括：

```text
更多 LLM calls
更多 search calls
更多 latency
更多 tokens
更复杂 failure surface
```

---

### 所以至少应该比较

```text
No Retrieval
Retrieve Once
Iterative Search
Learned Search Agent
```

---

### 公平性

需要控制：

```text
same retriever
same corpus
same total evidence budget
same backbone
same answer decoder
```

否则 agent 可能只是因为：

```text
看到了更多 documents
```

而赢。

---

### 一个更严格的实验

固定总 retrieval budget：

$$
K_{\text{total}}=20
$$

比较：

```text
Retrieve-once:
一次 Top-20

Agent:
4 次 Top-5
```

此时才能更清楚回答：

> adaptive retrieval 本身有没有价值。

---

## 6.17 Search Depth / Search Budget 应怎样理解？ `[P1]`

Search depth 可以指：

```text
number of search rounds
```

例如：

$$
D=3
$$

---

### 为什么更多轮可能更强？

因为每轮 query 可以利用前一轮 evidence：

$$
q_{t+1}
=
f(o_{\le t})
$$

能够做真正 multi-hop research。

---

### 为什么更多轮可能更差？

成本：

$$
C(D)
$$

随 depth 增长。

同时 context noise 也增长：

$$
N(D)
$$

可能出现：

```text
over-search
重复 evidence
conflicting evidence
context interference
```

---

### 因此性能不是简单：

$$
Accuracy \uparrow
\quad
\text{as}
\quad
D\uparrow
$$

更可能：

```text
depth too low
→ insufficient evidence

moderate depth
→ best

depth too high
→ diminishing returns / interference
```

---

### Search Budget 不一定只有 Round Count

还可以包括：

```text
tool calls
documents visited
tokens read
latency
API cost
```

因此更完整：

$$
B
=
(
B_{\text{calls}},
B_{\text{tokens}},
B_{\text{time}},
B_{\text{cost}}
)
$$

---

## 6.18 Agent 应怎样决定 Stop Searching？ `[P1]`

这是 Search Policy 的核心之一。

---

### 最简单：Fixed Budget

```text
search exactly 3 times
```

优点：

* 简单；
* reproducible。

问题：

```text
easy question
→ waste search

hard question
→ insufficient search
```

---

### Confidence-based

模型估计：

$$
P(
\text{answer correct}
|
evidence
)
$$

超过 threshold 就 stop。

问题：

> LLM confidence 不一定 calibrated。

---

### Evidence Sufficiency

检查：

```text
是否已有支持所有关键 claims 的 evidence？
```

更贴近 research task。

---

### Value-of-Information 思想

继续搜索的期望收益：

$$
\mathbb E[
\Delta U
|
\text{one more search}
]
$$

与 cost：

$$
C_{\text{search}}
$$

比较。

如果：

$$
\mathbb E[\Delta U]
<
C_{\text{search}}
$$

应该 stop。

现实中很难精确算，但这是非常好的理论视角。

---

### RL View

Stop 本身就是 action：

```text
Search(...)
Search(...)
Answer(...)
```

如果 reward 中包含：

```text
correctness
-
search cost
```

policy 有可能学出 stopping behavior。

但需要防：

```text
cost penalty too large
→ never search
```

---

## 6.19 WebThinker 的 Think–Search–and–Draft 与普通 Search Agent 有什么区别？ `[P1]`

普通 Search Agent 常假设：

```text
先研究
↓
最后一次性写答案
```

WebThinker 则允许：

```text
Think
Search
Read
Draft Section A
Search
Read
Edit Section A
Draft Section B
...
```

其论文明确将 autonomous reasoning、information gathering 和 report drafting 交错进行。

---

### 为什么 Draft 也应该成为 Action？

长篇 research 中：

> 写作本身会暴露新的信息缺口。

例如：

```text
Section:
"The two methods differ mainly in..."

↓
写到这里发现
缺少 method B 的训练细节
↓
new search
```

因此：

```text
draft state
```

本身成为 reasoning state 的一部分。

---

### 这改变了 State

短 QA：

$$
s_t
=
question + evidence
$$

Deep Research：

$$
s_t
=
question
+
evidence
+
research plan
+
partial report
+
unresolved claims
$$

显著更复杂。

---

## 6.20 Real Web Environment 相比 Static Corpus 多了哪些训练变量？ `[P1]`

Static corpus：

```text
documents fixed
retriever fixed
results reproducible
```

---

### Real Web

至少多：

#### Dynamic Content

今天和明天页面可能不同。

---

#### Ranking Drift

Search engine ranking 会变化。

---

#### Page Failure

```text
404
403
captcha
timeout
JS loading
```

---

#### HTML / Layout

网页结构不统一。

---

#### Navigation

信息可能藏在：

```text
link
subpage
PDF
table
interactive element
```

---

#### Duplicates

多个网站互相转载。

---

#### Source Quality

SEO spam 与可靠来源混合。

---

#### Latency

不同网页响应速度不同。

---

### DeepResearcher 的核心观点之一

真实 Web interaction 不是一个无关紧要的 implementation detail，而会实际改变 agent 必须学习的能力。它将 RL 从 fixed-corpus RAG environment 推入 noisy、unstructured、dynamic Web。

---

### 训练复现因此更难

Static corpus 可以保存：

```text
corpus hash
```

Real Web 还需要：

```text
timestamp
URL
search provider
page snapshot
```

否则后续无法 replay。

---

## 6.21 为什么 Short-form QA Reward 不足以训练 Long-form Deep Research？ `[P1]`

Short QA：

```text
Question:
Who founded X?

Answer:
Alice
```

可以：

$$
R=
ExactMatch
$$

甚至：

$$
R\in\{0,1\}
$$

---

### Long-form Report

可能要求：

```text
介绍三种方法
比较优缺点
给出证据
引用来源
讨论争议
指出不确定性
```

不存在一个唯一 string。

---

### Exact Match 完全失效

两个都正确的 report：

```text
Report A
Report B
```

文本可以完全不同。

---

### Long-form Reward 需要考虑

```text
factual correctness
coverage
source attribution
citation correctness
coherence
instruction following
depth
redundancy
```

甚至：

```text
是否遗漏关键 subtopic
```

---

### 一个简单 scalar judge 也困难

如果：

$$
R=7.8
$$

你还要问：

> 为什么是 7.8？

对 RL 来说：

* calibration；
* hacking；
* distribution drift；

都会成为问题。

---

### DR Tulu 的出发点

就是 short-form RLVR 的 reward paradigm 不能自然延伸到 realistic long-form deep research，因此转向 rubric-based feedback。

---

## 6.22 DR Tulu 的 Evolving Rubrics 为什么需要随 Policy 演化？ `[P1]`

假设固定 rubric：

```text
report 必须包含:
A
B
C
```

早期 policy：

```text
只能找到 A
```

rubric 有区分度。

---

### 训练后 Policy 变强

policy 开始发现：

```text
D
E
F
```

这些可能也是高价值信息。

但固定 rubric 不知道。

于是：

```text
真正更好的 report
```

不一定得到更多 reward。

---

### Evolving Rubrics

DR Tulu 的 Reinforcement Learning with Evolving Rubrics 让 rubrics 与 policy 共同演化，使评分标准能够纳入 policy 新探索到的信息，并保持 on-policy discriminative feedback。

---

### 为什么这与普通 Reward Model 不一样？

普通固定 RM：

```text
train once
↓
freeze
↓
policy keeps changing
```

容易 distribution shift。

RLER 更强调：

```text
policy distribution evolves
↓
evaluation rubric evolves
```

试图让 evaluator 继续覆盖当前 policy frontier。

---

### 但会产生新风险

rubric 由 policy exploration 影响：

> 如果 policy 新发现的是错误信息怎么办？

所以必须考虑：

```text
rubric verification
source grounding
rubric drift
feedback loop
```

这些属于后面 Reward/Verification Macro 的深水问题。

---

# P2

## 6.23 Search Agent 的 Learning Unit 到底应该是 Query、Turn、Trajectory 还是 Report？ `[P2]`

这是非常重要的 formulation 问题。

---

### Query-level

每个 search query：

$$
q_t
$$

单独给 reward。

例如：

```text
retrieval recall
evidence relevance
```

优点：

> dense signal。

缺点：

> 一个 query 看起来相关，不一定对最终任务真正有用。

---

### Turn-level

一个：

```text
reason
+
search
+
observation
```

作为 credit unit。

更能表达：

> 这一轮 search 是否推进了 reasoning。

---

### Trajectory-level

整个：

```text
search → search → answer
```

一个 outcome reward。

优点：

* objective aligned；
* 不需要 judge 每一步。

缺点：

* credit sparse。

---

### Report-level

Deep Research：

```text
entire report
```

可能是最终 optimization unit。

但其中包含：

* 50 个 claims；
* 20 个 sources；
* 多个 research turns。

一个 scalar reward credit 极粗。

---

### 所以这里存在 Granularity Mismatch

```text
Reward Granularity
vs
Action Granularity
```

例如：

```text
report-level reward
↓
token-level policy update
```

中间隔了很多层。

---

### 这就是后面 Credit Assignment 研究的根本动力

```text
Outcome
↓
Trajectory
↓
Turn
↓
Search Action
↓
Token
```

必须回答：

> 信息怎么往下分？

---

## 6.24 Prompted Search Agent 与 RL-trained Search Agent 应怎样公平比较？ `[P2]`

不能简单：

```text
RL model accuracy 70
prompt model accuracy 65
```

就下结论。

---

### 需要控制 Backbone

同一个：

```text
Qwen-7B
```

---

### 控制 Search Environment

```text
same corpus
same retriever
same Top-K
same tool protocol
```

---

### 控制 Search Budget

例如：

$$
max\ search\ calls=5
$$

否则 RL agent 搜 10 次，prompt baseline 只能搜一次。

---

### 控制 Generation Budget

```text
max reasoning tokens
```

---

### 控制 Sampling

```text
temperature
top-p
```

---

### 至少比较三条线

```text
No Search
Prompted Search
RL-trained Search
```

最好再有：

```text
Retrieve-once
```

---

### 行为分析

除了 accuracy，还看：

```text
search frequency
average search depth
query diversity
evidence recall
invalid action
token cost
latency
```

---

### 最关键 Ablation

训练了 RL Search Agent 后：

> 它到底学到了“更会搜索”，还是仅仅“更会回答”？

可以做：

```text
remove search tool at eval
```

或：

```text
freeze generated evidence
```

来拆能力来源。

---

## 6.25 Open-Web RL 中“On-policy”应该怎样理解？ `[P2]`

经典 on-policy：

$$
\tau\sim\pi_\theta
$$

但 Open Web trajectory probability 还包含 environment：

$$
P(\tau)
=
\prod_t
\pi_\theta(a_t|s_t)
P_{\text{web}}(
o_t|s_t,a_t,time
)
$$

这里：

$$
P_{\text{web}}
$$

会随时间变化。

---

### 即使 Policy 不变

今天：

```text
Search("X")
→ result A
```

明天：

```text
Search("X")
→ result B
```

trajectory distribution 已经变了。

---

### 所以 On-policy 至少有两层

#### Policy On-policy

trajectory action 来自当前 policy。

#### Environment Freshness

observation 来自当前环境状态。

---

### Replay 更复杂

如果保存旧 trajectory：

```text
query
old observation
```

之后拿来训练：

> 它不仅是 stale policy data，也是 stale environment data。

---

### 因此 Open-Web RL 需要记录

```text
policy version
search timestamp
search provider
URL
page snapshot
tool version
```

---

### 严格意义

完全 exact on-policy + exact environment replay 在 real Web 上几乎很难实现。

因此工程上往往追求：

```text
bounded policy staleness
+
well-defined environment snapshot/provenance
```

而不是假装环境固定。

---

## 6.26 Deep Search 与 Deep Research 应该怎样分别设计 Environment 和 Evaluator？ `[P2]`

可以把二者区分为：

### Deep Search

目标：

> 通过多轮搜索找到足够 evidence，回答相对明确的问题。

输出通常：

```text
short answer
structured answer
```

---

### Deep Research

目标：

> 自主拆解问题、广泛搜集来源、比较和综合信息，产出长篇 research artifact。

输出：

```text
report
analysis
citations
```

---

### Environment

Deep Search：

```text
Search
Visit
Answer
```

可能够。

Deep Research：

```text
Search
Visit
Navigate
Extract
Take Notes
Draft
Inspect Draft
Edit
Cite
```

action state 更复杂。

---

### Evaluator

Deep Search：

```text
EM
F1
verifier
answer correctness
```

Deep Research：

```text
rubric
claim factuality
citation correctness
coverage
source diversity
report coherence
```

---

### Horizon

Deep Search：

```text
5–10 actions
```

Deep Research 可能：

```text
几十甚至上百 actions
```

---

### Credit

Deep Search：

```text
final answer reward
```

有时还能工作。

Deep Research：

> 一个 report-level scalar reward 给上百 actions credit，方差太高。

---

### 所以不要认为

```text
Deep Research
=
Search Agent × more steps
```

它同时改变：

```text
state
action
reward
horizon
artifact
evaluator
```

---

## 6.27 如果重新设计 Search-R1 类 Baseline，哪些部分应该保留，哪些部分必须扩展？ `[P2]`

这不是批评某篇论文，而是面试里的研究设计题。

---

### 应该保留：简单 Action Protocol

例如：

```text
Search
Answer
```

baseline 越简单：

> 越容易知道性能提升到底来自哪。

---

### 保留：Outcome Reward

作为最基础 control。

因为它：

```text
cheap
objective
minimal process assumptions
```

---

### 保留：Retrieved-token Mask

这是 training correctness，不是可选 trick。

---

### 保留：Same-prompt Group Rollout

便于研究 group-relative RL。

---

### 然后逐层扩展

#### Expansion 1：Search / Visit 分离

```text
Search
↓
snippet
↓
Visit
↓
full document
```

研究 evidence acquisition policy。

---

#### Expansion 2：Cost-aware Reward

加入：

```text
tool calls
tokens
latency
```

研究 stopping。

---

#### Expansion 3：Process / Credit

加入：

```text
turn contribution
fatal masking
critic
```

---

#### Expansion 4：Harder Data

避免：

```text
single-hop shortcut
```

要求真正 multi-hop。

---

#### Expansion 5：Adaptive Search Depth

不再固定：

```text
max 3
```

研究 minimal sufficient search。

---

#### Expansion 6：Context Management

处理：

```text
observation accumulation
```

---

#### Expansion 7：Retriever Training

不再假设 retriever 永远固定。

---

### 实验顺序必须单变量

不能一次：

```text
换 retriever
+
换 reward
+
换 dataset
+
换 model
```

然后说：

> 新算法提升 8%。

那没有归因意义。

---

## 6.28 Search Agent 论文应该怎样纵向比较，而不是逐篇背摘要？ `[P2]`

以后所有 Search Agent 论文都建议使用同一张表。

---

### 维度一：Problem

这篇工作到底认为上一代哪里不够？

例如：

```text
knowledge insufficiency
search not learned
context noise
credit assignment
zero-variance rollout
search depth
retriever mismatch
memory
multimodal evidence
```

---

### 维度二：State

模型每一步能看到什么？

```text
question
history
retrieved snippets
full pages
memory
draft report
```

---

### 维度三：Action Space

```text
Search
Visit
Answer

vs

Search
Browse
Draft
Edit
```

---

### 维度四：Environment

```text
static corpus
search simulator
real web
multimodal web
```

---

### 维度五：Data

```text
existing QA
synthetic tasks
verified tasks
evolving tasks
```

---

### 维度六：Training

```text
Prompting
SFT
DPO
PPO
GRPO
custom credit algorithm
```

---

### 维度七：Reward

```text
EM
rule verifier
outcome reward
process judge
rubric
evolving rubric
```

---

### 维度八：Credit

```text
trajectory-level
turn-level
token-level
contribution-weighted
critic
```

---

### 维度九：Context Management

```text
raw concat
Reason-in-Documents
refiner
memory
structured state
```

---

### 维度十：Evaluation

```text
short QA
multi-hop QA
GAIA
HLE
long-form report
sim-to-real
```

---

### 最终表

| 工作             | 主要瓶颈                         | Environment          | Search Policy           | Training            | Reward               | Context                     |
| -------------- | ---------------------------- | -------------------- | ----------------------- | ------------------- | -------------------- | --------------------------- |
| ReAct          | 静态 LLM 无外部交互                 | Wikipedia API        | Prompted                | Few-shot            | Task metric          | Raw observation             |
| Search-o1      | Reasoning knowledge gap      | Retrieval system     | Agentic retrieval       | Inference framework | Task metric          | Reason-in-Documents         |
| Search-R1      | Search 没被真正学习                | Multi-turn retrieval | Learned                 | RL                  | Outcome              | Retrieved-token mask        |
| WebThinker     | Search QA 不足以做 Web research  | Web navigation       | Search + browse + draft | Online DPO          | Composite preference | Deep Web Explorer           |
| DeepResearcher | Controlled RAG 与真实 Web 有 gap | Real Web             | End-to-end research     | RL                  | Task/research reward | Real Web observations       |
| DR Tulu        | Short QA reward 不适合长报告       | Deep research infra  | Long-form research      | RLER                | Evolving rubric      | Long-horizon research state |

Search-o1、Search-R1、WebThinker、DeepResearcher 和 DR Tulu 的这些定位分别由其论文描述支持。

---

# 6.29 Search Agent 的纵向发展图

可以先记成：

```text
ReAct
│
│ Reason + Action + Observation
↓
Search-o1
│
│ reasoning 中动态检索
│ Reason-in-Documents
↓
Search-R1
│
│ multi-turn search
│ outcome RL
│ retrieved-token masking
↓
WebThinker
│
│ search + navigation
│ think-search-draft
│ online DPO
↓
DeepResearcher
│
│ real-world web RL
│ noisy / dynamic environment
↓
DR Tulu
│
│ long-form deep research
│ reward no longer short-answer EM
│ evolving rubrics
↓
Long-horizon Research Agent
```

但不要把它理解成：

> 后一篇“取代”前一篇。

更准确：

```text
problem formulation
不断扩张
```

---

# 6.30 Search Agent 横向问题树

纵向 paper lineage 之外，还应该形成这张横向图：

```text
                         Search Agent
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          Search           Evidence         Control
             │                │                │
         Should search?    relevance         depth
         query             credibility       stop
         reformulate       conflict          budget
         route             redundancy        cost
             │                │                │
             └────────┬───────┴────────┬───────┘
                      │                │
                  Context          Learning
                      │                │
                  noise            reward
                  length           credit
                  memory           exploration
                  state            RL
```

这张图比单纯背：

```text
Search-R1
WebThinker
...
```

更重要。

因为后面的论文基本都可以放进某一个 branch。

---

# 6.31 Search Agent 高频连环追问

## 第一组：RAG → Search Agent

```text
RAG 是什么？
↓
Agentic RAG 是什么？
↓
Search Agent 区别？
↓
为什么 Search 是 sequential decision？
↓
Search action 怎样影响下一 state？
↓
为什么 Retrieve-once 必须做 baseline？
```

---

## 第二组：Search-o1

```text
Search-o1 在解决什么？
↓
为什么 reasoning model 还需要 search？
↓
Reason-in-Documents 为什么存在？
↓
为什么不直接塞完整文档？
↓
它解决的是 retrieval 还是 context management？
```

---

## 第三组：Search-R1

```text
Search-R1 最大变化？
↓
为什么需要 RL？
↓
outcome reward 为什么能学 query？
↓
为什么 mask retrieved tokens？
↓
all-success/all-fail group 会怎样？
↓
哪里开始需要 credit assignment？
```

---

## 第四组：Search Policy

```text
Should search?
↓
What query?
↓
Need reformulation?
↓
How deep?
↓
When stop?
↓
如何平衡 accuracy 与 search cost？
```

---

## 第五组：Deep Research

```text
Search QA 和 Deep Research 区别？
↓
为什么 Web navigation 更复杂？
↓
为什么 final EM 不够？
↓
report 怎么 reward？
↓
rubric 为什么可能 drift？
↓
evolving rubric 又有什么风险？
```

---

# 6.32 Self-test

## Self-test 1

下面哪一个更接近传统 RAG？

```text
Question
↓
Retrieve Top-5
↓
LLM Answer
```

答案：

> 传统 RAG。

---

## Self-test 2

下面为什么已经属于 sequential search？

```text
Search(q0)
↓
observe o0
↓
Search(f(q,o0))
```

因为：

$$
q_1
$$

依赖：

$$
o_0
$$

第一轮 action 改变了第二轮 decision state。

---

## Self-test 3

Search-R1 中：

```text
Search Action Tokens
```

是否计算 policy loss？

是。

因为它们是模型 action。

Retrieved document tokens 是否计算？

否。

但它们仍然进入后续 context。

---

## Self-test 4

为什么：

```text
Retrieve Top-20 once
```

是多轮 Search Agent 非常重要的 baseline？

因为否则无法区分：

> adaptive search 真正有价值

还是：

> 只是 Agent 总共看了更多 documents。

---

## Self-test 5

如果长报告 factual correctness 很高，但：

```text
所有 citations 都指错网页
```

是否可以只用 factual reward？

不能。

Deep Research evaluator 需要把：

```text
claim quality
citation correctness
```

拆开。

---

# 6.33 推导 / 分析题

## 分析题 1：Search Cost Objective

定义：

$$
R
=
R_{\text{answer}}
-
\lambda N_{\text{search}}
$$

回答：

如果：

$$
\lambda
$$

太大，会发生什么？

可能：

```text
policy learns not to search
```

甚至在需要 external knowledge 时直接猜。

如果：

$$
\lambda=0
$$

可能：

```text
over-search
```

所以这个 objective 实际在控制：

$$
Accuracy
\leftrightarrow
Cost
$$

trade-off。

---

## 分析题 2：Search Depth

假设：

$$
P(\text{correct}|D)
$$

随 search depth \(D\)：

```text
D=0  40%
D=1  60%
D=2  70%
D=3  73%
D=4  73%
D=5  71%
```

解释为什么：

> 最大 depth 不一定最优。

因为：

```text
diminishing returns
+
context noise
+
cost
```

---

## 分析题 3：Outcome Credit

Trajectory：

```text
Search A   good
Search B   useless
Search C   good
Answer     correct
```

若：

$$
R=1
$$

vanilla trajectory-level outcome reward 对前三次 Search 的 signal 有何问题？

答案：

> 三个 action 获得同样 outcome direction，无法区分 B 的无效贡献。

这就是后续：

```text
CW-GRPO / Critic
```

等方法的动机。

---

# 6.34 Debug 题

## Debug 1：Agent 搜索次数越来越多，Accuracy 只提高一点

检查：

```text
reward 是否没有 search cost
stop action 是否学会
context 是否开始 interference
retriever 是否重复结果
query 是否重复
```

指标：

```text
accuracy
search calls
unique evidence
latency
token cost
```

必须一起看。

---

## Debug 2：Agent 几乎从不搜索

检查：

```text
training questions 是否可凭 parametric knowledge 回答
search latency / penalty 是否过大
tool action reward 是否被错误 mask
parser failure
search observation 是否低质量
```

不能立即说：

> 模型不会用工具。

---

## Debug 3：Search 次数正常，但 Evidence Recall 很低

问题更可能在：

```text
query formulation
retriever
corpus
```

而不是 answer synthesis。

---

## Debug 4：有 Gold Evidence 时回答正确率 90%，整体只有 40%

瓶颈更可能是：

```text
evidence acquisition
```

而不是 answer reasoning。

---

## Debug 5：真实 Web 结果明显差于 Offline Corpus

检查：

```text
search provider
dynamic ranking
page parser
JS pages
timeouts
stale links
real-web noise
```

这就是：

```text
sim / offline
→ real
```

environment gap。

---

# 6.35 系统设计题

## 系统设计题 1：设计最小 Search Agent Baseline

最小 action space：

```text
Search(query)
Visit(doc_id)
Answer(text)
```

State：

```text
question
history
observations
remaining budget
```

Termination：

```text
Answer
max_steps
timeout
```

Reward：

```text
final answer correctness
```

先不要：

```text
memory
critic
process reward
adaptive retriever
```

目的是建立清晰 baseline。

---

## 系统设计题 2：如何证明 Multi-turn Search 真有价值？

至少比较：

```text
No Search
Retrieve Once
Fixed Multi-hop Retrieval
Prompted Search Agent
RL Search Agent
```

控制：

```text
same model
same corpus
same retrieval budget
```

再报告：

```text
accuracy
cost
search depth
evidence recall
```

---

## 系统设计题 3：如何从 QA Search Agent 扩展为 Deep Research？

逐层加：

```text
Search
 ↓
Visit
 ↓
Navigation
 ↓
Notes / Memory
 ↓
Draft
 ↓
Citation
 ↓
Edit
```

同时 evaluator 从：

```text
EM
```

扩成：

```text
claim factuality
coverage
citation quality
source quality
coherence
```

这不是单纯增加 max_steps。

---

# 6.36 论文学习模板

以后看到任何 Search Agent 新论文，不建议先写：

```text
作者提出了 X
实验提升 Y
```

而先填这张模板。

```text
### Previous Bottleneck

上一代方法具体哪里失败？

### Problem Formulation

论文重新定义了什么问题？

### State

Agent 每一步看得到什么？

### Action Space

Search / Visit / Memory / Draft / ...

### Environment

Static corpus / simulator / real web / multimodal

### Data

任务从哪里来？
是否 verified？
是否 synthetic？

### Training

Prompt / SFT / DPO / PPO / GRPO / custom

### Reward

Outcome / Process / Judge / Rubric / Verifier

### Credit

Trajectory / Turn / Step / Token

### Context

Raw concat / refinement / memory / structured state

### Evaluation

测什么？
有没有成本指标？

### New Assumption

它依赖了什么新的假设？

### New Failure Mode

解决旧问题后又引入了什么？
```

只有这样才会真正形成：

> 论文之间的技术依赖图。

---

# 6.37 本章最小知识图

最终脑中至少应形成两张图。

第一张是历史纵向：

```text
ReAct
  │
  │ reasoning + acting
  ↓
Search-o1
  │
  │ search-enhanced reasoning
  │ Reason-in-Documents
  ↓
Search-R1
  │
  │ learned multi-turn search policy
  │ outcome RL
  ↓
WebThinker
  │
  │ web navigation
  │ think-search-draft
  ↓
DeepResearcher
  │
  │ real-web RL
  ↓
DR Tulu
  │
  │ long-form research
  │ evolving evaluation
  ↓
Deep Research Agent
```

第二张是技术横向：

```text
Search Agent
    │
    ├── Search Decision
    │     ├── Should Search
    │     ├── Query
    │     ├── Reformulate
    │     └── Stop
    │
    ├── Retrieval
    │     ├── Corpus
    │     ├── Retriever
    │     ├── Visit
    │     └── Evidence
    │
    ├── Context
    │     ├── Raw Observation
    │     ├── Refinement
    │     ├── Memory
    │     └── Structured State
    │
    ├── RL
    │     ├── Outcome
    │     ├── Credit
    │     ├── Exploration
    │     └── Group Rollout
    │
    └── Environment
          ├── Offline Corpus
          ├── Simulator
          ├── Real Web
          └── Deep Research
```

Macro 6 到这里建立的是：

> **Search Agent 是怎么从 RAG / ReAct 演化出来，以及为什么从 Search-o1 → Search-R1 → WebThinker → DeepResearcher → DR Tulu 后，研究问题逐渐从“能不能搜”转向“怎么探索、怎么控制 horizon、怎么管理上下文、怎么给长程研究行为 reward”。**

Macro 7 接下来就进入这条线的第二阶段：

```text
Data / Exploration
        │
        ├── SearchArt
        ├── SearchMaster
        ├── HiExp
        └── Evolving Rollouts

Environment / Long Horizon
        │
        ├── SearchGym
        ├── Context Interference
        ├── InfoFlow
        └── Table-as-Search
```

也就是不再问：

> “Search Agent 是什么？”

而开始问：

> **它到底应该在哪些任务上训练、如何产生足够有信息量的 rollout、环境怎样设计、为什么 horizon 一长就开始出现 context / exploration / reward-density 问题。**

## 7. Data / Environment / Evaluation / Exploration

前面的 Macro 解决了：

```text
模型怎么训练？
RL objective 怎么构造？
Agent trajectory 怎么表示？
Search Agent 怎么行动？
```

但算法项目最终能不能成立，还取决于另一组经常被低估的问题：

```text
训练数据是不是泄漏的？
任务是不是真的需要搜索？
环境里到底有没有答案？
baseline 公不公平？
失败运行算不算 denominator？
mean 提升是不是 seed 偶然？
LLM Judge 靠不靠谱？
synthetic task 有没有 shortcut？
simulator 学到的东西能不能迁移到真实 Web？
```

这一章因此分成两部分。

第一部分是所有算法岗都应该掌握的实验方法论：

```text
Dataset
Evaluation
Statistics
Reproducibility
Failure Analysis
```

第二部分是 Search Agent 特有的数据 / 环境 / exploration 问题：

```text
SearchArt
SearchMaster
HiExp
Evolving Rollouts
SearchGym
Context Interference
InfoFlow
Table-as-Search
```

不能因为后半部分论文更“新”就把前半部分基础实验方法挤掉。

---

## 7.0 问题矩阵

| 编号   | 问题                                                                        | 等级 |
| ---- | ------------------------------------------------------------------------- | -- |
| 7.1  | Train / Dev / Test 为什么必须严格分开？                                             | P0 |
| 7.2  | Answer Leakage 与 Evidence Leakage 有什么区别？                                  | P0 |
| 7.3  | Benchmark Contamination 是什么？                                              | P0 |
| 7.4  | Seed、Dataset Version、Corpus Hash 为什么都要记录？                                 | P0 |
| 7.5  | Accuracy、EM、F1、Pass@K 分别什么时候适用？                                           | P0 |
| 7.6  | Baseline Fairness 最基本应该控制什么？                                              | P0 |
| 7.7  | 为什么 Mean 必须配 Variance？                                                    | P0 |
| 7.8  | Execution Failure 与 Semantic Failure 有什么区别？                               | P0 |
| 7.9  | Synthetic Data 的主要风险是什么？                                                  | P0 |
| 7.10 | Fault Injection 为什么值得成为 Agent Evaluation 的标准能力？                           | P0 |
| 7.11 | Missing / Failed Run 的 denominator 应怎样处理？                                 | P1 |
| 7.12 | Bootstrap Confidence Interval 怎么做？为什么适合复杂 Agent Metric？                   | P1 |
| 7.13 | Statistical Significance 与 Practical Significance 有什么区别？                  | P1 |
| 7.14 | Experiment Artifact / Registry 应至少保存什么？                                   | P1 |
| 7.15 | LLM-as-a-Judge 应怎样验证可靠性？                                                  | P1 |
| 7.16 | Adversarial Evaluation 应怎样设计？                                             | P1 |
| 7.17 | Search Task 怎样验证“真的需要搜索”？                                                 | P1 |
| 7.18 | SearchArt 为什么强调 Synthetic + Verified + Long-horizon？                      | P1 |
| 7.19 | SearchMaster 为什么引入 Evidence Chain、Search Depth 和 Over-Opening 控制？         | P1 |
| 7.20 | HiExp 为什么认为纯 stochastic exploration 不够？                                   | P1 |
| 7.21 | Evolving Rollouts 为什么要复用历史 Rollout Experience？                            | P1 |
| 7.22 | SearchGym 为什么把 Environment Alignment 当成训练问题？                              | P1 |
| 7.23 | Context Interference 到底来自哪里？                                              | P1 |
| 7.24 | InfoFlow 的 Reward Density 到底是什么？                                          | P1 |
| 7.25 | Table-as-Search 为什么把搜索改写成 Table Completion？                               | P1 |
| 7.26 | 怎样做 Benchmark Contamination Audit？                                        | P2 |
| 7.27 | Sim-to-Real Gap 应怎样严格验证？                                                  | P2 |
| 7.28 | Search Difficulty 应该用 Success Rate、Hop Count 还是 Search Depth 定义？          | P2 |
| 7.29 | Self-generated Search Data 如何避免 Curriculum Collapse / Distribution Drift？ | P2 |
| 7.30 | Historical Experience Repository 怎样避免把错误经验越积越多？                           | P2 |
| 7.31 | Agent Evaluation 怎样同时处理 Accuracy、Cost、Latency 和 Robustness？               | P2 |
| 7.32 | 怎样设计一套真正可复现的 Agent RL Experiment Protocol？                                | P2 |

---

# 7A. Dataset / Split / Leakage

## 7.1 Train / Dev / Test 为什么必须严格分开？ `[P0]`

### 30～60 秒回答

最基本的划分：

```text
Train
↓
用于参数更新

Dev / Validation
↓
用于模型选择、超参数、early stopping

Test
↓
最终一次性评估泛化
```

如果 test 数据参与：

```text
prompt engineering
reward design
hyperparameter tuning
failure analysis 后针对性修改
```

那么它事实上已经变成 dev set。

---

### Search Agent 里为什么更复杂？

因为除了 question，还存在：

```text
document corpus
search index
retrieval evidence
trajectory
```

所以不仅要问：

> Question 有没有泄漏？

还要问：

> Test question 对应的答案 / evidence 是否以不合理方式进入训练数据或 synthetic data generation？

---

### 可能需要的 Split

#### Query Split

测试 query 不出现在 train。

#### Entity Split

测试实体不出现在训练任务。

#### Temporal Split

例如：

```text
Train documents: ≤ 2025
Test questions: 2026 facts
```

测试 freshness。

#### Corpus Split

训练构造 synthetic task 使用的 corpus 与测试 benchmark 的 evidence corpus 做隔离。

---

### 最重要原则

```text
Test
不是“没有做 gradient 的数据”。

Test
是“在所有设计决定完成前都不应该被使用的数据”。
```

---

## 7.2 Answer Leakage 与 Evidence Leakage 有什么区别？ `[P0]`

### Answer Leakage

答案直接进入模型可见输入。

例如 question：

```text
Who founded X?
```

retrieval result：

```text
Answer: Alice founded X.
```

如果这个文档本身是人工为 benchmark 构造的 answer key，而不是真实 corpus evidence，就是直接 leakage。

---

### Evidence Leakage

更隐蔽。

训练任务生成时可能先知道 gold answer：

```text
Alice
```

然后生成一篇 synthetic document：

```text
X was founded by Alice.
```

再让 Agent 搜索。

表面上没有：

```text
Answer = Alice
```

字段。

但 retrieval corpus 已经人为注入了精准支持答案的 evidence。

---

### 为什么 Evidence Leakage 也危险？

因为 Agent 可能根本没有学：

> 如何在真实复杂环境中发现 evidence。

它只是在：

> 一个为这个问题量身定制的 corpus 中找答案。

---

### Search Data 尤其要检查

```text
Question generation
↓
Answer generation
↓
Evidence generation
↓
Corpus insertion
```

是否共享同一个 generator / gold information。

---

## 7.3 Benchmark Contamination 是什么？ `[P0]`

Benchmark contamination 指：

> 测试题、答案或高度等价内容已经出现在模型训练 / post-training / data generation pipeline 中。

来源可以是：

```text
Pretraining
SFT
RL training
Synthetic data
Prompt examples
Experience repository
Retrieved corpus
```

---

### 为什么大模型尤其难审计？

因为 pretrained model 的原始 training corpus 通常巨大且不完全公开。

因此无法简单说：

```text
我自己的 RL train set 没 test
→ benchmark 一定没有 contamination
```

---

### Search Agent 还有一个特别问题

即使模型本身没有记住 benchmark，

搜索工具可能直接搜索到：

```text
benchmark solution page
GitHub answer
discussion forum
```

于是测试变成：

```text
search benchmark answer
```

而不是：

```text
solve task using primary evidence
```

---

### 所以 benchmark contamination 至少分

```text
model contamination
dataset contamination
retrieval contamination
evaluation leakage
```

---

## 7.4 Seed、Dataset Version、Corpus Hash 为什么都要记录？ `[P0]`

只记录：

```text
seed = 42
```

远远不够。

---

### Seed

控制随机过程：

```text
sampling
dataset shuffle
fault injection
environment randomness
```

---

### Dataset Version

如果：

```text
train.jsonl
```

后来加了 500 个任务，

即使 seed 一样：

> sampling sequence 也已经对应不同数据。

---

### Corpus Version

Search Agent 依赖 retrieval corpus。

例如：

```text
corpus_v1
```

和：

```text
corpus_v2
```

只差 10 篇文档，

也可能让任务：

```text
unsolvable
→ solvable
```

---

### Hash

最好记录：

$$
H(\text{dataset})
$$

$$
H(\text{corpus})
$$

例如：

```text
SHA256
```

证明本次实验到底用了哪个精确 artifact。

---

### 为什么文件名不够？

```text
nq_train.jsonl
```

可以在不改名字的情况下被修改。

Hash 才是 content identity。

---

## 7.5 Accuracy、EM、F1、Pass@K 分别什么时候适用？ `[P0]`

### Accuracy

分类 / 可判断 exact correctness：

$$
Accuracy
=
\frac{
N_{\text{correct}}
}{
N
}
$$

---

### Exact Match

对 QA：

$$
EM
=
\mathbb 1[
normalize(pred)
=
normalize(gold)
]
$$

适合：

```text
short factual answers
```

但对：

```text
长文本
同义表达
```

过于严格。

---

### Token F1

比较 prediction 和 gold token overlap：

$$
Precision
=
\frac{|P\cap G|}{|P|}
$$

$$
Recall
=
\frac{|P\cap G|}{|G|}
$$

$$
F1
=
\frac{
2PR
}{
P+R
}
$$

适合答案 span 不完全一致时。

---

### Pass@K

生成 \(K\) 次：

> 至少一个成功的概率 / estimator。

它衡量：

```text
模型分布里有没有正确解
```

而不是：

```text
单次最常见输出是否正确
```

---

### Pass@1 vs Pass@K

如果：

```text
pass@1 = 30%
pass@16 = 90%
```

说明模型：

> 有很强潜在探索能力，但单样本可靠性不高。

对 GRPO rollout 来说这很重要。

---

## 7.6 Baseline Fairness 最基本应该控制什么？ `[P0]`

比较 Search Agent A / B 时至少控制：

```text
same backbone
same checkpoint
same corpus
same retriever
same tool APIs
same max search calls
same token budget
same sampling settings
same evaluator
```

---

### 典型不公平

A：

```text
Top-20 retrieval
5 search rounds
32K context
```

B：

```text
Top-5 retrieval
1 round
8K context
```

然后说：

> A 的 policy 更强。

结论无法成立。

---

### 如果算法本身就是改变 Budget 怎么办？

例如 AutoSearch 就要学 adaptive depth。

那应该：

```text
固定 cost
比较 accuracy

或者

固定 accuracy
比较 cost
```

以及绘制：

```text
accuracy-cost Pareto curve
```

而不是强行所有系统搜索次数相同。

---

## 7.7 为什么 Mean 必须配 Variance？ `[P0]`

假设两个算法：

```text
A:
70, 71, 69, 70, 70

B:
60, 80, 55, 85, 70
```

mean 都：

$$
70
$$

但稳定性完全不同。

---

### 常见报告

$$
\bar x
\pm
s
$$

其中：

$$
s
=
\sqrt{
\frac{
\sum_i(x_i-\bar x)^2
}{
n-1
}
}
$$

---

### RL 为什么尤其需要？

RL training 有：

```text
rollout randomness
reward sparsity
optimization instability
environment stochasticity
```

单 seed：

```text
+3 points
```

很可能只是 lucky run。

---

### Mean 还应该配什么？

根据任务：

```text
std
confidence interval
per-task distribution
failure rate
median
```

---

## 7.8 Execution Failure 与 Semantic Failure 有什么区别？ `[P0]`

### Execution Failure

工具没有正确执行。

例如：

```text
Timeout
HTTP 500
InvalidArgument
browser crash
```

---

### Semantic Failure

工具正常执行，但结果对任务没帮助或是错误信息。

例如：

```text
Search("X founder")
↓
200 OK
↓
返回 10 个无关文档
```

这是 semantic retrieval failure。

---

### 为什么要拆？

如果所有失败统一：

```text
success = 0
```

无法知道：

```text
Agent query 差
Retriever 差
API 挂了
```

哪一层有问题。

---

### 推荐指标

```text
execution_success_rate
semantic_success_rate
task_success_rate
```

三个层次。

---

## 7.9 Synthetic Data 的主要风险是什么？ `[P0]`

Synthetic data 很有价值，因为可以扩大训练规模。

但常见风险包括：

### Generator Bias

所有问题都由同一个 LLM 生成：

```text
句式
难度
知识范围
推理结构
```

高度同质。

---

### Shortcut

表面 multi-hop：

```text
A → B → C
```

但答案其实能直接从第一篇文档找到。

Agent 不需要真的多跳。

---

### Answer Leakage

生成 question 时已经显式把 answer embedding 到 wording。

---

### Evidence Leakage

corpus 对任务过度定制。

---

### Unrealistic Difficulty

Synthetic question 很“复杂”，但不符合真实用户任务。

---

### Verifier Coupling

同一个模型：

```text
generate task
solve task
judge task
```

容易共享系统性错误。

---

### 因此 Synthetic 不等于低质量

关键是：

```text
generate
↓
verify
↓
filter
↓
measure diversity/difficulty
```

---

## 7.10 Fault Injection 为什么值得成为 Agent Evaluation 的标准能力？ `[P0]`

普通 QA benchmark 默认环境：

```text
永远成功
```

真实 Agent 系统不是。

---

### 可以注入

```text
Timeout
TransientError
InvalidArgument
NotFound
RateLimit
partial response
```

---

### 为什么值得测？

因为 Agent 的能力包括：

```text
retry?
reformulate?
switch tool?
stop?
escalate?
```

而不仅是：

> 正常环境下会不会解题。

---

### Deterministic Fault Injection

最好让 failure schedule 可复现。

例如：

$$
f(
task\_id,
rollout\_id,
step
)
\rightarrow
failure
$$

而不是：

```python
if random.random() < 0.2:
```

让 benchmark 每次都不一样。

---

# P1

## 7.11 Missing / Failed Run 的 Denominator 应怎样处理？ `[P1]`

假设测试 100 个任务：

```text
80 completed
10 timeout
10 crashed
```

completed 中：

```text
60 correct
```

---

### 方案一：只算 Completed

$$
Accuracy
=
\frac{60}{80}
=
75\%
$$

看起来很好。

但忽略：

```text
20% 的任务系统根本没完成
```

---

### 方案二：失败全算错

$$
Accuracy
=
\frac{60}{100}
=
60\%
$$

更接近 end-to-end success。

---

### 正确做法通常是同时报告

```text
Execution Success = 80/100 = 80%

Conditional Accuracy
= 60/80 = 75%

End-to-End Accuracy
= 60/100 = 60%
```

这样可以区分：

```text
系统可靠性
vs
模型语义正确性
```

---

### 为什么不能偷偷 Drop？

如果：

```text
drop failures
```

算法只要让困难样本 crash：

> conditional accuracy 反而可能提高。

这是严重 selection bias。

---

## 7.12 Bootstrap Confidence Interval 怎么做？为什么适合复杂 Agent Metric？ `[P1]`

假设 benchmark 有：

$$
N
$$

个 tasks。

观测 metric：

$$
M(D)
$$

---

### Bootstrap

从原 benchmark：

$$
D
=
\{x_1,\ldots,x_N\}
$$

有放回采样：

$$
D^{(b)}
$$

大小仍为：

$$
N
$$

计算：

$$
M^{(b)}
$$

重复：

$$
B
$$

次，例如：

$$
B=1000
$$

得到 empirical distribution。

95% percentile CI：

$$
[
Q_{0.025},
Q_{0.975}
]
$$

---

### 为什么适合 Agent Metric？

因为很多 metric 不容易写出标准解析方差：

```text
pass@k
cost-adjusted success
multi-benchmark aggregate
trajectory metric
```

Bootstrap 不要求先推导 metric 的正态方差公式。

---

### Paired Bootstrap

比较算法 A / B 时：

同一次 bootstrap 抽相同 task IDs：

$$
\Delta^{(b)}
=
M_A^{(b)}
-
M_B^{(b)}
$$

比各自独立 bootstrap 更好利用 task-level pairing。

---

### Bootstrap Unit 很重要

如果一个 task 有：

```text
16 rollouts
```

不能随便把所有 rollout 当成独立 sample。

更合理的 resampling unit 可能是：

```text
task
```

否则会低估 uncertainty。

---

## 7.13 Statistical Significance 与 Practical Significance 有什么区别？ `[P1]`

假设：

```text
A = 70.0%
B = 70.2%
```

有 1,000,000 个测试任务。

可能：

```text
p < 0.001
```

统计显著。

但：

$$
+0.2\%
$$

可能没有实际价值。

---

### 反过来

小 benchmark：

```text
A = 60%
B = 68%
```

但只有 50 道题。

CI 很宽。

实际 effect 看起来大，但统计不确定。

---

### 所以应该同时看

```text
effect size
confidence interval
statistical test
system cost
```

---

### Agent 尤其要看 Cost

如果：

```text
Accuracy +1%
Search Calls +500%
Latency +400%
```

是否值得，要看 deployment objective。

不能只写：

> SOTA +1%。

---

## 7.14 Experiment Artifact / Registry 应至少保存什么？ `[P1]`

一次实验至少应该能回答：

> 这个数字是怎么来的？

建议保存：

```text
run_id
timestamp
git commit
git dirty state
config
model checkpoint
tokenizer
dataset hash
corpus hash
seed
environment version
dependencies
hardware
```

---

### RL 还要加

```text
policy version
reference checkpoint
reward implementation
verifier version
rollout config
sampling config
```

---

### Outputs

至少：

```text
metrics.json
manifest.json
trajectories.jsonl
training logs
checkpoint
evaluation predictions
```

---

### 为什么 Trajectory 也要保存？

只看：

```text
accuracy = 68%
```

无法 debug：

```text
为什么错？
search 到了什么？
哪一步失败？
```

Agent evaluation 没 trajectory 几乎无法分析 failure。

---

## 7.15 LLM-as-a-Judge 应怎样验证可靠性？ `[P1]`

不能因为：

```text
GPT-X 很强
```

就认为 judge ground truth。

---

### Human Agreement

抽样人工标注：

$$
Agreement(
LLM,
Human
)
$$

例如：

```text
accuracy
Cohen's κ
rank correlation
```

---

### Position Bias

A/B 顺序交换：

```text
Judge(A,B)
```

和：

```text
Judge(B,A)
```

应该尽量一致。

---

### Verbosity Bias

同一内容：

```text
short
vs
long verbose version
```

判断是否偏向更长文本。

---

### Self-preference

如果 judge 与被评模型同 family：

> 是否偏爱自己风格？

---

### Repeat Consistency

temperature > 0 时多次 judge：

```text
7
8
6
9
```

说明 variance 很高。

---

### Rubric Sensitivity

改变 rubric wording 后结果是否大幅变化？

---

### 最终不要只报告 Judge Score

还要报告：

```text
judge-human agreement
judge consistency
bias probes
```

---

## 7.16 Adversarial Evaluation 应怎样设计？ `[P1]`

Search Agent 不应该只在“干净检索”上评估。

可以构造：

### Irrelevant High-ranked Evidence

正确 evidence 在：

```text
rank 8
```

前面都是诱导噪声。

---

### Contradictory Sources

```text
source A says X
source B says not X
```

测试 source comparison。

---

### Duplicate Evidence

Top-10 实际都是同一新闻转载。

测试是否误以为：

> 10 个 source 一致。

---

### Stale Evidence

旧年份结果排名更高。

---

### Search Poisoning

页面故意包含：

```text
Ignore previous instructions...
```

测试 observation robustness。

---

### False Snippet / Correct Page

snippet misleading，但 Visit 后正文正确。

测试 agent 是否会深读。

---

### Adversarial 的意义

不是为了：

> 把 benchmark 做得很难。

而是针对明确 failure hypothesis 做 stress test。

---

# 7B. Search Data / Exploration

## 7.17 Search Task 怎样验证“真的需要搜索”？ `[P1]`

如果训练任务：

```text
Who wrote Harry Potter?
```

强模型不用任何搜索也能答。

即使 trajectory：

```text
search
search
answer
```

也不能证明 search policy 学到了什么。

---

### Search-disabled Test

直接禁用 search：

$$
Acc_{\text{no-search}}
$$

如果：

$$
Acc_{\text{no-search}}
\approx
Acc_{\text{search}}
$$

说明任务不是好的 search-training data。

---

### Evidence Necessity

理想任务满足：

```text
parametric knowledge insufficient
+
external evidence available
+
multi-step search useful
```

---

### Multi-hop Necessity

再检查：

> 是否可以用一个 query 直接拿最终答案？

如果可以：

```text
伪 multi-hop
```

---

### Difficulty 不能只看 Answer Success

一个任务可能：

```text
成功率 20%
```

是因为模型不会 reasoning，

并不代表 search depth 高。

后面的 SearchMaster 正是在这里做了更细的控制。

---

## 7.18 SearchArt 为什么强调 Synthetic + Verified + Long-horizon？ `[P1]`

SearchArt 关注的问题是：

> Long-horizon Search Agent 缺少规模足够大、复杂度足够高、又能验证质量的训练任务。

它从 Web documents 和自动生成的 evidence graphs 构造 search/research/user-oriented tasks，并通过 QA consistency、trajectory quality、retrieved-evidence relevance 等检查过滤，再用于 SFT + RL post-training。

---

### 为什么 Synthetic？

真实人工 deep-search tasks：

```text
贵
少
扩展慢
```

synthetic 可以规模化。

---

### 为什么必须 Verified？

因为自动生成很容易产生：

```text
question unsupported
answer wrong
fake multi-hop
bad evidence chain
```

如果直接 RL：

> verifier 的错误会变成 reward signal。

---

### 为什么 Evidence Graph 有帮助？

它显式构造：

```text
Evidence A
   ↓
Entity B
   ↓
Evidence C
   ↓
Answer
```

相比“随机写一个复杂问题”，更容易确保任务真的存在多步 evidence dependency。

---

### SearchArt 的核心思想

```text
不是只 scale rollout

而是先 scale
可验证的长程任务
```

这说明 Search Agent 训练瓶颈不仅是算法，也可能是：

```text
training task supply
```

---

## 7.19 SearchMaster 为什么引入 Evidence Chain、Search Depth 和 Over-Opening 控制？ `[P1]`

SearchMaster 使用 self-play：同一个模型既生成 search task，又尝试解决和验证任务；其目标是减少对人工 QA 和 expert demonstrations 的依赖。

但 self-generated data 会出现三个典型 failure。

---

### Failure 1：Pseudo Multi-hop

生成的问题表面很复杂，

但实际上：

```text
一个文档
就能直接回答
```

所以引入 Evidence-Chain Generator，让任务建立在明确 cross-document evidence chain 上。

---

### Failure 2：Success Rate 不等于 Search Difficulty

一个任务 success rate 低，

可能只是：

```text
语言难
reasoning 难
```

而不是：

```text
需要更深 search
```

因此 SearchMaster 使用 Search-Depth Reward，以成功 trajectory 所需的 search depth 作为任务价值的一部分。

---

### Failure 3：Over-Opening

Agent：

```text
打开很多文档
```

看起来 horizon 很长，

但没有 targeted evidence acquisition。

所以加入 Over-Opening Penalty 抑制“长但浅”的 browsing。

---

### 很值得背的一条因果链

```text
Long trajectory
≠
Long-horizon reasoning

很多 tool calls
≠
有效 search depth
```

SearchMaster 的价值就在于试图区分这些。

---

## 7.20 HiExp 为什么认为纯 Stochastic Exploration 不够？ `[P1]`

HiExp 的出发点是：

> Agent RL 每轮都从随机 sampling 重新探索，会产生大量低效、重复 trajectory。

它通过对已有 trajectories 做 contrastive analysis 和 multi-level clustering，提炼成 hierarchical experience，再让后续训练利用这些经验，使 stochastic exploration 更有方向。

---

### Vanilla Exploration

```text
Prompt
↓
sample 16 rollouts
↓
many repeat same mistakes
↓
throw away
↓
next iteration
重新犯
```

---

### Experience-driven

```text
historical trajectories
↓
compare success/failure
↓
extract reusable patterns
↓
hierarchical experience
↓
guide future exploration
```

---

### Hierarchical 为什么合理？

经验可能有不同 abstraction level：

```text
低层：
某类 query 应该换关键词

中层：
多跳任务先定位实体再找属性

高层：
当 evidence 冲突时优先交叉验证
```

如果把所有经验写成一长段文本：

> retrieval 本身又会变成新的问题。

---

### 与 SFT Best-of-N 有什么区别？

HiExp 不只是：

```text
选最优 trajectory
→ SFT
```

它强调：

> 从 trajectory 之间的对比中抽取更抽象、可复用的经验。

---

## 7.21 Evolving Rollouts 为什么要复用历史 Rollout Experience？ `[P1]`

Group RL 的一个严重浪费：

```text
all rewards equal
↓
zero variance
↓
group-relative advantage = 0
```

这些 expensive rollouts 对参数更新几乎没有直接信号。

Evolving Rollouts 的思路是把历史 reward-labeled trajectories 提炼成 strategic experiences，并在未来 rollout 中作为 in-context guidance 使用，因此除了 parameter-space optimization，又引入 context-space optimization；论文特别强调这样可以从 zero-variance groups 中回收信息。该工作发表于 ICML 2026。

---

### Vanilla GRPO

```text
Rollout Group
↓
Rewards
↓
Advantage
↓
Parameter Update
↓
raw trajectories disappear
```

---

### Evolving Rollouts

```text
Rollout Group
   │
   ├── policy update
   │
   └── experience extraction
            ↓
     experience repository
            ↓
      future rollout context
```

形成：

```text
Policy improves
      ↕
Experience repository improves
```

---

### 为什么这是新的学习通道？

传统：

$$
\theta_t
\rightarrow
\theta_{t+1}
$$

知识都写进参数。

Evolving Rollouts 还增加：

$$
C_t
\rightarrow
C_{t+1}
$$

即 context / experience state 也在进化。

---

### 但风险也明显

如果历史 trajectory 错：

```text
错误经验
↓
进入 repository
↓
影响未来 rollout
↓
产生更多类似错误
```

所以 experience verification / forgetting / weighting 会成为下一层问题。

---

# 7C. Environment / Long Horizon

## 7.22 SearchGym 为什么把 Environment Alignment 当成训练问题？ `[P1]`

训练 Search Agent 有一个矛盾。

### Live Web

优点：

```text
真实
```

缺点：

```text
贵
慢
不稳定
难复现
```

---

### Static Snapshot

优点：

```text
便宜
可复现
```

但如果 task、corpus、answer 不一致：

> 会产生错误 reward。

例如：

```text
Question answer = X
```

但 snapshot corpus 中：

```text
根本没有 X 的支持证据
```

Agent reasoning 完全正确也无法完成任务。

SearchGym 将这个问题称为训练环境的数据 alignment 问题，构造 verifiable knowledge graph 和 aligned document corpus，使任务在模拟环境中严格 grounded/solvable，再用 curriculum RL 从简单交互逐渐提升到长程 planning，并验证 sim-to-real transfer。

---

### 为什么 Misalignment 会污染 Reward？

假设：

```text
正确 reasoning
↓
搜索环境缺 evidence
↓
wrong answer
↓
reward 0
```

RL 看到的是：

> 这个 trajectory 很差。

实际错误在环境。

---

### 反向也可能发生

snapshot 恰好包含：

```text
直接暴露答案的异常文档
```

模型 hallucinated reasoning 也可能拿高 reward。

---

### 因此 SearchGym 的重要观点

```text
Environment quality
就是 Reward quality 的一部分。
```

---

## 7.23 Context Interference 到底来自哪里？ `[P1]`

直觉上大家会认为：

> Search 越多，信息越多，应该越好。

但多轮检索会不断累积：

```text
old reasoning
old documents
new reasoning
new documents
```

Context Interference 工作系统研究了不同 context 组成对 Search Agent 的干扰，并报告主要干扰来自**最新检索到的文档**；它进一步使用 distillation-based context refiner，并把 context refinement 接入 RL training。

---

### 为什么“最新文档”可能特别危险？

因为它：

```text
离当前 generation 最近
```

并且往往占据大量 token。

模型可能过度依赖：

```text
recent but irrelevant evidence
```

而忽略之前已经形成的正确 reasoning。

---

### 所以 Context Problem 不只是 Context 太长

两个 trajectory：

```text
A: 20K tokens, relevant
B: 8K tokens, highly distracting
```

B 也可能更差。

问题是：

```text
content relevance
+
position
+
redundancy
+
contradiction
```

而不是单纯：

$$
T
$$

---

### 对 Search Agent 的启示

Observation pipeline 可以从：

```text
retrieve
↓
append
```

变成：

```text
retrieve
↓
refine / filter
↓
append useful evidence
```

---

## 7.24 InfoFlow 的 Reward Density 到底是什么？ `[P1]`

InfoFlow 观察到 RLVR Search Agent 的核心问题之一是：

```text
探索成本很高
但 positive reward 很少
```

它把问题形式化为 Reward Density Optimization：

> 单位探索成本能获得多少有效 reward / learning signal。

概念上可以理解：

$$
\rho_R
=
\frac{
\text{useful reward signal}
}{
\text{exploration cost}
}
$$

这不是一定要求论文使用这个简单比值作为唯一公式，而是帮助理解其 optimization view。

---

### 为什么只看 Success Rate 不够？

算法 A：

```text
success = 50%
每条 trajectory 100 tool calls
```

算法 B：

```text
success = 45%
每条 trajectory 10 tool calls
```

如果训练预算固定：

> B 可能每 GPU-hour 得到更多有效成功 trajectory。

---

### InfoFlow 三条路线

论文提出：

```text
Sub-goal Scaffolding
→ 中间目标 + process reward

Pathfinding Hints
→ stalled trajectory 获得纠正提示

Dual-agent Refinement
→ 把深度探索部分认知负担交给另一个 agent
```

---

### 这改变了一个常见思维

过去问：

> Reward 怎么设计？

InfoFlow 更强调：

> 每花一单位 rollout 成本，究竟得到多少训练信号？

这是 Agent RL 非常实际的问题。

---

## 7.25 Table-as-Search 为什么把搜索改写成 Table Completion？ `[P1]`

普通 long-horizon agent 把所有状态放进 plain text：

```text
plan
search result 1
search result 2
notes
new plan
search result 3
...
```

随着 horizon 增加，很容易失焦。

Table-as-Search 把 InfoSeeking 任务映射为外部结构化 table：row 表示 search candidate，column 表示 constraint / required information；filled cells 记录已有结果，empty cells 同时构成显式 search plan。论文还用这一表示统一 Deep Search、Wide Search 和 DeepWide Search。

---

### 传统状态

```text
"Need A and B.
I found A...
Then searched C...
Maybe B is..."
```

模型自己从文本恢复：

```text
完成了什么？
还缺什么？
```

---

### Table State

例如：

| Candidate | Country | Founder | Year |
| --------- | ------- | ------- | ---- |
| X         | China   | Alice   | ?    |
| Y         | ?       | Bob     | 2012 |

此时：

```text
filled cell
= 已获得 evidence

empty cell
= 下一步搜索目标
```

---

### 为什么这适合 Long Horizon？

它把：

```text
memory
+
planning
+
progress tracking
```

从隐式 natural-language state 变成 explicit structured state。

---

### 代价

你需要：

* schema construction；
* entity alignment；
* table update correctness；
* database state management。

如果 schema 错：

> Agent 可能从一开始就在错误的问题分解上搜索。

---

# P2

## 7.26 怎样做 Benchmark Contamination Audit？ `[P2]`

不能只：

```bash
grep exact_question train.jsonl
```

因为 contamination 可以是 paraphrase。

---

### Level 1：Exact Match

比较：

```text
normalized question
normalized answer
```

hash / string match。

---

### Level 2：Near Duplicate

使用：

```text
MinHash
n-gram overlap
embedding similarity
```

发现改写题。

---

### Level 3：Entity / Fact Overlap

即使问题不同：

```text
Who is X's father?
```

和：

```text
X is the son of whom?
```

事实完全一样。

需要构造：

```text
subject-relation-object
```

层面检查。

---

### Level 4：Retrieved Corpus Audit

查询 benchmark question，检查是否直接出现：

```text
benchmark answer page
solution repository
benchmark-specific explanation
```

---

### Level 5：Synthetic Generator Audit

如果生成训练任务时：

```text
generator prompt
```

包含 benchmark examples，

也可能造成 style/content leakage。

---

### 对 Pretraining 怎么办？

通常无法完全证明没有 contamination。

因此应该：

```text
明确 limitation
+
优先加入更新/私有/新构造 benchmark
+
做 no-search / memorization probe
```

而不是声称绝对无污染。

---

## 7.27 Sim-to-Real Gap 应怎样严格验证？ `[P2]`

训练：

```text
Simulator
```

评估：

```text
Real Web
```

如果结果不错，不能只说：

> Sim-to-real 成功。

---

### 需要明确哪些 Distribution 变了

#### Retrieval Distribution

```text
simulated ranking
vs
real search ranking
```

#### Document Noise

```text
clean corpus
vs
SEO / duplicate / irrelevant pages
```

#### Tool Reliability

```text
100% success
vs
timeout / 403
```

#### Latency

真实 latency 会影响 timeout / async system。

#### Page Structure

```text
plain text
vs
HTML / PDF / dynamic content
```

---

### 最好做阶梯式 Evaluation

```text
Level 1:
training simulator

Level 2:
held-out simulator corpus

Level 3:
different retriever

Level 4:
frozen real-web snapshot

Level 5:
live web
```

看性能逐层下降多少。

---

### Agent Behavior 也要比较

不只：

$$
Accuracy
$$

还要：

```text
search depth
query length
tool-error recovery
source diversity
```

如果真实环境下：

```text
accuracy 只掉 2%
但 search calls ×5
```

仍然说明存在 gap。

---

## 7.28 Search Difficulty 应该用 Success Rate、Hop Count 还是 Search Depth 定义？ `[P2]`

三个都不完全等价。

---

### Success Rate

$$
D_{\text{success}}
=
1-P_{\pi}(\text{success})
$$

优点：

> policy-aware。

缺点：

> 随 policy 变强，difficulty 会变化。

而且 success 低可能是 reasoning 难，不是 search 难。

---

### Hop Count

gold evidence chain：

```text
A → B → C
```

hop=3。

优点：

* task intrinsic；
* 容易解释。

问题：

> Agent 可能找到 shortcut。

实际只需一个 query。

---

### Search Depth

successful rollout 实际需要：

$$
N_{\text{search}}
$$

更直接衡量 agentic search effort。

SearchMaster 就特别强调成功轨迹的 search depth，而不是只用 success rate 表示 task difficulty。

---

### 更合理的 Difficulty Vector

可以写：

$$
D(q,\pi)
=
(
H_{\text{evidence}},
D_{\text{search}},
P_\pi(\text{success}),
C_{\text{tool}},
L_{\text{context}}
)
$$

而不是压成一个 scalar。

---

### Curriculum 更应该 Policy-aware

早期：

```text
2-hop
```

可能很难。

后期：

```text
5-hop
```

也可能很简单。

因此 difficulty 是：

```text
task property
×
current policy capability
```

共同决定。

---

## 7.29 Self-generated Search Data 如何避免 Curriculum Collapse / Distribution Drift？ `[P2]`

Self-play：

```text
current model
↓
generates tasks
↓
solves tasks
↓
trains on them
```

很自然，但存在 feedback loop。

---

### Failure 1：越来越简单

模型更容易生成自己会做的题：

```text
easy task
↓
success
↓
selected
↓
more easy data
```

最终 curriculum collapse。

---

### Failure 2：越来越奇怪

也可能 optimizer 偏爱：

```text
高 reward 但分布狭窄
```

产生不真实任务。

---

### Failure 3：Generator / Solver 共谋

如果同一模型生成 question 和 solution：

> generator 可能无意中埋下 solver 容易识别的 shortcut。

---

### 需要的控制

```text
difficulty floor / ceiling
external verifier
task diversity
evidence grounding
no-search filtering
held-out source documents
human spot-check
distribution monitor
```

---

### 一个重要指标

比较每轮 self-play 数据：

```text
topic distribution
entity distribution
search depth
success rate
query pattern
```

如果 entropy 持续下降：

> 数据分布可能 collapse。

---

## 7.30 Historical Experience Repository 怎样避免把错误经验越积越多？ `[P2]`

HiExp / Evolving Rollouts 这类方法带来：

```text
parameter memory
+
experience memory
```

新的 failure surface。

---

### 问题一：False Experience

失败 trajectory 的错误 causal explanation 被提炼成：

```text
“遇到 X 应该先搜 Y”
```

但其实并不成立。

---

### 问题二：Stale Experience

Policy 已经变强：

```text
旧策略需要的提示
```

可能现在反而多余。

---

### 问题三：Experience Conflict

```text
Experience A:
先 search broad

Experience B:
先 search narrow
```

如何选择？

---

### 问题四：Repository Growth

经验无限增加：

```text
100
1K
100K
```

retrieval / prompt cost 也增加。

---

### 可以做的机制

#### Verification

只有高 confidence / repeated evidence 的经验进入。

#### Reward-weighting

经验带：

$$
w_i
$$

由来源 trajectory reward、复用成功率决定。

#### Decay

长期没帮助的 experience 降权。

#### Contradiction Detection

冲突经验聚类/比较。

#### Policy-conditioned Retrieval

不是“最相似经验”，而是：

> 当前 policy 最需要哪种经验？

#### Deployment Ablation

训练完成后移除 repository：

> 参数模型到底学到了多少？

---

### 最重要的问题

如果训练性能提升只来自：

```text
越来越长的提示词
```

而参数模型并没进步，

这和真正 policy learning 是不同结论。

---

## 7.31 Agent Evaluation 怎样同时处理 Accuracy、Cost、Latency 和 Robustness？ `[P2]`

单一 Accuracy 不够。

定义 metric vector：

$$
M
=
(
A,C,L,R
)
$$

其中：

```text
A = task accuracy
C = search / token cost
L = latency
R = robustness
```

---

### 方案一：Pareto Frontier

算法 A：

```text
accuracy 80
cost 100
```

算法 B：

```text
accuracy 78
cost 20
```

没有统一 scalar 时：

> 二者都可能是 Pareto-optimal。

---

### 方案二：Budget-constrained

固定：

$$
C\le C_{\max}
$$

比较 Accuracy。

例如：

```text
最多 5 次搜索
```

---

### 方案三：Target-quality

固定：

$$
Accuracy\ge 75\%
$$

比较：

```text
最低 cost / latency
```

---

### 方案四：Utility Function

如果业务真的知道代价：

$$
U
=
Accuracy
-
\lambda C
-
\mu L
$$

可以 scalarize。

但：

> \(\lambda,\mu\) 必须有现实解释。

---

### Robustness 怎么放？

可以单独报告：

```text
clean accuracy
fault-injected accuracy
adversarial accuracy
```

和 degradation：

$$
\Delta_{\text{fault}}
=
A_{\text{clean}}
-
A_{\text{fault}}
$$

---

## 7.32 怎样设计一套真正可复现的 Agent RL Experiment Protocol？ `[P2]`

可以按下面完整链执行。

---

### 1. Freeze Task Definition

保存：

```text
dataset version
task IDs
split
dataset hash
```

---

### 2. Freeze Environment

```text
corpus
corpus hash
retriever config
tool implementation
fault schedule
```

如果 real Web：

```text
timestamp
provider
snapshot where possible
```

---

### 3. Freeze Model Inputs

```text
checkpoint
tokenizer
chat template
action protocol
```

---

### 4. Freeze Rollout

```text
temperature
top-p
top-k
max tokens
group size
seed derivation
max steps
```

---

### 5. Freeze Reward

```text
verifier code
judge model
judge prompt
reward weights
normalization
```

---

### 6. Freeze Trainer

```text
algorithm
learning rate
batch size
gradient accumulation
clip
KL
optimizer
```

---

### 7. Record Provenance

```text
git commit
git dirty
dependency versions
hardware
CUDA
framework
```

---

### 8. Run Multiple Seeds

不要：

```text
seed 42
→ result
→ conclusion
```

至少报告：

$$
mean\pm std
$$

---

### 9. Keep Every Failure

```text
success
wrong
timeout
crash
invalid action
```

不要 silent drop。

---

### 10. Save Trajectories

否则无法进行：

```text
failure analysis
credit analysis
paper ablation
```

---

### 11. Separate Development and Final Evaluation

Test benchmark 不用于：

```text
挑 reward weight
改 prompt
选 checkpoint
```

---

### 12. Statistical Report

至少：

```text
sample size
mean
variance
CI
paired comparison
```

---

# 7.33 Search Agent 数据与环境论文纵向关系

这一组工作并不是彼此平行的“八篇论文”。

更有价值的理解是：

```text
问题 1：
Long-horizon 任务不够
        ↓
SearchArt
Synthetic + Verified Tasks

问题 2：
Self-generated tasks 可能是假难题
        ↓
SearchMaster
Evidence Chain + Search Depth Regulation

问题 3：
每轮随机探索重复犯错
        ↓
HiExp
Historical Trajectory → Hierarchical Experience

问题 4：
Zero-variance rollout 白花成本
        ↓
Evolving Rollouts
Experience Repository + Context-space Evolution

问题 5：
真实 Web 贵，静态环境又可能错位
        ↓
SearchGym
Aligned Simulator + Sim-to-Real

问题 6：
长程搜索 observation 越来越干扰
        ↓
Context Interference
Refine Context before Generation

问题 7：
探索成本高，成功 reward 太稀
        ↓
InfoFlow
Reward Density Optimization

问题 8：
纯文本 history 难以管理搜索状态
        ↓
Table-as-Search
Structured External Search State
```

其中 SearchGym、Context Interference、InfoFlow 与 Table-as-Search 已发表在 ACL 2026 / Findings；Evolving Rollouts发表于 ICML 2026；SearchArt 与 SearchMaster 截至 2026 年 9 月仍以公开预印本为主要论文入口。

---

# 7.34 Search Data / Environment 对照表

| 工作                   | 主要问题                                | 主要改动层                |
| -------------------- | ----------------------------------- | -------------------- |
| SearchArt            | 缺可规模化的长程训练任务                        | Data                 |
| SearchMaster         | Self-play 任务伪多跳、浅搜索                 | Data + Reward        |
| HiExp                | 随机探索重复、低效                           | Experience           |
| Evolving Rollouts    | 历史 rollout / zero-variance group 浪费 | Experience + Context |
| SearchGym            | live Web 贵、static data misalignment | Environment          |
| Context Interference | 检索 observation 干扰 reasoning         | Context              |
| InfoFlow             | Reward 太稀、单位探索成本收益低                 | Exploration + Reward |
| Table-as-Search      | Plain-text search state 脆弱          | State Representation |

---

# 7.35 高频连环追问

## 第一组：Experiment Basics

```text
Train / Dev / Test？
↓
为什么 test 不能调参？
↓
Answer leakage？
↓
Evidence leakage？
↓
Benchmark contamination？
↓
Search tool 搜到 benchmark solution 怎么办？
```

---

## 第二组：Statistics

```text
为什么不能只报 mean？
↓
std 和 standard error 区别？
↓
CI 是什么？
↓
bootstrap 怎么做？
↓
paired bootstrap 为什么更合适比较两算法？
```

---

## 第三组：Failure

```text
timeout 算错误吗？
↓
denominator 怎么算？
↓
execution failure 和 semantic failure 区别？
↓
为什么不能 drop failed run？
↓
fault injection 有什么价值？
```

---

## 第四组：Synthetic Search Data

```text
为什么需要 synthetic data？
↓
有什么 shortcut？
↓
怎么验证任务真的需要 search？
↓
怎么确保 multi-hop 不是假的？
↓
SearchArt / SearchMaster 分别在解决什么？
```

---

## 第五组：Exploration

```text
为什么 stochastic rollout 浪费？
↓
HiExp 做什么？
↓
zero-variance group 为什么浪费？
↓
Evolving Rollouts 怎么回收经验？
↓
experience repository 会不会污染？
```

---

## 第六组：Environment

```text
为什么不用 live Web 直接训练？
↓
为什么 static corpus 也可能有问题？
↓
SearchGym 怎么解决 alignment？
↓
sim-to-real 怎么测？
↓
context interference 为什么出现？
```

---

# 7.36 Self-test

## Self-test 1：Denominator

100 个任务：

```text
70 correct
10 wrong
15 timeout
5 crash
```

Conditional Accuracy：

$$
\frac{70}{80}
=
87.5\%
$$

Execution Success：

$$
\frac{80}{100}
=
80\%
$$

End-to-End Accuracy：

$$
\frac{70}{100}
=
70\%
$$

三个数字都应该有明确语义。

---

## Self-test 2：Variance

三 seeds：

$$
[70,70,70]
$$

和：

$$
[60,70,80]
$$

mean 都是：

$$
70
$$

但第二个系统训练稳定性明显更差。

---

## Self-test 3：Search Necessity

如果：

```text
No-search accuracy = 88%
Search-agent accuracy = 90%
```

这不一定是一个好的 Search RL dataset。

可能大量任务依赖 parametric memory 就能回答。

---

## Self-test 4：Sim-to-Real

Simulator：

```text
90% accuracy
```

Real Web：

```text
60%
```

不能只调模型。

应该拆：

```text
retrieval mismatch
page parsing
tool failure
ranking
content noise
```

---

## Self-test 5：Context Interference

Agent：

```text
Search 1 → 正确 evidence
Search 2 → 大量 irrelevant docs
Answer → wrong
```

不能只认为：

> Search 1 没有用。

可能是后续 observation 把已有正确 context 干扰掉。

---

# 7.37 Debug 题

## Debug 1：新方法 Accuracy +4，但只有一个 Seed

不能直接宣称稳定提升。

下一步：

```text
multi-seed
CI
paired task analysis
```

---

## Debug 2：Synthetic Training 后 Benchmark 暴涨 20%

优先检查：

```text
train/test overlap
benchmark-derived documents
generator saw benchmark
answer leakage
near duplicates
```

再谈算法突破。

---

## Debug 3：Search Agent Offline Evaluation 很强，Live Web 很差

检查：

```text
environment alignment
ranking distribution
page parser
timeout
dynamic content
source quality
```

---

## Debug 4：训练成功率长期接近 0

检查：

```text
tasks truly solvable?
gold evidence in corpus?
retriever recall?
reward verifier?
policy exploration?
```

不要直接加更大的模型。

---

## Debug 5：Historical Experience 加入后训练指标提升，但裸模型 Evaluation 没变

说明 improvement 可能主要来自：

```text
in-context scaffolding
```

而不是：

```text
parameter learning
```

必须分别测：

```text
with experience
without experience
```

---

## Debug 6：LLM Judge 分数上涨，人评不涨

检查：

```text
verbosity bias
judge prompt
position bias
reward hacking
self-preference
```

---

# 7.38 系统设计题

## 系统设计题 1：怎样构造一个可信的 Synthetic Search Dataset？

可以按：

```text
Source Documents
      ↓
Evidence Graph
      ↓
Question Generation
      ↓
Reference Answer
      ↓
Search-required Verification
      ↓
Trajectory Generation
      ↓
Evidence / Answer Verification
      ↓
Deduplication
      ↓
Difficulty Filtering
      ↓
Train Split
```

并且每一步都保存 provenance。

---

## 系统设计题 2：Live Web 太贵，怎样做 Search Simulator？

需要保证：

```text
task
answer
corpus
retriever
```

彼此 aligned。

同时加入：

```text
noise
irrelevant docs
faults
variable ranking
```

否则 simulator 太干净，会产生巨大的 sim-to-real gap。

---

## 系统设计题 3：怎样评估 Context Management 方法？

至少比较：

```text
Raw Concatenation
Truncation
Summarization
Context Refiner
Structured State
Memory
```

控制：

```text
same search results
same policy
same token budget
```

报告：

```text
accuracy
context tokens
latency
search calls
```

---

# 7.39 Macro 7 最小知识图

最终应形成：

```text
                    Agent Experiment
                          │
         ┌────────────────┼────────────────┐
         │                │                │
       Data           Environment       Evaluation
         │                │                │
      Split             Corpus           Metric
      Leakage           Retriever        Variance
      Synthetic         Tool             CI
      Version           Failure          Judge
         │                │                │
         └────────────────┼────────────────┘
                          ↓
                    Reproducibility
                          │
                          ↓
                     Artifact Registry
```

Search Agent 专项再覆盖：

```text
                  Search Training
                        │
        ┌───────────────┼────────────────┐
        │               │                │
       Data         Exploration       Environment
        │               │                │
   SearchArt           HiExp          SearchGym
   SearchMaster        Evolving       Context
                       Rollouts       Interference
        │               │                │
        └───────────────┼────────────────┘
                        │
                 Long-horizon State
                        │
                 ┌──────┴──────┐
                 │             │
              InfoFlow   Table-as-Search
            reward density structured state
```

本章真正需要记住的不是八个新论文名字，而是四个实验原则：

```text
1. 数据质量决定你到底在训练什么。
2. 环境正确性决定 reward 是否可信。
3. 只报平均准确率不足以证明算法有效。
4. 长程 Agent 的 rollout 本身是一种昂贵训练资源，
   所以任务、探索、经验和 context 都必须提高 information density。
```

Macro 8 接下来就可以把本章出现但还没有深入的：

```text
Outcome Reward
Process Reward
Verifier
Judge
Credit
Fatal Mask
Historical Contribution
```

全部收束到整个项目算法含量最高的一章：

```text
Reward / Verification / Credit Assignment / Search Policy
```

并正式进入：

```text
CW-GRPO
CriticSearch
KbPO
AutoSearch
Agentic-R
MemSearcher
MemSearch-o1
Multimodal Search
```

其中通用 Reward / Verification 会先完整讲一遍，再进入 Search 专项，不会为了论文线再次把通用方法论压掉。

## 8. Reward / Verification / Credit / Search Policy

前面的 Search Agent 已经建立了：

```text id="l2cc0r"
Task
 ↓
Reason
 ↓
Search
 ↓
Observation
 ↓
Reason
 ↓
Search
 ↓
...
 ↓
Answer
 ↓
Outcome
```

现在真正困难的问题是：

> 最后的 Outcome 到底应该怎样变成每一个 Search Turn、Reasoning Turn，最终每一个 Policy Token 的训练信号？

这就是 Credit Assignment。

如果只使用：

$$
R(\tau)
$$

作为整条 trajectory 的 reward，那么最简单，但会遇到：

```text id="a5nkmt"
哪一轮 search 真正有用？
哪一步已经造成不可恢复失败？
最终答案错了，前面的正确 search 是否也该受罚？
搜索到了正确 evidence，但最后抄错答案怎么办？
某个 process judge 判断错了怎么办？
```

如果反过来给每一步都设计 process reward，又会遇到：

```text id="4o172w"
judge bias
reward hacking
calibration
annotation cost
process proxy 与最终任务目标不一致
```

所以这一章真正的主线不是：

```text id="ji6xqo"
Outcome Reward
vs
Process Reward
谁更高级？
```

而是：

```text id="zux1bz"
Outcome
Process Signal
Verifier
Critic
Contribution
Mask
Weight
Counterfactual
```

分别应该作用在：

```text id="5kl8by"
Reward
Advantage
Loss Weight
Token Mask
```

的哪一层。

这四层绝对不能混。

---

## 8.0 问题矩阵

| 编号   | 问题                                                          | 等级 |
| ---- | ----------------------------------------------------------- | -- |
| 8.1  | Outcome Reward 与 Process Reward 有什么区别？                      | P0 |
| 8.2  | Sparse Reward 与 Dense Reward 有什么区别？                         | P0 |
| 8.3  | Rule-based Verifier、Reward Model、LLM Judge 怎么选？             | P0 |
| 8.4  | Reward Hacking、Verifier Gaming、Reward Model Hacking 有什么区别？  | P0 |
| 8.5  | Trajectory / Turn / Step / Token Credit Assignment 有什么区别？   | P0 |
| 8.6  | Process Reward 与 Credit Weighting 为什么不是一回事？                 | P0 |
| 8.7  | Hard Mask 与 Soft Weight 有什么区别？                              | P0 |
| 8.8  | Fatal-aware Masking 在解决什么问题？                                | P0 |
| 8.9  | One-sided Advantage Clamping 是什么直觉？                         | P0 |
| 8.10 | Search Agent 中“Should I Search?”为什么本身就是 Policy Learning 问题？ | P0 |
| 8.11 | Over-search 与 Under-search 分别是什么？                           | P0 |
| 8.12 | 为什么普通 Retriever 不一定适合 Agentic Search？                       | P0 |
| 8.13 | Process Judge 应怎样校准？                                        | P1 |
| 8.14 | Learned Critic 判断错了怎么办？                                     | P1 |
| 8.15 | 多 Verifier / Judge 应怎样组合？                                   | P1 |
| 8.16 | Reward Scale / Reward Composition 为什么会改变训练行为？               | P1 |
| 8.17 | Fatal Step 之后的 Token 是否应该全部 Mask？                           | P1 |
| 8.18 | Hard Mask 和 Soft Weight 的 Bias–Variance Trade-off 是什么？      | P1 |
| 8.19 | CW-GRPO 到底修改了 GRPO 的哪一层？                                    | P1 |
| 8.20 | 为什么 CW-GRPO 不直接把 Process Judge 分数当 Reward？                  | P1 |
| 8.21 | CriticSearch 的 Retrospective Critic 在做什么？                   | P1 |
| 8.22 | Privileged Information 为什么只能训练时用？                           | P1 |
| 8.23 | KbPO 的 Knowledge Boundary 到底是什么？                            | P1 |
| 8.24 | AutoSearch 的 Minimal Sufficient Search Depth 是什么？           | P1 |
| 8.25 | Agentic-R 为什么认为 Passage Similarity 不等于 Agent Utility？       | P1 |
| 8.26 | MemSearcher 的 Multi-context GRPO 为什么需要单独设计？                 | P1 |
| 8.27 | MemSearch-o1 与普通 Summarization Memory 有什么区别？                | P1 |
| 8.28 | Counterfactual Credit Assignment 应怎样定义？                     | P2 |
| 8.29 | Shapley-value 思想怎样用于 Agent Credit？                          | P2 |
| 8.30 | Counterfactual Credit 为什么非常昂贵？                              | P2 |
| 8.31 | Search Depth 为什么是 Policy-dependent Quantity？                | P2 |
| 8.32 | Joint Retriever–Policy Training 为什么会产生 Non-stationarity？    | P2 |
| 8.33 | Memory 本身怎样做 Credit Assignment？                             | P2 |
| 8.34 | Query / Retrieval / Stopping 能不能 Jointly Optimize？          | P2 |
| 8.35 | MMSearch-R1 为什么需要 Search-required + Search-free Data？       | P2 |
| 8.36 | OpenSearch-VL 的 Fatal-aware GRPO 为什么值得单独理解？                 | P2 |
| 8.37 | ProMMSearchAgent 为什么把 Process Reward 与 Sim-to-Real 结合？      | P2 |
| 8.38 | LMM-Searcher 为什么把视觉信息移到 File-based External State？          | P2 |

---

# 8A. Reward Fundamentals

## 8.1 Outcome Reward 与 Process Reward 有什么区别？ `[P0]`

### Outcome Reward

只评价最终结果：

$$
R_{\text{outcome}}
=
f(
\text{final answer}
)
$$

例如：

```text id="5sb2ld"
exact answer correct → 1
wrong → 0
```

中间 trajectory：

```text id="bpzcws"
Search A
Search B
Search C
```

没有独立 reward。

---

### Process Reward

对中间行为也打分：

$$
r_t
=
f(
s_t,a_t
)
$$

例如：

```text id="ms40bp"
query useful          +0.3
evidence relevant     +0.2
invalid tool call     -0.5
reasoning incorrect   -0.3
```

---

### Outcome Reward 的优势

* task-aligned；
* 通常容易验证；
* process assumption 少；
* judge bias 少。

---

### 问题

Credit 非常稀疏。

成功 trajectory：

```text id="uqdc5l"
good
good
bad
good
correct answer
```

所有前面行为都吃到：

```text id="cuu1bn"
positive trajectory advantage
```

---

### Process Reward 优势

能区分：

```text id="wr7kb2"
good turn
bad turn
```

产生 dense signal。

---

### 风险

Process Judge 可能：

> 判断某一步“看起来合理”，但其实对最终结果没贡献。

因此：

```text id="jaooek"
process correctness
≠
causal contribution
```

---

## 8.2 Sparse Reward 与 Dense Reward 有什么区别？ `[P0]`

### Sparse

长 trajectory 中只有少数位置得到 reward。

例如：

```text id="18icsf"
r0 = 0
r1 = 0
r2 = 0
...
rT = 1
```

---

### Dense

许多 step 都有：

$$
r_t\neq0
$$

例如：

```text id="fq2r4d"
good search       +0.1
good evidence     +0.2
good synthesis    +0.1
correct answer    +1.0
```

---

### Sparse 的优点

通常更接近真实 objective。

例如：

```text id="oc28e7"
unit test pass
final answer correct
```

不需要人为猜：

> 哪一步该奖励多少。

---

### Sparse 的缺点

* credit assignment 难；
* exploration 难；
* reward variance 高。

---

### Dense 的优点

* 更快 learning；
* 更容易发现 useful behavior。

---

### Dense 的缺点

你实际优化的是：

$$
\sum_t r_t
$$

如果设计错了，Agent 会 exploit intermediate reward。

例如：

```text id="j9vcvj"
每次“找到相关文档” +0.1
```

可能学成：

> 无限找“看起来相关”的文档，不回答。

---

## 8.3 Rule-based Verifier、Reward Model、LLM Judge 怎么选？ `[P0]`

### Rule-based Verifier

例如：

```text id="qyl94t"
Exact Match
unit test
compiler
symbolic checker
citation URL exists
```

优点：

```text id="t4enwv"
cheap
deterministic
high reproducibility
```

问题：

> Coverage 有限。

---

### Reward Model

训练：

$$
r_\phi(x,y)
$$

优势：

* 快；
* 可批量；
* 能学习复杂 preference。

风险：

* distribution shift；
* hacking；
* calibration。

---

### LLM Judge

```text id="fe9cbn"
trajectory
+
rubric
↓
LLM
↓
score / critique
```

优势：

* 灵活；
* 能评 reasoning/process；
* 不必专门训练 scorer。

风险：

```text id="czzmsa"
cost
latency
stochasticity
prompt sensitivity
bias
```

---

### 一个非常实用的优先级

如果可靠 deterministic verifier 能覆盖任务：

```text id="1dcq5v"
优先 verifier
```

只有无法程序验证的东西再考虑：

```text id="dx9zll"
RM / Judge
```

不要因为 LLM Judge“更聪明”就主动替换更可靠的 task signal。

---

## 8.4 Reward Hacking、Verifier Gaming、Reward Model Hacking 有什么区别？ `[P0]`

三者有重叠，但可以分层理解。

---

### Reward Hacking

最广义：

> Agent 找到提高定义 reward 的方式，但没有真正提高我们想要的任务质量。

---

### Verifier Gaming

针对 rule/verifier。

例如 verifier：

```python id="7koey0"
if "42" in answer:
    reward = 1
```

模型学会：

```text id="bxiq7o"
答案里永远塞 42
```

而不真正解决题目。

---

### Reward Model Hacking

针对 learned RM。

例如 RM 偏好：

```text id="yg5p1h"
长
有标题
语气确定
```

policy 学会：

```text id="y727lg"
极长、自信、格式漂亮
```

即使内容没改善。

---

### LLM Judge Gaming

比如 Judge rubric 喜欢：

```text id="gj8tpi"
“根据多方来源”
```

模型可能开始反复使用这种表述。

---

### 核心问题

```text id="4ivzlq"
Proxy Reward
≠
True Utility
```

Policy optimizer 会主动寻找 proxy 中最容易 exploitation 的方向。

---

## 8.5 Trajectory / Turn / Step / Token Credit Assignment 有什么区别？ `[P0]`

假设：

```text id="qz0u90"
Turn 0:
reason + search

Turn 1:
reason + search

Turn 2:
reason + answer
```

---

### Trajectory-level

整个：

$$
\tau
$$

一个：

$$
A(\tau)
$$

所有 policy token 共享。

---

### Turn-level

$$
A_0,A_1,A_2
$$

每个 turn 不同。

---

### Step-level

如果 turn 内还有：

```text id="73wpgb"
Reason
Action
Observation
```

可以进一步给 Action 单独 credit。

---

### Token-level

每个 generated token：

$$
A_t
$$

甚至不同。

---

### Granularity 越细

优点：

> Credit 更准确。

代价：

* evaluator 成本；
* noise；
* calibration；
* implementation complexity。

---

## 8.6 Process Reward 与 Credit Weighting 为什么不是一回事？ `[P0]`

这是 Macro 8 必须掌握的一题。

---

### Process Reward

直接修改 reward：

$$
R'
=
R_{\text{outcome}}
+
\sum_t r_t^{process}
$$

那么 process judge 本身成为 optimization target。

---

### Credit Weight

不改变最终 reward本身。

先有：

$$
A_{\text{outcome}}
$$

然后根据 contribution：

$$
w_t
$$

构造：

$$
A_t
=
w_t
A_{\text{outcome}}
$$

也就是：

> Process signal 只决定 outcome credit 如何分配。

---

### 为什么区别很大？

Process Judge 错误时：

#### Process Reward

可能直接创造：

```text id="d31gaq"
假的正 reward
```

#### Contribution Weight

至少仍受：

```text id="hrxqal"
最终 outcome sign
```

约束。

---

### 可以记：

```text id="uqtnme"
Process Reward
改变“任务值多少钱”

Credit Weight
改变“这份结果该归功于谁”
```

---

## 8.7 Hard Mask 与 Soft Weight 有什么区别？ `[P0]`

### Hard Mask

$$
w_t\in\{0,1\}
$$

例如：

```text id="g15gt0"
before fatal failure: 1
after fatal failure:  0
```

loss：

$$
L
=
\sum_t
w_tL_t
$$

---

### Soft Weight

$$
w_t\in[0,1]
$$

例如：

```text id="4wuut0"
turn 0  0.9
turn 1  0.7
turn 2  0.2
turn 3  0.0
```

---

### Hard Mask

优点：

* 简单；
* robust；
* 不依赖精确 calibration。

缺点：

> 信息被彻底丢掉。

---

### Soft Weight

优点：

> 能表达程度。

缺点：

> 非常依赖 evaluator calibration。

---

## 8.8 Fatal-aware Masking 在解决什么问题？ `[P0]`

假设 trajectory：

```text id="1wahge"
Turn 0:
correct search

Turn 1:
wrong entity selected

Turn 2:
reasoning based on wrong entity

Turn 3:
wrong answer
```

Turn 1 后任务已经不可恢复。

---

### Vanilla Outcome RL

最终：

$$
R=0
$$

所有 token 都受 negative signal。

---

### 问题

Turn 0：

```text id="o7hjj0"
本来是对的
```

后面的 Turn 2/3：

> 很大程度上只是 fatal error 之后的 downstream consequence。

---

### Fatal-aware Idea

识别：

$$
t_f
$$

fatal failure。

然后重新定义哪些 token 应：

```text id="ztnq5g"
保留
削弱
mask
```

避免把 cascading failure 后的大量 token 当成独立错误学习。

---

## 8.9 One-sided Advantage Clamping 是什么直觉？ `[P0]`

假设 evaluator 对某个 turn 的判断：

> “这是 fatal mistake。”

我们可能比较相信：

```text id="07k8va"
不要强化它
```

但未必敢相信：

```text id="akv5zg"
应该以很大负梯度强烈 suppress 它
```

因为 judge 自身可能错。

---

### One-sided 思想

对某一方向上的 advantage 更保守。

例如概念上：

```text id="nx9yfp"
uncertain negative credit
不要无限放大

或

fatal 后 downstream token
不要继续获得错误方向的更新
```

---

### 为什么叫 One-sided？

不是对：

$$
A>0
$$

和：

$$
A<0
$$

完全对称处理。

它体现：

> 我们对某一方向的 credit inference 更不信任。

具体算法形式要看论文；后面 OpenSearch-VL 会出现一个明确例子。

---

## 8.10 Search Agent 中“Should I Search?”为什么本身就是 Policy Learning 问题？ `[P0]`

模型面对问题时有两类知识源：

```text id="q2wp7e"
Parametric Knowledge
External Retrieval
```

Search 有成本：

```text id="vi0dcb"
latency
tokens
tool cost
context noise
```

所以不是所有问题都应该搜索。

---

### 决策

$$
a
\in
\{
\text{AnswerDirectly},
\text{Search}
\}
$$

本身就是 action。

---

### 如果总搜索

会：

```text id="rpl36i"
over-search
```

---

### 如果从不搜

在知识不足时：

```text id="a2dz9v"
hallucination
```

所以理想 policy 应学：

> 当前 parametric knowledge 是否足以回答。

这就是 KbPO 和后来的多模态 on-demand search 很关注的问题。

---

## 8.11 Over-search 与 Under-search 分别是什么？ `[P0]`

### Under-search

证据不足时过早 Answer。

结果：

```text id="sdtot6"
low cost
high hallucination
```

---

### Over-search

已有足够证据后仍继续：

```text id="j4o5uh"
search
search
search
```

结果：

* 成本上升；
* context 更长；
* interference；
* latency。

---

### 理想目标

不是：

$$
\max \text{Search Count}
$$

也不是：

$$
\min \text{Search Count}
$$

而是：

> Minimal sufficient search。

这会直接连接 AutoSearch。

---

## 8.12 为什么普通 Retriever 不一定适合 Agentic Search？ `[P0]`

传统 Retriever 常优化：

$$
Rel(q,d)
$$

即：

> Passage 和 Query 看起来多相关？

但 Agentic Search 更关心：

$$
Utility(d|\tau)
$$

即：

> 这篇 passage 是否真的推进最终任务？

---

### 一个例子

Query：

```text id="fhvk2b"
Alice Smith education
```

Passage A：

```text id="nb2g0g"
大量重复 Alice 的简介
```

语义非常相似。

Passage B：

```text id="2o9sio"
提到她大学学位，但 lexical overlap 少
```

对最终 answer：

```text id="9249bb"
B utility > A
```

但 similarity retriever 可能相反。

Agentic-R 正是在这一点上强调局部 query-passage relevance 与全局 final-answer utility 都应该进入 retriever learning。

---

# 8B. Verification / Judge / Reward Engineering

## 8.13 Process Judge 应怎样校准？ `[P1]`

假设 Judge 输出：

```text id="1r3lyp"
0.9
```

不能自动理解为：

> 90% 概率这个 step 是好步骤。

---

### Calibration

如果所有 Judge confidence≈0.9 的样本中：

$$
90\%
$$

真的正确，才接近 calibrated。

---

### 可以测

#### Reliability Diagram

把分数分 bins：

```text id="7zcb0p"
0.0–0.1
0.1–0.2
...
0.9–1.0
```

比较：

```text id="8awruq"
predicted confidence
vs
empirical correctness
```

---

### Ranking Calibration

如果主要用 Judge 做：

```text id="r27e2h"
Turn A > Turn B
```

则更应测试 pairwise ranking accuracy。

---

### Human Agreement

抽样让人标：

```text id="zi0q0x"
query useful?
reasoning correct?
```

比较 Judge。

---

### Counterfactual Validation

Judge 认为某 turn：

```text id="hk4i1k"
contribution = high
```

可以删除/替换该 turn，看最终 success 是否真的大幅下降。

这是更强的 causal sanity check。

---

### Judge 不校准的后果

如果 score：

```text id="wmvazd"
0.2 vs 0.8
```

并不对应真实贡献差异，却直接作为 soft weights：

> gradient scale 会被错误放大。

---

## 8.14 Learned Critic 判断错了怎么办？ `[P1]`

任何 learned critic：

$$
c_\phi(\tau,t)
$$

都可能错。

所以不能把 Critic 当 oracle。

---

### 方法一：Outcome Anchor

仍保留：

$$
R_{\text{outcome}}
$$

作为最终方向。

Critic 只：

```text id="sk8bha"
redistribute
```

而不是完全覆盖。

---

### 方法二：Ensemble

多个 critics：

$$
c_1,c_2,\ldots,c_K
$$

看 disagreement。

若：

$$
Var(c_k)
$$

高，降低 confidence。

---

### 方法三：Uncertainty-aware Weight

$$
w_t
=
f(
\mu_t,
\sigma_t
)
$$

uncertainty 高：

```text id="mml2yb"
weight → conservative
```

---

### 方法四：Fallback

如果 critic 无法可靠判断：

```text id="ojlu67"
fallback to trajectory outcome
```

---

### 方法五：Ablation

必须比较：

```text id="hhfr8x"
Outcome only
+
Critic
+
Random critic weights
```

避免发现：

> 其实任何 random reweight 都有效。

---

## 8.15 多 Verifier / Judge 应怎样组合？ `[P1]`

假设有：

```text id="nrz1xe"
Rule Verifier
Citation Checker
LLM Factual Judge
Process Critic
```

不一定简单：

$$
R=\sum_iR_i
$$

---

### Weighted Sum

$$
R
=
\sum_i\lambda_iR_i
$$

简单，但 scale 敏感。

---

### Hard Gate

例如：

```text id="ddfnmy"
format invalid
→ reward = 0
```

再评 correctness。

适合：

> 某条件必须满足。

---

### Cascade

```text id="78p4hr"
cheap verifier
↓ pass
expensive judge
```

减少成本。

---

### Majority / Ensemble

适合 noisy Judges。

---

### Lexicographic

例如：

```text id="nx4acf"
先保证 safety
再优化 usefulness
```

不是简单线性 trade-off。

---

### 最重要

必须保存：

```text id="ij9ezq"
component rewards
```

而不是只保存：

```text id="48drlq"
final_reward = 0.64
```

否则后面无法知道：

> 到底哪个 verifier 在驱动 policy。

---

## 8.16 Reward Scale / Reward Composition 为什么会改变训练行为？ `[P1]`

Policy gradient：

$$
\nabla J
\propto
A
\nabla\log\pi
$$

如果某 reward component 放大 100 倍：

> 它几乎主导 gradient。

---

### 例如

$$
R
=
R_{\text{answer}}
+
0.1R_{\text{citation}}
-
0.01N_{\text{search}}
$$

如果 citation score 本身范围：

$$
[0,100]
$$

实际上：

$$
0.1R_{\text{citation}}
\in[0,10]
$$

而 answer：

$$
R_{\text{answer}}\in\{0,1\}
$$

结果 citation 远比 correctness 重要。

---

### 所以必须看

```text id="acpzdx"
range
variance
sparsity
frequency
```

而不是只看 \(\lambda\)。

---

## 8.17 Fatal Step 之后的 Token 是否应该全部 Mask？ `[P1]`

不一定。

---

### 如果 Failure 真正不可恢复

例如：

```text id="b16s5u"
选择了错误文件
之后所有 reasoning 都建立在错误对象上
```

后续 token 的 credit 很不可靠。

Mask 有道理。

---

### 但有些“Fatal”定义并不真 Fatal

例如：

```text id="oqx1l2"
一次错误 search
↓
下一轮重新 search
↓
成功恢复
```

如果过早 mask：

> 会丢掉 recovery behavior 的训练价值。

---

### 所以需要区分

```text id="8wc9d1"
error
recoverable error
fatal error
```

---

### 还可以只 Mask 某类 Loss

例如：

```text id="xxw5xo"
policy gradient mask
```

但仍保留：

```text id="3r2ffq"
behavior analysis
auxiliary loss
```

---

## 8.18 Hard Mask 和 Soft Weight 的 Bias–Variance Trade-off 是什么？ `[P1]`

### Hard Mask

如果判断正确：

> 很干净地去掉污染 credit。

但判断错：

> 直接丢失全部真实 training signal。

因此 estimator bias 可能很大。

---

### Soft Weight

例如：

$$
w_t=0.3
$$

即使 evaluator 有误：

> 仍保留一部分 signal。

更鲁棒。

但：

```text id="olax65"
noisy tokens
```

仍然进入 gradient，提高 variance。

---

### 可以粗略理解

```text id="llbmfo"
Hard
low residual noise
high decision sensitivity

Soft
higher residual noise
lower catastrophic deletion risk
```

选择取决于：

> evaluator 是否真的能可靠检测 fatal / contribution。

---

# 8C. Search Credit

## 8.19 CW-GRPO 到底修改了 GRPO 的哪一层？ `[P1]`

Vanilla GRPO：

同一个 prompt 采样：

$$
G
$$

条 trajectory。

得到 group-relative：

$$
A_i^{outcome}
$$

通常一条 trajectory 内大量 policy tokens 共用这个 outcome-derived signal。

---

### CW-GRPO

它不直接把每轮 process score 变成新的 reward。

而是用 LLM Judge 评估每轮：

```text id="g23mez"
retrieval utility
reasoning correctness
```

得到 contribution weight：

$$
w_{i,t}
$$

然后重新缩放 outcome advantage：

$$
A_{i,t}
=
w_{i,t}
A_i^{outcome}
$$

论文明确把 per-round process judgement 作为 contribution weights，用来重新分配 outcome-based advantage，而不是直接优化 process reward。

---

### 所以修改的是

```text id="pzt0in"
Reward?
No

Group normalization?
Not primarily

Advantage allocation?
Yes
```

---

### 最核心的一句话

> **CW-GRPO 是 process-informed credit assignment，不是简单的 process-reward GRPO。**

---

## 8.20 为什么 CW-GRPO 不直接把 Process Judge 分数当 Reward？ `[P1]`

因为：

$$
Judge_t
$$

是 learned proxy。

如果直接：

$$
R'
=
R_{\text{outcome}}
+
\sum_tJudge_t
$$

Agent 会开始优化：

> 如何让 Judge 觉得过程漂亮。

不一定最终 answer 更好。

---

### CW-GRPO 的保守策略

Outcome：

```text id="lh5stl"
决定最终方向
```

Process judge：

```text id="q06gyo"
决定方向如何在 trajectory 中分配
```

---

### 例如失败 trajectory

$$
A^{outcome}<0
$$

但某个前期 turn：

```text id="u6gwo4"
其实很好
```

Contribution 很低/特殊处理后，可以减少它承受的负更新。

---

### 为什么更稳定？

它试图保留：

```text id="sl69kg"
outcome supervision 的稳定性
```

同时获得：

```text id="fl8vjf"
process-level granularity
```

这正是论文针对 outcome supervision credit sparse 与 process supervision value estimation不稳之间折中的出发点。

---

## 8.21 CriticSearch 的 Retrospective Critic 在做什么？ `[P1]`

普通 online critic 在 turn \(t\) 时看到：

$$
history_{\le t}
$$

然后判断当前 action。

但有些步骤只有看到未来才知道其价值。

---

### Retrospective Critic

训练时看：

```text id="2sx4ss"
full trajectory
+
gold answer
```

再回头评估：

```text id="ylpqzw"
Turn 0
Turn 1
Turn 2
...
```

CriticSearch 使用冻结的 asymmetric critique LLM，借助完整 trajectory 和 gold answer 等 privileged information，对各 turn 做 retrospective evaluation，产生 dense turn-level feedback。

---

### 为什么“回头看”更容易？

Turn 1 搜：

```text id="7xryxh"
Alice education
```

当时不知道有没有用。

但看到最终 trajectory 后：

```text id="0cakla"
这条 evidence 最终确实用于 answer
```

就更容易判断贡献。

---

### 它在解决

```text id="1r55af"
Sparse Outcome
↓
Turn-level Dense Feedback
```

---

## 8.22 Privileged Information 为什么只能训练时用？ `[P1]`

Critic 训练时可能看到：

```text id="upj8o6"
gold answer
future turns
full successful/failed trajectory
```

但 inference policy 在 turn \(t\) 不可能看到未来。

---

### 如果 Policy 直接使用这些信息

会出现：

```text id="8pp0bm"
train-time information leakage
```

部署时不可用。

---

### 正确角色

Privileged info 应用于：

```text id="bsdl4y"
teacher
critic
label generator
```

产生训练 signal。

Policy 本身仍只条件于：

$$
s_t
$$

---

### 类似思想

```text id="tc6g29"
Learning using privileged information
Teacher–Student
Retrospective supervision
```

都要求：

> 部署模型不能依赖训练时 oracle 信息。

---

# 8D. Search Policy

## 8.23 KbPO 的 Knowledge Boundary 到底是什么？ `[P1]`

Search Agent 面临两个极端：

```text id="dc5jhk"
明明知道
却乱搜 noisy Web

不知道
却自信直接答
```

KbPO 试图显式建模：

> Parametric knowledge 什么时候值得信？

论文使用 semantic stability 来刻画可靠的内部知识，并将内部 certainty 与 retrieval quality 组合为四象限 taxonomy，再通过 quadrant-based reward 训练 calibrated search behavior。

---

### 可以抽象成两个变量

$$
K_{internal}
$$

模型内部知识可靠度。

$$
Q_{retrieval}
$$

外部 evidence 质量。

形成：

```text id="bto4z8"
Internal High / Retrieval High
Internal High / Retrieval Low
Internal Low  / Retrieval High
Internal Low  / Retrieval Low
```

---

### 四种状态含义

#### Internal High + Retrieval Low

更应该：

> Trust Within。

不要被 bad retrieval 带偏。

---

#### Internal Low + Retrieval High

更应该：

> Seek / trust external evidence。

---

#### 两者都高

需要融合 / cross-check。

---

#### 两者都低

最危险：

> 应降低 confidence，而不是 hallucinate。

---

### KbPO 的贡献

不是单纯：

```text id="bx546b"
鼓励 search
```

而是：

> 让 search behavior 与知识状态匹配。

---

## 8.24 AutoSearch 的 Minimal Sufficient Search Depth 是什么？ `[P1]`

固定：

```text id="0jnh33"
max search = 5
```

不能解决一个问题：

> 到底实际应该搜几次？

AutoSearch研究 accuracy 随 search depth 的变化，并提出 minimal sufficient search depth，它由 question complexity 与 agent capability 共同决定；框架通过 self-generated intermediate answers 评估当前深度是否已经足够，同时惩罚 over-search。

---

### 假设

搜索深度：

$$
d
$$

准确率：

$$
Acc(d)
$$

如果：

```text id="mvsjtp"
d=1  wrong
d=2  wrong
d=3  correct
d=4  correct
d=5  correct
```

那么最小充分深度：

$$
d^*=3
$$

---

### 为什么是 Policy-dependent？

强模型：

```text id="jhvx2q"
2 searches
```

可能够。

弱模型：

```text id="p2dl6x"
4 searches
```

才够。

所以：

$$
d^*
=
f(
question,
policy
)
$$

不是 task 固有常数。

---

## 8.25 Agentic-R 为什么认为 Passage Similarity 不等于 Agent Utility？ `[P1]`

传统 Retriever：

$$
score(q,d)
$$

通常只优化：

```text id="u4cdry"
local query-document relevance
```

但 Agent trajectory 有全局目标：

$$
AnswerCorrect
$$

---

### Agentic Utility

某 document 的价值还应考虑：

> 它最终是否提高 answer correctness。

Agentic-R 因此同时使用：

```text id="p3r0bp"
local query-passage utility
+
global answer correctness
```

评价 passage，并迭代地让 Search Agent 与 Retriever 双向改进；Agent 产生越来越好的 query，Retriever 又反过来提供更适合 Agent 的结果。

---

### 一个 Passage 可以：

```text id="f80h5q"
query similarity 高
但 answer utility 低
```

也可以：

```text id="bfhp5j"
surface similarity 一般
但包含关键 bridge evidence
```

所以 retriever objective 需要从：

```text id="lg7u2d"
retrieval relevance
```

扩展到：

```text id="umq1ou"
downstream agent utility
```

---

# 8E. Memory

## 8.26 MemSearcher 的 Multi-context GRPO 为什么需要单独设计？ `[P1]`

普通 ReAct-style Agent：

```text id="zoj1pk"
history 全 concat
```

同一 trajectory 可以比较自然 flatten。

MemSearcher 则每轮维护一个：

```text id="8lgfej"
compact memory
```

因此不同 turn 的模型 context 并不等于简单历史前缀。

论文指出，一条 trajectory 的不同 turns 实际处在不同 LLM contexts 下，因此提出 multi-context GRPO，把 trajectory-level advantage 传播到每个 turn，对这些独立 context 下的 generations 端到端优化。

---

### 数据流

```text id="30dwzo"
Turn 0:
Question + Memory0
→ Action0

Turn 1:
Question + Memory1
→ Action1

Turn 2:
Question + Memory2
→ Action2
```

其中：

$$
Memory_0
\neq
Memory_1
\neq
Memory_2
$$

而且不一定有：

$$
Context_0
\subset
Context_1
\subset
Context_2
$$

这种简单 prefix 关系。

---

### 所以不能粗暴当一条 Flat Sequence

每轮：

```text id="f2fn3y"
prompt context
```

都要单独保真。

这和 Macro 5 的 per-turn GenerationRecord 逻辑非常一致。

---

## 8.27 MemSearch-o1 与普通 Summarization Memory 有什么区别？ `[P1]`

最简单 memory：

```text id="fso04w"
history
↓
LLM summary
↓
replace history
```

问题：

> summary 很容易丢失 query-document 细粒度关系。

MemSearch-o1针对 iterative think-search 中的 memory dilution，使用 query 中的 memory seed tokens 动态生长细粒度 memory fragments，再用 contribution function retrace/refine，最终重组为 globally connected memory path。

---

### 普通 Summary

```text id="0y2kmy"
many observations
↓
compress into paragraph
```

---

### MemSearch-o1

更接近：

```text id="i7w0fy"
Query Concepts
↓
Memory Seed
↓
Fine-grained Fragment Growth
↓
Contribution-based Retracing
↓
Connected Memory Path
```

---

### 为什么更适合 Search？

搜索证据经常存在：

```text id="jtmnjq"
entity A
→ relation
→ document B
→ entity C
```

普通 summary 可能把这种 relation flatten 掉。

MemSearch-o1试图让 memory 结构更贴近 reasoning path，而不是 stream-like accumulation。

---

# 8F. Counterfactual Credit

## 8.28 Counterfactual Credit Assignment 应怎样定义？ `[P2]`

最直观的问题：

> 如果没有第 \(t\) 个 action，最终结果会怎样？

定义 trajectory utility：

$$
V(\tau)
$$

删除 action \(a_t\) 后：

$$
\tau_{-t}
$$

则一个简单 counterfactual contribution：

$$
C_t
=
V(\tau)
-
V(\tau_{-t})
$$

---

### 如果：

$$
C_t\gg0
$$

说明这个 step 很重要。

如果：

$$
C_t\approx0
$$

说明可能冗余。

如果：

$$
C_t<0
$$

说明：

> 删掉它反而更好。

---

### 但真正 Agent 中不能简单“删除一行”

因为删掉：

```text id="81mdy8"
Search A
```

后面的 observation、reasoning、queries 都会改变。

真正 counterfactual 应该：

```text id="8mjdcb"
从 t 前状态
重新 rollout
```

这就变得非常昂贵。

---

## 8.29 Shapley-value 思想怎样用于 Agent Credit？ `[P2]`

如果 trajectory 有：

$$
n
$$

个关键 components：

$$
1,\ldots,n
$$

设：

$$
v(S)
$$

表示保留 subset \(S\) 后的任务价值。

Shapley value：

$$
\phi_i
=
\sum_{S\subseteq N\setminus\{i\}}
\frac{
|S|!(n-|S|-1)!
}{
n!
}
[
v(S\cup\{i\})-v(S)
]
$$

---

### 它回答

> Component \(i\) 在所有可能 coalition/order 下的平均 marginal contribution。

---

### 为什么比单纯 Leave-one-out 更公平？

有些 search step：

```text id="qrk2n1"
单独没用
```

但和另一步组合才有用。

Shapley 会考虑 interaction。

---

### Search 例子

```text id="4wbov2"
Search A:
找到人物姓名

Search B:
用姓名找到学校
```

Search B 没有 A：

> 根本无法执行。

所以 contribution 有 interaction。

---

## 8.30 Counterfactual Credit 为什么非常昂贵？ `[P2]`

Trajectory：

$$
n=20
$$

Leave-one-out 至少：

$$
20
$$

次重新评估。

完整 Shapley：

$$
2^{20}
$$

subset 级别组合，无法直接枚举。

---

### Agent Environment 更贵

一次 counterfactual 还可能需要：

```text id="us4ijc"
LLM generation
search API
browser
judge
```

---

### 所以实践中常用近似

```text id="9mnm6r"
learned critic
LLM judge
Monte Carlo Shapley
leave-one-out
local counterfactual
causal proxy
```

本质是：

> 用 judge compute 换 policy-gradient variance。

---

# 8G. Search Policy / Retriever / Memory Deep Water

## 8.31 Search Depth 为什么是 Policy-dependent Quantity？ `[P2]`

假设同一个问题。

Policy A 已知其中一部分：

```text id="38wlfg"
只需 1 次 search
```

Policy B：

```text id="n5gk5t"
需要 4 次 search
```

所以：

$$
d^*
\neq
d^*(question)
$$

更合理：

$$
d^*
=
d^*(
question,
policy,
retriever,
environment
)
$$

AutoSearch明确把 minimal sufficient depth 归因于 question complexity 和 agent capability 的共同作用。

---

### 这带来一个实验问题

如果新模型搜索更少：

> 是学会更高效 search，还是 parametric knowledge 更强？

必须控制 backbone / initial checkpoint。

---

## 8.32 Joint Retriever–Policy Training 为什么会产生 Non-stationarity？ `[P2]`

Agentic-R 做双向迭代：

```text id="m820jn"
Policy improves
↓
queries change
↓
Retriever retrains
↓
retrieval distribution changes
↓
Policy state distribution changes
```

论文正是利用 agent 的 evolving higher-quality queries 持续改进 retriever。

---

### 但这意味着

Policy 优化时环境 transition：

$$
P(O|q)
$$

也在变化。

---

### Traditional RL Assumption

通常 environment dynamics 相对固定。

这里：

```text id="bjigof"
retriever parameters
```

也更新。

---

### 可能出现 Oscillation

```text id="zq7s1i"
Policy learns query style A
↓
Retriever adapts to A
↓
Policy switches to B
↓
Retriever A optimization becomes stale
```

---

### 需要考虑

```text id="bgozlf"
alternating updates
slow retriever updates
frozen phases
versioned environment
replay compatibility
```

---

## 8.33 Memory 本身怎样做 Credit Assignment？ `[P2]`

假设 memory 中有：

```text id="2xt4sj"
M1
M2
M3
...
```

最终 answer correct。

问题：

> 哪条 memory fragment 有贡献？

---

### 不能只 Reward Search Actions

因为 memory manager 也在做 policy：

```text id="204g9o"
keep
drop
merge
rewrite
retrieve
```

---

### 可以定义

$$
C(M_i)
$$

衡量：

> 删除 \(M_i\) 后 answer quality 是否下降。

---

### 也可以看 Usage

某 fragment：

```text id="s6xmmn"
被后续 reasoning attention / retrieval 使用
```

但 usage 不是 causal contribution。

---

### Memory Credit 的困难

好 memory 可能：

```text id="flq7rh"
现在没被用
但阻止未来重复 search
```

贡献是长期的。

因此 Memory Agent 也是 long-horizon credit assignment 问题。

---

## 8.34 Query / Retrieval / Stopping 能不能 Jointly Optimize？ `[P2]`

可以，甚至这是更完整的 Search Policy。

定义 action：

$$
a_t
\in
\{
Search(q),
Visit(d),
Stop
\}
$$

Retriever 又有参数：

$$
\phi
$$

Policy：

$$
\theta
$$

目标：

$$
J(\theta,\phi)
=
\mathbb E[
R_{\text{answer}}
-
\lambda C_{\text{search}}
]
$$

---

### Joint Optimize 的吸引力

query 和 retriever 可以共同适配。

---

### 但困难

#### Credit

到底是：

```text id="zn4zgd"
query 不好
还是 retriever 不好？
```

#### Non-stationarity

两边同时变。

#### Exploration

Search policy 不发 query：

> Retriever 根本拿不到训练信号。

#### Collapse

Retriever 可能学成：

> 只适合当前 narrow policy 的特殊 query distribution。

---

### 所以通常采用

```text id="084klw"
alternating optimization
```

而不是所有模块每 step 同时更新。

---

# 8H. Multimodal Search

## 8.35 MMSearch-R1 为什么需要 Search-required + Search-free Data？ `[P2]`

Multimodal模型既有视觉输入，也可能需要外部文本/图片 search。

如果训练数据全是：

```text id="s97jvv"
必须搜索
```

最容易学到：

> 永远 search。

如果全是：

```text id="od6zsb"
不需要 search
```

又学不会工具。

MMSearch-R1因此构造包含 search-required 与 search-free samples 的 search-balanced subset，并用 outcome reward + search penalty 学习 on-demand text/image search；论文报告这种 balance 对高效搜索行为很关键。

---

### Policy 应学的不是

```text id="t3za8b"
How to search
```

而是：

```text id="yz48a1"
Whether to search
+
Which modality to search
+
How to search
```

---

### 例如

图片本身足够：

```text id="ex2m0c"
直接视觉识别
```

不应该 Web Search。

但如果问：

```text id="l3la94"
这栋建筑是哪一年建成？
```

图片识别到 landmark 后：

```text id="b5bsdm"
text search
```

才合理。

---

## 8.36 OpenSearch-VL 的 Fatal-aware GRPO 为什么值得单独理解？ `[P2]`

多模态 Search Agent 工具链更长：

```text id="xw8fuu"
image search
OCR
crop
sharpen
super-resolution
perspective correction
text search
```

任一工具失败可能产生 cascading failure。

OpenSearch-VL 提出 multi-turn fatal-aware GRPO：识别 fatal tool failure 后 mask post-failure tokens，同时通过 one-sided advantage clamping 尽量保留 failure 前有价值的 reasoning。论文还构造了统一的 text/image/OCR/crop/sharpen/super-resolution 等工具环境。

---

### 为什么不是：

```text id="ngiv0q"
失败 trajectory 全部丢掉？
```

因为：

```text id="08srtx"
failure 之前
```

可能有高价值行为。

---

### 为什么不是：

```text id="2xl3yd"
所有 token 都负 advantage？
```

因为 post-failure token 是：

> cascade consequence。

不一定每个都是独立 policy mistake。

---

### 所以它体现了一个一般原则

```text id="1yyji6"
Failure Location
应该影响
Credit Region
```

而不是：

```text id="pwvk07"
trajectory reward
机械复制到全 trajectory
```

---

## 8.37 ProMMSearchAgent 为什么把 Process Reward 与 Sim-to-Real 结合？ `[P2]`

真实 Web：

```text id="2nvvcu"
dynamic
expensive
nondeterministic
```

对 RL 不友好。

ProMMSearchAgent把 policy training 放在 deterministic local static sandbox，再使用 introspective process-oriented reward，特别训练：

> 在视觉或事实不确定时才触发 text / multimodal search。

然后将本地训练 policy zero-shot transfer 到 live Google Search API。

---

### 它实际上同时解决两个问题

#### Environment

```text id="zdo8mx"
live Web instability
↓
static sandbox
```

#### Reward

```text id="4ffnma"
outcome sparse
↓
process-oriented uncertainty/search signal
```

---

### 关键研究问题

如果 sandbox 很干净：

> Process policy 会不会只适应模拟环境？

所以必须做：

```text id="qsk833"
sim-to-real
```

验证。

---

## 8.38 LMM-Searcher 为什么把视觉信息移到 File-based External State？ `[P2]`

文本 observation 已经容易 context explosion。

图片更贵。

如果每轮搜索到图片都序列化进 multimodal context：

```text id="mldu1k"
Turn 1 images
+
Turn 2 images
+
Turn 3 images
...
```

视觉 token 成本迅速爆炸。

---

### LMM-Searcher

把视觉资产：

```text id="8n40uj"
image
```

存到外部 file system。

context 中只留下：

```text id="ap2ueo"
UID / lightweight textual reference
```

需要时调用专门的 fetch-image tool，再按需加载视觉内容。论文报告这种 file-based visual representation + progressive on-demand loading 支撑到了 100-turn search horizon。

---

### 这其实是一个很重要的 Agent State 思想

不是所有 environment state 都必须：

```text id="lhvq4n"
serialize into LLM context
```

可以：

```text id="uz584o"
externalize state
↓
store handle in context
↓
retrieve on demand
```

---

### 类比 Operating System

可以粗略理解：

```text id="h7wz9q"
Context Window
≈ working memory

External File Store
≈ external storage

UID
≈ pointer / handle
```

虽然只是类比，但对系统设计很有帮助。

---

# 8I. Search Credit 方法纵向关系

可以先形成：

```text id="0q0h7w"
Vanilla GRPO
│
│ trajectory outcome
│ same advantage across many turns
↓
Credit Ambiguity
│
├───────────────┐
│               │
↓               ↓
CW-GRPO      CriticSearch
│               │
process judge     retrospective critic
│               │
contribution      dense turn feedback
weight            │
│                 │
└──────────┬──────┘
           ↓
Fine-grained Search Credit
```

但二者不能混成一样。

---

### CW-GRPO

```text id="9v0tmf"
Outcome Reward
↓
GRPO Advantage
↓
Process Contribution Weight
↓
Turn-level weighted advantage
```

---

### CriticSearch

```text id="q3fhza"
Full trajectory + gold
↓
Retrospective Critic
↓
Dense turn-level evaluation
↓
Policy learning
```

---

### 关键区别

CW-GRPO 强调：

> 保持 outcome-based advantage 主体，用 process signal 重分配。

CriticSearch 更强调：

> 利用 privileged retrospective critic 构造 dense turn feedback。

---

# 8.39 Reward Signal 到 Loss 的完整层级

以后看任何新算法，都问：

> 它究竟改了哪一层？

```text id="szn7wz"
Environment / Verifier
        ↓
Raw Reward
        ↓
Reward Transformation
        ↓
Advantage
        ↓
Credit Weight
        ↓
Token Mask
        ↓
Importance Ratio
        ↓
Loss Aggregation
        ↓
Gradient
```

---

### 例子

#### GRPO

主要改：

```text id="43r4hs"
Reward
↓
Group-relative Advantage
```

---

#### CW-GRPO

主要改：

```text id="y4jc78"
Advantage
↓
Contribution-weighted Advantage
```

---

#### Fatal-aware GRPO

主要改：

```text id="mb1ppb"
Token Region
↓
Mask / Clamp
```

---

#### DAPO

涉及：

```text id="mdetb2"
sampling
clipping
token aggregation
overlong reward
```

---

### 这是面试最有用的统一框架

不要回答：

> CW-GRPO 是一个新的 GRPO。

而回答：

> 它没有重新定义最终 task reward，而是在 outcome advantage 与 token loss 之间加入 round-level contribution weighting。

---

# 8.40 高频连环追问

## 第一组：Reward

```text id="ijxvhn"
Outcome Reward？
↓
Process Reward？
↓
Sparse / Dense？
↓
Dense 为什么不一定更好？
↓
Reward Hacking？
↓
Process Judge 错了怎么办？
```

---

## 第二组：Verifier

```text id="nlsqja"
Rule Verifier / RM / Judge 区别？
↓
哪个最可靠？
↓
为什么 deterministic verifier 优先？
↓
Judge 怎么校准？
↓
多 Judge 怎么组合？
```

---

## 第三组：Credit

```text id="damgoi"
Trajectory credit？
↓
Turn credit？
↓
Token credit？
↓
Process reward 和 contribution weight 区别？
↓
Hard mask / soft weight？
↓
Counterfactual credit？
```

---

## 第四组：CW-GRPO

```text id="peup2x"
CW-GRPO 解决什么？
↓
Judge 输出什么？
↓
为什么不是直接 process reward？
↓
Weight 乘在哪里？
↓
Judge 错了会怎样？
```

---

## 第五组：Fatal Credit

```text id="m9uz04"
什么叫 fatal failure？
↓
为什么 post-failure token credit 不可靠？
↓
全 mask 会不会太激进？
↓
什么叫 one-sided clamp？
↓
recoverable failure 怎么办？
```

---

## 第六组：Search Policy

```text id="xyw58w"
Should search？
↓
Knowledge boundary？
↓
Over-search？
↓
Minimal sufficient depth？
↓
为什么 depth 与 agent capability 有关？
```

---

## 第七组：Retriever

```text id="0by4lz"
传统 retriever 优化什么？
↓
为什么 relevance != agent utility？
↓
Agentic-R 加了什么？
↓
joint training 有什么问题？
↓
为什么 non-stationary？
```

---

## 第八组：Memory

```text id="q9mh34"
为什么不能一直 concat history？
↓
compact memory 有什么风险？
↓
MemSearcher 怎么训多 context？
↓
MemSearch-o1 和 summary 区别？
↓
memory fragment 本身怎么 credit？
```

---

# 8.41 Self-test

## Self-test 1：Reward vs Credit

最终：

$$
R=1
$$

贡献权重：

$$
w=[0.8,0.1,0.6]
$$

如果：

$$
A^{outcome}=1.2
$$

则一种 contribution weighting：

$$
A_t
=
w_tA
$$

得到：

$$
[0.96,\;0.12,\;0.72]
$$

注意：

> 最终 reward 没变。

变的是 credit allocation。

---

## Self-test 2：Hard Mask

假设 fatal step：

$$
t_f=3
$$

mask：

$$
[1,1,1,0,0,0]
$$

说明：

```text id="3p71t6"
fatal 前保留
fatal 后不参与目标
```

但这隐含：

> step 3 后真的不存在有价值 recovery。

---

## Self-test 3：Knowledge Boundary

如果：

```text id="4nwoj2"
Internal Confidence = High
Retrieval Quality = Low
```

合理行为更接近：

> 不应盲目相信检索噪声。

---

## Self-test 4：Agentic-R

两个 passage：

```text id="bwtvjc"
A relevance = 0.95
final answer utility = 0.1

B relevance = 0.7
final answer utility = 0.9
```

Agentic Search retriever 不应只按 local relevance 排 A。

---

## Self-test 5：Memory

如果 memory compression 后：

```text id="jr44qv"
context token ↓ 70%
accuracy ↓ 15%
```

不能只报告：

> memory 很高效。

必须看：

```text id="p2nfew"
compression-efficiency / accuracy trade-off
```

---

# 8.42 推导 / 分析题

## 推导题 1：Contribution Weight 应该放 Reward 还是 Advantage？

比较：

### A

$$
R_t
=
w_tR
$$

### B

$$
A_t
=
w_tA
$$

分析两者区别。

A 会改变：

```text id="h5eudd"
reward semantics
return / baseline construction
```

B 更接近：

> 在已有 outcome evaluation 上重新分配 gradient credit。

---

## 推导题 2：Leave-one-out Credit

定义：

$$
C_t
=
R(\tau)-R(\tau_{-t})
$$

回答：

为什么：

```text id="h2pxmv"
直接删文本
```

不是可靠 counterfactual？

因为后续 state/action 依赖该 step。

应该从：

$$
s_t
$$

重新 rollout 才更接近真实 counterfactual。

---

## 推导题 3：Search Cost

Reward：

$$
R
=
R_{\text{correct}}
-
\lambda N_{\text{search}}
$$

给定：

```text id="ep9e9t"
Policy A:
accuracy = 0.8
search = 5

Policy B:
accuracy = 0.75
search = 1
```

Utility：

$$
U_A=0.8-5\lambda
$$

$$
U_B=0.75-\lambda
$$

令二者相等：

$$
0.8-5\lambda
=
0.75-\lambda
$$

得到：

$$
\lambda=0.0125
$$

所以一旦：

$$
\lambda>0.0125
$$

B 的 scalar utility 反而更高。

说明：

> Cost coefficient 会直接改变最优 policy。

---

# 8.43 Debug 题

## Debug 1：加入 Process Reward 后 Reward 大涨，Final Accuracy 下降

优先怀疑：

```text id="2yzogk"
process proxy hacking
judge bias
reward scale domination
```

检查：

```text id="12ybfn"
outcome-only metric
process metric
judge-human agreement
high reward trajectories
```

---

## Debug 2：CW-style Weight 加入后训练不稳定

检查：

```text id="3mzo1r"
weight distribution
max/min
normalization
judge calibration
advantage scale
turn mapping
```

尤其：

$$
w_t
$$

是否出现：

```text id="1rl3u0"
0.001
100
```

这种巨大 scale。

---

## Debug 3：Fatal Mask 后 Loss 大幅下降

不一定是好事。

可能只是：

```text id="kc4fka"
大量 token 被 mask
```

有效训练 tokens 减少。

应该同时看：

```text id="6j9ti0"
active token ratio
success
gradient norm
```

---

## Debug 4：Search 次数越来越少，但 Accuracy 也下降

可能：

```text id="mzifvw"
search penalty 太强
knowledge boundary estimation 太乐观
stopping reward 错
```

---

## Debug 5：Retriever Recall 上升，Agent Accuracy 不涨

说明：

```text id="yrdqmo"
retrieval metric
≠
downstream utility
```

检查：

```text id="pjsj3v"
evidence redundancy
context interference
answer synthesis
retriever utility alignment
```

---

## Debug 6：Memory 更短，但 Agent 更容易 hallucinate

可能 memory compression：

```text id="4f4klm"
删掉 critical uncertainty / provenance
```

留下的是结论，却没保留证据来源。

---

# 8.44 系统设计题

## 系统设计题 1：怎样设计一个通用 Reward Pipeline？

建议拆：

```text id="oz7p86"
Trajectory
   ↓
Verifier Layer
   ├── Exact Verifier
   ├── Tool Checker
   ├── Citation Checker
   └── LLM Judge
   ↓
Reward Components
   ↓
Normalization
   ↓
Outcome Reward
   ↓
Credit Module
   ├── trajectory
   ├── turn
   ├── contribution
   ├── fatal mask
   └── critic
   ↓
Token-level Training Signal
```

这样：

> Reward 与 Credit 解耦。

---

## 系统设计题 2：Process Judge 很贵怎么办？

可以：

```text id="n6q6sv"
judge only failed trajectories
judge only ambiguous turns
judge only sampled subset
train distilled critic
cascade cheap → expensive
cache judgement
```

不要默认：

```text id="w9s0j8"
每个 token 调一次 GPT
```

---

## 系统设计题 3：怎样验证 Credit Algorithm 真的在做 Credit？

不能只：

```text id="yqstfb"
Final Accuracy +2
```

还应该做：

```text id="igztkk"
turn removal
counterfactual perturbation
known synthetic causal tasks
judge agreement
failure-localization accuracy
```

---

### 一个很好的 Synthetic Test

人工构造：

```text id="qg2lbm"
Turn 0 useful
Turn 1 distractor
Turn 2 fatal wrong evidence
Turn 3 consequence
```

知道真正 causal structure。

看算法是否：

```text id="w6nkwo"
高权重 Turn0
低权重 Turn1
识别 Turn2
不乱罚 Turn3
```

---

# 8.45 Search Reward / Credit Paper Map

把本章专用论文放到统一坐标：

```text id="8vnxs3"
                    Search Agent
                         │
          ┌──────────────┼──────────────┐
          │              │              │
        Credit         Policy       Retrieval
          │              │              │
       CW-GRPO          KbPO         Agentic-R
       CriticSearch     AutoSearch
          │
          │
        Failure
          │
   OpenSearch-VL
 fatal-aware GRPO

                         │
                       Memory
                         │
                  MemSearcher
                  MemSearch-o1

                         │
                    Multimodal
                         │
                    MMSearch-R1
                         ↓
                     VSearcher
                         ↓
                   OpenSearch-VL
                    ↙         ↘
           ProMMSearchAgent  LMM-Searcher
```

其中，CW-GRPO、KbPO、AutoSearch、Agentic-R、MemSearcher、MemSearch-o1 和 MMSearch-R1 均已进入 ACL 2026 / Findings ACL 2026；相关方法分别对应 credit weighting、knowledge-boundary-aware search、adaptive depth、agent-aware retrieval、compact memory 与 multimodal on-demand search。

---

# 8.46 多模态 Search Agent 的纵向关系

可以粗略记：

```text id="eq4z1h"
MMSearch-R1
│
│ on-demand text/image search
│ search-required + search-free
↓
VSearcher
│
│ long-horizon real-web multimodal tool use
│ SFT → RL
↓
OpenSearch-VL
│
│ richer perception tools
│ fatal-aware GRPO
↓
ProMMSearchAgent
│
│ process-oriented reward
│ static sandbox → live Web
↓
LMM-Searcher
│
│ externalized visual state
│ on-demand image loading
│ up to 100-turn horizon
```

VSearcher将文本搜索、图像搜索和网页浏览纳入长程 multi-turn multimodal search，并采用 SFT→RL；OpenSearch-VL进一步扩展多模态工具环境和 fatal-aware credit；ProMMSearchAgent强调 process reward 与 sim-to-real；LMM-Searcher则把问题进一步推进到 100-turn 时的视觉 context explosion。

---

# 8.47 本章最重要的统一坐标系

以后看到任何 Reward / Credit 新论文，都先问四个问题。

---

## 第一问：Signal 从哪里来？

```text id="yvqwfb"
Exact Verifier?
Reward Model?
LLM Judge?
Critic?
Human?
```

---

## 第二问：Signal 表示什么？

```text id="i77zp4"
Outcome quality?
Process correctness?
Causal contribution?
Confidence?
Search necessity?
```

---

## 第三问：Signal 加在哪里？

```text id="xlvlcy"
Reward?
Advantage?
Loss weight?
Mask?
Sampling?
```

---

## 第四问：Granularity 是什么？

```text id="92qy3j"
Trajectory
Turn
Step
Token
```

如果这四个问题答不出来：

> 基本还没有真正理解这个算法。

---

# 8.48 最小知识图

最终应该形成：

```text id="6sxo7t"
                        Task Outcome
                             │
                             ↓
                     Outcome Verifier
                             │
                             ↓
                       Raw Reward
                             │
              ┌──────────────┼──────────────┐
              │              │              │
          Process Judge   Critic       Counterfactual
              │              │              │
              ↓              ↓              ↓
         Contribution     Turn Value      Marginal
           Weight                         Utility
              │              │              │
              └──────────────┼──────────────┘
                             ↓
                         Credit Map
                             │
                 ┌───────────┼───────────┐
                 │           │           │
              Weight        Mask       Clamp
                 │           │           │
                 └───────────┼───────────┘
                             ↓
                         Advantage
                             ↓
                     Token Policy Loss
```

Search Policy 侧：

```text id="wpowcf"
                     Search Decision
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
      Whether            What                Stop
        │                  │                  │
      KbPO               Query            AutoSearch
                           │
                           ↓
                        Retriever
                           │
                       Agentic-R
                           │
                           ↓
                        Evidence
                           │
                  ┌────────┴────────┐
                  │                 │
               Context           Memory
                  │                 │
          interference       MemSearcher
                            MemSearch-o1
```

Multimodal 再扩成：

```text id="4vig9r"
                    Search Agent
                         │
             ┌───────────┴───────────┐
             │                       │
           Text                    Vision
             │                       │
          Search                 Image Search
          Visit                  OCR
                                 Crop
                                 Enhance
                                 Fetch Image
                                     │
                                     ↓
                           External Visual State
```

---

# 8.49 本章最后必须会回答的一个综合题

> **给你一条 12-turn Search Agent 失败 trajectory，final reward=0。第 4 turn 搜到了正确 evidence，第 6 turn 误读了实体，第 7–12 turn 都建立在错误实体上。你怎么训练？**

不能只说：

> reward=0，然后 GRPO。

至少要讨论：

```text id="h4m8jn"
1. Outcome signal
   final = failure

2. Failure localization
   turn 6 may be first fatal error

3. Pre-failure credit
   turn 4 should not necessarily receive full negative credit

4. Post-failure region
   turn 7–12 may be cascading consequence

5. Credit strategy
   outcome-only
   contribution weighting
   retrospective critic
   fatal mask
   soft weighting

6. Judge reliability
   how sure are we turn 6 is fatal?

7. Counterfactual validation
   replace / repair turn 6 and rerun?

8. Cost
   critic/judge/counterfactual expense

9. Bias
   does process supervision distort true outcome objective?

10. Token mapping
   how do turn-level signals map onto exact response tokens?
```

能把这十点完整讲出来，Macro 8 的通用 Reward / Credit 主线才算真正建立。

下一章 Macro 9 将从算法切到真正的 rollout / serving execution layer：

```text id="zlnvsp"
Prompt / Trajectory
        ↓
     Inference Engine
        ↓
   Prefill / Decode
        ↓
      KV Cache
        ↓
Scheduling / Batching
        ↓
vLLM / SGLang
        ↓
RL Rollout Engine
```

重点会先补齐你要求保留的通用 Serving：

```text id="9gvc3k"
TTFT
TPOT
Throughput
Latency
P99
Speculative Decoding
Quantization
Admission Control
Multi-LoRA
Prefix-aware Routing
KV Eviction
SLA
```

再进入 vLLM / SGLang 的 RL-specific 能力，而不是直接把它们当两个 API 框架背。

## 9. Serving / vLLM / SGLang / Rollout Engine

前面讨论的 PPO / GRPO / Search Agent 都隐含了一件事：

```text id="3k5x4e"
给模型一个 Context
        ↓
高效生成 Response
```

如果只是单个请求，本地直接：

```python id="7z1xb5"
model.generate(...)
```

当然可以。

但真正的：

```text id="tdgraz"
Online Serving
RL Rollout
Agent Evaluation
Best-of-N
GRPO Group Sampling
```

要求同时处理大量不同长度的请求。

这时问题从：

> 模型能不能生成？

变成：

```text id="w8pchg"
GPU 如何保持高利用率？
KV Cache 怎样管理？
长 prompt 会不会拖慢 decode？
不同长度请求如何 batching？
显存满了先赶谁出去？
相同 prefix 能不能复用？
如何控制 P99 latency？
训练更新权重后旧 KV Cache 还能不能用？
rollout engine 怎么拿到新权重？
为什么相同 seed 还可能产生不同 logprob？
```

这就是 Serving / Rollout Engine。

当前 vLLM 的官方文档明确把 PagedAttention、continuous batching、chunked prefill、prefix caching、量化、speculative decoding，以及 disaggregated prefill/decode 等作为主要能力；SGLang 则明确提供 RadixAttention/prefix caching、结构化生成、Model Gateway，并为 RL 生命周期提供 sleep/wake、weight refit、pause/continue generation、deterministic inference 与 cache-aware routing 等专用接口。

因此本章必须形成下面的分层：

```text id="dzs9ve"
Transformer Inference
        ↓
Prefill / Decode
        ↓
KV Cache
        ↓
Memory Management
        ↓
Scheduler / Batching
        ↓
Serving Engine
        ├── vLLM
        └── SGLang
                ↓
        RL Rollout Lifecycle
                ↓
Training ↔ Weight Sync ↔ Rollout
```

---

# 9.0 问题矩阵

| 编号   | 问题                                                                  | 等级 |
| ---- | ------------------------------------------------------------------- | -- |
| 9.1  | TTFT、TPOT、End-to-End Latency 分别是什么？                                 | P0 |
| 9.2  | Throughput 与 Latency 为什么经常冲突？                                       | P0 |
| 9.3  | Prefill 与 Decode 有什么区别？                                             | P0 |
| 9.4  | KV Cache 到底缓存什么？为什么能加速自回归生成？                                        | P0 |
| 9.5  | KV Cache 显存怎样估算？                                                    | P0 |
| 9.6  | Continuous Batching 是什么？                                            | P0 |
| 9.7  | PagedAttention 在解决什么？                                               | P0 |
| 9.8  | Prefix Caching 是什么？                                                 | P0 |
| 9.9  | Chunked Prefill 为什么存在？                                              | P0 |
| 9.10 | Speculative Decoding 是什么？                                           | P0 |
| 9.11 | Weight / Activation / KV Cache Quantization 有什么区别？                  | P0 |
| 9.12 | vLLM 与 SGLang 各自在系统中扮演什么角色？                                         | P0 |
| 9.13 | Admission Control 为什么是 Serving 的核心机制？                               | P1 |
| 9.14 | Preemption、KV Eviction、Recomputation 分别是什么？                         | P1 |
| 9.15 | P50 / P95 / P99 为什么比平均延迟更重要？                                        | P1 |
| 9.16 | Prefix Cache 为什么主要优化 Prefill 而不是 Decode？                            | P1 |
| 9.17 | Prefix-aware Routing 为什么有用？                                         | P1 |
| 9.18 | Multi-tenant Prefix Cache 有哪些 correctness / privacy 风险？             | P1 |
| 9.19 | Multi-LoRA Serving 在解决什么？                                           | P1 |
| 9.20 | Speculative Decoding 什么时候反而没有收益？                                    | P1 |
| 9.21 | KV Cache Quantization 的收益和风险是什么？                                    | P1 |
| 9.22 | 长序列 inference OOM 到底由哪些东西造成？                                        | P1 |
| 9.23 | vLLM Scheduler 大致在做什么？                                              | P1 |
| 9.24 | SGLang 的 RadixAttention / Radix Cache 在解决什么？                        | P1 |
| 9.25 | Structured Generation 为什么对 Tool Agent 有价值？                          | P1 |
| 9.26 | Chat Serving 与 RL Rollout Workload 有什么不同？                           | P1 |
| 9.27 | 为什么 Group Rollout 特别怕 Long-tail Request？                            | P1 |
| 9.28 | RL Rollout 为什么需要 exact token IDs / logprobs，而普通 Chat Serving 往往不需要？ | P1 |
| 9.29 | Weight Update 后为什么旧 KV / Prefix Cache 可能失效？                         | P1 |
| 9.30 | SGLang 的 Sleep / Wake 为什么适合 Co-located RL？                          | P1 |
| 9.31 | SGLang 的三种 Weight Refit 路线怎么选？                                      | P1 |
| 9.32 | Pause / Continue Generation 为什么对 RL Rollout 有意义？                    | P1 |
| 9.33 | Deterministic Inference 为什么不仅是设置 Seed？                              | P2 |
| 9.34 | Training–Inference Mismatch 为什么可能破坏严格 On-policy？                    | P2 |
| 9.35 | Prefix Cache 在频繁更新 Policy 的 RL 中为什么价值会下降？                           | P2 |
| 9.36 | Disaggregated Prefill / Decode 在解决什么？                               | P2 |
| 9.37 | Continuous Batching 为什么会同时改善 Throughput 又伤害 Determinism？            | P2 |
| 9.38 | Rollout Engine 的 Weight Version 怎样进入训练 Provenance？                  | P2 |
| 9.39 | 一个请求跨越 Weight Update 时该怎么办？                                         | P2 |
| 9.40 | Serving SLA、Cost、P99、Throughput 怎样联合优化？                             | P2 |
| 9.41 | 如果设计一个 GRPO Rollout Service，你会怎样做 Scheduling？                       | P2 |
| 9.42 | vLLM / SGLang 与 Trainer 为什么应该解耦？                                    | P2 |

---

# 9A. Serving Fundamentals

## 9.1 TTFT、TPOT、End-to-End Latency 分别是什么？ `[P0]`

### TTFT

Time To First Token：

$$
TTFT
=
t_{\text{first output token}}
-
t_{\text{request arrival}}
$$

主要包含：

```text id="02zdgw"
queueing
+
tokenization / request setup
+
prefill
+
first decode
```

长 prompt 往往主要增加：

> Prefill 时间。

---

### TPOT

Time Per Output Token：

通常表示首 token 之后，每个新 token 的平均生成间隔。

近似：

$$
TPOT
=
\frac{
t_{\text{last}}
-
t_{\text{first}}
}{
N_{\text{output}}-1
}
$$

与 decode 性能关系更紧密。

---

### ITL

Inter-Token Latency：

每两个输出 token 之间：

$$
ITL_i
=
t_{i+1}-t_i
$$

TPOT 可以看作某种平均 ITL。

---

### End-to-End Latency

$$
Latency
=
t_{\text{last token}}
-
t_{\text{arrival}}
$$

粗略：

$$
Latency
\approx
TTFT
+
(N_{\text{out}}-1)
\times TPOT
$$

---

### 为什么要拆？

两个系统：

```text id="vjpysq"
System A:
TTFT = 1 s
TPOT = 20 ms

System B:
TTFT = 100 ms
TPOT = 60 ms
```

短输出：

> B 可能更快。

长输出：

> A 可能更快。

所以不能只报：

```text id="4b984v"
latency = 3.2 s
```

---

## 9.2 Throughput 与 Latency 为什么经常冲突？ `[P0]`

### Throughput

常见：

```text id="81aqfe"
requests / second
tokens / second
output tokens / second
```

---

### 提高 Batch

GPU 一次处理更多 requests：

```text id="ao7kq7"
batch ↑
↓
GPU utilization ↑
↓
throughput ↑
```

但请求可能需要排队等待形成更大 batch：

```text id="381719"
queueing ↑
↓
latency ↑
```

---

### 所以

```text id="ji6vas"
Max Throughput
≠
Min Latency
```

---

### Online Serving

通常要满足：

$$
P99(TTFT)<\tau
$$

同时尽可能提高：

$$
Tokens/s
$$

---

### RL Rollout

情况又不同。

用户并不直接等待。

更关心：

```text id="ki2hef"
总 rollout tokens / GPU-hour
```

因此可以接受更高单-request latency，只要整体训练 wall-clock 更低。

这就是：

> Production serving 与 RL rollout 的 scheduler objective 不完全一样。

---

## 9.3 Prefill 与 Decode 有什么区别？ `[P0]`

假设 prompt：

$$
x_1,\ldots,x_T
$$

然后生成：

$$
y_1,\ldots,y_K
$$

---

### Prefill

一次处理全部 prompt：

```text id="acquf7"
x1 x2 ... xT
↓
Transformer
↓
KV Cache for all prompt tokens
+
next-token logits
```

可以高度并行。

其计算类似：

$$
O(Td^2+T^2d)
$$

---

### Decode

之后每次只生成一个新 token：

```text id="cv23dd"
y1
↓
append KV

y2
↓
append KV
...
```

历史 K/V 已缓存，所以不用重算。

每次只计算：

```text id="vhokap"
new Q/K/V
+
Q attending to historical K/V
```

---

### 性能特征

Prefill：

```text id="mi070p"
compute-heavy
parallelism high
```

Decode：

```text id="3x48tc"
small matmuls
KV memory bandwidth heavy
sequential dependency
```

---

### 这就是为什么

```text id="u9rj7w"
TTFT
```

和：

```text id="86iyqf"
TPOT
```

需要分开优化。

---

## 9.4 KV Cache 到底缓存什么？为什么能加速自回归生成？ `[P0]`

Self-Attention 每层都有：

$$
K_t,\;V_t
$$

历史 token 的 K/V 在下一步不会改变。

---

### 没有 Cache

生成 token \(t+1\) 时：

```text id="6jktrd"
重新计算
token 1...t
全部 K/V
```

造成大量重复。

---

### 有 KV Cache

第一次：

```text id="gdvs8f"
prompt
↓
compute K/V
↓
store
```

之后每个 token 只计算：

$$
K_{\text{new}},
V_{\text{new}}
$$

历史：

$$
K_{1:t},V_{1:t}
$$

直接复用。

---

### 于是 Decode

从：

> 每一步重新执行完整 prefix forward

变成：

> 只计算新 token，并读取历史 KV。

---

### 代价

KV Cache 需要显存，而且：

$$
M_{KV}\propto T
$$

长 context 和高 concurrency 会迅速吃掉 GPU memory。

---

## 9.5 KV Cache 显存怎样估算？ `[P0]`

对于标准 GQA/MHA 类模型，可以粗略写：

$$
M_{KV}
=
2
\times
N_{\text{layers}}
\times
T
\times
N_{\text{kv-heads}}
\times
d_{\text{head}}
\times
b
$$

其中：

* 2：K + V；
* \(T\)：cached tokens；
* \(b\)：每元素 bytes。

---

### 例子

假设：

```text id="09qrzi"
layers = 32
KV heads = 8
head dim = 128
context = 32768
dtype = BF16 = 2 bytes
```

单 sequence：

$$
M
=
2
\times32
\times32768
\times8
\times128
\times2
$$

约：

$$
4\text{ GiB}
$$

量级。

这只是粗算，不含：

* allocator metadata；
* alignment；
* hybrid attention；
* multimodal encoder cache；
* runtime buffers。

---

### 为什么 GQA 很值？

因为：

$$
M_{KV}
\propto
N_{\text{kv-heads}}
$$

32 KV heads 降到 8：

$$
KV\ memory
\approx
25\%
$$

---

## 9.6 Continuous Batching 是什么？ `[P0]`

传统 static batching：

```text id="gqe8e7"
Request A length 100
Request B length 500

必须一起等到 B 完成
↓
batch 才结束
```

A 结束后 GPU slot 闲着。

---

### Continuous Batching

每个 decode iteration 都重新决定：

```text id="rjqt9k"
哪些 requests 进入本轮 forward
```

如果 A 完成：

```text id="s8cg9n"
立刻加入新 Request C
```

不需要等待整个 batch。

---

### 数据流

```text id="94sybc"
step 1:
A B C

step 2:
A B C

A finishes

step 3:
D B C
```

---

### 优点

* GPU utilization 高；
* 不同长度请求混合更有效；
* throughput 提升。

vLLM 官方当前把 continuous batching 列为核心 serving 能力之一。

---

## 9.7 PagedAttention 在解决什么？ `[P0]`

KV Cache 的一个工程问题：

> 每个 request 最终长度未知。

如果预先分配：

$$
max\_seq\_len
$$

会浪费巨大显存。

---

### 连续分配的问题

Request A：

```text id="vjjd5m"
实际 1000 tokens
但预留 32000
```

大量空间空着。

此外不同 requests 开始结束时间不同，会产生 fragmentation。

---

### PagedAttention

核心思想类似 OS virtual memory：

```text id="dpn8gu"
logical KV sequence
↓
fixed-size blocks/pages
↓
physical GPU blocks
```

不要求某个 sequence 的 KV 在显存中物理连续。

---

### 好处

按需分配：

```text id="5bfq15"
token grows
↓
allocate new KV block
```

减少：

* internal fragmentation；
* over-reservation。

同时 block 更容易：

* share；
* evict；
* reuse。

vLLM 将 PagedAttention 明确作为高效管理 attention K/V memory 的核心机制。

---

### 不要答成

> PagedAttention 改了 Attention 数学公式。

没有。

主要改变：

> KV Cache 的物理存储与访问管理。

---

## 9.8 Prefix Caching 是什么？ `[P0]`

假设很多 requests 都共享：

```text id="dmdzks"
same system prompt
+
same long document
```

例如：

```text id="d2bp0o"
Prompt A:
[20K shared prefix] + question A

Prompt B:
[20K shared prefix] + question B
```

普通 inference：

> 20K prefix 被重复 prefill。

---

### Prefix Cache

第一次请求已经算出：

$$
KV_{\text{shared prefix}}
$$

第二个请求检测到相同 token prefix：

```text id="ht1i9m"
cache hit
↓
reuse KV
```

只需要 prefill新的 suffix。

vLLM 当前的 Automatic Prefix Caching 就是缓存已有 request 的 KV blocks，在新 request 命中相同 prefix 时跳过共享部分的重复计算。

---

### 它改变输出吗？

正确实现下不应该。

它只是：

```text id="kbgkyx"
reuse exact previous computation
```

而不是近似。

---

## 9.9 Chunked Prefill 为什么存在？ `[P0]`

假设突然来一个：

```text id="1zmm6i"
100K-token prompt
```

如果整个 prefill 一次占用一个巨大 forward：

```text id="l32fdj"
decode requests
必须等它
```

TPOT / P99 ITL 可能恶化。

---

### Chunked Prefill

把长 prompt：

$$
T
$$

拆成：

$$
T_1,T_2,\ldots
$$

分多 scheduler steps 处理。

例如：

```text id="9xd5cq"
100K prompt

→ 8K
→ 8K
→ 8K
...
```

这样 decode requests 可以在中间被 interleave。

vLLM 的 scheduler 当前支持 chunked prefill，并允许按 batched-token budget 分块调度。

---

### Trade-off

Chunk 太大：

```text id="yf5t8a"
prefill efficient
but decode tail latency bad
```

Chunk 太小：

```text id="jpp7z6"
better interleaving
but more scheduling/kernel overhead
```

---

## 9.10 Speculative Decoding 是什么？ `[P0]`

标准 decode：

```text id="7t5zyx"
Target Model
↓
1 token
↓
Target Model
↓
1 token
...
```

串行。

---

### Speculative

先让便宜的 draft mechanism 猜多个 tokens：

$$
\hat y_1,\ldots,\hat y_k
$$

然后 target model 一次验证多个位置。

```text id="uuzmdf"
Draft
→ A B C D

Target verifies
→ A ✓
→ B ✓
→ C ✓
→ D ✗
```

接受 prefix：

```text id="73wn0i"
A B C
```

再继续。

---

### 加速来源

一次昂贵 target forward：

> 推进多个 output tokens。

vLLM 当前支持多类 speculative decoding，包括 n-gram、EAGLE 等方案。

---

### Exact 吗？

正确 speculative sampling 算法可以保持 target distribution。

关键是：

> Draft 只是 proposal，不是偷偷用小模型替代 target output distribution。

---

## 9.11 Weight / Activation / KV Cache Quantization 有什么区别？ `[P0]`

### Weight Quantization

例如：

```text id="bj1rwf"
BF16 → INT8 / INT4 / FP8
```

主要减少：

* model weight memory；
* weight bandwidth。

---

### Activation Quantization

中间 activation 也降低 precision。

更难，因为 activation distribution 随输入变化。

---

### KV Cache Quantization

只量化：

```text id="vnutsa"
cached K/V
```

目的：

$$
KV\ capacity\uparrow
$$

于是：

* 更长 context；
* 更高 concurrency。

---

### 为什么不能混为“INT4 模型”？

因为可能：

```text id="teikxg"
Weights INT4
Activations BF16
KV FP8
```

各部分 dtype 不同。

vLLM 当前支持多种 weight quantization 格式，同时也提供独立 KV-cache dtype 配置；SGLang 文档也把 Quantization 与 Quantized KV Cache 作为分开的 serving 能力。

---

## 9.12 vLLM 与 SGLang 各自在系统中扮演什么角色？ `[P0]`

两者首先都是：

> 高性能 LLM inference / serving engines。

不是 RL optimizer。

---

### vLLM

重点能力包括：

```text id="506cw5"
PagedAttention
Continuous Batching
Prefix Caching
Chunked Prefill
Speculative Decoding
Quantization
Distributed Inference
OpenAI-compatible Serving
```

官方文档也列出了 TP / PP / DP / EP / CP 以及 disaggregated prefill/decode 等能力。

---

### SGLang

同样做高吞吐 serving，但有自己的：

```text id="y9cjrb"
RadixAttention / Radix Cache
structured generation
tool parser
Model Gateway
PD disaggregation
```

并且现在有一套非常明确的 RL lifecycle API：

```text id="6g3yn8"
sleep / wake
weight refit
pause / continue
deterministic inference
cache-aware load balancing
```

---

### 最重要边界

```text id="ct4phi"
vLLM / SGLang
= inference / rollout engine

verl
= distributed RL training/dataflow framework

rLLM
= Agent harness ↔ RL abstraction

Search Agent Harness
= environment / trajectory / policy logic
```

不能把它们全部说成：

> RL framework。

---

# 9B. Scheduling / Cache / Production Serving

## 9.13 Admission Control 为什么是 Serving 的核心机制？ `[P1]`

假设服务器显存只够：

```text id="nxg6z5"
100 GB KV
```

现在来：

```text id="3525mj"
200 个 128K requests
```

如果全部 admit：

```text id="hb8k4w"
KV oversubscription
↓
constant preemption
↓
recompute
↓
thrashing
↓
everyone slow
```

---

### Admission Control

决定：

> 哪些请求现在允许进入 running set？

考虑：

```text id="3mprwr"
KV capacity
prompt length
expected output
priority
SLA
```

---

### 为什么不是队列越短越好？

过度 admission：

> GPU 看起来一直忙，但大量工作被重复丢弃 / 重算。

这就是 thrashing。

---

### vLLM 例子

当前 scheduler 提供 full input length reservation 和 KV watermark 等机制，用于避免 over-admission 与 KV-cache thrashing。

---

## 9.14 Preemption、KV Eviction、Recomputation 分别是什么？ `[P1]`

### Preemption

暂停 running request，把资源让给别人。

---

### KV Eviction

释放该 request 的部分/全部 KV blocks。

---

### Resume

如果 KV 已丢失：

> 后面恢复 request 时需要重新 prefill历史 prefix。

即 recomputation。

---

### Trade-off

```text id="2kyu1r"
keep KV
→ memory expensive
→ resume cheap

evict KV
→ memory cheap
→ resume expensive
```

---

### 为什么 Long Request 很麻烦？

它占：

$$
M_{KV}\propto T
$$

且如果被 preempt：

> 重建成本也大。

---

## 9.15 P50 / P95 / P99 为什么比平均延迟更重要？ `[P1]`

假设：

```text id="l7a3wu"
99 requests = 1 sec
1 request = 100 sec
```

平均：

$$
1.99s
$$

看起来还能接受。

但有 1% 用户经历：

$$
100s
$$

---

### Production SLA

往往关注：

```text id="ja1psf"
P50
P95
P99
```

特别是：

$$
P99(TTFT)
$$

$$
P99(TPOT)
$$

---

### Agent RL 也有 Tail 问题

Group rollout：

```text id="np229n"
15 trajectories finish in 10 s
1 trajectory takes 120 s
```

同步训练可能全部等它。

于是：

> P99 rollout latency 直接决定 trainer idle time。

---

## 9.16 Prefix Cache 为什么主要优化 Prefill 而不是 Decode？ `[P1]`

Prefix cache 重用：

$$
K/V
$$

主要是为了避免再次计算共享 prompt prefix。

---

### 对 Prefill

原来：

$$
20K
$$

shared prefix 要重新跑。

命中 cache 后：

```text id="twjvtq"
skip 20K prefix compute
```

TTFT 显著降低。

---

### 对 Decode

生成新 token：

$$
y_t
$$

仍必须执行新一步 Transformer forward。

Prefix Cache 不会直接：

> 预先知道未来 token 的 KV。

所以 TPOT 收益通常没 TTFT 那么直接。

---

## 9.17 Prefix-aware Routing 为什么有用？ `[P1]`

假设两个 replicas：

```text id="c83soe"
Server A
cached prefix P

Server B
no prefix P
```

新 request 也以：

$$
P
$$

开头。

---

### Round-robin

可能发到 B：

> cache miss。

---

### Prefix-aware Router

优先发到 A：

> cache hit。

---

### 但不能只看 Cache

如果 A：

```text id="4n1vtx"
queue = 100
```

B：

```text id="qbygo8"
queue = 0
```

可能 cache hit 也不值得。

所以实际路由目标类似：

$$
Score
=
f(
cache\ hit,
load,
latency,
capacity
)
$$

SGLang RL 文档明确把 cache-aware load balancing 作为 Model Gateway 面向大规模 rollout 的能力之一。

---

## 9.18 Multi-tenant Prefix Cache 有哪些 Correctness / Privacy 风险？ `[P1]`

### Correctness

如果 cache-key hash collision：

```text id="bm8r9k"
Prefix A
和
Prefix B
误认为相同
```

可能复用错误 KV。

vLLM 当前文档因此明确提示，非加密 hash 理论上增加 hash collision 风险，并可能在多租户环境中导致未定义行为甚至隐私泄露。

---

### Privacy

如果跨 tenant 共享 cache metadata：

> cache hit timing 本身可能形成 side channel。

---

### Tenant Isolation

需要考虑：

```text id="5zn8mz"
tenant-specific namespace
cache key salt
secure hashing
access control
```

---

### 另一个 correctness 问题

即使 tokens 相同：

如果模型权重不同：

```text id="s2p4t4"
Policy v1
Policy v2
```

旧 KV 也不能直接认为有效。

后面 9.29 会展开。

---

## 9.19 Multi-LoRA Serving 在解决什么？ `[P1]`

假设：

```text id="2vnlrz"
一个 70B Base
+
100 个 Task LoRA
```

最笨方式：

```text id="hi276r"
启动 100 份完整模型
```

显然浪费。

---

### Multi-LoRA

共享：

$$
W_0
$$

请求只指定：

```text id="t0oz3u"
adapter A
adapter B
adapter C
```

服务器动态加载/路由 adapter。

---

### 好处

```text id="79cvv4"
Base 权重共享
adapter 很小
多任务部署成本下降
```

---

### 调度问题

同一个 batch：

```text id="9yfsgi"
Request 1 → LoRA A
Request 2 → LoRA B
Request 3 → LoRA A
```

runtime 必须处理 adapter-specific computation。

---

### RL 也有价值

例如：

```text id="77fknd"
Frozen Base
+
Policy LoRA
```

Trainer 只更新 LoRA。

Rollout engine 只需同步 adapter，而不一定同步完整 base model。

---

## 9.20 Speculative Decoding 什么时候反而没有收益？ `[P1]`

### Draft Acceptance 很低

Draft 猜：

```text id="3j9r1c"
A B C D
```

Target 每次第一个就拒绝。

那么：

```text id="kcns3u"
draft compute
+
verification compute
```

反而增加成本。

---

### Target 很小

本来 decode 已经很快。

draft overhead 不值。

---

### Memory / Communication 成为瓶颈

多个模型共存可能增加显存压力。

---

### RL Rollout 特别要注意 Sampling

高 temperature：

```text id="eqp80f"
target distribution 更散
```

draft acceptance 可能下降。

---

### 长 reasoning 是否一定适合 speculative？

不一定。

要测：

```text id="anq71s"
acceptance rate
tokens per target step
end-to-end throughput
```

而不是看到：

> speculative decoding

就默认加速。

---

## 9.21 KV Cache Quantization 的收益和风险是什么？ `[P1]`

原本：

```text id="8p0zsd"
KV BF16
= 2 bytes / element
```

如果：

```text id="k4c92x"
KV FP8
≈ 1 byte / element
```

理论 storage 接近减半。

---

### 收益

可以：

```text id="vmm8pw"
context ↑
concurrency ↑
```

---

### 风险

Attention 使用 quantized K/V：

> numerical error 进入后续所有 decode steps。

尤其 long context 时：

```text id="5cgfxp"
很多历史 token
都经过 quantized cache
```

误差可能影响 accuracy。

---

### 系统成本

还可能有：

```text id="zmsppb"
quantize
dequantize
scale metadata
kernel support
```

因此 storage 减半：

> 不等于 latency 减半。

---

## 9.22 长序列 Inference OOM 到底由哪些东西造成？ `[P1]`

不只一个原因。

### Model Weights

固定：

$$
M_W
$$

---

### KV Cache

随：

$$
T\times concurrency
$$

增长。

---

### Temporary Workspace

Attention / GEMM kernels 需要 scratch memory。

---

### CUDA Graph

不同 batch shape 可能预留 buffers。

---

### Multimodal Encoder Cache

VLM 还有 image/video embeddings。

---

### Fragmentation

即使 total free memory 看起来够：

> 也可能没有合适连续块 / allocator state。

---

### 所以 OOM 排查

```text id="c2j7nk"
weights?
KV?
batch concurrency?
max_model_len?
workspace?
graphs?
multimodal cache?
fragmentation?
```

不能只：

```text id="yzkjgz"
降低 max_new_tokens
```

---

## 9.23 vLLM Scheduler 大致在做什么？ `[P1]`

vLLM 当前 scheduler 每个 engine iteration 做一次 scheduling decision，每个 step 对应一次 model forward，并决定每个 request 本轮处理多少 tokens：新 request 可能处理多枚 prompt tokens，而 autoregressive request 通常推进少量 decode tokens。

---

### Scheduler 需要同时考虑

```text id="6z8hs7"
waiting requests
running requests
KV blocks
prefill budget
decode requests
priority
preemption
```

---

### 输出近似

```text id="2kbvlv"
Request A: process 1 token
Request B: process 1 token
Request C: prefill 4096 tokens
```

然后形成一个 batch forward。

---

### Scheduler 的本质

不是：

> 把请求放进队列。

而是在每个 inference step 解决：

$$
\max
\text{hardware utilization}
$$

subject to：

```text id="fck9jz"
KV capacity
latency constraints
request fairness
```

---

# 9C. SGLang / Agent Serving

## 9.24 SGLang 的 RadixAttention / Radix Cache 在解决什么？ `[P1]`

Search Agent / Multi-turn Chat 有大量 shared prefix：

```text id="d62x0d"
System Prompt
+
Conversation Prefix
+
Tool History
```

不同后续请求可能共享很长 prefix。

---

### Radix Tree

把不同 sequences 的共享 token prefix：

```text id="hjhrjk"
A B C D E
A B C F G
A B H I
```

组织成：

```text id="xbpinm"
A
└── B
    ├── C
    │   ├── D E
    │   └── F G
    └── H I
```

相同 prefix 的 KV 可以复用。

SGLang 官方把 RadixAttention / prefix caching 作为其 serving runtime 的核心机制之一。

---

### 为什么特别适合 Agent？

Multi-turn Agent：

```text id="c6a1yz"
Turn 0 context
      ↓
Turn 1 = Turn0 + observation
      ↓
Turn 2 = Turn1 + observation
```

prefix overlap 天然很高。

---

## 9.25 Structured Generation 为什么对 Tool Agent 有价值？ `[P1]`

普通 sampling：

```text id="0tn8hf"
任意 token
```

可能生成：

```text id="tkjfk6"
{"tool": "search", "query": "abc"
```

缺右括号。

---

### Structured Decoding

用：

```text id="ae5yp6"
JSON schema
grammar
regex
```

限制合法 next tokens。

SGLang 当前文档把 Structured Outputs 和 Tool Parser 都作为独立能力。

---

### 好处

```text id="5xwhdr"
invalid action ↓
parser failure ↓
retry ↓
```

---

### 但它改变 Behavior Policy

如果 unconstrained model：

$$
\pi_\theta(a|s)
$$

经过 grammar restriction：

$$
\tilde\pi_\theta(a|s)
$$

实际 rollout 来自：

$$
\tilde\pi
$$

而不是裸 softmax。

---

### RL 意义

old logprob 到底应该对应：

```text id="3dhzhj"
raw model distribution
还是
constrained behavior distribution
```

必须明确。

否则 behavior-policy provenance 不完整。

---

## 9.26 Chat Serving 与 RL Rollout Workload 有什么不同？ `[P1]`

### Chat Serving

目标：

```text id="esaozy"
低 TTFT
平滑 streaming
低 P99
用户公平性
```

请求一般独立。

---

### RL Rollout

目标更像：

```text id="2lv89a"
最大化
useful rollout tokens / GPU-hour
```

同时有：

```text id="xkgupi"
same-prompt groups
policy versions
old logprobs
exact token IDs
reward evaluation
weight refit
```

---

### Chat Request 完成即可释放

RL rollout 完成后还要：

```text id="ldiwji"
trace
reward
group assembly
trainer
```

---

### RL Policy 会频繁变化

Production model：

```text id="qtwd4m"
可能一天更新一次
```

RL：

```text id="ol7dxl"
可能每 optimizer iteration 更新
```

所以 weight sync 成为 first-class operation。

---

## 9.27 为什么 Group Rollout 特别怕 Long-tail Request？ `[P1]`

GRPO：

```text id="jh7i0v"
Prompt q
↓
G = 16 rollouts
```

需要组成完整 group 算：

$$
\mu_R,\sigma_R
$$

---

### 假设

```text id="x4av6n"
15 rollouts: 10 s
1 rollout: 120 s
```

如果严格 barrier：

> 15 个结果等 110 秒。

---

### 系统表现

```text id="1kwfhp"
rollout GPUs may be idle
trainer waits
wall-clock dominated by P99
```

---

### 为什么 Agent 更严重？

因为某条 trajectory 可能：

```text id="2hwpav"
tool timeout
very long reasoning
extra search turns
```

horizon variance 很大。

---

### 解决方向

```text id="7atjwe"
async rollout
partial groups
timeout
pause/recycle
dynamic batching
straggler mitigation
```

但每一种都可能改变 RL semantics。

---

## 9.28 RL Rollout 为什么需要 Exact Token IDs / Logprobs，而普通 Chat Serving 往往不需要？ `[P1]`

Chat API 用户只需要：

```text id="0koq2r"
"最终文字"
```

内部 token IDs 往往可以丢。

---

### PPO / GRPO

训练需要：

$$
\log\pi_{\text{old}}(a_t|s_t)
$$

必须知道：

```text id="8viwlw"
exact action token a_t
```

---

### 所以 Rollout API 最好返回

```text id="3cqv3k"
token_ids
token_logprobs
finish_reason
sampling seed
weight version
```

而不仅：

```text id="dcw941"
text
```

---

### 这就是

```text id="1jc8w3"
Serving API
```

和：

```text id="5phsud"
Training-grade Rollout API
```

之间的重要区别。

---

## 9.29 Weight Update 后为什么旧 KV / Prefix Cache 可能失效？ `[P1]`

KV Cache：

$$
K_l
=
H_lW_K
$$

$$
V_l
=
H_lW_V
$$

其中：

$$
H_l
$$

和：

$$
W_K,W_V
$$

都依赖模型权重。

---

### Policy 更新

$$
\theta
\rightarrow
\theta'
$$

对相同 prefix：

$$
KV_{\theta}
\neq
KV_{\theta'}
$$

---

### 如果继续使用旧 Cache

新模型：

```text id="rs6cyn"
θ'
```

却读取：

```text id="ef6w6m"
KV generated by θ
```

形成混合模型计算。

这不是正常：

$$
\pi_{\theta'}
$$

---

### 因此 Cache 必须 Invalidate / Version

vLLM 当前 scheduler 接口明确指出，模型权重 live update 后需要重置 prefix KV cache；其 scheduler 也提供 reset prefix cache 的逻辑。

SGLang 的 weight-update API 默认也提供 `flush_cache` 选项。

---

## 9.30 SGLang 的 Sleep / Wake 为什么适合 Co-located RL？ `[P1]`

Co-located：

```text id="b78bdn"
same GPUs
轮流做
Training
和
Rollout
```

问题：

```text id="5zg5du"
Trainer weights / optimizer
很占显存

Rollout KV cache / engine weights
也占显存
```

同时存在容易 OOM。

---

### Sleep

Training 阶段：

```text id="avpw7j"
release rollout KV
甚至 release rollout weights
```

但保持 server process 活着。

---

### Wake

Training 完成：

```text id="w0z8tk"
resume weights / memory
↓
rollout continues
```

SGLang 当前提供细粒度 memory saver，可以分别释放 `kv_cache`、`weights`，之后再 resume，同时避免每个 RL step 都完整重启服务和重新捕获 CUDA Graph。

---

### 本质

```text id="yp95bi"
time multiplex GPU memory
```

而不是：

> 同时把 trainer 和 rollout 全塞进显存。

---

## 9.31 SGLang 的三种 Weight Refit 路线怎么选？ `[P1]`

当前 SGLang RL 文档提供三类更新路线。

---

### 1. From Disk

```text id="be9aoj"
Trainer
↓
save checkpoint
↓
Rollout server load checkpoint
```

优点：

* 简单；
* checkpoint 是 source of truth；
* rollout replica 易弹性扩缩。

问题：

* disk/object-storage I/O。

---

### 2. From Tensor

```text id="kscq44"
Trainer tensor
↓
in-memory transfer
↓
Rollout
```

适合：

```text id="wfww95"
co-located trainer + rollout
```

避免 disk。

---

### 3. Distributed Weight Update

Trainer 与 rollout 分离：

```text id="etfmqq"
Trainer Workers
↓ NCCL / IB
Rollout Workers
```

适合大规模 disaggregated cluster。

---

### 对照

```text id="fjm7vd"
Disk
simple / elastic / slow I/O

Tensor
fast / co-located

Distributed
fast at scale / infra complex
```

---

## 9.32 Pause / Continue Generation 为什么对 RL Rollout 有意义？ `[P1]`

RL rollout 有 long-tail。

如果一个 trajectory 还在慢慢执行：

```text id="uts40c"
不能让整个 step 永远等它
```

---

### Pause

保存 request state。

可以：

```text id="i66ac9"
暂停慢请求
↓
先收集足够其他 rollouts
↓
trainer update
```

---

### Continue

之后：

```text id="2zdboi"
resume unfinished request
```

SGLang 当前明确提供 `pause_generation` / `continue_generation`，并指出多轮 RL 中少数长尾请求可能阻塞整个 batch；其推荐流程允许暂停、更新权重后再继续。

---

### 但这里有算法问题

如果：

```text id="j85ryf"
前 100 tokens
来自 policy v1

后 100 tokens
来自 policy v2
```

整个 response 已经不是单一 behavior policy。

因此必须记录：

```text id="xstf22"
per-token weight version
```

SGLang 当前甚至直接支持输出 token range 对应的 weight versions。

---

# 9D. RL-specific Deep Water

## 9.33 Deterministic Inference 为什么不仅是设置 Seed？ `[P2]`

很多人认为：

```python id="p1w07g"
torch.manual_seed(42)
temperature = 0
```

就完全 deterministic。

不够。

---

### GPU Floating Point

$$
(a+b)+c
\neq
a+(b+c)
$$

有限精度下 reduction order 不同：

> 结果有微小差异。

---

### Dynamic Batching

同一个 request：

第一次和 batch size 8 一起跑。

第二次和 batch size 37 一起跑。

kernel reduction shape 可能不同。

于是 logits：

$$
z
$$

有 tiny drift。

---

### Argmax Boundary

如果两个 token：

```text id="5n49bo"
A = 10.000001
B = 10.000000
```

tiny numerical perturbation 就可能反转。

---

### SGLang 当前文档

明确指出即使 `temperature=0`，dynamic batching 和 GPU reduction order 也可能带来不同输出；其 deterministic inference 通过 batch-invariant operations 降低这种差异。

---

### RL 为什么更敏感？

因为我们不仅关心 token：

还关心：

$$
\log p_t
$$

tiny drift 会直接进入：

$$
\frac{
\pi_\theta
}{
\pi_{\text{old}}
}
$$

---

## 9.34 Training–Inference Mismatch 为什么可能破坏严格 On-policy？ `[P2]`

Rollout engine：

```text id="0dtlrv"
SGLang/vLLM kernels
```

Trainer forward：

```text id="nl2t1j"
PyTorch / FlashAttention / different kernels
```

即使权重完全相同：

$$
\theta_{\text{rollout}}
=
\theta_{\text{trainer}}
$$

两边得到：

$$
\log p_{\text{rollout}}
\neq
\log p_{\text{trainer}}
$$

---

### PPO 初始 Ratio

理论上训练刚开始：

$$
\pi_\theta
=
\pi_{\text{old}}
$$

因此：

$$
r_t=1
$$

---

### 但如果 Backend Mismatch

可能：

$$
r_t
=
e^{
\log p_{\text{train}}
-
\log p_{\text{rollout}}
}
\neq1
$$

还没 optimizer.step：

> ratio 已经偏离 1。

---

### 这意味着

系统声称：

```text id="4cjbza"
on-policy
```

但 numerical execution path 已经制造 behavior mismatch。

SGLang 的 RL 文档直接把这一问题称为 training–inference mismatch，并指出仅让 inference deterministic 还不足以实现“true on-policy”，training engine 也要使用匹配的 deterministic kernels。

---

## 9.35 Prefix Cache 在频繁更新 Policy 的 RL 中为什么价值会下降？ `[P2]`

Production：

```text id="3rzbti"
weights fixed
```

同一个 system prompt：

> 可以 cache 很久。

---

### RL

```text id="w8teuw"
policy v1
↓
rollout
↓
optimizer
↓
policy v2
↓
rollout
```

每次：

$$
KV_{\theta}
$$

都会变化。

所以 weight update 后：

```text id="zerz7v"
old prefix cache invalid
```

---

### 结果

如果每 1 分钟 refit 一次：

> Prefix Cache 来不及积累长期高 hit rate。

---

### 但不是完全没用

一个 rollout phase 内：

```text id="cmiqp3"
weights temporarily fixed
```

同 prompt 的：

```text id="idvf3p"
G=16
```

group samples 可以共享 prompt prefix。

Multi-turn Agent 的 shared history 也可复用。

---

### 所以 Cache Value

大致取决于：

$$
reuse\ frequency
$$

和：

$$
weight\ update\ frequency
$$

之间的比值。

---

## 9.36 Disaggregated Prefill / Decode 在解决什么？ `[P2]`

Prefill 与 Decode 硬件特征不同：

```text id="35ksrn"
Prefill:
large GEMM
compute-heavy

Decode:
small steps
memory-bandwidth / latency sensitive
```

如果放同一 engine：

长 prefill 插入 decode batch：

> 可能伤害 tail TPOT。

---

### Disaggregation

```text id="ap4wur"
Prefill Pool
↓
KV transfer
↓
Decode Pool
```

两边可以独立调：

* parallelism；
* GPU types；
* capacity。

vLLM 当前官方将 disaggregated prefill 标为 experimental，并明确给出的动机包括独立调 TTFT 与 inter-token latency，以及控制 decode tail latency。

SGLang 当前也提供 PD Disaggregation。

---

### 代价

新增：

```text id="8no7yf"
KV transfer
network
routing
deployment complexity
```

所以不一定单机也值得。

---

## 9.37 Continuous Batching 为什么会同时改善 Throughput 又伤害 Determinism？ `[P2]`

Continuous batching 每个 step 动态改变：

```text id="80gczv"
batch composition
batch shape
```

---

### Performance

好处：

```text id="92eplr"
fill idle slots
↓
GPU utilization ↑
```

---

### Numerics

不同 batch shape：

> kernel implementation / reduction order 可能不同。

浮点结果出现微小变化。

---

### 所以产生张力

```text id="ejq6la"
dynamic scheduling
→ performance

batch invariance
→ determinism
```

高级 serving engine 要尽量：

> 两边都要。

而不是简单：

```text id="il3swa"
关闭 continuous batching
```

把 throughput 全牺牲掉。

---

## 9.38 Rollout Engine 的 Weight Version 怎样进入训练 Provenance？ `[P2]`

最低限度每条 generation 应保存：

```text id="e1vbln"
policy_version
```

例如：

```text id="ardlcs"
step_4200
```

---

### 如果整个 request 用同一权重

简单：

```text id="n45zjp"
response.weight_version = 4200
```

---

### 如果跨 Weight Update

需要：

```text id="zqzxfv"
token 0–57: v4200
token 57–128: v4201
```

SGLang 当前 RL API 已提供这种 per-token range weight-version attribution。

---

### Trainer 怎么办？

有三种选择。

#### 1. Reject Mixed-version Sequence

最干净。

#### 2. Split into Segments

每段对应不同 behavior policy。

但 sequence-level objective 会变复杂。

#### 3. Per-token Old Policy

每 token 使用它真实生成时的：

$$
\log\pi_{\text{behavior},t}
$$

理论更精确，但 group / sequence semantics 复杂。

---

### 最重要原则

不能：

```text id="k2adva"
整条 response
假装来自最后一个 policy version
```

---

## 9.39 一个请求跨越 Weight Update 时该怎么办？ `[P2]`

最简单：

```text id="xum0bm"
rollout phase
freeze weights
↓
all requests finish
↓
update
```

这是 synchronous barrier。

---

### 优点

behavior semantics 清楚。

---

### 缺点

long tail 拖慢训练。

---

### Async Alternative

暂停 unfinished：

```text id="d6rxjj"
v1 prefix
↓
update v2
↓
continue
```

---

### 问题

后续 token 条件于：

```text id="5s1rj1"
v1 generated prefix
```

但由：

```text id="k651rt"
v2
```

继续生成。

这在环境上没问题：

> Prefix 就是 state。

但 policy provenance 变成 mixed-version。

---

### 训练层必须决定

```text id="lzody4"
允许 mixed behavior?
segment?
discard?
off-policy correct?
```

系统不能偷偷替算法做决定。

---

## 9.40 Serving SLA、Cost、P99、Throughput 怎样联合优化？ `[P2]`

真实 serving objective 不是：

$$
\max Throughput
$$

这么简单。

更像：

$$
\min Cost
$$

subject to：

$$
P99(TTFT)\le\tau_1
$$

$$
P99(TPOT)\le\tau_2
$$

$$
Availability\ge A_0
$$

$$
Throughput\ge Q_0
$$

---

### 调参之间有关联

提高 batch：

```text id="ypvmpt"
throughput ↑
latency ↑
```

提高 KV utilization：

```text id="y5s5ai"
concurrency ↑
OOM/thrashing risk ↑
```

更 aggressive preemption：

```text id="uhd7yr"
fairness ↑?
recompute ↑
```

---

### RL Rollout SLA

可以换成：

$$
\min
GPUHours
$$

subject to：

```text id="bc2rtk"
group completeness
policy staleness
max rollout age
trace correctness
```

---

## 9.41 如果设计一个 GRPO Rollout Service，你会怎样做 Scheduling？ `[P2]`

假设：

```text id="ip853v"
N prompts
G = 16 rollouts / prompt
```

---

### Naive

```text id="6v6tpj"
Prompt 1 ×16
finish all
↓
Prompt 2 ×16
```

GPU utilization 可能很差。

---

### 更合理

全局 queue：

```text id="izderf"
P1-S1
P1-S2
...
P2-S1
P2-S2
...
```

Continuous batching。

---

### 但保留 Group Identity

每条 request：

```text id="40p2ip"
task_id
group_id
sample_index
policy_version
```

完成后 group assembler：

```text id="xhiwht"
collect same group
↓
reward
↓
advantage
```

---

### Long-tail 策略

设置：

```text id="5a4fd7"
timeout
max tokens
max steps
```

再明确：

> incomplete sample 的 algorithm semantics。

---

### Prefix Optimization

同 prompt group：

```text id="3zc9cz"
共享巨大 prompt
```

尽量让 prefix cache 命中。

---

### Load Balance

但不能为了 cache：

> 全部 16 条挤到同一 GPU。

所以 route：

$$
f(
prefix\ hit,
queue,
KV\ capacity
)
$$

---

### 最终系统

```text id="8jjqxu"
Prompt Producer
      ↓
Rollout Router
      ↓
┌────────┬────────┬────────┐
│ Engine │ Engine │ Engine │
└────────┴────────┴────────┘
      ↓
Trace Collector
      ↓
Group Assembler
      ↓
Reward
      ↓
Trainer
```

---

## 9.42 vLLM / SGLang 与 Trainer 为什么应该解耦？ `[P2]`

不推荐：

```text id="c0l8hh"
Agent code
直接调用
某个 Trainer 内部 generate()
```

---

### 更合理

```text id="0y059e"
Agent Harness
      ↓
Rollout Interface
      ↓
vLLM / SGLang
      ↓
Training-ready Trace
      ↓
Trainer Adapter
```

---

### 好处一：Serving Engine 可换

```text id="7yy446"
vLLM
↔
SGLang
```

不重写 Agent。

---

### 好处二：Trainer 可换

```text id="hw840f"
custom
↔
verl
```

---

### 好处三：Eval / Train 复用 Agent

同一个：

```text id="oq44pg"
Search Agent runtime
```

既能：

```text id="3012uo"
evaluation
```

也能：

```text id="q7w7jf"
RL rollout
```

---

### 但是 Interface 必须够丰富

不能只：

```text id="yldfa7"
generate(prompt) -> text
```

而应支持：

```text id="d12f5v"
prompt IDs
response IDs
logprobs
seed
sampling params
weight version
finish reason
```

否则 abstraction 太薄，无法训练。

---

# 9E. vLLM 深入

## 9.43 vLLM 的核心系统链应该怎么理解？

不要把 vLLM 只记成：

> PagedAttention。

更完整：

```text id="wl8r8k"
Request
 ↓
Tokenizer
 ↓
Scheduler
 ↓
KV Cache Manager
 ↓
Model Runner
 ↓
Attention / GEMM Kernels
 ↓
Sampling
 ↓
Streaming Output
```

---

### Scheduler

决定：

```text id="8x0dfx"
谁这一轮运行
处理多少 tokens
```

---

### KV Manager

负责：

```text id="lcs32n"
allocate
free
share
cache
```

KV blocks。

---

### Model Runner

执行：

```text id="apg6co"
forward
```

---

### Sampler

从 logits：

```text id="ng71vu"
temperature
top-p
top-k
```

生成 token。

---

### Engine

反复：

```text id="hngnaw"
schedule
→ execute
→ update request states
```

直到 request 完成。

---

## 9.44 Prefix Cache 与 PagedAttention 是什么关系？ `[P1]`

PagedAttention：

> KV blocks 怎么物理管理。

Prefix Caching：

> 已经计算过的 blocks 能否被未来请求复用。

---

### 所以

```text id="47tnyv"
Paged KV Blocks
      ↓
Hash / Prefix Identity
      ↓
Reusable Prefix Cache
```

两者相关，但不是同一个东西。

---

### 没 Prefix Cache

PagedAttention 仍然有价值：

* 减少 fragmentation；
* dynamic allocation。

---

### 没 PagedAttention

理论上也能做 prefix caching，

只是 cache memory management 更难。

---

## 9.45 Preemption 为什么可能造成 Performance Cliff？ `[P1]`

当 KV 资源不足：

```text id="h47rav"
Request A preempt
↓
KV removed
```

之后：

```text id="yki5gv"
A resumes
↓
recompute prefix
```

---

### 如果频繁发生

```text id="67ecxt"
compute
↓
evict
↓
recompute
↓
evict
```

大量 GPU FLOPs 没有产生新 output tokens。

这就是 thrashing。

---

### 所以

```text id="re32af"
GPU utilization = 100%
```

也不一定说明系统健康。

应该看：

```text id="6xibxi"
useful output tokens/s
preemption count
recompute tokens
cache hit
```

---

# 9F. SGLang 深入

## 9.46 SGLang Model Gateway 在大规模 Rollout 中做什么？ `[P1]`

当前 SGLang 将 Model Gateway 推荐为大规模 RL rollout 的 control plane，强调：

* async non-blocking routing；
* cache-aware load balancing；
* rollout / reward server 的故障转移；
* 多轮 request 的动态 dispatch。

---

### 架构

```text id="uij1qr"
Trainer / Harness
       ↓
Model Gateway
       ↓
 ┌─────┼─────┐
 ↓     ↓     ↓
S1     S2    S3
```

---

### 为什么不是 Client 自己 Round-robin？

因为 client 不应该自己维护：

```text id="s76c0v"
server health
cache state
queue depth
retry
```

---

### RL 中还可能有

```text id="h18z2o"
Rollout Servers
Reward Servers
```

Gateway 把它们服务化、解耦。

---

## 9.47 SGLang Weight Update 为什么默认要 Flush Cache？ `[P1]`

原因和 9.29 一样。

如果：

$$
\theta_1
\rightarrow
\theta_2
$$

旧：

$$
KV_{\theta_1}
$$

不能作为：

$$
\theta_2
$$

的 cache。

所以当前 SGLang 的 from-disk / tensor / distributed weight-update API 都提供 cache flush 语义，并在相关路径默认 flush。

---

### 另外还有 CUDA Graph

权重布局、运行路径变化时：

> 是否需要 recapture graph

也是 RL refit 需要考虑的 execution concern。

---

## 9.48 Deterministic Inference 是否等于 True On-policy？ `[P2]`

不等于。

Deterministic inference 解决：

> rollout engine 自己不同 batch 下的数值漂移。

---

### True On-policy 还需要

Trainer 对相同：

```text id="r32so2"
weights
prompt
response token
```

计算出一致的：

$$
\log p
$$

---

### 如果 Trainer kernel 不同

仍有：

$$
\log p_{\text{rollout}}
\neq
\log p_{\text{train}}
$$

所以 SGLang 官方也明确说明，仅启用 deterministic inference 还不够；为了更严格的 on-policy 对齐，training engine 也需要使用匹配的 deterministic execution。

---

# 9.49 Serving 高频连环追问

## 第一组：基础指标

```text id="njsddz"
TTFT？
↓
TPOT？
↓
为什么长 prompt 主要影响 TTFT？
↓
长 context 为什么也影响 TPOT？
↓
throughput vs latency？
↓
为什么还看 P99？
```

---

## 第二组：KV

```text id="u05wl6"
KV Cache 是什么？
↓
为什么 GQA 省 KV？
↓
KV 显存怎么算？
↓
PagedAttention 做什么？
↓
Prefix Cache 又是什么？
↓
两个是同一个东西吗？
```

---

## 第三组：Scheduler

```text id="f82cc3"
Continuous Batching？
↓
为什么优于 static batch？
↓
Chunked Prefill？
↓
为什么长 prefill 会伤 decode？
↓
Preemption？
↓
为什么可能 thrashing？
```

---

## 第四组：Quantization

```text id="motg20"
INT4 Weight？
↓
FP8 Activation？
↓
KV Quantization？
↓
各自在省什么？
↓
为什么 storage 减半不代表 latency 减半？
```

---

## 第五组：RL Rollout

```text id="2hofcd"
Chat Serving 和 Rollout 区别？
↓
为什么 rollout 要 token ID / logprob？
↓
为什么频繁 weight update？
↓
update 后 prefix cache 怎么办？
↓
为什么 long-tail 会卡 GRPO？
```

---

## 第六组：SGLang

```text id="fn2ce1"
RadixAttention？
↓
sleep / wake？
↓
weight refit？
↓
disk / tensor / distributed？
↓
pause / continue？
↓
weight version 为什么能到 token level？
```

---

## 第七组：Determinism

```text id="edz704"
temperature=0 为什么还不一定 deterministic？
↓
dynamic batching？
↓
floating-point reduction？
↓
deterministic serving 后就严格 on-policy 吗？
↓
trainer kernel 还要不要匹配？
```

---

# 9.50 Self-test

## Self-test 1：KV Cache

若 context：

$$
T
$$

翻倍，

其他都不变：

$$
M_{KV}
$$

约：

$$
2\times
$$

不是：

$$
4\times
$$

因为 KV cache 对长度是线性。

---

## Self-test 2：Attention Compute

Prefill 中：

$$
T\rightarrow2T
$$

dense attention pair interactions 约：

$$
4\times
$$

和 KV memory 不同。

---

## Self-test 3：Prefix Cache

两个 requests：

```text id="o9clx7"
A:
[10K shared][500 unique]

B:
[10K shared][800 unique]
```

cache hit 后 B 不需要重新 prefill前 10K。

但 B 的 800 unique 和之后 decode 仍需计算。

---

## Self-test 4：Policy Refit

Policy：

$$
v1\rightarrow v2
$$

能否继续复用 v1 prefix KV？

一般不能。

因为 hidden/KV 依赖权重。

---

## Self-test 5：GRPO Long-tail

16 samples：

```text id="8exg8q"
15 × 10 s
1 × 100 s
```

如果同步 barrier：

group latency：

$$
100s
$$

而不是：

$$
\frac{15\times10+100}{16}
$$

训练 step 等的是 max，不是 mean。

---

# 9.51 推导题

## 推导题 1：KV Cache

若：

$$
L=40
$$

$$
H_{kv}=8
$$

$$
d_h=128
$$

$$
T=65536
$$

FP16/BF16：

$$
b=2
$$

则：

$$
M_{KV}
=
2\times40\times65536\times8\times128\times2
$$

计算量级，并解释为什么单条长 context 就可能占数 GiB。

---

## 推导题 2：Serving Latency

若：

$$
TTFT=800ms
$$

$$
TPOT=25ms
$$

输出：

$$
200
$$

tokens，

粗略：

$$
Latency
=
800
+
199\times25
$$

$$
=
5775ms
$$

即约：

$$
5.8s
$$

---

## 推导题 3：Cache Hit Value

共享 prefix：

$$
P=20K
$$

unique suffix：

$$
U=2K
$$

cache hit 后 prefill token compute 从：

$$
22K
$$

降到：

$$
2K
$$

理论避免约：

$$
90.9\%
$$

prompt token prefill。

但实际 wall-clock speedup 不会严格等于 11×，因为还有：

* scheduling；
* memory；
* decode；
* cache lookup。

---

# 9.52 Debug 题

## Debug 1：GPU Utilization 99%，但 Tokens/s 很低

检查：

```text id="1zrbd8"
preemption
recompute
very long prefill
small inefficient batches
memory bandwidth
kernel fallback
```

GPU 忙不代表都在做 useful decode。

---

## Debug 2：TTFT 突然变差，TPOT 基本没变

优先看：

```text id="alv4rj"
prompt lengths
prefill queue
prefix hit rate
chunked prefill
admission
```

而不是 decode kernel。

---

## Debug 3：TPOT P99 很差，但平均 TPOT 正常

可能：

```text id="f6nmzp"
large prefill periodically blocks decode
```

考虑：

* chunked prefill；
* disaggregated prefill；
* scheduler policy。

---

## Debug 4：RL Ratio 在 Optimizer 第一步就不是 1

检查：

```text id="oih60k"
rollout/trainer checkpoint
token IDs
chat template
logprob definition
kernel mismatch
quantization
sampling transformation
```

这是非常关键的 RL serving debug。

---

## Debug 5：Weight Refit 后输出开始异常

检查：

```text id="rhhyh6"
KV cache flushed?
prefix cache flushed?
all TP ranks updated?
weight version consistent?
CUDA graph stale?
```

---

## Debug 6：同 Seed，同 Prompt，偶尔生成不同 Token

检查：

```text id="l37ezu"
dynamic batching
kernel determinism
distributed reduction
sampling generator
backend version
```

Seed 不是全部。

---

# 9.53 系统设计题

## 系统设计题 1：设计一个大规模 Agent Rollout Pool

```text id="z7l574"
Task Queue
   ↓
Agent Harness
   ↓
Gateway
   ↓
┌────────┬────────┬────────┐
│Rollout1│Rollout2│Rollout3│
└────────┴────────┴────────┘
   ↓
Tool Environment
   ↓
Trace Store
   ↓
Reward Service
   ↓
Group Assembler
   ↓
Trainer
```

需要额外保存：

```text id="i59xzf"
request_id
trajectory_id
group_id
sample_index
policy_version
token IDs
old logprobs
```

---

## 系统设计题 2：训练与 Rollout 共用 GPU 怎么做？

一个周期：

```text id="au1ovx"
Rollout
↓
pause
↓
release KV / rollout memory
↓
Training
↓
update weights
↓
flush stale cache
↓
resume rollout engine
↓
next rollout
```

这就是 SGLang sleep/wake/refit 一类 RL integration 能力的典型使用场景。

---

## 系统设计题 3：训练与 Rollout 分 GPU 怎么做？

```text id="z4rwvw"
Training Pool
     ↓
weight broadcast
     ↓
Rollout Pool
```

选择：

```text id="m03mo6"
checkpoint/object storage
NCCL
IB
```

然后 rollout nodes：

```text id="7x8d7h"
atomic update
↓
cache invalidate
↓
version bump
```

---

# 9.54 vLLM / SGLang / RL 统一理解

不要背成：

```text id="a50x3r"
vLLM:
PagedAttention

SGLang:
RadixAttention
```

太浅。

应该形成：

| 层               | vLLM / SGLang 解决的问题  |
| --------------- | -------------------- |
| Model Execution | 高效 Forward           |
| KV              | Cache 管理             |
| Scheduler       | 请求怎样共用 GPU           |
| Prefix          | 重复 Context 如何复用      |
| Sampling        | Token 怎么产生           |
| Distributed     | 模型如何跨卡推理             |
| Routing         | 请求去哪个 replica        |
| RL Integration  | 权重如何更新、request 如何暂停  |
| Provenance      | 哪个 Policy 生成哪些 Token |

---

# 9.55 Macro 9 最小知识图

最终应形成：

```text id="f2xpu6"
                        Request
                           │
                           ↓
                        Queue
                           │
                           ↓
                    Admission Control
                           │
                           ↓
                       Scheduler
            ┌──────────────┼──────────────┐
            │                             │
         Prefill                        Decode
            │                             │
            ↓                             ↓
      Prompt Compute                One Token Step
            │                             │
            └──────────────┬──────────────┘
                           ↓
                       KV Cache
                           │
          ┌────────────────┼────────────────┐
          │                │                │
      Paging          Prefix Cache      Quantization
          │                │                │
          └────────────────┼────────────────┘
                           ↓
                        Sampling
                           ↓
                     Output Tokens
```

Production 侧：

```text id="tg4b7m"
Serving
  │
  ├── TTFT
  ├── TPOT
  ├── Throughput
  ├── P99
  ├── SLA
  ├── Cost
  └── Reliability
```

RL 侧：

```text id="wcgq0h"
Rollout Engine
      │
      ├── exact token IDs
      ├── old logprobs
      ├── sampling seed
      ├── policy version
      ├── deterministic execution
      ├── pause / continue
      └── weight refit
             │
             ↓
        Training Trace
```

最后需要真正记住三个边界：

```text id="j7ej12"
Serving Engine
≠
Trainer

KV Cache
≠
Model State independent of weights

Same Checkpoint
≠
Automatically identical logprobs across different runtimes
```

以及整个 Macro 9 最值得在 Agent RL 面试中说清楚的一句话：

> **在普通推理系统里，Serving Engine 只要尽可能快且正确地产生文本；在 RL Rollout 系统里，它还必须成为行为策略的可审计执行器——准确告诉 Trainer 哪个 Policy、在什么 Context、用什么 Sampling 条件生成了哪些 Token，以及这些 Token 的 Behavior Logprob 是多少。**

Macro 10 接下来会从：

```text id="4zn1zo"
单个 Rollout Engine
```

继续放大到：

```text id="fw0307"
多 GPU / 多节点

Trainer
Actor
Reference
Rollout
Reward
Weight Sync
Checkpoint
Resource Placement
```

也就是：

```text id="54rzpa"
Data Parallel / DDP
AllReduce / AllGather / ReduceScatter
ZeRO / FSDP
TP / PP / CP / SP / EP
NCCL
MFU
Network Topology
↓
verl
↓
rLLM
↓
完整 Agent RL Distributed System
```

这会把前面你特别要求补回来的**基础分布式训练**与实际 `verl / rLLM` 工具链完整接起来。

## 10. Distributed Training / verl / rLLM / Agent RL Systems

前九个 Macro 已经能描述一条单机意义上的 Agent RL 链：

```text
Task
 ↓
Agent
 ↓
Rollout Engine
 ↓
Trajectory
 ↓
Reward
 ↓
Advantage
 ↓
Policy Loss
 ↓
Optimizer
```

但真正把：

```text
7B / 32B / 70B / MoE
×
G 个 rollout
×
长 context
×
大量 prompts
```

跑起来之后，问题会立刻变成：

```text
模型单卡放不下怎么办？
Adam state 为什么吃掉几十 GB？
梯度怎么跨卡同步？
参数为什么还要 AllGather？
TP / PP / CP / SP / EP 到底分别切什么？
Pipeline Bubble 是什么？
为什么 GPU 越多反而可能 MFU 越低？
训练卡和 rollout 卡应该共用还是分离？
Actor / Reference / Rollout 分别放哪里？
Policy 更新以后怎样把权重同步给 vLLM / SGLang？
Rollout 慢于 Trainer 会发生什么？
Async RL 中的 stale trajectory 怎么处理？
Checkpoint 除了 model weights 还必须保存什么？
rLLM 和 verl 到底是不是竞争关系？
```

所以本章分成三个层次：

```text
Layer 1
Distributed Training Fundamentals
DDP / Collectives / ZeRO / FSDP / TP / PP / CP / SP / EP

Layer 2
Distributed Agent RL System
Actor / Reference / Rollout / Reward / Placement / Weight Sync / Async

Layer 3
Framework Mapping
verl
rLLM
vLLM / SGLang
Agent Harness
```

需要形成的最终系统图是：

```text
                    Agent Harness
                         │
                         ↓
                  Rollout Requests
                         │
                  Model Gateway
                         │
                         ↓
              vLLM / SGLang Cluster
                         │
                         ↓
                 Training Traces
                         │
                         ↓
                    Reward
                         │
                         ↓
                   Advantage
                         │
                         ↓
                 verl Trainer
                  /          \
            FSDP/FSDP2      Megatron
                  \          /
                         ↓
                   Optimizer Step
                         │
                         ↓
                    Weight Sync
                         │
                         └────────→ Rollout Cluster
```

当前 `verl` 官方文档明确支持 FSDP/FSDP2 与 Megatron-LM 作为训练 backend，同时支持 vLLM、SGLang 等 rollout backend；官方更推荐 FSDP/FSDP2 用于研究与原型，Megatron-LM 用于进一步扩展规模。

---

# 10.0 问题矩阵

| 编号    | 问题                                                          | 等级 |
| ----- | ----------------------------------------------------------- | -- |
| 10.1  | Data Parallelism 是什么？                                       | P0 |
| 10.2  | DDP 为什么需要 AllReduce Gradient？                               | P0 |
| 10.3  | AllReduce、AllGather、ReduceScatter 分别是什么？                    | P0 |
| 10.4  | 为什么 AllReduce 可以理解成 ReduceScatter + AllGather？              | P0 |
| 10.5  | ZeRO-1 / ZeRO-2 / ZeRO-3 分别 Shard 什么？                       | P0 |
| 10.6  | FSDP 与 ZeRO-3 是什么关系？                                        | P0 |
| 10.7  | Tensor Parallelism 到底切什么？                                   | P0 |
| 10.8  | Pipeline Parallelism 到底切什么？                                 | P0 |
| 10.9  | Sequence Parallelism 与 Context Parallelism 有什么区别？           | P0 |
| 10.10 | Expert Parallelism 是什么？                                     | P0 |
| 10.11 | NCCL 在分布式训练中做什么？                                            | P0 |
| 10.12 | MFU 是什么？                                                    | P0 |
| 10.13 | Gradient Synchronization 为什么可以与 Backward Overlap？           | P1 |
| 10.14 | FSDP Forward / Backward 的 AllGather / ReduceScatter 数据流是什么？ | P1 |
| 10.15 | FSDP 为什么节省显存却增加通信？                                          | P1 |
| 10.16 | ZeRO-2 与 ZeRO-3 怎么选？                                        | P1 |
| 10.17 | TP 的 Column Parallel / Row Parallel Linear 是怎么回事？           | P1 |
| 10.18 | Pipeline Bubble 是什么？                                        | P1 |
| 10.19 | 1F1B / Interleaved Pipeline 为什么能减少 Bubble？                  | P1 |
| 10.20 | SP 为什么通常和 TP 搭配？                                            | P1 |
| 10.21 | CP 为什么特别适合 Long Context？                                    | P1 |
| 10.22 | EP 为什么会引入 All-to-All？                                       | P1 |
| 10.23 | Communication–Computation Overlap 怎么做？                      | P1 |
| 10.24 | Network Topology 为什么影响并行策略？                                 | P1 |
| 10.25 | Checkpoint Sharding 为什么必须理解？                                | P1 |
| 10.26 | Elastic Training 难在哪里？                                      | P1 |
| 10.27 | 为什么更多 GPU 不一定训练更快？                                          | P2 |
| 10.28 | 怎样根据 Model Size / Sequence Length / Network 选并行策略？          | P2 |
| 10.29 | MoE 的 TP / EP / DP 应怎样组合？                                   | P2 |
| 10.30 | 怎样分析一个分布式 Training Step 的 Critical Path？                    | P2 |
| 10.31 | verl 到底是什么？                                                 | P0 |
| 10.32 | verl 中 Actor / Rollout / Reference 分别负责什么？                  | P0 |
| 10.33 | `actor_rollout_ref` 为什么经常放在一个配置树里？                          | P1 |
| 10.34 | verl 一轮 GRPO 的完整数据流是什么？                                     | P1 |
| 10.35 | old logprob、reference logprob、current logprob 分别在哪产生？       | P1 |
| 10.36 | Response Mask 如何进入 verl 的 Loss？                             | P1 |
| 10.37 | Reward Function 应该在哪里接入？                                    | P1 |
| 10.38 | Group Advantage 应该在哪个阶段计算？                                  | P1 |
| 10.39 | FSDP backend 与 Megatron backend 在 verl 中怎么选？                | P1 |
| 10.40 | Colocated、Disaggregated、Hybrid RL 系统有什么区别？                  | P1 |
| 10.41 | Trainer 与 Rollout 为什么需要 Weight Sync？                        | P1 |
| 10.42 | Weight Sync 有哪些实现路线？                                        | P1 |
| 10.43 | RL Checkpoint 为什么不只是 Model Checkpoint？                      | P1 |
| 10.44 | Fully Async RL 为什么可能提升吞吐？                                   | P1 |
| 10.45 | Async RL 的 Policy Staleness 怎么定义？                           | P1 |
| 10.46 | Partial Rollout 在 Async Training 里意味着什么？                    | P2 |
| 10.47 | Rollout 与 Optimizer Throughput 应怎样配平？                       | P2 |
| 10.48 | Resource Placement 应怎样设计？                                   | P2 |
| 10.49 | 为什么 Agent RL 的瓶颈经常不在 Trainer？                               | P2 |
| 10.50 | rLLM 到底解决什么？                                                | P0 |
| 10.51 | rLLM 与 verl 为什么不是竞争关系？                                      | P0 |
| 10.52 | Episode / Trajectory / Step 在 rLLM 中是什么？                    | P0 |
| 10.53 | Model Gateway 为什么是 rLLM 的关键组件？                              | P1 |
| 10.54 | 为什么“同一份 Agent Code 做 Eval 和 Train”很重要？                      | P1 |
| 10.55 | Arbitrary Harness 怎样变成 Training-ready Trace？                | P1 |
| 10.56 | Sandbox Lifecycle 为什么是 Agent RL 的一部分？                       | P1 |
| 10.57 | rLLM Backend Adapter 为什么有价值？                                | P1 |
| 10.58 | rLLM / verl / vLLM / SGLang / Agent Harness 的边界是什么？         | P1 |
| 10.59 | 如果接入一个 Search Agent Harness 到 rLLM + verl，你怎么设计？            | P2 |
| 10.60 | 如果从零搭建 Agent RL Stack，你会怎么分层？                               | P2 |

---

# 10A. Distributed Training Fundamentals

## 10.1 Data Parallelism 是什么？ `[P0]`

最基本的 Data Parallel：

```text
GPU 0:
full model θ
batch shard 0

GPU 1:
full model θ
batch shard 1

GPU 2:
full model θ
batch shard 2
```

每个 GPU：

> 模型完全相同，但处理不同数据。

---

### Forward

GPU \(i\)：

$$
L_i
=
L(
\theta,
B_i
)
$$

---

### Backward

得到 local gradient：

$$
g_i
=
\nabla_\theta L_i
$$

---

### 全局梯度

希望：

$$
g
=
\frac1N
\sum_{i=1}^{N}g_i
$$

然后每个 rank：

$$
\theta
\leftarrow
\theta-\eta g
$$

因此需要：

```text
Gradient Synchronization
```

---

### 显存问题

DP 中每卡都有完整：

```text
Parameters
Gradients
Optimizer states
```

所以模型本身如果单 GPU 放不下：

> 单纯增加 DP 卡数无济于事。

这就是后面 ZeRO / FSDP 的出发点。

---

## 10.2 DDP 为什么需要 AllReduce Gradient？ `[P0]`

如果 GPU 0：

$$
g_0
$$

GPU 1：

$$
g_1
$$

各自直接 optimizer.step：

```text
θ0 ← θ0 - ηg0
θ1 ← θ1 - ηg1
```

下一 step：

$$
\theta_0
\neq
\theta_1
$$

Data Parallel replicas 立刻分叉。

---

### DDP

在 optimizer step 前：

$$
g
=
\frac{
g_0+\cdots+g_{N-1}
}{N}
$$

然后每个 rank 都得到相同：

$$
g
$$

再更新。

PyTorch DDP 的基本模型就是每个 rank 保留完整 replica，并通过 gradient reduction 保持 replicas 同步；FSDP2 官方教程也直接用 DDP 的 gradient all-reduce 与 FSDP 的 sharded collectives 做对比。

---

### 注意

DDP 一般：

```text
不同 rank
处理不同 microbatch
```

所以它不是：

> 把同一个 sample 重复算 N 次。

---

## 10.3 AllReduce、AllGather、ReduceScatter 分别是什么？ `[P0]`

这是分布式训练最基本的三个 collective。

假设：

```text
Rank 0: [a0]
Rank 1: [a1]
Rank 2: [a2]
Rank 3: [a3]
```

---

### AllGather

每个 rank 最终都拿到所有 shards：

```text
[a0, a1, a2, a3]
```

即：

$$
\text{shards}
\rightarrow
\text{full tensor on every rank}
$$

典型场景：

> FSDP 在 layer compute 前把 sharded parameters 临时拼回来。

---

### ReduceScatter

先 Reduce：

$$
x_0+x_1+x_2+x_3
$$

再 Scatter 结果 shards。

最终每 rank 只保留 aggregate 的一部分。

典型：

> FSDP backward 后同步并 shard gradient。

---

### AllReduce

所有 rank 的 tensor：

```text
Reduce
+
每个 rank 得到完整结果
```

例如：

$$
g
=
g_0+g_1+g_2+g_3
$$

每个 rank 最终都有：

$$
g
$$

典型：

> DDP gradient sync。

---

### 记忆方式

```text
AllGather:
碎片 → 每人完整

ReduceScatter:
每人的完整贡献 → 聚合后每人一个碎片

AllReduce:
每人的贡献 → 聚合后每人完整
```

---

## 10.4 为什么 AllReduce 可以理解成 ReduceScatter + AllGather？ `[P0]`

目标：

$$
Y
=
\sum_iX_i
$$

每个 rank 最终都需要完整 \(Y\)。

可以：

### 第一步 ReduceScatter

将：

$$
\sum_iX_i
$$

计算后分成：

$$
Y_0,Y_1,\ldots,Y_{N-1}
$$

每 rank 得一块。

---

### 第二步 AllGather

再把：

$$
Y_i
$$

全部收集：

$$
[Y_0,\ldots,Y_{N-1}]
=
Y
$$

于是：

$$
AllReduce
\approx
ReduceScatter
+
AllGather
$$

这也是理解 FSDP 的一个重要入口：PyTorch 官方直接指出，可以把 FSDP 看成把 DDP 的 gradient all-reduce 分解成 reduce-scatter 与后续 parameter all-gather。

---

## 10.5 ZeRO-1 / ZeRO-2 / ZeRO-3 分别 Shard 什么？ `[P0]`

Data Parallel 中每个 GPU 重复存储：

```text
Parameters
Gradients
Optimizer States
```

ZeRO 就是逐步消除这些冗余。

DeepSpeed 当前官方定义仍是：

```text
Stage 1:
Optimizer state partitioning

Stage 2:
Optimizer + Gradient partitioning

Stage 3:
Optimizer + Gradient + Parameter partitioning
```

---

### ZeRO-1

Shard：

```text
Optimizer States
```

例如 Adam：

$$
m,v
$$

每 rank 只保存一部分。

Parameters / gradients：

> 仍完整复制。

---

### ZeRO-2

再 Shard：

```text
Gradients
```

所以：

```text
Optimizer shard
Gradient shard
Parameters replicated
```

---

### ZeRO-3

再 Shard：

```text
Parameters
```

变成：

```text
Parameters shard
Gradients shard
Optimizer shard
```

这时单卡不再需要持有完整模型参数。

---

### 内存直觉

若：

$$
N
$$

个 DP ranks，

理想均匀情况下：

```text
Optimizer state
Gradient
Parameter
```

对应被 shard 的部分每 rank 可以接近：

$$
1/N
$$

存储。

但运行时还有：

* 临时 all-gather；
* activation；
* communication buffer；

所以 peak memory 不是简单除 \(N\)。

---

## 10.6 FSDP 与 ZeRO-3 是什么关系？ `[P0]`

概念上非常接近。

ZeRO-3：

> shard parameters + gradients + optimizer states。

FSDP FULL_SHARD：

> 同样 shard parameters、gradients、optimizer states。

PyTorch FSDP 官方当前也明确描述 FULL_SHARD 为参数、梯度和 optimizer state 全 shard。

---

### 主要区别不应该回答成

```text
ZeRO-3 是 DeepSpeed
FSDP 是 PyTorch
```

虽然这是事实，但太浅。

更重要是：

> 它们的系统实现、parameter lifecycle、communication scheduling、state dict、offload、framework integration 不同。

---

### FSDP 的典型 lifecycle

平时：

```text
parameter shard
```

需要某 layer forward 时：

```text
AllGather
↓
full layer parameters
↓
compute
↓
reshard/free
```

backward：

```text
AllGather params
↓
backward
↓
ReduceScatter gradients
```

FSDP2 官方就是这样描述其执行过程。

---

## 10.7 Tensor Parallelism 到底切什么？ `[P0]`

DP：

> 切 batch。

TP：

> 切单个 layer 内部 tensor / matrix。

例如 Linear：

$$
Y=XW
$$

权重：

$$
W
$$

太大，一张 GPU 放不下。

可以把：

$$
W
=
[W_1,W_2]
$$

分到多个 GPU。

---

### Column Parallel

沿 output dimension 切：

$$
W
=
[W_1,W_2,\ldots,W_p]
$$

每 GPU 计算部分输出。

---

### Row Parallel

沿 input dimension 切：

$$
W
=
\begin{bmatrix}
W_1\\
W_2\\
\vdots
\end{bmatrix}
$$

每 GPU 处理输入的一部分，之后需要 reduction。

Megatron Core 当前将 TP 定义为在单 layer 内切分参数，并明确提供 column-parallel / row-parallel linear。

---

### 为什么 TP 通信频繁？

因为同一个 layer 的计算被多个 GPU 合作完成。

基本每层附近都可能需要：

```text
AllReduce
AllGather
ReduceScatter
```

所以 TP 特别依赖：

> 高带宽低延迟互联。

---

## 10.8 Pipeline Parallelism 到底切什么？ `[P0]`

PP 沿模型深度切。

例如 32 layers：

```text
GPU 0: Layers 0–7
GPU 1: Layers 8–15
GPU 2: Layers 16–23
GPU 3: Layers 24–31
```

数据依次流：

```text
Stage 0
  ↓ activations
Stage 1
  ↓
Stage 2
  ↓
Stage 3
```

Backward 相反。

---

### 和 TP 区别

TP：

```text
同一个 layer
跨多卡
```

PP：

```text
不同 layers
放不同卡
```

---

### 优点

每卡只持有部分 layers。

---

### 问题

Pipeline dependency 导致：

```text
Bubble
```

以及 stage imbalance。

Megatron Core 目前把 PP 定义为沿模型 depth 切 transformer layers，并支持 virtual/interleaved pipeline 减少 bubble。

---

## 10.9 Sequence Parallelism 与 Context Parallelism 有什么区别？ `[P0]`

这两个特别容易混。

---

### Sequence Parallelism

Megatron 中 SP 通常是 TP 的配套优化。

它把原本在 TP ranks 上重复存储/计算的一部分：

```text
LayerNorm
Dropout
其他 sequence-wise activation
```

沿 sequence 维 shard。

目的主要：

> 减少 activation redundancy。

Megatron 当前仍建议使用 TP 时启用 sequence parallel。

---

### Context Parallelism

CP 则更彻底。

直接把整个 sequence：

$$
T
$$

沿长度分到不同 GPU：

```text
GPU 0:
tokens 0 ... T/2

GPU 1:
tokens T/2 ... T
```

并让各模块在 shard 上运行。

---

### Attention 特殊

因为 Q token 仍然需要看到全 sequence 的 K/V。

所以 CP 需要跨 ranks 交换：

```text
K/V
```

Megatron 当前明确区分：SP 主要切 LayerNorm/Dropout 等 activation，而 CP 则切整个网络输入和所有 activation，只在 attention 处需要额外跨 sequence shard 通信。

---

### 用途

```text
SP:
降低 TP 场景 activation redundancy

CP:
解决超长 context activation / attention 分片
```

---

## 10.10 Expert Parallelism 是什么？ `[P0]`

MoE：

```text
Token
↓
Router
↓
选择少数 Experts
```

例如：

$$
64
$$

个 experts。

不可能每 GPU 全存一遍。

---

### EP

将不同 experts 放到不同 GPU：

```text
GPU 0:
Expert 0–7

GPU 1:
Expert 8–15
...
```

---

### Token Routing

如果 GPU 0 上 token 被路由到 GPU 3 的 expert：

需要：

```text
send token activation
→ GPU 3
→ expert compute
→ send output back
```

因此典型通信是：

```text
All-to-All
```

---

### 为什么 MoE 难？

不仅模型大。

还会出现：

```text
expert load imbalance
token routing
all-to-all traffic
```

Megatron Core 将 EP 作为独立并行轴，并建议 MoE 与 TP/PP/DP 组合；当前文档特别指出 TP+EP 时需要 sequence parallel。

---

## 10.11 NCCL 在分布式训练中做什么？ `[P0]`

NCCL：

> NVIDIA Collective Communications Library。

它为多 GPU 提供高性能：

```text
AllReduce
AllGather
ReduceScatter
Broadcast
All-to-All
Send/Recv
```

等通信。

---

### PyTorch

你写：

```python
dist.all_reduce(tensor)
```

底层 GPU backend 经常就是 NCCL。

---

### NCCL 不负责什么？

它不是：

* Trainer；
* Optimizer；
* parallelism strategy。

它更像：

> GPU distributed communication runtime。

---

### 为什么面试经常问？

因为：

```text
DDP
FSDP
TP
EP
```

最后都会落成通信 collective。

如果只会说：

> FSDP 更省显存。

但不知道：

```text
AllGather / ReduceScatter
```

发生在哪里，就很难分析性能。

---

## 10.12 MFU 是什么？ `[P0]`

MFU：

> Model FLOPs Utilization。

粗略：

$$
MFU
=
\frac{
\text{实际有效 Model FLOPs/s}
}{
\text{硬件理论峰值 FLOPs/s}
}
$$

---

### 它不是 GPU Utilization

`nvidia-smi`：

```text
GPU Utilization = 100%
```

不代表 MFU 高。

GPU 可能在：

```text
低效率 kernel
通信等待
memory-bound operation
recompute
```

---

### MFU 低可能因为

```text
microbatch 太小
communication 太多
pipeline bubble
data loader
CPU bottleneck
load imbalance
kernel inefficient
```

---

### 为什么 Agent RL 更麻烦？

Trainer MFU 很高：

```text
50%
```

但 Rollout GPU：

```text
20%
```

整个 RL system wall-clock 仍然差。

因此还要看：

> End-to-end system utilization。

---

# 10B. Distributed Training Deep Dive

## 10.13 Gradient Synchronization 为什么可以与 Backward Overlap？ `[P1]`

Backward：

```text
Layer N grad
↓
Layer N-1 grad
↓
...
```

当 Layer N gradient 已经算完：

> 不必等 Layer 0。

可以立即开始：

```text
AllReduce(bucket N)
```

同时 GPU 继续算：

```text
Layer N-1 backward
```

---

### 时间线

```text
Compute:
[Bwd L4][Bwd L3][Bwd L2][Bwd L1]

Comm:
        [AR G4]
               [AR G3]
                      [AR G2]
```

communication 被 backward compute 隐藏。

---

### Bucket

不是每个 parameter 单独 collective。

而是 accumulate：

```text
gradient bucket
```

达到一定大小再通信。

---

### Trade-off

Bucket 太大：

```text
通信启动太晚
overlap 少
```

太小：

```text
collective 启动次数多
latency overhead 高
```

---

## 10.14 FSDP Forward / Backward 的 AllGather / ReduceScatter 数据流是什么？ `[P1]`

这是 FSDP 面试必须能画的一题。

平时：

```text
Rank 0: W0 shard
Rank 1: W1 shard
Rank 2: W2 shard
Rank 3: W3 shard
```

---

### Forward

当前 layer compute 前：

```text
AllGather
```

每 rank 临时得到：

$$
W=[W_0,W_1,W_2,W_3]
$$

然后：

```text
Forward
```

之后可：

```text
Reshard / Free full W
```

---

### Backward

需要当前 layer 参数重新：

```text
AllGather
```

完成 backward。

得到 full gradient contribution 后：

```text
ReduceScatter
```

最终：

```text
Rank 0: grad shard 0
Rank 1: grad shard 1
...
```

---

### Optimizer

每 rank 只更新自己：

```text
parameter shard
```

以及对应：

```text
optimizer state shard
```

PyTorch FSDP2 当前就是在 forward/backward 前 all-gather parameter group，并在 backward 后 reduce-scatter gradient。

---

## 10.15 FSDP 为什么节省显存却增加通信？ `[P1]`

DDP：

```text
每 rank 始终有完整 parameters
```

不用每 layer 临时获取参数。

---

### FSDP

平时只存：

$$
1/N
$$

parameter shard。

但 compute 需要完整当前 layer。

因此：

```text
before compute:
AllGather

after compute:
free
```

每次 forward/backward 都引入额外通信。

---

### Trade-off

```text
Memory ↓
Communication ↑
```

---

### 为什么仍然值得？

如果：

```text
模型根本放不下
```

没有 FSDP：

> 训练不能运行。

其次通信可以通过：

```text
prefetch
comm-compute overlap
NVLink
```

部分隐藏。

---

## 10.16 ZeRO-2 与 ZeRO-3 怎么选？ `[P1]`

### ZeRO-2

Parameters replicated。

所以 forward/backward：

> 不需要每 layer all-gather parameter。

通信相对更少。

但 parameter memory：

$$
M_P
$$

每卡仍完整存在。

---

### ZeRO-3

Parameters 也 shard。

Memory 更省。

代价：

```text
parameter all-gather
```

显著增加。

---

### 判断

如果模型参数本身：

> 单卡仍能放下。

ZeRO-2 可能吞吐更好。

如果模型参数本身：

> 已经放不下。

就需要 ZeRO-3 / FSDP。

---

### 不要回答

> ZeRO-3 一定比 ZeRO-2 好。

它只是：

```text
更省 memory
但通信更多
```

---

## 10.17 TP 的 Column Parallel / Row Parallel Linear 是怎么回事？ `[P1]`

考虑：

$$
Y=XW
$$

---

### Column Parallel

沿 output features 切：

$$
W=
[W_1,W_2]
$$

各 GPU：

$$
Y_i=XW_i
$$

最后：

$$
Y=
[Y_1,Y_2]
$$

如果下一层能直接接受 sharded output：

> 不一定立即 AllGather。

---

### Row Parallel

沿 input features 切：

$$
X=
[X_1,X_2]
$$

$$
W=
\begin{bmatrix}
W_1\\
W_2
\end{bmatrix}
$$

每 GPU：

$$
Y_i=X_iW_i
$$

最终：

$$
Y=\sum_iY_i
$$

需要：

```text
AllReduce / ReduceScatter
```

---

### Transformer 为什么容易这么切？

MLP：

$$
d
\rightarrow
4d
\rightarrow
d
$$

两个 Linear 可以设计成：

```text
Column Parallel
↓
activation
↓
Row Parallel
```

减少中间 communication。

Attention QKV/O projection 也可以类似组织。

---

## 10.18 Pipeline Bubble 是什么？ `[P1]`

4 个 stages：

```text
S0
S1
S2
S3
```

如果只处理一个 microbatch：

```text
time →
S0 [F]
S1     [F]
S2         [F]
S3             [F]
```

前面的 stages 很快 idle。

---

### 多 Microbatch Pipeline

```text
M1
M2
M3
M4
```

逐步把 pipeline 填满。

但：

* 开头 fill；
* 结尾 drain；

期间仍有 GPU idle。

这部分就是 bubble。

---

### 粗略

Pipeline stages：

$$
P
$$

microbatches：

$$
M
$$

如果 \(M\) 不够大：

> bubble ratio 高。

---

### 所以

增大 microbatch count：

```text
bubble ↓
```

但也影响：

* activation；
* batch size；
* optimizer semantics。

---

## 10.19 1F1B / Interleaved Pipeline 为什么能减少 Bubble？ `[P1]`

### GPipe 类

先：

```text
所有 Forward
```

再：

```text
所有 Backward
```

activation 保存多，bubble 也明显。

---

### 1F1B

pipeline warmup 后交替：

```text
1 Forward
1 Backward
```

减少 activation peak，并改善 pipeline utilization。

---

### Virtual Pipeline / Interleaving

一个物理 GPU 不只负责一个连续 stage，而负责多个：

```text
virtual pipeline stages
```

让调度更加细粒度。

Megatron 当前通过 `virtual_pipeline_model_parallel_size` 支持 interleaved pipeline，明确目的是降低 pipeline bubble。

---

## 10.20 SP 为什么通常和 TP 搭配？ `[P1]`

TP 切 Linear，但一些 operation：

```text
LayerNorm
Dropout
Residual
```

可能仍在每 TP rank 上持有相同 sequence activation。

形成冗余。

---

### Sequence Parallel

沿：

$$
sequence
$$

把这些 activation shard。

例如：

```text
Rank 0:
tokens 0–511

Rank 1:
tokens 512–1023
```

然后必要时：

```text
AllGather
ReduceScatter
```

Megatron 当前实现中，SP 相关层会在 forward all-gather、backward reduce-scatter。

---

## 10.21 CP 为什么特别适合 Long Context？ `[P1]`

长序列主要增加：

```text
activation memory
attention work
```

如果：

$$
T=128K
$$

即使模型参数不大，activation 也可能 OOM。

---

### CP

$$
T
$$

分成 \(C\) 份：

$$
T/C
$$

每 rank 只处理一段 sequence。

---

### Memory

activation per GPU 可以大致下降：

$$
\sim 1/C
$$

量级。

Megatron 官方当前明确说明 CP 可以按 CP degree 减少 per-GPU activation footprint，并用于长 context。

---

### 为什么 Attention 仍需通信？

GPU 0 的 Q：

> 需要和 GPU 1 上 token 的 K/V attention。

所以必须进行：

```text
KV exchange
```

可能通过：

* P2P；
* AllGather；
* all-to-all-like pattern；

具体取决于实现。

---

## 10.22 EP 为什么会引入 All-to-All？ `[P1]`

假设：

```text
GPU 0:
Experts 0–3

GPU 1:
Experts 4–7
```

GPU 0 上的某 token：

```text
Router → Expert 5
```

那 activation 必须发送 GPU 1。

---

### Routing Phase

每个 GPU 都可能有 token 去别的 GPU。

所以自然是：

```text
All-to-All
```

---

### Return Phase

Expert output 又需要回到原 token 所属 sequence/rank。

再次通信。

---

### 性能瓶颈

如果 router 极不均衡：

```text
Expert 2:
40% tokens

其他 experts:
~8%
```

Expert 2 对应 GPU 会成为 straggler。

---

## 10.23 Communication–Computation Overlap 怎么做？ `[P1]`

核心不是：

> 减少 communication 本身。

而是：

> 让 communication 在 GPU 正在做别的 compute 时运行。

---

### DDP

```text
Backward layer i
同时
AllReduce layer i+1 gradient
```

---

### FSDP

```text
Compute layer i
同时
AllGather layer i+1 params
```

以及：

```text
Backward compute
同时
ReduceScatter previous gradients
```

PyTorch FSDP2 当前明确提供 parameter prefetch，并把 AllGather 与 ReduceScatter 放在独立 CUDA streams 做 overlap。

---

### Megatron

也有：

```text
overlap-grad-reduce
overlap-param-gather
tp-comm-overlap
```

等机制。

---

### Overlap 的条件

Compute 时间必须足够长：

$$
T_{\text{compute}}
\ge
T_{\text{comm}}
$$

否则通信仍然露出来。

---

## 10.24 Network Topology 为什么影响并行策略？ `[P1]`

不同互联带宽差异巨大：

```text
same GPU:
HBM

same node:
NVLink / NVSwitch

cross node:
InfiniBand / RoCE
```

---

### TP

通信频率很高。

每 layer 都有 collective。

因此通常更适合：

```text
同节点高速 NVLink
```

---

### DP/FSDP

通信粒度相对大，可以更容易跨节点。

---

### PP

stage 之间主要发送 activation。

可以把：

```text
一个 stage
```

放在一个 node 内，再跨 node 做 P2P。

---

### EP

All-to-All 对网络 topology 非常敏感。

---

### 所以

不是：

```text
64 GPUs
```

就足够决定配置。

还要知道：

```text
8 GPUs/node?
NVLink?
IB bandwidth?
cross-rack?
```

---

## 10.25 Checkpoint Sharding 为什么必须理解？ `[P1]`

FSDP / TP / PP 后：

> 每个 rank 持有的模型状态不同。

如果每次保存时：

```text
gather full 70B model to rank 0
```

可能：

* rank 0 OOM；
* network bottleneck；
* save 时间极长。

---

### Sharded Checkpoint

每个 rank 保存：

```text
its local parameter shard
optimizer shard
```

外加：

```text
metadata
```

---

### 恢复时

需要保证：

```text
world size
parallelism layout
parameter mapping
```

能正确恢复或 reshard。

---

### RL Checkpoint 更复杂

因为还要保存：

```text
policy
optimizer
scheduler
global step
reference identity
rollout state
sampler state
```

后面 10.43 展开。

---

## 10.26 Elastic Training 难在哪里？ `[P1]`

Elastic training 希望：

```text
8 GPUs
↓
某卡挂了
↓
7/8 卡重组
```

或者训练过程中：

```text
8 → 16 GPUs
```

---

### 问题

World size 改变会影响：

```text
DP shards
FSDP shards
sampler
global batch
optimizer state placement
collective groups
```

---

### RL 更麻烦

还有：

```text
rollout replicas
policy version
unfinished trajectories
```

如果 rollout worker 还在生成旧 policy：

> 集群恢复后的训练数据如何处理？

---

### Elastic != Restart

真正 elastic 要保证：

> 统计语义和训练状态在资源变化后仍可恢复。

---

# 10C. Distributed System Design

## 10.27 为什么更多 GPU 不一定训练更快？ `[P2]`

假设：

$$
T_1
$$

单 GPU step 时间。

理想：

$$
T_N=\frac{T_1}{N}
$$

现实不是。

---

### 通信比例上升

模型计算 per GPU：

$$
\downarrow
$$

但：

```text
collective latency
```

不同比例下降。

---

### Strong Scaling Limit

固定 global problem size，GPU 越多：

```text
每 GPU compute ↓
communication / launch overhead 占比 ↑
```

---

### TP 特别明显

TP=8：

每 GPU matrix 变小。

可能：

```text
Tensor Core utilization ↓
collective ↑
```

---

### PP

stages 增加：

```text
bubble ↑
```

---

### EP

network all-to-all 可能成为瓶颈。

---

### 最终

$$
Speedup(N)
<
N
$$

甚至：

$$
Speedup(N+1)
<
Speedup(N)
$$

---

## 10.28 怎样根据 Model Size / Sequence Length / Network 选并行策略？ `[P2]`

可以使用一个实用决策树。

---

### Step 1：单卡能放下训练状态吗？

能：

```text
DP / DDP
```

先从最简单开始。

Megatron 当前官方 parallelism guide 也明确建议从 DP 开始，再按具体瓶颈增加其他 parallel axes。

---

### 参数/optimizer 太大

加：

```text
FSDP / ZeRO
```

---

### 单个 Layer 太大

即使 FSDP 临时 AllGather，一个 layer 仍塞不下：

```text
TP
```

---

### 模型非常深

加：

```text
PP
```

---

### Sequence 超长

activation OOM：

```text
CP
```

---

### MoE

experts 太多：

```text
EP
```

---

### 网络约束

高频通信轴：

```text
TP / EP
```

尽量放在高带宽域。

---

### 一个抽象配置

$$
WorldSize
=
DP
\times
TP
\times
PP
\times
CP
$$

MoE 时再考虑 EP grid。

Megatron 当前文档也用类似 product 表达总 GPU 数，并给出 TP/PP/CP/EP 的组合建议。

---

## 10.29 MoE 的 TP / EP / DP 应怎样组合？ `[P2]`

MoE 有两类参数：

```text
Dense/shared parameters
Experts
```

---

### EP

切 experts。

---

### TP

每个 expert 自身如果仍很大：

> expert 内继续 tensor parallel。

---

### DP

复制整个 expert partition group，对不同 batch shards 训练。

---

### 难点

Router 导致：

```text
每个 batch
不同 expert token 数
```

计算负载动态变化。

---

### 一个性能目标

不仅要：

```text
memory fit
```

还要：

```text
expert load balanced
all-to-all not saturated
```

---

### 为什么 topology 更关键？

Expert routing：

> Token 可能频繁跨设备。

如果 EP 横跨慢网：

> all-to-all 可能直接压垮 throughput。

---

## 10.30 怎样分析一个分布式 Training Step 的 Critical Path？ `[P2]`

不要只看总：

```text
step time = 8s
```

拆：

```text
Data
↓
Forward
↓
Backward
↓
Communication
↓
Optimizer
```

---

### Timeline

例如：

```text
0–2s Forward
2–6s Backward
   └─ 3–5.5s communication overlapped
6–7s exposed AllReduce
7–8s optimizer
```

虽然 collective 总时间：

$$
3.5s
$$

真正增加 wall-clock 的 exposed communication：

$$
1s
$$

---

### 所以 Profiling 应看

```text
compute kernel
NCCL kernel
overlap
idle gap
CPU dispatch
```

---

### Critical Path

只有不能被其他工作隐藏的部分：

> 真正决定 step wall-clock。

因此：

```text
communication bytes
```

大，不代表：

> 通信一定是瓶颈。

---

# 10D. verl Fundamentals

## 10.31 verl 到底是什么？ `[P0]`

可以把 verl 理解为：

> 面向大模型 post-training / RL 的分布式训练与数据流系统。

它负责把：

```text
Rollout
Reward
Logprob
Advantage
Actor Update
Reference
Checkpoint
Weight Sync
```

组织起来。

当前 verl 支持 FSDP/FSDP2 与 Megatron-LM 作为训练后端，并支持 vLLM、SGLang 等生成 backend。

---

### 它不是

```text
Search Agent Harness
```

也不是：

```text
Inference Engine
```

---

### 分层

```text
Search Agent
→ verl 不负责你的 Search / Visit 业务逻辑

vLLM/SGLang
→ verl 可以调用它们做 rollout

FSDP/Megatron
→ verl 可以用它们做 distributed update
```

---

## 10.32 verl 中 Actor / Rollout / Reference 分别负责什么？ `[P0]`

### Actor

正在训练的 policy：

$$
\pi_\theta
$$

负责：

```text
current logprob
policy loss
optimizer update
```

---

### Rollout

负责实际：

```text
generate trajectories
```

通常使用当前或近期 Actor weights。

Backend：

```text
vLLM
SGLang
```

---

### Reference

固定 reference policy：

$$
\pi_{\text{ref}}
$$

用于：

```text
KL regularization
```

---

### 三者逻辑身份不同

即使物理上可能：

```text
共享同一份权重 memory
```

或者 co-located，

语义上仍必须区分。

---

## 10.33 `actor_rollout_ref` 为什么经常放在一个配置树里？ `[P1]`

这容易让初学者误解：

> Actor、Rollout、Ref 是一个模型。

不是。

更合理理解：

> 它们通常来自同一 base architecture/checkpoint family，而且资源生命周期高度耦合，所以被统一配置。

---

### Actor

可训练。

---

### Rollout

Actor 的 serving/execution incarnation。

需要频繁同步 Actor weights。

---

### Ref

通常由初始 policy copy 而来并冻结。

---

### 共同配置

例如：

```text
model path
tokenizer
architecture
```

可以共享。

但：

```text
optimizer
rollout backend
reference freeze
```

各自不同。

---

## 10.34 verl 一轮 GRPO 的完整数据流是什么？ `[P1]`

可以记成：

```text
Batch Prompts
     ↓
Rollout
     ↓
G responses / prompt
     ↓
Reward Function
     ↓
Rewards
     ↓
Group Advantage
     ↓
Old Logprobs
Reference Logprobs
Current Logprobs
     ↓
Policy Loss
     ↓
Backward
     ↓
Optimizer
     ↓
Weight Sync
     ↓
Next Rollout
```

---

### 更具体

```text
Prompt Batch
↓
actor_rollout_ref.rollout
↓
Response token IDs
↓
Reward
↓
Advantage
↓
actor forward
↓
current logprob
↓
ratio
↓
loss
↓
update_actor
↓
update rollout weights
```

当前 verl 的 rollout config 也直接包含：

```text
sampling
rollout engine
async mode
GPU placement
```

等配置。

---

## 10.35 old logprob、reference logprob、current logprob 分别在哪产生？ `[P1]`

### old logprob

对应：

> behavior policy 生成 rollout 时的 action probability。

理想情况下由：

```text
rollout phase
```

生成/记录。

---

### current logprob

训练当前 policy：

$$
\pi_\theta
$$

对同一 response tokens 重新 forward。

---

### reference logprob

固定：

$$
\pi_{\text{ref}}
$$

对同一 tokens 打分。

---

### 用途

```text
current - old
→ importance ratio

current - ref
→ KL
```

---

### 不能混

如果拿：

```text
reference logprob
```

做 PPO denominator：

> 算法直接变了。

---

## 10.36 Response Mask 如何进入 verl 的 Loss？ `[P1]`

Agent trajectory：

```text
Prompt
Action
Observation
Action
```

只有 Action token：

```text
response_mask = 1
```

其他：

```text
0
```

---

### Policy Loss

$$
L
=
\frac{
\sum_t
m_t
L_t
}{
\sum_tm_t
}
$$

其中：

$$
m_t=response\_mask_t
$$

---

### KL / Entropy

也必须只在：

> 真正 policy-generated tokens

上计算，除非算法明确另有定义。

---

### 为什么 Step ID 仍有价值？

Response Mask 只告诉：

```text
是不是 policy token
```

Step ID 告诉：

```text
属于哪个 generation/turn
```

后续 stepwise credit 才能映射。

---

## 10.37 Reward Function 应该在哪里接入？ `[P1]`

通用数据流：

```text
Rollout
↓
Trajectory
↓
Evaluator / Reward Function
↓
Reward
↓
Advantage
```

Reward 不应该嵌进：

```text
inference engine
```

内部。

---

### 为什么解耦？

同一 rollout 可以换：

```text
Exact Match
Unit Test
LLM Judge
CW credit
```

而不重跑 model generation。

---

### Agent 场景

Reward function 可能读取：

```text
final answer
tool trace
citations
environment status
```

所以通常位于：

```text
Harness / Evaluation layer
```

比 serving layer 更合适。

---

## 10.38 Group Advantage 应该在哪个阶段计算？ `[P1]`

必须先有：

```text
同一个 prompt
G 个完整 reward
```

才能计算：

$$
\mu_G,\sigma_G
$$

---

### 因此

```text
individual rollout finishes
```

还不能马上得到完整 GRPO group advantage。

需要：

```text
Group Assembly
```

---

### Async 困难

Group 中：

```text
15 个完成
1 个没完成
```

你要决定：

* 等；
* timeout；
* partial group；
* substitute sample。

这些都是 algorithm semantics。

---

## 10.39 FSDP backend 与 Megatron backend 在 verl 中怎么选？ `[P1]`

当前 verl 官方建议：

```text
FSDP / FSDP2
→ research / prototype / flexibility

Megatron
→ better scalability
```

---

### FSDP 优势

* Hugging Face model integration 更自然；
* 修改算法方便；
* 原型门槛低。

当前 verl 的 FSDP 扩展文档也明确强调，它直接使用 Hugging Face model implementations；只要 `transformers` 与 rollout backend 都支持对应模型，通常无需复制整套 model code。

---

### Megatron 优势

大规模：

```text
TP
PP
CP
EP
```

成熟组合。

更容易扩展极大 dense / MoE 模型。

---

### 代价

模型支持和 engine integration 更复杂。

---

## 10.40 Colocated、Disaggregated、Hybrid RL 系统有什么区别？ `[P1]`

### Colocated

Trainer 与 Rollout 共用 GPU。

时间上轮流：

```text
Rollout
↓
free/sleep
↓
Train
↓
wake/refit
↓
Rollout
```

---

### 优点

GPU 数量少时：

> 资源利用灵活。

---

### 问题

Memory lifecycle 很复杂。

---

### Disaggregated

独立：

```text
Training Pool
Rollout Pool
```

同时运行。

---

### 优点

pipeline overlap：

```text
rollout generation
同时
trainer update
```

吞吐更高。

---

### 问题

* weight sync；
* policy staleness；
* 额外 network；
* 更多 GPUs。

---

### Hybrid

某些组件 colocated，某些分离。

例如：

```text
Actor Trainer + Ref
same pool

Rollout
separate pool
```

---

### 当前 verl

其 rollout 配置已经显式支持独立 rollout nodes，并且 fully async 路线区分 trainer 与 rollout 资源。

---

## 10.41 Trainer 与 Rollout 为什么需要 Weight Sync？ `[P1]`

Trainer 更新：

$$
\theta_t
\rightarrow
\theta_{t+1}
$$

Rollout server 如果仍然用：

$$
\theta_t
$$

下一批 trajectory 就来自 old policy。

---

### 同步系统

```text
optimizer.step()
↓
export updated weights
↓
rollout refit
↓
new policy version
↓
generate
```

---

### 如果不更新

staleness：

$$
k
=
version_{\text{current}}
-
version_{\text{rollout}}
$$

不断增加。

---

## 10.42 Weight Sync 有哪些实现路线？ `[P1]`

### Checkpoint / Disk

```text
Trainer
↓
save
↓
Rollout load
```

简单但慢。

---

### Host Memory

CPU staging。

---

### Direct Tensor Transfer

co-located：

```text
Trainer GPU memory
→ Rollout runtime
```

---

### NCCL / RDMA / NIXL

跨 GPU/node 直接通信。

---

### 关键 trade-off

```text
implementation simplicity
vs
sync latency
vs
memory
```

---

### 当前 verl

其 FSDP worker 可以把 parameter tensor stream 导出给 rollout weight update；近期版本也持续优化 weight-sync 和不同 quantized rollout path。

---

## 10.43 RL Checkpoint 为什么不只是 Model Checkpoint？ `[P1]`

真正 resume：

> 不只是恢复参数。

至少包括：

```text
Actor weights
Optimizer states
LR scheduler
Global step
RNG states
Sampler state
Reference identity
Training config
Dataset position
```

---

### Agent RL 还可能包括

```text
rollout policy version
experience repository
curriculum state
environment version
reward version
async queue state
```

---

### 如果只恢复 Model Weights

会出现：

```text
LR 从头开始
Adam moments 丢失
data 重复
rollout version 对不上
```

不能称严格 resume。

---

## 10.44 Fully Async RL 为什么可能提升吞吐？ `[P1]`

同步：

```text
Rollout batch
↓
WAIT
↓
Train
↓
WAIT
↓
next rollout
```

Rollout 和 Trainer 互相 idle。

---

### Async

```text
Rollout Pool:
v10 ─────────────→
     v11 ─────────────→

Trainer:
    update
       update
          update
```

两边 pipeline 化。

---

### 好处

```text
GPU idle ↓
throughput ↑
```

---

### 代价

trajectory 可能来自旧 policy。

当前 verl 已有 fully async training 路线，并显式配置：

```text
staleness_threshold
trigger_parameter_sync_step
partial_rollout
```

等参数。

---

## 10.45 Async RL 的 Policy Staleness 怎么定义？ `[P1]`

最直观：

$$
S
=
v_{\text{current}}
-
v_{\text{behavior}}
$$

例如：

```text
trajectory generated by v100
trainer now v104
```

则：

$$
S=4
$$

---

### 但 Version Gap 不等于 Distribution Gap

四个很小更新：

> 可能仍很接近。

一次巨大 update：

> 可能 version gap=1 就很远。

---

### 更算法意义的指标

```text
KL(current || behavior)
ratio distribution
clip fraction
```

---

### 所以 Staleness Control 可以基于

```text
step lag
time lag
KL
```

不同 proxy。

---

# 10E. verl Deep Water

## 10.46 Partial Rollout 在 Async Training 里意味着什么？ `[P2]`

假设 Agent 正在：

```text
Turn 0
Turn 1
Turn 2
...
```

Trainer 不想等整条 trajectory。

如果 `partial_rollout`：

> 未完成 trajectory 可以在 async pipeline 中被暂停/保留，并在后续继续。

verl 当前 fully async 配置已经暴露 `partial_rollout` 开关。

---

### 问题一：Reward

Outcome reward 尚未出现。

所以 partial prefix：

> 不能直接做 vanilla outcome GRPO update。

---

### 问题二：Policy Version

继续 generation 时 policy 可能已经更新。

于是：

```text
Turn 0: v10
Turn 1: v10
Turn 2: v12
```

---

### 问题三：Credit

最终：

$$
R
$$

应该怎样分配给跨 version trajectory？

---

### 所以 Partial Rollout

不是简单系统 trick。

它会直接改变：

```text
behavior-policy definition
trajectory unit
credit unit
```

---

## 10.47 Rollout 与 Optimizer Throughput 应怎样配平？ `[P2]`

定义：

$$
R
=
\text{rollout tokens/s}
$$

Trainer：

$$
T
=
\text{training tokens/s}
$$

---

### 如果：

$$
R\ll T
$$

Trainer 经常等数据。

瓶颈：

```text
Rollout
```

---

### 如果：

$$
R\gg T
$$

trajectory queue 增长。

数据越来越 stale。

瓶颈：

```text
Trainer
```

---

### 理想

在允许 staleness 范围内：

$$
R\approx T_{\text{consumption}}
$$

---

### 解决

Rollout 慢：

```text
more rollout GPUs
shorter generation
better serving
async tools
```

Trainer 慢：

```text
more trainer GPUs
better sharding
fewer PPO epochs
larger batch
kernel optimization
```

---

### 不能只优化单边峰值

如果 Rollout 快 2×：

> Trainer 完全没变，end-to-end 可能没有任何收益。

---

## 10.48 Resource Placement 应怎样设计？ `[P2]`

组件：

```text
Actor Trainer
Reference
Rollout
Reward Model
Tool Environment
```

都有资源需求。

---

### Actor

GPU-heavy：

```text
forward
backward
optimizer
```

---

### Reference

只 forward。

可以：

```text
GPU
CPU offload
shared weights
```

视规模决定。

---

### Rollout

需要：

```text
weights
KV cache
high concurrency
```

---

### Reward Model

如果 learned RM：

> 也可能单独吃 GPU。

---

### Tool Environment

Search / sandbox：

> 更多是 CPU / network / external API。

---

### Placement 目标

不是：

> 每个服务都平均分 GPU。

而是最小化：

$$
EndToEndStepTime
$$

---

## 10.49 为什么 Agent RL 的瓶颈经常不在 Trainer？ `[P2]`

普通 LM RL：

```text
prompt
→ generation
```

rollout 已经很贵。

Agent RL：

```text
generation
→ tool
→ wait
→ generation
→ browser
→ wait
...
```

---

### 可能 bottleneck

```text
LLM rollout
Search API
Sandbox startup
Browser
Reward Judge
Group straggler
```

---

### Trainer 可能只占

```text
20%
```

wall-clock。

即使训练 kernel 快 2×：

总系统只改善：

$$
\frac1{0.8+0.2/2}
\approx1.11\times
$$

这是 Amdahl's Law。

---

### 所以 Agent RL Profiling

必须做：

```text
rollout time
tool time
reward time
training time
weight-sync time
idle time
```

而不是只报：

```text
trainer MFU
```

---

# 10F. rLLM Fundamentals

## 10.50 rLLM 到底解决什么？ `[P0]`

rLLM 的定位可以压缩成：

> **把已有 Agent Harness 无侵入地变成可以进行 RL 的 Agent。**

当前 rLLM 自己的表述就是：

> Agentic RL on any harness, with any backend, on any benchmark.

它的核心 pipeline 是：

```text
Your Agent
↓
Traces
↓
Rewards
↓
RL Update
```

并通过 model gateway 自动捕获 LLM 调用的 token IDs 与 logprobs。

---

### 它想解决的痛点

传统做法：

```text
先写 Agent
↓
为了 RL
重写成 Trainer 特殊接口
```

rLLM 希望：

```text
Agent Code
基本保持不变
↓
Model Gateway 捕获轨迹
↓
Transform
↓
Trainer Backend
```

---

## 10.51 rLLM 与 verl 为什么不是竞争关系？ `[P0]`

这是必须秒答。

```text
rLLM
更靠上层
```

解决：

```text
Harness
Agent execution
Trace capture
Environment/Sandbox
Reward integration
```

---

```text
verl
更靠下层
```

解决：

```text
Distributed rollout/training
Policy update
FSDP/Megatron
vLLM/SGLang
```

---

### 当前 rLLM

本身就支持：

```text
backend = verl
```

以及其他后端。其 README 当前列出的 backend 包括 verl、Tinker 和 Fireworks。

---

### 所以

```text
rLLM
↓ uses
verl
```

完全合理。

不是：

```text
rLLM vs verl
谁赢？
```

---

## 10.52 Episode / Trajectory / Step 在 rLLM 中是什么？ `[P0]`

当前 rLLM 定义：

```text
Episode
= one task

Trajectory
= one agent run

Step
= one LLM call
```

Model Gateway 捕获 LLM calls 后，将它们组织成这样的层级。

---

### 例子

Task：

```text
Find X's university.
```

Episode：

```text
这个 task 的整个训练/eval 单元
```

---

### Group Rollout

同一 task：

```text
Trajectory 0
Trajectory 1
...
Trajectory 15
```

---

### 每个 Trajectory

```text
Step 0:
LLM decides Search

Step 1:
LLM sees result and searches again

Step 2:
LLM answers
```

---

### 与前面 Macro 5 对齐

```text
Step
≈ GenerationRecord / LLM generation
```

但具体框架字段仍要看实现。

---

## 10.53 Model Gateway 为什么是 rLLM 的关键组件？ `[P1]`

假设 Agent 原代码：

```python
client = OpenAI(
    base_url=config.base_url
)
```

平时 Eval：

```text
base_url
→ inference provider
```

Training：

```text
base_url
→ rLLM model gateway
```

---

### Gateway

拦截 LLM requests：

```text
messages
↓
model
↓
generation
```

并记录：

```text
token IDs
logprobs
session
step
```

rLLM 当前 README 明确说明，它通过 URL-routed session 的 model gateway 捕获 token IDs 和 logprobs，再构造 Episode / Trajectory / Step。

---

### 为什么这个设计聪明？

Agent 不需要知道：

> 我现在是不是在训练。

它仍然调用：

```text
OpenAI-compatible API
```

训练 instrumentation 发生在 gateway。

---

## 10.54 为什么“同一份 Agent Code 做 Eval 和 Train”很重要？ `[P1]`

如果：

```text
eval_agent.py
```

和：

```text
train_agent.py
```

是两套逻辑，很容易 drift。

例如：

```text
Eval:
max_steps=10

Train:
max_steps=5
```

或者：

```text
Eval parser strict
Train parser auto-repair
```

---

### 最危险

你训练的是：

> Agent A。

评估的是：

> Agent B。

---

### Shared Harness

```text
same Agent
same action protocol
same tools
same environment semantics
```

只替换：

```text
model endpoint
```

可以显著降低 train-eval mismatch。

rLLM 当前就把“same agent code drives both eval and training”作为架构目标。

---

## 10.55 Arbitrary Harness 怎样变成 Training-ready Trace？ `[P1]`

Agent Harness 本身可能是：

```text
LangGraph
OpenAI Agents SDK
CLI agent
Codex
Claude Code-like harness
custom Python
```

---

### rLLM 路径

```text
Harness
↓
OpenAI-compatible LLM request
↓
Model Gateway
↓
Capture exact generation
↓
Step
↓
Trajectory
↓
Episode
↓
Transform Pipeline
↓
Training Backend
```

当前 rLLM cookbook 甚至强调，不同 Agent framework 最终都可以把 LLM client 指向 `config.base_url`，由 Gateway 自动捕获 LLM calls，而无需每个 framework 单独写 tracing callback。

---

### Training-ready 的关键

Gateway 必须掌握：

```text
exact generated IDs
logprobs
request boundaries
session identity
```

否则最后只有 text：

> 仍然不足以做 PPO/GRPO。

---

## 10.56 Sandbox Lifecycle 为什么是 Agent RL 的一部分？ `[P1]`

Coding / terminal Agent：

```text
LLM
↓
bash
↓
filesystem
↓
tests
```

每个 rollout 必须有独立 environment。

---

### 需要

```text
create sandbox
reset
snapshot
execute
collect artifacts
destroy / recycle
```

---

### 如果不隔离

Trajectory A 修改：

```text
file.py
```

Trajectory B 继承这些修改。

结果：

```text
B 的 state
依赖 A
```

Rollouts 不再独立。

---

### Training Scale

假设：

```text
1024 concurrent agents
```

每次启动 Docker：

> startup cost 巨大。

所以需要：

```text
warm pool
snapshot
reuse
```

当前 rLLM 明确支持 Docker、Daytona、Modal 或 local sandbox，并强调 snapshot/warm-pool acceleration。

---

## 10.57 rLLM Backend Adapter 为什么有价值？ `[P1]`

Agent 逻辑：

```text
Search
Code
Browser
```

理论上不应该依赖：

```text
FSDP
Megatron
Cloud training API
```

---

### Backend Adapter

可以：

```text
rLLM Agent Trace
     ↓
verl
```

也可以：

```text
rLLM Agent Trace
     ↓
Tinker
```

---

### 好处

研究同一个算法时：

> 可以切换 infrastructure，而不重写 agent。

当前 rLLM 就把 backend abstraction 作为主要功能：同一 API 可切换 verl、Tinker、Fireworks。

---

## 10.58 rLLM / verl / vLLM / SGLang / Agent Harness 的边界是什么？ `[P1]`

这是整份八股最重要的系统边界之一。

```text
Agent Harness
负责：
任务逻辑
工具
搜索
状态机
动作协议
```

---

```text
rLLM
负责：
把任意 Harness 变成 RL workflow
trace capture
episode/trajectory/step
gateway
reward/backend glue
```

---

```text
verl
负责：
distributed RL dataflow
advantage
actor update
FSDP/Megatron
resource orchestration
weight sync
```

---

```text
vLLM / SGLang
负责：
高吞吐 inference / rollout
KV
scheduler
sampling
```

---

```text
FSDP / Megatron
负责：
distributed model training execution
```

---

### 图

```text
Search Harness
     ↓
rLLM
     ↓
verl
  ┌──┴──────────────┐
  ↓                 ↓
FSDP/Megatron    vLLM/SGLang
Training         Rollout
```

这张图面试必须能画。

---

# 10G. rLLM + verl Deep Dive

## 10.59 如果接入一个 Search Agent Harness 到 rLLM + verl，你怎么设计？ `[P2]`

假设 Harness 已经有：

```text
Task
Search
Visit
Answer
Trajectory
```

---

### 第 1 层：保留 Agent Runtime

不要为了 Trainer 改：

```text
Search policy logic
Action Parser
Environment
```

---

### 第 2 层：统一 Model Client

模型调用改为：

```python
OpenAI(
    base_url=config.base_url
)
```

---

### 第 3 层：rLLM Gateway

捕获每轮：

```text
prompt
token IDs
response IDs
old logprobs
```

形成：

```text
Step
```

---

### 第 4 层：Episode

同一 task：

```text
G Trajectories
```

用于 GRPO group。

---

### 第 5 层：Reward

Search Agent Evaluator：

```text
answer correctness
tool cost
optional process signal
```

---

### 第 6 层：Transform

转换成：

```text
response mask
step IDs
trajectory IDs
reward
advantage
```

---

### 第 7 层：verl

负责：

```text
Actor update
Reference logprob
distributed optimizer
```

---

### 第 8 层：Weight Sync

更新：

```text
Rollout backend
```

---

### 最终

```text
Search Agent
   ↓
rLLM Gateway
   ↓
Episode / Trajectory / Step
   ↓
Reward
   ↓
verl
   ↓
FSDP / Megatron
   ↓
Weight Update
   ↓
vLLM / SGLang
   ↓
next Search rollout
```

---

## 10.60 如果从零搭建 Agent RL Stack，你会怎么分层？ `[P2]`

不要写一个：

```text
train.py
3000 行
```

把所有东西塞一起。

至少分六层。

---

### Layer 1：Environment

```text
Task
Tool
Search
Browser
Sandbox
```

只负责：

> 外部世界。

---

### Layer 2：Agent Harness

```text
Policy call
Action parse
State
Termination
```

负责：

> Agent 怎样行动。

---

### Layer 3：Trace

```text
Episode
Trajectory
Generation / Step
Token provenance
Environment provenance
```

负责：

> 发生了什么。

---

### Layer 4：Evaluation / Credit

```text
Reward
Verifier
Judge
Advantage
Credit
```

负责：

> 应该怎样学习。

---

### Layer 5：Rollout Runtime

```text
vLLM
SGLang
Gateway
Scheduling
```

负责：

> 高效产生行为。

---

### Layer 6：Trainer

```text
verl
FSDP
Megatron
Optimizer
Checkpoint
Weight Sync
```

负责：

> 参数真正如何更新。

---

### 原则

```text
Harness
不能绑死 Trainer

Trainer
不能偷偷定义 Environment semantics

Serving
不能成为 Reward authority

Trace
必须跨这些边界保持 token truth
```

---

# 10H. Fully Async / On-policy Deep Water

## 10.61 Synchronous GRPO 为什么简单？ `[P1]`

最标准：

```text
Policy v10
   ↓
Freeze
   ↓
Generate all groups
   ↓
Reward
   ↓
Train
   ↓
Policy v11
```

所有 rollout：

$$
\tau_i
\sim
\pi_{v10}
$$

---

### 优势

Behavior policy 明确。

old logprob：

$$
\pi_{v10}
$$

没有 ambiguity。

---

### 缺点

Rollout 与 Training：

> 不能 overlap。

---

## 10.62 One-step-off 与 Fully Async 的差别是什么？ `[P2]`

可以粗略理解：

### Strict Sync

```text
policy k
→ rollout k
→ train k
→ policy k+1
```

---

### One-step-off

允许：

```text
trainer policy k+1
```

使用：

```text
policy k
```

近期 trajectory。

---

### Fully Async

rollout 和 trainer 独立推进。

trajectory lag：

$$
0,1,2,\ldots
$$

都有可能。

---

### 风险

随着 staleness：

$$
KL(
\pi_{\text{current}}
\|
\pi_{\text{behavior}}
)
\uparrow
$$

importance correction 越来越困难。

---

## 10.63 Async RL 为什么不只是“更快版同步 RL”？ `[P2]`

因为它改变了训练数据 distribution。

同步：

$$
\tau\sim\pi_{\theta_t}
$$

训练：

$$
\theta_t
$$

---

### Async

$$
\tau
\sim
\pi_{\theta_{t-k}}
$$

却更新：

$$
\theta_t
$$

所以算法变成：

> partially off-policy RL。

---

### 系统调度成为算法变量

如果 Search tool latency 很高：

```text
staleness ↑
```

所以：

> Web latency 最后竟然会影响 policy-gradient bias/variance。

这正是 Agent RL systems 的特色。

---

# 10I. Checkpoint / Failure / Recovery

## 10.64 分布式 Checkpoint 保存失败会怎样？ `[P1]`

假设：

```text
Rank 0 saved
Rank 1 saved
Rank 2 failed
Rank 3 saved
```

如果 checkpoint 没有 transactional semantics：

> 目录看起来存在，但无法恢复。

---

### 需要

```text
temporary checkpoint
↓
all ranks success
↓
manifest
↓
atomic commit / rename
```

---

### Manifest

记录：

```text
world size
parallelism
step
shards
hashes
```

---

## 10.65 Rollout Worker 崩了，GRPO Group 怎么办？ `[P2]`

同 prompt：

```text
G=8
```

完成：

```text
7
```

一条 worker crash。

---

### 方案 1：整个 Group Drop

统计最干净。

代价：

> 7 条 rollout 白算。

---

### 方案 2：Resample 第 8 条

需要保证：

```text
same behavior policy version
```

否则 group 内 samples 分布不同。

---

### 方案 3：Use G=7

Group statistics 改变。

训练 dynamic group size。

---

### 方案 4：Failure Sample 保留

如果 worker crash 是 infrastructure failure：

> 不应该变成负 reward。

---

### 关键

不能在系统实现中偷偷：

```python
except:
    continue
```

因为它隐式修改算法。

---

# 10J. Distributed Debug

## 10.66 多卡训练突然 Hang，应该怎么看？ `[P2]`

先想：

> Collective mismatch。

例如：

```text
Rank 0:
AllReduce A

Rank 1:
AllReduce B
```

各自等待不同 collective。

---

### 常见原因

```text
某 rank OOM
某 rank exception
unused parameter control flow 不一致
不同 tensor shape
process group 错
network failure
```

---

### Debug

```text
rank-specific logs
NCCL debug
collective timeout
torch distributed debug
```

先找：

> 最早离群 rank。

---

## 10.67 FSDP OOM 但参数已经 shard 了，为什么？ `[P2]`

可能：

```text
all-gather peak
```

虽然平时只有 parameter shard，

当前 layer compute 时：

> full parameter materialized。

---

### 还可能

```text
prefetch next layer
+
current layer full params
```

同时存在。

---

### 以及

```text
activations
gradients
communication buffers
```

所以：

```text
sharded parameter memory
```

不是 peak memory。

---

## 10.68 Scale 到 64 GPU 后 MFU 大跌，查什么？ `[P2]`

按：

```text
communication exposed?
microbatch too small?
TP too high?
PP bubble?
network topology?
CPU launch?
data loader?
EP imbalance?
```

逐项查。

---

### 特别看

```text
per-GPU matmul size
```

GPU 更多后矩阵变得太小：

> Tensor Core efficiency 下降。

---

# 10K. verl Debug

## 10.69 Rollout 很快，Trainer 很慢怎么办？ `[P1]`

Trajectory queue 越来越大：

```text
staleness ↑
```

---

### 可以

```text
减少 rollout replicas
增加 trainer GPUs
减少 PPO epochs
增加 trainer batch
优化 FSDP/TP
```

---

### 不要

只让 queue 无限堆。

因为：

> 更多 trajectory 最终可能因 stale 被丢弃。

---

## 10.70 Trainer 很快，Rollout 很慢怎么办？ `[P1]`

Trainer idle。

检查：

```text
model generation
tool latency
reward judge
max response
agent horizon
```

---

### 解决

```text
more rollout workers
better serving
async environment
parallel tools
shorter unnecessary reasoning
```

---

### Agent RL 中

最常见其实是：

> rollout / environment bottleneck。

---

## 10.71 Weight Sync 后 Reward 突然崩，怎么查？ `[P2]`

检查：

```text
all ranks weights consistent?
rollout cache flushed?
quantization refit correct?
tokenizer unchanged?
policy version bumped?
partial request mixed weights?
```

---

### 一个强 invariant

Weight sync 后用固定 prompt：

```text
Trainer model
Rollout model
```

比较 logits / greedy tokens。

如果完全不同：

> 先修系统，别调 RL 超参。

---

# 10L. rLLM Debug

## 10.72 Agent Eval 正常，rLLM Training Rollout 行为不同，查什么？ `[P2]`

第一优先：

```text
Gateway serialization
```

检查：

```text
chat template
messages
tool calls
special tokens
sampling config
```

---

### 因为

即使 Agent code 一样：

```text
Eval provider
```

和：

```text
Training gateway
```

也可能实际序列化不同。

---

### 再查

```text
environment
sandbox
model checkpoint
timeout
```

---

## 10.73 Gateway Capture 到的 Token IDs 对不上 Trainer 怎么办？ `[P2]`

这是 hard failure。

不能：

```text
重新 tokenize text
```

“修好”。

---

### 排查

```text
tokenizer version
chat template
backend-returned token IDs
BOS/EOS
tool special tokens
```

---

### 原则

如果：

$$
actual\ token\ provenance
$$

无法证明：

> 这条 trace 不应该进入 token-level RL。

---

# 10M. 高频连环追问

## 第一组：DDP / Collective

```text
Data Parallel？
↓
为什么梯度不同？
↓
怎么同步？
↓
AllReduce？
↓
ReduceScatter？
↓
AllGather？
↓
为什么 FSDP 能把 AllReduce 拆开？
```

---

## 第二组：ZeRO / FSDP

```text
ZeRO-1？
↓
ZeRO-2？
↓
ZeRO-3？
↓
FSDP 对应哪个？
↓
为什么 ZeRO-3 更省显存？
↓
为什么通信又更多？
```

---

## 第三组：Model Parallel

```text
TP 切什么？
↓
PP 切什么？
↓
SP？
↓
CP？
↓
EP？
↓
各自最主要 communication 是什么？
```

---

## 第四组：Topology

```text
为什么 TP 更喜欢 NVLink？
↓
为什么 EP 怕慢网络？
↓
PP 跨节点可不可以？
↓
DP 为什么比较适合跨节点？
```

---

## 第五组：verl

```text
verl 是什么？
↓
Actor / Rollout / Reference？
↓
FSDP vs Megatron？
↓
vLLM / SGLang 在哪？
↓
Reward 在哪？
↓
Weight sync 在哪？
```

---

## 第六组：Async

```text
为什么 fully async 快？
↓
为什么 stale？
↓
怎么定义 stale？
↓
旧 trajectory 怎么办？
↓
partial rollout 怎么办？
↓
还算 on-policy 吗？
```

---

## 第七组：rLLM

```text
rLLM 是什么？
↓
为什么还需要 verl？
↓
Model Gateway？
↓
Episode / Trajectory / Step？
↓
为什么 same code eval/train？
↓
sandbox 为什么是训练系统的一部分？
```

---

# 10N. Self-test

## Self-test 1：Global Batch

```text
DP = 8
micro batch per GPU = 2
gradient accumulation = 16
```

则：

$$
B_{\text{global}}
=
8\times2\times16
=
256
$$

TP / PP 通常：

> 不直接乘进 data batch 数。

因为它们合作计算同一 batch shard。

---

## Self-test 2：ZeRO

哪个 stage shard parameter？

```text
ZeRO-3
```

---

哪个 stage 只 shard optimizer？

```text
ZeRO-1
```

---

## Self-test 3：FSDP

Forward 前：

```text
AllGather parameters
```

Backward 后：

```text
ReduceScatter gradients
```

---

## Self-test 4：Parallelism

长 context OOM，但 parameters 本身能放下。

优先考虑：

```text
activation checkpointing
CP
```

而不是机械：

```text
加 PP
```

---

## Self-test 5：Agent RL

如果：

```text
Rollout = policy v10
Current = policy v14
```

即使 model architecture 一样：

> 不能叫 exact current-policy rollout。

---

# 10O. 推导题

## 推导题 1：DDP Gradient

全局 batch：

$$
B
=
\cup_iB_i
$$

若各 shard size 相同：

$$
L
=
\frac1N
\sum_iL_i
$$

则：

$$
\nabla L
=
\frac1N
\sum_i
\nabla L_i
$$

所以 gradient averaging 与 global batch gradient 一致。

---

## 推导题 2：ZeRO Memory

假设 parameter：

$$
P
$$

gradient：

$$
P
$$

Adam state：

$$
2P
$$

先忽略 dtype difference。

DDP 每卡：

$$
4P
$$

---

### ZeRO-1

$$
P
+
P
+
\frac{2P}{N}
$$

---

### ZeRO-2

$$
P
+
\frac{P}{N}
+
\frac{2P}{N}
$$

---

### ZeRO-3

$$
\frac{P}{N}
+
\frac{P}{N}
+
\frac{2P}{N}
=
\frac{4P}{N}
$$

这是理想稳态粗略模型，不包含 temporary all-gather。

---

## 推导题 3：Pipeline Bubble

如果 pipeline stages：

$$
P
$$

microbatches：

$$
M
$$

简单 GPipe 风格 bubble fraction 可粗略理解与：

$$
\frac{P-1}{M+P-1}
$$

同量级。

所以：

$$
M\gg P
$$

时 bubble 更小。

---

## 推导题 4：Async Staleness

若每：

$$
4
$$

optimizer steps 同步一次 rollout weights，

rollout 一条 trajectory 平均跨：

$$
3
$$

个 sync 周期才完成，

最大 policy lag 可能快速达到：

$$
O(12)
$$

steps 量级。

说明：

> `sync frequency`

不能独立于：

```text
trajectory latency
```

设计。

---

# 10P. System Design

## 系统设计题 1：8×H100 训练 7B GRPO 怎么配？

如果单机 8 卡：

```text
Actor:
FSDP2 / DP

Rollout:
colocated vLLM/SGLang
或
4 trainer + 4 rollout
```

取决于：

```text
memory
rollout/trainer ratio
```

---

### 原型优先

```text
FSDP2
```

因为：

* 代码简单；
* HF 兼容；
* 算法修改方便。

---

### 不一定需要

```text
TP / PP
```

如果 7B 本身已经能通过 FSDP 满足需求。

不要为了“高级”叠所有并行轴。

---

## 系统设计题 2：70B Agent RL，64 GPU 怎么想？

先估：

```text
training state memory
sequence
rollout concurrency
```

可能：

```text
Trainer:
TP × PP × DP
或 Megatron/FSDP hybrid

Rollout:
独立 TP serving replicas
```

---

### 更可能 Disaggregated

因为：

> 70B training 和 serving 同时 colocate 很难高效。

---

### Network

TP 尽量同 NVLink node。

DP 跨 node。

---

## 系统设计题 3：Search Agent Rollout 比纯 Math Rollout 慢 5× 怎么办？

不要先扩 Trainer。

拆：

```text
LLM generation
search latency
visit latency
reward
```

---

### Search I/O 占大头

增加：

```text
async tool concurrency
connection pooling
retrieval cache
local simulator
```

---

### LLM generation 占大头

扩：

```text
rollout engine replicas
```

---

### Group Barrier

加：

```text
straggler timeout
```

但明确训练 semantics。

---

# 10Q. Framework 对照表

| 层                    | 主要职责                                    | 代表组件                  |
| -------------------- | --------------------------------------- | --------------------- |
| Agent Logic          | Reason / Search / Tool / State          | TraceSearch Harness   |
| Agent-RL Abstraction | Harness → Trace → Reward → Trainer      | rLLM                  |
| Distributed RL       | Actor / Ref / Advantage / Update / Sync | verl                  |
| Training Backend     | Sharding / Model Parallel / Optimizer   | FSDP2 / Megatron      |
| Rollout Backend      | High-throughput generation              | vLLM / SGLang         |
| Communication        | GPU collectives                         | NCCL                  |
| Environment          | Search / Browser / Sandbox              | Custom / Docker / Web |
| Evaluator            | Verifier / Judge / Reward               | Custom                |

---

# 10R. `verl` 与 `rLLM` 的真正区别

不要回答：

> verl 更底层，rLLM 更上层。

这只是第一层。

更完整：

### verl 的中心对象

更接近：

```text
Tensor Batch
Worker
Actor
Rollout
Reference
Trainer
Resource Pool
```

---

### rLLM 的中心对象

更接近：

```text
Task
Episode
Trajectory
Step
Agent Harness
Model Gateway
Sandbox
Evaluator
```

---

### 二者交界

```text
Agent-native Trace
↓
Transform
↓
Training Batch
```

正是在这里连接。

---

### 当前 rLLM

其架构说明中也明确存在：

```text
Workflow Engine
Model Gateway
Transform Pipeline
Training Backend
```

其中 backend 可以直接选择 verl。

---

# 10S. 本章最重要的几条“不等式”

必须记住：

```text
DDP
≠
模型切分
```

它只是：

> Model Replica + Batch Shard。

---

```text
FSDP
≠
Tensor Parallel
```

FSDP：

> Data-parallel ranks 上 shard model states。

TP：

> 同一 layer computation 本身跨 GPU。

---

```text
Sequence Parallel
≠
Context Parallel
```

SP：

> 主要去掉 TP 下部分 activation duplication。

CP：

> 真正把整个长 sequence 分片。

---

```text
Rollout Engine
≠
RL Trainer
```

---

```text
rLLM
≠
verl
```

而更像：

```text
rLLM
can use
verl
```

---

```text
More GPUs
≠
Higher MFU
≠
Shorter End-to-End RL Time
```

---

```text
Trainer Throughput
≠
Agent RL Throughput
```

Agent RL 还受：

```text
Rollout
Tools
Environment
Reward
Straggler
Weight Sync
```

控制。

---

# 10T. 最小知识图

分布式训练：

```text
                         Training
                            │
             ┌──────────────┼──────────────┐
             │                             │
       Data Parallel                  Model Parallel
             │                             │
     ┌───────┴───────┐        ┌────────────┼────────────┐
     │               │        │            │            │
    DDP          FSDP/ZeRO    TP           PP           CP
                     │                                   │
              model-state shard                      long context
                                                     
                                  MoE
                                   │
                                   ↓
                                  EP
```

Collectives：

```text
DDP
→ AllReduce

FSDP
→ AllGather Parameters
→ ReduceScatter Gradients

TP
→ AllReduce / AllGather / ReduceScatter

PP
→ P2P Activation

CP
→ KV / Sequence Communication

EP
→ All-to-All
```

Agent RL：

```text
                         Agent Task
                             │
                             ↓
                         Harness
                             │
                             ↓
                           rLLM
                ┌────────────┼────────────┐
                │            │            │
             Gateway      Episode      Evaluator
                │            │            │
                └────────────┼────────────┘
                             ↓
                           verl
               ┌─────────────┴─────────────┐
               │                           │
            Rollout                     Trainer
               │                           │
        vLLM / SGLang              FSDP / Megatron
               │                           │
               └───────────┬───────────────┘
                           ↓
                     Weight Sync
                           ↓
                     Next Policy
```

---

# 10U. 最后一题：面试官让你画完整 Agent RL System

应该能从零画：

```text
                   Dataset / Curriculum
                           │
                           ↓
                       Task Queue
                           │
                           ↓
                     Agent Harness
                ┌──────────┼──────────┐
                │          │          │
             Search      Visit      Sandbox
                │          │          │
                └──────────┼──────────┘
                           │
                           ↓
                     Model Gateway
                           │
                           ↓
                Rollout Router / Pool
                           │
                   vLLM / SGLang
                           │
                           ↓
                  Generation Records
                           │
                           ↓
                      Trajectory
                           │
                 ┌─────────┴─────────┐
                 │                   │
             Verifier             Judge
                 │                   │
                 └─────────┬─────────┘
                           ↓
                         Reward
                           ↓
                     Credit Module
                           ↓
                       Advantage
                           ↓
                    Training Batch
                           ↓
                          verl
                           │
              ┌────────────┴────────────┐
              │                         │
            FSDP2                    Megatron
              │                         │
              └────────────┬────────────┘
                           ↓
                     Optimizer Step
                           ↓
                       Checkpoint
                           │
                           ↓
                      Weight Sync
                           │
                           ↓
                    Rollout Policy
```

然后解释五条 invariant：

```text
1. Harness 负责行为语义，不让 Trainer 偷偷重定义 Agent。

2. Gateway 必须保留 exact token / logprob provenance。

3. Reward 与 Credit 必须和 Execution Trace 解耦。

4. Trainer 与 Rollout 可以物理分离，但必须有明确 Policy Version。

5. Async 提升系统吞吐的同时，会把原本同步 on-policy RL 变成带 Staleness 的训练问题。
```

如果再被问：

> **那 rLLM、verl、vLLM / SGLang 三个到底是什么？**

可以直接回答：

```text
rLLM
把 Agent Harness 变成可训练的 RL Workflow。

verl
把 Training Trace 变成分布式 Policy Update。

vLLM / SGLang
高效执行 Rollout Policy。

FSDP / Megatron
负责真正的分布式 Forward / Backward / Optimizer。
```

这就是从：

```text
“我会调用一个 RL 框架”
```

到：

```text
“我知道 Agent RL 系统每一层的统计语义、数据边界和分布式执行路径”
```

之间真正的差距。
