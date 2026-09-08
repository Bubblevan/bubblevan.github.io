---
title: "Codex Session：Thread、Context 与 Compaction"
weight: 4
draft: true
---

> 占位页：解释 Codex 如何维持可恢复的长会话，以及 conversation history、model context、thread state 和 turn state 的区别。

## 预期主线

```text
Conversation History
        ≠ Model Context
        ≠ Thread Runtime State
        ≠ Turn Runtime State
```

重点覆盖 session 生命周期、持久化、interrupt、pending state、automatic compaction、rollout 与 thread store。

## 源码入口

```text
codex-rs/core/src/session/
codex-rs/core/src/state/
codex-rs/core/src/compact.rs
codex-rs/core/src/compact_remote*.rs
codex-rs/core/src/rollout/
codex-rs/core/src/thread_store/
```

## 主要参考

- [Unrolling the Codex agent loop](https://openai.com/index/unrolling-the-codex-agent-loop/)

后续正文要把 compaction 视为上下文管理机制，而不是自动替代文件化长期记忆。
