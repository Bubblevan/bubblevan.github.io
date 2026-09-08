---
title: "DSH Subagents：Spawn、Fork 与 Continuation"
weight: 8
draft: true
---

> 占位页：把 Subagent、Fork、Persistent Child 和 External Delegated Agent 拆开，避免统称为“多智能体”。

## 预期主线

```text
parent Agent
    ↓
SubagentProvider
    ↓
child agent / external delegated agent
    ↓
continuation
    ↓
result
```

重点研究 spawn vs fork、fresh child vs delegated turn、context isolation、session lineage、continuation 和 persistent subagent。

## 源码入口

```text
packages/subagent/
packages/session/
packages/jobs/
```
