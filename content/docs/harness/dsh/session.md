---
title: "DSH Session：Append-only Event Log 与 Projection"
weight: 2
draft: true
---

> 占位页：研究为什么 DSH 不把 mutable `messages[]` 当作 Agent 的 source of truth，而用 SessionEvent log 重建模型可见历史。

## 预期主线

```text
Append-only SessionEvent log
        ↓
projection
        ↓
deriveMessages()
        ↓
Model Request
```

重点覆盖 `user/message`、`assistant/message`、`assistant/attempt`、`tool/call`、`tool/result`、`turn/start`、`turn/end`、`step/start` 和 `step/end`。

## 这样设计支持什么

```text
resume / fork / retry / failure attempt
tool history / UI replay / persistence
telemetry / migration
```

## 源码入口

```text
packages/session/
packages/session-query/
SessionProjectionRegistry
```

后续正文需要解释 `Model-visible means logged` 这一 invariant，以及旧 attempt 为什么可以持久化但不一定进入下一次 model history。
