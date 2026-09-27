---
schema: bubblevan/v1
id: project-stablepay-agent-commerce-bagua
content_kind: project
title: StablePay Agent Commerce / Backend 通用八股
linkTitle: 02 · 通用八股
weight: 20
aliases:
- /projects/stablepay/stablepay-agent-commerce-bagua/
date: 2026-09-19
updated: 2026-09-22
status: draft
visibility: public
projects:
- project-stablepay
summary: 面向 Agent Infrastructure、Go 后端与分布式系统面试的通用知识主教材，覆盖 Agent Runtime、Go、RPC、MySQL、Redis、MQ、可靠性、支付安全、Discovery 与生产工程。
topics:
- stablepay
- agent
- backend
- distributed-systems
- payment
- interview
---

如果说 [01 · StablePay Agent Commerce 项目面试追问](/projects/stablepay/01-stablepay%E9%A1%B9%E7%9B%AE%E9%9D%A2%E8%AF%95%E8%BF%BD%E9%97%AE/) 回答的是 **这个项目实际上做了什么、为什么这样做、源码在哪里、测试如何证明、当前边界是什么**，那么本文回答的就是： **这些设计背后的通用计算机知识是什么；换一个支付、订单、库存、云资源或 Agent Runtime 系统，这些原理为什么仍然成立。** 本文把问题分为三个等级：

| 维度 | P0：高频基础 | P1：工程追问 | P2：系统设计与高阶追问 |
|---|---|---|---|
| **定位** | 高频基础 | 工程追问 | 系统设计与高阶追问 |
| **应答目标** | 看到问题后应能在 **30～60 秒**内直接回答 | 通常来自 P0 的下一句 | 不要求所有岗位都完整掌握 |
| **核心要求** | 目标不是背一句定义，而是至少说清：<br>**是什么 → 解决什么问题 → 最基本的工作方式 → 一个最容易混淆的边界** | 应该能够画出**最小 failure trace**，并解释设计选择 | 主要用于回答：<br>• 为什么这个方案在生产环境仍可能失效；<br>• alternative 是什么；<br>• 系统真正维护的 invariant 是什么；<br>• 如何处理跨进程、跨存储、跨副作用的一致性；<br>• 一个“看起来能跑”的实现为什么还不能称为可靠系统 |
| **典型追问 / 高阶问题** | — | 为什么？<br>如果并发呢？<br>如果超时呢？<br>如果 crash 呢？<br>代价是什么？<br>还有别的方案吗？ | — |
| **示例 / 边界** | 例如“什么是幂等”，只回答“多次执行结果一样”是不够的，还应说明：<br>• 为什么网络系统需要幂等；<br>• 幂等不代表底层代码物理上只执行一次；<br>• side effect 是否重复才是很多业务真正关心的问题 | — | — |
| **学习覆盖建议** | 第一遍学习只覆盖 P0 | 第二遍补 P1 | 针对 **Agent Infra、后端基础设施、支付与分布式系统**岗位，再选择性进入 P2 |

## 1. Agent Runtime 与 Harness

传统后端服务通常收到一条明确命令，然后执行确定性代码。Agent 系统多了一层不确定性：

```text
环境事实
  ↓
模型解释
  ↓
提出下一步动作
  ↓
调用工具
  ↓
环境变化
  ↓
重新观察
```

模型可以帮助决定“下一步值得尝试什么”，但这并不意味着模型天然应该拥有数据库写权限、支付权限、删除权限或任意外部副作用权限。 Agent Runtime / Harness 的核心问题因此不是“怎样让模型会调用 Tool”，而是：**怎样让一个概率性 Decision Maker 在确定性的权限、状态、预算、时间和审计边界内行动。**

### 1.1 [P0] Agent、Workflow 与 Agent Loop 有什么区别？

**30 秒回答**

Workflow 的执行路径主要由开发者提前定义，例如固定 DAG 或状态机；Agent 则允许模型根据运行中的 Observation 决定下一步 Action。 Agent Loop 强调的是一个闭环：

```text
State
  ↓
Action
  ↓
Environment
  ↓
Observation
  ↓
Decision
  ↓
Next Action
```

关键是 **前一步 Observation 是否真的改变后一步 Action**。

**展开**

下面这段程序即使调用了 LLM：

```text
输入
→ LLM 总结
→ 固定调用 API A
→ 固定调用 API B
→ 返回
```

仍然更接近 workflow。 而：

```text
调用搜索
→ 返回没有结果
→ 模型决定修改 query
→ 再搜索
→ 找到候选
→ 访问候选
→ 根据页面内容决定是否继续
```

才有明显的 Agent Loop。 所以判断 Agent 的重点是 **运行时 Observation 是否参与下一步控制流。**

**最容易混淆的地方**

Agent 和 Workflow 不是非黑即白。 生产系统通常是外层 deterministic workflow + 局部 agentic decision 例如：

```text
创建任务
→ [Agent 决定检索策略]
→ 固定安全校验
→ [Agent 决定候选]
→ 固定执行边界
→ 固定审计
```

真正可靠的 Agent Runtime 往往不是把整个程序都交给模型。

### 1.2 [P0] Model、Tool、Memory、Harness 分别是什么？

**30 秒回答**

**Model** 负责推理和生成候选决策。 **Tool** 是 Agent 可以调用的外部能力，例如搜索、数据库查询、HTTP API、代码执行器。 **Memory** 保存可能影响未来决策的信息。

**Harness** 则负责把模型放进一个可执行系统：组织上下文、调用模型、解析输出、选择 Tool、限制权限、维护状态、处理 retry、记录 trace，并决定什么时候继续或停止。 可以理解成：

- Model = Brain-like decision component
- Tool = Hands
- Memory = Persistent / retrievable context
- Harness = Runtime + control plane

**为什么 Harness 容易被低估？**

直接调用一次模型很简单：`response = model(prompt)` 真正的 Agent 系统还必须处理：

```text
上下文从哪里来？
Tool schema 如何暴露？
模型返回非法参数怎么办？
Tool timeout 怎么办？
Tool 是否允许调用？
最多调用几次？
副作用是否需要审批？
状态由谁保存？
crash 后如何恢复？
怎么追踪一次完整 trajectory？
```

这些基本都属于 Harness / Runtime 问题。因此 Agent 工程的复杂度经常不在模型调用本身，而在模型周围的控制系统。

### 1.3 [P0] Tool Calling 和 Agent 有什么区别？

Tool Calling 是一种接口能力：模型可以结构化地产生“调用哪个函数、传什么参数”。 Agent 是运行模式：系统可以根据 Tool 的结果继续观察、决策和执行。 一次：

```text
用户问天气
→ 模型调用 weather()
→ 返回结果
```

可以只有一次 Tool Calling，并不存在明显的长循环。 而：

```text
search
→ inspect
→ search again
→ compare
→ call API
→ validate
→ stop
```

才体现 Agent Runtime。因此这属于一种包含关系。

### 1.4 [P0] ReAct 是什么？

ReAct 可以概括成：

```text
Reason
→ Act
→ Observe
→ Reason
→ Act
→ ...
```

模型不再只根据最初 prompt 一次生成答案，而是在每次 Tool result 后重新决策。 它解决的核心问题是：

> 很多任务无法在执行前预先知道完整路径。

| 维度 | 内容 |
|---|---|
| **ReAct 的优势** | 灵活 |
| **特别适合** | • Search<br>• Research<br>• Debugging<br>• 浏览网页<br>• 文件探索<br>• 长尾工具选择 |
| **ReAct 的问题** | 自由度太高 |
| **难以保证** | • 是否无限循环<br>• 是否重复调用昂贵 Tool<br>• 是否做危险副作用<br>• 是否基于 stale observation 行动<br>• 是否违反预算或 deadline |

因此生产系统很少只实现：

```python
while True:
    action = llm(history)
    observation = tool(action)
```

而不加任何控制边界。

### 1.5 [P0] State Machine 和 ReAct 怎么选？

**30 秒回答**

ReAct 适合路径难以提前枚举的问题；State Machine 适合合法状态和迁移必须清晰的问题。 它们通常不是二选一：

- State Machine 控制“哪些阶段允许做什么”
- ReAct / LLM 控制“某个阶段内选择哪个合法动作”

**示例**

支付状态：

```text
CREATED
→ AUTHORIZED
→ SUBMITTING
→ CONFIRMED
```

不适合让模型自由创造：

```text
"I think this payment is probably successful."
```

但在`DISCOVERING`阶段，模型可能可以参与候选选择。 所以更合理的架构是：

```text
LLM proposes
Runtime validates
State Machine commits
```

而不是`LLM decides state = CONFIRMED`

### 1.6 [P0] Observation、Action、Decision 有什么区别？

**30 秒回答**

**Action** 是系统实际执行的动作。 **Observation** 是执行之后从环境获得的事实。 **Decision** 是基于当前 State 和 Observation 对下一步 Action 的选择。

### 1.7 [P0] 为什么 LLM 输出不能直接等于 Side Effect？

因为模型输出本质上是一个不可信候选。 它可能：

* hallucinate；
* 使用过期上下文；
* 理解错 Tool schema；
* 被 prompt injection 影响；
* 超预算；
* 重复调用；
* 对同一请求给出不同结果。

如果：

```text
LLM:
transfer_money(to=X, amount=1000)
```

直接意味着：

```text
链上转账执行
```

模型就同时拥有：

```text
Decision authority
+
Authorization authority
+
Execution authority
```

安全边界几乎不存在。 更合理的是：

```text
LLM Proposal
      ↓
Deterministic Validation
      ↓
Authorization
      ↓
Execution
```

也就是：

```text
proposal ≠ permission
```

### 1.8 [P1] Proposal 和 Authorization 为什么必须分离？

Proposal 表示：

> “我建议这样做。”

Authorization 表示：

> “根据当前策略和事实，这个动作被允许执行。”

两者解决不同问题。 假设模型提出：

```json
{
  "action": "purchase",
  "merchant": "M1",
  "amount": 50
}
```

Runtime 仍可能检查：

```text
merchant 是否允许？
金额是否超过预算？
报价是否过期？
当前 State 是否允许支付？
是否已经支付过？
用户是否批准？
credential 是否有效？
deadline 是否已经超过？
```

任何一个条件失败：

```text
Proposal 可以存在
Authorization 仍然拒绝
```

**为什么这是 Agent Infra 的核心边界？**

因为 LLM 的优势是：

```text
开放世界推理
```

而 Side Effect 的要求是：

```text
封闭世界授权
```

开放世界允许：

> “我觉得这可能是正确动作。”

封闭世界要求：

> “只有满足明确规则的动作才能执行。”

Harness 就是把二者连接起来。

### 1.9 [P1] 为什么模型不应该拥有 Authoritative State Write？

假设 Episode 当前状态是：

```text
PAYING
```

模型返回：

```json
{
  "next_state": "FULFILLED"
}
```

如果系统直接接受，就会出现一个根本问题：

> 模型实际上绕过了环境事实。

真实链路可能根本没有：

```text
Payment confirmed
Entitlement valid
Delivery valid
```

**正确模式**

模型可以：

```text
提出 Action
```

但真正的状态变化应由：

```text
Current State
+
Verified Observation
+
Deterministic Transition Rule
```

计算。 即：

```text
next_state =
    Transition(
        current_state,
        validated_action,
        authoritative_observation
    )
```

而不是：

```text
next_state = llm_output.next_state
```

**好处**

这样未来即使替换模型：

```text
Model A
→ Model B
→ Rule-based Policy
```

状态正确性边界仍然不变。

### 1.10 [P1] 什么是 Bounded Agent Loop？

Bounded Loop 指 Agent 的执行不是：

```text
while not success:
    continue
```

而是在明确资源边界内运行。 常见限制包括：

```text
max_steps
max_tool_calls
max_retries
max_tokens
max_cost
deadline
max_side_effect_attempts
```

**为什么 step limit 还不够？**

因为：

```text
10 次搜索
```

和：

```text
10 次支付
```

风险完全不同。 所以成熟 Runtime 往往区分资源：

```text
TotalActionLimit
SearchAttemptLimit
PaymentAttemptLimit
DeliveryAttemptLimit
TokenBudget
MoneyBudget
WallClockDeadline
```

**本质**

bounded loop 解决的不是：

> “模型笨，会不会死循环？”

而是：

> **任何自动系统都必须存在资源耗尽和失败退出条件。**

### 1.11 [P1] Step Limit、Deadline、Budget Limit 有什么区别？

三者分别限制不同维度。

**Step Limit**

限制离散动作次数：

```text
最多调用 30 次 Tool
```

主要防：

* loop；
* runaway execution；
* API call explosion。

**Deadline**

限制墙钟时间：

```text
必须在 2 分钟内结束
```

即使只做了两步：

```text
Tool A 卡 70 秒
Tool B 卡 70 秒
```

也可能已经违反业务要求。

**Budget Limit**

限制资源消费：

```text
最多 $5
最多 10000 tokens
最多支付 20 USDC
```

即使动作次数很少，也可能产生高成本。 因此：

```text
steps != time != cost
```

不能互相替代。

### 1.12 [P1] 什么是 Stale Observation / Stale Proposal？

考虑：

```text
T0 Agent 读取状态 version=5
T1 模型开始推理
T2 另一个 worker 把状态推进到 version=6
T3 原模型返回基于 version=5 的 Proposal
```

这个 Proposal 可能在内容上完全合理，但已经过期。 这就是 stale proposal。

**为什么危险？**

因为 Decision 的逻辑前提已经不成立。 例如模型看到：

```text
payment_status = UNKNOWN
```

于是建议：

```text
retry
```

但在它思考期间，另一个 worker 已经完成 reconciliation：

```text
payment_status = CONFIRMED
```

旧 Proposal 如果继续执行，就可能产生重复 side effect。

**常见解决方式**

Proposal 绑定：

```text
state version
event sequence
observation sequence
ETag
snapshot hash
```

提交时执行：

```text
compare-and-swap
```

或者 Guard 重新校验：

```text
proposal.based_on_version == current.version
```

不匹配就拒绝并重新决策。

### 1.13 [P1] 为什么 Observation 要有 Provenance？

Observation 不能只保存：

```json
{
  "payment": "confirmed"
}
```

还应该能回答：

```text
谁产生的？
什么时候产生？
对应哪个请求？
来自哪个 Tool / API？
是否能验证？
关联哪个 tx？
内容有没有变化？
```

这就是 provenance。 常见形式包括：

```text
source
facts_ref
event_id
transaction_id
timestamp
content hash
signature
schema version
```

**为什么重要？**

因为 Agent 的 Decision 往往依赖多个来源：

```text
LLM observation
Tool output
Database fact
Remote API response
Human approval
Cached result
```

它们的可信等级完全不同。 如果全部变成一段 prompt 文本：

```text
"payment confirmed"
```

Runtime 就失去了判断事实来源的能力。

### 1.14 [P1] Deterministic Runtime 和 Probabilistic Model 如何分工？

可以用一个简单原则：

> **模型负责在开放空间里提出候选；Runtime 负责在封闭规则里批准和提交。**

适合模型：

* 理解自然语言目标；
* query reformulation；
* semantic ranking；
* 解释 Tool error；
* 从多个合法候选中提出选择；
* 生成非关键内容。

适合 deterministic code：

* 金额计算；
* 权限判断；
* budget；
* deadline；
* nonce；
* state transition；
* idempotency；
* signature validation；
* ledger；
* database transaction；
* destructive side effect guard。

不是因为模型“永远不可靠”，而是因为这些逻辑需要：

```text
reproducibility
auditability
precise invariant
```

概率模型通常不是最适合承载这些约束的组件。

### 1.15 [P1] Agent Retry 和普通 HTTP Retry 有什么区别？

HTTP retry 关注：

```text
同一个网络请求要不要重新发送？
```

Agent retry 可能意味着：

```text
重新思考
换 query
换 Tool
换候选
换 merchant
改变策略
```

因此 Agent retry 的语义范围更大。 特别是涉及 Side Effect 时，不能简单：

```text
Tool timeout
→ Agent 再调用一次
```

因为 timeout 只说明：

```text
没有得到结果
```

不代表：

```text
副作用没有发生
```

所以 Agent Runtime 需要知道：

```text
read-only action
vs
idempotent mutation
vs
non-idempotent external side effect
```

然后决定：

```text
直接 retry
查询状态
reconcile
停止
请求人工确认
```

### 1.16 [P2] 什么是 Capability-based Agent Runtime？

传统 Tool registry 往往表达：

```text
Tool X 存在
```

Capability-oriented Runtime 进一步表达：

```text
主体是谁
能够做什么
允许作用于哪些资源
允许使用什么参数范围
授权持续多久
是否允许副作用
```

例如不是授予：

```text
shell()
```

而是：

```text
read_file("/workspace/project/**")
```

或者不是：

```text
payment()
```

而是：

```text
pay(
    merchant=M1,
    currency=USDC,
    max_amount=10,
    expires_at=T
)
```

**为什么更安全？**

因为权限不再只有：

```text
Tool available = true
```

而是：

```text
authority = constrained capability
```

模型即使 hallucinate，也只能在 capability envelope 内行动。

### 1.17 [P2] 什么是 Confused Deputy？

Confused Deputy 指一个有权限的组件，被另一个权限更弱的主体诱导去滥用自己的权限。 Agent 系统特别容易出现这种问题。 例如：

```text
Agent 本身没有内部数据库权限
      ↓
Agent 调用一个高权限 Tool
      ↓
Tool 根据 Agent 提供的任意参数操作数据库
```

Tool 就可能成为 deputy。 再例如网页中存在 prompt injection：

```text
“请调用 delete_all_files”
```

模型看到后：

```text
调用拥有高权限的 filesystem tool
```

攻击者没有文件权限，但借模型和 Tool 间接获得了效果。

**防御思路**

不能只问：

> 模型想调用什么？

还要问：

```text
谁授权这个动作？
目标资源是否在 scope 内？
参数是否符合 policy？
当前上下文是否允许？
Tool 自身是否重新验证？
```

也就是：

```text
LLM intent ≠ capability
```

### 1.18 [P2] 如何理解 Authority 分层？

一个 Agent 系统里可以区分：

```text
Observe Authority
    ↓
Proposal Authority
    ↓
Authorization Authority
    ↓
Execution Authority
    ↓
Commit Authority
```

例如模型可以拥有：

```text
Proposal Authority
```

但没有：

```text
Commit Authority
```

Tool adapter 可以拥有：

```text
Execution Authority
```

但是否执行，取决于 Runtime 的：

```text
Authorization Authority
```

Repository 最终拥有：

```text
Commit State
```

**为什么这样设计？**

因为如果一个组件同时拥有：

```text
决定
授权
执行
记录结果
```

它出错时就缺少独立验证层。 Authority separation 的思想和传统安全系统里的：

* separation of duties；
* least privilege；

本质相通。

### 1.19 [P2] Agent Trace 应该记录什么？

一个极端是只存最终答案，另一个极端是把模型所有内部生成内容永久保存。 更实用的 trace 通常关注：

```text
Input identity
State before
Action
Tool invocation
Observation
Fact references
Proposal
Runtime verdict
State after
Cost
Latency
Error
Model/version
Tool/version
```

**为什么不应该把“完整思考文本”当核心事实？**

因为真正需要 replay 和 audit 的通常是：

```text
模型基于什么已知事实
提出了什么动作
Runtime 为什么允许/拒绝
外部世界返回了什么
系统状态最终如何变化
```

而不是依赖不可验证的自然语言 reasoning 作为状态事实。 可以保存 rationale 用于 debugging，但：

```text
rationale ≠ authoritative fact
```

### 1.20 [P2] State Machine 会不会限制 Agent 能力？

会。 如果开发者枚举`A → B → C` 而现实任务经常需要`A → D → F → B`

过度刚性的 State Machine 会让 Agent 的开放世界能力失去意义。

**解决方式不是放弃 State Machine**

而是缩小它负责的范围。 例如：

```text
┌─────────────────────────────┐
│ DISCOVERY                   │
│                             │
│  Agent 可以自由 search      │
│  inspect / compare / rank   │
│                             │
└──────────────┬──────────────┘
               │
      Runtime validates
               ↓
┌─────────────────────────────┐
│ AUTHORIZED_EXECUTION        │
│                             │
│ deterministic transition    │
└─────────────────────────────┘
```

也就是：

```text
Agentic inside a bounded phase
Deterministic across authority boundaries
```

- State Machine 管安全与业务 invariant
- Agent 管开放世界搜索空间

这通常比“所有东西都是状态机”或“所有东西都交给 ReAct”更实用。

### 1.21 总结

**1.21.1 本章高频对比**

| 概念 A           | 概念 B                | 关键区别                                    |
| -------------- | ------------------- | --------------------------------------- |
| Workflow       | Agent               | 路径主要预定义 vs 根据 Observation 动态决定          |
| Tool Calling   | Agent               | 一次结构化调用能力 vs 持续 Observation–Action Loop |
| Proposal       | Authorization       | 建议做什么 vs 是否允许做                          |
| Decision       | Fact                | 对下一步的判断 vs 已经发生的事实                      |
| LLM state      | Authoritative state | 上下文中的表示 vs 系统事实源                        |
| Retry          | Reconciliation      | 再执行一次 vs 先确认之前到底发生了什么                   |
| Step limit     | Deadline            | 动作数量约束 vs 墙钟时间约束                        |
| Budget         | Attempt limit       | 资源消耗约束 vs 执行次数约束                        |
| Rationale      | Evidence            | 模型解释 vs 可验证事实依据                         |
| Tool available | Capability granted  | 能发现一个工具 vs 当前主体有权执行某范围动作                |

**1.21.2 面试前一分钟速记**

```text
Agent 的关键不是“用了 LLM”，而是 Observation 会改变下一步 Action。

Tool Calling ≠ Agent。

Proposal ≠ Authorization。

LLM output ≠ Fact。

Model 可以提出动作，
Runtime 决定动作是否合法，
Tool 执行动作，
Repository / external system 提供权威事实。

副作用越不可逆，
越不能让模型同时拥有 Decision + Authorization + Commit 权限。

Agent Loop 必须 bounded：
step / retry / deadline / budget 各管不同资源。

Proposal 必须绑定当前事实版本，
否则会出现 stale decision。

Observation 必须有 provenance，
否则 Runtime 无法区分模型文本与可信事实。

最常见生产形态不是
“纯 ReAct”
或
“纯 State Machine”，
而是：

bounded agentic decision
+
deterministic authority boundary
```

**1.21.3 StablePay 映射**

本章只保留概念映射，不重复实现：

```text
Proposal / Authorization separation
→ DecisionProposal / Runtime Guard

Authoritative State
→ CommerceEpisode / EpisodeEvent

Bounded execution
→ deadline / attempt / budget constraints

Observation provenance
→ facts_ref / payload_hash / external factual actions

Capability-constrained selection
→ CandidateSet / selection guard

Runtime-owned facts
→ payment / entitlement 等事实不能由模型 Proposal 直接提交
```

具体字段、状态迁移、源码函数、测试和当前 IMPLEMENTED / PLANNED 边界，统一回到 [01 · StablePay Agent Commerce 项目面试追问](/projects/stablepay/01-stablepay%E9%A1%B9%E7%9B%AE%E9%9D%A2%E8%AF%95%E8%BF%BD%E9%97%AE/)。

## 2. Go 语言与并发

StablePay 当前主体已经是 Go 微服务，Go 也是国内后端、基础设施和 Agent Runtime 岗位中很常见的一条追问线。 这一章按 Go 程序真正运行时会遇到的问题组织：

```text
语言对象
  ↓
内存共享
  ↓
Goroutine
  ↓
调度
  ↓
同步
  ↓
取消与生命周期
  ↓
资源控制
  ↓
GC / 性能
  ↓
生产排障
```

面试时最危险的回答方式是只背：

> Goroutine 很轻量，Channel 用来通信，Go 有 GMP。

真正的追问通常马上变成：

```text
轻量在哪里？
GMP 分别是什么？
goroutine 阻塞后发生什么？
channel 为什么会 deadlock？
谁应该 close channel？
context cancellation 怎么传？
map 为什么不能并发写？
mutex 和 channel 到底怎么选？
goroutine 泄漏怎么查？
10 万 goroutine 一定没问题吗？
```

### 2.1 [P0] Goroutine 和 OS Thread 有什么区别？

**30 秒回答**

Goroutine 是由 Go Runtime 管理的 **用户态并发执行单元**，OS Thread 是由操作系统内核调度的线程。 大量 goroutine 会复用较少数量的 OS threads：

```text
Many Goroutines
      ↓
Go Scheduler
      ↓
OS Threads
      ↓
CPU Cores
```

goroutine 的初始栈和创建、切换成本通常比直接创建 OS thread 小，所以 Go 可以比较自然地使用“一个请求 / 一个任务 / 一个 worker 一个 goroutine”的编程模型。 但 `goroutine ≠ free thread` 它仍然消耗：

* stack；
* scheduler bookkeeping；
* heap object；
* channel / timer；
* file descriptor；
* downstream connection；
* CPU。

**为什么 Goroutine 比 Thread 轻？**

1. goroutine 栈可以从较小规模开始并按需增长；
2. goroutine 的调度主要由 Go Runtime 完成；
3. 多个 goroutine 复用 OS thread；
4. goroutine creation / switching 通常比 kernel thread 更便宜。

因此可以支持比“一个连接一个 OS thread”更高的并发度。

**但 Goroutine 不等于 Parallelism**

Concurrency = 多个任务可以交错推进 Parallelism = 多个任务在不同 CPU core 同时执行 单核上可以有大量 goroutine，但不存在真正的 CPU parallel execution。

### 2.2 [P0] Go 的 GMP 调度模型是什么？

**30 秒回答**

简化地说：

* **G**：Goroutine；
* **M**：Machine，可以理解为承载 Go 代码执行的 OS thread；
* **P**：Processor，Runtime 的逻辑执行资源，维护可运行 goroutine 等调度状态。

更准确地说，是 M 持有 P，执行 P 调度到的 G。

**为什么需要 P？**

如果只有 `G ↔ M`，Runtime 很难高效组织：

* runnable queue；
* scheduler state；
* memory allocation cache；
* work stealing。

引入 P 后：

```text
P0 → local run queue
P1 → local run queue
P2 → local run queue
...
```

调度可以更多地在局部队列完成，减少所有 goroutine 都争抢一个全局队列。

**`GOMAXPROCS` 控制什么？**

它大致控制：

> 同时可以执行 Go 代码的 P 数量。

因此它和：

```text
goroutine 数量
```

完全不是一回事。 程序可以：

```text
100000 goroutines
GOMAXPROCS = 8
```

**一个 G 阻塞后怎么办？**

要区分阻塞类型。 例如：

* channel 等待；
* mutex 等待；
* network poll；
* syscall；
* CPU-bound execution。

Runtime 会根据具体情况调度其他 runnable G。 重点不是背某一个内部函数，而是理解：

> **一个 goroutine 等待，并不意味着整个 OS thread 上所有 Go 工作都必须跟着停止。**

### 2.3 [P0] Channel 是什么？

Channel 是 goroutine 之间传递数据和同步事件的一种语言级机制。 例如：

```go
ch := make(chan int)

go func() {
    ch <- 42
}()

value := <-ch
```

可以理解为：

```text
producer
   ↓
 channel
   ↓
consumer
```

但 channel 不只是“一个并发队列”。 一次 channel send / receive 还可以建立同步关系。

**Channel 常见用途**

**传递任务**

```go
jobs <- job
```

**返回结果**

```go
result := <-results
```

**通知完成**

```go
close(done)
```

**控制并发**

例如容量为 `N` 的 channel：

```go
sem := make(chan struct{}, N)
```

可以用作简单 semaphore。

**最重要的一句话**

Go 有一句经典设计思想：

> Do not communicate by sharing memory; share memory by communicating.

但这不是：

> “任何共享状态都必须用 channel。”

实际工程里 `Mutex`、atomic 和 channel 都有适用场景。

### 2.4 [P0] Buffered Channel 和 Unbuffered Channel 有什么区别？

**Unbuffered**

```go
ch := make(chan T)
```

发送：

```go
ch <- value
```

通常需要有对应 receiver 才能完成。 可以把它理解成一次 rendezvous：

```text
Sender ─────┐
            ├→ handoff
Receiver ───┘
```

它天然形成较强同步。

**Buffered**

```go
ch := make(chan T, 100)
```

只要 buffer 没满，sender 可以先写入：

```text
Sender
  ↓
[ buffer ]
       ↓
    Receiver
```

发送和接收在一定范围内解耦。

**Buffer 越大越好吗？**

不是。 大 buffer 可以吸收短期 burst：

```text
producer burst
      ↓
   buffer
      ↓
consumer
```

但如果长期：

```text
produce rate > consume rate
```

buffer 只是延迟问题暴露。 最终仍然会：

```text
buffer full
→ producer block
```

或者如果设计成无限队列：

```text
memory growth
→ OOM
```

所以 queue buffer 不能代替 capacity planning 和 backpressure。

### 2.5 [P0] Mutex 和 Channel 怎么选？

没有“Go 推荐永远用 Channel”的规则。 可以先这样判断：

**Mutex**

更适合：

> 多个 goroutine 访问同一份共享内存状态。

例如：

```go
type Counter struct {
    mu sync.Mutex
    n  int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.n++
}
```

**Channel**

更适合：

> ownership transfer、任务队列、pipeline、事件通知。

例如：

```text
producer
→ jobs channel
→ worker
```

**一个实用判断**

如果问题是：

```text
“谁可以访问这份共享对象？”
```

优先考虑 Mutex / ownership。 如果问题是：

```text
“一个任务如何从 A 流向 B？”
```

Channel 更自然。

**不要为了 Channel 而 Channel**

下面这种结构：

```text
读字段
→ 发 channel
→ 单独 goroutine 改字段
→ 再 channel 返回
```

如果只是保护一个小对象，可能比 mutex 更复杂。

### 2.6 [P0] `context.Context` 是干什么的？

`context.Context` 主要用于在调用链中传播：

* cancellation；
* deadline；
* request-scoped metadata。

典型调用链：

```text
HTTP Request
    ↓
Handler(ctx)
    ↓
Service(ctx)
    ↓
Repository(ctx)
    ↓
Database
```

如果客户端已经断开，或者 request deadline 到了：

```text
ctx.Done()
```

应该逐层让下游停止无意义工作。

**常见构造**

```go
ctx := context.Background()
```

根 context。

```go
ctx, cancel := context.WithCancel(parent)
defer cancel()
```

显式取消。

```go
ctx, cancel := context.WithTimeout(parent, time.Second)
defer cancel()
```

timeout。

```go
ctx, cancel := context.WithDeadline(parent, deadline)
defer cancel()
```

绝对 deadline。

**Context 不适合干什么？**

不要把 context 当：

```text
万能参数包
全局变量
Service container
```

只因为：

```go
ctx = context.WithValue(ctx, ...)
```

能存东西，就把数据库连接、配置对象、巨大业务实体全部塞进去。

### 2.7 [P0] `defer` 是什么？有什么常见坑？

`defer` 注册一个函数，在当前函数返回前执行。 典型用途：

```go
mu.Lock()
defer mu.Unlock()
```

```go
file, err := os.Open(path)
if err != nil {
    return err
}
defer file.Close()
```

```go
ctx, cancel := context.WithTimeout(parent, time.Second)
defer cancel()
```

**多个 defer 什么顺序？**

后注册先执行：

```go
defer A()
defer B()
defer C()
```

返回时：

```text
C
B
A
```

即 LIFO。

**defer 参数什么时候求值？**

例如：

```go
x := 1
defer fmt.Println(x)
x = 2
```

defer 注册时，函数参数已经求值，所以通常打印：

```text
1
```

**高频坑：循环中 defer**

```go
for _, path := range paths {
    f, _ := os.Open(path)
    defer f.Close()
}
```

所有 close 会等外层函数返回才执行。 如果文件很多：

```text
file descriptors
```

可能持续占用。 可改成：

```go
for _, path := range paths {
    func() {
        f, _ := os.Open(path)
        defer f.Close()
        ...
    }()
}
```

让 defer 生命周期缩小。

### 2.8 [P0] Go Interface 是什么？

Interface 描述一组方法。 例如：

```go
type Store interface {
    Get(ctx context.Context, id string) (*Item, error)
}
```

一个类型只要实现这些方法，就满足接口，不需要显式声明：

```text
implements Store
```

这是 Go 常见的结构化接口设计。

**为什么 Interface 有用？**

让上层依赖能力：

```text
Service
  ↓
Store interface
```

而不是依赖：

```text
MySQLStore concrete implementation
```

因此可以替换：

```text
MySQLStore
InMemoryStore
MockStore
```

**接口应该放哪里？**

一个很实用的 Go 设计习惯：

> 接口更适合由使用者定义，而不是为了“所有实现都可能需要”提前抽一个巨大接口。

如果 Service 只需要：

```go
Get()
Save()
```

就没必要依赖一个包含 25 个方法的：

```go
MegaRepository
```

### 2.9 [P1] 为什么 Interface 会出现“nil 不等于 nil”？

这是经典 Go 坑。 例如：

```go
type MyError struct{}

func (*MyError) Error() string {
    return "error"
}

func getErr() error {
    var e *MyError = nil
    return e
}
```

调用：

```go
err := getErr()
fmt.Println(err == nil)
```

可能得到：

```text
false
```

**为什么？**

可以把 interface 粗略理解成：

```text
(dynamic type, dynamic value)
```

真正的 nil interface：

```text
(nil, nil)
```

而这里是：

```text
(*MyError, nil)
```

dynamic type 不为空，所以整个 interface 不等于 nil。

**高频场景**

不要返回一个 typed nil pointer 作为 interface。 这在：

* `error`；
* repository interface；
* client interface；

中都可能制造隐蔽 bug。

### 2.10 [P0] Array 和 Slice 有什么区别？

Array 长度是类型的一部分：

```go
[3]int
[4]int
```

是不同类型。 Slice 是一个描述连续数组区域的结构。 概念上可以理解为：

```text
pointer
length
capacity
```

例如：

```go
a := []int{1, 2, 3, 4}
b := a[1:3]
```

`b` 通常仍引用 `a` 的底层数组：

```text
a: [1][2][3][4]
       ↑────↑
          b
```

所以：

```go
b[0] = 100
```

可能同时改变 `a[1]`。

**这就是为什么：**

```text
slice copy
```

不等于：

```text
deep copy
```

### 2.11 [P1] `append` 为什么可能产生很难发现的 Slice Bug？

考虑：

```go
a := make([]int, 2, 10)
a[0] = 1
a[1] = 2

b := a
b = append(b, 3)
```

由于 capacity 足够：

```text
a
b
```

可能仍共享底层数组。 但如果容量不足：

```go
append
```

会分配新的 backing array。 于是代码行为取决于：

```text
capacity
```

这很容易让 aliasing 难以理解。

**一个常见坑**

保存一个大 buffer 的小切片：

```go
big := make([]byte, 100<<20)

small := big[:10]
```

如果 `small` 长期存活，它仍可能引用整个大 backing array，使 100 MB 内存无法回收。 如果只需要 10 bytes，可以显式复制。

### 2.12 [P0] Go Map 是否并发安全？

普通 map：

```go
map[K]V
```

不支持无同步的并发读写。 多个 goroutine 同时操作时，必须建立同步。 例如：

```go
type Store struct {
    mu sync.RWMutex
    m  map[string]string
}
```

读取：

```go
s.mu.RLock()
v := s.m[key]
s.mu.RUnlock()
```

写：

```go
s.mu.Lock()
s.m[key] = value
s.mu.Unlock()
```

**并发读呢？**

如果完全没有写，并发只读通常没问题。 危险的是：

```text
read + write
write + write
```

**`sync.Map` 是不是更快？**

不是默认更快。 `sync.Map` 针对某些读多写少、key 生命周期等访问模式做了优化。 普通业务结构默认：

```text
map + mutex
```

通常更容易理解和维护。

### 2.13 [P1] Goroutine Leak 是什么？

Goroutine leak 指 goroutine 已经没有业务价值，却永久或长期无法退出。 例如：

```go
func worker(ch <-chan int) {
    for {
        value := <-ch
        process(value)
    }
}
```

如果：

* 再也没有 sender；
* channel 永远不 close；

这个 worker 可能永久阻塞。

**一个典型泄漏**

```go
func request() string {
    ch := make(chan string)

    go func() {
        result := slowCall()
        ch <- result
    }()

    select {
    case result := <-ch:
        return result
    case <-time.After(time.Second):
        return "timeout"
    }
}
```

如果 caller timeout 返回，而：

```text
slowCall()
```

稍后完成：

```go
ch <- result
```

因为没有 receiver，goroutine 可能永久阻塞。

**怎么解决？**

根据场景：

* buffered result channel；
* context cancellation；
* cancellable downstream call；
* worker lifecycle management。

核心不是某个固定写法，而是：

> **每个 goroutine 都应该能够回答：它在什么条件下退出？**

### 2.14 [P1] Channel 应该由谁 Close？

常见原则：

> **由 sender / producer 一侧关闭 channel，而不是 receiver。**

因为关闭的语义是：

```text
以后不会再有任何值发送
```

通常只有发送方知道这一事实。

**Receiver 如何判断 Channel 关闭？**

```go
value, ok := <-ch

if !ok {
    // closed
}
```

或者：

```go
for value := range ch {
    ...
}
```

channel close 后且 buffer 消耗完：

```text
range
```

自动结束。

**Close 一个已关闭 Channel 会怎样？**

panic。

**向已关闭 Channel 发送呢？**

panic。

**从已关闭 Channel 读取呢？**

可以继续读取。 buffer 清空后返回：

```text
zero value
ok = false
```

**为什么 Receiver 不应该随便 Close？**

因为可能还有别的 sender：

```text
Producer A ─┐
            ├→ channel
Producer B ─┘
```

Receiver 如果擅自 close：

```text
Producer B send
→ panic
```

### 2.15 [P1] `select` 是什么？

`select` 用于等待多个 channel operation。 例如：

```go
select {
case result := <-resultCh:
    return result

case <-ctx.Done():
    return ctx.Err()
}
```

表达：

```text
结果先回来
OR
取消先发生
```

**default**

```go
select {
case value := <-ch:
    ...
default:
    ...
}
```

会变成 non-blocking attempt。 如果滥用：

```go
for {
    select {
    case value := <-ch:
        ...
    default:
    }
}
```

可能造成 busy loop：

```text
CPU 100%
```

**多个 case 同时 ready 怎么办？**

Runtime 会在 ready cases 中选择执行，而不是永远按照源码从上到下挑第一个。 因此不要依赖：

```text
case textual order
```

建立业务优先级。

### 2.16 [P1] Cancellation 如何跨 Goroutine 传播？

典型结构：

```go
func handle(ctx context.Context) error {
    ctx, cancel := context.WithCancel(ctx)
    defer cancel()

    go workerA(ctx)
    go workerB(ctx)

    ...
}
```

worker：

```go
func worker(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            return

        case job := <-jobs:
            process(job)
        }
    }
}
```

这样：

```text
Parent cancel
     ↓
ctx.Done()
     ↓
Worker A stop
Worker B stop
```

**但 Context 不能魔法取消所有东西**

例如：

```go
result := thirdPartySDK.Call()
```

如果 SDK 根本不支持 context/cancellation：

```text
ctx canceled
```

并不会自动中断底层阻塞调用。 所以调用链每一层都必须真正支持：

```text
cancellation propagation
```

### 2.17 [P0] Timeout 和 Deadline 有什么区别？

Timeout 是相对时间：

```text
从现在开始最多 3 秒
```

Deadline 是绝对时间：

```text
必须在 15:03:27 前完成
```

例如外层请求已经消耗 800 ms：

```text
总 deadline = 1 秒
```

下游不应该重新创建：

```text
timeout = 1 秒
```

否则总调用可能变成：

```text
1.8 秒
```

更合理的是传播剩余 deadline。

**一个常见原则**

```text
child deadline
≤
parent deadline
```

子调用不应该活得比整个父请求还久，除非它本身就是显式设计的后台任务。

### 2.18 [P1] Mutex、RWMutex、Atomic 怎么选？

**Mutex**

适合保护：

```text
多个字段组成的一致性 invariant
```

例如：

```go
type Account struct {
    mu      sync.Mutex
    balance int64
    version uint64
}
```

更新 balance + version：

```text
应该在同一个 critical section
```

**RWMutex**

允许：

```text
multiple readers
OR
one writer
```

适合：

```text
读很多
写较少
critical section 足够长
```

但不是“读多就必然比 Mutex 快”。 RWMutex 本身有更复杂的协调成本。

**Atomic**

适合简单独立状态：

```text
counter
flag
pointer swap
```

例如：

```go
atomic.AddInt64(&count, 1)
```

但如果 invariant 是：

```text
a + b 必须始终一致
```

分别 atomic 修改 `a`、`b` 不自动让整个 invariant 原子。

**一句话**

```text
Atomic
→ 单个简单状态

Mutex
→ 多字段 invariant

Channel
→ task / ownership / event flow
```

### 2.19 [P1] 什么是 Race Condition？Data Race 又是什么？

两个概念不要完全混用。

**Data Race**

多个并发执行单元访问同一内存位置，并且至少一个是写，而没有正确同步。 例如：

```go
var count int

go func() {
    count++
}()

go func() {
    count++
}()
```

**Race Condition**

范围更广：

> 程序结果依赖不可控的执行顺序。

即使没有严格意义上的 data race，也可能有业务 race。 例如：

```text
Request A:
查询库存 = 1

Request B:
查询库存 = 1

A:
扣库存

B:
也扣库存
```

所有数据库操作本身都线程安全，但业务仍有：

```text
check-then-act race
```

**Go 怎么查 Data Race？**

开发阶段常用：

```bash
go test -race ./...
```

它不能证明：

```text
程序没有任何并发逻辑 bug
```

但对共享内存 data race 非常有价值。

### 2.20 [P1] Go GC 大致怎么工作？

面试通常不需要背 Runtime 源码细节，但需要理解：

> Go 使用自动垃圾回收，应用不需要手动 `free` 普通 heap object。

GC 的核心问题是：

```text
哪些对象仍然 reachable？
哪些对象已经不可达？
```

不可达对象最终可以被回收。

**为什么 GC 会影响服务性能？**

如果程序持续高速分配：

```text
request
→ allocate
→ allocate
→ allocate
```

GC 需要不断扫描和回收。 可能造成：

* CPU 消耗增加；
* latency 增加；
* heap 增长；
* GC cycle 更频繁。

**Go GC 的目标不是“零暂停”**

现代 Go GC 强调并发工作和较短 stop-the-world 阶段，但：

```text
GC ≠ completely free
```

仍然需要考虑：

```text
allocation rate
live heap
pointer density
```

**面试最实用的思路**

看到 GC 问题，不要第一反应：

> 调参数。

先看：

```text
为什么分配这么多？
```

例如：

* 每个 request 创建大量临时对象；
* 大量 `[]byte → string → []byte` 转换；
* 不必要 JSON 中间结构；
* buffer 没复用；
* retained object 生命周期过长。

### 2.21 [P2] 10 万 Goroutine 一定没问题吗？

不一定。 “Go 可以创建很多 goroutine”只是说明：

```text
goroutine 比 OS thread 轻
```

不是说明：

```text
数量没有成本
```

假设 10 万 goroutine 每个同时：

* 有 stack；
* 持有 timer；
* 持有 request object；
* 等待下游 HTTP；
* 占一个 DB connection；
* 等 MQ result。

真正瓶颈可能不是 scheduler，而是：

```text
DB connection pool
remote QPS
memory
file descriptor
network socket
queue depth
```

**Little's Law 的直觉**

如果：

```text
arrival rate = λ
average latency = W
```

系统平均并发量：

```text
L ≈ λW
```

例如：

```text
5000 requests/s
×
2 s latency
≈
10000 concurrent requests
```

延迟上升会直接推高 in-flight 数量。 如果完全不限制：

```text
downstream slow
→ request pile up
→ goroutine pile up
→ memory pile up
→ system collapse
```

这就是为什么“goroutine 很轻”不能替代 backpressure。

### 2.22 [P2] Worker Pool 为什么存在？

最简单的并发实现：

```go
for _, job := range jobs {
    go process(job)
}
```

如果 jobs 有 100 万个：

```text
100 万 goroutines
```

可能同时冲向：

* DB；
* RPC；
* disk；
* external API。

Worker Pool 改成：

```text
jobs
  ↓
bounded queue
  ↓
N workers
  ↓
downstream
```

例如：

```go
jobs := make(chan Job, 100)

for i := 0; i < 10; i++ {
    go worker(jobs)
}
```

**Worker Pool 控制什么？**

主要控制：

```text
active concurrency
```

而不是单纯减少 goroutine 数量。

**Worker 数量怎么定？**

没有固定：

```text
CPU 核数 × 2
```

这种万能公式。 如果任务是：

**CPU bound**

并发通常与 CPU parallelism 关系更大。

**IO bound**

可以高于 CPU 数量，但最终应该考虑：

```text
DB pool
remote capacity
rate limits
memory
latency
```

### 2.23 [P2] 什么是 Backpressure？

Backpressure 的核心是：

> 下游处理能力不足时，上游必须感知，而不能无限继续生产。

假设：

```text
Producer = 10k/s
Consumer = 2k/s
```

如果系统只做：

```text
enqueue forever
```

那就是：

```text
queue:
0
→ 8k
→ 16k
→ 24k
→ ...
```

最终只是把：

```text
throughput problem
```

变成：

```text
memory / latency problem
```

**常见 backpressure 方式**

**Block producer**

bounded channel 满后：

```text
send blocks
```

**Reject**

直接返回：

```text
429 / overload
```

**Drop**

例如某些 metrics / telemetry：

```text
允许丢弃低价值数据
```

**Shed load**

优先拒绝低优先级任务。

**Slow producer**

通过：

* rate limit；
* feedback；
* credits；

降低输入速度。

**关键点**

Backpressure 不是：

> “队列弄大一点。”

而是：

> **当 capacity 不够时，系统明确决定谁等待、谁失败、谁被丢弃。**

### 2.24 [P2] `sync.Pool` 是什么？什么时候不要用？

`sync.Pool` 用来复用临时对象，减少 allocation pressure。 例如：

```go
var pool = sync.Pool{
    New: func() any {
        return new(bytes.Buffer)
    },
}
```

使用：

```go
buf := pool.Get().(*bytes.Buffer)
buf.Reset()

defer pool.Put(buf)
```

**适合**

大量：

```text
短生命周期
可复用
创建频繁
```

的临时对象。 例如：

* buffer；
* encoder temporary state。

**不适合**

不要把它当：

```text
对象缓存数据库
持久 object pool
资源生命周期管理器
```

Pool 中对象可能被 Runtime 清理，不能假设：

```text
Put 之后未来一定 Get 得回来
```

也不要为了减少少量 allocation 就把代码复杂度显著提高。

**什么时候优化？**

先 profile。 如果 pprof 显示：

```text
某对象分配占据明显热点
```

再考虑：

* 减少分配；
* object reuse；
* `sync.Pool`。

不要先写 Pool，再去找性能问题。

### 2.25 [P2] 怎么排查 Goroutine Leak？

**第一步：确认现象**

例如：

```text
goroutine count
100
→ 1000
→ 10000
→ 一直不下降
```

并伴随：

```text
memory growth
open connection growth
latency increase
```

**第二步：看 Goroutine Profile**

常用：

```text
pprof goroutine
```

寻找大量 goroutine 堆积在相同 stack。 例如：

```text
chan receive
```

或：

```text
network read
```

或：

```text
mutex.Lock
```

**第三步：问生命周期**

对每一类 goroutine 问：

```text
谁创建它？
谁拥有它？
什么条件退出？
谁发 cancellation？
下游是否支持 cancellation？
shutdown 时是否 join？
```

**常见原因**

```text
channel 永远没人 close
send 没 receiver
receive 没 sender
forgot cancel()
downstream call 永久阻塞
ticker 没 stop
worker 没 shutdown path
```

**本质**

Goroutine leak 本质通常不是：

> scheduler 出问题。

而是：

> **生命周期 ownership 没设计清楚。**

### 2.26 [P2] 怎么排查 Lock Contention？

现象可能是：

```text
CPU 没满
QPS 上不去
latency 很高
goroutine 很多
```

原因可能是：

```text
所有 goroutine
      ↓
一个大 mutex
      ↓
serial execution
```

**常见原因**

**Critical Section 太大**

```go
mu.Lock()

callRemoteAPI()
doHeavyWork()
updateState()

mu.Unlock()
```

锁内部包含慢 IO。

**一个全局锁保护太多对象**

```text
all users
all requests
all cache entries
```

都争一个 mutex。

**锁顺序不一致**

可能进一步产生 deadlock。

**优化思路**

先确认 invariant。 不能为了“减少锁”破坏正确性。 再考虑：

```text
缩小 critical section
shard lock
per-key lock
copy then compute
immutable snapshot
atomic
ownership model
```

### 2.27 [P2] Deadlock 是什么？

Deadlock 指一组执行单元互相等待，谁都无法继续。 典型：

```text
G1:
lock A
wait B

G2:
lock B
wait A
```

形成：

```text
A → B → A
```

**Channel 也会 Deadlock**

例如：

```go
ch := make(chan int)

ch <- 1
```

当前 goroutine 发送到 unbuffered channel，但没有 receiver：

```text
永远等待
```

**常见防御**

* 固定 lock ordering；
* 避免持锁做阻塞 IO；
* 缩小 critical section；
* 简化 ownership；
* 让 cancellation / timeout 进入等待设计；
* 测试异常路径，而不是只测 happy path。

### 2.28 [P1] `WaitGroup` 是做什么的？

`sync.WaitGroup` 用于等待一组 goroutine 完成。 例如：

```go
var wg sync.WaitGroup

for i := 0; i < 10; i++ {
    wg.Add(1)

    go func() {
        defer wg.Done()
        work()
    }()
}

wg.Wait()
```

表示：

```text
启动 N 个任务
→ 等 N 个任务全部结束
```

**WaitGroup 不负责什么？**

它不负责：

* cancellation；
* error propagation；
* concurrency limit；
* timeout；
* result collection。

所以复杂任务常需要：

```text
context
+
WaitGroup / errgroup
+
semaphore / worker pool
```

一起完成生命周期管理。

### 2.29 [P1] `errgroup` 相比 WaitGroup 有什么意义？

常见并发场景：

```text
启动 A
启动 B
启动 C

任何一个失败
→ 取消其他任务
→ 返回错误
```

单纯 WaitGroup 需要自己处理：

* error channel；
* cancellation；
* first error。

`errgroup` 提供更适合这种任务组合的抽象。 概念上：

```text
fork concurrent work
       ↓
one fails
       ↓
cancel siblings
       ↓
join
       ↓
return error
```

**适合什么？**

例如同时查询三个后端：

```text
profile service
payment service
inventory service
```

要求：

```text
全部成功
```

任一失败即可取消剩余工作。

### 2.30 [P1] 为什么“启动后台 Goroutine”是一个生命周期设计问题？

很多代码看起来无害：

```go
go poll()
```

但立即带来几个问题：

```text
谁负责停止它？
进程 shutdown 时怎么办？
如果 poll panic 怎么办？
如果 poll 永远卡住怎么办？
重复启动怎么办？
多个实例会不会同时 poll 同一任务？
```

因此：

```text
go func()
```

不是单纯语法糖。 它意味着：

> 创建一个新的独立生命周期。

**生产代码应回答**

```text
owner
start condition
stop condition
cancellation
error handling
restart policy
duplication semantics
```

### 2.31 [P1] Context Value 什么时候适合用？

适合 request-scoped metadata，例如：

```text
trace_id
request_id
authenticated principal
```

但需要克制。

**不适合**

```text
database client
business config
repository
large payload
optional function arguments
```

因为 Context API 会隐藏依赖。 例如：

```go
func Process(ctx context.Context)
```

表面看不到它其实需要：

```text
User
Tenant
Config
Database
FeatureFlags
```

维护成本会变高。

**原则**

如果某个值是：

> 函数真正的业务输入。

应该优先显式参数。 Context 主要承担：

```text
request lifecycle
+
cross-cutting metadata
```

### 2.32 [P1] 为什么不能随便用 `context.Background()`？

假设：

```text
HTTP request
  ↓
Service
  ↓
Database
```

Service 突然：

```go
ctx := context.Background()
db.QueryContext(ctx, ...)
```

那么原请求：

```text
timeout
client disconnected
server shutting down
```

这些 cancellation 都被切断。 形成：

```text
request already gone
↓
database query still running
```

**什么时候 Background 合理？**

创建真正独立生命周期的 root task 时。 例如：

```text
application startup
```

然后由服务自己管理：

```text
cancel
shutdown
```

**如果要在请求结束后继续做后台任务？**

不要只是：

```go
go doWork(context.Background())
```

然后忘记它。 应该明确设计：

```text
job queue
worker
ownership
retry
shutdown
```

### 2.33 [P1] Go Error 应该怎么处理？

Go 使用显式 error value：

```go
value, err := f()
if err != nil {
    ...
}
```

工程上至少区分：

```text
产生错误
包装错误
分类错误
记录错误
返回错误
```

**不要每一层都 Log**

如果：

```text
repository logs
service logs
handler logs
```

同一个 error 可能出现三次：

```text
ERROR
ERROR
ERROR
```

通常更合理的是：

> 底层补充 context 并返回；由明确的边界统一记录。

**Wrapping**

例如：

```go
return fmt.Errorf("load payment %s: %w", id, err)
```

保留原 error chain。 然后：

```go
errors.Is(err, ErrNotFound)
```

仍可进行分类。

**Error message 应该包含什么？**

提供：

```text
operation
object identity
useful context
```

但不要泄漏：

```text
secret
private key
credential
full payment signature
```

### 2.34 [P1] Panic 和 Error 有什么区别？

一般业务失败应该返回：

```go
error
```

例如：

```text
DB unavailable
invalid request
not found
timeout
```

Panic 更适合：

```text
程序进入不应该出现的内部状态
```

或者某些初始化阶段的不可恢复错误。

**HTTP Server 为什么常有 Recovery Middleware？**

如果某个 handler panic：

```text
panic
```

不能让整个服务进程跟着退出。 Recovery middleware 可以：

```text
recover
→ log stack
→ return 500
```

但：

```text
recover ≠ 修复业务状态
```

如果 panic 前已经产生外部 side effect，仍然需要：

* idempotency；
* reconciliation；
* transaction；

处理正确性。

### 2.35 [P1] 为什么 Go 中要关注 Zero Value？

Go 很多类型设计成 zero value 就能使用。 例如：

```go
var mu sync.Mutex
```

不需要：

```go
NewMutex()
```

这让结构体更容易组合。 但自定义类型也应该想清楚：

```text
zero value
```

是：

```text
valid empty state
```

还是：

```text
invalid state
```

例如金额：

```go
AmountMinor int64
```

`0` 到底表示：

```text
免费
未填写
非法金额
```

如果语义不明确，就需要：

* pointer；
* optional wrapper；
* explicit validation。

这个问题看似语言基础，实际上会直接影响 API schema 和领域模型。

### 2.36 [P1] Value Semantics 和 Pointer Semantics 怎么选？

**Value**

传递一个副本：

```go
func F(v T)
```

适合：

* 小 immutable value；
* value object；
* 不需要共享 mutation。

**Pointer**

```go
func F(v *T)
```

适合：

* 需要修改；
* 对象较大；
* identity / shared lifecycle 明确；
* nil 有业务意义。

**不要只根据结构体大小机械决定**

更重要的是语义。 例如：

```text
Money
Coordinate
Hash
```

通常更像 value。 而：

```text
Database connection
Service
Mutable aggregate
```

更像 identity-bearing object。

### 2.37 [P2] Go 服务为什么容易出现 Unbounded Concurrency？

因为写：

```go
go handle(task)
```

太容易。 例如：

```go
for task := range tasks {
    go handle(task)
}
```

如果 upstream 突然：

```text
100k events
```

就会：

```text
100k goroutines
```

接着全部打：

```text
MySQL
Redis
RPC
```

即使 Go scheduler 扛得住，下游也可能扛不住。

**所以 Production Concurrency 要区分**

```text
goroutine capacity
application capacity
downstream capacity
```

真正限制往往来自：

```text
DB pool = 100
remote QPS = 500
API limit = 50 concurrent
```

因此并发上限应该从依赖 capacity 推导，而不是从：

> “Go 可以创建很多 goroutine。”

推导。

### 2.38 [P2] Semaphore 和 Worker Pool 有什么区别？

两者都可以限制并发。

**Semaphore**

任务本身仍可能由独立 goroutine 表示：

```text
task
task
task
task
  ↓
[ N permits ]
  ↓
active execution
```

适合：

> 限制某一段昂贵操作的 concurrent execution。

**Worker Pool**

任务首先进入 queue：

```text
queue
 ↓
N workers
```

不仅限制并发，还定义了：

* task buffering；
* worker ownership；
* shutdown；
* queue behavior。

**选择**

只需要控制：

```text
最多 20 个 concurrent RPC
```

semaphore 很自然。 如果需要：

```text
持续处理 job stream
```

worker pool 往往更自然。

### 2.39 [P2] 如何做 Graceful Shutdown？

一个正常服务收到：

```text
SIGTERM
```

不应该立即：

```text
os.Exit()
```

而应该按顺序收口。 典型：

```text
1. Stop accepting new traffic
2. Mark readiness = false
3. Cancel background workers
4. Stop consuming new jobs/messages
5. Wait for in-flight work
6. Flush critical state/logs
7. Close DB / Redis / MQ clients
8. Exit
```

**为什么顺序重要？**

如果：

```text
先关闭 DB
```

再等待 in-flight request：

```text
request
→ database
→ connection closed
→ failure
```

**还必须有 Shutdown Deadline**

不能无限等待：

```text
one stuck goroutine
→ service never exits
```

因此：

```text
graceful shutdown
```

本身也需要：

```text
bounded deadline
```

### 2.40 Go 并发里的四种“不要混”

面试里很容易把以下问题揉成一句：

> “加个锁就好了。”

实际上至少有四层。

**1. Data Race**

```text
两个 goroutine 无同步访问同一内存
```

工具：

```text
Mutex / Atomic / Channel
```

**2. Application Race**

```text
check
→ 时间窗口
→ act
```

即使单进程内存完全线程安全，也可能出错。 工具可能是：

```text
DB transaction
unique constraint
CAS
idempotency
```

**3. Distributed Race**

```text
Instance A
Instance B
```

本地 `sync.Mutex` 完全不起作用。 需要：

```text
DB lock
distributed coordination
unique constraint
version
fencing
```

**4. Side-effect Race**

两个 worker 同时调用：

```text
charge()
send_email()
create_vm()
```

即使 DB 最终只有一条记录，外部副作用可能已经发生两次。 需要进一步考虑：

```text
idempotency
economic identity
remote idempotency
reconciliation
```

因此：

```text
thread-safe
≠
business-safe
≠
distributed-safe
≠
side-effect-safe
```

这是后面分布式系统章节会反复出现的一条主线。

### 2.41 常见错误代码题

**Case 1：闭包捕获与并发任务**

现代 Go 已经改善了经典 `range` loop variable 问题，但面试更重要的是理解：

> goroutine 执行发生在未来，因此要确认闭包捕获的是你真正想要的值和对象。

例如业务对象本身如果后续继续 mutation：

```go
for _, task := range tasks {
    t := task

    go func() {
        process(t)
    }()
}
```

显式建立当前 iteration 的输入仍然让 ownership 更清晰。

**Case 2：忘记 `wg.Done`**

```go
wg.Add(1)

go func() {
    work()
}()
```

然后：

```go
wg.Wait()
```

永远等不到结束。 常见写法：

```go
go func() {
    defer wg.Done()
    work()
}()
```

**Case 3：在 Lock 内调用远程服务**

```go
mu.Lock()
defer mu.Unlock()

response := remote.Call()
```

如果 remote latency：

```text
10 ms
→ 5 s
```

所有等待这把锁的 goroutine 都跟着堵住。 应先判断：

> 是否真的必须把 remote call 包含在同一个 critical section 中？

很多时候可以：

```text
lock
→ read/capture local state
→ unlock
→ remote call
→ lock
→ validate version + commit
```

但这又引入 stale state，需要 CAS/version 等重新校验。 所以并发设计本质上总在：

```text
锁住更久
vs
重新验证
```

之间 trade-off。

**Case 4：每次请求启动永生后台任务**

```go
func Handler() {
    go pollForever()
}
```

10000 个请求：

```text
10000 pollers
```

如果实际需求是：

> 一个资源只需要一个 poller。

那就必须有：

```text
ownership
deduplication
worker management
```

### 2.42 高频追问：为什么 Go 推荐 CSP，不代表不要共享内存？

CSP 风格强调：

```text
communicating sequential processes
```

即通过消息传递组织独立执行单元。 这种模式非常适合：

```text
pipeline
worker
job queue
actor-like ownership
```

但现实后端存在大量共享对象：

```text
cache
connection pool
metrics
configuration snapshot
in-memory index
```

为它们全部创造专用 goroutine + channel，并不一定更简单。 所以面试中更成熟的回答是：

> Channel 适合表达数据流和 ownership transfer；Mutex 适合保护共享状态。两者都是工具，目标是建立清晰的 ownership 和 synchronization boundary，而不是追求某种语法上的“纯 Go”。

### 2.43 高频追问：CPU-bound 和 IO-bound Goroutine 有什么不同？

**CPU-bound**

例如：

```text
compression
hashing
image transform
large JSON computation
```

持续消耗 CPU。 并发再多：

```text
CPU cores 不会变多
```

过多 runnable goroutine 还会带来调度开销。

**IO-bound**

例如：

```text
DB
RPC
network
disk
```

大量时间处于等待。 因此可以存在：

```text
concurrency >> CPU core count
```

但仍受到：

```text
connection pool
remote server
memory
FD
```

限制。 所以：

```text
goroutine count
```

不能只根据：

```text
NumCPU
```

设置，也不能完全不限制。

### 2.44 高频追问：为什么 Connection Pool 和 Goroutine Pool 不是一回事？

假设：

```text
1000 goroutines
```

同时请求 MySQL，但 DB pool：

```text
MaxOpenConns = 50
```

最终：

```text
50 executing
950 waiting for connection
```

所以实际 DB concurrency 已经被 connection pool 限制。 但这并不意味着 950 个等待 goroutine 没成本。 它们仍：

* 占内存；
* 保留 request；
* 增加 latency；
* 可能继续持有上游资源。

因此好的系统会考虑：

```text
application concurrency
≈
downstream useful capacity
```

而不是完全依赖连接池在最后兜底。

### 2.45 高频追问：为什么 Context 取消不等于 Transaction Rollback？

假设：

```text
ctx canceled
```

只能表达：

> 调用者不再希望继续工作。

但远端系统可能已经：

```text
commit DB transaction
send payment
publish message
```

Context 不能穿越时间把已经发生的副作用撤销。 因此：

```text
cancellation
```

解决生命周期。

```text
transaction
```

解决本地原子性。

```text
idempotency / reconciliation / compensation
```

解决跨副作用正确性。 不要混在一起。

### 2.46 本章高频对比

| 概念 A             | 概念 B               | 关键区别                                       |
| ---------------- | ------------------ | ------------------------------------------ |
| Goroutine        | OS Thread          | Runtime 调度单元 vs 内核线程                       |
| Concurrency      | Parallelism        | 任务交错推进 vs 真正同时执行                           |
| G                | M / P              | goroutine vs OS thread / logical processor |
| Buffered Channel | Unbuffered Channel | 有中间容量 vs 同步 handoff                        |
| Channel          | Mutex              | 数据流/ownership vs 共享状态保护                    |
| Timeout          | Deadline           | 相对时长 vs 绝对终止时间                             |
| Mutex            | RWMutex            | 单一互斥 vs 多 reader / 单 writer                |
| Mutex            | Atomic             | 多字段 invariant vs 简单原子状态                    |
| Data Race        | Race Condition     | 内存并发冲突 vs 更广泛的时序依赖                         |
| WaitGroup        | Context            | 等待完成 vs 生命周期取消                             |
| WaitGroup        | errgroup           | 只等待 vs error + cancellation orchestration  |
| Semaphore        | Worker Pool        | 并发许可 vs queue + worker ownership           |
| Goroutine Limit  | Connection Pool    | 应用任务并发 vs 下游连接并发                           |
| Cancellation     | Rollback           | 停止继续工作 vs 撤销已提交事务                          |
| Panic            | Error              | 异常程序状态 vs 可预期失败                            |
| Thread-safe      | Business-safe      | 内存同步正确 ≠ 业务 invariant 正确                   |

### 2.47 面试前一分钟速记

```text
G = Goroutine
M = OS Thread
P = Runtime execution resource

GOMAXPROCS 控制的是可并行执行 Go code 的 P，
不是 goroutine 数量。

goroutine 很轻，
但不是免费资源。

Channel 更适合：
task / pipeline / ownership / notification

Mutex 更适合：
shared mutable state

Atomic 更适合：
简单独立状态

Context 主要传播：
cancellation / deadline / request-scoped metadata

每个 goroutine 都必须回答：
谁创建？
谁拥有？
什么时候退出？
如何取消？

Buffered channel 只能吸收 burst，
不能解决长期 produce > consume。

大量 goroutine 的真正瓶颈经常不是 scheduler，
而是 DB pool / RPC / memory / FD / remote QPS。

Data-race free
不代表
business-race free。

local mutex
不解决
multi-instance race。

context canceled
不代表
remote side effect 被 rollback。

Production concurrency 必须 bounded。
```

### 2.48 StablePay 映射

这一章只建立几个弱映射，不重复项目实现。

```text
Context / deadline
→ HTTP / Kitex 请求生命周期

Background goroutine lifecycle
→ transaction polling / consumer shutdown

Mutex / concurrent state
→ nonce cache 等进程内控制状态

Bounded concurrency
→ RPC / DB / MQ 下游 capacity

Graceful shutdown
→ HTTP server / MQ consumer / background task 收口

Race vs business race
→ 单机线程安全并不能替代 payment idempotency

Cancellation ≠ rollback
→ 请求结束不代表远端 payment side effect 消失
```

如果面试官继续问：

> StablePay 当前 Payment polling 是如何启动的？
> Commerce Runtime 的并发 resume 如何防 stale write？
> RocketMQ consumer 如何关闭？
> 哪些 nonce 是进程内，哪些在 Redis？

这些属于项目事实，应回到 01，而不是在本章重复。

### 2.49 本章学习优先级

如果时间有限，按这个顺序。

### 第一轮：P0

必须马上掌握：

```text
Goroutine
GMP
Channel
Buffered / Unbuffered
Mutex vs Channel
Context
Timeout / Deadline
Slice
Map
Interface
defer
```

### 第二轮：P1

重点进入：

```text
goroutine leak
channel lifecycle
select
cancellation propagation
Mutex / RWMutex / Atomic
data race
GC
WaitGroup / errgroup
error handling
background lifecycle
```

### 第三轮：P2

针对 Go 后端 / Agent Infra 岗：

```text
bounded concurrency
worker pool
backpressure
sync.Pool
lock contention
deadlock
graceful shutdown
pprof
capacity reasoning
```

最终不要背成：

> “Go 的 goroutine 很轻，所以适合高并发。”

应该能完整说成：

> Go 用 Runtime 调度大量 goroutine，让 IO-heavy 服务很容易表达并发；但 goroutine 本身以及它持有的请求、timer、socket 和下游调用仍然消耗资源，因此生产系统仍需要 connection pool、worker/semaphore、deadline、cancellation 和 backpressure 来形成有界并发。Go 解决的是并发编程成本，不是系统容量上限。

## 3. HTTP、RPC 与 CloudWeGo

一个典型 Go 微服务请求可能经过：

```text
Client
  ↓
DNS
  ↓
TCP connection
  ↓
HTTP Gateway
  ↓
Middleware
  ↓
RPC Client
  ↓
Service
  ↓
Database / Redis / MQ / External API
```

因此，“会用 Hertz 和 Kitex”与“理解一次请求发生了什么”是两件事。 面试官可能从：

> Hertz 和 Kitex 分别是什么？

一路追到：

```text
HTTP keep-alive 怎么工作？
为什么要 connection pool？
RPC timeout 应该设在哪？
一次请求 retry 三层会发生什么？
为什么 timeout 不能直接 retry payment？
deadline 怎么跨服务传播？
IDL 为什么不能随便删字段？
服务 A 慢了为什么会拖垮服务 B？
Circuit Breaker 和 Rate Limit 有什么区别？
```

这一章的重点不是 CloudWeGo API，而是：

> **一个请求如何跨进程传输，以及如何在失败、延迟和过载条件下仍保持有界。**

### 3.1 [P0] TCP 和 HTTP 是什么关系？

**30 秒回答**

TCP 是传输层协议，提供可靠、有序的字节流。 HTTP 是应用层协议，定义：

```text
request
response
method
headers
body
status code
```

等语义。 传统 HTTP/1.1 和 HTTP/2 通常运行在 TCP 之上：

```text
HTTP
 ↓
TCP
 ↓
IP
```

因此：

```text
HTTP request
```

不是直接“发到另一台服务”。 底层还涉及：

```text
DNS
TCP connection
possibly TLS
bytes transmission
HTTP parsing
```

### 3.2 [P0] TCP 为什么需要三次握手？

简化理解：

```text
Client                      Server

SYN ---------------------->

    <------------------ SYN + ACK

ACK ---------------------->
```

三次握手的目标之一，是让双方确认：

```text
对方可以发送
对方可以接收
初始序列号已经同步
```

不能简单背成：

> 三次握手只是为了建立连接。

真正需要理解的是：

> TCP 是一个有状态的可靠字节流协议，双方必须建立连接状态。

**和 HTTP 有什么关系？**

如果每一个 HTTP request 都重新：

```text
TCP handshake
TLS handshake
request
close
```

成本很高。 因此现代客户端通常会复用连接：

```text
connection pool
+
keep-alive
```

### 3.3 [P0] TCP 是“可靠”的，为什么应用还需要 Retry？

TCP 的可靠保证主要是：

> 在一个已经建立的连接中，对字节流进行重传、排序和错误检测。

它不能告诉业务：

```text
对方到底有没有 commit 数据库？
支付有没有真正执行？
服务是不是收到请求后 crash？
```

例如：

```text
Client
  ↓
Server receives request
  ↓
Server commits DB
  ↓
Server sends response
  X
connection breaks
```

Client 看到的是：

```text
network error
```

但业务事实已经是：

```text
operation committed
```

所以：

```text
TCP reliability
≠
business operation exactly-once
```

这是后面 idempotency 和 unknown outcome 的基础。

### 3.4 [P0] HTTP Request 包含什么？

最基本包括：

```text
Method
Path
Headers
Body
```

例如：

```http
POST /payments
Content-Type: application/json
Idempotency-Key: abc

{
  "amount": 100
}
```

其中：

**Method**

表达请求动作语义。

**Path**

定位资源或操作。

**Header**

携带：

* content type；
* authentication；
* tracing；
* cache；
* idempotency metadata。

**Body**

携带请求内容。 在安全系统里还可能需要把：

```text
method
path
query
body hash
timestamp
nonce
```

组成 canonical request，再进行签名。

### 3.5 [P0] GET / POST / PUT / PATCH / DELETE 有什么区别？

不是简单：

```text
GET = 查
POST = 增
PUT = 改
DELETE = 删
```

更重要的是 HTTP 语义。

**GET**

读取资源。 通常应该：

```text
safe
```

即调用本身不应该产生业务副作用。

**POST**

提交一个动作或创建 subordinate resource。 通常：

```text
not inherently idempotent
```

例如：

```http
POST /payments
```

重复调用可能产生两次 payment。

**PUT**

通常表示：

> 用给定表示创建或完整替换指定资源。

由于资源 identity 通常由 URL 决定，所以更容易设计成 idempotent。

**PATCH**

部分更新。 是否幂等取决于 patch 语义。 例如：

```text
set balance = 100
```

可能幂等。 而：

```text
balance += 100
```

就不是。

**DELETE**

通常设计为 idempotent：

```text
删除一次
删除两次
```

最终资源都不存在。 但 HTTP method 本身不能自动保证后端实现正确。

### 3.6 [P0] Safe 和 Idempotent 有什么区别？

两个概念容易混。

**Safe**

请求预期不会改变服务器业务状态。 典型：

```text
GET
HEAD
```

**Idempotent**

同一个操作执行一次或多次，最终预期效果相同。 例如：

```text
DELETE /resource/123
```

第一次删除：

```text
exists → deleted
```

第二次：

```text
already absent
```

最终都：

```text
resource absent
```

所以：

```text
safe
→ 通常没有副作用

idempotent
→ 可以有副作用，但重复执行不继续改变最终效果
```

### 3.7 [P0] HTTP Status Code 应该怎么理解？

不需要把所有 code 背下来，但常见分类要熟悉。

```text
2xx
成功

4xx
客户端请求问题或当前请求不允许

5xx
服务端未能完成请求
```

常见：

```text
200 OK
201 Created
202 Accepted
204 No Content

400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
429 Too Many Requests

500 Internal Server Error
502 Bad Gateway
503 Service Unavailable
504 Gateway Timeout
```

**`401` 和 `403`**

常见理解：

```text
401
身份认证缺失或失败

403
身份已知，但没有权限
```

**`409 Conflict`**

适合表达：

```text
请求本身格式合法
但和当前资源状态冲突
```

例如：

```text
version conflict
duplicate business state
invalid transition
```

### 3.8 [P0] REST 是什么？

REST 是一种围绕资源、统一接口等原则组织网络 API 的架构风格。 面试中不需要把它神化。 实际工程常见：

```text
/resource/{id}
```

配合 HTTP method：

```text
GET
POST
PUT
PATCH
DELETE
```

表达操作。

**REST 不等于 HTTP**

HTTP 是协议。 REST 是一种 API 设计风格。 同一个 HTTP 服务也可以设计：

```text
POST /createPayment
POST /cancelPayment
```

这更偏 RPC-style HTTP。

**REST 也不是“越 RESTful 越好”**

对内部复杂操作：

```text
POST /payments/{id}:reconcile
```

有时比强行映射成 CRUD 更清楚。 目标是：

```text
stable contract
clear semantics
predictable behavior
```

而不是追求形式纯度。

### 3.9 [P0] HTTP/1.1 和 HTTP/2 有什么主要区别？

面试阶段掌握几个关键点即可。

**HTTP/1.1**

一个 TCP connection 上虽然可以 keep-alive，但请求并发能力受到协议模型限制。 实际客户端常通过：

```text
multiple TCP connections
```

提高并发。

**HTTP/2**

将通信拆成多个 stream，可以在同一 connection 上 multiplex：

```text
TCP Connection

Stream 1
Stream 3
Stream 5
Stream 7
```

并支持：

* binary framing；
* header compression；
* stream multiplexing。

**解决了所有 Head-of-Line Blocking 吗？**

没有。 HTTP/2 可以减少 HTTP 层面的阻塞问题，但所有 stream 仍共享同一个 TCP 字节流。 如果 TCP 层丢包：

```text
packet loss
```

仍可能影响同连接中的多个 stream。 这也是 QUIC / HTTP/3 设计背景之一。

### 3.10 [P1] HTTP Keep-Alive 是什么？

如果每次 request：

```text
connect
request
response
close
```

高 QPS 下会不断：

* TCP handshake；
* TLS handshake；
* 分配 socket；
* 建连接状态。

Keep-alive 允许：

```text
request A
response A
request B
response B
request C
response C
```

复用同一 TCP connection。

**好处**

减少：

```text
connection setup latency
CPU
kernel resource
TLS cost
```

**但连接不能无限保存**

还需要：

```text
idle timeout
max connections
connection lifetime
```

否则 connection pool 本身会成为资源问题。

### 3.11 [P0] RPC 是什么？

RPC：

> Remote Procedure Call。

目的是让调用远程服务看起来类似：

```go
result, err := client.GetPayment(ctx, request)
```

而底层实际是：

```text
serialize request
→ network
→ remote server
→ deserialize
→ execute
→ serialize response
→ network
→ deserialize
```

所以：

```text
client.GetPayment()
```

表面像本地函数调用，但本质完全不同。

### 3.12 [P0] RPC 和本地函数调用最大的区别是什么？

本地函数调用失败通常比较明确：

```text
return value
error
panic
```

RPC 中多了一整个网络和远程进程。 可能出现：

```text
request 没发送出去
request 发到一半
server 收到了
server 执行成功
response 丢失
server crash
network timeout
client timeout
```

所以：

> **Remote call failure is ambiguous.**

这是 RPC 设计的核心认知之一。

**一个重要原则**

```text
local call abstraction
```

可以隐藏网络编码细节。 但不能假装：

```text
remote call == local call
```

因为：

```text
latency
partial failure
retry
timeout
unknown outcome
```

仍然存在。

### 3.13 [P0] 为什么内部服务喜欢 RPC？

常见原因：

**强类型 Contract**

例如：

```text
GetPaymentRequest
GetPaymentResponse
```

而不是到处：

```go
map[string]interface{}
```

**Code Generation**

从 IDL 生成：

```text
client
server
types
```

减少手写协议胶水。

**较清晰的服务边界**

调用形式：

```text
PaymentService.InitiatePayment
```

比拼 URL/string contract 更稳定。

**性能与框架能力**

很多 RPC framework 会整合：

* serialization；
* service discovery；
* timeout；
* retry；
* tracing；
* middleware。

但 RPC 并不天然比 HTTP API “高级”。 它只是更适合某些内部服务场景。

### 3.14 [P0] IDL 是什么？

IDL：

> Interface Definition Language。

用于定义跨服务 contract。 例如概念上：

```text
service PaymentService {
    InitiatePayment(Request) returns (Response)
}
```

Request：

```text
agent_did
skill_did
amount_minor
currency
idempotency_key
```

然后 codegen 生成：

```text
Go client
Go server interface
request/response types
```

**IDL 解决什么？**

如果没有 IDL，两个服务可能分别写：

```go
type Payment struct {
    Amount int
}
```

和：

```go
type Payment struct {
    Amount float64
}
```

编译时不会知道对方已经不兼容。 IDL 把跨进程 contract 放到显式 schema。

### 3.15 [P1] IDL 为什么比共享 Go Struct 更适合跨服务？

如果服务 A 和服务 B：

```text
import same Go package
```

直接共享内部 domain struct，短期很方便。 但会带来：

```text
language coupling
release coupling
domain model coupling
uncontrolled field exposure
```

例如内部结构：

```go
type Payment struct {
    InternalSecret string
    DBVersion      uint64
    ...
}
```

并不代表这些字段都应该成为网络 contract。 IDL 迫使开发者明确：

```text
哪些字段属于 API
哪些只是内部实现
```

因此：

```text
Domain Model
≠
Wire Contract
```

### 3.16 [P0] 什么是 Serialization？

网络只能传输字节。 所以：

```go
Request struct
```

必须转换成：

```text
bytes
```

接收端再转换回来。 这个过程是：

```text
serialization
deserialization
```

常见格式：

```text
JSON
Protobuf
Thrift
MessagePack
```

不同方案会在：

```text
readability
size
speed
schema
compatibility
```

之间做 trade-off。

### 3.17 [P1] 为什么内部 RPC 常用二进制 Serialization？

与 JSON 相比，schema-based binary format 常见优势：

```text
payload smaller
parse faster
stronger typing
generated code
explicit field identity
```

但 JSON 的优势也很明显：

```text
human-readable
easy debugging
browser/tool support
low integration barrier
```

所以典型架构可能是：

```text
External API
→ HTTP + JSON

Internal services
→ RPC + schema-based binary protocol
```

但这只是常见选择，不是绝对规则。

### 3.18 [P0] Hertz 和 Kitex 分别是什么？

在当前 StablePay 架构里可以先这样理解：

```text
Hertz
→ HTTP Server / Gateway 层

Kitex
→ 内部 RPC Client / Server 层
```

因此一次请求可能是：

```text
External Client
      ↓ HTTP
Hertz API Gateway
      ↓ Kitex RPC
Payment Service
```

这也是理解项目代码时最重要的边界。 不要把它背成：

> Hertz 是 Web 框架，Kitex 是 RPC 框架。

还要知道为什么分层：

```text
External contract
≠
Internal service contract
```

Gateway 可以负责：

* HTTP parsing；
* auth；
* request metadata；
* rate limit；
* HTTP status mapping。

内部服务则通过 RPC contract 通信。

### 3.19 [P0] Middleware 是什么？

Middleware 是位于请求处理链中的横切逻辑。 典型：

```text
Request
  ↓
Recovery
  ↓
Request ID
  ↓
Authentication
  ↓
Rate Limit
  ↓
Access Log
  ↓
Handler
```

适合处理：

```text
auth
logging
tracing
metrics
recovery
rate limit
request metadata
```

**为什么不全部写进 Handler？**

否则每个 handler 都变成：

```go
func Handler() {
    auth()
    trace()
    rateLimit()
    validate()
    business()
    log()
}
```

横切关注点会大量重复。

### 3.20 [P1] Middleware 顺序为什么重要？

假设：

```text
RateLimit
→ Auth
```

那么 rate-limit key 可能还不知道用户 identity。 如果：

```text
AccessLog
```

放在不能观察下游 response 的位置，也可能记录不到最终 status。 如果：

```text
Recovery
```

位置不对，可能捕获不了某些 downstream panic。 所以 Middleware 不是简单：

```text
list of functions
```

而是调用栈。 概念上：

```text
M1 before
  M2 before
    Handler
  M2 after
M1 after
```

改变顺序会改变语义。

### 3.21 [P0] Timeout 有哪些类型？

“设置一个 timeout”通常不够。 至少可能有：

```text
connection timeout
read timeout
write timeout
request timeout
RPC timeout
idle timeout
```

**Connection Timeout**

限制：

```text
建立连接最多等多久
```

**Read Timeout**

限制：

```text
读取数据允许等待多久
```

**Write Timeout**

限制：

```text
写数据允许等待多久
```

**Request / RPC Timeout**

限制：

```text
整个业务调用允许多久
```

**Idle Timeout**

限制：

```text
一个空闲 keep-alive connection 可以保留多久
```

它们解决的是不同阶段的问题。

### 3.22 [P1] 为什么 Timeout 不能只在最外层设置？

例如：

```text
Gateway timeout = 5s
```

内部：

```text
Service A
→ Service B
→ Database
```

如果 B 完全没有 timeout：

```text
DB hangs
```

Service A 可能一直占用：

* goroutine；
* connection；
* request state。

即使 Gateway 已经：

```text
return 504
```

内部工作还可能继续。 因此 deadline 最好逐层传播。

### 3.23 [P1] Deadline Propagation 应该怎么做？

假设用户请求最多：

```text
1000 ms
```

Gateway 已经用了：

```text
200 ms
```

那么 Service A 不应该重新给 Service B：

```text
1000 ms
```

而应该传播：

```text
remaining deadline ≈ 800 ms
```

调用链：

```text
Client
deadline T

   ↓

Gateway
deadline T

   ↓

Service A
deadline T

   ↓

Service B
deadline T
```

每一层看到的是同一个绝对 deadline。

**为什么比每层独立 Timeout 更合理？**

如果：

```text
A timeout = 1s
B timeout = 1s
C timeout = 1s
```

最坏可能变成：

```text
≈3s
```

而用户只愿意等：

```text
1s
```

### 3.24 [P1] 子调用 Timeout 是否应该等于剩余 Deadline？

不一定。 假设：

```text
request remaining = 900ms
```

当前业务还需要：

```text
RPC A
RPC B
response serialization
```

如果给 RPC A：

```text
900ms
```

A 一旦耗尽全部时间，后面没有任何恢复空间。 因此常做：

```text
parent budget
    ↓
allocate child budget
```

例如：

```text
总剩余 900ms

RPC A 300ms
RPC B 300ms
reserve 300ms
```

具体策略取决于调用图。 这里体现：

```text
Deadline propagation
```

和：

```text
Timeout budgeting
```

不是完全同一个问题。

### 3.25 [P0] 什么是 Retry？

Retry 是失败后重新尝试操作。 例如：

```text
attempt 1
→ transient network error

attempt 2
→ success
```

它对短暂故障非常有效。 例如：

```text
temporary connection reset
one unhealthy replica
brief overload
```

**但 Retry 不是默认安全**

必须先问：

```text
这个操作重复执行安全吗？
```

### 3.26 [P1] 哪些操作更适合自动 Retry？

**Read-only Query**

例如：

```text
GET user
read catalog
query status
```

通常更适合。

**Explicitly Idempotent Mutation**

如果有可靠：

```text
idempotency key
```

也可能适合。

**没有幂等保护的 Side Effect**

例如：

```text
charge card
transfer asset
send irreversible order
```

不能因为：

```text
timeout
```

就盲目 retry。 否则：

```text
first call succeeded
response lost
retry
→ duplicate side effect
```

### 3.27 [P1] Retry 为什么会放大故障？

假设系统正常：

```text
1000 req/s
```

下游开始变慢。 每个请求最多 retry 3 次：

```text
original
+
3 retries
```

最坏瞬间变成：

```text
4000 downstream attempts/s
```

于是：

```text
downstream slow
→ retry
→ more load
→ slower
→ more retry
→ collapse
```

这叫：

```text
retry amplification
```

或者更宽泛地：

```text
retry storm
```

### 3.28 [P2] 多层 Retry 为什么尤其危险？

假设：

```text
Gateway retry 3
Service A retry 3
Service B retry 3
```

一次用户请求最坏可能产生：

```text
3 × 3 × 3 = 27
```

次底层 attempt。 如果每层语义是：

```text
1 initial + 3 retries
```

甚至可能达到：

```text
4 × 4 × 4 = 64
```

因此：

> **Retry policy 必须按调用链设计，而不是每个团队独立“加个 retry”。**

常见原则：

```text
retry at one appropriate layer
```

或者明确：

```text
retry budget
```

避免指数放大。

### 3.29 [P1] Exponential Backoff 是什么？

如果 retry 间隔固定：

```text
100ms
100ms
100ms
100ms
```

大量客户端同时失败后，会一起再次冲击服务。 Exponential Backoff：

```text
100ms
200ms
400ms
800ms
...
```

逐步降低 retry 频率。 简化：

```text
delay_n = base × 2^n
```

通常还会设置：

```text
max delay
```

否则等待时间无限增长。

### 3.30 [P1] 为什么还要 Jitter？

假设 10000 个 client 同时失败。 即使都有 exponential backoff：

```text
100ms
200ms
400ms
```

它们仍然可能：

```text
同时 100ms retry
同时 200ms retry
同时 400ms retry
```

形成 synchronized burst。 Jitter 给 retry delay 加随机性：

```text
87ms
143ms
221ms
...
```

让请求分散。 因此常见组合是：

```text
exponential backoff
+
jitter
```

### 3.31 [P0] Connection Pool 是什么？

创建 TCP connection 有成本。 所以 client 通常维护：

```text
Connection Pool

conn1
conn2
conn3
...
```

request 来时：

```text
borrow / reuse connection
```

而不是每次：

```text
dial
handshake
close
```

**Connection Pool 解决**

```text
connection setup overhead
socket churn
TLS handshake overhead
```

**但 Pool 太大也有问题**

如果：

```text
100 application instances
×
1000 connections each
```

下游可能突然面对：

```text
100000 connections
```

所以 pool size 是系统容量设计的一部分。

### 3.32 [P1] Connection Pool 满了会发生什么？

可能：

```text
wait for connection
```

于是 request latency 包含：

```text
queueing time
+
actual RPC time
```

例如真正 DB query：

```text
20ms
```

但 connection pool 等了：

```text
980ms
```

用户看到：

```text
1s latency
```

如果只监控 SQL duration：

```text
20ms
```

可能完全找错方向。 所以需要区分：

```text
queue wait
connection acquisition
network
server processing
```

### 3.33 [P1] 什么是 Head-of-Line Blocking？

直觉上：

> 前面的请求阻塞，导致后面的请求也无法及时推进。

例如串行队列：

```text
slow request
  ↓
request 2
request 3
request 4
```

后面的请求必须等。 在不同协议、队列和资源池中都可能出现类似问题。 因此分析 latency 时，不只看：

```text
单个请求执行时间
```

也看：

```text
queueing
contention
shared transport
```

### 3.34 [P1] RPC Failure 应该怎么分类？

不要统一：

```text
if err != nil {
    retry
}
```

至少可以思考：

**Invalid Request**

```text
INVALID_ARGUMENT
```

重新执行没有意义。

**Not Found**

```text
NOT_FOUND
```

通常也是业务事实。

**Permission Failure**

```text
PERMISSION_DENIED
```

retry 不会自动获得权限。

**Timeout**

```text
DEADLINE_EXCEEDED
```

意味着没有及时拿到结果。 但：

```text
outcome may be unknown
```

**Transient Availability Failure**

例如：

```text
UNAVAILABLE
connection reset
temporary overload
```

有可能适合 retry。

**Internal Bug**

```text
INTERNAL
```

是否 retry 取决于错误性质。 核心是：

```text
error classification
→ retry policy
```

而不是：

```text
error
→ retry
```

### 3.35 [P1] Transport Error 和 Business Error 有什么区别？

例如调用 payment service。

**Transport Error**

```text
connection reset
timeout
RPC unavailable
```

说明：

> 调用通道出了问题。

**Business Error**

```text
insufficient balance
invalid currency
payment already settled
```

说明：

> 服务明确处理了请求，并返回业务结论。

如果二者都变成：

```text
500 error
```

上层就无法做可靠策略。 因此良好的 contract 应区分：

```text
transport status
business status
domain result
```

### 3.36 [P1] 为什么 Error Mapping 很重要？

假设内部 RPC：

```text
NOT_FOUND
```

Gateway 却统一：

```http
500 Internal Server Error
```

客户端会以为：

> 服务坏了，可以 retry。

但真实情况是：

> 资源不存在。

于是可能产生无意义 retry。 Error mapping 应保留语义，例如：

```text
RPC NOT_FOUND
→ HTTP 404

RPC INVALID_ARGUMENT
→ HTTP 400

RPC PERMISSION_DENIED
→ HTTP 403
```

但不能机械一一对应。 最终要看：

```text
public API contract
```

### 3.37 [P1] IDL / Schema Evolution 为什么危险？

服务不会永远同时升级。 可能存在：

```text
Client v1
Client v2
Server v2
Server v3
```

因此 schema 修改必须考虑兼容性。 危险操作包括：

```text
删除仍被旧 client 使用的字段
改变字段语义
复用旧 field id
修改 enum meaning
把 optional 变成 required
```

**更安全的方向**

常见原则：

```text
additive evolution
```

例如增加 optional field。 旧客户端：

```text
不知道新字段
```

但仍能工作。

### 3.38 [P1] Forward Compatibility 和 Backward Compatibility 是什么？

术语具体解释在不同语境会略有差异，但面试可以抓住主体。

**新 Server 能处理旧 Client**

例如：

```text
Client v1
→
Server v2
```

升级 server 后，旧 client 仍然能调用。

**新 Client 能与旧 Server 共存**

例如：

```text
Client v2
→
Server v1
```

client 不能假设所有 server 都已经支持最新字段。 核心不是背术语，而是理解：

> **分布式系统升级不是一个原子操作。**

所以协议设计必须允许 mixed-version deployment。

### 3.39 [P2] 为什么 Enum Evolution 特别容易踩坑？

例如原来：

```text
0 UNKNOWN
1 SUCCESS
2 FAILED
```

新版本加入：

```text
3 PENDING_REVIEW
```

旧 client 如果写：

```go
switch status {
case SUCCESS:
case FAILED:
default:
    panic("impossible")
}
```

新 enum 一出现就可能 crash。 因此客户端应该考虑：

```text
unknown future value
```

而不是假设：

```text
当前 schema 枚举集合永远封闭
```

这也是 schema evolution 的一部分。

### 3.40 [P1] 什么是 Service Discovery？

如果客户端写死：

```text
10.0.0.13:8081
```

服务扩容或实例迁移后就需要修改配置。 Service Discovery 解决：

```text
service name
→
available instances
```

例如：

```text
payment-service
→
10.0.0.13:8081
10.0.0.21:8081
10.0.0.37:8081
```

RPC client 再进行：

```text
load balancing
```

**当前项目为什么可以直接 HostPort？**

本地开发、小规模部署中：

```text
stablepay-payment-service:808x
```

本身就可以由容器/DNS 等基础设施解析。 这不影响 Service Discovery 作为通用知识理解。

### 3.41 [P1] Load Balancing 是什么？

当下游有多个实例：

```text
Service B1
Service B2
Service B3
```

客户端需要决定：

```text
这次调用谁？
```

最简单：

```text
round robin
```

还可以考虑：

```text
weighted
least-loaded
latency-aware
consistent hashing
```

**Load Balancing 不能修复慢服务**

如果所有实例都：

```text
CPU 100%
DB overloaded
```

换一个实例没有本质帮助。 它解决：

```text
traffic distribution
```

不是无限 capacity。

### 3.42 [P2] 什么是 Circuit Breaker？

Circuit Breaker 用于：

> 下游已经明显故障时，不继续无限发送注定失败的请求。

典型状态：

```text
CLOSED
  ↓ failures exceed threshold
OPEN
  ↓ cooldown
HALF-OPEN
  ↓ trial success
CLOSED
```

**Closed**

正常发送请求。

**Open**

快速失败：

```text
fail fast
```

不继续打下游。

**Half-open**

放少量 probe 请求判断是否恢复。

### 3.43 [P2] Circuit Breaker 和 Retry 有什么关系？

Retry：

```text
失败
→ 再试一次
```

Circuit Breaker：

```text
失败已经足够多
→ 暂时不要再试
```

两者方向甚至相反。 如果配置不好：

```text
retry aggressively
+
breaker opens slowly
```

可能先把下游彻底打垮。 更合理的是共同考虑：

```text
timeout
retry
breaker
load shedding
```

而不是分别打开默认配置。

### 3.44 [P2] Circuit Breaker 和 Rate Limit 有什么区别？

**Rate Limit**

限制：

```text
允许多少请求进入
```

例如：

```text
1000 req/s
```

主要保护：

* 服务 capacity；
* fair usage；
* API quota。

**Circuit Breaker**

根据：

```text
下游故障状态
```

决定：

```text
暂时停止调用
```

所以：

```text
Rate Limit
→ control traffic volume

Circuit Breaker
→ react to dependency failure
```

### 3.45 [P2] 什么是 Bulkhead？

名字来自船舱隔离。 如果船的一部分进水：

```text
不能让整艘船一起沉
```

系统里 Bulkhead 表示资源隔离。 例如：

```text
Payment RPC
→ pool A

Search RPC
→ pool B
```

如果 Search 卡死：

```text
pool B exhausted
```

Payment 仍有自己的：

```text
pool A
```

不会一起被拖死。

**可以隔离什么？**

```text
thread/goroutine capacity
connection pool
queue
worker pool
memory budget
```

### 3.46 [P2] 什么是 Load Shedding？

系统过载时主动拒绝部分工作。 例如：

```text
capacity = 1000 req/s
incoming = 5000 req/s
```

如果坚持全部排队：

```text
queue grows
latency grows
memory grows
timeout grows
retry grows
collapse
```

Load Shedding 选择：

```text
早失败一部分
```

让剩余请求仍能完成。 例如：

```http
429 Too Many Requests
```

或：

```http
503 Service Unavailable
```

**为什么早失败可能比慢失败更好？**

用户等：

```text
30 秒
→ timeout
```

占用大量系统资源。 而：

```text
50 ms
→ overload response
```

至少可以：

* retry later；
* fallback；
* degrade。

### 3.47 [P2] 什么是 Retry Budget？

如果每一个失败请求都可以 retry：

```text
系统越故障
→ retry 越多
```

这正好形成正反馈。 Retry Budget 的思路是：

> retry traffic 本身也必须有上限。

例如：

```text
original traffic = 1000/s

retry budget = 10%

最多额外：
100 retries/s
```

而不是：

```text
每个请求都有 5 次无限 retry 权利
```

这种思路更适合大规模系统。

### 3.48 [P2] Hedged Request 是什么？

对 tail latency 很敏感的 read-only 请求，可以考虑：

```text
request A
   ↓
等短暂时间
   ↓
还没回来
   ↓
向另一个 replica 发 request B
```

谁先返回就使用谁。 目的：

```text
降低 tail latency
```

**为什么危险？**

它会增加：

```text
load
```

如果服务本来就过载：

```text
slow
→ hedge
→ more requests
→ slower
```

会恶化问题。 所以通常只适用于：

* read-only；
* idempotent；
* 有严格 budget；
* tail latency 明显来自个别慢 replica；

等条件。

### 3.49 [P1] 为什么 Request ID 和 Trace ID 要跨 RPC 传播？

假设：

```text
Gateway
→ Payment Service
→ Blockchain Adapter
```

三个服务分别写 log。 如果没有共同 identity：

```text
Gateway log #1827
Payment log #37122
Blockchain log #9931
```

很难知道它们属于同一个用户请求。 传播：

```text
trace_id = abc
```

后：

```text
Gateway       trace=abc
Payment       trace=abc
Blockchain    trace=abc
```

可以重建调用链。

**Request ID 和 Trace ID 是否一定相同？**

不一定。 简单系统可以：

```text
trace_id = request_id
```

复杂系统可能：

```text
一个 trace
包含多个 span / request
```

后面 Observability 章节再展开。

### 3.50 [P1] 为什么 RPC Metadata 不能什么都塞？

跨服务 metadata 常放：

```text
trace id
request id
auth identity
deadline
```

如果不断把业务字段塞进去：

```text
merchant
price
user preferences
model result
...
```

就会形成：

> 隐式 contract。

代码函数签名看不出依赖哪些数据，却必须依赖 metadata 才能工作。 因此：

```text
业务输入
→ request message

cross-cutting context
→ metadata/context
```

边界更清楚。

### 3.51 [P2] 为什么 Timeout、Retry 和 Idempotency 必须一起设计？

这是整个 RPC 章节最重要的一条因果链。 假设：

```text
Client
  ↓
POST /charge
  ↓
Server charges successfully
  ↓
Response lost
```

Client：

```text
timeout
```

如果系统只有 timeout：

```text
不知道结果
```

如果再加 retry：

```text
可能重复 charge
```

所以还需要：

```text
idempotency identity
```

链路变成：

```text
request
  ↓
timeout
  ↓
retry same logical command
  ↓
server recognizes same identity
  ↓
return existing result
```

因此：

```text
Timeout
```

解决：

> 最多等多久。

```text
Retry
```

解决：

> 临时失败后要不要重新尝试。

```text
Idempotency
```

解决：

> 重试是否会重复产生业务效果。

这三个不能分别孤立设计。

### 3.52 [P2] 为什么 Retry 和 Reconciliation 不是一回事？

Retry：

```text
再做一次
```

Reconciliation：

```text
查清前一次到底发生了什么
```

对于 read-only 操作：

```text
retry
```

通常简单。 对于 payment：

```text
timeout
```

之后先做：

```text
query transaction status
query provider state
query ledger state
```

可能比直接：

```text
submit payment again
```

安全得多。 所以：

```text
unknown side effect
→ reconcile first
```

是后面分布式可靠性章节的主线。

### 3.53 [P2] 为什么“设置 Retry”并不能提高所有系统的可靠性？

因为可靠性不是：

```text
success rate of individual RPC
```

这么简单。 假设 retry 后 API 成功率从：

```text
99%
→ 99.9%
```

但同时：

```text
duplicate payment ↑
downstream overload ↑
tail latency ↑
```

系统整体反而可能更不可靠。 所以真正应该优化的是：

```text
business correctness
+
availability
+
latency
+
resource safety
```

而不是单个 RPC library 的：

```text
request success %
```

### 3.54 [P1] Gateway 应该负责什么？

典型 API Gateway 可以负责：

```text
HTTP termination
routing
authentication
request metadata
rate limit
protocol translation
access logging
basic validation
```

但不应该无限吸收业务逻辑。 危险趋势：

```text
Gateway
→ auth
→ payment state machine
→ catalog logic
→ ledger logic
→ reconciliation
→ everything
```

最终 Gateway 变成：

```text
distributed monolith core
```

**边界原则**

Gateway 更适合：

```text
edge concerns
+
protocol adaptation
```

而核心 domain state 应该有明确 owner。

### 3.55 [P1] API Gateway 和 BFF 有什么区别？

二者可以重叠，但关注点不同。

**API Gateway**

偏：

```text
routing
auth
rate limiting
protocol translation
cross-cutting concerns
```

**BFF**

Backend for Frontend 更偏：

> 为某类前端提供专门聚合和数据形态。

例如：

```text
Mobile BFF
Web BFF
```

根据客户端需求：

```text
aggregate A+B+C
```

减少前端多次调用。 StablePay 当前更接近：

```text
API Gateway
```

这一类边界。

### 3.56 [P2] 为什么 Gateway Retry 尤其需要谨慎？

Gateway 离业务 side effect 可能比较远。 它看到：

```text
RPC timeout
```

却不知道：

```text
Payment Service
```

内部到底：

```text
没收到
收到未执行
执行成功
commit 后 response 丢了
```

如果 Gateway 根据 transport error 自动：

```text
retry mutation
```

可能重复产生 side effect。 所以 Gateway retry 最安全的场景通常是：

```text
read-only
explicit idempotency
clearly retryable failure
```

不能只根据：

```text
err != nil
```

自动重试所有 RPC。

### 3.57 [P1] 请求为什么需要 Canonical Internal Contract？

Gateway 接收外部 JSON：

```text
amount
currency
idempotency_key
```

内部 Payment Service 也有自己的 RPC schema。 如果 Gateway 把 HTTP payload：

```text
原样 map 转发
```

内部服务就被外部 API shape 强耦合。 更合理：

```text
External HTTP Contract
       ↓
Gateway Translation
       ↓
Canonical Internal RPC Contract
```

这样：

```text
外部 API version
```

可以变化，而内部 domain contract 不一定同步变化。 反过来也一样。

### 3.58 [P1] 为什么 `map[string]interface{}` 不适合作为长期内部 Contract？

它很灵活：

```go
map[string]interface{}
```

但会失去：

```text
compile-time type checking
required-field visibility
field discoverability
schema evolution control
refactoring safety
```

例如：

```go
req["amount_minor"]
```

拼错成：

```go
req["amount_mionr"]
```

编译器不会发现。 IDL-generated type：

```go
req.AmountMinor
```

能让更多错误提前暴露。

**什么时候 Map 仍然合理？**

例如：

```text
dynamic metadata
generic JSON adapter
loosely structured extension field
```

但核心 payment/domain contract 应尽量强类型。

### 3.59 [P2] 为什么 Request Fan-out 会放大 Tail Latency？

假设一个 Gateway request 并行请求：

```text
Service A
Service B
Service C
Service D
Service E
```

最终必须：

```text
all succeed
```

整个请求 latency 大致受：

```text
最慢 dependency
```

影响。 如果 fan-out 到 100 个 shard：

```text
只要其中一个 tail request 很慢
```

整体就慢。 所以大型 fan-out 系统特别关注：

```text
tail latency
timeout budget
partial result
hedging
quorum
```

而不是只看平均 latency。

### 3.60 [P2] 为什么 P99 比平均延迟更能暴露 RPC 问题？

假设：

```text
99 requests = 10ms
1 request   = 5000ms
```

平均值：

```text
≈60ms
```

看起来还可以。 但 1% 用户会：

```text
5 秒
```

如果一次用户请求还 fan-out 到多个下游：

```text
遇到至少一个 tail latency
```

的概率会继续上升。 所以生产 RPC 通常更关注：

```text
P50
P95
P99
```

而不是只看 average。 详细方法放到 Observability 章节。

### 3.61 HTTP / RPC 的经典 Failure Timeline

这是本章最值得真正理解的一张图。

```text
T0
Client sends request

T1
Gateway receives

T2
Gateway sends RPC

T3
Service receives RPC

T4
Service commits database

T5
Service executes remote side effect

T6
Service prepares response

T7
Network breaks

T8
Gateway gets timeout

T9
Client retries
```

在 `T8`： Gateway 只知道：

```text
没有拿到成功 response
```

它并不知道：

```text
T3 有没有发生？
T4 有没有发生？
T5 有没有发生？
```

因此：

```text
timeout
```

不是一个完整业务结论。 这个模型后面会自然连接：

```text
Idempotency
Unknown Outcome
Reconciliation
Outbox
Saga
PaymentIntent
```

### 3.62 高频错误设计：每个 RPC 都 Retry 3 次

代码看起来很可靠：

```text
timeout
→ retry 3 times
```

但如果请求是：

```text
GET status
```

和：

```text
POST transfer
```

风险完全不同。 正确思考顺序应该是：

```text
这个 operation 是什么语义？
        ↓
是否 read-only？
        ↓
是否 idempotent？
        ↓
是否存在 external side effect？
        ↓
timeout 后 outcome 是否可知？
        ↓
哪些 error 属于 transient？
        ↓
retry 在哪一层？
        ↓
retry budget 是多少？
```

最后才是：

```text
retry count = ?
```

### 3.63 高频错误设计：每层各自 1 秒 Timeout

调用链：

```text
Gateway
→ A
→ B
→ C
```

每层：

```text
timeout = 1s
```

并不意味着：

```text
整个请求 ≤ 1s
```

如果 timeout 没有通过 deadline 正确传播，可能不断重新获得完整 1 秒预算。 正确模型：

```text
用户请求有一个整体 deadline
↓
各层只能消费剩余 budget
```

### 3.64 高频错误设计：把所有 5xx 都 Retry

`5xx` 只能说明服务端没有按正常成功路径完成请求。 但原因可能是：

```text
temporary overload
permanent application bug
already committed but response building failed
downstream unknown outcome
```

所以：

```text
HTTP 5xx
```

本身不足以决定：

```text
retry mutation
```

尤其是不可逆 side effect。

### 3.65 高频错误设计：Timeout 越长越可靠

把 timeout：

```text
1s
→ 30s
```

确实可能让更多慢请求“最终成功”。 但同时：

```text
in-flight requests ↑
memory ↑
connections occupied ↑
queue ↑
tail latency ↑
```

在过载情况下反而更容易雪崩。 Timeout 本质是：

> **系统资源和用户延迟预算的一部分。**

不是越长越好。

### 3.66 高频错误设计：只配置 Circuit Breaker 就能防雪崩

雪崩可能来自：

```text
unbounded concurrency
retry amplification
queue growth
slow database
connection pool exhaustion
downstream failure
```

Circuit Breaker 只覆盖其中一部分。 真正的 resilience 往往组合：

```text
deadline
bounded concurrency
rate limit
backpressure
retry budget
circuit breaker
load shedding
graceful degradation
```

所以“熔断”不是万能保险丝。

### 3.67 [P2] 什么是 Graceful Degradation？

下游部分功能不可用时，不一定让整个请求失败。 例如：

```text
Recommendation unavailable
```

可以：

```text
return core result
without recommendation
```

或者：

```text
semantic ranking unavailable
```

退化到：

```text
structured deterministic ranking
```

**但支付类功能不能随便 Degrade**

不能：

```text
authorization service unavailable
→ skip authorization
```

这属于：

```text
fail-open
```

可能破坏安全 invariant。 所以 degradation 必须看：

```text
这个 dependency 是 enhancement
还是 correctness boundary？
```

### 3.68 [P2] Fail-fast 和 Wait-longer 怎么选？

如果下游明显不可用：

```text
99% requests timeout
```

继续让每个请求：

```text
wait 10s
```

只会占资源。 此时：

```text
fail fast
```

往往更健康。 但如果：

```text
任务本身是离线 batch
```

对 latency 不敏感：

```text
wait / retry
```

可能更合理。 所以策略取决于：

```text
interactive vs offline
latency SLO
side-effect semantics
retryability
resource cost
```

### 3.69 [P2] 什么是 Timeout Budget？

假设 API SLO 要求：

```text
P99 < 1s
```

调用链：

```text
Gateway
→ Auth
→ Payment
→ Blockchain
```

不能所有组件各自配置：

```text
1s timeout
```

而应该进行 budget allocation。 例如：

```text
Gateway overhead      50ms
Auth                  100ms
Payment               200ms
Blockchain            400ms
response reserve      250ms
```

这里只是示意。 本质是：

> **Timeout 是端到端 latency budget 的分配问题。**

### 3.70 [P2] 什么是 Deadline-aware Work？

如果：

```text
ctx deadline remaining = 20ms
```

但当前操作平均：

```text
200ms
```

此时继续开始昂贵操作可能没有意义。 系统可以：

```text
check remaining deadline
```

然后：

```text
fail early
```

避免：

```text
明知不可能完成
仍占用资源
```

这是比单纯“调用时加 timeout”更进一步的设计。

### 3.71 [P2] 为什么 RPC Call 的 Error 不能简单包装成 500？

因为错误包含决策信息。 例如：

```text
deadline exceeded
```

上层可能需要：

```text
reconcile
```

而不是：

```text
generic internal error
```

又如：

```text
invalid argument
```

应该：

```text
reject
```

而不是：

```text
retry
```

因此 Error Taxonomy 本身是 distributed protocol 的一部分。

### 3.72 本章高频对比

| 概念 A            | 概念 B            | 核心区别                            |
| --------------- | --------------- | ------------------------------- |
| TCP             | HTTP            | 可靠字节流 vs 应用层请求语义                |
| HTTP            | RPC             | 网络协议/API 形式 vs 远程过程调用抽象         |
| HTTP API        | Internal RPC    | 外部兼容性边界 vs 内部服务 contract        |
| REST            | RPC-style API   | 资源导向 vs 操作导向                    |
| Safe            | Idempotent      | 无业务副作用 vs 重复效果等价                |
| Keep-alive      | Connection Pool | 连接复用能力 vs 多连接生命周期管理             |
| Timeout         | Deadline        | 相对等待时间 vs 绝对完成时间                |
| Deadline        | Timeout Budget  | 最晚结束时间 vs 各子调用资源分配              |
| Retry           | Reconciliation  | 再执行一次 vs 确认前次结果                 |
| Retry           | Circuit Breaker | 失败后继续尝试 vs 故障期停止尝试              |
| Rate Limit      | Circuit Breaker | 限制流量 vs 响应下游故障                  |
| Circuit Breaker | Load Shedding   | 阻断故障依赖 vs 主动拒绝过载工作              |
| Worker Pool     | Connection Pool | 应用执行容量 vs 网络连接容量                |
| Transport Error | Business Error  | 通信失败 vs 业务明确拒绝                  |
| Request ID      | Trace ID        | 单请求 identity vs 分布式调用链 identity |
| Domain Model    | Wire Contract   | 内部业务对象 vs 跨进程协议                 |
| Serialization   | IDL             | 对象转 bytes vs 定义跨服务 schema       |
| Backoff         | Jitter          | 延长重试间隔 vs 打散同步重试                |
| Gateway         | BFF             | 边缘跨切能力 vs 前端专用聚合                |
| Failure         | Unknown Outcome | 已知失败 vs 不知道是否成功                 |

### 3.73 面试前一分钟速记

```text
HTTP 是应用层协议，
TCP 提供可靠有序字节流。

TCP reliable
不等于
business exactly-once。

RPC 看起来像本地函数调用，
但远程调用存在：
latency / timeout / partial failure / unknown outcome。

IDL 的意义不仅是 codegen，
而是显式定义 wire contract。

Domain model
≠
wire contract。

Hertz：
当前项目的 HTTP edge。

Kitex：
当前项目的内部 RPC。

Middleware 顺序有语义，
不是随便排。

Timeout 不是一种：
connection / read / write / request / RPC / idle
解决不同问题。

Deadline 应该沿调用链传播。

Retry 之前先问：
read-only？
idempotent？
side effect？
unknown outcome？

Retry 会放大故障。

多层 Retry 可能乘法放大。

常见：
exponential backoff + jitter。

Connection pool 减少建连成本，
但 pool 本身也是 capacity boundary。

Circuit Breaker：
故障时 fail fast。

Bulkhead：
隔离资源。

Load Shedding：
过载时主动拒绝。

Timeout + Retry + Idempotency
必须一起设计。

Timeout ≠ Failed。

对不可逆 side effect：
unknown outcome
通常先 reconcile，
而不是 blind retry。
```

### 3.74 StablePay 映射

本章继续只保留概念锚点。 当前请求链可以帮助理解：

```text
External Client
      ↓ HTTP
Hertz API Gateway
      ↓
Middleware
      ↓
Kitex Client
      ↓ RPC
DID / Payment / Verification / Query Service
```

项目里已有对应概念：

```text
Hertz server
→ API Gateway HTTP edge

Kitex generated client
→ internal RPC

IDL
→ stablepayai-idl / generated RPC contract

RPCTimeout
→ downstream RPC timeout

FailureRetry
→ client retry policy

Request ID / Trace ID
→ request metadata propagation

Recovery middleware
→ panic boundary

Read / Write timeout
→ HTTP server resource boundary
```

这里有一个值得在 01 中单独追问、但不在 02 展开的项目问题：

```text
当前 Gateway 的 Kitex client
为多个 downstream 配置了 failure retry。

对于 read RPC，
这种设计和 mutation/payment RPC
并不天然具有相同安全语义。
```

02 只需要掌握通用判断：

```text
Transport retry policy
必须服从业务 side-effect semantics。
```

至于 StablePay 当前哪些 RPC 能安全 retry、哪些依赖 idempotency、哪些应该在 UNKNOWN 后 reconcile，应继续留给 01 的项目追问。

### 3.75 本章学习优先级

### 第一轮：P0

先确保可以立即回答：

```text
TCP / HTTP
HTTP Method
Safe / Idempotent
HTTP Status
REST
HTTP/1.1 / HTTP/2
RPC
IDL
Serialization
Hertz / Kitex
Middleware
Timeout
Retry
Connection Pool
```

### 第二轮：P1

重点：

```text
Keep-alive
Deadline propagation
Timeout budget
Retry safety
Exponential Backoff
Jitter
Retry amplification
Error classification
Transport vs Business Error
Schema evolution
Service discovery
Load balancing
Request ID / Trace ID
```

### 第三轮：P2

针对 Go 后端、Infra 和 Agent Runtime：

```text
multi-layer retry amplification
circuit breaker
bulkhead
load shedding
retry budget
hedged request
tail latency
fan-out
graceful degradation
deadline-aware work
side-effect-aware retry
```

最终不要只回答：

> “微服务里要配 timeout、retry、熔断和限流提高可靠性。”

更完整的回答应该是：

> Timeout 限制单次工作能占用资源多久；Retry 可以遮蔽瞬时故障，但会增加负载，而且 mutation 必须先确认幂等与 unknown-outcome 语义；Backoff 和 jitter 用来降低同步重试；Circuit Breaker 在下游持续失败时 fail fast；Bulkhead 隔离资源；Load Shedding 在本服务过载时主动拒绝部分工作。它们不是一组可以全部打开的默认开关，而需要根据调用链、side effect、deadline 和容量一起设计。

## 4. MySQL 与事务

数据库八股最容易出现两种极端： 第一种只会背：

```text
ACID
B+ Tree
MVCC
索引
事务隔离级别
```

第二种一上来就谈：

```text
分布式事务
Saga
Outbox
CDC
```

却解释不清最基本的：

```text
为什么两个请求会覆盖彼此？
为什么 SELECT 后 UPDATE 不是原子的？
为什么 UNIQUE 比应用层先查更可靠？
为什么 row lock 仍然会 deadlock？
为什么 DB commit 后调用远程 API 会产生 crash window？
```

这一章按下面的链路组织：

```text
数据如何存
    ↓
如何查得快
    ↓
事务如何保证本地正确性
    ↓
多个事务如何并发
    ↓
锁与 MVCC 如何协调
    ↓
并发写如何避免 lost update
    ↓
本地事务结束以后
    ↓
为什么跨服务副作用又失去原子性
```

### 4.1 [P0] 什么是事务？

事务是一组数据库操作组成的逻辑执行单元。 例如转账：

```text
账户 A -100
账户 B +100
```

希望：

```text
要么都成功
要么都失败
```

而不是：

```text
A 已扣款
B 没到账
```

因此：

```sql
BEGIN;

UPDATE account
SET balance = balance - 100
WHERE id = 'A';

UPDATE account
SET balance = balance + 100
WHERE id = 'B';

COMMIT;
```

如果中途失败：

```sql
ROLLBACK;
```

事务提供的是：

> **数据库内部一组状态变化的原子边界。**

### 4.2 [P0] ACID 分别是什么？

**Atomicity**

原子性：

```text
事务中的操作
要么全部提交
要么全部不提交
```

例如：

```text
debit A
credit B
```

不能只发生一半。

**Consistency**

一致性：

> 事务执行前后，数据库应该保持定义好的约束与 invariant。

例如：

```text
PRIMARY KEY 唯一
UNIQUE 不重复
外键约束满足
账户余额规则满足
```

注意这里的 Consistency 和 CAP 里的 Consistency 不是同一个概念。

**Isolation**

隔离性： 多个事务并发执行时，不应该随意看到彼此不完整的中间状态。 例如：

```text
Transaction A 正在改余额
Transaction B 同时读取
```

Isolation Level 决定 B 可以观察到什么。

**Durability**

持久性： 数据库确认：

```text
COMMIT success
```

后，即使进程 crash，已提交数据也应能够恢复。 这通常依赖：

```text
redo log
WAL-like mechanism
disk persistence
```

等机制。

### 4.3 [P0] ACID 的 Consistency 和 CAP 的 Consistency 是一回事吗？

不是。

**ACID Consistency**

强调：

```text
数据库状态满足业务 / schema invariant
```

例如：

```text
UNIQUE
CHECK
foreign key
balance rule
```

**CAP Consistency**

通常强调分布式副本：

> 对外表现得像一个一致的单一数据副本。

更接近：

```text
read sees latest write
```

这类分布式一致性语义。 所以面试时不要看到：

```text
Consistency
```

就当成同一件事。

### 4.4 [P0] MySQL 常见事务隔离级别有哪些？

SQL 标准常见四级：

```text
READ UNCOMMITTED
READ COMMITTED
REPEATABLE READ
SERIALIZABLE
```

隔离能力从弱到强。 一般：

```text
隔离越强
→ 并发自由度越低
→ coordination 成本可能越高
```

MySQL InnoDB 默认常见：

```text
REPEATABLE READ
```

但面试重点不是只背默认值，而是理解：

> 每个隔离级别允许什么并发现象。

### 4.5 [P0] 脏读是什么？

事务 A 修改：

```text
balance = 100
→ 0
```

但还没有 commit。 事务 B 却读到了：

```text
0
```

然后 A：

```text
ROLLBACK
```

真实最终状态还是：

```text
100
```

B 读到的是从未真正提交过的数据。 这叫：

```text
Dirty Read
```

### 4.6 [P0] 不可重复读是什么？

同一个事务中：

```text
第一次 SELECT
balance = 100
```

另一个事务提交：

```text
balance = 200
```

当前事务再次：

```text
SELECT
```

看到：

```text
200
```

同一行前后两次读取结果不同。 这叫：

```text
Non-repeatable Read
```

### 4.7 [P0] 幻读是什么？

事务 A：

```sql
SELECT *
FROM payment
WHERE amount > 100;
```

返回 10 行。 事务 B 插入一条：

```text
amount = 500
```

并提交。 事务 A 再执行相同范围查询，出现：

```text
11 行
```

像凭空出现了一条“幻影记录”。 这就是：

```text
Phantom Read
```

**与不可重复读区别**

可以粗略记：

```text
Non-repeatable Read
→ 同一行内容变化

Phantom Read
→ 查询结果集合变化
```

### 4.8 [P0] 什么是索引？

索引是额外的数据结构，用空间和写入成本换查询效率。 如果没有合适索引：

```sql
SELECT *
FROM payment
WHERE tx_id = ?;
```

可能需要：

```text
扫描大量记录
```

有索引后可以更快定位目标。

**索引并不是免费加速**

代价包括：

```text
额外磁盘空间
INSERT 更慢
UPDATE 更慢
DELETE 更慢
维护 B+ Tree
```

所以：

```text
index
```

是一种读写 trade-off。

### 4.9 [P0] 为什么 MySQL 索引常用 B+ Tree？

与普通二叉树相比，磁盘数据库更关心：

```text
减少随机 IO
```

B+ Tree 一个节点可以存很多 key：

```text
              [ ... many keys ... ]
             /        |        \
          node      node      node
```

所以树高较低。 假设：

```text
一层节点可以分叉数百次
```

少量层级就能覆盖大量记录。

**B+ Tree 的几个特点**

内部节点主要用于导航。 实际数据或叶子索引项集中在叶节点。 叶子通常按 key 有序并相互连接。

因此不仅适合：

```text
point lookup
```

也适合：

```text
range scan
ORDER BY
prefix range
```

### 4.10 [P0] 为什么 Hash Index 不适合替代 B+ Tree 做所有查询？

Hash：

```text
key
→ hash
→ bucket
```

非常适合：

```text
exact equality lookup
```

但不天然保留 key 顺序。 所以：

```sql
WHERE amount BETWEEN 100 AND 200
```

或者：

```sql
ORDER BY amount
```

就没有 B+ Tree 那么自然。 因此：

```text
Hash
→ exact lookup

B+ Tree
→ point + ordered/range access
```

### 4.11 [P0] 什么是聚簇索引？

InnoDB 中可以把聚簇索引理解为：

> 叶子节点保存完整行数据。

通常主键：

```text
PRIMARY KEY
```

就是聚簇索引 key。 概念上：

```text
Primary B+ Tree

key=1 → complete row
key=2 → complete row
key=3 → complete row
```

所以：

```sql
SELECT *
WHERE id = ?
```

可以直接通过主键树拿到整行。

### 4.12 [P0] 什么是二级索引？

Secondary Index 的叶子通常不是完整行，而是保存：

```text
secondary key
+
primary key
```

例如索引：

```sql
INDEX idx_status(status)
```

概念：

```text
status = PENDING
→ primary key 102

status = PENDING
→ primary key 391
```

如果查询还需要其他字段：

```sql
SELECT *
FROM payment
WHERE status = 'PENDING';
```

可能：

```text
先查 secondary index
→ 拿 primary key
→ 再查 clustered index
```

这个过程通常叫：

```text
回表
```

### 4.13 [P1] 什么是覆盖索引？

如果查询需要的所有字段已经存在于索引中：

```sql
SELECT id, status
FROM payment
WHERE status = 'PENDING';
```

假设索引已经包含：

```text
status
primary key id
```

就可能无需再回表。 这叫：

```text
covering index
```

**为什么快？**

减少：

```text
secondary index
→ primary index
```

的额外访问。

### 4.14 [P1] 什么是联合索引？

例如：

```sql
INDEX idx_user_status_created(
    user_id,
    status,
    created_at
)
```

它不是三个独立索引。 而是按类似：

```text
(user_id, status, created_at)
```

的组合排序。 因此索引字段顺序非常重要。

### 4.15 [P1] 什么是最左前缀原则？

联合索引：

```text
(a, b, c)
```

可以较自然支持：

```text
a

a, b

a, b, c
```

因为 B+ Tree 首先按：

```text
a
```

排序。 但直接：

```sql
WHERE b = ?
```

无法像从 `a` 开始那样高效定位整段 key space。

**不要机械背**

真正应该想：

> 当前查询能否利用索引已建立的排序前缀缩小扫描范围？

### 4.16 [P1] 哪些情况可能导致索引效果变差？

不是简单背“索引失效八股”。 常见考虑：

**对索引列进行难以利用索引的表达式**

```sql
WHERE YEAR(created_at) = 2026
```

可能不如范围条件：

```sql
WHERE created_at >= ...
  AND created_at < ...
```

**前导模糊匹配**

```sql
LIKE '%abc'
```

难以利用普通 B+ Tree 前缀排序。

**类型隐式转换**

字段类型和比较值不匹配，可能导致优化器无法使用预期索引。

**低选择性字段**

例如：

```text
gender
boolean flag
```

单独索引未必值得。

**查询返回大量行**

如果：

```text
80% 表数据
```

都满足条件，走索引 + 大量回表可能不如全表扫描。 所以最终还是：

```text
看 execution plan
```

而不是只靠规则表。

### 4.17 [P1] `EXPLAIN` 用来干什么？

用于观察 SQL 的执行计划。 重点可以关注：

```text
用了哪个索引？
扫描多少行？
访问类型是什么？
有没有额外排序？
有没有 temporary？
```

不要把：

```text
EXPLAIN
```

理解成性能优化终点。 它只是帮助回答：

> Optimizer 打算怎么执行这条 SQL？

真正性能还与：

```text
数据分布
cache
IO
concurrency
lock contention
```

有关。

### 4.18 [P0] PRIMARY KEY 和 UNIQUE INDEX 有什么区别？

Primary Key：

```text
一张表通常只有一个
不允许 NULL
通常作为行的主要 identity
```

Unique Index：

```text
可以有多个
用于保证其他字段组合唯一
```

例如：

```sql
UNIQUE KEY uk_idempotency(
    idempotency_key
)
```

数据库会保证：

```text
不能插入两个相同 key
```

**为什么业务系统经常需要 UNIQUE？**

因为：

> 应用层先查再写不是原子操作。

这是后面非常重要的一条线。

### 4.19 [P0] 为什么“先查有没有，再插入”挡不住并发？

代码：

```text
Request A:
SELECT
→ 不存在

Request B:
SELECT
→ 不存在
```

接着：

```text
A INSERT

B INSERT
```

如果数据库没有 UNIQUE：

```text
两个都成功
```

即使业务代码写了：

```go
if !exists {
    insert()
}
```

也没有用。 这就是典型：

```text
check-then-act race
```

**正确方向**

最终唯一性 invariant 应该尽量由：

```text
UNIQUE constraint
```

兜底。 应用层检查可以用于：

```text
更友好错误
```

但不能代替数据库约束。

### 4.20 [P0] 乐观锁是什么？

乐观锁假设：

> 冲突不是每次都会发生，因此先不持有长时间互斥锁，提交时检测版本是否仍然有效。

例如：

```text
version = 5
```

读取后进行计算。 更新：

```sql
UPDATE episode
SET
    state = 'PAYING',
    version = 6
WHERE id = ?
  AND version = 5;
```

如果：

```text
affected rows = 1
```

说明成功。 如果：

```text
affected rows = 0
```

说明期间有人更新过：

```text
stale write
```

### 4.21 [P0] 悲观锁是什么？

悲观锁假设冲突可能发生，所以先锁住目标数据。 例如：

```sql
SELECT *
FROM account
WHERE id = ?
FOR UPDATE;
```

当前事务获得相应锁后，其他冲突事务需要等待。

**适合**

例如：

```text
冲突概率高
critical section 短
必须基于最新数据立即更新
```

**代价**

```text
blocking
lock wait
deadlock
lower concurrency
```

### 4.22 [P0] 乐观锁和悲观锁怎么选？

**乐观锁**

特点：

```text
不长期阻塞
冲突时失败 / retry
```

适合：

```text
冲突较少
读多写少
```

**悲观锁**

特点：

```text
先拿锁
再操作
```

适合：

```text
冲突频繁
操作很短
失败重算成本高
```

但不要机械套：

```text
读多写少一定 OCC
写多一定 row lock
```

还要看：

* retry 成本；
* side effect 是否可重做；
* transaction duration；
* hot key；
* contention。

### 4.23 [P1] 什么是 Lost Update？

初始：

```text
balance = 100
```

A 读取：

```text
100
```

B 也读取：

```text
100
```

A：

```text
+20
→ write 120
```

B：

```text
-10
→ write 90
```

最终：

```text
90
```

A 的更新：

```text
丢失
```

正确结果应该是：

```text
110
```

这就是：

```text
Lost Update
```

### 4.24 [P1] 怎么避免 Lost Update？

根据语义不同可以有多种方法。

**Atomic SQL**

如果只是增减：

```sql
UPDATE account
SET balance = balance + 20
WHERE id = ?;
```

不必：

```text
SELECT
→ application compute
→ UPDATE absolute value
```

**Optimistic Lock**

```sql
UPDATE ...
WHERE version = old_version;
```

检测 stale write。

**Pessimistic Lock**

```sql
SELECT ... FOR UPDATE
```

然后在锁保护下计算与写入。

**Serializable Transaction**

用更强隔离控制并发。 实际选择取决于：

```text
业务 invariant
冲突率
吞吐
retry 成本
```

### 4.25 [P1] 什么是 MVCC？

MVCC：

> Multi-Version Concurrency Control。

核心思想是：

> 数据不是只有“现在这个值”，数据库可以维护多个版本，让 reader 在很多场景下读取合适的历史版本，而不必总是和 writer 互相阻塞。

概念上：

```text
Row version 1
    ↓
Row version 2
    ↓
Row version 3
```

不同事务根据自己的可见性规则读取不同版本。

**为什么有用？**

如果所有读写都需要：

```text
读锁
写锁
```

大量 reader 和 writer 会互相阻塞。 MVCC 让很多普通读取可以：

```text
non-blocking consistent read
```

提高并发性。

### 4.26 [P1] MVCC 为什么不等于“没有锁”？

MVCC 主要帮助：

```text
consistent read
```

但更新仍然要协调。 例如：

```sql
UPDATE account ...
```

不能两个事务随意同时修改同一行而不处理冲突。 此外：

```sql
SELECT ... FOR UPDATE
```

本身就是 locking read。 所以：

```text
MVCC
+
locks
```

通常共同存在。 不是二选一。

### 4.27 [P1] 什么是 Read View？

可以把 Read View 理解成：

> 当前事务判断哪些版本对自己可见的一组快照信息。

当读取一行时，数据库需要判断：

```text
这个版本是我事务开始前已经提交的吗？
来自仍然活跃的事务吗？
是未来版本吗？
```

再决定：

```text
当前事务能不能看到它
```

**为什么它重要？**

它是理解：

```text
Repeatable Read
MVCC snapshot
```

的关键。 不是说数据库真的把整张表：

```text
复制一份
```

给每个事务。 而是通过：

```text
版本信息
+
undo history
+
visibility rules
```

构造一致读取。

### 4.28 [P1] Undo Log 是什么？

Undo Log 可以理解为记录：

> 修改前的数据版本信息。

用途包括：

**Rollback**

事务失败：

```text
恢复修改前状态
```

**MVCC**

帮助构造旧版本：

```text
当前行
→ undo
→ earlier version
```

所以：

```text
undo log
```

不仅仅是：

> “事务回滚日志”。

它还和多版本读取密切相关。

### 4.29 [P1] Redo Log 是什么？

Redo Log 记录：

> 已经发生的数据页修改，可以如何重做。

核心服务于：

```text
Durability
```

例如：

```text
事务已 commit
```

但脏页还没完全刷入最终数据文件，机器突然断电。 恢复时：

```text
redo log
```

可以帮助恢复已提交修改。

**一个直觉**

```text
Undo
→ 回到过去

Redo
→ 重做已提交变化
```

虽然实现细节远比这复杂，但这个方向不会错。

### 4.30 [P1] Binlog 是什么？

Binlog 是 MySQL Server 层的逻辑日志。 常见用途：

```text
replication
point-in-time recovery
CDC
audit-like downstream consumption
```

**Redo 与 Binlog 不要混**

可以粗略区分：

```text
Redo
→ InnoDB storage engine durability

Binlog
→ MySQL server logical change log
```

它们用途和层次不同。

### 4.31 [P2] 为什么 Commit 需要协调 Redo 和 Binlog？

如果：

```text
redo 认为提交成功
```

但：

```text
binlog 没记录
```

可能造成：

```text
主库状态
≠
基于 binlog 的复制状态
```

反过来也存在问题。 因此 MySQL 需要协调两类日志，使：

```text
storage state
```

和：

```text
replication/logical history
```

尽量一致。 面试中理解到：

> **数据库内部也存在多份持久化事实需要原子协调。**

通常已经比只背：

```text
两阶段提交
```

更重要。

### 4.32 [P1] 什么是 Current Read 和 Snapshot Read？

在 MVCC 语境下可以粗略理解：

**Snapshot Read**

普通：

```sql
SELECT ...
```

很多情况下读取事务自己的可见快照。

**Current Read**

例如：

```sql
SELECT ... FOR UPDATE;
```

或者：

```sql
UPDATE
DELETE
```

需要基于当前最新可操作版本进行，并涉及锁。 所以不要认为：

```text
Repeatable Read
```

意味着事务内所有 SQL 都永远只看最初 snapshot。 不同类型读取语义不同。

### 4.33 [P1] `SELECT ... FOR UPDATE` 到底在解决什么？

假设：

```text
库存 = 1
```

两个事务同时：

```text
SELECT stock
```

都看到：

```text
1
```

然后都扣：

```text
stock = 0
```

如果业务要求：

```text
只有一个购买者成功
```

可以在事务中：

```sql
SELECT stock
FROM item
WHERE id = ?
FOR UPDATE;
```

让冲突事务等待。 然后：

```text
检查
→ 修改
→ commit
```

把：

```text
check + act
```

放进同一个锁保护事务。

### 4.34 [P1] `FOR UPDATE` 会锁什么？

不是永远只锁：

```text
查询出来那一行
```

实际锁范围和：

```text
索引
查询条件
隔离级别
执行计划
```

有关。 例如没有合适索引时，可能扫描和锁定更大的范围。 所以：

> “我加了 FOR UPDATE，所以只锁目标 row。”

这个回答过于绝对。 生产中应结合：

```text
EXPLAIN
索引设计
实际 lock behavior
```

分析。

### 4.35 [P1] 什么是 Gap Lock / Next-Key Lock？

在 InnoDB Repeatable Read 等场景下，为了控制范围查询的并发现象，数据库不仅可能锁：

```text
已有记录
```

还可能锁：

```text
记录之间的范围
```

概念上：

```text
10      20      30
 |-------|-------|

某些范围被锁住
```

**为什么？**

如果事务正在保护：

```text
10 < id < 20
```

只锁现有行仍可能允许另一个事务插入：

```text
id = 15
```

导致结果集合发生变化。 Range/gap locking 用来处理这类问题。 面试不需要死背所有 lock mode，但要理解：

> **范围查询的并发控制可能锁“区间”，而不只是已存在的行。**

### 4.36 [P1] 什么是 Deadlock？

事务 A：

```text
lock row 1
wait row 2
```

事务 B：

```text
lock row 2
wait row 1
```

形成：

```text
A waits B
B waits A
```

谁也不能继续。 数据库会检测这种循环并让其中一个事务失败/回滚，以打破 deadlock。

### 4.37 [P1] 怎么降低 Deadlock？

常见方法：

**固定锁顺序**

例如始终：

```text
按 account_id 从小到大加锁
```

避免：

```text
A 锁 1 → 2
B 锁 2 → 1
```

**缩短事务**

不要：

```text
BEGIN
→ remote HTTP
→ sleep
→ expensive computation
→ COMMIT
```

让锁持有很久。

**使用合适索引**

减少不必要的扫描和锁范围。

**控制 batch size**

一次 transaction 更新几万行，会扩大锁集合。

**对 deadlock 做安全 retry**

数据库 deadlock victim：

```text
整个 transaction rollback
```

如果业务操作可重试，可以重新执行事务。 但如果事务外已经产生 side effect，就不能只重跑数据库代码。

### 4.38 [P1] 为什么长事务危险？

长事务会：

```text
持锁时间更长
undo history 更长
资源占用更多
冲突概率更高
```

还可能阻碍：

```text
purge
```

导致历史版本积累。 所以不要：

```text
BEGIN
→ 用户交互
→ RPC
→ 大量计算
→ 外部支付
→ COMMIT
```

把不可控慢操作塞进数据库事务。

### 4.39 [P1] 为什么事务里调用远程服务通常危险？

例如：

```text
BEGIN
↓
锁住订单
↓
调用 Payment API
↓
等待 5 秒
↓
UPDATE
↓
COMMIT
```

如果 Payment 很慢：

```text
DB lock
```

也跟着持有 5 秒。 导致：

```text
contention
deadlock probability
connection occupancy
latency
```

增加。 更严重的是：

> 数据库事务无法自动 rollback 已经发生的远程 payment。

所以把 remote side effect 放在 DB transaction 里面，并不会获得真正的跨系统原子性。

### 4.40 [P2] 为什么数据库事务不能包住 Remote Side Effect？

代码：

```text
BEGIN DB TX
↓
call remote payment
↓
UPDATE local DB
↓
COMMIT
```

如果 remote payment 成功：

```text
T1 remote side effect committed
```

然后本地：

```text
T2 DB commit failed
```

rollback 只能撤销：

```text
local DB
```

不能穿过网络撤销：

```text
remote payment
```

所以：

```text
local ACID transaction
≠
distributed transaction
```

这是分布式后端最关键的边界之一。

### 4.41 [P1] 乐观锁为什么特别适合 Agent / Workflow State？

假设 Episode：

```text
state = DISCOVERING
version = 5
```

两个 worker 同时读取。 A：

```text
准备推进到 SELECTING
```

B：

```text
也准备推进
```

如果直接：

```sql
UPDATE episode
SET state = ...
WHERE id = ?;
```

后提交者可能覆盖前者。 加入：

```sql
WHERE version = 5
```

后：

```text
A:
5 → 6 success

B:
still expects 5
→ affected rows = 0
```

B 知道自己的 observation 已过期。 这和前面 Agent 章节的：

```text
stale proposal
```

实际上是同一个问题在数据库层的落地。

### 4.42 [P1] 为什么 OCC 成功后仍可能出现业务重复？

OCC 只保护：

```text
某条数据库状态的并发写
```

假设：

```text
A:
call payment
→ success
→ OCC update

B:
call payment
→ success
→ OCC update fails
```

最终 DB 只有 A 成功推进。 但远程：

```text
payment
```

已经执行：

```text
两次
```

所以：

```text
optimistic locking
```

不能替代：

```text
side-effect idempotency
```

这是非常重要的面试边界。

### 4.43 [P1] 为什么 UNIQUE Constraint 也不能解决所有幂等？

假设数据库：

```text
UNIQUE(economic_key)
```

两个请求：

```text
A
B
```

确实只能成功插入一个 PaymentIntent。 但如果代码顺序是：

```text
call remote payment
↓
INSERT PaymentIntent
```

那么：

```text
A remote success
B remote success
```

之后数据库才发生 unique conflict。 外部副作用仍然重复。 所以正确顺序通常需要先建立：

```text
durable intent / identity
```

再进行 remote side effect。

### 4.44 [P2] 什么是 Intent Record？

Intent Record 是：

> 在执行外部副作用之前，先持久化“我要执行哪个逻辑操作”。

例如：

```text
PaymentIntent
```

包含：

```text
intent_id
economic_key
amount
currency
target
state
```

先：

```text
DB commit intent
```

然后：

```text
execute remote side effect
```

这样 crash 后至少知道：

```text
系统原本打算做什么
```

而不是只剩：

```text
请求超时了，不知道有没有执行
```

### 4.45 [P2] Intent Record 解决所有问题了吗？

没有。 假设：

```text
T0 create intent
T1 commit
T2 call remote
T3 remote success
T4 process crash
T5 local state still SUBMITTING
```

恢复后：

```text
remote side effect
```

已经发生，但本地不知道。 因此还需要：

```text
UNKNOWN
reconciliation
remote idempotency identity
```

Intent 主要解决：

```text
durable command identity
```

不是完整 distributed transaction。

### 4.46 [P2] 什么是 Hot Row？

如果大量请求都更新同一行：

```text
counter row
wallet row
global quota row
```

无论数据库整体有多强，这一行都可能形成串行瓶颈。 例如：

```text
10000 requests
       ↓
same row lock
       ↓
serialized updates
```

这叫：

```text
hot row
```

**常见现象**

```text
lock wait ↑
P99 ↑
deadlock ↑
throughput plateau
```

### 4.47 [P2] Hot Row 怎么处理？

取决于业务 invariant。

**Sharding Counter**

一个总 counter：

```text
counter
```

拆成：

```text
counter_0
counter_1
...
counter_15
```

读取时 aggregate。

**Append Event**

不要反复更新：

```text
balance = balance + x
```

而是 append：

```text
delta event
```

后续聚合。

**Queue / Single Writer**

把同一 key 更新串行化到：

```text
one owner / partition
```

**Relax Real-time Consistency**

如果业务允许：

```text
eventually consistent counter
```

可以提高吞吐。

**但不能为了性能破坏 invariant**

例如支付余额需要严格保证：

```text
不能超扣
```

那不能随便把强一致约束变成异步聚合。

### 4.48 [P2] 为什么“数据库扛不住就分库分表”是过早结论？

性能问题可能来自：

```text
missing index
N+1 query
large transaction
hot row
bad query
connection pool
lock contention
too many round trips
```

分库分表会引入：

```text
routing
cross-shard query
cross-shard transaction
rebalancing
global ID
operational complexity
```

所以正确顺序通常是：

```text
identify bottleneck
→ fix local design
→ scale vertically/read replicas
→ only then consider sharding
```

而不是：

```text
QPS 高
→ 分库分表
```

### 4.49 [P1] 什么是 N+1 Query？

例如查询：

```text
100 orders
```

先：

```sql
SELECT * FROM orders;
```

然后每个 order：

```sql
SELECT * FROM user WHERE id = ?;
```

总共：

```text
1 + 100 queries
```

这就是 N+1。

**为什么危险？**

单次 SQL 可能都：

```text
1ms
```

但 101 次网络 round trip：

```text
总延迟
连接占用
DB QPS
```

都会上升。

**常见解决**

```text
JOIN
batch query
IN (...)
preload
data loader
```

但也不是所有关系都应该巨型 JOIN。

### 4.50 [P1] 什么是 Connection Pool？

和 RPC 一样，数据库连接也很昂贵。 应用通常维护：

```text
DB connection pool
```

而不是每次 query：

```text
connect
authenticate
query
close
```

**常见参数**

```text
max open
max idle
connection lifetime
```

**Pool 太小**

```text
requests wait connection
```

**Pool 太大**

多个实例：

```text
100 pods
×
500 connections
=
50000 DB connections
```

数据库可能直接被压垮。 所以：

```text
pool size
```

是整体 capacity planning。

### 4.51 [P1] 为什么数据库慢不一定是 SQL 慢？

用户看到：

```text
DB operation = 2s
```

实际可能：

```text
1.8s waiting connection
+
20ms waiting lock
+
180ms query
```

如果只看：

```text
query execution
```

可能发现：

```text
180ms
```

然后误判。 所以生产排障应区分：

```text
pool wait
lock wait
execution
network
result scan
```

### 4.52 [P1] 什么是 Transaction Boundary？

Transaction Boundary 表示：

> 哪些操作必须作为一个原子状态变化一起提交。

例如：

```text
create order
+
reserve local inventory
```

如果它们必须永远同时存在：

```text
same local transaction
```

可能合理。 但：

```text
create order
+
send email
```

不一定值得放在同一个事务语义中。

**事务边界应该围绕 Invariant**

而不是围绕：

```text
一个 HTTP request
```

机械展开。 不是每一个：

```text
Handler()
```

都应该：

```text
BEGIN at start
COMMIT at end
```

### 4.53 [P2] 什么是 Dual Write Problem？

系统需要同时写：

```text
Database
+
Message Queue
```

例如：

```text
UPDATE order = PAID
publish OrderPaid
```

如果顺序：

```text
DB commit
↓
process crash
↓
MQ publish 没发生
```

结果：

```text
DB = PAID
MQ 没事件
```

反过来：

```text
publish MQ
↓
DB commit failed
```

结果：

```text
下游收到 PAID
DB 实际没 PAID
```

这就是：

```text
dual-write problem
```

### 4.54 [P2] 为什么简单调整写入顺序解决不了 Dual Write？

**DB First**

```text
DB commit
→ MQ
```

crash window：

```text
commit 后
publish 前
```

**MQ First**

```text
MQ publish
→ DB commit
```

crash window：

```text
publish 后
commit 前
```

只是把不一致方向换了。 真正问题是：

> 两个独立系统之间没有同一个本地 ACID transaction。

### 4.55 [P2] Transactional Outbox 是什么？

Transactional Outbox 的思路：

> 把业务状态变化和“待发送消息”写入同一个数据库事务。

例如：

```sql
BEGIN;

UPDATE orders
SET status = 'PAID'
WHERE id = ?;

INSERT INTO outbox (
    event_id,
    event_type,
    payload
) VALUES (...);

COMMIT;
```

这时：

```text
Order = PAID
```

和：

```text
Outbox event exists
```

要么同时存在，要么都不存在。 之后独立 publisher：

```text
read outbox
→ publish MQ
→ mark published
```

### 4.56 [P2] Outbox 能保证消息只发一次吗？

不能简单这么说。 可能：

```text
publisher sends message
↓
broker receives
↓
publisher crashes
↓
outbox still looks unsent
↓
restart
↓
send again
```

所以可能：

```text
duplicate publish
```

因此下游仍然需要：

```text
event identity
+
idempotent consumer
```

Outbox 主要解决的是：

```text
DB commit
和
消息最终能够被发现并发送
```

之间的可靠性问题。 不是自动获得物理：

```text
exactly once delivery
```

### 4.57 [P2] Outbox 为什么通常和 At-least-once 配套？

因为系统选择：

> 宁愿同一 event 重复发送，也不要已经 commit 的业务事件永久丢失。

即：

```text
possibly duplicate
```

通常比：

```text
possibly missing forever
```

更容易恢复。 所以形成：

```text
Outbox
→ at-least-once publication
→ consumer idempotency
```

这也是后面 MQ 章节的核心。

### 4.58 [P2] 什么是 CDC？

CDC：

> Change Data Capture。

从数据库变化日志中捕获数据变更，并传给下游。 例如：

```text
MySQL Binlog
    ↓
CDC Connector
    ↓
Kafka / MQ
    ↓
Downstream
```

与应用自己：

```text
publish event
```

不同，CDC 从数据库事实变化中读取。

### 4.59 [P2] CDC 和 Outbox 有什么关系？

两者可以结合。 应用事务：

```text
Business Table
+
Outbox Table
```

都写 DB。 CDC 监听：

```text
Outbox Table changes
```

再发布到 MQ。 这样应用进程甚至不需要自己不断轮询 outbox。 概念链：

```text
Local DB Transaction
        ↓
Outbox Row
        ↓
Binlog
        ↓
CDC
        ↓
MQ
```

### 4.60 [P2] 为什么不直接 CDC Business Table？

可以，但有 trade-off。 直接 CDC：

```text
orders.status
PENDING → PAID
```

下游必须理解：

```text
数据库表结构
字段变化
业务语义
```

这会让：

```text
storage schema
```

变成：

```text
integration contract
```

而 Outbox 可以明确写：

```text
event_type = order.paid
schema_version = 1
payload = ...
```

让：

```text
domain event
```

与：

```text
database physical schema
```

解耦。

### 4.61 [P2] Outbox 和 Event Sourcing 是一回事吗？

不是。

**Outbox**

主要目标：

```text
可靠传播已经发生的业务变化
```

系统主状态仍可能在：

```text
orders
payments
users
```

普通状态表中。

**Event Sourcing**

核心状态本身由：

```text
事件序列
```

推导。 例如：

```text
AccountOpened
DepositAdded
PaymentMade
Refunded
```

当前状态：

```text
replay events
→ derive state
```

所以：

```text
Outbox
≠
Event Sourcing
```

### 4.62 [P2] 什么是 Projection？

Projection 是从一组 authoritative facts 构建出来的：

```text
便于读取的派生视图
```

例如：

```text
Ledger Events
    ↓
Balance Projection
```

或者：

```text
Order Events
    ↓
Order Summary Table
```

Projection 可以：

```text
rebuild
```

如果 authoritative event/fact 还在。

**为什么有用？**

写模型可能适合：

```text
correctness
audit
append-only
```

读模型更适合：

```text
fast query
aggregation
UI
```

不一定需要用同一个数据结构同时优化两者。

### 4.63 [P1] 为什么 Projection 不应该成为唯一事实源？

如果 Projection 本来是：

```text
derived state
```

但其他组件开始直接修改：

```text
projection.balance = 100
```

它就不再能可靠：

```text
rebuild from source facts
```

所以应该明确：

```text
source of truth
```

和：

```text
materialized view / projection
```

的边界。

### 4.64 [P1] 什么是 Upsert？

Upsert 表达：

```text
不存在则 INSERT
存在则 UPDATE
```

不同数据库语法不同。 适合一些：

```text
idempotent materialization
projection update
cache-like table
```

场景。 但：

```text
UPSERT
```

不是自动业务幂等。 如果：

```text
重复请求应该返回第一次结果
```

还需要明确：

```text
business identity
request fingerprint
stored result
```

### 4.65 [P1] 为什么金额字段一般不用 FLOAT / DOUBLE？

因为二进制浮点不能精确表示很多十进制小数。 例如：

```text
0.1
```

在二进制浮点中通常只是近似值。 金融金额通常使用：

```text
integer minor units
```

例如：

```text
$12.34
→ 1234 cents
```

或者：

```text
DECIMAL
```

**Integer Minor Unit 优点**

```text
精确
比较简单
跨语言稳定
```

但必须明确：

```text
currency decimals
```

不能假设所有资产：

```text
×100
```

即可。

### 4.66 [P1] 为什么时间字段也会有数据库坑？

常见问题：

```text
时区
精度
UTC / local time
timestamp / datetime 语义
```

服务端系统通常倾向存储：

```text
UTC
```

展示时再转换本地时区。 此外：

```text
CreatedAt
OccurredAt
ConfirmedAt
```

语义也不同。 不要把：

```text
数据库写入时间
```

当成：

```text
业务事件真实发生时间
```

如果事件来自外部系统，两者可能不一样。

### 4.67 [P1] 为什么 Soft Delete 会影响 Unique Constraint？

假设：

```text
merchant_name UNIQUE
```

然后 soft delete：

```text
deleted_at != NULL
```

逻辑上 merchant 已删除。 现在想重新创建同名 merchant：

```text
UNIQUE
```

仍然可能冲突，因为旧 row 物理上还在。 所以 soft delete 会影响：

```text
uniqueness
index
query condition
storage growth
```

需要提前设计，而不是只加：

```text
deleted_at
```

字段。

### 4.68 [P1] 为什么 ORM 不能替代 SQL 基础？

ORM 可以帮助：

```text
mapping
CRUD
transaction API
migration
```

但它仍然会生成 SQL。 如果不知道：

```text
索引
JOIN
N+1
transaction
lock
query plan
```

很容易写出：

```text
代码看起来很简单
数据库非常痛苦
```

所以面试里即使用 GORM，也应该能回答：

> 这段 ORM 最终大概生成什么 SQL，以及数据库为什么这样执行。

### 4.69 [P1] ORM Transaction 常见坑是什么？

例如：

```go
db.Transaction(func(tx *gorm.DB) error {
    ...
})
```

内部操作却意外使用：

```go
globalDB
```

而不是：

```go
tx
```

那么部分 SQL 可能根本不在同一 transaction。 概念上：

```text
tx.UpdateA()
globalDB.UpdateB()
```

看起来都在一个函数里：

```text
实际事务边界不同
```

所以 ORM 语法不能替代对：

```text
connection
transaction handle
commit boundary
```

的理解。

### 4.70 [P2] 为什么应用层 Version 和数据库 MVCC Version 不是一回事？

数据库内部 MVCC 有自己的：

```text
transaction/version visibility
```

应用可能另外维护：

```text
version = 7
```

用于：

```text
optimistic concurrency control
```

两者目标不同。 数据库 MVCC：

```text
帮助多个 transaction 并发读写
```

业务 version：

```text
表达 aggregate 的业务更新序列
检查 stale command
```

所以不能说：

> MySQL 已经有 MVCC，因此不用应用 version。

它们不是同一个层次。

### 4.71 [P2] 为什么 Version 还能帮助 Agent Proposal 校验？

假设模型 Proposal 基于：

```text
episode.version = 12
```

执行前 Runtime 读取：

```text
episode.version = 13
```

那么 Proposal：

```text
已经 stale
```

这时可以：

```text
reject
→ observe new state
→ re-decide
```

因此业务 version 不只保护 DB update。 它还可以成为：

```text
decision provenance
```

的一部分。 这是 Agent Runtime 和数据库并发控制连接得非常自然的地方。

### 4.72 [P2] Serializable 是否意味着完全没有并发问题？

Serializable 的目标是：

> 并发事务结果等价于某种串行执行顺序。

但它不能解决：

```text
数据库之外的 side effect
```

例如：

```text
Transaction
→ remote API
```

Remote API 不在 MySQL serialization graph 里。 也不能自动解决：

```text
客户端重试造成重复 command
```

所以：

```text
strong DB isolation
```

不等于：

```text
whole distributed system exactly once
```

### 4.73 [P2] 为什么“数据库里只有一条记录”不能证明 Side Effect 只发生一次？

假设：

```text
external payment call A
→ success

external payment call B
→ success
```

然后两个请求都试图：

```sql
INSERT payment
```

数据库 UNIQUE 只允许：

```text
1 row
```

最终查看 DB：

```text
只有一条 payment record
```

但外部系统：

```text
已经支付两次
```

这就是为什么工程验证不能只看：

```text
最终数据库 row count
```

还需要检查：

```text
remote transaction identity
event identity
ledger
side-effect count
```

### 4.74 [P2] 为什么 Audit Log 不等于 Ledger？

Audit Log 通常记录：

```text
谁
什么时候
做了什么
```

方便：

```text
debug
security
compliance
```

Ledger 则是具有明确业务经济语义的事实记录。 例如：

```text
Debit wallet A 100
Credit merchant B 100
```

它应满足自己的 invariant。 不能因为应用日志里写：

```text
payment success
```

就把日志当财务事实源。 这一点会在支付章节继续展开。

### 4.75 MySQL 中最重要的一条并发主线

把前面的概念连起来：

```text
Request A                         Request B

SELECT v=5                        SELECT v=5
    │                                 │
compute                           compute
    │                                 │
UPDATE WHERE version=5           UPDATE WHERE version=5
    │                                 │
success                           affected rows=0
    │                                 │
v=6                               stale write
```

这解决：

```text
local stale write
```

但如果两边在 UPDATE 前都执行：

```text
remote payment
```

那么：

```text
OCC
```

就太晚了。 所以完整设计变成：

```text
durable identity
→ local intent
→ commit
→ remote side effect
→ reconcile result
→ guarded state transition
```

这就是为什么数据库知识最终会自然进入分布式系统知识。

### 4.76 高频错误设计：应用层检查代替 UNIQUE

错误：

```text
SELECT exists
↓
if false
    INSERT
```

认为：

```text
不会重复
```

并发：

```text
A SELECT false
B SELECT false
A INSERT
B INSERT
```

正确：

```text
业务检查
+
DB UNIQUE constraint
```

数据库约束是最后 invariant boundary。

### 4.77 高频错误设计：给所有操作加 `FOR UPDATE`

这样确实可能让：

```text
race bug
```

减少。 但也可能：

```text
吞吐下降
lock wait 上升
deadlock 上升
```

正确问题不是：

> 加不加锁？

而是：

```text
要保护什么 invariant？
冲突概率多高？
critical section 多长？
能否用 atomic SQL？
能否用 OCC？
```

### 4.78 高频错误设计：一个巨大事务最安全

有人会认为：

```text
BEGIN 越早
COMMIT 越晚
```

越安全。 实际：

```text
lock duration ↑
connection occupation ↑
deadlock probability ↑
undo history ↑
```

而且 remote side effect 仍无法 rollback。 所以事务应该：

> **尽可能小，但必须完整覆盖本地 invariant。**

不是：

```text
越大越安全
```

也不是：

```text
越小越好
```

### 4.79 高频错误设计：数据库成功后直接发 MQ

```text
DB COMMIT
↓
MQ publish
```

看起来很正常。 但：

```text
commit
↓
crash
↓
publish 没发生
```

会丢业务事件。 如果事件是：

```text
PaymentConfirmed
```

下游 entitlement 永远收不到。 这就是：

```text
Outbox
```

要解决的 crash window。

### 4.80 高频错误设计：Outbox 就是 Exactly-once

Outbox 仍可能：

```text
publish
↓
crash before mark sent
↓
publish again
```

所以：

```text
duplicate event
```

仍然正常。 真正设计应该接受：

```text
at-least-once
```

再让：

```text
consumer idempotent
```

保证业务效果。

### 4.81 高频错误设计：ORM 帮我处理事务了，所以不用关心 SQL

ORM 不能替你决定：

```text
事务隔离级别
索引
锁范围
N+1
unique constraint
deadlock
hot row
```

代码：

```go
db.Where(...).First(...)
```

最终仍然落到：

```text
SQL
optimizer
storage engine
```

所以：

```text
会 ORM
≠
会数据库
```

### 4.82 高频错误设计：提高隔离级别解决所有并发问题

更强 isolation：

```text
可以解决更多数据库内部 anomaly
```

但不能解决：

```text
外部 API
MQ
payment provider
用户重复请求
```

所以如果问题是：

```text
payment duplicate
```

把 MySQL 从：

```text
READ COMMITTED
→ SERIALIZABLE
```

未必解决根因。 先找：

```text
invariant 究竟跨了哪些系统
```

### 4.83 本章高频对比

| 概念 A                | 概念 B                    | 核心区别                          |
| ------------------- | ----------------------- | ----------------------------- |
| Transaction         | Request                 | 数据库原子边界 vs 网络调用边界             |
| ACID Consistency    | CAP Consistency         | 数据 invariant vs 分布式读写一致性      |
| Dirty Read          | Non-repeatable Read     | 读未提交数据 vs 同一行重复读变化            |
| Non-repeatable Read | Phantom Read            | 行内容变化 vs 结果集合变化               |
| Primary Index       | Secondary Index         | 聚簇数据定位 vs 辅助查找                |
| Index               | Constraint              | 加速访问 vs 强制 invariant          |
| UNIQUE              | App Check               | 原子唯一约束 vs 易受并发影响              |
| Snapshot Read       | Current Read            | MVCC 可见版本 vs 当前可锁定版本          |
| MVCC                | Lock                    | 多版本读并发 vs 冲突协调                |
| Optimistic Lock     | Pessimistic Lock        | 提交时检测冲突 vs 先锁住资源              |
| OCC Version         | MVCC Version            | 业务 stale-write 检测 vs DB 内部可见性 |
| Undo Log            | Redo Log                | 回滚/旧版本 vs 崩溃恢复重做              |
| Redo Log            | Binlog                  | 存储引擎恢复 vs Server 层逻辑日志        |
| DB Transaction      | Distributed Transaction | 单数据库原子性 vs 跨系统原子协调            |
| Retry Transaction   | Retry Side Effect       | 本地重执行 vs 外部可能重复               |
| Intent              | Result                  | 要做什么 vs 已发生什么                 |
| Outbox              | MQ                      | 本地可靠待发送记录 vs 消息传输系统           |
| Outbox              | Event Sourcing          | 可靠传播 vs 事件作为主状态               |
| CDC                 | Application Event       | 捕获 DB 变化 vs 显式业务事件            |
| Projection          | Source of Truth         | 派生读模型 vs 权威事实                 |
| Audit Log           | Ledger                  | 操作记录 vs 经济事实记录                |

### 4.84 面试前一分钟速记

```text
事务解决本地数据库原子性，
不是整个分布式系统原子性。

ACID：
Atomicity
Consistency
Isolation
Durability

InnoDB 常见索引：
B+ Tree。

Primary clustered index：
叶子存完整 row。

Secondary index：
通常存 secondary key + primary key，
必要时回表。

UNIQUE 是 invariant，
应用层先查再写挡不住并发。

MVCC：
让很多 reader 不必和 writer 直接互斥。

MVCC ≠ 没有锁。

FOR UPDATE：
locking read，
但实际锁范围受索引和查询条件影响。

OCC：
UPDATE ... WHERE version=old_version。

affected rows = 0
代表 stale write。

OCC 只能解决本地 state race，
不能保证 remote side effect 只执行一次。

Undo：
rollback + historical version。

Redo：
durability / crash recovery。

Binlog：
replication / CDC / logical changes。

Long transaction：
lock / undo / connection / contention 都更重。

Local DB transaction
不能 rollback remote API。

DB + MQ 是 dual-write problem。

Transactional Outbox：
业务变化 + outbox row
在同一个 DB transaction commit。

Outbox 仍可能重复 publish，
所以 consumer 仍必须 idempotent。

数据库只有一条 row
不代表外部副作用只发生一次。
```

### 4.85 StablePay 映射

本章只保留数据库概念和项目结构之间的映射：

```text
Unique Constraint
→ action / event / economic identity 等唯一性边界

Optimistic Version
→ CommerceEpisode 并发状态推进

Transaction
→ 本地状态与事实的原子提交

Intent
→ PaymentIntent 等 durable command state

Projection
→ 从权威事实派生的查询状态

Ledger
→ 不应被普通日志替代的经济事实

Outbox / CDC
→ 当前可继续演进的 DB → MQ 可靠传播方案
```

其中必须特别记住两个项目追问边界：

```text
Episode OCC
```

解决：

```text
两个 worker 同时推进同一 Episode
```

但不能单独解决：

```text
两个 worker 都已经调用外部 payment
```

同样：

```text
UNIQUE(economic identity)
```

只有在正确的 side-effect ordering 下，才能成为“经济效果不重复”的一部分。 StablePay 当前到底在哪些 repository 使用 version、unique constraint、row lock，哪些链路已有 durable intent，哪些还没有 Outbox，应继续放到 01 的源码级项目追问中，而不在本章复制。

### 4.86 本章学习优先级

### 第一轮：P0

优先背熟：

```text
Transaction
ACID
Isolation Levels
Dirty / Non-repeatable / Phantom Read
Index
B+ Tree
Clustered / Secondary Index
UNIQUE
Optimistic Lock
Pessimistic Lock
```

至少做到：

```text
面试官随便抽一个
30 秒能说完整
```

### 第二轮：P1

重点掌握：

```text
联合索引
最左前缀
覆盖索引
EXPLAIN
Lost Update
MVCC
Read View
Undo / Redo / Binlog
FOR UPDATE
Gap / Next-Key Lock
Deadlock
Long Transaction
DB Connection Pool
ORM Transaction
```

做到能够解释：

```text
一个具体并发 timeline 为什么错
```

### 第三轮：P2

针对高质量后端 / Agent Infra：

```text
Local Transaction vs Remote Side Effect
Intent Record
Hot Row
Dual Write
Transactional Outbox
CDC
Projection
Event Sourcing boundary
OCC vs Side-effect Idempotency
```

最终不要把数据库八股背成：

> “MySQL 用 B+ Tree，InnoDB 支持 MVCC，事务有 ACID，解决并发可以加锁。”

更完整的理解应该是：

> B+ Tree 解决数据如何高效定位；MVCC 和锁解决多个事务如何同时访问数据；UNIQUE、事务、CAS/version 保护本地 invariant；但这些保证都止于数据库边界。一旦一次业务操作还需要调用支付、MQ 或其他远程服务，就重新出现 partial failure 和 unknown outcome，此时必须在本地 ACID 之上继续引入 durable intent、idempotency、Outbox、reconciliation 等分布式机制。

## 5. Redis、Cache 与限流

Redis 面试最容易停留在：

```text id="vv53l2"
Redis 是单线程
所以很快

有 String / Hash / List / Set / ZSet

可以做缓存
分布式锁
限流
```

真正的工程追问通常是：

```
为什么快？
单线程到底指什么？
TTL 怎么过期？
缓存和数据库不一致怎么办？
缓存击穿和雪崩区别是什么？
SET NX 为什么还不够？
锁为什么必须有 token？
锁过期以后旧 owner 还在执行怎么办？
Redlock 解决什么？
为什么还要 fencing token？
限流用 fixed window 还是 token bucket？
Redis 挂了应该 fail-open 还是 fail-closed？
```

这一章按：

```
Redis 本身
   ↓
缓存
   ↓
原子控制状态
   ↓
分布式锁
   ↓
限流
   ↓
一致性
```

展开。

### 5.1 [P0] Redis 为什么快？

不能只回答：

> 因为 Redis 是单线程。

Redis 快是多个因素共同作用。

**内存访问**

大部分数据主要在内存中：

```text id="l5m74t"
memory
```

远快于随机磁盘 IO。

**简单高效的数据结构**

Redis 针对不同结构有专门实现。

**请求处理路径短**

很多操作：

```text id="sg6uap"
GET
SET
INCR
HGET
```

逻辑简单。

**减少锁竞争**

Redis 经典命令执行模型主要串行处理命令，避免大量共享数据结构上的锁协调。

**高效网络模型**

Redis 能通过事件驱动 IO 处理大量连接。 所以正确表述更接近：

```text id="214sae"
Redis 快
=
内存
+
高效数据结构
+
较短执行路径
+
较少共享锁竞争
+
高效网络事件模型
```

而不是单纯：

```text id="r3czhf"
single thread
```

### 5.2 [P1] Redis 真的是“单线程”吗？

“Redis 单线程”通常指：

> 核心命令执行历史上主要由单个线程串行处理。

但 Redis 整个进程并不是只有一个线程。 现代 Redis 还可能有：

```text id="bkhuoy"
network I/O threads
background persistence
lazy free
replication-related work
```

因此：

```text id="rtm2fj"
Redis = one OS thread
```

这个说法不准确。 面试中更稳妥：

> Redis 主要依靠串行命令执行避免复杂锁竞争，但网络和后台任务并不意味着整个 Redis 只有一个线程。

### 5.3 [P0] Redis 常见数据结构有哪些？

至少掌握：

```text id="c1b12m"
String
Hash
List
Set
Sorted Set
```

**String**

常用于：

```text id="37rqzh"
cache value
counter
lock token
nonce marker
```

命令：

```text id="hi49po"
GET
SET
INCR
```

**Hash**

表示：

```text id="ju7mee"
field → value
```

适合较小对象字段。

**List**

有序序列。 可以：

```text id="ppijwn"
LPUSH
RPUSH
LPOP
RPOP
```

适合某些简单队列场景。 但复杂消息系统通常不会只依赖 Redis List 替代专业 MQ。

**Set**

无序唯一集合。 适合：

```text id="tnh8xa"
membership
dedup
intersection
```

**Sorted Set**

每个 member 带：

```text id="4rljh2"
score
```

按 score 排序。 适合：

```text id="hnxprj"
leaderboard
time-based window
priority/rank
```

### 5.4 [P0] Redis 和 MySQL 怎么选？

不是：

```text id="1e380t"
Redis 快
MySQL 慢
```

这么简单。

**MySQL 更适合**

```text id="jl96gn"
durable source of truth
transaction
constraint
relational query
strong local invariant
```

**Redis 更适合**

```text id="nafq8p"
cache
short-lived control state
counter
rate limit
ephemeral token
fast lookup
```

如果业务事实：

```text id="g8fzqg"
余额
订单
支付状态
账本
```

只存在 Redis：

```text id="w2ephv"
Redis 丢数据
→ authoritative fact 丢失
```

风险很高。 所以常见：

```text id="nrv8pf"
MySQL
→ authoritative durable state

Redis
→ acceleration / ephemeral coordination
```

### 5.5 [P0] TTL 是什么？

TTL：

> Time To Live。

表示 key 在一定时间后自动过期。 例如：

```text id="ms4rf8"
nonce
→ 5 minutes

session
→ 30 minutes

cache
→ 10 minutes
```

典型：

```text id="cmr928"
SET key value EX 300
```

**TTL 适合什么？**

当业务语义本身就是：

```text id="p7xa67"
temporary
```

例如：

```text id="2ne9bb"
replay window
verification token
cache
rate-limit bucket
```

### 5.6 [P1] Redis Key 是怎么过期的？

Redis 不会只依赖一种策略。 通常可以理解为：

**Lazy Expiration**

访问 key 时发现：

```text id="x8v7l4"
expired
```

再删除。

**Active Expiration**

Redis 后台主动采样一些带 TTL 的 key，清理已经过期的数据。 如果只有 lazy：

```text id="go0ohk"
永远不访问的过期 key
```

可能一直占内存。 如果每个 key 到期瞬间都精确启动 timer：

```text id="nz81fz"
大量 timer overhead
```

也不划算。 所以会组合处理。

### 5.7 [P0] 什么是 Cache Aside？

Cache Aside 是常见缓存模式。 读取：

```text id="a2e85w"
1. read cache
2. miss
3. read DB
4. write cache
5. return
```

即：

```text id="q5597t"
Client
 ↓
Cache
 ↓ miss
Database
 ↓
Cache fill
```

写入常见：

```text id="l8mmvf"
update DB
→ invalidate cache
```

而不是同时精确维护两份状态。

### 5.8 [P1] 为什么 Cache Aside 常选择“更新 DB 后删 Cache”？

假设：

```text id="cjkfmd"
DB = authoritative
Cache = derived
```

更新业务事实：

```text id="04kvew"
DB 100 → 200
```

然后：

```text id="28ul1d"
delete cache
```

下一次读：

```text id="ojqarh"
cache miss
→ read 200
→ refill
```

这样避免应用必须：

```text id="2bqktt"
同时精确 update DB + cache
```

两个系统。

**为什么不直接 Update Cache？**

可以，但更容易形成：

```text id="3vq9bt"
DB write success
Cache write failed
```

或：

```text id="f28u0g"
Cache success
DB failed
```

双写一致性问题。

### 5.9 [P1] “先删 Cache 再更新 DB”有什么问题？

初始：

```text id="hhnpoc"
DB = old
Cache = old
```

Writer：

```text id="g5cesm"
delete cache
```

此时 Reader：

```text id="sxy69u"
cache miss
→ read DB old
→ write old cache
```

然后 Writer：

```text id="te4ikb"
update DB new
```

最终：

```text id="ylw2ql"
DB = new
Cache = old
```

可能一直 stale 到 TTL。 因此：

```text id="b1z7rc"
update DB
→ invalidate cache
```

通常更自然。 但这也不是绝对无 race，后面继续讲。

### 5.10 [P1] “更新 DB 再删 Cache”就完全一致了吗？

也不是。 例如：

```text id="14lus6"
T0 Reader cache miss
T1 Reader reads old DB
T2 Writer updates DB new
T3 Writer deletes cache
T4 Reader writes old value into cache
```

最终：

```text id="t8a1fl"
DB = new
Cache = old
```

这类窗口虽然可能更窄，但仍存在。 所以 Cache Aside 一般提供的是：

```text id="h26iyl"
eventual cache consistency
```

不是严格强一致。

**如果业务必须强一致？**

可能：

* 不用 cache；
* cache 只做不影响 correctness 的加速；
* versioning；
* write-through；
* CDC invalidation；
* read from source of truth；

具体按业务要求设计。

### 5.11 [P0] 什么是缓存穿透？

Cache Penetration：

> 大量请求查询根本不存在的数据。

例如：

```text id="6kcfel"
user_id = random-nonexistent
```

每次：

```text id="hl2nh3"
cache miss
→ DB miss
```

缓存完全挡不住。

**常见解决**

**Cache Null**

不存在也缓存短 TTL：

```text id="o1wqdq"
user:xxx → NULL
```

**Bloom Filter**

先判断：

```text id="ja030b"
这个 key 是否可能存在？
```

明显不存在：

```text id="ua5k8l"
直接拒绝
```

**Request Validation**

非法 key 不进入数据库。

### 5.12 [P1] Bloom Filter 是什么？

Bloom Filter 是概率数据结构。 支持回答：

```text id="mj5cnq"
一个元素是否可能存在？
```

结果：

```text id="503xyd"
definitely not present

or

possibly present
```

可以有：

```text id="oi1tsm"
false positive
```

但正常设计下不会有：

```text id="p3uw1v"
false negative
```

因此适合挡：

```text id="b7fjsx"
明显不存在 key
```

**为什么不能单独作为最终存在性判断？**

因为：

```text id="ldqbsc"
possibly present
```

不代表真正存在。 还必须查真实数据源。

### 5.13 [P0] 什么是缓存击穿？

Cache Breakdown / Hot Key Expiry：

> 一个非常热门的 key 突然过期，大量请求同时打到数据库。

例如：

```text id="qd1r3z"
热门商品
cache expires
```

瞬间：

```text id="d9h0bj"
10000 requests
→ cache miss
→ 10000 DB queries
```

这就是：

```text id="95nfwu"
击穿
```

### 5.14 [P1] 怎么处理缓存击穿？

**Singleflight / Mutex Rebuild**

同一个 key：

```text id="6rkclg"
只有一个请求重建缓存
```

其他：

```text id="v9q1hw"
等待
```

概念：

```text id="s3puw6"
10000 misses
    ↓
one loader
    ↓
DB
    ↓
cache fill
```

**Logical Expiration**

缓存里保留旧值和：

```text id="etb6up"
logical_expire_at
```

发现过期：

```text id="nlt97n"
某个 worker 异步刷新
```

其他 reader 仍可短暂读旧值。 适合：

```text id="ma3gij"
允许短暂 stale
```

的场景。

**Hot Key Never Hard-expire**

使用主动刷新。 但这增加：

```text id="oncsdr"
refresh system complexity
```

### 5.15 [P0] 什么是缓存雪崩？

Cache Avalanche：

> 大量缓存 key 在同一时间失效，或 Redis 整体不可用，导致大量流量直接打到数据库。

例如：

```text id="g6mlnf"
100k keys
TTL = exactly 10 minutes
```

同一批写入：

```text id="u3l30j"
10 minutes later
→ mass expiry
```

数据库瞬间被打爆。

### 5.16 [P1] 怎么降低缓存雪崩风险？

**TTL Jitter**

不是全部：

```text id="iw7okg"
600s
```

而是：

```text id="kxmqb9"
600s ± random
```

打散过期时间。

**Multi-level Cache**

例如：

```text id="5thnve"
local cache
+
Redis
```

**Graceful Degradation**

Redis unavailable 时：

```text id="k7y5be"
不是所有请求都直打 DB
```

而是：

* rate limit；
* stale value；
* partial fallback。

**Redis HA**

减少单节点故障。

### 5.17 [P0] 缓存穿透、击穿、雪崩怎么区分？

最简记法：

```text id="rm8wvs"
穿透
→ 查不存在的数据

击穿
→ 一个热点 key 失效

雪崩
→ 大量 key / 整个缓存层同时失效
```

对应：

```text id="gtheum"
Penetration
→ nonexistent keys

Breakdown
→ one hot key

Avalanche
→ mass failure
```

### 5.18 [P0] `SET NX` 是什么？

`NX`：

> only set if key does not exist。

例如：

```text id="dvx8mv"
SET lock:order:123 token NX EX 10
```

只有 key 不存在时成功。 常用于：

```text id="tln1hr"
lock acquisition
nonce claim
one-time state
```

**为什么比：**

```text id="j4p728"
GET
if absent
SET
```

安全？ 因为：

```text id="5fypsf"
check + set
```

必须原子。 否则：

```text id="83f3n3"
A GET absent
B GET absent
A SET
B SET
```

两边都认为成功。

### 5.19 [P1] 为什么 Redis Lock 必须有 TTL？

如果：

```text id="f5m9h3"
SET lock token NX
```

成功后 owner：

```text id="hvr85d"
crash
```

没有执行：

```text id="m30c60"
DEL lock
```

那么锁可能永久存在。 所以通常：

```text id="i676ic"
SET key token NX EX ttl
```

让锁最终自动释放。

**但 TTL 又带来另一个问题**

如果业务操作：

```text id="qffu4h"
执行 20s
```

锁：

```text id="psl2oq"
TTL = 10s
```

第 10 秒：

```text id="0p5wf6"
lock expires
```

另一个 worker 获得锁。 此时：

```text id="ecml99"
old owner
+
new owner
```

可能同时工作。 所以 TTL 只是第一步。

### 5.20 [P1] 为什么 Lock Value 要放唯一 Token？

错误释放：

```text id="2gskz4"
DEL lock
```

假设：

```text id="ehhk1u"
A acquired lock
lock expired
B acquired lock
A finally finishes
A DEL lock
```

A 会误删：

```text id="ochabf"
B 的锁
```

因此 lock value 应记录：

```text id="jb91tb"
owner token
```

例如：

```text id="21gadi"
A token = uuid-a
B token = uuid-b
```

释放必须：

```text id="pzj9rq"
if current value == my token
    delete
```

### 5.21 [P1] 为什么“GET 然后 DEL”仍然不安全？

代码：

```text id="a91978"
GET lock
→ token matches

DEL lock
```

中间有 race：

```text id="4tr40l"
GET = token A

lock expires

B acquires token B

A DEL
```

A 仍删掉 B 的锁。 所以：

```text id="bsiey4"
compare token + delete
```

必须是原子操作。 可以使用：

```text id="hwcyb5"
Lua
```

把检查和删除放在一个 Redis command execution 中。

### 5.22 [P1] Redis Lua 为什么常用于锁和限流？

Redis 单条命令原子，但：

```text id="na7byv"
GET
DEL
```

是两条命令。 Lua 可以把：

```text id="cgde9h"
read
check
modify
```

组合成一个原子 server-side execution。 例如：

```text id="ehhcs1"
if GET(key) == token
then DEL(key)
end
```

避免客户端往返期间产生 race。

**Lua 的代价**

Redis 命令执行是关键共享执行路径。 如果 Lua：

```text id="2b8q90"
执行很久
```

会阻塞其他命令。 所以 Lua 应：

```text id="rywrqx"
short
bounded
deterministic enough
```

### 5.23 [P1] `GETDEL` 为什么有用？

`GETDEL` 原子完成：

```text id="54j4q1"
read value
+
delete key
```

适合一次性消费状态。 例如：

```text id="snw0n4"
one-time execution grant
```

两个 worker 同时：

```text id="uncl1n"
GETDEL
```

只有一个能拿到 value。 另一个得到：

```text id="m89p1e"
missing
```

因此可以实现：

```text id="n7eatv"
consume once
```

语义。

**但注意**

Redis key 被消费一次：

```text id="xywoot"
≠
外部 side effect exactly once
```

如果 worker：

```text id="lbf8b9"
GETDEL success
→ crash before action
```

grant 已经没了，但 action 没执行。 所以它适合：

```text id="67mgb3"
one-shot permission consumption
```

不自动解决 crash recovery。

### 5.24 [P1] Redis `INCR` 为什么常用来做计数器？

`INCR` 是原子操作：

```text id="wo31o6"
counter = counter + 1
```

多个客户端同时操作：

```text id="z2xgq0"
不会产生简单 read-modify-write lost update
```

相比：

```text id="mybgp9"
GET
parse
+1
SET
```

更安全。 常用于：

```text id="djbaoa"
rate counter
attempt counter
sequence
basic metrics
```

### 5.25 [P1] Redis Pipeline 和 Transaction 有什么区别？

**Pipeline**

主要目的是：

```text id="gky1nb"
减少 network round trips
```

一次发送多条命令。 例如：

```text id="nwo84u"
CMD1
CMD2
CMD3
```

一起发送。 但：

```text id="7reai6"
pipeline
```

本身不等于：

```text id="qmh79o"
all-or-nothing transaction
```

**Redis Transaction**

典型：

```text id="t6gi6h"
MULTI
...
EXEC
```

提供一组命令排队后执行。 但 Redis transaction 的语义也不能简单等同于：

```text id="vzceak"
MySQL ACID transaction
```

特别是：

```text id="u5vzl2"
rollback semantics
```

不同。 所以不要把：

```text id="zwu4ar"
pipeline
MULTI/EXEC
Lua
```

混成同一个概念。

### 5.26 [P1] 什么是 CAS 风格的 Redis 更新？

有时需要：

```text id="leus07"
如果值还是 old
才更新为 new
```

这就是 CAS：

```text id="u3z7aa"
compare and swap
```

可以通过：

* `WATCH` + transaction；
* Lua；

实现。 例如：

```text id="p76vzl"
version == 5
→ set version = 6
```

和数据库 OCC 思路很像。

### 5.27 [P0] 什么是 Rate Limiting？

Rate Limiting：

> 限制单位时间内允许多少请求或操作。

例如：

```text id="5jldoc"
100 requests / second / user
```

用途：

```text id="x7aeff"
保护系统
防滥用
公平使用
API quota
成本控制
```

### 5.28 [P0] Fixed Window 是什么？

例如：

```text id="9lv7bc"
每分钟最多 100 次
```

窗口：

```text id="0ik1bv"
12:00:00 - 12:00:59
```

Redis：

```text id="zphruk"
key = rate:user:123:12:00
INCR
EXPIRE
```

**优点**

简单。

**缺点**

窗口边界 burst。 例如：

```text id="fcn95d"
12:00:59
→ 100 requests

12:01:00
→ 100 requests
```

两秒内：

```text id="idwslc"
200
```

却都合法。

### 5.29 [P1] Sliding Window 是什么？

Sliding Window 不固定在：

```text id="ekhnwr"
整分钟
```

而看：

```text id="rb9xmm"
当前时刻往前 60 秒
```

例如：

```text id="60h5n0"
now = 12:01:20
window = 12:00:20 ~ 12:01:20
```

可以用：

```text id="tpqfjk"
Sorted Set
```

按 timestamp 保存请求。

**优点**

比 fixed window 更平滑。

**缺点**

维护每次请求记录成本更高。 高 QPS 下：

```text id="drdgm4"
memory
ZSET operation
cleanup
```

成本更明显。

### 5.30 [P0] Token Bucket 是什么？

Token Bucket：

```text id="bn371s"
bucket
```

按固定速率生成 token。 每个请求消费一个 token。 例如：

```text id="88zaf6"
capacity = 100
refill = 10 tokens/s
```

如果一段时间没有流量：

```text id="9l3l3w"
bucket accumulates tokens
```

允许短时间 burst。

**特点**

控制长期平均速率，同时允许一定突发。

### 5.31 [P1] Leaky Bucket 是什么？

可以理解：

```text id="cmzqbn"
requests enter bucket
```

然后以固定速率：

```text id="c1dyi7"
leak out
```

更强调：

```text id="ad3n5l"
平滑输出速率
```

如果输入过快：

```text id="x5v9zk"
bucket full
→ reject/drop
```

**和 Token Bucket**

```text id="5up2dr"
Token Bucket
→允许积累 token，因此允许 burst

Leaky Bucket
→更强调固定输出速率
```

### 5.32 [P1] Token Bucket 为什么很适合 API Rate Limit？

假设限制：

```text id="rhdi6f"
平均 10 req/s
```

但用户 UI 短时间：

```text id="f89ywz"
一次加载发 5 个请求
```

如果严格：

```text id="rwjahi"
每 100ms 只能 1 个
```

体验很差。 Token Bucket 可以允许：

```text id="zypdpk"
small burst
```

同时保证长期：

```text id="ixqvwe"
refill rate
```

受控。 因此很多 API rate limiter 喜欢这种语义。

### 5.33 [P1] 限流 Key 应该按什么维度？

取决于要保护的 invariant。 可能：

```text id="35dpm1"
IP
user ID
API key
tenant
DID
endpoint
merchant
global service
```

例如只按 IP：

```text id="sqztm0"
NAT 后大量用户共享一个 IP
```

会误伤。 只按 user：

```text id="4dmts3"
攻击者创建大量账号
```

又可能绕过。 生产限流往往：

```text id="fa3idj"
multi-dimensional
```

例如：

```text id="mi6d53"
global
+
tenant
+
user
+
endpoint
```

### 5.34 [P1] Rate Limit 应该放在哪一层？

可以有多层。

**Edge / Gateway**

尽早拦截：

```text id="zp249d"
明显过量流量
```

保护整个后端。

**Service**

保护具体业务资源。 例如：

```text id="b04sjf"
payment create
```

比普通 query 更昂贵。

**Dependency-specific Limit**

例如：

```text id="wyry38"
第三方 API
```

只允许：

```text id="rh5tp8"
50 concurrent
```

所以：

```text id="vvxrvf"
rate limit
```

不是只能存在 Gateway。

### 5.35 [P1] Rate Limit 和 Concurrency Limit 有什么区别？

**Rate Limit**

控制：

```text id="2tr6qg"
单位时间进入多少任务
```

例如：

```text id="m9my1p"
1000 req/s
```

**Concurrency Limit**

控制：

```text id="6bmafg"
同时执行多少任务
```

例如：

```text id="9njqe6"
max 100 in-flight
```

假设请求 latency：

```text id="zlr4fe"
10s
```

即使 rate：

```text id="uj2lv4"
100/s
```

也可能积累：

```text id="rtju2e"
~1000 concurrent
```

所以两者控制不同资源。

### 5.36 [P1] Redis 做 Rate Limit 为什么需要原子操作？

错误：

```text id="zm4ly8"
GET count
if count < limit
    INCR
```

两个请求同时：

```text id="wv4pgy"
count = 99
```

A 看：

```text id="kmqdu0"
99 < 100
```

B 也看：

```text id="clzg26"
99 < 100
```

两者都允许。 最后：

```text id="uw33ec"
101
```

所以：

```text id="ir8wn9"
check + increment
```

需要原子。 可通过：

```text id="9s12uc"
Lua
```

或者适合的数据结构 / 单命令组合。

### 5.37 [P1] Redis 不可用时 Rate Limiter 怎么办？

这就是：

```text id="efx2wg"
fail-open
vs
fail-closed
```

**Fail-open**

Redis 错误：

```text id="o8xm4b"
允许请求继续
```

优点：

```text id="9lgwbk"
availability 高
```

缺点：

```text id="r0jqv9"
限流失效
```

适合某些：

```text id="hb5otq"
非安全关键保护
```

场景。

**Fail-closed**

Redis 错误：

```text id="ud6ps7"
拒绝请求
```

优点：

```text id="5icunx"
保持安全/容量 invariant
```

缺点：

```text id="isykcd"
Redis 故障会扩大成业务不可用
```

### 5.38 [P1] Fail-open / Fail-closed 应该怎么选？

不是 Redis 固定应该哪一种。 要问：

> 这个 Redis state 在保护什么？

例如：

**Marketing API Rate Limit**

Redis 挂了：

```text id="6jzfc5"
临时 fail-open
```

可能可接受。

**Payment Replay Protection**

Redis 挂了：

```text id="yb294d"
直接跳过 nonce check
```

可能破坏：

```text id="jlhyxq"
anti-replay invariant
```

因此更倾向：

```text id="9phgdb"
fail-closed
```

所以策略从：

```text id="3n6z1m"
业务 invariant
```

推导。 不是：

```text id="10jbzm"
缓存都 fail-open
安全都 fail-closed
```

机械套用。

### 5.39 [P2] 什么是 Distributed Lock？

单机：

```text id="dsdlwl"
sync.Mutex
```

只能协调：

```text id="ae84w4"
同一个进程
```

如果：

```text id="ymgow6"
Instance A
Instance B
Instance C
```

都可能操作同一资源，本地 mutex 没用。 Distributed Lock 的目标：

> 多进程/多机器之间协调某个临界资源的 ownership。

Redis 常被用来实现：

```text id="ti86ux"
SET key token NX EX ttl
```

### 5.40 [P2] Redis Lock 最大的问题是什么？

问题不是“SET NX 会不会原子”。 它会。 真正问题是：

> **拿到锁以后，锁的 ownership 能否覆盖整个真实执行期间？**

例如：

```text id="jy6g7l"
A gets lock
TTL 10s
```

A 因 GC pause / network / slow API：

```text id="5h4a1e"
pause 15s
```

10 秒后：

```text id="66x72u"
lock expires
```

B：

```text id="1c9oua"
gets new lock
```

随后 A 恢复：

```text id="2a6jfx"
continues old operation
```

此时：

```text id="mt5tfq"
A
+
B
```

都认为自己可以执行。 即使 Redis 当前只有 B 的锁：

```text id="xczmk9"
old owner A
```

仍然在现实世界做事。

### 5.41 [P2] 什么是 Lock Renewal / Watchdog？

如果业务可能超过 TTL，可以由 owner 周期性续期：

```text id="z69ggn"
lock TTL = 10s

every 3s:
if still my lock
    extend TTL
```

这样长任务不会轻易：

```text id="8e62g2"
lock expire
```

**但 Watchdog 仍不是完美保证**

如果 owner：

```text id="ezyuax"
长时间 stop-the-world
network partition
process suspended
```

无法续期。 锁仍可能过期。 而旧任务恢复后仍可能继续产生 side effect。

所以更严格系统需要：

```text id="agansd"
fencing token
```

### 5.42 [P2] 什么是 Fencing Token？

每次获得 lock 时分配一个单调递增 token：

```text id="s305a4"
A gets token 41
B later gets token 42
```

真正执行资源也检查 token。 例如存储系统收到：

```text id="4jnavn"
write(token=42)
```

后，如果旧 A 恢复：

```text id="8d6s95"
write(token=41)
```

资源端拒绝：

```text id="oxp5p3"
41 < latest 42
```

这样即使旧 owner 继续运行：

```text id="4yv6z7"
也无法提交 stale side effect
```

**为什么它比“锁还在不在”更强？**

因为它在真正：

```text id="vybxpb"
resource commit point
```

校验 ownership generation。 而不是只相信：

```text id="en8tax"
之前某时刻拿过 Redis lock
```

### 5.43 [P2] Fencing Token 能用于所有外部 API 吗？

不能。 前提是目标资源支持：

```text id="qyeeka"
token comparison
```

例如数据库 row：

```text id="dpjl80"
WHERE fencing_token < new_token
```

可以实现。 但第三方 payment API 如果根本不认识：

```text id="xku3ey"
fencing token
```

你无法要求它拒绝旧 owner。 这时必须依赖：

```text id="jpxygq"
remote idempotency key
business identity
reconciliation
```

等其他机制。 所以 fencing 是工具，不是万能分布式锁答案。

### 5.44 [P2] Redlock 是什么？

Redlock 是 Redis 提出的一种分布式锁算法思路：

> 客户端尝试在多个相互独立 Redis 节点上获取同一个锁，并要求获得多数节点成功，在考虑锁有效时间后认为获得锁。

目标是避免：

```text id="9ah79v"
单 Redis 节点
```

成为锁安全性的唯一依据。

**为什么它有争议？**

分布式锁正确性涉及：

```text id="lyj416"
network delay
process pause
clock assumptions
failure model
lease expiry
```

如果业务需要非常强的 correctness：

```text id="qa6f2o"
只证明“多数 Redis 写成功”
```

不一定等价于：

```text id="ptjbq3"
旧 owner 永远不再执行
```

所以很多讨论强调：

> 即使有 lease/Redlock，也应关注真正资源端的 fencing 或业务幂等。

面试里没必要站队说：

```text id="l96pyd"
Redlock 一定正确
```

或者：

```text id="txv66s"
Redlock 完全不能用
```

更好的回答是：

> 要根据 failure model 和需要保护的 invariant 判断；对于高风险副作用，锁本身通常不应该是唯一 correctness mechanism。

### 5.45 [P2] Distributed Lock 和 Idempotency 有什么区别？

Lock：

```text id="qkk6fd"
尽量阻止两个执行者同时进入
```

Idempotency：

```text id="hdqiwh"
即使重复执行到达，也不产生重复业务效果
```

这是两种不同保证。 假设：

```text id="xcu30w"
锁过期
```

导致 A、B 都执行。 如果 remote operation 有：

```text id="r8u4ry"
idempotency key
```

最终仍可能只有一次效果。 反过来：

```text id="l8p66l"
只有 lock
```

但 owner 在成功后 response 丢失：

```text id="vvzyv2"
新请求稍后重新获得 lock
```

仍可能再执行一次。 所以：

```text id="f9jv5b"
Lock
≠
Idempotency
```

### 5.46 [P2] 为什么 Redis Lock 不应该保护长时间远程 Side Effect？

因为：

```text id="lw4vmf"
remote call latency
```

不可控。 锁持有期间：

* TTL 可能过期；
* network partition；
* owner crash；
* remote timeout；
* renewal failure。

所以对于支付之类：

```text id="x8jmye"
external irreversible side effect
```

更可靠的正确性基础通常是：

```text id="wxkj1i"
durable intent
+
economic identity
+
remote idempotency
+
reconciliation
```

Redis lock 最多辅助：

```text id="swszg7"
reduce concurrency
```

而不是唯一保证。

### 5.47 [P1] 什么是 Cache Stampede？

Cache Stampede 比“击穿”更广义：

> 缓存失效后大量请求同时开始昂贵重建工作。

不仅是数据库 query。 也可能：

```text id="bkax9w"
LLM generation
search
large aggregation
remote API
```

如果一个 expensive Agent result 缓存过期：

```text id="mnwlx5"
100 requests
→ 100 LLM calls
```

成本可能非常高。 解决方式仍可以：

```text id="zbd7qb"
singleflight
request coalescing
stale-while-revalidate
```

### 5.48 [P1] 什么是 Singleflight？

Singleflight 的核心：

> 同一 key 同一时刻只执行一次加载，其余请求等待并共享结果。

例如：

```text id="qbr42t"
A miss ─┐
B miss ─┼→ one DB load → shared result
C miss ─┘
```

适合：

```text id="qzpxuk"
hot cache rebuild
metadata load
expensive RPC
```

**注意**

Singleflight 通常解决：

```text id="2zsmyn"
single process
```

内重复工作。 多实例：

```text id="s8vncy"
Instance A
Instance B
```

仍可能各自重建一次。 是否需要跨实例协调，要看重建成本和业务需求。

### 5.49 [P1] 什么是 Stale-While-Revalidate？

允许：

```text id="p12muh"
缓存已经逻辑过期
```

时仍返回旧值。 同时：

```text id="m4o6vb"
background refresh
```

新值。 流程：

```text id="q1lrco"
read stale cache
   ↓
return quickly
   +
one refresh worker
   ↓
update cache
```

适合：

```text id="eslz7d"
推荐
catalog
非强一致配置
页面内容
```

不适合：

```text id="m24gvb"
支付余额
authorization
严格 eligibility
```

因为这些不能随便接受 stale fact。

### 5.50 [P1] 什么是 Cache Versioning？

缓存 key 带版本：

```text id="3moivt"
catalog:v42:item:123
```

新版本：

```text id="3wvfbt"
catalog:v43:item:123
```

这样不会覆盖旧 snapshot。 优点：

```text id="noclh5"
immutable snapshot
easy rollback
cache isolation
```

但需要管理：

```text id="86wax3"
old versions
TTL
current pointer
```

这种设计和后面的 Catalog versioning 很容易结合。

### 5.51 [P1] 什么是 Cache Key Design？

Cache key 应明确：

```text id="wfazgw"
namespace
entity
identity
version
scope
```

例如：

```text id="j46gui"
stablepay:catalog:v42:capability:abc
```

而不是：

```text id="6wmw1w"
abc
```

**为什么 Namespace 重要？**

防止不同模块：

```text id="44ckpu"
同 key collision
```

**为什么 Version 重要？**

schema 或数据语义变化时：

```text id="vxzkk4"
旧 cache
```

不能被新代码误解。

### 5.52 [P1] 什么是 Cache Serialization Version？

Redis 中 value：

```text id="ksgu9a"
JSON / protobuf
```

结构未来会变化。 旧值：

```json id="k8p73d"
{
  "price": "10"
}
```

新代码期待：

```json id="3tg19h"
{
  "amount_minor": 1000,
  "currency": "USD"
}
```

如果 key 不变：

```text id="k91epj"
new code reads old schema
```

可能出错。 因此可以：

```text id="gnm73t"
key namespace version
```

或者 value 中带：

```text id="f66j3d"
schema_version
```

### 5.53 [P2] Redis Replication 下为什么锁可能有问题？

假设：

```text id="1oz4uk"
Primary
→ Replica
```

Client A：

```text id="oh6nqo"
acquire lock on Primary
```

但 lock 还没复制到 Replica。 Primary crash。 Replica 被提升成新 Primary。

Client B：

```text id="ge8f4j"
does not see lock
→ acquires same lock
```

于是：

```text id="5icy5a"
A and B both believe ownership
```

这来自：

```text id="z60pjy"
asynchronous replication
```

和 failover。 所以：

```text id="0p0sgd"
single Redis primary lock
```

在某些 failure model 下并不是严格互斥证明。

### 5.54 [P2] Redis Cluster 能自动解决所有一致性问题吗？

不能。 Cluster 主要解决：

```text id="h9zslf"
sharding
availability
scale
```

不意味着：

```text id="2a1o4w"
所有 key strong consistency
```

也不意味着跨 key operation 自动：

```text id="wn0fca"
global transaction
```

如果 key 分布在不同 slot：

```text id="05c7pv"
multi-key atomic operation
```

还会受到限制。 所以要根据：

```text id="g7z8ks"
key placement
hash tag
replication semantics
```

设计。

### 5.55 [P1] Redis 持久化有哪两类基本思路？

面试常见：

```text id="45bs51"
RDB
AOF
```

**RDB**

周期性快照。 优点：

```text id="ckq2j9"
compact snapshot
recovery convenient
```

缺点：

```text id="06m8f4"
快照间隔内的数据可能丢
```

**AOF**

记录写操作日志。 通常：

```text id="ni7fqi"
durability 更细粒度
```

但：

```text id="w3anlg"
log size
rewrite
I/O
```

成本更高。

**为什么这里仍不把 Redis 当数据库？**

即使 Redis 开启持久化，它的：

```text id="ya7oko"
数据模型
transaction semantics
constraints
failure assumptions
```

仍然不同于 MySQL。 是否作为 source of truth 应由业务需求决定，而不是：

```text id="gyihd7"
Redis 也能落盘
```

就自动认为等价。

### 5.56 [P1] Redis 内存淘汰和 TTL 是一回事吗？

不是。

**TTL Expiration**

key 业务上：

```text id="6uexbw"
到期
```

所以删除。

**Eviction**

Redis 内存压力达到策略条件后：

```text id="u9128o"
为了腾内存
```

主动淘汰 key。 即使 key：

```text id="imrhvq"
TTL 还没到
```

也可能被 eviction。 所以如果某个 Redis key 是：

```text id="xmjexy"
critical lock / nonce / authorization fact
```

必须理解配置下：

```text id="bc5spz"
会不会被 eviction
```

而不能假设：

> 只要 TTL 没到它一定存在。

### 5.57 [P2] 为什么把安全关键事实和普通 Cache 放在同一个 Redis 要谨慎？

普通 cache 可以：

```text id="6p1d30"
evict
miss
rebuild
```

但：

```text id="bih4wu"
nonce used marker
one-time grant
lock ownership
```

如果被 eviction：

```text id="hv8qpo"
安全语义变化
```

例如 nonce marker 被提前淘汰：

```text id="c6y5xl"
replay may be accepted
```

所以安全关键 Redis state 需要单独考虑：

```text id="gve6jn"
eviction policy
memory reservation
namespace
failure behavior
persistence requirement
```

不能只当普通缓存。

### 5.58 [P2] 什么是 Cache Consistency 的本质？

缓存一致性不是：

> 如何保证 Redis 永远和 DB 一模一样？

更实际的问题：

```text id="ifnvfy"
允许 stale 多久？
谁是 source of truth？
什么时候 invalidate？
miss 如何 rebuild？
错误 stale 会不会破坏 correctness？
```

如果缓存只用于：

```text id="edh4ow"
页面展示
```

允许：

```text id="729dfv"
5s stale
```

可能完全合理。 如果缓存用于：

```text id="7gibyz"
authorization
payment eligibility
```

旧数据 5 秒可能无法接受。 所以：

```text id="pp9rt5"
cache consistency requirement
```

必须由业务 invariant 决定。

### 5.59 [P2] 什么是 Cache Invalidation Problem？

缓存最难的问题往往不是：

```text id="v5o2dj"
怎么写入
```

而是：

> 什么时候知道缓存已经不可信？

数据变化可能来自：

```text id="duer2p"
当前服务
其他服务
admin
batch job
DB migration
CDC
```

如果只有当前应用知道：

```text id="g4m2vi"
invalidate()
```

其他 writer 会让 cache stale。 所以大型系统常利用：

```text id="wuln34"
event
CDC
version
short TTL
```

组合解决。

### 5.60 [P2] CDC Cache Invalidation 是什么？

数据库发生变化：

```text id="5lre53"
UPDATE product
```

进入：

```text id="f1wc26"
binlog
```

CDC 捕获：

```text id="mw3npu"
ProductUpdated
```

缓存 invalidator：

```text id="unqf4h"
DELETE cache key
```

这样不是要求每个业务 writer 都记得：

```text id="dwin39"
delete Redis
```

**仍有什么问题？**

```text id="pkxc9f"
CDC lag
event loss/duplicate
cache delete race
```

所以仍是：

```text id="jhkyvb"
eventual consistency
```

设计，不是魔法强一致。

### 5.61 [P2] Redis 能不能做消息队列？

可以做某些队列模式。 例如：

```text id="vhawc3"
List
Streams
Pub/Sub
```

但不同机制语义差异很大。

**Pub/Sub**

更偏实时广播：

```text id="4nvxqx"
subscriber offline
→ message may be missed
```

**Streams**

支持更完整的：

```text id="q0y14b"
consumer group
pending entries
ack-like semantics
```

但如果业务需要：

```text id="4m02fp"
复杂 durable messaging
large-scale replay
DLQ
broker-level operations
```

专业 MQ 可能更合适。 所以不要：

```text id="5s4ja4"
Redis 很快
→ 所有 MQ 都换 Redis
```

### 5.62 [P1] 为什么 Redis Pub/Sub 不适合作为关键支付事件的唯一通道？

如果 consumer 暂时掉线：

```text id="dga02p"
event published
```

它可能：

```text id="3338ao"
收不到
```

而支付事件通常需要：

```text id="46l85g"
durability
redelivery
audit
replay
```

所以：

```text id="urcuwl"
best-effort pub/sub
```

通常不足以承担关键事实传播。

### 5.63 [P2] Rate Limit 和 Backpressure 有什么关系？

Rate Limit：

```text id="my8tiu"
限制进入速率
```

Backpressure：

```text id="9u0qei"
下游能力不足时向上游反馈
```

Rate Limit 可以作为 backpressure 的一种实现工具。 例如：

```text id="4cewnq"
DB pool saturated
```

系统动态降低：

```text id="04ms8h"
accepted request rate
```

而不是只依赖静态：

```text id="zn2aoe"
1000 req/s
```

所以高级系统可能：

```text id="wgp0mf"
adaptive concurrency / adaptive rate limit
```

根据实际 latency 和 error 调整。

### 5.64 [P2] 静态 Rate Limit 有什么问题？

例如：

```text id="f0y2hn"
limit = 1000 req/s
```

正常：

```text id="u9m7nk"
下游 capacity = 5000
```

限制过保守。 故障时：

```text id="34cv01"
下游 capacity = 200
```

1000 又太高。 所以固定 limit 只能近似容量。 更高级可以根据：

```text id="gfsn41"
latency
error rate
queue depth
CPU
in-flight requests
```

动态调整。 但 adaptive control 本身更复杂，容易振荡。

### 5.65 [P2] 为什么 Rate Limiter 本身不能成为单点瓶颈？

如果所有请求：

```text id="u490is"
global Redis INCR one key
```

限流 key：

```text id="f6aym9"
global:requests
```

会形成：

```text id="ltz1ar"
hot key
```

整个服务的每次请求都打它。 解决可以考虑：

```text id="62d1wa"
local approximate limit
sharded counters
hierarchical limit
token allocation
```

但会牺牲精确度。 所以：

```text id="bcqkrd"
global exact rate limit
```

本身也有 scalability cost。

### 5.66 [P2] Local Rate Limit 和 Distributed Rate Limit 怎么选？

**Local**

每实例：

```text id="cgox14"
100 req/s
```

10 instances：

```text id="2xqdjn"
≈1000 req/s
```

优点：

```text id="y0ylfj"
fast
no Redis dependency
```

缺点：

```text id="4khg99"
实例流量不均时不精确
scale up/down changes global capacity
```

**Distributed**

所有实例共享：

```text id="m0howt"
global counter
```

更精确。 代价：

```text id="ptzrg4"
network
Redis dependency
hot key
availability coupling
```

因此很多系统采用：

```text id="z39cw0"
local fast limiter
+
global coarse limiter
```

分层控制。

### 5.67 [P2] 什么是 Hierarchical Rate Limit？

例如：

```text id="n6h2l4"
Global:
10000 req/s

Tenant:
1000 req/s

User:
100 req/s

Sensitive endpoint:
10 req/s
```

请求必须同时满足多个 bucket。 这样既保护：

```text id="h8ko9d"
整个系统
```

又防止：

```text id="d4j1po"
单租户占满容量
```

还能对昂贵 API：

```text id="h47tz7"
更严格限制
```

### 5.68 [P2] 为什么 Payment Rate Limit 和普通 Query Rate Limit 不应该完全一样？

因为两类操作成本不同。 Query：

```text id="5ssyx4"
read-only
retry relatively safe
```

Payment：

```text id="myhpud"
external side effect
security sensitive
expensive reconciliation
```

所以可能需要：

```text id="hifztw"
更低 rate
更低 concurrency
per-user / per-merchant budget
```

甚至：

```text id="ziquzl"
attempt limit
```

而不仅仅是 QPS。

### 5.69 [P1] Redis Key 的高基数有什么影响？

例如：

```text id="87oy50"
rate:{user_id}:{endpoint}:{minute}
```

如果：

```text id="4zf9r3"
10 million users
100 endpoints
```

key 数量可能非常大。 即使 value 很小：

```text id="l69qcn"
key metadata
expire metadata
allocator overhead
```

也占内存。 所以设计 TTL key 时需要估算：

```text id="o94dvo"
cardinality
```

而不只是 value 大小。

### 5.70 [P1] 为什么 TTL Key 要考虑过期抖动？

如果所有用户登录 token：

```text id="b4sxsa"
创建时间相近
TTL 完全相同
```

可能同一时刻：

```text id="jh825v"
大量过期
大量重新认证
大量 cache rebuild
```

给 TTL 加：

```text id="46wihc"
small random jitter
```

可以平滑负载。 但对于：

```text id="vdthau"
security expiry
```

不能随便把有效期随机延长。 只能根据安全语义决定是：

```text id="rs4hrk"
提前抖动
```

还是缓存 TTL 与业务 expiry 分离。

### 5.71 [P2] Cache TTL 和 Business ValidUntil 有什么区别？

非常重要。

**Cache TTL**

表示：

```text id="aswn9v"
这份 Redis 副本最多保留多久
```

**Business ValidUntil**

表示：

```text id="dgt93u"
这个业务事实本身到什么时候仍合法
```

例如：

```text id="5ly5jx"
quote valid until 12:00
```

即使 cache：

```text id="2c824w"
TTL still 10 minutes
```

12:01 时 quote 仍然：

```text id="ps6chq"
invalid
```

所以：

```text id="61w7lz"
cache existence
≠
business validity
```

这条线后面 Catalog / Quote 会继续出现。

### 5.72 Redis 中最重要的一条 Correctness 主线

可以把 Redis 在后端系统中的位置总结成：

```text id="i2qzzf"
Redis
很适合
↓

cache
ephemeral coordination
short-lived token
counter
rate limit
fast derived state
```

但：

```text id="0idfj7"
Redis presence
```

通常不应自动被解释成：

```text id="yrjx5y"
authoritative irreversible business fact
```

尤其是：

```text id="uw7ygs"
payment succeeded
money settled
entitlement granted forever
```

这些通常需要更强的 durable source of truth。

### 5.73 高频错误设计：Redis 快，所以把所有状态都放 Redis

问题：

```text id="lfnbp7"
eviction
failover
replication semantics
persistence mode
memory pressure
```

都可能影响事实。 正确问题：

```text id="gr8ab0"
这份状态丢失后
系统能否从 authoritative source 重建？
```

如果答案：

```text id="jm8mwq"
不能
```

就要认真评估 Redis 是否适合作为唯一事实源。

### 5.74 高频错误设计：用了 SET NX 就等于 Exactly-once

`SET NX` 可以帮助：

```text id="dkur3e"
only one claimant at a moment
```

但：

```text id="z5xcf6"
claim
→ side effect success
→ process crash
```

下次怎么恢复？ 又或者：

```text id="x8mo6e"
lock expires
→ second owner
```

所以：

```text id="y0b9pt"
SET NX
```

不是 exactly-once business semantics。

### 5.75 高频错误设计：锁设置 TTL 就安全了

TTL 解决：

```text id="hvs2fo"
owner crash 后永久死锁
```

但引入：

```text id="96kbyq"
lease expires while owner still running
```

问题。 因此还需要思考：

```text id="p4m9dy"
renewal
fencing
idempotency
```

而不是：

```text id="ldpr24"
NX + EX
→ 完美分布式锁
```

### 5.76 高频错误设计：缓存和 DB 双写都成功概率很高，所以没事

只要两个独立系统：

```text id="hwqgne"
DB
Redis
```

分别写：

```text id="mirkle"
都可能独立成功/失败
```

就存在：

```text id="e0l89u"
partial failure
```

即使概率很低：

```text id="24j1ts"
高 QPS × 长时间
```

最终也会发生。 正确设计应该明确：

```text id="hbn3oy"
谁是 source of truth？
stale 能持续多久？
怎么修复？
```

### 5.77 高频错误设计：Redis 挂了就统一 Fail-open

如果 Redis 只是：

```text id="2fdei8"
recommendation cache
```

fail-open / fallback 很正常。 但如果：

```text id="34jeo6"
nonce store
```

fail-open：

```text id="hfj5jg"
skip replay protection
```

安全语义会改变。 所以 failure policy：

```text id="stxujo"
必须按 key 的业务语义
```

设计。

### 5.78 高频错误设计：分布式锁能替代数据库约束

Redis lock：

```text id="symt95"
只是协调机制
```

如果应用 bug、Redis failover、TTL race：

```text id="jq4x7o"
两个 writer 仍可能进入
```

数据库本地 invariant：

```text id="5seq33"
UNIQUE
CHECK
version
```

仍应该由数据库自己保护。 所以：

```text id="3kuugd"
distributed lock
```

不是：

```text id="or1569"
database constraint replacement
```

### 5.79 本章高频对比

| 概念 A         | 概念 B                    | 核心区别                                   |
| ------------ | ----------------------- | -------------------------------------- |
| Redis        | MySQL                   | 快速内存状态/协调 vs durable relational source |
| TTL          | Eviction                | 业务/缓存到期 vs 内存压力淘汰                      |
| Cache Aside  | Write-through           | 应用管理 miss/invalidate vs 写入经过缓存层        |
| Penetration  | Breakdown               | 不存在 key vs 热点 key 失效                   |
| Breakdown    | Avalanche               | 单热点失效 vs 大面积缓存失效                       |
| SET NX       | Distributed Correctness | 原子 claim vs 完整业务正确性                    |
| Lock TTL     | Business Deadline       | lease 生存时间 vs 业务最晚完成时间                 |
| Lock         | Idempotency             | 阻止同时执行 vs 重复执行结果安全                     |
| Owner Token  | Fencing Token           | 防误删锁 vs 防旧 owner 提交                    |
| Watchdog     | Fencing                 | 延长 lease vs 拒绝 stale owner             |
| Redlock      | Fencing                 | 多节点 lease 获取策略 vs 资源端代际校验              |
| GETDEL       | Exactly-once            | 一次消费 key vs 一次业务效果                     |
| Pipeline     | Transaction             | 减少 RTT vs 执行语义组合                       |
| Fixed Window | Sliding Window          | 固定时间段计数 vs 滑动时间范围                      |
| Token Bucket | Leaky Bucket            | 允许 burst vs 平滑输出                       |
| Rate Limit   | Concurrency Limit       | 每单位时间多少 vs 同时多少                        |
| Rate Limit   | Backpressure            | 静态/规则限速 vs 下游能力反馈                      |
| Local Limit  | Distributed Limit       | 快速近似 vs 全局协调                           |
| Cache TTL    | ValidUntil              | 副本生命周期 vs 业务事实有效期                      |
| Cache        | Projection              | 临时加速副本 vs 可重建派生读模型                     |

### 5.80 面试前一分钟速记

```text id="j93m6i"
Redis 快不是只因为单线程：
内存 + 数据结构 + 简单执行路径 + 事件模型。

Redis 更适合：
cache
counter
short-lived control state
rate limit
ephemeral coordination

MySQL 更适合：
durable source of truth
transaction
constraint

TTL：
key 生命周期。

Eviction：
内存不够时主动淘汰。

Cache Aside：
read cache
miss → DB
fill cache

write：
通常 DB first
then invalidate cache。

缓存穿透：
不存在 key。

缓存击穿：
一个 hot key 失效。

缓存雪崩：
大量 key / 整层缓存失效。

SET NX：
原子 claim，
不是 exactly-once。

Distributed Lock 至少要考虑：
TTL
owner token
atomic release

更严格还要：
fencing token。

Lock
≠
Idempotency。

GETDEL：
one-shot consumption，
不保证 side effect exactly once。

Rate Limit：
控制进入速率。

Concurrency Limit：
控制 in-flight。

Fixed Window 简单但有边界 burst。

Token Bucket：
长期限速 + 允许 burst。

Redis failure：
fail-open / fail-closed
必须从业务 invariant 推导。

Cache TTL
≠
Business ValidUntil。

Redis lock 最多减少竞争，
不能替代：
DB constraint
idempotency
reconciliation。
```

### 5.81 StablePay 映射

本章只做弱映射。

```text id="qx2tbb"
Redis Nonce Store
→ replay-control state

Rate Limiter
→ Gateway capacity / abuse control

Memory Fallback
→ availability 与 distributed correctness 的 trade-off

GETDEL
→ one-shot execution grant

TTL
→ nonce / temporary control state lifecycle

Fail-open / Fail-closed
→ security boundary 与 availability 的选择

Redis Lock / Token
→ 可用于降低并发竞争，
但不能替代 payment idempotency
```

当前 StablePay Gateway 在 Redis 可用时使用 Redis limiter 和 nonce store；Redis 不可用时会退回 memory implementation。这个项目事实非常适合 01 继续追问：

```text id="msrrdh"
单实例 fallback
和
多实例 distributed semantics
有什么差异？
```

02 在这里应该只掌握通用原理：

```text id="1y6kan"
local memory control state
```

不能天然提供：

```text id="mzqvk6"
cross-instance global invariant
```

同样，Payment Service 中使用 `GETDEL` 消费一次性执行授权，是理解：

```text id="qq30u9"
atomic one-shot consume
```

的好例子；但它本身仍不能证明：

```text id="o1x8ii"
外部支付 side effect 只发生一次
```

这类源码级实现和边界继续留给 01。

### 5.82 本章学习优先级

### 第一轮：P0

必须立即会：

```text id="w6xriq"
Redis 为什么快
常见数据结构
Redis vs MySQL
TTL
Cache Aside
穿透 / 击穿 / 雪崩
SET NX
Rate Limit
Fixed Window
Token Bucket
```

### 第二轮：P1

重点：

```text id="rk3x5f"
缓存一致性 race
Bloom Filter
Singleflight
Stale-While-Revalidate
owner token
Lua atomicity
GETDEL
Sliding Window
Leaky Bucket
Fail-open / Fail-closed
local vs distributed limit
cache versioning
```

### 第三轮：P2

针对后端 / Infra：

```text id="rr4unr"
lease expiry
watchdog
fencing token
Redlock
replication failover
Redis Cluster semantics
CDC cache invalidation
adaptive rate limiting
hierarchical rate limit
hot key
critical Redis state eviction
```

最终不要背成：

> “Redis 可以做缓存、分布式锁和限流，因为它很快。”

更完整的理解应该是：

> Redis 很适合承载低延迟缓存和短期协调状态，但缓存本身需要明确 source of truth 与 stale tolerance；分布式锁只能协调 ownership，不能替代幂等和资源端 invariant；限流也必须区分 rate 与 concurrency，并决定 Redis 故障时 fail-open 还是 fail-closed。Redis 是非常强的控制平面工具，但越接近支付、安全和不可逆副作用，就越不能把“Redis 里有一个 key”直接当成最终业务事实。

下面按“通用 MQ 与事件驱动 + RocketMQ 专有实现”合并。重复的概念只保留一次；RocketMQ 的具体机制并入对应通用概念。未重复的独特内容尽量保留。

## 6. MQ、RocketMQ 与事件驱动（合并精华版）

消息队列最容易被背成：

```text
削峰
解耦
异步
```

这三个词没有错，但不足以解释一个生产消息系统。 真正的追问通常是：

```text
Producer 返回成功时，消息一定不会丢吗？
Consumer 收到消息后什么时候 ACK？
DB commit 后 ACK 前 crash 会怎样？
为什么 Consumer 一定要幂等？
At-least-once 到底是谁至少一次？
Exactly-once 到底保证了什么？
消息重复和业务重复是一回事吗？
顺序消息能保证全局顺序吗？
Poison Message 为什么不能无限 retry？
DLQ 以后怎么办？
Consumer Lag 为什么会越来越大？
DB 和 MQ 双写为什么 Outbox 能改善？
Inbox 又解决什么？
Replay 历史消息为什么可能把业务再执行一遍？
```

这一章的核心不是：

> MQ 能不能把消息送到。

而是：

> **当消息可能延迟、重复、乱序、消费失败、Consumer crash 时，业务状态还能不能保持正确。**

StablePay 使用的是 RocketMQ，因此先建立 RocketMQ 完整心智模型：

```text
Producer
   ↓
NameServer / Route
   ↓
Broker
   ↓
Topic
   ↓
MessageQueue
   ↓
ConsumerGroup
   ↓
PushConsumer
   ↓
Business Handler
```

然后再回答更通用的问题。 RocketMQ 官方当前模型仍将消息生命周期划分为：

```text
生产
→ 存储
→ 消费
```

Topic 下由多个 Queue 实现水平分区，Consumer Group 则承担消费扩展和负载均衡。

### 6.1 为什么需要 MQ / RocketMQ？

最直接的三个理由：

```text
异步
解耦
削峰填谷
```

**异步**

同步链路：

```text
Payment Service
    ↓
Verification
    ↓
Notification
    ↓
Analytics
    ↓
Response
```

所有下游都在用户请求路径里。 如果分别耗时：

```text
100ms
100ms
200ms
300ms
```

整个链路越来越长。 改为：

```text
Payment Service
    ↓
commit payment
    ↓
publish PaymentSucceeded
    ↓
return
```

其他业务：

```text
Verification Consumer
Notification Consumer
Analytics Consumer
```

异步处理。

**解耦**

同步 RPC：

```text
Payment Service
必须知道
Verification Service 地址、接口、错误
```

事件模式：

```text
Payment
   ↓
payment.success
   ↓
RocketMQ
   ↓
任意订阅者
```

Producer 不需要知道：

```text
现在有多少 consumer
consumer 用什么语言
consumer 什么时候上线
```

只发布：

```text
OrderCreated
```

下游独立订阅。

**削峰填谷**

突然：

```text
10000 messages/s
```

但下游只能：

```text
2000/s
```

MQ 可以先存储消息：

```text
Producer burst
      ↓
RocketMQ
      ↓
 backlog
      ↓
Consumer 2k/s
```

这不是提高 Consumer 的实际处理能力，而是：

> **用时间换瞬时容量。**

**削峰不是消灭流量**

如果长期：

```text
produce rate > consume rate
```

最终只是：

```text
queue grows forever
```

因此 MQ 只能吸收：

```text
temporary burst
```

不能创造无限处理能力。

### 6.2 RocketMQ 核心组件：Producer、NameServer、Broker、Consumer

最基本模型：

```text
Producer
   ↓
Broker
   ↓
Consumer
```

RocketMQ 经典部署模型加 NameServer：

```text
Producer
NameServer
Broker
Consumer
```

Producer 和 Consumer 通过 NameServer 获取 Topic/Broker 路由，再直接和 Broker 通信。

**Producer**

负责：

```text
创建消息
选择 Topic / Queue
发送给 Broker
```

例如：

```text
Payment Service
→ PaymentConfirmed
```

**NameServer**

负责：

```text
Broker registration
+
Topic routing discovery
```

可以粗略理解：

```text
Topic A
→ Broker 1
→ Broker 2
→ Queue 信息
```

Broker：

```text
定期向 NameServer 注册自己
```

Producer / Consumer：

```text
查询 Topic 路由
↓
知道该连接哪些 Broker
```

之后消息数据流主要发生在：

```text
Client
↔
Broker
```

而不是：

```text
Client
→ NameServer
→ Broker
```

每条消息都经过 NameServer。 NameServer 不是消息存储主体。不要只回答：

> 类似 ZooKeeper。

这太粗。

**Broker**

真正负责：

```text
接收消息
持久化消息
管理 Queue
提供 Consumer 拉取消费
维护消息相关状态
```

例如：

```text
RocketMQ
Kafka
RabbitMQ
```

**Consumer**

订阅：

```text
Topic
```

并执行：

```text
message
→ business handler
→ success / failure
```

例如：

```text
Verification Service
```

收到：

```text
PaymentConfirmed
```

后写入购买记录。

### 6.3 Topic、Event Type、Tag

Topic 表示：

> 一类消息的逻辑集合。

例如：

```text
payment_events
order_events
catalog_events
agent_events
```

Producer：

```text
publish to payment_events
```

Consumer：

```text
subscribe payment_events
```

Topic 是：

```text
logical category
```

不是单一物理文件。

**Topic 不是 Event Type**

一个 Topic 内可能包含：

```text
payment.created
payment.confirmed
payment.failed
payment.refunded
```

这些属于不同：

```text
event_type
```

所以：

```text
Topic
→ routing category

Event Type
→ business semantic
```

**Tag 是什么？**

Topic 可以表示较粗的业务类别：

```text
payment_events
```

Tag 可以进一步分类：

```text
payment.success
payment.failed
payment.refunded
```

Consumer 可以根据 Tag：

```text
filter
```

只消费自己关心的子类。

**Topic 和 Tag 应该怎么划分？**

不要：

```text
每种 event 一个 Topic
```

也不要：

```text
整个公司所有事件一个 Topic
```

通常从：

```text
业务领域
消息规模
隔离需求
消费语义
SLA
```

判断。 例如：

```text
Topic:
payment_events

Tags:
payment.success
payment.failed
payment.refunded
```

比：

```text
payment_success_topic
payment_failed_topic
payment_refunded_topic
```

可能更容易管理。 但如果：

```text
成功事件 SLA 极高
失败审计流量巨大
```

也可能值得物理隔离。

### 6.4 Queue / Partition / MessageQueue

一个 Topic 往往会分成多个：

```text
Queue / Partition
```

RocketMQ 中称为：

```text
MessageQueue
```

概念：

```text
payment_events

Partition 0
Partition 1
Partition 2
Partition 3
```

RocketMQ 中：

```text
Topic: payment_events

Queue 0
Queue 1
Queue 2
Queue 3
```

目的包括：

```text
parallelism
scalability
ordering scope
```

不同 Broker 术语略有区别，但核心类似。 MessageQueue 是 RocketMQ 的分区和有序流基本单元之一；官方 5.0 文档明确把 Queue 描述为 Topic 的组成部分，并通过 Queue 支持水平分区，消息在 Queue 内按存储顺序排列并由 offset 标识。

**为什么不只用一个 Queue？**

一个 queue：

```text
只能由有限 consumer 顺序推进
```

分区后：

```text
P0 → Consumer A
P1 → Consumer B
P2 → Consumer C
```

可以增加消费并行度。 假如只有一个 Queue：

```text
Consumer 1
```

很容易成为单一消费通道。 多个 Queue：

```text
Q0 → Consumer A
Q1 → Consumer A
Q2 → Consumer B
Q3 → Consumer B
```

可以提高并发消费能力。

**MessageQueue 和 Kafka Partition 类似吗？**

在面试中可以类比：

```text
RocketMQ MessageQueue
≈
Kafka Partition
```

因为它们都承担：

```text
Topic 内水平分区
局部有序
consumer parallelism unit
offset-based consumption
```

但不能直接说：

> 两者完全一样。

不同 MQ：

```text
storage
rebalance
offset management
broker architecture
transaction
retry
```

细节不同。 面试最好说：

> 在帮助理解 Topic 分区和局部顺序时可以类比 Kafka Partition，但具体实现语义仍按 RocketMQ 自己理解。

### 6.5 Consumer Group、Clustering、Broadcasting

Consumer Group：

> 一组拥有相同消费语义的 Consumer 实例。

例如：

```text
Group = verification

Consumer A
Consumer B
Consumer C
```

Broker 会把 partitions / queues 分配给 group 内不同实例。 目标：

```text
scale consumption horizontally
```

RocketMQ 5.0 官方把 Consumer Group 定义为使用相同消费行为的 Consumer 的负载均衡组，组内 Consumer 用于扩展消费性能和高可用。

**不同 Group 呢？**

```text
verification_group
analytics_group
notification_group
```

可以分别获得同一 Topic 的消息。 也就是：

```text
同一事件
→ 多种独立业务处理
```

例如：

```text
payment.success
```

有：

```text
verification_group
notification_group
analytics_group
```

三个不同 Group。 那么逻辑上：

```text
Verification
看到一次

Notification
看到一次

Analytics
看到一次
```

但同一个：

```text
verification_group
```

里的多个实例则通常是：

```text
共同分担
```

而不是每个实例都执行全部消息。

**Cluster 模式和 Broadcast 模式**

RocketMQ 经典消费模型支持：

```text
Clustering
Broadcasting
```

官方 4.x 文档也将这两种模式作为 Consumer Group 的主要消费模式。

**Clustering**

同 Group 多 Consumer：

```text
C1
C2
C3
```

共同分担：

```text
Topic queues
```

整体上：

```text
这个 Group 消费全部消息
```

但每个实例只承担部分。 适合：

```text
业务处理
水平扩展
```

**Broadcasting**

同一 Group：

```text
每个 Consumer 都收到完整消息
```

适合：

```text
配置通知
本地 cache invalidation
某些广播事件
```

但如果业务副作用是：

```text
发券
扣款
创建订单
```

广播模式会让每个实例都执行，很危险。

### 6.6 Push Consumer 和 Pull Consumer

**Pull**

Consumer 主动问：

```text
有消息吗？
给我下一批。
```

它更显式控制：

```text
poll frequency
batch size
offset
```

**Push**

看起来 Broker 主动：

```text
push
```

给 Consumer。 很多实现底层仍可能是：

```text
long polling / managed pull
```

但框架帮开发者隐藏了拉取逻辑。 RocketMQ 中用户侧 API 看起来是：

```text
PushConsumer
```

消息到达后：

```text
callback()
```

像推送。 但 RocketMQ 客户端消费的底层历史实现主要仍基于客户端从 Broker 获取消息，再在客户端形成“Push”式回调体验。 因此面试回答最好是：

> PushConsumer 描述的是应用编程模型：应用注册 listener，由客户端管理取消息、缓存、负载均衡和回调；不要把它理解成 Broker 对业务 handler 直接建立一次真正无状态 HTTP push。

RocketMQ 当前官方也同时区分 PushConsumer、SimpleConsumer 和 PullConsumer 等消费者类型。

**核心区别**

不要纠结字面网络实现。 更重要的是：

```text
消费节奏由谁显式控制
```

以及框架提供什么：

```text
rebalance
retry
ack
backpressure
```

能力。

**PushConsumer 和 PullConsumer 怎么选？**

**PushConsumer**

开发者：

```text
register handler
```

SDK 负责更多：

```text
fetch
local buffering
delivery
retry interaction
```

适合普通业务消费。

**Pull / Simple-style Consumer**

应用更主动控制：

```text
什么时候拉
拉多少
什么时候确认
```

适合需要：

```text
精细流控
特殊流处理
自定义消费循环
```

的场景。 一般 StablePay 这种：

```text
payment event
→ business handler
```

使用 PushConsumer 更自然。

### 6.7 ACK、ConsumeSuccess、ConsumeRetryLater

ACK：

> Consumer 告诉 Broker，这条消息已经处理完成。

简化：

```text
Broker
→ Message
→ Consumer

Consumer handles successfully

Consumer
→ ACK
→ Broker
```

Broker 收到 ACK 后，知道这条消息不需要再按正常失败逻辑重投。 RocketMQ 以 PushConsumer 心智模型看：

```text
message delivered
↓
business handler
↓
success
or
failure
```

StablePay 当前 Go consumer 对应的就是类似：

```text
ConsumeSuccess
ConsumeRetryLater
```

这两个结果非常值得理解。

**Success**

表示：

```text
这一轮业务消费已经成功处理
```

Broker / client 可以推进该 Group 的消费状态。

**RetryLater**

表示：

```text
当前没有成功处理
请以后重新投递
```

**ACK 什么时候发？**

这是消息正确性的核心问题。 如果：

```text
收到消息
→ 立即 ACK
→ 再执行业务
```

Consumer 在业务执行前 crash：

```text
message lost from business perspective
```

因此通常：

```text
业务成功
→ ACK
```

更安全。 但这样又产生：

```text
业务成功
→ ACK 前 crash
```

导致 Broker：

```text
redelivery
```

所以 Consumer 必须：

```text
idempotent
```

这就是 at-least-once 系统的核心逻辑。

### 6.8 Offset、Consumer Offset、Consumer Lag

Offset 可以理解成：

> Consumer 在一个有序消息流中已经处理到哪里。

一个 MessageQueue 是有序消息流：

```text
M0
M1
M2
M3
...
```

每条消息有位置：

```text
offset 0
offset 1
offset 2
offset 3
```

RocketMQ 官方把 MessageQueueOffset 定义为消息在 Queue 中的唯一 Long 型位置。 Consumer Group 需要记录：

> 我已经消费到哪里。

例如：

```text
Queue 0
latest stored offset = 1000

verification_group
consumer offset = 800
```

表示：

```text
还有大约 200 条没跟上
```

RocketMQ 官方区分 MessageQueueOffset 和 ConsumerOffset，后者表示 Consumer Group 的消费进度。

**Consumer Lag 是什么？**

可以直觉理解：

```text
producer latest offset
-
consumer progress
```

或者更进一步看：

```text
oldest unconsumed message age
```

如果：

```text
Producer = 10k/s
Consumer = 5k/s
```

lag：

```text
越来越大
```

**为什么不能只看 Queue Length？**

因为：

```text
100000 messages
```

如果 Consumer：

```text
100000/s
```

也许一秒就追完。 而：

```text
1000 messages
```

每条要：

```text
10s
```

可能严重积压。 所以最好看：

```text
message count lag
+
time lag
+
consume rate
```

**Consumer 成功消费后消息会从 Broker 删除吗？**

通常不是：

```text
ACK
→ physical message immediately delete
```

RocketMQ 消息存储和消费进度是分离的。 Broker 按存储策略保留消息。 Consumer Group 记录：

```text
消费进度
```

官方 5.0 文档明确说明消息是否已消费并不决定物理存储生命周期；消息按存储时长统一保留，消费进度由 Consumer 管理，可以在消息仍处于保留期时进行回溯或重置位点消费。 这也是为什么：

```text
replay
```

成为可能。

### 6.9 投递语义：At-most-once、At-least-once、Exactly-once

**At-most-once**

At-most-once：

```text
最多处理一次
```

可能：

```text
0 次
或
1 次
```

不能保证一定处理。 例如：

```text
receive
→ commit offset / ACK
→ process
```

如果 ACK 后 crash：

```text
message won't redeliver
```

业务处理：

```text
0 次
```

**特点**

```text
no duplicate
but possible loss
```

适合某些允许丢失的 telemetry。 不适合重要支付事实。

**At-least-once**

At-least-once：

```text
消息最终至少会尝试处理一次
```

可能：

```text
1 次
2 次
3 次
...
```

即允许 duplicate delivery。 典型：

```text
process
→ commit DB
→ crash before ACK
```

Broker 不知道已经成功：

```text
redeliver
```

所以：

```text
at-least-once
```

几乎天然要求：

```text
idempotent consumer
```

**Exactly-once**

这是最容易回答错的一题。 不能直接说：

> Exactly-once 就是消息永远只消费一次。

首先要问：

```text
哪个层面的 once？
```

可能是：

```text
Broker delivery exactly once

Consumer handler invocation exactly once

Database update exactly once

External side effect exactly once

Business effect exactly once
```

这些不是一回事。 生产系统更常追求：

```text
effective exactly-once
```

即：

> 底层允许 retry / duplicate，但最终业务效果等价于执行一次。

通常依赖：

```text
stable identity
+
idempotency
+
transaction
+
dedup
+
reconciliation
```

而不是幻想网络永远只送一次。

**为什么“MQ Exactly-once”也不等于业务 Exactly-once？**

假设 Broker 真能确保 handler 只获得一次消息。 Handler：

```text
call payment API
↓
payment success
↓
process crashes
```

本地：

```text
没有记录结果
```

恢复后业务可能：

```text
重新创建另一个 command
```

又支付一次。 所以：

```text
MQ delivery semantics
```

只是整条链中的一层。 业务 exactly-once 还依赖：

```text
event identity
business identity
DB invariant
remote idempotency
side-effect ordering
reconciliation
```

### 6.10 Consumer 幂等、Event ID、Business Idempotency Key

**为什么 Consumer 必须幂等？**

经典 timeline：

```text
T0 Consumer receives event E

T1 Consumer writes DB successfully

T2 Consumer crashes

T3 ACK not sent

T4 Broker redelivers E

T5 Consumer receives E again
```

如果 Consumer：

```text
每次收到
→ balance += 100
```

最终：

```text
+200
```

错误。 所以需要：

```text
event identity
```

例如：

```text
event_id = evt-123
```

数据库：

```text
UNIQUE(event_id)
```

第二次：

```text
already processed
→ return success
```

**Idempotent Consumer 的基本模式**

```text
BEGIN

INSERT processed_event(event_id)
ON UNIQUE CONFLICT
    already done

apply business change

COMMIT
```

关键是：

```text
dedup marker
+
business update
```

最好处于：

```text
same local transaction
```

否则又会出现 crash window。

**为什么“先查 Event ID，再处理”仍然有 Race？**

错误：

```text
SELECT processed_event
→ not found

process business

INSERT processed_event
```

两个 Consumer 并发：

```text
A SELECT not found
B SELECT not found
```

然后都：

```text
process
```

最后才冲突。 所以：

```text
check then act
```

依然有 race。 应让数据库 constraint / transaction 成为：

```text
atomic boundary
```

**Event ID 和 Business Idempotency Key 有什么区别？**

**Event ID**

标识：

```text
这一个消息事件实例
```

例如：

```text
evt-123
```

**Business Idempotency Key**

标识：

```text
这一条逻辑业务命令
```

例如：

```text
payment:episode-1:merchant-42
```

可能存在：

```text
same business operation
→ different event IDs
```

例如系统错误地产生两条：

```text
evt-123
evt-999
```

都代表同一 payment。 如果 Consumer 只 dedupe：

```text
event_id
```

仍会执行两次业务效果。 所以：

```text
event identity
```

和：

```text
economic / business identity
```

解决不同层次的重复。

**Event ID 应该由谁生成？**

通常应该在：

```text
业务事件被创建时
```

生成稳定 identity。 不能每次重试 publish 都：

```text
生成新的 event_id
```

否则：

```text
redelivery/republication
```

在 Consumer 看来变成全新的事件。 例如：

```text
first publish:
evt-1

retry publish:
evt-2
```

Consumer 无法通过 event ID dedupe。 所以可靠重发应该保持：

```text
same logical event
→ same event identity
```

**Producer Message ID 能直接作为业务幂等 Key 吗？**

通常不应该机械这样做。 MQ-generated identity：

```text
描述消息实例
```

而业务 identity：

```text
描述业务操作
```

例如一次：

```text
PaymentConfirmed
```

因为故障恢复被重新构造了一条消息。 MQ Message ID：

```text
msg-A
msg-B
```

不同。 但业务：

```text
payment-intent-123
```

仍是同一件事。 所以关键业务事件最好包含：

```text
event_id
economic/business identity
```

而不是只依赖 broker-generated message id。

**Message Key 是什么？**

Message Key 常用于建立：

```text
business lookup identity
```

例如：

```text
order_id
payment_id
tx_id
```

方便：

```text
查询某一业务消息
```

RocketMQ 官方也把 MessageKey 描述为消息索引属性，可用于快速检索对应消息。

**但 Key 不是天然幂等**

```text
MessageKey = order-123
```

不会自动让 Consumer：

```text
只执行一次
```

幂等仍需要业务逻辑。

### 6.11 ACK 前后 Crash：核心 Failure Timeline

这是 MQ 必考题。

**Consumer 处理成功后 ACK 前 Crash 会怎样？**

```text
T0 receive E
T1 write DB
T2 COMMIT
T3 crash
T4 no ACK
```

Broker：

```text
认为没有成功
```

重新投递：

```text
E again
```

这不是 MQ bug。 而是：

```text
at-least-once
```

正常行为。 正确 Consumer：

```text
detect E already processed
→ return success
→ ACK
```

**ACK 后业务 Commit 前 Crash 会怎样？**

如果设计成：

```text
receive
→ ACK
→ DB write
```

然后：

```text
ACK success
DB not committed
crash
```

Broker：

```text
不会重新投递
```

事件业务效果永久丢失。 所以关键业务消息通常：

```text
不要在业务 durable commit 前确认消费成功
```

**RocketMQ Consume Success 前后 Crash**

```text
T0 message delivered

T1 handler starts

T2 DB transaction commits

T3 handler returns ConsumeSuccess
```

如果 crash：

**T1 前**

没有业务效果。 消息后续还能再投递。

**T2 前**

本地事务 rollback。 再消费通常安全。

**T2 后，T3 前**

数据库已经 commit。 但 MQ 可能不知道成功：

```text
redelivery
```

因此 consumer 必须幂等。

**T3 后**

正常推进消费。 这就是为什么：

```text
DB commit
→ ConsumeSuccess
```

仍然必须接受 duplicate delivery。

**为什么不能先返回 ConsumeSuccess 再处理 DB？**

如果：

```text
ConsumeSuccess
↓
DB write
```

中间 crash：

```text
message 已被认为完成
```

但：

```text
business effect 没完成
```

消息可能永久跳过。 所以关键业务通常采用：

```text
business commit
↓
success acknowledgment
```

接受：

```text
重复
```

而不是接受：

```text
丢失
```

### 6.12 Retry、DLQ、Poison Message、Transient / Permanent Failure

**Retry Queue**

Consumer 失败：

```text
temporary DB unavailable
```

Broker 不一定马上无限重新投递同一 Consumer。 可以：

```text
进入 retry queue
```

过一段时间再尝试。 例如：

```text
1 min
5 min
30 min
```

逐步延迟。 这和 RPC：

```text
backoff
```

思想相似。 RocketMQ 中 Consumer 处理失败：

```text
return failure / retry status
```

RocketMQ 会在后续重新投递。 当前官方 5.0 文档将 PushConsumer 的失败消费建模为：

```text
Ready
→ Inflight
→ WaitingRetry
→ ...
→ Commit or DLQ
```

超过配置最大重试次数后可进入 DLQ。

**DLQ**

DLQ：

> Dead Letter Queue。

消息多次处理失败后，不再进入正常 retry loop，而进入专门队列。 例如：

```text
normal queue
    ↓ fail
retry
    ↓ fail
retry
    ↓ fail
DLQ
```

目的：

```text
避免一条坏消息无限阻塞/消耗系统
```

RocketMQ 官方当前重试文档也把 DLQ 定义为达到最大重试次数后的保护机制，业务可后续消费 DLQ 进行恢复。

**Poison Message**

Poison Message：

> 某条消息因为自身内容或代码逻辑问题，几乎必然每次处理都失败。

例如：

```text
schema invalid
unsupported enum
corrupted payload
permanent business violation
```

如果无限 retry：

```text
consume
fail
retry
fail
retry
...
```

只会浪费：

```text
CPU
IO
consumer capacity
logs
```

所以需要：

```text
retry limit
→ DLQ
```

**Transient Failure 和 Permanent Failure 怎么区分？**

**Transient**

可能稍后恢复：

```text
DB temporarily unavailable
network timeout
rate limited
dependency overloaded
temporary lock conflict
```

适合：

```text
retry
```

**Permanent**

重试不会改变结果：

```text
invalid schema
missing required identity
unsupported currency
malformed payload
permanent authorization failure
program bug caused by one malformed payload
```

更适合：

```text
reject / DLQ / manual investigation
```

**为什么分类重要？**

否则：

```text
invalid JSON
```

可能被 retry：

```text
1000 次
```

它永远不会自己变合法。

**Retry 次数越多越可靠吗？**

不是。 如果失败原因是：

```text
permanent
```

retry 没意义。 如果下游：

```text
overloaded
```

大量 retry 反而：

```text
增加负载
```

所以 MQ retry 同样需要：

```text
bounded retries
backoff
DLQ
```

而不是：

```text
until success forever
```

**DLQ 以后怎么办？**

进入 DLQ 不代表问题解决。 必须有：

```text
inspection
classification
repair
replay policy
```

例如：

```text
为什么失败？
代码 bug？
schema incompatibility？
数据坏了？
依赖长期不可用？
```

修复后：

```text
是否允许 replay？
```

还要保证 replay 不会重复产生业务效果。 所以：

```text
DLQ
```

是故障隔离机制，不是垃圾桶。

**为什么 DLQ 必须可观测？**

如果：

```text
payment event
```

进入 DLQ。 系统主服务：

```text
看起来正常
```

但某些：

```text
entitlement
verification
```

永远没生成。 如果没有：

```text
DLQ size
DLQ arrival rate
oldest DLQ age
```

告警，就会形成 silent data loss。

**Retry 为什么可能导致 Head-of-Line Blocking？**

假设 Queue：

```text
M1 poison
M2 good
M3 good
M4 good
```

如果严格顺序消费：

```text
M1
失败
retry
失败
retry
```

后面的：

```text
M2 M3 M4
```

可能无法推进。 所以：

```text
顺序保证
```

和：

```text
failure isolation
```

存在 trade-off。 非顺序业务通常更容易把失败消息隔离出来重试。

### 6.13 顺序消息

消息顺序可以有不同范围。 例如：

```text
Order 1:
Created
Paid
Shipped
```

希望：

```text
Created → Paid → Shipped
```

按顺序处理。 但：

```text
Order 1
Order 2
Order 3
```

之间是否需要全局严格排序？ 通常不需要。 RocketMQ 不能说：

> RocketMQ 保证所有消息全局有序。

更准确：

> 顺序通常围绕同一有序分组 / Queue 内建立。

RocketMQ 当前官方 FIFO 文档也是围绕 MessageGroup 的有序存储与消费描述，并不要求不同 MessageGroup 之间建立顺序。

**为什么全局顺序很贵？**

全局顺序意味着：

```text
所有消息
→ one serial ordering point
```

并行度被限制。 例如：

```text
1 million orders
```

如果必须全部：

```text
one-by-one
```

吞吐很差。 更常见的是：

```text
per entity ordering
```

例如：

```text
same order_id
→ same partition
```

这样：

```text
同一订单有序
不同订单并行
```

**怎么实现 Per-key Ordering？**

常见：

```text
partition key = order_id
```

同一个：

```text
order_id
```

总是路由到：

```text
same partition
```

partition 内保持顺序。 例如：

```text
hash(order_id) % N
```

**代价**

如果某个 key 特别热：

```text
hot partition
```

会限制吞吐。

**Broker 保证顺序，Consumer 就一定按业务顺序完成吗？**

不一定。 假设消息顺序：

```text
A
B
```

Consumer 收到后：

```text
go process(A)
go process(B)
```

B 处理：

```text
10ms
```

A：

```text
2s
```

最终完成：

```text
B before A
```

所以：

```text
delivery ordering
≠
completion ordering
```

Consumer 自身并发模型也必须匹配顺序需求。 RocketMQ 顺序消费不能在 Handler 内随便开 Goroutine： Broker 按顺序：

```text
M1
M2
M3
```

交给 Consumer。 但 Handler：

```text
go process(M1)
go process(M2)
go process(M3)
```

实际完成顺序可能：

```text
M2
M3
M1
```

协议层的有序 delivery 被业务并发重新打乱。 官方 FIFO 文档也明确要求应用侧遵守 receive-process-reply 路径，避免异步处理重新造成乱序。

**Retry 会破坏消息顺序吗？**

可能。 例如：

```text
A fails
B succeeds
```

如果 B 可以继续提交：

```text
业务状态可能先看到 B
```

然后 A retry 后才成功。 因此严格顺序系统可能需要：

```text
A fail
→ block subsequent same-key messages
```

但这样 Poison Message 又会：

```text
阻塞整个 partition
```

所以：

```text
ordering
availability
throughput
```

之间存在 trade-off。

### 6.14 Consumer Lag、Backpressure、Prefetch / Batch

**Consumer Lag 为什么会上升？**

可能：

```text
Producer rate ↑
Consumer rate ↓
downstream DB slow
consumer errors/retries
hot partition
too few consumers
long processing time
```

核心公式：

```text
incoming rate > processing rate
→ lag grows
```

**Lag 本身不一定是故障**

如果 batch system：

```text
允许 30 分钟延迟
```

lag 可以存在。 关键是：

```text
lag 是否违反业务 SLA
```

**Consumer Lag 怎么处理？**

第一反应不能只有：

> 加 Consumer。

先找瓶颈。 如果：

```text
Consumer CPU saturated
```

扩容有效。 如果：

```text
DB already saturated
```

增加 Consumer：

```text
更多并发打 DB
```

反而更糟。 所以分析：

```text
consumer
→ downstream
→ bottleneck
```

整条链。

**MQ 中的 Backpressure 是什么？**

Consumer 处理不过来时：

```text
Broker queue grows
```

这是 MQ 自带的一种 buffering。 但系统仍需要：

```text
consumer concurrency limit
batch size
prefetch limit
producer throttling
```

防止：

```text
Consumer 一次拿太多消息
→ memory / DB overload
```

MQ 本身允许：

```text
Producer > Consumer
```

短期通过 backlog 吸收。 但 backlog 不是无限资源。 如果：

```text
10k/s produce
2k/s consume
```

每天都会持续增长。 最终：

```text
disk ↑
message age ↑
business freshness ↓
recovery time ↑
```

所以 MQ 只是提供：

```text
buffer
```

不是消灭 backpressure。

**Prefetch / Batch Size 为什么重要？**

如果 Consumer 一次拉：

```text
10000 messages
```

但只处理：

```text
100 concurrent
```

其余：

```text
9900
```

可能占在：

```text
consumer memory
```

还可能影响：

```text
rebalance
redelivery
fairness
```

太小又会：

```text
network overhead ↑
throughput ↓
```

所以 batch/prefetch 需要根据：

```text
processing latency
memory
downstream capacity
```

调节。

**消息堆积时应该先扩 Consumer 吗？**

先看瓶颈。

**CPU-bound Handler**

可以：

```text
increase consumers
```

直到 CPU capacity。

**DB-bound**

增加 Consumer 可能：

```text
把 DB 打爆
```

应该：

```text
optimize query
increase useful DB capacity
limit concurrency
```

**External API Rate Limited**

再多 Consumer：

```text
也不能超过 remote QPS
```

应该：

```text
rate limit
queue
controlled drain
```

所以：

```text
lag
```

是症状。 不是根因。

**消息积压恢复**

假设故障一小时：

```text
Producer continues
Consumer stops
```

产生：

```text
10 million backlog
```

Consumer 恢复后如果直接：

```text
full speed
```

可能同时：

```text
打爆 DB
打爆 Redis
打爆 third-party API
```

所以恢复需要：

```text
drain strategy
```

例如：

```text
逐步增加 consumer concurrency
dependency-aware throttle
priority restore
```

### 6.15 Consumer Rebalance

Consumer Group 中实例变化：

```text
A
B
C
```

例如 C crash。 Broker / coordinator 需要重新分配：

```text
partitions
```

给 A、B。 这叫：

```text
rebalance
```

RocketMQ 中同一个 Consumer Group：

```text
C1
C2
```

负责：

```text
Q0 Q1 Q2 Q3
```

可能分配：

```text
C1 → Q0 Q1
C2 → Q2 Q3
```

如果 C3 加入：

```text
C1 C2 C3
```

Queue assignment 需要重新调整。 这就是：

```text
rebalance
```

**为什么它可能影响延迟？**

Rebalance 期间：

```text
partition ownership changes
```

部分消费可能暂停。 如果 Consumer：

```text
频繁上线/掉线
```

会不断 rebalance，影响吞吐。 Rebalance 期间可能：

```text
某 Queue 暂停
ownership 转移
in-flight work 与新 consumer 交错
```

所以 Consumer 仍必须假设：

```text
duplicate / replay
```

可能发生。 如果 handler：

```text
执行十几分钟
```

rebalance 与长时间消费结合也会让状态更复杂。

**Rebalance 为什么会带来重复消费？**

假设 Consumer A：

```text
处理 message
DB commit
```

但 offset 尚未提交。 此时：

```text
rebalance
```

Partition 转给 B。 B 从旧 offset：

```text
重新读取 message
```

于是 duplicate。 因此即使没有 crash：

```text
rebalance
```

也可能形成 at-least-once redelivery。

**Consumer 数量是不是越多越快？**

不是。 假设 Topic：

```text
4 MessageQueues
```

Consumer Group：

```text
20 Consumers
```

在典型 Queue assignment 模型下，只有足够 Queue 可以提供并行消费分片。 额外 Consumer：

```text
可能闲置
```

所以：

```text
consumer parallelism
```

受：

```text
Queue count
```

影响。 RocketMQ 官方经典文档也用 Topic 的 Queue 在同 Group Consumer 间分配说明水平消费。

**Queue 数量是不是越多越好？**

更多 Queue：

```text
并行度潜力 ↑
```

但代价：

```text
metadata
routing
rebalance
storage index
management complexity
```

也增加。 因此应该根据：

```text
expected throughput
consumer concurrency
ordering key
broker layout
```

设计。

### 6.16 Event-driven Architecture

Event-driven Architecture：

> 系统通过“发生了什么”的事件进行松耦合协作。

例如：

```text
PaymentConfirmed
```

表达事实：

> 一笔支付已经确认。

下游：

```text
Entitlement Service
Analytics
Notification
Ledger Projection
```

都可以独立响应。

**Event 和 Command 有什么区别？**

**Command**

表达：

```text
请做某件事
```

例如：

```text
ChargePayment
SendEmail
GrantEntitlement
```

通常有：

```text
intended receiver
```

**Event**

表达：

```text
某件事已经发生
```

例如：

```text
PaymentConfirmed
EmailSent
EntitlementGranted
```

通常是过去式事实。

**为什么区分重要？**

如果事件叫：

```text
ProcessPayment
```

很难判断：

```text
这是事实
还是命令？
```

清晰语义有助于：

```text
ownership
retry
audit
```

这和前面 Agent 章节的：

```text
Command vs Fact
```

是一条共同主线。

**Command Queue 和 Event Topic 有什么区别？**

**Command Queue**

通常意味着：

```text
某个 worker 应该做这个任务
```

例如：

```text
GenerateInvoice
```

通常希望：

```text
一个 logical consumer 执行
```

**Event Topic**

意味着：

```text
事实已经发生
谁关心谁订阅
```

例如：

```text
InvoiceGenerated
```

可以：

```text
Accounting
Email
Analytics
```

同时响应。 如果命令和事件混淆：

```text
ownership
retry
fan-out
```

都会难以推理。

**一个 Event 应该包含多少数据？**

两个极端：

**Event Notification / Thin Event**

只发：

```text
payment_id = 123
```

Consumer 再查询源服务。 优点：

```text
payload small
source remains authoritative
```

缺点：

```text
extra RPC
source coupling
历史 replay 时源数据可能已改变
```

**Event-Carried State Transfer / Rich Event**

事件携带：

```text
payment_id
amount
currency
merchant
confirmed_at
...
```

Consumer 可以直接处理。 优点：

```text
less lookup
better replay independence
consumer self-contained
less synchronous dependency
```

缺点：

```text
schema larger
duplication
privacy/security considerations
schema evolution
payload duplication
stale semantics
```

没有万能答案。

**为什么 Event 应该包含发生时的 Fact，而不是只依赖查询最新状态？**

假设：

```text
T0 Payment = CONFIRMED
→ emit event

T1 Payment later = REFUNDED
```

Consumer 延迟到 T2 才处理。 如果 event 只有：

```text
payment_id
```

Consumer 查询：

```text
latest state = REFUNDED
```

已经失去：

> T0 时到底发生了什么。

如果系统需要历史事实语义：

```text
event payload
```

应该携带足够的：

```text
occurred-at fact
```

或稳定 FactRef。

**为什么 Event 要带 Schema Version？**

Event 是跨服务长期存在的 contract。 今天：

```json
{
  "event_type": "payment.success",
  "amount": "10"
}
```

未来可能变：

```json
{
  "event_type": "payment.success",
  "amount_minor": 10000000,
  "currency": "USDC"
}
```

Consumer 可能：

```text
旧版本仍在运行
历史消息仍要 replay
```

所以显式：

```text
schema_version
```

帮助：

```text
validation
migration
compatibility
```

**Event Schema Evolution 有什么原则？**

优先：

```text
additive
backward-compatible
```

例如增加 optional field。 谨慎：

```text
删除字段
改变字段语义
重用旧字段
改变金额单位
改变 enum meaning
```

特别危险的是：

```text
字段名字没变
语义变了
```

例如：

```text
amount
```

原来：

```text
major decimal
```

后来变：

```text
minor integer
```

这种 silent semantic change 很危险。

**为什么 Consumer 不应该默认所有历史消息都符合最新 Schema？**

因为 MQ 可能保留：

```text
days
weeks
months
```

消息。 代码升级后：

```text
new consumer
```

可能读到：

```text
old event
```

所以需要：

```text
version-aware decoder
```

或者明确：

```text
旧版本不可 replay
```

并接受这个边界。

**为什么 Consumer 不应该完全信任 Producer Payload？**

MQ 是系统边界。 即使 Producer：

```text
也是内部服务
```

Consumer 仍应该验证：

```text
required fields
event type
schema version
amount range
currency
identity
timestamp
```

原因：

```text
old producer
bug
manual replay
corrupted data
unexpected schema
```

都有可能。 所以 Consumer handler 第一层通常是：

```text
decode
→ validate
→ process
```

**Event Time 和 Processing Time**

**Event Time**

业务事实真正发生时间。

```text
payment confirmed at 10:01
```

**Processing Time**

Consumer 实际处理时间。

```text
consumer processes at 10:07
```

由于：

```text
queue lag
retry
network
```

二者可能不同。 所以分析业务时间线不能直接使用：

```text
DB created_at of consumer row
```

替代 event time。

**Event Ordering 应该看哪个时间？**

不能只按：

```text
timestamp
```

因为：

```text
clock skew
same timestamp
network delay
```

可能产生歧义。 如果严格要求：

```text
same aggregate ordering
```

更可靠的是：

```text
sequence number
version
partition ordering
```

例如：

```text
episode_version
1
2
3
4
```

比 wall-clock timestamp 更适合检测 stale event。

**Event Immutability**

已经发布的事实：

```text
PaymentConfirmed
```

不应该后来改成：

```text
PaymentFailed
```

如果原事实错了，更合理：

```text
PaymentConfirmationReversed
```

追加新的纠正事实。 这样保留：

```text
history
audit
causality
```

而不是重写过去。

**为什么 Event 不应该包含 mutable pointer-like 引用就结束？**

如果事件只有：

```text
facts_ref = current/payment/123
```

Consumer 稍后读取：

```text
current value
```

可能已经改变。 历史 replay 时：

```text
同一个 event
```

得到不同内容。 所以如果需要可重放性：

```text
immutable reference
version
hash
snapshot
```

比单纯：

```text
current pointer
```

更可靠。 这和后面 Catalog Snapshot 会直接关联。

**Eventual Consistency**

例如：

```text
Payment Service:
CONFIRMED
```

消息需要：

```text
200ms
```

传到：

```text
Verification Service
```

在这 200ms 内：

```text
两个服务状态暂时不同
```

最终：

```text
Verification catches up
```

这就是典型：

```text
eventual consistency
```

**关键不是“数据最终一样”**

还要问：

```text
多久最终？
如果 event 一直失败怎么办？
怎么检测 divergence？
怎么修复？
```

真正 production eventual consistency 必须有：

```text
monitoring
retry
DLQ
reconciliation
```

**为什么 Eventual Consistency 必须配合 Reconciliation？**

如果只相信：

```text
event 会最终送到
```

但实际上：

```text
schema bug
consumer bug
DLQ forgotten
operator mistake
```

状态可能永久不一致。 Reconciliation：

```text
periodically compare authoritative facts
```

发现：

```text
Payment confirmed
but entitlement missing
```

再修复。 所以：

```text
event delivery
```

负责正常路径。

```text
reconciliation
```

负责：

```text
repair convergence
```

**Message Deduplication**

Broker 或 Consumer 识别：

```text
same message identity
```

避免重复处理。 但要注意：

```text
broker dedup
```

只能减少某些重复消息。 不能替代业务 idempotency。 例如：

```text
two different event IDs
```

却代表同一个：

```text
PaymentIntent
```

Broker 看来不是 duplicate。 业务看来却是。

**Broker-level Dedup 和 Business-level Dedup 有什么区别？**

**Broker**

看：

```text
message id
```

**Business**

看：

```text
order_id + operation
payment economic key
episode + action
```

所以可靠系统可能有两层：

```text
message duplicate
→ event_id dedup

business duplicate
→ business identity dedup
```

**Trace ID、Correlation ID、Causation ID**

**Trace ID**

异步链路会打断同步调用栈。 例如：

```text
HTTP request
→ Payment Service
→ MQ
→ Verification Service
```

MQ 之后已经不是原来的 RPC call stack。 如果 event 保留：

```text
trace_id
correlation_id
```

可以继续追踪：

```text
原请求
→ event
→ consumer
```

否则故障排查会断链。

**Correlation ID 和 Event ID 有什么区别？**

**Event ID**

标识：

```text
这条事件
```

**Correlation ID**

关联：

```text
同一业务流程中的多条事件/命令
```

例如：

```text
Commerce Episode = ep-123
```

其中：

```text
event A
event B
event C
```

不同 Event ID，但：

```text
correlation_id = ep-123
```

便于重建流程。

**Causation ID 是什么？**

如果：

```text
Event B
```

是因为：

```text
Event A
```

产生，可以记录：

```text
causation_id = event_A
```

形成：

```text
A
↓ causes
B
↓ causes
C
```

对复杂 Agent / Workflow trace 非常有价值。

**Event ID、Correlation ID、Causation ID 怎么配合？**

例如：

```text
Episode ep-1
```

事件：

```text
E1 CapabilitySelected
E2 PaymentSubmitted
E3 PaymentConfirmed
```

可以：

```text
E1:
event_id=e1
correlation_id=ep-1
causation_id=request-1

E2:
event_id=e2
correlation_id=ep-1
causation_id=e1

E3:
event_id=e3
correlation_id=ep-1
causation_id=e2
```

这样可以同时知道：

```text
它是谁
属于哪个流程
由谁触发
```

**Event Storm**

不是领域设计里的 Event Storming。 这里指：

> 一个事件触发多个事件，再级联触发更多事件，形成爆炸式流量。

例如：

```text
Event A
→ B, C, D

B → E, F
C → G, H
...
```

如果每层还有 retry：

```text
流量快速放大
```

因此 event-driven 不代表：

```text
所有东西都异步事件化
```

也需要：

```text
bounded fan-out
ownership
dependency graph
```

**Event-driven Architecture 为什么可能更难 Debug？**

同步调用：

```text
A → B → C
```

请求失败时：

```text
call stack
```

相对清晰。 异步：

```text
A
→ event
→ B
→ another event
→ C
```

时间跨度可能：

```text
seconds
minutes
hours
```

还可能：

```text
retry
duplicate
reordering
```

所以必须增强：

```text
trace ID
event ID
correlation
structured logs
event store
```

否则“解耦”会变成：

```text
看不见耦合
```

**Event-driven 是否一定比 RPC 更解耦？**

不一定。 即使通过 MQ：

```text
Service B
```

如果强依赖：

```text
Service A event schema
timing
exact order
implementation detail
```

仍然高度耦合。 只是耦合从：

```text
runtime availability coupling
```

变成：

```text
schema / semantic coupling
```

所以真正的解耦依赖：

```text
stable event contract
clear ownership
limited assumptions
```

而不是用了 MQ 就自动获得。

**什么时候同步 RPC 更合适？**

如果调用者必须立即知道结果才能继续：

```text
validate permission
fetch required current state
simple low-latency query
```

RPC 更自然。 例如：

```text
CanUserPay?
```

如果必须立即决定：

```text
allow / deny
```

硬转成：

```text
publish request
wait event
```

反而复杂。

**什么时候 MQ 更合适？**

例如：

```text
notification
analytics
projection update
indexing
audit propagation
non-blocking downstream work
```

这些通常不要求：

```text
调用者同步等待结果
```

且希望：

```text
decouple availability
buffer burst
retry independently
```

MQ 更合适。 所以：

```text
RPC vs MQ
```

不是技术优劣，而是：

```text
interaction semantics
```

不同。

**为什么 Event Consumer 不应该随意修改 Producer 的状态？**

如果：

```text
Payment Service
```

拥有：

```text
Payment
```

状态。 Verification Consumer 收：

```text
PaymentConfirmed
```

应该更新自己的：

```text
PurchaseRecord
```

而不是直接连 Payment DB：

```text
UPDATE payments...
```

否则：

```text
state ownership
```

被破坏。 最终出现：

```text
谁都能改谁的数据
```

成为 distributed monolith。 事件的一个价值就是：

```text
各服务维护自己的 projection/state
```

而不是共享数据库。

### 6.17 Outbox、Inbox、Transactional Messaging、RocketMQ Transaction Message

**什么是 Transactional Messaging？**

目标：

```text
业务事务
+
消息发送
```

建立一致性。 方案可能包括：

```text
2PC-like broker transaction
transactional outbox
broker-specific transaction
```

但不同方案 failure model 差别很大。 通用面试最重要的不是背某个 RocketMQ API，而是理解：

> 两个独立 durable systems 之间的原子提交为什么困难。

**为什么 DB + MQ 本质是 Dual Write？**

因为：

```text
DB
```

和：

```text
Broker
```

是两个独立事实系统。 操作：

```text
UPDATE payment confirmed
```

和：

```text
publish PaymentConfirmed
```

不存在天然同一个：

```text
local ACID commit
```

因此必然需要额外机制：

```text
Outbox
broker transaction
CDC
reconciliation
```

之一或组合。

**Outbox Publisher 怎么工作？**

最简单：

```text
SELECT pending outbox rows
↓
publish
↓
mark published
```

但要继续问：

```text
多个 publisher 怎么并发？
publish 后 crash 怎么办？
失败怎么 retry？
如何避免一直扫描同一批？
```

所以可能需要：

```text
status
attempt count
next_retry_at
lease
batch
```

等控制字段。

**Outbox Publisher 为什么仍然可能重复发送？**

经典：

```text
T0 read outbox E
T1 publish E
T2 broker accepts E
T3 process crashes
T4 outbox not marked sent
T5 restart
T6 publish E again
```

所以：

```text
Outbox
→ no lost committed event
```

更接近真实目标。 不是：

```text
Outbox
→ physical one-time publication
```

**什么是 Inbox Pattern？**

Outbox 解决：

```text
Producer DB
→ MQ
```

可靠传播。 Inbox 解决：

```text
MQ
→ Consumer DB
```

幂等接收。 Consumer 收消息：

```text
BEGIN

INSERT inbox(event_id)

apply business update

COMMIT
```

如果：

```text
event_id already exists
```

说明已经处理过。 所以：

```text
Outbox
→ reliable producer side

Inbox
→ idempotent consumer side
```

RocketMQ 场景下： Outbox 解决 Producer：

```text
DB
→ MQ
```

Inbox 解决 Consumer：

```text
MQ
→ DB
```

Consumer 收到：

```text
event_id = E123
```

本地事务：

```text
BEGIN

INSERT inbox(event_id)
    UNIQUE

apply business state

COMMIT
```

如果重复：

```text
event_id already exists
→ return success
```

**为什么 Inbox Marker 和业务更新要放同一事务？**

错误：

```text
INSERT inbox
COMMIT

business update
```

如果：

```text
inbox committed
business update crashes
```

重投时：

```text
inbox says already processed
```

但业务效果没发生。 反过来：

```text
business update commit
then inbox insert
```

crash 后：

```text
业务已执行
但 inbox 不存在
```

重投会再执行。 所以二者必须尽量：

```text
same local transaction
```

**Outbox + Inbox 能实现什么？**

组合：

```text
Producer DB Transaction
  ├─ business state
  └─ outbox

        ↓ at-least-once

MQ

        ↓ redelivery allowed

Consumer DB Transaction
  ├─ inbox(event_id)
  └─ business state
```

得到：

```text
message can duplicate
but local business effect can be idempotent
```

这接近：

```text
effectively-once processing
```

RocketMQ 链路：

```text
Service A
business transaction
+
outbox
     ↓
RocketMQ
     ↓
Service B
inbox
+
business transaction
```

可以实现非常实用的：

```text
at-least-once transport
+
local atomicity
+
deduplication
```

最终获得：

```text
effectively-once business processing
```

而不需要假装：

```text
整个网络物理 exactly-once
```

**但如果 Consumer 还调用外部 API 呢？**

又重新出现：

```text
remote side effect crash window
```

Inbox 只能保护：

```text
Consumer local DB
```

不能自动保护：

```text
external payment/email/cloud API
```

**为什么 Exactly-once 经常只在某个边界内成立？**

例如某流处理系统可能保证：

```text
consume input
+
update internal state
+
produce output
```

在自身事务模型内 exactly-once。 但输出如果最终调用：

```text
third-party HTTP API
```

这个外部系统：

```text
不参与同一 transaction
```

exactly-once 边界就结束了。 所以面试时一定问：

```text
exactly once
within what boundary?
```

**RocketMQ Transaction Message 是什么？**

目标场景：

```text
Local DB Transaction
+
Message Publish
```

要尽量保持业务一致。 核心思路不是：

```text
Broker 和 MySQL 真正共享一个 ACID transaction
```

而是引入：

```text
half message
+
local transaction
+
transaction status check
```

协调消息最终是：

```text
commit
or
rollback
```

**RocketMQ Transaction Message 的基本流程**

概念上：

```text
Producer
  ↓
send half message
  ↓
Broker stores but not visible to consumer
  ↓
execute local transaction
  ↓
commit / rollback message
```

如果 Broker 长时间不知道结果：

```text
transaction check
```

回查 Producer 侧本地事务状态。

**Transaction Message 解决什么问题？**

典型：

```text
DB commit success
but
normal MQ send lost
```

如果直接：

```text
DB
→ MQ
```

存在 dual-write window。 Transaction Message 用协议让 Broker：

```text
先知道有这条待定 message
```

再根据本地事务结果决定是否最终投递。

**Transaction Message 是严格 Distributed Transaction 吗？**

不要这么说。 它更像：

> **RocketMQ 针对本地事务 + 消息发送一致性提供的一套事务消息协议。**

它不等于：

```text
MySQL + RocketMQ
共享同一个 XA-style global ACID transaction
```

而且 Producer 本地事务检查逻辑必须可靠。 因此：

```text
transaction message
```

仍需要：

```text
idempotent transaction check
consumer idempotency
business reconciliation
```

**RocketMQ Transaction Message 和 Transactional Outbox 怎么选？**

两种都在解决：

```text
DB state
+
MQ event
```

一致传播。

**Transaction Message**

Broker 协议参与：

```text
half message
local tx
commit/rollback
transaction check
```

优点：

```text
RocketMQ 原生支持
```

代价：

```text
与 RocketMQ 协议更耦合
transaction check logic
```

**Transactional Outbox**

本地 DB：

```text
business row
+ 
outbox row
```

同事务提交。 后续：

```text
publisher / CDC
→ RocketMQ
```

优点：

```text
本地 ACID 边界清楚
broker-agnostic
audit/replay straightforward
```

代价：

```text
outbox table
publisher
cleanup
duplicate publish
```

没有绝对赢家。 要根据：

```text
基础设施
团队经验
吞吐
一致性要求
运维复杂度
```

决定。

**为什么 Consumer 写 DB 后 ACK 是一个 Mini Dual-write？**

逻辑上 Consumer 要完成两件事：

```text
A:
commit business DB

B:
tell MQ consumption success
```

两件事无法共享一个普通 MySQL transaction。 所以：

```text
DB commit success
ACK lost
```

形成：

```text
duplicate delivery
```

解决方法不是要求永远不重复。 而是：

```text
make A idempotent
```

这样 B 可以安全重做。

**MQ 在分布式系统中真正提供的是什么？**

不是：

```text
Exactly-once magic pipe
```

而更接近：

```text
durable asynchronous handoff
+
buffering
+
fan-out
+
replay window
+
consumer scaling
```

业务正确性仍由：

```text
identity
transaction
idempotency
ordering
schema
reconciliation
```

共同建立。

### 6.18 Replay、Redelivery、Reprocessing、Projection、Side-effect

**为什么 Event Replay 很有价值？**

如果保留历史 event：

```text
Consumer bug fixed
```

可以：

```text
replay old events
```

重新构建：

```text
projection
analytics
search index
```

这也是 event-driven 系统的一大价值。 RocketMQ 的 offset + retention 模型允许在消息仍保留时进行这类回溯。

**Replay 为什么也很危险？**

如果 Consumer 不区分：

```text
rebuild projection
```

和：

```text
execute external side effect
```

replay：

```text
PaymentConfirmed
```

可能再次：

```text
send reward
call merchant
send money
```

所以 Consumer 必须明确：

```text
replay-safe?
```

**一个重要原则**

```text
Fact replay
```

适合：

```text
rebuild derived state
```

但：

```text
Fact replay
```

不应该自动重新执行原始：

```text
irreversible command
```

**Replay 和 Redelivery 有什么区别？**

**Redelivery**

通常是：

```text
Broker 因消费确认不完整
再次投递同一消息
```

属于正常 delivery semantics。

**Replay**

通常是：

```text
人为或系统主动重新读取历史消息
```

例如：

```text
重建 projection
修复 bug
重新索引
```

二者都要求幂等，但目的不同。

**什么是 Reprocessing？**

Reprocessing 更强调：

> 用新的代码/逻辑重新处理历史事实。

例如：

```text
旧 Projection 有 bug
```

修复程序后：

```text
reprocess events
```

生成正确 projection。

**为什么 Event 要尽可能 immutable？**

如果历史 event 被修改：

```text
same event_id
different content
```

reprocessing 就失去稳定事实基础。 因此事件通常倾向：

```text
append-only
immutable
```

**Replay-safe Consumer 怎么设计？**

区分：

```text
事实重建
```

和：

```text
不可逆副作用
```

例如 Projection：

```text
PaymentSucceeded
→ rebuild payment summary
```

可以通过：

```text
truncate projection
→ replay events
```

重建。 但：

```text
PaymentSucceeded
→ send real money
```

绝不能每次 replay 再执行一次。 所以 Handler 应明确：

```text
event fact
→ idempotent materialization
```

而不是：

```text
event replay
→ external side effect again
```

**什么是 Projection Consumer？**

一种 Consumer 只负责：

```text
event
→ derived read model
```

例如：

```text
PaymentConfirmed
→ update purchase_view
```

这种 Consumer 天然更适合：

```text
replay
```

因为目标状态：

```text
derived
```

可以重建。 这和：

```text
send payment
```

完全不同。

**什么是 Side-effect Consumer？**

收到 event 后执行：

```text
email
webhook
merchant callback
external API
```

这类 Consumer 的 replay 风险更高。 必须考虑：

```text
stable action identity
dedup
provider idempotency
delivery record
retry semantics
```

不能只靠 event ID。

**Webhook 为什么本质上也像 MQ Consumer？**

Webhook Provider：

```text
event
→ HTTP POST
→ your endpoint
```

如果 response timeout：

```text
provider retries
```

所以你的 webhook handler 也应该：

```text
idempotent
```

本质上和：

```text
at-least-once consumer
```

很像。 因此 MQ 知识也直接适用于：

```text
payment callback
webhook
async job
```

**为什么“至少一次消息 + 最多一次业务效果”是常见目标？**

Transport：

```text
宁愿重复
也不要永久丢失
```

所以：

```text
at-least-once
```

Business：

```text
不可重复扣款
不可重复发券
```

所以：

```text
at-most-once economic effect
```

组合：

```text
At-least-once Delivery
+
Idempotent Processing
=
Effectively-once Business Result
```

这是非常重要的一条主线。

### 6.19 RocketMQ 存储、刷盘、Producer 侧可靠性

**RocketMQ 消息是怎么存的？**

在经典 RocketMQ Broker 存储结构里，最重要的两个名字：

```text
CommitLog
ConsumeQueue
```

官方当前存储文档仍明确描述：

```text
commitlog
→ physical message files

consumequeue
→ logical queue indexes
```

消息默认持久化在 Broker 本地磁盘文件，并按保留时间清理。

**CommitLog 是什么？**

CommitLog：

> Broker 的主要物理消息存储日志。

不同 Topic / Queue 的消息可以顺序追加到物理 CommitLog。 直觉：

```text
CommitLog

M1
M2
M3
M4
M5
...
```

这种 append-oriented 设计有利于：

```text
sequential disk write
```

**ConsumeQueue 是什么？**

如果全部消息都混在：

```text
CommitLog
```

Consumer 想找：

```text
payment_events / Queue 3
```

不能每次扫描全部物理日志。 因此：

```text
ConsumeQueue
```

提供逻辑 Queue 索引。 可以粗略理解：

```text
Topic A / Queue 0
offset 0 → CommitLog location X
offset 1 → CommitLog location Y
offset 2 → CommitLog location Z
```

所以：

```text
CommitLog
→ physical storage

ConsumeQueue
→ logical consumption index
```

**为什么 RocketMQ 不给每个 Topic 单独写一套完整消息文件？**

统一顺序 Append 的思路可以降低：

```text
大量 Topic
大量 Queue
```

带来的随机磁盘写。 然后通过：

```text
ConsumeQueue
```

构建逻辑访问路径。 这是经典：

```text
write sequentially
index separately
```

设计思想。

**RocketMQ 为什么适合高吞吐写入？**

核心直觉包括：

```text
append-oriented storage
sequential write
memory mapping / page cache usage
batching
logical indexes
```

而不是：

> Java 写得快。

RocketMQ 经典实现还广泛使用 mmap 映射 CommitLog 和 ConsumeQueue 文件；官方运维文档也专门提到这两个结构的 mmap 使用。

**Sync Flush 和 Async Flush 有什么区别？**

Broker 收到 Producer 消息后：

```text
什么时候认为 send success？
```

与刷盘策略有关。

**Sync Flush**

倾向：

```text
flush durable storage
↓
ACK producer
```

更强 durability。 代价：

```text
latency ↑
throughput ↓
```

**Async Flush**

先：

```text
message accepted
↓
ACK
```

再异步批量刷盘。 优点：

```text
throughput ↑
latency ↓
```

但在某些极端 crash window：

```text
刚 ACK
还没 durable flush
```

可能有更高数据损失风险。 RocketMQ 官方经典配置文档也区分 `SYNC_FLUSH` 和 `ASYNC_FLUSH`，前者在确认 Producer 前完成刷盘，后者更偏批量异步刷盘。

**Producer Send Success 代表业务 Consumer 已经处理成功吗？**

完全不是。

```text
Producer send success
```

最多表示发送阶段达到了当前 Broker/config 所定义的成功条件。 后面还有：

```text
stored
↓
consumer fetch
↓
handler
↓
DB commit
↓
consume success
```

所以：

```text
send success
≠
business consumed
```

**Producer Retry 有什么风险？**

Producer：

```text
send message
```

如果：

```text
timeout
```

它可能不知道 Broker：

```text
到底有没有接收成功
```

Retry：

```text
可能产生 duplicate message
```

因此 Producer 侧也不能假设：

```text
send once
```

等于：

```text
broker stores once
```

这再次要求：

```text
message identity
consumer idempotency
```

**什么是 Message Retention？**

RocketMQ 不会永久保留所有消息。 消息存在：

```text
retention/storage duration
```

过期后 Broker 可以清理。 RocketMQ 5.0 官方强调消息存储时长独立于消费状态；即使消息没被消费，只要超出存储策略或磁盘压力要求，也可能被清理。 因此：

```text
MQ
```

不是永久档案数据库。

**为什么 Retention 必须大于合理恢复窗口？**

如果最长可能：

```text
Consumer outage = 24h
```

但：

```text
message retention = 6h
```

那么服务恢复时：

```text
最早 18h 消息已经不存在
```

无法靠 MQ replay 恢复。 所以 retention 是：

```text
recovery design
```

的一部分，而不是纯运维参数。

**RocketMQ 延迟消息是什么？**

延迟消息表示：

```text
现在生产
未来某个时间再可消费
```

典型用途：

```text
订单超时检查
retry delay
scheduled follow-up
```

例如：

```text
OrderCreated
↓
30 minutes later
↓
CheckOrderTimeout
```

**为什么不直接 `sleep(30m)`？**

因为：

```text
进程 crash
restart
deploy
```

都会让：

```text
sleep state
```

难以可靠恢复。 Broker-managed delay 更适合长期异步等待。

**延迟消息适合替代所有 Scheduler 吗？**

不是。 MQ 延迟消息适合：

```text
事件驱动的单次延迟任务
```

但复杂：

```text
calendar recurrence
cron
dependency scheduling
massive workflow DAG
```

可能更适合专用 scheduler/workflow system。

**MQ 和 Job Queue 有什么区别？**

有重叠。 MQ 更强调：

```text
message/event transport
pub/sub
multiple consumer groups
durability
```

Job Queue 更强调：

```text
一项任务
→ 某个 worker 执行
→ task lifecycle
```

例如：

```text
PaymentConfirmed
```

更自然是 Event。

```text
GenerateMonthlyReport
```

更像 Job。 但工程实现可能仍使用同一个 RocketMQ 基础设施。 关键在：

```text
semantic contract
```

而不是产品名称。

**Long-running Agent Task 应该怎样和 MQ 结合？**

不要：

```text
RocketMQ message
↓
Consumer callback
↓
Agent runs 3 hours
↓
ACK
```

更合理：

```text
message
↓
create durable task / episode
↓
commit
↓
ConsumeSuccess

Worker later:
resume durable task
```

这样：

```text
MQ
```

承担：

```text
trigger / wake-up
```

而：

```text
durable workflow state
```

由自己的 runtime 保存。 这对 Agent Runtime 尤其重要。

**Consumer Retry 和 Business Retry 是一回事吗？**

不是。

**Consumer Retry**

```text
同一消息重新投递
```

例如：

```text
DB unavailable
```

**Business Retry**

业务状态机明确产生：

```text
新的 attempt
```

例如支付：

```text
PaymentAttempt 1 FAILED
↓
policy allows
↓
PaymentAttempt 2
```

这两者身份和审计意义不同。 如果直接把：

```text
RocketMQ redelivery
```

当成：

```text
创建新的业务支付尝试
```

很容易重复 side effect。

**为什么 Message Retry 必须保持 Business Identity？**

第一次消息：

```text
event_id = E123
payment_id = P456
```

Retry：

```text
仍然是同一逻辑 event / command
```

不能重新生成：

```text
payment_id = P999
```

否则 Consumer / downstream：

```text
无法知道它是 retry
```

会把它当成新的业务动作。

**MQ 能不能解决服务间一致性？**

MQ 可以帮助实现：

```text
eventual consistency
```

例如：

```text
Payment DB
= CONFIRMED

↓ event

Entitlement DB
eventually = ACTIVE
```

但存在时间窗口：

```text
Payment confirmed
Entitlement not yet processed
```

所以业务必须明确：

```text
中间状态是否合法？
用户此时看到什么？
如何恢复？
```

MQ 不是让两个数据库：

```text
同一瞬间一致
```

而是支持：

```text
可靠地最终趋同
```

**Eventual Consistency 为什么必须有 Reconciliation？**

即使设计：

```text
Outbox
RocketMQ
Inbox
```

仍可能存在：

```text
software bug
DLQ
retention expiry
operator mistake
unexpected schema
```

所以高价值业务需要定期：

```text
source facts
vs
derived state
```

对账。 例如：

```text
confirmed payments
-
active entitlements
```

找：

```text
missing projection
```

然后修复。

**MQ Reconciliation 和 Message Retry 有什么区别？**

Message Retry：

```text
已知这条 message 失败
→ 重试它
```

Reconciliation：

```text
从业务事实重新检查
系统是否已经收敛
```

即使消息：

```text
已经永久丢失
```

Reconciliation 仍可能通过：

```text
source of truth
```

发现不一致。 所以高可靠系统通常：

```text
Retry
+
DLQ
+
Reconciliation
```

三层都有。

### 6.20 经典 Failure Timeline 与完整可靠链路

**RocketMQ 消费最重要的一条 Failure Trace**

```text
Producer
   ↓
Broker persists event E1
   ↓
Consumer receives E1
   ↓
DB commit business effect
   X
consumer crashes
   ↓
RocketMQ redelivers E1
   ↓
Consumer sees duplicate
```

设计目标不是幻想：

```text
E1 永不重复
```

而是让：

```text
process(E1)
process(E1)
```

最终等价于：

```text
process(E1)
```

一次。 所以正确公式：

```text
At-least-once Delivery
        +
Stable Event Identity
        +
Local Transaction
        +
Unique Constraint / Inbox
        =
Effectively-once Local Business Effect
```

如果里面还有：

```text
remote irreversible side effect
```

还需要继续增加：

```text
remote idempotency
reconciliation
```

**RocketMQ Producer 侧最重要的一条 Failure Trace**

```text
DB transaction commits
      ↓
need publish event
      X
process crashes
```

得到：

```text
DB fact exists
MQ event missing
```

解决：

```text
Transactional Outbox
```

或者在适合场景下：

```text
RocketMQ Transaction Message
```

**MQ 的经典 Failure Timeline**

必须会画。

```text
T0
Producer commits business state

T1
Producer publishes Event E

T2
Broker stores E

T3
Consumer receives E

T4
Consumer commits DB state

T5
Consumer crashes

T6
ACK not sent

T7
Broker redelivers E

T8
Consumer detects duplicate

T9
ACK success
```

这里分别需要：

```text
T0 → T1
Outbox / reliable publication

T4 → T6
Idempotent consumer / Inbox

T7
At-least-once semantics

T8
Stable Event Identity
```

把这条 timeline 理解以后，大部分 MQ 八股都能从它推导。

**DB + MQ 的完整可靠链路**

生产端：

```text
BEGIN
  business state
  outbox(event_id)
COMMIT
```

Publisher：

```text
outbox
→ MQ
```

可能重复发送。 Broker：

```text
durably stores
→ delivers
```

Consumer：

```text
BEGIN
  inbox(event_id)
  local business state
COMMIT
```

然后：

```text
ACK
```

所以：

```text
Producer local atomicity
+
at-least-once transport
+
Consumer local idempotency
```

组合出：

```text
eventually convergent business workflow
```

而不是依赖某个神奇：

```text
exactly_once=true
```

配置项。

### 6.21 高频错误设计

**收到消息就 ACK**

```text
receive
→ ACK
→ process
```

风险：

```text
ACK 后 crash
→ 消息不会回来
→ business effect lost
```

关键业务通常不能这样。

**业务成功后一定不会重复消费**

```text
DB commit
```

和：

```text
ACK
```

不是一个原子操作。 中间 crash：

```text
DB success
ACK missing
```

必然可能 redelivery。 所以：

```text
consumer must be idempotent
```

不是优化，而是设计前提。

**用了 MQ 的 Exactly-once 就不用做幂等**

即使 Broker 在自己的边界提供强语义：

```text
consumer
```

最终可能调用：

```text
MySQL
Redis
HTTP API
Payment Provider
```

外部系统未必参与同一事务。 所以仍然要定义：

```text
exactly-once boundary
```

不能笼统说：

```text
整个业务 Exactly-once
```

**消息处理失败就无限 Retry**

Permanent error：

```text
invalid schema
```

retry 10000 次也不会变好。 还会：

```text
consume worker
fill logs
increase lag
```

所以：

```text
bounded retry
→ DLQ
→ repair
```

才完整。

**DLQ 就等于处理完成**

DLQ 只是：

```text
故障隔离
```

如果从来没人看：

```text
永久业务数据缺失
```

所以必须监控：

```text
DLQ size
age
failure reason
```

并有 repair/runbook。

**顺序 Topic 就一定顺序处理**

Broker：

```text
A before B
```

Consumer：

```text
parallel handler
```

可能：

```text
B commits before A
```

所以顺序需求必须贯穿：

```text
routing
delivery
consumer concurrency
commit
retry
```

整条链。

**Consumer Lag 高就加机器**

如果真正瓶颈：

```text
MySQL lock contention
```

加 Consumer：

```text
更高 DB concurrency
→ more contention
→ slower
```

应该先：

```text
find bottleneck
```

再决定是否扩容。

**Event Payload 越完整越好**

Payload 大：

```text
network
storage
serialization
privacy exposure
schema coupling
```

都增加。 而太小：

```text
consumer repeatedly calls producer
```

又增加 runtime coupling。 所以 Event Data 应围绕：

```text
consumer autonomy
audit/replay need
privacy
contract stability
```

设计。

**一个 Topic 放所有 Event 最省事**

例如：

```text
all_events
```

里面：

```text
payment
catalog
auth
notification
agent trace
```

短期简单。 长期：

```text
retention
permission
consumer routing
schema governance
throughput
```

全部纠缠。 Topic 设计应该考虑：

```text
business domain
security boundary
retention
throughput
ordering
consumer ownership
```

**每个 Event 都建一个 Topic**

另一个极端：

```text
payment_created
payment_confirmed
payment_failed
payment_refunded
...
```

Topic 数量暴涨。 管理：

```text
ACL
monitoring
deployment
retention
```

非常复杂。 通常应在：

```text
domain-level topic
+
event_type
```

之间平衡。

**Event Timestamp 可以保证顺序**

两个机器：

```text
clock skew
```

A：

```text
10:00:01.100
```

B：

```text
10:00:01.050
```

真实顺序可能相反。 所以需要严格 aggregate ordering 时：

```text
sequence/version
```

比纯 wall clock 更可靠。

**Replay 就是从头再消费一遍**

如果 Consumer 包含：

```text
send email
charge money
grant reward
```

直接 replay 会重新 side effect。 所以应该区分：

```text
rebuildable projection consumer
```

和：

```text
irreversible effect consumer
```

后者必须有更严格：

```text
idempotency / replay mode
```

**MQ 有 Retry，所以 Consumer 不用幂等**

正相反。 因为：

```text
有 Retry
```

所以：

```text
更必须幂等
```

Retry 的存在意味着：

```text
same logical message
```

本来就可能再次到达。

**只要 Handler 返回 Success，就不会重复**

重复可能发生在：

```text
success response 到 Broker 之前 crash
network issue
rebalance
replay
manual offset reset
```

所以业务不能把：

```text
callback called once
```

当 invariant。

**Consumer 报错就全部 RetryLater**

如果：

```text
schema_version unsupported
```

无论 retry：

```text
1 次
100 次
10000 次
```

都不会自行修复。 这种 poison message 会：

```text
污染日志
消耗吞吐
延迟其他消息
```

应该明确：

```text
transient
vs
permanent
```

错误分类。

**DLQ 没有监控**

如果没有：

```text
alert
dashboard
repair procedure
```

DLQ 相当于：

```text
silent failure archive
```

而不是 resilience feature。

**Consumer 越多越快**

真正 throughput：

```text
min(
  queue parallelism,
  consumer CPU,
  DB capacity,
  RPC capacity,
  external API capacity
)
```

只扩 Consumer：

```text
不一定提高最小项
```

甚至可能把依赖打爆。

**消息顺序必须全局保证**

全局顺序：

```text
parallelism ↓
availability / throughput cost ↑
```

大多数业务实际只需要：

```text
per aggregate ordering
```

例如：

```text
per order
per account
```

而不是所有订单相互排序。

**Producer Send Success = 业务完成**

真实链路：

```text
Producer send
→ Broker store
→ Consumer fetch
→ Consumer process
→ DB commit
```

任何一个阶段都不同。 所以：

```text
MQ send success
```

只能回答发送阶段。

**RocketMQ 可以代替所有数据库状态**

MQ 保存：

```text
event stream
```

但业务经常仍需要快速回答：

```text
当前状态是什么？
当前余额多少？
当前 entitlement 是否有效？
```

这通常需要：

```text
DB / Projection
```

MQ 不应被当成普通 point-query database。

### 6.22 本章高频对比

| 概念 A | 概念 B | 核心区别 |
| --- | --- | --- |
| Producer | Consumer | 产生消息 vs 处理消息 |
| Broker | NameServer | 消息存储/传输 vs 路由注册 |
| Topic | Event Type | 路由类别 vs 业务语义 |
| Topic | MessageQueue / Partition | 逻辑流 vs 并行/顺序单元 |
| Consumer | Consumer Group | 单实例 vs 一组协作实例 |
| Clustering | Broadcasting | 组内分担消息 vs 每实例全量消费 |
| PushConsumer | Pull-style Consumer | SDK 管理交付回调 vs 应用主动拉取 |
| ACK | Offset | 消费确认动作 vs 消费进度位置 |
| Message Offset | Consumer Offset | 消息位置 vs Group 消费进度 |
| Queue Count | Consumer Count | 可并行分区数量 vs 处理实例数量 |
| At-most-once | At-least-once | 可能丢不重复 vs 不轻易丢但可重复 |
| At-least-once | Exactly-once Effect | 传输至少一次 vs 业务效果等价一次 |
| Delivery Once | Business Once | 消息传输次数 vs 业务效果次数 |
| Event ID | Business Key / Idempotency Key | 消息实例身份 vs 逻辑业务身份 |
| Message Key | Idempotency Key | 查询/索引标识 vs 业务去重身份 |
| Retry Queue | DLQ | 稍后重试 vs 隔离长期失败 |
| Retry | DLQ | 自动再尝试 vs 重试耗尽后的隔离 |
| Retry | Replay | 单消息失败再投递 vs 主动重新消费历史 |
| Retry | Reconciliation | 再处理消息 vs 从事实层检查系统收敛 |
| Transient Error | Permanent Error | 可能恢复 vs 重试通常无意义 |
| Delivery Order | Completion Order | 到达顺序 vs 业务提交顺序 |
| Global Order | Per-key Order | 所有消息有序 vs 同实体有序 |
| Ordered Delivery | Global Order | 某组/Queue 有序 vs 所有消息严格排序 |
| Consumer Lag | Queue Size | 消费进度落后 vs Broker 存量概念 |
| Lag | Backpressure | 消费落后结果 vs 容量不足反馈机制 |
| CommitLog | ConsumeQueue | 物理消息日志 vs 逻辑消费索引 |
| Sync Flush | Async Flush | durability 更强/延迟更高 vs 吞吐更高 |
| Tag | Topic | Topic 内细分类 vs 大类消息通道 |
| Command | Event | 请求做事 vs 已发生事实 |
| Event Time | Processing Time | 事实发生时间 vs Consumer 处理时间 |
| Outbox | Inbox | Producer 可靠发布 vs Consumer 幂等接收 |
| Redelivery | Replay | Broker 重投 vs 主动重放历史 |
| Replay | Reprocessing | 重放消息 vs 用新逻辑重算历史 |
| Event Notification | Event-carried State | 小引用事件 vs 携带较完整事实 |
| Correlation ID | Causation ID | 属于同一流程 vs 谁导致了谁 |
| RPC | MQ | 同步请求/响应 vs 异步消息协作 |
| MQ | Job Queue | 事件/消息传输模型 vs 任务执行语义 |
| Consumer Retry | Business Retry | 同消息重投 vs 新业务 attempt |
| Projection Consumer | Side-effect Consumer | 重建派生状态 vs 执行外部动作 |
| Delay Message | Scheduler | 延迟事件投递 vs 通用调度系统 |
| Transaction Message | Outbox | Broker 协议协调本地事务 vs DB 本地事务记录待发事件 |

### 6.23 面试前一分钟速记

```text
RocketMQ 核心：

Producer
NameServer
Broker
Topic
MessageQueue
ConsumerGroup
Consumer

NameServer：
路由注册，
不存业务消息主体。

Topic：
逻辑消息类别。

MessageQueue：
Topic 的分区和并行消费单元，
Queue 内有 offset 和局部顺序。

ConsumerGroup：
一组相同消费语义的 Consumer。

Clustering：
组内分担。

Broadcasting：
每个实例都处理全部。

PushConsumer：
应用看到 listener callback，
不要简单理解成 Broker 直接 push handler。

Message Offset：
消息在 Queue 的位置。

Consumer Offset：
Group 消费进度。

Consumer success
不等于消息物理删除。

At-most-once：
0 或 1 次，
可能丢。

At-least-once：
1 次或更多，
可能重复。

Exactly-once 必须问：
哪个边界的 exactly once？

业务系统更常追求：
effectively-once business effect。

Consumer 为什么必须幂等？

因为：
DB commit
→ ACK 前 crash
→ redelivery。

EventID
≠
Business Idempotency Key。

ACK 应该在 durable business success 后。

Poison Message：
重复 retry 不会变好。

Retry 必须：
bounded
backoff
DLQ。

DLQ 不是垃圾桶，
需要 repair / replay workflow。

顺序要区分：
global
partition
per-key。

一般顺序是：
per Queue / per MessageGroup，
不是全局顺序。

Broker 顺序
≠
Consumer commit 顺序。

Consumer Lag：
incoming > processing
就会增长。

CommitLog：
物理消息存储。

ConsumeQueue：
逻辑队列索引。

DB + MQ：
dual-write problem。

解决：
Transactional Outbox
或适合场景下 RocketMQ Transaction Message。

Consumer：
Inbox / UNIQUE(event_id)
实现幂等。

Outbox + RocketMQ + Inbox
典型目标不是物理 exactly-once，
而是 effectively-once business effect。

Outbox：
解决 Producer DB → MQ dual-write。

Inbox：
解决 Consumer duplicate processing。

Outbox 仍可能重复 publish。

Inbox 只能保证 Consumer 本地 DB，
不能自动保证 remote side effect。

Replay 适合重建 Projection，
不能盲目重新执行不可逆 Action。

Retry
≠
Replay
≠
Reconciliation。

MQ 可以缓冲峰值，
但不能消灭容量限制。

Lag 一直增长：
produce > consume，
必须找真正瓶颈。

常见目标：
At-least-once message delivery
+
Idempotent Consumer
+
At-most-once business effect。
```

### 6.24 StablePay 映射

本章仍只做轻量映射。

```text
payment_events
→ domain-level event topic

payment.success / payment.failed
→ Event Type

event_id
→ message/event identity

idempotency_key / tx_id
→ 更接近业务稳定 identity

Verification Consumer
→ downstream event consumer

ConsumeRetryLater
→ transient processing failure 进入重投路径

PurchaseRecord event_id dedup
→ idempotent consumer 基础

schema_version
→ event contract evolution boundary
```

当前 StablePay 的 Verification Consumer 可以映射为：

```text
payment-service
    ↓
Topic: payment_events
    ↓
RocketMQ
    ↓
verification_group
    ↓
PushConsumer
    ↓
decode PaymentEvent
    ↓
Validate
    ↓
persist PurchaseRecord
```

Consumer 返回语义：

```text
成功
→ ConsumeSuccess

decode / schema / persist failure
→ ConsumeRetryLater
```

这正好对应本章的：

```text
PushConsumer
Retry
At-least-once
Idempotent Consumer
```

项目当前 Consumer 已经显式检查：

```text
EventID
IdempotencyKey
TxID
AgentDID
SkillDID
SchemaVersion
Amount
Currency
```

并在持久化时对：

```text
EventID
```

做重复检查。 当前项目中，Payment Event 已经要求：

```text
event_id
idempotency_key
tx_id
agent_did
skill_did
amount_minor
currency
schema_version
```

这种设计非常适合在 01 中继续追问：

```text
为什么 event_id 和 idempotency_key 都要存在？

为什么 DB 写成功后 Consumer 返回前 crash
仍可能收到同一 event？

为什么 FindByEventID + Create 仍要处理并发 race？

为什么已经有 Consumer 去重
仍不能证明 Payment Side Effect Exactly-once？
```

02 在这里只保留通用结论：

```text
message identity
```

用于消息去重；

```text
business identity
```

用于业务幂等； 两者不能互相替代。 另外，当前系统的 DB → RocketMQ 路径是否已经具备完整 Transactional Outbox，应继续作为 01 的项目边界题，而不是在 02 中把“应该有的通用架构”写成“项目已经实现”。

**StablePay 当前 RocketMQ 特别值得准备的 5 个项目追问**

这些题应该主要在 01 回答，但 02 学完后应该能立即识别。

**1. 为什么 `payment_events` Consumer 选择 `ConsumeRetryLater`？**

因为：

```text
当前业务处理没有成功
```

不能直接：

```text
ConsumeSuccess
```

吞掉消息。 但进一步必须区分：

```text
transient failure
vs
permanent malformed event
```

否则 malformed event 可能成为 poison message。

**2. 为什么重复消费不能只靠第一次 `FindByEventID`？**

因为：

```text
Consumer A:
Find → missing

Consumer B:
Find → missing
```

然后并发：

```text
Create
```

仍有 race。 最终应依赖：

```text
database uniqueness
```

并将：

```text
duplicate create
```

解释成已处理。

**3. 为什么 Payment Event 需要 `schema_version`？**

因为：

```text
Producer
Consumer
```

不会保证同时部署。 消息可能还在 Broker backlog 时：

```text
Consumer 已升级
```

或反过来。 所以 schema 必须成为：

```text
explicit contract
```

**4. 为什么支付成功事件不能只传 `tx_id` 再查最新 Payment？**

因为：

```text
event
```

表达的是：

> 某个时间点已经发生的事实。

而：

```text
latest payment state
```

可能在 Consumer 真正处理时已经改变。 是否用：

```text
rich immutable event
```

还是：

```text
FactsRef + authoritative query
```

必须明确语义。

**5. 当前为什么仍值得考虑 Outbox？**

即使 Consumer 已经做到：

```text
idempotent redelivery
```

Producer 侧仍有另一个方向：

```text
local payment state commit
        ↓
publish RocketMQ
```

如果两个动作之间 crash：

```text
Payment fact exists
Event missing
```

Consumer 幂等无法修复：

```text
根本没有收到事件
```

所以：

```text
Consumer idempotency
```

解决：

```text
duplicate
```

而：

```text
Outbox / transaction message
```

解决：

```text
missing publication window
```

两个方向不要混。

### 6.25 本章学习优先级

### 第一轮：P0 —— RocketMQ 本体与 MQ 基本正确性

必须立即会：

```text
RocketMQ 为什么用
Producer
NameServer
Broker
Topic
MessageQueue
ConsumerGroup
Cluster / Broadcast
PushConsumer
Offset
ConsumeSuccess / Retry
At-most-once
At-least-once
Exactly-once 概念边界
Consumer Idempotency
Retry
DLQ
顺序消息
Tag / Key
Consumer Lag
Command vs Event
```

这是你项目用了 RocketMQ 后：

> **面试官有权默认你会的部分。**

### 第二轮：P1 —— 真正消费正确性

重点：

```text
DB commit → ACK crash window
Consumer idempotency
EventID vs BusinessID
Poison Message
Transient / Permanent Failure
Retry policy
Ordering
Per-key Partition
Rebalance
Schema Evolution
Event Time
Trace / Correlation
Backpressure
CommitLog / ConsumeQueue
Sync / Async Flush
Consumer Lag
Replay
```

做到能够现场画：

```text
T0
T1
T2
T3
crash
redelivery
```

解释为什么重复发生。

### 第三轮：P2 —— 高质量后端 / Infra / Agent Runtime

重点：

```text
Transactional Outbox
Inbox Pattern
Dual Write
RocketMQ Transaction Message
Outbox vs Transaction Message
Effective Exactly-once
Replay / Reprocessing
Projection Consumer
Side-effect Consumer
Reconciliation
Event Immutability
Causation
Event Storm
Recovery from backlog
Retention as recovery boundary
long-running task + MQ
Event vs Command
Rich vs Thin Event
eventual consistency
```

最终不要只回答：

> “MQ 可以异步、削峰、解耦，RocketMQ 支持重试和死信队列。”

更完整的理解应该是：

> RocketMQ 把 Topic 拆成多个 MessageQueue，以 Queue 提供水平分区和局部有序流；同一 Consumer Group 的实例通过 Queue 分配扩展消费能力。业务通常采用 at-least-once 的可靠消费模型，因此 Consumer 必须用稳定 EventID、数据库事务和唯一约束建立幂等；DB commit 后消费确认前 crash 会导致合法 redelivery。Producer 侧则存在 DB commit 与消息 publish 的 dual-write window，可以通过 Transactional Outbox 或适合场景下的 RocketMQ Transaction Message 缩小。Retry、DLQ 和 Replay 解决的是消息传输与处理恢复，而高价值业务还需要 reconciliation 从权威事实层验证系统最终是否真正收敛。消息可以重复、延迟甚至乱序，但业务 invariant 不能因此改变。

## 7. 分布式系统与可靠性

前面几章分别讨论了：

```text
Go
→ 单进程内并发

HTTP / RPC
→ 跨进程调用

MySQL
→ 本地事务与并发控制

Redis
→ 缓存与短期协调

RocketMQ
→ 异步传播与至少一次消费
```

这一章要回答的是：

> **当一次业务动作同时跨越这些组件以后，正确性到底怎么建立？**

典型调用链：

```text
Client
  ↓
API Gateway
  ↓
Service
  ↓
MySQL commit
  ↓
Remote Payment API
  ↓
RocketMQ
  ↓
Consumer
  ↓
Another DB
```

任何一个箭头之间都可能：

```text
timeout
crash
duplicate
retry
network partition
stale read
partial success
```

所以分布式系统最重要的认知不是：

> “如何让所有步骤永远同时成功？”

而是：

> **在无法获得全局原子性的情况下，如何定义清楚 invariant，并让系统在重复、延迟、部分失败和恢复之后仍然收敛到正确状态。**

### 7.1 [P0] 什么是幂等？

一个操作是幂等的，指：

```text
执行一次
```

和：

```text
执行多次
```

在定义的业务层面最终效果等价。 数学上常写：

```text
f(f(x)) = f(x)
```

但工程里最重要的是：

> **先说明“哪个效果”应该保持不重复。**

例如：

```text
PUT user.name = "Alice"
```

重复执行：

```text
name 仍然是 Alice
```

比较自然地幂等。 而：

```text
balance += 100
```

执行两次：

```text
+200
```

就不幂等。

### 7.2 [P0] 幂等是不是意味着代码只执行一次？

不是。 这点非常重要。 系统可能真实执行：

```text
handler call #1
handler call #2
handler call #3
```

但最终：

```text
只产生一笔订单
只扣一次款
只发放一次权益
```

所以：

```text
physical execution count
≠
business effect count
```

分布式系统更现实的目标通常是：

```text
allow duplicate execution
+
prevent duplicate effect
```

### 7.3 [P0] Idempotency Key 是什么？

Idempotency Key 用来告诉服务：

> 这些多次请求其实是同一个逻辑操作。

例如：

```http
POST /payments

Idempotency-Key: pay-order-123
```

第一次：

```text
create payment
→ store result
```

第二次：

```text
same key
→ return stored result
```

而不是：

```text
create another payment
```

### 7.4 [P1] Idempotency Key 应该绑定什么？

不能只存：

```text
key → success
```

还要考虑请求内容。 例如：

```text
key = K
amount = 10
```

第一次成功。 攻击者或 bug 第二次：

```text
key = K
amount = 1000
```

如果系统直接返回第一次结果：

```text
可能掩盖参数冲突
```

所以常见设计：

```text
IdempotencyKey
+
RequestFingerprint
```

第一次：

```text
K → hash(request A)
```

第二次：

```text
same K
same hash
→ replay existing result
```

如果：

```text
same K
different hash
```

应该：

```text
reject conflict
```

### 7.5 [P1] Request ID 和 Idempotency Key 有什么区别？

**Request ID**

标识：

```text
这一次网络请求
```

Retry 后可能变成：

```text
request-1
request-2
```

**Idempotency Key**

标识：

```text
同一个逻辑业务 command
```

Retry 应继续：

```text
same idempotency key
```

所以：

```text
Request ID
→ transport / tracing identity

Idempotency Key
→ logical command identity
```

两者不能混用。

### 7.6 [P1] Event ID、Idempotency Key、Economic Identity 有什么区别？

可以分三层。

**Event ID**

```text
这一条消息是谁
```

例如：

```text
evt-001
```

**Idempotency Key**

```text
这一条 API / command 的逻辑身份
```

例如：

```text
request-pay-order-123
```

**Economic Identity**

表达：

> 哪些请求在业务上属于“同一笔经济效果”。

例如：

```text
agent A
+
merchant M
+
quote Q
+
episode E
```

组合决定：

```text
这就是同一笔支付
```

即使系统：

```text
换了 request ID
换了 event ID
发生 redelivery
```

Economic Identity 仍不应该变。

### 7.7 [P0] Nonce 和 Idempotency Key 有什么区别？

Nonce 主要解决：

```text
replay attack
```

语义：

> 这个请求凭证不能被再次使用。

Idempotency Key 主要解决：

```text
safe retry
```

语义：

> 同一个逻辑请求可以再次到达，但不应该重复产生业务效果。

因此：

```text
Nonce
→ reject repeated authenticated request

Idempotency Key
→ accept repeated logical command safely
```

看起来都处理重复，但方向几乎相反。

### 7.8 [P0] Timeout 是否代表操作失败？

不代表。 Timeout 只说明：

> 调用方在规定时间内没有收到确定结果。

例如：

```text
Client
→ Payment Service
→ charge succeeds
→ response lost
→ Client timeout
```

真实业务状态：

```text
SUCCESS
```

客户端看到：

```text
TIMEOUT
```

所以：

```text
timeout
≠
failed
```

### 7.9 [P0] 什么是 Unknown Outcome？

Unknown Outcome：

> 当前系统不知道外部操作究竟成功还是失败。

例如：

```text
T0 send payment request

T1 remote receives

T2 remote possibly commits

T3 network breaks

T4 local timeout
```

本地只能知道：

```text
没有拿到确定响应
```

不能安全写：

```text
FAILED
```

也不能安全写：

```text
SUCCESS
```

因此需要一等状态：

```text
UNKNOWN
```

### 7.10 [P1] 为什么 UNKNOWN 必须是一等状态？

如果强行把：

```text
timeout
```

映射为：

```text
FAILED
```

后面业务可能：

```text
retry payment
```

结果：

```text
第一次其实成功
第二次又成功
→ double charge
```

如果强行当：

```text
SUCCESS
```

第一次其实没执行：

```text
系统又错误发放权益
```

所以：

```text
UNKNOWN
```

是在承认：

> **信息不足本身就是一种真实系统状态。**

### 7.11 [P0] 什么是 Blind Retry？

Blind Retry：

> 不确认前一次结果，直接重新执行。

例如：

```text
payment timeout
→ submit payment again
```

如果前一次其实：

```text
success
```

就可能重复 side effect。 因此：

```text
blind retry
```

对：

```text
read-only request
```

往往风险低。 对：

```text
irreversible mutation
```

风险很高。

### 7.12 [P0] 什么是 Reconciliation？

Reconciliation：

> 根据权威事实重新检查系统状态，并修复本地的不确定或不一致状态。

例如 PaymentIntent：

```text
state = UNKNOWN
tx_ref = X
```

后台：

```text
query provider X
```

结果：

```text
confirmed
```

本地：

```text
UNKNOWN
→ CONFIRMED
```

或者：

```text
definitely absent / failed
→ FAILED
```

### 7.13 [P1] Retry 和 Reconciliation 的区别是什么？

**Retry**

```text
再做一次
```

**Reconciliation**

```text
先确认前一次到底发生了什么
```

对没有副作用的查询：

```text
retry
```

很自然。 对支付：

```text
timeout
→ reconcile
```

往往比：

```text
timeout
→ resubmit
```

安全。

### 7.14 [P1] Reconciliation 需要什么前提？

必须有稳定身份能查询。 例如：

```text
provider request ID
transaction hash
payment intent ID
idempotency key
economic key
```

否则只剩：

```text
“刚才好像付过一笔 10 USDC”
```

无法可靠判断是哪一笔。 因此：

```text
stable identity
```

是 reconciliation 的基础。

### 7.15 [P1] Reconciliation 只用于支付吗？

不是。 任何跨系统状态都可能需要。 例如：

**Inventory**

```text
order says reserved
inventory system says no reservation
```

**Cloud Resource**

```text
local DB says CREATING
cloud API may already have created VM
```

**Email**

```text
local says pending
provider may have accepted send
```

**Agent Tool**

```text
runtime timeout
external tool may already have changed state
```

所以：

```text
reconciliation
```

是通用 distributed recovery pattern。

### 7.16 [P0] 什么是 Eventual Consistency？

Eventual Consistency：

> 系统不同副本或不同服务在短时间内可以不一致，但如果没有新的变化并且同步机制继续工作，最终会收敛到一致状态。

例如：

```text
Payment DB
CONFIRMED
```

但：

```text
Entitlement DB
PENDING
```

RocketMQ event 还没消费。 稍后：

```text
Entitlement
ACTIVE
```

### 7.17 [P1] Eventual Consistency 不等于“迟早应该会好”吧？

当然不是。 真正的 eventual consistency 需要：

```text
明确传播机制
明确 retry
明确 identity
明确 convergence rule
明确 recovery
```

否则：

```text
“消息应该最终到了吧”
```

不是一致性模型。 必须回答：

```text
如果事件丢了怎么办？
如果重复怎么办？
如果顺序乱了怎么办？
如果 consumer bug 了怎么办？
如果 DLQ 没处理怎么办？
```

### 7.18 [P0] Strong Consistency 是什么？

粗略来说：

> 对外表现出的读取结果满足更强的最新写入可见性要求。

例如写入：

```text
balance = 100
```

完成后，后续读取不应该看到旧值：

```text
balance = 80
```

但“Strong Consistency”是一个宽泛说法。 更精确的系统设计中需要继续说明：

```text
linearizability?
serializability?
read-your-writes?
monotonic reads?
```

### 7.19 [P1] 什么是 Read-your-writes？

用户刚刚：

```text
UPDATE profile
```

随后自己读取：

```text
GET profile
```

应该至少看到：

```text
自己刚写的新值
```

这叫：

```text
read-your-writes consistency
```

即使系统整体不是严格 linearizable，也可能单独提供这种 session guarantee。

### 7.20 [P1] 什么是 Monotonic Read？

如果用户已经看到：

```text
version 10
```

下一次读取不应该退回：

```text
version 9
```

即：

```text
read version
不会倒退
```

在多副本 eventual consistency 系统中，这类保证对用户体验很重要。

### 7.21 [P1] Replication 是什么？

Replication：

> 把数据复制到多个节点。

目的可能是：

```text
高可用
读扩展
容灾
地理分布
```

例如：

```text
Primary
  ↓
Replica A
Replica B
```

但复制会带来：

```text
replication lag
failover
stale read
```

等问题。

### 7.22 [P1] Replication Lag 会造成什么？

写：

```text
Primary:
state = CONFIRMED
```

Replica 尚未同步：

```text
Replica:
state = PENDING
```

用户：

```text
write primary
→ immediately read replica
```

可能看到旧值。 所以：

```text
read replica
```

提高读能力的同时，也会影响一致性语义。

### 7.23 [P0] Readiness 和 Liveness 有什么区别？

**Liveness**

回答：

```text
这个进程还活着吗？
```

如果失败：

```text
可以考虑 restart
```

**Readiness**

回答：

```text
这个实例现在适合接业务流量吗？
```

例如：

```text
process alive
```

但：

```text
critical dependency not ready
```

可能：

```text
liveness = true
readiness = false
```

### 7.24 [P1] 为什么 Readiness 不能等于“端口开着”？

服务：

```text
HTTP port = listening
```

但：

```text
DB migration incomplete
critical config missing
RPC clients not ready
```

如果 Load Balancer 已经导流：

```text
大量请求立即失败
```

所以 readiness 应表达：

> **是否已经满足接真实业务请求的条件。**

### 7.25 [P0] Graceful Shutdown 为什么重要？

实例退出前如果直接：

```text
kill process
```

可能：

```text
正在处理请求
正在消费 MQ
正在写 DB
正在执行 side effect
```

全部突然终止。 更合理：

```text
readiness false
→ stop accepting new work
→ stop new MQ consumption
→ wait in-flight
→ cancel workers
→ close resources
→ exit
```

减少 crash window。

### 7.26 [P1] Graceful Shutdown 能保证零失败吗？

不能。 如果机器：

```text
power loss
kernel panic
SIGKILL
```

没有 graceful window。 所以：

```text
graceful shutdown
```

只是减少计划内退出造成的问题。 真正 correctness 仍依赖：

```text
idempotency
transaction
retry
reconciliation
```

### 7.27 [P0] 什么是 TOCTOU？

TOCTOU：

> Time Of Check To Time Of Use。

即：

```text
检查时成立
```

不代表：

```text
真正执行时仍然成立
```

例如：

```text
T0:
check balance >= 100
→ true

T1:
另一个请求扣掉 80

T2:
当前请求仍执行扣 100
```

检查结果已经 stale。

### 7.28 [P1] TOCTOU 怎么解决？

取决于资源。

**Database**

```text
transaction
row lock
conditional update
version CAS
```

例如：

```sql
UPDATE account
SET balance = balance - 100
WHERE id = ?
  AND balance >= 100;
```

把：

```text
check + act
```

压进一个原子 operation。

**Agent Proposal**

Proposal 绑定：

```text
state version
event sequence
snapshot hash
```

执行前重新验证。

**External Resource**

可能需要：

```text
quote version
reservation
remote conditional write
```

核心：

> **把检查尽量靠近 commit point，并绑定执行时的事实版本。**

### 7.29 [P0] 什么是 Saga？

Saga 用于：

> 一个业务流程跨越多个本地事务时，通过一系列步骤和补偿操作实现最终一致性。

例如旅行预订：

```text
Book Flight
→ Book Hotel
→ Charge Payment
```

如果最后一步失败：

```text
Cancel Hotel
Cancel Flight
```

这些：

```text
Cancel...
```

就是 compensation。

### 7.30 [P1] Saga 和数据库 Transaction 有什么区别？

数据库 Transaction：

```text
BEGIN
A
B
C
COMMIT
```

失败：

```text
ROLLBACK
```

恢复到：

```text
像事务没发生过
```

Saga：

```text
T1 commit
T2 commit
T3 fail
```

前两个已经真实提交。 只能做：

```text
C2
C1
```

补偿。 所以：

```text
Saga
≠
跨服务 ACID rollback
```

而是：

```text
forward steps
+
semantic compensation
```

### 7.31 [P0] Compensation 和 Rollback 有什么区别？

**Rollback**

撤销未提交的本地事务。 例如：

```text
UPDATE
→ error
→ ROLLBACK
```

数据库恢复。

**Compensation**

执行一个新的业务动作，抵消旧动作影响。 例如：

```text
charge 100
```

补偿不是“让 charge 没发生”。 而是：

```text
refund 100
```

历史仍然是：

```text
charge
+
refund
```

这两个事实都存在。

### 7.32 [P1] 为什么 Compensation 不一定能完全恢复原状态？

例如：

```text
send email
```

补偿：

```text
send correction email
```

不能让用户：

```text
没看到第一封
```

再比如：

```text
reserve limited seat
```

释放后：

```text
别人可能已经拿走
```

所以 compensation 常常是：

```text
business-level mitigation
```

不是数学逆运算。

### 7.33 [P1] Saga 有哪些组织方式？

常见两种。

**Choreography**

各服务通过事件：

```text
OrderCreated
→ InventoryReserved
→ PaymentConfirmed
→ ...
```

自己决定下一步。 优点：

```text
低中心耦合
```

缺点：

```text
流程散落
难看全局状态
复杂错误路径难追踪
```

**Orchestration**

一个 Saga Coordinator：

```text
调用 Inventory
↓
调用 Payment
↓
调用 Delivery
```

并记录：

```text
当前步骤
补偿步骤
```

优点：

```text
流程显式
可观察
```

缺点：

```text
中心协调器复杂度高
```

### 7.34 [P1] Saga 为什么必须有 Durable State？

如果 Saga Coordinator 只在内存中：

```text
step 1 success
step 2 success
```

然后：

```text
process crash
```

恢复后不知道：

```text
执行到哪里
哪些需要补偿
```

所以长流程需要：

```text
durable saga state
```

例如：

```text
current step
completed steps
attempts
compensation state
```

### 7.35 [P1] 什么是 Duplicate Request 和 Concurrent Request？

这两个要区分。

**Duplicate Request**

同一逻辑 command：

```text
retry A
retry A
```

通常用：

```text
idempotency key
```

处理。

**Concurrent Request**

两个不同 command 同时操作同一资源：

```text
withdraw 80
withdraw 50
```

都可能合法但互相冲突。 需要：

```text
transaction
lock
OCC
invariant
```

所以：

```text
idempotency
```

不能替代：

```text
concurrency control
```

### 7.36 [P1] 幂等和并发控制有什么区别？

假设：

```text
Request A:
withdraw 80
key=A

Request B:
withdraw 50
key=B
```

两者 idempotency key 都不同。 不存在 duplicate。 但余额：

```text
100
```

仍然不能两个都成功。 所以：

```text
idempotency
→ same command repetition

concurrency control
→ different commands competing for shared state
```

### 7.37 [P1] 什么是 Local Transaction 和 Distributed Transaction？

**Local Transaction**

一个数据库或一个事务资源内部：

```text
MySQL transaction
```

提供 ACID。

**Distributed Transaction**

多个独立资源：

```text
DB A
DB B
MQ
remote payment
```

之间需要协调一致结果。 由于跨系统：

```text
独立 crash
独立 network
独立 commit
```

问题复杂得多。

### 7.38 [P2] 两阶段提交 2PC 是什么？

经典 2PC 有 Coordinator 和 Participants。

**Phase 1: Prepare**

Coordinator：

```text
Can you commit?
```

参与者：

```text
prepare
lock/record state
vote yes/no
```

**Phase 2: Commit / Abort**

如果所有：

```text
YES
```

Coordinator：

```text
COMMIT
```

否则：

```text
ABORT
```

### 7.39 [P2] 2PC 的问题是什么？

主要问题包括：

```text
协调复杂
参与者长时间持锁
Coordinator failure
网络分区
availability 较差
```

而且很多：

```text
第三方 API
blockchain
external payment
```

根本不支持参与 XA/2PC。 所以微服务里经常使用：

```text
Saga
Outbox
idempotency
reconciliation
```

而不是把所有东西强行纳入 2PC。

### 7.40 [P2] TCC 是什么？

TCC：

```text
Try
Confirm
Cancel
```

例如资源预留：

**Try**

```text
reserve 100
```

但还不真正完成最终消费。

**Confirm**

```text
commit reservation
```

**Cancel**

```text
release reservation
```

TCC 比 Saga 更强调：

```text
业务资源预留接口
```

参与方必须专门支持：

```text
Try / Confirm / Cancel
```

因此侵入性较强。

### 7.41 [P2] Saga 和 TCC 怎么区分？

Saga：

```text
先执行真实业务动作
失败后补偿
```

TCC：

```text
先预留资源
最后确认或取消
```

例如：

```text
Saga:
charge
→ later refund

TCC:
reserve balance
→ confirm debit
or cancel reservation
```

TCC 可以减少：

```text
已经完成后再补偿
```

的问题。 代价是：

```text
参与服务必须支持 reservation semantics
```

### 7.42 [P1] 什么是 Command 和 Fact？

**Command**

```text
我希望某件事发生
```

例如：

```text
SubmitPayment
GrantEntitlement
```

可能：

```text
成功
失败
拒绝
```

**Fact / Event**

```text
某件事已经发生
```

例如：

```text
PaymentConfirmed
EntitlementGranted
```

不能再：

```text
拒绝历史事实
```

只能产生新事实修正。

### 7.43 [P1] 为什么 Command 和 Fact 混淆很危险？

如果消息叫：

```text
payment.success
```

Consumer 却把它理解成：

```text
“请帮我执行一次 payment”
```

就可能重新产生副作用。 Fact 应该驱动：

```text
projection
entitlement
notification
```

而不是重新执行原 fact 对应的外部动作。

### 7.44 [P1] 什么是 Deterministic Replay？

给定：

```text
同一输入事实序列
```

系统能够：

```text
重新计算同样的派生状态
```

例如：

```text
Event 1
Event 2
Event 3
```

总能得到：

```text
Projection V3
```

这要求计算尽量不依赖：

```text
当前时间
随机数
实时 API
未记录环境状态
```

### 7.45 [P2] 为什么 Replay 中 Random / Time 很危险？

例如 projection 代码：

```text
if time.Now().Hour() < 12 ...
```

今天 replay 昨天事件：

```text
结果可能不同
```

又比如：

```text
random ranking
```

每次 replay：

```text
不同顺序
```

所以 deterministic replay 通常需要把：

```text
time
random seed
external result
```

作为显式事实记录，而不是 replay 时重新获取。

### 7.46 [P2] 什么是 Linearizability？

Linearizability 是一种强一致性模型。 直觉：

> 每个操作看起来像在调用开始和结束之间的某一个瞬间原子发生，并且这个顺序尊重现实时间。

例如：

```text
Write X=1 completes
```

之后另一个 Client 开始：

```text
Read X
```

不能看到：

```text
X=0
```

### 7.47 [P2] 什么是 Serializability？

Serializability 主要描述：

> 多个并发事务的执行结果，等价于某一种串行事务顺序。

重点是：

```text
transaction isolation
```

它不要求这个串行顺序一定符合真实墙钟时间。

### 7.48 [P2] Linearizability 和 Serializability 有什么区别？

可以粗略：

```text
Serializability
→ transaction correctness

Linearizability
→ real-time operation ordering
```

一个系统可能：

```text
serializable
```

但不：

```text
linearizable
```

因为合法串行顺序可能不尊重现实完成时间。

### 7.49 [P2] 什么是 CAP？

CAP 讨论存在网络分区时，分布式系统无法同时完全满足：

```text
C = Consistency
A = Availability
P = Partition tolerance
```

更准确的理解：

> 当 partition 已经发生时，需要在特定操作上权衡 consistency 和 availability。

不是：

```text
平时固定选两个字母
```

### 7.50 [P2] 为什么“Redis 是 AP / MySQL 是 CP”这种说法太粗？

因为：

```text
Redis
MySQL
```

都是产品。 不同：

```text
replication
cluster mode
read configuration
failover
transaction
```

会产生不同语义。 CAP 描述的是：

```text
某个分布式系统在 partition failure 下的行为
```

不是给数据库产品永久贴标签。

### 7.51 [P2] 什么是 Network Partition？

Network Partition：

> 系统中的节点仍然活着，但相互之间暂时无法正常通信。

例如：

```text
Node A alive
Node B alive

A ↔ B
network broken
```

这是分布式系统特别困难的 failure：

```text
你无法知道
对方死了
还是
只是网络断了
```

### 7.52 [P2] Failure Detector 为什么天然不完美？

如果节点 B 10 秒没响应：

```text
B crashed?
```

也可能：

```text
network slow
GC pause
CPU overloaded
packet loss
```

因此 timeout 本质是：

> **基于时间的怀疑。**

不是数学证明对方已经死了。 这也是：

```text
leases
leader election
distributed lock
```

复杂的根源之一。

### 7.53 [P2] 什么是 Lease？

Lease 是带有效期的 ownership。 例如：

```text
Worker A owns resource R
until T
```

只要：

```text
now < T
```

A 被认为拥有权限。

**和普通 Lock 区别**

Lease 自带：

```text
expiry
```

避免 owner crash 后永久持有。 但也产生：

```text
old owner after expiry
```

问题。 所以常和：

```text
fencing token
```

一起讨论。

### 7.54 [P2] 什么是 Fencing Token？

每次 ownership 变更生成：

```text
monotonically increasing token
```

例如：

```text
A → token 10
B → token 11
```

资源端记住：

```text
latest = 11
```

旧 A 即使恢复并提交：

```text
token 10
```

资源端拒绝。 这解决：

```text
expired lease owner
```

仍然执行的问题。

### 7.55 [P2] Lock 和 Fencing 的根本差异是什么？

Lock 试图：

```text
阻止旧 owner 继续
```

Fencing 接受：

```text
旧 owner 可能继续跑
```

但保证：

```text
它不能再提交结果
```

所以 fencing 更接近：

> **在最终 commit point 保护 invariant。**

### 7.56 [P2] 什么是 Split Brain？

Split Brain：

> 网络分区后，多个节点都认为自己是当前合法 leader / owner。

例如：

```text
Leader A
↓ network partition
Leader B elected
```

A 不知道自己已经失去领导权：

```text
A continues write
B also writes
```

形成双主。

### 7.57 [P2] 怎么防 Split Brain？

典型需要：

```text
quorum
term/epoch
fencing
consensus
```

例如：

```text
Leader term = 42
```

新 leader：

```text
term = 43
```

存储层拒绝：

```text
term 42 write
```

本质仍然是：

```text
stale authority cannot commit
```

### 7.58 [P2] 什么是 Quorum？

在 N 个副本中，要求：

```text
至少多数
```

节点参与某个决策。 例如：

```text
N = 5
quorum = 3
```

两个不同多数集合一定至少有：

```text
1 个节点重叠
```

这可以帮助避免两个完全独立的多数同时承认两个 leader。

### 7.59 [P2] Consensus 和普通分布式锁有什么区别？

Consensus 解决更根本的问题：

> 多个节点对一系列状态变化达成一致顺序。

例如：

```text
Raft
Paxos
```

而 Redis lock 之类更偏：

```text
某个资源当前谁拥有
```

分布式锁常常本身也依赖：

```text
某种一致性存储
```

才能提供强保证。

### 7.60 [P2] 为什么业务系统很少自己实现 Consensus？

因为：

```text
leader election
log replication
network partition
membership
snapshot
recovery
```

非常复杂。 业务系统通常使用：

```text
etcd
ZooKeeper
Consul
database
```

等已经实现共识或强协调语义的基础设施。

### 7.61 [P1] 什么是 Invariant？

Invariant：

> 无论系统经历怎样的合法执行路径，都必须成立的业务条件。

例如：

```text
同一 Economic Identity
最多一个 CONFIRMED payment
```

或者：

```text
balance >= 0
```

或者：

```text
没有 confirmed payment
就不能产生 paid entitlement
```

### 7.62 [P1] 为什么设计系统应该从 Invariant 开始？

如果只说：

```text
我们用了 Redis lock
用了 transaction
用了 MQ
```

无法判断系统是否正确。 应该先说：

```text
我要保证什么永远不能发生？
```

例如：

```text
不能重复扣款
```

再推导：

```text
需要稳定 business identity
需要 local unique constraint
需要 remote idempotency
需要 UNKNOWN
需要 reconciliation
```

工具是后面的。

### 7.63 [P1] Safety 和 Liveness 有什么区别？

**Safety**

```text
坏事永远不能发生
```

例如：

```text
不能 double charge
```

**Liveness**

```text
好事最终能够发生
```

例如：

```text
合法 payment 最终能完成
```

系统过度 fail-closed：

```text
可能 safety 很强
但 liveness 很差
```

所以生产系统必须权衡。

### 7.64 [P1] “At-most-once Economic Effect + At-least-once Message”是什么意思？

这是很实用的组合。 MQ：

```text
允许重复 delivery
```

即：

```text
at-least-once
```

但业务副作用：

```text
payment
entitlement
```

希望：

```text
at-most-once effect
```

通过：

```text
stable identity
unique constraint
idempotency
```

实现。 因此：

```text
message may repeat
business effect must not
```

### 7.65 [P1] 为什么 At-most-once Effect 不等于 At-most-once Attempt？

例如支付可能：

```text
Attempt 1
→ timeout
```

然后 reconcile：

```text
confirmed
```

业务效果仍只有一次。 另一个场景：

```text
Attempt 1 definitely failed
Attempt 2 succeeds
```

存在两个 attempt，但：

```text
一个 confirmed effect
```

所以需要区分：

```text
attempt identity
```

和：

```text
economic identity
```

### 7.66 [P1] 什么是 Effectively-once？

Effectively-once：

> 底层可能发生 retry、redelivery、重复 handler invocation，但系统通过去重和幂等，使业务可观察效果等价于一次。

通常组合：

```text
at-least-once transport
+
idempotent consumer
+
stable business identity
+
local transaction
```

获得。

### 7.67 [P2] 为什么 Exactly-once 往往是一个“范围声明”？

面试里听到：

```text
exactly-once
```

必须追问：

```text
在哪个边界？
```

例如：

```text
Kafka transaction 内？
某个 DB table？
MQ consumer offset + state store？
某个 provider idempotency key？
```

不能直接扩大到：

```text
整个分布式业务
```

### 7.68 [P1] 什么是 Side-effect-safe State Machine？

状态机不仅限制：

```text
什么状态可以去什么状态
```

还要限制：

```text
在哪个状态允许执行哪个不可逆动作
```

例如：

```text
CREATED
→ PREPARED
→ SUBMITTING
→ UNKNOWN / CONFIRMED
```

只有：

```text
PREPARED → SUBMITTING
```

对应真正调用 payment。 如果当前已经：

```text
CONFIRMED
```

任何 retry 都不能重新调用 payment。

### 7.69 [P1] 为什么要先 Persist Intent 再执行 Side Effect？

错误：

```text
call remote payment
↓
process crash
```

本地甚至没有记录：

```text
刚才打算执行什么
```

正确方向：

```text
create durable intent
↓
commit
↓
execute side effect
```

即使 crash：

```text
至少知道
哪个 command 处于 SUBMITTING / UNKNOWN
```

可以恢复。

### 7.70 [P1] 为什么 Persist Intent 仍然不能保证 Exactly-once？

仍有窗口：

```text
T0 intent persisted

T1 remote payment called

T2 remote succeeds

T3 crash

T4 local still SUBMITTING
```

恢复后不知道：

```text
T2 是否发生
```

因此还需要：

```text
remote identity
UNKNOWN
reconciliation
```

### 7.71 [P2] Side-effect-safe State Machine 的典型结构是什么？

一种通用形式：

```text
NEW
 ↓
PREPARED
 ↓
SUBMITTING
 ├─→ CONFIRMED
 ├─→ DEFINITELY_FAILED
 └─→ UNKNOWN
         ↓
     RECONCILING
         ├─→ CONFIRMED
         └─→ DEFINITELY_FAILED
```

关键：

```text
SUBMITTING
```

表示：

> side effect invocation 已经可能开始。

所以 crash 后不能退回：

```text
PREPARED
```

然后 blind resubmit。

### 7.72 [P1] 什么叫 Definitive Failure？

只有在系统能确认：

> 前一次副作用没有成功，并且不会稍后变成功。

才能叫：

```text
definitely failed
```

例如 provider 明确返回：

```text
invalid signature
insufficient funds
request rejected before submission
```

而：

```text
timeout
connection reset
```

通常不足以证明 definitive failure。

### 7.73 [P1] Retry Policy 为什么必须根据 Error Taxonomy？

错误可以分：

```text
INVALID_ARGUMENT
NOT_FOUND
PERMISSION_DENIED
TRANSIENT
TIMEOUT
UNKNOWN_OUTCOME
```

不同错误：

```text
retry strategy
```

不同。 例如：

```text
INVALID_ARGUMENT
→ do not retry

TRANSIENT read
→ retry with backoff

TIMEOUT mutation
→ reconcile

PERMISSION_DENIED
→ stop / reauthorize
```

### 7.74 [P1] 什么是 Backoff？

Retry 如果：

```text
立即连续重试
```

容易：

```text
把故障服务打得更严重
```

因此等待：

```text
100ms
200ms
400ms
...
```

即 exponential backoff。 一般再配：

```text
jitter
```

打散同步重试。

### 7.75 [P1] Retry Budget 是什么？

不是每个请求都允许：

```text
无限 retry
```

例如：

```text
1000 original requests/s
```

只允许：

```text
100 retry/s
```

避免：

```text
failure
→ retry traffic
→ more failure
```

正反馈。

### 7.76 [P1] 什么是 Backpressure？

当下游处理不过来：

```text
upstream
```

不能无限继续送任务。 需要：

```text
block
reject
queue with bound
rate limit
load shed
```

把容量不足反馈回去。 RocketMQ backlog 可以：

```text
暂时吸收峰值
```

但长期：

```text
produce > consume
```

仍然必须处理。

### 7.77 [P1] 为什么 Queue 不能无限大？

无限 Queue：

```text
不会立即拒绝
```

看起来 availability 很好。 但代价：

```text
memory / disk ↑
message age ↑
latency ↑
recovery time ↑
```

最终：

```text
所有请求都成功排队
但几小时后才执行
```

可能比直接失败更糟。

### 7.78 [P2] 什么是 Load Shedding？

系统已经过载时：

```text
主动拒绝部分请求
```

保住：

```text
核心请求
```

例如：

```text
low priority requests
→ reject

payment confirm
→ preserve
```

核心思想：

> **有限资源下，失败得有选择，而不是所有请求一起慢死。**

### 7.79 [P2] 什么是 Bulkhead？

通过资源隔离避免一个功能拖垮整个进程。 例如：

```text
Search worker pool = 50

Payment worker pool = 20
```

Search 卡死：

```text
不会占光 Payment capacity
```

来源类比：

```text
船舱隔板
```

一个舱进水不拖沉全船。

### 7.80 [P2] Circuit Breaker 在分布式可靠性中解决什么？

当下游持续失败：

```text
继续调用
```

只会：

```text
浪费资源
增加压力
增加 timeout
```

Circuit Breaker：

```text
failure threshold
→ OPEN
→ fail fast
→ cooldown
→ probe
```

保护双方。

### 7.81 [P2] Circuit Breaker 能保证正确性吗？

不能。 它主要保护：

```text
availability
resource safety
```

不能解决：

```text
duplicate side effect
unknown outcome
business consistency
```

所以：

```text
breaker
```

是 resilience mechanism。 不是：

```text
correctness mechanism
```

### 7.82 [P2] 什么是 Failure Amplification？

一个局部慢服务：

```text
Service C slow
```

导致：

```text
B waits
A waits
Gateway waits
Client retries
Gateway retries
A retries
```

最终流量指数增加。 这种：

```text
small failure
→ system-wide overload
```

就是 failure amplification。

### 7.83 [P2] 为什么 Tail Latency 会在调用链放大？

一次请求调用：

```text
10 downstreams
```

最终等待：

```text
最慢一个
```

即使每个：

```text
99% < 50ms
```

多个 fan-out 后：

```text
遇到至少一个 slow request
```

概率会上升。 所以 distributed service 更关注：

```text
P95 / P99
```

而不是 average。

### 7.84 [P2] 什么是 Retry Storm？

大量请求：

```text
同时 timeout
```

然后：

```text
同时 retry
```

下游：

```text
already overloaded
```

Retry 又加压。 于是：

```text
timeout
→ retry
→ overload
→ more timeout
→ more retry
```

形成 storm。 解决组合：

```text
backoff
jitter
retry budget
circuit breaker
load shedding
```

### 7.85 [P1] 什么是 Recovery Point 和 Recovery Path？

一个系统设计不能只描述：

```text
happy path
```

还应该明确：

**Recovery Point**

崩溃后：

```text
从哪份 durable state 恢复
```

例如：

```text
PaymentIntent
Outbox
EpisodeEvent
```

**Recovery Path**

恢复后：

```text
怎么继续
```

例如：

```text
scan SUBMITTING
→ reconcile
→ advance state
```

### 7.86 [P2] 为什么“能重启”不等于“能恢复”？

服务进程起来：

```text
health check green
```

不代表：

```text
crash 前半完成的业务
```

已经处理。 例如：

```text
100 PaymentIntent = UNKNOWN
```

如果 restart 后没人扫描：

```text
永远 UNKNOWN
```

所以真正 recovery 需要：

```text
durable recovery state
+
recovery worker
+
idempotent resume
```

### 7.87 [P1] 什么是 Reconciliation Convergence？

Reconciliation 不应该每次：

```text
查一下
然后随便改
```

而应该朝稳定终态收敛。 例如：

```text
UNKNOWN
↓
query provider
↓
CONFIRMED
```

一旦：

```text
CONFIRMED
```

后续 reconcile：

```text
仍然 CONFIRMED
```

不会来回：

```text
CONFIRMED ↔ UNKNOWN
```

这就是 convergence 思维。

### 7.88 [P2] Reconciliation 为什么最好单调推进？

状态如果：

```text
NEW
→ SUBMITTED
→ CONFIRMED
```

一旦获得更强事实：

```text
CONFIRMED
```

不应因为某次查询超时就退回：

```text
UNKNOWN
```

即：

```text
new evidence
```

应尽量：

```text
增加已知事实
```

而不是把确定事实覆盖成不确定。 这种单调性大幅降低恢复复杂度。

### 7.89 [P2] 什么是 Monotonic State Machine？

状态向：

```text
信息越来越确定
```

的方向推进。 例如：

```text
UNOBSERVED
→ SUBMITTED
→ UNKNOWN
→ CONFIRMED
```

虽然名字上 UNKNOWN 看似后退，但语义：

```text
已经知道 submit 发生过
```

仍比最初更多信息。 真正终态：

```text
CONFIRMED
DEFINITELY_FAILED
```

不轻易回退。

### 7.90 [P2] 为什么 Append-only Fact 往往比直接覆盖状态更容易审计？

如果：

```text
payment.status
```

一直：

```text
PENDING
→ UNKNOWN
→ CONFIRMED
```

只保存当前值，丢失：

```text
过程
```

Append facts：

```text
PaymentCreated
PaymentSubmitted
PaymentOutcomeUnknown
PaymentConfirmed
```

可以回答：

```text
发生过什么？
何时发生？
谁观察到？
```

更利于：

```text
audit
replay
reconciliation
```

### 7.91 [P2] Event Log 和 Current State 应该怎么配合？

常见：

```text
Append-only facts
       ↓
Current Projection
```

读取：

```text
current state
```

快。 审计：

```text
fact history
```

完整。 不一定要完全 Event Sourcing。 也可以：

```text
state table
+
immutable event table
```

同时存在。

### 7.92 [P1] 什么是 Source of Truth？

Source of Truth：

> 某个事实发生冲突时，最终应该相信哪一份数据。

例如：

```text
Redis cache = CONFIRMED
MySQL = UNKNOWN
provider = CONFIRMED
```

需要明确：

```text
哪个事实决定最终业务结论
```

否则每个系统都：

```text
觉得自己是对的
```

无法 reconcile。

### 7.93 [P1] 为什么不能有多个“最终事实源”？

多个系统都允许独立修改同一事实：

```text
DB A
DB B
Redis
MQ projection
```

最终：

```text
冲突时没人知道谁赢
```

更合理：

```text
one authoritative owner
```

其他：

```text
replica
projection
cache
derived state
```

### 7.94 [P2] 什么是 Single Writer Principle？

对于某类 authoritative state：

> 尽可能由一个逻辑 owner 负责提交。

例如：

```text
Payment Service
```

唯一有权决定：

```text
PaymentIntent transition
```

其他服务：

```text
只能发送 command
或者消费 fact
```

避免：

```text
Service A 修改 payment table
Service B 也修改 payment table
```

产生 authority ambiguity。

### 7.95 [P1] 为什么 Service Boundary 和 Authority Boundary 应该接近？

如果 Payment Service 名义上拥有 Payment：

```text
但 Verification Service 也能直接改 payment DB
```

那么：

```text
服务边界
```

只是形式。 更好的微服务边界：

```text
data ownership
+
write authority
+
business invariant
```

尽量一致。

### 7.96 [P2] 什么是 Distributed Invariant？

Invariant 跨多个服务时：

```text
A 中状态
+
B 中状态
```

共同构成约束。 例如：

```text
Entitlement ACTIVE
→ must correspond to confirmed payment
```

Payment 和 Entitlement 在不同 DB。 不能用一个 MySQL transaction 保证。 因此需要：

```text
event
idempotency
reconciliation
```

来维护。

### 7.97 [P2] 为什么分布式 Invariant 比本地 Invariant 难？

本地：

```text
UNIQUE
CHECK
transaction
lock
```

数据库直接保护。 分布式：

```text
network delay
partial failure
independent commits
message retry
```

使得约束可能暂时不成立。 所以常把 invariant 拆成：

**Safety**

```text
绝不能错误发放
```

**Convergence**

```text
应该最终补齐合法发放
```

分别设计。

### 7.98 [P2] 为什么“状态一致”不是唯一目标？

有时更重要的是：

```text
业务不重复
不可越权
可审计
可恢复
```

例如：

```text
UI 暂时显示 PENDING
```

但真实 payment 已 CONFIRMED。 这是 temporary stale。 通常比：

```text
重复扣款
```

严重程度低很多。 所以 distributed design 首先保护：

```text
safety-critical invariant
```

再优化：

```text
freshness
```

### 7.99 分布式系统最重要的一条 Failure Timeline

考虑一个不可逆操作：

```text
T0
receive command K

T1
validate K

T2
persist intent(K, PREPARED)

T3
commit local DB

T4
mark SUBMITTING

T5
call remote side effect

T6
remote commits

T7
response lost

T8
local timeout

T9
persist UNKNOWN

T10
reconcile using stable remote identity

T11
observe CONFIRMED

T12
persist fact

T13
publish downstream event

T14
consumer processes idempotently
```

每一步都对应一个知识点：

```text
T0
→ idempotency identity

T2
→ durable intent

T3
→ local transaction

T4
→ crash-recovery state

T5
→ side-effect boundary

T7
→ partial failure

T8
→ timeout ≠ failed

T9
→ UNKNOWN

T10
→ reconciliation

T12
→ authoritative fact

T13
→ Outbox / MQ

T14
→ at-least-once + idempotent consumer
```

这就是整个后端可靠性主线。

### 7.100 高频错误设计：Timeout 就标 FAILED

错误：

```text
remote timeout
→ FAILED
→ retry
```

可能：

```text
first call succeeded
```

结果重复副作用。 正确：

```text
timeout after possible submission
→ UNKNOWN
→ reconcile
```

### 7.101 高频错误设计：加 Redis Lock 就不会重复

Lock：

```text
可能过期
可能 failover
可能旧 owner 恢复
```

而且 response lost 后：

```text
下一次请求迟早还会拿到锁
```

所以：

```text
lock
```

只是减少并发。 不能代替：

```text
business identity
idempotency
```

### 7.102 高频错误设计：加数据库 UNIQUE 就绝不会 double charge

如果顺序：

```text
charge
↓
INSERT UNIQUE
```

两个请求都可能先 charge 成功。 Unique conflict 发生时：

```text
钱已经扣两次
```

所以：

```text
invariant must be enforced
before / at real side-effect boundary
```

而不是副作用后才发现。

### 7.103 高频错误设计：Saga 能像 Rollback 一样还原一切

Saga compensation 是：

```text
new business action
```

不是时间机器。 例如：

```text
charge
→ refund
```

仍然会留下：

```text
两笔真实经济事实
```

### 7.104 高频错误设计：Eventual Consistency 就不用管中间状态

中间可能持续：

```text
10ms
10s
10h
forever
```

如果没有：

```text
retry
DLQ
reconciliation
```

所谓：

```text
eventual
```

可能根本不会发生。

### 7.105 高频错误设计：Exactly-once 是 MQ 提供的功能

真正业务效果往往跨：

```text
MQ
DB
remote API
```

Broker 的 exactly-once claim 不能自动覆盖：

```text
外部系统
```

必须明确 exactly-once 的边界。

### 7.106 高频错误设计：Retry 越多 Availability 越高

过多 retry：

```text
会放大负载
```

故障期反而：

```text
availability 更差
```

需要：

```text
retry budget
backoff
jitter
circuit breaker
```

### 7.107 高频错误设计：只要状态机合法就不会重复副作用

如果：

```text
state transition
```

在副作用之后才 commit：

```text
remote success
↓
crash
↓
state still previous
```

恢复后仍可能再次进入同一动作。 所以状态机必须结合：

```text
durable pre-side-effect state
```

设计。

### 7.108 高频错误设计：只存最终状态，不存过程事实

最终：

```text
CONFIRMED
```

却不知道：

```text
谁提交的
什么时候 UNKNOWN
哪次 reconcile 确认
```

审计、恢复、debug 都困难。 高价值流程应考虑：

```text
immutable transition facts
```

### 7.109 本章高频对比

| 概念 A                   | 概念 B                    | 核心区别                                  |
| ---------------------- | ----------------------- | ------------------------------------- |
| Request ID             | Idempotency Key         | 网络调用身份 vs 逻辑 command 身份               |
| Event ID               | Business Identity       | 消息身份 vs 业务效果身份                        |
| Nonce                  | Idempotency Key         | 阻止 replay vs 安全接受 retry               |
| Duplicate Request      | Concurrent Request      | 同命令重试 vs 不同命令竞争                       |
| Timeout                | Failure                 | 没及时拿到结果 vs 已知操作失败                     |
| Failed                 | UNKNOWN                 | 已知失败 vs 结果不确定                         |
| Retry                  | Reconciliation          | 再执行 vs 查明前次结果                         |
| Retry                  | Business Retry          | transport 重试 vs 新业务 attempt           |
| Local Transaction      | Distributed Transaction | 单资源 ACID vs 跨资源协调                     |
| Rollback               | Compensation            | 撤销未提交状态 vs 新动作抵消旧动作                   |
| Saga                   | TCC                     | 执行后补偿 vs 预留后 Confirm/Cancel           |
| Saga Choreography      | Orchestration           | 事件驱动分散协调 vs 中央流程协调                    |
| Eventual Consistency   | Strong Consistency      | 最终收敛 vs 更强即时可见性                       |
| Serializability        | Linearizability         | 事务等价串行 vs 尊重现实时间的原子操作                 |
| Lock                   | Idempotency             | 防并发进入 vs 防重复业务效果                      |
| Lease                  | Lock                    | 带过期 ownership vs 普通互斥概念               |
| Lease                  | Fencing                 | 限时 ownership vs 阻止 stale owner commit |
| Safety                 | Liveness                | 坏事不能发生 vs 好事最终发生                      |
| At-least-once Delivery | At-most-once Effect     | 消息可重复 vs 业务效果不能重复                     |
| Exactly-once Delivery  | Effectively-once        | 传输声明 vs 最终业务可见结果                      |
| Command                | Fact                    | 希望发生 vs 已经发生                          |
| Intent                 | Fact                    | 准备执行 vs 已观察到结果                        |
| Current State          | Event Log               | 当前快照 vs 历史事实序列                        |
| Cache/Projection       | Source of Truth         | 派生数据 vs 权威事实                          |
| Retry                  | Recovery                | 某次操作重试 vs 系统崩溃后继续推进                   |
| Readiness              | Liveness                | 可接流量 vs 进程还活着                         |

### 7.110 面试前一分钟速记

```text
分布式系统最重要的不是：
“怎么不失败”

而是：
“失败后仍怎么保持正确”。

Idempotency：
重复执行，
业务效果不重复。

Request ID
≠
Idempotency Key。

Nonce：
防 replay。

Idempotency Key：
安全 retry。

Timeout
≠
Failed。

可能已产生副作用的 Timeout：
应考虑 UNKNOWN。

UNKNOWN：
不是错误码，
而是业务状态。

Retry：
再做一次。

Reconciliation：
查清上次到底发生了什么。

Remote mutation：
不能 blind retry。

Local transaction
只保护本地 DB，
不能 rollback remote side effect。

Saga：
多个本地事务
+
compensation。

Compensation
≠
rollback。

Duplicate request
和
concurrent request
是不同问题。

Idempotency
不能替代 concurrency control。

At-least-once message
+
idempotent consumer
→ effectively-once local effect。

Lock
不能替代 idempotency。

Lease 可能过期，
旧 owner 可能继续执行。

Fencing：
在 commit point 拒绝 stale owner。

Eventual consistency
必须有 retry / recovery / convergence，
不是“以后应该会一致”。

Invariant-first：
先说绝不能发生什么，
再决定 transaction / lock / MQ / reconciliation。

Side-effect-safe state machine：

persist intent
→ SUBMITTING
→ remote call
→ CONFIRMED / FAILED / UNKNOWN
→ reconcile UNKNOWN。

业务最终事实
和
transport response
不是一回事。
```

### 7.111 StablePay 映射

本章和 StablePay 的关系最紧，但仍然不展开源码。 可以直接映射：

```text
Idempotency
→ action / payment / discovery 等逻辑 command 身份

Economic Identity
→ 同一经济效果不能因为 transport retry 被创建成新 payment

UNKNOWN
→ 远程提交后结果不确定

Reconciliation
→ 从 provider / chain / entitlement 事实恢复本地状态

OCC
→ Episode stale write / concurrent resume

Saga
→ acquire capability 跨 payment / entitlement / delivery 的长流程

Compensation
→ refund / release 等未来恢复动作

Command vs Fact
→ Action / Event / Observation 分离

Durable Intent
→ PaymentIntent

At-least-once
→ RocketMQ 消费

Effectively-once
→ EventID + DB invariant + consumer idempotency

TOCTOU
→ Proposal based-on-version / CandidateSet snapshot

Source of Truth
→ Ledger / Payment / Catalog authoritative facts

Side-effect-safe state machine
→ SUBMITTING / UNKNOWN / reconcile
```

01 应继续负责回答：

```text
StablePay 的 UNKNOWN 具体在哪些状态出现？

EconomicIdentityKey 是怎么构造的？

哪些 retry 保持同一 intent？

哪些状态已经实现 reconcile？

CandidateSet 如何绑定 version / hash？

当前有哪些 Outbox / Inbox 缺口？

哪些 side effect 还只是 mock / planned？
```

02 只负责回答：

> 为什么这些机制普遍存在，以及少了它们会在哪个 failure window 出错。

### 7.112 本章学习优先级

### 第一轮：P0

必须立即能答：

```text
Idempotency
Nonce
Idempotency Key
Timeout ≠ Failed
UNKNOWN
Blind Retry
Reconciliation
Eventual Consistency
Strong Consistency
Readiness / Liveness
TOCTOU
Saga
Compensation
```

这是后端面试里最值得优先形成条件反射的一组。

### 第二轮：P1

重点掌握：

```text
RequestID / IdempotencyKey / EventID / BusinessID
Request Fingerprint
Duplicate vs Concurrent Request
Local vs Distributed Transaction
Command vs Fact
Deterministic Replay
Invariant
Safety / Liveness
At-least-once + At-most-once effect
Effectively-once
Durable Intent
Definitive Failure
Retry Taxonomy
Backpressure
Recovery Path
Source of Truth
Single Writer
```

做到看到一条 failure timeline 能自己推方案。

### 第三轮：P2

针对后端 Infra / Agent Infra / 支付：

```text
2PC
TCC
Linearizability
Serializability
CAP
Network Partition
Lease
Fencing
Split Brain
Quorum
Consensus
Distributed Invariant
Monotonic Reconciliation
Monotonic State Machine
Append-only Fact
Side-effect-safe State Machine
Failure Amplification
Retry Storm
Bulkhead
Load Shedding
```

最终不要把分布式八股背成：

> “分布式系统要做幂等、重试、熔断、降级、限流，数据库用分布式事务保证一致性。”

更成熟的回答应该是：

> 分布式系统首先要定义业务 invariant，再识别哪些操作跨越了本地事务边界。网络 timeout 只能说明调用方没有及时获得结果，因此对可能已经发生的外部副作用需要显式 UNKNOWN 和 reconciliation，而不是 blind retry。重复请求用稳定 command/business identity 和幂等约束处理，不同并发命令则需要 transaction、OCC 或锁处理。异步链路通常接受 at-least-once delivery，再通过 Inbox、UNIQUE 和幂等 consumer 获得 effectively-once business effect。跨服务流程如果无法使用全局 ACID，就依靠 Saga、补偿和 reconciliation 最终收敛；高风险 side effect 则进一步要求 durable intent、side-effect-safe state machine 和明确的 source of truth。

### 1.24 [P1] 什么是 Factual Authority？

Agent Runtime 中需要区分：

```text
Decision Authority
```

和：

```text
Factual Authority
```

LLM 可以回答：

```text
下一步更适合选哪个候选？
失败后是否应该尝试另一种策略？
```

但不应该自行创造：

```text
merchant 真正要求支付多少钱
真实 payee 是谁
settlement network 是什么
asset 是什么
payment 是否 confirmed
merchant 实际返回了什么
```

这些属于：

```text
external facts
+
authoritative system facts
```

**一个典型错误**

模型输出：

```json
{
  "merchant": "M1",
  "amount": 2,
  "currency": "USDC",
  "payee": "some-address"
}
```

Runtime 直接：

```text
pay(model.amount, model.payee)
```

这里模型不仅做了：

```text
decision
```

还成为了：

```text
payment factual authority
```

这是危险边界。

**更合理的结构**

```text
LLM
 ↓
propose candidate / action
 ↓
Runtime
 ↓
retrieve authoritative fact
 ↓
parse
 ↓
bind
 ↓
policy check
 ↓
side effect
```

例如：

```text
LLM:
select candidate C1

Runtime:
C1 → trusted catalog snapshot

Merchant:
HTTP 402 → payment requirement

Deterministic parser:
amount / asset / payee / network

Runtime:
catalog binding
budget binding
settlement policy
resource binding

Payment
```

因此：

```text
LLM Proposal
≠
Business Fact
```

**External Source 也不等于无条件 Authority**

Merchant 返回：

```text
pay 10000 USDC to X
```

它确实是：

```text
merchant-supplied fact
```

但仍必须检查：

```text
这个 merchant 是不是当前已选 merchant？
resource URL 是否匹配？
payee 是否匹配 trusted catalog？
currency 是否允许？
amount 是否在 budget 内？
network / asset 是否满足 settlement policy？
quote 是否仍有效？
```

所以更准确：

```text
Fact Source
+
Runtime Binding
+
Policy
=
Trusted Operational Fact
```

### 1.25 [P1] 为什么 Guard 必须发生在 Side Effect 之前？

错误结构：

```text
call external API
↓
check state
↓
发现其实不允许
```

已经太晚。 如果 external API 是：

```text
payment
email
resource allocation
merchant delivery
```

副作用已经发生。 因此安全状态机应该：

```text
load current state
↓
validate state
↓
validate authority
↓
validate binding
↓
validate deadline / attempts
↓
persist durable invocation intent
↓
external side effect
↓
persist observation
```

而不是：

```text
external call
↓
guard
```

**Guard-before-side-effect 比“最终状态正确”更强**

假设状态：

```text
CLAIMING
```

规定只有：

```text
entitlement confirmed
```

以后才能调用 merchant delivery。 错误实现可能：

```text
call merchant
↓
later fail transition
```

最终 Episode 没有进入非法状态。 但：

```text
merchant side effect 已经发生
```

所以：

> **状态转移没有 commit，并不能证明副作用没有发生。**

更强的测试应该验证：

```text
guard rejection
+
no invocation record
+
no external call
```

即：

```text
rejected operation leaves no side-effect footprint
```

### 3.76 [P1] 为什么 External Response 必须有 Size Bound？

外部 HTTP/RPC response 也是：

```text
untrusted input
```

如果：

```text
io.ReadAll(response.Body)
```

没有上限，对方可以返回：

```text
10 GB body
```

导致：

```text
memory exhaustion
storage exhaustion
GC pressure
```

所以边界适配器应限制：

```text
request body
response body
challenge payload
stored artifact
```

例如：

```text
read at most N + 1 bytes

if size > N:
    reject
```

这属于：

```text
bounded execution
```

在网络边界上的体现。

**为什么只限制内存还不够？**

如果系统之后：

```text
persist response body
```

还需要同时限制：

```text
durable storage size
```

否则攻击者可以通过大量合法上限 payload：

```text
fill DB / disk
```

因此：

```text
Memory Bound
+
Persistence Bound
+
Request Deadline
```

应一起设计。

### 4.87 [P1] SQLite 的 `BEGIN IMMEDIATE` 是什么？

SQLite 和 MySQL 的并发模型不同。 普通 transaction 如果延迟到真正写入时才竞争 writer：

```text
Transaction A
BEGIN
READ unused resource

Transaction B
BEGIN
READ same unused resource

A tries write
B tries write
```

应用可能已经基于：

```text
同一个旧观察
```

完成决策。 `BEGIN IMMEDIATE` 的核心意义可以理解为：

> **在进入 read-modify-write critical section 之前，先取得 SQLite write transaction。**

结构：

```text
BEGIN IMMEDIATE

read existing receipt
read unused resource
conditional update resource
insert result receipt

COMMIT
```

这样竞争 writer 会在更早的位置串行化。

**为什么 `sync.Mutex` 不够？**

```go
var mu sync.Mutex
```

只能保护：

```text
同一个 Go process
```

如果：

```text
Merchant Process A
Merchant Process B
```

同时打开同一个 SQLite DB：

```text
A.mu
```

和：

```text
B.mu
```

完全没有关系。 因此：

```text
process-local mutex
≠
cross-process serialization
```

如果 invariant 最终存在数据库里，就应尽量让：

```text
database transaction
```

成为最终并发边界。

### 4.88 [P2] 什么是“业务分配 + Idempotency Receipt”的本地 Dual-write？

Dual-write 不只存在：

```text
DB + MQ
```

任何逻辑操作需要提交两份 durable state，都应该寻找 crash window。 例如一次付费交付：

```text
1. allocate gift code
2. save idempotent response receipt
```

错误实现：

```text
allocate gift code
↓
CRASH
↓
save receipt never happens
```

Retry：

```text
没有 receipt
→ allocate another gift code
```

于是：

```text
one logical request
→ two scarce resources consumed
```

**反过来也有问题**

```text
save receipt
↓
CRASH
↓
gift code allocation never committed
```

之后 replay：

```text
receipt says delivered
```

但资源其实没分配。

**如果两个事实在同一个数据库**

最简单正确方向不是：

```text
Saga
MQ
distributed lock
```

而是：

```text
one local transaction
```

例如：

```text
BEGIN

check existing receipt

if absent:
    reserve resource
    build materialized result
    insert receipt

COMMIT
```

这里再次体现：

> **能用 local ACID 解决的 invariant，不要提前升级成 distributed protocol。**

### 7.113 [P1] 什么是 Idempotency Receipt？

最基础的幂等：

```text
same request
→ don't execute effect twice
```

但有些 API 需要更强语义：

```text
same logical operation
→ return the original committed result
```

这时可以持久化：

```text
Idempotency Receipt
```

例如：

```text
IdempotencyKey
AgentID
ResourceID
ResponsePayload
CreatedAt
```

第一次：

```text
execute
↓
materialize result
↓
persist receipt
```

Retry：

```text
lookup receipt
↓
return original result
```

### 7.114 [P1] Effect Idempotency 和 Result Idempotency 有什么区别？

**Effect Idempotency**

保证：

```text
gift code 只分配一次
payment 只发生一次
entitlement 只创建一次
```

**Result Idempotency**

还保证：

```text
retry 得到原先那个结果
```

例如第一次：

```json
{
  "gift_code": "ABC-123"
}
```

Retry 不能：

```json
{
  "gift_code": "XYZ-999"
}
```

即使两者都“有一个 gift code”。

**为什么 Exact Redelivery 有价值？**

如果 response 包含：

```text
gift code
signed proof
receipt ID
timestamp
artifact hash
```

重新计算 response 可能产生新值。 所以对于：

```text
materialized business outcome
```

更强的幂等策略是：

```text
persist result
→ replay stored result
```

而不是：

```text
re-run result generation
```

### 7.115 [P2] 为什么 Idempotency 必须跨 Process Restart？

如果：

```go
map[idempotencyKey]Result
```

只存在内存。 进程：

```text
request succeeds
↓
response lost
↓
process restart
↓
retry
```

内存状态没了。 系统会认为：

```text
first request never happened
```

因此高价值幂等状态必须根据语义选择：

```text
durable store
```

而不是只使用：

```text
in-memory mutex
in-memory map
```

正确测试不应只是：

```text
call twice in same process
```

还应包括：

```text
call once
↓
restart process
↓
call same operation again
↓
same durable result
```

### 7.116 [P1] 为什么 Same Idempotency Key + Different Request 必须冲突？

假设第一次：

```text
key = K
agent = A
resource = R1
```

第二次：

```text
key = K
agent = B
resource = R2
```

不能：

```text
直接返回第一次 response
```

也不能：

```text
当成新的请求执行
```

正确结果通常是：

```text
Idempotency Conflict
```

所以 Idempotency Record 必须绑定：

```text
logical operation identity
```

### 7.117 [P1] 什么是 Request Fingerprint？

可以计算：

```text
fingerprint = Hash(
    semantic request fields
)
```

第一次保存：

```text
K → fingerprint F1
```

Retry：

```text
K + F1
→ replay
```

如果：

```text
K + F2
```

则：

```text
conflict
```

**Fingerprint 应该包含什么？**

包含：

```text
会改变业务语义的字段
```

例如：

```text
merchant
resource
amount
currency
phase
attempt identity
```

**什么字段可能不应该包含？**

例如：

```text
trace ID
临时 authentication signature
transport retry metadata
```

如果它们变化：

```text
不代表产生了一个新的业务 operation
```

就不应该自动改变逻辑幂等身份。 因此：

```text
Request Fingerprint
≠
Hash every byte blindly
```

而应该：

> **Hash semantic operation identity。**

### 7.118 [P2] 什么是 Retry Scope？

系统失败以后，不应该机械地：

```text
restart whole workflow
```

而应该：

> **从失败的最小安全层级重试。**

例如：

```text
payment confirmed
↓
merchant delivery failed
```

正确：

```text
retry delivery
```

而不是：

```text
retry payment
```

否则：

```text
下游交付失败
```

会被错误放大成：

```text
第二次经济支付
```

**一个重要 Invariant**

```text
economic effect count
```

和：

```text
delivery attempt count
```

必须分开。 一个流程完全可能：

```text
PaymentAttemptCount = 1
RetryCount = 1
DeliveryAttemptCount = 2
```

意思是：

```text
付一次钱
↓
第一次交付无效
↓
做一次 recovery decision
↓
第二次交付
```

而不是：

```text
第一次交付无效
↓
重新付一次钱
```

**Retry 应该发生在哪一层？**

```text
payment failed definitively
→ payment layer may retry

delivery invalid
→ delivery layer retries

validation transient error
→ validation layer retries

MQ redelivery
→ consumer processing retries
```

原则：

> **Already-confirmed upstream effects must not be replayed merely because a downstream stage failed.**

### 7.119 [P2] 为什么 Side Effect 前最好先 Persist Invocation？

另一种 crash window：

```text
call external merchant
↓
CRASH
↓
no local record
```

恢复后甚至不知道：

```text
有没有调用过？
调用的是哪个 operation？
```

更好的结构：

```text
validate guard
↓
persist invocation {
    id
    idempotency key
    request fingerprint
    started_at
}
↓
external call
↓
persist response
```

这样 crash 后：

```text
incomplete invocation exists
```

Runtime 可以区分：

```text
never started

in-flight

stale in-flight

completed
```

而不是把所有情况都解释成：

```text
“没结果，所以没执行”
```

### 7.120 [P2] 什么是 Stale In-flight Recovery？

Invocation 已存在：

```text
started_at = T
completed_at = null
```

短时间再次进入：

```text
return IN_FLIGHT
```

避免并发重复执行。 但如果长期没有完成：

```text
now > started_at + stale_after
```

可能需要：

```text
recover / retry
```

前提必须是：

```text
same idempotency identity
```

并且下游能够安全处理重试。 所以：

```text
stale timeout
```

只说明：

```text
原 worker 很可能不会继续正常完成
```

不证明：

```text
external side effect 没发生
```

这仍然要靠：

```text
downstream idempotency
or
reconciliation
```

保证安全。

## 8. Payment Semantics 与金额边界

这一节补齐支付系统中最容易被混淆的一层：结算协议的 atomic amount、业务账本的 minor unit，以及它们之间必须可审计、不可静默 round 的转换边界。

### 8.1 [P1] Atomic Amount 和 Business Amount 为什么要分开？

支付协议或区块链可能使用：

```text
atomic unit
```

而业务系统可能使用：

```text
minor accounting unit
```

例如 USDC：

```text
atomic decimals = 6
```

如果商户要求：

```text
2.00 USDC
```

链上 atomic amount：

```text
2,000,000
```

但业务 Ledger 使用：

```text
2 decimal minor unit
```

则：

```text
business amount minor = 200
```

所以：

```text
AtomicAmount       = 2,000,000
AtomicDecimals     = 6

BusinessAmountMinor = 200
BusinessDecimals    = 2
```

二者都应该显式存在。

### 8.2 [P1] 为什么不能在 Amount Boundary 上偷偷 Round？

假设 atomic currency 有：

```text
6 decimals
```

业务账本只有：

```text
2 decimals
```

转换 quantum：

```text
10^(6-2)
=
10,000
```

只有当：

```text
AtomicAmount % 10,000 == 0
```

时才能精确映射。 例如：

```text
2,000,000
→ 200
```

完全精确。 但：

```text
2,000,001
```

如果直接 round：

```text
→ 200
```

系统已经改变经济事实。 因此 authority boundary 应：

```text
exactly representable
→ accept

not exactly representable
→ reject
```

而不是：

```text
round silently
```

**为什么解析时可以使用 Big Integer？**

外部数字字符串可能：

```text
超过 int64
恶意构造
带 exponent
带 decimal point
```

解析流程可以先：

```text
strict decimal integer syntax
↓
big integer
↓
range validation
↓
exact unit conversion
↓
int64 business representation
```

这样避免：

```text
float precision loss
integer overflow
silent rounding
```

### 8.3 [P1] Wire Amount 和 Ledger Amount 谁是 Authority？

两者代表不同层级。

```text
Atomic Amount
```

是：

```text
settlement protocol fact
```

而：

```text
Business Amount Minor
```

是：

```text
internal accounting representation
```

转换关系必须：

```text
deterministic
exact
auditable
```

因此最好同时保存：

```text
atomic amount
atomic decimals
business amount
currency
asset
network
```

而不是转换完成后丢掉原始 settlement 数值。 这样未来 reconcile 时才能回答：

```text
商户要求了多少 atomic units？

我们 Ledger 为什么记成这个 amount_minor？

二者转换是否精确？
```

**10.x [P2] S4 暴露出的 Crash-window Testing 模型**

这一部分等 Macro 10 正式写时展开，但必须保留以下测试思想。 正常测试：

```text
request
→ success
```

远远不够。 还需要故障窗口：

```text
allocate resource
→ injected failure
→ transaction rollback
→ resource still reusable
```

并发：

```text
Process A same key
Process B same key
→ one resource allocation
→ same persisted result
```

Restart：

```text
request succeeds
↓
process terminates
↓
new process starts
↓
same request
↓
exact persisted result
```

Conflict：

```text
same idempotency key
+
different semantic identity
→ reject
```

Guard：

```text
illegal state
→ call operation
→ rejected
→ zero external calls
→ zero invocation facts
```

这类测试比：

```text
assert function returned nil
```

更接近真实可靠性验证。

## 9. Catalog、Discovery 与 Retrieval

很多 Agent 项目一讲 Retrieval，就立刻跳到：

```text id="ikv8az"
Embedding
Vector Database
RAG
Cosine Similarity
```

但如果是：

```text id="vgnj1b"
Agent Commerce
Tool Discovery
Service Discovery
Capability Selection
```

真正的问题不是：

> “怎么搜得更像？”

而是：

> **怎么从大量候选里找到合适对象，同时保证最终执行仍然绑定到可信、可版本化、可审计的业务事实。**

这一章的核心链路是：

```text id="kp5vp7"
Query / Task
      ↓
Candidate Retrieval
      ↓
Hard Filter
      ↓
Ranking
      ↓
Materialized CandidateSet
      ↓
LLM / Policy Selection
      ↓
Re-resolve Authoritative Snapshot
      ↓
Binding / Guard
      ↓
Execution
```

其中最重要的三个不等式：

```text id="jufg9x"
Retrieval
≠
Authorization

Ranking
≠
Authority

LLM Understanding
≠
Factual Authority
```

### 9.1 [P0] 什么是 Structured Retrieval？

Structured Retrieval：

> 根据明确字段、布尔条件、范围条件进行检索。

例如：

```text id="bb1hsw"
task_type = transcription

currency = USDC

protocol contains x402-v2

status = active

price <= 500

valid_until > now
```

这类检索可以使用：

```text id="20ot9m"
SQL
structured index
filter engine
```

特点：

```text id="qecmc3"
条件明确
可解释
结果确定性较高
```

### 9.2 [P0] 什么是 Full-text Retrieval？

Full-text Search：

> 对文本中的关键词、词频、倒排索引等进行匹配。

例如用户：

```text id="f82kn7"
“英文播客转录服务”
```

候选描述：

```text id="xzwup2"
English podcast transcription
```

全文检索可以基于：

```text id="dop0h2"
term matching
inverted index
BM25-like ranking
```

找到文本相关候选。

### 9.3 [P0] 什么是 Semantic Retrieval？

Semantic Retrieval：

> 将 query 和 document 映射到语义表示，再根据相似度寻找语义接近内容。

例如：

```text id="p4e2lm"
query:
convert spoken audio into text
```

即使候选 description 没有：

```text id="yfxm7q"
transcription
```

这个词，也可能通过 embedding 相似度被召回。

### 9.4 [P0] Structured、Full-text、Semantic 怎么选？

不是三选一。 它们解决不同问题。

**Structured**

适合：

```text id="eui62m"
必须满足的业务条件
```

例如：

```text id="ajm580"
currency
protocol
status
budget
region
content type
```

**Full-text**

适合：

```text id="czbn67"
明确关键词和术语
```

**Semantic**

适合：

```text id="9v8c2j"
自然语言意图
同义表达
模糊任务描述
```

很多生产检索是：

```text id="mc5l0q"
Structured Filter
+
Lexical Retrieval
+
Semantic Retrieval
+
Ranking
```

而不是只靠 Vector DB。

### 9.5 [P0] Hard Filter 和 Ranking 有什么区别？

这是 Discovery 最重要的一题。

**Hard Filter**

回答：

> **这个候选有没有资格进入下一阶段？**

例如：

```text id="1u1dme"
protocol unsupported
→ eliminate

currency unsupported
→ eliminate

status inactive
→ eliminate

price exceeds hard budget
→ eliminate
```

**Ranking**

回答：

> **已经合格的候选里，谁更适合排前面？**

例如：

```text id="34j7fl"
semantic relevance
price
latency
quality
reliability
```

所以：

```text id="57gh4r"
Filter
→ eligibility

Ranking
→ preference
```

### 9.6 [P1] 为什么不能把 Hard Constraint 交给 Ranking？

假设用户：

```text id="1bxpaq"
budget <= 10
```

候选：

```text id="l0vxp7"
A:
price = 8
similarity = 0.80

B:
price = 100
similarity = 0.99
```

如果把价格只是作为：

```text id="gz6o1y"
ranking penalty
```

B 仍可能因为语义分数高：

```text id="ct4wqo"
rank first
```

但它根本：

```text id="q9owp5"
不应该参与决策
```

所以真正的 hard invariant：

```text id="wy5dh6"
应在 ranking 之前过滤
```

### 9.7 [P1] Structured-before-Semantic 是绝对规则吗？

不是。 这条原则只适用于：

```text id="ujxwgi"
eligibility / authority-sensitive retrieval
```

例如：

```text id="ou7lso"
支付能力选择
工具执行
权限候选
```

因为必须先去除：

```text id="4av7o5"
绝对不能执行
```

的对象。 但普通搜索：

```text id="epr8ro"
新闻
博客
知识问答
```

可能先 semantic recall，再结构过滤，也完全合理。 所以不要机械背：

```text id="ts0srr"
永远 structured first
```

而是：

> **Hard business constraints 必须在最终候选进入执行决策前被确定性验证。**

### 9.8 [P0] Recall 和 Precision 是什么？

**Recall**

```text id="szddgk"
真正相关的候选中
有多少被找出来
```

公式：

```text id="qgiznp"
Recall
=
Relevant Retrieved
/
All Relevant
```

**Precision**

```text id="ob3wt4"
找出来的候选中
有多少真的相关
```

公式：

```text id="jd0wg8"
Precision
=
Relevant Retrieved
/
All Retrieved
```

### 9.9 [P1] 为什么 Discovery 第一阶段更看重 Recall？

如果真正最合适的 merchant：

```text id="j0b2q6"
根本没被召回
```

后面再强的：

```text id="arzyie"
reranker
LLM
policy
```

都没机会选它。 所以第一阶段常倾向：

```text id="t7n9mu"
high recall
```

然后再：

```text id="05pkrt"
filter + rerank
```

提升 precision。

### 9.10 [P1] 为什么 Recall 也不能无限扩大？

如果：

```text id="l2givn"
TopK = 100000
```

理论上 recall 可能更高。 但：

```text id="wvfoeq"
ranking cost ↑
LLM context ↑
latency ↑
noise ↑
```

最终还可能：

```text id="4c4c44"
selection quality ↓
```

所以实际是：

```text id="4jqis5"
recall quality
vs
candidate budget
```

的 trade-off。

### 9.11 [P1] 什么是 Candidate Generation？

大规模候选：

```text id="yd9gu1"
1,000,000 capabilities
```

不会全部进行昂贵排序。 第一阶段：

```text id="3b0p58"
Candidate Generation
```

快速筛：

```text id="7ymczm"
100 ~ 1000
```

然后：

```text id="hvak6e"
Reranking
```

选 TopN。 这是经典多阶段检索结构：

```text id="w5pe5h"
Corpus
 ↓
Recall
 ↓
Candidate Set
 ↓
Rerank
 ↓
TopK
```

### 9.12 [P1] Retrieval 和 Ranking 为什么要分层？

Retrieval 强调：

```text id="vtowzb"
别漏掉好候选
```

Ranking 强调：

```text id="fmhpao"
把更好的放前面
```

两者算法和性能目标不同。 例如：

```text id="0zhxmf"
ANN retrieval
```

可以非常快。 然后：

```text id="pd22ek"
cross-encoder / LLM reranker
```

只处理少量候选。 避免对整个 corpus 使用昂贵模型。

### 9.13 [P0] 什么是 Reranking？

Reranking：

> 对第一阶段召回的候选使用更精细的模型或规则重新排序。

例如：

```text id="vh9pc8"
Stage 1:
BM25 / vector
→ Top 100

Stage 2:
reranker
→ Top 10
```

Reranker 可以考虑更复杂的：

```text id="uwz21n"
query-document interaction
business signals
quality signals
```

### 9.14 [P1] Ranking Score 应该等于业务 Authority 吗？

绝对不应该。 假设：

```text id="kjr77y"
semantic_score = 0.98
```

只能说明：

```text id="1vzmgn"
文本/语义更相关
```

不能证明：

```text id="5wj8fe"
merchant 仍 active
price 仍有效
payee 仍正确
quote 仍有效
```

所以：

```text id="hjzngn"
ranking score
```

只能进入：

```text id="dtc9co"
selection
```

不能进入：

```text id="pwcojp"
settlement fact
```

### 9.15 [P1] 什么是 Stable Tie-breaker？

假设两个候选：

```text id="n0u1hr"
score = 0.90
score = 0.90
```

如果数据库返回顺序不稳定：

```text id="bwd748"
Run 1:
A, B

Run 2:
B, A
```

相同输入可能产生不同结果。 所以 Ranking 最后可以加入：

```text id="0r9wju"
stable deterministic tie-breaker
```

例如：

```text id="dj01qp"
score DESC
price ASC
merchant_id ASC
capability_id ASC
```

使：

```text id="bqgrda"
same snapshot + same query
→ same ordering
```

### 9.16 [P1] 为什么 Deterministic Ranking 对 Agent 很重要？

普通推荐系统：

```text id="h3ly7y"
轻微随机
```

可能无所谓。 但 Agent 执行：

```text id="vm0kmx"
真实工具
真实支付
```

之后需要解释：

```text id="bewu1q"
为什么选了这个 merchant？
```

如果同样 facts replay：

```text id="xmybd7"
却排出不同结果
```

审计困难。 所以高风险 Agent 更倾向：

```text id="eqio3h"
deterministic filtering
+
deterministic tie-break
+
persisted candidate set
```

### 9.17 [P0] 什么是 Catalog？

Catalog：

> 对可发现能力/商品/工具的结构化登记。

例如一个 capability：

```text id="4h9k39"
MerchantDID
CapabilityID
Description
Protocol
Currency
Endpoint
InputSchema
OutputSchema
PriceHint
Status
Version
Validity
```

Catalog 的价值：

```text id="9xudzu"
可发现
可过滤
可验证
可版本化
```

### 9.18 [P1] Registry 和 Catalog 有什么区别？

语境不同会有重叠。 可以粗略：

**Registry**

更强调：

```text id="rrhh91"
谁存在
在哪里
```

例如：

```text id="14der4"
service registry
```

**Catalog**

更强调：

```text id="le2aeo"
有什么能力
能力属性是什么
```

例如：

```text id="x26mrz"
merchant capability catalog
```

在 Agent Commerce 中：

```text id="jmzrym"
Catalog
```

往往比简单：

```text id="mliikv"
service registry
```

承载更多业务语义。

### 9.19 [P0] 为什么 Catalog 需要 Version？

假设今天：

```text id="p71hqb"
Capability v1

price = 10
payee = A
endpoint = /v1
```

明天修改：

```text id="u5x7gp"
v2

price = 20
payee = B
endpoint = /v2
```

昨天已经做出的 Agent 决策：

```text id="q4re5d"
必须仍能解释
```

所以不能只存：

```text id="iuuzvc"
latest mutable row
```

而应该保留：

```text id="nj18xv"
versioned historical fact
```

### 9.20 [P1] Current Version 和 Historical Version 怎么设计？

一种常见模型：

```text id="wxblq1"
MerchantCapabilityVersion

merchant_id
capability_id
version
...
```

历史版本：

```text id="d25nw3"
immutable
```

另外维护：

```text id="vusjpn"
current_version pointer
```

例如：

```text id="1we2sn"
capability/current
→ v7
```

这样：

```text id="s5bqyc"
新请求
→ current v7

历史 Episode
→ still reference v4
```

### 9.21 [P1] 为什么历史版本最好 Immutable？

如果 Episode 记录：

```text id="tghrjx"
catalog_version = v4
```

但以后管理员：

```text id="7fug4m"
UPDATE v4
```

那么：

```text id="6y6715"
“v4”
```

已经不再代表当时事实。 所以真正版本语义需要：

```text id="l0q9vk"
version ID
→ immutable content
```

更新：

```text id="cz9y1y"
create new version
```

而不是修改旧版本。

### 9.22 [P1] Version 和 Snapshot 有什么区别？

**Version**

标识：

```text id="1g8q5m"
某个对象的具体历史版本
```

**Snapshot**

表示：

```text id="jjat46"
某个决策时刻所依据的一组完整事实
```

例如 CandidateSet 包含：

```text id="0ixwo7"
Merchant A v3
Merchant B v8
Merchant C v2
```

整个结果形成：

```text id="zewntl"
Discovery Snapshot
```

### 9.23 [P1] 为什么只存 Version ID 有时还不够？

如果：

```text id="ztkrpb"
外部 catalog
```

未来被删除。 虽然 Episode 保存：

```text id="7mvlqj"
version = v4
```

但：

```text id="5ombmz"
v4 内容已经取不到
```

审计仍失败。 所以高审计流程可以额外保存：

```text id="1557bb"
snapshot
snapshot hash
snapshot ref
```

至少能证明：

```text id="4fhj0h"
当时到底看到什么
```

### 9.24 [P1] Snapshot Hash 有什么作用？

假设 Candidate：

```text id="9swk6j"
merchant=M1
capability=C1
version=v4
```

Runtime 之后重新读取 v4。 计算：

```text id="3jx48d"
Hash(snapshot)
```

如果等于：

```text id="bkb1e9"
candidate.snapshot_hash
```

说明：

```text id="7wmn5h"
内容与决策时绑定的内容一致
```

如果不同：

```text id="6la0so"
拒绝执行
```

防止：

```text id="piq5fb"
same ID
but mutated content
```

### 9.25 [P1] 什么是 CandidateSet？

CandidateSet 不只是：

```text id="elqsvf"
[]Candidate
```

在高风险 Agent Runtime 中，它更适合作为：

> **某一次 Discovery 的 materialized immutable result。**

例如：

```text id="yxgj9j"
CandidateSetID
EpisodeID
QueryHash
Candidates
CreatedAt
ValidUntil
```

每个 Candidate 进一步绑定：

```text id="n6jhsq"
MerchantID
CapabilityID
CatalogVersion
SnapshotHash
SnapshotRef
Rank
```

### 9.26 [P1] 为什么要 Materialize CandidateSet？

如果 LLM 第一次：

```text id="m6vw33"
看到 A B C
```

几秒以后 commit selection 时再次：

```text id="jlgf2a"
live query catalog
```

可能得到：

```text id="m5hhgn"
A D E
```

那么：

```text id="epvg0k"
模型选择的是哪个世界里的 B？
```

变得不清楚。 因此：

```text id="x9jid7"
retrieve once
→ persist candidate set
→ model selects from set
→ runtime validates against same set
```

更稳定。

### 9.27 [P1] Materialized Result 和 Live Query 有什么区别？

**Live Query**

每次：

```text id="pw731h"
重新查询当前状态
```

优点：

```text id="8us4e5"
fresh
```

缺点：

```text id="zsqvco"
结果漂移
难 replay
```

**Materialized Result**

把结果：

```text id="k4tagb"
冻结
```

优点：

```text id="4sbtel"
deterministic
auditable
replayable
```

缺点：

```text id="y59jt6"
可能变 stale
```

所以通常需要：

```text id="29mg30"
ValidUntil
```

### 9.28 [P1] Snapshot 和 Freshness 的矛盾怎么解决？

Snapshot：

```text id="qp35fs"
保证稳定
```

但时间越久：

```text id="j2ll68"
越可能 stale
```

所以 CandidateSet：

```text id="xjkrrk"
CreatedAt
ValidUntil
```

commit 前：

```text id="e2z6fu"
now < ValidUntil?
```

如果过期：

```text id="tnab32"
rediscover
```

而不是：

```text id="vts9v5"
继续使用无限期旧 snapshot
```

### 9.29 [P1] TTL 和 ValidUntil 在 Discovery 里有什么区别？

这和 Redis 章节一样。

**Cache TTL**

```text id="g0ip4e"
缓存副本最多存多久
```

**CandidateSet ValidUntil**

```text id="zud9on"
这个决策快照到什么时候仍允许执行
```

例如：

```text id="f6bdn9"
Redis still contains CandidateSet
```

不代表：

```text id="5f67qv"
CandidateSet 仍业务有效
```

所以：

```text id="zzr0b7"
cache existence
≠
decision validity
```

### 9.30 [P1] 什么是 Stale Candidate？

Candidate 在 discovery 时：

```text id="xb1c9q"
valid
```

但 commit 时：

```text id="ighpg3"
expired
```

或者：

```text id="uv9c8l"
catalog version changed
merchant disabled
```

这种候选就是 stale。 执行前要重新检查：

```text id="cw4b2a"
snapshot binding
validity
runtime policy
```

### 9.31 [P1] 为什么 Stale Proposal 和 Stale Candidate 是不同问题？

**Stale Proposal**

模型的决策基于：

```text id="d4ld71"
旧 Episode state
```

例如 BasedOnSequence 不匹配。

**Stale Candidate**

候选本身：

```text id="mdowb7"
业务事实过期
```

两个都可能发生。 所以 commit guard 可能需要同时检查：

```text id="0bsb3b"
proposal sequence
+
candidate snapshot validity
```

### 9.32 [P0] Retrieval 为什么不等于 Authorization？

搜索出：

```text id="0mvkq2"
Tool X
```

只表示：

```text id="nm3f67"
它看起来符合检索条件
```

不代表当前 Agent：

```text id="201dea"
有权限执行 Tool X
```

例如：

```text id="dq83kd"
SearchResult:
wire_transfer_tool
```

Authorization：

```text id="jmmta8"
Agent budget = 0
```

应该拒绝。 所以：

```text id="2itx0x"
Retrieval
→ what exists / looks relevant

Authorization
→ what this principal may execute
```

### 9.33 [P1] Retrieval 为什么也不等于 Factual Authority？

这是 S4 后必须补上的一层。 检索系统可能返回：

```text id="uh09c8"
Merchant M
price_hint = 2 USDC
payee = P
```

这些字段可能来自：

```text id="b1u4c1"
index
embedding metadata
old catalog snapshot
```

真正执行支付时，Merchant 又返回：

```text id="1kmkg7"
HTTP 402 PaymentRequirement
```

包含：

```text id="o24zxn"
atomic amount
asset
network
payTo
resource
```

此时不能简单：

```text id="3w6x9s"
用 Search Result 替代 Payment Requirement
```

也不能：

```text id="lr984b"
无条件相信 Payment Requirement
```

而应：

```text id="w6yl7i"
Catalog Fact
+
Merchant Protocol Fact
+
Runtime Binding
+
Policy
```

共同决定可执行事实。

### 9.34 [P1] 什么是 Retrieval Trust Level？

不同字段可以有不同信任等级。 例如：

**Low Trust**

```text id="ced8xa"
semantic description
LLM-generated tags
search summary
```

适合：

```text id="om2xud"
ranking
```

**Medium Trust**

```text id="8is7qm"
indexed structured metadata
```

适合：

```text id="rtkyoa"
candidate filtering
```

但可能有同步延迟。

**High Trust**

```text id="7d7ovh"
versioned authoritative catalog
merchant signed protocol fact
ledger fact
```

可以进入：

```text id="l7ilpb"
execution guard
```

前提仍需验证其适用上下文。

### 9.35 [P2] 为什么 Field-level Trust 比“这个服务可信”更准确？

一个 Merchant Catalog 可能：

```text id="0q5erw"
Description
```

由 merchant 自己自由填写。 同时：

```text id="giytpt"
PayeeDID
```

来自经过验证的注册流程。 二者都在同一个 JSON：

```text id="f0pz2u"
但 trust 不一样
```

所以更准确：

```text id="09n9f0"
trust(field, source, version, verification)
```

而不是：

```text id="id8vxp"
trust whole object = true
```

### 9.36 [P2] Search Index 和 Authoritative Database 有什么区别？

Search Index 通常是：

```text id="cfz7f9"
derived projection
```

例如：

```text id="b1tx4f"
MySQL Catalog
     ↓
CDC
     ↓
Search Index
```

Index 可能：

```text id="prb5jr"
延迟
缺少最新更新
重建中
```

所以：

```text id="gmyg74"
search index
```

适合：

```text id="g6khhs"
recall / ranking
```

但执行前：

```text id="0l1m0n"
最好回源 authoritative catalog
```

验证关键字段。

### 9.37 [P2] 为什么 Search Index 适合“找”，不一定适合“执行”？

因为它优化目标是：

```text id="m9lplw"
search performance
```

可能接受：

```text id="anipma"
eventual consistency
```

而 execution guard 需要：

```text id="dr7wgj"
stronger freshness / version binding
```

所以常见架构：

```text id="gdebd5"
Search Index
→ Candidate IDs

Authoritative Store
→ Candidate Facts

Runtime Guard
→ Execution
```

### 9.38 [P1] 什么是 Dynamic Index？

Dynamic Index：

> 随业务对象变化持续更新的检索索引。

例如：

```text id="erqil7"
Merchant added
→ index

Merchant disabled
→ update index

Capability changed
→ new document
```

它可以：

```text id="s78drw"
快速 discovery
```

但不能忘记：

```text id="tk3237"
index synchronization lag
```

### 9.39 [P1] Index Staleness 怎么处理？

至少有三种策略。

**1. Execution-time Revalidation**

Search：

```text id="awtdip"
index candidate
```

执行前：

```text id="q0pdwg"
authoritative store validate
```

最常见。

**2. Versioned Index**

Index document 带：

```text id="3eaj9n"
catalog_version
```

Runtime：

```text id="fg4mn0"
fetch exact version
```

**3. Short Index SLA**

要求：

```text id="8sz5ot"
index update lag < X seconds
```

但这只能减少 stale。 不能完全消除。

### 9.40 [P1] 什么是 Semantic Tag？

Structured fields 太严格：

```text id="6s4s1h"
task_type = transcription
```

自由 description 又太模糊。 Semantic Tags 可以作为中间层：

```text id="fddz38"
speech-to-text
language=en
podcast
low-latency
```

可以用于：

```text id="bsdyxg"
structured filter
+
semantic retrieval
```

### 9.41 [P1] LLM 生成 Tag 能直接进入 Hard Filter 吗？

通常不应该。 LLM tag：

```text id="rb68tq"
可能 hallucinate
```

如果它决定：

```text id="uhdndd"
currency supported
security certification
payee identity
```

就会把 probabilistic inference 提升成 authority。 所以：

```text id="fnmm15"
LLM-derived tags
```

更适合：

```text id="mfhsyx"
soft recall / ranking
```

而关键资格字段：

```text id="gkrshg"
protocol
currency
status
payee
```

应该来自权威结构化数据。

### 9.42 [P1] 什么是 Hybrid Retrieval？

Hybrid Retrieval：

```text id="d2vpym"
lexical
+
semantic
```

组合。 例如：

```text id="hbga9s"
BM25 score
+
embedding score
```

优势：

* lexical 擅长精确名词、ID、专有术语；
* semantic 擅长同义表达、自然语言。

### 9.43 [P1] Hybrid Score 怎么合并？

可以：

```text id="oa4yhx"
normalized lexical score
+
normalized semantic score
```

或者：

```text id="zgbtei"
rank fusion
```

例如更稳健的：

```text id="89339p"
Reciprocal Rank Fusion
```

思想是：

```text id="in50pz"
不直接比较不同模型原始分数
```

而比较：

```text id="tb85cx"
rank position
```

### 9.44 [P1] 为什么不能直接把 BM25 和 Cosine 分数相加？

因为：

```text id="2hz4pu"
BM25 = 14.2
cosine = 0.83
```

量纲和分布不同。 直接：

```text id="argb2v"
14.2 + 0.83
```

没有稳定意义。 应：

```text id="by3xg0"
normalize
calibrate
or
rank fusion
```

### 9.45 [P1] RAG 和 Capability Discovery 有什么相似点？

都有：

```text id="6cg020"
Query
→ Retrieve
→ Rank
→ Provide context to model
```

但最终目标不同。

**Knowledge RAG**

目标：

```text id="vgs79q"
帮助模型回答问题
```

**Capability Discovery**

目标：

```text id="m4o1jh"
找到可执行对象
```

因此后者需要更多：

```text id="2ojz0q"
authority
version
policy
side-effect safety
```

### 9.46 [P1] RAG 为什么不能直接提供支付事实？

RAG 返回：

```text id="aqa9sv"
document chunk:
“价格约为 10 USDC”
```

这只能作为：

```text id="bb3y0r"
knowledge context
```

不能直接：

```text id="2m7kcq"
pay amount = 10
```

因为文档可能：

```text id="wyok2w"
outdated
ambiguous
untrusted
```

支付事实必须来自：

```text id="2ae1jk"
structured authoritative protocol
```

### 9.47 [P1] Structured Facts 和 RAG 应该怎么配合？

一个很实用的分工：

```text id="yukl78"
RAG / Semantic Search
→ understand / recall

Structured Store
→ validate / execute
```

例如：

```text id="pyls2q"
用户：
“我想找一个便宜的英文音频转写服务”

Semantic retrieval:
找到 transcription capabilities

Structured filter:
currency=USDC
protocol=x402
status=active

Authoritative snapshot:
endpoint/payee/version

Merchant protocol:
actual quote

Runtime guard:
budget/resource/payee binding
```

### 9.48 [P2] 为什么“搜索结果就是事实”是危险设计？

Search Result 可能是：

```text id="6bs6jn"
denormalized
cached
eventually consistent
summarized
LLM-enriched
```

它主要为了：

```text id="8jwzbl"
searchability
```

不一定为了：

```text id="dcgt49"
transaction correctness
```

所以：

```text id="cmqwjx"
search result
```

通常应该被当成：

```text id="fs8pfb"
reference / candidate
```

而不是：

```text id="mzrt2l"
execution authority
```

### 9.49 [P1] 什么是 Retrieval Provenance？

Retrieval result 不应该只有：

```text id="9aj1yq"
text
score
```

高质量系统还可以记录：

```text id="vij07d"
source
document ID
version
retrieval time
index version
snapshot ref
```

这样后续能回答：

```text id="nchifh"
这个候选从哪里来的？
```

### 9.50 [P1] Retrieval Provenance 和 Observation Provenance 有什么关系？

Retrieval 是一种 Observation。 所以应该继承前面 Agent Runtime 的原则：

```text id="yj8grg"
Observation
→ source
→ version
→ timestamp
→ payload hash
```

否则模型看到：

```text id="rymg19"
Candidate A
```

但以后无法知道：

```text id="dvgept"
Candidate A 来自哪个数据版本
```

### 9.51 [P2] 什么是 CandidateSet Hash？

将：

```text id="2b1sdv"
candidate identities
versions
snapshot hashes
ranking
```

canonicalize 后：

```text id="tv2s08"
Hash(CandidateSet)
```

可以得到：

```text id="y9d2me"
CandidateSetHash
```

DecisionProposal 绑定这个 hash。 Commit 时：

```text id="vwpa2d"
hash mismatch
→ reject
```

防止 CandidateSet 被悄悄替换。

### 9.52 [P2] 为什么 CandidateSet ID 单独不一定够？

如果存储允许：

```text id="otizjd"
UPDATE candidate_set
```

相同：

```text id="vg7wz8"
CandidateSetID
```

可能内容已变化。 所以更强绑定：

```text id="f1j7md"
CandidateSetID
+
CandidateSetHash
```

或者 CandidateSet 本身 immutable。

### 9.53 [P1] 什么是 Deterministic Discovery？

给定：

```text id="9rti2s"
same authoritative snapshot
same query constraints
same ranking algorithm version
```

输出：

```text id="stl4si"
same candidates
same order
```

这叫 deterministic discovery。

### 9.54 [P2] 为什么 Ranking Algorithm 也应该 Versioning？

今天：

```text id="7lqrx4"
score =
0.8 relevance
+
0.2 price
```

明天：

```text id="mi6oqh"
0.5 relevance
+
0.3 reliability
+
0.2 price
```

同一 query：

```text id="gl6ryp"
结果不同
```

如果需要 replay：

```text id="r0ym0r"
必须知道当时用了 ranking v1 还是 v2
```

所以高审计 Discovery 可以记录：

```text id="0jz9wh"
retrieval_version
ranking_version
```

### 9.55 [P1] 什么是 Discovery Budget？

检索也有成本。 例如：

```text id="kl077a"
max candidates
max retrieval latency
max vector queries
max reranker calls
```

Agent 如果无限：

```text id="w4iv4r"
search again
search again
search again
```

会变成：

```text id="vksvyf"
unbounded execution
```

所以 Agent Runtime 可以给 Discovery：

```text id="5eyz77"
step budget
latency budget
candidate budget
```

### 9.56 [P2] Discovery Loop 为什么也需要停止条件？

例如：

```text id="bc7lc3"
Search
→ no good candidate
→ rewrite query
→ search
→ no good candidate
→ rewrite
...
```

必须有：

```text id="a8yamh"
max search rounds
deadline
minimum acceptable score
no-candidate terminal state
```

否则：

```text id="mkadgo"
Agent loop
```

可能永远搜。

### 9.57 [P1] 为什么 No Candidate 应该是合法结果？

错误设计：

```text id="eh87uv"
没有候选
→ LLM 随便选一个最接近的
```

在支付/工具调用场景很危险。 应该允许：

```text id="96hm23"
NO_ELIGIBLE_CANDIDATE
```

成为合法终态。 因为：

```text id="8f12b8"
无解
```

比：

```text id="0b9wyw"
执行不符合约束的工具
```

更安全。

### 9.58 [P1] 为什么 Top-1 不等于“正确答案”？

Ranking：

```text id="m5nixi"
输出一个相对排序
```

Top-1 只代表：

```text id="5zc5nd"
在当前打分函数下最高
```

不代表：

```text id="a8t89x"
满足全部业务条件
绝对可靠
一定应该执行
```

所以：

```text id="v5351i"
Top-1
```

仍要过：

```text id="in4bx8"
hard guard
```

### 9.59 [P1] Confidence Score 应该如何理解？

LLM：

```text id="f3eq07"
confidence = 0.95
```

通常只是：

```text id="lbadjd"
模型内部自报告
```

不能直接当：

```text id="fsz3mq"
成功概率 95%
```

除非经过：

```text id="hjfzng"
calibration
```

验证。 所以 Confidence 更适合：

```text id="hdur75"
routing
human review threshold
fallback
```

而不是成为 security authority。

### 9.60 [P2] 什么是 Calibration？

如果系统说：

```text id="unvud1"
confidence ≈ 0.8
```

那么长期来看：

```text id="g2sayu"
约 80% 类似预测应正确
```

才算较好 calibrated。 模型 raw confidence：

```text id="doqydn"
往往不天然满足
```

所以高风险决策不能只看：

```text id="qwkzzj"
model confidence
```

### 9.61 [P1] Retrieval Evaluation 看什么指标？

至少：

```text id="8nv4b7"
Recall@K
Precision@K
MRR
NDCG
Latency
```

不同目标不同。

### 9.62 [P1] Recall@K 是什么？

例如：

```text id="u9ule7"
Top 10
```

中是否召回相关候选。 对于每个 query：

```text id="z8mu5o"
有多少 ground-truth relevant items
进入 TopK
```

适合评估：

```text id="hcw4dn"
candidate generation
```

### 9.63 [P1] MRR 是什么？

MRR：

```text id="oo1vea"
Mean Reciprocal Rank
```

如果第一个正确候选排名：

```text id="ns144g"
rank = 1
→ score 1

rank = 2
→ score 1/2

rank = 10
→ score 1/10
```

适合：

```text id="n1zcsw"
强调第一个正确结果尽量靠前
```

### 9.64 [P1] NDCG 大概解决什么？

NDCG 适合：

```text id="mfryaz"
多个候选具有不同相关程度
```

例如：

```text id="8fddnt"
A = perfect
B = good
C = somewhat relevant
```

不仅判断：

```text id="fpuud2"
relevant / irrelevant
```

还关注：

```text id="7u6b9z"
高相关结果是否更靠前
```

### 9.65 [P2] Discovery Evaluation 为什么不能只看 Retrieval Metric？

Agent Commerce 最终还要关心：

```text id="zr3v4h"
constraint violation rate
invalid candidate rate
execution success
cost
latency
recovery rate
```

一个模型：

```text id="o7m7aa"
Recall@10 很高
```

但经常返回：

```text id="4dptse"
inactive merchant
unsupported protocol
stale quote
```

仍然不好用。

### 9.66 [P2] Offline Retrieval Eval 和 Online Business Eval 有什么区别？

**Offline**

固定数据集：

```text id="iy9a43"
query
ground truth
```

计算：

```text id="1lcl23"
Recall@K
MRR
NDCG
```

**Online**

看：

```text id="rvdoc3"
selection success
conversion
latency
failure
cost
```

但在线指标容易被：

```text id="x61r6f"
用户行为
流量分布
系统变化
```

影响。 所以两者结合。

### 9.67 [P2] 为什么 Discovery Test 需要固定 Snapshot？

如果测试每次访问 live catalog：

```text id="1wr6cy"
今天 100 merchants
明天 105
```

测试结果变化：

```text id="hy17su"
不知道是算法变了
还是数据变了
```

所以 eval 最好绑定：

```text id="cpxrlx"
dataset snapshot
catalog version
ranking version
```

才能做可重复实验。

### 9.68 [P2] 什么是 Retrieval Drift？

随着：

```text id="s23i07"
catalog changes
embedding model changes
ranking model changes
query distribution changes
```

检索质量可能逐渐变化。 这就是：

```text id="20ual9"
retrieval drift
```

需要：

```text id="qcm8su"
periodic evaluation
```

### 9.69 [P2] Embedding Model Upgrade 为什么危险？

旧 index：

```text id="n37kdu"
embedding model v1
```

Query 升级成：

```text id="56vxkn"
model v2
```

向量空间可能：

```text id="2n445z"
不兼容
```

不能假设：

```text id="37czs1"
都是 1536 dimensions
→ 可以混
```

升级通常需要：

```text id="r9ral9"
re-embed corpus
version index
controlled rollout
```

### 9.70 [P2] 为什么 Vector Dimension 相同也不代表 Embedding Compatible？

Embedding 坐标语义由模型定义。 两个模型即使：

```text id="oxsueo"
dimension = 1024
```

向量：

```text id="y31ro3"
coordinate meaning
```

完全不同。 所以：

```text id="5ei66j"
same shape
≠
same vector space
```

### 9.71 [P1] Vector Search 为什么常用 ANN？

全量 exact search：

```text id="gn1fc7"
query vector
vs
millions vectors
```

成本高。 ANN：

```text id="6z8awn"
Approximate Nearest Neighbor
```

牺牲少量：

```text id="lnq6ln"
recall
```

换：

```text id="o9xk02"
latency
throughput
```

### 9.72 [P1] ANN 的“Approximate”意味着什么？

不是每次保证找到：

```text id="dl14v5"
真正全局最近向量
```

而是：

```text id="itd7sp"
高概率找到足够接近候选
```

所以对于 authority-sensitive lookup：

```text id="wqnham"
不能只依赖 ANN
```

例如：

```text id="gs1zpv"
lookup exact merchant ID
```

应该 structured exact lookup。

### 9.73 [P2] Semantic Retrieval 和 Exact Identity Lookup 为什么必须分开？

用户自然语言：

```text id="mtbdxz"
“帮我找转录服务”
```

适合 semantic。 但 Commit Proposal 已经选择：

```text id="u0xgn7"
MerchantID=M1
CapabilityID=C1
Version=v3
```

这时应该：

```text id="r0lret"
exact lookup
```

而不是再次：

```text id="xppq39"
semantic search M1 C1
```

因为执行阶段需要：

```text id="c1im8l"
identity-preserving lookup
```

### 9.74 [P2] Discovery Plane 和 Execution Plane 应该怎么分？

**Discovery Plane**

允许：

```text id="mypwh4"
approximate
semantic
eventually consistent index
ranking
```

目标：

```text id="vagchn"
找到候选
```

**Execution Plane**

要求：

```text id="ka8hv5"
exact identity
authoritative version
policy validation
deterministic binding
```

目标：

```text id="0qxfhh"
安全执行
```

所以：

```text id="hnq1cn"
Approximate Discovery
+
Deterministic Execution
```

是一个很重要的设计模式。

### 9.75 [P2] 为什么这是 Agent Commerce 很核心的架构边界？

LLM 擅长：

```text id="pc7e0u"
模糊意图
语义理解
候选比较
```

数据库和规则擅长：

```text id="n01uoe"
身份
金额
版本
约束
事务
```

如果反过来：

```text id="p18xoz"
LLM 决定精确 payee / amount / authority

DB 只负责存结果
```

就把：

```text id="djbdvf"
probabilistic component
```

放在了：

```text id="va0w5d"
correctness boundary
```

上。 更合理：

```text id="k3fm7w"
LLM
→ choose

Runtime
→ verify

Authoritative systems
→ provide facts

Side-effect layer
→ execute
```

### 9.76 高频错误设计：只用 Vector Search，不做 Structured Filter

结果可能语义很相关：

```text id="l35vx1"
但 currency 不支持
protocol 不支持
merchant inactive
budget 超限
```

所以：

```text id="q9f5by"
semantic relevance
```

不是：

```text id="etg7cc"
business eligibility
```

### 9.77 高频错误设计：把 Ranking Score 当可信度

```text id="q7exvf"
cosine = 0.99
```

只代表：

```text id="m6w6to"
embedding space 很接近
```

不代表：

```text id="eiwem5"
数据正确
merchant 可信
事实最新
```

### 9.78 高频错误设计：每次 Commit 都重新 Search

模型：

```text id="6q4nre"
基于 CandidateSet A
```

做出选择。 Runtime：

```text id="qvw81k"
重新 Search
```

得到 CandidateSet B。 然后把：

```text id="6vghkj"
A 的 Decision
```

应用到：

```text id="ye4izc"
B 的世界
```

容易产生 TOCTOU。

### 9.79 高频错误设计：Candidate 只存 Merchant ID

如果只存：

```text id="qn7hei"
merchant=M1
```

但 M1 的：

```text id="f94uqe"
payee
endpoint
price
protocol
```

以后都变化。 就无法知道模型当时选的是：

```text id="dc13hz"
M1 哪个版本
```

至少应绑定：

```text id="m57sts"
capability
version
snapshot
```

### 9.80 高频错误设计：有 Version 字段就认为不可变

如果 DB 允许：

```text id="0bmtqv"
UPDATE WHERE version='v1'
```

那么：

```text id="d48c7h"
v1
```

只是一个 label。 真正 version semantics 需要：

```text id="f73yy0"
immutable version content
```

### 9.81 高频错误设计：Cache TTL 当 Candidate Validity

Redis key：

```text id="wmp4tp"
还没过期
```

并不代表：

```text id="kxy864"
merchant quote
catalog snapshot
candidate
```

仍然合法。 业务 validity 必须独立判断。

### 9.82 高频错误设计：RAG 文档说多少钱就直接支付

RAG：

```text id="uzbl59"
“服务价格 2 USDC”
```

只应该帮助：

```text id="oy421a"
理解 / discovery
```

真正执行金额应来自：

```text id="nriv4c"
authoritative quote / payment requirement
```

并与：

```text id="qhm70t"
budget
catalog
payee
resource
```

绑定。

### 9.83 高频错误设计：LLM 生成 Merchant Address

如果模型：

```text id="7htn8w"
根据上下文输出 payee address
```

然后直接付款。 这相当于把：

```text id="opypbe"
factual authority
```

交给概率模型。 更安全：

```text id="dcvj73"
LLM outputs candidate ID

Runtime exact-resolves candidate

Trusted snapshot provides payee identity
```

### 9.84 高频错误设计：No Candidate 时强行选择 Top-1

如果所有候选：

```text id="vpgq8r"
都违反 hard constraint
```

正确结果是：

```text id="xw9ijy"
NO_ELIGIBLE_CANDIDATE
```

不是：

```text id="byu6qg"
“选最接近的”
```

### 9.85 本章高频对比

| 概念 A                  | 概念 B                      | 核心区别                |
| --------------------- | ------------------------- | ------------------- |
| Structured Search     | Semantic Search           | 明确字段条件 vs 语义相似      |
| Full-text             | Semantic                  | 词法匹配 vs 含义匹配        |
| Recall                | Precision                 | 别漏掉相关结果 vs 返回结果更干净  |
| Retrieval             | Reranking                 | 找候选 vs 重排候选         |
| Hard Filter           | Ranking                   | 是否有资格 vs 谁更优        |
| Top-1                 | Authorized Choice         | 排名第一 vs 允许执行        |
| Catalog               | Search Index              | 权威业务登记 vs 派生搜索结构    |
| Registry              | Catalog                   | 注册/位置更强 vs 能力业务属性更强 |
| Version               | Snapshot                  | 单对象历史版本 vs 决策时完整事实  |
| Version ID            | Snapshot Hash             | 逻辑版本标识 vs 内容完整性绑定   |
| Live Query            | Materialized CandidateSet | 最新结果 vs 冻结决策上下文     |
| Cache TTL             | ValidUntil                | 副本存活时间 vs 业务有效时间    |
| CandidateSet          | Search Result Page        | 可审计决策事实 vs 临时展示结果   |
| Candidate ID          | Candidate Snapshot        | 对象身份 vs 当时完整版本事实    |
| Retrieval             | Authorization             | 找到什么 vs 能执行什么       |
| Retrieval             | Factual Authority         | 搜到的信息 vs 可进入执行的权威事实 |
| Ranking Score         | Confidence                | 排序信号 vs 决策置信描述      |
| Search Index          | Source of Truth           | 派生索引 vs 权威事实        |
| RAG                   | Structured Facts          | 语义知识辅助 vs 确定性业务事实   |
| Approximate Discovery | Deterministic Execution   | 高召回模糊查找 vs 精确安全执行   |
| Semantic Lookup       | Exact Identity Lookup     | 按意义找对象 vs 按身份取对象    |
| LLM Tag               | Authoritative Field       | 推断标签 vs 已验证业务字段     |
| Snapshot Freshness    | Snapshot Determinism      | 越新越好 vs 同一决策上下文稳定   |
| Stale Proposal        | Stale Candidate           | 决策状态旧 vs 候选业务事实旧    |

### 9.86 面试前一分钟速记

```text id="m83jbw"
Discovery 不等于：
“丢进 Vector DB 搜一下”。

Structured Search：
明确约束。

Full-text：
关键词。

Semantic：
语义相似。

Hard Filter：
有没有资格。

Ranking：
合格者中谁更优。

Hard Constraint
不要只做 ranking penalty。

Recall：
别漏。

Precision：
别带太多噪音。

常见 pipeline：

structured eligibility
+
lexical / semantic recall
→ candidate generation
→ rerank
→ TopK。

Ranking score
≠
authority。

Catalog：
结构化能力登记。

Catalog Version：
历史版本。

Snapshot：
当时真正看到的事实。

Historical version 应尽量 immutable。

CandidateSet：
materialized discovery result。

为什么保存 CandidateSet？
因为不能让模型在世界 A 做决策，
Runtime 在世界 B 执行。

CandidateSet 应有：
ID
version/snapshot
CreatedAt
ValidUntil。

TTL
≠
ValidUntil。

Retrieval
≠
Authorization。

Retrieval
也
≠
Factual Authority。

Search Index：
适合找候选。

Authoritative Catalog：
适合 execution-time verification。

LLM：
可以选候选。

LLM：
不能创造 payee / amount / settlement fact。

RAG：
帮助理解。

Structured authoritative facts：
决定执行。

Agent Commerce 很重要的模式：

Approximate Discovery
+
Deterministic Execution。
```

### 9.87 StablePay 映射

这一章只做弱映射。 S3 可以对应：

```text id="9fmr4h"
MerchantCapability
→ authoritative catalog object

CatalogVersion
→ immutable historical capability

CatalogSnapshotHash
→ content binding

CandidateSet
→ materialized discovery result

CandidateSetID
→ proposal reference

ValidUntil
→ stale candidate guard

Stable ranking
→ deterministic candidate ordering
```

S4 又把这条边界继续向后推进：

```text id="qpqp10"
Catalog
告诉 Runtime：

merchant identity
capability identity
trusted endpoint
trusted payee identity
supported protocol
```

但真正 Merchant Invocation 后：

```text id="cokub1"
HTTP 402
```

又产生新的：

```text id="h013ka"
PaymentRequirementFact
```

包括：

```text id="wcqi5u"
atomic amount
network
asset
payTo
resource URL
```

因此：

```text id="gxoz97"
Catalog Fact
```

和：

```text id="iakj5g"
Merchant Protocol Fact
```

不是互相替代。 Runtime 应做：

```text id="5vl00q"
Merchant Protocol Fact
        ↓
bind against
        ↓
Selected Catalog Snapshot
        ↓
Budget / Settlement Policy
```

最后才能形成：

```text id="3fbvxx"
TrustedPaymentQuote
```

这就是本章最值得带走的：

```text id="jthoj4"
Retrieval Fact
+
Protocol Fact
+
Runtime Binding
≠
LLM-generated Fact
```

### 9.88 S4 后尤其值得记的一条 Factual Authority 分层

可以把 Agent Commerce 的事实来源分成：

```text id="vkinul"
User Contract
↓
用户想要什么、预算和约束

Catalog Snapshot
↓
某 merchant/capability 的登记事实

Merchant Protocol Response
↓
这次真实调用返回的支付要求

Settlement System
↓
钱是否真正结算

Delivery Artifact
↓
merchant 实际交付了什么

Validation Evidence
↓
交付是否符合合同

LLM Proposal
↓
基于这些事实建议下一步做什么
```

这里：

```text id="0o3yg5"
LLM
```

的位置始终是：

```text id="rooxxl"
Decision Layer
```

而不是：

```text id="kxncc3"
Fact Layer
```

这是比单纯：

```text id="dy01nu"
Proposal ≠ Authorization
```

更进一步的边界。

### 9.89 本章学习优先级

### 第一轮：P0

必须直接回答：

```text id="6zq3uw"
Structured / Full-text / Semantic
Hard Filter vs Ranking
Recall vs Precision
Catalog
Version
Snapshot
CandidateSet
TTL vs ValidUntil
Retrieval ≠ Authorization
```

### 第二轮：P1

重点：

```text id="rbw8ra"
Candidate Generation
Reranking
Hybrid Retrieval
Stable Tie-breaker
Immutable History
Current vs Historical Version
Materialized CandidateSet
Stale Candidate
Retrieval Provenance
Search Index vs Source of Truth
RAG vs Structured Facts
Factual Authority
```

### 第三轮：P2

针对 Agent / Search / Infra：

```text id="hcirwl"
CandidateSet Hash
Ranking Version
Deterministic Discovery
Retrieval Trust Level
Field-level Trust
Index Staleness
Embedding Versioning
ANN trade-off
Retrieval Drift
Discovery Budget
No-candidate terminal state
Approximate Discovery + Deterministic Execution
```

最终不要把这一章背成：

> “我们使用向量数据库，通过 embedding 相似度搜索商户，然后把 TopK 给 LLM 选择。”

更完整的回答应该是：

> Discovery 应把资格判断和偏好排序分开：协议、货币、状态、预算等 hard constraints 需要确定性过滤，全文与语义检索则负责提高候选召回。高风险 Agent 不应该让模型直接从 live search result 产生执行参数，而应把一次检索结果 materialize 成带版本、snapshot hash 和有效期的 CandidateSet；模型只从这个有限集合提出选择，Runtime 在执行前再按精确 identity 回源 authoritative catalog，验证 snapshot、policy 与 freshness。搜索索引、RAG 文档和模型推断都属于 discovery evidence，而不是支付金额、payee 或 settlement 的 factual authority。一个很实用的架构原则是：**Approximate Discovery，Deterministic Execution。**

## 10. Observability、Testing 与 Production

前面几章解决的是：

```text
系统应该怎么设计才正确？
```

这一章回答：

> **你怎么知道它真的正确？上线以后怎么知道它正在坏？发生故障以后怎么定位、恢复、验证？**

真正的生产工程不是：

```text
代码能跑
+
pytest/go test 通过
+
Docker 启动成功
```

而是建立：

```text
Observability
      +
Testing
      +
Failure Injection
      +
Deployment Safety
      +
Recovery Procedure
```

从而让系统具备：

```text
能发现
能解释
能恢复
能证明
```

四种能力。 对于 Agent Commerce 尤其重要，因为一次流程可能横跨：

```text
Agent Runtime
MySQL
Redis
RocketMQ
Merchant
Payment Provider
Blockchain
Entitlement
Validation
```

其中任何一步：

```text
timeout
duplicate
partial failure
restart
stale state
```

都可能只在生产条件下暴露。

### 10.1 [P0] Observability 是什么？

Observability：

> 根据系统外部产生的信号，理解系统内部正在发生什么。

最经典的三类信号：

```text
Logs
Metrics
Traces
```

也就是：

```text
日志
指标
分布式追踪
```

它们不是互相替代。

### 10.2 [P0] Logs、Metrics、Traces 分别擅长什么？

**Logs**

擅长：

```text
发生了什么具体事件？
```

例如：

```text
payment reconcile failed
event_id=E123
intent_id=P456
reason=provider_timeout
```

**Metrics**

擅长：

```text
系统整体趋势怎么样？
```

例如：

```text
payment_unknown_total
consumer_lag
request_p99
```

**Traces**

擅长：

```text
一次请求跨多个服务到底走了什么路径？
```

例如：

```text
Gateway
→ Runtime
→ Payment
→ Provider
→ RocketMQ
→ Verification
```

### 10.3 [P0] 为什么不能只有日志？

假设：

```text
每天 1 亿行日志
```

你想知道：

```text
过去 10 分钟 payment timeout rate 是否升高？
```

如果只能：

```text
grep logs
```

非常困难。 Metrics 更适合：

```text
聚合
趋势
告警
```

### 10.4 [P0] 为什么不能只有 Metrics？

Metric 告诉你：

```text
payment_failure_rate = 8%
```

但不能直接回答：

```text
是哪一批 merchant？
哪个 request？
什么参数？
哪个 error？
```

这时需要：

```text
logs
+
trace
```

下钻。

### 10.5 [P0] 什么是 Structured Logging？

错误：

```text
"payment failed something wrong"
```

更好的：

```json
{
  "level": "error",
  "event": "payment_reconcile_failed",
  "intent_id": "P123",
  "episode_id": "E456",
  "merchant_id": "M1",
  "error_code": "PROVIDER_TIMEOUT"
}
```

Structured Logging 让日志可以：

```text
filter
aggregate
join
alert
```

而不是只能全文搜索。

### 10.6 [P1] 日志应该记录什么 ID？

分布式系统中至少经常需要：

```text
request_id
trace_id
episode_id
payment_intent_id
event_id
invocation_id
idempotency_key
```

但不是每条日志全部堆进去。 原则：

> **记录能把当前事件连接到业务链路的稳定身份。**

### 10.7 [P1] Trace ID 和 Business ID 有什么区别？

**Trace ID**

表示：

```text
一次执行链路
```

Retry 后：

```text
trace_id
```

可能变化。

**Business ID**

例如：

```text
payment_intent_id
episode_id
```

跨 retry、restart 后仍保持。 所以生产排障经常需要：

```text
Trace ID
+
Business ID
```

两种维度。

### 10.8 [P1] 为什么 Idempotency Key 也值得进入日志？

出现：

```text
duplicate payment?
```

时最需要知道：

```text
两个请求是不是同一个逻辑 command？
```

如果日志只有：

```text
request_id
```

可能看起来是两个不同请求。 加：

```text
idempotency_key
```

才能判断：

```text
transport retry
or
new business command
```

### 10.9 [P0] 常见 Metric 类型有哪些？

四种常见概念：

```text
Counter
Gauge
Histogram
Summary
```

**Counter**

只增加：

```text
requests_total
payment_confirmed_total
```

**Gauge**

当前值：

```text
queue_depth
active_connections
unknown_payment_count
```

可以上升下降。

**Histogram**

观察值分布：

```text
request_latency_seconds
payment_reconcile_duration
```

可以进一步算：

```text
P50
P95
P99
```

### 10.10 [P0] 为什么平均延迟不够？

假设：

```text
999 requests = 10ms
1 request = 10s
```

平均值可能看起来还能接受。 但那个用户体验：

```text
10s
```

极差。 因此线上更关注：

```text
P50
P95
P99
P99.9
```

尤其：

```text
tail latency
```

### 10.11 [P0] P99 是什么意思？

P99：

> 99% 请求延迟不超过这个值。

例如：

```text
P99 = 500ms
```

意味着：

```text
约 99% 请求 <= 500ms
```

不是：

```text
99% 请求正好 500ms
```

### 10.12 [P1] 为什么 P99 在分布式调用链里特别重要？

一次请求 fan-out：

```text
Service A
├→ B
├→ C
├→ D
└→ E
```

最终 latency 常受：

```text
最慢 downstream
```

影响。 多个 downstream：

```text
尾延迟遇到一次的概率
```

会放大。 所以：

```text
平均 latency 很漂亮
```

不代表：

```text
用户尾部体验正常
```

### 10.13 [P0] 什么是 RED Method？

对请求型服务常看：

```text
R = Rate
E = Errors
D = Duration
```

也就是：

```text
请求量
错误率
延迟
```

例如 API Gateway：

```text
requests/s
5xx rate
P95/P99 latency
```

### 10.14 [P1] 什么是 USE Method？

更偏资源：

```text
U = Utilization
S = Saturation
E = Errors
```

例如 DB pool：

```text
Utilization:
多少 connection 正在使用

Saturation:
多少请求正在等待 connection

Errors:
acquire timeout / connection errors
```

### 10.15 [P1] 为什么只看 CPU 不够？

系统可能：

```text
CPU = 30%
```

但：

```text
DB pool exhausted
RocketMQ lag huge
external API rate limited
lock contention
```

服务仍然严重异常。 所以要看：

```text
resource bottleneck
```

真正在哪里。

### 10.16 [P0] 什么是 SLI？

SLI：

```text
Service Level Indicator
```

是实际测量指标。 例如：

```text
successful_request_ratio
P99 latency
payment_reconciliation_age
```

### 10.17 [P0] 什么是 SLO？

SLO：

```text
Service Level Objective
```

是目标。 例如：

```text
99.9% requests successful

99% requests < 500ms
```

### 10.18 [P0] SLA 和 SLO 有什么区别？

**SLO**

内部目标：

```text
我们希望服务达到什么水平
```

**SLA**

通常是：

```text
对外合同/承诺
```

可能包含：

```text
违约补偿
```

所以：

```text
SLA
```

往往不应该等同于内部更严格的：

```text
SLO
```

### 10.19 [P1] 什么是 Error Budget？

如果 SLO：

```text
99.9% availability
```

意味着允许：

```text
0.1%
```

失败。 这部分就是：

```text
error budget
```

概念上：

```text
Error Budget
=
1 - SLO
```

它用于平衡：

```text
reliability
vs
feature velocity
```

### 10.20 [P1] Error Budget 用来做什么？

如果长期：

```text
SLO 很稳定
```

可以更积极：

```text
release
experiment
```

如果：

```text
error budget 快耗尽
```

应该优先：

```text
reliability work
```

而不是继续高速上线高风险改动。

### 10.21 [P1] Agent Commerce 应该有哪些业务 SLI？

除了：

```text
HTTP availability
latency
```

更有价值的是：

```text
episode_success_rate
no_candidate_rate
payment_unknown_count
oldest_unknown_age
reconciliation_success_rate
delivery_validation_failure_rate
retry_count
duplicate_idempotency_hit_rate
```

因为这些更接近：

```text
业务流程是否真正收敛
```

### 10.22 [P1] 为什么 `UNKNOWN` 数量是很重要的 Metric？

单个 UNKNOWN：

```text
可能只是网络波动
```

但如果：

```text
UNKNOWN count
持续增长
```

说明：

```text
reconciliation 跟不上
provider 出问题
recovery worker 故障
```

尤其应看：

```text
count
+
oldest age
```

### 10.23 [P1] 为什么 Age 有时比 Count 更重要？

例如：

```text
10000 UNKNOWN
```

但全部：

```text
刚产生 2 秒
```

可能正常。 反过来：

```text
只有 3 个 UNKNOWN
```

但最老：

```text
7 天
```

说明有业务永远没收敛。 所以：

```text
oldest unresolved age
```

是非常有价值的 reliability metric。

### 10.24 [P1] RocketMQ 应重点监控什么？

至少：

```text
consumer lag
consume rate
produce rate
retry rate
DLQ arrival
oldest unconsumed age
```

如果：

```text
producer rate > consumer rate
```

lag 持续增长。

### 10.25 [P1] Redis 应重点监控什么？

例如：

```text
memory usage
eviction
hit ratio
latency
connection errors
hot key symptoms
```

如果 Redis 承担：

```text
nonce / limiter
```

还应该看：

```text
replay-store error
limiter backend error
fallback activation
```

### 10.26 [P1] DB 应重点监控什么？

至少：

```text
query latency
slow queries
connection pool usage
lock wait
deadlock
transaction duration
replication lag
```

不要看到：

```text
API slow
```

就只查 CPU。

### 10.27 [P0] 什么是 Distributed Trace？

一次请求：

```text
Gateway
→ Runtime
→ Payment
→ Blockchain
```

每一段：

```text
Span
```

共同组成：

```text
Trace
```

典型字段：

```text
trace_id
span_id
parent_span_id
duration
status
attributes
```

### 10.28 [P1] Span 应该表示什么？

通常表示：

```text
一个有明确开始/结束时间的操作
```

例如：

```text
HTTP request
RPC call
DB query
RocketMQ publish
payment reconcile
merchant invoke
```

不要把每一行函数都变成 span。

### 10.29 [P1] 什么是 Trace Context Propagation？

Gateway：

```text
trace_id=T1
```

调用 Payment Service 时：

```text
把 trace context 传过去
```

Payment 再调用 Provider：

```text
继续传
```

这样所有 span 才能组成：

```text
one distributed trace
```

### 10.30 [P1] 异步 MQ 链路怎么 Trace？

同步 HTTP：

```text
parent → child
```

关系清晰。 MQ：

```text
Producer publishes
↓
later
Consumer processes
```

中间可能隔很久。 仍可以在消息 metadata 中传播：

```text
trace context
```

或建立：

```text
linked span
```

但不要因为 tracing：

```text
改变 message business identity
```

### 10.31 [P1] Trace Sampling 是什么？

高 QPS 系统如果：

```text
100% traces
```

成本很高。 所以只采样：

```text
1%
10%
```

等。 但重要错误可以：

```text
always sample error traces
```

或使用更智能策略。

### 10.32 [P1] 为什么 Sampling 会影响排障？

如果一次极罕见 double-submit：

```text
刚好没被采样
```

就没有完整 trace。 所以关键业务还必须依赖：

```text
durable business facts
audit logs
stable IDs
```

不能把 tracing 当唯一审计记录。

### 10.33 [P1] Observability 和 Auditability 有什么区别？

Observability：

```text
理解系统运行状态
```

Auditability：

```text
证明某个业务事实为什么发生
```

Trace 可能：

```text
过期
sampled
```

Ledger / audit facts：

```text
必须更持久
```

所以：

```text
Trace
≠
Ledger
```

### 10.34 [P0] Unit Test 是什么？

Unit Test：

> 尽量隔离单个函数、组件、规则。

适合：

```text
parser
validator
state transition
amount conversion
ranking
```

优点：

```text
fast
deterministic
定位容易
```

### 10.35 [P0] Integration Test 是什么？

Integration Test：

> 验证多个真实组件之间能否正确合作。

例如：

```text
Service
+
MySQL
```

或：

```text
Repository
+
SQLite
```

或者：

```text
RocketMQ producer
+
consumer
```

### 10.36 [P0] End-to-End Test 是什么？

E2E：

```text
Client
→ Gateway
→ Runtime
→ Merchant
→ Payment
→ Delivery
```

尽量覆盖真实完整业务链。 优点：

```text
发现集成问题
```

缺点：

```text
慢
脆
难定位
```

所以不能只有 E2E。

### 10.37 [P1] Contract Test 是什么？

Contract Test：

> 验证两个系统之间约定的接口语义。

例如 Merchant：

```text
unpaid request
→ HTTP 402
→ valid payment requirement
```

paid request：

```text
→ HTTP 200
→ delivery payload
```

测试重点不是内部怎么写。 而是：

```text
外部 observable contract
```

### 10.38 [P1] 为什么 Contract Test 对微服务很重要？

Service A 单测通过。 Service B 单测也通过。 但 A 发送：

```json
{"amount_minor": 100}
```

B 还期待：

```json
{"amount": 1.00}
```

各自单测都可能通过。 Contract Test 可以提前发现：

```text
producer / consumer schema mismatch
```

### 10.39 [P1] Black-box Test 是什么？

Black-box Test：

> 只通过外部接口观察行为，不依赖内部实现细节。

例如启动真实 Merchant Server：

```text
HTTP request
↓
HTTP response
```

验证：

```text
402 challenge
paid response
replay behavior
restart behavior
```

它回答：

> **最终部署出来的程序是不是满足合同？**

### 10.40 [P1] Black-box 和 Unit Test 为什么都需要？

Unit Test：

```text
精确定位一个函数
```

Black-box：

```text
验证实际 composition root
```

可能出现：

```text
单测组件都正确

但

真实 server
没有配置 durable repository
```

只有 black-box：

```text
才能发现 deployment wiring 错误
```

### 10.41 [P1] 什么是 Composition Test？

验证：

```text
dependency wiring
configuration
real adapters
```

是否正确。 例如：

```text
ProductService
```

单测中注入：

```text
durableDeliveryStore
```

但生产 `main.go` 忘记：

```text
SetDeliveryResultRepository(...)
```

单测仍绿。 Composition test 可以抓出这种问题。

### 10.42 [P1] 什么是 Fault Injection？

主动制造：

```text
DB failure
network timeout
crash
partial write
provider error
```

观察系统是否仍满足 invariant。 它不是为了：

```text
让测试更酷
```

而是：

> **把设计文档中的 failure window 变成可执行验证。**

### 10.43 [P1] 为什么 Happy-path Test 不够？

Happy path：

```text
A
→ B
→ C
→ success
```

而实际最危险的是：

```text
A success
B success
CRASH
before C
```

或者：

```text
remote C success
response lost
```

这些正是：

```text
distributed correctness
```

问题所在。

### 10.44 [P2] 什么是 Crash-window Test？

把每一个：

```text
durable boundary
```

和：

```text
side-effect boundary
```

之间都当作可能 crash。 例如：

```text
allocate resource
↓
persist receipt
```

测试：

```text
allocate
↓
inject crash/failure
↓
restart
```

然后验证：

```text
有没有资源泄漏？
会不会重复分配？
能不能恢复？
```

### 10.45 [P2] 为什么 Crash-window Test 要基于 Timeline？

先画：

```text
T1 read
T2 allocate
T3 write receipt
T4 commit
T5 return
```

然后分别问：

```text
crash after T1?
after T2?
after T3?
after T4?
```

这比：

```text
随机 kill 一下
```

更能验证具体 invariant。

### 10.46 [P1] 什么是 Idempotency Concurrency Test？

不是：

```text
for i := 0; i < 2; i++ {
    CallSameRequest()
}
```

而是真正：

```text
Goroutine / Process A
        ↘
         same key
        ↗
Goroutine / Process B
```

同时进入 critical section。 最终验证：

```text
one business effect
same result
```

### 10.47 [P1] 为什么 Sequential Retry Test 不够？

Sequential：

```text
first finished
↓
second starts
```

很多 race 不会出现。 真正危险：

```text
A checks missing
B checks missing
A allocates
B allocates
```

必须并发才能暴露。

### 10.48 [P2] Process-level Concurrency 和 Goroutine-level Concurrency 有什么区别？

同一 Go Process：

```text
sync.Mutex
```

可能让测试通过。 两个 Process：

```text
Process A mutex
Process B mutex
```

互不相关。 所以如果 invariant 依赖：

```text
shared SQLite / DB
```

应该测试：

```text
different repository instances
different connections
甚至 different processes
```

而不是只测 goroutine。

### 10.49 [P2] 什么是 Restart Replay Test？

流程：

```text
request K
↓
business effect committed
↓
response persisted
↓
process stops
↓
new process starts
↓
same K
```

期望：

```text
same logical outcome
```

而不是：

```text
再执行一次 side effect
```

这是：

```text
durable idempotency
```

的重要证明。

### 10.50 [P2] 什么是 Exact Redelivery Test？

第一次：

```json
{
  "gift_code": "A",
  "receipt": "R1"
}
```

Retry 后必须：

```json
{
  "gift_code": "A",
  "receipt": "R1"
}
```

而不是：

```json
{
  "gift_code": "B",
  "receipt": "R2"
}
```

即使两次：

```text
都算业务成功
```

后者不满足：

```text
result idempotency
```

### 10.51 [P2] Exact Redelivery 一定要求 byte-for-byte 相同吗？

不一定。 要区分：

**Semantic Equality**

例如：

```json
{"a":1,"b":2}
```

和：

```json
{"b":2,"a":1}
```

业务语义相同。

**Byte Equality**

原始 bytes 完全相同。 如果协议：

```text
签名绑定原始 bytes
```

或者 response 本身作为：

```text
opaque receipt
```

则 byte equality 可能很重要。 否则：

```text
semantic equality
```

可能足够。 必须先定义 contract。

### 10.52 [P1] 什么是 Result Replay？

第一次执行后持久化：

```text
ResponseJSON
```

Retry：

```text
load persisted response
```

而不是：

```text
re-run builder
```

这样即使 builder 内有：

```text
time.Now()
random
resource allocation
```

也不会产生新结果。

### 10.53 [P2] 为什么 Result Replay 比 Recompute 更安全？

Recompute：

```text
same business state
```

也可能产生：

```text
different timestamp
different nonce
different gift code
different signature
```

如果 response 是：

```text
business artifact
```

这些变化可能破坏幂等。 Persisted Result：

```text
把第一次 outcome 固化
```

### 10.54 [P1] 什么是 Rollback Test？

故意：

```text
事务中途返回 error
```

然后检查：

```text
所有 transactional mutation
是否都没留下
```

例如：

```text
gift code allocated
↓
builder fails
```

事务 rollback 后：

```text
gift code must become reusable
receipt must not exist
```

### 10.55 [P1] 为什么只检查 Error 不够？

Test：

```go
_, err := Execute()
if err == nil { fail }
```

只证明：

```text
函数报告失败
```

没有证明：

```text
DB 没留下半写状态
```

还需要验证：

```text
resource state
receipt state
ledger state
```

### 10.56 [P2] 什么是 Invariant-based Test？

不是只 assert：

```text
state == FULFILLED
```

而是 assert：

```text
PaymentAttemptCount == 1
SettlementEntries == 1
DeliveryAttempts == 2
```

这类测试直接验证：

```text
系统必须永远成立的 invariant
```

比单纯检查最终枚举状态更强。

### 10.57 [P2] 为什么 Counter 很适合做 Acceptance Invariant？

例如一条 recovery path：

```text
payment once
delivery twice
```

期望：

```text
payment_call_count = 1
payment_settlement_count = 1
delivery_attempt_count = 2
```

如果最终：

```text
FULFILLED
```

但：

```text
payment_call_count = 2
```

系统仍然是错误的。

### 10.58 [P2] 什么是 Guard Test？

如果状态：

```text
CLAIMING
```

不允许 Delivery。 测试不能只验证：

```text
returned ErrActionNotAllowed
```

还必须检查：

```text
merchant call count = 0
invocation record absent
delivery record absent
```

即：

> **Guard 必须在 side effect 之前生效。**

### 10.59 [P1] 什么是 Negative Test？

不仅测试：

```text
valid input succeeds
```

也测试：

```text
invalid signature
expired snapshot
unsupported currency
oversized payload
same key different request
stale proposal
```

这些属于：

```text
negative path
```

对安全和协议代码尤其重要。

### 10.60 [P1] 什么是 Table-driven Test？

Go 中常见：

```go
tests := []struct {
    name string
    input ...
    want ...
}{ ... }
```

适合大量：

```text
validation cases
parser cases
error taxonomy
```

减少重复测试框架代码。

### 10.61 [P1] 什么是 Property-based Testing？

不是手写几个具体案例。 而是定义：

```text
永远应该成立的 property
```

例如金额转换：

```text
decode(encode(x)) == x
```

或者：

```text
canonicalize(canonicalize(x))
==
canonicalize(x)
```

然后自动生成大量输入。

### 10.62 [P1] Fuzz Testing 是什么？

Fuzzer 自动生成大量：

```text
unexpected
malformed
boundary
```

输入。 特别适合：

```text
JSON parser
protocol parser
canonicalization
URL handling
```

目标之一：

```text
never panic
never OOM
reject malformed safely
```

### 10.63 [P2] x402 / Protocol Parser 为什么很适合 Fuzz？

它接受：

```text
external untrusted bytes
```

需要处理：

```text
malformed JSON
huge integer
negative number
exponent
missing field
base64 variant
invalid URL
```

手写 testcase 很容易漏。 Fuzz 可以暴露：

```text
panic
integer overflow
parser inconsistency
```

### 10.64 [P1] Deterministic Test 为什么重要？

如果 test 依赖：

```text
real clock
random UUID
live network
```

可能：

```text
今天过
明天失败
```

所以关键逻辑应注入：

```text
clock
ID generator
fake adapter
```

让：

```text
same test
→ same result
```

### 10.65 [P1] 为什么 Clock 应该可注入？

测试：

```text
expires_at
deadline
stale_after
```

如果直接：

```go
time.Now()
```

很难精准控制边界。 注入：

```text
FakeClock
```

可以测试：

```text
T = expiry - 1ns

T = expiry

T = expiry + 1ns
```

### 10.66 [P1] Boundary Test 为什么重要？

很多 bug 出现在：

```text
<
<=
>
>=
```

边界。 例如：

```text
now == expires_at
```

到底：

```text
valid
or
expired
```

必须由 contract 明确定义并测试。

### 10.67 [P1] 什么是 Golden Test？

保存一份：

```text
canonical expected output
```

代码运行后对比。 适合：

```text
canonical serialization
protocol payload
generated config
```

但缺点：

```text
golden file 容易被无脑更新
```

所以必须理解变化意义。

### 10.68 [P1] Snapshot Test 和业务 Snapshot 是一回事吗？

不是。 Testing snapshot：

```text
expected output snapshot
```

业务 snapshot：

```text
decision-time immutable facts
```

只是名字相同。 面试时不要混。

### 10.69 [P1] Race Detector 能发现什么？

Go Race Detector：

```text
go test -race
```

主要发现：

```text
data race
```

即并发 goroutine 对共享内存的不安全访问。 它不能证明：

```text
业务无并发问题
```

### 10.70 [P1] 为什么没有 Data Race 仍可能有 Business Race？

例如：

```text
A:
SELECT balance=100

B:
SELECT balance=100

A:
withdraw 80

B:
withdraw 50
```

所有数据库 driver 内存访问都线程安全。 Race Detector：

```text
完全不会报
```

但业务 invariant 已经破坏。

### 10.71 [P1] Load Test 是什么？

模拟：

```text
大量并发用户
```

观察：

```text
throughput
latency
errors
resource usage
```

目的是了解：

```text
系统容量曲线
```

### 10.72 [P1] Stress Test 和 Load Test 有什么区别？

**Load Test**

在：

```text
预期负载
```

下验证表现。

**Stress Test**

故意：

```text
超过设计容量
```

看：

```text
怎么退化
什么时候崩
能不能恢复
```

### 10.73 [P1] Soak Test 是什么？

长时间运行：

```text
hours / days
```

用于发现：

```text
memory leak
connection leak
slow backlog accumulation
fragmentation
```

短测试可能完全看不出来。

### 10.74 [P2] Spike Test 是什么？

瞬间：

```text
100 req/s
→ 10000 req/s
```

测试：

```text
rate limiter
queue
autoscaling
backpressure
```

能不能承受突发。

### 10.75 [P1] Benchmark 和 Load Test 有什么区别？

Benchmark：

```text
某个函数/组件性能
```

例如：

```text
parser ns/op
allocs/op
```

Load Test：

```text
完整系统在真实并发下的表现
```

不能互相替代。

### 10.76 [P1] Production Capacity 应该看什么？

至少：

```text
throughput
latency
concurrency
resource saturation
```

还要结合：

```text
dependency limits
```

例如：

```text
App can do 10000/s
```

但 Payment Provider：

```text
100/s
```

实际 payment capacity：

```text
≤ provider capacity
```

### 10.77 [P1] Readiness Probe 应测试所有依赖吗？

不一定。 如果 readiness 每次都同步检查：

```text
10 downstreams
```

任何一个短暂异常：

```text
instance 全部下线
```

可能形成：

```text
cascading failure
```

应该问：

```text
这个依赖是否是接请求的必要条件？
```

### 10.78 [P1] Readiness 和 Dependency Health 怎么分？

可以：

```text
/readiness
```

只反映：

```text
是否能安全接流量
```

同时暴露：

```text
dependency health metrics
```

例如：

```text
redis degraded
```

不一定代表整个服务：

```text
not ready
```

取决于 fallback 和业务语义。

### 10.79 [P2] 为什么 Health Check 不能制造更多故障？

如果：

```text
1000 pods
```

每秒对 DB：

```text
SELECT heavy_query
```

做健康检查。 本身可能：

```text
把 DB 打爆
```

Health check 应：

```text
cheap
bounded
```

### 10.80 [P0] 什么是 Graceful Shutdown Test？

测试：

```text
server receiving traffic
↓
SIGTERM
```

是否：

```text
stop accepting new requests
drain in-flight
stop new MQ consume
finish bounded work
close resources
```

而不是只测试：

```text
server.Close() returns nil
```

### 10.81 [P1] 为什么 MQ Consumer 要测试 Shutdown？

假设 Consumer：

```text
processing message
```

Deployment：

```text
SIGTERM
```

如果立即 exit：

```text
message redelivers
```

这本身可接受。 但业务必须：

```text
idempotent
```

所以 graceful shutdown 和 consumer idempotency 是配合关系。

### 10.82 [P1] 什么是 Deployment Rollout？

新版本：

```text
v2
```

不是瞬间替换全部：

```text
v1
```

常见：

```text
rolling update
```

逐步替换。 这意味着一段时间：

```text
v1
+
v2
```

同时运行。

### 10.83 [P1] 为什么 Rolling Update 要求向后兼容？

例如 v2 Producer 开始发送：

```json
{
  "schema_version": 2
}
```

但 v1 Consumer 仍在线。 如果：

```text
v1 不能解析
```

部署期间就会失败。 所以：

```text
schema evolution
```

必须考虑：

```text
mixed-version window
```

### 10.84 [P1] 什么是 Canary Release？

先把：

```text
1%
5%
```

流量给新版本。 观察：

```text
errors
latency
business metrics
```

正常再扩大。 降低：

```text
blast radius
```

### 10.85 [P1] Blue-Green Deployment 是什么？

维护两套：

```text
Blue = old
Green = new
```

新版本准备完成后：

```text
switch traffic
```

优点：

```text
rollback 快
```

代价：

```text
资源成本更高
数据兼容仍要处理
```

### 10.86 [P1] 为什么 Application Rollback 不等于 Database Rollback？

新代码上线：

```text
migration alters schema
```

再把 App：

```text
rollback to old version
```

旧版本可能：

```text
不认识新 schema
```

所以 deployment 需要：

```text
schema compatibility
```

设计。

### 10.87 [P2] 什么是 Expand-Contract Migration？

先：

```text
Expand
```

增加新字段/结构，同时旧代码仍能工作。 然后：

```text
deploy new application
migrate data
```

最后：

```text
Contract
```

删除旧结构。 避免：

```text
schema change
和
application change
```

强耦合成一次原子部署。

### 10.88 [P2] 为什么不能先 Rename Column 再上线新代码？

旧版本还在：

```text
rolling deployment
```

它仍读：

```text
old_column
```

直接 rename：

```text
old pods fail
```

所以更安全：

```text
add new column
dual-read/write if needed
migrate
switch
remove old later
```

### 10.89 [P1] Feature Flag 有什么用？

可以：

```text
代码已经部署
```

但功能：

```text
尚未打开
```

遇到异常：

```text
disable feature
```

而不必立刻重新部署。 但 Feature Flag 也会产生：

```text
configuration complexity
```

旧 flag 要清理。

### 10.90 [P1] 什么是 Kill Switch？

对高风险功能：

```text
支付
Agent autonomous action
```

准备快速：

```text
disable execution
```

能力。 例如：

```text
discovery 可以继续
payment execution disabled
```

属于：

```text
operational safety boundary
```

### 10.91 [P1] 什么是 Runbook？

Runbook：

> 某类生产事故发生以后，人应该具体怎么做。

例如：

```text
RocketMQ consumer lag high
```

Runbook：

```text
1. check produce/consume rate
2. check consumer errors
3. check DB saturation
4. check poison message / DLQ
5. decide scale or throttle
6. verify lag recovery
```

不是一篇架构介绍。

### 10.92 [P1] 为什么 Alert 必须对应 Action？

差的 Alert：

```text
CPU > 70%
```

收到后：

```text
然后呢？
```

好的 Alert 应让 on-call 知道：

```text
用户影响是什么？
可能原因是什么？
第一步看什么？
```

否则就是：

```text
alert fatigue
```

### 10.93 [P1] 什么是 Alert Fatigue？

大量：

```text
无行动价值
重复
低优先级
```

告警。 工程师最终：

```text
忽略告警
```

真正重大事故也可能被淹没。 所以 Alert 更应该基于：

```text
SLO / user impact
```

而不是所有指标都设阈值。

### 10.94 [P1] Symptom-based Alert 和 Cause-based Alert 有什么区别？

**Symptom**

```text
payment success rate drops
```

直接代表用户影响。

**Cause**

```text
Redis CPU high
```

只是可能原因。 通常 Paging 更优先：

```text
symptom
```

Cause metric 用于：

```text
diagnosis
```

### 10.95 [P1] 什么是 Incident Timeline？

事故复盘按：

```text
T0 first symptom
T1 alert
T2 operator noticed
T3 mitigation
T4 recovery
```

整理。 帮助回答：

```text
检测为什么慢？
恢复为什么慢？
```

### 10.96 [P1] Postmortem 应该关注什么？

不是：

```text
谁写的 bug？
```

而是：

```text
为什么一个 bug 可以穿透所有防线？
```

例如：

```text
unit test 没覆盖
contract test 没覆盖
canary metric 没告警
reconciliation 没发现
```

寻找：

```text
systemic improvement
```

### 10.97 [P2] 什么是 MTTR？

MTTR 常表示：

```text
Mean Time To Recovery / Repair
```

具体组织定义可能不同。 它关注：

```text
事故发生后多久恢复
```

生产可靠性不仅是：

```text
减少事故
```

还要：

```text
缩短恢复时间
```

### 10.98 [P2] 为什么 Recovery Test 很重要？

系统设计文档里说：

```text
可以从 durable state 恢复
```

但如果从来没测试：

```text
真的 restart
真的 replay
真的 reconcile
```

这只是：

```text
理论恢复能力
```

不是已验证能力。

### 10.99 [P2] 什么是 Disaster Recovery Drill？

主动演练：

```text
DB failover
broker outage
region loss
credential rotation
```

验证：

```text
backup
restore
runbook
people
```

是否真的有效。

### 10.100 [P2] Backup 存在为什么不等于可恢复？

你可能每天都有：

```text
backup file
```

但：

```text
从没 restore
```

可能：

```text
backup corrupted
schema incompatible
missing encryption key
restore too slow
```

所以需要：

```text
restore test
```

### 10.101 [P1] RPO 和 RTO 是什么？

**RPO**

```text
Recovery Point Objective
```

能接受最多丢多少时间范围的数据。 例如：

```text
RPO = 5 min
```

**RTO**

```text
Recovery Time Objective
```

事故后多久恢复服务。 例如：

```text
RTO = 30 min
```

### 10.102 [P1] 为什么 RPO/RTO 是业务问题，不只是运维问题？

支付 Ledger：

```text
RPO = 1 day
```

通常无法接受。 普通推荐缓存：

```text
丢一天
```

可能可以重新构建。 因此：

```text
recovery requirements
```

来自数据价值。

### 10.103 [P1] 什么是 Production Parity？

测试环境应该尽量接近：

```text
production architecture
```

否则：

```text
local SQLite works
production MySQL differs

fake MQ works
real RocketMQ differs
```

可能隐藏问题。 但不意味着：

```text
测试环境必须和生产完全同规模
```

而是关键语义应一致。

### 10.104 [P1] Mock 的风险是什么？

Mock 很方便。 但如果 Mock：

```text
永远返回理想响应
```

你不会发现：

```text
timeout
invalid schema
duplicate
strange HTTP status
```

所以高质量测试组合：

```text
unit fake
+
integration real dependency
+
black-box contract
```

### 10.105 [P2] 什么是 Fault Model？

在设计测试前明确：

```text
我们假设什么会失败？
```

例如：

```text
process crash
network timeout
response loss
duplicate request
DB transaction failure
MQ redelivery
dependency restart
```

然后逐项测试。

### 10.106 [P2] 为什么 Testing 应该来自 Failure Model？

如果系统最危险 failure 是：

```text
response lost after side effect
```

但测试 100% 都在：

```text
validation input cases
```

覆盖率再高：

```text
也没测到真正风险
```

所以：

```text
test plan
```

应该映射：

```text
threat model
+
failure model
+
business invariants
```

### 10.107 [P2] Code Coverage 能证明正确吗？

不能。 100% line coverage：

```text
所有代码至少执行过
```

不代表：

```text
所有并发 interleaving
所有 crash window
所有业务 invariant
```

都验证了。 Coverage 是：

```text
测试盲区提示
```

不是 correctness proof。

### 10.108 [P2] 为什么测试名称应该描述 Invariant？

差：

```text
TestService2
```

好：

```text
TestSameIdempotencyKeyAllocatesOneGiftCode
```

或者：

```text
TestDeliveryRetryDoesNotCreateSecondPayment
```

测试名称本身表达：

```text
被保护的 invariant
```

### 10.109 [P2] 什么是 Model-based / State-machine Testing？

定义：

```text
states
allowed transitions
commands
invariants
```

自动生成不同操作序列：

```text
Create
Select
Pay
Retry
Validate
...
```

检查：

```text
永远不会进入非法状态
```

很适合：

```text
workflow
payment state machine
agent runtime
```

### 10.110 [P2] 为什么 Agent Runtime 特别适合 State-machine Test？

Agent 输出是概率的。 但 Runtime：

```text
allowed state transitions
```

应该确定。 可以随机生成：

```text
合法/非法 proposal
```

验证：

```text
stale proposal rejected
invalid action rejected
confirmed payment never resubmitted
attempt limit respected
```

### 10.111 [P2] Deterministic Replay 应该怎么测试？

保存：

```text
contract snapshot
candidate set
observations
actions
events
```

重新执行：

```text
deterministic runtime logic
```

期望得到：

```text
same derived state
```

如果不同：

```text
可能存在 hidden dependency
```

例如：

```text
time.Now()
random
live query
```

### 10.112 [P2] Replay Test 为什么能发现 Hidden State？

第一次运行依赖：

```text
current catalog
```

但没有持久化。 Replay 时 Catalog 已变化：

```text
结果不同
```

说明系统实际上依赖：

```text
未记录外部状态
```

Replayability 是检验：

```text
provenance completeness
```

的好方法。

### 10.113 [P1] Production Log 为什么不能成为唯一恢复数据？

Log：

```text
可能 rotation
sampling
retention limited
```

而且通常没有事务保证。 恢复关键状态应该来自：

```text
durable business records
```

例如：

```text
PaymentIntent
InvocationReceipt
Outbox
EpisodeEvent
```

### 10.114 [P1] 为什么 Metric Label 不能无限高基数？

例如 Prometheus label：

```text
user_id
payment_id
trace_id
```

每个值都不同。 会造成：

```text
millions of time series
```

内存和存储压力巨大。 所以 Metrics label 应：

```text
low-cardinality
```

具体 ID：

```text
放 log / trace
```

更合适。

### 10.115 [P1] 什么是 Cardinality Explosion？

例如：

```text
http_request_duration{
    path="/users/123"
}
```

如果把真实 user ID 放 path：

```text
/users/1
/users/2
/users/3
...
```

每个成为独立 series。 应 normalize：

```text
/users/:id
```

### 10.116 [P2] 为什么 Payment Amount 不应该直接作为 Metric Label？

```text
amount=123
amount=124
amount=125
...
```

高基数。 金额分布可以用：

```text
histogram
```

而不是 label。

### 10.117 [P1] Log Level 怎么理解？

典型：

```text
DEBUG
INFO
WARN
ERROR
```

不要：

```text
所有业务拒绝都 ERROR
```

例如：

```text
invalid user input
```

通常是预期行为。 真正 ERROR：

```text
unexpected dependency failure
invariant violation
```

### 10.118 [P2] 什么是 Invariant Violation Alert？

如果系统检测：

```text
same economic identity
→ two confirmed payments
```

这不是普通业务 error。 应该视为：

```text
high-severity invariant breach
```

立即告警。 这类指标甚至：

```text
一次 > 0
```

都可能值得 paging。

### 10.119 [P2] 为什么“一次 invariant violation”比 1% error rate 更严重？

1% 请求失败可能：

```text
可安全重试
```

但一笔：

```text
double charge
```

可能代表：

```text
money safety 已被破坏
```

可靠性目标不能只看：

```text
availability percentage
```

### 10.120 [P2] 生产系统最终应该测什么？

可以把整个测试目标压缩成四层。

**1. Functional Correctness**

```text
正常输入
→ 正常结果
```

**2. Invariant Correctness**

```text
重复
并发
retry
```

之后：

```text
业务约束仍成立
```

**3. Failure Correctness**

```text
crash
timeout
partial failure
restart
```

之后：

```text
能恢复并收敛
```

**4. Operational Correctness**

线上：

```text
坏了能发现
能定位
能缓解
能恢复
```

缺任何一层：

```text
生产可靠性都不完整
```

### 10.121 S4 后尤其值得记住的 Test Matrix

最新 S4 暴露出一套非常漂亮的通用测试矩阵。

**Case A：Happy Path**

```text
request
→ payment
→ delivery
→ validation
→ fulfilled
```

**Case B：Same-key Sequential Replay**

```text
request K
→ response R

request K again
→ response R
```

并且：

```text
side effect count stays 1
```

**Case C：Same-key Concurrent Replay**

```text
Process A ─┐
           ├→ K
Process B ─┘
```

要求：

```text
one allocation
same result
```

**Case D：Metadata Conflict**

```text
K + Agent A + SKU 1
```

已经存在。 然后：

```text
K + Agent B + SKU 1
```

必须：

```text
conflict
```

而不是 replay。

**Case E：Transactional Rollback**

```text
reserve resource
↓
inject error
↓
ROLLBACK
```

验证：

```text
resource reusable
receipt absent
```

**Case F：Restart Replay**

```text
request K
↓
commit result
↓
shutdown
↓
restart
↓
request K
```

要求：

```text
original result replayed
```

**Case G：Guard-before-side-effect**

```text
illegal state
↓
invoke
```

要求：

```text
error
external call count = 0
invocation record = absent
```

**Case H：Retry Scope**

```text
payment confirmed once
↓
delivery invalid
↓
retry delivery
```

最终：

```text
payment attempts = 1
settlements = 1
delivery attempts = 2
```

这比：

```text
最终 State=FULFILLED
```

更能证明系统正确。

### 10.122 为什么 `1 / 1 / 2` 是一个很好的 Acceptance Invariant？

一个典型恢复流程：

```text
1 Payment
1 Recovery Decision
2 Delivery Attempts
```

可以看成：

```text
economic layer
decision layer
delivery layer
```

三个不同 retry domain。 如果 Delivery 第一次失败：

```text
只扩大 delivery retry count
```

不能：

```text
扩大 payment count
```

所以 acceptance test 验证：

```text
PaymentAttemptCount = 1
RetryCount = 1
DeliveryAttemptCount = 2
```

实际上是在验证：

> **下游失败没有穿透并重放已经确认的上游经济副作用。**

这是一个非常通用的后端可靠性原则。

### 10.123 S4 中 `BEGIN IMMEDIATE` 对 Testing 的启发

如果只测试：

```text
同一个 repository object
+
two goroutines
```

本地：

```text
sync.Mutex
```

就可能掩盖 DB race。 更强测试：

```text
Repo Instance A
       ↓
same SQLite file
       ↑
Repo Instance B
```

并发 same-key。 这样才真正验证：

```text
database-level serialization
```

而不是：

```text
process-local synchronization
```

### 10.124 S4 Merchant Restart Replay 为什么比普通幂等单测更有价值？

普通：

```text
Call()
Call()
```

第二次运行仍在：

```text
同一个 process
同一堆内存
```

可能不小心依赖：

```text
mutex
map
cached object
```

Restart test：

```text
first process terminates
```

强制清空：

```text
process-local state
```

只留下：

```text
durable state
```

如果仍能：

```text
replay exact delivery
```

才能证明：

```text
idempotency really survives process lifecycle
```

### 10.125 S4 Black-box Test 最值得学的是什么？

不是：

```text
PowerShell 脚本怎么写
```

而是它测试了真正的：

```text
deployed Merchant contract
```

而不是直接调用 Go service method。 外部观察：

```text
HTTP 402
↓
payment requirement parse
↓
atomic/business amount
↓
paid HTTP 200
↓
durable response
↓
same-key replay
↓
merchant restart
↓
same persisted result
```

这是：

```text
unit correctness
```

向：

```text
system composition correctness
```

迈进的一步。

### 10.126 高频错误设计：所有 Test 都用 Mock

Mock 的接口行为：

```text
由你自己写
```

如果你对真实协议理解错：

```text
Mock 也会跟着错
```

所以还需要：

```text
contract test
integration test
black-box test
```

与真实边界验证。

### 10.127 高频错误设计：只测 Happy Path

如果项目主卖点是：

```text
reliable agent payment
```

却没有：

```text
timeout
duplicate
restart
crash
concurrency
```

测试。 面试官很容易问：

> 你的可靠性是谁证明的？

### 10.128 高频错误设计：测试 Retry，但没检查 Effect Count

测试：

```text
retry returned success
```

不够。 还应检查：

```text
payment provider called how many times？
resource allocated how many times？
ledger settlement how many rows？
```

否则重复 side effect 被隐藏。

### 10.129 高频错误设计：Restart 后重新生成 Response

如果 response 包含：

```text
gift code
proof
artifact ID
```

重启后重新生成：

```text
可能产生新 outcome
```

如果 API contract 要求 result idempotency：

```text
应 replay persisted result
```

### 10.130 高频错误设计：Guard Test 只 assert error

如果实现：

```text
先调用 merchant
再检查状态
最后 return error
```

test 仍可能：

```text
PASS
```

如果只检查：

```text
err != nil
```

所以必须验证：

```text
external call count = 0
```

### 10.131 高频错误设计：Integration Test 只用 In-memory Repository

In-memory 实现可能：

```text
天然串行
没有真实 transaction
没有 connection semantics
```

SQLite / MySQL 真实 repository：

```text
可能出现完全不同 concurrency behavior
```

所以关键 invariant 必须：

```text
在真实 persistence adapter 上再测一次
```

### 10.132 高频错误设计：上线前只跑 Unit Tests

可能遗漏：

```text
Docker wiring
env config
migration
port
service discovery
certificate
real dependency
```

所以至少还要：

```text
smoke test
composition test
```

### 10.133 高频错误设计：告警只看 HTTP 500

Agent Workflow 可能：

```text
HTTP 全部 200
```

但：

```text
大量 Episode 永远卡 UNKNOWN
```

用户仍然失败。 所以业务状态：

```text
stuck episode
unknown age
DLQ
reconciliation failure
```

必须进入 observability。

### 10.134 高频错误设计：Trace 就等于 Audit

Trace：

```text
可能 sampling
可能过期
```

经济事实：

```text
必须 durable
```

所以：

```text
observability data
```

不能替代：

```text
business evidence
```

### 10.135 高频错误设计：Metrics 带 PaymentID Label

会形成：

```text
high-cardinality explosion
```

具体 ID：

```text
Logs / Traces
```

聚合维度：

```text
Metrics
```

### 10.136 高频错误设计：Readiness 依赖所有下游实时健康

某个非关键：

```text
analytics
```

挂掉。 所有 pods：

```text
readiness false
```

LB 把全部 pod 下线。 局部故障变成：

```text
global outage
```

Readiness 必须反映：

```text
是否还能安全服务核心请求
```

### 10.137 高频错误设计：Deployment Rollback 没考虑 Schema

App rollback：

```text
v2 → v1
```

DB 已经：

```text
destructive migration
```

v1 无法运行。 所以：

```text
rollback plan
```

必须包含：

```text
database compatibility
```

### 10.138 高频错误设计：DLQ 有了就算恢复完成

DLQ：

```text
只是隔离失败消息
```

如果没有：

```text
alert
inspection
repair
replay
```

就是：

```text
durable graveyard
```

### 10.139 本章高频对比

| 概念 A               | 概念 B                | 核心区别                           |
| ------------------ | ------------------- | ------------------------------ |
| Logs               | Metrics             | 单事件细节 vs 聚合趋势                  |
| Metrics            | Traces              | 整体趋势 vs 单链路路径                  |
| Trace ID           | Business ID         | 一次执行链 vs 跨 retry 的业务身份         |
| Observability      | Auditability        | 系统运行理解 vs 业务事实证明               |
| Counter            | Gauge               | 单调累计 vs 当前值                    |
| Average            | P99                 | 平均体验 vs 尾部体验                   |
| SLI                | SLO                 | 实际指标 vs 目标                     |
| SLO                | SLA                 | 内部目标 vs 外部承诺                   |
| RED                | USE                 | 请求视角 vs 资源视角                   |
| Unit Test          | Integration Test    | 单组件 vs 多真实组件                   |
| Integration        | E2E                 | 局部真实组合 vs 完整链路                 |
| Contract Test      | Unit Test           | 外部协议 vs 内部逻辑                   |
| Black-box          | White-box           | 外部行为 vs 内部实现                   |
| Happy Path         | Failure Path        | 正常执行 vs 故障窗口                   |
| Sequential Retry   | Concurrent Retry    | 先后重试 vs 真正竞争                   |
| Goroutine Race     | Cross-process Race  | 单进程并发 vs 多进程共享资源               |
| Effect Idempotency | Result Idempotency  | 不重复副作用 vs 返回原结果                |
| Semantic Replay    | Byte Replay         | 业务等价 vs 原始字节相同                 |
| Crash Test         | Restart Replay      | 中途故障 vs 进程生命周期后重放              |
| Race Detector      | Business Race Test  | 内存 data race vs 业务并发 invariant |
| Load Test          | Stress Test         | 预期负载 vs 超容量                    |
| Stress Test        | Soak Test           | 极限容量 vs 长时间稳定性                 |
| Benchmark          | Load Test           | 单组件性能 vs 系统性能                  |
| Readiness          | Liveness            | 能否接流量 vs 进程是否存活                |
| Canary             | Blue-Green          | 小流量渐进 vs 双环境切换                 |
| App Rollback       | DB Rollback         | 程序版本恢复 vs 数据结构恢复               |
| RPO                | RTO                 | 可接受数据丢失量 vs 可接受恢复时间            |
| Mock               | Contract Test       | 模拟依赖 vs 验证真实协议                 |
| Code Coverage      | Correctness         | 执行覆盖率 vs invariant 是否成立        |
| Error Rate         | Invariant Violation | 可用性问题 vs correctness breach    |

### 10.140 面试前一分钟速记

```text
Observability 三件套：

Logs
Metrics
Traces。

Logs：
具体发生了什么。

Metrics：
总体趋势怎么样。

Trace：
一次跨服务请求怎么走。

Structured logging
优于自由文本日志。

Trace ID
≠
Business ID。

请求型服务看 RED：

Rate
Errors
Duration。

资源看 USE：

Utilization
Saturation
Errors。

平均 latency 不够，
看 P95 / P99。

SLI：
测量值。

SLO：
目标。

Error Budget：
允许失败空间。

Agent Commerce 除 HTTP 指标外，
还要监控：

UNKNOWN count
oldest UNKNOWN age
reconciliation
MQ lag
DLQ
delivery validation failure。

Testing 不只：

Unit
Integration
E2E。

还要：

Contract
Black-box
Fault Injection
Crash-window
Restart Replay
Concurrency Test。

幂等不能只测：
same request twice。

要测：

same key concurrently
process restart
same result replay
different request same key conflict。

Guard Test：
不仅 assert error，
还要 assert：

external side effect = 0。

Crash-window Test：
沿着 durable boundary / side-effect boundary
逐点注入 failure。

Race Detector
只能查 data race，
不能证明没有 business race。

Load：
预期容量。

Stress：
超过容量。

Soak：
长时间稳定。

Rolling update 意味着：
old/new version 同时存在。

所以 schema 必须考虑：
mixed-version compatibility。

生产可靠性最终要同时证明：

functional correctness
invariant correctness
failure correctness
operational correctness。
```

### 10.141 StablePay / S4 映射

这章和当前 S4 的最新实现可以形成非常直接的映射。

**Merchant Durable Result**

当前 Merchant 将：

```text
IdempotencyKey
AgentDID
SKUID
ResponseJSON
```

持久化为：

```text
InvocationReceipt
```

这对应：

```text
Durable Idempotency
+
Result Replay
```

而不是只在进程内：

```text
map[key]result
```

**Same-key Concurrent Test**

当前 SQLite 测试用：

```text
两个独立 repository instance
```

打开：

```text
同一个 SQLite DB
```

同时调用：

```text
GetOrCreateDeliveryResult(
    same-key
)
```

最终要求：

```text
两个 caller 得到相同 response
只分配一个 gift code
```

它验证的是：

```text
cross-connection concurrency invariant
```

而不只是 Go mutex。

**SQLite `BEGIN IMMEDIATE`**

当前 delivery transaction：

```text
BEGIN IMMEDIATE

check receipt

select unused gift code

conditional UPDATE gift code

build persisted response

INSERT invocation receipt

COMMIT
```

将：

```text
scarce resource allocation
+
idempotency result
```

放在同一个 local ACID boundary。 这正是：

```text
能用 local transaction 解决的
不要过度设计 distributed transaction
```

的实例。

**Rollback Injection**

当前测试在：

```text
gift code 已选中
```

之后让 builder：

```text
return injected error
```

然后验证：

```text
receipt 不存在
gift code 后续仍可重新分配
```

它真正证明的是：

```text
partial local effect
```

不会逃出 transaction。

**Restart Replay**

当前 Merchant 测试：

```text
第一次执行
↓
close repository
↓
重新打开 SQLite
↓
same key
```

builder：

```text
必须不再运行
```

而是：

```text
直接返回 persisted ResponseJSON
```

这证明：

```text
idempotency survives process restart
```

**Black-box Restart**

最新 S4 black-box 更进一步：

```text
HTTP paid request
↓
保存真实 response
↓
merchant process restart
↓
same HTTP operation
↓
response still equals persisted delivery
```

这验证的不只是：

```text
repository unit test
```

而是：

```text
real server composition
+
SQLite persistence
+
HTTP contract
```

共同成立。

**S4 `1 / 1 / 2`**

当前 canonical acceptance 明确保护：

```text
PaymentAttemptCount = 1
RetryCount = 1
DeliveryAttemptCount = 2
```

同时进一步检查：

```text
payment adapter call = 1
payment settlement ledger entry = 1
```

这其实就是一个非常好的：

```text
cross-layer acceptance invariant
```

说明：

```text
delivery recovery
```

没有反向穿透：

```text
payment layer
```

产生 second payment。

**Guard-before-side-effect**

S4 acceptance 还验证：

```text
在 CLAIMING 状态直接 InvokeDelivery
```

必须：

```text
ErrActionNotAllowed
```

而且：

```text
不存在 delivery invocation fact
```

这体现的不是单纯：

```text
state machine rejects illegal transition
```

而是：

> **非法 transition 在外部副作用发生前就被阻止。**

更理想的 production test 还应该持续验证：

```text
merchant external call count = 0
```

作为完整 guard invariant。

### 10.142 本章学习优先级

### 第一轮：P0

必须立即回答：

```text
Logs / Metrics / Traces
Structured Logging
P95 / P99
SLI / SLO / SLA
Unit / Integration / E2E
Contract Test
Readiness / Liveness
Load Test
```

### 第二轮：P1

重点：

```text
RED / USE
Error Budget
Business Metrics
Trace Propagation
MQ Trace
Black-box Test
Composition Test
Fault Injection
Concurrency Test
Rollback Test
Invariant-based Test
Fuzz
Deterministic Clock
Race Detector limitation
Stress / Soak
Canary
Schema Compatibility
Runbook
```

### 第三轮：P2

针对 Infra / Agent / Payment：

```text
Crash-window Test
Restart Replay
Exact Redelivery
Effect vs Result Idempotency
Cross-process concurrency
State-machine testing
Deterministic replay
Failure Model
Invariant Violation Alert
RPO / RTO
Disaster Recovery Drill
Expand-Contract Migration
```

最终不要把生产工程回答成：

> “我们用了 Prometheus、Grafana 和 Jaeger，并且写了单测和集成测试。”

更完整的理解应该是：

> Observability 的目标是让系统故障能够被发现和解释，因此 logs、metrics、traces 分别承担事件细节、整体趋势和跨服务链路；高价值工作流还必须监控 UNKNOWN、reconciliation age、MQ lag 和 invariant violation 等业务指标。Testing 则不能停留在 happy path：分布式 correctness 要沿 durable commit 与 side-effect boundary 建 crash-window tests，用并发 same-key 验证真正的幂等 race，用 restart replay 证明状态不依赖进程内存，并通过 effect count 验证下游 retry 没有重新执行已经确认的上游副作用。上线以后还必须考虑 mixed-version rollout、schema migration、runbook、SLO 与恢复演练。**一个机制只有在 duplicate、concurrency、crash、restart 和 recovery 下仍满足 invariant，才算真正被验证。**

## 11. StablePay 映射速查

这一章不再解释八股原理。 前面的 Macro 1–10 回答的是：

```text
这个知识点是什么？
为什么需要？
失败会怎样？
有哪些 trade-off？
```

这一章只回答：

> **这个知识点在 StablePay 里落在哪里？面试时怎么迅速把通用原理接回项目？**

目标不是把 01 的源码追问复制一遍，而是建立：

```text
八股概念
   ↓
StablePay 设计
   ↓
项目证据
   ↓
实现边界
```

面试时可以形成：

```text
先讲通用原理
↓
再说 StablePay 怎么落地
↓
最后主动说明当前边界
```

而不是一上来：

```text
“我们项目用了 Redis、RocketMQ、Kitex……”
```

### 11.1 StablePay 一句话是什么？

可以先把项目理解成：

> StablePay 在已有支付微服务基础上增加了一个 Agent Commerce Runtime，让模型参与 merchant/capability 的发现与决策，但把支付金额、收款方、授权、状态迁移和外部副作用控制在确定性 Runtime 中，并通过 durable intent、幂等、reconciliation、版本化 catalog 和可恢复 delivery loop 处理真实 Agent 长流程里的失败。

再压缩：

```text
LLM 决策
+
Deterministic Runtime
+
Payment Correctness
+
Durable Recovery
```

### 11.2 当前整体架构怎么记？

不要背仓库目录。 先背两层。

**原有 Payment Plane**

可以粗略理解：

```text
API Gateway
      ↓
Payment Service
      ↓
Blockchain Adapter

DID Service
Verification Service
Query Service
Merchant Service
```

以及：

```text
Redis
MySQL / SQLite
RocketMQ
```

分别承担认证/短期状态、持久化和异步事件传播。

**Agent Commerce Runtime**

上面再增加：

```text
AcquireCapabilityRequest
        ↓
CommerceEpisode
        ↓
Discovery
        ↓
CandidateSet
        ↓
LLM Proposal
        ↓
Runtime Guard
        ↓
Merchant Invocation
        ↓
Payment Requirement
        ↓
PaymentIntent
        ↓
Settlement / Reconciliation
        ↓
Entitlement
        ↓
Delivery
        ↓
Validation
        ↓
Fulfilled / Recovery
```

核心边界：

```text
LLM
负责 propose

Runtime
负责 authorize / validate / commit / execute
```

### 11.3 S0–S4 怎么理解？

当前可以用一条能力演进线记忆。

**S0：原有支付基础设施**

提供：

```text
API Gateway
DID
Payment Service
Blockchain Adapter
Verification
Query
Merchant
RocketMQ
Redis
```

主要回答：

```text
“一个普通后端支付系统怎么跑起来？”
```

**S1：Agent Commerce Runtime 基础**

重点转向：

```text
CommerceEpisode
DecisionProposal
RuntimeGuard
Action / Observation
event sequence
step / budget / deadline
```

主要回答：

```text
“怎么让 LLM 参与决策，
但不能直接拥有副作用权限？”
```

**S2：Payment Correctness**

引入更明确的：

```text
PaymentIntent
economic identity
UNKNOWN
reconciliation
ledger fact
entitlement
```

主要回答：

```text
“模型选完以后，
真实支付 timeout / retry / crash 怎么办？”
```

**S3：Catalog / Discovery**

增加：

```text
MerchantCapability
CatalogVersion
CatalogSnapshot
CandidateSet
stable ranking
ValidUntil
```

主要回答：

```text
“Agent 到底从哪里找到 merchant，
如何避免模型凭空生成目标？”
```

**S4：真实 Merchant Inner Loop**

进一步形成：

```text
initial merchant invocation
        ↓
402 payment requirement
        ↓
parse / bind
        ↓
one payment
        ↓
entitlement
        ↓
delivery
        ↓
validation
        ↓
same-merchant recovery
```

并增加：

```text
InvocationReceipt
exact result replay
merchant restart recovery
BEGIN IMMEDIATE
atomic/business amount
validation evidence
```

主要回答：

```text
“付完钱以后商户交付失败怎么办，
怎么保证 delivery retry 不会重新付款？”
```

### 11.4 一条最值得背的 S0–S4 主线

```text
User Contract
      ↓
CommerceEpisode
      ↓
Discovery
      ↓
CandidateSet
      ↓
LLM Proposal
      ↓
Runtime Guard
      ↓
Merchant Initial Invocation
      ↓
Payment Requirement
      ↓
Quote / Binding
      ↓
PaymentIntent
      ↓
Submit
      ↓
CONFIRMED / UNKNOWN
      ↓
Reconcile
      ↓
Entitlement
      ↓
Merchant Delivery
      ↓
Validation
      ↓
FULFILLED
```

失败：

```text
Delivery Invalid
      ↓
RECOVERING
      ↓
Retry Same Merchant
      ↓
Delivery Attempt 2
```

但：

```text
Payment Attempt
仍然只有 1
```

这就是当前 S4 最重要的 correctness 线。

### 11.5 Macro 1：Agent Runtime 对应 StablePay 什么？

| 通用八股                           | StablePay 落点                                                 |
| ------------------------------ | ------------------------------------------------------------ |
| Agent vs Workflow              | CommerceEpisode 是受约束 workflow，LLM 只决定有限动作                    |
| Model / Harness 分层             | LLMPolicy / proposal 与 RuntimeGuard 分离                       |
| Proposal ≠ Authorization       | DecisionProposal 必须通过 RuntimeGuard                           |
| Probabilistic vs Deterministic | LLM 选候选；金额、payee、版本、状态由 Runtime 验证                           |
| State Machine                  | Episode 显式状态迁移                                               |
| Observation Provenance         | Observation / FactsRef / PayloadHash                         |
| Stale Proposal                 | BasedOnEventSequence                                         |
| Deadline                       | proposal CreatedAt / ExpiresAt、Episode deadline              |
| Bounded Agent                  | step / action / retry / budget 等边界                           |
| Capability                     | Agent 只能在已暴露的能力和状态动作集合内操作                                    |
| Confused Deputy                | Runtime 不允许模型自由指定收款目标                                        |
| Factual Authority              | Catalog / Merchant response / settlement / validation 各自提供事实 |

一句话：

> StablePay 没把 LLM 当 transaction coordinator，而是把它放在 proposal layer。

### 11.6 StablePay 中模型到底能决定什么？

模型可以：

```text
从 CandidateSet 里选候选

在允许状态中建议：
select
retry
stop
```

模型不应该直接决定：

```text
真实 payee address
真实 settlement amount
payment 是否成功
entitlement 是否有效
delivery 是否合格
```

后者来自：

```text
Catalog Fact
Merchant Protocol Fact
Payment Fact
Entitlement Fact
Validation Evidence
```

所以：

```text
LLM Decision Authority
≠
Factual Authority
```

### 11.7 Macro 2：Go 并发对应 StablePay 什么？

项目不是以：

```text
复杂 goroutine framework
```

作为卖点。 但可以映射：

```text
Context
→ HTTP/RPC deadline/cancellation

Mutex
→ 进程内 repository critical section

Database transaction
→ 跨 connection/process 的最终数据 invariant

Background worker
→ reconciliation / event processing 类生命周期问题
```

特别值得强调：

```text
sync.Mutex
只能保护一个 process
```

S4 Merchant 的 same-key 并发最终不能只靠：

```text
r.mu.Lock()
```

因为多个 repository/process：

```text
各有自己的 mutex
```

最终还要靠：

```text
SQLite transaction
```

保护。

### 11.8 StablePay 中最好的“Mutex 不等于 Distributed Lock”例子

S4 Merchant：

```text
Repo A
  ↓
SQLite file
  ↑
Repo B
```

两个 repo instance 同时：

```text
GetOrCreateDeliveryResult(same-key)
```

如果只靠：

```text
Repo A.mu
Repo B.mu
```

双方互不知情。 所以：

```text
BEGIN IMMEDIATE
```

提前取得数据库 writer serialization。 这个例子比单纯背：

> “Mutex 只能单机。”

更适合面试。

### 11.9 Macro 3：HTTP / RPC 对应 StablePay 什么？

**Hertz**

可以映射：

```text
API Gateway / HTTP service
```

**Kitex**

内部：

```text
service-to-service RPC
```

客户端包含：

```text
RPC timeout
retry policy
```

**Merchant Invocation**

S4 又引入一条：

```text
Runtime
→ Merchant HTTP
```

需要处理：

```text
HTTP status
headers
body
content type
payload hash
request hash
deadline
```

### 11.10 StablePay 中 Retry 为什么不能统一处理？

最典型：

**Read RPC**

```text
temporary failure
→ retry
```

通常较安全。

**Payment Mutation**

```text
timeout
```

不能直接：

```text
new payment
```

**Merchant Delivery**

如果 payment 已 confirmed：

```text
delivery invalid
→ retry delivery
```

不能：

```text
retry entire workflow
```

所以 StablePay 很适合回答：

```text
HTTP retry
RPC retry
MQ retry
business retry
delivery retry
```

不是一回事。

### 11.11 Macro 4：数据库事务对应 StablePay 什么？

最重要几个点：

```text
PaymentIntent
→ durable command

Episode version
→ optimistic concurrency

Event / action identity
→ UNIQUE / idempotency boundary

InvocationReceipt
→ durable result identity

GiftCode + Receipt
→ same local transaction
```

### 11.12 StablePay 中最好的 Local Transaction 例子

S4 Merchant 的：

```text
GetOrCreateDeliveryResult()
```

逻辑：

```text
BEGIN IMMEDIATE

if receipt exists:
    replay it

else:
    select unused gift code
    allocate gift code
    build delivery response
    insert invocation receipt

COMMIT
```

这里保护：

```text
资源分配
+
幂等结果
```

两个事实。 如果分两次提交：

```text
allocate
↓
CRASH
↓
save receipt
```

就产生 local dual-write crash window。 所以这里最正确的工具：

```text
local ACID transaction
```

而不是 Saga。

### 11.13 为什么这个例子对数据库八股很有价值？

因为可以回答：

> 什么时候应该上分布式事务？

先说：

```text
只要 invariant 还能压进
同一个数据库事务
```

就优先：

```text
local ACID
```

StablePay S4 就是：

```text
gift code allocation
+
delivery receipt
```

在同一 SQLite DB。 没必要：

```text
MQ
Saga
distributed lock
```

复杂化。

### 11.14 Macro 5：Redis 对应 StablePay 什么？

当前最明显：

```text
nonce store
rate limiter
```

以及：

```text
GETDEL
```

一次性状态消费。

**Redis Nonce**

对应：

```text
anti-replay
```

不是：

```text
business idempotency
```

**Redis Limiter**

对应：

```text
abuse / capacity control
```

**Memory Fallback**

对应：

```text
availability
vs
distributed semantics
```

单实例 memory：

```text
可以正常工作
```

多实例：

```text
没有共享全局状态
```

所以：

```text
local fallback
≠
distributed invariant
```

### 11.15 StablePay 中 Redis 最容易被追问什么？

不要说：

> Redis 挂了自动内存降级，所以高可用。

应该继续说明：

```text
rate limiter fallback
```

和：

```text
security nonce invariant
```

不是同一风险级别。 以及：

```text
Redis runtime error
```

是否：

```text
fail-open
or
fail-closed
```

应该按业务语义设计。

### 11.16 Macro 6：RocketMQ 对应 StablePay 什么？

当前最明显：

```text
Payment Event
      ↓
RocketMQ
      ↓
Verification Consumer
```

Consumer：

```text
decode
validate
persist
```

失败：

```text
ConsumeRetryLater
```

成功：

```text
ConsumeSuccess
```

### 11.17 StablePay 怎么回答 At-least-once？

可以说：

> RocketMQ 消费按 at-least-once 思维设计，消费成功后确认；如果 DB 已经提交但成功确认前进程 crash，消息可能再次投递，因此 Verification Consumer 不能依赖 callback 只执行一次，而要通过 EventID 和数据库 invariant 处理重复。

然后主动补：

```text
check-then-insert
本身不足以抗并发
```

最终还需要数据库：

```text
UNIQUE
```

作为最后边界。

### 11.18 RocketMQ 和 S4 Result Replay 是不是一回事？

不是。 RocketMQ：

```text
message redelivery
```

目标：

```text
consumer business effect idempotent
```

S4 Merchant：

```text
HTTP request redelivery
```

进一步要求：

```text
exact durable result replay
```

两者共同属于：

```text
duplicate-safe execution
```

但边界不同。

### 11.19 Macro 7：分布式可靠性对应 StablePay 什么？

这是最强映射的一章。

| 通用概念                | StablePay                                    |
| ------------------- | -------------------------------------------- |
| Idempotency Key     | action/payment/invocation operation identity |
| Economic Identity   | 同一笔经济购买                                      |
| Timeout ≠ Failed    | payment submit/poll                          |
| UNKNOWN             | remote effect 结果不确定                          |
| Reconciliation      | payment outcome recovery                     |
| Durable Intent      | PaymentIntent                                |
| At-least-once       | RocketMQ                                     |
| Effectively-once    | EventID + DB invariant                       |
| TOCTOU              | stale proposal / candidate snapshot          |
| Saga                | acquire capability 长流程                       |
| Compensation        | refund/release 等未来路径                         |
| Source of Truth     | settlement / ledger / catalog facts          |
| Side-effect-safe SM | submit/reconcile/delivery guard              |
| Result Idempotency  | Merchant InvocationReceipt                   |
| Restart Replay      | persisted merchant response                  |
| Retry Scope         | payment 与 delivery 分离                        |

### 11.20 StablePay 最重要的 Failure Timeline

面试时可以画：

```text
Create Episode
      ↓
Discover
      ↓
Select
      ↓
Invoke Merchant
      ↓
Receive Payment Requirement
      ↓
Persist PaymentIntent
      ↓
Submit Payment
      ↓
remote may succeed
      X
response uncertain
      ↓
UNKNOWN
      ↓
Reconcile
      ↓
CONFIRMED
      ↓
Entitlement
      ↓
Delivery
      ↓
Validate
```

如果 delivery invalid：

```text
RECOVERING
↓
retry delivery
```

不返回：

```text
submit payment
```

这就是：

```text
side-effect-safe recovery
```

### 11.21 `1 / 1 / 2` 到底该怎么解释？

S4 canonical acceptance：

```text
PaymentAttemptCount = 1
RetryCount = 1
DeliveryAttemptCount = 2
```

另外：

```text
payment adapter calls = 1
payment settlement ledger entries = 1
```

对应：

```text
一次支付
一次 recovery decision
两次 delivery attempt
```

它证明：

> **delivery 层失败没有扩散成第二次 economic effect。**

这不是一个普通统计数字。 它是：

```text
retry-domain invariant
```

### 11.22 为什么 `1 / 1 / 2` 比最终 `FULFILLED` 更有说服力？

因为错误实现也可能最终：

```text
FULFILLED
```

但路径是：

```text
Payment 1
Delivery failed
Payment 2
Delivery succeeds
```

用户确实得到结果。 但被扣了两次钱。 所以只检查：

```text
final state
```

不足。 还必须检查：

```text
effect count
```

### 11.23 Macro 8：Security 对应 StablePay 什么？

**DID**

对应：

```text
principal identity
```

**Public Key**

用于：

```text
request signature verification
```

**Canonical Request**

绑定：

```text
method
path
query
body hash
```

等安全语义。

**Timestamp**

限制：

```text
request freshness
```

**Nonce**

防：

```text
signed request replay
```

**Policy / Runtime Guard**

决定：

```text
认证身份是否允许做这个 action
```

### 11.24 StablePay 怎么解释 Replay 和 Idempotency？

非常适合直接画：

```text
Transport Request Retry

nonce:
N1 → N2

business idempotency key:
K → K
```

即：

```text
新的合法认证请求
```

仍可以代表：

```text
同一个逻辑业务 command
```

所以：

```text
Nonce
≠
Idempotency Key
```

### 11.25 StablePay 里最好的 Confused Deputy 例子

如果模型说：

```text
pay arbitrary address X
```

Payment Runtime 有真实转账能力。 如果 Runtime：

```text
只验证 Agent 已认证
```

然后照做：

```text
Runtime
```

就可能成为 Confused Deputy。 因此真正参数要来自：

```text
selected Candidate
+
Catalog Snapshot
+
Merchant Payment Requirement
+
binding rules
```

而不是：

```text
LLM free-form address
```

### 11.26 StablePay 里的金额为什么很值得讲？

S4 将金额显式拆成：

```text
AtomicAmount
AtomicDecimals
BusinessAmountMinor
Currency
```

例如：

```text
2.00 USDC

atomic:
2,000,000
6 decimals

business ledger:
200
2 decimals
```

核心原则：

```text
exact conversion
```

而不是：

```text
float
round
```

### 11.27 什么情况下 StablePay 会拒绝金额？

如果 atomic amount：

```text
不能精确映射到内部业务账本单位
```

应该：

```text
reject
```

而不是：

```text
round silently
```

这体现：

```text
wire protocol fact
→ exact accounting fact
```

的安全边界。

### 11.28 Macro 9：Catalog / Retrieval 对应 StablePay 什么？

S3：

```text
MerchantCapability
CatalogVersion
CatalogSnapshotHash
CandidateSet
```

S4：

```text
PaymentRequirementFact
```

继续补充真实 merchant observation。

### 11.29 StablePay 的 Discovery Plane 和 Execution Plane

**Discovery**

允许：

```text
structured retrieval
ranking
candidate selection
```

**Execution**

要求：

```text
exact MerchantDID
exact CapabilityID
exact CatalogVersion
exact SnapshotHash
```

然后继续：

```text
Payment Requirement binding
```

所以可以总结：

```text
Approximate Discovery
+
Deterministic Execution
```

### 11.30 CandidateSet 为什么是项目里很关键的对象？

不是单纯：

```text
搜索返回 JSON
```

而是：

```text
一次 discovery 决策上下文
```

模型：

```text
只能从 CandidateSet 中选择
```

Runtime：

```text
commit 时检查同一个 CandidateSet
```

避免：

```text
模型在世界 A 做决策
Runtime 在世界 B 执行
```

### 11.31 Catalog Snapshot 为什么不能只存 ID？

如果只记录：

```text
merchant=M1
```

以后：

```text
payee
endpoint
protocol
```

都可能变化。 所以至少要绑定：

```text
MerchantDID
CapabilityID
CatalogVersion
CatalogSnapshotHash
```

这样历史 decision 才能重放与审计。

### 11.32 S4 之后 Factual Authority 怎么分层？

目前最值得背：

```text
User Contract
→ 用户目标/约束

Catalog Snapshot
→ merchant/capability 登记事实

Merchant Response
→ 本次 invocation 实际 observation

Payment Requirement
→ 本次 merchant 声明的支付条件

Payment / Chain
→ settlement fact

Entitlement
→ 使用权事实

DeliveryArtifact
→ merchant 实际交付内容

ValidationEvidence
→ delivery 是否满足合同

LLM Proposal
→ 下一步建议
```

所以：

```text
LLM
```

始终位于：

```text
decision layer
```

不是：

```text
fact layer
```

### 11.33 Macro 10：Testing 对应 StablePay 什么？

当前 S4 尤其适合回答 production correctness。

**Happy Path**

```text
initial
→ payment
→ delivery
→ validation
```

**Replay**

```text
same request
→ same persisted result
```

**Concurrency**

两个 repo：

```text
same SQLite
same idempotency key
```

最终：

```text
one gift code
```

**Rollback**

```text
allocation
→ injected error
```

最终：

```text
resource reusable
receipt absent
```

**Restart**

```text
commit
→ close
→ reopen
→ same key
```

最终：

```text
original response
```

**Guard**

```text
illegal state
→ delivery rejected
```

且：

```text
no invocation fact
```

**Retry Scope**

```text
Payment = 1
Delivery = 2
```

### 11.34 StablePay 中最好用的 Testing 故事是什么？

不要只说：

> 我写了很多单测，39/xx tests passed。

更好的回答：

> 我针对业务 invariant 建 acceptance test。比如 S4 故意让第一次 delivery 返回空 payload，系统进入 recovery 后只允许重试 delivery；最终断言 payment adapter 只调用一次、settlement ledger 只有一条，但 delivery 一共执行两次。这样测试的不是“最终能成功”，而是“下游失败不能重新触发已经确认的经济副作用”。

这属于：

```text
Invariant-based Testing
```

### 11.35 StablePay 中最好用的 Restart Recovery 故事是什么？

> Merchant 的幂等不是内存 map。第一次请求分配 gift code 后，response 和 allocation 在同一个 SQLite transaction 中持久化；关闭 repository 甚至重启 merchant 后，相同 idempotency key 会读取原 invocation receipt 并返回原结果，而不是重新分配资源。

对应：

```text
durable result idempotency
```

### 11.36 StablePay 中最好用的 Crash-window 故事是什么？

假设：

```text
allocate gift code
↓
save receipt
```

分开提交。 Crash 在中间：

```text
资源已经被消费
```

但系统没有：

```text
receipt
```

Retry：

```text
再次分配
```

因此 S4：

```text
BEGIN IMMEDIATE
...
allocate
...
insert receipt
COMMIT
```

把两个事实放进：

```text
same local transaction
```

### 11.37 StablePay 中最好用的 Guard-before-side-effect 故事是什么？

Episode 仍在：

```text
CLAIMING
```

还没完成 entitlement。 如果直接请求：

```text
InvokeDelivery
```

Runtime 返回：

```text
ErrActionNotAllowed
```

而且：

```text
没有生成 invocation fact
```

它说明：

```text
guard
```

在：

```text
merchant side-effect path
```

之前执行。

### 11.38 技术栈速查

| 技术 / 机制                        | StablePay 用途                               |
| ------------------------------ | ------------------------------------------ |
| Go                             | 主要服务实现                                     |
| Hertz                          | HTTP 服务/Gateway                            |
| Kitex                          | 内部 RPC                                     |
| MySQL                          | 主要 durable service state                   |
| SQLite                         | Merchant 当前 durable demo/state             |
| Redis                          | nonce / limiter / temporary control state  |
| RocketMQ                       | payment/event asynchronous propagation     |
| HTTP Merchant Contract         | S4 merchant invocation                     |
| x402-style Payment Requirement | merchant payment challenge parsing/binding |
| DID                            | Agent/merchant identity                    |
| Digital Signature              | authenticated request                      |
| SHA-256                        | request/payload/snapshot binding           |
| State Machine                  | CommerceEpisode                            |
| OCC / Version                  | stale update / proposal protection         |
| Idempotency                    | action/payment/invocation duplicate safety |
| Reconciliation                 | UNKNOWN payment recovery                   |
| Ledger                         | economic facts                             |
| CandidateSet                   | frozen discovery context                   |
| InvocationReceipt              | durable merchant result replay             |
| Validator Registry             | allowlisted delivery validation            |

### 11.39 面试题 → 项目落点速查

**“你项目里 Agent 和 Workflow 有什么区别？”**

```text
LLM produces proposal
Runtime state machine owns execution
```

**“怎么防止 Agent 越权？”**

```text
CandidateSet
RuntimeGuard
capability/budget
payee binding
state guard
```

**“模型 hallucinate 收款地址怎么办？”**

```text
LLM doesn't own payee factual authority
```

payee 来自：

```text
trusted catalog
+
merchant payment requirement
+
runtime binding
```

**“为什么需要状态机？”**

```text
限制每个阶段允许的 action
```

特别是：

```text
paid 后 delivery retry
不能重新 payment
```

**“为什么支付 timeout 不能直接失败？”**

```text
remote may already commit
```

所以：

```text
UNKNOWN
→ reconcile
```

**“怎么实现幂等？”**

先分边界：

```text
API command
MQ event
merchant delivery
payment economic effect
```

不同身份分别处理。

**“Redis lock 能解决重复支付吗？”**

```text
不能作为唯一 correctness mechanism
```

真正依赖：

```text
economic identity
durable intent
provider/remote idempotency
reconciliation
```

**“RocketMQ 为什么会重复消费？”**

```text
DB commit
↓
crash before consume success
↓
redelivery
```

所以 consumer 必须幂等。

**“怎么解决 DB + MQ dual-write？”**

通用答案：

```text
Outbox
or
RocketMQ Transaction Message
```

StablePay 当前不要夸大成：

```text
所有链路已经完整 Outbox 化
```

**“为什么需要 Catalog Version？”**

```text
历史 Agent decision
必须知道当时看到哪个 merchant fact
```

**“Vector Search 结果能直接执行吗？”**

```text
不能
```

应该：

```text
retrieval candidate
↓
authoritative snapshot
↓
runtime guard
```

**“你做过什么并发问题？”**

S4：

```text
two repository instances
same SQLite file
same idempotency key
```

通过：

```text
BEGIN IMMEDIATE
+
transaction
```

保证一份资源只分配一次。

**“你项目里最有价值的测试是什么？”**

优先说：

```text
1 / 1 / 2 retry-domain invariant
```

其次：

```text
restart exact replay
```

再其次：

```text
rollback leaves resource reusable
```

### 11.40 项目中几个最重要的 ID 不要混

```text
RequestID
→ 一次 transport request

TraceID
→ 一次执行 trace

EpisodeID
→ 一次 Agent Commerce workflow

ProposalID
→ 一次模型决策提案

CandidateSetID
→ 一次 discovery result

InvocationID
→ 一次 merchant invocation

IdempotencyKey
→ 一个逻辑 operation

PaymentIntentID
→ 一笔逻辑支付

TxID / TxHash
→ 一次外部 settlement execution

EventID
→ 一条消息事件

DeliveryID
→ 一次 delivery artifact

ValidationID
→ 一次 validation evidence
```

### 11.41 最容易在面试中混掉的四层 Identity

一定要区分：

```text
Transport Identity
RequestID / TraceID
```

```text
Workflow Identity
EpisodeID
```

```text
Operation Identity
IdempotencyKey / InvocationID
```

```text
Economic Identity
PaymentIntent / logical purchase
```

如果把：

```text
RequestID
```

当 payment identity： Retry 就会创造新支付。

### 11.42 StablePay 当前最核心的 Invariants

**Agent Authority**

```text
模型只能 propose
Runtime 才能 commit side effect
```

**Catalog Binding**

```text
执行目标必须来自已 materialize 的可信 candidate
```

**Stale Protection**

```text
proposal 必须基于当前 event sequence / valid snapshot
```

**Payment**

```text
同一 economic purchase
不能因为 transport retry 产生第二次 confirmed effect
```

**Recovery**

```text
UNKNOWN
必须 reconcile
而不是 blind retry
```

**Delivery**

```text
payment confirmed
才允许 delivery
```

**Delivery Retry**

```text
delivery failure
不能创建 second payment
```

**Merchant Idempotency**

```text
same logical delivery operation
→ same durable outcome
```

**Concurrent Allocation**

```text
same key
→ at most one scarce resource allocation
```

### 11.43 哪些内容现在可以大胆说“已经做了”？

截至当前 S4，可以较稳地说：

```text
bounded CommerceEpisode state machine
```

```text
LLM proposal / runtime authority separation
```

```text
stale proposal/version guard
```

```text
versioned merchant catalog
```

```text
materialized CandidateSet
```

```text
deterministic candidate binding
```

```text
durable PaymentIntent-style flow
```

```text
UNKNOWN / reconciliation semantics
```

```text
payment settlement fact / entitlement flow
```

```text
merchant initial 402 → payment → delivery loop
```

```text
delivery validation and same-merchant recovery
```

```text
atomic/business amount exact conversion
```

```text
merchant durable invocation receipt
```

```text
SQLite concurrent same-key protection
```

```text
restart result replay
```

```text
S4 acceptance invariant:
one payment + two delivery attempts
```

### 11.44 哪些内容不要为了面试夸大？

不要直接声称：

```text
生产级全球分布式支付系统
```

不要直接声称：

```text
严格 end-to-end exactly-once
```

更准确：

```text
at-least-once paths
+
idempotency
+
reconciliation
+
local invariants
```

不要说：

```text
Redlock 保证支付 exactly-once
```

当前也不是项目核心。 不要说：

```text
完整双重记账系统
```

除非后续真正实现。 不要说：

```text
完整 Saga compensation 已生产化
```

如果还只是架构方向。 不要说：

```text
所有 DB→MQ 路径都用了 Transactional Outbox
```

除非后续 S5/S6 确认补齐。 不要说：

```text
Merchant restart replay
等于跨商户灾备恢复
```

当前解决的是：

```text
same merchant durable operation replay
```

S5 的：

```text
cross-merchant recovery
```

是更大的问题。

### 11.45 目前 S4 和未来 S5 的关键边界

S4 已经解决：

```text
selected merchant
↓
payment
↓
merchant delivery failure
↓
retry same merchant
```

核心 invariant：

```text
no second payment
```

但更复杂的：

```text
Merchant A
已经收款

Merchant A
无法交付

是否切 Merchant B？
```

就不只是：

```text
retry
```

而涉及：

```text
cross-merchant recovery
refund / compensation
new quote
new authorization
new payment?
economic attribution
```

这是明显的新 correctness domain。 所以：

```text
same-merchant recovery
```

和：

```text
cross-merchant recovery
```

必须分开。

### 11.46 为什么 S5 不应该简单写成“换一家再试”？

因为 Merchant A 可能已经：

```text
收到钱
```

这时：

```text
switch to Merchant B
```

如果直接再支付：

```text
一份需求
→ 两笔钱
```

因此必须先回答：

```text
A 是否需要退款？
退款是否确认？
用户授权是否允许二次购买？
新 merchant 价格是否变化？
原 CandidateSet 是否仍有效？
是否需要重新 discovery？
```

这也是为什么：

```text
cross-merchant recovery
```

比：

```text
delivery retry
```

难一个层级。

### 11.47 一张 S0–S4 Correctness 图

```text
          ┌───────────────┐
          │ User Contract │
          └───────┬───────┘
                  ↓
          ┌───────────────┐
          │CommerceEpisode│
          └───────┬───────┘
                  ↓
       ┌───────────────────────┐
       │ Catalog / CandidateSet│
       └───────────┬───────────┘
                   ↓
            ┌────────────┐
            │LLM Proposal│
            └─────┬──────┘
                  ↓
            ┌────────────┐
            │RuntimeGuard│
            └─────┬──────┘
                  ↓
       ┌─────────────────────┐
       │ Merchant Invocation │
       └─────────┬───────────┘
                 ↓
       ┌─────────────────────┐
       │ Payment Requirement │
       └─────────┬───────────┘
                 ↓
          binding / policy
                 ↓
       ┌─────────────────────┐
       │    PaymentIntent    │
       └─────────┬───────────┘
                 ↓
      CONFIRMED / UNKNOWN
                 ↓
            reconcile
                 ↓
       ┌─────────────────────┐
       │    Entitlement      │
       └─────────┬───────────┘
                 ↓
       ┌─────────────────────┐
       │ Merchant Delivery   │
       └─────────┬───────────┘
                 ↓
       ┌─────────────────────┐
       │ ValidationEvidence  │
       └─────┬─────────┬─────┘
             │valid    │invalid
             ↓         ↓
         FULFILLED  RECOVERING
                        ↓
                 retry delivery
```

每个箭头都要问：

```text
谁拥有 authority？
状态是否 durable？
重复怎么办？
timeout 怎么办？
crash 在这里怎么办？
```

### 11.48 一张 Data Authority 图

```text
User
 │
 │ Contract authority
 ↓
AcquireCapabilityRequest
 │
 │
Catalog ───────────────→ Capability facts
 │
 ↓
CandidateSet
 │
 │ Decision context
 ↓
LLM Proposal
 │
 │ proposal only
 ↓
Runtime
 │
 ├── Merchant ────────→ Payment requirement fact
 │
 ├── Payment System ──→ Settlement fact
 │
 ├── Entitlement ─────→ Authorization/use fact
 │
 ├── Merchant ────────→ Delivery artifact
 │
 └── Validator ───────→ Validation evidence
```

其中：

```text
LLM
```

没有箭头指向：

```text
authoritative fact creation
```

### 11.49 一张 Retry Domain 图

```text
Discovery Retry
      │
      └→ 不应该自动 Payment

Payment Retry
      │
      └→ 只在 definitive failure / safe identity 下

Payment Reconciliation
      │
      └→ 不创建新 economic effect

Delivery Retry
      │
      └→ 不重新 Payment

Validation Retry
      │
      └→ 不重新 Delivery，除非状态机明确要求

MQ Retry
      │
      └→ Consumer 幂等

HTTP Redelivery
      │
      └→ Merchant result replay
```

这张图基本可以回答：

> “你们系统怎么处理 retry？”

### 11.50 一张 Idempotency Scope 图

```text
Request Idempotency
→ same logical API command

Payment Idempotency
→ same economic purchase

Event Idempotency
→ same MQ event

Invocation Idempotency
→ same merchant operation

Result Idempotency
→ same materialized response

Resource Allocation Idempotency
→ same scarce resource not allocated twice
```

所以面试时不要只说：

> “我们有 idempotency key。”

应该继续说：

> **先确定 idempotency 的作用域。**

### 11.51 一张 Storage Boundary 图

```text
MySQL
→ durable service state
→ transaction / unique / OCC

SQLite
→ merchant durable demo state
→ invocation receipt
→ resource allocation transaction

Redis
→ short-lived control state
→ nonce
→ rate limit

RocketMQ
→ asynchronous event handoff
→ retry / redelivery
```

不要把：

```text
Redis
```

说成 payment source of truth。 也不要把：

```text
RocketMQ
```

说成永久 ledger。

### 11.52 一张 Testing Boundary 图

```text
Unit
→ parser / guard / validator

Repository Integration
→ transaction / concurrency

Service Acceptance
→ state machine invariant

Black-box HTTP
→ deployed contract

Restart Test
→ durable recovery

Fault Injection
→ crash window

MQ Integration
→ redelivery / consumer idempotency
```

这比：

```text
“我们测试覆盖率很高”
```

信息量大得多。

### 11.53 如果面试官让你挑一个最能体现 Agent Engineering 的设计

优先：

```text
Proposal
vs
Authority
```

展开：

```text
LLM only proposes
↓
Runtime checks:
state
version
candidate set
budget
identity
deadline
↓
only then side effect
```

原因：

```text
体现 Agent Runtime
而不只是普通 CRUD 后端
```

### 11.54 如果面试官让你挑一个最能体现后端可靠性的设计

优先：

```text
UNKNOWN
+
Reconciliation
```

展开：

```text
timeout ≠ failure
```

以及：

```text
stable identity
→ reconcile remote fact
→ converge local state
```

这是分布式后端最有深度的一块。

### 11.55 如果面试官让你挑一个最能体现数据库能力的设计

优先：

```text
S4 Merchant
BEGIN IMMEDIATE
+
gift-code allocation
+
InvocationReceipt
```

因为它能同时讲：

```text
transaction
race
local dual-write
cross-process serialization
idempotency
rollback
```

### 11.56 如果面试官让你挑一个最能体现 MQ 的设计

讲：

```text
RocketMQ at-least-once
+
EventID
+
consumer idempotency
```

再扩：

```text
DB commit → ACK crash window
```

### 11.57 如果面试官让你挑一个最能体现测试能力的设计

讲：

```text
S4 canonical acceptance
```

因为：

```text
payment adapter call = 1

settlement entries = 1

delivery attempts = 2
```

比：

```text
assert final state == FULFILLED
```

强得多。

### 11.58 如果面试官让你挑一个最能体现安全性的设计

讲：

```text
LLM cannot choose arbitrary payment facts
```

链路：

```text
CandidateSet
→ trusted catalog
→ merchant requirement
→ deterministic binding
→ policy
→ payment
```

这同时体现：

```text
least authority
confused deputy prevention
factual authority
guard-before-side-effect
```

### 11.59 一分钟 StablePay 技术版总结

```text
StablePay 的核心不是让 LLM 直接调用支付 API，而是把 LLM 限制在 proposal layer。Runtime 用显式 CommerceEpisode 状态机维护 durable workflow，Discovery 会把 versioned merchant catalog materialize 成 CandidateSet，模型只能从候选集中选目标；commit 时再验证 event sequence、catalog snapshot、budget 和身份绑定。

支付侧把逻辑 PaymentIntent 和 transport request 分开，对 remote timeout 不直接标失败，而保留 UNKNOWN 并通过 reconciliation 获取 authoritative settlement fact。RocketMQ 按 at-least-once 思维设计，因此 consumer 通过稳定 EventID 和数据库 invariant 做幂等。

S4 又把流程扩展到真实 merchant inner loop：先调用 merchant 获取机器可读 payment requirement，精确解析 atomic amount 并绑定 catalog/payee/budget；支付 confirmed 后才允许 delivery。第一次 delivery 无效时只重试 delivery，不重新支付。Acceptance test 明确验证一笔 payment、一次 recovery decision、两次 delivery attempts。

Merchant 自身还把 scarce-resource allocation 和 InvocationReceipt 放入同一个 SQLite BEGIN IMMEDIATE transaction，使并发 same-key 请求只分配一个资源，并且重启以后仍返回原始持久化结果。
```

### 11.60 本章最终速记

```text
StablePay 不要背成：

LLM
+
微服务
+
支付。

应该背成：

Probabilistic Decision
+
Deterministic Authority
+
Durable State
+
Side-effect Safety
+
Recovery。

S1：
Agent Runtime。

S2：
Payment correctness。

S3：
Catalog / Discovery。

S4：
Merchant inner loop + delivery recovery。

最重要的模型边界：

Proposal
≠
Authorization

LLM
≠
Factual Authority。

最重要的支付边界：

Timeout
≠
Failure

UNKNOWN
→ Reconcile。

最重要的检索边界：

Retrieval
≠
Execution Authority。

最重要的幂等边界：

Duplicate execution
可以发生，

Duplicate business effect
不可以。

最重要的 S4 invariant：

Payment = 1
Recovery = 1
Delivery = 2。

最重要的数据库例子：

BEGIN IMMEDIATE
+
resource allocation
+
InvocationReceipt
+
one transaction。

最重要的测试例子：

Concurrent same-key
Restart replay
Rollback injection
Guard-before-side-effect
Effect-count acceptance。

最重要的未来边界：

Same-merchant recovery
已经进入 S4，

Cross-merchant recovery
属于下一层新的经济正确性问题。
```
