---
schema: bubblevan/v1
id: blog-20260815-cs336-a1-attention-rope
content_kind: blog
title: CS336 A1 复盘五：Attention 与 RoPE
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 用张量形状重新推导 scaled dot-product attention、causal mask、多头拆分和 RoPE，连接到后续 GQA 与 MLA 实验。
topics: [CS336, Attention, RoPE, MHA, Transformer]
projects: [cs336]
aliases: []
authors: [bubblevan]
---

这是 A1 baseline 最需要“手算 shape”的一章。attention 的公式并不长，真正容易错的是 Q/K/V 的布局、softmax 的维度、mask 的位置、head 拆分，以及 RoPE 到底作用在 Q/K/V 的哪一部分。

## 1. 从单头 attention 开始

scaled dot-product attention 可以拆为三步：

```text
scores = Q K^T / sqrt(d_k)
weights = softmax(scores + mask)
output = weights V
```

如果 Q、K、V 的序列长度都是 T，单个 head 的典型形状是：

```text
Q: [B, T_q, d_k]
K: [B, T_k, d_k]
V: [B, T_k, d_v]
scores: [B, T_q, T_k]
output: [B, T_q, d_v]
```

除以 sqrt(d_k) 是为了控制 dot product 随维度增大而变大的方差，避免 softmax 过早饱和。mask 必须在 softmax 之前参与 score 计算，否则未来位置仍然可能获得非零概率。

## 2. causal mask 是语言模型的因果边界

位置 t 只能看到 0 到 t 的历史，不能看到 t+1 之后的 token。对于长度 T 的序列，causal mask 是一个下三角可见性矩阵：

```text
1 0 0 0
1 1 0 0
1 1 1 0
1 1 1 1
```

这不仅是训练时的约束，也是 autoregressive generation 能成立的前提。如果训练时允许看到未来 token，loss 会被错误地降低，模型生成时却无法获得同样的信息。

实现时要想清楚 mask 的 dtype、广播形状和填充值。无论使用 boolean mask 还是加性 mask，最终都必须保证 softmax 后未来位置权重严格为零或数值上不可见。

## 3. 多头 attention 的 shape

A1 的输入 hidden state 是：

```text
x: [B, T, D]
```

经过 Q/K/V projection 后，拆成 H 个 heads，每个 head dimension 为 `D/H`：

```text
q, k, v: [B, H, T, Dh]
scores:   [B, H, T, T]
output:   [B, H, T, Dh]
merge:    [B, T, D]
```

最后再经过 output projection。最重要的检查是：`D = H * Dh`，head 维不能被错误地当成 sequence 维，softmax 应该沿 key sequence 维进行。

我会在纸上反复写 `[B,T,D] -> [B,H,T,Dh] -> [B,H,T,T] -> [B,T,D]`，直到看到任意 einsum 或 reshape 都能立即说出每个轴的含义。这种 shape 思维比记住某个 `rearrange` 字符串更可靠。

## 4. RoPE 作用在 Q/K，不是 V

RoPE 不是给每个 token 加一个 position embedding，而是按照 position 对 Q/K 的二维维度对做旋转。对于第 k 个维度对，旋转角度随着 token position 变化。

直观上：

```text
content -> Q/K projection -> position-dependent rotation -> attention score
```

RoPE 作用在 Q 和 K 上，V 保持内容表示。Q 与 K 的相对旋转关系会进入 dot product，因此 attention score 能感受到相对位置。

实现时需要明确：

- head dimension 必须适合两两配对；
- theta 决定不同维度的旋转频率；
- position ids 不一定只是从 0 连续增长；
- cache 的最大长度和真实输入长度可能不同；
- Q 和 K 必须使用一致的 position convention。

## 5. 官方测试覆盖的关键边界

A1 model tests 会分别检查：

- 无 mask 的 scaled dot-product attention；
- 4D `[B,H,T,Dh]` attention；
- 多头 self-attention；
- 加入 RoPE 的 multi-head attention；
- 单独的 RoPE；
- 不同 position ids；
- Transformer LM 的 truncated input。

这意味着不能只在固定的 `[B,T,D]` 小例子上验证。尤其是 truncated input 测试，要求模型实际使用的 context 不超过当前输入，而不是强行按照最大长度构造输出。

## 6. 从 MHA 走向 Architecture Lab

A1 baseline 是 MHA：Q、K、V 都有 H 个 heads。后面最自然的第一个 mutation 是 GQA：保留较多 query heads，但让多个 query heads 共享较少的 KV heads。

GQA 的研究问题不是“代码是否少了一个 reshape”，而是：

- KV cache 是否按 KV head 数减少；
- attention 表达能力损失多少；
- 相同 active compute 下 validation loss 如何变化；
- decode throughput 和 peak VRAM 是否改善。

再往后是 MLA、sliding-window、sparse/selective attention。它们的重点不同：GQA 主要研究 KV sharing，SWA 研究可见性范围，MLA 研究 latent KV 表示和推理内存，不能把它们混成同一类优化。

## 7. 当前 baseline 的验收方法

attention 接入完整 Transformer 前，我会做四组小测试：

1. 手工构造长度为 3 的输入，确认第一个位置看不到未来；
2. 用极小 head dimension 检查 QK score 的形状；
3. 给相同内容、不同 position ids 的 Q/K，确认 RoPE 输出发生预期变化；
4. 让 output projection 使用固定权重，确认 head merge 后仍回到 `[B,T,D]`。

这一章完成后还不开始正式训练。先把 attention snapshot、mask invariants 和 shape checks 做稳定，下一章再把 attention、FFN、residual 和 LM head 组装成 Transformer LM。

[上一章：RMSNorm / SiLU / SwiGLU](/blog/2026/2026-08-15-cs336-a1-rmsnorm-silu-swiglu/)

[下一章：Transformer block / LM](/blog/2026/2026-08-15-cs336-a1-transformer-block-lm/)

