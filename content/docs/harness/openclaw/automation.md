---
title: "OpenClaw Automation：Heartbeat、Cron 与 Persistent Agent"
weight: 11
draft: true
---

> 占位页：解释当用户没有正在发消息时，OpenClaw 如何通过 heartbeat、cron 和 standing intent 继续推进工作。

## 概念区分

```text
Memory
    “以后需要知道什么”

Cron
    “某个确定时间做什么”

Heartbeat
    “周期性醒来检查什么”

Standing Intent
    “某个未来条件发生时做什么”

Session
    “当前这次工作进行到哪里”
```

## 研究范围

覆盖 background work、delivery、retry、timeout、settlement、事件幂等和失败恢复。重点不是把 Persistent Agent 描述成长上下文聊天，而是说明无人主动发消息时，runtime 如何重新获得执行机会并把结果送达。

后续正文应给出至少一条可复现实验：配置一个周期任务，观察唤醒、session 选择、执行、持久化、delivery 和重试日志。
