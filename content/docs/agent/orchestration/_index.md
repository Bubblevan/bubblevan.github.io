---
title: "Agent Orchestration"
---

## 1. 先别急着加 Agent——Orchestration 到底在控制什么

看到一个需要多步处理的任务，很容易直接想到：

```text
拆成几个 Agent
→ 分别执行
→ 最后汇总
```

但多开几个模型调用，并没有回答“为什么需要编排”。

同一个模型可以连续调用三次，也可以并行调用十次；可以让一个模型负责生成、另一个模型负责检查；甚至可以让中央模型临时决定还需要多少个 worker。这些系统的复杂度差异很大，却都能被笼统地画成几个 `LLM` 方框和几条箭头。如果只从“用了多少个 Agent”观察，很难解释 Prompt Chaining、Routing、Parallelization、Orchestrator–Workers 和 Evaluator–Optimizer 为什么要被区分开。

Anthropic 在 *Building effective agents* 中采用了另一条起点：先区分 **workflow** 和 **agent**，再从一个带有 retrieval、tools、memory 等能力的 augmented LLM 出发，逐步增加控制结构。这里更关心的不是“系统里有几个模型”，而是：

```text
下一步由谁决定？
调用什么由谁决定？
任务怎样被拆分？
哪些步骤可以同时执行？
结果不合格时，谁决定继续？
```

这些问题共同指向的是 **control flow**。

本文讨论 Agent Orchestration，也从这条线开始。

### 1.1 一次 LLM Call 不等于一个 Agent 系统

最简单的 LLM 应用只有一次映射：

```text
Input
  │
  ▼
 LLM
  │
  ▼
Output
```

例如输入一段代码，要求模型解释它做了什么；或者给出一封邮件，让模型生成摘要。此时程序决定什么时候调用模型，模型拿到输入后产生输出，这次调用结束，整个任务也就结束了。

实际应用通常不会停在这里。模型还可能需要搜索文档、查询数据库、调用 API，或者读取之前保存的信息。Anthropic 把这样的基础单元称为 **augmented LLM**：

```text
                    ┌───────────┐
                    │ Retrieval │
                    └─────┬─────┘
                          │
                          ▼
Input ────────────────►  LLM  ◄────────────── Memory
                          │
                          ▼
                        Tools
                          │
                          ▼
                       Output
```

这里的 retrieval、tools 和 memory 扩展了模型能够获得的信息和执行的动作。例如模型可以自己构造搜索 query、选择工具，或者决定当前回答需要读取哪些上下文。

但“模型会使用工具”仍然不足以定义这里讨论的 orchestration。

设想下面三个系统：

```text
A:
用户问题
  ↓
LLM
  ↓
答案
```

```text
B:
用户问题
  ↓
LLM
  ↓
搜索工具
  ↓
LLM
  ↓
答案
```

```text
C:
用户问题
  ↓
判断任务类型
  ├─────────────┐
  ↓             ↓
技术支持 LLM   退款处理 LLM
  │             │
  └──────┬──────┘
         ↓
       答案
```

B 比 A 多了工具调用；C 又增加了多个下游处理路径。但真正发生变化的不只是模型能力，而是程序开始规定：

* 什么条件下还需要一次模型调用；
* 上一次结果送给哪个下游步骤；
* 哪些步骤之间存在依赖；
* 哪些结果可以被接受，哪些必须继续处理。

因此，本文把 **orchestration** 暂时定义为一个工程上的工作概念：

> Orchestration 描述系统如何组织模型、工具和程序逻辑之间的控制流：下一步执行什么、由谁执行、拿什么作为输入，以及什么时候继续、分支、汇合或停止。

这个定义是本文为了分析几种 pattern 使用的抽象，不是 Anthropic 给出的术语定义。

它也意味着需要先分开三个经常混在一起的问题：

```text
Model Capability
模型本身能理解和生成什么

Tool Capability
模型能够读取什么、执行什么动作

Control Flow
这些能力以什么顺序、条件和依赖关系被调用
```

例如，给同一个 Claude 配上网页搜索工具改变了第二项；把“搜索 → 总结”固定成两步 Prompt Chaining，则改变了第三项。换成更强的模型主要改变第一项，但未必改变系统的控制拓扑。

后面讨论的五种 pattern，主要发生在第三层。

### 1.2 Workflow 和 Agent 的分界，不在于有几个 LLM

Anthropic 在文章开头先给 `agentic systems` 划了一条架构边界：

```text
Workflow
LLM 和工具沿预定义的代码路径运行

Agent
LLM 动态决定自己的过程和工具使用方式
```

这个区分比“单 Agent / 多 Agent”更适合解释后面的五种 pattern。

以 Routing 为例：

```text
                     ┌─► Billing workflow
                     │
Request ─► Router ───┼─► Technical support
                     │
                     └─► General QA
```

Router 完全可以由一个 LLM 实现。它读取用户请求，然后判断应该进入哪个分支。这里已经出现了“模型在做决策”，但整个候选空间仍然由程序提前规定：

```python
route ∈ {
    "billing",
    "technical_support",
    "general_qa",
}
```

模型只能在已有路径之间选择，所以 Anthropic 仍将 Routing 称为 workflow。

Evaluator–Optimizer 甚至可能同时出现两个不同职责的模型：

```text
Generator
    │
    ▼
Candidate
    │
    ▼
Evaluator
  │     │
pass  feedback
  │     │
  ▼     └────────► Generator
Done
```

但“两个模型互相对话”也没有让它自动变成 Agent。Generator 负责生成，Evaluator 负责评价，不合格时再进入下一轮，这个角色结构和循环协议仍然是开发者事先写好的。

更容易混淆的是 Orchestrator–Workers：

```text
                    ┌─► Worker 1
                    │
Request ─► Orchestrator ─► Worker 2
                    │
                    └─► Worker N
                            │
                            ▼
                         Synthesis
```

这里中央 orchestrator 会根据具体输入 **动态决定需要哪些子任务**。处理一个代码修改请求时，它可能发现只需要改一个文件；另一个请求可能涉及 API、数据库 schema、前端组件和测试，因此临时拆出四组工作。

这已经存在明显的运行时动态性，但 Anthropic 仍然把它列在 workflow 一侧。

原因在于动态的对象是：

```text
这一次具体生成哪些 subtasks
```

而不是整个执行协议都交给模型决定。系统仍然预先规定了类似这样的高层结构：

```text
Orchestrator
    ↓
decompose
    ↓
Workers
    ↓
collect results
    ↓
synthesize
```

换句话说，可以把它理解成：

```text
高层控制协议：预定义
具体任务集合：运行时生成
```

真正进入 Anthropic 所说的 Agent 后，模型获得的控制权更大。典型执行过程更接近：

```text
Task
  │
  ▼
LLM
  │
  ├─► read_file
  │       │
  │       ▼
  │    observation
  │       │
  ├───────┘
  │
  ├─► run_tests
  │       │
  │       ▼
  │    observation
  │       │
  ├───────┘
  │
  ├─► edit_file
  │
  ...
  │
  ▼
 Done
```

在每一次 observation 返回后，模型重新判断：

```text
现在是否已经完成？
下一步需要什么信息？
应该调用哪个工具？
是否需要修改原计划？
是否遇到了阻塞？
```

程序仍然会提供工具、权限、最大迭代次数、预算和其他 stopping condition，并不意味着模型获得无限制控制权。区别在于，在这些边界内部，**完成任务所需的具体路径不再由开发者提前完整编码**。

因此至少可以排除几个常见误判：

```text
用了 Tool
≠ Agent

调用了多个 LLM
≠ Multi-Agent System

有一个 Planner
≠ Agent

存在循环
≠ Agent

模型做了某个分类决策
≠ Agent
```

更值得问的是：

> 模型究竟被允许决定控制流中的哪些变量？

这也解释了为什么 Anthropic 建议先寻找能够解决问题的最简单方案。很多任务使用单次 LLM 调用，加上 retrieval 和 in-context examples 就已经足够；如果任务能够稳定拆成固定步骤，workflow 通常还能提供更可预测的行为。只有当任务路径本身难以预先写死时，把更多控制权交给 Agent 才开始具有实际意义。

增加自主性同时也会扩大需要验证的状态空间。固定的：

```text
A → B → C
```

至少可以枚举主要路径；如果每一步都允许模型根据 observation 重新决定下一步，运行轨迹就可能变成：

```text
A → Tool 1 → B → Tool 3 → B
            ↘ Tool 2 → C
```

甚至同一输入在两次运行中产生不同轨迹。

所以从 workflow 走向 agent，并不是给系统增加一个更高级的标签，而是在改变：

```text
谁拥有下一步的决策权。
```

### 1.3 五种 Pattern，其实在移动控制流里的不确定性

如果只背 Anthropic 给出的五个名字，很容易得到一组互相独立的定义：

```text
Prompt Chaining
Routing
Parallelization
Orchestrator–Workers
Evaluator–Optimizer
```

真正实现时仍然会碰到问题：

> 我现在这个任务到底应该用哪个？

后面几节会分别讨论每一种 pattern。这里先建立一个统一坐标系，把它们看成对 **不同位置的不确定性** 的处理方式。

这个坐标系是本文在 Anthropic 五种 workflow pattern 之上做的工程归纳，不是 Anthropic 原文提供的正式 taxonomy。

先看五种控制流最小化后的形状：

```text
Prompt Chaining

A → B → C
```

```text
Routing

      ┌→ B
A → R ┼→ C
      └→ D
```

```text
Parallelization

      ┌→ B ─┐
A ────┼→ C ─┼→ Merge
      └→ D ─┘
```

```text
Orchestrator–Workers

           ┌→ W₁ ─┐
A → O ─────┼→ W₂ ─┼→ Synthesis
           ├→ ... │
           └→ Wₙ ─┘
```

```text
Evaluator–Optimizer

Generator → Evaluator
    ▲          │
    └─feedback─┘
```

这些图看起来只是箭头不同，但背后的控制问题并不一样。

| Pattern              | 运行前已经知道什么                            | 运行时需要决定什么     | 主要控制结构              |
| -------------------- | ------------------------------------ | ------------- | ------------------- |
| Prompt Chaining      | 有哪些步骤、先后顺序                           | 每一步产生的具体内容    | 串行依赖                |
| Routing              | 有哪些候选分支                              | 当前输入进入哪个分支    | 条件分支                |
| Parallelization      | 有哪些任务或重复尝试                           | 各分支产生什么结果     | fan-out / aggregate |
| Orchestrator–Workers | orchestrator / worker / synthesis 协议 | 需要拆出哪些子任务以及数量 | 动态分解                |
| Evaluator–Optimizer  | generator / evaluator 角色及反馈协议        | 当前结果是否合格、如何修改 | 反馈循环                |

这里能看到一个比“五种模式”更连续的变化。

Prompt Chaining 几乎把控制流全部提前写好：

```text
Step 1
  ↓
Step 2
  ↓
Step 3
```

不确定的是每一步会生成什么内容，而不是下一步去哪里。

Routing 放开了一点：

```text
下一步不是固定的，
但候选路径是固定的。
```

Parallelization 改变的又不是“选哪条路”，而是：

```text
这些相互独立的工作
不必继续排成一条串行链。
```

Orchestrator–Workers 再向前走一步。开发者甚至无法提前写出这次运行具体有哪些 worker task，于是把 **任务分解** 本身交给模型。

Evaluator–Optimizer 则处理另一种不确定性：

```text
第一次生成以后，
我们还不知道结果是否已经足够好。
```

因此系统需要显式的评价与反馈路径，而不是默认一次 generation 就结束。

把它们放到几个控制维度上，可以得到更清楚的比较：

| 控制维度 | 固定的一端   | 动态的一端        |
| ---- | ------- | ------------ |
| 执行顺序 | 固定串行步骤  | 根据运行状态改变     |
| 路径选择 | 唯一路径    | 从多个候选中动态选择   |
| 任务分解 | 子任务预先定义 | 运行时生成子任务     |
| 执行关系 | 串行      | 并行 / fan-out |
| 完成判断 | 运行一次即结束 | 根据评价继续迭代     |

这里不要把它误解成一条“越靠右越高级”的升级路线。

例如，一个每天运行的文档处理流水线如果始终只有：

```text
提取字段
→ 校验 JSON
→ 生成摘要
```

那么 Prompt Chaining 比开放式 Agent 更容易观察，也更容易复现失败。反过来，如果 coding task 在运行前连需要读取和修改哪些文件都不知道，硬把所有步骤编码成固定 chain，就会把大量任务特定的判断塞进条件分支里。

选择 Pattern 的问题因此可以改写成：

> **当前无法提前确定的东西究竟是什么？**

如果不知道的是：

```text
下一步应该进入哪个已知流程
```

优先考虑 Routing。

如果知道所有子任务，而且它们彼此独立：

```text
没有必要排队等待
```

可以考虑 Parallelization。

如果不知道：

```text
这次任务究竟应该拆成哪些子任务
```

才需要考虑 Orchestrator–Workers。

如果问题出在：

```text
能生成结果，
但一次生成不能可靠判断质量是否足够
```

则 Evaluator–Optimizer 更直接。

如果进一步连：

```text
需要多少步
使用什么工具
下一步做什么
什么时候修改计划
```

都难以预先编码，问题才逐渐越过固定 workflow 的边界，进入 Agent 更擅长处理的区域。

因此，后面讨论五种 pattern 时，我不会把它们当成五个需要背诵的架构模板，而会一直追踪四件事：

```text
1. 哪一部分控制流是固定的？
2. 哪一部分决策交给了模型？
3. 这种动态性解决了什么具体问题？
4. 它又增加了哪些 latency、cost 和 failure modes？
```

下一节从限制最多的一种开始：**Prompt Chaining**。它没有尝试让模型自由规划整个任务，而是利用一个更简单的前提——如果任务已经能够稳定拆成几个有数据依赖的步骤，就先把每一步分别做好。

## 2. Prompt Chaining——已知步骤时，把一个难调用拆成几个简单调用

Prompt Chaining 是五种 workflow 里控制结构最容易看懂的一种：

```text
Input
  │
  ▼
LLM A
  │
  ▼
LLM B
  │
  ▼
LLM C
  │
  ▼
Output
```

Anthropic 对它的定义很直接：把一个任务拆成一系列步骤，每次 LLM 调用处理上一次调用产生的结果；必要时，可以在中间插入程序化检查，也就是原文图里的 `gate`。这种方式适合能够被清楚拆成固定子任务的场景，主要交换关系是：

```text
更多调用
+
更高 latency

换取

每次调用面对更简单的问题
+
更容易检查中间结果
```

Anthropic 在原文中给出的两个例子分别是：

```text
生成营销文案
→ 翻译成另一种语言
```

以及：

```text
生成文章大纲
→ 检查大纲是否满足条件
→ 根据大纲写正文
```

Prompt Chaining 的价值并不只是“复杂任务要一步一步做”。如果只是把一段长 Prompt 人工拆成三段，但步骤之间没有明确的数据依赖，也没有任何中间状态值得观察，那么增加三次 API 调用未必得到什么。

真正值得保留的是两个性质：

```text
前一步的输出
确实构成后一步的输入

以及

中间结果本身值得检查
```

这两点决定了 Prompt Chaining 为什么既是一种 decomposition pattern，也是一种 observability pattern。

### 2.1 Chain 的关键不是“调用很多次”，而是显式的数据依赖

先看一个看起来像 Prompt Chaining、实际上没有多少意义的例子：

```text
LLM 1:
分析一下这个需求。

LLM 2:
再仔细想想这个需求。

LLM 3:
现在给我最终答案。
```

当然，它可能偶尔比一次回答表现更好，但三个步骤之间的 contract 很弱。第二步到底应该继承什么？第一步应该产出什么结构？第三步又依赖其中哪些信息？程序很难回答。

更典型的 Prompt Chaining 应该接近：

```text
Raw Requirement
      │
      ▼
   LLM 1
生成结构化需求
      │
      ▼
Requirement Spec
      │
      ▼
   LLM 2
生成实现计划
      │
      ▼
Implementation Plan
      │
      ▼
   LLM 3
生成代码
```

这里每一个箭头都有可以说清楚的数据含义：

```text
raw requirement
→ normalized requirement

normalized requirement
→ implementation plan

implementation plan
→ code
```

也就是说，Chain 更接近一个有类型的数据流水线：

```text
A → B → C → D
```

而不是：

```text
Prompt → Prompt → Prompt
```

例如，一个 SQL 生成任务可以设计成：

```text
Natural Language Question
          │
          ▼
        LLM
          │
          ▼
Structured Query Plan
          │
          ▼
     Schema Check
          │
          ▼
        LLM
          │
          ▼
         SQL
          │
          ▼
   Parser / EXPLAIN
          │
          ▼
       Execute
```

假设用户问：

```text
统计最近 30 天完成订单中，
每个地区的退款率，
按退款率从高到低排列。
```

第一步不直接生成 SQL，而是生成类似：

```json
{
  "tables": ["orders", "refunds"],
  "filters": [
    "orders.created_at >= now() - interval '30 days'",
    "orders.status = 'completed'"
  ],
  "group_by": ["region"],
  "metrics": [
    "completed_orders",
    "refunded_orders",
    "refund_rate"
  ],
  "order_by": "refund_rate DESC"
}
```

程序可以在 SQL 真正生成之前检查：

```text
表是否存在？
字段是否存在？
是否请求了禁止访问的数据？
metric 是否有定义？
```

检查通过后，再把这个结构化计划交给下一次调用生成 SQL。

相比直接：

```text
Question
   ↓
 LLM
   ↓
 SQL
```

Prompt Chaining 在这里增加的并不是一种新的模型能力。模型原本就可能一次生成正确 SQL。

它增加的是一个显式的中间状态：

```text
Query Plan
```

于是原本只能看到：

```text
输入问题
→ 最终 SQL 错了
```

现在可以进一步区分：

```text
需求理解错了？
        │
        ├─ 是 → Query Plan 已经错
        │
        └─ 否 → SQL generation 阶段出错
```

这种可定位性在工程上比“让模型多思考一次”更有价值。

同样的思想也适用于文章生成。

一个单次调用可能是：

```text
topic
  ↓
LLM
  ↓
完整文章
```

Chain 可以改成：

```text
topic
  ↓
outline
  ↓
outline check
  ↓
section plan
  ↓
draft
```

如果最后文章遗漏了一个必须讨论的问题，就不必直接归因于“模型写作能力不好”。可以先检查：

```text
outline 里有没有？

有
→ Draft 阶段丢失

没有
→ Planning 阶段已经遗漏
```

这里已经能看到 Prompt Chaining 和一次大型 Prompt 的根本区别：

```text
单次调用：
内部推理过程主要留在模型调用内部

Prompt Chaining：
把部分任务状态外显成应用可以读取、记录和验证的 artifact
```

这也是为什么 Anthropic 目前的 Prompting 文档仍然保留显式 chaining。较新的模型已经能够在单次调用内部处理很多多步推理，但如果开发者需要：

```text
inspect intermediate outputs
log intermediate outputs
branch based on intermediate outputs
enforce a pipeline structure
```

显式拆成多个 API call 仍然有意义。

因此判断是否需要 Chain 时，一个比“这个任务复杂吗”更有用的问题是：

> **有没有某个中间产物，我希望应用程序能够明确看见？**

如果答案是否定的，只是希望模型“多想两步”，那么未必需要把推理过程拆成多个外部调用。

如果答案是：

```text
我需要拿到一个明确的 Plan，
后面所有步骤都必须基于这个 Plan，
而且我希望单独验证它，
```

这就很接近 Prompt Chaining 的适用条件。

### 2.2 Gate 的意义，是在错误继续传播之前截住它

Anthropic 在 Prompt Chaining 的示意图里专门画了一个 `gate`。

这不是装饰。

假设有这样一条流水线：

```text
Requirement
    │
    ▼
  LLM A
    │
    ▼
  Plan
    │
    ▼
  LLM B
    │
    ▼
  Code
```

如果 `Plan` 已经错误，LLM B 很可能会忠实地沿着错误计划继续工作：

```text
Requirement
    │
    ▼
Wrong Plan
    │
    ▼
Consistent but Wrong Code
```

Chain 并不会自动修复这种问题。相反，它还可能把前一步的错误稳定地传递到后面的所有步骤。

因此真正有价值的形式通常是：

```text
Requirement
    │
    ▼
  LLM A
    │
    ▼
  Plan
    │
    ▼
   Gate
  ┌─┴─────────┐
  │ valid     │ invalid
  ▼           ▼
LLM B       reject /
  │         regenerate
  ▼
Code
```

最简单的 gate 完全不需要 LLM：

```python
plan = generate_plan(requirement)

errors = validate_plan(plan)

if errors:
    return {
        "status": "invalid_plan",
        "errors": errors,
    }

code = generate_code(plan)
```

如果输出必须符合 JSON Schema：

```python
from pydantic import BaseModel


class Plan(BaseModel):
    files: list[str]
    steps: list[str]
    tests: list[str]


raw = llm(prompt)
plan = Plan.model_validate_json(raw)
```

至少可以阻止：

```text
缺字段
类型错误
结构损坏
```

继续传到下游。

对于 SQL，可以检查：

```text
AST 是否能 parse
引用的 table 是否存在
是否包含禁止的 statement
EXPLAIN 是否成功
```

对于代码，可以运行：

```text
formatter
type checker
unit test
lint
```

对于一篇技术文章的大纲，可以检查：

```text
必须覆盖哪些问题
是否出现重复 section
引用是否已经有来源
是否把计划中的内容写成了完成结果
```

这些 gate 的共同点是：

> **只要判断条件能够可靠地用程序表示，就没有必要把所有判断重新交给模型。**

例如要求：

```text
结果必须包含字段:
title
summary
sources
```

适合 schema validation。

要求：

```text
Python 代码是否能通过类型检查
```

适合执行 `mypy` 或其他实际 verifier。

要求：

```text
SQL 有没有 DELETE
```

可以直接分析 AST。

如果已经存在确定性检查：

```text
Programmatic Check
```

再加一次：

```text
LLM:
“你觉得这里有没有 DELETE？”
```

反而增加额外的不确定性和成本。

这也需要避免另一个极端：并不是所有 gate 都能程序化。

比如要求：

```text
这段用户回复有没有真正解释清楚退款失败的原因？
```

可能没有一个简单的 deterministic function 可以判断。

这时可以使用 evaluator：

```text
Candidate
   │
   ▼
LLM Evaluator
   │
   ├─ pass
   │
   └─ feedback
```

但一旦进入“生成 → 评价 → 根据反馈重新生成”的循环，就开始接近后面的 **Evaluator–Optimizer** pattern。

因此可以把 Prompt Chaining 中的 gate 理解成一个边界：

```text
能确定验证
    ↓
programmatic gate

只能语义评价
    ↓
LLM evaluator

还需要根据评价反复改进
    ↓
Evaluator–Optimizer
```

Gate 的另一个价值，是缩小错误的传播距离。

假设一条五步 pipeline：

```text
S1 → S2 → S3 → S4 → S5
```

如果完全不检查中间状态，只在最后验证：

```text
S1 → S2 → S3 → S4 → S5 → FAIL
```

那么定位故障时，需要重新检查五个阶段。

如果每个高风险边界都有检查：

```text
S1
 ↓
G1
 ↓
S2
 ↓
S3
 ↓
G2
 ↓
S4
 ↓
S5
 ↓
G3
```

至少可以知道错误最晚在哪个区间出现。

这与普通软件 pipeline 并没有本质区别：

```text
parse
→ validate
→ transform
→ compile
→ test
```

LLM 只是其中部分 transformation 不再由确定性函数完成。

这种视角也能避免把 Prompt Chaining 神秘化。它可以写成非常普通的程序：

```python
def workflow(request: str) -> Result:
    spec = generate_spec(request)

    validate_spec(spec)

    plan = generate_plan(spec)

    validate_plan(plan)

    implementation = generate_implementation(plan)

    test_result = run_tests(implementation)

    if not test_result.passed:
        return Result(
            status="failed",
            stage="verification",
            details=test_result,
        )

    return Result(
        status="success",
        value=implementation,
    )
```

这里真正重要的是每个 stage 的 contract：

```text
输入是什么？
输出是什么？
失败如何表示？
什么条件允许进入下一步？
```

而不是用了哪个 Agent framework。

这也是 Prompt Chaining 最容易被低估的一点：它通过牺牲一部分 latency，把原本一次调用内部难以观察的过程拆成几个可以单独记录、单独测试、单独替换的组件。

### 2.3 Prompt Chaining 的边界：当下一步本身也无法提前写出来

Prompt Chaining 最舒服的任务通常具有这样的形状：

```text
我不知道每一步会生成什么内容，
但我知道总共有哪些步骤。
```

例如：

```text
generate outline
→ validate outline
→ write article
```

任务内容每次不同，但 pipeline 结构稳定。

另一个典型例子是：

```text
extract entities
→ normalize entities
→ query database
→ summarize results
```

只要业务合同没有改变，这几个阶段的顺序通常不会因为某次输入而突然变成：

```text
先生成图片
→ 再修改数据库
→ 再搜索 GitHub
```

因此 Chain 的优势来自一个很强的前提：

> **开发者能够在运行前写出有意义的任务分解。**

一旦这个前提不成立，继续增加 chain 就会越来越别扭。

比如处理一个 repository-level coding task：

```text
修复登录后偶发出现的 401，
补充测试，并确保 refresh token 行为没有回归。
```

我们可以强行设计一条固定链：

```text
1. 阅读 auth.py
2. 阅读 token.py
3. 修改 auth.py
4. 修改 token.py
5. 写 test_auth.py
6. 运行测试
```

问题是，在真正查看仓库以前，我们根本不知道：

```text
auth.py 存不存在？
问题是不是出在 middleware？
是否用了 Redis session？
refresh token 是否由另一个 service 管理？
现有测试文件叫什么？
是否根本不需要修改 token 逻辑？
```

这时固定 Chain 开始把未经验证的假设写进控制流。

为了补救，我们可能不断增加条件：

```python
if auth_file_exists:
    inspect_auth()

if middleware_detected:
    inspect_middleware()

if redis_detected:
    inspect_session_store()

if frontend_refresh_flow_detected:
    inspect_frontend()

if ...
```

最后得到：

```text
Prompt Chaining
+
大量 if / else
+
动态任务发现
+
动态工具选择
```

这已经说明问题不再是：

```text
怎样把固定步骤串起来？
```

而是：

```text
下一步到底应该做什么？
```

这就是 Prompt Chaining 的第一条边界。

可以把两类问题对比：

```text
Prompt Chaining

已知：
A → B → C → D

未知：
A/B/C/D 各自产生什么内容
```

对比：

```text
Dynamic orchestration

已知：
任务目标

未知：
要不要 A？
有没有 B？
C 应该出现几次？
D 是否取决于执行中的观察结果？
```

这时更合适的结构可能是 Orchestrator–Workers，甚至真正的 Agent loop。

Prompt Chaining 还有第二条边界：**错误可能被逐级放大。**

设：

$$
x_0
\xrightarrow{f_1}
x_1
\xrightarrow{f_2}
x_2
\xrightarrow{f_3}
x_3
$$

如果第一阶段误解了输入：

$$
x_1 \neq x_1^{*}
$$

后面的模型可能在错误状态上继续生成完全自洽的结果：

$$
f_3(f_2(x_1))
$$

即使 `f₂` 和 `f₃` 各自在局部上执行得很好，最终结果仍然可能偏离目标。

所以：

```text
更多步骤
≠
自动提高可靠性
```

如果每一步都有独立失败概率，而且错误不能被后续步骤发现，增加调用次数甚至增加了新的失败机会。

不能简单写成：

$$
P(\text{success}) = \prod_i p_i
$$

因为现实中的阶段错误通常并不独立，后续步骤也可能修复前面的偏差；但这个简化模型至少提醒我们：

> 把一次调用拆成五次，并不会凭空创造五倍可靠性。

Prompt Chaining 之所以可能提高结果质量，是因为它改变了任务难度和验证位置：

```text
一个很难的模型调用
```

变成：

```text
几个更窄的模型调用
+
可检查的中间状态
```

如果拆分以后每一步仍然模糊，而且没有 gate：

```text
模糊问题
→ 模糊输出
→ 模糊问题
→ 模糊输出
```

那么只是把一个难以调试的调用变成了多个难以调试的调用。

第三条边界是成本和 latency。

假设三个阶段顺序执行：

$$
T_{\text{chain}}
\approx
T_1 + T_2 + T_3 + T_{\text{validation}}
$$

因为 B 依赖 A，C 又依赖 B，它们通常无法像 Parallelization 那样直接同时启动。

Token 成本也至少包含：

$$
C_{\text{chain}}
=
C_1+C_2+C_3+\cdots
$$

而且后续阶段还可能需要重新携带部分前序上下文。

例如一次调用原本传：

```text
requirement
```

第二步可能需要：

```text
requirement
+
spec
```

第三步再需要：

```text
requirement
+
spec
+
plan
```

如果简单把全部历史原样累积：

$$
Context_n
=
\sum_{i=0}^{n-1} Output_i
$$

链条越长，context duplication 越明显。

因此实际设计时，更合理的做法通常是为阶段之间定义最小必要 contract：

```text
Stage A
输出 Spec

Stage B
只消费 Spec，
不必重新读取 Stage A 的完整 conversation

Stage C
消费 Plan + 必要的 Spec 字段，
而不是把前两轮所有自然语言重新塞进去
```

这和普通软件接口设计是同一个问题：

```text
不要把整个进程内存
当成函数参数。
```

Anthropic 当前的 Prompting 文档也给这类显式 Chain 一个更窄的定位：较新的 Claude 已经能够在一次调用内部完成很多多步推理，因此显式 chaining 尤其适合开发者需要检查中间输出或强制 pipeline structure 的场景。

这意味着在 2026 年写 Prompt Chaining，不应该再形成这样的默认规则：

```text
任务复杂
→ 拆成多个 Prompt
```

更适合问：

```text
这个任务是否有稳定的阶段边界？

中间产物是否能定义清楚？

中间产物是否值得单独验证？

后一步是否真的依赖前一步？

这些收益是否值得增加 latency 和 token cost？
```

如果答案大多是否定的，一次经过充分设计的调用可能更合适。

如果问题是：

```text
步骤已经知道，
只是每一步都需要单独完成并检查，
```

Prompt Chaining 提供了最简单的控制结构。

但如果问题变成：

```text
我们连应该走哪条已知流程都还不知道，
```

就需要改变的不是 Chain 里面的 Prompt，而是控制流本身。

下一节进入 **Routing**：不再固定唯一的下一步，而是在一组预先存在的处理路径之间做选择。

## 3. Routing——不是拆任务，而是选择哪条已经存在的路

Prompt Chaining 假设下一步已经确定：

```text
A → B → C
```

Routing 放开的第一个变量是：

```text
A 完成以后，
下一步究竟进入 B、C 还是 D？
```

因此它的基本结构不是链，而是条件分支：

```text
                         ┌─► Workflow A
                         │
Input ──► Router ────────┼─► Workflow B
                         │
                         └─► Workflow C
```

Anthropic 对 Routing 的定义是：先对输入进行分类，再把它导向一个更适合处理该类别的下游任务。这样可以把不同问题分开优化，而不必让同一个 Prompt、同一组工具或同一个模型兼顾所有输入。它尤其适用于能够划分为不同类别，而且这个分类本身可以被可靠完成的任务。

原文给出的客服例子很典型：

```text
Customer Request
        │
        ▼
      Router
     /   |    \
    /    |     \
General Refund Technical
  QA     Flow   Support
```

退款请求可能需要订单查询和退款工具，技术问题可能需要产品文档和诊断工具，而普通问答只需要知识库。如果把它们全部塞进一个大 Prompt：

```text
你是客服助手。

如果用户问普通问题……
如果用户想退款……
如果出现技术故障……
如果涉及账户……
如果……
```

不同任务的 instruction、tools 和 few-shot examples 会逐渐混在一起。对某一类别增加规则，还可能干扰其他类别。Routing 的做法不是继续扩大这个通用 Prompt，而是先回答一个更窄的问题：

```text
这个请求属于哪一种处理路径？
```

然后让每条路径维护自己的 contract。

这也是 Routing 与 Prompt Chaining 最直接的区别：

```text
Prompt Chaining:
下一步是什么已经知道，
需要生成的是下一步的内容。

Routing:
候选的下一步已经知道，
需要决定的是应该选哪一个。
```

这里的“候选路径已经知道”非常关键。它也是 Routing 与后面的 Orchestrator–Workers、Planner 最容易混淆的边界。

### 3.1 Router 负责选路，不负责现场发明路线

假设客服系统只允许三类处理：

```python
Route = Literal[
    "general_question",
    "refund_request",
    "technical_support",
]
```

Router 收到：

```text
我的耳机昨天升级固件以后，
左耳一直断连。
```

可能输出：

```json
{
  "route": "technical_support"
}
```

程序随后执行：

```python
route = classify(request)

match route:
    case "general_question":
        return answer_general_question(request)

    case "refund_request":
        return handle_refund(request)

    case "technical_support":
        return troubleshoot(request)
```

这里 LLM 确实做了一个控制流决策：

```text
technical_support
```

但它不能突然创造：

```text
send_engineer_to_customer_home
```

因为这条 route 根本不存在于系统定义中。

所以 Routing 的 contract 可以写成：

$$
r = f(x), \qquad r \in R
$$

其中：

* \(x\) 是输入；
* \(f\) 是 Router；
* \(R\) 是运行前已经定义好的有限候选集合。

例如：

$$
R =
\{
\text{refund},
\text{support},
\text{general}
\}
$$

真正重要的约束不是 Router 用不用 LLM，而是：

$$
R
$$

已经由开发者定义。

Router 甚至完全不需要 LLM。Anthropic 明确指出，分类可以由 LLM 完成，也可以使用传统分类模型或其他算法。

例如：

```python
def route(request: Request) -> str:
    if request.endpoint == "/refund":
        return "refund"

    if request.error_code is not None:
        return "technical_support"

    return classifier.predict(request.text)
```

如果现有 metadata 已经能可靠决定路径，没有必要为了“Agent 化”再调用一次模型。

---

这时需要把 **Router** 和 **Planner** 分开。

Router 面对的是：

```text
已有：

A
B
C

问题：

选哪个？
```

Planner 面对的可能是：

```text
只有 Goal

问题：

为了完成它，
究竟需要生成哪些 Steps？
```

可以画成：

```text
Routing

              ┌─► A
Input ─► R ───┼─► B
              └─► C

A/B/C 在部署系统以前已经存在
```

而 Planner / Orchestrator 更接近：

```text
Task
 │
 ▼
Planner
 │
 ├─► task_1
 ├─► task_2
 ├─► task_3
 └─► ...
```

这里的：

```text
task_1
task_2
task_3
```

可能直到看到具体任务以后才产生。

例如用户要求：

```text
给这个仓库增加 OAuth 登录。
```

如果系统只有：

```text
frontend
backend
database
```

三个固定 specialist，然后 Router 判断请求属于哪个 specialist，这仍然是 Routing。

但如果系统根据仓库内容发现：

```text
需要修改：
auth middleware
database schema
login page
session store
integration tests
documentation
```

然后动态创建六个子任务，这已经不是“从几个已有 route 中选一个”，而是后面要讨论的动态 decomposition。

因此：

```text
Router
≠
Planner
```

同样：

```text
Routing
≠
Task Decomposition
```

Routing 可以一次只选择一条路：

```text
Input
  ↓
Router
  ↓
Route B
```

也可以选择一个已有的组合：

```json
{
  "routes": [
    "security_review",
    "performance_review"
  ]
}
```

但如果候选工作本身是运行时根据任务内容生成的，就已经跨过了单纯 Routing 的边界。

这一区分在实现上也很有用。

Router 的输出通常应该尽量小：

```json
{
  "route": "technical_support",
  "confidence": 0.94
}
```

而不是要求 Router 同时输出：

```json
{
  "route": "technical_support",
  "root_cause": "...",
  "repair_plan": ["...", "..."],
  "user_response": "...",
  "tool_calls": ["...", "..."]
}
```

后一种设计把分类、规划、执行和回答重新混到一个调用里。此时出了问题，又很难判断：

```text
到底是 route 错了，
还是 plan 错了，
还是执行失败了？
```

Routing 的价值之一，就是让分类本身成为可以单独观察和评估的组件。

### 3.2 Routing 不只是“把问题分给不同 Agent”

Anthropic 给出的第二个例子并不是多 Agent，而是 **模型选择**：常见或简单的问题可以导向更便宜的小模型，困难或少见的问题使用能力更强的模型，以平衡效果和成本。

例如：

```text
                  ┌─► Small / Cheap Model
Request ─► Router─┤
                  └─► Strong Model
```

对应代码可能只是：

```python
route = classify_complexity(request)

if route == "simple":
    return call_small_model(request)

return call_strong_model(request)
```

这里没有出现多个自主 Agent。

Routing 改变的只是：

```text
这一次请求应该交给哪种 execution path。
```

沿着这个定义继续展开，工程里至少可以遇到几种 Routing 对象。

下面这四种是本文为了理解系统设计做的分类，不是 Anthropic 原文给出的正式 taxonomy。

#### Model Routing

```text
Request
  │
  ▼
Router
 ├─► cheap model
 ├─► reasoning model
 └─► long-context model
```

决策变量是：

```text
哪个模型来处理？
```

可以依据：

```text
task complexity
context length
latency requirement
cost budget
domain capability
```

例如：

```python
if task.tokens > LONG_CONTEXT_THRESHOLD:
    model = LONG_CONTEXT_MODEL
elif task.complexity == "low":
    model = FAST_MODEL
else:
    model = STRONG_MODEL
```

如果这些条件能直接计算，也没有必要调用 LLM Router。

---

#### Prompt Routing

仍然可以使用同一个模型，但为不同任务配置不同 system prompt：

```text
                ┌─► Coding Prompt ─────┐
Input ─► Router─┼─► Legal Prompt ──────┼─► Same Model
                └─► General Prompt ────┘
```

这允许每一类 Prompt 只维护与自己有关的 instruction 和 examples。

例如一个内部知识助手同时处理：

```text
HR policy
engineering docs
financial procedures
```

与其维护：

```text
一个包含所有业务规则的超级 Prompt
```

可以拆成：

```text
HR Prompt
Engineering Prompt
Finance Prompt
```

Router 负责选择。

---

#### Tool Routing

有些路径使用相同模型，但提供不同工具：

```text
                ┌─► Search Tools
Input ─► Router─┼─► SQL Tools
                └─► GitHub Tools
```

例如：

```text
“最近一周行业里有什么新闻？”
→ Web Search

“我们上季度退货率多少？”
→ Internal SQL

“这个函数上次是谁改的？”
→ Git Repository
```

如果所有工具始终暴露给模型：

```text
web_search
sql_query
github_search
send_email
calendar
crm
...
```

模型每一步都要在更大的工具集合中选择。

Routing 可以先缩小 action space：

```text
Request
 ↓
Domain Router
 ↓
Research Route
 ↓
只暴露 research tools
```

但这里也需要注意与 Agent Tool Selection 的区别。

如果程序先决定：

```text
这次属于 research workflow，
所以只加载 research tools
```

是 Routing。

如果 Agent 已经运行起来，每一步根据当前 observation 动态决定：

```text
下一步用 web_search，
还是 read_file，
还是 run_command？
```

这是 Agent loop 内部的 tool selection，不应该全部叫 Routing。

---

#### Workflow Routing

下游甚至可以是完整 workflow：

```text
                         ┌─► Refund Workflow
                         │     │
                         │     ├─ lookup order
Request ─► Router ───────┤     ├─ verify eligibility
                         │     └─ issue refund
                         │
                         └─► Support Workflow
                               │
                               ├─ retrieve docs
                               ├─ diagnose
                               └─ answer
```

因此 Router 的下游单位不一定是：

```text
Agent
```

它可以是：

```text
Prompt
Model
Tool Set
Function
Workflow
Agent
Human Queue
```

这也是为什么把 Routing 直接解释成：

> “一个 Agent 把问题转交给其他 Agent”

会把模式理解得太窄。

从控制流角度，更准确的表达是：

> Router 根据输入特征，在一组已经存在的 execution paths 中选择下一条路径。

至于那条路径内部是普通函数、一次 LLM Call、Prompt Chain，还是完整 Agent，并不是 Routing pattern 本身规定的。

---

这还带来一个很实用的组合方式：

```text
Request
   │
   ▼
Router
   │
   ├─ simple
   │     │
   │     ▼
   │  Single LLM
   │
   ├─ structured
   │     │
   │     ▼
   │ Prompt Chain
   │
   └─ open-ended
         │
         ▼
       Agent
```

Routing 因此也可以作为一种 **complexity gate**：

```text
不是所有请求
都进入最昂贵的执行路径。
```

这和 Anthropic 从简单方案开始、只有在收益值得时才增加 agentic complexity 的原则是一致的。Agentic system 通常用更多 latency 和 cost 换取任务表现，因此没有必要让所有输入无条件进入最复杂的架构。

### 3.3 Router 自己就是一个误差源，不能只测下游 Agent

Routing 解决了 separation of concerns，但也增加了一个新的 failure point：

```text
Input
  │
  ▼
Router
  │
  X
Wrong Route
```

如果一个退款请求被路由成普通 FAQ：

```text
Refund Request
      │
      ▼
    Router
      │
      ▼
 General QA
```

那么即使 General QA workflow 本身表现完美，也可能无法完成用户要求。

这与普通分类系统没有区别：

```text
downstream component
根本没有看到正确输入。
```

因此一个带 Routing 的系统至少有两层错误来源：

$$
\text{Failure}
=
\text{Routing Failure}
\cup
\text{Downstream Failure}
$$

这里的集合表达只表示失败来源，并不假设二者独立。

如果系统满足一个很强的条件：

```text
只要 route 错了，
下游一定无法恢复。
```

那么端到端任务成功率就受到 Router 正确率的上限约束：

$$
P(\text{task success})
\le
P(\text{correct route})
$$

现实系统通常没这么绝对。General workflow 也许能够识别：

```text
这看起来其实是 refund request
```

然后重新路由；Human fallback 也可能恢复错误，因此不能机械地把 Router accuracy 当成整个系统的 accuracy。

但这至少说明：

> **只评估每个 specialist，而不评估 Router，不足以评估整个 Routing workflow。**

---

最基本的 Router eval 可以先看 confusion matrix。

假设三个类别：

```text
refund
technical
general
```

测试结果可能是：

| Ground Truth \ Predicted | Refund | Technical | General |
| ------------------------ | -----: | --------: | ------: |
| Refund                   |     92 |         1 |       7 |
| Technical                |      2 |        96 |       2 |
| General                  |      5 |         4 |      91 |

单看：

```text
overall accuracy = 93%
```

可能还不够。

因为不同错误的业务代价可能不同：

```text
general → technical
```

最多浪费一次更昂贵的 workflow。

但：

```text
account compromise → general
```

可能意味着安全问题没有进入正确的 escalation path。

因此 Router 的类别设计通常需要考虑：

```text
不是所有 misrouting
都有相同 cost。
```

可以进一步定义成本矩阵：

$$
C_{ij}
=
\text{将真实类别 } i
\text{ 路由为 } j
\text{ 的代价}
$$

评价目标就不只剩：

$$
\text{Accuracy}
$$

还可以观察：

$$
\text{Expected Routing Cost}
=
\sum_{i,j}
P(i,j)C_{ij}
$$

这并不是 Anthropic 原文规定的 Routing 指标，而是普通分类问题自然带来的工程扩展。

---

第二个问题是 **unknown input**。

一个天真的 Router 往往被要求：

```text
你必须从 A、B、C 中选一个。
```

但真实输入可能根本不属于任何类别：

```text
A
B
C
都不合适
```

例如客服系统只有：

```text
refund
technical
general
```

突然收到：

```text
我怀疑账户被盗，
刚才出现了一笔我没有操作的付款。
```

如果强制三选一：

```text
argmax P(route | x)
```

哪怕所有类别的置信度都很低，系统最终仍然会输出一个“最像的错误答案”。

因此实际 Router 往往需要显式保留：

```text
unknown
fallback
human_review
```

例如：

```python
decision = router(request)

if decision.confidence < ROUTE_THRESHOLD:
    return escalate_to_fallback(request)

return dispatch(decision.route, request)
```

或者让输出 schema 本身支持：

```json
{
  "route": null,
  "reason": "No existing workflow covers suspected account compromise.",
  "action": "human_review"
}
```

这对应的是 **abstention**：

```text
Router 不只要学会选路，
还要允许自己说：
现有路线都不合适。
```

但需要注意，LLM 自报的：

```json
{
  "confidence": 0.97
}
```

并不天然等于经过校准的概率。

如果这个数真正承担生产决策，例如：

```text
confidence < 0.7
→ human review
```

就应该用真实 eval data 检查这个 threshold 的行为，而不是把模型输出的数字直接当成统计置信度。

---

第三个问题是 **taxonomy 本身可能设计错了**。

假设最开始定义：

```text
billing
technical
general
```

运行一段时间后发现 `billing` 里面其实混着：

```text
invoice question
refund request
payment failure
subscription cancellation
fraud report
```

这些任务：

```text
需要的工具不同
风险不同
响应流程不同
```

即使 Router 能 100% 正确地把它们都分类为：

```text
billing
```

下游仍然很难优化。

所以 Routing 的问题不只是：

```text
分类器准不准？
```

还包括：

```text
类别边界是否真的对应不同的处理方式？
```

一个有用的 route 通常应该满足：

```text
输入进入这个类别以后，
下游应该获得明显不同的：

Prompt
Tools
Model
Policy
Workflow
或 Escalation
```

如果两条 route 后面执行的是完全相同的逻辑：

```text
A → same_prompt
B → same_prompt
```

那么把它们拆成两个类别可能没有实际意义。

反过来，如果一个 route 内部不得不用几十个：

```python
if ...
elif ...
elif ...
```

处理完全不同的问题，则说明 route 可能过粗。

Routing 因此同时包含两个设计问题：

```text
1. Route Taxonomy
应该有哪些路？

2. Route Classifier
输入应该去哪条路？
```

第二个问题可以通过换模型、增加 examples 或训练 classifier 改善。

第一个问题通常需要重新观察真实任务分布和下游处理差异。

---

第四个问题是 distribution shift。

Router 可能在测试集上面对：

```text
refund
password reset
shipping delay
```

表现很好。

上线以后却逐渐出现：

```text
新的产品功能
新的错误码
新的政策
新的攻击方式
新的用户表达
```

原来的类别边界仍然存在，但输入分布已经发生变化。

因此除了：

```text
router accuracy
```

生产系统还可以记录：

```text
route distribution
unknown rate
fallback rate
human override rate
re-route rate
downstream failure by route
```

例如过去：

```text
technical_support = 18%
```

突然变成：

```text
technical_support = 61%
```

不一定说明 Router 出错，也可能真的发生了产品事故。

但它至少是值得调查的信号。

类似地，如果：

```text
fallback rate
2% → 25%
```

可能意味着出现了大量原 taxonomy 没覆盖的新输入。

---

最后，还要评估 **end-to-end task success**。

Router 分类正确，不代表用户任务完成。

例如：

```text
Request
   │
   ▼
Router
   │
   ▼
Refund Workflow     ← route 完全正确
   │
   ▼
Order lookup fails  ← 最终任务仍然失败
```

因此比较完整的观测链路应该保留：

```text
request_id
    │
    ├─ predicted_route
    ├─ route_confidence / score
    ├─ fallback?
    ├─ selected_workflow
    ├─ downstream_result
    └─ final_task_outcome
```

这样才能回答：

```text
用户任务失败时，
到底是：

Router 选错了？
Router 没有 fallback？
还是正确 workflow 自己失败了？
```

这也是为什么 Routing 虽然比自主 Agent 简单，仍然应该有自己的 evaluation contract。

---

把这一节收束成一个设计判断，可以写成：

```text
如果下一步已经唯一确定
→ 不需要 Router

如果存在一组已知路径，
而不同输入应该进入不同路径
→ Routing

如果连候选任务本身都要根据输入现场生成
→ 不再只是 Routing
```

因此 Routing 引入的是：

```text
选择的不确定性
```

而不是：

```text
任务分解的不确定性
```

接下来再放开另一个控制变量。

有些任务根本不需要在几条路之间二选一，因为：

```text
A 要做
B 也要做
C 也要做

而且它们彼此并不依赖。
```

这时继续串行执行只是浪费 wall-clock time。

下一节进入 **Parallelization**：什么时候应该把一条执行链拆成 fan-out，以及为什么“同时开多个 Agent”并不自动意味着真正可并行。

## 4. Parallelization——真正能并行的是独立性，不是多开几个 Agent

前两种 pattern 都还有一条明显的单线程控制流。

Prompt Chaining 是：

```text
A → B → C
```

Routing 虽然产生了分支，但单个请求通常只进入其中一条：

```text
      ┌→ B
A → R ┼→ C
      └→ D
```

Parallelization 改变的是另一个变量：

> 如果几个工作彼此不依赖，为什么一定要等前一个完成以后，再启动下一个？

最直接的结构是：

```text
              ┌─► Task A ─┐
              │           │
Input ────────┼─► Task B ─┼─► Aggregate
              │           │
              └─► Task C ─┘
```

Anthropic 把这种 workflow 分成两个不同的变体：

```text
Sectioning
把一个任务拆成彼此独立的子任务，并行执行。

Voting
对同一个任务执行多次，让多个结果共同参与最终判断。
```

两者在图上都像：

```text
fan-out
   ↓
并行执行
   ↓
fan-in
```

但解决的问题不同。

Sectioning 的目标通常是：

```text
这几件事情都要做，
而且没有必要互相等待。
```

Voting 则是：

```text
同一件事情不想只相信一次结果，
希望获得多个独立视角或尝试。
```

因此不能把 Parallelization 简化成：

```text
多开几个 Agent
```

真正需要先判断的是：

```text
这些调用之间究竟有没有数据依赖？
```

如果 B 必须读取 A 的输出：

```text
A → B
```

把 A 和 B 同时启动并不会得到更快的正确执行，只会让 B 缺少它应该消费的状态。

反过来，如果 A、B、C 都只依赖同一个输入：

```text
          ┌→ A
Input ────┼→ B
          └→ C
```

让它们排成：

```text
Input → A → B → C
```

才是在控制流里人为制造等待。

### 4.1 Sectioning：并行的前提是依赖关系允许，而不是任务名字不同

先看一个代码审查任务。

我们希望检查：

```text
correctness
security
performance
```

最简单的串行实现可以写成：

```text
Code
 ↓
Correctness Review
 ↓
Security Review
 ↓
Performance Review
 ↓
Summary
```

但如果 Security Review 并不需要读取 Correctness Review 的结论，Performance Review 也不需要等待前两者，那么这三个步骤之间不存在必要的数据依赖。

控制流更适合写成：

```text
                    ┌─► Correctness Review ─┐
                    │                       │
Code ───────────────┼─► Security Review ────┼─► Aggregate
                    │                       │
                    └─► Performance Review ─┘
```

把工作表示成依赖图会更清楚。

设：

```text
C = correctness review
S = security review
P = performance review
A = aggregation
```

依赖关系是：

$$
C \rightarrow A
$$

$$
S \rightarrow A
$$

$$
P \rightarrow A
$$

但不存在：

$$
C \rightarrow S
$$

也不存在：

$$
S \rightarrow P
$$

因此：

```text
C
S
P
```

可以同时进入 ready state，而：

```text
A
```

必须等待三者完成。

这本质上已经是一个很小的 DAG：

```text
      C ───┐
           │
      S ───┼──► A
           │
      P ───┘
```

所以判断 Sectioning 能否成立，比“能不能拆成三个 Agent”更准确的问题是：

> **这些节点之间的 dependency graph 是什么？**

如果两个任务分别满足：

$$
A = f_A(x)
$$

$$
B = f_B(x)
$$

二者都只依赖共同输入 \(x\)，而不需要：

$$
B = f_B(x, A)
$$

那么它们通常具备并行执行的基础。

这里也不需要要求数学意义上的完全独立。

例如两个 reviewer 都读取同一份代码：

```text
Reviewer A ─┐
            ├── shared input: repository snapshot
Reviewer B ─┘
```

它们显然共享输入，但不存在：

```text
Reviewer A 的输出
→ Reviewer B 才能开始
```

控制流上仍然可以并行。

---

Anthropic 给 Sectioning 的一个例子是 guardrail：

```text
                         ┌─► Generate Response
User Request ────────────┤
                         └─► Safety Check
```

与其让一次调用同时完成：

```text
理解请求
生成回答
检查安全性
```

可以把关注点拆开。

另一个例子是自动化 eval：

```text
                      ┌─► Correctness Judge
Model Output ─────────┼─► Style Judge
                      ├─► Citation Judge
                      └─► Safety Judge
```

每个 evaluator 只处理一个评价维度，然后程序汇总结果。

这里的收益不只来自并行。

还有一个容易忽略的变化：

```text
一个 Prompt 同时关注四件事
```

被改成了：

```text
四个 Prompt
每个只关注一件事
```

因此即使最后由于 rate limit 或资源约束没有真正同时执行，Sectioning 仍可能通过 **attention separation** 改善任务表现。

也就是说，需要区分两个效果：

```text
Task Decomposition
减少每次调用需要同时处理的关注点

Execution Parallelism
减少互不依赖任务之间的等待
```

二者经常一起出现，但不是同一个概念。

---

对于 coding task，另一个典型例子是：

```text
任务：
准备一次版本发布
```

假设已经确定需要：

```text
生成 changelog
检查依赖漏洞
运行 documentation link check
分析 bundle size
```

如果四项都只消费同一个 commit：

```text
commit SHA
```

可以得到：

```text
                         ┌─► changelog
                         │
Commit Snapshot ─────────┼─► dependency audit
                         │
                         ├─► docs check
                         │
                         └─► bundle analysis
                                  │
                                  ▼
                             release report
```

但如果流程是：

```text
修改代码
→ build
→ 分析 build artifact
```

那么：

```text
build
```

必须等待修改完成，

```text
bundle analysis
```

又必须等待 build artifact 出现。

不能因为：

```text
edit
build
analyze
```

看起来是三个不同 task，就把三者并行。

因此一个实际 orchestration runtime 判断 task 是否 ready，通常更接近：

```python
def ready(task, completed):
    return all(
        dep in completed
        for dep in task.dependencies
    )
```

而不是：

```python
spawn_everything(tasks)
```

如果任务关系是：

```text
A ─────► C ─────► E
│
└──────► D ─────► E

B ──────────────► E
```

第一次能够同时运行的是：

```text
A
B
```

A 完成以后：

```text
C
D
```

可以同时运行。

最后：

```text
E
```

等待 B、C、D 全部完成。

因此更准确的执行过程是：

```text
Wave 1:
A || B

Wave 2:
C || D

Wave 3:
E
```

这里已经能看到 Parallelization 和后面 Symphony 这类 orchestration runtime 的联系：当任务数量增大以后，需要管理的不是“并发按钮”，而是：

```text
dependency
ready state
running state
completion
failure
retry
resource conflict
```

本文暂时只讨论 pattern，不在这里展开 task scheduler。

---

还有一个比数据依赖更麻烦的问题：**副作用冲突**。

假设两个 worker 都能够修改同一个文件：

```text
Worker A
  │
  ▼
config.yaml

Worker B
  │
  ▼
config.yaml
```

即使它们的推理过程彼此不需要对方输出，也不意味着可以安全并行。

可能出现：

```text
A read config v1
B read config v1

A writes config v2
B writes config v3
```

最终：

```text
A 的修改被 B 覆盖
```

因此并行安全不仅要求：

```text
没有 read-after-write dependency
```

还可能要求考虑：

```text
write/write conflict
shared workspace
shared database state
rate limit
global resource
tool side effects
```

例如：

```text
Task A:
修改 auth.ts

Task B:
修改 README.md
```

通常比：

```text
Task A:
重构 auth.ts

Task B:
给 auth.ts 添加日志
```

更容易安全并行。

所以对于有副作用的 worker，需要额外问：

```text
它们读什么？
它们写什么？
写入范围会不会重叠？
失败后能否回滚？
结果最终怎样 merge？
```

这也是“并行 Agent”从 Demo 走向真实工程时经常遇到的问题。

逻辑上的 independent subtasks：

```text
≠
```

执行环境里的 conflict-free subtasks。

### 4.2 Voting：多次运行同一个任务，不意味着最后做多数表决

Parallelization 的第二种形式是 Voting。

这里不是：

```text
任务 A
任务 B
任务 C
```

而是：

```text
同一个任务
 ↓
Run 1

同一个任务
 ↓
Run 2

同一个任务
 ↓
Run 3
```

并行执行以后：

```text
            ┌─► Attempt 1 ─┐
            │              │
Input ──────┼─► Attempt 2 ─┼─► Aggregate
            │              │
            └─► Attempt 3 ─┘
```

Anthropic 给出的例子之一是代码安全审查：用多个 Prompt 或多次调用检查同一段代码，如果不同 reviewer 能发现不同问题，就可以扩大覆盖面。

例如：

```text
Input:
payment_callback.py
```

三个 reviewer 得到：

```text
Reviewer A:
发现 callback signature 没有验证。

Reviewer B:
发现 transaction lookup 存在 IDOR 风险。

Reviewer C:
没有发现高风险漏洞。
```

这里如果机械采用：

```text
多数票
```

结果是：

```text
A: signature vulnerability
B: IDOR
C: none
```

没有任何漏洞获得：

```text
2 / 3
```

多数支持。

最终可能得到：

```text
No issue
```

这显然不是代码安全场景里想要的聚合逻辑。

因此 Anthropic 把这种变体称为 Voting，并不意味着：

```text
aggregate = majority_vote(outputs)
```

一定是正确实现。

更一般的结构是：

$$
y_1, y_2, \dots, y_n
=
f(x)
$$

然后定义：

$$
y^{*} =
g(y_1,y_2,\dots,y_n)
$$

真正需要设计的是：

$$
g
$$

也就是 aggregation policy。

---

对于不同任务，合适的聚合方式可能完全不同。

#### Union

安全审查可以选择：

```text
只要任意 reviewer 找到一个问题，
都把它进入后续验证。
```

形式上更接近：

$$
F =
F_1 \cup F_2 \cup \dots \cup F_n
$$

例如：

```text
A → {SQL injection}
B → {IDOR}
C → {}
```

得到：

```text
{SQL injection, IDOR}
```

然后再对这些候选漏洞逐个 verifier。

这种策略倾向于提高 recall，但可能增加 false positive。

---

#### Majority Vote

如果任务有一个离散答案：

```text
A / B / C / D
```

多次独立尝试得到：

```text
A
A
C
A
C
```

可以用：

$$
\hat y
=
\operatorname{mode}(y_1,\dots,y_n)
$$

得到：

```text
A
```

这种方式更接近通常理解的 self-consistency / majority voting。

但它依赖一个条件：

```text
多个 attempt 的错误不能高度相关。
```

如果所有调用都使用：

```text
相同模型
相同 Prompt
相同错误假设
```

那么运行五次可能只是稳定地重复同一种错误。

因此：

```text
n 个结果
```

不等于：

```text
n 份独立证据。
```

---

#### Weighted Vote

如果 reviewer 的能力或任务适配性不同，可以使用：

$$
score(c)
=
\sum_i w_i \cdot I(y_i=c)
$$

其中：

```text
w_i
```

表示不同 evaluator 的权重。

比如：

```text
general reviewer        weight = 1
security specialist     weight = 2
domain verifier         weight = 3
```

但这些权重也需要 eval 支持，而不是根据角色名字主观指定。

---

#### Judge / Ranker

还可以把几个候选答案交给另一个模型：

```text
              ┌─ Candidate A ─┐
              │               │
Input ────────┼─ Candidate B ─┼─► Judge ─► Best
              │               │
              └─ Candidate C ─┘
```

此时 aggregate 本身又成为一次模型调用。

例如：

```text
Attempt A:
solution_a.py

Attempt B:
solution_b.py

Attempt C:
solution_c.py

Judge:
结合测试结果和实现复杂度选择最终方案
```

这可以利用 richer comparison，但同时增加新的错误源：

```text
candidate generation error
+
judge error
```

如果存在确定性 verifier，则应优先利用真实环境反馈。

例如代码方案可以先：

```text
run tests
type check
benchmark
```

再让 Judge 在通过硬约束的候选中比较。

---

#### Threshold

对于 moderation 这类任务，可能使用：

```text
至少 k 个 reviewer 判定违规
→ block
```

即：

$$
\sum_i I(y_i=\text{unsafe}) \ge k
$$

阈值 \(k\) 的选择对应不同的 false positive / false negative trade-off。

例如：

```text
k = 1
```

很敏感，只要有一个 reviewer 报警就拦截。

```text
k = n
```

则非常保守，必须全部 reviewer 同意才拦截。

所以 Voting 的设计问题并不是：

> “要不要三个 Agent 投票？”

而是：

```text
为什么需要多个样本？

希望提高 recall 还是 precision？

不同输出是否足够独立？

最终 aggregate function 是什么？

出现 disagreement 时怎么办？
```

---

Voting 还有一个常见误区：把“角色不同”直接当成“信息独立”。

例如：

```text
Agent A:
你是乐观主义者。

Agent B:
你是悲观主义者。

Agent C:
你是资深专家。
```

如果三者：

```text
读取相同输入
使用相同模型
依赖相同事实
缺少外部验证
```

这些角色 Prompt 可能产生一定行为差异，但不能自动证明：

```text
三个输出 = 三个独立专家意见
```

尤其当三者共同缺少同一条事实时：

```text
Missing Evidence
       │
       ├─► Agent A 猜错
       ├─► Agent B 猜错
       └─► Agent C 猜错
```

Voting 无法通过增加采样次数补回根本不存在的证据。

因此 Voting 更适合处理：

```text
model variance
different perspectives
search diversity
candidate diversity
```

而不是替代：

```text
ground truth
tool verification
test execution
source retrieval
```

在代码场景里：

```text
5 个 reviewer 都觉得代码没问题
```

仍然不如：

```text
实际跑一次 failing test
```

提供的环境反馈直接。

### 4.3 并行降低的主要是等待时间，不会自动降低 token 成本

Parallelization 最直观的工程收益是 wall-clock latency。

假设有三个独立任务：

$$
T_A = 8s
$$

$$
T_B = 10s
$$

$$
T_C = 6s
$$

如果串行：

$$
T_{\text{seq}}
\approx
T_A+T_B+T_C
$$

那么：

$$
T_{\text{seq}}
\approx24s
$$

如果能够理想并行：

$$
T_{\text{parallel}}
\approx
\max(T_A,T_B,T_C)
$$

那么：

$$
T_{\text{parallel}}
\approx10s
$$

现实系统还会有：

```text
dispatch overhead
queue
rate limit
network latency
aggregation
straggler
```

所以更接近：

$$
T_{\text{parallel}}
\approx
\max(T_A,T_B,T_C)
+
T_{\text{overhead}}
+
T_{\text{aggregate}}
$$

但只要任务耗时显著大于调度开销，仍可能明显缩短用户实际等待时间。

---

Token cost 却不是同一个关系。

三个任务串行时：

$$
C_{\text{seq}}
=
C_A+C_B+C_C
$$

并行以后仍然大致是：

$$
C_{\text{parallel}}
=
C_A+C_B+C_C
$$

如果还需要一次 aggregator：

$$
C_{\text{parallel}}
=
C_A+C_B+C_C+C_{\text{agg}}
$$

所以 Parallelization 通常改变的是：

```text
什么时候支付这些计算
```

而不是：

```text
这些计算是否需要支付。
```

甚至 Voting 明确是在增加 test-time compute。

例如：

```text
1 attempt
```

改成：

```text
8 attempts
```

假设每次调用平均 token 成本为 \(C\)，忽略 caching 和 aggregation：

$$
C_{\text{vote}}
\approx 8C
$$

latency 可以由于同时执行接近一次调用，但 token consumption 并不会因此变成：

$$
C
$$

因此必须区分：

```text
wall-clock latency
compute / token cost
```

这两个指标经常被“并行更快”一句话混在一起。

---

并行还有第三个约束：**并发容量不是无限的**。

假设一次 fan-out：

```text
1 request
→ 100 workers
```

理论上可以把 100 个任务同时运行。

现实中可能受到：

```text
API concurrency limit
rate limit
GPU capacity
tool quota
database connection pool
browser instances
sandbox capacity
```

约束。

于是执行器真正采用的可能不是：

```text
100-way parallel
```

而是：

```text
worker pool = 10
```

运行：

```text
Wave 1: 10 tasks
Wave 2: 10 tasks
...
Wave 10: 10 tasks
```

代码形态可能类似：

```python
async def run_parallel(tasks, limit=10):
    semaphore = asyncio.Semaphore(limit)

    async def run(task):
        async with semaphore:
            return await execute(task)

    return await asyncio.gather(
        *(run(task) for task in tasks)
    )
```

此时 pattern 仍然属于 Parallelization，只是 runtime 对实际并发量做了限制。

---

还需要考虑 straggler。

假设：

```text
Worker A:  5 s
Worker B:  6 s
Worker C: 48 s
```

如果最终 aggregation 必须等待所有结果：

$$
T_{\text{total}}
\approx48s
$$

而不是：

$$
(5+6+48)/3
$$

所以 fan-out 越大，越容易遇到：

```text
大多数 worker 已经完成，
但整个 workflow 仍在等最后一个。
```

这时系统需要明确：

```text
所有结果都必须回来吗？
是否允许 timeout？
partial result 能不能 aggregate？
失败 worker 要不要 retry？
什么时候放弃 slow worker？
```

例如搜索场景可能允许：

```text
10 个搜索 worker
7 个返回高质量来源
3 个超时
```

仍然继续 synthesis。

但财务核对任务可能要求：

```text
所有账户分片必须完成
```

否则不能生成最终结果。

因此：

```text
fan-in condition
```

也是 Parallelization contract 的一部分。

---

另一个成本来源是重复 context。

假设 20 个 worker 都读取：

```text
50k-token repository context
```

简单复制：

$$
20 \times 50k
$$

会让输入成本迅速增长。

因此并行拆分最好同时考虑 context partition：

```text
Worker A
只读取 auth/

Worker B
只读取 payment/

Worker C
只读取 tests/
```

如果每个 worker 都获得完整 context：

```text
Parallelization
```

可能把：

```text
执行时间
```

降低了，却把：

```text
context duplication
```

放大。

这也是后面 Orchestrator–Workers 更难的地方：如果 worker task 是运行时生成的，就不仅要决定：

```text
做什么？
```

还需要决定：

```text
每个 worker 应该拿到什么上下文？
```

---

最后再看一个容易误判成 Parallelization 的场景。

假设任务是：

```text
修复一个登录 bug。
```

我们直接启动：

```text
Agent A:
检查 backend

Agent B:
检查 frontend

Agent C:
检查 database

Agent D:
检查 tests
```

看上去符合：

```text
fan-out
```

但这套分解隐含了一个假设：

```text
每次登录 bug
都应该拆成这四部分。
```

如果这四个子任务是程序预先定义好的：

```text
backend
frontend
database
tests
```

这是 Parallelization。

如果面对另一个 bug，中央模型先读任务和仓库，然后临时判断：

```text
这次需要：
1. middleware investigator
2. Redis session investigator
3. integration-test worker

不需要 frontend worker
也不需要 database worker
```

这时任务集合：

$$
\{W_1,W_2,\dots,W_n\}
$$

已经不是 deployment time 固定，而是 runtime 生成。

控制流从：

```text
预定义 fan-out
```

变成了：

```text
动态 decomposition
→ fan-out
→ synthesis
```

这就是 Anthropic 区分 Parallelization 与 Orchestrator–Workers 的关键边界：

```text
Parallelization

要做哪些 subtasks
运行前已经知道。
```

```text
Orchestrator–Workers

连 subtasks 本身
都要根据当前输入临时决定。
```

所以这一节最后可以留下一个简单判断：

```text
步骤有依赖
→ Prompt Chaining

从多个已有路径中选一条
→ Routing

多个已知子任务都要执行，
且彼此没有必要的数据依赖
→ Parallelization / Sectioning

同一任务希望获得多个独立尝试
→ Parallelization / Voting

连需要哪些子任务都无法提前确定
→ Orchestrator–Workers
```

Parallelization 并没有让 workflow 获得更大的自主性。

它只是利用了一个已经存在的结构事实：

> **有些工作之间不存在必须等待的依赖关系。**

下一节才会放开任务分解本身：开发者不再提前写死 `A / B / C`，而是让一个 Orchestrator 根据当前输入决定应该创建哪些 worker，以及如何把结果重新合并。

## 5. Orchestrator–Workers——当子任务无法在运行前写死

上一节的 Parallelization 已经允许：

```text
             ┌─► Worker A ─┐
             │             │
Input ───────┼─► Worker B ─┼─► Aggregate
             │             │
             └─► Worker C ─┘
```

现在把图稍微改一下：

```text
                      ┌─► Worker 1 ─┐
                      │             │
Input ─► Orchestrator ┼─► Worker 2 ─┼─► Synthesis
                      │             │
                      ├─► ...       │
                      │             │
                      └─► Worker N ─┘
```

两张图拓扑上很接近，都可能出现 fan-out、并行执行和 fan-in。真正的区别不在有没有中央节点，也不在 worker 数量，而在：

> **这些 worker 要做什么，是部署 workflow 时就已经写好的，还是看到这一次具体输入以后才知道？**

Anthropic 把后一种模式称为 **Orchestrator–Workers**：中央 LLM 根据输入动态拆解任务，把生成出来的子任务交给 worker LLM，最后再综合 worker 的结果。

因此 Parallelization 更像：

```text
运行前：

tasks = [
    correctness_review,
    security_review,
    performance_review,
]
```

而 Orchestrator–Workers 更像：

```text
运行前：

tasks = ???

运行时：

tasks = orchestrator.decompose(current_request)
```

假设收到一个 repository-level coding request：

```text
修复用户刷新 access token 后偶发出现的 401，
补充 regression test，
不要改变现有 session API。
```

程序在读取仓库之前并不知道：

```text
要改几个文件？
问题发生在哪一层？
要不要改数据库？
有没有 Redis？
前端是否参与 refresh？
测试应该落在哪个目录？
```

一次具体运行可能得到：

```text
Worker 1:
检查 refresh token middleware

Worker 2:
检查 Redis session / token rotation

Worker 3:
检查现有 integration tests
```

另一个看起来相似的登录问题，Orchestrator 可能只生成：

```text
Worker 1:
检查前端重复 refresh request 的 race condition
```

子任务集合不是：

$$
\{A,B,C\}
$$

提前固化，而更接近：

$$
T(x)
=
\{t_1,t_2,\ldots,t_n\}
$$

其中任务集合 \(T\) 本身就是输入 \(x\) 的函数。

这一步把新的不确定性交给了模型：

```text
Prompt Chaining
→ 每一步内容不确定

Routing
→ 从已有路径里选哪条不确定

Parallelization
→ 每个已知分支会得到什么结果不确定

Orchestrator–Workers
→ 连这次到底需要哪些子任务都不确定
```

但这里仍然要保留 Macro 1 里的边界：Anthropic 把 Orchestrator–Workers 放在 **workflow**，而不是后面的 autonomous agent。

原因是高层协议仍然可以由程序提前规定：

```text
receive task
    ↓
orchestrator decomposes
    ↓
dispatch workers
    ↓
collect worker results
    ↓
synthesize
    ↓
return
```

动态的是具体 decomposition，不代表模型可以任意重写整个 runtime protocol。

### 5.1 它和 Parallelization 长得很像，差别在任务集合是谁生成的

先把两个模式放在一起。

Parallelization：

```text
Deployment time

tasks = {
    A,
    B,
    C
}

Runtime

        ┌─► A ─┐
Input ──┼─► B ─┼─► Aggregate
        └─► C ─┘
```

Orchestrator–Workers：

```text
Deployment time

task schema = known
actual tasks = unknown

Runtime

Input
  │
  ▼
Orchestrator
  │
  ├─► generates task_1
  ├─► generates task_2
  └─► generates task_n
          │
          ▼
       Workers
          │
          ▼
      Synthesis
```

这一区分看起来简单，实现时却很容易混掉。

例如我们做一个代码审查 workflow，永远启动：

```text
security reviewer
performance reviewer
correctness reviewer
```

即使三个 reviewer 都是独立的 LLM，仍然属于 Parallelization。

如果中央模型先阅读 issue：

```text
修复上传大文件时的内存峰值问题。
```

然后根据仓库结构生成：

```text
1. tracing worker
   找出文件读取和 buffering 路径

2. API worker
   检查 upload handler 是否一次性读入内存

3. storage worker
   检查 object-store client 是否支持 streaming

4. benchmark worker
   找出现有内存 benchmark 和复现方式
```

这里才出现了动态 decomposition。

因此：

```text
很多 Worker
≠
Orchestrator–Workers
```

需要出现的是：

```text
Task
  ↓
LLM-based decomposition
  ↓
Runtime-generated subtasks
```

---

这还意味着 Orchestrator 的输出不应该只是自然语言里的：

```text
“你去看看后端，
你去看看前端，
大家一起努力。”
```

如果这些子任务要进入真正的 runtime，最好至少形成可以执行和追踪的 task contract。例如：

```json
{
  "id": "task-2",
  "goal": "Inspect refresh-token rotation and Redis session state",
  "scope": [
    "src/auth/",
    "src/session/"
  ],
  "depends_on": [],
  "expected_output": {
    "type": "investigation_report"
  }
}
```

它未必需要使用这套字段，但至少应该能够回答：

```text
这个 worker 为什么存在？
它负责什么？
边界在哪里？
依赖谁？
需要拿到什么 context？
完成后交回什么？
```

否则动态 decomposition 很容易退化成多个模型同时“研究一下”。

例如中央 Orchestrator 发出：

```text
Worker A:
分析这个 bug。

Worker B:
也分析一下这个 bug。

Worker C:
从另一个角度分析这个 bug。
```

得到三个高度重叠的结果：

```text
A → auth middleware
B → auth middleware
C → auth middleware
```

系统只是为同一份工作支付了三次 token。

相比之下：

```text
Worker A
负责复现和 trace

Worker B
负责 refresh-token implementation

Worker C
负责 session persistence

Worker D
负责 regression tests
```

至少形成了可观察的 responsibility boundary。

动态分解因此需要解决两件事：

```text
Coverage
任务有没有被漏掉？

Overlap
不同 worker 有没有在重复做同一件事？
```

只追求：

```text
多拆几个 task
```

并不会自动改善任何一个指标。

---

还有一个容易混淆的地方：**动态分解之后，并不意味着所有 worker 都应该立刻并行。**

Orchestrator 可能生成：

```text
Task A:
找到 refresh-token bug 的 root cause

Task B:
根据 root cause 修改实现

Task C:
根据修改补 regression test
```

这里虽然：

```text
A
B
C
```

都是运行时生成的，依赖关系却是：

```text
A → B → C
```

如果同时启动：

```text
A || B || C
```

B 和 C 只能在缺少关键事实时猜测。

另一次 decomposition 可能得到：

```text
A:
检查 backend token rotation

B:
检查 frontend refresh deduplication

C:
检查 Redis session expiry
```

这三个 investigation task 都依赖同一个 issue 和 repository snapshot：

```text
        ┌─► A
Input ──┼─► B
        └─► C
```

才适合并行。

所以 Orchestrator 实际产生的最好不是一个无结构列表：

```text
[t1, t2, t3, t4]
```

而是包含依赖关系的任务图：

```text
t1 ────────┐
            ├──► t4
t2 ────────┤
            │
t3 ────────┘
```

动态 decomposition 和 Parallelization 因此是两个不同维度：

```text
谁产生 subtasks？
        ↓
Orchestrator–Workers

这些 subtasks 哪些能够同时执行？
        ↓
Parallelization / scheduler
```

一个 Orchestrator–Workers workflow 可以：

```text
动态生成任务
+
串行执行
```

也可以：

```text
动态生成任务
+
部分并行
+
部分依赖执行
```

这也是后面真正进入 orchestration runtime 后必须管理 dependency DAG 的原因。

### 5.2 Coding 和 Search 为什么经常落到这个模式

Anthropic 给 Orchestrator–Workers 的两个主要例子就是 **复杂、多文件的 coding change** 和 **需要从多个来源收集、分析信息的 search task**。原因并不是 coding 和 search 天然需要 Multi-Agent，而是这两类任务经常具有同一个结构特征：

> **在真正观察环境以前，无法可靠预测需要哪些子任务。**

先看 coding。

用户给出的通常是目标：

```text
升级项目里的鉴权逻辑，
支持 refresh-token rotation，
并保证已有客户端不受影响。
```

但真正的修改范围由仓库决定，而不是由 prompt 决定。

一个仓库可能是：

```text
app/
├── auth.py
├── models.py
└── tests/
```

另一个仓库可能是：

```text
services/
├── gateway/
├── identity/
├── session/
└── audit/

web/
└── auth/

packages/
└── shared-token/

integration/
└── auth/
```

同一句需求：

```text
支持 refresh-token rotation
```

在两个项目里对应的 task graph 完全可能不同。

如果强行提前规定：

```text
1. 修改 auth.py
2. 修改 token.py
3. 修改 test_auth.py
```

其实是在 workflow 里编码对仓库结构的猜测。

Orchestrator 可以先获得环境信息：

```text
Issue
+
Repository tree
+
Search results
+
Relevant code
```

再产生：

```text
Task 1
修改 identity service 的 rotation logic

Task 2
检查 gateway 是否缓存旧 token

Task 3
更新 shared token schema

Task 4
增加跨 service integration test
```

这就是 Anthropic 所说的：

```text
number of files
+
nature of changes
```

取决于具体 task。

---

Search 也有相同问题。

假设问题是：

```text
为什么某个模型在最近一次 benchmark 更新后排名明显变化？
```

在开始搜索前，我们不知道最终需要：

```text
官方 benchmark changelog？
模型 release note？
evaluation methodology？
issue discussion？
复现实验？
第三方分析？
```

一次初始搜索可能发现：

```text
benchmark 在 8 月修改了 scoring rule
```

于是新的子任务才出现：

```text
Worker A
确认 scoring rule 修改内容

Worker B
找修改前后的 leaderboard snapshot

Worker C
检查目标模型受影响的是哪些 category
```

Worker B 又可能发现：

```text
旧 leaderboard 不是同一模型版本
```

于是需要继续：

```text
Worker D
核对 model version / release date
```

任务分解是随着 evidence 到来逐渐具体化的。

这也是为什么搜索任务不能简单理解成：

```text
Google
+
三个搜索 Agent
+
总结
```

真正动态的是：

```text
我们目前缺少什么证据？
哪条支线值得继续追？
哪些问题已经可以停止？
```

如果搜索问题始终固定为：

```text
查官网
查论文
查 GitHub
```

三个来源并行跑，然后汇总，这仍然更像 Parallelization。

只有当具体 evidence 决定后续还需要什么搜索任务时，才开始进入动态 orchestration。

---

Coding 和 Search 还有一个共同特点：worker 可以从环境拿到相对明确的 observation。

Coding worker 可以获得：

```text
file contents
grep results
compiler output
test results
git diff
```

Search worker可以获得：

```text
source
publication date
quoted claim
search result
contradictory evidence
```

所以 worker 不只是：

```text
根据 prompt 自己想
```

而能够返回：

```text
我检查了什么
→ 我观察到了什么
→ 这对父任务意味着什么
```

例如 coding worker 的结果可以是：

```json
{
  "task_id": "investigate-session",
  "status": "completed",
  "findings": [
    {
      "file": "src/session/store.ts",
      "claim": "Refresh rotates the token but does not update the cached session key."
    }
  ],
  "recommended_next_steps": [
    "Add regression coverage for a second refresh using the rotated token."
  ]
}
```

这比：

```text
“我觉得可能是 session 的问题。”
```

更适合作为上游 Orchestrator 的输入。

Search worker 同理，最好返回：

```text
claim
source
evidence
uncertainty
```

而不是一整段无法追踪来源的总结。

也就是说，Orchestrator–Workers 的质量不仅取决于：

```text
Orchestrator 会不会拆任务
```

还取决于：

```text
Worker 能不能产出可合并的 artifact
```

没有 output contract，最后的 synthesis 会面对一堆风格、粒度、证据标准都不同的自然语言结果。

### 5.3 动态分解把灵活性带进来了，也把新的失败面一起带进来了

固定 workflow 的一个优势是，我们提前知道：

```text
A → B → C
```

所以至少能够检查：

```text
A 有没有执行？
B 有没有拿到 A？
C 有没有成功？
```

Orchestrator–Workers 把任务集合也变成运行时状态以后，需要观察的对象明显增加。

最常见的第一类问题是 **重复工作**。

例如：

```text
Worker A:
调查 auth middleware

Worker B:
调查 login middleware

Worker C:
调查 token middleware
```

三个任务最后都打开：

```text
src/middleware/auth.ts
```

并得出几乎相同的结论。

这可能来自：

```text
任务边界描述太模糊
Orchestrator 没看到已有任务
worker context 太宽
缺少 ownership
```

如果 worker 很昂贵，重复工作不是文字上的“不优雅”，而是直接形成额外：

```text
token
latency
tool execution
workspace contention
```

因此 Orchestrator 至少需要知道当前已经存在什么 work item。

---

第二类是 **dependency violation**。

比如：

```text
Task A
确定数据库 migration 方案

Task B
按照 migration 方案修改 ORM model
```

如果 B 在 A 完成之前启动，它可能自己假设一个 schema。

A 最后选择：

```text
column: expires_at
```

B 却实现：

```text
column: expiration_time
```

两个 worker 各自在自己的局部上下文里都“完成”了任务，但组合以后不一致。

所以动态任务也要携带：

```text
depends_on
```

以及：

```text
blocked
ready
running
completed
failed
```

这已经不只是 prompt engineering，而进入普通 scheduler / workflow engine 熟悉的状态管理问题。

---

第三类是 **workspace conflict**。

假设：

```text
Worker A
修改 src/auth.ts

Worker B
也修改 src/auth.ts
```

即使两者逻辑任务不同：

```text
A:
修 token refresh

B:
增加 audit logging
```

共享 workspace 下仍可能：

```text
A read v1
B read v1

A write v2
B write v3
```

最终必须处理 merge conflict，甚至出现 silent overwrite。

因此多 worker coding system 往往还要回答：

```text
Worker 是否共享 working tree？

每个任务是否拥有独立 workspace？

谁负责 merge？

冲突以后重新执行谁？

Worker 是否看到其他任务刚产生的 diff？
```

这些问题已经开始越过“Orchestrator–Workers 这个 pattern 是什么”，进入后面 Symphony 这类 runtime 设计真正要处理的内容。

---

第四类是 **context duplication**。

一个天真实现可能把完整 repository context：

```text
100k tokens
```

复制给：

```text
10 workers
```

仅输入上下文就可能出现近似：

$$
10 \times 100k
$$

的重复。

而 worker 实际只需要：

```text
Task A → auth/
Task B → session/
Task C → tests/
```

这就要求 decomposition 同时承担一部分 context allocation：

```text
Task
+
Relevant Context
```

而不是：

```text
Task
+
Everything We Know
```

当然，context 太窄也会产生另一种错误：

```text
Worker 看不到真正的跨模块依赖。
```

所以需要在：

```text
context isolation
```

与：

```text
cross-task information
```

之间做权衡。

---

第五类是 **worker failure**。

如果：

```text
8 workers
```

其中：

```text
7 completed
1 failed
```

Orchestrator 必须知道：

```text
最终还能 synthesis 吗？
失败任务是不是关键依赖？
要不要 retry？
retry 是否需要换策略？
是否应该重新分解任务？
```

对于搜索：

```text
一个来源搜索失败
```

可能允许继续。

对于：

```text
数据库 schema migration review
```

失败可能意味着整个 implementation 不能继续。

所以：

```text
worker failed
```

不能只有一个统一处理策略。

任务 contract 还需要描述：

```text
critical?
retryable?
optional?
```

至少 runtime 必须拥有等价的信息。

---

第六类是 **partial result**。

Worker 不一定只有：

```text
success
failure
```

两种状态。

例如搜索 worker 可能返回：

```text
找到两条可信来源，
但没有找到 2025 年以前的 leaderboard snapshot。
```

coding worker 可能返回：

```text
root cause 已确认，
但因为缺少 integration test fixture，
暂时无法验证修复。
```

如果 Orchestrator 把这种结果简单压成：

```text
completed
```

会丢失未完成部分。

压成：

```text
failed
```

又会丢失已经得到的证据。

因此更合理的 worker result 可能包含：

```text
status
findings
artifacts
unresolved
blockers
```

让父任务知道：

```text
哪些信息已经可以使用，
哪些缺口还需要新的 task。
```

---

最后一类最容易被忽略：**synthesis loss**。

假设四个 worker 分别发现：

```text
A:
refresh token rotation 正常。

B:
Redis 中仍保存旧 session key。

C:
客户端可能并发发送两次 refresh。

D:
现有 integration test 没覆盖第二次 refresh。
```

中央 synthesis 最后写成：

```text
问题主要与 Redis session 相关，
建议更新缓存逻辑并增加测试。
```

这段话看起来合理，却丢掉了：

```text
客户端存在并发 refresh 的观察。
```

如果那恰好是另一条触发路径，前面支付的 worker 调查成本就在 synthesis 阶段被抹掉。

因此：

```text
所有 worker 都做对了
```

并不能推出：

```text
最终结果保留了所有关键发现。
```

可以写成：

$$
\text{Final Quality}
\neq
\sum_i \text{Worker Quality}_i
$$

因为中间还有：

$$
\text{Aggregation / Synthesis}
$$

这一层信息瓶颈。

对于证据敏感任务，比让 Orchestrator重新自由总结更稳妥的方式之一，是先保存结构化结果：

```text
Finding F01
Finding F02
Finding F03
Finding F04
```

再要求 synthesis 显式处理这些 finding：

```text
covered
discarded with reason
unresolved
```

至少能够观察：

```text
哪个事实是在 worker 阶段丢的，
哪个事实是在 synthesis 阶段丢的。
```

---

把这些 failure mode 放在一起，Orchestrator–Workers 比最初那张架构图多出的实际状态大致是：

```text
                   Task
                    │
                    ▼
              Orchestrator
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
     Task A      Task B      Task C
     scope       scope       scope
     deps        deps        deps
        │           │           │
        ▼           ▼           ▼
    Workspace   Workspace   Workspace
        │           │           │
        ▼           ▼           ▼
     Result A    Result B    Result C
        │           │           │
        └───────────┼───────────┘
                    │
                    ▼
                Synthesis
                    │
                    ▼
                 Output
```

并且每个节点都可能处于：

```text
planned
ready
running
blocked
completed
failed
```

这也是为什么：

```text
Orchestrator–Workers
```

不能被实现层面缩成：

```python
for task in tasks:
    spawn_agent(task)
```

真正困难的部分不是调用几次模型，而是动态任务成为 runtime object 以后，必须开始管理：

```text
identity
scope
dependency
context
workspace
result
failure
```

Anthropic 在 *Building effective agents* 中给出的 pattern 到这里为止，主要解释的是控制结构：Orchestrator 动态分解、Worker 执行、结果再 synthesis。后面的状态持久化、workspace isolation、dependency scheduling、retry 和恢复，并不是这篇文章为该 pattern 给出的完整 runtime specification。

这条边界对本文后面的目录很重要。

`_index.md` 在这里回答：

```text
为什么需要动态 decomposition？
```

而不是继续回答：

```text
一个长期运行的工程系统，
怎样让这些动态 task
跨进程、跨 workspace、跨 CI feedback
可靠地活下去？
```

后一个问题会进入 Symphony 一类 orchestration runtime。

---

到这里，前四种 workflow 处理的不确定性已经逐渐展开：

```text
Prompt Chaining
步骤固定，
中间内容不确定

Routing
候选路径固定，
具体选择不确定

Parallelization
子任务固定，
执行结果不确定

Orchestrator–Workers
连具体子任务集合
也在运行时确定
```

但还有一种不同方向的不确定性没有处理。

有时我们并不缺任务分解：

```text
我们知道应该生成什么。
```

问题是：

```text
生成一次以后，
不知道这个结果到底够不够好。
```

如果质量能够被评价，而且评价能够产生下一轮可以执行的反馈，就没有必要继续增加 worker 数量。更合适的控制结构是把：

```text
Generation
```

和：

```text
Evaluation
```

拆成两个角色，让结果沿反馈环迭代。

下一节进入 **Evaluator–Optimizer**。

## 6. Evaluator–Optimizer——把生成和判断是否够好拆开

前面的几种 workflow 主要在回答：

```text id="eo01"
下一步做什么？
走哪条路？
哪些任务可以并行？
需要动态拆出哪些子任务？
```

Evaluator–Optimizer 处理的是另一种问题。

任务本身可能已经很明确：

```text id="eo02"
翻译这段文本
写这份技术文档
生成一段代码
回答这个研究问题
```

真正不确定的是：

```text id="eo03"
第一次生成出来以后，
这个结果到底够不够好？
```

Anthropic 在 *Building effective agents* 中把 Evaluator–Optimizer 描述成一个反馈循环：一个 LLM 负责生成结果，另一个 LLM 负责评价并给出反馈，Generator 根据反馈继续修改，直到满足要求。原文强调，这种模式适合 **评价标准比较清楚，而且迭代反馈能够产生可测量改善** 的任务。

最小结构是：

```text id="eo04"
Generator
    │
    ▼
Candidate
    │
    ▼
Evaluator
  ┌─┴───────────────┐
  │                  │
pass              feedback
  │                  │
  ▼                  │
Done                 │
                     │
                     ▼
                 Generator
```

这里最容易出现一个误解：

```text id="eo05"
Evaluator–Optimizer
=
如果失败就 Retry
```

两者并不一样。

普通 retry 更接近：

```text id="eo06"
Call
 │
 ├─ error
 │    │
 │    ▼
 │  retry
 │
 └─ success
```

例如：

```python id="eo07"
for _ in range(3):
    try:
        return call_api()
    except TimeoutError:
        continue
```

第二次调用并没有因为第一次的失败获得更多任务信息，只是重新执行相同动作。

Evaluator–Optimizer 则要求上一轮结果产生新的状态：

```text id="eo08"
Candidate v1
    │
    ▼
Evaluation
    │
    ▼
Feedback
    │
    ▼
Candidate v2
```

于是第二轮优化面对的输入已经改变：

$$
x_{t+1}
=
(x_t, y_t, f_t)
$$

其中：

* \(x_t\) 是任务上下文；
* \(y_t\) 是当前 candidate；
* \(f_t\) 是 evaluator 对它的反馈。

Generator 不是简单“再试一次”，而是：

```text id="eo09"
根据明确指出的缺口
修改当前结果。
```

所以这个 pattern 真正成立的关键，不只是存在一个 loop，而是存在一个 **有信息增量的 feedback loop**。

### 6.1 Evaluator 不是第二个 Generator，它需要产生可执行的反馈

先看一个很弱的 evaluator：

```text id="eo10"
Candidate:
这份实现基本完成了 OAuth 登录。

Evaluator:
这个实现还可以进一步优化。
```

这句反馈几乎没有提供新的控制信息。

Generator 下一轮仍然不知道：

```text id="eo11"
哪里有问题？
缺了什么？
哪条约束没有满足？
应该改哪一部分？
```

于是所谓优化可能只是：

```text id="eo12"
Candidate v1
    ↓
“再完善一下”
    ↓
Candidate v2
```

本质上仍然接近重新采样。

更有用的 evaluator 应该把评价标准落到当前 candidate 上。

例如任务要求：

```text id="eo13"
为 refresh token rotation 增加实现和 regression test，
不能破坏现有 session API。
```

Evaluator 可以输出：

```text id="eo14"
1. `rotate_refresh_token()` 已经生成新 token；
2. 旧 refresh token 没有在 Redis 中失效；
3. `tests/integration/test_refresh.py`
   只覆盖第一次 refresh；
4. 目前没有验证现有 session endpoint 的响应 schema。
```

这里每一条都能转成下一轮 action：

```text id="eo15"
invalidate old token
add second-refresh regression test
run session API compatibility test
```

所以可以把一个更完整的 evaluator contract 写成：

```json id="eo16"
{
  "verdict": "needs_revision",
  "criteria": [
    {
      "name": "old_token_invalidated",
      "status": "fail",
      "evidence": "Redis session key remains valid after rotation.",
      "feedback": "Invalidate the previous refresh token when rotation succeeds."
    },
    {
      "name": "regression_test",
      "status": "fail",
      "evidence": "No test attempts a second refresh with the old token.",
      "feedback": "Add a test that verifies the old token is rejected."
    },
    {
      "name": "session_api_compatibility",
      "status": "unknown",
      "feedback": "Run the existing session API tests before declaring compatibility."
    }
  ]
}
```

它比：

```json id="eo17"
{
  "score": 7.5
}
```

更适合 Optimizer。

单独一个分数可以用于排序或监控，但如果目标是驱动下一轮修改：

```text id="eo18"
7.5 → 8.0
```

并没有解释怎么改。

因此 Evaluator–Optimizer 里的 evaluator 更接近：

```text id="eo19"
grader
+
diagnostician
```

而不是：

```text id="eo20"
score function
```

---

Anthropic 原文给出了两个判断这种 workflow 是否合适的信号。

第一，如果人类给出反馈以后，Generator 的结果能够明显改善：

```text id="eo21"
初稿
→ 人类指出具体问题
→ 修改稿明显更好
```

说明任务本身存在可利用的 iterative refinement structure。

第二，LLM 是否也能产生类似有用的反馈。

这两个条件都很具体。

例如文学翻译中：

```text id="eo22"
Generator:
生成初稿

Evaluator:
指出语气、双关、文化含义或风格偏差

Generator:
重新处理对应句子
```

Anthropic 正是把 literary translation 作为典型例子之一。

但如果任务是：

```text id="eo23"
从 JSON 中读取 `user_id`
```

结果只有：

```text id="eo24"
正确
错误
```

而且 deterministic parser 已经能直接完成，就没有理由引入 Generator–Evaluator 循环。

所以这里仍然遵循整篇文章的原则：

```text id="eo25"
能用确定性程序解决的判断，
优先使用确定性 verifier。
```

Evaluator LLM 更适合那些：

```text id="eo26"
评价标准可以描述，
但很难完全编码成确定性函数。
```

例如：

```text id="eo27"
翻译是否保持原文语气？
技术解释是否漏掉关键步骤？
研究总结是否真正回答了问题？
文章结构是否出现重复论证？
```

---

还需要区分：

```text id="eo28"
Evaluation
```

和：

```text id="eo29"
Verification
```

这两个词在不同文章和系统里经常混用，本文不强制给它们一个行业统一定义，但在这个 workflow 中可以采用一个实用区分：

```text id="eo30"
Deterministic Verification
能直接从环境或规则验证

Semantic Evaluation
需要模型判断质量、覆盖、表达或推理
```

例如代码任务：

```text id="eo31"
pytest passed?
→ deterministic

type checker passed?
→ deterministic

endpoint returns expected schema?
→ deterministic
```

而：

```text id="eo32"
这个实现是不是引入了不必要的复杂度？
错误处理是否解释清楚？
这个 API 设计是否符合已有 repository convention？
```

更可能需要 evaluator。

最稳妥的结构通常不是二选一，而是组合：

```text id="eo33"
Candidate
    │
    ▼
Deterministic Checks
    │
    ├─ fail ───────────► actionable failures
    │
    ▼
LLM Evaluator
    │
    ▼
semantic feedback
    │
    ▼
Optimizer
```

这样 evaluator 不必浪费 token 去猜：

```text id="eo34"
测试到底过没过？
```

它可以直接读取：

```text id="eo35"
pytest:
2 failed, 81 passed
```

然后分析失败意味着什么。

这也是为什么：

```text id="eo36"
LLM as Judge
```

不应该被理解成“所有验证都改成让另一个模型看看”。

环境能回答的问题，优先让环境回答。

### 6.2 Evaluator 必须和 Generator 共享标准，但不应该只复述 Generator 的思路

如果 Generator 收到：

```text id="eo37"
写一篇解释 OAuth 2.0 PKCE 的文章。
```

Evaluator 只收到：

```text id="eo38"
你觉得下面文章写得好吗？
```

评价标准非常宽。

它可能输出：

```text id="eo39"
结构清晰，解释准确，建议增加示例。
```

这种反馈很难稳定。

更合理的做法是提前定义 evaluation criteria。

例如：

```text id="eo40"
必须解释：
1. Authorization Code Flow 的攻击面；
2. code_verifier；
3. code_challenge；
4. S256；
5. authorization request；
6. token exchange；
7. PKCE 不能替代 client authentication 的边界。
```

Evaluator 检查的是：

```text id="eo41"
Candidate
vs
Criteria
```

而不是：

```text id="eo42"
Candidate
vs
Evaluator 自己临时产生的审美标准
```

于是：

```text id="eo43"
Task Spec
   │
   ├──────────────► Generator
   │
   └──────────────► Evaluator
```

两者共享同一组 acceptance criteria。

但职责不同：

```text id="eo44"
Generator:
怎样满足标准？

Evaluator:
当前 candidate 哪些标准已经满足，
哪些没有满足？
```

这个 role separation 很重要。

如果 Evaluator 的 prompt 只是：

```text id="eo45"
这是 Generator 的答案和完整 reasoning，
请判断它是不是正确。
```

Evaluator 很容易沿着同一条解释轨迹继续确认已有结论。

一种更合适的输入组织是：

```text id="eo46"
Task
Acceptance Criteria
Candidate
Relevant Environment Evidence
```

而不是让 evaluator 必须继承 Generator 的全部自然语言过程。

这不保证两个模型就获得了统计意义上的独立性，但至少减少：

```text id="eo47"
把 Generator 自己的论证
直接当成 Evaluator 的证据。
```

在 coding 中尤其明显。

Generator 可能说：

```text id="eo48"
我已经修复了 race condition，
并确保所有测试通过。
```

Evaluator 不应该直接把这句话当事实。

它应该读取：

```text id="eo49"
git diff
test output
repository state
acceptance criteria
```

再形成判断。

即：

```text id="eo50"
Generator Claim
≠
Environment Evidence
```

这与真正的代码 review 很接近：

```text id="eo51"
作者说：
“这里已经修好了”

Reviewer:
“让我看 diff 和 tests。”
```

---

还需要注意 Evaluator 本身也会错。

假设：

```text id="eo52"
Generator 正确
Evaluator 错误地说存在问题
```

Optimizer 可能把一个正确答案改坏。

反过来：

```text id="eo53"
Generator 有问题
Evaluator 没发现
```

系统可能提前停止。

所以整个 loop 的成功不只是：

$$
Q_{t+1} > Q_t
$$

自动成立。

更准确地说，我们希望在 eval distribution 上观察：

$$
E[Q_{t+1} - Q_t] > 0
$$

也就是反馈循环平均能够产生正向改善。

这正是 Anthropic 原文为什么强调：

```text id="eo54"
iterative refinement
必须具有 measurable value
```

而不是因为“两个 LLM 相互批评听起来更可靠”。

例如我们可以实际运行：

```text id="eo55"
baseline:
Generator only

variant:
Generator + 1 eval cycle

variant:
Generator + up to 3 eval cycles
```

然后比较：

```text id="eo56"
task success
quality score
human preference
latency
token usage
```

如果：

```text id="eo57"
第一次生成已经足够好，
后面三轮只增加 4 倍 token，
质量几乎不变，
```

就没有理由保留这个 loop。

Anthropic 后续关于 agent architecture 的材料也明确把 first-attempt quality 已经满足要求、评价标准模糊，以及 latency / cost 不允许的场景列为不适合 Evaluator–Optimizer 的情况。

### 6.3 没有 stopping condition，Optimizer 可以一直“再改一版”

最危险的实现是：

```python id="eo58"
while not evaluator.is_satisfied(candidate):
    candidate = improve(candidate)
```

这段代码没有回答：

```text id="eo59"
如果 Evaluator 永远不满意呢？
```

LLM evaluator 很容易持续找到新的修改意见。

例如文章修改：

```text id="eo60"
Round 1:
缺少代码例子。

Round 2:
例子已经有了，但可以增加边界条件。

Round 3:
边界条件已经有了，但语气还能更简洁。

Round 4:
已经很简洁，但可以加入对比表。

Round 5:
对比表不错，不过开头还能更自然。
```

如果 stopping rule 是：

```text id="eo61"
直到没有任何改进空间
```

那几乎没有稳定终点。

因为开放式生成任务通常总能提出：

```text id="eo62"
另一个措辞
另一个例子
另一个结构
```

因此 Evaluator–Optimizer 必须显式定义 termination contract。

最简单的一种：

```python id="eo63"
MAX_ITERATIONS = 3

feedback = None

for iteration in range(MAX_ITERATIONS):
    candidate = generate_or_revise(
        task=task,
        candidate=candidate,
        feedback=feedback,
    )

    verdict = evaluate(
        task=task,
        candidate=candidate,
    )

    if verdict.status == "pass":
        return candidate

    feedback = verdict.feedback

return candidate
```

至少存在两个停止出口：

```text id="eo64"
pass

max_iterations
```

但生产系统通常还需要更多状态。

---

#### Pass

Evaluator 判断所有必须条件已经满足：

```json id="eo65"
{
  "status": "pass",
  "remaining_issues": []
}
```

这是正常完成。

但 `pass` 最好基于明确 criteria，而不是：

```text id="eo66"
整体感觉不错。
```

---

#### Max Iterations

例如：

```text id="eo67"
最多允许 3 轮。
```

达到：

$$
t = T_{\max}
$$

就退出。

此时退出并不等于：

```text id="eo68"
任务成功
```

更准确的结果可能是：

```json id="eo69"
{
  "status": "max_iterations_reached",
  "candidate": "...",
  "remaining_issues": [...]
}
```

这样上层才能区分：

```text id="eo70"
通过验收
```

与：

```text id="eo71"
只是预算不允许继续改。
```

---

#### Budget Exhausted

限制不一定是 iteration count。

还可能是：

```text id="eo72"
token budget
API cost
wall-clock deadline
tool execution budget
```

例如：

$$
C_{\text{used}}
+
C_{\text{next}}
>
C_{\max}
$$

就不再进入下一轮。

因为每轮 Evaluator–Optimizer 至少包含：

```text id="eo73"
Generator call
+
Evaluator call
```

如果进行了 \(n\) 轮，可以粗略写成：

$$
C_{\text{total}}
\approx
\sum_{i=1}^{n}
(C_{G_i}+C_{E_i})
$$

还没有计算 tool、retrieval 和 verification。

所以它的成本增长明显快于一次生成。

---

#### No Progress

还有一种比 max iteration 更值得检测的情况：

```text id="eo74"
Evaluator 一直重复同一个问题，
Optimizer 却始终没有解决。
```

例如：

```text id="eo75"
Round 1:
缺 test_second_refresh

Round 2:
仍然缺 test_second_refresh

Round 3:
仍然缺 test_second_refresh
```

这说明：

```text id="eo76"
继续重复相同 feedback
```

可能已经没有价值。

可以记录 unresolved criterion：

```python id="eo77"
if unresolved_criteria == previous_unresolved_criteria:
    stagnant_rounds += 1
else:
    stagnant_rounds = 0

if stagnant_rounds >= MAX_STAGNANT_ROUNDS:
    return NO_PROGRESS
```

当然，真实文本反馈不会完全字符串相同，所以可能需要基于 criterion ID：

```text id="eo78"
C01
C02
C03
```

追踪，而不是比较整段自然语言。

例如：

```text id="eo79"
Round 1:
C01 fail
C02 fail
C03 pass

Round 2:
C01 pass
C02 fail
C03 pass

Round 3:
C01 pass
C02 fail
C03 pass
```

可以明确看到：

```text id="eo80"
C02 连续两轮没有改善。
```

这比：

```text id="eo81"
“模型好像陷入循环了”
```

更可观察。

---

#### Regression

Optimizer 还可能修好一项、破坏另一项。

例如：

```text id="eo82"
Round 1

Correctness: fail
Compatibility: pass
```

修改后：

```text id="eo83"
Round 2

Correctness: pass
Compatibility: fail
```

如果 evaluator 只检查上一轮指出的问题：

```text id="eo84"
只检查 Correctness
```

就可能宣布：

```text id="eo85"
pass
```

所以每轮评价最好重新检查完整的必须 criteria，而不是只验证最新反馈。

即：

```text id="eo86"
Incremental Feedback
≠
Incremental Acceptance Criteria
```

反馈可以只强调当前缺口，但最终验收仍然应该覆盖整个 contract。

---

#### Human Escalation

还有一些情况不应该继续自动循环。

例如：

```text id="eo87"
两个要求互相冲突
```

或：

```text id="eo88"
Evaluator 连续两轮无法判断
```

或：

```text id="eo89"
修改将触发高风险副作用
```

这时可以退出为：

```text id="eo90"
human_review
```

例如：

```json id="eo91"
{
  "status": "human_review",
  "reason": "Requirement conflict",
  "conflict": [
    "Do not change the session API",
    "Remove the existing session field required by clients"
  ]
}
```

让系统继续自动“优化”只会让模型替用户选择一个没有被授权的 trade-off。

---

因此一个更完整的 termination state 可以写成：

```text id="eo92"
PASS
MAX_ITERATIONS
BUDGET_EXHAUSTED
NO_PROGRESS
BLOCKED
HUMAN_REVIEW
```

它们都代表：

```text id="eo93"
loop stopped
```

但只有：

```text id="eo94"
PASS
```

天然代表：

```text id="eo95"
验收标准已经满足。
```

这一点对于后面的长任务 orchestration 很重要，因为：

```text id="eo96"
terminated
≠
completed successfully
```

### 6.4 Evaluator–Optimizer 最后仍然需要外部验收，而不是自我确认

到这里可能会产生一种错觉：

```text id="eo97"
Generator
+
Evaluator
+
循环三次
=
可靠结果
```

但 Evaluator 本身仍然是模型。

如果任务存在外部 ground truth，最终仍然应该尽可能回到真实环境。

例如代码生成：

```text id="eo98"
Generator
    │
    ▼
Code
    │
    ▼
Evaluator
    │
    ▼
Revised Code
```

最后仍然需要：

```text id="eo99"
compile
test
integration test
benchmark
```

而不是让 Evaluator 说：

```text id="eo100"
“我认为代码现在应该可以通过测试。”
```

Anthropic 2026 年关于 agent eval 的文章也沿用了同样的方向：对 coding agent 的复杂 eval，不只是检查模型自己说了什么，而是让 agent 修改环境，再通过 unit tests 等 grader 检查最终环境状态。

因此代码场景更完整的链路可能是：

```text id="eo101"
Task
 │
 ▼
Generator
 │
 ▼
Candidate
 │
 ├────────────► Tests / Static Checks
 │                     │
 │                     ▼
 │                  Evidence
 │                     │
 ▼                     │
Evaluator ◄─────────────┘
 │
 ├─ pass
 │
 └─ feedback
      │
      ▼
   Generator
```

Evaluator 的职责变成：

```text id="eo102"
解释 evidence
+
发现 deterministic checks 没覆盖的问题
+
产生修改建议
```

而不是代替 environment。

对于 research task，同样可以是：

```text id="eo103"
Generator Draft
     │
     ▼
Citation Check
Source Coverage
Date Verification
     │
     ▼
Evaluator
     │
     ▼
Revision
```

对于技术博客：

```text id="eo104"
Draft
 │
 ├─ link check
 ├─ heading check
 ├─ code block check
 ├─ claim/source check
 │
 ▼
Editorial Evaluator
 │
 ▼
Revision
```

这和本文自己的写作流程已经很接近：能自动检查的格式和引用完整性不应该交给“文风 evaluator”猜，而主张、结构和解释质量再由语义评价处理。

---

这个 pattern 也可以和前面几种 workflow 组合。

例如一个 coding request：

```text id="eo105"
Request
   │
   ▼
Orchestrator
   │
   ├─► Worker A
   ├─► Worker B
   └─► Worker C
          │
          ▼
       Synthesis
          │
          ▼
      Evaluator
        │     │
     pass   feedback
        │     │
        ▼     └──────► Orchestrator / Generator
       Done
```

或者某个单独 worker 内部使用：

```text id="eo106"
Generate
  ↓
Evaluate
  ↓
Revise
```

因此 Evaluator–Optimizer 并不是：

```text id="eo107"
Orchestrator–Workers 的下一代架构
```

它们处理的是两个正交问题：

```text id="eo108"
Orchestrator–Workers
解决：
需要做哪些工作？

Evaluator–Optimizer
解决：
当前结果是否已经够好？
```

一个系统完全可以两个都需要。

---

把五种 workflow 放回前面的不确定性坐标，到这里已经完整了一轮：

```text id="eo109"
Prompt Chaining
不知道每一步会生成什么，
但知道步骤顺序。

Routing
不知道进入哪条路径，
但知道候选路径。

Parallelization
知道要做哪些任务，
只是它们可以独立执行。

Orchestrator–Workers
连这一次需要哪些子任务
都要运行时生成。

Evaluator–Optimizer
知道要生成什么，
但不知道一次生成是否已经满足质量标准。
```

这也说明五种 pattern 并不是：

```text id="eo110"
Level 1
Level 2
Level 3
Level 4
Level 5
```

它们没有统一的“高级程度”。

更准确的关系是：

```text id="eo111"
针对不同位置的不确定性，
加入不同的控制结构。
```

下一节就不再继续逐个 pattern 介绍，而是把它们重新组合起来。

真实系统很少严格属于：

```text id="eo112"
纯 Routing
```

或：

```text id="eo113"
纯 Evaluator–Optimizer
```

更常见的是：

```text id="eo114"
Routing
→ Orchestrator–Workers
→ Parallel Workers
→ Synthesis
→ Evaluator–Optimizer
```

真正需要设计的是：每增加一层控制结构，它解决了哪个已经观察到的问题，又额外带来了多少 latency、token、状态和 failure mode。

## 7. 五种 Pattern 不是互斥选项——现实系统通常是组合

到这里已经分别讨论了：

```text
Prompt Chaining
Routing
Parallelization
Orchestrator–Workers
Evaluator–Optimizer
```

如果把前面几节理解成“五选一”，反而会把 Anthropic 这套分类用错。

这些 pattern 描述的是不同位置的控制结构，不是五种互斥的产品架构。一个系统可以先 Routing，再进入 Orchestrator–Workers；Orchestrator 产生的几个独立任务可以 Parallelization；每个 worker 内部又可以执行 Prompt Chaining；最后合并的结果还可以进入 Evaluator–Optimizer。

Anthropic 在 *Building effective agents* 中专门强调，这些 building blocks 并不是一套必须照抄的 prescription，而是开发者可以根据 use case 塑造和组合的 common patterns。问题因此不应该是：

```text
我的系统到底属于哪一种 Pattern？
```

更有用的问法是：

```text
这个系统的哪个位置
存在什么类型的不确定性？

我为了处理这部分不确定性，
加入了哪一种控制结构？
```

这两个问题看似只换了一种说法，实际会直接改变系统设计。

### 7.1 一个请求可以同时经过五种控制结构

还是用 repository-level coding task 举例：

```text
修复 refresh token rotation 后偶发 401 的问题，
增加 regression test，
不要改变现有 session API。
```

如果系统只有一个 coding agent，可以直接：

```text
Request
   │
   ▼
Coding Agent
   │
   ├─ read
   ├─ search
   ├─ edit
   ├─ test
   └─ done
```

这当然可能工作。

但如果我们已经通过 eval 观察到，不同类型请求的复杂度差异很大，就可能不希望所有任务都进入同一套昂贵流程。例如：

```text
“把 README 里的版本号改成 2.4.1”
```

和：

```text
“修复跨服务 refresh-token rotation 的 race condition”
```

虽然都叫 coding request，需要的 orchestration 明显不同。

于是最外层可以先出现 Routing：

```text
                       ┌─► Simple Edit
                       │
Request ─► Router ─────┼─► Structured Workflow
                       │
                       └─► Open-ended Coding Agent
```

如果是简单修改：

```text
README typo
版本号
配置值
```

可能一次调用加 deterministic verification 就结束。

如果是复杂 repository change，再进入更重的路径：

```text
Request
   │
   ▼
Router
   │
   └─ complex coding task
            │
            ▼
       Orchestrator
```

这里 Routing 解决的是：

```text
这个请求应该进入哪一种已有 execution path？
```

它没有负责拆解具体代码任务。

进入 Orchestrator 后，新的不确定性才出现：

```text
这个 bug 到底涉及仓库里的哪些组件？
```

Orchestrator 根据 issue、repository tree 和初始搜索结果产生：

```text
Task A:
调查 auth middleware

Task B:
调查 Redis session state

Task C:
调查 frontend refresh deduplication

Task D:
检查现有 regression coverage
```

现在系统使用了 Orchestrator–Workers，因为：

```text
A / B / C / D
```

不是在写 workflow 时固定好的，而是根据本次输入动态生成。

接下来观察依赖关系：

```text
        ┌─► A ─┐
        │      │
Input ──┼─► B ─┼─► Synthesis
        │      │
        ├─► C ─┤
        │      │
        └─► D ─┘
```

如果四个 investigation 都只依赖 repository snapshot，而不需要彼此的输出，就可以同时执行。这一层使用的是 Parallelization。

注意，这里没有发生：

```text
Orchestrator–Workers
升级成
Parallelization
```

而是：

```text
Orchestrator–Workers
决定生成哪些 task

Parallelization
决定这些 task 的执行关系
```

两个 pattern 解决不同问题。

---

某一个 worker 内部又可能存在稳定 pipeline。

例如：

```text
Task D:
检查现有 regression coverage
```

worker 可以采用：

```text
search tests
   │
   ▼
extract relevant cases
   │
   ▼
compare against required behavior
   │
   ▼
produce coverage report
```

甚至把每一步显式拆成：

```text
LLM 1
识别 relevant tests
   │
   ▼
Gate
确认文件真实存在
   │
   ▼
LLM 2
分析 coverage gap
```

这里就是 Prompt Chaining。

为什么不用一个开放式 Agent 一直跑？

因为对于这个局部任务，我们已经知道：

```text
先定位测试
→ 再分析 coverage
```

是稳定的数据依赖。没有必要为了统一架构，强行把所有局部工作都交给自主 Agent。

---

多个 worker 完成后，Orchestrator 做 synthesis：

```text
A:
middleware 正常

B:
Redis 保存旧 session key

C:
客户端存在 duplicate refresh window

D:
缺少 second-refresh regression test
```

得到候选修复计划：

```text
Candidate Fix Plan
```

这时候系统还不知道：

```text
这个计划是不是已经覆盖任务要求？
```

于是可以进入 Evaluator–Optimizer：

```text
Worker Results
     │
     ▼
  Synthesis
     │
     ▼
 Candidate
     │
     ▼
 Evaluator
   │      │
 pass  feedback
   │      │
   ▼      └────────► Optimizer
 Done
```

Evaluator 根据原始 acceptance criteria 检查：

```text
root cause 是否有 evidence？
regression test 是否覆盖？
session API 是否保持兼容？
是否还有 worker finding 被 synthesis 丢掉？
```

如果发现：

```text
客户端 duplicate refresh
在最终方案中没有处理
```

就把这一条作为 feedback 返回。

于是一个完整 workflow 可能变成：

```text
Request
   │
   ▼
Routing
   │
   ├─ Simple ───────────────► Single Call
   │
   └─ Complex
         │
         ▼
    Orchestrator
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
      Worker A   Worker B   Worker C   Worker D
         │          │          │          │
         └──────────┴──────────┴──────────┘
                       │
                       ▼
                   Synthesis
                       │
                       ▼
                   Evaluator
                    │      │
                 pass   feedback
                    │      │
                    ▼      └──────► revision
                   Done
```

而 Worker D 内部可能还是：

```text
Prompt Chain
```

几个 Evaluator 又可能采用：

```text
Parallelization / Sectioning
```

例如分别检查：

```text
correctness
security
compatibility
test coverage
```

因此完整结构甚至可以写成：

```text
Routing
    │
    ▼
Orchestrator–Workers
    │
    ▼
Parallelization
    │
    ▼
Prompt Chaining inside workers
    │
    ▼
Synthesis
    │
    ▼
Parallel Evaluators
    │
    ▼
Evaluator–Optimizer
```

这不是为了把五种 pattern 全部凑齐。

如果其中任何一层没有解决实际问题，都应该删掉。

例如：

```text
所有 coding request
其实复杂度都差不多
```

那最外层 Router 没必要存在。

如果：

```text
worker tasks 之间有严格依赖
```

就不应该为了并行而并行。

如果：

```text
第一次 synthesis 的质量已经稳定满足要求
```

Evaluator–Optimizer 也没有存在的必要。

所以组合 pattern 的原则不是：

```text
组件越多
→ Agent System 越成熟
```

而是每个控制节点都应该能够回答：

```text
没有我，会出现什么可复现的问题？
```

如果答不出来，这一层 orchestration 很可能只是结构上的装饰。

### 7.2 选 Pattern 时，先找“不确定性究竟出现在哪里”

五种 pattern 最容易记住的方法，不是背五张架构图，而是从一个任务里不断问：

> **到底是哪件事，我在运行前无法确定？**

先考虑最简单的情况。

假设任务是：

```text
把英文产品说明翻译成中文，
然后根据固定模板生成摘要。
```

我们已经知道：

```text
translate
→ summarize
```

唯一不确定的是每一步会生成什么内容。

这里没有：

```text
路线选择
动态任务发现
并行需求
反复评价
```

所以直接使用 Prompt Chaining 就足够。

可以写成：

```text
步骤已知
+
存在数据依赖
────────────────
Prompt Chaining
```

---

再看客服：

```text
用户可能问退款，
也可能问技术问题，
也可能只是普通 FAQ。
```

每个下游流程都已经存在：

```text
refund
technical
general
```

不确定的是：

```text
当前输入属于哪一个？
```

于是：

```text
候选路径已知
+
当前路径未知
────────────────
Routing
```

---

再看代码 review。

系统每次都必须检查：

```text
correctness
security
performance
```

三项工作全部已知，而且互相不需要读取对方输出。

于是：

```text
子任务已知
+
都需要执行
+
没有必要的数据依赖
────────────────
Parallelization / Sectioning
```

如果不是三个不同检查，而是希望同一个安全问题获得多个独立 reviewer：

```text
同一个任务
+
需要多个独立尝试或视角
────────────────
Parallelization / Voting
```

这两种虽然都叫 Parallelization，解决的仍然不是同一个问题。

---

现在进入 repository coding。

用户只给出：

```text
修复登录 bug。
```

在真正查看代码之前，我们不知道：

```text
需要几个 task
涉及哪些文件
要调查哪些组件
```

此时：

```text
任务目标已知
+
子任务集合未知
────────────────
Orchestrator–Workers
```

---

最后看技术文档。

目标和结构都很明确，也能够一次生成，但经验表明：

```text
初稿经常遗漏边界条件
或者把证据不足的内容写成确定结论
```

这时未知的不是：

```text
下一步做什么？
```

而是：

```text
当前结果是否已经满足标准？
```

于是：

```text
输出目标已知
+
评价标准相对明确
+
反馈可以驱动修改
────────────────
Evaluator–Optimizer
```

---

把这些判断放到一张表里：

| 运行前无法确定的东西   | 已经确定的东西                   | 优先考虑的 Pattern                |
| ------------ | ------------------------- | ---------------------------- |
| 每一步的具体内容     | 步骤及先后关系                   | Prompt Chaining              |
| 当前应该进入哪条路径   | 候选路径集合                    | Routing                      |
| 无；多个工作都需要执行  | 子任务集合及独立性                 | Parallelization / Sectioning |
| 同一任务哪次尝试更可靠  | 任务本身                      | Parallelization / Voting     |
| 本次究竟需要哪些子任务  | 高层 orchestration protocol | Orchestrator–Workers         |
| 当前结果是否已经达到标准 | 目标和评价 criteria            | Evaluator–Optimizer          |

这张表还可以继续往下走。

如果连下面这些都无法提前决定：

```text
需要几步？
下一步使用哪个工具？
刚才的 observation 是否改变了计划？
要不要回头检查之前的假设？
什么时候停止探索？
```

那么固定 workflow 开始越来越难表达任务。

问题已经从：

```text
workflow 中某个位置存在不确定性
```

变成：

```text
整个 execution trajectory
都需要根据 observation 动态展开
```

这才逐渐接近 Anthropic 所说的 Agent。

因此可以得到一棵更实用的判断树：

```text
任务能否由一次调用稳定完成？
│
├─ 能
│   └─ Single / Augmented LLM
│
└─ 不能
    │
    ├─ 步骤固定，而且存在顺序依赖？
    │      └─ Prompt Chaining
    │
    ├─ 只是需要在已有路径中选择？
    │      └─ Routing
    │
    ├─ 已知的多个任务可以独立执行？
    │      └─ Parallelization
    │
    ├─ 连本次需要哪些子任务都不知道？
    │      └─ Orchestrator–Workers
    │
    ├─ 输出能够生成，但需要反馈改进？
    │      └─ Evaluator–Optimizer
    │
    └─ 连执行路径本身都无法合理预定义？
           └─ Agent
```

实际系统当然不会严格沿这棵树一次做出唯一选择。一个任务可能同时满足：

```text
需要动态 decomposition
+
部分 task 可以并行
+
最终结果需要 evaluator
```

这张图的用途只是帮助定位：

```text
为什么我要加入这一层结构？
```

而不是把系统归类成某一个标签。

---

还有一个很实用的反向判断。

如果需求可以写成：

```text
“我已经知道 X，
只是 Y 不知道。”
```

通常比较容易定位 pattern。

例如：

```text
我已经知道处理流程，
只是当前输入该走哪条不知道。
→ Routing

我已经知道所有任务，
只是没有必要一个一个等待。
→ Parallelization

我已经知道最终标准，
只是当前版本达没达到不知道。
→ Evaluator–Optimizer
```

而如果发现自己无法完成：

```text
“我已经知道……”
```

这一半，说明问题可能还没有被约束到足以设计 workflow。

这时候比马上增加 Agent 更值得做的，可能是：

```text
补任务 specification
补环境信息
补 tool contract
补 acceptance criteria
```

因为 orchestration 不能替代缺失的任务定义。

### 7.3 Pattern 不是升级树，每增加一层都应该对应一个可测量收益

前面的判断树很容易被误读成：

```text
Single Call
    ↓
Prompt Chaining
    ↓
Routing
    ↓
Parallelization
    ↓
Orchestrator–Workers
    ↓
Evaluator–Optimizer
    ↓
Agent
```

仿佛这是从：

```text
初级
→ 高级
```

的架构成熟度路线。

Anthropic 的结论恰好不是这样。

*Building effective agents* 一开始就建议寻找 **最简单能够解决问题的方案**，因为 agentic systems 通常是在 latency 和 cost 上付出更多，换取更好的任务表现；在介绍完这些 pattern 后，文章再次强调，增加复杂度应该以可测量的结果改善为前提。

因此 pattern selection 应该从 baseline 开始，而不是从架构图开始。

例如我们正在做一个文章生成任务。

Baseline：

```text
Topic
  │
  ▼
Single LLM
  │
  ▼
Article
```

测试 100 个 case 后发现：

```text
结构覆盖率       93%
事实错误率        2%
平均 latency      8 s
平均 cost         C
```

如果这些指标已经满足产品要求：

```text
不要因为知道 Prompt Chaining
就把它拆成五步。
```

如果实际失败主要是：

```text
文章经常漏掉用户明确要求的章节
```

我们才有理由尝试：

```text
outline
→ outline validation
→ draft
```

新的 variant 得到：

```text
结构覆盖率       98%
事实错误率        2%
平均 latency     14 s
平均 cost        1.6C
```

这时至少存在一个明确 trade-off：

```text
+5 percentage points structure coverage
换
+6 s latency
+0.6C cost
```

要不要接受，由产品要求决定。

而不是一句：

```text
Prompt Chaining 更可靠。
```

---

同样，如果发现大型 repository task 经常：

```text
underscope
```

也就是只修改了第一个看到的文件，却遗漏跨模块影响，可以加入 Orchestrator：

```text
Task
  ↓
Decompose
  ↓
Workers
  ↓
Synthesis
```

然后比较：

```text
Baseline Agent
vs
Orchestrator–Workers
```

关注：

```text
task success
missed dependency
files touched
test pass rate
token cost
wall-clock latency
```

如果动态 decomposition 把：

```text
task success
62% → 78%
```

同时成本：

```text
1.0C → 2.4C
```

这至少是可以讨论的工程决策。

如果结果却是：

```text
task success
62% → 63%

cost
1.0C → 3.1C
```

就没有理由因为：

```text
多 Agent 架构看起来完整
```

而保留它。

---

Evaluator–Optimizer 更需要这种 ablation。

假设：

```text
Generator only
quality = 84

+ 1 evaluation round
quality = 91

+ 2 rounds
quality = 92

+ 3 rounds
quality = 92
```

而成本：

```text
1.0C
1.9C
2.8C
3.7C
```

结果已经很清楚：

```text
第 1 轮 feedback
有明显价值

第 2 / 3 轮
边际收益很低
```

合理 stopping rule 可能就是：

```text
max_iterations = 1
```

而不是：

```text
循环越多越认真。
```

---

Parallelization 同样不能只看：

```text
更快
```

而应该分别记录：

```text
wall-clock latency
token usage
failure rate
aggregation quality
```

例如：

```text
Sequential

latency = 30 s
cost    = C
```

改成：

```text
Parallel

latency = 12 s
cost    = 1.1C
```

如果用户对等待时间敏感，这可能很值得。

但 Voting：

```text
1 reviewer
→ 5 reviewers
```

可能得到：

```text
latency   8 s → 10 s
cost      C   → 5.4C
recall    72% → 78%
```

是否值得，就要看漏检的业务代价。

因此不能把：

```text
parallel
```

本身当成优化指标。

---

Routing 也应该做相同检查。

假设原来：

```text
所有请求
→ Strong Model
```

成本：

$$
C_{\text{all-strong}}
$$

加入 Router：

```text
simple
→ cheap model

complex
→ strong model
```

得到：

```text
task success     94.2% → 94.0%
average cost     1.0C  → 0.55C
latency          9.2s  → 5.8s
```

那么 Router 的价值很明确。

但如果：

```text
router misclassification
```

导致任务成功率从：

```text
94%
→ 81%
```

即使成本降低一半，也可能不可接受。

所以每种 pattern 都应该建立自己的：

```text
Benefit
Cost
New Failure Mode
```

三列账。

可以整理成：

| Pattern              | 希望解决的问题         | 新增成本                                       | 新增 failure surface                          |
| -------------------- | --------------- | ------------------------------------------ | ------------------------------------------- |
| Prompt Chaining      | 单次调用过载、中间态不可观察  | 多次调用、串行 latency                            | error propagation、context duplication       |
| Routing              | 不同输入需要不同处理路径    | classifier / router call                   | misrouting、taxonomy drift                   |
| Parallelization      | 独立任务串行等待；需要多个尝试 | concurrency、更多 compute                     | conflict、straggler、aggregation error        |
| Orchestrator–Workers | 子任务无法预定义        | decomposition、worker context、runtime state | overlap、dependency、workspace、synthesis loss |
| Evaluator–Optimizer  | 一次生成质量不稳定       | 至少额外 evaluator / revision calls            | evaluator error、loop、regression             |
| Agent                | 整体路径无法合理预定义     | 更长 trajectory、更大状态空间                       | drift、tool error、termination、recovery       |

这张表比：

```text
哪个架构最先进？
```

更接近生产问题。

---

因此我更愿意把 architecture evolution 写成：

```text
Observed Failure
      │
      ▼
Smallest Useful Pattern
      │
      ▼
Evaluation
  ┌───┴─────────────┐
  │                  │
improved         no improvement
  │                  │
  ▼                  ▼
keep             remove / redesign
```

而不是：

```text
Single Agent
    ↓
Multi-Agent
    ↓
更多 Agent
    ↓
更复杂 Framework
```

每增加一个 component，都应该留下一个可检查的问题：

```text
它解决的是哪个 failure？

没有它时 baseline 是多少？

加上以后 task success 改变多少？

latency 改变多少？

token / API cost 改变多少？

它自己又引入了什么 failure mode？
```

如果这些问题没有答案，就暂时只能说：

```text
我们增加了一个架构组件。
```

还不能说：

```text
系统因此变得更可靠。
```

---

这个视角也解释了为什么 Anthropic 的五种 workflow pattern 到今天仍然有用。

真正稳定的部分并不是：

```text
2024 年应该使用哪一个 Agent framework
```

而是几个很普通的控制问题：

```text
sequence
branch
fan-out / fan-in
dynamic decomposition
feedback loop
```

模型、SDK 和工具协议会变化，但只要一个系统需要组织多次具有依赖关系的计算，这些控制结构就不会因为模型版本更新而消失。

变化的是：

```text
哪些结构还值得显式放在模型外部？
```

模型能力增强以后，原来必须拆成三次 Prompt Chaining 的任务，可能一次调用已经可以稳定完成；原来需要 Planner 的任务，模型可能自己已经能在 Agent loop 中规划；原来需要五个 specialized agents 的领域知识，也可能重新包装成 Skills 和 tools。

所以 pattern 本身也应该接受 ablation。

这与前面 Claude Code Harness 里的一个结论是一致的：

```text
Scaffolding
不是永久真理。

它应该对应
当前模型在当前任务上的
可复现 failure。
```

当模型、工具或任务分布改变以后，原来的 orchestration component 也需要重新验证。

到这里，Anthropic 五种 workflow pattern 已经可以放进同一张地图：

```text
                   Control Flow

     fixed                              dynamic
       │                                   │
       │  Prompt Chaining                  │
       │  A → B → C                        │
       │                                   │
       │  Routing                          │
       │  A → {B | C | D}                  │
       │                                   │
       │  Parallelization                  │
       │  A → {B || C || D} → Merge        │
       │                                   │
       │                Orchestrator–Workers
       │                A → generate T(x)
       │                     → Workers
       │                     → Synthesis
       │                                   │
       │  Evaluator–Optimizer              │
       │  Generate ↔ Evaluate              │
       │                                   │
       └───────────────────────────────────┘
```

这里还缺最后一块。

这些图能够告诉我们：

```text
控制流应该长什么样。
```

但它们没有自动回答：

```text
Task 状态放在哪里？
进程挂了怎么恢复？
Worker 的 workspace 怎么隔离？
谁负责权限？
Tool 的副作用怎么控制？
任务怎样取消？
CI 和 Review 这种异步反馈怎么重新进入系统？
```

这些已经不是再画一种 workflow pattern 能解决的问题。

下一节需要把 **Pattern、Harness、Specification 和 Evaluation** 的边界拆开，再解释为什么 `_index.md` 到这里应该停止，而 `spec.md`、`symphony.md` 和 verification 还各自有自己的问题要处理。

## 8. 从 Pattern 到生产 Orchestration——本文停在哪里

到这里，我们已经能用五种 pattern 描述相当多的控制结构：

```text id="border01"
A → B → C
```

是 Prompt Chaining。

```text id="border02"
      ┌→ B
A → R ┼→ C
      └→ D
```

是 Routing。

```text id="border03"
      ┌→ B ─┐
A ────┼→ C ─┼→ Merge
      └→ D ─┘
```

是 Parallelization。

```text id="border04"
A → Orchestrator
       │
       ├→ Worker 1
       ├→ Worker 2
       └→ Worker N
              │
              ▼
          Synthesis
```

是 Orchestrator–Workers。

```text id="border05"
Generate
   │
   ▼
Evaluate
   │
   ├─ pass
   │
   └─ feedback ──► Generate
```

是 Evaluator–Optimizer。

这些结构已经足以回答：

```text id="border06"
步骤是不是固定？
下一步是不是分支？
哪些工作能够并行？
子任务是不是运行时产生？
结果不合格以后要不要反馈迭代？
```

但如果真的要让一个 coding agent 连续运行几个小时，甚至让几十个任务跨进程、跨 workspace、跨 CI pipeline 同时推进，仅有这些图还远远不够。

因为图里的：

```text id="border07"
Worker
```

只是一个逻辑节点。

现实系统还必须知道：

```text id="border08"
这个 Worker 属于哪个 Task？
Task 当前是什么状态？
它在哪个 workspace 运行？
进程挂了以后谁恢复？
重复 dispatch 怎么避免？
它改过哪些文件？
它能调用哪些工具？
达到什么条件才算完成？
CI 失败以后谁重新处理？
用户取消任务以后怎么停止？
```

这些问题已经从：

```text id="border09"
Control Topology
```

进入：

```text id="border10"
Runtime Semantics
```

这也是 `_index.md` 需要停下来的位置。

### 8.1 Pattern 说明控制流长什么样，但没有替我们实现一个可靠 Runtime

假设我们已经决定使用 Orchestrator–Workers：

```text id="runtime01"
Issue
  │
  ▼
Orchestrator
  │
  ├─ Task A
  ├─ Task B
  └─ Task C
```

架构图到这里看起来已经完成。

但第一行代码写下去就会出现一个问题：

```text id="runtime02"
Task A
```

到底是什么？

最简实现可能只是：

```python id="runtime03"
tasks = [
    "inspect auth middleware",
    "inspect session storage",
    "inspect regression tests",
]
```

如果进程下一秒退出：

```text id="runtime04"
Process Crash
```

这些 task 也跟着消失。

于是首先需要区分：

```text id="runtime05"
Task Description
```

和：

```text id="runtime06"
Task State
```

一个真正进入 runtime 的任务可能至少需要：

```text id="runtime07"
id
goal
status
dependencies
workspace
attempt
result
```

例如：

```json id="runtime08"
{
  "id": "AUTH-42/session-investigation",
  "status": "running",
  "depends_on": [],
  "workspace": "/workspaces/AUTH-42-session",
  "attempt": 1
}
```

Pattern 本身没有规定这些字段。

它只告诉我们：

```text id="runtime09"
存在一个 Orchestrator
和若干 Worker。
```

至于这些 Worker 如何成为可以恢复、追踪和调度的 runtime object，是另一层设计。

---

第二个问题是 **ownership**。

假设 scheduler 每隔 10 秒检查一次：

```text id="runtime10"
哪些 task 还没有执行？
```

第一次检查：

```text id="runtime11"
AUTH-42
→ 尚未执行
→ dispatch Worker A
```

Worker A 还没有完成时，第二次 poll 又来了：

```text id="runtime12"
AUTH-42
→ 看起来仍未完成
→ dispatch Worker B
```

现在同一个 issue 出现两个 worker：

```text id="runtime13"
AUTH-42
  ├─ Worker A
  └─ Worker B
```

两者可能同时修改同一份代码。

所以 runtime 必须有某种 claim / ownership 语义：

```text id="runtime14"
Unclaimed
   │
   ▼
Claimed
   │
   ▼
Running
```

OpenAI 公开的 Symphony `SPEC.md` 就专门区分了：

```text id="runtime15"
Unclaimed
Claimed
Running
RetryQueued
Released
```

并明确说明 orchestrator 是唯一修改 scheduling state 的组件。

这已经不是：

```text id="runtime16"
Orchestrator–Workers pattern
```

本身能够推导出来的细节。

它属于：

```text id="runtime17"
这个 pattern 怎样被可靠执行。
```

---

第三个问题是 **workspace**。

在纯文本任务中：

```text id="runtime18"
Worker A
Worker B
```

也许只是两个独立模型调用。

coding agent 不一样。

它们会产生真实副作用：

```text id="runtime19"
read file
edit file
run command
install dependency
git commit
```

如果两个 Worker 共用：

```text id="runtime20"
/repo
```

那么：

```text id="runtime21"
Worker A:
修改 auth.ts

Worker B:
修改 session.ts
```

看起来没有冲突，但 B 运行测试时看到的可能已经包含 A 尚未完成的修改。

更糟的情况是：

```text id="runtime22"
Worker A
修改 auth.ts

Worker B
也修改 auth.ts
```

于是逻辑上的：

```text id="runtime23"
parallel tasks
```

变成文件系统里的：

```text id="runtime24"
shared mutable state
```

OpenAI 的 Symphony 为每个 active issue 建立独立 agent workspace，就是把这个 runtime 问题显式化：Issue 不只是 prompt，它对应一个可以持续存在的执行空间。

因此：

```text id="runtime25"
Parallelization
```

只能告诉我们：

```text id="runtime26"
这些工作在依赖关系上可以同时运行。
```

它没有自动保证：

```text id="runtime27"
这些工作在副作用层面能够安全同时运行。
```

后一个问题需要 workspace isolation、ownership 和 merge policy。

---

第四个问题是 **failure recovery**。

最简单的 workflow：

```python id="runtime28"
result = await worker(task)
```

默认：

```text id="runtime29"
worker 启动
→ worker 完成
```

现实执行却可能是：

```text id="runtime30"
worker 启动
→ API timeout
```

或者：

```text id="runtime31"
worker 启动
→ process crash
```

或者：

```text id="runtime32"
worker 启动
→ 20 分钟没有任何进展
```

或者：

```text id="runtime33"
worker 完成
→ CI 失败
```

这几个 failure 的处理方式并不一样。

例如：

```text id="runtime34"
API timeout
→ retry
```

可能合理。

但：

```text id="runtime35"
测试稳定失败
→ 原样 retry
```

只会重复同样的错误。

因此 runtime 需要区分：

```text id="runtime36"
transient failure
task failure
stalled execution
external rejection
```

OpenAI 的 Symphony 公开描述中就包括：

```text id="runtime37"
crash / stall restart
bounded concurrency
retry
reconciliation
```

以及 CI、rebase、conflict 和 flaky check 等任务完成后的外部反馈。

这些都说明：

```text id="runtime38"
Worker returned
```

不一定意味着：

```text id="runtime39"
Task permanently done
```

这一点在长期运行系统中尤其关键。

---

第五个问题是 **外部状态会变化**。

普通 Prompt Chain 可以近似看成：

```text id="runtime40"
Input
  ↓
Workflow
  ↓
Output
```

但长任务执行期间，世界并不会冻结。

例如：

```text id="runtime41"
Agent 正在处理 issue
```

同时可能发生：

```text id="runtime42"
用户关闭 issue
PR 收到 review comment
CI 新增失败
main branch 前进
依赖任务完成
需求状态改变
```

所以 runtime 不只是执行：

```text id="runtime43"
plan once
→ run forever
```

它还需要：

```text id="runtime44"
reconcile
```

即比较：

```text id="runtime45"
我内部认为的状态
```

和：

```text id="runtime46"
外部控制面的当前状态
```

是否仍然一致。

OpenAI 在 Symphony 中把 Linear 作为 control plane，并让 orchestrator 持续读取 issue tracker 状态；如果 issue 已经不再 eligible，正在执行的 run 也需要停止或释放。

这种逻辑已经很接近传统 distributed system 中熟悉的 reconciliation loop：

```text id="runtime47"
Desired State
     │
     ▼
Current State
     │
     ▼
Reconcile
     │
     ▼
Action
```

这里没有必要把 Symphony 直接等同于 Kubernetes controller；两者的状态模型、容错语义和一致性保证都不同。

更有限的类比是：

> 长运行 Agent Orchestrator 不只执行一次 workflow，它还需要持续比较外部任务状态和自己的 runtime state，并据此决定 dispatch、stop、retry 或 release。

---

第六个问题是 **权限与副作用**。

五种 pattern 可以画：

```text id="runtime48"
Worker
  │
  ▼
Tool
```

但没有回答：

```text id="runtime49"
这个 Tool 能不能执行？
```

例如 coding worker 请求：

```text id="runtime50"
rm -rf build/
```

和：

```text id="runtime51"
git push --force
```

虽然都是 tool call，但风险完全不同。

真正的 Harness 还需要处理：

```text id="runtime52"
schema validation
permission
sandbox
effect boundary
credential exposure
cancellation
```

Orchestration pattern 只规定：

```text id="runtime53"
谁在什么时候可能调用工具。
```

它没有定义：

```text id="runtime54"
系统是否允许这个动作真实发生。
```

这也是为什么 Claude Code 那篇 Harness 文章里 Tool 需要被理解成模型和真实副作用之间的 contract，而不只是普通 function calling。

---

因此可以把两层先分开：

```text id="runtime55"
Orchestration Pattern
│
│ 描述
│
├─ sequence
├─ branch
├─ fan-out
├─ decomposition
└─ feedback loop
```

对比：

```text id="runtime56"
Harness / Runtime
│
│ 负责
│
├─ state
├─ persistence
├─ scheduling
├─ isolation
├─ permission
├─ retry
├─ cancellation
├─ recovery
└─ observability
```

这里的 `Harness / Runtime` 是本文为了和前面 Claude Code 学习笔记保持一致使用的工程抽象，不代表行业里所有框架都采用完全相同的术语边界。

但这个区分足够解决一个常见误会：

```text id="runtime57"
我画出了 Multi-Agent Workflow
```

不等于：

```text id="runtime58"
我已经设计出了一个
可长期运行的 Agent 系统。
```

前者主要解决控制拓扑。

后者还要解决：

```text id="runtime59"
这些节点怎样在现实世界里
可靠地活下去。
```

这就是为什么 Anthropic 的五种 pattern 可以成为 orchestration 的入口，却不能成为整篇 Agent Runtime 的终点。

### 8.2 Pattern、Spec、Harness、Eval 分别回答不同问题

还有四个概念特别容易在 Agent 工程讨论里混在一起：

```text id="boundary60"
Orchestration Pattern
Specification
Harness / Runtime
Evaluation / Verification
```

它们都可能出现在同一个系统里，但负责的问题不同。

还是用一个 coding task：

```text id="boundary61"
修复 refresh token rotation 后偶发 401，
增加 regression test，
不要改变现有 session API。
```

来看这四层分别承担什么。

---

#### Specification：什么才算完成？

原始需求：

```text id="boundary62"
修复偶发 401。
```

对于真正执行来说太宽。

因为 agent 可以：

```text id="boundary63"
修改 retry 次数
```

然后声称：

```text id="boundary64"
“现在发生概率更低了。”
```

这是不是修复？

如果我们不能回答，runtime 也无法替我们回答。

所以 Spec 应该逐渐把意图变成可检查的约束，例如：

```text id="boundary65"
Goal:
消除 refresh token rotation 后
使用新 token 访问 session endpoint 时的错误 401。

Constraints:
- 不改变现有 session API schema；
- 旧 refresh token 在 rotation 后必须失效；
- 新 token 必须能够继续访问 session endpoint。

Acceptance:
- 增加 second-refresh regression test；
- 现有 session integration tests 全部通过。
```

Spec 回答的是：

> **What should be true when this task is complete?**

它不是在规定：

```text id="boundary66"
必须先读 auth.ts
再读 session.ts
再开三个 Agent
```

那些属于 execution strategy。

因此：

```text id="boundary67"
Spec
≠
Workflow
```

一个好的 Spec 可以被：

```text id="boundary68"
Single Agent
```

执行，也可以被：

```text id="boundary69"
Orchestrator–Workers
```

执行。

甚至以后换了模型、工具或 orchestration framework，Spec 的主要验收条件仍然可能成立。

---

#### Orchestration Pattern：这项工作怎样被组织？

拿到同一个 Spec 后，我们才决定：

```text id="boundary70"
一个 Agent 直接做？
```

还是：

```text id="boundary71"
先调查
→ 再实现
→ 再验证
```

还是：

```text id="boundary72"
Orchestrator
  ├─ backend investigation
  ├─ session investigation
  └─ test investigation
```

Pattern 回答的是：

> **How should the work be decomposed and connected?**

它关心：

```text id="boundary73"
sequence
branch
parallelism
dynamic decomposition
feedback
```

但不负责定义：

```text id="boundary74"
最终什么结果才满足业务要求。
```

---

#### Harness / Runtime：这些工作怎样真正运行起来？

假设已经选择：

```text id="boundary75"
Orchestrator–Workers
```

Harness 接下来才处理：

```text id="boundary76"
创建哪个 session？
workspace 在哪里？
Task ID 是什么？
最多并发几个？
进程挂了怎么办？
工具权限是什么？
怎样记录日志？
怎样 cancel？
怎样 resume？
```

即：

> **How does this execution survive contact with the real environment?**

这层特别容易被架构图隐藏。

图里一个：

```text id="boundary77"
Worker
```

在 runtime 里可能展开成：

```text id="boundary78"
Task State
+
Workspace
+
Agent Session
+
Tool Policy
+
Context
+
Logs
+
Retry State
+
Cancellation
```

OpenAI 的 Symphony 已经越过单纯 pattern 讨论，进入了这一层：公开 `SPEC.md` 明确把自己界定为 scheduler / runner 和 tracker reader，并规定 issue polling、bounded concurrency、per-issue workspace、retry、reconciliation 和 orchestration state。

因此 `symphony.md` 不应该再花大量篇幅重新解释：

```text id="boundary79"
什么是 Orchestrator–Workers。
```

这篇 `_index.md` 已经完成了那个任务。

`symphony.md` 更值得回答的是：

```text id="boundary80"
当任务变成长期存在的 runtime object 后，
怎样调度、隔离、恢复和接收外部反馈？
```

---

#### Evaluation / Verification：我们凭什么说它真的完成了？

最后还有：

```text id="boundary81"
Agent:
“任务已经完成。”
```

这句话本身不能成为验收证据。

如果 Spec 要求：

```text id="boundary82"
old refresh token invalid
```

就应该实际验证。

如果要求：

```text id="boundary83"
session API schema unchanged
```

就应该运行相应测试或 schema comparison。

因此 Evaluation / Verification 回答：

> **How do we know the result satisfies the requirement?**

可以表示成：

```text id="boundary84"
Spec
 │
 │ defines
 ▼
Acceptance Criteria
 │
 │ checked by
 ▼
Verifier / Evaluator
 │
 ▼
Evidence
 │
 ▼
Pass / Fail / Unknown
```

这里最好再保留 Macro 6 已经做过的区分：

```text id="boundary85"
能确定性验证
→ tests / parser / static checks / environment

需要语义评价
→ evaluator
```

而不是全部交给另一个 LLM 判断。

---

把四层放到一张表里：

| 层                         | 主要问题             | 典型对象                                       |
| ------------------------- | ---------------- | ------------------------------------------ |
| Specification             | **什么叫完成？**       | goal、constraints、acceptance criteria       |
| Orchestration Pattern     | **工作之间是什么控制关系？** | chain、route、fan-out、decomposition、feedback |
| Harness / Runtime         | **这些工作怎样可靠执行？**  | state、workspace、permission、retry、recovery  |
| Evaluation / Verification | **凭什么认为完成了？**    | tests、graders、evidence、pass/fail           |

还可以再压成：

```text id="boundary86"
Spec
定义正确状态

Orchestration
组织到达这个状态的工作

Harness
让这些工作真实运行

Eval / Verification
判断是否真的到达这个状态
```

这四层不是严格的行业标准分层，而是本文为了避免职责混淆使用的工作模型。

真正写系统时它们会互相交叉。

例如 Spec 中的：

```text id="boundary87"
Acceptance Criteria
```

会影响 Evaluator。

Harness 里的：

```text id="boundary88"
Tool Policy
```

会限制 Orchestrator 能创建什么任务。

Verification 失败以后：

```text id="boundary89"
test failed
```

又可能重新进入 orchestration：

```text id="boundary90"
Failure Evidence
      │
      ▼
new task / retry / revision
```

所以关系不是一次性的：

```text id="boundary91"
Spec
→ Orchestration
→ Harness
→ Eval
→ End
```

更接近：

```text id="boundary92"
             Spec
              │
              ▼
        Orchestration
              │
              ▼
           Runtime
              │
              ▼
         Verification
          │         │
        pass      failure
          │         │
          ▼         └──────► Orchestration
        Done
```

但每一层仍然应该有自己的主要职责，否则所有问题最后都会被塞进一个：

```text id="boundary93"
Agent Prompt
```

里面。

---

这也给当前 `agent/orchestration/` 目录划出了比较清楚的分工。

```text id="boundary94"
agent/orchestration/
│
├── _index.md
├── vibe.md
├── spec.md
└── symphony.md
```

这篇 `_index.md` 负责建立通用控制模式：

```text id="boundary95"
Prompt Chaining
Routing
Parallelization
Orchestrator–Workers
Evaluator–Optimizer
```

以及：

```text id="boundary96"
什么时候应该继续保持 workflow，
什么时候任务路径已经动态到更适合 Agent。
```

它回答的是：

> **我可以怎样组织模型调用和任务之间的控制关系？**

---

`spec.md` 不需要重新介绍五种 pattern。

它更应该回答：

> **在让 Agent 开始工作以前，怎样把自然语言意图变成能够执行和验收的任务规范？**

对应：

```text id="boundary97"
Intent
  ↓
Specification
  ↓
Constraints
  ↓
Acceptance Criteria
```

于是 Orchestrator 拿到的不是：

```text id="boundary98"
“帮我把登录系统弄好一点。”
```

而是边界更明确的 task contract。

---

`symphony.md` 再向下走一层。

OpenAI 在 2026 年公开的 Symphony 把 issue tracker 变成 coding agent 的 control plane：active task 对应独立 workspace，orchestrator 持续读取任务状态、管理并发和 retry，agent 还能继续处理 CI、review、rebase 和 PR landing 等后续反馈。OpenAI 将其定位为 intentionally minimal orchestration layer，并以语言无关的 `SPEC.md` 提供参考实现边界。

因此 `symphony.md` 应该回答：

> **当任务不再绑定一个聊天 session，而成为长期存在的工作项以后，怎样持续保证该做的任务有人执行？**

这时讨论的对象变成：

```text id="boundary99"
Issue
Workspace
Claim State
Agent Session
Dependency
Retry
CI
Review
Reconciliation
```

与当前 `_index.md` 的五种抽象 pattern 已经处于不同层级。

---

而 verification / eval 方向的文章负责另一端：

```text id="boundary100"
Agent 做完了
```

以后：

```text id="boundary101"
怎么证明？
```

例如：

```text id="boundary102"
unit tests
integration tests
environment state
grader
LLM evaluator
human review
```

这部分不应该由 orchestration 文章代替。

Orchestrator 可以决定：

```text id="boundary103"
现在应该启动 verifier。
```

但：

```text id="boundary104"
什么证据足以证明任务成功
```

仍然属于 verification contract。

---

把目录放到同一条工作链上，就得到：

```text id="boundary105"
User Intent
    │
    ▼
Specification
    │
    │  什么叫做对？
    ▼
Task
    │
    ▼
Orchestration Pattern
    │
    │  工作怎么组织？
    ▼
Harness / Runtime
    │
    │  怎么真实执行并持续运行？
    ▼
Environment
    │
    ▼
Verification / Evaluation
    │
    │  真的满足要求了吗？
    │
    ├─ No ───────────────► Orchestration
    │
    └─ Yes
         │
         ▼
        Done
```

这张图也说明为什么 Agent Engineering 很难被某一个：

```text id="boundary106"
更聪明的 Prompt
```

或者：

```text id="boundary107"
更复杂的 Multi-Agent Graph
```

单独解决。

如果 Spec 模糊：

```text id="boundary108"
Agent 不知道什么叫完成。
```

如果 orchestration 不合适：

```text id="boundary109"
任务被错误拆分或者产生不必要等待。
```

如果 Harness 薄弱：

```text id="boundary110"
任务可能在 crash、权限、workspace 或外部状态变化时失控。
```

如果 Verification 薄弱：

```text id="boundary111"
系统可能只是相信 Agent 自己宣布完成。
```

这四类 failure 的修复位置不同。

把它们全部归因于：

```text id="boundary112"
模型不够强
```

会让调试方向变得模糊。

---

Anthropic 在 *Building effective agents* 开头建议：先寻找能够解决问题的最简单方案，只有当任务确实需要时才增加 agentic complexity；workflow 更适合边界清晰、需要 predictable execution 的任务，而 agent 则适合执行路径需要模型根据环境动态决定的情况。

五种 pattern 的价值也就在这里。

它们没有提供一套：

```text id="boundary113"
2026 年最先进 Agent 架构
```

而是给出了几个比较稳定的控制结构：

```text id="boundary114"
sequence
route
parallelize
decompose
evaluate
```

以后再看到新的 Agent framework，可以先暂时忽略它的类名和 DSL，问几个更基础的问题：

```text id="boundary115"
它的 task 是怎样产生的？

控制路径是谁决定的？

哪些节点能够并行？

状态保存在哪里？

失败以后怎样恢复？

完成条件来自哪里？

最后由什么证据证明成功？
```

前四个问题开始进入 orchestration 和 runtime，后两个问题连接 specification 与 verification。

回答完这些问题以后，一个看起来全新的框架，往往也能重新落回本文建立的几个基本结构里。

这就是 `_index.md` 在这里需要完成的任务。

再往下，就不继续增加新的 pattern 名词，而是分别进入这些结构在真实 Agent 工程中的具体实现。
