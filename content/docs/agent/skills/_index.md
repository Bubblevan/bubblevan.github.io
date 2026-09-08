Agent在工业界的实践经验：《Claude Skills构建和使用指南》
内容来自Claude官方的3篇博客，链接如下：
https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers
https://claude.com/blog/building-agents-with-skills-equipping-agents-for-specialized-work
https://claude.com/blog/complete-guide-to-building-skills-for-claude

skills是给ReAct模式的agent用的，它在agent loop里动态调用，有点像动态提示词。workflow则是人工提前写好的流程程序，虽然里面可能会用到LLM，但执行完全按代码走。也就是说，agent有了skills，不一定会按你希望的顺序用，而workflow一定会按流程执行。实际应用中，用带skills的ReAct agent还是workflow，要看场景，前者更灵活、能探索，后者更可控、稳定。

Agent在工业界的实践经验：《skill-creator升级详解》
内容来自Claude官方博客和github库里面的skill，链接如下：
https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills
https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
https://github.com/MegaSuperKitty/WeClaw
最后一个链接是我在1月做的类openclaw应用，里面集成了我几乎所有视频提到的技术


还有几个2026早期的prompt联合优化：
工作流Agent多Prompt联合优化（1）GEPA：超越GRPO，让Prompt 像基因一样进化
01-29
工作流Agent多Prompt联合优化（2）MIPRO：贝叶斯优化探索最优Prompt提示词组合
586
0
08:00
工作流Agent多Prompt联合优化（2）MIPRO：贝叶斯优化探索最优Prompt提示词组合
01-30
工作流Agent多Prompt联合优化（3）ADOPT：超越GEPA，像训练模型一样训练Prompt
988
0
08:27
工作流Agent多Prompt联合优化（3）ADOPT：超越GEPA，像训练模型一样训练Prompt

以及半年内的
[Agent skill编排]01-腾讯GraSP-编排skill graph，规划Agent行动路径
3310
0
10:03
[Agent skill编排]01-腾讯GraSP-编排skill graph，规划Agent行动路径
04-23
[Agent skill编译] 上海交大爆火论文-SkVM-把Agent Skill从提示词变成可编译的系统组件
4146
0
12:45
[Agent skill编译] 上海交大爆火论文-SkVM-把Agent Skill从提示词变成可编译的系统组件
04-26
[Agent skill编排]02-阿里最新论文-SKILLGRAPH-让技能关系图和模型参数共同进化
4122
1
09:16
[Agent skill编排]02-阿里最新论文-SKILLGRAPH-让技能关系图和模型参数共同进化
05-24
[Agent Skills] 视觉Skill来了-上海交大新论文-MMSkills让Agent学会判断屏幕状态
3984
1
09:05
[Agent Skills] 视觉Skill来了-上海交大新论文-MMSkills让Agent学会判断屏幕状态
06-03
[Agent skill编译] 港中文新论文-SkillRAE：把检索到的技能在线编译为有效且紧凑的上下文
2304
0
10:44
[Agent skill编译] 港中文新论文-SkillRAE：把检索到的技能在线编译为有效且紧凑的上下文
07-14

## 1. Agent 已经有 Tool，为什么还需要 Skill？

如果只看一个最小的 Agent Loop，Skill 似乎不是必需品。模型已经能理解用户目标，也能通过 Tool 调搜索、文件系统、数据库或浏览器：

```text
User
  ↓
LLM
  ↓
选择 Tool
  ↓
执行
  ↓
Observation
  ↓
LLM
  ↓
继续执行 / 返回答案
```

只要 Tool 足够丰富，Agent 看起来已经具备了完成任务所需的能力。

问题出现在任务从“调用一个 API”变成“按照某套专业方法把事情做完”之后。

假设给一个 Agent 接上 GitHub、浏览器和终端，并要求它：

> 调研一个新的 Agent 论文方向，判断哪些论文值得学习，然后整理成 Hugo 技术笔记。

从 capability 的角度，它并不缺东西：

```text
GitHub
→ 能读仓库

Web Search
→ 能找论文和官方博客

Shell
→ 能运行脚本

Filesystem
→ 能读写 Markdown
```

但这些能力没有告诉模型：

```text
应该优先查论文原文还是二手博客？
哪些数字必须回到论文重新核对？
论文和工程博客冲突时应该怎样表述？
什么时候只是整理材料，什么时候允许开始写正文？
代码、公式和实验结果应该保留到什么粒度？
Hugo front matter 应该长什么样？
哪些不确定信息不能被改写成确定事实？
写完以后又该检查什么？
```

这些东西不是另一个 API，而是一套**过程知识（procedural knowledge）**。

Anthropic 在介绍 Agent Skills 时给出的出发点就是这个缺口：通用 Agent 已经有相当强的推理能力，也能使用越来越多的工具，但“有能力访问一个系统”和“知道怎样按照某个领域的做法完成工作”不是一回事。

Skill 要封装的主要是后者。

### 1.1 General Agent 缺的不是另一个 API，而是过程知识

先看一个更小的例子。

假设 Agent 已经有：

```python
search_logs(query)
query_metrics(service, start, end)
restart_service(service)
create_incident_ticket(title, body)
```

从 Tool Schema 看，它已经可以操作整个故障排查链路。

用户现在说：

```text
支付服务的 p95 latency 突然升高，帮我处理一下。
```

Agent 知道可以搜索日志，也知道可以查指标，但仍然有很多决策没有写在 Tool 里：

```text
先确认告警时间窗口，还是先搜 error log？

p95 升高时应该先看：
CPU？
数据库连接池？
下游 RPC？
GC？
队列积压？

什么证据足够支持 restart？

restart 之前需不需要：
确认流量？
检查副本数？
建立 incident？
通知值班人员？

恢复以后检查多久才能宣布结束？

哪些信息必须进入 incident report？
```

当然，可以继续扩充每个 Tool 的 description。

例如把：

```text
query_metrics:
Query service metrics.
```

改成：

```text
query_metrics:
Query service metrics.

When investigating latency incidents:
1. inspect p50/p95/p99;
2. compare against the previous healthy window;
3. inspect CPU, memory and downstream dependencies;
...
```

但做到这里，实际上已经开始把另一种东西塞进 Tool contract。

Tool 原本回答的是：

```text
这个动作是什么？
输入是什么？
输出是什么？
有什么副作用和权限？
```

而现在我们试图让它顺便回答：

```text
完成一类复杂任务时，
这一组动作应该在什么条件下、
按照什么方法组合起来？
```

这两类信息的生命周期并不相同。

一个 `query_metrics` Tool 可能同时服务于：

```text
线上故障排查
容量规划
SLA 报表
成本分析
性能回归
```

如果把所有业务 SOP 都继续写进 Tool description，结果很快会变成：

```text
一个 capability
+
十几套彼此无关的 workflow
+
大量领域约束
```

不仅 Tool definition 越来越长，模型还必须在每一次看到 Tool 时承担这些无关 Context。

Skill 提供了另一个拆法：

```text
Tool
├── search_logs
├── query_metrics
├── restart_service
└── create_incident_ticket

Skill: latency-incident-response
├── 什么时候应该使用
├── 故障排查顺序
├── 判断条件
├── escalation policy
├── recovery checklist
└── report template
```

底层 capability 没有变化。

变化的是 Agent 获得了一份与当前任务相关的操作手册。

这也是为什么把 Skill 简化成“动态 Prompt”只说对了一部分。它最终确实会有一部分内容进入模型 Context，但一个完整 Skill 可以同时包含：

```text
instructions
scripts
references
assets
```

Markdown 负责模型需要理解的过程，脚本负责适合确定性执行的工作，reference 保存按需查阅的长材料，asset 则可以保存模板或其他生成结果所需的文件。

以我自己的 `Hugo-Blog-Skills` 为例，`writing-shape` 并不是一句：

```text
请帮我设计一篇博客的文章结构。
```

它还规定了输入前提、source snapshot、evidence ledger、grounding ledger、Shape 与 Beats 的职责边界以及允许修改哪些文件。对于能确定性验证的部分，又不让模型“凭感觉判断”，而是把 SHA-256 snapshot validation 交给脚本。

于是 Skill 更接近：

```text
可按需装载的 procedure package
```

而不是：

```text
一个保存起来的长 Prompt
```

这里也能解释为什么 Agent Skills 会在通用 Agent 变强以后出现。

如果每个任务都单独做一个专用 Agent：

```text
Research Agent
Incident Agent
Financial Analysis Agent
PDF Agent
Blog Agent
...
```

每个 Agent 都可以拥有独立的 system prompt、tools 和业务规则。问题是大量能力会开始重复：

```text
读取文件
搜索网页
执行代码
写结构化结果
请求人工确认
```

另一种组织方式是保留较通用的 Agent runtime，再把差异较大的领域过程拆成可以组合的 Skills：

```text
                 General Agent
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
   Research Skill  Incident Skill  Blog Skill
        │             │             │
        └─────────────┼─────────────┘
                      ↓
             shared tools / runtime
```

这并不意味着“一个通用 Agent + 无限 Skills”一定比专用 Agent 好。权限边界、模型选择、独立 Context、延迟和安全隔离仍可能要求不同 Agent。

这里只说明一个更窄的结论：

> 当不同任务共享同一套基础 capability，但依赖不同的 SOP、领域知识、检查表、模板和脚本时，这部分差异没有必要全部固化进 Agent 本体或 Tool definition，可以被拆成独立的 Skill。


### 1.2 Prompt、Tool、MCP、Skill、Workflow 分别控制什么

Skill 最容易和四个概念混在一起：

```text
Prompt
Tool
MCP
Workflow
```

它们都可能“让 Agent 做得更好”，但解决的问题不同。

先不讨论产品实现差异，可以按下面五个问题区分：

| 组件 | 主要回答的问题 | 典型内容 |
| --- | --- | --- |
| Prompt | 这一次任务要做什么？ | 目标、约束、当前输入、输出要求 |
| Tool | Agent 能执行什么动作？ | function/schema、参数、返回值、副作用 |
| MCP | Agent 怎样以标准接口连接外部能力和数据？ | resources、tools、prompts、transport |
| Skill | 这类任务应该怎样做？ | SOP、领域知识、判断规则、脚本、references、templates |
| Workflow | 哪些步骤必须由系统按既定控制流执行？ | node、branch、retry、checkpoint、state transition |

这张表不是协议规范，只是帮助划清工程职责。

#### Prompt：描述当前任务

用户可以直接告诉模型：

```text
分析这篇论文。

要求：
1. 先读 Method；
2. 再检查实验设置；
3. 最后总结 limitation；
4. 不要引用二手媒体。
```

如果这个要求只用一次，Prompt 已经够了。

问题是当同一段要求每周都要重新复制：

```text
今天分析 GraSP
明天分析 SkillGraph
后天分析 SkillRAE
```

它开始具有：

```text
repeatable
task-specific
procedural
```

这些特征。

此时把它保存成 Skill，比继续让用户重复输入更合理。

Claude Code 当前文档甚至给了一个很实用的判断方式：如果自己不断往聊天里粘贴相同的 instructions、checklist 或 multi-step procedure，或者 `CLAUDE.md` 中的一部分已经从“项目事实”长成了“执行流程”，就可以考虑把它移动到 Skill。

所以 Prompt 和 Skill 之间并不存在协议级的墙。

更像是：

```text
一次性 instruction
        │
        │ 重复出现
        │ 形成稳定 procedure
        ↓
      Skill
```

Skill 把这种过程从当前 conversation 中抽离出来，使它能够独立维护、按需加载和复用。

#### Tool：提供动作，不应该承担完整业务教程

Tool 更接近 Agent 与环境之间的 action interface。

例如：

```python
def create_pull_request(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str,
) -> PullRequest:
    ...
```

Tool contract 应该让模型知道：

```text
它能做什么
参数分别是什么
返回什么
什么时候调用是危险的
有哪些权限或副作用
```

但：

```text
修一个 GitHub issue 时，
应该先复现 bug，
再写 regression test，
然后改实现，
跑哪些测试，
什么时候允许创建 PR，
PR description 必须包含什么
```

属于更高一层的 procedure。

可以记成：

```text
Tool
=
action primitive

Skill
=
how to combine primitives for a class of tasks
```

当然，Skill 不一定使用 Tool。

例如一个纯写作 Skill 可能只规定：

```text
术语怎样翻译
文章怎样组织
哪些表达禁止使用
输出遵循什么格式
```

反过来，一个 Tool 也不依赖 Skill 才能工作。用户直接要求 Agent 查询数据库时，模型完全可以直接调用数据库 Tool。

二者是可组合关系，不是上下级依赖。

#### MCP：解决 connectivity，Skill 解决 expertise

MCP 和 Skills 的混淆更常见，因为两者都会给 Agent “增加能力”。

但 Anthropic 对两者的分工写得相当明确：

```text
MCP
→ connectivity

Skills
→ expertise
```

假设公司内部有：

```text
GitHub
Linear
Slack
Google Drive
```

MCP 可以让 Agent 通过统一的协议看到这些系统暴露出来的数据和操作。

但“能查 Linear”不代表 Agent 自动知道团队的开发流程。

比如一次 release readiness review 可能要求：

```text
1. 从 Linear 找出当前 milestone 的 unresolved blocker；
2. 从 GitHub 检查相关 PR 是否 merge；
3. 查 CI 是否通过；
4. 从 Drive 读取 release checklist；
5. 若存在 P0/P1 blocker，则不得给出 ready；
6. 最后按照团队模板生成报告。
```

连接层可以是：

```text
Linear MCP Server
GitHub MCP Server
Drive MCP Server
```

而 procedure 可以封装成：

```text
release-readiness Skill
```

形成：

```text
                release-readiness Skill
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
     Linear MCP      GitHub MCP      Drive MCP
          │              │              │
          ↓              ↓              ↓
       Issues           PR / CI       Checklist
```

这样，同一个 GitHub MCP Server 可以被：

```text
code-review Skill
release-readiness Skill
incident Skill
dependency-audit Skill
```

共同使用；同一个 release Skill 也可以协调多个 MCP Server。

所以：

```text
MCP 不替代 Skill
Skill 也不替代 MCP
```

如果问题是：

> 模型根本访问不到 Jira。

需要解决的是 connectivity。

如果问题是：

> 模型已经能访问 Jira，但不知道我们什么情况下才能关闭事故单。

需要补的是 procedural knowledge。

如果两个问题同时存在，就同时使用 MCP 和 Skill。

#### Skill：封装可复用的过程知识

因此到这里可以给 Skill 一个更工程化的工作定义：

```text
Skill
=
Discoverable Procedure
+
Domain Knowledge
+
Optional Executable Resources
```

其中 `Discoverable` 很关键。

普通 Markdown 文件放在磁盘上，并不会自动成为 Skill。宿主 Harness 至少需要知道：

```text
有哪些 Skills
每个 Skill 大致负责什么
什么时候值得加载
去哪里读取完整内容
```

这也是下一节 Progressive Disclosure 要解决的问题。

但这里先只关心职责：Skill 不是给 Agent 增加一个新的外部 endpoint，而是在不必永久塞进主 Context 的前提下，为一类任务提供可复用的执行知识。

#### Workflow：关键差别在谁拥有 control flow

最后是最容易被一句“Skill 灵活，Workflow 稳定”带过去的区别。

Anthropic 在 `Building effective agents` 中区分 workflow 与 agent 时，使用的是 control flow：

```text
Workflow
→ LLM 与 Tool 通过预定义 code path 被编排

Agent
→ LLM 动态决定自己的过程与 Tool 使用
```

这个区分放到 Skill 上同样有用。

假设有一个 Skill 写道：

```markdown
## Deploy

1. Run tests.
2. If tests pass, build the image.
3. Push the image.
4. Deploy to staging.
5. Run smoke tests.
6. If staging is healthy, ask for production approval.
```

看起来已经是非常明确的流程。

但如果这段 Markdown 是交给 Agent 执行，那么：

```text
哪一个 Tool 对应 “Run tests”？
测试失败以后该看什么？
是否要重试？
什么时候算 tests pass？
是否真的已经完成第 4 步？
能不能暂时跳过某一步？
```

仍有一部分由模型解释。

可以把它想成：

```text
SKILL.md

"先测试，再构建，再部署 staging"
              ↓
             LLM
              ↓
        理解当前状态
        选择下一动作
        调用 Tool
        阅读 Observation
        决定是否继续
```

如果改成程序化 Workflow：

```python
test_result = run_tests()

if not test_result.ok:
    return fail("tests failed")

image = build_image()
push_image(image)

deployment = deploy_staging(image)
health = smoke_test(deployment)

if not health.ok:
    rollback(deployment)
    return fail("staging unhealthy")

approval = wait_for_approval()

if approval:
    deploy_production(image)
```

控制流的位置变了。

这里：

```text
test fail
→ stop

health fail
→ rollback

没有 approval
→ production 不会执行
```

不是模型“应该遵守”的自然语言要求，而是 runtime 的 transition rule。

这就是 Skill 与 Workflow 最需要记住的边界：

```text
Skill
更偏向告诉模型：
how this class of task should be done

Workflow
更偏向由程序规定：
what transition is allowed next
```

它们仍然可以组合。

程序化 Workflow 的一个 node 完全可以启动带 Skill 的 Agent：

```text
Workflow
│
├── collect requirements
│
├── research
│      └── Research Skill Agent
│
├── implementation
│      └── Coding Skill Agent
│
├── deterministic tests
│
└── human approval
```

所以不应该把它们理解成：

```text
Skill OR Workflow
```

更准确的是问：

```text
这条约束应该被写在哪里？
```

如果它是：

```text
“处理这种故障时，通常先检查依赖服务。”
```

写进 Skill 很合理。

如果它是：

```text
“没有人工批准，支付动作绝对不能执行。”
```

只在 Skill 里写一句：

```text
MUST ask for approval.
```

就不够了。

这条限制更适合进入 runtime、permission system 或显式 Workflow gate。


### 1.3 Skill 与 Workflow 的差别，最终落到 control flow ownership

为了把前面的概念从定义拉回工程问题，可以直接比较同一个任务。

假设我要把一堆 Agent 论文学习材料整理成 Hugo 博客。输入可能包含：

```text
论文 PDF
官方博客
GitHub README
代码片段
实验日志
自己过去的聊天草稿
```

输出要求：

```text
一篇结构完整的技术学习笔记
+
保留事实、数字、公式、代码和引用
+
区分 observed / inferred / planned
+
通过 Hugo build
```

如果完全交给一个带 Blog Skill 的 Agent，运行过程可能是：

```text
User
 ↓
Agent
 ↓
load blog Skill
 ↓
阅读材料
 ↓
判断需要什么结构
 ↓
写正文
 ↓
自己发现缺证据
 ↓
重新搜索 / 回读
 ↓
修改
 ↓
运行 Hugo
 ↓
完成
```

它的优势很明显。

面对一堆脏乱材料时，模型可以动态决定：

```text
哪些地方需要多读一篇论文
哪些章节可以合并
哪个代码片段更适合作为例子
发现新证据以后是否调整文章结构
```

这些步骤事先很难完全枚举。

但相应地，如果只是写在一个 Skill 里：

```text
先 Research
再 Shape
再 Beats
再 Draft
再 Verify
```

也不能保证模型不会：

```text
材料还没有读完
→ 提前开始 Draft

Shape 还没确认
→ 顺手把正文也写了

source 已经发生变化
→ 继续使用旧结构

verification 没运行
→ 根据文本外观宣布完成
```

这些失败不是因为 Skill 没有写清楚。

而是：

```text
instruction
≠
state machine
```

这正是我后来在 `Hugo-Blog-Skills` 里逐渐把写作过程拆开的原因。

例如：

```text
raw material
      ↓
   research
      ↓
    shape
      ↓
    beats
      ↓
    draft
      ↓
    edit
      ↓
    verify
```

其中一部分适合写成 Skill：

```text
writing-shape
→ 怎样从 evidence pile 建立 information architecture

writing-beats
→ 怎样按照 reader knowledge traversal 写一个 Beat

stop-slop
→ 怎样删除模板化技术文风而不改变事实
```

另一部分则更适合做 deterministic gate：

```text
source snapshot hash 一致吗？
→ script

Hugo 能 build 吗？
→ command

引用的文件存在吗？
→ validator

Beat 的 evidence ID 在 ledger 里存在吗？
→ deterministic check
```

如果以后再把这些步骤编成真正的工作流，还可以继续把状态转换从模型手里拿出来：

```text
                 MODEL CONTROL
                       ↑
                       │
      open-ended exploration
      interpretation
      evidence synthesis
      prose generation
                       │
               ───────┼───────
                       │
      source hash validation
      schema validation
      build
      permission gate
      irreversible action
                       │
                       ↓
                RUNTIME CONTROL
```

这里没有一个固定百分比告诉我们：

```text
70% 给模型
30% 给 Workflow
```

工程上真正要判断的是每条 transition 的失败成本。

例如：

#### 情况一：错误后很容易恢复

```text
研究论文时先看 Introduction
还是先看 Method？
```

让模型决定通常没有问题。

即使路线不是最优，只会增加一点 token 或时间。

#### 情况二：错误会产生昂贵副作用

```text
是否发送邮件？
是否 merge PR？
是否 deploy production？
是否执行支付？
```

这时“Skill 里已经明确写了不要乱做”不能代替 permission 和 runtime gate。

#### 情况三：顺序本身就是正确性的一部分

比如：

```text
migration
↓
backfill
↓
switch read path
↓
verify
↓
remove legacy path
```

如果第二步没有完成就执行第三步，系统可能进入错误状态。

这种依赖不能只依靠 Agent 记住自然语言步骤。

#### 情况四：步骤本身无法事先预测

修一个陌生代码库里的 bug 时，很难预定义：

```text
一定先读 A.ts
再改 B.ts
再跑 C test
```

需要改几个文件、在哪一层发现根因，都取决于模型执行后的 observation。

这时硬编码完整 Workflow 反而会失去 Agent 的价值，Skill 更适合提供：

```text
先复现
建立 failure hypothesis
修改前寻找相关 test
避免 unrelated refactor
修改后跑 targeted test
最后扩大 regression scope
```

具体行动仍由 Agent 根据环境决定。

所以可以把 Skill 与 Workflow 的选择压缩成一组更具体的问题：

| 问题 | 更适合交给 |
| --- | --- |
| 这个任务通常应该怎样做？ | Skill |
| 这一步有哪些领域经验和检查项？ | Skill |
| 下一步需要根据开放环境动态探索吗？ | Agent + Skill |
| 某个状态转换是否必须满足硬条件？ | Workflow / Runtime |
| 一个危险动作是否需要不可绕过的审批？ | Permission / Runtime |
| 某个检查能否被程序确定性判断？ | Script / Validator |
| Agent 需要怎样访问外部系统？ | Tool / MCP |
| 只是这一次任务的目标和特殊要求？ | Prompt |

于是我现在不会再把 Skill 和 Workflow 简单总结成：

```text
Skill 更灵活
Workflow 更稳定
```

这种说法方向没错，但信息太少。

更有用的区分是：

```text
Skill
把 procedure 放在模型可以解释和组合的知识层

Workflow
把关键 transition 放在 runtime 可以强制执行的控制层
```

同一个生产 Agent 往往同时需要两者。

如果任务要求探索，就给模型足够的行动空间；如果某一步涉及不可接受的副作用、严格状态迁移或可以确定性检查的事实，就不要指望自然语言 instruction 单独承担约束。

到这里，Skill 的位置才比较清楚：

```text
                   User Task
                      │
                    Prompt
                      │
                      ▼
                Agent / Model
                      │
             ┌────────┴────────┐
             │                 │
          Skills            Workflow
     procedural knowledge   control flow
             │                 │
             └────────┬────────┘
                      │
                 Tool / MCP
                      │
                      ▼
                  Environment
```

接下来的问题才是：

> 如果一个 Agent 安装了几十甚至几百个 Skill，总不能把所有 `SKILL.md` 每次都塞进 Context。它怎么知道自己拥有哪些 Skill，又如何只在需要时加载对应内容？

这就进入 Agent Skills 最有辨识度的一层设计：**Progressive Disclosure**。

## 2. 一个 Skill 到底是怎样进入 Agent Context 的？

上一节留下了一个实际问题。

假设我已经写了：

```text
pdf-processing
code-review
incident-response
paper-research
hugo-writing
database-migration
release-check
...
```

几十个 Skill。

最直接的实现当然是启动 Agent 时把所有 `SKILL.md` 拼进 system prompt：

```python
system_prompt = BASE_PROMPT

for skill in installed_skills:
    system_prompt += read(skill / "SKILL.md")
```

这样模型确实“知道”所有 Skill。

但它很快会产生另一个问题：

```text
Skill A: 3000 tokens
Skill B: 4000 tokens
Skill C: 2500 tokens
...
Skill Z: 3500 tokens
```

用户只是问：

```text
帮我检查这篇论文的实验设置。
```

模型却可能在当前 Context 中同时看到：

```text
PDF 处理规范
Excel 格式规范
数据库迁移规则
前端设计规范
Release SOP
Incident SOP
博客发布规则
...
```

其中绝大部分与当前任务无关。

问题不只是 token 账单。

更直接的是：

```text
Context Window
=
System Prompt
+ Conversation History
+ Tool Definitions
+ Skill Instructions
+ Retrieved Documents
+ Tool Results
+ Current Task
```

Skill 永久占掉的每一段 Context，都在和任务真正需要的信息竞争。

Agent Skills 没有选择“安装一个 Skill，就永久加载整个 Skill”，而是把 Skill 拆成不同披露层级：

```text
Level 1
Metadata
name + description
        ↓
模型判断相关

Level 2
SKILL.md
完整 procedure
        ↓
执行过程中发现需要更多材料

Level 3
Resources
references / scripts / assets
```

这套机制被称为 **Progressive Disclosure**。

它解决的不是“怎样把长 Prompt 存进文件夹”，而是：

> **怎样让 Agent 拥有很多潜在过程知识，却只为当前任务支付与之相关的 Context 成本。**


### 2.1 `SKILL.md` 只是入口，不是整个 Skill

按照 Agent Skills specification，一个最小 Skill 是一个目录，其中至少存在：

```text
skill-name/
└── SKILL.md
```

一个更完整的 Skill 通常可以组织成：

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

其中只有：

```text
SKILL.md
```

是必需文件。

官方规范允许目录里继续出现其他文件和子目录；`scripts/`、`references/`、`assets/` 是约定俗成的组织方式，而不是说 Skill 只能包含这三个目录。

最小的 `SKILL.md` 长这样：

```yaml
---
name: paper-review
description: Reviews research papers with emphasis on methodology, experiments, baselines, ablations, and limitations. Use when analyzing or comparing academic papers.
---

# Paper Review

Read the paper before drawing conclusions.

When evaluating experimental claims:

1. identify the task and benchmark;
2. identify baselines;
3. inspect the evaluation protocol;
4. separate reported results from your interpretation;
5. record limitations and missing evidence.
```

它可以拆成两部分：

```text
SKILL.md
│
├── YAML frontmatter
│   ├── name
│   └── description
│
└── Markdown body
    └── procedure / instructions
```

按照当前 Agent Skills specification，`name` 与 `description` 是两个必填字段。

其中 `name` 有明确的格式约束：

```text
1–64 characters
lowercase letters
numbers
hyphens
```

不能：

```text
PDF-Processing
-pdf
pdf--processing
```

而且 `name` 应与父目录名一致。

例如：

```text
skills/
└── paper-review/
    └── SKILL.md
```

对应：

```yaml
name: paper-review
```

`description` 最大允许 1024 characters，并且不应该只解释：

```text
what
```

还应该包含：

```text
when
```

因此：

```yaml
description: Helps with papers.
```

虽然短，但作为 discovery metadata 信息不足。

更好的版本会写成：

```yaml
description: Reviews research papers with emphasis on methodology, experiments, baselines, ablations, and limitations. Use when the user asks to analyze, compare, reproduce, or critique academic papers.
```

这里同时编码了：

```text
它做什么？
→ reviews research papers

重点是什么？
→ methodology / experiments / baselines / ablations / limitations

什么任务应该触发？
→ analyze / compare / reproduce / critique papers
```

除了两个必填字段，Agent Skills specification 还定义了几个可选字段：

| Field | 是否必需 | 作用 |
| --- | --- | --- |
| `name` | 是 | Skill identifier |
| `description` | 是 | capability + invocation context |
| `license` | 否 | Skill 的许可证 |
| `compatibility` | 否 | 环境、依赖、网络等要求 |
| `metadata` | 否 | 自定义字符串 metadata |
| `allowed-tools` | 否 | 预批准 Tool，目前仍属于 experimental |

例如：

```yaml
---
name: postgres-migration
description: Plans and validates PostgreSQL schema migrations. Use when changing database schemas, indexes, constraints, or migration scripts.
license: MIT
compatibility: Requires Python 3.12+, PostgreSQL client tools, and database access.
metadata:
  author: bubblevan
  version: "0.2"
allowed-tools: Bash(psql:*) Bash(python:*) Read
---
```

这里需要注意一个边界：

```text
Agent Skills specification
≠
所有 Harness 的实现行为完全相同
```

特别是 `allowed-tools`，规范当前仍明确标记为 experimental，不同 Agent implementation 是否支持、具体怎样解释，不能仅凭字段存在就假定一致。

而真正的过程知识写在 frontmatter 之后的 Markdown body 中。

规范没有规定正文必须使用：

```text
## Workflow
## Rules
## Examples
## Output
```

这样的固定模板。

它只要求：

> 写下有助于 Agent 正确完成任务的 instructions。

因此一个 Skill 可以偏 checklist：

```markdown
## Review checklist

- reproduce the reported command;
- inspect changed files;
- run targeted tests;
- run broader regression tests;
- report checks that were not run.
```

也可以偏 procedure：

```markdown
## Workflow

1. Reproduce the failure.
2. Form a hypothesis from observable evidence.
3. Locate the smallest relevant code path.
4. Add or identify a regression test.
5. Modify the implementation.
6. Run the targeted test.
7. Expand verification scope.
```

还可以引用外部文件：

```markdown
For database-specific rules, read:

references/database.md

Before finishing, run:

scripts/verify.py
```

这也解释了为什么：

```text
Skill
≠
SKILL.md
```

更准确地说：

```text
SKILL.md
=
Skill 的 discovery entry
+
procedure index
+
核心 instructions

整个 Skill directory
=
SKILL.md
+
deterministic code
+
on-demand knowledge
+
output resources
```

`SKILL.md` 更像 Skill 的入口和导航页，而不是要求把所有知识都写在这一个文件里。


### 2.2 Progressive Disclosure：不是把几百个 Skill 全塞进 Prompt

Agent Skills specification 当前把 Progressive Disclosure 分成三个层级。

第一层是：

```text
Metadata
≈ name + description
≈ ~100 tokens / Skill
```

这些 metadata 会在启动阶段提供给 Agent，使模型至少知道当前有哪些 Skill 可以使用。

假设安装了三个 Skill：

```yaml
name: paper-review
description: Reviews research papers...

name: hugo-writing
description: Writes technical Hugo articles...

name: database-migration
description: Safely plans database migrations...
```

模型启动时需要看到的不是三个完整 Skill，而更接近：

```text
Available Skills

paper-review
Reviews research papers...

hugo-writing
Writes technical Hugo articles...

database-migration
Safely plans database migrations...
```

此时用户说：

```text
帮我检查 GraSP 的实验到底支不支持论文里的主要结论。
```

模型根据 metadata 判断：

```text
paper-review
→ relevant

hugo-writing
→ not needed yet

database-migration
→ irrelevant
```

随后才进入第二层：

```text
load:
paper-review/SKILL.md
```

官方规范目前推荐：

```text
SKILL.md instructions
< 5000 tokens
```

Anthropic 的 Skill authoring guide 另外给出了一个便于维护的经验约束：

```text
SKILL.md
< 500 lines
```

这里要区分两个数字的含义。

```text
< 5000 tokens
→ Progressive Disclosure 的推荐 Context budget

< 500 lines
→ authoring / maintainability guidance
```

它们都不是：

```text
超过 5001 tokens
→ Skill 无法执行
```

或者：

```text
第 501 行
→ Harness 拒绝加载
```

这种硬运行限制。

官方明确把这些数字写作 recommended / ideal guidance。真正的目标仍然是控制激活以后进入 Context 的内容量。

因此假设：

```text
Skill A metadata = 100 tokens
Skill B metadata = 100 tokens
...
Skill N metadata = 100 tokens
```

安装 `N` 个 Skill 时，启动成本可以粗略写成：

\[
C_{\text{startup}}
\approx
C_{\text{base}}
+
\sum_{i=1}^{N} C_{\text{metadata},i}
\]

如果 metadata 平均约 100 tokens，那么只是为了帮助记忆，可以近似成：

\[
C_{\text{skill-discovery}}
\approx
100N
\]

但这只是数量级直觉，不是每个 Skill 都会严格消耗 100 tokens。

真正命中某个 Skill 后，Context 才进一步增加：

\[
C_{\text{active}}
=
C_{\text{startup}}
+
C_{\text{SKILL.md}}
+
C_{\text{selected references}}
+
C_{\text{relevant tool results}}
\]

因此 Progressive Disclosure 的主要区别是：

```text
传统做法

Skill A body ─┐
Skill B body ─┤
Skill C body ─┼──→ Context
Skill D body ─┤
Skill E body ─┘


Progressive Disclosure

A metadata ─┐
B metadata ─┤
C metadata ─┼──→ Context
D metadata ─┤
E metadata ─┘
              │
              │ match C
              ↓
         Skill C body
              │
              │ need reference
              ↓
       selected resource
```

这和 RAG 有一点表面相似之处：

```text
都不是一次性加载全部知识
都先判断相关性
都只把当前需要的信息送入 Context
```

但不应该直接把 Agent Skills 写成一种 RAG。

RAG 常见的检索单位是：

```text
document chunk
```

目标通常是：

```text
找到与 query 语义相关的 evidence
```

Agent Skill discovery 的第一阶段面对的是：

```text
capability / procedure description
```

它需要判断的是：

```text
这个任务需要哪一种操作过程？
```

例如用户说：

```text
我这份 Excel 里有 sales、cost、region 三列，帮我算利润率再画季度图。
```

Skill discovery 可能选择：

```text
spreadsheet-analysis
```

不是因为 `SKILL.md` 某一段和 query 的 embedding 最接近，而是因为：

```text
description
→ 表示这个 Skill 能解决什么任务
→ 以及什么场景应该使用它
```

当然，具体 Harness 完全可以进一步引入 embedding、search index、tool search 或其他 retrieval mechanism。

Agent Skills specification 本身并没有规定：

```text
必须使用 BM25
必须使用 embedding
必须使用某个 reranker
```

它规定的是可发现的 Skill 表示和逐层加载接口，而不是唯一的检索算法。

第三层才是 Skill 内部的 resources：

```text
references/
scripts/
assets/
```

而且仍然不是一次性全部进入 Context。

例如：

```text
cloud-deploy/
├── SKILL.md
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

用户说：

```text
把这个服务部署到 GCP Cloud Run。
```

合理的加载过程是：

```text
cloud-deploy metadata
        ↓
cloud-deploy/SKILL.md
        ↓
发现 target = GCP
        ↓
references/gcp.md
```

而不是：

```text
aws.md
+
gcp.md
+
azure.md
→ 全塞进 Context
```

这就是 Progressive Disclosure 真正发挥作用的地方。

它不是简单地：

```text
文件放在磁盘上，所以节省 token
```

而是要求 Skill 的 information architecture 本身支持：

```text
先发现
再展开
再局部读取
```

如果一个 `SKILL.md` 写成：

```text
8000 行
+
所有框架文档
+
几十个示例
+
全部 API reference
```

那么即使它启动前没有进入 Context，一旦 Skill 被命中，还是会瞬间产生大量无关内容。

所以 Progressive Disclosure 同时要求 Skill 作者主动把信息拆层。


### 2.3 `description` 为什么实际上承担了 retrieval contract

这套设计带来一个很容易被低估的问题：

> `description` 并不是 README 里随便写的一句介绍，它决定了 Agent 有没有机会看到后面的 Skill。

假设真正有用的 `SKILL.md` 写得非常详细：

```text
准确的 SOP
完整的边界条件
好的示例
确定性脚本
详细 reference
```

但 description 是：

```yaml
description: Helps with technical work.
```

用户问：

```text
帮我 review 这个 PR，重点检查数据库 schema migration 会不会破坏 rollback。
```

模型面前可能同时还有：

```text
code-review
database
deployment
testing
incident
```

几个 Skill。

`Helps with technical work` 几乎没有提供 discriminative information。

结果可能是：

```text
Skill 本身写得很好
        ↓
Discovery 没选中
        ↓
SKILL.md 从未加载
        ↓
对最终任务的贡献 = 0
```

可以把一次 Skill invocation 粗略拆成：

\[
P(\text{Skill succeeds})
=
P(\text{trigger})
\times
P(\text{execute correctly}\mid\text{trigger})
\]

哪怕：

\[
P(\text{execute correctly}\mid\text{trigger})
\]

已经非常高，只要：

\[
P(\text{trigger})
\]

很低，整体效果仍然很差。

这就是 `description` 的 retrieval contract 含义。

它至少要回答：

```text
1. What does this Skill do?
2. When should it be used?
```

Agent Skills specification 还特别建议加入能帮助 Agent 判断相关任务的具体关键词。

例如：

```yaml
description: Reviews code.
```

信息太少。

可以改成：

```yaml
description: Reviews code changes for correctness, regressions, test coverage, security issues, and maintainability. Use when reviewing pull requests, patches, diffs, commits, or proposed code changes.
```

这里 deliberately 加入：

```text
pull requests
patches
diffs
commits
code changes
```

是因为真实用户不一定会说：

```text
请调用 code-review Skill。
```

他更可能说：

```text
看看这个 PR 有没有坑。
```

或者：

```text
帮我过一下这个 diff。
```

或者：

```text
这个 commit 能 merge 吗？
```

所以触发条件如果只写：

```text
Use for code review.
```

会把大量真实表达留在边界外。

另一方面，description 也不是越宽越好。

例如：

```yaml
description: Use this Skill whenever the user asks anything involving code, software, GitHub, debugging, testing, development, deployment, infrastructure, files, or technical work.
```

这样会产生相反的问题：

```text
over-trigger
```

用户只是问：

```text
Python 的 dataclass 和 NamedTuple 有什么区别？
```

却加载了一整套：

```text
PR review procedure
security checklist
test workflow
git diff instructions
```

这会带来：

```text
不必要的 Context cost
+
与当前任务冲突的 procedure
+
模型行为被过度约束
```

所以 Skill discovery 至少有两类基本错误：

```text
False Negative

任务本来需要 Skill
        ↓
description 没有覆盖
        ↓
Skill 未加载
```

以及：

```text
False Positive

任务不需要 Skill
        ↓
description 过宽
        ↓
无关 Skill 被加载
```

可以对应到一个普通 retrieval confusion matrix：

| | Skill 应该触发 | Skill 不应该触发 |
| --- | ---: | ---: |
| 实际触发 | True Positive | False Positive |
| 实际未触发 | False Negative | True Negative |

于是 Skill 作者实际上有两个不同的优化目标：

```text
Body optimization
→ Skill 被加载以后，Agent 能不能正确执行？

Description optimization
→ Skill 应该出现的时候能不能被发现？
```

这两个问题不能混在一起。

一个 Skill 在测试里失败，原因可能根本不是：

```text
procedure 写错了
```

而是：

```text
从来没有触发
```

反过来，一个执行质量很好的 Skill，也可能因为 description 过宽而伤害其他任务。

这也是 Anthropic 后来把 **description optimization** 单独加入 `skill-creator` 的原因之一。

当前 `skill-creator` 甚至明确提醒：

```text
description
=
primary triggering mechanism
```

并要求：

```text
what the Skill does
+
specific contexts for when to use it
```

当前实现还特别针对 Claude 的 under-triggering 倾向，建议 description 在合理范围内写得更积极一些。

但这里不能把：

```text
“写得 pushy”
```

理解成：

```text
“什么都触发”
```

真正要优化的仍然是 task distribution 上的 selection quality。

假设我有一个 `hugo-writing` Skill，可以人为构造一组 should-trigger：

```text
把这些实验日志整理成 Hugo 博客
继续写 content/docs/agent/skills/_index.md
帮我把这份技术笔记改成 Hugo 页面
按照博客仓库规范整理这篇学习笔记
```

再构造 should-not-trigger：

```text
解释一下这个 Python traceback
帮我比较两篇论文的方法
这个函数的时间复杂度是多少
帮我写一个 pytest
```

如果 description 改了一版，就重新检查：

```text
Trigger Recall
=
正确触发的 should-trigger
/
全部 should-trigger
```

以及：

```text
Trigger Precision
=
正确触发
/
全部触发
```

实际 `skill-creator` 的 description optimization 会用真实查询集合来做类似的 should-trigger / should-not-trigger 测试，而不是只盯着 Skill body。

于是一个成熟 Skill 的测试对象至少有两层：

```text
Layer A
Discovery Eval
任务来了以后会不会选中？

Layer B
Execution Eval
选中以后能不能正确完成？
```

后面进入 Skill Creator 时，这个区分会非常重要。


### 2.4 `scripts/`、`references/`、`assets/` 为什么不能都写进 Markdown

Progressive Disclosure 的第三层不是为了让目录看起来整洁，而是在处理三类性质不同的信息。

假设要写一个：

```text
financial-report/
```

最偷懒的版本可以把所有东西都写进 `SKILL.md`：

```text
会计术语解释
CSV schema
100 行 Python
公司报告模板
过去三个完整 example
图表规范
异常值检查
行业 benchmark
```

结果可能是一个几千行 Markdown。

但这些内容进入模型的必要性并不相同。

更合理的拆法可能是：

```text
financial-report/
├── SKILL.md
│
├── scripts/
│   ├── validate_csv.py
│   └── calculate_metrics.py
│
├── references/
│   ├── metric-definitions.md
│   ├── accounting-rules.md
│   └── report-schema.md
│
└── assets/
    ├── report-template.docx
    └── company-logo.png
```

四类文件承担不同职责。


#### `SKILL.md`：模型必须知道怎样做

应该放：

```text
任务目标
步骤
什么时候读哪个 reference
什么时候运行哪个 script
判断边界
失败处理
输出 contract
```

例如：

```markdown
## Workflow

1. Inspect the input schema.
2. Run `scripts/validate_csv.py`.
3. If validation fails, report the failing rows and stop.
4. Read `references/metric-definitions.md` for required metrics.
5. Run `scripts/calculate_metrics.py`.
6. Generate the report using `assets/report-template.docx`.
```

模型需要理解的是 control logic。

不需要理解：

```python
validate_csv.py
```

里面每一行 pandas 是怎样实现的。


#### `scripts/`：把确定性工作从自然语言推理中拿出去

假设要求：

```text
检查 front matter 是否包含：
title
date
weight
```

完全可以让模型自己读文本判断：

```text
我看到了 title。
我看到了 date。
应该没问题。
```

但既然规则可以确定性表达，更可靠的方式是：

```python
REQUIRED_FIELDS = {
    "title",
    "date",
    "weight",
}

missing = REQUIRED_FIELDS - frontmatter.keys()

if missing:
    raise ValueError(
        f"Missing required fields: {sorted(missing)}"
    )
```

再例如验证 Source Snapshot。

让 LLM 比较：

```text
几十个 filename + SHA-256
```

没有实际收益。

脚本可以直接：

```python
from pathlib import Path
import hashlib

def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()
```

然后模型只需要得到：

```text
Snapshot check: PASS
```

或者：

```text
Snapshot check: FAIL

changed:
- notes.md

added:
- result.json
```

于是：

```text
LLM
→ 处理 interpretation

Script
→ 处理 deterministic computation
```

这不只是 token 优化。

还有 correctness 的差别。

例如：

```text
hash comparison
schema validation
JSON parsing
file inventory
numeric aggregation
unit tests
build
lint
```

这些事情有明确算法时，没有必要把它们重新退化成：

```text
请语言模型认真检查一下。
```

Anthropic 对 Skill authoring 还给了一个很实用的 **degrees of freedom** 分类。

任务可以允许：

```text
High freedom
→ natural-language instructions

Medium freedom
→ pseudocode / parameterized scripts

Low freedom
→ exact deterministic scripts
```

例如代码 review：

```text
不同项目有不同架构
不同 bug 有不同根因
```

适合给模型较高自由度。

而数据库 migration：

```text
必须备份
必须执行固定验证
顺序错了可能破坏数据
```

则应该降低自由度。

这和上一章讨论的：

```text
Skill vs Workflow
```

其实是同一个工程判断在 Skill 内部的缩影：

> 能确定性表达且失败代价高的部分，不必坚持让模型自己推理。


#### `references/`：模型可能需要知道，但不是每次都需要知道

Reference 的典型内容包括：

```text
API documentation
schema
business rules
long examples
domain definitions
framework-specific instructions
```

例如：

```text
deploy-cloud/
├── SKILL.md
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

主 Skill 只需要告诉模型：

```markdown
Determine the target cloud first.

- For AWS, read `references/aws.md`.
- For GCP, read `references/gcp.md`.
- For Azure, read `references/azure.md`.

Do not read provider references that do not match the deployment target.
```

如果用户明确要：

```text
AWS
```

才读取：

```text
references/aws.md
```

这相当于在 Skill 内部继续做第二次 information routing：

```text
User Query
   ↓
Skill Discovery
   ↓
SKILL.md
   ↓
Task State
   ↓
Reference Selection
   ↓
Relevant Reference
```

所以 Progressive Disclosure 不是只有：

```text
Skill A vs Skill B
```

这一层。

它可以递归地存在于一个 Skill 内部：

```text
Skill
  ↓
core workflow
  ↓
variant
  ↓
specific reference
```

官方规范也因此建议 reference file 保持 focused，并尽量避免：

```text
SKILL.md
  ↓
reference-A.md
  ↓
reference-B.md
  ↓
reference-C.md
  ↓
真正需要的信息
```

这种深层 reference chain。

否则模型必须反复导航才能找到真正的 procedure。

Agent Skills specification 当前建议从 `SKILL.md` 引用文件时尽量保持一层深度。

例如：

```text
good:

SKILL.md
├── references/aws.md
├── references/gcp.md
└── references/azure.md
```

而不是：

```text
SKILL.md
└── references/cloud/index.md
    └── providers/gcp/index.md
        └── deployment/cloud-run.md
```

文件系统不是越抽象越好。

这里优化的是 Agent 的 navigation cost，不是传统软件工程里的 package purity。


#### `assets/`：输出需要，但 Context 不需要理解

最后一种更容易被忽略。

假设 Agent 要生成一个公司报告。

它可能需要：

```text
report-template.docx
logo.png
font configuration
example theme
```

这些文件参与最终产物，但模型不一定需要把它们的内容转换成文本以后放进 Context。

因此：

```text
references/
→ 给 Agent 阅读

assets/
→ 给产物使用
```

概念上最好分开。

例如：

```text
slides/
├── SKILL.md
├── references/
│   └── slide-guidelines.md
└── assets/
    ├── title-template.pptx
    └── logo.png
```

Agent 要理解：

```text
slide-guidelines.md
```

但使用：

```text
title-template.pptx
logo.png
```

不意味着必须先把这两个二进制文件“读懂”以后再生成演示文稿。

于是一个 Skill 的信息可以按“模型是否需要看见”重新分类：

| 内容 | 模型需要进入 Context？ | 更适合放哪里 |
| --- | --- | --- |
| 核心执行步骤 | 是 | `SKILL.md` |
| 什么时候读取什么资料 | 是 | `SKILL.md` |
| 长篇领域规则 | 需要时 | `references/` |
| provider-specific 文档 | 对应任务需要时 | `references/` |
| hash / schema / build 等确定性操作 | 通常不需要源码进入 Context | `scripts/` |
| 模板、图像、静态资源 | 通常不需要 | `assets/` |

我自己的 `Hugo-Blog-Skills` 已经可以拿来做一个更具体的例子。

`writing-shape/SKILL.md` 没有把所有 contract 全部复制进去，而是要求需要时读取：

```text
references/claim-state.md
references/grounding-ledger.md
references/evidence-ledger.md
references/source-snapshot.md
references/rich-payload.md
references/shape-artifact.md
```

`writing-beats` 又在正式写 Beat 前要求运行 deterministic snapshot validation，而不是让模型自己比较 SHA-256。

整个结构可以抽象成：

```text
                  writing-shape
                       │
                       │ core procedure
                       ▼
                    SKILL.md
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
 claim-state     evidence-ledger   rich-payload
        │
        │ accepted shape
        ▼
                writing-beats
                       │
                       ▼
             deterministic checks
                       │
                       ▼
                  next Beat
```

这里真正节省 Context 的，不是简单地把一个 1 万行 Prompt 切成 20 个 Markdown 文件。

如果 `SKILL.md` 一启动就写：

```text
Read every file in references/
```

那么拆文件几乎没有改变运行时信息量。

Progressive Disclosure 要求的是：

```text
Metadata
→ 只负责发现

SKILL.md
→ 只负责核心 procedure 与 navigation

Reference
→ 当前分支需要时再加载

Script
→ 能直接执行就不要把源码当推理材料

Asset
→ 能直接使用就不要转成 Prompt
```

这可以压成一个上下文预算模型：

\[
C_{\text{task}}
=
C_{\text{base}}
+
C_{\text{skill metadata}}
+
C_{\text{activated procedures}}
+
C_{\text{selected evidence}}
\]

而不是：

\[
C_{\text{task}}
=
C_{\text{everything installed}}
\]

到这里，Agent Skills 最有辨识度的运行机制已经比较清楚了。

但还有一个问题没有回答。

即使 Skill 的目录结构设计正确、Progressive Disclosure 也工作正常，我们仍然不知道：

```text
加载 Skill 以后，
Agent 真的变强了吗？
```

一个看起来很专业的 `SKILL.md` 可能：

```text
从未触发
触发错任务
增加无用步骤
消耗更多 token
让强模型过度服从旧 SOP
在某个模型上有效、换模型以后失效
甚至比不装 Skill 更差
```

所以 Skill Engineering 的下一步不是继续讨论怎么把 Markdown 写漂亮，而是把 Skill 本身变成一个可以测试的对象：

```text
Draft Skill
     ↓
With Skill
vs
Without Skill
     ↓
Task-level Eval
     ↓
Pass Rate
Latency
Tokens
Failure Pattern
     ↓
Refine
```

这就是 Anthropic 后来升级 `skill-creator` 时真正补上的那一层：**Skill 不再只被“编写”，而开始被测量。**

## 3. Skill 写出来以后，怎么证明它真的有用？

到目前为止，我们讨论的还是 Skill 的设计问题：

```text
怎样写 description
怎样拆 SKILL.md
什么时候放 references
什么时候改成 script
怎样用 Progressive Disclosure 控制 Context
```

这些原则可以让一个 Skill 看起来合理，却不能证明它真的改善了 Agent。

例如我写了一个 `code-review` Skill：

```markdown
---
name: code-review
description: Reviews code changes for correctness, regressions, test coverage, security issues, and maintainability...
---

# Code Review

1. Read the diff.
2. Locate affected call paths.
3. Inspect existing tests.
4. Look for regressions.
5. Run relevant tests.
6. Report findings with file and line references.
```

人工读起来没有明显问题。

然后我测试一次：

```text
帮我 review 这个 PR。
```

Claude 找到了一个 bug。

很容易得到结论：

```text
Skill 有效。
```

但这个实验什么都没有证明。

因为我们不知道：

```text
不加载 Skill 时，
Claude 会不会也找到同一个 bug？

Skill 是否只在这个例子上有用？

它有没有漏掉原本能发现的问题？

它是不是多花了两倍 token，
但最终结果没有变化？

换一个模型以后是否还有效？

修改 Skill 的 description 以后，
它是不是反而不触发了？
```

如果不能回答这些问题，所谓：

```text
这个 Skill 效果不错
```

仍然只是一次 anecdotal observation。

Anthropic 在 2026 年 3 月更新 `skill-creator` 时，补上的正是这一层：不再把 Skill authoring 停留在“写完以后试一下”，而是把它变成：

```text
Draft
  ↓
Eval
  ↓
Baseline
  ↓
Measure
  ↓
Inspect failures
  ↓
Refine
  ↓
Run again
```

也就是把一部分软件工程里熟悉的：

```text
test
benchmark
regression
A/B comparison
```

带到自然语言 Skill 上。


### 3.1 从“写一个 Skill”转向“Skill + Eval”

Anthropic 更新 `skill-creator` 时举过一个很具体的例子。

他们的 PDF Skill 以前处理普通 PDF 已经比较稳定，但遇到 **non-fillable form** 会失败。

这种 PDF 没有可以直接填写的 form field。Agent 必须自己判断：

```text
姓名应该放在哪里？
日期应该放在哪里？
这一行文字的准确坐标是多少？
```

如果只进行几次人工试用，这个 failure 很容易被正常 PDF 样本掩盖。

加入针对这一情况的 eval 后，问题才被单独稳定复现，随后实现改成利用抽取文本的坐标来锚定输入位置。

这类过程很接近普通软件测试：

```text
发现 failure
    ↓
保存为 test case
    ↓
修改实现
    ↓
旧 failure 应通过
    ↓
其他 test 不应 regression
```

Skill eval 也可以这样理解。

假设我要测试一个：

```text
paper-analysis
```

Skill。

不应该只准备：

```text
Prompt:
帮我分析这篇论文。
```

然后人工评价：

```text
写得挺详细。
```

而应该把预期行为拆成可以观察的要求。

例如：

```json
{
  "skill_name": "paper-analysis",
  "evals": [
    {
      "id": 1,
      "prompt": "检查这篇论文的主要实验结论是否被 ablation 支持。",
      "expected_output": "Distinguish reported evidence from interpretation and inspect the relevant ablation tables.",
      "files": [
        "paper.pdf"
      ]
    }
  ]
}
```

进一步还可以定义 assertions：

```text
是否指出主要 claim？
是否定位对应实验表？
是否区分论文报告值和自己的推断？
是否检查 baseline？
是否检查 ablation？
是否没有把缺失实验写成已完成实验？
```

例如：

```json
{
  "text": "The answer identifies the paper's primary experimental claim.",
  "passed": true,
  "evidence": "..."
}
```

这里的 Eval Unit 不再是：

```text
Skill 文件写得好不好看
```

而是：

```text
Task Prompt
+
Input
+
Expected Behavior
+
Observable Result
```

真正值得比较的是：

```text
Agent + Skill
```

和某个 baseline 之间的差异。


#### 新 Skill 的 baseline：without skill

创建全新 Skill 时，最自然的实验是：

```text
same task
same model
same environment
same input

A:
without skill

B:
with skill
```

可以把第 \(i\) 个任务的结果记为：

\[
y_i^{\text{skill}}
\]

和：

\[
y_i^{\text{base}}
\]

如果任务最终可以判定 pass / fail，那么最简单的总体指标就是：

\[
P_{\text{skill}}
=
\frac{1}{N}
\sum_{i=1}^{N}
y_i^{\text{skill}}
\]

以及：

\[
P_{\text{base}}
=
\frac{1}{N}
\sum_{i=1}^{N}
y_i^{\text{base}}
\]

Skill 的 pass-rate uplift：

\[
\Delta P
=
P_{\text{skill}}
-
P_{\text{base}}
\]

例如：

```text
without skill
6 / 10 pass
→ 60%

with skill
8 / 10 pass
→ 80%
```

那么：

\[
\Delta P = +20\text{ pp}
\]

这里是：

```text
percentage points
```

不是：

```text
提升 20%
```

相对提升实际上是：

\[
\frac{0.8 - 0.6}{0.6}
\approx 33.3\%
\]

技术笔记里最好把这两种表达分开。


#### 修改旧 Skill 时，baseline 又不同

如果任务不是：

```text
从零创建 Skill
```

而是：

```text
优化已有 Skill
```

那么 baseline 更合理的是旧版本：

```text
old Skill
vs
new Skill
```

Anthropic 当前 `skill-creator` 会在修改前保存旧 Skill snapshot，再让相同 test case 分别运行：

```text
old_skill/
new_skill/
```

因此可以回答：

```text
这次修改到底改善了什么？
```

而不是只比较：

```text
有 Skill
vs
没 Skill
```

这两个实验回答的问题不同：

```text
with Skill vs without Skill
→ 这个 Skill 本身有没有 marginal utility？

new Skill vs old Skill
→ 这次修改有没有带来 improvement？
```

如果混在一起，就可能出现这种错误判断：

```text
New Skill pass rate = 80%
Without Skill = 50%

于是宣布：
新版本很好。
```

但旧版本其实：

```text
Old Skill = 90%
```

这次修改反而产生了 regression。


#### 为什么每个 Eval 最好运行在独立 Context

Skill evaluation 还有一个和普通 unit test 不太一样的问题：

```text
LLM Context 会泄漏前一个 test 的信息。
```

假设顺序跑：

```text
Eval 1
→ 告诉 Agent 正确做法

Eval 2
→ Context 里仍然保留 Eval 1 的 correction

Eval 3
→ Agent 已经知道你在检查什么
```

后面的任务就不再是独立样本。

因此 Anthropic 当前 `skill-creator` 在具备 subagent 能力的环境中，会让不同 eval run 使用独立 Agent context，并行运行。

可以画成：

```text
               Eval Harness
                    │
        ┌───────────┼───────────┐
        ↓           ↓           ↓
      Eval 1      Eval 2      Eval 3
        │           │           │
   fresh agent  fresh agent  fresh agent
        │           │           │
   with/base    with/base    with/base
```

这里并行只是顺带减少等待时间。

更关键的是：

```text
clean context
```

这样结果不会因为执行顺序而彼此污染。

这和 Agent Eval 中经常强调的：

```text
task isolation
```

是同一类要求。


### 3.2 Skill Creator 当前到底测什么

如果只看 Anthropic 2026 年 3 月的博客，会看到：

```text
eval
benchmark
multi-agent
comparison
description optimization
```

几个概念。

直接看当前 `anthropics/skills` 仓库里的 `skill-creator/SKILL.md`，整个实现会更具体。

它现在不是：

```text
输入需求
↓
吐出 SKILL.md
```

而是一套迭代流程：

```text
Capture Intent
      ↓
Draft Skill
      ↓
Create realistic eval prompts
      ↓
Run with-skill + baseline
      ↓
Grade objective assertions
      ↓
Human review
      ↓
Aggregate benchmark
      ↓
Analyze failures
      ↓
Modify Skill
      ↓
New iteration
```

对于一个新 Skill，目录大致会逐渐形成：

```text
my-skill/
├── SKILL.md
└── evals/
    └── evals.json

my-skill-workspace/
├── iteration-1/
│   ├── eval-.../
│   │   ├── with_skill/
│   │   │   ├── outputs/
│   │   │   ├── grading.json
│   │   │   └── timing.json
│   │   │
│   │   ├── without_skill/
│   │   │   ├── outputs/
│   │   │   ├── grading.json
│   │   │   └── timing.json
│   │   │
│   │   └── eval_metadata.json
│   │
│   ├── benchmark.json
│   └── benchmark.md
│
└── iteration-2/
    └── ...
```

这套结构里至少有四种不同证据，不能只盯 pass rate。


**第一类是最终产物。**

例如一个 PPT Skill，真正需要比较的是：

```text
with_skill/output.pptx

vs

without_skill/output.pptx
```

如果是 spreadsheet Skill：

```text
report.xlsx
```

如果是 coding Skill：

```text
patch
+
tests
```

有些结果不能被一个数字完整表达，所以 Anthropic 的 workflow 一直保留 human review。

例如写作风格：

```text
是不是更自然？
```

演示文稿：

```text
视觉层次是否合理？
```

或者：

```text
这两种调查报告里，哪份更符合团队实际需求？
```

硬写一个：

```json
{
  "assertion": "looks professional"
}
```

没有比人工评价更可靠。


**第二类是 objective assertions。**

能被程序确定性检查的事情，不应该完全交给 LLM grader。

例如：

```text
生成的 CSV 是否包含指定列？
JSON 是否满足 schema？
代码是否通过 pytest？
文件是否存在？
公式计算是否正确？
Hugo 是否能够 build？
```

直接：

```bash
pytest
python validate_output.py
hugo
```

更合适。

当前 `skill-creator` 也明确要求：可以程序化检查的 assertion，优先写脚本，而不是让 grader 肉眼判断。

LLM grader 更适合：

```text
回答有没有区分观察与推断？
是否覆盖用户要求的三个维度？
是否引用了提供材料中的证据？
```

这类无法用简单 deterministic predicate 判断的问题。


**第三类是运行成本。**

当前 benchmark 会同时记录：

```text
pass rate
time
tokens
```

并汇总：

```text
mean ± stddev
delta
```

为什么不能只看 pass rate？

假设两个版本：

| Configuration | Pass Rate | Tokens | Time |
| --- | ---: | ---: | ---: |
| Baseline | 82% | 20k | 30s |
| Skill | 83% | 75k | 95s |

这里不能简单写：

```text
Skill 提升了性能。
```

更完整的信息是：

```text
+1 pp pass rate
+
约 3.75× token
+
约 3.2× latency
```

到底值不值得取决于任务。

如果这是：

```text
一次性的关键合同审核
```

可能值得。

如果这是：

```text
每分钟执行几千次的低风险分类
```

很可能不值得。

Skill evaluation 因此更适合保留一个结果向量：

\[
E =
(
\Delta \text{Pass},
\Delta \text{Tokens},
\Delta \text{Latency},
\text{Failure Modes}
)
\]

而不是强行压成一个“Skill Score”。


**第四类是 failure pattern。**

假设：

```text
10 个 Eval
8 个 pass
```

平均值并不能说明失败集中在哪里。

可能是：

```text
简单任务 8/8
复杂任务 0/2
```

也可能是：

```text
普通 PDF 8/8
non-fillable form 0/2
```

这两种 Skill 的修改方向完全不同。

因此当前 `skill-creator` 还有一个 analyst pass，用来检查：

```text
哪些 assertions baseline 也总能通过？
→ test 没有 discriminative power

哪些 eval 方差特别大？
→ 可能 flaky

哪里 token 暴涨但质量没变？
→ procedure 可能冗余

哪些 failure 只出现在某类输入？
→ Skill coverage 有缺口
```

这里已经非常接近普通 eval engineering，而不只是 Prompt Engineering。


#### Blind A/B comparison：不知道哪个版本是谁

如果两个结果高度主观，还可以做 blind comparison。

例如：

```text
Output A
Output B
```

交给独立 comparator Agent，但不告诉它：

```text
A = old Skill
B = new Skill
```

让 comparator 根据预先定义的标准选择：

```text
A
B
Tie
```

然后再由 analyst 分析：

```text
为什么赢？
```

这样至少减少：

```text
“我刚改完，所以我觉得新版更好”
```

这种 confirmation bias。

不过当前 `skill-creator` 也没有把 blind comparator 设成每个 Skill 的必选步骤。它属于更严格比较时的 advanced mechanism；普通迭代通常仍以 human review + assertion benchmark 为主。


#### Description Optimization：触发本身也可以做 Eval

上一节提到：

```text
好的 Skill body
+
坏的 description
=
用户看不到这个 Skill
```

当前 `skill-creator` 已经把 description optimization 做成了单独流程。

首先构造 **20 个 trigger eval queries**：

```json
[
  {
    "query": "把这些实验日志整理成 Hugo 技术文章",
    "should_trigger": true
  },
  {
    "query": "Python dataclass 和 NamedTuple 有什么区别？",
    "should_trigger": false
  }
]
```

而且要求这些 query 尽量像真实用户输入，而不是：

```text
Please invoke the Hugo writing Skill.
```

这种测试题。

真实 query 可以包含：

```text
文件名
路径
缩写
具体业务背景
错别字
口语
不完整表达
```

因为真正要测试的是：

```text
用户自然说话时，
Skill 会不会被发现？
```

当前实现随后把 eval set 按：

```text
60% train
40% held-out test
```

拆分。

每条 trigger query 会重复运行 **3 次**，减少一次随机决策造成的误判，然后让模型根据失败样本提出新的 description。

默认优化循环最多：

```text
5 iterations
```

并且最后不是选择：

```text
train score 最高
```

的 description，而是根据：

```text
held-out test score
```

选 `best_description`。

这件事非常值得单独记下来，因为它把 Skill description 从：

```text
一句营销文案
```

变成了一个真正可以优化的 retrieval interface。

整个过程可以写成：

```text
Current Description
       ↓
20 trigger queries
       ↓
60 / 40 split
       ↓
run each query × 3
       ↓
FP / FN
       ↓
propose new description
       ↓
evaluate again
       ↓
up to 5 iterations
       ↓
choose by held-out score
```

它和修改 Skill body 是两个不同循环：

```text
Description Eval
→ selection quality

Task Eval
→ execution quality
```

一个 Skill 至少要同时通过这两个入口。


### 3.3 Capability Uplift 与 Encoded Preference

Anthropic 在更新 Skill Creator 时还给出了一个很有用的分类：

```text
Capability uplift skill

vs

Encoded preference skill
```

它解释了为什么不同 Skill 的 Eval 目标不能完全一样。


**Capability uplift** 解决的是：

```text
Base Model
本来不会
或者
做得不稳定
```

Skill 注入一些额外技术以后：

```text
Base Model
+
Skill
→ 能稳定完成
```

Anthropic 自己的 document creation Skills 就属于这类。

例如：

```text
复杂 PDF 操作
高质量 presentation
特定 document transform
```

Skill 中可能编码模型默认不会主动采用的：

```text
操作技巧
脚本
布局方式
验证过程
```

这种 Skill 的核心 Eval 是：

\[
P(\text{with Skill})
>
P(\text{without Skill})
\]

如果模型升级以后变成：

```text
without Skill
≈
with Skill
```

这不代表 Skill “坏了”。

可能是：

```text
模型已经把原来需要外部 procedure 才能完成的能力学会了。
```

此时继续加载 Skill 反而可能只是：

```text
增加 Context
增加 latency
限制新模型本来更好的策略
```

所以 Capability Uplift Skill 需要随模型版本重新做 ablation。


**Encoded Preference** 则不同。

例如团队要求每周生成状态报告：

```text
1. 先查 Linear 的当前 milestone；
2. 再查 GitHub merged PR；
3. 查本周 incidents；
4. 按固定模板整理；
5. blockers 必须放第一段；
6. 不允许省略 unresolved owner。
```

Claude 本来就会：

```text
读 Linear
读 GitHub
写 summary
```

Skill 并没有给模型增加全新的基础能力。

它编码的是：

```text
我们团队希望事情怎么做
```

也就是：

```text
organizational workflow
SOP
style
policy
preference
```

对于这种 Skill：

```text
without Skill
```

甚至可能已经能得到一份内容不错的周报。

因此只测：

```text
最终答案看起来好不好
```

会漏掉真正目标。

更应该测：

```text
有没有按要求读取 milestone？
有没有遗漏 incident？
blocker 是否放在规定位置？
是否保留 owner？
是否遵循模板？
```

也就是：

```text
workflow fidelity
```

所以两类 Skill 可以整理成：

| | Capability Uplift | Encoded Preference |
| --- | --- | --- |
| Base model | 不会或不稳定 | 通常已经会基本任务 |
| Skill 主要增加 | technique / capability | SOP / preference / policy |
| 主要 Eval | task success uplift | workflow fidelity |
| 模型升级影响 | 可能逐渐失去必要性 | 通常更持久 |
| 常见风险 | Skill 变成冗余 scaffolding | SOP 已过时却继续执行 |

这两个类别还揭示了 Skill 的一个生命周期问题：

```text
Skill
不是写完以后永久正确的文档。
```

它依赖至少三样东西：

```text
Model
Harness
Environment
```

可以写成：

\[
Q_{\text{skill}}
=
f(
S,
M,
H,
E,
D
)
\]

其中：

```text
S = Skill
M = Model
H = Harness
E = Environment
D = Task Distribution
```

同一个 `SKILL.md`：

```text
在 Claude A 上有效
```

不能直接推出：

```text
在 Claude B 上也有效
```

更不能推出：

```text
在另一个 Harness 上仍然有效
```

因为模型可能：

```text
更会推理了
更会用 Tool 了
更容易 under-trigger
更倾向自主探索
```

Harness 也可能改变：

```text
Tool definitions
Context policy
sandbox
permission
filesystem
subagent
```

环境本身还可能升级：

```text
API v1 → v2
framework 1.x → 2.x
旧 CLI flag 被删除
```

这也是为什么 Skill 需要 regression eval，而不能被当作静态知识库。


### 3.4 Skills 到底有没有用？SkillsBench 与 SWE-Skills-Bench 给出了不同答案

到这里自然会出现一个更大的问题：

> 如果 Skill 可以测试，那么大规模测试以后，结果到底怎么样？

2026 年出现的两个 benchmark 给出了一个很有意思的组合答案：

```text
Skills 可以显著帮助 Agent

同时：

大量真实 Skill 并没有帮助 Agent
```

这两句话并不矛盾。


#### SkillsBench：高质量 curated Skills 的平均收益很明显

2026 年 2 月发布的 **SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks** 做了一组规模更大的实验。

它包含：

```text
86 tasks
11 domains
7 agent-model configurations
7,308 trajectories
```

每个任务比较三种设置：

```text
No Skills

Curated Skills

Self-generated Skills
```

结果里最醒目的数字是：

```text
Curated Skills
平均 pass rate
+16.2 percentage points
```

但这个平均值背后差异非常大。

不同 domain 的提升从：

```text
Software Engineering
+4.5 pp
```

到：

```text
Healthcare
+51.9 pp
```

变化明显。

而且论文报告：

```text
16 / 84 tasks
加入 Skill 后出现 negative delta
```

也就是即使 Skill 是 curated 的，也不存在：

```text
加 Skill
→ performance 单调上升
```

这种规律。

SkillsBench 还有两个对 Skill Engineering 很有价值的结果。

一个是：

```text
Self-generated Skills
平均没有带来收益。
```

模型能够：

```text
消费高质量 procedural knowledge
```

不意味着它天然能够：

```text
自己写出同样高质量的 procedural knowledge。
```

第二个是 Skill 粒度。

论文发现 focused Skills——通常集中在 **2–3 个 modules**——比试图覆盖所有内容的 comprehensive documentation 表现更好。

这和前面 Progressive Disclosure 的工程直觉一致：

```text
更多 instruction
≠
更多有效信息
```

过大的 Skill 可能同时带来：

```text
无关规则
冲突指导
Context competition
过度约束
```

SkillsBench 甚至观察到：

```text
较小模型 + Skills
```

在部分任务上可以达到：

```text
较大模型 without Skills
```

的水平。

于是它支持这样一个结论：

> 对某些任务，经过人工整理的 procedure 本身就是 inference-time capability 的组成部分。

但还不能推出：

> 随便下载一个 `SKILL.md` 都能获得 +16.2 pp。


#### SWE-Skills-Bench：把公开 Skill 放回真实软件仓库以后，平均收益只剩 +1.2%

一个月后的 **SWE-Skills-Bench: Do Agent Skills Actually Help in Real-World Software Engineering?** 专门把问题收窄到软件工程。

它没有自己设计一组理想化的 Skill，而是选择：

```text
49 public SWE skills
```

再与固定 commit 的真实 GitHub repository 和 requirement document 配对。

总计大约：

```text
565 task instances
6 SWE subdomains
```

而且验收不是让 Judge 看一眼代码说：

```text
looks correct
```

而是把 requirement 里的 acceptance criteria 映射成 execution-based deterministic tests。

结果与 SkillsBench 的整体均值差别很大：

```text
39 / 49 Skills
pass rate 没有提升
```

所有 Skill 的平均 gain：

```text
+1.2%
```

同时 token cost 的变化范围很夸张。

最极端的情况：

```text
token overhead
+451%
```

但：

```text
pass rate
没有变化
```

当然，也不是所有 Skill 都失败。

论文找到：

```text
7 个 specialized Skills
```

具有比较明确的收益，最高：

```text
+30%
```

但也有：

```text
3 个 Skills
```

让结果变差，最差达到：

```text
-10%
```

论文分析其中一个重要原因是：

```text
version-mismatched guidance
```

Skill 教 Agent：

```text
按照某个 framework/API 的旧版本这样做
```

而实际 repository 使用的是：

```text
另一个版本
```

于是：

```text
没有 Skill
→ 模型根据当前代码自己推断

有 Skill
→ 模型更加坚定地执行已经过时的 procedure
```

结果反而更差。

这类 failure 很有代表性，因为它说明 Skill 并不是纯粹的：

```text
额外知识
```

它还会改变 Agent 的 action prior。

可以粗略写成：

\[
\pi(a\mid s)
\quad\rightarrow\quad
\pi(a\mid s,\text{Skill})
\]

如果 Skill 正确：

```text
probability mass
→ 推向更好的 action
```

如果 Skill 过时：

```text
probability mass
→ 反而被推向错误 action
```

因此 Skill 的价值不只取决于：

```text
写得详细不详细
```

还取决于：

```text
是否和当前 environment 相容。
```


#### 两个 Benchmark 其实回答了不同的问题

把结果放在一起看，会比争论：

```text
SkillsBench 说 Skills 有用
SWE-Skills-Bench 说 Skills 没用
```

更有意义。

| | SkillsBench | SWE-Skills-Bench |
| --- | --- | --- |
| 主要问题 | curated procedural knowledge 能否帮助 Agent | 公开现成 SWE Skills 在真实任务里有没有 marginal utility |
| Skill 来源 | benchmark curated + self-generated | 49 个 public SWE skills |
| Task | 86 tasks / 11 domains | ~565 instances / 6 SWE subdomains |
| 验证 | deterministic verifiers | requirement-driven execution tests |
| 平均结果 | curated +16.2 pp | +1.2% |
| 主要负面结果 | 16/84 tasks negative；self-generated 无平均收益 | 39/49 无提升；3 个退化 |
| 额外成本 | 关注不同 Skill 条件 | token overhead 最高 +451% |
| 最值得记住的变量 | Skill quality / domain / granularity | specialization / compatibility / version fit |

SkillsBench 更接近问：

> **如果有人真的为任务整理了一份高质量 procedure，它能不能帮助 Agent？**

答案是：

```text
经常可以，而且平均提升明显。
```

SWE-Skills-Bench 更接近问：

> **如果我从网上拿一个公开 Skill 塞进真实工程 Agent，它是不是天然有用？**

答案是：

```text
大多数情况下不能直接假定。
```

这两者合起来，反而给出了比：

```text
Agent Skills 很强
```

更有用的工程判断。


#### 我现在会怎样判断一个 Skill 值不值得保留

如果以后真的维护一个 Skill Library，我不会只看：

```text
Skill 有多少个
GitHub star 有多少
SKILL.md 有多详细
```

至少要记录四类信息：

```text
1. Selection
应该触发时触发了吗？
不该触发时有没有误触发？

2. Quality
with-skill 的任务成功率是否真的高于 baseline？

3. Cost
token / latency / tool calls 增加了多少？

4. Compatibility
当前 model / harness / dependency version 下还成立吗？
```

可以把它写成：

```text
Skill Registry
│
├── trigger eval
├── task eval
├── supported environment
├── benchmark history
└── known failure modes
```

一个 Skill 如果出现：

```text
ΔPass ≈ 0
ΔTokens >> 0
```

就应该考虑删掉、缩短或者提高触发门槛。

如果：

```text
ΔPass < 0
```

则不能因为：

```text
“这是官方 Skill”
```

或者：

```text
“以前挺好用”
```

继续保留。

如果：

```text
某一小类任务 +25 pp
其他任务无变化
```

更合理的方向可能不是把 Skill 扩成一个“大而全”的工程百科，而是让 description 更精确，只在这类任务上触发。

这也解释了为什么 Skill Library 一旦继续增长，新的问题会很快出现。

假设只有：

```text
3 Skills
```

模型自己选通常还比较简单。

当库里出现：

```text
100 Skills
500 Skills
1000 Skills
```

以后，就不再只是：

```text
一个 description 写得好不好
```

的问题了。

真实任务还可能同时需要：

```text
Skill A
+
Skill B
+
Skill C
```

并且它们之间存在：

```text
prerequisite
dependency
conflict
ordering
```

例如：

```text
先识别数据库版本
        ↓
再选择 migration Skill
        ↓
再执行 schema inspection
        ↓
再做 rollback verification
```

这时 flat Skill retrieval 开始不足。

Skill Engineering 的问题也随之从：

```text
How to write one good Skill?
```

变成：

```text
How to retrieve,
compose,
order,
verify,
and repair many Skills?
```

接下来 GraSP 和 SkillGraph 要处理的，就是这一层。

## 4. 当 Skill 从几个增长到几百个，问题变成了 Skill Orchestration

前面几节一直把一个 Skill 当成基本单位：

```text
Task
  ↓
Skill Discovery
  ↓
SKILL.md
  ↓
references / scripts
  ↓
execute
```

只有几个 Skill 时，这种视角已经够用。

例如：

```text
paper-review
hugo-writing
code-review
```

用户要求分析论文，选：

```text
paper-review
```

用户要求整理博客，选：

```text
hugo-writing
```

问题主要是：

```text
description 写得准不准？
Skill body 写得好不好？
```

但真实任务并不总能由一个 Skill 完成。

例如一个 coding task：

```text
升级数据库 schema，
迁移旧数据，
修改 API，
补测试，
最后部署。
```

可能同时涉及：

```text
schema-migration
data-backfill
api-change
test-generation
deployment
```

假设 retrieval 已经非常准确，把这五个 Skill 全部找出来：

```text
Retrieved Skills

- schema-migration
- data-backfill
- api-change
- test-generation
- deployment
```

问题还没有解决。

因为这个列表没有告诉 Agent：

```text
谁依赖谁？

哪些 Skill 必须先执行？

哪些可以并行？

哪个 Skill 的输出要作为另一个 Skill 的输入？

某一步失败以后，后面哪些步骤失效？

是否需要重新规划整条路线？
```

比如：

```text
schema-migration
       ↓
data-backfill
       ↓
switch-read-path
       ↓
verification
       ↓
remove-old-schema
```

这里如果：

```text
data-backfill
```

失败，那么：

```text
switch-read-path
```

不应该继续。

但如果一个完全无关的：

```text
generate-release-note
```

节点失败，也没有必要把已经完成的数据库迁移全部作废。

这类问题已经超出了：

```text
Skill Retrieval
```

本身。

Retrieval 只能回答：

> 哪些 Skill 和任务相关？

现在还需要回答：

> 这些 Skill 之间是什么结构？

2026 年开始出现的一批工作，就是在这一层引入：

```text
Skill Graph
```

不过“Skill Graph”这个词也不能直接当成一种统一架构。

不同论文实际上在解决不同问题：

```text
GraSP
→ 把当前任务取回的 Skill
  编译成一次任务使用的 executable DAG

SkillGraph
→ 把长期 Skill Library 本身
  维护成一张会随 trajectory 和 RL 演化的图
```

两者都使用 graph，但 graph 的生命周期、用途和更新方式并不一样。


### 4.1 Skill Library 越大，为什么不等于 Agent 越强

上一节 SkillsBench 已经出现一个重要结果：

```text
focused 2–3 Skills
```

通常比一次性提供大量综合说明更有效。

因此：

\[
|\mathcal{S}| \uparrow
\]

并不意味着：

\[
P(\text{success}) \uparrow
\]

甚至可能出现：

\[
|\mathcal{S}| \uparrow
\quad\Rightarrow\quad
P(\text{success}) \downarrow
\]

原因至少有两层。


#### 第一层：Selection Problem

假设 Skill Library 有：

```text
500 Skills
```

任务实际只需要：

```text
3 Skills
```

如果全部提供给模型：

```text
500 Skill descriptions
+
大量 SKILL.md
```

不仅 Context 成本增加，模型还要自己从大量相近 procedure 里判断：

```text
到底哪个适合？
```

所以我们需要 retrieval：

```text
Task
  ↓
Retriever
  ↓
500 Skills
  ↓
Top-K Skills
```

例如：

```python
retrieved = skill_retriever.search(
    query=task,
    top_k=5,
)
```

这解决：

```text
Skill Selection
```

但还没有解决下一层。


#### 第二层：Composition Problem

假设 retrieval 已经找到了正确的 5 个 Skill：

```text
A
B
C
D
E
```

它们真实的关系可能是：

```text
      A
     / \
    B   C
     \ /
      D
      |
      E
```

但 flat retrieval 给模型看到的是：

```text
[A, B, C, D, E]
```

这个表示丢失了：

```text
A must precede B

A must precede C

B and C can proceed independently

D requires both B and C

E requires D
```

于是 Agent 还得在运行时重新推导这张图。

如果 Skill 描述本身已经比较复杂，模型实际上同时承担：

```text
Skill Selection
+
Dependency Inference
+
Planning
+
Execution
+
Failure Recovery
```

其中 Selection 已经交给 Retriever，Dependency 却又偷偷塞回了模型。

这也是 GraSP 论文提出的一个具体缺口：

```text
Retrieval
回答：
What skills are relevant?

Execution
回答：
Do this step now.

中间还缺：

Compilation
回答：
How do these skills depend on each other?
```

所以更完整的 Skill runtime 开始变成：

```text
Skill Library
     ↓
 Retrieval
     ↓
Selected Skills
     ↓
 Compilation
     ↓
Execution Structure
     ↓
 Runtime
```

注意这里的：

```text
Compilation
```

暂时不是传统意义的：

```text
source code
→ machine code
```

而是：

```text
flat procedural units
→ structured executable representation
```

后面讲 SkVM 和 SkillRAE 时，还会看到另外两种“Skill Compilation”。


### 4.2 GraSP：把 retrieved Skills 编译成可执行 DAG

2026 年 4 月的 **GraSP: Graph-Structured Skill Compositions for LLM Agents** 把问题定义得很直接：

```text
Skill Retrieval
       ↓
flat skill set
       ↓
? missing layer
       ↓
Execution
```

GraSP 在中间补了一层：

```text
DAG Compilation
```

整个流程可以简化成：

```text
Task + Current State
          ↓
Memory-conditioned Retrieval
          ↓
   Retrieved Skills
          ↓
      Compile
          ↓
   Typed Skill DAG
          ↓
 Execute + Verify
          ↓
 Local Repair
```

论文把一次任务的 GraSP 表示成：

\[
G=(V,E)
\]

其中：

```text
V
→ instantiated skill invocation

E
→ dependency
```

节点不是抽象的：

```text
“有一个 database Skill”
```

而是一次具体 invocation。

一个节点还会携带：

```text
skill schema
bound arguments
preconditions
effects / postconditions
verifier
execution status
confidence
repair budget
```

可以近似想成：

```python
SkillNode(
    schema="deploy_service",
    args={
        "service": "payment-api",
        "target": "staging",
    },
    preconditions=[
        "image_built",
        "tests_passed",
    ],
    effects=[
        "staging_deployed",
    ],
    verifier="check_staging_health",
)
```

这与普通：

```text
Skill Name + Description
```

相比多了一层 runtime semantics。


#### GraSP 的三种 Edge：state、data、order

GraSP 没有只使用：

```text
A → B
```

这种没有语义的边。

它定义三种 dependency。


**State Edge**

表示：

```text
A 的 effect
满足
B 的 precondition
```

例如：

```text
authenticate
     │
     │ state
     ↓
checkout
```

如果：

```text
authenticate
```

没有成功，那么：

```text
logged_in = true
```

这个状态没有建立，`checkout` 就不能运行。


**Data Edge**

表示：

```text
A 的 output
绑定到
B 的 input
```

例如：

```text
build_image
     │
     │ output: image_id
     ▼
deploy_image
```

可以抽象成：

```python
image = build_image(...)
deploy_image(image=image)
```

如果 `build_image` 没产生合法 `image_id`，后面的 deployment 不是“最好等等”，而是输入本身不存在。


**Order Edge**

表示一种 precedence constraint：

```text
A 应该先于 B
```

但不一定存在硬 state/data dependency。

例如：

```text
run_targeted_tests
        ↓
run_full_regression
```

从技术上也许可以反过来执行，但经验上通常先跑 targeted test 更省成本。

GraSP 把：

```text
state
data
```

看作更硬的依赖，而：

```text
order
```

可以在 repair 时被重新连接。

所以：

```text
DAG
```

不是为了画图。

它使 dependency 本身成为 runtime 可以检查的结构。


#### Flat Sequence 是 DAG 的特殊情况

假设传统 Skill Agent 得到：

```text
A → B → C → D → E
```

这实际上也是 DAG，只不过只有：

```text
order edge
```

真正有价值的是图可以表示：

```text
        A
       / \
      B   C
       \ /
        D
```

这意味着：

```text
B
```

和：

```text
C
```

可能不存在彼此依赖。

这种表示至少带来两件事。

第一，依赖范围更准确。

第二，失败传播范围可以被限制。


#### 不只是执行：每个 Node 前后都做 Verification

GraSP 不是：

```text
DAG
→ 按拓扑序把节点调用一遍
```

它执行每个 ready node 时会检查：

```text
1. Precondition

2. Execute Skill

3. Postcondition / Verifier

4. Mark Verified
```

可以粗略写成：

```python
for node in topological_order(graph):

    if not check(node.preconditions, state):
        repair(node, reason="precondition")
        continue

    result = execute(node)

    if not node.verifier(result):
        repair(node, reason="postcondition")
        continue

    node.status = "verified"
```

这和前面讲 Evaluator / Verification 时的思想是一致的：

```text
动作已经调用
≠
目标状态已经成立
```

例如：

```text
deploy()
```

Tool 没报异常，并不证明：

```text
service healthy
```

还需要 verifier：

```text
health endpoint
deployment status
smoke test
```

GraSP 把 verifier 直接绑定到了 node 上。


#### Failure 发生以后，不一定重做整条 Plan

Flat sequence 的问题可以画成：

```text
A ✓
↓
B ✓
↓
C ✗
↓
D ?
↓
E ?
```

一个简单 Agent 可能：

```text
C 失败
→ 重新让 LLM 规划剩余任务
```

甚至：

```text
重新生成整个 plan
```

GraSP 利用 DAG 判断：

```text
C 的 failure
到底影响哪些 descendant？
```

例如：

```text
          A ✓
         /   \
       B ✓   C ✗
       |      |
       D ✓    E
         \   /
           F
```

此时：

```text
B
D
```

分支已经验证完成。

`C` 失败不应该把它们一起撤销。

真正受影响的是：

```text
C
E
F
```

因此 repair 可以限制在局部子图。

论文把 flat replanning 的规模写成：

\[
O(N)
\]

而局部图修复建模为：

\[
O(d^h)
\]

其中可以把 \(d^h\) 理解为由局部图分支和 repair neighborhood 深度限制出的受影响范围。

这里不要把公式理解成：

> GraSP 在任何环境里真实运行时间都严格从线性复杂度变成指数复杂度。

论文表达的是 **replanning scope**：flat plan 可能重新考虑整条长度为 \(N\) 的 trajectory，而 graph repair 只展开失败节点附近受约束的局部 neighborhood。


#### 五种 Local Repair Operator

GraSP 没有只写：

```text
如果失败，让 LLM 再想想。
```

论文定义了五类 graph transformation。


**1. Rebind**

Skill 本身没错，只是参数错了：

```text
deploy(service="paymant")
```

发现实际 service：

```text
payment
```

于是：

```text
same node
new arguments
```


**2. InsertPrereq**

当前节点缺少 precondition。

例如：

```text
checkout
```

要求：

```text
authenticated
```

但当前没登录。

于是图从：

```text
checkout
```

修成：

```text
login
  ↓
checkout
```


**3. Substitute**

当前 Skill 不适合，但存在可以保持 downstream interface 的替代 Skill。

例如：

```text
download-with-curl
```

在当前环境失败，可以替换为：

```text
download-with-browser
```

只要后续仍能拿到所需输出。


**4. Rewire**

Skill 本身可能没问题，依赖图画错了。

例如：

```text
A → B → C
```

后来发现真正关系应该是：

```text
A ──→ C
 \
  → B
```

于是局部修改 edge。


**5. Bypass**

某个节点原计划要做，但当前 state 已经满足它要建立的 downstream requirement。

例如计划：

```text
install_dependency
```

运行时发现 dependency 已安装且版本符合要求，那么该节点可以跳过。

这些 operator 的作用不是说：

```text
所有 failure 都能修复
```

而是把过去模糊的：

```text
replan
```

分成可以诊断的 failure class。

如果局部 repair 仍失败，GraSP 才升级到：

```text
global replanning
```

或者：

```text
reactive fallback
```


#### Retrieval Confidence 低时，不强行使用 Skill Graph

GraSP 还有一个很容易被忽略的设计：不是任何任务都必须进入 DAG runtime。

它会根据：

```text
memory similarity
retrieval agreement
top-skill margin
goal coverage
```

等信号计算 retrieval confidence。

如果 confidence 太低：

```text
retrieved skills 可能就不可靠
```

系统可以退回：

```text
ReAct-style reactive control
```

这与 SkillsBench 里：

```text
Skill 有时反而产生负收益
```

其实是同一个问题。

Graph Orchestration 不能修复：

```text
一开始取回的全是错误 Skill
```

所以 runtime 还需要知道：

```text
什么时候不要相信 Skill Library。
```


#### GraSP 的实验结果要怎样读

论文在：

```text
ALFWorld
ScienceWorld
WebShop
InterCode
```

四类 interactive benchmark 上测试了 8 个 LLM backbone，并和：

```text
ReAct
Reflexion
ExpeL
ReAct + Skills
```

等方法比较。

论文报告最高：

```text
+19 reward points
```

以及最多：

```text
-41% environment steps
```

这里比绝对数字更值得关注的是 baseline：

```text
ReAct + Skills
```

已经拥有同样的 Skill Library 和 episodic memory。

GraSP 与它之间的主要区别不是：

```text
有 Skill
vs
没 Skill
```

而是：

```text
flat skills
vs
compiled skill graph
```

所以这组实验真正试图验证的是：

> 当 Skill 已经存在时，把它们组织成显式 dependency structure 是否比直接扔给 Agent 更有效？

论文结果支持这一点，但仍然是在 ALFWorld、ScienceWorld、WebShop 和 InterCode 这些 benchmark 上得到的 preprint 实验结果，不能直接外推成：

```text
生产 Coding Agent 一律应该把 Skill 编译成 DAG。
```

如果真实任务只有：

```text
1–2 个独立 Skill
```

或者 dependency 本身非常简单，DAG compiler、verifier 和 repair runtime 的成本可能没有必要。


### 4.3 SkillGraph：图不只用于执行，也参与 Skill Library 演化

GraSP 解决的是：

```text
这一轮任务
取回几个 Skill 以后
怎样组织和执行？
```

2026 年 5 月的 **SkillGraph: Skill-Augmented Reinforcement Learning for Agents via Evolving Skill Graphs** 又把图的生命周期往前推了一层。

它处理的问题是：

```text
Skill Library 本身
为什么还要是一张 flat list？
```

传统 Skill Library 可以写成：

```text
Skill 1
Skill 2
Skill 3
...
Skill N
```

每一个 Skill 独立保存：

```text
description
procedure
embedding
usage stats
```

新任务来了以后按 semantic similarity 取：

\[
\operatorname{TopK}
(
\operatorname{sim}(q,s_i)
)
\]

这种方法的问题是，skill-to-skill relation 没被保存。

比如任务：

```text
把一个脏锅加热后放进柜子。
```

可能需要：

```text
locate object
↓
pick up
↓
clean
↓
heat
↓
place
```

单纯 semantic retrieval 可以找到：

```text
clean
heat
place
```

但仍然不知道：

```text
clean 应该在 heat 之前
```

以及：

```text
这些技能过去是不是经常组合成功。
```

SkillGraph 于是直接把长期 Skill Library 表示成：

\[
G=(V,E)
\]

其中：

```text
V
→ reusable skills

E
→ relation between skills
```

这里和 GraSP 的第一个关键差别已经出现：

```text
GraSP Node
→ task-specific instantiated skill invocation

SkillGraph Node
→ persistent reusable skill
```


#### 三种 Edge：prerequisite、enhancement、co-occurrence

SkillGraph 使用三类主要关系。


**Prerequisite**

表示：

```text
A 是 B 的前置技能
```

例如：

```text
pick_up
   ↓ prerequisite
heat_object
```

如果没有先持有物体，就不能加热。


**Enhancement**

不一定是严格前置条件，但 A 会提高 B 的效果。

例如某个一般性的：

```text
verify_current_state
```

策略可能不是：

```text
search_product
```

的逻辑前置条件，却能提高后续 web interaction 的稳定性。


**Co-occurrence**

表示：

```text
A 和 B 在成功 episode 中经常共同出现
```

它不直接声称：

```text
A causes B
```

而是在记录经验关联。

因此：

```text
prerequisite
→ stronger dependency semantics

enhancement
→ beneficial relation

co-occurrence
→ empirical association
```

SkillGraph 还给 edge 分配：

\[
w(e)\in[0,1]
\]

表示关系强度。

所以 Library 不再只有：

```text
有哪些 Skill
```

还开始记录：

```text
哪些 Skill 之间有关系
关系是什么类型
这种关系目前有多可信
```


#### Retrieval 不再返回孤立 Top-K，而是 Ordered Skill Subgraph

传统 retrieval：

```text
Task
 ↓
Embedding Search
 ↓
Skill A
Skill D
Skill G
```

SkillGraph 则做 graph-aware retrieval。

论文实现里大致包括：

```text
Seed Selection
       ↓
Backward BFS
       ↓
Forward Beam Search
       ↓
Union
       ↓
Topological Ordering
       ↓
Ordered Skills
```

为什么同时向后和向前查？

假设 semantic retrieval 找到：

```text
heat_object
```

作为 seed。

向后查 prerequisite 可能发现：

```text
pick_up
```

如果只按 semantic similarity：

```text
用户 query 重点在“加热”
```

那么 `pick_up` 与 query 的文本相似度可能并不高，却是实际执行不可缺的步骤。

反过来向前展开可能发现：

```text
heat_object
      ↓
place_object
```

这些 relation 来自已有 graph，而不是重新要求模型在 prompt 中临时推导。

所以最后取回的不只是：

```text
relevant skills
```

而是：

```text
dependency-aware ordered skills
```


#### SkillGraph 的 graph 不是静态知识图谱

如果只是：

```text
人工提前把所有 Skill 的依赖画出来
```

它仍然是一套静态 metadata。

SkillGraph 更进一步的地方在于：

```text
Graph
```

和：

```text
Policy
```

一起在 RL loop 中演化。

整个闭环可以压成：

```text
Skill Graph
    ↓
Graph-aware Retrieval
    ↓
Policy
    ↓
Environment
    ↓
Rollout
    ↓
Reward / Trajectory
    ↓
Graph Evolution
    ↓
Skill Graph
```

同时：

```text
Rollout
↓
GRPO
↓
Policy Update
```

所以形成：

```text
better graph
→ better retrieved context
→ better policy trajectory
→ better graph evidence
```


#### Node-Level Evolution：Insert / Merge / Split / Deprecate

Skill Library 的维护不再只是：

```text
不断 append 新 Skill。
```

SkillGraph 定义了几种 node-level 操作。


**Insert**

当 trajectory 暴露出一个新的、可以复用的 strategy 时，可以加入新 Skill。

```text
trajectory
   ↓
teacher model
   ↓
new reusable skill
   ↓
graph node
```


**Merge**

两个 Skill 如果实际上编码的是高度重叠策略，可以合并。

论文实现会参考它们 graph neighborhood 的 overlap。

设：

\[
N(v)
\]

表示一个 Skill 的 neighbor set，则可以使用 Jaccard similarity：

\[
J(N(v_i),N(v_j))
=
\frac{
|N(v_i)\cap N(v_j)|
}{
|N(v_i)\cup N(v_j)|
}
\]

论文实验配置使用：

\[
\tau_{\text{merge}}=0.85
\]

作为 merge threshold。

这不是 Agent Skills 标准的一部分，只是 SkillGraph 论文里的实验设计。


**Split**

另一个问题是：

```text
一个 Skill 写得太大。
```

例如：

```text
web-shopping
```

里面同时混着：

```text
search
filter
compare
checkout
```

整体使用很多，但成功率一直一般。

SkillGraph 可以把这种 broad Skill 拆成多个更 focused 的子技能，再重新建立 prerequisite relation。


**Deprecate**

某个 Skill：

```text
经常被 retrieve
```

但：

```text
长期失败
```

就不应该一直留在 active Library 里。

论文实验设置中，如果某 Skill：

```text
usage >= 20
```

而 empirical success rate：

```text
< 0.15
```

则进入 deprecation 条件。

这个数字同样只是论文具体配置，不能拿来变成：

```text
生产 Skill Library 的通用规则。
```

真正值得借鉴的是机制：

```text
Skill 有 usage stats
Skill 有 success stats
Skill 可以退出
```

而不是：

```text
Skill 一旦创建就永久存在。
```


#### Edge-Level Evolution：关系也会失效

SkillGraph 不只更新 node。

edge 本身也会随 trajectory 改变。


**Path Reinforcement**

如果一次成功 trajectory 使用了：

```text
A → B → C
```

这些 edge 获得正向证据：

\[
w(e)
\leftarrow
\min(w(e)+\alpha,1)
\]


**Co-occurrence Discovery**

如果：

```text
A
B
```

以前没有 relation，但反复在成功 episode 中一起出现，可以新建：

```text
co_occurrence edge
```


**Decay and Pruning**

旧关系也可能过时。

所以 edge weight 会进行 decay：

\[
w(e)
\leftarrow
\gamma w(e)
\]

低于阈值后被 prune。

这点和 Memory 系统很像：

```text
新的成功经验
→ reinforce

长期没有证据
→ decay

持续失败
→ deprecate
```

Skill Library 因此开始从：

```text
static prompt files
```

向：

```text
experience-conditioned procedural memory
```

靠近。


#### Progressive Unlocking：不是训练一开始就开放所有复杂 Skill

SkillGraph 还有一个 curriculum-style 的设计。

Graph 中的 Skill 可以根据 prerequisite / enhancement relation 计算 topological level：

```text
Level 0
基础 Skill

Level 1
依赖 Level 0

Level 2
依赖更低层 Skill
...
```

训练早期只激活：

```text
Level 0
```

当当前最高 active level 的平均成功率超过阈值，再解锁下一层。

论文实验中使用：

\[
\theta_{\text{unlock}}=0.6
\]

因此：

```text
基础技能还不稳定
→ 暂时不把更复杂组合塞给 Policy

基础技能达到 threshold
→ unlock next level
```

这相当于让 Skill Graph 同时承担一部分：

```text
curriculum
```

作用。


#### 这已经不是普通的 `SKILL.md` 管理了

到这里需要把一个边界说清楚。

Anthropic Agent Skills 标准里的 Skill：

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

本身没有规定：

```text
必须使用 graph
必须使用 RL
必须有 success statistics
必须自动 merge / split
```

SkillGraph 是建立在：

```text
reusable procedural knowledge
```

这个抽象之上的研究系统。

它研究的问题已经从：

```text
Skill 文件格式
```

变成：

```text
Agent 如何从 trajectory 学习、
组织、
检索、
维护 procedural knowledge。
```

因此文章里不能写成：

> Agent Skills 后来升级成 SkillGraph。

更准确的是：

> Agent Skills 形成可复用 procedure 这一工程抽象以后，研究工作开始探索：当 procedure 数量增长并且需要组合时，能否把它们表示成带关系、可演化的 graph。


#### SkillGraph 的实验里，Graph 各部分真的有用吗？

SkillGraph 使用：

```text
Qwen2.5-7B-Instruct
```

作为 base policy，并使用 teacher model 完成 skill distillation、SFT 数据生成和部分 graph evolution，再使用 GRPO 做 policy optimization。

实验覆盖：

```text
ALFWorld
WebShop

NQ
TriviaQA
PopQA
HotpotQA
2Wiki
MuSiQue
Bamboogle
```

也就是：

```text
interactive environment
+
single-hop search QA
+
multi-hop search QA
```

论文报告的主结果中：

```text
ALFWorld overall success
90.6%

WebShop success
84.4%
```

这些绝对值依赖它的训练、模型、数据和实验设置，本身不适合脱离论文直接宣传。

更有解释力的是 ablation。

例如 ALFWorld：

```text
SkillGraph
90.6

w/o Graph-aware Retrieval
59.4
```

下降：

```text
31.2 pp
```

这和 ALFWorld 本身有较强：

```text
prerequisite order
```

相符。

一个典型任务可能要求：

```text
find
→ pick
→ clean
→ heat
→ place
```

缺少 graph-aware retrieval，取到正确 Skill 也未必能建立正确顺序。

但 WebShop 的结果又不同。

论文中：

```text
SkillGraph
84.4

w/o Graph Structure
72.7

w/o Graph Evolution
70.3
```

这里 Graph Evolution 的影响尤其明显。

WebShop 的路径更加灵活：

```text
搜索词不唯一
筛选顺序不唯一
浏览路线不唯一
```

因此：

```text
哪几个 Skill 当前可靠
```

可能比：

```text
唯一正确的固定顺序
```

更重要。

这种 ablation 比一句：

```text
Graph 很重要
```

更有信息量：

> Graph 的价值并不是一个统一机制在所有环境里贡献相同，而是不同环境分别利用了 dependency ordering、retrieval 和 library evolution。


### 4.4 Skill Graph 解决的其实是三个不同问题

GraSP 和 SkillGraph 放在一起以后，可以把所谓：

```text
Skill Orchestration
```

继续拆成三层。


#### Selection：选哪些 Skill？

输入：

```text
Task
+
Skill Library
```

输出：

```text
Relevant Skills
```

最简单是：

```text
semantic retrieval
```

更复杂可以加入：

```text
episodic memory
graph relation
historical success
dependency expansion
```

这一层解决：

```text
不要把整个 Skill Library 都塞进 Context。
```


#### Composition：这些 Skill 怎样组合？

输入：

```text
Relevant Skills
```

输出：

```text
Execution Structure
```

例如：

```text
      A
     / \
    B   C
     \ /
      D
```

需要显式表达：

```text
precondition
effect
data dependency
order
parallelism
```

GraSP 主要把重点放在这里：

```text
Retrieved Skills
→ Compile
→ Typed DAG
→ Verify
→ Local Repair
```


#### Maintenance：Skill Library 自己怎样演化？

随着长期 trajectory 积累，系统还要回答：

```text
哪些 Skill 已经过时？

哪些重复？

哪些过大？

哪些应该合并？

哪些 dependency 经常成功？

哪些 edge 已经没有证据？
```

SkillGraph 把主要创新放在这一层：

```text
trajectory
→ node update
→ edge update
→ retrieval changes
→ new trajectory
```

因此二者可以放进同一张表：

| | GraSP | SkillGraph |
| --- | --- | --- |
| Graph 生命周期 | 当前任务执行期 | 长期 Skill Library |
| Node | instantiated skill invocation | reusable Skill |
| Edge | state / data / order | prerequisite / enhancement / co-occurrence |
| 输入 | retrieved Skill set | trajectories + Skill Library |
| 主要目标 | execution / verification / local repair | retrieval / library evolution / RL |
| 是否修改 Skill Library | 不是重点 | 是 |
| 是否强调 node verifier | 是 | 不是同一层重点 |
| failure 后处理 | local graph repair | 更新长期 Skill statistics / topology |
| Policy 是否训练 | 不要求以 RL 为主体 | 与 RL policy co-evolve |

这张表也可以防止把：

```text
Skill Graph
```

当成一个模糊 buzzword。

不同系统说：

```text
我们使用 Skill Graph
```

时，至少还要追问：

```text
Graph 是离线建的吗？
还是 runtime 编译？

Node 是 abstract Skill
还是 instantiated invocation？

Edge 表示 dependency
还是 empirical co-occurrence？

Graph 是只读的吗？
还是会随着 trajectory 更新？

它只是帮助 retrieval
还是直接控制 execution？

失败以后是重新 retrieval
还是 repair 子图？
```

这些问题的答案比：

```text
“用了 Graph，所以能处理复杂 Skill”
```

有用得多。


#### 从几个 Markdown 文件，到程序化 Skill Runtime

回头看这一篇目前走过的路线：

```text
一个 Skill

SKILL.md
  ↓
Progressive Disclosure
  ↓
Eval
```

继续扩展后变成：

```text
很多 Skills
  ↓
Retrieval
  ↓
Composition
  ↓
Graph
  ↓
Verification
  ↓
Repair
  ↓
Evolution
```

这里出现了一个很明显的变化。

最初 Skill 更像：

```text
可发现的 procedure package
```

到了 GraSP 和 SkillGraph，系统开始主动给 Skill 增加：

```text
schema
precondition
effect
dependency
verifier
statistics
versioned relation
runtime state
```

也就是说，研究路线正在尝试把原本主要存在于：

```text
natural-language Markdown
```

里的过程知识变成更显式的 machine-operable representation。

这也自然引出下一层问题。

如果 Skill 已经不仅是：

```text
模型读一段 Markdown，
然后自己理解怎么做
```

那么能不能直接根据：

```text
当前 Model
当前 Harness
当前 Tool Set
当前 Task
```

把 Skill 转换成一个更适合执行的表示？

2026 年的 SkVM 和 SkillRAE 都使用了：

```text
Compilation
```

这个词，但它们编译的对象并不一样。

一个在处理：

```text
Skill
×
Model
×
Harness
```

之间的执行兼容性。

另一个在处理：

```text
Retrieved Skill Evidence
×
Context Budget
```

之间的信息压缩。

所以接下来不能只问：

> Skill 应该检索哪些？

还要问：

> **检索出来以后，什么形式的 Skill 才应该真正交给 Agent 执行？**

## 5. “编译 Skill”到底是什么意思？SkVM 与 SkillRAE 编译的不是同一种东西

上一节已经出现了：

```text
Skill Retrieval
Skill Graph
Skill Composition
```

再往前走一步，2026 年的几篇工作开始直接使用：

```text
compile
compiler
runtime
VM
```

这些更接近编程语言和系统软件的词。

如果只看论文标题，很容易形成一个模糊印象：

> Skill 原来只是 Markdown，现在有人把它“编译”成代码了。

这个理解并不准确。

至少在这里要区分两种不同问题。

第一种问题来自 **portability**。

同一个：

```text
SKILL.md
```

交给：

```text
Claude Opus + Claude Code
Qwen + OpenCode
另一个模型 + 极简 Agent Harness
```

即使 Tool 大致相同，也未必得到相同结果。

因为 Skill 的自然语言 procedure 隐含了很多假设：

```text
模型能理解多复杂的步骤？
模型会不会正确处理相对路径？
模型能不能稳定生成复杂 Shell？
Harness 支不支持并行 Tool Call？
Harness 能不能启动 Subagent？
机器上有没有依赖包？
```

SkVM 试图解决这一层：

```text
Skill
×
Model
×
Harness
×
Environment
```

之间的适配问题。

第二种问题来自 **Context**。

假设 retrieval 已经找到：

```text
Skill A
Skill B
Skill C
```

仍然不代表把三个完整 `SKILL.md` 原样塞进 Context 就是最好的输入。

其中可能出现：

```text
Skill A 整体相关
但真正有用的只有两个 procedure

Skill D 整体没有入选
但其中一个局部规则恰好是当前任务需要的

几个 Skill 重复解释同一件事

真正关键的约束被长篇说明淹没
```

SkillRAE 处理的是：

```text
Retrieved Skill Evidence
        ↓
task-specific context compilation
        ↓
Executor Context
```

所以两篇论文虽然都使用：

```text
Compilation
```

这个词，但可以先用一句话分开：

```text
SkVM
→ 把 Skill 针对执行目标编译

SkillRAE
→ 把 Skill Evidence 针对当前任务编译
```

前者的 target 更接近：

```text
Model + Harness + Host Environment
```

后者的 target 更接近：

```text
Task + Context Budget + Executor
```


### 5.1 SkVM：同一个 Skill 不一定能原样跑在所有 Model + Harness 上

2026 年 4 月，上海交通大学 IPADS 的 Le Chen、Erhu Feng、Yubin Xia、Haibo Chen 提出了 **SkVM: Revisiting Language VM for Skills across Heterogenous LLMs and Harnesses**。

它的切入点不是：

```text
怎样再设计一种 Skill 格式？
```

而是一个更具体的问题：

> Agent Skills 强调 portability，但“同一个 Markdown 文件能被很多 Agent 读取”和“它能在不同 Agent 上可靠执行”其实是两件事。

当前 Skill 最常见的执行方式可以叫：

```text
interpreted execution
```

大致就是：

```text
SKILL.md
    ↓
直接进入 Context
    ↓
LLM 阅读
    ↓
LLM 理解 procedure
    ↓
选择 Tool
    ↓
执行
```

也就是：

```text
Raw Skill
→ Model
```

这和上一章讨论的 Progressive Disclosure 并不冲突。

Progressive Disclosure 解决：

```text
什么时候加载这个 Skill？
```

但 Skill 一旦加载以后，通常仍然是：

```text
把对应自然语言 instruction 交给当前 Model + Harness。
```

SkVM 认为这里缺少了一层类似传统 compiler/runtime 的适配。


#### 先看数据：Skill 其实已经带有大量可分析的“程序结构”

SkVM 从：

```text
clawhub.ai
skills.sh
```

收集了超过：

```text
118,000 Skills
```

其中进一步分析了：

```text
15,063
```

个下载量超过 100 的 Skill。

他们把这些 Skill 粗分成三类：

```text
Tool Reference
52%

Procedural Guidance
28%

Content Generation
20%
```

这里前两类加起来已经占：

```text
80%
```

也就是说，大量 Skill 不是单纯：

```text
“帮我写得更好看”
```

而是在告诉 Agent：

```text
这个 CLI 怎么调用
这个 API 怎么使用
这个任务有哪些步骤
什么条件下走哪个分支
```

论文还统计到：

```text
76%
```

的样本含有显式 procedural structure，例如：

```text
编号步骤
条件分支
步骤间依赖
```

而：

```text
75%
```

包含 code-like fragment，例如：

```text
Shell command
API call pattern
script snippet
```

因此 SkVM 的基本判断是：

> Skill 虽然用自然语言书写，但其中已经存在大量类似程序的结构，而当前 Agent 基本把它们当成普通 Context 解释执行。


#### 三类 Mismatch：Model、Harness、Environment

问题首先来自模型。

假设一个 Skill 写：

```markdown
1. Inspect all CSV files.
2. Run the analysis scripts independently.
3. Aggregate the outputs.
4. Compare all results.
5. Produce a final report.
```

对一个比较强的模型，这段 instructions 可能足够。

较弱模型却可能出现：

```text
漏步骤
参数传错
中间结果没有保存
复杂 Shell 写错
```

所以：

```text
Skill requirements
```

和：

```text
Model capabilities
```

之间可能不匹配。

第二个问题来自 Harness。

同一个 Model 放进两个 Harness：

```text
Harness A
├── read
├── write
├── shell
├── batch tool call
└── subagent

Harness B
├── read
├── write
└── shell
```

Skill 如果写：

```text
Spawn three subagents and analyze the services in parallel.
```

在 A 上可能非常自然。

在 B 上：

```text
根本不存在 spawn_subagent primitive。
```

于是：

```text
Same Model
+
Same Skill
+
Different Harness
=
Different Executability
```

第三个问题是 Environment。

Skill 可能默认：

```text
pandas installed
git available
curl available
某个 CLI 已登录
特定 Python package 已安装
```

用户机器实际上：

```text
dependency missing
```

模型就不得不在任务执行过程中临时诊断：

```text
为什么 import 失败？
该安装什么？
用 pip 还是 conda？
版本冲突怎么办？
```

SkVM 的实验中，在人为移除所需 dependency 后，较弱 Qwen 模型的成功率降到：

```text
33%–67%
```

并因为尝试 workaround 多生成：

```text
2–4×
```

输出 token。

Claude Opus 4.6 在论文测试中仍然可以恢复成功，但处理环境问题本身会增加：

```text
56%–69%
```

输出 token。

也就是说：

```text
强模型
```

有时候能够把 Environment Mismatch 暴力解决掉，但代价仍然存在。

于是 SkVM 把三个 failure source 写成：

```text
P1: Model Mismatch

P2: Harness Mismatch

P3: Environment Mismatch
```


#### SkVM 的核心类比：Skill 是 Code，LLM 是异构 Processor

论文用的类比很直接：

```text
Traditional Computing

Source Code
    ↓
Compiler
    ↓
Target-specific representation
    ↓
CPU / Runtime
```

对应到 Agent：

```text
Agent Skill
    ↓
SkVM Compiler
    ↓
Target-specific Skill Variant
    ↓
Model + Harness
```

这里需要保留一个限制：

```text
Skill
≠
传统严格语法定义的 Source Code

LLM
≠
CPU
```

自然语言没有固定 AST，LLM execution 又有随机性，所以 SkVM 并不是传统 compiler 的直接复制。

论文自己也承认 skill compilation 存在：

```text
non-determinism
```

这里借用 VM / compiler，更主要是为了提出一种系统边界：

> 不再假设同一个自然语言 Skill 可以原样适配所有执行目标，而是在安装和运行阶段为不同 target 做 specialization。


#### 第一步不是 Compile，而是给 Model + Harness 做 Profile

如果 compiler 想判断：

```text
这个 Skill 对当前模型太难了吗？
```

首先必须描述：

```text
Skill 要求什么能力？
```

以及：

```text
当前 target 有什么能力？
```

SkVM 为此定义了一组：

```text
Primitive Capabilities
```

论文最后得到：

```text
26 primitive capabilities
4 categories
```

覆盖其分析语料中约：

```text
95%
```

Skill 的需求。

其中一些例子是：

| Primitive | L1 | L2 | L3 |
| --- | --- | --- | --- |
| `gen.code.shell` | `ls`、`cat` 等基本命令 | pipe、redirect、loop | `sed`、`awk` 等复杂 pipeline |
| `reason.arithmetic` | 单步计算 | 多步计算 | compound reasoning |
| `tool.exec` | 单命令 | 参数、relative path | chained execution |
| `follow.procedure` | 3 个顺序步骤 | 5–7 步并带 branch | loop + verification |

这里的：

```text
L1 / L2 / L3
```

不是整个模型的统一能力等级。

它表达的是：

```text
在某个 primitive capability 上，
目标需要什么 proficiency。
```

因此可以得到一个 Target Capability Profile：

```text
Target:
Qwen-X + Harness-Y

gen.code.shell      L2
tool.exec           L1
follow.procedure    L2
reason.arithmetic   L3
...
```

这个 profile 不是让模型自己说：

```text
“我觉得我挺会 Shell。”
```

而是通过针对 primitive capability 的 microbenchmark 实际测量。

于是整个关系变成：

```text
Skill Requirement
       ↓
   [Capability Gap]
       ↑
Target Capability Profile
```

之后 compiler 才有依据判断：

```text
原 Skill 能直接运行？

需要补偿？

还是需要换一条执行路径？
```


#### Capability-Based Compilation：Compensation 与 Substitution

假设 Skill 要求：

```text
tool.exec = L2
```

而当前 target 只有：

```text
tool.exec = L1
```

SkVM 优先做：

```text
Compensation
```

也就是尽量保留原 procedure，只降低它对模型隐式能力的要求。

可能包括：

```text
把 instruction 写得更明确
增加 example
补充 constraint
提前解析路径
把隐式步骤显式化
```

论文给了一个 PPTX Skill 的例子。

原 Skill 使用：

```text
python-pptx
```

当前 target 基本能力够，但在：

```text
relative path resolution
```

上不稳定。

一种方案可以完全换实现：

```text
python-pptx
→
PptxGenJS
```

但 Skill 对 `tool.exec` 只是差一个 capability level，因此 SkVM 优先 compensation：

```text
提前把 relative path
改写成 absolute path
```

从而不要求模型自己正确解析。

如果 gap 太大，compensation 不再可靠，就使用：

```text
Substitution
```

例如：

```text
Skill 要求：
gen.code.python L3

当前 Model：
gen.code.python L1

但：
gen.code.sql L2
```

如果任务存在语义等价的 SQL 实现，就可以：

```text
Python path
    ↓
Substitute
    ↓
SQL path
```

所以 compilation 不是：

```text
把 Markdown 压缩一下
```

而是在根据 target capability 重写：

```text
how this procedure should be realized
```


#### Environment Binding：不要每次都让 Agent 临时修环境

AOT 的第二个 Pass 处理 environment。

Compiler 会从 Skill 和 prerequisites 中提取：

```text
dependency manifest
```

比如：

```text
Python library
CLI
system service
```

然后执行类似：

```text
pip show
which
```

这样的轻量检查。

最终生成：

```text
idempotent env-binding script
```

于是：

```text
安装 Skill
    ↓
提取 dependency
    ↓
生成 env binding
    ↓

每次执行前：
check / repair environment
    ↓
再进入 Agent execution
```

而不是：

```text
Agent 开始任务
    ↓
import error
    ↓
模型诊断
    ↓
模型搜索
    ↓
模型安装
    ↓
模型重新执行
```

这实际上是在把：

```text
重复出现的 environment recovery
```

从 Agent loop 中拿出去。

如果 binding script 本身失败，SkVM 才退回 LLM，并把脚本结果提供给模型。


#### Concurrency Extraction：自然语言写成顺序，不代表执行必须串行

AOT 第三个 Pass 处理 parallelism。

假设 Skill 写：

```text
1. Analyze service A.
2. Analyze service B.
3. Analyze service C.
4. Compare the results.
```

自然语言是：

```text
1
2
3
4
```

但真实 dependency 可能是：

```text
A ─┐
B ─┼→ Compare
C ─┘
```

前三个步骤之间没有数据依赖。

SkVM 会先把 workflow 分解成：

```text
Step
Input
Output
Dependency
```

再构造 DAG。

论文借用了三种 parallelism 术语。


**Data-Level Parallelism，DLP**

同一个操作作用于多个彼此独立的数据。

例如：

```text
15 CSV files
```

执行相同 analysis：

```text
CSV1 ─→ analyze
CSV2 ─→ analyze
...
CSV15 ─→ analyze
```

可以转成：

```text
multiprocessing
Promise.all
shell parallel execution
```

这类 parallelism 不一定需要 Harness 原生支持。


**Instruction-Level Parallelism，ILP**

多个彼此独立的 step 都需要 Tool Call：

```text
analysis-script-A
analysis-script-B
analysis-script-C
```

如果 Harness 支持：

```text
batch tool dispatch
```

可以在同一个模型 turn 中一起发出，而不是：

```text
LLM
→ Tool A
→ LLM
→ Tool B
→ LLM
→ Tool C
```


**Thread-Level Parallelism，TLP**

任务之间不仅需要单次 Tool Call，还各自需要多轮推理。

例如：

```text
Debug service A
Debug service B
Debug service C
```

可以编译成：

```text
Parent Agent
├── Subagent A
├── Subagent B
└── Subagent C
```

前提是 Harness 支持：

```text
subagent spawning
```

如果 target Harness 没有对应能力，就回退到 sequential execution。

这点非常关键：

```text
parallelism
```

不只取决于 Skill 里：

```text
哪些步骤理论上可以并行
```

还取决于：

```text
当前 Harness 到底暴露什么 primitive。
```


#### AOT 之后还有 JIT：Runtime 才会暴露的失败，静态 Profile 看不到

SkVM 没有假定安装阶段的 AOT 能解决所有问题。

运行后仍可能发现：

```text
模型重复在某一步失败
Rate Limit 导致并行效果恶化
某段生成代码每次其实都一样
静态 profile 没发现某种 capability gap
```

于是又增加：

```text
JIT Optimization
```


#### Adaptive Recompilation：把失败轨迹变成下一版 Skill Variant

普通 Agent 可能已经能够自我纠错：

```text
第一次命令错了
↓
观察报错
↓
第二次修正
↓
任务完成
```

问题是：

```text
下一次调用相同 Skill
```

可能又从同一个错误开始。

SkVM 会记录：

```text
failure
retry
self-recovery trace
```

如果多个 invocation 表明这是：

```text
systematic capability gap
```

而不是一次 task-specific failure，就触发 adaptive recompilation：

```text
Runtime Failure Logs
        ↓
Compiler
        ↓
Targeted Compensation
        ↓
New Skill Variant
```

而且保留：

```text
best-performing variant
```

如果新 variant 更差，可以 rollback。

这开始和：

```text
skill-creator
```

产生一点相似。

区别是：

```text
skill-creator
→ 通过显式 eval / benchmark 改 Skill

SkVM adaptive recompilation
→ 通过 target runtime failure
  修改 target-specific variant
```

一个偏开发时优化，一个偏运行时 specialization。


#### Code Solidification：如果 LLM 每次都生成同一段代码，就别每次都让它再生成

SkVM 还观察到：

```text
75%
```

的分析 Skill 包含可被视为 code pattern 的片段。

例如天气 Skill 每次可能都生成类似：

```bash
curl "https://example.com/weather?city=<CITY>"
```

真正变化的只有：

```text
CITY
```

如果每次都经过：

```text
LLM
↓
读 Skill
↓
重新组织命令
↓
生成相似代码
```

重复消耗 token 和 latency。

SkVM 的 Code Solidification 会先识别：

```text
固定结构
+
参数槽位
```

形成：

```text
Code Signature
Code Template
Parameter Schema
```

然后观察多次真实 invocation。

只有连续结果都与预期 signature 匹配，才 promote：

```text
LLM-generated pattern
        ↓
validated repeatedly
        ↓
solidified function
```

之后：

```text
Task
 ↓
extract parameters
 ↓
call function directly
```

绕过模型生成。

如果：

```text
生成结构不稳定
```

则不 promote。

如果 solidified code 执行失败：

```text
fallback
→ LLM path
```

论文里的 PDF extraction case 报告：

```text
10,469–15,116 ms
```

降到：

```text
206–568 ms
```

即大约：

```text
19–50×
```

加速。

另一个 weather-forecast case 因生成结构不稳定，就没有进入 solidified path。

因此它不是简单地：

```text
看起来重复
→ 自动硬编码
```

而是有一个 promotion gate。


#### SkVM 到底做出了什么结果

论文最终在：

```text
8 LLMs
3 Harnesses
118 representative tasks
```

上评估。

模型覆盖：

```text
SOTA
Mid-tier
Small
```

Harness 则包括：

```text
BareAgent
OpenCode
OpenClaw
```

论文报告 SkVM 对 task completion 的平均提升约：

```text
15.3%
```

并在部分配置中将 token consumption 降低最多：

```text
40%
```

Concurrency Extraction 的最高端到端加速约：

```text
3.2×
```

Code Solidification 的局部案例则达到前面的：

```text
19–50×
```

论文还观察到，原始 Skill 在约：

```text
15%
```

的任务上造成性能退化，而 SkVM compiled Skills 中出现退化的比例降到：

```text
4.5%
```

这些数字都是论文实验设置下的结果，不能直接写成：

```text
装 SkVM
→ 所有 Agent 自动快 3.2×
```

其中一个尤其需要注意的实验边界是：

> 为了支持 compiled skill artifact，论文对目标 Harness 增加了 SkVM 所需的 loading / management mechanism。

所以它证明的是：

```text
如果 runtime 愿意增加一层 Skill compilation support，
这种 specialization 可以工作。
```

不是：

```text
任何今天原封不动的 Agent Harness
都天然拥有这层行为。
```


### 5.2 SkillRAE：它编译的不是 Runtime，而是 Executor 看到的 Context

SkVM 的输入可以写成：

```text
Skill
+
Model
+
Harness
+
Environment
```

SkillRAE 的问题则从另一端开始。

2026 年 5 月，香港中文大学（深圳）的 Xiangcheng Meng、Shu Wang、Yixiang Fang 提出了：

**SkillRAE: Agent Skill-Based Context Compilation for Retrieval-Augmented Execution**。

它把 Skill execution 写成一个三段过程：

```text
Retrieval
    ↓
Context Compilation
    ↓
Execution
```

论文称这种范式为：

```text
Retrieval-Augmented Execution
RAE
```

和传统 RAG 相比：

```text
RAG
retrieve factual evidence
→ help generation

RAE
retrieve procedural artifacts
→ help execution
```

最容易想到的 RAE 是：

```text
Task
  ↓
Retriever
  ↓
Top-K Skills
  ↓
把完整 Skills 放进 Context
  ↓
Agent 执行
```

SkillRAE 认为这里仍然缺一步。

因为：

```text
retrieval relevance
≠
execution readiness
```


#### “Skill 整体没入选”不代表其中每条 procedure 都没用

假设 Library 中有：

```text
citation-management
paper-review
latex-writing
literature-search
```

当前任务是：

```text
整理几个 DOI，
生成 BibTeX，
然后输出一个简短文献表。
```

retrieval 可能选：

```text
citation-management
latex-writing
```

但：

```text
literature-search
```

这个 Skill 虽然整体 relevance 不够高，其中却可能有一条：

```text
DOI normalization convention
```

恰好非常有用。

传统 Top-K Skill selection 会出现：

```text
Skill 没被选中
→ 整个 Skill 所有内容消失
```

SkillRAE 想保留这种：

```text
local evidence
```

同时又不想：

```text
把所有“差一点入选”的完整 Skill
一起塞回 Context
```

所以它把 Skill 再拆成：

```text
Subunit
```

论文中的 subunit 可以是：

```text
short procedure
file convention
usage note
constraint
script-related instruction
```

例如：

```text
Generate properly formatted BibTeX entries
```

可以成为一个 subunit。


#### Offline：先建立三层 Skill Graph

SkillRAE 在离线阶段把 Skill Repository 表示成：

\[
\mathcal{G}=(C,S,U,E,m)
\]

其中：

```text
C
→ Skill Communities

S
→ Skills

U
→ reusable Subunits

E
→ Skill–Subunit extraction edges

m
→ Skill → Community assignment
```

可以画成：

```text
Community
   │
   ├── Skill A
   │    ├── Subunit 1
   │    └── Subunit 2
   │
   ├── Skill B
   │    ├── Subunit 2
   │    └── Subunit 3
   │
   └── Skill C
        └── Subunit 4
```

这里：

```text
Subunit 2
```

甚至可以被多个 Skill 共享，因为 extraction edge 是：

```text
many-to-many
```

SkillRAE 会从源 `SKILL.md` 中抽取 procedural line、element reference 和 constraint-like statement，再：

```text
normalize
filter
exact-match deduplicate
```

得到 Subunit。

Skill Community 则来自对 Skill representation 的 embedding 和 clustering。

因此三层 representation 分别服务：

```text
Community
→ coarse semantic region

Skill
→ executor-compatible procedure

Subunit
→ fine-grained local evidence
```


#### Online Retrieval：同时 Top-down 和 Bottom-up

任务：

\[
q
\]

进入在线阶段后，SkillRAE 并不只做：

```text
query embedding
vs
skill description embedding
```

而是同时使用两条路。


**Top-down**

先判断：

```text
这个 Task
更像哪个 Skill Community？
```

得到：

\[
\mathcal{B}(q)
\]

也就是 community-supported Skills。


**Bottom-up**

同时直接把 Task 和 Subunit 做匹配。

如果一个局部 procedure：

```text
与 query 高度匹配
```

就把这个 evidence 沿 extraction edge 投回其来源 Skill。

Skill \(s\) 的 bottom-up evidence 可以写成：

\[
\ell_0(s,q)
=
\operatorname{norm}_{S}
\left(
\sum_{u\in\mathcal{T}_N(q)}
\mathbf{1}\{(s,u)\in E\}
\frac{\sigma(q,u)}{\deg(u)}
\right)
\]

其中：

```text
σ(q,u)
→ Task 与 Subunit 的相似度

deg(u)
→ 这个 Subunit 出现于多少个 Skills

1{(s,u)∈E}
→ 这个 Subunit 是否属于 Skill s
```

除掉：

\[
\deg(u)
\]

的直觉是：

```text
到处都有的通用 Subunit
```

应该比：

```text
只在少数 Skill 中出现的特异 procedure
```

贡献得更少。


#### 最终 Skill Score 同时融合四类信号

SkillRAE 的最终 score 是：

\[
\operatorname{score}(s,q)
=
\left(
\alpha\ell_1(s,q)
+
\beta\ell_0(s,q)
+
\gamma p(s,q)
\right)
\left(
1+\lambda\mathbf{1}\{s\in\mathcal{B}(q)\}
\right)
\]

其中：

```text
ℓ1
→ Task vs Skill Description

ℓ0
→ Bottom-up Subunit Evidence

p
→ Skill Name Score

B(q)
→ Top-down Community Support
```

最后：

\[
K(q)
=
\operatorname{TopK}_{s\in S}
\operatorname{score}(s,q)
\]

得到 selected Skills。

但 retrieval 输出还不止：

```text
K(q)
```

它同时保留：

```text
H(q)
→ selected Skill 中最相关的 local highlights

R(q)
→ 没入选 Skill 中值得后续 rescue 的候选 evidence
```

这给后面的 compilation 留了材料。


#### Context Compilation 第一步：Rescue 被 Top-K Skill Selection 丢掉的局部证据

假设：

```text
Skill D
```

没进入：

```text
K(q)
```

但其中：

```text
Subunit d3
```

非常匹配当前任务。

SkillRAE 不会把整个 Skill D 塞回来。

它先建立：

\[
Z(q)
\]

即经过：

```text
relevance
non-redundancy
source alignment
budget
```

过滤后的少量 rescued subunits。

于是：

```text
Skill D
├── d1   irrelevant
├── d2   irrelevant
├── d3   useful   ← rescue
└── d4   irrelevant
```

真正进入下一阶段的只有：

```text
d3
```


#### 第二步：Rescued Subunit 不独立暴露，而挂到已选 Skill 上

这里有一个细节很重要。

如果直接把：

```text
Subunit d3
```

作为独立的第四个“临时 Skill”交给 Agent，可能破坏 executor 原本理解 Skill 的接口。

SkillRAE 会为它找一个已 selected Skill：

\[
s^\star(u)
=
\arg\max_{s\in K(q)}
\operatorname{Aff}(u,s\mid q)
\]

然后把 rescued evidence 附着到这个 Skill 上。

例如：

```text
Selected:
citation-management

Rescued:
DOI normalization convention
来自 literature-search

Compiled:
citation-management
├── original relevant procedure
└── affiliated cue:
    normalize DOI before BibTeX generation
```

这样 executor 仍然看到：

```text
selected Skills
```

而不是突然多出一堆没有完整上下文的零碎 procedure。


#### 第三步：不是 rescue 出来多少就塞多少

Compiler 接下来还要过滤：

```text
concrete?
task-aligned?
redundant?
within budget?
```

最终形成：

\[
\mathcal{A}_{\mathrm{final}}(q)
\]

也就是实际准备进入 Context 的 affiliated cues。

这一步防止：

```text
rescue
```

退化成：

```text
把所有候选 Subunit 全塞回 Prompt。
```


#### 第四步：组织成 Task-Specific Context

最后：

\[
\mathcal{C}(q)
=
\operatorname{Compile}_B
\left(
q,
K(q),
H(q),
\mathcal{A}_{\mathrm{final}}(q),
\mathcal{O}(q)
\right)
\]

其中：

```text
q
→ Task Request

K(q)
→ Selected Skills

H(q)
→ Selected Skill Highlights

A_final(q)
→ Rescued / Affiliated Cues

O(q)
→ Output Contract

B
→ Context Budget
```

结果不是：

```text
一个新的 executable program
```

而是一份：

```text
compact
grounded
task-specific
execution context
```

交给原来的 downstream executor。


#### SkillRAE 最需要记住的边界：它不接管控制流

这和上一章的 GraSP 很不一样。

GraSP 会建立：

```text
executable DAG
```

并做：

```text
node verification
local repair
```

SkillRAE 明确不这么做。

它没有改变：

```text
source Skill
planner
executor
runtime control policy
```

改变的是：

```text
executor 在开始执行前看到什么 Context。
```

可以画成：

```text
                  SkillRAE
                     │
Task ─→ Retrieval ─→ Compile Context
                     │
                     ▼
               Existing Executor
                     │
                     ▼
                  Tools
```

而不是：

```text
SkillRAE
  ↓
自己控制 Tool Execution
```

所以它属于：

```text
advisory compiler
```

论文自己的 limitation 也很明确：

```text
Compiled Context
≠
保证 Executor 一定使用这些信息

Compiled Context
≠
执行失败后的 recovery mechanism
```

如果 Agent 在 runtime：

```text
Tool 执行失败
Environment 改变
状态不符合预期
```

SkillRAE 本身没有像 GraSP 那样做局部 repair，也没有像 SkVM 那样做 adaptive recompilation。


#### SkillRAE 的实验结果，比“+11.7%”本身更值得细拆

论文主要在：

```text
SkillsBench
AgentSkillOS
```

两个 benchmark 上评估。

SkillsBench 的实验配置里有：

```text
87 tasks
207 skills
14 communities
4,834 subunits
5,255 extraction edges
```

主 backbone 使用：

```text
Codex CLI + GPT-5.2
```

结果：

| Method | SkillsBench Reward Mean |
| --- | ---: |
| Benchmark-native Curated Skills | 26.20 |
| Vanilla Retrieval | 19.44 |
| LLM-based Retrieval | 16.34 |
| SkillRouter | 22.04 |
| SkillRAE | **29.26** |

因此 SkillRAE 相对 curated Skills 是：

```text
29.26 - 26.20
=
+3.06 percentage points
```

换算成相对增幅：

\[
\frac{29.26-26.20}{26.20}
\approx
11.7\%
\]

这就是摘要里：

```text
11.7%
```

的来源。

所以正文最好不要写：

```text
SkillRAE 比 SOTA 高 11.7 个百分点。
```

正确的是：

```text
相对 curated Skills +3.06 pp
即约 +11.7% relative improvement
```

如果和 SkillRouter 比：

```text
29.26 - 22.04
=
+7.22 pp
```

差距反而更大。


#### Ablation 更能说明“Compilation”到底贡献了什么

完整 SkillRAE：

```text
29.26
```

去掉 Bottom-up Retrieval：

```text
23.43
```

去掉 Top-down Retrieval：

```text
16.61
```

去掉 Context Compilation：

```text
22.59
```

因此在：

```text
Codex CLI + GPT-5.2
```

这个配置中：

```text
Context Compilation
22.59 → 29.26
=
+6.67 pp
```

说明这篇论文不是：

```text
只靠检索更准
```

拿到的结果。

它确实观察到：

```text
same general executor
+
better organization of retrieved evidence
→ higher downstream reward
```

不过换成：

```text
Gemini CLI + Gemini 3 Flash
```

以后：

```text
Full
28.85

w/o Context Compilation
27.80
```

差距只剩：

```text
1.05 pp
```

因此也不能写成：

```text
Context Compilation 固定贡献 +6.67 pp。
```

更准确的是：

> Context compilation 的收益明显依赖 downstream model/harness；同一 ablation 在不同 backbone 上 effect size 不同。

这一点和 SkVM 其实形成了很好的呼应：

```text
Skill behavior
是 model-relative
也是 harness-relative。
```


### 5.3 两篇都叫 Compilation，但优化目标完全不同

把 SkVM 和 SkillRAE 放在一起以后，最容易犯的错误是：

```text
它们都在把 Skill 编译成更好的 Skill。
```

实际上可以从输入和输出直接分开。


| | SkVM | SkillRAE |
| --- | --- | --- |
| 核心问题 | 同一个 Skill 如何跨不同执行目标工作 | retrieved Skills 如何形成当前任务需要的 Context |
| 输入 | Skill + Model + Harness + Environment | Task + Skill Repository |
| Target | `(model, harness, host)` | 当前 Task / Executor |
| 中间表示 | capability profile、compiled variant、dependency DAG、JIT artifact | community、Skill、Subunit、retrieval evidence |
| 主要动作 | specialization / binding / parallelization / JIT | retrieval / rescue / filtering / context organization |
| 输出 | target-specific executable Skill variant / runtime artifact | task-specific compiled Context |
| 是否改变执行方式 | 会，runtime 参与 scheduling / JIT | 不接管 executor control flow |
| 是否解决环境依赖 | 是，Environment Binding | 否 |
| 是否把重复代码绕开 LLM | 可以，Code Solidification | 不做 |
| 是否针对当前 query 选择局部 Skill Evidence | 不是核心 | 是 |
| Runtime failure recovery | Adaptive Recompilation / fallback | 不负责 |
| Compiler 生命周期 | install-time AOT + runtime JIT | offline index + per-task online compilation |


可以用同一个 Skill 举例。

假设有：

```text
data-analysis/
└── SKILL.md

要求：
1. 加载 CSV
2. 计算几个统计量
3. 画图
4. 验证结果
```

如果目标是：

```text
Qwen + BareAgent
```

而它不擅长复杂 pandas chain，SkVM 关注：

```text
当前模型 capability 不足
→ instructions 是否要写得更明确？

是否应该换 SQL path？

pandas 是否安装？

三个 CSV 是否能并行分析？

某段固定脚本是否可以 solidify？
```

输出的是：

```text
适合 Qwen + BareAgent 的 variant。
```

如果换成：

```text
Claude + OpenCode
```

SkVM 可能得到另一种 variant：

```text
强模型不用补那么多 example
Harness 支持 batch dispatch
→ 可以暴露更多 parallelism
```

所以：

```text
same source Skill
→ different execution target
→ different compiled variant
```


SkillRAE 面对同一个 Skill 时关注的却是另一件事。

用户现在说：

```text
这 20 个 CSV 里，
只比较 2025 和 2026 的 retention，
画一张季度趋势图，
不要做其他统计。
```

完整 `data-analysis` Skill 里可能还有：

```text
missing-value analysis
outlier detection
correlation matrix
regression
forecasting
```

SkillRAE 要做的是：

```text
当前 task 到底需要哪些 procedure？

selected Skill 里哪些 Subunit 应该突出？

其他没入选 Skill 中
有没有一个 plotting convention
恰好值得 rescue？

最终 Context 怎样在预算内组织？
```

输出：

```text
适合这一次 retention task 的 Context。
```

所以：

```text
SkVM:
target-specific specialization

SkillRAE:
query-specific evidence compilation
```


#### 一个处理“能不能跑”，另一个处理“应该给它看什么”

这两个系统甚至可以概念上叠起来。

假设：

```text
Skill Library
    ↓
SkillRAE
```

先根据 Task 生成：

```text
Task-specific Skill Context
```

与此同时，真正 selected Skill 已经针对：

```text
Model + Harness + Environment
```

经过 SkVM compilation。

于是理论上的 pipeline 可以变成：

```text
                 Skill Repository
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
       SkillRAE Index       SkVM Compile
              │                 │
Task ─────────┘                 │
   │                            │
   ▼                            ▼
retrieve + context      target-specific
compile                 Skill variants
   │                            │
   └────────────┬───────────────┘
                ▼
            Executor
                │
                ▼
             Runtime
```

这里不是说两篇论文已经实现了这个联合系统。

只是从接口看，它们优化的是正交问题：

```text
Which evidence should this task see?

vs

How should this Skill execute on this target?
```


#### 这也解释了“Skill = Prompt”为什么开始越来越不够用

回到全文最开始。

最简单的 Skill 可以确实理解成：

```text
saved reusable Prompt
```

但一路走到现在已经出现：

```text
metadata
description retrieval
progressive disclosure
references
scripts
eval
trigger optimization
skill graph
dependency
compiler
runtime specialization
context compilation
```

于是 Skill 本身逐渐出现三个层次。


**Source Representation**

```text
SKILL.md
scripts/
references/
assets/
```

负责：

```text
人怎样编写和分发 Skill。
```


**Intermediate Representation**

研究系统开始额外抽取：

```text
Capability Requirement
Subunit
Dependency
Precondition
Effect
Community
Workflow DAG
```

负责：

```text
机器怎样分析 Skill。
```


**Runtime Representation**

再根据：

```text
Task
Model
Harness
Environment
```

形成：

```text
Compiled Variant
Task-specific Context
Execution DAG
Solidified Function
```

负责：

```text
Agent 真正执行时应该使用什么。
```

可以画成：

```text
        Source Skill
        SKILL.md
           │
           ▼
      Static Analysis
           │
           ▼
 Intermediate Structure
           │
    ┌──────┼───────────┐
    │      │           │
    ▼      ▼           ▼
 Model   Harness      Task
Profile Capability  Retrieval
    │      │           │
    └──────┼───────────┘
           ▼
     Runtime Artifact
```

这还远没有形成一种公认的：

```text
Agent Skill IR
```

SkVM、GraSP、SkillGraph、SkillRAE 各自在定义自己的 representation。

但问题已经比较明确：

> 当 Skill 数量、复杂度和执行环境继续增长，只靠“模型打开一个 Markdown 然后自己理解”会把越来越多本可显式处理的工作留在每一次 inference 中。


#### 不过也不要太快把 Agent Skills 类比成新的 Programming Language

这里需要保留一个反方向的限制。

自然语言 Skill 的一个优势本来就是：

```text
authoring cost 低
模型可以解释不完整 procedure
能够根据环境灵活调整
```

如果不断加入：

```text
类型系统
dependency schema
precondition
effect
compiler
JIT
VM
```

最终可能重新造出一个：

```text
复杂 workflow language
```

然后失去 Skill 原本：

```text
Markdown-first
easy to author
easy to inspect
cross-harness readable
```

的特点。

SkVM 也没有声称：

```text
自然语言已经变成确定性程序。
```

其 compilation 自身依然可能依赖 LLM，因此存在 non-determinism。

SkillRAE 同样没有保证：

```text
编译后的 Context
→ Executor 必然遵守。
```

所以目前更合适的理解不是：

```text
Prompt
已经被 Compiler 淘汰
```

而是：

```text
Natural-language Skill
仍然作为 Source Representation

但 Harness 可以逐渐把：
能够分析的结构
能够确定性执行的代码
能够提前验证的环境
能够局部选择的证据
从每次 LLM inference 中拿出来。
```

这和前面多次出现的工程原则是一致的：

```text
开放判断
→ 留给 Model

确定性约束
→ 下沉到 Runtime

重复计算
→ 下沉到 Script

环境依赖
→ 提前 Binding

大量候选知识
→ Retrieval

局部相关 procedure
→ Context Compilation
```


到了这里，Skill 已经从：

```text
一份文本 procedure
```

扩展到了：

```text
可检索
可评测
可组合
可编译
可运行时优化
```

但前面默认的 Skill 仍然主要是一种：

```text
text-centric procedural knowledge
```

对于 GUI Agent，这个假设会再次遇到边界。

例如一个桌面 Skill 写：

```text
点击右上角 Save。
```

真正执行时还必须判断：

```text
现在显示的是不是编辑页面？

Save 按钮长什么样？

保存以后成功状态是什么？

弹出了错误窗口还是确认窗口？

当前画面与 reference trajectory
到底处于哪一个状态？
```

这种 knowledge 已经不能只靠一段文本 procedure 完整表达。

下一节的 MMSkills 就把 Skill representation 从：

```text
Text Procedure
```

进一步扩展成：

```text
Procedure
+
Visual Runtime State
+
Keyframes
```

也就是从“告诉 Agent 怎么做”，继续走向“同时告诉 Agent 执行过程中应该看到什么”。

## 6. 当“步骤”还不够：MMSkills 把视觉状态也变成 Skill 的一部分

前面讨论的 Skill，无论是 Anthropic Agent Skills、GraSP、SkillGraph、SkVM 还是 SkillRAE，大多数时候都默认一个前提：

```text
只要把 procedure 描述清楚，
Agent 就能够从当前环境中识别：
“我现在处在哪一步。”
```

对于代码、CLI 和结构化数据任务，这个假设经常成立。Agent 可以读取：

```text
exit code
JSON
filesystem
compiler error
test result
API response
```

然后把环境状态转换成相对明确的文本。

GUI Agent 和游戏 Agent 则不同。

例如 Skill 写着：

```text
1. Open the chart editor.
2. Select the data range.
3. Choose a clustered column chart.
4. Confirm the preview.
5. Save the chart.
```

procedure 本身完全没有错，但运行中的 Agent 还必须回答：

```text
当前到底有没有进入 chart editor？

现在选中的是数据区域，
还是旁边一个空白单元格？

弹出的窗口是 chart type 页面，
还是 data range 页面？

这个按钮是 Next，
还是 Finish？

点击之后出现的是成功状态，
还是另一个 modal dialog？
```

这些问题不只是：

```text
what should I do?
```

而是：

```text
what state am I in?
```

以及：

```text
what visual evidence proves that state?
```

如果状态识别错了，即使 Agent 背熟了正确 procedure，也可能从错误节点开始执行。

例如：

```text
Skill:
点击 “Install”

Live Screen:
其实已经安装完成，
现在显示的是 “Uninstall”
```

如果模型只根据文本 Skill 强行执行：

```text
find Install
```

可能开始搜索一个根本不存在的按钮。

或者：

```text
Skill:
选择 File → Export

Live Screen:
当前有一个 unsaved-changes dialog 挡在最前面
```

正确行为应该先处理 modal，而不是机械沿着 procedure 继续。

所以视觉任务中的 procedure 更接近：

```text
State
  ↓
Evidence
  ↓
Decision
  ↓
Action
  ↓
New State
```

而不是单纯：

```text
Step 1
↓
Step 2
↓
Step 3
```

2026 年 5 月提交的 [MMSkills: Towards Multimodal Skills for General Visual Agents](https://arxiv.org/abs/2605.13527) 就从这个问题出发，把 reusable skill 从：

```text
Text Procedure
```

扩展为：

```text
Text Procedure
+
Runtime State
+
Visual Evidence
```

论文作者主要来自上海交通大学，同时包含小红书与东南大学作者。它没有把“多模态 Skill”定义成：

```text
在 SKILL.md 旁边随便放几张 screenshot
```

而是要求视觉材料承担明确的 runtime decision role。


### 6.1 Text-only Skill 的缺口，不是“看不到图片”，而是缺少 State Recognition

先构造一个桌面任务。

用户要求：

```text
在 LibreOffice Calc 里，
根据现有数据创建 clustered column chart。
```

Text Skill 可以写得非常详细：

```markdown
## Create a clustered column chart

1. Select the data range.
2. Open Insert > Chart.
3. Choose Column.
4. Choose the clustered variant.
5. Verify series and labels.
6. Finish.
```

如果 Agent 已经准确处在：

```text
正常 worksheet
+
正确 sheet
+
正确 data range
```

这套 procedure 很有用。

问题是执行过程中还有很多状态：

```text
State A
普通 worksheet

State B
range selected

State C
chart wizard opened

State D
chart type selected

State E
data series incorrect

State F
chart inserted
```

而且两个视觉上相近的状态，行动可能完全不同。

例如：

```text
State D:
Chart Type = Column
Subtype = Normal
```

和：

```text
State D':
Chart Type = Column
Subtype = Stacked
```

从高层文本看都可以被总结为：

```text
column chart selected
```

但用户要求的是：

```text
clustered
```

只告诉 Agent：

```text
Choose a clustered column chart.
```

等于把真正困难的一步：

```text
如何判断当前 UI 是否已经处于正确 subtype
```

继续留给 VLM 自己解决。

MMSkills 因此区分：

```text
Procedure Knowledge
```

和：

```text
State Recognition Knowledge
```

前者回答：

```text
What should normally happen?
```

后者回答：

```text
What should I see
before deciding that this step applies?
```

论文用一个很直接的例子解释这种差异：desktop agent 可能知道正确 operation，却没有发现当前 dialog 其实还没有 ready；game agent 可能知道目标，却无法从视觉画面区分：

```text
progress
```

和：

```text
completion
```

所以 Text Skill 的问题并不一定是：

```text
步骤写少了。
```

继续补文本甚至可能越来越长：

```markdown
If the dialog looks like...
If there is a box on the left...
If the top tab says...
If the preview shows...
```

最终会出现一种奇怪状态：

```text
为了描述视觉状态，
不断用文字重建图片。
```

MMSkills 把这部分直接表示成 multimodal procedural knowledge。


### 6.2 一个 MMSkill = Procedure + State Card + Keyframe

论文把一个 MMSkill 写成：

\[
M=(D,P,S,K)
\]

其中：

```text
D
→ Descriptor

P
→ Textual Procedure

S
→ Runtime State Cards

K
→ Keyframe Bundles
```

如果用目录直觉理解，可以近似写成：

```text
MMSkill/
├── descriptor
├── procedure
│
├── state-1
│   ├── state-card
│   └── keyframes
│
├── state-2
│   ├── state-card
│   └── keyframes
│
└── state-n
    ├── state-card
    └── keyframes
```

其中：

```text
P
```

仍然是前面熟悉的 reusable procedure。

例如：

```text
Select range
→ Insert chart
→ choose type
→ verify
→ finish
```

真正新增的是：

\[
S=\{S_j\}_{j=1}^{m}
\]

和：

\[
K=\{K_j\}_{j=1}^{m}
\]

每一组：

\[
(S_j,K_j)
\]

描述 procedure 中一个 **decision-relevant state**。


#### State Card 不是 Screenshot Caption

MMSkills 的 state card 不只是：

```text
“这张图是打开 Chart Wizard 后的截图。”
```

论文定义：

\[
S_j=
(
\text{when\_to\_use}_j,
\text{when\_not\_to\_use}_j,
\text{visible\_cues}_j,
\text{verification\_cue}_j,
\mathcal{V}_j
)
\]

也就是说至少包含：

```text
when_to_use
→ 什么情况下这个 state/procedure 分支适用？

when_not_to_use
→ 什么状态下不要照着做？

visible_cues
→ 当前画面应该检查什么？

verification_cue
→ 怎样确认 progress / completion？

available_views
→ 哪些视觉 reference 可以按需查看？
```

假设做一个简化版 GUI Skill：

```yaml
state: chart-type-selection

when_to_use:
  - Chart Wizard is open.
  - The current page is Chart Type.

when_not_to_use:
  - The wizard has already moved to Data Range.
  - A modal error dialog is blocking the wizard.

visible_cues:
  - "Column" is selected in the chart category list.
  - A subtype preview is visible.

verification_cue:
  - The non-stacked clustered column preview is selected.

available_views:
  - full_frame
  - focus_crop
```

这里真正增加的信息是：

```text
before action
→ applicability

during action
→ visible evidence

after action
→ verification
```

这和前面 GraSP 的：

```text
precondition
effect
verifier
```

在抽象上有一点相似。

差别是 MMSkills 处理的是：

```text
视觉环境中
怎样识别这些状态。
```


#### Keyframe 也不是“给模型一个标准答案照着点”

每个 State Card 可以绑定一个小的 multi-view bundle。

论文定义候选 view：

\[
\mathcal{V}
=
\{
\text{full\_frame},
\text{focus\_crop},
\text{before},
\text{after}
\}
\]

不同 view 有不同用途。


**`full_frame`**

保存全局位置关系。

例如：

```text
Chart Wizard
```

在当前整个桌面中的状态。

模型可以判断：

```text
是不是同一个 application？
有没有 modal？
当前在哪个 wizard stage？
```


**`focus_crop`**

把真正的 diagnostic region 裁出来。

例如：

```text
chart subtype selector
```

或者：

```text
VS Code extension Install 按钮区域
```

这样模型不用从整张 1920×1080 截图里重新寻找关键细节。


**`before / after`**

用于表达 transition。

例如：

```text
before:
extension 尚未安装

after:
Install 按钮变成 Uninstall
```

这比文字写：

```text
“如果按钮变化就说明成功”
```

更容易形成视觉 verification reference。

但论文特别强调：

```text
reference image
≠
action coordinate
```

也就是说：

```text
Reference screenshot:
按钮在 x=1530, y=410
```

不能推出：

```text
Live screenshot:
也点击 x=1530, y=410
```

UI 可能因为：

```text
窗口尺寸
主题
语言
软件版本
侧边栏
显示缩放
```

改变位置。

所以 keyframe 的作用是：

```text
帮助识别 semantic state
```

而不是：

```text
保存 replay coordinate。
```


#### Text-only Skill 是 MMSkill 的退化形式

从公式看，这个关系很清楚：

\[
M_{\text{text}}
=
(D,P,\emptyset,\emptyset)
\]

也就是：

```text
Descriptor
+
Procedure
```

没有：

```text
State Cards
Keyframes
```

因此 MMSkills 并不是完全否定 Text Skill。

它更像是在说：

```text
当环境状态可以可靠抽象成文本
→ Text Skill 足够

当正确执行依赖视觉状态识别
→ 再增加 multimodal state evidence
```

这点很重要，因为不是所有 Skill 都值得多模态化。

例如：

```text
Python package release checklist
```

大部分状态可以通过：

```text
git
pytest
filesystem
package metadata
```

确定性读取。

强行给：

```text
terminal screenshot
```

几乎没有价值。

而：

```text
GIMP
LibreOffice
游戏
桌面 UI
浏览器 visual workflow
```

才更符合 MMSkills 的问题设定。


### 6.3 Skill 从哪里来？MMSkills 不直接把完整 Demonstration 当成 Skill

如果多模态 Skill 必须包含：

```text
procedure
state
visual evidence
```

下一个问题是：

> 难道每个 Skill 都要人工录屏，然后手动截图、裁图、写 State Card？

MMSkills 的另一个部分就是：

```text
trajectory-to-skill Generator
```

它从 public interaction trajectories 中构建 Skill，而且论文明确要求：

```text
Skill source trajectories
```

与：

```text
evaluation tasks
```

分离，避免直接把测试任务 demonstration 变成 Skill。

一条 trajectory 可以表示成：

\[
\tau_i=
(
I_i,
O_{i,1:T_i},
A_{i,1:T_i}
)
\]

其中：

```text
I_i
→ Task Instruction

O_i
→ 一系列视觉 Observation

A_i
→ 对应 Action
```

最简单的 Skill 生成方法可能是：

```text
成功 trajectory
↓
压缩一下
↓
Skill
```

例如直接保留：

```text
Screenshot 1
Action 1
Screenshot 2
Action 2
Screenshot 3
Action 3
...
```

这更像：

```text
demonstration replay
```

而不是 reusable procedure。

因为 trajectory 中有大量：

```text
task-specific object
specific coordinate
accidental detour
specific window layout
instance-specific data
```

MMSkills 的 Generator 因此分成五个阶段：

```text
Phase 0
Task Embedding + Clustering
        ↓
Phase 1
Cluster-level Skill Planning
        ↓
Phase 2
Merge / Generalize
        ↓
Phase 3
Text-first Drafting
        ↓
Phase 4
Image Grounding + Audit
```

这里的顺序设计很值得注意。


#### Phase 0：先按任务语义聚类，而不是一条轨迹生成一个 Skill

如果输入是：

```text
1000 条 GUI trajectories
```

直接：

```text
1 trajectory
→
1 Skill
```

很容易得到：

```text
1000 个 highly specific Skills
```

例如：

```text
create-blue-chart-in-sheet1
create-red-chart-in-sheet2
create-chart-from-a1-b8
...
```

这些并不具有 reusable abstraction。

所以先：

```text
embed task instructions + trajectory metadata
```

再聚成更一致的 workflow cluster。


#### Phase 1：找 atomic workflow boundary

对每个 cluster，再让 LLM-based agent 提出：

```text
candidate atomic Skills
```

并明确：

```text
workflow boundary
completion condition
covered task IDs
```

这和前面的 focused Skill 原则一致。

不是把：

```text
LibreOffice
```

整个软件打成一个：

```text
LibreOffice Expert Skill
```

而是尽量找到可复用、边界明确的 procedure。


#### Phase 2：Merge，但拒绝过大的 umbrella Skill

不同 cluster 可能产生重复 Skill。

所以接下来：

```text
deduplicate
merge
generalize
```

但论文同时明确拒绝：

```text
overly broad umbrella skills
```

因为：

```text
覆盖范围更大
```

并不必然等于：

```text
更 reusable。
```

如果一个 Skill 同时包含：

```text
create chart
edit formula
merge cell
conditional formatting
export CSV
```

触发、状态识别和 runtime guidance 都会变得模糊。


#### Phase 3：先写 Text，再看 Image

这一步尤其值得保留。

MMSkills 没有一开始就把大量 screenshot 交给 Generator。

而是先：

```text
只看 task / trajectory structure
```

起草：

```text
Descriptor D
Procedure P
planned State Cards
```

得到：

\[
\widehat{M}
\]

然后 Phase 4 才：

```text
读取选定 frame
```

把真正有诊断价值的视觉证据加进去。

这样做减少了一个很常见的问题：

```text
先看到某条具体 trajectory
↓
Skill 被具体 screenshot 细节绑死
```

也就是说，它先建立：

```text
procedure abstraction
```

再用视觉 evidence grounding。


#### Phase 4：视觉证据只保留 diagnostic states

最后才：

```text
choose keyframes
ground focus regions
construct multi-view bundles
audit Skill
```

论文采用相对保守的 visual grounding policy。

只在三种情况加入 view：

```text
state recognition

transition comparison

completion verification
```

而不是：

```text
每一个 action
都保存一张 screenshot。
```

因此最终转换是：

\[
\widehat{M}_r
=
(D_r,P_r,\widehat{S}_r,\widehat{K}_r)
\]

经过：

```text
ground + audit
```

得到：

\[
M_r=
(D_r,P_r,S_r,K_r)
\]

这里与 Skill Creator 的思路也有一点相似：

```text
生成 Skill
```

不是流程终点。

后面还有：

```text
quality gate
audit
evaluation
```


### 6.4 Branch Loading：为什么有视觉 Skill 以后反而更不能把所有东西塞进主 Context

MMSkills 最有意思的设计，可能不是：

```text
Skill 里放图片
```

而是：

```text
Branch Loading
```

因为多模态 Skill 会让前面的 Progressive Disclosure 问题更加严重。

一个纯文本 Skill 可能：

```text
2000 tokens
```

直接加载进 main trajectory 尚且能接受。

一个 MMSkill 可能同时包含：

```text
Procedure
+
5 State Cards
+
Full Frames
+
Focus Crops
+
Before / After Views
```

如果几个候选 Skill 都直接加载：

```text
Main Agent Context
├── Live Screenshot
├── Skill A images
├── Skill B images
├── Skill C images
├── Previous Screenshots
├── Conversation
└── Tool Results
```

这不只是 Context 变贵。

视觉 Agent 还有一种额外风险：

```text
Reference Anchoring
```

也就是模型过度相信：

```text
Skill screenshot
```

而忽略：

```text
Live screenshot
```

例如 reference 中：

```text
按钮在右上角
```

当前 UI 中：

```text
按钮已经移动到左侧菜单
```

模型可能围绕旧 screenshot 继续规划。

所以 MMSkills 不直接把完整 skill package 注入 main trajectory，而是：

```text
Main Agent
   │
   │ considers Skill
   ▼
Temporary Branch
   │
   ├── inspect procedure
   ├── inspect state cards
   ├── select required views
   ├── compare with live observation
   └── produce compact guidance
   │
   ▼
Main Agent
   │
   └── grounded action from LIVE screenshot
```

这是另一种 Progressive Disclosure：

```text
不是只决定：
加载哪个 Skill

还决定：
Skill 里的哪几个视觉证据
值得为当前 State 加载。
```


#### Stage 1：先选 State，再决定要不要加载 Image

假设当前使用 Skill：

\[
M_t=(D_t,P_t,S_t,K_t)
\]

Branch 第一阶段做：

\[
(J_t,R_t)
=
\operatorname{SelectViews}
(
O_t,
H_{t-1},
P_t,
S_t
)
\]

其中：

```text
O_t
→ live observation

H_t
→ recent history

J_t
→ relevant state cards

R_t
→ 每个 state 需要哪些 view
```

然后：

\[
V_t
=
\{
K_j^v:
j\in J_t,\;
v\in R_{t,j}
\}
\]

一个很重要的细节是：

```text
R_t
可以为空。
```

也就是说：

```text
Agent 调用了 MMSkill
```

不代表：

```text
必须加载 screenshot。
```

如果：

```text
文本 procedure
+
state card
```

已经足够判断当前状态，就不支付视觉 Context 成本。


#### Stage 2：Branch 输出的是 Guidance，不是 Action

选完 visual evidence 后，临时 branch 才把：

```text
Live State
vs
Skill State
```

进行 alignment。

最后输出：

\[
G_t=
(
\text{applicable}_t,
\text{subgoal}_t,
\text{plan}_t,
\text{do\_not\_do}_t,
\text{verify}_t
)
\]

对应：

```text
applicable
→ 当前 Skill / State 到底适不适用？

subgoal
→ 现在局部目标是什么？

plan
→ 下一段 procedure 应怎样执行？

do_not_do
→ 当前状态下不要做什么？

verify
→ 下一步以后观察什么才算成功？
```

然后：

```text
G_t
```

回到 Main Agent。

Main Agent 最终仍然根据：

```text
Live Observation
```

选择真正 Action。

所以：

```text
Reference Images
→ evidence

Branch Output
→ decision support

Live Screenshot
→ action grounding
```

论文有意不把：

```text
Reference
```

变成：

```text
replay instruction。
```


#### Branch Loading 也可以理解成 Context Isolation

这个结构与前面讲过的 Subagent / Branch Context 有同一个工程动机：

```text
把中间推理产生的大量 Context
隔离出去。
```

传统做法：

```text
Main Context
├── Current Task
├── Live Screenshot
├── Skill Procedure
├── State Cards
├── 8 Reference Images
├── Image Comparison Reasoning
├── More Tool Results
└── Continue...
```

Branch Loading：

```text
Main Context
├── Current Task
├── Live Screenshot
│
├── call branch
│      ├── Skill Procedure
│      ├── State Cards
│      ├── Selected Images
│      ├── alignment reasoning
│      └── return compact G_t
│
├── G_t
└── Continue...
```

主 trajectory 不需要保留 branch 中所有中间内容。

所以这一设计同时解决：

```text
Visual Context Pressure
+
Reference Anchoring
+
Main Context Pollution
```


### 6.5 实验里，多模态 Skill 并不是只让模型“多看了几张图”

MMSkills v3 在：

```text
OSWorld
macOSWorld
VAB-Minecraft
Super Mario Bros / LMGame-Bench
```

上测试 GUI 与 game-based visual agents。

它比较：

```text
No Skill
Text-only Skill
MMSkills
```

而且 Skill 都来自：

```text
non-test trajectories
```

不是把 benchmark test trajectory 直接存成 demonstration。

仅看 OSWorld overall success：

| Model | No Skill | Text-only | MMSkills |
| --- | ---: | ---: | ---: |
| Gemini 3.1 Pro | 44.08 | 40.76 | **50.11** |
| Gemini 3 Flash | 36.65 | 40.27 | **47.97** |
| Qwen3-VL-235B | 21.34 | 28.57 | **39.17** |
| GLM-5V | 28.71 | 36.61 | **38.51** |
| Kimi-K2.6 | 34.98 | 39.66 | **46.59** |
| Qwen3-VL-8B-Instruct | 10.78 | 14.93 | **25.40** |

这里至少能看到三个现象。


#### Text-only Skill 不是稳定正收益

最明显的是 Gemini 3.1 Pro：

```text
No Skill
44.08

Text-only
40.76
```

也就是：

```text
-3.32 pp
```

但 MMSkills：

```text
50.11
```

这和前面 SkillsBench / SWE-Skills-Bench 的结论一致：

```text
增加 procedure
不保证 performance 增加。
```

尤其视觉环境里，procedure 可能让 Agent 更坚定地执行：

```text
错误状态下的正确步骤。
```


#### 小模型的 absolute gain 更明显，但不能直接推出“Skill 可以替代模型能力”

Qwen3-VL-8B-Instruct 在 OSWorld：

```text
10.78
→
25.40
```

增加：

```text
14.62 pp
```

Qwen3-VL-235B：

```text
21.34
→
39.17
```

增加：

```text
17.83 pp
```

这说明显式 external procedural knowledge 对较弱 visual agent 可以补充一部分 model-internal prior。

但：

```text
25.40%
```

本身仍然不是高成功率。

所以正确结论不是：

```text
小模型 + Skill
→ 等于 frontier visual agent
```

而是：

> 当模型缺少特定视觉 procedure / state prior 时，外部 multimodal procedural knowledge 可以显著改变成功率，但无法消除底层 perception、grounding 与 reasoning 能力上限。


#### MMSkills 还缩短了部分 trajectory

如果 Skill 只是：

```text
多调用一个 Branch
多看几张图片
```

很容易预期：

```text
steps 增加。
```

实际论文记录的 interaction 不是这样。

例如 OSWorld + Gemini 3 Flash：

```text
No Skill
13.11 steps

Text-only
15.64
→ +2.53

MMSkills
11.86
→ -1.25
```

Text-only Skill 反而增加交互，而 MMSkills 降低了平均步数。

Qwen3-VL-235B 更明显：

```text
No Skill
15.22

Text-only
13.34
→ -1.88

MMSkills
9.87
→ -5.35
```

在 VAB-Minecraft 上，论文同样观察到 MMSkills 在报告配置中缩短平均 trajectory。

这不能简单解释成：

```text
图片让 Agent 变快。
```

更可能的机制是：

```text
更准确识别 State
→
减少错误探索
→
减少重复低价值 Action
→
更早进入正确 procedure branch
```


#### Agent 也更频繁认为 Skill 与当前 State 相关

在 OSWorld + Qwen3-VL-235B 中：

```text
Text-only Skill invoked
37.50%

MMSkills invoked
65.28%
```

Gemini 3 Flash：

```text
41.11%
→
62.50%
```

论文将其解释为 state card 和 visual cues 提高了 Agent 识别：

```text
“这个 Skill 现在真的适用”
```

的能力。

但 invocation rate 本身不是质量指标。

如果：

```text
100% 任务都调用 Skill
```

反而可能代表：

```text
over-trigger。
```

这里有意义的是它同时伴随：

```text
higher success
+
shorter trajectories
```

所以不能单独把：

```text
Skill 调用次数更多
```

写成 improvement。


#### Ablation：图片、State Card、Branch Loading 各自不是装饰

论文继续做了几种删除实验：

```text
Text-only

MMSkills w/o State Cards

MMSkills w/o Images

Full MMSkills
```

以及：

```text
Direct Loading

Branch Loading

with / without View Selection
```

结果显示删除：

```text
State Cards
```

会降低 Agent 对 runtime state 的 discrimination；

删除：

```text
Keyframes
```

则保留判断规则，但失去 visual grounding evidence。

此外：

```text
Direct-full loading
```

会因为大量 image / state description 污染主 Context 而降低表现。

只增加：

```text
view selection
```

可以缓解，但总体仍接近 baseline；完整的：

```text
Branch Loading
+
View Selection
```

表现最好。

这里得到的结论不是：

```text
“Subagent 总比主 Agent 强。”
```

而是一个更窄的 Context Engineering 结果：

> 当辅助 knowledge 本身非常大、包含多张视觉 reference，并且可能与 live observation 竞争注意力时，把 evidence inspection 隔离到临时 branch，再只返回结构化决策信息，比直接把全部 evidence 注入 main trajectory 更合适。


### 6.6 从这些论文回头看，Skill Engineering 还有哪些没有解决的问题

到这里已经出现：

```text
Agent Skills
Skill Creator
SkillsBench
GraSP
SkillGraph
SkVM
SkillRAE
MMSkills
```

如果只按论文名字记，很容易变成另一种技术清单。

更有用的方式是回到 failure。

一个 Skill-enabled Agent 从任务开始到执行结束，大致经过：

```text
Task
  ↓
Discovery
  ↓
Retrieval
  ↓
Loading
  ↓
Composition
  ↓
Execution
  ↓
Verification
  ↓
Update
```

每一层都可能失败。


#### Discovery Failure：description 写错了

```text
Task should use Skill
        ↓
False Negative
        ↓
Skill never loaded
```

或者：

```text
Task doesn't need Skill
        ↓
False Positive
        ↓
irrelevant procedure enters context
```

对应方法：

```text
Trigger Eval
Description Optimization
```


#### Retrieval Failure：库变大以后选错 Skill

```text
Relevant Skill exists
        ↓
Retriever ranks wrong items
        ↓
Agent gets wrong procedure
```

对应：

```text
better retrieval
subunit retrieval
graph-aware retrieval
```


#### Composition Failure：Skill 都选对了，但关系错了

```text
A
B
C
```

都相关。

但 Agent 执行：

```text
C → A → B
```

而真正 dependency 是：

```text
A → B → C
```

对应：

```text
GraSP
Skill Graph
typed dependency
```


#### Compatibility Failure：Skill 对别的 Model/Harness 写得没问题

例如：

```text
Skill expects subagent
```

但 Harness 没有；

或者：

```text
Skill expects complex shell generation
```

但目标 Model 不稳定。

对应：

```text
SkVM
Capability Profile
Target-specific Compilation
```


#### Environment Failure：procedure 依赖的世界已经变了

例如 Skill 写：

```text
framework v1 API
```

实际 repository：

```text
v2
```

或者：

```text
CLI flag 已删除
dependency 未安装
UI 已改版
```

这也是 SWE-Skills-Bench 里已经观察到的真实负收益来源。

对应：

```text
environment binding
version metadata
regression eval
runtime failure monitoring
```


#### Context Failure：Skill 本身太大

```text
Retriever 选对了
```

但一股脑加载：

```text
4 full Skills
20 references
8 screenshots
```

真正有用的信息反而被稀释。

对应：

```text
Progressive Disclosure
SkillRAE
Branch Loading
```


#### State Recognition Failure：procedure 对，State 错

尤其 visual agent：

```text
正确 Skill
+
正确 Step
+
错误 UI State
=
错误 Action
```

对应：

```text
MMSkills
State Cards
Visual Verification
```


#### Verification Failure：Tool 没报错就被当成成功

```text
deploy()
→ no exception

≠

service healthy
```

对应：

```text
deterministic verifier
postcondition
GraSP node verification
Skill Eval
```


#### Staleness Failure：过去有用的 Skill 现在还应该存在吗？

模型升级以后：

```text
without Skill
```

可能已经追上：

```text
with Skill
```

或者业务 SOP 改变。

对应：

```text
Regression Eval
Capability Uplift Ablation
SkillGraph Deprecation / Evolution
```


#### Distribution Shift：Eval 上有效，不等于用户现场有效

如果 Skill Creator 的测试全是：

```text
清晰输入
标准文件
正常路径
```

生产用户却输入：

```text
残缺文件
奇怪版本
混合语言
权限错误
非标准目录
```

那么：

\[
P_{\text{eval}}(x)
\neq
P_{\text{prod}}(x)
\]

之前的：

\[
\Delta P > 0
\]

不保证仍然成立。

因此生产 Skill Library 最终也需要：

```text
offline eval
+
runtime telemetry
+
failure harvesting
+
regression set expansion
```

而不是一次 benchmark 以后永久冻结。


### 6.7 最后回到工程选择：什么时候真的应该用 Skill？

如果不讨论具体 Agent 产品，我现在会把整个技术栈按问题拆成下面这样：

| 当前问题 | 更直接的机制 |
| --- | --- |
| 用户只是这一次告诉 Agent 一个要求 | Prompt |
| Agent 缺少执行某个动作的能力 | Tool |
| Agent 需要标准化连接外部系统 | MCP |
| 一类任务反复需要同样的 SOP / domain procedure | Skill |
| procedure 中有可确定性执行的计算或检查 | `scripts/` / Tool |
| 有大量长资料，但每次只需要一小部分 | `references/` + Progressive Disclosure |
| Skill 是否该触发经常判断错 | Trigger Eval / Description Optimization |
| 不知道 Skill 是否真的带来提升 | With-Skill vs Baseline Eval |
| 一条状态转换绝对不能让模型自行决定 | Workflow / Runtime Gate |
| 一个任务要组合多个有依赖的 Skill | Skill Graph / Orchestration |
| 失败后只想修当前受影响分支 | GraSP-style Local Repair |
| Skill Library 要随长期经验演化 | SkillGraph-style Maintenance |
| 同一个 Skill 换模型 / Harness 就失效 | SkVM-style Compilation |
| Retrieval 后 Context 仍然太冗余 | SkillRAE-style Context Compilation |
| Agent 必须识别 GUI / Game 的视觉运行状态 | MMSkills-style State-conditioned Evidence |

这里没有：

```text
Skills > Workflow
```

或者：

```text
Graph > Flat Skill
```

这样的固定升级路线。

例如一个：

```text
release production
```

任务，即使模型非常强，也可能最应该写成：

```text
Deterministic Workflow
+
Permission Gate
```

而不是：

```text
给它一个 deployment Skill，
然后相信 Agent 会记得审批。
```

一个：

```text
陌生代码库 debug
```

任务，则很难提前把完整路径编码成 Workflow，更适合：

```text
General Agent
+
Debugging Skill
+
Tools
+
Tests
```

如果公司只有：

```text
6 个 Skills
```

而且任务通常只触发一个，可能根本不需要：

```text
Skill Graph
Compiler
复杂 Retriever
```

如果已经有：

```text
500 个 Skills
```

且一次任务经常需要 5–10 个 procedure，才开始值得认真研究：

```text
selection
composition
dependency
context compilation
```


### 6.8 从 `SKILL.md` 到 Skill Runtime，这条路线真正增加了哪些东西

把这一篇从头压回一个工程演化过程，可以得到：

```text
Stage 0
Prompt

用户每次重复写 procedure
```

然后：

```text
Stage 1
Agent Skill

把 procedure
变成可复用的 Skill package
```

再通过：

```text
name
description
```

实现 discovery：

```text
Stage 2
Progressive Disclosure

Metadata
→ SKILL.md
→ references / scripts / assets
```

接着发现：

```text
“看起来合理”
不能证明有效
```

所以：

```text
Stage 3
Skill Eval

with Skill
vs
baseline

Pass Rate
Tokens
Latency
Failure Pattern
```

Library 继续扩大：

```text
Stage 4
Skill Retrieval + Orchestration

flat list
→
selected Skills
→
dependency structure
```

GraSP 把当前任务的 Skill：

```text
compile
→
typed executable DAG
```

SkillGraph 则维护长期：

```text
Skill relation
usage
success
evolution
```

然后：

```text
Stage 5
Compilation
```

又分成不同方向：

```text
SkVM
Skill
→ target-specific execution variant

SkillRAE
retrieved evidence
→ task-specific execution context
```

到了 visual agent：

```text
Stage 6
Multimodal Procedural Knowledge

Procedure
+
Runtime State
+
Visual Evidence
```

MMSkills 再通过：

```text
Branch Loading
```

避免让 reference evidence 污染主 trajectory。

最后可以把整条研究路线画成：

```text
                          Agent Skill
                              │
             reusable procedural knowledge
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
      Discovery            Execution           Evaluation
          │                   │                   │
   description             SKILL.md          with / without
   trigger eval            scripts               │
          │                   │                   ▼
          │                   │             Skill Creator
          │                   │             SkillsBench
          │                   │
          ▼                   ▼
      Retrieval          Composition
          │                   │
          │                   ▼
          │                GraSP
          │             executable DAG
          │
          ├───────────────┐
          │               │
          ▼               ▼
   Context Compile    Library Evolution
      SkillRAE          SkillGraph
          │               │
          └───────┬───────┘
                  │
                  ▼
         Runtime Specialization
                SkVM
                  │
                  ▼
       Multimodal State Grounding
              MMSkills
```

这张图里没有哪一篇论文真正定义了：

```text
“未来所有 Agent 都必须采用的 Skill Stack”。
```

目前这些工作使用的：

```text
Skill Schema
Graph Representation
Compiler IR
Runtime
Eval Protocol
```

仍然彼此不同，而且绝大多数研究截至 2026 年仍然是 preprint 或新发布系统。

所以我更愿意把它们看成对同一个问题的不同切面：

> **当 Agent 的 procedure 不再硬编码进模型参数，也不想全部硬编码进 Workflow，我们怎样把它作为外部、可发现、可验证、可组合的运行时知识来管理？**

Anthropic Agent Skills 给出的最小答案是：

```text
SKILL.md
+
Progressive Disclosure
```

而后面的论文逐渐补上：

```text
Eval
Retrieval
Graph
Compiler
Runtime
Multimodal State
```

如果以后真的自己实现一个 Skill 系统，我反而不会从 GraSP 或 SkVM 开始。一个更合理的最小实现顺序是：

```text
1. Skill Registry
   name + description + path

2. Progressive Loading
   metadata → SKILL.md → resource

3. Trigger Eval
   should / should-not

4. Task Eval
   with Skill / without Skill

5. Deterministic Scripts
   把可验证部分从 LLM 拿出去

6. Runtime Trace
   记录：
   selected Skill
   loaded resources
   tokens
   latency
   result

7. Skill Library 足够大以后
   再做 retrieval / composition

8. 真正观察到 cross-harness failure
   再研究 compilation

9. 真正进入 visual agent
   再增加 multimodal state package
```

这样每增加一层复杂度，都对应一个已经观察到的 failure。

而不是：

```text
因为最新论文里有 Skill Graph
→ 所以先做 Skill Graph

因为 SkVM 有 Compiler
→ 所以再造一个 Compiler
```

对于我自己的 toy Agent 或学习项目尤其如此。真正值得复现的不是把所有论文架构一次性塞进去，而是先让日志回答：

```text
Skill 没触发？

触发了但没用？

选错 Skill？

Context 太大？

步骤关系错？

环境不兼容？

模型已经不需要这个 Skill？

还是根本缺少 visual state？
```

确定 failure class 以后，再决定应该增加的是：

```text
Eval
Retriever
Graph
Compiler
Verifier
Branch
```

中的哪一层。

这样，Skill 才不是又一套被塞进 Agent Harness 的抽象名词，而是一组可以通过输入、trajectory、benchmark 和 failure log 被检查的工程组件。