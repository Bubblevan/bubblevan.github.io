---
title: "Hermes Gateway：平台适配与 AIAgent 解耦"
weight: 8
draft: true
---

> 占位页：轻量研究 Hermes 如何让 Telegram、Discord、Slack 等平台通过 Adapter 接入同一个 AIAgent，而不把平台逻辑污染 Agent Core。

## 预期主线

```text
User
  ↕
Messaging Platform
  ↕
Platform Adapter
  ↕
Gateway Runner
  ↕
AIAgent
```

## 源码入口

```text
gateway/run.py
gateway/session.py
gateway/delivery.py
gateway/pairing.py
gateway/hooks.py
gateway/mirror.py
gateway/platforms/
```

本页不重复 OpenClaw 的 Gateway 平台分析，只关注 adapter、delivery、pairing 和 Agent Core 的边界。
