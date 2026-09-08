---
title: "Codex Tools：动态工具面与执行路由"
weight: 5
draft: true
---

> 占位页：研究工具如何从候选能力变成本轮模型可见的工具，并经过 router、registry、MCP、approval、并发执行和结果回传。

## 预期主线

```text
tool candidate
    ↓
model-visible tool spec
    ↓
ToolRouter / ToolRegistry
    ↓
approval + sandbox
    ↓
execution / parallelism
    ↓
ResponseInputItem
    ↓
next inference
```

## 源码入口

```text
codex-rs/core/src/tools/router.rs
codex-rs/core/src/tools/spec_plan.rs
codex-rs/core/src/tools/parallel.rs
codex-rs/core/src/tools/handlers/
```

后续正文要重点回答：Tool availability 是静态工具表，还是由 session、turn、environment、MCP、apps 和 candidates 动态构建？
