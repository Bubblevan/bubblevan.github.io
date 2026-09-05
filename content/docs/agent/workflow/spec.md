https://github.com/Fission-AI/OpenSpec
https://github.com/github/spec-kit
https://github.com/obra/superpowers

这三个项目都聚焦于 **“规格驱动开发”（Spec-Driven Development）**，旨在规范AI编程助手的开发流程，但它们在个人知识库中的定位可以有所区分。

简单来说，我的建议是：
*   **`github/spec-kit`** 和 **`Fission-AI/OpenSpec`**：更适合放在 **`agent orchestration`** 部分。
*   **`obra/superpowers`**：则更适合放在 **`skills`** 部分。

## 1. 📝 各项目简介与归类分析

1.  **`github/spec-kit` (agent orchestration)**
    *   **简介**：这是GitHub官方推出的工具包，提供了一套完整的、可执行的**规格驱动开发流程**。它通过 `/speckit.*` 等一系列命令，引导用户从定义项目原则 (`/speckit.constitution`)、创建规格 (`/speckit.specify`)，到制定计划 (`/speckit.plan`) 和最终执行 (`/speckit.implement`)。
    *   **归类理由**：它更像一个**工作流编排器**。它定义了一个从“想法”到“代码”的完整、结构化的**开发流程**，并提供了命令行工具来驱动这个流程的每个阶段。这符合“orchestration”的定义，即管理和协调一个复杂过程的执行。

2.  **`Fission-AI/OpenSpec` (agent orchestration)**
    *   **简介**：这是一个同样强调规格驱动的开源框架。其核心工作流围绕 `/opsx:propose`、`/opsx:apply` 和 `/opsx:archive` 等命令展开，强调在编写代码前通过“提案（proposal）”和“任务（tasks）”来对齐需求。
    *   **归类理由**：与 `spec-kit` 类似，`OpenSpec` 也定义了一个**端到端的开发流程**。它通过一系列命令引导用户完成从探索、提案到实施和归档的完整周期。因此，它同样更适合归类为一种“orchestration”工具。

3.  **`obra/superpowers` (skills)**
    *   **简介**：这是一个为AI编程代理设计的**技能框架和软件开发方法论**。它提供了一套可组合的“技能（skills）”，如 `brainstorming`、`test-driven-development`、`systematic-debugging` 等。
    *   **归类理由**：它更像一个**技能库或方法论集合**。其核心是提供一系列**独立的、可复用的“技能”**（如TDD、调试、代码审查等），代理可以根据需要调用这些技能来执行特定任务。虽然它也有一个“subagent-driven-development”的流程，但其本质是提供构建模块（技能），而不是编排一个固定的、线性的流程。因此，它更适合放入 `skills` 部分。

## 2. 💎 总结

| 项目 | 核心定位 | 推荐归类 |
| :--- | :--- | :--- |
| **`github/spec-kit`** | 端到端的开发流程编排工具 | **`agent orchestration`** |
| **`Fission-AI/OpenSpec`** | 端到端的开发流程编排框架 | **`agent orchestration`** |
| **`obra/superpowers`** | 可复用的技能与开发方法论集合 | **`skills`** |

简单来说，如果你的知识库是围绕“如何组织和引导AI代理完成复杂任务”来构建的，那么 `spec-kit` 和 `OpenSpec` 是很好的流程案例。而 `Superpowers` 则更像是一本“技能手册”，可以为你的代理提供各种具体的“做事方法”。

---
title: "从 Vibe Coding 到 SDD：我为什么不再直接让 Coding Agent 开始写代码"
weight: 2
---

我以前理解的“工程化 Vibe Coding”，大致是一条朴素流程：

~~~
PRD → TRD → 拆成若干任务 → Agent 逐项实现 → Test + Diff
~~~

这已经比“帮我实现 XX”强得多：目标被说出来，技术路线有了落点，工作跨度受到控制，最后还有一次检查。

但后来我意识到，真正关键的不是 PRD、TRD 或“六到八个任务”这些名字和数字，而是把原先藏在人脑里的意图、约束与完成定义，变成 Agent 能阅读、实施和验证的显式契约。

这就是我现在理解的 Spec-Driven Development，简称 SDD。它不是“在写代码前多写几个 Markdown”，也不是某个 CLI 的命令教程；它是一种先定义正确性、再组织实现的开发方式。

本文以 OpenSpec、GitHub Spec Kit 和我原有的 PRD → TRD → Task 工作流为线索，讨论：

1. 为什么直接让 Coding Agent 开始实现会失控；
2. Spec、Plan、Tasks 与验证分别负责什么；
3. OpenSpec 与 Spec Kit 各自给了什么启发；
4. Spec 写清楚后，哪些问题应当留给上层的 orchestration。

这是一篇任务定义层的笔记。它只讨论“Agent 应交付什么、怎样证明交付了”；任务调度、独立 workspace、CI 回流、失败恢复与多 Agent 协作，属于相邻的编排问题。

## Macro 1：我原来的 Vibe Coding 为什么有效，又为什么还不够

### Beat 1.1：Agent 最危险的输入，是未经重建的隐性意图

一句自然语言需求经常同时省略了目标、边界、历史决定和验收方式。例如：

> 给设置页加一个通知开关。

这句话没有说明：

* 开关控制的是邮件、站内消息，还是两者；
* 默认值是什么，已有用户怎样迁移；
* 设置应立即持久化，还是离开页面时提交；
* 哪些用户不可见，权限从哪里判断；
* 失败时 UI 怎样反馈；
* 哪些既有行为绝不能改变；
* 修改后，谁用什么证据判断“做完了”。

人类团队常把这些信息散在口头交流、旧 issue、代码惯例和某位同事的记忆里。Agent 看不到这些条件时，并不是“故意不听需求”，而是在用它能观察到的局部证据重建需求；它会选择看似合理、却未必是团队真正想要的实现。

我把这种补全过程称为 implicit-intent reconstruction：执行者必须从模糊指令、仓库现状和零散上下文里，猜出完整任务。猜对时很高效；猜错时，错误往往在代码写完、测试变绿之后才暴露。

PRD 与 TRD 的价值正在于减少这种猜测。前者让“为什么做、为谁做、边界在哪里”可见，后者让关键约束、模块关系和选择理由可见。但它们不应成为两个万能大文件：不同信息应以最适合被执行和验证的形式出现。

### Beat 1.2：任务的边界来自可独立验证，而不是固定数量

我曾经喜欢“拆成六到八个任务”这个经验规则。它对避免一次让 Agent 大改整站确实有帮助，但它抓错了重点：任务数不是质量指标。

一个适合交给 Agent 的任务，至少应满足：

* bounded：范围有明确起点和终点；
* independently executable：前置条件被声明，不依赖大量未写出的工作；
* independently verifiable：完成后能以测试、行为或运行信号判断；
* dependency-aware：先后关系明确，而不是靠执行者碰运气。

因此，“Task 3：实现 Context 模块”并不合格。它没有范围、依赖与完成定义。相同目标可以改写为：

> 实现 Required Context Preservation。  
> 完成条件：
> - required items 不被静默丢弃；
> - hard budget 超限时明确失败；
> - optional items 可以按策略裁剪；
> - selector 的测试全部通过。

这并不是把任务写得更长，而是把“实现了什么”改成“什么事实必须成立”。在 Hi-Agent 的 Context Budget、Selector 和 Compiler 实践里，我越来越确信：Agent 最适合接收的不是一个模块名，而是一个带边界和证据的可验证变化。

## Macro 2：SDD 要解决的不是文档数量，而是正确性的链路

### Beat 2.1：Proposal、Spec、Design 和 Tasks 不该互相代替

很多流程把背景、接口、实现选择与待办塞进一份“需求文档”。这样短期写起来省事，长期却很难判断一条内容到底是意图、约束、设计决定，还是实现顺序。

更稳定的分工是：

| 工件 | 它回答的问题 | 不负责什么 |
| --- | --- | --- |
| Proposal | 为什么值得做，变更范围是什么 | 不给出全部实现细节 |
| Spec | 什么行为必须成立，什么不能发生 | 不决定代码应落在哪一行 |
| Design / Plan | 在当前仓库中怎样实现，取舍是什么 | 不重新定义产品正确性 |
| Tasks | 谁先做什么，依赖如何排列 | 不以清单代替验收 |
| Verification | 用什么证据证明已达成 | 不反过来替产品决定目标 |

这就是 artifact-responsibility boundary：工件不是按篇幅区分，而是按它们负责的决策不同来区分。

例如，“支持导出 CSV”只是目标；“用户可以导出自己有权限访问的记录，导出请求不得阻塞页面，失败时可见错误提示”才接近 Spec；“使用现有异步 job 队列、复用 ExportService、新增审计日志”属于 Design；“先扩展授权查询，再实现 job，再补端到端测试”才是 Tasks。

### Beat 2.2：验收标准应写成可观察的行为场景

“实现导出”“支持深色模式”“优化启动速度”都不是可验证的要求。它们描述方向，但没有给出观察点。

把要求转成可执行行为，可以使用一个简单场景：

~~~
Given：谁处于什么前置状态
When：执行什么动作
Then：可观察到什么结果
And：哪些负向约束仍然成立
~~~

例如：

> Given 管理员在筛选后的用户列表页；  
> When 点击“导出 CSV”；  
> Then 页面立即显示已开始导出的状态，并在后台创建导出任务；  
> And 导出的记录只包含该管理员有权限访问的数据；  
> And 任务失败时页面可见失败原因，且不会生成部分下载文件。

这就是 observable-behavior scenario。它不要求每个 Spec 都写成 BDD 测试脚本，但要求读者能回答：我在哪里、对什么输入、通过什么信号，判断要求成立？

当行为无法被观察时，Agent 的“Done”只能意味着“我改过相关代码”。这是 Coding Agent 最常见的完成错觉。

### Beat 2.3：从意图到证据必须存在可追踪的链路

SDD 最重要的结构不是一堆文件，而是一条可追踪链：

~~~
Intent → Requirement → Acceptance criteria → Design decision
→ Task → Implementation → Verification evidence
~~~

其中任何一环断掉，都会产生不同的问题：

| 断点 | 常见后果 |
| --- | --- |
| Intent → Requirement | 做得很完整，但解决了错误问题 |
| Requirement → Acceptance | “完成”只能凭感觉判断 |
| Acceptance → Design | 实现路线无法解释为何足以满足要求 |
| Design → Tasks | Agent 不知道先后顺序和工作边界 |
| Task → Evidence | 任务勾选完成，却没有证明结果 |

这条 requirement-traceability chain 不要求每个小改动都有重型文档；它要求风险较高、跨度较大的变更，能够回答“这一行实现服务哪项要求”“这个验收条件由什么证据支持”。

## Macro 3：OpenSpec 给我的启发——把变更当成有生命周期的 Delta

### Beat 3.1：先区分 Base Spec 与 Change Delta

OpenSpec 的一个关键启发，是不要把每一次需求都写成对整个系统的重新描述。

稳定存在的能力、规则与边界属于 Base Spec；某次需求带来的新增、修改或移除，则作为 Change Delta 提出和审查。这样做有两个好处：

* 读者能看到“这次到底改变了什么”，不必在大文档中寻找差异；
* 已成立的系统约束不会因为一次变更被静默改写。

例如，Base Spec 可以说“导出只能返回调用者有权限读取的数据”；新的 Change Delta 可以说“允许管理员选择 JSON 或 CSV 格式，同时审计每次导出”。后者不需要复制前者，但必须明确是否影响它。

### Beat 3.2：一次变更不是单页文档，而是一组有关联的工件

OpenSpec 的流程围绕 proposal、spec、design、tasks、apply、verify 与 archive 展开。重要的不是逐字记住命令，而是理解这是一张变更工件图：

~~~
发现需求 → Proposal：为何改变、影响哪里
→ Spec：新增或改变的行为
→ Design：实现选择与风险
→ Tasks：可执行的顺序
→ Apply：实施
→ Verify：获得证据
→ Archive：把已完成变化纳入历史
~~~

Proposal 不等于 Spec，Spec 不等于 Design，Tasks 也不等于验收。每个工件都保留一种未来仍有价值的上下文。

尤其 archive 很重要。完成的变更不应继续像“当前待办”一样影响 Agent，但其中的决策理由也不应被删除。归档让系统同时拥有清晰的当前状态和可追溯的历史。

### Beat 3.3：OpenSpec 最可信的案例，是它对自身流程的 dogfooding

学习一个 SDD 工具时，我不太关心“它能不能生成 Markdown”，更关心它是否把自身的变更也放进同样的流程。OpenSpec 的仓库以变更工件来组织演化，这比一份宣言更有说服力。

当然，一个工具仓库的流程适合自身，不代表所有项目都应完整照搬。它至少证明了一件值得学习的事：

> 当变更被当成一等对象时，需求、设计、任务和验证可以拥有清楚连接，而不是散落在聊天记录、PR 描述和个人记忆中。

## Macro 4：Spec Kit 给我的启发——把质量门槛放到实现之前

### Beat 4.1：Constitution 是项目级不变量，不是又一份需求

GitHub Spec Kit 的工作流包含 constitution、specify、clarify、plan、tasks、analyze、implement 等阶段。它最值得借鉴的部分，是把 Constitution 放在单个需求之前。

Constitution 适合记录长期稳定、跨任务生效的原则，例如：

* 外部输入必须在系统边界解析；
* 任何功能必须有可运行的验证方式；
* 隐私数据不得出现在日志与测试 fixture 中；
* 依赖方向不能从领域层指向 UI；
* 改动数据库结构必须包含迁移与回滚策略。

这些不是某次功能的验收，而是项目持续成立的约束。我把它称为 project constitution。

它不应膨胀成百科全书。只对某个领域、目录或临时迁移有效的规则，应放在局部规范、设计文档或执行计划中，否则 Constitution 很快会退化为另一个巨型 AGENTS.md。

### Beat 4.2：Clarify 与 Analyze 是实现前的质量门

Spec Kit 的 clarify 提醒我：含糊不应该等到 Agent 已经写出一大段代码才被发现。实施前先暴露不确定项，可以避免“模型替你作了产品决定”。

典型澄清包括：

* 谁是目标用户，权限边界是什么？
* 默认行为和失败行为分别是什么？
* 哪些旧接口必须兼容？
* 需要哪些非功能约束，例如延迟、审计或无障碍？
* 哪些边界条件会导致要求不成立？

analyze 则更接近一致性检查：Spec 的目标、Plan 的路线、Tasks 的拆分有没有遗漏或矛盾？

两者共同形成 pre-implementation quality gates。它们不保证需求永远正确，但将关键不确定性从代码之后移动到代码之前。

### Beat 4.3：实现之后仍要回到收敛，而不是只看代码生成

SDD 的终点不是 Agent 生成一份看起来合理的 diff，而是让实际状态收敛到 Spec 所描述的状态。

这个过程至少包含：

1. 实现是否覆盖每项验收；
2. 测试、静态检查或实际运行是否提供相应证据；
3. 已知偏差是否被明确记录，而非隐藏在“以后再修”；
4. 实现中出现的新事实，是否要求更新 Spec 或 Plan。

这就是 post-implementation convergence。当现实与 Spec 不一致时，不能默认“改代码直到测试绿”；有时是实现错误，有时是原始要求遗漏，有时是设计选择已经不成立。SDD 的价值在于让这种偏差可见、可讨论、可回写。

## Macro 5：我不会机械照搬任何一种 SDD

### Beat 5.1：SDD 应按风险进入，而不是每个改动都走完整流程

OpenSpec 和 Spec Kit 是很好的脚手架，但都不意味着每次改文案、修 typo 或升级一个小依赖都要写 Proposal、Design、Task Graph。

更合理的是 adaptive-spec entry：先按变更风险决定需要哪些工件。

| 变更类型 | 合理的最低工件 |
| --- | --- |
| 明确、可逆、局部小修 | 任务描述 + 验证命令 |
| 单模块新能力 | 行为 Spec + Tasks + 测试证据 |
| 跨模块或有用户行为影响 | Proposal + Spec + Design + Tasks + 验证 |
| 架构、安全、数据迁移 | Constitution / ADR + 完整 Spec、Plan、回滚与观测方案 |

判断风险时，不只看改动行数。一个十行的权限修改可能比几百行纯内部重构更需要明确 Spec；一个 UI 改动若影响付款、隐私或数据删除，也不应被当成“小需求”。

## Macro 6：我最终形成的 Lightweight SDD

### Beat 6.1：用风险，而不是工具名称，决定流程重量

我的工作流不再从“这次用 OpenSpec 还是 Spec Kit”开始，而从三个问题开始：

1. 这次变更是否会改变用户可见行为、数据或安全边界？
2. 是否存在多个合理实现，且取舍会影响后续维护？
3. 完成后能否得到直接、可信的证据？

如果三个答案都很简单，写一个短任务和验证即可；如果任意一个答案复杂，就增加对应工件。这样 SDD 不是仪式化流水线，而是把更多精力放在真正危险的未知处。

### Beat 6.2：Spec 中必须区分事实、假设、决定与未决问题

一份看似完整的 Spec 经常混入四种性质不同的句子：

| 句子类型 | 例子 | 应如何处理 |
| --- | --- | --- |
| Fact | 当前 API 返回分页结果 | 链接代码、文档或可运行证据 |
| Assumption | 首期用户量不会很高 | 标注为假设，说明失效条件 |
| Decision | 导出改为异步 job | 记录理由与替代方案 |
| Open question | 失败的导出文件是否保留 | 在实现前澄清，不能悄悄假定 |

我把这种区分称为 claim-state。它能降低一个关键风险：Agent 把暂时猜测读成硬约束，把旧事实读成当前真相，或者把尚未决定的问题自行决定。

在多人协作、长周期任务和历史资料很多的仓库里，标注状态比写得自信更重要。一个诚实的“尚未决定”通常比一个未经证实的“必须如此”更能保护后续实现。

### Beat 6.3：把博客写作本身当成一次可验证的 SDD 实验

这篇文章也是一个小型实验。与其把 OpenSpec、Spec Kit 和 Symphony 逐条复述，不如让每一节都满足同样要求：

* 引入的概念有明确边界；
* 观点能回到一手资料或我自己的项目实践；
* 推论与事实被区分；
* 示例说明它会怎样改变一次真实任务；
* 读者能看出它不负责什么。

Macro 是一段完整问题的学习目标；Beat 是一个可以独立阅读、独立质疑的结论单元。它不是为了制造章节数量，而是为了让文章自己拥有从问题、概念、案例到边界的可追踪链路。

## Macro 7：SDD 的终点，也是 orchestration 的起点

### Beat 7.1：Symphony 同时证明了 Spec 的力量和 Spec 的边界

到这里可以用一句直接的话概括两者的关系：

> Spec 规定编排器应该做什么，但不会替它运行。

这里有两个很容易混淆、但必须分开的“Spec”。

第一种是本篇讨论的任务 Spec：它面向 Coding Agent、Reviewer 与人类协作者，定义一次任务要交付的行为、范围、依赖、验收和证据。它回答“这个变更什么样才算正确”，但不负责调度谁来做、何时重试或在哪个 workspace 执行。

第二种是 OpenAI Symphony 使用的语言无关 SPEC.md：它面向 Symphony 的实现者，定义编排服务自身的外部行为与约束。语言无关不是“没有技术细节”，而是该行为契约不绑定某一种实现语言；多种实现若按同一 SPEC.md 做出不同理解，恰好会暴露规范里的歧义。

两者都在定义正确性，但面对的对象不同：

| 层次 | 主要对象 | 它要定义什么 | 它不负责什么 |
| --- | --- | --- | --- |
| 任务 Spec | Coding Agent 与 Reviewer | 功能行为、范围、验收、证据 | 领取任务、隔离环境、重试与恢复 |
| Symphony 的 SPEC.md | 编排系统实现者 | 编排服务应有的行为契约 | 实际运行服务、调度真实任务 |
| Orchestrator runtime | 任务系统与 Agent 执行环境 | 任务生命周期如何推进 | 重新发明任务的产品正确性 |

Symphony 将 issue tracker 作为控制面，把合格 issue 映射到隔离的 agent workspace，并让任务在生命周期里持续推进。这个例子正好说明：即使任务 Spec 已经把“要做什么”写清，运行时仍然需要有人处理“从哪里领取任务、如何隔离、何时把结果送入 Review、失败怎样恢复”。

因此，本页在这里应当停止。它可以为任务留下一个清晰接口：

~~~
任务目标 → 行为 Spec → 设计与任务 → 验证证据
~~~

但它不应继续把 Linear 控制面、workspace 生命周期、依赖 DAG、PR 回流、CI/review 反馈和多 Agent 调度塞进同一篇文章。它们不是 Spec 的附属命令，而是 orchestration 的运行时问题。

这个边界也避免另一种错误理解：好像只要写出完整 Spec，Agent 就自然拥有浏览器、日志、权限、可观察性、隔离环境和失败恢复能力。现实恰好相反。Spec 告诉 Agent 与编排器何为正确；Harness 和 orchestration 则提供产生、观察并验证那个结果的条件。

所以，本文不是 SDD 的“万物总论”，而是一份任务契约的学习笔记。上层的 orchestration 页面再讨论 Symphony 所揭示的长期运行工作流；本页保留在更具体、也更重要的问题上：

> 在 Agent 触碰代码之前，我们能否先把正确性说清楚，并在它完成后拿到足以相信的证据？

## 参考与延伸

* [OpenSpec](https://github.com/Fission-AI/OpenSpec)
* [GitHub Spec Kit](https://github.com/github/spec-kit)
* [OpenAI Symphony](https://openai.com/zh-Hans-CN/index/open-source-codex-orchestration-symphony/)
* [OpenAI Harness engineering](https://openai.com/index/harness-engineering/)
