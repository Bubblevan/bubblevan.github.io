---
schema: bubblevan/v1
id: blog-20260918-ftec5660-agentic-ai-for-fintech
content_kind: blog
title: "FTEC5660：Agentic AI for FinTech 课程大纲与错过的前两节课"
date: 2026-09-18
updated: 2026-09-18
status: draft
visibility: public
summary: "我根据 2026 年 9 月 7 日版本的课程大纲，补回 FTEC5660 前两节课的主题、课程路线、考核结构和关键截止日期。"
topics: [FTEC5660, Agentic AI, FinTech, CUHK, LLM Agents]
projects: []
aliases: []
authors: [bubblevan]
---

我相当于错过了 FTEC5660 的前两节课，现在拿到一份 2026 年 9 月 7 日修订的课程大纲，终于可以把这门课的真实路线补起来。系统里显示的课程名是 **Agentic AI for FinTech**，但大纲封面写的是 **Agentic AI for Business and FinTech**；从课程内容看，两者指的是同一门课。

## 1. 这门课到底在学什么

### 1.1 Agentic AI 和普通的 prompt-response 有什么不同

大纲给出的切入点很清楚：传统 AI 模型可以回答 prompt 或执行预定义任务，但 agentic AI 会把一次请求拆成一串连续动作。系统可以先规划，再调用工具、检查结果、继续下一步，也可以让多个 agent 协调完成一个共同目标。

我会把它理解成三层能力：

1. 不只生成一次回答，而是能够 chaining 一系列 action；
2. 不只完成固定流程，而是能够根据中间结果调整下一步；
3. 不只依赖一个模型，而是可以组织多个 agent、工具和外部信息源。

课程会把这些机制放到 business 和 fintech 场景中，包括 cryptocurrency / blockchain、financial analysis、portfolio management、customer service、human resources、business planning 和 operations。

### 1.2 课程希望我最后能做到什么

课程 learning outcomes 不是“会调用一个 agent framework”这么简单，而是要求我能够：

- 解释 reinforcement learning、language model 和 agentic system 背后的技术机制；
- 从真实 business / fintech 问题中抽象出适合 agent 解决的任务；
- 做出一个 minimal viable agentic system；
- 用多个指标评估和比较不同 agent architecture；
- 在资源受限的条件下完成部署。

所以它不是一门只讲 prompt engineering 的课，后面会逐步进入 system design、evaluation、resource constraint 和 deployment。

## 2. 我错过的前两节课

### 2.1 9 月 8 日：Introduction 与 Prompt Chaining

第一周讲 Pattern 0: Introduction 和 Pattern 1: Prompt chaining。也就是说，课程一开始就从 agent pattern 进入，而不是先花几周单独讲语言模型基础。

第一周的 homework 是注册 AI for SDG hackathon，报名链接写在课程大纲里，截止日期是 **9 月 14 日**。这个节点已经过去，我接下来需要直接去 Blackboard 看是否还有补报名或替代安排。

### 2.2 9 月 15 日：Routing、Parallelization 与 Reflection

第二周讲了三个 pattern：

- **Routing**：先判断输入属于哪一类，再把任务交给合适的路径或 agent；
- **Parallelization**：把可以同时完成的子任务并行分发，最后汇总结果；
- **Reflection**：让系统检查自己的中间结果，再决定是否修改或继续。

这一周已经发布 HW1。下一次课是 **9 月 22 日**，主题是 Pattern 5: Planning，以及 Pattern 6: Goal Setting and Monitoring。也就是说，我接下来要补的重点不是重新从 prompt 开始，而是把前面四个 pattern 和 planning 接起来。

## 3. 从现在到学期末的课程路线

| 日期 | 内容 | 作业或活动 |
| --- | --- | --- |
| 9 月 8 日 | Introduction；Prompt Chaining | AI for SDG hackathon registration，截止 9 月 14 日 |
| 9 月 15 日 | Routing；Parallelization；Reflection | HW1 released |
| 9 月 22 日 | Planning；Goal Setting and Monitoring |  |
| 9 月 29 日 | Tool Use / Function Calling；Model Context Protocol | HW1 due；HW2 released |
| 10 月 6 日 | No class；Individual Project 1: Hackathon AI for SDG |  |
| 10 月 13 日 | Memory Management |  |
| 10 月 20 日 | Knowledge Retrieval / RAG | HW2 due；HW3 released |
| 10 月 27 日 | Multi-Agent Collaboration；Inter-Agent Communication |  |
| 11 月 3 日 | No class；Reproduce an agentic AI paper | HW3 due；HW4 released；三人组 project proposal |
| 11 月 10 日 | Human in the Loop；Resource Aware Optimization |  |
| 11 月 17 日 | Reasoning；Learning and Adaptation；Exploration and Discovery | HW4 due；HW5 released |
| 11 月 24 日 | Guardrails |  |
| 12 月 1 日 | Exception Handling and Recovery；Evaluation and Monitoring；Prioritization | HW5 due |
| 12 月 8 日 | Poster / Oral examination | Physical attendance required |

这里有一个容易看错的地方：大纲首页写的是 9 月 8 日到 12 月 1 日，共 13 次 class sessions；时间表额外列出的 12 月 8 日是 poster / oral examination，不是第 14 次普通 lecture。

## 4. 考核结构：真正的压力在 project

课程总评由三部分组成：

| 项目 | 比例 |
| --- | ---: |
| 5 Homeworks | 20% |
| Individual Projects | 30% |
| Group Project（3 人一组） | 50% |

这意味着 group project 是绝对的大头，不能只把它当成最后几周临时拼起来的作业。课程大纲列了两个 individual project：

1. **Individual Project 1：Hackathon AI for SDG**，安排在 10 月 6 日的 no-class 周；
2. **Individual Project 2：Reproduce an agentic AI paper**，大纲标出的截止时间是 **11 月 11 日午夜**；9 月 22 日课堂口头提到的日期听起来像 **11 月 13 日**，最终应以 Blackboard 最新通知为准。

第 9 周还要求三人组 project proposal。大纲把它和 11 月 3 日这一周放在一起，但没有在表格里另列一个具体时刻；我需要到 Blackboard 看老师实际发布的 project brief。

HW 时间线也很清楚：HW1 在 9 月 15 日发布，9 月 29 日截止；之后每两周左右发布下一份，HW5 在 12 月 1 日截止。

## 5. 迟交、缺席和最终展示

迟交政策不是“每天统一扣一点”：

- day 1 扣 30%；
- day 2 再扣 30%；
- day 3 扣 40%。

课程大纲还明确写着，缺席 test examination 不安排 make-up exam 或 special arrangements。12 月 8 日的 poster / oral examination 又特别写了 physical attendance required，所以这个日期需要当作必须到场的课程节点来安排，而不是普通 lecture 可以随便错过。

## 6. AI 可以用，但学术声明不能漏

这份大纲采用的是 **Approach 4：AI tools are freely permitted with no acknowledgement**。也就是说，课堂活动和 assignments 可以使用任何 AI tools，而且不要求单独注明每次使用了什么工具。

但这不等于可以把生成结果直接当成自己的理解。大纲同时要求：

- 每份 assignment 都要提交签署过的 academic honesty declaration；
- 提交内容必须是原创，不能把同一份作业未声明地用于多个课程；
- group project 的每个成员都要对提交内容负责；
- 只有最终版本通过 VeriGuide 提交；
- 没有正确签署 declaration 的 assignment 不会被评分。

所以我会把“允许使用 AI”和“必须对提交内容负责”放在一起理解：工具限制比较宽，但学术责任并没有消失。

另外，课程大纲提醒 lecture notes、assignments、exam questions 和 lecture recordings 都属于学校或课程教学材料。可以从 Blackboard 下载给自己学习，但不能未经老师书面同意转发或分享。

## 7. 我现在的补课顺序

我现在最实际的顺序是：先从 Blackboard 找到 HW1 和第一、第二周的 lecture notes，再用一晚上把 prompt chaining、routing、parallelization、reflection 的定义和例子补起来；下一节课前至少要理解 planning 和 monitoring 为什么是在这些 pattern 之后出现的。

作业方面，第一件事是确认 HW1 的具体题目和 9 月 29 日的提交入口。课程大纲只能告诉我时间线，真正的 rubric、文件格式和是否有额外声明要求，还是要看 Blackboard 上的 assignment 页面。

这门课的路线比我之前想象的更完整：从 prompt chaining 开始，经过工具调用、MCP、RAG、多 agent、memory、guardrails 和 evaluation，最后落到一个需要展示、需要项目合作、还要考虑资源限制的 agentic system。错过两节课确实需要补，但现在至少已经知道应该从哪几个 pattern 开始追。
