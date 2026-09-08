---
title: "Pi Tools：从 Tool Call 到 ToolResultMessage"
weight: 4
draft: true
---

> 占位页：以一个具体 `read` 调用为例，追踪工具查找、参数验证、执行、事件发射、结果回写和下一轮推理。

## 预期主线

```text
AssistantMessage.content
    ↓ filter(toolCall)
executeToolCalls(...)
    ├── lookup tool
    ├── validate arguments
    ├── execute
    └── emit tool events
    ↓
ToolResultMessage
    ↓
currentContext.messages.push(result)
    ↓
下一次 streamAssistantResponse()
```

## 失败路径

后续正文至少覆盖：tool 不存在、schema validation 失败、输出因 length 截断、AbortSignal 到来，以及 `sequential` 与可并行执行模式下的结果顺序和取消语义。

## 源码入口

```text
packages/agent/src/agent-loop.ts
packages/agent/src/types.ts
packages/agent/src/harness/execution/
```
