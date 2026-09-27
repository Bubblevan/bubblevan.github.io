---
title: "L14 · Data II"
weight: 14
date: 2026-08-31
updated: 2026-09-16
course: "CS336"
topics: ["CS336", "data", "filtering", "deduplication", "data-mixing", "synthetic-data"]
aliases:
  - /blog/2026/2026-08-31-cs336-lecture14/
---

Lecture 13 讨论数据从哪里来，Lecture 14 讨论拿到原始数据以后如何把它变成可训练的数据。整讲可以压成四个 data algorithm：**Transformation、Filtering、Deduplication、Data Mixing**；随后把同样的思想延伸到 mid-training、SFT 和 agent synthetic data。

一条完整的数据管线大致是：

$$
\text{raw source}
\rightarrow
\text{representation}
\rightarrow
\text{filtering}
\rightarrow
\text{deduplication}
\rightarrow
\text{mixture}
\rightarrow
\text{training}
$$

这些步骤不是单纯的数据清洁。每一步都在改变模型看到的分布、有效 token 数、能力覆盖面和成本，因此应该像训练超参数一样被实验和评估。

## 1. Transformation：先把原始对象变成可训练序列

原始数据通常不是纯文本：网页是 HTML，论文可能是 PDF，代码是 repository 与版本历史，图文资料还包含图片、表格和版面信息。模型最终需要 token sequence，所以 transformation 必须把不同结构线性化，同时尽量保留对目标任务有用的信息。

HTML 到文本通常要删除导航、广告、cookie 提示和模板内容，再抽取正文、标题、代码块或表格。它天然是有损转换：图片和布局可能被丢弃，表格需要重新组织，正文顺序也可能被打乱。trafilatura、resiliparse、jusText 等规则工具的差异会直接改变最终训练分布。

![HTML 转文本后的数据差异](/learning/cs336/lectures/l14-dclm-wet.png)

PDF 还要面对截断、双栏、公式、表格和扫描件问题。FinePDFs 的路线包括重新抓取被截断的 PDF、用 OCR 或文档解析模型恢复文本，再进行清理和过滤；即使如此，很多 layout 信息仍然难以完整保留。对论文、教材和代码文档而言，结构损失可能比少几个 token 更严重。

所以 transformation 的评价标准不是“文本是否变长”，而是：正文保留了吗？结构是否可恢复？噪声是否被移除？目标能力需要的公式、代码、表格和上下文是否仍然存在？

## 2. Filtering：用目标数据定义什么叫“好”

Filtering 的统一抽象是：给定大量 raw data \(R\) 和代表目标质量的 target data \(T\)，从 \(R\) 中选出一个与 \(T\) 相似的子集 \(T'\)：

$$
T' \subseteq R,
\qquad
T' \approx T
$$

![Raw data 与 target data 的筛选框架](/learning/cs336/lectures/l14-raw-target-schema.png)

这个框架可以表达多种任务：

| 过滤目标 | target data 的例子 | 典型用途 |
| --- | --- | --- |
| Language ID | 某种语言的文本 | 保留英语、中文或低资源语言 |
| Quality | Wikipedia、教材、高质量指令 | 去除模板、乱码和低信息网页 |
| Domain | 数学证明、代码、医学文献 | 构造领域能力数据 |
| Toxicity / Safety | 标注过的有害评论 | 降低毒性或显式研究风险 |

一般流程是先建立 score function，再按 threshold 保留样本：

$$
\operatorname{score}(x)
\rightarrow
\operatorname{keep}(x)
$$

score 可以来自 target distribution 的生成模型，例如 KenLM：

$$
\operatorname{score}(x)=p_T(x)
$$

也可以来自二分类器：

$$
\operatorname{score}(x)=p(T\mid x)
$$

一个实用的 filtering algorithm 要同时满足两点：能从有限的 target 泛化到不同的 raw example，而且足够快，能够在数十万亿 token 上运行。模型过滤与手工规则各有优缺点：C4、Gopher、RefinedWeb、FineWeb、Dolma 更依赖规则以减少 classifier bias；GPT-3、LLaMA、DCLM 则使用 model-based filtering，当前逐渐成为主流。

## 3. Language ID 与领域过滤：从简单规则到强监督

Language identification 是最基础的 filtering。fastText 的语言分类器支持约 176 种语言，可以根据 Wikipedia、Tatoeba 和 Southeast European news 等多语言来源训练。Dolma 采用英文概率阈值，例如保留 \(p(\\text{English})\ge 0.5\) 的页面；阈值不同会在召回率与混入其他语言之间做取舍。

OpenMathText 展示了领域过滤如何组合多种信号。它先用规则寻找 LaTeX 或数学符号，再用 ProofPile 训练的 KenLM，保留 perplexity 小于 15000 的文本，并训练 fastText classifier 判断数学写作：数学样本阈值约为 0.17，非数学样本阈值约为 0.8。最后得到约 14.7B mathematical tokens，用于训练 1.4B 模型时，效果优于使用约 20 倍普通数据的模型。

GPT-3 用 Wikipedia、WebText2、Books1、Books2 作为 positive examples，把 Common Crawl 作为 negative examples，训练线性 classifier，再按分数随机保留文档。LLaMA/RedPajama 则把“被 Wikipedia 参考页面链接”作为高质量弱标签，与普通 Common Crawl 做对比。

Phi-1 进一步体现“教育价值”这个 target construct：用 GPT-4 对 Python 子集样本进行分类，问题是“它对一个想学习基础编程的学生有多大教育价值”，再用 CodeGen embedding 训练 random forest。1.3B 模型在原始 Python 子集上 HumanEval 约为 12.19%，在过滤后的数据上约为 17.68%，而且只训练了更少的 steps。

毒性过滤也是同一套框架。Dolma 使用 Jigsaw Toxic Comments 的 toxic、severe toxic、obscene、threat、insult、identity hate 等标签训练或校准过滤器，但要注意：从有害内容中筛掉风险数据，和为了研究安全而保留风险样本，是两个不同的目标。

## 4. Filtering 的阈值依赖训练规模

过滤最反直觉的一点是：不存在脱离训练规模的唯一最佳 threshold。短训练预算需要更高质量的数据，因为模型没有时间消化大量噪声；训练 token 变多以后，继续重复高质量小池子会过拟合，因此需要放宽过滤、加入更多长尾样本。

可以把它写成：

$$
\text{small training budget}
\Rightarrow
\text{higher-quality, smaller pool}
$$

$$
\text{large training budget}
\Rightarrow
\text{broader pool, more lower-quality data}
$$

![Filtering threshold 随训练规模变化](/learning/cs336/lectures/l14-data-filtering-scale.png)

这意味着 filtering 不是一次性清洗任务，而是与模型规模、训练 token 数、目标能力和 evaluation 共同决定的优化变量。一个在 1B 模型上最优的过滤器，不一定适用于 70B 模型；一个在短实验上有效的 threshold，可能在 full run 中造成严重重复和覆盖不足。

## 5. Deduplication：不是节省硬盘，而是在改变训练分布

重复数据有两类：

- **Exact duplicate**：镜像站、GitHub fork、相同的 license 或模板页面。
- **Near duplicate**：只改了少数 token、格式、标点或变量名的同一段内容。

网页中同一段产品描述可能被重复数万次；模板化条款、新闻转载、SEO 页面和代码 fork 都会放大某些表达。去重的直接收益有三点：减少无效训练 token、降低记忆与 contamination、减少隐私和版权复现风险。

但 deduplication 本身包含三个设计选择：

1. 什么是 item：句子、段落、三句 span、文档、repository，还是 PR？
2. 什么算 match：完全相同、共享某个子片段，还是相似度超过阈值？
3. 检测到重复后做什么：全部删除，保留一份，还是按来源质量加权？

去重本质上是 item-to-item comparison，而数据规模要求近似线性算法。过于激进会误删同一事实的不同表达、同一项目的不同版本或有价值的上下文，因此“去重率越高越好”同样是错误目标。

## 6. Hash 与 Exact Dedup：最简单、最可靠的基线

Hash function \(h\) 把一个 item 映射成较小的整数或字符串。若不同 item 产生相同 hash，就是 collision。SHA-256 等 cryptographic hash 更抗碰撞但更慢；MurmurHash、DJB2、CityHash 更适合 hash table 和大规模工程，速度快但不提供密码学安全性。

Exact dedup 的基本流程是：

1. 对每个 item 计算 hash；
2. 按 hash 分组；
3. 每组只保留一个 item。

它的优点是语义清晰、精度高、容易用 MapReduce 并行扩展；缺点是无法识别只改了一个词、标点或格式的 near duplicate。C4 的一个设计是把三句 span 作为 item 做 exact match，删除重复 span，但如果 span 位于文档中间，直接删除可能让剩余文档不连贯。

因此 exact dedup 适合作为第一层基线，却不能独立解决 web 数据中大量的 near duplicate。

## 7. Jaccard 与 MinHash：把文本相似度变成可估计的碰撞

把文档表示成 token、word n-gram 或 sentence span 的集合 \(A,B\)，Jaccard similarity 定义为：

$$
J(A,B)=\\frac{|A\\cap B|}{|A\\cup B|}
$$

例如：

$$
A=\\{1,2,3,4\\},\quad
B=\\{1,2,3,5\\}
$$

则：

$$
J(A,B)=\\frac{3}{5}=0.6
$$

如果 \(J(A,B)\) 超过设定阈值，就可以把两个文档看作 near duplicate。但直接对所有文档两两计算集合交并，复杂度太高，需要 MinHash。

MinHash 的关键性质是：随机 hash function \(h\) 对两个集合取最小 hash 值时，

$$
\Pr[h(A)=h(B)]=J(A,B)
$$

这和普通 hash 的目标正好相反。普通 hash 希望不同对象尽量不要碰撞；MinHash 则希望碰撞概率精确反映集合相似度。

直觉上，把元素随机排列后，观察 A 和 B 中哪个元素最先出现。如果最先出现的是共同元素 1、2、3，两个集合的 minimum 相同；如果最先出现的是 4 或 5，minimum 不同。重复使用多组独立 hash，两个集合发生相同 minimum 的比例就能估计 Jaccard。用 100 个 hash function 时，经验碰撞比例应接近 0.6，但单次估计仍有随机误差。

## 8. LSH：把 MinHash 的概率曲线变成近似阈值

一次 MinHash 只有：

$$
\Pr[A\\text{ and }B\\text{ collide}]=J(A,B)
$$

相似样本更容易碰撞，但边界很随机。Locality-Sensitive Hashing（LSH）把 \(n\) 个 MinHash 分成 \(b\) 个 bands，每个 band 有 \(r\) 个 hash function：

$$
n=b\\times r
$$

两个文档在某个 band 中的所有 \(r\) 个 hash 都相同，才算这个 band 命中；只要有一个 band 命中，就把两个文档送入候选集合。若 Jaccard similarity 为 \(s\)，固定 band 完全相同的概率是 \(s^r\)，至少一个 band 命中的概率是：

$$
P(\\text{collision})
=
1-(1-s^r)^b
$$

这就是 LSH 的 AND-OR 结构：band 内部用 AND 提高严格性，多个 band 之间用 OR 保留召回率。

参数作用可以这样记：

| 参数 | 效果 |
| --- | --- |
| 增大 \(r\) | 一个 band 更难完全匹配，曲线向右移动，只有更相似的文档才容易命中 |
| 增大 \(b\) | 可命中的 band 更多，曲线向左移动，召回更多近重复 |
| 固定 \(n=b r\) | 在精度和召回之间移动近似 threshold |

课程中的大规模例子取 \(n=9000\)、\(b=20\)、\(r=450\)。一个常用的 threshold 近似是：

$$
s_0\\approx\\left(\\frac{1}{b}\\right)^{1/r}
$$

在 \(s=1/b\) 时，某个固定 band 命中的概率是 \(1/b\)，至少一个 band 命中的概率为：

$$
1-\\left(1-\\frac{1}{b}\\right)^b
\\approx 1-\\frac{1}{e}
$$

LSH 的目标不是精确判断所有 pair，而是用近似线性成本筛出候选 pair，再对候选做更精确的 Jaccard 或 token-level 比较。它因此成为几十亿文档上做 fuzzy dedup 的实用工程折中。

## 9. Data Mixing：数据来源比例也是训练超参数

语言模型通常同时训练 Wikipedia、general web、code、books 和 papers。假设来源集合是 \(S\)，混合分布是 \(p(s)\)，问题就是如何选择：

$$
p(s),\qquad \sum_{s\\in S}p(s)=1
$$

最常见的 baseline 有三种：

| 方法 | 规则 | 风险 |
| --- | --- | --- |
| 手工 vibes | 凭经验给高质量来源更大权重 | 主观、难复现 |
| Uniform | 每个来源等概率 | 忽略来源大小和质量差异 |
| Proportional | 按 token 数采样 | 大 web 来源吞掉稀缺高质量数据 |

直觉上应提高高质量来源的权重，但每个来源都是有限的。如果一个小来源只有 10B tokens，却给它与 10T web 来源相同的采样概率，训练时就会反复 epoch，最后过拟合。

例如 low-quality source 有 10T tokens，high-quality source 只有 10B tokens；两者各占一半，训练总量为 1T tokens，则：

$$
\\text{low epochs}
=
\\frac{0.5\\times 1T}{10T}
=0.05
$$

$$
\\text{high epochs}
=
\\frac{0.5\\times 1T}{10B}
=50
$$

这就是数据 mixing 的隐藏坑：高质量不代表可以无限重复。

## 10. UniMax、RegMix 与 Simulated Epoching

UniMax 针对多语言或多来源混合提出 hard cap：让任何来源的训练次数不超过 \(C\)：

$$
p(s)\\times N_{\\text{train}}
\\le C
$$

它位于 uniform mixing 与 proportional mixing 之间，既照顾小语言或小领域的质量，又避免无限 epoch。

RegMix 把 mixture 当成可优化对象。先从一个分布（例如 Dirichlet）采样若干候选 \(p\)，在小规模模型上训练并得到 validation loss，再用 linear model 或 gradient-boosted tree 拟合：

$$
p
\longrightarrow
L_{\\text{small}}(p)
$$

最后预测更优 mixture。它的风险是小模型上的最优点未必能 transfer 到大模型，而且下游 eval 太多时容易 overfit。这个思路和 scaling law 类似：用便宜的实验拟合 expensive regime，但必须验证外推误差。

Simulated epoching 处理的正是尺度依赖。若小实验只有 10B tokens、大实验计划使用 1T tokens，可以把所有 source 按 \(10B/1T=0.01\) 比例 downsample，再在小实验上模拟未来的大规模重复。这样过度 epoch 的 mixture 会在小规模时暴露过拟合，最优分布通常会更均衡。

![RegMix 的 mixture 搜索与回归](/learning/cs336/lectures/l14-regmix.png)

![不同 data mixing 方法的比较](/learning/cs336/lectures/l14-data-mixing-methods.png)

## 11. Synthetic Data：从评价任务生成训练数据

进入 mid-training 和 post-training 后，数据管线不再只是筛选现有文本，还会主动生成样本。一个通用 recipe 是：

1. 定义 environment；
2. 定义 tasks 或 prompts；
3. 让强模型作为 teacher 生成多个 responses；
4. 过滤、验证并用于训练 student。

OpenThoughts 使用 QwQ-32B 作为 teacher，构造约 1.2M examples，问题来自 27 个 human 与 synthetic sources，包括 StackExchange、NuminaMath 和 chemistry。对每个 prompt 采样约 16 个回答有帮助，但更强的 benchmark 模型不必然是更好的 teacher：在这套 recipe 中，QwQ-32B 的教学效果优于 DeepSeek-R1。答案过滤也不一定有益，小而高质量的 OpenMath-2-Math 可能优于大而混杂的来源。

![OpenThoughts 的数据来源](/learning/cs336/lectures/l14-openthoughts-sources.png)

![OpenThoughts 的生成与筛选流程](/learning/cs336/lectures/l14-openthoughts-pipeline.png)

软件工程 synthetic data 更难，因为真实 repository 有依赖、环境、测试和状态。SWE-smith 给定 repository，让模型主动制造 bug 和任务，128 个 repository 生成约 50K tasks。SWE-rebench 则尽量使用真实 PR，构造约 21K interactive Python SWE tasks，来自约 3.4K repositories，并用模型协助安装依赖与判断 PR quality。

![SWE-smith 的任务生成流程](/learning/cs336/lectures/l14-swe-smith.png)

SWE-Zero 的观察是：一些强模型不需要真正执行 repository，也能凭借内部 code world model 解决不少任务。因此它生成约 300K 不依赖 repository-specific execution 的 agent trajectories 和约 150K GitHub PRs，用 OpenHands scaffold，并删除未来 commit 以避免 agent 通过查看答案作弊；另有约 13K 需要 execution feedback 的 SWE-Hero trajectories。

![SWE-Zero 不依赖执行反馈的路线](/learning/cs336/lectures/l14-swezero-noexec.png)

![SWE-Zero 的任务提示与约束](/learning/cs336/lectures/l14-swezero-prompt.png)

![SWE-Zero 的结果对比](/learning/cs336/lectures/l14-swezero-results.png)

后续把 SWE-Zero 扩展到约 12M trajectories，使用约 32K executable 和 120K non-executable tasks，再用较小的 mini-coder 与 scaffold 验证数据质量。这说明 synthetic data 的瓶颈不只在 teacher model，还在环境构建、执行成本、任务去重、轨迹验证和防止 reward hacking。

![SWE-rebench 的真实 PR 数据路线](/learning/cs336/lectures/l14-swe-rebench.png)

## 12. 把 Lecture 13、14 与 A4 串起来

Lecture 13 讲 raw source、crawl、版权和数据集来源；Lecture 14 讲如何做 transformation、filtering、deduplication 和 mixing。两讲合起来，才是一个可运行的 data pipeline：

$$
\text{GitHub / Web / Books / Papers}
\rightarrow
\text{dump}
\rightarrow
\text{representation}
\rightarrow
\text{filter}
\rightarrow
\text{dedup}
\rightarrow
\text{mix}
\rightarrow
\text{train}
$$

这也解释了 A4 的核心：训练实现通常已经固定，学生真正需要设计的是数据处理规则。以课程配置为例，若训练固定在 8 张 B200、16384 steps 和约 8.6B training tokens，那么每一个 rule 都要回答：保留什么能力、删除什么噪声、如何避免污染、如何控制数据重复，以及怎样在有限预算下验证改动是否有效。

Data filtering 可以理解成“定义什么是好数据”；deduplication 可以理解成“控制同一信息被重复放大的次数”；data mixing 可以理解成“规定不同能力在训练分布中的相对权重”；synthetic data 则是“主动制造更贴近 evaluation 和 post-training 目标的样本”。它们最终都必须回到 Lecture 12 的 evaluation：没有目标任务和可靠 eval，就没有办法判断某个 data rule 是否真的有效。

## 面试复盘

1. **Filtering 的统一抽象是什么？** 给定代表目标质量的 \(T\) 和大量 raw data \(R\)，学习 score function，从 \(R\) 中选择与 \(T\) 相似的子集 \(T'\)。

2. **为什么 filtering threshold 依赖训练规模？** 小预算需要高质量小池子，长训练需要更多长尾数据；固定 threshold 可能造成覆盖不足或高质量小池子过拟合。

3. **OpenMathText 说明了什么？** 规则、KenLM perplexity 和 fastText classifier 可以组合做领域过滤，少量高质量数学 token 可能胜过大量普通文本。

4. **为什么 deduplication 不只是节省硬盘？** 重复会改变训练分布、浪费 token、增加记忆与污染风险；但过度去重又可能删掉有价值的版本和互补上下文。

5. **Jaccard similarity 如何定义？** \(J(A,B)=|A\cap B|/|A\cup B|\)，用集合交集与并集衡量两个文档共享信息的比例。

6. **MinHash 的核心性质是什么？** 对随机 hash function，\(\Pr[h(A)=h(B)]=J(A,B)\)，因此多次碰撞比例可以估计 Jaccard。

7. **LSH 的碰撞概率公式是什么？** 把 \(n=b r\) 个 hash 分成 \(b\) 个 band、每 band \(r\) 个 hash，则 \(P=1-(1-s^r)^b\)。\(r\) 控制严格性，\(b\) 控制召回。

8. **为什么 data mixing 会发生 epoching？** 不同来源 token 数差异很大，给小来源较高采样概率会让它被反复使用；10B tokens 的来源在 1T 总训练量中很容易被重复几十次。

9. **UniMax、RegMix、Simulated Epoching 分别解决什么？** UniMax 用 epoch cap 防止小来源过拟合；RegMix 用小规模实验回归最优 mixture；Simulated Epoching 让小实验提前暴露大规模训练时的重复问题。

10. **Synthetic data 的最大瓶颈是什么？** 不只是 teacher model，还包括任务设计、环境依赖、执行成本、轨迹验证、数据去重与防止 agent 利用未来答案。

如果只能记住一句话，那就是：**数据算法不是训练前的杂务，而是在决定模型看到什么、重复什么、忽略什么，以及最终会表现出什么能力。**
