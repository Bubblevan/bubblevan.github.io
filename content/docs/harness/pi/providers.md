---
title: "Pi Providers：Harness 与 Model API 的解耦"
weight: 7
draft: true
---

> 占位页：研究 `pi-ai` 如何提供统一的多 Provider LLM API，以及 Model、Adapter、Streaming 和 Agent Runtime 的边界。

## 预期分层

```text
Agent Runtime
    ↓
pi-ai unified API
    ↓
provider adapter
    ↓
model API / event stream
```

重点覆盖消息格式、tool call、stream event、认证、context limit 和 provider-specific 差异，而不是把 API endpoint 直接写进 Agent Loop。

## 源码入口

```text
packages/ai/
packages/agent/
```
