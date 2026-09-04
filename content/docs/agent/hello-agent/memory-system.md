---
schema: bubblevan/v1
id: blog-20260722-agent-memory
content_kind: blog
title: Hi-Agent Memory 实现复盘：从记忆生命周期到 Neo4j 图投影
date: 2026-07-22
updated: 2026-08-13
status: published
visibility: public
linkTitle: Memory System
weight: 7
summary: 这篇复盘从 MemoryItem 和 MemoryManager 出发，梳理 Hi-Agent 的记忆写入、检索、遗忘、巩固与删除生命周期，并记录 SQLite、Qdrant 和 Neo4j 的职责边界。Neo4j 作为可选图投影加入后，记忆可以建立 RELATED 关系并按用户隔离遍历；单元测试、真实 Neo4j 冒烟和当前证书边界也一并记录。
topics: [hi-agent, memory, lifecycle, qdrant, neo4j, eval, python]
projects: [hi-agent]
aliases:
  - /blog/2026/2026-07-22-agent-memory/
authors: [bubblevan]
---

## 0. 记忆系统

根据认知科学的研究，人类记忆的形成经历以下几个阶段：
1. **编码（Encoding）**：将感知到的信息转换为可存储的形式
2. **存储（Storage）**：将编码后的信息保存在记忆系统中
3. **检索（Retrieval）**：根据需要从记忆中提取相关信息
4. **整合（Consolidation）**：将短期记忆转化为长期记忆
5. **遗忘（Forgetting）**：删除不重要或过时的信息

由此构建的记忆系统由四种不同类型的记忆模块构成，每种模块都针对特定的应用场景和生命周期进行了优化：

首先是 **工作记忆 (Working Memory)**，它扮演着智能体“短期记忆”的角色，主要用于存储当前对话的上下文信息。为确保高速访问和响应，其容量被有意限制（例如，默认50条），并且生命周期与单个会话绑定，会话结束后便会自动清理。

其次是 **情景记忆 (Episodic Memory)**，它负责长期存储具体的交互事件和智能体的学习经历。与工作记忆不同，情景记忆包含了丰富的上下文信息，并支持按时间序列或主题进行回顾式检索，是智能体“复盘”和学习过往经验的基础。

与具体事件相对应的是 **语义记忆 (Semantic Memory)**，它存储的是更为抽象的知识、概念和规则。例如，通过对话了解到的用户偏好、需要长期遵守的指令或领域知识点，都适合存放在这里。这部分记忆具有高度的持久性和重要性，是智能体形成“知识体系”和进行关联推理的核心。

> 为了与日益丰富的多媒体交互，Hello Agent 引入了 **感知记忆 (Perceptual Memory)**。该模块专门处理图像、音频等多模态信息，并支持跨模态检索。其生命周期会根据信息的重要性和可用存储空间进行动态管理，但是这里我们不作为重点。

课程中，记忆系统采用了四层架构设计：
```
HelloAgents记忆系统
├── 基础设施层 (Infrastructure Layer)
│   ├── MemoryManager - 记忆管理器（统一调度和协调）
│   ├── MemoryItem - 记忆数据结构（标准化记忆项）
│   ├── MemoryConfig - 配置管理（系统参数设置）
│   └── BaseMemory - 记忆基类（通用接口定义）
├── 记忆类型层 (Memory Types Layer)
│   ├── WorkingMemory - 工作记忆（临时信息，TTL管理）
│   ├── EpisodicMemory - 情景记忆（具体事件，时间序列）
│   ├── SemanticMemory - 语义记忆（抽象知识，图谱关系）
│   └── PerceptualMemory - 感知记忆（多模态数据）
├── 存储后端层 (Storage Backend Layer)
│   ├── QdrantVectorStore - 向量存储（高性能语义检索）
│   ├── Neo4jGraphStore - 图存储（知识图谱管理）
│   └── SQLiteDocumentStore - 文档存储（结构化持久化）
└── 嵌入服务层 (Embedding Service Layer)
    ├── DashScopeEmbedding - 通义千问嵌入（云端API）
    ├── LocalTransformerEmbedding - 本地嵌入（离线部署）
    └── TFIDFEmbedding - TFIDF嵌入（轻量级兜底）
```

RAG系统专注于外部知识的获取和利用：
```
HelloAgents RAG系统
├── 文档处理层 (Document Processing Layer)
│   ├── DocumentProcessor - 文档处理器（多格式解析）
│   ├── Document - 文档对象（元数据管理）
│   └── Pipeline - RAG管道（端到端处理）
├── 嵌入表示层 (Embedding Layer)
│   └── 统一嵌入接口 - 复用记忆系统的嵌入服务
├── 向量存储层 (Vector Storage Layer)
│   └── QdrantVectorStore - 向量数据库（命名空间隔离）
└── 智能问答层 (Intelligent Q&A Layer)
    ├── 多策略检索 - 向量检索 + MQE + HyDE
    ├── 上下文构建 - 智能片段合并与截断
    └── LLM增强生成 - 基于上下文的准确问答
```

先给这篇复盘一张阅读地图。第一次接触 Memory 时，不要先背 Working、Episodic、Semantic 这些名词，先看一条记忆从哪里来、经过谁、最后保存在哪里：

```text
Agent / MemoryTool
        ↓
MemoryManager
        ↓
MemoryItem
        ↓
主记录：SQLite / Working Memory
语义检索：Qdrant
关系遍历：Neo4j（可选图投影）
```

后文先解释 `MemoryItem` 和四类记忆，再解释 `MemoryManager` 如何编排 add、search、forget、consolidate、update、delete，最后落到 Neo4j 的节点、关系、租户隔离、同步策略和测试。这样读者可以先建立职责地图，再看类名和 Cypher。

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

Hi-Agent 当前实现和教程不是完全一致。现在的工程分工是：SQLite 保存主记录，Qdrant 提供语义向量检索，Neo4j 是可选的关系图投影，DashScope 负责生产环境 embedding。这个差异不是“少装一个数据库”这么简单，而是每个后端承担的问题不同；后文会把这条边界展开。

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
内存、SQLite、Qdrant 等主存储实现
  ↓
Neo4j（启用时）保存关系投影
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

当前结果：Manager 已经承担了核心调度责任。Neo4j 接入后，它还负责决定什么时候把主记录投影到图中、什么时候删除图节点，以及如何在清空、遗忘、巩固后重建当前用户的图数据。这样 Agent 仍然只看到 Manager，不需要知道底层用了哪几个数据库。

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
Hi-Agent 的 RAG 已经负责外部文档检索，Memory 负责保存交互中形成的用户事实。
相互关联的记忆可以通过 Neo4j 建立关系，但图关系不能替代事实本身。
```

这类内容如果保存正确，会让 Agent 后续回答更贴合我自己的项目状态。但它也有风险：旧事实可能被新事实覆盖，错误总结可能长期污染后续回答。

近两年 Agent Memory 论文也在强调这个问题。LongMemEval 把长期记忆能力拆成信息抽取、多 session 推理、时间推理、知识更新和拒答五类，这说明“记住事实”只是基础能力，后续还要处理事实更新和不知道的问题。

Hi-Agent 现在已经接入了 Neo4j，但它不是“完整知识图谱自动抽取器”，也没有替代 Semantic Memory 的主记录。SQLite 仍然保存事实本身，Qdrant 负责语义相似检索；Neo4j 只保存记忆节点和显式的 `RELATED` 关系，用于“这条记忆还关联了什么”的遍历。

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

当前结果：Perceptual Memory 可以保留为实验模块。RAG 主链路已经完成，但多模态 Memory 仍然不属于当前主线；先把文本记忆的生命周期和隔离契约做稳更重要。

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

更新和删除也会经过 Manager，因此启用了 Neo4j 时，MemoryTool 不会只改 SQLite 而留下孤立的图节点。工具层仍然只负责参数和动作分发，图同步属于 Manager 的生命周期职责。

当前结果：MemoryTool 的动作集合已经比较完整。它不需要暴露“写 SQLite”“写 Qdrant”“写 Neo4j”这些存储细节，Agent 只面对 add、search、update、remove 等稳定动作。

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

当前结果：forget 不只是删主记录。启用图投影时，Manager 会同步删除对应的图节点；批量遗忘结束后还会重建当前用户的图投影，避免 SQLite 和 Neo4j 长期漂移。不同记忆类型仍需要继续收敛到统一的删除契约。

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

不过现在的 consolidate 仍然是初版。它还没有做 LLM 摘要，也没有把多个相似工作记忆合并成一条更抽象的语义记忆。这个阶段先不做复杂总结是合理的，因为幂等和来源记录比“智能总结”更基础。启用 Neo4j 时，巩固产生的新 `MemoryItem` 会被投影，批量操作结束后再同步一次图数据。

## 11. Neo4j：把记忆投影成可遍历的关系图

### 11.1 为什么 Neo4j 是投影层，而不是第二个主数据库

这一节最容易写错。看到“Memory + Neo4j”，很容易以为以后所有记忆都应该直接写进图数据库。Hi-Agent 目前不是这样设计的：

```text
MemoryItem
   │
   ├── SQLite：保存主记录，负责 CRUD 和生命周期
   ├── Qdrant：保存向量，负责语义相似检索
   └── Neo4j：保存节点和关系，负责显式关联与图遍历
```

Neo4j 保存的是 SQLite 记录的一个图投影。所谓“投影”，就是把主数据转换成适合另一种查询方式的副本。这样做有两个好处：

```text
Neo4j 暂时不可用时，基础记忆 CRUD 仍然可以工作；
图数据库只解决关系问题，不会和 SQLite 争夺事实的最终来源。
```

这也解释了为什么 Manager 的 `_project_to_graph()` 是 best-effort：写图失败会记录到 `graph_sync_errors`，但不应该让一次 Neo4j 网络故障阻塞主记忆写入。

### 11.2 一个 Memory 节点保存什么

`memory/storage/neo4j.py` 中的 `Neo4jMemoryStore` 把 `MemoryItem` 映射为 `Memory` 节点。关键属性不是随便挑的，它们共同决定了查询和隔离边界：

```text
id：MemoryItem 的稳定 ID
user_id：租户边界，所有读取、删除、关系遍历都必须带上它
content：记忆正文，供图侧的关键词过滤使用
memory_type：working / episodic / semantic / perceptual
timestamp：时间线排序
importance：重要性过滤和排序
session_id：会话范围过滤
metadata_json：额外 metadata 的 JSON 表示
```

初始化时会创建唯一约束和查询索引：

```cypher
CREATE CONSTRAINT memory_id_unique IF NOT EXISTS
FOR (m:Memory) REQUIRE m.id IS UNIQUE;

CREATE INDEX memory_user_id IF NOT EXISTS
FOR (m:Memory) ON (m.user_id);
```

这里的唯一约束解决“同一个 `MemoryItem` 重复投影会不会产生两个节点”；`user_id` 索引则服务于每次查询都必须执行的租户过滤。

### 11.3 关系类型固定，关系名称放在属性里

Manager 对外提供的是：

```python
manager.link_memories(
    source_id="memory-a",
    target_id="memory-b",
    relation="SUPPORTS",
    weight=0.9,
)

related = manager.retrieve_related_memories(
    memory_id="memory-a",
    relation="SUPPORTS",
    limit=10,
)
```

底层没有把 `SUPPORTS` 直接拼进 Cypher 的关系类型，而是统一使用 `RELATED`，把业务关系名保存为属性：

```cypher
MATCH (source:Memory {id: $source_id, user_id: $user_id})
MATCH (target:Memory {id: $target_id, user_id: $user_id})
MERGE (source)-[r:RELATED]->(target)
SET r.relation = $relation,
    r.weight = $weight;
```

这不是为了少写一个字符串。Cypher 的节点属性可以参数化，但关系类型不能用普通参数替代；如果把用户输入直接拼到关系类型中，就会同时带来注入风险和难以控制的 schema。固定 `RELATED` 后，关系名称变成普通数据，查询时再用 `r.relation = $relation` 过滤。

此外，`relate()` 和 `related()` 都会检查 source、target 与当前 `user_id`。因此一个用户不能通过知道另一个用户的 memory ID 来建立关系或遍历关系。

### 11.4 记忆生命周期怎样同步到图

Neo4j 适配完成后，Memory 的写入路径可以画成这样：

```text
MemoryTool
    ↓
MemoryManager
    ↓
SQLite / Working / Episodic / Semantic
    ↓
主记录成功后，best-effort upsert 到 Neo4j
```

具体动作对应的同步规则是：

```text
add：写入主存储后 upsert 图节点
update：先更新主记录，再刷新同一个图节点
delete：删除主记录，并删除当前用户的图节点
clear_all：清空主存储，同时清理当前用户的图投影
forget：批量遗忘后同步图数据
consolidate：投影巩固产生的新节点，并在批量结束后同步
sync_graph：清空当前用户的图投影，再从主存储重建
```

`sync_graph()` 是修复漂移的保险机制。它不是每次查询都运行的实时复制系统，而是一个可以显式调用的重建流程。工程上要承认：只要存在两个存储，就存在短暂不一致的窗口；关键是明确谁是主数据源、失败如何记录、怎样恢复。

### 11.5 配置、测试和真实连接边界

启用图投影只需要在配置中打开开关：

```python
from memory.base import MemoryConfig
from memory.manager import MemoryManager

config = MemoryConfig.from_env()
manager = MemoryManager(
    config=config,
    user_id="your_user_id",
    enable_working=True,
)
```

```env
NEO4J_ENABLED=true
NEO4J_URI=neo4j+s://your-cluster.example
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

单元测试不依赖真实数据库，而是把 fake driver 注入 `Neo4jMemoryStore`，检查节点 CRUD、关键词过滤、关系遍历和 `user_id` 隔离。实际结果是：

```text
Neo4j 单元测试：8 passed
Neo4j + MemoryTool 测试：11 passed
全量 pytest：通过
真实 Neo4j 冒烟：临时节点、关系创建、查询和删除通过
```

真实连接还暴露了一个不能靠“测试通过”掩盖的运维问题：当前机器使用 `neo4j+s` 时遇到自签名证书链错误，改用临时 `neo4j+ssc` 才完成冒烟。正式环境应该配置正确的 CA；只有明确接受自签名证书风险时才使用 `neo4j+ssc`。这属于连接信任配置，不是 Neo4j CRUD 逻辑已经正确的证明。

## 12. 为什么先写 pytest，再写 eval harness

这次 Memory 项目里有两层测试。

第一层是 pytest。它测的是代码逻辑是否正确，例如：

```text
add 后能否 search；
同一个 user_id 能否读到自己的记忆；
不同 user_id 是否隔离；
forget 后是否删除；
consolidate 是否幂等；
TTL 和容量限制是否生效。
Neo4j 节点是否按 `user_id` 隔离；
关系创建、遍历和删除是否符合生命周期；
图数据库不可用时，主存储是否仍然是事实来源。
```

这些测试应该用 fake embedder、临时存储和 fake Neo4j driver。它们不应该真实调用 LLM、DashScope 或 Qdrant Cloud。原因是单元测试要稳定，不能让网络、API Key、模型波动影响结果；真实服务的连通性、TLS 和供应商响应另用 smoke/integration test 验证。

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

这对 Hi-Agent 的意义是：图结构确实适合表达跨记忆的关联，但“接入 Neo4j”不等于已经实现 HippoRAG。当前 Hi-Agent 只支持显式创建 `RELATED` 关系和按关系遍历，没有自动抽取实体、构建知识图谱，也没有 Personalized PageRank。下一步仍然要用多跳失败样本判断这些能力是否值得增加。

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

当前结果：程序性记忆是后续方向，不放进当前 Memory 版本。Neo4j 现在解决的是“已知两条记忆有关联，如何保存和遍历”，还没有解决“系统如何自动发现新的关系”。

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
link_memories
retrieve_related_memories
update_memory
delete_memory
sync_graph
```

我现在把它当作 Memory 的主入口。它同时维护主存储和可选的 Neo4j 图投影，但不会把 Neo4j 当成基础 CRUD 的前置依赖。后续 RAG 不应该直接依赖这里的内部实现，但可以参考它的接口风格。

### `memory/storage/neo4j.py`

这是 Memory 的图存储适配层，职责比 `core/storage/qdrant.py` 更窄：

```text
MemoryItem → Memory 节点
memory_id + user_id → 租户安全的节点读取和删除
RELATED + relation 属性 → 显式关系
fake driver → 不依赖真实数据库的单元测试
```

它不负责替代 SQLite，也不负责把自然语言自动抽成知识图谱。

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

Semantic Memory 的向量检索仍然需要确认 Qdrant payload 的 `user_id` 强过滤；Neo4j 的关系检索则在 Cypher 的节点匹配和关系遍历中强制带上 `user_id`。两条链路都要靠测试确认，不能只看注释。

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

当前结果：文件边界比刚开始清楚了。RAG 主链路已经按 loader、splitter、index、retriever、context 和 generator 分层；Memory 也形成了“主记录、向量索引、关系投影”三种职责，而不是把所有能力塞进一个 Manager 文件。


## 17. Memory 现在已经形成一个可继续演进的闭环

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

这次 Neo4j 适配真正补上的，不只是一个数据库客户端，而是一个完整的生命周期问题：记忆更新时图节点要更新，记忆删除时关系要清理，批量遗忘和巩固后要能重建投影，跨用户查询不能泄露关系。它也让我更清楚地看到，工程里的“接入一个后端”通常意味着数据模型、失败策略、同步时机、测试替身和运维连接一起变化。

后续最值得继续做的是扩充 Memory fixture，补充事实更新、冲突、多 session、多跳关系和无答案样本；再用真实 embedding 重新评估阈值和检索质量。Neo4j 则先保持为显式关系层，等失败样本证明需要自动关系抽取或图排序时，再考虑更复杂的 GraphRAG 能力。

当前的 Memory 主线可以概括成：

```text
MemoryTool：Agent 的入口
MemoryManager：生命周期和存储编排
MemoryItem：统一记忆单元
SQLite：主记录和 CRUD
Qdrant：语义相似检索
Neo4j：可选关系投影和图遍历
pytest：验证契约、隔离和生命周期
eval harness：验证检索质量与拒答
trace evaluator：评估记录好的工具调用
```
