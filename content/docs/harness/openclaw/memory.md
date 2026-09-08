---
title: "OpenClaw Memory：从 Workspace 文件到 Durable Recall"
weight: 8
draft: true
---

> 占位页：研究 OpenClaw 如何把 Markdown 文件、检索、compaction flush 和后台 consolidation 组合成可审阅的长期记忆。

## 预期结构

```text
USER.md
    ↓
稳定的 user model / preference

MEMORY.md
    ↓
精选的 durable memory

memory/YYYY-MM-DD.md
    ↓
工作中的 daily observations

DREAMS.md
    ↓
后台 consolidation 的 review surface
```

同时覆盖 `memory_search`、`memory_get`、hybrid retrieval、memory flush、dreaming / promotion、provenance 和 taint gate。

## 研究问题

- 什么应该进入长期 Memory，什么只留在 transcript？
- 为什么不能每次都注入全部 daily notes？
- Retrieval、compaction 和 workspace 的边界如何划分？
- 如何处理 stale memory、contradiction 和模型主动写入的风险？

## 源码入口

```text
extensions/memory-core/
extensions/memory-core/src/session-search-visibility.ts
```
