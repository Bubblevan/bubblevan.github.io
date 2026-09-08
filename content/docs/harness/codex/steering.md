---
title: "Codex Steering：AGENTS.md、Skills 与配置"
weight: 7
draft: true
---

> 占位页：研究项目指令、Skills、配置和 prompt construction 如何进入运行时，并持续影响模型的行动边界。

## 预期主线

```text
repository / user instructions
    ↓
AGENTS.md discovery
    ↓
config + skills + environment
    ↓
prompt / context construction
    ↓
model-visible capabilities
```

重点区分 durable steering 与一次性 prompt：前者应可审阅、可版本化、可随项目恢复；后者只表达当前任务。

## 源码入口

```text
codex-rs/core/src/agents_md*
codex-rs/core/src/skills/
codex-rs/core/src/config/
prompt / context construction
```

后续正文要记录指令发现顺序、作用域、冲突处理以及 Skills 对工具面和上下文的影响。
