---
title: "L13 · Data I"
weight: 13
date: 2026-08-30
updated: 2026-09-16
course: "CS336"
topics: ["CS336", "data", "pretraining", "data-curation", "copyright"]
aliases:
  - /blog/2026/2026-08-30-cs336-lecture13/
---

Lecture 13 把问题从“如何训练模型”推进到“模型究竟吃什么数据”。前面的架构、训练系统和 scaling law 都默认训练数据已经存在，但真实的 foundation model pipeline 并不是把“整个互联网”下载下来再喂给模型。它要经历来源选择、爬取、格式转换、语言识别、质量过滤、去重、隐私处理、版权审查和混合配比。

数据工作的难点也和架构工作不同：架构可以用清晰的代码和实验复现，数据质量却大量依赖长尾规则、人工判断、来源偏差和法律边界。数据不是一个静态的 jsonl 文件，而是一套持续变化的生产系统。

## 1. Data 决定模型学到什么

模型会被训练语料的分布塑形。代码比例高，模型的编程和结构化推理通常更强；百科与教材比例高，知识表达更稳定；多语言数据不足，低资源语言能力就会受限；合成指令、对话和高质量推理轨迹则更接近 mid-training 或 post-training 的目标。

训练过程可以先用三段来理解：

| 阶段 | 主要数据 | 目标 |
| --- | --- | --- |
| Pre-training | 大规模网页、书籍、代码、论文等原始文本 | 学习通用语言分布与世界知识 |
| Mid-training | 更高质量、更聚焦的文本或领域数据 | 增强知识、代码、长上下文或特定能力 |
| Post-training | 对话、示范、偏好比较、可验证任务 | 改变交互行为、遵循指令和策略 |

实际项目里三条边界并不绝对，可能有更多阶段；但总体趋势很稳定：从大规模、较低质量的数据，逐步移动到更小、更干净、更贴近目标的数据。

Base model 通常指 pre-training 与 mid-training 后的模型，instruct/chat model 则还经过 post-training。现在不少模型只发布最终 instruct 版本，不再公开完整的 base model，因此数据构成与阶段配方会更难审计。

![LLaMA 3 对训练数据的披露方式](/learning/cs336/lectures/l13-llama3-data.png)

以 OLMo 为例，数据工作会被显式拆成预训练、mid-training 和 post-training 数据，而不是把所有样本混在一个池子里。这个拆分也提醒我们：同一条文本放在不同训练阶段，作用可能完全不同。

![OLMo 的 pre-training 数据阶段](/learning/cs336/lectures/l13-olmo2-pretraining.png)

![OLMo 的 mid-training 数据阶段](/learning/cs336/lectures/l13-olmo2-dolmino.png)

![OLMo 的 post-training 数据阶段](/learning/cs336/lectures/l13-tulu.png)

## 2. “在整个互联网训练”为什么不准确

互联网首先是一组可以连接的 live server，而不是一个可以直接读取的训练集。crawler 从 seed URL 出发，发现网页、下载响应、提取超链接，再把新的 URL 放回队列。模型训练只能使用已经抓取并保存下来的快照。

从 live web 到可训练文本，至少有四类限制：

| 限制 | 具体问题 |
| --- | --- |
| Dynamic content | Discord、WandB 等应用需要点击、提交表单或执行 JavaScript，单次下载 HTML 看不到完整内容 |
| Authentication | Facebook、X、LinkedIn、付费新闻等内容需要账号、订阅或登录状态 |
| Technical policy | robots.txt、CAPTCHA、IP/地区封锁、rate limit 和 Cloudflare 会限制爬取 |
| Legal policy | Terms of Service 可能禁止 bot 下载，复制网页也可能缺少相应 license |

因此，Common Crawl 之类的公开抓取只覆盖 web 的一个可访问子集，而且会随时间变化。课程用“consent decline”提醒我们：许多网站逐渐增加 robots、ToS 或其他限制，数据集的可访问范围并不是稳定扩大的。

![网站对自动抓取限制的变化](/learning/cs336/lectures/l13-decline-consent.png)

爬虫还会给网站带来服务器负载和成本。无视 robots、ToS 或 rate limit 的抓取不是一个单纯的工程效率问题，而会影响原站服务，也会把数据获取、版权和隐私风险转嫁给数据集使用者。

![不当爬取可能造成的服务器负担](/learning/cs336/lectures/l13-anthropic-crawling.png)

## 3. 版权、许可与数据来源的合法边界

课程以美国版权法的基本框架说明：版权保护的是固定在某种介质上的原创表达，而不是抽象想法或算法本身。一个网页只要达到很低的原创性门槛，通常就可能受到保护；是否公开可访问，不等于可以任意复制和用于训练。

使用受版权保护的材料，常见路径有两种：取得 license，或在具体事实下主张 fair use。课程强调 fair use 不是一个自动开关，而要综合考虑：

1. 使用目的与性质：教育、非商业、transformative use 通常更有利，但不是自动成立。
2. 原作品性质：事实性、非创作性内容与高度创作性的小说受到的考量不同。
3. 使用的数量与实质性：使用片段和复制整部作品的风险不同。
4. 对原市场的影响：训练和生成是否影响作品的现有或潜在市场。

对语言模型而言，复制数据是训练的第一步，模型是否最终逐字复述又是另一层问题；“不会逐字记忆”不能自动解决复制、许可或市场影响。Terms of Service 也独立于版权存在：即使某项内容有开放许可，网站的服务条款仍可能限制自动下载或特定用途。

Creative Commons、公共领域和 permissive software license 可以让数据使用更清晰，但必须确认 license 适用于单条作品，而不是只适用于一个数据集的打包或分发方式。Common Pile 之类的工作正是在探索：只使用 public-domain 与 openly licensed 数据，能否训练出有竞争力的模型。

课程列举的诉讼与争议案例说明，训练是否构成 fair use、复制书籍本身是否合法、模型对原市场的影响如何判断，都高度依赖事实和司法辖区，不能把某一个案件的结论推广成“AI training 一律合法”或“一律违法”。工程上最稳妥的做法仍然是记录来源、保留许可信息、执行 opt-out 与隐私处理，并把法律审查纳入数据 pipeline。

## 4. Common Crawl：从网页快照到文本

Common Crawl 是非营利的公开网页抓取项目，大约每月增加数十亿页面，累计规模达到数百 billions of pages。它可以提供大规模、跨领域的原始网页，但原始数据并不等于自然语言语料。

一个 crawler 要同时处理：

- **Selection policy**：选择哪些 URL，如何扩展 seed 和队列；
- **Politeness policy**：如何尊重 robots、控制并发和服务器负载；
- **Revisit policy**：页面多久重新抓取一次；
- **URL duplication**：不同 URL 可能指向几乎相同的内容，动态参数还会制造大量重复页面。

Common Crawl 常见的两种存储形式是：

| 格式 | 含义 | 代价 |
| --- | --- | --- |
| WARC | 原始 HTTP response，例如 HTML、header 和元信息 | 信息完整，但仍需做 HTML 解析和内容抽取 |
| WET | 已经转换出的纯文本 | 方便训练，但转换过程有损，可能丢结构或保留噪声 |

HTML 到文本不是无关紧要的预处理。导航栏、广告、cookie 提示、评论区和模板文字如果被错误保留，会改变 token 分布；正文、代码块、表格和标题如果被错误删除，又会损失对下游任务有用的结构。DCLM 的可视化正好说明：同一网页经过不同 extraction pipeline，最后得到的文本量和质量都不同。

![HTML 到文本的转换结果](/learning/cs336/lectures/l13-dclm-wet.png)

## 5. 专门数据源：网页之外的结构与质量信号

Common Crawl 提供覆盖面，但专门数据源通常有更好的结构、质量信号或领域密度：

| 来源 | 主要价值 | 主要风险 |
| --- | --- | --- |
| Wikipedia | 多语言百科知识、编辑历史、定期 dump | 主题范围有边界，也可能有 vandalism 或被人为污染 |
| GitHub | 源代码、目录结构、commit、issue、PR 和评论 | fork 与复制严重，license 和 PII 需要处理 |
| arXiv | 论文 metadata、PDF 和可选 LaTeX source | 预印本不等于同行评审，格式解析复杂，领域分布偏 |
| StackExchange | 问答、votes、tags、comments 和 reputation | 用户群体偏，答案质量与社区规则相关 |
| Project Gutenberg | 大量版权已过期的公共领域书籍 | 语言、年代和体裁分布不均 |

GitHub 不只是“把网页上的代码复制下来”。repository 可以通过 git 结构获取，issues、pull requests、comments 等 metadata 则来自 API 或事件快照；这些元数据能帮助判断问题质量、答案关系和开发上下文。Software Heritage 还以长期保存代码为目标，聚合多个代码托管源，但不一定保留同样完整的社区讨论信息。

Wikipedia 的价值来自编辑和维护机制，但高质量来源也不等于没有攻击面。有人可以在定期 dump 前注入恶意编辑，使下游模型学到带触发条件的错误关联；所以来源信誉、版本时间和异常编辑检测都值得纳入 pipeline。

## 6. 数据集历史：从手工规则到数据混合

经典数据集的变化体现了“什么是好数据”的认识演进：

| 数据集/路线 | 核心策略 | 代表性教训 |
| --- | --- | --- |
| BERT | Wikipedia + BooksCorpus | 文档级连续序列比孤立句子更接近语言建模；BooksCorpus 的来源与 ToS 也留下争议 |
| GPT-2 WebText | 选择 Reddit karma ≥ 3 的外链页面 | 用人类分享行为作为 web 质量的弱标签；约 800 万页面、40GB 文本 |
| CCNet | 语言识别、段落去重、用 Wikipedia 风格的 KenLM 过滤 | 可以把高质量来源当作弱监督，尤其帮助低资源语言 |
| C4 / T5 | 规则过滤 Common Crawl | 标点、句子数、坏词、模板词和语言识别能迅速降噪，但会引入规则偏差 |
| GPT-3 | Common Crawl、WebText2、书籍和 Wikipedia，加入 learned quality classifier | 用高质量参考分布训练分类器，并做模糊去重与 benchmark 去重 |
| The Pile | 22 个明确领域的 mixture，约 825GB、275B tokens | 与其假装 web 无偏，不如显式控制领域构成与来源 |

The Pile 的重要性不只在规模，还在于它把 Common Crawl、PubMed Central、论文、邮件、书籍和 StackExchange 等来源拆开，让研究者能讨论 mixture 的影响。它也同时暴露了 Books3 这类影子图书馆数据的版权风险：一个数据集能被分发，不代表其中每个作品都获得了合法授权。

## 7. 2022 之后：更多 token 与更强过滤并存

Gopher 的 MassiveText 把 MassiveWeb、C4、Books、News、GitHub 和 Wikipedia 组合起来，并做语言筛选、去重、train-test overlap 检查、手工质量规则与 SafeSearch 毒性过滤。它最终准备了约 10.5TB 文本，但 Gopher 实际只训练了约 300B tokens，说明“收集到的数据量”与“模型实际消费的 token 数”是两个不同指标。

LLaMA 的配方将 Common Crawl/CCNet、C4、GitHub、Wikipedia、Project Gutenberg、Books3、arXiv 和 StackExchange 组合起来，最终约 1.2T tokens。它展示了一个重要模式：不同来源的处理规则不同，代码需要 license 筛选，论文需要清理 comments、宏和 bibliography，StackExchange 可以利用答案 score 排序。

随后出现了强调 web-only 的 RefinedWeb 与 FineWeb。RefinedWeb 使用 WARC、trafilatura、Gopher 风格规则和 MinHash 去重，从约 5T tokens 中发布约 600B；FineWeb 扩展到 95 个 Common Crawl dump，加入 URL 过滤、语言识别、更多规则、MinHash 和 PII 匿名化，规模达到约 15T tokens。

Dolma 则重新强调多来源 mixture，包含 Reddit、Semantic Scholar 论文、C4、Project Gutenberg、Wikipedia/Wikibooks 等，经过语言识别、质量与毒性过滤、Bloom filter 去重，约 3T tokens。这里的趋势不是“最后只剩 web”，而是不同训练目标会重新权衡覆盖面、质量、领域多样性与数据新鲜度。

## 8. Quality Filtering：过滤越狠不一定越好

DCLM 把数据处理变成更可控的实验：先从 Common Crawl 构建约 240T tokens 的 DCLM-pool，再用统一的质量分类器筛出 DCLM-baseline。它的关键思想是，固定 raw pool、模型 recipe 和 evaluation，让“数据处理算法”成为主要实验变量。

DCLM 的 quality classifier 使用约 20 万条正例和 20 万条负例训练：正例来自高质量 instruction 与解释型问答，负例来自 RefinedWeb 等 web 数据。之后把这个快速分类器运行在整个 pool 上。它在相同模型与计算量下优于若干手工规则，说明高质量数据筛选本身可以成为模型能力的重要来源。

![DCLM 的过滤流程](/learning/cs336/lectures/l13-dclm-filter.png)

![DCLM 的质量分类器结果](/learning/cs336/lectures/l13-dclm-quality.png)

但过滤并非越 aggressive 越好。FineWebEdu 和 DCLM 等方法可能移除约 90% 的候选数据；如果 scaling regime 需要更多 tokens，过度过滤会让模型缺少覆盖面、长尾知识和低资源语言。Nemotron-CC 的思路是保留更多数据，同时提高教育价值：让大型 instruct model 对文档评分，再蒸馏成更快的分类器；对低质量文本做重写，对高质量文本生成 QA、关键信息和任务结构。

Nemotron-CC 最终报告约 6.3T tokens，其中 high-quality subset 约 1.1T。作为尺度参照，LLaMA 3 约使用 15T、Qwen3 约使用 36T tokens。核心结论不是某个固定数字，而是 data filtering 形成 Pareto frontier：

$$
\text{质量} \uparrow
\quad\Longleftrightarrow\quad
\text{覆盖面、数量、偏差和成本之间重新取舍}
$$

![Nemotron-CC 在数据规模与质量之间的结果](/learning/cs336/lectures/l13-nemotron-results.png)

## 9. Code Data：代码既是能力数据，也是结构数据

代码不只是另一种自然语言。它同时携带语法、依赖关系、执行反馈、目录结构、版本历史和 issue-to-patch 的因果链，因此既能提升 programming，也常被认为能帮助结构化推理。

The Stack 通过 GitHub Archive 获取 repository 名称，再 git clone 约 1.37 亿个 repository、约 510 亿个文件，最后保留 MIT、Apache 等 permissive license，并用 MinHash 与 Jaccard similarity 去重，得到约 3.1TB 代码。Stack v2 又加入 GitHub Archive 的 issues、comments、PR，以及 Software Heritage 的 repository、PyPI/npm/devdocs 等文档，并做二进制和恶意代码清理、bot activity 过滤、PII redaction 与 PR 子采样。

PR 数据不能简单拼成一段字符串。它需要把结构化对象 linearize 成 token sequence，同时补充 diff 周围的文件上下文；低资源语言还可以和共享的低级表示、LLVM 结构配对。这样得到的训练样本不只教模型“代码长什么样”，还可以教它“一个工程问题如何通过讨论、修改和测试被解决”。

![Stack v2 中 PR 数据的结构化样本](/learning/cs336/lectures/l13-stackv2-pr1.png)

![Stack v2 中补充上下文后的 PR 样本](/learning/cs336/lectures/l13-stackv2-pr2.png)

代码数据的三条底线是：license 要可追踪，重复和 fork 要控制，安全与隐私要单独处理。否则模型可能在 benchmark 上看似很强，却因为训练集泄露、复制代码、恶意依赖或个人信息而产生实际风险。

## 10. Provenance、去重与 Poisoning：数据集不是一个文件

一个可用数据集应该能回答每条样本来自哪里、何时抓取、经过哪些转换、适用什么 license、是否和 evaluation overlap，以及为什么被保留或删除。这个 provenance graph 比单个最终文件更重要，因为后续发现问题时需要回溯、删除或重新加权。

去重也不是简单的数据卫生。网页转载、SEO mirror、GitHub fork、新闻 syndication 和模板页面会让某种表达在训练分布中被重复放大。重复会让模型过度拟合高频文档，污染 evaluation，还会改变 token budget 实际覆盖的独立信息量。常见的轻量方法包括规范化后的段落去重、MinHash、n-gram 相似度、Bloom filter，以及跨数据源的 fuzzy deduplication。

去重策略又不能过度激进：同一事实的不同表达、同一项目的不同版本、代码与文档之间可能包含有价值的互补结构。真正的问题不是“有没有重复”，而是重复是否改变了目标能力与数据分布。

Poisoning 是另一个方向：攻击者可以在高影响来源中注入少量恶意文本，等待 crawler 或定期 dump 收集后影响模型。Wikipedia 的可编辑性、公共代码仓库、开放评论区都可能成为注入面。因此，质量过滤之外还需要来源版本、编辑异常、重复模式、触发词关联和人工抽检。

## 11. Common Pile：许可清晰的数据能否训练好模型

Common Pile 探索一个很重要的问题：如果尽量只使用 public-domain 或 openly licensed 数据，能否得到有竞争力的 foundation model？它收集了约 8TB 数据，试图让来源与许可更容易审计。

这条路线仍有几个细节不能忽略：

- **License laundering**：有人可能把受版权保护的作品重新发布成 permissive license，数据集很难自动发现。
- **Collection license 不等于 item license**：一个集合采用开放许可，不代表集合中的每一条作品都可按同样方式使用。
- **Synthetic data 的来源问题**：由未明确许可的数据训练出的模型生成样本，再用于新模型训练，许可与衍生关系仍然需要具体分析。

Common Pile 的结果说明，许可清晰的数据可以训练出不错的模型，但在 token 数、领域覆盖和竞争力上通常更困难。它不是简单地证明“开放数据足够”或“开放数据不够”，而是把 provenance、法律风险和模型质量放进同一个优化问题。

![Common Pile 的数据来源组成](/learning/cs336/lectures/l13-commonpile.png)

![许可清晰数据上的模型结果](/learning/cs336/lectures/l13-comma-results.png)

## 面试复盘

1. **为什么不能说“模型在整个互联网训练”？** 因为训练使用的是 crawler 能访问、允许保存、经过处理的 web 子集；动态页面、登录、技术策略、ToS 和版权都会限制可用范围。

2. **WARC 和 WET 的区别是什么？** WARC 保存原始 HTTP response，信息完整但需要抽取；WET 是转换后的文本，方便训练但会丢失结构，也可能继承 extraction 噪声。

3. **为什么 HTML 到文本会影响模型能力？** 导航、广告和模板会污染 token 分布，错误删除正文、代码和表格又会损失任务相关结构，因此 extraction 不是无关紧要的预处理。

4. **为什么专门数据源比纯 web 更重要？** Wikipedia、GitHub、论文和 StackExchange 带有领域结构、质量信号或 metadata，能够补足 Common Crawl 的噪声与分布偏差。

5. **BERT、GPT-2、C4、The Pile 体现了哪些数据策略？** 从 Wikipedia/Books 的文档语料，到 Reddit karma 弱监督，再到规则过滤和显式多 domain mixture，逐步把来源与质量控制说清楚。

6. **为什么质量过滤越狠不一定越好？** 过滤提高平均质量，但会损失数量、长尾知识、语言多样性和覆盖面；数据规模与质量需要在目标 scaling regime 下共同优化。

7. **DCLM 的实验价值是什么？** 它固定 raw pool、训练 recipe 和 eval，把 data processing algorithm 变成主要变量，从而更公平地比较过滤方法。

8. **代码数据为什么需要单独处理？** 代码包含执行结构、依赖、版本和 issue/PR 上下文，不能只当普通文本；同时 license、重复、恶意代码和 PII 风险更突出。

9. **为什么 provenance 和 deduplication 都是模型能力问题？** provenance 决定能否追责、删除和解释样本来源；重复会改变有效数据分布、放大某些表达并造成 evaluation contamination。

10. **Common Pile 想验证什么？** 它探索在 public-domain 与 openly licensed 数据上训练有竞争力模型的可行性，同时暴露 license laundering、集合许可和 synthetic data 继承关系等问题。

如果只能记住一句话，那就是：**训练数据不是从互联网自动掉下来的 token，而是经过来源选择、结构化处理、质量过滤、去重、法律审查和目标配比之后，主动构造出来的模型行为分布。**
