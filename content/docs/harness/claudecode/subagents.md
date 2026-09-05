---
title: "Claude Code Subagents：AgentTool、隔离与生命周期"
weight: 4
---

## 1. 到这里再看 Claude Code 的 `AgentTool`

现在把镜头从 Anthropic 的**上层实验 Harness**拉回 Claude Code v2.1.88 源码。

`AgentTool.tsx` 的 Tool 描述非常直接：

```text
Launch a new agent
```

它的 search hint 也是让模型可以：

```text
delegate work to a subagent
```

基础 input schema 至少包含：

```ts
description
prompt
subagent_type?
model?
run_in_background?
```

扩展参数里还可以出现：

```ts
name?
team_name?
mode?
isolation?
cwd?
```

这里非常值得停一下。

因为这几组参数刚好说明：

```text
“启动另一个 Agent”
```

并不只是：

```text
再调用一次模型 API
```

Harness 还要决定：

```text
它做什么任务？
        → prompt

它是什么 Agent 类型？
        → subagent_type

用什么模型？
        → model

同步等它还是后台跑？
        → run_in_background

在哪工作？
        → cwd

是否隔离代码环境？
        → isolation = worktree

采用什么权限模式？
        → mode
```

所以 Agent 本身也变成一个可配置 runtime unit。

---

### 1.1 `subagent_type` 特别能说明“Role”不是名字

源码允许：

```ts
subagent_type?: string
```

这意味着父 Agent 可以说：

```text
这项任务不要由“我自己继续想”
完成。

我要把它交给
某一种 specialized agent。
```

真正的角色差异可以进一步对应：

```text
不同 system prompt
不同 Tool set
不同 MCP requirements
不同 permission rules
不同 model
```

实际上 `AgentTool` 在生成自己的 prompt 时，会先根据当前可用 MCP Server 和 permission rule 过滤 Agent definition，再决定哪些 Agent 类型能展示给模型。

所以：

```text
Agent role
```

至少可以成为 runtime 配置的一部分，而不是自然语言标签。

---

### 1.2 `model` 又说明一个角色不必和一种模型绑定

源码还允许：

```ts
model:
  'sonnet'
  | 'opus'
  | 'haiku'
```

作为可选 override。

这意味着：

```text
role
```

和：

```text
model
```

是两个轴。

例如从 Harness 设计上完全可以有：

```text
Planner
→ 强模型

简单搜索型 subagent
→ 更便宜模型

Evaluator
→ 再根据任务难度决定模型
```

这里我不是说 Claude Code 已经固定这样配置。

源码能证明的只是：

> **AgentTool 提供了按 Agent invocation 选择模型的能力。**

这点很重要。

因为成熟 Multi-Agent Harness 的优化对象不仅有：

```text
结果质量
```

还有：

```text
latency
token
cost
```

没必要因为有三个角色，就强制所有角色都用最贵模型。

---

### 1.3 `run_in_background` 又改变了父子 Agent 的时间关系

如果子 Agent 必须：

```text
父 Agent 停下来
    ↓
等待 Subagent
    ↓
Subagent 完成
    ↓
父 Agent 继续
```

那 delegation 仍然是严格同步的。

但 `AgentTool` 的 schema 明确支持：

```ts
run_in_background
```

并且异步输出包含：

```text
status = async_launched
agentId
outputFile
```

于是父 Agent 可以：

```text
启动 Agent A
        ↓
Agent A 后台调查

同时
        ↓
父 Agent 继续别的工作
```

结果之后通过 Agent ID / output file 再被消费。

这说明 Multi-Agent runtime 还多了一个普通聊天系统没有的问题：

```text
lifecycle
```

谁在运行？

谁结束了？

谁在后台？

结果在哪里？

父 Agent 是否还活着？

这些都必须由 Harness 管理。

---

### 1.4 `isolation = worktree` 更能说明 Subagent 不只是“另一个脑子”

这是我觉得源码里最有工程味的参数之一：

```ts
isolation: 'worktree'
```

为什么 Agent 需要 worktree？

因为两个 Coding Agent 如果同时：

```text
Agent A
修改 src/auth.ts

Agent B
也修改 src/auth.ts
```

并且共享同一个 working tree：

```text
race
conflict
dirty state
```

马上出现。

所以给 Agent：

```text
独立 context
```

还不够。

有时候还需要：

```text
独立 filesystem state
```

可以画成：

```text
Parent repo
     │
     ├── Agent A
     │     ↓
     │   worktree A
     │
     └── Agent B
           ↓
         worktree B
```

这就提醒我：

> **Multi-Agent 隔离不只发生在 Prompt 层，也可能发生在真实工作环境层。**

这已经完全不是：

```text
复制一份 chat history
```

能够解决的问题了。

---

### 1.5 但这里必须特别强调证据边界

看到 `AgentTool` 有：

```text
subagent_type
model
background
worktree
team
```

以后，很容易写出一句：

> Claude Code 内部采用 Planner → Generator → Evaluator 架构。

**这句话是不成立的。**

我们目前有两套不同来源的证据。

#### Anthropic 文章证明的是

实验 Harness 建在 Claude Agent SDK 上，并显式设计成：

```text
Planner
    ↓
Generator
    ↔
Evaluator
```

每个角色承担不同职责。

#### Claude Code v2.1.88 源码证明的是

Claude Code runtime 提供：

```text
delegate task to subagent
specialized agent type
model override
background execution
worktree isolation
cwd
permission mode
```

等 primitive。

但源码**没有因此证明**：

```text
Claude Code 主循环
固定由 Planner / Generator / Evaluator
三个 Agent 组成。
```

两者的关系应该写成：

```text
Upper-level experimental Harness
────────────────────────────────

Planner
Generator
Evaluator
Contracts
QA loop

            可以建立在

Runtime primitives
────────────────────────────────

Agent SDK / AgentTool
subagent
tools
context
background
isolation
...
```

而不是：

```text
AgentTool
=
Planner / Generator / Evaluator
```

这是这一节最重要的证据边界。
