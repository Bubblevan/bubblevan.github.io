---
title: "Hermes Subagents：Delegate Tool 与 Child Agent"
weight: 7
draft: true
---

> 占位页：以 `delegate_tool.py` 为入口，研究 Parent Agent 如何创建、隔离、等待并消费 Child Agent 的结果。

## 预期主线

```text
Parent Agent
    ↓ delegate
Child Agent
    ↓ isolated task / context
result
    ↓
Parent Context
```

## 待回答的问题

- delegation input 包含哪些边界？
- child 获得哪些 tools，session 是否持久？
- 如何限制深度和并行污染？
- 什么时候 Child Agent 比直接 Tool Call 更划算？

## 源码入口

```text
tools/delegate_tool.py
```
