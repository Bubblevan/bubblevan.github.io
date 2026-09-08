---
title: "Codex Runtime：一次 Agent Loop 如何运行"
weight: 3
draft: true
---

> 占位页：沿着官方 agent-loop 文章和源码，追踪一条 prompt 从 Client 进入模型、工具执行、结果回传到 turn 结束的完整路径。

## 预期主线

```text
CLI / TUI / App Server client
    ↓
ThreadManager
    ↓
CodexThread
    ↓
Session
    ↓
run_turn / session turn
    ↓
ModelClientSession + Responses API stream
    ↓
ToolRouter → tool result
    ↓
下一次 inference 或 terminal event
```

## 源码入口

```text
codex-rs/cli/src/main.rs
codex-rs/core/src/thread_manager.rs
codex-rs/core/src/session/turn.rs
```

## 主要参考

- [Unrolling the Codex agent loop](https://openai.com/index/unrolling-the-codex-agent-loop/)

后续正文要区分“模型生成动作提议”和“Harness 让动作真正发生”，并记录 tool failure 如何作为 observation 返回。
