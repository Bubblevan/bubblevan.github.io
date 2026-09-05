---
title: "Claude Code Security：Permission、Sandbox 与 Auto Mode"
weight: 3
---

## 1. 权限系统解决“模型想做”和“系统允许做”的差距


**权限不是 `Bash = dangerous`。**

真正的问题是：

> **Harness 怎样针对一次具体 Tool Call，在当前工作目录、规则集和交互模式下决定 allow、deny 还是 ask？**


### 1.1 权限不是 `Bash = dangerous`


前两个 Macro 已经把 Tool execution 拆得比较细了。

模型先提出：

```text
tool_use
```

Harness 再通过 Tool contract 判断：

```text
输入是否合法？
这个动作有什么 effect？
能不能并发？
怎样执行？
```

但这里还缺一个最关键的判断：

> **技术上能执行，不代表当前 Agent 被授权执行。**

比如 Claude Code 拥有 Bash Tool。

这只能说明：

```text
Harness 具备执行 Shell command 的 capability
```

它不能推出：

```text
Claude 对任意 Shell command 都拥有 authorization
```

假设 Model 连续提出：

```bash
pwd
```

```bash
git status
```

```bash
npm test
```

```bash
rm -rf dist
```

```bash
git push --force origin main
```

如果权限模型只有：

```text
Bash = dangerous
```

那系统就只能二选一：

```text
所有 Bash 都问用户
```

或者：

```text
所有 Bash 都放行
```

前者会把 Agent 变成 permission-dialog generator。

后者显然又太粗暴。

Claude Code v2.1.88 的权限数据结构至少已经说明，它真正想表达的不是：

```text
ToolName → allow / deny
```

而是更接近：

```text
具体 Tool Call
+
rule content
+
rule source
+
current permission mode
+
working-directory scope
+
current runtime context
        ↓
allow / deny / ask
```


* **parameter-aware authorization**：授权对象不是抽象的 Tool 类别，而是“某个 Tool 在当前上下文下、携带这组具体参数的一次调用”。

---

#### 第一步先把 Capability 和 Authorization 分开

这两个概念特别容易混。

假设系统注册了：

```text
Read
Edit
Bash
WebFetch
Agent
```

那么这定义的是 Agent 的：

```text
Action Surface
```

也就是：

> 模型可以提出哪些种类的动作。

但权限系统回答的是另外一个问题：

> **这一次具体动作是否真的允许进入执行阶段？**

所以：

```text
Tool exists
```

只意味着：

```text
模型可以提出它
```

并不意味着：

```text
这次一定执行
```

可以画成：

```text
             Model
               │
               │ proposes
               ▼
            tool_use
               │
               ▼
        Tool exists?
               │
               ▼
       input valid?
               │
               ▼
       permission?
          /    |    \
       allow  ask   deny
         │     │      │
         ▼     ▼      ▼
      execute human   stop
              input
```

这里 permission 是模型和真实 effect 之间的最后几道门之一。

---

#### Claude Code 的权限结果不是 Boolean

如果自己写最小实现，很容易定义：

```ts
function canUseTool(...): boolean
```

然后：

```text
true
false
```

结束。

但 Claude Code 的 permission behavior 至少明确区分：

```ts
type PermissionBehavior =
  | 'allow'
  | 'deny'
  | 'ask'
```

这三个状态的区别非常重要。

##### `allow`

```text
Harness：
这次调用可以直接继续。
```

##### `deny`

```text
Harness：
这次调用不能执行。
```

##### `ask`

```text
Harness：
我不能独立决定，
需要把 decision boundary
交还给人类。
```

所以权限系统不是简单的：

```text
safe / unsafe classifier
```

而是一套：

```text
machine autonomy boundary
```

---

#### `ask` 其实是一个很关键的状态

因为很多行为本身并不是：

```text
绝对安全
```

或者：

```text
绝对禁止
```

比如：

```bash
git push
```

这件事情不是语法错误，也不是天然恶意。

在某些任务里它甚至就是用户明确要求的目标：

> 改完代码以后帮我提交并 push。

但如果用户只是说：

> 帮我看看这个 bug。

Claude 自己一路修改完以后突然：

```bash
git push
```

就未必应该默认发生。

因此权限系统真正需要的是：

```text
allow automatically
```

和：

```text
never allow
```

之间还有第三种：

```text
require explicit human decision
```

这就是：

```text
ask
```

存在的意义。

---

#### Rule 也不是只有 Tool name

`types/permissions.ts` 中，permission rule 的值被定义成：

```ts
export type PermissionRuleValue = {
  toolName: string
  ruleContent?: string
}
```

这里的：

```text
ruleContent?
```

很重要。

如果权限规则只需要：

```text
toolName
```

那其实定义：

```ts
{
  toolName: "Bash"
}
```

就够了。

但额外存在 `ruleContent` 意味着 permission system 的规则表达能力可以进一步针对 Tool 的**具体内容**。

抽象地说：

```text
Bash
```

可以继续细化成类似：

```text
Bash(some pattern)
```

而不是把整个 Bash Tool 当成一个不可分割的安全单元。

---

#### 为什么 Bash 特别能说明这个问题？

因为 Bash Tool 的 input space 太大。

一个 Tool：

```text
Bash(command: string)
```

实际上背后包含了近乎无数种 effect：

```text
观察
├─ pwd
├─ ls
├─ git status
└─ grep ...

本地修改
├─ mkdir
├─ mv
├─ rm
└─ npm install

版本控制副作用
├─ git add
├─ git commit
├─ git reset
└─ git checkout

外部副作用
├─ git push
├─ curl POST ...
├─ gh pr create
└─ deployment command
```

如果权限单位是：

```text
Tool name
```

那它只能看到：

```text
Bash
Bash
Bash
Bash
```

可如果权限单位能够进一步看到：

```text
Tool + concrete invocation
```

才有机会区分：

```text
Bash("git status")
```

和：

```text
Bash("git push --force origin main")
```

所以这里的核心不是：

> Bash 很危险。

而是：

> **Bash 的 capability surface 太宽，因此授权必须尽可能落到具体 invocation。**

---

#### Permission Context 还带着完整的规则集

回头看上一 Macro 已经出现过的：

```ts
ToolPermissionContext
```

它至少包含：

```ts
mode

additionalWorkingDirectories

alwaysAllowRules

alwaysDenyRules

alwaysAskRules

isBypassPermissionsModeAvailable
```

此外还有 auto mode、危险规则剥离、后台 Agent 无法展示 permission prompt 等相关状态。

所以一次 permission decision 并不是：

```text
tool.checkPermissions(input)
```

孤零零决定的。

它实际上依附于一个更大的权限环境：

```text
                 Tool Call
                     │
                     ▼
           ToolPermissionContext
                     │
     ┌───────────────┼────────────────┐
     │               │                │
     ▼               ▼                ▼
 permission mode   rule sets    directory scope
     │               │                │
     └───────────────┼────────────────┘
                     ▼
             permission decision
```

这也解释了为什么上一 Beat 里：

```text
Tool-specific checkPermissions
```

不能被理解成整个 permission system。

`Tool.ts` 自己就明确写着：

> 通用权限逻辑位于 permission system；Tool 上的方法只补充 Tool-specific logic。

---

#### 为什么会同时有 Allow / Deny / Ask 三套 Rules？

`ToolPermissionContext` 不是一个：

```ts
rules: Rule[]
```

而是显式区分：

```ts
alwaysAllowRules
alwaysDenyRules
alwaysAskRules
```

这说明 Rule 的作用不是单纯：

```text
match / no match
```

匹配之后还有行为：

```text
allow
deny
ask
```

从用户视角很好理解。

比如某个项目里，我可能希望：

```text
读取 repo 内文件
→ 自动允许
```

某些特定命令：

```text
测试 / lint
→ 自动允许
```

某些外部动作：

```text
发布 / push / 删除
→ 总是问
```

某些路径：

```text
workspace 外敏感目录
→ 明确拒绝
```

这里的例子是为了理解规则模型，并不是说 Claude Code 内部恰好预置了这些具体规则。

重点在于权限系统需要表达：

```text
长期允许
长期禁止
长期保留人工确认
```

三种完全不同的 policy。

---

#### Rule 还带着 Source

Claude Code 甚至不只是记录：

```text
allow Bash(...)
```

Permission Rule 还记录来源：

```ts
export type PermissionRuleSource =
  | 'userSettings'
  | 'projectSettings'
  | 'localSettings'
  | 'flagSettings'
  | 'policySettings'
  | 'cliArg'
  | 'command'
  | 'session'
```

于是权限系统不仅知道：

> 这条规则是什么？

还知道：

> **是谁、在哪一层配置了它？**

这在一个真实开发工具里很重要。

例如：

```text
userSettings
```

可能代表个人长期偏好。

```text
projectSettings
```

可能是 repo 层的规则。

```text
localSettings
```

可能只针对当前机器。

```text
policySettings
```

则可能来自组织治理。

```text
session
```

只在当前会话有效。

如果把这些来源全部拍平成：

```text
Set<string> allowedTools
```

就很难回答：

```text
这条权限为什么存在？
它应该修改在哪里？
它是一次性的还是长期的？
```

---

#### 这也是为什么 Permission Update 还需要 Destination

源码的 permission update 不是：

```text
allow forever
```

这么模糊。

它定义了更新去向，例如：

```ts
type PermissionUpdateDestination =
  | 'userSettings'
  | 'projectSettings'
  | 'localSettings'
  | 'session'
  | 'cliArg'
```

同时 Rule Update 可以：

```text
addRules
replaceRules
removeRules
setMode
addDirectories
removeDirectories
```

这个设计特别像真实用户在 permission dialog 里面对的选择：

```text
只允许这一次？
以后这个 session 都允许？
这个项目以后都允许？
```

这些选择在 UI 上可能只是几个按钮。

但 runtime 后面必须落到：

```text
policy mutation
```

否则“记住我的选择”就没有真正含义。

---

#### 工作目录本身也是权限的一部分

`ToolPermissionContext` 中还有：

```ts
additionalWorkingDirectories:
  Map<string, AdditionalWorkingDirectory>
```

对应类型里：

```ts
export type AdditionalWorkingDirectory = {
  path: string
  source: WorkingDirectorySource
}
```

为什么 directory scope 会出现在 permission model 里？

因为：

```text
Read("/project/src/a.ts")
```

和：

```text
Read("~/.ssh/id_rsa")
```

即使使用的都是：

```text
Read
```

其安全含义显然不同。

同理：

```text
Edit("/project/src/a.ts")
```

与：

```text
Edit("/some/unrelated/repo/file")
```

也不能只因为 Tool 都叫：

```text
Edit
```

就得到一样的授权。

这就是 parameter-aware authorization 还不够完整的地方。

更准确地说，授权依赖：

```text
Tool
+
Input
+
Environment scope
```

---

#### 同一个动作，在不同工作区也可能得到不同决定

可以想象：

```text
                 Edit("src/a.ts")
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
cwd = project A             cwd = another place
file inside scope           file outside scope
           │                       │
           ▼                       ▼
potentially routine         potentially elevated
```

所以权限判断不是属性：

```text
Edit.isAllowed = true
```

而更像函数：

```text
permission(
  tool,
  input,
  context
)
→ decision
```

这就是为什么我会把它叫：

> **contextual authorization**

而不是单纯的 Tool whitelist。

---

#### Permission Mode 又是在控制什么？

Claude Code v2.1.88 的类型里可以看到用户侧 mode 包括：

```text
default
acceptEdits
bypassPermissions
dontAsk
plan
```

并且内部还存在受 feature gate 控制的 mode。

这一 Beat 不准备把每个 mode 的完整运行语义全部展开。

但从架构上应该先理解：

```text
Rules
```

和：

```text
Mode
```

不是同一个东西。

Rule 更像：

```text
这个具体动作匹配什么 policy？
```

Mode 更像：

```text
当前 session 整体采用什么授权姿态？
```

因此一次 decision 更接近：

```text
specific rule
    +
global/session mode
    +
current context
```

共同决定。

这比：

```text
safeCommands = [...]
```

已经复杂很多。

---

#### 后台 Agent 甚至可能“不能 Ask”

这里有一个我觉得特别能体现 production Harness 的字段：

```ts
shouldAvoidPermissionPrompts?: boolean
```

源码注释给出的典型场景就是：

```text
background agents
that can't show UI
```

这揭示了一个很有意思的问题。

我们刚刚说：

```text
allow / deny / ask
```

但：

```text
ask
```

本身需要一个前提：

> **当前执行单元真的有办法把问题问到用户面前。**

主 Agent 在交互 CLI 里可能可以：

```text
需要执行这个命令，允许吗？
```

可后台 subagent 如果没有交互 UI：

```text
Agent
   ↓
needs permission
   ↓
ask whom?
```

就不能永远阻塞在那里。

所以 permission policy 还必须考虑：

```text
execution topology
```

这正是 Agent 从聊天机器人变成长时间 runtime 后才会出现的问题。

---

#### `ask` 不是错误，而是主动缩小 Agent 自治边界

我觉得这点也值得重新理解。

很多人会把 permission prompt 看成：

```text
Agent 不够自动化
```

于是理想状态是：

```text
永远不要问我
```

但真正可靠的 Harness 并不是：

```text
autonomy = 100%
```

而是：

```text
在高可靠区域自动行动
在边界区域显式交还决策权
```

于是：

```text
ask
```

不是 permission system 的失败。

恰恰是 permission system 正常工作的一个结果。

可以画成：

```text
                Action space

        low risk / known
        ┌────────────────┐
        │     allow      │
        └────────────────┘

        uncertain / consequential
        ┌────────────────┐
        │      ask       │
        └────────────────┘

        forbidden
        ┌────────────────┐
        │      deny      │
        └────────────────┘
```

这里实际上已经开始和后面 Anthropic 的：

```text
earned autonomy
```

产生联系。

只不过我们现在先在 Claude Code runtime 里看最底层的机制。

---

#### 为什么不能把所有写操作都 Ask？

因为这样会毁掉 Agent 的 long-horizon execution。

假设 Agent 在一个小时里要：

```text
Edit
Edit
pytest
Edit
pytest
Edit
...
```

如果每次文件写入都：

```text
Allow?
Allow?
Allow?
Allow?
```

人类就重新成为 loop 的同步 bottleneck。

Agent 表面上很 autonomous。

实际上：

```text
每 30 秒等一次人
```

那长任务根本没有意义。

所以 permission engineering 真正困难的是：

> **怎样既不把能力全部放开，又不把所有步骤都升级成人工审批？**

这就是：

```text
rules
modes
scope
remembered decisions
```

这些机制存在的根本原因。

---

#### 可以把 Permission System 看成自治预算分配器

不是所有动作都需要同样多的人类注意力。

例如抽象地说：

```text
低副作用动作
→ Harness 自动处理

已经明确授权的重复动作
→ Harness 自动处理

超出当前范围的动作
→ 重新询问

明确禁止的动作
→ 直接拒绝
```

于是人类注意力只被用在：

```text
decision boundary
```

而不是每个 Tool Call。

这其实和 Anthropic 长任务 Harness 一开始提出的问题非常接近：

> 当 Agent 可以长期运行以后，人类不能继续逐动作监督。

否则瓶颈根本没有消失。

---

#### 一个更准确的权限执行链

所以到这里，可以把上一 Macro 的 Tool pipeline 补完整：

```text
Model
  │
  ▼
tool_use
  │
  ▼
Input Schema
  │
  ▼
validateInput
  │
  ▼
Permission System
  │
  ├── rules
  ├── mode
  ├── working-directory scope
  ├── tool-specific checks
  └── interaction availability
  │
  ▼
allow / ask / deny
  │
  ├──────── ask ───────→ Human
  │                       │
  │                       ▼
  │                  permission update
  │                       │
  └───────────────────────┘
  │
  ▼
Scheduling
  │
  ▼
tool.call()
  │
  ▼
Environment
```

这样看以后：

```text
Permission
```

就不再像一个独立弹窗系统。

它其实是：

> **Harness 把模型意图转换成真实副作用过程中不可缺的一层 policy enforcement。**

---

#### 一个适合面试的回答：Claude Code 为什么不直接给 Tool 做白名单？

如果面试官问：

> Tool 不就是白名单吗？允许 Read、Bash、Edit，不就行了吗？

我现在会回答：

Tool whitelist 只解决 capability discovery，不能解决 invocation-level authorization。

同一个 Tool 的不同 input 可以有完全不同的副作用：

```text
Bash("git status")
```

和：

```text
Bash("git push --force")
```

都叫 Bash。

所以生产 Harness 需要：

```text
Tool identity
+
concrete input
+
permission rules
+
working-directory scope
+
current permission mode
```

共同决定：

```text
allow
ask
deny
```

更进一步，还需要记录：

```text
规则来自 user/project/policy/session 哪一层，
用户新的选择应该写回哪一层。
```

这才是完整授权系统。

---

#### Capability 和 Authorization 的最终关系

可以压成一句：

```text
Capability 决定模型“能提出什么”；
Authorization 决定系统“允许发生什么”。
```

模型看到：

```text
Bash
```

表示：

> 我有能力请求 Shell action。

并不等于：

> 所有 Shell effect 都属于我的自治范围。

这一区别对于 Coding Agent 特别重要。

因为 Tool surface 一旦变宽：

```text
Shell
Browser
GitHub
Cloud
Database
MCP
```

模型能够提出的动作会迅速超过：

```text
用户希望它无需监督就执行的动作
```

两者之间那块差值，就是 Permission System 必须管理的地方。

---

#### 再接回父文的“约束”

到现在，父文里的：

```text
约束
```

已经开始具体起来。

它不是一句：

> 给 Agent 加 Guardrail。

而是：

```text
Model intention
      ↓
schema
      ↓
semantic validation
      ↓
authorization
      ↓
effect-aware scheduling
      ↓
execution
```

每一层都在缩小：

```text
模型理论上可以提出的动作
```

与：

```text
当前环境真正允许发生的动作
```

之间的距离。

所以 Harness 的“约束”更准确地说，是：

> **在不拿走模型行动能力的前提下，为真实副作用建立明确的执行边界。**

---

#### 源码与证据边界

从 Claude Code v2.1.88 的恢复源码，可以直接确认：

* Permission behavior 至少区分 `allow`、`deny` 和 `ask`；
* Permission Rule Value 包含 `toolName` 和可选 `ruleContent`，因此规则表达能力不局限于 Tool name；
* Permission Rule 记录来源，包括 user/project/local/policy/CLI/session 等层级；
* `ToolPermissionContext` 持有 `alwaysAllowRules`、`alwaysDenyRules`、`alwaysAskRules`、permission mode 和 additional working directories 等信息；
* Permission update 可以针对不同 destination 添加、替换、删除规则，以及改变 mode 或 directory scope；
* Tool-specific `checkPermissions()` 不是整个授权系统；`Tool.ts` 明确说明 general permission logic 位于 permission subsystem，并且该检查发生在 `validateInput()` 通过之后。
* Permission context 还考虑后台执行单元无法展示 permission prompt 的情况。

### 1.2 Macro 4 小结

权限系统真正解决的不是：

```text
哪些 Tool 危险？
```

而是：

```text
这一次具体动作，
在当前 context 和已有授权下，
属于 Agent 的自治范围吗？
```

所以最有用的模型是：

```text
Capability
        │
        │ Model can request
        ▼
    Tool Call
        │
        ▼
Authorization
        │
   ┌────┼────┐
   ▼    ▼    ▼
 allow ask  deny
   │    │
   │    ▼
   │   Human
   │
   ▼
Environment
```

这也让我觉得：

> **好的 Permission System 不是尽可能阻止 Agent，而是尽可能准确地划出 Agent 可以自主行动的边界。**


现在前四个 Macro 已经回答了：

```text
任务怎样持续？
        ↓
动作怎样进入现实？
        ↓
动作怎样安全调度？
        ↓
哪些动作被授权发生？
```

但还有一个最容易被 Coding Agent 自己骗过去的问题：

> **动作都执行完以后，谁来证明任务真的完成了？**

模型自己很容易说：

```text
实现完成。
测试应该已经没问题。
页面看起来应该正常。
```

可“我认为完成了”和“现实证明完成了”不是同一件事。

这正是 Anthropic 长任务 Harness 实验里第二个非常核心的失败模式：

**self-evaluation failure。**

下一 Macro 我们暂时离开 Claude Code 的底层 Tool runtime，回到 Anthropic 那篇长任务 Harness 文章：

