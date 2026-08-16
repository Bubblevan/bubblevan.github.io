---
schema: bubblevan/v1
id: blog-20260815-cs336-a1-linear-embedding
content_kind: blog
title: CS336 A1 复盘二：Linear 与 Embedding
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 从 Transformer 最小的两个参数模块出发，复盘 Linear 与 Embedding 的 shape contract、参数布局、初始化和 checkpoint 语义，并进一步理解 vocabulary、weight tying 与现代 LLM 参数组织之间的关系。
topics: [CS336, PyTorch, Transformer, Linear, Embedding]
projects: [cs336]
aliases: []
authors: [bubblevan]
--------------------

Tokenizer 做完以后，文本已经从 Unicode string 变成了一串整数：

```text
"the cat"
    ↓ tokenizer
[127, 531, 82, ...]
```

但这些整数还不能直接拿去做 attention。

`127` 并没有天然比 `531` “更小”，两个 token ID 之间也没有欧氏距离、方向或者语义关系。它们首先只是 vocabulary 中两个不同位置的索引。

于是 Transformer 真正开始进行连续数值计算之前，需要完成：

```text
token ID
   ↓
Embedding lookup
   ↓
d_model 维向量
```

而这些向量进入模型之后，Q/K/V projection、attention output projection、SwiGLU 的三组权重以及最终 LM head，几乎又全部由另一种最基础的运算组成：

```text
Linear
```

所以 A1 把 `Linear` 和 `Embedding` 放在 Transformer 架构实现的最前面并不是凑两个简单题。

这两个模块已经提前暴露出后面会反复遇到的四个问题：

```text
1. tensor 的最后一维究竟代表什么？
2. 参数矩阵到底按照哪个方向存储？
3. 参数初始化如何影响模型刚开始训练时的数值尺度？
4. 一个看似数学等价的实现，为什么可能和 checkpoint 不兼容？
```

2026 年 CS336 的课程网站仍然把 A1 定义为从零实现 tokenizer、Transformer architecture、optimizer 和训练流程，而官方仓库通过 `tests/adapters.py` 把学生自己的实现接入统一测试。换句话说，A1 的目标不是“模仿 PyTorch API 写几个类”，而是自己掌握这些模块背后的 tensor contract。

---

# 1. Linear 其实是整个 Transformer 最常见的操作

神经网络教材里经常写：

[
y = Wx + b
]

A1 的 Linear 则更加简单：

[
y = Wx
]

没有 bias。

作业要求这一实现跟随 PyTorch `nn.Linear` 的接口，但去掉 bias，这也符合许多现代 decoder-only LLM 大量使用 bias-free projection 的设计。A1 handout 对 Linear 的要求就是实现：

[
y = Wx
]

同时显式说明不使用 bias。

最容易产生困惑的是：

```text
W 到底应该存成什么 shape？
```

A1 / PyTorch 的约定是：

```text
input:  [..., d_in]

weight: [d_out, d_in]

output: [..., d_out]
```

PyTorch 官方 `nn.Linear` 同样把 learnable weight 存为：

```text
[out_features, in_features]
```

而输入允许拥有任意数量的 leading dimensions，只要求最后一维等于 `in_features`。

这条规则后面几乎贯穿整个 Transformer。

---

# 2. 为什么代码里的 Linear 看起来和数学公式“反了”

这是第一次实现 Linear 时最容易卡住的地方。

数学教材通常把一个向量写成列向量：

[
x \in \mathbb{R}^{d_{\text{in}}}
]

然后：

[
W \in
\mathbb{R}^{d_{\text{out}}\times d_{\text{in}}}
]

因此：

[
Wx
\in
\mathbb{R}^{d_{\text{out}}}
]

完全没有问题。

但 PyTorch 里的 batch 通常把每一个 sample 放在 row 上。

例如：

```text
x.shape = [B, d_in]
```

于是代码中实际想算的是：

[
Y = XW^T
]

因为：

[
[B,d_{\text{in}}]
\times
[d_{\text{in}},d_{\text{out}}]
==============================

[B,d_{\text{out}}]
]

而参数本身存的是：

[
W:
[d_{\text{out}},d_{\text{in}}]
]

所以 forward 可以写成：

```python
x @ self.weight.T
```

也可以用 `einsum` 更直接表达：

```python
torch.einsum(
    "... d_in, d_out d_in -> ... d_out",
    x,
    weight,
)
```

这里有一个值得留下的认知：

> `weight.shape == [out, in]` 不是说运行时真的非要先把矩阵完整 transpose 一遍。

这是一个**参数布局和数学接口约定**。具体底层 GEMM 如何消费这个布局，是 kernel/library 的实现问题。

所以不要看到：

```python
weight.T
```

就理解成 Transformer 每跑一次 Linear 都在浪费时间复制一整块权重。

transpose 很多时候只是创建不同 stride/view，真正的矩阵乘 kernel 会按相应布局执行。

---

# 3. `...` 比 `[B, D]` 更重要

如果只拿普通 MLP 举例，我很容易把 Linear 写成：

```text
[B, D]
  ↓
[B, D']
```

但 Transformer 最常见的输入其实是：

```text
[B, T, D]
```

例如：

```text
batch_size = 8
seq_len = 512
d_model = 768
```

hidden states：

```text
[8, 512, 768]
```

经过：

```python
Linear(768, 3072)
```

以后应该直接得到：

```text
[8, 512, 3072]
```

并不是先手动 reshape：

```text
[B, T, D]
→ [B*T, D]
→ Linear
→ [B*T, D']
→ [B, T, D']
```

虽然这样数学上也能做，但 Linear 的正确 abstraction 应该直接支持：

```text
[..., d_in]
→
[..., d_out]
```

也就是说：

> Linear 只解释最后一维，其余维度全部保持原样。

PyTorch 官方接口也是这样定义的：输入可以拥有任意 leading dimensions，输出只替换最后一个 feature dimension。

这个约定后面会不断出现：

```text
RMSNorm      操作最后一维
Linear       替换最后一维
softmax      指定某一维
RoPE         操作 head_dim
attention    明确 sequence/head 维
```

所以第一次把 `...` 想清楚，比记住某个具体 shape 更重要。

---

# 4. Linear 在 Transformer 里到底出现了多少次

A1 之后再回头看整个 Transformer，会发现所谓“复杂架构”其实大量由 Linear 拼出来。

一个普通 attention block 里至少有：

```text
x
├── W_Q
├── W_K
├── W_V
└── W_O
```

对应：

[
Q = XW_Q^T
]

[
K = XW_K^T
]

[
V = XW_V^T
]

以及 attention 合并之后：

[
O = HW_O^T
]

SwiGLU 又通常包含三组 Linear：

```text
gate projection
up projection
down projection
```

最后模型还要有：

```text
LM head:
d_model → vocab_size
```

所以一层 Transformer 真正的大头并不是“attention 公式里那个 softmax”，而是大量 dense matrix multiplication。

这也是为什么后面 A2 Systems 会进一步关心：

```text
GEMM
kernel fusion
tensor parallel
communication
FlashAttention
```

A1 在这里先让自己实现 Linear，相当于先认识之后绝大多数 FLOPs 的基本单位。

---

# 5. 参数量也从 Linear 的 shape 开始算

一个：

```python
Linear(d_in, d_out)
```

没有 bias 时，参数量就是：

[
d_{\text{in}}d_{\text{out}}
]

例如：

```text
d_model = 4096
```

一个：

```text
4096 → 4096
```

projection 就有：

[
4096^2
======

16,777,216
]

约 16.8M 参数。

如果 attention 里：

```text
W_Q
W_K
W_V
W_O
```

全部都是：

```text
4096 × 4096
```

单层 attention projection 就已经有：

[
4\times4096^2
\approx 67.1M
]

参数。

这对理解后面的 GQA 很重要。

传统 MHA：

```text
Q heads = H
K heads = H
V heads = H
```

而 GQA 会减少 K/V heads。

因此 K/V projection 的输出维度可以降低：

```text
d_model
→
n_kv_heads × head_dim
```

Linear 本身没有变。

变的是：

```text
out_features
```

于是：

```text
参数量减少
KV cache 减少
memory bandwidth 降低
```

以后看到 Llama、Qwen、DeepSeek 里的：

```python
q_proj
k_proj
v_proj
o_proj
```

其实仍然是在讨论这一章最简单的东西。

---

# 6. Linear 为什么通常没有 bias

这里值得比原稿多讲一步。

经典：

```python
nn.Linear
```

默认拥有：

```text
weight + bias
```

但 A1 明确要求：

```text
bias = False
```

原因首先当然是 architecture contract：你实现的是课程指定的 Transformer，而不是自由设计网络。

不过从现代 LLM 的角度看，bias-free Linear 也非常常见。

对于一个大矩阵：

```text
[D_out, D_in]
```

bias 只有：

```text
[D_out]
```

所以取消 bias **几乎不是为了显著减少参数量**。

例如：

```text
4096 × 4096
```

权重有 1677 万个元素，而 bias 只有：

```text
4096
```

差别几乎可以忽略。

它更多是 architecture simplification：

```text
Linear(x) = xWᵀ
```

整个 block 的 affine shift 不再由每个 projection 独立提供。

所以这件事不能写成：

> “现代 LLM 去掉 bias 是为了省很多参数。”

省下来的参数实际上很少。

---

# 7. 从零实现 Linear，不是从零实现 GEMM

A1 禁止我直接：

```python
self.linear = nn.Linear(...)
```

但这不代表我要自己写：

```python
for b in batch:
    for i in out_features:
        for j in in_features:
            ...
```

这种 Python 三重循环。

课程要求“from scratch”的边界是：

```text
参数语义
module abstraction
tensor operations
architecture
```

由自己实现。

而真正底层数值运算仍然交给 PyTorch。

例如完全可以：

```python
return x @ self.weight.T
```

或者：

```python
return torch.einsum(...)
```

这里让我第一次比较明确地区分三个层次：

```text
architecture layer
    Linear

tensor operator layer
    matmul / einsum

kernel layer
    GEMM / CUDA kernel
```

A1 主要要求我掌握第一层和第二层。

A2 才会进一步逼我往第三层走。

这也是 CS336 整个课程结构很漂亮的地方：

```text
A1:
模型到底怎么算

A2:
这些计算在 GPU 上到底怎么跑
```

---

# 8. `nn.Parameter` 才让一个 Tensor 变成“模型权重”

如果只写：

```python
self.weight = torch.empty(...)
```

它只是一个普通 tensor。

而：

```python
self.weight = nn.Parameter(...)
```

注册到 `nn.Module` 后，它会进入模块的 parameter tree，随后才能自然地参与：

```python
model.parameters()

optimizer = AdamW(model.parameters())

model.state_dict()

model.to(device)

model.to(dtype)

checkpoint save/load
```

PyTorch 的 `nn.Module` 正是通过子模块和参数注册构成一棵 module tree。

这也是为什么 A1 允许使用：

```text
nn.Module
nn.Parameter
ModuleList
```

却不允许直接把 `nn.Linear` 等核心组件全部拿来拼起来。

课程不是想让我重新实现 autograd。

它想让我搞清楚：

> **哪些 tensor 是模型的状态。**

---

# 9. state dict contract 比“forward 数学正确”更严格

假设我自己偏偏喜欢把 Linear weight 存成：

```text
[d_in, d_out]
```

然后：

```python
return x @ weight
```

数学结果完全正确。

那么这个模块“错了吗”？

脱离上下文当然没有错。

但是放进 A1 就有问题。

因为官方 snapshot 可能提供：

```text
weight:
[d_out, d_in]
```

外部 checkpoint 也按照这个 convention 保存。

于是加载权重时就产生：

```text
expected [d_in, d_out]
got      [d_out, d_in]
```

必须额外 transpose。

更麻烦的是一个 Transformer 有几十乃至几百个：

```text
q_proj.weight
k_proj.weight
v_proj.weight
...
```

如果每个实现都有自己的 orientation，checkpoint interoperability 会立刻变成灾难。

因此：

```text
parameter name
parameter shape
dtype
storage semantics
```

都是模型接口的一部分。

这也是 snapshot test 比：

```python
assert output.shape == ...
```

严格很多的原因。

---

# 10. dtype 和 device 也属于 constructor contract

例如：

```python
Linear(
    in_features=768,
    out_features=3072,
    device="cuda",
    dtype=torch.bfloat16,
)
```

合理实现应该直接创建：

```text
CUDA bf16 parameter
```

而不是：

```text
先 CPU float32 创建
↓
之后再希望外层帮我搬过去
```

因此：

```python
nn.Parameter(
    torch.empty(
        out_features,
        in_features,
        device=device,
        dtype=dtype,
    )
)
```

比 constructor 里无视 `device/dtype` 更符合模块 abstraction。

这件事在 A1 规模下似乎无所谓。

但模型真的变成：

```text
几十 GB
几百 GB
```

后，parameter initialization 在哪里发生、以什么 dtype 创建，会影响：

```text
host RAM
GPU memory
temporary copies
distributed initialization
checkpoint loading
```

A1 的一个小参数因此已经在训练大模型真正需要的 API discipline。

---

# 11. 初始化为什么不是“随便给点随机数”

现在进入这一篇真正值得扩展的部分。

如果：

```python
weight = torch.randn(...)
```

当然模型也能 forward。

问题是训练刚开始时，每一层输出的 variance 会怎样变化？

考虑：

[
y_i =
\sum_{j=1}^{d_{\text{in}}}
W_{ij}x_j
]

粗略假设：

```text
x_j independent
W_ij independent
E[W] = 0
```

那么：

[
\mathrm{Var}(y)
\approx
d_{\text{in}}
\mathrm{Var}(W)
\mathrm{Var}(x)
]

如果：

```text
Var(W)
```

太大：

```text
一层
↓
activation variance 变大
↓
几十层
↓
可能爆炸
```

如果太小：

```text
signal 不断衰减
```

所以 Xavier、Kaiming 等 initialization 的核心都不是“随机化”这么简单，而是在试图控制：

```text
forward signal scale
backward gradient scale
```

---

# 12. A1 的 Linear 初始化到底是什么

A1 的 Linear 不应该直接照搬 PyTorch `nn.Linear` 默认初始化。

作业要求采用课程指定的截断正态初始化。

对应 Linear：

[
\sigma
======

\sqrt{
\frac{2}
{d_{\text{in}}+d_{\text{out}}}
}
]

然后：

```python
nn.init.trunc_normal_(
    weight,
    mean=0.0,
    std=std,
    a=-3 * std,
    b=3 * std,
)
```

也就是在类 Xavier 的尺度上使用 ±3σ 截断。公开的 A1 实现复盘和 handout 摘录都对应这一设置。

这里：

[
\sqrt{
\frac{2}{fan_{in}+fan_{out}}
}
]

正是在兼顾：

```text
fan_in
fan_out
```

两端的 variance propagation。

对于：

```text
d_in = d_out = D
```

就变成：

[
\sigma
======

\frac{1}{\sqrt D}
]

所以随着 hidden size 增大，单个 weight 的初始 magnitude 会相应变小。

---

# 13. 为什么还要 truncation

普通 Gaussian：

[
W\sim\mathcal N(0,\sigma^2)
]

理论上可以产生任意大的 outlier。

虽然概率非常低，但一个拥有几十亿参数的模型会抽样几十亿次。

因此：

```text
很小的 tail probability
×
海量参数
```

不一定意味着实际永远遇不到极端值。

truncated normal：

```text
[-3σ, +3σ]
```

会把极端 tail 去掉。

A1 的目的当然不是让我们深入讨论所有 initialization theory，但这个实现细节本身值得记录：

```python
trunc_normal_(..., a=-3 * std, b=3 * std)
```

和：

```python
trunc_normal_(..., std=std)
```

并不完全是同一件事。

后者的默认 truncation bound 是绝对值范围，而不是自动理解成“±3 个 std”。

---

# 14. 初始化为什么到现代 LLM 仍然没有变成无关问题

一个容易产生的误解是：

```text
有 RMSNorm
有 residual
有 AdamW
→ 初始化已经不重要
```

A1 handout 自己就指出，pre-norm Transformer 的确对初始化相对 robust，但 initialization 仍然会显著影响训练速度和 convergence。

现代深层网络更麻烦的一点在于 residual accumulation。

非常粗略地想：

```text
x₀
↓
x₁ = x₀ + f₁(x₀)
↓
x₂ = x₁ + f₂(x₁)
↓
...
↓
x_L
```

即使每个 residual branch 单独都比较合理，几十层、上百层不断累加以后，variance dynamics 依然需要控制。

因此现代模型会看到各种：

```text
scaled initialization
residual scaling
depth-dependent scaling
μP
DeepNorm
specialized parameterization
```

它们解决的都是同一类根问题：

> 模型宽度和深度变化后，怎样保持训练 dynamics 可控？

A1 现在只让我实现最朴素的一套方案，但后面 Architecture Lab 如果开始自己造 mini-Llama / mini-Qwen，就不能把 initialization 当成无关变量。

---

# 15. 为什么架构对比一定要控制初始化

假设我做两个实验：

```text
Model A:
MHA + 原初始化

Model B:
GQA + 另一套初始化
```

最后 B loss 更低。

能得出：

```text
GQA 更好
```

吗？

不能。

因为一次改了两个东西：

```text
attention architecture
initial parameter distribution
```

更严重的是小模型实验的 variance 本来就可能比较大。

所以以后我自己做 architecture ablation 时，应该尽量：

```text
same tokenizer
same dataset
same parameter budget
same training tokens
same optimizer
same LR schedule
same initialization
same random seeds / 多 seed
```

然后只改变一个因素。

这也是为什么 baseline 阶段严格照 handout 初始化反而是一件好事：

```text
先建立 reference point
再做 architecture experiments
```

---

# 16. Embedding 到底是什么

Tokenizer 输出：

```text
[B, T]
```

例如：

```python
token_ids = [
    [12, 88, 5],
    [43, 12, 91],
]
```

但 token ID 只是 category index。

Embedding 保存一个：

[
E
\in
\mathbb R^{V\times D}
]

其中：

```text
V = vocabulary size
D = d_model
```

例如：

```text
V = 32,000
D = 768
```

那么：

```text
embedding.weight:
[32000, 768]
```

输入：

```text
[B, T]
```

输出：

```text
[B, T, D]
```

PyTorch `Embedding` 官方定义也正是一个 lookup table：

```text
weight:
[num_embeddings, embedding_dim]
```

而输入可以是任意 shape 的整数 index tensor，输出会在最后追加 embedding dimension。

---

# 17. Embedding 不是在“计算 token ID”

假设：

```text
token_id = 57
```

Embedding 做的并不是：

[
57W
]

而只是：

```python
weight[57]
```

取第 57 行。

因此：

```python
Embedding(V, D)
```

本质可以理解成：

```text
V 行
每行一个 D 维可学习向量
```

例如：

```text
token 0   → E[0]
token 1   → E[1]
...
token 57  → E[57]
...
```

所以相同 ID 无论出现在哪里：

```text
token_ids[0, 3] = 57
token_ids[7, 91] = 57
```

在进入 Transformer 之前都会先得到：

```text
同一个 E[57]
```

位置差异并不是 token embedding 自己编码的。

A1 后面用 RoPE 把 position information 注入 attention，而不是直接让 embedding row 随位置变化。

---

# 18. Embedding 与 one-hot × Linear 的数学等价

这是我认为这一章很值得保留的一个理解。

假设 vocabulary size：

```text
V = 5
```

token ID：

```text
2
```

写成 one-hot：

[
x =
[0,0,1,0,0]
]

embedding matrix：

[
E
\in
\mathbb{R}^{V\times D}
]

那么：

[
xE
]

得到的就是：

[
E_2
]

也就是 embedding matrix 第 2 行。

因此数学上：

```text
Embedding lookup
```

等价于：

```text
one-hot vector
×
embedding matrix
```

但真正实现绝对不应该构造 one-hot。

因为假设：

```text
V = 150,000
```

每一个 token 都创建：

```text
150000 维向量
```

其中只有一个位置是 1：

```text
99.999% 都是 0
```

完全没有必要。

lookup 直接：

```python
weight[token_ids]
```

就能拿到同样结果。

于是 embedding 是一个非常典型的例子：

> 数学等价，并不意味着计算实现也应该一样。

这个思想后面在 attention、softmax、cross-entropy 和 FlashAttention 里会不断重现。

---

# 19. Embedding 的输入 dtype：整数，不是浮点数

因为：

```python
weight[token_ids]
```

本质是在做索引，所以 token IDs 必须是整数 tensor。

这里我会修正原稿的一句话。

不要写：

> 输入必须是 LongTensor。

当前 PyTorch 文档给出的 Embedding 输入可以是：

```text
IntTensor
或
LongTensor
```

关键条件是：

```text
integer indices
```

而不是某一种固定 bit width。

这也是 token ID 和 hidden state 的一个非常清晰的边界：

```text
Tokenizer output:
integer IDs

Embedding output:
floating-point vectors
```

从这里开始，Transformer 主体才进入：

```text
fp32 / fp16 / bf16
```

世界。

---

# 20. Embedding 初始化和 Linear 也不完全一样

A1 同样要求 Embedding 使用课程指定的 truncated normal 初始化，而不是直接依赖 `nn.Embedding` 默认 initialization。公开 handout 摘录也明确要求自行初始化 Embedding。

Embedding 和 Linear 在数学角色上不同：

```text
Linear:
把已有连续表示映射到另一个空间

Embedding:
直接定义每一个离散 token 的初始连续表示
```

训练 step 0 时：

```text
"cat"
"dog"
"the"
"for"
```

并没有任何语言学意义上的向量关系。

它们只是来自某个随机分布的不同 row。

经过大量 next-token prediction 训练以后：

```text
哪些 token 出现在相似 context
哪些 token 对输出预测承担类似作用
```

才逐渐塑造这个 embedding space。

所以：

> Embedding 不是一个预先编码了词义的字典，而是语言模型共同训练出来的参数。

---

# 21. 为什么现在通常不需要 Word2Vec/GloVe 来初始化 LLM embedding

以前 NLP 很自然的想法是：

```text
我已经有 Word2Vec / GloVe
↓
为什么不拿它初始化 embedding？
```

但现代大规模 Transformer pretraining 通常从随机 embedding 开始。

其中一个原因是整个模型会通过 language modeling objective 联合学习自己的 token representation，而 tokenizer 又往往是 subword/byte-level 的，和传统 word embedding 的 vocabulary 本身都未必对应。

2024 年一项专门研究 Transformer embedding initialization 的工作也发现：简单把一些预训练 embedding 搬过来不一定比随机初始化更好，embedding 的初始分布尺度以及它与位置表示之间的相互作用都会影响训练；在某些情况下，重新标准化这些 embedding 才能恢复效果。

这再次说明：

```text
“有预训练信息”
```

并不自动等于：

```text
“是更好的初始化”
```

initialization distribution 本身就是训练 dynamics 的一部分。

---

# 22. Vocabulary size 为什么会直接进入模型参数量

上一章 BPE 已经提到：

```text
vocab size
```

不是一个 tokenizer 独立参数。

现在到了 Embedding 就可以直接看到原因。

Embedding 参数：

[
P_{\text{embed}}
================

V D
]

例如：

```text
D = 768
```

使用：

```text
V = 10K
```

得到：

[
10,000\times768
===============

7.68M
]

参数。

如果换成：

```text
V = 32K
```

则：

[
32,000\times768
===============

24.576M
]

多出将近：

```text
17M parameters
```

对于一个 100M 左右的小模型，这已经是非常大的差别。

所以比较：

```text
TinyStories 10K tokenizer
```

与：

```text
OpenWebText 32K tokenizer
```

时，即使 Transformer block 完全一样：

```text
model parameter count
```

也不会一样。

---

# 23. LM head：Embedding 的反方向问题

输入端做：

```text
token ID
↓
D-dimensional vector
```

模型经过若干 Transformer blocks 后得到：

```text
hidden:
[B, T, D]
```

最后语言模型必须回答：

```text
下一个 token 是 vocabulary 中哪一个？
```

所以需要：

```text
Linear(D, V)
```

把 hidden state 投影回 vocabulary space：

```text
[B, T, D]
→
[B, T, V]
```

得到每一个 token 的：

```text
logit
```

这层通常叫：

```text
LM head
```

于是语言模型形成了一个非常对称的结构：

```text
token ID
  ↓
Embedding
[V, D]
  ↓

Transformer

  ↓
LM head
[D → V]
  ↓
vocabulary logits
```

注意 LM head 的 Linear weight 按 PyTorch orientation 存储也是：

```text
[V, D]
```

这一下就出现了一个非常有趣的现象。

---

# 24. Input Embedding 和 LM head 居然拥有完全相同的 shape

Embedding：

[
E
\in
\mathbb R^{V\times D}
]

LM head：

[
W_{\text{LM}}
\in
\mathbb R^{V\times D}
]

于是自然会产生一个问题：

> 为什么不直接让它们用同一个参数？

也就是：

```text
weight tying
```

设：

```python
lm_head.weight = token_embedding.weight
```

那么输出：

[
\text{logits}
=============

hE^T
]

含义可以粗略理解为：

```text
hidden state h
```

与 vocabulary 中所有 token vectors 做某种 learned compatibility scoring。

---

# 25. Weight tying 能省多少参数

如果不共享：

```text
Embedding:
V × D

LM head:
V × D
```

总共：

[
2VD
]

如果共享：

[
VD
]

直接少掉一整块 vocabulary projection 参数。

比如：

```text
V = 50,000
D = 4096
```

单块：

[
50,000\times4096
================

204.8M
]

parameters。

BF16 权重只算参数本身：

```text
≈ 410 MB
```

如果 optimizer 还保留额外 states，训练时对应成本会更大。

Weight tying 因此并不是一个微不足道的小技巧。

经典工作早已发现，input/output embedding sharing 可以同时减少模型大小，并在语言模型中带来不错的效果。

---

# 26. 但 tied embedding 并不是一个“免费的真理”

这里可以接一点非常新的研究。

一个直觉是：

```text
输入 embedding 负责“理解 token”
输出 embedding 负责“预测 token”
```

既然都是 token representation，共享应该很自然。

但两者接受的梯度其实来自不同角色。

Input embedding：

```text
某个 token 出现在 context 中
↓
这个 row 接收更新
```

Output embedding / LM head：

```text
几乎每一个 prediction step
↓
整个 vocabulary 都进入 logits
```

这两种 optimization pressure 不完全相同。

2026 年一项专门研究 weight tying 的工作发现，共享后的 embedding space 更像 untied model 的 **output embedding**，而不是 input embedding；也就是说，共享矩阵会更强地被 output-prediction objective 塑造。

这说明：

> weight tying 本质上是一种 parameter-sharing inductive bias，而不只是“省一块内存”。

共享以后我们是在强迫模型满足：

```text
input representation
≈
output classifier representation
```

到底是不是最佳选择，要看 architecture 和规模。

---

# 27. 现代模型也没有统一选择 tying

这一点对后面自己造 mini-Qwen / mini-Llama 很重要。

不要形成：

```text
“现代 LLM 一定 tie embedding”
```

的刻板印象。

不同模型家族会做不同选择。

例如 Qwen 系列的公开配置中就可以看到：

```text
tie_word_embeddings: false
```

也就是说输入 embedding 与输出 LM head 可以是独立参数。

因此后面做 architecture lab 时：

```text
tie embeddings
```

完全可以作为一个独立 ablation：

```text
Tied:
更少参数
更强约束

Untied:
更多参数
输入/输出表示拥有独立自由度
```

而不是把 weight tying 当成一种绝对正确的标准做法。

---

# 28. 一个特别容易忽略的事实：大 vocab 对小模型非常贵

对于几十 B 参数的大模型：

```text
V × D
```

可能只是总参数量中的一部分。

但对于我之后想训练的：

```text
几十 M
几百 M
```

级别小模型，embedding + LM head 占比可能非常高。

例如一个：

```text
D = 512
V = 150K
```

embedding：

[
150000\times512
===============

76.8M
]

如果 untied LM head：

```text
又 76.8M
```

总共：

```text
153.6M
```

甚至 Transformer body 还没开始，vocab 两端已经一亿多参数。

所以以后复刻：

```text
mini-Qwen
```

时绝对不能只写：

```text
“沿用 Qwen 的 150K vocab”
```

然后把 hidden dimension 缩成几百。

那样 architecture scaling 已经严重失衡。

小模型设计往往需要重新考虑：

```text
tokenizer vocab size
embedding tying
d_model
depth
FFN ratio
```

这些变量是联动的。

---

# 29. Tokenizer 与 Architecture 在这一章真正连起来了

上一章留下了一个 trade-off：

```text
更大 vocabulary
→
更少 tokens
→
更短 sequence
```

现在又出现另一边：

```text
更大 vocabulary
→
更大的 Embedding
→
更大的 LM head
```

所以 tokenizer 的 vocabulary choice 会同时作用于两个完全不同的计算方向：

```text
                  vocab size ↑
                    /     \
                   /       \
                  ↓         ↓
       sequence length ↓    embedding/head params ↑
                  ↓         ↓
       Transformer token    parameter memory /
       computation ↓        output projection ↑
```

这才是 tokenizer 与 model architecture 真正发生耦合的位置。

所以理论上：

```text
10K tokenizer
32K tokenizer
100K tokenizer
```

谁“更好”不能只比较：

```text
compression ratio
```

还必须考虑：

```text
parameter budget
training FLOPs
context efficiency
softmax cost
language coverage
```

---

# 30. Linear 的 FLOPs 和 Embedding 的成本完全不是一个量级

虽然 Linear 和 Embedding 都拥有二维 weight matrix，但运行方式非常不同。

Embedding：

```python
weight[token_ids]
```

主要是：

```text
memory lookup
```

对于每个 token，只读取对应的一行。

Linear：

```text
x @ Wᵀ
```

则要让当前 activation 和大量权重参与 multiply-accumulate。

所以：

```text
Embedding parameter 很大
```

并不意味着每个 token 都要把整个：

```text
V × D
```

embedding matrix 算一遍。

但 LM head 不一样。

输出 logits：

```text
D → V
```

每一个 prediction position 都需要计算 vocabulary logits。

因此大 vocabulary 不仅增加 parameter storage，还增加 output projection 和后续 softmax/cross-entropy 的工作量。

下一章讲 cross-entropy 时，这个联系会更加明显。

---

# 31. 为什么 LM head 在训练时尤其值得关注

假设：

```text
B = 8
T = 2048
D = 4096
V = 100K
```

最终 logits shape：

```text
[8, 2048, 100000]
```

元素数：

[
8\times2048\times100000
=======================

1.6384\times10^9
]

如果真把完整 fp32 logits materialize：

```text
约 6.5 GB
```

仅仅是一个 tensor。

当然实际训练框架会通过：

```text
bf16
tensor parallel
fused cross entropy
chunking
```

等方法降低压力。

但这里已经可以看出：

> `Linear(D,V)` 并不是模型最后一个无关紧要的小层。

随着 vocabulary 变大，LM head 可以成为非常明显的计算和显存问题。

这一点等之后学 A2 Systems 再回来，会更有感觉。

---

# 32. Embedding / LM head 也是 Tensor Parallel 最自然的切分对象

进一步往真正大模型训练走，假设：

```text
V = 150K
D = 8192
```

单块 embedding：

[
150000\times8192
]

已经巨大。

不一定能方便地只放在单张 GPU。

于是大型训练系统会把这些矩阵进行 partition。

Embedding 可以沿：

```text
vocabulary dimension
```

切：

```text
GPU 0: vocab rows 0 ~ N
GPU 1: vocab rows N ~ 2N
...
```

LM head 同样可以分 vocabulary。

Linear 也可以沿：

```text
output dimension
```

或者：

```text
input dimension
```

做 column / row parallel。

于是 A1 这一章里一句非常普通的：

```text
weight.shape = [out_features, in_features]
```

到了 distributed training 以后，会直接决定：

```text
我沿哪一维 shard？
谁需要 all-reduce？
谁需要 all-gather？
```

这就是为什么 shape contract 不只是“防止 RuntimeError”。

它实际上决定整个 distributed computation graph。

---

# 33. 现代 Linear 还会继续被低秩化、量化和共享

A1 的 Linear 是最纯粹的 dense projection：

[
y=Wx
]

但真正现代模型工程里，围绕这个矩阵会出现大量变化：

```text
LoRA:
W + BA

Quantization:
W_fp16 → W_int8 / int4

MoE:
不同 token 选择不同 FFN Linear weights

Tensor Parallel:
W 被多 GPU shard

Low-rank attention:
投影先进入低维 latent space

Weight sharing:
不同模块复用部分 projection
```

甚至 2026 年还有工作重新研究 attention 中：

```text
Q/K/V projection
```

是否真的必须全部独立，尝试共享部分 projection，从而减少参数和 inference memory。

所以：

> “Linear 是最简单的一层”

和：

> “Linear 不值得研究”

完全不是一回事。

恰恰因为 LLM 的绝大多数参数都是这些矩阵，任何对 Linear 的结构性修改都可能影响整个模型。

---

# 34. LoRA 为什么其实也从这一章就能理解

例如一个 pretrained Linear：

[
W
\in
\mathbb R^{d_{out}\times d_{in}}
]

LoRA 不直接训练整个：

[
\Delta W
]

而是假设 update 近似 low-rank：

[
\Delta W = BA
]

其中：

[
A
\in
\mathbb R^{r\times d_{in}}
]

[
B
\in
\mathbb R^{d_{out}\times r}
]

且：

[
r\ll d_{in},d_{out}
]

于是：

[
y
=

Wx
+
BAx
]

参数从：

[
d_{out}d_{in}
]

变成额外：

[
r(d_{in}+d_{out})
]

所以未来看到：

```text
LoRA target_modules:
q_proj
k_proj
v_proj
o_proj
gate_proj
up_proj
down_proj
```

其实全部都是：

> 给这一章里的 Linear 加一个低秩 update。

A1 先搞清楚每一个矩阵到底是什么 shape，LoRA 才不会变成只会复制配置文件。

---

# 35. Embedding 也不是“语义 embedding 模型”的那个 embedding

这里还需要防止一个术语混淆。

A1 的：

```text
nn.Embedding
```

指：

```text
token ID
→
learned token vector
```

它不是今天 RAG 里讲的：

```text
text embedding model
```

后者通常是：

```text
完整文本
↓
Transformer encoder
↓
pooling
↓
sentence/document vector
```

两个都叫 embedding，但层级完全不同。

A1 的 token embedding 是：

```text
模型内部最底层参数表示
```

RAG 的 embedding 是：

```text
模型计算后的高层语义表示
```

这个区别最好从一开始就分清楚。

---

# 36. Embedding gradient 实际只和出现过的 token 强相关

考虑：

```python
output = embedding(token_ids)
```

当前 batch 如果只出现：

```text
ID = 1, 5, 17, 102
```

作为 input lookup 而言，只有这些对应 rows 被读取。

因此 input embedding 的 gradient 具有天然的 index-locality。

PyTorch 的 Embedding 甚至支持某些场景下使用 sparse gradient。

不过语言模型如果使用：

```text
tied LM head
```

情况会发生变化。

因为 output softmax 对整个 vocabulary 产生 logits，shared matrix 还会受到 output objective 的 dense pressure。

这也是为什么前面提到的 2026 weight-tying 研究观察到共享 embedding 更偏向 output representation。

---

# 37. 为什么重复 token 一开始得到完全相同的 embedding

例如：

```text
the cat chased the dog
```

两个：

```text
the
```

在 Embedding 之后都是：

[
E_{\text{the}}
]

完全相同。

那模型怎么知道：

```text
第一个 the
```

和：

```text
第二个 the
```

处在不同位置、不同语境？

靠后面的 context mixing：

```text
Embedding
↓
RoPE / positional information
↓
Causal self-attention
↓
不同 context
↓
不同 contextual hidden states
```

所以应该区分：

```text
token embedding
```

和：

```text
contextual representation
```

token embedding：

```text
the → 固定一行参数
```

经过几层 Transformer 后：

```text
the₁ → h₁
the₂ → h₂
```

已经可以完全不同。

这也是现代语言模型和静态 Word2Vec representation 的根本区别之一。

---

# 38. 为什么初始化时 token embedding 没有“语义”

随机初始化后：

```text
king
queen
dog
CUDA
浙江大学
```

的 vectors 一开始只是随机点。

不存在：

```text
king - man + woman ≈ queen
```

这类已经学好的结构。

语义是 language modeling objective 训练出来的。

对于 causal LM：

```text
前文 tokens
↓
predict next token
↓
cross entropy
↓
gradient
↓
embedding + Transformer + LM head 一起更新
```

所以语言模型的 representation 并不是 Embedding layer 单独学出来的。

它是整个网络联合优化的结果。

---

# 39. 参数初始化与随机种子还决定 reproducibility

假设 architecture 完全相同。

两次运行：

```python
torch.manual_seed(...)
```

不同，就会得到不同 initial parameters。

对于大模型，训练足够久后宏观趋势可能比较稳定；但对于 A1 的 TinyStories 小模型：

```text
seed
```

完全可能对最终 validation loss 产生可见影响。

所以以后做实验日志，我不应该只记录：

```yaml
d_model: 512
num_layers: 8
lr: 3e-4
```

还应该记录：

```yaml
seed: ...
init_scheme: ...
dtype: ...
tokenizer: ...
```

特别是准备做：

```text
architecture ablation
```

时。

---

# 40. snapshot test 为什么比“模块可以跑”严格得多

假设我测试：

```python
linear = Linear(5, 10)
x = torch.randn(2, 3, 5)

y = linear(x)

assert y.shape == (2, 3, 10)
```

只能证明：

```text
shape 对了
```

却证明不了：

```text
weight orientation 对了
forward 数学对了
parameter mapping 对了
```

如果官方 fixture 给定：

```text
固定 weight
固定 input
固定 expected output
```

然后通过 adapter 加载我的实现，就能直接验证：

```text
相同参数
+
相同输入
→
相同数值
```

这也是为什么 A1 要求实现通过 `tests/adapters.py` 接到统一 tests，而不是根据学生自己的 class name 写测试。

Adapter 本身其实是一层非常好的软件工程设计：

```text
official behavioral contract
        ↑
      adapter
        ↑
student implementation
```

课程测试不用关心我内部文件怎么组织。

---

# 41. Adapter 也让我区分“内部 API”和“外部 API”

例如我内部完全可以命名：

```python
class TransformerLinear(...)
```

而不是：

```python
class Linear(...)
```

也可以把实现放：

```text
model/layers/linear.py
```

而不是课程示例位置。

只要：

```python
tests/adapters.py
```

知道怎样调用就行。

因此：

```text
我的源码组织
```

和：

```text
assignment contract
```

应该解耦。

这也是以后写真实 library 很常见的设计：

```text
internal representation
≠
public API
```

笔记负责帮助我理解。

adapter 负责满足 external interface。

不应该反过来为了 test fixture，把整个自己的代码架构写死。

---

# 42. 我现在会怎样实现最小 Linear

核心逻辑实际上非常少：

```python
class Linear(nn.Module):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        device=None,
        dtype=None,
    ):
        super().__init__()

        self.in_features = in_features
        self.out_features = out_features

        self.weight = nn.Parameter(
            torch.empty(
                out_features,
                in_features,
                device=device,
                dtype=dtype,
            )
        )

        std = math.sqrt(
            2 / (in_features + out_features)
        )

        nn.init.trunc_normal_(
            self.weight,
            mean=0.0,
            std=std,
            a=-3 * std,
            b=3 * std,
        )

    def forward(self, x):
        return x @ self.weight.T
```

这里最重要的不是代码长度。

而是每一行都对应一个明确 contract：

```text
nn.Module
    → module tree

nn.Parameter
    → learnable model state

[out, in]
    → checkpoint convention

device/dtype
    → construction semantics

truncated Xavier-like init
    → initialization contract

x @ W.T
    → [..., in] → [..., out]
```

如果这些都理解了，Linear 本身确实应该很短。

---

# 43. Embedding 的实现甚至更短

概念上：

```python
class Embedding(nn.Module):
    def __init__(
        self,
        num_embeddings,
        embedding_dim,
        device=None,
        dtype=None,
    ):
        super().__init__()

        self.weight = nn.Parameter(
            torch.empty(
                num_embeddings,
                embedding_dim,
                device=device,
                dtype=dtype,
            )
        )

        # 按 handout 的 Embedding initialization 初始化
        ...

    def forward(self, token_ids):
        return self.weight[token_ids]
```

真正应该花时间理解的是：

```text
为什么 weight 是 [V, D]
为什么直接 advanced indexing 就行
为什么不用 one-hot
为什么 token ID 不需要 gradient
为什么 embedding weight 需要 gradient
```

而不是把简单 lookup 包成几十行 abstraction。

---

# 44. Token ID 本身为什么不需要 gradient

模型参数需要：

```text
∂L / ∂W
```

hidden state 需要：

```text
∂L / ∂h
```

但是 token ID：

```text
57
```

只是：

```text
“选择第 57 行”
```

这个离散索引。

不存在自然的：

[
\frac{\partial L}{\partial 57}
]

让 optimizer 把：

```text
57 → 56.83
```

这种操作。

所以：

```text
token IDs:
integer / non-differentiable

embedding weights:
floating point / differentiable
```

Embedding layer 正好就是离散世界和连续可微世界之间的接口。

---

# 45. Embedding 可以被看成模型的“离散入口”

整个 language model 可以抽象成：

[
p(x_{t+1}\mid x_{\leq t})
]

这里：

```text
x_t
```

最开始是一个离散 token。

Embedding 做：

[
x_t
\mapsto
e_{x_t}\in\mathbb{R}^D
]

从这一刻开始，模型才能使用：

```text
dot product
linear transformation
normalization
attention
gradient descent
```

这些连续空间工具。

最后 LM head 又把：

[
h_t\in\mathbb R^D
]

映射到：

[
z_t\in\mathbb R^V
]

然后 softmax 回到离散 vocabulary distribution。

所以一个 causal LM 很漂亮地形成：

```text
discrete token
    ↓
Embedding
    ↓
continuous representation
    ↓
Transformer
    ↓
continuous hidden state
    ↓
Linear LM head
    ↓
discrete-token logits
```

这一章实际上把模型两端都串起来了。

---

# 46. 从 Linear / Embedding 已经能读懂很多模型 config

以后打开一个 Hugging Face config，看到：

```json
{
  "vocab_size": 152064,
  "hidden_size": 3584,
  "intermediate_size": 18944,
  "num_attention_heads": 28,
  "num_key_value_heads": 4,
  "tie_word_embeddings": false
}
```

不应该只看到一堆数字。

已经可以立即推出：

```text
Embedding:
[152064, 3584]

LM head:
[152064, 3584]

因为 tie=false：
两套独立参数
```

以及 FFN：

```text
up/gate:
3584 → 18944

down:
18944 → 3584
```

Q projection：

```text
3584 → num_heads × head_dim
```

K/V：

```text
3584 → num_kv_heads × head_dim
```

这就是 A1 从零实现的价值：

> 模型 config 开始从“参数列表”变成真正可推导的 tensor graph。

Qwen 的公开 config 就明确展示了诸如 `hidden_size`、`vocab_size` 和 `tie_word_embeddings=false` 之间的这种关系。

---

# 47. 如果以后自己做 mini architecture，应该怎么缩

假设参考一个大模型：

```text
V = 150K
D = 7168
L = 60
```

想造：

```text
mini version
```

最差的方法是：

```text
所有配置简单除以 10
```

因为不同组件 scaling law 不一样。

Embedding 参数：

[
VD
]

attention/FFN 参数：

[
O(D^2L)
]

所以当：

```text
D 大幅缩小
```

时：

[
D^2
]

下降得比：

[
VD
]

快很多。

结果是：

```text
大模型：
Transformer body 占主要参数

小模型：
Embedding / LM head 占比突然非常夸张
```

这也是为什么我以后复刻 mini-Qwen、mini-Llama 时，tokenizer 和 weight tying 不能机械照搬原模型。

这是一个真正的 architecture scaling 问题。

---

# 48. A1 baseline 最小测试应该覆盖什么

这一章的 local tests 至少可以分四层。

### Shape

Linear：

```text
[D]
→
[D']

[B, D]
→
[B, D']

[B, T, D]
→
[B, T, D']
```

Embedding：

```text
[]
→
[D]

[T]
→
[T, D]

[B, T]
→
[B, T, D]
```

---

### Numerical semantics

手动设置：

```python
weight = ...
```

确认：

```python
linear(x)
==
x @ weight.T
```

Embedding：

```python
embedding(ids)
==
weight[ids]
```

---

### Parameter semantics

确认：

```python
dict(model.named_parameters())
```

里确实存在：

```text
weight
```

以及：

```python
state_dict()
```

能够保存/恢复。

---

### dtype / device

例如：

```text
float32 CPU
bf16 CUDA
```

在环境允许时分别验证。

参数和输出 dtype/device 都应满足 constructor 和输入约定。

---

# 49. Embedding 的边界测试也应该更准确地写

原稿里写：

```text
token ID 的边界行为
```

这里我会具体拆成：

```text
ID = 0
ID = vocab_size - 1
重复 ID
多维 IDs
非法 negative / out-of-range ID
```

不过要注意：

```python
weight[-1]
```

在普通 Python tensor indexing 里存在负索引语义。

因此如果希望 tokenizer token ID contract 明确限定：

[
0\le id < V
]

最好在 tokenizer / data pipeline 层确保不会产生非法 ID，而不是依赖 Embedding 帮忙“理解 token 语义”。

这也是模块边界问题：

```text
Embedding 的职责：
lookup

Tokenizer/data contract：
产生合法 token IDs
```

---

# 50. A1 官方测试真正想验证的不是初始化结果本身

还有一个很重要的测试思维。

如果官方 snapshot：

```text
先构造模块
↓
再加载固定 weights
↓
比较 output
```

那么这类 snapshot test 主要验证的是：

```text
parameter shape
weight orientation
forward implementation
adapter mapping
```

而不是：

```text
你的 random initialization
```

因为初始化出来的值已经被 fixture 覆盖。

所以 initialization 需要另外通过：

```text
code review
distribution test
统计 mean/std/range
```

验证。

这一点很值得写进复盘：

> 不要把“官方测试过了”误认为“所有 handout contract 都自动被验证了”。

测试只能覆盖它实际观测到的行为。

---

# 51. 我会额外给初始化写一个 statistical test

例如创建一个比较大的 Linear：

```python
layer = Linear(1024, 4096)
w = layer.weight.detach().float()
```

然后检查：

```python
std_expected = math.sqrt(2 / (1024 + 4096))

w.mean()
w.std()
w.min()
w.max()
```

预期大致：

```text
mean ≈ 0
std ≈ specified scale
min >= -3σ
max <= +3σ
```

当然有限采样和 truncation 会让 empirical standard deviation 不会与未经截断的 nominal `std` 完全相同。

这个 test 的目的不是：

```text
精确到 1e-8
```

而是防止自己写成：

```python
torch.randn(...)
```

或者忘记：

```text
±3σ bounds
```

这比只依赖 snapshot 更完整。

---

# 52. 为什么 `state_dict` 对之后 Architecture Lab 特别重要

假设我之后实现：

```text
Baseline Transformer
↓
改成 GQA
↓
改成 MLA
↓
改成 MoE
```

如果每次都随便命名：

```text
linear1
linear2
foo
bar
```

那就很难：

```text
复用 baseline 权重
检查参数变化
做部分 load
比较 checkpoint
转换 Hugging Face 权重
```

更好的方式是从一开始就尽量让参数语义明确：

```text
token_embedding.weight

q_proj.weight
k_proj.weight
v_proj.weight
o_proj.weight

gate_proj.weight
up_proj.weight
down_proj.weight

lm_head.weight
```

这样之后看到 checkpoint 就能直接理解 architecture。

这不是 A1 强制要求的 class naming，但对于自己后续扩展非常值得保留。

---

# 53. 参数命名其实是一种 architecture serialization

想象只给我：

```text
checkpoint.safetensors
```

没有模型代码。

如果里面有：

```text
layers.0.attn.q_proj.weight
layers.0.attn.k_proj.weight
layers.0.attn.v_proj.weight
layers.0.attn.o_proj.weight
```

我已经可以猜出：

```text
这是某种显式 Q/K/V projection attention
```

如果发现：

```text
q_a_proj
q_b_proj
kv_a_proj_with_mqa
kv_b_proj
```

就会怀疑：

```text
是不是 MLA / low-rank latent projection
```

因此：

```text
state_dict
```

不只是“保存参数”。

它在一定程度上也是 architecture 的 serialized description。

Linear weight shape 就是其中最基本的语法。

---

# 54. 到这里再看 A1 的 Linear / Embedding，其实没那么“小”

代码上：

```text
Linear:
十几行

Embedding:
十几行
```

但是已经连接到：

```text
Tensor shape contract
GEMM
parameter registration
checkpoint compatibility
initialization
vocabulary scaling
LM head
weight tying
tensor parallel
LoRA
quantization
GQA
MLA
```

这也是我现在越来越喜欢 CS336 这种教学方式的原因。

它不需要单独给我列一章：

```text
“现代大模型工程技巧大全”
```

只要真正把：

```text
weight.shape = [out, in]
```

这种最小细节想明白，就可以一路推出后面的系统设计。

---

# 55. 当前 baseline 应该留下什么

这一章完成以后，我希望代码里至少明确留下：

```text
Linear
├── weight: [d_out, d_in]
├── bias: none
├── device/dtype support
├── handout initialization
└── arbitrary leading dimensions

Embedding
├── weight: [V, D]
├── integer index lookup
├── device/dtype support
└── handout initialization
```

并且可以回答：

1. 为什么 Linear 的参数存成 `[out, in]`，forward 却像 `x @ W.T`？
2. 为什么 `[B,T,D]` 不需要手动 flatten 就可以过 Linear？
3. 为什么 Embedding 不是“把 token ID 做一次线性变换”？
4. 为什么 one-hot × matrix 与 embedding lookup 数学等价、实现却差很多？
5. 为什么 tokenizer vocabulary size 会直接改变模型参数量？
6. 为什么 LM head 和 input Embedding 恰好拥有相同 shape？
7. weight tying 到底在共享什么，又牺牲了什么自由度？
8. 为什么小模型不能机械照搬大模型的 vocab size？
9. 为什么 initialization 会影响 architecture ablation 的公平性？
10. 为什么 snapshot passing 不一定意味着 initialization 也写对了？

如果这些问题都能不看代码回答，这一章基本就真正过去了。

---

# 56. 小结

Tokenizer 把自然语言离散化成：

```text
token IDs
```

Embedding 再把这些离散 ID 送进：

```text
continuous vector space
```

于是：

[
[B,T]
\rightarrow
[B,T,D]
]

Linear 则构成 Transformer 内部最普遍的 feature transformation：

[
[...,D_{in}]
\rightarrow
[...,D_{out}]
]

表面上只是：

```text
lookup
+
matrix multiplication
```

背后却已经决定：

```text
参数怎么存
checkpoint 怎么解释
FLOPs 怎么计算
模型怎么并行
初始化怎样传播
vocabulary 如何影响参数预算
输入和输出 embedding 是否共享
```

我现在更愿意把这两个模块理解为：

> **Embedding 定义了模型如何进入连续表示空间，而 Linear 定义了这个空间内部绝大多数可学习变换。**

后面 attention、SwiGLU 甚至 LM head，看起来越来越复杂，拆开以后仍然只是大量不同 shape 的 Linear，以及它们之间附加的 normalization、activation 和 token mixing。

下一章进入另一个看起来只有几行代码、却非常容易因为数值范围写错的部分：

```text
logits
  ↓
softmax
  ↓
probability

prediction + target
  ↓
cross-entropy
  ↓
training objective
```

也就是 **softmax 与 cross-entropy**。

[上一章：Tokenizer / BPE](/blog/2026/2026-08-15-cs336-a1-tokenizer-bpe/)

[下一章：softmax / cross-entropy](/blog/2026/2026-08-15-cs336-a1-softmax-cross-entropy/)
