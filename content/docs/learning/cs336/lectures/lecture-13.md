---
title: "L13 · Data"
weight: 13
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "data"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture13/
---
Lecture 13 是 CS336 从“**模型工程**”切到“**数据工程**”的第一讲，而且我觉得它是整门课里最容易被低估的一讲。

Stanford 2026 官方课程表里，Lecture 13 是 5 月 11 日 Percy 主讲的 **Data (sources, datasets)**；Lecture 14 才进一步讲 **filtering、deduplication、mixing、synthetic data**。所以 Lecture 13 重点不是教你 MinHash 怎么写，而是先回答：

$$
\boxed{
\textbf{语言模型训练的那些万亿 token，
到底从哪里来？}
}
$$

官方讲义开头甚至直接说：

> **Data is the most important thing to get right in training language models.**

而且指出一个很有意思的行业现象：开放权重模型往往对 architecture、训练流程披露很多，对真正的数据细节却披露得很少，原因包括竞争优势和法律风险。

我会把整堂 Lecture 13 压成一个核心思想：

$$
\boxed{
\textbf{“The Internet” 不是训练集。
训练集是经过获取、许可、转换、筛选、去重和组合之后，
人为构造出来的一个概率分布。}
}
$$

---

# 一、为什么 Data 会直接决定模型是什么？

先不要谈 Common Crawl。

从你已经熟悉的语言模型 loss 开始：

$$
\mathcal L(\theta)
==================

\mathbb E_{x\sim p_{\text{data}}}
[-\log p_\theta(x)].
$$

你一直在优化：

$$
p_\theta.
$$

但注意 expectation 是对：

$$
\boxed{p_{\text{data}}}
$$

取的。

所以训练本质是在说：

> “请让模型在**我选择给你的这个数据分布**上表现得好。”

这意味着：

$$
\boxed{
\text{Architecture 决定模型能学什么，Data 决定模型被要求学什么。}
}
$$

如果数据里：

```text
50% 普通网页
30% code
10% math
10% papers
```

和：

```text
90% 普通网页
1% code
1% math
...
```

即使：

* Transformer 完全一样；
* optimizer 完全一样；
* FLOPs 完全一样；

最终能力也可以完全不同。

更数学一点，假设数据来自多个 source：

$$
p_{\text{train}}(x)
===================

\sum_s w_s p_s(x).
$$

那么梯度：

$$
\nabla_\theta\mathcal L
=======================

\sum_s
w_s
\mathbb E_{x\sim p_s}
[\nabla_\theta\ell(x)].
$$

所以所谓：

> “把 code 从 5% 提升到 20%”

不是一个无关紧要的数据处理参数。

它实际上是在：

$$
\boxed{\text{把 code gradient 的权重放大 4 倍。}}
$$

这就是为什么数据 mixture 本身可以理解成一种**训练目标设计**。

Lecture 13 最后的总结也直接说，data 是区分语言模型的关键 ingredient。

---

# 二、Lecture 13 先把训练过程分成三个数据阶段

官方讲义给了一个很实用的粗分类：

$$
\boxed{
\text{Pre-training}
\rightarrow
\text{Mid-training}
\rightarrow
\text{Post-training}
}
$$

其中 pre-training 主要是大量原始/通用文本；mid-training 更偏高质量、针对能力提升的数据；post-training 则进一步进入 chat transcripts、监督数据和 RL。讲义强调现实边界并不严格，但总体趋势是：

$$
\boxed{
\text{大量、较杂的数据}
\rightarrow
\text{更少、更高质量、更目标化的数据}
}
$$



这条趋势非常重要。

你可以把训练想成漏斗：

```text
            整个可访问世界
                  ↓
         大规模 pretraining
       海量、覆盖广、质量参差
                  ↓
             mid-training
        更小、更干净、更能力导向
                  ↓
            post-training
       少量、高价值、行为导向
```

于是三种阶段承担不同任务：

$$
\boxed{
\text{Pretrain：建立世界模型和语言能力}
}
$$

$$
\boxed{
\text{Mid-train：提高特定能力/数据质量}
}
$$

$$
\boxed{
\text{Post-train：塑造交互行为}
}
$$

这也解释了为什么今天“数据工程”不能只理解成：

> “爬网页”。

不同训练阶段需要的 data product 根本不同。

---

# 三、第一个最重要的纠正：“模型在整个 Internet 上训练”其实是错的

Lecture 13 专门纠正这句话。

互联网首先是一堆：

$$
\boxed{\text{live servers}}
$$

你访问：

```bash
curl https://cs336.stanford.edu/
```

得到的是某一刻服务器给你的响应。

但训练不能说：

> 每个 batch 临时访问几十亿个网站。

必须先：

$$
\boxed{\text{把 Web snapshot 下来。}}
$$

于是需要：

$$
\boxed{\text{Crawler}}
$$

Crawler 大致：

```text
seed URLs
   ↓
download page
   ↓
extract hyperlinks
   ↓
push new URLs into queue
   ↓
download...
```

官方 Lecture 13 把 crawler 定义为从 seed set 发现网页并下载网页。

所以第一步就已经发生了 selection：

$$
\boxed{
\text{World Wide Web}
\neq
\text{Crawled Web}
}
$$

你抓到什么，已经影响后面的模型。

---

# 四、为什么你根本不可能抓到“整个 Web”？

因为很多现代 Web 根本不是：

```text
GET URL → 一页静态 HTML
```

Lecture 13 把限制分成了好几类。

动态网站可能需要：

```text
点击
登录
提交表单
JavaScript interaction
```

很多大型平台和付费媒体处于 authentication / paywall 后面；网站还可能通过 robots.txt、rate limit、CAPTCHA、Cloudflare、防爬规则等限制 crawler；另外 Terms of Service 和版权/许可还形成法律层限制。

于是：

$$
\boxed{
p_{\text{web}}
\rightarrow
p_{\text{accessible web}}
\rightarrow
p_{\text{crawl}}
}
$$

每一步都会产生偏差。

比如特别容易 crawler 抓到的：

```text
SEO 网页
博客
静态文档
论坛
新闻
Wikipedia
```

可能被过度代表。

而：

```text
私密聊天
企业内部资料
付费数据库
动态应用
现实世界对话
```

天然少得多。

所以一个 base model 所谓：

> “学习了人类知识”

实际上更准确是：

$$
\boxed{
\text{学习了某套数据管线能观测到的人类数字痕迹。}
}
$$

这是非常重要的认识。

---

# 五、Common Crawl 到底是什么？

这就是现代开放预训练数据绕不开的基础设施。

Common Crawl 是一个非营利组织，定期抓取公开 Web 并公开 crawl archive。Lecture 13 用它作为核心 web source；例如 2026 年 4 月的官方 crawl 有 **21.9 亿网页，约 379.2 TiB 未压缩内容**。

注意：

$$
\boxed{\text{Common Crawl 本身还不是“干净的 LLM dataset”。}}
$$

它更像：

> 一个巨大的原矿。

里面有：

```text
网页正文
导航栏
cookie banner
广告
菜单
HTML
模板
乱码
重复网页
SEO spam
成人内容
机器生成文本
多语言
代码
错误页
...
```

这就是为什么：

$$
\boxed{
\text{Common Crawl}
\neq
\text{C4}
\neq
\text{FineWeb}
\neq
\text{DCLM}
}
$$

它们不是几个不同的网站。

而是：

> **对同类 raw web substrate 使用不同 data recipe 后得到的不同训练分布。**

---

# 六、WARC 和 WET 到底是什么？

这是 A4 真要碰的东西，所以应该搞懂。

Common Crawl 里重要的两个 representation：

### WARC

Web ARChive。

里面接近：

$$
\boxed{\text{raw HTTP response}}
$$

比如原始 HTML。

概念上：

```html
<nav>Home | News | Login</nav>

<div class="article">
  Transformer models...
</div>

<footer>Cookies...</footer>
```

---

### WET

已经经过文本提取后的结果：

```text
Transformer models...
```

所以：

$$
\boxed{\text{WARC = 更原始，信息更多}}
$$

$$
\boxed{\text{WET = 已转成 text，更方便，但有损}}
$$

官方讲义明确说 WET 是一种 lossy conversion，并指出 HTML→text 工具的选择会实际影响最终语言模型的 downstream accuracy。

这点极其值得理解。

---

# 七、为什么“HTML → Text”不是一个无聊的预处理步骤？

假设网页：

```html
<nav>
Products Pricing About Login
</nav>

<article>
The proof of the theorem proceeds...
</article>

<aside>
Related stories...
</aside>
```

你真正想要：

```text
The proof of the theorem proceeds...
```

但 parser 可能输出：

```text
Products Pricing About Login
The proof...
Related stories...
Accept cookies...
Copyright...
```

如果 trillion-token 规模上每一页都多一点 boilerplate：

$$
\boxed{\text{你最终真的会花大量 FLOPs 学导航栏和 cookie banner。}}
$$

再假设 parser 太激进：

```text
table → 丢掉
code block → 丢掉
equation → 丢掉
lists → 丢掉
```

那模型又失去有价值结构。

所以：

$$
\boxed{
\text{Text extraction 本身就是 information bottleneck。}
}
$$

DCLM 的工作也发现，仅仅更换 Common Crawl 文本提取方式，就能影响最终模型质量。

这也预告 Lecture 14：

> transformation 不是“先随便处理一下，再认真 filtering”。

**Transformation 本身就是 data quality。**

---

# 八、为什么不能只有 Web？专门数据源有什么用？

Lecture 13 接下来开始逐个看 specialized sources：

$$
\boxed{
\text{Wikipedia、GitHub、arXiv、Books、StackExchange...}
}
$$

每种 source 给模型的东西完全不同。

我给你一个最重要的“source → inductive bias”表：

| Source        | 主要价值                    | 先天问题                 |
| ------------- | ----------------------- | -------------------- |
| Common Crawl  | 规模、覆盖面、现实 Web 文本        | 极脏、重复、质量不均           |
| Wikipedia     | 高密度事实、百科式表达、多语言         | 风格单一、不是现实全部知识        |
| Books         | 长篇连贯文本、叙事、长程依赖          | 版权/许可复杂              |
| GitHub        | 代码、软件结构、开发文本            | fork/复制严重、license复杂  |
| arXiv         | 数学、科学、LaTeX、专业知识        | domain 偏、PDF/LaTeX转换 |
| StackExchange | 高质量问答、problem→answer 格式 | 社区偏差、重复、许可约束         |

官方 Lecture 13 分别介绍这些 source，并特别指出 GitHub 不只有源代码，还有 commits、issues、PR、comments 等 metadata；arXiv 还可能直接提供 LaTeX source；StackExchange 则有 votes、tags、comments 等质量信号。

这说明一个非常重要的概念：

$$
\boxed{\text{数据不只是 text，还有 metadata。}}
$$

---

# 九、Metadata 为什么可能比文本本身还值钱？

看 Reddit。

GPT-2 的 WebText 并不是：

> 随便抓整个互联网。

它用了一个很聪明的人类信号：

$$
\boxed{\text{Reddit links with ≥ 3 karma}}
$$

也就是说：

> 如果有人在 Reddit 分享这个网页，而且至少有一些人觉得它值得看，那它可能比随机网页质量高。

WebText 最终约 800 万网页、40 GB 文本。Lecture 13 把它作为早期 data curation 的经典案例。

这其实是在用：

$$
\boxed{\text{Human behavior as a quality classifier}}
$$

类似地：

StackExchange：

$$
\boxed{\text{upvote / score}}
$$

GitHub：

```text
stars
forks
issues
PRs
commit history
```

Wikipedia：

```text
编辑历史
引用
页面结构
```

所以你以后看到 raw source 时，不应该只问：

> “文本在哪？”

还要问：

$$
\boxed{\text{这个平台有没有免费的 quality signal？}}
$$

---

# 十、数据集历史其实是一部“我们到底认为什么是好数据”的历史

Lecture 13 后半基本是在带你走一遍这个演化。

我认为你不应该把它背成 dataset 名字，而应该看背后的哲学变化。

---

## BERT：Wikipedia + Books

早期 recipe 很朴素：

$$
\boxed{\text{有组织的高质量文本}}
$$

BERT 使用 Wikipedia 和 BooksCorpus；Lecture 13 还特意指出它处理的是 document-level sequences，而不是孤立句子。

核心信仰：

> 人写的百科 + 书，本身质量应该不错。

---

# 十一、GPT-2 WebText：让人类投票帮你筛 Web

哲学变成：

$$
\boxed{\text{Web 很大，但随机 Web 太差；先找人觉得值得看的网页。}}
$$

于是 Reddit karma 作为 proxy。

然后 OpenWebText 做了开放复现，加语言识别和近重复移除。

这是第一次很明显看到：

$$
\boxed{\text{source selection 本身就是 filtering。}}
$$

---

# 十二、CCNet：让“Wikipedia 风格”定义高质量

CCNet 做了三件很典型的事：

$$
\boxed{\text{deduplication}}
$$

$$
\boxed{\text{language identification}}
$$

以及：

$$
\boxed{\text{quality filtering}}
$$

它用 5-gram KenLM 判断 Common Crawl 文档在多大程度上像 Wikipedia，并据此筛选。

这里出现一个非常关键的问题：

> **为什么“像 Wikipedia”就等于高质量？**

因为 Wikipedia 通常：

```text
语法好
信息密度高
格式正规
垃圾少
```

但副作用是什么？

如果 classifier 只保留：

$$
\boxed{\text{Wikipedia-like}}
$$

那么：

```text
论坛
口语
小说
教程
非标准方言
特定文化文本
```

可能被误认为低质量。

所以：

$$
\boxed{\text{每个 quality classifier 都偷偷定义了“什么样的语言值得学习”。}}
$$

这不是纯技术问题。

---

# 十三、C4：规则派

T5 的 C4 从一个约 1.4T-token Common Crawl snapshot 出发，用大量 manual heuristics 清洗。

例如要求：

* 行有足够单词、像自然句子；
* 文档有足够句子；
* 去一些模板文本、代码特征；
* 做语言识别；
* 使用 bad-word list 等。

最后得到约 156B tokens。

C4 代表：

$$
\boxed{\text{Rule-based filtering}}
$$

好处是：

```text
透明
快
便宜
容易 debug
```

缺点：

$$
\boxed{\text{规则本身可能非常粗糙。}}
$$

例如：

> 看到 `{` 就扔。

那可能把高质量编程内容全部扔掉。

再比如 bad-word filtering：

> 一篇讨论性教育、医学、社会问题的高质量文章，也可能因为一个词整页被删除。

所以规则绝不“中立”。

---

# 十四、GPT-3：开始用 learned quality classifier

GPT-3 的训练数据混合了 processed Common Crawl、WebText2、books 和 Wikipedia；对 Common Crawl，则训练一个 classifier，让优质数据更像 WebText/Wikipedia/books，再做 fuzzy deduplication。官方 Lecture 13 报告其最终 corpus 约 400B tokens。

这代表另一个阶段：

$$
\boxed{
\text{Manual Rules}
\rightarrow
\text{Learned Quality Model}
}
$$

也就是从：

```python
if bad_word:
    reject
```

变成：

$$
q(x)=P(\text{high-quality}\mid x).
$$

然后：

$$
q(x)>\tau
\Rightarrow
\text{keep}.
$$

注意，模型里的“高质量”来自：

$$
\boxed{\text{positive examples 的定义}}
$$

所以核心问题又转移了：

> **谁来定义 positive set？**

---

# 十五、The Pile：既然一个 source 有偏差，那就明确做多 domain mixture

The Pile 是开放模型时代非常经典的数据工程项目。

它不再追求：

> “找一个最纯净的 Web corpus。”

而是主动收集多个 domain，包括 Common Crawl、PubMed、arXiv、Project Gutenberg、StackExchange、代码等，总计约 825GB / 275B tokens。

这代表：

$$
\boxed{\text{curated mixture}}
$$

哲学。

即：

> 世界不是只有“高质量网页”。

模型需要：

```text
science
books
code
Q&A
news
general web
...
```

所以你主动构建：

$$
p_{\text{train}}
================

\sum_iw_i p_i.
$$

到了这里，“data mixture weights”已经开始像模型超参数了。

---

# 十六、Gopher / LLaMA：工业 recipe 开始成熟

Gopher 的 MassiveText 把 Web、C4、Books、News、GitHub、Wikipedia 等组合起来，并做语言、去重、train-test overlap、quality/toxicity 等处理；值得注意的是，收集的数据远多于最终实际训练用的 tokens。

LLaMA 1 又采用了：

```text
Common Crawl / CCNet
C4
GitHub
Wikipedia
Books
arXiv
StackExchange
```

等来源，形成约 1.2T-token 训练数据。

你应该注意到一个趋势：

$$
\boxed{
\text{raw data pool}
\gg
\text{actual training data}
}
$$

这非常重要。

现代 data pipeline 不是：

> “我只有 1T token，所以全拿来训。”

而更像：

> “我手里有 100T、200T raw tokens，然后决定哪些 token 值得花昂贵 GPU FLOPs。”

数据 filtering 本质变成：

$$
\boxed{\text{Compute allocation problem}}
$$

---

# 十七、RefinedWeb / FineWeb：Web-only 路线又复兴了

Falcon 的 RefinedWeb 提出了一个很有意思的观点：

$$
\boxed{\text{Web data itself can be enough if you处理得足够好}}
$$

它从 Common Crawl WARC 做更好的文本提取，用 Gopher-like rules 和 MinHash fuzzy dedup；发布了数百 B token 量级数据。Lecture 13 随后介绍 FineWeb，后者处理了大量 Common Crawl snapshots，做 URL filtering、language ID、规则过滤、MinHash 去重和 PII 处理，形成约 **15T tokens** 的公开英文 Web corpus。

这背后的 lesson 是：

$$
\boxed{
\text{“Web 很垃圾”并不是 Web source 的宿命，
也可能是 processing pipeline 太差。}
}
$$

换句话说：

$$
\boxed{
\text{source quality}
\neq
\text{final dataset quality}
}
$$

---

# 十八、DCLM：这是 Data 研究非常关键的一步

DataComp-LM 做的事情特别值得理解。

过去论文：

> “我们做了一个新 filtering pipeline，最终模型不错。”

但不同论文：

```text
raw pool 不同
模型不同
compute 不同
evaluation 不同
```

根本不好比较。

DCLM 于是建立一个 standardized benchmark：

$$
\boxed{\text{固定 raw data pool + 固定训练框架 + 固定 eval}}
$$

让大家只比较：

$$
\boxed{\text{data curation algorithm}}
$$

它发布了一个从 Common Crawl 得到的约 **240T-token raw pool**，并通过统一训练和 53 个 downstream evaluations 比较不同 selection/filtering 方法。DCLM 的 baseline 实验显示 model-based filtering 是非常强的方法。

这件事有一个非常深的意义：

以前 benchmark：

$$
\boxed{\text{谁的 architecture 好？}}
$$

DCLM 问：

$$
\boxed{\text{谁的数据算法好？}}
$$

即：

$$
\boxed{\text{Data itself becomes an experimental variable.}}
$$

---

# 十九、DCLM 的 Quality Classifier 到底在干嘛？

Lecture 13 给出的例子很有意思。

Positive examples 来自偏高质量/指令式的数据，如 OpenHermes、ELI5；negative examples来自更普通的 RefinedWeb。然后训练一个 fastText classifier，在超大 DCLM raw pool 上打分、过滤。

粗略：

$$
q(x)
====

P(
\text{looks like useful high-quality text}
\mid x
).
$$

然后：

$$
x\in D_{\text{train}}
\iff
q(x)>\tau.
$$

这意味着一个 frontier data pipeline 可能是：

```text
几百 TB / PB raw data
        ↓
便宜 fast classifier
        ↓
只保留最值得训练的那部分
        ↓
GPU pretraining
```

为什么 classifier 必须便宜？

因为你可能要跑：

$$
\boxed{10^{14}\text{ 级 token}}
$$

任何 per-document scoring 如果太慢，data processing 自己就烧不起了。

这是典型：

$$
\boxed{\text{Data quality model 也需要 systems thinking。}}
$$

---

# 二十、但是 filter 越狠越好吗？Nemotron-CC 告诉你：不是

这就是 Lecture 13 很有现代感的一部分。

FineWebEdu、DCLM 类型的 high-quality filtering 可以非常激进。

问题是：

> 质量提高了，但 token 数突然不够了。

Lecture 13 对 Nemotron-CC 的概括就是：

$$
\boxed{\text{Need more tokens, but preserve quality.}}
$$

所以他们组合多个 classifier，并利用大模型给 Web 文档打教育价值分数、再 distill 成更快 scorer；同时对于低质量数据，还可以让语言模型进行 rephrasing，高质量数据则进一步生成 QA/task 等 synthetic variants。最终构成更大的数据池。

这里出现 Lecture 13 一个非常重要的 trade-off：

$$
\boxed{
\text{Quality}
\leftrightarrow
\text{Quantity}
}
$$

你不能把：

$$
q(x)>0.99999
$$

的文档全留下就宣布成功。

如果最后只有：

$$
50B\text{ tokens}
$$

但 Scaling Law 告诉你目标模型需要：

$$
10T\text{ tokens},
$$

那也不够。

---

# 二十一、所以数据 filtering 本质是一个 Pareto 问题

可以想象：

```text
average quality
     ^
     |   ● 非常高质，但只有 50B
     |
     |      ● 500B
     |
     |          ● 5T
     |
     |                ● 50T，质量一般
     +----------------------------> amount of data
```

你的目标不是：

$$
\max \text{average quality}
$$

也不是：

$$
\max \text{token count}
$$

而更接近：

$$
\boxed{
\min L_{\text{downstream}}
\quad
\text{s.t. fixed training compute}
}
$$

所以 Lecture 9 的 Scaling Laws 到这里又回来了。

如果你只有：

$$
100B\text{ token training budget}
$$

就可以极端挑精品。

如果你要：

$$
30T\text{ tokens},
$$

可能必须放宽 threshold、引入更多 domains、重复部分数据或 synthetic expansion。

这就是现代数据工程和 scaling engineering 接起来的地方。

---

# 二十二、Code Data 为什么应该单独看？

Lecture 13 专门讲 GitHub、The Stack、Stack v2，因为 code 绝不是“另一种普通文本”。

一个 repository 是：

```text
directories
files
imports
tests
commits
issues
pull requests
comments
documentation
```

你可以只把 `.py` 文件 dump 成文本。

但那就丢失了：

$$
\boxed{\text{软件工程结构}}
$$

The Stack v2 开始纳入：

* repositories；
* GitHub Archive issues/comments/PRs；
* Software Heritage；
* 文档站点；
* contests、StackOverflow、arXiv 等辅助数据；

并对 PR 这种 structured object 做 linearization，同时加入 diff 周围的上下文。

这很重要。

真正想训练 coding agent 时，目标数据可能不是：

```text
code completion
```

而是：

```text
Issue
↓
repository context
↓
patch
↓
review/comment
```

数据格式必须开始接近 downstream behavior。

---

# 二十三、这和 Lecture 12 的 Evaluation 完美接上了

Lecture 12 说：

> 先决定你想让模型会什么。

Lecture 13 回答：

> 那你就应该考虑什么数据能够产生这种能力。

例如目标 eval：

$$
\boxed{\text{SWE-Bench}}
$$

如果 pretraining data 只有：

```text
孤立 Python 文件
```

模型虽然会补代码，却不一定学会：

```text
issue → inspect repository → patch
```

如果加入：

```text
PR
issue
commit diff
code review
tests
```

数据结构就更接近真正 software engineering。

因此：

$$
\boxed{
\text{Evaluation defines desired behavior;
Data supplies training evidence for that behavior.}
}
$$

这就是为什么课程把：

$$
\boxed{\text{Lecture 12 Evaluation}}
$$

放在：

$$
\boxed{\text{Lecture 13–14 Data}}
$$

前面。

---

# 二十四、数据 Poisoning 为什么在这里突然出现？

Lecture 13 在 Wikipedia 部分特别提了 poisoning。

你可能觉得 Wikipedia 很高质量：

> 有管理员，错误会回滚。

但 crawler/dump 是：

$$
\boxed{\text{某个时间点的 snapshot}}
$$

攻击者可以：

```text
恶意修改网页
↓
刚好等 crawler/dump 抓到
↓
随后再被社区撤销
```

数据集里却可能已经永久留下。

官方用相关 data poisoning 工作提醒：

$$
\boxed{\text{even high-quality sources may contain bad content}}
$$



所以 data provenance 不只是：

> “这个 domain 靠谱吗？”

还要问：

```text
什么时候抓的？
谁改过？
版本是什么？
有没有 provenance？
```

这在未来数据供应链里会越来越重要。

---

# 二十五、Lecture 13 为什么花这么大篇幅讲版权？

因为：

$$
\boxed{\text{Can crawl}}
\neq
\boxed{\text{Can legally use however you want}}
$$

这是很多纯 ML 课程会跳过，但 CS336 故意放进来的现实问题。

Lecture 13 介绍了版权、许可、fair use、Terms of Service，以及围绕模型训练的美国诉讼。

这里我建议你不要把课件里的简化总结当成普遍法律结论。美国版权法下，生成式 AI training 的 fair-use 分析目前仍然是高度事实相关且持续发展的领域；美国版权局 2025 年 Part 3 报告也专门分析了 training data 与 fair use，而不是给出“所有 AI training 一律合法/非法”的简单答案。([美国版权局][1])

所以从 ML 工程角度，只要形成三个层次就够：

$$
\boxed{\text{publicly accessible}}
$$

不等于：

$$
\boxed{\text{permissively licensed}}
$$

也不等于：

$$
\boxed{\text{unrestricted for every use}}
$$

这三个概念一定要分开。

---

# 二十六、什么叫 Permissively Licensed Data？

这就是为什么 Lecture 13 最后讲 Common Pile。

过去：

> Web 大多数内容版权状态复杂。

那么有没有可能：

$$
\boxed{\text{只用 public-domain / openly licensed content 训练模型？}}
$$

Common Pile v0.1 专门探索这个问题：它构建了一个约 **8TB**、来自 30 个不同来源的 public-domain / openly licensed dataset，并训练 7B 模型验证这种路线的可行性。([arXiv][2])

Lecture 13 同时提醒这种做法也有 subtle issues：

```text
license laundering
collection-level license ≠ item-level license
synthetic data provenance
```

而且最大的现实问题之一仍然是：

$$
\boxed{\text{合法/开放的高质量 token 数够不够？}}
$$

官方课件的结论很直白：

> 可以做得不错，但没有足够 tokens 时很难和更大数据池竞争。

这又回到：

$$
\boxed{\text{quality × quantity × legality}}
$$

三者权衡。

---

# 二十七、所以 Dataset 不是一个 `.jsonl` 文件

这是我希望你真正形成的认知。

你看到：

```text
FineWeb
DCLM
Dolma
The Pile
```

不要想：

> “哦，这是几个下载链接。”

应该想：

$$
\boxed{\text{Dataset = Data pipeline + policy decisions}}
$$

完整过程大概是：

```text
Live world
   ↓
Acquisition / crawling
   ↓
Raw snapshots
   ↓
Representation conversion
   ↓
Language selection
   ↓
Quality selection
   ↓
Deduplication
   ↓
Safety / PII processing
   ↓
Source mixture
   ↓
Tokenization / packing
   ↓
Training stream
```

Lecture 13 总结得非常明确：

$$
\boxed{
\text{live service}
\rightarrow
\text{raw data}
\rightarrow
\text{processed data}
}
$$

并指出 transformation、filtering、deduplication 等 pipeline 大量依赖 heuristic，所以还有巨大的研究空间。

Lecture 14 才会把中间几个 processing box 真正拆开。

---

# 二十八、为什么“重复”不是简单的数据卫生问题？

Lecture 14 才会正式讲 dedup，但 Lecture 13 看到 GitHub forks、Web duplicates 后就应该提前理解这个数学事实。

假设训练集：

```text
Document A
Document B
Document C
```

经验风险：

$$
\hat L
======

\frac13
(
L_A+L_B+L_C
).
$$

如果 crawler 里 Document A 重复 100 次：

$$
\hat L
======

\frac{
100L_A+L_B+L_C
}{102}.
$$

所以重复实际上等价于：

$$
\boxed{\text{隐式增加该文档的 sampling weight}}
$$

模型不是在浪费一点 compute 那么简单。

而是：

> 你不知不觉改变了训练 objective。

这就是为什么 GitHub fork、新闻转载、SEO mirrors、网页模板等 duplication 会真正改变模型。

---

# 二十九、这也是为什么“数据越多越好”是错的

假设 Dataset A：

$$
1T
$$

unique useful tokens。

Dataset B：

$$
5T
$$

tokens。

但其中：

```text
1T useful
4T spam / duplicates / boilerplate
```

从磁盘上看：

$$
B=5\times A.
$$

从有效训练信息看，不一定。

甚至：

$$
\boxed{\text{B 可能更差}}
$$

因为你花：

$$
4T\times6N
$$

FLOPs 学没有价值的内容。

这就是现代数据 curation 的经济学：

$$
\boxed{\text{每一个 token 都要问：值得花 GPU FLOPs 学它吗？}}
$$

DCLM 的结果尤其体现这一点：通过更好的 data curation，7B 模型可以在明显更少训练 compute 下达到非常有竞争力的 benchmark 表现。([arXiv][3])

---

# 三十、Lecture 13 最有意思的历史趋势，其实可以压成四代

我会这样记，而不是背十几个 dataset 名：

```text
第一代：
Curated sources
Wikipedia + books
        ↓
第二代：
Heuristic Web filtering
WebText / CCNet / C4
        ↓
第三代：
Large multi-source mixtures
GPT-3 / Pile / Gopher / LLaMA
        ↓
第四代：
Data algorithm engineering
RefinedWeb / FineWeb
DCLM / Nemotron-CC
The Stack v2 / Common Pile
```

这里每一代的核心问题依次是：

$$
\boxed{\text{哪里有好文本？}}
$$

↓

$$
\boxed{\text{怎样从垃圾 Web 中找好文本？}}
$$

↓

$$
\boxed{\text{怎样组合不同能力域？}}
$$

↓

$$
\boxed{\text{怎样系统优化整个 data recipe？}}
$$

这就是 Lecture 13 真正的历史脉络。

---

# 三十一、Lecture 13 和 Lecture 9 Scaling Laws 的连接

Lecture 9：

$$
C\approx6ND.
$$

假设你决定：

$$
D=10T\text{ tokens}.
$$

这不是结束。

真正的问题是：

$$
\boxed{\text{哪 10T？}}
$$

因为：

$$
10T_{\text{spam}}
$$

和：

$$
10T_{\text{high-quality math/code/web}}
$$

在公式中都是：

$$
D=10T.
$$

Scaling Law 的 (D) 看似只是数字，但实际上每个 token 的 information value 不一样。

所以更加真实的概念应该是：

$$
\boxed{\text{effective data}}
$$

而不只是 raw token count。

Lecture 13 正是在告诉你：

> Scaling Law 的 (D) 后面，藏着一整套 data pipeline。

---

# 三十二、Lecture 13 和 A4 是什么关系？

官方 2026 Assignment 4 就叫 **Data**。课程网站描述它要求学生把 raw Common Crawl dumps 转成可用的 pretraining data；官方 repo 中 `cs336_basics` 已经给你固定训练实现，而你的工作主要放在 `cs336_data`，也就是说刻意固定模型和 training code，让你专注研究：

$$
\boxed{\text{同一个模型，同样训练预算，谁的数据 pipeline 更好。}}
$$

2026 A4 甚至把最终训练固定为 **8 张 B200、16,384 steps、约 8.6B tokens**，让 leaderboard 尽可能变成 data quality competition，而不是“谁模型更大”。

这其实就是 DCLM 精神的小型版。

---

# 三十三、因此你做 A4 时真正的思维方式不应该是

```text
下载 WET
↓
写几个 if
↓
输出 jsonl
↓
完成
```

而应该是：

$$
\boxed{\text{我只有固定的 token budget。}}
$$

假设 raw pool：

$$
100B\text{ tokens}.
$$

训练只能吃：

$$
8.6B.
$$

那么你的任务变成：

$$
\boxed{
\text{从 100B candidates 中，
挑出最值得模型花 FLOPs 学习的 8.6B。}
}
$$

这已经很像一个：

$$
\boxed{\text{ranking / retrieval problem}}
$$

甚至可以写：

$$
s(x)
====

f(
\text{language},
\text{quality},
\text{domain},
\text{toxicity},
\text{duplication},
\dots
).
$$

然后：

$$
\boxed{\text{select top / sample according to }s(x)}
$$

Lecture 14 就会正式进入这些算法。

---

# 三十四、我给 Lecture 13 一个最重要的四层框架

以后读任何模型 technical report 的 data section，都可以用它分析：

| 层                  | 核心问题         | 示例                                  |
| ------------------ | ------------ | ----------------------------------- |
| **Source**         | 数据原来在哪里？     | Web、Books、Code、Papers               |
| **Access**         | 能不能得到？能不能用？  | Crawl、API、dump、license              |
| **Representation** | 怎样变成模型可吃的文本？ | HTML→text、PDF→text、PR linearization |
| **Selection**      | 哪些值得花算力训练？   | quality/language/dedup/mixing       |

Lecture 13 主要解决前三层 + 历史 dataset recipes。

Lecture 14 会重点深入第四层。([GitHub][6])

---

# 三十五、最后给你 10 道 Lecture 13 自测题

1. **为什么“LLM 在 Internet 上训练”是不严谨的？**
   必须说出 live Web → crawl → snapshot → processing → selected corpus。

2. **WARC 与 WET 有什么区别？**
   一个更接近 raw HTTP/HTML，一个已经文本化且有损。

3. **为什么 HTML-to-text converter 的选择可以影响 benchmark？**
   因为它改变真正进入 loss 的信息，而不仅仅改变存储格式。

4. **为什么 Common Crawl 不是一个现成的 LLM dataset？**
   因为 raw crawl 含大量 boilerplate、重复、垃圾、多语言等，需要进一步 processing。

5. **WebText 为什么体现了一种巧妙的数据质量思想？**
   它用 Reddit 人类行为作为 quality proxy。

6. **CCNet/C4/GPT-3 filtering 哲学有什么区别？**
   CCNet 偏“像 Wikipedia”的统计质量模型；C4 主要用规则；GPT-3 开始使用 learned quality classifier。

7. **为什么 quality classifier 不是客观真理？**
   因为 positive/negative data 的选择实际上定义了“什么叫好文本”。

8. **为什么 deduplication 会改变训练 objective，而不仅仅节约算力？**
   因为重复 (k) 次等价于把样本权重放大 (k) 倍。

9. **为什么高质量 filter 不能无限严格？**
   因为最终需要足够 tokens；存在 quality–quantity trade-off。

10. **为什么 DCLM 是数据研究的重要进展？**
    因为它尽量固定 raw pool、training recipe 和 eval，让“数据处理算法”成为主要实验变量。([arXiv][3])

---

# 最后，把 Lecture 13 压成一块黑板

第一行：

$$
\boxed{
\mathcal L(\theta)
==================

\mathbb E_{x\sim p_{\text{data}}}
[-\log p_\theta(x)]
}
$$

**你选择什么数据，就选择了模型被优化去模仿什么世界。**

第二行：

$$
\boxed{
\text{Internet}
\neq
\text{Common Crawl}
\neq
\text{Training Dataset}
}
$$

第三行：

$$
\boxed{
\text{Live source}
\rightarrow
\text{raw snapshot}
\rightarrow
\text{text representation}
\rightarrow
\text{selected training data}
}
$$

第四行：

$$
\boxed{
\text{Quality}
\leftrightarrow
\text{Quantity}
\leftrightarrow
\text{Diversity}
\leftrightarrow
\text{Legal/ethical constraints}
}
$$

最后一行，我认为是整堂 Lecture 13 真正最重要的结论：

$$
\boxed{
\textbf{Data does not fall from the sky.}
}
$$

所谓一个“15T-token dataset”，并不是互联网上本来就躺着一个 `15T.jsonl` 等你下载。

它是无数人为决定累积出来的：

> 抓哪些网站、抓哪个时间点、哪些内容拿不到、HTML 怎么抽正文、什么语言留下、什么算“高质量”、什么被删掉、哪些 source 被加权、哪些文本有许可、哪些内容被去重……

**这些决定合在一起，本身就是模型设计。**

这也解释了为什么 Lecture 14 紧接着要讲 filtering、deduplication、mixing 和 synthetic data：Lecture 13 告诉你“原矿从哪来”；Lecture 14 才真正教你**怎么把几百 T raw tokens 炼成值得拿昂贵 GPU 去训练的那几 T tokens**。
