---
title: "Codex Security：Approval、Permission 与 Sandbox"
weight: 6
draft: true
---

> 占位页：说明 Codex 如何把“是否允许动作”和“动作获准后能触碰什么”拆成互补的安全边界。

## 预期主线

```text
model request
    ↓
tool policy
    ↓
approval decision
    ↓
permission profile
    ↓
sandbox transform
    ↓
OS enforcement
    ↓
spawn
```

覆盖 approval、sandbox、网络、凭证、规则、managed config 和审计；特别关注 Windows restricted token、macOS Seatbelt 与 Linux isolation 的差异。

## 源码入口

```text
codex-rs/sandboxing/
codex-rs/core/src/sandboxing/
codex-rs/core/src/exec_policy.rs
codex-rs/linux-sandbox/
```

## 主要参考

- [Running Codex safely at OpenAI](https://openai.com/index/running-codex-safely/)
- [Building a safe, effective sandbox to enable Codex on Windows](https://openai.com/index/building-codex-windows-sandbox/)
