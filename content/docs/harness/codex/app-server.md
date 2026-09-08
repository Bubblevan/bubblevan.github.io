---
title: "Codex App Server"
weight: 2
draft: true
---

> 占位页：研究 Codex harness 如何通过 App Server 向 TUI、IDE、桌面端或其他 Client 暴露统一的线程与事件接口。

## 待回答的问题

- App Server 与 CLI / TUI client 的边界在哪里？
- Thread、turn、event 和 approval 如何通过协议传递？
- `app-server` 与 `app-server-protocol` 如何和 `ThreadManager` 对接？

## 源码入口

```text
codex-rs/app-server/
codex-rs/app-server-protocol/
codex-rs/core/src/thread_manager.rs
```

## 主要参考

- [Unlocking the Codex harness](https://openai.com/index/unlocking-the-codex-harness/)

后续正文需要以具体 commit、协议类型和一条完整事件流为证据。
