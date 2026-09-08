---
title: "Hermes Agent：从 Agent Runtime 到 Learning Harness"
weight: 6
---

## 为什么单独研究 Hermes

Hermes 与 OpenClaw 适合回答不同的问题：

```text
OpenClaw
  Persistent Agent System / Agent Platform
  Gateway + Channel + Runtime + Session + Security + Multi-Agent

Hermes
  Agent Harness + Research Runtime
  Agent Loop + Tools + Context + Memory + Skills
  + Trajectory + Batch Eval + RL + Self-Evolution
```

Hermes 的认知中心不是 Gateway，而是一个 platform-agnostic 的 `AIAgent`。CLI、Gateway、ACP、Batch Runner、API Server 和 Python Library 都应是不同入口，最终汇入同一个 Agent Core：

```text
CLI / Gateway / ACP / Batch / API
              │
              ▼
           AIAgent
              │
      ┌───────┼────────┐
      ▼       ▼        ▼
   Prompt  Provider   Tools
   Builder  Resolution Dispatch
```

因此本目录不是 Hermes 使用教程，而是研究：**一个 Agent Harness 如何从稳定的 Runtime Core 连接到 Memory、Skills、Trajectory、Evaluation 和 Self-Evolution。**

## 一条完整研究主线

```text
User Input
    ↓
AIAgent / Agent Loop
    ↓
Prompt + Provider + Tool Environment
    ↓
Model inference
    ↓
tool call / observation
    ↓
Session + Memory + Trajectory
    ↓
Skill reuse / Batch Eval / RL data
    ↓
Prompt、Skill 或 Runtime 的下一次改进
```

Hermes 的学习价值正好在中间：它不是只研究如何运行 Agent，也不是直接研究模型策略训练，而是研究运行时如何产生可检索、可评估、可优化的经验。

## 页面导航

| 页面 | 主要问题 | 研究重点 |
| --- | --- | --- |
| [runtime](runtime/) | 一条 Prompt 如何穿过完整 Agent Loop？ | `AIAgent`、turn、tool call、retry、persistence |
| [prompt-context](prompt-context/) | Prompt 的稳定层级如何保持？ | stable / context / volatile、压缩、缓存 |
| [provider](provider/) | Model 与 Provider 如何解耦？ | API mode、auth、adapter、fallback |
| [tools-environments](tools-environments/) | Capability 如何与执行环境解耦？ | registry、approval、local / Docker / SSH / Modal |
| [session-memory](session-memory/) | Session、History、Context、Memory 如何区分？ | SQLite、FTS5、retrieval、lineage |
| [skills-learning](skills-learning/) | 一次经验何时应抽象成 Skill？ | procedural memory、复用、更新和失效 |
| [subagents](subagents/) | Child Agent 如何被委派和回收？ | delegate tool、隔离、深度、结果消费 |
| [gateway](gateway/) | 平台适配如何不污染 Agent Core？ | adapter、pairing、delivery、session |
| [trajectory-rl](trajectory-rl/) | Runtime Trace 怎样变成研究数据？ | batch、trajectory、export、Atropos、reward |
| [self-evolution](self-evolution/) | Agent 如何在评测门控下改进？ | DSPy、GEPA、candidate、regression gate、PR |
| [security](security/) | Tool、凭证和环境的边界在哪里？ | approval、credential passthrough、sandbox、pairing |

建议优先阅读：`runtime.md → prompt-context.md → tools-environments.md → session-memory.md → skills-learning.md → trajectory-rl.md → self-evolution.md`。Gateway、Provider、Subagents 和 Security 作为第二梯队补充。

## 与 Codex、OpenClaw 的对照

| 项目 | 最值得学的东西 | 最适合回答 |
| --- | --- | --- |
| Codex | Coding loop、Thread、Tools、Sandbox、App Server | 成熟 Coding Harness 如何划分 Runtime 与协议边界 |
| OpenClaw | Gateway、Channel、持久 Session、Runtime ownership | 长期在线 Agent Platform 如何运行 |
| Hermes | AIAgent、Provider、Tools / Environment、Skills、Trajectory、Self-Evolution | Harness 怎样连接 Agent Research 与 Learning |

## 证据边界

Hermes 主体是 Python，官方源码与文档是主证据。正文应固定 source baseline、commit SHA 和检查日期；第三方材料只用于寻找入口。特别是 self-evolution 仓库要区分：哪些能力已经实现，哪些仍是 roadmap，不能把计划写成现状。

每篇成熟文章至少留下：

```text
一张执行图
一条源码调用链
一个可复现实验或 log
3～8 个面试问题
```

## 参考入口

- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs/)
- [NousResearch/Hermes-Agent](https://github.com/NousResearch/Hermes-Agent)
- [Hermes Agent self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution)
