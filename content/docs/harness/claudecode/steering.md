---
title: "Claude Code Steering"
draft: true
---

## 1. 为什么一个 `CLAUDE.md` 不够？

### 1.1 所谓 Steering，到底在 Steering 什么？

我第一次认真折腾 Claude Code 的自定义配置时，思路其实很简单：既然 `CLAUDE.md` 会告诉 Claude 这个项目应该怎么做事，那有什么要求就往里面写好了。

比如：

```markdown
# CLAUDE.md

使用 pnpm，不要使用 npm。

项目采用 monorepo，前端在 apps/web，后端在 apps/api。

修改代码后运行 prettier。

提交前运行 pnpm test。

Review 时先检查安全问题，再检查类型错误。

发布前执行：
1. pnpm lint
2. pnpm test
3. pnpm build
4. 检查 CHANGELOG
5. 创建 tag

不要执行 git push --force。

分析大型日志时，不要把全部日志塞回主会话。

所有回答使用中文。
```

单看每一条都没什么问题。

真正的问题是：它们虽然都叫“给 Claude 的指令”，实际上根本不是一类东西。

`pnpm`、目录布局这些内容，是 Claude 几乎每次进入仓库都可能用到的**项目事实**。

```text
使用 pnpm
apps/web 是前端
apps/api 是后端
```

“Review 时先检查什么”已经不太像事实了。它更像一套需要在特定任务中执行的**工作流程**。

```text
开始 Code Review
    ↓
读取 diff
    ↓
检查安全问题
    ↓
检查类型和逻辑问题
    ↓
检查测试覆盖
    ↓
输出 findings
```

“修改后一定运行 prettier”又不一样。我真正想表达的不是：

```text
Claude，请记得有空跑一下 prettier
```

而是：

```text
只要发生 Edit
      ↓
formatter 就应该运行
```

这已经开始接近自动化。

至于：

```text
不要执行 git push --force
```

需求更强。

这里甚至不是希望 Claude“记住我的偏好”，而是希望某个动作无论如何都不要穿过执行边界。

再往下看：

```text
分析大型日志时，不要把全部日志塞回主会话
```

解决的其实是 Context 污染。最合适的办法可能根本不是再教主 Agent 一套“如何节省 Context”的 Prompt，而是把日志分析交给另一个拥有独立 Context 的 Agent，让主会话最后只接收结果。

最后：

```text
所有回答使用中文
```

它改变的又不是项目本身，而是 Claude 在这次运行中的全局行为。

把这些东西全塞进 `CLAUDE.md`，文件当然也能工作。只是随着项目变大，它会逐渐长成一种很奇怪的混合物：

```text
CLAUDE.md
│
├── repo facts
├── coding conventions
├── file-specific constraints
├── deployment procedure
├── review procedure
├── safety rules
├── automation requirements
├── delegation strategy
└── response style
```

这时候问题就不再是“Prompt 写得够不够好”。

我真正需要回答的是：

> **这一条信息，应该在什么时候交给 Claude？应该交给哪个 Agent？是让模型参考，还是让 Harness 直接执行？**

这就是我现在理解的 **Steering**。

Anthropic 在 2026 年 6 月发布的 Claude Code Steering 文章里，把目前这些入口整理成了七类：

```text
CLAUDE.md
Rules
Skills
Subagents
Hooks
Output Styles
Append System Prompt
```

官方没有把它们当成七种同义的配置文件来讲，而是首先问三个问题：

```text
什么时候进入 Context？

长会话发生 Compaction 后，
它还会不会存在？

这条 Steering 到底有多大的控制力？
```

再结合实际使用时很难绕开的 Context cost，我觉得这比单独背每一种配置的语法有用得多。

因为这些机制真正拉开的，是**控制信息的生命周期**。

举个最简单的区别。

如果我把：

```text
这个仓库使用 pnpm
```

写进根目录 `CLAUDE.md`，那它应该从 Session 开始就陪着主 Agent 工作。

但如果我有一份 80 行的发布流程：

```text
检查版本
更新 changelog
构建
测试
生成 artifact
检查 git status
创建 tag
……
```

日常修一个 CSS Bug 时，Claude 完全没有必要先读一遍。

它应该等到我真的执行 release workflow 时再出现。

日志分析又进一步：

```text
Main Context
│
├── 用户需求
├── 当前实现
├── 已修改文件
├── 测试结果
└── 当前推理
```

如果接下来要搜索一个几万行日志，我并不一定希望：

```text
grep 结果
无关日志
第二次搜索
第三次搜索
错误方向
更多 grep 输出
……
```

全部混进这里。

这部分工作可以拥有自己的 Context，最后只返回：

```text
根因
证据位置
建议修改
```

而 formatter 更极端。

如果我的要求是：

```text
每次修改以后都运行 prettier
```

那最稳定的实现甚至不是继续提高 Prompt 的语气：

```text
IMPORTANT:
ALWAYS run prettier.
NEVER forget this.
THIS IS CRITICAL.
```

这种写法看起来越来越严厉，运行机制却没有发生变化。

最终仍然是：

```text
instruction
    ↓
LLM 读取
    ↓
LLM 判断下一步
    ↓
可能执行 formatter
```

如果把它放进 Hook，路径就变成了：

```text
Edit event
    ↓
Hook fires
    ↓
formatter executes
```

前一个方案在改变模型的行为倾向。

后一个方案在改变 Harness 的运行行为。

这两种东西如果都只叫“Prompt”，很多设计上的区别反而被藏掉了。

所以后面再看 `CLAUDE.md`、Skill、Hook 和 Subagent，我不准备把问题问成：

```text
“哪一个功能更强？”
```

我更关心：

```text
这条信息需要常驻吗？

只对某类文件有效吗？

它描述的是知识还是流程？

中间过程需要留在主 Context 吗？

这件事可以交给模型决定吗？

还是说 Harness 必须保证它发生？
```

这些问题回答完，应该使用哪个 Steering 入口，通常已经八九不离十了。

---

### 1.2 Claude Code 提供的与其说是七种 Prompt，不如说是七个 Control Surface

Anthropic 那篇文章开头有一张表。我第一次看时比较关注的是“什么时候用哪个”，后来再回头看，反而觉得前面几列更值得记。

因为它把七种 Steering 机制摆在了同一套坐标里：

| Mechanism                    | 什么时候出现                  | 对 Main Context 的影响 | 更适合放什么                     |
| ---------------------------- | ----------------------- | ------------------ | -------------------------- |
| Root `CLAUDE.md`             | Session 开始              | 一直占用主 Context      | 项目布局、构建命令、团队约定             |
| Nested `CLAUDE.md`           | 访问对应目录时                 | 按需进入               | 某个子目录自己的约定                 |
| Rules                        | Session 开始或匹配路径时        | 取决于是否 path-scoped  | 针对某类代码的约束                  |
| Skills                       | 先暴露名称和描述，调用时再加载正文       | Procedure 按需进入     | Review、Release、Deploy 等工作流 |
| Subagents                    | 被调用时                    | 在独立 Context 中运行    | 搜索、日志分析、依赖审计等 Side Task    |
| Hooks                        | 对应 lifecycle event 发生时  | 配置本身通常不占主 Context  | formatter、拦截命令、通知、自动备份     |
| Output Style / System Prompt | Session 或 invocation 开始 | 直接影响全局行为           | 角色、语言、输出格式等                |

这里先不用急着记每一行的细节，后面几章会分别拆。

先看同一个要求放错位置以后会发生什么。

假设团队规定：

```text
所有 API Handler 都必须先经过 Zod validation。
```

如果写进 root `CLAUDE.md`：

```text
Session start
    ↓
加载 API rule
    ↓
修改 README
    ↓
API rule 仍然在 Context
```

它没有错，只是 docs-only 任务也要为这条 API 规则付 Context 成本。

如果这个约束只在：

```text
src/api/**
**/*.handler.ts
```

出现时才加载，那么它和实际工作范围就对上了。

再看 Release：

```text
Release checklist = 80 lines
```

放 `CLAUDE.md`：

```text
修 README
→ 带着 80 行 release procedure

修 CSS
→ 带着 80 行 release procedure

查一个类型错误
→ 还是带着 80 行 release procedure
```

做成 Skill：

```text
普通任务
→ 只知道存在 release skill

真正 release
→ 加载完整 procedure
```

再看日志分析：

```text
10 万行 production.log
```

做 Skill，执行过程依然发生在 Main Agent：

```text
Main Agent
    ↓
加载 log-analysis procedure
    ↓
grep
    ↓
Read
    ↓
grep
    ↓
更多中间结果
```

改成 Subagent：

```text
Main Agent
    │
    └── “调查 production.log 中的 500 错误”
             ↓
        Subagent Context
             ↓
           grep
           Read
           grep
           分析
             ↓
        final summary
             ↓
Main Agent
```

Procedure 可能差不多，Context 拓扑却完全变了。

这也是我觉得把它们全叫“Claude Code 配置方式”不太够的原因。

我更愿意借一个系统设计里的词，把这些东西看成不同的 **Control Surface**。

这里的 Control Surface 不是 Anthropic 给出的正式术语，只是我自己为了记忆做的一层抽象。它强调的是：我都可以通过这些入口改变 Claude Code 的行为，但改变发生的位置不同。

大致可以先画成这样：

```text
                     Claude Code Steering
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                      │
   Context Steering      Execution Steering    Runtime Steering
        │                     │                      │
        │                     │                      │
   CLAUDE.md              Subagents                Hooks
   Rules                  Skills*
   Skills*
        │
        └──────────────┐
                       │
                Global Behavior
                       │
                Output Styles
                System Prompt
```

`Skills` 故意在这里显得有点尴尬，因为它本来就横跨两边：Skill 的正文会进入模型 Context，但里面描述的是一套要执行的 Procedure。后面专门讲 Skill 时再把这件事拆开。

如果再换成 Runtime 视角，会更清楚：

```text
                     User / Repository
                            │
                            ▼
                  ┌──────────────────┐
                  │ Steering Layer   │
                  └──────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
     Context              Agent            Harness
          │                 │                 │
    CLAUDE.md           Subagent            Hook
      Rules               Skill          Permission
      Skill
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
                      Agent Runtime
                            │
                            ▼
                         Tools
                            │
                            ▼
                       Environment
```

这样一来，它和前面的 `runtime.md`、`tools.md`、`subagents.md` 就接上了。

`runtime.md` 里我关心的是：

```text
一次 Conversation 怎么跨很多轮继续活着？
```

`tools.md` 关心的是：

```text
模型提出一个动作以后，
Harness 怎样验证、授权、调度并执行？
```

`subagents.md` 关心的是：

```text
什么时候需要另起一个 Agent runtime，
以及它怎样获得自己的 Context、模型和工作环境？
```

到了这篇 `steering.md`，问题换成：

```text
人怎样把自己的意图，
注入这些已经存在的 Runtime 边界？
```

比如：

```text
                我的意图
                   │
        ┌──────────┼───────────┐
        │          │           │
     项目事实     工作流程     强制动作
        │          │           │
  CLAUDE.md      Skill        Hook
```

或者：

```text
                我的意图
                   │
              “调查这个问题”
                   │
                   ▼
              是否值得污染
              Main Context？
              /          \
            yes           no
             │             │
           Skill        Subagent
```

这才是后面几章真正要解决的问题。

我不需要背：

```text
CLAUDE.md 是 Markdown
Skill 也是 Markdown
Subagent 还是 Markdown
Rule 仍然是 Markdown
```

文件长什么样当然要会，但那只是接口语法。

更容易在真实项目里踩坑的是：明明每一种机制都配置成功了，Agent 还是越来越难用——`CLAUDE.md` 长到几百行、所有 Rule 全局加载、几十行 Procedure 常驻 Context、能自动执行的事情还在靠模型“记得去做”，一场搜索又把主会话塞满了中间结果。

这些问题靠继续润色 Prompt 很难解决，因为真正出问题的是**指令被放在了错误的生命周期里**。

接下来先从最常见的那个文件开始。

`CLAUDE.md` 到底应该常驻什么？哪些内容应该赶出去？为什么 Anthropic 会专门区分 root `CLAUDE.md`、nested `CLAUDE.md` 和 path-scoped Rules？

这也是 Steering 从“写一份项目说明”开始变成 Context Engineering 的地方。

## 2. `CLAUDE.md` 与 Rules：哪些知识值得一直让模型记着？

### 2.1 Root `CLAUDE.md` 是项目 Context 的底座

上一节最后留下的问题是：

```text
一条 instruction
到底应该活多久？
```

先看最简单的一类。

假设我刚打开一个完全陌生的项目，第一件事通常不是立刻改代码。我得先搞清楚：

```text
这是 pnpm 还是 npm？

怎么跑测试？

源码在哪？

是不是 monorepo？

某个 package 怎么单独测试？

生成文件能不能手改？

团队有哪些一直遵守的约定？
```

Claude Code 也面对同样的问题。

如果这些信息每次都靠 Agent 自己重新探索：

```text
ls
↓
读 package.json
↓
找 workspace config
↓
读 README
↓
猜测试命令
↓
再问用户
```

当然不是不能工作。

只是很多结论其实早就确定了。

比如一个仓库可能一直满足：

```text
package manager = pnpm

frontend = apps/web

backend = apps/api

shared packages = packages/*

unit tests = pnpm test

generated files under src/generated/ must not be edited manually
```

这些内容没有必要在每个任务里重新发现一次。

这就是 root `CLAUDE.md` 最自然的位置。

Anthropic 对它的定位也很直接：root `CLAUDE.md` 在 Session 开始时进入 Context，并在整个 Session 中保持可用；长会话发生 compaction 后，Claude Code 会重新读取它。官方给出的典型内容正是 build commands、directory layout、monorepo structure、coding conventions 和 team norms。

可以先把它理解成：

```text
Repository
    │
    ├── source code
    ├── config
    ├── tests
    └── CLAUDE.md
             │
             ▼
       Session starts
             │
             ▼
        Main Context
```

这和我在 `runtime.md` 里讨论 conversation state 时有一点不同。

`QueryEngine` 保存的是一次会话运行过程中不断变化的东西：

```text
messages
tool results
usage
file state
permission denials
...
```

而 root `CLAUDE.md` 更像一个外部的、可以重新读取的项目说明。

即使 Conversation 已经跑了很久：

```text
用户需求
↓
读文件
↓
改代码
↓
测试失败
↓
继续修改
↓
更多 Tool Result
↓
Compaction
```

`CLAUDE.md` 不是只能寄希望于“摘要的时候刚好没把它忘掉”。

Claude Code 在 compaction 后会重新读取这类 root 文件。

所以这两类状态的来源并不一样：

```text
Conversation history
        │
        ├── 会变化
        ├── 会增长
        └── 会被 compaction

CLAUDE.md
        │
        ├── 位于 repository / config
        └── compaction 后可以重新注入
```

这个区别挺实用。

例如：

```markdown
# CLAUDE.md

## Commands

- Install dependencies: `pnpm install`
- Run unit tests: `pnpm test`
- Run a single package test: `pnpm --filter <package> test`

## Repository layout

- `apps/web/`: frontend
- `apps/api/`: backend
- `packages/`: shared packages

## Conventions

- Do not edit files under `src/generated/` manually.
- Use existing repository utilities before adding new dependencies.
```

这份文件提供的东西并不复杂。

Claude 进入项目后，不需要再猜：

```text
npm test?
yarn test?
pnpm test?
```

也不用每一次碰到：

```text
src/generated/foo.ts
```

才临时推断这个文件到底是不是生成物。

我现在会把这一类信息叫做 **repository invariants**：对于大量不同任务，它们都相对稳定，而且 Claude 提前知道以后能少走一些重复的探索。

这里的“稳定”也不是说它永远不变。

如果项目从：

```text
npm
```

迁移到了：

```text
pnpm
```

那 `CLAUDE.md` 就应该跟代码一起改。

如果：

```text
apps/server/
```

重构成：

```text
apps/api/
```

旧目录说明也应该删掉。

Anthropic 甚至建议给共享 `CLAUDE.md` 指定 owner，并像 review code 一样 review 它的修改。

这点我很认同，因为错误的 `CLAUDE.md` 比没有还麻烦。

比如仓库实际上已经改成：

```text
pnpm test
```

文件里还留着：

```text
npm test
```

那么 Agent 不再需要自己探索正确答案——它会更有信心地拿着一个过期答案去执行。

于是 `CLAUDE.md` 的价值和风险其实来自同一个地方：

```text
它会被反复信任。
```

这里也可以解释为什么：

```text
“README 已经写了，为什么还要 CLAUDE.md？”
```

不是所有仓库都需要把 README 再复制一遍。

如果 README 已经清楚写着完整的开发说明，更好的 `CLAUDE.md` 完全可以像索引：

```markdown
# CLAUDE.md

Before changing the API, read `docs/api-architecture.md`.

Testing conventions live in `docs/testing.md`.

Do not edit generated files under `src/generated/`.
```

Anthropic 自己也建议把 `CLAUDE.md` 看成 codebase overview，或者一个指向其他资料的 index，而不是把所有文档重新塞一遍。

这和我以前写这类 Agent 配置时的习惯不太一样。

以前很容易觉得：

```text
给得越详细
    ↓
Claude 知道得越多
    ↓
效果应该越稳定
```

但 root `CLAUDE.md` 有一个很特殊的成本：

```text
它不是“需要时再看”的文档。
```

只要它属于 Session 启动时加载的那一层，里面的每一行都会进入每次 Session 的工作 Context。

所以真正麻烦的问题马上就来了：

> 如果某条 instruction 只有 5% 的任务会用到，它还有资格住在 root `CLAUDE.md` 里吗？

---

### 2.2 为什么 `CLAUDE.md` 不应该长成项目 Wiki？

假设一开始只有十几行：

```markdown
# CLAUDE.md

Use pnpm.

Run tests with `pnpm test`.

Frontend lives in `apps/web`.

Backend lives in `apps/api`.
```

用了一阵 Claude Code 后，大家会不断遇到新的问题。

有人发现 Claude 写 API 时忘了 Zod：

```markdown
All API handlers must validate input using Zod.
```

有人发现 migration 被改坏过：

```markdown
Never modify an existing migration.
Always create a new migration.
```

前端组发现它经常绕开 Design System：

```markdown
Always use components from packages/ui.
```

安全同事加了一套 checklist：

```markdown
Before modifying auth code:
1. Check authorization boundaries.
2. Check token lifetime.
3. ...
```

Release 又出过一次事故：

```markdown
Before release:
1. Run pnpm lint.
2. Run pnpm test.
3. Run pnpm build.
4. Update CHANGELOG.
5. ...
```

半年以后就可能得到：

```text
CLAUDE.md

  35 lines    repository overview
  24 lines    frontend conventions
  31 lines    backend conventions
  42 lines    database rules
  60 lines    security checklist
  45 lines    release procedure
  30 lines    review procedure
  ...
```

每一段几乎都能解释：

> “我们以前确实遇到过这个问题，所以最好告诉 Claude。”

单独来看都合理。

放在一起却有一个很现实的结果。

今天的任务只是：

```text
修 docs/quickstart.md 里的一个错误链接
```

Session 仍然可能带着：

```text
数据库 migration 规则

React component 约定

Auth review checklist

Release checklist

API validation 规则
```

一起开工。

这些 instruction 没有因为今天用不上就免费消失。

Anthropic 在 Steering 文章里专门提醒了这种情况：共享仓库的 `CLAUDE.md` 很容易变成一个“大家只往里面加、没人负责删”的配置文件；而 root 文件里的每一行都会进入每个 Session。随着文件变长，不相关内容会消耗 Context，也会稀释真正相关的 instructions。

这里的成本不只是账单上的 Token。

更麻烦的是 **instruction competition**。

假设当前任务真正相关的要求只有：

```text
1. docs 使用相对链接
2. 不要修改自动生成的 API reference
```

但 Context 里还同时存在几十条：

```text
Always ...
Never ...
Must ...
Before doing X ...
When modifying Y ...
```

模型面对的已经不是：

```text
“这里有两条项目约束。”
```

而是：

```text
“这里有五十条约束，
请自己判断今天哪两条值得注意。”
```

于是 Harness 又把一部分筛选工作扔回了模型。

这和我们本来使用 `CLAUDE.md` 的目的有点拧巴。

原本是为了省掉重复探索：

```text
Claude 不用每次重新猜项目事实。
```

文件无限增长以后，又变成：

```text
Claude 每次重新判断
哪些项目说明和当前任务有关。
```

所以 Anthropic 给了一个很具体的经验值：尽量把 `CLAUDE.md` 控制在 **200 行以内**。这个数字更适合看成维护警戒线，而不是“201 行 Claude 就坏掉”的硬限制。官方同时建议给它指定 owner，把 procedure 移到 Skills，把 team-specific conventions 移到只在相关时候加载的配置里。

我觉得判断一条内容该不该留下，可以用一个很土但很好用的问题：

```text
随便抽十个这个仓库里的正常任务，
其中有几个任务会需要这条信息？
```

例如：

```text
“这个项目使用 pnpm”
```

可能是：

```text
8 / 10
```

留在 root 很合理。

```text
“所有数据库 migration 都是 append-only”
```

可能是：

```text
2 / 10
```

已经值得考虑缩小作用范围。

而：

```text
完整 Release Checklist
```

可能是：

```text
0.5 / 10
```

那它大概率根本不是一个应该常驻的项目事实。

还可以换一种方式判断。

如果一句话回答的是：

```text
这个仓库是什么样的？
```

它很适合 `CLAUDE.md`：

```text
使用 pnpm。

这是一个 monorepo。

前端位于 apps/web。

不要直接修改 generated files。
```

如果一大段内容回答的是：

```text
当我要完成某一种任务时，
具体应该按哪几步操作？
```

就已经开始像 Procedure：

```text
如何 release

如何 code review

如何跑 security audit

如何生成 changelog
```

这部分后面会搬到 Skill。

如果 instruction 回答的是：

```text
只有碰到这一类文件时，
才必须遵守什么？
```

那么问题就不是内容写得长不长，而是它的**作用域本来就不是整个 repository**。

例如：

```text
*.sql
→ migration 不允许回改

src/api/**
→ handler 必须做 Zod validation

apps/web/**
→ 优先使用现有 Design System
```

这些约束本身可以很简短，但即使只有一行，也不代表必须让每一个 docs-only Session 都带着。

于是接下来真正要解决的，不是：

```text
怎么把 CLAUDE.md 再压缩 30 行？
```

而是：

```text
哪些 instruction 可以只在需要的时候出现？
```

Claude Code 为此提供了两种很接近、但作用域表达方式不同的机制：subdirectory `CLAUDE.md` 和 path-scoped Rules。

---

### 2.3 Nested `CLAUDE.md` 与 Path-scoped Rules

先考虑一个 monorepo：

```text
repo/
├── CLAUDE.md
├── apps/
│   ├── web/
│   │   ├── CLAUDE.md
│   │   └── src/
│   └── api/
│       ├── CLAUDE.md
│       └── src/
└── packages/
    └── ui/
```

根目录的 `CLAUDE.md` 可以只保留整个仓库都成立的信息：

```markdown
# Repository

This is a pnpm monorepo.

Run all tests with:

`pnpm test`

Shared packages live under `packages/`.
```

Web 团队自己的约定则放在：

```text
apps/web/CLAUDE.md
```

例如：

```markdown
Use components from `packages/ui` before creating new primitives.

Frontend tests use Vitest.

Routes live under `src/routes/`.
```

API 目录可以有另一份：

```text
apps/api/CLAUDE.md
```

```markdown
API tests use pytest.

Database access goes through the repository layer.

OpenAPI output is generated; do not edit it manually.
```

Anthropic 当前给出的加载语义是：位于启动目录以下的 subdirectory `CLAUDE.md` 不会在 Session 开始时全部塞进 Context。Claude 读取该子目录里的文件时，相应的 `CLAUDE.md` 才会加载。

所以一个只修改：

```text
apps/web/src/Button.tsx
```

的任务，不需要开局就同时读取：

```text
apps/api/CLAUDE.md
```

可以画成：

```text
Session start
    │
    ├── root CLAUDE.md
    │       ↓
    │   Main Context
    │
    ▼
Read apps/web/src/Button.tsx
    │
    ▼
discover apps/web/CLAUDE.md
    │
    ▼
load web conventions
```

这已经和 root 文件有了明显区别。

Root 的逻辑是：

```text
repository-wide
→ always resident
```

Nested 的逻辑则更接近：

```text
directory ownership
→ enter this part of the tree
→ load its local conventions
```

Compaction 行为也不同。

Anthropic 说明，root `CLAUDE.md` 在 compaction 后会重新读取；subdirectory `CLAUDE.md` 则不会一直保留，直到 Claude 再次触碰那个子目录才重新进入 Context。

也就是：

```text
Root CLAUDE.md
       │
       └── Session-level residency

Nested CLAUDE.md
       │
       └── Directory-triggered residency
```

对于 monorepo，这已经很好用了。

但目录并不总是最合适的作用域。

假设我有一条数据库规则：

```text
所有 migration 都只能追加，不能修改已有 migration。
```

相关文件可能散在：

```text
apps/api/migrations/
packages/database/migrations/
tests/fixtures/migrations/
```

为了这一个约束，分别维护三份：

```text
CLAUDE.md
```

就有点别扭。

或者 API Handler 并不全部住在单一目录里，而是：

```text
apps/auth/src/login.handler.ts
apps/users/src/user.handler.ts
apps/payment/src/payment.handler.ts
```

它们在目录树上分散，但文件语义相同。

这时 path-scoped Rule 更自然。

Claude Code 的 Rules 位于：

```text
.claude/rules/
```

一个 Rule 可以用 front matter 指定匹配路径：

```markdown
---
paths:
  - "src/api/**"
  - "**/*.handler.ts"
---

All API handlers must validate input with Zod before processing.
```

Anthropic 对它的描述是：只有 Claude 触及匹配的文件时，这条 Rule 才需要进入 Context；如果整个 Session 只在修改 docs，它可以一直不出现。

所以同样是 conditional loading，两种机制表达的是两种不同的边界。

```text
Nested CLAUDE.md
        │
        ▼
“进入这个目录以后，
这里有自己的工作约定。”


Path-scoped Rule
        │
        ▼
“无论这些文件散落在哪里，
只要匹配这一类文件，
就应用这条约束。”
```

比如：

```text
apps/web/CLAUDE.md
```

很适合说：

```text
这里是 Web 项目。
使用 Vitest。
优先复用 packages/ui。
Routes 放在 src/routes。
```

而：

```text
.claude/rules/migrations.md
```

更适合：

```yaml
---
paths:
  - "**/migrations/**"
---

Existing migrations are append-only.
Create a new migration instead of modifying an applied one.
```

这里还有一个容易漏掉的情况：**unscoped Rules**。

如果 Rule 没有 `paths`，它会像 root `CLAUDE.md` 一样在 Session 开始时加载，并在 compaction 后重新注入。

也就是说，把：

```text
50 行 API Rule
```

从：

```text
CLAUDE.md
```

搬到：

```text
.claude/rules/api.md
```

但完全不写 path scope，并不会自动解决 Context 膨胀。

文件是拆开了：

```text
CLAUDE.md
rules/api.md
rules/db.md
rules/frontend.md
```

Main Context 里却可能还是：

```text
全部加载
```

这是一种很容易出现的“目录结构优化了，Runtime 行为没变”。

真正有用的变化发生在：

```text
always loaded
        ↓
conditionally loaded
```

Anthropic 在原文里给的建议也很具体：如果约束只针对某类文件，比如 migration append-only，就优先考虑 path-scoped Rule；尤其当它是一个横跨多个目录的 concern 时，Rule 比 nested `CLAUDE.md` 更自然。

到这里，可以把目前出现的三层先整理一下：

```text
                    Instruction
                         │
             这条信息作用范围多大？
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   整个 Repository     某个目录         某类文件
        │                │                │
        ▼                ▼                ▼
 root CLAUDE.md    nested CLAUDE.md   path Rule
        │                │                │
 Session start      directory touch      path match
```

我觉得这里最值得留下来的，并不是：

```text
CLAUDE.md 放哪里
```

这种文件路径知识。

而是第一次真正看到 Claude Code 在做一种很朴素的 Context Engineering：

```text
已经确定某条信息什么时候才可能有用，
那就尽量不要更早加载它。
```

这也为下一个问题铺好了路。

到目前为止，我们处理的仍然主要是**知识和约束**：

```text
项目使用什么命令

某个目录怎么组织

某类文件必须遵守什么规则
```

但前面那个 40 行 Release Checklist 还没有找到住处。

它既不是什么“仓库长期事实”，也不是“一碰到某类文件就自动成立的约束”。

它描述的是：

```text
当我要做 Release 时，
请按照这套步骤工作。
```

这种 instruction 再继续塞进 `CLAUDE.md` 或 Rule，就开始有些勉强了。

下一层正好是 Skill。

## 3. Skills：Instruction 什么时候应该变成 Procedure？

### 3.1 事实和 Procedure 是两种东西

前两节一直在处理“Claude 应该知道什么”。

比如：

```text
这个仓库使用 pnpm。

apps/web 是前端。

migration 只能追加，不能回改。

修改 **/*.handler.ts 时必须做 Zod validation。
```

这些 instruction 的共同点是：Claude 一旦进入对应作用域，就应该把它们当成当前工作的背景条件。

但下面这段东西明显不太一样：

```markdown
发布前：

1. 确认工作区干净；
2. 更新版本号；
3. 运行 lint；
4. 运行 unit tests；
5. 运行 build；
6. 检查 changelog；
7. 生成 release notes；
8. 创建 tag；
9. 推送 release artifact。
```

它不是在描述仓库。

它是在描述：

```text
当某个任务发生时，
Claude 应该怎样一步一步完成它。
```

前者更像 **knowledge / constraints**。

后者更像 **procedure**。

Anthropic 在 Steering 文章里直接把 Skills 的典型用途写成了 procedural workflows，例如 deploy workflow、release checklist 和 review process；如果 `CLAUDE.md` 里已经出现一段三十行左右的 procedure，官方建议就是把它搬进 `.claude/skills/`。

这个区别看起来简单，实际挺容易写混。

比如：

```markdown
Run tests with `pnpm test`.
```

我会留在 `CLAUDE.md`。

因为它回答的是：

```text
这个仓库怎么跑测试？
```

但如果写成：

```markdown
When verifying a bug fix:

1. Reproduce the original failure.
2. Run the narrowest relevant test.
3. Apply the fix.
4. Re-run the narrow test.
5. Run the related test suite.
6. Report the original failure and final result separately.
```

它已经在回答另一个问题：

```text
“验证一个 Bug Fix”这项工作，
应该按什么顺序完成？
```

这就更像 Skill。

可以先用一个不严谨但很好记的分界：

```text
CLAUDE.md / Rule
        ↓
What should Claude know?


Skill
        ↓
How should Claude do this task?
```

当然，这条线并不是说 Skill 里不能出现事实。

一个 Release Skill 里当然可能写：

```text
release branch = main
artifact directory = dist/
```

但这些信息存在的原因，是为了服务那套 Release Procedure。

反过来也一样。

`CLAUDE.md` 里当然可以写：

```text
Before submitting a change, run tests.
```

这种很短的工作约定没有必要为了“纯粹”硬拆成 Skill。

真正开始值得迁移的，是 instruction 已经出现明显的过程结构：

```text
先做 A

检查 B

如果 B 失败则做 C

成功后执行 D

最后输出 E
```

换成控制流看会更明显：

```text
Task
  │
  ▼
Inspect current state
  │
  ▼
Run check
  │
  ├── fail ──? diagnose ──? fix ──┐
  │                               │
  └────────────── success ?────────┘
                  │
                  ▼
              verify result
                  │
                  ▼
                report
```

这已经不像一句“项目约定”了。

它是一份给 Agent 执行的 playbook。

如果继续把这种东西塞在 root `CLAUDE.md`：

```text
Session Start
    │
    ▼
加载：

项目布局
测试命令
编码规范
+
Release Procedure
+
Code Review Procedure
+
Security Audit Procedure
+
Blog Writing Procedure
```

那么又回到 Macro 2 的老问题：

今天明明只是：

```text
修一个 README typo
```

Claude 却要先带着一整套：

```text
“怎样发布”
“怎样审计依赖”
“怎样写博客”
```

开始工作。

Skill 的第一个作用，就是把这种 **task-specific procedure** 从长期驻留的 Context 里移出去。

但如果只是把：

```text
CLAUDE.md
```

拆成：

```text
.claude/skills/release/SKILL.md
```

而 Claude Code 开局仍然把所有 Skill 全文读一遍，那其实也没有解决什么。

真正让 Skill 有意思的，是它的加载方式。

---

### 3.2 Skill 为什么适合做 Progressive Disclosure？

一个 Skill 的典型目录长这样：

```text
.claude/
└── skills/
    └── code-review/
        ├── SKILL.md
        ├── scripts/
        └── references/
```

其中 `SKILL.md` 至少会有类似：

```markdown
---
name: code-review
description: Review the current diff for correctness, security, and maintainability.
---

# Code Review

...
```

Claude Code 在 Session 开始时并不会把这里的完整正文全部加载进来。

官方当前的行为是：

```text
Session Start
    │
    ▼
只加载 Skill 的
name + description
```

真正匹配到任务，或者用户显式调用 Skill 后：

```text
Skill invoked
    │
    ▼
加载完整 SKILL.md
```

Skill 既可以通过 slash command 触发，也可以由 Claude 根据任务和 Skill description 自动匹配。

这就形成了一个很典型的 **Progressive Disclosure**：

```text
Level 1
────────────────────────
“我有哪些能力？”

code-review
release
deploy
security-audit
blog-shape

        │
        │ only when needed
        ▼

Level 2
────────────────────────
“这项能力具体怎么执行？”

完整 SKILL.md
scripts
references
resources
```

平时 Claude 只需要知道：

```text
有一个 release Skill，
它大概负责发布流程。
```

不需要提前背完整的发布说明。

只有用户真的说：

```text
帮我做这次 release
```

它才有理由继续展开：

```text
release
  │
  ▼
读取完整 procedure
  │
  ▼
开始执行
```

对 Context 来说，这和我们上一节的 path-scoped Rule 很像，都是：

```text
不要在信息还没用到时，
提前占用 Main Context。
```

但二者的触发依据并不一样。

Rule 是：

```text
我碰到了什么文件？
```

例如：

```text
**/*.handler.ts
        ↓
加载 API validation rule
```

Skill 是：

```text
我现在正在做什么任务？
```

例如：

```text
“review 这个 PR”
        ↓
加载 code-review Skill
```

所以两种 conditional loading 实际上落在两个不同维度：

```text
                 Conditional Context

          ┌──────────────┴──────────────┐
          │                             │
       File Scope                    Task Scope
          │                             │
        Rules                         Skills
```

这个区别对我自己写 Agent 配置挺有用。

以前看到一段“不常用的 instruction”，第一反应往往只是：

```text
那我想办法不要全局加载。
```

现在还得再问一句：

```text
它到底是跟“文件”绑定，
还是跟“任务”绑定？
```

如果是：

```text
编辑 migration 时遵守 append-only
```

这是 File Scope。

如果是：

```text
执行 database migration review 时，
按六步 checklist 检查
```

这是 Task Scope。

二者甚至可以同时存在：

```text
                      Database change
                           │
             ┌─────────────┴─────────────┐
             │                           │
      migration Rule                db-review Skill
             │                           │
      “不能回改旧文件”           “Review 要检查哪些步骤”
```

这里 Skill 还有一个 compaction 细节。

Anthropic 当前说明：已经调用过的 Skills 在发生 compaction 后，会在一个共享的 Skill token budget 内重新注入；如果一个 Session 调用了很多 Skills，较早的 Skill 会先从这个预算中被淘汰。

所以 Skill 也不是：

```text
调用一次
→ 永远完整常驻
```

更接近：

```text
未调用
→ 只有 descriptor

调用
→ body 进入 Context

Compaction
→ 在 Skill budget 内重新注入
→ 太多时旧 Skill 先退出
```

这和 root `CLAUDE.md` 的语义又不同：

```text
root CLAUDE.md
        │
        └── 这是 Session 的长期底座


Skill
        │
        └── 这是当前阶段临时展开的 Procedure
```

到这里，“Skill = 一个比较长的 Prompt 文件”这个理解已经不太够用了。

文件当然还是 Markdown。

但 Harness 给它增加了两个行为：

```text
discoverability
+
on-demand loading
```

于是一个原本只能：

```text
把所有 instruction 塞进 System Prompt
```

的问题，被拆成：

```text
先告诉模型：
“有哪些 procedure 可以用”

真正用到时：
“再把 procedure 展开”
```

这和软件里常见的 lazy loading 很像。

我不会说两者实现机制完全一样，但用这个类比记忆很顺手：

```text
Eager loading
────────────────────
开局加载所有 procedure

Context:
[release]
[review]
[deploy]
[audit]
[writing]
...


Lazy / progressive loading
────────────────────────────
开局：
release: 发布流程
review: Code Review
deploy: 部署流程
...

需要 review 时：
        ↓
展开 review body
```

Anthropic 官方表格也把 Skill 的 Context cost 标为低，理由就是 full body 只在调用时进入 Context。

不过，说到这里仍然有一个容易把 Skill 写坏的地方。

既然 `description` 决定 Claude 是否知道“什么时候该想到这个 Skill”，那 description 就不能写成：

```yaml
description: A useful skill.
```

或者：

```yaml
description: Helps with code.
```

它至少得把触发场景说清楚：

```yaml
description: >
  Review the current code diff for correctness, security,
  test coverage, and maintainability without editing files.
```

因为 Progressive Disclosure 的第一层并不是空壳。

Claude 正是靠这一小块 metadata 判断：

```text
“当前任务和这个 Skill 有没有关系？”
```

Skill body 可以写得很详细，但入口写得含糊，Agent 可能根本不会走进去。

这也是我后来再看自己的 `Hugo-Blog-Skills` 时觉得最有意思的一点。

我本来只是想“把写博客的方法整理成几个 Skill”。

结果真正拆下去以后，已经不只是把一份写作 Prompt 分成几个文件了。

---

### 3.3 用 `Hugo-Blog-Skills` 看一个 Procedure 是怎么被拆开的

拿我现在正在用的 `Bubblevan/Hugo-Blog-Skills` 来说。

如果最开始粗暴一点，我完全可以在一个巨大的：

```text
CLAUDE.md
```

里写：

```markdown
写技术博客时：

1. 先确认文章意图；
2. 读取所有原始材料；
3. 提取 evidence；
4. 设计文章结构；
5. 给出 2~3 个 opening；
6. 设计 Macro；
7. 每个 Macro 拆成 Beats；
8. 每个 Beat 标记 depends_on；
9. 每个 Beat 只能 introduce 一个 concept；
10. 写正文；
11. 检查 AI 味；
12. humanize；
13. 生成 Hugo Markdown；
14. ...
```

这样肯定也能跑。

问题是，我平时让 Claude Code：

```text
修一个 Hugo shortcode
```

时，也得背这套写作流程。

而且“写博客”本身还不是一个单步任务。

里面其实存在几个完全不同的阶段：

```text
原始材料
   │
   ▼
Research / Evidence
   │
   ▼
Shape
   │
   ▼
Beats
   │
   ▼
Draft
   │
   ▼
Edit / Humanize
```

拿现在的 `writing-shape` 来看，它的 description 已经明确限定了职责：

```text
把技术笔记、research、logs、code evidence
转换成 article information architecture。
```

而且明确说它负责的是：

```text
what should this article cover,
in what order,
and why?
```

它不负责下一句话具体怎么写，也不直接输出 Hugo 成稿。

这个边界非常像一个程序接口。

输入：

```text
raw material
+
article intent
+
writing rules
```

输出：

```text
thesis

scope

candidate openings

Macro purposes

Beat plan

evidence mapping

grounding ledger

gaps
```

然后它明确 handoff 到：

```text
writing-beats
```

而不是自己继续写。

如果把它画出来：

```text
┌──────────────────────┐
│    writing-shape     │
│                      │
│ raw materials        │
│       ↓              │
│ evidence inventory   │
│       ↓              │
│ thesis / scope       │
│       ↓              │
│ Macro / Beat plan    │
│       ↓              │
│ grounding ledger     │
└──────────┬───────────┘
           │
           │ handoff
           ▼
┌──────────────────────┐
│    writing-beats     │
│                      │
│ approved shape       │
│       ↓              │
│ one Beat at a time   │
│       ↓              │
│ reader knowledge     │
│ traversal            │
└──────────────────────┘
```

这已经不是一句：

```text
“请帮我认真写博客。”
```

能描述清楚的东西了。

而且有些规则甚至已经开始像程序 contract。

例如 `writing-shape` 要求：

```text
每个 Beat 必须有 depends_on

每个 Beat exactly one introduces concept

每个 claim 要绑定 evidence ID

不能把 inference 升级成 observation

Shape 不能直接假装自己已经写完正文
```

这些限制的意义不在“让 Claude 写得更文艺”。

它们是在限制工作流中的**状态转换**。

比如：

```text
raw claim
   │
   │ 没 evidence
   ▼
unknown
```

不能直接：

```text
unknown
   │
   ▼
verified
```

或者：

```text
Shape
  │
  ├── 决定 Macro / Beat
  │
  └── 不负责 final prose

writing-beats
  │
  └── 按 approved Shape 向前推进
```

把这些都放进一个长期 system prompt，当然也可以。

但我更喜欢现在这种拆法，因为每个 Procedure 都有自己的入口和边界。

例如：

```text
“我现在有一堆资料，不知道文章怎么组织”
                │
                ▼
         writing-shape
```

而：

```text
“Shape 已经定了，开始一 Beat 一 Beat 写”
                │
                ▼
         writing-beats
```

再比如这篇 `steering.md`。

我们前面先确定：

```text
Macro 1
为什么一个 CLAUDE.md 不够

Macro 2
CLAUDE.md / Rules

Macro 3
Skills

Macro 4
Subagents
...
```

现在真正写正文时，没有重新设计整个文章。

只是沿着已经接受的知识顺序往下走。

这就是 Procedure 被拆开以后带来的一个挺实际的变化：

```text
每一步 Claude
只需要关心当前阶段的 contract。
```

而不是每次都拿着一份：

```text
《如何从零到发布完成一篇博客的 300 行超级 Prompt》
```

重新判断现在做到第几步。

这和前面讲的 Progressive Disclosure 正好对上了。

Claude Code Session 开始时，没有必要把：

```text
writing-shape/SKILL.md
writing-beats/SKILL.md
blog-draft/SKILL.md
stop-slop/SKILL.md
...
```

全部全文塞进 Context。

更合理的状态是：

```text
Main Context
    │
    ├── 知道 writing-shape 是干什么的
    ├── 知道 writing-beats 是干什么的
    ├── 知道 stop-slop 是干什么的
    │
    └── 当前真的需要哪一个
              │
              ▼
         再展开正文
```

这也是为什么我现在不会再把 Skill 理解成：

```text
“可以用 /xxx 调用的 Prompt 模板”
```

这个描述没有错，但漏掉了 Harness 最有价值的那半截。

更完整一点应该是：

```text
Skill
=
可发现的 task capability
+
按需加载的 procedure
+
它需要的 scripts / references / resources
```

Anthropic 当前也明确把 Skill 描述成一个目录，而不只是单个 Markdown：里面可以包含 instructions、scripts 和 resources；`SKILL.md` 负责提供 name、description 和正文。

所以一些 Procedure 还可以继续往下拆。

例如：

```text
release Skill
│
├── SKILL.md
│
├── scripts/
│   └── verify-release.py
│
└── references/
    └── release-policy.md
```

正文负责告诉 Agent：

```text
什么时候执行什么步骤。
```

脚本负责完成适合代码确定执行的检查。

reference 保存不值得全部塞进 `SKILL.md` 的详细资料。

到了这里，Skill 已经很接近一个小型的 Agent capability package 了。

但这里马上会出现下一个问题。

假设我的 Procedure 是：

```text
搜索整个仓库
读取 40 个文件
分析 dependency graph
跑几个命令
最后给我一份结论
```

我当然可以把它写成 Skill。

问题是，Skill 被调用以后，这些：

```text
搜索结果
40 个文件内容
grep 输出
错误方向
中间推理
dependency 信息
```

仍然发生在**当前 Main Context** 里。

Progressive Disclosure 只解决了：

```text
Procedure 什么时候加载？
```

它没有解决：

```text
Procedure 执行过程中产生的大量中间信息
应该放在哪里？
```

这正是 Skill 和 Subagent 最容易混淆的地方。

下一节不再重新讲一遍 `AgentTool.tsx` 的内部实现——那部分已经留给 `subagents.md`。

这里只解决一个问题：

```text
什么时候应该继续在当前 Context
执行一个 Skill，

什么时候应该干脆
给这个任务另开一个 Context？
```

## 4. Subagents：什么时候不是加载 Instruction，而是换一个 Context？

### 4.1 Skill：在当前 Context 里换一套 Procedure

上一节最后留了一个没解决的问题。

Skill 确实能避免：

```text
Session 一开始
就把所有 Procedure 全文加载进来
```

但 Skill 被调用以后，工作还是发生在当前这条会话里。

假设我有一个：

```text
dependency-audit
```

Skill。

里面的 Procedure 大概是：

```text
1. 读取 package.json
2. 找 workspace packages
3. 搜索依赖声明
4. 检查重复版本
5. 查找废弃依赖
6. 检查 lockfile
7. 输出风险
```

调用以后，大致会发生：

```text
Main Context
    │
    ├── 用户原始需求
    ├── 前面修改代码的记录
    ├── 已经读过的文件
    ├── 测试结果
    │
    ├── dependency-audit Skill body
    │
    ├── package.json
    ├── workspace config
    ├── grep 结果
    ├── lockfile 片段
    ├── 第一次错误搜索
    ├── 第二次搜索
    └── 最后的 audit 结论
```

这里没有任何异常。

Skill 本来就是这么工作的：Procedure 被按需加载，然后 Claude 在当前线程里执行它。

这甚至经常是我想要的效果。

比如 Code Review：

```text
我：
看看这个 diff

Claude：
先检查 changed files
↓
发现 auth.ts 有问题
↓
我：
这一条先别管，是兼容旧接口
↓
Claude：
继续检查剩下的问题
```

我需要看到中间过程，也可能随时打断、补充背景、改变检查重点。

那就应该留在 Main Context。

Anthropic 给 Skill 和 Subagent 的区分也是这样：如果我希望 Procedure 在主线程里展开，而且需要看见、干预它的步骤，就更适合 Skill；Subagent 更适合那些中间过程没必要污染主线程的 Side Task。

所以：

```text
Skill
```

真正改变的是：

```text
当前 Agent 使用哪套 Procedure
```

而不是：

```text
这项工作由谁来做
```

调用前：

```text
Main Agent
    │
    └── 当前 Context
```

调用 Skill：

```text
Main Agent
    │
    ├── 当前 Context
    │
    └── + code-review procedure
```

Agent 没换。

Context 也没有新开一份。

只是这个 Agent 临时获得了一套更具体的做事方法。

这也是为什么上一节我把 Skill 写成：

```text
Progressive Disclosure
```

而没有直接叫：

```text
Context Isolation
```

它解决的是：

```text
Procedure 什么时候进来？
```

还没有解决：

```text
Procedure 进来以后，
产生的所有中间信息放在哪里？
```

这个问题在短任务里没什么。

但一旦任务变成：

```text
搜索整个代码库

分析一份 200 MB 日志

调查 30 个依赖

阅读几十个 issue

对比五种实现方案
```

情况就开始变化。

我真正需要的可能已经不是：

```text
“Main Agent，请加载一份更好的操作手册。”
```

而是：

```text
“这件事你别在这里展开了。
找另一个 Context 做完，
把结论拿回来。”
```

这才轮到 Subagent。

---

### 4.2 Subagent：把 Side Task 放进新的 Context

Anthropic 当前把 Subagent 定义成：

```text
.claude/agents/
```

里的独立 assistant 定义。

它和 Skill 开局时有一点像。

Session 开始后，主 Agent 会知道有哪些 Subagent 可用，包括它们的：

```text
name
description
tool list
```

但 Subagent 正文不会因此全部塞进父 Context。

真正调用时，Claude 通过 Agent tool 给它一个 prompt，Subagent 的正文成为那个 Agent 自己的 system prompt。

到这里和 Skill 还只是“加载位置不一样”。

真正把两者拉开的，是下一步：

> Subagent 的完整 instruction body 不会进入父会话；它在自己的 fresh context window 里运行，最后只有 final message 和 metadata 返回主 Session。

比如我正在修一个复杂 Bug：

```text
Main Context
────────────────────────

用户：
支付接口偶发 500，
帮我查出来并修掉。

Claude：
读 payment.ts
读 retry.ts
定位到一个可疑分支
...
```

这时候我还想调查：

```text
production.log
```

里面过去 24 小时的所有 500。

直接在主线程查：

```text
Main Context
    │
    ├── Bug 原始需求
    ├── payment.ts
    ├── retry.ts
    ├── 当前修改思路
    │
    ├── grep production.log
    ├── 800 条匹配
    ├── 过滤 trace id
    ├── 找时间窗口
    ├── 第二轮 grep
    ├── 第三轮 grep
    ├── 误命中的 health check
    ├── 一堆 stack trace
    └── 最后才得到三个异常模式
```

其中真正对修 Bug 有长期价值的，可能只有：

```text
17:42:31
payment retry exhausted
trace_id=xxx

共同特征：
upstream timeout 后第二次 retry
使用了已经失效的 request body。
```

前面的几十次搜索只是为了得到这两句话。

如果这些中间结果之后再也不会用，它们留在 Main Context 里就很浪费。

换成 Subagent：

```text
Main Agent
─────────────────────

“调查 production.log 中
和 payment 500 有关的异常模式”
          │
          │ Agent Tool
          ▼

Log-analysis Subagent
─────────────────────

fresh context

grep
↓
过滤
↓
读 stack trace
↓
按 trace id 聚合
↓
排除 health check
↓
统计异常模式
↓
形成结论

          │
          │ final message
          ▼

Main Agent
─────────────────────

“过去 24 小时共发现 3 类 payment 500。
其中 81% 出现在 upstream timeout
之后的第二次 retry……”

```

父 Agent 得到的已经是压缩后的调查结果。

这就是一个很直接的 **information boundary**：

```text
             Parent Context
                   │
                   │ task
                   ▼
          ┌──────────────────┐
          │ Subagent Context │
          │                  │
          │ search           │
          │ grep             │
          │ read             │
          │ failed attempts  │
          │ aggregation      │
          └────────┬─────────┘
                   │
                   │ final result
                   ▼
             Parent Context
```

这里的“压缩”不要和 Claude Code 的 Compaction 混在一起。

Compaction 是：

```text
一个 Context 太长
        ↓
压缩它自身的历史
```

Subagent Isolation 是：

```text
这部分工作一开始
就不进入 Parent Context
        ↓
只把需要跨边界的信息带回来
```

两者解决的时间点不一样。

可以画成：

```text
Compaction
──────────────────────────

Main Context
A B C D E F G H I J
        │
        ▼
      summary


Subagent
──────────────────────────

Main Context
A B C
   │
   ├───────────────┐
   │               ▼
   │        Subagent Context
   │        D E F G H I
   │               │
   │               ▼
   │            summary
   │               │
   ?───────────────┘
   │
A B C + summary
```

这个区别我觉得挺重要。

如果一个 Side Task 天生只需要：

```text
输入任务
↓
大量中间调查
↓
最终结论
```

那么先把垃圾全塞进 Main Context，再寄希望于后面的 Compaction 清掉，有点倒过来了。

一开始就隔离更干净。

Anthropic 给出的典型例子也正是：

```text
deep search
log analysis
dependency audit
```

因为这些任务最容易产生大量“为了得到答案而必须看，但之后不需要保留”的中间信息。

所以我现在判断 Skill 和 Subagent 时，不太会再问：

```text
这个任务大不大？
```

任务“大”并不能直接推出 Subagent。

比如：

```text
重构一个核心模块
```

可能很大。

但我需要持续看到：

```text
设计判断
修改结果
测试反馈
下一步选择
```

那它完全可以继续留在 Main Agent。

反过来：

```text
查一下这 12 个 package
分别用了哪个 React 版本
```

任务可能不复杂。

但中间会产生一堆：

```text
package.json
grep
workspace path
version
```

我只要最终表格。

这种任务反而很适合 Subagent。

更准确的问题应该是：

```text
完成这项任务所产生的
中间 Context，

父 Agent 后面还需要吗？
```

如果需要：

```text
留在 Main Thread
→ Skill
```

如果大部分不需要：

```text
隔离
→ Subagent
```

---

### 4.3 Context Isolation 到底解决了什么？

这里容易把 Subagent 理解成：

```text
“多开一个 Claude，
所以算力更强了。”
```

这个说法有时候结果上没错，但并没有抓住 Steering 里最有用的那部分。

至少从这篇文章的角度，我更关心三个具体问题：

```text
Context 污染

任务专门化

并行 Side Work
```

先看第一个。

#### 1. 把 disposable context 留在任务内部

很多 Agent 工作都会产生一种很尴尬的信息：

```text
为了完成当前步骤必须读，

但主任务之后不会再引用。
```

例如：

```text
搜索候选文件时的几十个 grep result

分析日志时的大量正常请求

依赖审计里的 package metadata

查 API 时试错过的多个入口

调研时淘汰掉的候选资料
```

我会把它们叫做：

```text
disposable context
```

不是说这些信息没价值。

恰恰相反，它们在 Subtask 内部非常有价值。

问题只是：

```text
它的有效作用域
只有这个 Subtask。
```

如果把所有局部状态都提升到 Parent：

```text
Parent Context
│
├── Parent Task State
├── Subtask A State
├── Subtask B State
├── Subtask C State
└── ...
```

父 Agent 后面还得自己重新判断：

```text
哪些是当前真正应该继续关注的？
```

而隔离以后：

```text
Parent
│
├── Main Task State
│
├── Result A
├── Result B
└── Result C
```

信息密度会高很多。

这和软件里的函数局部变量有一点像。

函数内部可能有：

```python
candidate_files
matches
filtered_matches
temporary_index
retry_count
```

调用方不需要获得所有局部变量。

它通常只要：

```python
return result
```

Subagent 也提供了类似的边界：

```text
internal working state
        │
        X
        │
   parent does not need it

final message
        │
        ▼
      parent
```

这个类比不是 Claude Code 的官方实现描述，只是我自己理解 Context Isolation 时比较顺手的一种方式。

---

第二个问题是专门化。

一个 Subagent 文件自己的 body 会成为它的 system prompt，而且定义还可以指定 model、tool access 等配置。

这意味着“换一个 Context”通常还可以顺便换掉一些 Runtime 条件：

```text
Main Agent
│
├── Main instructions
├── Main tools
└── Main model
```

调用：

```text
security-reviewer
```

之后可以变成：

```text
Security Subagent
│
├── security-specific system prompt
├── restricted / specialized tool set
└── configured model
```

我在单独的 `subagents.md` 里已经从 Claude Code v2.1.88 的 `AgentTool.tsx` 快照看过这件事。

那个版本的 input schema 至少能看到：

```ts
description
prompt
subagent_type?
model?
run_in_background?
```

扩展参数里还存在：

```ts
name?
team_name?
mode?
isolation?
cwd?
```

其中甚至有：

```ts
isolation: 'worktree'
```

这样的 Runtime 隔离能力。

这里要把证据边界说清楚。

`v2.1.88` 是我手里的历史源码快照。

2026 年现在的 Claude Code 产品行为，我还是以 Anthropic 当前文档和博客为准；旧源码只能证明这些 delegation / model override / background / isolation primitives 在那个版本里已经存在，不能拿它反推今天所有内部实现都没变。

在这篇 Steering 笔记里，我也不准备再把那些源码重新讲一遍。

这里需要的结论只有：

```text
Subagent 的隔离
不只是 Markdown 写法上的隔离。

Harness 本身就有
独立执行单元所需要的 Runtime 边界。
```

---

第三个问题是并行。

如果两个 Side Task 互不依赖：

```text
调查测试失败原因

同时

检查 dependency 是否有 breaking change
```

把它们全部串在 Main Agent 上：

```text
Main
 │
 ├── 做 A
 │
 └── 做完 A 再做 B
```

当然可以。

但独立 Agent 给 Harness 留出了：

```text
Main
 │
 ├────────? Agent A
 │
 ├────────? Agent B
 │
 └── 继续自己的工作
```

这种可能。

Anthropic 当前甚至提到 Subagent 可以继续嵌套，最多五层；动态 workflow 可以编排大量 background agents，而 orchestration plan 和部分中间结果可以放在 script variables 中，而不必全部留在 Claude 的 Context Window。

不过这句话很容易被写成：

```text
“Subagent 越多越先进。”
```

我不太想这么理解。

并行以后会马上冒出另一批工程问题：

```text
任务怎么拆？

两个 Agent 会不会改同一个文件？

谁拥有最终决定权？

结果冲突怎么办？

失败怎么恢复？

什么时候应该 cancel？

成本值不值得？
```

这些已经接近 orchestration，而不是这一篇 Steering 想展开的范围。

所以这里仍然只保留一个判断。

当一个任务满足：

```text
中间信息很多
+
父任务以后基本不用
+
结果可以通过一个清晰接口返回
```

它就是一个很好的 Context Isolation 候选。

可以把 Macro 3 和 Macro 4 放在一起：

```text
                  一项新任务
                      │
                      ▼
            有没有现成 Procedure？
                 /          \
               no            yes
                              │
                              ▼
                 中间过程是否应该留在
                    Main Context？
                       /       \
                     yes        no
                      │          │
                      ▼          ▼
                    Skill     Subagent
```

再精确一点：

```text
Skill
────────────────────────────

same agent
same main context
+
load procedure

适合：
“我想看着它怎么做，
中途还可能继续 Steering。”


Subagent
────────────────────────────

delegated agent
fresh context
+
return final result

适合：
“过程你自己消化，
把调查结果带回来。”
```

这条边界也解释了为什么 Skill 和 Subagent 经常一起出现。

例如一个：

```text
dependency-audit
```

Subagent 自己完全可以再使用某套：

```text
dependency-audit Skill
```

一个负责：

```text
在哪里执行
```

另一个负责：

```text
怎么执行
```

它们并不冲突。

到这里，前四种 Steering 手段已经开始分层：

```text
CLAUDE.md
    │
    └── Session 长期需要知道什么

Rules
    │
    └── 哪类文件需要额外遵守什么

Skills
    │
    └── 某类任务应该怎样执行

Subagents
    │
    └── 哪些任务应该在独立 Context 里执行
```

但还有一种要求始终没有被这四层解决。

比如我真的要求：

```text
每次 Edit 之后，
必须运行 formatter。
```

我可以写进 `CLAUDE.md`。

可以写 Rule。

可以做一个 formatting Skill。

甚至可以专门开一个 Formatter Subagent。

但它们最终都有一个共同点：

```text
先把要求告诉模型
        ↓
再希望模型正确行动
```

而我的真实需求其实是：

```text
只要 Edit event 发生
        ↓
formatter 就执行
```

到了这种地方，再继续研究“Instruction 应该放在哪个 Context”已经走偏了。

下一层需要看的不是另一种 Prompt。

是 Claude Code Runtime 的 lifecycle event。

也就是 Hooks。

## 5. Hooks：有些事情根本不应该“告诉 Claude 去做”

### 5.1 Instruction 与 Enforcement 是两回事

前面几章出现的 Steering 手段，基本都有一个共同前提：

```text
先把某些信息交给 Claude
        ↓
Claude 读到它
        ↓
Claude 根据这些信息决定下一步动作
```

`CLAUDE.md` 是这样。

Rule 是这样。

Skill 也是这样。

即使 Subagent 换了一份 Context，真正执行任务的仍然是另一个模型。

这套机制很适合表达：

```text
项目使用 pnpm

修改 API 时要遵守什么规范

Code Review 应该按什么步骤进行

日志分析可以交给哪个 Agent
```

但假如要求变成：

```text
每次修改代码以后都运行 formatter。
```

我当然还能写：

```markdown
# CLAUDE.md

IMPORTANT:

After EVERY file edit,
ALWAYS run the formatter.

NEVER forget this.
```

甚至还可以再加粗一点：

```markdown
THIS IS CRITICAL.

You MUST run prettier after EVERY edit.
```

这在 Prompt 层面确实表达得非常清楚。

可 Runtime 路径还是：

```text
Edit 完成
   │
   ▼
Claude 获得 tool result
   │
   ▼
Claude 继续推理
   │
   ▼
Claude 是否想起 formatter？
   │
   ├── yes → Bash("prettier ...")
   │
   └── no  → 继续下一步
```

`ALWAYS` 写了五遍，并没有把最后那个分支删掉。

如果我真正想表达的是：

```text
只要 Edit 发生
formatter 就一定跟着运行
```

那期望的执行图其实是：

```text
Edit
 │
 ▼
Edit completes
 │
 ▼
PostToolUse event
 │
 ▼
formatter
```

Claude 不需要“记得”。

这件事直接成为 Harness 生命周期的一部分。

Anthropic 在 Steering 文章里把这个区别说得很直白：Hooks 适合那些应该 **deterministically** 发生的行为，例如编辑后运行 linter、任务完成后通知 Slack，或者在危险命令执行前阻止它。Hook 的触发由 Claude Code Runtime 决定，而不是让模型判断这次要不要执行。

这也是我现在觉得最值得区分的一对概念：

```text
Instruction
    │
    ▼
“告诉 Agent 应该怎么做”


Enforcement / Automation
    │
    ▼
“让 Runtime 保证某件事发生”
```

这两个东西并不是互斥的。

比如项目里完全可以同时有：

```markdown
# CLAUDE.md

Run formatting before considering a code change complete.
```

让 Claude 理解项目习惯。

同时配置一个 Hook：

```text
PostToolUse(Edit|Write)
        ↓
run formatter
```

让 Runtime 自动完成。

前者影响 Claude 的理解。

后者改变实际执行路径。

---

这里再看一个更敏感的例子：

```text
NEVER run rm -rf.
```

把它写进 `CLAUDE.md`，表达的是：

```text
Claude 看见这条 instruction
        ↓
希望 Claude 不提出 rm -rf
```

但如果某一轮模型还是生成了：

```text
Bash
{
  command: "rm -rf ..."
}
```

那么 instruction 已经失败了。

这时候我真正需要的不是：

```text
Prompt 再严厉一点
```

而是一个位于 Tool execution 前面的控制点：

```text
Model
  │
  ▼
tool_use
  │
  ▼
PreToolUse
  │
  ├── safe → continue
  │
  └── dangerous → deny
  │
  ▼
Permission
  │
  ▼
Execute
```

这恰好能和前面的 `tools.md` 接起来。

那篇里我已经把生产级 Tool 看成一份 runtime contract：Harness 不只要知道函数怎么调用，还要关心输入是否合法、动作是否 destructive、是否需要 permission、能不能 interrupt，以及最后怎样执行。

所以现在加入 Hook，并不是凭空又多了一层“Claude Code 魔法”。

它只是把 Tool Pipeline 再展开了一点：

```text
Model proposes tool_use
        │
        ▼
structured input
        │
        ▼
schema / validation
        │
        ▼
PreToolUse Hook
        │
        ▼
permission evaluation
        │
        ▼
execute
        │
        ▼
PostToolUse Hook
        │
        ▼
tool_result
        │
        ▼
Model
```

其中 `PreToolUse` 当前可以检查 `tool_name` 和 `tool_input`，并在 Tool 真正执行之前做出 allow、deny、ask 或 defer 一类决定。官方文档也明确说明，command hook 使用退出码 `2` 可以阻止 `PreToolUse` 对应的 Tool Call，并把 stderr 作为反馈送回 Claude。

例如一个最朴素的 Bash guard：

```bash
#!/bin/bash

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

if echo "$COMMAND" | grep -q "rm -rf"; then
  echo "Blocked: rm -rf is not allowed in this project." >&2
  exit 2
fi

exit 0
```

此时路径变成：

```text
Claude proposes:
rm -rf build/
        │
        ▼
PreToolUse
        │
        ▼
script inspects command
        │
        ▼
exit 2
        │
        ▼
tool call cancelled
        │
        ▼
stderr returned to Claude
```

这里甚至可以看到一个很有意思的反馈环：

```text
模型提出了非法动作
        ↓
Harness 拦截
        ↓
模型得到“为什么被拒绝”
        ↓
模型重新规划
```

所以 Hook 也不是简单粗暴地：

```text
“不让模型知道，直接报错”
```

它可以同时做两件事：

```text
阻止真实副作用
+
给 Agent 可恢复的反馈
```

这就比在 Prompt 里写：

```text
请务必不要这样做
```

多了一条真正的执行边界。

---

不过这里还要再分清一层：

```text
Hook
```

和：

```text
Permission
```

也不是完全一样的东西。

Claude Code 自己有 Permission 系统，用于定义某类 Tool Call 是：

```text
allow
ask
deny
```

例如一些稳定的规则本身就适合直接写成 Permission：

```text
允许 npm test

拒绝读取 secrets/

某些 Bash 命令必须询问
```

Hook 更适合需要**动态检查 Runtime Input** 的情况。

比如不是粗暴地：

```text
deny Bash
```

而是：

```text
Bash 本身允许

但是：

command 中包含 drop table
→ deny

command 是 npm test
→ allow

command 要写 production
→ ask
```

官方权限文档也专门说明了这层关系：`PreToolUse` Hook 可以参与运行时权限判断，但 Hook 并不会绕过已有的 permission rules；deny / ask 规则仍然保持自己的优先级，而 blocking Hook 也可以在 allow rule 之前直接阻止 Tool Call。

所以我现在会把三者分成：

```text
CLAUDE.md / Rules
─────────────────
模型应该知道什么、倾向怎么做


Permissions
─────────────────
某类 capability 是否允许


Hooks
─────────────────
某个 lifecycle event 发生时
自动运行什么检查或动作
```

例如：

```text
“不要删除生产数据库”
```

如果只是写进 `CLAUDE.md`：

```text
instruction
```

如果可以通过稳定的 Tool Rule 表达：

```text
permission deny
```

如果必须根据具体 SQL 内容判断：

```text
PreToolUse Hook
    ↓
inspect tool_input
    ↓
deny / ask / allow
```

这三个层次承担的责任不同。

---

### 5.2 Hook 是 Harness 生命周期上的 Event Handler

理解 Hook 最简单的方法不是先背 JSON 配置。

先看 Claude Code Session 里有哪些“事件”。

一个普通任务大概经历：

```text
Session starts
      │
      ▼
User submits prompt
      │
      ▼
Model reasons
      │
      ▼
Tool requested
      │
      ▼
Tool executes
      │
      ▼
Tool completes
      │
      ▼
Model continues
      │
      ▼
Context gets large
      │
      ▼
Compaction
      │
      ▼
Claude eventually stops
```

如果 Harness 在这些节点暴露 Event：

```text
SessionStart

UserPromptSubmit

PreToolUse

PermissionRequest

PostToolUse

PreCompact

PostCompact

Stop

...
```

那用户就可以把自定义逻辑挂到这些节点上。

这就是 Hook。

Anthropic 当前文档已经提供了相当多的 lifecycle events，而且 Hook 不只可以放在全局 `settings.json`，也可以定义在 Skill 或 Subagent 的 frontmatter 中，让 Hook 的生命周期和那个组件绑定。

可以把它看成：

```text
Claude Code Runtime
────────────────────────────────

SessionStart
    │
    │ hook
    ▼

UserPromptSubmit
    │
    │ hook
    ▼

LLM
    │
    ▼
tool_use
    │
    │ PreToolUse
    ▼
permission
    │
    ▼
execute
    │
    │ PostToolUse
    ▼
tool_result
    │
    ▼
LLM
    │
    ▼
PreCompact
    │
    ▼
compaction
    │
    ▼
PostCompact
    │
    ▼
...
```

这种视角下，很多以前塞在 Prompt 里的东西一下子有了更自然的位置。

比如：

```text
“每次 Session 启动时，
告诉 Claude 当前 git status。”
```

以前可能写：

```markdown
At the beginning of every session,
run git status.
```

现在可以直接：

```text
SessionStart
    ↓
git status
    ↓
stdout → Context
```

官方 Hook 文档说明，`SessionStart` 这类事件可以把 stdout 加入 Claude 的 Context，因此动态状态不一定非要静态写在 `CLAUDE.md`。

这解决的是一个很现实的问题。

`CLAUDE.md` 很适合：

```text
相对稳定的 repository facts
```

但：

```text
当前 branch
当前 dirty files
今天剩余 TODO
当前 environment
```

这些信息会一直变化。

硬写进 `CLAUDE.md` 根本不合理。

用：

```text
SessionStart
```

动态读取，就更自然：

```text
Static Context
─────────────────
CLAUDE.md
“项目使用 pnpm”


Dynamic Context
─────────────────
SessionStart Hook
“当前 branch 是 feat/auth”
“工作区有 3 个 modified files”
```

Steering 开始不再只有：

```text
static prompt files
```

而出现了：

```text
runtime-generated context
```

---

再看编辑后格式化。

```text
PostToolUse
```

发生在 Tool 已经成功完成之后。

所以可以写：

```text
Edit / Write
     │
     ▼
Tool executes
     │
     ▼
PostToolUse
     │
     ▼
prettier
```

这正是 Anthropic 官方反复拿来举例的 Hook 使用方式：Write/Edit 后自动执行 formatter 或 linter，避免这种机械工作继续依赖模型记忆。

比如：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bun run format || true"
          }
        ]
      }
    ]
  }
}
```

这段配置表达的已经不是：

```text
“Claude，编辑完以后记得 format。”
```

而是：

```text
Write|Edit event
        ↓
format
```

模型连“要不要 format”这个 decision 都不必占用一次推理。

---

`PreCompact` 又是另一个很好的例子。

我在 `runtime.md` 里已经把 Compaction 当成了长 Session 必须面对的 Runtime 行为：

```text
Context 越来越长
      ↓
需要压缩历史
      ↓
保留继续完成任务所需的信息
```

现在 Hook 可以插在这个生命周期之前：

```text
Context nearly full
      │
      ▼
PreCompact
      │
      ├── backup transcript
      ├── 保存某些状态
      └── 写外部文件
      │
      ▼
Compaction
```

Anthropic 在 Steering 文章里专门用这个例子说明 Hooks 为什么和 CLAUDE.md / Skills 不一样：如果 `PreCompact` Hook 在压缩前把完整聊天记录备份到文件，Hook 本身可以完成这项工作，而这段配置并不需要一直占据主 Context；除非 Hook 主动把路径返回进去，否则 Claude 甚至不一定知道这个备份文件存在。

这句话一下就把 Hook 的位置说清楚了：

```text
CLAUDE.md / Skill
        │
        ▼
information enters model context


Hook
        │
        ▼
Harness reacts to runtime event
```

有些 Hook 最终会给 Context 增加信息。

但：

```text
“是否进入 Context”
```

只是 Hook 的一种结果。

不是它存在的前提。

---

当前 Hook 也不只一种执行方式。

Anthropic 在 2026 年这篇 Steering 文章里列出的 Hook handler 包括：

```text
command
HTTP
mcp_tool
prompt
agent
```

其中 command、HTTP、MCP Tool 这几类 handler 的执行本身可以是确定的；prompt 和 agent handler 虽然触发时机仍由 Hook event 确定，但 handler 内部会再调用模型，因此输出依旧带有模型判断。

这个细节很值得保留，否则很容易把：

```text
Hooks are deterministic
```

理解成：

```text
Hook 的所有输出都一定 deterministic
```

更准确的说法应该是：

```text
Event 是否触发
        ↓
deterministic


Handler 如何计算结果
        ↓
取决于 hook type
```

例如：

```text
PreToolUse
        │
        ├── command hook
        │       ↓
        │   shell script
        │
        └── agent hook
                ↓
             model call
```

两个 Hook 都会在指定 Event 出现时运行。

但后者内部仍然交给 Agent 判断。

所以如果我要实现：

```text
任何 rm -rf 都绝对阻止
```

我不会优先选一个 agent hook：

```text
“请判断这个命令是否危险。”
```

因为这样又重新引入模型的不确定性。

更直接的是：

```text
PreToolUse
+
command hook
+
明确规则
```

反过来，如果需求是：

```text
提交前检查这次改动
有没有明显遗漏的测试场景
```

这种判断本来就很难写成简单正则，那么：

```text
Stop / agent hook
```

反而可能合适。

所以“Hook”解决的首先是：

```text
什么时候运行
```

至于：

```text
运行什么
```

依然可以是程序，也可以是模型。

---

### 5.3 能让 Runtime 确定执行，就不要让模型每次重新决定

现在回头看 Macro 1 里的那几条：

```markdown
After every edit, ALWAYS run prettier.

NEVER commit secrets.

NEVER run rm -rf.
```

它们看起来都是一句 instruction。

拆到 Harness 以后，可能分别落在完全不同的层：

```text
格式化
──────────────────────
PostToolUse Hook

敏感文件访问
──────────────────────
Permission deny
+
必要时 PreToolUse validation

危险 Bash pattern
──────────────────────
PreToolUse Hook
```

这时 `CLAUDE.md` 反而可以变短。

不是因为这些规则不重要。

而是因为其中一些规则已经被 Runtime 接管了。

例如以前：

```markdown
# CLAUDE.md

IMPORTANT:

- Always run prettier after file edits.
- Never edit generated files.
- Never run rm -rf.
- Never access .env.production.
- Always run lint after editing TypeScript.
- Always save the transcript before compaction.
```

调整以后可能变成：

```markdown
# CLAUDE.md

Generated files under `src/generated/` are not source files.
Do not modify them manually.

The project uses prettier and eslint.
```

而那些确定性动作移到：

```text
Hooks
Permissions
```

里面。

这还有一个额外好处：

```text
Prompt 更短
```

并不是唯一收益。

更重要的是责任边界开始变得可检查。

比如我想知道：

```text
“为什么 formatter 没有运行？”
```

如果它只存在于 Prompt：

```text
需要回看模型为什么没遵守 instruction
```

如果它是 Hook：

```text
检查：

Event fired?
Matcher matched?
Hook launched?
Exit code?
stderr?
```

问题变成可以 debug 的 Runtime 行为。

同样：

```text
“为什么这个危险命令被执行了？”
```

如果答案是：

```text
因为 Claude 忘记遵守 CLAUDE.md
```

这听上去就很难让人放心。

如果答案是：

```text
PreToolUse matcher 没覆盖这个命令 pattern
```

至少我知道应该修哪里。

一个是：

```text
模型 adherence 问题
```

另一个是：

```text
policy implementation bug
```

后者才更像普通软件工程能够处理的问题。

---

这里也能看到为什么 Hook 对 Agent Harness 很有意义。

普通 Chatbot 的主要控制面往往只有：

```text
System Prompt
User Prompt
Tool schema
```

但长时间运行的 Coding Agent 会不断经历：

```text
Session

Tool Use

Permission

File Change

Compaction

Subagent lifecycle

Stop
```

如果这些阶段都没有可插入的控制点，那么每一次“发生 X 后做 Y”都只能写进 Prompt：

```text
如果你编辑了文件，请……

如果你准备执行 Bash，请……

如果 Context 快满了，请……

如果你准备结束，请……
```

最后又会得到一个巨大的：

```text
行为说明书
```

而且每条 instruction 都要依赖模型在正确时机想起来。

Hook 相当于把：

```text
when X happens, do Y
```

里的：

```text
when X happens
```

从模型推理里拿了出来。

变成 Runtime Event。

```text
Prompt 版本

LLM:
“我现在是不是刚编辑完？
我是不是应该运行 formatter？”


Hook 版本

Runtime:
PostToolUse(Edit)
        ↓
formatter
```

这减少的并不只是 Token。

还减少了一次不必要的模型 decision。

如果一个复杂 Agent 一次任务会循环几十、几百个 Tool Call，这种小差别累计起来就很明显。

---

当然，这也不意味着：

```text
能 Hook 的都应该 Hook。
```

如果要求本身带有大量语义判断：

```text
“如果这次代码改动涉及比较敏感的架构决策，
提醒我补 ADR。”
```

硬用 shell script 去判断：

```text
什么叫“敏感的架构决策”
```

可能比让模型判断更糟。

Hook 更适合边界清楚的事件和检查：

```text
Edit 后 format

Bash 前检查 command

SessionStart 注入动态状态

PreCompact 备份数据

Stop 时运行 tests

任务结束后发送通知
```

而：

```text
代码风格是否自然

架构是否合理

是否值得重构

Review 重点在哪里
```

仍然是模型更擅长的判断。

所以判断问题可以变成：

```text
这件事的 trigger 是否明确？

结果是否可以由程序可靠判断？
```

如果都是：

```text
yes
```

就应该认真考虑 Hook / Permission，而不是继续堆 Prompt。

如果：

```text
trigger 明确
但结果需要语义判断
```

可以考虑：

```text
prompt / agent hook
```

如果连 trigger 都是：

```text
“看情况”
```

那它大概本来就更适合保留在 Agent 的 reasoning / Skill 里。

---

到这里，前面几种 Steering 已经可以排列成一条越来越靠近 Runtime 的路径：

```text
CLAUDE.md
    │
    │ repository knowledge
    ▼

Rules
    │
    │ scoped constraints
    ▼

Skills
    │
    │ task procedure
    ▼

Subagents
    │
    │ isolated execution context
    ▼

Hooks
    │
    │ lifecycle automation
    ▼

Permissions
    │
    │ capability authorization
    ▼

Environment
```

这张图并不是说它们有严格的上下级关系。

更像是在问：

```text
一条人类意图
最终应该停在哪一层？
```

例如：

```text
“项目使用 pnpm”
        ↓
CLAUDE.md


“只有 migration 文件要遵守 append-only”
        ↓
Rule


“Release 应该按这 8 步做”
        ↓
Skill


“查十万行日志，但别污染主会话”
        ↓
Subagent


“每次 Edit 后都 format”
        ↓
Hook


“绝不允许访问这个目录”
        ↓
Permission / policy
```

这个划分比把所有东西都写成：

```text
IMPORTANT
ALWAYS
NEVER
```

更接近一个真正可维护的 Agent Harness。

而且它也解释了为什么 Anthropic 把 Hooks 单独放在 Steering 文章里。

它已经不太像传统意义上的 Prompt Engineering 了。

人不只是告诉模型：

```text
“你应该怎么想。”
```

还开始直接规定：

```text
“当 Runtime 走到这里，
系统就执行这段逻辑。”
```

下一章剩下的两种 Steering 会重新回到 Prompt 层，但位置比 `CLAUDE.md` 更高：

```text
Output Style

Append System Prompt
```

它们解决的不是某个仓库、某类文件或者某项 Procedure。

它们改变的是 Claude 在整次 Session 中以什么角色、什么方式说话和工作。

## 6. Output Style 与 System Prompt：什么时候真的要改变 Claude 本身？

### 6.1 Output Style 是更重的 Role Steering

写到这里，前面的几种 Steering 都还有一个共同特点：

```text
CLAUDE.md
→ 告诉 Claude 这个项目是什么样

Rules
→ 告诉 Claude 某类文件有什么额外约束

Skills
→ 告诉 Claude 某类任务应该怎么做

Subagents
→ 把某类任务交给另一个 Context

Hooks
→ Runtime 走到某个节点时自动做什么
```

它们都没有真正回答一个更基础的问题：

```text
“Claude 在这次 Session 里，
到底应该以什么方式和我工作？”
```

比如我可能不想让 Claude Code 默认表现成：

```text
收到任务
→ 尽快定位
→ 修改代码
→ 验证
→ 汇报
```

而是希望它变成：

```text
收到任务
→ 先解释当前代码为什么这样写
→ 每一步都把设计权衡讲出来
→ 再让我自己决定要不要修改
```

或者：

```text
不要把我当成只想拿到 Patch 的用户。

把这次 Session 当成教学：
每次修改之前解释涉及的语言机制，
修改之后再解释 diff。
```

这类要求当然也能写进：

```text
CLAUDE.md
```

例如：

```markdown
# CLAUDE.md

Always explain every code change in detail.

Teach me the underlying concept before editing.

Prefer educational explanations over terse answers.
```

能工作。

但仔细看，它根本不是这个 repository 的知识。

换到另一个项目，我大概率还想这样。

而且它影响的不是：

```text
某个目录
某种文件
某个任务
```

而是：

```text
几乎每一次 response。
```

Claude Code 为这种需求提供了 Output Style。

当前官方文档对它的描述很准确：

> Output styles change how Claude responds, not what Claude knows.

也就是说，它改变的是 Claude 的：

```text
role
tone
default response format
```

而不是给它增加某个 codebase 的知识。

这和 `CLAUDE.md` 的位置其实差得挺远。

官方现在甚至直接把二者放在表格里对比：

```text
Output Style
→ modifies the system prompt

CLAUDE.md
→ adds project context after the system prompt
```

所以前面我一直把 `CLAUDE.md` 叫作：

```text
repository context
```

而不是简单说它也是一种 system prompt。

从当前 Claude Code 的实现语义来看，这个区分是成立的。

可以画成：

```text
                Claude Code Request
                       │
                       ▼
              ┌─────────────────┐
              │  System Prompt  │
              │                 │
              │ identity        │
              │ behavior        │
              │ response style  │
              └────────┬────────┘
                       │
             Output Style 修改这里
                       │
                       ▼
              ┌─────────────────┐
              │ Project Context │
              │                 │
              │ CLAUDE.md       │
              │ Rules           │
              │ Skill body ...  │
              └────────┬────────┘
                       │
                       ▼
                     Model
```

这个图不是 Claude Code 完整 Prompt Assembly 的源码图。

我这里只用它表达一个 Steering 层级：

```text
Output Style
比 repository instruction
更靠近 Agent 的全局行为定义。
```

这也是为什么它的影响会更大。

---

Claude Code 当前内置了几种常见 Output Style，例如：

```text
Proactive
Explanatory
Learning
```

Anthropic 在 Steering 文章里也建议：在自己维护 custom style 之前，先看看这些内置模式是不是已经覆盖需求。

比如我想学一段陌生代码。

与其反复说：

```text
解释详细一点。

这里为什么？

这行背后的机制是什么？

先别急着改。
```

更合理的需求其实是：

```text
这整个 Session
都采用更偏解释 / 教学的响应方式。
```

那就已经很接近 Output Style 的适用范围。

反过来，如果我的要求只是：

```text
这个 repository 使用 pytest，
测试目录在 tests/
```

把它做成 Output Style 就很奇怪。

因为我实际上是在修改：

```text
“Claude 是怎样的 assistant”
```

来保存：

```text
“这个项目有什么事实”
```

作用域完全错了。

---

Custom Output Style 本身仍然是 Markdown 文件。

例如：

```text
.claude/
└── output-styles/
    └── tutor.md
```

可以写成类似：

```markdown
---
name: Tutor
description: Explain code changes as a teacher while preserving coding assistance.
keep-coding-instructions: true
---

Explain the relevant concept before making non-trivial changes.

When presenting a diff, explain:
- what changed;
- why it changed;
- what alternative was rejected;
- how to verify it.
```

这里最需要注意的其实不是这些自然语言 instructions。

而是：

```yaml
keep-coding-instructions: true
```

为什么会有这么一个选项？

因为 Custom Output Style 默认不是像 `CLAUDE.md` 那样：

```text
“再补几条项目要求”
```

它会修改 Claude Code 的 system prompt 行为。

Anthropic 在这篇 Steering 文章里专门提醒：默认情况下，一个自定义 Output Style 会替换 Claude Code 原来的 coding-oriented style instructions；如果没有保留 coding instructions，Claude 可能不再按照原本的软件工程 assistant 方式工作。官方举出的被影响内容包括：

```text
怎么控制 change scope

什么时候应该写 code comment

遇到 security concerns 怎么处理

什么时候应该跑 tests 再宣布完成
```

如果希望保留这些默认 coding 行为，就需要显式使用：

```yaml
keep-coding-instructions: true
```

。

这个细节让我觉得 Output Style 不应该被当成：

```text
“高级版 CLAUDE.md”
```

因为它不是“instruction 更多”。

它动的是另一层。

可以做一个很夸张的对比：

```text
CLAUDE.md
────────────────────────

Claude 还是 Claude Code。

只是知道：
这个项目用 pnpm、
目录怎么组织、
有哪些项目规范。


Output Style
────────────────────────

我开始改：
Claude Code 应该以什么角色工作，
怎么组织回答，
默认关注什么，
甚至是否继续保留原本
software-engineering-oriented instructions。
```

前者比较像：

```text
给员工一份项目手册。
```

后者更像：

```text
重新定义这个岗位的工作方式。
```

当然这个比喻也不能往实现细节上硬套。

但拿来判断配置该放哪儿很方便。

---

再回头看一组需求：

```text
所有回答使用中文。
```

这个有点微妙。

如果只是我个人希望 Claude Code 一直用中文：

```text
user-level Output Style
```

就很合理。

如果是：

```text
这个开源仓库的贡献规范要求
所有生成的 issue summary 都使用英文。
```

那可能更像 repository instruction 或对应的 Skill。

再比如：

```text
回答尽量短。
```

这不是 codebase fact。

```text
像导师一样解释原因。
```

也不是。

```text
每个结论都按：
Evidence → Interpretation → Limitation
输出。
```

如果我希望整个 Session 每一轮都这么说，那也明显更接近 Output Style。

所以我会用一个很直接的问题来判断：

```text
假如我换到另一个 repository，
这条要求还成立吗？
```

如果答案是：

```text
no
```

优先考虑：

```text
CLAUDE.md
Rules
Skills
```

如果答案是：

```text
yes，而且几乎每一轮都成立
```

才开始考虑：

```text
Output Style
```

---

Output Style 还有两个 Context 行为值得记住。

第一，它在 Session 开始时加载。

第二，它位于 system prompt，因此不会随着 conversation compaction 被压掉。

Anthropic 的 Steering 文章也正因为这一点，把它看作比前面多数方式拥有更高 instruction-following weight 的 Steering 手段，并提醒谨慎使用。

也就是说：

```text
Session Start
      │
      ▼
Output Style
      │
      ▼
System Prompt
      │
      ├──── turn 1
      ├──── turn 2
      ├──── ...
      │
      ▼
Compaction
      │
      ▼
Output Style 仍然属于 System Prompt
```

所以拿它保存：

```text
“只有修改 SQL 时才需要遵守的规则”
```

不只是语义位置错。

Context 生命周期也太重了。

这类信息明明可以：

```text
path match
→ 才加载
```

却被提升成：

```text
整个 Session 的 system-level behavior。
```

这又回到了整篇文章从 Macro 1 就在问的问题：

```text
一条 instruction
到底值得住在哪一层？
```

---

不过现在会碰到另一个很实际的情况。

有时候我并不想：

```text
创建一个 style 文件
↓
保存
↓
以后每个 Session 复用
```

我只是今天这一次执行想加一句：

```text
“输出必须是 JSON。”
```

或者：

```text
“这次只给我 unified diff。”
```

再或者我正在写脚本：

```bash
claude -p "Analyze these files"
```

希望这一次调用额外遵守某个 domain constraint。

为了这种一次性的要求专门创建 Output Style，又有点重。

于是最后还剩一个更轻的入口：

```text
--append-system-prompt
```

---

### 6.2 `--append-system-prompt` 为什么更适合一次性全局偏好？

Claude Code 当前 CLI 支持：

```bash
claude \
  --append-system-prompt "Always use TypeScript"
```

也支持从文件追加：

```bash
claude \
  --append-system-prompt-file ./extra-rules.txt
```

关键字是：

```text
append
```

不是：

```text
replace
```

当前 CLI 文档把 system prompt 相关入口分得很清楚：

```text
--system-prompt
→ 替换完整默认 prompt

--system-prompt-file
→ 用文件替换完整默认 prompt

--append-system-prompt
→ 在默认 prompt 后追加

--append-system-prompt-file
→ 从文件追加
```

。

对于 Steering 这篇笔记，真正需要掌握的是第三种。

例如：

```bash
claude \
  --append-system-prompt \
  "Respond with a concise JSON object containing summary, risk, and recommendation."
```

执行路径大致可以理解成：

```text
Claude Code default system prompt
              │
              │ preserve
              ▼
┌────────────────────────────────┐
│ Default Claude Code behavior   │
│                                │
│ coding role                    │
│ verification habits            │
│ built-in behavior              │
└──────────────┬─────────────────┘
               │
               │ append
               ▼
┌────────────────────────────────┐
│ My invocation-only instruction │
│                                │
│ output JSON with:              │
│ summary / risk / recommendation│
└────────────────────────────────┘
```

这和前面的 custom Output Style 有一个很实用的区别。

Output Style 可以更深地改变：

```text
Claude 应该以什么 role / style 工作
```

而 append 更适合：

```text
保留原来的 Claude Code，
但这一次额外遵守几条要求。
```

Anthropic 原文就是这么区分的：Output Style 可能对原有 behavior 产生比较大的改变，而 append 是 additive 的，不需要替换 Claude Code 原来的角色。

所以如果我只是想：

```text
“这一次所有回答都使用中文”
```

可以：

```bash
claude \
  --append-system-prompt \
  "Respond in Chinese for this session."
```

如果我是在 CI 里跑：

```bash
claude -p ...
```

要求机器消费：

```text
只输出 JSON，
不要 Markdown fence。
```

也很适合 append。

比如：

```bash
claude -p "Review the current diff" \
  --append-system-prompt \
  "Return valid JSON only with fields: severity, file, line, message."
```

这类要求同时满足两个特点：

```text
对当前 invocation 的所有响应都有效

但我并不希望永久改变其他 Session
```

这正好处在：

```text
system-level
+
session/invocation-scoped
```

这个位置。

---

把 `CLAUDE.md`、Output Style 和 append 放在一起更容易看清：

| 需求                     | 更自然的位置                   |
| ---------------------- | ------------------------ |
| 这个项目用 `pnpm`           | `CLAUDE.md`              |
| migration 只能追加         | path-scoped Rule         |
| Release 要走固定 Procedure | Skill                    |
| 这个 Side Task 单独调查      | Subagent                 |
| Edit 后必须 format        | Hook                     |
| Claude 每一轮都像导师一样解释     | Output Style             |
| 这一次调用只输出 JSON          | `--append-system-prompt` |

也可以换成生命周期：

```text
Repository lifetime
────────────────────────────
CLAUDE.md
Rules
Skills


Reusable role/style
────────────────────────────
Output Style


Single invocation/session
────────────────────────────
--append-system-prompt
```

这个图依然只是为了方便理解，并不是说 Skills 绝对只能属于 Repository。

真正要抓的是：

```text
instruction 的 persistence
和它的实际需求要匹配。
```

---

append 还有一个很容易诱惑人的地方。

既然它位于 system prompt，而且比普通项目 instruction 更高，我完全可以写：

```bash
claude \
  --append-system-prompt "
You MUST always do A.
You MUST always do B.
You MUST never do C.
Before X do D.
After X do E.
When Y do F.
...
"
```

然后又重新造出：

```text
CLAUDE.md 超级大杂烩
```

只不过这次换到了 system prompt。

Anthropic 对此也专门提醒：append system prompt 越堆越多，会出现 adherence 的 diminishing returns；instructions 越多，尤其互相矛盾时，模型并不会因为它们都放在 system prompt 就无限稳定。

这和 Macro 2 其实是同一个问题的更高层版本。

假设追加：

```text
A
B
C
D
E
F
G
H
...
```

不能推导出：

```text
instruction-following reliability
单调增加
```

反而可能变成：

```text
更多 instruction
      ↓
更多竞争
更多例外
更多冲突
      ↓
模型还是得判断
当前到底哪条最相关
```

所以 system prompt 不是“垃圾桶的最高权限版本”。

---

这里还能顺便解释为什么：

```text
“NEVER run git push --force”
```

即使 append 到 system prompt，也不意味着可以替代 Macro 5 的 Permission / Hook。

比如：

```bash
claude \
  --append-system-prompt \
  "NEVER run git push --force."
```

它的路径依然是：

```text
system instruction
      ↓
model sees it
      ↓
model hopefully obeys
```

而：

```text
Permission / PreToolUse
```

是：

```text
tool call actually appears
      ↓
runtime evaluates
      ↓
deny
```

instruction authority 更高，不等于：

```text
deterministic enforcement
```

这两个维度不能混。

我会把它们画成两根轴：

```text
              Instruction Authority
                       ▲
                       │
            System Prompt / Style
                       │
                 CLAUDE.md
                       │
                     Skill
                       │
                       └──────────────?
                         Runtime Enforcement

                              Hook
                               │
                          Permission
```

这张图不是在给它们排一个官方“强弱榜”。

只是为了提醒自己：

```text
Prompt 权重
```

和：

```text
Runtime 是否真的卡住动作
```

根本不是同一个问题。

---

还有一个成本问题。

把内容追加进 system prompt，会增加输入 Token；同一 Session 内 prompt caching 能降低后续重复成本，但第一次请求还是需要把这些内容放进去。如果 append 本身又要求 Claude：

```text
每次详细解释

每次给五种方案

每次附完整推导
```

那还会进一步增加 output tokens。Anthropic 在 Steering 文章和 Output Style 文档里都明确提醒了这一点。

所以：

```text
--append-system-prompt
```

虽然调用起来很方便：

```bash
一条 flag 就行
```

但这不意味着它应该承载：

```text
三百行长期工作流
```

那类东西还是应该回到：

```text
Skill
```

按需加载。

---

到这里，Anthropic 这篇文章里的七种 Steering 手段已经全部走过一次。

可以先不急着背最终决策树。

把 Macro 1 那份最开始的大杂烩重新拿回来：

```markdown
使用 pnpm，不要使用 npm。

项目采用 monorepo。

修改代码后运行 prettier。

Review 时先检查安全问题。

发布前执行一套 8 步流程。

不要执行 git push --force。

分析大型日志时不要污染主会话。

所有回答使用中文。
```

现在已经可以逐条搬家：

```text
使用 pnpm
        ↓
CLAUDE.md


monorepo layout
        ↓
CLAUDE.md


某类文件的额外规范
        ↓
Rule


Code Review Procedure
        ↓
Skill


Release Procedure
        ↓
Skill


大型日志调查
        ↓
Subagent


Edit 后运行 prettier
        ↓
PostToolUse Hook


禁止危险 capability
        ↓
Permission / PreToolUse


整个 Session 都使用某种角色/风格
        ↓
Output Style


仅本次调用增加全局格式要求
        ↓
--append-system-prompt
```

所以最终的问题已经不再是：

```text
“CLAUDE.md 应该怎么写得更厉害？”
```

而变成：

```text
“这条意图究竟应该由
Context、
Procedure、
Agent Boundary、
Lifecycle，
还是 Runtime Policy
来承载？”
```

下一节就可以把这些判断真正收束成一棵 Decision Tree。

不是再介绍第八种机制。

而是面对一条新的 instruction 时，从哪里开始问，最后把它放到正确的位置。

## 7. 把 Instruction 放对地方

### 7.1 一张 Steering Decision Tree

写到这里，我已经不太想继续按：

```text
CLAUDE.md 是什么？

Rules 是什么？

Skills 是什么？

Subagents 是什么？
```

这样背了。

真正碰到项目配置时，我手上往往只有一句很普通的需求：

```text
“以后 Claude 要记住这个。”
```

麻烦就在“这个”到底是什么。

比如：

```text
以后记得用 pnpm。

以后修改 migration 时别改旧文件。

以后做 release 按这套流程走。

以后分析大日志不要污染主会话。

以后每次 Edit 都跑 formatter。

以后永远不要执行 git push --force。

以后回答都详细解释原因。
```

如果没有分类意识，最简单的做法当然是：

```text
全部写进 CLAUDE.md。
```

这也是这篇笔记最开始的状态。

Anthropic 现在给出的七种 Steering 方法，本质上就在逼我多问几步：Instruction 什么时候进入 Context、长 Session 里怎样保留、Context 成本多大，以及它拥有多大的控制力。

所以我最后更愿意从下面这棵树开始。

```text
有一条新的 Steering 需求
          │
          ▼
它是不是必须确定发生 / 确定禁止？
          │
      ┌───┴───┐
     yes      no
      │        │
      ▼        ▼
它是在控制     它描述的是
某个 Runtime   “Claude 应该知道/怎么做”？
事件或能力？           │
      │                ▼
      │         是否只在某个
      │         Task 才需要？
      │              │
      │         ┌────┴────┐
      │        yes        no
      │         │          │
      │         ▼          ▼
      │      Procedure?   是否只对
      │         │         特定文件/
      │     ┌───┴───┐     目录生效？
      │    yes      no       │
      │     │        │    ┌──┴──┐
      │     ▼        │   yes    no
      │   Skill      │    │      │
      │              │    ▼      ▼
      │              │  Rule /  Root
      │              │  Nested   CLAUDE.md
      │              │  CLAUDE.md
      │              │
      │              ▼
      │      中间过程是否应该
      │       留在 Main Context？
      │          ┌───┴───┐
      │         yes      no
      │          │        │
      │          ▼        ▼
      │        Skill   Subagent
      │
      ▼
事件自动化？
  │
  ├── yes → Hook
  │
  └── capability authorization
             ↓
         Permission
```

这棵树还没有处理：

```text
Claude 整体应该以什么角色工作？
```

因为它属于另一个入口：

```text
这条要求是否几乎影响整个 Session？
             │
        ┌────┴────┐
       yes        no
        │
        ▼
它是否是可复用的
Role / Response Style？
        │
   ┌────┴────┐
  yes        no，只是本次调用
   │             │
   ▼             ▼
Output Style   append-system-prompt
```

把两部分合起来，就得到我现在真正会用的版本。

```text
                      New Steering Requirement
                                │
                                ▼
                   ┌────────────────────────┐
                   │ 必须确定执行 / 禁止吗？ │
                   └───────────┬────────────┘
                         yes   │   no
                 ┌─────────────┘
                 ▼
       ┌────────────────────┐
       │ Runtime 能直接管吗？│
       └─────────┬──────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
 Lifecycle Event        Authorization
        │                  │
        ▼                  ▼
      Hook             Permission


否则继续问：
                                │
                                ▼
                    ┌────────────────────┐
                    │ 是全局 Role/Style 吗？│
                    └─────────┬──────────┘
                              │
                     ┌────────┴─────────┐
                    yes                 no
                     │                   │
                     ▼                   ▼
             reusable across        本次调用临时要求？
                sessions                  │
               │      │                   ▼
              yes     no         append-system-prompt
               │
               ▼
          Output Style


普通 Instruction：
                                │
                                ▼
                       是 Procedure 吗？
                          │          │
                         yes        no
                          │          │
                          ▼          ▼
                   是否应该留在     是否只对局部
                  Main Context？    文件/目录生效？
                    │      │          │       │
                   yes     no        yes      no
                    │       │         │        │
                    ▼       ▼         ▼        ▼
                  Skill  Subagent   Rule /    root
                                  nested     CLAUDE.md
                                  CLAUDE.md
```

这不是 Anthropic 官方画出来的 taxonomy。

官方给的是七种机制的加载时机、compaction 行为、Context cost 和适用场景；上面这棵树是我为了实际配置 Claude Code，把那些信息重新排成了一个“遇到需求时从哪里开始问”的顺序。

这里有几个分叉尤其容易选错。

---

#### 第一问不要先问“写在哪个文件”，先问“这是不是应该让模型决定？”

比如：

```text
修改文件后运行 prettier。
```

如果从文件组织出发，很容易想：

```text
这是一条项目约定
→ CLAUDE.md
```

但真正先问的是：

```text
这件事是否允许偶尔忘掉？
```

答案如果是：

```text
不允许。
```

那就已经没必要继续纠结：

```text
CLAUDE.md
还是 Rule？
```

应该直接转向 Runtime：

```text
PostToolUse(Edit)
        ↓
formatter
```

Anthropic 也把这类 `"Every time X, always do Y"` 明确列为应该考虑 Hook 的反例：模型“决定运行 formatter”和 Runtime “自动运行 formatter”是两件事。

同理：

```text
绝不能执行某种危险动作。
```

也不应该先想：

```text
怎么把 NEVER 写得更醒目？
```

官方建议直接考虑 Hooks、Permissions；组织级不可被用户覆盖的强约束则进一步放到 managed settings。

所以第一刀其实是：

```text
Model Choice
vs
Runtime Guarantee
```

只要这一刀切错，后面 Prompt 写得再漂亮也只是提高遵循概率。

---

#### 第二问：它到底是 Fact、Constraint，还是 Procedure？

看三个例子：

```text
使用 pnpm。
```

```text
修改 migration 时不能回改已应用文件。
```

```text
发布时依次执行 lint、test、build、changelog、tag。
```

它们都可以写成 Markdown。

但信息结构完全不同。

第一条：

```text
repository fact
```

第二条：

```text
scoped constraint
```

第三条：

```text
procedure
```

所以：

```text
pnpm
→ root CLAUDE.md
```

```text
migration append-only
→ path-scoped Rule
```

```text
release checklist
→ Skill
```

Anthropic 的反例甚至直接用了“30 行 Procedure 写在 `CLAUDE.md`”这个场景：deployment runbook、security review checklist 这类 Procedure 应该进入 Skill，由需要时动态加载。

我现在判断 Procedure 时会看有没有这种结构：

```text
Step 1
  ↓
check
  ↓
if ...
  ↓
Step 2
  ↓
verify
  ↓
report
```

一旦 instruction 开始描述：

```text
状态转换
顺序
条件分支
验证
最终产物
```

它通常已经不像一个应该常驻的项目事实了。

---

#### 第三问：局部到底是“目录局部”还是“语义局部”？

假设：

```text
apps/web/
```

整个目录都有自己的：

```text
Vitest

React Router

packages/ui

frontend conventions
```

很自然：

```text
apps/web/CLAUDE.md
```

但：

```text
migration append-only
```

可能同时出现在：

```text
apps/api/migrations/**
packages/db/migrations/**
tests/migrations/**
```

这里不是某一个目录拥有规则。

而是某种文件拥有规则。

所以更合适：

```yaml
---
paths:
  - "**/migrations/**"
---
```

也就是 path-scoped Rule。

Anthropic 当前也专门建议：cross-cutting concern 或散布在多个目录中的某类文件，更适合 path-scoped Rule，而不是为了目录结构重复 nested `CLAUDE.md`。

可以记成：

```text
Directory locality
        ↓
nested CLAUDE.md


Semantic / path locality
        ↓
Rule
```

---

#### 第四问：Procedure 是不是就一定 Skill？

也不是。

假设有一项工作：

```text
搜索 50 个文件
读取大量日志
反复 grep
最后告诉我最可能的 root cause
```

它当然需要 Procedure。

但如果直接在 Main Context 展开：

```text
grep result
grep result
grep result
error
retry
stack trace
candidate
rejected candidate
...
```

这些信息会留在父 Session。

而我真正需要带回来的只有：

```text
root cause
evidence
confidence
```

这时选择就不是：

```text
有没有 Procedure？
```

而要再多问一层：

```text
Procedure 的 working state
父 Agent 后面还需要吗？
```

Anthropic 官方给的 Skill / Subagent 判断也几乎就是这一点：希望在主线程看见、Steer 每一步，用 Skill；Side Task 会制造大量以后不会再引用的中间信息，则用 Subagent，把最后消息和 metadata 带回来。

所以：

```text
Procedure
   │
   ▼
需要 Main Thread 的连续可见性？
   │
 ┌─┴─┐
yes  no
 │    │
 ▼    ▼
Skill Subagent
```

这比：

```text
小任务用 Skill
大任务用 Subagent
```

准确得多。

任务大小不是决定因素。

**Context ownership 才是。**

---

#### 第五问：Role Steering 不应该污染 Repository Steering

比如：

```text
请始终用中文。

回答时多解释底层原理。

把我当成学习者，而不是只输出 Patch。
```

如果这些要求跟项目无关，我以前可能也顺手写：

```text
CLAUDE.md
```

但这样团队成员 clone 仓库以后：

```text
我个人的对话偏好
```

变成了：

```text
repository policy
```

显然不太对。

Anthropic 也专门提醒：个人偏好不要随便写到 project-level `CLAUDE.md`，文件类 Steering 机制都有对应的 user-level 使用方式。

如果要求进一步影响 Claude 整体的角色和输出行为：

```text
教学型 assistant

解释型 coding assistant

更主动的 autonomous agent
```

就更接近 Output Style。

如果只是今天这一条命令临时需要：

```text
只输出 JSON。
```

用：

```text
--append-system-prompt
```

就够了。

官方当前的区别也很明确：Output Style 会进入 system prompt 并可能重塑默认角色；append 则是 additive、invocation-scoped，不会持久化成跨 Session 的配置。

---

把这些判断压缩以后，我自己最后会留一张表。

| 我真正想表达的东西                           | 优先考虑                     |
| ----------------------------------- | ------------------------ |
| 整个项目长期成立的事实                         | Root `CLAUDE.md`         |
| 某个子目录自己的惯例                          | Nested `CLAUDE.md`       |
| 针对某类路径/文件的约束                        | Path-scoped Rule         |
| 一种可复用工作流程                           | Skill                    |
| Side Task 的中间过程不值得进入主 Context       | Subagent                 |
| X 事件发生后必须执行 Y                       | Hook                     |
| 某类 Capability 必须允许 / 询问 / 禁止        | Permission               |
| 长期改变 Claude 的 Role / Response Style | Output Style             |
| 仅当前 invocation 增加全局要求               | `--append-system-prompt` |

这里比 Anthropic 官方“七种方法”多了一行 Permission。

原因不是我把 Permission 擅自算成第八种 Steering 方法。

官方这篇文章列举的是七种“delivering instructions”的机制；但它自己在讨论 `"Never do this"` 时又明确把 Permissions 与 Hooks 当成 deterministic enforcement 手段。

所以在我的 Decision Tree 里，Permission 必须出现。

否则：

```text
“禁止某种能力”
```

只能被错误地硬塞进七种 Prompt / Context 机制之一。

---

### 7.2 从 Prompt Engineering 到 Harness Steering

如果只看文件形式，这篇文章其实很容易被理解成：

```text
Claude Code 新增了好多种 Prompt 文件。
```

毕竟：

```text
CLAUDE.md
Rule
SKILL.md
Agent markdown
Output Style
```

看起来到处都是 Markdown。

但一路拆下来以后，我觉得更有用的理解刚好相反。

Claude Code 并不是简单地给：

```text
prompt.txt
```

增加了几个不同后缀。

它把“人怎样控制一个 Coding Agent”拆到了不同的 Runtime 边界。

我为了学习，最后把它整理成下面这组对应关系：

```text
CLAUDE.md
→ Context Residency


Rules
→ Conditional Context Injection


Skills
→ Progressive Disclosure / Procedure


Subagents
→ Context Isolation & Delegation


Hooks
→ Lifecycle Control


Permissions
→ Authorization


Output Style / System Prompt
→ Global Role & Prompt Steering
```

先强调一次：

> **这一组英文名是我为了理解 Claude Code Harness 自己做的抽象，不是 Anthropic 官方给这七种功能重新命名。**

官方真正明确说的是：这些方法在 instruction 加载时间、compaction 行为、Context cost 和 authority 上不同。

我的抽象只是把这些产品行为重新放回 Agent Harness 的几个常见工程问题里。

---

先看最原始的 Prompt Engineering。

一个很朴素的 Agent 可能就是：

```python
system_prompt = """
You are a coding agent.

Use pnpm.

Never edit migrations.

After every edit run prettier.

When reviewing code:
1. check security
2. check correctness
3. check tests

When analyzing logs...
When releasing...
Never run...
Always...
"""
```

然后：

```text
System Prompt
      │
      ▼
LLM
      │
      ▼
Tool
      │
      ▼
Environment
```

所有控制都从同一个入口进来。

这套东西当然能跑。

很多 ReAct demo 就是这么开始的。

但随着任务变长，很快会出现几个问题。

第一：

```text
所有 instruction 都一直占 Context。
```

第二：

```text
模型需要自己判断
哪条 instruction 当前 relevant。
```

第三：

```text
“必须执行”
和
“建议执行”
最终都只是一段自然语言。
```

第四：

```text
所有 Side Task 的 working state
都堆在同一个 Context。
```

第五：

```text
动态状态、生命周期事件、
权限控制
没有独立接口。
```

于是 Prompt 越写越大。

```text
                    giant system prompt

repo facts
frontend rules
backend rules
release workflow
review workflow
security policy
formatter reminder
log-analysis guide
response style
...
        │
        ▼
      Model
```

Claude Code 的 Steering 机制其实是在把这团东西重新拆出去。

---

第一步：

```text
长期项目知识
```

留下：

```text
CLAUDE.md
```

于是：

```text
System / Session
     │
     ├── repository invariants
     └── project overview
```

---

第二步：

只有局部代码需要的信息：

```text
if path matches
        ↓
inject Rule
```

不用再：

```text
每个 Session 都背所有团队规范。
```

---

第三步：

Procedure：

```text
release
review
deploy
research
```

不再常驻。

变成：

```text
descriptor
   │
   ▼
task matches
   │
   ▼
load Skill body
```

Context 开始拥有：

```text
按任务展开
```

的能力。

---

第四步：

有些 Procedure 会制造很多 temporary state。

于是：

```text
Main Context
```

也不再是整个 Agent System 唯一的工作记忆空间。

```text
Parent Context
      │
      ├─────? Subagent Context A
      │
      ├─────? Subagent Context B
      │
      └─────? Subagent Context C
```

每个 Side Task 可以自己搜索、试错、压缩。

父 Agent 只收需要继续决策的信息。

---

第五步：

一些 instruction 根本不需要进入模型。

```text
Edit 后 format

PreCompact 前 backup

禁止某个 Bash pattern
```

于是 Harness 直接暴露：

```text
Lifecycle Event
      │
      ▼
Hook
```

“什么时候执行”从：

```text
模型是否想起来
```

变成：

```text
Runtime event 是否发生。
```

---

第六步：

再把：

```text
Claude 有没有资格执行这个动作？
```

从自然语言里剥出来。

```text
Model proposes action
        │
        ▼
Authorization
        │
  ┌─────┼─────┐
 allow  ask   deny
        │
        ▼
    execution
```

到了这里，Prompt 已经不需要承担所有 Security Policy。

---

最后才是：

```text
Claude 整体应该怎么表现？
```

留给：

```text
Output Style
System Prompt
```

也就是说，越往后看，我越觉得 Steering 的演化并不是：

```text
Prompt Engineering
        ↓
写更复杂的 Prompt
```

而更接近：

```text
Prompt Engineering
        ↓
Context Engineering
        ↓
Runtime / Harness Engineering
```

但这里也不要把它理解成：

```text
Prompt Engineering 已经过时。
```

Claude Code 里仍然大量使用自然语言 instructions。

`CLAUDE.md` 是。

Rules 是。

Skills 是。

Subagent system prompt 也是。

Output Style 更是。

变化只是：

> **不再要求一个 Prompt 同时承担知识存储、作用域、Procedure、隔离、事件触发和授权。**

这些责任被 Harness 拆开以后，自然语言 Prompt 反而可以只负责它真正擅长的部分。

---

这也能把我这一个目录下面几篇笔记串起来。

前面的：

```text
runtime.md
```

问的是：

```text
一次 Agent Session
怎样跨很多轮继续运行？
```

所以我去看：

```text
QueryEngine.submitMessage()

query()

queryLoop()

context

compaction
```

---

`tools.md` 问的是：

```text
模型提出真实动作以后，
Harness 怎么把它变成一次安全执行？
```

所以关注：

```text
Schema

Validation

Permission

Concurrency

Execution

Tool Result
```

---

`subagents.md` 问的是：

```text
什么时候启动另一个 Agent Runtime？

它有什么 Model、Tool、
Isolation 和 Lifecycle？
```

所以去看：

```text
AgentTool

subagent_type

model

run_in_background

worktree
```

---

而这一篇 `steering.md` 真正补上的问题是：

```text
既然 Runtime、Tools、Subagents
这些执行结构已经存在，

人到底从哪里
把自己的意图插进去？
```

答案已经不是只有：

```text
System Prompt
```

而是：

```text
                      Human Intent
                           │
                           ▼
                 ┌──────────────────┐
                 │ Steering Surface │
                 └─────────┬────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
    Context             Execution            Runtime
       │                   │                   │
 CLAUDE.md              Skills               Hooks
 Rules                 Subagents          Permissions
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                      Agent Runtime
                           │
                           ▼
                         Tools
                           │
                           ▼
                      Environment
```

这里的 `Context / Execution / Runtime` 还是我的理解框架。

它不是 Claude Code 源码里真的有三个叫：

```text
ContextSteeringManager

ExecutionSteeringManager

RuntimeSteeringManager
```

的模块。

但这个抽象能帮我避免以后看到新 Agent 产品时，只检查：

```text
“它有没有 CLAUDE.md？”
```

更值得检查的是：

```text
它怎样管理 persistent instructions？

有没有 scoped context？

Procedure 怎么按需发现？

Side Task 有没有 Context Isolation？

Lifecycle 有没有 event surface？

Authorization 放在哪？

哪些行为仍然只能依赖模型 adherence？
```

这组问题已经不局限于 Claude Code 了。

---

比如以后我自己写一个很小的 Coding Agent。

最开始可能真的只有：

```python
while True:
    response = llm(messages, tools=tools)

    if response.tool_call:
        result = execute(response.tool_call)
        messages.append(result)
    else:
        break
```

如果想继续往生产级走，我现在会自然问：

```text
项目级 instruction 怎么进来？

所有 instruction 都要常驻吗？

能不能按 path 加载？

Procedure 要不要按 task 加载？

什么时候应该开新的 Context？

Tool 前后能不能插 Hook？

Dangerous Action 谁来 authorize？

Context 太长怎么办？

哪些 state 应该存在 Context 外？
```

这时候 Claude Code 的这些功能才真正从：

```text
产品使用技巧
```

变成：

```text
Harness Design 的案例。
```

这也是为什么我把这篇笔记放在：

```text
docs/harness/claudecode/
```

而不是仅仅记：

```text
Claude Code 配置文件大全。
```

---

最后再回头看 Anthropic 官方那三个维度：

```text
When does it load?

Does it survive compaction?

How much authority does it have?
```

我自己会再补两个问题：

```text
它会占据哪个 Context？

这个行为最终由 Model 决定，
还是由 Harness 决定？
```

于是任何新的 Steering 需求，我都可以拿五个问题过一遍：

```text
1. 什么时候需要它？

2. 它应该活多久？

3. 谁需要看见它？

4. 它是知识、Procedure，
   还是 Runtime Policy？

5. 最终允许模型自己决定吗？
```

比如：

```text
“Edit 后跑 prettier”
```

答案是：

```text
什么时候？
→ Edit 后

活多久？
→ 不需要进入 Session Memory

谁看见？
→ Harness 就够了

是什么？
→ Runtime automation

模型决定？
→ 不需要

因此：
→ Hook
```

再比如：

```text
“Release 按 12 步操作”
```

```text
什么时候？
→ Release Task

活多久？
→ Task 期间

谁看见？
→ 执行 Release 的 Agent

是什么？
→ Procedure

模型决定？
→ Procedure 内仍需要 reasoning

因此：
→ Skill
```

再比如：

```text
“调查十万行日志，
最后只汇报 root cause”
```

```text
什么时候？
→ Debug Side Task

活多久？
→ Side Task 期间

谁看见？
→ 调查 Agent

是什么？
→ Procedure + disposable working context

Main Agent 需要过程？
→ 不需要

因此：
→ Subagent
```

再比如：

```text
“绝不能读取 production secrets”
```

```text
什么时候？
→ Tool 尝试发生时

活多久？
→ 不需要进 Context

谁看见？
→ Runtime authorization layer

是什么？
→ Guardrail

模型决定？
→ 不允许

因此：
→ Permission / deterministic policy
```

到这里，Macro 1 里那份：

```text
CLAUDE.md 大杂烩
```

终于拆完了。

不是因为 `CLAUDE.md` 不好用。

正相反，它承担：

```text
长期、广泛、稳定的 repository context
```

时很好用。

问题只是不能因为它是最容易编辑的一块 Markdown，就让它顺便负责：

```text
Procedure

Delegation

Automation

Security

Role

Authorization
```

这些工作。

真正让我改变理解的地方，也就在这里。

一开始我以为：

```text
Steering Claude Code
=
找到最合适的 Prompt 写法。
```

现在更接近：

```text
Steering Claude Code
=
决定人的意图
应该进入哪个 Runtime Boundary。
```

Prompt 当然还是其中的一部分。

但它不再是唯一的入口。

剩下的事情，交给 Context Loader、Skill、Agent Boundary、Hook、Permission 和 Harness 本身。
