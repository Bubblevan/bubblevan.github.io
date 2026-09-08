---
title: "Pi State Machine：Agent Loop 之上的 Harness 控制平面"
weight: 2
draft: true
---

> 占位页：解释为什么一个 Agent Loop 之外还需要 AgentHarness，以及 lane、operation、queue、retry、abort 和 compaction 如何形成控制平面。

## 预期区分

```text
Agent Loop
  单次模型—工具反馈循环

Agent Harness
  session / lane / queue / retry / abort
  compaction / navigation / events / usage
```

## 源码入口

```text
packages/agent/src/harness/agent-harness.ts
packages/agent/src/runtime/
packages/agent/src/session/
packages/agent/src/execution/
packages/agent/src/compaction/
packages/agent/src/events.ts
```

重点研究 `OperationRequest`、`OperationAdmission`、`DriveOutcome`、`LaneSnapshot`、`SessionSnapshot` 和 `HarnessEvent` 的状态关系，以及 `settled`、`waiting(retry)`、`waiting(deferred)` 的区别。
