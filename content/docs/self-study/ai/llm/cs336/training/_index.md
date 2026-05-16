---
title: "Training"
weight: 1
math: true
---
```
token_ids (x, y)
    ↓
TransformerLM(x)
    ↓
logits [B, S, V]
    ↓
CrossEntropy(logits, y)
    ↓
scalar loss
    ↓
loss.backward()
    ↓
所有参数得到 grad
    ↓
gradient clipping（可选）
    ↓
AdamW.step()
    ↓
参数更新
    ↓
scheduler 改下一个 step 的 lr
```
{{% jupyter "training.ipynb" %}}