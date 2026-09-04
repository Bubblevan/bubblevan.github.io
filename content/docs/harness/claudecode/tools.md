---
title: "Claude Code Tools：Tool Contract、ToolUseContext 与并发调度"
weight: 2
---

## 3. Tool 不只是函数，而是 Harness 的执行边界

### 3.1 一个生产工具到底比普通函数多了什么？


上一节已经把 Agent loop 拆成了：

```text
Model
  ↓ propose
tool_use
  ↓
Harness
  ↓ execute
Environment
  ↓
tool_result
  ↓
Model
```

于是现在有一个看似很简单的问题：

> Harness 收到 `tool_use` 以后，到底需要什么，才能安全地把它变成真实动作？

最朴素的实现大概是：

```ts
const tools = {
  Read: readFile,
  Bash: runCommand,
  Edit: editFile,
}

const fn = tools[toolUse.name]
const result = await fn(toolUse.input)
```

对于一个几十行的 ReAct demo，这已经够了。

但如果这个 Agent 真的拥有我的：

```text
文件系统
Shell
Git 仓库
网络
MCP Server
其他 Agent
```

那么问题很快就不是：

> “这个函数怎么调用？”

而变成：

```text
输入长什么样？
输入是否合法？
当前环境允许执行吗？
需要问用户吗？
这个动作会写状态吗？
会不会造成不可逆副作用？
能不能和其他 Tool 并发？
执行到一半能不能取消？
结果如何重新交给模型？
结果太大怎么办？
用户界面又应该显示什么？
```

Claude Code v2.1.88 的 `Tool.ts` 很能说明这个变化。

里面的 `Tool` 根本不像一个普通函数。

它更像一份 **runtime contract**。


* **Tool contract**：Tool 不只是可调用函数，而是 Harness 对一类外部动作的完整声明，包括输入结构、执行能力、权限接口、副作用属性、调度属性、取消行为以及结果如何重新映射回模型。

---

#### 如果 Tool 只是函数，我们实际上缺了什么？

先从一个最简单的 Bash 函数开始：

```ts
async function bash(command: string) {
  return exec(command)
}
```

它能跑。

但调用者除了知道：

```text
给 string
→
得到 result
```

以外，几乎什么都不知道。

比如：

```text
bash("pwd")
```

和：

```text
bash("rm -rf build/")
```

从 TypeScript 函数签名看，完全一样：

```text
string → result
```

可它们对 Harness 来说根本不是同一种动作。

前者可能只是观察环境。

后者会改变环境。

再比如：

```text
bash("git status")
```

和：

```text
bash("git push --force")
```

也都只是一个字符串。

于是普通函数签名丢掉了一大堆 Agent runtime 真正关心的信息：

```text
function signature
    │
    ├── 输入类型
    └── 输出类型

但 Harness 还需要
    │
    ├── 输入语义
    ├── 当前是否可用
    ├── 是否只读
    ├── 是否 destructive
    ├── 是否 concurrency-safe
    ├── 是否需要 permission
    ├── 是否允许 interrupt
    ├── 如何描述给模型
    └── 如何把结果送回模型
```

这就是为什么 Tool 一旦进入生产 Agent，就会从“函数”膨胀成“协议”。

---

#### Claude Code 的 `Tool` 首先有一层 Schema

在 `Tool.ts` 中，Tool 至少要求：

```ts
readonly inputSchema: Input
```

还可以提供：

```ts
readonly inputJSONSchema?: ToolInputJSONSchema
outputSchema?: z.ZodType<unknown>
```

这意味着 Model 不能随便生成一句：

```text
帮我读这个文件
```

然后 Harness 自己猜参数。

Tool Call 应该落到某个结构化空间里，例如：

```json
{
  "file_path": "/src/auth.ts",
  "offset": 1,
  "limit": 200
}
```

这个变化非常重要，因为 Harness 开始拥有一个明确边界：

```text
自然语言意图
      ↓
structured tool input
      ↓
schema validation
      ↓
runtime
```

模型负责生成。

Schema 负责回答：

> **这个输入至少在结构上是不是我认识的东西？**

例如：

```text
Read(
  file_path = 123
)
```

就不应该一路跑进文件系统以后才发现：

```text
TypeError
```

而应该在 Tool boundary 尽早被拒绝。

所以 Tool Schema 并不仅仅是为了“让 API 支持 function calling”。

它还在缩小：

```text
模型可以生成的开放语言空间
```

与：

```text
系统愿意执行的动作空间
```

之间的距离。

---

#### 但 Schema 合法，不等于动作合法

这是第二个很关键的区别。

假设 Bash Schema 只要求：

```json
{
  "command": "string"
}
```

那么：

```text
"ls"
```

当然合法。

但：

```text
"rm -rf /tmp/project"
```

从 Schema 看也完全合法。

甚至：

```text
"curl ... | sh"
```

依然是合法字符串。

所以：

```text
schema validation
```

只能证明：

> 参数长得对。

它不能证明：

> 这个动作应该执行。

因此 Claude Code 的 Tool contract 又单独保留了：

```ts
validateInput?(
  input,
  context,
): Promise<ValidationResult>
```

源码对此的说明很直接：它用于判断当前 context 下，这个输入是否允许运行，并把失败原因反馈给模型。

这就形成了两个完全不同的检查层：

```text
inputSchema
    ↓
“它长得像合法输入吗？”

validateInput
    ↓
“以当前语义和环境，
  这个输入可以运行吗？”
```

举个抽象例子：

```text
Read("/workspace/foo.ts")
```

Schema 合法。

但如果当前系统只允许：

```text
/workspace/project/
```

内部的路径，那么：

```text
/workspace/foo.ts
```

仍然可能被 runtime 拒绝。

或者 Edit 的：

```text
old_string
```

根本不存在。

它的参数类型没有任何问题，但作为一次具体修改却无法成立。

所以：

> **类型正确和动作成立，是两回事。**

这其实是 Agent Tool 设计里很容易被忽略的一层。

---

#### 然后还有第三层：能运行，不代表不需要用户批准

`Tool.ts` 又继续定义：

```ts
checkPermissions(
  input,
  context,
): Promise<PermissionResult>
```

而且源码专门注明：

> `checkPermissions()` 只在 `validateInput()` 通过以后调用；通用权限逻辑位于 permission system 中，这里承载 Tool-specific logic。

于是：

```text
invalid
```

和：

```text
not permitted
```

又不能混成一件事。

比如：

```text
Bash("git status")
```

可能：

```text
输入合法
语义合法
允许直接执行
```

而：

```text
Bash("git push origin main")
```

可能：

```text
输入合法
语义合法
但是需要用户确认
```

再比如：

```text
Edit("/etc/passwd", ...)
```

可能更早就在：

```text
validateInput / general permission policy
```

附近被拦掉。

这三个判断回答的是三个不同问题：

```text
Schema
  ↓
你说的话格式对吗？

Validation
  ↓
这个动作在当前 runtime 中成立吗？

Permission
  ↓
即使成立，你现在被授权做吗？
```

如果把它们全部塞进：

```ts
function call()
```

内部，系统当然也能工作。

但 Harness 就失去了一个统一的执行边界。

---

#### 我觉得这里最重要的是：Tool 把“能力”和“授权”分开了

Agent 系统里非常危险的一种思维是：

```text
模型拥有 Bash Tool
=
模型可以执行任何 Bash
```

实际上二者应该是：

```text
Capability
    ≠
Authorization
```

Tool 列表回答：

> **系统具备什么能力？**

Permission system 回答：

> **这次具体调用允许使用多少能力？**

所以一个 Tool 可以存在于模型的 action space：

```text
Bash
```

但某一次具体：

```text
Bash("some command")
```

依旧可以：

```text
allow
deny
ask user
```

这也是为什么 `ToolUseContext` 里会携带完整的：

```text
ToolPermissionContext
additionalWorkingDirectories
alwaysAllowRules
alwaysDenyRules
alwaysAskRules
permission mode
...
```

Claude Code 甚至区分了 bypass availability、自动模式、无法展示 prompt 的后台 Agent 等场景。

这一部分我们留到 Macro 4 再详细拆。

现在只需要先建立一个认识：

> **Tool contract 并不因为 Tool 已经暴露给模型，就默认这次 Tool Call 可以执行。**

---

#### Tool 还必须声明自己的副作用

接下来这几个方法，我觉得特别能体现 Harness Engineering：

```ts
isConcurrencySafe(input): boolean

isReadOnly(input): boolean

isDestructive?(input): boolean
```

注意它们都不是单纯问：

```text
这个 Tool 是什么类型？
```

其中至少 `isConcurrencySafe`、`isReadOnly`、`isDestructive` 都可以接收**具体 input**。

也就是说，副作用属性可以是：

```text
parameter-aware
```

而不是：

```text
Tool-name-aware
```

这非常重要。

比如 Bash 不能简单标成：

```text
Bash = write
```

因为：

```text
pwd
git status
grep foo bar.txt
```

可能都只是观察。

但也不能简单标成：

```text
Bash = read-only
```

因为：

```text
rm
mv
git commit
npm install
```

显然会改变环境。

所以 Harness 更关心的不是：

> “这是 Bash Tool 吗？”

而是：

> “这一次 Bash(input) 会产生什么 effect？”

抽象一下：

```text
Tool identity
     +
Concrete input
     +
Current context
     ↓
Effect classification
```

这比给 Tool 打一个静态标签要精细得多。

---

#### `isConcurrencySafe(input)` 为什么会出现在 Tool contract 里？

表面看，并发不是调度器该管的吗？

确实。

但调度器怎么知道两个动作能不能同时执行？

比如 Model 一次返回：

```text
Read(a.ts)
Read(b.ts)
Read(c.ts)
```

大概率可以并发。

但如果返回：

```text
Edit(a.ts)
Bash("npm test")
Edit(a.ts)
```

直接：

```ts
Promise.all(...)
```

就可能出问题。

所以 Tool contract 必须把某些调度所需的**语义信息**暴露给 Harness：

```text
Tool
  ↓ declares
isConcurrencySafe(input)
  ↓
Scheduler
  ↓ decides
parallel / serial
```

这说明：

> Tool 不只负责“怎么执行自己”，还要向整个 Harness 描述“我对环境意味着什么”。

下一 Beat 我们会专门沿着这个字段进入 `toolOrchestration.ts`，看看 Claude Code 到底怎么避免：

```ts
Promise.all(toolCalls)
```

这种天真的实现。

现在暂时只记住：

```text
调度器不应该重新猜 Tool 的语义。
```

Tool contract 应该主动暴露它。

---

#### `interruptBehavior()` 又解决了另一个完全不同的问题

Claude Code 的 Tool 还可以定义：

```ts
interruptBehavior?(): 'cancel' | 'block'
```

源码给出的语义是：

```text
cancel
→ 用户在 Tool 运行时发送新消息，
  停止 Tool 并丢弃结果

block
→ Tool 继续运行，
  新消息等待
```

默认没有实现时采用 `block`。

这个字段很有意思，因为普通函数根本不需要考虑：

> “调用到一半，用户又发了一句话怎么办？”

但交互式 Agent 必须考虑。

假设 Claude 正在：

```text
Bash("pytest")
```

用户突然输入：

```text
别跑了，我发现问题不是这里。
```

此时 Harness 需要决定：

```text
终止 pytest？

还是让 pytest 完成以后
再处理用户新消息？
```

这已经不是 Model reasoning 问题。

它是：

```text
interactive runtime semantics
```

而 Tool contract 必须参与定义。

---

#### Tool 的 `call()` 其实反而只是其中一个字段

到了这里再看真正执行动作的方法：

```ts
call(
  args,
  context,
  canUseTool,
  parentMessage,
  onProgress?,
): Promise<ToolResult<Output>>
```

如果从普通函数思维来看：

```text
call()
```

应该是 Tool 最重要的东西。

但放到整个 `Tool` interface 里看，它反而只是 contract 的一部分。

它旁边还有：

```text
inputSchema
validateInput
checkPermissions

isConcurrencySafe
isReadOnly
isDestructive

interruptBehavior

description
prompt

mapToolResultToToolResultBlockParam

renderToolUseMessage
renderToolResultMessage
...
```

于是一个生产 Tool 的生命周期更接近：

```text
                 Model
                   │
                   ▼
              tool_use
                   │
                   ▼
          ┌─────────────────┐
          │   Tool contract │
          ├─────────────────┤
          │ schema          │
          │ validation      │
          │ permissions     │
          │ effect metadata │
          │ scheduling info │
          │ interrupt rules │
          └────────┬────────┘
                   │
                   ▼
                 call()
                   │
                   ▼
              Environment
                   │
                   ▼
              ToolResult
                   │
                   ▼
        model-facing serialization
                   │
                   ▼
                Model
```

这比：

```text
name → function
```

已经不是同一个抽象层次了。

---

#### `ToolResult` 也不是随便返回一个字符串

`Tool.ts` 定义：

```ts
export type ToolResult<T> = {
  data: T
  newMessages?: (...)
  contextModifier?: (
    context: ToolUseContext
  ) => ToolUseContext
  mcpMeta?: ...
}
```

首先有：

```text
data
```

也就是 Tool 真正产生的数据。

但 Tool 还可以产生：

```text
newMessages
```

甚至：

```text
contextModifier
```

也就是说，一次 Tool execution 不一定只是：

```text
input → output string
```

它还可能：

```text
修改后续 runtime context
附加新的 message
携带 MCP metadata
```

这就进一步说明 Tool 是 runtime participant，而不是纯函数。

---

#### 最终给模型看的结果，也不是 `JSON.stringify(result)`

`Tool` contract 还有一个我非常喜欢的边界：

```ts
mapToolResultToToolResultBlockParam(
  content,
  toolUseID,
): ToolResultBlockParam
```

为什么需要这一层？

因为：

```text
Tool 内部返回的数据结构
```

和：

```text
应该送回模型 context 的内容
```

不一定相同。

例如一个 Tool 内部可能得到：

```text
几十 MB 日志
大量 metadata
UI 状态
完整响应对象
```

模型未必需要全部看到。

于是：

```text
Environment result
        ↓
Tool internal Output
        ↓
mapToolResult...
        ↓
Model-facing tool_result
```

这又和 Macro 1 形成了一个呼应：

> Harness 的工作经常不是“有没有状态”，而是“当前模型应该看到状态的哪一部分”。

---

#### 甚至 UI 和模型看到的结果都不一定一样

`Tool` 里还有：

```text
renderToolUseMessage
renderToolResultMessage
renderToolUseProgressMessage
renderToolUseErrorMessage
...
```

这看起来像前端细节，可以跳过。

但里面隐藏着一个挺重要的结构：

```text
同一次 Tool execution
        │
        ├── model-facing representation
        │
        └── human-facing representation
```

两者不必完全相同。

比如 Bash 返回一万行日志。

模型侧可能需要：

```text
经过预算约束后的工具结果
```

用户侧可能更适合：

```text
折叠显示
可展开
带进度
带错误样式
```

所以生产 Harness 同时在服务两个 observer：

```text
Model
Human
```

这也是为什么 Agent CLI 的 Tool abstraction 会比普通后端函数复杂得多。

---

#### 一个 Tool 实际上同时服务四个系统

看到这里，我觉得可以把 Claude Code 的 Tool contract 压成四个方向：

```text
                    Tool
                     │
       ┌─────────────┼─────────────┐
       │             │             │
       ▼             ▼             ▼
     Model        Runtime        Human
       │             │             │
 schema/prompt   execution     rendering
 description    permission     progress
 result format  scheduling     errors
                     │
                     ▼
                 Environment
```

换个更好记的说法：

| 面向谁         | Tool 必须回答什么          |
| ----------- | -------------------- |
| Model       | 我是什么？参数怎么给？结果怎么返回？   |
| Harness     | 能不能执行？怎么调度？怎样中断？     |
| Environment | 真正执行什么副作用？           |
| Human       | 当前在做什么？要不要授权？结果怎样展示？ |

所以 `Tool` 才会看起来“臃肿”。

不是因为 Anthropic 不会抽象。

而是因为生产 Tool 本来就在几个边界的交叉点上。

---

#### 一个我觉得很适合面试的例子：为什么不能只有 `execute()`？

如果面试官问：

> 一个 Agent Tool 为什么要设计这么复杂？定义一个 `execute(input)` 不好吗？

可以先回答：

`execute()` 只能描述能力本身，却无法让 runtime 在执行前理解这个动作。

假设：

```ts
interface Tool {
  execute(input: unknown): Promise<unknown>
}
```

那么调度器拿到一个 Tool Call 时，只知道：

```text
“这里有个函数可以运行。”
```

它不知道：

```text
输入是否合法？

是否允许？

是不是只读？

是不是 destructive？

能不能和旁边那个调用并发？

用户发新消息时应该 cancel 还是 block？
```

结果就是每个上层模块都必须：

```text
重新识别 Tool name
重新解析 input
重新猜 Tool effect
```

最终会出现：

```ts
if (tool.name === "Bash") ...
if (tool.name === "Read") ...
if (tool.name === "Edit") ...
```

散落在整个代码库。

更合理的是让 Tool 自己声明：

```text
what I can do
what this input means
what effect I may cause
how I may be scheduled
how my result should be exposed
```

Harness 再围绕统一 contract 编排。

所以这不是单纯的 OO 封装问题。

它真正解决的是：

> **把动作语义从具体执行代码里提取出来，使权限、调度、恢复、UI 和模型接口都能共享。**

---

#### `buildTool()` 的默认值还能看到 Claude Code 的保守策略

`Tool.ts` 最后还有一个 `buildTool()`。

它会为没有显式实现的字段填默认值。

里面最值得注意的是：

```ts
isEnabled: () => true

isConcurrencySafe: () => false

isReadOnly: () => false

isDestructive: () => false
```

以及 Tool-specific `checkPermissions` 默认返回 allow，把决策交给通用 permission system。

这里要特别小心，不要写成：

> Claude Code 的所有 Tool 权限默认 fail-closed。

**源码不支持这个说法。**

它真正保守的地方主要体现在：

```text
不知道能不能并发
→ 当作不能并发

不知道是不是只读
→ 当作会写
```

但：

```text
tool-specific checkPermissions
```

默认并不是 deny。

源码明确写的是：

```text
allow + updatedInput
→ defer to general permission system
```

这也是一个很好的阅读源码教训：

```text
“看起来安全”
```

不能自动脑补成：

```text
“所有安全判断默认拒绝”
```

不同字段的默认策略是不同的。

---

#### 为什么 `isDestructive` 默认又是 `false`？

乍看这里好像和：

```text
isReadOnly → false
```

矛盾。

如果不知道一个 Tool 是不是只读，就认为它会写。

那为什么不知道是否 destructive 时，不默认 destructive？

因为这两个概念并不相同：

```text
not read-only
≠
destructive
```

例如：

```text
创建一个新文件
```

不是 read-only。

但未必属于：

```text
irreversible delete / overwrite / send
```

这种 destructive operation。

源码注释也明确把 `isDestructive` 留给 delete、overwrite、send 这类不可逆行为。

于是：

```text
Read-only?
```

和：

```text
Destructive?
```

实际上是两条不同的 effect dimension。

这个设计比简单：

```text
safe / dangerous
```

二分类更接近真实世界。

---

#### 所以 Tool contract 本质上是在描述“Effect”

把所有字段放在一起以后，我觉得最有用的理解不是：

> Claude Code 的 Tool interface 很复杂。

而是：

> **Harness 必须知道一个动作对系统意味着什么，才能在模型和真实环境之间安全地做中介。**

普通函数更关注：

```text
input → output
```

Agent Tool 还必须关注：

```text
input
  ↓
valid?
  ↓
permitted?
  ↓
what effects?
  ↓
parallelizable?
  ↓
interruptible?
  ↓
execute
  ↓
runtime changes
  ↓
model-facing observation
```

所以从 Harness 的角度：

```text
Tool
≠
Function
```

更准确的是：

```text
Tool
=
Capability
+
Schema
+
Policy hooks
+
Effect metadata
+
Execution
+
Observation mapping
```

这不是一个严格公式。

但它已经比：

```text
Tool = function calling
```

接近得多。

---

#### 再接回父文的“行动”和“约束”

父文里我们把 Harness 写成：

```text
找到
行动
观察
约束
修正
```

上一 Macro 已经看到了：

```text
行动
→ Tool execution

观察
→ Tool result
```

这一 Beat 又补上：

```text
行动并不是裸执行。
```

中间还有：

```text
Schema
Validation
Permission
Effect classification
Scheduling metadata
Interrupt semantics
```

也就是说：

```text
              模型提出动作
                   │
                   ▼
               【约束】
        schema / validate / permission
                   │
                   ▼
               【行动】
               tool.call
                   │
                   ▼
              Environment
                   │
                   ▼
               【观察】
               tool_result
```

Harness 的：

```text
行动
```

和：

```text
约束
```

其实从一开始就是缠在一起的。

---

#### 源码与证据边界

从 Claude Code v2.1.88 的恢复源码，可以直接确认：

* `Tool` 定义了 `inputSchema`，并可提供 JSON Schema 和 output schema；
* Tool contract 包含 `validateInput()` 与 `checkPermissions()`，且源码明确说明 Tool-specific permission 检查发生在 validation 通过之后；
* Tool 可以依据具体输入声明 `isConcurrencySafe`、`isReadOnly`、`isDestructive`；
* Tool 可以定义 `interruptBehavior()`，区分运行中收到新用户消息时 cancel 或 block；
* Tool 的执行通过 `call()` 完成，并通过 `mapToolResultToToolResultBlockParam()` 把内部结果映射成模型可消费的 Tool Result；
* `ToolUseContext` 还携带 Tools、MCP、AbortController、文件状态、Agent 定义、消息、预算等执行上下文；
* `buildTool()` 默认认为未知 Tool **不具备并发安全性，也不假定只读**；但 Tool-specific `checkPermissions` 默认允许并交给通用 permission system，不能笼统描述为权限 fail-closed。


现在 Tool 已经不再是：

```text
一个可以调用的函数
```

而是：

```text
Harness 可以理解其 effect 的动作对象
```

这马上引出一个很具体的问题。

假设 Claude 一次生成三个 Tool Call：

```text
Read(a.ts)
Read(b.ts)
Bash("pytest")
```

最简单的实现当然是：

```ts
await Promise.all(toolCalls.map(run))
```

但如果变成：

```text
Edit(a.ts)
Bash("pytest")
Edit(a.ts)
```

事情马上就不对了。

于是下一 Beat 要直接进入 `toolOrchestration.ts`：


**为什么并发不是 `Promise.all(toolCalls)`？**

真正的问题不是：

> “Tool 能不能并发？”

而是：

> **这一组具体 Tool Call，在当前输入和 effect 下，哪些可以同时发生，哪些必须保持顺序？**

### 3.2 为什么并发不是 `Promise.all(toolCalls)`？


上一节我们已经把 Tool 从：

```text
name → function
```

升级成：

```text
Capability
+
Schema
+
Policy hooks
+
Effect metadata
+
Execution
+
Observation mapping
```

其中有一个字段当时只点了一下：

```ts
isConcurrencySafe(input): boolean
```

现在就来追它为什么存在。

假设模型一次返回：

```text
Read(a.ts)
Read(b.ts)
Read(c.ts)
```

最直觉的优化当然是：

```ts
await Promise.all([
  Read(a.ts),
  Read(b.ts),
  Read(c.ts),
])
```

三个文件一起读，明显比串行快。

但如果下一次模型返回的是：

```text
Edit(a.ts)
Bash("pytest")
Edit(a.ts)
```

还敢：

```ts
Promise.all(...)
```

吗？

显然不行。

因为三个动作之间已经可能存在真实的**顺序依赖**：

```text
先修改 a.ts
    ↓
测试看到修改后的状态
    ↓
根据结果再继续修改
```

如果全部同时启动：

```text
Edit #1 ───────┐
               │
pytest ────────┼──→ race
               │
Edit #2 ───────┘
```

测试到底读到哪个版本？

第二个 Edit 会不会覆盖第一个？

结果还具有原来的语义吗？

这就是这一 Beat 的新概念。


* **effect-aware scheduling**：Agent runtime 不能仅根据“模型一次返回了几个 Tool Call”决定并发，而必须根据每个具体动作对环境可能产生的 effect，决定哪些可以并行、哪些必须保序。

---

#### 多个 Tool Call 并不天然表示“可以同时做”

先从 LLM 视角看。

模型一次 assistant message 完全可能给出多个：

```text
tool_use
tool_use
tool_use
```

但模型表达的只是：

> “基于当前状态，我认为这些动作值得执行。”

它没有自动提供一个并发正确性证明。

假设：

```text
Tool A
Tool B
Tool C
```

摆在同一个 assistant response 里。

我们最多知道：

```text
它们都由同一轮模型提出
```

却不知道：

```text
A 和 B 是否互相影响？
B 是否依赖 A？
C 是否会修改 B 读取的状态？
```

所以：

```text
same model response
≠
independent operations
```

这和普通异步编程有点像。

你看到三个 Promise，不代表它们一定应该：

```ts
Promise.all(...)
```

并发正确性的前提始终是：

> **这些操作之间没有需要保留的因果顺序。**

---

#### Claude Code 先做的不是执行，而是 partition

`toolOrchestration.ts` 中的核心入口是：

```ts
export async function* runTools(
  toolUseMessages,
  assistantMessages,
  canUseTool,
  toolUseContext,
)
```

它没有直接：

```ts
yield* all(toolUseMessages.map(runToolUse))
```

而是先调用：

```ts
partitionToolCalls(
  toolUseMessages,
  currentContext,
)
```

然后逐个处理 partition 出来的 batch。

整体结构可以先压成：

```text
model returns N tool calls
          ↓
partitionToolCalls(...)
          ↓
┌────────────┬────────────┬────────────┐
│ batch 1    │ batch 2    │ batch 3    │
│ concurrent │ serial     │ concurrent │
└────────────┴────────────┴────────────┘
          ↓
按 batch 顺序执行
```

这里最值得注意的是：

> **并发是 batch 内部属性；batch 之间仍然保持顺序。**

也就是说 Claude Code 不是简单做：

```text
安全的都扔到一个全局并发池
不安全的另算
```

而是保留原始 Tool Call 序列中的边界。

---

#### `partitionToolCalls()` 判断的不是 Tool 名，而是具体 input

真正关键的代码在这里：

```ts
const tool = findToolByName(
  toolUseContext.options.tools,
  toolUse.name,
)

const parsedInput = tool?.inputSchema.safeParse(
  toolUse.input,
)

const isConcurrencySafe = parsedInput?.success
  ? (() => {
      try {
        return Boolean(
          tool?.isConcurrencySafe(parsedInput.data),
        )
      } catch {
        return false
      }
    })()
  : false
```

这个判断顺序很值得拆。

不是：

```text
Tool name
↓
查一个 static concurrent=true/false
```

而是：

```text
找到 Tool
    ↓
先 parse 具体 input
    ↓
把 parse 后的 input
交给 isConcurrencySafe(input)
    ↓
得到这一次调用
是否并发安全
```

也就是说：

```text
Concurrency safety
```

属于：

```text
Tool + concrete input
```

而不是单独属于：

```text
Tool class
```

这和上一 Beat 讲的 parameter-aware effect 完全接上了。

---

#### 为什么这比“Read 并发，Write 串行”更准确？

最简单的并发策略会写：

```text
Read Tool
→ concurrent

Edit Tool
→ serial

Bash Tool
→ serial
```

这种静态分类很容易理解。

但真实 Tool 没有这么整齐。

比如 Bash：

```text
pwd
```

```text
git status
```

```text
grep -R foo .
```

它们和：

```text
rm foo
```

```text
npm install
```

```text
git checkout other-branch
```

虽然都是同一个：

```text
Bash
```

但 effect 显然完全不同。

如果 Tool 自己能够分析 input，那么：

```text
Bash("git status")
```

和：

```text
Bash("git checkout foo")
```

就有机会返回不同的：

```text
isConcurrencySafe(...)
```

所以更理想的抽象不是：

```text
Tool A 安全
Tool B 不安全
```

而是：

```text
Invocation A(input₁)
是否安全？

Invocation A(input₂)
是否安全？
```

这就是 parameter-aware scheduling 的价值。

---

#### 这里源码注释甚至有一点“历史残留”

`toolOrchestration.ts` 的注释写的是类似：

```text
read-only batch concurrently
non-read-only batch serially
```

但真正执行判定的代码已经不是：

```ts
tool.isReadOnly(...)
```

而是：

```ts
tool.isConcurrencySafe(...)
```

这一点我觉得特别值得在博客里保留。

因为它提醒我们：

> **源码注释描述的概念模型，可能落后于当前实现。**

如果只读注释，我们会写：

```text
Claude Code：
Read-only → parallel
Write → serial
```

但真正读判断逻辑以后，更准确的是：

```text
Claude Code：
isConcurrencySafe(input) → parallel candidate
otherwise → serial
```

两者不是一回事。

因为：

```text
read-only
```

只是：

```text
concurrency-safe
```

的一种常见来源。

却不是严格等价关系。

---

#### `read-only` 和 `concurrency-safe` 为什么不能画等号？

先看一个简单例子。

某个动作可能：

```text
不修改文件
```

但仍然不适合并发。

比如它可能读取：

```text
一个会变化的 process state
一个共享 cursor
一个外部 rate-limited resource
一个需要顺序访问的 session
```

于是：

```text
read-only
```

不自动推出：

```text
concurrency-safe
```

反过来，也可能存在某些“写”操作彼此完全独立。

例如理论上：

```text
Write(file_a)
Write(file_b)
```

如果两个文件完全无关，并且 runtime 能证明没有其他共享状态，它们未必天然不能并发。

所以：

```text
isReadOnly
```

回答的是：

> 会不会修改状态？

而：

```text
isConcurrencySafe
```

回答的是：

> 和其他当前操作同时运行，会不会破坏预期语义？

这是两个不同维度：

```text
effect dimension #1
read / write

effect dimension #2
parallel-safe / order-sensitive
```

上一 Beat 中把它们拆成独立接口，就开始显出意义了。

---

#### 解析失败时为什么直接串行？

再看这句：

```ts
const isConcurrencySafe =
  parsedInput?.success
    ? ...
    : false
```

也就是说：

```text
inputSchema.safeParse(toolUse.input)
```

失败以后，runtime 不会说：

> “反正可能只是 schema 有一点小问题，先并发跑起来再说。”

而是：

```text
unknown input semantics
        ↓
cannot prove concurrency safety
        ↓
false
        ↓
serial path
```

这是一种很典型的保守调度原则：

> **不知道是否安全，就不要用更激进的调度。**

它和上一 Beat 的默认：

```text
isConcurrencySafe → false
```

完全一致。

这里所谓保守，不是：

```text
不知道就禁止 Tool 执行
```

而是：

```text
不知道就不给并发优化
```

这是很重要的区别。

---

#### 连 `isConcurrencySafe()` 自己出错，也退回串行

源码还专门包了一层：

```ts
try {
  return Boolean(
    tool?.isConcurrencySafe(parsedInput.data),
  )
} catch {
  return false
}
```

旁边的注释给的例子是：

```text
shell-quote parse failure
```

这其实很合理。

假设 Bash Tool 为了判断：

```text
git status
```

是否只读，需要解析 shell command。

但解析器遇到某个奇怪输入：

```text
foo "$(bar ..."
```

直接抛异常。

这时有两种策略：

```text
A:
分类失败
→ 那就默认可以并发

B:
分类失败
→ 无法证明安全
→ 串行
```

Claude Code 选择 B。

所以这里真正的安全逻辑是：

```text
Concurrency optimization
requires positive evidence
```

而不是：

```text
unless proven unsafe,
assume safe
```

这对执行真实副作用的 Agent 很合理。

---

#### partition 本身还保留了原始顺序

现在来看真正 batch 是怎么形成的：

```ts
if (
  isConcurrencySafe &&
  acc[acc.length - 1]?.isConcurrencySafe
) {
  acc[acc.length - 1]!.blocks.push(toolUse)
} else {
  acc.push({
    isConcurrencySafe,
    blocks: [toolUse],
  })
}
```

这段很短，但语义其实非常重要。

假设 Tool Calls 原始顺序是：

```text
A safe
B safe
C unsafe
D safe
E safe
F unsafe
```

不会被整理成：

```text
safe:
A B D E

unsafe:
C F
```

而是：

```text
Batch 1
A B
concurrent

Batch 2
C
serial

Batch 3
D E
concurrent

Batch 4
F
serial
```

也就是：

```text
[A B] → [C] → [D E] → [F]
```

这样 preserved order 的好处是：

```text
C
```

天然形成一道 execution barrier。

后面的：

```text
D E
```

不会越过 C 提前执行。

---

#### 为什么不能把所有 safe call 抽出来一起并发？

假设模型输出：

```text
Read(config)
Edit(config)
Read(config)
```

如果单纯按：

```text
safe
unsafe
safe
```

分类，然后把所有 safe 调用提前并发：

```text
Read #1 ──┐
Read #2 ──┴→ simultaneous
    ↓
Edit
```

第二次 Read 就读错了时间点。

模型原本的序列是：

```text
读取旧状态
    ↓
修改
    ↓
读取新状态
```

它表达了因果关系。

因此即使：

```text
Read #1
Read #2
```

单独看都是 concurrency-safe，

它们也不能跨过：

```text
Edit
```

被重新排序。

这就是：

```text
safe to overlap
```

和：

```text
safe to reorder
```

之间的区别。

Claude Code 的 partition 只允许：

> **相邻且都被判定为 concurrency-safe 的调用形成一个并发 batch。**

它没有因为追求 throughput 就重排整个 Tool sequence。

---

#### 这是一个很重要的调度原则：并发不等于重排

可以抽象成：

```text
原序列：

A → B → C → D → E

其中：
A safe
B safe
C unsafe
D safe
E safe

允许：

[A || B]
   ↓
   C
   ↓
[D || E]
```

但不允许：

```text
[A || B || D || E]
        ↓
        C
```

所以系统做的是：

```text
preserve happens-before boundaries
```

而不是：

```text
maximize parallelism at all costs
```

这个思路在长任务 Harness 里特别重要。

因为 Agent Tool 往往不是纯计算函数。

它们接触的是：

```text
filesystem
git repository
processes
browser
network
MCP server
shared runtime state
```

任何不恰当的重排都可能改变任务语义。

---

#### Safe batch 内部才真正并发

当 batch 被判定为 concurrency-safe 时：

```ts
runToolsConcurrently(
  blocks,
  assistantMessages,
  canUseTool,
  currentContext,
)
```

被调用。

源码最终使用一个 `all(...)` helper，并带最大并发度：

```ts
getMaxToolUseConcurrency()
```

默认值来自：

```text
CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY
```

没有配置时默认：

```text
10
```

所以 even safe batch 也不是：

```text
无限制地全部启动
```

而是：

```text
concurrency-safe
        ↓
仍受 max concurrency 限制
```

这一点也很工程化。

因为：

```text
safe to parallelize
```

只表示：

> 并发不会破坏语义。

不表示：

> 并发越多越好。

---

#### 为什么并发安全了还要限制为 10？

即使只是：

```text
Read
Read
Read
...
```

一次模型生成 100 个读取操作，如果同时全部启动，仍可能造成：

```text
文件句柄压力
磁盘竞争
MCP rate limit
network saturation
UI progress flood
memory pressure
```

所以调度还有两个维度：

```text
Correctness
    ↓
哪些可以并发？

Resource control
    ↓
最多同时跑多少？
```

前者由：

```text
isConcurrencySafe(input)
```

参与决定。

后者由：

```text
max concurrency
```

控制。

不能混为一谈。

---

#### Serial batch 又做了什么？

对于不安全 batch，Claude Code 进入：

```ts
runToolsSerially(...)
```

内部结构基本是：

```ts
for (const toolUse of toolUseMessages) {
  ...
  for await (
    const update of runToolUse(...)
  ) {
    ...
  }
}
```

也就是说：

```text
Tool A
执行完
    ↓
更新 context
    ↓
Tool B
执行完
    ↓
更新 context
```

这里有个值得注意的细节：

每次 `runToolUse()` 如果返回：

```text
contextModifier
```

serial path 会立即：

```text
currentContext =
  modifier(currentContext)
```

然后后面的 Tool 再拿到新的 context。

所以串行不只是：

```text
为了不抢文件锁
```

还可能是在保证：

> **前一个 Tool 对 runtime context 的修改，后一个 Tool 能看到。**

这让“顺序”不仅包含环境状态，也包含 Harness 自己的内部状态。

---

#### 并发 batch 的 context modifier 为什么不能立刻应用？

这部分更有意思。

并发 path 中，源码没有在某一个 Tool 一返回：

```text
contextModifier
```

时就立刻改 `currentContext`。

而是先把这些 modifier 暂存：

```ts
const queuedContextModifiers = {}
```

等整个 concurrent batch 执行过程结束后，再按照原始 block 顺序应用。

为什么？

因为假设：

```text
Tool A
Tool B
```

真正运行速度可能是：

```text
B 先返回
A 后返回
```

如果按 completion order 更新 context：

```text
B modifier
    ↓
A modifier
```

那么多跑几次以后，结果可能取决于：

```text
哪个 Tool 恰好先完成
```

这就把 runtime state 变成了 nondeterministic。

Claude Code 更接近：

```text
并发执行
    ↓
收集 modifier
    ↓
仍按照原始 Tool Call 顺序
应用 modifier
```

也就是说：

```text
execution
可以并发

state commit
仍然保序
```

这个区分非常漂亮。

---

#### 这其实有点像“并发执行，确定性提交”

可以画成：

```text
Model order:

A
B
C

Execution:

A ──────────────┐
B ───────┐      │
C ───────────┐  │
             │  │
完成顺序：
B → C → A
             │
             ▼

Context update:

A modifier
   ↓
B modifier
   ↓
C modifier
```

于是：

```text
wall-clock completion order
```

不会偷偷变成：

```text
semantic order
```

这对 Agent runtime 很重要。

否则同一个模型输出：

```text
A B C
```

两次运行可能因为机器负载不同得到不同 context。

这种 bug 最难排查。

---

#### `Promise.all(toolCalls)` 最大的问题其实不是 Promise

因此现在可以重新看标题：

> 为什么并发不是 `Promise.all(toolCalls)`？

问题当然不在 JavaScript 的 `Promise.all` 本身。

真正的问题是：

```text
Promise.all
```

默认假设：

```text
这些任务已经被上游证明
可以同时开始
```

但 Agent Tool Calls 并没有天然满足这个条件。

所以在：

```ts
Promise.all(...)
```

之前，Harness 必须先回答：

```text
哪些调用具有共享副作用？
哪些依赖前序状态？
哪些输入我甚至无法正确分类？
哪些 context update 必须保序？
并发规模应该多大？
```

因此真正复杂的是：

```text
Scheduling policy
```

不是：

```text
Async API
```

---

#### 我觉得可以把这里理解成一个简化版 effect system

虽然 Claude Code 没有真的实现一个编程语言意义上的 formal effect system，但从设计思路上很像：

```text
一个动作
不只是有：
Input
Output

还带着：
read?
write?
destructive?
parallel-safe?
permission?
interruptible?
```

Harness 再根据这些 effect metadata 做：

```text
validation
authorization
scheduling
rendering
recovery
```

所以 Tool contract 在某种程度上是在给：

```text
LLM-generated program
```

补上一套 runtime effect semantics。

这是我觉得很适合面试里往深处聊的一句话：

> Coding Agent 的 Tool Calls 可以看成模型动态生成的一小段程序，而 Harness 要做的事情之一，就是在真正执行前对这些动作进行 effect-aware validation、authorization 和 scheduling。

这比：

> “Claude Code 支持并发调用工具。”

信息量高很多。

---

#### 一个具体例子：模型一次返回四个调用

假设模型返回：

```text
1. Read(src/a.ts)
2. Read(src/b.ts)
3. Edit(src/a.ts)
4. Read(src/c.ts)
```

假设判断结果为：

```text
1 safe
2 safe
3 unsafe
4 safe
```

`partitionToolCalls()` 会形成：

```text
Batch 1
┌─────────────────────┐
│ Read(a) || Read(b)  │
└─────────────────────┘
          ↓
Batch 2
┌─────────────────────┐
│ Edit(a)             │
└─────────────────────┘
          ↓
Batch 3
┌─────────────────────┐
│ Read(c)             │
└─────────────────────┘
```

而不会变成：

```text
Read(a)
Read(b)
Read(c)
   ↓
一起并发
   ↓
Edit(a)
```

因为第四个 Read 在原始 sequence 中位于 Edit 后面。

这可能意味着模型就是想：

```text
先改完
再读取另一个文件
```

Harness 不应该擅自重写这层语义。

---

#### 如果分类器错了怎么办？

这里还有一个系统级边界。

`isConcurrencySafe(input)` 本身不是数学证明。

它是 Tool 实现者提供的一段逻辑。

所以理论上仍可能：

```text
误判 safe
        ↓
实际有共享 effect
        ↓
race condition
```

因此整个方案并没有神奇消灭并发风险。

它做的是把：

```text
并发决策
```

从：

```text
调度器靠 Tool name 猜
```

变成：

```text
Tool 实现者显式声明具体 input 的 effect
```

责任边界更清楚了。

这也意味着写一个新 Tool 时：

```text
isConcurrencySafe()
```

不是性能优化小细节。

它属于 correctness contract。

如果不确定，Claude Code 默认：

```text
false
```

反而是更合理的行为。

---

#### 这和数据库里的可串行化有点像，但别画等号

看到这里很容易联想到：

```text
transaction scheduling
serializability
conflict detection
```

这个类比是有帮助的：

```text
多个操作
    ↓
判断有没有冲突
    ↓
无冲突则重叠执行
有冲突则保持顺序
```

但不要写成：

> Claude Code 实现了数据库式 serializable scheduler。

源码没有支持这么强的结论。

它没有完整：

```text
read set
write set
transaction rollback
conflict graph
serializability proof
```

这里更准确的说法是：

> Claude Code 使用 Tool 提供的 concurrency-safety predicate，对相邻 Tool Calls 做保守分批，在不主动重排原始序列的前提下获得有限并发。

这就是我们真正能从源码确认的东西。

---

#### 所以 Harness 并发优化的顺序应该是什么？

我现在会把它总结成：

```text
第一步：
保证语义正确

第二步：
识别可并发调用

第三步：
保留必要 happens-before

第四步：
限制资源并发度

第五步：
让 runtime state commit 尽量确定
```

而不是：

```text
模型给了 N 个调用
↓
全部 Promise.all
↓
出了 race 再修
```

这是 Agent 工程里一个非常典型的：

```text
correctness before throughput
```

问题。

---

#### 再接回父文的五个动词

这个 Beat 其实主要落在：

```text
行动
+
约束
```

之间。

因为 Tool 调度解决的是：

```text
模型已经提出了多个合理动作
```

以后：

> **Harness 应该以什么顺序让这些动作真正进入世界？**

因此：

```text
Model
   ↓
Tool Calls
   ↓
Effect classification
   ↓
Scheduling constraints
   ↓
Environment
```

约束不是只体现在：

```text
“允许 / 不允许”
```

还包括：

```text
“现在 / 稍后”
“并发 / 串行”
```

换句话说：

> Harness 不仅控制**能不能做**，也控制**怎样做才不破坏任务语义**。

---

#### 源码与证据边界

从 Claude Code v2.1.88 恢复源码可以直接确认：

* `runTools()` 会先调用 `partitionToolCalls()` 对 Tool Calls 分批，再选择 concurrent 或 serial execution path；
* `partitionToolCalls()` 会先用 Tool 的 `inputSchema` 解析具体输入，再调用 `isConcurrencySafe(parsedInput)`；
* 输入解析失败，或 `isConcurrencySafe()` 判断过程中抛异常，均保守退回 `false`；
* 只有**相邻的** concurrency-safe 调用会合并到同一个 batch，不安全调用形成顺序边界；
* safe batch 通过 `runToolsConcurrently()` 执行，并受到默认 10 的最大并发度限制；
* serial path 会在每个 Tool execution 后立即应用 context modifier；concurrent path 则先收集 modifier，再按原 Tool Call 顺序应用，从而避免 completion order 直接决定 runtime state。
* `Tool.ts` 本身对未声明 `isConcurrencySafe` 的 Tool 默认返回 `false`。

### Macro 3 小结

到这里，Tool 这一 Macro 已经形成两层：

```text
Beat 3.1
Tool contract

Harness 必须理解：
这个动作是什么？
有什么 effect？
可以怎样执行？
        ↓

Beat 3.2
Effect-aware scheduling

Harness 再根据这些语义决定：
哪些动作可以重叠执行？
哪些必须保序？
```

所以所谓：

```text
Tool calling
```

真正进入 production runtime 后，其实已经变成：

```text
Tool declaration
    ↓
Input validation
    ↓
Effect classification
    ↓
Scheduling
    ↓
Execution
    ↓
Observation
```

而不是：

```text
模型输出一个函数名
↓
直接调用
```


现在我们已经把：

```text
动作怎么执行
```

讲得比较清楚了。

但还有一个更敏感的问题一直没有真正展开：

```text
模型提出动作
        ↓
Harness 技术上可以执行
```

并不等于：

```text
用户授权它执行
```

尤其当 Tool 拥有：

```text
Shell
文件修改
Git
网络
MCP
```

以后，权限系统不能只是：

```text
Bash = dangerous
Read = safe
```

因为同一个 Bash：

```text
git status
```

和：

```text
git push --force
```

显然不应该得到完全相同的处理。

所以下一个 Macro 要把：

```text
Capability
```

和：

```text
Authorization
```

彻底拆开。

