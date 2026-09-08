---
title: "OpenClaw：从 Gateway 到 Agent Runtime 的 Harness 架构"
weight: 1
---

## 这组笔记要回答什么

OpenClaw 不应被理解成另一个简单的 `LLM → Tool → LLM` 示例。它更接近一个长期在线的 Agent System：把外部消息、Gateway、Session、Agent Runtime、Tools、Memory、Security、Plugins、Multi-Agent 和 Automation 接到同一条运行链上。

这也是它和 Codex 最重要的差异：

```text
Codex：一个 agent turn 如何运行？

OpenClaw：一个长期在线的 Agent System，如何把外部世界、Agent Runtime
          和持久状态接起来？
```

本目录借用 Codex 的研究方法，但不机械复制 Codex 的文件名：每篇专题都沿着“官方设计描述 → 当前源码入口 → struct/function/event 执行链 → 最小实验 → 面试问题”向下钻。

## OpenClaw 的层次边界

最重要的第一张图不是功能列表，而是 Provider、Model、Runtime、Harness 和 Channel 的边界：

```text
Provider
    ↓
认证、模型发现、请求准备

Model
    ↓
本轮真正选择的模型

Agent Runtime
    ↓
执行 prepared turn 的低层 agent loop / backend

Harness
    ↓
Agent Runtime 的具体实现

Channel
    ↓
消息从哪里进入、从哪里送出
```

OpenClaw 的核心系统图可以压缩成：

```text
External World
      │
      ▼
   Channel
      │
      ▼
   Gateway
      │
      ├── routing / binding
      ├── session / persistence
      ├── memory / context
      └── policy / security
      │
      ▼
 Prepared Turn
      │
      ▼
 Agent Runtime
      │
      ▼
 Model ↔ Tools
      │
      ▼
 events / transcript / delivery
```

因此，“Provider 和 Agent Runtime 有什么区别”不能只回答成“OpenAI / Anthropic 是 Provider，OpenClaw 是 Agent”。更精确的拆法是：Provider 负责认证与模型目录，Model 是本轮模型，Runtime 决定谁拥有 agent loop，Harness 是 Runtime 的实现，Channel 负责通信表面。

## 一条消息怎样穿过系统

本目录的主线是从一条 WhatsApp、Telegram、Discord、Slack、WebChat 或 CLI 消息开始：

```text
Channel ingress
      ↓
Gateway
      ↓
authentication / pairing
      ↓
normalize inbound message
      ↓
binding / routing
      ↓
sessionKey
      ↓
agent RPC
      ↓
prepared turn
      ↓
Agent Runtime
      ↓
Model / Tool loop
      ↓
streaming events + persistence
      ↓
Gateway
      ↓
Channel delivery
```

Gateway 是长期运行的 daemon，而不是一次性 API wrapper。它统一持有 messaging surfaces，客户端和 device nodes 通过 WebSocket 接入，同时处理协议、鉴权、pairing、routing、agent event、heartbeat 和 cron。

## 专题导航

| 页面 | 主要问题 | 研究重点 |
| --- | --- | --- |
| [gateway](gateway/) | 外部消息怎样进入某个 Agent？ | channel、Gateway、WS、binding、sessionKey、delivery |
| [runtime](runtime/) | 一次 prepared turn 如何真正执行？ | embedded runner、Agent、agent loop、queue、stream、persistence |
| [runtimes](runtimes/) | 到底谁拥有 Agent Loop？ | OpenClaw、Codex、Pi 等 Runtime ownership |
| [session-context](session-context/) | 状态和上下文怎样维持？ | transcript、workspace、skills、context engine、compaction |
| [tools](tools/) | Tool 如何进入本轮可见能力？ | candidate、policy、sandbox、loop detection、result sanitize |
| [skills-plugins](skills-plugins/) | Skill、Tool、Hook、Plugin 如何区分？ | instruction、capability、lifecycle、typed extension contract |
| [memory](memory/) | 什么被写进长期记忆？ | Markdown memory、retrieval、flush、dreaming、provenance |
| [security](security/) | LLM 的真实安全边界在哪里？ | auth、pairing、policy、approval、sandbox、plugin trust |
| [multi-agent](multi-agent/) | 多 Agent 的不同层次是什么？ | routing isolation、child agent、external runtime |
| [automation](automation/) | 没有用户消息时如何继续工作？ | heartbeat、cron、standing intent、retry、delivery |

建议优先完成：`gateway.md → runtime.md → runtimes.md → session-context.md → tools.md → security.md`。之后再扩展 Memory、Extensibility、Multi-Agent 和 Persistent Autonomy。

## 研究与证据边界

每篇成熟文章至少留下四个工件：

```text
① 一张系统图
② 一条源码调用链
③ 一个可复现实验 / log
④ 3～8 个逆向面试问题
```

源码和实验应以固定版本为基线。当前规划暂以 OpenClaw `2026.9.2` 作为待核实的版本线索；正式正文需要补充 commit SHA、检查日期和实际源码路径。官方文档与 pinned source 是主证据，自己的测试和日志用于验证，git history / PR / issue 用于解释演化，第三方博客只用来寻找入口。

需要特别区分事实和推断：源码能证明 Runtime primitive、状态字段或事件链，但不能仅凭目录名推断完整产品架构。Plugin SDK 处于快速变化的边界时，应 pin host version 并记录兼容性。

## 与其他 Agent 知识的边界

OpenClaw 适合 Agent Engineering、Agent Infra、Harness 和 Applied Agent 面试；它回答的是：

```text
训练好的模型
      ↓
怎样被放进一个长期运行的 Agent System
```

它不替代 Search-R1、Agentic RL 或 GRPO 这类模型策略与训练主题。相关内容继续放在 `agent`、`eval`、`orchestration` 和 `self-evolve` 体系中，不在这里重复。
