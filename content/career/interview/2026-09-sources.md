---
schema: bubblevan/v1
id: career-interview-sources-202609
content_kind: interview_sources
title: 2026-09 面经资料（首批）
date: 2026-09-06
status: draft
visibility: private
topics: [面经, Agent, Harness, RL, AI coding, 后端]
---

这是面经资料库的第一批来源。部分条目本身不是面试记录，而是项目、八股或笔试准备资料；保留它们是因为它们直接决定面试准备方向。

## A. 求职与面试准备背景

### 波哥聊求职：2026-08 AI 求职

来源：[小红书 AFPEKjSqLDI](https://xhslink.cn/o/AFPEKjSqLDI)

本地归档：`D:\MyLab\_data_archive\xhs-job-advice-202608.json`

状态：已保存正文摘要；图片 OCR 字段目前为空，待补图文提取。

保留价值：大模型岗位的项目、八股、coding 三线准备；推理 Infra 的重点包括 Transformer/Attention/RoPE/RMSNorm/MHA-GQA-MQA/MoE、Prefill/Decode/KV Cache/PagedAttention/Continuous Batching、TP/PP/DP/EP/通信原语、性能分析、投机推理和 Agentic inference。

### 28 届 Agent 算法日常实习战况

来源：[小红书 2Ff43lHgA4H](https://xhslink.cn/o/2Ff43lHgA4H)

本地归档：`D:\MyLab\_data_archive\xhs-agent-intern-oc.json`

核心信息：腾讯/字节日常实习的面试体验高度依赖项目展开质量；项目讲得顺时，可能少问八股、少手撕；项目追问不稳时，会被放进真实业务场景继续追问。作者主要用 Codex 根据简历生成八股，再针对简历内容逐版迭代。

## B. Agent / Harness 面经

### “基础知识不扎实”的 Agent 面评

来源：[小红书 9263zmd2LIO](https://xhslink.cn/o/9263zmd2LIO)

本地归档：`D:\MyLab\_data_archive\xhs-interview-weak-basics.json`

题目清单：

1. 项目是否在学校完成；智能体项目整体架构与个人职责。
2. Harness 的接触和理解；Agent Harness 所处阶段、组成部分和作用。
3. 为什么多 Agent；审查 Agent 如何设计。
4. 任务队列的幂等与限流；多 Agent 并行领任务如何避免重复领取。
5. Cache Breakdown/缓存命中率；32 轮窗口、30 轮迭代和 300 秒超时的依据。
6. 主 Agent + sub Agent 架构、子 Agent 分工和协作调度。
7. 多 Agent 同时修改记录时如何处理锁、冲突与快速定位方案。
8. RAG 评测集和 MRR 计算。
9. MCP 失败后的最终状态反馈；Skill Register 动态加载业务 Skill 的过程和设计初衷。
10. LangFuse 如何排查 bad case；是否读过主流 Agent 源码；Hermes 的亮点。
11. 算法题：岛屿数量、判断对称二叉树。

评论区有效补充：涉及共享文件/记录时，不应把上锁和解锁交给 Agent 自己记忆；更稳的方式是把编辑动作收敛到专门的非 Agent edit node，由代码完成上锁—编辑—解锁。另有评论提醒，Agent 应用开发仍可能追问传统后端基础，具体取决于简历和岗位。

### 字节 AI 应用日常实习二面

来源：[小红书 8Po9hYxpCJG](https://xhslink.cn/o/8Po9hYxpCJG)

本地归档：`D:\MyLab\_data_archive\xhs-mysql-redis-qa.json`

题目清单：

- MySQL 行级悲观锁、Redis 缓存击穿、互斥锁和加锁失败处理。
- 对称/非对称加密、常用算法、用户敏感信息处理。
- 项目取舍、校园心理项目动机、意图识别和安全判断。
- 子 Agent 分工、黑板机制、路由规则、生产者/消费者、Redis 与数据库选型。
- 数据库表、记忆摘要表、短期/长期记忆、对话压缩和 800 轮对话处理。
- Docker 部署、MCP 能力、任务队列幂等与并发/总量限流。
- 手撕：字符串分割并打印结果。

### 字节 AI 应用日常实习一面

来源：[小红书 2CiQSocZDRv](https://xhslink.cn/o/2CiQSocZDRv)

本地归档：`D:\MyLab\_data_archive\xhs-project-grilling.json`

题目清单：

- 代表性项目、引擎启动/触发机制、多智能体核心 Agent、协作与调度。
- 风控指标、发布策略、策略因子获取/计算。
- Harness 的角色、职责、解决的问题，以及引入 Harness 的工程思想。
- 链路完整性的定义、校验标准、请求未到中台时的兜底和异常处理。
- 算法题：把数组中小于等于 X 的元素聚集在一起所需的最少两两交换次数。
- 进程与线程区别、DNS 原理。

## C. Agent / RL 与项目资料

### Agentic 开源代码与 task 众筹讨论

来源：[小红书 1ratBmPAGtk](https://xhslink.cn/o/1ratBmPAGtk)

记录要点：计划做 Linux 本地运行、无需 remote sandbox/API key 的 long-horizon agentic task；提供 GRPO/Critic PPO + trick suite 的一键基线复现，并支持 context compaction。评论建议关注 BrowseComp-plus、SWE-bench 变种、AAII、τ-bench/τ²-bench、AppWorld、GAIA、WebArena、SciWorld、AgentVista、Terminal-Bench 等。

工程启示：这类项目的价值不只在算法，还在环境替代、部署成本、基线透明度、可复现性和长任务的上下文/工具治理。

### Pi + Slime Agentic RL

来源：[小红书 1fdduBamAX9](https://xhslink.cn/o/1fdduBamAX9)

本地归档：`D:\MyLab\_data_archive\xhs-pi-slime-agentic-rl.json`

状态：此前已收藏，但仍需纳入项目对照表。核心是 Pi Harness 接入 Slime，在 ShopSimulator 做 SFT + RL；Qwen3.5-2B，单卡 RTX PRO 6000D，成功率从 0% 到 SFT 后 10.5%，再经 100 step GRPO 到 31%。

### 98 个模型架构对比

来源：[小红书 3L6wuOLth9j](https://xhslink.cn/o/3L6wuOLth9j)

本地归档：`D:\MyLab\_data_archive\xhs-arch-98-compare.json`

用途：和 CS336 A1 的实现放在一起理解，作为模型结构、Attention、MoE、残差与不同架构取舍的对照材料；它本身不是 TODO，后续可转成学习任务。

## D. Coding / AI coding 面经

### 阿里 AI coding 笔试全 0

来源：[小红书 1OnSNiQzId7](https://xhslink.cn/o/1OnSNiQzId7)

本地归档：`D:\MyLab\_data_archive\xhs-ali-ai-coding-zero.json`

记录事实：模拟题通过，正式笔试给 AI coding 约 75 分钟却四个维度全 0；评论区同时出现大量全 0，也有人直接把 README 交给模型得到较高分。

可复用但不能当定律的经验：先保证原始代码能运行；对照 README 和官方测试；复杂 spec 流程未必提升结果；可以保留原始代码，多开独立会话做受控尝试，但每次必须记录初始版本、修改范围、冒烟结果和正式分数。

## E. 待补与后续动作

## F. 港硕实习与 Agent 岗位现实补充

### 港硕实习与晚课冲突

来源：[小红书 729avHWIOnJ](https://xhslink.cn/o/729avHWIOnJ)

标签：`#cuhk` `#港中文` `#实习` `#深圳实习`

本地原文：[raw-2026-09-06-addendum-729-2NaJM9EjSpR.txt](raw-2026-09-06-addendum-729-2NaJM9EjSpR.txt)

场景：港硕学生在上学期做深圳实习，mentor 给出的工作时间为 9:30–18:30，而晚课通常 18:45 开始；作者询问应如何与 mentor 协调，还是自行灵活处理。

评论区可复用的做法：提前和 mentor 沟通固定早退、调换工作时段、在晚间线上补处理，或接受按实际工时计算；关键是入职前把安排说清楚。评论区也有“逃课”“直接放弃实习”等相反建议，这些只能作为个人经验，不能当作学校、签证或雇佣规则。

风险核对清单：确认课程签到和退课/withdraw 门槛；确认港硕学生的实习、出入境及工时要求；计算深圳往返后的真实可用工时；把 mentor 同意的出勤安排留成文字记录。这里记录的是求职/实习决策素材，不替代学校或官方政策解释。

### 校招生的迷茫：Agent 开发、Vibe Coding 与能力积累

来源：[小红书 2NaJM9EjSpR](https://xhslink.cn/o/2NaJM9EjSpR)

本地已有归档：`D:\MyLab\_data_archive\xhs-campus-agent-2months.json`

本地原文：[raw-2026-09-06-addendum-729-2NaJM9EjSpR.txt](raw-2026-09-06-addendum-729-2NaJM9EjSpR.txt)

场景：校招生入职约两个月，工作内容主要是 Vibe Coding、Skills/MCP 以及简单前后端；代码多由 AI 生成，因担心没有积累传统硬技能而迷茫。评论区围绕 RAG、LangChain/LangGraph、Agent Harness、评测、业务理解和工程能力展开。

评论区观点整理：

- 先补 RAG、embedding、reranker、评测等基本概念，但不要把“会调框架”当成能力终点；可以用 deepeval、Vitabench 等工具理解评测闭环。
- LangChain/LangGraph 在既有业务和传统岗位中仍可能有用，但 Agent 方向也在转向 Pi、dsh、Claude Code、Codex runtime 及自定义 Harness；具体岗位要看实际栈。
- 更长期的能力是把业务目标、约束、权限、数据安全、错误处理、可观测性和指标接起来，解释为什么这样设计、如何验证，而不是只会让 AI 生成代码。
- 要区分“用 AI 写代码”和真正负责 Agent 生命周期：工具调用、状态管理、重试、并发冲突、上下文治理、评测和上线后的故障闭环都应成为准备题。

准备动作：把这条和当前 Agent/Harness 面经放在一起复习；为自己的项目补一页“业务目标—架构约束—指标—失败模式—评测方式”；至少能手写一个小型 RAG/工具调用链路，并解释何时不该使用 RAG 或大框架。评论区存在互相冲突的职业建议，统一按“观点素材”保存，不当作行业定律。

- [ ] 补 `AFPEKjSqLDI` 的图片 OCR；当前本地 JSON 的 OCR 字段为空。
- [ ] 补 `6nmWX8P8S7M` 的图文 OCR；当前本地 JSON 的图片 OCR 字段为空。
- [ ] 把 `1fdduBamAX9` 的 Pi + Slime 项目整理成一张复现卡：环境、模型、rollout、reward、训练参数、成功率、可复现性。
- [ ] 将 Agent/Harness 面经拆成自测题，而不是只背题目：每题补“我的项目证据—设计理由—失败模式—验证方式”。
- [ ] 将后端基础题补进面试准备索引：锁、Redis、队列、加密、Docker、网络、进程线程。
- [ ] AI coding 笔试保留多个过程记录，区分“模型随机性”“提示流程”“代码初始状态”“测试/评分问题”。

## G. 小红书战魂哥与波哥直播：校招、后训练与岗位选择

来源：用户提供的直播后半段文字转录；未提供原始直播链接。

本地原文：[raw-2026-09-06-live-xhs-zhanhun-boge.txt](raw-2026-09-06-live-xhs-zhanhun-boge.txt)

记录范围：用户迟到约 10 分钟，因此只录到直播后半段。以下是可确认的主题摘要，不把缺失的前半段补成完整访谈。

### 直播中的主要观点

- **后训练经历对求职的帮助**：如果目标是后训练岗位，简历最好有微调、强化学习或可解释的训练项目；没有真实项目时可以先做项目补足，但包装的前提是自己真正理解，能够回答训练流程、方法选择和实验结果。原文中的“GRPU/GSPO”等词存在转录误差，需回看音频或原帖确认具体术语。
- **岗位方向与个人体验**：嘉宾目前偏搜推工作，认为纯大模型更符合兴趣、上限更高；搜推业务相对稳定、下限较高，但技术和薪资变化可能没那么剧烈。大模型、初创和大厂创新业务的薪资溢价，来自业务仍处于争夺人才和验证方向的阶段，并非所有挂 AI 名称的岗位都如此。
- **选 offer 的维度**：先匹配自己想要的工作强度，再看技术成长、组内技术主动性、能否拿到训练/算力/项目资源，以及岗位实际内容；大厂 title 只能作为一个维度，不能替代对具体工作含金量的判断。公司战略可能半年一变，选 offer 存在信息不对称和运气成分。
- **秋招实习转正**：区分“实习转正概率不明、用实习替代正式 offer”和“正式 offer 已基本确定，只是允许学生提前以实习身份入职”。前者风险高，后者可以通过提前体验团队、观察强度和 leader，降低正式入职后的信息差；具体要看书面 offer、转正条件和是否还有其他选择。
- **投递与研究生项目**：不要在同一招聘系统留下过于分散的岗位方向；导师与企业合作项目的求职价值差异很大，有的只是完成任务，有的能形成论文、前沿项目和大厂合作经历，需要自己判断预期，不要默认导师项目会提升秋招竞争力。
- **大模型与搜推的选择/转向**：大模型岗位可能更看重硬背景、训练实践和论文/项目；搜推更看重实习、比赛、数据集项目和工程经验。纯大模型转搜推需要补完整业务链路，搜推转纯大模型也需要自己的训练项目，不能只靠岗位名称迁移。
- **简历长度与内容**：AI 让简历普遍变长，但长度不是价值；重点是能否用较少篇幅讲清楚项目目标、本人贡献、技术取舍、指标和结果。过长的经历应删掉重复的工具名和泛化描述。
- **不要人为划死岗位边界**：直播强调前端、后端、算法和 Agent 的边界正在变薄，尤其在 AI coding 普及后，公司可能期待一个人能理解上下游并使用 Agent 提升产出；但这应理解为需要具备跨界协作和基本工程能力，不等于每个人都要把所有方向学到同等深度。
- **当前方向建议**：对尚未确定方向、且还没有开始积累项目的人，直播建议关注 Agent Harness；对尚未进入头部后训练团队的人，则先脚踏实地补基础、做能展示的项目。这个建议属于直播嘉宾的观点，不作为普适结论。

### 可转成自己的准备任务

1. 写一张后训练项目卡：数据、SFT/RL 方法、训练/推理链路、评测指标、失败案例和本人贡献。
2. 为每个目标 offer 建立对照表：岗位实际工作、技术主动权、团队稳定性、强度、薪资确定性、转正条件和可迁移能力。
3. 把搜推与 Agent/大模型的差异写成能讲清楚的系统图，避免只背“算法岗/开发岗”的标签。
4. 将简历压缩到“项目目标—关键决策—结果—证据”结构；所有写上的技术点都准备追问答案。

备注：这是 ASR/人工整理的直播转录，原文中有明显同音、术语和人名识别错误；原文完整保存，摘要只提取可辨认内容。

## 资料来源说明

本页的链接来自小红书；题目、正文和评论摘要来自用户提供的原文或本地归档。没有 OCR 或没有抓取到的部分标为待补，不把推测写成面试事实。
