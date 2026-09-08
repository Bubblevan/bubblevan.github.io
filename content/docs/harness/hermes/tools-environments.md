---
title: "Hermes Tools 与 Environments：Capability 不等于执行环境"
weight: 4
draft: true
---

> 占位页：研究集中式 Tool Registry 如何发现、收集 schema、审批和 dispatch 工具，并将工具能力与实际执行环境解耦。

## 预期主线

```text
tools/registry.py
      ↑
tools/*.py
      ↑
model_tools.py
      ↑
AIAgent
      ↓
local / Docker / SSH / Daytona / Modal / Singularity
```

## 源码入口

```text
tools/registry.py
tools/approval.py
tools/process_registry.py
tools/environments/
tools/terminal_tool.py
tools/file_tools.py
tools/browser_tool.py
tools/code_execution_tool.py
tools/mcp_tool.py
```

后续正文要回答：为什么注册逻辑不应散落在 Agent Loop 中，以及 Capability 与 Execution Environment 如何分别测试和控制。
