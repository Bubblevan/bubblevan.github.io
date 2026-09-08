---
title: "Organizational Context"
weight: 1
---

## 1. 从 Prompt Engineering 到 Context Engineering

如果只看一次普通的 LLM 调用，输入问题似乎并不复杂。开发者写好 system prompt，用户给出任务，模型根据这些文字生成答案：

```text
System Prompt
User Prompt
Few-shot Examples
        │
        ▼
       LLM
        │
        ▼
    Response
```

在这种一次性生成任务里，Prompt Engineering 是一个相当准确的名字。工程工作的重点确实是怎样组织指令：角色怎么描述，约束写在哪里，是否提供示例，输出格式怎样规定。Agent 把这个问题扩大了。一个 Coding Agent 接到“修复这个测试失败”之后，不会只完成一次推理。它可能先读取文件，再搜索符号，运行测试，根据报错继续读取其他文件，修改代码，再次运行测试。在后续每一次模型调用里，模型面对的输入已经不只是最初那几段 prompt，还包括工具定义、此前的消息、刚才读取的源码、测试输出以及运行过程中不断产生的状态。

```text
System Instructions
User Request
Tool Definitions
Message History
Retrieved Files
Tool Results
External Data
Current Task State
        │
        ▼
       LLM
```

Anthropic 在 2025 年 9 月发布的 *Effective context engineering for AI agents* 中，把这种变化概括成从 Prompt Engineering 向 Context Engineering 的扩展：Prompt Engineering 主要处理如何编写和组织模型指令，而 Context Engineering 管理的是 **LLM 每次 inference 时实际得到的整组 token**。对于长时间运行的 Agent，这个集合除了 prompt，还会包含 tools、MCP、external data、message history 等不断变化的信息。这意味着 Agent Harness 里真正需要管理的对象已经发生了变化。

```text
Prompt Engineering
       │
       │  如何写好输入指令？
       ▼
Prompt

Context Engineering
       │
       │  当前这一次 inference
       │  应该让模型看到什么？
       ▼
Context
```

后一个问题明显更大，因为 Prompt 只是 Context 的一部分。

### 1.1 Prompt 只是 Context 的一部分

这里需要先固定本文对两个词的用法。本文所说的 **Prompt**，主要指开发者或者用户主动提供给模型的指令性信息，例如 system instructions、task description、few-shot examples 和 output contract。**Context** 则采用更宽的含义：模型在某一次 inference 中能够直接注意到的全部 token。因此可以先写下一个很简单的关系：

$$
\text{Prompt} \subset \text{Context}
$$

这不是说 prompt 不再重要，而是说，对于 Agent 来说，仅仅优化 prompt 已经无法控制模型真正面对的信息环境。假设最初的任务只有一句：

```text
修复 tests/test_auth.py 中失败的测试。
```

Agent 第一次 inference 可能看到：

```text
System Prompt
User Request
Tool Definitions
CLAUDE.md
```

它随后读取：

```text
tests/test_auth.py
src/auth/service.py
```

运行测试得到：

```text
AssertionError:
expected 401
received 500
```

又搜索 `validate_token`，读取调用链，并查看最近一次修改。到了第五次 inference，真正参与模型决策的输入已经更接近：

```text
最初的 System Prompt
+ 用户任务
+ Tool Schema
+ 前四轮 Message History
+ tests/test_auth.py
+ src/auth/service.py
+ grep 结果
+ pytest 错误
+ 已经尝试过但失败的修改
```

即使 system prompt 一个字都没有变化，模型工作的上下文已经完全不同。这也是为什么 Anthropic 把 Context Engineering 描述成一个持续发生的过程。Agent 在 loop 中每执行一步，都会产生新的潜在信息；Harness 下一轮必须重新决定哪些内容继续保留、哪些应该加入、哪些已经可以丢弃。可以把一次 Agent loop 粗略表示为：

```text
                  ┌──────────────────────┐
                  │   Available State    │
                  │                      │
                  │ prompt               │
                  │ messages             │
                  │ files                │
                  │ tool results         │
                  │ external data        │
                  │ persistent state     │
                  └──────────┬───────────┘
                             │
                     context selection
                             │
                             ▼
                    ┌────────────────┐
                    │ Current Context│
                    └───────┬────────┘
                            │
                            ▼
                           LLM
                            │
                            ▼
                       Tool / Answer
                            │
                            └───────► new state
```

这里有一个容易混淆的边界：**某条信息存在于系统里，不等于它存在于当前模型 Context 里。**源码当然存在于 repository 中，历史 issue 可能存在于 GitHub，项目决策可能存在于文档系统，Agent 自己上一轮留下的进度也可能存在于磁盘。但只要 Harness 没有把这些内容直接加载进当前 inference，它们就只是模型**可能获得的信息**，而不是模型**当前看到的信息**。于是 Context Engineering 至少包含两层状态：

```text
Available Information
        │
        │ selection / retrieval
        ▼
Current Model Context
```

后面讨论 Persistent Memory、Workspace Context 和 Organizational Knowledge 时都会反复遇到这个区别。一个组织可以拥有 TB 级文档，一个 Agent 也可以拥有整个代码库的读取权限，但这并不意味着一次 inference 应该承载 TB 级信息。真正的问题始终是：**当前这一步需要从那个更大的信息空间里取出什么。**

### 1.2 Context Window 不是仓库

随着模型 Context Window 从几千 token 增长到几十万乃至更大的数量，一个自然的想法是：既然窗口越来越长，为什么还要费力做 Context Engineering？把项目资料、历史消息和工具结果尽量完整地塞进去，不就可以避免遗漏吗？问题在于：

```text
Context Window 能装下
        ≠
这些信息应该同时出现
```

Anthropic 在文章里把 Context 描述成一种 **critical but finite resource**。这里的“有限”不能只理解成 API 上的最大 token 数。即使还没有碰到硬性的 Context Window 上限，模型处理越来越长的输入时也会面对注意力分散、检索精度下降和长距离依赖变难等问题。Anthropic 将这种随着 Context 增长而出现的性能退化联系到 `context rot`，并用 `attention budget` 来描述模型在大量输入之间分配注意力的约束。这和一种常见的工程直觉有冲突。我们很容易把 Context Window 想象成硬盘：

```text
容量还有剩余
→
继续往里面放
```

但它更接近 working memory。多放一条信息不只是占掉若干 token，也会增加模型需要区分、关联和选择的信息。Transformer 的 self-attention 让序列中的 token 可以彼此建立注意力关系。对于长度为 \(n\) 的序列，完整 attention 可以形成 \(n^2\) 量级的 token pair relationships。Anthropic 用这一点解释为什么更长的 Context 会在“能够容纳更多信息”和“维持注意力聚焦”之间形成张力。这里并不需要得出“长 Context 一定效果差”这样的结论；更准确的说法是，性能通常表现为一个逐渐变化的 gradient，而不是在某个 token 数突然发生断崖。不同模型的退化程度也可能不同。因此，下面两种 Context 即使 token 数都合法，也不具有相同的工程质量：

```text
Context A

任务目标
相关代码
当前错误
关键历史决策
需要使用的 Tool
```

```text
Context B

任务目标
整个 Repository 的大量源码
过去几十轮完整 Shell 输出
已经解决的问题
重复日志
无关文档
所有可能用到的 Tool
相关代码
当前错误
```

B 包含 A，信息量也更多，但这不自动意味着 B 更好。模型还需要从更多竞争信号中找到真正决定下一步行为的那几项。这也是为什么“更大的 Context Window”不会自动删除 Context Engineering 这个问题。Anthropic 在讨论 long-horizon agent 时明确指出，即使 Context Window 继续扩大，context pollution 和 information relevance 仍然会存在。对于 Harness 来说，更实用的判断因此不是：

```text
还能不能塞？
```

而是：

```text
这段信息是否值得继续占用
下一次 inference 的 attention budget？
```

这个问题会直接决定后面的多种机制为什么存在。旧的 raw tool result 如果已经被提炼成明确结论，就可能不需要永久保留；几十轮工作历史如果已经超出当前窗口，就需要 compaction；跨 session 才需要的状态可以写到 persistent memory；整个 repository 没必要预加载，可以在需要时通过 grep、glob、read 等工具取回；组织里数量更大的文档和会议记录更不可能直接进入 Prompt，而只能成为受权限和检索策略约束的信息源。这些机制表面上分别叫：

```text
compaction
memory
retrieval
tool result clearing
subagent isolation
```

但它们解决的是同一个资源分配问题：**不要把“系统知道什么”和“模型这一刻应该看到什么”混成一件事。**

### 1.3 从“更多 Context”转向“High Signal / Low Noise”

如果 Context 是有限的 attention resource，那么 Context Engineering 的目标也就不是最大化输入长度。Anthropic 给出的原则是寻找：

> the smallest possible set of high-signal tokens

也就是在满足任务要求的前提下，用尽可能紧凑、相关的信息提高模型产生目标行为的概率。这里的 `smallest` 不能机械理解成“token 越少越好”；Anthropic 紧接着也说明，minimal 并不等同于 short，Agent 仍然需要足够的信息才能正确工作。可以把这个问题抽象成一个选择过程。设当前时刻 \(t\)：

$$
I_t
$$

表示 Harness 理论上能够取得的全部信息，例如：

```text
system instructions
message history
files
tool results
memory
database rows
web pages
issues
documents
```

而：

$$
C_t \subseteq I_t
$$

表示最终真正送入这一次模型 inference 的 Context。如果模型当前的有效 Context budget 为 \(B_t\)，那么我们希望找到：

$$
C_t^*
=
\arg\max_{C \subseteq I_t,\;\operatorname{Tokens}(C)\le B_t}
U(C\mid G_t)
$$

其中：

$$
G_t
$$

表示当前需要完成的目标，而 \(U(C\mid G_t)\) 表示这组 Context 对完成当前目标的有效程度。这个公式是**本文为了组织后续讨论给出的抽象，不是 Anthropic 原文中的公式，也不是要求 Harness 真正运行一个组合优化算法。** 实际系统很少能够精确计算某段文本的 \(U\)。它更像一个设计检查表：每当我们准备向 Context 中继续加入内容时，都应该问这段内容是否提高了当前决策需要的 signal，以及它带来的 token、重复和干扰是否值得。例如，一个测试失败以后，下面这些信息的 signal 通常很高：

```text
失败测试的断言
实际错误信息
相关实现
最近一次有影响的修改
```

而下面这些内容即使属于同一个项目，也未必值得立即进入 Context：

```text
三个月前已经解决的构建日志
与当前模块无关的设计文档
完整的 dependency lockfile
几十个暂时不会使用的 Tool Schema
```

所谓 `High Signal / Low Noise` 并不要求 Harness 永远做出完美选择，而是要求系统承认：**Context 的价值来自相关性和可操作性，而不是来自覆盖率本身。**这进一步改变了我们看待“Agent 知识”的方式。传统的一次性 Prompt 往往追求：

```text
在调用模型以前
把它需要知道的东西准备好
```

Agent 更适合另一种模式：

```text
系统保留一个远大于 Context Window 的信息空间
                    │
                    ▼
             当前任务产生需求
                    │
                    ▼
           retrieve / select / compress
                    │
                    ▼
              Current Context
                    │
                    ▼
                    LLM
                    │
                    ▼
               新状态产生
                    │
                    └──────────────┐
                                   │
                         下一轮重新选择
```

于是 Context 不再是一份在任务开头写完就不动的输入文本，而是一个随 Agent 行动不断更新的 working set。这个 working set 里有些信息天然应该从任务开始就存在，例如稳定的行为规则和 Tool contract；有些只在当前 Session 中有用，例如刚刚运行测试得到的错误；有些需要跨 Session 保存，例如还没有解决的 blocker；有些根本不应该提前加载，而应该留在 repository、database 或 document store 中按需读取；当 Agent 进入团队以后，还会面对 Slack、会议记录、设计文档和权限系统构成的更大知识空间。因此，后面几节会把同一个 Context Engineering 问题沿着信息生命周期逐渐展开：

```text
Prompt Context
      ↓
Session Context
      ↓
Persistent Memory
      ↓
Workspace Context
      ↓
Organizational Knowledge
```

这五层不是 Anthropic 原文提出的一套正式 taxonomy，而是本文用来整理工程边界的模型。它们也不是五个越来越大的 Prompt。越往后，可供 Agent 使用的信息总量反而越大，而真正进入单次 inference 的内容仍然需要受到同一个约束：

$$
\text{Available Information}
\gg
\text{Current Context}
$$

所以从 Prompt Engineering 走到 Context Engineering，变化并不是“以后少研究 Prompt，多研究 RAG”。真正改变的是 Harness 所负责的边界：从编写一段输入文字，扩展到维护一个不断变化的信息空间，并在每一次模型调用之前决定——**这一刻，什么应该被模型看到。**

## 2. Prompt Context：什么值得在任务开始前就让模型知道？

上一节把 Context Engineering 写成一个选择问题：

$$
C_t^*
=
\arg\max_{C \subseteq I_t,\;\operatorname{Tokens}(C)\le B_t}
U(C\mid G_t)
$$

但在 Agent 真正开始搜索文件、调用工具和产生运行轨迹之前，Harness 已经做过第一次 Context Selection。System instructions、工具定义、输出格式、项目规则以及少量示例，通常会在第一轮 inference 之前直接进入模型上下文。本文把这一部分称为 **Prompt Context**。

```text
User Request
     +
System Instructions
     +
Tool Definitions
     +
Stable Rules
     +
Canonical Examples
     │
     ▼
First Inference
```

Prompt Context 的共同特征不是“它们都由用户写在聊天框里”，而是：

> **Harness 认为这些信息足够稳定、足够通用，而且对任务早期决策足够重要，因此值得提前支付 Context 成本。**

这和后面的 Workspace Context 有明显区别。一个代码库可能有几万个文件，但 Harness 不会在第一轮把它们全部读进来；相反，诸如“修改文件前先阅读”“不要提交 secrets”“使用哪些工具”“输出必须满足什么 contract”之类的规则，通常不能等到 Agent 犯错以后才去 repository 里搜索。所以 Prompt Context 实际上承担的是一种 **bootstrap** 作用：它不是提供完成任务所需的全部知识，而是给 Agent 足够的信息，让它知道自己是谁、当前要做什么、有哪些能力、受到哪些约束，以及接下来应该怎样取得还不知道的信息。

### 2.1 System Prompt 的问题不是越详细越好，而是找到合适的抽象高度

写 Agent system prompt 时，很容易滑向两个极端。第一个极端是把所有行为都提前规定成流程：

```text
如果用户要求修复 bug：
1. 读取测试
2. 读取实现
3. 搜索调用方
4. 运行测试
5. 修改代码
6. 再次运行测试

如果测试失败：
1. 检查 stderr
2. 搜索错误字符串
3. ...
```

继续增加 edge case 后，system prompt 会逐渐变成一份自然语言写成的状态机：

```text
if A:
    do B
elif C:
    do D
elif E:
    ...
```

这种写法的问题不只是 token 多。它还把本来可以由模型根据环境判断的控制流冻结在 prompt 中。一旦真实任务偏离预设路径，Agent 要么机械执行不适用的步骤，要么同时面对大量互相竞争的例外规则。另一个极端则是什么都不规定：

```text
You are a helpful coding agent.

Solve the user's task carefully.
```

这样的 system prompt 很短，但没有告诉 Agent 怎样使用工具、哪些操作需要谨慎、完成条件是什么，也没有说明项目里哪些约束不能违反。模型只能依赖训练阶段形成的一般先验补齐这些空白，而这些先验未必适合当前 Harness。Anthropic 在 *Effective context engineering for AI agents* 中把合适的位置称为 system prompt 的 **right altitude**：规则应该足够具体，让模型知道需要遵循的行为边界；又不能具体到把整个任务执行过程写成 brittle logic。原文给出的方向是，把 Prompt 分成清晰的部分，例如背景、指令和工具使用规则，并使用简单、直接的语言，而不是塞入大量为特定案例编写的复杂条件。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)对 Coding Agent 来说，一个更合理的规则可能是：

```text
修改代码前先取得足够的局部上下文。

优先使用项目已有的测试验证行为。

不要为了让测试通过而删除或弱化测试。

遇到无法从代码和测试确认的产品行为时，
停止推断并寻找对应的 Spec 或用户确认。
```

这里没有规定：

```text
先 grep 哪个字符串
先读哪三个文件
测试失败几次以后换策略
```

这些属于运行时决策，可以交给模型根据当前状态处理；但它规定了更稳定的行为边界：

```text
需要证据
需要验证
不能篡改验收条件
遇到产品语义缺口不能自行编造
```

这就是“抽象高度”的差异。可以把 Prompt 规则粗略分成三层：

```text
太低
────────────────────────
具体命令
固定文件名
硬编码执行顺序
大量 edge-case 分支

合适
────────────────────────
稳定目标
行为约束
安全边界
验收原则
工具使用原则

太高
────────────────────────
Be helpful
Be careful
Do a good job
Use best practices
```

中间这一层通常最适合常驻 Prompt Context，因为它的复用范围足够大，又能真正改变 Agent 的行为。这个判断也解释了为什么 CLAUDE.md、AGENTS.md 或 repository instructions 不应该无限增长。假设一个项目持续出现失败案例，最直接的反应是不断追加：

```text
以后不要这样做。
以后遇到 X 一定先做 Y。
如果 Z 出现必须执行 W。
```

短期看，每条规则都能对应一个真实事故；长期看，它们会把一次失败的局部修复永久变成所有任务都要支付的 Context 成本。更稳妥的更新方式是先判断失败属于哪一种：

```text
模型不知道稳定规则
→ 值得加入 Prompt Context

模型缺少当前任务的信息
→ 应该让它检索 Workspace

模型忘记之前已经获得的信息
→ Session / Memory 问题

Tool 返回的信息结构不好
→ Tool design 问题

验收标准本身缺失
→ Spec / Eval 问题
```

只有第一种问题真正应该通过增加常驻 system instructions 解决。否则，Prompt 会逐渐承担本不属于它的职责。

### 2.2 Tool Definitions 和 Examples 同样在消费 Prompt Context

Prompt Context 还有一个容易被忽视的部分：**模型看到的 Tool Schema 本身也是 Context。**假设 Harness 给 Agent 暴露：

```text
read_file
write_file
grep
glob
bash
git_diff
run_tests
browser_search
database_query
send_message
...
```

模型要决定下一步执行哪个动作，必须先理解每个 Tool 的：

```text
name
description
input schema
parameter semantics
return shape
```

这些描述最终都会变成模型输入的一部分。所以工具数量并不是只有运行时成本。即使某个 Tool 从头到尾都没有被调用，只要它的定义在每次 inference 中被注入，它就已经占用了 Prompt Context，并参与 Tool Selection。可以把它理解成：

$$
C_{\text{prompt}}
=
C_{\text{instructions}}
+
C_{\text{tools}}
+
C_{\text{examples}}
+
C_{\text{contracts}}
+\cdots
$$

这几个部分共享同一个 Context budget，而不是各自拥有免费空间。Anthropic 在讨论工具设计时强调了一个很实际的标准：工具应该有清晰、互不混淆的职责。如果人类开发者看到两个工具以后都很难判断应该使用哪一个，模型通常也会遇到同样的问题。工具的返回结果还应该尽量提供高 signal 信息，而不是把大量实现细节和低价值文本直接灌回 Context。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)例如下面这组 Tool：

```text
search
search_files
find_file
find_text
grep_files
code_search
repository_search
```

看起来能力丰富，但如果描述之间的边界只是：

```text
search_files:
Search files.

repository_search:
Search repository.

code_search:
Search code.
```

模型需要额外消耗注意力去猜它们之间的差异。更清楚的接口可能只有：

```text
glob(pattern)
    按路径模式查找文件

grep(pattern, path)
    在文本文件中查找内容

read(path, offset, limit)
    读取已知文件的具体范围
```

Tool 数量更少，但每个动作的语义和输入空间都不同：

```text
不知道文件在哪
→ glob

知道要找什么文本
→ grep

已经知道目标文件
→ read
```

这种设计不仅减少 Tool Selection 的歧义，也降低需要常驻 Prompt Context 的 schema 数量。Few-shot examples 也是相同的问题。假设一个 Agent 需要生成结构化结果，可以提供一个正确示例：

```json
{
  "status": "blocked",
  "reason": "Missing database credentials",
  "next_action": "Request credentials"
}
```

这个 example 的价值不是“让 Prompt 显得完整”，而是把仅靠抽象语言不容易表达的输出模式具体化。模型可以从少量 canonical examples 中学到：

```text
字段怎样组合
什么算 blocked
信息粒度应该到哪里
```

但如果为了覆盖所有可能情况，一次预加载几十个例子：

```text
成功案例 × 10
失败案例 × 10
超时案例 × 10
权限问题 × 10
```

它们同样会成为每轮 inference 都必须携带的 Context。因此 Examples 也应遵循与工具相同的原则：

```text
能够提供新的行为信号
        ↓
保留

只是重复已经清楚的模式
        ↓
删除
```

这一点在 Agent Harness 中尤其重要，因为 Prompt Context 通常不是一次性成本。普通文本生成调用一次模型：

```text
Prompt 3k tokens
→ Response
→ End
```

Agent 可能连续调用几十次：

```text
Prompt Context
     ↓
Inference 1

Prompt Context
+ History
     ↓
Inference 2

Prompt Context
+ More History
     ↓
Inference 3

...
```

如果一组稳定 instructions、examples 和 tool definitions 每轮都需要重新出现在模型输入中，那么它们的设计质量会影响整个 Agent loop，而不只是第一步。这也是为什么 Tool Design、Prompt Design 和 Context Engineering 不能完全拆开看：一个返回 20,000 token 原始 JSON 的 Tool，会制造 Session Context 压力；一个拥有巨大 schema 的 Tool 集合，会增加 Prompt Context；两个边界模糊的 Tool 则会降低模型选择动作的准确性。

```text
Tool Interface
      │
      ├─ definition → Prompt Context
      │
      └─ result     → Session Context
```

同一个工具会同时影响 Context 的两个阶段。

### 2.3 Minimal Prompt 不等于 Short Prompt

走到这里，很容易把前面的原则误解成：

```text
Context 有成本
→ Prompt 越短越好
```

Anthropic 原文专门提醒不要这样理解 `minimal`。目标不是追求最少 token，而是找到完成任务所需的 **minimal sufficient context**：该有的信息不能缺失，不影响当前行为的信息也不应该因为“可能有用”而全部预加载。因此下面这个 Prompt 虽然很短：

```text
Fix the bug.
```

并不是好的 minimal prompt。如果 Agent 不知道：

```text
哪个 repository
什么行为被认为是 bug
什么测试必须通过
能否修改 public API
是否允许新增 dependency
```

Harness 只是把必要信息省掉了。反过来，这样也不是好的 Prompt Context：

```text
整个项目的开发规范
所有历史事故
全部 API 文档
几十个示例
完整 architecture overview
所有 Tool
过去三年的 design decisions
```

它的问题不是这些信息全部错误，而是它们没有经过当前任务的 relevance 判断。因此 `minimal` 更接近：

```text
必要且稳定
+
当前阶段确实有用
-
重复信息
-
低概率相关信息
-
可以按需检索的信息
```

这里可以引入一个比“Prompt 长短”更有用的区分：

```text
Must Know Before Acting
        vs.
Can Discover While Acting
```

第一类信息适合 Prompt Context，例如：

```text
任务目标
安全规则
不可违反的项目约束
Tool 使用 contract
完成条件
```

第二类信息应该尽量保留在外部环境：

```text
某个函数的实现
某个 Issue 的历史讨论
数据库当前有哪些表
五个月前某次测试失败的日志
某个库的 API 文档
```

Agent 在真正需要时再读取。可以把这种设计写成：

```text
                     ┌───────────────────────┐
                     │   Prompt Context      │
                     │                       │
                     │ stable instructions   │
                     │ task                  │
                     │ tools                 │
                     │ contracts             │
                     │ canonical examples    │
                     └──────────┬────────────┘
                                │
                                ▼
                           Agent starts
                                │
                  ┌─────────────┴─────────────┐
                  │                           │
          enough information?          information missing
                  │                           │
                  ▼                           ▼
                act                    retrieve / inspect
                                              │
                                              ▼
                                      Session Context
```

这种结构允许 Prompt 保持相对稳定，同时让 Agent 在运行过程中逐渐取得局部知识。Anthropic 给出的实践方式也接近这个方向：从相对简单的 Prompt 出发，用 evaluations 和实际失败案例观察模型哪里缺少指导，再针对已观察到的 failure mode 增加 instruction 或 example，而不是在上线之前想象所有可能的 edge case，并全部写进 system prompt。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)这实际上给 Prompt 的增长设置了一道证据门槛：

```text
Observed Failure
      │
      ▼
为什么失败？
      │
      ├─ 缺少稳定行为规则
      │       ↓
      │   Update Prompt
      │
      ├─ 缺少任务局部信息
      │       ↓
      │   Improve Retrieval
      │
      ├─ Tool 难以正确调用
      │       ↓
      │   Redesign Tool
      │
      └─ 长运行后忘记状态
              ↓
        Session / Memory
```

这样做的意义在于避免一个常见的 Agent Harness 演化路径：

```text
第一次失败
→ Prompt + 5 行

第二次失败
→ Prompt + 20 行

第三次失败
→ Prompt + 3 个 Example

第四次失败
→ Prompt + 新的特殊规则

半年以后
→ 没有人知道哪些规则仍然必要
```

如果所有 failure 都通过追加 Prompt 修复，Prompt 最终会成为整个系统历史债务的堆放处。规则之间可能冲突，旧约束可能已经失效，真正影响当前任务的几行文字被埋在大量防御性指令中。Prompt Context 更适合承担的是 **稳定控制面**，而不是整个 Agent 的知识库：

```text
Prompt Context
=
How should I work?
+
What must I respect?
+
What can I use?
+
What is the current task?
```

它不需要回答：

```text
What does the whole world contain?
```

后一个问题应该交给 Agent 在运行时逐步解决。这样，第一轮 inference 结束之后，Context 的性质也会发生变化。Agent 开始读取文件、运行命令、观察错误并形成中间结论，新的信息不断进入工作集。即使 Prompt Context 保持完全不变：

$$
C_{\text{prompt}}^{(1)}
=
C_{\text{prompt}}^{(20)}
$$

完整 Context 仍可能从：

```text
Prompt
```

增长成：

```text
Prompt
+ Message History
+ Tool Calls
+ Tool Results
+ Files Read
+ Intermediate State
```

这时问题就不再是“任务开始前应该预加载什么”，而是：

> **Agent 已经工作了几十步以后，怎样避免它自己的工作历史把 Context Window 填满，同时又不丢失继续行动所需的状态？**

这就是下一层 **Session Context** 要解决的问题。
## 3. Session Context：Agent 会不断制造自己的上下文

Prompt Context 在任务开始时相对稳定，但 Agent 一旦进入 tool-use loop，Context 就不再是静态输入。每一次读取文件、执行命令、查询数据库或者调用外部服务，都会产生新的 observation；模型根据 observation 做出的判断又会进入后续 message history。Anthropic 对 Agent 的一个简化定义就是“LLM autonomously using tools in a loop”，而 Context Engineering 的困难也正是在这个 loop 中出现：Agent 不断制造下一轮可能需要的信息，但当前 Context Window 不可能无限保存整个运行历史。以一个 Coding Agent 修复测试为例，任务轨迹可能从最初几千 token 很快扩展：

```text
User:
修复 OAuth refresh token 的测试失败。

        ↓

Agent:
读取 tests/test_refresh.py

        ↓

Tool Result:
240 行测试源码

        ↓

Agent:
搜索 refresh_token

        ↓

Tool Result:
17 个匹配结果

        ↓

Agent:
读取 src/auth/token.py

        ↓

Tool Result:
380 行源码

        ↓

Agent:
运行 pytest

        ↓

Tool Result:
600 行测试日志

        ↓

Agent:
修改实现并重新测试

        ↓

Tool Result:
新的错误日志
```

如果把第 \(t\) 步之前累计的会话历史记成 \(H_t\)，那么一次简单的 Agent loop 可以写成：

$$
H_{t+1}
=
H_t
+
A_t
+
O_t
$$

其中 \(A_t\) 是 Agent 在第 \(t\) 步做出的 action，\(O_t\) 是工具返回的 observation。这里只是本文对运行过程的抽象，并不是 Anthropic 原文中的公式。它揭示的问题很直接：如果 Harness 对历史只做 append，那么 Session Context 的增长方向几乎总是单向的。

```text
Message 1
   +
Tool Call 1
   +
Tool Result 1
   +
Message 2
   +
Tool Call 2
   +
Tool Result 2
   +
...
   ↓
越来越长的 Session Context
```

这种增长和 Prompt Context 的冗余还不完全相同。Prompt 中一条没用的规则通常只是持续占据空间，而 Session 中产生的信息往往**曾经确实有用**：Agent 必须读测试才能理解失败，必须看到 traceback 才能定位错误，必须检查 diff 才能判断修改是否正确。问题在于，一条信息在第 5 步很重要，不代表第 50 步仍然需要以原始形态留在 Context 中。Session Context 因此需要处理的是信息的**生命周期**：

```text
产生
 ↓
当前决策需要
 ↓
被理解 / 被使用
 ↓
结论进入任务状态
 ↓
原始表示是否还需要保留？
```

这也是 compaction、tool result clearing 等机制出现的原因。它们并不是简单地“省 token”，而是在 Agent 继续行动所需的状态与已经完成使命的运行痕迹之间建立边界。

### 3.1 Agent Loop 产生的是 Transcript，不等于下一步需要的 State

先区分两个很容易混在一起的对象。一个 Agent 运行十分钟以后，可以拥有完整的 **Transcript**：

```text
用户说了什么
Agent 每轮回答了什么
调用了哪些工具
每个工具返回了什么
哪些命令失败
哪些文件读过
做过哪些尝试
```

但下一步行动真正需要的 **Task State** 往往小得多。例如修复一个认证 Bug，完整 Transcript 可能已经有几十万 token，而当前状态可以压缩成：

```text
Goal:
修复 refresh token 过期后返回 500 的问题。

Root cause:
decode_refresh_token() 没有捕获 ExpiredSignatureError。

Files:
- src/auth/token.py
- tests/test_refresh.py

Changes:
token.py 已加入异常转换，但 integration test 仍失败。

Remaining failure:
refresh endpoint 返回 403，预期 401。

Hypothesis:
middleware 可能在 endpoint 之前拦截异常。

Next:
检查 auth middleware。
```

这两份信息并不等价。Transcript 记录的是：

```text
How did we get here?
```

Task State 更接近：

```text
Where are we now?
```

对于刚发生的错误，完整 traceback 可能仍然比一句总结有价值；但当 Agent 已经确认根因、完成修改，并通过对应单元测试以后，十轮之前那份几百行 traceback 的边际价值会明显下降。Harness 需要维护的不是完整历史本身，而是足以支持后续行为的状态。可以把这个关系表示为：

$$
\text{Transcript}_t
\longrightarrow
\text{State}_t
$$

理想情况下：

$$
|\text{State}_t|
\ll
|\text{Transcript}_t|
$$

但：

$$
\text{State}_t
$$

仍然应该保留后续行动需要恢复的关键事实。这和传统日志系统的目标不同。服务器日志往往追求审计、调试和事后恢复，因此原始记录越完整越好；Model Context 则直接参与下一次推理，多余记录会消耗有限的 attention budget。Harness 完全可以把完整 Transcript 保存在磁盘、数据库或 trace system 中，同时只把压缩后的 Task State 放进当前模型 Context。

```text
                     Full Transcript
                    /               \
                   /                 \
          observability            model input
                │                       │
                ▼                       ▼
         完整保存用于调试          当前所需 State
```

因此：

```text
stored
≠
in context
```

这个区别和上一节的 `Available Information ≫ Current Context` 是同一条原则，只是现在信息来源从外部 Workspace 变成了 Agent 自己刚刚产生的运行历史。

### 3.2 Compaction：压缩的不是文字，而是继续工作的状态

当 Session 足够长时，只依赖删除几个旧 Tool Result 仍然不够。Anthropic 将 **compaction** 定义为：当 conversation 接近 Context Window 限制时，对已有内容进行总结，并用这份压缩结果重新建立新的 Context Window，使 Agent 能够继续长时间任务。因此最基本的结构不是：

```text
Long Text
   ↓
Short Text
```

而是：

```text
Context Window A

Prompt
Messages
Tool Calls
Tool Results
Decisions
Errors
Current Progress
        │
        │ compaction
        ▼
Structured State
        │
        ▼
Context Window B

Prompt
Compacted State
Recent Working Context
        │
        ▼
继续执行原来的任务
```

判断 compaction 是否成功，也不能只看：

```text
100k tokens
→
8k tokens
```

真正需要测试的是，新 Context Window 中的 Agent 是否仍然知道：

```text
目标是什么
哪些工作已经完成
哪些尝试失败过
为什么失败
做过哪些关键决定
当前有哪些未解决问题
哪些文件或 Artifact 仍然相关
下一步准备做什么
```

Anthropic 在 Claude Code 的例子中描述了一种具体实现：接近 Context 上限时，把 message history 交给模型进行总结，保留 architectural decisions、unresolved bugs 和 implementation details，同时丢弃重复的 Tool Output 或消息；压缩以后，Agent 使用这份 compacted context 加上最近访问的五个文件继续工作。这里的“五个文件”是 Anthropic 当时文章中描述的 Claude Code 实现细节，不应扩展成所有 Agent 都应该采用的固定参数。这个例子说明 compaction 的对象不是均匀的。假设历史中有：

```text
A. 用户要求：
   不允许改变 public API。

B. Agent 决定：
   保持 TokenService.refresh() 签名不变。

C. pytest 首次输出：
   612 行日志。

D. Agent 从日志确认：
   ExpiredSignatureError 未被转换。

E. 修改后的 pytest 输出：
   对应单测已经通过。

F. 当前 integration test：
   middleware 返回 403，仍需定位。
```

如果只按“旧信息优先删除”，A 和 B 可能比 F 更早被清掉，但它们仍然约束最终方案；如果只按“文本长度优先压缩”，C 很适合删除，而 D 应该保留，因为它已经把 612 行输出转化成了后续可以使用的诊断状态。所以更合理的 compaction 类似：

```text
Raw Observation
      │
      ▼
Interpretation
      │
      ▼
Decision / State Change
      │
      ▼
需要继续保存吗？
```

其中：

```text
600 行旧测试输出
→ 可以删除

“该错误由 ExpiredSignatureError 未处理导致”
→ 保留

“不能改变 public API”
→ 保留

已经验证无关的 hypothesis
→ 可以压缩成一句失败结论

仍未验证的 hypothesis
→ 保留
```

这里体现的是 **semantic compression**，而不仅是 lexical compression。系统不是把每段文字缩成原来的 10%，而是在尝试把运行轨迹转化成更紧凑的任务表示。可以用本文自己的抽象表示：

$$
K(H_t)
\rightarrow
\widetilde{S}_t
$$

其中 \(K\) 是 compaction process，\(\widetilde{S}_t\) 是压缩后保存的任务状态。理想目标不是最小化：

$$
|\widetilde{S}_t|
$$

本身，而是在缩小 Context 的同时，让：

$$
P(\text{successful continuation}\mid \widetilde{S}_t)
$$

尽量接近使用完整有效历史时的表现。这仍然只是帮助理解的抽象，不意味着实际 Harness 能直接计算这个概率。也正因为如此，compaction 最难的部分并不是“怎么调用 summarization model”，而是：

> **什么现在看起来可以删，但十步以后可能重新变得重要？**

Anthropic 把这一点直接描述为 keep 与 discard 之间的选择问题，并指出过于激进的 compaction 可能删除当下看似微妙、稍后却变得关键的信息。

### 3.3 先保 Recall，再提高 Precision

既然 compaction 最大的风险是丢掉以后还需要的信息，那么第一次实现时应该压得多短？Anthropic 对这个问题给出的建议很明确：在复杂 Agent trace 上调试 compaction prompt 时，**先最大化 recall，确认相关信息能够被保留下来，再逐步提高 precision，删除多余内容**。这里的 recall / precision 可以借用信息检索里的直觉来理解。假设完整 Session 中存在 20 条后续真正需要的事实，而 compaction 保存了其中 18 条：

$$
\text{Recall}
\approx
\frac{\text{保留下来的相关事实}}
{\text{原历史中的相关事实}}
$$

如果压缩结果一共保存了 60 条事实，其中只有 18 条后来真正有用：

$$
\text{Precision}
\approx
\frac{\text{保留下来的相关事实}}
{\text{压缩结果保存的全部事实}}
$$

这两个公式只是本文用于解释 Anthropic 调优建议的概念化写法，并不是其文章定义的 compaction evaluation metric。一种非常激进的摘要可能得到：

```text
正在修复 auth bug。
修改了 token.py。
还有测试失败。
```

它很短，precision 看起来也不差，但 recall 太低。Agent 已经不知道：

```text
哪个测试失败
为什么修改 token.py
哪些测试已经通过
public API 是否允许变化
下一步应该检查哪里
```

另一份早期 compaction 可以稍微冗余一些：

```text
Goal:
修复 refresh token 过期请求返回错误状态码的问题。

Constraints:
- 不修改 TokenService.refresh() public API。
- 保持现有 login flow 行为。

Confirmed:
- ExpiredSignatureError 原先未转换。
- token.py 已增加异常转换。
- token unit tests 已通过。

Remaining:
- tests/integration/test_refresh.py::test_expired_refresh
  仍返回 403，预期 401。

Rejected:
- refresh token decoding 本身已不是剩余失败原因。

Hypothesis:
- auth middleware 在 refresh endpoint 前返回 403。

Next:
- 检查 middleware 对 expired refresh token 的处理。
```

它并没有追求最短，但恢复任务所需的信息更完整。这也是为什么 compaction 的第一次优化方向不应该是：

```text
summary tokens
8000 → 2000 → 500
```

而应该先问：

```text
重启 Context 后，
Agent 是否会重复已经做过的工作？

是否违反之前确定的约束？

是否重新尝试已经证伪的路线？

是否知道仍未解决的问题？

是否能解释关键修改为什么存在？
```

这些 failure 可以作为 compaction eval 的输入。如果 Agent reset 后重新走了一遍已经失败的方案，说明 rejected hypothesis 没有被保存；如果它删除了一个不能修改的接口，说明 constraint 丢失；如果它重新调查已经定位完成的根因，说明完成状态没有被正确保存。等 recall 基本稳定以后，再寻找 precision 问题，例如：

```text
重复描述同一个根因

已经结束的中间讨论

没有影响任何决策的搜索结果

可以重新生成的原始输出

重复出现的文件内容
```

调优方向因此更像：

```text
Phase 1

Full Trace
    ↓
High-recall Compaction
    ↓
可以可靠继续工作


Phase 2

High-recall Compaction
    ↓
删除可证明的冗余
    ↓
Higher-precision Compaction
```

而不是一开始就要求模型：

```text
请在 300 字以内总结以上十万 token。
```

固定字数可以控制成本，却不能自动保证任务状态完整。

### 3.4 Tool Result Clearing：不一定等到整次 Compaction

完整 compaction 通常发生在 Session 已经比较长的时候，但很多 Context 垃圾其实可以更早清理。Anthropic 把 **tool result clearing** 称为一种较安全、较轻量的 compaction：一个 Tool Call 已经发生在很久以前，如果 Agent 已经吸收了它的结果，后续 Context 未必还需要继续携带原始 Tool Result。例如：

```text
$ pytest tests/auth -vv
```

返回 8,000 token：

```text
================ test session starts ================
...
FAILED test_refresh_expired
FAILED test_refresh_revoked
PASSED ...
...
Traceback ...
...
```

Agent 读取以后形成了更紧凑的状态：

```text
Auth tests:
42 passed, 2 failed.

Failures:
1. expired refresh token → expected 401, got 500
2. revoked refresh token → expected 401, got 500

Both reach the same unhandled exception path.
```

如果十轮之后，两个错误都已经定位并修复，那么完整的 8,000 token 日志继续存在于每轮 Context 中通常没有太大价值。可以把这一过程表示成：

```text
Raw Tool Result
    8,000 tokens
         │
         ▼
Agent Interpretation
         │
         ▼
Structured State
      150 tokens
         │
         ├───────────────┐
         │               │
         ▼               ▼
raw result         raw result cleared
仍有后续用途        已被状态吸收
```

Tool Result Clearing 和完整 compaction 的区别在于，它不需要把整个 Session 重写成新的摘要。它只处理已经明显失去当前价值的局部 observation，因此可以更频繁地执行：

```text
Full Compaction
────────────────────────
作用范围：整个 Session
时机：Context 接近压力区间
风险：可能丢失跨多轮的隐含状态

Tool Result Clearing
────────────────────────
作用范围：特定旧 Tool Result
时机：结果已被消费且不再需要原始形式
风险：如果删得过早，可能失去原始证据
```

“Tool Result 用完就删”仍然过于激进。有些原始数据即使已经被 Agent 总结，后面仍可能需要精确值。例如数据库查询：

```text
customer_id | plan       | renewal_at
------------|------------|-------------------
381         | enterprise | 2026-10-17 08:00
```

如果后面需要生成 migration SQL，那么精确的 `customer_id` 和 timestamp 不能只被总结成：

```text
有一个 Enterprise 客户下个月续费。
```

类似地：

```text
精确错误字符串
benchmark 数值
文件路径
line number
API response field
用户明确给出的数字
```

都可能是 evidence-bearing tokens。删除之前需要确认它们是否已经被无损转移到其他状态表示，或者是否能够可靠、低成本地重新取得。所以 Tool Result 是否可以清理，可以用三个问题判断：

```text
1. 结果中的关键事实是否已经进入当前 State？

2. 后续是否还需要原始精度，而不仅是语义摘要？

3. 如果判断错了，这份结果能否低成本重新获取？
```

例如：

```text
旧的 grep 输出
+ 文件仍然存在
+ 已记录关键 path
→ 较容易重新生成

一次昂贵的远程查询
+ 数据正在变化
+ 原始结果没有持久化
→ 不应该轻易删除

用户上传后已经不存在的临时数据
→ 需要先持久化，再考虑清理
```

这使 Session Context 出现了一个比“只 append history”更接近运行时 GC 的模型：

```text
                 Agent Loop
                     │
                     ▼
              New Observation
                     │
                     ▼
              Working Context
                     │
          ┌──────────┴──────────┐
          │                     │
    still actionable       state absorbed
          │                     │
          ▼                     ▼
        keep              clear / compress
          │                     │
          └──────────┬──────────┘
                     ▼
                 Next Turn
```

这里的 `GC` 只是类比：真正决定信息生命周期的不是对象是否还有程序引用，而是它是否仍然可能影响后续决策。到这一层，我们已经可以处理一个持续数十分钟甚至数小时的 Session。Prompt Context 提供稳定规则，Session Context 保存近期工作状态；旧 Tool Result 可以逐步清理，Context 接近上限时再通过 compaction 把长轨迹转换成能够继续执行的 Task State。Anthropic 也正是把 compaction 作为 long-horizon context engineering 的第一类手段，并把 structured note-taking 和 multi-agent architecture 放在后面继续处理更长生命周期和更大信息量的问题。但 Session Context 仍然有一个生命周期边界。假设今天的任务在这里停止：

```text
17:40

已定位根因
修改完成 70%
剩余 integration test
还需要确认 middleware 行为

Agent Session End
```

明天重新启动一个全新的 Agent：

```text
09:00

New Context Window
```

如果所有状态只存在于昨天的 message history 和 compaction summary 中，而这些内容没有被持久化，那么新的 Session 仍然可能从零开始。这就出现了下一层问题：

```text
Session Context
解决：
“这一次运行里，我刚才做过什么？”

Persistent Memory
解决：
“上一次运行已经结束以后，
哪些状态还应该继续存在？”
```

Context 的生命周期至此第一次跨出了单个 Session。
## 4. Persistent Memory：Session 结束以后，什么还应该继续存在？

Session Context 解决的是同一次运行里的连续性。Agent 在几十轮 tool-use 之后，仍然需要知道目标、当前进度、已经排除的路线和剩余问题；compaction 可以把过长的 Transcript 压缩成更紧凑的 Task State，让同一个任务继续运行。但只要 Session 真正结束，另一个问题就会出现。假设一个 Agent 在周一处理到这里：

```text id="7nt0wa"
Goal:
完成 auth middleware migration。

Completed:
- refresh token exception mapping
- token unit tests

Remaining:
- integration test 仍返回 403
- 需要检查 middleware

Constraint:
不能修改 public TokenService API
```

然后当前运行结束：

```text id="wse89a"
Session A
   │
   ▼
End
```

周二重新创建一个新的 Session：

```text id="68hwlu"
Session B
   │
   ▼
New Context Window
```

如果周一的状态只存在于 Session A 的 message history 中，而且 Harness 没有保存或重新加载它，那么对 Session B 来说：

```text id="9pv9b2"
昨天做了什么
为什么这样改
什么已经验证过
什么不能改
```

都可能不存在。因此，Context 的生命周期第一次跨出了当前 conversation：

```text id="5if0jo"
Prompt Context
    │
    │ task start
    ▼
Session Context
    │
    │ session ends
    ▼
Persistent State
    │
    │ later retrieval
    ▼
New Session Context
```

本文把这种跨 Session 保留下来的 Agent 状态称为 **Persistent Memory**。这里最需要避免的误解是：

> Memory 不是一个无限扩展的 Context Window。

Memory 的价值恰恰来自它可以存在于模型 Context 之外，并在需要时重新进入 Context。

### 4.1 Memory 存在于 Context Window 外

Anthropic 在 *Effective context engineering for AI agents* 中把 structured note-taking，也称作 agentic memory，作为长时间 Agent 的一种 Context Engineering 技术：Agent 可以定期把信息写入 Context Window 之外的持久存储，在之后需要时再读取回来。文章举出的实现甚至可以简单到一个 `NOTES.md` 文件。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)因此最小的 Memory 系统并不需要复杂组件。它可以只是：

```text id="lyas96"
Session A
   │
   │ write
   ▼
NOTES.md
   │
   │ read
   ▼
Session B
```

关键不是文件格式，而是状态生命周期发生了变化。Session Context 中的信息：

```text id="gbiakj"
依赖当前 Context Window
```

Persistent Memory 中的信息：

```text id="yx1q5y"
独立于当前 Context Window 存在
```

可以用集合关系表示：

$$
M \not\subseteq C_t
$$

其中 \(M\) 表示系统已经持久化的 Memory，\(C_t\) 表示时刻 \(t\) 当前 inference 的 Context。更准确地说，只有 Memory 中被当前任务选中的一部分才会进入 Context：

$$
R(G_t, M) \subseteq M
$$

然后：

$$
R(G_t, M) \subseteq C_t
$$

这里 \(R\) 表示根据当前目标 \(G_t\) 执行的 retrieval 或 selection。这个公式是本文的抽象，不是 Anthropic 原文中的正式定义。关系可以画成：

```text id="8p26bp"
                    Persistent Memory
                 ┌────────────────────┐
                 │                    │
                 │ decision history   │
                 │ progress           │
                 │ user preference    │
                 │ unresolved items   │
                 │ learned facts      │
                 │                    │
                 └─────────┬──────────┘
                           │
                       retrieval
                           │
                           ▼
                  Current Context
                           │
                           ▼
                          LLM
```

这带来一个非常重要的区别：

```text id="hqj24c"
remembered by the system
        ≠
currently attended by the model
```

如果一个 Agent 曾经把 10,000 条信息写进 Memory，并不意味着下一次 inference 应该加载 10,000 条。Persistent Memory 扩大的是系统可以在未来恢复的信息范围，而不是模型每轮应该承担的输入规模。这一点和数据库很像。数据库中存在：

```text id="ppw6t8"
100 million rows
```

不代表每个 SQL 查询都会：

```text id="dwam4v"
SELECT * FROM everything;
```

Memory Store 同样需要 query 或 selection。如果不区分 storage 和 context，Memory 很容易退化成：

```text id="mquz5z"
以前 Context 太长
        ↓
把它移进 Memory
        ↓
下一轮又全部塞回来
```

这只是换了一个存储位置，没有解决 Context Selection。

### 4.2 `NOTES.md` 已经可以构成 Memory System

讨论 Agent Memory 时，经常很快进入：

```text id="nl45yw"
vector database
embedding
episodic memory
semantic memory
memory graph
learned retrieval
```

这些技术当然可能有用，但它们不是 Persistent Memory 成立的前提。Anthropic 举出的 Claude Code 风格例子更简单：Agent 可以维护 todo list，也可以把重要状态写进 `NOTES.md` 或其他文件，以便跨越 Context reset 或更长时间的任务继续工作。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)假设一个长期 Coding Agent 使用：

```text id="g9t0ts"
.agent/
├── NOTES.md
├── TODO.md
└── progress.json
```

其中 `NOTES.md` 保存：

```markdown id="1wslcm"
## Auth migration

- Refresh token expiry is now mapped to 401.
- Do not change `TokenService.refresh()` public signature.
- Remaining 403 comes from `AuthMiddleware`.
- Previous hypothesis that JWT decode caused the integration failure was rejected.
```

`TODO.md` 保存：

```markdown id="x8fe26"
- [x] Fix refresh token exception mapping
- [x] Add unit coverage
- [ ] Inspect `AuthMiddleware`
- [ ] Run full auth integration suite
```

而 `progress.json` 保存机器更容易读取的结构：

```json id="7hwvam"
{
  "task": "auth-migration",
  "status": "in_progress",
  "completed": [
    "refresh-token-error-mapping",
    "unit-tests"
  ],
  "remaining": [
    "middleware-investigation",
    "integration-suite"
  ]
}
```

从 Memory 的核心功能看，这已经满足三个条件：

```text id="61utsw"
1. 状态可以离开当前 Context

2. 状态可以跨 Session 保留

3. 后续 Agent 可以重新读取状态
```

因此：

```text id="2qrsfy"
Plain Files
+
Write Policy
+
Read Policy
=
一种最小 Persistent Memory
```

复杂 Memory Framework 主要是在这个基本循环上继续解决：

```text id="57tet9"
写什么
什么时候写
怎么组织
什么时候更新
怎样删除过期信息
如何检索
发生冲突时相信谁
```

而不是从根本上改变“状态在 Context 外持久存在，之后按需读取”这件事。对于 Coding Agent 来说，文件系统还有一个很实际的优点：Memory Artifact 和普通工程 Artifact 可以使用相同的工具链。例如：

```text id="txj91j"
read
write
git diff
grep
history
```

都可以直接处理 Markdown、JSON 或 YAML 状态。如果一个 Agent 在周二启动，第一步读取：

```text id="r8eg23"
TODO.md
NOTES.md
```

它就能恢复：

```text id="2logfj"
昨天做到哪里
什么已经完成
哪些方案不要重复尝试
哪些约束仍然有效
```

而不需要重新读取完整 Transcript。这相当于把：

```text id="smgvsm"
Conversation History
```

转换成更稳定的：

```text id="23mx4a"
Work Artifact
```

与上一节的 compaction 相比，两者有相似之处，但生命周期不同。

```text id="dzk7wd"
Compaction
────────────────────────
输入：
当前 Session 的长 Transcript

输出：
继续当前 Session 所需的压缩状态

主要解决：
Context Window 压力


Persistent Memory
────────────────────────
输入：
需要跨 Session 保留的状态

输出：
Context 外长期存在的 Artifact

主要解决：
跨 Session 连续性
```

有些系统会把 compaction 结果直接持久化，因此两者在实现上可能重叠。但概念上仍然应该区分：

```text id="5gibzz"
Compact
回答：
“现在继续工作还需要记住什么？”

Persist
回答：
“当前 Session 结束以后，
什么仍然值得存在？”
```

并不是所有 Session 信息都值得变成长期 Memory。例如：

```text id="tnx1ai"
刚才 grep 返回了 17 行
```

可能只在当前调查阶段有意义。但：

```text id="hcfu4p"
public API 不能修改
```

如果这是跨多天任务仍然有效的约束，就更值得持久化。这开始涉及 Memory 的写入策略。

### 4.3 Memory 的难点不是“能写”，而是决定什么值得长期保存

如果允许 Agent 在任何时候把任何东西写进 Memory，一个最简单的实现可能是：

```text id="1y3xa8"
每轮结束
    ↓
把当前 Context 全部保存
```

它确实不会忘。但过一段时间以后，Memory 会变成另一个 Transcript Archive：

```text id="5d3tui"
memory/
├── turn-0001.md
├── turn-0002.md
├── turn-0003.md
├── turn-0004.md
├── ...
└── turn-4832.md
```

这并没有建立有效的长期状态，只是把 Session Context 的增长问题搬到了硬盘。更有用的 Memory 需要一种写入标准：

```text id="cb2ggg"
什么信息的未来价值
足以支付它进入长期存储的成本？
```

对于长期工程任务，可以优先持久化：

```text id="v4hu25"
稳定约束
关键决策
已经确认的事实
任务进度
未解决 blocker
失败路线及其原因
重要 Artifact locator
```

而不必长期保存：

```text id="i2mhpo"
每次 shell command 的完整 stdout
已经被吸收的临时 grep 结果
无关搜索路径
重复的代码内容
模型自己的所有中间表述
```

例如下面两条记录的长期价值明显不同：

```text id="8hm5hl"
Memory A:
17:23 跑了一次 pytest，
输出很多红色错误。
```

```text id="ve9dq1"
Memory B:
`test_expired_refresh` 的剩余 403
来自 `AuthMiddleware`，
不是 `decode_refresh_token()`；
不要重复调查 JWT decode。
```

B 保留了：

```text id="au5wtz"
confirmed result
+
rejected path
+
future action relevance
```

它可以直接减少未来 Session 的重复工作。因此 Memory Write 也可以看成一次 selection：

$$
W_t \subseteq C_t
$$

只有当前 Context 中一部分信息应该被写入长期存储。如果进一步考虑时间：

$$
M_{t+1}
=
\operatorname{Update}(M_t, W_t)
$$

这个 `Update` 也不一定等于 append。假设 Memory 里原本写着：

```text id="nyttw9"
Auth migration is P0.
```

两周后项目决定：

```text id="2cgntf"
Auth migration paused until Q4.
```

如果系统只追加而不更新，Memory 中会同时存在：

```text id="c2sh54"
Auth migration is P0.

Auth migration is paused until Q4.
```

这时问题不再是遗忘，而是**冲突和过期状态**。因此 Persistent Memory 至少要考虑：

```text id="80v4ly"
Write
Update
Supersede
Delete
Retrieve
```

而不能只有：

```text id="l6l76a"
Append forever
```

对于简单文件 Memory，可以用显式状态覆盖：

```markdown id="6c91aq"
## Auth migration

Status: PAUSED

Supersedes:
- P0 migration plan from 2026-08-12

Reason:
Waiting for Q4 identity-platform rollout.
```

这样未来 Agent 检索到的是当前状态，同时仍然可以通过 history 查到旧版本。这一点以后扩展到 Organizational Knowledge 时会更加重要：团队里的 roadmap、ownership、策略和设计决定都可能变化。一个能够“记住所有历史”的 Agent，如果无法判断什么已经过期，仍然可能做出错误决策。所以：

```text id="4ifhdd"
Memory quality
≠
memory volume
```

长期 Memory 的质量至少取决于：

```text id="p33u1z"
relevance
freshness
conflict handling
retrievability
```

本文不在这里展开完整的 Memory Architecture，因为那值得单独讨论。对当前五层模型来说，更关键的是确定边界：Persistent Memory 提供跨 Session continuity，但它仍然只是**更大的可用信息空间**，而不是默认 Context。

### 4.4 `stored ≠ loaded`：Memory 仍然需要 Retrieval

假设经过几个月工作，一个 Agent 已经积累：

```text id="mr19ua"
memory/
├── auth.md
├── billing.md
├── deployment.md
├── frontend.md
├── infra.md
├── incidents.md
├── preferences.md
└── ...
```

总量可能从几 KB 增长到几十 MB，甚至更多。如果每次 Session 启动都执行：

```text id="tpjtf8"
cat memory/*
```

然后全部塞进 Prompt，那么 Persistent Memory 只会制造新的 Context 问题。因此：

```text id="hc2nek"
stored
≠
loaded
```

应该作为 Memory 系统的基本边界。例如用户要求：

```text id="veo56q"
继续昨天的 auth migration。
```

系统真正需要加载的可能是：

```text id="tn4e2n"
memory/auth.md
当前 TODO
最近一次相关 decision
```

而不是：

```text id="g2ff8m"
billing history
frontend migration
three-month-old deployment incident
所有用户偏好
```

这种选择可以非常简单。如果 Memory 已按 project / topic 分类：

```text id="k1k78m"
task
  ↓
known project key
  ↓
read corresponding memory file
```

也可以通过：

```text id="nysnsa"
keyword search
metadata filter
embedding retrieval
graph traversal
learned memory router
```

执行更复杂的 retrieval。无论实现方式如何，逻辑仍然是：

```text id="qpu2z7"
Persistent Memory
       │
       │ retrieve relevant state
       ▼
Current Session Context
```

这和上一节的 compaction 构成了一对相反方向的数据流：

```text id="x37q4r"
Current Context
       │
       │ compact / persist
       ▼
Persistent State
       │
       │ retrieve
       ▼
Future Context
```

于是一个跨 Session Agent 的 Context 生命周期可以表示成：

```text id="h33uc3"
Session A

Prompt
  +
Working Context
  +
Tool Results
     │
     │ summarize / select
     ▼
Persistent Memory
     │
     │ Session ends
     │
     │
     │ later
     ▼
Persistent Memory
     │
     │ retrieve relevant state
     ▼
Session B

Prompt
  +
Retrieved Memory
  +
New Working Context
```

这里有一个容易出现的边界问题：如果 Memory 中只保存“上次做到哪里”，那 Agent 如何取得实际项目内容？比如 Memory 写着：

```text id="m7y0xk"
Next:
inspect `src/auth/middleware.py`
```

它告诉 Agent：

```text id="ssk902"
应该看什么
```

但并不需要把整个 `middleware.py` 永久复制到 Memory 中。源代码本来就存在于 Repository。因此更合理的 Memory 可以保存：

```text id="h831xi"
locator
+
reason
+
state
```

例如：

```text id="m3xm1p"
Relevant file:
src/auth/middleware.py

Why:
Remaining 403 likely originates here.

Last verified commit:
a38f91c
```

等 Agent 真正需要代码时，再从 Workspace 中读取当前版本。这使 Persistent Memory 和下一层 Workspace Context 出现了明确分工：

```text id="v0yrax"
Persistent Memory
回答：
我过去知道了什么？
我做到哪里？
哪些决定需要延续？

Workspace Context
回答：
这个工作环境现在实际有什么？
```

两者可能指向同一个 Artifact，但角色不同。Memory 可以记：

```text id="zgqm49"
README 中的 migration section 很关键。
```

Workspace 提供：

```text id="9zrbgp"
README 当前实际内容。
```

Memory 可以记：

```text id="98ynmq"
上次调查定位到了 `AuthMiddleware`。
```

Workspace 提供：

```text id="zvmlg5"
`AuthMiddleware` 当前实现。
```

这一区分也能减少 Memory duplication。如果 Repository、数据库和文档系统已经是 authoritative source，就没有必要把它们完整复制成 Agent Memory；Memory 更适合保存无法仅靠重新读取 Workspace 恢复出来的工作状态：

```text id="w49zqp"
为什么调查到这里
什么已经排除
哪些约束已确认
下一步准备做什么
```

### 4.5 Memory 保存的是工作连续性，不应该复制整个 Workspace

考虑两个极端设计。第一种 Agent 没有任何 Persistent Memory：

```text id="e37u2x"
Session A
→ investigate
→ decide
→ progress
→ end

Session B
→ 从零重新调查
```

第二种 Agent 把看过的一切全部复制进 Memory：

```text id="iuu2fk"
read file
→ copy into memory

search issue
→ copy into memory

query database
→ copy into memory

read docs
→ copy into memory
```

第一种缺乏 continuity，第二种制造大量 duplication 和 staleness。更合适的关系是：

```text id="j4melb"
Workspace
─────────────────────────────
authoritative artifacts

code
docs
issues
database
tests

        ▲
        │ locator / retrieve
        │
Memory
─────────────────────────────
agent-specific continuity state

progress
decisions
rejected paths
constraints
next actions
```

例如一个 Agent 周一读到：

```python id="vm7s4s"
class AuthMiddleware:
    ...
```

不必永久复制整个 class。Memory 只需要保存：

```text id="scx9xz"
Remaining auth failure appears before route handler.
Inspect `src/auth/middleware.py`.
```

周二 Agent 再读取当前文件。如果代码在夜间发生修改，这种模式甚至比保存旧源码更安全，因为 Agent 会重新取得当前 Workspace 状态，而不是相信昨天缓存的副本。所以长期 Agent 的一个实用原则是：

```text id="7zbeg8"
Memory 保存难以重新推导的工作状态；
Workspace 保存可以重新读取的事实源。
```

这个原则不是绝对规则。例如远程资源可能消失，实验数据可能不可复现，一次性 Tool Result 也可能需要持久化。但它提供了一个判断方向：不要因为 Agent “以后可能需要”，就把所有 Workspace Artifact 都复制到 Memory。到这里，我们已经从一次 inference 跨到了多个 Session：

```text id="62imeq"
Prompt Context
      ↓
告诉 Agent 如何开始工作

Session Context
      ↓
维持当前运行中的工作状态

Persistent Memory
      ↓
把需要延续的状态带到未来 Session
```

但 Persistent Memory 仍然没有回答一个更大的问题。假设 Memory 中只写着：

```text id="d1vp5f"
需要检查 OAuth implementation。
```

而真正完成任务所需的信息分散在：

```text id="o53hnu"
2,000 个源码文件
500 个测试
Git history
Issue tracker
数据库 schema
产品文档
API reference
```

这些信息都不应该被长期复制进 Memory，也不应该在任务开始时全部预加载。Agent 需要的是另一种能力：

> **在一个远大于 Context Window 的工作环境中，根据当前问题逐步发现并取得需要的信息。**

这就是下一层 **Workspace Context**。
## 5. Workspace Context：不要记住整个项目，让 Agent 自己去找

Persistent Memory 解决了跨 Session continuity，但它不应该复制整个工作环境。一个 Coding Agent 可以记住：

```text
上次剩余的 403
可能来自 AuthMiddleware。

下一步检查：
src/auth/middleware.py
```

真正的 `middleware.py` 仍然应该留在 Repository 中。Agent 下一次工作时重新读取当前版本，而不是依赖昨天复制进 Memory 的源码。这背后有一个更大的规模问题。一个真实 Workspace 可能包含：

```text
20,000 source files
5,000 tests
Git history
Issue tracker
API documentation
database schema
build artifacts
logs
design docs
```

即使这些信息全部对 Agent 开放，也不可能同时进入一次模型 inference。Workspace Context 因此不是：

```text
把 Workspace 放进 Context
```

而是：

```text
让 Workspace 成为
Agent 可以按需取得 Context 的环境
```

Anthropic 在 *Effective context engineering for AI agents* 中把这种模式称为 **just-in-time context**。Agent 不需要预先把所有相关数据塞进 Context，而可以保留轻量级 locator——例如文件路径、查询、链接——在真正需要时通过工具动态读取信息。文章还特别指出，Coding Agent 已经天然采用这种方式：模型可以通过 `grep`、`glob`、文件读取等操作自行探索代码库。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)这使 Context Engineering 的问题进一步变化。在 Prompt Context 中，我们问：

```text
什么必须在行动前知道？
```

到了 Workspace：

```text
什么可以等到需要时再找？
```

### 5.1 Preload 与 Just-in-Time Retrieval

最直接的 Workspace Context 策略是预加载。假设任务是：

```text
修复支付服务的重试逻辑。
```

Harness 可以在模型开始工作以前执行搜索：

```text
query:
payment retry
```

然后把 top-k 结果直接塞入 Context：

```text
User Task
    +
README
    +
payment_service.py
    +
retry.py
    +
两个相关 Issue
    +
设计文档片段
    │
    ▼
   Agent
```

这是典型的 **pre-retrieval / preload**。它有明显优势：模型第一轮就能得到可能相关的信息，不需要自己花多个 tool call 搜索。如果 retrieval 非常准确，而且任务模式稳定，这可能是成本更低的方案。问题也很明显：Harness 必须在 Agent 开始推理以前猜中什么相关。假设支付问题实际来自：

```text
src/network/backoff.py
```

但 initial retrieval 只根据语义相似度找到了：

```text
docs/payment-retry.md
src/payment/service.py
tests/payment/test_retry.py
```

那么 Agent 得到的是一组“看起来很相关”的 Context，却没有真正决定行为的文件。另一种策略是只告诉 Agent：

```text
你可以访问这个 Repository。
```

以及提供：

```text
glob
grep
read
```

让它根据当前证据逐步搜索：

```text
Task
 ↓
grep retry
 ↓
发现 PaymentService
 ↓
read PaymentService
 ↓
发现调用 BackoffPolicy
 ↓
read BackoffPolicy
 ↓
找到真正实现
```

这就是 just-in-time retrieval。两种模式可以表示成：

```text
Preload

Workspace
    │
    │ retrieval before reasoning
    ▼
Selected Context
    │
    ▼
   Agent
```

与：

```text
Just-in-Time

Workspace
    ▲
    │ tool query
    │
   Agent
    │
    │ observation
    ▼
Current Context
```

两者的根本区别不是“有没有搜索”，而是 **谁决定下一步需要什么 Context**。Preload 中：

```text
Harness
→ 先决定相关信息
→ Agent 阅读结果
```

Just-in-Time 中：

```text
Agent
→ 根据当前推理形成信息需求
→ Tool 获取信息
→ Agent 根据新证据继续搜索
```

这使 Agent 可以形成多轮的信息获取链：

```text
Question
   ↓
Search
   ↓
Evidence A
   ↓
New Question
   ↓
Search
   ↓
Evidence B
   ↓
New Hypothesis
   ↓
Read exact source
```

对 Coding Agent 来说，这尤其自然。例如最初用户只说：

```text
登录以后偶尔会被立刻登出。
```

Harness 很难仅靠一句自然语言准确判断应该预加载：

```text
frontend cookie handling
backend session store
JWT validation
Redis TTL
reverse proxy headers
```

Agent 可以从测试、日志或入口代码开始调查，在每一步缩小信息空间。但这不意味着 just-in-time retrieval 永远优于 preload。Anthropic 在文章中也明确把实践描述成 **hybrid**，而不是要求所有信息都运行时发现。稳定而小的信息适合预加载；规模大、任务相关性动态变化的信息更适合按需取得。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)可以粗略分成：

```text
适合 Preload
────────────────────────
稳定规则
项目入口说明
Tool contract
常用约束
少量高价值 metadata


适合 Just-in-Time
────────────────────────
具体源码
大量文档
历史 Issue
日志
数据库数据
不确定是否相关的 Artifact
```

真正的设计目标不是选择一个阵营，而是决定：

> 哪些信息值得每一次任务都预付 Context 成本，哪些信息应该等到形成明确需求以后再读取。

### 5.2 Progressive Disclosure：先看地图，再决定读哪里

Just-in-time retrieval 并不意味着 Agent 必须在一个完全未知的巨大空间里盲目搜索。Workspace 可以通过 **progressive disclosure** 逐层暴露信息。假设 Repository 是：

```text
repo/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── auth.md
│   └── payments.md
├── src/
│   ├── auth/
│   ├── billing/
│   ├── network/
│   └── storage/
└── tests/
    ├── auth/
    ├── billing/
    └── network/
```

Agent 不需要一开始读取全部文件内容。只看到目录结构，已经获得了相当多的信息：

```text
src/auth/
```

比：

```text
src/storage/
```

更可能与登录问题有关。文件名：

```text
refresh_token.py
```

比：

```text
invoice_export.py
```

更值得优先检查。也就是说，Context 不一定直接从“什么都不知道”跳到“读取完整 Artifact”。它可以逐层扩大：

```text
Workspace

   ↓

Metadata
path
filename
size
type

   ↓

Candidate Artifacts

   ↓

Small Preview / Search Match

   ↓

Relevant Region

   ↓

Full Artifact if necessary
```

Anthropic 在介绍 just-in-time retrieval 时特别提到，文件系统本身已经提供了丰富的 metadata。即使两个文件都叫 `test_utils.py`，下面两个路径：

```text
tests/test_utils.py
```

和：

```text
src/core_logic/test_utils.py
```

已经向模型提供了不同的语义信号。路径、目录结构和命名可以帮助 Agent 在真正读取内容之前缩小搜索范围。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)这可以看成一种 Context 的逐步展开：

```text
Level 0
────────
Repository exists

Level 1
────────
directory / filename

Level 2
────────
grep matches / metadata

Level 3
────────
relevant file region

Level 4
────────
full file / dependent artifacts
```

每升一级，都支付更多 Context 成本，但也有更明确的证据说明这些 token 值得读取。例如：

```text
用户：
修复 OAuth callback 的 state mismatch。

Agent:
glob **/*oauth*
```

得到：

```text
src/auth/oauth.py
src/auth/oauth_state.py
tests/auth/test_oauth.py
docs/oauth.md
```

Agent 不需要立即：

```text
read all four files
```

它可以先：

```text
grep "state" src/auth
```

得到：

```text
src/auth/oauth_state.py:41
src/auth/oauth.py:118
```

然后读取：

```text
src/auth/oauth_state.py:1-120
```

再根据代码中的调用：

```text
SessionStore.get(...)
```

继续查：

```text
SessionStore
```

整个过程是：

```text
locator
   ↓
small evidence
   ↓
new locator
   ↓
more precise evidence
```

这和传统“把 top-k chunk 一次性送给模型”的 RAG 有明显不同。传统 retrieval pipeline 更像：

```text
User Query
    ↓
Embedding Search
    ↓
Top-k
    ↓
LLM
```

Agentic retrieval 更像：

```text
User Goal
    ↓
LLM forms query
    ↓
Search
    ↓
Observation
    ↓
LLM updates hypothesis
    ↓
New query
    ↓
More targeted retrieval
```

因此检索本身已经成为 reasoning loop 的一部分。但这里也有成本。一次预检索可能：

```text
1 retrieval
+
1 model call
```

而 Agent 自主探索可能：

```text
grep
read
grep
read
git log
read
...
```

产生更多 latency 和 token consumption。所以 progressive disclosure 并不是免费的“更智能检索”。它是在：

```text
预先猜测相关信息
```

和：

```text
让 Agent 支付探索成本
```

之间做取舍。任务越开放、信息空间越复杂，runtime exploration 的价值通常越高；任务越固定、retrieval pattern 越稳定，preload 越有机会直接命中。

### 5.3 Claude Code：稳定规则预加载，代码按需探索

Claude Code 是这个 hybrid pattern 很直接的例子。一个 Coding Agent 启动时，可以预先获得：

```text
System Instructions
Tool Definitions
CLAUDE.md
User Task
```

其中 `CLAUDE.md` 提供项目级的稳定指导，例如：

```text
build command
test command
directory conventions
project-specific constraints
```

这些信息相对小，而且在大量任务里都有较高概率影响行为，所以适合提前进入 Context。但 Claude Code 不会因为 Repository 中有：

```text
30,000 files
```

就把它们全部预加载。实际项目内容通过：

```text
glob
grep
read
bash
```

等工具逐步取得。Anthropic 在 *Effective context engineering for AI agents* 中直接用 Claude Code 来说明 hybrid strategy：`CLAUDE.md` 被预先放进 Context，而文件系统中的具体内容则通过 `glob`、`grep` 等工具按需发现。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)可以把这个结构简化为：

```text
                    Claude Code

        ┌──────────────────────────┐
        │       Preloaded          │
        │                          │
        │ system instructions      │
        │ CLAUDE.md                │
        │ tool schemas             │
        │ user request             │
        └────────────┬─────────────┘
                     │
                     ▼
                    LLM
                     │
               information need
                     │
          ┌──────────┴──────────┐
          │                     │
        glob                  grep
          │                     │
          └──────────┬──────────┘
                     ▼
                  filepath
                     │
                     ▼
                    read
                     │
                     ▼
              Workspace Context
```

这里 `CLAUDE.md` 和源码虽然都属于项目信息，但它们进入 Context 的方式不同。原因不是：

```text
CLAUDE.md 比源码更重要
```

而是它们的复用模式不同。`CLAUDE.md` 中的一条规则可能：

```text
所有 Python 测试必须通过 uv run pytest 执行。
```

几乎每一个 Python 任务都可能用到。而：

```text
src/payments/refund.py
```

只有处理退款模块时才值得读取。因此可以用一个简单判断解释 preload：

$$
\text{Preload Value}
\propto
\text{Reuse Probability}
\times
\text{Behavioral Importance}
$$

同时还要考虑它的 token cost。这个公式仍然是本文用于解释设计直觉的抽象。例如：

```text
10 行项目规则
+
80% 的任务会用到
→ 很适合 preload

2,000 行 payment implementation
+
5% 的任务会用到
→ 更适合 JIT
```

这也解释了为什么项目 instruction file 不应该逐渐变成：

```text
Repository Encyclopedia
```

如果把每个目录结构、每个 API、每个实现细节都塞进 `CLAUDE.md`：

```text
原本：
稳定规则 preload
具体事实 JIT

最终：
稳定规则 + 大量具体事实全部 preload
```

Hybrid pattern 就会重新退化成 Context stuffing。所以 `CLAUDE.md` 更适合保存：

```text
How to work in this repo
```

而 repository 本身回答：

```text
What is actually in this repo
```

两者不能互相替代。

### 5.4 Agentic Search 不代表 RAG 失效

Just-in-time retrieval 很容易被写成一个过度结论：

```text
RAG 已经过时
Agent 会自己搜索
```

这个判断并不成立。如果一个 Workspace 有数百万份文档，让 Agent 从：

```text
/
```

开始逐级浏览，本身就非常低效。索引、embedding retrieval、全文搜索、metadata filter 仍然可以帮助 Agent 快速获得候选集。区别在于，retrieval 不必把最终 Context Selection 一次性固定下来。例如：

```text
Agent:
找出过去一年关于 OAuth migration 的设计决定。

        ↓

Search Index:
返回 20 个候选文档

        ↓

Agent:
根据 title / timestamp / owner
缩小到 4 个

        ↓

Read:
读取具体决策段落

        ↓

Agent:
发现引用 ADR-142

        ↓

Fetch:
读取 ADR-142
```

这里仍然使用了 retrieval system，只是 Agent 可以围绕 retrieval 继续推理。因此更准确的关系是：

```text
Retrieval
可以是
Agent 的 Tool
```

而不是：

```text
Retrieval
与
Agent
二选一
```

Anthropic 的文章也把 agentic search 描述成混合系统的一部分，而不是取消传统 retrieval。对于某些任务，预先把高概率相关信息放进 Context 更简单、更快；另一些任务则适合让 Agent 自主探索。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)这意味着 Workspace Context 可以有多种入口：

```text
                      Workspace

        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    File Search      Vector Search     SQL Query
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                  Candidate Evidence
                         │
                         ▼
                        Agent
                         │
                         ▼
                 Further Retrieval
```

真正的 Context Engineering 发生在最后：

```text
哪些 candidate
值得继续进入
Current Context？
```

### 5.5 Workspace Context 和 Persistent Memory 解决的是两个不同问题

到了这里，Persistent Memory 和 Workspace Context 很容易再次混在一起。两者都：

```text
存在于 Context Window 之外
```

两者都可以：

```text
通过 Tool 被读取
```

但它们保存的信息来源和职责不同。Persistent Memory 主要保存：

```text
Agent 工作过程中产生的连续性状态
```

Workspace 主要保存：

```text
任务本来就在操作的外部事实与 Artifact
```

例如：

| 信息                            | 更自然的归属                  |
| ----------------------------- | ----------------------- |
| “昨天已经排除 JWT decode”           | Persistent Memory       |
| `src/auth/token.py` 当前内容      | Workspace               |
| “下一步检查 middleware”            | Persistent Memory       |
| `src/auth/middleware.py` 当前内容 | Workspace               |
| “不能修改 public API”             | Prompt / Memory，视生命周期而定 |
| Git commit 历史                 | Workspace               |
| “commit a81f2c 很可能与当前失败有关”    | Memory / Session State  |
| 测试文件                          | Workspace               |
| “已有 42 个测试通过，剩 2 个”           | Session / Memory        |

可以用两个问题区分：

```text
Persistent Memory:
如果 Workspace 完全不变，
未来 Agent 是否仍然需要知道
“我过去做过什么”？

Workspace Context:
如果换一个全新的 Agent，
它能否从当前环境重新读取
“系统现在是什么样”？
```

于是：

```text
Memory
=
history of work

Workspace
=
state of environment
```

当然这不是严格的数据类型划分。例如一个 Issue 本身既记录环境状态，也记录历史决策；一个 `TODO.md` 既可能属于 Repository，也可能被 Agent 用作 Memory。真正重要的不是文件放在哪个目录，而是 Harness 在 Context 生命周期中如何使用它。

### 5.6 Workspace 应该尽量保留 Source of Truth

这种边界还带来一个很实际的工程好处：减少 stale Context。假设 Agent 周一读取：

```text
src/auth/config.py
```

并把整份源码复制到 Memory。周二工程师修改了：

```text
TOKEN_TTL = 3600
```

变成：

```text
TOKEN_TTL = 7200
```

如果 Agent 新 Session 直接加载昨天的 Memory copy，它看到的是：

```text
TOKEN_TTL = 3600
```

但 Repository 的 Source of Truth 已经变成：

```text
TOKEN_TTL = 7200
```

这就产生：

```text
Persistent Snapshot
        ≠
Current Workspace
```

因此 Memory 更适合保存：

```text
上次发现 TOKEN_TTL
与 session expiry 有关，
重新检查 config。
```

而不是永久保存：

```text
TOKEN_TTL = 3600
```

除非这个历史值本身就是后续分析需要的事实。这里可以形成一个实用模式：

```text
Memory
保存：
locator + interpretation + provenance

Workspace
保存：
current artifact
```

例如：

```text
Memory:

Relevant:
src/auth/config.py

Reason:
TOKEN_TTL influences refresh expiry.

Observed at:
commit a81f2c
```

Agent 下一次读取当前 Workspace：

```text
git rev-parse HEAD
read src/auth/config.py
```

如果 commit 已经变化，它就知道需要重新验证旧结论。这比把所有外部事实直接复制进 Memory 更容易处理 freshness。

### 5.7 Workspace Context 把 Agent 从“回答问题”变成“调查环境”

到这一层，Agent 和普通的一次性 Chat Completion 已经出现明显差异。普通调用更接近：

```text
Context prepared
      ↓
Model reasons
      ↓
Answer
```

Workspace-aware Agent 则可以：

```text
Goal
  ↓
形成 hypothesis
  ↓
选择信息源
  ↓
Tool query
  ↓
获得 observation
  ↓
更新 hypothesis
  ↓
决定下一次 query
  ↓
...
```

模型不再必须在第一次 inference 就拥有完成任务所需的全部事实。它需要的是：

```text
足够的 Prompt Context
让它知道如何行动

+

足够的 Tool Surface
让它取得未知信息

+

足够好的 Session Management
让探索过程不会撑爆 Context
```

这三者开始组合成一个完整 Harness：

```text
                Prompt Context
              stable control plane
                      │
                      ▼
                    Agent
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
   Session Context          Workspace Context
   what I learned           what exists outside
          │                        │
          └───────────┬────────────┘
                      │
                      ▼
               Persistent Memory
               what should survive
```

但 Workspace 仍然有一个边界。Repository、数据库和项目文档描述的是一个项目的世界。真实团队里的很多决定却并不完整地存在于这些 Artifact 中。例如代码里可以看到：

```text
payments-v2/
```

仍然存在。Issue tracker 可以看到：

```text
Migration to Payments V2
Status: Open
Priority: P0
```

README 可能仍然写着：

```text
Q3 goal:
Complete Payments V2 migration.
```

但昨天的一次产品会议已经决定：

```text
Payments V2 暂停，
等待新的合规要求确认。
```

如果这个决定只存在于会议、Slack 或某份团队文档里，那么只拥有 Repository Workspace 的 Agent 仍然会得出：

```text
应该继续 Payments V2 migration。
```

这不是它没有正确搜索 Workspace。它已经把 Workspace 搜索得很好。问题是：

> **决定当前工作优先级的信息，根本不只存在于 Workspace 内。**

Agent 一旦从“操作一个项目”扩展成“参与一个团队”，Context 的信息边界还要继续扩大。下一层面对的就是整个组织积累的：

```text
Slack
Docs
Meeting Notes
Specs
Decision Logs
Ownership
Policies
Cross-team Knowledge
```

这些内容共同构成 **Organizational Knowledge**。
## 6. Context Isolation：有些信息根本不该进入主 Agent

Workspace Context 解决了一个规模问题：Repository、数据库和文档库可以远大于 Context Window，Agent 不必提前读取全部内容，而可以通过 `glob`、`grep`、SQL、全文检索等工具逐步取得需要的信息。但只要 Agent 开始自主探索，新的问题马上出现。假设主 Agent 接到：

```text id="6gmq69"
分析最近三个月认证失败率上升的原因，
给出可能根因和修复方案。
```

为了完成任务，它可能需要：

```text id="xek4ug"
搜索代码
读取十几个文件
查询日志
分析指标
阅读 Incident
检查历史 PR
验证多个 hypothesis
```

即使每一步 retrieval 都合理，这条调查轨迹本身也可能产生几十万 token。于是我们再次遇到：

```text id="5bf314"
信息确实有用
        ≠
这些信息必须全部进入同一个 Context Window
```

Compaction 的做法是让同一个 Agent 在 Context 过长以后压缩历史；另一种办法则更早建立边界：把一个局部调查放进独立 Context，让主 Agent 只接收调查结果。Anthropic 把这种设计归入 **sub-agent architectures**。主 Agent 保留高层计划，而专门的 sub-agent 使用一个干净的 Context Window 完成深度搜索、技术调查或资料整理。一个 sub-agent 可能在自己的工作中消耗数万 token，最后只把大约 `1,000–2,000` token 的 distilled summary 返回主 Agent。这里真正改变的不是 Agent 数量，而是 Context 的拓扑。

### 6.1 Subagent 不只是并行工具，也是 Context Boundary

先看一个没有 subagent 的实现。主 Agent 需要调查三个问题：

```text id="62h1x4"
A. 最近 auth 代码发生了什么变化？

B. Production 日志里的错误模式是什么？

C. 以前有没有类似 Incident？
```

如果全部由同一个 Agent 完成：

```text id="hiq4nf"
Main Context
│
├─ git log
├─ git show × 8
├─ read source × 12
│
├─ query logs
├─ query logs again
├─ inspect stack traces
│
├─ search incidents
├─ read incident docs × 6
│
└─ synthesize
```

到了最终综合阶段，主 Context 中可能同时存在：

```text id="qb5rzz"
Git diff
源码
日志
traceback
历史 Incident
失败搜索
重复 Tool Result
中间 hypothesis
```

其中许多信息只对某一个局部调查有意义。例如为了回答：

```text id="db7mr1"
过去有没有类似 Incident？
```

Agent 可能阅读：

```text id="2qfknp"
Incident 103
Incident 117
Incident 121
Incident 132
Incident 148
Incident 155
```

最终发现只有 `Incident 132` 真正相关。如果所有搜索过程都留在主 Agent：

```text id="crzvs1"
6 份 Incident 原文
+
搜索返回
+
筛选理由
+
最终结论
```

都会持续占据主 Context。换成 subagent：

```text id="84ev4z"
                     Main Agent
                         │
            “检查类似历史 Incident”
                         │
                         ▼
                  Incident Subagent
                         │
                         ├─ search
                         ├─ read 103
                         ├─ read 117
                         ├─ read 121
                         ├─ read 132
                         ├─ read 148
                         └─ compare
                         │
                         ▼
                  Distilled Result
                         │
                         ▼
                     Main Agent
```

返回主 Agent 的可能只有：

```text id="8izfw6"
Relevant precedent:
Incident 132 (2026-05-14)

Observed pattern:
- refresh requests increased after cache eviction
- middleware performed synchronous key refresh
- latency spike caused retry amplification

Difference from current incident:
current failures return 403 rather than timeout.

Relevant artifact:
docs/incidents/132.md
```

主 Agent 不需要知道 subagent 曾经读过哪些无关 Incident，也不需要携带所有搜索结果。所以 subagent 可以理解为：

```text id="td8jqo"
Detailed Local Context
        │
        │ distill
        ▼
Interface Result
        │
        ▼
Parent Context
```

这和软件工程里的模块边界有相似之处。函数内部可能：

```text id="cg3w7d"
分配变量
循环
调用多个内部函数
处理中间错误
```

调用方通常只关心：

```text id="q1bfhi"
input
→
output
```

Subagent 也可以把复杂的信息处理过程封装在局部 Context 中：

```text id="aqbx0m"
Task
→
local exploration
→
distilled artifact
```

主 Agent 消费的是这个接口，而不是整个执行栈。Anthropic 对这种结构的描述也是 separation of concerns：详细搜索 Context 留在 subagent 中，lead agent 负责综合和分析返回结果。

### 6.2 Context Isolation 和 Parallelism 是两个不同收益

Multi-Agent 经常和：

```text id="2zbn31"
parallelization
```

绑定在一起。例如：

```text id="v98mrm"
             Main Agent
          ┌──────┼──────┐
          ▼      ▼      ▼
        Agent A Agent B Agent C
```

三个 Agent 同时执行，可以降低 wall-clock latency。但 Context Engineering 里更值得单独强调的是：**即使三个任务完全串行，subagent 仍然可能有价值。**例如主 Agent 依次执行：

```text id="3qahvx"
先调查代码
      ↓
再调查日志
      ↓
再调查历史 Incident
```

没有任何并发。如果每次调查都开独立 Context：

```text id="dyg3ma"
Main
 │
 ├─ Subagent A
 │      40k local tokens
 │      ↓
 │    1.5k summary
 │
 ├─ Subagent B
 │      60k local tokens
 │      ↓
 │    1.2k summary
 │
 └─ Subagent C
        30k local tokens
        ↓
      1.4k summary
```

主 Agent 最终看到的可能只有：

```text id="2racm6"
A summary
+
B summary
+
C summary
```

而不是：

$$
40k + 60k + 30k
$$

token 的全部探索轨迹。因此：

```text id="jq0m6y"
Subagent Value
=
Parallelism
+
Context Isolation
```

两者可以同时存在，但不是同一件事。这一区分对 Harness 设计很重要，因为如果一个任务不能并行：

```text id="1o61ci"
A 的结果
必须先于 B
```

仍然不能直接得出：

```text id="ttdr80"
那就没必要用 subagent。
```

只要 A 本身需要大量局部搜索，而且 B 只需要 A 的少量结果，隔离 Context 仍然有意义。例如：

```text id="k1pqwo"
Subagent A:
调查新的认证协议实现。

输出：
- public interface
- known limitations
- relevant files
- recommended integration point
```

主 Agent 后续实现时只需要这四项，而不需要 A 调查期间读过的几十篇文档。

### 6.3 一个 Subagent 应该返回 Artifact，而不是“我查了一下”

Context Isolation 只有在 subagent 输出足够完整时才成立。下面这种返回没有多少价值：

```text id="74kdwt"
我检查了相关代码，
问题似乎和 middleware 有关。
建议继续调查。
```

它确实短，但把 parent agent 继续行动所需的信息一起压掉了。更可靠的 handoff 应该回答：

```text id="ijglmy"
调查目标是什么？

确认了什么？

证据在哪里？

排除了什么？

还有什么不确定？

Parent 下一步需要什么？
```

例如：

```text id="v091sd"
Task:
定位 expired refresh token 返回 403 的来源。

Confirmed:
`AuthMiddleware.handle()` 在 route handler 前检查
`session.is_active`，失败时直接返回 403。

Evidence:
- src/auth/middleware.py:88-101
- tests/integration/test_refresh.py:142

Rejected:
`decode_refresh_token()` 已正确转换 expired token，
不再是剩余失败原因。

Uncertain:
当前产品语义到底要求 middleware
对 refresh endpoint bypass session check，
还是把 403 改成 401。

Next dependency:
需要查 auth Spec / historical decision。
```

这类结果已经是一个小型 Artifact。它让主 Agent 不必重新读取所有局部 Context，同时保留：

```text id="a5zvb5"
claim
evidence
uncertainty
next dependency
```

这和前面 Persistent Memory 中使用结构化状态是同一套思想：

```text id="8zlhhu"
不要把连续性寄托在
“另一个 Agent 应该记得自己看过什么”

而是把需要跨 Context Boundary 的状态
显式化成 Artifact
```

如果 subagent 只返回 prose conclusion，却不返回 evidence locator，主 Agent 后续可能无法验证它；如果只返回大量 source fragment，又没有完成 distillation，则 Context Isolation 的收益也会消失。可以把 subagent output 看成一个受预算约束的接口：

$$
O_s
=
f(E_s)
$$

其中 \(E_s\) 是 subagent 收集的全部局部 evidence，\(O_s\) 是返回 parent 的结果。希望：

$$
|O_s| \ll |E_s|
$$

但同时满足：

```text id="0og6j8"
parent 可以继续决策
+
关键 claim 可以追溯
+
不确定性没有被伪装成结论
```

这和 compaction 的 recall / precision 问题高度相似，只不过压缩发生在：

```text id="hc9vpw"
Agent Boundary
```

而不是：

```text id="fj5w14"
同一个 Agent 的 Session Boundary
```

### 6.4 Subagent Context 不是天然可信的

隔离 Context 带来的一个副作用是：parent agent 不再直接看到完整 evidence。如果 subagent 阅读了 50,000 token，只返回：

```text id="6kb3rb"
结论：应该修改 middleware。
```

parent 无法从这句话判断：

```text id="mmftfi"
它是不是漏看了反例
是不是误读了日志
是不是把 hypothesis 当成事实
是不是读到了过期文档
```

所以 Context Isolation 并不意味着：

```text id="04953c"
hide all evidence
```

更合理的是：

```text id="9i73kb"
detail stays local
+
important provenance crosses boundary
```

例如返回：

```text id="65dp78"
Claim:
middleware currently causes the 403.

Evidence:
src/auth/middleware.py:88-101
trace id: auth-prod-20260905-18421

Confidence:
high

Unresolved:
desired status-code behavior is not specified.
```

如果 parent 对这个结论产生怀疑，它可以根据 locator 精确读取：

```text id="9ts9tq"
src/auth/middleware.py:88-101
```

而不需要把整个 subagent Context 重新加载进来。因此 Context Isolation 更接近：

```text id="utlm9c"
local detail
      │
      ├─ distilled claim
      ├─ provenance
      ├─ uncertainty
      └─ locator
             │
             ▼
         parent
```

而不是：

```text id="6ll43r"
local detail
      ↓
opaque answer
      ↓
parent blindly trusts
```

这会在组织级 Context 中再次出现，因为组织搜索同样可能跨越大量 Slack、Docs 和 Meeting Notes。Agent 最终不能只是说：

```text id="9oa8pt"
公司以前讨论过，
所以应该这样做。
```

它需要知道这个判断来自哪个 Artifact、什么时候形成、是否仍然有效。

### 6.5 什么任务适合通过 Context Isolation 拆出去？

Anthropic 没有把 multi-agent architecture 描述成所有任务的默认方案。原文给出的适用场景是复杂 research / analysis，尤其当 parallel exploration 能带来收益时；相较之下，compaction 更适合维持长 conversation flow，而 structured note-taking 适合有清晰 milestone 的 iterative development。从 Context 角度，还可以增加一个判断：

```text id="2248tn"
一个子任务是否拥有
“大量局部 Context
+
较小输出接口”？
```

如果答案是肯定的，它通常比较适合隔离。例如：

```text id="l02f6y"
适合隔离
────────────────────────────
搜索几十篇论文
→ 返回 5 个候选与比较结果

分析大量日志
→ 返回错误模式与 evidence

浏览大型代码模块
→ 返回调用链和修改入口

调查历史 Incident
→ 返回相关先例

比较多个实现方案
→ 返回 trade-off table
```

因为：

$$
\text{Local Context}
\gg
\text{Useful Handoff}
$$

反过来，一个非常简单的任务：

```text id="teld2x"
读取 config.yaml 中 timeout 的值
```

如果还要：

```text id="npinsn"
spawn subagent
→ read
→ summarize
→ return
```

只是增加 orchestration overhead。所以 Context Isolation 的判断不是：

```text id="06ainb"
任务复杂
→ 多 Agent
```

而更接近：

```text id="gr9s3f"
局部探索信息量大
+
parent 只需要小型结果
→ 考虑独立 Context
```

### 6.6 Context Isolation 也可以是“读很多，带回来很少”

Anthropic 给出了一个很直观的数量级：一个 subagent 可能探索 tens of thousands of tokens，最后只返回约 `1,000–2,000` token 的 distilled summary。例如：

```text id="xbxukx"
Research Subagent

Input:
500 tokens task

Exploration:
42,000 tokens

Output:
1,600 tokens
```

对于主 Agent 来说，其 Context 成本主要变成：

```text id="t5pxiz"
task delegation
+
1,600-token result
```

而不是 42,000 token 的调查过程。假设同时有四个方向：

```text id="tax7k1"
Code       40k
Logs       50k
Docs       35k
Incidents  30k
```

如果全部直接进入主 Agent：

$$
40k + 50k + 35k + 30k
=
155k
$$

如果每个方向各返回约 1.5k token：

$$
4\times1.5k
=
6k
$$

这里不能简单理解成“Context 成本从 155k 降到 6k”，因为 subagents 仍然真实消费了自己的 token，系统总 token consumption 并没有凭空消失。降低的是：

```text id="gqx2v8"
Main Agent 的 Context Pressure
```

而不是：

```text id="8hqk0x"
全系统总推理成本
```

甚至因为 delegation、重复 Prompt 和多个 Agent 初始化，multi-agent system 的总 token 使用可能更高。这是一个需要明确保留的限制。Context Isolation 优化的是：

```text id="n2wy4d"
attention locality
separation of concerns
parent context quality
```

不保证优化：

```text id="y58gns"
total tokens
latency
monetary cost
```

如果多个 Agent 并行，wall-clock latency 可能下降；如果它们大量重复搜索，token cost 反而可能增加。因此不能从：

```text id="zsm81u"
Subagent 可以保持 Main Context 干净
```

推出：

```text id="oh3ulo"
Subagent 一定更便宜。
```

### 6.7 Context Boundary 需要明确的输入和输出 Contract

一旦 subagent 被当成 Context Boundary，它就需要像 Tool 一样有清楚的 contract。模糊 delegation：

```text id="wy5jbu"
帮我看看 auth 有什么问题。
```

容易导致 subagent：

```text id="fndyd4"
范围无限扩大
重复调查 parent 已知内容
返回大量背景
缺少明确 conclusion
```

更好的 delegation 可以是：

```text id="hx29vq"
Task:
确认当前 403 是否由 AuthMiddleware 产生。

Scope:
- src/auth/
- tests/integration/test_refresh.py

Known:
- token decode 已修复并通过 unit tests。
- 不需要重新调查 JWT decode。

Return:
1. confirmed execution path
2. relevant file + line ranges
3. evidence for 403 source
4. unresolved product-semantic question

Do not:
- modify files
- propose unrelated auth redesign
```

这样 subagent 的 Context 从一开始就得到边界：

```text id="9xqudn"
Goal
Scope
Known State
Expected Output
Constraints
```

它不需要读取 parent 的整个 Transcript，也不应该重新建立所有背景。这和 Tool Design 的逻辑一致。Tool 需要：

```text id="zdpdds"
clear inputs
clear outputs
clear semantics
```

Subagent 同样如此：

```text id="8xjb7j"
Context In
       ↓
Focused Work
       ↓
Artifact Out
```

如果 parent 每次 spawn subagent 都把完整历史复制进去：

```text id="i9t0ct"
Parent 100k Context
        ↓
复制给 Subagent
        ↓
Subagent 再开始搜索
```

那么所谓 clean context window 已经失去很大一部分意义。真正需要传递的是：

```text id="209lju"
minimum sufficient delegation context
```

也就是让 subagent 可以独立完成局部任务的最小高信号信息集合。到这里，Anthropic 文章中针对 long-horizon Context 的三种主要手段可以放在同一张图里：

```text id="ww67ze"
                        长时间 Agent
                             │
              Context 不断增长 / 超出窗口
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   Compaction         Persistent Notes       Subagents
        │                    │                    │
        ▼                    ▼                    ▼
压缩当前历史          状态移到窗口外        隔离局部探索
        │                    │                    │
        ▼                    ▼                    ▼
继续同一任务          跨时间恢复状态        只返回 distilled result
```

Anthropic 将这三种技术分别概括为：compaction 适合需要大量来回交互的任务，note-taking 适合具有明确 milestone 的迭代式开发，而 multi-agent architectures 更适合复杂 research 和 analysis。它们并不是互斥方案，一个长期 Agent 完全可能同时使用三者。例如：

```text id="4jyz8t"
Main Agent
   │
   ├─ 使用 Session Compaction
   │
   ├─ 将项目进度写进 NOTES.md
   │
   └─ 把大规模资料调查交给 Subagents
```

无论采用哪一种手段，底层原则仍然没有变化：

```text id="tyizjc"
System 可取得的信息
          ↓
经过生命周期和任务边界筛选
          ↓
当前 Agent 真正需要的信息
```

而接下来，这个“System 可取得的信息”还要继续扩大。到目前为止，我们默认 Agent 工作在一个比较清晰的 Workspace 中：

```text id="rn8353"
Repository
Database
Docs
Issue Tracker
```

但如果 Agent 不再只是一个项目里的 Coding Assistant，而是连续几周参与真实团队工作，它很快会遇到一种 Workspace Search 无法解决的问题。例如：

```text id="1p60gf"
代码显示项目还存在。

Issue 显示任务仍然 Open。

旧 Spec 显示优先级仍然是 P0。

但昨天产品、工程和法务已经在会议里决定：
项目暂停。
```

如果最后一条信息没有进入 Agent 可搜索的世界，那么即使它：

```text id="ot0vqf"
没有 Context Rot
Compaction 完美
Memory 正确
Repo 搜索准确
Subagent 调查充分
```

它仍然会基于一个已经过期的组织状态作出判断。这时缺少的 Context 不在某个更大的 Repository 中。它存在于：

```text id="oq9cgu"
团队讨论
会议记录
Slack
产品文档
设计决策
跨团队经验
权限边界
```

也就是说，Context Engineering 的问题已经从：

```text id="jguwqh"
怎样让 Agent 理解这个 Workspace？
```

扩大到：

```text id="6f1sh2"
怎样让 Agent 获得
当前任务真正需要的组织知识？
```

下一层就是 **Organizational Knowledge**。
## 7. Organizational Knowledge：组织知道，不等于 Agent 能知道

本节先引入：

```text
discoverable organizational context
```

也就是：

> 当 Agent 真正进入团队长期工作以后，Harness 的 Context 问题不再只是多少 Token，而变成组织知识是否以可搜索、可授权、可追踪的形式存在。

### 7.1 为什么组织里“没人写下来的知识”，对 Agent 来说等于不存在？

前面七个 Macro 基本都还围绕一个 Coding Agent 展开。即使加入：

```text
Planner
Generator
Evaluator
Subagent
```

它们面对的工作世界依然相对明确：

```text
Repository
Spec
Terminal
Browser
Database
```

Agent 要找的信息，大部分已经在：

```text
代码
README
CLAUDE.md
Issue
测试
Tool Result
```

这些 Artifact 里。但如果 Agent 不再只是：

> “帮我修这个 Repo。”

而是真的进入一个团队，连续几周甚至几个月工作呢？它很快会遇到一种完全不同的问题。比如今天有人在会议里决定：

> 登录页重构暂停，下季度再做。

产品经理和工程师都知道。但没有人把它写进：

```text
Slack
文档
Meeting Notes
Issue
```

第二天 Agent 搜索项目状态时，看到：

```text
旧 Spec：
登录页重构是 P0

GitHub：
还有几个相关 Issue

代码：
已经有半成品 branch
```

于是它很合理地建议：

> 下一步应该优先继续登录页重构。

人类一看：

> 这不是昨天刚取消吗？

Agent 也很冤。因为对它来说：

```text
昨天会议室里的口头决定
```

实际上从未进入它能够检索的世界。Anthropic 在 2026 年 6 月的 **Building effective human-agent teams** 里把这件事说得非常明确：Agent 对组织的理解完全建立在团队让它能够搜索到的文本上，例如 Slack、代码、文档和会议记录；私聊、走廊交流以及它无权访问的材料，都无法成为它的上下文。换句话说，对于 Agent 而言，**没有写下来并且没有权限访问的信息，效果上就等于不存在。**

* **discoverable organizational context**：组织知识只有在被显式记录、可搜索，并且位于 Agent 可访问的安全边界内时，才真正成为 Agent 可以用于决策的 Context。

---

#### 这和“Context Window 不够大”已经不是同一个问题了

Macro 1 里，我们一直在讨论：

```text
Context 太长怎么办？
```

比如：

```text
compaction
reset
handoff
transcript
```

这些问题默认有一个前提：

> **信息已经进入系统，只是怎么装进下一次模型调用。**

到了组织层，问题反过来了。不是：

```text
已有 500k Token，
怎么压成 100k？
```

而是：

```text
关键事实
压根没有进入任何
Agent 能搜索的数据源。
```

比如：

```text
会议里说过
但没纪要

私聊里决定了
但项目频道没记录

某个老员工脑子里知道
但文档里没有

文档存在
但 Agent 没权限

代码改了
但为什么改没人写
```

这些都不是：

```text
context compression problem
```

而是：

```text
context discoverability problem
```

可以画成：

```text
现实组织知识
      │
      ├─ 已写入 + 可访问
      │        ↓
      │   Agent 能检索
      │
      ├─ 已写入 + 无权限
      │        ↓
      │   Agent 看不到
      │
      └─ 根本没写
               ↓
          Agent 不可能知道
```

所以组织级 Harness 面对的第一个 Context Engineering 问题已经从：

> **“一次 Prompt 能塞多少？”**

变成：

> **“哪些现实中的组织状态，真正变成了机器可发现的 Artifact？”**

---

#### 人类其实一直依赖大量“隐式 Context”

我们自己在公司里工作，很容易低估这一点。比如一个工程师知道：

```text
这个服务别碰，
老板上周说准备下线。

这个接口虽然标 deprecated，
但某个大客户还在用。

Alex 对这块最熟，
出问题去问他。

这个项目 PRD 还写着 P1，
但实际上已经 deprioritize。

这个 Feature 看起来能上线，
但法务还没同意。
```

这些信息经常来自：

```text
饭桌
会议
私聊
表情
语气
某个人顺口一句话
历史经验
```

人类同事在组织里待久了以后，会形成一种：

```text
ambient context
```

即使没有任何数据库写着：

```text
Project X = politically dead
```

大家也知道它已经死了。Agent 没有这种长期浸泡式社会经验。它只能从：

```text
observable artifacts
```

建立组织模型。所以当人类说：

> Claude 为什么这么没有常识？

很多时候真正的问题不是模型缺少常识。而是：

> **我们把决定保留在了人类社会层，却期待 Agent 自动获得。**

---

#### “写下来”第一次变成了 Agent Infrastructure

以前做团队文档，我们通常会觉得：

```text
写文档
```

是为了：

```text
新人 onboarding
方便搜索
避免重复沟通
知识沉淀
```

这些理由当然都还成立。Anthropic 的文章还提出了一个新视角：

> Agent 本身正在成为组织文档的重要消费者。

因此：

```text
meeting notes
decision logs
design docs
Slack channel
code comments
```

不再只是在服务未来的人。它们也在服务：

```text
未来的 Agent invocation
```

Anthropic 因此建议，团队做出决定时，应尽量让决定最终落在可搜索的频道、文档或会议纪要中，而不是停留在无法被组织检索的交流里。更准确地说：

```text
Documentation
```

在 Agent Native 组织里，其实开始获得一种新的角色：

```text
Human communication artifact
          +
Agent context infrastructure
```

---

#### 这与前文强调 Artifact 的理由相同

Macro 1 里，我们说：

```text
Structured Handoff
```

为什么比：

```text
旧 Agent 自己记着
```

可靠？因为任务状态被显式化了。Macro 6 又说：

```text
Planner
Generator
Evaluator
```

通过：

```text
Spec
Contract
QA Report
```

这些 Artifact 通信，比单纯 Agent 群聊更稳定。现在同样的思想扩展到整个组织：

```text
人脑里的决定
     ↓
显式 Artifact
     ↓
组织可搜索
     ↓
Agent 可发现
```

所以三种情况其实是同一种工程动作：

#### Session 层

```text
隐式 conversation state
        ↓
handoff / transcript
```

#### Multi-Agent 层

```text
隐式 agent communication
        ↓
shared artifact
```

#### Organization 层

```text
隐式人类知识
        ↓
searchable organizational artifact
```

都是：

> **把重要状态从短生命周期、不可观察的地方，迁移到长期、可发现的载体里。**

---

#### “可搜索”比“存在”更重要

假设公司里确实有一个文档：

```text
2026-Q3-authentication-roadmap-final-v7-revised-2.md
```

里面写着：

> 登录页改版取消。

但这个文件：

```text
藏在某个人私人 Drive

没有链接

没有索引

没有加入 Agent 可访问 Connector
```

那从 Agent 使用效果看：

```text
文件存在
```

和：

```text
Agent 能找到
```

仍然是两回事。所以组织 Context 至少要经历：

```text
Record
  ↓
Index / Search Surface
  ↓
Permission
  ↓
Retrieval
  ↓
Model Context
```

只有第一步是不够的。这和普通 RAG 里经常说的：

```text
knowledge exists in corpus
≠
retrieval will surface it
```

其实完全一致。只是这里的 Corpus 已经从：

```text
几百篇 PDF
```

变成：

```text
整个组织的工作历史
```

---

#### Anthropic 为什么那么强调 Slack、代码、文档和会议记录？

因为这些系统有一个共同特点：

```text
工作过程
```

会留下：

```text
searchable text
```

例如：

#### Slack

可以留下：

```text
讨论
决策
反对意见
优先级变化
临时背景
```

#### Code

留下：

```text
实现
接口
历史约束
技术事实
```

#### Docs

留下：

```text
设计意图
产品目标
流程
策略
```

#### Meeting Notes

留下：

```text
同步讨论后的最终决定
行动项
方向变化
```

这些不同 Source 拼在一起，Agent 才可能逐渐恢复：

```text
What happened?

Why?

Who decided?

What changed?

What is current?
```

Anthropic 也提到，如果 Agent 能读取会议决策，它就不容易继续建议已经被 deprioritize 的项目；如果能读到其他团队的产品 Spec，它还能发现别的团队已经成功验证过的模式。这里最有价值的其实不是：

> Slack Connector 很好用。

而是：

> **组织的工作痕迹越完整地成为可检索 Artifact，Agent 对组织状态的重建就越接近现实。**

---

#### 这实际上是在把“组织记忆”外部化

传统组织很依赖：

```text
Alice 已经干了 8 年，
她知道为什么这里不能改。
```

问题是：

```text
Alice 离职
        ↓
组织失忆
```

所以几十年来知识管理一直在试图解决：

```text
Tacit knowledge
→
Explicit knowledge
```

Agent 的出现并没有改变这个问题。它反而提高了显式知识的价值。因为人类面对一万个 Slack Thread：

```text
根本不可能全读。
```

而 Agent 更有机会从大量文字中：

```text
搜索
聚合
比较
恢复历史
```

Anthropic 就明确认为，因为 Agent 能够比人类快得多地阅读大量文本，它可以发现人类原本会错过的相关工作，从而帮助团队保持同步。所以以前一个现实问题是：

```text
文档太多
→
没人读
→
写文档收益降低
```

而 Agent Native 组织可能出现新的关系：

```text
文档很多
        ↓
Agent 可以搜索 / 汇总
        ↓
过去不可利用的知识
重新变得有价值
```

---

#### 但这里很容易得出一个危险结论：那就让 Agent 看所有东西？

当然不是。如果只看：

```text
Context 越多
→
Agent 越聪明
```

那最简单的策略就是：

```text
全公司所有信息
全部开放给 Agent
```

这显然不成立。因为组织 Context 还有另一半：

```text
security boundary
```

Anthropic 的做法也不是取消权限。恰恰相反，他们强调的是：

> 与其每天对每个单独文档、频道做模糊的软边界判断，不如定义少量清晰的 workspace-level security boundaries；在边界内部让上下文比较自由地流动，在边界之间保持明确隔离。

这和 Macro 4 的 Permission System 其实直接对应起来了。

---

#### Coding Agent 里的 Permission 是 Action Boundary

前面我们研究 Claude Code：

```text
Bash("git status")
```

和：

```text
Bash("git push --force")
```

不应该获得相同授权。所以：

```text
Tool + input + context
        ↓
allow / ask / deny
```

这是：

```text
Action Boundary
```

到了组织 Context，变成：

```text
Slack workspace
Doc library
Meeting transcript
Repository
```

哪些可以访问？哪些不能？这是：

```text
Information Boundary
```

所以 Agent Harness 同时需要管理：

```text
              Agent
             /     \
            /       \
     Information    Action
       Boundary     Boundary
            \       /
             \     /
             Runtime
```

一个决定：

> **Agent 能知道什么。**

一个决定：

> **Agent 能做什么。**

这两者不能混。

---

#### “安全”并不意味着每天让人重新决定每个文件能不能给 Agent 看

Anthropic 在文章里对 per-item soft boundary 的批评很有意思。想象一个团队每天都要判断：

```text
这个频道 Claude 能看吗？

那个 Doc Claude 能看吗？

这条 Thread 可以给吗？

这份会议纪要呢？
```

结果就是：

```text
Decision fatigue
```

而且每个人理解还可能不一致。所以他们更倾向：

```text
先定义几个明确 Security Zones
            ↓
Workspace / Doc sharing
与 Security Zone 对齐
            ↓
Zone 内正常流动
Zone 间明确隔离
```

从 Harness 角度看，这其实和：

```text
Permission rule
```

特别像。差的规则：

```text
每次临时问
```

好的规则：

```text
提前定义可重复 policy
```

这样人类才能从：

```text
每一步审批
```

升级到：

```text
设计 policy boundary
```

这也为后续讨论 autonomy 铺路。

可以把组织知识的逐步收缩写成集合关系。设：

$$
K_{\text{org}}
$$

表示组织拥有的全部知识，Agent \(a\) 被允许访问的部分为：

$$
K_{\text{allowed}}(a) \subseteq K_{\text{org}}
$$

当前任务 \(G_t\) 真正相关的信息只是其中更小的一部分：

$$
K_{\text{relevant}}(G_t) \subseteq K_{\text{allowed}}(a)
$$

最后进入某一次 inference 的 Context 仍然只有：

$$
C_t \subseteq K_{\text{relevant}}(G_t)
$$

因此，Broad Context 描述的是 Agent 可以搜索的外部信息空间；它不意味着每轮 inference 都要装入全部组织知识。

---

#### Agent Identity 又让“谁有权限”变得更清晰

Anthropic 把多人团队 Agent 和传统个人 Assistant 区分得很明确。单人模式：

```text
Human
  ↓
自己的 Google / GitHub / Slack credential
  ↓
Agent 代表这个 Human 行动
```

而多人工作空间里的 Agent：

```text
多个 Human
      ↓
Shared Agent
      ↓
如果始终借用某一个人的身份
就很难定义它到底代表谁
```

所以这类 Agent 会需要：

```text
自己的身份
自己的 Credential
自己的 Access Boundary
```

Anthropic 将这种模式称为 **agent identity**：Agent 使用属于 Workspace 自身、由管理员配置的账号和权限，而不是永远借某个具体员工的个人身份。这意味着 Context Access 也第一次从：

```text
“谁正在和 Claude 聊天？”
```

逐渐变成：

```text
“这个 Agent identity
在这个 Workspace 里
本来就允许看到什么？”
```

对 long-running Agent 来说，这比：

```text
临时借当前用户 Token
```

稳定得多。

---

#### 因为一个长期 Agent 不应该随着“今天是谁 @ 它”改变人格和世界观

假设团队 Agent 今天被 Alice @：

```text
Alice 的权限：
Repo A
Docs A
Dashboard A
```

明天 Bob @：

```text
Bob 的权限：
Repo B
Docs B
Dashboard B
```

如果 Agent 完全：

```text
impersonate caller
```

那它的工作世界每天都在变。甚至可能出现：

```text
Agent 昨天看到某个事实
        ↓
今天换了调用者
        ↓
突然访问不到
```

对于一个真正：

```text
persistent team member
```

来说，这种身份模型很难形成稳定自治边界。所以 Anthropic 在 multiplayer agent 的基础能力中明确列出：

```text
persistent memory

credentials not tied to humans

ongoing broad information access
```

作为 Agent 长期参与团队工作的技术基础。这三个东西其实是一套：

```text
Memory
+
Identity
+
Access
```

共同定义：

> **这个 Agent 作为长期工作单元，到底生活在哪个世界里。**

---

#### 这和 Claude Code 的 QueryEngine 其实又发生了一次“尺度升级”

Macro 1 里：

```text
One QueryEngine per conversation
```

负责：

```text
session-scoped runtime state
```

现在把尺度拉大：

```text
Conversation
        ↓
Workspace Agent
        ↓
Organization
```

问题变成：

```text
哪些状态应该活过一次 conversation？

哪些目标应该记几天？

哪些知识属于整个 workspace？

哪些 credential 属于 Agent 自己？

哪些 Context 对所有团队成员可见？
```

于是：

```text
session state
```

向上变成：

```text
organizational state
```

可以画成：

```text
Model Context
     │
     │ 一次调用
     ▼
Conversation State
     │
     │ 多个 turn
     ▼
Agent Memory
     │
     │ 多天 / 多任务
     ▼
Workspace Context
     │
     │ 团队共享知识
     ▼
Organization Knowledge
```

每往上一层，Harness 需要解决的就越来越不是：

```text
Prompt 怎么写
```

而是：

```text
State
Search
Identity
Permission
Retention
```

这些系统问题。

---

#### “Work in Public”真正优化的是 Context Availability

Anthropic 把这一条建议叫：

> **Work in public and give agents broad context.**

这里的 Public 不是：

```text
发到互联网上
```

而是：

```text
在预先定义的组织安全边界内
尽量让工作可见、可搜索。
```

比如：

```text
私聊做了重要决定
```

尽量转成：

```text
项目 Channel 留一个结论
```

```text
会议改了 Roadmap
```

尽量：

```text
Meeting Notes 写清楚
```

```text
某个架构决策改变
```

尽量：

```text
Design Doc / ADR 留痕
```

这其实是在提高：

```text
organizational state observability
```

---

#### “Observability”是一个有用的类比

传统分布式系统里：

```text
服务内部发生了什么
```

如果不暴露：

```text
Logs
Metrics
Traces
```

运维人员只能猜。组织里的 Agent 也类似。现实团队每天发生：

```text
decision
trade-off
priority change
incident
customer feedback
```

如果这些都没有留下：

```text
searchable artifacts
```

Agent 同样只能猜。所以：

```text
Docs
Slack
Meeting Notes
Decision Records
```

某种意义上就是：

> **Organization Observability for Agents。**

这个词是我为了理解做的类比，不是 Anthropic 的正式术语。这个类比可以表达为：

```text
系统没有 telemetry
→ operator 看不见系统状态

组织没有 searchable artifacts
→ Agent 看不见组织状态
```

---

#### 所以未来的“上下文工程”并不只是给 Prompt 塞资料

Context Engineering 很容易被写窄。很多教程把它定义成：

```text
System Prompt
+
Memory
+
RAG
+
Tool Result
+
Compaction
```

这些当然都是 Context Engineering。但如果 Agent 真正进入团队，最上游的问题其实是：

```text
组织到底生产了什么
可供 Agent 使用的 Context？
```

如果：

```text
公司决定都口头完成

项目状态靠问人

设计原因留在人脑里

会议没人做纪要
```

那么再厉害的：

```text
RAG
Embedding
Reranker
Long Context
```

也无法检索：

```text
从未存在的 Artifact
```

这就是一句非常简单但很重的话：

> **Retrieval cannot retrieve what the organization never externalized.**

---

#### 这也解释了为什么 Blog、ADR、Issue、PR 都可能越来越重要

这甚至能反过来解释我们现在写技术博客这件事。如果我今天只是：

```text
脑子里大概理解了 Harness
```

半年以后：

```text
忘了
```

那这份知识的生命周期就是：

```text
human short-term memory
```

但写成：

```text
Bubblevan/bubblevan.github.io
```

以后，它变成：

```text
searchable artifact
```

未来：

```text
我
Agent
Search Tool
```

都可以重新利用。同样，在真实开发团队里：

```text
ADR
PR Description
Issue discussion
Incident report
Architecture doc
```

以前经常被认为是：

```text
“写给人看的附属劳动”
```

在 Agent Native workflow 里，它们会越来越像：

```text
future context substrate
```

这就是“Work in Public”真正改变工程文化的地方。

---

#### 但“所有东西都写下来”同样不是答案

这里也需要边界。否则很容易变成：

```text
既然 Agent 靠文本
→
那什么都记录
→
越多越好
```

结果：

```text
200 个 Slack Channel
20 版过期 Spec
无数会议纪要
互相冲突的 Roadmap
```

最后 Agent 搜索出来：

```text
2025：
Project X 是 P0

2026-01：
Project X 暂停

2026-03：
Project X 恢复

2026-05：
Project X 再暂停
```

然后：

> 当前到底是什么？

所以：

```text
discoverable
```

还不是完整答案。组织 Context 还需要：

```text
provenance
freshness
authority
```

也就是说 Agent 最好能知道：

```text
谁说的？

什么时候说的？

它覆盖了哪个旧决定？

当前 Source of Truth 是谁？
```

这一部分 Anthropic 这篇短文没有展开成完整知识治理框架，因此这里不把它伪装成他们已经解决的问题。但从 Harness Engineering 角度，这会是很自然的下一层。

---

#### Searchable 不等于 Truth

这一点一定要写清楚。假设 Agent 搜到：

```text
Slack：
“我们可能下个月上线。”

Old PRD：
“计划 Q3 上线。”

最新 Roadmap：
“项目取消。”
```

如果只是：

```text
retrieval top-k
```

就不一定得到正确组织状态。所以：

```text
Discoverable Context
```

解决的是：

```text
Agent 有没有机会看到证据？
```

不是：

```text
Agent 一定能正确判断事实。
```

可以继续拆：

```text
Externalization
    ↓
Searchability
    ↓
Authorization
    ↓
Retrieval
    ↓
Source evaluation
    ↓
Current belief
```

这里主要讨论前三层。后面依然还有大量 Research / Engineering 空间。

---

#### “Broad Context”也不能理解成每轮 Prompt 全塞进去

Anthropic 说 Agent 需要 broad ongoing access to information。这里的：

```text
access
```

不等于：

```text
每次 request
把整个 Slack
整个 GitHub
整个 Drive
全部放进 prompt
```

那当然不现实。更准确的是：

```text
Agent 可以在需要时
搜索这些 Source
```

因此：

```text
Broad Access
+
Selective Retrieval
```

才是可扩展形态。也就是：

```text
Organization knowledge
       │
       │ available
       ▼
Search / Tools / MCP
       │
       │ task-relevant retrieval
       ▼
Model Context
```

这又呼应 Macro 1：

```text
Runtime State
≠
Model Context
```

现在升级成：

```text
Organizational Knowledge
≠
Model Context
```

知识可以存在于更大的外部系统。当前 Context 只装：

> **这一轮真正需要的部分。**

---

#### “找到”这个动词还需要再扩展

前文一开始的第一个词是：

```text
找到
```

前面我们更多理解成：

```text
找文件
搜代码
找 Memory
```

到了这里，它变成：

```text
找到：

需求为什么改了
团队刚刚决定了什么
其他项目以前怎么解决
谁负责这件事
当前真正优先级是什么
哪些设计已经被否决
```

也就是说：

```text
Search
```

不再只是：

```text
repository search
```

而是：

```text
organizational state reconstruction
```

这对 Agent 真正进入团队工作，是一个很大的尺度变化。

---

#### 一个很适合面试的问题：为什么 Agent Native 团队更需要文档？

如果面试官问：

> 模型这么强了，为什么反而更强调写文档？

我会回答：

> 因为强模型仍然只能根据它能够观察到的信息推理。人类团队大量依赖没有显式记录的 ambient context——会议口头决定、私聊、历史经验和组织常识。Agent 没有这种隐式社会上下文。如果这些信息不被写入可搜索并且它有权访问的 Artifact，那么更大的模型 Context Window 也帮不了它。Agent Native 团队因此需要把关键决策和工作状态更稳定地 externalize，让 Slack、Docs、代码和 Meeting Notes 成为可检索的组织记忆。

再压一句：

```text
Long context
解决：
“看得下多少？”

Discoverable context
解决：
“到底有什么可看？”
```

这是两个完全不同的问题。

---

#### 为什么 Security Boundary 和 Searchability 必须一起设计？

如果只有 Searchability：

```text
Everything searchable
```

会造成：

```text
权限泄露
敏感信息暴露
```

如果只有极端 Access Control：

```text
每项信息默认不可见
每次单独授权
```

又会造成：

```text
Agent 缺 Context
permission friction
human decision fatigue
```

所以组织级 Harness 需要做的是：

```text
                 Security Boundary
                       │
             ┌─────────┴─────────┐
             │                   │
          Inside              Outside
             │                   │
             ▼                   X
     Broad discoverability    inaccessible
             │
             ▼
         Retrieval
```

这也是 Anthropic 为什么强调少量清晰的 workspace-level boundary，而不是无数模糊的 item-level sharing 决策。

---

#### 从 Coding Agent 到 Team Agent，本质上发生了什么？

可以把整个尺度变化画成：

```text
Coding Agent
────────────────

Repository
CLAUDE.md
Terminal
Tests

问题：
如何读懂并修改一个 Codebase？


        ↓


Team Agent
────────────────

Slack
Docs
Meetings
Repositories
Product Specs
Tools
Shared Memory

问题：
如何理解一个团队正在发生什么？


        ↓


Organization Agent
────────────────

Multiple workspaces
Security boundaries
Agent identity
Persistent memory
Cross-team artifacts

问题：
如何在组织边界内长期行动，
同时保持上下文、权限和责任清晰？
```

所以：

> **Harness Engineering 一旦从 Coding Agent 扩展到长期 Team Agent，Context Engineering 就自然变成 Knowledge + Identity + Access Engineering。**

---

#### 这一节真正想保留的不是“公司应该公开聊天”

而是一条更一般的原则：

> **Agent 可用的现实，不等于组织真实拥有的全部知识，而等于“被外部化、可发现并且被授权访问”的那一部分。**

写成集合直觉：

```text
Agent Knowledge
≈
Recorded Knowledge
∩
Discoverable Knowledge
∩
Authorized Knowledge
```

这不是正式数学公式。但非常好记。如果：

```text
Recorded = 0
```

再好的 Search 没用。如果：

```text
Discoverable = 0
```

文件放在那也没用。如果：

```text
Authorized = 0
```

Agent 依然看不到。这三个缺一不可。

---

#### 源码与证据边界

Anthropic 2026 年 6 月 24 日的 **Building effective human-agent teams** 可以直接支持：

* multiplayer Agent 要长期参与团队，需要 persistent memory、独立于具体人的 credential，以及持续的 broad information access；
* Agent 对团队的理解来自它能够搜索到的文本，包括 Slack、代码、文档和会议记录；
* 私聊、走廊交流和它无权访问的文档不能为 Agent 提供上下文，因此对 Agent 来说，没有记录并可访问的信息实际上等于不存在；
* Anthropic 倾向于定义少量清晰的 workspace-level security boundaries，并在边界内让 Context 更自由地流动，而不是每天处理大量模糊的 per-item sharing 决策；
* 他们建议重要决定最终进入 Channel、Docs 或 Meeting Notes，使 Agent 能够检索；
* Agent 在拥有广泛组织 Context 后，可以避免重新建议已经 deprioritize 的工作，也可以发现其他团队已经采用过的成功模式。
* Anthropic 另文把多人 Agent 的 access model 描述为 agent identity：Agent 使用 Workspace 级、管理员配置的身份和工具权限，而不是天然绑定某个单一人类账号。

本文把这些现象总结成：

```text
discoverable organizational context
```

以及：

```text
Organization Observability
```

后者是为了帮助理解所做的类比，并不是 Anthropic 的正式术语。现在我们已经回答：

> **Agent 要怎样才能真正“知道团队知道的东西”？**

答案不是：

```text
给它一个更大的 Context Window。
```

而是：

```text
让关键工作被记录
        ↓
让记录可搜索
        ↓
建立清晰的访问边界
        ↓
让 Agent 按任务检索
```

但这样一来，一个更棘手的问题马上出现。假设一个 Team Agent：

```text
记得过去几个月的工作

能搜索大量组织知识

有自己的 Credential

能调用真实工具

甚至可以主动跟进任务
```

那人类到底什么时候应该介入？如果每一步都：

```text
Ask human
```

Agent 根本没有长期自治。如果什么都：

```text
Auto allow
```

又显然不可靠。Anthropic 给出的思路不是：

```text
一开始就给最大自治权
```

而是：

> **让 autonomy 与已经被证明的 reliability 成比例。**

这也是整篇文章最后真正落回“人应该在哪里”的地方。**为什么 Agent 的自治权应该是“挣出来”的？**这里先引入一个概念：

```text
earned autonomy
```

也就是：

> **先用 review、checklist、verifier 和真实结果观察一个 Agent 是否可靠，再随着重复成功逐步放宽人类监督；而模型升级以后，还要重新测试旧 Guardrail 是否仍然需要。**

## 8. 一次完整运行：同一个请求怎样穿过五层 Context

前面几节分别讨论了 Prompt、Session、Persistent Memory、Workspace 和 Organizational Knowledge。如果只分开看，很容易把它们理解成五套独立组件：

```text
Prompt
Memory
RAG
Repository Search
Slack Search
```

更准确的理解是：它们共同组成一次 Agent Runtime 中不同生命周期、不同所有权的信息来源。可以用一个具体请求把五层串起来：

```text
检查认证服务的 migration 为什么还没有完成，
确认现在是否应该继续推进，
并给出下一步计划。
```

这个请求同时包含三个问题：

```text
发生了什么？
        ↓
为什么还没完成？
        ↓
现在应该做什么？
```

其中没有任何一层 Context 能单独回答全部问题。

### 8.1 第一层：Prompt Context 决定 Agent 怎样开始调查

Agent 启动时首先获得稳定的控制信息：

```text
System Instructions

- 先调查现状，再提出修改。
- 不把旧文档自动视为当前事实。
- 重要结论必须保留来源。
- 不自行修改 production。
```

以及 Tool Definitions：

```text
read
grep
git
issue_search
doc_search
slack_search
```

再加上用户任务：

```text
检查认证 migration 为什么还没有完成，
确认现在是否应该继续推进。
```

因此第一轮 Context 可以表示成：

```text
Prompt Context
────────────────────────────

How should I work?

What is the task?

What tools can I use?

What constraints must I respect?
```

它并没有告诉 Agent：

```text
migration 当前做到哪里
为什么停了
负责人是谁
项目现在是否仍然优先
```

这些都属于运行过程中需要取得的事实。Prompt Context 的作用只是让 Agent 有足够的控制信息开始工作。

### 8.2 第二层：Persistent Memory 告诉 Agent 上次做到哪里

假设这个 Agent 并不是第一次处理 auth migration。上一个 Session 结束前已经写入：

```text
memory/auth-migration.md
```

内容是：

```text
Goal:
migrate refresh-token path to new auth service.

Completed:
- token decoding migration
- unit tests
- staging smoke test

Remaining:
- AuthMiddleware integration
- production rollout

Confirmed:
- remaining 403 originates in AuthMiddleware

Constraint:
- do not change TokenService public API

Last relevant artifact:
src/auth/middleware.py

Last verified commit:
a81f2c
```

Agent 新 Session 不需要重新调查：

```text
JWT decode 有没有问题？
单元测试修了吗？
403 最初来自哪里？
```

Memory 提供的是：

```text
我过去已经知道什么？
```

因此：

```text
Prompt
   +
Retrieved Memory
        │
        ▼
Agent
```

这时 Agent 已经知道：

```text
技术 migration 大部分已经完成
        +
最后阻塞在 middleware
```

但 Memory 同样不应该直接回答：

```text
现在 middleware 还是那个版本吗？
```

因为 Repository 可能已经发生变化。所以 Memory 给出的是：

```text
locator
+
prior state
+
reason
```

下一步仍然需要检查当前 Workspace。

### 8.3 第三层：Workspace Context 告诉 Agent 项目现在实际是什么状态

Agent 首先检查：

```text
git rev-parse HEAD
```

发现当前 commit：

```text
c92bd14
```

已经不是 Memory 中记录的：

```text
a81f2c
```

因此旧结论需要重新验证。Agent 执行：

```text
git log -- src/auth/middleware.py
```

发现两天前已经有修改：

```text
c92bd14
fix(auth): allow refresh path through middleware
```

读取当前实现：

```text
src/auth/middleware.py
```

再运行：

```text
pytest tests/auth
```

得到：

```text
58 passed
```

继续查看 migration Issue：

```text
AUTH-382
Migration refresh flow to Auth Service V2

Status: Open
Priority: P0

Checklist:
[x] decoder migration
[x] middleware integration
[x] staging tests
[ ] production rollout
```

只根据 Workspace，Agent 现在可以得到一个比 Memory 更新的状态：

```text
Memory:
middleware 仍然阻塞

Current Workspace:
middleware 已经修复
测试全部通过
只剩 production rollout
```

这说明：

```text
Persistent Memory
不能替代
Workspace Validation
```

因为：

```text
Memory
=
过去保存的工作连续性

Workspace
=
当前 Source of Truth
```

此时 Agent 如果只拥有前三层，很可能给出：

```text
认证 migration 已经完成代码修改和 staging 验证，
当前只剩 production rollout。

建议下一步：
1. 完成 production validation
2. 安排 rollout window
3. 部署 Auth Service V2
4. 关闭 AUTH-382
```

从代码、测试和 Issue 来看，这个计划完全合理。问题是用户问的不只是：

```text
技术上还剩什么？
```

还问了：

```text
现在是否应该继续推进？
```

后一个问题已经超出了 Repository。

### 8.4 第四层：Organizational Knowledge 改变“下一步应该做什么”

Agent 搜索项目文档：

```text
doc_search:
"Auth Service V2 rollout"
```

找到旧 Roadmap：

```text
2026-Q3 Identity Roadmap

Priority:
Auth Service V2 migration = P0

Target:
production rollout before September 15
```

如果到这里停止，结论仍然是：

```text
应该尽快上线。
```

但 Agent 继续搜索最近的 Meeting Notes：

```text
2026-09-04 Identity Platform Sync
```

其中记录：

```text
Decision:
暂停 Auth Service V2 production rollout。

Reason:
Security review 发现新的 cross-region
session replication requirement。

Current scope:
- 已完成代码继续保留
- 不回滚 staging
- production rollout 暂停
- 等待 Security Architecture review

Owner:
Identity Platform

Revisit:
review 完成后重新决定 rollout date
```

这一 Artifact 直接覆盖了旧 Roadmap。现在 Agent 面对的证据是：

```text
Repository
──────────
技术实现已经基本准备好

Issue
──────────
production rollout 尚未完成

Old Roadmap
──────────
目标是在 9 月中旬上线

Latest Meeting Decision
──────────
production rollout 已暂停
```

因此正确结论变成：

```text
Migration 技术上已经接近完成，
但目前不应该继续 production rollout。
```

这里没有任何代码变化。变化的是：

```text
Agent 获得的 Context Boundary
```

只看 Workspace：

```text
remaining work
→ production rollout
```

加入 Organizational Knowledge：

```text
remaining technical work
→ production rollout

current organizational decision
→ do not rollout yet
```

两个结论并不矛盾。真正需要区分的是：

```text
Can we do it?
```

和：

```text
Should we do it now?
```

Workspace 很擅长回答第一个问题，第二个问题往往需要更大的组织 Context。

### 8.5 Session Context 保存的是这一次调查怎样改变了 Agent 的认识

在整个调查过程中，Session Context 也一直在变化。Agent 最初从 Memory 进入任务时相信：

```text
middleware 仍然阻塞 migration
```

读完当前代码以后更新为：

```text
middleware 已修复
```

读完 Issue：

```text
只剩 production rollout
```

读完旧 Roadmap：

```text
按原计划应该尽快 rollout
```

读完最新会议记录：

```text
计划已经被 supersede，
当前 rollout 暂停
```

因此本次 Session 的 Task State 最终可能是：

```text
Technical status:
- implementation complete
- middleware fix merged
- auth tests: 58 passed
- staging validation complete
- production rollout not performed

Organizational status:
- rollout explicitly paused on 2026-09-04
- blocker is Security Architecture review
- old Q3 P0 rollout target is superseded

Next:
- do not modify production
- wait for / check Security Architecture review
- keep AUTH-382 open
```

注意这里保存的不是所有 Tool Output。Agent 可能已经产生：

```text
git log output
git diff
58-test pytest output
issue search results
多个 doc search candidates
meeting notes search results
```

真正需要继续带到下一步的只是这些 observation 提炼出的状态。于是：

```text
Workspace / Organization
        │
        │ observations
        ▼
Session Context
        │
        │ distillation
        ▼
Current Task State
```

这就是第三节里：

```text
Transcript
→
State
```

在完整任务中的具体表现。

### 8.6 Context Isolation 可以把组织调查留在局部窗口

假设这个组织已经有几年历史，搜索：

```text
Auth Service V2
```

会返回：

```text
143 Slack threads
37 design docs
18 meeting transcripts
12 roadmap documents
9 security reviews
```

主 Agent 没必要把这些内容全部放进自己的 Context。它可以委派一个局部任务：

```text
Task:
找出 Auth Service V2 production rollout
当前仍然有效的组织决定。

Return:
- current status
- latest authoritative decision
- superseded decision
- owner
- evidence locator
```

Research Subagent 在独立 Context 中：

```text
search
read
compare dates
compare owners
follow references
discard obsolete docs
```

最后只返回：

```text
Current status:
PAUSED

Authoritative source:
2026-09-04 Identity Platform Sync

Reason:
pending Security Architecture review

Supersedes:
2026-Q3 Identity Roadmap rollout target

Owner:
Identity Platform

Evidence:
docs/meetings/2026-09-04-identity-platform-sync.md
```

主 Agent 只需要这个 Artifact。于是整个结构变成：

```text
                       Main Agent
                           │
              ┌────────────┴─────────────┐
              │                          │
              ▼                          ▼
        Workspace Search          Org Research Agent
              │                          │
              ▼                          │
       technical state            large local search
                                         │
                                         ▼
                                  distilled decision
              │                          │
              └────────────┬─────────────┘
                           ▼
                    Final Task State
```

Context Isolation 并没有增加一种新的知识层，它只是控制某一层的信息怎样进入 Main Context。

### 8.7 五层 Context 实际回答的是五个不同问题

到这里，可以把整个请求重新展开。用户问：

```text
检查认证 migration 为什么还没有完成，
确认现在是否应该继续推进，
并给出下一步计划。
```

Prompt Context 回答：

```text
我应该怎样完成这个任务？
```

例如：

```text
需要查证
保留 provenance
不能擅自操作 production
```

Session Context 回答：

```text
这一次调查已经发现了什么？
```

例如：

```text
middleware 已经不再是 blocker
最新组织决定已经覆盖旧 Roadmap
```

Persistent Memory 回答：

```text
上一次工作留下了什么状态？
```

例如：

```text
之前已经定位 middleware
不要重新调查 JWT decode
```

Workspace Context 回答：

```text
项目现在实际是什么样？
```

例如：

```text
当前代码
当前测试
当前 Issue
当前 implementation state
```

Organizational Knowledge 回答：

```text
团队现在对这个项目的意图是什么？
```

例如：

```text
项目仍然存在
但 production rollout 已经暂停
```

可以整理成：

| Context Layer            | 主要问题       | 本例提供的信息                       |
| ------------------------ | ---------- | ----------------------------- |
| Prompt Context           | 我应该怎样工作？   | 调查规则、工具、权限约束                  |
| Session Context          | 这一次已经发现什么？ | 当前调查状态和最新结论                   |
| Persistent Memory        | 上一次做到哪里？   | middleware 曾是 blocker         |
| Workspace Context        | 项目现在是什么状态？ | middleware 已修、58 tests passed |
| Organizational Knowledge | 团队现在想做什么？  | rollout 暂停，等待安全评审             |

这里没有任何一层是其他层的“升级版”。如果只有 Organizational Knowledge，没有 Workspace，Agent 可能知道：

```text
production rollout 已暂停
```

却不知道：

```text
技术实现到底完成没有
```

如果只有 Workspace，没有 Organization，它又会知道：

```text
只剩 rollout
```

却不知道：

```text
当前不应该 rollout
```

如果没有 Persistent Memory，它可能重复调查已经证伪的问题；没有 Session Management，则长调查过程本身可能污染 Context；如果 Prompt Context 没有要求保留 provenance，它还可能把旧 Roadmap 和新 Meeting Decision 混成一句没有来源的总结。因此五层提供的是互补状态。

### 8.8 越往外，信息空间越大；越接近模型，Context 反而必须越小

现在可以重新画一次文章开头的结构。Agent 理论上能够接触的信息从内向外不断扩大：

```text
┌───────────────────────────────────────────────┐
│            Organizational Knowledge           │
│ Slack / Meetings / Specs / Policies / Teams   │
│                                               │
│   ┌───────────────────────────────────────┐   │
│   │           Workspace Context           │   │
│   │ Repo / DB / Issues / Project Docs     │   │
│   │                                       │   │
│   │   ┌───────────────────────────────┐   │   │
│   │   │       Persistent Memory       │   │   │
│   │   │ progress / decisions / notes  │   │   │
│   │   │                               │   │   │
│   │   │   ┌───────────────────────┐   │   │   │
│   │   │   │    Session Context    │   │   │   │
│   │   │   │ current task state    │   │   │   │
│   │   │   │                       │   │   │   │
│   │   │   │   ┌───────────────┐   │   │   │   │
│   │   │   │   │Prompt Context │   │   │   │   │
│   │   │   │   └───────────────┘   │   │   │   │
│   │   │   └───────────────────────┘   │   │   │
│   │   └───────────────────────────────┘   │   │
│   └───────────────────────────────────────┘   │
└───────────────────────────────────────────────┘
```

这张图容易产生一个错误印象：

```text
越往外
Context 越大
```

准确说应该是：

```text
越往外
Available Information Space 越大
```

模型真正处理的 Context 位于另一条路径上：

```text
Organizational Knowledge
        │
        │ authorized retrieval
        ▼
Relevant Org Evidence
        │
        │ selection
        ▼
Workspace Evidence
        │
        │ state update
        ▼
Session State
        │
        │ compaction / distillation
        ▼
Current Context
        │
        ▼
       LLM
```

所以更完整的关系是：

$$
I_{\text{organization}}
\supseteq
I_{\text{workspace}}
\supseteq
I_{\text{memory}}
$$

描述信息可获得范围不断扩大，而每一次 inference 实际消费的：

$$
C_t
$$

仍然只应该包含当前行为需要的一小部分。不能写成：

$$
C_t
=
\text{Prompt}
+
\text{All Session History}
+
\text{All Memory}
+
\text{All Workspace}
+
\text{All Organizational Knowledge}
$$

实际 Harness 更接近：

$$
C_t
=
P_t
+
S_t
+
R_M(G_t)
+
R_W(G_t)
+
R_O(G_t)
$$

其中：

* \(P_t\)：当前需要的 Prompt Context；
* \(S_t\)：压缩后的 Session State；
* \(R_M\)：从 Persistent Memory 取回的相关状态；
* \(R_W\)：从 Workspace 取回的相关 evidence；
* \(R_O\)：从有权限访问的 Organizational Knowledge 中取回的相关 evidence。

这个公式仍然是本文用于整理五层模型的抽象，并不是 Anthropic 提出的形式定义。它表达的核心是：

```text
Memory 有 10 MB
≠ 读取 10 MB

Repository 有 10 GB
≠ 读取 10 GB

Slack 有十年历史
≠ 读取十年历史
```

每一层都需要自己的 selection mechanism。

### 8.9 五层之间真正传递的是 State、Locator 和 Evidence

如果把文章里的例子继续压缩，还可以看到五层之间并不需要复制完整内容。Persistent Memory 不需要复制 Workspace：

```text
记：
“检查 src/auth/middleware.py”

而不是：
复制 middleware.py 全文
```

Session Context 不需要复制所有 Tool Result：

```text
记：
“58 auth tests passed”

而不是：
永久保存完整 pytest stdout
```

Subagent 不需要返回所有 Organizational Search：

```text
返回：
“2026-09-04 meeting 暂停 rollout”

而不是：
返回 143 个 Slack thread
```

Prompt 也不需要保存完整公司知识：

```text
定义：
“重要组织状态需要查证最新 authoritative source”

而不是：
把所有组织规则写进 system prompt
```

因此跨 Context Boundary 传递的高价值对象通常可以归成三类：

```text
State
────────────
现在是什么情况？

Locator
────────────
需要时去哪里重新取得原始信息？

Evidence
────────────
为什么相信这个结论？
```

例如：

```text
State:
production rollout paused

Locator:
2026-09-04 Identity Platform Sync

Evidence:
explicit decision under “Rollout Status”
```

这种结构比单纯复制原始文本更容易跨：

```text
Session
Agent
Workspace
Organization
```

传递，同时保留重新验证的能力。它也把本文前面几节串成了同一个工程模式：

```text
Prompt
提供稳定控制状态

Session
维护当前任务状态

Memory
持久化跨 Session 状态

Workspace
提供 authoritative artifacts

Organization
提供更大范围的决策与协作证据
```

Harness 负责在这些状态之间建立：

```text
write
retrieve
validate
compact
authorize
distill
```

而不是把一切都交给一个越来越长的 Prompt。

### 8.10 Context Engineering 最终设计的是一条 Selection Path

回到文章最开始的一次模型调用：

```text
Prompt
   ↓
LLM
```

到了组织里的长期 Agent，真实的数据路径已经更接近：

```text
                         Organization
                             │
                             │ search + permission
                             ▼
                           Docs
                             │
                             │ retrieve
                             ▼
Workspace ───────────────► Evidence
   ▲                         │
   │                         │ select
   │                         ▼
   │                      Session
   │                         ▲
   │                         │ retrieve
   │                         │
   └──── locator ──────── Memory
                             │
                             ▼
                           Prompt
                             +
                      Current Task State
                             │
                             ▼
                            LLM
                             │
                             ▼
                     Action / Tool Call
                             │
                             └────────────► new state
```

这时所谓 Context Engineering 已经不再是一项“写 Prompt”的局部工作。它包含的问题是：

```text
哪些规则应该 preload？

哪些运行轨迹应该继续保留？

什么时候应该 compact？

哪些状态值得跨 Session persist？

什么信息应该留在 Workspace 按需读取？

什么调查应该隔离到 Subagent？

组织决定是否已经被记录并索引？

Agent 是否拥有读取它的权限？

新旧 Artifact 冲突时，
哪一个仍然 authoritative？

最后到底哪些 token
值得进入下一次 inference？
```

Anthropic 在 *Effective context engineering for AI agents* 中把目标概括为寻找尽可能小的高信号 token 集合；从 system prompt、tools 到 just-in-time retrieval、compaction、structured notes 和 subagents，其实都在处理这条 selection path 的不同位置。到了 *Building effective human-agent teams*，信息边界继续扩大到 Slack、文档、会议记录和组织权限，但问题的形式没有改变：Agent 只能基于它能够发现、能够访问并最终进入当前 Context 的信息行动。
[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
[Building effective human-agent teams](https://claude.com/blog/building-effective-human-agent-teams)因此本文使用：

```text
Prompt Context
      ↓
Session Context
      ↓
Persistent Memory
      ↓
Workspace Context
      ↓
Organizational Knowledge
```

并不是要提出五种新的 Context Store，也不是把 Anthropic 的文章重新包装成一套官方 taxonomy。这套划分只是为了回答一个工程问题：

> 当 Agent 从一次模型调用，逐渐扩展到跨 Session、跨项目和跨团队工作时，状态应该存在哪里，又应该在什么时候进入模型？

越靠近模型，信息应该越经过筛选；越远离模型，系统可以保存和搜索的信息越多。所以最终需要维护的不是：

```text
一个越来越大的 Prompt
```

而是：

```text
一个越来越大的可用信息空间
        +
一条越来越精确的 Context Selection Path
```

模型每一次真正看到的，只是这条路径在当前任务、当前时刻选出的结果。

