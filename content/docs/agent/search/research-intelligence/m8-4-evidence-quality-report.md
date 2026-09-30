---
schema: bubblevan/v1
id: docs-agent-search-research-intelligence-m8-4-evidence-quality-report
content_kind: docs
title: "RI-M8.4 Evidence Quality — Luna Synthesis Blocked"
date: 2026-09-30T00:00:00+08:00
status: draft
visibility: public
summary: M8.4 evidence-quality gates and Case A evidence revision; live Luna synthesis remains unavailable because the active Codex CLI reports no login.
topics: [research-intelligence, search-agent, evidence-quality]
aliases: []
authors: [bubblevan]
---

# RI-M8.4 Evidence Quality & Case A Status

截至 2026-09-30。工作基于 `ad8fdd8 RI-M8.3 real research case and promotion gates`，继续在 `codex/xhs-anonymous-reader-20260927`；没有合并 `main`，没有进入 M9。

## M8.3 文档收尾

[M8.3 Real Research Case](m8-real-research-case.md) 的 Gate K 保持要求值：`373 Python tests; 1196 Hugo pages`，对应已成功的 [GitHub Actions run #111](https://github.com/Bubblevan/bubblevan.github.io/actions/runs/36683771100)。本次没有重跑 Case A 来完成 S0。

## Codex 登录环境诊断

只读取 Codex CLI 的公开诊断输出；没有打开认证目录、`auth.json` 或任何 token。

| 项目 | 当前执行环境 |
| --- | --- |
| CLI 路径 | `D:\npm-global\codex.ps1` |
| CLI 版本 | `codex-cli 0.146.0` |
| `codex login status` | `Not logged in` |
| `USERPROFILE` / `HOME` | 前者存在；后者不存在 |
| `CODEX_HOME` / `RI_CODEX_HOME` | 均未设置 |

仓库中可找到一个 synthetic 研究 session，但它的状态是 `evidence_ready`、`model_config` 为空、brief revision 为 0；没有记录成功的 Luna 调用。M8.2 的历史调用环境也没有留存登录状态快照。因此无法从现有记录证明那次 smoke 使用了哪个 Codex home，或精确解释两次执行上下文的差别。当前可确认的是：本次 CLI 进程没有可用登录态；此前与当前执行上下文或 Codex home 不同是可能原因，但仍属推测。

M8.4 支持可选 `RI_CODEX_HOME`：仅把这个路径传给 `codex exec` 子进程的 `CODEX_HOME`，不读取目录、不复制凭据。相关回归确认了传递行为与不读取认证文件。当前未配置该变量，也没有采用 API key、LiteLLM 或其他 provider 兜底。

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

## Synthesis 与后续门

在重新检查 `codex login status` 后，它仍返回 `Not logged in`。本次没有启动 Case A 的 `research-synthesize`，也没有发起 provider 请求。状态为 `auth_environment_unavailable`；provider/backend 的实际调用未发生，billing、input/output tokens 与 cost 均为 `null` / 未知，没有宣称为零。Claim/citation/factuality metrics 未评估，未生成 brief、`research-review` 或 private preview，也没有 approve、promote 或 publish。

| Gate | 状态 |
| --- | --- |
| Real corpus | PASS：canonical corpus、fresh Dense 和有效 EvidenceRefs |
| Evidence quality | PASS：5 篇主题匹配的 first-party 论文、metadata 25%、integrity issues 0；未达到 6–8 的目标范围，没有填充无关内容 |
| Codex Luna live synthesis | BLOCKED：`auth_environment_unavailable` |
| Citation / factuality audit | NOT RUN：尚无 brief |
| Human review | NOT RUN：用户尚无真实 brief 可检查 |
| Private Hugo preview | NOT CREATED：须先完成真实 synthesis 和用户 review |
| Local Python regression | PASS：384 tests |
| Hugo production build / GitHub Actions | PASS：[run 36691676391](https://github.com/Bubblevan/bubblevan.github.io/actions/runs/36691676391) 的远端 384 tests、Hugo production build 和 Pages artifact upload 均成功；`main` deploy job 按分支规则跳过。 |

恢复时，请在本机 Codex CLI 完成 ChatGPT 登录并确认 `codex login status` 显示已登录；若登录态属于另一个 Codex home，在运行 Research Intelligence 的进程启动前设置 `RI_CODEX_HOME` 为那个已有目录路径即可，不要复制认证文件。随后对现有 Case A 执行 `research-synthesize`，再检查真实 brief 和 citation/factuality audit；用户本人确认 review 后，才可生成 private preview。M8.4 其余工作在这些门完成前保持未完成。
