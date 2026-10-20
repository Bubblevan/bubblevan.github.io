---
schema: bubblevan/v1
id: blog-20261020-ftec5660-retrieval-rag
content_kind: blog
title: "FTEC5660：从文档索引到 Agentic RAG 的检索系统"
date: 2026-10-20
updated: 2026-10-20
status: draft
visibility: public
summary: "沿 10 月 20 日课堂与 tutorial 顺序，整理 chunking、稀疏与稠密检索、向量索引、RRF、重排、Agentic RAG、Precision/Recall 及 Langfuse 链路调试。"
topics: [FTEC5660, Retrieval, RAG, Embeddings, Vector Database, Evaluation]
projects: []
aliases: []
authors: [bubblevan]
---

10 月 20 日 FTEC5660 从语言模型的知识边界讲到 Retrieval-Augmented Generation（RAG），后半段再用 notebook 搭了一条最小检索问答链路。整堂课的问题不是“向量数据库怎么调用”，而是：怎样把外部资料变成可检索的证据，怎样从候选里挑出适合回答当前问题的片段，又怎样判断这个检索过程到底好不好。

本文按转写的讲课顺序展开。前半是概念讲解，后半是 LangChain、embedding、Milvus 和 Langfuse 的 tutorial。若模型名称、参数或课堂数字受转写影响，我会标成课堂示例或保留其范围，不把一次 notebook 结果推广成普遍规律。

## 1. 为什么让模型检索外部资料

语言模型的参数来自某个时间点之前的训练数据；它未必知道最新政策，也看不到用户私有文档或刚发生的事实。即使它不知道答案，也可能给出听起来完整的内容，这就是事实性错误和 hallucination 风险。Grounding 的目的，是让生成过程能够使用可检查的外部依据。

一种办法是把整份资料直接塞进 prompt。报告较短时这很直接，但长报告会占满 context window，而且每个问题都要重复支付读取整份资料的 token 成本。Map–Reduce 会先把报告切成块，让模型逐块总结，再汇总摘要；它能处理超长输入，但仍要扫描大部分甚至全部文档，并多出汇总调用。

RAG 把资料先建成可查询的知识库。每次问题到来时先取少量相关片段，再把这些片段连同问题交给生成模型。它减少了每次生成需要读取的内容，但正确性转移到了检索环节：如果相关证据没被找回，生成模型就无法凭空从这套资料中回答。

课堂 notebook 用 Tesla 10-K 中查找 2021 年 accounts receivable 净值作例子，对比全文输入、Map–Reduce 与检索少量片段。示范配置下，RAG 只把 top-4 片段交给生成模型，并报告相较前两种方式成本下降超过百倍。这个数字属于该报告、模型价格和 prompt 设置下的演示结果，不是所有 RAG 项目的固定倍率。

## 2. 先把文档变成可定位的 chunks

检索系统通常从一批文档开始。每份文档先抽取文本，再切成较小的 chunks；随后为每个 chunk 计算 embedding，把向量连同正文、ID 和来源信息写入索引。查询时再把问题转成向量，找出相似的 chunks。

Chunking 不只是按固定字数切开。课堂先以约 100 个词的块说明流程，再指出机械切分可能把一个句子、公式、表格或论证从中间截断。更好的边界通常会优先尊重段落、换行或句子；若相邻块之间没有重叠，恰好横跨边界的定义与解释可能被拆散。加入 overlap 可以保留局部上下文，但重叠太多又会制造大量近重复内容，挤占 top-K 名额。

因此 chunk size 与 overlap 是要根据文档类型和任务调节的参数。课堂提到约 200–500 tokens 是一个常见的经验范围，并用“约千字符”帮助估算；这不是统一最优值。tutorial 对一篇约两万字符的 Anthropic context-engineering 文章使用递归文本切分，按段落、换行等层次寻找边界，得到 29 个有重叠的 chunks。

切得太大时，chunk 同时含有很多不相关内容，embedding 的表示可能被稀释；切得太碎时，定义、前提和结论容易失去联系。所谓“合理 chunk”，本质是让一个检索单元能独立表达足够完整的意思，同时又不过度混入别的主题。

## 3. 两类检索：关键词匹配与向量语义相似

### 稀疏检索：词项本身就是线索

Exact/lexical retrieval 按查询词与文档词项的重合度排序。课堂用 TF-IDF 解释这个思路：某个词在当前 chunk 出现得越多，通常越能代表这个 chunk；但如果它在整个语料里到处都是，区分力就低。常见形式是以词频乘逆文档频率，再对 query 中的词汇总分数：

$$
\operatorname{score}(q,d)=\sum_{t\in q\cap d}\operatorname{tf}(t,d)\,\operatorname{idf}(t),
\qquad
\operatorname{idf}(t)\propto\log\frac{N}{\operatorname{df}(t)}.
$$

这里 $N$ 是文档或 chunks 数量，$\operatorname{df}(t)$ 是包含词项 $t$ 的单元数。具体系统会对词频和长度做不同的归一化；BM25 是更常见的改进形式。词项检索擅长产品名、代码符号、专有名词和精确短语，但用户换一种说法时，字面重合可能不足。

### 稠密检索：把句子映射到向量空间

Embedding model 把文本转换为高维向量。查询和候选 chunk 被编码后，可以用 cosine similarity、dot product 等度量比较方向或距离。若用户问“如何重置密码”，相关文档即使写“找回账号凭据”，也可能因为语义相近而被召回。

课堂把常见结构称作 bi-encoder / two-tower：一座塔编码 query，另一座塔编码文档。文档向量可以预先计算并存进向量库；查询到来时只需编码 query，再与库中向量搜索。它适合大规模第一阶段召回，但 query 与每个 chunk 没有在编码过程中逐 token 交互，分数只是相关性估计，不是深层推理结论。

课堂用简单的数学文本说明这个边界：embedding 有时会把 query 与包含相同数学表达式的文本排得很近，但不代表模型真的完成了积分或求导。长 chunk 中夹入大量噪声时，相关片段的相似度也可能下降。这既解释了 chunking 的作用，也提醒我们不能把 embedding similarity 当成语义理解或答案正确性的证明。

检索度量还要和 embedding 模型的训练/推荐配置一致。tutorial 的示范使用 Qwen3 系列 embedding（转写读作 “Q1,3”，所选配置输出 2560 维），并在 query 侧按模型要求加 instruction prefix；不加可能仍能运行，但效果会变差。课堂演示 cosine similarity 的计算方式为：

$$
\cos(q,d)=\frac{q^\top d}{\lVert q\rVert_2\lVert d\rVert_2}.
$$

## 4. 向量库、近似搜索与混合召回

小型向量库可以逐一计算 query 与所有文档向量的距离，取 top-K。这类 Flat/exact search 容易理解，结果是全库精确比较，但库越大，逐一比较的成本越高。ANN（Approximate Nearest Neighbor）索引用额外索引结构换取更快查询，代价是近似结果不一定等于精确最近邻。

课堂以 HNSW 为例：图中有多层节点，顶层稀疏、底层稠密。查询从稀疏层快速靠近目标区域，再逐层进入更细的邻居集合。建图需要额外时间和存储；线上检索速度较快，但返回的是近似近邻。若语料规模不大，Flat 的简单和精确可能更合适；是否换 ANN 应由数据规模、延迟预算和可接受的召回损失决定。

关键词检索与 dense retrieval 各有盲区。可以并行取回两路候选，再融合排名。直接相加 TF-IDF 分数和 cosine 分数通常不稳，因为它们量纲与分布不同。Reciprocal Rank Fusion（RRF）只使用名次：

$$
\operatorname{RRF}(d)=\sum_{m=1}^{M}\frac{1}{c+\operatorname{rank}_m(d)}.
$$

$\operatorname{rank}_m(d)$ 是文档 $d$ 在第 $m$ 路检索中的名次，$c$ 是平滑常数。某个候选只要在多路结果里都靠前，融合分就会上升；课堂示例用 60 作为常数，但仍需在具体任务上调整。融合不同名次而非原始分数，降低了分值尺度不一致的问题。

## 5. 查询改写、HyDE 与 Cross-Encoder 重排

### 查询不够明确时，先扩展召回机会

如果用户问得含糊，原始 query 可能缺少能命中文档的术语。课堂介绍两种轻量办法：

1. **HyDE**：让模型先生成一段假设性的答案或文档，再用这段文本做向量检索。假设文本不应直接当成可信答案；它只提供更丰富的检索表达，检索结果仍需回到真实资料核对。
2. **Multi-query**：把原问题改写成若干不同措辞的 $q_1,q_2,q_3$，分别检索，再对候选去重和融合。不同说法有机会召回不同片段，但会增加模型调用和检索成本。

### 用 Cross-Encoder 对候选重新打分

Bi-encoder 的优点是文档向量能预计算；缺点是 query 与 chunk 分开编码。Cross-Encoder 则把 query 和单个候选 chunk 拼在一起送进另一个编码器，让两者的 token 在模型内部交互，直接输出相关性分数。它更有机会识别细粒度匹配，但每个候选都要单独计算，不能像 bi-encoder 一样把文档侧完全预计算。

因此常见流程是先用快速检索扩大候选池到 top-N，再让 cross-encoder 逐个评分，最后选 top-K。课堂建议 N 可以取最终 K 的约两到三倍作为起点；这只是讲解中的调参建议。候选池过小会漏掉正确片段，过大则增加重排延迟。

## 6. Agentic RAG：把检索配置交给 Planner

传统 RAG 往往提前固定“何时检索、查哪个库、取多少条、用什么相似度、是否重写 query、是否重排”。Agentic RAG 把一部分选择交给一个 planner：根据用户问题和当前已知信息，决定是否检索、何时检索、使用哪些知识库、如何改写 query、采用什么参数，以及如何汇集多路结果。

这使检索策略更能随任务变化，也新增了一个决策模型及其调用成本。Planner 选错库或错误地认为自己已有足够信息，仍会造成漏检；所以 agentic 并不自动意味着更准。课堂把“何时检索、去哪里检索、检索参数、是否改写/重排”列为需要显式考虑的决策，而不是让一个固定 top-K 参数承担所有场景。

## 7. 怎么评价检索：Precision 与 Recall

假设系统为一个 query 取回 $K$ 个 chunks，其中 $R_K$ 个被标为相关；全部相关 chunks 的真值数为 $G$。

$$
\operatorname{Precision@K}=\frac{R_K}{K},\qquad
\operatorname{Recall@K}=\frac{R_K}{G}.
$$

Precision 衡量返回结果里有多少有用，Recall 衡量所有已知相关证据中有多少被取回来。调高 K 常能增加召回机会，但也可能把更多无关内容塞给生成模型、拉低 Precision 并增加 token 成本。要在两者之间取舍，必须明确查询需要哪些证据。

课堂用“谁创办了 Alibaba”作例子，把答案拆成事实，再检查哪些 chunk 支持每个事实。这个例子也暴露出标注边界的重要性：若原问题只问创办者，却把“Jack Ma 住在 Shanghai”也塞入 ground truth，相关事实和相关 chunk 的集合都会改变，Recall 便会下降。评测集必须把 query、答案事实和相关证据定义在同一范围内；否则指标反映的可能是标注口径，而非检索器本身。

Precision/Recall 评价的是检索证据，不等于生成答案正确率。若要声称整个 RAG 系统答得好，还需要另行检查回答是否正确、是否受到取回证据支持；这些不是今天这组检索指标本身所能替代的。

## 8. Tutorial：把一条 RAG 链路跑通并追踪错误

后半段 notebook 用 LangChain 组装一条简单链路。课堂示范的组件包括：递归文本切分、Qwen3 embedding、Milvus 向量库、cosine 距离、Flat 索引和生成模型；Langfuse 用来记录每个组件的输入、输出和运行时间。讲解中还提到 DeepSeek 与 OpenRouter 的 API 配置，embedding query 需要加模型指令前缀。

对约两万字符的 Anthropic context-engineering 文本，切分器产生 29 个带 overlap 的 chunks；向量写入 Milvus 后，示例 retriever 取 top-3，再将正文格式化进 prompt，要求生成模型依据给定 context 回答。`retriever` 只返回候选文档，不负责生成答案；把 retrieval、文档格式化与 generation 接成链之后，才得到端到端问答。

调试环节中，最终回答说提供的 context 没有答案。Langfuse trace 显示 retriever 实际找到了相关文档；问题在下游组装 context 时读错字段，把描述信息而不是文档正文放进 prompt。修正为正确的 page content 后，链路恢复正常。这个排查顺序很实用：先沿 trace 检查每一层的输入输出，确认错误发生在哪个组件，再动对应的部分；最终回答错，不等于 retriever 一定错。

![RAG 的组件流：文档切分、embedding、向量索引、召回与生成](/blog/2026/rag-end-to-end.png)

课堂收尾把 advanced RAG techniques 留作后续阅读，没有在这份 tutorial 里逐项展开。今天完成的部分覆盖了从文档预处理到向量检索、重排、Agent 决策、离线检索指标与 trace 调试的主干；不同数据、embedding 模型和 query 分布下的 chunk size、K、ANN 参数、RRF 常数与重排深度仍需实测。
