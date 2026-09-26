---
schema: bubblevan/v1
id: project-health-copilot
content_kind: project
title: Health-Copilot：证据 RAG、受限 Agent 与可复现评测
aliases:
  - /projects/health-copilot/01-项目结构与实现基础/
date: 2026-07-19
updated: 2026-09-27
status: draft
visibility: public
summary: 面向患者教育的 Safety-Gated Evidence RAG 项目；包含冻结的 R2MED 医疗检索实验、受限 Agent、Memory 与 Multi-Agent 工程探索及其真实边界。
topics:
  - agent
  - rag
  - health-ai
project:
  role: ML Engineer
  stage: prototype
  highlights:
    - 在复用的 R2MED public TEST（303 queries）上，冻结 DualSource 将 macro nDCG@10 从普通 BM25+BGE RRF 的 0.1392 提升至 0.2142；未超过最强复现 LameR-MV（0.2225）。
    - M0–M10.1 建立 safety-gated evidence runtime、受限 Agent、可验证 Memory/Context 与实验性 Agent Team。
    - 将负结果、数据边界、锁定配置、hash 和测试分母一起保留，不把工程诊断包装成临床效果或 SOTA。
  tech_stack:
    - Python
    - Pyserini / Lucene BM25
    - BGE-large
    - Qwen3-8B GGUF / llama.cpp
    - Reciprocal Rank Fusion
    - pytest / offline evaluation
  repository:
  demo:
---

Health-Copilot 是一个面向患者教育的原型，不是诊断、处方、互联网诊疗或临床决策系统。面试时先把项目拆成两条**相关但不等同**的线：

1. **产品/Runtime 主线**：M0–M10.1，研究如何让受控的 evidence workflow、Agent、Context、Memory 和 Team 有清晰权限、状态和失败边界。
2. **RAG 检索研究线**：在固定公开 R2MED 数据上复现 BM25、BGE 和 generation-augmented retrieval，并研究 LameR 与结构化 clinical bridge 的候选互补和融合。

R2MED 实验不是把产品默认运行时换成了 Qwen/BGE，也没有在 R2MED 上生成临床答案。它是独立的 retrieval-only 实验管线。这个区分能避免把几个实验拼成一个并不存在的“端到端医疗 Agent”。

## 面试时的项目总述

> 我做的是一个患者教育场景的 evidence-first assistant。主 runtime 从 deterministic safety gate 和 BM25 evidence retrieval 起步，再逐步加入有硬预算的单 Agent、claim/evidence 验证、可审计的 Context/Memory 以及实验性 Team。RAG 研究线则用 R2MED 评估 reasoning-driven medical retrieval：固定 Qwen3-8B 做生成增强检索，比较 BM25、BGE-large、普通 RRF、LameR-MV、Compact CRB 和 DualSource。复用 public TEST 的 303 个问题上，DualSource 的 equal-subset macro nDCG@10 是 0.2142，相比普通 BM25+BGE RRF 的 0.1392 高 0.0750；但最强复现 LameR-MV 是 0.2225，所以我把结论限定为超过合理基础 hybrid baseline，没有声称胜过最强 GAR 或 SOTA。

## 输入、数据和任务边界

| 轨道 | 输入 | 它实际回答的问题 | 不能据此声称 |
| --- | --- | --- | --- |
| M0/M1 产品诊断包 | 自建 reviewed patient-education questions、KnowledgeCard、期望 route/source 和 failure case | 安全门、词面检索、引用契约及一次 recovery 是否按设计工作 | 医学准确率、临床安全率、公开 benchmark 泛化 |
| M5/NFCorpus 历史 sanity | BEIR NFCorpus query、corpus、qrels | 检索组件在公开标准数据上的基本 sanity | R2MED 结果，或当前中文患者教育产品的效果 |
| R2MED DEV | 官方 query/corpus/qrels 的冻结副本；PMC-Treatment 150、PMC-Clinical 114、IIYi-Clinical 129，共 393 queries | 在 DEV 上选生成方法/融合配置、分析候选召回和方法差异 | 用 TEST 继续调参 |
| R2MED public TEST | MedQA-Diag 118、MedXpertQA-Exam 97、Medical-Sciences 88，共 303 queries；三个子集合计 152,439 corpus rows | 对已冻结 pipeline 做一次公开 TEST 评估 | 未触碰 holdout、临床问答正确率、整个 876-query R2MED benchmark 的代表性结论 |

R2MED 原论文描述的是 reasoning-driven medical retrieval：用户表面措辞与支持答案的医学文献可能隔着诊断或机制推理。项目最终协议只使用上述三个 DEV 子集和三个 TEST 子集，并且 TEST 已在早期工作中被访问，因此明确记作 `PUBLIC_BENCHMARK_REUSED`，不是 untouched confirmatory set。

R2MED 每条 query 对应一个候选 corpus 和 qrels。**检索输入**是原生 query text；**ranking 输入**是 query、corpus 和允许的生成视图；**qrels/relevance labels**只由 evaluator 在排名冻结后读取。生成阶段没有 gold answer、正确选项或 gold document。我们沿用上游 corpus unit，不在该 Sprint 自行发明 chunking。

例子用任务形态来理解：一个问题可能用症状或考试题表达，相关文献却以疾病实体、机制、诊断或治疗术语表述；检索器需要跨过这种词汇/语义表示差异。这里的“推理桥”用于构造检索表示，不负责回答题目，也不等价于临床推理能力。

## 产品 Runtime：M0 到 M10.1 的主干

```text
原始 user question
  → input validation
  → deterministic safety gate
      ├─ urgent / prescription → short-circuit / HUMAN_REVIEW
      └─ normal
  → reviewed KnowledgeScope + retrieval
  → Evidence[]（带来源与 provenance）
  → bounded model / Agent proposal
  → runtime policy、citation/claim support verification
  → deterministic materialization 或 abstain
```

M0 的 retrieval 是中文 tokenizer + BM25，并不等于后续 R2MED 实验的 Lucene BM25。M1 最多 2 次 model turn、1 次只读 `search_knowledge(query)` 工具调用；模型不能覆盖 safety gate 或 verifier。后续 M2/M3 加入 evidence policy、claim-first contract 和 deterministic materialization；M4/M7 建立 budget、trace/replay 和 eval 边界；M8 是有硬上限的实验性 Team；M10/M10.1 是 opt-in Context/Memory substrate。生产/默认 profile 仍以 memory-off 的 `m3-bm25-default` 为准，不能把所有 milestone 说成一个默认开启的产品路径。

## R2MED：可复述的检索 Pipeline

```text
R2MED native query q
  ├─ B0: Lucene BM25(q), top-100
  ├─ B1: BGE-large(q), cosine top-100
  ├─ B2: RRF(B0, B1), k=60, weights=[1,1]
  ├─ LameR-MV:
  │    BM25(q) top-10 noisy passages → local Qwen3-8B → generated bridge
  │    → BM25(q), BM25(bridge), BGE(q), BGE(bridge) → weighted RRF
  ├─ Compact CRB-Q:
  │    q → local Qwen3-8B → compact {q,t,e} bridge
  │    → same four retrieval views → equal-weight RRF
  └─ DualSource:
       frozen LameR-MV ranking + frozen Compact CRB ranking → RRF(k=60, λ=.5)
          ↓
       frozen ranked list → evaluator opens qrels → metrics/bootstrap
```

### 生成与检索的固定配置

- Generator：本地 `Qwen3-8B-Q4_K_M.gguf`，revision `6a569868d07d3bd59e8b97fb001bf8c0b254bb20`，SHA-256 `d98cdcbd…5745785`；llama.cpp；只绑定 `127.0.0.1`。
- 每 query / generation arm 一次调用，temperature `0`、reasoning disabled、最多 `256` output tokens、无 retry；TEST 共 303 LameR + 303 CRB 调用，付费 API 调用 0。
- Dense retriever：`BAAI/bge-large-en-v1.5`，revision `d4aa6901d3a41ba39fb536a557fa166f842b0e09`，weights SHA-256 `45e19549…2f64ae7`。
- BM25：Lucene/Pyserini，`k1=.9, b=.4`；不是 SQLite FTS5。
- LameR-MV 四通道各取 top-100，`RRF k=20, weights=[1,2,1,2]`；权重顺序是 BM25(original), BM25(bridge), BGE(original), BGE(bridge)。LameR 的 bridge 由同 query 的原始 BM25 top-10 passage 提示生成。
- Compact CRB-Q 使用相同四类通道，`RRF k=20, weights=[1,1,1,1]`；冻结 schema 为紧凑 `q/t/e`，无效 JSON 固定 fallback 到 original query，不重试。
- DualSource 仅融合两份冻结排名：`1/(60+lamer_rank) + 0.5/(60+crb_rank)`，确定性去重和 tie-break。它不重新调用 generator，也不增加新的文档级 reranker。
- 本轮 TEST 没有 CrossEncoder reranker。之前 DEV 上的 BGE reranker-v2-m3 实验是负迁移，完整结论见 RAG 文档。

R2MED 上游固定为 `R2MED/R2MED@11244a4925a39082967a6c9d38ef01f279c316a5`；prompt-family 的 subset 名称映射有单独记录。这是 pinned upstream 的可审计适配和 reproduction，不宣称 byte-for-byte official reproduction。

## 输出是什么：指标与结果

R2MED 实验输出是每 query 的 ranked document IDs，以及按 qrels 离线评分的检索指标；不是自然语言答案，也不是医生/患者结果。

| 指标 | 在这里衡量什么 | 面试时的读法 |
| --- | --- | --- |
| nDCG@10 | top-10 相关文档排序质量，并对位置折损 | Primary；越靠前的相关文档贡献越大 |
| MRR@10 | 第一个相关文档出现位置的倒数平均 | 首个可用证据出现得是否早 |
| Recall@K | 截止 K 找到的 relevant query-document pairs / 该 query 的全部相关对 | 关注候选覆盖，区分召回与排序 |
| Equal-subset macro | 每个数据子集先对 query 求均值，再对三个子集做不加权平均 | 防止较大子集只凭 query 数量主导 headline |
| Paired bootstrap CI | 同一 query 的两个方法成对重采样，并按 subset 分层 | 描述方法差值不确定性；本例 exploratory，非未触碰测试上的确认性显著性 |

主结果（TEST；equal-subset macro）：

| 方法 | MedQA-Diag | MedXpertQA-Exam | Medical-Sciences | nDCG@10 macro | MRR@10 | Recall@10 | Recall@100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Lucene BM25 | .0255 | .0066 | .1968 | .0763 | .0798 | .1137 | .2973 |
| BGE-large | .0833 | .0410 | .2781 | .1341 | .1347 | .2029 | .4275 |
| BM25 + BGE RRF | .0811 | .0257 | .3109 | .1392 | .1472 | .2010 | .4157 |
| Compact CRB-Q | .1376 | .0766 | .3841 | .1995 | .2205 | .2752 | .5340 |
| DualSource-RRF λ=.5 | .1510 | .0894 | .4023 | .2142 | .2328 | .2904 | **.5791** |
| **LameR-MV** | **.1655** | **.0980** | **.4039** | **.2225** | **.2406** | **.2971** | .5699 |

强而公平的 headline comparator 是普通 BM25+BGE RRF，而非只选最弱 BM25：

- `0.139227 → 0.214245`：绝对 `+0.075018`，相对约 `+53.88%`；paired subset-stratified bootstrap 10,000 次，探索性 95% CI `[+0.05825, +0.09232]`。
- 对 BM25 的差是 `+0.13794`，但不建议将 `+180.8%` 作为主 headline，因为低 baseline 会显得挑对照。
- 对最强 reproduced method LameR-MV：`0.214245 − 0.222471 = −0.008226`；探索性 95% CI `[-0.01974, +0.00318]`，跨 0。因此既不能说 DualSource 胜 LameR，也不能把这一差值讲成 LameR 显著胜出。
- R2MED 的 TEST 是 public/reused。bootstrap 是对该固定样本差值的 exploratory uncertainty，不把它升级成临床显著性或未污染 holdout 的确认结论。

## 结果怎样解释，创新点在哪里

1. **dense 表示带来最大基础台阶**：BGE-large `.1341` 高于 BM25 `.0763`。普通 RRF `.1392` 只比 BGE 多约 `.0051`，说明“加一个融合器”本身不是主要故事。
2. **生成视图与多视图 pipeline 有更大的系统级增益**：LameR-MV 相比普通 RRF 为 `+.08324`，在同一个 benchmark/test 和固定 generator 下表现强。它仍然是公开 LameR 方法的适配，不是我们原创的 LLM retriever。
3. **CRB 单独弱于 LameR，却有真实候选互补性**：Recall@100 是 CRB `.53399`、LameR `.56987`；两者 raw top-100 union 的池上限 `.62045`，最终 DualSource ranked top-100 `.57911`。按 query-document relevance pair 计，LameR-only 95、CRB-only 62、both 430、neither 471。融合比 LameR 多回收约 `.00924` Recall@100，但 top-10 nDCG 仍低于 LameR。
4. **核心诊断是“候选池有互补，不代表融合会把它们排到前面”**。raw union `.62045` 是候选池上限，不是最终系统分数；排名融合只到 `.57911`，仍存在排序损失。
5. **通用 CrossEncoder 不是自动修复**：DEV 上 LameR-MV `.2998`，只用原始 query 做 BGE rerank K=20 后 `.2009`；Recall@100 候选覆盖仍 `.7076`。候选没明显丢失而 nDCG 大跌，说明冻结 reranker 在此设置下重排次序破坏了有效顺序；不能据此推断所有 reranker/所有医疗场景都无效。

这里真正可讲的贡献是：把同 generator 的 GAR baselines 放进固定、可复现的 retrieval protocol；设计 compact structured clinical bridge 并做成同样四视图的成本对照；用 candidate-pool union 和 pair overlap 检查互补性；尝试 DualSource rank fusion 并保留其未超过 strongest GAR 的结论；用 gold isolation、hash 锁定和 pre-qrels 检查保护结果可信度。**不是新检索理论，不是 SOTA，不是临床改善。**

## 可信度、复盘和边界

这次 TEST 的身份错误修正发生在评分前：原 runner 把数字 `query_id` 当成跨子集全局唯一；R2MED 实际是 subset-local ID。预检在 qrels 打开前停止，修正成 `(subset, query_id)` 后核对 query order、generation/ranking artifact hashes、final lock 和冻结代码 hash，再由原 scorer 只评分一次。更改没有触碰生成、ranking、method config 或 metric。记录在 `runs/rag_r2med_final_test/evaluation_preflight_erratum.json`。

关键局限：

- public TEST 已复用；不能叫 untouched holdout，也不主张正式显著性或 leaderboard SOTA。
- 最终 headline 是 retrieval-only。我们没有用这 303 条 query 评估答案正确率、faithfulness、拒答、医疗安全或患者 outcome。
- 仅三个 TEST subset；R2MED 原始总体规模和任务面更广，不能推广到所有医学 retrieval。
- BGE-large/Lucene 的具体 tokenizer、源文档粒度、上游重复 ID 处理、prompt family adaptation 都是实验 identity 的一部分；不要擅自称官方逐字复现。
- Compact CRB 7/303 输出 schema 无效，按冻结策略 fallback 到原 query；LameR 16/303 到达输出 token cap 但作为有效生成照用。没有 TEST 重试或修 prompt。
- DualSource 在 DEV 上仅 `.002117` 高于 LameR，未过 strongest-method DEV gate；随后 TEST 的用途明确收窄为 frozen pipeline 对 basic baselines 的评估。TEST 没用于继续调参。
- BGE reranker 的负迁移来自一个冻结设置，不能推广成 reranker 家族定理。

当前 R2MED 结论已 closeout：不要在看过 TEST 后继续调 λ、prompt、RRF、top-k、模型或 reranker。未来要继续应开新的方法/benchmark protocol，而不是把本 TEST 变成开发集。

## 同项目其他方向：证据等级不能混

| 方向 | 当前完成度 | 可以讲 | 不可以讲 |
| --- | --- | --- | --- |
| RAG / R2MED | 冻结 public/reused TEST retrieval evaluation | 对普通 hybrid baseline 有明确 positive delta；与 LameR 的差距如实披露 | 超过最强 GAR、SOTA、临床准确率 |
| Memory / Context | M10/M10.1 实现和 deterministic synthetic suite | session/memory/context 边界、显式写策略、projection contract | LongMemEval/公开 benchmark 提升、患者长期记忆已验证 |
| Multi-Agent | M8 有实现、v2 frozen 12-case × 3-trial diagnostic | bounded star-team 工程；cross-source slice 有提升但整体更贵且较弱 | 通用 multi-agent 有效、并行 team 提升总体质量/延迟 |
| RL / post-training | M11 future，未启动 | 能讲理论和一个待验证研究设想 | Health-Copilot 做过 SFT/DPO/PPO/GRPO/GSPO 训练 |

按模块准备：[RAG 项目追问](/projects/health-copilot/01-rag项目面试追问/)、[Memory 项目追问](/projects/health-copilot/02-memory项目面试追问/)、[Multi-Agent 项目追问](/projects/health-copilot/03-multi-agent项目面试追问/)、[RL 项目追问](/projects/health-copilot/04-rl项目面试追问/)；概念公式放在[通用 Agent/LLM 八股](/projects/health-copilot/05-agent-llm通用八股/)。

## 证据入口

- R2MED final report：`Health-Copilot/docs/research/r2med_final_public_test.md`
- Machine-readable scores and confidence intervals：`Health-Copilot/runs/rag_r2med_final_test/test_report.json`
- Frozen TEST lock, model/config/data identities：`Health-Copilot/runs/rag_r2med_final_test/final_eval_lock.json`
- Candidate complementarity：`Health-Copilot/runs/rag_r2med_final_test/candidate_analysis.json`
- Pre-qrels erratum：`Health-Copilot/runs/rag_r2med_final_test/evaluation_preflight_erratum.json`
- Reranker DEV negative result：`Health-Copilot/docs/research/r2med_candidate_reranking.md`
- Multi-Agent closeout：`Health-Copilot/docs/m8_empirical_v2_closeout.md`
- Context/Memory closeout：`Health-Copilot/docs/m10_1_context_closeout.md` 和 `docs/m10_context_memory.md`

本页是项目地图和整体叙事；RAG 文档负责具体检索问答、追问和必背数字；Memory/Multi-Agent/RL 文档各讲一条经历边界；通用八股只讲跨项目原理。
