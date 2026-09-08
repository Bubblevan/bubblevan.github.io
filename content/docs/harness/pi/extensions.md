---
title: "Pi Extensions：Minimal Core 如何扩展成 Coding Agent"
weight: 6
draft: true
---

> 占位页：研究 Pi 如何把 workflow、skills、prompt templates、hooks 和 packages 留在核心之外，以保持 minimalism。

## 预期边界

```text
Core Agent Loop
        ↓
hooks / events / skills / prompt templates
        ↓
coding-agent extensions / packages
```

## 待回答的问题

- 什么应该进入 core，什么应该成为 extension？
- Skill 与 Extension 如何区分？
- Extension 如何改变 tool、context 或 runtime？
- 第三方 extension 可能破坏哪些 invariant？
- 为什么 Pi 不默认内置 sub-agents 和 plan mode？

## 源码入口

```text
packages/agent/src/hooks.ts
packages/agent/src/events.ts
packages/agent/src/skills.ts
packages/agent/src/prompt-templates.ts
packages/coding-agent/src/extensions/
```
