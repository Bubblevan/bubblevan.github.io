---
title: "Hermes Provider：Model、API Mode 与 Runtime 解耦"
weight: 3
draft: true
---

> 占位页：研究 Hermes 如何把 provider、model、API mode、credentials 和 base URL 分开解析，再交给 Runtime Provider Resolver。

## 预期主线

```text
(provider, model)
    ↓
Runtime Provider Resolver
    ↓
(api_mode, api_key, base_url)
    ↓
provider adapter
```

重点覆盖 `chat_completions`、`codex_responses`、`anthropic_messages` 等 API mode，以及 tool-call 格式、streaming、context limit、retry 和 fallback。

## 源码入口

```text
hermes_cli/runtime_provider.py
hermes_cli/auth.py
hermes_cli/models.py
agent/anthropic_adapter.py
```
