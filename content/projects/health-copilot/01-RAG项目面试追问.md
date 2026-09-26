---
schema: bubblevan/v1
id: project-health-copilot-01-rag-interview
content_kind: project
title: Health-Copilot：RAG 检索项目与面试追问
linkTitle: 01 · RAG
weight: 10
date: 2026-09-27
updated: 2026-09-27
status: draft
visibility: public
projects:
  - project-health-copilot
summary: R2MED 医疗检索实验的输入、数据边界、pipeline、baseline、指标、结果解释、论文阅读和面试追问；明确区分正向基础 baseline 与未胜过 LameR 的边界。
topics:
  - rag
  - information-retrieval
  - health-ai
  - interview
---

> **这篇是项目专属面试手册。** BM25、dense retrieval、RRF 和指标的通用原理放在[Agent/LLM 通用八股](/projects/health-copilot/05-agent-llm通用八股/)；[项目总览](/projects/health-copilot/)讲产品 Runtime 与 RAG research 的整体关系。这里重点回答：我在 R2MED 上究竟做了什么、如何证明、哪些话不能说。

## 先背这段：60 秒项目回答

> 我在 Health-Copilot 里做了两条相关但分开的 RAG 工作。产品主线是 safety-gated evidence workflow；简历量化结果来自另一条 retrieval-only 研究线。我固定 R2MED 的公开 query/corpus 和 split，用本地 Qwen3-8B 生成 retrieval bridge，对照 Lucene BM25、BGE-large、普通 BM25+BGE RRF，以及复现适配的 LameR-MV。然后把自己设计的 compact clinical bridge CRB 与 LameR 做 DualSource rank fusion。最终在复用的 public TEST 303 个 query 上，equal-subset macro nDCG@10 从普通 hybrid RRF 的 .1392 到 .2142，绝对增加 .0750，探索性 paired 95% CI 是 [.0582,.0923]。但最强复现 LameR-MV 是 .2225，高于 DualSource，所以我只说超过 basic hybrid baseline，不说胜过最强 GAR、SOTA 或临床准确率。实验是 retrieval-only，不生成最终医疗答案。

这段要自然说完，不要把限制藏到面试官抓出来才承认。结果有提升，边界讲清，可信度反而更高。

## 项目中 RAG 的两种含义

### 产品 Runtime：证据问答

M0 主链是：

```text
患者教育问题
 → 校验与 deterministic safety gate
 → reviewed KnowledgeCard 上的中文 BM25
 → Evidence[]
 → generator 草拟回答
 → runtime 校验 citation IDs
 → materialize Citation / abstain
```

urgent / prescription 类输入先短路；空证据、模型异常、缺失/伪造 citation 等走 fail-closed。M1 加的是一次受限 `search_knowledge(query)` recovery，不是本次 R2MED pipeline。M0 的自建 80-case evaluation 和 M1 的 12-case focused diagnostic 只能作为产品契约/故障诊断证据，不是这次简历上的公开 R2MED 分数。

### R2MED Research：只评 retrieval

本实验输入为公开 benchmark query 和各自 corpus；输出为按 document ID 排列的 ranking。它**不**把 query 交给最终回答 generator，不评答案正确率、医学安全性、faithfulness 或患者 outcome。

| Split | Subsets | Query 数 | 用途 |
| --- | --- | ---: | --- |
| DEV | PMC-Treatment / PMC-Clinical / IIYi-Clinical | 150 / 114 / 129 = 393 | 生成方法和 RRF 配置选择、诊断 |
| public TEST | MedQA-Diag / MedXpertQA-Exam / Medical-Sciences | 118 / 97 / 88 = 303 | 冻结 pipeline 的最终 retrieval 评分 |

R2MED 总体 benchmark 比本实验使用的 6 个 subset 更广；不要说本实验覆盖官方整个 benchmark。并且这 303 条 TEST 以前已经被访问过，所以协议标记 `PUBLIC_BENCHMARK_REUSED`，不是 untouched holdout。

TEST 的 query/corpus 在锁中按 revision 与 SHA-256 固定。三份 TEST corpus 分别有 56,250、61,379、34,810 行。实验沿用上游 corpus unit，没有在这轮另外做 chunking。原生 query text 是检索问题；qrels、relevance label 和 gold document ID 只在 ranking artifacts 冻结以后供 evaluator 使用。若选项本来属于 query 原文，则保持 benchmark 输入；不额外读取正确选项。

上游 prompt family 的数据集别名映射固定为：`PMC-Treatment → PMC-Treat`、`PMC-Clinical → PMCPatients`、`IIYi-Clinical → IIYiPatients-EN`、`MedQA-Diag → MedQA-Diag`、`MedXpertQA-Exam → MedXpertQA-Exam`、`Medical-Sciences → Stack-Medical`。这是适配 pinned upstream prompt family 的命名映射，不是 byte-for-byte official reproduction。

Corpus duplicate IDs 也属于数据处理身份：BM25 延续 pinned upstream 行为，先索引各 row 再按 document ID 折叠 scored result；dense corpus 使用 unique-ID view。相同 ID 的重复文本行保留在 BM25 输入中，不同文本则拒绝；原始 JSONL 不改写。

## Pipeline：从 query 到 ranking

### 0. 固定数据与 source identity

- Upstream：`R2MED/R2MED@11244a4925a39082967a6c9d38ef01f279c316a5`。
- query/corpus 使用独立 source revision 和 SHA；prompt family 的数据集别名映射有单独文档。
- Generation / ranking phase 只能读 query、corpus，以及 LameR 的同 query BM25 top-10 passage；禁止读 qrels、答案、正确选项和 gold docs。
- evaluator 是 qrels 的唯一消费者。各 subset 的 `query_id` 是 subset-local，因此全局身份键必须是 `(subset, query_id)`。

### 1. Baseline 检索

| ID | Pipeline | 固定点 |
| --- | --- | --- |
| B0 | Original query → Lucene BM25 | `k1=.9, b=.4, top-100`，Pyserini/Lucene；不是 SQLite FTS5 |
| B1 | Original query → BGE-large | `BAAI/bge-large-en-v1.5` pinned revision；cosine top-100 |
| B2 | B0 + B1 → ordinary RRF | 每路 top-100，`k=60`、`weights=[1,1]`，输出 top-100 |

BM25 与 BGE 是互补类型：前者是精确词项匹配，后者是稠密语义表示。B2 是非常合理的 basic hybrid baseline；比较只挑 BM25 会夸大效果。

### 2. Same-generator generation-based retrieval

所有生成方法统一本地 generator：Qwen3-8B Q4_K_M GGUF，SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`；llama.cpp，temperature 0、reasoning 关闭、256 输出 token、每 query 每方法一次、不 retry。BGE-large revision 为 `d4aa6901d3a41ba39fb536a557fa166f842b0e09`，weights SHA-256 `45e1954914e29bd74080e6c1510165274ff5279421c89f76c418878732f64ae7`。

**LameR-MV（公开方法的适配）**：

```text
original query
 → upstream-compatible BM25 top-10 passages（noisy，不用 qrels 标 relevance）
 → Qwen3-8B 合成 retrieval bridge passage
 → 四路各取 top-100：
      BM25(original query)
      BM25(LameR bridge)
      BGE(original query)
      BGE(LameR bridge)
 → weighted RRF: k=20, weights=[1,2,1,2]
```

注意 attribution：LameR 是原论文方法，不是我的原创算法；本项目做了 pinned upstream prompt family mapping、同 generator 重跑、四路 retrieval 适配和 artifact identity。不能说 byte-for-byte official reproduction，应该说 “pinned-upstream, same-generator reproduction/adaptation”。

**Compact CRB-Q（本项目设计的 structured bridge）**：

```text
original query
 → Qwen3-8B 产生紧凑 q/t/e bridge
      q: canonical query
      t: clinically useful key terms
      e: short pseudo-evidence text
 → 相同类型的四路 top-100 retrieval
 → uniform RRF: k=20, weights=[1,1,1,1]
```

CRB 想解决的不是“模型先答题”，而是 query 的表面表达与医学文献表述之间的 representation gap。生成内容是 retrieval aid，不是事实证据。最终冻结 schema 用紧凑 q/t/e；七条 invalid JSON 按预定策略 fallback 到 original query，没有第二次生成。

**DualSource-RRF（系统级融合，不是新 rank-learning 算法）**：

```text
冻结的 LameR-MV top-100 ranking
                    + → RRF(k=60, LameR weight=1, CRB weight=.5)
冻结的 Compact CRB-Q top-100 ranking
```

候选按 document ID 去重；rank 缺失置后，并使用锁定 tie-break。它只融合两个已经完成的排序，不看 qrels、不重新生成、不经过 CrossEncoder。

## 指标：为什么看这些数

本项目的公式通用版在[八股文档的 Retrieval Metrics](/projects/health-copilot/05-agent-llm通用八股/)；这里记住这次实验的操作定义：

- **nDCG@10（primary）**：对前 10 名的 graded relevance 做位置折损，再除以理想排序的 DCG。更重视高相关文档是否排在前面。
- **MRR@10**：每个 query 的第一个 relevant document 出现在 rank `r≤10` 时记 `1/r`，否则记 0，再平均。看“第一个可用证据”排得早不早。
- **Recall@K**：前 K 名找回的 relevant query-document pairs 数 / 该 query 全部 relevant pairs 数，再平均。看 candidate coverage，而不完全看排序质量。
- **Equal-subset macro**：先分别在 MedQA-Diag、MedXpertQA-Exam、Medical-Sciences 内平均，再把 3 个均值等权平均。不是把 303 个 query 全部混一起的 query-count-weighted micro average。
- **Paired, subset-stratified bootstrap**：对同一批 query 的 A/B 分数成对重采样，按 subset 分层，10,000 resamples、seed `20260926`。区间是公开复用 TEST 上的探索性不确定性描述，不是独立确认试验。

Recall@100 与 raw pool union 用来诊断 candidate generation 是否互补；raw union 的召回是候选池天花板，不可冒充系统最终 Recall 或 nDCG。

## 实验结果矩阵

所有 nDCG 是 TEST 的 equal-subset macro 和各子集 nDCG；所有 recall/MRR 是 equal-subset macro。

| Method | MedQA-Diag | MedXpertQA-Exam | Medical-Sciences | Macro nDCG@10 | MRR@10 | R@5 | R@10 | R@50 | R@100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | .0255 | .0066 | .1968 | .0763 | .0798 | .0714 | .1137 | .2442 | .2973 |
| BGE-large | .0833 | .0410 | .2781 | .1341 | .1347 | .1441 | .2029 | .3390 | .4275 |
| BM25+BGE RRF | .0811 | .0257 | .3109 | .1392 | .1472 | .1392 | .2010 | .3530 | .4157 |
| Compact CRB-Q | .1376 | .0766 | .3841 | .1995 | .2205 | .1980 | .2752 | .4517 | .5340 |
| DualSource λ=.5 | .1510 | .0894 | .4023 | .2142 | .2328 | .2064 | .2904 | .4785 | **.5791** |
| **LameR-MV** | **.1655** | **.0980** | **.4039** | **.2225** | **.2406** | **.2209** | **.2971** | **.4971** | .5699 |

### 三个必须会说的对比

| Comparison | Difference in macro nDCG@10 | Exploratory paired 95% CI | Interpretation |
| --- | ---: | ---: | --- |
| DualSource − BM25 | +.13794 | `[+.11446, +.16316]` | 大幅高于 sparse baseline；不是 headline 的唯一对照 |
| DualSource − ordinary BM25+BGE RRF | **+.07502** | **`[+.05825, +.09232]`** | 可支持 public basic-hybrid baseline improvement，绝对 +.0750 / 相对 +53.88% |
| DualSource − LameR-MV | −.00823 | `[−.01974, +.00318]` | point score 更低且 CI 跨 0；不能说超过 strongest reproduced GAR，也不能说差值显著 |
| LameR-MV − ordinary RRF | +.08324 | `[+.06397, +.10305]` | LameR multi-view pipeline 是本次最强 frozen arm |

**推荐简历 bullet**：

> 在复用的 R2MED public TEST（303 queries）上，将冻结的 generation-augmented DualSource retrieval 的 equal-subset macro nDCG@10 从 ordinary BM25+BGE RRF 的 **0.139 提升到 0.214（+0.075 absolute / +53.9% relative）**；exploratory paired 95% CI `[+0.058, +0.092]`。同时保留 strongest reproduced LameR-MV **0.222**，不声称超过最强 GAR。

想更短可把 CI 放面试时展开，但要保留 `public/reused TEST` 和 `未超过 LameR` 的事实。

## 从结果推原因：方法论复盘

### 1. 为什么普通 RRF 只比 BGE 稍高？

BGE `.1341`，普通 RRF `.1392`，仅约 `+.0051`。这说明“BM25 与 dense 两路一融合”不是天然大幅提升：在当前三子集上，BM25 的额外候选/排序信号可能有限，也可能和 dense 有重叠。RRF 的 rank-only 设计减少了原始 score scale 不可比问题，但不会创造不存在的 relevant candidates。

### 2. 为什么 LameR-MV 是强 baseline？

它先用 BM25 top-10 给生成器 in-domain corpus style/noisy candidates，再用生成 bridge 产生第二个 sparse 和 dense view。R2MED 的核心难点正是 query 与文献表述之间的差异；额外的生成 view 可能扩展术语/表述覆盖，multi-view 同时保留原 query。该解释符合方法结构和数据，但 TEST 的整体 delta 不能单独证明是哪一个子组件造成收益；需要同通道数的 DEV 对照及消融才可分解归因。

### 3. CRB 为什么有互补性，却没赢 LameR？

| Candidate view | Macro Recall@100 |
| --- | ---: |
| LameR-MV top-100 | .56987 |
| Compact CRB-Q top-100 | .53399 |
| Raw candidate union pool | .62045 |
| DualSource ranked top-100 | .57911 |

相关 query-document pairs 中，LameR-only `95`，CRB-only `62`，both `430`，neither `471`。所以 CRB 不是纯重复：它引入了一部分 LameR 未召回的相关文档。DualSource 最终把 Recall@100 从 `.56987` 提到 `.57911`（约 `+.00924`），但没把 candidate complementarity 完整转成高位 nDCG；新候选里可能有噪声，也可能固定 λ 的 RRF 没把最有用的 CRB-only 文档放到 top 10。这个结论是“候选互补存在、排序利用不足”，不是“CRB 已经优于 LameR”。

### 4. 为什么 CrossEncoder reranker 反而伤害？

在冻结 DEV 设置里，LameR-MV 的 macro nDCG@10 `.2998`，用 BGE-reranker-v2-m3 对 top-20 重排后 `.2009`，但 Recall@100 仍 `.7076`。它主要伤了 top-rank order，而非候选池覆盖。推测 cross-encoder 看到的是原始 query + 文档，未看到生成 bridge/候选 provenance；这可能与 reasoning-driven query mismatch 不匹配，但只是解释假设。模型加载和 score direction 已用模型卡示例 sanity check。结论限定为“这个冻结模型/输入/截断/候选配置发生负迁移”，不泛化成 CrossEncoder 无效。它不是最终 TEST pipeline 的组件。

## 方法的“创新点”如何说才准确

不要说“发明 CRB 算法并超过 SOTA”。更可信的回答：

1. **研究问题具体**：把优化点从单纯 rerank 往前移到 query representation / reasoning bridge。
2. **对照更公平**：generation-based methods 使用同一个本地 generator、调用次数和输出预算；多视图方法采用相同 retrieval channels 和声明好的 fusion grid。
3. **CRB 是自己的结构化适配**：让生成器产出紧凑 query、clinical terms、pseudo-evidence，而不是直接作答；无效结构按预先固定 fallback。
4. **测试的是互补候选能否融合**：保留 LameR 与 CRB 的候选来源，比较 raw union pool ceiling 和最终融合排名，解释 Recall 与 nDCG 差异。
5. **可信度工程也属于贡献**：gold isolation、pinned upstream/model/data hashes、generation manifests、frozen lock、qrels 单点边界、paired uncertainty 和 pre-qrels erratum 都可审计。

这些是实验设计、工程 adaptation 和误差分析上的贡献，不等于新颖的学习算法，也没有胜过最强复现方法。

## 高频面试追问与答法

### “你这个到底是不是 RAG？最终回答效果有测吗？”

**答**：这条 R2MED 实验严格说是 RAG pipeline 的 retrieval stage evaluation，不是 end-to-end QA evaluation。它输出排名和检索指标，没有让答案模型对 303 题作答，因此我不会用它证明 answer correctness、grounding 或临床效果。产品 Runtime 的 Evidence RAG 是另外一条线。

### “你说提升 53.9%，是不是挑了最弱 baseline？”

**答**：主 comparator 不是 BM25，而是普通 BM25+BGE RRF：`.1392 → .2142`，绝对 `+.0750`。同时我报告最强 reproduced LameR-MV `.2225`；DualSource 没有赢它，所以 headline 明确限定为超过 basic hybrid baseline。

### “那你是不是在测试集上调出来的？”

**答**：不是。方法/权重先在 393-query DEV 上选择并记录 lock。DualSource 相对 LameR 的 DEV 优势只有 `.002117`，没通过 strongest-method gate。随后 final TEST 的问题被显式收窄为 frozen pipelines 是否超过 basic baselines；TEST 没用于改 prompt、λ、RRF 或模型。TEST 是 public/reused，不是 untouched，报告对此有披露。

### “为什么 DEV 没过最强方法 gate，后面还跑 TEST？”

**答**：它没有被当作 confirmatory test 来宣称打败 LameR。后续单独批准的 final evaluation 重新锁定目标，只问固定系统相对 BM25/普通 hybrid baseline 的公开 benchmark 表现；lock 里保留 `new_method_dev_win=false`，并且 final report 明示 LameR 仍然更高。若把这次 TEST 说成预注册的 strongest-GAR 确认实验，那就不准确。

### “RRF 的权重也调了吧？会不会只是多跑了几路？”

**答**：DEV protocol 对各 multi-view 方法使用同一预声明 grid 和四条 top-100 channel；按 macro nDCG@10 选择，并在 TEST 锁定。ordinary RRF 是双通道 basic baseline；LameR-MV 与 CRB-MV 的比较有共同四路设定。DualSource 是两个冻结排名再做第二层融合，所以它和单通道方法不是等成本比较；我把它定位为融合适配，并用最强 LameR-MV 作为主要强方法参照，而不是把所有增益归给 CRB。

### “qrels 有没有泄漏进生成或排序？”

**答**：生成函数和 ranking phase 接口不接 qrels、gold IDs、答案或 relevance label。LameR 只看到同 query 的 BM25 top-10 原始候选，不知道其中谁相关。ranking artifacts/hash 冻结以后，单独的 evaluator 才读取 qrels。这个数据边界在代码与 preflight 中验证。

### “最终结果里有什么负面或反直觉发现？”

**答**：首先普通 RRF 只比 BGE 略高。其次 CRB 自己弱于 LameR，但提供一部分新相关候选；简单 DualSource 能增加 Recall@100，却没提高 nDCG@10。最后 BGE cross-encoder reranker 在 DEV 上大幅降低 nDCG，虽然 Recall@100 不变。这说明系统问题不只是“多召回一些”，更难的是如何把 reasoning-relevant candidates 排到前面。

### “结果能叫 statistically significant 吗？”

**答**：我会给 paired subset-stratified bootstrap 的探索性 95% interval。DualSource 对 ordinary RRF 的区间下界高于 0，但样本是 public/reused TEST，且这是同一固定数据上的不确定性估计，不应包装成独立确认性显著性或临床意义。对 LameR 的区间跨 0。

### “为什么发生过 TEST ID 修正？这不是改测试集吗？”

**答**：原始 bug 是 validation guard 错把 subset-local 的数字 ID 当成全局唯一，实际唯一键应为 `(subset, query_id)`。首次 preflight 在打开 qrels 前失败。erratum 后只修 identity scope，重新核验锁、query order、全部 generation/ranking hashes 和 frozen code；没有变更数据、排名、方法、metric 或 scorer，再从冻结排名执行一次原 qrels scoring。记录了 pre-qrels 状态，不能把它说成“看过结果再修方法”。

### “如果让你继续做，会怎么改？”

**答**：我不会继续用这个 public TEST 调参。若开启新 protocol，会先在新的独立数据/holdout 上问：如何用 query-conditioned 或 learning-to-rank fusion 利用候选来源及其 bridge；或者让 reranker 读到合理的 query/bridge representation；还要单独做 CRB/LameR candidate union 与 ranking loss 消融。先用 DEV 验证候选质量和 attribution，再冻结到新的测试集。当前 Sprint 已按 stop rule closeout，这些是 future work，不是已完成工作。

## 必须硬背的事实卡

```text
任务：R2MED medical information retrieval，不是 end-to-end medical QA
DEV：393 = 150 + 114 + 129
TEST：303 = 118 + 97 + 88；PUBLIC_BENCHMARK_REUSED
主指标：equal-subset macro nDCG@10
BM25：Lucene/Pyserini，k1=.9，b=.4
BGE：bge-large-en-v1.5，pinned revision
Generator：Qwen3-8B Q4_K_M，temperature 0，reasoning off，256 tokens，one call/query/method
ordinary BM25+BGE RRF：.1392
Compact CRB-Q：.1995
DualSource λ=.5：.2142
LameR-MV（最强复现）：.2225
DualSource − ordinary RRF：+.07502，exploratory CI [.05825,.09232]
DualSource − LameR：−.00823，CI [−.01974,.00318]，crosses zero
Dual R@100 .57911；LameR .56987；raw pool union .62045
结论：超过 basic hybrid baseline；没有胜过 strongest GAR；非 SOTA、非临床验证
```

## 精读论文与顺序

先读本项目所依赖的方法原文，再读 retrieval 基础。每篇至少回答“输入是什么、生成/索引什么、检索器是什么、评测如何做、什么条件下会失败”。

1. **必须精读：R2MED** — [R2MED: A Benchmark for Reasoning-Driven Medical Retrieval](https://arxiv.org/abs/2505.14558)。读任务定义、query/document mismatch 例子、子集构成、baselines 和作者对 reasoning methods 的分析。重点比较“论文全 benchmark”与“本项目 6 subsets / TEST 303”的范围差异。
2. **必须精读：LameR** — [Retrieval-Augmented Retrieval: Large Language Models are Strong Zero-Shot Retriever](https://aclanthology.org/2024.findings-acl.943/)。看它为何先取 in-corpus candidates、LLM 如何用 candidate context 生成 retrieval augmentation，以及为什么 BM25 是透明的第一阶段。面试归因时记得这是公开方法。
3. **必须精读：HyDE** — [Precise Zero-Shot Dense Retrieval without Relevance Labels](https://arxiv.org/abs/2212.10496)。掌握 hypothetical document 是“虚构查询视图”而不是证据，dense encoder 如何把它落回真实 corpus neighborhood。
4. **必须精读：Query2doc** — [Query2doc: Query Expansion with Large Language Models](https://arxiv.org/abs/2303.07678)。看 few-shot pseudo-document 怎样扩展 sparse/dense query；对照本实验 upstream semantics，不能把不同 prompt/retrieval 拼法都叫复现。
5. **方法基础：RRF** — [Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)。读公式和 `k` 的作用；理解 rank-level fusion 不要求原始 score 可比，但不会自动提高 candidate coverage。
6. **检索 baseline：BM25 / DPR / BEIR** — [BM25 review](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf)、[Dense Passage Retrieval](https://arxiv.org/abs/2004.04906)、[BEIR](https://arxiv.org/abs/2104.08663)。BM25 读 saturation/length normalization；DPR 看 dual encoder；BEIR 看 zero-shot heterogeneous retrieval evaluation 的意义与局限。
7. **RAG 概念：Lewis et al.** — [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)。它用于理解 parametric/non-parametric memory 与 generation；不要误说本次 R2MED retrieval-only 实验复现了 end-to-end RAG generation。

源码/报告建议按顺序看：`docs/research/r2med_final_public_test.md` → `runs/rag_r2med_final_test/final_eval_lock.json` → `test_report.json` → `candidate_analysis.json` → `evaluation_preflight_erratum.json` → `docs/research/r2med_candidate_reranking.md`。项目总览页有其他 Runtime 线索，不要把两条 pipeline 混为一条。
