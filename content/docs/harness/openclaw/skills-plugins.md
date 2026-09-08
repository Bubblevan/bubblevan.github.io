---
title: "OpenClaw Skills 与 Plugins：Instruction、Capability 与 Extension"
weight: 7
draft: true
---

> 占位页：把 Skill、Tool、Hook、Plugin 和 Harness 放到同一张边界图中，避免把 instruction、capability 和 authorization 混为一谈。

## 初始区分

| 概念 | 本质 | 是否直接执行动作 | 是否等于授权 |
| --- | --- | --- | --- |
| Skill | Markdown instruction | 否 | 否 |
| Tool | callable capability | 是 | 需要 policy |
| Hook | lifecycle interception | 间接 | 可参与 guard |
| Plugin | core extension package | 可以注册多种能力 | 位于 Gateway trust domain |
| Harness | Agent Runtime 的实现 | 控制 agent turn | 取决于 runtime |

Skill eligibility 不等于 Tool authorization。Skill 教 Agent 何时以及怎样使用工具，Tool 才提供可调用能力，Policy 决定这次调用能否发生。

## 源码入口

```text
src/plugins/
src/plugin-sdk/
extensions/
```

后续正文需要关注 Plugin SDK 的 typed contract、Provider / Channel / Agent Harness / CLI Backend 等注册能力，以及 experimental API 的版本兼容边界。
