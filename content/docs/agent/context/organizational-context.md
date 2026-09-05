---
title: "Organizational Context"
weight: 1
---

## 1. 从 Coding Agent 往前，人类应该放在哪里？


**为什么组织里“没人写下来的知识”，对 Agent 来说等于不存在？**

下一节只引入：

```text
discoverable organizational context
```

也就是：

> 当 Agent 真正进入团队长期工作以后，Harness 的 Context 问题不再只是多少 Token，而变成组织知识是否以可搜索、可授权、可追踪的形式存在。

### 1.1 为什么组织里“没人写下来的知识”，对 Agent 来说等于不存在？


前面七个 Macro 基本都还围绕一个 Coding Agent 展开。

即使加入：

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

这些 Artifact 里。

但如果 Agent 不再只是：

> “帮我修这个 Repo。”

而是真的进入一个团队，连续几周甚至几个月工作呢？

它很快会遇到一种完全不同的问题。

比如今天有人在会议里决定：

> 登录页重构暂停，下季度再做。

产品经理和工程师都知道。

但没有人把它写进：

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

Agent 也很冤。

因为对它来说：

```text
昨天会议室里的口头决定
```

实际上从未进入它能够检索的世界。

Anthropic 在 2026 年 6 月的 **Building effective human-agent teams** 里把这件事说得非常明确：Agent 对组织的理解完全建立在团队让它能够搜索到的文本上，例如 Slack、代码、文档和会议记录；私聊、走廊交流以及它无权访问的材料，都无法成为它的上下文。换句话说，对于 Agent 而言，**没有写下来并且没有权限访问的信息，效果上就等于不存在。**


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

到了组织层，问题反过来了。

不是：

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

我们自己在公司里工作，很容易低估这一点。

比如一个工程师知道：

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

大家也知道它已经死了。

Agent 没有这种长期浸泡式社会经验。

它只能从：

```text
observable artifacts
```

建立组织模型。

所以当人类说：

> Claude 为什么这么没有常识？

很多时候真正的问题不是模型缺少常识。

而是：

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

这些理由当然都还成立。

但 Anthropic 的文章提出了一个很有意思的新视角：

> Agent 本身正在成为组织文档的重要消费者。

因此：

```text
meeting notes
decision logs
design docs
Slack channel
code comments
```

不再只是在服务未来的人。

它们也在服务：

```text
未来的 Agent invocation
```

Anthropic 因此建议，团队做出决定时，应尽量让决定最终落在可搜索的频道、文档或会议纪要中，而不是停留在无法被组织检索的交流里。

这让我觉得：

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

#### 这和我们前面为什么喜欢 Artifact 是同一条逻辑

Macro 1 里，我们说：

```text
Structured Handoff
```

为什么比：

```text
旧 Agent 自己记着
```

可靠？

因为任务状态被显式化了。

Macro 6 又说：

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

这些 Artifact 通信，比单纯 Agent 群聊更稳定。

现在同样的思想扩展到整个组织：

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

仍然是两回事。

所以组织 Context 至少要经历：

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

只有第一步是不够的。

这和普通 RAG 里经常说的：

```text
knowledge exists in corpus
≠
retrieval will surface it
```

其实完全一致。

只是这里的 Corpus 已经从：

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

Anthropic 也提到，如果 Agent 能读取会议决策，它就不容易继续建议已经被 deprioritize 的项目；如果能读到其他团队的产品 Spec，它还能发现别的团队已经成功验证过的模式。

这里最有价值的其实不是：

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

Agent 的出现并没有改变这个问题。

它反而提高了显式知识的价值。

因为人类面对一万个 Slack Thread：

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

Anthropic 就明确认为，因为 Agent 能够比人类快得多地阅读大量文本，它可以发现人类原本会错过的相关工作，从而帮助团队保持同步。

所以以前一个现实问题是：

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

当然不是。

如果只看：

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

这显然不成立。

因为组织 Context 还有另一半：

```text
security boundary
```

Anthropic 的做法也不是取消权限。

恰恰相反，他们强调的是：

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

不应该获得相同授权。

所以：

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

哪些可以访问？

哪些不能？

这是：

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

Anthropic 在文章里对 per-item soft boundary 的批评很有意思。

想象一个团队每天都要判断：

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

而且每个人理解还可能不一致。

所以他们更倾向：

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

特别像。

差的规则：

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

这也正好为下一 Beat 的 autonomy 铺路。

---

#### Agent Identity 又让“谁有权限”变得更清晰

Anthropic 把多人团队 Agent 和传统个人 Assistant 区分得很明确。

单人模式：

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

Anthropic 将这种模式称为 **agent identity**：Agent 使用属于 Workspace 自身、由管理员配置的账号和权限，而不是永远借某个具体员工的个人身份。

这意味着 Context Access 也第一次从：

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

那它的工作世界每天都在变。

甚至可能出现：

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

来说，这种身份模型很难形成稳定自治边界。

所以 Anthropic 在 multiplayer agent 的基础能力中明确列出：

```text
persistent memory

credentials not tied to humans

ongoing broad information access
```

作为 Agent 长期参与团队工作的技术基础。

这三个东西其实是一套：

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

#### 对，我觉得这里可以直接借“Observability”这个类比

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

运维人员只能猜。

组织里的 Agent 也类似。

现实团队每天发生：

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

Agent 同样只能猜。

所以：

```text
Docs
Slack
Meeting Notes
Decision Records
```

某种意义上就是：

> **Organization Observability for Agents。**

这个词是我为了理解做的类比，不是 Anthropic 的正式术语。

但我觉得非常准确：

```text
系统没有 telemetry
→ operator 看不见系统状态

组织没有 searchable artifacts
→ Agent 看不见组织状态
```

---

#### 所以未来的“上下文工程”并不只是给 Prompt 塞资料

这也是我觉得 Context Engineering 容易被写窄的地方。

很多教程把它定义成：

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

这些当然都是 Context Engineering。

但如果 Agent 真正进入团队，最上游的问题其实是：

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

这甚至能反过来解释我们现在写技术博客这件事。

如果我今天只是：

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

都可以重新利用。

同样，在真实开发团队里：

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

这里也需要边界。

否则很容易变成：

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

还不是完整答案。

组织 Context 还需要：

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

这一部分 Anthropic 这篇短文没有展开成完整知识治理框架，因此这里不把它伪装成他们已经解决的问题。

但从 Harness Engineering 角度，这会是很自然的下一层。

---

#### Searchable 不等于 Truth

这一点一定要写清楚。

假设 Agent 搜到：

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

就不一定得到正确组织状态。

所以：

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

这一 Beat 主要讲到前三层。

后面依然还有大量 Research / Engineering 空间。

---

#### “Broad Context”也不能理解成每轮 Prompt 全塞进去

Anthropic 说 Agent 需要 broad ongoing access to information。

这里的：

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

那当然不现实。

更准确的是：

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

才是可扩展形态。

也就是：

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

知识可以存在于更大的外部系统。

当前 Context 只装：

> **这一轮真正需要的部分。**

---

#### 所以“找到”这个动词到这里终于被扩展完整了

父文一开始的第一个词是：

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

这不是正式数学公式。

但非常好记。

如果：

```text
Recorded = 0
```

再好的 Search 没用。

如果：

```text
Discoverable = 0
```

文件放在那也没用。

如果：

```text
Authorized = 0
```

Agent 依然看不到。

这三个缺一不可。

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

后者是为了帮助理解所做的类比，并不是 Anthropic 的正式术语。


现在我们已经回答：

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

但这样一来，一个更棘手的问题马上出现。

假设一个 Team Agent：

```text
记得过去几个月的工作

能搜索大量组织知识

有自己的 Credential

能调用真实工具

甚至可以主动跟进任务
```

那人类到底什么时候应该介入？

如果每一步都：

```text
Ask human
```

Agent 根本没有长期自治。

如果什么都：

```text
Auto allow
```

又显然不可靠。

Anthropic 给出的思路不是：

```text
一开始就给最大自治权
```

而是：

> **让 autonomy 与已经被证明的 reliability 成比例。**

这也是整篇文章最后真正落回“人应该在哪里”的地方。


**为什么 Agent 的自治权应该是“挣出来”的？**

下一节只引入一个概念：

```text
earned autonomy
```

也就是：

> **先用 review、checklist、verifier 和真实结果观察一个 Agent 是否可靠，再随着重复成功逐步放宽人类监督；而模型升级以后，还要重新测试旧 Guardrail 是否仍然需要。**
