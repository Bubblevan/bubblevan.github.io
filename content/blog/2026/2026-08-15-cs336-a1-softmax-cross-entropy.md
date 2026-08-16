---
schema: bubblevan/v1
id: blog-20260815-cs336-a1-softmax-cross-entropy
content_kind: blog
title: CS336 A1 复盘三：softmax 与 cross-entropy
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 从稳定 softmax 到 causal LM 的 next-token cross-entropy，复盘 logits、log-sum-exp、target 对齐、梯度语义和 perplexity，并进一步理解大词表模型为什么开始融合 LM head 与 loss。
topics: [CS336, PyTorch, Softmax, Cross Entropy, Language Model]
projects: [cs336]
aliases: []
authors: [bubblevan]
--------------------

前两章已经完成了两次表示转换：

```text
Unicode text
    ↓ Tokenizer
token IDs
    ↓ Embedding
continuous hidden vectors
```

Transformer 接下来会不断对这些 hidden vectors 做 Linear、attention、FFN 和 normalization，最终得到：

```text
hidden states:
[B, T, D]
```

LM head 再把每一个位置投影回整个 vocabulary：

```text
[B, T, D]
    ↓ Linear(D, V)
[B, T, V]
```

得到的最后一维就是：

```text
logits
```

但模型真正要训练的是：

> 给定前面的 token，应该给真实的下一个 token 多大的概率？

因此还需要完成最后两步：

```text
logits
   ↓ softmax
probability distribution
   ↓ negative log likelihood
cross-entropy loss
```

这两个操作的公式都非常短。

softmax：

[
p_i
===

\frac{e^{z_i}}
{\sum_j e^{z_j}}
]

cross-entropy：

[
L=-\log p_y
]

第一次学机器学习时，很容易觉得这里已经没有什么值得继续讨论的。

但 A1 把 softmax 和 cross-entropy 单独要求从零实现是有原因的。

这一小段代码实际上同时连接了：

```text
概率分布
数值稳定性
causal LM objective
gradient dynamics
perplexity
mixed precision
大 vocabulary 显存瓶颈
```

甚至到了 2026 年，围绕：

```text
LM head + softmax + cross-entropy
```

还在发生非常实际的系统优化。

所以这一章真正要搞清楚的不是：

> “PyTorch 里怎么调用 `F.cross_entropy`？”

而是：

> **语言模型的最后一串任意实数，究竟怎样变成一个稳定、可微、可以大规模训练的概率目标？**

---

# 1. logits 到底是什么

假设 vocabulary 只有五个 token：

```text
0: the
1: cat
2: dog
3: sat
4: .
```

某一个位置经过 LM head 后得到：

```python
logits = [
    2.1,
    0.7,
    -0.5,
    1.9,
    0.2,
]
```

这些数不是概率。

它们可以：

```text
大于 1
小于 0
总和不等于 1
```

都没有问题。

logit 更准确的含义是：

```text
模型对各个 class/token 给出的未归一化 score
```

例如：

```text
the  → 2.1
cat  → 0.7
dog  → -0.5
sat  → 1.9
.    → 0.2
```

只能说：

```text
the 比 cat 更受模型偏好
sat 也相当有可能
dog 当前非常不受偏好
```

但还不能说：

```text
the 的概率是 2.1
```

因为概率必须满足：

[
p_i\ge 0
]

以及：

[
\sum_i p_i=1
]

softmax 就负责把这些 relative scores 映射成一个 categorical distribution。

PyTorch 的 `CrossEntropyLoss` 文档也明确要求输入是 **unnormalized logits**，它们不需要为正，也不需要总和为 1。

---

# 2. softmax 做的不是简单“归一化”

softmax 定义：

[
p_i
===

\frac{\exp(z_i)}
{\sum_{j=1}^{V}\exp(z_j)}
]

首先通过：

[
\exp(z_i)
]

把任意实数映射到正数。

然后除以总和：

[
\sum_j\exp(z_j)
]

于是最终：

[
0<p_i<1
]

且：

[
\sum_i p_i=1
]

PyTorch 的官方定义也是这样：softmax 将指定 dimension 上的元素重新缩放到 ([0,1])，并使其总和为 1。

但这里有一个比“变成概率”更重要的性质：

> softmax 保留 logits 之间的相对差异。

例如：

```text
logits:
[0, 1, 2]
```

和：

```text
[1000, 1001, 1002]
```

应该得到完全一样的 probability distribution。

因为真正重要的是：

```text
谁比谁高多少
```

而不是它们共同位于数轴的什么绝对位置。

---

# 3. softmax 的平移不变性

对任意常数 (c)：

[
\operatorname{softmax}(z_i+c)
=============================

\frac{e^{z_i+c}}
{\sum_j e^{z_j+c}}
]

把：

[
e^c
]

提出：

# [

\frac{e^ce^{z_i}}
{e^c\sum_j e^{z_j}}
]

于是：

# [

\frac{e^{z_i}}
{\sum_j e^{z_j}}
]

所以：

[
\boxed{
\operatorname{softmax}(z+c)
===========================

\operatorname{softmax}(z)
}
]

这是一个非常重要的不变量。

例如：

```text
[1, 2, 3]
```

和：

```text
[101, 102, 103]
```

应该拥有相同输出。

A1 当前官方 test 就明确检查了这一点。

测试先计算：

```python
F.softmax(x, dim=-1)
```

然后再要求：

```python
run_softmax(x + 100, dim=-1)
```

得到同样结果。

这并不是随便选的一个 edge case。

它正好对应 stable softmax 最核心的数值技巧。

---

# 4. naive softmax 为什么会 overflow

最直接实现：

```python
def softmax(x, dim):
    exp_x = torch.exp(x)
    return exp_x / exp_x.sum(dim=dim, keepdim=True)
```

数学完全正确。

但假设：

```python
x = torch.tensor([
    1000.0,
    1001.0,
    1002.0,
])
```

需要计算：

[
e^{1002}
]

这个数字远远超过普通 floating-point 能表示的范围。

于是：

```text
exp(1002)
→ inf
```

分母也可能：

```text
inf
```

最终：

```text
inf / inf
→ NaN
```

也就是说：

> 数学公式正确，不意味着浮点数实现正确。

这是 A1 里第一个非常典型的 numerical stability 问题。

---

# 5. stable softmax：减去最大值

利用前面的平移不变性，可以选：

[
c=-\max(z)
]

得到：

[
p_i
===

\frac{
e^{z_i-\max(z)}
}{
\sum_j e^{z_j-\max(z)}
}
]

这样最大的 logit：

[
z_{\max}-z_{\max}=0
]

于是最大的 exponential：

[
e^0=1
]

其他项则满足：

[
z_i-z_{\max}\le0
]

所以：

[
0<e^{z_i-z_{\max}}\le1
]

整个 exponentiation 再也不会因为巨大正值而 overflow。

实现就是：

```python
def softmax(x, dim):
    x_max = x.max(dim=dim, keepdim=True).values
    exp_x = torch.exp(x - x_max)

    return exp_x / exp_x.sum(
        dim=dim,
        keepdim=True,
    )
```

这里的：

```python
keepdim=True
```

也很重要。

假设：

```text
x:
[B, T, V]
```

沿：

```text
V
```

求 max 后希望：

```text
[B, T, 1]
```

这样 broadcasting：

```text
[B, T, V]
-
[B, T, 1]
```

才自然成立。

---

# 6. stability 不只是在防 overflow

减最大值之后：

```text
最大的 exp = 1
```

确实解决了 overflow。

但很小的值仍然可能 underflow：

```text
exp(-1000)
→ 0
```

这通常不是同等严重的问题。

因为如果一个 token 比最大 logit 小 1000：

```text
probability ≈ 0
```

在有限精度下被表示为：

```text
0
```

通常符合实际需求。

所以 numerical stability 的基本取舍是：

```text
overflow:
很危险
→ inf / NaN

underflow:
很多情况下只是把极小概率压成 0
```

stable softmax 主要解决的是前者。

---

# 7. softmax 的 `dim` 不是一个无关 API 参数

对于语言模型：

```text
logits:
[B, T, V]
```

每一个：

```text
(batch, position)
```

都应该独立得到：

```text
V 个 token 的 probability distribution
```

所以 normalization dimension 必须是：

```text
V
```

也就是：

```python
dim=-1
```

如果错误写成：

```python
dim=1
```

模型就会在：

```text
sequence positions
```

之间归一化。

也就是说：

```text
第 1 个位置
第 2 个位置
...
第 T 个位置
```

在竞争同一份概率质量。

这完全不是语言模型定义。

更危险的是：

```text
代码不会报错。
```

输出 shape 仍然是：

```text
[B, T, V]
```

数值甚至仍然看起来：

```text
0 到 1 之间
```

因此：

> shape correctness 并不能保证 semantic correctness。

这是张量程序里非常常见的一类 bug。

---

# 8. 我更愿意把 softmax 理解成“竞争”

假设：

```text
V = 4
```

logits：

```text
[1, 1, 1, 1]
```

因为所有 token 完全一样：

[
p_i=\frac14
]

如果把第一个 logit 提升：

```text
[3, 1, 1, 1]
```

那么它的 probability 增大。

但因为所有概率必须满足：

[
\sum_i p_i=1
]

其他 token 的 probability 就会一起减少。

所以 softmax 并不是独立地给每个 token：

```text
“打一个 0~1 的分”
```

而是在一个互斥 categorical space 中：

```text
所有 token 竞争同一份 probability mass
```

这和 sigmoid 非常不同。

如果做 multi-label classification：

```text
猫？
狗？
室内？
白色？
```

多个标签可以同时成立，更常用的是独立 sigmoid。

语言模型 next-token prediction 则是：

```text
下一个位置最终只能出现一个 vocabulary token
```

所以 softmax categorical distribution 很自然。

---

# 9. logit difference 比 absolute logit 更有意义

考虑只有两个 token：

```text
A
B
```

softmax：

[
p(A)
====

\frac{e^{z_A}}
{e^{z_A}+e^{z_B}}
]

分子分母同除：

[
e^{z_A}
]

得到：

[
p(A)
====

\frac{1}
{1+e^{z_B-z_A}}
]

所以概率完全取决于：

[
z_A-z_B
]

而不是：

```text
z_A = 10
```

本身有什么绝对意义。

这也是为什么：

```text
logits
```

这个名字很合适。

对两个 class：

[
\log
\frac{p(A)}
{p(B)}
======

z_A-z_B
]

也就是说：

> logit difference 就是 log probability ratio。

softmax 把线性空间中的 score difference 转成 probability odds。

---

# 10. temperature 其实只是缩放 logits

生成模型里经常看到：

```python
softmax(logits / temperature)
```

如果：

[
T<1
]

logits difference 被放大：

```text
distribution 更尖锐
```

如果：

[
T>1
]

difference 被压缩：

```text
distribution 更平坦
```

例如：

```text
logits = [5, 4, 3]
```

用：

```text
T = 0.5
```

相当于：

```text
[10, 8, 6]
```

最大 token 更占优势。

而：

```text
T = 2
```

变成：

```text
[2.5, 2, 1.5]
```

差距变小。

值得注意的是：

> training cross-entropy 通常使用原始 logits，不是在训练时随便加生成 temperature。

temperature 更多是 inference sampling 或蒸馏、校准等场景的控制变量。

---

# 11. 从概率到 language modeling objective

causal language model 要学习：

[
p(x_1,x_2,\dots,x_T)
]

根据 chain rule：

[
p(x_1,\dots,x_T)
================

\prod_{t=1}^{T}
p(x_t\mid x_{<t})
]

直接最大化一大串概率乘积数值上非常不方便。

取 logarithm：

[
\log p(x_1,\dots,x_T)
=====================

\sum_t
\log p(x_t\mid x_{<t})
]

训练希望最大化 log-likelihood。

等价于最小化：

[
-\sum_t
\log p(x_t\mid x_{<t})
]

这就是：

```text
negative log likelihood
```

再对 token 求平均：

[
L
=

-\frac1N
\sum_{t=1}^{N}
\log p(x_t\mid x_{<t})
]

就是 causal LM 最常见的 token-level cross-entropy objective。

所以 cross-entropy 并不是：

```text
“大家习惯用的一个分类 loss”
```

它直接来自：

> **maximum likelihood estimation。**

---

# 12. 为什么这里叫 cross-entropy

真实 target distribution 对一个位置实际上是：

```text
one-hot
```

假设真实 token 是：

```text
y
```

那么：

[
q_i
===

\begin{cases}
1,&i=y\
0,&i\neq y
\end{cases}
]

模型预测：

[
p_i
]

两个分布的 cross-entropy：

[
H(q,p)
======

-\sum_i q_i\log p_i
]

因为只有 target 位置：

[
q_y=1
]

其他地方全为 0，所以：

[
H(q,p)
======

-\log p_y
]

因此普通 hard-target language modeling CE：

```text
实际上就是 target token 的 negative log probability。
```

这也解释了为什么我们根本没必要显式构造：

```text
[B,T,V]
```

大小的 one-hot target。

只保存：

```text
[B,T]
```

的 integer token IDs 就够了。

---

# 13. cross-entropy 最直接的实现

如果已经有稳定 probability：

```python
probs = softmax(logits, dim=-1)
```

可以：

```python
target_probs = probs[
    torch.arange(N),
    targets,
]

loss = -torch.log(target_probs).mean()
```

数学上完全正确。

但是实际实现通常不这么做。

原因是：

```text
先 softmax
再 log
```

会引入额外数值问题和中间 tensor。

更好的方式是直接从 logits 推导 cross-entropy。

---

# 14. 从 softmax 推出 log-sum-exp

target token 的概率：

[
p_y
===

\frac{e^{z_y}}
{\sum_j e^{z_j}}
]

negative log：

[
-\log p_y
]

代入：

# [

-\log
\frac{e^{z_y}}
{\sum_j e^{z_j}}
]

拆开：

# [

-\log e^{z_y}
+
\log
\sum_j e^{z_j}
]

于是：

[
\boxed{
L
=

\log\sum_j e^{z_j}
-z_y
}
]

这就是 cross-entropy 最重要的计算形式。

也就是：

```text
log-sum-exp
-
target logit
```

PyTorch 提供的 `torch.logsumexp` 就专门实现这一类稳定 reduction。

---

# 15. log-sum-exp 也必须稳定

naive：

```python
torch.log(torch.exp(x).sum())
```

仍然会遇到：

```text
exp(1000)
→ inf
```

所以同样利用最大值 (m)：

[
m=\max_j z_j
]

那么：

[
\log\sum_j e^{z_j}
]

写成：

[
\log
\left(
e^m
\sum_j e^{z_j-m}
\right)
]

展开：

# [

m
+
\log
\sum_j e^{z_j-m}
]

于是：

[
\boxed{
\operatorname{LSE}(z)
=====================

m+
\log\sum_j e^{z_j-m}
}
]

所有 exponentiation 的输入仍然：

[
\le0
]

因此不会 overflow。

最终稳定 CE：

[
L
=

m
+
\log\sum_j e^{z_j-m}
--------------------

z_y
]

---

# 16. A1 cross-entropy 真正在测试的就是这一点

当前官方 `test_nn_utils.py` 不只是拿一组普通输入和：

```python
F.cross_entropy
```

比。

测试随后直接构造：

```python
large_inputs = 1000.0 * inputs
```

再比较学生实现和 PyTorch。

所以如果实现：

```python
softmax
→
log
→
target
```

很可能在普通 fixture 通过。

但：

```text
logits × 1000
```

之后直接炸掉。

这类 test 很有 CS336 的味道：

> 单元测试不是只验证数学公式，而是在验证可用于真实训练的 numerical behavior。

---

# 17. 为什么通常不应该把 softmax 输出再传给 CrossEntropyLoss

PyTorch `CrossEntropyLoss` 的 input contract 是：

```text
raw logits
```

而不是 probability。

也就是说：

```python
F.cross_entropy(logits, targets)
```

是对的。

而：

```python
F.cross_entropy(
    F.softmax(logits, dim=-1),
    targets,
)
```

语义上是错的。

因为 CE 内部本来就会进行对应于：

```text
log-softmax + negative log likelihood
```

的稳定计算。

如果先 softmax：

```text
logits
↓
probability
↓
CrossEntropy 再把 probability 当 logits
```

目标函数已经被改变。

所以训练分类/语言模型时一个很实用的习惯是：

> **模型 forward 返回 logits，loss 自己处理 normalization。**

---

# 18. `log_softmax` 也比 `log(softmax())` 更合理

同理：

```python
torch.log(
    torch.softmax(logits, dim=-1)
)
```

数学上等价于：

```python
torch.log_softmax(logits, dim=-1)
```

但后者可以直接用稳定形式：

[
z_i-\operatorname{LSE}(z)
]

避免先产生可能 underflow 到 0 的 probability，再：

```text
log(0)
→ -inf
```

所以数值计算里一个反复出现的模式是：

```text
数学上的复合操作
```

往往应该：

```text
代数化简
→
重新实现成稳定 primitive
```

而不是机械按照公式执行每一步。

---

# 19. cross-entropy 的 shape contract

A1 当前 adapter 测试实际上把问题简化成：

```text
inputs:
[N, V]

targets:
[N]
```

官方测试原本构造：

```text
[2, 4, 5]
```

的 logits 和：

```text
[2, 4]
```

targets，然后显式：

```python
inputs.view(-1, inputs.size(-1))
targets.view(-1)
```

得到：

```text
[8, 5]
[8]
```

再计算 CE。

所以 A1 的核心 contract 可以理解为：

```text
logits:
[..., V]

targets:
[...]

flatten:
[N, V]
[N]
```

其中：

[
N
=

\text{所有 prediction positions}
]

vocabulary 维永远保留为最后一维。

---

# 20. 为什么 flatten `[B,T]` 很自然

语言模型里：

```text
B:
batch 中的不同 sequence

T:
同一 sequence 的不同 prediction position
```

对于 cross-entropy 来说，两者其实都只是：

```text
独立的 supervised examples
```

例如：

```text
[B,T,V]
```

展平：

```text
[B*T,V]
```

意味着：

```text
batch 0, token 0
batch 0, token 1
...
batch 1, token 0
...
```

全部放进同一组 token-level predictions。

然后：

```python
loss.mean()
```

就是：

[
\frac{1}{BT}
\sum_{b,t}
L_{b,t}
]

这也是为什么正常情况下：

```text
batch size 改变
```

并不会直接改变 loss 的量纲。

---

# 21. causal LM 最容易写错的是 target shift

假设原始 token sequence：

```text
[A, B, C, D, E]
```

模型应该学习：

```text
给 A
预测 B

给 A B
预测 C

给 A B C
预测 D

给 A B C D
预测 E
```

因此训练 pair：

```text
input:
[A, B, C, D]

target:
[B, C, D, E]
```

也就是：

```python
inputs = tokens[:, :-1]
targets = tokens[:, 1:]
```

模型输入长度：

```text
T
```

对应：

```text
T
```

个 next-token prediction。

这个 shift 属于：

```text
training/data contract
```

而不是 cross-entropy 函数本身应该猜的东西。

---

# 22. 为什么不能让第 t 个位置预测自己

假设错误地：

```text
input  = [A,B,C,D]
target = [A,B,C,D]
```

而模型 causal mask 又允许 position (t) 看到自己的 token embedding。

那么：

```text
位置 t
```

在预测：

```text
token t
```

时输入里已经包含了：

```text
token t
```

于是任务变成了某种：

```text
copy input token
```

而不是：

```text
predict next token
```

loss 可能下降得异常漂亮。

模型却根本没在做正确的 causal language modeling。

所以如果 validation loss：

```text
好得离谱
```

第一批该检查的问题就是：

```text
target 有没有 shift？
mask 有没有泄漏 future？
训练/验证数据有没有重叠？
```

A1 leaderboard 的官方仓库甚至专门提醒，异常漂亮的 validation loss 可能意味着 metric/data pipeline 算错，并建议检查 decoded samples、vocab 和 validation setup。

---

# 23. causal mask 和 target shift 解决的是两个不同问题

这两个非常容易混。

### Target shift

决定：

```text
当前位置的监督标签是谁？
```

即：

[
h_t\rightarrow x_{t+1}
]

---

### Causal mask

决定：

```text
当前位置可以看见哪些输入？
```

即：

[
h_t
===

f(x_{\le t})
]

而不能看：

[
x_{>t}
]

所以完整 causal LM contract 是：

```text
model sees:
x_0 ... x_t

model predicts:
x_(t+1)
```

必须同时保证：

```text
正确 shift
+
正确 causal attention mask
```

只做一个不够。

---

# 24. 为什么 cross-entropy 的梯度如此漂亮

这是这一章最值得真正手推一次的地方。

设：

[
L
=

-\log p_y
]

其中：

[
p_i
===

\frac{e^{z_i}}
{\sum_j e^{z_j}}
]

前面已经写成：

[
L
=

## \log\sum_j e^{z_j}

z_y
]

对某个 logit (z_k) 求导。

第一项：

[
\frac{\partial}
{\partial z_k}
\log\sum_j e^{z_j}
==================

\frac{e^{z_k}}
{\sum_j e^{z_j}}
================

p_k
]

第二项：

[
\frac{\partial z_y}
{\partial z_k}
==============

\begin{cases}
1,&k=y\
0,&k\ne y
\end{cases}
]

所以：

[
\boxed{
\frac{\partial L}{\partial z_k}
===============================

p_k-\mathbf 1[k=y]
}
]

也就是：

[
\boxed{
\nabla_z L=p-y_{\text{one-hot}}
}
]

这是 softmax + cross-entropy 最漂亮的性质之一。

---

# 25. 这个梯度到底在说什么

对正确 token：

[
k=y
]

梯度：

[
p_y-1
]

因为：

[
0\le p_y\le1
]

所以通常：

[
p_y-1\le0
]

gradient descent：

[
z_y
\leftarrow
z_y-\eta(p_y-1)
]

于是：

```text
正确 token logit 被提高
```

对于错误 token：

[
k\neq y
]

梯度：

[
p_k
\ge0
]

gradient descent 后：

```text
错误 token logit 被降低
```

所以 cross-entropy 本质上干的是：

```text
抬高 target
压低 competitors
```

而 softmax 决定压低每一个 competitor 的力度。

---

# 26. 模型越错，correct token gradient 越大

假设 target token 当前：

```text
p_y = 0.01
```

那么：

[
\frac{\partial L}{\partial z_y}
===============================

-0.99
]

更新信号很强。

如果模型已经：

```text
p_y = 0.99
```

那么：

[
\frac{\partial L}{\partial z_y}
===============================

-0.01
]

信号很弱。

所以 CE 自动具备一种非常直观的性质：

> **预测越错，纠正越强；已经非常确定且正确，更新就变小。**

这比简单做：

```text
target logit 和某个固定值的 MSE
```

自然得多。

---

# 27. 错误 token 也并不是平均受到惩罚

对于错误 token：

[
\frac{\partial L}{\partial z_k}
===============================

p_k
]

所以：

```text
模型非常相信的错误 token
```

会得到很大梯度。

而：

```text
本来 probability 就接近 0 的错误 token
```

得到的梯度也接近 0。

例如：

```text
target = cat

p(cat) = 0.1
p(dog) = 0.8
p(the) = 0.001
```

那么最需要被压下去的是：

```text
dog
```

而不是：

```text
the
```

这就是 softmax competition 产生的 adaptive gradient。

---

# 28. 一个非常好的单元测试：target logit 单调性

由：

[
L
=

\operatorname{LSE}(z)-z_y
]

可以知道：

```text
其他 logits 固定
```

时，提高：

[
z_y
]

应该：

```text
loss 不增加
```

因此可以写：

```python
loss1 = cross_entropy(
    logits,
    target,
)

logits2 = logits.clone()
logits2[..., target] += 1

loss2 = cross_entropy(
    logits2,
    target,
)

assert loss2 <= loss1
```

比只和 PyTorch reference 对齐更有意义。

因为这个 test 在检查：

```text
目标函数的数学语义
```

而不是 implementation equality。

---

# 29. uniform logits 是另一个非常好的 sanity check

如果：

```text
z_1=z_2=\dots=z_V
```

那么：

[
p_i=\frac1V
]

所以任意 target 的 loss：

[
L
=

# -\log\frac1V

\log V
]

例如：

```text
V = 10
```

随机/均匀预测：

[
L\approx\log10\approx2.3026
]

如果：

```text
V = 32000
```

均匀分布：

[
L\approx\log32000\approx10.37
]

这个公式对 debug 特别有价值：

> 如果模型初始化后完全接近 uniform prediction，first loss 应该大概靠近 (\log V)。

当然真正随机初始化的 LM 并不一定严格 uniform，但这是一个很好的数量级 sanity check。

---

# 30. 这也解释了为什么不同 vocab 的绝对 loss 不能机械比较

假设两个完全随机模型：

```text
Model A:
V = 10K

Model B:
V = 100K
```

uniform baseline：

[
L_A=\log10000\approx9.21
]

[
L_B=\log100000\approx11.51
]

即使两者都：

```text
完全不会预测
```

loss 也天然不同。

所以：

```text
不同 tokenizer
不同 vocabulary
```

下比较绝对 cross-entropy 必须非常谨慎。

这正好承接前两章：

```text
Tokenizer
→ V

V
→ Embedding/LM head size

V
→ random/uniform CE baseline
```

tokenizer 继续影响着训练 metric。

---

# 31. perplexity 本质就是 geometric mean inverse probability

如果平均 token loss：

[
L
=

-\frac1N
\sum_t \log p_t
]

定义 perplexity：

[
\mathrm{PPL}=e^L
]

代入：

# [

\exp
\left(
-\frac1N\sum_t\log p_t
\right)
]

可以写成：

# [

\left(
\prod_t\frac1{p_t}
\right)^{1/N}
]

也就是说 perplexity 本质上是：

```text
每个真实 token inverse probability 的 geometric mean
```

直觉上：

```text
PPL = 10
```

常被粗略理解成：

> 模型平均像是在十个同等可能的候选项之间困惑。

这个解释不是严格等价于“每步真的有 10 个候选”，但作为 intuition 很有帮助。

---

# 32. perplexity 和 cross-entropy 没有新的信息

如果：

[
\mathrm{PPL}=e^L
]

那么：

```text
loss 知道了
```

就完全决定：

```text
perplexity
```

两者排序也完全一致。

所以 PPL 不是新的 training objective。

它只是把：

```text
nats/token
```

形式的 cross-entropy 做了 exponential transformation。

例如：

```text
loss = 2
```

PPL：

[
e^2\approx7.39
]

loss：

```text
3
```

PPL：

[
e^3\approx20.09
]

所以 PPL 的尺度会更加非线性。

---

# 33. 为什么不同 tokenizer 下 perplexity 也不能直接比

假设同一段中文：

```text
Tokenizer A:
100 tokens

Tokenizer B:
170 tokens
```

如果都按：

```text
mean loss per token
```

计算 perplexity，那么一个“token”对应的文本单位已经不同。

所以：

```text
PPL_A = 10
PPL_B = 8
```

并不能直接证明 B 是更好的语言模型。

tokenizer 改变：

```text
token granularity
vocabulary size
sequence length
```

也改变了 PPL 的 measurement unit。

这就是上一章 BPE 里说的：

> tokenizer 不稳定，后面 loss 和 architecture comparison 的基础就不稳定。

对于跨 tokenizer 比较，有时候：

```text
bits per byte
bits per character
```

之类更接近统一的文本级 measurement unit。

---

# 34. nats、bits 和 log base

A1 / PyTorch 默认使用：

```text
natural logarithm
```

所以 cross-entropy 单位可以称作：

```text
nats
```

如果使用：

[
\log_2
]

则单位是：

```text
bits
```

二者只是常数倍：

[
\log_2 x
========

\frac{\ln x}{\ln2}
]

所以：

[
\text{bits}
===========

\frac{\text{nats}}{\ln2}
]

深度学习框架通常使用 natural log，因此：

```text
perplexity = exp(loss)
```

而不是：

```text
2 ** loss
```

除非你的 loss 本身是在 bit unit 下计算的。

---

# 35. 交叉熵可以分解成 entropy + KL

对于真实 distribution (q) 与模型 distribution (p)：

[
H(q,p)
======

H(q)
+
D_{KL}(q|p)
]

其中：

[
H(q)
]

只由真实数据分布决定。

训练模型能改变的是：

[
D_{KL}(q|p)
]

所以最小化 cross-entropy 等价于：

```text
让模型 distribution p
逼近真实 data distribution q
```

在 hard one-hot supervised label 下，这个 decomposition 看起来有点抽象。

但到了：

```text
knowledge distillation
RL policy matching
teacher-student model
```

里面 target 不再一定是 one-hot，这个视角就会非常重要。

---

# 36. label smoothing 改变了 target distribution

普通语言模型 CE：

```text
target distribution:
one-hot
```

例如：

```text
cat:
1.0

其他 token:
0
```

label smoothing 会改成：

```text
cat:
1 - ε

其他 probability mass:
分散给其他 classes
```

PyTorch 当前 `CrossEntropyLoss` 也原生支持 `label_smoothing` 参数。

它的直觉是：

```text
不要要求模型把正确 class 学成绝对 1.0
```

可以降低过度 confidence。

但对于 decoder-only LM pretraining：

```text
普通 hard-target CE
```

仍然是非常标准的 baseline。

所以 A1 不需要擅自加：

```text
label smoothing
```

否则又改了 objective。

---

# 37. 训练 loss 和 sampling 不是同一阶段

训练时：

```text
logits
↓
cross entropy
↓
gradient
```

不需要：

```text
argmax
top-k
top-p
temperature sampling
```

这些 decoding 策略是 inference 阶段的事情。

训练 objective 关心的是：

[
p(y\mid x)
]

真实 token 获得了多大概率。

而生成时才要从：

[
p(\cdot\mid x)
]

中决定：

```text
怎么选一个 token
```

所以：

```text
training:
distribution matching

generation:
decision/sampling policy
```

这两个问题应该分开。

---

# 38. cross-entropy 为什么几乎处处可微

logits：

```text
任意实数
```

softmax：

```text
平滑函数
```

log-sum-exp：

```text
平滑函数
```

所以整个 loss：

[
L(z)
]

对 logits 可微。

然后：

```text
logits
↓
LM head
↓
Transformer
↓
Embedding
```

通过 chain rule，把 gradient 一直传回模型全部参数。

唯一不可微的东西是：

```text
target token ID
```

但它本来就不是需要优化的 parameter。

这也继续承接上一章：

```text
token ID:
离散 index

Embedding / hidden / logits:
连续可微空间
```

---

# 39. 为什么 backward 后 LM head 一定应该有 gradient

假设：

```text
hidden:
[N,D]

W_lm:
[V,D]

logits:
[N,V]
```

有：

[
z=hW^T
]

上面已经知道：

[
\frac{\partial L}{\partial z}
=============================

p-y
]

所以：

[
\frac{\partial L}{\partial W}
]

不会为零，除非处于非常特殊的完美状态。

因此 tiny test：

```python
loss.backward()

assert lm_head.weight.grad is not None
```

很有价值。

进一步，如果 input embedding 和 LM head 没有 tying，那么 embedding 仍然应该通过：

```text
Embedding
↓
Transformer
↓
LM head
↓
loss
```

获得 gradient。

如果没有：

```text
可能哪里 detach 了
```

或者 forward graph 被破坏了。

---

# 40. weight tying 后 gradient 路径会变成两条

上一章讨论：

```python
lm_head.weight = embedding.weight
```

之后，同一个矩阵同时扮演：

```text
input embedding
```

和：

```text
output classifier
```

那么它收到的 gradient 包含两部分：

```text
input path gradient
+
output LM-head gradient
```

也就是说：

```text
CrossEntropy
```

不仅更新 output representation。

还会直接塑造：

```text
shared token embedding space
```

这就是为什么 tying 不是简单：

```text
少存一份 matrix
```

它还改变 optimization dynamics。

---

# 41. 真实训练里还会出现 ignore_index / masking

A1 最小情况可以假设：

```text
每一个 target token 都参与 loss
```

但真实 batch 很可能存在：

```text
padding
prompt tokens 不计算 loss
packing boundary
masked region
```

于是会维护：

```text
loss mask
```

例如：

```text
targets:
[12, 43, -100, -100]
```

PyTorch 的 `CrossEntropyLoss` 默认：

```text
ignore_index = -100
```

可以把指定 target 从 loss/reduction 中排除。

对于 instruction tuning 经常看到：

```text
user prompt:
不算 loss

assistant response:
算 loss
```

本质就是对不同 token position 控制 CE 是否参与。

---

# 42. reduction 里的 denominator 也不能随便写

假设：

```text
100 个 positions
```

其中：

```text
30 个被 mask/ignore
```

正确 token mean 通常应该是：

[
\frac{
\text{70 个有效 token 的 loss sum}
}{
70
}
]

而不是：

[
\frac{
\text{loss sum}
}{
100
}
]

否则：

```text
padding 越多
loss 看起来越低
```

不同 sequence packing 策略就无法公平比较。

因此生产训练代码应该明确：

```text
loss_sum
valid_token_count
mean_loss = loss_sum / valid_token_count
```

尤其在 distributed training 中。

---

# 43. Distributed training 里正确平均 loss 也没有想象中简单

假设 GPU 0：

```text
有效 token = 1000
loss mean = 2
```

GPU 1：

```text
有效 token = 100
loss mean = 4
```

如果直接平均：

[
\frac{2+4}{2}=3
]

是不对的。

全局 per-token mean 应该：

[
\frac{
1000\times2+100\times4
}{
1100
}
]

约等于：

[
2.18
]

所以正确 aggregation 应该 all-reduce：

```text
loss_sum
valid_token_count
```

再做：

```text
global_loss_sum
/
global_token_count
```

而不是：

```text
mean of means
```

A1 单 GPU baseline 还不需要面对这个问题，但之后做 distributed training 时非常重要。

---

# 44. 为什么“loss 是 per-token mean”必须写进实验日志

假设实验 A：

```text
batch = 8
seq = 512
```

实验 B：

```text
batch = 2
seq = 2048
```

两边都是：

```text
4096 tokens / batch
```

如果 loss 是：

```text
token sum
```

其绝对值会跟 token 数量线性变化。

而：

```text
token mean
```

才更适合跨 batch shape 比较。

这也是为什么实验记录最好明确写：

```text
train_loss:
mean negative log-likelihood per valid token
```

而不是模糊写：

```text
loss = 3.1
```

---

# 45. loss 本身和 sequence length 没有直接线性关系

如果 reduction 是：

```text
mean over tokens
```

那么：

```text
T = 128
```

和：

```text
T = 2048
```

并不会仅因为 sequence 更长就把 loss 放大 16 倍。

但是 longer context 会改变：

```text
模型可利用的 conditioning information
```

所以实际 prediction difficulty 可能变化。

这里要区分：

```text
reduction scale
```

与：

```text
modeling difficulty
```

前者是数学定义。

后者是模型能力。

---

# 46. 为什么 validation loss 必须 `model.eval()` 但又不是因为 CE 自己

Cross-entropy 本身没有：

```text
training mode
```

但整个 model 可能有：

```text
dropout
```

或者其他 train/eval 行为。

所以 validation 通常：

```python
model.eval()

with torch.no_grad():
    ...
```

然后再算同样的 CE。

这里：

```text
training loss
validation loss
```

最好使用完全相同的 objective/reduction。

区别只来自：

```text
data split
model mode
是否更新参数
```

而不是换一个 metric definition。

---

# 47. cross-entropy 为什么在大 vocabulary 下会突然变成显存问题

上一章已经算过：

```text
hidden:
[B,T,D]

LM head:
[D,V]

logits:
[B,T,V]
```

假设：

```text
N = B*T
```

则 logit matrix：

[
[N,V]
]

元素数量：

[
NV
]

当：

```text
N = 16384
V = 150000
```

得到：

[
2.4576\times10^9
]

个 logits。

BF16：

```text
约 4.9 GB
```

FP32：

```text
约 9.8 GB
```

而 cross-entropy 最后输出的却只是：

```text
每个 token 一个 scalar
```

甚至最终 reduction 后：

```text
一个 scalar loss
```

于是产生一个非常明显的问题：

> **为了最后求一个 loss，我们真的有必要把完整 `[N,V]` logits 写进 GPU global memory 吗？**

---

# 48. Cut Cross-Entropy：把上一章和这一章真正接起来

2024 年的 Cut Cross-Entropy（CCE）工作就是针对这个问题。

作者观察到标准语言模型：

```text
hidden
↓
LM head matrix multiplication
↓
巨大 logits tensor
↓
cross entropy
```

会 materialize：

[
[N,V]
]

中间结果。

但 CE 真正需要的是：

```text
1. target logit
2. 所有 logits 的 log-sum-exp
```

并不需要把整个 matrix 长时间存下来。

CCE 因此把：

```text
linear projection
+
log-sum-exp
+
target selection
```

融合起来，在片上更局部地计算，不把完整 logits 写入 global memory。

论文在 Gemma 2 2B 的例子里报告，loss computation 的显存占用可以从约 24 GB 降到约 1 MB，classifier head 的总 training-time memory 从约 28 GB 降到约 1 GB。

这就是一个特别漂亮的：

```text
A1 数学公式
↓
现代 LLM system optimization
```

案例。

---

# 49. 为什么 CCE 和 FlashAttention 的思想很像

普通 attention：

```text
QKᵀ
↓
[N,N] attention matrix
↓
softmax
↓
乘 V
```

FlashAttention 的核心思想之一就是：

```text
不要把巨大中间 attention matrix
反复写到 HBM
```

而是利用：

```text
tiling
online softmax
local memory
```

完成结果。

CCE 做的事情非常类似：

```text
hidden × vocab weight
↓
不要 materialize 巨大 [N,V]
↓
边算边做 log-sum-exp / CE
```

共同思想是：

> **数学上需要某个巨大中间矩阵，并不代表系统实现必须把它完整存进 global memory。**

这可能是 CS336 最重要的系统直觉之一。

---

# 50. 更有意思的是：到 2026 年它已经进入 PyTorch

截至 2026 年的 PyTorch 2.13 文档里，已经可以看到：

```text
torch.nn.LinearCrossEntropyLoss
```

以及：

```text
torch.nn.functional.linear_cross_entropy
```

官方 API。

它的输入不再必须是：

```text
完整 logits
```

而可以把：

```text
input features
linear weight
target
```

交给融合后的 linear-cross-entropy 实现。

当前文档还明确提供了 chunked implementation 选项，用来减少 memory usage。

这个变化非常值得记录。

因为我在 A1 里实现：

```python
cross_entropy(logits, targets)
```

学习的是：

```text
数学 contract
```

而工业框架 2026 年正在进一步把这个 API 边界改成：

```text
hidden + classifier weight + targets
```

原因就是：

> 原先 `logits` 这个中间 tensor 的 materialization 本身可能已经成为性能问题。

---

# 51. 这也解释了为什么 abstraction 有时会“漏”

最干净的软件 abstraction 是：

```text
LM head
负责输出 logits

CrossEntropy
负责消费 logits
```

两者完全独立。

这很好理解，也很好组合。

但是系统层发现：

```text
模块边界正好要求 materialize 巨型 tensor
```

于是为了效率：

```text
把两个 abstraction fuse
```

变成：

```text
LinearCrossEntropy
```

这和前面课程一直强调的：

```text
abstraction is useful
but abstraction can leak
```

非常一致。

数学/架构层：

```text
分开理解
```

kernel/system 层：

```text
必要时融合执行
```

两者并不矛盾。

---

# 52. 为什么 A1 仍然应该先实现普通 CE

既然 2026 已经有：

```text
LinearCrossEntropy
Cut Cross-Entropy
```

为什么不直接从这些学起？

因为不先理解：

[
L
=

\operatorname{LSE}(z)-z_y
]

就很难真正理解 CCE 到底省掉了什么。

CCE 并没有换 objective。

它仍然精确计算同一个：

```text
cross-entropy
```

只是改变：

```text
execution schedule
memory traffic
intermediate materialization
```

所以学习顺序非常合理：

```text
A1:
先把 reference math 写对

A2 / modern systems:
再把同一个 math 跑快
```

---

# 53. approximate softmax 是另一条完全不同的路线

历史上面对超大 vocabulary，还有：

```text
hierarchical softmax
sampled softmax
noise contrastive estimation
adaptive softmax
```

等方案。

它们通常试图减少：

[
O(V)
]

的计算，例如只计算部分 vocabulary，或者构造 hierarchy。

经典 Adaptive Softmax 就是利用词频高度不均衡这一性质，把 vocabulary 分组，让常见词的计算更便宜。

但这和 CCE 的理念不同。

很多 approximate method 是：

```text
改变计算目标/近似 full softmax
```

CCE 更强调：

```text
保持 exact CE objective
但不 materialize 巨型 logits
```

这对现代 GPU 和大 vocab LLM 很有吸引力。

---

# 54. 为什么今天又更倾向保留 full vocabulary objective

早期 neural LM：

```text
百万词级 word vocabulary
```

使 full softmax 极其昂贵。

现代 BPE / SentencePiece：

```text
几十 K
到十几万 token
```

虽然仍然很大，但 GPU GEMM 已经极其高效。

所以相比复杂 approximate objective：

```text
直接算 exact full softmax
```

变得更加现实。

今天的新问题反而常常是：

```text
计算虽然能做
但中间 logits 太占显存
```

于是出现 CCE 这种：

```text
不改变 exact objective
只优化 memory movement
```

的路线。

这也是硬件变化如何反过来改变算法 engineering trade-off 的一个例子。

---

# 55. mixed precision 下 softmax / CE 更值得小心

现代 LLM 训练常用：

```text
BF16
FP16
```

而不是所有东西 FP32。

低精度意味着：

```text
exponent range
mantissa precision
```

更有限。

softmax/logsumexp 又正好涉及：

```text
exp
sum
log
```

这些容易受范围和精度影响的运算。

PyTorch 当前 AMP 文档就明确描述了 mixed precision 会让不同操作根据 numerical suitability 使用不同精度。

所以“减最大值”并不是：

```text
FP32 时代的老技巧
```

反而在 mixed precision 训练里更加重要。

---

# 56. attention softmax 和 vocabulary softmax 是同一个数学 primitive

这一章实现：

```text
softmax(logits)
```

后，下一次很快会在 attention 里看到：

[
\operatorname{softmax}
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)
]

数学形式完全相同。

区别只是 softmax 维度代表的含义：

### LM output

```text
softmax over vocabulary
```

回答：

```text
下一个 token 是谁？
```

### Attention

```text
softmax over key positions
```

回答：

```text
当前位置应该关注哪些历史 token？
```

所以 softmax 本身是一个通用：

```text
score → normalized competition
```

primitive。

---

# 57. 为什么 attention 还要除以 (\sqrt d)

这个问题应该留到 attention 篇详细讲。

但这一章已经可以提前看到原因。

如果 (Q,K) 每个 component 大致：

```text
variance ≈ 1
```

那么：

[
Q\cdot K
]

随着：

```text
head_dim
```

增大，其 variance 会增大。

logits scale 太大时：

```text
softmax
```

会变得非常尖：

```text
接近 one-hot
```

gradient 也可能进入不好的区域。

因此 scaled dot-product attention：

[
\frac{QK^T}{\sqrt{d_k}}
]

本质是在控制：

```text
softmax 输入 logits 的尺度
```

也就是说：

> Linear 初始化、RMSNorm、attention scaling、softmax stability 并不是互不相关的章节。

它们都在共同控制模型中的数值尺度。

---

# 58. softmax saturation 是什么意思

例如：

```text
logits:
[100, 0, 0]
```

softmax 几乎：

```text
[1, 0, 0]
```

这叫非常：

```text
peaked / saturated
```

如果最大 token 恰好正确：

```text
gradient 很小
```

如果最大 token 错误：

```text
正确 token 有很强负梯度
错误最大 token 有很强正梯度
```

所以 cross-entropy 相比某些 sigmoid saturation 情况其实仍然能提供明显 corrective signal。

但 logits 规模过大仍然可能给训练带来：

```text
数值稳定
optimization
confidence calibration
```

等问题。

因此控制 logit scale 依然重要。

---

# 59. z-loss 在解决另一类 logit scale 问题

一些大型模型训练配方会添加类似：

```text
z-loss
```

的辅助项，约束：

[
\log\sum_j e^{z_j}
]

不要无限漂移到很大的 magnitude。

原因在于 softmax 对：

```text
所有 logits 同时 + c
```

完全不敏感。

也就是说普通 CE 存在一个：

```text
common-shift direction
```

在概率意义上没有区别。

z-loss 可以对这个自由度施加额外控制。

不过：

```text
A1 baseline
```

不需要加入这种额外 regularization。

值得知道它的意义即可：

> 有些现代 loss modification 不是改变“正确 token 应该高概率”这一目标，而是在控制 logits 的 numerical scale。

---

# 60. calibration 与 perplexity 也不是完全同一个问题

一个模型可能：

```text
PPL 更低
```

但：

```text
confidence calibration 不一定更好
```

calibration 问的是：

> 模型说 80% confidence 的事件，长期来看是不是大约 80% 真的发生？

而 CE/PPL 更关心：

```text
真实 token 的整体 log likelihood
```

cross-entropy 是 proper scoring rule，因此与概率质量有关，但现代模型的 calibration 仍然会受到：

```text
temperature
post-training
RLHF
distribution shift
```

等因素影响。

所以：

```text
low perplexity
```

不能简单翻译成：

```text
所有概率都完美可信
```

---

# 61. pretraining CE 也不等于最终 downstream quality

这是做 TinyStories / OWT 实验时特别应该记住的。

validation CE 衡量：

```text
next-token prediction
```

而最终我们可能关心：

```text
reasoning
coding
instruction following
tool use
factuality
```

它们通常与好的 pretraining loss 有关系，但不是一一对应。

同样 validation loss：

```text
architecture A
architecture B
```

可能在：

```text
generation quality
long-context
reasoning
```

上表现不同。

所以 Architecture Lab 里：

```text
validation CE
```

应该是最基础、最干净的统一指标。

但不是唯一最终指标。

---

# 62. 为什么 A1 baseline 里 CE 仍然是最好的架构比较起点

尽管有上面的限制，在固定：

```text
tokenizer
training data
token budget
parameter budget
optimizer
schedule
```

下：

```text
validation token CE
```

仍然非常适合比较基础架构。

因为它：

```text
连续
稳定
无需生成 decoding
直接对应 training objective
样本效率高
```

相比：

```text
跑一小批生成
然后凭肉眼觉得“更聪明”
```

靠谱得多。

所以后面比较：

```text
MHA
GQA
MLA
SwiGLU variants
RoPE variants
```

首先还是看：

```text
held-out per-token CE
```

再补其他能力评估。

---

# 63. 一个 tiny vocabulary 可以手算整条路径

调试时可以故意构造：

```text
V = 3
```

logits：

[
[0,0,0]
]

target：

```text
1
```

softmax：

[
\left[
\frac13,
\frac13,
\frac13
\right]
]

loss：

[
-\log\frac13
============

\log3
\approx1.0986
]

gradient：

[
p-y
]

所以：

[
\left[
\frac13,
-\frac23,
\frac13
\right]
]

也就是：

```text
class 0:
+0.333

target class 1:
-0.667

class 2:
+0.333
```

这样一个例子已经能同时验证：

```text
softmax
CE
target indexing
backward direction
```

比一上来跑 TinyStories 有用得多。

---

# 64. 再手算一个模型非常自信但预测错的情况

假设：

```text
target = class 1
```

但：

```text
p =
[0.98, 0.01, 0.01]
```

loss：

[
-\log0.01
\approx4.605
]

gradient：

[
p-y
]

得到：

[
[0.98,-0.99,0.01]
]

所以：

```text
错误 class 0:
被强烈压低

正确 class 1:
被强烈抬高

无关 class 2:
只有微小更新
```

这非常直观地说明：

> CE 并不是只盯着 target token，它同时在重排整个 vocabulary distribution。

---

# 65. 如果模型非常自信且正确

假设：

```text
target = class 1
```

同时：

```text
p =
[0.01, 0.98, 0.01]
```

loss：

[
-\log0.98
\approx0.0202
]

gradient：

[
[0.01,-0.02,0.01]
]

已经非常小。

所以在训练后期：

```text
大量 easy tokens
```

可能贡献极小 gradient。

真正的训练 signal 越来越集中在：

```text
模型仍然不确定
或者预测错误
```

的位置。

这个 intuition 后面理解：

```text
hard example mining
token-level difficulty
data selection
```

也会有帮助。

---

# 66. token-level loss 本身就是一种“样本难度”

对 token (t)：

[
L_t=-\log p_t
]

如果：

```text
p_t = 0.9
```

loss：

```text
≈ 0.105
```

如果：

```text
p_t = 0.01
```

loss：

```text
≈ 4.605
```

所以 per-token CE 可以直接看成：

```text
模型觉得这个 token 有多 surprising
```

这和 information theory 里的：

```text
surprisal
```

完全对应。

高 loss token：

```text
模型很意外
```

低 loss token：

```text
模型早就猜到了
```

---

# 67. cross-entropy 也是数据压缩问题

如果模型给 token：

[
x_t
]

概率：

[
p(x_t)
]

理想 entropy coding 所需的编码长度大约：

[
-\log_2p(x_t)
]

bits。

所以 language model loss 其实有非常直接的数据压缩解释：

```text
预测越准确
→
文本理论上越容易被压缩
```

平均 cross-entropy：

```text
bits/token
```

就是模型对数据的一种 compression performance。

这也让第一篇 BPE 的：

```text
tokenization compression
```

和第三篇的：

```text
probabilistic compression
```

形成一个很有意思的联系。

---

# 68. BPE compression 与 LM compression 是两层不同的压缩

BPE：

```text
raw bytes
↓
更少的 discrete symbols
```

依赖：

```text
固定 vocabulary / merge rules
```

LM：

```text
token sequence
↓
predictive probabilities
```

依赖：

```text
context-dependent statistical model
```

所以可以粗略理解：

```text
BPE:
静态字典压缩

Language Model:
上下文概率压缩
```

前者决定：

```text
文本被表示成多少 token
```

后者决定：

```text
这些 token 有多难预测
```

这两个东西共同影响最终计算效率和模型 quality。

---

# 69. 为什么 tokenizer 不同会同时改变两层压缩

Tokenizer A：

```text
更长 token
更短 sequence
```

可能有：

```text
更大 vocab
```

于是 next-token prediction 每一步面对更多 class。

Tokenizer B：

```text
更短 token
更长 sequence
```

每步 vocabulary 可能更小，但要预测更多步。

所以 architecture / tokenizer joint design 本质上在平衡：

```text
每步预测难度
×
总 prediction steps
×
output vocabulary cost
```

这再次说明：

> tokenizer 并不是模型外一个可以完全独立优化的预处理模块。

---

# 70. A1 官方 tests 当前具体覆盖了什么

当前 Stanford A1 的 `test_nn_utils.py` 对这一部分测试得其实相当直接。

softmax：

```text
1. 和 F.softmax 对齐
2. x + 100 后仍保持相同结果
```

cross-entropy：

```text
1. 将 [B,T,V] flatten 成 [BT,V]
2. 和 F.cross_entropy 对齐
3. logits × 1000 后仍和 reference 对齐
```

这些行为在当前官方 test 文件中都可以直接看到。

所以官方 contract 重点是：

```text
数学正确
+
数值稳定
```

而不是复杂 API。

---

# 71. 我自己的 softmax 测试应该再加什么

除了官方 reference comparison，我会增加几个 property tests。

### 概率和为 1

```python
p = softmax(x, dim=-1)

assert torch.allclose(
    p.sum(dim=-1),
    torch.ones_like(p[..., 0]),
)
```

---

### 非负

```python
assert (p >= 0).all()
```

---

### 平移不变

```python
softmax(x)
≈
softmax(x + 12345)
```

---

### uniform input

```text
x 全相同
→
p ≈ 1/V
```

---

### ordering

如果：

```text
x_i > x_j
```

应该：

```text
p_i > p_j
```

这些都是比“给一个 fixture 得到某组数字”更通用的不变量。

---

# 72. 我自己的 CE 测试应该加什么

### uniform baseline

```text
zero logits
→
loss ≈ log(V)
```

---

### target-logit monotonicity

```text
只提高 target logit
→
loss 下降
```

---

### wrong-logit monotonicity

```text
只提高某个错误 class
→
loss 不应下降
```

---

### shift invariance

因为：

[
\operatorname{CE}(z+c,y)
========================

\operatorname{CE}(z,y)
]

所以：

```python
ce(logits, y)
≈
ce(logits + 10000, y)
```

---

### gradient

tiny case：

```text
gradient
≈
softmax(logits) - one_hot(target)
```

这几乎能把实现的数学语义完全锁死。

---

# 73. gradient test 可以直接做解析比较

例如：

```python
logits = torch.randn(
    4,
    7,
    requires_grad=True,
)

targets = torch.tensor([1, 3, 2, 6])

loss = cross_entropy(
    logits,
    targets,
)

loss.backward()
```

如果 reduction 是 mean，那么理论 gradient：

[
\frac1N
(p-y)
]

所以可以自己构造：

```python
expected = softmax(
    logits.detach(),
    dim=-1,
)

expected[
    torch.arange(N),
    targets
] -= 1

expected /= N
```

然后：

```python
assert_allclose(
    logits.grad,
    expected,
)
```

这是一个非常有教育意义的 test。

---

# 74. finite difference 也可以验证 autograd

选择某个：

```text
logit z_k
```

用：

[
\frac{
L(z_k+\epsilon)
---------------

L(z_k-\epsilon)
}{
2\epsilon
}
]

近似：

[
\frac{\partial L}
{\partial z_k}
]

然后和：

```python
autograd
```

结果比较。

A1 不要求自己实现 autograd。

但做一次 finite-difference gradient check，可以非常直观地理解：

> PyTorch backward 到底在帮我算什么。

---

# 75. 为什么 tiny CPU case 比直接跑 GPU 更适合 debug

这一章没有任何操作必须依赖 GPU。

甚至：

```text
V = 3
B = 1
T = 2
```

往往比：

```text
TinyStories
CUDA
mixed precision
完整 Transformer
```

更适合发现 bug。

因为小 case 可以：

```text
手算 probability
手算 target
手算 loss
手算 gradient
```

如果直接训练：

```text
loss 不降
```

潜在原因可能有几十个：

```text
Tokenizer
Embedding
RoPE
mask
attention
FFN
optimizer
lr
data
shift
CE
```

tiny unit test 能把变量迅速缩到：

```text
softmax / CE 本身
```

---

# 76. `NaN` 出现时应该往哪查

如果训练突然：

```text
loss = NaN
```

这一章给出第一套排查链：

```text
logits 是否已经 NaN/Inf？
↓
softmax/logsumexp 是否稳定？
↓
hidden state 是否爆了？
↓
attention score 是否爆了？
↓
gradient 是否爆了？
↓
learning rate / initialization 是否异常？
```

如果：

```text
logits 本身已经 Inf
```

那就不是 CE 单独的问题。

stable CE 只能解决：

```text
有限但很大的 logits
```

不能把：

```text
输入已经 NaN
```

恢复正常。

所以 debugging 要检查：

```text
first non-finite tensor
```

而不是最后看到 loss NaN 就只怪 loss。

---

# 77. 这一章开始能理解“numerical stability 是端到端属性”

Linear initialization：

```text
控制 activation scale
```

RMSNorm：

```text
控制 hidden norm
```

attention scaling：

```text
控制 QK logits
```

softmax：

```text
避免 exp overflow
```

gradient clipping：

```text
控制 backward norm
```

mixed precision：

```text
限制可表示数值范围
```

这些不是独立的 patch。

它们共同构成：

```text
整个 Transformer 的 numerical system
```

所以 A1 把这些组件分开实现，最终又会在完整训练中重新连接起来。

---

# 78. 为什么这篇和下一篇 RMSNorm 是自然相连的

这一章最后关心的是：

```text
logits scale
softmax scale
gradient scale
```

下一章 RMSNorm 问的是：

```text
hidden state scale 如何控制？
```

SwiGLU 又会问：

```text
FFN activation 如何改变分布？
```

所以完整的数据流是：

```text
hidden
↓ RMSNorm
controlled scale
↓ Linear
Q/K/V or FFN activations
↓ ...
hidden
↓ LM head
logits
↓ stable CE
loss
```

这也是我现在更愿意按“数值传播”而不是“模块 API”理解 Transformer 的原因。

---

# 79. 当前 baseline 的最小实现可以非常短

softmax：

```python
def softmax(
    x: torch.Tensor,
    dim: int,
) -> torch.Tensor:
    max_value = x.max(
        dim=dim,
        keepdim=True,
    ).values

    exp_x = torch.exp(
        x - max_value
    )

    return (
        exp_x
        /
        exp_x.sum(
            dim=dim,
            keepdim=True,
        )
    )
```

cross-entropy 可以概念上写成：

```python
def cross_entropy(
    logits: torch.Tensor,
    targets: torch.Tensor,
) -> torch.Tensor:
    max_logits = logits.max(
        dim=-1,
        keepdim=True,
    ).values

    shifted = logits - max_logits

    log_normalizer = (
        max_logits.squeeze(-1)
        +
        torch.log(
            torch.exp(shifted).sum(
                dim=-1
            )
        )
    )

    target_logits = logits.gather(
        dim=-1,
        index=targets.unsqueeze(-1),
    ).squeeze(-1)

    return (
        log_normalizer
        -
        target_logits
    ).mean()
```

也可以直接围绕：

```text
torch.logsumexp
```

组织。

真正重要的不是最后到底写成几行。

而是我能解释每一个操作为什么存在。

---

# 80. 我会刻意避免在 CE 内构造 one-hot

targets：

```text
[N]
```

只需要拿：

```text
每行 target class 对应的一个 logit
```

因此：

```python
logits[
    torch.arange(N),
    targets,
]
```

或者：

```python
gather
```

就足够。

没必要创建：

```text
[N,V]
```

one-hot matrix。

对于：

```text
N = 16K
V = 150K
```

那又是一个巨大 tensor。

这也是一个很好的系统习惯：

> 如果数学公式写了一个 object，不代表程序里一定要 materialize 它。

---

# 81. 这一原则已经连续出现三次

### Embedding

数学：

```text
one-hot × E
```

实现：

```text
直接 lookup
```

---

### Cross entropy

数学：

```text
one-hot target distribution
```

实现：

```text
直接 gather target logit
```

---

### Cut Cross-Entropy

数学：

```text
完整 [N,V] logits
```

优化实现：

```text
边做 projection 边做 reduction
```

这三件事情背后其实是同一个思想：

> **不要把数学表示机械映射成物理内存里的 dense tensor。**

这大概是到目前为止 A1 最值得留下的系统直觉之一。

---

# 82. 如果以后自己做 mini-LLM，loss 侧也可以做 ablation

baseline 应该保持：

```text
standard next-token CE
```

但超纲实验里可以研究：

```text
label smoothing
z-loss
token weighting
confidence regularization
distillation KL
focal-style weighting
```

不过一定要区分：

```text
architecture change
```

和：

```text
objective change
```

例如：

```text
Model A:
MHA + CE

Model B:
GQA + CE + z-loss
```

最后 B 更好，不能归因给：

```text
GQA
```

所以和 initialization 一样：

> 做 architecture ablation 时，loss recipe 也应该保持固定。

---

# 83. 未来做 reasoning/RL 时还会再次遇到 log-probability

预训练：

```text
cross entropy
```

需要：

[
\log p(y\mid x)
]

SFT：

```text
仍然是 token-level CE
```

DPO：

```text
比较 chosen / rejected response 的 log-probability
```

policy gradient / PPO / GRPO 一类 RL：

```text
继续需要 policy token log-probability
```

KL regularization：

```text
继续比较两个 token distributions
```

所以这章的：

```text
logits
softmax
log-prob
cross entropy
```

并不是只在 A1 出现一次。

它几乎会贯穿：

```text
pretraining
post-training
distillation
RL
evaluation
```

整个 LLM pipeline。

---

# 84. 甚至 2026 年 RL 系统也在重新碰到大 vocab CE 的显存问题

随着长 trajectory 的 RL 和大 vocabulary 模型出现：

```text
rollout token 数量巨大
```

如果训练侧重新计算每个 token 的：

```text
full vocabulary logits
```

显存成本同样高。

2026 年的一些 RL 工作已经明确把 Cut Cross-Entropy 当成减少大 vocabulary log-probability / loss 内存的一部分。

这再次说明：

```text
A1 的 cross-entropy
```

绝对不是“入门以后就再也不用管”的东西。

---

# 85. 当前 baseline 完成后，我至少应该能回答这些问题

这一章结束后，我希望自己能不看代码回答：

1. logits 为什么可以是任意实数？
2. softmax 为什么一定要指定 dimension？
3. 为什么 `softmax(x+c)=softmax(x)`？
4. 为什么 stable softmax 要减 maximum？
5. 为什么 underflow 通常比 overflow 更可接受？
6. 为什么训练 CE 应该直接吃 logits，而不是 probability？
7. cross-entropy 为什么可以写成 `logsumexp - target_logit`？
8. causal LM 为什么需要 target shift？
9. target shift 和 causal mask 有什么不同？
10. uniform logits 为什么得到 `loss = log(V)`？
11. softmax + CE 的 gradient 为什么是 `p-y`？
12. perplexity 和 loss 有什么严格关系？
13. 为什么不同 tokenizer 的 PPL 不适合直接横比？
14. 为什么 large vocab 下 CE 会成为显存问题？
15. Cut Cross-Entropy 到底省掉了哪一个 tensor？
16. 为什么 2026 PyTorch 会增加 `LinearCrossEntropyLoss`？
17. 为什么“数学上存在某个 dense tensor”不意味着程序里应该真的把它创建出来？

如果这些都能讲明白，就不仅是“会写 CE”了。

---

# 86. 当前 baseline 的验收清单

我会把这一章的 baseline 验收分成四层。

### 数学正确性

```text
softmax 与 reference 对齐
CE 与 reference 对齐
```

### Numerical stability

```text
x + large constant 不变
large logits 不 NaN / Inf
log-sum-exp 使用稳定形式
```

### Shape semantics

```text
softmax 沿正确 dimension
[B,T,V] → [BT,V]
targets [B,T] → [BT]
```

### Language-model semantics

```text
input / target shift 正确
loss 是 valid-token mean
backward 能传到 LM head / Transformer / Embedding
```

官方测试覆盖其中最核心的数学与数值部分；A1 仓库要求学生通过 adapter 将自己的实现接到统一测试，而当前 softmax/CE fixture 也直接与 PyTorch reference 对齐。

---

# 87. 从这篇开始，“loss 下降”终于有明确含义了

前两章写完：

```text
Tokenizer
Linear
Embedding
```

都还只能说明：

```text
模型能表示数据
模型能做 forward
```

写完这一章后第一次拥有一个 scalar：

```text
loss
```

它告诉我：

```text
模型给真实下一个 token
分配了多少概率
```

从此以后：

```text
optimizer
learning rate
architecture
data quality
scaling law
```

所有实验最终都可以投影到：

```text
这个 probability objective 有没有改善？
```

所以 cross-entropy 是整个训练闭环真正闭合的地方。

---

# 88. 小结

这一章从一个看起来非常简单的公式开始：

[
p_i
===

\frac{e^{z_i}}
{\sum_j e^{z_j}}
]

最终得到：

[
L
=

## \operatorname{logsumexp}(z)

z_y
]

以及更加重要的：

[
\boxed{
\nabla_z L
==========

p-y
}
]

从 A1 的角度看，需要掌握的是：

```text
logits
↓
stable softmax
↓
target probability
↓
negative log likelihood
↓
token mean loss
```

从语言模型的角度看，它对应：

[
-\log
p(x_{t+1}\mid x_{\le t})
]

从数值计算的角度看，关键是：

```text
subtract max
log-sum-exp
避免不必要的 probability materialization
```

从系统角度看，到了大 vocabulary：

```text
[B,T,V]
```

这个 logits tensor 本身又会成为巨大开销。

于是 Cut Cross-Entropy 进一步把：

```text
LM head
+
log-sum-exp
+
target gathering
```

融合执行；到了 2026 年，PyTorch 2.13 甚至已经提供正式的 `LinearCrossEntropyLoss` / `linear_cross_entropy` API 来支持这一方向。

所以现在我对 softmax / cross-entropy 的理解已经不再是：

> “分类任务最后套一个 softmax，再算 CE。”

而更接近：

> **softmax 把相对 score 转成竞争性的概率分布；cross-entropy 用 maximum likelihood 训练这个分布，而 stable log-sum-exp 和 fused execution 则让同一个数学目标能够真正扩展到十几万 vocabulary 和大规模 GPU 训练。**

更有意思的是，到这一章为止，前三篇已经形成了一条完整链路：

```text
BPE
决定模型操作什么离散单位
        ↓
Embedding
把离散 ID 送进连续空间
        ↓
Transformer
计算 contextual representation
        ↓
LM head
重新投影到 vocabulary
        ↓
Softmax + Cross Entropy
衡量下一个 token 是否预测正确
```

接下来继续往 Transformer 内部走。

下一章处理所有 residual block 都高度依赖的数值尺度，以及现代 decoder-only LLM 中最常见的 FFN 形式：

**RMSNorm、SiLU 与 SwiGLU。**

[上一章：Linear / Embedding](/blog/2026/2026-08-15-cs336-a1-linear-embedding/)

[下一章：RMSNorm / SiLU / SwiGLU](/blog/2026/2026-08-15-cs336-a1-rmsnorm-silu-swiglu/)
