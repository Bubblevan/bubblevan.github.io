---
title: "DSH Context：从 Session Projection 到 Immutable Model Request"
weight: 6
draft: true
---

> 占位页：只研究模型到底看到了什么，不把 Session persistence 和 Context assembly 混成一个问题。

## 预期主线

```text
Session Event Log
      ↓
deriveMessages()
      ├── workspace instructions
      ├── time context
      ├── references
      ├── injected context
      └── tool schemas
      ↓
immutable model request
```

## 待回答的问题

- system prompt 由谁组装？
- tool schema 在哪里进入 prompt？
- workspace instruction 和 `agent.inject()` 何时生效？
- 为什么注入的 context 也必须最终能由日志重建？
- Prefix cache 应如何作为 request stability 问题研究？

## 源码入口

```text
packages/core/system-prompt/
packages/context/
packages/core/agent-loop/
```
