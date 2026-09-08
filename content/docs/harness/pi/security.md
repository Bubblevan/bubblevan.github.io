---
title: "Pi Security：轻量核心与安全责任边界"
weight: 8
draft: true
---

> 占位页：研究为什么 Pi 没有默认复制 Claude Code 式完整 permission system，以及安全责任如何落在 Tool、Execution Environment 和宿主侧。

## 预期问题

```text
minimal core
    ≠
没有安全问题
```

需要区分 tool contract、用户确认、containerization、工作目录、网络、凭证和宿主权限。后续正文应明确哪些保护由 Pi 提供，哪些必须由使用 Pi 的 Coding Agent 或外部环境负责。

## 参考入口

```text
README.md
containerization.md
packages/agent/
packages/coding-agent/
```
