---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-m8-4-evidence-quality-report
content_kind: docs
title: "RI-M8.4 Evidence Quality — Luna Synthesis Complete, Human Review Pending"
date: 2026-09-30T00:00:00+08:00
status: draft
visibility: public
summary: Case A Luna synthesis and citation-quality gates passed on the frozen evidence set; the private brief is awaiting user review.
topics: [research-intelligence, search-agent, evidence-quality]
aliases: []
authors: [bubblevan]
---

# RI-M8.4 Evidence Quality & Case A Status

截至 2026-09-30。工作基于 `ad8fdd8 RI-M8.3 real research case and promotion gates`，继续在 `codex/xhs-anonymous-reader-20260927`；没有合并 `main`，没有进入 M9。

## M8.3 文档收尾

[M8.3 Real Research Case](m8-real-research-case.md) 的 Gate K 保持要求值：`373 Python tests; 1196 Hugo pages`，对应已成功的 [GitHub Actions run #111](https://github.com/Bubblevan/bubblevan.github.io/actions/runs/36683771100)。本次没有重跑 Case A 来完成 S0。

## Codex 登录环境与真实调用

CLI 路径为 `D:\npm-global\codex.ps1`，版本为 `codex-cli 0.146.0`。任务 shell 没有继承 `CODEX_HOME`：默认探测返回 `Not logged in`；显式通过 `RI_CODEX_HOME` 指向现有用户 Codex home 后，`codex login status` 返回 `Logged in using ChatGPT`。没有读取认证文件或 token，也没有复制凭据。

首次调用因新进程未显式选择 `RI_RESEARCH_BACKEND` 而返回 `unconfigured`，没有启动 provider。随后显式设置 `RI_RESEARCH_BACKEND=codex`、`RI_CODEX_MODEL=gpt-5.6-luna` 与 `RI_CODEX_HOME` 后完成调用；没有 LiteLLM 或 API key fallback。`RI_CODEX_HOME` 仅作为路径传入子进程的 `CODEX_HOME`，adapter 不读该目录。

## Case A 证据 revision 7

- Corpus hash：`7dba89778c33e7562a06caa097307bccb49472404eec19ae8852048ae7cda853`
- Evidence set hash：`b0a1fcd3756ed452f988ee567cf6ec4b90eec89903597af0f3656731ea6a648a`
- Evidence revision：`7`
- 候选 union：30 个 canonical Artifacts；分别来自 general top 20、first-party top 12、curator top 8 和 discussion top 5。
- 最终选择：5 个 first-party Artifacts，6 条 Observation/source-text 引用和 2 条 metadata 引用；metadata 占 `2/8 = 25%`，并记录 `metadata_fallback=true`。
- Evidence integrity issues：`0`；Dense 状态为 `fresh`，manifest 对应同一 corpus hash。
- Curator / discussion Artifacts：均为 `0`；两项缺口都显式记录为 unavailable，后续 synthesis prompt 要求说明该限制。
- PaperQA2：`unconfigured`。

原始的 M8.3 版本仍保留作比较：11 条 first-party EvidenceRefs、39 条 metadata EvidenceRefs、0 个 curator Artifacts。新版本把 Observation/source text 放在 metadata 前面，不再单独引用 title；metadata 不计入 substantive first-party gate。

经 Observation 原文复核，revision 7 的五篇论文是：

- [IGSD: Environment-Verified Hindsight Self-Distillation for Search Agents](https://arxiv.org/abs/2609.32694)
- [Dr. Free: You Don't Need Difficulty Rewards for Self-Evolving Search Agents](https://arxiv.org/abs/2609.33565)
- [Dr.Credit: Rubric-Grounded Process Credit Assignment for Deep Research Agents](https://arxiv.org/abs/2609.34296)
- [SIPO: Selective-Inference Policy Optimization for Tree-Structured Agentic RL](https://arxiv.org/abs/2609.34805)
- [Rufus-Air: An Open LLM Post-Training Recipe](https://arxiv.org/abs/2609.29421)

其中 seed papers 是用户已选上下文；SIPO 和 Rufus-Air 经本轮检索进入候选。Case A 的 6–8 篇 first-party 是目标范围，不是凑数配额；在固定候选 union 中最终有 5 篇论文通过主题过滤，因此没有把泛 Agent、语音、GUI、search benchmark 或控制任务论文补进证据包。硬门槛（至少 2 个 substantive first-party Artifact、metadata 不超过 25%、真实引用 integrity 通过）均满足。

检索修正包括保留未进入 route Top-K 的显式 seed、为 Search Agent 后训练补充确定性的英文复数与 policy-learning 查询扩展，以及要求非 seed first-party Observation 原文同时出现 Search Agent 主题和训练/蒸馏/奖励/RL/policy optimization 线索。perspective lanes 使用同一个问题和扩展词；curator/discussion 仍须满足 lexical 或 Dense 相关性门槛。

## Synthesis 与质量审计

Case A 使用冻结的 revision 7 Evidence set，成功生成 brief revision 1。Provenance 为 `backend=codex_exec`、`auth_mode=chatgpt`、`billing_mode=chatgpt_plan`、`model=gpt-5.6-luna`；输入 12,250 tokens、输出 2,018 tokens，cost 为 `null`（CLI 未提供费用数据）。Brief 与质量报告保存在本地 private research 目录。

模型输出包含 8 项主张、28 个引用、1 项方法间不可直接排名的分歧。5 项事实主张均有 first-party 证据；unsupported、secondary-only、metadata-only、broken citation 与 missing evidence 均为 0。证据由 6 条论文 Observation 原文和 2 条 metadata 引用组成，metadata share 恰为 25%；curator 与 discussion 证据仍 unavailable，brief 明确说明无法判断社区共识。论文实验优势仅按摘要转述，没有声称已核对全文实验表或独立复现。

首次生成的质量报告没有把 `metadata_share` 纳入指标，因而错误地把精确 25% 判为 blocked。已修复指标传递，并从冻结证据与既有 brief 确定性重算质量报告；没有再次调用模型。当前质量报告 `quality_status=pass`，各项 gate 均通过。无配置响应中的未知 token/cost 也改为 `null`，不会把未知费用报告成 0。

当前私有 brief：`data/intelligence/private/research/briefs/rs-2bc9c18058c23fdc73907d75-r0001.md`。未运行 `research-review`，没有记录用户审阅；private promotion preview、approve、promote 与 publish 均未执行。

| Gate | 状态 |
| --- | --- |
| Real corpus 与冻结证据 | PASS：corpus `7dba8977…`、Evidence set `b0a1fcd3…`、Dense fresh、integrity issues 0 |
| Codex Luna live synthesis | PASS：ChatGPT 登录态、12,250 input / 2,018 output tokens；cost 未知 |
| Citation / factuality audit | PASS：unsupported 0、secondary-only 0、metadata-only 0、broken citations 0、missing evidence 0；metadata share 25% |
| Curator / discussion interpretation | LIMITED：两类证据均 unavailable，brief 未声称社区共识 |
| Human review | PENDING：brief 已生成，等待用户阅读；没有代替用户记录 review |
| Private Hugo preview | NOT CREATED：待用户 review 后再生成 |
| Local Python regression | PASS：385 tests（`.ri-ops-venv`） |
| Local Hugo build | NOT AVAILABLE：此执行环境没有 Hugo executable；远端 production build 已通过 |
| GitHub Actions | PASS：[run #115](https://github.com/Bubblevan/bubblevan.github.io/actions/runs/36711375760)：385 Python tests、Hugo production build、Pages artifact upload 均成功；分支规则跳过 deploy job |
| No auto-publish | PASS：未 approve、promote 或 publish |

请先阅读上面的本机 private brief。确认内容后再告知我继续记录 human review 并生成 private preview；在此之前 M8.4 停在人工审阅门，不会自动发布。
