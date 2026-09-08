---
title: "Pi Steering：执行中的输入、Follow-up 与 Queue"
weight: 5
draft: true
---

> 占位页：研究 Agent 正在生成或执行工具时，用户的新消息如何通过 steering 或 follow-up 进入运行时。

## 预期区分

```text
模型正在生成 / 工具正在执行
            │
            ▼
      steering queue
            │
            ▼
下一次 assistant response 前注入
```

```text
agent 原本准备结束
            ↓
检查 follow-up queue
            ↓
有消息则重新进入 inner loop
```

## 待回答的问题

- steer、follow-up、interrupt、abort 的边界是什么？
- 新输入是在当前 turn 还是下一个 turn 注入？
- queue 如何与 lane、retry 和 session state 协作？
- 如何处理用户说“不要继续修改某个文件”时的竞态？

## 源码入口

```text
packages/agent/src/agent-loop.ts
packages/agent/src/runtime/
packages/agent/src/events.ts
```
