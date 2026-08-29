---
schema: bubblevan/v1
id: blog-20260829-llm-agent-job-map
content_kind: blog
title: LLM / Agent 求职工作台：项目锚点、知识图谱与面试索引
date: 2026-08-29
updated: 2026-08-29
status: draft
visibility: private
draft: true
summary: 用三个项目锚点组织 LLM / Agent 求职准备，并为知识方向、Interview QA、资源入口和 NOW/NEXT/LATER 建立可维护索引。
topics: [LLM, Agent, Career, Knowledge Management]
projects: [llm-agent-job-map]
aliases: []
authors: [bubblevan]
---

## Dashboard：现在准备什么

这是一份长期维护的私人求职笔记。当前输入包括一份 729 行的付费资料 dump、三个已下载项目目录、一组 Broad View 讨论和我自己的计划。完整问答、下载链接、密码及截图只保存在 Git 忽略的 `.blog-state/llm-agent-job-map/`；这里保存脱敏后的 Project Map、Knowledge Map、QA Index、Resource Map 和 Action Map。

### 三个主项目

| ID | 项目锚点 | 求职作用 | 当前状态 | 当前能确认什么 | 最近的证据动作 |
|---|---|---|---|---|---|
| P1 | Agent + Backend | 工程主线：service、retrieval、deployment、observability、harness | `planned` | 行政助手项目目录和 Go/CloudWeGo 笔记存在；StablePay 项目文件不在当前 source set | 找回 StablePay 复盘；在行政助手中 trace 一条真实 request path |
| P2 | Agent Harness | Agent Broad View 中心：loop、skills、memory、RAG、tool use、multi-agent、eval | `planned` | 医疗助手/Swarm/R1 目录存在；尚未运行或逐模块核对 | 选一个概念，定位代码入口、I/O、状态与 failure mode |
| P3 | Post-training | 算法主线：multi-turn tool use、SFT/RL、reward、rollout、eval | `planned` | 客服项目的 RL/SFT 目录存在；资料描述与代码结构存在待核对差异 | 先跑 baseline，再决定 Search Agent 扩展实验 |

### 当前动作

| 时间层 | 动作 | 状态 | 完成条件 |
|---|---|---|---|
| NOW | 保持三条主线的 Project Card、Evidence State 和私有指针同步 | `verified`：本工作台已建立 | 新证据可以落到明确项目和 Claim State |
| NOW | 从 P1/P2/P3 中选择第一个可运行 baseline | `unknown`：尚未决定顺序 | 有命令、环境、输出和失败记录 |
| NEXT | 整理 Search-R1 reading map | `planned` | 有来源、阅读状态、与 P3 的具体连接；不等于已经复现 |
| NEXT | 补 Harness / Memory / Eval 卡片的代码证据 | `planned` | 每张卡至少有一个代码 locator 或一次运行观察 |
| LATER | Search Agent benchmark / reproduction | `candidate` | 目标算法岗或 P3 baseline 暴露明确问题 |
| LATER | Mem0 / Zep / LangMem comparison | `candidate` | P2/P1 出现 memory 行为或 JD trigger |
| LATER | Long-horizon、Self-evolving、其他候选项目 | `backlog` | 出现具体 JD、实习任务或实现问题 |

### 状态和来源怎么读

| 标签 | 含义 |
|---|---|
| `paid source says` | 付费材料如此描述；不能改写成我的实现或实验结果 |
| `verified` | 我有文件、代码、命令、日志、测试或直接观察；要保留 locator |
| `inferred` | 基于现有证据的判断；必须保留依据和限制 |
| `chosen` | 我主动选择的结构、范围或取舍，不是实验结论 |
| `planned` | 已明确准备做，尚未完成 |
| `candidate` / `backlog` | 值得保留但尚未承诺；需要 trigger 才升级 |
| `unknown` | 当前不能确认；不根据话术或目录名补答案 |

下载了项目，只能证明文件存在。付费材料列出某项技术，也只能证明该 token 出现在资料中。业务指标、dataset provenance、模型配置、latency、代码 ownership 和实际完成范围，在出现 direct evidence 前均为 `unknown`。

## 用项目锚点扩展知识

当前策略是先把项目跑通、讲清并留下可验证产物，再沿项目暴露的问题扩展知识。项目负责提供任务、代码和面试入口；知识图谱负责解释设计选择、补齐追问和寻找下一次实验。

```text
项目中的具体问题
  -> Evidence gap
  -> Knowledge Card
  -> 最小阅读或实验
  -> 回写项目证据
  -> 面试 QA
```

知识方向只在以下事件出现时升级：目标 JD 明确要求；实习任务需要；面试追问暴露理解或证据缺口；当前实现遇到阻塞。没有 trigger 时，`TBD` 比虚构 reading list 更有用。

三条线承担的重点不同：P1 证明 Agent 工程和 backend 能力；P2 连接 Agent 架构的横向模块；P3 承担 post-training 算法叙事。它们可以共享 Tool Use、Eval、Data 等知识卡，但不能共享未经验证的项目结果。

## Project Map：三个主项目怎么维护

### P1 — Agent + Backend

**角色。** 工程锚点。当前连接 StablePay/OpenClaw plugin 经历线索、行政助手参考项目和已有 Go/CloudWeGo 笔记。它应当回答一个 Agent 服务怎样接入 backend、怎样检索和存储、怎样部署、怎样观察 failure，而不承担主要算法项目的定位。

**私有来源。** 原始资料见 `raw/2026-08-29-juliye.md` 的 P1 段落；本地目录结构见 `local-inventory.md`。StablePay 项目文件目前缺失，不能用行政助手项目替代 StablePay 的真实经历。

| 维度 | 当前记录 |
|---|---|
| `paid source says` | 项目描述覆盖 Harness Engineering、Agent DAG、RAG、Memory、Skill Workflow、服务和部署组件 |
| `verified` | 行政助手目录包含 `backend/`、`deploy/`、`docs/`、`loadtest/`、`services/`、`web/`；CloudWeGo 笔记存在 |
| `unknown` | 哪些模块实际可运行；哪些由我实现；StablePay 的 request path、指标和失败记录 |
| Why keep | 能连接 Agent application 与 backend/service 工程，避免三个项目都只讲模型或 prompt |
| Next verification | 选一条请求，记录入口、鉴权、Agent 调用、retrieval、storage、response、日志和错误路径 |
| Resume gate | 只有我实际运行、修改和解释过的模块进入简历；付费项目技术栈不整体搬运 |

**技术入口清单。** 以下 token 用于代码审计，状态均为 `paid source says / unknown implementation`：

- Harness Engineering、Agent DAG、Loop Engineering、Skill Workflow；
- BM25、Milvus、RRF、Reranker、MongoDB、Redis Stream；
- FastAPI、K8s、HPA、Prometheus；
- AgentScope、BGE-m3、PostgreSQL、async architecture 可作为相邻参考，不自动归入 P1 实现。

**准备讲清的边界。** 一条请求为什么需要 Agent；确定性 workflow 与自由规划怎样分工；retrieval 失败时怎样定位；Redis/MongoDB 各存什么；异步队列的交付语义；扩缩容依据什么 signal；哪些指标只有本地或离线证据。

### P2 — Agent Harness

**角色。** Broad View 中心。医疗只是载体，真正需要验证的是 Agent loop、Harness、Skills、Memory、RAG、Tool Use、Multi-Agent 和 Eval 怎样组合，以及它们与 SFT/RL、inference、deployment 的边界。

**私有来源。** 原始资料见 P2 段落；本地观察到 `medix-agent-swarm/`、`MediX-R1/` 和运行讲解视频。目录名不能证明 Swarm、Memory 或训练流程已经工作。

| 维度 | 当前记录 |
|---|---|
| `paid source says` | Skills-Agent、Agent Swarm、双层记忆、RAG、VLM 两阶段训练等被列为项目组成 |
| `verified` | 两个主要目录和视频文件存在 |
| `unknown` | loop 停止条件、agent 间共享状态、memory 写入/读取规则、评测数据和训练结果 |
| Why keep | 一个项目可以触发大部分 Agent architecture 问题，适合作为横向知识中心 |
| Next verification | 从 Memory 或 Skill 选一个模块，定位入口、输入、输出、持久化、错误处理和测试 |
| Resume gate | 场景叙述必须让位于实际实现；医疗模型、数据和评分若未运行，不进入我的结果 |

**技术入口清单。** `ReAct`、Agent Swarm、RAG、Milvus、Redis、Mem0、YAML Skills、SFT、GSPO、easyr1、FP8、vLLM。`Qwen3.5-9B`、`MedEmbed` 等配置只保留在私有审计中，直到代码、运行参数和资源条件相互一致。

**第一轮代码审计问题。** Agent 由谁创建和调度；状态存在哪里；Skill 是说明、schema 还是 executable implementation；工具失败怎样返回；memory 的生命周期和淘汰规则是什么；多个 agent 冲突怎样仲裁；Eval 测的是单组件还是端到端任务。

### P3 — Post-training / Customer-service Agent

**角色。** 算法锚点。当前载体是客服场景的 multi-turn tool-use Agentic RL。Search-R1、后续 Search Agent 论文、benchmark 和 reproduction 是我计划沿 P3 展开的方向，不是原客服项目已经实现的内容。

**私有来源。** 原始资料和差异清单在 P3 段落；本地观察到 `OpenSearch-VL-clean/`，其下有 `RL/`、`SFT/`、`opensearch_vl/`。这仍不证明 baseline、reward、rollout 或 eval 可复现。

| 维度 | 当前记录 |
|---|---|
| `paid source says` | 项目定位为 multi-turn tool-use Agentic RL / post-training |
| `verified` | 代码目录存在；付费说明文本内部记录了工具数、数据构造、评测构造和模型规格的多项差异 |
| `unknown` | 实际工具集合、dataset provenance、训练 recipe、reward 实现、rollout 轨迹、baseline 和结果 |
| Why keep | 能形成偏算法岗位主项目，并自然连接 Tool Use、Agentic RL、Eval 与 Search Agent |
| Next verification | 固定环境与 commit，运行最小 baseline；记录数据样本、工具 schema、trajectory、reward 和 metric |
| Resume gate | 先解决文档—代码差异；任何训练曲线、准确率或提升值必须来自我自己的 run |

**验证顺序。** 先读 task definition 和数据样本；再核对 SFT/RL 入口、模型和工具集合；然后运行 inference/baseline；最后才讨论 reward、rollout、RL recipe 与 Search 扩展。若 baseline 无法运行，失败日志本身是 `verified observation`，不能用付费问答代替。

**计划扩展。** `Search-R1 -> follow-up literature -> benchmark/reproduction` 当前为 `planned/candidate`。下一步 reading map 仍需补来源和筛选标准；没有决定的论文名称保持 `TBD`。

## Knowledge Map：19 个可下钻方向

每张卡使用同一组字段：`Anchor` 表示从哪里触发，`State` 表示当前深度，`Next` 是最小的阅读或实验，`Deepen when` 是升级条件。表中的连接表示“值得从该项目下钻”，不表示项目已经实现了该技术。

| ID | Direction | Anchor / Why it matters | State | Next resource / experiment | Related projects | Deepen when |
|---|---|---|---|---|---|---|
| K01 | Agent Core / Loop / Planning | P2；要能解释 observe-decide-act、停止条件和失败恢复 | `broad awareness` | 在 P2 找到真实 loop，画一次 state transition；资源 `TBD` | P1, P2 | loop 行为、长任务或 planning 追问出现 |
| K02 | Harness Engineering | P1/P2；连接模型、工具、状态、策略和观测 | `planned` | 对 P1/P2 各做一张 runtime boundary 图 | P1, P2, P3 | Agent infra/harness JD 或实现边界不清 |
| K03 | Context Engineering | P2；决定每一步实际给模型什么 | `broad awareness` | 记录一次 context assembly：system、history、memory、retrieval、tool result | P1, P2 | token、污染、长上下文或可靠性问题出现 |
| K04 | Memory | P2；处理跨轮状态与可复用经验 | `planned` | 下一入口：Mem0 / Zep / LangMem；先定义同一比较任务 | P1, P2 | JD、实习或项目出现持久状态需求 |
| K05 | RAG / Retrieval | P1/P2；为工具和回答提供外部信息 | `planned` | trace query -> BM25/vector -> fusion -> rerank -> context；记录失败样本 | P1, P2 | retrieval quality、latency 或数据更新成为瓶颈 |
| K06 | Search Agent | P3；把主动检索策略连接到 Agentic RL | `planned` | Search-R1 reading map；后续资源 `TBD`；最小实验待 baseline 后决定 | P3 | 算法岗、Search Agent JD 或 P3 baseline 跑通 |
| K07 | Tool Use / Function Calling / MCP | P1/P2/P3；三个项目的共同执行接口 | `planned` | 核对 schema、参数校验、超时、重试、结果注入和多轮轨迹 | P1, P2, P3 | tool-use eval、协议兼容或 failure 追问出现 |
| K08 | Skills | P2；区分可复用能力说明与实际执行代码 | `broad awareness` | 在 P2 定位一个 Skill 的 metadata、binding、execution 和 test | P1, P2 | “为什么不是一个 Skill 就够”或技能路由问题出现 |
| K09 | Workflow | P1/P2；承载确定性步骤和业务约束 | `broad awareness` | 对比 DAG/workflow 与自由规划的职责、状态和补偿机制 | P1, P2 | 需要稳定交付、审批或可恢复流程 |
| K10 | Multi-Agent | P2；需要解释职责拆分、共享状态和冲突 | `candidate` | 找一个真实协作路径；记录通信、冲突和仲裁；框架资源 `TBD` | P2, stock candidate | Swarm 代码可运行或目标岗位明确要求 |
| K11 | Agent Eval | 横切三项目；决定改动是否有效 | `planned` | 每个项目补 task、baseline、dataset、metric、failure cases | P1, P2, P3 | 任一实验、简历指标或面试结果追问出现 |
| K12 | Agentic RL / Post-training | P3；算法主线的核心 | `planned` | 先核对 trajectory、reward、rollout、policy update 与 eval | P3, phone candidate | P3 baseline 跑通或 post-training JD 出现 |
| K13 | Data | P3；训练和评测 claim 的来源边界 | `unknown` | 建 data card：source、license、schema、split、contamination、version | P2, P3, K12 candidate | 要运行训练、复现实验或解释 dataset |
| K14 | SFT / Distillation | P2/P3；行为初始化与数据利用的候选路径 | `candidate` | 核对实际 SFT 脚本和样本；Distillation 资源 `TBD` | P2, P3, K12 candidate | 数据或 baseline 显示需要行为初始化 |
| K15 | Long-horizon | 独立兴趣；暂未绑定具体问题 | `backlog` | 资源和实验均 `TBD` | P2, P3 | 出现长任务 credit assignment、memory 或 benchmark 需求 |
| K16 | Self-evolving / Agent Optimization | P2 与 harness 演化问题 | `backlog` | 先定义可测的自改进对象；资源 `TBD` | P2, P3 | 岗位、论文复现或在线优化问题出现 |
| K17 | Deep Research / Research Agent | Search/Context 的相邻方向 | `backlog` | 资源 `TBD`；先明确与普通 RAG/Search Agent 的任务差异 | P2, P3 | 目标岗位或研究任务需要多步证据综合 |
| K18 | Inference / Serving / Deployment | P1；把模型/Agent 变成可运行服务 | `planned` | trace batching、streaming、timeout、resource、K8s/HPA 和 observability | P1, P2, P3 | latency、成本、容量或部署任务出现 |
| K19 | Training Systems | P3；训练是否可运行的系统基础 | `candidate` | 核对 DeepSpeed/easyr1、资源占用、checkpoint、rollout worker；资源 `TBD` | P2, P3, phone/K12 candidates | 真实训练出现显存、吞吐或分布式问题 |

### Project ↔ Knowledge 快速索引

| 项目 | Primary | Secondary | 暂不承担 |
|---|---|---|---|
| P1 Agent + Backend | K02 Harness、K05 Retrieval、K09 Workflow、K18 Serving | K03 Context、K04 Memory、K07 Tool Use、K11 Eval | K12 Agentic RL 的主要实验 |
| P2 Agent Harness | K01 Loop、K02 Harness、K03 Context、K04 Memory、K08 Skills、K10 Multi-Agent | K05 RAG、K07 Tool Use、K09 Workflow、K11 Eval、K18 Serving | 仅凭医疗场景声明模型或算法效果 |
| P3 Post-training | K07 Tool Use、K11 Eval、K12 Agentic RL、K13 Data | K06 Search Agent、K14 SFT、K18 Serving、K19 Training Systems | 把 Search-R1 写成原项目能力 |

同一个 Knowledge Card 可以被多个项目复用，但 Evidence 必须按项目记录。例如 P1 和 P2 都涉及 Memory，并不意味着它们使用同一种 memory，也不能把 P2 的付费描述拿来回答 P1 的实现追问。

## Candidate Pool：保留，但不和主项目抢优先级

`不做 != 删除资料`。候选项目用于借鉴模块、复用 QA、响应特定 JD，或在主项目撞车、过时、不可运行时提供替换。状态变化只更新索引，不删除 raw、技术 token、资源 pointer 或 QA。

| ID | Candidate | 可借鉴内容 | 关联 Knowledge | 当前状态 | 升级条件 | 主要风险 |
|---|---|---|---|---|---|---|
| C1 | 差旅助手 Agent | hybrid retrieval、Skill Plugins、async architecture、项目撞车 QA | K05, K08, K09, K18 | `backlog` | Agent application/JD 需要对应模块，且能复现实际代码 | 参考开源项目的 provenance 与个人贡献边界 |
| C2 | 手机智能助理 RL | Tool Use、LoRA/PPO、DeepSpeed、vLLM 的参考实现 | K07, K12, K18, K19 | `backlog` | P3 需要替换/补充 RL 载体，且代码更可验证 | 训练资源、数据和结果未知 |
| C3 | 股票投资顾问 Agent | latency、storage、multi-agent conflict、Skills、Eval 的高密度 QA | K04, K07, K10, K11, K18 | `reference only` | 某类 failure mode 或 JD 高度匹配 | 金融场景知识、指标真实性、项目包装风险 |
| C4 | K12 多模态全链路训练 | dataset provenance、格式清洗、训练与 eval-set 追问 | K11, K13, K14, K19 | `backlog` | 多模态 JD 或训练模块出现明确需求 | 数据来源、最小实现和评测口径未知 |

候选项目升为主线前要同时满足：目标问题不能被现有主项目覆盖；代码/数据/日志可由我复现；authenticity 风险可解释；有时间预算和完成条件。借鉴一个模块，只能写成我实际采用、修改和验证的模块，不能写成拥有整个项目经历。

## Interview QA Knowledge Base：16 条现有索引

逐字问题和付费回答继续放在 private raw。这里给每组问答稳定 ID、简短问题、项目视图、问题类型、证据要求和 raw locator。以后重新分类只改索引，不复用或删除 QA ID。

### 按 QA 记录

| ID | 项目 | 类型 | 问题摘要 | 回答状态 | 变成我的回答前需要什么 | Private locator |
|---|---|---|---|---|---|---|
| QA001 | cross-project | Learning Strategy | 八股提前系统背，还是按面试追问复盘？ | paid answer recorded | 我的投递/面试节奏和失败复盘 | raw L3-L17 |
| QA002 | P2 | Learning Scope / Post-training | 算法岗需要补哪些推理、训练、模型和 RL 知识？ | paid answer recorded | 目标 JD 与当前缺口；不能自动变成全量计划 | raw L82-L89 |
| QA003 | P2 | Evaluation | 开发类 Agent 的组件层和系统层怎样评？ | paid answer recorded | P2 的 task、component boundary、dataset、metric、failure | raw L108-L113 |
| QA004 | P2 | Authenticity / Dataset | 小模型和公开医疗数据应怎样陈述？ | paid answer recorded | 实际模型、运行参数、数据来源、许可和评测 | raw L115-L118 |
| QA005 | C1 / cross-project | Collision / Authenticity | 项目撞车时怎样解释？ | paid answer recorded | provenance、我的修改、差异、取舍和验证 | raw L252-L259, L328-L353 |
| QA006 | C3 / internship packaging | Authenticity / Metrics / System Design | 未实现模块、包装内容和指标是否可信？ | paid answer recorded | 模块清单、代码 locator、baseline、日志；用于审计，不作简历话术 | raw L355-L405 |
| QA007 | cross-project | Evaluation / Dataset / Authenticity | 个人项目没有真实业务流量和企业数据时怎样说明评测？ | paid answer recorded | 公开/自建数据来源、离线 protocol、限制；不得虚构线上用户 | raw L409-L423 |
| QA008 | C4 | Dataset / Implementation Gap | 最小实现、数据清洗和评测集来源怎样解释？ | paid answer recorded | dataset card、清洗脚本、split 和 evaluation command | raw L430-L449 |
| QA009 | C3 | Relevance / Collision | 股票知识会不会卡住，项目是否撞车或过时？ | paid answer recorded | 目标 JD、可迁移模块和当前项目比较 | raw L528-L566, L636-L640 |
| QA010 | C3 | Evaluation / Authenticity | 包装成实验室项目后灰度测试是否保留？ | paid answer recorded | 实际测试记录；没有运行就明确没有 | raw L568-L571 |
| QA011 | C3 | Latency / Multi-Agent / Observability | 端到端 latency、并行拆分和冲突怎样定位？ | paid answer recorded | 分段 timing、trace、并发条件、冲突样本和修改前后结果 | raw L573-L587 |
| QA012 | C3 | Memory / Storage | Redis 到底存什么，格式是什么？ | paid answer recorded | 实际 key/schema、TTL、读写路径和持久化边界 | raw L589-L592 |
| QA013 | C3 | RL / Finetuning | 为什么用 LoRA 而不是 full finetuning？ | paid answer recorded | 资源约束、训练配置和自己的对比；资料中的效果数字不可冒用 | raw L594-L599 |
| QA014 | C3 | Dataset / Evaluation / Caching | 回测样本怎样采样，缓存怎样兼顾实时性？ | paid answer recorded | 数据时间范围、sampling、TTL、失效策略和实验 | raw L601-L608 |
| QA015 | C3 | System Design / Skills | 为什么不是写一个 Skill 文档就够？ | paid answer recorded | Skill interface、背后执行代码、状态与 failure boundary | raw L610-L617 |
| QA016 | C3 | Evaluation | accuracy 为什么不够，Precision/Recall 与回测指标怎样定义？ | paid answer recorded | 针对当前 task 的正负样本、K、baseline、计算代码和 failure cases | raw L619-L634 |

### 按项目查看

| 项目视图 | QA IDs | 当前 coverage gap |
|---|---|---|
| cross-project / preparation | QA001, QA005, QA007 | 缺少我自己的面试失败复盘 |
| P1 Agent + Backend | — | 需要从真实项目和 private interview docs 新增 service/retrieval/deployment QA |
| P2 Agent Harness | QA002, QA003, QA004 | Memory、Harness、Swarm、Tool Use 的实现追问不足 |
| P3 Post-training | — | 当前 raw 只有项目差异说明；需从代码/面试资料抽取 RL、reward、rollout、tool-use QA |
| C1 差旅助手 | QA005 | 技术追问不足 |
| C2 手机助手 RL | — | 只有技术栈和资源 pointer |
| C3 股票 Agent | QA006, QA009–QA016 | 密度最高，只能作为 taxonomy 样本，不能主导所有项目 |
| C4 K12 多模态 | QA008 | 训练稳定性、inference 和 evaluation 追问未索引 |

### 按问题类型查看

| 问题类型 | QA IDs | 以后新增记录必须补什么 |
|---|---|---|
| Evaluation | QA003, QA007, QA010, QA014, QA016 | task、baseline、dataset、metric、failure、evidence state |
| Memory / Storage | QA012 | working/session/long-term memory 与 cache/storage 的边界 |
| Latency / Performance | QA011 | observation -> instrumentation -> bottleneck -> change -> result |
| RL / Finetuning | QA002, QA013 | 算法解释、资源选择、训练证据分别记录 |
| Project Authenticity | QA004–QA007, QA010, QA013 | claim 来源、实际完成范围、不能声称的内容 |
| Dataset | QA004, QA007, QA008, QA014 | 来源、许可、构造、split、规模、污染和 unknown |
| System Design | QA006, QA011, QA015 | requirement、boundary、trade-off、failure mode |
| Multi-Agent Conflict | QA011 | 数据冲突、结论冲突、职责重叠和仲裁策略 |
| Skills / Tool Use | QA015 | Skill interface 与 executable implementation 的边界 |
| Learning Strategy | QA001, QA002 | 只作策略输入，不自动写成 confirmed plan |

### 面试回答 Grounding Gate

Paid answer 只能提示下一步查什么。要变成我的回答，至少需要：能定位到自己的代码和修改；dataset 来源与 split 可说明；baseline 与 metric 定义可复现；latency 有 trace；失败案例和限制有记录；不存在的线上流量、用户反馈或业务指标不写。

每次面试后新增一条 QA record，字段至少包含 `qa_id`、`project_ids[]`、`question_types[]`、`question_summary`、`raw_locator`、`answer_provenance`、`claim_state`、`technical_tokens[]`、`requires_actual_evidence[]`、`last_reviewed`。同一问题可挂多个标签，但只有一个 source record。

## Resource Map：入口、凭据和使用状态分开

正文不保存付费 URL、密码、提取码或截图。精确值在 `private-links.md`；这里仅记录资源类别、关联对象、是否实际访问和下一次使用条件。`recorded` 只说明 raw 中出现过，不能推导 `accessible`、`used` 或 `still current`。

| ID | Resource type | 服务对象 | Recorded | Accessible / Used | Freshness | Next use | Private pointer |
|---|---|---|---|---|---|---|---|
| R01 | 八股速记与开发/算法学习计划 | QA001, general preparation | yes | `unknown / unknown` | `unknown` | 根据第一次目标面试补缺口时 | `private-links.md` learning entries |
| R02 | P1 项目、面试文档和解析 | P1 | yes | local project exists；docs 未逐项验证 | `unknown` | P1 request-path audit | P1 link entries + raw locator |
| R03 | P2 项目、面试文档和视频 | P2 | yes | local project/video exists；未运行 | `unknown` | P2 module audit | P2 link entries + screenshot pointers |
| R04 | P3 项目、面试文档和解析 | P3 | yes | local project exists；未运行 | `unknown` | P3 baseline audit | P3 link entries + discrepancy locator |
| R05 | Candidate project packages | C1–C4 | yes | `unknown` | `unknown` | candidate 升级或模块借鉴时 | candidate entries |
| R06 | 简历模板与技能模块示例 | resume | yes | `unknown / unused` | 2026.8 记录，是否仍适用未知 | 有自己的 verified evidence 后检查表达 | resume entries |
| R07 | 招聘表、内推表和 Job Feed | target JD | yes | 本轮未访问 | `unknown` | 开始新一轮投递或调整项目权重时 | job-resource entries |
| R08 | 面经、刷题和面试技巧入口 | QA KB | yes | 本轮未访问 | `unknown` | 目标公司面试前或复盘后 | interview entries |

资源打开后才更新 `accessible`；实际用于代码、阅读或投递后才更新 `used`；结合日期和目标岗位复查后才更新 `still current`。访问失败也是记录，不用立刻删除 pointer。

## Action Map：怎样避免再次变成收藏夹

### NOW

- [ ] 在 P1/P2/P3 中确定第一个 baseline；当前顺序 `unknown`。
- [ ] 为选定项目保存环境、启动命令、输入、输出、失败日志和 commit。
- [ ] 新增该项目第一批 direct QA，优先补 P1 或 P3 的空白。
- [x] Raw、逐字 QA、密码、链接和 8 张截图已迁入 ignored private state，并保存 SHA-256 snapshot。
- [x] 本工作台已建立 3 个 Project Cards、19 个 Knowledge Cards、16 条 QA 索引和 8 类资源登记。

### NEXT

- [ ] P1：补 StablePay/OpenClaw plugin 复盘，或明确永久缺失；行政助手 trace 一条 request path。
- [ ] P2：从 Memory、Skill 或 Agent loop 选择一项完成代码审计。
- [ ] P3：核对文档—代码差异，运行最小 inference/baseline。
- [ ] Search-R1：建立 reading map，区分已读、待读、候选复现；后续论文保持 `TBD` 直到筛选。
- [ ] Eval：给已运行项目补 task、baseline、dataset、metric 和 failure cases。

### LATER

- [ ] 目标 JD 触发后，再决定 Search Agent benchmark/reproduction。
- [ ] Memory 需求出现后，再设计 Mem0 / Zep / LangMem 的同任务比较。
- [ ] Long-horizon、Self-evolving、Deep Research、Training Systems 保持 backlog。
- [ ] Candidate Pool 只在替换、模块借鉴或 JD 高匹配时升级。

### 状态转换规则

```text
backlog / candidate
  --明确 trigger + 时间预算--> planned
planned
  --代码、命令、日志或实验--> verified
verified
  --source/hash/实现发生变化--> recheck
```

计划阅读不等于已经理解；下载项目不等于已经跑通；资料回答不等于我的面试答案；目录中的组件名不等于实现证据。失败的运行可以升级为 `verified observation`，`unknown` 也允许长期保留。

## Private / Public 边界与维护入口

| 层级 | 内容 | 位置 | Git 状态 |
|---|---|---|---|
| L1 Dashboard | 项目、知识、行动的快速状态 | 本文件 | draft/private，可 track；不含付费原文 |
| L2 Cards | Project / Knowledge / Candidate cards | 本文件 | 脱敏摘要，可 track |
| L3 Index | Evidence、QA、资源和私有 pointer | `.blog-state/llm-agent-job-map/*.md` | ignored/local-only |
| L4 Raw | 逐字 paid QA、URL、密码、截图、source snapshots | `.blog-state/llm-agent-job-map/raw/` | ignored/local-only |

维护入口：

- `source-set.md`：source snapshot 和 SHA-256 manifest；
- `evidence-inventory.md`：I001–I046 的来源类型与保留方式；
- `qa-index.md`：QA001–QA016 的稳定记录；
- `private-links.md`：付费 URL、密码、提取码、截图 pointer；
- `grounding-ledger.md`：claim、evidence、limitation 的对应关系；
- `raw/`：原始材料，禁止 normalize、覆盖或从 Draft 回写。

如果 source hash 变化，先停止后续改稿，重新做 inventory 和 grounding。若 private 文件已经被 Git track，仅添加 `.gitignore` 不算修复；先报告，未经确认不 rewrite history。

## 当前缺口

- StablePay/OpenClaw plugin 的文件和可验证实现不在当前 source set。
- 三个下载项目都还没有形成我的运行记录、benchmark 或逐模块审计。
- P1 与 P3 的 Interview QA coverage 近乎空白。
- 具体目标 JD、实习任务和投递优先级尚未进入工作台。
- Search-R1 之后的论文、Search Agent benchmark、Long-horizon 与 Self-evolving 资源仍为 `TBD`。
- 所有外部资源的可访问性和时效性本轮均未复查。

下一次更新从一次真实项目运行或一次真实面试开始。先补 evidence，再调整项目权重和知识卡；不再向正文堆新的未分类链接。
