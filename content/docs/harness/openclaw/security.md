---
title: "OpenClaw Security：Gateway Trust Boundary 与 Tool Sandbox"
weight: 9
draft: true
---

> 占位页：从 trust boundary 出发解释 Gateway、Plugin、Workspace、Tool policy 和 Sandbox 的真实安全边界。

## 关键判断

开启 sandbox 后，被隔离的主要是 Tool execution，不是整个 OpenClaw Gateway：

```text
Host
├── Gateway
├── Plugin runtime
├── Session state
├── Routing
└── tool request
          ↓
Sandbox backend
  Docker / Podman / SSH / OpenShell
          ↓
    exec / file / browser
```

不要把它简化成“OpenClaw 整体运行在 Docker 中”。还要分别研究 Authentication、Pairing、Tool policy、Approval、Sandbox、Workspace permissions、Plugin trust 和 Network policy。

## 必须保留的边界

> Workspace 是默认 cwd，不是 hard security boundary。

后续正文需要用实际配置、请求和执行日志证明每一层的作用范围，并说明 Gateway 重启或 Sandbox backend 故障时的失败行为。
