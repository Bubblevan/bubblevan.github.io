---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-m6-operational-report
content_kind: docs
title: "RI-M6 Operational Validation"
date: 2026-09-29T00:00:00+08:00
status: draft
visibility: public
summary: RI-M6 离线回归、规模基准、HF Daily Papers live smoke 与当前未通过的来源 gate。
topics: [research-intelligence, source-discovery, operations]
aliases: []
authors: [bubblevan]
---

# RI-M6 Operational Validation

截至 2026-09-29。此报告记录 M6 的可重复验证结果和仍需人工/外部条件的 live gates；未通过的 gate 不能当作 M6 完成，也不解锁 M7。

## 本地验证

- `python -m unittest discover -s scripts -p 'test*.py' -q`：283 tests passed。
- `python -m compileall -q scripts/intelligence apps/research_intelligence_feed.py`：passed。
- `git diff --check`：passed（Git 显示的 LF/CRLF 转换提示不影响退出码）。
- Hugging Face Daily Papers 首次 source poll：114 fetched、114 new observations、2 pages、succeeded；立即第二次：114 duplicate、0 new、succeeded。
- 后续 daily pipeline 收到 115 条，其中 114 条重复、1 条新增；source coverage 当前统计 1 次 DailyRun poll、115 observations、115 canonical artifacts。FeedRun 有 12 个条目，其中 2 个关联到 Hugging Face Daily Papers source。
- Graph backfill/rebuild 成功；最近 daily pipeline 构建了 6,462 个 canonical Artifacts、16,345 条 graph edges。Corpus hash：`a911642833f655d1987fb3c4bcbab5696a0eabc0952b3509ac32e4f0e6c6d6ce`。
- `retrieval-build` 成功，BM25、graph、topic、source manifests 已更新到同一 corpus hash；可选 Dense index 未重算，避免在无明确 Dense warming 请求时重新编码 2,800 余个新增文档。

## 3k / 10k / 30k JSONL 基准

每个规模在独立 Python 进程运行，避免 Windows peak working set 跨样本累计。均为本机临时 synthetic 数据；耗时用于趋势比较，不是跨机器门槛。

| Records | Ingest (s) | Ingest / s | Graph backfill (s) | Edges / s | Corpus snapshot (s) | Peak working set (MB) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 9.777 | 306.86 | 1.248 | 2,403.49 | 21.650 | 130.57 |
| 10,000 | 34.360 | 291.04 | 4.411 | 2,267.18 | 72.004 | 366.76 |
| 30,000 | 103.430 | 290.05 | 15.088 | 1,988.28 | 218.848 | 1,040.17 |

30k / 3k 耗时比分别为 ingest **10.58×**、graph **12.09×**、corpus **10.11×**。Ingest 和 corpus 接近线性；graph 比线性比例高约 21%，需要在后续规模观测中留意。当前基准没有达到足以直接迁移 SQLite 的证据门槛；M6 不迁库。

## 未通过的 live gates

### OpenReview

只使用官方 `openreview-py` 做只读 probe。公开 venue group 可以读取；当前试验的 submission invitation 返回 expired，notes 请求返回 `403 ChallengeRequired`。没有把未经验证的 venue 写入 active catalog，也没有摄取 review/comment。OpenReview live poll 和公开决策核验仍待可用 invitation/API 通路。

### OpenAlex topic mapping

映射仍为空，候选只保存在 gitignored private proposal store。当前最贴合的两项待人工批准：

- `T10456` — Multi-Agent Systems and Negotiation → `topic-multi-agent`，proposal `ot-3f7c38e7c6b66a988f7ddc8e`。
- `T10906` — AI-based Problem Solving and Planning → `topic-reasoning-verification-and-planning`，proposal `ot-217c64d19a436c6b8dc2b3b7`。

其他宽泛搜索候选包含制造、城市规划、临床推理等无关聚类，不应自动映射。审批前不会创建正式 OpenAlex Source。

### RSS/Atom proposals

现有待发现 SourceCandidate 没有公开页面上的标准 RSS/Atom `rel=alternate` 链接；RSS proposal store 当前为空。没有猜测 `/feed`、`/rss.xml` 等路径，也没有自动启用来源。M6 的两个 RSS proposal 仍待从新的有效候选中发现并逐项批准。

### Daily pipeline 与 provider backoff

本次生产 pipeline 新建 DailyRun `daily-20260929-r0005-90ea4f4c7cf301b33792`，状态为 partial：8 个 active sources 中 5 个成功，3 个 GitHub Releases source 收到 provider-directed backoff，要求等到 `2026-09-29T10:26:39Z`。它们没有被重试；其余 graph、corpus snapshot、feed preparation、health stages 均成功。后续只能在该时间后再次 polling。

GitHub Actions production build 尚需由本分支 push 触发并检查。7-day observation window 从首个 M6 source poll 开始；在观察期和上述 live gates 通过前停止在 M6。

## 本机计划任务

用户此前选择的 05:00 Windows Task Scheduler 任务已注册，运行本仓库 `.ri-ops-venv` 的 `intelligence-daily --mode production --scheduled`，设置 `StartWhenAvailable`、联网条件和单实例。提升权限核验显示任务为 Ready、下一次计划时间为 05:00。
