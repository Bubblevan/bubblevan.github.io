---
schema: bubblevan/v1
id: 
content_kind: project
title: TraceSearch-R1 项目面试追问
linkTitle: 01 · 项目面试追问
weight: 10
date: 2026-09-19
updated: 2026-09-19
status: draft
visibility: public
projects:
  - 
summary: 
topics:

---

# TraceSearch-R1 项目面试追问

> 事实截面：2026-09-19。当前 Git `HEAD = 7273383aa131ffebb1fe03c579ee65235eb788a7`，但 M0 相关源码、数据、测试和 run artifact 仍包含未提交修改或未跟踪文件。
>
> 本文只回答“TraceSearch-R1 当前实际做了什么、为什么这样做、如何证明”。通用的 Search Agent、Agentic RL、credit assignment、系统和多模态知识统一放在 [`bagua.md`](bagua.md)。
>
> 状态标签：`[WORKTREE IMPLEMENTED]` 表示当前工作区代码可见；`[ARTIFACT VALIDATED]` 表示有本地 run/test artifact，但不自动等于已提交或 benchmark 结论；`[PLANNED]` 表示设计或路线图中的后续能力。

## 先记住的 30 秒版本

TraceSearch-R1 是一个研究多轮 Search Agent 失败传播与 credit assignment 的个人研究/工程项目。当前 M0 不是 RL 训练系统，而是一套可复现的 research substrate：它把 `Task`、policy decision、`search/visit/answer` action、结构化 `ToolResult`、`Step`、`Trajectory`、离线环境、故障注入、指标和 run artifact 分开保存，为后续比较 Search-R1 风格训练、fatal-aware masking 和 contribution-weighted advantage 提供同一实验边界。

当前已经能在小型 synthetic fixture 上运行确定性的 BM25 Search/Visit 环境，保存 manifest、trajectory、metrics 和 summary，并重算答案、证据召回、工具失败与终止指标。当前 smoke run 使用显式命名的 `OracleFixturePolicy`，会读取 evaluation-only gold evidence；因此它只能验证环境与产物链路，不能说明模型学会了搜索，更不能声称 RL、GRPO、CW-GRPO 或多模态能力已经实现。

## 面试前的事实纪律

| 能力 | 当前状态 | 证据 | 可以怎么说 |
| --- | --- | --- | --- |
| typed Task/Action/ToolResult/Step/Trajectory | `[WORKTREE IMPLEMENTED]` | `src/tracesearch/data/schema.py` | M0 固定了 policy、environment、evaluator 和未来 trainer 的共享数据边界 |
| async Search/Visit/Answer loop 与预算终止 | `[WORKTREE IMPLEMENTED]` | `src/tracesearch/agent/loop.py` | runtime 能执行 sync/async policy 和 tool，并记录结构化轨迹 |
| 本地 BM25 Search/Visit 环境 | `[WORKTREE IMPLEMENTED]` | `src/tracesearch/environment/` | 当前默认是 aligned offline fixture，不是 live Web |
| deterministic fault injection | `[WORKTREE IMPLEMENTED]` | `environment/faults.py`、`tests/test_faults.py` | 可定点或按 seed 注入 failure，便于做干净消融 |
| manifest/trajectory/metrics/summary | `[ARTIFACT VALIDATED]` | `runs/m0-*-final/` | 产物链路可运行；必须同时说明 worktree dirty 与 Oracle policy |
| learned policy、真实 LLM inference | `[PLANNED]` | README / design | 当前没有模型服务或学习到的搜索策略 |
| SFT、PPO、GRPO、GSPO、verl/rLLM | `[PLANNED]` | research roadmap | 当前没有训练 objective、optimizer 或 rollout-training integration |
| fatal-aware training mask | `[PLANNED]` | `rewards/credit.py` 只有 failure index/helper | helper 不等于训练 loss 已接入 |
| contribution judge / CW-GRPO | `[PLANNED]` | `weighted_advantages` 只有占位式映射 | 没有 judge、过程标注或真实消融 |
| live Web、multimodal search、memory | `[PLANNED]` | design non-goals | 不能写成当前能力 |

特别注意：`runs/*/manifest.json` 中记录了 `7273383...`，但当前 M0 文件没有全部提交。这个 hash 不能单独证明 artifact 可由该 commit 干净复现；对外表述应写“当前工作区 M0 artifact”，直到实现与 artifact 一起提交并从 clean checkout 复跑。

## 第一轮：项目定位与整体架构

### Q1：请介绍一下 TraceSearch-R1。

#### 30 秒回答

TraceSearch-R1 研究的不是“能不能调一次搜索 API”，而是多轮 Search Agent 中失败如何沿轨迹传播，以及最终 outcome 应如何分配到 search、visit 和 reasoning step。M0 先把任务、环境、动作、观察、轨迹、故障和评测固定成可复现边界；M1 及之后才会在相同边界下比较 SFT/RL、fatal-aware 和 contribution-weighted credit assignment。

#### 深挖

当前控制链是：

```text
Task
  → PolicyOutput(reasoning, Action)
  → search / visit / answer
  → ToolResult
  → Step
  → Trajectory
  → evaluator
  → manifest + trajectories + metrics + summary
```

核心设计是让 environment output 成为结构化事实，而不是只保留一段不可重放的日志。后续 trainer 可以读取同一种 trajectory schema，而不必猜测旧日志中哪些字符串代表 timeout、empty result 或 irrelevant result。

#### 源码落点

- `src/tracesearch/agent/loop.py`：`SearchAgent.run_async`。
- `src/tracesearch/data/schema.py`：M0 canonical objects。
- `src/tracesearch/experiment/runner.py`：离线 M0 runner。
- `src/tracesearch/evaluation/metrics.py`：可从保存轨迹重算的指标。

#### 证据

- `runs/m0-smoke-final/` 与 `runs/m0-faults-final/` 保存四类 artifact。
- `tests/test_m0_integration.py` 验证 artifact 写入与指标重算。

#### 当前边界

这是 M0 research substrate，不是已经训练完成的 Search-R1 模型，也不是线上 Deep Research 产品。

### Q2：它真正研究的问题是什么？

#### 30 秒回答

它关注两个问题：第一，工具失败、无关结果或错误访问如何影响后续 trajectory；第二，只有最终答案 reward 时，怎样避免把同一个 outcome advantage 粗暴地平均归因给所有搜索步骤。

#### 深挖

最终答案成功不代表每个搜索步骤都有用；最终答案失败也不代表所有 prefix step 都错。前者可能包含冗余搜索或错误访问，后者可能在最后生成、超时或某个后缀步骤才失败。因此需要把 execution failure、semantic failure、process quality 和 final outcome 分开记录，再比较不同 credit assignment 进入 objective 的位置。

#### 源码落点

- `src/tracesearch/environment/faults.py`：可复现 failure injection。
- `src/tracesearch/rewards/credit.py`：`fatal_step_index`、`weighted_advantages` 的早期 helper。
- `docs/design.md`：fatal-aware 与 contribution weighting 的研究假设。

#### 当前边界

当前只有表示层和 helper，没有训练 loss、judge-produced contribution 或有效性消融。

### Q3：为什么它不是普通 RAG？

#### 30 秒回答

普通 RAG 常把 retrieval 当作生成前的一次固定步骤；TraceSearch-R1 的研究对象是多轮 policy：模型可以根据 observation 决定继续 search、visit 还是 answer，动作会改变后续 state、成本和失败路径。重点是 trajectory policy 与 credit assignment，不只是把文档放进 prompt。

#### 深挖

M0 的本地 BM25 只是可控 environment backend。即使把 BM25 换成 live Web，若控制流仍是固定 retrieve-once，它也不自动成为 Search Agent。反过来，当前虽然有 action loop，但 Oracle fixture policy 不代表学习到的自主策略。

#### 当前边界

不能因为存在 `SearchAgent` 类，就声称当前已经验证了 learned agent policy。

### Q4：为什么不能只写一个 harness？

#### 30 秒回答

Harness 能约束工具、预算、超时和记录，但研究问题还要求稳定的数据、环境、reward、trajectory schema 和可比较实验。只写一个能调用工具的 loop，无法回答某种 credit assignment 是否有效，也无法区分变化来自 policy、数据还是搜索后端。

#### 深挖

Harness 是必要的执行边界；research substrate 还需要任务划分、gold evidence 隔离、corpus hash、seed、fault profile、artifact schema 和 metrics denominator。TraceSearch-R1 M0 的价值正是把这些变量显式化。

#### 当前边界

当前 M0 更准确的名字是“可复现 Search Agent 实验脚手架”，不是完整 RL infrastructure。

## 第二轮：Trajectory、Environment 与数据边界

### Q5：一条 trajectory 怎么执行？

#### 30 秒回答

`SearchAgent.run_async` 为 Task 创建 Trajectory，循环调用 policy 得到 `PolicyOutput`。`answer` 直接终止；`search/visit` 交给 environment，返回 `ToolResult` 后写成 Step。达到答案、最大 turn、工具预算或 policy error 时记录明确 termination reason。

#### 源码落点

- `agent/loop.py`：policy 调用、tool dispatch、budget、termination。
- `data/schema.py`：Step/Trajectory 的序列化与派生计数。

#### 面试官继续追问

- 为什么 budget 在调用 policy 前检查？
- sync wrapper 为什么不能在已有 event loop 中直接调用？
- policy exception 与 environment error 为什么要分开？

### Q6：Search 和 Visit 有什么区别？

#### 30 秒回答

Search 根据 query 返回带 rank/score/snippet 的候选 Evidence；Visit 根据稳定 `doc_id` 读取完整对齐文档。前者解决“找哪些候选”，后者解决“展开哪条证据”，二者的成本、失败和 credit 不应混在一起。

#### 源码落点

- `environment/bm25.py`：candidate ranking。
- `environment/local.py`：`search` 与 `visit` 的不同返回协议。
- `environment/tools.py`：工具 Protocol。

#### 当前边界

当前 Visit 读取本地 corpus，不是网页抓取器，也没有动态网页、robots、登录或内容漂移问题。

### Q7：为什么 observation 必须属于 environment output？

#### 30 秒回答

Observation 描述环境实际返回了什么；policy 只能提出 Action，不能自己宣称“搜索成功”或伪造证据。把 observation 固定为 `ToolResult`，才能区分 success、timeout、empty、malformed 与 semantic corruption，并在训练和评测时追溯事实来源。

#### 深挖

M0 仍保留渲染后的 observation text 供 policy/context 使用，但 canonical fact 是结构化 `ToolResult`。文本只是 projection，不应反过来成为唯一事实源。

#### 源码落点

- `data/schema.py`：`ToolResult` invariant。
- `environment/render.py`：结构化结果到文本 observation 的渲染。

### Q8：为什么 environment alignment 很重要？

#### 30 秒回答

如果任务的 gold evidence 在环境中不存在、doc ID 对不上或搜索后端无法召回，那么 policy 无论怎样学习都不可能完成任务。此时训练信号会把环境缺陷误归因给模型，导致 reward 噪声和错误 credit。

#### 深挖

M0 fixture 要求每个 gold ID 存在于 corpus；普通 policy 只能看到 `Task.policy_view()`，看不到 answer alias 和 gold evidence。Oracle policy 只用于 smoke runner，并通过显式名称与 `allow_gold_evidence` 标记隔离。

#### 当前边界

synthetic aligned fixture 证明的是 plumbing，不代表真实 Web task 的 solvability、uniqueness 或难度分布。

### Q9：为什么先做 offline simulator，而不是直接接 live Web？

#### 30 秒回答

离线环境能固定 corpus、排序、seed 和 fault position，适合回归测试和 attribution 消融；live Web 更接近真实部署，但内容、排名、延迟和失败随时间变化，很难判断实验差异来自 policy 还是环境漂移。

#### 深挖

合理路线不是二选一，而是 offline 用于机制验证和 clean ablation，之后再做 sim-to-real：冻结任务与预算，记录 live backend/version/cache，并单独报告环境变化。

#### 当前边界

当前只有 local BM25 环境，没有 live Web adapter 或 sim-to-real 结果。

## 第三轮：故障、评测与可复现性

### Q10：execution failure 和 semantic failure 有什么区别？

#### 30 秒回答

Execution failure 表示工具没有正常产生结果，例如 timeout、exception、malformed 或 empty；semantic failure 表示调用技术上成功，但内容与任务无关或误导。两者对 retry、credit 和评测的含义不同。

#### 源码落点

- `environment/faults.py`：`IRRELEVANT_RESULT` 与其他 fault type 分离。
- `environment/local.py`：无关结果保留 `ok=True`，并写 semantic-corruption metadata。

#### 面试官继续追问

- 为什么 irrelevant result 不能记成 timeout？
- policy 是否应该对 execution failure 和 semantic failure 采用相同重试策略？

### Q11：为什么需要 fault injection？

#### 30 秒回答

真实 API failure 不可控、样本稀少且难复现，不能支持干净的 ablation。FaultSchedule 可以命中确定的 task/step/tool；FailureInjector 用固定 seed 和抽样顺序生成可复现故障，使两种策略在同一 failure surface 上比较。

#### 证据

`runs/m0-faults-final/metrics.json` 记录 10 次 injected timeout；这证明注入与计数路径运行，不证明某种恢复策略优于另一种策略。

### Q12：怎么保证实验可复现？

#### 30 秒回答

至少固定代码状态、task/corpus、corpus hash、split、policy/model、search backend、seed、tool budget、fault config、reward/training config 和 artifact schema。只保存最终分数不够，因为无法判断差异来自哪一个变量。

#### 源码落点

- `experiment/manifest.py`：manifest schema。
- `data/hashing.py`：canonical corpus hash。
- `experiment/artifacts.py`：artifact writer。
- `evaluation/metrics.py`：从 tasks + trajectories 重算指标。

#### 当前边界

当前 manifest 记录 commit hash，但没有 dirty-worktree fingerprint；在实现尚未提交时，这仍是复现缺口。

### Q13：当前 M0 指标能证明什么？

#### 30 秒回答

它们能证明 12 条 synthetic fixture 在 Oracle policy 下贯通了 search/visit/answer、故障注入、trajectory 保存和 metrics 重算。它们不能证明 learned search quality、泛化、真实 Web 鲁棒性或 RL 收益。

#### 证据

`m0-smoke-final` 记录 12/12 answer 与 evidence 指标；`m0-faults-final` 记录 10 次 timeout 和 `tool_failure_rate=0.2777...`。两组都使用 `OracleFixturePolicy`，数据又与 gold evidence 对齐，因此不能把 `exact_match=1.0` 当模型 benchmark。

#### 当前边界

任何简历表述都应强调“deterministic fixture integration validation”，而不是“搜索准确率 100%”。

### Q14：为什么 OracleFixturePolicy 不算数据泄漏 bug，却也不能拿来评模型？

#### 30 秒回答

它被显式命名、只用于 smoke runner，并通过 `allow_gold_evidence=True` 有意读取 gold ID，因此适合验证 environment 和 artifact plumbing。它若被混进训练或模型 benchmark 就会构成 answer/evidence leakage。

#### 源码落点

- `agent/policy.py`：Oracle policy 的边界声明。
- `agent/loop.py`：普通 policy 接收 `task.policy_view()`。

## 第四轮：从 M0 走向 Agentic RL

### Q15：当前已经完成什么，哪些仍是 planned？

#### 30 秒回答

当前完成的是 M0 typed trajectory、async loop、本地 Search/Visit、BM25、预算和终止、故障分类与注入、manifest/artifact、离线指标和 synthetic fixture。没有完成 learned policy、LLM serving、SFT/RL、GRPO/PPO、rollout-training engine、contribution judge、真实 benchmark、live Web 或 multimodal tools。

#### 当前边界

`fatal_step_index` 和 `weighted_advantages` 只是研究接口/helper，不能写成 fatal-aware GRPO 或 CW-GRPO 已经训练验证。

### Q16：为什么 Search Agent 适合研究 RL？

#### 30 秒回答

搜索是序列决策：query、是否 visit、是否继续 search、何时 answer 都会影响后续状态、成本与最终结果；很多高质量动作没有逐步标签，而最终答案又可部分验证，所以 RL 有研究价值。

#### 深挖

但“适合研究”不等于“RL 一定优于 SFT”。必须先有足够难度且可解的任务、可靠环境、稳定 verifier、合理预算和无泄漏数据，再与 prompt/SFT/rejection sampling 等基线比较。

#### 当前边界

当前项目尚无 RL 实验，不能把研究动机写成结果。

### Q17：Fatal-aware masking 想解决什么？

#### 30 秒回答

如果 trajectory 在某一步进入不可恢复的连续 failure cascade，后续 token/action 可能只是在坏状态上继续滚动。Fatal-aware 方法尝试识别 fatal boundary，避免把后缀噪声与早期可能有效的 prefix 一起更新。

#### 当前边界

当前 `fatal_step_index` 只按连续失败阈值定位候选边界；还没有证明这个启发式等价于真正 fatal、没有接入 token mask，也没有消融 bias/variance 与 reward hacking。

### Q18：`weighted_advantages` 当前做了什么，没做什么？

#### 30 秒回答

它把一个 trajectory-level advantage 按非负 contribution weight 归一化到各 step，并保持平均尺度；缺失 contribution 默认中性 1.0。它没有生成 contribution、没有实现 judge、没有修改 GRPO loss，也没有回答 process quality 应该乘 outcome advantage 还是直接加入 reward。

#### 源码落点

`src/tracesearch/rewards/credit.py`。

#### 面试官继续追问

- 全部 contribution 为 0 为什么返回全 0？
- clamp 到非负会丢失什么信息？
- successful trajectory 中的坏步骤如何得到负向信号？
- 直接加 process reward 与用 process quality 加权 outcome advantage 有何不同？

## 真实踩坑与待补证据

1. **Commit hash 不足以描述当前 M0**：artifact manifest 指向初始 commit，但实现处于 dirty worktree；后续要从 clean checkpoint 复跑。
2. **Oracle 指标极易被误读**：12 条 synthetic fixture 的满分只验证 plumbing，不是模型能力。
3. **结构化成功不等于语义成功**：irrelevant result 必须与 timeout 等 execution failure 分开。
4. **固定 latency 与 wall-clock latency 不同**：真实测量值包含运行抖动，不应当作严格 determinism 证据。
5. **Credit helper 不等于训练算法**：没有 reward→advantage→loss 的真实链路，就不能使用“实现 CW-GRPO”的表述。

## 一页式复述顺序

1. 研究问题：多轮搜索失败传播与 credit assignment。
2. M0 目的：固定 task/policy/environment/trajectory/eval 的可复现实验边界。
3. 控制流：`Task → PolicyOutput → Action → ToolResult → Step → Trajectory`。
4. 环境：local BM25 Search/Visit + aligned synthetic fixture。
5. 可靠性：预算、termination、结构化 failure taxonomy、deterministic injection。
6. 证据：artifact pipeline 可运行，但当前是 Oracle fixture validation。
7. 研究边界：RL、learned policy、live Web、multimodal 全部尚未验证。
8. 下一步：先提交 clean M0 checkpoint，再建立真实 policy/baseline 和固定评测集。

## 简历 claim 审计清单

- [ ] 每个“已实现”能回到当前源码或测试。
- [ ] 每个数字能回到具体 artifact，并说明 policy、dataset 和 denominator。
- [ ] 明确区分 committed baseline、dirty worktree 和 planned design。
- [ ] 不把 Oracle fixture 结果写成模型或 RL 指标。
- [ ] 不把 helper、schema 或 interface 写成完整训练算法。
- [ ] 不把 synthetic local environment 写成 live Web deployment。
- [ ] 不虚构 GPU、模型、训练时长、成本、吞吐或提升百分比。
