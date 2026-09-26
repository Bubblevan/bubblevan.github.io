---
schema: bubblevan/v1
id: project-health-copilot-03-agent-llm-bagua
content_kind: project
title: Agent / LLM 通用八股：跨项目基础概念
linkTitle: 05 · 通用八股
weight: 50
date: 2026-09-19
updated: 2026-09-27
status: draft
visibility: public
projects:
  - project-health-copilot
summary: 与具体项目实现解耦的 Agent、RAG、LLM、推理、分布式训练、RL 和 Eval 基础概念、公式与常见追问。
topics:
  - agent
  - llm
  - rag
  - post-training
  - interview
---

本文只讲跨项目可复用的概念、核心公式、trade-off 与失败模式，不描述任何特定项目已经实现了什么。项目事实与面试追问分别见 [RAG](/projects/health-copilot/01-rag项目面试追问/)、[Memory](/projects/health-copilot/02-memory项目面试追问/)、[Multi-Agent](/projects/health-copilot/03-multi-agent项目面试追问/) 和 [RL 项目边界](/projects/health-copilot/04-rl项目面试追问/) 页面。

## 先用这套答题模板

面对一个八股问题，先用 20～30 秒给定义，再按四步展开：

1. 它解决什么问题？
2. 最小原理或公式是什么？
3. 代价、边界和失败模式是什么？
4. 如果落到项目，源码或 eval 怎么证明？

不要只背“用了某个名词”。面试官真正想知道的是：为什么需要它，如何验证它，失败时怎么停。

## A. Agent Runtime

### 面试官：Agent 和 Workflow 有什么区别？

**短答**：Workflow 的主要控制流由代码预先决定；Agent 在显式状态、工具和 policy 约束下，让模型选择下一步。两者都可以调用 LLM，所以“用了 LLM”不等于“是 Agent”。

**原理**：固定的 `validate → retrieve → generate → verify` 是 workflow。Agent 多了一个 decision step：读取 state 和 observation，提出 action，runtime 校验并执行，再把结果写回 state。

**trade-off**：Agent 更灵活，但 action space、成本、延迟、非确定性和评测难度更高；workflow 更容易缓存、测试和复现，但未编码的路径会僵硬。

**常见追问**：什么程度的模型选择才算自主？谁拥有最终终止权？一个系统可以把确定性 workflow 与局部 Agent decision 组合起来，不必给整个系统贴单一标签。

### 面试官：ReAct 是什么？

**短答**：ReAct 把 reasoning/action/observation 交替起来：模型根据当前观察选择工具，拿到结果后再决定下一步，直到完成或停止。

**原理**：抽象循环是 `state → thought/decision → action → observation → state`。工程实现里不应依赖模型输出的自由文本解析，action 应落到结构化 tool call，observation 应有明确 schema。

**trade-off**：它能处理未预先写死的路径，但会增加循环、工具错误、prompt injection、成本和不可复现性。先做 bounded action 往往比直接开放长循环容易验证。

**常见追问**：ReAct 和 chain-of-thought 是否一回事？如何隐藏 reasoning 又保留可观测性？参考 [ReAct 原论文](https://arxiv.org/abs/2210.03629)。

### 面试官：tool calling / function calling 到底是什么？

**短答**：模型不直接执行函数，而是返回工具名和结构化参数；宿主 runtime 验证、执行工具，再把结构化结果放回下一轮上下文。权限和副作用始终属于 runtime。

**原理**：一个工具至少需要 `name`、`description`、`input schema` 和返回协议。调用 ID 用来把 assistant tool call 与 tool result 配对；结果必须区分成功数据和错误。

**trade-off**：结构化调用比解析 prose 稳定，但 schema 设计、版本兼容、异常、重试和权限都需要维护。JSON valid 也不代表参数合理，更不代表结果可信。

**常见追问**：未知工具怎么办？工具异常是终止还是 observation？参考 [OpenAI function calling 文档](https://developers.openai.com/api/docs/guides/function-calling) 和 [Anthropic tool use 文档](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)。

### 面试官：Agent State、Context、Session、Memory 怎么区分？

**短答**：State 是当前执行的结构化状态；context 是某一轮提供给模型的输入材料；session 是一次对话或运行的边界；memory 是跨 turn、跨 session 保存并可再次使用的信息。

**原理**：不要把所有历史都塞进 context。state 适合计数器、stop reason 和当前 plan；transcript 适合消息协议；memory 需要生命周期、写入策略、检索、删除和隐私边界。

**trade-off**：更多 memory 可以减少重复询问，但增加陈旧信息、隐私泄漏和错误召回风险；短 context 更可控，但可能丢失任务所需信息。

**常见追问**：如何区分 session 和 memory？检查生命周期、写入策略、更新/删除语义，以及是否会跨 session 被检索复用。

### 面试官：message protocol、tool schema、Tool Registry 为什么需要显式化？

**短答**：它们把隐式约定变成可验证边界：message protocol 规定消息类型，tool schema 规定参数，registry 规定允许的 capability 和执行入口。

**原理**：结构化协议至少要处理 assistant final、assistant tool call、tool result、错误和调用 ID。registry 还可以做重复名字拒绝、schema 暴露、权限过滤和版本迁移。

**数量级**：随着消息类型、工具数和 schema 版本增加，隐式组合的测试面会迅速扩大；显式 contract 能把变化收敛到边界。

**trade-off**：前期设计和迁移成本更高，但能减少 prose parsing、名字猜测和跨服务耦合。

**常见追问**：tool result 是否天然可信？如何防工具被模型越权调用？

### 面试官：串行和并行 tool calls 如何选择？

**短答**：独立、只读、没有顺序依赖的查询适合并行；有状态依赖、写操作或需要上一结果决定下一步时应串行。

**原理**：并行减少 wall-clock latency，近似是 `max(latency_i)` 加聚合开销；串行通常接近 `Σ latency_i`，但 observation 更容易解释。并行写操作需要幂等键、冲突处理和提交顺序。

**trade-off**：并行提高吞吐，却扩大瞬时负载、错误聚合和权限面。先限制为串行通常更适合安全敏感原型。

**常见追问**：一个响应中有多个 tool calls 是不是已经支持并行？不是，是否执行要由 runtime 明确决定。

### 面试官：idempotency、timeout、retry 怎么设计？

**短答**：幂等性保证同一个逻辑操作重试不会重复副作用；timeout 限制单次等待；retry 只能在错误可重试且剩余预算允许时使用。

**原理**：为写操作生成稳定 idempotency key，在服务端去重；把错误分为参数错误、业务拒绝、瞬时网络错误和未知错误；超时后不能假设服务端没有执行。

**trade-off**：retry 可以提升瞬时成功率，但会放大成本、延迟和副作用；指数退避、最大重试次数和总 deadline 要同时存在。只读检索比扣款、发消息更容易重试，但也可能造成重复负载。

**常见追问**：tool 返回 timeout 时如何告诉模型？如果结果未知，应该 abstain 还是补偿查询？

### 面试官：Agent Loop 怎么终止？

**短答**：至少要有显式 final、硬 step/tool/token/time budget、错误终止和 cancellation；预算耗尽时要有安全的 fallback，不能把半成品当答案。

**原理**：可以写成 `while status == RUNNING and steps < max_steps`，每次 action 前再检查权限和剩余预算。还应防同名工具重复调用、相同参数重复调用和无进展状态。

**trade-off**：预算太小会误拒答，太大则提高循环、成本和风险。hard guard 保证终止，但不保证 action 有意义。

**常见追问**：如何定义 progress signal？工具失败算一步吗？预算至少应覆盖 model turn、tool execution、token、deadline 和重复无进展动作，并在执行副作用前校验。

### 面试官：Context Engineering 和 Prompt Engineering 有什么差别？

**短答**：Prompt engineering 主要优化指令文字；context engineering 还负责把正确的状态、工具 schema、证据、历史、权限和输出约束在正确时间装进 context。

**原理**：context 有容量和噪声预算。应明确哪些信息是 source of truth，哪些是 observation，哪些是 instruction；工具结果不能自动获得指令权。

**trade-off**：更多 context 可能提高信息覆盖，却增加 token 成本、冲突和 prompt injection 面；摘要能省 token，但可能丢失约束或 provenance。

**常见追问**：如何做 context compaction？如何保证 evidence 不被后来的用户文本覆盖？

### 面试官：Agent Skills 是什么？和普通工具有什么区别？

**短答**：Skill 通常是一组面向任务的工作方法、资源和约束；tool 是 runtime 可以调用的具体 capability。skill 可以指导何时、怎样使用多个工具，但不应绕过权限。

**原理**：一个 skill 可包含 instruction、模板、脚本或检查清单；工具调用仍必须经过 registry、schema 和 policy。把 skill 当成“可执行代码”时，需要同样的版本、权限和供应链审计。

**trade-off**：skill 提高复用性，但会扩大 context、版本依赖和 prompt 注入风险。

**常见追问**：skill 是否等于 plugin？谁能安装和更新 skill？还要明确 skill 如何被版本化、信任、审计，以及它能否请求未授权 capability。

### 面试官：MCP 是什么？

**短答**：MCP 是一种让模型应用以标准化协议连接外部 server capability 的协议；它定义工具等能力如何发现、描述和调用，但不自动赋予安全权限。

**原理**：MCP 的 tools 规范描述工具列表、输入 schema、调用结果和错误。实际系统仍需要 server 认证、用户授权、工具 allowlist、超时、审计和数据边界。

**trade-off**：标准协议减少每个 provider 的 bespoke adapter，但引入 server 供应链、远程信任、schema 演化和权限治理问题。

**常见追问**：MCP tool 与本地 function call 的差别？如何做 capability security？参考 [MCP tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)。协议标准化发现/调用，不等于授权或安全审查。

### 面试官：Harness Engineering 是什么？

**短答**：它不是一个单独算法，而是围绕 Agent 建立可执行边界和反馈回路：context、工具、权限、预算、状态、终止、验证、trace、replay 和 eval。

**原理**：prompt 告诉模型“应该做什么”，harness 还要在 runtime 验证“能不能做、做了几次、结果能不能被接受”。关键 invariant 必须落到代码和测试，不只写在 prompt。

**trade-off**：harness 增加工程成本，但能把不可控行为变成可观察、可回归、可停止的行为。

**常见追问**：harness 和 workflow 会不会矛盾？不会；harness 可以承载固定 workflow、局部 Agent decision、policy gate 和 verification。

### 面试官：sandbox、permission、capability security 为什么是 Agent 的一等问题？

**短答**：因为 Agent 可能通过工具影响文件、网络、数据库或现实业务。sandbox 限制执行环境，permission 决定主体能否做某事，capability security 则只把必要能力的引用交给主体，并在执行点再次校验。

**原理**：最小权限、deny-by-default、资源范围、用户授权和审计要组合使用。不能只靠工具描述中的“请勿删除文件”；runtime 应拒绝超出 capability 的参数。

**trade-off**：限制越强，任务成功率可能下降；权限越宽，误操作和 prompt injection 的 blast radius 越大。

**常见追问**：read-only tool 是否没有风险？没有，仍有数据泄露、成本、侧信道和错误召回风险；最小权限、allowlist 和执行时验证仍然必要。

### 面试官：trace、replay、evaluation 为什么重要？

**短答**：只看最终答案无法解释 Agent 在哪一步错。trace 保存 state、action、tool result、耗时和 policy decision；replay 用固定版本重放；eval 把轨迹转成可比较的回归指标。

**原理**：trace 要有 run ID、版本、模型、prompt/config hash、tool call ID、错误和终止原因，并处理 PII 脱敏。replay 要标记哪些外部依赖被固定、哪些仍是 live。

**trade-off**：信息越完整，调试越好，但隐私、存储和泄漏风险越大。Trace/replay 还需要绑代码、模型、prompt/config、工具结果和外部状态身份。

**常见追问**：如何保证 replay 与原运行一致？如何防 trace 把用户隐私写进日志？

## B. RAG / Retrieval

### 面试官：RAG 解决什么问题？

**短答**：RAG 在生成前检索外部或非参数知识，把相关内容放进 context，以支持知识更新、来源追溯和领域资料注入。

**原理**：典型链路是 `query → retrieve → select/rerank → context → generate → verify`。检索 recall 是回答上限之一，但检索到内容不代表它支持具体 claim。

**trade-off**：RAG 比重新训练更容易更新知识，却引入 chunking、检索、来源冲突、上下文长度和 grounding 问题。

**常见追问**：RAG 和 fine-tuning 的边界？为什么需要 abstain？参考 [RAG 原论文](https://arxiv.org/abs/2005.11401)。RAG 通常改变 inference-time context；fine-tuning 更新模型参数，二者可以组合但不能互相替代。

### 面试官：sparse 和 dense retrieval 怎么选？

**短答**：sparse 用离散词项和倒排结构，解释性强、术语和精确匹配好；dense 用 embedding 把 query/document 映射到向量空间，能覆盖词面不同的语义近邻。

**原理**：sparse 通常依靠 TF/IDF 类信号；dense 常用 bi-encoder 预编码文档，再以 cosine、inner product 或 L2 检索。两者的训练数据、索引版本和阈值都会影响结果。

**trade-off**：sparse 便宜可解释但同义改写弱；dense 语义覆盖强但有 embedding/domain drift、OOD 误召回和解释性问题。hybrid 可以互补，但要做融合和消融。

**常见追问**：为什么不总是 dense？为什么 dense 仍会误召回？要按术语精确匹配、语义改写、索引成本、领域迁移和负例分析选择，而不是把 dense 当成默认优胜者。

### 面试官：BM25、TF、DF、IDF 怎么讲？

**短答**：TF 是 term 在当前文档出现的次数，DF 是包含该 term 的文档数，IDF 让稀有 term 更有区分度；BM25 再加入 TF saturation 和文档长度归一化。

**公式**：

```text
BM25(D,Q) = Σ IDF(t) · tf(t,D)(k1+1)
             / [tf(t,D) + k1(1-b+b|D|/avgdl)]
IDF(t) = log((N-df(t)+0.5)/(df(t)+0.5)+1)
```

**trade-off**：k1、b、分词、分析器和字段权重会改变 ranking；BM25 score 是检索打分，不是相关概率，不能直接跨 query 当置信度。

**常见追问**：为什么中文 tokenizer 会改变 BM25？为什么高分仍不等于 evidence sufficiency？

### 面试官：embedding、bi-encoder、cross-encoder 分别是什么？

**短答**：embedding 把文本变成向量；bi-encoder 分别编码 query 和 document，适合离线建库和大规模召回；cross-encoder 把 query-document 拼起来共同编码，适合对候选对做精细 rerank。

**数量级**：bi-encoder 的文档向量可预计算，检索成本接近向量近邻查询；cross-encoder 要对每个候选做一次联合前向，若候选数为 K，在线开销近似随 K 增长。

**trade-off**：bi-encoder 快但表示交互弱；cross-encoder 准但慢。常见两阶段是 dense/sparse recall → cross-encoder rerank。

**常见追问**：如何避免 reranker 把不支持 claim 的相似文档推高？reranker 只估 query-document relevance，生成回答前仍需 evidence sufficiency、claim support 和 answerability policy。

### 面试官：cosine、inner product、L2 有什么区别？

**短答**：cosine 比较方向，`x·y/(||x||||y||)`；inner product 同时受方向和向量范数影响；L2 是距离，越小越近。若向量都做单位化，最大化 inner product 等价于最大化 cosine，也等价于最小化平方 L2。

**trade-off**：是否 normalize 会改变排名和索引配置；模型训练时使用的相似度应和线上 index 一致。

**常见追问**：为什么同一个模型换 metric 结果会变？如何选择 threshold？不能脱离 embedding 训练目标和验证集回答。

### 面试官：HNSW 和 IVF 是什么？

**短答**：HNSW 用分层小世界图做近似近邻；IVF 先把向量分到 coarse clusters，查询时只搜索部分倒排列表。

**原理**：HNSW 的 `M`、`efConstruction`、`efSearch` 控制图连接和搜索宽度；IVF 的 cluster 数和 probe 数控制召回/速度折中，常与 PQ 压缩配合。

**trade-off**：搜索更快但不是精确 top-K；提高召回通常要多搜节点/cluster，增加延迟和内存。索引构建版本、删除更新和冷热数据也要考虑。

**常见追问**：小知识库为什么不用 ANN？小 corpus 上 exact search 更简单且无近似召回损失；规模、延迟和内存到达阈值后再评估 HNSW/IVF。

### 面试官：hybrid search 和 RRF 怎么讲？

**短答**：hybrid 把 sparse 与 dense 的候选或分数融合；RRF 不直接比较不同检索器的原始分数，而按名次给贡献，例如 `RRF(d)=Σ 1/(k+rank_i(d))`。

**trade-off**：RRF 对分数校准要求较低，适合不同 ranker；但融合参数和候选截断仍会影响结果，且互补假设需要 ablation 验证。

**常见追问**：为什么 hybrid 不一定更好？如果 dense 给 OOD 高相似度，融合可能把错误候选推上来；要同时报告 relevance、OOD 和 grounding。

### 面试官：reranker 为什么放在召回之后？

**短答**：召回阶段追求高 recall 和低延迟，reranker 在较小候选集上追求更精细的 query-document 相关性；把昂贵的 cross-encoder 对全库运行通常不划算。

**原理**：先取较大的 top-N，再重排为 top-K。N 太小会让 reranker 无法找回漏召回的文档；N 太大增加 latency 和成本。

**trade-off**：reranker 可能改善排序，但不能创造候选中不存在的证据，也不能自动完成 claim-level verification。

**常见追问**：如何评估 reranker？固定 recall stage，比较 nDCG/MRR、slice recall、latency 和 OOD。

### 面试官：Chunking 为什么重要？

**短答**：chunk 决定检索的粒度、上下文噪声和 citation 颗粒度。太大容易把无关内容一起召回，太小会丢失条件、例外和上下文。

**原理**：要尽量在一个 chunk 里保留完整 claim、限制条件和来源 metadata；overlap 可能减少边界丢失，但会增加索引重复和相似 chunk。

**trade-off**：固定 token chunk 简单，按标题/段落/语义切分更贴近文档结构却更复杂；医学资料的阈值、适用人群和例外不能随意跨 chunk 拼接。

**常见追问**：如何判断 chunk 是否过大？看 recall、context token、duplicate rate、grounding 和人工 bad case。

### 面试官：Recall@K、Hit@K、MRR、nDCG 怎么比较？

**短答**：Hit@K 只看 top-K 是否至少命中；Recall@K 看找回全部相关项的比例；MRR 关注第一个相关项的位置；nDCG 适合 graded relevance 和多个相关项。

**公式**：

```text
Recall@K = |retrieved_K ∩ relevant| / |relevant|
RR = 1 / rank(first relevant)
DCG@K = Σ (2^rel_i - 1) / log2(i+1)
nDCG@K = DCG@K / ideal_DCG@K
```

**trade-off**：指标回答的问题不同，不能用一个指标代替全部；分母、多个 gold source 和 relevance grade 必须公开。

**常见追问**：只有一个 gold source 时，Hit@K 是否比 Recall@K 更有解释力？当 qrels 有多个 graded relevant documents 时，为什么还要看 Recall 和 nDCG？答案取决于标注结构和任务目标，不能只因为某个指标看起来更高就换 headline。

### 面试官：grounding、hallucination、abstention 怎么区分？

**短答**：grounding 是回答 claim 被给定 evidence 支持；hallucination 是回答包含来源不支持或虚构的内容；abstention 是系统在证据/安全条件不足时不回答或转人工。

**原理**：合法 citation ID 只说明 source 被观察到，不等于 claim entailment。可以逐 claim 检查 source span、关系方向、数值和条件。

**trade-off**：严格 abstain 降低 unsupported answer，却可能提高 false abstain；需要按风险、coverage 和 calibration 评估 selective answering。

**常见追问**：检索高分或 citation ID 合法能否当 grounding？不能。检索相关性、来源合法性、claim 被证据蕴含是不同层次的判断。

## C. LLM 推理与模型结构

> 本节介绍通用组件原理；是否适合某个项目，仍需由它的真实实现与实验协议决定。

### 面试官：Transformer 的 self-attention 在做什么？

**短答**：每个 token 用 query 去和所有 key 计算相关性，再对 value 加权汇总，让当前位置能动态读取上下文。

**公式**：

```text
Attention(Q,K,V) = softmax(QK^T / √d_k)V
```

**数量级**：长度为 L 时，标准 self-attention 的 token-to-token 交互和 attention matrix 约为 `O(L²)`；MLP 和投影另有成本。

**trade-off**：全局依赖强但长上下文昂贵；分块、稀疏 attention、KV cache 和更高效 kernel 都是在不同维度做折中。

**常见追问**：prefill 和 decode 有什么区别？GQA/MQA 怎么影响 KV cache？参考 [Attention Is All You Need](https://arxiv.org/abs/1706.03762)。

### 面试官：为什么需要 KV Cache？

**短答**：自回归 decode 每生成一个 token，都需要用历史 token 的 key/value；把已经算过的 K/V 缓存起来，就不必每步重新计算历史部分。

**数量级**：每层 cache 元素近似 `2 × batch × sequence_length × n_kv_heads × head_dim`；乘层数和每元素 bytes 才是显存量。MHA、GQA、MQA 的差别主要在 `n_kv_heads`。

**trade-off**：cache 降低重复计算、提高 decode 速度，但显存随并发和上下文长度增长；长上下文、多轮 Agent 和 beam/branch 会放大占用。

**常见追问**：prefill 阶段也需要 cache 吗？需要建立；为什么 paged KV cache 有用？它改善内存碎片和动态请求管理。

### 面试官：MHA、MQA、GQA 有什么区别？

**短答**：MHA 每个 query head 有独立 K/V head；MQA 让所有 query heads 共享一组 K/V；GQA 把 query heads 分成组，每组共享一个 K/V head。

**原理**：若 query head 数为 `h_q`，KV head 数为 `h_kv`，MHA 是 `h_kv=h_q`，MQA 是 `h_kv=1`，GQA 介于二者之间。

**trade-off**：减少 KV heads 可以近似按 `h_kv/h_q` 降低 KV cache 和带宽，但共享过多可能损失表示能力。它主要优化 inference memory/bandwidth，不等于减少所有 attention FLOPs。

**常见追问**：为什么 GQA 常是工程折中？它保留多头 query 的表达力，同时比 MHA 更省 KV cache。

### 面试官：RoPE 解决什么问题？

**短答**：Rotary Position Embedding 把位置信息通过旋转作用到 Q/K 上，使 attention 分数带有相对位置信息，同时不需要单独加位置向量。

**原理**：对每个二维维度对按位置角度旋转；Q/K 的内积会随位置差变化。长上下文扩展通常需要处理频率、缩放和训练/推理长度外推。

**trade-off**：实现简单且适合 decoder-only Transformer，但外推到训练长度之外并不免费，频率缩放策略可能影响近距离和远距离能力。

**常见追问**：RoPE 只作用于 Q/K 还是 V？通常作用于 Q/K；不同模型的 scaling 方案不能混为一谈。

### 面试官：RMSNorm、LayerNorm、Pre-Norm、Post-Norm 怎么比较？

**短答**：LayerNorm 对均值和方差做归一化；RMSNorm 只按均方根缩放，不减均值。Pre-Norm 把 norm 放在子层之前，Post-Norm 放在残差之后。

**公式**：RMSNorm 可简写为 `x / sqrt(mean(x²)+ε) · g`。

**trade-off**：RMSNorm 计算更简洁；Pre-Norm 通常更利于深层训练稳定和梯度传播，Post-Norm 的表示路径不同、初始化和学习率更敏感。具体效果依赖架构和训练配方。

**常见追问**：为什么不能只说 Pre-Norm 一定更好？因为稳定性、最终质量和深度/初始化有关，需要实验。

### 面试官：SwiGLU 是什么？

**短答**：SwiGLU 是带门控的 MLP 变体，用 SiLU 激活的一条分支门控另一条线性分支，表达能力通常比普通 ReLU/GELU FFN 更强，但参数和计算布局要重新配平。

**简式**：`SwiGLU(x) = (SiLU(xW_g) ⊙ xW_u)W_d`。

**trade-off**：门控增加投影和实现复杂度，但能提供更灵活的 feature selection；hidden dimension 通常需要调整，不能只照搬普通 FFN 的宽度。

**常见追问**：SwiGLU 是否等于 MoE？不是，SwiGLU 是单个 token 内的门控 MLP，MoE 是在多个 expert 之间路由。

### 面试官：MoE 的基本原理是什么？

**短答**：MoE 用多个 expert 子网络和一个 router，对每个 token 选择 top-k expert；总参数可以增大，但每个 token 只激活一部分参数。

**原理**：router 产生 expert scores，按 capacity 和 load balancing 规则分配 token；输出通常是选中 expert 输出的加权和。

**trade-off**：参数容量和计算量可以解耦，但带来通信、负载不均、capacity overflow、路由不稳定和训练/推理系统复杂度。稀疏不等于免费。

**常见追问**：为什么 RL 训练 MoE 更难？路由变化会放大 off-policy likelihood 和负载波动；GSPO 论文讨论了它的一个训练场景。

## D. Serving / 推理系统

### 面试官：prefill、decode、TTFT、TPOT、throughput、latency 怎么讲？

**短答**：prefill 一次处理输入 prompt，通常计算密集；decode 逐 token 生成，通常受 memory bandwidth 和 KV cache 影响。TTFT 是首 token 时间，TPOT 是每输出 token 时间，throughput 是单位时间完成的 token/request 数，latency 是单请求端到端耗时。

**数量级**：Agent 两次模型调用时，端到端 latency 近似包含两次 TTFT、两段 decode、工具耗时和序列化/排队；不能只报单次 token speed。

**trade-off**：continuous batching 提高吞吐，但可能增加单请求 tail latency；低 P99 和高 GPU 利用率常需平衡。

**常见追问**：为什么短 prompt 也可能 TTFT 高？排队、冷启动、provider network 和 prefill kernel 都可能主导。

### 面试官：prefix caching 解决什么？

**短答**：对多个请求共享的 prompt 前缀复用已计算的 KV，减少重复 prefill；适合长 system prompt、固定工具 schema 或多轮共享前缀。

**原理**：只有 token-identical 且缓存语义安全的 prefix 才能复用；动态用户内容、权限和工具列表变化会截断共享前缀。

**trade-off**：降低 TTFT 和 prefill FLOPs，但占用显存/内存，带来 eviction、租户隔离、缓存污染和隐私风险。

**常见追问**：Agent tool result 能否无条件缓存？不能，必须把用户权限、版本和敏感数据边界纳入 cache key。

### 面试官：PagedAttention / vLLM 解决什么？

**短答**：PagedAttention 把 KV cache 按固定 block 管理，让动态请求可以像虚拟内存一样分配/回收，减少连续内存要求和碎片，提高并发 serving 的利用率。

**原理**：逻辑 sequence 的 KV blocks 映射到不连续物理 blocks，attention kernel 按 block 读取；共享 prefix 时还可以共享物理 blocks，写时再复制。

**trade-off**：需要专门 kernel、调度和 block 管理；优化的是 serving memory/throughput，不等于模型质量或安全性。

**常见追问**：PagedAttention 是否改变 Transformer 数学结果？目标是更高效地管理 cache，数值细节仍受 kernel/precision 影响。参考 [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180)。

### 面试官：量化是什么？GPTQ、AWQ、KV cache quantization 怎么区分？

**短答**：量化用更低 bit 表示权重、激活或 KV cache，以降低显存和带宽；GPTQ/AWQ 常指权重量化方法，KV cache quantization 则压缩运行时缓存。

**原理**：线性量化可写成 `x ≈ scale · (q-zero_point)`；实际要处理 per-tensor/per-channel、校准数据、异常值和 dequant kernel。

**trade-off**：低 bit 省内存、可能提高吞吐，但会带来精度损失、长上下文误差积累、kernel 限制和模型/硬件依赖。

**常见追问**：为什么量化不能只看 perplexity？还要看目标 task、长上下文、tool calling、拒答和 tail latency。

## E. 分布式训练与并行

### 面试官：DP、TP、PP、CP、SP 分别是什么？

**短答**：DP 复制模型并切 batch；TP 把层内矩阵/attention 切到多卡；PP 把不同层放到不同 stage；CP 沿 context/sequence 维切长序列；SP 通常指把 sequence 相关计算和通信切分以降低激活或同步压力，具体语义要看框架。

**trade-off**：DP 易扩展但需梯度同步；TP 通信频繁；PP 有 pipeline bubble；CP/SP 适合长上下文但通信和实现更复杂。并行维度可以组合，但拓扑、batch 和 microbatch 要一起设计。

**常见追问**：为什么不能只说“多卡就是 TP”？因为不同并行切分解决不同内存和计算瓶颈。

### 面试官：FSDP 和 ZeRO 在解决什么问题？

**短答**：两者都通过切分训练状态降低单卡内存：参数、梯度、optimizer states 不必完整复制在每张卡上。FSDP 是 PyTorch 的 fully sharded data parallel 实现；ZeRO 是分阶段的 optimizer/gradient/parameter partitioning 思路。

**数量级**：Adam 类训练状态常包含参数、梯度和两份一阶/二阶 moment，混合精度还可能有 master weights；sharding 可以把这些状态按 world size 分摊，但通信和重建仍存在。

**trade-off**：更省显存，代价是 all-gather/reduce-scatter、通信、checkpoint 和调试复杂度；不是“免费把模型放大 N 倍”。

**常见追问**：FSDP 与 TP 是互斥的吗？不一定，可以组合；要说明训练阶段、参数切分和硬件拓扑。参考 [PyTorch FSDP 文档](https://docs.pytorch.org/docs/stable/fsdp.html) 和 [ZeRO 论文](https://arxiv.org/abs/1910.02054)。

## F. 后训练与 RL

### 面试官：SFT、DPO、RL 有什么区别？

**短答**：SFT 用示范答案做 maximum likelihood；DPO 直接用 chosen/rejected preference pair 优化相对偏好，不需要在线 rollout 的显式 RL loop；RL 则通过 policy 与 reward 交互更新，通常有 rollout、reward、advantage 和 policy update。

**原理**：SFT 常优化 `-log πθ(y|x)`；DPO 把 reference policy 纳入偏好比值；RL 需要处理 on/off-policy、credit assignment、KL 和 reward hacking。

**trade-off**：SFT 稳定简单但受示范覆盖限制；DPO 工程负担较低但依赖偏好数据质量；RL 可优化可验证或长期目标，却更容易不稳定、过拟合 reward 和崩溃。

**常见追问**：什么时候 DPO 比 PPO 合适？取决于偏好数据是否充足、是否需要在线探索/环境交互、reward 能否直接验证以及训练成本约束。

### 面试官：PPO 在 LLM 后训练里做什么？

**短答**：PPO 用旧 policy 采样的 response，在新旧 policy 的比率上做 clipping，限制单次更新不要离旧 policy 太远；通常还配合 value model、advantage 和 KL regularization。

**公式**：

```text
r_t(θ) = π_θ(a_t|s_t) / π_old(a_t|s_t)
L = min(r_t A_t, clip(r_t, 1-ε, 1+ε) A_t)
```

**trade-off**：clipping 提高稳定性，但会丢掉过度 off-policy 样本；value model、rollout、reference policy 和 KL 都增加显存与工程复杂度。

**常见追问**：为什么 LLM 的 token-level PPO 可能有长序列方差？每个 token 的 ratio、credit assignment 和 reward 粒度不一定匹配。参考 [PPO 原论文](https://arxiv.org/abs/1707.06347)。

### 面试官：GRPO 是什么？

**短答**：GRPO 用同一 query 生成一组 responses，以组内 reward 的均值/标准差计算相对 advantage，从而省去显式 value model；常见实现仍在 token level 使用 importance ratio 和 clipping。

**简式**：

```text
A_i = (r_i - mean(r_group)) / std(r_group)
```

**trade-off**：省 value model 的内存和训练成本，但需要 group rollouts；token-level ratio 在长序列、MoE 或 off-policy 条件下可能有高方差和不稳定。

**常见追问**：group size 怎么影响方差？reward 全相同怎么办？需要处理 std 接近 0 和样本利用率。

### 面试官：GSPO 的重要性比率到底是什么？

**短答**：GSPO 把 reward、clipping 和优化粒度放在 response sequence 层面。它不是简单写一个未归一化的 `exp(logπθ - logπold)`，而是使用 length-normalized sequence-level importance ratio：

```text
s_i(θ) = [π_θ(y_i|x) / π_old(y_i|x)]^(1/|y_i|)
       = exp((1/|y_i|) · Σ_t log[π_θ(y_i,t|x,y_i,<t)
                                   / π_old(y_i,t|x,y_i,<t)])
```

随后 sequence-level objective 对整个 response 使用 `min(s_i A_i, clip(s_i, 1-ε, 1+ε) A_i)`；一个 response 的 token 共享 sequence ratio，clipping 也按 response 发生。

**原理**：序列 likelihood 是 token likelihood 的乘积；长度归一化相当于对 log ratio 做平均，减少长度导致的数值尺度差异和方差。它把优化单元和 sequence-level reward 对齐。

**trade-off**：sequence-level credit assignment 更粗，一个 response 内 token 不再用各自的 ratio；更稳定不等于在所有任务、长度和 reward 上都更好，clip range 也和 GRPO 的典型量级不同。

**常见追问**：GSPO 与 GSPO-token 一样吗？论文还定义了 GSPO-token 变体；不能把二者和标准 token-level GRPO 混为一谈。参考 [GSPO 原论文的公式 (5)–(7)](https://arxiv.org/abs/2507.18071)。

### 面试官：什么是 reward hacking？

**短答**：模型找到了提高 reward 的捷径，却没有真正完成目标。例如只学会套格式、堆免责声明、重复关键词或迎合 judge，而不是提高事实性和任务质量。

**原理**：代理目标 `reward` 与真实目标 `utility` 不完全相同；优化越强，越可能放大 reward model 的盲点。

**trade-off**：增加 reward 维度可以减少单一捷径，但也增加冲突、权重和调参；需要 holdout、人审、对抗测试和 reward decomposition。

**常见追问**：如何发现？看 reward 与独立质量指标是否分离，检查长度、格式、引用和人审 slice。

### 面试官：RL 后训练常见的失败模式有哪些？

**短答**：常见问题包括 reward model overoptimization、长度偏置、格式 reward 饱和、KL 太高或太低、reward variance 过大、LLM-as-a-Judge 噪声、训练/评测污染，以及探索不足。

**原理**：

- reward model overoptimization：policy 过度拟合 proxy。
- length bias：更长回答获得更多表面 reward，或者被错误惩罚。
- format saturation：模型只学会 JSON/模板，内容没有变好。
- KL 太高：偏离 reference 太快；太低：几乎没有学习。
- reward variance：advantage noisy，更新方向不稳定。
- judge noise：评分模型的偏好、位置和 prompt bias 进入 reward。

**trade-off**：更强 KL、clip 或 reward normalization 能稳住训练，却可能压低探索和上限；需要用独立 holdout、多个 judge、人工抽样和 failure slices 共同判断。

**常见追问**：如何区分模型真的变好和 reward hacking？看未参与 reward 的独立指标、反事实测试、长度控制和人审，而不是只看训练 reward。

### 面试官：entropy collapse 是什么？

**短答**：policy 的输出分布过快变尖，熵下降，模型几乎只选择少数 token/路径，探索和泛化能力下降，严重时训练崩溃。

**原理**：token policy entropy 可写为 `H(π)=-Σ p(a)log p(a)`；RL 更新、过强 reward、过低 KL 或过度 clipping 都可能让分布收缩。

**trade-off**：提高 entropy bonus 或放宽探索可以减缓 collapse，但可能带来随机性和 reward 下降；应按训练阶段监控 entropy、KL、clip fraction、reward variance 和独立质量。

**常见追问**：entropy 下降一定是坏事吗？不是，训练收敛时适度下降可能正常，关键是速度、范围和质量是否同步。

## G. Eval / Harness

### 面试官：deterministic eval、model-based grader、human grader 怎么选？

**短答**：deterministic grader 适合 schema、route、citation ID、字符串或数值契约；model-based grader 适合开放文本的相关性、风格和部分 grounding；human grader 适合高风险、争议或需要领域判断的质量。

**trade-off**：deterministic 可复现但覆盖窄；LLM judge 便宜灵活却有偏差和漂移；人审可靠但贵、慢、需要 rubric 和一致性监控。

**常见追问**：LLM judge 如何校准？用金标准、盲评、交叉 judge、人工 agreement 和定期回测，不能把 judge 分数当绝对真值。

### 面试官：pass@k 和 pass^k 有什么区别？

**短答**：pass@k 问“k 个样本里至少有一个成功”，适合有多次尝试的生成任务；pass^k 通常问“k 个样本是否全部成功”，更严格，反映一致性。

**公式直觉**：若单次成功率近似为 p，独立时 `pass@k ≈ 1-(1-p)^k`，`pass^k ≈ p^k`；真实采样往往不独立，估计要谨慎。

**trade-off**：pass@k 容易被多次采样成本掩盖，pass^k 对偶发失败非常敏感；报告时要写 k、采样温度、是否独立和估计方式。

**常见追问**：重复运行 3 次就是 pass@3 吗？不一定；必须看任务是否允许多次抽样后择优。重复 robustness trial 不能随意改名为 pass@k。

### 面试官：为什么需要 multiple trials？

**短答**：如果模型、工具或网络有随机性，一次 run 只能看到一个样本。multiple trials 可以观察重复成功率、方差和 route/tool policy 的不稳定性。

**原理**：固定 case、模型配置和 knowledge pack，改变 trial seed 或重复请求；同时保存每条 trajectory，不能只保存平均分。

**trade-off**：更多 trial 提高估计成本，但小样本下仍可能有很宽的不确定性；trial 不是扩大 case coverage 的替代品。

**常见追问**：为什么要同时报告 category slice？因为平均值会掩盖 OOD、safety、paraphrase 等不同失败。

### 面试官：如何设计 regression set？

**短答**：把历史真实 bad cases、边界 case、负例和关键 invariant 固定下来；每次改动都重跑并比较相关指标，而不是只测新增 happy path。

**原理**：case 至少要有 ID、输入、预期 route/来源、类别、版本和标注状态；新增失败要进入 pack，修复后不能删除原 case。

**trade-off**：set 太小容易过拟合，太大则运行成本高；可分为 PR smoke、nightly focused 和 release full suite。

**常见追问**：如何让回归集可执行？CI 应固定 case、grader、数据/config identity，并对必要的冻结指标设置合理 tolerance，而不只是比较最终文案。

### 面试官：什么是 benchmark contamination？

**短答**：评测样本或其近似内容进入了训练/检索语料，使分数反映记忆或数据泄漏，而不是泛化能力。

**原理**：污染可能是 exact overlap、模板/题目变体、公开答案、检索库泄漏或人工 prompt 复用。要保留时间切分、来源 provenance、去重和未公开 holdout。

**trade-off**：完全避免公开 benchmark 污染很难，关键是透明报告数据来源、时间、去重方法和独立测试。

**常见追问**：自建 Product Eval 就一定不污染吗？不一定；它也可能被 prompt、知识卡或训练数据间接泄漏。

### 面试官：如何评估一个 Agent，而不是只评最终答案？

**短答**：同时评估 outcome、trajectory 和 cost/safety：最终 route/answer、工具是否必要、参数是否合规、是否越权、是否终止、耗时、token、重试和 citation/grounding。

**原理**：把指标拆成 action policy、tool correctness、evidence quality、final answer、abstention 和 invariant violation。对 OOD 要单独记录工具激活率和错误回答率。

**trade-off**：指标越多，解释更清楚但维护成本更高；必须写清 denominator，尤其是短路 case 和 missing run 如何计数。

**常见追问**：为什么不能只看 accuracy？Agent 可能最终答对但用了不必要工具，或最终 abstain 掩盖了高成本/高风险轨迹。

## 如何映射到项目面试

本页不重复各项目的实现、指标和 claim 边界。先用这里的定义和公式回答“是什么/怎么工作”，再去对应专题页回答“项目怎么实现/结果是什么”： [RAG](/projects/health-copilot/01-rag项目面试追问/)、[Memory](/projects/health-copilot/02-memory项目面试追问/)、[Multi-Agent](/projects/health-copilot/03-multi-agent项目面试追问/)、[RL 项目边界](/projects/health-copilot/04-rl项目面试追问/)。

## 参考源

- Agent/runtime： [ReAct](https://arxiv.org/abs/2210.03629)、[OpenAI Harness Engineering](https://openai.com/index/harness-engineering/)、[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)、[Anthropic tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)、[MCP tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)。
- RAG/retrieval： [RAG](https://arxiv.org/abs/2005.11401)、[BM25 review](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf)、[BEIR](https://arxiv.org/abs/2104.08663)、[HNSW](https://arxiv.org/abs/1603.09320)。
- 模型/serving： [Transformer](https://arxiv.org/abs/1706.03762)、[PagedAttention/vLLM](https://arxiv.org/abs/2309.06180)。
- 分布式/后训练： [PyTorch FSDP](https://docs.pytorch.org/docs/stable/fsdp.html)、[ZeRO](https://arxiv.org/abs/1910.02054)、[PPO](https://arxiv.org/abs/1707.06347)、[DPO](https://arxiv.org/abs/2305.18290)、[GRPO/DeepSeekMath](https://arxiv.org/abs/2402.03300)、[GSPO](https://arxiv.org/abs/2507.18071)。
