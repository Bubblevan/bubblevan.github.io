---
schema: bubblevan/v1
id: blog-20260814-agent-context
content_kind: blog
title: Hi-Agent 上下文工程学习
date: 2026-08-14
updated: 2026-08-14
status: draft
visibility: public
summary: 在完成 Hi-Agent RAG 后，规划上下文工程的 TDD 学习路线：从领域模型、单元测试和长任务集成测试，到真实 LLM 评测与上下文专用 Bench。
topics: [Agent, Context Engineering, TDD, Evaluation, LLM]
projects: [hi-agent]
aliases: []
authors: [bubblevan]
---

> 本文目前是实施大纲。目标不是先写一个更大的 ContextBuilder，而是用 Test-Driven Development 逐步构建一个可观察、可评估、可恢复的 Context Compiler。

## 1. 这一篇要解决什么问题

RAG 已经解决了“从外部知识库找哪些证据”，但 Agent 在长任务中还要面对另一类问题：

```text
系统指令、任务目标、对话历史、Memory、RAG 证据、工具结果和任务笔记
如何在有限 token 预算内共同进入下一次 LLM 调用？
```

因此本文的主线不是“把更多信息塞进上下文”，而是：

```text
候选信息
  → 选择
  → 分配预算
  → 压缩或清理
  → 编译为合法消息
  → 观察 Agent 是否还能完成任务
```

## 2. 现状与目标

### 2.1 Hi-Agent 已经有什么

当前仓库已经具备以下基础：

```text
retrieval/models.py                 # Document、Chunk、RetrievalResult
retrieval/context_builder.py        # RAG 专用上下文组装
retrieval/pipeline.py               # 检索、上下文、生成和引用校验
memory/                             # Memory 分层、存储与隔离
tests/unit/                         # RAG、Memory、租户隔离测试
tests/integration/test_rag_live.py  # 真实 RAG 服务测试
```

当前 `ContextBuilder` 仍然主要负责“检索结果 → 有编号证据块”，而 `core/agent_base.py` 的历史管理仍偏向按消息数量截断。这正好构成上下文工程的起点：保留 RAG 上下文兼容性，再逐步加入多来源选择、token 预算和生命周期管理。

### 2.2 最终目标

最终希望 Hi-Agent 拥有一个最小但完整的上下文管理链路：

```text
ContextSource
  → ContextItem
  → ContextCompiler
  → CompiledContext
  → Agent Runtime
  → Trace / Evaluator
```

它应当能够：

- 在 hard token limit 内生成合法消息序列；
- 永不丢弃系统约束和当前任务目标；
- 对 Conversation、Memory、RAG、Tool Result 和 Notes 统一建模；
- 清理可以重新获取的工具输出；
- 在长任务中执行 checkpoint 和 compaction；
- 在 compaction 后恢复任务状态；
- 用真实 LLM 验证上下文策略是否确实改善任务完成，而不是只验证字符串拼接成功。

## 3. 现有基线与测试入口

### 子任务 1：冻结现有基线与测试入口

先不改架构，冻结现有单元测试、Memory eval 和真实 RAG eval，避免后续改动后失去可比较的参照。当前基线如下：

| 层次 | 当前结果 | 应该怎样解释 |
| --- | --- | --- |
| 单元测试 | `137 passed, 1 skipped` | 当前代码契约的回归基线；`skipped` 的原因需要一并记录 |
| Memory eval | 71 个查询，其中 48 个正例、23 个拒答例 | 同时覆盖召回和拒答，不只是命中率 |
| Memory：无阈值 → `0.35` 阈值 | Recall@5：`0.9375 → 0.8542`；abstention recall：`0 → 0.3043` | 阈值减少了不应回答的查询，但牺牲了一部分正例召回，这是一个明确的 precision/recall trade-off |
| Memory 其他指标 | 两组均计算 Recall、MRR、nDCG、abstention、leakage 和延迟 | 当前文章先不补没有保存的具体数值，后续应把完整 report 固化为 artifact |
| 真实 RAG eval | 2 个问题；回答成功率 `2/2`；期望术语检索覆盖 `2/2`；回答覆盖 `2/2`；引用有效率 `2/2` | 证明 PDF + 博客两条链路能跑通，暂时不能证明 RAG 策略稳定 |
| 真实服务成本 | 未记录 | 明确标记为未记录，不虚构金额 |
| 平均输入 token | 未记录 | 需要在下一轮真实评测中记录，而不是回填估算值 |
```

这里的 `2/2` 应该准确地称为“端到端契约通过”，而不是泛化意义上的“回答质量 100%”。当前测试主要检查期望术语是否被检索和回答覆盖、引用编号是否合法；它还没有覆盖答案完整性、事实一致性、问题难度分层和多次运行稳定性。

因此，第一阶段的基线不需要抛弃，而是增加三个字段：

```text
eval_version
model / embedding_model
git_commit
```

同时保存每个 case 的原始回答、召回 Chunk、citation、输入/输出 token、延迟、错误信息和配置。只有总分没有 per-case artifact，后面无法解释一次回归究竟是检索错了、上下文丢了，还是模型回答错了。

### 3.1 Hello-Agents PDF 能不能扩成评测集

当前 RAG fixture 中的 Hello-Agents PDF 是一篇 5 页论文，抽取正文约 2.8 万字符，包含摘要、问题背景、YOLOv8-BFDS 的三个改进模块、实验指标定义、模型对比表、可视化比较、消融实验和结论。它不是只有一个事实，因此足够支撑一组小型、人工核验的 RAG 题目。

适合从 PDF 生成约 8～10 个正向问题，覆盖不同答案位置和问题类型：

```text
摘要：YOLOv8-BFDS 集成了哪三个关键优化？
机制：DCNv2 解决什么问题，和固定感受野有什么区别？
机制：E-SEModule 如何结合 channel attention 与 spatial attention？
机制：Concat_BiFPN 相比传统 FPN 增加了哪些能力？
架构：YOLOv8 的 Backbone、Neck、Head 分别承担什么职责？
数据：JAMSTEC 数据集包含多少张图像和多少个目标类别？
表格：YOLOv8-BFDS 在 Precision、Recall、mAP50、mAP50-95 上的结果是什么？
对比：相比原始 YOLOv8，四项指标分别提升了多少？
消融：YOLOv8+BiFPN、YOLOv8+DSConv 和完整 BFDS 的 mAP50 如何比较？
指标：mAP50 与 mAP50-95 的 IoU 范围和含义有什么不同？
```

但不能把这些问题全部当作完全独立的统计样本：摘要、结论和表格重复描述了相同结果，若只做同义改写，样本数会虚高。更稳妥的做法是为每题标注：

```text
source_section
answer_type: fact / comparison / multi-hop / abstention
gold_evidence
expected_terms
difficulty
```

PDF 适合做第一批“可回答性 + 引用 + 表格/机制检索”的 mini-bench，不适合单独证明长上下文能力。论文只有一个主题、一个来源，不能替代跨文档、跨轮次和工具结果压缩测试。

### 3.2 真实 RAG eval 应该扩到多大

我建议把当前 2 个问题保留为每次提交都运行的 smoke eval，再增加一个 12～16 题的 RAG mini-bench：

```text
6～8 个 Hello-Agents PDF 正向问题
3～4 个 Bubblevan 博客正向问题
1 个跨段或跨文档问题
2～3 个明确不在资料中的拒答问题
```

这里的总数可以是 15～16 题，但拒答题不应被混入普通“回答成功率”。报告至少拆成：

```text
positive answer success
retrieval evidence recall
answer expected-term coverage
citation validity
abstention recall
false answer rate
```

如果预算有限，先做 12 题：6 个 PDF、3 个博客、1 个跨段问题、2 个拒答；如果要观察不同上下文策略的稳定性，再把正向题扩到 15～16 题，并对每题重复 3 次。这样比直接从一篇 5 页 PDF 生成几十道相似题更可靠。

### 3.3 上下文工程还需要另一套任务集

RAG mini-bench 不能直接评估 compaction。上下文工程至少要另建 6～10 个可控长任务样本，样本中显式提供：

```text
task goal
current state
completed work
key decisions
tool observations
stale noise
must-preserve facts
allowed-to-clear items
```

这些样本的 gold label 不是“某个 PDF 术语”，而是：

```text
哪些 ContextItem 必须保留
哪些内容可以清理
压缩后哪些事实必须存在
Agent 下一步应该采取什么动作
```

因此推荐三层评测规模：

```text
Smoke：2 个真实 RAG 问题，每次提交运行
RAG mini-bench：12～16 个问题，评估检索与回答回归
Context bench：6～10 个长任务，评估选择、压缩、恢复和任务成功
```

产出：`baseline.md`、每个 case 的 JSONL 结果、统一测试命令和失败分类。

### 子任务 2：定义 Context 领域模型

新增最小模型：

```python
ContextItem
ContextCandidate
ContextBudget
CompiledContext
ContextTrace
```

先写单元测试，再实现字段校验、稳定 ID、来源类型、优先级、是否必选和 token 数量。

重点测试：

```python
def test_context_item_has_stable_id()
def test_required_item_cannot_be_dropped()
def test_invalid_budget_is_rejected()
```

### 子任务 3：实现基于 token 的 Budget Manager

把“最大字符数”升级为可替换的 token counter，并明确：

```text
soft_limit
hard_limit
output_reserve
source_budget
```

重点测试预算不变量：

```python
def test_compiled_context_never_exceeds_hard_limit()
def test_output_reserve_is_preserved()
def test_required_items_are_selected_even_when_budget_is_tight()
```

### 子任务 4：把现有模块适配为 Context Sources

为现有 RAG 和 Memory 增加适配器，而不是让 Compiler 直接依赖 Qdrant、SQLite 或具体 Memory Manager：

```text
ConversationSource
TaskStateSource
RetrievalContextSource
MemoryContextSource
ToolResultSource
NoteSource
```

重点测试来源边界、租户隔离、来源 metadata 和 RAG citation 是否保留。

### 子任务 5：实现确定性的 Select / Structure / Validate

第一版选择算法不追求复杂模型，先实现可解释、可复现的策略：

```text
必选项优先
任务状态优先
来源可靠性
相关性与新近性
重复惩罚
可重新获取内容降权
```

重点测试：

```python
def test_selection_is_deterministic()
def test_duplicate_facts_are_deduplicated()
def test_low_priority_tool_output_is_dropped_first()
def test_compiled_messages_are_valid()
```

### 子任务 6：实现 Tool Result Clearing 与 JIT Workspace

为工具结果增加 artifact 引用和可重新获取标记：

```text
原始输出过大
  → 提取 error/head/tail
  → 保存 artifact_ref
  → 上下文只保留摘要和引用
```

这一阶段不开放任意 Shell，而是沿用现有工具边界，测试路径限制、输出限制和恢复能力。

### 子任务 7：实现 Structured Checkpoint 与 Compaction

先实现确定性压缩，再接入可替换的真实 LLM compactor。压缩结果必须保留：

```text
Goal
Current State
Completed Work
Decisions and Rationale
Modified Files
Tool Outcomes
Open Problems
Constraints
Next Actions
Evidence References
```

重点测试：

```python
def test_compaction_preserves_task_goal()
def test_compaction_preserves_open_actions()
def test_compaction_preserves_evidence_references()
def test_compaction_is_idempotent()
def test_recovery_restores_checkpoint()
```

### 子任务 8：建立 Context Bench 数据集与 Evaluator

新增专门的 JSONL 数据集，每条样本描述上下文候选、必须保留项、允许清理项和压缩后必须存在的事实：

```json
{
  "case_id": "ctx-001",
  "task": "继续完成代码库迁移",
  "candidate_items": [],
  "must_include": ["goal", "decision"],
  "must_exclude": ["stale_tool_log"],
  "required_facts_after_compaction": ["双写迁移", "新 schema"]
}
```

Evaluator 第一版计算：

```text
Context Recall
Context Precision
Budget Violation Rate
Compression Fidelity
Redundancy Ratio
Recovery Success
```

### 子任务 9：加入真实 LLM Eval

真实 LLM Eval 不替代单元测试，而是回答单元测试无法回答的问题：

> 被选中的上下文真的能让模型更好地完成任务吗？

至少比较四个策略：

```text
最近消息截断
全量历史
Context Compiler
Context Compiler + Compaction + Checkpoint
```

真实评测任务先从 20～30 个可控样本开始，覆盖：

- 任务目标保持；
- 历史决策恢复；
- 工具错误恢复；
- RAG 证据与 Memory 去重；
- 长任务中避免重复工作；
- 压缩后继续执行下一步。

每个样本至少重复运行 3 次，记录：

```text
最终任务成功率
关键事实召回率
引用有效率
工具调用正确率
平均输入 token
压缩次数
恢复失败率
总成本与延迟
```

### 子任务 10：长任务集成、回归门禁与博客复盘

构造一个 30～50 轮的代码库维护任务：

```text
探索代码库
→ 读取文件
→ 运行测试
→ 遇到错误
→ 修改计划
→ 创建 checkpoint
→ 触发清理和 compaction
→ 恢复并继续
→ 验证最终状态
```

最后将单元测试、Property-Based Test、真实 LLM Eval 和长任务回归结果统一输出，形成后续 PR 的验收依据。

## 5. 测试分层设计

### 5.1 Unit Test：确定性、快速、无外部服务

覆盖：

```text
领域模型
token budget
选择与去重
消息结构
压缩契约
checkpoint 序列化
引用保留
租户隔离
```

### 5.2 Property-Based Test：验证不变量

使用 Hypothesis 生成随机 ContextItem，验证：

```text
永不超过 hard limit
选中 ID 不重复
必选项不丢失
输出消息始终合法
相同输入得到相同结果
压缩不会增加 token
```

### 5.3 Integration Test：验证组件协作

使用 fake LLM、fake tool 和临时存储，模拟完整长任务，但不产生真实 API 成本。

### 5.4 Real LLM Eval：验证行为效果

使用真实模型、固定 prompt、固定数据集和可复现配置。真实评测结果必须保存原始 trace、模型名、时间、输入 token、输出 token 和版本信息，不能只保存一个总分。

## 6. 真实 LLM Eval 的设计原则

### 6.1 不让 LLM 评审所有东西

能用程序判断的内容，优先使用程序判断：

```text
token budget        → 程序
引用编号是否合法     → 程序
文件是否被修改       → 程序
测试是否通过         → 程序
任务状态字段是否存在  → 程序
```

只有“答案是否满足语义要求”“压缩后是否仍足以继续任务”等内容，再交给 LLM Judge 或人工抽样。

### 6.2 Judge 必须结构化输出

Judge 不直接返回一句自然语言评价，而返回：

```json
{
  "task_success": true,
  "goal_preserved": true,
  "critical_facts_preserved": ["新 schema"],
  "unnecessary_context": ["旧日志"],
  "reason": "..."
}
```

随后由程序校验 JSON schema，并记录 judge disagreement。

### 6.3 评测 baseline 必须存在

没有 baseline，就无法证明 Context Engineering 有效。至少保留：

```text
Last-N baseline
Full-history baseline
Deterministic Compiler baseline
LLM Compaction baseline
```

## 7. 评估指标大纲

```text
Context Recall
  必须保留的信息中有多少进入上下文

Context Precision
  进入上下文的信息中有多少真正有用

Compression Fidelity
  压缩后关键事实的保留比例

Budget Violation Rate
  超过 hard limit 的比例，目标为 0

Redundancy Ratio
  重复 token 占总 token 的比例

Recovery Success
  checkpoint / compaction 后能否恢复正确状态

Task Success
  Agent 是否真正完成任务

Cost and Latency
  输入 token、压缩调用次数、总成本和延迟
```

## 8. 研究进展如何进入实现

### 8.1 立即吸收

- Compaction、tool-result clearing 和持久化 memory 的组合；
- ACON 对 observation 与 history 的统一压缩视角；
- MemoryOS 的短期、中期、长期分层思想。

### 8.2 后续专题

- Context Folding：完成的子任务折叠为结果；
- Tree of Agents：通过上下文隔离处理长输入；
- ACE：把任务经验演化成可检索的 playbook；
- CompactionRL：将上下文管理纳入 Agent 训练。

第一阶段不直接实现 RL 或专用压缩模型。先把 Context Compiler、Trace、Bench 和真实评测做稳定，再讨论模型训练。

## 9. 计划中的目录变化

```text
context/
├── models.py
├── budget.py
├── compiler.py
├── trace.py
├── lifecycle.py
├── sources/
├── selection/
└── compression/

tests/unit/context/
tests/integration/test_long_horizon_context.py
tests/eval/test_context_bench.py
tests/fixtures/context_cases.jsonl
evals/context/
```

现有 `retrieval/context_builder.py` 暂时保留为 RAG 专用兼容层，避免把检索证据格式和 Agent 全局上下文生命周期耦合在一起。

## 10. 第一阶段完成定义

当下面条件同时满足时，第一阶段才算完成：

```text
所有单元测试通过
Property-Based Test 验证核心不变量
Context Bench 能独立运行
真实 LLM Eval 至少完成一个 baseline 对比
长任务 compaction 后可以恢复
完整 trace 可以解释“为什么选中或丢弃一项信息”
真实服务测试和本地测试分离
结果包含 token、成本、成功率和失败样本
```

本文后续将按上述 10 个子任务逐个实施，每个子任务都遵循：

```text
先写失败测试
→ 实现最小代码
→ 运行本地测试
→ 运行必要的真实 LLM Eval
→ 记录结果
→ 再进入下一个子任务
```
