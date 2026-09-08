---
title: "DSH Tools：Scoped Registry 与 Guarded Execution"
weight: 3
draft: true
---

> 占位页：以一个真实 Bash 或 read Tool 为例，追踪 registry lookup、hook、approval、execution、result 和下一 Step。

## 预期主线

```text
model ToolCall
    ↓
schema / registry lookup
    ↓
tools/pre-execute
    ↓
approval / policy
    ↓
tools/execute
    ↓
tools/post-execute
    ↓
ToolResult
    ↓
SessionEvent
    ↓
next Step
```

## 失败路径

后续正文至少覆盖错误参数、tool timeout、abort、过大的 tool result、重复 tool call、parallel / sequential，以及要求 continuation 的 Tool。

## 源码入口

```text
packages/core/tools/
packages/core/agent-loop/src/tool-calls.ts
packages/hooks/
```
