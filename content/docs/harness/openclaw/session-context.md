---
title: "OpenClaw Session 与 Context：从 Transcript 到 Prepared Turn"
weight: 5
draft: true
---

> 占位页：解释 OpenClaw 如何在 session、workspace、memory 和 context engine 之间组装本轮模型输入。

## 预期区分

```text
Conversation History
        ≠ Submitted Model Context
        ≠ Session Runtime State
        ≠ Workspace
        ≠ Durable Memory
```

## 预期主线

```text
sessionKey
    ↓
load transcript
    ↓
resolve workspace + bootstrap files
    ↓
skills snapshot
    ↓
memory / context retrieval
    ↓
context engine
    ↓
budget / truncation / compaction
    ↓
model-visible prompt
```

## 源码入口

```text
src/agents/sessions/
src/context-engine/
src/agents/system-prompt*
compaction / session database / queue lanes
```

重点研究 writer claims、并发 run、旧 transcript 覆盖和 compaction 后原始记录的保存边界。
