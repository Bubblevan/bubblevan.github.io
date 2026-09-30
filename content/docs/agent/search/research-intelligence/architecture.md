---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-architecture
content_kind: docs
title: "Research Intelligence 数据层架构（M0–M8）"
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

来源适配器可承接 RSS/Atom、博客、arXiv/OpenReview、GitHub、Hugging Face、OpenAlex、技术报告和讨论社区。当前实现 RSS/Atom、GitHub Releases、OpenReview 投稿与公开决策、Hugging Face Daily Papers、OpenAlex exact-ID works 查询，以及现有 PKB/XHS 的手动导入。

## 当前边界

M0–M7 的来源采集、语料、检索、Feed 与运行控制面已关闭。M7 支持 XHS browser-assisted manual/detail acquisition、Zhihu Answer browser-assisted acquisition、交互式来源订阅，以及可选的 RSSHub proposal path。`tabris` 小红书 profile 只进行交互式尝试，曾遇到登录壳，未成功同步任何笔记；没有尝试绕过登录。这是已记录的单次来源状态，不是 connector regression。M8 增加用户主动触发的证据研究和带人审边界的 Hugo promotion，不添加 Source 或自动日更综合。X、Discord、Telegram 仍不是当前新增来源目标；不实现推荐排序训练、learning-to-rank 或 contextual bandit。

Source Candidate 仍不是个性化推荐；发现不会自动关注、订阅、激活候选或修改 Source catalog。身份解析只使用本地精确别名，或 provider 明确给出的 DOI、OpenAlex、Semantic Scholar、ORCID、ROR、GitHub 数字 ID 等精确等价关系；相似标题、姓名和语义相似度不会合并实体。

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

## M3.1 Artifact mention、语料资格与时间语义

Observation 记录一次来源内容及其原始发布时间；Artifact 表示被描述的研究对象。每个 `artifact_candidates[]` mention 可以标记 `primary`、`referenced` 或 `incidental`。缺少 role 的历史 mention 按 `referenced` 读取，不回溯升级成 primary。`incidental` 不会新建 searchable Artifact。RSS connector 为每个 entry 明确生成 primary candidate；其条目标题、摘要（最多 4000 字符）、作者、发布时间和确定性主题进入 primary Artifact，并记录 Observation、Source 和 connector provenance。Feed 中其他显式 URL 标记为 referenced。来源 catalog 可声明 `artifact_policy.primary_type`：arXiv cs.AI/cs.LG 为 paper，Hugging Face Blog 和 OpenAI News 为 blog；普通未知 RSS 默认 blog。GitHub Releases 保持 repository contract。

只有 primary Artifact 继承 Observation 的发布时间和主题。Referenced Artifact 只有在 candidate 自身给出明确时间时才使用该时间，不从引用它的 feed entry 继承。Artifact summary 有界；正文不会无限复制。显式引用建立 `references` Artifact → Artifact predicate，同时保留历史 Artifact ID、别名和图节点。HF `created_at`、`last_modified`、首次本地观察时间分别保存；模型的历史 cutoff 可使用 `created_at`，缺失时回退到 first observed，不以 `last_modified` 或 API refresh time 替代内容时间。

RetrievalEligibility 是 snapshot 的派生字段：`full_text`、`metadata_only`、`graph_only` 或 `excluded`。空标题且空正文的 document 不进入 BM25 或 Dense；graph-only Artifact 仍留在图中。默认 `research-default` 包含可搜索的非模型类型，以及 full-text、primary 或经过明确元数据 enrichment 的 model/dataset/space。`all-artifacts` 用于调试，`models` 用于模型、数据集和 Space 专项查询。HF Hub enrichment 只针对精确 repo ID，最多 20 项，仅读取选择后的 API metadata，不下载权重或仓库文件，也不按 downloads/likes 排 relevance。Native tags/pipeline tags 只经 topic catalog 的精确 alias 映射。

Retrieval manifest v2 固定报告语料资格、路由索引数、缺失标题/正文/发布时间、primary/referenced 分布，以及按 Artifact type、Source 和 mention role 统计的 canonical topic coverage。`Observation`、`Artifact`、`Graph node`、`retrieval candidate` 和 `recommendation` 是不同对象；存在于图中不代表进入默认检索，也不代表推荐。

## M3.1 Graph、fusion 与 relevance evaluation

`graph` 是 explicit-seed-graph：给定一个明确 Artifact，返回有结构证据的邻居。纯文本查询不注入手工 seed。可选 `graph-expand` 先取 BM25/Dense 的前 5 个 canonical Artifact 作为 seed，再扩图；每条路径保留 seed route、seed rank 和 graph path。candidate degree 与 seed support 只作诊断，degree-normalized 只能作为独立实验 variant。

每路默认抓取 `route_depth=50`，RRF 使用更深的 route lists，再按 `final_top_k` 返回结果；运行 manifest 记录 `rrf_k`、route depth、final top-k 和 corpus profile。DEV judgments 可以由人类或明确署名的 model judge 产生；两者均先冻结 query、corpus、候选池和 benchmark hash，再用于回归比较。20 个 DEV queries 不支持反复调参或 SOTA 声明。

DEV-v1 是保留不变的初始 GPT-6 Luna-judged pool；DEV-v1.1 使用同一 query set、相同 corpus 和重新取得的 B0–B4 top-20 并集。增量 model judge 只接收旧 qrels 未覆盖的 pair。blind payload 可包含 query、category、specificity 和 Artifact 展示字段，不含 route、rank、score、baseline 或 fusion。评分为 0（不相关）、1（有用）、2（直接重要），metadata 不足单独记录。Prompt、judge 身份、时间、guideline 与可获得的运行时元数据随 model-judged pseudo-gold provenance 冻结；无法恢复的历史 prompt hash、revision、temperature 或 request ID 明确记为未知。正式 B0–B4 comparison 要求 `Judged@10` 与 `Judged@20` 都为 1；未满足时只能发布 exploratory metrics。`holdout-draft.json` 保持隔离，不用于开发调参。

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

Hugging Face 的 `/blog/`、`/papers/`、`/docs/`、`/api/`、`/collections/`、`/organizations/`、`/join/`、`/tasks/` 是站点保留路径，不是 model 仓库；`/datasets/` 与 `/spaces/` 也必须保持各自 Artifact 类型。reserved path audit 会逐项检查这些 URL 下没有误标为 `model` 的 Artifact。修复历史 `/blog/` 误分类时保留旧 Artifact ID，添加 `old_id → url:<canonical-blog-url>` redirect，并删除指向该旧 ID 的 Hugging Face model alias。Corpus snapshot 对 redirect 合并组优先选 canonical Artifact 记录，避免旧记录覆盖 canonical type 并进入错误的 retrieval profile。

## M2 graph 与 source discovery

`graph-backfill` 只从本地 Sources、Observations、Artifacts 和 topic catalog 建图，不联网。Observation → Artifact 只在 Observation 明确包含链接，或 GitHub Releases connector 的 `api_metadata/repository` 明确给出精确仓库 ID 时形成 `Source --mentions--> Artifact`；后一种边保留 GitHub provider 和仓库 ID 作为证据。只有 `Observation.kind=recommendation` 才使用 `recommends`。OpenAlex、Semantic Scholar 和 GitHub GraphProvider 与 connector 分开：connector 摄取外部 Observation，GraphProvider 只对一个明确 Artifact / Entity 补全精确公开 metadata。Provider cache 只保存选取后的字段和可用 ETag，使用 7 天 paper / author 与 30 天 institution TTL，不落原始大 JSON。

source discovery 使用显式 `ExpansionBudget`，默认最大深度 2，并限制节点、边、候选、provider request、引用、被引和作者近期论文 fanout。确定性遍历先解析 Entity canonical ID，再检查 visited set。第一版路径包含 curator → linked paper → author、paper → author → institution、paper citation 和 repository → owner。Similarity Text / BM25 / embedding 不属于 M2。

`SourceCandidate` 与 `Source` 分开持久化。状态为 pending / approved / rejected / deferred；拒绝原因会跨重放保留，精确身份新增 evidence 时不会重置。approve 只更新 candidate state。`export-source-template` 只向 stdout 输出一个默认 paused 的 YAML 建议，不写 `sources.yaml`，也不启动 connector。Provider verification 不是 independent Source；同一 Source 多条 Observation 仍只计一个来源。topic_support 是按 supporting Artifact 与 Source 聚合的诊断，不改写 Entity.topics。

SourceCandidate 时间字段冻结为：`first_discovered_at` 是候选首次写入本地的时间，`last_supported_at` 只随新增支持 evidence 前进，`last_evaluated_at` 每次 discovery 都更新。重复遍历同一 Graph 不会刷新支持时间。三种 freshness clock 分开保存：内容时间取 `Artifact.published_at` 或 `Observation.published_at`；发现时间取 `Observation.observed_at` 或 `SourceCandidate.first_discovered_at`；验证时间取 `GraphEdge.last_observed_at` 或 provider cache 的 `fetched_at`。检索 freshness 过滤优先用内容时间；缺失时才使用首条 Observation 的 `observed_at`，并标记 `freshness_basis=observed_at_fallback`。Provider metadata refresh time 不得替代发布时间。

Source discovery 默认 `max_depth=2` 保持不变，可覆盖 `Source → Artifact → Person`。Institution candidate 的完整证据路径 `Source → Artifact → Person → Institution` 至少需要 `max_depth=3`。

## M3 canonical corpus 与 retrieval

`Source / Observation / Artifact / Graph → Corpus Snapshot → RetrievalRequest → independent candidate routes → RRF → RetrievalCandidate`。Corpus 只通过统一 snapshot 构建；Artifact redirect 在索引前 canonicalize，redirect 合并组以 canonical Artifact 记录作为字段来源，Observation excerpt 最多 3 条、每条最多 2000 字符并保留 Observation 与 Source provenance。Corpus hash 由排序后的 retrieval documents 确定，manifest 的 `built_at` 不属于语义 hash。BM25 使用 bm25s，中文由 Jieba 加 CJK bigram tokenizer 处理；Dense 使用可替换 embedding backend、归一化 NumPy 向量和精确点积，逐文档缓存键为 model revision + retrieval text hash。CI 使用 deterministic fake embeddings，不下载模型；默认 live 配置为 `Qwen/Qwen3-Embedding-0.6B`，可通过 CLI 替换模型。

Text query 会运行 BM25 和 Dense；seed Artifact 会启用有界 Graph 路由，并可选调用 Semantic Scholar 的 exact-paper-ID recommendations；topic 与 source 约束分别启用 exact Topic 和 Source 路由。Semantic Scholar 只接受正、负 Artifact seeds 能精确解析到的 paper ID；未配置 transport、没有 exact seed 或 provider 暂时不可用时，记录 skipped/deferred 并保留本地 route 结果。任一 route 失败都不会丢弃其他 route 的候选。

Graph retrieval 有界为每请求至多 10 个 seed、每 seed 至多 100 个邻居、总计至多 500 个候选、深度至多 2；信号包括 citation neighbor、exact common author 和 accepted-source co-mention。解释保留 seed、candidate、canonical Person/Source IDs、predicate、edge 和 evidence。各 route 分开保存 rank 与原始分数，fusion 只使用 `score(d) = Σ 1/(60 + rank_r(d))`；canonical Artifact 在 fusion 前折叠。`as_of` 先排除内容时间晚于 cutoff 的 Artifact；没有 publication time 时用首个 Observation `observed_at`，时间未知的 Artifact 不进入历史查询。检索 freshness filter 不参与 RRF 分数。

冻结的 synthetic fixture 位于 `data/intelligence/eval/retrieval/synthetic-v1.json`，绑定 fixture corpus hash 与 qrels hash，用于 CI 验证 BM25 / Dense / Graph 的互补候选、B0–B4 路线和 future-leak gate。它不表示真实相关性。DEV qrels 可以是 human-judged 或显式 model-judged development relevance judgments；报告须标明 judge provenance，model judgments 称为 pseudo-gold，不称 ground truth 或 human-evaluated。HOLDOUT 在独立冻结和审阅前不得用于开发比较。`retrieval-build` 与 `retrieval-manifest` 可复建本地索引并核对 corpus、document 和 route manifests；live dense smoke 结果保存在 ignored runtime，不进入 Artifact / Observation 源记录。

M3.2 的 Artifact 业务读取必须经过 `ArtifactRepository`：`get`、`iter_canonical` 和 `resolve_id` 返回 canonical Artifact 视图；`raw_rows` 仅用于迁移、审计和调试。`ArtifactAliases.canonical_redirect_map()` 与 `EntityAliases.canonical_redirect_map()` 返回 cycle-checked、path-flattened、只读映射，检索代码不访问 alias store 的私有 redirect rows。物理 Artifact 行数与 canonical Artifact 数分别通过 `artifact-stats` 观察；普通产品统计中的 Artifact 数采用 canonical 数。

Argilla 或离线 JSON adapter 可导入 human 或 model judgments；generic qrels 使用 `bubblevan/retrieval-qrels/v2`，每条 qrel 标明 judge type/name/model，旧 human-qrels schema 保持可读。通过 hash、身份、grade 和完整性校验后冻结的 benchmark 才作为 qrels source of truth。质量问题标签独立于相关性 grade。DEV-v1 与 DEV-v1.1 的完整候选清单、qrels、prompt 与 retrieval provenance 分开保留。

Retrieval relevance != personal preference；retrieval score != quality score；citation connectivity != scientific correctness；freshness filter != freshness ranking。M3 不使用 Feedback，不做个性化排序；当前 feedback events 为 0，所以不进入 LambdaRank、bandits 或 RecBole。M4 下一步是 Personal Feed v0 + Explicit Feedback Loop，先交付可解释的日常推荐与显式反馈采集。DEV model-judged pseudo-gold 用于回归和产品诊断，不用于 benchmark SOTA 声明；HOLDOUT qrels 独立管理。

图数据源位于 `data/intelligence/events/graph_edges.jsonl`、`entity_aliases.jsonl`、`entity_redirects.jsonl` 和 `source_candidates.jsonl`。`data/intelligence/runtime/graph/` 下的 `out_edges.json` / `in_edges.json` 可删后用 `graph-rebuild` 重建；损坏的 edge、alias 或 redirect 会 fail closed。邻居、路径与统计可用 `graph-neighbors`、`graph-path` 和 `graph-stats` 查看。

M2 的边界是：Discovery candidate != recommendation；Candidate approval != subscription；Provider metadata != independent Source evidence；Graph relation != verified scientific claim。人工确认 Source、连接器和订阅策略之后，才进入已配置 Source 流程。

## 证据与 Hugo 边界

raw observation != Hugo article。

Observation 可以是未复核的摘录或候选链接，不自动成为公开知识文章。只有经历 deep_read、verify、synthesis 和显式 promote_to_hugo 后，高价值整理结果才进入 content/docs/、content/papers/ 或 content/blog/。模型猜测不能替代原始出处，provenance 应随 Observation 保留。

## 后续扩展方向（不是 M2 功能）

后续可以把 Semantic Scholar 式 positive/negative seeds、ResearchRabbit/Litmaps 式 similar-text 路线以及用户 open/save/dismiss/deep_read 反馈接入独立 candidate generators。它们属于后续 retrieval / ranking milestone，不改变本阶段的 graph evidence 与人审边界。

参考系统提供的是设计线索，不复制其产品 UI 或实现：Karakeep 等阅读器启发 ingestion、storage 和规则边界；ResearchRabbit、Litmaps 和 Semantic Scholar 启发有 provenance 的候选扩张路径；STORM/Co-STORM、PaperQA2 和 SurfSense 启发 provenance 与 cited synthesis。个性化推荐、定时调度和研究综合仍不属于 M2。

## M6 structured source coverage

M6 在现有 SourceCandidate 与 Daily Pipeline 上增加 OpenReview submissions、Hugging Face Daily Papers、OpenAlex exact-ID Works queries，以及从公开页面标准 RSS/Atom alternate link 发现的 SourceProposal。SourceCandidate 表示值得审看的对象；SourceProposal 表示已找到并验证的订阅 endpoint。Probe 不写 Observation、不激活 Source；订阅必须由用户逐项批准并写入 gitignored 的 `data/intelligence/private/sources/subscriptions.jsonl`。Seed catalog 与私有订阅按确定性 Source ID 合并。

OpenReview Source 必须显式指定 API version 与 invitation ID。采集仅请求配置的 submission / public decision invitation，并只接收 readers 明确标记公开的 submission 或 decision；没有公开 readers 的记录跳过，M6 不抓 review/comment thread。凭据从 `OPENREVIEW_USERNAME` / `OPENREVIEW_PASSWORD` 环境变量读取；`ChallengeRequired` 分类为 `auth_required`，无当前可用 invitation 或 provider 过期分类为 `DEFERRED_UPSTREAM`。该来源是软 gate，不阻塞 M6；禁止付费、CAPTCHA/challenge 绕过和注入浏览器 Cookie。Hugging Face Daily Papers 使用官方 `/api/daily_papers` structured endpoint，作为 curator Observation；它建立 `Source --recommends--> Paper`，upvotes 和 trending metadata 不进入 Artifact 或排序分数。OpenAlex Source 仅接受精确 topic / author / institution / source IDs，每次最多抓 200 works，默认日期边界为 `today - 7 days` 至 `today`（含两端，按 publication date 过滤）。可选 `OPENALEX_API_KEY` 只通过 Authorization header 从环境读取，不写入 catalog、runtime 或诊断。OpenAlex 在查询前读取 provider budget，并在剩余比例低于 10% 时停止该轮；诊断仅记录数值型 limit、remaining、credits-used 和 reset。Publication-window polling 不能保证捕获“很晚才被 OpenAlex 索引、但 publication_date 很旧”的工作；系统不宣称 exactly-once sync。

OpenAlex topic IDs 到内部 topic 的关系是 human-reviewed external-topic mapping，不表示语义等价。生产 mapping 必须有 reviewer 和 UTC review time；测试 fixture 只写临时路径。RSS discovery 接受标准 `link rel=alternate` RSS/Atom 类型，以及链接文字或 `type` 明确标注 RSS、Atom、Feed 的 anchor；不会猜测 feed endpoint。探测只创建 private SourceProposal，只有逐项人工批准后才进入 active subscriptions。免费/public API、免费账户/API key 与公开 RSS 是默认来源策略。Paid external data sources are not required for core operation. 若来源要求付款方式、付费 plan 或预付 credits，将其标记 `deferred_paid`，不自动购买。

新增 connector 与 HTTP transport diagnostic 只持久化受控 error class/category，不保存 request URL、hostname、headers、Cookie、token 或 raw exception text。Windows scheduled pipeline 在所有 Source 首轮完成后，只对 M6 列出的 transient transport categories 等待 30 秒并重试一次；手动运行不等待，HTTP status、schema、privacy 和 provider-directed backoff 不触发这轮恢复。每个 DailyRun 保留 attempt count、初次类别和最终状态。

Source Coverage 使用 Observation 的首次本地 `observed_at`，按 canonical Artifact 计算 source-level 新增、唯一贡献、重复率、发现延迟、元数据完整度、topic 覆盖、poll health 和 pairwise overlap。`polls` 统计 DailyRun 内的尝试；connector checkpoint 同时显示最近一次尝试与成功时间，因此独立的 `run-source` 也能反映在当前 health 中。Graph backfill 先构建 primary Artifact 到 Observation 的索引，再对每条 Observation 做常数时间查询；一次 backfill 载入并合并一个 `GraphSnapshot`，校验通过后原子提交并从同一快照重建索引。Observation / Feedback ID 索引只在进程内缓存；持久层仍是 JSONL，并继续遵循单 writer per store directory。

M6 engineering gate 与 M6-OBS 分离：HF Daily、OpenAlex、RSS live smoke、structured pipeline integration、coverage metrics、scale benchmark、offline regression 和 CI 构成 M6 engineering gate。通过后 M6 标为 CLOSED；M6-OBS 继续观察原定窗口至到期，不阻塞后续工程 milestone。

## M7 社交来源与交互式采集

来源获取优先级固定为 official API → 原生 RSS/Atom → 配置的 RSSHub/兼容 feed → browser-assisted → 手工 URL。RSSHub 仍使用 `rss-atom` connector；source acquisition 可记录 `via: rsshub`，Observation provenance 记录 `upstream_adapter: rsshub`。只有 `RSSHUB_BASE_URL` 私有配置时才尝试 RSSHub，不依赖公共 `rsshub.app`。知乎 `/zhihu/people/answers/:id` 先探测并形成人工批准的 SourceProposal；探测失败时才允许精确 Answer 的浏览器 fallback。

Source `operations.acquisition_mode` 分为 `scheduled`、`interactive` 和 `manual`。常规 API/RSS source 默认 `scheduled`；浏览器 source 必须为 `interactive`，只由 `social-sync` 或 `social-sync-inbox` 在用户触发时运行。05:00 Daily Pipeline 跳过 interactive source，健康状态单独报告 `interactive_ready`、`interactive_stale` 或 `never_synced`；交互运行不伪装成 scheduled poll。

`InteractiveAcquirer` 通过 `chrome-use` 控制已有、明确采用的 Chrome 标签页。它不启动 Chrome、不注入 Cookie、不使用 stealth、指纹修改、网络拦截或验证码绕过。浏览器预算是每次最多 3 个来源、每来源最多 10 个对象、最多 20 次页面访问、并发 1。遇到完整登录页、安全挑战或 DOM 字段变化即停止当前来源，之前完成的对象和逐项 checkpoint 保留。已渲染且字段齐全的公开正文即使被登录弹窗遮挡仍可读取。

多 profile 或多 session 的本机环境可通过进程环境 `CHROME_USE_BROWSER` 和 `CHROME_USE_SESSION` 固定 chrome-use 目标；这两个值不写入 source、Observation、checkpoint 或日志。profile 参数只用于 `open`，session 参数用于同一已连接 session 的 tab/adopt/status 命令。Windows 驱动优先遵循 `CHROME_USE_BIN` 和 PATH，PATH 被隔离时回退到已安装的 `D:\DevTools\chrome-use\chrome-use.exe`。

默认只把规范化的公开字段写成 Observation / Artifact，不保存浏览器 stdout、原始 snapshot、Cookie、Authorization、session/local storage、账号标识或 profile 路径。checkpoint 只保存 source/platform、最近成功时间、最近对象 ID、失败数、状态和计数器。手工 inbox 只保存去掉跟踪参数的公开 URL、platform、可选 source ID、加入时间和状态。debug snapshot 仅在明确 opt-in 的本机 gitignored runtime 路径中允许。

小红书 note ID 和知乎 answer ID 是平台对象 identity；跟踪 query 不产生新 Observation。小红书 note 本身是 `social_post` primary Artifact；知乎 Answer 是 `discussion` primary Artifact，Question 不独立 materialize。正文中明确出现的论文、仓库、模型和博客继续作为 referenced Artifacts。只有正文出现“推荐 / 值得看 / paper 推荐”等固定文本证据时才把小红书 Observation 标为 recommendation。图片 VLM 默认关闭；显式 `--enrich-images` 时只写 `image_extract` 候选，不形成 authoritative merge。

社交采集后可选运行既有 graph backfill、corpus snapshot 和 Feed service。如果当前 FeedRun 已被 impression、open、deep_read、save 或 useful 事件查看，就保留其不可变内容并写入 `refresh_pending` 状态；未查看时可以生成新 revision。Dense warming 仍是用户显式选择；`retrieval-status` 展示当前 corpus hash、Dense manifest corpus hash、manifest 文件 hash 和 `fresh` / `stale` / `missing` / `unavailable` 状态。stale Dense 不参与 M8 research retrieval，Research UI 只显示状态和 `retrieval-build --routes dense` 提示；Streamlit request thread 不下载或加载 Qwen。

Source Coverage 对交互来源单独给出最近同步状态、新 Observation、重复、login、challenge 和 DOM change 计数；`polls` 只统计 scheduled DailyRun，不会为社交同步造 poll。X/Twitter 保持 `DEFERRED_NOT_REQUIRED`。

M6 运行 3k / 10k / 30k synthetic Observation、Artifact 基准，报告 ingestion、graph backfill、corpus snapshot wall time、吞吐和可用的峰值 RSS。增长比例是本机诊断数据，不是跨机器秒数门槛；若 30k 路径仍出现不合理的超线性增长，应暂停扩源并单独评估 M6.1 SQLite，而不是默认迁库。新 Source 只扩大 Daily Pipeline 和 Personal Feed 的候选集，不增加排序权重。PaperFlow 的功能对照见 [M6 PaperFlow reference](m6-paperflow-reference.md)。

## M8 研究综合与 Hugo promotion

研究只能由 Feed/Saved 的 `Research this`、Research 页面或 `research-start` 显式启动。保存、有用和研究是三种不同动作；没有后台或 05:00 日管线 LLM 综合。第一版流程是 bounded local retrieval → immutable EvidenceRefs → perspective/subquestion plan → claims and evidence links → disagreement/uncertainty → private draft。Research Intelligence 语料、Source catalog、Observation 和 connector checkpoint 在生成时只读。

ResearchSession、EvidenceRef、ResearchClaim、ResearchBrief 与 promotion preview 位于 gitignored 且 Hugo 排除的 `data/intelligence/private/research/{sessions,evidence,briefs,promotion-previews}`。EvidenceRef 必须解析到 canonical Artifact / Observation，保存 locator、原始捕获文本及 SHA256；Evidence ID 由 canonical Artifact、locator 和 text hash 确定。历史 brief、generated summary 和 model speculation 不会作为 primary evidence。LocalCorpusEvidenceBackend 不联网；默认预算为 20 retrieved Artifacts、12 evidence Artifacts、50 refs、每 Artifact 6 refs、合计 80,000 字符。

BM25、Topic、Source 与 exact Graph 是本地稀疏回退。Dense 仅在 Dense manifest 与当前 corpus hash 匹配且模型可用时进入检索；stale/missing/unavailable 均跳过，不启动自动重建。明确重建命令为 `python -m scripts.intelligence.cli retrieval-build --routes dense`。Dense manifest 状态为 `fresh`、`stale`、`missing` 或 `unavailable`，同时报告 current corpus hash、Dense corpus hash 和 manifest file hash。

可选 `requirements-research.txt` 提供 LiteLLM adapter；model 由 `RESEARCH_MODEL` / `RI_RESEARCH_MODEL` 配置，provider key 只从进程环境读取。每个 draft revision 记录 provider/model、可用的 model revision/request ID、temperature、prompt hashes、evidence-set hash、output hash 与可用 token/cost diagnostics。Synthesis 接受冻结 EvidenceRefs，不具备 browser、shell、connector 或文件写工具；网页和社交文本始终作为不可信引用数据。

可选 PaperQA2 adapter 独立使用 `data/intelligence/runtime/paperqa/`（PaperQA `PQA_HOME`），只对 paper/technical_report 和调用方显式提供的本地全文文件工作；正文处理上限 50 MiB，并关闭自动 document-detail lookup 与 multimodal enrichment。M8 不按 Artifact URL 自动下载 PDF，不绕过 paywall；PaperQA 缺失或失败时继续本地 evidence backend。

事实 Claim 必须引用当前 EvidenceRefs；未知 Evidence ID、文本 hash 漂移、canonical Artifact/Observation 断链均失败关闭。未获证据支持的 fact、missing evidence 或 broken citation 阻止 approval/promotion。Inference / interpretation 在 brief 中明确标识。ResearchBrief 每次生成增加 revision，旧版本不可覆盖；evidence-set 变化后新的输出必须引用新 hash。LiteLLM 仅是 synthesizer，不能成为来源或 citation。

Hugo 预览写在私有目录，不写 repository content。Promotion target 必须由用户明确选择为 `content/docs/research/`、`content/papers/` 或 `content/blog/` 下的 Markdown。Markdown 包含规范 front matter、Evidence footnotes 与 `research_intelligence.ai_assisted: true`。必须先人工 review，再显式 `research-approve`，最后单独执行 `research-promote`；系统不会自动 approve、publish 或 commit。promotion event 记录在私有研究事件日志，不参加 relevance projection。每次 promotion 对相同目标与内容幂等；已有不同内容则安全失败。

M8 不把知识 STORM、Co-STORM 或 Open Deep Research 引入 runtime；STORM 是研究计划和视角设计参考，不重复构建独立互联网搜索链。PaperQA2 仅作为可选全文 adapter。M8 不启动自动 Weekly Digest、LTR 或 Bandit。
