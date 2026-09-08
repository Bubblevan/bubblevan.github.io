---
title: "Codex Harness：从长期工作系统到开源运行时"
weight: 1
---

## 这组笔记要回答什么

这里的核心判断是：**Codex 作为产品族并非全部开源，但 Codex CLI / harness 的主体足够公开，适合沿着官方源码做一套可验证的运行时学习。** `openai/codex` 是公开的 Rust 项目；因此，学习时可以把官方工程文章、固定 commit 的源码、Git 历史以及实验日志串成一条证据链，而不必把第三方逆向结果当成最终事实。

这套内容同时保留两个层次：

1. **Codex 怎么被用成长期工作系统**：durable threads、文件化记忆、steering、heartbeat、goals、工具连接和 artifact review。
2. **Codex 为什么能这样工作**：agent loop、session state、工具路由、权限与 sandbox、App Server 以及 subagent runtime。

前者对应 Codex-maxxing 的工作方法，后者对应 OpenAI 工程文章和 `openai/codex` 源码。不要把“如何使用 Codex”和“Codex 内部如何运行”混成一篇。

## 谈话里最值得保留的精髓

### 1. Harness 不只是 `LLM → Tool → LLM`

一次可靠的长任务还需要维护线程、上下文、持久化、取消、预算、权限、工具副作用、并发、恢复和验证。模型提出下一步，Harness 把提议映射成真实动作，再把真实结果重新编码进下一轮输入：

```text
用户 / Client
    ↓
Thread / Session
    ↓
Model inference
    ↓
tool call（动作提议）
    ↓
ToolRouter + policy + sandbox
    ↓
真实环境中的执行
    ↓
tool result（现实反馈）
    ↓
下一轮 inference 或结束
```

所以 Agent loop 真正循环的不是“思考”，而是**动作与现实反馈**。尤其要保留失败结果：命令失败、权限拒绝和测试失败都必须进入 trajectory，否则模型会在一个虚假的世界状态上继续推理。

### 2. 长期上下文不是一份聊天记录

学习 Codex 时应明确区分：

```text
Conversation History
        ≠ Model Context
        ≠ Thread Runtime State
        ≠ Turn Runtime State
```

线程需要持久化和恢复，模型上下文需要构建和压缩，turn 还要管理 pending approval、用户输入、动态工具和中断等运行时状态。自动 compaction 解决的是容量和连续性问题，不等于所有长期记忆都应该塞进对话；AGENTS.md、项目笔记、TODO 和可审阅 artifact 才是更稳定的外部记忆。

### 3. 工具是能力与副作用之间的契约

Tool availability 不是简单的静态白名单。Codex 会根据 session、turn、环境、MCP、apps 和候选工具构造本轮真正暴露给模型的工具集合，然后经过路由、权限、sandbox 和执行，最后把结果映射回模型。

```text
tool spec
    ↓
model-visible tool
    ↓
ToolRouter / ToolRegistry
    ↓
approval + sandbox
    ↓
execution / parallelism
    ↓
ResponseInputItem
```

这也解释了为什么“模型能请求什么”和“这次请求是否被允许”必须分开；并发也不能只按工具名称判断，而要尊重副作用与 happens-before 关系。

### 4. 安全边界是互补的两层

approval 回答“这次动作是否需要人批准”，sandbox 回答“即使获准，动作还能触碰哪些资源”。网络、凭证、规则、managed config 和审计又构成更外围的控制面。后续安全笔记会重点保留这条执行链：

```text
model request
    ↓
tool policy
    ↓
approval decision
    ↓
permission profile
    ↓
sandbox transform
    ↓
OS enforcement
    ↓
spawn
```

### 5. 多 Agent 不是默认答案

Planner、Evaluator、Research subagent 或 background agent 都应该由可复现的 failure mode 驱动：目标容易 underscope、生成者自评过于乐观、探索污染主上下文，或任务需要隔离。源码里的 spawn / wait / delegation primitive 只能证明“系统可以运行另一个 Agent”，不能自动证明产品内部固定采用某种 Planner → Generator → Evaluator 架构。

## 学习路线与占位页

| 页面 | 要回答的问题 | 主要证据入口 |
| --- | --- | --- |
| [runtime](runtime/) | 一条 prompt 如何经过完整 agent loop？ | `cli/`、`ThreadManager`、`Session`、`session/turn.rs` |
| [app-server](app-server/) | Harness 如何服务不同 Client？ | `app-server/`、`app-server-protocol/` |
| [session](session/) | Thread、context、history 和 compaction 如何协作？ | `session/`、`state/`、`compact.rs`、rollout / thread store |
| [tools](tools/) | 工具如何动态暴露、路由、并发和回传？ | `core/src/tools/`、MCP、skills |
| [security](security/) | approval、permission profile 和 sandbox 如何分层？ | `sandboxing/`、`exec_policy.rs` |
| [steering](steering/) | AGENTS.md、Skills、config 如何影响行为？ | agents instructions、skills、config、prompt construction |
| [subagents](subagents/) | 当前多 Agent primitive 如何实现和隔离？ | delegation tools、spawn / wait、agent graph |

建议先读 `runtime.md`，再读 `session.md` 和 `tools.md`，最后进入 `security.md`、`steering.md` 与 `subagents.md`。这条顺序先建立“动作—反馈”的主循环，再补齐状态、能力和约束。

## 证据边界

官方工程文章和 `openai/codex` 当前源码是主证据；第三方源码导读和知识库只作为目录地图，具体文件路径和架构判断必须回到固定 commit 核实。Codex 仓库变化很快，后续正文应记录观察时的 commit、源码路径和必要的实验结果。

外围的 Harness Engineering、Symphony 和 self-improving systems 属于“用 Codex 组成更大系统”的上层主题，不在本目录重复展开；它们分别保留在 `harness`、`orchestration` 和 `self-evolve` 的既有体系中。

## 参考入口

- [openai/codex](https://github.com/openai/codex)
- [Unrolling the Codex agent loop](https://openai.com/index/unrolling-the-codex-agent-loop/)
- [Unlocking the Codex harness](https://openai.com/index/unlocking-the-codex-harness/)
- [Running Codex safely at OpenAI](https://openai.com/index/running-codex-safely/)
- [Building a safe, effective sandbox to enable Codex on Windows](https://openai.com/index/building-codex-windows-sandbox/)
