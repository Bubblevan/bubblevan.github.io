---
title: "OpenClaw Multi-Agent：Routing、Child Agent 与 External Runtime"
weight: 10
draft: true
---

> 占位页：拆清 OpenClaw 中三种不同的“多 Agent”，避免把隔离路由、子 Agent 和外部 Runtime 混成一个概念。

## 三种层次

```text
Multi-agent Routing
        ≠
Sub-agent / Child Agent
        ≠
External Agent Runtime
```

### Multi-agent Routing

同一 Gateway 中运行多个隔离 Agent，每个 Agent 拥有独立的 workspace、agentDir、auth profiles 和 session store；外部消息通过 bindings 路由到对应 Agent。这是 identity + state + routing isolation。

```text
Gateway
  ├── Binding → Agent A → workspace / session
  ├── Binding → Agent B → workspace / session
  └── Binding → Agent C → workspace / session
```

### Child Agent 与 External Runtime

一个 Agent 动态创建 child/sub-agent，和一个 Agent 把任务交给 Codex 等外部 Runtime，是另外两种关系。后续正文要分别追踪 spawn、wait、artifact、隔离和结果回传。

## 关键边界

多 Agent 不应因为任务“看起来复杂”就默认开启；应由 underscope、context pollution、独立验证或权限隔离等可复现 failure mode 驱动。
