---
title: "DSH Runtime：Turn、Step 与 Agent Loop"
weight: 1
draft: true
---

> 占位页：从 Inbox 到 Turn End，追踪 DSH 一次真实输入如何经过模型、工具和 Session Event。

## 预期主线

```text
turn/start
    ↓
claim input
    ↓
agent/pre-step
    ↓
step/start
    ↓
derive model history
    ↓
agent/request
    ↓
llm/stream
    ↓
assistant/message
    ↓
tool/call → tools/pre-execute → execute → post-execute
    ↓
tool/result
    ↓
step/end
    ↓
next step / stopping
    ↓
turn/end
```

## 源码入口

```text
packages/core/agent-loop/src/index.ts
packages/core/agent-loop/src/agent.ts
packages/core/agent-loop/src/inbox.ts
packages/core/agent-loop/src/assistant-stream.ts
packages/core/agent-loop/src/tool-calls.ts
packages/core/agent-loop/src/runtime-context.ts
packages/core/agent-loop/src/invariant.ts
```

后续正文要明确：`Step = 一次 model request + tools`，`Turn = 0 个或多个 Step`，并记录 claim、stream、tool result 和 next step 的状态变化。
