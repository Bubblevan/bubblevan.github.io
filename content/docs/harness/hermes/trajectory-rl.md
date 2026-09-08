---
title: "Hermes Trajectory 与 RL：从运行时轨迹到研究数据"
weight: 9
draft: true
---

> 占位页：研究 Hermes 如何批量运行任务、导出 trajectory，并把 Agent Runtime 与评估、RL rollout 和训练接口接起来。

## 预期主线

```text
Agent Runtime
    ↓
run tasks
    ↓
collect trajectories
    ↓
normalize / export
    ↓
evaluate
    ↓
train / optimize
    ↓
new policy / prompt / skill
```

## 源码入口

```text
batch_runner.py
agent/trajectory.py
Atropos integration
```

## 核心研究问题

- Tool call 是 action，tool result 是 observation 吗？
- 哪些 token 应进入 loss？
- 失败 trajectory 是否应该保存？
- Online Agent Session 如何变成 offline training data？
- Harness telemetry 与 RL rollout logger 有什么区别？
