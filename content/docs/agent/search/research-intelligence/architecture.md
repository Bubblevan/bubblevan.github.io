---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-architecture
content_kind: docs
title: "Research Intelligence 数据层架构（M0）"
date: 2026-09-28T00:00:00+08:00
status: draft
visibility: public
summary: 统一 source、observation、artifact、entity 与 feedback 的离线数据层及 M0 边界。
topics: [research-intelligence, source-discovery, agent]
aliases: []
authors: [bubblevan]
---

# 目标与边界

Research Intelligence 是统一研究数据层，不是第二套 PKB。现有 scripts/pkb/capture.py 仍负责低摩擦 capture 和原有 promotion；M0 通过只读桥接消费 type_hint 为 link 或 bookmark 的 capture。现有 XHS reader 保持原样，是第一个 acquisition connector。此阶段不增加 scraper。

来源适配器最终可以承接 Xiaohongshu、Zhihu、X、RSS/Atom、博客、arXiv/OpenReview、GitHub、Hugging Face、技术报告和讨论社区。M0 只实现 PKB capture 与现有 sanitized XHS JSON 的离线转换。

## M0 明确不做

当前阶段不训练 embedding model，不引入 vector database，不实现 LLM ranking、learning-to-rank 或 contextual bandit，不建立推荐 dashboard，不运行多源 cron，不增加 Zhihu、X、Discord 或 Telegram connector，不改变 XHS scraper 行为，也不实现广告竞价。M0 也不做实体的模糊神经解析或自动论文结论验证。

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

schemas/intelligence 下的六份 JSON Schema 定义 source、observation、artifact、entity、feedback 和 topic。scripts/intelligence/ids.py 使用 namespace、规范化 identity 和 SHA-256 确定性生成 src、obs、art、ent、fb ID；topic ID 使用可读 slug。同一 identity 重放不会生成随机 ID。

Artifact identity 优先级为 DOI → arXiv ID → GitHub owner/repo → Hugging Face repo ID → canonical URL → 规范化标题指纹。GitHub 与 Hugging Face 地址会折叠仓库子路径；URL 规范化复用 scripts/pkb/normalize_url.py 并先移除私密查询参数。M0 只解析明示标识，不做 fuzzy neural entity resolution。

data/intelligence/topics.yaml 提供 11 个研究顶层主题和 agent、search、memory、RAG、OPD、verifier、reward、multi-agent、inference-serving 等 cross-cutting leaf。Leaf 可以有多个 parents；Observation 和 Artifact 的 topics 本身也是多标签。

本地 JSONL 写入 data/intelligence/events/，此目录默认 gitignored，因为观察正文可能包含捕获内容。Observation 与 Feedback 按月份写入，仅第一次写入同一 ID；sources、artifacts、entities JSONL 是按 ID 排序的 materialized index，upsert 通过临时文件加原子替换。重复 XHS post 只关联原 Observation；不同 Observation 提及相同 arXiv/DOI/仓库时共享 Artifact。

## 证据与 Hugo 边界

raw observation != Hugo article。

Observation 可以是未复核的摘录或候选链接，不自动成为公开知识文章。只有经历 deep_read、verify、synthesis 和显式 promote_to_hugo 后，高价值整理结果才进入 content/docs/、content/papers/ 或 content/blog/。模型猜测不能替代原始出处，provenance 应随 Observation 保留。

## 后续候选扩展方向（不是 M0 功能）

架构为后续独立 candidate generators 留出接缝：Semantic Scholar 式 positive/negative seeds，ResearchRabbit/Litmaps 式 citation/reference、common-author 和 similar-text 多路扩张，以及用户 open/save/dismiss/deep_read 等反馈。这些都可以汇入同一 Candidate → Ranking 边界，而不改变 capture 或 source identity。

参考系统提供的是设计线索，不复制其产品 UI 或实现：Karakeep 等阅读器启发 ingestion、storage 和规则边界；FreshRSS/Folo 类系统启发 subscription connector 分离；ResearchRabbit、Litmaps 和 Semantic Scholar 启发候选扩张路径；STORM/Co-STORM、PaperQA2 和 SurfSense 启发 provenance 与 cited synthesis。推荐、抓取调度和研究综合均不属于 M0。
