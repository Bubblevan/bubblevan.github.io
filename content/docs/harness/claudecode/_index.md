---
title: "Claude Code：从源码快照理解 Harness"
weight: 1
---

## 9. 面试复盘——如果只给我五分钟，我会怎么讲 Claude Code Harness？

### 9.1 不要背模块，先讲清楚 Harness 到底在解决什么

如果面试官问我：

> 你最近看 Claude Code 源码和 Anthropic 的 Harness 文章，有什么收获？

我不会从：

```text
QueryEngine
Tool.ts
AgentTool
Permission
MCP
```

开始报菜名。

因为这很容易讲成：

> Claude Code 有一个会话管理模块、一个 Tool 模块、一个权限模块……

听完以后，对方还是不知道：

> **为什么这些东西必须存在？**

我现在更愿意从一个矛盾开始：

> **一个模型明明已经会读代码、改代码、跑命令，为什么把任务从 10 分钟拉到几个小时以后，可靠性还是会明显下降？**

Anthropic 的长任务实验给出的答案不是：

```text
模型不会写代码
```

而是：

```text
任务持续时间变长以后，
失败开始发生在模型之外。
```

比如：

```text
上下文越来越长
→ 目标漂移 / 提前收尾

模型想执行动作
→ 真实世界需要安全执行

修改已经发生
→ 不代表功能真的完成

一次进程挂掉
→ 任务不能跟着消失

多个 Agent 并行
→ 状态和副作用不能互相踩

模型升级
→ 旧 Harness 甚至可能反过来成为负担
```

所以我现在对 Harness Engineering 的理解是：

> **模型负责提出下一步，Harness 负责让一个长任务在现实世界里能够持续、受控、可观察、可验证地向前推进。**

---

#### 面试最可能追问的四个问题

| 面试官可能问                                     | 我会怎么回答                                                                                                                                                                                                    |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Harness 和普通 Agent Loop 有什么区别？**       | Demo 里的 Agent Loop 往往只是 `LLM → Tool → LLM`；生产 Harness 还要长期维护 session state、权限、预算、取消、工具副作用、并发、持久化和恢复。Claude Code 的 `QueryEngine` 很能说明这一点：一次模型调用结束了，会话仍然必须继续存在。                                             |
| **2. Tool 不就是 Function Calling 吗？**        | 不是。模型生成 `tool_use` 只是动作提议，Harness 才真正执行。生产 Tool 还需要 schema、validation、permission、effect metadata、interrupt semantics、result mapping 等 contract。否则上层根本不知道这个动作能不能执行、能不能并发、结果如何反馈。                           |
| **3. 为什么还需要 Evaluator / Multi-Agent？**     | 不是因为“Agent 越多越强”，而是某些职责需要隔离。Generator 容易沿着自己的实现轨迹自我确认，因此可以拆出 Evaluator，主动寻找“任务还没完成”的反例；Planner 则解决 raw prompt 容易 underscope。Multi-Agent 的价值来自 role boundary，而不是开几个聊天窗口。                                   |
| **4. 那是不是 Planner、Evaluator、Reset 越多越可靠？** | 也不是。Anthropic 最重要的结论之一就是 Harness 是 model-relative scaffolding。Sonnet 4.5 需要 Context Reset，Opus 4.5 可以删；Opus 4.6 又让 Sprint decomposition 变得没那么必要。每个 Harness component 都应该对应一个可复现 failure，并在模型升级后重新 ablate。 |

这四个问题基本可以覆盖整篇文章。

---

#### 如果只让我讲 30 秒

我会说：

> Claude Code 源码让我意识到，生产 Agent 真正困难的部分不是再套一层 ReAct，而是模型调用以外的 runtime。比如 `QueryEngine` 要维护跨 turn 的会话状态并把用户消息提前持久化以支持 resume；Tool 不是普通函数，它带有 validation、permission、并发和副作用语义；模型的 `tool_use` 只是动作 proposal，Harness 执行后得到的 `tool_result` 才是真实反馈。Anthropic 的长任务实验又把这个问题往上推了一层：长任务还需要独立 verification、role-specialized agents 和持续的 Harness ablation。所以我现在更愿意把 Harness 理解成 Agent 与真实世界之间的运行时，而不只是 Prompt 或编排框架。

---

#### 如果面试官追问：“那 Claude Code 里的核心对象是谁？”

我会先答：

```text
QueryEngine
```

但不会停在：

> 它是 query engine。

而会说：

> `query()` 更像一次用户 turn 内部的模型—工具循环，而 `QueryEngine` 管的是整个 conversation 怎样持续活着。

它拥有的不是只有：

```text
messages
```

还有：

```text
permission denials
usage
read-file state
abort controller
skill / memory state
```

所以：

```text
Conversation State
≠
LLM Message History
```

更进一步：

```text
Model Context
≠
Conversation State
≠
Durable Task State
```

这是我看这份源码以后最想记住的一组区分。

---

#### 如果面试官问：“为什么提前写 Transcript 这么重要？”

我会直接举源码里的 crash window。

天真实现：

```text
用户发送消息
    ↓
等 Claude 回答
    ↓
最后保存 Transcript
```

问题是：

```text
消息已经被系统接受
    ↓
API 还没返回
    ↓
进程挂了
```

这时用户认为：

```text
这个任务已经开始
```

但恢复系统可能认为：

```text
这段 conversation 根本不存在
```

所以 Claude Code 会在进入后面的 query loop 以前，就先把用户消息写入 transcript。

这不是为了日志好看。

而是在定义：

> **从什么时候开始，这个任务状态应该被认为已经持久存在。**

我会把它类比成：

```text
write-before-execute intuition
```

但不会说：

> Claude Code 实现了数据库 WAL。

因为源码没有证明完整事务语义。

---

#### 如果面试官问：“Tool 为什么设计得那么复杂？”

我会回答：

> 因为 Tool 是模型和真实副作用之间的边界。

普通函数只关心：

```text
Input
↓
Output
```

生产 Agent 还要知道：

```text
Input 合法吗？
        ↓
当前 Context 下能运行吗？
        ↓
用户授权了吗？
        ↓
它会不会修改状态？
        ↓
是否 destructive？
        ↓
是否 concurrency-safe？
        ↓
用户打断时 cancel 还是 block？
        ↓
结果应该怎样进入模型 Context？
```

所以可以用一个帮助记忆的式子：

```text
Tool
≈
Capability
+
Schema
+
Policy Hooks
+
Effect Metadata
+
Execution
+
Observation Mapping
```

不是正式公式。

但比：

```text
Tool = Function Calling
```

准确很多。

---

#### 如果面试官接着问：“那 Tool 为什么不能全部 Promise.all？”

因为：

```text
同一轮模型提出
≠
这些动作没有因果依赖
```

Claude Code 真正判断的是：

```text
isConcurrencySafe(input)
```

而不是简单：

```text
Read = parallel
Write = serial
```

并且：

```text
无法解析 input
```

或者：

```text
并发安全判断本身异常
```

都会保守退回串行。

更重要的是，它只合并**相邻**的 safe calls。

例如：

```text
A safe
B safe
C unsafe
D safe
E safe
```

会变成：

```text
[A || B]
    ↓
    C
    ↓
[D || E]
```

而不是为了 throughput 把：

```text
A B D E
```

全部提到 C 前面。

所以一句话：

> **并发可以重叠执行，但不能随便重写原始 happens-before。**

---

#### 如果面试官问：“Permission 不就是 Tool 白名单吗？”

我会说：

> Tool whitelist 决定 Capability，Permission 决定一次具体 Invocation 的 Authorization。

因为：

```text
Bash("git status")
```

和：

```text
Bash("git push --force")
```

都叫 Bash。

但显然不能只靠：

```text
Bash = safe / dangerous
```

二分类。

Claude Code 的 Permission model 至少能表达：

```text
allow
ask
deny
```

并结合：

```text
Tool
Input
Rule Content
Rule Source
Permission Mode
Working Directory Scope
```

判断。

所以最重要的区分是：

```text
Capability:
模型可以请求什么

Authorization:
系统允许什么真正发生
```

而：

```text
ask
```

也不是失败。

它表示：

> 当前动作刚好落在 Agent 自治边界之外，所以把 decision boundary 交还给人。

---

#### 如果面试官问：“Evaluator 为什么有用？”

我会先反问一句：

> 谁写代码、谁写测试、谁跑测试、谁解释测试、最后还是谁宣布完成，会不会有点危险？

因为整个链可能共享同一个错误假设：

```text
误解需求
    ↓
按误解实现
    ↓
按误解写测试
    ↓
测试全绿
    ↓
高置信宣布完成
```

所以独立 Evaluator 的价值不是：

```text
它一定比 Generator 聪明
```

而是：

```text
Generator:
寻找让任务完成的方法

Evaluator:
寻找“任务其实没完成”的反例
```

两个角色的 objective 不一样。

---

#### 如果再问：“那 Evaluator 看代码不就够了吗？”

不够。

因为：

```text
Implementation exists
≠
Behavior works
```

典型情况是：

```text
函数已经写了
Route 已经定义了
Component 已经存在
```

但真实用户操作：

```text
点击
拖动
保存
刷新
调用 API
```

以后就是失败。

所以 Anthropic 给 Evaluator Playwright MCP，让它去操作运行中的 App，并同时检查：

```text
UI
API
Database
```

我会把证据强度简单记成：

```text
Implementation Evidence
        ↓
Execution Evidence
        ↓
Behavior Evidence
```

任务越接近真实产品，Verification 就越应该向后两层走。

---

#### “有 Evaluator”同样不是终点

这是 Anthropic 那篇文章里我非常喜欢的一点。

早期 Evaluator 会：

```text
发现真实 Bug
    ↓
自己解释：
“其实问题不大”
    ↓
PASS
```

或者：

```text
只测 Happy Path
    ↓
没发现深层问题
    ↓
PASS
```

所以最后变成：

```text
Generator 需要 Eval

Evaluator
同样需要 Eval
```

Anthropic 真正做的是：

```text
运行真实任务
    ↓
看 Evaluator Trace
    ↓
找到它和人工判断不同的地方
    ↓
调整 Prompt / Criteria / Threshold
    ↓
重跑
```

这让我觉得：

> **Harness Engineering 很大一部分其实是 trace-driven debugging。**

调试的对象只是从：

```text
普通程序
```

变成了：

```text
Model behavior + Runtime policy
```

---

#### 如果问：“Multi-Agent 是不是未来必然方向？”

我的回答会非常保守：

> 不一定。Multi-Agent 应该来源于明确的 failure mode，而不是架构审美。

比如：

```text
raw prompt 容易 underscope
→ Planner

Generator 自评偏乐观
→ Evaluator

大量探索污染主 Context
→ Research Subagent
```

而不是：

```text
任务复杂
→ 那就开 8 个 Agent
```

对我来说，一个 Subagent 最好能回答五件事：

```text
Goal
Context
Tools
Artifact
Consumer
```

说不清这五个边界，多半只是在：

```text
“多开一个 Claude。”
```

---

#### Claude Code 的 `AgentTool` 和 Anthropic 三 Agent Harness 要严格分开

这个是很容易在面试里说错的一点。

Anthropic 长任务实验：

```text
Planner
Generator
Evaluator
```

是建立在 Claude Agent SDK 上的**上层实验 Harness**。

而 Claude Code v2.1.88 的 `AgentTool` 源码能证明的是 runtime 提供了：

```text
subagent_type
model override
background execution
permission mode
cwd
worktree isolation
```

这些 delegation primitive。

因此：

```text
AgentTool
```

能证明：

> Claude Code 可以运行和隔离其他 Agent。

不能证明：

> Claude Code 内部固定就是 Planner → Generator → Evaluator。

一句好记的话：

```text
Primitive 回答：
“怎样把另一个 Agent 跑起来？”

Architecture 回答：
“为什么这里需要另一个 Agent？”
```

---

#### 如果面试官最后问：“所以你会怎么设计自己的 Harness？”

我不会先画：

```text
Planner
Memory
RAG
Multi-Agent
Evaluator
Graph
```

然后告诉他：

> 这是我的 Agent 架构。

我会先做：

```text
真实任务
    ↓
Baseline Agent
    ↓
读取 Trace
    ↓
找到反复出现的 Failure
```

然后每次只针对一个 Failure 加结构。

例如：

```text
状态经常丢
→ Persistence / Handoff

动作容易越权
→ Permission

并发发生冲突
→ Effect-aware Scheduling

自评太乐观
→ Independent Evaluator

Evaluator 太宽松
→ Calibration

Raw Prompt 总 underscope
→ Planner
```

最后还要记录：

```text
为什么加？

什么时候可以删？
```

因为模型升级以后需要重新 ablate。

---

#### 这也是为什么我不会把 Anthropic 那套架构叫“最佳实践”

它更像一组：

```text
failure → intervention → experiment
```

的案例。

最重要的不是：

```text
Anthropic 用了 Planner，
所以我也必须用 Planner。
```

而是：

```text
Anthropic 发现 raw prompt 下
Generator 经常 underscope，
所以加 Planner。

后来重新实验，
Planner 仍然提供增益，
于是继续保留。
```

这两句话看起来只差一点。

但工程思维完全不同。

---

# 最终映射：父文的五个动词，到 Claude Code / Anthropic Harness

整篇文章最终可以重新压回父文的五个动词：

| Harness 责任 | 在本文里真正落到了哪里                                                                                                                               |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **找到**     | `QueryEngine` 组装当前 Context；Memory / searchable artifacts；组织层的 Slack、Docs、代码、会议记录，以及“Recorded ∩ Discoverable ∩ Authorized”的 Context        |
| **行动**     | Model 生成 `tool_use`；Tool contract 把 proposal 映射成真实 filesystem / shell / MCP / Agent effect                                                |
| **观察**     | `tool_result`、stdout / stderr、运行中的 App、Playwright、API、DB，以及 Evaluator 得到的真实 behavior evidence                                             |
| **约束**     | Schema、`validateInput()`、Permission allow/ask/deny、working-directory scope、effect-aware scheduling、Sprint Contract、verification threshold |
| **修正**     | Query loop 根据 Tool Result 继续推理；Evaluator failure evidence 回流 Generator；Compaction / Resume 维持长期任务；人通过 trace 调 Harness 本身                  |

所以最终：

```text
找到
↓
得到足够正确的当前状态

行动
↓
让模型意图进入现实世界

观察
↓
把现实结果重新带回来

约束
↓
限制什么能发生、怎样发生、什么算完成

修正
↓
根据差异继续改变系统
```

这五步真正连起来以后：

```text
Agent
```

才不再只是：

```text
一个会调用 Tool 的 LLM
```

而逐渐成为：

```text
一个能够在现实环境里
持续推进任务的执行系统。
```

---

#### 最后一句

如果半年以后我只记得这篇文章的一句话，我希望是：

> **Harness Engineering 不是给模型外面堆更多 Agent、Prompt 和 Workflow，而是在模型能力之外，把长任务继续存在、真实行动、获得反馈、受到约束、验证完成以及失败恢复这些责任，明确地交给运行时；然后随着模型变强，再持续删除已经不再必要的那部分脚手架。**

这应该比记住：

```text
QueryEngine.ts
Tool.ts
AgentTool.tsx
```

本身更重要。
