---
title: "Hermes Session 与 Memory：从 SQLite 到可检索上下文"
weight: 5
draft: true
---

> 占位页：区分 Session、History、Context、Profile 和 Memory，并追踪它们如何进入下一次模型调用。

## 预期主线

```text
raw conversation
    ↓
SessionDB / state.db
    ↓
search / lineage
    ↓
context selection
    ↓
model-visible context
```

Hermes 的 canonical session/state storage、FTS5、Gateway routing index、transcript/export 和 Memory provider 应分开讨论。

## 研究问题

```text
Session ≠ Memory
History ≠ Context
Memory retrieval ≠ prompt injection
Persistence ≠ recall
```

## 源码入口

```text
agent/memory_manager.py
agent/memory_provider.py
plugins/memory/
SessionDB / state.db
```
