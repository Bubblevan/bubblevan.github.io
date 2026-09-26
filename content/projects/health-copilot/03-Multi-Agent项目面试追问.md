---
schema: bubblevan/v1
id: project-health-copilot-03-multi-agent-interview
content_kind: project
title: Health-Copilot：Multi-Agent 项目面试追问
linkTitle: 03 · Multi-Agent
weight: 30
date: 2026-09-27
updated: 2026-09-27
status: draft
visibility: public
projects:
  - project-health-copilot
summary: M8 有界、顺序、star-topology Agent Team 的架构、对照实验、负结果和面试答法；不将小样本诊断包装成 Multi-Agent 优势。
topics:
  - multi-agent
  - agent
  - evaluation
  - interview
---

> 这里讲 Health-Copilot M8 的真实实验。Agent 的通用定义、串并行与工具原理放在[通用八股](/projects/health-copilot/05-agent-llm通用八股/)；项目总览在[首页](/projects/health-copilot/)。

## 30 秒版本

> 我实现过一个实验性的 bounded Agent Team，不是通用 agent swarm。它是 star topology：一个 Team Lead，Evidence 和 Guideline 两种角色，单轮顺序 delegation，最多两个 worker/task；TaskStore、Mailbox、EvidenceLedger、共享 RunContext/budget 和最终 M3 claim-support verifier 都由 runtime 管。我们用同一组 12 个闭集 case、每 case 3 次，共 36 个 trial，对比 deterministic workflow、frozen single Agent 和 Team。Team 在 cross-source comparison slice 的 route accuracy 是 .833，single 是 .333；但总体 route accuracy .806 对 .833、evidence-group coverage .333 对 .444、全部试验通过 .250 对 .333，tokens/case 5449 对 4188，elapsed 19.1s 对 7.25s。worker productive report 为 0/12。结论是团队在特定 cross-source slice 有信号，但本组诊断里 overall 更贵、更慢、没有显示总体优势，所以产品默认仍是 single Agent。

## 问题与架构

目标不是“加更多模型”，而是测试 source/role specialization 是否有助于需要多证据组或 cross-source comparison 的任务，同时把 tool/citation 的最终权力留在已有 runtime。

```text
user question → safety gate → initial BM25 Evidence → Team Lead
                                               ├─ FINAL / ABSTAIN
                                               └─ DELEGATE (single wave)
                                                    ├─ Evidence Worker → report
                                                    └─ Guideline Worker → report
                                                           ↓
                                                   Team Lead synthesis
                                                           ↓
                                            M3 claim-support verifier
                                                           ↓
                                          deterministic materialization / abstain
```

固定拓扑为 `star-supervisor-v1`，调度为 `sequential-v1`。Lead 是唯一协调者，worker 只回报给 Lead；没有 worker-to-worker chat、共享 mutable workspace、动态 spawn、并行 worker 或多轮开放式 replanning。

| 部件 | 责任与限制 |
| --- | --- |
| Team Lead | 只能提出 final / abstain / bounded delegation；runtime 验证 role 和 objective |
| Evidence Worker | 聚焦事实证据获取和 source coverage；避免建议综合 |
| Guideline Worker | 聚焦 guideline/recommendation context、publisher/jurisdiction 区分；避免无证据扩写 |
| TaskStore | runtime 创建 task/worker/message IDs，状态受控：PENDING → RUNNING → SUCCEEDED/FAILED/CANCELLED |
| Mailbox | typed、point-to-point 的 assignment/report/error；拒绝 broadcast 和 worker-to-worker message |
| TeamEvidenceLedger | 标明 INITIAL 或 WORKER source provenance；worker 只能引用自己实际观察到的 source |
| Shared parent RunContext | provider/tool/token/deadline budget 共用，不让每个 worker 各自绕开总预算 |
| Final verifier | 复用 M3：citation integrity、claim support、确定性 materialization；worker consensus 不能替代 evidence support |

默认限制：最多两次 Lead calls、最多两个 tasks/workers、一轮 delegation；每个 worker 最多两次 model turns、一次 tool execution。urgent/prescription 在建 Team 前 short-circuit。

## 对照是怎么做的

冻结 suite `m8-agent-team-focused-v1` 有 12 个 closed-corpus case：4 direct、4 decomposable、2 cross-source comparison、2 uncovered/OOD；human_reviewed_frozen。每个 arm 同样 12 case × 3 trials：

| Arm | 含义 |
| --- | --- |
| L0 Workflow | deterministic retrieval + 一次 final-only model call |
| L1 Single | frozen `m3-bm25-default` 单 Agent |
| L2 Team | `m8-team-bm25-v1` bounded Team |

三组共享数据、BM25、provider model 和 final verifier。这里比较的是 orchestration/control flow，不是换掉 corpus、retriever、模型之后把收益错归因给 Team。报告同时看 outcome、consistency、evidence coverage、provider/tool calls、token、latency、budget 与 failure taxonomy。

## 真实结果：没有总体胜利

最终 v2 frozen comparison（36 trials）：

| Metric | L0 Workflow | L1 Single | L2 Team | 面试解释 |
| --- | ---: | ---: | ---: | --- |
| route accuracy | .806 | **.833** | .806 | Team 与 workflow 持平，低于 single |
| expected-answer rate（30 个 answer-expected trials） | .767 | **.833** | .767 | Team 没提高 overall answer completion |
| evidence-group coverage | .333 | **.444** | .333 | Team 未补足所有需要的 evidence groups |
| OOD answer pass rate | 1.000 | .833 | 1.000 | 只 2 个 OOD case，不能讲总体安全提升 |
| all-trials-pass | .333 | .333 | .250 | Team 最低 |
| route consistency | .833 | .750 | .500 | Team 对相同 case 的输出更不稳定 |
| citation integrity | 1.000 | 1.000 | 1.000 | 窄的 ID/provenance contract；不是 semantic correctness |
| provider calls / case | 1.556 | 2.361 | 2.361 | Team 与 single 平均调用数相同但团队任务没有产出 |
| total tokens / case | 3,245 | 4,188 | 5,449 | Team 比 single 多约 1,261 tokens/case |
| elapsed ms / case | 8,662 | 7,248 | 19,096 | Team 比 single 慢约 11.8 秒/case |

按类别看，最有意思的正向 slice 是 `cross_source_comparison`：route accuracy L1 `.333`，L2 `.833`，差 `+.500`。但 direct case 是 L1 `1.000`、L2 `.750`；decomposable 是 `.917` 对 `.750`。这说明复杂 cross-source 场景可能需要来源/职责分解，但团队的固定协调成本可能伤害简单任务。

重要失败事实：L2 有 9 次 delegate action，8 次 trial 至少 delegation，创建并启动 12 个 worker；**worker completion 0/12，productive report 0/12**（11 次在 `max_tool_calls` 前失败，1 次 `model_error`）。因此不能把 cross-source category 的变化归因成“worker 找到更多独特证据”；当前更可能是 Lead 的决策/流程差异。全 context worker evidence overlap 是 1.0、unique contribution 0.0（仅 4 个可比多 worker observations），Recovery-only contribution 也为 0。

v1 曾有 33/36 `lead_error`，旧 trace 信息不足，不能倒推是哪种 provider/JSON/contract 错误。M8.3 增加明确 failure taxonomy 和可观测性后，v2 没有 Lead/provider failure，但 worker 仍 0/12。应把 v1 说成接口诊断失败，而不是“Agent Teams 本质上很差”；v2 才是修复后 frozen comparison。

## 什么可以叫贡献

- 把 Team 的 topology、worker role、消息协议、budget、任务状态和 citation provenance 变成可审计 runtime contract。
- 用相同 case/model/retriever/verifier 的 L0/L1/L2 比较，将 quality、consistency 和 cost 分开报告。
- 把 0/12 worker completion 作为真实 failure 记录，避免把 delegation intent 冒充有用协作。
- 数据表明 cross-source slice 可能是值得进一步研究的任务类型，但当前 evidence 不足以证明真实 worker specialization 增益。

不是新 multi-agent 算法；不支持“并行降低 latency”（本系统刻意顺序执行）；不支持“Team overall 提升质量”；也不是产品默认运行方式。

## 高频追问

### “为什么要做 Multi-Agent？”

需要区分简单问题和 breadth/cross-source 任务。单 Agent 对直答通常便宜；当不同来源、证据组或 guideline jurisdiction 要分开处理时，角色隔离可能改善覆盖与可追踪性。我们把这个假设变成 bounded experiment，而不是先假设 agent 数量越多越好。

### “两个 worker 真的是异构模型吗？”

不是。异构的是职责/contract（Evidence 与 Guideline），没有做模型异构性实验。它们可共用 provider/checkpoint/executor。不要把 role specialization 写成 heterogeneous-model ensemble。

### “为什么不并行，岂不是更快？”

M8 先冻结 sequential scheduler，因为 `RunBudgetState`、`RunTrace` 等是 per-run mutable control state；先把任务生命周期、证据 provenance、共享预算和 failure semantics 验证清楚，再谈并行。并行不是免费的，需要并发预算、错误聚合、取消、结果顺序和一致性语义。实际 M8 比 L1 慢，不存在 latency improvement 证据。

### “多 agent 是否提升了整体效果？”

没有。它只在 2-case cross-source slice 上有 route accuracy 的正向差异；overall route accuracy/evidence coverage/all-trials-pass 不如 frozen single，而且成本和时延更高。样本很小，所以只能讲 diagnostic signal，不做 generalization claim。

### “worker 没成功，为什么还值得保留结果？”

因为这暴露了真正瓶颈：Lead 能发 delegation 不等于 worker 能产生可验证、独特的 evidence。completion、productive report、unique evidence contribution 必须分开定义；否则只看 agent call/任务数会把空转当成协作能力。

### “安全边界由谁掌握？”

模型只能提出 decision/report。Runtime 验证 role allowlist、task ID/state、参数、预算和来源 provenance；最终 citation 必须在 ledger，claim 必须通过 M3 verifier，之后才由 runtime materialize。urgent/prescription 先于 team 构造短路。

### “这有外部 benchmark 分数吗？”

没有。它是一个 12-case closed-corpus、36 trial/arm 的 focused diagnostic，不是公开 Multi-Agent benchmark、临床验证或规模定律。HealthBench/MultiAgentBench 等没有在这个 M8 实验上执行。

## 面试结尾：结论与下一步

> M8 的收获不是“Team 一定更好”，而是把适合 Team 的条件和协调失败变得可见。cross-source slice 有潜在线索，但 worker 没有贡献可用的独特 evidence，overall quality/cost 也不支持切成 Team default。如果继续，我会先修 worker invocation/contract 并用独立 holdout 验证它能否完成并增加唯一 evidence，再比较只对复杂 slice 路由 Team 与 always-single；不会先扩大 worker 数或 claim 并行提速。

但 M8 已冻结，不会为简历数字继续改写当时结果。证据入口：`docs/m8_agent_team.md`、`docs/m8_empirical_v1_failure.md`、`docs/m8_empirical_v2_closeout.md`。
