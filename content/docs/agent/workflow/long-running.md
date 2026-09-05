---
title: "Long-running Agent Harness"
weight: 2
---
> 截止2026.9，随着DSH以及Pi等涌现，我不认为A\得出的这个结论完全正确

**为什么模型升级以后，反而应该删除 Harness 代码？**

model-relative scaffolding 的概念也就是：

> **Harness 不是一套固定最佳实践，而是当前模型可靠性边界的补丁集合。**

## 更复杂的 Harness 不天然更先进

### 为什么模型升级以后，反而应该删除 Harness 代码？

主要是在这之前针对CC泄露快照学习的前面几节一路加了很多东西：

```text
Context Reset
Transcript
Tool Contract
Permission
Effect-aware Scheduling
Evaluator
Sprint Contract
Subagent
Worktree Isolation
```

如果把这些机制逐个拿出来看，它们都很合理。于是很容易得出一个错误直觉：

> 既然这些东西都能提升可靠性，那 Harness 越复杂越先进。

但 Anthropic 在后续实验里得到的结论恰好相反：

> Harness 里的每一个组件，本质上都编码了一个“模型自己做不到”的假设。随着模型升级，这些假设可能变错，也可能迅速过时。

* **model-relative scaffolding**：Harness 组件不是永恒正确的架构层，而是针对当前模型能力边界添加的 scaffolding。模型能力变化以后，每一层 scaffolding 都应该重新接受消融，而不是默认永久保留。

---

#### Context Reset 是最典型的例子

先回到 Macro 1。

Anthropic 早期 long-running harness 使用 Sonnet 4.5 时，遇到了一个很具体的问题：

```text
Context 越来越长
        ↓
模型开始出现 context anxiety
        ↓
还没真正完成任务
        ↓
却提前准备收尾
```

单纯 compaction 不够。

因为 compaction 是：

```text
旧 Context
    ↓
压缩历史
    ↓
同一个 Agent 继续
```

历史轨迹仍然存在。

于是 Anthropic 加入：

```text
Context Reset
+
Structured Handoff
```

把：

```text
旧 Agent
```

彻底换成：

```text
Fresh Agent
```

只通过 handoff artifact 继续任务。

在 Sonnet 4.5 上，这个机制是：

```text
load-bearing
```

没有它，长任务可靠性明显下降。

所以当时最合理的 Harness 是：

```text
Agent session
    ↓
接近长 Context
    ↓
写 Handoff
    ↓
RESET
    ↓
新 Agent
```

---

#### 然后换成 Opus 4.5，问题自己消失了

到了下一轮实验，Anthropic 改用 Opus 4.5。

结果他们发现：

> 原来 Context Reset 要解决的那种 context anxiety，Opus 4.5 基本已经不再表现出来。

于是原来的：

```text
Context Reset
```

不再是：

```text
必要保护
```

而变成：

```text
额外 orchestration
+
额外 token
+
额外 latency
+
handoff information loss risk
```

所以 Anthropic 直接把它删掉。

新的设计变成：

```text
Continuous Session
        ↓
Automatic Compaction
        ↓
继续长时间工作
```

也就是说：

```text
Sonnet 4.5
Context Reset = reliability mechanism

Opus 4.5
Context Reset = dead weight
```

这件事非常关键。

因为 Context Reset 本身并没有“变差”。

变的是：

```text
Model capability
```

于是同一个 Harness component 的价值发生了翻转。

---

#### 这就是 Harness 最容易积累“历史包袱”的地方

传统软件里，我们经常遇到：

```text
过去某个 Bug
    ↓
加一个 workaround
    ↓
几年以后没人敢删
```

Agent Harness 特别容易出现这种问题。

例如：

```text
模型容易忘记任务
→ 加 task reminder

模型长 Context 容易漂
→ 加 reset

模型不会分解工作
→ 加 sprint

模型自评不可靠
→ 加 evaluator

模型不会自己 plan
→ 加 planner
```

几年——甚至几个月——以后，Harness 就可能变成：

```text
Prompt A
↓
Planner
↓
Decomposer
↓
Context Manager
↓
Generator
↓
Reflection
↓
Evaluator
↓
Verifier
↓
Reviewer
↓
Finalizer
```

每一层都能讲出历史理由。

但现在的问题变成：

> **这些理由今天还成立吗？**

---

#### Anthropic 自己就经历了一次“减法失败”

他们第一版 full-stack Harness 很强。

但代价也很夸张。

同一个 Retro Game Maker 任务：

```text
Solo:
约 20 分钟
约 $9

Full Harness:
约 6 小时
约 $200
```

质量确实明显更高，但成本超过 20 倍。

于是下一步很自然：

```text
既然效果已经有了，
能不能把 Harness 简化？
```

Anthropic 一开始尝试的是：

```text
大幅砍结构
+
加入一些新想法
```

结果没有复现原 Harness 的性能。

更糟的是：

> 一次删太多以后，已经很难判断究竟哪一块是 load-bearing，哪一块只是多余。

这个经验特别重要。

因为它告诉我们：

```text
Harness simplification
```

也不能靠感觉。

---

#### 正确方法更接近 Ablation

后来 Anthropic 换成了更方法化的方式：

```text
完整 Harness
    ↓
每次只删一个 component
    ↓
重新跑真实任务
    ↓
看结果发生什么变化
```

这其实就是很标准的：

```text
ablation
```

思路。

例如：

```text
Baseline:
Planner
+ Sprint
+ Generator
+ Evaluator

Experiment A:
去掉 Sprint

Experiment B:
去掉 Planner

Experiment C:
去掉 Evaluator
```

然后比较：

```text
quality
cost
latency
failure mode
```

所以 Harness Engineering 不只是：

```text
不断加组件
```

还应该包含：

> **持续证明某个组件仍然值得存在。**

---

#### Opus 4.6 又让 Sprint Decomposition 变得没那么必要

接着模型再次升级。

Anthropic 发布 Opus 4.6 后，模型在几项能力上都有明显提升：

```text
更会 planning
长时间 agentic task 更稳定
大型 codebase 中更可靠
code review / debugging 更强
long-context retrieval 更好
```

这些能力恰好就是旧 Harness 在帮模型补的地方。

于是 Anthropic 做了一个很直接的实验：

> 把 Sprint structure 整个删掉。

旧设计：

```text
Large Product Spec
    ↓
Sprint 1
    ↓
QA
    ↓
Sprint 2
    ↓
QA
    ↓
Sprint 3
    ↓
...
```

Sprint 的作用本来是：

```text
限制每次工作范围
        ↓
减少长期 coherence 压力
```

这对 Opus 4.5 很有帮助。

但到了 Opus 4.6：

```text
Model itself
已经能在更长时间里
保持 coherent build
```

于是强行切 Sprint 反而未必必要。

---

#### 新模型真的能连续工作两个多小时

Anthropic 后来用新版 Harness 构建浏览器 DAW。

删掉 Sprint decomposition 后：

```text
Generator
```

单次连续 coherent build 超过两小时。

文章里给出的 Build Round 1 是：

```text
2 hr 7 min
```

而不再是：

```text
每个 feature 一个短 Sprint
```

这就是最直观的证据：

```text
旧 Harness:
必须人为切短任务

新模型:
已经能自己维持更长 horizon
```

因此：

```text
Sprint
```

从过去的：

```text
necessary decomposition
```

变成了可能的：

```text
unnecessary ceremony
```

---

#### 但 Planner 却没有一起删掉

这一点特别能说明 Anthropic 不是在追求：

```text
Harness 越简单越好
```

如果目标只是减组件，那 Planner 也应该删。

但他们实际测试后发现：

```text
没有 Planner
    ↓
Generator 收到 raw prompt
    ↓
很快开始写
    ↓
产品 scope 明显偏小
```

换句话说，Opus 4.6 虽然更强了，但：

```text
product scoping
```

这个 gap 仍然存在。

所以 Planner 继续保留。

这说明真正原则不是：

```text
复杂 = 差
简单 = 好
```

而是：

```text
有证据证明有价值
→ 留

没有增益
→ 删
```

---

#### Evaluator 更有意思：它不是“保留”或者“删除”的二元问题

Anthropic 对 Evaluator 的观察更细。

在 Opus 4.5 时：

```text
Generator solo capability
```

和任务复杂度之间的边界很近。

也就是说大量问题都处在：

```text
模型勉强能做
但不太可靠
```

的位置。

这时 Evaluator 能经常发现重要 Bug。

所以：

```text
Evaluator
=
high value
```

到了 Opus 4.6：

```text
solo reliability boundary
```

往外移动了。

过去一些需要：

```text
Generator
+
Evaluator
```

才能稳定完成的东西，现在：

```text
Generator alone
```

就已经够可靠。

在这些任务上：

```text
Evaluator
```

就变成：

```text
额外 token
额外 latency
额外 orchestration
```

却没有明显质量收益。

---

#### 但在能力边缘，Evaluator 仍然有价值

这里千万不要写成：

> Opus 4.6 不需要 Evaluator。

Anthropic 的结论恰恰不是这么绝对。

更准确的是：

```text
任务难度
──────────────────────────────→

简单
│
│  Generator solo 已可靠
│  Evaluator ≈ overhead
│
├──────── reliability boundary
│
│  Generator 开始不稳定
│  Evaluator 有明显 lift
│
复杂
```

所以是否加 Evaluator 不是：

```text
model-level boolean
```

而是：

```text
task × model
```

共同决定。

---

#### 这就是 “Model-relative” 的真正含义

假设任务难度记作：

```text
D(task)
```

模型可靠能力边界记作：

```text
R(model)
```

当然这不是 Anthropic 的数学定义，只是帮助理解。

如果：

```text
D(task) << R(model)
```

任务远在模型能力边界以内：

```text
额外 Harness
往往收益很小
```

如果：

```text
D(task) ≈ R(model)
```

任务刚好在可靠性边缘：

```text
Verifier
Decomposition
Specialized Agent
```

这些 scaffolding 最可能产生明显收益。

如果：

```text
D(task) >> R(model)
```

任务远远超出当前模型能力：

```text
单靠 Harness
也未必救得回来
```

所以最有价值的 Harness 空间其实经常在：

```text
model reliability frontier
```

附近。

---

#### 这和很多 AI 工程讨论非常不一样

我们很容易形成：

```text
Architecture Best Practice
```

思维。

比如：

```text
长任务必须 Context Reset

复杂任务必须 Multi-Agent

Coding Agent 必须 Planner

生产环境必须 Evaluator

大任务必须先拆 Sprint
```

但 Anthropic 这篇文章真正有价值的地方，就是把这些：

```text
必须
```

全部拆掉。

更准确的表达应该是：

```text
在某个模型
某类任务
某种 failure mode
下

这个机制曾经有明显收益。
```

这比写：

```text
Agent 系统最佳实践：
1. Planner
2. Memory
3. Evaluator
4. Multi-Agent
```

要严谨很多。

---

#### 这也是为什么老源码仍然值得看，但不能照抄

我们现在研究的是 Claude Code v2.1.88 的 restored snapshot。

它当然不是最新 Claude Code。

这件事反而非常适合作为文章结尾前的一个方法论提醒。

例如源码里某个机制今天存在：

```text
Context handling
Permission flow
Agent Tool
Scheduling rule
```

我们可以从中学习：

```text
当时 Anthropic
面对什么 runtime problem？
他们把责任放在哪一层？
接口为什么长这样？
```

但不能轻易推出：

> 最新 Claude Code 仍然必须使用完全相同的结构。

因为 Harness 与 runtime：

```text
本身就在跟模型能力一起演化。
```

Anthropic 甚至在 2026 年 4 月的 Managed Agents 文章里再次强调：Harness 会持续变化，因为里面对模型弱点的假设会过期；他们举的例子仍然是 Sonnet 4.5 需要 Context Reset，而 Opus 4.5 已经不需要。

所以：

```text
读旧源码
```

真正应该学的是：

```text
problem → mechanism
```

而不是：

```text
mechanism → 永恒架构
```

---

#### Harness Component 本质上都是“能力缺口假设”

现在可以把前面的内容全部反过来看。

#### Context Reset

隐含假设：

```text
当前模型无法在长 Context 下
稳定保持 coherence。
```

如果假设消失：

```text
Reset 可以删。
```

---

#### Sprint Decomposition

隐含假设：

```text
当前模型无法连续规划并执行
整个复杂 Build。
```

如果模型能连续稳定工作两小时以上：

```text
Sprint 可能可以删。
```

---

#### Planner

隐含假设：

```text
当前模型从 raw prompt 直接 coding
容易 underscope。
```

目前实验仍支持这个假设：

```text
Planner 留。
```

---

#### Evaluator

隐含假设：

```text
当前 Generator 在这个任务上
不能稳定发现自己的失败。
```

如果任务进入 solo reliability boundary：

```text
Evaluator 可以成为 overhead。
```

---

于是整个 Harness 可以重新理解成：

```text
Model gap #1
    ↓
Component A

Model gap #2
    ↓
Component B

Model gap #3
    ↓
Component C
```

而不是：

```text
Harness Framework
规定必须拥有
A + B + C
```

---

#### 这就是为什么一个 Harness 应该附带“删除条件”

这点是我觉得可以直接借到自己工程里的。

我们平常写设计文档时，会记录：

```text
为什么加入这个组件？
```

以后可以进一步记录：

```text
在什么条件下可以删掉它？
```

例如：

```text
Component:
Context Reset

Reason:
模型在 >X 长任务中出现提前收尾。

Removal criterion:
新版模型在同一 Eval 集合中，
continuous + compaction
达到相同或更高成功率。
```

又例如：

```text
Component:
Evaluator

Reason:
关键 workflow 经常漏 Bug。

Removal criterion:
solo generator 在相同 task suite 中
达到相同 acceptance pass rate，
并且 evaluator 增量收益低于成本阈值。
```

这样 Harness component 才不会变成：

```text
once added
→ immortal
```

---

#### 甚至每个 Guardrail 都应该被怀疑一次

这和 Anthropic 后来 `Building effective human-agent teams` 里讲的 autonomy 思路也很一致。

旧模型不可靠时：

```text
加 checklist
加 verifier
加人工 review
```

是合理的。

但模型升级以后，如果仍然：

```text
永远沿用旧 guardrail
```

就可能让更强模型：

```text
被旧约束卡死
```

所以 autonomy 不是只会：

```text
不断放更多权限
```

也包括：

> **重新测试历史约束是否还有必要。**

这也是 Harness Engineering 和传统安全规则最大的张力之一：

```text
可靠性需要约束
但过时约束会限制能力
```

---

#### 一个很适合面试的问题：为什么 Harness 不能追求“最完整”？

如果面试官问：

> 既然 Planner、Evaluator、Context Reset 都有帮助，为什么不全放进去，反正更稳？

我会回答：

> 因为每个 Harness component 都有成本，而且都编码了一个模型能力不足的假设。这个假设一旦因为模型升级而失效，组件就只剩 token、latency、状态交接和 orchestration complexity。Anthropic 在 Sonnet 4.5 上需要 Context Reset，到了 Opus 4.5 直接删除；Opus 4.6 又让原来用于 coherence 的 Sprint decomposition 变得不再必要。因此 Harness 应该做 component-level ablation，而不是把历史 workaround 永久叠加。

然后再补一句：

> **最好的 Harness 不是功能最多，而是每一层复杂度都能被当前 failure evidence 证明。**

---

#### 这里其实和普通 System Design 很像

好的 distributed system 也不会因为：

```text
Queue 有用
Cache 有用
Replica 有用
Event Bus 有用
Consensus 有用
```

就：

```text
所有项目全部加。
```

否则一个简单服务也会变成：

```text
Kafka
Redis
ZooKeeper
Kubernetes
Service Mesh
CQRS
Event Sourcing
```

Agent Harness 同样有这种 architecture astronaut 风险。

```text
Planner
Memory
RAG
Reflection
Evaluator
Multi-Agent
Skill
Graph
Workflow Engine
```

每个词都很诱人。

但真正应该问的是：

```text
它具体解决了哪个失败？
```

以及：

```text
不加以后真实 Eval 会坏多少？
```

---

#### 所以 Harness Engineering 的核心循环其实是实验

到这里可以把 Anthropic 整篇文章的开发方式抽成：

```text
选真实任务
    ↓
跑 Model + Harness
    ↓
读 Trace
    ↓
识别 recurring failure
    ↓
加一个最小机制
    ↓
重新跑
    ↓
比较结果
```

模型更新以后再：

```text
换新模型
    ↓
重新跑同类任务
    ↓
逐个删除旧 component
    ↓
看谁已经不再 load-bearing
```

因此：

```text
Harness Engineering
```

其实特别接近：

```text
experimental systems engineering
```

而不是：

```text
套一个固定 Agent Framework
```

---

#### 一个组件的价值应该看“边际收益”

假设：

```text
Solo
质量 = 70
成本 = 10
```

加入 Evaluator：

```text
质量 = 85
成本 = 15
```

这个 component 很值。

模型升级以后：

```text
Solo
质量 = 84
成本 = 10
```

Evaluator：

```text
质量 = 85
成本 = 15
```

这时：

```text
增量质量：
+1

成本：
+50%
```

那它就很可能不值。

虽然这些数字只是示意，但判断方式应该是：

```text
marginal quality gain
----------------------
marginal cost / latency / complexity
```

而不是：

```text
Evaluator 理论上有用，
所以保留。
```

---

#### 这也解释了 Anthropic 为什么没有完全追求最低成本

新版 DAW Harness：

```text
总运行时间：
约 3 小时 50 分

token 成本：
$124.70
```

仍然非常贵。

所以 Anthropic 并不是：

```text
越便宜越好
```

他们真正做的是：

```text
删除不再产生质量收益的复杂度

同时保留仍然能够
把能力边界往外推的部分
```

这两个目标不同。

---

#### 模型越强，Harness 不是消失，而是“边界往外移动”

这也是文章结尾特别有意思的一点。

一种悲观理解是：

```text
模型越来越强
    ↓
Harness 最终没意义
```

Anthropic 的判断反而是：

```text
旧 Harness
补过去的缺口
        ↓
模型变强
        ↓
旧缺口消失
        ↓
删掉旧 scaffolding
        ↓
利用新模型能力
构建更 ambitious 的 Harness
        ↓
去解决以前根本碰不到的问题
```

所以：

> **Harness 的有趣空间不会缩小，而是会跟着模型能力边界一起移动。**

这也是我觉得整篇文章最值得带去面试的一层。

---

#### 所以不要问“2026 最佳 Harness 是什么”

更好的问题应该是：

```text
当前模型是谁？

目标任务是什么？

真实失败在哪里？

哪些失败是稳定复现的？

哪些机制能改善这些失败？

这个机制的成本是多少？

换模型以后还成立吗？
```

因此不存在脱离模型和任务的：

```text
Best Harness Architecture
```

只有：

```text
Harness(model, task, constraints)
```

这同样不是正式公式，只是帮助理解。

---

#### 再回头看我们一路写下来的所有机制

现在可以重新给它们分类。

```text
Context / Compaction / Reset
```

解决：

```text
长期状态与 coherence gap
```

```text
Tool Contract
Permission
Scheduling
```

解决：

```text
现实动作执行 gap
```

```text
Evaluator
Grounded Verification
Calibration
```

解决：

```text
completion judgment gap
```

```text
Planner / Subagent
```

解决：

```text
scope / role / context isolation gap
```

所以真正的 Harness 不是：

```text
模块清单
```

而是：

```text
Failure
   ↓
Mechanism
   ↓
Evidence of improvement
   ↓
Re-evaluate later
```

这正好也是为什么这篇博客不能写成：

```text
Claude Code 有哪些模块
```

而应该写成：

> **长任务到底怎样坏，Harness 为什么必须承担这些责任。**

---

#### 源码与证据边界

Anthropic 2026 年 3 月文章可以直接支持：

* 每个 Harness component 都编码了一个关于“模型独立做不到什么”的假设，而这些假设应该持续 stress test；
* Sonnet 4.5 上 Context Reset 是关键机制，但 Opus 4.5 基本消除了相应 context-anxiety behavior，因此后续 Harness 删除了 Reset，改用 continuous session + automatic compaction；
* 初版 Harness 比 solo run 成本高 20 倍以上，推动了后续 simplification；
* 一次删除太多组件难以判断谁真正 load-bearing，因此 Anthropic 后来改为逐组件 ablation；
* Opus 4.6 能够更稳定执行长任务后，Sprint construct 被整体删除；
* Planner 仍有明显增益，因为 raw-prompt Generator 容易 underscope；
* Evaluator 的收益依赖任务相对于当前模型 solo reliability boundary 的位置；boundary 内可能只是 overhead，boundary 附近仍能产生真实提升。
* Anthropic 后续 Managed Agents 文章再次用 Context Reset 的删除说明 Harness 假设会随模型进步而过期。

### Macro 7 小结

如果要把这一节压成一句真正值得记住的话，我会写：

> **Harness 不是模型外面越堆越厚的永久脚手架，而是当前模型可靠性边界的显式补丁；模型升级以后，第一件事不应该是把新模型塞进旧 Harness，而应该重新证明每一块脚手架还值得存在。**

因此正确循环不是：

```text
Model improves
    ↓
Old Harness + New Model
    ↓
继续加组件
```

而应该是：

```text
Model improves
    ↓
Re-run realistic evals
    ↓
Ablate old scaffolding
    ↓
Keep only load-bearing pieces
    ↓
Use freed capability
to attack harder tasks
```


到这里，我们已经从：

```text
一个 Coding Agent
为什么长任务会失败？
```

一路走到：

```text
为什么 Harness 本身
也必须跟着模型持续进化？
```

但还有最后一个问题。

前面的系统里，人似乎越来越少出现：

```text
Planner 自动规划
Generator 自动实现
Evaluator 自动验证
Permission 可以自动决策
Subagent 可以后台运行
```

那么最后是不是：

```text
Human
→ eventually removed from the loop
```

？

Anthropic 在另一篇 **Building effective human-agent teams** 里给出的答案并不是简单的“人退出”。

更准确的是：

> 人类的位置从逐动作操作和监督，逐渐上移到目标、上下文、评价标准和自治边界的设计。

因此下一 Macro 要从 Coding Agent 往组织层再走一步：
