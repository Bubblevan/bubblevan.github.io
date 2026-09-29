---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-m6-operational-report
content_kind: docs
title: "RI-M6 Operational Validation"
date: 2026-09-29T00:00:00+08:00
status: draft
visibility: public
summary: RI-M6.1 structured source closeout, live smoke, corpus rebuild and engineering gate status.
topics: [research-intelligence, source-discovery, operations]
aliases: []
authors: [bubblevan]
---

# RI-M6 Operational Validation

截至 2026-09-29。RI-M6.1 关闭 M6 engineering blockers。状态：**M6 = CLOSED；M6-OBS = OBSERVING**。观察窗口继续到期，但不阻塞后续工程 milestone；本次没有开始后续 milestone 的实现。

## 本地验证与数据快照

- `python -m unittest discover -s scripts -p 'test*.py' -q`：**290 tests passed**。
- `python -m compileall -q scripts/intelligence apps/research_intelligence_feed.py`：passed。
- `git diff --check`：passed。
- 删除生产 topic map 中的 T42 测试污染。当前两个 OpenAlex topic mapping 均由 `bubblevan` 人工审阅并带真实 UTC 时间：T10456 → `topic-multi-agent`；T10906 → `topic-reasoning-verification-and-planning`。它们是 human-reviewed external-topic mapping，不声明 semantic equivalence。新增 regression 确认 tracked map 不含 `test-reviewer`、fixture、`example.org` 或 T42；审批 fixture 使用临时目录。
- `rematerialize-primary-artifacts`、`graph-backfill`、`retrieval-build` 在采集完成后依次成功。最终 canonical corpus 有 **6,945 Artifacts**，graph 有 **17,353 edges**，BM25 索引 **5,731** 篇文档。BM25、graph、topic、source manifests 使用同一 `corpus_hash`：`2f302e423d08b42673bd142cc13a18a234fe70eea944834cb1d51dd3e57807d`。Dense warming 仍关闭。
- 生产 FeedRun `feed-7bc97e42bdd35cec9f939bbd` 为 ready，包含 12 条目、7 个来源、8 个 topics；三个已启用 retrieval routes 成功，隐藏项泄漏计数为 0。
- 最近 `source-coverage --days 7` 成功，窗口为 2026-09-23 至 2026-09-29。新 OpenAlex、Lil'Log、BAIR、Simon 与 HF Daily checkpoints 均显示最近 poll 成功。Coverage 中 HF Daily 为 124 observations / 124 canonical Artifacts；两个 OpenAlex source 分别为 200 与 170 canonical Artifacts；Lil'Log 53、BAIR 24、Simon 31。这里的 coverage 是滚动窗口按 canonical Artifact 统计，与单次 connector 的 fetched/new/duplicate 计数定义不同。

## 3k / 10k / 30k JSONL 基准

每个规模在独立 Python 进程运行，避免 Windows peak working set 跨样本累计。均为本机临时 synthetic 数据；耗时用于趋势比较，不是跨机器门槛。

| Records | Ingest (s) | Ingest / s | Graph backfill (s) | Edges / s | Corpus snapshot (s) | Peak working set (MB) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 9.777 | 306.86 | 1.248 | 2,403.49 | 21.650 | 130.57 |
| 10,000 | 34.360 | 291.04 | 4.411 | 2,267.18 | 72.004 | 366.76 |
| 30,000 | 103.430 | 290.05 | 15.088 | 1,988.28 | 218.848 | 1,040.17 |

30k / 3k 耗时比分别为 ingest **10.58×**、graph **12.09×**、corpus **10.11×**。Ingest 和 corpus 接近线性；graph 比线性比例高约 21%，后续观察需留意。当前基准没有达到直接迁移 SQLite 的证据门槛；M6 不迁库。

## Live source closeout

### ACTIVE FREE SOURCES

本轮新增并启用：

- **OpenAlex Multi-Agent Systems and Negotiation** — exact topic `T10456`，source `src-07f5ffdc326b2ceedd4f1eb5`。成功；200 fetched、200 new observations、2 pages，遵守每 source 每轮最多 200 Works。
- **OpenAlex AI Problem Solving and Planning** — exact topic `T10906`，source `src-12471e1198d40b6e91bfa693`。成功；198 fetched、170 new observations、28 duplicates、2 pages。
- **Lil'Log** — `https://lilianweng.github.io/index.xml` 探测有效并经批准。成功；53 fetched/new。
- **BAIR Blog** — `https://bair.berkeley.edu/blog/feed.xml` 探测有效并经批准。成功；10 fetched/new。
- **Simon Willison** — `https://simonwillison.net/atom/everything/` 探测有效并经批准。成功；30 fetched/new。
- **Hugging Face Daily Papers** — 最终 smoke 成功；124 fetched，9 new observations，115 duplicates，2 pages。

原有 active free sources 继续包括 OpenAI News、Hugging Face Blog、arXiv cs.AI、arXiv cs.LG，以及 Karakeep、STORM、Transformers 的公开 GitHub Releases。来源配置和 approved RSS subscriptions 已合并进 `sources` 命令结果。

### OpenAlex budget mode

本机 `.env` 中提供的 key 仅作为进程环境变量使用，经 Authorization header 发给 OpenAlex；不写入 repo、source URL、runtime/checkpoint 或日志。模式为 `free_api_key`。两次 OpenAlex poll 后观测到 budget **9,996 / 10,000 remaining**；只保存安全数值字段。剩余比例低于 10% 时，connector 会在发 Works 请求前停止该轮，并使用 provider reset 延后重试。没有启用付费 plan 或预购 credits。

### DEFERRED FREE SOURCES

- **OpenReview submissions — `DEFERRED_UPSTREAM`。** 环境凭据已交给官方 `openreview-py` authenticated client；官方 venue group metadata 可读。但所探测的精确 submission invitation 已过期，当前公开 invitation 查询未找到可用的投稿入口。没有读取 review/comment notes，也没有使用付费服务、CAPTCHA/challenge 绕过或浏览器 Cookie。Connector regression 覆盖 `ChallengeRequired → auth_required`；失效/过期 invitation 分类为 `invalid`，不无限阻塞运行。

### PAID SOURCES = none

Paid external data sources are not required for core operation. 默认只用免费/public API、免费账户/API key 与公开 RSS；若将来 provider 要求付款方式、付费计划或预付 credits，来源状态设为 `deferred_paid`，不会自动购买。

## Source discovery 与工程 gate

RSS discovery 支持标准 `link rel=alternate` RSS/Atom 和文字或 `type` 明确标注 RSS、Atom、Feed 的链接。Lil'Log、BAIR、Simon 都从公开页面实际发现并验证 endpoint；没有猜测 `/feed`、`/rss.xml` 或 `/atom.xml`。每项均先建 SourceProposal，再由本轮明确授权批准。

RI-M6.1 离线回归覆盖：两个生产 OpenAlex mapping、API key 安全传递和安全预算字段、低于 10% 时 defer、OpenReview authenticated client / challenge / expired invitation 分类、RSS anchor feed discovery。Live smoke 验证 HF Daily、两个 OpenAlex topics、Lil'Log、BAIR 和 Simon 的 Observation/Artifact 入库；随后重建 graph、retrieval corpus、Feed 与 Source Coverage。

M6 engineering gate 包含 HF Daily、OpenAlex、RSS live smoke、structured pipeline integration、coverage metrics、规模基准、Python regression、Hugo production build 和 GitHub Actions。全部通过后 M6 标记为 CLOSED。M6-OBS 单独保留到原定 observation window 到期，不阻塞后续工程工作。

## 本机计划任务

用户此前选择的 05:00 Windows Task Scheduler 任务已注册，运行本仓库 `.ri-ops-venv` 的 `intelligence-daily --mode production --scheduled`，设置 `StartWhenAvailable`、联网条件和单实例。提升权限核验显示任务为 Ready、下一次计划时间为 05:00。

## 后续扩展方向（不是 M6.1 工作）

Semantic Scholar 式 positive/negative seeds、ResearchRabbit/Litmaps 式相似文本扩张和反馈驱动候选生成属于后续独立 milestone。M6.1 不增加推荐算法或排序权重。

参考系统提供的是设计线索，不复制其产品 UI 或实现：Karakeep 等阅读器启发 ingestion、storage 和规则边界；ResearchRabbit、Litmaps 和 Semantic Scholar 启发有 provenance 的候选扩张路径；STORM/Co-STORM、PaperQA2 和 SurfSense 启发 provenance 与 cited synthesis。
