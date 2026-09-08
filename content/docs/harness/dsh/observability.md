---
title: "DSH Observability：Attempt、Replay 与 Runtime Diagnostics"
weight: 13
draft: true
---

> 占位页：研究 Session Events、Assistant Attempts、Telemetry、Session Query 和 Runtime Diagnostics 如何构成可重放、可诊断的运行记录。

## 预期结构

```text
session events
    ↓
assistant attempts
    ↓
telemetry / session-query
    ↓
runtime diagnostics
    ↓
replay / trajectory UI
```

需要重点区分：

```text
assistant/message
        ≠
assistant/attempt
```

失败、retry、cancel 和 stream error 可以被持久记录为 attempt，但不一定应该进入下一次 model history。

## 源码入口

```text
packages/session-query/
packages/telemetry/
runtime diagnostics
SessionEvent projection
```

后续正文应以一条失败或重试 trace 为例，展示输入、事件、状态变化和最终诊断结果。
