---
title: "Pi Context 与 Session：四种消息状态不相等"
weight: 3
draft: true
---

> 占位页：从消息转换和 session 持久化出发，区分 AgentMessage、LLM Message、Model Context 和 Session Transcript。

## 预期区分

```text
AgentMessage[]
        ≠
LLM Message[]
        ≠
Model Context
        ≠
Session Transcript
```

## 预期主线

```text
context.messages
    ↓
transformContext()
    ↓
convertToLlm()
    ↓
Context { systemPrompt, messages, tools }
    ↓
Model
```

## 源码入口

```text
packages/agent/src/harness/context.ts
packages/agent/src/harness/messages.ts
packages/agent/src/session/
packages/agent/src/compaction/
```

后续正文要回答哪些状态被持久化、哪些只在当前运行存在、compaction 改的是 transcript 还是 model context，以及 branch / navigation 如何影响 tip。
