---
schema: bubblevan/v1
id: project-health-copilot
content_kind: project
title: Health-Copilot：面向 Evidence Agent 的 Harness Engineering
aliases:
  - /projects/health-copilot/01-项目结构与实现基础/
date: 2026-07-19
updated: 2026-09-27
status: draft
visibility: public
summary: 从患者教育场景出发构建可控、可验证、可复现的 Agent Harness：围绕 Evidence RAG、受限工具调用、Context/Memory、Multi-Agent 与后训练逐步扩展 Runtime，并用公开 benchmark 验证关键组件。
topics:
  - agent
  - harness
  - rag
  - health-ai
project:
  role: ML / Agent Engineer
  stage: prototype
  highlights:
    - 从 deterministic safety gate 出发，逐步构建带 Evidence、Tool Budget、Claim Verification、Trace/Replay 与 Eval 的受限 Agent Runtime。
    - 在 R2MED public TEST 303 queries 上，将冻结 retrieval pipeline 的 equal-subset macro nDCG@10 从普通 BM25+BGE RRF 的 0.1392 提升到 0.2142。
    - 围绕 retrieval failure、candidate complementarity、reranking negative transfer 做完整组件分析，而不是只保留正结果。
    - Context/Memory、Multi-Agent 与 post-training 作为同一 Harness 的后续能力层继续展开。
  tech_stack:
    - Python
    - Agent Runtime / Harness
    - Pyserini / Lucene BM25
    - BGE-large
    - Qwen3-8B / llama.cpp
    - Reciprocal Rank Fusion
    - Structured Output
    - Tool Budget / Policy Guard
    - Trace / Replay / Eval
    - pytest
  repository:
  demo:
---

Health-Copilot 最初是患者教育场景的知识问答原型。开发过程中，我逐渐把重点从“接上模型和检索”转向 Agent Harness：模型能做什么、何时检索、工具失败后如何恢复、回答中的 claim 怎样对应到 evidence，以及每次运行能否追踪和复现。

医疗场景在这里用于提出对证据、拒答、权限和可追溯性的要求。

> **一句话介绍：Health-Copilot 是一个以 Evidence 为中心的 Agent Harness；Runtime 主干覆盖安全门控、bounded tool loop、claim/evidence verification、预算、trace/replay 与 evaluation，RAG 是目前实验最完整的一层，并在 R2MED public TEST 上完成了从 BM25、Dense、Hybrid 到 generation-augmented retrieval 的系统对照。**

## 1. 项目定位与面试介绍

### 30 秒版本

> 我做的 Health-Copilot 本质上是一个 Agent Harness 项目。它从患者教育 RAG 原型开始，后来重点转向 Runtime 对 evidence、tool use、权限、状态和失败恢复的控制。我逐步实现了 safety gate、bounded agent loop、claim verification、budget、trace/replay 和 eval。RAG 是目前实验最完整的一块：在 R2MED public TEST 的 303 个 query 上，DualSource 的 equal-subset macro nDCG@10 为 0.2142，高于普通 BM25+BGE RRF 的 0.1392；但仍低于 LameR-MV 的 0.2225。

### 90 秒版本

> Health-Copilot 一开始是患者教育知识问答项目，后来我把主线转向 Agent Harness。实际难点不只是让模型回答问题，还包括 Runtime 如何决定何时检索、允许调用什么工具、失败后能恢复几次，以及如何验证 claim 是否有 evidence 支持。
>
> 我把这些约束放进 Runtime contract：前面有 deterministic safety gate 和 capability 判断，中间是 Evidence RAG 与 bounded tool loop，后面有 citation、claim support、policy guard 和 deterministic materialization；整个过程还由 budget、trace、replay 和 eval 支撑。
>
> RAG 是目前实验最完整的能力层。我从 Lucene BM25、BGE-large 和 BM25+BGE RRF 开始，继续复现并改造 HyDE、Query2Doc、LameR 等 generation-augmented retrieval，再尝试 Compact Clinical Reasoning Bridge 和 DualSource candidate fusion。R2MED 的 303-query public TEST 上，DualSource 的 nDCG@10 为 0.2142，比普通 hybrid 的 0.1392 高 0.0750；但 LameR-MV 为 0.2225，仍是更强的结果。实验还显示 CRB 与 LameR 能召回互补的 relevant documents，简单融合却没有超过 LameR，这把后续问题指向 candidate ranking，而不只是 recall。

### 我在项目里负责什么

项目架构、检索实验、Runtime contract、评测协议和大部分实现由我完成，主要包括三部分：

- **Agent Runtime / Harness：** safety gate、bounded tool loop、EvidencePolicy、claim/citation verifier、budget、trace 和 replay。
- **RAG / Retrieval：** BM25、dense、hybrid、generation-augmented retrieval、candidate fusion 和公开 benchmark。
- **Evaluation Engineering：** deterministic case、public benchmark、artifact freeze、per-query trace 和 failure analysis。

Memory、Multi-Agent 和 post-training 属于同一 Harness 的扩展方向；面试时会把已有进展与未完成部分分开说明。

## 2. 为什么从 RAG 转向 Harness

最初的链路是“问题 → 检索 → LLM → 回答”。它没有说明模型能否越过安全规则、证据不足时怎么办、工具失败后能否无限重试，也不能保证回答中的 claim 有 evidence 支持。Health-Copilot 后来把这些责任交给 Runtime 中可审计的约束，而不是只继续给 prompt 加规则。

| 需要控制的事情 | Runtime 中的处理 |
|---|---|
| safety、权限和工具能力 | deterministic safety gate、capability guard；urgent / prohibited capability 可 short-circuit 或进入 `HUMAN_REVIEW`，模型可以提出 action，但没有最终权限 |
| 检索结果为空、冲突或不足 | EvidencePolicy 区分 sufficient、insufficient、conflicting 和 recoverable evidence gap；必要时 abstain |
| 工具调用与失败恢复 | model-turn、tool-call、recovery budget 和明确的 failure semantics 限制循环 |
| claim 与来源 | Evidence 保留 document、retriever、query、rank 等 provenance；Runtime 校验 citation ID，claim 必须能回到 Evidence |
| 长任务状态 | Context / Memory 处理跨 turn 状态；具体能力仍在推进 |
| 运行是否可解释和可复现 | Trace、Replay、Failure Record 与 Evaluation 记录每次运行 |

当前 Runtime 主链路：

```text
User Request
→ Input Validation
→ Deterministic Safety Gate
→ Knowledge Scope / Retriever
→ Evidence[]
→ Bounded Agent Proposal
→ Evidence Policy
→ Claim-first Output
→ Citation / Grounding / Support Verification
→ Runtime Policy Guard
→ Deterministic Materialization
→ Answer / Abstain
```

Budget、Trace、Replay、Failure Record 和 Evaluation 横跨整条链路。模型提出的内容要经过 Runtime 检查，side effect 不会因为模型的一句话自动发生。

## 3. Runtime 主线：M0 到 M4

| 阶段 | 解决的问题 | 形成的 contract |
|---|---|---|
| **M0：Evidence RAG** | 如何让模型只基于受控知识回答？ | deterministic safety gate、reviewed knowledge scope、BM25、Evidence、citation ID、evidence-aware generation、citation verification、fail-closed |
| **M1：Bounded Recovery** | evidence 不足时能否有限恢复？ | 增加 `search_knowledge(query)`；早期版本最多 2 个 model turns、1 次搜索，循环边界由 Runtime 控制 |
| **M2：Evidence Policy** | 检索到内容是否就足以回答？ | 区分 sufficient、insufficient、conflicting 和 recoverable evidence gap |
| **M3：Claim-first** | 怎样验证回答中的事实？ | `Evidence → Claims → Verify → Materialize Answer`，而不是直接生成整段 prose 后再猜哪些句子有依据 |
| **M4：Budget / Trace / Replay** | 如何定位运行中的问题并复现？ | 记录 step、tool call/result、budget consumption、claim、evidence 和 failure，服务 debug、evaluation、regression test 与未来 trajectory |

这条主线形成了 Evidence、Recovery、Policy、Claim、Budget、Trace 和 Replay 的 Runtime contract。RAG 结果因此能接入 Agent；未来也可用运行轨迹研究何时检索、怎样改写 query、选择哪种 retrieval action，以及何时停止 search，但这不代表项目已经开始 post-training。

RAG 还为 Runtime 提供 retriever abstraction、带来源的 Evidence、candidate ranking、retrieval confidence / diagnostics、fallback behavior、可复现 artifacts 和 evaluation protocol。

## 4. RAG Benchmark：为什么选 R2MED

Runtime 内部的 patient-education case 适合检查 route、citation、fail-closed 和 tool recovery，却不足以判断检索方法是否真的更强，还是只适配了自己的知识库。因此我另外建立公开 retrieval benchmark 线。

R2MED 聚焦 reasoning-driven medical retrieval。问题表述与相关文献的医学表达之间，可能隔着疾病实体、机制、诊断、治疗和专业术语，适合研究 query expansion、generation-augmented retrieval、multi-view retrieval 和 reasoning bridge，而不只是 lexical matching。

一条 retrieval task 由三部分构成：

| 输入 | 含义 | 评估边界 |
|---|---|---|
| **Query** | benchmark 原始问题，可能是症状描述、临床 case、考试型或治疗相关问题 | retriever 要把相关 document 排到前面，不负责直接回答 |
| **Corpus** | 候选医学文档集合 | 检索只在 corpus 中寻找候选 |
| **Qrels** | `query → relevant document IDs → relevance score` | 只用于离线评价，正常 retrieval pipeline 不应在检索时读取 |

RAG 的实现由 Sparse、Dense、Hybrid 起步，逐步扩展到 generation-augmented retrieval、structured query bridge、multi-view retrieval、candidate fusion 和 reranking diagnostics。完整实验记录见[01 · RAG 项目面试追问](/projects/health-copilot/01-rag项目面试追问/)。

## 5. 检索方法：从 baseline 到 DualSource

### Baseline 与 LameR-MV

普通 baseline 将原始 query 分别送入 Lucene BM25 和 BGE-large，再用 RRF 融合：

```text
original query → BM25 ─┐
                       ├→ RRF
original query → BGE ──┘
```

LameR-MV 先用 BM25 从 corpus 召回 top-10 noisy candidates，再由本地 Qwen3-8B 根据这些 in-domain evidence 生成 retrieval bridge。随后建立四个 view 并融合：

```text
BM25(original) · BM25(generated bridge)
BGE(original)  · BGE(generated bridge)
```

这里的 bridge 是检索表示，不是答案，也不是 evidence。LameR 是公开方法；本项目进行 reproduction / adaptation，并在统一实验中比较。

### Compact Clinical Reasoning Bridge

我进一步尝试把自由文本 bridge 压缩成更结构化的内容，让不同 retrieval channel 能利用不同信息：

```text
q = canonical retrieval query
t = clinical / biomedical terms
e = short pseudo-evidence
```

生成结构为 `{q, t, e}`，之后仍分别进行 sparse original、sparse transformed、dense original 和 dense transformed 检索。生成文本只作为 retrieval representation，不是最终医疗答案，也不能替代 evidence。

### DualSource Fusion

CRB 单独的 nDCG@10 低于 LameR-MV，但二者的 candidate pool 有互补性，因此我测试了 DualSource RRF：

```text
LameR-MV ranking × 1.0
CRB ranking     × 0.5
```

在 R2MED TEST 上，LameR-only 有 95 个独有 relevant pairs，CRB-only 有 62 个，二者共有 430 个。Recall@100 分别为：LameR 0.5699、CRB 0.5340、raw union 0.6204、DualSource 0.5791。DualSource 提高了 LameR 的 Recall@100，但没有超过 LameR 的 nDCG@10；结果说明 candidate generation 有互补，不等于融合后的高位排序更好。

## 6. 公开结果与实验结论

R2MED public TEST 共 303 个 query：MedQA-Diag 118 个、MedXpertQA-Exam 97 个、Medical-Sciences 88 个。Primary metric 是 **equal-subset macro nDCG@10**。

| Method | Macro nDCG@10 |
|---|---:|
| BM25 | 0.0763 |
| BGE-large | 0.1341 |
| BM25+BGE RRF | 0.1392 |
| Compact CRB-Q | 0.1995 |
| DualSource-RRF | 0.2142 |
| LameR-MV | 0.2225 |

面试中如果比较 DualSource 与普通 hybrid，应报 **0.1392 → 0.2142**：绝对提升 0.0750，相对提升 53.9%。同时要说明 LameR-MV 的 0.2225 更高，不能把 DualSource 描述成最佳方法。

面试前记住 benchmark、query 数、metric、比较对象和结论即可；模型 commit、文件 hash、Git SHA 留在实验记录里，需要时再查。

实验中值得保留的结果：

- **Dense 明显强于纯 lexical，但普通 Hybrid 增益有限。** BGE 为 0.1341，BM25 为 0.0763；BM25+BGE RRF 只有 0.1392。RRF 只能融合已有 ranking，不能凭空增加 relevant candidate。
- **Generation-augmented retrieval 带来明显提升。** 普通 RRF 为 0.1392，LameR-MV 为 0.2225，说明 query 与文档的 representation gap 是 R2MED 的重要困难。
- **Recall 提升不等于 top-rank quality 提升。** DualSource Recall@100 为 0.5791，高于 LameR 的 0.5699；但 DualSource nDCG@10 为 0.2142，低于 LameR 的 0.2225。
- **Cross-Encoder 会产生负迁移。** DEV 上 LameR-MV 的 nDCG@10 为 0.2998；加入通用 BGE reranker 后降到 0.2009，candidate Recall@100 基本不变。问题在于 reranker 打乱了有效的高位顺序，而不是候选文档消失。
- **评估要拆开看。** Candidate generation、ranking、fusion 和 generation validity 应分别分析，不能只看一个 end score。

实验把两个问题分开了：不同 query representation 能带来 candidate complementarity，但怎样融合并排好前几位仍需单独验证；Cross-Encoder 也可能因输入 representation 与第一阶段 reasoning signal 不匹配而造成 negative transfer。

## 7. 当前进展与未完成边界

| 能力层 | 当前状态 | 尚未完成的部分 |
|---|---|---|
| **RAG / Evidence Acquisition** | 已形成公开 benchmark 结果：BM25、Dense、Hybrid RRF、HyDE / Query2Doc / LameR reproduction、structured CRB、multi-view retrieval、candidate complementarity、DualSource fusion、reranker negative analysis 和 R2MED public TEST | 细节见[01 · RAG 项目面试追问](/projects/health-copilot/01-rag项目面试追问/) |
| **Memory / Context** | 工程基础存在 | 外部 benchmark 和最终方法结论尚未完成；短期 context 与长期 memory 的区分、写入与检索、更新冲突、遗忘、compaction，以及如何进入 Agent Runtime 仍需继续回答。本文暂不提前总结实验结果 |
| **Multi-Agent** | 已有 Harness 级探索 | 正式项目实验和最终定位尚未完成；任务拆分、worker 分配、Context 共享、结果合并、并发收益成本与失败隔离仍需验证 |
| **RL / Post-training** | 尚未开始正式 Health-Copilot post-training | 未来希望利用 Trace、Trajectory、Tool Result、Evidence、Claim、Verifier 和 Reward Signal 构造训练数据闭环，再研究 retrieval policy、tool-use policy、credit assignment、failure-aware reward、process verifier、trajectory filtering，以及 SFT / preference optimization / RL；未训练的内容不写成项目成果 |

对应专题页：[02 · Memory 项目面试追问](/projects/health-copilot/02-memory项目面试追问/)、[03 · Multi-Agent 项目面试追问](/projects/health-copilot/03-multi-agent项目面试追问/)和[04 · RL 项目面试追问](/projects/health-copilot/04-rl项目面试追问/)。

这些能力共享同一套 Runtime contract：RAG / Search 提供外部知识，EvidencePolicy / Verifier 检查证据，Capability / Tool Guard 限制工具权限，Budget 与 Bounded Recovery 限制执行过程，Trace / Replay 记录运行，Memory / Context 处理长期状态，Multi-Agent 探索协作，Evaluation Harness 判断策略是否真的变好。

当前项目完成度仍按原进展记录：

```text
Agent Harness / Runtime
████████████████░░░░

RAG / Evidence
████████████████████
DONE

Memory / Context
████████░░░░░░░░░░░░
IN PROGRESS

Multi-Agent
██████░░░░░░░░░░░░░░
TO REVISIT

RL / Post-training
░░░░░░░░░░░░░░░░░░░░
NOT STARTED
```

## 8. 面试复盘：贡献、亮点与岗位

### 最大亮点

nDCG 提升只是项目结果的一部分。我把 RAG、Agent 和其他能力放进同一个 Harness contract 中：RAG 部分有 BM25、BGE、RRF、GAR 的公开 benchmark，也分析了 query transformation、candidate complementarity 和 reranker negative transfer；Runtime 再把检索结果转成带 provenance 的 Evidence，经过 bounded tool use 和 claim verification。

Memory、Multi-Agent 与 RL 仍要按第 7 节的状态分别介绍，不能把后续方向说成已完成成果。

### 我具体设计的部分

- **Harness Architecture：** 明确 Safety、Capability、Evidence、Budget、Recovery、Claim、Verification、Materialization、Trace 和 Replay 之间的 contract。
- **RAG adaptation：** 实现 Compact CRB、candidate complementarity analysis、DualSource fusion、same-generator fairness、multi-view retrieval 和 failure attribution；面试时按这些实际工作描述，不把实验结果扩大成算法贡献。
- **Evaluation Harness：** 固定 config、model、data、artifact、ranking、metric 和 failure，让“这次更好”能追到具体 component、数据、指标和配置。

### 岗位对应

| 岗位方向 | 可重点展开的内容 |
|---|---|
| Agent Harness / Agent Infra | Runtime、Tool abstraction、Capability、Budget、Context、Trace、Replay、Recovery、Evaluation |
| Agent / LLM 算法 | Retrieval、Query transformation、Generation-Augmented Retrieval、Reranking、Memory、Multi-Agent、Reward / Verifier、Post-training；讨论方法为何有效或失败时，区分已有结果与未完成方向 |
| LLM 应用 / RAG 算法 | BM25、Dense、Hybrid、RRF、Query Expansion、GAR、CrossEncoder、Evaluation、Failure Analysis，以及怎样接入 Agent Runtime |

## 9. 后续方向

RAG 主线已停止围绕当前 TEST 继续调参。若未来重新开启独立 protocol，我更想研究：

| 方向 | 问题 |
|---|---|
| Retrieval | learned query transformation、reasoning-aware reranker、query-conditioned fusion、retrieval policy learning |
| Agentic RAG | `retrieve → inspect → rewrite → retrieve again → stop`；判断多一次 search 何时有价值 |
| Context / Memory | 将 retrieval 从 external corpus 延伸到 Agent 自身积累的长期状态 |
| Multi-Agent | 不同 Agent 是否需要不同 knowledge scope / tool capability，怎样减少重复 retrieval |
| Post-training | 怎样在 `query → action → evidence → outcome` 之间建立 reward 和 credit assignment |

项目沿着 Runtime → Evidence → Context → Collaboration → Learning 逐步推进，每一步都需要独立证据支持。

## 10. 项目文档与证据入口

### 项目专题

- **已完成：** [01 · RAG 项目面试追问](/projects/health-copilot/01-rag项目面试追问/)，涵盖 R2MED、BM25、Dense、Hybrid、HyDE、Query2Doc、LameR、CRB、Multi-view、DualSource、Reranking、Metrics、Ablation、Failure Analysis、Paper Reading 和 Interview Questions。
- **待补：** [02 · Memory 项目面试追问](/projects/health-copilot/02-memory项目面试追问/)、[03 · Multi-Agent 项目面试追问](/projects/health-copilot/03-multi-agent项目面试追问/)和[04 · RL 项目面试追问](/projects/health-copilot/04-rl项目面试追问/)，分别待 Memory 主线形成正式实验结论、Multi-Agent 完成 architecture 与 benchmark、Health-Copilot 正式进入 post-training 后完善。
- [05 · Agent / LLM 通用八股](/projects/health-copilot/05-agent-llm通用八股/)只放跨项目知识，如 Transformer、Attention、KV Cache、BM25、Dense Retrieval、RRF、Reranker、Context、Memory、MCP、Agent Loop、Multi-Agent、SFT、DPO、PPO、GRPO、Verifier、Reward 和 Distributed Systems basics。项目页记录“我为什么这么做、实际做了什么”，通用八股解释技术本身。

### 实验记录

RAG 主要实验文件：

```text
Health-Copilot/docs/research/r2med_final_public_test.md
Health-Copilot/runs/rag_r2med_final_test/test_report.json
Health-Copilot/runs/rag_r2med_final_test/candidate_analysis.json
Health-Copilot/docs/research/r2med_candidate_reranking.md
```

Runtime 主线可沿 M0 → M1 → M2 → M3 → M4 查看：

```text
Evidence → Recovery → Policy → Claim → Budget / Trace / Replay
```

Memory、Multi-Agent 与 RL 的详细证据入口等对应阶段完成后再补。

Health-Copilot 的主线是 Agent Harness Engineering，Evidence RAG 是目前实验最完整、已有公开 benchmark 的能力层。Memory / Context 和 Multi-Agent 仍处于项目记录所述的未完成阶段，post-training 尚未开始。
