---
schema: bubblevan/v1
id: blog-20260722-agent-memory
content_kind: blog
title: Memory
date: 2026-07-22
updated: 2026-07-22
status: draft
visibility: public
summary: memory eval 跑出来 abstention_recall = 0.0，意味着所有不该回答的查询都返回了结果。在 MemoryManager.retrieve_memories() 里加了 min_relevance_score 参数，把 RRF 融合分数写回 metadata，让检索层支持拒答。eval harness 增加 --min-relevance-score 和 --debug 参数。16 维 FakeEmbedder 下 abstention_recall 从 0 升到 0.30
topics: [hi-agent, memory, retrieval, eval, abstention, python]
projects: [hi-agent]
aliases: []
authors: [bubblevan]
---

## 0. 隔了一两个月后，我已经忘了 Memory 写到哪了

这次重新打开 Hi-Agent，是从一条 push 记录开始的：

```text
To github.com:Bubblevan/hi-agent.git
   198a8fd..22cbd5a  main -> main
```

我上一次认真看这个项目已经是一两个月前。当时跟着 Hello-Agents 学到第八章《记忆与检索》，印象里 Memory 还没有完全收尾，RAG 还没进入。重新接手时，我已经忘了 `importance`、`forget`、`consolidate` 这些字段和动作分别做什么。

我这次先不写 RAG。目标是重新理解 Memory 的结构，确认 Hi-Agent 现在每个文件承担什么职责，以及这些职责和 Hello-Agents 第八章的学习文档如何对应。

---

## 1. Hello-Agents 第八章到底在讲什么

Hello-Agents 第八章的主线是给前面章节的 Agent 框架补两个能力：Memory 和 RAG。文档里直接把问题分成两类：
- LLM 本身是无状态的，所以会忘记长期对话；
- LLM 的训练知识有截止时间，所以需要外部知识检索。

这一章里，Memory 和 RAG 被设计成两个工具。`memory_tool` 负责存储和维护交互过程中的信息，`rag_tool` 负责从用户提供的知识库检索相关内容，再把检索结果作为上下文交给模型。这个设计对 Hi-Agent 很重要，因为它说明 Memory 和 RAG 不应该混成一个模块。

我现在对这两个词的理解是：

| 类型 | 说明 |
|------|------|
| Memory | 保存 Agent 和用户之间已经发生过的事情。例如用户偏好、当前任务状态、历史调试经历、某次提交的结论。 |
| RAG | 检索外部文档里的知识。例如博客、论文、README、PDF、API 文档。 |

Hello-Agents 第八章里把 Memory 拆成四层：基础设施层、记忆类型层、存储后端层、嵌入服务层。
基础设施层包括 `MemoryManager`、`MemoryItem`、`MemoryConfig`、`BaseMemory`；
记忆类型层包括 Working、Episodic、Semantic、Perceptual；
存储层包括 Qdrant、Neo4j、SQLite；
嵌入层包括 DashScope、本地 Transformer 和 TF-IDF。

Hi-Agent 当前实现和教程不是完全一致。教程里有 Neo4j 图数据库，但 Hi-Agent 现在主要是内存、SQLite、Qdrant 和 fake embedder。这个差异暂时可以接受，因为我现在要学的是 Memory 的工程边界，不是一次性复现完整教程。

## 2. MemoryItem 是所有记忆的统一格式

重新看代码后，我先把 `MemoryItem` 理解成记忆系统的最小单位。无论是工作记忆、情景记忆还是语义记忆，最后都要被包装成一个标准对象。

我现在关心这些字段：

```text
id：
这条记忆的唯一标识。

user_id：
这条记忆属于哪个用户。多用户隔离必须依赖它。

content：
记忆正文。

memory_type：
记忆类型，通常是 working、episodic、semantic、perceptual。

importance：
重要性，0.0 到 1.0。用于检索过滤、遗忘和巩固判断。

metadata：
扩展信息，例如 session_id、timestamp、来源、relevance_score、provenance。

timestamp：
这条记忆创建或记录的时间。
```

我原先把 `importance` 和“相关性”混在一起了。重新看后发现它们不是一回事。`importance` 表示这条记忆值不值得保留；相关性表示这条记忆和当前查询是否匹配。

例子：

```text
content = "用户偏好博客保留真实命令、错误信息和未确认信息"
importance = 0.9
```

这条记忆很重要。但如果用户现在问“北京旅行酒店”，它仍然不相关。检索层不能只因为它重要就返回它。

这个区别后来影响了 `retrieve_memories()` 的设计。Hi-Agent 已经在 `MemoryManager` 里增加了 `MemorySearchResult` 和 RRF 融合，把检索分数写回 `metadata["relevance_score"]`，再用 `min_relevance_score` 做低相关过滤。当前代码里 `retrieve_memories()` 的参数已经包含 `min_relevance_score`，并在返回前过滤低分结果。

---

## 3. MemoryManager 为什么是中枢

Hi-Agent 的 `memory/manager.py` 文件注释里把 `MemoryManager` 定位成统一门面和中枢调度器。它负责初始化不同记忆类型，把 add、retrieve、forget、consolidate 这些操作分发到对应模块，再把结果统一返回。

我现在可以把它看成下面这条链路：

```text
MemoryTool.execute(...)
  ↓
MemoryManager.add_memory / retrieve_memories / forget_memories / consolidate_memories
  ↓
WorkingMemory / EpisodicMemory / SemanticMemory / PerceptualMemory
  ↓
内存、SQLite、Qdrant 等存储实现
```

它的意义不是“多写一层类”，而是让 Agent 不需要知道底层用了哪种记忆。Agent 只要调用 memory 工具，Manager 决定应该写入哪种 memory，或者从哪些 memory 里检索。

当前 `MemoryManager.__init__()` 默认只启用 `working`，其他类型按参数打开。这一点对调试很有用，因为 WorkingMemory 可以先不依赖数据库和向量服务。等基本行为跑通后，再打开 episodic、semantic、perceptual。

我这次重新看时，最需要关注的不是所有记忆类型的内部算法，而是 Manager 是否把这些公共约束统一住：

```text
user_id 是否始终传下去；
检索分数是否被保留；
低相关结果是否能被过滤；
forget 是否返回结构化报告；
consolidate 是否能避免重复写入。
```

当前结果：Manager 已经承担了核心调度责任。仍需要用测试确认各子模块是否都遵守同样的用户隔离和检索分数约定。

## 4. Working Memory 保存当前上下文

Working Memory 是短期记忆。它保存当前会话中临时但有用的信息，例如“这轮正在调试 MemoryTool search 行为”。

它适合这种内容：

```text
当前任务是把 memory demo 迁移成 pytest。
用户刚刚问了 min_relevance_score 的作用。
这轮讨论先不进入 RAG。
```

Working Memory 的特点是快、短、容量有限。它通常放在内存里，不保证程序重启后还存在。Hello-Agents 文档里也把它描述成当前对话上下文的短期保存区域，类似人类工作记忆。

`importance` 在 Working Memory 里会影响容量淘汰。容量满了以后，低重要性的记忆先被删。TTL 则负责时间过期。这样做的原因不是追求复杂，而是避免当前上下文无限增长。

举例：

```python
memory_tool.execute(
    "add",
    content="当前任务是调试 MemoryTool search 的相关性排序",
    memory_type="working",
    importance=0.6,
)
```

这条记忆可以帮助同一轮对话里的后续回答。如果一个月后我重新接手项目，它通常不应该还占用长期记忆。

当前结果：Working Memory 是我理解 Memory 系统最好的入口。它不依赖复杂存储，适合先写单元测试。

## 5. Episodic Memory 记录发生过的事件

Episodic Memory 是情景记忆。它关注“什么时候发生了什么”。

它适合记录：

```text
2026-07-21，Hi-Agent 新增了 4 memory modules。
2026-07-21，提交 097511d 把 memory demo 迁移成 pytest。
2026-07-21，提交 22cbd5a 增加了 memory eval harness。
```

这类记忆和时间、session、事件来源有关。以后如果我要问“这个项目上次做到哪一步”，情景记忆应该能还原项目进展。

Hi-Agent 的 `MemoryManager` 里已经有 `get_session_history()` 和 `get_timeline()` 这类方法，用来从情景记忆中按会话或时间线取回历史。

我之前对 Episodic Memory 的理解不清晰，容易把它和 Semantic Memory 混在一起。现在我会用这个判断区分：

```text
如果内容是一次具体发生过的事件，放 episodic。
如果内容是从多次事件中总结出来的事实或偏好，放 semantic。
```

例如：

```text
episodic：
2026-07-22，我发现 abstention_recall = 0.0。

semantic：
当前 Memory 检索层需要支持低相关拒答。
```

当前结果：Episodic Memory 已经有初步入口，但我还没有确认它的时间范围查询和 session 顺序还原是否足够稳定。

## 6. Semantic Memory 保存长期事实和偏好

Semantic Memory 保存更稳定的事实、偏好、规则和知识。它不一定关心某件事发生在哪一天，而是关心这个事实后续是否还应该被使用。

适合保存：

```text
用户偏好技术博客从真实命令、日志或错误开始。
Hi-Agent 当前学习路线是先完成 Memory，再进入 RAG。
Memory 和 RAG 应该分成两个工具。
```

这类内容如果保存正确，会让 Agent 后续回答更贴合我自己的项目状态。但它也有风险：旧事实可能被新事实覆盖，错误总结可能长期污染后续回答。

近两年 Agent Memory 论文也在强调这个问题。LongMemEval 把长期记忆能力拆成信息抽取、多 session 推理、时间推理、知识更新和拒答五类，这说明“记住事实”只是基础能力，后续还要处理事实更新和不知道的问题。

Hi-Agent 当前 Semantic Memory 还没有完整知识图谱。Hello-Agents 教程里提到了 Qdrant 和 Neo4j，但 Hi-Agent 现在不应该为了对齐教程而马上加 Neo4j。更稳的方式是先把长期事实的写入、检索、更新、冲突和删除跑通。

当前结果：Semantic Memory 是后续最容易产生价值的一类记忆，但也是最需要测试的一类。它不能只做向量相似度检索，还要处理旧事实、新事实和隐私删除。

## 7. Perceptual Memory 暂时不作为主线

Perceptual Memory 是感知记忆，用来处理图片、音频、截图、文件等多模态输入。Hello-Agents 第八章把它列入四类记忆之一。

我现在暂时不把它作为主线。原因是感知记忆会引入很多额外问题：

```text
图片要不要 OCR；
OCR 结果和原图如何关联；
音频转写失败怎么处理；
原始文件删除后 memory 是否还有效；
图像向量和文本向量是否处在同一个语义空间。
```

这些问题和我当前要补的 Memory 基础能力不是同一层。现在更重要的是让文本记忆的 add、search、forget、consolidate 和 eval 先稳定下来。

当前结果：Perceptual Memory 可以保留为实验模块。进入 RAG 之前，我不准备继续扩展它。

## 8. MemoryTool 是 Agent 看到的入口

`tools/builtin/memory_tool.py` 是 Agent 工具层。文件注释里写得很清楚：它位于 Agent 工具系统和记忆子系统之间，把底层记忆能力包装成标准工具接口，并自动注入会话 ID、用户 ID 等元数据。

这层的意义是让 Agent 不需要直接调用 `MemoryManager`。Agent 面对的是统一的工具动作：

```text
add
search
summary
stats
update
remove
forget
consolidate
clear_all
```

我重新理解后，觉得 MemoryTool 更像“遥控器”，MemoryManager 才是“中枢”。工具层负责参数检查、动作分发和输出格式；Manager 负责真正的记忆生命周期。

举例：

```python
memory_tool.execute(
    "add",
    content="用户正在从头学习 Hi-Agent Memory",
    memory_type="episodic",
    importance=0.8,
)
```

这个调用不会让 Agent 关心底层数据最后存在内存、SQLite 还是 Qdrant。这个边界对后续 RAGTool 也有参考价值。

当前结果：MemoryTool 的动作集合已经比较完整。后面需要继续确认每个 action 的返回格式是否适合 eval harness 和真实 Agent trace。

## 9. forget 是主动清理，不是异常

我之前忘了 `forget` 的作用，重新看后发现它不应该被理解成“删除功能”。它是 Memory 系统的维护动作。

如果 Agent 保存所有对话，后面检索会越来越脏。低价值记忆、过期记忆、已被新事实替代的记忆，都应该被清理或归档。

现在我把遗忘分成三类：

```text
importance_based：
根据重要性删除。例如 importance < 0.2 的内容被清掉。

time_based：
根据时间删除。例如超过 30 天的短期事件被清掉。

hybrid：
同时考虑重要性和时间。
```

Hello-Agents 文档把记忆过程概括为编码、存储、检索、整合、遗忘。遗忘在这里不是附属功能，而是完整记忆生命周期的一部分。

Hi-Agent 现在已经有 `ForgetReport`，这比只返回删除数量更适合测试。一个结构化报告可以记录删除了多少、跳过了多少、哪些模块出错。

当前结果：forget 的接口方向是对的。后面要确认所有记忆类型都实现同样的 forget 契约，而不是靠 `hasattr()` 临时判断。

## 10. consolidate 是把短期记忆提升为长期记忆

`consolidate` 对应记忆巩固。它的任务是把重要的短期记忆提升到长期记忆里。

典型例子：

```text
working：
这轮对话里用户说，下一步不要进入 RAG。

consolidate 后的 episodic：
2026-07-22，用户决定先完成 Memory 测试，再进入 RAG。

consolidate 后的 semantic：
当前 Hi-Agent 学习路线是先 Memory 后 RAG。
```

这一步不能只是复制。复制会带来重复写入、来源丢失和冲突问题。Hi-Agent 当前的 `consolidate_memories()` 已经比早期版本更完整：它会生成目标 `MemoryItem`，写入 `provenance`、`consolidation_key`，并标记源记忆已经巩固。

不过现在的 consolidate 仍然是初版。它还没有做 LLM 摘要，也没有把多个相似工作记忆合并成一条更抽象的语义记忆。这个阶段先不做复杂总结是合理的，因为幂等和来源记录比“智能总结”更基础。

## 11. 为什么先写 pytest，再写 eval harness

这次 Memory 项目里有两层测试。

第一层是 pytest。它测的是代码逻辑是否正确，例如：

```text
add 后能否 search；
同一个 user_id 能否读到自己的记忆；
不同 user_id 是否隔离；
forget 后是否删除；
consolidate 是否幂等；
TTL 和容量限制是否生效。
```

这些测试应该用 fake embedder 和临时存储。它们不应该真实调用 LLM、DashScope 或 Qdrant Cloud。原因是单元测试要稳定，不能让网络、API Key、模型波动影响结果。

第二层是 eval harness。它不只问“代码有没有报错”，还会计算检索质量。当前 `memory_eval.py` 会把 `memory_cases.jsonl` 里的用例写入 MemoryManager，再对 positive queries 和 negative queries 做检索，输出 recall@k、MRR、nDCG、cross-user leakage、abstention 和 latency。

这次本地跑出的 baseline 是：

```text
recall@5 = 0.9375
mrr = 0.775
cross_user_leakage_rate = 0.0
abstention_recall = 0.0
```

这个结果说明用户隔离已经有进展，但拒答能力没有做好。`abstention_recall = 0.0` 的含义是：所有本该返回空的 negative query，都返回了结果。

当前 eval 里，使用 `"北京旅行酒店"` 这种 negative query 去搜只包含代码调试内容的 memory，系统仍然会返回 top-k。这个问题的原因不是数据条数太少，而是检索层默认总是返回 top-k，没有“分数低于阈值就返回空”的机制。

后面我加了 `min_relevance_score`，并用阈值扫了一遍。日志里记录的结果是：

```text
不设阈值：
recall@5 = 0.9375
abstention_recall = 0.0000
mrr = 0.775

min_relevance_score = 0.35：
recall@5 = 0.8542
abstention_recall = 0.3043
mrr = 0.7368
cross_user_leakage_rate = 0.0
```

这个修改解决了“检索层完全不会拒答”的问题，但没有说明阈值已经合理。当前 fake embedder 是 16 维，负样本分数分布不一定能代表真实 embedding。真实 embedding 下是否能把 `abstention_recall` 提到 0.6 以上，目前还不能确认。

## 13. 现在的数据只有 29 条，还不够做 Memory v1

当前 `tests/fixtures/memory_cases.jsonl` 大约 29 条。这个规模适合 smoke eval，也能暴露用户隔离和拒答这种明显问题。但它不够证明 Memory 检索质量稳定。

我之前整理过一个更合理的 Memory v1 数据分布：

| 类型           | 数量 |
| ------------ | -: |
| 单条事实回忆       | 20 |
| 跨 session 多跳 | 15 |
| 时间顺序/日期推理    | 15 |
| 偏好更新和事实冲突    | 15 |
| 干扰项和无答案      | 10 |
| 删除与隐私        | 10 |
| 跨用户隔离        | 10 |
| 合计           | 95 |

这 95 条不是为了追求数量，而是为了覆盖不同失败方式。当前 29 条更多是在证明 harness 能跑起来。

我不准备马上接大型公开数据集。原因是现在 Memory schema、阈值机制和失败输出还在变。如果此时直接接 LoCoMo 或 LongMemEval，很容易把转换数据、真实检索、答案评估和工具行为混在一起。

当前结果：下一步先把 29 条扩到 60 条，再扩到 95 条。公开 benchmark 等 Memory eval runner 稳定后再接。

## 14. Agent 行为评估现在还没有真实调用 Agent

`agent_memory_eval.py` 这个名字容易让人误解。它目前测的不是 Agent 运行能力，而是 trace 里的工具调用是否符合预期。

当前 trace 数据大概是这种形态：

```json
{
  "case_id": "example",
  "turns": [
    {
      "expected_tools": ["memory.add"],
      "actual_tools": ["memory.add", "memory.search"],
      "used_stale_memory": false,
      "leaked_private_memory": false
    }
  ]
}
```

这个评估器会计算：

```text
memory_write_precision
memory_write_recall
memory_search_precision
memory_search_recall
unnecessary_memory_write_rate
unnecessary_memory_search_rate
tool_call_correctness
stale_memory_usage_rate
private_memory_leakage_rate
```

它的价值是先固定指标定义。它还没有实际构造 `SimpleAgent`，也没有调用 LLM，更没有捕获真实 tool call。

所以博客里不能写“Agent 已经会正确使用 memory”。更准确的说法是：

```text
当前已经有 Agent memory trace evaluator。
它可以评估记录好的 trace。
真实 Agent runner 尚未实现。
```

当前结果：trace evaluator 可以保留。真实 Agent 行为评估等 MemoryTool 和 RAGTool 都稳定后再做。

## 15. 近两年 Agent Memory 的几种方向

这部分不是当前实现内容，是我为后续学习整理的外部资料。它们帮助我判断 Hi-Agent 后面应该往哪里扩，而不是现在就复现。

### 15.1 长期对话记忆：LoCoMo 和 LongMemEval

LoCoMo 是 ACL 2024 的长期对话记忆 benchmark。论文介绍的数据包含多 session 长对话，每个对话平均约 300 turns、9K tokens，最多 35 个 session，并评估问答、事件摘要和多模态对话生成。

LongMemEval 是 ICLR 2025 的长期交互记忆 benchmark。它把聊天助手长期记忆能力拆成五类：信息抽取、多 session 推理、时间推理、知识更新和拒答。

这两类 benchmark 对 Hi-Agent 最直接的启发是：Memory eval 不应该只测“能不能搜到”。它还要测：

```text
新事实是否覆盖旧事实；
跨 session 是否能推理；
时间顺序是否正确；
无答案时是否拒答；
长期记忆是否泄露其他用户数据。
```

我当前 29 条 fixture 还没覆盖这些维度。后面扩到 95 条时，可以参考 LongMemEval 的分类。

### 15.2 图式长期记忆：HippoRAG

HippoRAG 是 NeurIPS 2024 的工作，思路是用 LLM、知识图谱和 Personalized PageRank 模拟人类长期记忆中的关联式检索。论文重点是跨文档、多跳知识整合。

这对 Hi-Agent 的意义是：Neo4j 或 GraphRAG 不应该因为教程里出现就立刻加入。只有当我有稳定失败样本，例如“向量检索能找到局部相关内容，但无法跨多个事件推理”，再考虑图结构。

当前判断：Hi-Agent 现在不做图记忆。先收集多跳失败样本。

### 15.3 链接式记忆：A-MEM

A-MEM 是 NeurIPS 2025 的 Agent Memory 工作，借鉴 Zettelkasten，把记忆动态组织成互相关联的知识网络。论文页面明确提到 dynamic indexing and linking。

这对 Semantic Memory 有启发。后面如果要处理事实更新和冲突，可以在 metadata 里加入：

```text
derived_from
supersedes
conflicts_with
version
links
tags
```

当前我只准备先做 `provenance` 和 `consolidation_key`。更复杂的链接网络暂时不实现。

### 15.4 反思式记忆管理：RMM

ACL 2025 的 Reflective Memory Management 研究长期个性化对话 Agent 的记忆管理。论文页面介绍了前瞻式反思和回看式反思：前者把不同粒度的交互总结进记忆库，后者根据回答引用的证据迭代优化检索。

这对应 Hi-Agent 当前两个薄弱点：

```text
写入前：什么内容值得保存？
检索后：拿到的记忆是否真的支持回答？
```

当前不做 RMM，但这个方向提醒我：Memory 不能只做 add 和 search，还需要管理写入质量和检索后校验。

### 15.5 程序性记忆：Agent Workflow Memory

ICML 2025 的 Agent Workflow Memory 关注从过去任务轨迹中归纳可复用 workflow，并在后续类似任务中提供给 Agent。

这和 coding agent 更接近。它保存的不是“用户喜欢什么”，而是“过去怎么完成某类任务”。

例如 Hi-Agent 以后可以保存：

```yaml
trigger: 修改 MemoryManager 检索逻辑
steps:
  - 先运行 pytest
  - 再运行 memory_eval
  - 检查 recall@5、abstention_recall、cross_user_leakage_rate
  - 更新博客记录
failure_lessons:
  - 不要只看 recall，negative query 也要看
```

这类记忆更像 Procedural Memory。Hello-Agents 第八章没有单独列这个类型，但对 Agent 工程很实用。

当前结果：程序性记忆是后续方向，不放进 Memory v0.1。

## 16. 当前文件应该怎么理解

这次重新接手后，我把 Hi-Agent Memory 相关文件按职责重新梳理了一遍。

### `memory/base.py`

这个文件应该放公共数据结构和抽象接口。

我现在关心：

```text
MemoryItem
MemoryConfig
MemorySearchResult
ForgetReport
BaseMemory
```

它的意义是统一各类记忆的输入输出。后面 Working、Episodic、Semantic、Perceptual 都不应该各自发明一套返回格式。

当前限制：需要确认 BaseMemory 是否已经强制定义 add、retrieve、update、delete、forget、clear、stats。若某些行为仍靠 `hasattr()` 判断，后面测试要补上。

### `memory/manager.py`

这个文件是 Memory 系统门面。它负责初始化子模块、注入 user_id、聚合检索结果、执行遗忘和巩固。

当前它已经包含：

```text
add_memory
retrieve_memories
forget_memories
consolidate_memories
get_session_history
get_timeline
clear_all
get_stats
```

我现在把它当作 Memory 的主入口。后续 RAG 不应该直接依赖这里的内部实现，但可以参考它的接口风格。

### `memory/types/working.py`

这个文件负责短期工作记忆。

它应该重点测试：

```text
容量限制；
TTL 过期；
低 importance 淘汰；
query 相关性；
user_id 过滤。
```

### `memory/types/episodic.py`

这个文件负责情景记忆。

它应该重点测试：

```text
session_id；
timestamp；
时间线查询；
会话历史；
事件顺序。
```

### `memory/types/semantic.py`

这个文件负责长期事实和知识。

它应该重点测试：

```text
同义查询；
旧事实和新事实；
冲突；
删除；
user_id 和 namespace 隔离。
```

当前不确认它是否完全实现了 Qdrant payload 的 user_id 强过滤。这个点需要靠测试确认，不能只看注释。

### `memory/types/perceptual.py`

这个文件负责感知记忆。

当前只作为实验模块保留。我不会在进入 RAG 前继续投入它。

### `memory/policies/`

这个目录适合放记忆生命周期策略。

我期望它以后包含：

```text
consolidation.py：
决定哪些短期记忆提升为长期记忆。

forgetting.py：
决定哪些记忆删除或归档。

conflict.py：
处理旧事实、新事实和相互矛盾的记忆。
```

当前如果里面已经有文件，也需要继续检查是否只是占位。策略层最好不要一开始写得很复杂，先让测试能覆盖。

### `tools/builtin/memory_tool.py`

这是 Agent 可调用的工具入口。

它应该负责：

```text
解析 action；
校验参数；
调用 MemoryManager；
把结果整理成工具返回值。
```

它不应该承担检索排序和存储细节。

### `evals/memory_eval.py`

这是检索质量评估。

它应该负责：

```text
读取 memory_cases.jsonl；
写入 MemoryManager；
执行 positive / negative query；
计算 recall@k、MRR、nDCG、abstention、leakage、latency；
输出失败样本。
```

它不应该把产品逻辑偷偷放在 eval 里。比如拒答过滤应该由 Manager 支持，eval 只透传参数。

### `evals/agent_memory_eval.py`

这是 trace 行为评估。

它现在不是真实 Agent runner。后面如果要真实评测 Agent，需要另写一层：

```text
输入任务
→ 调用 SimpleAgent
→ 捕获 tool_calls
→ 生成 trace
→ 交给 agent_memory_eval.py 打分
```

当前结果：文件边界比刚开始清楚了。下一步写 RAG 时，也应该先按这种方式分层，而不是把 loader、splitter、retriever 和 Tool 全塞进一个文件。


## 17. 下一步不急着写 RAG，先把 Memory 收稳

现在 Memory 的主线已经比一开始清楚：

```text
MemoryTool 是 Agent 入口。
MemoryManager 是调度层。
MemoryItem 是统一记忆单元。
Working 保存短期上下文。
Episodic 保存事件。
Semantic 保存长期事实。
Perceptual 暂时冻结。
pytest 测逻辑。
eval harness 测检索质量。
trace evaluator 测工具调用记录。
```

下一步我准备先做三件事：

```text
1. 扩展 memory_cases.jsonl，从 29 条扩到 60 条。
   重点补 hard negative、时间推理、偏好更新、删除与隐私。

2. 用真实 embedding 重新跑 threshold sweep。
   当前 16 维 FakeEmbedder 下 abstention_recall 只有 0.3043，不能说明真实模型效果。

3. 把 agent_memory_eval.py 的说明改准确。
   当前它是 trace evaluator，不是真实 Agent 行为评估。
```
