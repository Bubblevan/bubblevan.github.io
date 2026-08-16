---
schema: bubblevan/v1
id: blog-20260815-cs336-a1-adamw-schedule-clipping
content_kind: blog
title: CS336 A1 复盘七：AdamW、Learning-rate Schedule 与 Gradient Clipping
date: 2026-08-15
updated: 2026-08-15
status: draft
visibility: public
summary: 复盘从梯度到参数更新的完整路径，理解 AdamW 的 decoupled weight decay、warmup/cosine schedule 和全局梯度裁剪。
topics: [CS336, AdamW, Optimization, Training]
projects: [cs336]
aliases: []
authors: [bubblevan]
---

Transformer forward 正确并不意味着模型会训练。A1 把 AdamW、学习率 schedule 和 gradient clipping 单独列出来，是因为训练稳定性来自很多小契约的组合：梯度什么时候读取，weight decay 什么时候应用，warmup 的边界在哪里，裁剪的是单个参数还是所有参数的全局范数。

## 1. AdamW 的状态

对每个可训练参数，AdamW 通常维护一阶 moment 和二阶 moment：

```text
m_t: gradient 的指数移动平均
v_t: gradient^2 的指数移动平均
```

它们分别反映梯度方向和梯度尺度。更新时还要做 bias correction，使训练初期的 moment 估计不因为从零开始而过度偏小。

A1 要求实现自己的 AdamW，但允许继承 `torch.optim.Optimizer`。这让我关注 optimizer 的结构：参数组、状态字典、step 计数、zero_grad 后的梯度状态和 checkpoint 序列化，而不是只关注一条公式。

## 2. AdamW 与 L2 regularization 的区别

AdamW 的关键是 decoupled weight decay：weight decay 作为独立的参数缩减步骤，不把参数本身简单地混入 Adam 的自适应梯度里。

这会带来一个实现顺序问题。A1 的更新顺序和 handout/测试 fixture 是契约，不能凭网上另一种 AdamW 伪代码替换。尤其需要确认：

- 当前 step 使用哪个 learning rate；
- weight decay 使用哪个参数值；
- moment 更新和参数更新的先后；
- 没有 gradient 的参数是否跳过；
- 多个 parameter groups 是否各自使用配置。

一个 optimizer 的错误通常不会立刻报错，而是表现成 loss 下降慢、不同实现结果略有差异，或者训练一段时间后发散。因此 snapshot 和小型数值对照非常重要。

## 3. Learning-rate schedule 的三个阶段

A1 的 cosine schedule 带 warmup，通常分为：

```text
t < warmup_iters
    learning rate 从 0 或较小值上升到 max_lr

warmup_iters <= t <= cosine_cycle_iters
    从 max_lr 进行 cosine decay 到 min_lr

t > cosine_cycle_iters
    保持 min_lr
```

最容易错的是边界：warmup 的最后一步、cosine decay 的终点、超过终点后的行为。实验记录必须明确 step 是从 0 还是从 1 开始，否则相同的 `warmup_iters` 看起来会产生不同曲线。

学习率 schedule 也应该与训练总步数绑定。如果总 token budget 改了，却保留原来的 cosine end step，模型可能还没训练完就已经降到 min_lr，或者在训练结束时仍处在高学习率区间。

## 4. Gradient clipping 是全局约束

梯度裁剪不是逐个参数 tensor 单独裁剪，而是先把所有有梯度参数的平方和汇总，得到全局 L2 norm，再按照同一个比例缩放所有梯度。

概念上：

```text
global_norm = sqrt(sum(||g_i||^2))
scale = min(1, max_norm / global_norm)
所有梯度同时乘以 scale
```

需要跳过 `grad is None` 的参数，因为冻结参数或没有参与当前 forward 的参数可能没有梯度。裁剪系数也要避免除以零。

## 5. 官方测试和自己的测试

A1 官方测试会检查：

- AdamW 与参考数值一致；
- learning-rate schedule 的多个边界；
- 梯度 clipping 的全局范数；
- 没有梯度参数的处理；
- checkpoint 中 optimizer state 的保存和恢复。

我还需要补：

1. 一个参数组和多个参数组的行为一致性；
2. 固定 seed、固定 batch 时，resume 后下一步结果与连续运行一致；
3. 梯度范数小于上限时保持不变；
4. 梯度范数大于上限时所有参数按同一比例缩放；
5. schedule 在 warmup、decay end 和 after end 三个边界连续可解释。

## 6. optimizer 和 architecture 实验的关系

后续比较 GQA、MoE、MLA 时，optimizer 不能随意跟着 architecture 一起改变。第一轮实验应该固定 AdamW、warmup、cosine decay、weight decay 和 clipping，只改变一个 architecture component。

如果某个变体明显更容易发散，可以先记录“在 baseline recipe 下不稳定”，然后再做单独的稳定性实验。不能在 architecture 和 learning rate 同时变化后，把最终 loss 差异全部归因于 architecture。

## 7. 当前 baseline 的完成边界

这一章完成后，模型已经具备：

- forward 输出；
- loss；
- backward 梯度；
- 参数更新；
- learning-rate schedule；
- gradient clipping。

但还没有开始正式的 TinyStories 训练。接下来要把 tokenized dataset 变成随机 batch，并把 model、optimizer 和 iteration 可靠地保存下来。只有这样，训练过程才不会变成一次不可恢复的长脚本。

[上一章：Transformer block / LM](/blog/2026/2026-08-15-cs336-a1-transformer-block-lm/)

[下一章：data / checkpoint](/blog/2026/2026-08-15-cs336-a1-data-checkpoint/)

