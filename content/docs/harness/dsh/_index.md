---
title: "DeepSeek Harness：当 Agent Loop 本身也是 Plugin"
weight: 4
---

## 为什么单独研究 DSH

Pi 的核心问题是“最小 Agent Loop 到底是什么”，Codex / Claude Code 的核心问题是“生产 Coding Harness 如何组织 Runtime、Session、Tools 和安全边界”。

DSH 最有区分度的问题则是：

> **怎样把一个 Agent Harness 设计成可组合、可替换、可卸载的 capability graph？**

DSH 的底层是 Cordis。Model adapter、tool registry、session log、agent loop 等能力都可以作为 Plugin 挂载 Service、typed event 和可撤销的 Effect。甚至 Agent Loop 本身也不是不可替换的 privileged core。

## 一张总图

```text
                         Cordis Context
                              │
             ┌────────────────┼────────────────┐
             │                │                │
         Agent Loop       Session Log       LLM Service
             │                │                │
             ├────── events ──┼────────────────┤
             │                │                │
             ▼                ▼                ▼
           Tools          Compaction        Providers
             │
        ┌────┼────┬──────┬─────┐
        ▼    ▼    ▼      ▼     ▼
       FS  Shell  LSP    Web  Subagent
        │    │
        └─ Subprocess
             │
           Sandbox
```

所有箭头都应该能追到同一套结构：

```text
Service Definition
        ↓
Service Provider
        ↓
Consumer
        ↓
Cordis registration / effect
```

这就是 DSH 与其他 Harness 的主要差异：它研究的不只是“如何执行一个 Agent”，而是“如何让执行能力成为可替换的系统组合”。

## 运行时基本单位：Step 与 Turn

DSH 当前把一次运行明确拆成两层：

```text
Turn
└── Step 0
    ├── claim input
    ├── assemble prompt / tools
    ├── model request
    ├── assistant stream
    ├── tool calls
    ├── tool results
    └── step/end
└── Step 1
    └── ...
└── turn/end
```

```text
Step = 一次 model request + 它调用的 tools
Turn = 0 个或多个 Step
```

这条区分会贯穿 runtime、session、tools、compaction 和 observability，而不是停留在术语层面。

## 页面导航

| 页面 | 主要问题 | 研究重点 |
| --- | --- | --- |
| [runtime](runtime/) | 一个 DSH Turn / Step 到底如何运行？ | Inbox、claim、model request、stream、tool、next step |
| [session](session/) | 为什么 append-only event log 是 source of truth？ | SessionEvent、projection、deriveMessages、replay |
| [tools](tools/) | Tool call 如何穿过 registry、hook 和 execution？ | schema、approval、execute、result、failure |
| [composition](composition/) | Cordis、Profile、Bundle、Patch 如何组成 Harness？ | Plugin tree、Effect、profile overlay |
| [capability-seams](capability-seams/) | 为什么 Definition、Provider、Consumer 要拆开？ | FS、Shell、Subprocess、Sandbox seams |
| [context](context/) | Session log 如何变成 model request？ | prompt、injection、tool schema、immutable request |
| [compaction](compaction/) | 长上下文如何压缩而不破坏 durable history？ | projection、spill、truncate、compact |
| [subagents](subagents/) | 子 Agent 如何隔离、fork 和 continue？ | provider、lineage、continuation、persistent child |
| [workflow](workflow/) | Workflow Engine 与 Multi-Agent 有什么区别？ | worker thread、workflow tool、Ralph |
| [security](security/) | Approval、Credential、Sandbox 如何分层？ | interaction、credentials、policy、subprocess |
| [extensions](extensions/) | Harness 如何允许运行期自修改？ | live service inspection、mount、unmount |
| [protocol](protocol/) | Harness 如何暴露给 SDK、ACP 和 Web Client？ | SDK、API、Typert、ACP、Host |
| [observability](observability/) | Retry、Failure、Tool、Stream 如何重放和诊断？ | events、attempt、telemetry、session-query |

建议优先阅读：`runtime.md → session.md → tools.md → composition.md → capability-seams.md → context.md → compaction.md`。

## DSH 与其他 Harness 的坐标

```text
Pi
  Minimal Agent Runtime
        ↓
Claude Code / Codex
  Production Coding Harness
        ↓
DSH
  Composable / Replaceable Harness
        ↓
OpenClaw
  Persistent Agent Platform
```

DSH 的主题不是“插件越多越好”，而是把可替换能力从中央 Runtime 中抽出来，用明确的 Service Definition 和 Consumer 依赖它们，进而支持不同 Profile、Provider、环境和组合方式。

## 源码快照与证据链

本轮第一版固定以下源码快照：

```yaml
source:
  repo: deepseek-ai/deepseek-harness
  commit: c389f96bf3a9b6807cb71ed6bdad5849be0df6d8
  checked: 2026-09-08
```

推荐证据顺序：

```text
官方 Architecture / Subsystem README
        ↓
Package README
        ↓
实际 TypeScript
        ↓
Tests / architecture notes
        ↓
PR / commit
        ↓
最小实验
```

每篇正文都应尽量留下：一个问题、一个源码入口、一条执行链、至少一个状态变化、一个失败路径和一个可复现实验。不要只把 DSH 概括成“Context、Skill、Multi-Agent、Plugin 都有”。

## 暂不单独展开的主题

当前没有足够证据把 `memory` 作为一级 capability family；它先放在 session、session-query、storage、goal 和 skill 等机制中观察。Prefix cache 先作为 context 中的 request stability / immutable prefix / provider cache behavior 研究，不预先为它创造独立文章。
