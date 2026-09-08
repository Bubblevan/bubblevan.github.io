---
title: "OpenClaw Tools：从 Capability 到 Turn-visible Tool"
weight: 6
draft: true
---

> 占位页：研究工具如何从注册能力变成本轮模型可见的 schema，并经过 policy、sandbox、执行、清理和持久化。

## 预期主线

```text
registered capability
    ↓
tool candidate
    ↓
runtime / channel capability
    ↓
allow / deny policy
    ↓
sandbox policy
    ↓
turn-visible Tool schema
    ↓
model tool call
    ↓
before_tool_call
    ↓
execution
    ↓
sanitize result
    ↓
after_tool_call → persist / stream
    ↓
next inference
```

## 源码入口

```text
src/agents/agent-tools.ts
src/agents/tool-loop-detection-config.ts
```

后续正文要回答 Tool list 是否动态构建、Skill 与 Tool 的区别、MCP 与 native Tool 的信任边界、结果截断和并发安全。
