---
schema: bubblevan/v1
id: blog-20260815-cs336-a1-data-checkpoint
content_kind: blog
title: CS336 A1 复盘八：Data Loader 与 Checkpoint
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 复盘 token stream、随机 batch、memmap、checkpoint 和 baseline 装配，完成从“模块正确”到“可以训练”的最后一章。
topics: [CS336, Data, Checkpoint, Training Loop, Reproducibility]
projects: [cs336]
aliases: []
authors: [bubblevan]
---

这是 CS336 A1 baseline 搭建阶段的最后一章。前面的模型、loss 和 optimizer 即使全部正确，如果 data loader 的输入输出错位，或者 checkpoint 没有保存 optimizer state，训练仍然无法可靠复现。

## 1. 语言模型训练数据是一条 token stream

tokenizer 把文档变成 token IDs 后，最简单的训练表示是一条长序列：

```text
x_0, x_1, x_2, ..., x_n
```

从中随机取一个起点 i 和长度 T，就得到：

```text
input:  x_i,     x_(i+1), ..., x_(i+T-1)
target: x_(i+1), x_(i+2), ..., x_(i+T)
```

batch loader 只需要重复采样 B 个起点，并保证每个起点都有足够的下一个 token。这里最常见的 off-by-one 错误是允许起点太靠近末尾，导致 target 少一个元素，或者偷偷 padding 但没有在 loss 中处理。

## 2. dataset 不一定要全部装进 RAM

TinyStories 和 OpenWebText 都是大文本。tokenized 后可以保存成适合随机访问的整数数组，再使用 `numpy.memmap` 或类似机制按需读取。这样训练过程只需要把当前 batch 搬到 device，而不是把整个 token stream 复制进 GPU 或 Python heap。

这一步的资源边界要记录清楚：

- 原始文本大小；
- tokenized 文件大小；
- token dtype；
- vocabulary size；
- 是否使用 memmap；
- batch 读取耗时。

如果 vocabulary 小于 65536，某些数据可以使用 uint16 存储；但必须确保 token ID 不会超出 dtype 范围。数据压缩是资源优化，不应该以静默截断为代价。

## 3. batch loader 的验收

官方 `get_batch` 测试会检查：

- `x` 和 `y` shape 都是 `[B,T]`；
- y 是 x 向右移动一位；
- 起点范围覆盖合法边界；
- device 参数被正确使用；
- 无效 CUDA device 会产生可理解的错误。

我还会增加一个 deterministic test：给定固定 dataset、固定随机 seed 和固定 batch size，采样出的 batch 可复现。正式训练时可以使用随机采样，但调试时必须能固定采样，否则很难判断 loss 变化来自代码还是来自 batch。

## 4. checkpoint 保存的不是模型一个对象

一个可恢复的训练 checkpoint 至少需要：

```text
model state_dict
optimizer state_dict
iteration / step
```

实际工程中还应保存：

- config；
- random seed 或 RNG state；
- 数据版本和文件 hash；
- tokenizer vocabulary / merges 的定位信息；
- 当前 best validation loss；
- scheduler state 或可重建的 schedule 参数。

如果只保存 model state，恢复后 optimizer 的 moments 会被清空，训练轨迹就不再连续。对于 AdamW，这意味着恢复后的更新和中断前并不是同一个优化过程。

## 5. checkpoint 的正确性测试

A1 官方 checkpoint 测试会创建一个小模型和 optimizer，保存后重新构造对象，再加载状态并比较：

- iteration 是否一致；
- model parameters 是否一致；
- optimizer state 是否一致。

我会再加一个真正的 resume test：

```text
路线 A：连续执行两步
路线 B：执行一步 -> 保存 -> 重新加载 -> 再执行一步
比较第二步之后的参数、optimizer state 和 loss
```

如果两条路线不一致，通常说明 checkpoint 漏了 optimizer、scheduler、随机数状态，或者 data loader 在恢复后拿到了不同 batch。

## 6. 从模块到 baseline 的装配顺序

到这里，A1 baseline 的依赖关系可以写成：

```text
raw text
  -> train BPE
  -> serialize vocab / merges
  -> encode train / valid
  -> token arrays or memmap
  -> get_batch
  -> TransformerLM
  -> cross-entropy
  -> AdamW + schedule + clipping
  -> checkpoint / evaluation / generation
```

这条链路中每一段都应该有自己的最小测试。不要一上来就把完整 TinyStories 训练脚本跑几个小时；先用小 fixture、短 context 和极小模型检查每个箭头是否成立。

## 7. RTX 5060 8GB 的第一轮实验

本机的目标应该是“验证能训练”和“取得可解释趋势”，不是直接追逐 B200 leaderboard。建议分三档：

```text
Debug:
  极小 vocabulary、短 context、1–2 个 block、单 batch overfit

Smoke:
  TinyStories 小模型、context 128/256、短 token budget

Architecture:
  固定 seed 和 token budget，对比 GQA/QK-Norm/SWA/小型 MoE
```

由于 8GB 显存有限，batch size、dtype、gradient accumulation 和模型宽度需要通过 peak VRAM 实测决定。OpenWebText 可以先做短训练 sanity test；完整官方 token budget 和 B200 时间限制不应在本机上作等价承诺。

## 8. 这一章完成后，A1 baseline 到哪一步

到这里，我的 baseline 搭建阶段应当完成：

- 官方核心模块已经有实现位置；
- adapter 可以连接到官方 tests；
- tokenizer 能产出可复用的 token 文件；
- model 能在 tiny batch 上 forward/backward；
- optimizer 能更新参数；
- checkpoint 能恢复连续训练；
- 本机能跑最小 TinyStories smoke test。

这还不代表训练和消融实验已经完成。下一阶段才是正式的 TinyStories 训练、学习率和 batch size sweep、OpenWebText baseline，以及后续 Architecture Lab 的 GQA、MoE、MLA 和可视化。

## 9. 八章复盘的总回顾

```text
Tokenizer / BPE
  -> token IDs
Linear / Embedding
  -> hidden states
softmax / cross-entropy
  -> training objective
RMSNorm / SiLU / SwiGLU
  -> stable nonlinear block
attention / RoPE
  -> causal token interaction
Transformer block / LM
  -> logits
AdamW / schedule / clipping
  -> parameter updates
data / checkpoint
  -> reproducible training system
```

这八章共同组成 A1 baseline 的“可解释骨架”。下一步不是继续增加模型名字，而是把每一章对应的实现、官方测试、额外不变量测试和第一份实验记录一一落回仓库。

[上一章：AdamW / schedule / clipping](/blog/2026/2026-08-15-cs336-a1-adamw-schedule-clipping/)

