## 1. 当 Agent 已经会写代码，为什么还需要 Symphony？

Symphony 出现之前，OpenAI 已经在尝试一种相当激进的开发方式：让一个内部代码仓库中的每一行代码都由 Codex 生成。为此，他们先解决了代码库本身是否适合 Agent 工作的问题，包括自动化测试、guardrail，以及此前 [Harness Engineering](https://openai.com/index/harness-engineering/) 一文讨论的环境和工具建设。

模型已经能够读代码、修改文件、运行测试，接下来遇到的瓶颈却不在单次编码能力上。工程师开始同时打开多个 Codex session，把不同任务分配出去，再逐个检查输出、补充指令和处理异常。按照 OpenAI 在 [Symphony](https://openai.com/zh-Hans-CN/index/open-source-codex-orchestration-symphony/) 文章中的内部观察，大多数人通常只能同时管理 **3～5 个 session**；再往上增加，会话之间的上下文切换开始抵消并行执行带来的收益。

这也是 Symphony 要处理的问题：如果 Coding Agent 已经可以独立完成越来越长的工作，人还要不要继续以“盯住每一个 session”的方式来组织这些 Agent？

### 1.1 3～5 个 Session 之后，瓶颈落到了人类注意力

交互式 Coding Agent 最自然的使用方式，是从一个会话开始。工程师给出任务，Agent 读取代码、执行命令、修改文件；中间遇到歧义时，人继续补充上下文，最后检查 diff 和测试结果。

单个任务时，这种模式没有明显问题。任务增加以后，最直接的扩展方式通常是多开几个 session：

```text
Session A
修登录接口的 regression

Session B
升级前端依赖

Session C
补数据库 migration

Session D
调查 CI 偶发失败
```

四个 Agent 可以同时工作，但工程师并没有退出这四条执行链。每个 session 仍然需要有人记住它在做什么、上一次停在哪里、是否跑偏、什么时候应该继续，以及最终输出是否已经满足任务要求。

于是人的工作逐渐变成另一种 loop：

```text
分配任务
  ↓
切到 Session A
  ↓
检查当前进度
  ↓
补一句 steering
  ↓
切到 Session B
  ↓
发现测试还没跑
  ↓
要求继续
  ↓
切到 Session C
  ↓
处理一个停滞的命令
  ↓
再回 Session A
```

OpenAI 描述的 3～5 个 session 上限不是模型并发能力的限制，而是他们观察到的人类操作经验：session 再多以后，工程师会忘记不同 Agent 正在处理什么，需要在终端之间来回切换，把跑偏的 Agent 拉回来，还要处理那些执行到一半停滞的长任务。

这里可以把两种并行度分开看：

```text
Model concurrency
=
同时可以运行多少 Agent

Human supervision bandwidth
=
一个工程师还能持续理解并管理多少 Agent
```

把前者从 1 提高到 10，并不会自动把后者也提高到 10。只要每个 Agent 都要求人持续维护一份“它现在做到哪里”的短期记忆，人就仍然处在所有执行路径的关键路径上。

这也解释了为什么简单增加后台 Agent 或终端窗口不能解决问题。假设一个工程师可以启动 20 个 session，但每天仍然需要依次打开这 20 个窗口判断：

```text
完成了吗？
为什么停了？
测试跑了吗？
PR 创建了吗？
CI 过了吗？
现在应该继续做什么？
```

那么调度、恢复和状态跟踪只是从模型那里转移给了人。Agent 的执行速度提高以后，这部分人工协调成本反而会更加明显。

因此，Symphony 面对的第一个问题并不是：

```text
怎样让 Codex 写得更好？
```

而是：

```text
怎样让工程师不必持续管理
每一个正在工作的 Codex session？
```

要做到这一点，仅仅把 session 放到后台还不够。系统需要一个独立于某次对话的工作对象，能够记录“什么工作仍然存在、现在处于什么阶段、是否还应该继续执行”。

### 1.2 真正需要被管理的是 Work，而不是 Session

OpenAI 在 Symphony 中做的第一个抽象调整，是重新选择编排系统所围绕的对象。

原来的工作方式很容易形成这样的关系：

```text
一个任务
    ↓
开一个 Codex Session
    ↓
Agent 工作
    ↓
得到一个 PR
```

如果任务都很短，这三个对象看起来几乎可以互换。工程师说“那个 session”，往往就是在说“那个任务”；看到 PR merge，也往往可以认为对应的工作已经结束。

长任务会打破这种一一对应关系。

一个 issue 可能需要 Agent 多次运行，中间经历进程退出、重试、代码评审和 CI 修复。它也可能跨越多个代码仓库，最终生成不止一个 PR。反过来，有些 issue 只是让 Agent 调查代码库、整理资料或形成实现方案，最终根本不会产生 PR。

于是：

```text
Issue
≠
Session
≠
Pull Request
```

它们描述的是三种不同对象。

`Session` 是一次 Agent 交互或运行过程，随时可能结束；`Pull Request` 是代码变更进入 review 和 merge 流程的一种 artifact；`Issue`、task 或 ticket 则描述一份仍然需要完成的工作。只要工作还存在，某一次 session 是否已经退出并不应该决定任务是否消失。

可以用一个稍长的任务来看这种区别。假设 issue 是：

```text
Migrate frontend build system from Webpack to Vite
```

执行过程中可能出现：

```text
Issue
  │
  ├─ Session 1
  │    └─ 分析现有构建配置
  │
  ├─ Session 2
  │    └─ 修改 Vite 配置与入口
  │
  ├─ Session 3
  │    └─ 修复测试和 CI
  │
  └─ Pull Request
       └─ 最终进入 review
```

如果 Session 2 因进程异常退出，这意味着一次执行失败，并不意味着：

```text
Vite migration 已经不存在
```

同样，如果 Agent 已经创建 PR，但 CI 仍然失败，那么：

```text
PR exists
```

也不能推出：

```text
work completed
```

因此，能够长期存在的工作对象应该位于 session 之上。OpenAI 选择直接利用团队已经在使用的 issue tracker：任务的标题、描述、状态、依赖关系和后续 review 都已经在那里，没必要再维护一套只供 Agent 使用的平行任务系统。

这个变化可以画成两种管理方式。

```text
Session-centric

                   Human
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
      Session A  Session B  Session C
          │          │          │
          ▼          ▼          ▼
        Agent      Agent      Agent
```

人的注意力直接挂在每个运行中的 session 上。session 越多，需要同时维护的执行上下文也越多。

Symphony 改成：

```text
Work-centric

                   Issue Tracker
                        │
                 durable work state
                        │
                        ▼
                    Symphony
               ┌────────┼────────┐
               │        │        │
               ▼        ▼        ▼
            Issue A  Issue B  Issue C
               │        │        │
               ▼        ▼        ▼
             Agent    Agent    Agent
```

工程师主要操作的是 issue，而不是某个 Codex 窗口。Agent session 成为处理 issue 的运行资源：需要时可以启动，失败后可以重新启动，任务进入不再需要 Agent 的状态后也可以停止。

这也是为什么 OpenAI 把这种变化称为从 session 和 PR 转向 work。软件团队原本就围绕 issue、task、ticket 和 milestone 组织交付，Symphony 只是让 Coding Agent 进入了这套已经存在的工作系统。

这里还有一个后面会反复出现的区分：

```text
Agent process is ephemeral.
Work item is durable.
```

一次 Agent run 可以失败，workspace 可以继续存在；一个 Codex thread 可以结束，issue 仍然可以保持 active；甚至具体执行 Agent 可以被替换，只要系统仍然知道这份工作是什么、现在是否应该继续。

把编排对象放在 work item 上以后，恢复机制才有稳定的参照物。否则系统只能知道“某个进程退出了”，却不知道“它原本承担的工作是否仍然需要执行”。

### 1.3 Symphony 到底负责什么

把 issue 作为工作对象以后，还需要一个组件把任务系统和 Coding Agent 接起来。OpenAI 对 Symphony 的描述很直接：它把类似 Linear 的项目管理看板变成 Coding Agent 的 **control plane**。

这里的 control plane 不负责亲自写代码。它回答的是另一组运行时问题：

```text
现在有哪些工作可以执行？

哪些工作已经有人处理？

哪些任务还被依赖阻塞？

每个任务应该在哪个 workspace 运行？

Agent 退出以后是否还需要继续？

外部 issue 状态变化后，
当前运行中的 Agent 是否还应该存在？
```

因此，从外部看，Symphony 的基本路径可以先压缩成：

```text
Issue Tracker
      │
      │ candidate work
      ▼
   Symphony
      │
      │ dispatch
      ▼
Per-Issue Workspace
      │
      ▼
 Coding Agent
      │
      │ result / progress / failure
      ▼
   Symphony
      │
      └────→ continue / retry / stop
```

官方博客给出的简单模型是，每个未关闭的 Linear issue 都对应一个专属 Agent workspace，Symphony 持续观察任务看板，并让仍然需要工作的任务保持 Agent 执行。如果 Agent 崩溃或卡住，编排器可以再次启动执行；出现新的 eligible work 后，也不再要求工程师手工新建一个 Codex 会话。

这里容易产生一个误解：既然 Symphony 决定哪个任务什么时候运行，它是不是也要决定 Agent 每一步应该调用什么 Tool、先改哪个文件、什么时候运行哪条测试？

并不是这样。至少在 Symphony 的设计里，orchestration 和 coding-agent reasoning 仍然是两层职责。

```text
Symphony
负责：
work discovery
claim
dispatch
workspace lifecycle
retry
reconciliation
concurrency
observability

Codex
负责：
理解任务
读取代码
决定实现路径
调用工具
修改文件
运行测试
处理执行过程中的局部问题
```

前者解决“这份工作怎样持续存在并被执行”，后者解决“当前拿到这份工作以后应该怎样完成”。Symphony 没有因为位于 Agent 上层，就重新实现一套更大的 Coding Agent。

这种分工和单个 Claude Code / Codex runtime 处理的问题也不同。单个 Coding Agent 的 runtime 主要维持一次任务内部的模型—工具循环，例如：

```text
LLM
 ↓
tool call
 ↓
environment
 ↓
tool result
 ↓
LLM
```

Symphony 位于更外层：

```text
Issue
  ↓
Orchestrator
  ↓
Agent Run
  ↓
LLM ↔ Tools
```

最里面的 loop 解决一次 Agent 如何继续思考和行动；外面的 loop 解决某个 work item 在跨 session、跨失败甚至跨较长时间以后，怎样仍然有人继续处理。

因此，我暂时会把 Symphony 看成一个 **work-item-oriented coding-agent scheduler/runner**，而不是一个新的模型推理框架。它从 issue tracker 中读取可以工作的任务，为任务分配隔离运行环境，启动 Coding Agent，再根据任务状态和运行结果决定继续、重试或停止。

不过到这里仍然只是外部模型。下面还有几个尚未回答的问题：一个 Linear issue 如何避免被重复 dispatch，Agent 正在工作时 issue 被人改成其他状态怎么办，两个 issue 能否同时运行，以及一次 Agent 正常退出为什么仍然可能需要继续执行。

这些问题需要进入 Symphony 自己维护的 orchestration state。下一部分从 issue tracker 作为 control plane 开始，把 tracker state、workspace 和 task dependency 分开来看。

## 2. 把 Issue Tracker 变成 Control Plane，到底改变了什么？

上一节把 Symphony 的编排对象从 `Session` 换成了 `Issue`。但如果只是定期读取 Linear，再替工程师执行一次 `codex` 命令，这还称不上一个能够长期运行的 orchestration service：系统还需要知道每个任务在哪里工作、当前是否已经有人执行，以及哪些任务现在根本不应该启动。

Symphony 因此没有把 issue tracker 只当成一个 prompt 来源。任务状态、依赖关系和项目范围会参与 dispatch，issue identifier 又会进一步映射到独立 workspace；与此同时，Orchestrator 还维护一套不写回 tracker 的运行时状态，用来避免重复执行和追踪 retry。这样才形成了 OpenAI 所说的 control plane。

### 2.1 一个 Issue 对应一个长期存在的 Workspace

如果 Agent 只执行一次，临时目录通常已经够用：

```text
receive task
    ↓
create temp directory
    ↓
run agent
    ↓
return result
    ↓
delete directory
```

Symphony 面对的任务生命周期更长。一次 issue 可能经历多个 Codex turn，也可能因为进程异常、超时或其他失败重新启动 worker；如果每次重新执行都回到一份全新的文件系统状态，Agent 上一次已经完成的修改也会跟着消失。

因此当前 Symphony `SPEC.md` 使用的是 per-issue persistent workspace：

```text
Issue MT-649
     │
     ▼
workspace key
     │
     ▼
<symphony_workspaces>/MT-649
     │
     ├─ Run 1
     ├─ Run 2
     └─ Run 3
```

这里最容易混淆的是：

```text
Run lifecycle
≠
Workspace lifecycle
```

`Run Attempt` 描述一次执行尝试；`Workspace` 则属于 issue。正常 run 结束以后，workspace 不会因为这次 Codex 进程退出就自动删除，后续 continuation 或 retry 可以回到同一个目录继续工作。

当前语言无关规范对这个映射给得相当具体。`Issue` 同时有两个容易混淆的标识：

```text
id
=
tracker scope 内部使用的稳定 dispatch identity

identifier
=
人类可读的 ticket key
例如 MT-649
```

Orchestrator 内部的 map 主要使用 opaque `id`，workspace naming 则从 `identifier` 派生。这样做的原因并不复杂：调度器需要一个不会因为显示格式改变而产生歧义的内部身份，而工程师查看日志和磁盘目录时，更希望看到 `MT-649` 而不是一串 provider-specific ID。

规范还要求 `identifier` 在当前 tracker scope 内唯一，并把它转换成合法的 `workspace_key`：

```text
issue.identifier
      │
      ▼
sanitize
[A-Za-z0-9._-]
      │
      ▼
workspace_key
      │
      ▼
<workspace.root>/<workspace_key>
```

如果原始 identifier 中包含不允许用于目录名的字符，不能只简单替换然后结束。因为：

```text
A/B
A?B
```

都可能被朴素地处理成：

```text
A_B
```

两个不同 issue 最终撞进同一个 workspace。

当前规范因此要求：如果 sanitization 改变了原始 identifier，还要附加基于原字符串生成的稳定 hash suffix，并要求至少提供 64 bit entropy，使两个经过清洗后文本相同的 identifier 仍然能够得到不同目录。

不过这里不要进一步推出：

> Symphony 为每个 issue 创建一个 Git worktree。

这并不是规范要求。

Symphony 强制的是：

```text
Issue
  ↓
deterministic isolated directory
```

至于目录里的代码怎样出现，可以是：

```text
git clone
git worktree
checkout
rsync
prebuilt image
其它 bootstrap 逻辑
```

当前 `SPEC.md` 把 workspace population 明确保留为 implementation-defined，常见准备逻辑可以通过 `after_create`、`before_run` 等 hook 完成。

所以 Symphony 的 workspace isolation 与 Git branch、Git worktree 是不同层次的概念：

```text
Workspace
=
Agent 实际执行命令的 filesystem boundary

Branch / Worktree
=
一种可能的 VCS 实现方式
```

这个区别到了安全边界时还会更明显。规范要求启动 Coding Agent 前确认：

```text
cwd == workspace_path
```

并且：

```text
workspace_path
必须位于
workspace_root
内部
```

也就是说，workspace 不是为了把目录排得整齐，而是在定义某个 issue 的 Agent 能够从哪个工作环境开始执行。具体 sandbox 能限制到什么程度仍然取决于 Codex 和宿主环境；Symphony 本身并没有因为创建了目录，就自动获得完整的 filesystem sandbox。

到这里，一个 issue 已经有了稳定的执行位置。但仅有 workspace 还不能阻止另一个 poll tick 再次启动同一个 issue，因为 tracker 只告诉 Symphony“这个任务处于 In Progress”，并不知道当前进程里是不是已经有一个 worker 正在处理它。

这就需要第二套状态。

### 2.2 Tracker State 与 Orchestrator State 不是同一套状态

假设 Linear 中有一个 issue：

```text
MT-649
"Add cache invalidation for user profile"

State:
In Progress
```

`In Progress` 对产品团队已经足够明确：这个任务已经开始，目前还没有结束。但对于 scheduler 来说信息还不够，因为下面几种情况在 tracker 上都可能显示同一个状态：

```text
In Progress
│
├─ 还没有 Agent 运行
│
├─ Agent 正在运行
│
├─ 上一次 Agent 刚失败
│  正在等待 retry
│
└─ Agent 刚正常退出
   准备继续检查是否还有工作
```

如果 Orchestrator 只看：

```text
state == "In Progress"
```

那么每次 poll 都可能重新启动一个 worker。

因此 Symphony 必须同时维护两种状态。

第一种来自外部 tracker：

```text
Tracker State

Todo
In Progress
Human Review
Done
Canceled
...
```

它回答：

```text
这项工作在团队流程中处于什么阶段？
```

具体名称由 provider 和项目配置决定。Symphony 只会配置哪些属于 `active_states`、哪些属于 `terminal_states`，并在调度时比较当前 issue state。

第二种只存在于 Orchestrator runtime：

```text
Orchestration State

Unclaimed
Claimed
Running
RetryQueued
Released
```

它回答的是：

```text
Symphony 当前是否占有这项工作？
有没有 worker 正在执行？
有没有 retry 已经排队？
```

两者可以组合成这样的情况：

| Tracker State  | Orchestrator State | 当前含义                      |
| -------------- | ------------------ | ------------------------- |
| `Todo`         | `Unclaimed`        | tracker 中存在可执行工作，目前没人处理   |
| `In Progress`  | `Running`          | worker 正在处理这个 issue       |
| `In Progress`  | `RetryQueued`      | 当前没有 worker，但任务已保留给 retry |
| `Human Review` | `Released`         | Agent 已交棒，不再占用任务          |
| `Done`         | `Released`         | 任务已经进入终态                  |

这里尤其需要注意 `Claimed`。

它不是产品工作流里多出来的一个阶段，也不要求 Linear 新增一个名为 Claimed 的 column。它是 Orchestrator 内部的 reservation：

```text
candidate issue
     │
     ▼
   Claim
     │
     ├─ Running
     │
     └─ RetryQueued
```

只要某个 issue 已经存在于：

```text
claimed
```

集合中，后面的 poll 就不能再次把它当成一项没人处理的新工作。

于是：

```text
Tracker:
In Progress

并不能推出：

Symphony:
可以 dispatch
```

Scheduler 还要检查：

```text
state eligible?
dispatchable?
required labels match?
already running?
already claimed?
global slot available?
per-state slot available?
```

这些条件全部通过，issue 才真正拥有一次新的 dispatch 机会。

当前 `SPEC.md` 甚至明确要求所有调度状态修改都由一个 authoritative orchestrator 串行管理，并在 worker 启动之前检查：

```text
claimed
running
```

这样做解决的是同一个进程内部的 duplicate dispatch，而不是构建一个完整的分布式事务系统。当前 Draft v1 也没有要求用持久化数据库保存 scheduler state；服务重启以后，精确的 `running`、`claimed` 和 retry timer 不会被原样恢复。

恢复依赖的是两个更持久的事实来源：

```text
Issue Tracker
+
Filesystem Workspaces
```

这也是为什么前一节把 issue 称作 durable work item，而没有把 Orchestrator 内存状态称作 durable task state。Symphony 可以重新读取 tracker，再根据 workspace 和当前 issue 状态重新建立运行关系；它并没有承诺恢复崩溃前每一个内存对象。

因此，下面三个概念最好一直分开：

```text
Tracker State
=
团队对工作生命周期的定义

Orchestrator State
=
当前 Symphony 进程的执行占有关系

Workspace State
=
这项工作已经在文件系统中留下了什么
```

它们彼此有关，但任何一个都不能完整替代另外两个。

例如：

```text
Tracker: In Progress
Orchestrator: RetryQueued
Workspace: 已经修改 17 个文件
```

这是一个完全合理的状态。Agent 现在没有运行，但前面的工作没有丢，Orchestrator 又知道这个 issue 已经被 claim，等 retry timer 到期以后可以重新回到原 workspace 继续。

有了这三层状态以后，Symphony 才能把 tracker 真正用于调度，而不是仅仅定时扫描一个 Todo List。

### 2.3 依赖关系怎样形成可并行的 Task DAG

有了多个独立 workspace 以后，下一步自然会遇到并发问题。

假设项目里有三个任务：

```text
A: Upgrade React
B: Migrate frontend to Vite
C: Update documentation
```

如果 B 依赖 A，那么同时启动：

```text
Agent A → 修改 React 版本和相关 API
Agent B → 根据旧 React 状态修改 Vite 配置
```

可能只是在制造一组马上失效的修改。

工程团队本来就会在 issue tracker 里描述这种关系。例如：

```text
A: Upgrade React
        │
        │ blocks
        ▼
B: Migrate to Vite
        │
        │ blocks
        ▼
C: Remove legacy build config
```

一旦 tracker 中已经存在这些 dependency，Orchestrator 没必要再维护另一份人工同步的：

```text
task_graph.yaml
```

OpenAI 的 Symphony 博客描述的内部工作方式就是利用 Linear 中已有的依赖和状态：被其他 issue 阻塞的任务先不进入运行集合；前置任务完成、blocker 解除以后，后继任务才变成可以领取的工作。

从效果上看，整个 project backlog 就形成了一张 work graph：

```text
                 ┌─→ B ──→ D
                 │
A ───────────────┤
                 │
                 └─→ C ──→ E
```

只要 B 和 C 之间没有依赖关系，并且当前 concurrency budget 允许，它们就可以分别进入不同 workspace：

```text
            ┌─ Issue B
            │    ↓
Issue A ────┤  Workspace B
 completed  │    ↓
            │  Agent B
            │
            └─ Issue C
                 ↓
               Workspace C
                 ↓
               Agent C
```

这里的并行度来自：

```text
work dependencies
+
available concurrency
```

而不是：

```text
看到很多 ticket
→ 全部同时启动
```

不过如果只读 OpenAI 博客，很容易继续把这个设计抽象成：

> Symphony 内部维护了一套通用 DAG scheduler。

当前语言无关 `SPEC.md` 刻意没有这样规定。

规范中的标准 `Issue` 确实保留了：

```text
blocked_by
```

字段，其中可以携带 blocker 的：

```text
id
identifier
state
```

但这个字段被定义成：

```text
best-effort provider metadata
```

更关键的是，通用 scheduler 并不负责读取 `blocked_by` 后自行推导：

```text
这个 blocker 算不算完成？
跨项目 blocker 怎么解释？
Canceled 算解除依赖吗？
Duplicate 算不算 terminal？
父子 ticket 是不是 dependency？
```

这些语义在 Linear、GitHub Projects、Jira 或其它 tracker 中未必相同。

因此规范又要求 adapter 输出一个明确字段：

```text
dispatchable: boolean
```

它表示：

> provider-specific eligibility 已经通过。

例如某个 Linear adapter 可以根据：

```text
assignment
board membership
blocker semantics
```

计算出：

```text
dispatchable = false
```

然后通用 Orchestrator 只需要把它作为 candidate selection 的一个条件。

边界因此变成：

```text
Provider / Adapter
负责理解：
“这个 tracker 中什么叫可领取？”

                ↓

Normalized Issue
dispatchable = true / false

                ↓

Generic Orchestrator
继续检查：
active state
required labels
claim
retry
global concurrency
per-state concurrency
```

这和 `blocked_by` 的存在并不冲突。`blocked_by` 可以保留下来用于 prompt、日志、dashboard 或 provider-native tools，但 Core Scheduler 不需要为了支持所有 tracker，发明一套看似统一、实际会损失 provider semantics 的 dependency language。

所以更准确的说法不是：

```text
Symphony 是一个 DAG Workflow Engine
```

而是：

```text
Symphony 可以消费
Issue Tracker 已经表达出来的工作依赖，

并让这些依赖参与
“当前任务是否可以 dispatch”
这一判断。
```

它甚至在 `SPEC.md` 的 Non-Goals 中明确排除了：

```text
General-purpose workflow engine
Distributed job scheduler
```

这一点反而把 Symphony 的范围限制得更清楚。它不准备替代 Airflow、Temporal 或 Kubernetes scheduler，也不要求用户把整套软件工程过程重新编码成一张新的工作流图。

它只需要回答一个更窄的问题：

```text
当前有哪些 issue
已经满足进入 Coding Agent 的条件？
```

于是到一个 poll tick 开始时，Symphony 面对的已经不是简单的：

```text
fetch all Todo issues
```

而是一批带有状态和运行约束的 candidate work：

```text
Issue Tracker
      │
      ▼
active-state candidates
      │
      ▼
provider eligibility
(dispatchable)
      │
      ▼
required labels
      │
      ▼
claim / running check
      │
      ▼
concurrency check
      │
      ▼
dispatch
```

到这里，Issue Tracker 作为 control plane 的含义就比较具体了。它保存团队真正关心的 work state 和 provider-specific workflow；Symphony 则保存短期的 execution state，并把 eligible issue 映射到隔离 workspace 和 Agent run。

下一步还缺的是时间维度：poll tick 到底按什么顺序处理这些对象，一次正常 Agent exit 为什么不等于任务结束，失败以后什么时候重试，外部 tracker 在 Agent 运行期间发生变化又怎样收敛回来。Macro 3 再把这条运行时链路从 `Poll` 一直追到 `Retry` 和 `Reconciliation`。

## 3. 一个 Issue 从发现到失败重试，Runtime 实际发生了什么？

前两节已经有了三个长期存在的对象：

```text
Issue Tracker
Workspace
Orchestrator State
```

但它们还只是静态关系。Symphony 真正运行起来以后，需要不断回答另一组带时间的问题：什么时候重新读取 tracker，哪些 candidate 可以启动，一个 Codex turn 完成以后是否应该继续，worker 异常退出以后多久再试，以及运行期间 issue 状态被人修改时，已经启动的 Agent 要不要停下来。

当前语言无关 `SPEC.md` 把这些行为集中在一个持续运行的 poll loop 中。Orchestrator 是调度状态的单一修改者；每个 tick 先处理已经运行的工作，再决定要不要启动新的工作。这个顺序很关键，因为系统不能一边基于旧状态派发新 worker，一边等下一轮才发现现有任务早已失去执行资格。

### 3.1 Poll、Claim 与 Dispatch：一次 Tick 到底做什么

Symphony 是一个 long-running service，不是收到一次 HTTP 请求以后就结束的 CLI wrapper。服务启动后会先验证配置、清理已经进入 terminal state 的遗留 workspace，然后立即执行一次 tick；之后按照 `polling.interval_ms` 周期重复。

当前规范中的默认值是：

```text
polling.interval_ms = 30000
```

也就是 30 秒。

一次 tick 的逻辑顺序可以压成：

```text
Tick
 │
 ├─ 1. Reconcile running issues
 │
 ├─ 2. Validate current workflow/config
 │
 ├─ 3. Fetch active-state candidates
 │
 ├─ 4. Sort candidates
 │
 ├─ 5. Check eligibility
 │
 ├─ 6. Claim issue
 │
 └─ 7. Dispatch worker
```

这里第一步不是：

```text
fetch new work
```

而是：

```text
reconcile old work
```

因为已经运行中的 worker 可能在过去 30 秒内失去了继续运行的理由。例如：

```text
In Progress
     ↓
人类手动改成 Done
```

或者：

```text
required label 被移除
```

如果不先处理这些变化，新一轮 dispatch 就是在一个过期的世界模型上继续增加工作。

完成 reconciliation 后，Orchestrator 才执行 dispatch preflight validation。`WORKFLOW.md` 无法读取、tracker 配置无效、Codex command 缺失等问题会阻止这一轮产生新的 worker，但并不要求整个 service 立即崩溃；已经存在的运行状态仍然尽可能继续被观察和收敛。

然后才从 tracker 获取处于 configured `active_states` 的 issue。

这里的结果仍然只是：

```text
candidate
```

不是：

```text
worker
```

真正 dispatch 之前还要连续通过多层判断：

```text
required core fields exist?
        │
        ▼
state ∈ active_states?
        │
        ▼
state ∉ terminal_states?
        │
        ▼
dispatchable == true?
        │
        ▼
required labels match?
        │
        ▼
not running?
        │
        ▼
not claimed?
        │
        ▼
global slot available?
        │
        ▼
per-state slot available?
        │
        ▼
dispatch
```

这几层判断处理的是不同问题。

`state` 判断任务在业务流程上是否处于允许 Agent 工作的阶段；`dispatchable` 由 tracker adapter 表示 provider-specific eligibility；`claimed / running` 避免同一个 Symphony 进程重复派发；最后两项则限制并发规模。

全局可用槽位的计算很直接：

$$
available\_slots
=
\max(
max\_concurrent\_agents-running\_count,\ 0
)
$$

当前规范中的默认值是：

```text
agent.max_concurrent_agents = 10
```

所以如果：

```text
max_concurrent_agents = 10
running_count = 7
```

那么当前最多还能启动：

```text
3 workers
```

规范同时支持：

```text
agent.max_concurrent_agents_by_state
```

例如团队可以配置：

```yaml
agent:
  max_concurrent_agents: 10
  max_concurrent_agents_by_state:
    "In Progress": 6
    "Needs Fix": 2
```

于是即使全局还有空位，也可以限制某类工作一次运行多少个 Agent。

这不是为了让 YAML 看起来更完整。不同状态的任务可能对应不同成本，例如：

```text
In Progress
可能是普通实现

Needs Fix
可能意味着：
已有 PR
已有 review feedback
需要反复访问 CI / GitHub
```

团队可以让调度器在不改变 tracker workflow 的前提下，控制不同工作阶段消耗多少 Agent capacity。

如果同一轮里有多个 candidate，则还需要决定先派谁。当前 Draft v1 给出的排序意图是：

```text
1. priority
2. created_at
3. identifier
```

其中有效 priority `1..4` 按数字从小到大排序，未知值和其他整数放在后面；同优先级时优先处理更早创建的 issue，最后再用 identifier 做稳定 tie-break。

因此一个 poll tick 实际上已经很接近一个小型 scheduler：

```text
Tracker
  ↓
Candidates
  ↓
Eligibility Filter
  ↓
Priority Ordering
  ↓
Capacity Check
  ↓
Claim
  ↓
Worker
```

但 claim 发生以后，任务也还没有“完成”。它只是获得了一次执行机会。

接下来真正容易误解的是 worker 与 Codex turn 的关系。

### 3.2 一次成功 Turn 为什么不代表 Issue 已经完成

如果把 Coding Agent 想成普通 job，很容易写出这样的生命周期：

```text
dispatch
   ↓
run Codex
   ↓
success
   ↓
job done
```

Symphony 没有把一次 turn completion 等同于 work completion。

当前规范至少区分四个层次：

```text
Issue
  ↓
Worker Run
  ↓
Codex Thread
  ↓
Turn
```

`Turn` 是 Coding Agent protocol 中一次具体执行；`Thread` 保存同一段连续 Agent 上下文；`Worker Run` 是 Symphony 当前为一个 issue 启动的一次执行实例；而 `Issue` 则位于最外层，可能跨越多个 worker lifetime。

第一次进入 worker 时，Agent 会收到完整的 rendered task prompt：

```text
WORKFLOW.md prompt template
          +
       issue data
          ↓
    first turn
```

这个 turn 完成以后，worker 不会立刻退出。它会重新读取当前 tracker state，判断这个 issue 是否仍然处于 active 且 routable 的状态。

如果答案是 yes，规范建议继续使用同一个 live Codex thread：

```text
Turn 1
  │
  │ completed
  ▼
Refresh Issue
  │
  ├─ no longer active ──→ stop worker
  │
  └─ still active
         │
         ▼
      Turn 2
         │
         ▼
      Turn 3
         │
         ...
```

这种 continuation turn 不需要重新发送原始任务描述，因为完整 prompt 已经存在于 thread history 中。后面的 turn 应该只发送 continuation guidance。

这能避免一种很笨重的循环：

```text
Turn 1:
重新发完整 issue
做工作

Turn 2:
再次重新发完整 issue
再次解释任务

Turn 3:
再次重新发完整 issue
...
```

在同一个 live thread 中延续，可以保留前面已经建立的上下文。

当然，worker 也不能无限循环。

当前默认：

```text
agent.max_turns = 20
```

表示一个 worker lifetime 内最多启动 20 个 Coding Agent turn。

因此：

```text
max_turns reached
```

只能说明：

```text
当前 worker 应该结束
```

不能直接推出：

```text
issue 已经完成
```

这两个状态的区别在 Symphony 中非常重要。

例如一个 Agent 完成 20 个 turn 后仍然把 Linear issue 留在：

```text
In Progress
```

那么 Orchestrator 必须认为：

```text
work may still remain
```

而不是因为子进程正常退出，就擅自把 issue 当作 finished。

这也是为什么当前规范在 worker **正常退出**以后，仍然安排了一次短 continuation retry。

默认语义大约是：

```text
worker exits normally
        ↓
remove running entry
        ↓
schedule retry
        ↓
delay ≈ 1000 ms
        ↓
refresh issue
        ↓
still active?
```

这里的 1 秒不是错误退避。

它更像：

```text
yield
→ 再确认一次 durable work state
```

如果 issue 已经进入：

```text
Human Review
Done
Canceled
```

或者其它不再 active 的状态，就可以释放 claim。

如果仍然 active，并且有可用 slot，Symphony 可以再启动一个新的 worker session，在原有 per-issue workspace 上继续。

因此：

```text
Turn success
≠
Worker success
≠
Issue completed
```

甚至：

```text
Worker exited normally
```

也不能推出：

```text
Task is done forever
```

真正具有决定权的仍然是 workflow 所定义的 task state，而不是某个 Agent process 的 exit code。

这套设计还有一个现实上的好处：Agent 不需要准确预测“我是不是已经永远做完这件事”。

Agent 只需要在当前 turn 中推进任务，并通过工具更新代码、PR、CI 或 tracker。外层 Orchestrator 再根据 durable state 判断：

```text
还需不需要有人继续？
```

这比要求模型在自然语言结尾里输出：

```text
TASK_COMPLETE=true
```

更容易和团队真实工程流程对齐。

正常退出走短 continuation retry，真正的错误则走另一条路径。

### 3.3 Retry Queue：失败以后不是立即无限重跑

Agent 的一次执行可能因为很多原因失败：

```text
Codex process startup failed
turn failed
turn cancelled
timeout
stall
workspace hook failed
tracker request failed
```

如果所有失败都立即重启，就很容易形成：

```text
failure
  ↓
restart
  ↓
same failure
  ↓
restart
  ↓
same failure
  ↓
...
```

这不仅浪费 token，也可能持续冲击 tracker、GitHub、CI 或其它外部服务。

所以 Symphony 给失败路径设置了显式 retry queue。

当前规范使用指数退避：

$$
delay
=
\min
\left(
10000\times 2^{attempt-1},
\text{agent.max\_retry\_backoff\_ms}
\right)
$$

默认：

```text
agent.max_retry_backoff_ms = 300000
```

也就是 5 分钟。

按照这个默认值：

| Retry Attempt | Delay |
| ------------: | ----: |
|             1 |  10 s |
|             2 |  20 s |
|             3 |  40 s |
|             4 |  80 s |
|             5 | 160 s |
|             6 | 300 s |
|             7 | 300 s |
|             8 | 300 s |

从第六次开始达到 5 分钟上限，后续不再继续翻倍。

这里需要和上一节的正常 continuation 分开：

```text
Clean worker exit
→ fixed short delay ≈ 1 s

Failure
→ exponential backoff
```

两者都放进 retry machinery，并不意味着它们语义相同。

前者表达：

```text
这次 worker 正常结束了，
但 durable issue 可能仍然 active，
很快再确认一次。
```

后者表达：

```text
这次执行出现异常，
不要立即重复制造同样的失败。
```

一个 retry entry 至少要记住：

```text
issue_id
identifier
attempt
due_at_ms
timer_handle
error
```

此时任务通常处于：

```text
Claimed
+
RetryQueued
```

也就是说，它虽然没有 running worker，但仍然没有被释放给普通 candidate dispatch。

等 timer 到期以后，Symphony 也不是直接：

```text
launch Codex again
```

而是先重新读取这一个 issue。

流程更接近：

```text
Retry Timer Fired
        │
        ▼
fetch_issues_by_ids(issue_id)
        │
        ├─ not found
        │      ↓
        │   release claim
        │
        ├─ terminal
        │      ↓
        │   cleanup workspace
        │   release claim
        │
        ├─ active + routable
        │      │
        │      ├─ slot available
        │      │      ↓
        │      │   dispatch
        │      │
        │      └─ no slot
        │             ↓
        │          requeue
        │
        └─ inactive / unroutable
               ↓
          release claim
```

这一步重新读取 tracker 很重要。

假设 Agent 在 12:00:00 失败：

```text
issue = In Progress
```

系统安排：

```text
retry at 12:00:40
```

但工程师在 12:00:15 已经手动把它改成：

```text
Canceled
```

那么 12:00:40 到来时，正确行为显然不是：

```text
无视 tracker
按照 40 秒前的 snapshot
重新启动 Agent
```

而应该重新确认当前事实。

所以 retry queue 保存的是：

```text
什么时候重新考虑这个 issue
```

而不是：

```text
什么时候无条件重新执行上一次动作
```

这个 distinction 也是 Symphony 为什么依赖 durable work state 的另一个例子。

不过 retry timer 只解决“未来某个时刻再检查”。还有一种变化发生在 Agent **当前正在运行的时候**，不能等它自己退出以后再发现。

这就是 reconciliation。

### 3.4 Reconciliation：当外部世界已经变了，正在运行的 Agent 怎么办

Coding Agent 工作期间，Symphony 不是唯一可以修改世界的参与者。

同时还可能有：

```text
Engineer
Reviewer
CI
Issue Tracker Automation
GitHub Bot
Other Agents
```

所以一个 worker 启动时看到的：

```text
Issue Snapshot
```

很快就可能过期。

例如：

```text
12:00
MT-649 = In Progress
Agent starts

12:04
工程师发现需求重复
把 MT-649 改成 Canceled

12:05
Agent 仍然在修改代码
```

如果 Orchestrator 从不重新读取 tracker，Agent 就可能继续为一个已经取消的任务消耗 token 和修改 workspace。

因此每次 poll tick 的第一步是 active-run reconciliation。

当前规范把它拆成两类检查。

第一类是 stall detection。

对于每个 running issue，Orchestrator 观察最近一次 Codex event 的时间。如果还没有收到 event，就从 worker `started_at` 开始计算。

可以简化成：

$$
elapsed
=
now
-
\begin{cases}
last\_codex\_timestamp,& \text{if event exists}\\
started\_at,& \text{otherwise}
\end{cases}
$$

当前默认：

```text
codex.stall_timeout_ms = 300000
```

也就是 5 分钟。

如果：

```text
elapsed_ms > stall_timeout_ms
```

Orchestrator 会终止 worker，并把它转入 retry path。

这里检测的不是：

```text
这个任务总共已经跑了多久
```

而是：

```text
多久没有看到 Agent activity
```

这两个 timeout 不能混为一谈。

例如一次长测试可能持续十分钟，但如果 Codex runtime 在期间持续产生允许重置 inactivity timer 的 protocol output，就不一定属于 stall。

如果：

```text
stall_timeout_ms <= 0
```

则规范允许完全禁用 stall detection。

第二类 reconciliation 来自 tracker state refresh。

Symphony 会批量读取所有 running issue 的最新状态，再逐个比较：

```text
Current Tracker State
        │
        ├─ terminal
        │     ↓
        │  terminate worker
        │  cleanup workspace
        │
        ├─ still active + routable
        │     ↓
        │  keep running
        │  update in-memory snapshot
        │
        ├─ active but unroutable
        │     ↓
        │  terminate worker
        │  keep workspace
        │
        └─ neither active nor terminal
              ↓
           terminate worker
           keep workspace
```

这里几个分支的 workspace 处理并不一样。

如果任务已经进入 terminal state，例如：

```text
Done
Canceled
```

那么 workspace 可以进入 cleanup 流程。

但如果它只是暂时不再 routable，例如某个 required label 被移除，规范不会要求立即删除已经积累的工作目录。

这保持了：

```text
停止当前执行
```

与：

```text
销毁任务工作状态
```

之间的区别。

Reconciliation 还有一个比较保守的失败策略。

如果 tracker refresh 本身失败：

```text
Linear unavailable
network timeout
provider 5xx
```

Symphony 不会因为“暂时无法证明任务仍然 active”就立即杀掉所有 Agent。

当前行为是：

```text
log error
keep workers running
retry refresh on next tick
```

这相当于在两种风险之间选择：

```text
A:
tracker 暂时不可用
→ 杀掉所有正在工作的 Agent

B:
tracker 暂时不可用
→ 暂时维持当前运行状态
→ 下一轮再确认
```

规范选择后者。

它并不保证任何时候都掌握绝对最新的 tracker state，而是在外部控制面暂时不可读取时，避免一次基础设施故障扩大成所有 worker 同时被终止。

整个运行时循环因此可以画成：

```text
                  ┌───────────────────────┐
                  │       Poll Tick       │
                  └──────────┬────────────┘
                             │
                             ▼
                       Reconciliation
                      /              \
                     /                \
               stall check       tracker refresh
                     \                /
                      \              /
                             │
                             ▼
                       Validate Config
                             │
                             ▼
                     Fetch Candidates
                             │
                             ▼
                     Eligibility Filter
                             │
                             ▼
                    Capacity + Claim
                             │
                             ▼
                        Worker Run
                             │
                  ┌──────────┴──────────┐
                  │                     │
              Turn Success          Run Failure
                  │                     │
                  ▼                     ▼
           refresh issue          Retry Queue
                  │                     │
           still active?          exponential
             /        \              backoff
           yes        no                │
            │          │                │
            ▼          ▼                │
       next turn      stop              │
            │                           │
       max_turns?                       │
            │                           │
            ▼                           │
       worker exits                     │
            │                           │
            ▼                           │
      ~1s continuation                  │
            retry                       │
            └──────────────┬────────────┘
                           │
                           ▼
                      refresh issue
                           │
                           ▼
                    dispatch / release
```

到这里，Symphony 已经不再像“每 30 秒跑一次 Codex”的 cron job。

它实际维护的是一组持续收敛的关系：

```text
Tracker says what work currently exists.

Orchestrator says who currently owns execution.

Workspace preserves what execution has already changed.

Codex advances the work.

Reconciliation keeps these views from drifting indefinitely.
```

这个模型同时解释了前面几个看似零散的设计：为什么 claim 需要独立于 Linear state，为什么 workspace 不能跟着一次 process exit 消失，为什么正常退出以后还有 1 秒 continuation retry，以及为什么失败重试前必须重新读取 issue。

下一节再往 Agent 执行边界内部走一步：Symphony 如何准备 workspace、`WORKFLOW.md` 怎样同时承载 runtime configuration 与 prompt policy，以及 Orchestrator 为什么通过 Codex app-server 启动 Agent，而不是自己重新实现一套模型—工具循环。

## 4. Workspace、WORKFLOW.md 与 Agent Runner 怎样拼起来？

到目前为止，Symphony 已经能够从 tracker 找到 eligible issue，把它 claim 下来，并在失败后重新调度。但真正启动 Coding Agent 之前还有一层接口需要明确：Agent 到底在哪个目录执行、团队怎样告诉 Symphony 这类任务应该遵守什么规则，以及 Symphony 如何把一次 worker run 交给 Codex。

当前语言无关 [`SPEC.md`](https://github.com/openai/symphony/blob/main/SPEC.md) 把这几件事拆成了三个对象：

```text id="n8torz"
Workspace Manager
      │
      ├─ execution directory
      │
      ▼
WORKFLOW.md
      │
      ├─ runtime config
      └─ prompt policy
      │
      ▼
Agent Runner
      │
      ▼
Codex app-server
```

这个分层看起来比直接写：

```text id="h2mc2r"
cd repo
codex "fix issue"
```

复杂不少，但它分别解决了执行状态、团队 policy 和 Coding Agent protocol 三个不同的问题。

### 4.1 Workspace Isolation 不是 Git Branch 的同义词

前面已经提到，每个 issue 都会映射到一个独立 workspace。这里还需要进一步限定这个词，因为看到：

```text id="cibsmx"
one issue
→
one workspace
```

很容易自然联想到：

```text id="tofi6n"
one issue
→
one git worktree
```

但 Symphony 的规范并没有规定这一层。

它要求的是一个 filesystem execution boundary：

```text id="wkpgtk"
workspace.root
      │
      ├─ MT-649/
      ├─ MT-650/
      ├─ MT-651/
      └─ ...
```

Agent 处理 `MT-649` 时，运行目录应该是：

```text id="tm956j"
<workspace.root>/MT-649
```

而不是：

```text id="pwck6l"
repository root

其它 issue 的 workspace

任意用户目录
```

当前规范把两个安全不变量写得很明确：

```text id="hdf0sa"
cwd == workspace_path
```

以及：

```text id="hd293z"
workspace_path
必须位于
workspace.root
内部
```

也就是说，Orchestrator 在启动 Coding Agent 前，至少要确认它确实把这个 Agent 放进了属于当前 issue 的目录。

但这依然不能推出：

```text id="05ea4u"
Workspace Isolation
=
完整 Sandbox
```

一个独立目录只能确定 Agent 从哪里开始工作，以及 Symphony 怎样区分不同 issue 的文件状态。Agent 能不能访问：

```text id="2dxke9"
../
~/
network
credentials
other processes
```

取决于 Codex sandbox policy、宿主操作系统以及实际部署环境。

Symphony 当前规范也没有要求所有实现统一采用一种强 sandbox。approval、sandbox 和 operator confirmation 的具体 posture 都属于 implementation-defined，并要求实现者明确记录自己的选择。

所以这里最好把三个层次分开：

```text id="t56jbk"
Workspace Isolation
=
不同 work item 的执行目录隔离

Codex Sandbox
=
Agent 在一次执行中
能访问哪些 filesystem / network resource

Host Isolation
=
进程、容器、VM、OS account 等
更外层运行边界
```

Symphony Core 强制的是第一层，并把第二层交给 Coding Agent runtime 的配置。

同样，它也没有规定 workspace 里的 repository 必须怎样准备。

第一次看到新 issue 时，Workspace Manager 只需要确保：

```text id="10b98j"
workspace directory exists
```

至于代码如何进入这个目录，可以由实现选择：

```text id="oc3ct1"
git clone

git worktree

git checkout + copy

内部 repository bootstrap tool

预先挂载好的 filesystem
```

当前 `SPEC.md` 把这一部分称为：

```text id="96voav"
workspace population
```

并明确留作 implementation-defined。

Symphony 提供的一个通用连接方式是 lifecycle hooks。

当前规范定义四类 hook：

| Hook            | 什么时候运行               | 失败后的处理            |
| --------------- | -------------------- | ----------------- |
| `after_create`  | workspace 第一次创建后     | 当前 workspace 创建失败 |
| `before_run`    | 每次 Agent attempt 开始前 | 当前 attempt 失败     |
| `after_run`     | 每次 attempt 结束后       | 记录错误，但不改变已有结果     |
| `before_remove` | workspace 删除前        | 记录错误，仍继续 cleanup  |

默认 hook timeout 是：

```text id="1figyz"
hooks.timeout_ms = 60000
```

即 60 秒。

例如一个团队完全可以把 repository bootstrap 放到：

```yaml id="smf4f8"
hooks:
  after_create: |
    git clone "$REPOSITORY_URL" .
    npm ci

  before_run: |
    git fetch origin
```

这只是一个可能的 workflow，不是 Symphony 的内建 Git 语义。

这种设计还有一个直接后果：`after_create` 和 `before_run` 不能混用。

假设：

```text id="zkbvq4"
after_create
→ npm ci
```

那么它只会在 workspace 第一次出现时执行一次。

而：

```text id="rm88jm"
before_run
→ git fetch origin
```

则会在：

```text id="l1oc34"
Run 1
Run 2
Run 3
```

每次 Agent attempt 前重新执行。

这正好对应前面已经建立的生命周期关系：

```text id="v0n86u"
Workspace
   │
   ├─ created once
   │
   ├─ Run 1
   │
   ├─ Run 2
   │
   └─ Run 3
```

因此 workspace 既保存长期文件状态，又允许每次 run 开始前做短期环境准备。

到这里还缺一个问题：这些 hook、并发限制、tracker state 和 Agent prompt 应该写在哪里？

如果全部硬编码进 Orchestrator，那么每个团队改一次工作流程都要修改 Symphony 源码。

`WORKFLOW.md` 就是为这个边界准备的。

### 4.2 `WORKFLOW.md` 怎样把 Policy 留在 Repo 里

Symphony 没有把：

```text id="3pue24"
哪些 state 可以工作
workspace 放在哪里
同时允许多少 Agent
启动 Codex 时用什么参数
Agent 应该遵循什么任务说明
```

全部编译进 service binary。

它使用 repository-owned：

```text id="7cjbcw"
WORKFLOW.md
```

作为运行契约。

文件结构很简单：

```text id="nt7fhg"
WORKFLOW.md
│
├─ YAML Front Matter
│    └─ Runtime Configuration
│
└─ Markdown Body
     └─ Per-Issue Prompt Template
```

例如可以写成：

```yaml id="mx8lka"
---
tracker:
  kind: linear
  active_states:
    - Todo
    - In Progress
  terminal_states:
    - Done
    - Canceled

polling:
  interval_ms: 30000

workspace:
  root: /tmp/symphony_workspaces

agent:
  max_concurrent_agents: 10
  max_turns: 20

codex:
  command: codex app-server
---

You are working on issue {{ issue.identifier }}:

{{ issue.title }}

{{ issue.description }}

Work on the issue in the provided workspace.
Run the relevant validation before handing the task off.
```

上半部分决定 runtime 怎样运行，下半部分决定 Agent 拿到 issue 后看到什么。

当前规范定义的 core top-level config 包括：

```text id="k6aa77"
tracker
polling
workspace
hooks
agent
codex
```

这个列表本身不需要全部背下来，更值得记的是配置被放在了哪个层次。

例如：

```text id="knykiz"
polling.interval_ms
```

属于 Orchestrator cadence；

```text id="3cwxz7"
agent.max_concurrent_agents
```

属于 scheduler capacity；

```text id="7e059v"
hooks.before_run
```

属于 workspace lifecycle；

而：

```text id="bgbjib"
codex.command
```

属于 Coding Agent integration。

它们虽然都存在一个 Markdown 文件里，但控制的是不同 runtime component。

Markdown body 则完全是另一类数据。

Symphony 会把：

```text id="moit1v"
workflow.prompt_template
+
normalized issue
+
attempt
```

送入 template renderer，生成这一次 issue 的 Agent prompt。

例如：

```text id="djbhlz"
Issue
{
  identifier: "MT-649",
  title: "Fix cache invalidation",
  ...
}
```

经过：

```text id="46hwp1"
WORKFLOW.md
```

以后才得到：

```text id="8ajj40"
You are working on MT-649:
Fix cache invalidation
...
```

这就把：

```text id="8re96q"
Task Data
```

和：

```text id="hmcrdg"
Task Policy
```

分开了。

Issue tracker 提供：

```text id="zjgt2u"
这一次具体是什么任务？
```

`WORKFLOW.md` 提供：

```text id="8kjenh"
我们团队希望这类任务怎么工作？
```

Orchestrator 再把两者组合成一次 Agent execution。

当前规范对模板错误采取的是严格模式。未知 variable 或 filter 不应该悄悄变成空字符串，而是让这次 prompt rendering 失败。

例如 workflow 写错：

```text id="mnaoi2"
{{ issue.titel }}
```

而实际字段是：

```text id="dpjgzh"
issue.title
```

更安全的结果是：

```text id="f58emv"
template_render_error
```

而不是让 Agent 收到：

```text id="cni21t"
Title:
```

然后在缺少任务信息的情况下继续工作。

这里还有一个对长期运行服务很有用的设计：`WORKFLOW.md` 不只是启动时读一次。

当前 `SPEC.md` 要求：

```text id="o7eb96"
Dynamic reload is REQUIRED
```

也就是说：

```text id="jdgc5g"
edit WORKFLOW.md
       ↓
Symphony detects change
       ↓
reload config + prompt
       ↓
future runtime operations
use new configuration
```

能够动态应用的内容包括未来的：

```text id="9jrwls"
poll cadence
concurrency limits
active / terminal states
workspace settings
hooks
Codex settings
prompt content
```

但这里需要注意：

```text id="cbs1jr"
reload config
≠
强制重启所有 in-flight Agent
```

当前规范明确不要求配置变化后自动 restart 正在运行的 session。新配置主要影响未来 dispatch、retry、hook execution 和 Agent launch。

这可以避免一种非常危险的实现：

```text id="fkjqij"
工程师保存 WORKFLOW.md
        ↓
10 个运行中的 Agent
全部瞬间被 kill
```

规范也规定无效 reload 不应该直接把整个 service 打挂。

如果刚保存的 YAML 写成：

```yaml id="lza2da"
agent:
  max_concurrent_agents: ???
```

合理的行为是：

```text id="5d8kzp"
reload fails
      ↓
emit operator-visible error
      ↓
keep last-known-good configuration
```

而不是：

```text id="z3e4me"
Symphony crashes
```

这让 `WORKFLOW.md` 更接近一种可版本化的 runtime policy，而不是一次性启动参数。

不过这里还需要和另一份文件分清。

Symphony 仓库现在还有：

```text id="y5hdzd"
SPEC.md
```

两者名字都像“规范”，但职责并不一样：

```text id="3rt9tk"
SPEC.md
=
定义一个 Symphony-compatible implementation
应该满足什么行为

WORKFLOW.md
=
定义某个具体 repository / team
希望 Symphony 怎样运行
```

换成前面 `spec.md` 那篇文章使用的语言，可以写成：

```text id="284fwe"
SPEC.md
        │
        │ implementation contract
        ▼
Symphony Service
        │
        │ consumes
        ▼
WORKFLOW.md
        │
        │ runtime policy
        ▼
Issue Execution
```

这也是两篇文章最需要守住的接口。

你的 `spec.md` 讨论的是：

```text id="4d3fbv"
我们怎样把系统应该是什么
写成足够明确的 contract
```

这里的 `symphony.md` 则讨论：

```text id="k1b1d0"
一个已经存在的 orchestration service
怎样消费 runtime policy
并持续推进 work item
```

因此 `WORKFLOW.md` 不是另一份 PRD，也不应该把每个 feature 的全部产品需求重新复制进去。具体任务仍然来自 issue；`WORKFLOW.md` 更适合保存所有 issue 共用的运行规则和 Agent instructions。

现在：

```text id="f70o04"
Issue
+
WORKFLOW.md
+
Workspace
```

都已经准备好了。

剩下的最后一步，是怎样把这三个输入交给真正会写代码的 Codex。

### 4.3 Orchestrator 为什么不重新实现 Codex

如果 Symphony 已经负责：

```text id="fdw8om"
poll
claim
dispatch
retry
workspace
prompt rendering
```

继续往下扩似乎很自然：

```text id="wqgll5"
再自己调用模型 API

再实现 tool calling

再维护 conversation history

再解析 shell command

再处理 edit tool

再实现 compaction
```

这样最后就会得到另一套 Coding Agent。

Symphony 刻意没有走这条路。

当前规范中的 Agent Runner 只承担一层 adapter-like responsibility：

```text id="z0w962"
Issue
  │
  ▼
Create / Reuse Workspace
  │
  ▼
Render Prompt
  │
  ▼
Launch Codex app-server
  │
  ▼
Start Thread / Turn
  │
  ▼
Stream Events
  │
  ▼
Report Outcome to Orchestrator
```

真正的模型—工具循环仍然发生在 Codex runtime 内部。

所以完整层次更接近：

```text id="kk386h"
Issue Tracker
      │
      ▼
Orchestrator
      │
      ▼
Agent Runner
      │
      ▼
Codex app-server
      │
      ▼
Codex Agent Loop
      │
   ┌──┴───────────┐
   ▼              ▼
 Model           Tools
   ▲              │
   └──────────────┘
```

Symphony 到：

```text id="b2m4kl"
Codex app-server
```

这里就停止继续向内抽象。

这和前面 Claude Code Harness 的文章可以直接对应起来。

在 Claude Code 那一层，我关注的是：

```text id="ryndm0"
Model
  ↓
tool_use
  ↓
permission
  ↓
execution
  ↓
tool_result
  ↓
Model
```

这是一个 Coding Agent runtime 怎样把一次任务内部的 reasoning 与真实环境连接起来。

Symphony 位于更外面：

```text id="s0faxd"
Issue
  ↓
Workspace
  ↓
Codex Session
  ↓
Model ↔ Tool Loop
```

它不需要知道 Codex 在一个 turn 内部：

```text id="tpahea"
读了哪些文件
为什么选择 Bash
怎样修改 patch
何时压缩 context
下一次 inference 输入是什么
```

这些都应该由 Codex 自己决定。

当前 Symphony 默认启动：

```text id="r7nk96"
codex app-server
```

并通过 app-server protocol 与 Coding Agent 通信。

规范在这里还特意声明了一层 source-of-truth boundary：

```text id="5orxx5"
Codex app-server protocol
=
Codex documentation / generated schema
是协议真源

Symphony SPEC.md
=
只定义 orchestration integration responsibility
```

也就是说，Symphony 不应该复制一份 Codex protocol schema，然后假定：

```text id="l3ausq"
thread/start 永远长这样
turn/start 永远有哪些字段
SandboxMode 永远只有这些 enum
```

因为 Codex 自己还会演化。

Symphony 应该根据目标 Codex 版本的真实 protocol 来发送请求。

这和 Tool protocol versioning 是同一个工程问题：如果上层系统偷偷复制了下层 API 的内部结构，就会形成两份需要同步维护的事实来源。

Symphony 只保留自己必须约束的部分，例如：

```text id="rdylgi"
Agent process
必须在当前 issue workspace 中启动

first turn
使用 rendered issue prompt

continuation turn
继续使用同一个 live thread

runtime events
需要回传 Orchestrator
```

第一次 turn 会带完整 prompt：

```text id="nsczlo"
Thread
  │
  ▼
Turn 1
  │
  └─ Full rendered issue prompt
```

如果上一节所说的 worker continuation 发生，则：

```text id="nfdcw7"
same Thread
  │
  ├─ Turn 1
  │    full prompt
  │
  ├─ Turn 2
  │    continuation guidance
  │
  └─ Turn 3
       continuation guidance
```

不会重新创建一个没有历史的新 Agent，再把完整 issue 从头解释一次。

Agent Runner 同时负责把 Codex 的运行事件翻回 Symphony 能观察的 session metadata，例如：

```text id="o24gjs"
thread_id
turn_id
last event
last event timestamp
token usage
process id
```

Orchestrator 不需要理解每一段模型 reasoning，只需要知道：

```text id="jrmfpi"
session started?
still active?
turn completed?
turn failed?
多久没有 event?
token usage 到多少?
```

这些数据已经足够支撑前一节的：

```text id="jpx0bb"
stall detection
runtime status
retry decision
reconciliation
```

这里还存在一个安全相关的接口边界。

Symphony 自己可能持有 tracker credential，用于：

```text id="9lefh2"
poll issues
refresh issue state
execute provider-native agent tools
```

但这不代表：

```text id="wxt02w"
Codex child process
必须拿到 raw tracker token
```

当前规范反而建议 host-side tracker secret 不要被 Coding Agent child process 继承。需要修改 tracker 时，可以由 Symphony host-side tool implementation 使用 credential 执行，再把结构化结果返回给 Agent。

于是：

```text id="w6j8et"
Agent has capability
to request tracker action
```

和：

```text id="w7pcsw"
Agent owns tracker credential
```

也可以继续分开。

这个问题会在下一节讨论 tracker write 时展开。

现在整条执行链已经可以拼完整：

```text id="koeagt"
                    SPEC.md
                       │
             implementation contract
                       │
                       ▼
              Symphony Service
                       │
      ┌────────────────┼────────────────┐
      │                │                │
      ▼                ▼                ▼
Issue Tracker     WORKFLOW.md      Workspace Root
      │                │                │
      │ work data      │ policy         │ execution state
      └──────────┬─────┴───────────────┘
                 │
                 ▼
             Orchestrator
                 │
           claim / dispatch
                 │
                 ▼
              Worker
                 │
                 ▼
            Agent Runner
                 │
                 ▼
          Codex app-server
                 │
                 ▼
       Model ↔ Tool Runtime Loop
```

这个结构也解释了为什么 Symphony 可以保持相对薄。

它没有试图拥有完整的软件开发过程，而是在几个已经存在的系统之间建立稳定关系：

```text id="rdbozz"
Issue Tracker
保存 durable work state

WORKFLOW.md
保存 repository-owned runtime policy

Workspace
保存 per-issue execution state

Codex
负责实际完成任务

Symphony
负责让这些对象在时间上持续对应
```

下一节要处理的是这个边界里最容易重新膨胀的一部分：如果 Agent 已经能够自己创建 PR、读 CI、回复 review、修改 tracker，哪些行为还应该硬编码在 Orchestrator state machine 中，哪些应该退回给 Agent 根据 objective 和 tools 自己完成。OpenAI 在 Symphony 的演进过程中，恰好对这条边界做过一次明显调整。

## 5. 为什么 OpenAI 后来又从 State Machine 转向 Objective？

到这里，Symphony 看起来已经是一套很标准的状态驱动系统：issue tracker 提供 `Todo`、`In Progress`、`Human Review` 等工作状态，Orchestrator 自己又维护 `Claimed`、`Running`、`RetryQueued` 等执行状态。

顺着这个方向继续设计，很容易把整个开发过程都塞进状态机：

```text id="k0m5hj"
Todo
  ↓
Agent Implements
  ↓
Create PR
  ↓
Wait CI
  ↓
Fix CI
  ↓
Wait Review
  ↓
Fix Review
  ↓
Merge
  ↓
Done
```

每一步都由外层 Harness 判断当前状态，再决定下一步允许 Agent 做什么。这种设计的优点是容易观察和控制，但 OpenAI 在实际使用中发现，它也会逐渐形成另一种限制：模型能力已经能够覆盖更大的工作范围，外层系统却还在按照早期模型能力，把它限制成一个只负责完成单步动作的执行节点。

Symphony 后来的变化不是删除状态，而是重新划分 **哪些状态应该属于 Orchestrator，哪些决策应该交还给 Agent**。

### 5.1 早期 Harness 写死了哪些事情

OpenAI 在 Symphony 文章里回顾，早期的 Agent workflow 给 Codex 的任务范围相当窄：

```text id="ck171i"
Implement the task.
```

也就是把 Codex 放在整个工程流程中的一个固定位置：

```text id="e9tgha"
Task
  ↓
Codex implements
  ↓
Harness takes over again
```

PR 怎样创建、CI 怎样读取、review feedback 怎样处理、任务什么时候转换状态，这些事情很容易继续由外围 automation 实现。

这种设计在 Agent 能力不足时有实际理由。假设模型只能比较可靠地完成：

```text id="ncvbhh"
read code
edit code
run local test
```

那么把剩下的：

```text id="u76m3x"
create PR
wait CI
read review
update tracker
merge
```

写进传统程序，会比要求模型自己完成整条流程更可控。

于是整个系统可能发展成：

```text id="ohqmt4"
Orchestrator
    │
    ▼
Step 1: Start Agent
    │
    ▼
Step 2: Detect completion
    │
    ▼
Step 3: Create PR
    │
    ▼
Step 4: Poll CI
    │
    ▼
Step 5: Parse failure
    │
    ▼
Step 6: Start Agent again
    │
    ▼
Step 7: Wait review
    │
    ▼
...
```

这时候 Coding Agent 更接近一个：

```text id="y1aimo"
implementation function
```

输入一个 ticket，输出一份代码修改。

但模型能力继续提高以后，这个接口开始显得过窄。

OpenAI 举出的变化包括：Codex 可以自己创建多个 PR，可以读取 review feedback 并修改代码；团队还给它提供了 `gh` CLI，以及读取 CI logs 等能力。进一步以后，Agent 甚至可以承担关闭旧 PR、整理已经完成和放弃工作的报告等任务。

于是一个 issue 的真实执行路径可能变成：

```text id="8rdho5"
Agent
 │
 ├─ inspect repository
 │
 ├─ implement change
 │
 ├─ run tests
 │
 ├─ create PR A
 │
 ├─ discover another repo also needs change
 │
 ├─ create PR B
 │
 ├─ inspect CI
 │
 ├─ fix failure
 │
 ├─ read review feedback
 │
 ├─ update implementation
 │
 └─ prepare handoff
```

如果外层 Harness 仍然只允许：

```text id="5g8u7b"
Agent
=
Step 2: Implement
```

那么很多已经进入模型能力范围的动作仍然要经过一次固定状态转换：

```text id="g55st5"
Agent says done
     ↓
Harness detects result
     ↓
Harness creates PR
     ↓
Harness waits
     ↓
Harness sees feedback
     ↓
Harness starts another Agent
```

这会产生一个很奇怪的局面。

模型已经能够根据当前代码、CI 和 review context 连续推理：

```text id="j1xx7w"
看到测试失败
→ 定位原因
→ 修改
→ 重新运行
```

但 Harness 强行把它拆成：

```text id="qou0wy"
Run 1
→ stop
→ state transition
→ Run 2
→ stop
→ state transition
→ Run 3
```

外层控制逻辑开始承担大量：

```text id="cb7cl0"
模型本来能够自己判断的局部执行决策
```

而每多写一条这种规则，Harness 就多拥有一份关于“软件开发应该怎样进行”的假设。

例如：

```text id="0yb6oq"
一个 issue 只能有一个 PR
```

可能在某类任务成立，但基础设施 migration 完全可能需要多个 repository。

又比如：

```text id="jhc4c0"
CI failed
→ 一定重新启动新的 Agent session
```

如果当前 live thread 本来就拥有足够上下文，这也未必是最佳选择。

因此 OpenAI 后来发现，问题不只是：

```text id="4u0xs0"
Agent 是否足够强？
```

还包括：

```text id="wm5qo3"
Harness 有没有把一个更强的 Agent
限制在旧模型时代设计出来的接口里？
```

这和前面 Claude Code Harness 文章里的 model-relative scaffolding 是同一个方向的问题。Harness component 并不是加得越多越可靠；模型能力变化以后，一些原本用于补能力缺口的外部流程可能应该被重新评估。

OpenAI 在 Symphony 中采取的调整，是逐渐扩大 Agent 接收到的任务范围。

原来更接近：

```text id="yl97w9"
Objective:
implement this change
```

后来可以变成：

```text id="03rc3j"
Objective:
take this issue to a reviewable handoff state
```

这两句话看起来只差一点，但后者允许 Agent 自己决定：

```text id="rqp88f"
需要几个 PR？
什么时候看 CI？
review feedback 怎么处理？
是否需要继续修改？
应该调用什么已有工具？
```

这里才是“从 strict transitions 转向 objectives”的实际含义。

### 5.2 State Machine 管生命周期，Objective 管执行

如果只读 OpenAI 那句：

> moved toward giving agents objectives instead of strict transitions

很容易把 Symphony 理解成后来放弃了 state machine。

但当前 `SPEC.md` 正好说明情况并不是这样。

Orchestrator 仍然明确维护：

```text id="asaj7w"
Unclaimed
Claimed
Running
RetryQueued
Released
```

tracker 仍然有：

```text id="h4v7rx"
active_states
terminal_states
```

worker 仍然需要经过：

```text id="tub5rc"
claim
dispatch
retry
reconcile
release
```

这些状态没有因为 Agent 更聪明而消失。

真正减少的是另一类状态：

```text id="remyd7"
Implementing
CreatingPR
ReadingCI
FixingCI
WaitingReview
RespondingToReview
UpdatingPR
...
```

如果这些步骤都被写成 Orchestrator 的强制 transition，就相当于外层系统规定：

```text id="c95rti"
Agent 下一步必须干什么
```

而 Symphony 真正需要规定的通常只是：

```text id="lh9srb"
这个 Agent
现在还应该不应该继续工作
```

两者的粒度完全不同。

可以把边界画成：

```text id="ltp6h4"
        Orchestration State Machine

Todo / Active
      │
      ▼
    Claim
      │
      ▼
   Running
      │
      │
      │        Agent Objective
      │     ┌────────────────────┐
      │     │ inspect            │
      │     │ implement          │
      │     │ test               │
      │     │ create PR          │
      │     │ inspect CI         │
      │     │ fix feedback       │
      │     │ validate           │
      │     └────────────────────┘
      │
      ▼
Handoff / Release
```

外层状态机决定生命周期：

```text id="5msp55"
何时可以启动？

是否已经被 claim？

失败后是否应该 retry？

tracker 已经 terminal 时要不要停止？

什么时候释放 runtime ownership？
```

Agent objective 决定执行路径：

```text id="kk6lqd"
为了完成当前任务，
我接下来应该观察什么？

调用什么工具？

修改什么？

怎样验证？

发现新的反馈以后怎样继续？
```

我更愿意把这条边界记成：

```text id="d24ewm"
Orchestrator controls eligibility and lifetime.

Agent controls the path toward the objective.
```

这不是为了减少代码量，而是因为两类决策需要的信息不同。

Orchestrator 擅长处理结构化事实：

```text id="ouybof"
issue state == In Progress
claimed == false
running_count == 7
max_concurrent_agents == 10
retry_due_at <= now
```

这些规则适合普通程序：

```text id="vcxub6"
deterministic
observable
testable
```

但“现在应该先修 CI 还是先处理 reviewer comment”通常要结合：

```text id="m0ntgo"
代码内容
错误日志
任务目标
review context
前面已经尝试过什么
```

这正是 Agent reasoning 的工作区间。

如果把后者也强制写成：

```text id="ql7odf"
if ci_failed:
    transition(FIX_CI)
elif review_comments:
    transition(FIX_REVIEW)
```

就会遇到大量现实中的组合情况。

例如：

```text id="784so5"
CI failure
实际上就是 reviewer 指出的同一个问题
```

或者：

```text id="btfxxr"
reviewer 建议修改接口
但另一个 repository 的 PR
必须先同步更新
```

此时固定状态机需要不断添加：

```text id="rm5yel"
special case
```

Agent 则可以直接根据 objective 和当前 evidence 做下一步判断。

所以 Symphony 后来的设计并不是：

```text id="u7eqo9"
State Machine → Agent
```

而更接近：

```text id="el40n1"
       hard lifecycle invariants
              │
              ▼
         State Machine

              +

       flexible execution path
              │
              ▼
          Objective
```

这条边界也解释了为什么：

```text id="12d6qc"
retry
claim
workspace safety
```

仍然应该放在 deterministic Orchestrator 中。

不能因为 Agent 会 reasoning，就让它自己决定：

```text id="dg9m13"
“我是不是已经被另一个 worker claim？”

“我的 workspace path 是否逃出了 root？”

“这次 failure 应该等待多少秒才重新 dispatch？”
```

这些都是 Runtime invariants，不需要模型参与。

反过来，如果 Agent 已经能够调用 GitHub 工具，那么：

```text id="ubx1vj"
“这个任务是否需要第二个 PR？”
```

就没有必要由 Orchestrator 写死。

这里可以和 Claude Code 的 Tool 层再做一次对应。

在单 Agent runtime 中：

```text id="b8uw8f"
Harness
定义：
哪些 Tool 存在
怎样授权
怎样执行

Model
决定：
为了当前 objective
什么时候调用哪个 Tool
```

Symphony 只是把同样的原则扩到更外层：

```text id="g9xph5"
Symphony
定义：
这个 work item
什么时候拥有 Agent

Agent
决定：
在拥有这段执行时间以后
怎样推进 work
```

于是 deterministic control 和 model reasoning 各自留在更适合的位置。

### 5.3 Tracker Write 为什么没有继续塞进 Orchestrator Core

这条边界在 issue tracker integration 上表现得很具体。

既然 Symphony 已经需要读取 tracker，自然可以继续给 Orchestrator 添加：

```text id="yxax5f"
transition_issue_state()

create_comment()

attach_pr()

upload_attachment()

close_issue()
```

然后写成：

```text id="6suqav"
worker succeeded
      ↓
orchestrator.update_issue(
    state="Human Review"
)
```

这种设计并非做不到。

但当前语言无关 `SPEC.md` 明确选择了另一条边界：

```text id="44z51q"
Symphony Core
=
scheduler / runner
+
tracker reader
```

Ticket mutation 通常由 Coding Agent 通过 selected adapter 提供的 provider-native tools 完成，而不是要求 Orchestrator Core 拥有一套通用 tracker write API。

因此数据流更接近：

```text id="vv4ru2"
              Tracker
             ▲       │
             │       │ reads
       tool mutation │
             │       ▼
           Agent   Symphony
             ▲       │
             │       │ dispatch
             └───────┘
```

例如 `WORKFLOW.md` 可以告诉 Agent：

```text id="p6dc8f"
完成实现和验证后，
把 issue 推进到 Human Review，
并附上 PR 与验证结果。
```

Agent 根据当前任务执行：

```text id="9lj6zd"
inspect
  ↓
implement
  ↓
test
  ↓
create PR
  ↓
update tracker
  ↓
Human Review
```

而不是：

```text id="gpd5ao"
Agent exits
  ↓
Orchestrator guesses
  ↓
create PR?
  ↓
attach PR?
  ↓
transition issue?
```

这个设计至少有两个明显好处。

第一个是 Orchestrator 不需要理解 workflow-specific success。

对于项目 A：

```text id="x5kb54"
success
=
进入 Human Review
```

项目 B 可能是：

```text id="fwle8d"
success
=
提交 investigation report
```

项目 C 又可能要求：

```text id="nu6opo"
success
=
创建多个 PR
并留下 rollout plan
```

如果 Core 自己负责所有 write，它就需要逐渐知道：

```text id="a69569"
这个项目有哪些 column
哪个状态算 review
PR 应该怎样挂载
什么 comment 格式算完成
```

`WORKFLOW.md + Agent Tools` 则可以把这些差异保留在 repository policy 层。

第二个是避免为了统一 provider 而制造一个越来越大的最低公分母接口。

假设 Orchestrator 定义：

```text id="3qq3gb"
Tracker.update_state()
Tracker.comment()
Tracker.attach_pr()
```

Linear、GitHub Issues、Jira 看起来就都能接进来。

但 provider 实际能力通常不止这些：

```text id="d1r2qe"
project item metadata
custom fields
relationships
attachments
subtasks
labels
review-specific objects
provider-specific state semantics
```

为了让所有 tracker 看起来一样，很容易丢掉这些差异。

Symphony 当前的选择是让 Core Scheduler 只依赖比较小的 normalized read contract：

```text id="o1cy3o"
id
identifier
state
labels
dispatchable
...
```

真正需要修改 provider 时，则允许 adapter 暴露：

```text id="3n9t41"
provider-native agent tools
```

Agent 可以看到工具 schema，再结合当前 objective 决定是否调用。

还有一个安全细节也值得保留。

即使 Agent 可以执行：

```text id="70c30t"
update issue
create comment
```

也不代表 Codex child process 必须直接拥有 tracker credential。

当前规范建议：

```text id="3rzyce"
Codex
   │
   │ tool request
   ▼
Symphony Host
   │
   │ uses configured credential
   ▼
Tracker
```

结果再返回给：

```text id="19pwkl"
Codex
```

也就是说：

```text id="oz6jke"
Agent 能调用 tracker action
```

和：

```text id="5ezmxk"
Agent 能读取 raw tracker token
```

仍然是两件不同的事情。

这样一来，Symphony 的职责边界已经比较清楚：

```text id="38i2wj"
Orchestrator Core

负责：
poll
eligibility
claim
concurrency
retry
reconciliation
workspace lifecycle
agent lifecycle
observability
```

Agent 与 Tool Layer 则负责：

```text id="05brk8"
理解 issue objective
修改代码
运行验证
操作 GitHub
读取 CI
处理 review
更新 tracker
形成 handoff artifact
```

这里不是简单地追求：

```text id="dc986w"
“让 Agent 做更多事情”
```

更准确的是，只有那些需要根据任务语义和当前 evidence 做判断的动作，才适合逐渐退回给 Agent；调度正确性、安全不变量和资源控制仍然留在 deterministic runtime。

OpenAI 在文章里把这一变化概括为“不把 Agent 当成 rigid nodes in a state machine”，后来更倾向于给 Agent objective、tools 和 context，让模型自己决定到达目标的路径。

把它放回整篇文章，可以得到现在这套边界：

```text id="d042ny"
Issue Tracker
定义：
work 当前处于什么阶段

        ↓

Symphony State Machine
定义：
work 现在是否拥有 execution

        ↓

Agent Objective
定义：
这段 execution 要达到什么目标

        ↓

Tools + Context
允许：
Agent 自己寻找执行路径

        ↓

Tracker Handoff
重新改变 durable work state
```

这条链的最后一个状态通常也不是：

```text id="9rtvgl"
Done
```

OpenAI 当前规范明确允许一次 successful run 结束在 workflow-defined handoff，例如：

```text id="od1fze"
Human Review
```

也就是说，扩大 Agent 自治范围并没有取消人的工程判断。它只是让 Human 不必再管理：

```text id="rahk6e"
每一步怎么执行
```

而更多关注：

```text id="ru8620"
这个结果是否应该被接受
```

下一节就从这个 handoff 开始，讨论 Symphony 到底把工程师从哪些工作里移了出去、为什么它仍然高度依赖 Harness Engineering，以及哪些高不确定性任务不适合塞进这种持续自动编排模式。

## 6. Symphony 能自动化到哪里？

前面几节一直在扩大 Agent 的自治范围：issue 可以自动 dispatch，失败可以 retry，workspace 可以跨 run 保留，Agent 可以自己读 CI、处理 review、创建 PR，甚至通过 tracker tool 更新任务状态。

但 Symphony 的目标并不是把工程师从软件交付中完全删除。

当前规范甚至没有把：

```text
successful run
```

定义成：

```text
issue == Done
```

一次执行完全可以停在 `Human Review`。这意味着 Symphony 自动化的是从“有人需要不断盯着 Agent 工作”，到“Agent 可以自己把 work 推进到一个可检查的 handoff point”这一段，而不是把所有工程判断都交给模型。

### 6.1 Successful Run 可以结束在 Human Review

如果把 Agent automation 简化成：

```text
Todo
  ↓
Agent
  ↓
Done
```

那么 `Done` 就同时承担了两个不同含义：

```text
Agent 已经完成它能完成的工作

以及

团队已经接受这份工作
```

现实工程流程里，这两件事经常不是同时发生。

假设 issue 是：

```text
Add retry support to payment webhook handler
```

Agent 可以完成：

```text
读取现有实现
修改 retry logic
补测试
运行测试
创建 PR
检查 CI
修复失败
整理验证结果
```

到了这里，它已经没有必要继续占有 Coding Agent execution。

但团队仍然可能需要确认：

```text
retry policy 是否符合业务语义？

是否可能重复扣款？

监控指标是否足够？

失败后的 operational behavior 是否可接受？
```

这些判断没有因为：

```text
tests passed
```

就自动得到答案。

因此更合理的生命周期是：

```text
Todo
  ↓
In Progress
  ↓
Agent works
  ↓
implementation + validation + PR
  ↓
Human Review
  ↓
Engineer evaluates
  ↓
Done
```

在这个模型中：

```text
Human Review
```

不是 Agent “失败了所以叫人来救火”，而是 workflow 明确定义的 handoff boundary。

当前 Symphony `SPEC.md` 也明确保留了这一点：successful run 可以结束在 workflow-defined handoff state，例如 `Human Review`，不要求一定进入 `Done`。

这会进一步改变 success 的定义。

对于普通 batch job：

```text
process exit code = 0
```

可能已经足够。

对于 Symphony：

```text
Agent process exit = 0
```

只表示当前一次 execution 没有因为 runtime error 中断。

真正的 workflow success 更接近：

```text
Issue 已经被推进到
团队定义的下一责任边界
```

例如某个项目的 `WORKFLOW.md` 可以要求：

```text
Before handing off the issue:

- implement the requested change;
- run the relevant tests;
- make sure CI is green;
- create or update the pull request;
- summarize validation and known limitations;
- move the issue to Human Review.
```

Agent 的 objective 就不再是模糊的：

```text
fix this
```

而是一个可观察的 handoff contract。

于是可以区分三种完成：

```text
Turn Completion
=
一次 Codex turn 结束

Run Completion
=
当前 worker lifecycle 结束

Work Handoff
=
任务已经进入 workflow 规定的下一阶段
```

真正值得工程团队关注的是第三种。

这里也能解释 OpenAI 博客里为什么提到 PM 和 designer 可以直接提交 feature request。

他们不需要先学会：

```text
怎样开 Codex session

怎样把 repo 路径告诉 Agent

Agent 卡住以后敲什么命令

什么时候让它继续

怎样从 terminal 找到结果
```

他们仍然使用团队已经熟悉的 work surface：

```text
Issue Tracker
```

例如：

```text
Feature Request
      │
      ▼
    Linear
      │
      ▼
   Symphony
      │
      ▼
     Agent
      │
      ├─ implementation
      ├─ PR
      ├─ tests
      └─ demo / review material
      │
      ▼
 Human Review
```

OpenAI 在原文中提到，PM 和设计师可以从任务系统发起 feature request，最终拿到适合 review 的结果，包括 walkthrough 或 video 等 review packet。

但这并不意味着：

```text
PM wrote ticket
→
production code automatically accepted
```

更准确的是：

```text
提出一个结构足够明确的 work item
→
自动获得一次完整的 implementation attempt
→
把结果送回已有的工程 review surface
```

人的工作从：

```text
supervise execution
```

更多移动到：

```text
evaluate outcome
```

这个差别也是 Symphony 所谓降低 supervision cost 的实际含义。

### 6.2 Symphony 依赖 Harness，而不是替代 Harness

如果只看 orchestration diagram，很容易认为 Symphony 位于最外层，所以它已经把 Coding Agent 的问题全部解决了：

```text
Issue Tracker
      ↓
Symphony
      ↓
Agent
```

但这个图省略了 Agent 内部的大部分工程基础。

真实结构至少是：

```text
Issue Tracker
      │
      ▼
Symphony
      │
      ▼
Per-Issue Workspace
      │
      ▼
Coding Agent Harness
      │
      ├─ context
      ├─ tools
      ├─ permissions
      ├─ sandbox
      ├─ command execution
      ├─ feedback
      └─ verification
      │
      ▼
Model
```

Symphony 管的是外层 work lifecycle。

它并不会因为能重新启动 Agent，就自动解决：

```text
Agent 有没有读到正确文件？

Tool schema 是否足够清楚？

危险命令应该怎样授权？

测试是否真的覆盖需求？

context 被污染以后怎么办？

模型是否能读懂 CI log？

repository 是否给出了可执行的验证入口？
```

这些仍然属于 Harness Engineering。

例如一个 repository 根本没有可靠测试：

```text
Issue
  ↓
Symphony
  ↓
Agent implements
  ↓
"looks good"
```

把 Agent 从一个变成十个并不会产生：

```text
correctness evidence
```

它只会让十份缺乏验证的修改更快进入 review queue。

同样，如果项目构建流程需要工程师口头知道：

```text
先启动内部 VPN

手动复制一个配置

去某个 dashboard 找 token

运行一个没人写进文档的脚本

最后肉眼点页面确认
```

那么 Symphony 很难把这个任务变成稳定的 unattended execution。

这也是 OpenAI 为什么把 Symphony 和前面的 Harness Engineering 联系起来。

一个适合 Agent 长时间工作的 codebase，通常需要把原本存在于工程师脑中的隐式知识外部化为：

```text
tests
docs
skills
tools
scripts
guardrails
repository instructions
machine-readable feedback
```

比如原来的验证过程是：

```text
工程师打开浏览器
→
点五个页面
→
觉得页面没坏
```

Agent 很难稳定复现。

如果把它改造成：

```bash
npm run test:e2e
```

并输出：

```text
3 failed, 126 passed
```

那么结果才能重新进入 Agent loop：

```text
edit
  ↓
test
  ↓
failure evidence
  ↓
edit
```

Symphony 做的是：

```text
让这个 loop
在一个 durable work item 上
持续运行
```

而不是替代 loop 本身。

可以把几层职责压成：

| 层                   | 主要问题                    |
| ------------------- | ----------------------- |
| Spec / Issue        | 要完成什么                   |
| Symphony            | 这份 work 什么时候、在哪里、由谁继续执行 |
| Harness             | Agent 怎样安全地观察、行动和验证     |
| Model               | 根据当前 context 决定下一步      |
| Tests / CI / Review | 结果是否满足工程要求              |

其中任何一层过弱，外层 orchestration 都无法补回来。

例如：

```text
Spec vague
```

会导致 Agent 对 objective 理解不稳定；

```text
Tool weak
```

会导致模型知道该做什么，却无法可靠执行；

```text
Verifier weak
```

会导致 Agent 无法判断当前修改是不是已经满足要求；

```text
Orchestrator weak
```

则表现为任务一失败就丢失，需要人工重新进入 session 恢复。

它们解决的是不同 failure mode。

这也解释了 OpenAI 在 Symphony 使用过程中观察到的一个反馈循环：Agent 失败以后，他们并不只是把这个 instance 手工修好，而是会检查失败暴露了什么系统缺口，再把修复沉淀成：

```text
test
tool
skill
documentation
guardrail
workflow change
```

假设某类 Agent 经常因为不知道如何运行一个内部 integration test 而停下来。

局部修复是：

```text
这次进入 session
告诉它：
"run ./scripts/foo_test.sh"
```

系统修复则是：

```text
把 ./scripts/foo_test.sh
和使用条件
写进 repository instructions / skill / workflow
```

下一次新的 issue 再进入 Symphony 时，就不需要依赖某个人记得补这一句。

因此 Symphony 带来的一个工程压力反而是：

```text
repository 必须能够被机器理解和操作
```

以前只有人在工作时，一个隐藏的操作约定可能多年都不会暴露成明确问题；Agent 开始长期无人值守运行后，这些隐式依赖会变成：

```text
stalls
failed runs
wrong changes
repeated retries
review burden
```

这也是 Harness Engineering 和 orchestration 连在一起的原因。

### 6.3 哪些任务仍然应该由工程师直接处理

Symphony 最适合的并不是“最困难的任务”，而是 **work state 足够明确，并且进展能够被环境反馈验证的任务**。

例如：

```text
升级一个依赖并修复测试

实现已经定义好的 API endpoint

根据明确 design 修改 UI

处理确定范围内的 migration

修复一个有 reproduction 的 bug

根据 review feedback 修改已有 PR
```

这类任务通常具备几个条件：

```text
objective 比较清楚

repository boundary 明确

Agent 能访问需要的工具

validation 可以自动执行

失败后可以安全重试

最终结果存在明确 handoff point
```

任务越接近这种结构，越适合：

```text
Issue
→
Symphony
→
Agent
→
Human Review
```

但另一些工作的问题不在执行，而在“我们到底应该做什么”。

例如：

```text
这套系统未来三年应该采用 event-driven
还是 request-response architecture？

我们是否应该重写这个 service？

这个跨团队 API
到底应该由哪个 domain ownership？

产品应该牺牲一致性换延迟吗？

这个 security tradeoff 是否值得接受？
```

这些任务当然可以让 Coding Agent 搜索代码、整理 evidence、提出方案，但：

```text
objective
```

本身还没有稳定下来。

如果把一个高度模糊的问题直接包装成：

```text
issue = "Improve architecture"
```

然后期待 Symphony 长时间自动推进，Agent 可能确实会持续地产生动作：

```text
读代码
改抽象
新建接口
删除旧实现
创建 PR
```

但动作数量并不能证明：

```text
direction is correct
```

对于这类任务，更适合的模式可能仍然是交互式 Codex session：

```text
Engineer
   ↕
Codex
```

工程师可以持续调整：

```text
scope
assumption
tradeoff
objective
```

直到问题被压缩成可以交给 orchestration 的 work item。

所以这里可以画出一个简单边界：

```text
High uncertainty
High judgment
      │
      ▼
Interactive Agent
Human stays in reasoning loop


Clear objective
Observable execution
Verifiable result
      │
      ▼
Symphony
Human moves to review boundary
```

它们不是两代工具，也不是后者必然替代前者。

同一个 feature 甚至可能先后经历两种模式：

```text
Architecture Exploration
      │
      │ interactive
      ▼
Engineer + Codex
      │
      ▼
Decision / Spec
      │
      ▼
Task Breakdown
      │
      ├─ Issue A
      ├─ Issue B
      ├─ Issue C
      └─ Issue D
           │
           ▼
        Symphony
```

这时候 Symphony 接手的是已经被压缩过的不确定性。

前面的架构讨论解决：

```text
What should we do?
Why?
Under what constraints?
```

后面的 orchestration 解决：

```text
Which work is ready?
Who runs it?
Where?
What happens on failure?
When should execution stop?
```

这个接口也正好连接到上一篇 `spec.md`。

如果 SDD 的目标之一，是把：

```text
模糊意图
```

逐渐压缩成：

```text
可以验证的实现 contract
```

那么 Symphony 可以消费 contract 进一步拆出来的 work item：

```text
Intent
   ↓
Spec
   ↓
Implementation Tasks
   ↓
Issue Tracker
   ↓
Symphony
   ↓
Workspace + Agent
   ↓
PR / Validation
   ↓
Human Review
```

但 Symphony 本身不负责完成最前面的：

```text
Intent → Spec
```

它也不应该假定最后的：

```text
Human Review → Accepted
```

一定可以自动完成。

把整篇文章的边界收回来，可以得到五个不同对象：

```text
Spec
=
什么结果才算正确

Issue
=
现在有哪些具体 work

Symphony
=
这些 work 怎样被持续调度和恢复

Harness
=
一次 Agent execution 怎样观察、行动和验证

Review
=
当前结果是否值得接受
```

OpenAI 在 Symphony 中真正改变的，是这五层中间的一段。

原来的工作方式更接近：

```text
Issue
  ↓
Human opens session
  ↓
Human supervises Agent
  ↓
Human remembers progress
  ↓
Human restarts when needed
  ↓
Human watches CI
  ↓
Human brings result back
```

Symphony 把中间这一段变成：

```text
Issue
  ↓
Orchestrator
  ↓
Persistent Workspace
  ↓
Agent
  ↓
retry / continuation / reconciliation
  ↓
Handoff
```

因此，一个 coding task 即使跨过多次 turn、worker failure 和 CI feedback，也不再必须依赖某个工程师一直记得：

```text
那个 terminal 里的 Agent
现在做到哪里了？
```

但这个系统能够稳定运行的前提仍然没有改变：任务需要有足够清楚的 objective，repository 需要提供 Agent 可操作的工具和验证反馈，而最终需要工程判断的地方仍然应该明确保留 handoff。

这也是我目前给 Symphony 留下的使用边界：**把已经能够被描述、执行和验证的 work 从 session supervision 中移出来；对于尚未形成稳定 objective 的问题，先继续把人留在 reasoning loop 里。**
