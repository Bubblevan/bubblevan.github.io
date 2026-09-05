---
title: "Claude Code Tools：Tool Contract、ToolUseContext 与并发调度"
weight: 2
---

## 1. 有 Tool，不代表 Agent 会用 Tool

### 1.1 为什么 API 对程序好用，对 Agent 却可能很难用？

假设我现在要给 Claude 做一个公司日历工具。

后端其实早就写好了：

```text
GET /users
GET /events
POST /events
GET /rooms
GET /documents
```

于是最自然的想法就是：把现成 API 一层一层包成 Tool。

```text
list_users
list_events
create_event
list_rooms
get_document
```

再给每个 Tool 补一个 JSON Schema：

```json
{
  "name": "list_users",
  "description": "List users",
  "input_schema": {
    "type": "object",
    "properties": {}
  }
}
```

从传统软件工程的角度看，这没什么毛病。

后端已经有 API 了。

MCP Server 或 Agent Harness 只不过再加一层 Adapter：

```text
Backend API
    ↓
Tool wrapper
    ↓
LLM
```

甚至还能顺便得到一份很漂亮的对应关系：

```text
一个 API Endpoint
=
一个 Agent Tool
```

问题是，真正把它扔给 Agent 以后，事情很快就会变得奇怪。

比如用户说：

> 帮我约 Jane 下周开个会，聊一下最近的 Acme 项目。把上次项目规划会的笔记附上，再订一个会议室。

如果是我自己写传统程序，调用路径很容易确定：

```python
jane = find_user("Jane")
project = find_project("Acme")
notes = find_latest_planning_notes(project)
slots = get_common_availability(jane)
room = find_available_room(slots)
create_event(...)
```

控制流是谁写的？

**程序员。**

什么时候遍历，什么时候过滤，什么时候停止搜索，哪些中间结果根本不需要暴露出去，也是程序员提前决定的。

但 Agent 面对的是另外一个问题。

它首先得自己判断：

```text
我要调用哪个 Tool？
        ↓
Tool 参数应该填什么？
        ↓
返回结果是什么意思？
        ↓
下一步调用哪个 Tool？
        ↓
现在的信息够了吗？
```

也就是说，我们虽然把同一个 Backend 暴露了出去，但调用者已经换了。

传统 API 面对的是一个大体确定的调用程序：

```text
deterministic program
```

Agent Tool 面对的却是一个会根据上下文临时决定下一步的模型：

```text
non-deterministic agent
```

Anthropic 在《Writing effective tools for agents — with agents》里专门强调了这个区别：普通函数和 API 通常是在两个相对确定的系统之间建立 contract，而 Tool 则开始连接一个确定性的外部系统和一个行为并不完全确定的 Agent。

这不是一句抽象定义。

它会直接改变 Tool 应该怎么设计。

---

#### 一个 `list_contacts()` 就能把这个问题暴露出来

假设通讯录后端只有：

```python
list_contacts()
```

里面一共有 5000 个联系人。

传统程序完全可以这么干：

```python
for contact in list_contacts():
    if contact.name == "Jane":
        return contact
```

这里的 5000 条记录主要占的是：

```text
内存
CPU
网络传输
```

对程序来说，这虽然未必最高效，但通常也不是什么灾难。

LLM Agent 却不一样。

如果 Tool 返回：

```text
5000 contacts
```

这些记录并不会神奇地待在某个“Agent 内存”里等待模型随机访问。

通常它们最终要形成一次 Tool Result，重新进入模型的 Context：

```text
tool_use
   ↓
list_contacts()
   ↓
5000 条记录
   ↓
tool_result
   ↓
Context
   ↓
Claude 从 Token 中找到 Jane
```

Claude 为了找一个 Jane，可能先读进去几千个完全没有关系的人。

所以同一个接口：

```text
list_contacts()
```

对普通程序来说只是一个不够优雅的 API。

对 Agent 来说，却可能直接变成：

```text
Context 消耗
+
更长的 Tool Result
+
更高的模型推理成本
+
更多无关信息
+
更高的后续出错概率
```

Anthropic 给出的改法很朴素：

```text
list_contacts()
```

未必应该直接成为 Agent Tool。

更合适的接口可能是：

```text
search_contacts(query)
```

例如：

```json
{
  "query": "Jane"
}
```

Tool 自己先在确定性世界里完成：

```text
5000 contacts
      ↓
search / filter / rank
      ↓
3 candidates
```

再把真正有意义的部分交给 Claude：

```text
1. Jane Doe — Sales
2. Jane Smith — Engineering
3. Jane Wang — Product
```

这时一个很有意思的变化出现了。

以前我理解 Tool，容易把它想成：

```text
LLM 调用外部函数
```

但从 Context 的角度看，它其实还承担了另一件事：

> **把本来需要模型处理的确定性计算，从 Context 里面搬出去。**

比如：

```text
查找
过滤
排序
聚合
格式转换
数据库查询
日志检索
```

这些工作根本没有必要全部变成 Token，让 LLM 自己“看”。

能让普通程序算的，就先让普通程序算。

最后只把 Agent 做决策真正需要的 observation 送回来。

于是：

```text
Tool
```

既在扩展模型能够做的事情，也在限制模型需要亲自处理的事情。

这一点其实已经开始和 Context Engineering 接上了。

---

#### API 追求“通用”，Agent Tool 往往需要追求“合适”

传统 API 很喜欢提供底层原语。

因为调用 API 的程序员知道自己要干什么。

例如：

```text
list_users
list_events
create_event
```

分别对应用户、日历和事件资源，REST 味非常正。

但用户刚才真正想做的是：

```text
schedule a meeting
```

如果把三个底层动作全部交给 Claude：

```text
list_users
   ↓
找到 Jane

list_events
   ↓
自己推共同空闲时间

create_event
   ↓
创建会议
```

中间每一步都会制造新的决策点。

甚至还可能继续展开：

```text
list_rooms
get_room
list_documents
search_documents
get_document
```

对于程序员来说：

```text
more primitives
=
more flexibility
```

但对 Agent 来说，还多出了一层代价：

```text
more primitives
=
more possible action paths
```

Claude 不只得完成任务。

它还得在这些 action 之间不停做 routing。

Anthropic 因此给出了一个很典型的建议：不要机械地把每个 Backend Endpoint 都映射成 Tool，而应该考虑 Agent 实际面对的 workflow。

例如：

```text
list_users
list_events
create_event
```

在某些场景里可以收敛成：

```text
schedule_event
```

内部再由确定性程序完成：

```text
查用户
→ 查日历
→ 计算空闲时间
→ 创建事件
```

另一个例子是：

```text
read_logs
```

与其返回整段日志，不如提供：

```text
search_logs
```

先检索真正相关的日志行，再带上一点前后文。

Anthropic 还举过 `get_customer_context` 这种接口：不是逼 Agent 自己先查 Customer、再查 Transaction、再查 Notes，而是把完成这个工作流常用的相关信息先聚合起来。

这里暂时不展开讨论到底应该设计多少个 Tool。

Macro 2 会专门处理 Tool Set 和 Action Space。

现在我更想先抓住一个变化：

```text
Backend API 的抽象边界
```

和：

```text
Agent 最容易完成任务的抽象边界
```

并不一定相同。

所以：

```text
已有 API
   ↓
包一层 JSON Schema
   ↓
Agent Tool
```

并不是一个自动成立的推导。

---

#### Tool 的“易用性”也不再只是开发者体验

普通 SDK 的 Developer Experience 不好，通常是程序员抱怨：

```text
函数名难懂
参数奇怪
文档太差
返回值麻烦
```

但程序员至少还能：

```text
Google
看文档
下断点
读源码
写 Adapter
```

Agent 用错 Tool 的表现却可能只是：

```text
调用错 Tool
```

或者：

```text
调用对 Tool，
参数却填错了
```

又或者：

```text
第一次结果不理想，
于是连续重复调用
```

甚至：

```text
根本没有调用那个 Tool
```

这些行为最后看到的可能只是：

> Claude 怎么这么笨？

可真正的问题未必出在 Model。

也可能是 Tool 给它提供了很差的 affordance。

所谓 **affordance**，我这里不打算翻译成很玄的词。

可以暂时把它理解成：

> 一个接口本身让使用者“看得出来它能拿来干什么”的程度。

比如：

```text
list_all_records
```

和：

```text
search_customer_orders
```

即使底层最后调用的是同一套数据库，模型看到这两个 Tool 时，形成的下一步动作判断也不一样。

所以 Tool Name、Description、Schema、返回结果，并不只是 API 文档。

它们本身就是 Model 推理时看到的环境。

---

#### Tool 实际上同时在塑造 Action Space 和 Observation Space

到这里，我觉得可以把最开始的图稍微改一下。

以前我们会画：

```text
Model
  ↓
Tool
  ↓
World
```

但对 Agent 来说，更完整的过程其实是：

```text
             Action
Model ─────────────────→ Tool
                          │
                          │ deterministic work
                          ↓
                     Environment
                          │
                          │ result
                          ↓
Model ←───────────────── Tool
          Observation
```

Tool 的输入这一面定义：

```text
Agent 能做什么？
```

也就是它的 **Action Space**。

Tool 的输出这一面则决定：

```text
Agent 做完以后能看到什么？
```

也就是它的 **Observation Space**。

一个 Tool 即使执行结果完全正确：

```text
HTTP 200
数据库查询成功
函数没有异常
```

只要返回给模型的 observation 很差：

```text
5000 条无关记录
一堆 UUID
完整 HTTP Header
几十 KB Debug 信息
模糊错误码
```

Agent 依然可能把下一步走错。

反过来也一样。

Result 再漂亮，如果 Tool 名字、Description 和参数让模型根本不知道什么时候该调用它，它还是没用。

所以：

```text
Tool quality
```

不能只看：

```text
function correctness
```

还至少要同时看：

```text
Model 能不能选对它？
Model 能不能填对参数？
Tool 能不能完成真实动作？
返回结果能不能帮助下一步推理？
```

这也是为什么 Anthropic 那篇文章最后会一路讲到：

```text
Tool selection
Namespacing
Tool description
Response format
Pagination
Truncation
Error message
Evaluation
```

乍一看这些东西分别属于：

```text
API Design
Prompt Engineering
Context Engineering
Evaluation
```

结果放进 Agent 以后，全都汇进了 Tool Engineering。

---

#### 但这还只讲完了 Model 一边

到这里，我们其实仍然只回答了：

> **怎样设计一个 Model 比较容易使用的 Tool？**

可 Claude Code 面对的事情还没有结束。

比如模型已经成功产生：

```json
{
  "name": "Bash",
  "input": {
    "command": "git push origin main"
  }
}
```

从 Model 的角度：

```text
Tool 选对了
Schema 也填对了
```

是不是就应该直接：

```ts
exec("git push origin main")
```

？

显然不能。

Harness 还要知道：

```text
输入在当前环境中真的成立吗？
这一次调用有权限吗？
它会不会修改状态？
能和别的 Tool 同时跑吗？
运行时用户发来新消息应该取消吗？
执行完成以后，哪些东西给模型看？
哪些东西只留给 Runtime？
```

于是 Agent Tool 还有另一半 contract。

Anthropic 那篇文章主要回答：

```text
怎样把 Tool 设计得让 Agent 好用？
```

而我们手里的 Claude Code v2.1.88 `Tool.ts`，正好能继续回答：

```text
当这个 Tool 真正进入生产 Harness，
Runtime 还需要知道什么？
```

这就是下一 Beat 要接上的东西。

---

### 1.2 Tool 同时面对 Model 和 Harness

我第一次只看 Claude API 里的 Tool Definition 时，很容易形成一种印象：

```text
Tool
=
name
+
description
+
input_schema
```

毕竟模型真正能看到的大体就是这些信息。

例如：

```json
{
  "name": "Read",
  "description": "Read a file from the local filesystem",
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path": {
        "type": "string"
      }
    }
  }
}
```

Model 根据这些信息决定：

```text
要不要用 Read？
```

以及：

```text
Read 的参数怎么填？
```

如果只做到一个 Function Calling Demo，这已经够用了。

比如：

```python
if tool_call.name == "Read":
    result = read_file(tool_call.input["file_path"])
```

几十行代码就能跑起来。

但再回头看 Claude Code v2.1.88 的 `Tool.ts`，会发现它明显比：

```ts
(input) => output
```

胖得多。

把具体泛型和实现细节先放到一边，我关心的字段大致长成这样：

```ts
Tool
├── inputSchema
├── inputJSONSchema
├── outputSchema
│
├── validateInput(...)
├── checkPermissions(...)
│
├── isConcurrencySafe(input)
├── isReadOnly(input)
├── isDestructive?(input)
├── interruptBehavior?()
│
├── call(...)
│
└── result mapping / rendering
```

真正负责“调用函数”的：

```ts
call(...)
```

只占其中一部分。

剩下那些字段都在回答：

> **Harness 怎样理解这次动作？**

于是这里其实出现了两个不同的消费者。

---

#### Model 看到的是“我能做什么”

对 Model 来说，Tool 首先是一种行动提示。

它需要知道：

```text
这个 Tool 叫什么？
什么时候应该用？
输入是什么？
参数分别是什么意思？
结果大概是什么？
```

我们可以把这一层叫：

```text
Agent-facing contract
```

大致对应：

```text
name
description
input schema
output semantics
```

它解决的是：

```text
Natural-language intent
        ↓
Choose a tool
        ↓
Construct tool input
```

例如用户说：

> 看一下 `src/auth.ts` 前 200 行。

Model 得从一堆 Tool 里识别：

```text
Read
```

然后生成：

```json
{
  "file_path": "src/auth.ts",
  "offset": 1,
  "limit": 200
}
```

这正是上一 Beat 讲的 Agent affordance。

Tool Definition 本身就是模型 Context 的一部分。

描述写得含糊，参数命名模棱两可，功能互相重叠，Claude 的 Action Selection 就会被影响。

Anthropic 甚至在实际 Tool Eval 中发现过这种问题：Claude 的 Web Search Tool 曾经出现过模型没必要地在 Query 后面追加年份的行为，最后不是去改模型权重，而是修改 Tool Description，把调用行为纠正回来。

换句话说：

```text
Tool spec
```

本身也有 Prompt 的性质。

不过 Tool Description 怎么写，我们留到 Macro 4 再详细讲。

现在继续往 Runtime 里面走。

---

#### Harness 看到的却是“这个动作意味着什么”

模型产生：

```json
{
  "name": "Bash",
  "input": {
    "command": "git status"
  }
}
```

以后，它自己的工作其实暂停了。

接下来真正接手的是 Harness。

Harness 不能只知道：

```text
name = Bash
```

它还要判断：

```text
这个输入结构合法吗？
         ↓
这个动作在当前环境成立吗？
         ↓
这次调用获得授权了吗？
         ↓
它会修改什么状态？
         ↓
能不能与其他调用重叠执行？
         ↓
运行过程中允许被打断吗？
         ↓
结果怎样重新送回 Model？
```

这部分可以叫：

```text
Runtime-facing contract
```

于是完整的 Tool 已经不像：

```text
function
```

而更像：

```text
Tool
├── Agent-facing semantics
│   ├── name
│   ├── description
│   └── schema
│
└── Runtime-facing semantics
    ├── validation
    ├── authorization
    ├── effects
    ├── scheduling
    ├── interruption
    ├── execution
    └── result mapping
```

这也是我现在更愿意把 Claude Code 的 Tool 理解成：

> **Model 与真实环境之间的一份 Runtime Contract。**

---

#### Schema 只是第一道边界

先看一个看起来很普通的字段：

```ts
readonly inputSchema: Input
```

另外还有类似：

```ts
readonly inputJSONSchema?: ToolInputJSONSchema
outputSchema?: z.ZodType<unknown>
```

Schema 很容易被理解成：

> 给 Function Calling 用的参数定义。

这当然没错。

但站到 Harness 视角再看，它还有另一层意义。

Model 原本产生的是开放的自然语言：

```text
把 auth.ts 给我看一下
```

Tool Call 会把它压缩进一个结构化动作：

```json
{
  "file_path": "src/auth.ts",
  "offset": 1,
  "limit": 200
}
```

所以它完成了一次空间转换：

```text
开放语言空间
      ↓
有限结构化输入
      ↓
Runtime Action
```

如果 Model 输出：

```json
{
  "file_path": 123
}
```

Harness 根本没必要等到：

```ts
fs.readFile(123)
```

以后才发现有问题。

Tool boundary 就可以把它拦下来。

Schema 回答的是：

> **你构造出来的动作，至少长得对不对？**

但它只能回答到这里。

---

#### 参数长得对，不代表动作真的成立

假设 Bash 的 Schema 是：

```json
{
  "command": {
    "type": "string"
  }
}
```

那么：

```text
pwd
```

合法。

```text
git status
```

也合法。

```text
git push origin main
```

还是合法。

甚至：

```text
rm -rf some-directory
```

从类型系统看，也只不过是一个：

```text
string
```

所以：

```text
schema valid
```

最多只能说明：

```text
参数符合结构
```

它并不能说明：

```text
这次动作在当前 Runtime 中成立
```

这也是为什么 Claude Code 的 Tool contract 还保留了：

```ts
validateInput(...)
```

这样的阶段。

例如：

```text
Edit(
  file_path = "foo.ts",
  old_string = "abc",
  new_string = "xyz"
)
```

所有参数类型都对。

但当前文件里根本不存在：

```text
abc
```

那么这次 Edit 作为一个具体动作就无法成立。

又比如某个 Tool 只允许访问当前 Workspace：

```text
/workspace/project/
```

模型给出的却是另一个位置。

路径仍然是：

```text
string
```

Schema 没问题。

Runtime 语义却可能不允许。

所以可以把两层先拆开：

```text
Schema
  ↓
“输入长得对吗？”

Validation
  ↓
“这个具体动作现在成立吗？”
```

这一区分看似很细，实际上能避免 Tool 最后变成一个巨大的：

```ts
try {
    // 什么东西都塞进来
} catch (e) {
    // 再统一报错
}
```

---

#### 动作成立，也不代表已经获得授权

再往后才是：

```ts
checkPermissions(...)
```

这又是第三个问题。

例如：

```text
Bash("git status")
```

可能满足：

```text
Schema OK
Validation OK
Permission OK
```

于是直接执行。

而：

```text
Bash("git push origin main")
```

也可能：

```text
Schema OK
Validation OK
```

但到 Permission 这一层变成：

```text
Ask user
```

所以至少在概念上应该分成：

```text
Schema
  ↓
你生成的 Action 格式正确吗？

Validation
  ↓
这个 Action 在当前环境中成立吗？

Permission
  ↓
即使成立，这次允许执行吗？
```

这里我先不继续展开 Claude Code 的：

```text
allow
deny
ask
permission mode
sandbox
auto mode
```

因为这些已经属于 `security.md` 的主线。

在 `tools.md` 里，我只需要留下这条边界：

```text
Capability
≠
Authorization
```

Model 能看到一个 Tool，意味着：

```text
系统具有这种能力
```

并不意味着：

```text
任何具体 Tool Call 都获得了执行授权
```

否则只要把：

```text
Bash
```

暴露给 Model，就等价于：

```text
Model 拥有整个 Shell
```

那生产 Agent 基本也不用谈什么 Harness 了。

---

#### `isReadOnly()` 这些字段为什么不属于普通函数，却属于 Agent Tool？

接下来几个字段更有意思：

```ts
isConcurrencySafe(input)
isReadOnly(input)
isDestructive?(input)
```

普通业务函数很少会把：

```text
我是不是 destructive
我能不能和别人并发
```

写进函数接口里。

因为传统程序里的调用关系本来就是程序员写好的。

例如：

```python
a = read_file("a.ts")
b = read_file("b.ts")
```

要不要：

```python
await asyncio.gather(...)
```

是程序员自己的决定。

Agent Harness 却面对一段**运行时才由 Model 生成的程序**。

Claude 一次 Response 完全可能吐出：

```text
Read(a.ts)
Read(b.ts)
Read(c.ts)
```

也可能吐出：

```text
Edit(a.ts)
Bash("npm test")
Edit(a.ts)
```

Harness 事先并不知道下一轮会得到什么。

于是 Runtime 要想进行调度，就得知道每次 Action 对环境的 effect。

而这种 effect 甚至不能简单绑定在 Tool Name 上。

看看 Bash 就知道了：

```text
pwd
git status
grep foo bar.txt
```

和：

```text
rm file
npm install
git commit
```

都来自同一个：

```text
Bash
```

但显然不能全部按同一种副作用处理。

所以 Claude Code 的 Tool interface 让类似：

```ts
isReadOnly(input)
```

接收**具体 input**。

判断单位从：

```text
Tool name
```

变成：

```text
Tool
+
Concrete input
+
Runtime context
```

于是：

```text
Bash
```

不再天然等于：

```text
dangerous write
```

也不天然等于：

```text
read-only
```

Harness 真正关心的是：

```text
Bash("这一条具体 command")
```

对环境意味着什么。

这已经很接近一种朴素的：

```text
effect semantics
```

当然，我不会把 Claude Code 硬说成实现了一套形式化 Effect System。

它没有必要背这么大的理论包袱。

这里真正有价值的只是这个设计方向：

> **让 Tool 自己向 Runtime 暴露调度和副作用所需的语义，而不是让调度器看到 Tool Name 以后重新猜一次。**

后面的 Macro 5，我们再顺着：

```ts
isConcurrencySafe(input)
```

进入 `toolOrchestration.ts`，看为什么 Claude Code 没有简单写成：

```ts
await Promise.all(toolCalls)
```

---

#### Tool 的生命周期甚至包括“用户插话以后怎么办”

Claude Code 的 Tool contract 里还有一个很容易被忽视的概念：

```ts
interruptBehavior()
```

大致区分：

```text
cancel
```

和：

```text
block
```

这件事如果放到普通函数教程里，看着会有点莫名其妙。

一个：

```ts
readFile()
```

为什么还要告诉别人“我能不能被用户打断”？

但把 Tool 放回 Agent Session 就合理了。

Agent 正在执行一个长时间 Tool 时，用户可能突然发来：

> 等等，不用了。

或者：

> 先别改这个文件，我刚想到另一种方案。

那么 Harness 面对的就不是：

```text
Promise 怎么 resolve
```

而是：

```text
这次 Action 能取消吗？
取消以后结果还能交给 Model 吗？
某些临界操作是不是必须先完成？
当前 Session 的状态怎么恢复？
```

Tool 已经不是一个孤立 Function。

它生活在：

```text
长期运行的 Session
```

里面。

所以中断语义也进入了 Tool Contract。

---

#### 更容易被忽略的是：Tool 内部结果和 Model 看到的结果也不是一回事

如果 Tool contract 到：

```ts
call(...)
```

就结束，那它最终仍然可以理解成一个复杂一点的函数。

但 Claude Code 还存在另一层很值得注意的东西：

```text
ToolResult
```

按你现在这份 v2.1.88 快照整理出来的结构，内部结果除了普通：

```text
data
```

之外，还可能携带：

```text
newMessages
contextModifier
MCP metadata
...
```

然后 Runtime 再通过类似：

```ts
mapToolResultToToolResultBlockParam(...)
```

的路径，把内部结果转成真正重新进入 Model Context 的：

```text
tool_result
```

也就是说：

```text
Environment result
```

不一定等于：

```text
Model observation
```

完整过程更像：

```text
Tool.call(...)
    ↓
Internal ToolResult
    ↓
Harness processing
    ├── runtime state
    ├── context modification
    ├── UI rendering
    └── model-facing mapping
             ↓
         tool_result
             ↓
           Model
```

这件事其实会在后面变得非常重要。

例如一个 Tool 内部可能拿到：

```text
原始 HTTP Response
大量 metadata
调试字段
分页信息
缓存信息
```

Runtime 自己也许需要其中一些字段。

但这不意味着应该一股脑全部塞进模型 Context。

同样一份执行结果：

```text
给 Runtime 看的
```

和：

```text
给 Claude 看的
```

完全可以是两种 representation。

甚至：

```text
给用户 UI 看的
```

还可以是第三种。

这也解释了为什么 Tool Result 设计最终会和：

```text
Context Engineering
```

纠缠在一起。

Macro 3 我会单独拆这件事。

---

#### 所以生产 Tool 实际上横跨了三条边界

到这里，把整个过程重新画一遍会更清楚：

```text
User Intent
    │
    ↓
┌─────────────────────┐
│        Model        │
│                     │
│ Tool name           │
│ description         │
│ schema              │
└─────────┬───────────┘
          │
          │ tool_use
          ↓
┌─────────────────────┐
│       Harness       │
│                     │
│ validateInput       │
│ permissions         │
│ effect semantics    │
│ scheduling          │
│ interruption        │
│ execution           │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│     Environment     │
│ filesystem / shell  │
│ git / network / MCP │
└─────────┬───────────┘
          │
          │ raw result
          ↓
┌─────────────────────┐
│       Harness       │
│                     │
│ ToolResult          │
│ context update      │
│ result mapping      │
└─────────┬───────────┘
          │
          │ tool_result
          ↓
┌─────────────────────┐
│        Model        │
│ next reasoning step │
└─────────────────────┘
```

这样再回头看：

```ts
const result = await tools[name](input)
```

就知道这个几十行 Demo 到底省略掉了什么。

它省略的不只是：

```text
工程细节
```

而是生产 Agent 中几种性质完全不同的边界：

```text
Action Interface
Execution Contract
Observation Interface
```

因此，我现在更愿意用下面这个式子记 Claude Code 的 Tool：

```text
Tool
≈
Agent Action Interface
+
Harness Execution Contract
+
Agent Observation Interface
```

第一部分决定：

```text
Claude 会不会用。
```

第二部分决定：

```text
Claude 想做以后，系统能不能正确地做。
```

第三部分决定：

```text
做完以后，Claude 能不能看懂发生了什么。
```

这也正好把 Anthropic 的 Tool Engineering 和 Claude Code 的 Harness Engineering 接到了一起：

```text
Anthropic Tool Engineering
        ↓
怎样设计 Agent 容易使用的 Action / Observation？

Claude Code Runtime
        ↓
怎样把这些 Action 可靠地变成真实 Effect？
```

所以所谓：

```text
Tool 不只是 API wrapper
```

并不是因为 Tool 的代码一定很复杂。

而是因为一旦调用者从传统程序换成 Agent，它就必须同时面对两个完全不同的世界：

```text
上面是概率性的 Model
下面是确定性的 Environment
```

Tool 加 Harness 做的事情，就是把这两个世界接起来。

下一 Macro 再往前走一步：

> 如果 Tool 本身就在定义 Agent 的 Action Space，那么到底应该给 Agent 多少个 Tool？

这时问题就从：

```text
一个 Tool 应该长什么样？
```

变成了：

```text
整个 Tool Set 应该怎样设计？
```

而答案同样不会是：

```text
Backend 有多少 API，
我就暴露多少 Tool。
```

### 1.3 从 Claude Code 源码看，Tool 是一个 Action Object

前面的章节已经从设计角度说明了 Tool 为什么不只是函数。后半部分的源码材料可以补上 runtime 这一面：Claude Code 的 `Tool` contract 同时描述“模型如何提出动作”和“Harness 如何把动作送进环境”。

从 v2.1.88 的恢复源码看，一个生产 Tool 至少要围绕这些职责组织：

```text
name / description
inputSchema / output schema
validateInput()
checkPermissions()
isConcurrencySafe(input)
isReadOnly(input)
isDestructive(input)
interruptBehavior()
call()
mapToolResultToToolResultBlockParam()
renderToolUseMessage()
renderToolResultMessage()
```

这些字段不是同一层的重复配置：

```text
Schema
  → 输入长什么样

Validation
  → 这个动作在当前世界里是否成立

Permission
  → 当前调用是否获得授权

Effect metadata
  → 它会怎样影响环境，能否并发

Interrupt semantics
  → 用户插话时是取消还是等待

Execution
  → 怎样真正调用环境

Observation mapping
  → 哪些结果进入模型和用户界面
```

因此，`call()` 只是执行链中的一个节点，并不是 Tool 的全部抽象。把 Tool 简化成：

```ts
interface Tool {
  execute(input: unknown): Promise<unknown>
}
```

会让 Harness 失去在执行前进行解析、验证、授权和调度的统一边界。

### 1.4 `ToolUseContext` 和 `ToolResult` 说明 Tool 属于 Runtime

Tool 调用也不是只接收 `input`。`ToolUseContext` 会把一次调用放回完整的 Agent Session 中，至少涉及：

```text
Tools
MCP connections
AbortController
file state
Agent definitions
messages
budgets
ToolPermissionContext
additionalWorkingDirectories
alwaysAllowRules
alwaysDenyRules
alwaysAskRules
permission mode
```

这解释了为什么同一个 Tool 在不同 Session、目录范围或权限模式下，可能得到不同的执行结果。Tool 不只是一个被调用的函数，它是 Runtime 参与者。

内部结果也不必直接等于模型看到的 `tool_result`。恢复源码中的 `ToolResult` 可以携带：

```ts
data
newMessages?
contextModifier?
mcpMeta?
```

Runtime 还会通过：

```ts
mapToolResultToToolResultBlockParam(content, toolUseID)
```

把内部结果映射成模型可消费的表示。于是一次执行至少有三种可能的观察面：

```text
Environment result
        ↓
Internal ToolResult
        ├── runtime state
        ├── context modification
        ├── human-facing rendering
        └── model-facing tool_result
```

同一份数据不需要原样同时交给 Runtime、模型和用户。原始响应、调试字段、MCP metadata 或长日志可以留在内部；模型获得经过预算和语义筛选的 observation，用户界面则可以用进度、折叠和错误样式呈现。

### 1.5 默认值体现的是“按维度保守”，不是所有地方都拒绝

`buildTool()` 的默认值也值得单独记录：

```ts
isEnabled: () => true
isConcurrencySafe: () => false
isReadOnly: () => false
isDestructive: () => false
```

这组默认值不能概括成“所有安全判断都 fail-closed”。它的保守性主要体现在不同维度：

```text
不知道能不能并发
→ 不给并发优化

不知道是不是只读
→ 不把它当只读

不知道是不是 destructive
→ 不能直接推出它属于不可逆操作
```

同样，Tool-specific `checkPermissions` 的默认行为不是简单 `deny`，而是先允许这一层通过，再交给通用 Permission System 做最终授权判断。源码阅读时必须把这些维度分开，不能因为某个 Effect 默认保守，就推导出整个 Runtime 的默认策略都是拒绝。

因此，Tool 可以压缩成一个比“函数调用”更准确的模型：

```text
Tool
=
Capability
+ Schema
+ Policy hooks
+ Effect metadata
+ Execution
+ Observation mapping
```

这段源码补充放在 Macro 1，是因为它解释的是 Tool 的身份和边界；具体的 Result 设计、Description 设计、Permission 细节和 effect-aware scheduling，分别在后面的 Macro 3、4、5 展开。这样前后两半形成互补，而不会让同一套 `Tool` 字段在文末重复出现。

## 2. Tool Set 本身就是 Agent 的 Action Space

### 2.1 为什么 Tool 不是越多越好？

上一节最后把 Tool 的输入侧理解成了：

```text
Agent Action Interface
```

那接下来很自然会冒出一个问题：

> 如果 Tool 决定了 Agent 能做什么，是不是应该尽可能多给它一些 Tool？

直觉上似乎是这样。

一个 Claude Code 只有：

```text
Read
Edit
Bash
```

另一个 Claude Code 拥有：

```text
Read
Write
Edit
Glob
Grep
Bash
GitStatus
GitDiff
GitCommit
GitPush
NpmInstall
NpmTest
Pytest
SearchDocs
SearchWeb
FetchUrl
...
```

第二个看起来显然“能力更强”。

毕竟：

```text
更多 Tool
=
更多 Capability
```

至少从系统能力集合上说，这句话没错。

可 Model 真正运行时面对的不是一个抽象集合。

它每走一步都必须回答：

```text
现在该选哪个？
```

Tool 每增加一个，实际上也在扩大：

```text
possible next actions
```

所以 Tool Set 同时在做两件相反的事情：

```text
增加可做的事情
        ↑
        │
Tool Set
        │
        ↓
增加需要做的选择
```

这也是 Anthropic 在总结内部 Tool Eval 时观察到的问题之一：**更多 Tool 并不自动带来更好的任务结果**。尤其是直接把现有软件功能或者 Backend API Endpoint 一一包装成 Tool，很容易得到一套对软件架构很整齐、对 Agent 却很难使用的接口。

---

#### 我以前很容易把 Tool 设计成 Backend 的镜像

假设公司内部已经有这样几个 API：

```text
GET /users
GET /users/:id
GET /events
POST /events
GET /rooms
POST /reservations
GET /documents
GET /documents/:id
```

如果我要写 MCP Server，最机械的做法就是：

```text
list_users
get_user
list_events
create_event
list_rooms
reserve_room
list_documents
get_document
```

甚至可以自动生成。

Backend 有什么：

```text
endpoint
```

我就暴露什么：

```text
tool
```

最后 MCP Server 的结构和 REST API 高度一致：

```text
Backend Resource Model
          ↓
       Tool Set
```

这种设计对程序员很舒服。

因为我一眼就能找到：

```text
/users
→
list_users
```

但 Claude 面对用户任务时，并没有先拿到一张 API 调用流程图。

用户说的是：

> 下周找时间和 Jane 开个 Acme 项目会，把上次项目规划笔记附上，再订一个会议室。

Model 要自己把这句话拆成：

```text
找 Jane
    ↓
找 Jane 的 ID
    ↓
找双方日程
    ↓
计算共同空闲时间
    ↓
找会议室
    ↓
判断会议室是否可用
    ↓
预订会议室
    ↓
搜索 Acme
    ↓
找上次 planning meeting
    ↓
找 meeting notes
    ↓
创建 event
    ↓
把 document attach 上去
```

假如每一步刚好都有一个底层 Tool：

```text
list_users
get_user
list_events
list_rooms
reserve_room
list_documents
get_document
create_event
```

从 Capability Coverage 看，什么都没缺。

但 Agent 得自己承担整段 orchestration。

每个中间节点又可能返回一批结果：

```text
list_users
→ 200 users

list_events
→ 87 events

list_rooms
→ 30 rooms

list_documents
→ 500 documents
```

然后 Model 再从这些 Token 里找下一步。

于是“Tool 很丰富”渐渐变成：

```text
Action Routing
+
Intermediate Context
+
Error Surface
+
Longer Trajectory
```

真正麻烦的地方不只是调用次数变多。

Trajectory 每增长一步，Agent 就多了一次走偏的机会。

比如第一步找错 Jane：

```text
Jane Doe
Jane Smith
Jane Chen
```

后面所有日程搜索都可能跟着错。

或者前面找到正确会议记录，却在几十个 Document ID 里选错附件。

于是：

```text
8 个底层 API 全都执行正确
```

并不能保证：

```text
整个 Agent Task 正确
```

这就是 Agent 系统和传统 API Integration 很不一样的地方。

---

#### Anthropic 给出的方向是：Tool 可以围绕 Workflow 来切

还是刚才那个例子。

与其直接暴露：

```text
list_users
list_events
create_event
```

可以考虑提供：

```text
schedule_event
```

然后让 Tool 内部自己完成：

```text
resolve attendees
      ↓
query calendars
      ↓
find availability
      ↓
create event
```

Anthropic 在文章里给出的另外两个例子也很典型：

```text
read_logs
```

可以变成：

```text
search_logs
```

不再要求 Agent 自己读取大块日志以后做字符串检索。

以及：

```text
get_customer_by_id
list_transactions
list_notes
```

可以针对常见客服工作流组合成：

```text
get_customer_context
```

一次返回这个 Customer 当前任务真正相关的交易、记录和上下文。

这三个例子看起来分别属于：

```text
Calendar
Logs
CRM
```

但做的其实是同一件事情：

```text
把频繁重复的确定性子流程
从 Agent Trajectory
搬进 Tool Implementation
```

也就是：

```text
Before

Agent
  ↓ choose
Tool A
  ↓
Agent
  ↓ choose
Tool B
  ↓
Agent
  ↓ choose
Tool C
  ↓
Agent


After

Agent
  ↓ choose
Workflow Tool
  ↓
A → B → C
  ↓
Agent
```

注意第二种并不是让 Agent “少干活”这么简单。

它把一些并不需要语言模型判断的步骤交回给普通程序。

例如：

```text
按 ID join 两张表
按 timestamp 排序
计算时间区间交集
过滤 error level
按照 customer_id 聚合
```

这些事情用：

```python
SQL
Python
TypeScript
```

做得又快又稳定。

没必要让 Claude：

```text
读取
→ 理解
→ 决策
→ 再调用
```

一遍。

---

#### 所以 Workflow Tool 本质上也在压缩 Trajectory

前面讲 Context Engineering 的时候，我更多想到：

```text
压缩 Token
```

但 Tool Consolidation 其实还在压另一种东西：

```text
Agent Trajectory
```

比如原来完成任务需要：

```text
Tool A
→ observation
→ reasoning
→ Tool B
→ observation
→ reasoning
→ Tool C
→ observation
→ reasoning
→ Tool D
```

如果 A → B → C 本质上是一个稳定工作流，就可能收成：

```text
Workflow Tool
→ observation
→ Tool D
```

于是少掉的不只是：

```text
Tool Call 数量
```

还有三轮中间：

```text
Observation
Reasoning
Routing
```

这会直接减少：

```text
Context consumption
Tool-selection mistakes
Invalid parameters
Recovery steps
```

Anthropic 甚至建议在 Tool Eval 时统计：

```text
total tool calls
runtime
token consumption
tool errors
```

因为大量重复 Tool Call 本身就是一种诊断信号：它可能说明某些操作应该被重新组合，或者 Tool 的分页、过滤和抽象粒度需要调整。

这时候我才觉得：

> Tool Set 的设计，其实已经开始参与 Agent 的控制流设计。

我们没有像传统 Workflow Engine 那样提前写死：

```python
step1()
step2()
step3()
```

但我们可以通过 Tool Boundary 告诉模型：

```text
哪些步骤值得让你自己推理，
哪些步骤已经有稳定程序替你完成。
```

---

#### 可这并不意味着“Tool 越少越好”

这里也很容易从一个极端走到另一个极端。

既然：

```text
list_users
list_events
create_event
```

太碎，那是不是干脆做一个：

```text
do_calendar_task
```

？

Schema：

```json
{
  "request": "string"
}
```

Description：

```text
Perform any calendar-related task.
```

表面看只剩一个 Tool：

```text
Action Space = 1
```

Claude 再也不会选错 Tool 了。

但问题只是被塞到了 Tool 里面。

比如：

```text
do_calendar_task(
  "看看 Jane 明天下午有没有空"
)
```

和：

```text
do_calendar_task(
  "取消我下周全部会议并重新安排"
)
```

它们：

```text
副作用不同
权限不同
验证方式不同
失败恢复不同
返回信息不同
```

可现在全部挤进一个：

```text
request: string
```

里面。

Tool 表面简单了，Runtime Contract 却变得越来越模糊。

而且模型也失去了结构化 Action：

```text
schedule_event
search_events
cancel_event
```

所提供的明确 affordance。

所以这里真正要找的不是：

```text
max tools
```

或者：

```text
min tools
```

而是一个合适的：

```text
abstraction level
```

太低：

```text
API primitive
API primitive
API primitive
API primitive
```

Agent 被迫自己编排大量机械步骤。

太高：

```text
do_everything(request)
```

又把动作语义、副作用和结构化约束全部揉掉。

比较理想的位置更像：

```text
                    Too low-level
                         │
                         │
list_users
list_events
create_event
reserve_room
                         │
                         │
                  schedule_event
                         │
                         │
                do_everything()
                         │
                         │
                    Too high-level
```

中间那个位置通常更接近：

> **一个人类也能自然描述、具有明确目标，同时内部又能稳定完成若干机械步骤的动作。**

这也解释了 Anthropic 为什么强调 high-impact workflows，而不是简单地说：

> 把 Tool 数量减少到 N 个。

没有这个神奇的 N。

---

#### Primitive Tool 也并没有失去价值

拿 Claude Code 自己来说，这点尤其明显。

Coding Agent 很难完全依赖：

```text
fix_bug
implement_feature
refactor_project
```

这种大型 Workflow Tool。

因为代码任务的组合空间太大了。

一个真正的 Bug Fix 可能需要：

```text
搜索符号
→ 读文件
→ 再搜索
→ 修改
→ 跑测试
→ 看错误
→ 再读文件
→ 再修改
```

你无法提前把所有可能 trajectory 编译成：

```text
fix_bug()
```

所以 Claude Code 仍然很依赖：

```text
Read
Grep
Glob
Edit
Bash
```

这类相对 primitive 的 Tool。

这和 Anthropic 的建议并不矛盾。

关键不在：

```text
Primitive = bad
Workflow = good
```

而在：

```text
这个决策到底需不需要 Agent 做？
```

例如：

```text
Grep → 找相关文件
```

搜索什么 Query、搜索哪个目录，往往跟当前推理状态有关。

适合留给 Agent。

但：

```text
拿到 customer id
→ 查询 transactions
→ 查询 notes
→ 按时间排序
→ 拼接固定格式
```

如果每个客服任务都这么走一遍，就很可能是在浪费 Agent Trajectory。

我觉得可以暂时用这样一个问题判断：

```text
这几个步骤之间，
究竟存在新的语义决策，

还是只是稳定的数据搬运？
```

如果每一步都需要根据上一轮 Observation 重新理解问题：

```text
保留 Primitive
```

通常更有价值。

如果中间只是：

```text
lookup
join
filter
sort
format
```

那就很值得考虑：

```text
Workflow Tool
```

---

#### Tool Consolidation 也不能提前靠感觉做完

还有一个我很喜欢的细节。

Anthropic 并没有建议：

> 先坐在会议室里设计一套完美 Tool Taxonomy。

他们的路线反而是：

```text
Prototype
   ↓
Realistic Eval
   ↓
Inspect Trajectory
   ↓
Find repeated / confused workflows
   ↓
Redesign Tools
```

比如 Eval Trace 经常长成：

```text
search_user
search_user
get_user
list_events
list_events
create_event
```

这里可能已经暴露：

```text
search / user resolution 太弱
```

或者：

```text
calendar workflow 应该 consolidation
```

另一个 Trace：

```text
search_logs
search_logs
search_logs
search_logs
search_logs
```

则未必说明应该做：

```text
investigate_incident()
```

也可能只是：

```text
search_logs 的 filter 不够好
```

甚至：

```text
pagination 默认值不合理
```

所以 Tool Set 是可以用 Eval 反推出来的。

这一点后面 Macro 6 还会回来。

现在只需要先把：

```text
Tool Set
```

理解成一个真正需要设计和测量的：

```text
Agent Action Space
```

而不是：

```text
Backend API Inventory
```

---

#### 如果让我现在做一次 Tool Review，我会先画这张图

假设现有系统是：

```text
Backend
├── Users API
├── Calendar API
├── Documents API
├── Logs API
└── Billing API
```

我不会直接推出：

```text
Tools
├── list_users
├── get_user
├── list_events
├── get_event
├── create_event
├── list_documents
├── get_document
├── list_logs
├── get_log
├── list_transactions
└── ...
```

我会先多加一层：

```text
Backend Resources
       ↓
Real User Workflows
       ↓
Agent Decisions
       ↓
Tool Boundary
```

比如：

```text
用户工作流：
调查重复扣款

Agent 真正需要决定：
哪个 customer？
问题发生在哪个时间范围？
哪些异常值得继续追？

确定性系统可以完成：
按 customer_id 搜索
按 transaction_id join
按时间窗口筛日志
聚合同类错误

于是可能得到：
search_payment_incident(...)
```

而另一个：

```text
代码里查某个 symbol 为什么报错
```

里面每一步都可能根据搜索结果改变方向：

```text
Grep
Read
Grep
Read
```

那就没必要强行包成：

```text
debug_symbol()
```

这才是我现在理解的 Tool Selection。

它并不是：

```text
哪些 Backend Function 值得暴露？
```

而更接近：

> **哪些决策应该留给 Agent，哪些确定性的工作应该藏在 Tool 后面？**

这句话会一路影响后面的 Tool Result、Context Consumption 和 Eval。

---

### 2.2 Tool 名字为什么也会影响模型行为？

假设现在已经解决了 Tool 数量问题。

我的系统里只剩几个精心设计过的搜索 Tool：

```text
search
search_project
search_user
search_issue
search_document
```

好像已经挺清楚了。

直到我又接入：

```text
GitHub MCP
Jira MCP
Asana MCP
Google Drive MCP
Slack MCP
```

然后 Claude 真正看到的 Tool Set 开始长成：

```text
search
search
search
search
search
get_user
get_user
get_user
create_comment
create_comment
...
```

当然实际 MCP Client 通常不会真的允许一堆完全同名 Tool 直接裸奔。

于是我们会开始加：

```text
namespace
```

例如：

```text
github_search
jira_search
asana_search
drive_search
slack_search
```

乍一看，这只是程序员最熟悉的命名冲突问题：

```text
foo.search()
bar.search()
```

但对于 LLM Agent，namespace 还有更直接的作用。

它正在帮助 Model 回答：

```text
这个动作属于哪个世界？
```

Anthropic 在内部工具经验里专门把 Namespacing 单独列成了一条原则：当 Agent 同时接触几十个 MCP Server、甚至数百个 Tool 时，功能重叠或意义模糊的 Tool 会让模型更容易混淆；使用 Service 或 Resource 前缀可以帮助划分这些功能边界。

---

#### Tool Name 本身就在参与 Routing

传统程序调用：

```python
jira.search(...)
```

之前，程序员已经明确写下：

```text
jira
```

不会在运行时突然想：

> 要不去 Asana 找？

LLM 的动作选择却是动态的。

比如用户说：

> 看看 Apollo 项目最近还有哪些没解决的问题。

此时模型可能拥有：

```text
github_search
jira_search
asana_search
drive_search
slack_search
```

每个 Tool 都有一个 Description。

Model 要从上下文判断：

```text
Apollo 的“问题”
```

到底意味着：

```text
GitHub Issue？
Jira Ticket？
Asana Task？
Slack discussion？
```

所以：

```text
jira_
github_
asana_
```

这些前缀绝不只是为了：

```text
避免函数重名
```

它还在给模型建立一层非常廉价的先验：

```text
Service
  ↓
Resource
  ↓
Action
```

例如：

```text
jira_issues_search
```

已经隐含：

```text
Jira
  ↓
Issues
  ↓
Search
```

Model 还没读完 Description，就已经得到了一部分结构。

---

#### 我可以把 Tool Selection 想成一次很小的分类问题

假设 Agent Context 里加载了：

```text
Tool A
Tool B
Tool C
...
Tool Z
```

当前用户 Intent 是：

```text
I
```

那么每一次工具调用之前，Model 都在做类似：

```text
P(Tool | Intent, Context)
```

的判断。

当然真实 Transformer 并没有真的在外面跑一个：

```python
classifier.predict()
```

这里仅仅是一个方便理解的抽象。

如果 Tool Set 是：

```text
search
find
lookup
query
retrieve
```

它们 Description 又高度重叠：

```text
Search for relevant information...
Find relevant information...
Look up relevant information...
Query relevant information...
Retrieve relevant information...
```

那么这些候选 Action 之间的边界就很模糊。

大概像：

```text
Intent
  │
  ├──────── search
  ├──────── find
  ├──────── lookup
  ├──────── query
  └──────── retrieve
```

Model 得依赖大量细小语义去猜：

```text
到底哪个才是设计者想让我用的？
```

如果换成：

```text
github_code_search
github_issues_search
slack_messages_search
drive_documents_search
```

Action Space 会更像：

```text
Intent
  │
  ├── source = GitHub
  │      ├── code
  │      └── issues
  │
  ├── source = Slack
  │      └── messages
  │
  └── source = Drive
         └── documents
```

这相当于利用 Tool Name 给 Action Space 加了一点结构。

---

#### Namespace 的价值不在“名字长”，而在边界清楚

所以我不会机械地得出：

> Tool Name 越长越好。

例如：

```text
company_internal_productivity_platform_google_drive_document_full_text_semantic_search
```

当然够明确。

但每个 Tool 都这样命名：

```text
Tool Definition Token
```

也会越来越多。

真正有意义的是让相关 Tool 在命名上形成稳定结构。

例如：

```text
github_code_search
github_issues_search
github_pr_get

jira_issues_search
jira_issue_get
jira_issue_update

slack_messages_search
slack_thread_get
slack_message_send
```

Model 很容易从名字中看到：

```text
namespace_resource_action
```

或者你也可以设计成：

```text
search_github_code
search_github_issues
get_github_pr
```

问题来了：

> 到底 prefix 好，还是 suffix 好？

Anthropic 自己的答案挺有意思。

他们发现 prefix-based 和 suffix-based namespacing 在 Tool Eval 中确实会产生非平凡的性能差异，而且效果会随模型变化，所以并没有给出一个永远正确的命名模板，而是建议根据自己的 Evaluation 决定。

这一点很符合整个 Tool Engineering 的味道：

```text
jira_search
```

还是：

```text
search_jira
```

已经不能只靠：

```text
“哪个看起来更优雅”
```

决定了。

如果它影响 Model Tool Selection，那它就是一个可测的 Agent Interface 设计问题。

---

#### Resource Namespace 还能继续切第二层边界

只写：

```text
github_search
```

在 Tool 少的时候已经不错。

但如果 GitHub MCP 里逐渐加入：

```text
search code
search issues
search pull requests
search commits
search discussions
```

又会回到一个：

```text
万能 search
```

的问题。

于是可以继续细分：

```text
github_code_search
github_issues_search
github_pr_search
github_commits_search
```

这里的 Resource Name 起到第二次路由作用：

```text
GitHub
  ↓
Code / Issue / PR / Commit
  ↓
Search
```

这和传统 Object-Oriented API 的 namespace 有一点像，但重点又不完全相同。

传统 namespace 主要帮助：

```text
程序员组织代码
```

Agent namespace 还在帮助：

```text
Model 组织可能的动作
```

换句话说：

```text
Tool Taxonomy
```

本身就会进入模型推理。

---

#### Tool Description 很强，但不能拿 Description 给烂命名擦屁股

理论上我们可以把所有 Tool 都叫：

```text
tool_1
tool_2
tool_3
```

然后写特别详细的 Description：

```text
tool_1:
Search GitHub source code...

tool_2:
Search Jira issues...

tool_3:
Search Slack messages...
```

Model 仍然可能学会。

可这相当于把一个本来能在名字里表达的信息，全部推给 Description。

另一方面，也不要因为名字叫：

```text
github_search
```

就觉得 Description 可以只写：

```text
Search GitHub.
```

因为名字只能划分：

```text
大致 Action Boundary
```

具体：

```text
什么时候应该用？
支持什么 Query？
会搜哪些 Resource？
参数是什么意思？
返回什么？
限制是什么？
```

还是要靠 Description 和 Schema。

所以三者的职责可以暂时分成：

```text
Name
  ↓
我大概是谁？

Description
  ↓
什么时候应该找我？

Schema
  ↓
找我时具体应该怎么说？
```

后面 Macro 4 会专门把：

```text
Description
+
Schema
```

当作 Prompt Surface 来处理。

这里先只看：

```text
Name
```

对 Action Routing 的影响。

---

#### 最麻烦的情况其实是“两个 Tool 都能做”

假设我接入了：

```text
github_issues_search
jira_issues_search
```

这两个名字已经非常清楚。

但用户说：

> 找一下登录超时那个 Bug。

问题还是存在。

因为这个 Bug 可能同时出现在：

```text
GitHub Issues
Jira
```

此时的冲突已经不再是命名不好。

而是：

```text
Functional overlap
```

也就是说，Namespace 可以帮助 Model 看懂：

```text
它们属于不同系统
```

却不能替设计者回答：

```text
究竟什么时候该查哪个系统？
```

这就要求 Description 补上组织里的真实语义：

```text
github_issues_search
→ Public/open-source issue tracking

jira_issues_search
→ Internal engineering planning and incident tracking
```

如果现实里团队自己都没有清晰边界：

```text
Bug 有时在 GitHub
有时在 Jira
有时两个都有
```

那 Tool Design 也不可能凭一个漂亮名字把这个组织问题抹掉。

可能需要设计：

```text
search_engineering_issues
```

在 Tool 内部同时检索两个系统；

也可能应该让 Agent：

```text
先搜 Jira
必要时再搜 GitHub
```

到底哪一个更好，仍然要回到：

```text
真实 Workflow
+
Eval Trace
```

判断。

---

#### 这也是为什么 Tool Set 不能只看单个 Tool

我们做普通 API Review 时，很容易逐个检查：

```text
Tool A 的 Schema 好不好？
Tool B 的 Description 清不清楚？
Tool C 的 Error Handling 完不完整？
```

但对于 Agent 来说，还有一个系统级问题：

```text
A、B、C 放在一起以后怎么样？
```

一个 Tool 单独看可能非常好。

例如：

```text
search_documents
```

另一个也很好：

```text
find_files
```

再来一个：

```text
semantic_search
```

每个都有自己的合理用途。

可三个一起交给 Claude 时，Model 可能开始：

```text
search_documents
  ↓ no result

find_files
  ↓ some result

semantic_search
  ↓ some result

search_documents
  ↓ again
```

最终不是任何一个 Tool 写坏了。

而是：

```text
Tool Set 的边界坏了。
```

这也是我现在觉得 **Tool Eval 一定要把整个 Tool Set 放进去测** 的原因。

只写：

```python
assert search_documents("foo") == ...
```

测到的是：

```text
Function correctness
```

却测不到：

```text
Agent 到底会不会选它
```

---

#### Tool 数量甚至会直接占 Context

这里还有一个非常现实的成本。

一个 Tool 不只在被调用时才消耗资源。

为了让 Model 知道：

```text
我可以用什么？
```

Tool Definition 本身就需要以某种形式进入模型可用的上下文。

一个 Tool 至少有：

```text
name
description
input schema
```

几十个 Tool 加起来就是一大片 Tool Specification。

所以：

```text
100 个 Tool
```

并不只是意味着：

```text
100 种 Action
```

还意味着模型在当前工作环境里需要识别和区分更多 Action Description。

Anthropic 在总结 Namespacing 时也指出，选择性地实现 Tool，一方面降低工具间的混淆，另一方面也减少需要加载进 Agent Context 的 Tool 和 Tool Description。

这让我觉得 Tool Set 和 Context Engineering 的关系其实有两层：

```text
Tool Definitions
    ↓
consume context before action

Tool Results
    ↓
consume context after action
```

Macro 2 处理前一个。

Macro 3 就要正式进入后一个。

---

#### 所以我现在不会再把 Tool Set 当成“能力菜单”

更准确一点，它像是：

```text
一个模型每一步可以选择的操作语言
```

可以把 Agent Loop 稍微改写成：

```text
State
  ↓
Model
  ↓
Choose an action from Tool Set
  ↓
Environment transition
  ↓
Observation
  ↓
New State
```

从这个角度：

```text
Tool Set
```

已经很像一套：

```text
Action Vocabulary
```

如果 Vocabulary 里全是过细的底层动作：

```text
Agent trajectory 变长
```

如果全是模糊的大型动作：

```text
Agent loses control / semantics
```

如果大量 Action 重叠：

```text
routing ambiguity 增加
```

如果命名又没有稳定 namespace：

```text
边界进一步模糊
```

所以真正值得设计的是：

```text
            Tool Set
               │
      ┌────────┴────────┐
      │                 │
 abstraction         separation
      │                 │
任务粒度是否合适？    动作边界是否清楚？
      │                 │
 workflow           namespace
 primitive          naming
 consolidation      description boundary
```

这也是为什么我现在不太愿意说：

> “我给这个 Agent 接了 80 个 MCP Tools，所以它能力特别强。”

80 只能说明：

```text
Capability Surface 很大
```

不能说明：

```text
Agent 能稳定使用这 80 个 Tool
```

甚至很可能刚好相反。

真正应该问的是：

```text
它在真实任务里，
能不能选到正确的 Action，
并用尽可能短而稳定的 Trajectory 完成任务？
```

Anthropic 对 Tool Set 的建议最后也落在这里：Tool 应该拥有清晰、彼此区分的目的，并让 Agent 能以接近人类自然拆解任务的方式组合它们；过多或重叠的 Tool 会干扰高效策略。

---

到这里，Tool 的输入侧基本已经讲清楚了：

```text
Macro 1

单个 Tool 是什么？
        ↓
Action Interface
+
Runtime Contract
+
Observation Interface


Macro 2

Tool Set 怎么组织？
        ↓
Agent Action Space
```

但我们的图还有右半边没有真正展开：

```text
Agent
  ↓ Action
Tool
  ↓
Environment
  ↓
Tool Result
  ↓ Observation
Agent
```

一个 Agent 选对了 Tool、参数也填对了，执行甚至完全成功，最后仍然可能因为：

```text
Tool Result 太长
信息太杂
字段太底层
ID 看不懂
错误信息没法行动
```

而在下一步推理里翻车。

所以接下来的 Macro 3，要从 Action Space 转到 **Observation Space**：

> **Tool 返回什么，本身就是 Context Engineering。**

## 3. Tool Result 本身就是 Context Engineering

### 3.1 为什么返回完整 API Response 反而可能更差？

前两节一直在研究 Tool 的输入侧：

```text
User Intent
    ↓
Model
    ↓
Choose Tool
    ↓
Construct Input
```

但一个 Agent Loop 真正跑起来以后，还有完全对称的另一半：

```text
Tool
    ↓
Environment
    ↓
Result
    ↓
Model
    ↓
Next Action
```

如果把前半段叫：

```text
Action Space
```

后半段其实就是：

```text
Observation Space
```

Model 通过 Tool 能做什么，决定它的 Action Space。

Tool 做完以后 Model 能看到什么，则决定它下一步基于怎样的 Observation 继续推理。

于是一个 Tool 的质量至少有两个方向：

```text
Tool Input
   ↓
Claude 能不能正确表达动作？

Tool Output
   ↓
Claude 能不能正确理解发生了什么？
```

第二个问题很容易被低估。

因为传统程序里我们已经习惯：

```text
返回的信息越完整越好
```

例如一个 REST API 可能给我：

```json
{
  "id": "msg_01JX93K..."
  "channel_id": "C08Q2M4...",
  "user_id": "U027AK...",
  "thread_ts": "1754022918.339100",
  "text": "The deployment failed again.",
  "mime_type": "text/plain",
  "created_at": "2026-08-31T11:15:18Z",
  "updated_at": "2026-08-31T11:15:18Z",
  "workspace_id": "T019...",
  "permalink": "...",
  "metadata": {
    ...
  }
}
```

作为程序员，我甚至会觉得：

> 很好，一个字段都没丢。

因为普通程序可以拿：

```python
response["text"]
```

然后无视剩下所有内容。

没有读到的字段，几乎没有认知成本。

LLM 却不太一样。

只要这些内容进入 Tool Result：

```text
id
channel_id
user_id
thread_ts
mime_type
workspace_id
metadata
...
```

就已经一起进入了它这一轮可见的 Context。

即使它最终只需要：

```text
The deployment failed again.
```

其他字段还是变成了 Token。

所以传统 API 常见的：

```text
Return everything,
let the caller decide.
```

到了 Agent Tool 这里，未必还是一个好的默认值。

Anthropic 在 2025 年的 Tool Engineering 文章里直接建议 Tool 返回 **high-signal information**，优先给模型有语义、能推动后续行动的信息，而不是把 UUID、技术尺寸、底层 MIME 类型等实现字段机械地搬进结果里。

---

#### 一个 UUID 对数据库很有意义，对 Claude 却可能什么也没说

假设我做一个文件搜索 Tool：

```text
search_documents("agent memory")
```

Backend 返回：

```json
[
  {
    "id": "5cdd51c4-97b6-49fe-b347-ec31e93fd50c",
    "type": "application/vnd.google-apps.document",
    "parent_id": "fc12467e-...",
    "modified_time": "2026-08-14T03:11:21Z"
  },
  {
    "id": "6fb47cc0-a88d-4d84-a1da-76e311a41697",
    "type": "application/vnd.google-apps.document",
    "parent_id": "a917d362-...",
    "modified_time": "2026-07-22T12:31:10Z"
  }
]
```

数据库当然知道这些东西是什么意思。

Claude 看完却只能得到：

```text
有两个 UUID。
```

如果接下来要决定：

> 哪一份更像我要找的 Context Engineering 笔记？

它基本无从判断。

换一种 Result：

```text
1. Agent Context Engineering 学习笔记
   Updated: 2026-08-14
   Folder: Hi-Agent / Context

2. Agent Memory 与 RAG 实现笔记
   Updated: 2026-07-22
   Folder: Hi-Agent / Memory
```

同样是两条 Backend Record。

可对模型来说，这已经形成了可以直接推理的 Observation：

```text
query = context engineering
        ↓
candidate 1 的 title / folder 更匹配
        ↓
下一步读取 candidate 1
```

Anthropic 也特别提到，他们观察到自然语言名称、术语或可解释 identifier 往往比任意字母数字 UUID 更容易让 Agent 正确使用；仅仅把无意义 ID 映射成更可解释的表示，就能改善检索任务中的精度。

这里有一个我以前容易混淆的地方：

```text
machine-readable
```

和：

```text
model-useful
```

根本不是同一个标准。

UUID 非常 machine-readable。

但它的：

```text
semantic density
```

几乎为零。

---

#### Tool Result 应该回答“下一步决策需要什么”

于是设计 Tool Output 时，我现在不会先问：

> Backend 能返回哪些字段？

我会先问：

> Claude 拿到这个 Result 以后，下一步通常需要判断什么？

比如一个：

```text
search_users("Jane")
```

后续目的通常是：

```text
区分几个 Jane
```

那么结果至少应该有：

```text
name
team / role
email 或其他可识别信息
```

比如：

```text
1. Jane Smith
   Engineering — Infrastructure
   jane.smith@example.com

2. Jane Wang
   Product — Growth
   jane.wang@example.com
```

而不是：

```text
user_id
workspace_id
avatar_64px_url
locale
account_type_code
...
```

再比如一个：

```text
search_logs(query="database timeout")
```

后续目的通常是：

```text
判断错误发生在哪里
判断值不值得进一步追
```

所以更适合返回：

```text
timestamp
service
severity
message
少量 surrounding context
```

例如：

```text
[03:41:08] ERROR payment-api
Database timeout after 5000 ms
request_id=req_18392

  03:41:07 retrying query...
> 03:41:08 database timeout after 5000 ms
  03:41:08 request failed with 503
```

而不是整个：

```text
500 MB raw log file
```

---

#### 这和 RAG 里的 Retrieval 其实很像

写到这里，我会自然联想到前面学 RAG 时的一个问题：

```text
Retriever 的目标，
到底是“把东西搜出来”，
还是“把有助于回答的东西搜出来”？
```

两者当然不完全一样。

Agent Tool 也类似。

一个 Tool 的 Backend Correctness 可以是：

```text
数据库查询成功
```

但 Agent-facing Correctness 还要再问一层：

```text
返回的 Observation，
真的足以支持下一步决策吗？
```

例如搜索结果召回了一百条记录：

```text
Recall 很高
```

但相关的那三条淹没在第：

```text
17
43
89
```

条。

对程序来说数据没有丢。

对 Agent 来说，实际效果可能仍然很差。

所以 Tool Result Design 已经很接近：

```text
Retrieval
+
Ranking
+
Context Construction
```

这三个问题的交界处。

---

#### 这里终于能解释 Claude Code 为什么还需要 Result Mapping

前面看 Claude Code 的 `Tool` contract 时，我们已经见过：

```text
call(...)
   ↓
ToolResult
```

但 `ToolResult` 并不等于最终原封不动塞进 API 的：

```text
tool_result
```

Runtime 中还存在结果映射这一层。

抽象以后更像：

```text
Environment
    ↓
Raw execution result
    ↓
Internal ToolResult
    ↓
Harness mapping
    ↓
Model-facing tool_result
```

这层边界很有意思。

因为 Harness 内部需要的信息和 Claude 需要的信息可能不同。

例如 Tool 内部可能需要保存：

```text
execution metadata
UI data
state update
context modifier
MCP metadata
```

但 Model 的下一步决策真正需要的可能只有：

```text
3 files matched:

src/auth.ts
src/login.ts
tests/auth.test.ts
```

反过来也一样。

用户终端 UI 可能只需要显示：

```text
✓ Read src/auth.ts
```

Model 却需要真实的文件内容。

所以现在至少已经出现三种 representation：

```text
Internal Runtime Representation

Model-facing Observation

Human-facing Rendering
```

它们没有理由强制完全相同。

---

#### “Raw Result” 和 “Observation”最好在脑子里分开

我觉得可以直接把两个词分开记：

```text
Result
=
Environment 实际返回了什么

Observation
=
Harness 决定让 Agent 看到什么
```

例如：

```text
Bash("npm test")
```

真实 Result 可能包括：

```text
stdout
stderr
exit code
signal
duration
process metadata
shell metadata
```

Claude 下一步需要的 Observation 可能只是：

```text
Exit code: 1

FAIL tests/auth.test.ts
Expected 200, received 401

1 failed, 37 passed
```

如果发生 Hang，则可能更需要：

```text
Command exceeded timeout after 120s.
Last output:
...
```

Raw Result 当然还在那里。

但 Agent-facing Observation 应该围绕：

```text
下一步怎么做
```

组织。

所以 Tool Output Design 其实是在做一次：

```text
Environment State
      ↓
Observation Function
      ↓
Agent-visible State
```

这让我更容易理解为什么一个好的 Agent Harness 不能只是：

```ts
return JSON.stringify(rawResponse)
```

---

#### 但也不能为了省 Token 把关键字段全删了

这里马上又遇到另一个极端。

既然 UUID 没意义，那全部删掉：

```text
Jane Smith
Engineering
```

很清爽。

结果下一步 Claude 要调用：

```text
send_message(user_id=...)
```

完蛋。

刚才为了 Context Efficiency 删除的：

```text
user_id
```

恰好是下一次 Tool Call 必需的参数。

于是 Tool Output 有两种需求开始打架：

```text
Human / Model semantic context
          ↕
Machine continuation identifiers
```

一个结果既要：

```text
看得懂
```

又要：

```text
接得上下一次调用
```

Anthropic 给出的处理方式不是简单二选一，而是让 Tool 可以根据任务需要提供不同 Response Format。

这正好进入下一 Beat。

---

### 3.2 `concise` / `detailed` 为什么不是一个 UI 小功能？

假设还是：

```text
search_user(name="Jane")
```

第一次调用的目的只是：

> 先看看有几个 Jane。

这时：

```text
1. Jane Smith — Infrastructure
2. Jane Wang — Product
```

已经够了。

可如果下一步要：

```text
send_message(user_id=...)
```

Claude 还得拿到：

```text
user_id
```

于是同一个 Tool 的理想输出会随着：

```text
下一步任务
```

变化。

这时候一个非常自然的设计就是：

```json
{
  "name": "Jane",
  "response_format": "concise"
}
```

或者：

```json
{
  "name": "Jane",
  "response_format": "detailed"
}
```

Anthropic 在文章里就展示了类似的 `response_format` 设计，用 `concise` 与 `detailed` 让 Agent 自己决定当前是否需要底层 identifier。其 Slack 示例中，简洁结果只保留主要内容，而详细格式额外带上 `thread_ts`、`channel_id`、`user_id` 等支持后续 Tool Call 的字段；文章给出的那组示例里，简洁结果大约只用了详细结果三分之一的 Token。

---

#### 同一个 Tool，其实可能承担两个阶段

例如：

```text
search_threads
```

Agent 第一次调用它时可能处在：

```text
Exploration
```

阶段。

目标只是：

```text
这里有没有相关内容？
```

此时：

```text
Concise
```

更合理：

```text
1. #infra
   Alice: Deployment failed after DB migration.

2. #backend
   Bob: Seeing database timeout in payment-api.
```

Claude 看完发现第二条最相关。

下一步进入：

```text
Manipulation / Follow-up
```

阶段。

它要：

```text
读取 thread replies
```

这时需要一个真正可调用的 identifier：

```text
channel_id
thread_ts
```

于是可以重新请求：

```json
{
  "query": "database timeout",
  "response_format": "detailed"
}
```

得到：

```json
{
  "text": "Seeing database timeout in payment-api.",
  "channel_name": "backend",
  "channel_id": "C09284...",
  "thread_ts": "1754022918.339100",
  "author": "Bob",
  "user_id": "U02..."
}
```

这两个结果谁更好？

没有统一答案。

因为它们服务的是不同的：

```text
Agent state
```

---

#### 这比“详情展开按钮”多了一层 Agent 语义

普通 Web UI 里：

```text
简略
详细
```

一般只是用户显示偏好。

Agent Tool 里的：

```text
concise
detailed
```

却会改变：

```text
Context Cost
+
Available Information
+
Available Future Actions
```

例如：

```text
concise
```

可能意味着：

```text
更少 Token
更低干扰
更适合 ranking
```

但也可能意味着：

```text
没有下游调用所需 ID
```

而：

```text
detailed
```

意味着：

```text
信息更完整
可以继续调用其他 Tool
```

代价则是：

```text
Context 更大
```

所以它其实是一种：

```text
Observation Budget Control
```

---

#### 甚至可以继续走向“按字段取 Observation”

Anthropic 在文章里顺带提到，可以继续扩展不同 Response Format，思路有点类似 GraphQL：让调用者选择自己真正需要哪些信息。

比如：

```json
{
  "query": "agent memory",
  "fields": [
    "title",
    "path",
    "updated_at"
  ]
}
```

而不是固定：

```text
每次返回整个 Document object
```

这类设计特别适合：

```text
Search
List
Database
CRM
Cloud resources
```

因为 Backend Object 往往非常胖。

例如一个 GitHub Issue 在 Backend 可能包含：

```text
id
node_id
url
repository_url
labels_url
comments_url
events_url
html_url
number
state
title
body
user
labels
assignee
assignees
milestone
locked
active_lock_reason
comments
pull_request
closed_at
created_at
updated_at
...
```

如果我的任务只是：

> 找最近还没解决的 auth bug。

Agent 可能只需要：

```text
number
title
state
updated_at
labels
short body preview
```

等确定：

```text
#183
```

最相关以后，再调用：

```text
get_issue(183)
```

拿完整正文。

这比一开始：

```text
search
→ 返回 30 个完整 Issue
```

舒服得多。

---

#### 这个模式其实就是 Progressive Disclosure

虽然 Anthropic 那篇 Tool 文章没有必要把它包装成复杂术语，但从系统设计看，这很像：

```text
Progressive Disclosure
```

先给：

```text
足够做当前决策的信息
```

只有当 Agent 确定值得深入时，再继续请求。

例如：

```text
search
  ↓
small observation
  ↓
select candidate
  ↓
get detail
  ↓
large observation
```

而不是：

```text
search
  ↓
everything about every candidate
```

这和我在 Agent Context 里越来越喜欢的一种原则很像：

> **Context 不应该提前装满所有可能有用的信息，而应该按当前决策逐步 materialize。**

Tool 正好提供了这种 materialization boundary。

---

#### 所以 Context Window 变大也没有解决这个问题

这里有一个很容易出现的反驳：

> 现在 Context Window 都几百 K、甚至更大了，这点 Tool Result 算什么？

但如果一个 Agent 在长任务里不断：

```text
Search
Read
Bash
Grep
Read
Test
Search
...
```

Tool Result 是持续累积的。

一次多：

```text
5K tokens
```

似乎没什么。

连续几十次以后就是完全不同的东西。

而且问题还不只是：

```text
塞不塞得下
```

还有：

```text
真正相关的信息占多少？
```

假如 Context 有：

```text
200K
```

其中：

```text
150K
```

都是过去 Tool Call 的低价值原始输出，

那“Context Window 足够大”并没有让模型得到：

```text
150K 有价值信息
```

只是允许垃圾留得更久。

所以我更愿意区分：

```text
Context Capacity
```

和：

```text
Context Quality
```

大 Context Window 解决的是前者。

Tool Result Design 处理的是后者。

Anthropic 在文章里也明确表示，即使 Agent 的有效 Context 长度未来继续增长，Context-efficient Tool 仍然会有价值。

---

#### Output Format 甚至也可能影响效果

这里还有一个很反直觉的小点。

假设相同数据，我可以输出：

```json
{
  "matches": [
    {
      "path": "src/auth.ts",
      "line": 83,
      "text": "..."
    }
  ]
}
```

也可以：

```text
src/auth.ts:83
...
```

或者：

```xml
<match file="src/auth.ts" line="83">
...
</match>
```

从程序员角度：

```text
信息一样
```

所以理应：

```text
模型效果一样
```

实际不一定。

Anthropic 提醒过，JSON、XML、Markdown 等 Response Structure 本身都可能改变 Eval 表现，并不存在一个适用于所有任务和模型的固定最佳格式，最终仍应该通过实际 Evaluation 选择。

这再次说明：

```text
Tool Result
```

不能只按：

```text
serialization correctness
```

来设计。

它是模型真正会读的东西。

---

#### 但 Format 再漂亮，也救不了一次返回十万行日志

所以这一 Beat 解决的是：

```text
每条 Observation 应该有多详细？
```

下一步还有另一个更暴力的问题：

```text
返回多少条？
```

比如：

```text
Grep
Search
Logs
Database Query
Directory Listing
Web Search
```

这些 Tool 最大的危险并不是某条 Record 太胖。

而是：

```text
结果数量没有上限。
```

这就需要进入：

```text
Pagination
Filter
Range
Truncation
```

---

### 3.3 Pagination、Filter、Truncation 为什么属于 Tool 设计？

假设 Claude 在一个大型项目里调用：

```text
Grep("TODO")
```

整个仓库有：

```text
18,423 matches
```

从 Unix Tool 的角度：

```text
grep 成功了。
```

Exit Code：

```text
0
```

Output 也是百分之百正确。

但如果 Harness 真把：

```text
18,423 matches
```

全部塞回 Context，

这个 Tool 对 Agent 来说大概率已经坏了。

有趣的是：

```text
Bug 不在搜索算法
```

甚至也不在：

```text
结果准确率
```

问题在：

```text
Observation unbounded
```

---

#### 普通 API 的“无限结果”到了 Agent 这里会直接烧 Context

例如：

```text
list_logs()
```

假如服务一天产生：

```text
2 GB logs
```

Tool 理论上可以全部读出来。

但 Agent 的需求通常不是：

> 把 2GB 看一遍。

更可能是：

> 为什么今天凌晨 3 点 payment-api 大量 503？

这句话已经给出了几个天然 Filter：

```text
time ≈ 03:00
service = payment-api
status = 503
```

所以一个更适合 Agent 的 Tool 可能是：

```json
{
  "service": "payment-api",
  "start_time": "2026-09-06T02:55:00",
  "end_time": "2026-09-06T03:10:00",
  "query": "503",
  "limit": 50
}
```

这里的：

```text
filter
time range
limit
```

并不是 Backend API 的“小优化”。

它们在直接控制：

```text
多少 Environment State
会被 materialize 到 Context
```

---

#### Anthropic 给出的四件套很实用

对任何可能产生大量 Output 的 Tool，Anthropic 建议考虑组合使用：

```text
Pagination
Range selection
Filtering
Truncation
```

并且给出合理默认值。

这四个东西解决的问题略有区别。

**Pagination**：

```text
我知道还有很多，
但一次只拿一部分。
```

例如：

```json
{
  "query": "authentication",
  "page": 1,
  "page_size": 20
}
```

**Range selection**：

```text
我只需要明确区间。
```

例如：

```json
{
  "file_path": "server.log",
  "offset": 1000,
  "limit": 200
}
```

或者：

```json
{
  "start_time": "...",
  "end_time": "..."
}
```

**Filtering**：

```text
先让确定性系统把无关记录剔掉。
```

例如：

```json
{
  "level": "ERROR",
  "service": "payment-api"
}
```

**Truncation**：

```text
前面三层都没拦住时，
Runtime 至少还有最后一道硬上限。
```

例如：

```text
Output truncated after 500 lines.
```

四者合在一起：

```text
Environment
    ↓ filter
Relevant subset
    ↓ range
Relevant region
    ↓ paginate
Current chunk
    ↓ truncate as safety limit
Bounded Observation
```

---

#### `limit=100` 这种参数其实是在定义 Agent 的 I/O Budget

以前写 API：

```text
limit
```

我更多把它理解成：

```text
保护数据库
减少网络带宽
```

到了 Agent Tool 里，它还有一层：

```text
保护 Context
```

例如：

```text
search_code(query, max_results=20)
```

已经在告诉 Runtime：

```text
这次 Observation 的规模应该有上界。
```

所以一个看起来很普通的：

```text
limit
```

其实已经参与：

```text
Context Budgeting
```

---

#### 默认值比“支持这个参数”更重要

Tool 支持：

```text
limit
```

却默认：

```text
limit = unlimited
```

对 Agent 来说仍然很危险。

因为模型未必每次都会主动填写：

```text
limit=20
```

尤其如果 Description 没提醒。

所以设计 Tool 时不能只问：

```text
Agent 有没有办法控制 Output？
```

还要问：

```text
Agent 什么都不特别指定时，
默认 Output 安全吗？
```

例如：

```text
search_logs(query, limit=50)
```

通常比：

```text
search_logs(query, limit?)
```

且缺省无限更合理。

这也是 Anthropic 特别强调：

```text
sensible default parameter values
```

的原因。

生产 Agent 里，默认路径非常重要。

因为它就是 Model 最容易走的路径。

---

#### Claude Code 的 Tool Output 上限其实非常能说明这个问题

Anthropic 在 **2025 年 9 月 11 日**发布那篇文章时写到：

> Claude Code 当时默认会把 Tool Response 限制在 25,000 tokens。

这里我会特意写：

```text
当时 / 文章所描述的 Claude Code
```

而不把这个数字硬当成 2026 年当前版本永远不变的实现事实。

因为具体阈值随版本完全可能调整。

真正值得学的不是：

```text
25000
```

这个 Magic Number。

而是：

> **一个 production coding agent 连 Tool Result 都必须有硬性体积边界。**

也就是说，即使 Tool 自己忘了：

```text
limit
```

Harness 层最好仍然不要相信：

```text
Output 会自然保持合理大小。
```

这和网络服务里的：

```text
timeout
max request size
memory limit
```

很像。

属于：

```text
runtime guardrail
```

---

#### Truncation 最怕的是“偷偷截断”

不过有硬上限又会产生新的 Bug。

例如 Tool 返回：

```text
Found 4812 matching lines.

src/a.ts:...
src/b.ts:...
...
```

到了第 500 行 Harness 直接：

```text
slice(0, maxTokens)
```

然后交给 Claude。

如果 Result 没告诉模型：

```text
我被截断了
```

Claude 很可能认为：

```text
这就是全部结果。
```

于是：

```text
absence from truncated output
```

被错误理解成：

```text
absence from environment
```

例如用户问：

> 项目里还有其他 `deprecated_api()` 调用吗？

结果第 501 行其实还有一个。

Claude 却回答：

> 没有了。

这就是很典型的：

```text
Observation semantics 被 truncation 改坏
```

所以正确的 Truncation 最好显式告诉 Agent：

```text
Showing first 100 of 4,812 matches.
Results were truncated.

Narrow your query with:
- path
- file_type
- max_results
```

这时候截断本身变成了 Observation 的一部分。

---

#### 好的 Truncation 应该顺便教模型下一次怎么搜

Anthropic 的建议更进一步：

如果结果因为太大被截断，不要只说：

```text
Output truncated.
```

还可以告诉 Agent：

```text
如何做一个更小、更 targeted 的下一次请求。
```

例如：

```text
4,812 results matched; only the first 100 are shown.

Try:
- restricting `path`
- adding `file_type`
- using a more specific query
- lowering the time range
```

这就出现了一个很有意思的循环：

```text
Broad Tool Call
      ↓
Large Result
      ↓
Truncation Message
      ↓
Model learns how to narrow query
      ↓
Targeted Tool Call
```

也就是 Tool Result 开始反过来：

```text
steer future Tool Use
```

Anthropic 也明确建议让被截断的结果向 Agent 提供帮助，引导它采用更小、更有针对性的检索，而不是一次把所有内容拖入 Context。

---

#### 这和 Search Agent 里的 Query Refinement 已经很像了

比如：

```text
Search("LLM Agent")
```

结果太宽。

Tool 返回：

```text
10,000+ results.
Please narrow by year, venue, or topic.
```

Model 下一轮：

```text
Search(
  query="LLM agent tool use evaluation",
  year_from=2025
)
```

然后再根据 Observation refine。

所以一个设计得好的 Search Tool 不只是：

```text
query → documents
```

还可以通过 Result Shape 帮 Agent形成：

```text
query
  ↓
observe
  ↓
refine
  ↓
query again
```

这种交互策略。

---

#### Range Selection 在 Coding Agent 里尤其常见

Claude Code 很典型的一类动作就是：

```text
Read file
```

如果每次 Read：

```text
整个文件
```

一个几千行文件连续读几次，Context 很快就很难看。

更合理的行为是：

```text
先搜索定位
   ↓
知道大概行号
   ↓
Read relevant range
```

例如：

```text
Grep("validateInput")
   ↓
Tool.ts:231
   ↓
Read(Tool.ts, offset=200, limit=100)
```

这和：

```text
cat Tool.ts
```

相比，

代码没有变。

真正改变的是：

```text
Observation materialization strategy
```

所以 Coding Agent 的：

```text
Grep
Read offset/limit
Search
```

组合，本质上也在做 Context Engineering。

---

#### Tool 可以把 Token Efficiency 变成“默认正确路径”

最后我觉得最有价值的一点是：

好的 Tool 不应该完全依赖 Prompt 里写：

> 请节省 Token，不要读取太多内容。

当然 Prompt 可以提醒。

但 Tool 本身完全可以通过接口设计，让高效路径更自然：

```text
默认 limit = 20
支持 filter
支持 range
支持 pagination
超限明确 truncation
```

那么模型即使没有每轮都记住：

```text
我要节约 Context
```

Runtime 也不至于直接爆掉。

这又回到 Harness Engineering 的味道：

```text
把希望模型遵守的关键约束
尽可能下沉到 deterministic system
```

Prompt 是软约束。

Tool Interface 和 Runtime Limit 则可以提供更硬的结构。

---

#### 但 Tool Result 还有最后一种特别重要的 Observation：失败

目前为止我们一直假设：

```text
Tool execution succeeded
```

可生产 Agent 一定会遇到：

```text
参数错
文件不存在
权限不足
Query 格式错误
资源冲突
结果太大
请求超时
```

如果失败以后 Tool 只返回：

```text
ERROR 400
```

Claude 虽然知道：

```text
失败了
```

却不知道：

```text
下一步怎么修
```

于是 Error Message 本身，也得按照 Observation 来设计。

---

### 3.4 Error 也可以教 Agent 下一步怎么做

假设 Claude 调用：

```json
{
  "tool": "search_logs",
  "input": {
    "time": "yesterday night"
  }
}
```

而 API 要求：

```text
ISO-8601 timestamp
```

最普通的后端 Error 可能是：

```text
400 Bad Request
```

或者稍微好一点：

```text
Invalid parameter.
```

对人类程序员来说，我看到：

```text
400
```

可以：

```text
查 API Docs
看 Stack Trace
打开源码
搜索错误码
```

Claude 在 Agent Loop 里却未必拥有这些东西。

它这一轮最直接得到的事实就是：

```text
Tool failed.
```

如果 Result 到此结束，下一步只能靠猜。

---

#### 不透明 Error 很容易制造无意义重试

例如：

```text
search_logs(...)
→ Error 400
```

Claude 可能猜：

```text
Query 太长？
```

于是缩短 Query。

还是：

```text
400
```

再猜：

```text
service 参数错？
```

换 Service。

还是失败。

最后 Transcript 长成：

```text
search_logs
→ 400

search_logs
→ 400

search_logs
→ 400

search_logs
→ 400
```

站在后端监控看：

```text
Agent 怎么这么蠢？
```

可如果 Error 一开始直接返回：

```text
Invalid `start_time`.

Expected ISO-8601 format:
YYYY-MM-DDTHH:MM:SSZ

Example:
2026-09-05T20:00:00Z
```

下一轮 Claude 很可能直接修正。

所以这里真正损失的不只是：

```text
一次失败调用
```

而是：

```text
失败以后缺少 recovery information
```

---

#### Error Result 也应该回答“下一步能做什么”

这和成功 Result 的原则其实完全一样。

成功时我们问：

> Claude 下一步需要什么信息？

失败时也应该问：

> Claude 下一步需要什么信息才能恢复？

例如一个文件路径不存在。

差的 Error：

```text
ENOENT
```

好一点：

```text
File not found:
src/auth/authentication.ts
```

更适合 Agent 的：

```text
File not found:
src/auth/authentication.ts

Closest matches:
- src/auth/auth.ts
- src/auth/authentication.test.ts

Use Glob or Grep if you are unsure of the path.
```

现在 Error 已经不是：

```text
异常描述
```

而是：

```text
Recovery Observation
```

---

#### Validation Error 特别适合这样做

Macro 1 里已经讲过：

```text
Schema
Validation
Permission
```

三层。

其中 Validation Failure 往往发生在：

```text
真正修改 Environment 之前
```

这其实是一个非常好的机会。

例如 Edit：

```text
old_string
```

没有找到。

如果只返回：

```text
Edit failed.
```

Claude 可能又提交一次差不多的 Edit。

如果返回：

```text
`old_string` was not found in src/auth.ts.

The file may have changed since you last read it.
Read the relevant section again before retrying the edit.
```

Harness 已经明确告诉 Model：

```text
为什么失败
+
下一步应该重新观察什么
```

于是 Loop：

```text
Edit
  ↓ fail
Read
  ↓ fresh state
Edit
```

很自然地形成。

---

#### Error 甚至可以给一个正确参数示例

Anthropic 在 Tool Engineering 文章里同样强调，与其给 Agent 不透明错误码或 Traceback，不如返回具体、可执行的修正信息，必要时直接展示一个正确格式的 Input Example。

例如：

```text
Invalid `user`.

Expected `user_id`, not a user name.

Example:
{
  "user_id": "U12345"
}

If you only know the person's name,
call `search_users` first.
```

这里其实一次解决了三个问题：

```text
当前哪里错了
↓
正确格式是什么
↓
缺信息时该调哪个 Tool
```

这比：

```text
INVALID_USER
```

对 Agent 有用得多。

---

#### 这里又出现了 Tool Result 对 Tool Routing 的反向影响

前面 Macro 2 讲：

```text
Tool Name
Tool Description
Namespace
```

会影响：

```text
Agent 选哪个 Tool
```

现在发现 Result 也能做到。

例如：

```text
send_message(name="Jane")
```

失败后 Tool 返回：

```text
`send_message` requires `user_id`.

Call `search_users` with the person's name first.
```

Model 下一步很自然：

```text
search_users(name="Jane")
```

所以 Agent 的 Action Selection 并不只由：

```text
Tool Definition
```

决定。

上一轮：

```text
Tool Result
```

也在不断 reshape 下一轮的 Action Distribution。

完整循环更像：

```text
Tool Definition
       ↓
Model chooses Action
       ↓
Tool executes
       ↓
Tool Result
       ↓
Result steers next Action
       ↓
Tool executes
       ↓
...
```

这就是为什么：

```text
Error message
```

完全可以是一种：

```text
Runtime Steering
```

---

#### 但这里也不能写成一大篇 Prompt

有了这个想法以后，很容易把每个 Error 写成：

```text
很抱歉，你这次操作失败了。
为了帮助你解决问题，请遵循以下步骤……
1.
2.
3.
4.
5.
...
```

然后 Error 本身又吃掉几百 Token。

没必要。

好的 Agent Error 往往只需要四样东西：

```text
What failed?
Why?
What constraint was violated?
What can I do next?
```

例如：

```text
Query returned 8,412 matches and exceeded the result limit.

Narrow the search with `path` or a more specific query.
Example:
{"query":"validateInput","path":"src/tools"}
```

已经足够。

---

#### Stack Trace 也不一定应该直接给 Model

传统开发 Tool 很喜欢：

```text
try/catch
→ 返回整个 Stack Trace
```

有时确实有价值。

如果 Claude 正在 Debug 这个 Tool 自身：

```text
Stack Trace
```

非常有帮助。

但如果 Claude 只是普通调用者，

内部：

```text
node_modules/...
SDK internals
HTTP client frames
runtime implementation
```

可能完全无助于恢复。

所以又回到了：

```text
Raw Error
     ↓
Harness mapping
     ↓
Agent-facing Error Observation
```

Runtime 可以保留完整 Stack Trace 给：

```text
log
telemetry
debug UI
```

同时给 Model 一个：

```text
结构化、可行动的错误
```

例如：

```json
{
  "error": "invalid_time_range",
  "message": "`start_time` must be earlier than `end_time`.",
  "retryable": true,
  "example": {
    "start_time": "2026-09-05T20:00:00Z",
    "end_time": "2026-09-05T21:00:00Z"
  }
}
```

这就是前面：

```text
Internal Runtime Representation
≠
Model Observation
```

在失败路径上的同一个设计。

---

#### 一个 Tool 的 Failure Mode 其实也是接口的一部分

普通 API 文档经常认真写：

```text
200
400
401
403
404
429
500
```

Agent Tool 也应该认真考虑自己的 Failure Surface。

比如：

```text
search_logs
```

可能失败在：

```text
Query syntax invalid
Time range too large
Service does not exist
Result set too large
Backend unavailable
Timeout
```

这些情况下一步策略并不一样：

```text
invalid query
→ 修改 query

time range too large
→ 缩小 range

service unknown
→ 列出 available services

result too large
→ filter / paginate

backend unavailable
→ retry later / switch strategy

timeout
→ narrow query
```

如果所有失败最后压成一个：

```text
ToolError
```

Model 又得自己猜。

所以 Tool Contract 设计里，我现在会把：

```text
Failure Observation
```

也当成正式接口。

---

#### 成功和失败其实都只是在告诉 Agent“世界现在是什么样”

这样回头看，成功 Result 和 Error Result 的区别没有想象中那么大。

成功：

```text
Found 3 files.
```

告诉 Claude：

```text
世界里有三个候选。
```

失败：

```text
Query is too broad; 8,412 matches.
```

也在告诉 Claude：

```text
世界比你这次 Observation Budget 能承载的大，
需要收窄。
```

成功：

```text
Edit applied.
```

告诉 Claude：

```text
文件状态已经改变。
```

失败：

```text
old_string no longer exists.
```

告诉 Claude：

```text
你脑子里的文件状态已经过期。
```

两者其实都是：

```text
Observation
```

只不过一个告诉 Agent：

```text
Action succeeded
```

另一个告诉 Agent：

```text
当前 Action 无法成立，以及为什么。
```

---

#### 所以 Macro 3 最后可以收成一个 Observation Pipeline

现在再看完整 Tool Loop：

```text
              Agent
                │
                │ Action
                ↓
        ┌───────────────┐
        │     Tool      │
        └───────┬───────┘
                │
                ↓
          Environment
                │
                │ Raw Result
                ↓
        ┌───────────────┐
        │    Harness    │
        │               │
        │ semantic      │
        │ filtering     │
        │ formatting    │
        │ pagination    │
        │ truncation    │
        │ error mapping │
        └───────┬───────┘
                │
                │ Observation
                ↓
              Agent
```

其中 Harness 做的已经不是简单：

```ts
JSON.stringify(result)
```

它正在决定：

```text
什么值得进入 Context？
用什么形式进入？
进入多少？
如果太多怎么办？
如果失败又该告诉 Model 什么？
```

于是：

```text
Tool Result Design
```

实际上就是：

```text
Context Construction
```

的一部分。

---

#### 到这里，我会把 Tool Engineering 和 Context Engineering 连成一条线

Macro 1 里我们得到：

```text
Tool
≈
Action Interface
+
Execution Contract
+
Observation Interface
```

Macro 2 展开了第一项：

```text
Action Interface
        ↓
Tool Set
        ↓
Agent Action Space
```

这一章则展开第三项：

```text
Observation Interface
        ↓
Tool Result
        ↓
Agent Observation Space
```

而 Observation Space 的设计目标并不是：

```text
尽可能完整地复刻 Environment
```

而更像：

```text
Environment
        ↓
select
filter
rank
format
bound
        ↓
Decision-useful Context
```

所以 Tool 其实一直夹在两个空间之间：

```text
        Model
          │
   Action │ Observation
          │
        Tool
          │
          │
     Environment
```

Tool Input 把自然语言意图压成可执行 Action。

Tool Output 再把巨大的 Environment State 压成可推理 Observation。

这两次转换，才是 Agent 真正和现实世界交换信息的 I/O Boundary。

而接下来还有一个问题没有解决：

> Claude 到底怎么知道这些 Tool 应该什么时候用、参数到底是什么意思？

名字已经在 Macro 2 讲过一部分。

下一章要继续拆：

```text
Description
Schema
Parameter semantics
```

因为对 LLM 来说，这些东西并不只是 API Documentation。

**它们本身就是 Prompt。**

## 4. Tool Description 其实也是 Prompt

### 4.1 模型到底从哪里知道一个 Tool 怎么用？

前面已经花了很长时间讨论：

```text
Tool Name
Tool Set
Tool Result
```

但一直有一个最基础的问题没有正面回答：

> Claude 第一次看到一个 Tool 时，凭什么知道它应该怎么用？

假设我刚给 Agent 接入一个从来没见过的内部系统：

```text
Acme Incident Platform
```

里面有个 Tool：

```text
search_incidents
```

Claude 不可能天生知道我们公司的：

```text
incident
```

到底指：

```text
线上事故？
客服投诉？
安全事件？
内部工单？
测试失败？
```

也不知道：

```text
severity = SEV2
```

在我们公司意味着什么。

更不知道：

```text
service
```

参数到底应该填：

```text
payment-api
```

还是：

```text
payments
```

甚至不知道：

```text
query
```

支持：

```text
自然语言
Lucene
SQL
正则表达式
```

中的哪一种。

这些东西都不在模型权重里。

它只能从当前 Context 里学。

而 Tool Definition 恰好就是它获得这些信息的主要入口之一。

---

#### 一个 Tool Definition 本来就长得很像 Prompt

最简单的 Tool Specification 大概会有：

```json
{
  "name": "search_incidents",
  "description": "Search incidents",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string"
      }
    }
  }
}
```

从 API 角度：

```text
Schema 正确。
```

Model 也确实能够调用。

但它真正知道的信息只有：

```text
有一个东西叫 search_incidents

它好像可以 search incidents

输入里有一个叫 query 的字符串
```

剩下全部得猜。

比如用户说：

> 看一下昨晚支付系统是不是又因为 Redis 出事故了。

Claude 可能生成：

```json
{
  "query": "Redis"
}
```

也可能：

```json
{
  "query": "payment Redis yesterday"
}
```

还可能把：

```text
昨晚
```

理解成 Query Language 的一部分，而不是应该单独设置：

```text
start_time
end_time
```

如果搜索效果不好，很容易得到一个结论：

> Model 不会用我们的 Tool。

但这里真正的问题可能只是：

```text
我们根本没教它。
```

Anthropic 在 Tool Engineering 文章里把这一节直接叫做：

```text
Prompt-engineering your tool descriptions
```

原因就在这里：Tool Description 和 Specification 会进入 Agent Context，它们会持续影响模型如何选择和调用 Tool。

---

#### 我现在更愿意把 Tool Description 当成“给新员工的交接文档”

Anthropic 给了一个很形象的思路：

> 写 Tool Description 时，想象你在给一个刚入职的新同事解释这个内部工具。

这个类比比：

```text
写 API 文档
```

更适合 Agent。

因为 API 文档经常默认读者已经知道大量 Domain Context。

例如公司内部开发者看到：

```text
customer
workspace
incident
deployment
run
```

脑子里已经自动补齐含义。

Claude 不一定有。

假设 Tool 写成：

```text
get_run
```

Description：

```text
Get a run.
```

这和没写差不多。

因为所谓：

```text
run
```

到底是：

```text
CI run
workflow run
model inference run
experiment run
deployment run
```

没有任何说明。

更好的版本可能是：

```text
Get one CI workflow run by its run ID.

A run represents one execution of the repository's CI workflow,
not an individual job inside the workflow.

Use this after `search_runs` when you need detailed logs,
job status, or failure information for a specific workflow run.
```

注意这里多出来的不只是：

```text
英语更详细
```

而是几类完全不同的信息：

```text
这个 Resource 是什么？
它不是什么？
什么时候应该调用？
通常接在哪个 Tool 后面？
能得到哪些下一步需要的信息？
```

Claude 原本缺失的 Domain Knowledge，被显式塞进了 Tool Interface。

---

#### Tool Description 最该补的是“人类默认知道，但模型不知道”的东西

这点非常容易被忽略。

比如：

```text
search_transactions
```

公司里的工程师都知道：

```text
Transaction
```

指的是：

```text
支付交易
```

而不是：

```text
数据库 Transaction
```

那么 Description 最好直接说：

```text
Search customer payment transactions.
```

而不是：

```text
Search transactions.
```

再比如：

```text
environment = prod
```

内部人员都知道：

```text
prod
staging
dev
```

Claude 也许猜得到。

但如果公司还有：

```text
canary
preprod
sandbox
dogfood
```

这时候枚举和值的含义最好直接写清楚。

例如：

```json
{
  "environment": {
    "type": "string",
    "enum": [
      "prod",
      "staging",
      "canary"
    ],
    "description": "Deployment environment. `canary` is the limited-production rollout environment used before full `prod` deployment."
  }
}
```

这样 Domain Knowledge 就不再依赖：

```text
模型碰巧知道
```

而变成：

```text
Tool contract 显式提供
```

---

#### Description 还应该讲清楚 Tool 之间的边界

Macro 2 讲过：

```text
search
find
lookup
retrieve
```

一堆意义重叠的 Tool 会让 Routing 变得很难。

即使名字已经 namespace 了，仍可能出现：

```text
github_issues_search

jira_issues_search
```

两个都能搜“问题”。

此时 Description 里最有价值的信息往往不是：

```text
Search issues in Jira.
```

而是：

```text
Use this for internal engineering work items,
incident follow-ups, sprint tasks, and bugs tracked by the company.

Do not use this for public GitHub issues.
Use `github_issues_search` for issues hosted in GitHub repositories.
```

为什么：

```text
Do not use...
```

也值得写？

因为 Agent Tool Selection 需要的不只是：

```text
Positive Affordance
```

还需要一定程度的：

```text
Boundary
```

也就是：

```text
什么时候用我？
什么时候别用我？
```

这样 Model 才能把几个相似 Action 分开。

Anthropic 在更早的 Agent Engineering 指南里也强调过：好的 Tool Definition 应包含清晰边界、输入格式、Example 和 Edge Case，而不是只给一个函数名。

---

#### 一个模糊参数名，会把不确定性直接传给模型

假设 Tool Schema：

```json
{
  "user": {
    "type": "string"
  }
}
```

这个：

```text
user
```

到底要填什么？

可能是：

```text
Jane
jane@example.com
U019283
用户名
显示名
邮箱
内部 UUID
```

程序员看过 SDK 文档以后自然知道。

Claude 只看到：

```text
user: string
```

只能猜。

Anthropic 在文章里专门用了这个例子：

```text
user
```

最好改成：

```text
user_id
```

因为第二个名字已经把一部分约束编码进了参数本身。

如果继续做得更明确：

```json
{
  "user_id": {
    "type": "string",
    "description": "Internal Slack user ID such as `U12345`. Do not pass a display name or email. Use `search_users` first if the ID is unknown."
  }
}
```

Model 现在知道：

```text
要什么
不要什么
不知道时怎么获得
```

三件事。

---

#### 好的 Schema 其实在减少 Model 需要推断的自由度

假设我设计一个删除文件 Tool：

```json
{
  "path": {
    "type": "string"
  },
  "recursive": {
    "type": "boolean"
  },
  "force": {
    "type": "boolean"
  },
  "mode": {
    "type": "string"
  }
}
```

这里每多一个开放参数，

Claude 就多一个决策：

```text
recursive 应该 true 吗？
force 呢？
mode 填什么？
```

如果实际上：

```text
mode
```

只有：

```text
trash
permanent
```

两个合法值，

那么不要让它猜字符串：

```json
{
  "mode": {
    "type": "string",
    "enum": [
      "trash",
      "permanent"
    ]
  }
}
```

如果产品绝大多数情况都应该：

```text
trash
```

甚至可以直接：

```text
默认 trash
```

再把永久删除设计成更明确的 Action。

这种思路在传统工业工程里有一个很老的词：

```text
poka-yoke
```

也就是所谓防错设计。

Anthropic 在早期 Agent Tool 指南里也直接使用过这个说法：

> 改变 Tool Arguments，让模型更难犯错。

例如他们在 SWE-bench Agent 中发现 Relative Path 容易造成错误，于是干脆让 Tool 要求 Absolute Path，把一种常见错误从 Prompt Reminder 变成接口约束。

这件事我很喜欢。

因为很多 Agent Prompt 都会写：

```text
Always use absolute paths.
```

模型大部分时候会听。

但如果：

```text
Schema / Runtime
```

本身就不接受 Relative Path，

系统就不再需要赌：

```text
这次它还记不记得。
```

---

#### 能进 Schema 的约束，就没必要全留在自然语言里

例如一个：

```text
search_logs
```

Tool。

差一点的 Schema：

```json
{
  "service": {
    "type": "string"
  },
  "level": {
    "type": "string"
  },
  "limit": {
    "type": "number"
  }
}
```

然后 Description 写：

```text
level must be DEBUG, INFO, WARN or ERROR.
limit must be between 1 and 100.
```

Model 能看懂。

可 Deterministic Runtime 也完全可以直接表达：

```json
{
  "level": {
    "type": "string",
    "enum": [
      "DEBUG",
      "INFO",
      "WARN",
      "ERROR"
    ]
  },
  "limit": {
    "type": "integer",
    "minimum": 1,
    "maximum": 100,
    "default": 20
  }
}
```

于是：

```text
Prompt
```

负责告诉 Model：

```text
为什么 / 什么时候
```

Schema 负责保证：

```text
结构上有哪些合法选择
```

两边各做自己最擅长的事。

---

#### 但 Schema 越严格，也不等于永远越好

这里又不能走到：

```text
所有东西都 Enum
```

的极端。

比如：

```text
search_code(query)
```

如果 Query 本来就需要自由表达：

```text
validateInput
"permission denied"
TODO
function foo
```

那：

```text
query: string
```

就是合理设计。

如果为了“约束模型”硬拆：

```text
symbol
keyword
phrase
regex
semantic_intent
```

Claude 在每次 Search 之前反而多了一个新的分类问题：

> 我这次到底算 keyword 还是 semantic_intent？

所以 Poka-yoke 的目标不是：

```text
限制越多越好
```

而是：

```text
把真实存在的确定性约束
变成机器可执行的边界。
```

仍然需要模型做的开放语义判断，就应该留给模型。

---

#### Example 很适合解释文字很难说清的格式

比如一个 Tool 接受：

```text
repository
```

Description 写：

```text
Repository name.
```

没说清楚应该是：

```text
Bubblevan/Hi-Agent
```

还是：

```text
Hi-Agent
```

或者：

```text
https://github.com/Bubblevan/Hi-Agent
```

一个 Example 可以瞬间解决：

```json
{
  "repository": "Bubblevan/Hi-Agent"
}
```

再比如：

```text
date_range
```

如果要求：

```text
YYYY-MM-DD..YYYY-MM-DD
```

最省事的解释之一就是直接放：

```text
Example:
2026-09-01..2026-09-06
```

这和给新员工一个：

```text
正确工单范例
```

非常像。

很多时候 Example 比再写三行抽象描述更有效。

---

#### 可 Tool Description 不能变成长篇 README

发现它是 Prompt 以后，另一个常见反应是：

> 那我把所有文档都塞进去。

于是：

```text
search_incidents
```

Description 长到两千字。

里面包含：

```text
Incident 历史
公司组织结构
所有 Severity 定义
完整 Query Language
十几个 Example
所有 Edge Case
所有错误码
```

一个 Tool 尚且如此。

几十个 Tool 一起加载：

```text
Tool Definitions
```

本身就开始吞 Context。

Macro 2 已经讲过：

```text
Tool Set
```

本身就是 Context Cost。

Description 也一样。

所以好的 Tool Prompt Engineering 不是：

```text
写得越多越好
```

而是：

```text
把真正影响 Tool Selection
和 Input Construction 的信息
写清楚。
```

至于：

```text
极其罕见的高级 Query Syntax
大段 Background
完整领域手册
```

可能更适合：

```text
按需文档
Resource
Skill
另一个 Help Tool
```

而不是每轮都塞进 Tool Definition。

---

#### 所以 Description 的信息密度比篇幅更重要

我现在如果 Review 一个 Tool Description，会问几个很具体的问题：

```text
Claude 能从名字知道它大概干什么吗？

Description 有没有告诉它什么时候应该用？

有没有和邻近 Tool 明确边界？

参数里有没有公司内部术语？

参数到底期待 name、ID、URL 还是 path？

有哪些常见格式错误可以直接通过 Schema 消掉？

如果必须遵循特殊 Query Syntax，有没有 Example？
```

而不是：

```text
Description 有没有写到 500 字？
```

---

#### Tool Prompt 最终还是要拿行为验证

Tool Description 最麻烦的地方和普通 Prompt 一样：

```text
写的人觉得很清楚
```

并不等于：

```text
模型真的按照预期理解
```

Anthropic 给过一个非常好的真实例子。

他们上线 Web Search Tool 时发现，Claude 会在没有必要的情况下：

```text
自动给搜索 Query 加上 2025
```

于是：

```text
OpenAI latest model
```

可能被模型改造成类似：

```text
OpenAI latest model 2025
```

搜索结果反而受到年份偏置。

这里 Backend 没坏。

Search Engine 也没坏。

Tool Call 格式甚至完全合法。

真正的问题在：

```text
Agent learned a bad calling behavior
```

最后 Anthropic 通过调整 Tool Description 来纠正这个行为。

这个例子特别适合说明：

```text
Tool Description
```

不只是开发者文档。

如果：

```text
改 Description
→
Tool Call Distribution 改变
→
Task Performance 改变
```

它就已经在做 Prompt Engineering。

---

#### Tool Description 和 System Prompt 其实是两种不同粒度的 Steering

假设我想告诉 Claude：

> 搜索时不要无意义地加年份。

可以写进 System Prompt：

```text
When searching the web, do not append years unless necessary.
```

也可以写进：

```text
WebSearch Tool Description
```

后者通常更局部：

```text
只有在模型考虑 WebSearch 时出现这个约束。
```

这其实是一种很好的职责分层。

System Prompt 适合：

```text
整个 Agent 都需要遵守的行为
```

例如：

```text
尊重用户权限
不要伪造执行结果
使用工具验证可验证事实
```

Tool Description 更适合：

```text
这个 Action 特有的操作语义
```

例如：

```text
Query 应该怎么写
什么时候不要调用
哪个参数是什么
这个 Resource 在公司里代表什么
```

如果所有 Tool-specific Knowledge 都塞到 System Prompt：

```text
Global Prompt
```

会越来越胖。

反过来，把全局安全规则都偷偷藏进某个 Tool Description 也不合理。

所以：

```text
System Prompt
      ↓
Agent-wide policy

Tool Description
      ↓
Action-local policy
```

两者都是 Prompt Surface，

但作用范围不同。

---

#### 到这里，Tool Spec 已经在承担一部分“局部程序语言”的职责

例如：

```json
{
  "tool": "search_logs",
  "input": {
    "service": "payment-api",
    "level": "ERROR",
    "start_time": "2026-09-05T20:00:00Z",
    "limit": 20
  }
}
```

Tool Definition 实际上在教 Claude 一套小语言：

```text
动作：
search_logs

参数：
service
level
start_time
limit

合法 level：
DEBUG / INFO / WARN / ERROR

时间：
ISO-8601

默认 limit：
20
```

从这个角度：

```text
Tool Description + Schema
```

正在把开放的：

```text
用户自然语言
```

映射成一个小型：

```text
Domain-specific Action Language
```

Model 负责完成：

```text
Natural Language
      ↓
Structured Action
```

而这套 Action Language 设计得好不好，会直接影响模型能不能稳定地编译过去。

---

#### 但还有一个问题：模型完全按照 Schema 生成了参数，也可能照样不能执行

比如 Claude 生成：

```json
{
  "file_path": "/workspace/project/src/auth.ts",
  "old_string": "return true",
  "new_string": "return false"
}
```

所有字段：

```text
类型正确
名字正确
格式正确
```

Tool Description 也没有被误解。

但真实文件里：

```text
return true
```

已经不存在了。

这时候不能再靠：

```text
Prompt Engineering
```

解决。

我们开始进入另外一种边界：

```text
Runtime Validation
```

也就是上一章已经出现过、现在需要正式拆清楚的：

```text
Schema
Validation
Permission
```

三层。

---

### 4.2 Schema 合法、动作成立、获得授权为什么是三件事？

拿一个最简单的 Edit 来说。

Model 输出：

```json
{
  "file_path": "/workspace/src/auth.ts",
  "old_string": "return true",
  "new_string": "return false"
}
```

如果 Tool 的 Schema 是：

```text
file_path: string
old_string: string
new_string: string
```

那么这次 Tool Call：

```text
100% Schema Valid
```

可真实世界里仍然有很多种可能：

```text
文件不存在

old_string 不存在

old_string 出现了五次

文件已经被另一个过程修改

当前 Workspace 不包含这个文件

当前用户没有权限修改

当前 Permission Mode 要求先询问
```

如果把这些全部统称成：

```text
invalid tool call
```

很多完全不同的问题就混在一起了。

Claude Code v2.1.88 的 `Tool` contract 之所以把：

```text
inputSchema
validateInput(...)
checkPermissions(...)
```

拆开，正好可以用来理解这三层边界。

---

#### 第一层：Schema 只判断“这句话有没有说成合法语法”

还是刚才的：

```json
{
  "file_path": "/workspace/src/auth.ts",
  "old_string": "return true",
  "new_string": "return false"
}
```

Schema 能检查：

```text
file_path 是不是 string？
old_string 有没有？
new_string 是不是正确类型？
有没有未知字段？
Enum 值合法吗？
数字范围合法吗？
```

也就是：

```text
Syntax / Shape
```

如果 Model 输出：

```json
{
  "file_path": 123,
  "old_string": null
}
```

这里甚至不需要访问文件系统。

Runtime 已经知道：

```text
这个 Action 表达不合法。
```

可以直接拒绝。

这和编译器里的：

```text
Parsing / Type Checking
```

有一点类比关系。

注意只是类比。

我并不是说 JSON Schema 就是一门完整编程语言的 Type System。

重点只是：

```text
错误在接触真实环境之前
已经可以确定。
```

---

#### 第二层：Validation 判断“这个动作在当前世界里成立吗”

现在参数长得完全正确：

```json
{
  "file_path": "/workspace/src/auth.ts",
  "old_string": "return true",
  "new_string": "return false"
}
```

Runtime 打开：

```text
/workspace/src/auth.ts
```

发现里面根本没有：

```text
return true
```

那么：

```text
Schema
```

没有任何问题。

可：

```text
Edit 这个动作
```

在当前 Environment State 下无法成立。

这是：

```text
Semantic / Runtime Validation
```

的问题。

Claude Code 的 Tool contract 中因此存在类似：

```ts
validateInput(...)
```

的边界。

它考虑的已经不只是：

```text
input
```

还可能需要：

```text
current context
current workspace
current resource state
```

因为动作是否合法依赖世界现在是什么样。

---

#### 这正是 Agent 特别容易碰到的“世界已经变了”

传统函数调用时，程序往往很快：

```text
read
→
compute
→
write
```

Agent 却可能经历：

```text
Read file
   ↓
Reason
   ↓
Search another file
   ↓
Run tests
   ↓
Reason
   ↓
Edit original file
```

中间可能过去：

```text
几十秒
几分钟
很多 Tool Calls
```

Environment 完全可能变化。

例如：

```text
其他 Agent 改了文件

用户自己改了文件

测试生成了新文件

Git checkout 改变 Working Tree

外部 API 状态变化
```

于是 Model Context 里记得的：

```text
World State_t
```

不一定等于实际执行时的：

```text
World State_t+n
```

Validation 就在检查：

```text
你基于旧 Observation 提出的 Action，
现在还成立吗？
```

---

#### `old_string` 不存在，其实是在告诉 Claude：你的 Context 过期了

这个 Error 很适合重新理解。

普通 Editor API 会说：

```text
string not found
```

Agent Runtime 可以把它理解成：

```text
Model's belief about environment
        ≠
Current environment
```

于是正确恢复动作不是：

```text
再盲改一次
```

而是：

```text
重新 Read
   ↓
获得最新 Observation
   ↓
重新 Construct Action
```

也就是：

```text
Validation Failure
      ↓
refresh state
      ↓
retry
```

这和 Macro 3 讲的：

```text
Error as Recovery Observation
```

正好接上。

---

#### Schema 和 Validation 的边界不能倒过来

假设：

```text
limit
```

只允许：

```text
1 ~ 100
```

却没有写进 Schema，

而是在：

```ts
validateInput()
```

里判断。

系统当然也能工作。

但 Model 本来可以在生成阶段就知道：

```text
1000
```

是不合法的。

现在它只能：

```text
生成 1000
→ Tool Call
→ Runtime reject
→ Error 回 Context
→ 再生成 100
```

白白多了一轮。

所以能够静态表达的约束：

```text
type
enum
required
minimum
maximum
format
```

最好尽量留在 Schema。

而真正依赖 Runtime State 的：

```text
文件是否存在
资源是否仍有效
old_string 是否匹配
branch 是否存在
record 是否已删除
```

才属于 Validation。

可以简单记成：

```text
Schema
=
不看真实世界也能判断

Validation
=
必须看看真实世界现在是什么样
```

这比：

```text
Schema = 基础检查
Validation = 高级检查
```

更容易区分。

---

#### 可 Action 合法以后，还有第三个问题没有回答

比如：

```text
Bash("git push origin main")
```

Schema：

```text
command: string
```

当然合法。

Runtime：

```text
git
remote
branch
```

也都存在。

所以：

```text
Validation = pass
```

是不是就执行？

这里马上碰到：

```text
Authorization
```

问题。

因为：

```text
能执行
```

和：

```text
被允许执行
```

不是一件事。

---

#### Permission 检查的是 Principal 对 Action 的授权关系

可以抽象成：

```text
Capability
   ↓
系统会做 git push

Validity
   ↓
这个 git push 当前确实能做

Authorization
   ↓
这次调用者被允许做吗？
```

比如：

```text
git status
```

可能：

```text
allow
```

而：

```text
git push
```

可能：

```text
ask
```

再比如：

```text
rm -rf build/
```

在某种配置里允许；

```text
rm -rf /
```

则直接：

```text
deny
```

所以：

```text
Permission
```

问的是完全不同的问题：

> **即使这个 Action 技术上成立，我们是否允许当前 Agent 在当前 Policy 下执行？**

---

#### Capability ≠ Authorization 是我觉得面试里一定要说清楚的一句话

例如 Model Context 里存在：

```text
Bash Tool
```

只能证明：

```text
Claude 知道系统具有 Shell Capability
```

不能推出：

```text
Claude 的所有 Bash(input)
都已经获得授权
```

如果这两个概念混掉：

```text
Tool available
=
Tool call allowed
```

那最简单的权限系统就是：

```text
危险 Tool 全部不要给 Model
```

可这又会损失大量正常 Capability。

例如 Bash 同时承担：

```text
pwd
git status
pytest
rm
git push
curl
```

不可能简单写：

```text
Bash = dangerous
```

所以 Production Harness 更需要针对：

```text
concrete action
```

做 Permission Decision。

这部分你在：

```text
security.md
```

里会展开：

```text
allow
deny
ask
sandbox
permission mode
auto mode
```

`tools.md` 这里只需要把层次留清楚。

---

#### Permission 也不能和 Validation 混在一起

想象这两个错误：

```text
File does not exist.
```

和：

```text
You are not permitted to modify this file.
```

对 Agent 来说，恢复策略完全不同。

第一个：

```text
重新搜索正确文件
```

可能就解决。

第二个：

```text
换一个文件名
```

不应该成为绕过权限的办法。

如果都压成：

```text
Edit failed
```

Claude 不知道自己该：

```text
修参数
重新观察
询问用户
还是彻底停止
```

所以 Error Type 本身最好保留：

```text
Validation Failure
```

和：

```text
Permission Denial
```

的语义区别。

---

#### 三层边界最终对应三种不同的 Recovery

可以直接画成：

```text
Tool Call
   │
   ↓
Schema
   │
   ├── fail
   │     ↓
   │   修正参数结构
   │
   ↓ pass
Validation
   │
   ├── fail
   │     ↓
   │   刷新环境 / 修正语义
   │
   ↓ pass
Permission
   │
   ├── ask
   │     ↓
   │   请求用户批准
   │
   ├── deny
   │     ↓
   │   不执行
   │
   ↓ allow
Execution
```

例如：

```text
Schema Failure
```

可能是：

```text
limit = "many"
```

恢复：

```text
改成 integer
```

---

```text
Validation Failure
```

可能是：

```text
file does not exist
```

恢复：

```text
重新 Glob / Grep
```

---

```text
Permission Ask
```

可能是：

```text
git push
```

恢复：

```text
等待用户授权
```

---

```text
Permission Deny
```

则意味着：

```text
不能通过重复 Tool Call 来“试试看”
```

这就是为什么把三种 Error 分开，对 Agent Loop 本身都有价值。

---

#### Tool Description 解决不了 Runtime Truth

这里还可以顺便划清：

```text
Prompt Engineering
```

的边界。

假设我们在 Description 里写：

```text
Only edit files that exist.
```

看起来合理。

可 Model 无法永远保证：

```text
执行瞬间文件一定存在。
```

因为 Environment 会变。

又比如：

```text
Only modify files you have permission to edit.
```

Model 也未必知道真实 Permission State。

所以一些规则虽然可以：

```text
Prompt 提醒
```

却仍必须：

```text
Runtime enforce
```

这也是 Harness Engineering 和单纯 Prompt Engineering 的区别之一。

Prompt 能：

```text
steer behavior
```

Runtime 则能：

```text
enforce invariant
```

---

#### 我现在会把约束按“谁最适合负责”分层

比如：

```text
“这个参数代表 Slack user ID”
```

适合：

```text
Description
+
parameter name
```

---

```text
“user_id 必须是 string”
```

适合：

```text
Schema
```

---

```text
“这个 user_id 当前是否存在”
```

适合：

```text
Validation
```

---

```text
“当前 Agent 是否允许给这个用户发消息”
```

适合：

```text
Permission
```

---

```text
“发送以后返回什么给 Model”
```

适合：

```text
Result Mapping
```

这样整个 Tool Boundary 会非常清楚：

```text
Description
    ↓
How should the model think about this action?

Schema
    ↓
Can this action be expressed this way?

Validation
    ↓
Does this action make sense in the current world?

Permission
    ↓
Is this action authorized?

Execution
    ↓
Perform effect

Result Mapping
    ↓
What should the model observe afterward?
```

---

#### 这比“所有规则都写 Prompt”稳定得多

假设我做一个生产 Agent，System Prompt 写：

```text
Never delete important files.

Only use valid paths.

Do not modify files without permission.

Avoid destructive commands.

Do not run multiple conflicting commands at once.
```

这些提醒当然有用。

但它们有几个共同问题：

```text
什么叫 important？
什么叫 valid？
permission 当前是什么？
哪些 command 冲突？
```

很多东西明明可以由确定性 Runtime 判断，

却全部推给 LLM。

这实际上是在：

```text
用概率系统维护系统不变量
```

风险很高。

更合理的是：

```text
Prompt
→ 提供意图层 Steering

Schema
→ 结构约束

Validation
→ Runtime Truth

Permission
→ Authorization

Effect Metadata
→ Scheduling / Safety
```

让 Model 和 Harness 各自承担自己擅长的工作。

---

#### 这也是 Tool Contract 为什么会越长越像一个“小协议”

最开始我们的 Tool 只有：

```ts
async function tool(input) {
  return output
}
```

现在已经变成：

```text
Model-facing
├── name
├── description
└── schema

Runtime-facing
├── validation
├── permission
├── execution
└── result mapping
```

但还有几个字段没有解释完：

```text
isReadOnly(input)

isDestructive(input)

isConcurrencySafe(input)

interruptBehavior()
```

这些既不是：

```text
Prompt
```

也不是：

```text
Input Validation
```

它们在回答另一类问题：

> **这一次 Action 会对世界产生什么 Effect，而 Runtime 应该怎样安排它？**

这就是下一章真正要进入的地方。

---

## 5. Tool 进入 Runtime 后还需要 Effect Semantics

### 5.1 为什么 `execute(input)` 远远不够？

到上一节为止，Tool Call 已经通过了三道门：

```text
Schema
  ↓
参数结构正确

Validation
  ↓
动作在当前环境中成立

Permission
  ↓
当前策略允许执行
```

看起来接下来终于可以：

```ts
await tool.execute(input)
```

然后收工。

但只要一次 Model Response 里出现多个 Tool Call，或者 Tool 执行时间稍微长一点，新的问题马上冒出来。

假设 Claude 给出：

```text
Read(package.json)
Read(tsconfig.json)
Bash("git status")
```

Harness 会想：

> 这三个能不能一起跑？

换成：

```text
Edit(package.json)
Bash("npm install")
Bash("npm test")
```

又会想：

> `npm test` 应该看到 install 之前还是之后的环境？

再换一个长时间命令：

```text
Bash("pytest")
```

运行到一半，用户突然发：

> 算了，先别跑了，我知道问题在哪。

Harness 还得决定：

```text
杀掉 pytest？
还是让它跑完？
Tool Result 还要不要交给 Model？
新消息什么时候进入 Agent Loop？
```

这些问题和：

```text
input → output
```

已经没多少关系了。

它们问的是：

> **这个 Action 会怎样影响 Environment，以及 Runtime 应该怎样围绕这个 Effect 安排它。**

所以生产 Tool 除了“怎么执行”，还需要一组 **Effect Semantics**。

---

#### `call()` 只负责做事，却不能告诉 Runtime 这件事意味着什么

把 Tool 简化成：

```ts
interface Tool {
  execute(input: unknown): Promise<unknown>
}
```

确实可以完成 Function Calling。

Model 生成：

```text
tool_use
```

Harness 找函数：

```text
tool_use.name
    ↓
execute(input)
```

然后把结果返回：

```text
tool_result
```

一个小 Demo 足够了。

真正的问题出现在 Tool 外面的系统开始需要做决策。

比如调度器拿到：

```text
Bash("git status")
```

和：

```text
Bash("npm install")
```

如果 Tool 只有：

```ts
execute(input)
```

调度器能看到的最多是：

```text
name = Bash
input = string
```

它不知道两次 Action 的副作用完全不同。

于是上层只能自己写：

```ts
if (tool.name === "Bash") {
  // 再解析一次 command
}
```

Permission 模块也解析一次。

并发调度器再解析一次。

UI 再根据 Tool Name 猜一次。

最后代码库里到处都是：

```text
if Bash ...
if Edit ...
if Read ...
```

每个 subsystem 都在重新理解同一个 Action。

Claude Code 当前这份 v2.1.88 恢复源码走的是另一条路线：

```text
Tool
不仅知道 how to execute

还主动声明：
what kind of effect this action has
```

也就是把动作语义留在 Tool Contract 附近，再让 Harness 的其他部分消费。

---

#### 最直观的三个 Effect 字段，不是同一件事

在这份 `Tool` contract 里，可以看到类似：

```ts
isReadOnly(input): boolean

isDestructive?(input): boolean

isConcurrencySafe(input): boolean
```

第一眼很容易把它们压成：

```text
safe / dangerous
```

两类。

但这三个字段回答的其实是不同问题。

---

`isReadOnly(input)` 问：

> **这次 Action 会不会修改状态？**

例如：

```text
Read("src/auth.ts")
```

明显接近：

```text
read-only
```

而：

```text
Edit("src/auth.ts", ...)
```

则不是。

---

`isDestructive(input)` 问的是更窄的一件事：

> **这次 Action 是否具有删除、覆盖、发送等更难恢复的破坏性 Effect？**

所以：

```text
not read-only
```

并不自动等于：

```text
destructive
```

例如：

```text
创建一个新的临时文件
```

当然修改了 Environment：

```text
isReadOnly = false
```

但它未必属于：

```text
delete
overwrite
send
```

这种更难回退的操作。

于是：

```text
Read-only?
```

和：

```text
Destructive?
```

其实是两条坐标轴。

不是：

```text
safe
dangerous
```

的一维刻度。

---

`isConcurrencySafe(input)` 又在问第三件事：

> **这次 Action 和其他 Action 同时运行，会不会破坏原本的执行语义？**

这和前两个字段依旧不能画等号。

例如理论上某个 Tool：

```text
只读取共享 Session Cursor
```

没有写文件。

但多个调用如果同时移动、消费或者依赖同一个 Cursor，依然可能不适合并发。

所以：

```text
read-only
≠
concurrency-safe
```

反过来也存在一种理论情况：

```text
Write(file_a)
Write(file_b)
```

两个 Action 都不是 read-only。

可如果它们修改完全独立的 Resource，而且 Runtime 能确认没有共享状态，就未必天然无法并发。

所以这里已经不是：

```text
Tool Type Classification
```

而更接近：

```text
Effect Classification
```

---

#### 为什么这些方法还要接收具体 `input`？

这里是我觉得最值得保留的源码细节之一。

接口没有只写：

```ts
isReadOnly(): boolean
```

而是允许：

```ts
isReadOnly(input): boolean
```

类似地：

```ts
isConcurrencySafe(input)
isDestructive(input)
```

判断的对象不是抽象：

```text
Bash
```

而是：

```text
Bash("这一条具体 command")
```

拿 Bash 最容易看出来。

下面这些全属于：

```text
Bash
```

```bash
pwd
git status
grep -R "validateInput" src/
```

但它们和：

```bash
rm foo.txt
npm install
git commit -am "fix"
```

对真实 Environment 的意义显然不同。

所以如果 Harness 只做：

```text
Bash = write
```

会非常粗糙。

做：

```text
Bash = read-only
```

当然更离谱。

更合理的分类过程是：

```text
Tool identity
     +
Concrete input
     +
Runtime knowledge
     ↓
Effect semantics
```

这和 Macro 4 的：

```text
Schema
Validation
Permission
```

也能接起来。

Tool Runtime 不是只理解：

```text
“模型调用了 Bash”
```

而是在逐渐理解：

```text
“模型现在想执行这一条 Bash Command，
它在当前 Runtime 里意味着什么？”
```

---

#### 这其实很像数据库里“我要知道这个操作碰了什么状态”

假设只有：

```text
Read(file_a)
Read(file_b)
```

两个动作。

我们很自然会觉得可以：

```text
parallel
```

因为它们大体只观察状态。

但：

```text
Edit(file_a)
Read(file_a)
```

就开始出现一个：

```text
happens-before
```

问题：

```text
Read
```

到底应该看到：

```text
Edit 前
```

还是：

```text
Edit 后
```

如果 Model 原本给出的顺序是：

```text
Edit(file_a)
Read(file_a)
```

那这个顺序已经带了一层语义。

再比如：

```text
Bash("npm install")
Bash("npm test")
```

第二个命令明显更希望观察：

```text
npm install
```

完成后的 Environment。

所以 Runtime 不能把所有 Action 只理解成：

```text
Promise
```

它还得知道这些 Promise 背后可能存在：

```text
filesystem state
process state
repository state
runtime context
external service state
```

的读写关系。

---

#### 我不会把 Claude Code 硬说成实现了形式化 Effect System

写到这里很容易上价值：

> Claude Code 实现了一套 Effect System。

我觉得这样反而过头了。

编程语言里的 Effect System 往往有更严格的：

```text
type rules
effect inference
formal semantics
```

甚至静态证明。

这里看到的更像一种工程化的：

```text
effect metadata
```

或者：

```text
effect-aware runtime contract
```

Tool 主动声明：

```text
read-only?
destructive?
concurrency-safe?
interruptible?
```

Harness 再根据这些 metadata 做：

```text
permission
scheduling
interaction
```

决策。

这个说法已经足够。

没必要为了显得高级硬套理论。

---

#### `buildTool()` 的默认值也很值得看，因为它暴露了“不知道怎么办”

真正的生产接口除了：

```text
显式配置
```

还要处理：

```text
Tool 没有告诉我怎么办？
```

你当前恢复源码里的 `buildTool()` 给了一组默认行为，大致包括：

```ts
isEnabled: () => true

isConcurrencySafe: () => false

isReadOnly: () => false

isDestructive: () => false
```

这里很容易读错。

最值得注意的是前两条 Effect 默认：

```text
不知道能不能并发
→ 不给并发优化

不知道是不是只读
→ 不把它当只读
```

这是一种很典型的：

```text
conservative classification
```

也就是：

> **没有正面证据时，不假设拥有更强的安全属性。**

但不能进一步脑补成：

```text
所有东西默认 dangerous
所有 permission 默认 deny
```

因为源码不是这样。

例如 Tool-specific `checkPermissions` 的默认行为并不是简单 Deny，而是允许这层通过，再把通用授权问题交给 general permission system。

所以不能把整个 Runtime 的默认值概括成：

```text
fail closed everywhere
```

更准确的理解是：

```text
不同 Effect Dimension
有不同默认策略。
```

---

#### `isReadOnly = false`，为什么 `isDestructive` 却默认 `false`？

这个细节刚看到时很容易觉得矛盾。

如果 Runtime 不知道一个 Tool 是不是只读：

```text
isReadOnly = false
```

也就是保守地当它：

```text
可能会写
```

那为什么不知道它是否 destructive 时：

```text
isDestructive = false
```

而不是：

```text
true
```

？

因为两者根本不是同一个 Boolean 的正反面。

可以画成：

| Action       | Read-only | Destructive |
| ------------ | --------: | ----------: |
| `Read(file)` |      true |       false |
| 创建新文件        |     false |       false |
| 修改普通文件       |     false |       视语义而定 |
| 覆盖重要状态       |     false |        true |
| 删除资源         |     false |        true |
| 发送不可撤回消息     |     false |        true |

所以：

```text
not read-only
```

表达的是：

```text
有写 Effect
```

而：

```text
destructive
```

表达的是更具体的：

```text
具有某类高风险、不可逆 Effect
```

这种拆法比：

```text
safe / dangerous
```

二分类好用得多。

---

#### Effect Metadata 还有一个完全不同的方向：Interaction

再看：

```ts
interruptBehavior?(): "cancel" | "block"
```

这个字段和文件读写没有直接关系。

它处理的是：

> Tool 运行过程中，用户又发来消息怎么办？

例如 Claude 正在：

```text
Bash("pytest")
```

用户突然：

> 停，不用测了，我刚发现配置文件写错了。

如果 Tool 是：

```text
cancel
```

那么 Harness 可以倾向于：

```text
停止 Tool
丢弃/处理未完成结果
尽快响应用户新意图
```

如果是：

```text
block
```

则意味着：

```text
先让当前 Tool 完成
再消费新消息
```

为什么这件事会进入 Tool Contract？

因为不同 Action 的中断语义可能不同。

一个纯读取动作被取消，通常比较简单。

某些已经开始提交外部 Effect 的动作却不能假装：

```text
AbortController.abort()
```

以后世界就自动回到了执行前。

比如：

```text
发送消息
发起支付
提交 deployment
修改远程资源
```

动作可能已经越过某个不可逆点。

这时候：

```text
cancel Promise
```

和：

```text
cancel real-world effect
```

完全不是一件事。

所以 interactive Agent Runtime 还必须考虑：

```text
User Interrupt
      ↓
Tool-specific semantics
      ↓
cancel / block / recovery
```

这也是普通 Function Calling Demo 很少碰到、长时间 Agent Session 却迟早会碰到的东西。

---

#### `call()` 反而只是整个生命周期的中间一步

现在再看 Tool 的执行过程：

```text
Model
  ↓
tool_use
  ↓
Schema
  ↓
Validation
  ↓
Permission
  ↓
Effect classification
  ↓
Scheduling decision
  ↓
call()
  ↓
Environment changes
  ↓
ToolResult
  ↓
Observation mapping
  ↓
Model
```

真正的：

```ts
call(...)
```

只在中间。

它当然不可缺。

但它不再足以定义：

```text
这个 Tool 在 Agent Runtime 里是什么。
```

所以一个生产 Tool 更像：

```text
Capability
+
Input Contract
+
Runtime Validation
+
Authorization Hook
+
Effect Metadata
+
Execution
+
Observation Mapping
+
Interaction Semantics
```

这不是严格数学公式。

只是比：

```text
Tool = function
```

更接近 Claude Code 这类 Harness 真正在实现的东西。

---

#### 为什么把 Effect 放进 Tool，而不是全部塞进 Scheduler？

还有一个架构问题。

既然：

```text
isConcurrencySafe
```

最后是 Scheduler 要用，

为什么不直接让 Scheduler 写：

```ts
if (toolName === "Read") return true
if (toolName === "Edit") return false
...
```

？

短期当然可以。

Tool 少的时候甚至很省事。

问题是 Scheduler 会慢慢变成：

```text
世界上所有 Tool 语义的百科全书
```

新增一个 MCP Tool，还要同时去改：

```text
Permission layer
Scheduler
UI
Interrupt layer
Result layer
```

Tool Contract 则允许反过来：

```text
Tool
  ↓ declares
its own runtime semantics

Harness
  ↓ consumes
uniform interface
```

这样调度器只需要理解：

```text
isConcurrencySafe(input)
```

而不需要理解：

```text
为什么某条 Bash 是 safe
为什么某个 MCP Read 不是 safe
为什么某个远程 Query 需要串行
```

换句话说：

```text
Scheduler
```

应该做：

```text
调度
```

而不是：

```text
重新推断每种 Tool 的业务语义。
```

---

#### 这也解释了为什么 Tool Contract 看起来会“胖”

如果只看：

```ts
execute()
```

其他字段都像：

```text
多余的 OO ceremony
```

但把实际参与者摆出来：

```text
Model

Permission System

Scheduler

Interactive Session Runtime

Environment

Context Manager

Human UI
```

会发现大家都需要知道同一个 Action 的不同侧面。

所以 Tool 恰好成了几条边界交汇的位置：

```text
                     Model
                       │
                 Action Interface
                       │
                       ▼
                  ┌─────────┐
Permission ──────→│  Tool   │←──── Scheduler
                  └────┬────┘
                       │
                    Effect
                       │
                       ▼
                  Environment
                       │
                    Result
                       ▼
                  Observation
                       │
                       ▼
                     Model
```

它不是因为代码写得“面向对象”才变厚。

而是 Agent Tool 本来就在：

```text
概率模型
确定性 Runtime
真实 Environment
人类交互
```

几个世界的交叉点上。

---

#### Effect Semantics 真正派上用场的地方，是 Model 一次给出多个 Action

如果永远只有：

```text
一个 Tool Call
执行完
再问 Model
```

那么：

```text
isConcurrencySafe
```

存在感不会很强。

一旦 Model 一次返回：

```text
Read(a.ts)
Read(b.ts)
Read(c.ts)
```

Runtime 很自然地想利用并发。

毕竟：

```text
串行：
A ───→ B ───→ C

并发：
A ──────────┐
B ──────────┼→
C ──────────┘
```

延迟差距可能很明显。

问题是：

```text
多个 Tool Call
```

并不自动等于：

```text
多个 Independent Task
```

这就是下一 Beat 真正要解决的事情。

---

### 5.2 为什么并发不是 `Promise.all(toolCalls)`？

先看最舒服的一组调用：

```text
Read(a.ts)
Read(b.ts)
Read(c.ts)
```

如果每次读取各花：

```text
500 ms
```

串行大约：

```text
1.5 s
```

同时启动则接近：

```text
0.5 s + overhead
```

所以最自然的代码就是：

```ts
await Promise.all(
  toolCalls.map(runTool)
)
```

然后 Model 下一次返回：

```text
Edit(package.json)
Bash("npm install")
Bash("npm test")
```

如果还这么做：

```text
Edit ─────────────┐
npm install ──────┼──→ simultaneously
npm test ─────────┘
```

测试到底看到：

```text
旧 package.json？
新 package.json？
install 前的 node_modules？
install 中间状态？
```

已经说不清了。

所以真正的问题不是：

> JavaScript 怎么并发 Promise？

而是：

> **谁来证明这一组具体 Action 可以同时发生？**

---

#### Model 把多个 `tool_use` 放在同一个 Response，不等于它给出了并发证明

一个 Assistant Response 里完全可以有：

```text
tool_use A
tool_use B
tool_use C
```

这只能说明：

```text
在同一个 Model State 下，
Claude 提出了 A、B、C。
```

不能推出：

```text
A、B、C 相互独立。
```

更不能推出：

```text
A、B、C 可以任意重排。
```

举个很简单的序列：

```text
Read(config)
Edit(config)
Read(config)
```

第一个 Read 想看到：

```text
旧 config
```

第二个 Read 很可能想看到：

```text
Edit 后的新 config
```

虽然两个：

```text
Read
```

单独看都非常安全，

也绝不能把它们抽出来做：

```text
Read #1 ──┐
Read #2 ──┴→ parallel
    ↓
Edit
```

因为这已经改变 Model 原始 Action Sequence 的含义。

所以：

```text
same response
≠
same concurrent batch
```

---

#### Claude Code 先做 `partition`，再决定怎么执行

在你当前这份 `toolOrchestration.ts` 恢复代码里，核心入口：

```ts
runTools(...)
```

并没有马上把整个：

```text
toolUseMessages
```

扔进一个并发池。

它会先经过：

```ts
partitionToolCalls(...)
```

抽象起来更像：

```text
Model output
A B C D E F
      ↓
Effect classification
      ↓
partition
      ↓
[A B] → [C] → [D E] → [F]
```

其中：

```text
[A B]
[D E]
```

可能作为 concurrent batch，

而：

```text
[C]
[F]
```

形成 serial barrier。

这里有一个特别值得记住的设计：

> **并发发生在 batch 内；batch 本身仍按照原始顺序推进。**

不是：

```text
把所有安全 Tool 抽出来一起跑
```

---

#### 分类先依赖 Schema Parse，再调用 `isConcurrencySafe(parsedInput)`

你旧稿里恢复出的核心逻辑大致是：

```ts
const tool = findToolByName(...)

const parsedInput =
  tool?.inputSchema.safeParse(toolUse.input)

const isConcurrencySafe =
  parsedInput?.success
    ? (() => {
        try {
          return Boolean(
            tool?.isConcurrencySafe(parsedInput.data)
          )
        } catch {
          return false
        }
      })()
    : false
```

这几行其实把前面几个 Macro 串起来了。

首先：

```text
Tool Name
```

还不够。

要先得到具体 Tool。

然后：

```text
raw model input
```

也不能直接拿去做 Effect 判断。

先：

```text
Schema parse
```

得到 Tool 真正理解的：

```text
parsed input
```

最后才问：

```text
isConcurrencySafe(parsedInput)
```

所以并发判断单位是：

```text
Tool
+
Concrete parsed input
```

而不是：

```text
Tool name
```

---

#### `Read → parallel，Write → serial` 只是一个近似，不能当实现规则

解释 Agent 并发时很容易写：

```text
Read Tool 并发
Write Tool 串行
```

作为第一层直觉没有问题。

但如果把它写成 Claude Code 实现事实，就过于粗糙。

更准确的是：

```text
isConcurrencySafe(input) = true
→ concurrent candidate

otherwise
→ serial
```

为什么不能直接等价于：

```text
read-only?
```

前一 Beat 已经讲过：

```text
read-only
```

回答：

> 会不会写状态？

而：

```text
concurrency-safe
```

回答：

> 与其他当前 Action 同时运行，会不会破坏预期语义？

它们相关，但不是同义词。

所以：

```text
Read/Write
```

更像一种 Effect Dimension。

```text
Concurrency Safety
```

是另一种。

---

#### Parse 失败时为什么直接走串行？

源码里有一个很工程化的选择：

```text
parsedInput failure
→ isConcurrencySafe = false
```

Runtime 没有说：

> 输入看起来大概没问题，先并发跑吧。

而是：

```text
无法理解 input
      ↓
无法可靠分类 Effect
      ↓
不给并发优化
```

这里不是：

```text
Tool 禁止执行
```

而是：

```text
Optimization denied
```

这两件事要区分开。

也就是说：

```text
concurrent execution
```

不是默认权利，

更接近一种需要正面证据才能获得的优化。

---

#### 连 Effect Classifier 自己报错，也会退回串行

还有更细的一层。

即使 Schema 成功：

```text
parsedInput.success
```

调用：

```ts
isConcurrencySafe(parsedInput)
```

本身也可能出错。

比如 Bash 的 Effect Classification 可能需要解析：

```text
shell command
```

结果遇到奇怪 Quote、Subshell 或 Parser 无法处理的输入。

Claude Code 这里不是：

```text
classifier failed
→ assume safe
```

而是：

```text
classifier failed
→ false
→ serial
```

所以这条策略可以概括成：

```text
Concurrency Optimization
requires positive evidence.
```

不知道的时候：

```text
慢一点
```

比：

```text
赌它没共享 Effect
```

便宜。

---

#### 真正漂亮的是：它只合并“相邻”的 safe calls

假设原始 Tool Call 顺序是：

```text
A safe
B safe
C unsafe
D safe
E safe
F unsafe
```

一种追求最大吞吐量的调度器可能重新分组：

```text
safe:
A B D E

unsafe:
C F
```

甚至先跑完所有 safe。

Claude Code 恢复代码里的 partition 不是这么做。

它更接近：

```text
[A B]
  ↓
[C]
  ↓
[D E]
  ↓
[F]
```

只把：

```text
相邻
+
concurrency-safe
```

的调用组成一个 batch。

这样：

```text
C
```

天然成了 Barrier。

D、E 不能越过 C 提前发生。

---

#### 为什么“安全的 Tool”也不能跨过 unsafe Tool 重排？

还是：

```text
Read(config)
Edit(config)
Read(config)
```

标记：

```text
safe
unsafe
safe
```

如果调度器只想着：

```text
所有 safe 并发
```

就会变成：

```text
Read old? ──┐
Read new? ──┴── simultaneously
       ↓
      Edit
```

第二次 Read 的语义直接坏了。

Model 原来的：

```text
Read
  ↓
Edit
  ↓
Read
```

其实已经隐式表达：

```text
old state
  ↓
transition
  ↓
new state
```

所以一个单独 Action：

```text
safe to overlap
```

不代表这个 Action：

```text
safe to reorder
```

这是 Macro 5 我觉得最值得记的一句话：

> **safe to overlap ≠ safe to reorder**

Claude Code 允许相邻安全操作重叠执行，却没有因此随意打乱 Model 原始 Action Sequence。

---

#### 可以把这种调度理解成“保留 happens-before barrier”

假设：

```text
A safe
B safe
C unsafe
D safe
E safe
```

Runtime 允许：

```text
A ───────┐
         ├─→ finish batch
B ───────┘
         ↓
         C
         ↓
D ───────┐
         ├─→ finish batch
E ───────┘
```

也就是：

```text
[A || B]
    ↓
    C
    ↓
[D || E]
```

而不会做：

```text
[A || B || D || E]
        ↓
        C
```

这实际保留了：

```text
C before D
C before E
```

这样的 happens-before boundary。

对于接触：

```text
filesystem
git
processes
network
MCP servers
runtime state
```

的 Agent 来说，这比单纯追求：

```text
maximize throughput
```

靠谱得多。

---

#### Safe Batch 内部也不是无限并发

通过 partition 以后，Safe Batch 才进入类似：

```ts
runToolsConcurrently(...)
```

的路径。

你当前源码快照里还能看到一个：

```text
max concurrency
```

限制。

旧稿根据这份 v2.1.88 恢复代码记录的是：

```text
CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY
```

未额外配置时默认：

```text
10
```

这里我同样只把它写成：

```text
这份 v2.1.88 快照的实现数字
```

而不把：

```text
10
```

说成 Claude Code 永久的产品契约。

真正值得学习的是：

```text
concurrency-safe
```

只回答：

> **语义上可不可以并发？**

它不回答：

> **资源上应该同时跑多少个？**

即使全是：

```text
Read
```

一次并发 1000 个也可能遇到：

```text
file descriptor pressure
disk contention
network saturation
MCP rate limit
memory pressure
UI progress flood
```

所以 Scheduler 其实有两个问题：

```text
Correctness:
哪些可以并发？

Resource Control:
最多同时并发多少？
```

Effect Metadata 主要帮助第一个。

Concurrency Limit 处理第二个。

---

#### Serial Path 不只是“一个一个等”

再看串行路径。

抽象代码大概是：

```ts
for (const toolUse of toolUseMessages) {
  for await (
    const update of runToolUse(...)
  ) {
    ...
  }
}
```

最容易看到的是：

```text
A finished
  ↓
B starts
```

但还有一个更容易被漏掉的东西：

```text
contextModifier
```

如果 Tool Result 带回一个 Runtime Context 修改，

Serial Path 可以在 A 完成后立即：

```text
apply modifier
```

于是 B 开始时看到的是：

```text
updated currentContext
```

这意味着顺序保证的不只是：

```text
外部 Environment
```

还包括：

```text
Harness internal context
```

整个关系更像：

```text
Tool A
  ↓
Environment effect
  ↓
Context modifier
  ↓
apply new Runtime Context
  ↓
Tool B
```

所以 Serial Ordering 不只是为了：

```text
避免两个 Tool 同时写一个文件。
```

它也可能保证：

> **前一个 Action 对 Runtime State 的改变，能够成为后一个 Action 的输入条件。**

---

#### 并发时最麻烦的是：谁先完成并不稳定

现在假设 safe batch 里有：

```text
Tool A
Tool B
Tool C
```

它们同时开始：

```text
A ──────────────┐
B ────────┐     │
C ───────────┐  │
```

这一轮可能：

```text
B → C → A
```

完成。

下一轮因为磁盘、网络或者机器负载变化，可能：

```text
C → A → B
```

如果哪个 Tool 一完成就立刻把自己的：

```text
contextModifier
```

应用到共享 Context：

```text
completion order
=
state commit order
```

那么相同的 Model Output：

```text
A B C
```

可能得到不同最终 Runtime State。

这就很难调试。

---

#### Claude Code 这里做了一个很漂亮的区分：Execution 可以并发，Commit 仍然保序

你当前恢复代码里，并发路径没有简单：

```text
Tool 完成
→ 立刻 apply contextModifier
```

而会先收集类似：

```text
queuedContextModifiers
```

的东西。

等 Safe Batch 的执行结果回来以后，再按照：

```text
原始 Tool Call 顺序
```

应用这些 Modifier。

假设：

```text
Model order:
A → B → C
```

实际完成顺序：

```text
B → C → A
```

Runtime 最终仍按：

```text
A modifier
    ↓
B modifier
    ↓
C modifier
```

提交。

所以：

```text
Execution Order
```

可以部分放松。

但：

```text
Semantic Commit Order
```

没有直接交给 Wall-clock Race 决定。

---

#### 我会把它记成“并发执行，确定性提交”

不是 Claude Code 官方术语。

只是我觉得很好记：

```text
Model order:
A B C

Execution:
A ────────────────┐
B ─────────┐      │
C ─────────────┐  │

Completion:
B → C → A

Commit:
A → B → C
```

也就是：

```text
parallel execution
+
ordered state application
```

这个设计特别适合 Agent Runtime。

因为 Agent 自己已经是：

```text
non-deterministic
```

的。

Runtime 没必要再因为：

```text
网络抖了一下
某个 Tool 快了 20ms
```

额外制造一层无意义的 nondeterminism。

---

#### 但这里也不要硬套数据库的“可串行化”

看到：

```text
ordered commit
```

以后，又很容易说：

> Claude Code 实现了数据库一样的 Serializable Transaction。

这个结论同样太大。

我们看到的是：

```text
Tool batching
Conservative effect classification
Barrier preservation
Ordered context modifiers
```

它们确实和并发系统的一些思想相似。

但仅凭这些还不能证明：

```text
严格 serializability
transaction isolation
rollback semantics
conflict detection
```

所以博客里更准确的写法是：

> Claude Code 在 Tool Runtime 中做了 **effect-aware scheduling**：允许部分 Action 并发执行，同时保留关键顺序边界，并避免让 Tool 的 Wall-clock Completion Order 直接决定 Runtime Context 的提交顺序。

已经足够有东西了。

---

#### `Promise.all(toolCalls)` 真正漏掉的是它前面的证明义务

现在重新回答标题。

为什么不能：

```ts
await Promise.all(toolCalls.map(run))
```

？

不是因为：

```text
Promise.all 很低级。
```

而是因为这行代码默认它的调用者已经解决了：

```text
这些 Action 是否相互独立？
它们是否读取/修改共享状态？
其中有没有顺序依赖？
Effect 分类失败怎么办？
哪些调用之间存在 Barrier？
最大并发度是多少？
并发返回的 Context Update 怎么提交？
```

对于普通程序，这些答案通常已经隐含在：

```text
程序员写好的控制流
```

里面。

但 Agent 的 Tool Sequence 是：

```text
Runtime 才由 Model 生成
```

的。

所以 Harness 必须在执行现场补上这层语义。

---

#### 这其实再次解释了 Harness 为什么存在

如果 Model 直接控制 Environment：

```text
Model
  ↓
tool calls
  ↓
Environment
```

那么它一次生成五个动作以后：

```text
并发？
串行？
重排？
中断？
失败恢复？
```

都得让模型自己解决。

而 Harness 的作用正是在中间接管：

```text
Model proposes actions
        ↓
Harness interprets effects
        ↓
Scheduler constructs execution plan
        ↓
Environment
```

Model 负责：

```text
我想做什么
```

Runtime 负责：

```text
这些动作怎么发生才不改变原本语义
```

这就是 Harness Engineering 里一个非常具体的职责边界。

---

#### 到这里，整个 Tool Runtime 已经可以串起来了

现在一个 Tool Call 从出生到完成，大致经历：

```text
User Intent
    ↓
Model
    ↓
Tool Selection
    ↓
Structured Input
    ↓
Schema
    ↓
Validation
    ↓
Permission
    ↓
Effect Classification
    ↓
Scheduling
    ↓
Execution
    ↓
Environment Effect
    ↓
Internal ToolResult
    ↓
Ordered Runtime Update
    ↓
Observation Mapping
    ↓
Model
```

前面五个 Macro 分别在拆这条路径的不同部分：

```text
Macro 1
Tool 到底是什么？

Macro 2
Agent 可以选择哪些 Action？

Macro 3
Agent 应该看到怎样的 Observation？

Macro 4
Model 怎么知道 Tool 应该怎么用？

Macro 5
Tool 真进入 Runtime 后，
这些 Action 怎么被正确执行？
```

但还剩最后一个问题。

我们到目前为止写的所有判断：

```text
这个名字更清楚

这个 Workflow Tool 应该合并

这个 Result 更简洁

这个 Error 更可行动

这个 Description 应该这样写

这个参数名应该改成 user_id
```

都很合理。

可“看起来合理”仍然不是证据。

到底：

```text
改了以后 Agent 真变好了吗？
```

不能靠工程师拍脑袋。

Anthropic 那篇文章真正有意思的地方，也正是在最后把 Tool Engineering 拉回：

```text
Eval
```

——构造真实任务，看完整 Transcript，然后让 Agent 的实际行为反过来修改 Tool。

所以下一章就是整篇 `tools.md` 的最后一块：

## 6. Tool 的好坏最终要靠 Agent Eval，而不是工程师拍脑袋

### 6.1 怎么设计一个真的能测出 Tool 好坏的 Eval？

前面五个 Macro 已经积累了一大堆看起来很合理的原则：

```text id="a1hczp"
不要机械包装 Backend API

Tool 数量不是越多越好

Workflow 可以适当 consolidation

Tool Name 要有清楚边界

Result 应该 high-signal

大结果需要 filter / pagination / truncation

Error 应该 actionable

Description 应该像 Prompt 一样认真写

Schema / Validation / Permission 要分层

Runtime 应该理解 Tool Effect
```

读到这里，很容易产生一种危险的满足感：

> 好，我已经知道怎么写一个“好 Tool”了。

问题是 Agent Tool 最麻烦的一点恰恰在这里：

```text id="umpj0m"
对程序员看起来合理
```

并不自动等于：

```text id="4y1npx"
Model 用起来真的更好。
```

比如我觉得：

```text id="3bup7p"
jira_issues_search
```

比：

```text id="f0yt4z"
search_jira_issues
```

好。

另一个工程师觉得刚好相反。

我觉得：

```text id="u6xaii"
20 results
```

是合理默认值。

Claude 可能在真实任务里经常需要 30 条。

我觉得：

```text id="rkytwi"
schedule_event
```

把三个 API 合成一个很优雅。

实际 Eval 却可能发现，它把几个本来需要 Agent 判断的选择藏得太深，反而降低成功率。

所以 Tool Engineering 和普通 API Design 最大的区别之一，就是：

> **调用者本身是一个概率模型，因此接口设计最好靠行为实验，而不是只靠静态 Review。**

Anthropic 那篇文章的整个工作流其实就是围绕这件事展开：

```text id="fmbjxz"
Prototype
    ↓
Evaluation
    ↓
Inspect behavior
    ↓
Improve tools
    ↓
Evaluation again
```

然后不断重复。

---

#### 最差的一种 Eval，是给 Tool 自己出单元测试

假设我刚写完：

```text id="r7kaqj"
search_contacts
```

然后测试：

```python id="9r64bx"
result = search_contacts("Jane")

assert len(result) > 0
assert result[0]["name"] == "Jane Smith"
```

当然应该有。

这是 Tool Implementation 的：

```text id="4noc3k"
Unit Test
```

它证明：

```text id="adpmr7"
函数实现正确
```

却没有证明：

```text id="jtdyxv"
Agent 会在正确时间选择它。
```

也没有证明：

```text id="m3owh2"
Agent 知道 Query 怎么填。
```

更没证明：

```text id="j3mxde"
拿到 Result 后会继续正确完成任务。
```

所以：

```text id="w15zps"
Tool Unit Test
```

和：

```text id="tgcjyp"
Tool-use Eval
```

不是一个东西。

前者可以：

```text id="ecwnn7"
直接调用 Tool
```

后者必须让：

```text id="fo74xp"
Agent 自己决定要不要调用。
```

---

#### 一个真正的 Tool Eval 应该从用户任务开始

比如不要测试：

> 调用 `search_contacts` 搜索 Jane。

因为你已经把答案塞进 Prompt 里了。

更接近真实任务的是：

> 下周找个时间和 Jane 开会，讨论我们最近的 Acme Corp 项目。附上上次项目规划会的笔记，再预订一个会议室。

这是 Anthropic 在原文里给出的 strong evaluation task 之一。

为什么它更强？

因为 Claude 自己必须发现：

```text id="os65zw"
我要找 Jane
        ↓
要识别正确 Jane
        ↓
要找 Acme 项目
        ↓
要找上一次 planning meeting
        ↓
要找到对应 notes
        ↓
要查 availability
        ↓
还要 reserve room
        ↓
最后 create event
```

也就是说它在同时测试：

```text id="cahfa1"
Tool discovery

Tool selection

Parameter construction

Tool composition

Result interpretation

Longer-horizon recovery
```

这才真正接近：

```text id="0kk2x4"
Agent 使用 Tool
```

而不是：

```text id="6g5rrh"
工程师调用函数。
```

---

#### Anthropic 给出的“强任务”和“弱任务”对比特别值得抄作业

原文还给了一组很清楚的对照。

弱任务像：

```text id="qxd552"
Schedule a meeting with jane@acme.corp next week.
```

它已经把：

```text id="eeztst"
Jane 的精确邮箱
```

告诉 Model。

于是 Agent 根本不用测试：

```text id="zrgk64"
search user
identity resolution
```

再比如：

```text id="ewgg8u"
Search the payment logs for
purchase_complete
and customer_id=9182.
```

连：

```text id="tydnlt"
搜什么字段
搜什么关键词
```

都替 Agent 决定了。

Claude 只是在执行一条已经拆好的 API 操作。

Anthropic 更推荐的任务则是：

> Customer ID 9182 报告一次购买被扣款三次。找出所有相关日志，并判断有没有其他客户受到同一个问题影响。

现在 Model 必须自己推：

```text id="b14c9q"
三次扣款
      ↓
哪几个 Transaction？
      ↓
对应哪些 Request / Logs？
      ↓
共同异常模式是什么？
      ↓
怎么搜索其他 Customer？
```

这个任务可能需要多次 Tool Call，甚至几十次。

Anthropic 明确建议不要只构造浅层 sandbox 题目；好的 Eval 应来自真实使用场景、真实复杂度，并允许需要多次甚至大量 Tool Call。

---

#### 所以 Eval Task 不应该泄露 Strategy

这点我觉得特别重要。

假设真正任务是：

> 查出为什么 Customer 9182 被重复收费。

一种 Eval Prompt 写法是：

```text id="mujkzj"
1. Call get_customer_by_id(9182)
2. Call list_transactions(...)
3. Call search_logs(...)
4. Search for duplicate payment attempts
5. Report the root cause
```

这样几乎已经变成：

```text id="j34unv"
Workflow Script
```

Tool Selection 根本没被测。

如果你刚好想比较：

```text id="n89s06"
get_customer_by_id
+
list_transactions
+
list_notes
```

和：

```text id="3mq8ia"
get_customer_context
```

哪套 Tool Design 更好，

这种 Prompt 更是直接把第一种设计写死了。

更好的 Eval 应该只描述：

```text id="qywi4h"
Goal
+
Necessary factual constraints
```

而不要规定：

```text id="x7wqsp"
Strategy
```

比如：

```text id="valofc"
Customer 9182 says they were charged three times
for one purchase attempt.

Determine what happened and whether
other customers were affected.
```

至于 Agent 是：

```text id="pn1v6h"
search customer
→ transactions
→ logs
```

还是：

```text id="o06719"
customer context
→ incident search
```

应该由它自己决定。

Anthropic 也特别提醒：你可以记录“预期 Tool Calls”作为诊断指标，但真实任务通常可能有多种正确路径，因此不要把 Evaluator 写到只接受一种固定 Strategy。

---

#### 这和我们前面讲 Action Space 正好接起来

Macro 2 说：

```text id="uh41fs"
Tool Set
=
Agent Action Space
```

那么 Eval 真正应该测的是：

```text id="0m3iv8"
给定 Goal
+
给定 Action Space

Agent 能不能自己找到
一条成功 Trajectory？
```

如果 Eval Prompt 已经把：

```text id="9eepr6"
Trajectory
```

写进去了，

就测不到 Action Space 设计好不好。

这也是为什么一个：

```text id="0c7jt0"
API benchmark
```

和一个：

```text id="v6x7u8"
Agent tool-use benchmark
```

会有明显区别。

---

#### Eval 里的 Environment 也不能太干净

还有一种我以前很容易设计出来的玩具 Eval：

```text id="wbc0qv"
通讯录里只有：
Jane Smith
Bob
Alice
```

然后问：

> 找 Jane。

成功率 100%。

到了真实公司：

```text id="zlyjtd"
Jane Smith
Jane Wang
Jane Chen
Jane Doe
Jane S.
J. Smith
```

其中甚至有人：

```text id="7fys9v"
离职
同名
多个 Workspace
多个邮箱
```

Tool 立刻开始出问题。

所以 Anthropic 特别强调：

```text id="hswt93"
realistic data sources
realistic services
real workflow complexity
```

而不是为了方便 Evaluator，构造一个所有答案都在第一条记录里的 sandbox。

如果是 Coding Agent 也一样。

差的 Eval：

```text id="dzxud1"
一个 30 行 Python 文件
只有一个明显 TODO
```

真实任务却可能是：

```text id="fi0s26"
1000 files
多个同名 symbol
生成代码
测试 fixture
package scripts
Git state
lint / unit / integration tests
```

这两种环境测到的 Tool Use 根本不是一个东西。

---

#### 每道 Eval 还必须有“可以验证的结果”

只让 Agent 自己最后说：

> 我完成了。

当然不够。

一个任务至少要有某种：

```text id="xpu3ny"
Verifier
```

Anthropic 给的范围很宽。

最简单可以是：

```python id="8wg8pu"
assert response == ground_truth
```

复杂一点可以：

```text id="qtqb3b"
检查数据库状态

检查 Calendar 是否真的创建 Event

检查正确 Document 是否被 Attach

检查 Logs 中识别出的 Customer 集合

运行测试

检查 Git Diff
```

再复杂一些，也可以使用 Model Judge 判断开放式答案是否满足要求。

关键是：

```text id="5e2yuk"
task completion
```

应该尽量能从外部确认，而不是相信 Agent 自报成功。

---

#### Verifier 也不能严格到把正确答案判错

例如任务问：

> 哪些 Customer 受到影响？

Ground Truth：

```text id="8ll9gl"
9182, 1371, 6628
```

Agent 回答：

```text id="582l2i"
Customers 1371, 6628, and 9182 were affected.
```

如果 Evaluator 做：

```python id="r0v8dt"
assert output == "9182, 1371, 6628"
```

就很荒谬。

同样：

```text id="y9redj"
标点
排序
Markdown
措辞
```

都可能产生并不影响 Correctness 的差异。

Anthropic 因此也提醒不要把 Verifier 写得过度严格，以免因为 Formatting、Punctuation 或其他合法表达差异拒绝正确答案。

---

#### 我会把 Tool Eval 分成三层

如果以后真的给 Hi-Agent 或 MCP Tool 做 Eval，我会比较喜欢这种拆法：

```text id="h51w3k"
Level 1
Tool Implementation Test
    ↓
函数本身正确吗？

Level 2
Tool Contract Test
    ↓
Schema / Validation /
Permission / Result mapping 正确吗？

Level 3
Agent Tool-use Eval
    ↓
Model 在真实任务里
会不会正确使用整套 Tool？
```

三层都要。

但不能拿：

```text id="q68p6r"
Level 1 passed
```

推出：

```text id="xc55bb"
Agent 会用。
```

---

#### Tool Eval 最好也不要只跑一次

还有一个普通软件测试里没那么明显的问题：

```text id="ci9i85"
Agent 是 non-deterministic 的。
```

同一个 Prompt：

```text id="227n86"
同一 Tool Set
同一 Environment
```

重复运行，

Model 可能：

```text id="pen8vy"
这次先搜 Jira
下次先搜 GitHub

这次 5 calls 完成
下次 8 calls 完成

这次选对 Jane
下次碰巧选错
```

所以：

```text id="6hf5wp"
1 run = pass
```

很难给出可靠结论。

更合理的 Eval 会考虑：

```text id="4lv639"
多 Task
+
必要时重复采样
+
Aggregate Metric
```

例如：

```text id="qrsbgi"
Accuracy

Success@N

Average Tool Calls

Error Rate
```

具体统计方式可以根据项目规模决定。

不用为了一个 Toy Project 一上来搭一座 Benchmark Platform。

但至少不要拿：

```text id="ayf7sj"
“我手动试了一遍，好像不错”
```

当最终证据。

---

#### 到这里，Accuracy 似乎已经能比较 Tool 版本了

假设：

```text id="7wlkeh"
Tool Set A
Accuracy = 74%

Tool Set B
Accuracy = 86%
```

看起来 B 赢。

可再看两个 Agent Transcript：

```text id="h44xcm"
A:
6 tool calls
8K tokens
12 s
0 errors

B:
31 tool calls
47K tokens
91 s
7 invalid parameter errors
```

事情开始没那么简单。

B 虽然最后更多题答对，

Tool Interface 可能仍然暴露了很明显的问题。

这就是下一 Beat。

---

### 6.2 看 Accuracy 还不够，还应该看什么？

假设两套 Tool 都拿到：

```text id="p31t8f"
90% task success
```

它们真的一样好吗？

先看第一套：

```text id="v3b5ti"
search_customer
      ↓
get_customer_context
      ↓
search_logs
      ↓
answer
```

4 次 Tool Call。

第二套：

```text id="hp2wzd"
list_customers
      ↓
get_customer
      ↓
list_transactions
      ↓
get_transaction
      ↓
get_transaction
      ↓
list_logs
      ↓
list_logs
      ↓
list_logs
      ↓
...
```

最后也答对。

如果只存：

```text id="bqk5he"
final_answer_correct = true
```

两者完全相同。

可从 Harness 的角度看，

第二条 Trajectory 已经在喊救命了。

---

#### Anthropic 建议至少顺手记录这些指标

除了：

```text id="c6ncl4"
top-level accuracy
```

原文建议记录：

```text id="d5hzbs"
Total runtime

Tool-call runtime

Total number of tool calls

Total token consumption

Tool errors
```

这些指标并不是为了做一个漂亮 Dashboard。

它们能帮你反推：

```text id="m7kg9s"
Tool Design 到底哪里坏了。
```

---

#### Tool Call Count 是一个非常便宜但很好用的信号

比如一个任务理论上比较自然的路径是：

```text id="tqekmg"
search_contact
      ↓
schedule_event
```

结果 Agent 经常：

```text id="6pq4pg"
search_contact
search_contact
search_contact
list_contacts
search_contact
schedule_event
```

最后也成功。

单看 Accuracy：

```text id="b5cqfi"
PASS
```

看 Tool Calls：

```text id="nkdetx"
6
```

就会问：

> 为什么它一直重复搜？

可能原因很多：

```text id="lwmz1i"
search_contact Result 不够明确

Search Ranking 太差

Tool Description 没告诉模型
返回的是候选而非完整结果

Identifier 不可读

pagination 太小

Tool 间职责重叠
```

所以 Tool-call Count 本身不是诊断答案。

它更像：

```text id="ejmibc"
烟雾报警器。
```

---

#### 重复调用往往能提示 Tool 粒度有问题

假设大量 Transcript 都是：

```text id="vgl62k"
get_customer
      ↓
list_transactions
      ↓
list_notes
```

而且几乎每个客服 Task 都这么走。

那 Macro 2 说过的：

```text id="w1q0ik"
Workflow Consolidation
```

就获得了真正的行为证据。

不是工程师凭感觉说：

> 我觉得可以做 `get_customer_context`。

而是 Eval 里显示：

```text id="efjckc"
这三个 Tool 在大量任务中
稳定形成固定链条。
```

于是可以试：

```text id="kefydc"
get_customer_context
```

再跑 Eval：

```text id="ca91le"
Accuracy?
Tool calls?
Tokens?
Latency?
```

看结果。

Anthropic 也明确提到，分析 Tool Calling Metrics 能揭示 Agent 的常见 Workflow，并指出值得 consolidation 的地方。

---

#### Invalid Parameter Error 则很像在给 Schema / Description 投票

假设：

```text id="s3ssr5"
send_message
```

Eval 一百次里有 27 次：

```text id="ekfxyu"
Invalid user
```

Transcript 一看：

```json id="ves9ab"
{
  "user": "Jane Smith"
}
```

Tool 实际需要：

```text id="5sew8s"
user_id
```

这时模型已经通过统计告诉我：

```text id="goj2cn"
Parameter Interface 不好。
```

可能修法：

```text id="k7zq50"
user
→
user_id
```

再加：

```text id="2aylpu"
Use search_users if the user ID is unknown.
```

然后重新跑。

如果：

```text id="3esme5"
Invalid Parameter Rate:
27%
→
3%
```

而 Accuracy 上升，

我们才有资格说：

```text id="xejvzn"
这个 Description / Schema 改进有效。
```

而不是：

> 新名字感觉专业多了。

Anthropic 也把“大量 Invalid Parameter Error”直接列成一种诊断线索：可能需要更清晰的 Description 或 Example。

---

#### Token Consumption 能看出 Observation Space 有没有失控

假设：

```text id="snsi6w"
search_logs
```

任务最终正确。

但是每道题：

```text id="9lzjfs"
Average tool-result tokens = 80K
```

那 Macro 3 基本就该回去重写。

可能发生了：

```text id="oj1grg"
Search 太宽

没有 Filter

默认 Pagination 太大

Result 带了一堆 Metadata

Agent 每次都请求 detailed

Truncation Guidance 太差
```

如果改完：

```text id="snlj4m"
80K
→
18K
```

而 Accuracy：

```text id="bxx4on"
保持不变甚至提高
```

这就是非常实际的 Tool Improvement。

---

#### Latency 则可能揭示另一类低效率

例如：

```text id="68q8l8"
Tool A:
search all logs
then agent filters

Tool B:
backend-filtered search_logs
```

两者 Accuracy 相同。

但：

```text id="f43ir4"
Tool A:
42 s

Tool B:
6 s
```

从生产体验看显然不是一回事。

又例如 Macro 5 的并发优化：

```text id="f3xath"
Read A
Read B
Read C
```

如果都被错误标成 Serial：

```text id="a4q5ma"
Correctness
```

可能完全不变。

但：

```text id="g0vmx4"
Latency
```

明显变差。

所以：

```text id="eom56e"
Accuracy-only Eval
```

也测不到 Runtime Effect Metadata 有没有配置得合理。

---

#### Error Rate 还可以继续分类，而不是只记一个数字

比如：

```text id="vbeg1n"
tool_error = true
```

信息量太少。

可以进一步分：

```text id="b8jsq0"
schema_error

validation_error

permission_denied

timeout

backend_error

result_too_large

resource_not_found
```

然后看分布：

```text id="71vgt5"
Schema Error 高
→ Tool Spec / 参数命名可能差

Validation Error 高
→ Model 常基于过期状态操作，
  或 Result 没提供足够 continuation info

Permission Denial 高
→ Agent Strategy 与 Capability Policy
  可能存在冲突

Timeout 高
→ Query 过宽 / Tool Implementation 慢

Result Too Large 高
→ Pagination / Filter / Default 不合理
```

这时候 Tool Eval 已经不是：

```text id="nl54ju"
一个 Accuracy 数字
```

而变成一张：

```text id="zt218j"
行为诊断图。
```

---

#### 可 Metrics 仍然解释不了“为什么”

假设数据告诉我：

```text id="lgvfm1"
search_logs
平均每题调用 7.3 次
```

为什么？

光看：

```text id="ntjui0"
7.3
```

不知道。

可能是：

```text id="gfcesh"
第一次结果太少

第一次结果太多

Query Description 不清楚

Agent 误以为 Search 不支持 regex

Agent 每次都忘记设置 service

Result 里缺少下一步 Identifier

搜索结果排序不好
```

这时候就必须回到：

```text id="ppkapr"
Transcript
```

---

#### Raw Transcript 才是 Tool Engineering 最值钱的 Debug Artifact

一个 Agent Eval 最好至少能留下：

```text id="m01mrx"
User task

Tool definitions / version

Tool calls

Tool inputs

Tool results

Errors

Final answer

Verifier result

Tokens / latency / counts
```

例如：

```text id="tg9qw7"
USER
Find out why customer 9182 was charged three times.

ASSISTANT
→ search_customer
  {"customer_id":"9182"}

TOOL
...

ASSISTANT
→ list_transactions
  ...

TOOL
237 transactions...

ASSISTANT
→ list_transactions
  ...

TOOL
237 transactions...

ASSISTANT
→ list_transactions
...
```

单看这里就会觉得：

> 等等，你为什么连续读三次一模一样的东西？

这种行为未必出现在 Agent 自己的最终反馈里。

Anthropic 因此明确建议不要只看 Agent 的自我解释，还要直接 Review Raw Transcript，包括 Tool Calls 和 Tool Responses；因为模型自己对行为的叙述可能遗漏真正重要的问题。

---

#### 我会特别小心不要把这理解成“必须保存隐藏 CoT”

Anthropic 这篇 **2025 年**文章还谈到让 Eval Agent 输出 reasoning / feedback，或者利用当时 Claude 的 Interleaved Thinking 帮助分析 Tool Use。

但如果我今天自己搭 Eval Harness，我不会把系统设计建立在：

```text id="nhxcmc"
必须拿到模型完整隐藏 Chain-of-Thought
```

这个前提上。

对 Tool Debug 来说，很多最关键的信息其实已经是可观察的：

```text id="c4jgsx"
它选了哪个 Tool？

参数填了什么？

Tool 返回了什么？

它是不是立刻重试？

换了什么参数？

在哪里停止？

最终结果是否正确？
```

这些：

```text id="9m7d04"
Action / Observation Trace
```

本身就足以暴露大量 Tool Design Bug。

需要时再额外让 Eval Agent给：

```text id="x3jcyk"
简短 decision rationale
structured feedback
```

即可。

重点不是获得一篇模型内心独白。

而是：

> **让行为轨迹足够可观察。**

---

#### 比如 Anthropic 那个“莫名其妙加 2025”就只有看 Trace 才容易发现

Web Search Tool 上线以后，Anthropic 发现 Claude 会不必要地把：

```text id="evbpgh"
2025
```

塞进 Search Query。

比如原本需要：

```text id="q8xfqp"
latest foo
```

Model 可能变成：

```text id="28uo19"
latest foo 2025
```

从 API 角度：

```text id="2fmbw8"
完全合法。
```

Search Tool：

```text id="al3dqi"
执行成功。
```

如果答案最后碰巧也答对：

```text id="irqzlj"
Accuracy = PASS
```

甚至可能没有任何红灯。

但 Raw Tool Call 已经暴露：

```text id="rouoi0"
Agent strategy 存在系统性偏差。
```

Anthropic 最后通过改 Tool Description 把这个行为纠正。

这个案例特别能说明：

```text id="193zek"
Transcript
```

和：

```text id="32qy6k"
Final Score
```

解决的是两个不同问题。

---

#### 所以 Eval 最终应该同时回答“好不好”和“为什么”

我会把它拆成：

```text id="4vldwq"
Outcome Metrics
      ↓
Tool 改完以后真的更好吗？

Behavior Metrics
      ↓
它用了多少成本完成？

Trajectory Inspection
      ↓
它为什么成功 / 失败？
```

对应大概：

```text id="yekqb4"
Outcome
├── Accuracy
├── Task success
└── Verifier score

Efficiency
├── Tool calls
├── Tokens
├── Runtime
└── Latency

Reliability
├── Tool errors
├── Invalid parameters
├── Timeouts
└── Recovery rate

Trace
├── Tool-selection path
├── Inputs
├── Results
└── Repeated / confused behavior
```

这样才能真的 Debug Tool。

---

#### 我甚至可以拿 Eval Trace 反推前面五个 Macro

看到：

```text id="y3i5vu"
经常选错 Tool
```

回去看：

```text id="4fagtn"
Macro 2 / Macro 4
Tool Set
Name
Description
```

---

看到：

```text id="1eui6p"
经常把参数填错
```

回去看：

```text id="dgljld"
Macro 4
Schema
parameter naming
examples
```

---

看到：

```text id="e7agrd"
Result 之后经常走错下一步
```

回去看：

```text id="k7ihai"
Macro 3
Observation Design
```

---

看到：

```text id="x56pzy"
重复十几次 Search
```

可能看：

```text id="borzn6"
Macro 2
Workflow Tool

Macro 3
Pagination / Filtering
```

---

看到：

```text id="kaghzq"
任务正确但特别慢
```

再看：

```text id="b2p36n"
Macro 5
Concurrency / Scheduling
```

也就是说这整篇文章其实不是六堆散乱 Best Practice。

Macro 6 给了它们共同的：

```text id="0439hy"
feedback channel
```

---

#### 但这里还有一个很现实的问题：谁来读几百条 Transcript？

十道 Eval 可以自己看。

一百道已经开始烦。

一千道基本不可能每条人工 Review。

Anthropic 接下来的做法很 Agent-Native：

> 既然 Transcript 是文字，为什么不让 Claude 自己帮忙分析？

这就到了文章标题里最后那个：

```text id="5066to"
using AI agents
```

---

### 6.3 让 Claude Code 反过来优化 Claude 的 Tool

假设我已经跑了：

```text id="bynazj"
100 evaluation tasks
```

每道题留下：

```text id="dw0atm"
Prompt
Tool Calls
Tool Results
Final Response
Verifier
Metrics
```

现在我得到一百份 Transcript。

最传统的工作流当然是：

```text id="37f7tr"
工程师
  ↓
一条一条看
  ↓
记问题
  ↓
改 Tool
  ↓
重新跑
```

Anthropic 做了一个很自然的升级：

```text id="hcf99v"
Eval Agents
   ↓
Transcripts
   ↓
Claude Code
   ↓
Analyze patterns
   ↓
Modify tools
   ↓
Run Eval again
```

也就是说：

> **让使用 Tool 的同类 Agent，反过来分析自己的 Tool-use 失败，再修改 Tool Interface。**

Anthropic 原文说得很直接：可以把 Eval Transcript 拼起来交给 Claude Code，让它寻找矛盾的 Tool Description、低效实现、混乱 Schema 等问题，并同时重构一组相关 Tool，保持实现和描述的一致性。

---

#### 这个循环其实很像普通软件工程，只是 Feedback Source 换了

传统 API 开发：

```text id="f0mx8c"
Developer
    ↓
API
    ↓
Users
    ↓
Bug report / telemetry
    ↓
Developer
```

Agent Tool：

```text id="a7nsyg"
Developer / Agent
    ↓
Tool
    ↓
Agent
    ↓
Eval Transcript
    ↓
Developer / Agent
```

调用者本身变成模型以后，

它留下的：

```text id="kzs40p"
Tool-use traces
```

就成了一种新的接口 Telemetry。

然后另一个 Agent 又很擅长：

```text id="uf6x9u"
读大量文本 Trace
找重复模式
改代码
改 Description
```

这就形成一种很自然的：

```text id="pwbdob"
Agent-assisted Tool Engineering
```

---

#### 比如 Claude Code 可以从 Transcript 里发现什么？

假设二十条失败 Trace 都出现：

```text id="l95ucj"
search_user(name="Jane")
      ↓
returns 12 people + cryptic IDs
      ↓
Agent chooses wrong Jane
```

它可能建议：

```text id="crdwou"
增加 team / role / email

对 Result 排序

修改 Description

增加更明确的 identity fields
```

这对应：

```text id="076dvl"
Macro 3
```

---

另一批：

```text id="is0fpv"
send_message(user="Jane")
→ invalid parameter

send_message(user="jane@example.com")
→ invalid parameter
```

它可能改：

```text id="ntowdg"
user
→
user_id
```

并补：

```text id="l60g1h"
Call search_users first if ID is unknown.
```

对应：

```text id="8ywg2u"
Macro 4
```

---

还有：

```text id="jqyh59"
list_users
list_events
create_event
```

大量重复出现，

Claude Code 可能提出：

```text id="aikcp3"
schedule_event
```

对应：

```text id="wh0crk"
Macro 2
```

---

也就是说它不需要一开始就知道：

```text id="9t91jr"
Agent Tool Design 的真理
```

它可以从：

```text id="2sonht"
Behavior
```

倒推：

```text id="4pj5yg"
Interface
```

---

#### 更有意思的是，Anthropic 说这篇文章很多经验本身就是这么来的

原文不是只说：

> 理论上可以让 Claude Code 优化 Tool。

Anthropic 明确表示，这篇文章中的很多建议，本身就是在反复使用 Claude Code 优化内部 Tool Implementation 的过程中得到的。

他们的 Eval 建在内部 Workspace 上，尽量保留真实复杂度，包括真实 Project、Document 和 Message 等，而不是专门造一个简单实验环境。

所以这篇文章实际展示的流程是：

```text id="ulsfxd"
Agent uses Tools
      ↓
Eval captures behavior
      ↓
Agent analyzes behavior
      ↓
Agent modifies Tools
      ↓
Agent uses new Tools
```

这里已经有一点：

```text id="v0g60b"
self-improvement
```

的味道。

但我不会直接叫它：

```text id="jqfs8i"
Self-Evolving Agent
```

因为 Tool 代码修改仍然处在一个明确的外部 Eval / Engineering Loop 里，

并不是 Model 在生产运行时：

```text id="vpg8km"
无限自主修改自己的能力。
```

更准确的是：

```text id="9owx8b"
evaluation-driven
agent-assisted tool optimization
```

---

#### 最危险的问题马上来了：Claude 会不会把 Tool 调到“只会做这套 Eval”？

当然会有这个风险。

假设 Training Eval 有十道题：

```text id="au5iyw"
Task 1
Task 2
...
Task 10
```

Claude Code 每次拿到失败 Trace 后继续改：

```text id="foeqwr"
Description
Schema
Implementation
Default
```

然后重新跑同样十道题。

跑到最后：

```text id="zlf33q"
100% Accuracy
```

是不是说明 Tool 完美？

不一定。

最极端可以直接在 Tool 里：

```python id="hce31c"
if query == "the exact eval query":
    return known_answer
```

当然没人会这么明着写。

但更隐蔽的 Overfitting 很容易发生。

例如根据 Eval 里反复出现：

```text id="6hdh8t"
Acme
Jane
payment-api
```

把 Description 调得特别适合这些 Pattern。

结果新任务：

```text id="h116gh"
Globex
Sarah
inventory-api
```

性能又掉下来。

---

#### 所以 Anthropic 专门留了 Held-out Test Set

他们把用于反复调整 Tool 的 Eval 和最终验证性能的：

```text id="ztjs8d"
held-out test set
```

分开。

也就是：

```text id="jr7trr"
Training / Development Evaluations
        ↓
看 Transcript
改 Tool
继续调

Held-out Test Set
        ↓
不要参与日常调参
最终检查 Generalization
```

Anthropic 说正是通过 Held-out Test Set，他们确认 Claude 优化后的内部 Tool 并不只是记住了“训练 Eval”，而且在未用于优化的测试集上仍能获得额外性能提升；文章还表示这些优化后的版本可以超过他们所谓的 expert tool implementations——包括研究人员手写或 Claude 原先生成的实现。

这里是整个流程中非常重要的一道保险。

---

#### Tool Eval 也应该有我们熟悉的 Train / Dev / Test 思维

虽然我们不是在训练 Model Weight，

但只要：

```text id="2owrb7"
你根据 Eval Result
持续修改 Tool
```

这套 Eval 就已经参与：

```text id="f8u2jo"
Optimization
```

了。

所以逻辑和 Machine Learning 很像：

```text id="1u3pyz"
Development set
      ↓
observe failures
      ↓
modify tool

Development set
      ↓
observe failures
      ↓
modify tool

...

Held-out test set
      ↓
final evaluation
```

甚至：

```text id="pmzl24"
Tool Description
Default parameters
Tool boundaries
Result format
```

都可以理解成在 Eval Objective 上被调优的：

```text id="05ku2p"
System Parameters
```

不是 Gradient Descent。

但仍然存在：

```text id="3a7z63"
Overfitting
```

---

#### 如果是我自己的 Toy Project，不需要把这套搞成 ML 平台

比如 Hi-Agent 只有：

```text id="083fkj"
20 个 Tool Eval Cases
```

没必要装成：

```text id="mmdj7t"
Train 10000
Dev 2000
Test 5000
```

完全没必要。

简单一些也行：

```text id="dncrmk"
12 development cases
    ↓
日常看 Transcript、调 Tool

8 held-out cases
    ↓
尽量不看具体失败细节，
阶段性检查
```

或者：

```text id="u14qao"
每次新积累真实 Failure
加入未来 regression set
```

真正要保留的是思想：

> **不要一边看所有测试答案，一边不断调接口，然后再拿同一批题宣布自己性能提升。**

这跟代码里：

```text id="h94xiz"
只为通过当前 Unit Test
写硬编码
```

是同一个问题。

---

#### 更完整一点，Tool Optimization Loop 可以这样搭

我会把整套流程写成：

```text id="5iq9qa"
        ┌──────────────────┐
        │  Tool Prototype  │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Development Eval │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Metrics + Traces │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Analyze Failures │
        │ Human / Agent    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Modify Tool      │
        │ name             │
        │ description      │
        │ schema           │
        │ implementation   │
        │ output           │
        │ defaults         │
        └────────┬─────────┘
                 │
                 └───────────────┐
                                 │
              iterate ◀──────────┘

                 ↓
         when stable enough

        ┌──────────────────┐
        │ Held-out Test    │
        └────────┬─────────┘
                 │
                 ▼
        Generalization?
```

这个循环其实就是整篇 Anthropic Tool Engineering 文章最核心的方法。

具体原则：

```text id="qgob6j"
workflow tools
namespacing
high-signal results
token efficiency
description prompting
```

都是从这个过程里总结出来的。

---

#### 这样一来，“Tool 是 Prompt”这句话也终于能测了

Macro 4 说：

```text id="dd2mm4"
Tool Description
=
Prompt Surface
```

过去 Prompt Engineering 很容易：

```text id="wnh6m1"
改一句
试一下
感觉不错
```

现在可以变成：

```text id="5ioag8"
Description v1
      ↓
Eval

Description v2
      ↓
Eval

Compare:
Accuracy
Invalid params
Tool selection
Tokens
```

甚至：

```text id="ojdu7k"
jira_search
```

和：

```text id="dlwad5"
search_jira
```

这种看起来极其细枝末节的命名变化，

如果真的影响 Tool-use Accuracy，

就可以在 Eval 里看到。

Anthropic 甚至明确说，他们发现 Prefix 和 Suffix Namespacing 在 Tool-use Eval 上会产生非平凡差异，而且不同 LLM 的结果还可能不同。

这时候 Tool Naming 就从：

```text id="mmp60l"
Style Guide
```

变成：

```text id="7guz1c"
Behavioral Interface Experiment
```

---

#### “最优 Tool”本身还是 Model-relative 的

这点和父文里 Harness 的结论其实完全一致。

假设：

```text id="8e9n4p"
Tool Set A
```

在：

```text id="2ngudm"
Claude Model X
```

上最好。

换一个更强的 Model：

```text id="m089ny"
Model Y
```

可能：

```text id="pnzmf3"
能更好地处理 Primitive Tools
```

原来必须 consolidation 的：

```text id="f454nf"
Workflow Tool
```

不再那么必要。

或者更擅长处理长结果以后：

```text id="0smoko"
pagination default
```

也可能需要重新调。

反过来，一个较弱 Model 可能需要：

```text id="wmma2z"
更明确 Tool Boundary
更强 Description
更少 Action Choices
更多确定性 Workflow
```

所以：

```text id="0pxzwf"
good Tool Design
```

不是永远脱离 Model 存在的。

它更像：

```text id="xazd43"
Tool
+
Model
+
Task Distribution
+
Environment
```

共同决定的系统属性。

这也是为什么 Anthropic 最后强调：

```text id="v7t5dd"
systematic
evaluation-driven
```

而不是：

```text id="bywawf"
记住十条 Best Practice，
以后永远照抄。
```

---

#### 到这里，我终于能重新回答这篇文章开头那个问题

最开始我问：

> Backend 已经有 API 了，为什么不能包一层 JSON Schema 就叫 Agent Tool？

现在答案已经比：

```text id="jgsra3"
因为 Agent 不稳定
```

具体得多。

Backend API 通常假定：

```text id="817tzz"
调用者知道要调用哪个接口

调用者理解返回字段

调用者自己维护控制流

调用者自己处理副作用

调用者自己决定并发

调用者自己处理错误恢复
```

LLM Agent 并不天然拥有这些保证。

所以 Agent Tool 要重新设计：

```text id="1448eh"
Action Space
      ↓
什么值得暴露成 Tool？

Observation Space
      ↓
什么值得返回 Context？

Prompt Surface
      ↓
Model 怎么知道 Tool 怎么用？

Runtime Contract
      ↓
动作是否有效、授权、有何 Effect？

Scheduling
      ↓
多个 Action 怎么正确发生？

Evaluation
      ↓
这些设计真的让 Agent 变好了吗？
```

---

#### 如果把整篇 `tools.md` 最后压成一张图

我会画成：

```text id="57wq99"
                    User Goal
                        │
                        ▼
                 ┌─────────────┐
                 │    Model    │
                 └──────┬──────┘
                        │
                     Action
                        │
        ┌───────────────▼────────────────┐
        │            Tool               │
        │                                │
        │  Name / Description / Schema   │
        │           ↓                    │
        │  Validation / Permission       │
        │           ↓                    │
        │  Effect Semantics              │
        │           ↓                    │
        │  Scheduling / Execution        │
        └───────────────┬────────────────┘
                        │
                        ▼
                  Environment
                        │
                    Raw Result
                        │
        ┌───────────────▼────────────────┐
        │            Harness            │
        │                                │
        │ filter / rank / paginate       │
        │ truncate / error mapping       │
        │ context update                 │
        └───────────────┬────────────────┘
                        │
                   Observation
                        │
                        ▼
                 ┌─────────────┐
                 │    Model    │
                 └──────┬──────┘
                        │
                    next Action
                        │
                       ...
```

而整套系统的外面，再包一层：

```text id="m6tjag"
                Evaluation
                    │
      ┌─────────────┴─────────────┐
      │                           │
   Outcome                     Trace
      │                           │
 accuracy                    tool calls
 verifier                    responses
 success                     errors
                             tokens
                             latency
      │                           │
      └─────────────┬─────────────┘
                    │
                    ▼
              Tool Improvement
                    │
                    └──────→ 再跑 Eval
```

这才是我现在理解的：

```text id="jp5mi7"
Writing effective tools for agents
```

它不是单纯：

```text id="ux6xze"
把函数描述写清楚。
```

它是在设计 Agent 和真实世界之间的：

```text id="qbmy9x"
Action / Observation / Execution Contract
```

然后用 Agent 自己的真实行为，反过来验证这份 Contract 是否好用。

---

#### 最后回到 Claude Code：Tool 为什么是 Harness 的核心边界？

现在再打开 Claude Code v2.1.88 的：

```text id="spwdgi"
Tool.ts
toolOrchestration.ts
```

我不会再把里面那些字段看成：

```text id="k98m7c"
Anthropic 给普通函数堆了很多工程代码。
```

它们分别对应前面一路遇到的问题：

```text id="nnuuwt"
inputSchema
→ Action Language

validateInput
→ Runtime Truth

checkPermissions
→ Authorization

isReadOnly
isDestructive
→ Effect Metadata

isConcurrencySafe
→ Scheduling Semantics

interruptBehavior
→ Interactive Runtime

call
→ Actual Capability

ToolResult
→ Internal Result

mapToolResult...
→ Observation Construction

render...
→ Human-facing Representation
```

而：

```text id="lyvzrx"
toolOrchestration.ts
```

则真正把这些 Contract 信息消费掉：

```text id="bq8293"
parse
classify
partition
parallel / serial
ordered context update
```

所以在 Claude Code 这样的 Coding Agent 里：

```text id="8jx1vw"
Tool
```

已经远远不是 OpenAI / Anthropic API 文档里那个：

```text id="e0xc16"
name
description
JSON Schema
```

那么简单。

那只是：

```text id="wwmbp6"
Model-facing surface
```

真正进入 Harness 以后，它还必须成为一个 Runtime 能够理解的：

```text id="rp8e23"
Action Object
```

---

#### 如果面试官最后只让我用一分钟总结

我大概会这样说：

> Agent Tool 不能简单理解成给 LLM 暴露一个函数。因为调用者从确定性程序变成了概率模型以后，Tool 同时决定了 Agent 的 Action Space 和 Observation Space。
>
> Model-facing 这一侧，Tool 的 Name、Description、Schema 本质上都在做 Steering；Tool Set 太多、边界重叠、Result 太长或者参数含糊，都会直接影响 Tool-use 行为。
>
> Runtime-facing 这一侧，像 Claude Code 还需要 Validation、Permission 和 Effect Metadata，让 Harness 知道一次具体 Action 是否成立、是否授权、是不是只读、能否并发以及如何中断。`toolOrchestration.ts` 再根据这些语义做 effect-aware scheduling，而不是简单 `Promise.all(toolCalls)`。
>
> 最后这些设计都不能只靠工程师觉得“合理”。应该用 realistic multi-step Tool Eval 看 Task Success、Tool Calls、Tokens、Latency、Errors 和 Raw Transcript，再根据行为修改 Tool，并用 held-out cases 防止把接口调到只会做当前 Eval。

如果还能再补一句：

> **Tool 是概率模型和确定性世界之间的 Contract；Harness 的工作，就是让这份 Contract 真正可执行、可观察、可约束、可评估。**

到这里，这篇 `tools.md` 的主线也就完整闭合了。
