---
title: "DSH Workflow：编排引擎不等于 Multi-Agent"
weight: 9
draft: true
---

> 占位页：研究 workflow seam、worker-thread engine、workflow tool 和 Ralph，回答 Workflow Engine 与 Agent Orchestration 是否是同一个抽象。

## 预期边界

```text
Agent
  ├── agent loop
  └── subagent delegation

Workflow
  ├── worker thread
  ├── durable steps
  ├── workflow tool
  └── Ralph / repeated execution
```

## 源码入口

```text
packages/workflow/
packages/jobs/
workflow tool
ralph tool
```

后续正文要重点分析任务状态、重试、持久化和 worker 生命周期，而不是再次介绍 Multi-Agent 理论。
