---
title: "Codex Subagents：Delegation 与多 Agent Runtime"
weight: 8
draft: true
---

> 占位页：研究 Codex 当前如何创建、等待、隔离和汇总其他 Agent，并把 runtime primitive 与上层多 Agent 架构区分开。

## 预期主线

```text
parent task
    ↓
spawn / delegation
    ↓
isolated agent context
    ↓
work / artifact
    ↓
wait / result
    ↓
parent continues
```

Multi-Agent 不应作为默认架构；它应由明确 failure mode 驱动，例如 raw prompt underscope、探索污染主 context 或需要独立 verification。

## 需要保持的证据边界

源码可以证明系统提供了 spawn、wait、background 或 worktree 等 delegation primitive，但不能仅凭这些 primitive 推出 Codex 内部固定采用 Planner → Generator → Evaluator 的组织方式。

## 源码入口

```text
multi-agent tools
agent graph / delegation runtime
spawn / wait implementations
```

后续正文需要固定源码 commit，并为每一种 delegation 说明 Goal、Context、Tools、Artifact 和 Consumer。
