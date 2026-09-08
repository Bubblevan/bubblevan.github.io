---
title: "DSH Capability Seams：Definition、Provider 与 Consumer"
weight: 5
draft: true
---

> 占位页：用 FS、Shell、Subprocess 和 Sandbox 说明可替换 capability seam 如何隔离接口、实现和使用方。

## 预期结构

```text
Service Definition
        ↓
Service Provider
        ↓
Consumer
```

```text
FS Service Definition
       ├── Local Provider
       └── Remote Provider
                ↓
             FS Tools
```

```text
Shell Tool
    ↓
Shell Service
    ↓
Subprocess Service
    ↓
Sandbox
    ↓
OS
```

## 源码入口

```text
packages/fs/
packages/shell/
packages/subprocess/
packages/sandbox/
```

核心面试问题：如何设计可替换 local / remote execution 的 Agent Harness，而不让每个 Tool 直接依赖具体 Provider？
