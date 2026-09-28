---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-architecture
content_kind: docs
title: "Research Intelligence 数据层架构（M0–M3）"
date: 2026-09-28T00:00:00+08:00
status: draft
visibility: public
summary: 统一研究数据层、可恢复的来源采集、证据图、信源发现与多路检索。
topics: [research-intelligence, source-discovery, agent]
aliases: []
authors: [bubblevan]
---

# 目标与边界

Research Intelligence 是统一研究数据层，不是第二套 PKB。现有 scripts/pkb/capture.py 仍负责低摩擦 capture 和原有 promotion；PKB bridge 只读消费 type_hint 为 link 或 bookmark 的 capture。XHS bridge 只接受现有 reader 产出的脱敏 JSON，不获取页面。M1 增加 RSS/Atom 与 GitHub Releases 两种 pull connector；M2 从已接受的来源和 Artifact 出发，沿有公开证据的关系发现待人工复核的 Source Candidate。

来源适配器可继续承接 RSS/Atom、博客、arXiv/OpenReview、GitHub、Hugging Face、技术报告和讨论社区。当前实现 RSS/Atom、GitHub Releases，以及现有 PKB/XHS 的手动导入。

## 当前边界

当前阶段不训练 embedding model，不引入 vector database，不实现 LLM ranking、learning-to-rank 或 contextual bandit，不建立推荐 dashboard，不运行 daemon/cron，不增加 Zhihu、X、Discord 或 Telegram connector，不改变 XHS reader 行为，也不实现广告竞价。M2 的自动发现输出是带证据路径的 Source Candidate，不是个性化推荐；它不会关注、订阅、激活候选或修改 Source catalog。身份解析只使用本地精确别名，或 provider 明确给出的 DOI、OpenAlex、Semantic Scholar、ORCID、ROR、GitHub 数字 ID 等精确等价关系；相似标题、姓名和语义相似度不会合并实体。

## 端到端数据流

Source → Acquisition → Observation → Canonicalization → Artifact / Entity Graph → Auditable Source Candidates → Human Review → Source

每一层的职责：

- **Source** 是作者、策展人、实验室、出版物、订阅源、社区、平台或仓库的稳定身份。Source 只保存公开标识和 connector 配置，不保存 Cookie、session 或 xsec_token。
- **Acquisition** 是可替换的输入适配器。XHS reader 只提供已有脱敏 JSON；PKB bridge 只读 link/bookmark capture。抓取状态和浏览器运行时状态不进入知识记录。
- **Observation** 保留某 Source 在某一时刻公开、推荐或提到内容的证据，以及 retrieval mode、evidence level、source URL 和 collector。平台对象 ID 是同一帖重复读取时的首选 identity。
- **Canonicalization** 用确定性的标识优先级把 Observation 中的显式链接和标识符折叠成 Artifact candidate。无法确认的内容留在 candidate 状态，不依靠模糊模型补全。
- **Artifact / Entity** 是去重后的研究对象和参与者。M2 使用 JSONL `GraphEdge` 保存关系、观察时间和 evidence；图索引只是可以删除重建的本地派生视图。
- **Source Candidate** 是从已认可 Source / Artifact 沿公开证据图发现的待审对象。每个候选携带 seed Source、完整关系路径、Observation 或 provider evidence、跳数和逐项支持信号。M2 不做最终 feed ranking。
- **Feedback** 保留 impression、open、save、dismiss、deep_read、verify、cite、implement 和 promote_to_hugo 等研究价值信号，不把点击率当作唯一目标。

## 契约、身份和存储

schemas/intelligence 定义 source、observation、artifact、artifact alias、entity、entity alias、graph edge、source candidate、feedback 和 topic。scripts/intelligence/ids.py 使用 namespace、规范化 identity 和 SHA-256 确定性生成 src、obs、art、ent、fb、edge 和 candidate ID；topic ID 使用可读 slug。同一 identity 重放不会生成随机 ID。

Artifact identity 优先级为 DOI → arXiv ID → GitHub owner/repo → Hugging Face 类型与 repo ID → canonical URL → 规范化标题指纹。Hugging Face 的 model、dataset、space 使用不同 identity 和 canonical URL。URL 规范化复用 scripts/pkb/normalize_url.py 并先移除私密查询参数。Artifact 字段冲突进入 field_conflicts，标识符不会静默覆盖。

M2 的 `graph_predicates.yaml` 限制 canonical predicate 与方向。相同 subject / predicate / object 只有一个确定性 edge ID；来自不同 Observation 或 provider 的 distinct evidence 合并到该 Edge，并保留 first / last observed 时间。持久化 edge 只接受 `exact_provider_metadata` 或 `explicit_source_link`。图片 OCR、文本抽取、相似度和 LLM 推断只能留在 candidate 层。`authored` 只作为反向查询投影，不与 `authored_by` 双写。

Entity exact alias 使用 Semantic Scholar author ID、OpenAlex author / institution / source ID、ORCID、ROR、ISSN 和 GitHub numeric user / organization ID。姓名不是 alias。只有同一份 provider exact record 明确同时给出多个 ID 时才建立等价映射；Entity redirect 做 cycle check 和 path compression，历史 GraphEdge 不批量重写，查询时解析 canonical ID。

data/intelligence/topics.yaml 提供 11 个研究顶层主题和 agent、search、memory、RAG、OPD、verifier、reward、multi-agent、inference-serving 等 cross-cutting leaf。确定性 mapper 只映射 topic_id、名称和别名；来源原始标签单独放在 Observation.native_tags，未知标签不猜 topic。Leaf 可以有多个 parents；Observation 和 Artifact 的 topics 本身也是多标签。每个 artifact candidate 保存自己的 mention evidence 与 origin。

本地 JSONL 写入 data/intelligence/events/，此目录默认 gitignored，因为观察正文可能包含捕获内容。Observation 与 Feedback 按月份写入，仅第一次写入同一 ID；sources、artifacts、entities JSONL 是按 ID 排序的 materialized index，upsert 通过临时文件加原子替换。重复 Observation 只保留一个 ID；不同 Observation 提及相同标识时共享 Artifact。

时间字段语义固定如下：`Observation.published_at` 是来源报告的发布时间；`Observation.observed_at` 是本地首次成功摄取该 Observation 的时间，重复摄取相同 ID 不会改写它；`ConnectorState.last_attempt_at` 是最近一次轮询尝试时间；`ConnectorState.last_success_at` 是最近一次成功完成的 connector poll 时间。

当前 M1/M2 的 `JsonlStore`、`ArtifactAliases` 和 `ConnectorStateStore` 都假定每个 store directory 只有一个 writer。两台机器不得同时写入同一个 store directory。临时文件加原子替换只能保证 crash-safe file replacement，不提供并发 writer 序列化；SQLite 不属于本次实现。Collector 多机同步需要后续 deployment milestone 单独设计。

## M1 connector runtime

Connector protocol 与 registry 位于 scripts/intelligence/connectors/。RSS/Atom 使用 feedparser；GitHub Releases 只读取已发布 release。两个 pull connector 共用有超时、条件请求和有界重试的 HTTP transport。每次运行是 one-shot；没有后台调度器。

Source 配置在 data/intelligence/sources.yaml，目前只放四个 RSS/Atom 和三个 GitHub 仓库 seed。运行状态放在 gitignored 的 data/intelligence/runtime/connectors/<source_id>.json，不进入 Source 记录。状态文件原子替换并 fsync。运行顺序是抓取、写入 Observation 和 Artifact、再原子推进 checkpoint；写入后 checkpoint 失败时，确定性 Observation ID 允许安全重放。

`run-all` 按 source 隔离 connector fetch 失败和单个 source 的隐私记录拒绝，并继续运行后续 source；输出 `sources_total`、`succeeded`、`failed` 和逐 source `results`，只要有 source 失败，命令就以非零状态退出。source 结果中的 `fetched` 表示本次响应处理的 Observation 数，包含已存在的重复项，不表示新发现。`new_observations` 和 `duplicate_observations` 分别报告首次写入数和重复数；`artifacts_touched` 是本轮 upsert 的不同 Artifact 数；`pages` 是 connector 报告的已处理页数。Source catalog、JSONL store、schema、checkpoint 损坏及精确身份不变量错误仍作为全局错误中止。

HTTP 429 的 `Retry-After` 与 GitHub exhausted rate limit（403、`X-RateLimit-Remaining: 0`）的 `X-RateLimit-Reset` 会直接决定该 source 的 `backoff_until`。timeout、5xx 和其他普通 connector failure 使用有界 exponential backoff。错误汇总仅输出安全的错误类别和通用说明，不保存 provider 异常正文、请求 URL 或凭据。

命令示例：

```powershell
python -m pip install -r requirements-intelligence.txt
python -m scripts.intelligence.cli connectors
python -m scripts.intelligence.cli sources
python -m scripts.intelligence.cli run-source <source_id>
python -m scripts.intelligence.cli run-all --once
python -m scripts.intelligence.cli connector-state <source_id>
python -m scripts.intelligence.cli resolve-artifact <artifact_id>
```

`GITHUB_TOKEN` 可从环境变量提供；它不进入 source catalog、checkpoint、Observation、Artifact 或诊断输出。Semantic Scholar 是可选增强：只对显式 DOI/arXiv 请求 Academic Graph fields，登记 DOI、arXiv、Semantic Scholar、OpenAlex 和 URL alias。`smoke semantic-scholar --arxiv ...` 是唯一默认关闭的 live smoke 命令；离线测试使用固定 fixture 与 fake transport。

Artifact alias 与 `artifact_redirects.jsonl` 保留精确身份映射。redirect 解析会检测环并压缩路径；Observation 和 Feedback 的历史 ID 不重写。仅 Semantic Scholar provider equivalence 可以把不同精确标识的 Artifact 指向一个 canonical artifact；标题相似不会触发合并。

## M2 graph 与 source discovery

`graph-backfill` 只从本地 Sources、Observations、Artifacts 和 topic catalog 建图，不联网。Observation → Artifact 只在 Observation 明确包含链接，或 GitHub Releases connector 的 `api_metadata/repository` 明确给出精确仓库 ID 时形成 `Source --mentions--> Artifact`；后一种边保留 GitHub provider 和仓库 ID 作为证据。只有 `Observation.kind=recommendation` 才使用 `recommends`。OpenAlex、Semantic Scholar 和 GitHub GraphProvider 与 connector 分开：connector 摄取外部 Observation，GraphProvider 只对一个明确 Artifact / Entity 补全精确公开 metadata。Provider cache 只保存选取后的字段和可用 ETag，使用 7 天 paper / author 与 30 天 institution TTL，不落原始大 JSON。

source discovery 使用显式 `ExpansionBudget`，默认最大深度 2，并限制节点、边、候选、provider request、引用、被引和作者近期论文 fanout。确定性遍历先解析 Entity canonical ID，再检查 visited set。第一版路径包含 curator → linked paper → author、paper → author → institution、paper citation 和 repository → owner。Similarity Text / BM25 / embedding 不属于 M2。

`SourceCandidate` 与 `Source` 分开持久化。状态为 pending / approved / rejected / deferred；拒绝原因会跨重放保留，精确身份新增 evidence 时不会重置。approve 只更新 candidate state。`export-source-template` 只向 stdout 输出一个默认 paused 的 YAML 建议，不写 `sources.yaml`，也不启动 connector。Provider verification 不是 independent Source；同一 Source 多条 Observation 仍只计一个来源。topic_support 是按 supporting Artifact 与 Source 聚合的诊断，不改写 Entity.topics。

SourceCandidate 时间字段冻结为：`first_discovered_at` 是候选首次写入本地的时间，`last_supported_at` 只随新增支持 evidence 前进，`last_evaluated_at` 每次 discovery 都更新。重复遍历同一 Graph 不会刷新支持时间。三种 freshness clock 分开保存：内容时间取 `Artifact.published_at` 或 `Observation.published_at`；发现时间取 `Observation.observed_at` 或 `SourceCandidate.first_discovered_at`；验证时间取 `GraphEdge.last_observed_at` 或 provider cache 的 `fetched_at`。检索 freshness 过滤优先用内容时间；缺失时才使用首条 Observation 的 `observed_at`，并标记 `freshness_basis=observed_at_fallback`。Provider metadata refresh time 不得替代发布时间。

Source discovery 默认 `max_depth=2` 保持不变，可覆盖 `Source → Artifact → Person`。Institution candidate 的完整证据路径 `Source → Artifact → Person → Institution` 至少需要 `max_depth=3`。

## M3 canonical corpus 与 retrieval

`Source / Observation / Artifact / Graph → Corpus Snapshot → RetrievalRequest → independent candidate routes → RRF → RetrievalCandidate`。Corpus 只通过统一 snapshot 构建；Artifact redirect 在索引前 canonicalize，Observation excerpt 最多 3 条、每条最多 2000 字符并保留 Observation 与 Source provenance。Corpus hash 由排序后的 retrieval documents 确定，manifest 的 `built_at` 不属于语义 hash。BM25 使用 bm25s，中文由 Jieba 加 CJK bigram tokenizer 处理；Dense 使用可替换 embedding backend、归一化 NumPy 向量和精确点积，逐文档缓存键为 model revision + retrieval text hash。CI 使用 deterministic fake embeddings，不下载模型；默认 live 配置为 `Qwen/Qwen3-Embedding-0.6B`，可通过 CLI 替换模型。

Text query 会运行 BM25 和 Dense；seed Artifact 会启用有界 Graph 路由，并可选调用 Semantic Scholar 的 exact-paper-ID recommendations；topic 与 source 约束分别启用 exact Topic 和 Source 路由。Semantic Scholar 只接受正、负 Artifact seeds 能精确解析到的 paper ID；未配置 transport、没有 exact seed 或 provider 暂时不可用时，记录 skipped/deferred 并保留本地 route 结果。任一 route 失败都不会丢弃其他 route 的候选。

Graph retrieval 有界为每请求至多 10 个 seed、每 seed 至多 100 个邻居、总计至多 500 个候选、深度至多 2；信号包括 citation neighbor、exact common author 和 accepted-source co-mention。解释保留 seed、candidate、canonical Person/Source IDs、predicate、edge 和 evidence。各 route 分开保存 rank 与原始分数，fusion 只使用 `score(d) = Σ 1/(60 + rank_r(d))`；canonical Artifact 在 fusion 前折叠。`as_of` 先排除内容时间晚于 cutoff 的 Artifact；没有 publication time 时用首个 Observation `observed_at`，时间未知的 Artifact 不进入历史查询。检索 freshness filter 不参与 RRF 分数。

冻结的 synthetic fixture 位于 `data/intelligence/eval/retrieval/synthetic-v1.json`，绑定 fixture corpus hash 与 qrels hash，用于 CI 验证 BM25 / Dense / Graph 的互补候选、B0–B4 路线和 future-leak gate。它不表示真实相关性。真实语料的 DEV / HOLDOUT qrels 必须经人工确认后才能报告真实 Recall、MRR、nDCG、Precision 和 route unique hits；模型输出不能自标为 ground truth。`retrieval-build` 与 `retrieval-manifest` 可复建本地索引并核对 corpus、document 和 route manifests；live dense smoke 结果保存在 ignored runtime，不进入 Artifact / Observation 源记录。

Retrieval relevance != personal preference；retrieval score != quality score；citation connectivity != scientific correctness；freshness filter != freshness ranking。M3 不使用 Feedback，不做个性化排序。人工确认的 DEV / HOLDOUT qrels 必须冻结 benchmark hash；合成 benchmark 只验证管线，不能作为真实相关性指标。

图数据源位于 `data/intelligence/events/graph_edges.jsonl`、`entity_aliases.jsonl`、`entity_redirects.jsonl` 和 `source_candidates.jsonl`。`data/intelligence/runtime/graph/` 下的 `out_edges.json` / `in_edges.json` 可删后用 `graph-rebuild` 重建；损坏的 edge、alias 或 redirect 会 fail closed。邻居、路径与统计可用 `graph-neighbors`、`graph-path` 和 `graph-stats` 查看。

M2 的边界是：Discovery candidate != recommendation；Candidate approval != subscription；Provider metadata != independent Source evidence；Graph relation != verified scientific claim。人工确认 Source、连接器和订阅策略之后，才进入已配置 Source 流程。

## 证据与 Hugo 边界

raw observation != Hugo article。

Observation 可以是未复核的摘录或候选链接，不自动成为公开知识文章。只有经历 deep_read、verify、synthesis 和显式 promote_to_hugo 后，高价值整理结果才进入 content/docs/、content/papers/ 或 content/blog/。模型猜测不能替代原始出处，provenance 应随 Observation 保留。

## 后续扩展方向（不是 M2 功能）

后续可以把 Semantic Scholar 式 positive/negative seeds、ResearchRabbit/Litmaps 式 similar-text 路线以及用户 open/save/dismiss/deep_read 反馈接入独立 candidate generators。它们属于后续 retrieval / ranking milestone，不改变本阶段的 graph evidence 与人审边界。

参考系统提供的是设计线索，不复制其产品 UI 或实现：Karakeep 等阅读器启发 ingestion、storage 和规则边界；ResearchRabbit、Litmaps 和 Semantic Scholar 启发有 provenance 的候选扩张路径；STORM/Co-STORM、PaperQA2 和 SurfSense 启发 provenance 与 cited synthesis。个性化推荐、定时调度和研究综合仍不属于 M2。
