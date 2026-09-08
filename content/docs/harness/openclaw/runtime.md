---
title: "OpenClaw Runtime：一次 Prepared Turn 如何运行"
weight: 3
draft: true
---

> 占位页：研究 OpenClaw 外层 runner、Agent 对象和 low-level agent loop 如何串成一次可持久化的执行。

## 预期主线

```text
Gateway agent RPC
    ↓
agentCommand
    ↓
runEmbeddedAgent
    ↓
session lane / global lane
    ↓
prepare workspace + load skills
    ↓
assemble context + build prompt
    ↓
Agent.prompt(...)
    ↓
agent-loop
    ↓
model inference ↔ tool execution
    ↓
stream + persist transcript
    ↓
lifecycle end
```

## 源码入口

```text
packages/agent-core/src/agent-loop.ts
packages/agent-core/src/agent.ts
src/agents/embedded-agent-runner/run-loop.ts
```

## 待回答的问题

- 为什么 agent run 要按 session 串行？
- steer、follow-up、collect、interrupt 有什么区别？
- `agent.wait` timeout 为什么不等于 cancel？
- 旧 run 如何避免在新 run 之后写 transcript？
