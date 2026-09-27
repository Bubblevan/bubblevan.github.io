---
schema: bubblevan/v1
id: project-health-copilot-01-rag-interview
content_kind: project
title: Health-Copilot：RAG / Evidence Retrieval 项目面试手册
linkTitle: 01 · RAG
weight: 10
date: 2026-09-27
updated: 2026-09-27
status: draft
visibility: public
projects:
  - project-health-copilot
summary: Health-Copilot Evidence/RAG 子系统的项目级面试手册：从 BM25、Dense、Hybrid、GAR、LameR、CRB、Multi-View、DualSource 到 Reranking、R2MED、指标、消融、Failure Analysis、论文与面试追问。
topics:
  - rag
  - retrieval
  - agent
  - harness
  - information-retrieval
  - health-ai
  - interview
---
这篇记录的是 Health-Copilot 的 Evidence/RAG 子系统。BM25、DPR、RRF、CrossEncoder 和 nDCG 的通用原理已经在另一份文档里讲过；这里集中复盘它们在项目中的用法：为什么需要、我怎么实现、数据怎样流动、实验怎样设计、结果为什么会这样、拿掉组件会有什么影响，以及面试官可能从哪些地方继续追问。

面试时，如果只说“我接了一个医疗向量数据库，然后做 RAG”，就把项目讲窄了。更准确地说，RAG 是 Health-Copilot Agent Harness 里负责获取外部证据的一层；我围绕“Agent 怎样可靠获取外部证据”，从 lexical retrieval 做到 dense、hybrid、generation-augmented、multi-view 和 candidate fusion，并用公开 R2MED benchmark 做系统验证与 failure analysis。

## 1. 先把项目讲明白：项目定位与 Evidence Retrieval

### 30 秒回答

> Health-Copilot 是一个 Evidence-first Agent Harness，RAG 是里面负责外部证据获取的一层。我最开始用 BM25 做 reviewed knowledge retrieval，后来为了验证检索能力本身，单独建立了公开 R2MED benchmark，从 Lucene BM25、BGE-large、Hybrid RRF，一直做到 HyDE、Query2Doc、LameR 这类 generation-augmented retrieval。我还设计了一个 compact clinical bridge，把 query 转成 canonical query、clinical terms 和 pseudo-evidence，再和 LameR 做候选融合。最终 public TEST 303 个 query 上，普通 BM25+BGE RRF 的 macro nDCG@10 是 0.1392，冻结的 DualSource pipeline 是 0.2142。

### 60–90 秒回答

> Health-Copilot 里的 RAG 不只是“向量检索 + Prompt”。在 Agent Harness 里，我把 retrieval 看成 Evidence Acquisition：检索出来的内容需要有来源、rank 和 provenance，后面才能给 claim verifier、citation 和 policy 使用。
>
> 产品早期先用 reviewed KnowledgeCard 和中文 BM25，把最基本的 evidence flow 跑起来。之后我发现内部 case 只能证明工程 contract，不能说明 retrieval 本身是否真的强，所以建立了公开 R2MED retrieval benchmark。
>
> 实验从 Lucene BM25、BGE-large、BM25+BGE RRF 开始，然后复现 HyDE、Query2Doc、LameR 等 generation-augmented retrieval。R2MED 的难点是 query 的表面措辞和真正相关医学文献之间可能隔着诊断、机制或治疗推理，所以我又设计了 Compact CRB，把 query 转成 canonical query、clinical terms 和 pseudo-evidence，通过 sparse/dense × original/generated 四路检索。
>
> CRB 自己没有超过 LameR，但它召回了一批 LameR 没找到的 relevant documents，所以最后做了 DualSource fusion。public TEST 上 DualSource 的 macro nDCG@10 是 0.2142，比普通 BM25+BGE RRF 的 0.1392 高 0.0750，但 LameR-MV 仍有 0.2225。这个结果让我把瓶颈定位到了“如何利用互补 candidate 并做好 top-rank ordering”，而不是简单继续增加召回。

### RAG 在整个 Harness 里的位置

整个 Runtime 可以抽象成：

```text
User Request
   ↓
Input / Safety / Capability
   ↓
Evidence Acquisition
   │
   ├─ Product Knowledge Retrieval
   ├─ Search / Retrieval Tool
   └─ Future external retrieval
   ↓
Evidence[]
   ↓
Bounded Agent Proposal
   ↓
Claim Construction
   ↓
Claim / Evidence Verification
   ↓
Policy Guard
   ↓
Materialize / Abstain
```

RAG 负责：

```text
query
→ candidates
→ ranked evidence
```

它不负责最终决定：

```text
这个 evidence 是否足够？
这个 claim 是否被支持？
是否允许回答？
是否应该拒答？
```

这些属于 Harness 的其他层。

### 为什么 Evidence Retrieval 不能只是 Vector DB

很多 RAG Demo 是：

```text
query
→ embedding
→ vector database
→ top-k
→ prompt
→ answer
```

工程上能跑，但有几个明显问题。

#### Dense retrieval 不是任何 query 都占优

精确实体、专业术语、药名、缩写等场景，lexical signal 仍然很强。因此一开始就丢掉 BM25 不合理。

#### Query 与 relevant document 可能不在同一种表达空间

例如 query 描述的是：

```text
症状 + 年龄 + 表现
```

文献写的是：

```text
诊断实体 + 病理机制 + 治疗术语
```

两边甚至没有明显词面重叠。这就是 reasoning-intensive retrieval 的典型问题。

#### Top-k 找到了，不代表排对了

Candidate generation 和 ranking 是两个问题。你可能：

```text
Recall@100 很高
```

但：

```text
nDCG@10 很低
```

意味着 relevant evidence 虽然存在于候选池，但排不到用户真正会使用的前几名。

#### Reranker 也不是万能的

CrossEncoder 能重新看 query-document interaction，但：

- 它可能破坏第一阶段已有的 reasoning signal；
- 输入 representation 可能和第一阶段不一致；
- top-k 太大会加入更多噪声；
- 通用 relevance model 未必理解 reasoning-driven relevance。

Health-Copilot 实验恰好出现了这个 failure。

### 产品 RAG 与 Benchmark RAG 的关系

它们属于**同一个 Evidence 子系统的两个视角**。

**产品 Runtime** 目标：

> 让 Agent 在 reviewed knowledge 范围里稳定拿到 evidence。

早期链路：

```text
患者教育问题
 → Safety Gate
 → Knowledge Scope
 → 中文 BM25
 → Evidence[]
 → Generator
 → Citation / Claim Verify
 → Answer / Abstain
```

它关注：

```text
route
source
citation
fail-closed
recovery
```

**R2MED Benchmark** 目标：

> 单独测 Retrieval 能力，避免产品知识库太小导致“自测自嗨”。

它不生成最终答案。输入：

```text
query + corpus
```

输出：

```text
ranked document IDs
```

再用：

```text
qrels
```

评分。所以 R2MED 是：

> **Evidence Acquisition component benchmark**

而不是整个 Health-Copilot 的端到端 benchmark。

## 2. 为什么选择 R2MED：数据与评测协议

R2MED 是 reasoning-driven medical retrieval benchmark。传统 retrieval 往往默认：

```text
query relevance
≈
lexical overlap / semantic similarity
```

R2MED 刻意强调：

```text
query
 → latent medical reasoning
 → relevant evidence
```

相关医学证据可能更接近：

```text
隐含诊断
机制
治疗策略
疾病实体
```

而不是 query 的表面措辞。

R2MED 原论文共包含 876 条 query，并覆盖不同医学 retrieval 场景；本项目没有使用全部 subset，而是按当前实验协议使用 3 个 DEV subset 和 3 个 TEST subset。R2MED 原论文也指出 reasoning-driven retrieval 对传统 lexical、dense、reranking 与 generation-augmented methods 仍然有明显挑战。

### 我们真正使用的数据

#### DEV

```text
PMC-Treatment    150
PMC-Clinical     114
IIYi-Clinical    129

Total            393
```

作用：

```text
选择方法
选择 fusion config
分析 failure
做 ablation
```

#### Final public TEST

```text
MedQA-Diag        118
MedXpertQA-Exam    97
Medical-Sciences   88

Total              303
```

对应 corpus row：

```text
MedQA-Diag         56,250
MedXpertQA-Exam    61,379
Medical-Sciences   34,810
```

三个 corpus 合计：

```text
152,439 rows
```

### 一条 R2MED 数据到底长什么样

逻辑上可以看成：

```python
query = {
    "id": "...",
    "text": "..."
}
```

corpus：

```python
document = {
    "id": "...",
    "text": "..."
}
```

qrels：

```python
relevance = {
    "query_id": "...",
    "document_id": "...",
    "score": ...
}
```

注意：

> 这里是结构示意，不是复制某一条 R2MED 原始样本。

Retriever 看到：

```text
query
corpus
```

Evaluator 才看到：

```text
qrels
```

### 为什么必须区分 query、document 和 qrels

这是 retrieval 实验最基本的数据边界。如果 generation 时知道：

```text
gold document ID
```

或者：

```text
relevance score
```

那么模型其实已经拿到了答案的一部分。因此我们的边界是：

```text
Generation:
query
+ allowed BM25 feedback

Retrieval:
query/generated representation
+ corpus

Evaluation:
ranking
+ qrels
```

qrels 不进入：

```text
query rewrite
candidate generation
fusion
ranking
```

### 为什么没有重新 Chunk R2MED

这一轮沿用 R2MED upstream 的 corpus unit。原因不是：

> chunking 不重要。

恰恰相反，chunking 会显著影响 retrieval：

```text
chunk 太长
→ semantic dilution
→ embedding 中目标信息占比下降

chunk 太短
→ context fragmentation
→ evidence 不完整
```

但如果我们同时：

```text
换 chunking
换 retriever
换 query rewrite
```

就无法知道 improvement 来自哪里。所以这一轮把：

```text
document unit
```

固定下来。如果未来做产品化 RAG，chunking 会单独成为一条实验轴。

### Query ID 的坑

R2MED 不同 subset 会复用数字 query ID。所以真正 identity 不是：

```text
query_id
```

而是：

```text
(subset, query_id)
```

这个坑我们在 final TEST preflight 中实际踩到过。错误代码相当于：

```python
assert len(set(all_query_ids)) == 303
```

但不同 subset 的 `"33"` 不是同一个 query。正确 identity：

```python
(subset_name, query_id)
```

这是一个非常典型的数据工程问题：

> **数据主键一定要理解 dataset scope，而不能看到一个 `id` 字段就假定全局唯一。**

## 3. BM25：为什么仍然要认真做，以及 Dense、Hybrid 与 RRF

BM25 不是“老东西所以拿来凑 baseline”。它仍然是检索系统里非常强的 lexical baseline。核心思想：

```text
Term Frequency
+
Inverse Document Frequency
+
Document Length Normalization
```

典型形式：

\[
score(q,d)
=
\sum_{t\in q}
IDF(t)
\frac{
tf(t,d)(k_1+1)
}{
tf(t,d)+k_1(1-b+b|d|/\text{avgdl})
}
\]

项目使用：

```text
Lucene / Pyserini
k1 = 0.9
b  = 0.4
top-100
```

### k1 和 b 应该怎么解释

**k1** 控制 TF saturation。不是：

```text
term 出现 10 次
= term 出现 1 次的 10 倍重要
```

而是：

> term frequency 增益逐渐饱和。

`k1` 越大，TF 饱和越慢。

**b** 控制 document length normalization。

```text
b = 0
```

基本不惩罚文档长度。

```text
b → 1
```

长度归一化影响更强。

**为什么医疗 retrieval 中 BM25 仍有价值** 例如：

```text
specific disease name
drug name
gene name
procedure name
abbreviation
rare term
```

这些词本身可能已经高度 discriminative。此时 lexical exact matching 很有优势。所以合理架构通常不是：

```text
BM25 OR Dense
```

而是：

```text
什么时候 lexical 更重要？
什么时候 semantic 更重要？
怎样融合？
```

### Dense Retrieval 在做什么

Dense retriever 用：

```text
query encoder
document encoder
```

把文本映射到向量：

\[
q \rightarrow \mathbf q
\]

\[
d \rightarrow \mathbf d
\]

再计算：

\[
sim(q,d)
\]

例如 cosine similarity：

\[
\cos(\mathbf q,\mathbf d)
=
\frac{\mathbf q^\top\mathbf d}
{\|\mathbf q\|\|\mathbf d\|}
\]

本实验使用：

```text
BAAI/bge-large-en-v1.5
```

**Dense 相比 BM25 的核心优势** BM25 看：

```text
token overlap
```

Dense 看：

```text
learned semantic representation
```

例如：

```text
myocardial infarction
```

与：

```text
heart attack
```

词面不同，但 dense representation 可能很接近。

**Dense 的问题** Dense 不是“理解语义所以一定更好”。主要问题：

**1. embedding bottleneck** 整段文本必须压到一个固定维度向量。

**2. domain mismatch** 训练数据和目标医学 retrieval 可能分布不同。

**3. reasoning gap** 一个 query 的真正 relevant evidence 可能需要先推理出：

```text
diagnosis X
```

而不是直接和症状文本做 similarity。

**4. exact entity dilution** 有时 lexical exact match 比模糊 semantic similarity 更可靠。

**我们的 basic dense baseline**

```text
Original Query
   ↓
BGE-large
   ↓
cosine similarity
   ↓
top-100
```

Final TEST：

```text
BM25       0.0763
BGE-large  0.1341
```

在 TEST 上 dense 明显优于 lexical。但 DEV：

```text
BM25       0.1913
BGE-large  0.1874
```

反而接近甚至 BM25 略高。因此不能简单记成：

> BGE 一定比 BM25 强。

更合理的结论：

> retriever relative strength 会随着 query type / corpus / subset 改变。

**为什么 DEV 和 TEST 数字差这么多** 首先不能直接做：

```text
DEV 0.30
vs
TEST 0.22
```

然后说：

> 泛化下降 0.08。

因为 DEV 和 TEST 本来就是**不同 subset**：

```text
DEV:
PMC-Treatment
PMC-Clinical
IIYi-Clinical

TEST:
MedQA-Diag
MedXpertQA-Exam
Medical-Sciences
```

任务性质和难度不相同。所以只能说：

> 不同 subset 的 retrieval difficulty 和 method ranking 存在明显差异。

不能把它当普通 IID train/test accuracy drop 来解释。

### Hybrid Retrieval 为什么存在

BM25：

```text
lexical view
```

BGE：

```text
semantic view
```

它们可能找到不同 documents。因此：

```text
BM25
   \
    → Fusion
   /
Dense
```

理论上有机会改善 candidate coverage。

**为什么不能直接加 BM25 score 和 cosine score** 因为两个分数不在同一个 scale。例如：

```text
BM25 score = 14.2
cosine     = 0.82
```

`14.2 + 0.82` 没有明确意义。你当然可以：

```text
normalize
calibrate
learn weights
```

但最简单稳定的办法是：

> 不看原始分数，只看 rank。

这就是 RRF。

### RRF 是什么

Reciprocal Rank Fusion：

\[
RRF(d)
=
\sum_i
\frac{w_i}{k+r_i(d)}
\]

其中：

```text
r_i(d)
```

是 document 在第 `i` 个 ranking 中的位置。 `w_i` 是该来源权重。 `k` 用来控制：

> rank 1 和 rank 20 的差距有多大。

**RRF 的优点**

**1. 不要求 score calibration** BM25 和 cosine 可以直接融合。

**2. 对单路 score distribution 鲁棒** 只依赖排名。

**3. 工程简单** 很适合 heterogeneous retrievers。

**RRF 的缺点**

**1. 丢掉 magnitude information** rank 1：

```text
score = 0.99
```

和：

```text
score = 0.61
```

在 RRF 看来都只是 rank 1。

**2. 固定权重不能 query-adaptive** 某个 query 可能：

```text
BM25 很可靠
```

另一个 query：

```text
dense 更可靠
```

但固定 RRF 不会变。

**3. 不能自动发现 reasoning relation** 它只能融合已有候选。

### 普通 Hybrid RRF 实验

```text
BM25 top100
+
BGE top100
↓
RRF(k=60, [1,1])
```

TEST：

```text
BGE             0.1341
BM25+BGE RRF    0.1392
```

只提高：

```text
+0.0051
```

所以：

> “Hybrid”这个词本身不是技术亮点。

真正重要的是：

> 两路到底有没有 complementary evidence。

## 4. 为什么开始做 Generation-Augmented Retrieval：HyDE、Query2Doc 与 LameR

R2MED 的核心问题可以写成：

```text
query representation
!=
relevant document representation
```

所以一种思路是：

> 在 retrieval 之前，先把 query 转换成更接近 corpus 语言空间的表示。

这就是：

```text
Query Transformation
Query Expansion
Hypothetical Document
Generation-Augmented Retrieval
```

### HyDE：必须会讲

HyDE = Hypothetical Document Embeddings。核心：

```text
query
 ↓
LLM
 ↓
hypothetical document
 ↓
dense encoder
 ↓
real corpus retrieval
```

它最重要的思想不是：

> 让 LLM 先猜答案。

而是：

> **用 LLM 生成一个更像 relevant document 的 representation，再由真实 corpus grounding。**

原论文明确指出 hypothetical document 本身可能包含虚构信息，它的作用是提供 relevance pattern，再由 dense encoder 将其映射到真实文档邻域。

**为什么 HyDE 即使“幻觉”也可能工作** 因为最终返回给用户的不是 hypothetical document。它只是：

```text
query representation intermediate
```

最终 evidence 仍然来自：

```text
real indexed corpus
```

所以其目标是：

> representation useful for retrieval

而不是：

> generated text factually correct。

**HyDE 的局限** 如果 hypothetical document：

```text
走错疾病方向
```

就可能把 embedding 带到错误 neighborhood。同时：

```text
LLM knowledge
```

未必和目标 corpus 分布一致。这就是为什么 LameR 引入：

```text
in-corpus candidates
```

非常有意义。

### Query2Doc 是什么

Query2Doc 同样使用 LLM 生成 pseudo-document。但典型思想更偏：

```text
query expansion
```

把：

```text
original query
+
generated pseudo document
```

组合起来用于 sparse / dense retrieval。原论文报告 LLM pseudo-document 可以改善 query disambiguation，并对 sparse 与 dense retrieval 都有帮助。

**HyDE 和 Query2Doc 怎么区别** 面试不要只说：

> 都是生成一段文本。

更准确：

**HyDE** 强调：

```text
generated hypothetical document
→ embedding
→ dense neighborhood
```

**Query2Doc** 强调：

```text
pseudo-document
→ query expansion
```

并可以直接增强 BM25 / dense query。

### LameR 为什么是这个项目最重要的论文

LameR 的核心不是：

```text
LLM 生成 query expansion
```

这么简单。它先做：

```text
query
 ↓
vanilla retrieval
 ↓
in-domain candidate documents
 ↓
LLM
 ↓
query augmentation
```

也就是：

> Retrieval-Augmented Retrieval。

LameR 的关键观察是：即使第一阶段 candidate 有很多错误，它们仍然提供了目标 corpus 的：

```text
style
terminology
genre
distribution
```

LLM 可以利用这些 in-collection signals 生成更适合 retrieval 的表示。原论文也强调这一点。

**为什么 LameR 用 BM25 做 first stage 很合理** 因为 BM25：

```text
transparent
non-parametric
lexical
```

不依赖另一个 dense retriever 的 representation bottleneck。流程：

```text
query
 ↓
BM25 top10
 ↓
Qwen
 ↓
bridge
```

这些 top10 不被标成：

```text
correct / wrong
```

LLM 不知道 qrels。只是把它们作为：

```text
noisy corpus feedback
```

### 我们的 LameR adaptation

使用：

```text
original query
→ BM25 top10
→ local Qwen3-8B
→ generated bridge
```

之后做四路 retrieval：

```text
1. BM25(original)
2. BM25(bridge)
3. BGE(original)
4. BGE(bridge)
```

再：

```text
weighted RRF
```

DEV 选出的 frozen config：

```text
RRF k = 20
weights = [1, 2, 1, 2]
```

意味着：

> generated representation 通道权重更高。

但原 query 仍然保留。

**为什么不能只搜 generated bridge** 因为 generation 可能：

```text
偏题
漏掉 exact entity
过度推断
```

所以：

```text
original query
```

是一个 anchor。这也是 multi-view retrieval 的核心思想：

> 不赌一个 representation 一定正确。

### Multi-View Retrieval

我们的四视图实际上是一个 2×2：

| | Original | Generated |
|---|---|---|
| Sparse | BM25(q) | BM25(g) |
| Dense | BGE(q) | BGE(g) |

它同时覆盖两个维度：

**Retrieval inductive bias**

```text
lexical vs semantic
```

**Query representation**

```text
original vs generated
```

**为什么这是比“多搜几次”更合理的解释** 如果只是：

```text
同一个 query
BM25 跑 4 次
```

没有新增信息。这里每个 channel 代表不同假设：

```text
original sparse
→ exact lexical anchors

generated sparse
→ expansion terms

original dense
→ original semantic intent

generated dense
→ inferred / corpus-like semantics
```

## 5. 我为什么没有停在 LameR：CRB、候选互补与 DualSource

LameR bridge 是自由文本。我当时的问题是：

> 能不能把 query transformation 结构化，使不同信息显式分离？

于是有了：

```text
Clinical Reasoning Bridge
CRB
```

### CRB 的原始设计

第一版包含：

```text
canonical_query

key_concepts

disambiguating_terms

pseudo_evidence
```

目标：

**canonical_query** 把自然语言 case 转成更标准的 retrieval formulation。

**key_concepts** 显式抽取可能有价值的医学实体/机制。

**disambiguating_terms** 减少相似疾病/概念之间的 ambiguity。

**pseudo_evidence** 生成一个 corpus-like evidence representation。

### CRB 第一版为什么“失败”

第一版：

```text
max_output_tokens = 256
```

同时要求输出完整四字段 JSON。结果：

```text
CRB-Q valid:
156 / 393
= 39.7%
```

很多 output 在 JSON 尾部被截断。这不是：

> reasoning 一定错。

而是：

> serialization 没完成。

更糟的是 invalid 时按 contract fallback：

```text
original query
```

所以第一版 CRB 分数其实混合了：

```text
真实 CRB
+
大量 original-query fallback
```

**为什么这是一个很好的工程教训** Structured Output 有两个不同 failure：

**semantic invalid** JSON 合法，但内容不满足要求。

**syntactic invalid** JSON 本身没有闭合。如果：

```text
grammar
```

只能约束 token 合法性，但：

```text
max_tokens
```

提前耗尽， grammar 也无法凭空补完整 JSON。

### Compact CRB 为什么出现

我们没有：

```text
max_tokens 256 → 1024
```

直接增加成本。而是压缩 schema：

```json
{
  "q": "...",
  "t": ["...", "..."],
  "e": "..."
}
```

分别表示：

```text
q = canonical query
t = key biomedical terms
e = short pseudo-evidence
```

**Compact CRB 修复效果** DEV：

```text
旧 CRB valid:
39.7%

Compact CRB:
97.2%
```

截断：

```text
241
→
0
```

macro nDCG@10：

```text
0.2482
→
0.2921
```

提升：

```text
+0.0439
```

这说明：

> structured generation 的 interface design 本身会直接影响 retrieval quality。

### Compact CRB 为什么仍没超过 LameR

DEV：

```text
LameR-MV       0.2998
Compact CRB    0.2921
```

分 subset：

```text
PMC-Treatment
CRB 0.3870
LameR 0.4571
Δ -0.0701

PMC-Clinical
CRB 0.2650
LameR 0.2627
Δ +0.0023

IIYi-Clinical
CRB 0.2243
LameR 0.1796
Δ +0.0447
```

所以 CRB 不是全局无效。它在：

```text
IIYi / clinical-style queries
```

明显有 signal。但：

```text
PMC-Treatment
```

损失太大。

**为什么 LameR 在 Treatment 类 query 特别强** 这只能做**机制假设**，不能说已经因果证明。合理解释：

> LameR 先看 BM25 的 in-corpus passages，因此对 treatment evidence 的 corpus wording、药物/治疗描述和 document style 可能适应得更好。

CRB-Q 没有 PRF feedback，只从 query 自己生成结构。所以：

```text
LameR:
query + corpus feedback

CRB-Q:
query only
```

这是一个重要差异。

**那为什么 CRB 还有价值** 因为：

```text
weak standalone ranker
```

不意味着：

```text
no complementary candidates
```

这就是后来 candidate union analysis 的意义。

### Candidate Complementarity

TEST Recall@100：

```text
LameR-MV
0.56987

Compact CRB
0.53399
```

CRB 单独更弱。但是 raw union：

```text
0.62045
```

明显高于两者。 Relevant document pairs：

```text
LameR-only = 95
CRB-only   = 62
Both       = 430
Neither    = 471
```

所以：

> CRB 确实找到了 LameR 没找到的一部分 relevant evidence。

**为什么 Raw Union 不能直接当系统分数** Raw union：

```text
top100(LameR)
∪
top100(CRB)
```

可能有接近：

```text
200 distinct candidates
```

它只是说：

> relevant doc 有没有存在于 pool 里。

但系统最后需要：

```text
ranked top100
```

甚至更关心：

```text
top10
```

所以 raw union Recall 是：

> candidate ceiling。

不是：

> final retrieval quality。

### DualSource-RRF

为了利用互补性：

\[
S(d)
=
\frac{1}{60+r_L(d)}
+
0.5
\frac{1}{60+r_C(d)}
\]

其中：

```text
rL = LameR ranking
rC = CRB ranking
```

候选按：

```text
doc_id
```

去重。

**为什么 CRB weight 是 0.5** DEV sweep：

```text
λ = 0.5
1
2
```

结果：

```text
λ=.5  0.3019
λ=1   0.3010
λ=2   0.2981
```

所以 frozen：

```text
λ = .5
```

这和直觉也一致：

> CRB 有补充价值，但 standalone quality 比 LameR 略低，所以不应该和 LameR 完全等权。

### DualSource 最终做到了什么

TEST：

```text
LameR:
nDCG@10  0.2225
R@100    0.5699

DualSource:
nDCG@10  0.2142
R@100    0.5791
```

也就是：

> Recall 更高，但 top-10 ranking 更差。

这是整个项目最重要的 insight 之一。

**为什么 Recall 高但 nDCG 低** 举一个简单例子。系统 A：

```text
relevant doc at rank:
1, 3
```

系统 B：

```text
relevant doc at rank:
20, 30, 60
```

B 可能 Recall@100 更高。但是：

```text
nDCG@10
```

A 会远远更高。所以：

```text
Candidate Generation
```

和：

```text
Top-Rank Ordering
```

必须分开评估。

## 6. 为什么尝试 Reranker：Reranking 与 Reasoning-Intensive Retrieval

既然：

```text
raw candidate union recall 很高
```

自然的问题是：

> 能不能让一个 stronger ranker 把 relevant candidates 推上去？

所以尝试：

```text
BGE-reranker-v2-m3
```

### Bi-Encoder 和 CrossEncoder 的差别

#### Bi-Encoder

```text
query → vector
doc   → vector

similarity(q,d)
```

document embedding 可以提前算好。优点：

```text
快
可 ANN
适合大规模 retrieval
```

#### CrossEncoder

输入：

```text
[query ; document]
```

一起进入 Transformer。模型可以看：

```text
token-level query-document interaction
```

通常精度更高，但：

```text
每个 query-doc pair 都要 forward
```

所以只适合：

```text
top-K reranking
```

### 我们的 Reranker 实验

DEV：

```text
LameR-MV
0.2998
```

加入 BGE reranker：

```text
K=20
0.2009

K=30
0.1763

K=50
0.1591
```

K 越大越差。同时：

```text
Recall@100
```

没有变化，因为候选池没变。所以：

> 失败发生在 ordering，不是 candidate generation。

### 为什么 CrossEncoder 反而更差

有几个合理解释。

#### 假设一：representation mismatch

第一阶段 LameR 的 ranking 已经包含：

```text
original query
generated bridge
sparse signal
dense signal
```

但 CrossEncoder 只看：

```text
original query
+
document
```

它看不到 bridge/provenance。

#### 假设二：通用 relevance ≠ reasoning relevance

一个 document 表面看起来和 query 不够类似，但经过：

```text
诊断 / 机制 inference
```

其实高度 relevant。通用 reranker 可能把它降下去。

#### 假设三：candidate depth 加大引入噪声

实验中：

```text
K20 > K30 > K50
```

与此一致。

**为什么不能因此说“CrossEncoder 没用”** 因为我们只验证：

```text
BGE-reranker-v2-m3
+
当前输入格式
+
当前 truncation
+
当前 candidate source
+
R2MED DEV
```

不能外推：

```text
所有 reranker 都没用。
```

**ReasonRank 为什么值得看** ReasonRank 是专门面向 reasoning-intensive reranking 的工作。

它不是简单 pointwise relevance scorer，而是通过 reasoning-intensive ranking data 和两阶段训练增强 listwise ranking 能力；其公开项目描述包括 cold-start SFT 和 multi-view ranking reward RL。它说明：

> reasoning-intensive retrieval 可能需要 reasoning-aware ranking model，而不是普通 relevance CrossEncoder。

**GroupRank 为什么值得看** 传统：

```text
Pointwise
```

一次看：

```text
query + one doc
```

容易缺少 document 间比较。 Listwise：

```text
query + many docs
```

能做全局比较，但 context/cost 很大。 GroupRank 尝试 groupwise：

```text
query
+
small group of candidates
```

同时保留 comparative ranking 能力和较好的扩展性，并使用 GRPO 与 ranking-oriented reward 训练。这和我们的 failure 非常相关：

> candidate pool 有好 document，但怎么把它排到前面？

### Reasoning-Intensive Retrieval 的更一般定义

2026 的 Reasoning-Intensive Retrieval Survey 把这类任务概括为：

> relevance 不直接由 lexical / semantic similarity 决定，而通过 latent inferential links 连接 query 与 evidence。

这正是理解 R2MED 的最佳抽象。

**为什么未来不能只继续 Prompt Engineering** CRB 和 LameR 都属于：

```text
training-free query transformation
```

问题是：

> generator 输出什么内容，对最终 retrieval reward 并没有直接优化。

ExpandR 直接指出很多 LLM query augmentation 方法存在：

```text
generation objective
和
retrieval objective
不对齐
```

它通过 jointly optimizing LLM 与 retriever，并用 retrieval effectiveness / generation consistency 引导生成。我们的 CRB failure 正好可以这样理解：

> prompt 认为“好的 clinical bridge”不一定等价于 retriever 认为“最有用的 bridge”。

**DEPT 对我们有什么启发** DEPT 更进一步做：

```text
query expansion
+
retrieval representation
```

端到端优化。它关注一个实际问题：

> retriever 训练过程中，如果 document embeddings 也不停变化，那么已建好的 index 会失效。

所以引入：

```text
Document Embedding Preservation
```

让 query side 更可塑，document embedding 尽量稳定，并让 retrieval gradient 影响 expansion。这和真实生产系统非常相关：

> 你不能每次 retriever update 都重新 encode 数百万文档。

**Agentic-R 为什么是未来方向** 普通 RAG retriever 优化：

```text
local query-passage relevance
```

但 Agentic Search 真正关心：

> 这个 passage 最终有没有帮助 Agent 得到正确答案？

Agentic-R 同时利用：

```text
local passage relevance
+
global answer correctness
```

训练 retriever，并让 Agent 与 retriever 迭代优化。这正好连接 Health-Copilot 后面的：

```text
Harness
→ Trajectory
→ Reward
→ Post-training
```

### 输入输出完整 Pipeline

最终 RAG research pipeline 可以展开成：

```text
                     R2MED Query
                         │
            ┌────────────┴────────────┐
            │                         │
        LameR branch              CRB branch
            │                         │
      BM25 top10                      │
            │                         │
         Qwen3-8B                  Qwen3-8B
            │                         │
       bridge passage             {q,t,e}
            │                         │
      ┌─────┼─────┐             ┌─────┼─────┐
      │     │     │             │     │     │
 BM25(q) BM25(g) BGE(q) BGE(g) ... same 2×2 views
      │     │     │             │
      └─────┴─────┘             └───────────
            │                         │
       weighted RRF              weighted RRF
            │                         │
       LameR-MV                  Compact CRB
             \                       /
              \                     /
               └── DualSource RRF ─┘
                         │
                    ranked docs
                         │
                    evaluator
                         │
             nDCG / MRR / Recall
```

## 7. 最终 TEST 指标矩阵：指标、统计检验与 Ablation

| Method | MedQA-Diag | MedXpertQA | Medical-Sciences | Macro nDCG@10 | MRR@10 | R@10 | R@100 |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 | .0255 | .0066 | .1968 | .0763 | .0798 | .1137 | .2973 |
| BGE-large | .0833 | .0410 | .2781 | .1341 | .1347 | .2029 | .4275 |
| BM25+BGE RRF | .0811 | .0257 | .3109 | .1392 | .1472 | .2010 | .4157 |
| Compact CRB-Q | .1376 | .0766 | .3841 | .1995 | .2205 | .2752 | .5340 |
| DualSource | .1510 | .0894 | .4023 | .2142 | .2328 | .2904 | **.5791** |
| **LameR-MV** | **.1655** | **.0980** | **.4039** | **.2225** | **.2406** | **.2971** | .5699 |

### 三个必须背的结果

#### DualSource vs ordinary Hybrid

```text
0.2142 - 0.1392
= +0.0750
```

相对：

```text
+53.9%
```

#### DualSource vs BM25

```text
+0.13794
```

但不建议作为主 headline，因为 BM25 baseline 太低。

#### DualSource vs LameR

```text
-0.00823
```

所以：

> 最强 reproduced method 仍然是 LameR-MV。

### nDCG@10 到底是什么

DCG：

\[
DCG@K
=
\sum_{i=1}^{K}
\frac{2^{rel_i}-1}{\log_2(i+1)}
\]

然后：

\[
nDCG@K
=
\frac{DCG@K}{IDCG@K}
\]

核心：

> relevant document 越靠前，价值越高。

**为什么使用 nDCG 而不是只用 Recall** Recall 不关心：

```text
rank 1
```

还是：

```text
rank 99
```

只要都在 top100。但真实 RAG context window 不可能塞 100 篇全文。所以 top-ranking 很关键。

**MRR@10** 对每条 query：

```text
第一个 relevant doc 排第 r
```

则：

\[
RR=\frac{1}{r}
\]

如果 top10 都没有：

```text
0
```

平均以后是 MRR。它回答：

> 第一个有用 evidence 到底出现得多早？

**Recall@K**

\[
Recall@K
=
\frac{
\#relevant\ documents\ retrieved\ in\ topK
}{
\#all\ relevant\ documents
}
\]

它主要回答：

> Candidate generation 有没有漏证据？

**为什么看 Recall@100** 因为如果：

```text
Recall@100 很低
```

那么 reranker 再强也没用。相关 document 根本不在 candidate pool。如果：

```text
Recall@100 高
nDCG@10 低
```

则说明：

> ranking 是主要瓶颈。

### Equal-Subset Macro

TEST 三个 subset query 数：

```text
118
97
88
```

不是完全相同。我们先各自求 mean：

```text
M1
M2
M3
```

再：

\[
Macro = \frac{M_1+M_2+M_3}{3}
\]

防止：

> query 更多的 subset 自动主导最终分数。

**为什么不用 Micro** Micro：

```text
303 queries
全部直接平均
```

这样 118-query subset 权重大于 88-query subset。如果我们想：

> 每个任务类型同等重要

macro 更合理。

### Paired Bootstrap 为什么是 paired

因为两个方法是在：

```text
同一批 query
```

上比较。所以每次 resample 时：

```text
A_query_i
和
B_query_i
```

必须一起抽。否则会破坏 query-level correlation。

**为什么还要按 subset stratify** 因为三个 subset 分布不同。如果完全自由 resampling，有些 bootstrap sample 可能：

```text
MedQA 多很多
Medical-Sciences 少很多
```

改变 macro 结构。所以按 subset 各自 sample，再求 macro。

### 完整 DEV 路径

这部分面试非常值得讲，因为它体现：

> 不是一次就知道最终 architecture。

主要 DEV 节点：

| Method | Macro nDCG@10 |
|---|---:|
| BM25 | .1913 |
| BGE-large | .1874 |
| BM25+BGE RRF | .2169 |
| HyDE-BGE | .2416 |
| Query2Doc-BM25 | .2109 |
| LameR-BM25 | .2596 |
| LameR-BGE | .2892 |
| LameR-MV | .2998 |
| Old CRB-Q | .2482 |
| Compact CRB-Q | .2921 |
| DualSource λ=.5 | **.3019** |
| LameR+BGE rerank K20 | .2009 |

这张表就是整个研究过程。

### 我们到底做没做 Ablation

做了。只是更准确地叫：

> staged ablation / component diagnostics

而不是一次统一 factorial ablation。

**Ablation 1：Sparse vs Dense**

```text
BM25
vs
BGE
```

回答：

> lexical 和 semantic 哪个更合适？

**Ablation 2：Single vs Hybrid**

```text
BGE
vs
BM25+BGE RRF
```

回答：

> 两路基础 retrieval 是否互补？

**Ablation 3：Original vs Generated Query**

```text
Original
vs
HyDE
vs
Query2Doc
vs
LameR
```

回答：

> generation augmentation 是否有用？

**Ablation 4：Corpus Feedback** 粗略比较：

```text
HyDE / Query2Doc
vs
LameR
```

LameR 多了：

```text
BM25 top10 corpus feedback
```

虽然不能完全做严格单因素因果归因，但可以观察 PRF-aware generation 的价值。

**Ablation 5：Single-view vs Multi-view** 例如：

```text
LameR-BGE
0.2892

LameR-MV
0.2998
```

说明：

> 保留 sparse/original/generated 多视图有进一步收益。

**Ablation 6：CRB Serialization**

```text
Old CRB:
valid 39.7%
nDCG .2482

Compact:
valid 97.2%
nDCG .2921
```

这是非常清楚的 interface ablation。

**Ablation 7：CRB Internal Components** DEV 做过：

```text
original dense
CRB lexical
CRB dense
lexical fusion
dense fusion
full CRB
```

用于判断：

> gain 来源是 lexical、dense 还是 fusion。

结果显示 full four-view fusion 相比 best simplified CRB arm 有明显增量。

**Ablation 8：Candidate Union**

```text
LameR candidates
CRB candidates
raw union
```

回答：

> 两个方法到底只是重复，还是有真实 complementarity？

**Ablation 9：DualSource λ**

```text
0.5
1
2
```

回答：

> CRB 权重增加是否有帮助？

结果：

```text
0.5 最佳
```

**Ablation 10：Reranker Depth**

```text
K=20
K=30
K=50
```

结果：

```text
越深越差
```

说明：

> 更多 candidate 进入通用 reranker 并没有改善 reasoning ranking。

### 从实验结果倒推原因

#### 结果一

```text
BM25 TEST .0763
BGE      .1341
```

推论：

> TEST subsets 更依赖 semantic retrieval。

但不是：

> Dense 永远比 BM25 好。

因为 DEV 不是如此。

**结果二**

```text
BGE  .1341
RRF  .1392
```

推论：

> basic sparse+dense complementarity 有，但有限。

**结果三**

```text
RRF    .1392
LameR  .2225
```

推论：

> 关键提升不只是 fusion，而是 query representation transformation。

**结果四**

```text
CRB < LameR
```

但：

```text
union recall > both
```

推论：

> representation diversity 有价值，但 standalone ranking quality 和 complementarity 是两回事。

**结果五**

```text
Dual R@100 > LameR
Dual nDCG < LameR
```

推论：

> 当前瓶颈转向 candidate ordering。

**结果六**

```text
CrossEncoder 大幅掉点
```

推论：

> 通用 semantic relevance scorer 可能覆盖掉 GAR 构造出的 reasoning-aware ordering。

这是一种解释，不是已证明机制。

### 实验工程为什么也值得讲

严肃面试官会问：

> 你这些分数可信么？

这时不要开始背 commit SHA。直接讲四件事。

**1. Same-generator fairness** 所有 GAR method 使用同一：

```text
Qwen3-8B
```

**2. Gold isolation** generation/ranking 不读 qrels。

**3. Frozen config** TEST 前 config lock。

**4. Per-query artifacts** ranking、generation、manifest 可 replay。

## 8. 为什么使用本地 Qwen3-8B：实验工程与系统设计

现实考虑：

```text
公平
成本
可重复
隐私
无需 API 波动
```

固定：

```text
temperature = 0
one call/query
no retry
```

减少 stochastic variance。

**为什么 Q4 量化也可以用于这个实验** 因为目的不是：

> 证明 Qwen3-8B full precision SOTA。

而是：

> 给多个 GAR methods 提供同一个 frozen generator。

公平性主要来自：

```text
同模型
同量化
同调用预算
同 decoding
```

**为什么生成只允许一次** 如果：

```text
invalid → retry
```

某个方法实际享受更多 model budget。于是：

```text
方法能力
```

和：

```text
额外采样预算
```

混在一起。所以 compact CRB invalid 时直接：

```text
fallback original query
```

### 为什么没有把失败 generation 删掉

因为真实系统也会失败。如果只评：

```text
valid cases
```

会形成 selection bias。所以 final pipeline 必须包含：

```text
failure semantics
```

**为什么要 Cache** Retrieval experiment 很多计算是可复用的：

```text
document embedding
generation outputs
ranking artifacts
reranker pair score
```

如果每次 config 都重算：

```text
成本高
容易漂移
不利于 debug
```

所以 cache identity 必须绑定：

```text
model
data
query
document
config
```

### 如果真正上线，该怎么设计 Index

产品化通常会：

```text
Document ingestion
 → parse
 → clean
 → metadata
 → chunk
 → sparse index
 → dense embedding
 → vector index
```

在线：

```text
query
 → route
 → retrieve
 → fusion
 → optional rerank
 → evidence
```

### FAISS / Milvus / Elasticsearch 应该怎么选

不要背“哪个最好”。

**FAISS** 适合：

```text
单机
离线
embedding experiment
```

**Milvus / Qdrant / Vector DB** 适合：

```text
在线 vector service
filter
scaling
persistence
```

**Elasticsearch / OpenSearch** 适合：

```text
lexical BM25
filter
production search
hybrid
```

真正选择看：

```text
corpus scale
latency
filter
update frequency
ops complexity
```

**为什么本实验不用 Vector DB** 因为这是：

```text
frozen offline benchmark
```

真正关心：

```text
ranking method
```

不是：

```text
distributed serving
```

增加 Milvus 并不会让研究问题更清楚。

### 如果 corpus 每天更新怎么办

需要：

```text
incremental indexing
embedding version
index version
document tombstone
cache invalidation
```

尤其 dense：

> embedding model 一换，旧 index 很可能需要重建。

这也是 DEPT 关注 document embedding preservation 的现实意义之一。

**如果 Query 很长怎么办** 可能：

```text
query decomposition
query compression
multi-query
field extraction
```

但要防止：

```text
rewrite 丢掉关键约束
```

产品中最好保留：

```text
original query
```

作为一个 retrieval view。

**如果 Query 是多轮对话怎么办** 直接 embed：

```text
整个 chat history
```

通常不理想。可以先：

```text
conversation
→ standalone query rewrite
```

再 retrieval。 2026 SemEval 多轮 RAG 系统大量采用：

```text
query rewriting
→ hybrid retrieval
→ reranking
```

并证明它仍是非常强的实践路线。

**如果没有相关文档怎么办** Retriever 必须允许：

```text
no evidence
```

而不是：

```text
top-k 永远返回东西
→ 就假设有答案
```

所以在 Harness 里 retrieval confidence 之后还需要：

```text
EvidencePolicy
```

判断：

```text
sufficient / insufficient / conflicting
```

### RAG 的真正 failure taxonomy

面试可以按四层说。

#### Query failure

```text
ambiguous
underspecified
wrong rewrite
missing context
```

#### Retrieval failure

```text
relevant doc absent
index stale
embedding mismatch
lexical mismatch
```

#### Ranking failure

```text
candidate exists
but ranked too low
```

#### Generation failure

```text
evidence good
but final answer hallucinated / unsupported
```

Health-Copilot R2MED 主要评前三层中的：

```text
query representation
retrieval
ranking
```

不评最终 answer generation。

**为什么 RAG 不是“防幻觉万能药”** Retriever 可能：

```text
检索错
```

Generator 可能：

```text
忽略 evidence
```

Evidence 可能：

```text
冲突
过期
不充分
```

所以：

```text
RAG
≠
factual guarantee
```

Health-Copilot 才会继续有：

```text
Claim/Evidence Verifier
Policy
Abstain
```

### RAG 与 Agentic Search 的区别

Static RAG：

```text
query
→ retrieve once
→ generate
```

Agentic Search：

```text
query
→ reason
→ retrieve
→ inspect
→ reformulate
→ retrieve again
→ stop
```

后者多了：

```text
policy
state
trajectory
stopping
credit assignment
```

所以自然进入 Harness/RL 范畴。

### 如果未来做 Retrieval RL，我会训练什么

不是一上来训练最终回答。可以先训练 policy：

```text
Should Retrieve?
Which Query?
Which Tool?
Retrieve Again?
Stop?
Which Evidence?
```

Trajectory：

```text
state
→ retrieval action
→ result
→ next state
→ final outcome
```

Reward 可以考虑：

```text
retrieval quality
answer correctness
cost
latency
tool failures
```

这就是 RAG 与后续 RL 的接口。

## 9. 论文精读路线

这一部分不是“论文收藏夹”。每篇都要能回答：

```text
解决什么问题？
输入输出是什么？
方法在哪一层改？
训练还是 inference-only？
指标是什么？
和 Health-Copilot 哪一步对应？
它能解释我们的哪个结果？
```

### S 级：R2MED

**R2MED: A Benchmark for Reasoning-Driven Medical Retrieval，2025** 必须读：

```text
Task Definition
Dataset Construction
Subsets
Reasoning gap
Baseline matrix
GAR
Reranking
Reasoning models
Error analysis
```

你要能回答：

> 为什么不用 BEIR/NFCorpus 作为最终主 benchmark？

答：

> 因为 Health-Copilot 后续研究重点是 reasoning-driven evidence retrieval，而 R2MED 明确构造了 query 与 evidence 之间存在 latent clinical reasoning gap 的任务；NFCorpus 更适合通用 biomedical sanity。

**S 级：LameR**

**Retrieval-Augmented Retrieval: Large Language Models are Strong Zero-Shot Retriever，Findings ACL 2024** 必须理解：

```text
为什么是 Retrieval-Augmented Retrieval
为什么 first-stage candidate 即使错误也可能有用
为什么强调 in-domain corpus style
为什么 BM25 做 first stage
```

项目映射：

```text
R2MED strongest reproduced method
```

**S 级：HyDE**

**Precise Zero-Shot Dense Retrieval without Relevance Labels** 必须理解：

```text
hypothetical document
dense bottleneck
zero-shot retrieval
generated document ≠ evidence
```

项目映射：

> 解释“为什么生成错误事实也可能改善 retrieval”。

**S 级：Query2Doc**

**Query2doc: Query Expansion with Large Language Models** 重点：

```text
pseudo-document
few-shot generation
sparse improvement
dense improvement
```

项目映射：

> 与 HyDE/LameR/CRB 比较 query expansion philosophy。

**S 级：RRF**

**Reciprocal Rank Fusion** 必须手写：

\[
\sum_i \frac{w_i}{k+r_i}
\]

并回答：

```text
为什么不用 raw score 相加？
k 变大会怎样？
weight 如何理解？
missing rank 怎么处理？
```

**S 级：BM25** 必须会：

```text
TF saturation
IDF
document length normalization
k1
b
```

不是只背公式。

**S 级：DPR**

**Dense Passage Retrieval** 重点不是复现 DPR。而是掌握：

```text
bi-encoder
in-batch negatives
MIPS
pre-computed document embeddings
```

这样面试官问 BGE 时你有理论底座。

### A 级：BEIR

重点：

```text
zero-shot evaluation
heterogeneous domains
nDCG@10
retriever generalization
```

同时理解：

> 一个 retriever 在一个 benchmark 强，不等于跨 domain 都强。

**A 级：Original RAG**

**Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks** 重点：

```text
parametric memory
non-parametric memory
retriever + generator
RAG-Sequence / RAG-Token
```

但不要说：

> R2MED 实验复现了 Lewis RAG。

没有。

**A 级：ExpandR**

**ExpandR: Teaching Dense Retrievers Beyond Queries with LLM Guidance，EMNLP 2025** 关键问题：

> query generator 和 retriever 分开优化，生成内容未必对 retrieval 最有用。

方法：

```text
LLM expansion
+
retriever training
+
DPO
+
retrieval-oriented reward
```

项目映射：

> CRB 是 prompt-defined bridge；ExpandR 提醒我们应该让 retrieval reward 真正反向约束 expansion。

**A 级：DEPT**

**DEPT: Document Embedding Preservation Tuning for Unified Query Expansion and Retrieval，2026** 核心：

```text
single decoder model
expansion + retrieval
straight-through optimization
document embedding preservation
index reuse
```

项目映射：

> 如果以后从 prompt CRB 升级到 trainable retrieval bridge，怎样避免 document index 随训练不断失效。

**A 级：ReasonRank** 核心：

```text
reasoning-intensive reranker
listwise ranking
SFT
RL
ranking reward
```

项目映射：

> 解释为什么通用 BGE CrossEncoder 失败后，更合理的方向是 reasoning-aware reranker，而不是再换一个类似 CrossEncoder。

**A 级：GroupRank** 核心：

```text
pointwise myopia
listwise rigidity
groupwise ranking
GRPO
ranking reward
```

项目映射：

> 对 DualSource raw union 的高 candidate recall，groupwise comparative reasoning 可能比 independent pointwise score 更适合。

**A 级：Reasoning-Intensive Retrieval Survey** 作用：

> 建立完整 taxonomy，不让自己只会几个论文名字。

建议整理：

```text
Reasoning at Query side
Reasoning in Retriever
Reasoning in Reranker
Agentic Retrieval
Benchmarks
Training
Evaluation
```

### B 级：Agentic-R

核心变化：

```text
passage relevance
→
passage utility for final answer
```

使用：

```text
local relevance
+
global answer correctness
```

并迭代更新 agent/retriever。项目映射：

> Health-Copilot 后训练真正值得做的不是“让 query rewrite 更像人”，而是让 retrieval action 对 downstream outcome 更有 utility。

**B 级：Query Rewriting Bias** 2026 有工作系统研究 query rewriting 对 dense retriever bias 的影响，指出 rewriting 并不会统一解决所有 bias，不同 retriever 上效果差异明显。项目映射：

> 不要把 query rewrite 当 universally-positive preprocessing。

## 10. 面试策略：回答任何 RAG 问题的五步法

如果面试官问一个复杂问题，不要立刻钻公式。按：

```text
1. 问题是什么
2. 为什么 baseline 不够
3. 我的设计是什么
4. 实验怎么看
5. trade-off / failure 是什么
```

例如：

> 为什么做 CRB？

不要回答：

> 因为我想生成 q/t/e。

应该回答：

> R2MED 的核心问题是 query-document representation gap。LameR 用 corpus feedback 自由生成 bridge，我想测试结构化 query representation 是否能提供另一类 complementary evidence，所以把 canonical query、terms 和 pseudo-evidence 分开，再让 sparse/dense 分别利用。结果 standalone 不如 LameR，但 union recall 确实说明它提供了一部分独立 candidates。

这就是“项目回答”。

### P0：必须秒答的问题

下面这些如果卡壳，项目基本就会被判成“只会跑代码”。

**Q1：你的项目为什么需要 RAG？**

答题抓手：

```text
knowledge grounding
fresh/non-parametric evidence
citation/provenance
Harness evidence layer
```

**Q2：你这个 RAG 和普通向量数据库 Demo 有什么区别？**

答：

```text
sparse+dense+GAR+multi-view
evidence object
candidate analysis
benchmark
failure semantics
```

**Q3：BM25 是什么？**

必须解释：

```text
TF saturation
IDF
length normalization
```

**Q4：为什么 BM25 现在还重要？**

答：

```text
exact term/entity
zero training
transparent
complement dense
```

**Q5：Dense Retrieval 是什么？**

答：

```text
bi-encoder
embedding
similarity
ANN
```

**Q6：为什么 dense 可能比 BM25 好？**

答：

```text
semantic paraphrase
lexical mismatch
```

**Q7：为什么 dense 可能比 BM25 差？**

答：

```text
domain shift
exact entity
embedding bottleneck
reasoning gap
```

**Q8：什么是 Hybrid Retrieval？**

答：

```text
multiple retrieval inductive biases
sparse+dense
```

**Q9：RRF 是什么？**

手写：

\[
\sum \frac{w_i}{k+r_i}
\]

**Q10：为什么用 RRF 不直接加分？**

答：

```text
heterogeneous score scales
```

**Q11：什么是 HyDE？**

答：

```text
query
→ hypothetical doc
→ dense embedding
→ real corpus
```

**Q12：HyDE 的生成内容是 evidence 吗？**

答：

```text
不是
retrieval representation
```

**Q13：Query2Doc 与 HyDE 区别？**

答：

```text
query expansion vs hypothetical embedding emphasis
```

**Q14：LameR 的关键创新？**

答：

```text
retrieve first
→ in-domain noisy candidates
→ LLM query augmentation
→ retrieve again
```

**Q15：为什么叫 Retrieval-Augmented Retrieval？**

因为：

```text
第一次 retrieval
服务于第二次 retrieval
```

**Q16：你的 CRB 是什么？**

答：

```text
structured query-side retrieval bridge
q/t/e
```

**Q17：为什么 CRB 第一版失败？**

答：

```text
256-token cap
structured JSON truncation
39.7% valid
```

**Q18：怎么修的？**

答：

```text
compact schema
same token budget
valid 97.2%
```

**Q19：什么是 Multi-View Retrieval？**

答：

```text
Sparse/Dense × Original/Generated
```

**Q20：最终最强方法是谁？**

```text
LameR-MV
TEST nDCG@10 .2225
```

**Q21：你的 DualSource 是多少？**

```text
.2142
```

**Q22：你超过了 LameR 吗？**

```text
没有
```

**Q23：那你提升体现在哪？**

```text
ordinary BM25+BGE RRF
.1392 → .2142
+0.0750
```

**Q24：为什么 headline 不和 BM25 比？**

因为：

> 更合理的 comparator 是 ordinary hybrid baseline，不应挑最低 baseline 营销。

**Q25：为什么看 nDCG？**

答：

```text
relevance + rank position
```

**Q26：Recall 和 nDCG 区别？**

答：

```text
coverage vs ordering
```

**Q27：为什么你的 Recall 更高但 nDCG 更低？**

答：

```text
new relevant docs enter candidate pool
but ranked too low
```

**Q28：CrossEncoder 为什么失败？**

答：

```text
ordering negative transfer
not candidate loss
```

**Q29：qrels 是什么？**

答：

```text
query-document relevance judgments
```

**Q30：有没有 label leakage？**

答：

```text
qrels only evaluator after ranking
```

### P1：项目深挖

**Q31：为什么用 top100？**

回答：

> 用较深 candidate pool 同时支持 Recall@100、fusion 与后续 reranking analysis；最终 quality 仍主要看 top10。

**Q32：为什么 LameR feedback top10？**

回答：

> Follow upstream-style design；足够提供 corpus pattern，同时控制 prompt noise 和 token cost。

**Q33：为什么 generated channel 权重 2？**

回答：

> DEV frozen configuration 的结果，不是理论常数。

**Q34：RRF k=20 和 k=60 有什么区别？**

回答：

> k 越小越强调高 rank 差距；k 越大 rank contribution 更平滑。

**Q35：为什么第二层 DualSource 用 k=60？**

回答：

> 更平滑地融合两个已经较强的完整 ranking，而不是再次极端放大 top few。

**Q36：为什么 CRB weight=.5？**

回答：

> DEV λ sweep 的 frozen choice；reflect standalone quality lower but complementary.

**Q37：为什么不训练 λ？**

回答：

> 数据量小，固定 grid 更容易控制 overfit；真正 learned fusion 应开新 protocol。

**Q38：为什么不直接 concat LameR bridge 和 CRB bridge？**

回答：

> 会把 representation 与 fusion 两个变量混在一起，也失去来源 provenance。

**Q39：为什么 original query 必须保留？**

回答：

> 防 generation drift；保留 exact lexical/semantic anchor。

**Q40：generated sparse view 有什么作用？**

回答：

> expansion terms 可以产生新 lexical matches。

**Q41：generated dense view 有什么作用？**

回答：

> 把 query 映射到更接近 corpus/document style 的 semantic representation。

**Q42：为什么 multi-view 不一定比 single-view 好？**

回答：

> 新 view 可能只是噪声；fusion 会把错误 ranking 一起带进来。

**Q43：你的实验怎么控制 multi-view fairness？**

回答：

> 同类 multi-view 方法使用相同 channel family，并在 DEV 使用预声明 fusion grid。

**Q44：为什么 same-generator 很重要？**

回答：

> 否则 improvement 可能来自 generator 能力差，而不是 GAR method。

**Q45：为什么没有 OpenAI API？**

回答：

> 成本、repeatability 和公平性；不是因为 API 一定不好。

**Q46：温度为什么 0？**

回答：

> 控制 stochastic variance，使 method comparison 更稳定。

**Q47：为什么 no retry？**

回答：

> retry 是额外 inference budget，会改变方法成本。

**Q48：如果 output invalid 怎么办？**

回答：

> frozen fallback 到 original query。

**Q49：这样不会伤 CRB 分数吗？**

回答：

> 会，但这是系统真实 failure semantics；删掉 invalid case 会产生 selection bias。

**Q50：为什么 Compact CRB 97.2% 还没到 100%？**

回答：

> 剩余是结构/semantic validation failure，不再发生大量 token truncation。

**Q51：为什么最后不继续修 7 条 TEST invalid？**

回答：

> config 已冻结；测试后修复等于 test tuning。

**Q52：为什么 R2MED 而不是只有 NFCorpus？**

回答：

> NFCorpus 适合 biomedical retrieval sanity；R2MED 直接 targeting latent reasoning relevance，更贴合 query transformation / reasoning bridge 研究。

**Q53：为什么不用整个 R2MED 876 queries？**

回答：

> 当前 protocol 使用了固定 6 subsets；不能把结果外推成完整 benchmark result。

**Q54：三个 TEST subset 为什么等权？**

回答：

> 防止 query 数不同导致 headline 被大 subset 支配。

**Q55：BM25 DEV 为什么比 BGE 稍高，而 TEST BGE 明显高？**

回答：

> subset/task composition 不同；不能把某个 retriever strength 当全局规律。

**Q56：为什么不能直接比较 DEV .30 和 TEST .22？**

回答：

> 它们是不同 subset，不是同 distribution 下简单 train/test split。

**Q57：为什么普通 RRF TEST Recall@100 反而比 BGE 单路低？**

回答：

> RRF 优化 rank fusion，不保证每个 cutoff 的 recall 单调优于最佳 source；融合可能把某些单路 candidate 挤出 top100。

**Q58：为什么 raw union Recall 高于 DualSource Recall？**

回答：

> raw union pool 有最多约 200 candidate；DualSource 最后截成 top100，需要排序取舍。

**Q59：为什么不直接给 generator raw union 200 docs？**

回答：

> token/cost 很高，且这是另一个方法 family；需要新的 DEV protocol。

**Q60：Candidate overlap 怎么算？**

可以讲：

```text
Jaccard(A,B)=|A∩B|/|A∪B|
```

并进一步看：

```text
relevant-only overlap
```

比普通 candidate overlap 更有解释力。

### P1：Metrics 与实验

**Q61：Precision@K 呢？为什么没 headline？**

R2MED 当前协议主要关注：

```text
nDCG / MRR / Recall
```

Precision 当然能算，但 relevant set 大小和 task 结构下 nDCG 更适合作为 primary ranking metric。

**Q62：MAP 和 MRR 区别？**

MRR：

```text
只看第一个 relevant
```

MAP：

```text
综合多个 relevant docs 的 precision-at-relevant positions
```

**Q63：nDCG 支持 graded relevance 吗？**

支持。

\[
2^{rel}-1
\]

可以让更高 relevance 得到更大 gain。

**Q64：如果 qrels 只有 binary relevance 呢？**

nDCG 仍然成立，只是 gain 退化为：

```text
0/1
```

**Q65：为什么 K=10？**

因为主要关心：

> 实际上下文前部和 top-rank evidence。

同时它也是 retrieval benchmark 常见 cutoff。

**Q66：Recall@100 是否太深？**

它不是最终 UX metric，而是：

> candidate generation diagnostic。

**Q67：Bootstrap CI 是什么？**

不断：

```text
resample queries
→ recompute Δ
```

得到 empirical delta distribution。

**Q68：为什么不直接做 t-test？**

Retrieval per-query metrics：

```text
non-normal
bounded
often skewed
```

bootstrap 更直观。

**Q69：CI 跨 0 怎么解释？**

当前数据下：

> 方法差值的不确定区间包含无差异。

不能声称稳定胜出。

**Q70：为什么 LameR 与 Dual CI 跨 0，但 point LameR 高？**

Point estimate 与 uncertainty 是两回事。

```text
observed mean Δ < 0
```

但 resampling uncertainty 包含 0。

### P2：刁钻架构问题

**Q71：你这个 CRB 不就是 Prompt Engineering？**

应答：

> 第一阶段确实是 training-free prompt-defined query transformation，但贡献不止 prompt：我固定 same-generator/cost，设计 structured representation、multi-view retrieval、candidate provenance 与 complementarity analysis，并用公开 benchmark验证。它不是新训练算法，我不会说成新模型。

**Q72：DualSource 不就是 RRF 套 RRF？**

回答：

> 从算法公式上确实是 hierarchical rank fusion，所以我称 adaptation，不称新 rank-learning algorithm。价值在于验证两个不同 generation mechanisms 的 candidate complementarity，以及 quantifying recall-vs-ranking trade-off。

**Q73：那创新性是不是很弱？**

回答：

> 如果按论文算法创新衡量，确实不主张 novel SOTA；这个项目的目标是 Agent/RAG/Harness 岗，核心是完整技术栈、公开 benchmark、实验设计、failure attribution 和可复现 Runtime integration。若继续做 research innovation，我会进入 learned query transformation / reasoning-aware ranker / retrieval RL。

**Q74：为什么不用更强 embedding，例如 2026 新模型？**

回答：

> Baseline selection需要可复现且和 R2MED upstream 有合理对应；中途更换 dense model 会改变整个实验坐标。如果开新 benchmark protocol，可以加入新 retriever。

**Q75：为什么不直接用最强 32B generator？**

回答：

> 项目需要控制成本和 local reproducibility；same-generator fairness 比绝对 generator size 更重要。

**Q76：如果换强 generator，结果会不会变？**

会。尤其：

```text
HyDE/Q2D/LameR/CRB
```

都依赖 generation quality。所以 Qwen3-8B 是实验 identity 的一部分。

**Q77：你的 improvement 是不是只因为多调用 LLM？**

这是非常关键的问题。回答：

> 对 BM25/BGE/RRF，GAR 确实额外用了 generator，因此不能说是同成本系统。为此我另外做 same-generator GAR comparisons、multi-view cost-matched comparisons，并报告 strongest LameR，而不是只拿 BM25 做“公平算法胜利”。

**Q78：那成本指标为什么最终表里没 headline？**

当前主研究目标是 retrieval quality，生成 call 数和 zero-paid-API 被审计，但没有建立完整 wall-clock/cost-normalized TEST frontier，所以不能假装有完整成本最优结论。

**Q79：如果面试官要求 latency 怎么做？**

拆：

```text
retrieval latency
generation latency
fusion latency
optional rerank latency
```

再报告：

```text
p50
p95
throughput
GPU utilization
tokens/query
```

**Q80：你的 Qwen 是同步还是异步？**

当前 final frozen local generation 是受控批量实验 pipeline；如果上线，应把 generation service、retriever、cache 做异步/批处理和 backpressure。

**Q81：如果 BM25 top10 全错，LameR 为什么还能工作？**

因为 candidates 还能暴露：

```text
corpus terminology/style
```

但如果完全 off-topic，也可能误导 generator。

**Q82：Pseudo-Relevance Feedback 和 LameR 有什么关系？**

传统 PRF：

```text
top docs
→ extract terms
→ expand query
```

LameR：

```text
top docs
→ LLM synthesize augmentation
```

可以视为更 expressive 的 LLM-based PRF。

**Q83：为什么不直接做 RM3？**

RM3 是非常合理的传统 PRF baseline；当前实验没有系统加入，因此如果面试官问，承认这是 baseline completeness 可以继续补的方向，不要虚构结果。

**Q84：为什么不加 SPLADE？**

同理，SPLADE 是 learned sparse retrieval，很适合作为更强 sparse baseline，但当前 benchmark 没有跑，不声称做过。

**Q85：为什么不加 ColBERT？**

ColBERT 提供 late interaction，能保留 token-level matching 且比 full cross-encoder 更 scalable，也是合理未来 baseline；当前未运行。

**Q86：为什么不用 late interaction 解决 embedding bottleneck？**

这正是 ColBERT 类模型的动机之一；如果重新开启 retrieval protocol，它值得和 single-vector BGE 对比。

**Q87：CrossEncoder 为什么通常比 Bi-Encoder 准？**

因为 query/document 进入同一个 attention graph，可直接建模 token-level interaction。

**Q88：那为什么不把整个 corpus CrossEncode？**

复杂度接近：

```text
O(number_of_documents × model_forward)
```

不可扩展。所以：

```text
retrieve → rerank
```

**Q89：为什么你的 Rerank K 越大越差？**

可能：

```text
更多噪声
cross-encoder miscalibration
reasoning mismatch
```

当前实验只证明现象，不证明唯一原因。

**Q90：为什么不融合 CrossEncoder score 和原 RRF score？**

这是一个合理 future method。当前 frozen reranker 是：

```text
replace top-K order
```

如果做 score fusion，需要单独解决：

```text
calibration
α selection
DEV tuning
```

不能测试后临时补。

### P2：数据与工程死角

**Q91：Duplicate document ID 怎么处理？**

BM25 延续 upstream indexing 行为，再按 doc ID fold scored result；dense 使用 unique-ID view。不同文本却复用同 ID 时应该 fail，而不是静默合并。

**Q92：为什么 BM25 与 Dense corpus view 不完全一样还叫公平？**

核心 document identity 一致；差异来自 upstream duplicate-row semantics。这个边界需要记录，不能假装 byte-for-byte identical preprocessing。

**Q93：你用了什么 tokenizer？**

BM25 由 Lucene/Pyserini analyzer 负责 lexical tokenization；BGE 使用自己的 Transformer tokenizer。

**Q94：中文患者教育为什么不是同一个 BM25？**

产品侧中文 tokenizer / KnowledgeCard retrieval 和 R2MED 英文 Lucene benchmark 是两套运行环境。共同抽象：

```text
Retriever
```

而不是同一 index。

**Q95：如何防止 model/data version 漂移？**

项目里有：

```text
model pin
dataset revision
artifact hash
generation manifest
final config lock
```

面试不背 hash，只讲机制。

**Q96：为什么 TEST 前要 freeze？**

否则：

```text
看结果
→ 改 λ
→ 再看结果
```

测试集就变开发集。

**Q97：你已经早期访问过 TEST，后面为什么还跑？**

最终 TEST 的用途被重新限制为：

> frozen pipeline 相对 basic baselines 的公开 benchmark evidence。

没有把它包装成 untouched confirmatory test。

**Q98：这会不会削弱结果？**

会削弱“独立 confirmatory”意义，但不影响：

> 这些 frozen rankings 在这个公开数据上真实达到这些分数。

面试重点是工程/算法能力，不要主动把自己说成论文统计推断。

**Q99：为什么 final TEST 出现 ID bug？**

因为错误假设：

```text
numeric ID globally unique
```

实际：

```text
subset-local
```

**Q100：这次修复有没有污染结果？**

没有重新生成或 rerank；修复发生在 qrels scoring 前，只修改 identity validation scope。

### P2：如果我要把系统上线

**Q101：Online RAG 最大区别是什么？**

Benchmark：

```text
frozen corpus
offline metrics
```

Production：

```text
updates
latency
availability
filters
permissions
cache
observability
```

**Q102：文档更新怎么处理？**

需要：

```text
versioned ingestion
incremental sparse index
incremental dense index
deletion
re-embedding policy
```

**Q103：怎么处理权限文档？**

Retrieval 前或 retrieval 内做：

```text
ACL filter / tenant filter
```

不能：

```text
先 retrieve unauthorized doc
再让 LLM 自己忽略
```

**Q104：怎么做 Cache？**

可以分：

```text
query embedding cache
retrieval result cache
generation bridge cache
document embedding cache
```

但 cache key 必须带：

```text
model/index/version
```

**Q105：如何做 Observability？**

每个 retrieval trace 至少记录：

```text
query
rewrite
retriever
candidate IDs
scores/ranks
fusion
latency
index version
evidence selected
```

**Q106：怎么判断线上 retrieval regression？**

建：

```text
golden query set
offline regression
online click/evidence utility
failure slices
```

**Q107：Embedding model 升级怎么灰度？**

A/B 两个 index version：

```text
old embedding
new embedding
```

同 query shadow evaluation，再逐步切流。

**Q108：如何处理 embedding/index mismatch？**

Index manifest 必须记录：

```text
model identity
dimension
normalization
corpus hash
```

不匹配直接 fail。

### P2：RAG 与 Harness

**Q109：什么时候不应该检索？**

可能：

```text
simple conversational
already sufficient context
prohibited/urgent requests
tool cost > value
```

由 routing/policy 决定。

**Q110：什么时候需要 second retrieval？**

当：

```text
evidence insufficient
conflicting
query under-specified
```

但需要 budget。

**Q111：为什么 model 不能无限 search？**

因为：

```text
latency
cost
loop
context pollution
```

Harness 必须有 termination condition。

**Q112：Retrieval tool 的输出为什么要结构化？**

后续需要：

```text
source
rank
score
doc_id
provenance
```

做 verification 和 audit。

**Q113：为什么 Evidence 不能直接变成 Context String？**

一旦 flatten：

```text
来源
rank
identity
support relation
```

容易丢失。

**Q114：Evidence 和 Memory 什么区别？**

Evidence：

```text
当前任务的外部支持材料
```

Memory：

```text
跨 turn/跨 session 的内部状态
```

它们都可能 retrieval，但语义不同。

**Q115：RAG 与 Tool Use 什么关系？**

Retriever 可以作为：

```text
read-only tool
```

Agent 根据状态决定是否调用。

**Q116：RAG 与 RL 怎么连接？**

Retrieval actions 进入 trajectory：

```text
state
action
candidate
reward
```

可优化：

```text
retrieve / rewrite / stop / select
```

### P2：Future Research

**Q117：如果只允许做一个下一步，你做什么？**

不是再改 prompt。会考虑：

> retrieval-objective-aligned query transformation，类似 ExpandR/DEPT 思路，让生成的 bridge 真正被 retrieval reward 优化。

**Q118：为什么不是更大 LLM？**

更大 LLM 可能提高生成质量，但没有解决：

```text
generation objective
!=
retrieval objective
```

**Q119：为什么不是再加一个 reranker？**

已有通用 reranker negative result。更有价值的是：

```text
reasoning-aware reranking
```

或者：

```text
ranker receives bridge/provenance
```

**Q120：为什么 candidate union 这么高，却没转成 nDCG？**

因为缺一个真正有效的：

```text
candidate utility estimator
```

这是未来 ranking research 的重点。

**Q121：Learned Fusion 怎么做？**

Feature 可以有：

```text
BM25 rank
dense rank
LameR rank
CRB rank
source agreement
score margin
retriever confidence
query type
```

训练：

```text
LTR
small MLP
GBDT
neural ranker
```

**Q122：为什么当前没做 Learned Fusion？**

393 DEV queries 太少，且如果继续围绕当前 TEST 打磨容易过拟合；应该开新 protocol 和新 holdout。

**Q123：Agentic-R 对你最大的启发？**

未来 relevance 不应只定义为：

```text
query-document similarity
```

而应该问：

> 这条 evidence 是否提高最终 Agent outcome？

**Q124：ReasonRank/GroupRank 对你最大的启发？**

ranking 本身也可以成为：

```text
reasoning problem
```

而不只是分类问题。

**Q125：DEPT 对工程最大的启发？**

trainable query-side adaptation 不能破坏：

```text
production document index stability
```

## 11. 严肃面试官可能要求你现场画什么：面试复盘与复习卡片

至少会画四张。

### 图一：Harness 总图

```text
Safety
→ Retrieval
→ Evidence
→ Agent
→ Claim
→ Verify
→ Answer
```

### 图二：Basic RAG

```text
BM25
   \
    RRF
   /
BGE
```

### 图三：LameR Multi-View

```text
q
↓
BM25 top10
↓
LLM bridge
↓
Sparse/Dense × Original/Generated
↓
RRF
```

### 图四：DualSource

```text
LameR-MV
    \
     RRF → final
    /
CRB-MV
```

如果这四张能白板顺畅画出来，项目理解基本不会太差。

### 面试最容易翻车的十句话

不要说：

**1.**

> 我们的 RAG 准确率 21.4%。

错。这是：

```text
macro nDCG@10
```

不是 accuracy。

**2.**

> CRB 比 LameR 强。

错。

**3.**

> DualSource 是我们的新 SOTA 算法。

错。

**4.**

> R2MED 是我们的端到端医疗问答 benchmark。

错。它这里用于 retrieval。

**5.**

> CrossEncoder 在医学 RAG 里没用。

错。只能说 frozen BGE reranker setting negative。

**6.**

> HyDE 生成的是 evidence。

错。

**7.**

> Recall 越高系统就越好。

错。

**8.**

> RRF 会提高 recall。

不一定。

**9.**

> Dense 一定比 BM25 好。

错。

**10.**

> 加 RAG 就不会 hallucinate。

错。

### 硬背数字卡

```text
R2MED DEV
393
= 150 PMC-Treatment
+ 114 PMC-Clinical
+ 129 IIYi-Clinical
```

```text
R2MED TEST
303
= 118 MedQA-Diag
+ 97 MedXpertQA-Exam
+ 88 Medical-Sciences
```

```text
BM25
k1=.9
b=.4
```

```text
Generator
Qwen3-8B Q4_K_M
temp=0
reasoning off
256 output tokens
1 call/query/method
```

```text
TEST nDCG@10

BM25          .0763
BGE           .1341
RRF           .1392
CRB           .1995
DualSource    .2142
LameR         .2225
```

```text
Dual - RRF
+.07502
+53.88%
```

```text
Recall@100

LameR         .56987
CRB           .53399
Raw union     .62045
DualSource    .57911
```

```text
DEV

LameR-MV      .2998
Compact CRB   .2921
Dual λ=.5     .3019
BGE rerank    .2009
```

### 硬背公式卡

BM25 至少记住结构：

```text
IDF
×
TF saturation
×
length normalization
```

RRF：

\[
\sum_i \frac{w_i}{k+r_i}
\]

Cosine：

\[
\frac{q^\top d}{\|q\|\|d\|}
\]

DCG：

\[
\sum_i \frac{2^{rel_i}-1}{\log_2(i+1)}
\]

nDCG：

\[
DCG/IDCG
\]

MRR：

\[
\text{mean}(1/r_{\text{first relevant}})
\]

Recall：

\[
\frac{\text{retrieved relevant}}{\text{all relevant}}
\]

### 硬背 Attribution 卡

```text
BM25
经典 sparse retrieval

BGE
公开 dense embedding model

RRF
经典 rank fusion

HyDE
公开 hypothetical-document retrieval

Query2Doc
公开 LLM query expansion

LameR
公开 Retrieval-Augmented Retrieval 方法

Compact CRB
Health-Copilot structured query bridge

DualSource
Health-Copilot 两个 frozen rankings 的 fusion adaptation
```

### 简历结果应该怎么说

推荐：

> 在公开 R2MED 医疗检索 benchmark 的 303-query TEST 上，复现并改造 BM25、BGE、Hybrid RRF 与 generation-augmented retrieval pipeline；通过 LameR 与结构化 clinical bridge 的候选融合，将 equal-subset macro nDCG@10 从普通 BM25+BGE RRF 的 **0.139 提升至 0.214（+0.075 absolute / +53.9% relative）**，并通过候选重叠和 Recall/nDCG 消融定位 candidate coverage 与 top-rank ordering 的瓶颈。

面试追问时再主动补：

> strongest reproduced LameR-MV 是 0.2225，所以 DualSource 没超过它。

### 如果面试官问“所以你的最大贡献到底是什么”

可以答：

> 如果按论文算法创新来说，我不会说自己发明了一个新 SOTA retriever。我的贡献更偏 Agent/RAG engineering 和实验方法：第一，我把 retrieval 做成 Harness 里带 provenance 的 Evidence 层；第二，从 sparse/dense/hybrid 到 GAR 和 multi-view 做了一条完整可复现 baseline ladder；第三，设计了 structured CRB，并通过 compact schema、candidate union、DualSource 和 reranker ablation 把失败原因拆到了 generation validity、candidate coverage 和 ranking 三层；第四，所有关键实验都有固定数据、配置、artifact 和 per-query trace，所以面试时每个结果都能解释到组件级，而不是只展示一个最终分数。

### 如果面试官问“这个项目让你真正学到了什么”

一个好的结尾：

> 我最大的收获是 RAG 不是“选个 embedding 模型 + vector DB”。真正复杂的是表示、候选生成、排序、证据边界和系统约束之间的关系。实验里最典型的例子就是 CRB：它确实带来了 LameR 没召回的 evidence，所以 raw union Recall 提高，但简单 fusion 没把这些 candidate 排到 top10；再加一个通用 CrossEncoder 又会破坏已有 ranking。这个过程让我从“堆组件”转向了“先判断 bottleneck 在 query representation、candidate generation 还是 ranking，再决定下一步该改哪里”。我觉得这个思路比某一个具体模型更能迁移到 Agent Harness 和后续的 retrieval policy learning。

### 最终复习顺序

如果明天面试，按下面顺序复习。

### 第一轮：10 分钟

只背：

```text
项目 60 秒介绍
Harness 中 RAG 的位置
最终 architecture
六个 TEST 分数
三个核心 insight
```

### 第二轮：30 分钟

重点：

```text
BM25
Dense
RRF
HyDE
Query2Doc
LameR
CRB
Multi-view
DualSource
Reranker
Metrics
```

### 第三轮：1 小时

把：

```text
P0 + P1
```

全部口头过一遍。

### 第四轮：论文

优先顺序：

```text
R2MED
→ LameR
→ HyDE
→ Query2Doc
→ RRF
→ DPR / BEIR
→ ExpandR
→ ReasonRank
→ DEPT
→ GroupRank
→ Agentic-R
```

### 最终 Checklist

面试前确认自己可以不看文档回答：

```text
[ ] Health-Copilot 为什么不是普通 RAG Demo
[ ] RAG 在 Harness 的位置
[ ] R2MED 为什么适合这个项目
[ ] query / corpus / qrels 是什么
[ ] DEV / TEST 有多少 query
[ ] BM25 / BGE / RRF 的原理
[ ] HyDE / Query2Doc / LameR 区别
[ ] LameR 为什么强
[ ] CRB 为什么做
[ ] CRB 第一版为什么失败
[ ] Compact schema 怎么修
[ ] Multi-view 四个 channel 是什么
[ ] DualSource 为什么做
[ ] raw union / ranked recall 区别
[ ] nDCG / MRR / Recall 区别
[ ] 最终六个 TEST 分数
[ ] 为什么 reranker 会 negative transfer
[ ] 哪些是公开方法，哪些是自己的 adaptation
[ ] 为什么没有继续 TEST tuning
[ ] 如果未来继续做，为什么应该走 retrieval-aligned training / reasoning reranking / retrieval policy
```

如果这些问题能够自然回答，这一块就已经足够支撑一次严肃的 RAG / Agent / Harness 技术面。
