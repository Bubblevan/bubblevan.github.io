---
title: "从 Vibe 到 SDD：我为什么不再直接让 Coding Agent 开始写代码"
weight: 2
---

## 1. 原来那套 PRD → TRD → Tasks，其实只解决了一半问题
### 1.1 我以前已经不太敢直接把一句需求丢给 Coding Agent

我最早用 Codex、Claude Code 这类 Coding Agent 时，也试过最省事的方式：

```text
帮我实现Yuedong的前端HomePage模块。
```

或者稍微具体一点：

```text
给 Hi-Agent 加一个 Context Engineering 模块，
支持 token budget、context selection 和 trace。
```

这种 Prompt 很适合做 demo。Agent 会搜仓库、建文件、补代码、跑测试，十几分钟后给出一个看起来相当完整的 diff。

问题通常不是它完全写不出来，而是任务一旦跨过几个文件，我开始很难回答：

```text
它现在做的，
还是不是我一开始想做的东西？
```

于是后来我的习惯逐渐变成：

```text
PRD
 ↓
TRD
 ↓
拆成 6～8 个 Tasks
 ↓
一次只让 Agent 做一个 Task
 ↓
Test
 ↓
看 Diff
```

这套方法不是错误路线。

PRD 至少会迫使我先回答“为什么做、准备做到哪里、不做什么”；TRD 把接口、模块边界和技术选择从聊天记录里拿出来；Task 拆分则限制单次 Agent 修改的跨度。

相比：

```text
帮我做一个 Agent Memory
```

我更愿意给它：

```text
Task 3：实现 Context Selector

输入：
- ContextItem[]
- available_input_tokens

要求：
- required item 不能静默丢弃
- optional item 可以按策略裁剪
- 输出 selected / dropped
- 超过 hard budget 时明确失败
```

至少到了这一步，我和 Agent 已经不是靠一句自然语言共同猜需求。

但我后来发现，我真正依赖的并不是：

```text
PRD
TRD
6～8 Tasks
```

这些名字。

尤其“6～8 个任务”只是我为了控制工作跨度形成的经验值。一个需求拆成 5 个还是 11 个任务，本身不能说明它有没有被定义清楚。

我真正依赖的是另一件事：

> **在 Agent 开始改代码以前，先把原本只存在于我脑中的目标、限制和完成条件写出来。**

只是当时我还没有把这件事叫作 Spec。

### 1.2 任务拆小以后，“Done”仍然可能没有定义

PRD、TRD 和 Task 帮我控制了输入，却没有自动解决另一个问题：**什么时候算做完？**

例如我可以把任务写成：

```text
Task 3：实现 Context Selector
```

Agent 很容易完成它：

```text
- 新建 selector.py
- 实现 select_items()
- 添加排序逻辑
- 更新 import
- pytest passed
```

从实现清单看，它确实做完了。

但如果我真正关心的是：

```text
required context 永远不能因为预算不足被静默删除
```

那“存在 `select_items()`”和“相关测试是绿色”都还不够。

我至少还要继续问：

```text
required 和 optional 怎么区分？

required 本身已经超过 hard budget 怎么办？

是抛错，还是截断？

两个 item ID 冲突时怎么办？

selected 和 dropped 能不能同时出现同一个 item？

total_input_tokens 是估算值还是最终值？

谁验证这些不变量？
```

这些问题如果没有提前写出来，Agent 仍然必须自己补答案。

更麻烦的是，它补出的答案往往完全合理。

比如 hard budget 超限时，它可以：

```text
方案 A：把最后一个 required item 截掉
方案 B：继续超预算
方案 C：抛出异常
方案 D：压缩 required item
```

四种实现都能写出能运行的代码。

但它们对应的是四种不同的产品语义。

此时失败的根因已经不是“Agent 不会写代码”，而是我只给了它一个 **implementation task**，没有给出足够明确的 **correctness contract**。

这也是我后来开始重新看待“任务拆分”的原因。

过去我判断一个 Task 是否合格，主要看它够不够小：

```text
一天能不能做完？
文件是不是太多？
能不能一次交给 Agent？
```

现在我会多问一句：

```text
这个 Task 完成以后，
有没有一组不用猜的事实可以判断它是否成立？
```

如果没有，那么任务再小也可能只是：

```text
一个更小的模糊需求
```

### 1.3 “六到八个任务”不是规则，可独立验证才是

因此，我现在不会再把：

```text
拆成 6～8 个 Tasks
```

当作 Coding Agent 工作流里的规则。

数量仍然有用。它可以提醒我不要一次把半个仓库交给 Agent，但真正决定 Task 边界的是依赖和验证。

例如下面这个任务：

```text
Task 3：实现 Context 模块
```

范围看起来只有一句话，实际上里面至少混着：

```text
ContextItem 数据结构
Token Budget
Selection Policy
Required Preservation
Ordering
Trace
Formatting
Provider Payload
```

把它机械拆成八项也没有意义。

更合适的拆法，是找到一个能单独成立、也能单独失败的行为边界。例如：

```text
Task：实现 Required Context Preservation

前置：
ContextItem 已经能区分 required / optional

行为：
1. required items 优先进入 selected
2. optional items 可以因预算被 dropped
3. required items 本身超过 hard budget 时明确失败
4. selected 与 dropped 不得共享 item ID

验证：
- required preservation case
- optional trimming case
- hard-budget failure case
- duplicate / partition invariant case
```

现在 Agent 得到的不只是：

```text
写一个 selector
```

而是一组可以被反驳的声明。

只要其中一个 case 不成立，我就不能把这个 Task 标记为完成。

这种变化看起来只是 Task 写得更详细，实际改变的是任务的中心：

```text
以前：

我要 Agent 写什么代码？
        ↓
拆文件
        ↓
拆功能
        ↓
跑测试
```

变成：

```text
现在：

最终哪些事实必须成立？
        ↓
怎样观察这些事实？
        ↓
实现需要哪些决策？
        ↓
哪些工作可以独立完成并验证？
```

到这里，我才开始真正理解后来在 OpenSpec 和 Spec Kit 里反复看到的那件事。

它们并不是单纯在教人：

```text
写更多 Markdown
```

它们试图把 Coding Agent 开工以前那段经常被压缩成一句 Prompt 的过程，拆成几个职责不同的工件：

```text
为什么改
什么必须成立
准备怎么改
分成哪些工作
怎样证明改对了
```

这也就是下一节要先解决的问题：**Proposal、Spec、Design、Tasks 和 Verification 为什么不能继续塞在一份万能 PRD / TRD 里。**

可以。之后我都按这种形式给你：**一整块可以直接复制进 Markdown 的正文**，不再把说明和正文混在一起。

下面继续重写 **Macro 2**。这一版不继承旧正文的措辞，只保留 Macro 1 已经建立的叙事：**我原来已经会写 PRD/TRD/Tasks，但后来发现“任务拆小”仍然不能回答“什么算正确”，于是开始拆分不同工件的责任。**

## 2. 我后来才开始把 Spec、Design、Tasks 和 Verification 分开

### 2.1 PRD 和 TRD 最大的问题，不是它们太长，而是什么都能往里面塞

在我原来的工作流里，PRD 和 TRD 基本承担了所有前置思考。

一个稍复杂的需求通常会写成：

```text
PRD
├── 背景
├── 目标
├── 用户场景
├── 功能要求
├── 非功能要求
└── 验收标准

TRD
├── 当前架构
├── 技术方案
├── 数据结构
├── API
├── 文件改动
├── 测试
└── Tasks
````

对于个人项目，这种方法很好用。文件数量少，我也知道每一段是谁写的、为什么存在，不需要为了“规范”再维护十几个目录。

问题出现在 Agent 开始真正消费这些文档以后。

比如我在 TRD 里写：

```text
Context Selector 优先保留 required items，
再根据 priority 和 token budget 选择 optional items。

为了让行为容易理解，V1 使用确定性的贪心策略，
暂时不做 knapsack。
```

这里其实已经混进了至少三种完全不同的信息。

第一句：

```text
required items 必须优先保留
```

更接近系统必须满足的行为。

第二句：

```text
根据 priority 和 token budget 选择 optional items
```

已经开始涉及机制。

第三句：

```text
V1 使用确定性的贪心策略，不做 knapsack
```

则是一次明确的设计选择。

如果把它们都叫“TRD 内容”，人当然看得懂，但 Agent 很容易把三句话理解成同一级别的硬要求。以后即使我发现另一个 selector 算法更合适，它也可能继续把“贪心”当成不能改变的产品约束。

反过来也一样。

如果我只写：

```text
required items 必须保留
```

Agent 还不知道：

```text
required items 总长度已经超过 hard budget 时怎么办？
```

这时它必须补设计。

它可以选择：

```text
truncate
compress
ignore budget
raise error
```

但这些选择一旦会改变外部行为，就不能只是藏在实现里。

所以我后来开始觉得，“PRD / TRD 到底应该叫什么”不是最值得纠结的问题。真正要分清的是：

> **这句话究竟在定义正确性，还是在记录一种实现选择？**

我现在更愿意把常见工件理解成几个不同的问题：

| 工件            | 主要回答的问题            |
| ------------- | ------------------ |
| Proposal      | 为什么要发生这次变化，影响范围是什么 |
| Spec          | 变化完成后，哪些行为和约束必须成立  |
| Design / Plan | 在当前系统里准备怎样实现这些要求   |
| Tasks         | 实现工作怎样切成有依赖关系的执行单元 |
| Verification  | 用什么证据判断要求已经成立      |

这不是要求每次开发都创建五份 Markdown。

一个很小的改动完全可以把这些内容写在同一个 issue 里。

例如：

```markdown
## Requirement

空搜索结果必须显示 Empty State，而不是白屏。

## Design

复用现有 EmptyState 组件。

## Task

修改 SearchResultView 的 empty branch。

## Verify

运行对应 component test，并手工检查空结果页面。
```

它仍然只有一个文件。

关键是四段内容不会互相冒充。

这也是我现在理解的 artifact boundary：**分的不是 Markdown 文件，而是决策责任。**

### 2.2 Spec 最难写的部分，是把“我要什么”改成“我能观察到什么”

当我开始区分 Spec 和 Design 后，第二个问题马上出现了：

```text
什么样的句子才算 Spec？
```

最开始我很容易写成：

```text
实现 Context Budget
支持可靠的 Context Selection
保证重要上下文不会丢失
优化 Context 使用效率
```

这些句子作为方向没有问题，但它们还不足以判断实现是否正确。

例如：

```text
保证重要上下文不会丢失
```

什么叫“重要”？

是：

```text
priority >= 8
```

还是：

```text
required == true
```

还是某个模型动态判断出来的 relevance？

如果 budget 不够，所谓“不丢失”是：

```text
允许超预算
```

还是：

```text
整个请求失败
```

如果这些问题没有答案，“保证重要上下文不会丢失”只是一个愿望。

我后来越来越习惯把要求改写成可以观察的场景。

比如 Required Context Preservation，可以写成：

```text
Given:
- available input budget = 100 tokens
- required item A = 40 tokens
- optional item B = 80 tokens

When:
- Selector 执行 selection

Then:
- A 必须出现在 selected
- B 可以出现在 dropped
- selected token 总量不得超过 available budget
```

再补一个失败场景：

```text
Given:
- available input budget = 100 tokens
- required item A = 120 tokens

When:
- Selector 执行 selection

Then:
- selection 必须明确失败
- 不得静默截断 required item
- 不得把 required item 移入 dropped 后继续返回成功结果
```

到这里，要求才从：

```text
required 很重要
```

变成：

```text
什么输入下，系统必须产生什么可观察结果。
```

这并不意味着所有 Spec 都必须写成完整的 BDD。

我并不打算在博客项目里把每一条要求都机械写成：

```text
Given
When
Then
```

它更像一种自检方式。

每次写完 Requirement，我会问：

```text
给我一个具体输入。

告诉我从哪个入口执行。

告诉我应该看到什么输出或状态。

再告诉我什么结果一定不能出现。
```

如果这四个问题完全答不出来，这条 Requirement 很可能还停留在目标描述，而没有进入可验证状态。

这在性能要求里尤其明显。

例如：

```text
应用必须快速启动。
```

它甚至不能算一个完整的验收条件。

改成：

```text
应用冷启动时间必须小于 800 ms。
```

已经好了一步，但仍然有一堆没有定义的东西：

```text
什么叫冷启动？
从哪个事件开始计时？
哪个状态算启动完成？
在哪台机器测？
测几次？
取平均值、P95 还是最差值？
CI 测，还是本地测？
```

这些问题不是为了挑字眼。

如果没有它们，Agent 可以跑一个完全不同的 benchmark，然后很真诚地告诉我：

```text
Requirement satisfied.
```

所以我现在会把 acceptance criteria 理解成 Spec 和现实世界之间的第一个接口。

它负责把：

```text
我希望系统变成这样
```

继续压缩成：

```text
出现这些输入和条件时，
我应该能看到这些事实。
```

只有到了这一步，后面的测试、日志、浏览器操作和人工检查才知道自己究竟应该证明什么。

### 2.3 Test Passed 不是终点，测试必须能追回它在证明哪条 Requirement

我过去还有一个很容易形成错觉的习惯：

```text
pytest 全绿
=
任务完成
```

对于边界清楚的小函数，这个判断经常成立。

但任务一复杂，问题就变成：

```text
这些 test 到底在证明什么？
```

假设一个 Agent 完成修改以后告诉我：

```text
89 passed
```

这个数字当然有价值。

它至少证明：

```text
本次运行的 89 个测试没有失败。
```

但它没有自动证明：

```text
所有 Requirement 都有对应测试
```

也没有证明：

```text
测试覆盖了真实环境里的关键行为
```

更不能自动推出：

```text
产品需求已经全部完成。
```

因此，我现在越来越在意一条从需求一直延伸到证据的链：

```text
Intent
  ↓
Requirement
  ↓
Acceptance Criteria
  ↓
Design Decision
  ↓
Task
  ↓
Implementation
  ↓
Verification Evidence
```

拿 Required Context Preservation 来看，这条链可以具体到：

```text
Intent
避免长 Context 编译时静默丢失必要信息
        ↓
Requirement
required item 不得被普通裁剪策略删除
        ↓
Acceptance
required + optional 超预算时，
optional 可被删除，但 required 必须保留
        ↓
Design
Selector 先处理 required，
剩余预算再用于 optional
        ↓
Task
实现 Required Context Preservation
        ↓
Implementation
select_items(...)
        ↓
Evidence
对应 selector tests 通过
```

如果链条在不同位置断掉，会产生完全不同的问题。

例如：

```text
Intent
  ↓
Requirement
  ✕
Acceptance
```

这时我知道“想要什么”，但没有明确怎么判断。

结果很容易变成：

```text
看起来差不多就算完成。
```

如果是：

```text
Requirement
  ↓
Acceptance
  ✕
Design
```

则可能出现一个 Requirement 有清楚验收标准，但 Agent 的实现路线为什么能满足它没有被解释。

如果是：

```text
Design
  ↓
Task
  ✕
Evidence
```

就会出现我以前经常看到的情况：

```text
[x] Task 1
[x] Task 2
[x] Task 3
```

所有 checkbox 都打完了，却没人能指出：

```text
Task 2 完成的证据在哪里？
```

我现在不会要求每个项目都建立一套需求管理数据库，把 Requirement ID 从 PRD 一路贴到每个 commit。

对于 Hi-Agent 这种学习项目，那会制造比问题本身更大的维护成本。

但至少对关键行为，我希望以后能回答三个问题：

```text
1. 这段实现服务于哪条 Requirement？
2. 这条 Requirement 的完成条件是什么？
3. 哪个测试、日志或运行结果证明了它？
```

回答不出来，就说明某一段上下文已经丢了。

这种 traceability 对 Agent 比对人类开发者更重要一点。

人写完代码以后，往往还记得：

```text
我当时为什么这样改。
```

Agent session 结束以后，这种隐性记忆几乎没有可靠存在的理由。

下一个 Agent 看到的可能只剩：

```text
代码
测试
几个 Markdown
Git history
```

如果 Requirement、Design 和 Evidence 之间没有显式关系，它只能重新推断。

这又回到了 Macro 1 的问题：

```text
让 Agent 猜一次，
就会留下以后继续猜的空间。
```

因此，SDD 在这里开始显露出和我原来 PRD → TRD → Tasks 工作流不同的地方。

我以前更关心的是：

```text
怎样把工作拆开，
让 Agent 一次不要做太多。
```

现在还会再加一条：

```text
怎样让每一次实现，
都能追回它为什么存在，
以及凭什么认为它已经完成。
```

而 OpenSpec 给我的第一个直接启发，正好不是“换一个 CLI 写 Spec”，而是把这种关系进一步落到一次**变更**上：不要每次重新描述整个项目，而是明确记录当前系统是什么、这一次准备改变什么，以及变化完成以后怎样回到新的稳定状态。

## 3. OpenSpec：我开始把“这次改什么”当成一个独立对象

前面把 Spec、Design、Tasks 和 Verification 分开以后，还有一个问题没有解决。

假设 Hi-Agent 现在已经存在一套 Context 行为：

```text
ContextItem
    ↓
Budget
    ↓
Selector
    ↓
Compiler
    ↓
Message Structure
    ↓
Provider Payload
```

现在我要修改其中一个规则：

```text
required item 超过 hard budget 时，
从“继续编译”改成“明确失败”。
```

最直接的做法，是重新打开 PRD 或 TRD，在原来的章节里修改几句话。

这样当然能工作。

但半年以后再看，我很难回答：

```text
这条规则是什么时候加进去的？

为什么从原来的行为改成现在这样？

当时还考虑过哪些方案？

这次变更只影响 Selector，
还是连 Compiler、Trace 和测试一起改变？

哪些内容是修改以前就存在的，
哪些是这次新增的？
```

如果每次需求都直接改“大文档”，历史最终只剩下：

```text
现在是什么样
```

而逐渐丢失：

```text
为什么变成这样
```

OpenSpec 给我最直接的启发，就在这里。

它没有把一次开发理解成：

```text
打开总需求文档
→ 修改几段
→ 开始写代码
```

而是把 **Change 本身变成一等工件**。

当前 OpenSpec 的目录模型可以压缩成两个部分：

```text
openspec/
├── specs/
│   └── 当前系统已经成立的行为
│
└── changes/
    └── 当前正在讨论或实施的变化
```

官方文档对两者的定义很直接：

- `openspec/specs/` 描述系统**现在怎样工作**；
- `openspec/changes/` 中的每个目录表示一次独立变化；
- Change 内部保存 proposal、delta specs、design、tasks 等工件；
- Change 完成并归档后，delta 会合入主 specs，新的行为成为“现在的事实”。

参见：[OpenSpec Core Concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/overview.md)。

这个结构比“多建几个 Markdown”更值得学，因为它把两种时间状态分开了：

```text
Base Spec
当前已经成立的契约

        +

Change Delta
这一次准备改变的契约
```

对于一个已经存在的项目，我通常不需要重新说明整个 Context 系统。

我只需要描述这次 diff。

---

### 3.1 Base Spec 与 Delta Spec：不要每次修改都重新描述整个系统

假设当前 Base Spec 已经有：

```markdown
### Requirement: Required context preservation

The compiler SHALL preserve every required context item
when the required set fits within the hard input budget.
```

现在我发现一个之前没有说清楚的边界：

```text
required items 本身已经超过 hard budget 怎么办？
```

如果沿用我过去写 PRD 的习惯，我可能重新整理整个 Context Budget 章节，把新规则揉进去。

OpenSpec 更倾向于只描述变化。

例如：

```markdown
## ADDED Requirements

### Requirement: Required context overflow

The selector SHALL fail explicitly when required context items
alone exceed the available hard input budget.

#### Scenario: Required items exceed hard budget

- **GIVEN** the available input budget is 100 tokens
- **AND** required items consume 120 tokens
- **WHEN** context selection runs
- **THEN** selection fails explicitly
- **AND** no required item is silently dropped
- **AND** no required item is silently truncated
```

这里没有重新复制整个 Context 系统。

它只说：

```text
ADDED
MODIFIED
REMOVED
```

哪些行为发生变化。

OpenSpec 把这种文件称为 **Delta Spec**。

它解决了一个很实际的问题：对于 brownfield 项目，我真正需要表达的通常不是：

```text
系统应该是什么样
```

而是：

```text
相对于当前已经成立的系统，
这次到底改变什么？
```

这两个问题看起来接近，写出来却很不一样。

假设 Base Spec 已经有十几条权限规则，这次需求只是：

```text
管理员导出增加 JSON 格式
```

那么 Change 不应该重新复制：

```text
谁可以导出
哪些数据可以导出
审计怎样保存
权限怎样判断
```

然后在其中某处插入：

```text
新增 JSON
```

更干净的表达是：

```text
Base Spec

导出只能包含调用者有权读取的数据
导出必须记录审计事件
支持 CSV

        ↓ 当前变化

Delta

MODIFIED:
导出格式由 CSV 改为 CSV | JSON
```

这样 Review 的对象也变了。

以前 Review 一份重写后的 PRD，我要自己寻找：

```text
到底哪句话变了？
```

现在 Change 天然就是 diff。

这和 Git 的思路很接近。

代码层面我们早就习惯：

```text
repository state
+
commit diff
=
new repository state
```

OpenSpec 只是把类似结构搬到了需求层：

```text
Base Spec
+
Change Delta
=
New Base Spec
```

这也是我认为它比“每个需求写一份完整 PRD”更适合 Coding Agent 的地方。

Agent 不需要每次重新理解整个世界。

它可以先读取当前成立的规则，再读取这次变化。

输入从：

```text
请理解这个 3000 行需求文档，
其中部分内容是旧的，
部分内容是新的，
自己判断区别。
```

变成：

```text
这是当前事实。

这是本次 Delta。

请实现 Delta，
同时不要破坏 Base Spec 中未被修改的约束。
```

当然，Delta 也不是免费的。

如果 Base Spec 本身没有维护，已经严重落后于真实代码，那么：

```text
Base Spec
+
Delta
```

只会得到一份结构清晰但事实错误的文档。

所以 OpenSpec 的前提仍然是：

> `specs/` 中所谓的“当前事实”，需要有人持续让它和现实保持一致。

它解决的是 Change 的表达问题，不会自动解决文档腐化。

---

### 3.2 一次 Change 不是一个 Prompt，而是一组职责不同的工件

OpenSpec 当前默认的 `spec-driven` schema 中，一次 Change 主要由四类 planning artifacts 构成：

```text
proposal
    ↓
specs
    ↓
design
    ↓
tasks
```

官方在 Core Concepts 中把它压缩成：

```text
proposal ──► specs ──► design ──► tasks ──► implement
   why        what       how       steps      do it
```

这条关系正好回答了我上一节留下的问题。

过去我的 TRD 很容易长成：

```text
为什么做
+
什么算正确
+
准备怎么实现
+
要改哪些文件
+
任务清单
+
测试方法
```

全部混在一起。

OpenSpec 至少在工件层明确要求：

```text
Proposal ≠ Specs ≠ Design ≠ Tasks
```

例如还是 Required Context Overflow 这个变化。

Proposal 可以只负责说明为什么现在要改：

```markdown
# Proposal

当前 Selector 在 required items 已超过 hard budget 时
没有明确失败语义。

这会让调用方无法区分：

1. optional context 因预算被正常裁剪；
2. required context 已经无法满足，但系统仍继续生成 payload。

本次变化要求为 required-overflow 建立显式失败边界。
```

到了 Specs，关注点变成：

```markdown
### Requirement: Required context overflow

When required items alone exceed the hard input budget,
selection SHALL fail explicitly.

The selector SHALL NOT silently drop or truncate
a required item to satisfy the budget.
```

Design 才讨论：

```markdown
# Design

在 Selector 进入 optional selection 之前：

1. 计算 required_token_total；
2. 与 available_input_tokens 比较；
3. 若 required_token_total > available_input_tokens，
   抛出 RequiredContextBudgetExceeded；
4. Compiler 不负责重新裁剪 required items；
5. Trace 保存失败类型与预算数据。
```

最后 Tasks 才落到执行顺序：

```markdown
# Tasks

- [ ] 定义 RequiredContextBudgetExceeded
- [ ] 在 Selector required phase 增加 hard-budget check
- [ ] 增加 required-overflow fixture
- [ ] 增加 optional trimming regression case
- [ ] 检查 Compiler 不会捕获异常后静默降级
- [ ] 保存对应 Trace evidence
```

四份内容描述的是同一件事，但它们不能互换。

如果只保存 Tasks：

```text
[ ] 增加异常
[ ] 修改 Selector
[ ] 增加测试
```

半年以后看不到：

```text
为什么需要这个异常？
```

如果只有 Design：

```text
先统计 required token，
超限后抛 RequiredContextBudgetExceeded
```

又无法确定：

```text
这只是作者选择的一种实现，
还是产品要求本身就是“必须抛这个异常类型”？
```

如果把 Design 当 Spec，未来重构时就容易出现：

```text
为了保持需求兼容，
这个实现细节不能改。
```

而实际 Requirement 可能只要求：

```text
必须明确失败，
不得静默丢 required context。
```

异常类叫什么，本来应该允许变化。

因此我现在看 OpenSpec，最想保留的不是 `/opsx:propose` 这个命令，而是这几个工件之间的责任边界：

| 工件 | 应稳定保存的内容 | 容易写错成什么 |
| --- | --- | --- |
| Proposal | intent、scope、为什么要改 | 提前写成完整技术方案 |
| Specs | requirement、scenario、行为边界 | 塞入文件路径和类名 |
| Design | architecture decision、trade-off、实现路线 | 偷偷重新定义需求 |
| Tasks | 可执行步骤、依赖与完成进度 | 用 checkbox 代替验收 |

这也解释了为什么单纯把原来的：

```text
PRD.md
TRD.md
```

改名成：

```text
proposal.md
design.md
```

没有意义。

如果内部职责还是混着的，就只是换了文件名。

---

### 3.3 OpenSpec 的 artifact graph 比固定阶段更值得学

看到：

```text
proposal
→ specs
→ design
→ tasks
→ implement
```

很容易把 OpenSpec 理解成另一套瀑布流程：

```text
阶段 1 写 Proposal
阶段 2 写 Spec
阶段 3 写 Design
阶段 4 写 Tasks
阶段 5 才允许 Coding
```

但当前 OpenSpec 的 OPSX 文档专门反对这种理解。

它把这些关系描述为：

> dependencies are enablers, not gates

也就是：

```text
依赖告诉你“现在已经具备什么条件”，
而不是强制规定“永远不能回头”。
```

这点对 Agent 开发尤其合理。

真实实现里很常见：

```text
Proposal
    ↓
Spec
    ↓
Design
    ↓
Tasks
    ↓
开始 Implementation
    ↓
发现仓库和预想不一样
```

例如我原来 Design 写：

```text
Selector 直接接收 model context window。
```

实现时才发现当前 Hi-Agent 的 Budget 层已经提前计算了：

```text
available_input_tokens
```

那正确动作不是：

```text
Design 已经批准了，
所以硬着头皮照原方案写。
```

而应该回去改：

```text
design.md
```

必要时继续检查：

```text
spec 是否受到影响？
tasks 是否要调整？
```

如果只是实现手段变了：

```text
Requirement 不变
Design 变
Tasks 变
```

如果连行为都发现定义错了：

```text
Requirement 也要变
```

OpenSpec 当前的 `/opsx:update` 就是为这种情况设计的：更新已有 planning artifacts，并维持它们之间的一致性，而不是假设所有规划在第一行代码写下之前就永久冻结。

参见：[OpenSpec OPSX Workflow](https://github.com/Fission-AI/OpenSpec/blob/main/docs/opsx.md)。

这也让我修正了以前对 SDD 的一个误解。

我一开始很容易把 Spec 理解成：

```text
人类先想得百分之百清楚
        ↓
冻结 Spec
        ↓
Agent 按图施工
```

这在现实里很难成立。

代码本身也是一种信息来源。

只有真正开始读依赖、跑测试、调用接口以后，才会暴露一些规划阶段看不到的事实。

因此，更现实的关系应该是：

```text
Intent
  ↓
Proposal
  ↓
Spec
  ↓
Design
  ↓
Tasks
  ↓
Implementation
  │
  ├──── 新事实 ────→ Design
  │
  ├──── 新边界 ────→ Spec
  │
  └──── 范围改变 ──→ Proposal
```

重点不是“绝不回头”。

重点是：

> **回头时修改对应的工件，而不是让代码和聊天记录悄悄形成一个只有当前 Agent 知道的新版本需求。**

这也是为什么我觉得 artifact graph 比固定 workflow 更有价值。

命令会变。

实际上 OpenSpec 自己的工作流已经发生过明显变化：当前 OPSX 被定义为 standard workflow，官方明确把它描述成 fluid、iterative，并提供 `update`、`sync` 等动作，而不是只剩一条固定的 proposal → apply → archive 流程。

但只要下面这些依赖仍然成立：

```text
Tasks 需要知道准备怎么做
        ↑
Design 需要知道什么行为必须成立
        ↑
Spec 需要知道这次为什么改、边界在哪里
```

这套结构就仍然有意义。

---

### 3.4 Apply 不是终点，Archive 才解释了为什么 Spec 可以成为长期状态

如果 OpenSpec 只有：

```text
proposal
→ specs
→ design
→ tasks
→ apply
```

那它本质上仍然只是一个更结构化的 Coding Prompt 生成器。

我更在意的是后半段：

```text
implementation
    ↓
verification
    ↓
sync / archive
```

这里需要区分 OpenSpec 当前工具提供的具体命令，和我自己想保留的 SDD 原则。

截至当前版本，OpenSpec 默认 `core` profile 主要提供：

```text
/opsx:propose
/opsx:explore
/opsx:apply
/opsx:update
/opsx:sync
/opsx:archive
```

`/opsx:verify` 位于 expanded workflow，而不是默认 core profile。

因此我不会写成：

```text
OpenSpec 强制所有变更执行 verify。
```

这不准确。

但从 SDD 的角度，我仍然要求：

```text
Implementation
≠
Verified Implementation
```

例如 `/opsx:apply` 把五个 Tasks 都勾完：

```text
[x] 定义异常
[x] 修改 Selector
[x] 添加 fixture
[x] 添加 regression test
[x] 保存 trace
```

这里只能说明：

```text
计划中的实现步骤已经执行。
```

是否真的满足 Spec，还需要证据：

```text
required-overflow case 是否真的失败？

optional trimming 是否没有 regression？

失败时 required item 是否确实没有进入 dropped？

Compiler 有没有把异常吞掉？

Trace 是否保存了正确状态？

完整 test suite 是否跑过？
```

所以在我自己的 Lightweight SDD 里，不管具体工具有没有叫 `/verify` 的命令，都会保留一个明确阶段：

```text
Spec
    ↓
Implementation
    ↓
Evidence
```

没有 Evidence，就不能把：

```text
implemented
```

升级成：

```text
verified
```

OpenSpec 另一个值得保留的动作是 `sync / archive`。

假设 Change 最终确认完成：

```text
openspec/changes/required-context-overflow/
```

它不应该永远作为一个“正在进行的需求”留在那里。

否则半年以后 Agent 看到几十个 Change：

```text
change-a
change-b
change-c
change-d
...
```

根本不知道哪些仍然有效，哪些已经完成，哪些已经被替代。

Archive 做的事情，是把已经完成的 Delta 折回当前事实：

```text
Before

openspec/specs/context/
    当前规则 V1

openspec/changes/required-context-overflow/
    本次 Delta


After

openspec/specs/context/
    当前规则 V2

openspec/changes/archive/.../
    变化历史
```

也就是：

```text
Current Truth
     +
Change Delta
     +
Verified Reality
     ↓
New Current Truth
```

这一点对长期使用 Agent 很关键。

Agent 下一次进入仓库时，不应该先回放所有历史聊天和所有旧 Proposal，才能知道：

```text
现在系统究竟应该怎样工作？
```

它应该能够直接读取当前 Base Spec。

只有在需要理解：

```text
为什么会变成这样？
```

时，再去查 Archive。

这和代码仓库也有一点类似：

```text
工作树
回答“现在是什么”

Git history
回答“为什么变成这样”
```

如果所有历史状态都同时堆在当前 Context 里，就会把知识系统变成考古现场。

---

### 3.5 OpenSpec 最值得我抄的不是命令，而是 Change 的生命周期

因此，如果半年以后 OpenSpec 把：

```text
/opsx:propose
```

改成另一个命令，我并不会觉得这篇笔记过时。

我真正想从它留下来的结构只有几条：

```text
1. 当前事实和本次变化分开保存。

2. 一次 Change 有自己的生命周期，
   不直接污染整个项目 Spec。

3. Proposal、Spec、Design、Tasks
   保存不同类型的决策。

4. Implementation 中发现新事实后，
   允许回写前面的工件。

5. 完成的 Delta 最终进入新的 Base Spec，
   历史 Change 则归档。
```

把它放回我原来的工作流，可以看到一个明显变化。

以前是：

```text
PRD
  ↓
TRD
  ↓
6～8 Tasks
  ↓
Coding Agent
  ↓
Test + Diff
```

现在更接近：

```text
Current System
      │
      ├── Base Spec
      │
      ▼
   New Intent
      │
      ▼
   Change
      │
      ├── Proposal
      │      why / scope
      │
      ├── Delta Spec
      │      what changes
      │
      ├── Design
      │      how
      │
      └── Tasks
             executable steps
              │
              ▼
       Implementation
              │
              ▼
         Verification
              │
              ▼
           Archive
              │
              ▼
        New Base Spec
```

这里也终于能解释为什么我现在不再执着于：

```text
到底应该写 PRD 还是 Spec？
```

对于小项目，我完全可以继续保留 `PRD.md` 和 `TRD.md`。

真正需要改变的是内部结构。

我希望以后至少能区分：

```text
这是当前事实。

这是本次变化。

这是行为要求。

这是我选择的实现。

这是尚未完成的任务。

这是已经得到的证据。
```

只要这些状态不再混在一起，文件名反而是次要的。

OpenSpec 给我解决的是 **Change 怎样被描述和收敛**。

但它还留下了另一个问题。

即使 Proposal、Spec、Design、Tasks 都已经写得很好，开发开始以前仍然可能存在：

```text
项目级的不变量没有被声明；

需求中仍然藏着歧义；

Plan 和 Spec 之间互相矛盾；

Tasks 漏掉某条 Requirement；

Agent 在真正实现以前，
没有一个明确阶段检查这些问题。
```

GitHub Spec Kit 对这部分的处理比 OpenSpec 更重。

它增加了 Constitution、Clarify、Analyze 等步骤，把一些质量检查显式放到了 Implementation 之前。

这也是下一节我想拿它和 OpenSpec 对照的地方：不是比较哪个 CLI 更好用，而是看两套 SDD 在 **“什么时候应该阻止 Agent 开始写代码”** 这件事上，选择了不同的重量。

## 4. Spec Kit：把“先别急着写代码”拆成一组质量门

OpenSpec 让我开始把一次 Change 当成独立对象，但如果需求本身还没有想清楚，只是把模糊 Prompt 包进：

```text
proposal
spec
design
tasks
```

并不会自动变得可靠。

例如我可以写一份结构完整的 Context 模块 Spec：

```text
目标：
优化 Context 使用效率

Requirement：
优先保留高价值 Context

Design：
使用 priority-based selector

Tasks：
1. 实现排序
2. 实现 budget
3. 增加测试
```

文件齐全，流程也走完了。

问题仍然存在：

```text
什么叫高价值？

priority 谁来定义？

required 和 high-priority 是同一件事吗？

budget 不够时允许删除哪些信息？

排序稳定性是不是要求？

Selector 的失败行为是什么？
```

如果这些问题直到 Implementation 才暴露，前面的 Spec 只是在结构上完整。

GitHub Spec Kit 给我的启发主要在这里。

它的默认 SDD 路线比 OpenSpec 更重。当前官方 README 给出的主路径已经是：

```text
Constitution
     ↓
Specify
     ↓
Plan
     ↓
Tasks
     ↓
Implement
     ↓
Converge
```

对于存在明显歧义或质量风险的任务，还可以插入：

```text
Clarify
Checklist
Analyze
```

官方文档把更完整的 Agentic SDD 路线描述为：

```text
constitution
    ↓
specify
    ↓
clarify
    ↓
plan
    ↓
checklist
    ↓
tasks
    ↓
analyze
    ↓
implement
    ↓
converge
```

参见：

- [GitHub Spec Kit](https://github.com/github/spec-kit)
- [Agentic SDD Reference](https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md)

我不准备把这条命令链原样搬进自己的项目。

对我更有用的是其中的几个检查位置：

```text
项目有哪些长期不能被单次需求推翻的约束？

Requirement 还有哪些歧义？

Requirement 本身是否足够完整、清楚、可测试？

Spec、Plan、Tasks 是否互相覆盖？

代码写完以后，与最初的 Spec 还差多少？
```

这些问题过去不是没有出现，只是大多散在我的脑内检查、Agent 对话和最后一次 Code Review 里。

Spec Kit 把它们放到了显式位置。

### 4.1 Constitution：有些约束不应该由每一次 Task 重新决定

假设我连续给 Coding Agent 做三个 Context 任务：

```text
Task A
实现 Budget

Task B
实现 Selector

Task C
实现 Provider Formatter
```

三个任务可能分别写得很好。

但它们都应该遵守一组更长期的规则，例如：

```text
required context 不得静默丢失

公开 API 的输入必须先做结构校验

Provider-specific 行为不得反向污染领域模型

所有 completion claim 必须有本次运行产生的证据

测试 fixture 不得包含真实凭据
```

这些内容不属于某一个 Task。

如果我把它们分别复制进：

```text
task-a.md
task-b.md
task-c.md
```

马上会出现维护问题。

例如 A 写：

```text
required item 超限必须 fail
```

B 写：

```text
required item 尽量保留
```

C 又没有提。

三个 Agent session 就可能对同一个不变量产生三种理解。

Spec Kit 的 Constitution 解决的是这一层。

官方把 `/speckit.constitution` 定义为创建或更新项目级 governing principles 和 development guidelines。它通常不是每个 feature 都重新执行一次，而是建立一组后续 Specify、Plan、Tasks 和 Implementation 都应遵守的项目原则。

放到我自己的项目里，我会把它理解成：

```text
Project-level invariants
```

也就是：

> 单次 Feature 可以增加行为，但不能在没有明确讨论的情况下推翻这些约束。

例如 Hi-Agent 可以有：

```markdown
## Context Integrity

Required context MUST NOT be silently dropped.

If all required items cannot fit inside the hard input budget,
the compilation path MUST expose an explicit failure.

## Evidence Discipline

A test, build, benchmark, or completion state MUST NOT be reported
as passed unless that check was executed in the current verification run.

## Layer Boundary

Provider-specific payload formatting MUST NOT change
the semantic meaning of ContextItem or CompiledContext.

## Deterministic Baseline

V1 selection behavior MUST remain deterministic unless a later change
explicitly introduces and evaluates a non-deterministic strategy.
```

这些句子与：

```text
实现 Required Context Preservation
```

不是同一个层级。

后者是一次 Change。

前者决定这次 Change 可以怎样做。

这种区别也能解释为什么我不想把所有长期规则继续塞进一个越来越大的 `AGENTS.md`。

两者确实可能有内容重叠，但职责不同。

例如：

```text
AGENTS.md
更适合告诉 Agent：
仓库在哪里、命令怎么跑、有哪些局部规则和知识入口。

Constitution
更适合表达：
哪些工程原则跨多个 feature 长期生效。
```

实际项目未必需要真的同时维护两个文件。

小项目完全可以写成：

```text
AGENTS.md
├── Repository Map
├── Commands
└── Project Invariants
```

但概念上我希望把：

```text
如何在这个仓库工作
```

和：

```text
这个仓库哪些性质不能被普通 Feature 随意改变
```

分开理解。

这里也有一个明显风险：Constitution 很容易膨胀。

如果每次 Code Review 发现一个偏好都追加进去：

```text
函数最好不要超过 50 行
这个目录尽量别新增文件
这里推荐用 dataclass
那个地方更喜欢 composition
```

几个月以后，它就会变成另一份没有优先级的规则仓库。

我目前给自己的限制是，只有满足下面至少一个条件的约束才值得进入项目级不变量：

```text
违反它会造成跨模块架构漂移；

违反它会破坏安全、数据或兼容性边界；

它需要跨很多 Change 持续成立；

它的违反可以被相对明确地检查；

如果每个 Task 都重复声明，维护成本会明显上升。
```

否则放在局部 Design、目录规则或当前 Change 里更合适。

---

### 4.2 Clarify：不要让 Agent 在 Implementation 阶段替我补产品决定

`Specify` 最大的问题不是写不出 Requirement，而是 Requirement 很容易在语法上完整、语义上仍然缺东西。

例如：

```markdown
### Requirement

The system SHALL preserve important context
when the input exceeds the model budget.
```

读起来很合理。

但只要问几轮就会开始松动：

```text
“important” 是谁定义？

超过的是 soft budget 还是 hard budget？

preserve 是原文保留还是允许 summarization？

system message 与 tool result 谁优先？

同 priority 时顺序怎么办？

required 本身超限怎么办？
```

如果我直接开始写代码，Agent 必须自行决定这些问题。

它甚至未必意识到自己正在做需求决策。

它可能只是看到现有结构以后自然选择：

```python
items.sort(key=lambda x: x.priority, reverse=True)
```

代码本身没有明显错误。

但这一行已经隐含决定：

```text
priority 是全局可比较的；

数值越大越重要；

required 没有单独语义；

同 priority 的稳定顺序由现有 sort 行为决定。
```

这类决定如果只存在于代码里，后面很难区分：

```text
这是需求，

还是当时 Agent 为了把代码写完临时选择的实现？
```

Spec Kit 的 `/speckit.clarify` 就是在 Plan 之前主动寻找这种 underspecified area。

我不会把它理解成：

```text
Agent 多问用户几个问题
```

而更像：

```text
把隐藏的决策点枚举出来，
在 Design 开始以前决定哪些必须澄清。
```

对于 Required Context Preservation，可以出现这样的 Clarification Set：

```markdown
## Clarifications

### Q1. required items 超过 hard budget 时怎么办？

Decision:
Fail explicitly.

Reason:
Continuing would violate the semantic meaning of `required`.

### Q2. required item 是否允许自动摘要？

Decision:
No in V1.

Reason:
Summarization changes content and introduces another lossy operation.
It can be evaluated separately in a later change.

### Q3. optional items 的裁剪顺序是什么？

Decision:
Use deterministic priority order, then preserve original order
for equal-priority items.

### Q4. failure 是否允许 Compiler 自动 fallback？

Decision:
No.

Compiler propagates the explicit selection failure.
```

到这里，一些原本可能偷偷进入实现的选择，被提前变成显式决定。

这不是为了追求“所有问题都提前想完”。

有些信息必须实现以后才会知道。

Clarify 更适合处理的是：

```text
现在已经能看到，

而且如果不决定，

Agent 就一定得替我决定的问题。
```

判断一条问题是否值得在实现前 Clarify，我现在会看两个条件：

```text
不同答案是否会产生明显不同的外部行为？

不同答案是否会让后面的 Design 或 Tasks 发生明显变化？
```

如果答案都是“不会”，就没必要为了流程完整而多问。

---

### 4.3 Checklist：检查的对象不是代码，而是 Requirement 本身

这是 Spec Kit 里我以前很容易忽略的一步。

我们习惯给代码写测试：

```text
unit test
integration test
e2e test
```

却很少问：

```text
谁来测试 Spec？
```

Spec Kit 当前把 `/speckit.checklist` 描述成一种面向 Requirements 的质量检查，官方甚至用了一个很直观的类比：

> “unit tests for English”

它检查的不是：

```text
这个功能实现了吗？
```

而是：

```text
要求本身是否写到了可以实施和验证的程度？
```

例如：

```markdown
### Requirement: Context overflow

The system should handle context overflow gracefully.
```

代码一行还没写，这个 Requirement 已经有问题。

可以给它做一组类似测试的检查：

```text
[ ] “gracefully” 是否有可观察定义？

[ ] soft limit 与 hard limit 是否区分？

[ ] required overflow 是否定义？

[ ] optional trimming 是否定义？

[ ] failure result 是否可观察？

[ ] 是否定义不得发生的静默行为？

[ ] Requirement 是否把某个具体实现写成强制要求？
```

如果前三项都回答不了，就没必要急着 Implementation。

这给我一个很有用的类比：

```text
普通 Test：

Implementation
     ↓
符合 Requirement 吗？


Requirement Checklist：

Requirement
     ↓
足够完整，可以被实现和验证吗？
```

两个检查对象完全不同。

例如：

```text
系统必须快速启动
```

可以实现出一个很快的系统，却依然是一条差 Requirement。

因为它没有定义：

```text
fast 是多少？

什么环境？

什么起点？

什么终点？

统计哪个指标？
```

因此，Checklist 放在 Implementation 之前才有意义。

它不是测试代码，而是在减少：

```text
拿一份不可验证的 Spec 去要求 Agent 验证自己
```

这种循环。

对我自己的 Lightweight SDD 来说，我大概率不会给每个 Change 都创建 `checklist.md`。

但对于下面几类要求，我会借用这种思路：

```text
性能指标
安全边界
权限
数据迁移
失败恢复
跨模块契约
Agent completion criteria
```

因为这些地方最容易出现：

```text
一句话听起来没有问题，
真正执行时却有五种解释。
```

---

### 4.4 Analyze：实现前再检查一次 Spec、Plan 和 Tasks 有没有脱节

假设 Clarify 已经把 Requirement 写清楚，Plan 也写好了，Tasks 也拆完了。

还是可能出问题。

例如 Spec 要求：

```text
R1:
required overflow 必须明确失败

R2:
optional items 可以裁剪

R3:
失败状态必须进入 Trace
```

Design 写：

```text
D1:
Selector 在 required phase 检查 token total

D2:
超限时抛 RequiredContextBudgetExceeded
```

Tasks 却只有：

```text
T1:
修改 Selector

T2:
添加 required-overflow test
```

这里 `R3` 已经失踪了。

如果不检查，Agent 完成两个 Tasks 后完全可以合理地宣布：

```text
All tasks completed.
```

它没有遗漏 Task。

是 Tasks 在生成时就漏掉 Requirement。

Spec Kit 的 `/speckit.analyze` 负责的就是这种 cross-artifact consistency 与 coverage analysis，官方建议在 Tasks 生成以后、Implementation 以前运行。

我会把它理解成一个静态一致性检查：

```text
Spec
  │
  │ coverage
  ▼
Plan
  │
  │ decomposition
  ▼
Tasks
```

至少问：

```text
每条 Requirement 是否有实现路径？

每个关键 Design Decision 是否有对应 Task？

每个 Task 是否能追回 Requirement 或 Design？

Tasks 有没有偷偷加入 Spec 从未要求的新行为？

Plan 有没有违反 Constitution？

不同工件之间是否出现矛盾？
```

还是刚才的例子。

Analyze 后可以得到：

```text
R1 → D1, D2 → T1, T2
R2 → existing selector policy → regression test missing
R3 → no design coverage → no task coverage
```

这时应该先补：

```text
D3:
failure state is emitted to SelectionTrace

T3:
add failure trace mapping

T4:
add trace assertion
```

再让 Agent 开始实施。

这一步和 Test 的区别也很清楚。

Test 只能在实现以后告诉我：

```text
现有断言有没有通过。
```

Analyze 则能在实现以前发现：

```text
有一整条 Requirement 根本没有进入 Tasks。
```

两者防的是不同错误。

---

### 4.5 Plan 和 Tasks 的价值，不是替 Agent 决定每一行代码

Spec Kit 的流程比 OpenSpec 更容易给我一种错觉：

```text
既然已经 Plan 得这么详细，
最好把所有实现决定都提前写死。
```

但如果走到这个极端，Coding Agent 就退化成：

```text
根据 Markdown 机械生成代码
```

这既不现实，也浪费模型读取仓库和局部推理的能力。

我现在更愿意让 Plan 固定那些：

```text
如果两个 Agent 分别实现，
不希望它们自由选择出两个不兼容答案
```

的东西。

例如：

```text
模块边界

public API

关键数据结构

数据迁移方式

安全边界

依赖方向

失败语义

必须复用的基础设施

明确拒绝的方案
```

而不需要提前写：

```text
具体 helper 函数叫什么

某个 for loop 怎样展开

一个纯内部函数拆成两个还是三个

变量名必须是什么

每一行代码放在哪
```

例如 Context Selector 的 Plan 可以固定：

```markdown
Selector owns selection policy.

Compiler orchestrates selection results but does not
silently reinterpret failure.

Provider Formatter receives already-compiled structured context
and MUST NOT perform another semantic selection pass.
```

这是架构责任。

至于 Selector 内部究竟写：

```python
required_items = [...]
optional_items = [...]
```

还是抽成：

```python
partition_by_requirement(...)
```

没有必要进入 Spec。

这也是我现在区分 SDD 和“提前把代码写成自然语言”的标准。

如果 Plan 已经细到：

```text
Agent 除了翻译成 TypeScript 以外没有任何局部设计空间
```

那我可能写得过头了。

Task 也一样。

一个好的 Task 应该限制：

```text
工作边界
前置依赖
可观察完成条件
```

而不是描述所有操作。

例如：

```markdown
### Task: Required Context Overflow

Depends on:
- ContextItem required semantics
- Token budget calculation

Implement:
- explicit failure when required items exceed hard budget
- preserve existing optional trimming behavior
- expose failure through trace

Done when:
- required-overflow case passes
- optional trimming regression case passes
- trace records overflow failure
```

这比：

```text
1. 打开 selector.py
2. 在第 42 行下面添加 if
3. 新建 error.py
4. import error
5. 修改 test_selector.py
```

更适合 Agent。

前者定义边界。

后者试图遥控实现。

---

### 4.6 Converge：Tasks 全部完成以后，再问一次“现实和 Spec 还差多少”

我最开始看 Spec Kit 时，关注点主要在：

```text
constitution
specify
clarify
plan
tasks
analyze
implement
```

但当前 Spec Kit 的主路径已经把 `/speckit.converge` 放到了 Implement 后面。

官方 Quickstart 明确给出：

```text
Implement
    ↓
Converge
    ↓
如果尚未收敛
    ↓
继续 Implement
    ↓
再次 Converge
```

直到 Converge 报告：

```text
Converged
```

这一变化很符合我前面讨论的 Requirement Traceability。

因为：

```text
Tasks completed
```

只能证明计划中的 Task 被执行了。

它不能证明：

```text
Spec 已经完全被现实满足。
```

这两个集合并不总是相等。

可以写成：

```text
S = Spec 要求的行为集合
T = Tasks 覆盖的工作集合
I = 当前 Implementation 实际行为
```

理想状态是：

```text
I ⊨ S
```

也就是 Implementation 满足 Spec。

但实际很可能出现：

```text
T 全部完成

同时：

S 中仍有 Requirement 没有被 I 满足
```

原因可能是：

```text
Tasks 漏了要求；

实现与 Plan 偏离；

测试覆盖不足；

实现过程中发现了新边界；

某个 Task 标记完成，但真实行为仍然错误。
```

Converge 的意义，就是不再把：

```text
task checkbox
```

当成终止条件。

而是重新比较：

```text
codebase
vs
spec
vs
plan
vs
tasks
```

把剩余工作追加回 Tasks，然后继续实现。

这形成了一个更合理的后半段：

```text
Spec
 ↓
Plan
 ↓
Tasks
 ↓
Implement
 ↓
Observe current codebase
 ↓
Compare against Spec
 ↓
Remaining gaps
 ↓
Tasks
 ↓
Implement
 ↓
...
```

这和我过去：

```text
Agent：Done.
我：看一下 diff，好像差不多。
```

已经不是同一种完成定义。

不过我仍然不会因为 Spec Kit 有 `/speckit.converge`，就在自己的项目里直接写：

```text
Converge passed
=
功能绝对正确
```

Converge 本身仍然依赖它能够观察到的证据。

如果一个 UI Requirement 必须通过真实浏览器验证，而 Agent 只有静态代码和 unit tests，那么它最多能确认：

```text
静态实现与已有测试层面没有发现差距
```

不能把没有观察过的 UI 行为升级成 verified。

所以 Convergence 仍然需要 Harness 提供：

```text
tests
browser
logs
metrics
runtime
database
trace
```

才能把 Spec 中的要求变成可检查事实。

这个边界后面还会回到 Harness Engineering。

---

### 4.7 OpenSpec 和 Spec Kit，我现在不会再问“应该二选一哪个”

刚接触这两个项目时，很自然会做功能表：

| | OpenSpec | Spec Kit |
| --- | --- | --- |
| Spec | ✓ | ✓ |
| Design | ✓ | ✓ |
| Tasks | ✓ | ✓ |
| Agent Integration | ✓ | ✓ |
| Verification | ✓ | ✓ |

然后试图得出：

```text
A 比 B 好
```

现在我觉得这种比较价值有限。

两个项目都在快速演化。

截至我这次整理时，OpenSpec 已经把 OPSX 作为标准 workflow，并强调：

```text
fluid
iterative
actions, not phases
dependencies are enablers, not gates
```

Spec Kit 也已经走到 1.0.0，主流程中增加了 Converge，同时拥有 Extensions、Presets、Bundles 等扩展机制。

因此它们已经不是两个固定不变的命令集合。

我更愿意比较它们各自在提醒我什么。

OpenSpec 最让我想保留的是：

```text
Current Spec
    +
Change Delta
    +
Archive
```

它很适合解释：

> 一个已经存在的系统如何持续发生小范围变化，而不是每次重新描述整个世界。

Spec Kit 最让我想保留的是：

```text
Constitution
     ↓
Requirement Quality
     ↓
Cross-artifact Analysis
     ↓
Implementation
     ↓
Convergence
```

它更强烈地提醒我：

> 不要只让 Agent 拥有一份 Spec，还要检查 Spec 自己是否合格，以及实现后是否真的收敛到了 Spec。

如果硬要画成两个侧重点，大致是：

```text
OpenSpec

Current Truth
     │
     ▼
  Change
     │
     ├── Proposal
     ├── Delta Spec
     ├── Design
     └── Tasks
     │
     ▼
 Implementation
     │
     ▼
 Archive
     │
     ▼
New Current Truth
```

而 Spec Kit 更像：

```text
Project Constitution
        │
        ▼
      Spec
        │
     Clarify
        │
     Checklist
        │
        ▼
      Plan
        │
        ▼
      Tasks
        │
     Analyze
        │
        ▼
   Implement
        │
        ▼
    Converge
        │
    gap exists
        └────────→ Tasks → Implement
```

一个更容易让我思考：

```text
Change 怎样进入长期事实？
```

另一个更容易让我思考：

```text
怎样减少一份坏 Spec 直接进入 Implementation？
```

所以我不打算在 Hi-Agent 里完整安装两套流程，再为了形式要求每个实验走十个命令。

我更想把两边对我有用的约束压缩成自己的 Lightweight SDD：

```text
项目级不变量
      ↓
本次 Change
      ↓
明确 Requirement 与 Acceptance
      ↓
必要时 Clarify
      ↓
记录关键 Design Decision
      ↓
拆成可独立验证的 Tasks
      ↓
实现
      ↓
按 Evidence 检查 Requirement
      ↓
现实与 Spec 不一致就回写
      ↓
完成后更新当前事实
```

到这里，“SDD 是不是 OpenSpec”“SDD 是不是 Spec Kit”这个问题对我已经没有太大意义。

我接下来更需要解决的是另一个更实际的问题：

> **一次什么样的修改，值得走这么完整的流程？**

改一个 typo，如果也要求：

```text
Proposal
Spec
Clarify
Design
Tasks
Analyze
Implement
Converge
Archive
```

SDD 很快就会变成维护 Markdown 的工作。

但涉及权限、数据、安全边界或跨模块行为的变化，如果只给一句 Prompt，又会回到文章开头的问题。

所以我最终没有选一套固定流程，而是开始按变更风险决定 Spec 应该写到多重。

## 5. 我最终留下的不是一套固定流程，而是一套按风险加重的 Lightweight SDD

看完 OpenSpec 和 Spec Kit 以后，我最不想做的一件事，就是把自己的开发流程从：

```text
PRD
→ TRD
→ Tasks
```

升级成：

```text
Constitution
→ Proposal
→ Spec
→ Clarify
→ Checklist
→ Design
→ Tasks
→ Analyze
→ Implement
→ Verify
→ Converge
→ Archive
```

然后要求所有修改都走一遍。

这样确实“更规范”，但对于 Hi-Agent 这种主要用来学习和实验的项目，很快会出现一个荒唐结果：我花在维护 SDD 工件上的时间，比真正做实验还多。

另一方面，回到：

```text
想到什么
→ Prompt
→ Agent 开写
```

又会重新遇到前面的问题。

所以我最后保留的不是某个框架的完整命令，而是一条更轻的判断逻辑：

```text
先看这次 Change 的风险在哪里
        ↓
只为这些风险增加必要的 Spec 工件
        ↓
把关键行为写到可以验证
        ↓
让 Agent 实现
        ↓
用证据判断是否收敛
```

这套方法里，SDD 的重量不是固定的。

同一个仓库里完全可以同时存在：

```text
一行 typo
只需要一句 Task + diff

普通内部重构
需要 Task + tests

新的模块行为
需要 Spec + Design + Tasks + verification

权限 / 数据 / 安全变化
需要完整 Proposal + Spec + Design + rollback + evidence
```

关键不在于“有没有使用 OpenSpec”，而在于：

> **这次修改如果做错了，错误会以什么方式暴露，以及我们是否已经把那部分不确定性写清楚。**

### 5.1 我现在先判断风险，而不是先决定写几个 Markdown

以前我拿到一个需求，第一反应通常是：

```text
要不要写 PRD？

要不要写 TRD？

拆成几个任务？
```

现在我会先问另外几个问题。

第一类是行为风险：

```text
这次修改会不会改变用户可见行为？

会不会改变 API contract？

会不会改变已有数据的解释？

会不会改变失败语义？
```

第二类是不可逆风险：

```text
会不会写数据库？

会不会删除或迁移数据？

会不会产生真实外部副作用？

失败以后能不能简单回滚？
```

第三类是边界风险：

```text
会不会碰权限？

会不会碰认证？

会不会改变支付、安全、隐私边界？

会不会让一个原来无权限的组件获得新能力？
```

第四类是架构风险：

```text
是否跨多个模块？

是否改变依赖方向？

是否引入新的长期抽象？

是否存在两种以上都合理、但后果差很多的实现路线？
```

第五类才是验证风险：

```text
实现以后，我是否能够直接观察它是否正确？

还是只能通过“代码看起来合理”判断？

需要 unit test、integration test、browser、logs，
还是必须访问真实外部系统？
```

把这些问题放在一起，比单纯看代码量更有用。

例如：

```text
修改 300 行 CSS
```

可能只是低风险视觉重构。

而：

```text
修改 8 行权限判断
```

却可能直接改变：

```text
谁能够读取哪些数据。
```

所以我现在不会使用：

```text
改动小
=
不需要 Spec
```

这种判断。

更接近的是：

| 变化 | 主要风险 | 我会保留的最低工件 |
| --- | --- | --- |
| typo、文案、明显局部修复 | 几乎没有行为歧义 | Task + Diff |
| 内部重构，不改变外部行为 | regression | Task + Tests |
| 单模块新行为 | Requirement、edge cases | Spec + Tasks + Tests |
| 跨模块能力 | 接口与责任边界 | Proposal + Spec + Design + Tasks + Verification |
| 数据迁移 | 不可逆状态变化 | Spec + Design + Migration / Rollback + Evidence |
| 权限、安全、支付 | 高后果错误 | Explicit invariants + Spec + Negative cases + Review + Evidence |
| 长任务 / 多 Agent | 状态、调度、恢复 | Spec 之外还需要 Harness / orchestration |

这张表不是新的流程模板。

它只是帮助我判断：

```text
哪里值得把隐性决定变成显式工件。
```

---

### 5.2 一个真正的小改动，不应该被 SDD 仪式化

例如：

```text
README 里把 Context Complier
改成 Context Compiler。
```

这里如果创建：

```text
proposal.md
spec.md
design.md
tasks.md
```

没有任何意义。

合理 Task 就是一句话：

```markdown
Fix the `Context Complier` typo in the README.

Done when:
- all occurrences are corrected;
- no unrelated content changes.
```

然后看 diff。

甚至这都不一定需要单独保存成文件。

直接作为 Agent Prompt 就足够。

因为它已经天然满足：

```text
目标明确
范围明确
实现几乎唯一
验证直接
错误容易回滚
```

也就是不确定性很低。

SDD 并不是：

```text
简单需求
+
更多文档
=
更专业
```

相反，如果一个流程要求我为了这种修改维护四份工件，我会认为流程本身开始制造噪声。

这也是我最终不愿意完整照搬任何 SDD 框架的原因。

工具为了支持团队、企业、不同 Agent 和复杂项目，需要提供完整能力；个人项目没有义务把所有能力同时启用。

---

### 5.3 普通功能开发，我通常只保留 Spec、Decision、Tasks 和 Evidence

对于 Hi-Agent 里一个正常规模的新能力，我现在最常用的其实只有四类信息：

```text
Spec
    什么必须成立

Decision
    哪些关键实现选择已经决定

Tasks
    怎样把工作拆成可执行单元

Evidence
    完成以后拿什么证明
```

例如我要增加：

```text
Required Context Preservation
```

可以先写：

```markdown
## Spec

Required context items MUST NOT be silently dropped.

If required items fit inside the hard input budget:
- all required items must be selected;
- optional items may be trimmed.

If required items alone exceed the hard input budget:
- selection must fail explicitly;
- required items must not be silently truncated;
- the failure must be visible to the caller.
```

这里先不出现：

```text
selector.py
RequiredContextBudgetExceeded
partition_required_items()
```

因为它们不属于行为契约。

然后单独记录 Decision：

```markdown
## Decisions

- V1 uses deterministic selection.
- Required items are processed before optional items.
- Required overflow is represented as an explicit exception.
- Compiler propagates this failure instead of retrying with lossy fallback.
```

这里已经允许出现实现策略，因为目的就是保存：

```text
我们具体选择了什么。
```

再拆 Tasks：

```markdown
## Tasks

1. Add required/optional partition behavior to Selector.
2. Add explicit required-overflow failure.
3. Propagate failure through Compiler.
4. Add trace representation.
5. Add boundary and regression tests.
```

最后准备 Evidence：

```markdown
## Verification

Required evidence:

- required-fit case passes;
- optional-trimming case passes;
- required-overflow case fails explicitly;
- selected/dropped partition invariant passes;
- Compiler does not silently recover;
- Trace exposes overflow state.
```

对于我现在的大部分学习项目，这已经足够。

它没有 OpenSpec 那么完整的 Change lifecycle，也没有 Spec Kit 那么多 quality gates，但几个最危险的信息已经不会混在一起：

```text
Requirement
≠
Design Decision
≠
Task
≠
Evidence
```

---

### 5.4 我现在特别在意 Claim State，因为 Agent 很容易把“计划”读成“事实”

写 Spec 时还有一个以前经常被忽略的问题。

下面四句话看起来都像技术文档：

```text
当前 Selector 使用稳定排序。

我们假设 V1 的 Context 不会超过 128K。

未来会增加自动 Summarization。

Required overflow 应该直接失败。
```

但它们的状态完全不同。

第一句可能是：

```text
Observed Fact
```

第二句是：

```text
Assumption
```

第三句是：

```text
Planned Work
```

第四句可能是：

```text
Decision
```

如果全部用同一种陈述语气写进 TRD，几轮 Agent 以后很容易发生状态升级。

例如原文：

```text
未来考虑加入 Summarization。
```

被另一个 Agent 总结成：

```text
Context Compiler supports Summarization.
```

或者：

```text
V2 planned to evaluate learned ranking.
```

最后在博客里变成：

```text
Hi-Agent 使用 learned ranking 优化 Context Selection。
```

技术名词越来越完整，事实却越来越错。

所以我现在愿意显式保留一层 claim state。

最简单可以只有：

| State | 含义 |
| --- | --- |
| `verified` | 有当前代码、测试、日志或一手资料支持 |
| `observed` | 当前确实观察到，但没有完整验证 |
| `decided` | 已经作出的设计决定 |
| `assumed` | 为推进工作暂时接受的假设 |
| `planned` | 准备做，但尚未实现 |
| `unknown` | 当前没有足够信息判断 |

例如：

```markdown
| Claim | State | Evidence |
| --- | --- | --- |
| Selector output is deterministic | verified | selector tests |
| required overflow should fail explicitly | decided | current Change |
| summarization will improve retention | assumed | not evaluated |
| learned ranking is implemented | planned | V2 only |
```

这看起来有一点像项目管理。

但它真正防的是：

```text
语态漂移
```

也就是：

```text
可能
→ 计划
→ 已决定
→ 已实现
→ 已验证
```

在多轮 Agent 协作里被逐渐压缩成同一个状态。

对于我这种会同时维护：

```text
项目代码
技术博客
研究笔记
未来 TODO
```

的人，这个区分尤其重要。

因为一项：

```text
planned experiment
```

如果进入博客时被写成：

```text
实验结果表明
```

就已经不是文风问题，而是事实错误。

---

### 5.5 Assumption 不是坏东西，但必须知道它什么时候失效

我以前写技术方案时，很少单独记录 Assumption。

例如：

```text
V1 数据量不大，所以先使用 SQLite。
```

这种话很容易顺手写进 Design，然后以后就被忘掉。

问题是任何 Design 都依赖前提。

比如：

```text
使用 SQLite
```

可能依赖：

```text
单机运行
写入并发低
数据量有限
没有跨节点事务要求
```

如果三个月以后项目变成：

```text
多 worker
高并发写
远程部署
```

继续引用：

```text
“之前已经决定用 SQLite”
```

就失去了意义。

所以我现在更希望 Assumption 写成：

```markdown
## Assumption A1

V1 runs as a single local process with low write concurrency.

This assumption supports the decision to use SQLite.

Re-evaluate when:
- multiple writers are introduced;
- the service becomes distributed;
- write contention appears in profiling.
```

这里最有用的不是：

```text
Assumption
```

这个标签。

而是：

```text
Re-evaluate when
```

因为它把一个临时成立的决定，从永久真理改成：

```text
在条件 C 成立时有效。
```

同样，Context Selector 也可以写：

```markdown
## Assumption A2

The deterministic greedy selector is sufficient as the V1 baseline.

Re-evaluate when:
- token utilization becomes a measured bottleneck;
- ranking quality is evaluated with a labeled dataset;
- learned or optimization-based policies can be compared against the baseline.
```

这比直接写：

```text
Greedy is enough.
```

可靠得多。

因为后者几年以后仍然看起来像架构原则。

---

### 5.6 Task 的大小最终还是由“能否单独失败”决定

回到文章最开始那个：

```text
6～8 Tasks
```

的问题。

现在我会用一个更具体的方法判断任务是不是拆对了：

> **这个 Task 有没有自己独立的失败状态？**

例如：

```text
Task 1：实现 Context 系统
```

几乎无法独立失败。

因为它里面同时包含：

```text
Budget
Selector
Compiler
Formatter
Trace
Provider Payload
```

其中三个完成、三个失败时，我不知道 Task 到底算什么状态。

相反：

```text
Task：实现 Required Context Preservation
```

可以明确失败：

```text
required item 被 dropped
```

也可以明确成功：

```text
required-fit
optional-trim
required-overflow
```

几个 case 都满足。

另一个例子：

```text
Task：支持 OpenAI Provider
```

还是太大。

可以继续拆成：

```text
Task A
将 CompiledContext 转成 provider-neutral ContextMessage

Task B
将 ContextMessage 映射成 OpenAI payload

Task C
保证 provider formatting 不改变 selection result
```

三个 Task 都有独立验证点。

所以现在我的拆分规则大概是：

```text
一个 Task 应该有：

明确输入
明确责任边界
明确依赖
明确输出
明确失败状态
明确验证方法
```

而不是：

```text
一个 Task 应该刚好需要半天。

一个 Feature 应该拆成 8 个 Task。
```

时间估计仍然有价值，但不应该定义语义边界。

---

### 5.7 Verification 也要按 Claim 分层，不能把一次 `pytest` 扩张成所有结论

SDD 里另一个很容易滥用的词是：

```text
Verified
```

例如 Agent 跑：

```bash
pytest tests/context/test_selector.py -q
```

输出：

```text
12 passed
```

这能支持的 Claim 是：

```text
本次运行中，
这 12 个 selector tests 全部通过。
```

它不能自动支持：

```text
Context 模块所有测试通过。

Hi-Agent 测试全部通过。

真实 Provider 集成正常。

Context quality 得到提升。

生产环境没有 regression。
```

这些结论分别需要不同证据。

所以我现在会把 Verification 理解成：

```text
Evidence
      ↓
supports
      ↓
Claim
```

而不是：

```text
有一个绿色命令
      ↓
整个项目 verified
```

例如：

```markdown
## Evidence

E1:
`pytest tests/context/test_selector.py -q`

Result:
`12 passed`

Supports:
- required-fit selector behavior;
- optional trimming behavior;
- required-overflow behavior.

Does not support:
- Compiler integration;
- provider payload correctness;
- full test suite status;
- LLM answer quality.
```

这种写法看起来有一点保守。

但它能防止我博客里以前很容易出现的：

```text
测试全部通过
```

实际上只跑了某个子目录。

也能防止 Agent 在完成 Task 后总结：

```text
The feature is fully verified.
```

而实际只是：

```text
unit tests passed.
```

我越来越愿意接受：

```text
当前只验证到这里
```

这种结论。

因为未验证的范围不会因为文章写得流畅就自动消失。

---

### 5.8 我自己的 Lightweight SDD 最终大概长这样

把前面内容压到真正能使用的程度，我现在日常不会打开一套十二阶段流程。

对于普通但值得认真做的 Change，我会走：

```text
1. Intent
   这次为什么改？

2. Scope
   改什么，不改什么？

3. Requirements
   哪些行为必须成立？

4. Clarifications
   哪些歧义如果不解决，Agent 就必须替我决定？

5. Decisions
   哪些关键实现选择已经确定？

6. Tasks
   哪些工作可以独立执行、独立失败、独立验证？

7. Implementation
   Agent 实际修改。

8. Evidence
   哪些检查实际运行了，分别证明什么？

9. Reconcile
   实现与 Spec 不一致时，改实现还是改 Spec？
```

根据风险，有些步骤可以折叠。

最轻：

```text
Task
→ Diff
```

普通：

```text
Requirement
→ Task
→ Tests
```

中等：

```text
Spec
→ Design
→ Tasks
→ Implementation
→ Verification
```

高风险：

```text
Project Invariants
→ Proposal
→ Spec
→ Clarify
→ Design
→ Tasks
→ Negative Cases
→ Implementation
→ Independent Verification
→ Rollback / Reconcile
```

这里没有：

```text
必须拆 8 个任务
```

也没有：

```text
每次必须创建 5 个文件。
```

只有一个持续不变的问题：

> **这次修改里，哪些东西如果不提前写清楚，就只能让 Agent 猜？**

那些地方才值得增加 SDD 的重量。

---

### 5.9 一个我现在不会再做的例子：先让 Agent 写完，再反推 Spec

还有一种工作方式表面效率很高：

```text
先让 Agent 实现
      ↓
代码跑通
      ↓
让 Agent 根据现有代码生成 Spec
```

这种方法不是完全没有价值。

对于：

```text
接手遗留系统
补文档
做 reverse engineering
```

它当然合理。

但如果本来是一个新 Change，再这么做，就会产生一个很危险的方向：

```text
Implementation
      ↓
Spec
```

这时 Spec 描述的往往不再是：

```text
我们希望什么行为成立
```

而是：

```text
Agent 恰好实现成什么样
```

例如 Agent 自己选择：

```text
required overflow → truncate
```

然后反向生成 Spec：

```text
The selector truncates required context when the budget is exceeded.
```

文档和代码现在完全一致。

但产品决定已经被实现偷偷做掉了。

所以我会区分：

```text
Descriptive Spec
描述系统现在事实上怎样工作

Normative Spec
定义系统应该怎样工作
```

对遗留系统做逆向整理时：

```text
Implementation
→ Descriptive Spec
```

没有问题。

对一个尚未实现的新需求：

```text
Intent
→ Normative Spec
→ Implementation
```

仍然更重要。

否则所谓 Spec-Driven Development 会退化成：

```text
Code-Driven Documentation
```

只是 Markdown 看起来很整齐。

---

### 5.10 到这里，SDD 已经解决了“做什么”，但还没有解决“Agent 能不能真的做到”

假设现在我已经有一份相当完整的 Task：

```markdown
## Requirement

Cold startup P95 must be below 800 ms
under the defined benchmark environment.

## Verification

- start from a clean process;
- execute the benchmark workload 20 times;
- record startup latency;
- compute P95;
- fail when P95 >= 800 ms.
```

从 Spec 的角度，这已经比：

```text
优化启动速度
```

强很多。

但 Coding Agent 拿到它以后，还可能面对另一组完全不同的问题：

```text
它能不能启动真实服务？

有没有 benchmark command？

能不能访问 Metrics？

有没有浏览器？

有没有数据库？

能不能读 Logs？

它是否有修改配置的权限？

测试失败以后能否继续迭代？

Context 不够以后怎样恢复？

进程挂了以后任务状态还在不在？
```

这些都不是继续把 Spec 写长能够解决的。

同样：

```text
Requirement:
用户完成支付以后必须看到真实购买权益。
```

Spec 可以定义：

```text
什么叫支付成功
什么叫权益成功
什么状态不能算完成
```

但如果 Agent 根本：

```text
查不到链上状态
访问不了数据库
看不到 delivery result
不能执行真实验证
```

那它仍然无法获得 Evidence。

这就是我后来开始把 SDD 和 Harness Engineering 分开的原因。

SDD 主要解决：

```text
What should be true?
```

也就是：

```text
目标
约束
行为
边界
完成条件
```

Harness 则开始解决：

```text
How can the Agent act and observe?
```

例如：

```text
Tools
Permissions
Sandbox
Context
Runtime
Browser
Logs
Metrics
Tests
Trace
Feedback
```

而当任务不再只是一个 Session，而是：

```text
几十个 issue
多个 workspace
多次 Agent run
失败后恢复
Human Review
PR / CI 回流
```

还会再往上一层进入 orchestration。

所以到这里，我不会继续试图通过：

```text
更长的 Spec
```

解决所有 Agent Engineering 问题。

一份 Spec 可以非常清楚地告诉 Agent：

```text
什么结果才算正确。
```

但它不会凭空给 Agent：

```text
浏览器
权限
日志
可观测性
隔离环境
任务状态
失败恢复
```

这也是这篇 SDD 笔记接下来必须划清的一条边界：

```text
Spec
定义目标状态

Harness
让一次 Agent run 有能力行动、观察和验证

Orchestration
让多个任务和多次 run 能够被持续调度、隔离、恢复和交接
```

如果这三层继续混在一起，那么：

```text
OpenSpec
Spec Kit
Claude Code
Harness Engineering
Symphony
```

最后又会重新被塞进一个名叫“Agent Workflow”的大桶里。

而前面花这么多时间区分 Spec、Design、Tasks 和 Evidence，也就失去了意义。

## 6. 把 SDD 用回自己的项目：先验证“契约”到底能不能减少 Agent 猜测

如果这篇文章最后只是把 OpenSpec 和 Spec Kit 的目录结构整理一遍，对我自己的开发方式没有任何改变，那它仍然只是一篇工具笔记。

所以我想把前面得到的几条原则重新放回自己的项目里。

这里我没有打算马上给 Hi-Agent 全面引入：

```text
openspec/
.specify/
constitution.md
proposal.md
design.md
tasks.md
```

也不准备为了证明“我在用 SDD”，把现有 PRD 和 TRD 全部迁移。

我更想验证一个更小的问题：

> **把 Requirement、Decision、Task 和 Evidence 明确分开以后，是否真的能减少 Agent 在长任务中自行补全语义的次数？**

这个问题甚至不只存在于代码项目。

我自己维护的 `Hugo-Blog-Skills` 恰好就是一个很适合观察这种问题的例子。

它处理的不是：

```text
source code
→ executable binary
```

而是：

```text
raw material
→ research
→ shape
→ beats
→ draft
→ edit
→ verification
```

表面看是博客写作，实际也不断遇到和 Coding Agent 相同的问题：

```text
输入材料里什么是事实？

什么只是作者计划？

什么内容已经验证？

什么只是一个待验证的推断？

编辑器允许改什么？

哪些数字、路径、引用不能被润色掉？

没有运行 Hugo build 时，
能不能说“文章已经可以发布”？
```

如果这些边界只留在 Prompt 里，写作 Agent 一样会猜。

所以我开始把这类流程也当成 contract 来设计。

---

### 6.1 从 Source 到 Draft，每一步都应该知道自己能改什么、必须保留什么

最早让 Agent 整理一堆技术笔记时，我很容易直接写：

```text
根据这些材料，
帮我整理成一篇完整博客。
```

这句话把太多责任压进了一次调用：

```text
理解材料
判断事实
补充研究
设计结构
决定教学顺序
写正文
润色
检查引用
判断完成状态
```

只要最后文章读起来通顺，中间发生了什么几乎不可见。

例如原始材料里写：

```text
V2 计划尝试 Mem0、Zep 和 LangMem。
```

经过几轮总结以后，可能变成：

```text
Hi-Agent 的 Memory 层集成了 Mem0、Zep 和 LangMem。
```

语句更完整，事实却被改变了。

或者原材料里只有：

```text
pytest tests/context/test_selector.py -q
12 passed
```

正文最后却写成：

```text
Hi-Agent Context 模块所有测试均已通过。
```

这类错误和 Coding Agent 把：

```text
planned behavior
```

当成：

```text
implemented behavior
```

本质上是同一种问题。

所以在 `Hugo-Blog-Skills` 里，我后来更愿意把流程拆成职责明确的中间状态：

```text
Source Set
    ↓
Shape
    ↓
Beats
    ↓
Draft
    ↓
Edit
    ↓
Validator / Verification
```

这里最重要的不是文件数量，而是每一步拥有不同权限。

例如 Source Set 可以包含：

```text
原始 Markdown
代码
日志
论文
官方文档
用户自己的推断
TODO
```

Shape 可以重新组织：

```text
文章从哪个问题开始？

哪些概念必须先解释？

哪些材料属于同一节？

哪些地方缺证据？
```

但它不应该把：

```text
planned
```

改成：

```text
verified
```

Beats 可以决定知识进入正文的顺序：

```text
先解释 Requirement
再解释 Delta Spec
再解释 Artifact Graph
```

却不能因为这一顺序更好讲，就创造一个原材料里不存在的实验结果。

Draft 可以把碎片改成完整段落，却不能为了语言流畅改变：

```text
数字
日期
代码
命令
路径
引用
否定关系
因果关系
不确定性
```

Validator 最后检查的也不应该只是：

```text
Markdown 格式对不对？
```

还要检查：

```text
完成声明有没有证据？

事实状态有没有被升级？

原始数字有没有漂移？

链接和引用有没有丢？

没有执行的检查，
是否被写成已经通过？
```

这套写作链路和软件 SDD 并不相同。

我不会说：

```text
写博客就是写软件。
```

但它们共享一个问题：

> **Agent 会把模糊输入补全成一个看起来连贯的结果，所以必须明确哪些补全是允许的，哪些状态变化必须有证据。**

换句话说，SDD 对我真正有用的部分不只是：

```text
功能开发前写 Spec
```

而是：

```text
任何多阶段 Agent workflow，
都应该明确阶段之间传递的 contract。
```

---

### 6.2 “验证通过”本身也必须有 Scope，不能让一句话越过证据边界

我在写作 Skill 里碰到过一个特别适合解释 SDD 的问题：

```text
到底什么时候可以说“通过”？
```

假设一次检查实际只运行了：

```text
C04  passed
C20  passed
C21  passed
```

而：

```text
pytest
Hugo build
link checker
```

都没有运行。

这时合理结论是：

```text
C04、C20、C21 已通过。

Pytest 未检查。
Hugo build 未检查。
Link check 未检查。
```

而不是：

```text
所有测试通过。
```

也不是：

```text
文章已完成验证，可以发布。
```

问题不在于后两句话“太自信”。

它们在逻辑上扩大了证据的作用域。

可以把它写成一个很简单的关系：

```text
Evidence E
supports
Claim C
```

如果：

```text
scope(E) ⊂ scope(C)
```

那么 Claim 就越界了。

例如：

```text
E1:
selector unit tests passed

C1:
selector unit tests passed
```

成立。

但：

```text
E1:
selector unit tests passed

C2:
Context subsystem is fully verified
```

不成立。

因为：

```text
selector tests
```

只覆盖：

```text
Context subsystem
```

的一部分。

这个问题看起来只是写作措辞，但放回 Coding Agent 就非常常见。

Agent 完成一个 Task 后经常会输出：

```text
Implementation complete.
All tests pass.
Feature verified.
```

实际上它可能只执行了：

```bash
pytest tests/unit/test_selector.py
```

甚至可能只是：

```text
阅读测试文件后认为应该通过
```

如果 SDD 最后仍然允许这种 completion claim，前面把 Acceptance Criteria 写得再详细也没有用。

所以我现在希望 Verification Artifact 至少回答：

```text
执行了什么？

结果是什么？

这个结果支持哪条 Requirement？

哪些相关检查没有执行？

还有哪些行为只能算 observed，
不能算 verified？
```

例如：

```markdown
## Verification Evidence

### E1 — Required preservation

Command:

    pytest tests/context/test_selector.py -k required_preservation -q

Observed result:

    passed

Supports:

- R1: required items are preserved when they fit the hard budget.

Does not verify:

- Compiler propagation;
- provider payload behavior;
- full Context test suite.

### E2 — Required overflow

Command:

    pytest tests/context/test_selector.py -k required_overflow -q

Observed result:

    passed

Supports:

- R2: required overflow fails explicitly.

Not checked:

- production provider integration;
- full repository test suite;
- runtime latency.
```

这种记录当然比一句：

```text
tests passed
```

啰嗦。

但它有一个实际收益：下一次 Agent 不需要猜：

```text
上一次到底测到了哪里。
```

更重要的是，它不会把：

```text
局部绿色
```

自动传播成：

```text
全局绿色
```

这也是我现在理解 Verification 的原因。

Verification 不是 SDD 流程末尾的一个勾：

```text
[x] Verify
```

而是一组：

```text
Requirement
↔
Evidence
```

之间可以追踪的关系。

---

### 6.3 我准备拿一个真实 Change 跑一次 OpenSpec，而不是继续凭感觉评价 SDD

到这里还有一个问题。

我可以写：

```text
OpenSpec 的 Delta Spec 很合理。

Spec Kit 的 Clarify 很有帮助。

Lightweight SDD 比直接 Prompt 更可靠。
```

这些都是分析。

但它们还不是实验结果。

如果我没有真的拿一个 Change 从头走过一次，就不能继续写成：

```text
SDD 显著提高了开发效率。

SDD 减少了返工。

OpenSpec 提高了 Agent 代码质量。
```

这些都是需要数据的 Claim。

所以我更想把下一次合适的 Hi-Agent Change 留作一个前瞻实验。

不选：

```text
改一个 typo
```

也不选：

```text
从零重写整个 Memory 系统
```

而是找一个中等复杂度、存在真实设计分支、又能够独立验收的 Change。

在开始以前先冻结：

```text
Repository commit
OpenSpec version
Coding Agent
Model
主要工具
任务范围
```

然后保留一份 Baseline。

Baseline 不要求故意让 Agent 做坏，只使用我原来的工作方式：

```text
PRD / TRD
→ Tasks
→ Agent implementation
→ Tests + Diff
```

记录：

```text
初始 Prompt
总对话轮次
人工澄清次数
Agent 主动修改过的文件
测试失败次数
返工次数
最终 diff
最终 verification evidence
未解决问题
```

下一次选择结构相近的 Change，再使用：

```text
Proposal
→ Delta Spec
→ Design
→ Tasks
→ Apply
→ Verify
→ Archive
```

同样保存：

```text
artifact 内容
Agent 输入
命令输出
人工干预
Spec 修改次数
Design 回退次数
Task 漏项
Verification 结果
最终 diff
```

我真正想观察的不是：

```text
用了 OpenSpec 以后感觉更专业。
```

而是几个可以记录的问题。

例如需求歧义：

```text
Implementation 开始以后，
还有多少次需要我补产品决定？
```

任务覆盖：

```text
有没有 Requirement 在 Tasks 中完全丢失？
```

实现漂移：

```text
有没有代码实现了 Spec 没要求的行为？
```

验证：

```text
每条关键 Requirement 最后能不能找到直接 Evidence？
```

返工：

```text
因为需求理解错误造成了多少次代码重写？
```

Artifact 修改：

```text
实现过程中发现新事实以后，
改的是 Spec、Design、Tasks，
还是只在聊天里临时告诉 Agent？
```

甚至可以记录 Context 成本：

```text
Agent 为了重新理解任务，
重复读取了多少材料？
```

不过第一次做这种实验时，我不会把它包装成严格的 A/B Test。

两个 Feature 很难完全等价：

```text
代码复杂度不同
模型状态不同
仓库状态不同
依赖不同
任务本身不同
```

一次 Baseline 和一次 OpenSpec run 最多能告诉我：

```text
流程在哪些地方暴露了以前不可见的信息。
```

它不能直接证明：

```text
OpenSpec 让效率提升 37%。
```

如果以后真想比较效率，需要多个可比任务、相同模型配置、重复运行和更稳定的评价标准。

对现在的个人学习项目来说，没有必要装成一篇实验论文。

第一轮只要把下面这些东西完整留下来就已经有价值：

```text
输入是什么？

中间工件是什么？

Agent 哪里理解错了？

哪一步发现错误？

谁修正了错误？

最终有什么证据？

哪些地方 SDD 没有解决？
```

这样下一次我再写：

```text
“OpenSpec 对我最有帮助的是……”
```

至少可以指向一次真实 run，而不是从 README 里推出来。

---

### 6.4 我更想观察失败发生在哪一层，而不是只统计“成功 / 失败”

如果真的跑这次实验，我还想把失败分类。

因为：

```text
Agent 没做对
```

这个结论太粗。

例如一个任务失败，可能是：

```text
Requirement 没说清
```

也可能是：

```text
Design 本身错误
```

还可能是：

```text
Tasks 漏项
```

或者：

```text
Agent 明明知道要求，
但实现代码写错了
```

甚至：

```text
实现其实正确，
Harness 没提供验证环境，
所以无法证明
```

这几种情况对应完全不同的改进方向。

我准备至少分成：

| Failure | 表现 | 应优先改什么 |
| --- | --- | --- |
| Requirement gap | Agent 必须猜行为 | Spec / Clarify |
| Design gap | 行为清楚，但实现路线不成立 | Design |
| Decomposition gap | Requirement 没进入 Task | Tasks / Analyze |
| Implementation error | Spec 与 Task 清楚，代码仍然错误 | Coding Agent / implementation loop |
| Verification gap | 有实现，但没有足够证据判断 | Harness / eval |
| Runtime gap | Agent 缺工具、权限或环境 | Harness |
| Lifecycle gap | 任务掉线、重复执行、状态丢失 | Orchestration |

这张表能防止一种我以前很容易做的事：

```text
Agent 做错了
→ Prompt 写得再详细一点
```

如果根因其实是：

```text
Agent 根本没有浏览器
```

继续加 Prompt 没用。

如果根因是：

```text
Requirement 没定义失败语义
```

增加工具同样没用。

SDD 的价值之一，就是让我能先问：

```text
错误是不是在“正确性定义”这一层就已经存在？
```

如果答案是，那就应该先修 Spec。

如果 Spec 已经足够明确，而 Agent 仍然无法行动或观察，就不应该继续往 Spec 里塞运行时细节。

这正好把文章带到最后一条边界。

前面讨论的 OpenSpec、Spec Kit 和 Lightweight SDD，都还主要站在：

```text
定义 Change
```

这一侧。

但 Coding Agent 真正开始长期工作以后，还会出现：

```text
谁来发现新 issue？

哪个任务先执行？

一个任务在哪个 workspace 中运行？

失败以后什么时候重试？

进程退出以后谁恢复？

多个 Agent 会不会修改同一个目录？

CI 失败以后谁重新接管？

Human Review 之后如何继续？

任务什么时候才从 active 变成 done？
```

这些问题已经不是：

```text
Spec 应该再写清楚一点
```

能够解决的。

我最近看到 Symphony 时，正好发现它提供了一个很干净的切口：它自己的仓库顶层就放着一份语言无关的 `SPEC.md`，但那份 Spec 定义的不是某个 Feature 应该做什么，而是一个 **Agent Orchestrator 本身应该怎样运行**。

用它收尾，正好可以把：

```text
Task Spec
Harness
Orchestration
```

三层的责任彻底分开。

## 7. SDD 应该停在哪里：用 Symphony 划清 Spec、Harness 与 Orchestration

写到这里，我还剩一个容易混淆的问题。

前面一直在说：

```text
Requirement
→ Spec
→ Design
→ Tasks
→ Verification
```

但现实中的 Coding Agent 项目还有另一批东西：

```text
Linear issue
workspace
agent process
concurrency
retry
CI
PR
review
recovery
```

它们显然也和“让 Agent 完成任务”有关。

如果把所有这些东西都继续叫作：

```text
Spec-Driven Development
```

那么 SDD 最后会膨胀成：

```text
需求工程
+
软件设计
+
Agent Runtime
+
任务调度
+
CI/CD
+
多 Agent
+
项目管理
```

这个概念就失去边界了。

OpenAI 在 2026 年 4 月公开的 Symphony 恰好提供了一个很好用的分界案例。

Symphony 是一个面向 Coding Agent 的 orchestrator。OpenAI 的文章把它描述成：

```text
把 Linear 这类 project-management board
变成 Coding Agent 的 control plane。
```

它会持续读取任务，为符合条件的 issue 创建隔离 workspace，在里面启动 Coding Agent，并负责并发、失败重试、状态协调和恢复。

但 Symphony 仓库最值得注意的地方，不是它用了 Linear，也不是参考实现选择了 Elixir，而是仓库顶层直接放了一份：

```text
SPEC.md
```

而且文件开头写的是：

```text
Status: Draft v1 (language-agnostic)

Purpose:
Define a service that orchestrates coding agents
to get project work done.
```

这意味着同一个单词：

```text
Spec
```

在这里已经不是：

```text
“给 Hi-Agent 加一个 Required Context Preservation”
应该满足什么行为
```

而是：

```text
“一个 Agent Orchestrator”
本身应该满足什么行为。
```

这两个 Spec 都是规范，但规范的对象完全不同。

这正好可以用来把前面几层彻底分开。

### 7.1 Task Spec 定义的是“这次 Change 什么样才算正确”

先回到我前面一直讨论的 Required Context Preservation。

它的 Spec 可能是：

```markdown
### Requirement: Required context overflow

If required context items alone exceed the hard input budget,
selection MUST fail explicitly.

The system MUST NOT silently drop or truncate a required item
in order to satisfy the budget.
```

这里规定的是：

```text
业务 / 功能行为
```

它回答：

```text
完成这次 Change 以后，
哪些事实必须成立？
```

再例如：

```markdown
### Requirement: Export authorization

A user MUST NOT export records
that the user cannot read through the normal query API.
```

它仍然是在定义产品或系统行为。

我把这一层叫：

```text
Task Definition
```

典型工件可以是：

```text
Requirement
Acceptance Criteria
Feature Spec
Delta Spec
Proposal
Design
Tasks
```

这些工件最终服务于同一个问题：

> **Agent 这次到底应该交付什么？**

如果 Spec 写错了，Agent 即使严格按照它实现，结果也可能是错的。

所以这一层的失败主要表现为：

```text
需求歧义
遗漏边界
错误验收标准
Design 与 Requirement 混淆
Task 漏掉 Requirement
```

对应的修复对象也是：

```text
Spec
Clarification
Design
Tasks
```

而不是给 Agent 增加浏览器或重试队列。

---

### 7.2 Symphony 的 `SPEC.md` 规范的是 Orchestrator，不是某个 Feature

Symphony 的 `SPEC.md` 处在另一层。

它定义的对象是：

```text
Symphony Service
```

所以里面出现的 Requirement 是：

```text
轮询 issue tracker

限制最大并发 Agent 数量

为每个 issue 创建确定性的独立 workspace

issue 不再符合运行条件时停止对应 run

暂时性失败后进行 exponential backoff

重启以后根据 tracker 和 filesystem 恢复

暴露结构化日志

从仓库中的 WORKFLOW.md 加载运行策略
```

这些要求当然也是 Spec。

但它们没有告诉 Coding Agent：

```text
ABC-123 应该改哪个 API。

登录按钮应该长什么样。

Context overflow 应该抛什么语义错误。
```

它定义的是：

```text
谁负责把 Issue 变成 Agent Run，
以及这些 Run 怎样被长期管理。
```

换句话说：

```text
Task Spec

定义某一次工作完成后的正确状态。


Symphony SPEC.md

定义“管理这些工作”的服务本身应当怎样运行。
```

所以不能因为 Symphony 自己有一份 `SPEC.md`，就得出：

```text
Symphony 属于 SDD。
```

更准确的说法是：

```text
Symphony 自己也需要一个 Spec，
而它被规范的对象是 Orchestration Service。
```

任何软件都可以有 Spec。

数据库可以有 Spec，编译器可以有 Spec，Agent Harness 也可以有 Spec。

“使用 Spec 描述一个 orchestrator”与“orchestrator 属于任务定义层”不是同一件事。

---

### 7.3 `WORKFLOW.md` 又是第三种东西：仓库级的 Agent 运行策略

Symphony 里还有一个特别容易和 Task Spec 混淆的文件：

```text
WORKFLOW.md
```

按照它当前的语言无关规范，`WORKFLOW.md` 是一个 repository-owned、version-controlled 的运行契约。

文件由两部分组成：

```text
YAML front matter
+
Markdown prompt body
```

前面的配置可以描述：

```yaml
tracker:
  kind: linear

polling:
  interval_ms: 30000

workspace:
  root: ...

agent:
  max_concurrent_agents: ...

codex:
  command: codex app-server
```

还可以配置 workspace lifecycle hooks、Agent 参数等。

Markdown body 则作为每个 issue 的 Prompt Template。

所以 `WORKFLOW.md` 回答的问题更接近：

```text
这个仓库里的 Agent Run 应该怎样被配置？
```

例如：

```text
从哪个 tracker 读任务？

哪些状态属于 active？

workspace 放哪里？

一个仓库最多同时跑几个 Agent？

创建 workspace 后需要执行什么 hook？

Agent 收到 issue 后应该遵循什么工作规则？

完成以后交接到什么状态？
```

它既不是：

```text
某个 Feature 的 Requirement
```

也不是：

```text
Symphony Orchestrator 的语言无关实现规范。
```

可以把三者放在一起：

| 层次 | 典型工件 | 回答的问题 | 不负责什么 |
| --- | --- | --- | --- |
| Task Definition | Requirement / Acceptance Criteria / Feature Spec | 这次 Change 什么样才算正确 | 调度 issue、管理 workspace、重试 run |
| Repository Runtime Policy | `WORKFLOW.md` | 这个仓库中的 Agent 应采用什么 Prompt、配置、hooks 和交接规则 | 定义一个通用 orchestrator 应怎样实现 |
| Orchestration Service Spec | Symphony `SPEC.md` | scheduler、runner、tracker reader、retry、reconciliation、workspace lifecycle 应满足什么行为 | 决定某个具体 Feature 的产品需求 |
| Runtime | Symphony implementation + Coding Agent | 哪个 issue 现在执行、在哪执行、失败后什么时候再试 | 替产品重新决定验收标准 |

这个分层解决了我之前一个很容易混在一起的问题：

```text
“Spec”
```

并不是一种固定文件格式。

它必须先回答：

```text
Spec of what?
```

---

### 7.4 Symphony 管理的是 Issue → Run 的生命周期

如果把一个具体任务放进去，Symphony 的责任会更容易看出来。

假设 Linear 中有：

```text
HA-127

Title:
Fail explicitly when required context exceeds hard budget
```

这个 issue 自己可能已经有足够清楚的任务定义：

```text
Requirement
Acceptance Criteria
Design
Tasks
```

此时 Symphony 不需要重新判断：

```text
required overflow 到底应该 truncate 还是 fail。
```

这件事应该在任务定义阶段已经决定。

Symphony 更关心另一组状态。

例如：

```text
Linear
  │
  │ HA-127 becomes eligible
  ▼
Orchestrator
  │
  │ concurrency available?
  ▼
Workspace Manager
  │
  │ create isolated workspace
  ▼
Agent Runner
  │
  │ render WORKFLOW.md + issue context
  ▼
Coding Agent
  │
  │ edit / test / inspect
  ▼
handoff
```

如果 Agent 进程挂掉，Task Spec 并不会告诉系统：

```text
30 秒后重试还是 5 分钟后重试？
```

如果两个 issue 同时进入 active state，Task Spec 也不会决定：

```text
最大并发是多少？
```

如果 issue 被人从：

```text
In Progress
```

改成：

```text
Cancelled
```

Task Spec 同样不会告诉一个长期运行的 daemon：

```text
应该停止对应 Agent。
```

这些都是 orchestration state。

Symphony 当前规范里维护的状态就包括：

```text
running

claimed

retry_attempts

completed

token / runtime totals

rate-limit snapshot
```

Orchestrator 根据这些信息决定：

```text
dispatch
retry
stop
release
reconcile
```

这里的中心对象已经不是：

```text
Requirement
```

而是：

```text
Run Lifecycle
```

所以我会把 Orchestration 理解成：

> **管理任务与 Agent Run 之间的映射，以及这些 Run 在时间上的生命周期。**

---

### 7.5 Workspace Isolation 也不是 Feature Spec 应该承担的责任

Symphony 规范里还有一类要求：

```text
每个 issue 使用独立 workspace。
```

而且它明确要求 Agent 只能在对应 issue 的 workspace 中运行，并要求 workspace path 始终位于 workspace root 之下。

这种约束非常重要，但我不会把它塞进每个 Feature Spec：

```markdown
### Requirement

The user can enable dark mode.

### Requirement

Agent MUST execute inside an isolated workspace.
```

两句话的作用域不同。

前一句属于产品行为。

后一句属于：

```text
Agent Execution Environment
```

如果把它们混在一起，每份 Feature Spec 最后都会重复：

```text
必须 sandbox
必须独立 workspace
必须记录日志
必须限制并发
必须支持 retry
```

这些实际上是执行系统的长期约束。

所以更合理的是：

```text
Feature Spec
告诉 Agent：
改成什么样。


Orchestrator / Harness Policy
告诉系统：
Agent 在什么环境里改。
```

这个区别也解释了为什么：

```text
Spec 写得再完整
```

仍然无法替代 workspace isolation。

Spec 可以规定：

```text
不得修改 unrelated files。
```

但如果两个 Agent 本来就在同一个工作目录并行运行，仍然可能发生：

```text
Agent A
修改 package.json

Agent B
同时修改 package.json

Agent A
跑测试时读到 B 的半成品
```

这种错误不是再补一句：

```text
Please don't interfere with other agents.
```

就能可靠解决的。

它需要运行环境本身提供隔离。

---

### 7.6 Harness 和 Orchestration 也不是同一层

到了这里，还剩下一个容易混淆的关系：

```text
Harness
vs
Orchestration
```

因为两边都会出现：

```text
Agent
Tools
Runtime
State
```

我现在会用“单次 Run”和“多次 Run”来区分它们。

假设 Symphony 已经选中了：

```text
HA-127
```

并创建：

```text
workspace/HA-127
```

接下来 Coding Agent 真正进入这个 workspace 后，它还需要：

```text
读文件
改文件
执行 shell
运行测试
读取日志
调用浏览器
控制权限
管理 Context
接受 tool_result
处理中断
记录 Transcript
```

这些更接近 Harness 的责任。

例如 Claude Code 的 Harness 可以处理：

```text
LLM
 ↓
tool_use
 ↓
permission
 ↓
tool execution
 ↓
tool_result
 ↓
LLM
```

并维护一次 session 内的：

```text
conversation state
tool state
context
permissions
abort
usage
transcript
```

所以对于一次具体 Run：

```text
Harness
```

提供的是：

> **让 Agent 能够在真实环境中行动、观察、得到反馈并继续迭代的执行条件。**

而 Symphony 关注：

```text
这个 Run 为什么现在启动？

应该在哪个 workspace？

它是否仍然 eligible？

同时还能跑几个？

失败以后什么时候再启动？

重启后如何重新发现它？

什么时候释放 claim？
```

这就是 orchestration。

可以压成：

```text
Task Spec
    │
    │ what should be true?
    ▼
Orchestrator
    │
    │ which work runs, where and when?
    ▼
Harness
    │
    │ how can this run act and observe?
    ▼
Coding Agent
    │
    │ reason + act
    ▼
Repository / Runtime
```

这里为了说明责任关系画成一条链，但实际并不是严格的调用栈。

Harness 可能包含 Codex CLI、Claude Code 或其他 Coding Agent Runtime；Orchestrator 则在更长时间尺度上管理这些 Runtime 的创建、停止和恢复。

---

### 7.7 一个完整例子：`启动 P95 < 800 ms` 分别落在哪一层

前面我留过一个性能 Requirement：

```text
Cold startup P95 < 800 ms
```

现在可以把它从 Spec 一直放到执行系统里。

Task Spec 先定义：

```markdown
### Requirement

Cold startup latency P95 MUST be below 800 ms
under the benchmark profile.

### Acceptance

- execute 20 clean-process startup runs;
- collect startup latency;
- calculate P95;
- fail verification when P95 >= 800 ms.
```

这一步解决：

```text
什么叫正确。
```

Design 再决定：

```text
准备从哪里计时？

哪个事件代表 ready？

benchmark script 放在哪里？

指标怎样采集？
```

Tasks 把实现拆开：

```text
T1:
add benchmark entry point

T2:
remove synchronous startup bottleneck

T3:
record startup metric

T4:
add benchmark verification
```

到这里 SDD 已经可以停了。

因为 Agent 真正开始验证时，需要的是：

```text
启动真实服务
     ↓
执行 workload
     ↓
读取 ready signal
     ↓
采集 latency
     ↓
重复 20 次
     ↓
计算 P95
     ↓
与 800 ms 比较
```

这些动作需要 Harness 提供真实环境。

如果 Agent 没有 shell：

```text
Spec 再详细也跑不了 benchmark。
```

如果它能运行服务，但读不到 metrics：

```text
仍然不能验证 P95。
```

如果 benchmark 经常跑十几分钟导致 Context 被压缩：

```text
Harness 还要处理 session continuity。
```

如果现在同时有：

```text
HA-127 优化 Context
HA-128 优化 Startup
HA-129 修复 Login
HA-130 升级 Database
```

而我希望四个任务能够在不同 workspace 中自动推进，失败自动恢复，CI 结果回来后继续处理，那就再进入 Symphony 处理的 orchestration。

因此：

```text
启动 P95 < 800 ms
```

不是一句 Spec 就能形成完整 Agent workflow。

它在不同层分别变成：

| 层 | 负责什么 |
| --- | --- |
| Spec | 定义 `< 800 ms` 以及统计口径 |
| Design | 定义测量路径与技术实现 |
| Tasks | 拆成可执行工作 |
| Harness | 启动服务、执行 benchmark、读取 metrics、反馈结果 |
| Orchestration | 决定这个任务何时运行、在哪个 workspace、失败后怎样恢复 |

这也是我现在最愿意保留的边界。

---

### 7.8 Symphony 并不替 Agent 写 Ticket，这是一个很容易说错的地方

第一次看 Symphony 的介绍时，我很容易把整个流程脑补成：

```text
Symphony
读取 Linear
→ 修改代码
→ 跑 CI
→ 更新 Ticket
→ 发 PR
→ 回评论
→ 标记 Done
```

但当前 `SPEC.md` 对这一点划得比这个更细。

它明确把 Symphony 定义为：

```text
scheduler / runner
+
tracker reader
```

而 Ticket Write，例如：

```text
状态迁移
评论
PR 链接
```

通常由 Coding Agent 使用运行环境里提供的工具完成。

这意味着：

```text
Orchestrator
```

不应该不断吸收业务工作流逻辑。

例如：

```text
如果 CI 失败三次就给 Linear 写哪句话；

PR 创建以后应该添加什么 label；

什么时候从 In Progress 改到 Human Review。
```

这些策略可以存在于：

```text
WORKFLOW.md
+
Agent tools
```

而不是硬编码进通用 Scheduler。

这个边界很像前面 Spec 和 Design 的分离。

如果把所有团队工作流都写死进 Orchestrator：

```text
Symphony
```

很快就会退化成一个：

```text
只能适配某个团队流程的巨大状态机。
```

所以它的规范把通用协调机制和 repo-specific policy 分开。

我觉得这一点比：

```text
Symphony 支持 Linear
```

本身更值得学。

---

### 7.9 “成功”也不一定等于 `Done`

Symphony 规范里另一个值得保留的细节是：

```text
successful run
```

不要求一定把 issue 推到：

```text
Done
```

成功的 Run 可以停在 workflow 定义的 handoff state，例如：

```text
Human Review
```

这和前面讨论 Verification 很一致。

一个 Coding Agent 可以成功完成：

```text
代码实现
测试
PR
证据整理
```

但团队仍然规定：

```text
必须人工 Review 才能 Merge。
```

那么这一轮 Agent 的完成条件就是：

```text
ready for human review
```

而不是：

```text
整个业务任务已经终结。
```

如果不区分：

```text
Run Completion
Issue Completion
Product Completion
```

很容易又产生 completion claim 膨胀。

例如：

```text
Agent Run succeeded.
```

并不能自动推出：

```text
PR merged.
```

更不能推出：

```text
feature deployed.
```

所以在 Orchestration 层也仍然需要我们前面使用过的那种 Scope Discipline：

```text
哪个状态变化实际发生了，
就只报告到哪个状态。
```

---

### 7.10 到这里，我会明确停止继续扩张 `spec.md`

如果继续往下写，还可以展开很多内容：

```text
Linear 如何作为 Control Plane

Issue eligibility

Dependency DAG

Per-issue workspace

Concurrency control

Exponential backoff

Reconciliation

Restart recovery

CI feedback

PR review

Human handoff

Multi-Agent coordination
```

但我不会把这些继续塞进这篇 SDD 笔记。

因为到了这里，问题已经从：

```text
Agent 应该做什么？
```

变成：

```text
任务怎样被持续调度和执行？
```

这应该进入单独的 orchestration 笔记。

同样，我也不会在这里完整展开：

```text
Context compaction

Tool contract

Permission

Sandbox

Transcript

Evaluator

Browser / Logs / Metrics

Agent Loop
```

这些更适合 Harness。

所以我现在对三个目录的划分会比较稳定：

```text
agent/workflow/spec.md

Requirement
Spec
Design
Tasks
SDD
Verification Contract


harness/

Tool
Permission
Context
Runtime
Sandbox
Observation
Verification Loop


agent/orchestration/

Issue
Workspace
Run
Scheduler
Concurrency
Retry
Reconciliation
Recovery
Handoff
Multi-Agent
```

这不是说三者互不相干。

恰恰相反，它们需要通过明确接口连接。

Task Definition 向下一层提供：

```text
目标
约束
任务
验收条件
```

Harness 让一次 Agent Run 能够：

```text
读取
修改
执行
观察
验证
```

Orchestration 再决定：

```text
哪些任务何时进入 Run，
Run 在哪里运行，
失败后如何继续，
结果交给谁。
```

如果前一层没有定义好，后一层只会更高效地执行模糊任务。

如果后一层没有提供执行条件，再完整的 Spec 也只能停留在 Markdown。

---

### 7.11 回到文章开头，我最终改变的是完成定义

我最开始的工作流是：

```text
PRD
→ TRD
→ 6～8 Tasks
→ Agent
→ Test + Diff
```

现在我不会把它全部推翻。

PRD 仍然可以写。

TRD 仍然可以写。

Task 仍然应该拆。

Diff 和 Test 仍然必须看。

真正改变的是，我不再用：

```text
文档写完了

任务拆完了

Agent 说 Done 了

测试出现绿色了
```

直接代表：

```text
Change 已经完成。
```

我会继续追问：

```text
哪些 Requirement 必须成立？

哪些只是 Design Decision？

哪些是假设？

哪些仍然是 Planned？

每个关键 Requirement 怎样被观察？

实际跑过什么验证？

当前 Evidence 能支持多大的 Claim？

实现和 Spec 不一致时，
究竟应该改代码还是改 Spec？
```

所以我现在自己的流程更接近：

```text
Intent
  ↓
Change
  ↓
Requirements
  ↓
Clarification
  ↓
Design Decisions
  ↓
Independently Verifiable Tasks
  ↓
Implementation
  ↓
Evidence
  ↓
Reconcile
```

OpenSpec 让我开始认真区分：

```text
Current Truth
vs
Change Delta
```

Spec Kit 让我开始在 Implementation 之前检查：

```text
Constitution
Ambiguity
Requirement Quality
Cross-artifact Coverage
```

而 Symphony 又提醒我：

```text
Spec 写清楚以后，
仍然需要另外一套系统管理工作的执行生命周期。
```

因此，我现在不会再把 SDD 理解成：

```text
在 Coding Agent 前面多写几个 Markdown。
```

它对我更实际的用途，是把原本藏在人脑、聊天记录和 Agent 临时推断里的：

```text
正确性
边界
决定
假设
任务
证据
```

拆成可以留下来的工程状态。

这篇文章到这里也应该停下来。

它只给下一层留下四类输入：

```text
Task Goal

Explicit Constraints

Executable Tasks

Observable Acceptance Criteria
```

至于 Coding Agent 怎样拿着这些输入进入真实仓库，怎样调用工具、管理 Context、读取日志、运行测试并根据失败继续修改，是 Harness 的问题。

当任务进一步变成多个 issue、多个 workspace 和多次 Agent Run以后，怎样轮询、调度、重试、恢复和交接，则进入 Orchestration。

Symphony 正好从这里开始。