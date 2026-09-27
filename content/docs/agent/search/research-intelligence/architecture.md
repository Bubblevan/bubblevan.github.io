---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-architecture
content_kind: docs
title: "Research Intelligence 数据层架构（M1）"
date: 2026-09-28T00:00:00+08:00
status: draft
visibility: public
summary: 统一研究数据层、可恢复的 RSS/GitHub connector runtime 和保守的 Artifact 身份解析。
topics: [research-intelligence, source-discovery, agent]
aliases: []
authors: [bubblevan]
---

# 目标与边界

Research Intelligence 是统一研究数据层，不是第二套 PKB。现有 scripts/pkb/capture.py 仍负责低摩擦 capture 和原有 promotion；PKB bridge 只读消费 type_hint 为 link 或 bookmark 的 capture。XHS bridge 只接受现有 reader 产出的脱敏 JSON，不获取页面。M1 增加 RSS/Atom 与 GitHub Releases 两种 pull connector，不增加新 scraper。

来源适配器可继续承接 RSS/Atom、博客、arXiv/OpenReview、GitHub、Hugging Face、技术报告和讨论社区。当前实现 RSS/Atom、GitHub Releases，以及现有 PKB/XHS 的手动导入。

## 当前边界

当前阶段不训练 embedding model，不引入 vector database，不实现 LLM ranking、learning-to-rank 或 contextual bandit，不建立推荐 dashboard，不运行 daemon/cron，不增加 Zhihu、X、Discord 或 Telegram connector，不改变 XHS reader 行为，也不实现广告竞价。身份解析只使用本地精确别名或 Semantic Scholar 对显式 DOI/arXiv 的确认；相似标题只生成待核候选。

## 端到端数据流

Source → Acquisition → Observation → Canonicalization → Artifact / Entity Graph → Candidate Generation → Ranking → Feed → Feedback

每一层的职责：

- **Source** 是作者、策展人、实验室、出版物、订阅源、社区、平台或仓库的稳定身份。Source 只保存公开标识和 connector 配置，不保存 Cookie、session 或 xsec_token。
- **Acquisition** 是可替换的输入适配器。XHS reader 只提供已有脱敏 JSON；PKB bridge 只读 link/bookmark capture。抓取状态和浏览器运行时状态不进入知识记录。
- **Observation** 保留某 Source 在某一时刻公开、推荐或提到内容的证据，以及 retrieval mode、evidence level、source URL 和 collector。平台对象 ID 是同一帖重复读取时的首选 identity。
- **Canonicalization** 用确定性的标识优先级把 Observation 中的显式链接和标识符折叠成 Artifact candidate。无法确认的内容留在 candidate 状态，不依靠模糊模型补全。
- **Artifact / Entity** 是去重后的研究对象和参与者。关系通过 predicate 和 target ID 表示；M0 不建立 graph database。
- **Candidate Generation、Ranking、Feed** 是后续 milestone 的消费层。M0 不训练推荐模型，也不安排多源定时任务。
- **Feedback** 保留 impression、open、save、dismiss、deep_read、verify、cite、implement 和 promote_to_hugo 等研究价值信号，不把点击率当作唯一目标。

## 契约、身份和存储

schemas/intelligence 定义 source、observation、artifact、artifact alias、entity、feedback 和 topic。scripts/intelligence/ids.py 使用 namespace、规范化 identity 和 SHA-256 确定性生成 src、obs、art、ent、fb ID；topic ID 使用可读 slug。同一 identity 重放不会生成随机 ID。

Artifact identity 优先级为 DOI → arXiv ID → GitHub owner/repo → Hugging Face 类型与 repo ID → canonical URL → 规范化标题指纹。Hugging Face 的 model、dataset、space 使用不同 identity 和 canonical URL。URL 规范化复用 scripts/pkb/normalize_url.py 并先移除私密查询参数。Artifact 字段冲突进入 field_conflicts，标识符不会静默覆盖。

data/intelligence/topics.yaml 提供 11 个研究顶层主题和 agent、search、memory、RAG、OPD、verifier、reward、multi-agent、inference-serving 等 cross-cutting leaf。确定性 mapper 只映射 topic_id、名称和别名；来源原始标签单独放在 Observation.native_tags，未知标签不猜 topic。Leaf 可以有多个 parents；Observation 和 Artifact 的 topics 本身也是多标签。每个 artifact candidate 保存自己的 mention evidence 与 origin。

本地 JSONL 写入 data/intelligence/events/，此目录默认 gitignored，因为观察正文可能包含捕获内容。Observation 与 Feedback 按月份写入，仅第一次写入同一 ID；sources、artifacts、entities JSONL 是按 ID 排序的 materialized index，upsert 通过临时文件加原子替换。重复 Observation 只保留一个 ID；不同 Observation 提及相同标识时共享 Artifact。

## M1 connector runtime

Connector protocol 与 registry 位于 scripts/intelligence/connectors/。RSS/Atom 使用 feedparser；GitHub Releases 只读取已发布 release。两个 pull connector 共用有超时、条件请求和有界重试的 HTTP transport。每次运行是 one-shot；没有后台调度器。

Source 配置在 data/intelligence/sources.yaml，目前只放四个 RSS/Atom 和三个 GitHub 仓库 seed。运行状态放在 gitignored 的 data/intelligence/runtime/connectors/<source_id>.json，不进入 Source 记录。状态文件原子替换并 fsync。运行顺序是抓取、写入 Observation 和 Artifact、再原子推进 checkpoint；写入后 checkpoint 失败时，确定性 Observation ID 允许安全重放。

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

## 证据与 Hugo 边界

raw observation != Hugo article。

Observation 可以是未复核的摘录或候选链接，不自动成为公开知识文章。只有经历 deep_read、verify、synthesis 和显式 promote_to_hugo 后，高价值整理结果才进入 content/docs/、content/papers/ 或 content/blog/。模型猜测不能替代原始出处，provenance 应随 Observation 保留。

## 后续候选扩展方向（不是 M1 功能）

架构为后续独立 candidate generators 留出接缝：Semantic Scholar 式 positive/negative seeds，ResearchRabbit/Litmaps 式 citation/reference、common-author 和 similar-text 多路扩张，以及用户 open/save/dismiss/deep_read 等反馈。这些都可以汇入同一 Candidate → Ranking 边界，而不改变 capture 或 source identity。

参考系统提供的是设计线索，不复制其产品 UI 或实现：Karakeep 等阅读器启发 ingestion、storage 和规则边界；ResearchRabbit、Litmaps 和 Semantic Scholar 启发候选扩张路径；STORM/Co-STORM、PaperQA2 和 SurfSense 启发 provenance 与 cited synthesis。推荐、全网 source discovery、定时调度和研究综合均不属于 M1。
