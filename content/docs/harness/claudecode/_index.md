---
title: "Claude Code：从源码快照理解 Harness"
weight: 1
---

这篇笔记的目标不是复述 Claude Code 的产品功能，而是准备面试时最容易被追问的部分：一个 Coding Agent 如何把模型的文本输出变成受权限控制、可恢复、可验证的真实工作流。

## 先记住版本边界

本页主要依据 `@anthropic-ai/claude-code@2.1.88` 的公开源码快照整理。它来自 2026 年 3 月的一次 npm source map 暴露，不是 Anthropic 官方开源仓库；当前 Claude Code 的发布版本已经更新很多，因此下面的文件名和实现细节只能作为架构学习材料，不能当作当前产品行为的精确文档。

本地资料目录中有几种不同性质的内容：

| 目录 | 应该怎样理解 |
| --- | --- |
| `original-source-code` | 原始 TypeScript 快照，适合确认文件和符号是否真的存在 |
| `claude-code-source-code` | 整理、解包并附带分析文档的版本，适合阅读架构 |
| `claw-code`、`clawspring` 等 | 根据观察到的架构进行的重写，不是 Anthropic 原始实现 |

## 一分钟回答：Claude Code 的 Harness 是什么

可以这样回答：

> Claude Code 是一个运行在终端中的 Coding Agent。模型负责理解目标、规划下一步并选择工具；Harness 负责组装上下文、声明和校验工具、执行工具、处理权限、保存会话状态、压缩上下文、接收运行结果，并在失败后继续或交还给人。它把一次模型调用变成了一个可以在真实代码库里持续工作的闭环。

最重要的边界是：

```text
模型：下一步应该做什么？
Harness：允许做什么？怎样执行？结果是什么？是否真的完成？失败后如何恢复？
```

这比“给模型挂几个工具”更准确。工具解决的是动作空间，Harness 解决的是长期运行时的状态、控制、反馈和可靠性。

## 总体执行链路

在 v2.1.88 快照中，可以把主路径概括为：

```text
用户输入
  ↓
REPL / CLI 入口（main.tsx）
  ↓
会话级 QueryEngine.submitMessage()
  ↓
组装 system prompt、用户上下文、系统上下文、工具和 MCP
  ↓
query() / queryLoop()
  ↓
调用 Claude API 并流式读取 assistant message
  ↓
发现 tool_use
  ↓
校验参数 → 权限判断 → 执行工具 → 产生 tool_result
  ↓
把结果写回消息历史，继续下一轮模型调用
  ↓
最终回答 / 中断 / 达到预算或轮次上限
```

用伪代码表示就是：

```ts
while (true) {
  context = buildContext(messages, tools, permissions, memory)
  assistant = await model.stream(context)

  if (!assistant.containsToolUse()) return assistant.finalText

  calls = assistant.toolUses()
  results = await runToolsInParallelWhenSafe(calls)
  messages.push(assistant, ...results)

  if (needsCompaction(messages)) messages = compact(messages)
  if (aborted || maxTurnsReached || budgetExceeded) return
}
```

这里的关键不是 `while` 本身，而是每一轮都把“模型的意图”转换成“受控的外部动作”，再把真实结果反馈给模型。模型不能因为自己说“已经完成”就绕过工具执行和验证。

## 源码阅读地图

阅读时建议按下面的顺序，而不是从 1,884 个文件逐个浏览：

| 关注点 | 快照中的位置 | 面试要回答的问题 |
| --- | --- | --- |
| 入口与交互 | `src/main.tsx`、`src/replLauncher.tsx` | 用户输入如何进入 Agent？ |
| 会话生命周期 | `src/QueryEngine.ts` | 多轮消息、文件状态、用量和中断由谁持有？ |
| 核心循环 | `src/query.ts` | 何时调用模型、何时执行工具、何时继续？ |
| 工具契约 | `src/Tool.ts`、`src/tools.ts` | 工具怎样描述、校验、授权和返回结果？ |
| 工具编排 | `src/services/tools/toolOrchestration.ts` | 多个 tool call 如何调度和合并结果？ |
| 上下文 | `src/context.ts`、`src/utils/queryContext.ts` | 哪些信息进入 system prompt？ |
| 压缩与恢复 | `src/services/compact/`、`src/services/contextCollapse/` | 历史过长时如何继续工作？ |
| 权限 | `src/utils/permissions/`、`src/hooks/toolPermission/` | 如何控制文件、Shell、网络等高风险动作？ |
| 子 Agent | `src/tools/AgentTool/`、`src/coordinator/` | 如何隔离上下文并协调多个 Agent？ |
| 外部工具 | `src/services/mcp/` | MCP 如何进入工具集合？ |
| SDK / 远程 | `src/cli/structuredIO.ts`、`src/bridge/` | 同一核心如何服务 REPL、SDK 和远程 UI？ |

## 1. QueryEngine 与 query loop 的分工

这是一个很适合面试展开的设计：

- `QueryEngine` 是会话级对象，持有消息历史、文件读取缓存、累计用量、权限拒绝记录、AbortController 等跨轮状态。
- `query()` / `queryLoop()` 是一次 turn 内部的执行循环，负责调用模型、处理流式事件、执行 tool use、把 tool result 接回消息历史，以及触发压缩和恢复。
- `submitMessage()` 把两者连接起来：同一个 QueryEngine 可以连续接收多个用户消息，同时保留会话状态。

这样做的好处是把“会话状态”和“单轮控制流”分开。REPL、headless SDK 和远程桥接可以复用同一个查询核心，只替换输入输出适配器。

### 面试追问：为什么不把所有逻辑写在一个 `agent()` 函数里？

因为真实 Agent 同时面对流式输出、权限等待、工具并发、用户中断、重试、上下文压缩和多种调用入口。把会话状态、查询循环、工具执行和 UI 适配拆开，才能独立测试，也能避免 REPL 的状态污染 SDK 或子 Agent。

## 2. Tool contract：模型不能直接执行任意函数

一个可靠工具至少需要这些边界：

```text
name / description
  ↓
input schema
  ↓
validateInput(input)
  ↓
checkPermissions(input, context)
  ↓
call(input, toolUseContext)
  ↓
tool result + progress + error
```

源码中的 `Tool` 类型把工具定义、输入校验、权限检查、执行上下文和结果类型放在了同一份契约里。工具上下文还会携带当前工作目录、模型、MCP 客户端、AbortController、文件状态缓存、应用状态和子 Agent 信息。

面试时要强调两点：

1. Schema 校验是系统边界，不是给模型看的装饰。非法输入应该在进入内部实现前被拒绝。
2. 工具结果必须回到消息历史，形成 `assistant: tool_use → user: tool_result` 的闭环；只在终端打印结果而不回传，模型就无法基于真实结果继续推理。

### 为什么工具执行可以并行？

同一轮中彼此独立的只读操作，例如读取多个文件或搜索多个目录，可以并行降低延迟；会修改共享状态的操作必须串行或显式协调，否则会产生竞态、覆盖和难以解释的中间状态。并行的判断应该由工具的副作用和依赖关系决定，而不是简单地把所有 Promise 都 `Promise.all`。

## 3. 上下文工程：模型看到什么，决定它能做什么

Claude Code 的上下文不是只有用户最后一句话，通常包括：

- system prompt 和当前模型能力说明；
- 用户输入、历史 assistant/tool messages 和工具结果；
- 当前工作目录、项目说明文件、用户/项目级记忆；
- 工具定义、权限规则、额外工作目录和 MCP 能力；
- 当前任务、子 Agent、错误信息、用量和运行状态。

因此，“模型能力不够”并不是所有失败的第一解释。Agent 找不到文档、看不到运行时错误、没有访问权限、拿不到正确工具或上下文已被压缩掉，都可能表现成模型能力问题。

### 自动压缩不只是截断字符串

当历史接近上下文上限时，Harness 需要在保持可继续工作的前提下减少输入：

1. 识别当前 token 和输出预算；
2. 保留最近、正在进行或对下一步最重要的消息；
3. 总结较早的目标、决策、改动、失败和待办；
4. 保持 tool use 与 tool result 的结构配对；
5. 把压缩事件和新上下文继续交给模型。

要区分两种策略：

- **Compaction**：在原会话中总结历史，保留连续性，但可能保留错误假设。
- **Context reset**：创建一个干净上下文，通过 handoff artifact 交接状态，恢复成本更高，但能摆脱长上下文中的噪声和“快到上限了，赶紧收尾”的倾向。

面试回答可以是：先用压缩控制普通上下文增长；如果任务长到历史本身已经影响判断，就用结构化交接做 reset，并把目标、已完成工作、未完成工作、已知失败和下一步写入持久化 artifact。

## 4. 权限和安全：把模型的“想做”与系统的“能做”分开

Claude Code 快照中的权限体系不是一个简单的布尔开关，而是多个维度共同决定：

- 工具类型：读文件、写文件、执行 Shell、访问网络、调用 MCP；
- 参数和目标路径：同一个工具对不同目录可能有不同结果；
- 当前模式：默认询问、计划模式、接受编辑、绕过权限等；
- allow / deny / ask 规则及其持久化；
- 当前工作目录、额外工作目录和 sandbox / 网络权限；
- 用户交互是否存在，例如后台子 Agent 不能弹出对话框时应如何处理。

一个安全的调用顺序应该是：

```text
解析参数
  → Schema 校验
  → 路径 / 命令归一化
  → 权限规则匹配
  → 必要时询问用户
  → 最小权限执行
  → 记录决定和结果
```

这里有一个很好的面试观点：权限检查必须发生在执行前，而且要针对“具体参数”检查，不能只按工具名称授权。`Bash` 工具本身不等于所有 Shell 命令都安全；`Write` 工具本身也不等于可以写任意路径。

## 5. 子 Agent 和多 Agent 协调

源码快照中可以看到 `AgentTool`、Agent definition、coordinator、task 和 scratchpad 等结构。它们解决的不是“让模型更聪明”，而是三个工程问题：

- **上下文隔离**：研究、实现和审查不必共享全部历史；
- **任务并行**：互不依赖的调查可以同时进行；
- **职责分离**：一个 Agent 生成结果，另一个 Agent 以更怀疑的视角验证结果。

典型流程是：主 Agent 拆分任务 → 子 Agent 获得受限上下文和权限 → 子 Agent 执行并返回结构化结果 → 主 Agent 汇总、处理冲突并决定是否继续。

但多 Agent 不是默认更好：它会增加 token、调度、同步和冲突成本。共享文件时还会遇到覆盖、锁、worktree、权限继承和结果合并问题。任务很小或依赖很强时，单 Agent 往往更简单、更可靠。

### 面试追问：子 Agent 为什么不能无限递归？

因为递归会同时放大成本、上下文复杂度和权限风险。系统应设置深度和轮次上限，限制子 Agent 可用工具，明确父子任务边界，并把子 Agent 的结果作为结构化消息返回，而不是把所有内部过程无条件复制到父上下文。

## 6. MCP 和多种运行入口

MCP 可以看作外部能力的标准接入层：远程 MCP server 提供工具、资源或提示，Claude Code 在会话初始化和运行过程中把它们纳入工具/上下文体系。

面试时不要只说“MCP 是工具协议”，还要补上 Harness 视角：

- server 连接失败不能让整个会话无提示地卡死；
- 动态工具列表变化会影响 system prompt 和缓存；
- MCP 工具同样需要输入校验、权限、超时、取消和错误回传；
- 外部服务的权限不能因为接入了 MCP 就自动继承本地权限。

同一个核心查询引擎还可以被不同入口复用：

```text
REPL：人类友好的终端交互
SDK / print：结构化、可编程的事件流
Bridge / remote：远程消息和权限响应
子 Agent：受限上下文中的嵌套查询
```

这体现了一个重要设计：核心 Agent loop 不应该依赖某个具体 UI。

## 7. 可恢复性、可观测性和“完成”的定义

长任务不能只靠最终的一段自然语言总结判断成功。至少需要记录：

- 当前 turn、tool call、tool result 和错误；
- token、费用、延迟、重试和中断原因；
- 权限请求、用户决定和被拒绝的动作；
- 会话 transcript、压缩边界和子 Agent 关系；
- 测试、构建、运行时和真实用户路径的验证结果。

失败处理可以按类别区分：

| 失败类型 | 处理方式 |
| --- | --- |
| 输入不合法 | 修正或拒绝，不应盲目重试 |
| 权限被拒绝 | 询问用户、换方案或终止 |
| 临时网络 / 服务错误 | 有上限、有退避地重试 |
| 工具执行失败 | 把真实 stderr / 结构化错误返回模型 |
| 结果不符合验收标准 | 继续修改并重新验证 |
| 超过轮次、费用或时间预算 | 保存状态并交还给人 |

因此，“完成”不应等于模型说完成，而应等于验收条件被可重复地验证。例如代码任务至少要考虑编译、测试、静态检查、运行时路径、Diff 和副作用；UI 任务还要通过真实浏览器交互验证，而不是只看 DOM 或截图。

## 高频面试题与答题要点

### 1. Harness 和 Agent 有什么区别？

Agent 是围绕目标进行观察、决策和行动的系统，通常包含模型、提示、工具和循环。Harness 更强调包住模型的运行环境：上下文、状态、权限、执行、反馈、恢复和验收。两者在不同文章中的边界可能不同，面试时先说明自己的口径，再解释具体组件。

### 2. 为什么不能只调用一次 LLM？

因为一次调用只能产生计划或动作意图，不能可靠地完成文件修改、命令执行和结果确认。工具循环让模型看到真实的工具结果，并根据结果决定下一步；权限和预算则防止循环无限执行。

### 3. 如何避免上下文窗口爆炸？

控制每轮输出、压缩旧历史、保留结构化任务状态、减少重复工具结果，并在长任务中用 artifact 做跨会话交接。压缩不能破坏 tool call/result 配对，也不能丢掉下一步所需的约束和失败信息。

### 4. 如何避免 Agent 执行危险命令？

工具参数先做 Schema 和语义校验，再通过 allow / deny / ask 规则和当前权限模式作决定；高风险动作要求用户确认或放进更小的 sandbox。权限应针对具体命令、路径和参数，而不是只针对 `Bash` 这个工具名。

### 5. 如何判断模型真的修好了 Bug？

把自然语言需求转换成可观察的验收条件，让 Agent 运行测试、构建、静态检查或真实用户路径，并读取日志、指标和 trace。修改代码只是中间动作，验证结果才是完成信号；无法观测的验收标准不能要求 Agent 自己可靠判断。

### 6. 为什么要有 evaluator / verifier？

生成者容易对自己的结果过于宽容。独立验证者可以使用不同上下文和更严格的标准，执行真实路径后返回具体失败证据。不过 verifier 也需要校准、预算和反作弊约束，不能把“另一个 LLM 说通过”当成真相。

### 7. 什么时候并行，什么时候串行？

无共享状态、无依赖的只读任务适合并行；写同一资源、依赖前一步结果或需要统一顺序的任务必须串行或显式协调。并行带来的延迟收益要和竞态、成本、限流及结果合并复杂度一起评估。

### 8. Compaction 和 Context Reset 怎么选？

Compaction 成本低且保留连续性，适合正常的上下文增长；Reset 用新的上下文加结构化 handoff，适合历史噪声已经影响推理、或模型在长任务末尾出现提前收尾的情况。Reset 的代价是交接信息可能不完整，并且会增加编排和 token 成本。

### 9. 多 Agent 一定比单 Agent 好吗？

不一定。多 Agent 适合任务可以拆分、需要独立视角或需要并行探索的场景；强依赖、小任务和共享状态复杂的场景，单 Agent 更简单。评价标准应是端到端成功率、延迟、成本和可恢复性，而不是 Agent 数量。

### 10. 这份源码能代表现在的 Claude Code 吗？

不能。它代表一次公开暴露的 `v2.1.88` 快照，适合学习生产级 Coding Agent 的架构思想；当前版本、feature flag、服务端能力、权限规则和产品行为都可能已经变化。回答时应把“源码中确认的事实”和“基于架构的推断”分开。

## 和 Harness 总页的关系

你在上一级页面总结的五个动作——**找到、行动、观察、约束、修正**——可以直接映射到 Claude Code：

| Harness 动作 | Claude Code 中的对应物 |
| --- | --- |
| 找到 | 上下文、项目说明、记忆、Glob/Grep、MCP resources |
| 行动 | FileRead / Edit / Write、Bash、MCP tools、AgentTool |
| 观察 | tool result、终端输出、测试、日志、浏览器和 SDK events |
| 约束 | Tool schema、权限规则、sandbox、预算、轮次和工作目录 |
| 修正 | 继续 query loop、重试、重新压缩、回滚或交还人工 |

一句话总结：

> Claude Code 的价值不只是“会写代码”，而是把模型放进一个能找到信息、执行动作、看到真实反馈、受到边界约束并在失败后继续修正的运行环境。

## 延伸阅读

- [Anthropic：Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [Anthropic：Building effective human-agent teams](https://claude.com/blog/building-effective-human-agent-teams)
- [源码合集：collection-claude-code-source-code](https://github.com/chauncygu/collection-claude-code-source-code)
- [源码快照中的 `query.ts`](https://github.com/chauncygu/collection-claude-code-source-code/blob/main/claude-code-source-code/src/query.ts)
- [源码快照中的 `QueryEngine.ts`](https://github.com/chauncygu/collection-claude-code-source-code/blob/main/claude-code-source-code/src/QueryEngine.ts)
- [源码快照中的 `Tool.ts`](https://github.com/chauncygu/collection-claude-code-source-code/blob/main/claude-code-source-code/src/Tool.ts)
