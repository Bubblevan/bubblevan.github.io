---
title: "Hermes Runtime：AIAgent 如何运行一轮 Conversation"
weight: 1
draft: true
---

> 占位页：追踪 Hermes 从 CLI 输入到模型推理、工具 dispatch、下一轮 inference 和 SessionDB 持久化的完整链路。

## 预期主线

```text
HermesCLI.process_input()
    ↓
AIAgent.run_conversation()
    ↓
build_system_prompt()
    ↓
resolve_runtime_provider()
    ↓
model inference
    ↓
tool_calls?
    ↓
model_tools.handle_function_call()
    ↓
tool result → next model iteration
    ↓
final response → SessionDB
```

## 源码入口

```text
run_agent.py
agent/conversation_loop.py
agent/turn_*.py
```

后续重点回答：谁拥有 loop、turn 与 conversation 如何区分、异常和 interruption 如何传播、provider fallback 与 context compression 位于哪一层。
