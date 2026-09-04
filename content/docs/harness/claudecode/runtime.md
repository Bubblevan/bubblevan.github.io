---
title: "Claude Code Runtime：从 QueryEngine 看一次 Agent Session 如何真正运行"
weight: 1
---

## 1. 长任务首先坏在“还能不能继续做下去”

### 1.1 Context 长不只是 Token 不够


读者已经知道 Coding Agent 通常通过一个循环持续工作：模型读取当前消息与工具结果，决定下一步动作，Harness 执行动作，再把结果放回上下文。只要任务没有结束，这个过程就可以继续。

但这里还没有解释一个问题：如果任务持续几个小时，经历几十次甚至更多次模型调用，为什么这个循环不能简单地一直运行下去？


* **long-horizon coherence**：长任务的困难不只是上下文窗口最终会装满，更在于模型能否在不断增长、不断压缩的历史中继续保持对目标、状态和下一步工作的稳定理解。


Anthropic 在 2026 年的 *Harness design for long-running application development* 中总结长任务 Agent 时，首先指出的故障并不是工具调用失败，也不是模型不会写某段代码，而是 **任务运行得足够久以后，Agent 会逐渐失去连贯性**。他们观察到，随着 context window 被越来越多的需求、代码、工具结果、错误和中间讨论填满，模型更容易偏离早期目标。

这个问题很容易被简单理解成“Token 快不够了”。如果只是容量问题，那么在达到上下文上限之前把较早的消息压缩一下，理论上就足够了。

Anthropic 的实验说明事情没有这么简单。

他们还观察到一种称为 **context anxiety** 的现象：某些模型在判断自己正在接近上下文限制时，会开始提前收尾。它可能减少继续探索，倾向于把当前状态包装成一个差不多完成的结果，而不是继续推进原本还没有完成的任务。Anthropic 特别提到，在他们较早使用 Claude Sonnet 4.5 的长任务实验中，这种现象明显到仅靠 compaction 还不够。

因此，这里其实存在两个不同问题：

```text
问题一：历史越来越长
        ↓
输入成本提高，最终超过 context window

问题二：历史本身开始影响模型的行为
        ↓
目标漂移、错误假设累积、提前收尾
```

第一个问题主要是容量管理。

第二个问题则是 **长程任务状态怎样保持可继续推理的形状**。

这也是为什么 Anthropic 区分了 **Compaction** 和 **Context Reset**。

Compaction 的做法，是在当前会话里把较早的内容总结掉，让同一个 Agent 带着缩短后的历史继续工作：

```text
完整历史

[需求]
[调查]
[修改]
[测试失败]
[继续修改]
[更多工具结果]
[更多讨论]

        ↓ compaction

[较早历史的摘要]
[最近消息]
[当前工具结果]

        ↓

同一个 Agent 继续运行
```

它最大的优势是连续性。模型不需要重新建立一套任务认知，最近的讨论和当前推理过程也仍然存在。Anthropic 后来的 Opus 4.5 实验中，模型自身的长任务连贯性已经明显改善，因此作者删除了额外的 context reset，只依赖 Claude Agent SDK 的 automatic compaction 维持长会话。

但 compaction 有一个天然限制：**它仍然是在原来的会话轨迹上继续。**

早期形成的错误假设可能被写进摘要；模型对这段任务已经形成的思维惯性也不会因为摘要而自动消失。如果问题本身正来自“这个上下文已经让模型开始错误地理解任务”，那么单纯缩短它并不一定能解决问题。

Context Reset 更激进。

它不再让当前 Agent 继续，而是把工作状态写成一个结构化的 handoff artifact，然后清空旧 context，启动一个新的 Agent：

```text
旧 Agent

目标
已完成工作
关键决策
当前代码状态
已知失败
未完成事项
下一步

        ↓ structured handoff

┌──────────────────────────┐
│ 任务目标                  │
│ 已完成：A / B             │
│ 当前失败：测试 C          │
│ 已确认约束：D             │
│ 下一步：先检查 E          │
└──────────────────────────┘

        ↓ context reset

新 Agent
        ↓
读取 handoff
        ↓
继续任务
```

Reset 解决的是另一个问题：让下一阶段工作获得一个**干净的推理环境**。Anthropic 认为这能够同时缓解上下文过长造成的连贯性下降，以及他们在 Sonnet 4.5 上观察到的 context anxiety。

代价也很直接。

新的 Agent 不再拥有旧 Agent 的完整上下文，因此 handoff 必须真的包含下一阶段所需要的状态。如果只写一句：

```text
已经完成大部分功能，继续修 Bug。
```

那么 Reset 几乎一定会丢信息。

至少需要回答：

```text
我们最终要完成什么？
现在代码处于什么状态？
已经做过哪些修改？
哪些方案已经失败？
哪些约束不能违反？
目前具体卡在哪里？
下一步最合理的动作是什么？
```

所以 Reset 并没有消灭状态管理问题，只是把状态从：

```text
隐含在巨大 conversation history 中
```

转换成：

```text
显式存在于 handoff artifact 中
```

这也是我现在理解长任务 Harness 时一个很重要的区别。

以前我容易把 context management 理解成 Token engineering：计算剩余窗口、裁剪历史、做摘要、控制工具输出长度。Anthropic 这组实验说明，对于真正长时间运行的 Agent，更准确的问题是：

> **下一轮模型究竟需要哪些状态，才能在不知道全部历史的情况下继续正确工作？**

一旦这样问，compaction、memory、transcript、task state 和 handoff artifact 就不再只是几种“省 Token 技巧”，而是在处理同一个工程问题：**如何把一次长任务的连续性从模型脆弱的短期上下文中分离出来。**

这里还要特别划清一个版本边界。

Anthropic 文中所说的 **Context Reset + structured handoff** 是他们为长时间 autonomous coding 实验额外搭建的 Harness 机制。不能因为这篇笔记接下来会研究 Claude Code，就反过来把它写成 `Claude Code v2.1.88` 已经实现的某个固定模块。

在这份 Claude Code 源码快照里，我们接下来能够直接确认的是另一组机制：

```text
conversation state
transcript persistence
compact boundary
message compaction
session resume
```

它们同样服务于“任务怎样跨很多轮继续运行”，但和 Anthropic 实验 Harness 中的 context reset 不是同一个实现。

这个区别也解释了为什么读旧版本源码仍然有价值。

具体的 Harness 结构会随着模型能力变化。Anthropic 自己就记录了这样的演化：Sonnet 4.5 时代，context reset 是重要支撑；到了 Opus 4.5，模型对长任务的处理改善以后，这层额外编排就可以删除，改回连续 session 加 automatic compaction。

所以真正值得记住的不是：

```text
长任务 Agent 必须每 N 轮 Reset
```

而是：

```text
先观察模型在哪种长期状态下开始失去连贯性
                  ↓
判断普通 compaction 是否足够
                  ↓
如果历史本身已经成为干扰，再考虑 reset
                  ↓
用显式 artifact 保存继续任务所需的最小状态
```

Harness 的设计对象不是某个永远不变的模型，而是**当前模型在真实任务中的可靠性边界**。


到这里，我们只知道了一个需求：

> 长任务不能把全部连续性寄托在模型当前的 context 里。

下一步就可以打开 Claude Code 的 `QueryEngine.ts`，看一个生产级 Coding Agent 怎样把 **conversation state 从单次模型调用中提出来**。

也就是 Beat 1.2 要回答的问题：

> **如果一次任务跨越很多轮，到底是谁替模型保存那些不会随着一次 API 调用结束而消失的状态？**


### 1.2 Claude Code 把“会话”做成了一个真正的运行时对象


上一节已经留下了一个问题：长任务不能把连续性全部寄托在模型当前看到的 context 中。

Compaction 可以减少历史，handoff 可以把关键状态显式交给新 Agent，但无论采用哪种策略，Harness 都必须先知道一件事：

> **这项任务运行到现在，到底有哪些状态需要跨模型调用继续存在？**

如果每次调用 Claude API 都只传入用户最后一句话，那么模型调用结束以后，这一轮读过哪些文件、花了多少钱、用户拒绝过什么权限、会话是否已经被取消，这些运行时信息都会无处安放。

在 Claude Code v2.1.88 的快照里，这个问题首先落在了一个很具体的对象上：`QueryEngine`。


* **session-scoped runtime state**：模型的一次 API 请求是短暂的，但 Coding Agent 的 conversation 是长期存在的。Harness 需要一个生命周期长于单次模型调用的运行时对象，持有多轮工作共同依赖的状态。


第一次看 `QueryEngine.ts` 时，我最容易犯的错误，是把它理解成另一个名字更复杂的 `query()`。

其实源码自己已经把两者的边界写得很清楚。

`QueryEngine` 上方有一段注释：

```ts
/**
 * QueryEngine owns the query lifecycle and session state for a conversation.
 *
 * One QueryEngine per conversation. Each submitMessage() call starts a new
 * turn within the same conversation. State (messages, file cache, usage, etc.)
 * persists across turns.
 */
```

这段注释基本已经把设计目的说完了：

```text
一个 conversation
        ↓
一个 QueryEngine
        ↓
submitMessage()
submitMessage()
submitMessage()
        ↓
多个 turn 共用同一批 session state
```

也就是说，`submitMessage()` 并不会为每一句用户输入重新创建一个干净的 Agent runtime。新的用户消息只是同一个 conversation 里的下一轮。消息历史、文件状态、累计用量等信息可以继续存在。

这和一次普通 LLM API 调用的生命周期差别很大。

如果把最简单的聊天程序写成：

```ts
async function ask(prompt: string) {
  return client.messages.create({
    model,
    messages: [{ role: "user", content: prompt }]
  })
}
```

函数返回以后，这次调用自己的局部状态也就结束了。

要实现多轮对话，我们当然可以把 `messages` 放到外面：

```ts
const messages = []

async function ask(prompt: string) {
  messages.push({
    role: "user",
    content: prompt
  })

  const result = await client.messages.create({
    model,
    messages
  })

  messages.push(result)
}
```

但 Coding Agent 很快就会发现：

**只有 `messages` 仍然不够。**

Claude Code 的 `QueryEngine` 至少直接持有了这些成员：

```ts
private mutableMessages: Message[]
private abortController: AbortController
private permissionDenials: SDKPermissionDenial[]
private totalUsage: NonNullableUsage
private readFileState: FileStateCache

private discoveredSkillNames = new Set<string>()
private loadedNestedMemoryPaths = new Set<string>()
```

逐个看其实很有意思，因为它们回答的是完全不同的问题。

---

##### `mutableMessages`：模型目前走过了什么路径？

最容易理解的是：

```ts
private mutableMessages: Message[]
```

这里保存的已经不只是：

```text
user
assistant
user
assistant
```

这样的聊天记录。

Claude Code 的 message stream 里还会出现：

```text
assistant
user
progress
attachment
system
compact_boundary
tool_use_summary
...
```

后面 `QueryEngine` 消费 `query()` 的流式结果时，会按照消息类型不断把相关事件加入 `mutableMessages`。

因此它更接近：

> **这条 Agent execution trajectory 到目前为止发生过什么。**

工具调用及其结果为什么一定要重新进入消息历史，也可以从这里理解。

假设模型第一次说：

```text
我应该运行 pytest。
```

Harness 真正执行以后得到：

```text
3 failed, 48 passed
```

如果这个结果只打印在用户终端里，却没有重新进入 Agent 的状态，那么下一轮 Claude 实际上并不知道测试失败了。

正确路径应该是：

```text
assistant
    ↓
tool_use: pytest
    ↓
Harness 执行
    ↓
tool_result: 3 failed, 48 passed
    ↓
写回 conversation
    ↓
下一次模型调用
```

所以 message history 不只是聊天记录。

在 Agent runtime 中，它还是**模型观察现实世界结果的通道之一**。

---

##### `readFileState`：读文件也会产生跨轮状态

第二个值得注意的是：

```ts
private readFileState: FileStateCache
```

它说明文件工具也不是纯粹：

```text
模型调用 Read
    ↓
文件内容回来
    ↓
结束
```

Harness 还维护文件读取相关状态。

这类缓存至少说明一个设计事实：**工具的执行环境本身也可能具有 conversation-level state，而不是每次调用都完全无状态。**

这里我暂时不会把 `FileStateCache` 的全部机制展开，因为那会偏离这一 Beat 的目标。现在只需要记住：

```text
conversation state
≠
LLM message history
```

一个真实 Coding Agent 的状态还可能存在于：

```text
messages
file cache
permission state
task state
background processes
memory
transcript
tool runtime
...
```

换句话说，模型看到的 context 只是整个 runtime state 的一个投影。

---

##### `permissionDenials`：用户说过“不”也是状态

还有一个很容易被教程级 Agent 忽略的字段：

```ts
private permissionDenials: SDKPermissionDenial[]
```

在 `submitMessage()` 里，Claude Code 会把传入的 `canUseTool` 包一层：

```ts
const wrappedCanUseTool: CanUseToolFn = async (...) => {
  const result = await canUseTool(...)

  if (result.behavior !== 'allow') {
    this.permissionDenials.push({
      tool_name: sdkCompatToolName(tool.name),
      tool_use_id: toolUseID,
      tool_input: input,
    })
  }

  return result
}
```

也就是说，一次权限拒绝不是弹窗消失以后就算了。

Harness 会记录：

```text
哪个 Tool
哪个 tool_use
什么 input
没有获得 allow
```

为什么要记录？

因为从 Agent runtime 的角度看：

```text
用户拒绝 rm -rf ...
```

本身就是一次重要执行结果。

如果系统完全忘记这个决定，模型后面可能不断重复提出相同动作；SDK 消费者也无法在最终结果中知道这一轮发生过什么权限事件。

实际上，`QueryEngine` 最终返回的 SDK result 里就包含：

```ts
permission_denials: this.permissionDenials
```

以及：

```ts
total_cost_usd
usage
modelUsage
num_turns
duration_ms
duration_api_ms
```

这已经开始显示一个很重要的变化：

> Coding Agent 的一次运行结果，不再只是最后那段自然语言答案。

它还包括：

```text
运行了多少轮？
花了多少钱？
用了多少 token？
为什么停止？
哪些操作被拒绝？
运行了多久？
```

这些都是 Harness state。

---

##### `totalUsage`：预算属于 Harness，不属于模型

`QueryEngine` 还维护：

```ts
private totalUsage: NonNullableUsage
```

流式 API 返回 `message_start` 和 `message_delta` 时，它持续更新本次消息的 usage；等到 `message_stop` 时，再把它累积进 conversation-level usage。

这一点看起来很普通，但它解释了为什么类似：

```text
最多运行 20 轮
最多花 5 美元
```

这种条件不能只写进 system prompt：

```text
Please do not spend more than $5.
```

模型并不知道真实账单。

真正能够判断：

```ts
getTotalCost() >= maxBudgetUsd
```

的是 Harness。

所以预算控制的边界实际上是：

```text
模型：
我还想继续尝试

Harness：
当前累计成本已经达到预算
        ↓
停止本次 execution
```

这里再次出现了我们在总页里一直强调的区别：

```text
模型决定下一步想做什么

runtime 决定当前系统还能不能继续做
```

---

##### `AbortController`：用户的 Stop 不能只是一条 Prompt

同样：

```ts
private abortController: AbortController
```

也是很典型的 runtime state。

用户在 UI 中点击 Stop 时，并不是给 Claude 再补一句：

```text
请你停止。
```

因为此时可能正有：

```text
API streaming
Bash process
MCP call
subagent
tool execution
```

正在执行。

停止行为必须从模型之外进入运行时，并通过 `AbortSignal` 传播给可以取消的任务。

所以：

```text
cancel / abort
```

也不是自然语言层面的概念，而是 Harness 的控制信号。

---

到这里，就可以更准确地理解 `QueryEngine` 这个名字。

它真正承担的不是：

```text
一个更大的 query()
```

而是：

```text
                 Conversation
                      │
          ┌───────────┴────────────┐
          │      QueryEngine       │
          │                        │
          │ messages               │
          │ file state             │
          │ usage                  │
          │ permission denials     │
          │ abort state            │
          │ memory loading state   │
          │ skill discovery state  │
          └───────────┬────────────┘
                      │
              submitMessage()
                      │
                   Turn 1
                      │
              submitMessage()
                      │
                   Turn 2
                      │
                     ...
```

每一个 turn 会结束。

但 conversation runtime 不会因此消失。

---

#### `submitMessage()` 做的第一件大事：把这一轮需要的环境重新投影给模型

有了这些 session state，并不意味着它们全部原封不动塞进模型 context。

`submitMessage()` 在真正调用 `query()` 以前，会先重新构造这一轮模型所需要看到的环境。

例如源码会调用：

```ts
const {
  defaultSystemPrompt,
  userContext: baseUserContext,
  systemContext,
} = await fetchSystemPromptParts({
  tools,
  mainLoopModel: initialMainLoopModel,
  additionalWorkingDirectories: ...,
  mcpClients,
  customSystemPrompt,
})
```

然后继续组合：

```ts
const systemPrompt = asSystemPrompt([
  ...(customPrompt !== undefined
    ? [customPrompt]
    : defaultSystemPrompt),
  ...(memoryMechanicsPrompt
    ? [memoryMechanicsPrompt]
    : []),
  ...(appendSystemPrompt
    ? [appendSystemPrompt]
    : []),
])
```

这让我觉得一个很有用的区分是：

```text
Runtime state
        ↓ 选择 / 转换 / 组装
Model context
```

而不是：

```text
Runtime state = Model context
```

模型每轮看到的是 Harness 根据当前状态组装出来的一份输入。

例如：

* 当前有哪些 Tools；
* 当前工作目录是什么；
* MCP 连接有哪些；
* 当前 model 是什么；
* additional working directories 有哪些；
* system prompt 是哪一版；
* memory mechanics 是否需要注入；
* 当前消息历史是什么。

真正长期存在的状态在 Harness 里。

当前这一轮需要推理的部分，再被投影进 context。

这其实正好接上上一 Beat：

> **Context management 的核心不只是把历史塞得更紧，而是决定下一次模型调用究竟需要看到哪些状态。**

---

#### 然后 `QueryEngine` 才把这一轮交给 `query()`

完成输入处理、system prompt 组装、skills/plugins 加载等准备以后，`QueryEngine` 才真正进入：

```ts
for await (const message of query({
  messages,
  systemPrompt,
  userContext,
  systemContext,
  canUseTool: wrappedCanUseTool,
  toolUseContext: processUserInputContext,
  fallbackModel,
  querySource: 'sdk',
  maxTurns,
  taskBudget,
})) {
  ...
}
```

到这里，`QueryEngine` 和 `query()` 的关系就比较清楚了。

可以暂时压成：

```text
QueryEngine
负责 conversation lifecycle
以及跨 turn 的 state

            ↓

submitMessage()

            ↓

query(...)
负责这一轮内部的
model → tool → result → model
执行过程

            ↓

产生的新 message / usage / state
重新回到 QueryEngine
```

这是一种很典型的生命周期分层。

如果把所有东西都写进：

```ts
async function agent() {
  while (...) {
    ...
  }
}
```

刚开始当然也能运行。

但当系统开始出现：

```text
多轮 conversation
resume
streaming
permission
abort
cost budget
compaction
MCP
subagent
SDK / REPL
```

以后，“当前这次 loop 的局部变量”和“整个 conversation 必须持续存在的状态”就必须被明确区分。

`QueryEngine` 做的正是这件事。

---

#### 一个我现在会在面试里强调的区别

所以如果面试官问：

> Claude Code 为什么还需要一个 QueryEngine？`query()` 不就已经是 Agent loop 了吗？

我不会回答成：

> 为了代码模块化。

这太浅了。

更准确的答案是：

> `query()` 描述的是一次执行过程中模型和工具如何继续交互；`QueryEngine` 描述的是这个执行过程依附在哪个 conversation runtime 上。模型调用是短生命周期的，conversation state 是长生命周期的，所以消息、文件状态、累计 usage、权限拒绝、取消信号等跨 turn 信息不能只存在于一次 query 的局部变量里。

可以进一步压成一句：

```text
query() 管这一轮怎么跑，
QueryEngine 管这段会话怎样活着。
```

这也是为什么 Claude Code 这种 Harness 和一个几十行的 ReAct demo，哪怕表面上都有：

```text
LLM
→ Tool
→ Observation
→ LLM
```

工程复杂度仍然差很多。

难的并不只是让模型循环起来。

难的是这个循环运行十分钟、一个小时甚至更久以后，系统仍然知道：

```text
我是谁？
我在哪个 conversation？
我已经做过什么？
哪些状态还有效？
用户拒绝过什么？
我还能花多少钱？
当前能不能取消？
下一轮应该带哪些东西进入模型？
```

这些问题都发生在模型外部。

这正是 Harness 开始出现的地方。


但是目前还有一个漏洞。

即使 `QueryEngine` 在内存里把 conversation state 管得很好，只要 Claude Code 进程突然退出：

```text
mutableMessages
readFileState
usage
...
```

依然可能一起消失。

长任务真正想做到“可以继续”，还必须再回答一个更苛刻的问题：

> **如果用户消息刚刚进入系统，Claude 甚至还没来得及回复，进程就被杀掉了，下一次启动凭什么知道这段 conversation 曾经存在？**

Claude Code 在这里做了一个很具体、甚至有点反直觉的选择：

**用户消息被接受以后，在真正进入 Agent query loop 之前就先写 transcript。**

这就是下一 Beat 要看的内容。


**为什么用户消息要在模型回答之前就落盘？**

### 1.3 为什么用户消息要在模型回答之前就落盘？


上一节我们已经把 Claude Code 的两层生命周期拆开了：

```text
Conversation
    ↓
QueryEngine
    ↓
submitMessage()
    ↓
一次 turn / query loop
```

`QueryEngine` 可以让 `messages`、usage、文件状态、权限拒绝等信息跨 turn 存在。

但这里还有一个非常现实的问题：

> **“存在于 QueryEngine 内存里”和“这个任务真的可以恢复”，其实是两回事。**

只要进程还活着：

```text
mutableMessages
totalUsage
readFileState
...
```

当然都在。

可如果用户刚发完一句话，Claude Code 还没收到模型回复，进程就在这一瞬间被杀掉呢？

这不是一个理论问题。

Claude Code v2.1.88 的 `QueryEngine.ts` 里，恰好留着一段异常详细的注释，专门解释这个 failure case。


* **recoverable transcript**：对一个长任务来说，“系统已经接受了这一步”不能只意味着它进入了内存；关键状态必须先进入可恢复的持久记录，才能在进程死亡后重新构造 conversation。

---

#### 先看一个很容易写出来的错误实现

如果自己写一个最小 Coding Agent，我很可能会这么组织日志：

```ts
async function submitMessage(prompt: string) {
  messages.push({
    role: "user",
    content: prompt,
  })

  const result = await runAgentLoop(messages)

  messages.push(result)

  await saveTranscript(messages)
}
```

乍看没有什么问题。

顺序是：

```text
用户输入
   ↓
Agent 开始工作
   ↓
Claude 回复
   ↓
保存 transcript
```

正常运行的时候，它确实没有问题。

问题出现在两个箭头之间：

```text
用户输入
   ↓
Agent 开始工作
   │
   │  ←─── 进程在这里死掉
   X
Claude 回复
   ↓
保存 transcript
```

此时用户明明已经看到：

```text
> 修复登录接口的 race condition
```

甚至可能已经按下 Enter 几秒钟了。

但磁盘上的 transcript 还停留在上一轮。

于是从人的角度：

> “这条任务我已经交给 Claude 了。”

从持久化系统的角度：

> “这句话从来没有发生过。”

这就是问题。

---

#### Claude Code 把持久化放在了 `query()` 前面

在 v2.1.88 恢复出的 `QueryEngine.ts` 中，`processUserInput()` 完成以后，先把这一轮产生的消息放进 `mutableMessages`：

```ts
this.mutableMessages.push(...messagesFromUserInput)

const messages = [...this.mutableMessages]
```

紧接着，并不是直接进入模型调用。

源码先做：

```ts
if (persistSession && messagesFromUserInput.length > 0) {
  const transcriptPromise = recordTranscript(messages)

  if (isBareMode()) {
    void transcriptPromise
  } else {
    await transcriptPromise

    if (
      isEnvTruthy(process.env.CLAUDE_CODE_EAGER_FLUSH) ||
      isEnvTruthy(process.env.CLAUDE_CODE_IS_COWORK)
    ) {
      await flushSessionStorage()
    }
  }
}
```

也就是说，主路径更接近：

```text
用户输入
   ↓
processUserInput()
   ↓
加入 mutableMessages
   ↓
recordTranscript()
   ↓
必要时 flush
   ↓
进入 query loop
   ↓
Claude API / Tool / 后续消息
```

而不是：

```text
用户输入
   ↓
query()
   ↓
等 Claude 回复
   ↓
最后再保存
```

源码旁边的注释甚至直接说明了为什么要这么做：原来的后续 transcript 写入依赖 `query()` yield 出 assistant、user 或 `compact_boundary` 消息，而这些都要等 API 有响应以后才会发生。如果进程在这之前死亡，session log 可能只剩下会被恢复逻辑过滤掉的 queue-operation，最终 `--resume` 会找不到 conversation。于是这里选择在**用户消息被接受以后立刻持久化**。

这不是“顺手记个日志”。

它实际上定义了一个很重要的时间点：

```text
            用户按 Enter
                 │
                 ▼
          processUserInput
                 │
                 ▼
        mutableMessages.push
                 │
                 ▼
        recordTranscript()
                 │
      ───────────┼───────────
                 │
       从这里开始，即使
       后面的模型没有回答，
       conversation 也已经
       有了可恢复的记录
                 │
                 ▼
              query()
```

我更愿意把这条线理解成：

> **任务被 Harness 接受的持久化边界。**

---

#### 为什么不能等 assistant message 回来再存？

因为模型调用本身就是失败区。

想象一次真实 Coding Agent 请求，中间可能经历：

```text
用户输入
    ↓
构造 context
    ↓
发送 HTTP 请求
    ↓
等待首 token
    ↓
streaming
    ↓
产生 tool_use
    ↓
执行 Bash
    ↓
等待 tool_result
    ↓
下一次 Claude API 请求
```

任何地方都可能被打断：

```text
Ctrl+C

UI Stop

网络断开

Claude API 超时

CLI 被系统杀掉

IDE 重启

机器休眠

进程 crash
```

如果 transcript 的创建条件是：

```text
Claude 至少成功返回了一条 assistant message
```

那么：

```text
用户已经提交任务
```

和：

```text
系统认为这个 session 可以恢复
```

之间，就存在一个失败窗口。

Claude Code 这里真正做的事情，是把这个窗口向前压：

```text
旧：

user accepted
│
├──────────── vulnerable window ────────────┐
│                                           │
API request                            assistant reply
                                             │
                                             ▼
                                         persist


现在：

user accepted
│
▼
persist
│
├────── 后续执行即使失败也已经有锚点 ──────→
│
▼
API request
```

换句话说：

> **它不是在等任务成功以后记录历史，而是在任务刚刚开始的时候就确保“这个任务曾经开始过”可以被恢复出来。**

---

#### 这和普通 logging 最大的区别是什么？

如果 transcript 只是日志，那么最自然的目标是：

```text
尽量完整记录发生过什么
```

晚一点写其实没有关系。

少一两条日志，可能只是 debug 信息不完整。

但当 transcript 被 `--resume` 用来**重建 Agent conversation**以后，它就不再只是日志。

它同时承担了：

```text
Debug artifact
        +
Conversation recovery state
```

这两种职责对“什么时候写”的要求完全不同。

普通日志可以接受：

```text
best effort
```

恢复状态则不能轻易接受：

```text
用户已经提交，
但持久记录里不存在。
```

所以我看到这段源码以后，对“Agent memory”这类词反而会谨慎很多。

有时候我们讨论 Memory，会立刻想到：

```text
向量数据库
长期偏好
知识检索
episodic memory
semantic memory
```

但对一个真正跑长任务的 Coding Agent 来说，更基础的问题甚至是：

> **刚刚那一轮用户输入，有没有活过一次进程重启？**

如果这个都做不到，再高级的长期 Memory 其实离“任务可以持续执行”还很远。

---

#### `recordTranscript(messages)` 也不是简单的 `writeFile()`

这里还有一个容易误解的地方。

源码写的是：

```ts
recordTranscript(messages)
```

并不意味着每次都简单粗暴地：

```ts
writeFile(
  "session.json",
  JSON.stringify(messages)
)
```

`sessionStorage.ts` 本身维护 session 文件、写入队列以及 transcript message 的组织方式。源码注释还特别区分了 growing-array caller，例如 `QueryEngine`，以及 compaction 以后消息前缀关系发生变化时应该怎样处理。

也就是说，真正的设计不是：

```text
偶尔 dump 一份聊天数组
```

而是：

```text
运行时消息不断产生
        ↓
session storage 按自己的持久化语义记录
        ↓
形成能够用于 resume / continue 的 transcript
```

这也是为什么代码里会存在：

```text
sessionId
parentUuid
queue-operation
compact_boundary
sidechain
summary
file-history-snapshot
...
```

这些看起来不像聊天应用需要的东西。

因为它保存的已经不是：

> “用户和 Claude 聊过什么？”

而更接近：

> “这一段 Agent execution 到底发生过什么，以及下一次应该从哪里继续。”

---

#### 为什么交互模式这里必须 `await`？

还有一个很值得抠的小细节。

源码没有统一写成：

```ts
await recordTranscript(messages)
```

而是区分：

```ts
if (isBareMode()) {
  void transcriptPromise
} else {
  await transcriptPromise
}
```

并且注释直接说明：

* `--bare / SIMPLE` 下采用 fire-and-forget；
* 普通需要 resume 的路径则等待写入；
* 某些环境下还进一步调用 `flushSessionStorage()`。

为什么？

因为：

```text
调用 save()
```

和：

```text
save 已经完成到足以支撑恢复
```

不是一回事。

假设只是：

```ts
void recordTranscript(messages)

await query(...)
```

那么仍可能出现：

```text
recordTranscript 开始
        │
        ├──────────────┐
        │              │
        ▼              ▼
   异步磁盘写入       query()
                       │
                       X process killed
```

如果此时磁盘写入还没有完成，理论上的失败窗口仍然存在。

所以普通交互路径选择：

```text
await transcript
        ↓
再继续
```

是在明确用一点 latency 换 recoverability。

源码注释甚至留下了当时观察到的成本量级：SSD 上约数毫秒，在磁盘竞争情况下可能达到几十毫秒。

这就是一个很典型的工程 trade-off：

```text
更低首响应延迟
        VS
用户发送以后立即可恢复
```

Claude Code 并没有在所有运行模式中选择同一个点。

对脚本化、bare 的调用：

```text
优先 latency
→ fire-and-forget
```

对于真正可能发生 `--resume` 的交互 session：

```text
优先 recovery guarantee
→ await persistence
```

这一点比简单写一句：

> “Claude Code 支持 session persistence。”

信息量大得多。

因为我们现在知道：

**它具体把 persistence 放在哪个时序位置，以及为什么。**

---

#### 这很像数据库里的 write-ahead 思路，但不要把两者画等号

我第一次读这里时，很容易联想到数据库的 Write-Ahead Logging。

这个类比有帮助：

```text
先把关键状态写到可恢复介质
        ↓
再执行后面可能失败的工作
```

但这里只适合把它当成**设计直觉**。

不能直接写：

> Claude Code 实现了 WAL。

因为这里并没有证明它具备数据库 WAL 的完整事务语义、redo/undo protocol 或 crash consistency guarantee。

更准确的说法是：

> Claude Code 在这个位置采用了类似 write-before-execute 的恢复思路：先确保用户已经被接受的消息进入 transcript，再进入可能被中断的 query loop。

这也正好符合我们整篇文章一直要坚持的：

```text
源码证明了什么
        ≠
我可以顺势脑补成什么
```

---

#### `resume` 恢复的不是“Claude 的脑子”

到这里还需要纠正一个很常见的表达：

> Claude Code resume 以后，Claude 还记得之前发生的事情。

严格来说并不是。

Claude 模型本身没有在 CLI 退出以后神奇地保存某个隐藏脑状态。

真正发生的是：

```text
上一进程
────────────────────

QueryEngine
    ↓
Transcript
    ↓
Disk


进程死亡


下一进程
────────────────────

Disk
    ↓
读取 Transcript
    ↓
重新构造 Conversation
    ↓
构造新的 Model Context
    ↓
新的 Claude API 调用
```

所以：

```text
continuity
```

不是来自：

```text
同一个模型实例一直活着
```

而是来自：

```text
Harness 能够把足够的状态持久化，
然后在新的模型调用前重新构造出来。
```

这和 Beat 1.1 的结论其实完全扣上了。

当时我们说：

> 长任务的关键不是永远保存完整 context，而是让下一轮拥有足够继续工作的状态。

现在又多了一层：

> 这些状态还不能只存在于当前进程里；它们必须能够跨越进程生命周期。

于是我们可以把 Macro 1 到这里得到的三层东西连起来：

```text
Beat 1.1
Long-horizon coherence

历史越来越长以后，
下一轮到底需要知道什么？
        ↓

Beat 1.2
Session-scoped runtime state

这些信息不能全部寄托给一次模型调用，
需要由 QueryEngine 这样的 runtime 持有。
        ↓

Beat 1.3
Recoverable transcript

runtime 本身也会死亡，
关键状态还必须越过进程边界持久化。
```

最后得到：

```text
模型 context
      ≠
conversation state
      ≠
durable task state
```

三者有关，但不是同一个东西。

---

#### 这也是为什么 Harness 要“拥有状态”

如果现在面试官问：

> 为什么 Agent Harness 不能只是一个 `while(tool_call)` 循环？

我觉得可以从这个例子回答得非常具体：

一个 `while` loop 可以维持：

```text
model → tool → model
```

但一个生产级 Harness 还得决定：

```text
哪些状态跨 model call？
哪些状态跨 turn？
哪些状态跨 process？
什么时候一条用户输入算真正 accepted？
进程在任意位置死亡以后从哪里恢复？
```

`QueryEngine` 负责的是其中一部分生命周期。

Transcript 又把生命周期继续向外延伸：

```text
Model call lifetime
        <
Turn lifetime
        <
Conversation lifetime
        <
Process-independent recoverable state
```

所以我现在理解 Harness 时，会把“状态所有权”看得比以前重很多。

很多 Agent demo 的控制流其实没错。

真正缺的是：

> **谁拥有状态，以及这个状态能活多久。**

---

### Macro 1 小结：长任务首先是一道状态连续性问题

到这里，Anthropic 那篇长任务 Harness 文章里所谓的：

```text
context degradation
context anxiety
compaction
reset
structured handoff
```

就不再只是 Prompt 技巧了。

它们背后其实共享一个问题：

> **任务的连续性应该寄托在哪里？**

最脆弱的方式是：

```text
全部寄托在当前模型 context
```

更进一步是：

```text
Harness 持有 conversation runtime state
```

再进一步是：

```text
关键状态进入可恢复 artifact / transcript
```

如果任务真的长到需要换 Agent、换 context、甚至换进程：

```text
当前模型
可以死

当前 context
可以丢

当前进程
也可以重启

但任务状态
必须还能重新构造
```

这就是我认为 Macro 1 最值得记住的一句话：

> **Long-running Agent 的“长期”首先不是模型连续运行得足够久，而是任务状态不依赖任何一个短生命周期组件才能继续存在。**

---

#### 源码与证据边界

这里仍然要保留版本与证据边界。

本文阅读的是从 npm 发布物 `@anthropic-ai/claude-code@2.1.88` 的 source map 恢复出的源码快照，而不是把第三方仓库当作 Anthropic 官方开发仓库。该快照仓库明确说明其来源是 npm 包中的 `cli.js.map`。

从这份源码，我们可以直接确认：

```text
QueryEngine 在进入 query loop 前
持久化已经接受的用户消息；

普通交互路径会等待 transcript 写入；

特定模式还会主动 flush；

源码明确把这样做的原因
和 --resume 在 kill-before-response 场景下的失败联系起来。
```

但这里**不能反向证明**：

```text
Claude Code 的 transcript
=
Anthropic 长任务实验中的 structured handoff
```

它们解决的是相关但不同的问题：

```text
Transcript
    → 尽量保存真实 execution history
    → 支撑 conversation resume

Structured handoff
    → 主动提炼继续任务所需状态
    → 支撑 context / agent reset
```

一个更偏：

```text
recover history
```

另一个更偏：

```text
distill state
```

后面讲 Context Reset 时，不能把它们混成同一种机制。


Macro 1 到这里已经回答了：

```text
一个任务怎样活过
一次 model call、
多个 turn，
甚至一次 process death？
```

但我们仍然只是解决了：

> **Agent 怎样继续活着。**

下一步要问的不是状态，而是动作：

> **模型说“我要读文件”“我要执行测试”“我要修改代码”以后，为什么不能把这句话本身就当成动作？**

因为 LLM 能产生的首先只是一个**动作提议**。

真正接触文件系统、shell、网络和外部世界的，是 Harness。

## 2. Agent loop 真正循环的不是“思考”，而是现实反馈

### 2.1 一次模型输出为什么还不算一次动作？


Macro 1 已经解决了长任务的第一层问题：

```text
模型 context 会变化
        ↓
conversation state 不能只活在一次模型调用里
        ↓
QueryEngine 持有跨 turn 状态
        ↓
transcript 让关键状态进一步跨越 process death
```

因此，到目前为止我们解决的是：

> **Agent 怎样持续存在。**

但一个 Coding Agent 只“活着”显然没有意义。

它还得真的：

```text
读文件
搜索代码
修改代码
执行测试
运行命令
访问 MCP
启动子 Agent
```

这里就出现了 Harness 的第二个核心问题。

假设 Claude 输出：

```json
{
  "name": "Bash",
  "input": {
    "command": "pytest"
  }
}
```

这时测试跑了吗？

**没有。**

模型只是生成了一段结构化输出。

真正的：

```text
fork process
执行 pytest
读取 stdout / stderr
取得 exit code
发现 3 failed
```

还没有发生。

这一节只引入一个概念：


* **tool-mediated action**：LLM 产生的是对动作的提议；Harness 才负责把这个提议映射成真实环境中的执行，并把执行结果重新变成模型能够观察的输入。

---

#### 先把一个最容易混淆的地方拆开

我们平常会很自然地说：

> Claude 执行了 `pytest`。

> Claude 读取了 `QueryEngine.ts`。

> Claude 修改了这个文件。

这种说法在人机交互层面没有问题。

但如果从 Agent runtime 的结构去看，它把两件完全不同的事情压成了一句话。

真正的路径其实更接近：

```text
Claude
  │
  │  “我想运行 pytest”
  ▼
tool_use
  │
  │  structured proposal
  ▼
Harness
  │
  │  找到 Bash Tool
  │  检查输入
  │  检查权限
  │  执行命令
  ▼
Operating System
  │
  │  pytest 真正运行
  ▼
stdout / stderr / exit code
  │
  ▼
Harness
  │
  │  转换成 tool_result
  ▼
Claude
  │
  │  “原来现在有 3 个测试失败”
  ▼
决定下一步
```

这条链里，只有中间那部分真的接触了现实世界。

LLM 本身负责的是：

```text
根据目前观察
提出下一步动作
```

Harness 负责的是：

```text
让动作真正发生
+
告诉模型到底发生了什么
```

这一区别看起来像基础知识，但它实际上决定了我们怎么理解整个 Agent loop。

---

#### 一个 `tool_use` 本身不会改变任何东西

先用最小例子看。

模型可能返回：

```json
{
  "type": "tool_use",
  "id": "toolu_123",
  "name": "Read",
  "input": {
    "file_path": "/src/auth.ts"
  }
}
```

这个结构表达的是：

```text
模型预测：

“根据我现在知道的信息，
下一步最好读取 /src/auth.ts。”
```

仅此而已。

假如 Harness 在这里突然 crash：

```text
assistant:
  tool_use(Read, "/src/auth.ts")
          ↓
          X
      process died
```

文件有没有被读？

未必。

模型不能因为自己生成了：

```text
Read("/src/auth.ts")
```

就自动拥有文件内容。

同理：

```text
Bash("rm foo")
```

不等于文件已经删除。

```text
Edit(...)
```

不等于磁盘已经改变。

```text
Agent(...)
```

也不等于一个 subagent 已经真的被创建。

所以必须把：

```text
intention
```

和：

```text
effect
```

分开。

我觉得这是理解 Harness 很重要的一步。

---

#### Claude Code 的 `query()` 本身就是一个跨多次模型调用的循环

回到 v2.1.88 的 `query.ts`。

`query()` 并不是简单地：

```ts
return callClaude(messages)
```

源码内部进入的是一个 `queryLoop()`，并显式维护跨 iteration 的状态：

```ts
type State = {
  messages: Message[]
  toolUseContext: ToolUseContext
  autoCompactTracking: AutoCompactTrackingState | undefined
  ...
  turnCount: number
  transition: Continue | undefined
}
```

然后：

```ts
while (true) {
  ...
}
```

换句话说，一次用户 turn 内部本身还可以包含多次：

```text
model invocation
    ↓
tool execution
    ↓
model invocation
    ↓
tool execution
    ↓
...
```

源码甚至直接把这些字段称为 **Mutable cross-iteration state**。

所以这里要先纠正一个术语直觉：

```text
用户的一轮对话
```

不等于：

```text
一次 Claude API 请求
```

一个 turn 完全可能是：

```text
User
│
│ “修复这个 bug”
▼
Claude API #1
│
│ tool_use: Read
▼
Read
│
│ tool_result
▼
Claude API #2
│
│ tool_use: Edit
▼
Edit
│
│ tool_result
▼
Claude API #3
│
│ tool_use: Bash pytest
▼
Bash
│
│ tool_result: 3 failed
▼
Claude API #4
│
│ tool_use: Edit
▼
...
```

到最后 Claude 才可能真正返回：

```text
已经修复，并通过全部测试。
```

这才是 Agent loop。

---

#### 模型首先产生 `tool_use`

在每一次 iteration 里，Claude Code 都会把当前：

```text
messages
systemPrompt
userContext
tools
...
```

送给模型。

模型可以直接回答文本，也可以产生一个或多个 `tool_use` block。

概念上类似：

```text
AssistantMessage
├─ text
├─ thinking
└─ tool_use
      ├─ id
      ├─ name
      └─ input
```

这里的 `tool_use.id` 很重要。

例如：

```json
{
  "type": "tool_use",
  "id": "toolu_A",
  "name": "Bash",
  "input": {
    "command": "pytest"
  }
}
```

随后真实结果回来时，会通过同一个 id 对应：

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_A",
  "content": "3 failed, 48 passed"
}
```

于是系统才能知道：

```text
tool_use A
    ↓
对应
    ↓
tool_result A
```

而不是把一堆命令和结果混在一起。

甚至在异常路径中，如果某个 Tool 没有正常得到结果，`query.ts` 也会构造与原 `tool_use.id` 对应的 error `tool_result`：

```ts
{
  type: 'tool_result',
  content: errorMessage,
  is_error: true,
  tool_use_id: toolUse.id,
}
```

这说明一个很关键的契约：

> **对 Agent 来说，“动作失败”仍然应该成为 observation，而不是从 execution trajectory 里凭空消失。**

---

#### 然后 Harness 才真正执行这些 Tool

`query.ts` 拿到模型产生的 Tool Calls 后，会进入 Tool execution 路径。

源码中可以看到：

```ts
const toolUpdates = streamingToolExecutor
  ? streamingToolExecutor.getRemainingResults()
  : runTools(
      toolUseBlocks,
      assistantMessages,
      canUseTool,
      toolUseContext,
    )

for await (const update of toolUpdates) {
  ...
}
```

这里的结构已经足够说明：

```text
模型生成 tool_use
        ↓
query.ts 收集 Tool Calls
        ↓
runTools(...)
        ↓
真实 Tool execution
        ↓
不断产生 update
```

注意 `runTools()` 是 Claude Code 自己 runtime 的函数。

它接收：

```ts
toolUseMessages
assistantMessages
canUseTool
toolUseContext
```

然后进一步把每个 Tool Call 送给：

```ts
runToolUse(...)
```

执行。

也就是说：

```text
Claude API
```

和：

```text
Tool runtime
```

在架构上确实是两层不同的东西。

---

#### 这里有个非常重要的“现实边界”

假设 Claude 说：

```text
我认为 src/auth.ts 第 47 行有一个 race condition。
```

这仍然只是模型对当前 context 的推理。

它可能对，也可能错。

然后它提出：

```text
Read(src/auth.ts)
```

这还是 proposal。

只有 Harness 真正打开文件以后返回：

```text
第 47 行实际上是：
...
```

模型才获得了新的现实证据。

因此可以把整个 Agent 过程抽象成：

```text
           Model
             │
             │ proposal
             ▼
           Action
             │
             │ executed by Harness
             ▼
         Environment
             │
             │ observation
             ▼
        Tool Result
             │
             └──────────────→ Model
```

这也是为什么我觉得：

```text
LLM → Tool → LLM
```

这个常见写法其实少了一层。

更准确的写法应该是：

```text
Model
  ↓ proposes
Harness
  ↓ executes
Environment
  ↓ returns reality
Harness
  ↓ encodes observation
Model
```

**Harness 正好夹在“语言世界”和“现实世界”中间。**

---

#### Tool Result 才是下一轮推理真正新增的信息

假设任务是：

> 修复所有单元测试。

第一次模型调用认为：

```text
可能是 tokenizer.py 的问题。
```

如果只是让模型继续“想”：

```text
Model #1
  ↓
Model #2
  ↓
Model #3
```

它不会凭空知道测试究竟怎么失败。

真实 Agent 必须做：

```text
Model #1
    ↓
Bash("pytest")
    ↓
3 failed
    ↓
Model #2
```

此时第二次模型调用和第一次相比，真正新增的重要信息不是：

```text
我又思考了一轮
```

而是：

```text
真实 pytest 告诉我：

test_merge failed
expected ...
actual ...
```

再例如：

```text
Model #2
    ↓
Read("tokenizer.py")
    ↓
真实源码
    ↓
Model #3
```

新增的又不是更多内部推理，而是：

```text
文件实际长什么样
```

于是我现在更愿意把 Agent loop 理解成：

```text
Hypothesis
    ↓
Action
    ↓
Observation
    ↓
Updated hypothesis
    ↓
Action
    ↓
Observation
```

而不是：

```text
Think
↓
Think harder
↓
Think even harder
```

---

#### 这也是 ReAct 真正重要的地方

我们经常把 ReAct 背成：

```text
Thought
Action
Observation
Thought
Action
Observation
```

背完以后很容易觉得：

> 不就是 Prompt 里多加三个标签吗？

但到了 Coding Agent runtime 里，`Observation` 其实是非常重的一环。

它可能来自：

```text
Read
    → 磁盘真实内容

Grep
    → repository 中真实匹配

Bash
    → stdout / stderr / exit code

Edit
    → 文件系统真实修改结果

MCP
    → 外部服务真实响应

Agent
    → 另一个执行单元的真实结果
```

只有这些东西重新进入 execution trajectory，下一次 model call 才是在**新世界状态**上推理。

于是 ReAct 在工程里真正变成：

```text
模型生成 Action
       │
       ▼
Harness 执行 Action
       │
       ▼
环境发生或拒绝发生变化
       │
       ▼
Harness 捕获 Observation
       │
       ▼
Observation 写回 Messages
       │
       ▼
再次调用模型
```

所以重点不在：

```text
Thought 字段怎么写
```

而在：

> **Observation 是否真的来自执行后的世界。**

---

#### 一个失败结果甚至比成功结果更重要

假设 Claude 想：

```text
我修改完函数以后，测试应该通过。
```

然后执行：

```text
pytest
```

现实回来：

```text
FAILED test_login_race
AssertionError: expected 1 session, got 2
```

此时 Agent 面临的是：

```text
模型预测：
    修好了

现实：
    没修好
```

如果 Harness 把这个失败结果忠实送回模型：

```text
prediction
    ≠
observation
```

模型就还有机会修正。

如果不执行测试，只让 Claude 自己判断：

```text
代码看起来没问题。
```

那么这个 mismatch 永远不会出现。

这其实已经提前碰到了后面 Anthropic evaluator 那一 Macro 的核心：

> 模型自己的“我觉得完成了”和环境真正证明“完成了”，是两套信号。

但这一 Beat 暂时不展开 evaluator。

现在只需要记住一个更底层的事实：

```text
Tool result
```

就是最基础的一种 external feedback。

---

#### 为什么 Tool failure 也必须返回给模型？

再看一个细节。

假设 Claude 请求：

```text
Bash("npm test")
```

但系统返回：

```text
command not found
```

错误的 Agent runtime 可能写成：

```ts
try {
  await runTool()
} catch {
  // ignore
}
```

然后直接让模型继续。

这样模型下一轮看到：

```text
我刚才请求了 npm test
```

却看不到：

```text
它根本没有成功运行
```

于是它很容易产生一个错误假设：

> 测试应该已经运行了，只是没有问题。

因此执行失败也必须显式进入 trajectory：

```text
tool_use
   ↓
execute
   ↓
ERROR
   ↓
tool_result(is_error=true)
   ↓
next model call
```

Claude Code 的异常路径正是这样给缺失 Tool Result 构造 error result，并保留对应 `tool_use_id`。

所以：

> **失败不是 loop 的异常噪音；失败本身就是模型下一步决策需要的 observation。**

这是我认为很值得记住的一句话。

---

#### 到底是谁“调用 Tool”？

这个问题在面试里其实可以故意抠字眼。

问：

> Claude 会调用 Bash 吗？

比较松的回答当然是：

> 会。

但如果讲 Harness，可以进一步说：

> Claude 生成 Bash Tool 的结构化调用请求；Claude Code runtime 解析这个 `tool_use`，根据当前 ToolContext 和权限策略决定如何执行，再把真实结果包装成 `tool_result` 返回给后续模型调用。

差别就在：

```text
Claude：
决定想调用什么

Harness：
决定这个调用如何落地

Environment：
决定真正发生了什么
```

这三者不能混成一个“Claude 执行了”。

---

#### 这也解释了为什么 Model 和 Harness 的能力边界不同

假设 Claude 本身很聪明，但 Harness 只有：

```text
Read
```

那么它最多能：

```text
理解代码
分析问题
提出修改建议
```

却无法真正：

```text
Edit
Bash
Git
Browser
MCP
```

反过来，Harness 即使有一百种 Tool：

```text
Shell
Browser
Database
GitHub
Slack
AWS
...
```

模型不会正确选择和组合它们，也没有用。

最终能力更接近：

```text
Agent capability
=
Model reasoning
×
Harness action surface
×
Feedback quality
```

这里不是数学公式，只是帮助理解：

任意一项接近零，整体能力都会明显塌掉。

例如：

```text
强模型
+
弱 Tool surface
=
想得到，做不到
```

```text
强 Tool surface
+
弱模型
=
什么都能做，但乱做
```

```text
强模型
+
强 Tool
+
没有真实 feedback
=
做了以后不知道做成什么样
```

所以 Coding Agent 的能力绝不只是：

```text
benchmark 上模型代码能力有多高
```

还取决于 Harness 是否让它可靠接触现实。

---

#### 从这里重新理解父文的五个动词

父文里我们把 Harness 压成：

```text
找到
行动
观察
约束
修正
```

现在 Macro 2 已经可以把中间三个开始接起来：

```text
模型提出 Tool Call
       ↓
【行动】
Harness 执行
       ↓
真实世界产生结果
       ↓
【观察】
Tool Result 回来
       ↓
重新进入 context
       ↓
【修正】
模型依据新证据改变下一步
```

所以：

```text
Action → Observation → Revision
```

并不是三个抽象能力标签。

它在 Claude Code 源码里真的对应了一条 runtime path。

---

#### 我现在会怎样定义 Agent Loop？

以前如果别人问：

> Agent loop 是什么？

我可能会回答：

```text
LLM 不断调用工具，直到任务完成。
```

现在我觉得这句话至少少了一半。

更准确的是：

> Agent loop 是 Harness 不断把模型基于当前状态提出的动作映射到真实环境，再把环境反馈重新编码进模型输入，使下一步决策能够建立在更新后的现实状态上，直到达到停止条件。

压缩成图就是：

```text
          ┌──────────────────────┐
          │                      │
          ▼                      │
       Model                     │
          │                      │
          │ propose              │
          ▼                      │
      tool_use                   │
          │                      │
          ▼                      │
       Harness                   │
          │                      │
          │ execute              │
          ▼                      │
     Environment                 │
          │                      │
          │ result               │
          ▼                      │
      tool_result                │
          │                      │
          └──────────────────────┘
```

真正让这个循环不断前进的，不只是模型“继续生成”。

而是：

> **每一轮都有新的现实反馈进入下一轮。**

这就是这一 Macro 标题里：

> **Agent loop 真正循环的不是“思考”，而是现实反馈。**

想表达的东西。

---

#### 一个非常实用的判断标准

以后看到一个所谓 Agent 系统，我觉得可以先不看它用了：

```text
ReAct
Plan-and-Execute
Reflection
Multi-Agent
Graph
```

先问三个更基础的问题：

```text
1. 模型的动作提议在哪里变成真实副作用？

2. 执行结果在哪里重新进入模型状态？

3. 如果执行失败，失败是否同样作为 observation 返回？
```

如果三件事说不清楚：

```text
LLM → Tool → LLM
```

很可能只是架构图画得像 Agent。

真正 Harness Engineering 的难题，恰恰藏在两个箭头里。

---

#### 源码与证据边界

从 Claude Code v2.1.88 的恢复源码，我们可以直接确认：

1. `query()` 内部有一个维护跨 iteration state 的 `queryLoop()`，而不是“一次用户消息 = 一次模型请求”。
2. 模型产生 Tool Calls 后，`query.ts` 会把它们交给 streaming executor 或 `runTools(...)` 继续执行。
3. `runTools()` 最终通过 `runToolUse(...)` 进入真实工具执行路径。
4. 即使工具无法正常执行，runtime 也会创建带原 `tool_use_id` 的错误 `tool_result`，让失败进入后续 trajectory。

这里目前**还没有展开**：

```text
一个 Tool 到底怎样定义？
输入怎样验证？
权限在哪里检查？
哪些 Tool 可以并发？
怎样描述 destructive effect？
```

因为这些已经属于下一 Macro 的问题。

这一 Beat 只证明了一件事：

```text
tool_use
≠
真实动作
```

中间必须存在 Harness。


现在我们已经知道：

```text
Claude 负责提出动作，
Harness 负责让动作发生。
```

于是下一个问题自然来了。

既然 Harness 真正掌握着：

```text
文件系统
Shell
网络
MCP
其他 Agent
```

那一个 Tool 显然不能只是：

```ts
function bash(command) {
  exec(command)
}
```

因为生产系统还必须回答：

```text
输入是否合法？
谁允许执行？
它会不会改状态？
能不能和别的 Tool 并发？
执行中怎样取消？
结果怎样回给模型？
```

