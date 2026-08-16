---
schema: bubblevan/v1
id: blog-20260815-cs336-a1-transformer-block-lm
content_kind: blog
title: CS336 A1 复盘六：Transformer Block 与 Language Model
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 从 pre-norm residual block 到 LM head，复盘一个 token 如何穿过完整 Transformer LM，并建立 baseline 的集成验收标准。
topics: [CS336, Transformer, Language Model, Residual Stream]
projects: [cs336]
aliases: []
authors: [bubblevan]
---

前五章分别处理 tokenizer、参数模块、loss、normalization、FFN、attention 和 RoPE。到了这里，真正的问题变成：这些模块怎样以正确的顺序组合，让一个 token 从 Embedding 一直走到 vocabulary logits。

## 1. 一个 Transformer block 的数据流

A1 baseline 使用 pre-norm block：

```text
x
  -> RMSNorm
  -> causal MHA + RoPE
  -> residual add
  -> RMSNorm
  -> SwiGLU
  -> residual add
  -> y
```

用符号表示就是：

```text
z = x + Attention(RMSNorm(x))
y = z + FFN(RMSNorm(z))
```

这里的两个 residual add 不是可有可无的连接。它们构成 residual stream，让每个 block 在已有表示上添加 attention 和 FFN 的更新，同时给梯度提供较直接的路径。

## 2. TransformerLM 的整体形状

完整 decoder-only LM 的 shape flow 可以固定为：

```text
input IDs       [B, T]
Embedding       [B, T, D]
N blocks        [B, T, D]
final RMSNorm   [B, T, D]
LM head         [B, T, V]
logits          [B, T, V]
```

其中 B 是 batch size，T 是实际 sequence length，D 是 d_model，V 是 vocabulary size。`context_length` 是模型允许的最大长度，不代表每次输入一定使用完整长度。

LM head 的输出要交给上一章的 cross-entropy；训练时通常对输入做 one-token shift，使位置 t 的 logits 预测 t+1 的 token。

## 3. 为什么 block 里还要 final RMSNorm

每个 block 内的 RMSNorm 服务于进入 attention 和 FFN 前的稳定性；最后的 RMSNorm 服务于整个 stack 输出到 LM head 前的统一尺度。它们的位置不同，作用也不同。

这也是为什么不能因为 block 已经有 norm，就把 final norm 当成重复代码删掉。A1 的 TransformerLM snapshot 会把完整 state dict 加载进去，缺少 final norm 不只是性能变化，也会改变参数结构和输出数值。

## 4. context length 和 truncated input

模型构造时会根据最大 context length 准备 RoPE 相关缓存或 mask，但 forward 时应该尊重实际输入长度。一个长度为 `T/2` 的输入不能因为模型最大 context 是 T，就返回一份长度为 T 的输出。

这件事对后面 generation 也很重要：当生成序列超过 context window 时，需要截取最近的上下文，而不是让 position、mask 和 logits 的形状悄悄失配。

## 5. state dict 是模块组合的契约

A1 测试不是随机初始化后只看 loss，而是提供参考权重，再通过 adapter 装载到你的模块中。这样做会检查：

- block 内部模块的命名；
- Q/K/V/output projection 的 weight 方向；
- RMSNorm gain 的位置；
- FFN 三张 weight 的结构；
- token embedding、final norm 和 LM head 是否都被正确使用；
- residual 顺序是否一致。

因此我在 baseline 阶段会把 state dict 看成一种内部 ABI：模块可以按自己的文件划分组织，但参数语义必须稳定。后面新增 GQA、MoE 或 MLA 时，也应尽量让每个 component 的 state dict 可读、可检查。

## 6. 参数量和资源账

一个现代 Transformer 的比较不能只看层数。至少需要记录：

- vocab size；
- d_model；
- d_ff；
- number of layers；
- number of heads；
- context length；
- embedding 和 LM head 是否共享；
- attention / FFN 参数量；
- activation 和 optimizer state 的显存。

特别是 vocabulary size 会同时影响输入 embedding 和输出 projection。TinyStories 的 10K vocabulary 与 OpenWebText 的 32K vocabulary，即使使用相同 hidden size，也会产生明显不同的参数量和 LM head 计算量。

## 7. baseline 集成测试

官方 snapshot 覆盖 block 和 LM，但还需要我自己补三类 integration check：

1. **shape check**：随机输入从 `[B,T]` 到 `[B,T,V]` 全链路形状正确；
2. **causality check**：改变未来 token 时，较早位置的 logits 不应变化；
3. **tiny overfit check**：固定一个极小 batch，loss 应该可以明显下降。

第三项虽然已经接近训练，但它不是正式预训练。它的目的只是确认 forward、loss、backward 和 optimizer 之间的连接没有断开。

## 8. 从 baseline 到可插拔基座

Architecture Lab 的基座不应该让 `TransformerBlock` 里写满架构名称分支。更好的边界是：

```text
TransformerLM
  -> BlockFactory
       -> Norm component
       -> Attention component
       -> FFN component
```

同一个训练入口可以接受 MHA、GQA、SWA 或 MLA；同一个 block 可以接受 dense SwiGLU 或 MoE FFN。这样做的前提是每个 component 都有清晰的输入输出 shape 和可选统计信息。

不过这个抽象要等 baseline 通过 snapshot 后再做。过早抽象会把一个尚未验证的实现错误扩散到所有变体。

## 9. 当前完成标准

这一章完成，意味着我已经能从整数 token IDs 解释到 vocabulary logits，但还没有开始正式训练、学习率 sweep 或 architecture ablation。baseline 的下一块是 optimizer、scheduler、gradient clipping 和 checkpoint，它们决定这个模型是否真的能被训练起来。

[上一章：attention / RoPE](/blog/2026/2026-08-15-cs336-a1-attention-rope/)

[下一章：AdamW / schedule / clipping](/blog/2026/2026-08-15-cs336-a1-adamw-schedule-clipping/)

