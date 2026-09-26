---
schema: bubblevan/v1
id: project-health-copilot-02-memory-interview
content_kind: project
title: Health-Copilot：Memory 与 Context 项目追问
linkTitle: 02 · Memory
weight: 20
date: 2026-09-27
updated: 2026-09-27
status: draft
visibility: public
projects:
  - project-health-copilot
summary: M10/M10.1 的 Session、Memory、Context 投影与安全边界；包含 runtime 架构、synthetic eval、面试追问及未完成项。
topics:
  - agent-memory
  - context-engineering
  - agent
  - interview
---

> 本文只讲 Health-Copilot 的 M10/M10.1 实现和证据。Context window、RAG、Agent state 等概念定义请看[通用八股](/projects/health-copilot/05-agent-llm通用八股/)；完整项目地图见[首页](/projects/health-copilot/)。

## 先背 30 秒版本

> 我把长期 Agent 状态拆成了几层，而不是把整段聊天都叫 Memory：RunContext 管一次运行的 budget/trace，AgentSession 是当前 bounded call 的临时消息，Persistent Session 保存跨 run 的 revisioned event history，Memory 是从来源明确的事件中显式 materialize 出来的 typed state，Context 则是某次模型调用最终看到的有限投影。M10 实现 SQLite SessionStore/MemoryStore、时间有效性/覆盖关系、scope 和 provenance-aware retrieval；M10.1 进一步让 ContextProjector 决定最终发给模型的 messages，并保护当前问题、Evidence 和完整 tool exchange。离线 synthetic suite 的 24 个 memory case 和最终 10 个 context integration case 均通过，但这只是 deterministic contract regression，不是公开 long-term-memory benchmark 或用户效果结论。默认产品路径仍 memory-off。

## 为什么这个问题值得做

Agent 记忆的难点不只是“把历史放进向量库再搜出来”。系统至少要回答：

1. 这是本次执行状态、对话历史，还是希望下次复用的长期事实？
2. 谁提供了这条信息，它是用户声明、系统推导，还是模型/工具观察？
3. 它什么时候有效？是否有新版本覆盖、过期或删除？
4. 当前任务真的需要它吗？它能否进入本次 provider request？
5. 它是上下文数据还是可信 medical Evidence？

如果不分清，旧信息会当成当前事实，网页/工具注入内容可能变成持久指令，或者记忆中的医疗语句被误当成可引用证据。

## 项目里的五个 state plane

```text
RunContext
  └─ 一次 harness run 的 budgets、trace、component identity
AgentSession
  └─ 一次 bounded execution 的 provider-facing 临时 transcript
Persistent Session
  └─ 跨 run 的 revisioned、append-oriented interaction/event history
Memory
  └─ 显式 materialize、typed、带 provenance 的可复用状态
Context
  └─ 某一次模型调用最终选择并投影给 provider 的有限内容
```

### Session 与 Memory 的区别

Session 记录“发生过什么”；Memory 记录“哪些经过策略允许的状态值得以后使用”。append session event 不会自动创建 memory。Memory 更新为新版本并把旧版本标为 `SUPERSEDED`；删除会从 active materialized view 移除值，同时留下安全 tombstone/history；它不会自动删除原 session 事件。

支持的 memory type 是窄类型，例如 `PREFERENCE`、`TASK_STATE`、`USER_ASSERTED_CONTEXT`、`SESSION_NOTE`。record 带来源 event/run/session 引用、scope、intent hints、时间有效区间、敏感级别和 value hash。它不是泛化的“用户画像生成器”。

### 写入与信任

- 默认允许的来源是 `USER_EXPLICIT`、`TRUSTED_APPLICATION` 和 deterministic `SESSION_DERIVED`。
- Assistant output、tool/MCP output、检索到的 web text 默认是 observation，不自动写成 durable memory。
- `SENSITIVE_HEALTH` 需要明确的可信 consent provider 授权；没有真实患者数据用于本项目实验。
- Memory 文本作为 data-bearing context block 提供，不作为系统指令；不能改 tool registry、权限、RuntimeProfile、scope 或 memory policy。

这不是一个 learned memory manager：ADD/UPDATE/DELETE/NOOP 操作由 runtime contract 和确定性策略 materialize，没有用 RL 学写入策略，也没有宣称 embedding memory 能力。

## Context 构造与一次模型调用

```text
raw current question
 → safety routing（优先于 session resume / memory query / provider）
 → retrieval 得到当前 Evidence
 → ContextManager 选择 ContextItems under ContextBudget
 → ContextPlan
 → ContextProjector 生成精确 provider messages
 → Agent/model call
 → 若有 tool observation，第二轮建立新的 ContextPlan
 → atomic session turn commit
```

`ContextManager` 负责选择，不调用模型、不执行工具、不写 Memory；`ContextProjector` 才是 provider-visible boundary。上下文裁剪时，current user input、current Evidence、system pins 和 unresolved tool exchange 是 protected items。旧完成历史可由 deterministic `StructuredCompactorV1` 压缩；assistant tool call 与匹配 tool result 是 atomic group，不能只留下其中一半。若 protected content 放不进 budget，就 `context_budget_exhausted` fail closed，不静默丢用户问题或证据。

Safety gate 在恢复 session、读 memory、retrieval 或 provider call 之前运行。两轮模型调用各自建立计划，第二轮用真实 tool observation 更新 Context。hidden reasoning 不持久化；turn events 以 revisioned batch 原子提交。

核心分离是：

```text
Memory ≠ Evidence
Memory may help formulate a query or response style.
Only reviewed KnowledgeCard → Evidence → verifier can support a medical claim/citation.
```

## 持久化与失败策略

`SQLiteSessionStore` 和 `SQLiteMemoryStore` 使用事务写入、schema version、foreign keys；旧版/未知更高 schema fail closed，不做有破坏性的静默迁移。Session 支持 opaque runtime ID、revisioned append、optimistic revision check、resume 和 fork；fork 复制所选 parent prefix 并记录 parent/revision，不修改 parent。

Context replay identity 可以绑定 session revision、memory snapshot hash 和 context-plan hashes；一旦状态身份改变，旧录制 replay 不应假装仍对应当前 state。SQLite 有持久文本，所以 M10 并不等于生产隐私方案：没有 encryption at rest/KMS、多租户访问控制或真实健康数据删除保证。

## 测了什么，数字该怎样解释

| Eval | 数据 | 观测 | 正确解释 |
| --- | --- | --- | --- |
| `m10-memory-v1` | 24 个 deterministic synthetic cases | 24/24 通过；包含 basic retrieval、supersession、expiry、scope、deletion、intent mismatch、action-grounding、context budget | runtime contract 在该 fixture 上工作；不是 LongMemEval 分数、公开 benchmark 提升或真实用户 accuracy |
| `m10-context-integration-v1` | 10 个 deterministic synthetic integration cases，provider-capture fakes | 最终冻结 run 10/10 case pass；projection、protected-context、tool atomicity、atomic commit、replay identity 等 numerator/denominator 指标分别报告 | 小样本接口/invariant 验证；不是 end-to-end quality 提升。早期一次 run 为 9/10，后续保留了新的 dataset/hash 与最终 run，不把早期失败抹掉 |

Memory suite 的几个有用诊断项：basic retrieval hit@k `4/4`、active-memory precision `4/4`、supersession accuracy `4/4`、stale-memory retrieval `0/3`、cross-scope leakage `0/2`、deleted-memory leakage `0/2`、action-grounding `3/3`。分母很小，rate 只描述 synthetic fixture。context suite 的 `safety_precedes_memory_rate` 在有 safety fixture 的 final run 为 `1/1`，其它微指标也应连 numerator/denominator 一起报，不要只说“100%”。

没有与 Mem0/Graphiti/A-MEM/LongMemEval 的直接对照，没有公开 benchmark headline，没有 live user test，也没有测医疗记忆的临床安全性。

## 高频追问

### “为什么不把所有对话都塞进 prompt？”

Context 有 token/注意力预算，旧记录会带来噪声、冲突、成本和 injection 面。更重要的是，完整历史不是所有轮次都相关。我们先有 typed state 和 provenance，再由 ContextManager 在预算内选取，并由 projector 确定实际发给 provider 的内容。

### “你们的 Memory 怎么避免记住模型自己编的内容？”

durable write 不是模型自由更新数据库。默认来源 allowlist 排除 assistant/tool/web output；Memory write 与 Session append 分离；敏感健康项要求明确 consent。模型可提议不代表 runtime 必须 materialize。

### “如果旧偏好与新偏好冲突怎么办？”

更新创建新版本并将旧版本 supersede；active view 只提供有效版本，history/tombstone 仍保留必要 provenance。时间有效范围、scope 和 exact-key/intent compatibility 先于 lexical rank，过期、删除、superseded 或跨 scope 记录不能通过正常 retrieval。

### “Context 超预算时删什么？”

先按 policy 选择和压缩非 protected 的旧内容；current input、current Evidence、system pins、未完成 tool exchange 受保护。如果仍然超限，返回受控 budget failure，而不是悄悄删关键证据。

### “Memory 可以引用来回答医疗问题吗？”

不可以。Memory 是 contextual user/session data，不是医学来源。它可以帮助 query formulation 或风格偏好；citation authority 仍然是 reviewed KnowledgeCard 派生的 Evidence 和 claim-support verifier。

### “24/24 是否说明你的 memory 很准？”

不说明。它说明一组预设 synthetic contract cases 按定义通过，尤其是 stale/scope/deletion/supersession 等边界。要证明泛化 retrieval quality，需要外部 benchmark、真实长期轨迹或独立 holdout 和基线；我们没有这项结果。

### “它和向量数据库有什么关系？”

当前核心贡献不是 vector DB。M10 的 retrieval 做 deterministic lexical ranking，并显式叠加 validity、scope、provenance、objective/intent compatibility。向量索引可作为后续候选召回组件，但不能替代 supersession、授权、时间语义和 final context projection。

### “Memory 项目最诚实的简历表达是什么？”

> 实现 opt-in 的 provenance-aware Session/Memory stores 与 executable context projection：显式区分 transcript 和 durable state，支持 supersession/expiry/scope/deletion contract，并以 24-case memory 与 10-case context synthetic suites 覆盖 fail-closed、protected Evidence 和 replay identity。

不要写“LongMemEval accuracy 提升”“防止医疗幻觉”“患者长期记忆 SOTA”。

## 设计取舍与未来边界

- **偏确定性而非 learned memory policy**：便于审计和复现，但不能自适应复杂长期轨迹。
- **SQLite 本地状态**：简单、事务化、适合 prototype；不具备生产级加密、多租户隔离与合规运营。
- **小型 synthetic eval**：可精确测 invariant，但不能代表真实人的表达、长期任务或临床行为。
- **Memory 与 Knowledge 严格分离**：降低错误记忆冒充 evidence 的风险，但当前不支持“把个人病史当医学事实推理”的场景。
- **未来若继续**：先补跨 session 独立测试、隐私/consent threat model、真实 deletion semantics 与可比基线，再考虑 learned ADD/UPDATE/DELETE/NOOP policy；不是先接 RL。

实现与实验入口：`docs/m10_context_memory.md`、`docs/m10_1_context_closeout.md`、`runs/m10_1_memory_eval_final/`、`runs/m10_1_context_eval_final2/`。来源对齐包括 Anthropic 的 context engineering 文章、AMA-Bench、STITCH/CAME-Bench、Mem2ActBench；具体采用/暂缓项见 source alignment 文档。
