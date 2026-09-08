---
title: "Hermes Security：Approval、Credential 与 Execution Boundary"
weight: 11
draft: true
---

> 占位页：研究危险命令检测、approval、credential passthrough、terminal environment、container isolation 和 Gateway pairing 的边界。

## 预期问题

```text
Agent 运行在 Docker / SSH / Modal
        ≠
credential、filesystem、network 自动安全
```

需要分别追踪 Tool approval、凭证文件、环境变量透传、执行环境、容器隔离和 Gateway pairing，而不是把它们统称为 sandbox。

## 源码入口

```text
tools/approval.py
tools/credential_files.py
tools/env_passthrough.py
tools/environments/
gateway/pairing.py
```
