---
title: "Agent Autonomy"
weight: 1
---

### 8.2 为什么 Agent 的自治权应该是“挣出来”的？


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

### Macro 8 小结

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
```

接下来不需要再引入一个新的大概念了。

正文只差最后一个非常短的 **Macro 9：面试复盘**：

把整篇文章压成几个最可能被问到的问题，以及一张从父文“五个动词”映射到 Claude Code / Anthropic Harness 的最终表格。
