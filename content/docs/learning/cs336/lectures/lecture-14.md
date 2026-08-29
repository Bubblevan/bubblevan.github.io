---
title: "L14 · Data Selection"
weight: 14
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "data", "filtering"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture14/
---

Lecture 14 可以说是 **CS336 Data 部分真正进入“算法”的一讲**。

2026 官方课程表把 Lecture 14 定义为 **Data (filtering, deduplication, mixing, synthetic data)**。官方 `lecture_14.py` 的执行顺序非常明确：

[
\boxed{
\text{Transformation}
\rightarrow
\text{Filtering}
\rightarrow
\text{Deduplication}
\rightarrow
\text{Data Mixing}
\rightarrow
\text{Synthetic / Post-training Data}
}
]

Lecture 13 告诉你 Common Crawl、GitHub、arXiv、Books 等“原矿”从哪里来；Lecture 14 则真正回答：

[
\boxed{
\textbf{假设我手里已经有 100T raw tokens，
到底哪几个 token 值得我花昂贵 GPU FLOPs 去学？}
}
]

官方总结本身也就是：filtering 用 classifier 定义什么是好数据；dedup 用 hashing 把 fuzzy matching 扩展到巨型数据集；mixing 用小规模实验预测更大的最优 mixture；post-training 数据则越来越像 evaluation task，并大量依赖 synthetic data。

---

# 1. 先抓住 Lecture 14 的统一视角：Data Selection

这一讲虽然表面上有四五个主题，其实所有东西都可以统一成：

[
\boxed{
\text{我们想让训练分布 }p_{\text{train}}
\text{长成什么样？}
}
]

回到 LM loss：

[
\mathcal L(\theta)
==================

\mathbb E_{x\sim p_{\text{train}}}
[-\log p_\theta(x)].
]

Lecture 13 已经告诉你，数据来源决定 (p_{\text{train}})。

Lecture 14 更进一步：

> **即使 raw corpus 固定，你仍然可以通过 transformation、filtering、dedup、sampling weights，把它变成完全不同的训练分布。**

例如原始数据：

[
R=
{
\text{Wikipedia},
\text{spam},
\text{code},
\text{math},
\text{forums}
}.
]

你做 filtering：

[
q(x)>0.8
]

其实在修改：

[
p(x).
]

你把 code 权重从：

[
0.05\rightarrow0.20
]

也是修改：

[
p(x).
]

一个网页重复 100 次却没 dedup，又是在偷偷让：

[
p(x)\times100.
]

因此：

[
\boxed{
\textbf{Data pipeline 本质是 loss function 的隐式设计。}
}
]

这比“数据清洗”四个字准确得多。

---

# 2. Transformation：为什么“先把 HTML 变成文本”也算 Data Algorithm？

Lecture 14 第一部分延续 Lecture 13：

raw data 根本不是天然的纯文本。

它可能是：

[
\boxed{\text{HTML}}
]

也可能是：

[
\boxed{\text{PDF}}
]

或者一个：

[
\boxed{\text{Git repository directory tree}}.
]

HTML → text 必须决定：导航栏删不删、广告删不删、table 怎么表示、图片怎么办、代码块怎么办；PDF 还涉及 OCR、reading order、公式、表格和 layout。官方特别强调这种转换天然是 **lossy** 的，而且 DCLM 的实验已经说明 text extraction accuracy 会影响最后语言模型质量。2026 讲义还用 FinePDFs 举例：PDF 可能需要重新抓取、OCR/VLM/Docling 等工具以及大量后处理。

所以你不能把：

```text
HTML → text
```

看作：

> “工程师写个 parser 就完事。”

它真正做的是：

[
\boxed{
\text{决定原始世界里的哪些结构最终进入 Transformer。}
}
]

举个极端例子。

原网页：

```html
<h1>Pythagorean Theorem</h1>

<p>For a right triangle...</p>

<table>
...
</table>

<pre>
a**2 + b**2 == c**2
</pre>
```

Extractor A 得到：

```text
Pythagorean Theorem
For a right triangle...
```

Extractor B 得到：

```text
Pythagorean Theorem
For a right triangle...
Table:
...
a**2 + b**2 == c**2
```

它们抓的是同一个网站。

但从模型角度：

[
\boxed{\text{这已经是两个不同 dataset。}}
]

---

# 3. Filtering：整堂课最重要的抽象之一

Percy 在 Lecture 14 给出了一个非常干净的算法框架。

你有大量 raw data：

[
\boxed R
]

再准备一小批你认为“好”的 target data：

[
\boxed T.
]

目标：

[
\boxed{
\text{从 }R\text{ 中找到一个子集 }T'
\text{，使它像 }T.
}
]

官方明确把这个框架用于三类任务：

[
\text{Language Identification}
]

[
\text{Quality Filtering}
]

[
\text{Toxicity Filtering}.
]

而 filtering algorithm 有两个重要要求：必须能从 (T) 泛化，不能简单记住 target examples；还必须**极快**，因为它要跑过巨大的 (R)。

这可以写成一个 scorer：

[
s(x)
====

\text{“x 有多像 target data?”}
]

然后：

[
x\text{ kept}
\iff
s(x)>\tau.
]

---

# 4. 这个 scorer 可以怎么做？

Lecture 14 给了两个经典方向。

## 生成式模型

训练一个只描述 target distribution 的模型：

[
p_T(x).
]

例如 KenLM。

定义：

[
\boxed{
s(x)=p_T(x)
}
]

或者更常见用：

[
-\operatorname{PPL}_T(x).
]

如果 target 是数学论文：

> 一个文本在数学语言模型下 perplexity 很低，说明它很“像数学”。

---

## 判别式模型

准备：

[
x\sim T
]

作为正样本，

[
x\sim R
]

作为负样本。

训练：

[
\boxed{
s(x)
====

P(y=\text{target}\mid x).
}
]

例如 fastText、linear classifier、random forest。

官方正是以 KenLM 和 fastText 分别代表这两种 filtering 方法。

---

# 5. 这里有个很深的问题：谁定义“High Quality”？

假设你的 positive set：

[
T=
\text{Wikipedia}.
]

那么 classifier 学到的是：

[
\boxed{\text{Wikipedia-like}}
]

而不是某种神定义的：

[
\boxed{\text{objective quality}}.
]

如果 (T) 是教材：

classifier 可能偏好：

```text
结构清晰
正式语言
教学式解释
```

如果 (T) 是 Reddit：

它又会喜欢完全不同的东西。

所以：

[
\boxed{
\textbf{Filtering classifier 的 label 本质上是一种价值判断。}
}
]

你不是发现了“好数据”。

而是：

> **首先定义什么叫好，然后把这个定义外推到几百 T raw tokens。**

这就是为什么 Lecture 14 的总结不是“训练一个 powerful classifier”，而是：

[
\boxed{
\text{define target data — what good looks like}
}
]

再向 raw data extrapolate。

---

# 6. Language ID 就是最简单的 Filtering

假设目标：

[
\boxed{\text{只训练英文模型}}
]

那么：

[
T=\text{English}.
]

用 fastText language ID：

[
P(\text{English}\mid x).
]

例如：

[
P=0.97
]

留下；

[
P=0.13
]

删除。

官方讲义引用的 fastText language identification 支持 176 种语言；Dolma 采用过类似 (P(\text{English})\ge0.5) 的规则。

这里最容易误解的是：

> Language ID 很简单，所以不会有什么偏差。

其实也会。

比如：

```text
English paragraph
+
Python code
+
Chinese comment
```

到底属于哪一种？

又比如公式密集的数学文本：

```text
Let f : R^n → R ...
```

language classifier 可能置信度很低。

所以 threshold：

[
\tau
]

永远是：

[
\boxed{\text{precision-recall tradeoff}}.
]

---

# 7. OpenMathText 是一个特别漂亮的例子

目标不是：

> “找高质量文本。”

而是更具体：

[
\boxed{\text{从 Common Crawl 找数学文本。}}
]

Lecture 14 展示的 pipeline 大概是：

规则先找 LaTeX 等数学信号；

再训练一个基于 ProofPile 的 KenLM，通过 perplexity 衡量文本有多像数学 corpus；

再训练 fastText classifier 判断 mathematical writing。最终整理出约 14.7B tokens；讲义引用的结果显示，用这些数据训练的 1.4B 模型可以超过使用远更多数据的一些 baseline。

这件事最值得学的是：

[
\boxed{
14.7B\text{ relevant tokens}
\quad\text{可能比}\quad
300B\text{ random tokens}
\text{ 更有价值。}
}
]

所以：

[
\boxed{\text{Token count} \neq \text{information value}.}
]

---

# 8. GPT-3 / LLaMA 的 Filtering 又是什么思路？

GPT-3 的 positive data 来自：

[
{\text{Wikipedia, WebText2, Books1, Books2}}
]

negative：

[
\text{generic Common Crawl}.
]

训练一个基于文本特征的 classifier，然后不是简单 hard threshold，而根据质量分数进行**随机保留**。Lecture 14 直接展示了对应的 stochastic selection 代码。

为什么 stochastic filtering 有意义？

假设：

[
s(x)=0.79
]

和：

[
s(y)=0.80.
]

hard threshold：

```text
x：扔
y：留
```

但它们明明几乎一样。

随机 sampling：

[
P(\text{keep}\mid x)=f(s(x))
]

可以避免这样一个生硬的 cliff，同时保留一些 distribution diversity。

这和 RL 里：

[
\boxed{\text{soft weighting vs hard selection}}
]

是同一种直觉。

---

# 9. Phi-1 更进一步：让大模型帮你定义“教育价值”

Lecture 14 的 phi-1 例子特别像现代 data flywheel。

Raw：

[
R=\text{The Stack 中的 Python}.
]

先让 GPT-4 判断 100K 样本：

> “对于一个学习基础编程概念的学生，这段代码的教育价值如何？”

于是 GPT-4 生成昂贵但高质量 labels。

然后不用 GPT-4 去扫整个 dataset——太贵。

而是训练一个便宜 classifier，再把它扩展到全部 raw data。讲义给出的实验中，同样 1.3B 模型，用 filtered subset 训练更少 steps，HumanEval 反而从约 12.19% 提高到 17.68%。

这个模式特别重要：

```text
强模型
 ↓ expensive labels on small subset
便宜 student scorer
 ↓
巨大 raw corpus
 ↓
filtered corpus
```

即：

[
\boxed{
\text{Teacher model}
\rightarrow
\text{data-label distillation}
\rightarrow
\text{cheap scalable filter}
}
]

今天很多数据管线其实都在玩这个。

---

# 10. Filtering 最反直觉的一点：最佳 threshold 会随训练规模改变

这是 Lecture 14 和 Lecture 9 Scaling Laws 直接连接的地方。

官方明确写：

[
\boxed{\text{不存在一个永远最优的 filtering threshold}}
]

短训练：

> 更希望留下少量最高质量数据。

长训练：

> 必须接受更多质量略低的数据，否则高质量小 corpus 会被重复很多 epochs。

假设 raw data 中：

[
D_{\text{gold}}=10B
]

超高质量 tokens。

模型只训练：

[
D_{\text{train}}=5B.
]

完全可以只吃 gold。

但如果要训练：

[
1T.
]

仍只使用 10B gold：

[
\text{epochs}
=============

# \frac{1T}{10B}

100.

]

这时候：

[
\boxed{\text{质量非常高}}
]

却因为：

[
\boxed{\text{重复 100 遍}}
]

带来 overfitting / memorization / diminishing returns。

所以最佳 threshold 实际是：

[
\boxed{
\tau^*
======

f(\text{training token budget})
}
]

这是一条非常深的结论。

---

# 11. Deduplication：为什么它不是简单“节约硬盘”？

假设数据：

[
D={A,B,C}.
]

那么：

[
L
=

\frac13
(L_A+L_B+L_C).
]

如果 A 重复 100 次：

[
L
=

\frac{
100L_A+L_B+L_C
}{102}.
]

也就是说：

[
\boxed{
\text{duplicate}
================

\text{implicit sample reweighting}
}
]

于是模型会被迫：

> “这个 A 极其重要，请你学习 100 遍。”

所以 Dedup 并不只是：

[
\boxed{\text{减少数据量}}
]

而是在：

[
\boxed{\text{纠正意外的训练权重。}}
]

官方 Lecture 14 区分 exact duplicate 和 near duplicate，并引用经典研究说明去重不仅让训练更高效，也降低 memorization。对应论文还报告，dedup 后模型逐字复述训练数据的情况可大幅下降，并能减少 train-test overlap。

---

# 12. Exact Dedup 最简单怎么做？

假设：

```python
items = [
    "hello",
    "bye",
    "hello",
]
```

不要做：

[
O(N^2)
]

两两比较。

为每个 item 算：

[
h(x).
]

例如：

[
h(\text{"hello"})=12345.
]

然后按 hash group：

```text
12345 → hello, hello
93728 → bye
```

每组只留一个。

Lecture 14 用 MurmurHash 演示这种做法，而且特意把代码写成一种容易 MapReduce/parallelize 的风格。

核心复杂度从 naive：

[
\boxed{O(N^2)}
]

变成接近：

[
\boxed{O(N)}
]

或排序情况下：

[
O(N\log N).
]

这对于：

[
10^{10}
]

documents 才有意义。

---

# 13. 但“什么东西算一个 item”本身就是设计选择

Lecture 14 专门把 Dedup 的 design space 拆成三个问题：

[
\boxed{\text{item 是什么？}}
]

sentence？

paragraph？

document？

然后：

[
\boxed{\text{怎样算重复？}}
]

exact？

共享一部分？

Jaccard 超过 threshold？

最后：

[
\boxed{\text{检测到重复以后做什么？}}
]

全部删除？

还是只留一份？

这非常重要。

假如两个 5000-word documents：

只有其中三个句子一样。

Document-level exact dedup：

> 完全检测不到。

Sentence-level exact dedup：

> 可以删掉这三个句子。

但删完以后原文可能变成：

```text
第一段介绍背景。
[中间三句被删除]
因此，根据上述定义……
```

语义突然断掉。

官方就用 C4 的 3-sentence span dedup 提醒了这种 coherence 问题。

所以：

[
\boxed{\text{Dedup granularity 本身会改变文档质量。}}
]

---

# 14. Exact Dedup 不够：网页世界大量是 Near Duplicate

例如：

Document A：

```text
Copyright 2025.
Our product has free shipping.
Contact us...
```

Document B：

```text
Copyright 2026.
Our product has free shipping!
Contact us...
```

只改两个字符。

Exact hash：

[
h(A)\neq h(B).
]

但人一看：

[
\boxed{\text{基本是同一份东西。}}
]

所以必须引入：

[
\boxed{\text{similarity}}
]

---

# 15. Jaccard Similarity 必须掌握

假设把一个 document 表示成一个 set (A)。

另一个：

[
B.
]

Jaccard：

[
\boxed{
J(A,B)
======

\frac{|A\cap B|}
{|A\cup B|}
}
]

Lecture 14 的例子：

[
A={1,2,3,4}
]

[
B={1,2,3,5}.
]

交集：

[
|A\cap B|=3.
]

并集：

[
|A\cup B|=5.
]

所以：

[
\boxed{
J(A,B)=\frac35=0.6
}
]

然后定义：

[
\boxed{
J(A,B)\ge\tau
\Rightarrow
\text{near duplicate}
}
]

问题来了：

> 我有十亿篇网页，还是不能两两算 Jaccard。

因为仍然：

[
O(N^2).
]

于是出现整讲最重要的算法：

[
\boxed{\text{MinHash}}
]

和：

[
\boxed{\text{LSH}}
]

。

---

# 16. MinHash 为什么如此神奇？

MinHash 的性质：

[
\boxed{
P[h(A)=h(B)]
============

J(A,B)
}
]

第一次看到会觉得这是什么魔法。

其实证明非常漂亮。

想象 universe：

[
U=A\cup B.
]

对 (U) 做一个随机排列。

定义：

[
h(A)
====

\text{排列中最先出现在 A 的元素}.
]

同理：

[
h(B).
]

什么时候：

[
h(A)=h(B)?
]

答案是：

> (A\cup B) 中排列最靠前的那个元素，必须属于 (A\cap B)。

由于随机排列下，并集里的每个元素成为“第一个”的概率相同：

[
P[h(A)=h(B)]
============

\frac{|A\cap B|}
{|A\cup B|}
===========

J(A,B).
]

所以：

[
\boxed{
\text{我们把一个昂贵的 set similarity，
变成了一个 hash collision probability。}
}
]

这就是 MinHash 的核心。官方 Lecture 14 就通过 characteristic matrix / 随机 permutation 的方式推导这一性质。

---

# 17. 一次 MinHash 还是太随机怎么办？

如果：

[
J=0.8
]

那么一次 MinHash：

[
P(\text{collision})=0.8.
]

但你仍有：

[
20%
]

概率错过。

于是做：

[
n=100
]

个 independent MinHash。

统计：

[
\frac{
#\text{matching hashes}
}{n}.
]

根据大数定律：

[
\boxed{
\hat J
\approx
J.
}
]

官方代码就是生成 100 个不同 seed 的 MinHash，然后用 collision fraction 近似 Jaccard。

但是我们仍有一个问题：

> 如果每篇 document 都有 100 个 signatures，怎么快速找“Jaccard > 0.8”的 pair？

总不能还是全部 pairs 对比 signatures。

所以还有最后一步：

[
\boxed{\text{Locality Sensitive Hashing}}
]

---

# 18. LSH 是 Lecture 14 最需要亲手推的公式

现在有：

[
n=b\times r
]

个 MinHash values。

分成：

[
b
]

个 bands，

每个 band：

[
r
]

个 hashes。

例如：

```text
h1 h2 h3 h4 | h5 h6 h7 h8 | h9 h10 h11 h12
```

也就是：

[
b=3,\quad r=4.
]

定义：

> 如果**至少一个 band**里，A 和 B 的所有 (r) 个 hash 都完全相同，就把它们当 candidate pair。

这是：

[
\boxed{\text{OR of ANDs}}
]

结构。

---

# 19. LSH 的 collision probability 怎么推？

假设两篇文档真实 Jaccard：

[
s.
]

一个 MinHash 相等的概率：

[
s.
]

一个 band 里 (r) 个全部相等：

[
\boxed{s^r}
]

因为要求全部 match。

一个 band 不 match：

[
1-s^r.
]

所有：

[
b
]

个 bands 都不 match：

[
(1-s^r)^b.
]

所以至少一个 band match：

[
\boxed{
P_{\rm candidate}(s)
====================

1-(1-s^r)^b
}
]

这就是 Lecture 14 官方推导的 LSH 核心公式。

---

# 20. 为什么这个公式可以制造一个“近似 threshold”？

假设 (r) 很大。

如果：

[
s=0.5
]

那么：

[
s^{20}
]

已经非常小。

但：

[
s=0.95
]

时：

[
s^{20}
]

仍然不算太小。

于是：

[
1-(1-s^r)^b
]

会变成一种 S-shaped curve：

```text
collision probability
1 |                   _______
  |                __/
  |              _/
  |            _/
0 |___________/
  +------------------------ similarity
              ^
          threshold-ish
```

大概 threshold：

[
\boxed{
s_0
\approx
\left(\frac1b\right)^{1/r}
}
]

Lecture 14 就直接推到了这个式子。

---

# 21. (r) 和 (b) 分别控制什么？

提高：

[
r
]

意味着一个 band 要同时命中更多 hashes。

所以：

[
\boxed{\text{更难成为 candidate}}
]

curve 往右移、threshold 更严格。

提高：

[
b
]

意味着你有更多 band 可以“碰巧”匹配。

所以：

[
\boxed{\text{更容易成为 candidate}}
]

curve 往左移。

因此：

[
\boxed{
r\approx\text{precision knob}
}
]

[
\boxed{
b\approx\text{recall knob}
}
]

虽然严格来说 precision/recall 还取决于数据分布，但作为直觉非常好。

你终于可以通过：

[
(b,r)
]

控制 near-dedup aggressiveness。

---

# 22. 把 Dedup 整体串起来

现在你应该能看到完整管线：

```text
Document
   ↓
normalize / tokenize
   ↓
convert to set of shingles / features
   ↓
many MinHashes
   ↓
split signature into bands
   ↓
LSH bucket
   ↓
only compare candidate pairs
   ↓
calculate actual similarity
   ↓
remove duplicates
```

最核心的思想不是 MinHash 这个名字。

而是：

[
\boxed{
\textbf{不能解决 }O(N^2)\textbf{ 的比较问题，
就无法在互联网规模做 Data Engineering。}
}
]

这和 Lecture 5–8 的 systems 思维完全一样：

> 数学正确还不够，必须能 scale。

---

# 23. Data Mixing：又一个经常被低估的“超参数”

假设数据源：

[
S=
{
\text{Wikipedia},
\text{Common Crawl},
\text{GitHub}
}.
]

你必须定义：

[
\boxed{
p(s)
}
]

例如：

[
p(\text{Wiki})=0.3
]

[
p(\text{CC})=0.5
]

[
p(\text{GitHub})=0.2.
]

那么每次采样 token/document 时：

[
s\sim p.
]

这就是：

[
\boxed{\text{data mixture}}
]

官方 Lecture 14 明确把“不同 data source 的 sampling distribution 应该是什么”作为核心问题。

---

# 24. 最简单的三种 baseline

可以人工凭经验：

[
p(s)=\text{vibes}.
]

也可以 uniform：

[
\boxed{
p(s)=\frac1{|S|}
}
]

或者 proportional：

[
\boxed{
p(s)
====

\frac{D_s}
{\sum_jD_j}
}
]

其中：

[
D_s
]

是该 source 的 token 数。

官方讲义非常幽默地把第一种直接叫 **Vibes**，并承认现实中相当常见。

但三个方法都不理想。

因为：

> 高质量小 source 理论上应该 upweight。

然而如果 upweight 太多，又会出现另一个问题。

---

# 25. Epoching 是 Data Mixing 最大的隐藏坑

官方给了一个非常好的数字例子。

假设：

[
D_{\rm low}=10T
]

低质量但丰富的数据。

[
D_{\rm high}=10B
]

高质量但稀缺的数据。

你总共训练：

[
D_{\rm train}=1T.
]

然后天真设置：

[
p_{\rm low}=0.5,
\quad
p_{\rm high}=0.5.
]

高质量 source 会被采：

[
0.5T=500B.
]

但它实际只有：

[
10B.
]

所以：

[
\boxed{
\text{epochs}_{high}
====================

# \frac{500B}{10B}

50
}
]

而 low source：

[
\text{epochs}_{low}
===================

# \frac{500B}{10T}

0.05.
]

也就是说：

```text
Low quality：只看 5%
High quality：看 50 遍
```

官方直接提醒：

[
\boxed{\text{50 epochs on high-quality data can overfit.}}
]



所以 data mixture 不是简单：

> “高质量 source 权重越高越好。”

---

# 26. UniMax 的思想现在就非常自然了

Multilingual model 面临同样的问题。

英语：

[
10T
]

tokens。

某个低资源语言：

[
1B.
]

如果 uniform sampling：

低资源语言可能被重复：

[
1000
]

遍。

UniMax 的思路：

> 尽量平衡语言，但是为任何 source 设置一个最大的 epoch cap。

也就是类似约束：

[
\boxed{
\frac{
p(s)D_{\rm train}
}{
D_s
}
\le C
}
]

其中 (C) 是允许最多重复次数。

UniMax 原论文的核心正是：让语言 sampling 更均衡，同时通过显式限制重复次数，减少尾部语言过拟合。

这又是：

[
\boxed{
\text{quality/diversity}
\leftrightarrow
\text{repeat/overfit}
}
]

的 trade-off。

---

# 27. RegMix：为什么 Data Mixing 突然变成 Scaling Laws 了？

假设有：

[
10
]

个 data sources。

mixture：

[
p\in\Delta^{9}.
]

你不可能把所有 mixture 都训练 7B 模型试一遍。

RegMix 的办法特别 CS336：

先随机采很多 mixture：

[
p_1,p_2,\dots,p_K.
]

每个只训练一个**很小的 proxy model**。

得到：

[
(p_i,L_i).
]

然后训练 regression：

[
\boxed{
\hat L=f(p)
}
]

再解：

[
\boxed{
p^*
===

\arg\min_p
\hat L(p).
}
]

最后把这个 mixture：

[
p^*
]

迁移到真正大模型。

这就是：

[
\boxed{\text{data mixture scaling law}}
]

官方 Lecture 14 直接把这个方法类比 Scaling Laws。RegMix 原论文实际上训练了 512 个 1M 参数 proxy models、每个 1B tokens，用它们预测 mixture，再把预测结果迁移到更大的训练；论文显示 mixture 的影响很大，而且不同 domains 的交互往往违反直觉。

---

# 28. 但是小模型的最佳 mixture 能直接 transfer 到大模型吗？

这正是 Lecture 14 又一次提醒你的地方：

[
\boxed{\text{未必。}}
]

原因仍然是：

[
\boxed{\text{epoching is scale-dependent}}
]

小实验可能只训练：

[
10B\text{ tokens}.
]

那么一个只有：

[
10B
]

tokens 的精品 source：

[
\text{epoch}\le1.
]

你会得出：

> 权重 90% 很好！

但正式训练：

[
1T.
]

同样 90%：

[
900B/10B=90\text{ epochs}.
]

完全不是同一个 regime。

所以小规模 mixture optimum：

[
p^*_{\rm small}
]

可能根本不等于：

[
p^*_{\rm large}.
]



---

# 29. Simulated Epoching 是一个非常漂亮的 Scaling trick

这和 Lecture 11 的 WSD 有一种神似。

思想：

> **让小实验尽可能模拟大实验会看到的数据重复程度。**

假设最终：

[
D_{\rm large}=1T.
]

proxy：

[
D_{\rm small}=10B.
]

ratio：

[
r=
\frac{10B}{1T}
==============

0.01.
]

那么在小规模 experiment 里，不让它访问完整 source pool。

而是把每个 source 的可用数据也缩成：

[
\boxed{
D_s^{small}
===========

rD_s^{large}.
}
]

这样：

[
\frac{
p_sD_{\rm small}
}{
D_s^{small}
}
=

\frac{
p_sD_{\rm large}
}{
D_s^{large}
}
]

注意两边相等！

也就是：

[
\boxed{
\text{small experiment 和 large run 的 expected epochs 相同。}
}
]

这就是 Lecture 14 所谓 simulated epoching：**把大规模会遇到的 scarcity/重复现象，在小规模实验里提前模拟出来。** 

这和整门 CS336 的主题高度一致：

[
\boxed{\text{让 small scale predict large scale}}
]

---

# 30. 到这里，Lecture 14 前半可以压成三个 optimization variables

Filtering：

[
\boxed{\text{Which examples?}}
]

Deduplication：

[
\boxed{\text{How many effective copies?}}
]

Mixing：

[
\boxed{\text{How often sample each source?}}
]

其实都在控制：

[
\boxed{p_{\text{train}}(x)}
]

所以它们并不是三个孤立的 preprocessing tricks。

它们共同组成：

[
\boxed{\text{Data Distribution Engineering}}
]

---

# 31. 然后 Lecture 14 突然从 Pretraining 跳到 Synthetic Data

官方后半的 recipe 非常简单：

[
\boxed{
1.\ Define environments
}
]

[
\boxed{
2.\ Define tasks/prompts
}
]

[
\boxed{
3.\ Collect responses from a strong teacher
}
]



注意这和前面的 Web filtering 看起来完全不是一个世界。

但其实完全一样。

前半：

```text
raw web
↓
找 desired examples
```

后半：

```text
task distribution
↓
生成 desired examples
```

也就是说：

[
\boxed{
\text{如果现实世界里没有你想要的数据，
那就主动制造训练分布。}
}
]

---

# 32. OpenThoughts：Reasoning Data 已经变成一门实验科学

OpenThoughts 做的是：

[
\boxed{\text{reasoning SFT / distillation data recipe}}
]

2026 Lecture 14 引用的 pipeline 扩展到约 1.2M examples，以 QwQ-32B 为 teacher；questions 来自 27 个 human/synthetic sources，而且对每个 prompt sample 多个回答（讲义给的是 16）会有帮助。一个很值得注意的实验结论是：**benchmark 更强的模型并不必然是更好的 teacher**；课程引用 OpenThoughts 的结果指出 QwQ-32B 在其 recipe 里反而优于 DeepSeek-R1 作为 teacher。([arXiv][1])

为什么会这样？

因为：

[
\boxed{\text{Teacher capability}}
\neq
\boxed{\text{Teacher data quality}}
]

一个 teacher 可能最终解题率很高，但是：

```text
推理特别长
style 奇怪
错误模式不适合 student
输出 diversity 不合适
```

另一个稍弱 teacher 的 trajectory：

> 可能反而更适合小 student imitation。

所以 synthetic data 的问题不是：

[
\boxed{\text{“调用最强 API 就完事。”}}
]

而仍然是：

[
\boxed{\text{data recipe engineering}}
]

。

---

# 33. 为什么“同一个 Prompt 采 16 条”可能有用？

假设 teacher：

[
p_T(y|x)
]

不是 deterministic。

一个 prompt 只采一次：

[
y_1.
]

你看到的只是 teacher distribution 的一个 sample。

如果：

[
y_1,\dots,y_{16}
\sim p_T(y|x),
]

你能够获得：

[
\boxed{\text{solution diversity}}
]

包括：

```text
不同推理路径
不同错误模式
不同解题策略
```

对于有 verifier 的数学/code task，还可以：

[
\boxed{\text{sample → verify → select}}
]

所以 synthetic data pipeline 的一个关键 knob 本身就是：

[
\boxed{\text{samples per prompt}}
]

它和 inference 里的 pass@k、RL rollout 数量实际上是同一类思想。

---

# 34. SWE-smith：Synthetic Data 开始进入 Agent 时代

数学题 synthetic data 很容易：

```text
题目
↓
teacher reasoning
↓
答案
```

Software engineering 困难得多。

因为真实任务需要：

[
\boxed{\text{repository environment}}
]

SWE-smith 的思路是：

> 给一个真实 repository，让 LM 主动引入 bug，从而制造新的修复任务。

Lecture 14 给出的规模是：

[
128\text{ repositories}
\rightarrow
50K\text{ tasks}.
]

([GitHub][2])

这属于非常漂亮的：

[
\boxed{\text{semi-synthetic data}}
]

Environment 是真的：

[
\text{real GitHub repo}
]

Task 是合成的：

[
\text{synthetic bug}.
]

这样比完全让 LLM 凭空编 repository 真实得多。

---

# 35. 但是 Software Agent Synthetic Data 最大瓶颈不是 LLM，而是环境

这点特别值得你注意。

数学：

```text
Python function
→ check final answer
```

很便宜。

Repository-level SWE：

```text
clone repo
install dependency
build
Docker
database
specific OS
old package
run tests
```

可能比模型推理本身更折腾。

Lecture 14 直接说：

[
\boxed{\text{setting up thousands of Docker images is an infrastructural nightmare}}
]

。([GitHub][2])

所以 Agent Data 的核心瓶颈常常是：

[
\boxed{\text{Environment scaling}}
]

而不仅是：

[
\boxed{\text{model generation scaling}}
]

这和你以后读 Agent-RL / coding-RL 特别相关。

---

# 36. SWE-Zero 的想法就非常 2026

Lecture 14 使用了 2026 年最新的 SWE-Zero 作为例子。

观察：

> 很强的 coding model 即使没有真的执行 repository，也能依靠内部 code semantics/world model 解决大量 SWE tasks。

于是他们构造大量不要求 repository-specific execution 的 agent trajectories，从而绕开昂贵环境建设。讲义给出的 SWE-Zero 数据包括约 300K agent trajectories 和 150K GitHub PRs；同时还有更少量、真正需要 execution feedback 的 SWE-Hero trajectories。([GitHub][2])

这背后的思想很重要：

[
\boxed{
\text{Fully executable data}
\text{质量高但昂贵}
}
]

[
\boxed{
\text{Execution-free synthetic trajectories}
\text{稍弱但可以巨量扩展}
}
]

又是：

[
\boxed{\text{quality vs quantity}}
]

只不过现在从 Web data 搬到了 Agent data。

---

# 37. SWE-rebench 又体现“用真实 PR 制造真实任务”

Lecture 14 还介绍 SWE-rebench：

约 21K interactive Python SWE tasks，来自 3.4K GitHub repositories；raw pool 使用数十万 GitHub PR，并让模型协助安装依赖和判断 PR quality。

你应该看到 Synthetic Data 的 spectrum：

```text
完全 synthetic
     ↓
synthetic task + real environment
     ↓
real task + synthetic teacher response
     ↓
real PR + reconstructed environment
     ↓
fully real human trajectory
```

越往下：

[
\boxed{\text{realism}\uparrow}
]

但：

[
\boxed{\text{cost}\uparrow}
]

[
\boxed{\text{availability}\downarrow}.
]

这和 Lecture 12 Evaluation 的 **realism vs practicality** 是完全同一矛盾。

---

# 38. 这就是 Lecture 14 最深的统一：Filtering 和 Synthetic Data 是镜像

Filtering：

[
\boxed{
\text{世界给我太多数据，我选择。}
}
]

Synthetic：

[
\boxed{
\text{世界没给我足够数据，我生成。}
}
]

二者最终都在追求：

[
\boxed{
p_{\text{train}}(x)
\approx
p_{\text{desired behavior}}(x)
}
]

例如你希望模型：

[
\boxed{\text{会数学 reasoning}}
]

可以从 Web 中：

[
\text{filter math}
]

也可以：

[
\text{generate reasoning traces}.
]

希望模型：

[
\boxed{\text{会修 repository bugs}}
]

可以从 GitHub：

[
\text{mine PRs}
]

也可以：

[
\text{synthesize bugs + teacher trajectories}.
]

现代 data pipeline 通常就是：

[
\boxed{
\textbf{Mine + Filter + Generate + Verify + Mix}
}
]

。

---

# 39. Lecture 14 和 A4 的关系：你终于知道作业真正想考什么了

2026 A4 官方仓库故意把训练实现固定在 `cs336_basics`，而 `cs336_data` 基本留空给学生实现 data processing。最终训练配置也固定为 **8 张 B200、16,384 steps、约 8.6B training tokens**。([GitHub][3])

所以 A4 的真正思想不是：

> “我也实现一个 fastText wrapper。”

而是做一个受限优化：

[
\boxed{
\max_D
\text{ModelQuality}(D)
}
]

subject to：

[
\boxed{
|D|
\approx 8.6B\text{ tokens}
}
]

以及：

[
\boxed{
\text{model/training recipe fixed}.
}
]

换句话说：

> 大家拿的是同一辆赛车、同样汽油预算。

你竞争的是：

[
\boxed{\text{汽油里到底装什么。}}
]

---

# 40. 所以你做 A4 时应该如何看待每一个 Data Rule？

不要问：

> “这个 heuristic 合不合理？”

应该问：

[
\boxed{
\text{它改变了哪些 examples 的 sampling probability？}
}
]

例如：

```python
if len(doc) < 200:
    drop()
```

真正的后果可能是：

[
\boxed{\text{短 FAQ、短代码解释、简洁高质量 QA 全被 downweight}}
]

。

再比如：

```python
if p_english < 0.8:
    drop()
```

可能顺手删：

```text
code
LaTeX
multilingual technical docs
```

。

再比如 aggressive dedup：

> 可能减少 memorization。

但也可能误删：

```text
公式化法律文本
许可证
模板化但有价值的代码
```

。

所以数据规则一定要：

[
\boxed{\text{看 examples}}
]

而不是只盯：

```text
kept 47.2%
```

这个 scalar。

官方 Lecture 14 的最后一句总结就特别强调：**大量 data work 是 domain-specific 的，而且核心工作之一就是实际查看 examples。** 

---

# 41. Lecture 12 → 13 → 14 现在可以彻底串起来了

Lecture 12：

[
\boxed{\text{What behavior do we value?}}
]

例如：

> coding、math、agentic SWE。

Lecture 13：

[
\boxed{\text{Where might relevant evidence exist?}}
]

例如：

> GitHub、arXiv、StackExchange、Web。

Lecture 14：

[
\boxed{\text{How do we select/create the right training distribution?}}
]

于是：

```text
Evaluation
    ↓
定义 desired behavior
    ↓
Sources
    ↓
找到 raw evidence
    ↓
Transform / Filter / Dedup / Mix
    ↓
Synthetic augmentation
    ↓
Training
    ↓
Evaluation
```

这就是完整：

[
\boxed{\text{Data Flywheel}}
]

。

---

# 42. Lecture 9/11 → Lecture 14 也有一条非常漂亮的连接

Scaling Laws：

[
\boxed{\text{小模型预测大模型}}
]

Data Mixing：

[
\boxed{\text{小模型 mixture experiments 预测大模型}}
]

甚至有同样的问题：

[
\boxed{\text{scale mismatch}}
]

所以才有：

[
\boxed{\text{simulated epoching}}
]

让小模型的数据稀缺程度模拟正式训练。

也就是说这门课一直重复同一个方法论：

[
\boxed{
\textbf{不要在 hero scale 上盲试；
设计便宜而忠实的 proxy experiment。}
}
]

Lecture 11 是模型超参数。

Lecture 14 是数据超参数。

---

# 43. 我最建议你亲手推一次的 Lecture 14 内容

真正值得“做题式”掌握的不是 dataset 名称，而是三组公式。

第一组是 MinHash：

[
\boxed{
P[h(A)=h(B)]
============

# J(A,B)

\frac{|A\cap B|}{|A\cup B|}
}
]

你必须能解释为什么。

第二组是 LSH：

[
\boxed{
P_{\rm candidate}(s)
====================

1-(1-s^r)^b
}
]

并解释：

[
r\uparrow
\Rightarrow
\text{更严格}
]

以及：

[
b\uparrow
\Rightarrow
\text{更宽松}.
]

第三组是 source epoch：

[
\boxed{
E_s
===

\frac{
p_sD_{\rm train}
}{
D_s
}
}
]

这条式子极其重要。

因为它告诉你：

[
\boxed{
\text{mixing weight 不能脱离 source size 和 training horizon 来看。}
}
]

---

# 44. 十道 Lecture 14 自测题

1. 为什么 filtering 可以形式化为 “target (T) + raw (R) → 找 (R) 中类似 (T) 的子集”？这与 classifier training 有什么关系？
2. 为什么一个 quality classifier 从根本上不可能完全“客观”？它的 positive examples 在定义什么？
3. 为什么训练 100B tokens 与训练 10T tokens 时，最佳 filtering threshold 可能完全不同？
4. 为什么 duplicate 不只是浪费算力，而等价于隐式 sample reweighting？
5. 请证明 (P[\mathrm{MinHash}(A)=\mathrm{MinHash}(B)]=J(A,B))。
6. 从“一个 band match 的概率”开始，推导 (1-(1-s^r)^b)。
7. 为什么 (r) 增大让 LSH 更严格，而 (b) 增大让它更宽松？
8. 有一个 10B-token 高质量 source，总训练 1T tokens，mixture 权重为 30%。它会被重复多少遍？答案是 (0.3T/10B=30) epochs。这个数字可能带来什么问题？
9. RegMix 与 Lecture 9 的 Scaling Laws 在实验哲学上有什么相同之处？
10. 为什么 Synthetic Data 不能简单等价成“找最强模型生成越多越好”？请从 teacher distribution、environment cost、verification、diversity 和 scale 五个角度解释。

如果这十题你能真正推出来，这一讲就不是“听懂了几个数据集名字”，而是真正开始拥有 data researcher 的思维。

---

# 最后，把 Lecture 14 压成一块黑板

我会先写：

[
\boxed{
\text{Transformation}
=====================

\text{What representation?}
}
]

然后：

[
\boxed{
\text{Filtering}
================

\text{Which examples?}
}
]

然后：

[
\boxed{
\text{Deduplication}
====================

\text{How many effective copies?}
}
]

然后：

[
\boxed{
\text{Mixing}
=============

\text{How often sample each source?}
}
]

最后：

[
\boxed{
\text{Synthetic Data}
=====================

\text{What examples should we create?}
}
]

你会发现五个问题其实都在决定同一个东西：

[
\boxed{
p_{\text{train}}(x)
}
]

所以整堂 Lecture 14 最核心的一句话，我会写成：

[
\boxed{
\textbf{Data engineering 不是把垃圾数据“洗干净”；
而是在固定训练预算下，主动设计模型将要看到的经验分布。}
}
]

这也是为什么 **Filtering、MinHash、LSH、RegMix、OpenThoughts、SWE-Zero** 这些看起来完全不属于同一领域的东西，会被 Percy 塞进同一讲：它们全是在回答——

[
\boxed{
\textbf{如果每一个训练 token 都要花钱，
我们怎样决定哪些 token 值得存在？}
}
]

而到 Lecture 15，课程会立即发生下一次大的转向：到这里我们主要还是在构造“模型应该学习什么数据”；接下来则要正式讨论 **SFT / RLHF 如何把一个会续写文本的 base model，变成一个会按照人的意图回答问题的 assistant**。
