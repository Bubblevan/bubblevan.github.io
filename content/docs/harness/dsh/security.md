---
title: "DSH Security：Interaction、Credential 与 Sandbox"
weight: 10
draft: true
---

> 占位页：从 Model Request 到 OS 执行，拆解 approval、credential reference、capability policy、sandbox 和 subprocess 的安全分层。

## 预期主线

```text
Model request
      ↓
Tool
      ↓
Interaction / approval
      ↓
Credential references
      ↓
Capability policy
      ↓
Sandbox
      ↓
Subprocess
```

`interaction` 不只是弹窗，而是 human-collaboration plane：包括 approval、permission preset 和 ask-user tool。后续正文需要与 Credentials、Sandbox、Hooks 和 Subprocess 的实现边界对应。

## 源码入口

```text
packages/interaction/
packages/credentials/
packages/sandbox/
packages/subprocess/
packages/hooks/
```
