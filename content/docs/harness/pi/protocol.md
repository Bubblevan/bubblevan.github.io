---
title: "Pi Protocol：把 Harness 从 TUI 解耦"
weight: 9
draft: true
---

> 占位页：研究 Pi 如何通过 client、server、protocol 和 RPC 让同一个 Agent Runtime 服务不同 UI 或调用方。

## 预期主线

```text
TUI / Client / Server
        ↓
Protocol / RPC entry
        ↓
Agent Runtime
        ↓
events / state / result
```

## 源码入口

```text
packages/client/
packages/server/
packages/protocol/
rpc-entry.ts
```

后续正文要回答事件如何恢复 UI、协议如何表达 tool / steering / abort，以及 TUI 不应拥有的 Runtime 状态是什么。
