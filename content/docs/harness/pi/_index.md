---
title: "Pi：从 Minimal Agent Loop 到 Agent Harness"
weight: 5
---

## 为什么单独研究 Pi

Pi 不应放在 OpenClaw 下面。它和 OpenClaw 是两条不同的 Harness 设计路线：

```text
Pi
  minimal / composable harness
        ↓
Oh My Pi
  IDE-wired coding harness
        ↓
OpenClaw
  persistent agent platform
```

官方 Pi 仍然最适合作为“最小 Harness”教材：核心负责 Agent Loop、messages、tools、state 和 session；extensions、skills、prompt templates、themes 和 packages 负责把它扩展成具体 Coding Agent。这里的 minimal 不是源码行数少，而是核心不替用户预设所有 workflow。

## 官方项目与研究边界

主线固定研究官方 `earendil-works/pi`，而不是第三方 Rust port。Pi 当前 monorepo 的关键层次可以先压缩成：

```text
pi-ai
    ↓
unified multi-provider LLM API

pi-agent-core
    ↓
agent runtime / tool calling / state management

pi-coding-agent
    ↓
interactive coding agent CLI
```

Oh My Pi 作为最后的对照实验：它是 Pi 的 fork，加入 LSP、DAP、持久化 REPL、subagents、advisor、memory 和 native tooling，用来观察一个 minimal harness 面对 IDE 和生产 Coding Agent 需求时会增加什么。

## 这组笔记的主线

```text
User / UI
    ↓ prompt / steer
AgentHarness
    ↓ session / lane / queue / retry / abort
Agent Loop
    ↓ transform / convert context
pi-ai provider
    ↓ stream
AssistantMessage
    ↓ tool calls?
Tool execution
    ↓
ToolResultMessage
    ↓ append to context
下一轮 inference
```

核心问题不是“Pi 支持 Tool Calling”，而是：**模型输出 tool call 后，状态如何变化、结果如何回到 context、何时重试、何时中止，以及这些控制面为什么不应该全部塞进最小 loop。**

## 页面导航

| 页面 | 主要问题 | 研究重点 |
| --- | --- | --- |
| [runtime](runtime/) | 一条 Prompt 如何完成完整 Agent Loop？ | `agent-loop.ts`、stream、tool call、observation |
| [state-machine](state-machine/) | Agent Loop 之上为什么还需要 AgentHarness？ | lane、operation、queue、retry、abort、events |
| [context-session](context-session/) | Message、Context、Transcript 和 Compaction 如何区分？ | transform、convert、session、navigation |
| [tools](tools/) | Tool 如何声明、验证、执行并重新进入模型？ | dispatch、schema、parallel、failure、abort |
| [steering](steering/) | Agent 执行中用户追加输入如何处理？ | steering、follow-up、interrupt、queue semantics |
| [extensions](extensions/) | Minimal core 如何扩展成 Coding Agent？ | hooks、skills、templates、packages、extensions |
| [providers](providers/) | 为什么 Harness 不应直接绑定单一 API？ | provider、model、stream、adapter、fallback |
| [security](security/) | Pi 的安全边界为什么较轻？ | containerization、tool boundary、host responsibility |
| [protocol](protocol/) | 如何把 Harness 从 TUI 解耦？ | client、server、protocol、RPC |
| [evals](evals/) | 如何证明 Harness 改动真的有效？ | evals、telemetry、trajectory、regression |
| [oh-my-pi](oh-my-pi/) | Minimal Pi 如何长成 IDE-aware Agent？ | LSP、DAP、REPL、native core、subagents |

建议先连续阅读 `runtime.md → state-machine.md`，再读 `context-session.md → tools.md → steering.md`。这条顺序先建立执行循环，再解释为什么要有 Harness 控制平面。

## 源码快照与写作粒度

每篇正文应固定仓库、commit 和检查日期。当前规划使用：

```yaml
source:
  repo: earendil-works/pi
  commit: f53ac1135149f03fd1e2a5bfd29861120eaf5b96
  checked: 2026-09-08
```

源码文章的最低粒度是：

```text
一个问题
    ↓
一个源码入口
    ↓
一个关键 type / function
    ↓
一条完整执行路径
    ↓
至少一个 state mutation
    ↓
一个真实 input → intermediate state → output
    ↓
一个失败路径 / edge case
    ↓
设计原则
```

这意味着不要只写“Pi 支持 streaming”，而要追踪 event stream、partial message、context mutation、最终 AssistantMessage 和 abort 时的状态。

## 与其他 Harness 的坐标

| 项目 | 主要学习价值 |
| --- | --- |
| Pi | minimalism：Agent Harness 的不可再约简核心 |
| Claude Code | production：权限、上下文、验证和长任务运行时 |
| Codex | protocol/runtime boundary：Runtime 与 App Server 的边界 |
| DSH | composition：Plugin、依赖注入和能力组合 |
| OpenClaw | platform：Gateway、Channel 和持久 Agent System |
| Hermes | self-evolution：Memory、Skills、Trajectory 和优化 |

## 参考入口

- [Pi Coding Agent](https://pi.dev/)
- [earendil-works/pi](https://github.com/earendil-works/pi)
- [Oh My Pi](https://github.com/can1357/oh-my-pi)
