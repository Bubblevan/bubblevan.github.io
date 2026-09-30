---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-m8-real-research-case
content_kind: docs
title: "RI-M8.3 Real Research Case — Blocked at Codex Authentication"
date: 2026-09-30T00:00:00+08:00
status: draft
visibility: public
summary: Real-corpus evidence collection and honest M8.3 gate status for Search Agent post-training; Luna synthesis is blocked because the local Codex CLI reports no login.
topics: [research-intelligence, search-agent, operations]
aliases: []
authors: [bubblevan]
---

# RI-M8.3 Real Research Case

截至 2026-09-30。Real Case A 的本地证据采集与引用完整性检查通过；Codex 登录探测明确返回 `auth_unavailable`，因此没有执行 Luna synthesis。M8.3 **未完成**，当前停止在 synthesis 之前，未生成 review、promotion preview 或公开研究笔记。

## Research Case A

问题：

> 2026 年 Search Agent 后训练最近真正发生了什么变化？哪些方法改进有原始论文证据支持，哪些只是社区或 curator 的解释？

- Research Case ID：`rs-2bc9c18058c23fdc73907d75`
- Corpus hash：`7dba89778c33e7562a06caa097307bccb49472404eec19ae8852048ae7cda853`
- Evidence set hash：`d887b75e3d8116881a5422d7b4849d4617fed705737e63fc6826e5757d9dda04`
- Dense：`fresh`；BM25、Dense、topic 三条 retrieval route 均成功；Graph 只用于 exact provenance lookup。
- 检索候选：20 Artifacts；Evidence selector 选择 12 个位置，其中 10 个 Artifact 实际产生了引用；共 50 EvidenceRefs。预算为 20 个 retrieval 候选、12 个 evidence Artifacts、50 条引用、每个 Artifact 最多 6 条、最多 80,000 字符。
- Evidence composition：10 个 first-party Artifacts、0 个 curator Artifacts、0 个 discussion Artifacts、10 个含 metadata 的 Artifacts；50 条引用中 11 条 first-party、39 条 metadata。Evidence integrity issue 为 0；real-case synthetic marker 检查没有命中。
- PaperQA2：`unconfigured`。

## Seeds and collected sources

三个 seeds 均来自当前 canonical corpus 的 arXiv 论文：

- IGSD — [Environment-Verified Hindsight Self-Distillation for Search Agents](https://arxiv.org/abs/2609.32694)
- Dr. Free — [You Don't Need Difficulty Rewards for Self-Evolving Search Agents](https://arxiv.org/abs/2609.33565)
- Dr.Credit — [Rubric-Grounded Process Credit Assignment for Deep Research Agents](https://arxiv.org/abs/2609.34296)

实际产生 EvidenceRefs 的 10 个 Artifacts：

- [IGSD: Environment-Verified Hindsight Self-Distillation for Search Agents](https://arxiv.org/abs/2609.32694)
- [Dr. Free: You Don't Need Difficulty Rewards for Self-Evolving Search Agents](https://arxiv.org/abs/2609.33565)
- [Dr.Credit: Rubric-Grounded Process Credit Assignment for Deep Research Agents](https://arxiv.org/abs/2609.34296)
- [Inspire: Benchmarking Scientific Literature Search for Open Research Problems](https://arxiv.org/abs/2609.33233)
- [From Search to Research: Exploring Search Scaling in Autonomous Quantitative Factor Mining](https://arxiv.org/abs/2609.35559)
- [PEAR: Progressive Evidence-Based AutoResearch for Industrial Search Systems](https://arxiv.org/abs/2609.35031)
- [Beyond Scripted Search: Sample-Efficient Reward Discovery via Agentic Black-box Optimization](https://arxiv.org/abs/2609.32394)
- [Evaluating Real-Time Voice Agents: From Component Quality to Grounded Outcomes](https://arxiv.org/abs/2609.30798)
- [What is Missing from AI Post-Training AI: An Empirical Analysis](https://arxiv.org/abs/2608.19072)
- [Agentic Resource Discovery: Let agents search](https://huggingface.co/blog/agentic-resource-discovery-launch)

检索候选中包含与本题关系较弱的 Agent/Voice 论文，且收集到的 Evidence 没有独立 curator 或 discussion 来源。检索结果因此需要在 Luna 可运行后继续检查；这次收集本身不能证明最终综述值得发布。

## Synthesis and quality gate

- Requested backend/model：`codex_exec` / `gpt-5.6-luna`。
- Codex CLI：`codex-cli 0.146.0`。
- Auth mode：`auth_unavailable`。`codex login status` 明确返回未登录；未执行模型 inference。
- Billing mode、input tokens、output tokens、cost：`null` / 未知。没有尝试 LiteLLM、OpenAI API key、Claude、Gemini 或本地模型 fallback。
- Claim count、unsupported facts、secondary-only facts、disagreements、broken citations、missing evidence：未评估，因为没有 synthesis。EvidenceSet 本身完整性检查为 0 issues；这不等同于 claim citation audit 通过。
- Quality JSON：保存在 private research reports，状态 `claim_metrics_not_evaluated`；未把不可评估指标记成 0。
- Hugo preview：`not_created`。Research review surface 的回归覆盖通过，但当前没有 brief 可供用户逐条审阅，因此没有写入 `research-review` 或假设 `reviewed_by=bubblevan`。

## Gate status

| Gate | 状态 |
| --- | --- |
| A — Auth provenance | PASS：只按 CLI 输出判定为未登录；billing 未知 |
| B — Real corpus | PASS：Evidence 来自真实 canonical corpus |
| C — Primary evidence | PASS：10 个 first-party Artifacts |
| D — Real Luna synthesis | BLOCKED：本机 Codex CLI 未登录 |
| E–G — Citation/factuality/interpretation | NOT RUN：没有 synthesis |
| H — Human review | NOT RUN：没有 brief |
| I — Private Hugo preview | NOT CREATED |
| J — No auto-publish | PASS：未 review、approve、promote 或 publish |
| K — Regression/build/CI | PASS：373 Python tests、1196 Hugo pages；[GitHub Actions run #111](https://github.com/Bubblevan/bubblevan.github.io/actions/runs/36683771100) 全部成功，包含 Hugo 0.153.0 production build 和 Pages artifact upload。 |

继续本 Case A 前，需要在这台机器的 Codex CLI 完成 ChatGPT 登录，然后重试 `research-synthesize rs-2bc9c18058c23fdc73907d75`。确认 CLI 显示 ChatGPT 登录后，才能继续 citation/claim quality audit、review surface、private preview，并在真实内容可见后交用户审阅。
