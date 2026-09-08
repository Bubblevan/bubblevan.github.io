---
title: "Pi Evals：怎样证明 Harness 改动有效"
weight: 10
draft: true
---

> 占位页：研究如何评估 Agent Loop、工具执行、Context、Steering 或 Extension 的改动，而不是依赖“体感更好”。

## 预期证据链

```text
Harness change
    ↓
fixed task set
    ↓
trajectory / telemetry
    ↓
behavioral comparison
    ↓
regression decision
```

重点覆盖 `packages/evals/`、`packages/telemetry/`、失败 trajectory、tool latency、interrupt correctness、context preservation 和 extension regression。

后续正文需要把“模型能力变化”和“Harness 改动收益”尽量分离。
