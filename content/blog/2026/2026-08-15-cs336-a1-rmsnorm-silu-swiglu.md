---
schema: bubblevan/v1
id: blog-20260815-cs336-a1-rmsnorm-silu-swiglu
content_kind: blog
title: CS336 A1 复盘四：RMSNorm、SiLU 与 SwiGLU
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 复盘现代 decoder-only Transformer 中的 RMSNorm 和 gated FFN，重点关注数值范围、dtype、残差流和参数量。
topics: [CS336, RMSNorm, SiLU, SwiGLU, Transformer]
projects: [cs336]
aliases: []
authors: [bubblevan]
---

在我的 notebook 里，RMSNorm 和 SwiGLU 很容易被写成两个独立模块；重新对照 A1 后，我更愿意把它们看作同一个问题的两面：如何让 residual stream 在深层网络中保持可训练，同时让 FFN 有足够的非线性表达能力。

## 1. RMSNorm 处理的是 hidden state 的尺度

对最后一维 hidden state，RMSNorm 先计算均方根尺度，再用可学习 gain 恢复每个维度的表达：

```text
RMS(x) = sqrt(mean(x^2) + eps)
y_i = g_i * x_i / RMS(x)
```

它和 LayerNorm 的区别是没有减去均值，因此不显式去除 mean，只对 root mean square 做缩放。A1 baseline 使用 RMSNorm，并把它放在 attention 和 FFN 之前形成 pre-norm block。

## 2. dtype 是 RMSNorm 的实际难点

A1 handout 特别要求先把输入 upcast 到 float32，再执行平方、平均和开方，最后转换回输入 dtype。原因是低精度下平方和累积更容易产生溢出或精度损失。

因此 RMSNorm 的 contract 不只是 shape：

```text
input:  [..., D], dtype = input_dtype
compute: float32
output: [..., D], dtype = input_dtype
```

参数 gain 的 device、dtype 也必须和 module 构造保持一致。这个模块很小，却是第一个让我必须同时考虑数学、数值稳定性和 PyTorch module 语义的地方。

## 3. pre-norm 和 residual stream

A1 的 Transformer block 采用 pre-norm：

```text
z = x + Attention(RMSNorm(x))
y = z + FFN(RMSNorm(z))
```

这里的 residual stream 可以理解成跨层传递的主通道。Norm 负责在进入子层前控制输入尺度，residual add 则保留一条相对直接的信息和梯度路径。

后面的消融实验会比较不使用 RMSNorm、以及改成 post-norm 的情况。那时真正要观察的不是“哪段代码更短”，而是 loss 曲线、梯度范数和训练稳定性如何变化。

## 4. SiLU 是 gated FFN 的基础

SiLU/Swish 的形式是：

```text
SiLU(x) = x * sigmoid(x)
```

它比 ReLU 平滑，在负数区域仍保留连续的非零响应。A1 允许直接使用稳定的 sigmoid 相关实现，重点是把 activation 语义固定下来。

单独看 SiLU，它只是一个逐元素函数；放进 SwiGLU 后，它会成为一条 gated pathway 的非线性部分。

## 5. SwiGLU 的三矩阵结构

A1 的 FFN 使用三个 bias-free weight：

```text
h = SiLU(W1 x) elementwise_mul (W3 x)
y = W2 h
```

其中 W1 和 W3 都把 hidden dimension 投影到 d_ff，W2 再投影回 d_model。可以把它理解成：

- W1 pathway 提供经过 SiLU 的内容；
- W3 pathway 提供 gate；
- elementwise multiplication 决定哪些中间维度被放大或抑制；
- W2 把 gated representation 合并回 residual stream。

相比传统两层 ReLU MLP，SwiGLU 多了一条线性 pathway，因此参数量和 d_ff 的选择必须一起考虑。A1 建议 d_ff 约为 8/3 * d_model，并向硬件友好的 64 的倍数取整。

## 6. 为什么不能只比较 d_model

FFN 往往是 Transformer block 参数和计算的主要来源之一。改变 d_ff 会同时改变：

- W1、W2、W3 的参数量；
- 每个 token 的矩阵乘法量；
- 激活内存；
- 梯度和 optimizer state；
- 训练速度。

因此之后比较 SwiGLU 与 SiLU FFN 时，应该尽量匹配参数量。A1 的消融要求 SiLU baseline 使用约 4 * d_model 的 inner dimension，以抵消它只有两张 weight matrix 的差异。

## 7. 官方测试和迁移检查

官方测试会分别验证 RMSNorm、SiLU 和 SwiGLU，并通过给定权重的 snapshot 检查数值结果。迁移 notebook 代码时需要重点核对：

- RMSNorm 是否只沿最后一维归一化；
- RMSNorm 是否在平方前 upcast；
- 输出是否恢复原 dtype；
- SwiGLU 三张 weight 的方向是否一致；
- gate 是逐元素乘法，而不是矩阵乘法；
- d_ff 是接口参数还是在 module 内被悄悄改写；
- state dict key 是否能被 adapter 加载。

除了 snapshot，还应该做一个 tiny numerical check：输入尺度整体放大后，RMSNorm 输出尺度不应同样放大；输入为零时，结果不应出现 NaN。

## 8. baseline 到 architecture lab 的连接

这一章完成后，后续 architecture lab 可以自然加入：

- QK-Norm：只归一化 attention 的 Q/K；
- dense SiLU：移除 gate 并匹配参数量；
- MoE FFN：把一个 dense FFN 替换成多个 routed FFN；
- shared expert：增加一条所有 token 都经过的共享路径；
- zero-compute expert：研究动态计算分配。

但这些变量必须建立在 baseline SwiGLU 数值正确且能训练的前提上，否则无法区分“新架构效果”与“原始 FFN bug”。

下一章把 Q/K/V projection 和 normalization 后的 hidden state 接到 attention。

[上一章：softmax / cross-entropy](/blog/2026/2026-08-15-cs336-a1-softmax-cross-entropy/)

[下一章：attention / RoPE](/blog/2026/2026-08-15-cs336-a1-attention-rope/)

