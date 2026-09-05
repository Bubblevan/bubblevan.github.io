---
title: "Agent Verification：从自评到外部验证"
weight: 1
---

## 1. `我改完了`为什么不等于任务完成


**为什么不能让做事的 Agent 自己宣布通过？**

这次要看的不再只是：

```text
tool_result
```

而是更高一层的：

```text
independent verification
```

### 1.1 为什么不能让做事的 Agent 自己宣布通过？


前面几节已经把执行路径拆得很清楚了：

```text
Model
  ↓
tool_use
  ↓
Tool contract
  ↓
Permission
  ↓
Scheduling
  ↓
Environment
  ↓
tool_result
  ↓
Model
```

到这里，一个 Coding Agent 已经能够：

```text
读代码
修改文件
跑测试
处理权限
并发执行安全的 Tool Call
根据结果继续修正
```

看起来已经很完整。

但还有一个非常容易被忽略的问题：

> **谁来决定“任务已经完成”？**

最天真的答案当然是：

```text
Agent 自己。
```

它做完以后说：

```text
实现已完成。
测试通过。
所有功能已经正常工作。
```

然后 Harness 退出。

可 Anthropic 在长任务 Harness 实验里专门把这个问题列成第二类持续出现的 failure mode：

**self-evaluation。**

他们观察到，当 Agent 被要求评价自己刚刚产出的工作时，往往会明显偏向正面；即便在人类看来质量很一般，它也可能给出相当自信的肯定。这个问题在设计等主观任务上尤其明显，但即使面对有客观结果的软件任务，也仍然会出现判断失准。


* **independent verification**：执行任务和判断任务是否达标，不应该默认由同一个推理轨迹承担；Harness 可以把“做”与“验”分离，让完成状态依赖独立证据，而不是生成者自己的信心。

---

#### 先看一个我们平时已经习惯的 Coding Agent 结尾

比如我让 Agent：

> 修复注册接口重复创建用户的问题。

它可能经历：

```text
Read
  ↓
发现代码
  ↓
Edit
  ↓
pytest
  ↓
测试通过
  ↓
assistant:
“已经修复。”
```

这个例子似乎没问题。

因为：

```text
pytest passed
```

已经提供了一个外部 signal。

但真实长任务往往不是：

```text
修一个明确单测
```

而是：

```text
实现完整注册流程
```

或者：

```text
构建一个可用的管理后台
```

甚至：

```text
实现这个完整 Web App
```

这时“完成”就不再对应一个 Boolean：

```text
pytest == green
```

而是很多条件同时成立：

```text
页面真的能打开？
按钮真的可用？
后端接口真的连上？
状态能不能保存？
错误路径是否正常？
功能是不是只有 UI 壳子？
设计有没有达到要求？
边界情况有没有被漏掉？
```

这时如果让负责实现的人自己回答：

> 我是不是都做完了？

风险就开始出现。

---

#### 问题不是 Agent 会“故意撒谎”

这里很容易把 self-evaluation failure 理解成：

```text
模型为了偷懒，
故意骗用户说自己完成了。
```

我觉得这个理解不太准确。

更接近的问题是：

> **执行过程中形成的推理轨迹，会影响它之后怎么看自己的成果。**

假设 Generator 一路经历：

```text
我需要实现登录
        ↓
我已经写了 LoginForm
        ↓
我写了 /api/login
        ↓
我补了 auth state
        ↓
我修了几个 bug
        ↓
我觉得整体已经差不多完整
```

最后再问：

```text
请评价你的实现是否完整。
```

它不是一个真正从零开始的 Reviewer。

它带着整段：

```text
我为什么这样设计
我已经修过什么
我认为哪些问题重要
我为什么觉得当前方案合理
```

继续判断。

于是：

```text
implementation trajectory
```

和：

```text
evaluation trajectory
```

高度耦合。

---

#### 这和人类 Code Review 的逻辑其实很像

假设一个工程师刚连续写了六个小时代码。

然后你问他：

> 你觉得这个 PR 有问题吗？

他的第一反应很可能是：

```text
我已经想过这些问题了。
```

否则他大概不会提交。

所以软件工程从来没有设计成：

```text
作者完成代码
    ↓
作者再次确认：
“我觉得挺好”
    ↓
merge
```

我们反而引入：

```text
code review
CI
tests
QA
staging
acceptance criteria
```

不是因为作者一定不可靠。

而是因为：

> **生成过程和验证过程拥有不同的目标函数。**

作者更关心：

```text
怎样让它工作？
```

Reviewer 更关心：

```text
哪里还没有工作？
```

这两个问题看起来接近，其实推理姿态完全不同。

---

#### Generator 天然在证明“为什么它应该工作”

Generator 的轨迹通常是：

```text
需求
  ↓
提出方案
  ↓
实现方案
  ↓
遇到错误
  ↓
解释错误
  ↓
修正
  ↓
继续实现
```

整个过程中，它不断积累的是：

```text
支持当前方案的理由
```

比如：

```text
这里用了 React state，因为……
这个接口这样设计，因为……
这个 bug 已经通过……
这个测试现在已经 green……
```

最后让它进行 self-evaluation，很容易变成：

```text
寻找证据证明我做得不错
```

而不是：

```text
主动寻找能推翻“已经完成”的反例
```

这其实就是 verification 里最重要的区别：

```text
confirmation
vs
falsification
```

---

#### Evaluator 的角色恰好应该反过来

如果单独启动一个 Evaluator，它收到的任务不是：

```text
请理解为什么 Generator 的设计是合理的。
```

而应该是：

```text
这是需求。
这是完成标准。
这是当前产物。

请找出它不满足要求的地方。
```

于是它的默认姿态变成：

```text
claim:
任务完成了

       ↓

尝试寻找反例

       ↓

如果找不到足够反例，
才接受这个 claim
```

而不是：

```text
任务完成了
       ↓
找几个支持证据
       ↓
确认完成
```

这就是为什么 Anthropic 发现，把“做工作”和“判断工作”分离，是缓解 self-evaluation 问题的一个强杠杆。

---

#### 但“换一个 Agent”并不会神奇解决问题

这一点 Anthropic 也特别强调了。

他们并没有说：

```text
Generator = biased

Evaluator = objective
```

恰恰相反。

文章明确指出：

> 即使把判断任务交给独立 Evaluator，它仍然是一个 LLM，同样可能对 LLM 生成内容过于宽容。

所以：

```text
separate evaluator
```

不是：

```text
ground truth oracle
```

更准确的是：

```text
把“生成”和“批判”拆成两个
更容易分别调优的角色
```

这很重要。

否则我们很容易从一个极端：

```text
相信 Generator 自评
```

跳到另一个极端：

```text
相信 Evaluator 评分
```

实际上两者都不应该无条件相信。

---

#### 为什么独立 Evaluator 反而更容易调？

Anthropic 的一个很有启发性的观察是：

> 把一个独立 evaluator 调成更加 skeptical，比让 generator 在完成自己工作以后突然变得高度自我批判，更容易。

这其实很好理解。

如果让 Generator 同时承担：

```text
阶段 1：
积极想办法完成任务

阶段 2：
积极证明自己刚才做得不好
```

两个 instruction 在同一个轨迹里有一定冲突。

它刚刚还在建立：

```text
这个方案可行
```

下一秒却要切成：

```text
我要证明这个方案不行
```

独立 Evaluator 则从一开始就可以被定义成：

```text
你的工作不是实现。

你的工作是：
找缺陷。
找遗漏。
找不符合验收标准的地方。
```

这样它的行为目标更单纯。

---

#### 这就是“角色分离”真正有价值的地方

Multi-Agent 讨论很容易滑向：

```text
多开几个模型
=
更强
```

其实不是。

如果三个 Agent 都做：

```text
各自想一遍答案
```

那只是多采样。

Anthropic 这里真正有价值的是：

```text
Generator
和
Evaluator
```

拥有**不同职责**。

```text
Generator
目标：
maximize completion

Evaluator
目标：
find violations
```

这比：

```text
Agent A
Agent B
Agent C
```

重要得多。

所以 Multi-Agent 的价值之一不是数量，而是：

> **能不能人为制造相互制衡的目标。**

---

#### 软件任务不是有测试吗？为什么还需要 Evaluator？

这个问题非常自然。

如果代码有：

```text
unit tests
integration tests
typecheck
lint
```

为什么不直接：

```text
tests pass
→ done
```

因为测试只能证明：

> **你写进测试里的东西满足了测试。**

它不能自动证明：

```text
测试覆盖了完整需求。
```

例如用户要求：

```text
做一个 sprite editor。
```

Generator 可能实现：

```text
可以画一个像素
```

并写测试：

```text
点击 canvas 会改变 pixel state
```

测试全绿。

但用户想要的可能还有：

```text
颜色选择
缩放
橡皮擦
填充
帧动画
导入导出
```

此时：

```text
tests passed
```

和：

```text
feature complete
```

之间仍然有巨大差距。

---

#### 更糟的是，Generator 还控制了测试怎么写

如果同一个 Agent 同时：

```text
实现功能
+
设计测试
+
运行测试
+
解释测试结果
+
宣布完成
```

那么整个验证链都被同一个 belief system 包住了。

可以画成：

```text
Generator:
  我认为需求是 A
      ↓
  我按 A 实现
      ↓
  我为 A 写测试
      ↓
  A 的测试通过
      ↓
  所以需求完成
```

但真实需求可能是：

```text
A + B + C
```

于是形成一个很危险的 closed loop：

```text
错误理解
    ↓
错误实现
    ↓
与错误理解一致的测试
    ↓
全部 green
    ↓
高置信宣布完成
```

这个闭环内部完全自洽。

但和用户真实目标错位。

---

#### 所以 Verification 最重要的是引入“独立约束”

比如：

```text
Spec
Acceptance Criteria
User behavior
External tests
Existing tests
Browser interaction
API response
Database state
Human judgment
```

这些东西的价值就在于：

> 它们不是由 Generator 此刻的主观信念临时产生出来的。

验证越依赖：

```text
Generator 自己定义的标准
```

越容易出现：

```text
我定义了一个我自己能通过的考试。
```

验证越依赖：

```text
外部预先存在或独立生成的标准
```

越可能真的发现 gap。

---

#### Anthropic 做 frontend experiment 时为什么先写 grading criteria？

他们面对的最难问题之一是：

```text
“这个设计好看吗？”
```

这种问题没有：

```text
assert design == good
```

所以他们没有直接让 Evaluator：

> 请给这个页面打分。

而是先拆出更具体的 grading dimensions，比如整体设计质量、原创性、craft 和 usability；再让 evaluator 围绕这些 criteria 判断。

这里真正值得我们学的不是那四个设计指标本身。

而是这个动作：

```text
模糊目标
     ↓
显式 criteria
     ↓
可重复 evaluation
```

也就是说：

> **Evaluator 不是因为“独立”就可靠，而是因为它有一套相对明确的判断依据。**

---

#### 这和 Spec / Acceptance Criteria 其实是同一件事

回到我们前面一直在写的：

```text
PRD
TRD
SPEC
```

这里就能看到 Spec 的另一个作用。

以前我们强调 Spec 是：

```text
告诉 Agent 要做什么
```

但其实它同时应该回答：

```text
别人之后凭什么判断它做完了？
```

所以一个好 Spec 不只是：

```text
Implementation input
```

也是：

```text
Verification oracle 的来源
```

例如：

```text
用户可以创建项目
```

太宽。

如果变成：

```text
Given:
没有项目

When:
用户点击 New Project，
输入名称并保存

Then:
项目出现在列表中，
刷新页面后仍然存在
```

它就同时服务：

```text
Generator
```

和：

```text
Evaluator
```

---

#### “Done”其实应该在写代码之前就开始定义

这也是为什么 Anthropic 后来的 full-stack harness 会让 Generator 和 Evaluator 在 sprint 开始前先协商 sprint contract：先约定这一块工作到底要产出什么，以及怎么验证，再进入实现。

这比：

```text
写完以后再想怎么测
```

强很多。

因为后者很容易发生：

```text
我已经这样实现了
        ↓
那我就把完成标准解释成
“现在这个实现已经满足的样子”
```

而提前定义：

```text
done
```

相当于先把终点钉住。

然后 Generator 再往那个终点走。

---

#### 可以把 self-evaluation failure 画成一个闭环偏差

单 Agent：

```text
          ┌────────────────┐
          │                │
          ▼                │
     Interpretation        │
          │                │
          ▼                │
     Implementation        │
          │                │
          ▼                │
       Self-test           │
          │                │
          ▼                │
     Self-evaluation       │
          │                │
          └───────✓────────┘
```

问题是：

```text
interpretation
implementation
test
evaluation
```

可能共享同一个错误假设。

---

#### Generator + Evaluator 则是在闭环外插入另一个视角

```text
           Spec / Contract
            /          \
           ▼            ▼
      Generator      Evaluator
           │            ▲
           │            │
           ▼            │
        Artifact ────────┘
           ▲
           │
        Feedback
```

Generator 不再自己决定：

```text
“我已经够好了。”
```

而是接收：

```text
你还违反了 criterion 3
这个 interaction 实际不可用
这个 API 返回错误
这个功能只是视觉占位
```

然后继续修改。

这才形成真正有意义的：

```text
generate
→ verify
→ revise
```

循环。

---

#### 为什么这比 Reflection 更强？

很多 Agent pattern 会加入：

```text
Reflection
```

比如让同一个模型做完以后：

> 请反思你的答案有什么问题。

Reflection 当然有价值。

但它仍然是：

```text
same agent
same trajectory
same context
```

所以更接近：

```text
internal critique
```

而 Generator / Evaluator separation 则引入：

```text
independent role
independent prompt
potentially independent context
different objective
```

它没有完全消除模型偏差，但至少降低了：

```text
“我刚才就是这么做的，所以它应该是对的”
```

这种轨迹耦合。

---

#### 所以“模型更聪明”也不会自动消灭 Verification

这里还要避免另一个误区：

```text
如果模型足够强，
Evaluator 就不需要了。
```

更准确的说法应该是：

> Evaluator 的价值取决于任务相对于当前模型 solo reliability boundary 的位置。

Anthropic 后续用 Opus 4.6 做 harness 简化时，确实发现一些原本需要 evaluator 才能稳定完成的任务，已经进入新模型单独就能可靠处理的范围；这时 evaluator 会变成额外成本。但对于仍处于能力边缘的部分，独立检查继续能带来明显收益。

这个结论很关键。

因为它再次说明：

```text
Evaluator
```

不是 Harness 的宗教仪式。

它是一块：

```text
model-relative scaffolding
```

后面 Macro 7 我们还会专门回来讲这一点。

---

#### 一个适合面试的回答：为什么 Agent 需要 Verifier？

如果面试官问：

> 模型自己已经会跑测试、检查代码了，为什么还要额外 verifier？

我现在会这样回答：

> 因为执行者自己的验证容易和实现轨迹共享同一套假设。Generator 可能误解需求，然后围绕这个误解实现、写测试、运行测试，最后得到一个内部完全自洽但与真实目标错位的结果。独立 verifier 的价值不是它绝对正确，而是它拥有不同目标：主动寻找对“任务已完成”这一 claim 的反例，并依据独立的 acceptance criteria 或真实环境反馈给 Generator 提供修正信号。

再压成一句：

```text
Generator asks:
“How can I make this work?”

Verifier asks:
“How can I prove this is not done yet?”
```

这两个问题不能完全互换。

---

#### 这也是为什么“完成”应该是一条外部证据链

所以更可靠的：

```text
DONE
```

不应该来自：

```text
assistant:
“I’m done.”
```

而应该越来越接近：

```text
Requirement
    ↓
Acceptance Criteria
    ↓
Artifact
    ↓
Independent Checks
    ↓
Observed Results
    ↓
Pass / Fail
```

这才是真正的 completion protocol。

也就是说：

> **完成不是一种模型情绪，而是一组可以被外部观察支持的状态。**

---

#### 再接回父文的五个动词

现在：

```text
修正
```

这个词也更完整了。

之前我们已经有：

```text
Tool result
    ↓
模型看到执行失败
    ↓
继续修正
```

这是局部反馈。

现在 Evaluator 引入的是更高一级：

```text
整个 Artifact
    ↓
独立 Verification
    ↓
发现 Requirement Gap
    ↓
Generator Revision
```

所以 Harness 的反馈层级可以是：

```text
Level 1
Tool feedback
命令失败 / 文件内容 / API result

Level 2
Task verification
功能是否真正满足 acceptance criteria

Level 3
Human/product judgment
是否真的达到用户想要的质量
```

越往上，就越不能简单依赖 Generator 自己一句：

```text
looks good
```

---

#### 源码与证据边界

从 Anthropic 2026 年 3 月的 long-running harness 文章，我们可以直接确认：

* Anthropic 将 self-evaluation 明确列为复杂长任务中的第二类 failure mode；
* Agent 在评价自己生成的内容时有明显正向偏差，主观设计任务尤其明显；
* 即使在具有可验证结果的任务上，也仍然会出现判断失准；
* 将执行者与评价者分离能够显著缓解这个问题；
* 但独立 evaluator 仍然是 LLM，也会过度宽容，因此分离本身并不自动产生可靠 QA；
* 独立 evaluator 的好处之一，是更容易单独调成 skeptical，并把具体反馈送回 generator。

这里目前还没有展开：

```text
Evaluator 到底怎样看到真实 App？
它怎样验证 UI / API / DB？
怎样把 “done” 变成 testable contract？
```

这些留到下一 Beat。


现在我们只是说明了：

```text
Generator 不应该拥有
“最终宣布自己通过”
的唯一权力。
```

但如果另开一个 Evaluator，只让它读代码然后说：

```text
看起来不错。
```

其实只是把：

```text
self-evaluation
```

换成了：

```text
another-LLM evaluation
```

仍然不够。

下一 Beat 要继续追问：

> **Verifier 到底应该看什么，才能比 Generator 的自我评价更接近现实？**

Anthropic 在这里做了一个非常具体的选择：

```text
不要只读代码。
```

让 Evaluator 真的通过 Playwright MCP：

```text
打开运行中的 App
点击 UI
调用功能
检查 API
观察数据库状态
```

也就是说：


**Verifier 为什么必须看到真实世界？**

下一节的关键词是：

```text
grounded verification
```

也就是把：

```text
“代码看起来应该工作”
```

换成：

```text
“我实际操作过，它确实这样工作。”
```

---

### 1.2 Verifier 为什么必须看到真实世界？


上一 Beat 已经留下了一个很重要的区分：

```text
Generator
    ↓
负责让系统“看起来已经完成”

Evaluator
    ↓
负责寻找“其实还没完成”的证据
```

但这里只解决了：

```text
谁来验？
```

还没有解决：

```text
拿什么验？
```

如果我们只是新开一个 Agent，让它读取 Generator 写出的代码：

```text
Generator
    ↓
写代码
    ↓
Evaluator
    ↓
读代码
    ↓
“看起来没问题”
```

那其实离真正的 verification 还差很远。

因为软件是否可用，不只存在于源码里。

一个功能真正成立，至少跨过了这样一条链：

```text
Code
  ↓
Build
  ↓
Runtime
  ↓
API
  ↓
State
  ↓
UI
  ↓
User interaction
```

其中任意一层断掉，用户看到的都可能是：

```text
“代码明明写了，
但功能就是不能用。”
```

Anthropic 在 full-stack Harness 实验里正好碰到了这个问题：早期系统生成出的 App 表面上已经相当完整，但实际点进去以后仍然存在真正的功能性 Bug。于是他们没有让 Evaluator 只读代码，而是给它 Playwright MCP，让它像用户一样操作正在运行的应用，同时检查 UI、API endpoint 和数据库状态。


* **grounded verification**：Verifier 的判断应该尽可能建立在系统实际运行后产生的外部 observation 上，而不是只根据实现代码推测“它应该能工作”。

---

#### “代码存在”不是“行为存在”

这个区别特别适合用一个最简单的前端例子理解。

假设 Generator 写出了：

```ts
function handleDelete() {
  deleteEntity(selectedEntityId)
}
```

Evaluator 读代码以后可能说：

```text
有 deleteEntity()
有 click handler
有 selectedEntityId

所以删除功能已经实现。
```

从静态代码层面看，确实很合理。

但真实运行时可能是：

```text
用户点击实体
    ↓
selectedEntityId 被设置
    ↓
按 Delete
    ↓
handler 额外要求 selection !== null
    ↓
条件不成立
    ↓
什么都没有发生
```

于是出现：

```text
Implementation exists
        ≠
Behavior works
```

这个差别在复杂 App 里会大量出现。

因为功能成立往往依赖多个模块正确连接：

```text
UI event
   ↓
frontend state
   ↓
API request
   ↓
backend route
   ↓
business logic
   ↓
database mutation
   ↓
response
   ↓
frontend refresh
```

源码里每一块都可能：

```text
“看起来有实现”
```

但整条 path 仍然坏掉。

---

#### 所以仅靠 Code Review 存在天然盲区

Code Review 很重要。

但它擅长发现的是：

```text
明显逻辑错误
类型问题
危险实现
坏味道
不合理结构
遗漏的 edge case
```

它没有天然能力证明：

```text
这个按钮在浏览器里真的能点

点击以后请求真的发出去了

后端真的匹配到了正确 route

DB 真的写入了正确状态

刷新以后状态真的还存在
```

这就是：

```text
Static correctness
```

和：

```text
Runtime correctness
```

之间的差距。

可以粗略画成：

```text
Source Code
    │
    │ code review
    ▼
“按实现来看应该工作”
    │
    │ run system
    ▼
Runtime
    │
    │ interaction
    ▼
“实际确实这样工作”
```

Verifier 如果只停留在第一层，它得到的是：

```text
prediction
```

而不是：

```text
observation
```

---

#### Anthropic 的 Evaluator 不是“看看页面截图”

这一点也很重要。

在早期 frontend experiment 中，Evaluator 已经通过 Playwright MCP 主动操作页面，而不是只看 Generator 截出来的一张静态图：它会导航页面、截图并研究真实实现，再按照评价 criteria 输出 critique。

到了 full-stack coding experiment，这个思路又继续往前走。

Evaluator 被要求：

```text
启动 / 访问真实 App
        ↓
点击 UI
        ↓
尝试真实 workflow
        ↓
检查 API
        ↓
检查 database state
        ↓
对照 sprint contract
        ↓
PASS / FAIL
```

Anthropic 明确写到，这个 Evaluator 会通过 Playwright MCP 像用户一样点击运行中的应用，并同时测试 UI feature、API endpoint 和数据库状态。

所以这里的关键不是：

```text
用了 Browser Automation
```

而是：

> **Verifier 获得了一个与用户更加接近的 observation channel。**

---

#### 为什么“像用户一样操作”特别重要？

因为真实用户根本看不到：

```text
你写了多少个 Component
你定义了多少个 function
代码结构有多优雅
```

用户看到的是：

```text
我点了没有？
有没有反应？

我保存了没有？
刷新以后还在不在？

我创建了对象没有？
页面里出现没有？

我按键以后角色动没动？
```

所以从 acceptance 的角度：

```text
用户行为
```

往往比：

```text
源码结构
```

更接近 Ground Truth。

比如需求是：

> 用户可以创建 Sprite 并在 Level Editor 中使用。

Code Review 可能确认：

```text
SpriteEditor exists
createSprite() exists
LevelEditor exists
spriteId exists
```

但真实 verification 应该做：

```text
打开 Sprite Editor
    ↓
新建 Sprite
    ↓
画几个像素
    ↓
保存
    ↓
进入 Level Editor
    ↓
选择刚才的 Sprite
    ↓
把它放到地图上
    ↓
确认显示正确
```

这里每一步都在问：

> **系统真正发生了什么？**

---

#### 这其实和前面的 Tool Result 是同一种思想，只是层级更高

Macro 2 里我们已经讲过：

```text
模型认为：
pytest 应该通过

        ↓

Harness 实际运行 pytest

        ↓

现实：
3 failed
```

这里的：

```text
tool_result
```

就是一种 grounded feedback。

现在 Evaluator 做的事情只是把 verification scope 放大了。

##### 局部层级

```text
Bash("pytest")
    ↓
tool_result
    ↓
3 failed
```

验证：

```text
这条命令有没有成功？
```

##### Feature 层级

```text
Open browser
    ↓
Create project
    ↓
Refresh
    ↓
Project still exists
```

验证：

```text
这个用户故事有没有成立？
```

##### System 层级

```text
完整 workflow
    ↓
UI + API + DB
    ↓
cross-component behavior
```

验证：

```text
整个系统是不是像一个真实产品一样工作？
```

因此：

```text
Tool feedback
```

和：

```text
Evaluator feedback
```

本质上都属于父文里的：

```text
观察
```

只是 observation granularity 不同。

---

#### 一个特别好的例子：Route 明明存在，但 API 就是坏的

Anthropic 在文章里展示了 Evaluator 抓到的一类真实问题：

某个 animation frame reorder API 本身已经定义出来了。

也就是说读代码时完全可以找到：

```text
PUT /frames/reorder
```

乍看：

```text
reorder feature = implemented
```

但运行时实际请求却被前面的动态 route 当成：

```text
/{frame_id}
```

来解析，于是字符串 `reorder` 被当成整数 ID，最终请求失败。

这就是非常典型的：

```text
Route exists
    ≠
Route reachable correctly
```

静态检查看到的是：

```text
“函数在那里。”
```

运行时看到的是：

```text
“请求根本到不了那里。”
```

如果不真的：

```text
PUT /frames/reorder
```

一次，这个 Bug 很容易被：

```text
代码完整性幻觉
```

掩盖。

---

#### UI 更是这样

另一个常见例子是：

```text
function exists
```

但交互没有把它连起来。

Anthropic 的 Evaluator 就发现过类似问题：某个 rectangle fill 实现函数存在，但真实 mouse interaction 并没有正确触发它，因此实际拖拽行为只处理了起点和终点，并没有完成用户期望的区域填充。

这种 Bug 特别值得记住。

因为 Generator 很容易在源码里看到：

```text
fillRectangle()
```

然后形成：

```text
“Rectangle Fill 已经实现。”
```

但用户真正拥有的是：

```text
mouseDown
    ↓
drag
    ↓
mouseUp
    ↓
???
```

所以：

```text
function implementation
```

只是能力潜力。

只有：

```text
user event → actual behavior
```

才是功能。

---

#### 这就是为什么我现在会区分三种“证据”

以后读 Agent 生成的项目，我觉得可以把 evidence 分成三个层级。

##### 第一层：Implementation Evidence

例如：

```text
函数存在
组件存在
接口存在
测试文件存在
```

它能证明：

> 有人尝试实现了这件事。

但不能证明：

> 这件事真的可用。

---

##### 第二层：Execution Evidence

例如：

```text
pytest passed

curl API 返回 200

build 成功

数据库确实插入 row
```

它证明某个 concrete execution 成功了。

这已经比：

```text
代码看起来正确
```

强很多。

---

##### 第三层：Behavior Evidence

例如：

```text
用户真实 workflow 完成

点击 → UI 更新
保存 → DB 更新
刷新 → 状态恢复
删除 → UI / API / DB 一致
```

它验证的是：

```text
system-level behavior
```

这才最接近：

```text
Acceptance Criteria
```

所以 evidence strength 可以大致理解成：

```text
Implementation evidence
        ↓
Execution evidence
        ↓
Behavior evidence
```

不是说后者永远取代前者。

而是它们回答不同问题。

---

#### 为什么测试也不一定够？

前一 Beat 已经说了：

```text
tests pass
≠
requirements satisfied
```

这一 Beat 可以把原因说得更具体。

自动测试很可能只覆盖：

```text
developer anticipated behavior
```

但真实用户还会遇到：

```text
workflow sequencing
state transitions
layout
navigation
integration
browser-specific behavior
unexpected combinations
```

例如：

```text
Create Sprite
```

的 unit test 通过了。

```text
Create Entity
```

的 unit test 也通过了。

```text
Place Entity
```

的 unit test 也通过了。

但真实 workflow：

```text
创建 Sprite
    ↓
创建 Entity
    ↓
绑定 Sprite
    ↓
加入 Level
    ↓
进入 Play Mode
```

仍然可能断在：

```text
Entity definition
        ↓
runtime representation
```

之间。

Anthropic 的 solo run 正好出现了这种情况：界面上实体已经存在，但真正进入 play mode 后并不能按照预期响应输入，问题出在 entity definition 与 runtime 的 wiring。Harness run 则通过更系统的验证把核心 playable behavior 做了出来。

---

#### 于是真正好的 Acceptance Criterion 应该尽量写成 Behavior

这也接上上一 Beat 的：

```text
Sprint Contract
```

差的 criterion：

```text
Implement entity deletion.
```

它很容易被 Generator 解释成：

```text
存在 deleteEntity()
```

更好的 criterion 是：

```text
Given:
Level 中有一个 entity spawn

When:
用户选中它并按 Delete

Then:
该 spawn 从画布消失，
对应状态也被删除。
```

这就天然告诉 Evaluator：

```text
去做什么
去观察什么
什么结果算通过
```

所以：

```text
Spec
```

真正进入 Harness 以后，不应该只是 implementation description。

它最好逐渐变成：

```text
Executable expectation
```

---

#### Sprint Contract 真正补的是高层 Spec 和真实执行之间的距离

Anthropic 的 Planner 故意保持 product spec 较高层，避免一开始就把具体技术实现写死；但这会留下一个问题：

```text
用户故事
    ↓
？
    ↓
具体这一 Sprint 怎样算 Done
```

因此在每个 Sprint 开始之前，Generator 和 Evaluator 会先协商 contract：

```text
Generator:
我准备实现这些东西。

我会通过这些行为证明完成。

Evaluator:
这些验证还不够。
这里还有一个 requirement 没覆盖。

        ↓

双方继续修改

        ↓

Contract agreed
        ↓
开始写代码
```

Anthropic 的目的就是在 high-level product spec 与 testable implementation 之间建立这一层桥梁。

这一步我觉得非常值得借到自己的 Vibe Coding / SDD 流程里。

---

#### 因为“Done”的定义应该在 implementation 之前被冻结一部分

假设不这样做。

Generator 可能：

```text
先实现
    ↓
发现自己的实现只能做到 A
    ↓
于是把 Done 解释成 A
```

这就是：

```text
implementation
rewrites acceptance
```

而 Sprint Contract 的思路是：

```text
Requirement
    ↓
Define observable success
    ↓
Implementation
```

虽然执行过程中 contract 仍然可能调整，但至少不能完全变成：

```text
我做成什么样，
什么样就叫完成。
```

所以：

```text
Verifier
```

不仅发生在写完代码之后。

它甚至在写代码之前，就参与：

```text
定义什么证据才算完成
```

---

#### 这和 TDD 很像，但范围更大

这里很容易联想到 Test-Driven Development：

```text
先定义 expected behavior
    ↓
写失败测试
    ↓
实现
    ↓
测试通过
```

Sprint Contract 的精神确实很接近：

```text
先定义 observable done
    ↓
再 implementation
```

但范围要大得多。

它可能包含：

```text
UI interaction
API behavior
database state
visual quality
workflow completeness
code quality
```

其中很多东西未必能轻易压成一个：

```ts
expect(...).toBe(...)
```

所以：

> **Contract 可以看成比 automated test 更宽的 verification specification。**

---

#### Verifier 的输入不应该只有代码

到这里可以得到一个非常具体的 Harness 设计原则。

差的 Verifier interface：

```text
verify(sourceCode)
```

更好的可能是：

```text
verify(
  spec,
  acceptanceCriteria,
  runningEnvironment,
  availableTools
)
```

为什么？

因为它需要：

```text
知道应该发生什么
        ↓
亲自触发行为
        ↓
观察真正发生什么
        ↓
比较两者
```

也就是：

```text
Expected
    ↓
Interact
    ↓
Observed
    ↓
Diff
```

这个：

```text
Diff
```

才是 Generator 真正有用的 revision signal。

---

#### “真实世界”也不是只有浏览器

这里不要把：

```text
grounded verification
```

误解成：

> 一定要上 Playwright。

Playwright 只是这个 full-stack experiment 的具体工具。

真正原则是：

> **Verifier 应该获得与被验证对象相匹配的 observation channel。**

如果是 CLI：

```text
运行 CLI
检查 stdout
检查 exit code
检查生成文件
```

如果是 API：

```text
发 HTTP request
检查 response
检查 DB
```

如果是 compiler：

```text
编译
运行 binary
比较输出
```

如果是 data pipeline：

```text
跑 pipeline
检查产物
检查 row counts / invariants
```

如果是 Browser App：

```text
Playwright
真实点击
真实导航
真实状态
```

如果是 infrastructure：

```text
部署
health check
integration probe
logs / metrics
```

所以原则不是：

```text
Browser is magic
```

而是：

```text
Verification
must touch the relevant environment.
```

---

#### Harness 的“观察能力”决定了它能验证什么

这其实又回到了 Tool surface。

假设 Evaluator 的 tools 只有：

```text
Read
Grep
```

那么它最多做到：

```text
static review
```

如果增加：

```text
Bash
```

它可以：

```text
run tests
call APIs
inspect DB
```

如果再增加：

```text
Playwright MCP
```

它可以：

```text
observe user-facing behavior
```

所以：

```text
Verifier quality
```

不只取决于：

```text
Evaluator model
```

也取决于：

```text
Evaluator observation surface
```

可以粗略写成：

```text
Verification capability
≈
Evaluator reasoning
×
Observable environment
×
Quality of criteria
```

还是那句话：

这不是数学公式。

但很适合帮助理解。

---

#### 为什么这对 Agent 特别重要？

传统工程里，人类 QA 天然拥有很多隐式能力：

```text
我可以打开浏览器
我会觉得这个按钮不对
我会乱点几下
我会尝试刷新
我会故意输奇怪的值
我会发现流程很别扭
```

但 Agent 不会天然拥有这些 observation channel。

如果 Harness 只给它：

```text
repo filesystem
```

然后要求：

> 请验证整个 Web App。

它只能用：

```text
source-level proxy
```

去猜用户体验。

所以 Agent QA 的关键不是：

```text
Prompt 写得像 QA
```

而是：

> **Harness 有没有真正给它 QA 所需的眼睛和手。**

这也是 Playwright MCP 在 Anthropic 实验中的真正意义。

它不是“多了一个 Tool”。

它让 Evaluator 从：

```text
看代码猜页面
```

变成：

```text
真正进入页面。
```

---

#### 这与我们最开始定义 Harness 的方式完全对上了

父文里我们定义 Harness Engineering 是让 Agent：

```text
找到正确知识
执行真实动作
观察动作结果
受到稳定约束
根据反馈继续修正
```

现在 Evaluator 几乎把这五个词重新走了一遍：

```text
找到
↓
读 Sprint Contract

行动
↓
点击 UI / 调 API

观察
↓
看到页面、response、DB state

约束
↓
按 criteria / threshold 判断

修正
↓
把 failure feedback 交给 Generator
```

于是 Verification 根本不是 Agent loop 外面临时加的一道：

```text
QA step
```

它自己就是另一种 Agent loop。

---

#### Generator Loop 和 Evaluator Loop 是两种不同的反馈循环

Generator：

```text
Requirement
    ↓
Hypothesis
    ↓
Code
    ↓
Tool feedback
    ↓
Revision
```

Evaluator：

```text
Acceptance Criteria
    ↓
Test hypothesis
    ↓
Interact with system
    ↓
Observation
    ↓
Pass / Failure report
```

然后两者再组成更大的 loop：

```text
Generator
    ↓
Artifact
    ↓
Evaluator
    ↓
Failure Evidence
    ↓
Generator
```

这就是 Anthropic 那个 generator-evaluator pattern 真正有意义的地方。

不是：

```text
两个 Claude 互相聊天
```

而是：

```text
两个角色通过真实 Artifact
和外部 Observation
形成 feedback control loop。
```

---

#### 一个我现在会用的 Verification Ladder

如果我自己设计 Coding Agent Harness，我会把验证大概分成这样：

```text
Level 0
模型自评
“看起来应该好了”

        ↓

Level 1
Static checks
类型 / lint / code review

        ↓

Level 2
Executable checks
unit / integration test
build / API probe

        ↓

Level 3
Behavior checks
真实 workflow
UI / API / DB 联动

        ↓

Level 4
Human/product judgment
体验、审美、业务合理性
```

不是每个任务都必须爬到 Level 4。

比如修一个纯算法函数：

```text
Level 2
```

可能已经非常充分。

但如果任务是：

```text
“做一个完整可用的 Web App”
```

然后 Harness 只做到：

```text
npm build
```

就宣布：

```text
DONE
```

显然 verification depth 和 task depth 不匹配。

所以还有一个很实用的原则：

> **Verification depth 应该和任务的真实 failure surface 匹配。**

---

#### 一个适合面试的回答：为什么 Verifier 要真的跑系统？

如果面试官问：

> Evaluator 读代码不就行了吗，为什么一定要启动 App？

可以回答：

> 因为静态实现只能证明代码看起来具备某种 capability，却不能证明跨组件的 runtime behavior 真正成立。很多 Agent 生成代码的问题恰好出现在 wiring、route precedence、state synchronization 和 UI interaction 这些运行时边界上。把 Evaluator 接到真实运行环境，让它通过 browser、API、database 等 observation channel 执行 acceptance criteria，才能把“应该工作”的预测转成“实际工作”的证据。

再压成一句：

```text
Code review asks:
“Why should this work?”

Grounded verification asks:
“What actually happened when I tried?”
```

---

#### 源码与证据边界

从 Anthropic 2026 年 3 月的 long-running harness 实验，可以直接确认：

* frontend evaluator 获得了 Playwright MCP，可以直接导航和操作真实页面，而不是只对静态输出进行评分；
* full-stack evaluator 同样使用 Playwright MCP 操作运行中的应用，并验证 UI feature、API endpoint 和 database state；
* 每个 Sprint 都依据具体 contract criteria 进行验证，并设置 hard threshold；任一关键 criterion 低于要求，Sprint 就失败并把具体反馈交回 Generator；
* Generator 和 Evaluator 在编码前会先协商 Sprint Contract，用于把高层 product spec 转成具体、可测试的 done；
* Anthropic 的实际结果中，Evaluator 找到了多类“源码看起来已经实现、真实运行却失败”的 integration / interaction bug。

这里仍然不能推出：

```text
有 Playwright
=
Verification 已经可靠
```

因为下一节恰好要讲：

> **Evaluator 自己也会偷懒、合理化 Bug、测试得过于表面。**

Grounding 只是让它拥有真实证据。

它愿不愿意认真找证据、怎样解释这些证据，是另一个问题。


现在我们已经从：

```text
Generator：
“我认为完成了。”
```

推进到了：

```text
Evaluator：
“我实际打开系统，
执行了这些行为，
观察到了这些结果。”
```

看起来 Verification 已经解决了。

但 Anthropic 真正运行这个 Harness 以后，很快又发现一个非常尴尬的问题：

```text
Evaluator：
发现 Bug
    ↓
解释 Bug
    ↓
想了想
    ↓
“其实也没那么严重”
    ↓
PASS
```

甚至还有：

```text
只点最明显的 Happy Path
    ↓
没发现问题
    ↓
PASS
```

也就是说：

> **让 Evaluator 看到真实世界，只解决了“有没有证据源”；并没有解决“它是否会严格使用这些证据”。**

于是 Macro 5 还差最后一层：


**Verifier 自己不可靠吗？**

下一节的新概念是：

```text
verification calibration
```

也就是：

> Harness 不只要验证 Generator，甚至还得通过 logs、failure examples 和 prompt iteration 去调试那个负责验证的 Evaluator。
### 1.3 Verifier 自己不可靠吗？


前两节已经把 Verification 推了两层。

第一层：

```text
Generator
≠
Evaluator
```

因为执行者容易对自己的结果过于宽容。

第二层：

```text
Evaluator
+
真实运行环境
```

因为只看代码仍然只能得到：

```text
“它应该工作。”
```

而 Playwright、API、数据库这些 observation channel 可以把判断推进到：

```text
“我实际试过，它就是这样工作。”
```

看起来事情已经解决了。

但 Anthropic 真正把这套 Harness 跑起来以后，又撞到了一个非常尴尬的问题：

> **Evaluator 明明看到了 Bug，却不一定愿意判它失败。**

甚至有时候，它根本不会认真去找那些比较隐蔽的 Bug。

Anthropic 对早期 QA Agent 的描述非常直白：它会先找到真实问题，然后自己把这些问题解释成“不算太严重”，最后照样批准；同时它还倾向于只做表面测试，不主动探索 edge case，于是更深层的 Bug 很容易漏掉。

这说明：

```text
有独立 Evaluator
≠
Evaluator 可靠

有真实环境
≠
Evaluator 会认真验证
```

所以这一 Beat 再引入一个概念。


* **verification calibration**：Verifier 本身也是一个需要通过真实 trace、failure case 和人工判断不断调试的 Agent；Harness 不应该把 Evaluator 当作天然可靠的 oracle，而要持续校准它“什么算失败、应该测试多深、什么时候不能自我合理化”。

---

#### 最危险的不是“没看到 Bug”，而是“看到了又放过去”

先看第一类失败。

假设 Sprint Contract 写着：

```text
用户可以拖拽矩形区域进行 Fill。
```

Evaluator 实际操作以后发现：

```text
拖动鼠标
    ↓
只填了起点和终点
    ↓
中间区域没有填充
```

这已经是非常清楚的：

```text
Expected
    ≠
Observed
```

如果是一个硬判断程序：

```ts
if (observed !== expected) {
  fail()
}
```

事情到这里就结束了。

但 LLM Evaluator 不是普通断言函数。

它可能继续“理解”这个失败：

```text
虽然矩形没有完全填充，
但 fillRectangle 函数已经存在，
主体实现基本完成，
这个问题可能只是一个小的 wiring bug，
整体功能仍然比较完整……
```

然后：

```text
PASS
```

这正是 Anthropic 早期实验里观察到的问题：Evaluator 找到了 legitimate issue，却随后通过自己的解释把严重性降下来，最终仍然批准工作。

这件事非常值得注意。

因为此时失败并不发生在：

```text
Observation
```

层。

Evaluator 已经正确观察到了现实。

失败发生在：

```text
Observation
    ↓
Judgment
```

之间。

---

#### 所以 Verification 其实还有两步

我们前面一直写：

```text
Expected
    ↓
Interact
    ↓
Observed
    ↓
Pass / Fail
```

现在要再拆细一点：

```text
Expected
    ↓
Test Selection
    ↓
Interaction
    ↓
Observation
    ↓
Interpretation
    ↓
Judgment
```

其中至少有两类不同的 verifier failure：

##### Failure A：没测到

```text
测试太浅
    ↓
关键路径没有执行
    ↓
Bug 没被发现
```

##### Failure B：测到了但没判 Fail

```text
观察到明显偏差
    ↓
LLM 开始解释
    ↓
“也许问题不大”
    ↓
PASS
```

所以：

> **真实 observation 只是 verification 的必要条件，不是充分条件。**

---

#### 为什么 LLM Evaluator 会替 Bug 找理由？

这里和上一 Beat 的 self-evaluation 有一点相似，但又不完全一样。

独立 Evaluator 已经没有：

```text
“这是我自己写的，所以我想维护它。”
```

这层 trajectory coupling。

但它仍然是一个语言模型。

而语言模型非常擅长：

```text
理解上下文
寻找合理解释
平衡多个观点
给出温和判断
```

这些能力在很多任务里是优点。

到了 QA 场景，却可能变成问题。

QA 有时真正需要的不是：

```text
“全面、平衡地看待这个问题。”
```

而是：

```text
“Criterion 没满足就是没满足。”
```

比如：

```text
Requirement:
click-drag fills entire rectangle

Observed:
only start/end points filled
```

这时最有用的判断其实非常机械：

```text
FAIL
```

而不是：

```text
虽然核心实现存在，
但交互连接存在轻微问题，
整体已经接近完成……
```

于是：

> **一个好 Evaluator 有时反而需要被训练得比普通 Assistant 更不善解人意。**

---

#### `Hard Threshold` 的意义就在这里

Anthropic 的 full-stack Harness 没有只让 Evaluator：

```text
整体打个 8/10。
```

他们给每个 criterion 设置了 hard threshold：只要任何一项低于要求，Sprint 就失败，并把具体反馈送回 Generator。

为什么这样设计？

因为如果只用总分：

```text
视觉设计 9
代码质量 9
功能完整度 5
整体平均 7.7
```

Evaluator 很容易得出：

```text
整体还不错，可以过。
```

但假如用户真正最在意的是：

```text
核心功能必须可用
```

那么：

```text
functionality = 5
```

就应该直接阻断。

所以：

```text
weighted average
```

有时会掩盖：

```text
critical failure
```

而 hard threshold 在做的是：

```text
Criterion A >= threshold
AND
Criterion B >= threshold
AND
Criterion C >= threshold
...
```

任何关键项不满足：

```text
FAIL
```

这实际上是在减少 LLM 的：

```text
“综合考虑以后我觉得也可以。”
```

空间。

---

#### 这和软件测试里的 Assertion 很像

例如：

```ts
expect(loginSucceeded).toBe(true)
expect(projectPersisted).toBe(true)
expect(deleteActuallyRemovedEntity).toBe(true)
```

不会因为：

```text
前两个都很好，
第三个只差一点
```

就给你：

```text
2.7 / 3，算通过。
```

第三个断言失败：

```text
test failed
```

Anthropic 的 hard threshold 本质上也是在给自然语言 Evaluator 引入更强的：

```text
assertion semantics
```

这很好地说明了：

> Prompt 中的 criteria 不只是“评价建议”，还可以成为 Harness 的控制逻辑。

---

#### 第二类问题更隐蔽：Evaluator 测得太浅

另一个早期问题是：

```text
QA 只测 Happy Path。
```

例如 criterion 是：

```text
用户可以删除 entity。
```

Evaluator 可能只做：

```text
打开页面
    ↓
点一个最明显的对象
    ↓
按 Delete
    ↓
某个对象消失
    ↓
PASS
```

但真实系统可能还有：

```text
不同 layer 下呢？

只有 selectedEntityId、
没有 selection 时呢？

删除以后 DB state 呢？

刷新以后对象会不会回来？

键盘 focus 不在 canvas 时呢？
```

如果 Evaluator 不主动 probing：

```text
edge cases
```

就只验证了：

```text
最顺的一条路径
```

而不是：

```text
feature reliability
```

Anthropic 明确说，早期 Evaluator 倾向于 superficial testing，而不是主动探测 edge cases，所以更细微的问题会漏掉。

---

#### “跑过一次”不等于“验证充分”

这点很适合拿我们平时写测试来类比。

假设函数：

```ts
divide(a, b)
```

你只测：

```text
divide(6, 2) = 3
```

然后说：

```text
divide works
```

显然不够。

因为你还会想到：

```text
b = 0
负数
浮点数
NaN
overflow
```

同理，对一个 UI feature：

```text
我点过一次
```

只能证明：

```text
这个特定 interaction path
在这个特定状态下成功过
```

不能证明：

```text
功能整体可靠
```

因此 grounded verification 还必须回答：

> **Test coverage 到底够不够？**

---

#### LLM QA 最大的问题之一：它没有天然 Coverage Sense

人类资深 QA 看到：

```text
用户可以创建、删除 Entity
```

往往会本能地想：

```text
创建两个呢？
删除当前选中的呢？
删除没有选中的呢？
Undo 呢？
刷新呢？
别的 layer 呢？
```

这是长期工程经验形成的：

```text
failure imagination
```

但 LLM 如果 Prompt 里只写：

```text
verify this feature
```

它很可能找到一个最简单的成功路径，然后结束。

所以一个 QA Agent 不只是需要：

```text
能力足够强
```

还需要 Prompt 明确诱导：

```text
不要只证明 happy path
主动寻找反例
尝试 edge case
检查跨层状态
不要因为功能“大致存在”就放行
```

这其实就是 calibration 的一部分。

---

#### Anthropic 真正怎么调 Evaluator？

这里最值得学的是他们的方法。

不是：

```text
感觉 QA 不好
    ↓
再加一句
“Please be more careful.”
```

而是：

```text
运行 Harness
    ↓
读取 Evaluator logs
    ↓
找到我和 Evaluator
判断不一致的具体案例
    ↓
更新 QA prompt
    ↓
重新运行
    ↓
再读 logs
```

Anthropic 明确描述了这个 tuning loop：阅读 Evaluator 的日志，找出它的判断和作者人工判断发生偏差的实例，然后修改 QA prompt 去针对这些失败；如此迭代数轮以后，Evaluator 才达到相对合理的 grading 行为。

这其实就是：

```text
Evaluator
```

自己也成了一个需要 Eval 的模型组件。

---

#### 这就出现了一个很有意思的递归问题

我们一开始问：

```text
谁验证 Generator？
```

答案是：

```text
Evaluator。
```

现在又问：

```text
谁验证 Evaluator？
```

答案不能简单变成：

```text
Evaluator 2。
```

否则：

```text
Generator
    ↓
Evaluator
    ↓
Evaluator evaluator
    ↓
Evaluator evaluator evaluator
    ↓
...
```

无限套娃。

Anthropic 实际上的答案更朴素：

```text
human judgment
+
trace inspection
+
failure examples
+
prompt iteration
```

也就是说，在开发 Harness 的阶段，人类仍然承担：

```text
meta-evaluator
```

的角色。

---

#### 人类不是逐动作监督，而是监督 Harness 的判断边界

这点非常重要。

传统的人在 loop：

```text
Agent 做一步
    ↓
问人
    ↓
再做一步
    ↓
再问人
```

这样人类是：

```text
execution supervisor
```

而更成熟的 Harness 希望变成：

```text
Agent 自主跑很多步
    ↓
Evaluator 自主验
    ↓
人类偶尔查看 traces
    ↓
发现 evaluator 系统性偏差
    ↓
修改 criteria / prompt / tools
```

人类角色从：

```text
逐动作审批者
```

上移成：

```text
verification policy designer
```

这才真正降低了长期 Agent 的监督成本。

---

#### 这和传统软件测试也非常像

测试代码本身也会有 Bug。

比如：

```text
生产代码
    ↓
unit test
```

不代表：

```text
unit test = truth
```

测试可能：

```text
assert 写错
fixture 不合理
覆盖不完整
mock 过度
只测 happy path
```

所以成熟团队也会：

```text
review tests
看 coverage
做 mutation testing
看线上故障反推测试缺口
```

Evaluator 也是一样。

它本质上是一段：

```text
动态生成 verification procedure
```

因此同样需要验证它自己的质量。

---

#### 从这里可以重新理解 Trace 的价值

很多 Agent 系统都会存：

```text
trace
```

我们经常把它理解成：

```text
出 Bug 以后方便 debug。
```

但 Anthropic 这里展示的是更强的用途：

```text
Trace
    ↓
观察 Agent 如何判断
    ↓
找到系统性失败模式
    ↓
修改 Harness
```

例如：

```text
Evaluator:
发现 Bug
    ↓
写了一大段理由
    ↓
最终 PASS
```

如果只看最终输出：

```text
PASS
```

你可能不知道发生了什么。

但看 trace 才能发现：

> 它不是没发现 Bug，而是在 reasoning 过程中把 Bug 合理化掉了。

这两种 failure 的修法完全不同。

---

#### 如果只看最终指标，很容易修错地方

假设 QA recall 很低。

可能原因 A：

```text
没有足够 Tools
→ 看不到真实系统
```

修法：

```text
增加 Playwright / API / DB access
```

可能原因 B：

```text
有 Tools
但测试太浅
```

修法：

```text
改 QA strategy / criteria
```

可能原因 C：

```text
发现 Bug
但判断太宽松
```

修法：

```text
hard threshold
更 skeptical 的 prompt
few-shot calibration
```

如果不看 trace，只看到：

```text
Evaluator missed bug
```

就无法判断是哪一层坏了。

所以：

> **Harness Engineering 很大一部分工作，其实是 trace-driven debugging。**

---

#### Anthropic 的 frontend evaluator 也用了 Few-shot Calibration

这点在前面的 frontend design 实验里其实已经出现。

Anthropic 为 Evaluator 提供了：

```text
detailed score breakdown
few-shot examples
```

目的是让它的 judgment 更接近作者偏好，同时减少迭代之间的评分漂移。

这说明 calibration 至少包括：

```text
criteria
+
examples
+
threshold
+
trace review
```

而不只是：

```text
system prompt:
“You are a strict reviewer.”
```

---

#### 评价标准的措辞本身也会改变系统行为

Anthropic 还观察到一个挺有意思的问题：

```text
criteria wording
```

不仅影响 Evaluator 怎么打分。

它还会反过来影响 Generator 输出的风格。

比如他们在设计 criteria 中用了非常强调高质量审美的措辞，结果模型输出逐渐向特定视觉方向收敛。

这意味着：

```text
Evaluator rubric
```

并不是一个中立测量仪。

它本身也是：

```text
optimization pressure
```

因为：

```text
Evaluator feedback
    ↓
Generator 根据 feedback 改
    ↓
最终输出逐渐朝 rubric 偏好移动
```

所以设计 Evaluator criteria，本质上是在定义：

> **Harness 想把系统优化到什么方向。**

---

#### 这和 Reward Model 的味道已经很像了

这里虽然不是 RLHF，也没有训练 Reward Model，但结构上确实有点相似：

```text
Generator
    ↓
Candidate
    ↓
Evaluator
    ↓
Score / Critique
    ↓
Generator update
```

区别是这里：

```text
update
```

不是梯度更新。

而是：

```text
下一轮 context 中收到反馈
```

但从系统视角看：

```text
Evaluator
```

仍然在定义：

```text
什么行为被奖励
什么行为被惩罚
```

所以 Evaluator 一旦 calibration 有问题：

```text
reward signal
```

就会歪。

---

#### 一个差的 Verifier 甚至会把 Generator 教坏

假设 Evaluator 总是：

```text
UI 大概能用
→ PASS
```

那么 Generator 很快会发现：

```text
只做一个浅层 UI 壳子
也足够得到 PASS
```

虽然这里不存在显式强化学习训练，但 repeated feedback loop 仍然会让 Generator：

```text
围绕 evaluator weakness
收敛到更便宜的实现
```

这就是一种类似：

```text
Goodhart's law
```

的问题。

当：

```text
Evaluator score
```

成为优化目标以后，Generator 优化的可能不再是：

```text
真实产品质量
```

而是：

```text
怎样让这个 Evaluator 满意
```

所以 verifier calibration 不只是：

```text
测准一点
```

而是在保护整个 feedback loop 不被错误 reward signal 带偏。

---

#### 这也是为什么“具体 Bug 报告”比抽象低分更有价值

Anthropic 的 Evaluator 最终比较有用的地方，不只是说：

```text
Functionality: 6/10
```

而是能写出：

```text
Rectangle fill：
drag 只影响起点和终点；
fillRectangle 存在，
但 mouseUp 没正确调用。

Entity deletion：
点击 entity 只设置 selectedEntityId，
Delete handler 却同时要求 selection。

Frame reorder：
/frames/reorder 被 /{frame_id}
route 抢先匹配，返回 422。
```

这些反馈几乎可以直接送给 Generator 修。

这就是：

```text
score
```

和：

```text
actionable failure evidence
```

之间的区别。

前者告诉你：

```text
不好。
```

后者告诉你：

```text
哪里不好，
怎么复现，
可能坏在哪。
```

Generator 真正需要的是后者。

---

#### 所以 Evaluator 的目标不是“给分”

我现在会把 Evaluator 的任务重新定义成：

```text
寻找能够阻止当前 Artifact
被错误宣布为 Done 的证据。
```

评分只是其中一种 control mechanism。

真正有用的输出更像：

```text
Criterion
    ↓
Reproduction steps
    ↓
Observed behavior
    ↓
Expected behavior
    ↓
Evidence
    ↓
Likely failure location
```

也就是一个高质量 Bug Report。

---

#### QA Agent 最好默认是“反例搜索器”

这也是我觉得很适合写进自己 Harness 的一句 Prompt 思路：

```text
Do not try to prove that the implementation works.

Try to falsify the claim that it is complete.
```

对应中文就是：

> **不要寻找“为什么它已经完成”的证据，而要寻找一个足以证明“它还没完成”的反例。**

这比：

```text
Please review carefully.
```

具体很多。

因为它直接改变：

```text
search objective
```

---

#### Verification Calibration 可以拆成四层

到这里，可以把整个问题压成四层：

##### 1. Observation calibration

```text
Evaluator 有没有正确工具看到系统？
```

例如：

```text
Playwright
API
DB
CLI
```

---

##### 2. Coverage calibration

```text
它测得够不够深？
```

例如：

```text
Happy Path
Edge Case
Cross-component workflow
Nested feature
```

---

##### 3. Judgment calibration

```text
发现失败以后会不会放水？
```

通过：

```text
hard threshold
skeptical prompt
explicit FAIL semantics
```

约束。

---

##### 4. Feedback calibration

```text
失败结果是否足够让 Generator 修？
```

需要：

```text
reproduction
expected / observed
specific evidence
```

所以：

```text
Verifier quality
```

不是一个单维度指标。

---

#### 最关键的是：Harness 也需要自己的 Eval Loop

这已经不是：

```text
Agent 完成任务
```

层面的问题了。

而是：

```text
Harness developer
    ↓
run realistic tasks
    ↓
inspect traces
    ↓
compare with human judgment
    ↓
identify recurring failure pattern
    ↓
change prompt / criteria / tools / orchestration
    ↓
run again
```

Anthropic 在文章结尾其实把这个方法论总结得很明确：应该针对真实任务实验、阅读 trace，并根据观察结果持续调 Harness。

这和我们写普通软件很像：

```text
写代码
    ↓
跑测试
    ↓
看失败
    ↓
改代码
```

只是现在被调试的对象变成：

```text
Agent behavior
+
Harness policy
```

---

#### 一个适合面试的回答：Verifier 不是 Ground Truth，那为什么还值得做？

如果面试官追问：

> Evaluator 自己也会犯错，那为什么还要它？

可以回答：

> 因为我们不要求 Evaluator 成为绝对正确的 oracle，而是要求它相对于 Generator 的 self-evaluation 提供更独立、更可调的 failure signal。关键是把 Evaluator 当成 Harness 中另一个需要 Eval 的组件：通过 hard criteria、真实环境、few-shot calibration、trace inspection 和人工 failure examples 去不断提高它的 precision 和 recall，而不是无条件相信它的最终 PASS。

再压成一句：

```text
Verifier 不是 Truth。

Verifier 是一个
可以被工程化调优的
external critic。
```

---

#### 为什么这比“再加一个 Reviewer Agent”更重要？

因为：

```text
增加 Agent 数量
```

并不会自动增加：

```text
verification quality
```

如果你开：

```text
Evaluator A
Evaluator B
Evaluator C
```

但它们都：

```text
只测 Happy Path
都倾向于宽容
都使用同一套模糊 criteria
```

那只是：

```text
三份相似的宽松意见
```

真正提高质量的是：

```text
更好的 observation
更好的 criteria
更好的 coverage strategy
更好的 judgment calibration
```

所以 Multi-Agent 的数量始终不是主角。

**角色与反馈设计才是。**

---

#### Macro 5 小结：从自评到可校准的外部验证

现在可以把三节完整连起来。

##### 5.1 为什么不能自己宣布完成？

```text
Generator
    ↓
共享实现轨迹
    ↓
self-evaluation bias
```

解决：

```text
separate evaluator
```

---

##### 5.2 为什么 Evaluator 要看真实系统？

```text
只读代码
    ↓
只能预测“应该工作”
```

解决：

```text
grounded verification
UI / API / DB / runtime observation
```

---

##### 5.3 为什么还要调 Evaluator？

```text
有真实证据
    ↓
仍可能测试浅
仍可能合理化失败
```

解决：

```text
verification calibration
criteria
threshold
few-shot
trace inspection
prompt iteration
```

最终变成：

```text
Generator
    ↓
Artifact
    ↓
Grounded Evaluator
    ↓
Strict Criteria
    ↓
Failure Evidence
    ↓
Generator Revision
```

这样：

```text
DONE
```

才逐渐从：

```text
模型的一句自然语言声明
```

变成：

```text
由外部证据支持的
Harness state transition
```

---

##### 再接回父文的五个动词

Macro 5 最终把：

```text
观察
+
修正
```

两件事真正推到了系统级。

```text
观察
```

不是：

```text
模型看看自己写了什么
```

而是：

```text
Verifier 去触碰真实系统，
得到独立 observation。
```

```text
修正
```

也不是：

```text
再想一次
```

而是：

```text
把具体 failure evidence
送回 Generator，
迫使实现发生变化。
```

于是：

```text
找到
行动
观察
约束
修正
```

这五个动词到这里已经不再是抽象口号。

---

#### 源码与证据边界

Anthropic 的文章能够直接支持这些结论：

* 早期 QA Agent 会发现真实问题，却随后把问题合理化为“不严重”，最终仍然批准；
* Evaluator 也倾向于 superficial testing，不主动探测 edge cases，因此深层 Bug 会漏掉；
* Anthropic 的调试方法是阅读 Evaluator trace，找出其判断与人工判断不一致的具体案例，再更新 QA prompt，连续迭代多轮；
* 即使调优以后，仍然存在布局问题、交互不自然以及未深入测试的嵌套功能 Bug，说明 verifier 仍有明显 headroom；
* frontend evaluator 还通过 few-shot score breakdown 做过 calibration，以减少 judgment drift；
* full-stack Harness 对每个 criterion 设置 hard threshold，任一关键项低于要求就 fail，而不是用整体印象覆盖局部关键失败。


到这里，我们已经看到三个不同角色：

```text
Planner
Generator
Evaluator
```

很容易下一步就得出一个过于简单的结论：

> 所以高级 Harness 就是 Multi-Agent，多开几个 Claude 分工。

但这其实又会理解错。

真正的问题不是：

```text
有几个 Agent？
```

而是：

```text
为什么这些 Agent
需要拥有不同的信息、
不同目标、
不同工具和不同职责？
```

更重要的是：

Claude Code 自己源码里的 `AgentTool` 确实提供了：

```text
subagent
background execution
agent type
model choice
worktree isolation
```

之类的运行时 primitive。

但这**不能反向证明**：

```text
Claude Code 内部固定实现了
Planner → Generator → Evaluator
```

Anthropic 那套三 Agent 架构是建立在 Claude Agent SDK 上的实验 Harness。

Claude Code 的源码能证明的，是它具备构建 delegation / subagent execution 的底层能力。

所以下一个 Macro 要非常注意这个边界：
