---
title: "Hermes Self-Evolution：评测门控下的外部优化"
weight: 10
draft: true
---

> 占位页：研究 `hermes-agent-self-evolution` 如何作用于 Hermes，而不是把“Agent 修改自己并直接上线”当成实现事实。

## 预期主线

```text
current skill / prompt / tool
    ↓
generate eval dataset
    ↓
execution traces
    ↓
DSPy + GEPA
    ↓
candidate variants
    ↓
evaluation + regression gates
    ↓
best variant
    ↓
PR + human review
```

## 证据边界

需要明确区分已实现与 roadmap：当前优先研究 Skill evolution；tool descriptions、system prompts、tool implementation code 和 continuous improvement loop 不能在没有源码证据时写成已完成能力。

## 主要参考

- [Hermes Agent self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution)
- [PLAN.md](https://github.com/NousResearch/hermes-agent-self-evolution/blob/main/PLAN.md)
