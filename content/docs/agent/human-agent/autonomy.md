---
title: "Agent Autonomy"
weight: 1
---

## 1. 为什么 Agent 的自治权应该是“挣出来”的？


上一 Beat 已经解决了一个很基础的问题：

```text
Agent 想长期参与团队工作
        ↓
就必须拥有
可发现的组织上下文
+
稳定身份
+
明确访问边界
```

也就是说，一个真正的 Team Agent 已经不再只是：

```text
等人发 Prompt
→
做一次任务
→
结束
```

而可能逐渐变成：

```text
记得长期目标
        ↓
持续读取团队状态
        ↓
发现新的工作机会
        ↓
主动提出任务
        ↓
执行任务
        ↓
验证结果
```

这时真正棘手的问题来了：

> **人类到底应该在哪一步介入？**

最保守的方案当然是：

```text
每个决定
        ↓
问人

每个 Tool Call
        ↓
问人

每个提交
        ↓
问人

每个下一步
        ↓
问人
```

这样安全。

但也意味着：

```text
Agent autonomy ≈ 0
```

Agent 看起来在长期运行，实际上每几分钟就停下来等待人类。

反过来，如果一开始就：

```text
读什么都行
做什么都行
自己决定优先级
自己改代码
自己提交
自己上线
```

那显然又把：

```text
模型能够行动
```

误当成：

```text
模型已经值得被信任
```

Anthropic 在 **Building effective human-agent teams** 里给出的原则非常明确：

> 团队按照 Agent 已经证明出来的可靠性给予自治，并且有意识地逐步扩大这个自治范围。

这就是这一 Beat 要引入的概念。


* **earned autonomy**：Agent 的自治范围不应该由“它理论上有什么能力”决定，而应该由它在某一类真实任务上已经反复证明出的可靠性决定；成功记录越稳定，人工监督才能越向后移。

---

#### Capability 还是不等于 Trust

Macro 4 我们已经区分过：

```text
Capability
≠
Authorization
```

现在还要再加一层：

```text
Capability
≠
Reliability
≠
Autonomy
```

比如一个 Agent：

```text
会 Edit
会 Bash
会 Git
会 Browser
```

这说明：

```text
它有能力完成复杂开发任务。
```

但并不能推出：

```text
它可以无人监督地完成所有复杂开发任务。
```

因为真正决定自治的不是：

```text
Can it do this?
```

而是：

```text
Can it repeatedly do this
to an acceptable standard
without requiring rescue?
```

这两个问题差别很大。

---

#### 一个最简单的例子：你会不会一上来就让新同事直接发版？

假设团队来了一个新工程师。

他的简历很好：

```text
会 Java
会 Kubernetes
会 AWS
会数据库
```

你不会因此第一天就说：

> Production credential 给你，以后自己上线吧。

更常见的是：

```text
先做几个小任务
        ↓
Code Review
        ↓
看看风格
        ↓
看看测试意识
        ↓
看看遇到不确定问题会不会主动问
        ↓
逐渐扩大 ownership
```

因为：

```text
skill inventory
```

和：

```text
trusted operating scope
```

本来就是两回事。

Anthropic 直接拿人类新同事做类比：一个新同事加入团队后，需要多个 feedback cycle 才能了解他的能力、形成稳定协作方式，并把大量隐式要求逐渐说清楚；Agent 也是如此。

所以：

> **Agent autonomy 更像 onboarding 过程中逐步扩大的 ownership，而不是安装以后默认打开的 feature flag。**

---

#### Anthropic 的 500 个 Bug Fix 特别能说明这个过程

Anthropic 提到，他们的工程师后来已经能够把：

```text
500 个 bug fixes
```

交给团队里的 Agent 独立处理。

但原文紧接着强调：

> 事情并不是一开始就这样。

这一句比“500 个 Bug”本身更重要。

因为如果只截取：

```text
Agent independently handled 500 bug fixes
```

很容易变成：

```text
Claude 已经可以无人值守修 500 个 Bug。
```

真正的方法论却是：

```text
早期
        ↓
高人工监督

反复任务
        ↓
观察错误模式

补充 Context / Skill / Prompt / Checklist
        ↓
再次尝试

重复成功
        ↓
扩大某类任务自治范围

最终
        ↓
可以一次性处理非常多同类工作
```

所以这里真正积累的不是：

```text
勇气
```

而是：

```text
evidence of reliability
```

---

#### 自治权最好按“任务类型”挣，而不是按 Agent 整体挣

Anthropic 有一句特别关键：

> 记录每个 Agent 已经在哪些种类的任务上获得自治，并在重复成功后按任务类型扩大范围。

这意味着自治不是：

```text
Agent A = trusted
Agent B = untrusted
```

这种全局标签。

而应该更像：

```text
Agent A

修简单单测：
high trust

改文档：
high trust

小型 refactor：
medium trust

数据库 migration：
low trust

生产发布：
human required
```

也就是说：

```text
Autonomy
```

是一个：

```text
Agent × Task Type
```

的关系。

这和 Macro 7 的：

```text
Model × Task
→ 是否需要 Evaluator
```

其实非常接近。

---

#### 为什么不能只有一个“Autonomous Mode”开关？

很多 Agent 产品喜欢给出：

```text
Plan Mode
Auto Mode
Full Auto
```

这样的模式。

产品交互上当然需要简化。

但从 Harness Engineering 的角度：

```text
autonomous = true
```

其实过于粗糙。

因为一个 Agent 可能已经非常可靠地：

```text
整理 Issue
跑测试
修 lint
更新依赖锁文件
```

但仍然不应该自动：

```text
删生产数据库
决定产品 Roadmap
修改法律条款
上线高风险配置
```

所以真正的自治边界应该更像：

```text
Task type
+
Effect
+
Reliability history
+
Verification availability
        ↓
supervision level
```

而不是：

```text
Agent = autonomous
```

---

#### Earned Autonomy 的起点反而是“多看”

Anthropic 描述的一个团队案例很具体。

一个工程负责人接手大量 backlog 后，让人和 Agent 一起做整理和代码修改。

一开始：

```text
Humans reviewed every decision
made by an agent.
```

也就是：

```text
Agent 决策
    ↓
Human Review
    ↓
允许继续
```

后来人类逐渐发现：

```text
哪些 decision
其实 Agent 可以稳定自己处理

哪些 hard tradeoff
必须交给人类
```

于是团队进一步教 Agent：

> 碰到真正需要权衡的决定时，主动把它们浮现给人。

这一步特别关键。

因为监督方式从：

```text
Human inspects everything
```

变成了：

```text
Agent handles routine cases
        ↓
Agent detects decision boundary
        ↓
Only escalates hard tradeoffs
```

这才真正开始出现 scalability。

---

#### 最成熟的 Agent 不是“从不问人”，而是“知道什么时候该问”

这点我觉得特别值得写进文章。

我们很容易把 autonomy 理解成：

```text
Ask Human 次数越少
=
Agent 越高级
```

其实并不对。

假设两个 Agent。

#### Agent A

几乎从不问：

```text
遇到歧义
→ 自己猜

遇到风险
→ 自己决定

遇到产品 tradeoff
→ 自己拍板
```

表面看很 autonomous。

但本质可能只是：

```text
不会识别 uncertainty。
```

#### Agent B

平时：

```text
90% routine work
自己完成
```

但在：

```text
不可逆动作
产品方向冲突
缺少关键 Context
高风险权衡
```

时会主动说：

```text
这里需要人类决定。
```

Agent B 的自治能力其实更成熟。

所以真正目标是：

> **减少不必要的人类介入，同时提高必要介入被准确触发的概率。**

这和 Permission System 的：

```text
allow
ask
deny
```

是同一逻辑的组织级版本。

---

#### `ask` 的质量比 `ask` 的数量更重要

Macro 4 里我们已经看到：

```text
ask
```

不是错误。

现在可以再往前一步。

假设 Agent 每半小时问：

```text
我现在要不要读这个文件？
```

```text
我要不要跑测试？
```

```text
我要不要继续？
```

这些问题其实是在浪费：

```text
human attention
```

但如果它跑了两个小时，只在最后问一次：

```text
当前有两个都合理的 migration 策略：
A 更安全但会增加 downtime；
B 无 downtime，但 rollback 风险更高。

这个 tradeoff 需要你决定。
```

这一次 Ask 非常有价值。

所以 Human-in-the-loop 的目标不是：

```text
more human checkpoints
```

而是：

```text
higher-value human checkpoints
```

---

#### Anthropic 甚至直接把 Human Attention 当成稀缺资源

当那个 backlog 团队里的 Agent 逐渐独立以后，负责人开始训练它们：

```text
不要频繁打断人
```

而是：

```text
把多个问题 batch 在一起

重新提供必要 Context
让人不用重新考古

一次只让人处理少量最重要事项
```

Anthropic 明确把 human attention 当作 scarce resource。

这件事很有意思。

传统 Agent 优化常盯着：

```text
Token cost
Latency
GPU cost
```

但进入组织以后，还有一个更贵的成本：

```text
Human interruption cost
```

尤其是：

```text
高质量工程师
产品负责人
领域专家
```

他们的一小时注意力，往往比模型 Token 贵得多。

---

#### 所以 Agent 的目标之一应该是“压缩需要人处理的决策”

可以把一个复杂任务看成：

```text
1000 个微决策
```

传统 Workflow：

```text
Agent
↓
每个不确定点问人

Human 需要处理：
200 个问题
```

成熟 Harness 希望变成：

```text
Agent
↓
自动解决 routine decisions
↓
Verifier 过滤低质量结果
↓
合并相关 uncertainty
↓
只留下真正 high-stakes tradeoff

Human 需要处理：
5 个问题
```

于是 Agent 并不是：

```text
把 Human 删除
```

而是在做：

```text
decision compression
```

这个词是本文为了帮助理解的抽象，不是 Anthropic 的正式术语。

但我觉得很贴切。

---

#### Human 应该逐渐从 Execution Loop 上移

我们可以把人类位置分成几层。

#### Level 0：Human Executes

```text
Human
    ↓
自己完成任务
```

Agent 只是辅助查询。

---

#### Level 1：Human Approves Every Action

```text
Agent proposes
    ↓
Human approves
    ↓
Agent acts
```

类似非常严格的：

```text
tool-by-tool permission
```

---

#### Level 2：Human Reviews Every Result

```text
Agent 自己执行
    ↓
Human review 每个 deliverable
```

比 Level 1 自主，但仍高度同步。

---

#### Level 3：Human Reviews Exceptions

```text
Agent
    ↓
Verifier / Tests / Checklist
    ↓
Routine success
→ 自动继续

Uncertainty / Failure / Tradeoff
→ Human
```

---

#### Level 4：Human Sets Direction

```text
Human
    ↓
North Star
Quality Bar
Policy
Risk Boundary
        ↓
Agent Team
        ↓
长期执行
```

人类不再逐任务操作，而主要负责：

```text
为什么做
什么不能做
什么叫做好
什么时候必须升级给人
```

Anthropic 的组织实践明显是在往后两层移动，而不是简单追求“没人参与”。

---

#### North Star 为什么仍然要由人定义？

Anthropic 前一节谈 proactivity 时强调：

```text
north star
```

始终由人类讨论、辩论并记录下来，然后才交给 Agent 使用。

这其实正好说明：

```text
Autonomous execution
```

不等于：

```text
Autonomous purpose
```

Agent 可以越来越擅长：

```text
怎样达到目标？
```

甚至主动提出：

```text
有哪些新工作值得做？
```

但：

```text
我们最终追求什么？
```

这种价值和组织方向问题仍然需要人类定义。

所以一个成熟的人机结构不是：

```text
Human:
做所有决定

→

Agent:
做所有决定
```

而更像：

```text
Human
  ↓
North Star
Quality Bar
Risk Boundary
  ↓
Agent
  ↓
Planning / Execution / Verification
  ↓
Escalate exceptional tradeoffs
  ↓
Human
```

这是一个层级变化，不是简单替代。

---

#### Verification 是 Earned Autonomy 的基础设施

Anthropic 特别强调：

> 最好的 long-running Agent，在人真正看到结果以前，就已经拥有多种方式验证自己的工作。代码有测试，文档也可以使用 rubric 和 style guide。

这和 Macro 5 完全连起来了。

为什么：

```text
Verifier
Tests
Rubric
Checklist
```

会让 Agent 更 autonomous？

因为如果没有 verification：

```text
Agent 完成
    ↓
唯一 QA
    ↓
Human
```

那么人类永远是必经节点。

而有了：

```text
Agent 完成
    ↓
Test
    ↓
Verifier
    ↓
Checklist
    ↓
只有异常才 Human
```

才能真正把：

```text
Human review
```

从同步 mandatory step 变成：

```text
exception path
```

所以：

> **Verification 不只是质量保障组件，也是自治扩张的前提。**

---

#### 这正好重新解释了 Doer–Verifier

Macro 5 里，我们从：

```text
self-evaluation bias
```

出发引入 Evaluator。

现在组织层又多出一个作用：

```text
Doer
    ↓
Verifier
    ↓
高置信 Routine Outcome
    ↓
不需要 Human
```

只有：

```text
Verifier Fail
Verifier Uncertain
High-stakes Tradeoff
```

才：

```text
↓
Human
```

于是：

```text
Doer-Verifier
```

不只是：

```text
质量更好
```

还改变了：

```text
Human supervision topology
```

---

#### 人类真正设置的是“Bar”，而不是每一份答案

Anthropic 有一句很适合这一节：

> 当人类设置质量标准，并确保 Agent 承担的工作都有办法被检查，质量就更不容易偏离最初意图。

也就是说，人类从：

```text
检查每个答案
```

转变为：

```text
定义什么算好答案
```

例如代码：

```text
Test Suite
Review Checklist
CI
```

文档：

```text
Style Guide
Rubric
Required Sections
Fact checks
```

数据分析：

```text
Invariant
Reconciliation
Expected Range
```

于是：

```text
Human judgment
```

被部分 externalize 成：

```text
Verification Artifact
```

这又和上一 Beat 的：

```text
组织隐式知识
→
显式 Artifact
```

完全接上。

---

#### Earned Autonomy 其实是一个反馈控制过程

可以把它画成：

```text
Task Type
   ↓
Agent Executes
   ↓
Verification
   ↓
Human Review
   ↓
Outcome History
   ↓
Reliable repeatedly?
   │
   ├─ No
   │   ↓
   │  tighter supervision
   │  better prompts
   │  better skills
   │  better verifier
   │
   └─ Yes
       ↓
     expand autonomy
```

然后继续循环。

这不是：

```text
一次认证
```

而是持续校准。

---

#### 为什么模型升级以后还要重新测试？

这点和 Macro 7 几乎是同一个原则。

Anthropic 明确提醒：

> 模型变化以后，要重新测试之前的任务；Prompt 可能需要重新写，而过去有帮助的 Guardrail 也可能限制更聪明模型寻找更好的解法。

也就是说：

```text
earned autonomy
```

不能理解成：

```text
Model X 在 2026-06
证明这个任务可靠

        ↓

以后所有 Model 永远继承
同一个 trust level
```

因为换模型以后：

```text
行为可能更好
```

也可能：

```text
行为方式发生变化
```

甚至旧 Harness：

```text
过度约束
```

新的模型。

所以 autonomy policy 同样需要：

```text
version awareness
```

---

#### 新模型不一定只需要“更多 Guardrail”

模型升级以后常见本能是：

```text
能力更强
        ↓
风险也更大
        ↓
再加更多限制
```

某些场景当然需要。

但 Anthropic 提醒的另一面是：

```text
旧 Guardrail
```

可能本来只是为了修复：

```text
旧模型弱点
```

而不是永恒安全原则。

例如 Macro 7 已经看到：

```text
Sonnet 4.5
需要 Context Reset

Opus 4.5
不再需要
```

组织层同样如此。

某个旧 Checklist：

```text
强制先拆成 10 个小步骤
```

可能以前防止 Agent 漂移。

新模型已经能稳定完成整体任务以后：

```text
这套强制拆分
```

反而可能：

```text
增加摩擦
破坏整体规划
限制创造性方案
```

所以：

> **Trust calibration 既可能收紧自治，也可能删除已经过时的限制。**

---

#### Earned Autonomy 不是单向越来越大

这里还应该多补一层。

“挣出来”很容易让人理解成：

```text
Level 1
→
Level 2
→
Level 3
→
永远升级
```

但实际更合理的是：

```text
reliability changes
        ↓
autonomy changes
```

比如：

```text
任务环境改变

Tool 权限扩大

进入新代码库

模型版本改变

业务风险提高

Verifier 失效
```

都可能意味着：

```text
原来的 trust evidence
不能完全复用
```

于是 autonomy 应该：

```text
重新收紧
        ↓
重新验证
        ↓
再逐步放开
```

所以真正关系是：

```text
Autonomy ∝ demonstrated reliability
```

而不是：

```text
Autonomy ∝ time since installation
```

---

#### 一种很实用的“Autonomy Ladder”

如果以后自己设计 Agent Workflow，我觉得完全可以显式维护类似：

```text
A0 — Suggest only
只提出建议，不执行

A1 — Execute with approval
行动前要人确认

A2 — Execute, review every result
自己行动，但结果逐项人工 Review

A3 — Execute with automated verification
Routine Task 自动做；
Verifier 通过后直接结束

A4 — Exception-based escalation
正常工作无人介入，
只把失败 / 不确定 / hard tradeoff 提给人

A5 — Proactive within North Star
不仅响应任务，
还能主动发现并提出新工作
```

这不是 Anthropic 官方分级。

但它很好地表达：

```text
earned autonomy
```

不是一个：

```text
on / off
```

开关。

---

#### 哪些事情最适合先获得自治？

通常应该从：

```text
低风险
可重复
容易验证
Failure 可恢复
```

的任务开始。

例如：

```text
修明确 failing test

整理 backlog

生成格式化报告

修 lint

批量机械改动

更新文档索引
```

因为这些任务：

```text
Expected Outcome 清晰
Verifier 容易建立
出错容易发现
Rollback 便宜
```

这也是为什么 Anthropic 案例里，Agent 团队先处理：

```text
backlog classification
medium / low complexity code changes
```

而不是直接接管所有高风险 tradeoff。

---

#### 高风险任务不是“永远不给 Agent”，而是需要更强证据

例如：

```text
数据库 Migration
生产发布
高价值客户配置
权限策略
```

完全可以逐渐自动化。

但它们需要：

```text
更强 test
更强 verifier
dry-run
rollback
staging
audit log
human checkpoint
```

所以 autonomy 和 verification 应该一起增长：

```text
Low autonomy
    ↓
简单 Verification

Higher autonomy
    ↓
更强 Verification

Very high autonomy
    ↓
多层 Verification
+
明确 Escalation
+
Recoverability
```

这也是为什么：

> **Autonomy 不能脱离 Harness 单独讨论。**

---

#### Recoverability 其实也是自治的前提

再回到 Macro 1。

如果 Agent 一旦失败：

```text
任务状态全丢
```

那你当然不敢让它长期自己跑。

如果：

```text
Transcript
Handoff
Checkpoint
Git
Worktree
Rollback
```

让错误可以恢复，

人类就更敢把执行距离放长。

所以：

```text
Autonomy
```

背后的真正支柱至少包括：

```text
Observability
Verification
Permission
Recoverability
```

不是纯粹：

```text
模型变聪明
```

---

#### 一个很重要的视角：Autonomy 是 Harness 的输出，不只是模型属性

很多讨论会说：

```text
Claude 有多 Autonomous？
```

好像 autonomy 是模型 benchmark。

但同一个模型：

#### Harness A

```text
没有测试
没有权限边界
没有状态恢复
没有 verifier
```

你可能只敢：

```text
让它改一个小文件
然后人工看。
```

#### Harness B

```text
有明确 Spec
有 Tool contract
有 Permission
有 CI
有 Verifier
有 Recoverability
有 Escalation
```

同一个模型，你可能敢让它：

```text
连续跑几个小时。
```

所以：

```text
Operational autonomy
```

其实更像：

```text
Model capability
×
Harness reliability
×
Task verifiability
×
Risk tolerance
```

仍然只是帮助理解的公式。

但它比：

```text
“这个模型支持 Autonomous Agent”
```

准确很多。

---

#### Human-in-the-loop 最终变成了 Human-on-the-loop

这个术语不是 Anthropic 这篇文章的正式表述，但很适合帮助理解。

#### Human-in-the-loop

```text
Agent 每一轮
都依赖 Human
```

Human 是 execution dependency。

#### Human-on-the-loop

```text
Agent 系统正常自主运行

Human
负责：
目标
政策
监督
例外
升级
```

Human 不需要每一步参与，但仍然掌握：

```text
direction
quality bar
risk boundary
```

Anthropic 描述的成熟团队已经明显朝这种结构移动：随着 Agent 更独立，负责人减少日常指导，把注意力集中到真正需要人类判断的部分。

---

#### 这就是为什么人类仍然应该拥有 North Star

Agent 可以越来越擅长：

```text
How?
```

甚至越来越擅长：

```text
What next?
```

但 Anthropic 仍然明确把：

```text
North Star
```

放在人类手中。

因为：

```text
Which goal is worth pursuing?
```

不是单纯技术执行问题。

它包含：

```text
业务价值
组织优先级
风险偏好
伦理边界
长期战略
```

所以 Team Agent 的终极形态并不是：

```text
Human disappeared
```

而更像：

```text
Human:
“我们为什么做、
什么最重要、
什么不能接受。”

Agent:
“我怎样持续把这个目标推进。”
```

---

#### 所以“人类应该放在哪里”的答案已经出来了

不是：

```text
永远站在 Tool Call 前面。
```

也不是：

```text
完全离开系统。
```

而是逐渐站到这些位置：

```text
North Star
    ↓
定义目标

Quality Bar
    ↓
定义什么算完成

Policy
    ↓
定义什么可以自主做

Verification Design
    ↓
定义怎么检查

Escalation Boundary
    ↓
定义什么时候必须找人
```

具体执行：

```text
Read
Edit
Search
Test
Routine decision
```

则尽量交给 Harness。

---

#### 这也终于把整篇文章里的“人”放回来了

最开始我们一直问：

```text
为什么一个会写代码的模型
还是不能自己长期完成任务？
```

于是 Harness 开始接管：

```text
State
Action
Observation
Permission
Verification
Delegation
```

看起来人类越来越远。

但真正发生的是：

```text
Human responsibility
```

在上移。

从：

```text
“这一行代码怎么改？”
```

上移到：

```text
“这个 Agent 应该追求什么？”
```

从：

```text
“这条命令能不能执行？”
```

上移到：

```text
“什么类型的动作可以长期自动授权？”
```

从：

```text
“这个结果有没有问题？”
```

上移到：

```text
“怎样定义一个可重复使用的 Verification Bar？”
```

这才是 Human-Agent Team 真正的结构变化。

---

#### 一个适合面试的回答：Human-in-the-loop 应该放在哪里？

如果面试官问：

> Long-running Agent 里是不是 Human-in-the-loop 越少越好？

我会回答：

> 不是。目标不是机械地减少 Human-in-the-loop，而是把人类注意力从 routine execution 移到高价值 decision boundary。Anthropic 的做法是按任务类型记录 Agent 已证明的可靠性：早期人工检查每个决定，通过 tests、rubrics、verifier 和 failure review 建立信任；重复成功以后，逐渐扩大该类任务的自治，只把高风险 tradeoff 或异常情况升级给人。模型变化后还要重新测试，因为旧 Prompt 和 Guardrail 可能不再合适。

再压成一句：

> **Autonomy is earned per task, not granted per agent.**

---

#### Macro 8 到这里可以收束

Beat 8.1 回答：

```text
Agent 要长期参与团队，
必须先能看到团队的真实状态。
```

所以需要：

```text
Recorded
∩
Discoverable
∩
Authorized
```

的组织上下文。

Beat 8.2 回答：

```text
看得到、做得到以后，
Agent 到底可以自己走多远？
```

答案是：

```text
Autonomy
        ↑
随 repeated verified success 增长

Human intervention
        ↓
从 routine step
迁移到 exception / tradeoff / policy
```

把两节拼在一起：

```text
Discoverable Context
        ↓
Agent 能理解团队

Clear Role + Tools
        ↓
Agent 能行动

Verification
        ↓
Agent 能证明工作

Reliability History
        ↓
Agent 挣到自治

Escalation Boundary
        ↓
Human 只处理真正需要人的决策
```

这就是从：

```text
Coding Assistant
```

走向：

```text
Long-running Team Agent
```

真正发生的变化。

---

#### 源码与证据边界

Anthropic 2026 年 6 月 24 日的 **Building effective human-agent teams** 可以直接确认：

* Anthropic 团队按照 Agent 已经表现出的 reliability 来给予自治，再有意识地扩大自治范围；
* 工程团队后来能够让 Agent 独立处理约 500 个 Bug Fix，但这种自治是逐步建立出来的，并非初始状态；
* Anthropic 建议早期人工检查 Agent 工作、提供反馈并设计 verification checklist，再使用 verifier、reflection 和 repeated success 扩大自治；
* 自治应按 task type 记录和扩展，而不是把整个 Agent 简单标记成“trusted”；
* 在一个工程团队案例中，人类最初检查 Agent 的每一个决定，之后逐步教 Agent 主动把 hard tradeoff 升级给人；
* 随着 Agent 更独立，人类开始要求其 batch questions、提供必要背景，并减少不必要的人类注意力消耗；
* Anthropic 强调模型变化以后要重新测试任务，因为过去有效的 Prompt 与 Guardrail 可能反而限制更强的新模型；
* 对长期 Agent 而言，在人类看到结果前建立 tests、rubrics、verifier 等多种 verification mechanism，有助于保持质量并减少人工同步监督。

### 1.1 Macro 8 小结

如果这一 Macro 最后只能留一句，我会写：

> **人类不应该永远充当 Agent 的下一步按钮；更合理的位置，是定义目标、质量标准、权限边界和升级条件，再让 Agent 在已经被验证可靠的任务范围内逐步挣到自治。**

---


到这里，正文主线其实已经完整了。

我们最开始的问题是：

```text
模型已经会读代码、改代码、运行命令，
为什么长任务还是会坏？
```

一路拆下来，答案不是：

```text
因为 Prompt 还不够好。
```

而是 Agent 的可靠工作依赖一整套 Harness 责任：

```text
Context 不应该只存在于模型脑子里
        ↓
State 必须跨 turn / process 存活

模型输出不等于现实动作
        ↓
Tool 才把 intention 变成 effect

Tool 不能只是函数
        ↓
需要 schema / effect / permission / scheduling

动作发生不等于任务完成
        ↓
需要 grounded verification

Evaluator 也不天然可靠
        ↓
需要 trace-driven calibration

Multi-Agent 不等于多开模型
        ↓
要按 failure mode 和 role boundary 分工

Harness 也不能永久叠加
        ↓
模型升级以后重新 ablate

Agent 越长期工作
        ↓
组织 Context、Identity、Access 越重要

Agent 越可靠
        ↓
Human supervision 越应该上移

## 2. Human on the loop：监督从“推动执行”变成“观察、抽样与接管”

上一节留下的问题是：如果人不再负责批准 Agent 的每一步，监督应该放到哪里？

一种更适合 long-running Agent 的结构，是把人从 execution loop 内部移到 loop 外部：

```text
Human-in-the-loop

Agent
  ↓
Action
  ↓
Human Approval
  ↓
Action
  ↓
Human Approval
```

变成：

```text
Human-on-the-loop

             Human
               │
        observe / review
               │
               ▼
      ┌──────────────────┐
      │    Agent Loop    │
      │                  │
      │ plan             │
      │   ↓              │
      │ act              │
      │   ↓              │
      │ observe          │
      │   ↓              │
      │ verify           │
      │   ↓              │
      │ retry / continue │
      └──────────────────┘
               │
               │ exception
               ▼
             Human
```

这里的 `Human on the loop` 是本文为了描述监督位置使用的分析框架，不是 Anthropic 在 **Building effective human-agent teams** 中定义的正式术语。它想表达的不是“人退出系统”，而是人不再承担维持 Agent loop 运转的同步职责。

在这种结构里，Agent 可以自己完成：

```text
search
→ edit
→ test
→ inspect failure
→ retry
→ verify
```

人则保留另一组职责：

```text
设定目标
观察状态
检查结果
抽样 Review
处理异常
重新划定边界
```

两种监督模式的区别并不是有没有 Human，而是谁负责日常 control flow。

```text
Human-in-the-loop

Human
  ↓
推动下一步
  ↓
Agent
```

```text
Human-on-the-loop

Human
  ↓
定义运行条件

Agent
  ↓
自己推动下一步

Human
  ↓
监督运行结果
```

这一步如果只写成“减少人工参与”，反而会漏掉最关键的系统要求。人可以退出逐动作审批，是因为 Harness 必须补上别的控制面：任务状态要可见，结果要能验证，异常要能被识别，运行过程还必须允许暂停和接管。

所以 Human-on-the-loop 并不比 Human-in-the-loop 少一层控制。

它只是把控制从：

```text
approve every step
```

换成：

```text
observe the system
+
verify its outputs
+
intervene at defined boundaries
```

### 2.1 人退出 Execution Loop 的前提，是 Agent 的运行状态能够被看见

假设我同时启动两个 Agent。

Agent A 的界面只有：

```text
Running...
```

半小时以后变成：

```text
Done
```

Agent B 则持续保留：

```text
Goal
Current phase
Files changed
Tests executed
Verification status
Open questions
Budget consumed
Last checkpoint
```

即使两个 Agent 最终生成完全一样的代码，我也更容易允许 B 连续运行更久。

原因并不在于 B 的模型更可靠，而是它提供了更多可以监督的状态。

Human-on-the-loop 依赖的第一个条件就是 **Observability**。

一个最简单的 long-running task 至少存在三种状态：

```text
Task State
Runtime State
Artifact State
```

`Task State` 回答：

```text
目标是什么？
现在做到哪一步？
还有什么没有完成？
```

例如：

```text
Goal:
Fix flaky authentication test

Phase:
verification

Completed:
- reproduced failure
- identified race condition
- changed session cleanup
- unit tests passed

Pending:
- integration tests
- final diff review
```

`Runtime State` 回答：

```text
Agent 现在还活着吗？
它在做什么？
是否陷入重复循环？
已经消耗了多少资源？
```

可能包括：

```text
running
waiting
blocked
retrying
failed
completed
```

以及：

```text
tool calls
elapsed time
token usage
retry count
last progress timestamp
```

`Artifact State` 则回答：

```text
Agent 到目前为止真正改变了什么？
```

例如：

```text
3 files modified
1 migration created
27 tests passed
2 tests skipped
1 generated artifact
```

把这些信息放在一起，人看到的不应该只是一串模型消息：

```text
I will inspect the repository.
I found the likely issue.
I will now modify...
```

更有用的是一个能够和实际环境对应的状态面：

```text
                  Task
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
     Progress   Artifacts   Verification
        │          │          │
        └──────────┼──────────┘
                   ▼
                 Human
```

这和传统聊天交互差别很大。

聊天窗口天然把：

```text
conversation
```

当作主要状态。

但 Agent Runtime 真正需要监督的是：

```text
world state
+
task state
+
execution evidence
```

因为模型说：

```text
“已经修复了。”
```

并不等于环境已经满足：

```text
tests pass
```

模型说：

```text
“只修改了 auth.ts。”
```

也不等于 Git diff 里真的只有这个文件。

因此 Human-on-the-loop 需要尽量把监督建立在外部状态和 artifact 上，而不是建立在 Agent 对自己行为的叙述上。

对于 Coding Agent，比较容易观察：

```text
git diff
test result
lint result
build result
CI status
```

对于研究 Agent，也可以观察：

```text
已读取文献
引用来源
证据表
未解决冲突
最终报告
```

对于数据任务，可以观察：

```text
input snapshot
rows processed
validation failures
output artifact
summary statistics
```

共同点都是：

```text
Agent says X
```

不能作为唯一证据。

更稳定的结构是：

```text
Agent acts
    ↓
Environment changes
    ↓
Harness records state
    ↓
Verifier produces evidence
    ↓
Human observes
```

这也是为什么 Human-on-the-loop 不等于：

```text
把 Agent 放后台，
偶尔回来看看有没有完成。
```

如果系统只给一个：

```text
running / done
```

那么人虽然形式上站在 loop 外面，实际上没有足够的信息进行监督。

最后遇到失败时只能重新打开整个 transcript，从头考古：

```text
Agent 为什么做这个修改？

什么时候偏离目标的？

哪一步开始失败？

测试到底有没有跑？

这个决定是根据什么做的？
```

这不是真正降低了 Human Work，只是把同步 Review 变成了事后的 Debugging。

因此 Human-on-the-loop 的第一个工程要求可以写成：

```text
Autonomy requires observability.
```

但这里的 observability 不能只理解成“保存日志”。

真正要让人看见的是那些能够改变监督决策的信息：

```text
Goal
Progress
Effects
Evidence
Exceptions
```

而不是所有 token、所有 Tool Output、所有中间 Thought 都完整倾倒给人。

否则又会进入另一个问题：状态虽然都可见了，但人根本看不过来。

---

### 2.2 Human Review 不需要覆盖所有过程，但必须覆盖能够证明结果的 Evidence

人从 execution loop 退出以后，会出现一个很直接的风险。

以前：

```text
Agent 做一步
Human 看一步
```

所以错误可能很快被发现。

现在：

```text
Agent
  ↓
连续工作几十分钟
  ↓
Human 才看到结果
```

如果监督机制只是把 Review 推迟到最后：

```text
manual review later
```

那错误可能在内部累计很久。

因此 Human-on-the-loop 不能简单依靠：

```text
Agent 更聪明
→
所以少看一点
```

它需要把原来由 Human 连续承担的一部分检查工作，转移给 Verification。

Anthropic 在 **Building effective human-agent teams** 中明确提到，他们观察到表现较好的 long-running Agent 往往会在结果交给人以前使用多种方式验证工作。代码可以运行测试，技术文档也可以使用 rubric 和 style guide；还有一些团队会把执行和检查拆给两个不同 Agent，也就是 Doer–Verifier。

于是监督链可以从：

```text
Agent
  ↓
Human checks everything
```

变成：

```text
Agent
  ↓
Task execution
  ↓
Self-check
  ↓
Tests / Rubric / Verifier
  ↓
Evidence
  ↓
Human Review
```

这不是为了证明：

```text
Verifier 能代替 Human
```

而是为了把两类工作分开。

有些判断机器非常适合反复执行：

```text
测试是否通过？
格式是否符合规范？
引用是否存在？
输出 schema 是否有效？
文件是否超出允许范围？
```

如果这些东西仍然每次都让人手动检查，人退出 execution loop 后也不会获得多少时间。

但另一些判断并没有那么容易自动化：

```text
这个产品 tradeoff 是否值得？
这个结果在业务上是否可以接受？
当前设计有没有偏离团队长期目标？
两个都合法的方案应该选哪个？
```

这些仍然需要 Human Judgment。

因此更合理的分层是：

```text
Machine-verifiable constraints
        ↓
Verifier

Judgment-heavy decisions
        ↓
Human
```

例如一个 Coding Agent 修改完成以后，可以先交：

```text
Changed files:
- src/auth/session.ts
- tests/session.test.ts

Verification:
- pnpm lint: pass
- pnpm test session: 18/18 pass
- pnpm typecheck: pass

Scope:
- no dependency changes
- no migration
- no public API change
```

而不是只交：

```text
修好了，请 Review。
```

这样 Human Review 的输入已经从：

```text
整个执行过程
```

压缩成：

```text
Artifact
+
Verification Evidence
+
Remaining Decisions
```

人在 loop 外面要做的也不再是重放 Agent 的全过程，而是检查：

```text
它最终改变了什么？

已有 verifier 能证明什么？

还有哪些东西 verifier 不能证明？
```

这一区别对长任务尤其明显。

假设 Agent 一晚上完成 20 个互相独立的小型 bug fix。

如果第二天人面对的是：

```text
20 × 完整 transcript
```

Human-on-the-loop 没有任何意义。

如果面对的是：

```text
Bug #1
diff
tests
risk
status

Bug #2
diff
tests
risk
status

...

Bug #20
diff
tests
risk
status
```

人至少可以进行：

```text
review by evidence
```

再进一步，如果这些任务属于已经比较稳定的类型，就可以使用：

```text
full automated verification
+
sampled human review
```

例如：

```text
100 low-risk changes
        ↓
100 automated checks
        ↓
10 sampled human reviews
```

当然，`10` 并不是一个通用比例。具体采样率取决于任务风险、错误代价、历史表现和 verifier 强度。

这里真正发生的是监督单位发生了变化：

```text
每一步动作
        ↓
每个可验证结果
```

也可以理解成：

```text
Process supervision
        ↓
Evidence-backed outcome supervision
```

这不是所有 Agent 场景都能一步切过去。

如果任务缺少有效 verifier，例如：

```text
“重新设计我们的产品定位。”
```

那么：

```text
output exists
```

很难自动推出：

```text
output is correct
```

人类 Review 的比例自然会更高。

所以 Human-on-the-loop 能退多远，并不只取决于模型。

它还取决于：

```text
How observable is the task?

How verifiable is the output?
```

可以粗略写成：

```text
More reliable verification
        ↓
Less process-level supervision required
```

这也解释了为什么同一个 Agent 在不同任务上的自治范围不应该一样。

它可能已经能够无人盯守地处理：

```text
lint fix
test repair
dependency update
documentation formatting
```

但到了：

```text
architecture change
schema migration
product requirement
security-sensitive operation
```

仍然需要更密集的人类判断。

后面讲 `Earned Autonomy` 时会继续回到这个问题。

此处只需要得到一个中间结论：

```text
Human-on-the-loop
```

并不是取消 Review，而是把 Review 从“持续观察 Agent 怎么做”逐渐移动到：

```text
检查 Agent 产生的可验证证据
```

这使人可以离开 execution loop，却不必完全依赖模型自报成功。

---

### 2.3 Human Attention 也有 Budget，Agent 需要压缩交给人的信息

当 Agent 可以运行得更久以后，一个新的瓶颈会出现。

以前的问题是：

```text
Agent 每一步都等 Human
```

现在可能变成：

```text
Agent 自己做很多事
        ↓
最后把所有东西一起扔给 Human
```

例如，一个 Agent 工作两个小时以后发来：

```text
17 个问题
43 个文件修改
12 个测试结果
6 个不确定点
4 个设计选择
3 个失败尝试
2 个需要产品确认的问题
```

这在技术上已经实现了 asynchronous execution。

但人的负担未必降低。

只是从：

```text
continuous interruption
```

换成：

```text
information overload
```

Anthropic 在自己的工程团队案例里专门处理了这个问题。随着 Agent 逐渐独立，负责人开始要求它们把 **human attention 当作稀缺资源**：问题尽量合并后一次提出；在请求人处理之前重新提供必要 Context；同时限制一次让一个人处理的事项数量。Anthropic 还提到，有团队专门让某个 Agent 负责决定哪些信息应该 batch、哪些事情值得升级给 Human。

这个变化很适合用一个简单的成本模型理解。

传统 Agent 系统经常优化：

```text
Token Cost
Latency
Tool Cost
Compute Cost
```

进入 Human-Agent Team 以后，还多了一项：

```text
Human Attention Cost
```

它又至少包含：

```text
Interruption Cost
Context Reload Cost
Decision Cost
Review Cost
```

于是一个需要人处理的问题，成本并不只和问题本身长度相关。

假设 Agent 每隔十分钟发一句：

```text
要不要继续？
```

每句话都很短。

但人需要：

```text
切回任务
    ↓
回忆上下文
    ↓
查看当前状态
    ↓
判断
    ↓
回复
    ↓
重新回到自己的工作
```

这种碎片化 interruption 很贵。

相反，Agent 一小时以后一次性交：

```text
我完成了 8 个 routine decisions。

还有 2 个问题需要你处理：

1. API 是否继续兼容 v1？
   当前调用量：...
   删除后影响：...
   两个方案：...

2. migration 能否接受 10 分钟只读？
   原因：...
   alternatives：...
```

消息更长，但 Human Attention Cost 可能明显更低。

因此好的 Agent communication 不应该优化：

```text
message length
```

而应该优化：

```text
time-to-decision
```

换句话说，人真正需要的不是更多信息，而是足够完成当前判断的信息。

可以把一次升级给人的内容组织成：

```text
Why am I seeing this?

What has already happened?

What decision is required?

What are the options?

What changes if I choose A or B?
```

例如不要发：

```text
migration 有问题，需要你看看。
```

也不要把完整日志直接贴出来：

```text
[5000 lines of migration output]
```

而可以压缩成：

```text
Decision required:
是否允许最多 15 分钟只读窗口。

Why:
当前表有约 8M rows。
online migration 在 staging 中两次触发 lock timeout。

Verified:
- offline migration: 11m42s
- rollback test: pass
- backup restore: pass

Options:
A. 15 分钟只读窗口
   风险较低，已有完整 rollback

B. 继续设计 online migration
   无 downtime，但当前方案尚未通过 lock test
```

这其实是一种：

```text
decision compression
```

这个词是本文为了描述结构使用的，不是 Anthropic 的正式术语。

Agent 内部可能处理了：

```text
100 个 micro-decisions
```

但经过：

```text
routine handling
+
verification
+
aggregation
+
prioritization
```

最后真正暴露给人的可能只有：

```text
3 个 decisions
```

流程大致变成：

```text
100 micro-decisions
        │
        ├── 82 routine
        │      ↓
        │   Agent handles
        │
        ├── 12 verifiable
        │      ↓
        │   Verifier checks
        │
        └── 6 uncertain
               ↓
            aggregate
               ↓
          2 human decisions
```

这个结构有一个容易被忽略的前提：Agent 需要保留足够好的 Context，才能在升级问题时重新构造人所需要的信息。

否则人会收到：

```text
方案 A 还是方案 B？
```

却不知道：

```text
A/B 是什么？
为什么现在要选？
之前已经尝试过什么？
```

最终还是要手动翻历史。

所以一次高质量 Escalation 应该尽量是 self-contained 的。

不是说必须复制全部历史，而是把完成当前判断需要的局部 Context 一并带回来：

```text
Escalation
=
Decision
+
Relevant Context
+
Evidence
+
Alternatives
+
Consequences
```

这也和 Anthropic 所说的“repeat key context to get a human up to speed quickly”对应。

Human Attention Budget 还会进一步影响 Agent 能做多少工作。

Anthropic 提到，有团队会直接限制 Agent 每天完成的工作量，使人类仍然能够有意义地参与 Review；这些 guardrail 一方面保证需要人工检查的项目数量保持可持续，另一方面也避免团队成员因为把某类任务完全交出去而失去自己希望保留的技能。

这一点很容易和：

```text
Agent 越多
→ throughput 越高
```

发生冲突。

假设：

```text
1 Agent
→ 10 PR/day

10 Agents
→ 100 PR/day
```

如果团队每天只能认真 Review：

```text
20 PR
```

那么真正的系统 throughput 并不是：

```text
100 PR/day
```

而是：

```text
min(
    Agent Production Capacity,
    Verification Capacity,
    Human Review Capacity
)
```

即：

```text
System Throughput
=
min(
  Agent Throughput,
  Verifier Throughput,
  Human Attention Throughput
)
```

Agent 产生工作越快，不代表整个 Human-Agent Team 的 throughput 就一定越高。

超过 Review capacity 以后，结果可能只是：

```text
review backlog
        ↓
less careful review
        ↓
lower feedback quality
        ↓
more accumulated mistakes
```

所以 Human Attention 并不是 Agent 系统外部一个无限供应的东西。

它本身就是 runtime capacity 的一部分。

---

### 2.4 Human on the loop 最大的风险不是 Agent 停下来，而是它一直跑却已经偏了

Human-in-the-loop 有一个很明显的失败状态：

```text
Waiting for approval...
```

人很容易发现。

Human-on-the-loop 的失败可能反而没有这么显眼。

Agent 可以一直正常运行：

```text
tool call successful
test passed
task progressing
```

但目标已经开始偏移。

例如用户最开始要求：

```text
修复登录页的 flaky test，
不要修改 authentication behavior。
```

Agent 发现测试很难稳定，于是选择修改 production code：

```text
retry logic
session timing
authentication fallback
```

所有单元测试仍然通过。

从 Runtime 看：

```text
running normally
```

从 Tool Permission 看：

```text
all allowed
```

从局部 Verification 看：

```text
tests pass
```

但任务实际上已经从：

```text
修测试稳定性
```

漂移成：

```text
改变 authentication behavior
```

这是 Human-on-the-loop 比较麻烦的一类 failure：

```text
silent drift
```

Agent 没有 crash，也没有触发权限错误。

它只是沿着一个局部合理、全局错误的方向继续工作。

这类问题至少可以来自几个地方：

```text
stale goal
missing constraint
wrong decomposition
bad verifier
reward proxy
context loss
```

`stale goal` 指任务进行很久以后，环境发生了变化，但 Agent 还在优化旧目标。

例如：

```text
09:00
Agent 开始修 Issue A

10:00
Human 已经决定取消 Feature A

11:30
Agent 仍然在继续实现
```

如果 Agent 没有重新读取共享状态，它可能高质量地完成一件已经不再需要的工作。

`missing constraint` 则是 Agent 从一开始就没有获得某条隐式限制。

例如：

```text
“优化查询性能”
```

但团队默认要求：

```text
不能改变结果排序
```

这条约束如果只存在于某个工程师脑子里，Agent 很可能选择：

```text
改变 query semantics
→ latency 大幅下降
```

从性能指标看成功了，从产品行为看失败了。

`bad verifier` 更隐蔽。

假设 Agent 的唯一验收条件是：

```text
unit tests pass
```

那么它很容易把：

```text
pass tests
```

当成任务目标本身。

如果测试没有覆盖：

```text
performance regression
security behavior
backward compatibility
user experience
```

Agent 完全可能在 verifier 看来持续成功，同时离真实质量标准越来越远。

因此：

```text
Automated verification
```

虽然能减少 Human Process Review，却不能自动解决：

```text
Are we verifying the right thing?
```

Human-on-the-loop 仍然需要人定期检查：

```text
Goal
        ↕
Observed behavior
        ↕
Verifier
        ↕
Artifact
```

是不是还对齐。

这也是为什么只给 Agent 一个 dashboard 并不够。

好的监督面不只是：

```text
73% complete
42 tool calls
all checks green
```

而应该允许人回答：

```text
Agent 现在在追求什么目标？

它产生的 artifact 和这个目标有什么关系？

当前 verifier 覆盖了哪些要求？

哪些要求仍然只能靠人工判断？
```

因此人的监督位置虽然从 loop 内部向外移动，但不能移动到：

```text
只在最终失败以后出现
```

更合理的是按风险设计多层 checkpoint。

例如：

```text
Low-risk routine task

continuous execution
        ↓
final evidence
        ↓
sample review
```

中等风险任务：

```text
continuous execution
        ↓
milestone checkpoint
        ↓
continue
        ↓
final review
```

高风险任务：

```text
plan
  ↓
human approval
  ↓
bounded execution
  ↓
verification
  ↓
human approval
  ↓
effect
```

这说明：

```text
Human-in-the-loop
```

和：

```text
Human-on-the-loop
```

并不是非黑即白的两种产品模式。

同一个系统完全可以同时存在：

```text
Routine work
→ on-the-loop

High-impact decision
→ in-the-loop
```

甚至同一个任务在不同阶段也可以切换监督方式：

```text
Repository exploration
→ on-the-loop

Implementation
→ on-the-loop

Migration plan
→ in-the-loop

Local validation
→ on-the-loop

Production execution
→ in-the-loop
```

监督粒度应该跟着 action effect 和 uncertainty 变化，而不是跟着一个全局：

```text
autonomous = true
```

变化。

走到这里，人类虽然已经退出 Agent 的日常 control flow，但又出现了一个新的问题。

如果每次运行都临时决定：

```text
这一条可以自己做吗？

这一类文件可以改吗？

多久需要 checkpoint？

什么结果必须验证？

哪些事情一定要问人？
```

Human-on-the-loop 很快又会退化成：

```text
Human manually configures every task
```

这依然无法扩展。

真正可扩展的做法，是把这些重复出现的人类判断提前外化：

```text
哪些目标由 Agent 自己推进
哪些资源允许访问
哪些动作可以自动执行
哪些结果必须经过 verifier
哪些风险必须暂停
哪些决定必须升级
```

也就是把 Human 的角色继续向上移动：

```text
Human in the loop
        ↓
负责批准具体动作

Human on the loop
        ↓
负责观察运行、检查结果、处理异常

下一步
        ↓
Human defines how the system should operate
```

这已经不再只是监督某一次执行。

人开始设计一套可以反复作用于很多任务、很多 Agent、很多运行周期的规则。

也就是下一层：

```text
Policy Designer
```

从这一层开始，问题会从：

```text
“这次要不要让 Claude 继续？”
```

变成：

```text
“什么条件下，
这类 Agent 本来就应该能够继续？”
```

## 3. Policy Designer：人开始定义 Agent 的 Operating Envelope

如果 Human-on-the-loop 只做到：

```text
Agent 自己运行
      ↓
Human 偶尔检查
```

还不够。

因为每次任务开始以后，人仍然可能需要重新回答一组几乎相同的问题：

```text
这个 Agent 可以改哪些文件？

可以访问哪些系统？

什么结果算完成？

失败几次以后应该停？

哪些动作可以直接执行？

什么事情必须告诉我？

能不能自己创建新的工作？

能不能改变原来的需求？
```

如果这些问题每次都靠临时对话解决：

```text
Human
  ↓
逐条解释边界
  ↓
Agent
```

Human 虽然已经不在 execution loop 里，却仍然是每个 Agent Runtime 启动以前的配置瓶颈。

真正可扩展的方向，是把这些重复出现的人类判断提前外化成可以复用的规则：

```text
Goal
Role
Scope
Access
Quality Bar
Escalation Rules
```

然后让 Agent 在这个范围里自己运行。

可以把这块范围先叫作：

```text
Operating Envelope
```

这个词是本文为了描述 Agent 可自主行动的边界使用的系统设计抽象，不是 Anthropic 在 **Building effective human-agent teams** 里定义的正式术语。

它表达的是：

> Agent 可以在什么目标、资源、动作和决策范围内自行工作，而不需要每一步重新获得人的授权。

结构大致是：

```text
                  Human
                    │
                    │ defines
                    ▼
          ┌────────────────────┐
          │ Operating Envelope │
          │                    │
          │ Goal               │
          │ Role               │
          │ Scope              │
          │ Access             │
          │ Quality Bar        │
          │ Escalation Policy  │
          └────────────────────┘
                    │
                    ▼
               Agent Runtime
                    │
              autonomous work
```

Human 的角色因此再次发生变化：

```text
Human-in-the-loop
→ 决定“这一步能不能做”

Human-on-the-loop
→ 观察“Agent 现在做得怎么样”

Policy Designer
→ 定义“这类 Agent 原本就应该怎样工作”
```

这不是把人的判断交给配置文件。

相反，它是在区分两类判断：

```text
重复出现、可以提前表达的判断
        ↓
Policy

新的、上下文相关、无法提前穷举的判断
        ↓
Human Judgment
```

Agent autonomy 能否扩展，很大程度上取决于团队能不能把前一类判断稳定地外化出来。

### 3.1 人应该保留 North Star，而不是提前替 Agent 拆完所有步骤

Policy 最容易被误解成：

```text
给 Agent 写一套更长、更详细的 SOP。
```

例如任务是：

```text
提升登录模块稳定性
```

于是人提前写：

```text
1. 打开 auth.ts
2. 搜索 session
3. 打开 test
4. 找 flaky test
5. 修改 cleanup
6. 跑 npm test
7. 如果失败……
```

这其实是在把 Agent 重新退化成 Workflow Executor。

人依然承担：

```text
task decomposition
control flow
next-step selection
```

Agent 只是按照预定义流程填空。

Anthropic 在 Human-Agent Team 的文章里给出的方向不一样。人类仍然负责提供团队的 **north star**，也就是最终应该朝哪里走；但具体工作可以由 Agent 自己发现、拆解和执行。文章中的团队甚至允许部分 Agent 主动提出新的工作，只是这种主动性并不是默认授予所有 Agent，而是需要由人决定哪些 Agent 有资格这么做。

因此 Policy 首先应该规定：

```text
Agent 在优化什么？
```

而不是：

```text
Agent 下一步必须调用哪个 Tool？
```

可以把两种控制方式对比一下。

过度指定过程：

```text
Human
  ↓
step 1
  ↓
step 2
  ↓
step 3
  ↓
Agent executes
```

定义 North Star：

```text
Human
  ↓
Goal
Constraints
Quality Bar
  ↓
Agent
  ↓
plan
  ↓
act
  ↓
observe
  ↓
adapt
```

例如一个代码维护 Agent 的 Policy 可以写：

```text
Goal:
保持 main branch 可构建，
优先处理明确可复现的回归问题。

Constraints:
不要改变 public API。
不要修改数据库 schema。
不要发布到 production。

Quality Bar:
相关测试必须通过。
新增行为必须有测试覆盖。
```

这里没有告诉 Agent：

```text
先读哪个文件
先运行哪个命令
要修改几次
```

这些属于 execution。

但它已经限定了：

```text
什么方向值得推进
什么结果不可接受
什么副作用不允许发生
```

这才是 Policy 和 Workflow 的区别之一。

Workflow 更接近：

```text
How to do this task?
```

Policy 更接近：

```text
Within what rules may the Agent choose how to do the task?
```

这个区分很重要。

如果 Human 把所有步骤都提前定义完：

```text
Agent autonomy
≈
workflow flexibility
```

如果 Human 只定义目标而没有任何限制：

```text
Agent autonomy
≈
unbounded optimization
```

两个极端都不是我们想要的。

真正需要的是：

```text
clear objective
+
bounded freedom
```

也就是：

```text
North Star
+
Operating Envelope
```

Agent 可以自行选择路线，但不能自行重新定义地图。

---

### 3.2 Role 不是一个名字，而是一组稳定的 Responsibility 和 Authority

Anthropic 在描述 Human-Agent Team 时，特别强调了清晰角色、共享 roster、独立 credential 和适合各自工作的 Tool。

表面上看，这些像是组织管理问题。

放到 autonomy 里，其实是在解决同一个问题：

```text
这个 Agent 到底被授权负责什么？
```

假设系统里有三个 Agent：

```text
Triage Agent
Coding Agent
Review Agent
```

如果这三个名字只是 Prompt 里的角色扮演：

```text
You are a reviewer.
```

但它们实际拥有完全一样的：

```text
Context
Credentials
Tools
Write Access
```

那角色边界并没有真正落到 Runtime。

一个 Review Agent 如果同时可以：

```text
修改源码
重写测试
直接 merge
```

它在发现问题以后可能选择自己修掉。

从效率看似乎不错。

但这样一来：

```text
review
```

和：

```text
implementation
```

之间原本存在的职责分离就消失了。

更严格的角色应该同时定义：

```text
Role
=
Responsibility
+
Context
+
Capability
+
Authority
```

例如：

```text
Review Agent

Responsibility:
检查实现是否满足 issue 和项目规范

Context:
issue
diff
tests
repository conventions

Capabilities:
Read
Search
Run tests

Authority:
cannot edit
cannot merge
can request changes
```

Coding Agent 则可能是：

```text
Coding Agent

Responsibility:
实现已经接受的 task

Context:
issue
repo
relevant design docs

Capabilities:
Read
Edit
Bash

Authority:
can modify workspace
cannot deploy
cannot change product requirement
```

两者都可能使用同一个基础模型。

真正不同的是 Harness 给它们构造出来的 operating scope。

于是：

```text
Agent Identity
```

不能只理解成：

```text
system prompt 中的名字
```

而更像：

```text
Identity
  │
  ├── role
  ├── responsibility
  ├── accessible context
  ├── credentials
  ├── tools
  └── authority
```

这也是为什么 Anthropic 会强调 Agent 应该拥有自己的 credential。

如果十个 Agent 全部复用：

```text
one shared superuser credential
```

那么日志里看到：

```text
changed database
```

很难进一步回答：

```text
是谁做的？

它当时以什么角色工作？

这项操作是否属于它的职责？

这个 Agent 本来应该拥有这项权限吗？
```

独立身份让 Policy 可以绑定到具体 Actor：

```text
Agent A
→ read-only analytics

Agent B
→ repository write access

Agent C
→ CI read access

Human Maintainer
→ production deploy
```

这和传统访问控制的思想并不陌生。

但 Agent 带来一个额外问题：

```text
角色不仅决定它能做什么，
还决定它应该主动做什么。
```

比如：

```text
Triage Agent
```

可能有权限读取所有 Issue。

但 Policy 还要定义：

```text
它可以自行关闭 Issue 吗？

可以给 Issue 重新定优先级吗？

可以创建 Coding Task 吗？

可以把问题升级给人吗？
```

也就是说，Agent Role 同时包含：

```text
Capability Boundary
```

和：

```text
Decision Boundary
```

这比传统：

```text
read / write / execute
```

更复杂。

因此设计 Agent Role 时，一个比较实用的检查方式不是问：

```text
“它需要哪些 Tool？”
```

而是分别回答：

```text
它负责什么结果？

它可以读取什么？

它可以改变什么？

它可以自行决定什么？

它必须把什么决定交出去？
```

如果这些问题没有分开，最后往往会得到一个“大而全”的 Agent：

```text
read everything
write everything
decide everything
```

然后再依赖 Prompt 告诉它：

```text
请谨慎使用这些能力。
```

这种结构很难形成稳定自治边界。

---

### 3.3 Scope 决定的是“自治发生在哪里”，而不仅是能不能调用某个 Tool

在 `security.md` 里已经看到，Permission 不能只看 Tool name。

下面两个调用都叫：

```text
Edit
```

但意义完全不同：

```text
Edit("src/auth.ts")
Edit("../billing/prod-config.yaml")
```

到了组织级 autonomy，这个问题还要继续扩大。

Agent 的 scope 不只包括路径。

至少可能包括：

```text
Repository Scope
Data Scope
Environment Scope
Task Scope
Time Scope
Effect Scope
```

例如一个 Agent 可以拥有：

```text
Repository Scope:
services/auth/**

Environment Scope:
local + staging

Data Scope:
synthetic test data

Effect Scope:
code changes only

Task Scope:
bug fixes tagged auth

Time Scope:
current sprint
```

这时 autonomy 不是：

```text
Agent 可以 Edit
```

而是：

```text
Agent 可以在 auth service 的 bug-fix 工作中，
修改指定 repository scope，
并在 local/staging 中自行验证，
但不能触碰 production。
```

这才接近真实授权。

如果只用一个全局：

```text
Edit = allow
Bash = allow
```

就会把很多差异压扁。

例如：

```text
运行 unit test
```

和：

```text
执行 production migration
```

都可能通过 Bash 完成。

但它们的 effect scope 完全不同。

所以 Policy 应该尽量靠近真实 effect，而不只是 Tool Surface。

可以把它抽象成：

```text
Allowed Action
=
Tool
×
Target
×
Environment
×
Effect
×
Task Context
```

这不是一个必须真的写成代码的公式。

它只是提醒我：

```text
“允许 Bash”
```

这种授权粒度通常太粗。

同样的问题也会出现在信息访问上。

一个研究 Agent 可能需要：

```text
公开论文
内部知识库
项目文档
实验结果
```

但未必应该同时拥有：

```text
HR records
customer secrets
unrelated project data
```

所以 Shared Context 不代表：

```text
所有 Agent 看所有内容
```

更合理的是：

```text
Shared environment
+
role-scoped visibility
```

Agent 要能发现完成职责所需的信息，又不能因为“可能有用”就无限扩大 Context 和 Access。

这一点和前面的 organizational context 是同一个问题的另一面：

```text
Context Engineering
→ 什么应该给 Agent 看？

Autonomy Policy
→ Agent 被允许在这些信息上做什么？
```

读取范围、修改范围和决策范围最好被分别表达。

例如：

```text
Can read:
whole repository

Can edit:
services/auth/**

Can execute:
local tests

Can decide:
implementation details

Must escalate:
public API changes
```

这样 Agent 才可能在一个明确区域里长时间运行。

否则所谓 autonomy 很容易变成：

```text
给很多 Tool
+
要求模型自己克制
```

这并不是一个稳定的系统边界。

---

### 3.4 Quality Bar 也是 Policy：完成任务以前，Agent 必须拿出什么证据？

前面 Human-on-the-loop 已经讲过：

```text
Agent says “done”
```

不能自动等于：

```text
Task is done
```

到了 Policy 层，这个问题应该进一步提前。

不是等 Agent 做完以后，人再临时决定：

```text
我还想看一下 test。
```

而是任务开始以前就定义：

```text
什么 evidence 才能把状态从
working
变成
completed？
```

例如一个简单的 Coding Task 可以要求：

```text
Completion Policy:

1. Relevant tests pass
2. Typecheck passes
3. No unrelated files changed
4. New behavior has test coverage
5. Final diff is summarized
```

那么 Agent 的 Runtime 就不应该是：

```text
写完代码
→ done
```

而是：

```text
写完代码
  ↓
run tests
  ↓
typecheck
  ↓
inspect diff
  ↓
verify scope
  ↓
completion criteria satisfied?
      │
   yes│     no
      ▼      │
    done ← retry
```

这会产生一个很重要的变化：

```text
Verification
```

不再只是 Agent “最好做一下”的习惯。

它变成了 operating policy 的一部分。

Anthropic 在 Human-Agent Team 的文章里也把这一点说得很直接：能够可靠工作的 Agent 通常会在结果交给人之前进行验证；软件任务可以运行测试，其他工作可以使用 rubric、style guide，团队也可以加入 Doer–Verifier 结构。

从 autonomy 的角度看，Verifier 的价值不只在提高质量。

它还在决定：

```text
哪些工作可以离开 Human-in-the-loop。
```

举个简单例子。

Task A：

```text
修复 formatter error
```

存在非常明确的 verifier：

```text
formatter passes
tests pass
diff scoped correctly
```

Task B：

```text
重新设计 onboarding experience
```

最终质量标准包含：

```text
用户理解
产品定位
视觉风格
业务取舍
```

即使可以做自动检查，也很难把最终判断全部机器化。

因此两个任务的监督方式自然不同：

```text
Task A
strong verifier
      ↓
more autonomous execution

Task B
weak / partial verifier
      ↓
more human review
```

可以暂时写成：

```text
Autonomy Ceiling
∝
Verification Strength
```

这不是数学定律，只是一个工程关系。

当任务很难验证时，就很难安全地把 Human Review 无限向后移动。

反过来，当质量标准可以被稳定地表达成：

```text
tests
schemas
rubrics
invariants
constraints
```

人就更容易从重复检查中退出。

这也是 Policy Designer 的一个重要工作：

> 不只定义“Agent 要做什么”，还要定义“我们凭什么相信它已经做完”。

如果没有这一层，Agent 的完成状态最终很容易退化成模型自己的判断：

```text
I think this is complete.
```

对于 long-running task，这个信号太弱。

---

### 3.5 Policy 不能全部写进 Prompt：软约束和硬约束必须分开

一提到 Agent Policy，很容易想到：

```text
system prompt
CLAUDE.md
rules
instructions
```

这些当然是 Policy 的一种承载方式。

但不是所有 Policy 都应该只靠模型遵守。

假设有一条要求：

```text
不要修改 production database。
```

可以写成 Prompt：

```text
IMPORTANT:
Never modify production database.
```

这会改变模型的行为倾向。

运行链仍然是：

```text
Policy text
    ↓
Model reads
    ↓
Model decides
    ↓
Tool call
```

如果这个约束必须被保证，系统还需要更硬的控制：

```text
Production credential unavailable
```

或者：

```text
network route blocked
```

或者：

```text
permission rule denies production target
```

于是执行链变成：

```text
Model proposes action
        ↓
Harness policy
        ↓
blocked
```

这两者表达的强度完全不同。

可以粗略分成：

```text
Soft Policy
→ Steering

Hard Policy
→ Enforcement
```

Soft Policy 更适合：

```text
优先复用现有 abstraction

尽量保持 diff 小

先调查根因再修改

输出中说明假设
```

因为这些要求很难被 Harness 完整机械判断。

Hard Policy 更适合：

```text
不能访问 production

不能读取 secrets

不能 force push

不能修改某目录

不能超过预算

必须通过指定 verifier
```

因为这些规则如果真的构成边界，就不应该只依赖模型“记住”。

这里和 `steering.md` 的区别也就清楚了。

`steering.md` 主要在回答：

```text
一条控制信息应该通过哪个 Control Surface
进入 Agent Runtime？
```

这篇 `autonomy.md` 更关心：

```text
哪些控制信息共同定义了
Agent 可以自主工作的区域？
```

两个问题相交，但不是一回事。

Policy 可以分布在很多层：

```text
                    Policy
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
   Context        Harness        Environment
       │              │              │
 Prompt/Rules    Permission      Sandbox
 Skills          Verifier        Credentials
 CLAUDE.md       Budget          Network
```

如果一条规则非常关键，却只存在：

```text
Prompt line 143
```

那就应该问：

```text
如果模型忽略它，
系统还有什么东西会阻止错误发生？
```

如果答案是：

```text
没有。
```

那么这其实不是一个被 enforce 的 boundary。

只是一项行为期望。

这个区分对于 autonomy 特别重要。

因为 Agent 的运行时间越长：

```text
更多 steps
更多 context transitions
更多 compaction
更多 environment interaction
```

单纯依赖：

```text
模型一直正确记住一条文字要求
```

风险就越难忽略。

所以成熟的 Policy Design 不是把 Prompt 写得越来越严厉：

```text
IMPORTANT
VERY IMPORTANT
NEVER
ABSOLUTELY NEVER
```

而是按照规则性质决定它应该落在哪一层。

---

### 3.6 Policy 的价值在于把重复判断提前，但它永远不可能穷举所有情况

到这里似乎可以得到一个很诱人的方案：

```text
把所有边界都提前写成 Policy
        ↓
Agent 永远不用问人
```

但这几乎不可能。

真实任务会不断产生 Policy 没有覆盖的情况。

例如 Policy 写着：

```text
不要改变 public API。
```

Agent 发现：

```text
Bug 的根因就是 public API 本身设计错误。
```

现在怎么办？

或者 Policy 写着：

```text
优先保证 backward compatibility。
```

但 Agent 发现：

```text
兼容旧行为会保留一个安全漏洞。
```

再比如：

```text
允许修改 tests。
```

但某次 Agent 发现：

```text
最简单的修复方式
是删除一个一直失败的测试。
```

形式上：

```text
within scope
```

语义上却可能明显违背任务目标。

这说明 Operating Envelope 不可能是一张穷举表：

```text
case 1 → allow
case 2 → deny
case 3 → allow
...
```

Policy 最多能够覆盖：

```text
known boundaries
common cases
repeatable decisions
```

真实 Runtime 仍然会产生：

```text
novel situation
ambiguous objective
conflicting policy
uncertain impact
```

这时候 Agent 必须判断：

```text
当前情况还能不能安全地留在 operating envelope 内？
```

如果不能，就应该把控制权重新交还给人。

所以 Policy Designer 并不是 autonomy 链的终点。

恰恰相反，Policy 越清楚，我们越能定义它在哪里失效。

可以把结构画成：

```text
                 Human
                   │
             defines policy
                   │
                   ▼
        ┌──────────────────────┐
        │  Operating Envelope  │
        │                      │
        │ routine cases        │
        │ known constraints    │
        │ verifiable outcomes  │
        └──────────────────────┘
                   │
            Agent operates
                   │
          ┌────────┴────────┐
          │                 │
          ▼                 ▼
     within policy      boundary hit
          │                 │
       continue             ?
                            │
                            ▼
                          Human
```

真正缺少的是中间那个判断：

```text
boundary hit?
```

什么情况算越界？

是权限不足？

是不确定性太高？

是结果不可逆？

是两个 Policy 冲突？

还是 Agent 已经无法用现有 verifier 判断哪个方案更好？

如果这条边界没有定义，Human-on-the-loop 最终还是只能依赖：

```text
Agent 自己感觉什么时候应该问人。
```

这显然不够稳定。

所以 Policy 的下一层，不是继续增加更多规则。

而是明确：

```text
什么时候必须停止自主决策，
把问题重新升级给 Human。
```

也就是：

```text
Escalation Boundary
```

从这一刻开始，autonomy 才真正拥有了一条可以在 Runtime 中反复判断的边界：

```text
Inside boundary
→ Agent decides

Outside boundary
→ Human decides
```

下一章要解决的，就是这条线到底应该怎么画。
## 4. Escalation Boundary：什么时候 Agent 必须把决定交还给人？

上一节把 Agent autonomy 表达成一个 Operating Envelope：

```text
                  Human
                    │
              defines policy
                    │
                    ▼
          ┌────────────────────┐
          │ Operating Envelope │
          │                    │
          │ Goal               │
          │ Role               │
          │ Scope              │
          │ Access             │
          │ Quality Bar        │
          └────────────────────┘
                    │
                    ▼
               Agent Runtime
```

但只定义“允许做什么”仍然不够。

真实任务不会永远落在已经提前写好的规则里。Agent 可能遇到缺失的 Context、互相冲突的要求、无法验证的结果，也可能发现继续执行会产生远超原任务范围的副作用。

比如：

```text
Task:
修复登录接口的超时问题

Agent finds:
当前实现依赖一个已经接近容量上限的数据库索引
```

接下来可能有几条路线：

```text
A. 修改查询
   → 小改动
   → 可能降低部分查询精度

B. 新建索引
   → 需要 migration
   → 会改变数据库结构

C. 加 cache
   → 涉及新的基础设施
   → 改变系统复杂度
```

Agent 也许有能力实现 A、B、C。

Permission System 甚至可能允许它修改代码、运行 migration script、编辑配置。

但原来的任务：

```text
修复登录接口超时
```

并没有自动授权 Agent 决定：

```text
是否改变查询语义
是否修改数据库 schema
是否引入新的基础设施
```

这时真正的问题已经不是：

```text
Can the Agent do it?
```

而是：

```text
Is the Agent still authorized
to make this decision?
```

所以自治系统需要一条能够在 Runtime 中反复判断的边界：

```text
inside boundary
→ Agent decides and continues

boundary reached
→ stop autonomous decision
→ escalate
```

这里的 `Escalation Boundary` 是本文用于组织这些问题的分析框架，不是 Anthropic 给出的正式术语。

它描述的是：

> **Agent 在什么情况下不应该继续自行填补不确定性，而应该把决策权重新交给 Human。**

这条边界如果太窄，Agent 会不断打断人；如果太宽，Agent 又会开始替人做没有获得授权的判断。

成熟自治真正难的部分，恰好就在这条线怎么画。

### 4.1 Escalation 不是失败，而是 Agent 识别出了自己的决策边界

我们很容易把 Agent 请求帮助理解成能力不足：

```text
Agent:
“我需要你决定一下。”

        ↓

Autonomy failure
```

于是优化 Agent 时会产生一种很直觉的指标：

```text
Ask Human 越少
→ Agent 越 autonomous
```

但这个指标并不可靠。

假设有两个 Agent。

Agent A 遇到需求歧义：

```text
“提升 onboarding conversion。”
```

代码库里同时存在两个 onboarding flow：

```text
enterprise onboarding
consumer onboarding
```

Agent A 不询问，直接选择 consumer flow：

```text
ambiguous scope
→ infer
→ modify
→ test
→ done
```

它一次都没有打断人。

Agent B 在搜索后发现：

```text
两个 flow 都可能符合任务描述
```

并且现有 Context 无法判断这次实验到底针对哪一类用户，于是暂停：

```text
I found two onboarding paths.

The issue does not identify which one is in scope.

A:
consumer onboarding

B:
enterprise onboarding

Changing either path affects different metrics.
Which one should this task target?
```

如果只统计：

```text
human interruptions
```

Agent A 是：

```text
0
```

Agent B 是：

```text
1
```

但 Agent A 并没有表现出更好的自治。

它只是把：

```text
missing information
```

自动转换成了：

```text
unsupported assumption
```

Agent B 做的事情反而更接近成熟运行：

```text
detect uncertainty
        ↓
determine it cannot be resolved locally
        ↓
identify affected decision
        ↓
escalate
```

所以需要先把：

```text
Escalation
```

和：

```text
Failure
```

分开。

Failure 更接近：

```text
Agent 无法完成
```

Escalation 则可能是：

```text
Agent 知道下一步有哪些可行方案，
但这个选择不属于它当前拥有的决策权。
```

一个 Coding Agent 完全可能知道两种数据库 migration 应该分别怎么实现，却仍然不应该替业务负责人决定：

```text
允许多少 downtime？
```

研究 Agent 可能已经找到两组互相冲突的证据，却不能自行决定：

```text
是否改变研究问题，
把原来的 endpoint 换掉？
```

客服 Agent 可能清楚退款操作怎么执行，但不能自行决定：

```text
是否为一个超出既有政策的特殊案例退款？
```

这些都不是单纯的 capability 问题。

更准确的分类是：

```text
Cannot act
→ capability problem

May not act
→ authorization problem

Cannot determine safely
→ uncertainty problem

Should not decide
→ escalation problem
```

最后一类尤其容易被忽略。

因为 Agent 完全可能：

```text
有信息
有 Tool
有实现能力
```

却仍然不应该拥有这个决定。

Anthropic 在 backlog 案例中的变化正好说明了这一点。

早期，人类检查 Agent 做出的每一个决定，并标记哪些决定实际需要 human input。随后并不是简单地删掉人工 Review，而是让 Agent 学会自己把这些决定暴露出来，尤其保证存在 hard tradeoff 的地方仍然有人参与。

因此监督结构从：

```text
Every decision
      ↓
Human
      ↓
classify:
routine / hard tradeoff
```

逐渐变成：

```text
Agent decision
      │
      ├── routine
      │      ↓
      │   continue
      │
      └── hard tradeoff
             ↓
          escalate
             ↓
           Human
```

真正被自动化的，不只是：

```text
decision execution
```

还包括：

```text
decision triage
```

Agent 开始承担一个新的职责：

> 判断当前决定是否仍属于自己的 authority。

这一步非常关键。

如果 Agent 只能：

```text
做决定
```

却不会：

```text
判断自己是否应该做这个决定
```

那么它的 autonomy 很难扩大。

因此可以把成熟 Agent 的决策过程多加一道：

```text
Observe
   ↓
Generate options
   ↓
Can I decide this within policy?
   │
   ├── yes
   │     ↓
   │   decide
   │     ↓
   │   execute
   │
   └── no
         ↓
      escalate
```

Escalation 并不是自治的反面。

它本身就是自治系统的一部分。

---

### 4.2 什么情况应该触发 Escalation？

最简单的 Escalation Policy 可以写成一张清单：

```text
遇到高风险问题
→ ask human
```

但“高风险”本身没有多少可执行信息。

模型最终还是需要判断：

```text
什么算高风险？
```

更有用的做法，是把可能要求升级的原因拆开。

本文可以先用五类信号来理解：

```text
Uncertainty
Impact
Reversibility
Policy Conflict
Verification Failure
```

这不是 Anthropic 官方定义的五类 Escalation，而是一套便于分析 Runtime 边界的工程抽象。

#### Uncertainty：现有 Context 是否足够支持这个决定？

Agent 经常遇到：

```text
missing requirement
ambiguous owner
unclear priority
multiple plausible interpretations
```

但并不是所有 uncertainty 都应该升级。

例如：

```text
变量名该叫 cacheKey 还是 key？
```

即使没有明确规范，Agent 通常可以从 repository conventions 中自行决定。

但下面这种不确定性就不同：

```text
Issue:
“删除旧 API。”

Agent discovers:
仍有三个内部服务调用旧 API，
但无法确认这些服务是否即将迁移。
```

现在 Agent 缺失的信息直接影响：

```text
是否会造成 downstream breakage
```

这时更合理的行为是：

```text
insufficient context
+
material consequence
        ↓
escalate
```

所以不是：

```text
uncertainty > 0
→ ask
```

而更接近：

```text
uncertainty affects a material decision
and cannot be resolved from available context
→ escalate
```

否则 Agent 会重新退化成：

```text
不知道一个小细节
→ 问人
```

---

#### Impact：如果判断错了，影响范围有多大？

两个动作都可能产生修改：

```text
修一个 README typo

修改 authentication policy
```

从 Tool 层看都可以只是：

```text
Edit
```

但 effect 完全不同。

可以粗略把 Impact 看成：

```text
Local
Team
Customer
Organization
External
```

例如：

```text
修改局部测试 fixture
→ local impact

改变共享 package API
→ team impact

改变用户登录行为
→ customer impact

修改生产访问策略
→ organization impact
```

Impact 越大，对错误判断的容忍度通常越低。

因此同一种 uncertainty，在不同 impact 下可能产生不同监督方式：

```text
Low uncertainty
+
Low impact
→ continue
```

但：

```text
Low uncertainty
+
Very high impact
→ possibly escalate anyway
```

例如 Agent 可能非常确信自己知道：

```text
如何执行 production database migration
```

但团队仍然可以规定：

```text
production migration
→ human required
```

这不是因为 Agent“不懂”。

而是因为这类 action 的 impact 本身已经超过 autonomy boundary。

---

#### Reversibility：做错以后能不能廉价恢复？

Impact 之外还需要单独考虑可逆性。

下面两个动作都可能影响大量数据：

```text
生成一份错误报告
```

和：

```text
删除原始数据
```

前者影响可能很大，但只要重新生成即可。

后者一旦没有 backup，就可能无法恢复。

所以风险并不只取决于：

```text
How much changes?
```

还取决于：

```text
Can we undo it?
```

对于 Agent，可以粗略分成：

```text
easy to undo
→ edit local source

recoverable
→ merge PR with rollback

costly to undo
→ migration

irreversible
→ destructive external action
```

越接近不可逆动作，越应该提高 Human Gate 的要求。

例如：

```text
create draft email
→ autonomous

send email to customer
→ stronger boundary

delete customer record
→ human required
```

这和 Tool 是否相同没有直接关系。

Agent 甚至可能通过同一个 API：

```text
POST /draft
POST /send
POST /delete
```

产生完全不同的 reversibility。

---

#### Policy Conflict：两条都正确的规则发生冲突怎么办？

Policy Designer 无法保证规则永远一致。

例如：

```text
Policy A:
优先保持 backward compatibility

Policy B:
安全漏洞必须立即修复
```

Agent 发现：

```text
修复漏洞必须打破旧行为
```

如果它机械执行 A：

```text
保留漏洞
```

显然不对。

如果机械执行 B：

```text
直接 breaking change
```

又可能产生重大业务影响。

真正的问题是：

```text
两个有效 Policy
要求互相冲突的行为
```

这已经不是继续增加 Prompt 能解决的。

Agent 应该把冲突本身显式暴露：

```text
Policy conflict:

Security requirement:
旧行为允许 privilege escalation.

Compatibility requirement:
3 internal clients still depend on that behavior.

No option satisfies both constraints.

Human decision required.
```

这里升级的不是：

```text
“我不会修。”
```

而是：

```text
“现有 Policy 无法唯一决定优先级。”
```

这类冲突尤其应该由 Policy Owner 解决，因为它经常意味着：

```text
组织真正的优先级
还没有被明确写下来
```

一次好的 Escalation 甚至可以反过来改善 Policy。

Human 做完决定：

```text
安全优先于 compatibility
```

以后就可以把这条信息外化：

```text
security-critical vulnerability
overrides backward compatibility
```

下一次类似情况就不需要重新询问。

因此 Escalation 不只是异常处理，也是发现隐式组织知识的一种机制。

---

#### Verification Failure：Agent 无法证明自己的结果满足 Quality Bar

最后一种边界和前面的 Verification 直接相关。

假设 Completion Policy 是：

```text
relevant tests pass
typecheck pass
no unrelated regression
```

Agent 修改完成后：

```text
unit tests:
pass

typecheck:
pass

integration tests:
cannot run
because staging dependency is unavailable
```

它不能简单把：

```text
2 / 3 checks passed
```

改写成：

```text
done
```

现在存在一个 verification gap。

接下来有几种可能：

```text
retry later
use alternative verifier
reduce claim
escalate
```

如果 alternative verifier 足够：

```text
可以继续
```

如果关键质量条件无法验证：

```text
Agent 不能证明任务完成
```

这本身就应该成为 escalation signal。

这里尤其要区分：

```text
Execution Failure
```

和：

```text
Verification Failure
```

代码可能已经正确。

只是 Agent 没有足够证据证明它正确。

对于 autonomy 来说，后者同样重要。

因为 Human-on-the-loop 的前提之一正是：

```text
Human 不检查全部过程，
而检查可验证结果。
```

Verifier 一旦失效，原来的 supervision design 也跟着失效。

因此运行路径应该更像：

```text
implementation complete
        ↓
verification
        │
        ├── sufficient evidence
        │        ↓
        │     continue
        │
        └── insufficient evidence
                 ↓
          retry / escalate
```

而不是：

```text
implementation complete
→ done
```

---

把上面的几个信号放在一起，可以得到一个用于思考的伪公式：

```text
Escalate if:

    material_uncertainty
 OR high_impact
 OR low_reversibility
 OR policy_conflict
 OR verification_failure
```

需要再次强调，这不是一个可以直接拿五个 Boolean 拼起来就部署的通用 Agent 算法。

真实系统还需要考虑：

```text
task type
agent role
historical reliability
available verifier
environment
```

比如：

```text
high impact
```

并不意味着任何动作都必须人工确认。

一个已经高度自动化的 CI 系统每天可能影响整个组织，却仍然能够自动运行，因为：

```text
动作高度标准化
输入边界明确
结果可验证
失败可回滚
```

所以 Escalation Boundary 更接近一个多因素决策：

```text
escalation(
    decision,
    task,
    effect,
    uncertainty,
    reversibility,
    policy,
    verification,
    agent_scope
)
→ continue | escalate
```

真正重要的不是公式长什么样，而是不要把边界压成：

```text
“感觉危险就问人。”
```

---

### 4.3 高质量 Escalation 应该提交一个 Decision Package，而不是一句“怎么办？”

Agent 能识别需要升级的决定以后，新的问题很快就会出现。

如果它只是发：

```text
我这里不确定，要怎么做？
```

Human 虽然重新获得了决策权，却需要自己重新调查整个问题。

例如：

```text
Human:
为什么不确定？

Agent:
因为 migration 有两个方案。

Human:
哪两个？

Agent:
一种 online，一种 offline。

Human:
区别呢？

Agent:
offline 有 downtime。

Human:
多久？

Agent:
测试大约 12 分钟。

Human:
online 呢？

Agent:
遇到了 lock timeout。
```

这已经不是一个 Escalation。

它只是把 Agent 原本拥有的 Context 拆成多轮重新传给人。

Human Attention Cost 会非常高。

Anthropic 在 Agent 更独立以后明确要求它们 batch questions，并在请求人处理时重新给出必要 Context，让人能够快速进入状态。

因此一次升级最好不是：

```text
question
```

而是一份：

```text
Decision Package
```

最小结构可以是：

```text
Decision required

Relevant context

What has already been verified

Options

Tradeoffs

Agent recommendation

What changes after the decision
```

例如：

```text
Decision required:
是否接受最多 15 分钟只读窗口完成 migration。

Context:
users 表约 8M rows。
当前 migration 必须补写 normalized_email。

Verified:
- offline migration staging: 11m42s
- rollback: pass
- backup restore: pass
- application compatibility: pass

Online approach:
两次 staging 测试均出现 lock timeout，
当前没有通过 verifier。

Option A:
15 分钟只读窗口。
已有完整 rollback。

Option B:
继续开发 online migration。
无计划 downtime，
但当前方案尚未通过 lock test。

Recommendation:
A。

Reason:
当前已有验证证据更完整，
且 rollback path 已测试。
```

这时 Human 不需要重做：

```text
repository search
log inspection
test execution
option discovery
```

他只需要完成真正属于自己的部分：

```text
tradeoff decision
```

这个结构也能让 Escalation 更容易被记录。

假设人选择：

```text
A
```

同时说明：

```text
我们允许 maintenance window，
只要小于 20 分钟且 rollback 已验证。
```

这个决定以后可以沉淀成 Policy：

```text
For this service:

maintenance window <= 20 min
+
verified rollback
→ no escalation required
```

于是下一次：

```text
same class of migration
```

可能不再需要 Human。

Escalation 因此还承担一种反馈作用：

```text
Unknown boundary
        ↓
Agent escalates
        ↓
Human decides
        ↓
Decision recorded
        ↓
Policy / Skill / Rubric updated
        ↓
Future routine case
```

这和新同事 onboarding 很像。

一开始很多事情需要问：

```text
“这种情况团队一般怎么做？”
```

但一个有效组织不会希望同一个问题永远由同一个负责人重新回答。

它会逐渐外化成：

```text
documentation
policy
checklist
example
```

Agent 也一样。

如果同一种 Escalation 每周出现几十次：

```text
same question
same context
same answer
```

那问题往往不只是 Agent 太爱问。

更可能说明：

```text
团队还没有把这条隐式规则
写进 Agent 可以发现的 Policy。
```

因此可以把 Escalation Log 当作一个很有用的诊断源：

```text
Escalation Log
      ↓
cluster repeated decisions
      ↓
identify missing policy
      ↓
externalize rule
```

这会让 Operating Envelope 逐渐变得更清楚。

---

### 4.4 Escalation 太多和太少都是 Calibration Failure

一旦系统开始记录 Escalation，就很容易优化：

```text
减少 Escalation 数量
```

但这个指标和：

```text
减少 Human Interruptions
```

一样，单独使用会产生问题。

需要同时看两个方向。

第一类是：

```text
False Escalation
```

Agent 把原本属于自己 operating scope 的 routine decision 交给了人。

例如：

```text
是否运行测试？
是否读取另一个相关文件？
是否修复 formatter？
是否重试一次已知 transient failure？
```

如果 Policy 已经允许这些动作，Agent 仍然不断暂停：

```text
Agent
→ routine ambiguity
→ Human
```

人最终重新成为 Runtime bottleneck。

第二类是：

```text
Missed Escalation
```

Agent 遇到了真正需要人判断的问题，却没有升级。

例如：

```text
产品目标发生冲突
→ Agent 自己选一个

production data 有删除风险
→ Agent 继续

关键 verifier 不可用
→ Agent 宣布完成

需求缺少业务范围
→ Agent 猜一个
```

这类错误更加危险，因为系统表面上甚至可能运行得很顺畅：

```text
no interruption
no error
task completed
```

只有后来才发现 Agent 跨过了自己本来不应该跨的 decision boundary。

于是 Escalation 可以用一个类似分类器的视角理解：

```text
                   Human judgment actually required

                       Yes             No

Agent        Yes    Correct         False
escalates           Escalation      Escalation

             No     Missed          Correct
                    Escalation      Autonomy
```

目标不是：

```text
maximize:
Correct Autonomy
```

而忽略其他格子。

因为如果为了减少 False Escalation，不断放宽边界：

```text
ask less
ask less
ask less
```

Missed Escalation 可能迅速增加。

反过来，如果为了避免任何 Missed Escalation：

```text
anything uncertain
→ ask human
```

就会回到 Human-in-the-loop。

所以自治系统真正需要优化的是：

```text
Escalation Calibration
```

也就是：

```text
该问的时候问，
不该问的时候继续。
```

不同任务对两种错误的容忍度也完全不同。

例如文档格式：

```text
False Escalation cost:
annoying

Missed Escalation cost:
minor
```

可以让 Agent 更激进地自行处理。

生产数据删除：

```text
False Escalation cost:
one human review

Missed Escalation cost:
potentially catastrophic
```

边界自然应该保守得多。

所以更准确的 Policy 应该按 task type 区分：

```text
Docs formatting
→ low escalation sensitivity

Routine bug fix
→ medium

Schema migration
→ high

Production destructive action
→ human required
```

而不是给整个 Agent 一个全局：

```text
confidence_threshold = 0.8
```

因为：

```text
80% confidence
```

对改 README 和删 production table 的意义根本不同。

---

### 4.5 Escalation Boundary 其实是组织级的 `allow / ask / deny`

回到 `security.md`，一次 Tool Call 的 Permission 可以粗略表示成：

```text
allow
ask
deny
```

到了 Human-Agent Team，这个结构其实会再次出现，只是判断对象从：

```text
concrete tool call
```

扩大成：

```text
decision
task
effect
```

可以把它画成：

```text
                     Agent Decision
                           │
                           ▼
                    Operating Policy
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
           allow           ask           deny
             │             │             │
             ▼             ▼             ▼
          continue       Human          stop
```

`allow` 表示：

```text
这类决定属于 Agent
当前已经拥有的自治范围。
```

例如：

```text
修 lint
运行 test
在指定目录修改实现
重试 transient failure
```

`ask` 表示：

```text
这个决定本身可能合理，
但当前 Policy 无法证明
Agent 有权自行选择。
```

例如：

```text
改变 API compatibility

在 downtime 与复杂度之间做业务取舍

扩大原任务 scope

采用未被验证的新 migration strategy
```

`deny` 则表示：

```text
无论 Human 是否暂时没在线，
这个 Agent 都不应该执行。
```

例如某个只负责代码 Review 的 Agent：

```text
production deploy
→ deny
```

或者数据分析 Agent：

```text
delete raw dataset
→ deny
```

这三个状态比：

```text
autonomous / not autonomous
```

更能描述真实系统。

因为 autonomy 并不是：

```text
所有事情自动做
```

而是：

```text
routine cases → allow

boundary cases → ask

out-of-scope cases → deny
```

其中最难设计的恰好是中间的：

```text
ask
```

`allow` 可以通过扩大授权增加。

`deny` 可以通过权限和 sandbox 强制执行。

`ask` 要解决的是：

```text
系统如何识别
“这件事不是禁止的，
但也不应该由 Agent 自己决定”？
```

这就是 Escalation Boundary。

---

把前四章连起来，Human 的位置已经发生了几次变化：

```text
Human in the loop
        │
        │ 每一步推动
        ▼
具体动作审批
```

变成：

```text
Human on the loop
        │
        │ 观察、Review、接管
        ▼
运行监督
```

然后：

```text
Policy Designer
        │
        │ 提前定义
        ▼
Operating Envelope
```

再到：

```text
Escalation Boundary
        │
        │ Runtime 判断
        ▼
continue / ask / stop
```

走到这里，Agent 已经具备了一套可以持续运行的自治结构。

但还有最后一个问题没有解决：

```text
Operating Envelope
到底应该一开始就有多大？
```

最激进的做法是：

```text
Agent capability 很强
        ↓
直接给大范围 autonomy
```

但前面的分析已经说明：

```text
Capability
```

只能回答：

```text
Can it do this?
```

无法回答：

```text
Can it repeatedly do this
to an acceptable standard
without requiring rescue?
```

反过来，如果永远保持：

```text
所有新任务
→ manual review
```

那么 Agent 的 operating envelope 又永远不会扩大。

所以还缺少一个动态过程：

```text
supervised work
        ↓
observed outcomes
        ↓
verification
        ↓
feedback
        ↓
repeated success
        ↓
expand autonomy
```

而且扩大的不应该是：

```text
Agent globally trusted = true
```

而应该是：

```text
这个 Agent
在这种 Task Type 上
已经积累了什么可靠性证据？
```

Anthropic 对这一点给得很明确：他们按照已经证明的 reliability 授予 autonomy，并在重复成功以后按 task type 扩大 scope；500 个 bug fixes 的案例是这个过程后期的状态，而不是初始配置。

因此下一章才轮到这篇文章真正的终点：

```text
Earned Autonomy
```

自治不是一个 Agent 安装完成以后默认获得的属性。

它是一段由监督记录、Verifier、错误反馈和重复成功共同支持的运行历史。
## 5. Earned Autonomy：自治不是模式，而是一段被验证过的历史

前四章解决的都是“自治如何运行”的问题：

```text
Human in the loop
        ↓
人参与具体动作和决定

Human on the loop
        ↓
人监督状态、Evidence 和异常

Policy Designer
        ↓
提前定义 Operating Envelope

Escalation Boundary
        ↓
运行时判断 continue / ask / stop
```

但到这里还有一个问题没有回答：

> Agent 一开始应该获得多大的 Operating Envelope？

最简单的答案有两个极端。

一种是按照能力授予权限：

```text
Agent 会写代码
Agent 会运行测试
Agent 会操作 Git
        ↓
允许它独立完成软件任务
```

另一种则始终保持保守：

```text
所有新任务
        ↓
Human Review
```

前者把模型的 capability 当成了实际 reliability，后者又使监督范围永远无法随着经验积累而变化。

Anthropic 在 **Building effective human-agent teams** 中给出的原则更接近第三种路径：团队按照 Agent 已经证明出来的可靠性授予 autonomy，并在重复成功以后逐步扩大这个范围。文章还特别强调，要记录每个 Agent 已经在哪些 **task types** 上挣到了 autonomy，而不是简单给整个 Agent 打一个“可信”标签。

因此这里需要再区分三个概念：

```text
Capability
≠
Reliability
≠
Autonomy
```

`Capability` 回答：

```text
Agent 有没有能力完成这类动作？
```

`Reliability` 回答：

```text
Agent 能不能在反复执行中，
稳定达到团队接受的质量标准？
```

`Autonomy` 回答：

```text
基于已有证据，
这类任务还需要多少 Human supervision？
```

这三个变量相关，但不能互相替代。

一个模型可以第一次就写出非常好的数据库 migration，这说明它具备能力；但如果团队还没有观察过它在 schema compatibility、rollback、生产约束和异常处理上的表现，就很难从这一次成功直接推出：

```text
以后所有 migration
→ autonomous
```

Earned Autonomy 的含义正在这里：**自治范围来自已经观察和验证过的行为记录，而不是来自模型理论上能够做到什么。**

### 5.1 Capability 只能说明“可能会做”，不能说明“应该放手让它做”

假设一个 Agent 拥有：

```text
Read
Edit
Bash
Git
Browser
Database
```

它从能力上已经可以完成很复杂的软件任务。只要给够 Context，它可能自己完成：

```text
理解 issue
→ 修改代码
→ 更新测试
→ 运行 CI
→ 修改数据库
→ 发布服务
```

但 Tool Surface 越宽，越不能直接推出对应的 autonomy。

原因很简单：真实任务要求的不只是“能执行动作”，还要求 Agent 在大量局部决定里保持稳定。

一个 bug fix 里可能包含：

```text
修改哪个文件？
应该保留哪种旧行为？
测试失败是实现错了，还是测试错了？
要不要扩大修改范围？
遇到 flaky test 要重试还是调查？
应该修根因还是加入 workaround？
```

单次任务中，模型完全可能把这些判断都做对。

Reliability 要问的是另一件事：

```text
如果把同一类任务重复 10 次、50 次、500 次，
错误模式是什么？
```

例如 Agent 可能表现为：

```text
简单 bug fix
→ 98% 情况正确处理

涉及 compatibility 的 bug
→ 经常过度修改 API

测试失败
→ 偶尔通过删除断言让测试重新通过

需求模糊
→ 倾向于自行猜测而不是升级
```

从 capability 看，它仍然是同一个 Agent。

从 autonomy 看，这些任务显然不应该拥有相同的监督级别。

因此：

```text
Agent is capable
```

最多只能支持：

```text
值得让它尝试
```

不能直接支持：

```text
值得让它无人监督地持续执行
```

这和新成员加入一个工程团队很像。一个工程师可能熟悉 Java、Kubernetes、AWS 和数据库，但团队通常不会仅根据技能列表，在第一天就把所有 production credential 和发布责任全部交出去。

更常见的过程是：

```text
先完成有限范围任务
        ↓
Code Review
        ↓
观察实现和判断方式
        ↓
给反馈
        ↓
继续完成类似任务
        ↓
逐渐扩大 ownership
```

Anthropic 在文章里也用类似 onboarding 的视角描述 Human-Agent Team：新成员——无论是人还是 Agent——都需要多个 feedback cycle，才能逐渐明确哪些隐式要求需要外化、哪些工作可以独立完成、哪些决定仍然需要更有经验的人介入。

这里积累的不是：

```text
感觉这个 Agent 挺聪明
```

而是：

```text
Evidence of reliability
```

### 5.2 自治应该按 Task Type 获得，而不是给 Agent 一个全局 Trust Score

如果把 autonomy 设计成：

```text
Agent A = trusted
Agent B = untrusted
```

很快就会遇到问题。

同一个 Agent 可能已经非常稳定地完成：

```text
修 lint
更新文档
补测试
修简单 regression
```

但仍然很不稳定地处理：

```text
大型 refactor
数据库 migration
安全配置
产品需求冲突
production deploy
```

所以更合理的表示方式是：

```text
Autonomy
=
Agent
×
Task Type
```

还可以再加上 Environment 和 Effect：

```text
Autonomy Scope
=
Agent
×
Task Type
×
Environment
×
Effect
```

例如：

| Task Type           | 当前监督方式                                  |
| ------------------- | --------------------------------------- |
| Markdown / 格式修复     | autonomous                              |
| lint / formatter 修复 | autonomous + verifier                   |
| 小型单元测试修复            | automated verification + sampled review |
| 局部 bug fix          | output review                           |
| public API 修改       | human decision required                 |
| schema migration    | plan review + bounded execution         |
| production deploy   | human required                          |

这里并不存在一个统一的：

```text
autonomy_level = 4
```

能够描述 Agent 的全部行为。

如果一定要给它画成一张图，更像是：

```text
                 Agent A

Docs               ██████████
Lint                ██████████
Unit-test fix       █████████
Small bug fix       ███████
Refactor            █████
Migration           ██
Production deploy   █
```

每一条都由不同的历史证据支持。

这也解释了为什么产品层面的：

```text
Plan Mode
Auto Mode
Full Auto
```

虽然交互简单，却很难完整描述 Harness 中真正的 autonomy。

一个全局 Auto Mode 很容易把两件性质完全不同的事情压在一起：

```text
自动修改本地测试
```

和：

```text
自动执行不可逆生产操作
```

真正稳定的系统需要把自治绑定到 task/effect boundary，而不是绑定到 Agent 名称。

Anthropic 在原文中特别建议团队记录每个 Agent **在哪些种类的任务上已经获得 autonomy**，并在重复成功后按任务类型逐步扩大范围。这个设计其实已经否定了：

```text
Agent 一旦可信
→ 什么都可以放手
```

更接近：

```text
这类任务已经证明稳定
→ 减少这类任务的监督
```

### 5.3 从 Supervised 到 Autonomous，真正变化的是 Human Review 被移动到了哪里

Earned Autonomy 不需要被实现成一套固定五级制度，但为了理解监督如何变化，可以画出一个典型过程：

```text
Stage 1
Human reviews every decision

Stage 2
Agent executes,
Human reviews every output

Stage 3
Agent + verifier,
Human reviews selected outputs

Stage 4
Agent handles routine tasks,
Human receives exceptions

Stage 5
Agent handles batches,
Human reviews aggregated evidence
and hard tradeoffs
```

这里最重要的变化不是：

```text
Human 越来越少
```

而是 Human Review 的位置不断向后移动。

早期：

```text
Agent decision
      ↓
Human
      ↓
action
```

随后变成：

```text
Agent
  ↓
complete task
  ↓
Human reviews artifact
```

再往后：

```text
Agent
  ↓
complete task
  ↓
Verifier
  ↓
Evidence
  ↓
sampled Human Review
```

最后，部分已经高度标准化的任务可以变成：

```text
Agent
  ↓
batch execution
  ↓
automated verification
  ↓
routine cases continue
  ↓
exceptions → Human
```

Human 仍然存在，只是监督单位从：

```text
single action
```

逐渐变成：

```text
decision
artifact
task
batch
exception
```

这就是“挣到 autonomy”在运行层真正改变的东西。

它不是给 Agent 增加一个抽象分数，而是减少某一类任务中不再必要的同步 Gate。

### 5.4 500 个 Bug Fix 的案例，应该被理解成结果而不是起点

Anthropic 在文章里提到，他们的工程师后来可以把 **500 个 bug fixes** 交给团队中的 Agent 独立处理。

如果只截取这一句话，很容易变成：

```text
Claude 已经可以无人监督修 500 个 Bug。
```

但原文紧接着说明，团队并不是一开始就这样工作。

这件事更接近：

```text
早期任务
        ↓
Human reviews decisions
        ↓
发现常见错误模式
        ↓
补充 Context / instructions / verifier
        ↓
继续运行同类任务
        ↓
观察 repeated success
        ↓
减少 routine review
        ↓
扩大 batch size
```

最终才会出现：

```text
500 bug fixes
```

这个数字真正说明的不是 Agent 单次 horizon 有多长，而是团队已经对某类工作积累了足够多的可靠性证据，使监督可以从逐任务检查退到更高层级。

例如最开始可能是：

```text
1 bug
→ full review

1 bug
→ full review

1 bug
→ full review
```

随着错误模式变得稳定：

```text
10 bugs
→ automated verification
→ full output review
```

然后：

```text
50 bugs
→ automated verification
→ sampled review
```

再到：

```text
large batch
→ verifier
→ exception handling
→ human review where required
```

实际系统当然不一定按这些数字线性扩张，这里只是为了说明监督粒度的变化。

所以：

```text
500
```

不是一个可复制的 autonomy threshold。

不能写成：

```text
Agent 成功 499 次
→ 仍然 supervised

成功第 500 次
→ autonomous
```

它只是 Anthropic 案例中某个成熟阶段的 workload scale。

真正可以迁移的方法是：

```text
observe
→ verify
→ feedback
→ repeat
→ expand scope
```

### 5.5 Repeated Success 只有在任务和质量标准稳定时才有意义

这里还有一个很容易被忽略的问题。

假设 Agent 连续成功完成 100 个任务：

```text
100 / 100 success
```

这个数字看起来很强。

但如果这 100 个任务都是：

```text
修 typo
```

它不能证明 Agent 可以可靠处理：

```text
database migration
```

同样，如果所谓 success 的判定标准只是：

```text
Agent 自己说 Done
```

那么 100 次成功也没有太强的意义。

因此 Reliability Evidence 至少要回答两个问题：

```text
Success on what?
```

以及：

```text
Success according to what verifier?
```

更完整一点可以写成：

```text
Reliability Evidence
=
Task Distribution
+
Outcome
+
Verification
+
Human Feedback
```

比如：

```text
Task Type:
small bug fix

Observed:
82 tasks

Verification:
unit tests
integration tests
typecheck
diff scope check

Human sampled review:
18 tasks

Material regressions:
1

Missed escalations:
2
```

这样的记录比：

```text
Agent success rate = 96%
```

更有解释力。

因为后者隐藏了最重要的信息：

```text
在哪类任务上？
怎么判断成功？
失败是什么类型？
```

Autonomy 的扩大应该依赖具体 evidence，而不是单个漂亮指标。

### 5.6 只统计 Task Success 不够，还必须观察 Escalation Calibration

前一章已经区分过：

```text
Correct Escalation
False Escalation
Missed Escalation
Correct Autonomy
```

Earned Autonomy 不能只看：

```text
最终任务有没有完成
```

还需要看 Agent 是怎么处理边界问题的。

假设两个 Agent 最终成功率都很高。

Agent A：

```text
routine case
→ 经常问人

hard tradeoff
→ 也问人
```

Agent B：

```text
routine case
→ 自己处理

hard tradeoff
→ 稳定升级
```

如果只看 task success，两者可能差不多。

但从 autonomy 看，B 明显能够在更大范围内独立运行。

再看另一种情况。

Agent C：

```text
routine case
→ 自己处理

hard tradeoff
→ 也自己处理
```

因为很多 tradeoff 最终没有立即造成失败，它的 task success 甚至可能暂时很好。

但这并不意味着应该扩大自治。

它可能只是存在：

```text
missed escalation
```

并且风险还没有在有限样本里暴露。

所以 Autonomy Promotion 至少应该同时考虑：

```text
Task Quality
Verification Pass Rate
Human Correction Rate
Escalation Precision
Missed Escalations
Recovery Frequency
```

不一定真的要把每一项都做成 Dashboard，但设计思路应该如此。

如果 Agent 每次都能完成任务，却需要人频繁救场：

```text
Task success = high
Rescue rate = high
```

也不能称为高可靠自治。

因为实际运行仍然依赖：

```text
Human recovery
```

因此 Reliability 更准确的问题是：

```text
Can the Agent repeatedly reach
an acceptable verified outcome
inside its policy boundary
without requiring rescue?
```

这比单纯：

```text
Can it finish?
```

严格得多。

### 5.7 Earned Autonomy 的扩张应该改变 Policy，而不是只改变人的心理预期

如果团队观察到 Agent 已经稳定处理某类任务，却只是形成一种非正式感觉：

```text
“这个 Agent 做这种事一般没问题。”
```

系统结构并没有真正变化。

下一次任务仍然可能：

```text
ask
ask
ask
```

所以 reliability evidence 最终应该反馈到 Operating Policy。

例如一开始：

```text
Task:
dependency patch update

Policy:
Human review required
```

连续运行一段时间以后发现：

```text
只允许 patch version
lockfile diff 有 verifier
tests 必须通过
禁止 major/minor upgrade
过去 80 次没有 material regression
```

那么 Policy 可以升级为：

```text
patch-only dependency update
+
all checks pass
+
no API changes
        ↓
auto merge to staging branch
```

这时 autonomy 的扩大真正进入 Runtime。

可以画成一个 feedback loop：

```text
Task execution
      ↓
Outcome
      ↓
Verification
      ↓
Human feedback
      ↓
Reliability record
      ↓
Policy update
      ↓
Next execution
```

所以 Earned Autonomy 不是：

```text
模型越来越聪明
→ 人越来越放心
```

而是：

```text
系统积累证据
→ Policy 被重新配置
→ Agent 获得更大的 bounded operating scope
```

这一区别很重要。

前一种变化发生在人脑里。

后一种变化发生在 Harness 里。

### 5.8 Autonomy 不是只升不降，模型、环境和任务变化都可能要求重新收紧边界

如果 autonomy 真的是 evidence-based，就必须接受一个结果：

```text
Evidence changes
→ Autonomy changes
```

也就是说，自治不仅可以扩大，也必须能够降级。

最直接的情况是连续出现 regression：

```text
原本：
small refactor
→ autonomous

后来：
连续出现 scope creep
和 missed regression
```

那么合理的动作不是：

```text
“再提醒 Agent 注意一点。”
```

而可能是：

```text
small refactor
→ output review required
```

也就是：

```text
demote autonomy
```

模型更新同样可能改变这一结论。

假设某个 task policy 是基于：

```text
Model v1
```

经过大量任务调出来的。

换成：

```text
Model v2
```

以后，新模型可能在总体 benchmark 上更强，但这并不能证明它在原有 Harness 中仍然具有相同的行为分布。

它可能：

```text
更愿意扩大 scope
更少请求 clarification
对某些 instruction 解释不同
更主动使用某个 Tool
```

于是以前积累的 reliability evidence 不能完全无条件继承。

Anthropic 在长期 Agent 相关经验中也反复强调，模型升级后应该重新检查已有任务和 guardrail：一些旧 scaffolding 可能已经不再必要，但旧 Prompt、Verifier 和边界也可能需要重新评估。

所以自治状态最好支持：

```text
promote
demote
retest
revoke
```

而不是：

```text
once trusted
→ always trusted
```

环境变化同样如此。

例如：

```text
过去：
Agent 只能操作 staging

现在：
同一 credential 新增 production access
```

Agent 本身没变，但 effect surface 已经变了。

原来的 autonomy evidence 不应该自动推出：

```text
production 也可以 autonomous
```

任务分布发生变化也一样。

```text
过去：
小型单仓库 bug

现在：
跨服务 refactor
```

不能因为都叫：

```text
bug fix
```

就认为风险完全一致。

因此真正稳定的 autonomy state 应该绑定版本和环境：

```text
Agent / Model
Task Type
Policy Version
Environment
Verifier
Observed Reliability
```

这样发生变化以后，系统至少知道：

```text
哪些 evidence 可能已经 stale
```

### 5.9 Earned Autonomy 最终形成的是一张动态 Trust Map，而不是一条等级线

把前面所有内容放在一起，会发现自治并不太像：

```text
Level 1
↓
Level 2
↓
Level 3
↓
Level 4
↓
Full Autonomy
```

更接近一张不断变化的矩阵：

```text
                     Supervision

Docs formatting        autonomous
Lint fixes             autonomous
Unit-test repair       autonomous + verifier
Small bug fix          sampled review
Refactor               output review
Schema migration       plan approval
Production deploy      human required
Product tradeoff       human decision
```

而且这张表会随着：

```text
Agent behavior
Model version
Verifier quality
Task history
Policy
Environment
```

继续变化。

可以把它叫作：

```text
Task-scoped Trust Map
```

这个词同样是本文为了帮助理解使用的抽象，不是 Anthropic 的正式术语。

它比：

```text
Agent A is autonomous
```

更接近真实运行。

因为同一个 Agent 完全可以同时处于：

```text
high autonomy
```

和：

```text
low autonomy
```

只是对应不同任务。

这也把前面的 Escalation Boundary 接了回来。

对于已经积累大量可靠性证据的 task type：

```text
Operating Envelope
        ↓
更宽
```

所以更多情况会进入：

```text
allow
```

对于缺少证据的任务：

```text
Operating Envelope
        ↓
更窄
```

更多情况会进入：

```text
ask
```

明显超出角色和风险边界的动作仍然是：

```text
deny
```

于是最终结构变成：

```text
                       Task
                        │
                        ▼
                 classify task type
                        │
                        ▼
               Reliability History
                        │
                        ▼
                 Operating Policy
                        │
           ┌────────────┼────────────┐
           │            │            │
           ▼            ▼            ▼
         allow          ask          deny
           │            │            │
           ▼            ▼            ▼
        Agent          Human        Stop
           │
           ▼
       Verification
           │
           ▼
     Outcome + Evidence
           │
           ▼
   Reliability History
```

Autonomy 在这里形成了一个真正的 feedback loop。

它不再是安装 Agent 时选择的一项模式。

### 5.10 人没有从团队里消失，而是从执行者逐渐变成边界和责任的所有者

现在再回头看最开始那条链：

```text
Human in the loop
↓
Human on the loop
↓
Policy designer
↓
Escalation boundary
↓
Earned autonomy
```

容易误读成：

```text
Human participation
越来越少
直到 Agent 完全取代 Human
```

但前面五章真正得到的结论不是这样。

变化的是 Human 所处的位置。

最开始：

```text
Human
→ 批准下一步
```

随后：

```text
Human
→ 观察结果和状态
```

再往后：

```text
Human
→ 定义 Agent 的 Role、Goal、Scope 和 Quality Bar
```

然后：

```text
Human
→ 保留 hard tradeoff 和越界决定
```

当 Agent 在某些 task type 上反复证明可靠以后：

```text
Human
→ 调整 Policy
→ 扩大这一类任务的 autonomy
```

所以 Human 并没有退出控制结构。

他只是从：

```text
micro-decision owner
```

逐渐变成：

```text
policy owner
boundary owner
exception owner
accountability owner
```

Agent 则承担越来越多可以被验证、可以被约束、可以在既定 Policy 下重复执行的工作。

这也是为什么我现在更愿意把 Human-Agent autonomy 理解成：

```text
不是减少 Human，
而是重新分配 Decision Rights。
```

Routine decision 尽量留给 Agent：

```text
实现细节
低风险修复
可验证操作
重复性工作
```

需要组织判断的决定留给人：

```text
目标改变
高影响 tradeoff
不可逆动作
Policy 冲突
缺失关键业务 Context
```

两者之间通过：

```text
Policy
Verifier
Observability
Escalation
Reliability History
```

连接起来。

最终目标不是：

```text
Ask Human = 0
```

也不是：

```text
Human Review = 100%
```

而是让人工判断集中到那些机器无法仅凭已有 Policy 和 Evidence 安全解决的问题上。

对于已经证明可靠的 routine work：

```text
Agent
→ execute
→ verify
→ continue
```

对于越过边界的问题：

```text
Agent
→ detect boundary
→ package context
→ escalate
→ Human decides
```

对于新的任务类型：

```text
supervise
→ observe
→ verify
→ learn
→ update policy
```

如果这个过程持续运行，自治才会逐渐扩大。

所以 `Earned Autonomy` 最后强调的并不是“Agent 最终能够独立做多少事情”。

更准确的问题是：

```text
我们拥有什么证据，
能够证明这类任务已经不再需要
原来那么多的人类监督？
```

只要这个问题还没有答案，扩大 autonomy 就只是扩大信任假设。

当答案能够由真实任务记录、Verifier、Human Feedback 和 Escalation History 支撑时，监督位置才有理由继续向后移动。
