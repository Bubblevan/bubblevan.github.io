---
title: "Pi Runtime：一次 Agent Loop 如何完成"
weight: 1
draft: true
---

> 占位页：以官方源码为基准，追踪 Prompt 从 `Agent.prompt()` 进入模型、工具执行、结果回写到下一轮 inference 的完整路径。

## 预期主线

```text
Agent.prompt(...)
    ↓
agentLoop(...)
    ↓
runAgentLoop(...)
    ↓
runLoop(...)
    ↓
streamAssistantResponse(...)
    ├── transformContext
    ├── convertToLlm
    └── streamFunction
    ↓
AssistantMessage
    ↓
executeToolCalls(...)
    ↓
ToolResultMessage[]
    ↓
append to currentContext.messages
    ↓
下一轮模型调用
```

## 源码入口

```text
packages/agent/src/agent-loop.ts
packages/agent/src/agent.ts
packages/agent/src/types.ts
```

后续正文需要展示 `currentContext`、`newMessages`、`lastCompletedTurn`、`pendingMessages` 和 `hasMoreToolCalls` 如何变化，并覆盖 length 截断、abort、error 和无 tool call 的结束路径。
