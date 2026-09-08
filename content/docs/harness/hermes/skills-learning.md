---
title: "Hermes Skills Learning：从经验到 Procedural Memory"
weight: 6
draft: true
---

> 占位页：研究 Hermes 何时把一条 trajectory 抽象成可复用 Skill，以及如何处理过拟合、冲突、重复和过期。

## 预期主线

```text
experience
    ↓
candidate reusable behavior
    ↓
abstraction
    ↓
skill representation
    ↓
reuse
    ↓
feedback
    ↓
update
```

这篇是 Hermes 的核心特色之一：Skill 不只是静态说明文件，也可能成为 procedural memory。重点不是安装 Skill，而是研究 skill selection、skill explosion、duplicate / stale skill、instruction conflict 和错误经验固化。
