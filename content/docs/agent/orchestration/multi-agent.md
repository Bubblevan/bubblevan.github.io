---
title: "Multi-Agent Roles：Planner、Generator 与 Evaluator"
weight: 1
---

## 1. 多 Agent 的意义不是多开几个 Claude


**Planner、Generator、Evaluator 为什么不是三个聊天窗口？**

下一节要引入：

```text
role-specialized agents
```

并且把：

```text
Anthropic 的上层实验 Harness
```

和：

```text
Claude Code 的 AgentTool runtime primitive
```

明确分开。

### 1.1 Planner、Generator、Evaluator 为什么不是三个聊天窗口？


Macro 5 最后，我们已经自然得到三个角色：

```text
Planner
Generator
Evaluator
```

于是很容易把 Anthropic 这套 Harness 总结成：

> 单 Agent 不够强，所以多开几个 Agent 分工。

但这个总结其实把最关键的东西漏掉了。

如果我只是开三个 Claude Code 窗口：

```text
窗口 A：你想想怎么做
窗口 B：你也想想怎么做
窗口 C：你再检查一下
```

然后三个人：

* 读同样的输入；
* 拿同样的工具；
* 追求差不多的目标；
* 最后各自产出一段自然语言；

那它更接近：

```text
multi-sampling
```

而不是 Anthropic 那篇文章里真正值得学的 Multi-Agent Harness。

Anthropic 的 Planner、Generator、Evaluator 之所以有意义，不是因为它们有三个独立的聊天窗口，而是因为三个 Agent 被刻意放在了**不同的职责位置**：Planner 负责把短 prompt 扩展成产品级约束，Generator 负责真正改变代码和系统状态，Evaluator 则主动寻找实现与验收标准之间的偏差。


* **role-specialized agents**：多 Agent 的价值不首先来自数量，而来自职责、目标、输入、工具和输出契约的差异。不同 Agent 承担不同阶段的决策，使整个 Harness 可以把“规划、执行、验证”拆成相互制约的运行角色。

---

#### 先从 Planner 开始：它不是“Generator 前面多想一遍”

Anthropic 给 Planner 的输入其实非常短。

文章中的实验从：

```text
1～4 句话的用户 prompt
```

开始。

Planner 的任务是把它扩展成：

```text
完整 product spec
```

但这里有一个非常有意思的限制：

> Planner 被要求关注产品上下文和 high-level technical design，而不要过早规定过细的实现细节。

为什么？

因为 Planner 自己也会犯错。

假设用户只说：

```text
做一个 2D retro game maker。
```

如果 Planner 一上来就规定：

```text
LevelEditor 第 892 行应该这样写；
Frame API 一定使用某套 route；
状态一定存在某个 React hook；
数据库一定拆成某几个 table；
```

那么只要前期其中一个技术判断错了：

```text
Planner mistake
      ↓
写进 Spec
      ↓
Generator 把它当约束
      ↓
错误被实施
      ↓
Evaluator 再围绕错误结构验
```

一个早期错误就可能向下游 cascade。

所以 Anthropic 的选择反而是：

```text
Planner
负责确定：
“要交付什么”

而不是过早确定：
“每一行应该怎么写”
```

这和我们前面 Spec 讨论其实很一致。

好的上层 Spec 应该更多约束：

```text
Deliverables
Behavior
Scope
Product direction
Important constraints
```

而不是提前替执行者写完：

```text
implementation recipe
```

Anthropic 明确说，他们更愿意约束最终应交付什么，再让后续 Agent 在工作过程中决定实现路径。

---

#### 所以 Planner 输出的是 Generator 的“任务世界”

可以把它理解成：

```text
User
  │
  │  一两句话
  ▼
Planner
  │
  │  扩展产品意图
  ▼
Product Spec
  │
  ├─ Features
  ├─ Scope
  ├─ Product behavior
  ├─ High-level technical direction
  └─ Design direction
       │
       ▼
    Generator
```

Planner 并没有直接把代码改好。

它改变的是：

> **后面 Generator 看到的任务定义。**

这已经说明 role-specialization 的第一层：

```text
Planner 的产物
≠
最终软件
```

它的产物是：

```text
另一个 Agent 的工作约束
```

---

#### Generator 的目标完全不同：不是写 Spec，而是改变世界

接下来才轮到 Generator。

Anthropic 的第一版 full-stack Harness 里，Generator 按 Sprint、按 feature 工作，真正使用 React、Vite、FastAPI、SQLite/PostgreSQL 等栈去实现应用，并通过 Git 管理变化。

所以 Generator 的核心 loop 更接近我们前面已经研究过的：

```text
Spec / Contract
       ↓
读代码
       ↓
形成 hypothesis
       ↓
Edit / Bash / Tool
       ↓
Environment changes
       ↓
Tool result
       ↓
继续修
```

它拥有的是：

```text
execution objective
```

也就是：

> **怎样让当前 Artifact 越来越接近目标。**

Planner 的问题是：

```text
“What should exist?”
```

Generator 的问题是：

```text
“How do I make it exist?”
```

虽然它们都可以是 Claude，但系统给它们的工作问题已经不是同一个问题。

---

#### Evaluator 又反过来：它不是另一个 Generator

到了 Evaluator，目标再次翻转。

它不是：

```text
继续帮 Generator 把代码写得更好。
```

而是：

```text
根据已经约定的标准，
寻找当前实现还不能被接受的证据。
```

所以它拿到：

```text
running App
Playwright MCP
API
database state
Sprint Contract
```

以后，做的是：

```text
点击
检查
尝试
制造失败
比较 expected / observed
```

而不是继续：

```text
“我觉得这里应该改成这样。”
```

Anthropic 的 Evaluator 会直接操作运行中的应用，测试 UI、API 和数据库状态，再按照 criteria 决定 Sprint 是否失败。

于是三个 Agent 的目标其实可以压成：

| Role      | 核心问题            |
| --------- | --------------- |
| Planner   | 我们到底应该交付什么？     |
| Generator | 怎样让这个东西真实存在？    |
| Evaluator | 有什么证据说明它还不能算完成？ |

这才是分角色的意义。

---

#### 三个 Agent 最重要的差异其实是 Objective

假设让三个 Agent 都读：

```text
同一个 repo
同一个 prompt
```

但是目标不同：

```text
Planner:
扩大、组织和约束产品目标

Generator:
最大化实现进度

Evaluator:
寻找违反 acceptance criteria 的反例
```

那么它们即使使用完全相同的底层模型，行为也会明显不同。

因为：

```text
same model
+
different objective
+
different context
+
different tools
=
different runtime role
```

所以：

> **Agent role 不是给 Claude 起一个名字，而是在 Harness 中定义它究竟优化什么。**

这和很多 Multi-Agent Demo 最大的区别就在这里。

差的“角色扮演”可能只是：

```text
You are a senior developer.

You are a product manager.

You are a QA engineer.
```

然后三个人都在聊天。

真正的 Harness role 则还应该对应：

```text
谁能改 Artifact？
谁只能评估？
谁写什么文件？
谁读谁的输出？
什么时候被调用？
谁决定下一阶段是否开始？
```

---

#### Anthropic 甚至让 Generator 和 Evaluator 在写代码前先交锋一次

这一点其实特别能说明它们不是三个独立聊天窗口。

每个 Sprint 开始前：

```text
Generator
    ↓
提出：
我要实现什么
如何证明它完成

    ↓

Evaluator
    ↓
检查：
这些 deliverables 对吗？
这些验证足够吗？

    ↓

不同意
    ↓
继续修改 Contract

    ↓

双方 agree
    ↓
Generator 才开始 Coding
```

这意味着 Evaluator 并不是：

```text
所有代码写完以后
突然冒出来打分
```

它提前参与了：

```text
“Done 到底意味着什么”
```

的定义。

因此真正的工作流是：

```text
Planner
    ↓
High-level Spec
    ↓
Generator + Evaluator
    ↓
Testable Contract
    ↓
Generator
    ↓
Artifact
    ↓
Evaluator
    ↓
Failure Evidence
    ↓
Generator
```

这已经不是：

```text
三个 Agent 各做一个任务
```

而是：

> **不同角色围绕同一 Artifact 建立显式的信息依赖和反馈关系。**

---

#### Agent 之间甚至不需要“聊天”

Anthropic 这套实验里还有一个我觉得特别有 Harness 味道的设计：

**Agent 之间主要通过文件通信。**

一个 Agent 写文件，另一个 Agent 读文件，再通过修改文件或写新文件回应。

为什么不直接：

```text
Agent A → message → Agent B
```

当然直接传消息也可以。

但文件有一个明显优点：

```text
conversation
是瞬时执行上下文

artifact
是显式任务状态
```

这恰好又接回 Macro 1。

例如：

```text
product-spec.md
sprint-contract.md
qa-report.md
```

这样的文件可以：

```text
被另一个 Agent 读取
被人类检查
进入 Git
跨 context 保留
发生失败以后重新恢复
```

于是 Multi-Agent communication 不再只是：

```text
A 记得 B 刚才说过什么
```

而是：

```text
A 和 B
围绕共享 Artifact
交换显式状态
```

这其实比“Agent 群聊”更接近工程系统。

---

#### 我现在会怎样区分“多 Agent”和“多人聊天”

一个聊天式 Multi-Agent：

```text
Agent A
  ↓ message
Agent B
  ↓ message
Agent C
  ↓ message
Agent A
```

主要依赖：

```text
conversation traffic
```

而 Anthropic 这套 Harness 更接近：

```text
           Product Spec
                │
                ▼
             Planner
                │
                ▼
          Shared Artifact
                │
        ┌───────┴────────┐
        ▼                ▼
    Generator        Evaluator
        │                │
        ▼                │
      Code               │
        │                │
        └───────────────→│
                         ▼
                     QA Report
                         │
                         ▼
                     Generator
```

真正中心的位置其实不是 Agent。

而是：

```text
Artifact + Contracts + Feedback
```

Agent 只是承担不同职责的执行者。

这也是为什么我觉得“多 Agent”这个词有时会让人误解。

它太容易让人把注意力放到：

```text
Agent 数量
```

而不是：

```text
work decomposition
state handoff
role boundary
feedback topology
```

上。

---

#### Primitive 和 Architecture 是两回事

这一点其实很适合面试里问。

假设一个 framework 给你：

```text
spawnAgent()
```

这只证明：

> 系统支持 delegation。

它不能告诉你：

```text
什么时候 spawn？
spawn 谁？
为什么要 spawn？
给它什么 context？
让它拿什么 Tool？
它输出什么 Artifact？
谁消费这个 Artifact？
它失败以后怎么办？
```

这些才构成：

```text
Multi-Agent architecture
```

所以：

```text
runtime primitive
```

和：

```text
orchestration policy
```

必须分开。

Claude Code `AgentTool` 更像前者。

Anthropic 那篇文章的 Planner / Generator / Evaluator Harness 更像后者。

---

#### 这也解释了为什么“多 Agent”不是越多越好

如果我已经拥有：

```text
AgentTool
```

理论上可以：

```text
spawn 2 个
spawn 5 个
spawn 20 个
```

但增加 Agent 数量意味着同时增加：

```text
Context handoff
Token cost
Tool cost
Scheduling
Filesystem conflicts
Permission complexity
Failure handling
Result aggregation
```

因此需要问的始终不是：

```text
“还能不能再开一个 Agent？”
```

而是：

> **这里是否真的存在一个值得单独隔离的职责？**

Anthropic 三 Agent 的每一个角色都有非常具体的来源：

* Planner：解决原始 prompt 下 Generator 容易 underscope 的问题；
* Generator：承担真实建设工作；
* Evaluator：解决 self-evaluation 和真实 Bug 漏检。

也就是说：

```text
先观察 failure
    ↓
再创建 role
```

而不是：

```text
先决定我要 Multi-Agent
    ↓
再给五个 Agent 编职位名称
```

这和整篇 Harness 文章的方法论其实完全一致。

---

#### 一个 Agent 应该对应一个“需要隔离的失败模式”

我觉得这是特别值得记进自己的面试答案里的。

例如：

##### 如果 Generator 总是 underscope

```text
raw prompt
    ↓
直接 Coding
    ↓
产品做得很薄
```

那可以引入：

```text
Planner
```

让 scope definition 独立发生。

---

##### 如果 Generator 总是自评过于乐观

```text
implementation
    ↓
“我觉得好了”
```

那可以引入：

```text
Evaluator
```

让 verification 独立发生。

---

##### 如果某项研究会污染主 Agent context

可能引入：

```text
Research subagent
```

在独立 context 中完成 investigation，再只带回结果。

---

也就是说：

> **Subagent 最合理的创建依据，是存在一个值得隔离的工作目标或 failure mode。**

不是：

```text
这个任务看起来很复杂，
所以多开几个。
```

---

#### 这里又接回了 Macro 1 的 Context 问题

Subagent 其实还有一个非常重要的附带价值：

```text
context isolation
```

假设主 Agent 要修一个 bug。

期间需要调查：

```text
整个大型 SDK 的 30 个文件
阅读大量文档
跑十几个探索命令
```

如果全部塞回主 context：

```text
main context
    ↓
越来越长
    ↓
irrelevant exploration
    ↓
coherence degradation
```

而 Subagent 可以：

```text
Main Agent
    │
    │ “调查这个问题，最后只给我结论和证据”
    ▼
Subagent
    │
    ├─ 读 30 个文件
    ├─ 跑大量命令
    ├─ 产生大量中间失败
    │
    ▼
Compact result
    │
    ▼
Main Agent
```

于是：

```text
大量 exploration context
```

留在子 Agent。

主 Agent 只接收：

```text
task-relevant result
```

Claude Code 的 `AgentTool` 能启动独立 Agent，是支撑这种设计的 runtime primitive；但具体什么时候这样用，仍然属于上层 orchestration policy。

---

#### Multi-Agent 的核心其实是信息边界

到这里，我觉得可以把一个 Agent role 拆成五个问题：

```text
1. Goal
   它到底负责解决什么问题？

2. Context
   它应该知道什么，不应该知道什么？

3. Tools
   它能触碰哪些现实世界接口？

4. Artifact
   它完成以后留下些什么？

5. Consumer
   谁读取它的结果并决定下一步？
```

如果这五个问题说不清楚，只剩：

```text
Agent A
Agent B
Agent C
```

那 Multi-Agent 很可能只是 UI 上看起来热闹。

---

#### Planner / Generator / Evaluator 正好可以这样拆

| Role      | Goal                   | 主要输入                       | 主要输出                    | 谁消费                   |
| --------- | ---------------------- | -------------------------- | ----------------------- | --------------------- |
| Planner   | 定义足够完整的产品目标            | 用户短 Prompt                 | Product Spec            | Generator / Evaluator |
| Generator | 让 Artifact 满足 Contract | Spec + Contract + Feedback | 可运行应用                   | Evaluator             |
| Evaluator | 寻找尚未满足的要求              | Contract + Running App     | Failure Evidence / PASS | Generator / Harness   |

Anthropic 的文件通信机制，让这些输出不是模糊的：

```text
“我刚才和另一个 Agent 聊过”
```

而是显式 Artifact。

所以真正的 Multi-Agent Harness 更像：

```text
typed dataflow
```

而不是：

```text
group chat
```

这里的 “typed” 只是帮助理解，不是说 Anthropic 实现了某种编程语言类型系统。

---

#### 一个我现在会在面试里给出的回答

如果面试官问：

> Multi-Agent Harness 的价值是什么？是不是模型不够强，所以多调用几次？

我会回答：

> Multi-Agent 的主要价值不是增加模型调用数量，而是把互相冲突或需要隔离的职责拆开。比如 Planner 优化 scope 和 deliverables，Generator 优化 implementation progress，Evaluator 则优化 falsification 和 acceptance verification。每个角色可以拥有不同 context、tools、model、permission 和工作环境，并通过显式 artifact 交接状态。这样做的价值来自 role boundary 和 feedback topology，而不是“有三个 Claude”。

如果继续追问 Claude Code：

> Claude Code 本身是不是 Planner / Generator / Evaluator？

就应该回答：

> 不能这么从源码推出。Claude Code v2.1.88 的 `AgentTool` 能证明的是 runtime 支持向 specialized subagent delegation，并提供 model override、background execution、cwd 和 worktree isolation 等能力。Anthropic 的 Planner / Generator / Evaluator 是另一层建立在 Agent SDK 上的实验 orchestration architecture。

这两个层级一定要分清。

---

#### Macro 6 的核心可以压成这一张图

```text
                   User Goal
                       │
                       ▼
                    Planner
                       │
                       │ Product Spec
                       ▼
              ┌─────────────────┐
              │ Shared Artifacts│
              └────────┬────────┘
                       │
             Sprint Contract
                       │
                       ▼
                   Generator
                       │
                       │ runnable artifact
                       ▼
                   Evaluator
                       │
                       │ failure evidence
                       └──────────────┐
                                      │
                                      ▼
                                  Generator
```

而在更底层：

```text
Claude Code Runtime
────────────────────────

AgentTool
├─ prompt
├─ subagent_type
├─ model
├─ run_in_background
├─ cwd
├─ isolation: worktree
└─ permission mode
```

上层回答：

```text
为什么分这些角色？
```

底层回答：

```text
怎样把另一个 Agent 真正跑起来？
```

这就是 architecture 和 primitive 的区别。

---

#### 源码与证据边界

从 Anthropic 的 2026 年长任务 Harness 文章可以直接确认：

* 最终 full-stack 实验采用 Planner、Generator、Evaluator 三角色架构；
* Planner 把很短的用户 prompt 扩展成 product spec，但被刻意限制在产品上下文和高层技术设计，避免过早错误细节向下游 cascade；
* Generator 负责真实实现工作，而 Evaluator 负责通过运行中的应用验证功能；
* Generator 和 Evaluator 会在编码前协商 Sprint Contract；
* 各 Agent 之间通过文件形式的 Artifact 通信。

从 Claude Code v2.1.88 的恢复源码可以直接确认：

* `AgentTool` 的目标是启动另一个 Agent，并明确提供 delegation 到 subagent 的能力；
* 输入可以指定任务 prompt、`subagent_type` 和 model override；
* Agent 可以同步运行，也可以通过 `run_in_background` 进入后台任务生命周期；
* Agent invocation 还可携带工作目录、权限模式和 worktree isolation 等执行配置；
* Agent definition 还会受到当前 MCP availability 与 permission rule 的过滤。

但这些源码证据不能证明 Claude Code 主循环固定采用：

```text
Planner → Generator → Evaluator
```

这一架构。


到这里很容易再次产生一种冲动：

```text
Context Reset 有用
Planner 有用
Evaluator 有用
Sprint 有用
Subagent 有用
Worktree 有用

        ↓

那就全部保留。
```

但 Anthropic 接下来做的事情恰恰相反。

他们发现：

```text
Harness component
```

本质上都在表达一句话：

> **“我认为当前模型自己做不好这件事，所以我替它加一层结构。”**

问题是：

```text
模型会变。
```

Sonnet 4.5 需要的 Context Reset，到 Opus 4.5 已经可以删除。

Opus 4.5 需要的 Sprint decomposition，到 Opus 4.6 又开始可以删除。

Evaluator 也不是永远有收益：如果任务已经落入当前模型的 solo reliability boundary，它就会从质量保障变成额外 token、latency 和 orchestration cost。Anthropic 因而建议逐个移除 Harness 组件并重新测量效果，而不是把历史 scaffolding 永远积累下去。

所以接下来要进入这篇文章里我认为最适合面试的一层：

