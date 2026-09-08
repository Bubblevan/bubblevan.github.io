---
title: "Hermes Prompt Context：稳定前缀与动态上下文"
weight: 2
draft: true
---

> 占位页：研究 Hermes 如何将 Prompt 分成稳定、上下文和易变层，并通过压缩和缓存控制输入变化。

## 预期结构

```text
stable
  identity / tool guidance / skills
        ↓
context
  context files
        ↓
volatile
  memory / profile / timestamp / runtime information
```

## 源码入口

```text
agent/prompt_builder.py
agent/context_engine.py
agent/context_compressor.py
agent/prompt_caching.py
agent/model_metadata.py
```

重点研究 prompt stability、context budget、压缩触发点以及为什么频繁修改稳定前缀会破坏缓存收益。
