---
schema: bubblevan/v1
id: blog-20260922-ftec5660-parallelization-reflection
content_kind: blog
title: "FTEC5660：Parallelization、Reflection 与课程项目规则"
date: 2026-09-22
updated: 2026-09-22
status: draft
visibility: public
summary: "我根据第三节课录音，整理 FTEC5660 的并行化、Reflection、Tutorial 实现、作业提交规则和课程项目安排。"
topics: [FTEC5660, Agentic AI, Parallelization, Reflection, LangChain, FinTech]
projects: []
aliases: []
authors: [bubblevan]
---

今天这节 FTEC5660 不只是讲了新的设计模式。老师先回顾了前两周的 chaining 和 routing，然后把课程考核、Hackathon、Individual Project 和 Group Project 的关系重新解释了一遍，最后由 tutorial 演示 parallel chain 和 reflection loop。

这份录音的自动转写有不少明显错误，所以我只保留能和上下文对应上的内容；像 “Python5”、某些模型名字和最后一句下周安排，都不能直接当成正式通知。

## 1. 先把课程安排和作业规则说清楚

### 1.1 老师希望问题公开回答

老师解释了为什么普通邮件通常不会得到回复：他希望所有同学获得对称的信息。如果每个人私下问、老师分别回答，其他人就不知道同一个问题的答案。

所以之后遇到课程安排问题，比较稳妥的顺序是：

1. 先发到 Slido；
2. 或者在课堂上直接问；
3. 等老师在课堂上统一回答。

除非是非常特殊的情况，否则不要只发邮件等待私人回复。

### 1.2 五次 Homework 的两个提交入口

老师明确说课程有 **5 次 Homework**。Blackboard 上可能出现两个提交项，并不代表只有两次作业，而是学校要求保留学生的提交记录。

从录音中能确定的分工是：

- 用于 grading 的入口：提交 GitHub repository 或 GitHub link，方便助教下载代码并批改；
- 用于 records 的入口：上传 Python 文件，作为学校留档；
- 每次作业基本放在一个 item 里即可，通常一个 `.py` 文件就够。

老师说 Blackboard 没有方便的 API 让他们批量下载作业，所以批改部分需要通过 GitHub 完成。这里的 GitHub 不只是额外展示，而是老师实际批改流程的一部分。

### 1.3 README 可以变成简历资产

老师还提醒，不要只把作业当成一次性的提交。代码会公开放在 GitHub 上，因此 README 写得越完整，越能说明自己的工程能力。

我应该至少写清楚：

- 这个项目解决什么问题；
- 如何安装和运行；
- 输入输出是什么；
- 使用了哪些 Agent pattern；
- 如何测试；
- 有哪些结果和限制。

老师的意思不是 README 一定会被仔细评分，而是这些作业以后可以抽出来发展成独立项目，再加上 UI 或其他功能，成为求职时能展示的作品。

## 2. Hackathon、Individual Project 和 Group Project 不是一回事

### 2.1 Hackathon 至少参加一个

老师说 Hackathon 有两个选择：

- HACK4SDG / AI for SDG；
- ICBC Cup。

两个都参加也可以，但最低要求是参加其中一个。

老师本人不是这些比赛的组织者，所以课程要求并不是比赛方的规则，而是 FTEC5660 对学生参与实践活动的要求。

### 2.2 Hackathon 项目本身主要用于留档

提交 Hackathon 项目时，老师主要想确认我确实参加过这个活动。他不会按照 Hackathon 官方格式去重新评审整个比赛作品。

课程真正会读、会评分的是 reflection。录音中老师明确提到这一部分占 **15%**，它不是简单的“我参加了某比赛”的证明，而是要写我对项目的思考。

如果几个人参加了同一个 Hackathon：

- 可以提交同一个项目文件；
- 但每个人的 reflection 必须不同；
- 每个人应该写自己的贡献、判断和学习过程。

### 2.3 Group Project 是独立的 50% 项目

有人在 Slido 问三人项目是否就是 ICBC Cup，老师明确回答：两者是两个独立项目。

课程大纲里的 Group Project 另占总评 **50%**。它不能被简单理解成“把 ICBC Cup 的报名材料交上去就结束”。不过，Hackathon 项目可以继续发展为课程的 Group Project，只要后续体现出课程要求的 Agentic AI 设计、实现和评估。

### 2.4 三个人是最理想的组队规模

老师补充说：

- 不能一个人完成 Group Project；
- 两个人可以；
- 三个人最好；
- 不能四个人。

我现在和两个队友组成三人组，人数上正好符合老师认为最合适的形式，但具体分工还没有确定。

## 3. 12 月 8 日的 Poster–Oral examination

### 3.1 三个人都要站在海报前

Group Project 最后一天是 12 月 8 日的 poster / oral examination。老师描述的形式是：

1. 每组准备一个项目海报；
2. 三个人一起站在海报前；
3. 考官到各组提问；
4. 每个人都应该能够解释项目。

老师当时说海报尺寸大概是 A0 或 A1，但语气并不是最终确认，所以具体尺寸和模板还要看 Blackboard。

### 3.2 考官会追问技术决策

问题不会只停留在“你们项目做了什么”，而可能继续追问：

- 为什么做这个项目？
- 你们具体是怎么做的？
- 为什么用这个组件？
- 为什么调用这个 API？
- 为什么要搜索互联网？
- 为什么使用 RAG？
- 这是最优的实现方式吗？

这意味着三个人不能把项目切成完全隔离的三块，然后只熟悉自己写的部分。即使最后按模块分工，也需要理解整体架构、关键取舍和实验结果。

## 4. 从 Agent 黑盒到工程优化

### 4.1 Agent 是一个需要被设计的黑盒

老师把 Agentic AI 系统先画成一个黑盒：

```text
User Input → Agentic System → Output
```

工程师要做的不是只调用一个模型，而是设计黑盒内部的结构。里面可以放：

- 多个顺序执行的步骤；
- 条件路由；
- 并行分支；
- 外部工具；
- 反思和修改循环；
- 多个 Agent 的协作。

Chaining、Routing、Parallelization 和 Reflection，其实就是搭建这个黑盒的几种基本 Lego brick。

### 4.2 准确率不是唯一目标

老师把 Agent 系统的工程目标讲成多指标问题。至少需要同时考虑：

- accuracy：用户的任务是否真正完成；
- latency：从用户按下提交到收到答案需要多久；
- token / API cost：运行一次要花多少钱；
- development cost：系统要投入多少开发和维护工作；
- privacy：数据是否可以发送给外部服务；
- scalability：用户增加后成本如何变化。

成本还可以分为 fixed cost 和 variable cost。自己搭建模型或 Agent 的初始开发成本较高，但长期运行可能更可控；直接使用商业服务开发成本低，却可能随着用户数和 token 数快速增加。

因此工程师不应该只展示一个“最高准确率”的版本，而应该尝试多种架构、模型和参数，画出 accuracy-cost-latency 的 trade-off，并寻找 frontier，也就是没有明显被其他方案全面超过的方案集合。

### 4.3 Reproducibility homework 要测试系统敏感性

老师把这个工程视角和 reproducibility homework 联系起来。论文或 GitHub 可能给出一个看起来很好的结果，但我需要对系统做轻微扰动，例如：

- 更换 language model；
- 修改 search depth；
- 更换某个 Agent 组件；
- 改变重要参数；
- 观察 accuracy、cost 和 latency 如何变化。

老师举了去年的例子：原论文把 search depth 设置为 1，学生只把它改成 2，模型就不再工作，准确率变成 0。

这个作业不是简单重跑论文，而是在问：

> 论文里的结果到底依赖哪些组件和超参数？

## 5. Parallelization：把独立工作同时做完

### 5.1 为什么需要并行化

如果几个任务互相独立，顺序执行会产生不必要的等待。例如三个步骤分别需要 10 秒、5 秒和 3 秒：

```text
Sequential: 10 + 5 + 3 = 18 seconds
```

如果它们可以同时执行：

```text
Parallel: max(10, 5, 3) = 10 seconds
```

所以 Parallelization 的核心规则是：

> 先识别独立子任务，再并发执行，最后同步并汇总。

### 5.2 Synchronizer 和 Aggregator

并行不是把结果丢出去就结束了。所有分支完成后，需要：

1. synchronizer 等待所有独立任务；
2. aggregator 收集并合并结果；
3. synthesis chain 把结果变成用户最终看到的回答。

这也是为什么并行化的总响应时间通常接近最慢分支，而不是所有分支时间之和。

### 5.3 并行化的收益和代价

收益是降低 latency，尤其适合等待外部 API 或数据库的任务。

代价是：

- 同时调用多个模型或 API，token 成本可能增加；
- 并发日志更难看懂；
- 错误处理和重试更复杂；
- 最后必须等待所有分支；
- 如果任务实际上相互依赖，并行会得到错误结果。

老师举到的应用包括：

- 同时搜索多个网站；
- 同时分析多个市场；
- 同时查询航班、酒店和用户资格；
- 同时做多个数据分析或可视化；
- 同时检查邮件和日历；
- 同时处理文字、图片和语音。

### 5.4 Tutorial：两个独立解释和航班改签

第一个 tutorial 示例把同一个问题同时生成两种答案：两句话的简短解释，以及带公式或正式定义的 formal explanation。并行链最后返回一个 dictionary：

```python
{
    "concise_answer": "...",
    "formal_answer": "...",
}
```

第二个示例是航空公司改签。用户想把航班从香港改到 Santiago，系统需要同时检查：

- 目标航班是否有空位；
- 用户是否有资格改签。

这两个查询互不依赖，所以可以放进 `RunnableParallel`。两个分支完成后，synthesis chain 再生成一条短的客户回复，说明航班可用性、用户资格、费用，并询问是否继续。

老师展示了并行版本比顺序版本更快的示例，但重点不是记住某个固定秒数，而是理解：只有真正独立的工作才适合并行。

## 6. Reflection：让 Agent 回头检查自己的输出

### 6.1 基本结构

Reflection 是这节课另一个重点。它和普通的从左向右执行不同，会把输出送回一个 critic / reflector：

```text
Generator → Output → Reviewer
                         ↓
                 revise / regenerate
                         ↓
                    New Output
```

完整过程是：

1. Generator 生成初始结果；
2. Reviewer 检查结果是否满足要求；
3. Reviewer 指出错误和改进方向；
4. Reviser 根据反馈修改；
5. 再次审查；
6. 通过或达到最大迭代次数后停止。

### 6.2 Reviewer 不能只说对或错

一个有用的 Reviewer 至少应该回答两个问题：

1. 结果是否正确？
2. 如果不正确，具体应该怎么改？

Reviewer 需要根据任务给出检查标准，例如 correctness、edge cases、numerical precision、test compatibility，以及是否满足用户的全部限制。

### 6.3 Self-reflection 和不同模型的 Reflection

如果 Generator 和 Reviewer 用同一个模型，这是 self-reflection。如果使用不同模型，则可能减少共同偏差，但不代表第二个模型一定更可靠。

强 Reflector 通常更有机会发现问题，但成本和延迟更高；弱 Reflector 更便宜，却可能误判一个本来正确的答案。因此系统的最终 accuracy 取决于 Generator、Reflector、Prompt 和 Refinement strategy 的组合。

### 6.4 Reflection 自己也会引入错误

老师强调了一个容易忽略的风险：初始答案可能已经正确，但 Reviewer 误判为错误，系统就会把正确答案改坏。

所以需要评估：

- Reviewer 是否真的能识别错误；
- Reviewer 的误报率是多少；
- 重写后的答案是否比原答案更好；
- 额外 token 和 latency 是否值得。

### 6.5 设置最大迭代次数并升级给人

Reflection 不能无限循环。老师建议设置最大迭代次数，例如三次左右。如果多轮后仍然无法解决，就应该停止消耗 token，返回无法处理，之后再接入 Human-in-the-loop 进行人工处理。

## 7. Tutorial：用 Reflection 修正 Python 代码

### 7.1 三个 prompt

Tutorial 做的是一个代码生成 Agent，里面有三个角色：

1. Generator：根据用户任务写初始代码；
2. Reviewer：检查代码；
3. Reviser：根据 review 修改代码。

Reviewer 的终止触发器是类似：

```text
The code is perfect.
```

如果 Reviewer 输出这个信号，循环终止；否则把当前代码和 review 交给 Reviser，生成下一版代码。

### 7.2 简单任务：计算阶乘

第一个任务是写 Python function 计算 `n!`。由于这是模型很熟悉的任务，初始代码很可能已经满足要求，Reviewer 直接返回通过，循环只执行一轮。

### 7.3 困难任务：计算 `n!` 的位数

第二个任务要求计算 `n!` 有多少位，并且加入了严格限制：`n` 最大为 50 million、不能为负数、需要 constant time、需要 constant memory，如果做不到就返回 `-1`。

模型可能用 Stirling approximation 估计 `log(n!)`，再通过：

```text
digits(n!) = floor(log10(n!)) + 1
```

得到位数。这个方案数学上看起来合理，也能通过很多小规模测试，但在很大的输入附近，浮点数精度可能让结果跨过 floor 的边界，最终少一位或多一位。

老师用这个例子说明：模型输出“看起来很对”并不代表满足所有硬约束。Reviewer 必须检查数值精度、边界输入和复杂度要求。

最终的判断是：如果要求对指定范围内的所有输入都精确、同时又要求 constant time 和 constant memory，那么这个任务可能本身不可实现；正确行为不是继续编造算法，而是按照用户规定返回 `-1`。

## 8. 这节课对 AgentRisk 的启发

我之前想做的金融 Agent 自动化安全测试，正好可以把今天学的 pattern 组合起来：

```text
Routing
    ↓
按风险类型选择测试流程
    ↓
Parallelization
    ↓
同时检查权限、隐私、工具调用和业务状态
    ↓
Reflection
    ↓
审查 Agent 行为、失败原因和测试证据
    ↓
Human-in-the-loop
    ↓
高风险结果交给人工审批
```

例如“临时贷记已经入账，但 API 返回超时”的测试任务：

- 一个分支检查审批参数是否匹配；
- 一个分支检查账本最终状态；
- 一个分支检查是否使用了重复的幂等键；
- 最后由审查器判断是否发生重复入账。

这比单纯让一个模型回答“这个 Agent 安全吗”更符合课程的工程方法：把问题拆成可执行步骤，再用日志、状态和规则判断结果。

## 9. 录音与课程大纲之间的差异

有几处我不会直接把录音转写当成最终通知：

1. 课程大纲写 Individual Project 2 截止为 **11 月 11 日午夜**，老师口头提到的日期听起来像 **11 月 13 日**；
2. 海报尺寸听起来是 A0 或 A1，但老师说的是大概尺寸；
3. 录音最后疑似提到下一周进入 Tool Use 和 MCP，但课程大纲的 Week 3 写的是 Planning 和 Goal Setting；
4. 自动转写中的模型名、Hackathon 名称和文件格式有明显听写错误。

这些内容最后都应该以 Blackboard 上老师发布的 assignment、project brief 和最新课程通知为准。

## 10. 我接下来要做什么

- [ ] 在 Blackboard 确认 HW1 的两个提交入口：GitHub link 和 Python 文件。
- [ ] 把自己的 FTEC5660 作业统一放进一个 GitHub repository，并先写好 README。
- [ ] 和两个队友确认 Group Project 的具体分工以及 proposal 要求。
- [ ] 确认 Individual Project 2 的最终日期和正式说明。
- [ ] 用 `RunnableParallel` 复现“简短解释 + 正式解释”的 tutorial。
- [ ] 用 Generator–Reviewer–Reviser 结构复现 Reflection coding example。
- [ ] 把 AgentRisk 的重复入账测试设计成一个真正有状态、可审计的实验。

