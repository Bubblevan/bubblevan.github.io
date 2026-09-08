---
title: "DSH Protocol：SDK、API 与 ACP 边界"
weight: 12
draft: true
---

> 占位页：研究 DSH Harness Core 如何通过 Typert、RPC、SDK、API 和 ACP 服务 TypeScript、Python、Editor 或 Automation Client。

## 预期主线

```text
Harness Core
      ↓
Typert / RPC
      ↓
SDK server
      ↓
TypeScript / Python SDK
```

```text
Harness
      ↓
ACP
      ↓
Editor / Automation Client
```

## 源码入口

```text
packages/sdk/
packages/api/
packages/typert/
packages/acp/
packages/host/
```

后续正文要说明协议如何表达 Session Event、Tool、Approval、Streaming、Abort 和 Runtime Capability，而不是只列 API endpoint。
