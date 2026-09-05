---
title: "L12 · Evaluation"
weight: 12
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "evaluation"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture12/
---

Lecture 12 是 CS336 很关键的一次转向：前面 11 讲一直在回答“**怎么造出一个更强、更大、更快的语言模型**”，Lecture 12 突然问：

$$
\boxed{\textbf{等一下，“更强”到底是什么意思？}}
$$

Stanford 2026 官方课程表中，Lecture 12 是 5 月 6 日 Percy Liang 主讲的 **Evaluation**；同一天 A3 Scaling 截止、A4 Data 发布。官方 `lecture_12.py` 的开场也明确说：架构、训练、Systems、Scaling 都讲完了，下一步要讲训练数据；但**在决定给模型什么数据之前，必须先决定我们希望模型表现出什么行为，而这就需要 Evaluation。** ([GitHub][1])

整讲的官方结构是：

$$
\boxed{
\text{What is good?}
\rightarrow
\text{Perplexity}
\rightarrow
\text{Exam benchmarks}
\rightarrow
\text{Chat benchmarks}
\rightarrow
\text{Agentic benchmarks}
\rightarrow
\text{Reasoning}
\rightarrow
\text{Safety}
\rightarrow
\text{Realism}
\rightarrow
\text{Validity}
}
$$

最后再回来问：

$$
\boxed{\text{我们到底是在评 method、model，还是整个 agent system？}}
$$

([GitHub][2])

而我认为这堂课最重要的一句话不是任何 benchmark 名字，而是：

$$
\boxed{
\textbf{Evaluation 的本质，是把一个抽象概念，
转换成一个可测量的 concrete metric。}
}
$$

官方课件直接把这称为：

> abstract construct → concrete metric. ([GitHub][2])

---

# 一、为什么 Evaluation 比“跑 benchmark”深得多？

表面上 evaluation 很机械：

```text
1. 准备 prompts
2. 模型输出 responses
3. 算 accuracy
```

好像写几十行代码就结束。

但真正的问题在第 0 步：

$$
\boxed{\text{你到底想测什么？}}
$$

例如“模型好不好”至少可能有这些完全不同的定义：

```text
知识丰富吗？
数学强吗？
代码强吗？
指令遵循好吗？
用户喜欢吗？
能完成真实工作吗？
安全可靠吗？
便宜吗？
速度快吗？
Agent 能自主做多久？
```

甚至：

> “市场上真的有人愿意为它付钱吗？”

也是一种 evaluation。

官方 Lecture 12 开头就故意展示了几种完全不同的“模型好”的定义：benchmark 分数、成本、Arena 人类偏好，以及真实使用量。([GitHub][2])

所以评价不是：

$$
\boxed{\text{找到唯一正确的 leaderboard}}
$$

而是：

$$
\boxed{
\text{先明确你关心的 construct，
再设计 metric 去近似它。}
}
$$

---

# 二、这里有一个很重要的词：Construct

例如你说：

> 我想测“智能”。

“智能”就是一个：

$$
\boxed{\text{latent / abstract construct}}
$$

你无法拿尺子直接测。

于是只能设计 observable：

```text
数学题正确率
编程任务成功率
ARC-AGI
工具使用成功率
...
```

问题是：

$$
\boxed{
\text{metric}
\neq
\text{construct itself}
}
$$

例如：

$$
\text{MMLU accuracy}
$$

并不等于：

$$
\text{intelligence}.
$$

它只是 intelligence / knowledge 某个侧面的 proxy。

这就是为什么：

> “Model A MMLU 高 2%，所以 Model A 全面更智能”

逻辑上并不成立。

---

# 三、Lecture 12 第一个真正的 metric：Perplexity

先回到最纯粹的语言建模。

语言模型定义：

$$
p(x_1,\dots,x_T)
================

\prod_{t=1}^{T}
p(x_t|x_{<t}).
$$

平均 negative log-likelihood：

$$
L
=

-\frac1T
\sum_{t=1}^{T}
\log p(x_t|x_{<t}).
$$

那么 perplexity：

$$
\boxed{
\operatorname{PPL}
==================

e^L
}
$$

等价地：

$$
\boxed{
\operatorname{PPL}(D)
=====================

\left(
\frac1{p(D)}
\right)^{1/|D|}
}
$$

这是官方 Lecture 12 给出的定义。([GitHub][2])

---

# 四、Perplexity 到底是什么意思？

假设：

$$
PPL=10.
$$

不要机械理解成：

> 模型每次“有 10 个候选词”。

更准确的直觉是：

> 模型在平均 log-probability 意义上，面对一个有效分支数大约为 10 的预测问题。

越低：

$$
\boxed{\text{模型越能给真实数据高概率}}
$$

因此 pretraining：

$$
\boxed{\min \text{cross entropy}}
$$

本质就是：

$$
\boxed{\min \text{perplexity}}
$$

---

# 五、为什么 Perplexity 在 Scaling Laws 中那么好用？

Lecture 9 你已经看到：

$$
L(C)\sim C^{-\alpha}
$$

这种漂亮曲线。

原因之一就是：

$$
\boxed{\text{cross-entropy / perplexity 是非常 dense 的 signal}}
$$

一个长度：

$$
T=4096
$$

的 document，不是只给你：

```text
对 / 错
```

一个 bit。

而是贡献：

$$
4096
$$

个 token-level log probabilities。

所以它：

```text
连续
低方差
每个 token 都提供信号
```

非常适合：

$$
\boxed{\text{模型研发 + scaling prediction}}
$$

Lecture 12 也明确说 perplexity 直到今天仍大量用于语言模型开发，尤其因为它具有平滑的 scaling behavior。([GitHub][2])

---

# 六、那为什么不干脆说“Perplexity is all you need”？

有一个看起来挺漂亮的理论论证。

假设真实世界文本分布：

$$
t(x).
$$

我们的模型：

$$
p(x).
$$

cross entropy：

$$
H(t,p)
======

H(t)+D_{\mathrm{KL}}(t||p).
$$

最小值在：

$$
\boxed{p=t}
$$

时取得。

如果：

$$
p=t
$$

那理论上所有现实中的 conditional distribution：

$$
p(\text{answer}|\text{question})
$$

也应该正确。

所以可以产生一种信仰：

> “只要无限降低 perplexity，所有能力最终自然出现。”

Lecture 12 故意把这个称为有点“more faith than science”的立场。([GitHub][2])

---

# 七、Perplexity 的第一个问题：它测了很多你可能根本不关心的东西

例如句子：

> Stanford was founded in 1885.

语言模型 loss 会要求你预测：

```text
Stanford
was
founded
in
1885
.
```

但你如果想评：

> “模型是否知道 Stanford 建校年份？”

真正关心的是：

$$
p(1885|
\text{Stanford was founded in})
$$

而不是：

$$
p(\text{founded}|\text{Stanford was})
$$

这种普通语法 token。

所以官方提出：

$$
\boxed{\text{conditional perplexity}}
$$

也就是只测：

$$
p(\text{response}|\text{prompt})
$$

而不是整段文本所有 token。([GitHub][2])

---

# 八、很多 benchmark 其实是“Perplexity 戴了一顶帽子”

例如 multiple choice：

```text
Q: ...
A. ...
B. ...
C. ...
D. ...
```

可以比较：

$$
p(A|\text{Q}),
p(B|\text{Q}),
p(C|\text{Q}),
p(D|\text{Q}).
$$

选择：

$$
\arg\max p(\text{answer}|\text{question}).
$$

LAMBADA、HellaSwag 这类 continuation / completion benchmark，本质上和语言模型 conditional probability 有非常直接的关系。官方 Lecture 12 就把它们描述为某种意义上的 “perplexity in disguise”。([GitHub][2])

---

# 九、然后为什么出现 Exam Benchmarks？

因为你想直接问：

> “模型会不会数学？”

> “模型知道法律吗？”

> “它会不会物理？”

考试题非常方便。

优点：

$$
\boxed{\text{subject 可控}}
$$

$$
\boxed{\text{difficulty 可控}}
$$

$$
\boxed{\text{答案相对明确}}
$$

$$
\boxed{\text{grading 便宜}}
$$

所以 MMLU 这种 benchmark 大火。

官方 Lecture 12 将 MMLU 描述为 57 个学科的 multiple-choice benchmark，并且特别指出：**虽然名字叫 Massive Multitask Language Understanding，它实际很大程度是在测知识。** ([GitHub][2])

这个提醒非常重要。

---

# 十、Benchmark Saturation 是什么？

假设一个 benchmark：

```text
2019:
best model = 45%

2022:
75%

2024:
89%

2026:
96%
```

这时候你比较：

```text
Model A = 95.8%
Model B = 96.2%
```

这 0.4%：

* 可能是噪声；
* 可能是 dataset bug；
* 可能只是某几个怪题；
* 根本区分不了 frontier models。

这叫：

$$
\boxed{\text{benchmark saturation}}
$$

于是 benchmark 会不断升级难度。

Lecture 12 给出一条很清楚的演化线：

$$
\boxed{
\text{MMLU}
\rightarrow
\text{MMLU-Pro}
\rightarrow
\text{GPQA}
\rightarrow
\text{HLE}
}
$$

MMLU-Pro 去掉部分 noisy/trivial questions，并把选项从 4 个扩到 10 个；课程引用其结果显示模型准确率相对 MMLU 明显下降，从而重新拉开区分度。GPQA 使用博士级问题；Humanity's Last Exam 则进一步追求 frontier difficulty。([GitHub][2])

---

# 十一、这告诉我们一个 Evaluation 基本规律

好的 benchmark 必须处在某个：

$$
\boxed{\text{Goldilocks zone}}
$$

不能：

### 太容易

```text
大家 99%
```

没有 discrimination。

也不能：

### 太难

```text
大家 0%
```

还是没 discrimination。

理想：

```text
Model A 30%
Model B 45%
Model C 65%
Model D 80%
```

这才有 ranking signal。

因此：

$$
\boxed{\text{difficulty 本身就是 eval design 的核心参数}}
$$

官方 Lecture 12 最后的总结也把 **difficulty** 列为 evaluation 的核心 consideration 之一。([GitHub][2])

---

# 十二、但 Exam Benchmark 又有一个致命问题：人平时根本不是这么用 AI 的

真实用户通常不问：

```text
A/B/C/D 选哪个？
```

而是：

> “帮我比较这两个方案。”

> “给我改一封邮件。”

> “这个 bug 怎么修？”

> “我的沙拉适合放什么香草？”

答案：

$$
\boxed{\text{open-ended}}
$$

没有唯一 ground truth。

这就是 Lecture 12 从 Exam Benchmarks 转向：

$$
\boxed{\text{Chat Benchmarks}}
$$

的原因。([GitHub][2])

---

# 十三、Open-ended Response 怎么评分？

假设：

Model A：

> 加薄荷、莳萝会不错……

Model B：

> 欧芹、罗勒、百里香……

谁更好？

你不能像 MMLU 那样：

```python
prediction == label
```

于是出现：

$$
\boxed{\text{Pairwise Preference}}
$$

不要让人给回答打：

```text
7.6 / 10
```

而只问：

> A 和 B 哪个更好？

通常 pairwise judgment 更稳定。

---

# 十四、Chatbot Arena 的基本思想

随机用户给真实 prompt。

随机抽两个匿名模型：

```text
Prompt
  ↓
Model A response
Model B response
```

用户选择：

$$
A>B,\quad B>A,\quad \text{tie}.
$$

然后根据大量 pairwise comparisons 拟合 ranking。

Lecture 12 给出的经典 ELO probability：

$$
\boxed{
P(A>B)
======

\frac1{
1+10^{(E_B-E_A)/400}
}
}
$$

其中：

$$
E_A,E_B
$$

是两个模型的 rating。([GitHub][2])

---

# 十五、这个公式怎么理解？

如果：

$$
E_A=E_B
$$

则：

$$
P(A>B)=\frac12.
$$

如果 A 高：

$$
400
$$

分：

$$
P(A>B)
======

\frac1{1+10^{-1}}
\approx0.91.
$$

所以 ranking 不是：

> 平均打分。

而是找一组 latent scores，让它尽可能解释观察到的：

$$
\boxed{\text{pairwise preferences}}
$$

---

# 十六、Arena 为什么特别有吸引力？

因为它有很强的：

$$
\boxed{\text{ecological realism}}
$$

prompt 不是 benchmark 作者脑补出来的。

是真的：

$$
\boxed{\text{用户实际想问的问题}}
$$

而且模型不断更新，prompt 也不断更新。

所以不会那么容易：

```text
benchmark 固定 5 年
→ 所有人针对 benchmark 调参
```

官方 Lecture 12 特别指出 Arena 的优点包括真实 prompts、动态加入新模型和 prompts。([GitHub][2])

---

# 十七、可是用户偏好并不等于 Correctness

这是非常重要的。

假设两个回答：

### A

正确、简洁：

> 答案是 37。

### B

错误但极其自信：

> 经过详细推导，根据三个重要定理……答案显然为 42。

用户可能：

$$
\boxed{\text{喜欢 B}}
$$

因为它：

```text
更长
更有结构
更自信
更会迎合
```

于是 pairwise preference 可能把：

$$
\boxed{\text{style}}
$$

和：

$$
\boxed{\text{correctness}}
$$

混在一起。

官方 Lecture 12 明确指出 Chatbot Arena 的 preference 会混合 style/correctness，也可能受到 sycophancy 等影响。([GitHub][2])

所以：

$$
\boxed{\text{user preference}\neq\text{truth}}
$$

---

# 十八、那用 LLM 当 Judge 不就行了吗？

这就是 AlpacaEval / WildBench 一类工作。

你给 judge：

```text
Prompt
Response A
Response B
```

问：

> Which one is better?

优点：

$$
\boxed{\text{便宜}}
$$

$$
\boxed{\text{快}}
$$

$$
\boxed{\text{可重复}}
$$

于是你可以每次 checkpoint 都跑一遍。

---

# 十九、但 LLM Judge 也会有 Bias

Lecture 12 给了一个非常经典的例子：

$$
\boxed{\text{verbosity / length bias}}
$$

Judge 往往更喜欢：

> 更长、更详细、看起来更全面的回答。

于是开发者发现：

```text
只要把答案写长
↓
AlpacaEval win rate ↑
```

Leaderboard 被“hack”了。

AlpacaEval 2.0 因此使用统计方法校正 length bias。课程也提到 WildBench 通过更明确的 checklist/rubric 来提升 judge reliability。([GitHub][2])

这就是一个极其重要的规律：

$$
\boxed{
\textbf{一旦 metric 成为 optimization target，
模型就会开始利用 metric 的漏洞。}
}
$$

这正是 Goodhart-like failure。

---

# 二十、Rubric 为什么如此重要？

比较：

### Judge Prompt A

> Is this response good? Score 1–10.

非常模糊。

### Judge Prompt B

分别检查：

```text
1. Factual correctness
2. Instruction following
3. Completeness
4. Relevance
5. Style
```

Judge 的任务分解清楚了。

于是 reliability 通常：

$$
\uparrow
$$

Lecture 12 总结 chat evaluation 时明确提出：

$$
\boxed{\text{checklist / rubric improves reliability}}
$$

无论 judge 是人还是 LLM。([GitHub][2])

这其实与你做任何 Eval 框架都高度相关：

$$
\boxed{\text{先定义 failure taxonomy，再设计 scorer}}
$$

比一句：

> “让 GPT-5 给 1–10 分”

靠谱得多。

---

# 二十一、然后 Lecture 12 做了一个非常重要的升级：

以前：

$$
\boxed{\text{evaluate what LMs say}}
$$

现在：

$$
\boxed{\text{evaluate what LMs do}}
$$

也就是：

$$
\boxed{\text{Agentic Evaluation}}
$$

官方课件就是这样从 chat benchmarks 过渡到 agentic benchmarks。([GitHub][2])

---

# 二十二、Agent 和 LM 到底差在哪里？

Lecture 12 给出的简洁定义：

$$
\boxed{
\text{Agent}
============

\text{Language Model}
+
\text{Agent Scaffold}
}
$$

scaffold 包括：

```text
工具调用
循环
planning
memory
context management
subagents
error recovery
...
```

([GitHub][2])

所以假设：

```text
Claude Model X
```

放进两个不同 harness：

```text
Agent A:
simple ReAct loop

Agent B:
planning + memory + subagents + context compression
```

它们的 SWE-Bench 分数可以差非常多。

于是：

$$
\boxed{
\text{Agent benchmark score}
\neq
\text{pure LM capability}
}
$$

---

# 二十三、这就是 Lecture 12 一个非常重要的警告

如果 leaderboard 上：

```text
System A: 70%
System B: 55%
```

你必须先问：

> 比较的是 model 吗？

还是：

> model + scaffold？

甚至：

> model + scaffold + retries + tools + token budget + human intervention？

官方在 agentic 部分明确总结：

$$
\boxed{\text{evaluating agents = evaluating scaffold + LM}}
$$

([GitHub][2])

这句话以后看 SWE-Bench leaderboard 特别重要。

---

# 二十四、SWE-Bench 为什么是一个漂亮的 Agent Benchmark？

任务不是：

> “下面哪个 Python 语法正确？”

而是：

```text
给你真实 GitHub repository
+
真实 issue
↓
修改 codebase
↓
提交 patch
↓
跑 unit tests
```

metric：

$$
\boxed{\text{tests passed}}
$$

官方 Lecture 12 描述 SWE-Bench 为来自 12 个 Python repositories 的 2294 个软件工程任务，输入 codebase + issue，目标相当于生成一个能通过 tests 的 PR。([GitHub][2])

为什么这类 benchmark 好？

因为：

$$
\boxed{\text{verifier 很客观}}
$$

不是让 LLM judge 说：

> “这段代码看起来挺不错。”

而是：

```bash
pytest
```

通过就是通过。

---

# 二十五、这是一个很重要的 Eval 设计原则

如果能够把 task 设计成：

$$
\boxed{\text{verifiable outcome}}
$$

通常优于：

$$
\boxed{\text{subjective judge}}
$$

例如：

### Coding

$$
\boxed{\text{unit tests}}
$$

### Math

$$
\boxed{\text{exact final answer / symbolic verifier}}
$$

### CTF

$$
\boxed{\text{flag}}
$$

### Kaggle

$$
\boxed{\text{held-out metric}}
$$

这也是为什么 agent/RL 领域特别喜欢：

$$
\boxed{\text{verifiable tasks}}
$$

---

# 二十六、Lecture 12 给出的 Agent Benchmark 谱系很有意思

官方列出了：

**SWE-Bench**

$$
\rightarrow\text{真实代码库修 bug}
$$

**Terminal-Bench**

$$
\rightarrow\text{通用 terminal/computer tasks}
$$

**CyBench**

$$
\rightarrow\text{CTF cybersecurity tasks}
$$

**MLE-Bench**

$$
\rightarrow\text{Kaggle-style ML engineering}
$$

([GitHub][2])

它们共同在把 evaluation 从：

```text
回答一道题
```

扩展到：

```text
在环境中行动
观察结果
修改策略
继续行动
直到完成目标
```

也就是：

$$
\boxed{\text{long-horizon interaction}}
$$

---

# 二十七、Long-Horizon 为什么突然让 Evaluation 难很多？

单轮问答：

$$
x\rightarrow y.
$$

只需评：

$$
y.
$$

Agent：

$$
s_0
\xrightarrow{a_1}
s_1
\xrightarrow{a_2}
s_2
\cdots
\xrightarrow{a_T}
s_T.
$$

你现在有大量新问题：

```text
允许几步？
允许多少 tokens？
允许多少 API calls？
能不能 retry？
能不能联网？
可以调用哪些 tools？
失败后可以 reset 吗？
有没有 human help？
```

两个系统：

```text
Agent A: 30% success, $0.10/task
Agent B: 50% success, $50/task
```

你不能只说：

> B 更强。

因为 resources 不一样。

所以 agent evaluation 必须明确：

$$
\boxed{\text{rules of the game}}
$$

这正是 Lecture 12 最后的核心 takeaway 之一。([GitHub][2])

---

# 二十八、这和 Lecture 10 的 Inference 又连起来了

Agent benchmark：

Model A：

$$
50%
$$

但每个 task：

$$
100K\text{ output tokens}
$$

Model B：

$$
47%
$$

但：

$$
5K\text{ tokens}.
$$

哪一个更好？

取决于你的目标。

所以 Evaluation 不应该只有：

$$
\boxed{\text{Capability}}
$$

还要同时看：

$$
\boxed{\text{Cost}}
$$

例如：

$$
\text{success rate}
$$

vs

$$
\text{$ / task}
$$

vs

$$
\text{latency}
$$

这也是 Lecture 12 开场为什么专门展示“benchmark score + cost”的评价视角。([GitHub][2])

---

# 二十九、然后 Percy 问：能不能测“Pure Reasoning”？

Exam benchmark 有个长期问题。

模型答对：

> “法国首都是巴黎。”

它是：

$$
\boxed{\text{推理出来的？}}
$$

还是：

$$
\boxed{\text{记住的？}}
$$

MMLU、GPQA 都混杂：

$$
\text{knowledge}
+
\text{reasoning}.
$$

于是有人希望设计：

$$
\boxed{\text{memorization 没用的任务}}
$$

Lecture 12 用 ARC-AGI 来代表这条路线。([GitHub][2])

---

# 三十、ARC-AGI 的直觉是什么？

给你几个彩色 grid：

```text
input 1 → output 1
input 2 → output 2
input 3 → output 3

test input → ?
```

每道题都有一个新的 hidden rule。

模型需要：

$$
\boxed{\text{从少量 examples 推断规则}}
$$

而不是：

> “我在 Wikipedia 看过答案。”

因此目标是更偏：

$$
\boxed{\text{fluid reasoning}}
$$

官方 Lecture 12 强调 ARC tasks 相对独特，希望减少 memorization 的帮助，并指出 ARC-AGI-2 提高了多步推理要求；2026 的 ARC-AGI-3 又进一步走向 interactive environments。([GitHub][2])

---

# 三十一、但是所谓 “Pure Reasoning” 其实也没有那么 pure

因为你还是需要：

```text
视觉抽象
objects
spatial concepts
colors
counting
```

而且：

$$
\boxed{\text{人类自己的 reasoning 也建立在 prior knowledge 上}}
$$

所以：

$$
\boxed{
\text{reasoning}
\quad\text{vs}\quad
\text{knowledge}
}
$$

并没有绝对干净的分界。

Lecture 12 的总结也直接说：

> disentangle reasoning from knowledge 本身就很难。([GitHub][2])

---

# 三十二、接下来是另一根完全不同的轴：Safety

一个模型：

```text
GPQA 95%
SWE-Bench 90%
```

并不自动意味着：

$$
\boxed{\text{应该部署}}
$$

你还必须问：

```text
会不会协助危险行为？
会不会被 jailbreak？
会不会严重 hallucinate？
会不会迎合错误前提？
会不会歧视？
```

所以：

$$
\boxed{\text{Capability}\neq\text{Safety}}
$$

Lecture 12 给出 HarmBench、AIR-Bench 等安全 benchmark，并讨论 jailbreak 以及不同风险类别。([GitHub][2])

---

# 三十三、Safety Benchmark 比数学 Benchmark 更难在哪里？

数学：

$$
2+2=4.
$$

不同国家基本一样。

但很多 safety decision：

$$
\boxed{\text{context dependent}}
$$

依赖：

```text
法律
地区
文化
用户身份
实际意图
具体环境
```

同一条信息：

> 网络安全攻击技巧

可以被：

```text
攻击者
```

用于犯罪，也可以被：

```text
penetration tester
```

用于防御。

这就是：

$$
\boxed{\text{dual use}}
$$

官方 Lecture 12 特别强调 safety 很多方面高度 contextual，并以 cybersecurity agent 作为 dual-use 例子。([GitHub][2])

因此 Safety Eval 很难简化成：

$$
\boxed{\text{refusal rate 越高越安全}}
$$

因为：

> 什么都拒绝的模型当然“安全”，但也没用了。

---

# 三十四、现在进入一个我认为 Lecture 12 最重要的概念：Ecological Validity

$$
\boxed{\text{Ecological validity}}
$$

意思是：

> 你的 benchmark 到底像不像模型真正会遇到的现实环境？

官方定义就是 evaluation 对 real-world use 的捕捉程度。([GitHub][2])

---

# 三十五、比如 GPQA 很难，但它真的代表现实工作吗？

一个博士平时工作：

> 会连续回答 50 道 multiple-choice graduate questions 吗？

通常不是。

真实工作可能是：

```text
查资料
读 PDF
整理数据
写代码
和同事沟通
检查结果
反复修改
```

所以：

$$
\boxed{
\text{difficulty}
\neq
\text{realism}
}
$$

这是 Evaluation 特别容易混淆的两个轴。

---

# 三十六、因此出现 GDPVal、MedHELM 这种方向

Lecture 12 用 GDPVal 作为职业任务例子：从重要经济行业和职业中收集由有经验专业人士设计的任务。

MedHELM 则强调：

> 医疗模型不能只做 medical exam multiple choice。

更应该测：

$$
\boxed{\text{真实临床任务}}
$$

Lecture 12 描述 MedHELM 包含由多位临床医生贡献的 121 个 clinical tasks。([GitHub][2])

这里你应该看到 benchmark 演化：

```text
考试题
↓
真实 prompt
↓
真实工作任务
↓
真实 interaction
```

越来越 realistic。

---

# 三十七、但 Realism 和 Privacy 又发生冲突

最真实的用户数据：

$$
\boxed{\text{真实 ChatGPT/Claude conversations}}
$$

可是这些里面可能有：

```text
个人信息
公司机密
健康信息
私人文本
```

不能直接把它们发布为 benchmark。

Lecture 12 用 Anthropic Clio 作为例子：利用模型分析真实用户数据，只发布聚合后的使用模式；课件直接总结：

$$
\boxed{\text{realism and privacy are sometimes at odds}}
$$

([GitHub][2])

这就是 Eval design 的另一个 trade-off。

---

# 三十八、到这里我们还没触碰最危险的问题：Validity

假设你造了：

$$
1000
$$

道“很好”的 benchmark。

Model A：

$$
90%.
$$

问题：

> 这 90% 真的说明模型会做吗？

还是：

> 它训练时已经看过 benchmark？

这就是：

$$
\boxed{\text{Train-Test Contamination}}
$$

---

# 三十九、以前为什么污染比较容易控制？

经典 ML：

```text
ImageNet train
ImageNet test
```

训练集明确。

测试集明确。

规则：

$$
\boxed{
D_{\rm train}\cap D_{\rm test}=\varnothing
}
$$

---

# 四十、Foundation Model 时代怎么变了？

训练数据：

$$
\boxed{\text{整个互联网}}
$$

benchmark：

$$
\boxed{\text{也发布在互联网}}
$$

于是：

> 你怎么知道模型没见过答案？

更麻烦的是很多公司：

$$
\boxed{\text{不公开训练数据}}
$$

所以外部评测者甚至无法直接算 overlap。

Lecture 12 把它明确列为现代 eval validity 的首要问题之一。([GitHub][2])

---

# 四十一、Lecture 12 给了四类解决污染的路线

官方归纳的办法包括：

**从模型行为推断 contamination**：利用数据 exchangeability 等统计特征判断模型是否对某些测试样本表现异常熟悉。

**要求模型提供方报告 overlap**：建立更好的 reporting norms。

**Fresh evals**：持续抓取新发布的问题，例如 LiveCodeBench 一类思路。不过课件也提醒，timestamp 并不绝对安全，因为旧内容可能被重新复制。

**Private evals**：使用从未上网的公司内部 codebase、个人文本、私有数据。([GitHub][2])

我会把这浓缩成：

$$
\boxed{
\text{Detect}
\quad
\text{Disclose}
\quad
\text{Refresh}
\quad
\text{Keep Private}
}
$$

---

# 四十二、为什么 Private Eval 特别有价值？

假设你把 benchmark：

```text
eval.json
```

公开放 GitHub。

第二天：

```text
所有 crawler 抓走
```

下一代 pretraining：

$$
\boxed{\text{它可能直接进入 training corpus}}
$$

你永远在追 contamination。

Private eval：

$$
\boxed{\text{训练方理论上接触不到}}
$$

提供非常强的 held-out guarantee。

但缺点：

$$
\boxed{\text{不可公开复现}}
$$

所以又是 trade-off。

---

# 四十三、Validity 还不只是 Contamination

另一个大问题：

$$
\boxed{\text{Dataset 本身可能有错}}
$$

例如软件工程 benchmark：

Issue 描述看起来合理。

但：

```text
test 有 bug
environment 装不上
任务不可解
patch 不完整
test coverage 不够
```

于是：

$$
\boxed{\text{benchmark score 不等于真实能力}}
$$

Lecture 12 以 SWE-Bench → SWE-Bench Verified 为例，说明需要人工验证/清洗 benchmark；也提到了打造更高质量 “Platinum” benchmark 的方向。([GitHub][2])

---

# 四十四、Agent Benchmark 尤其容易出现“Verifier Hack”

假设任务：

> 修复这个 bug。

测试只有：

```python
assert output == 5
```

一个笨 agent 直接：

```python
return 5
```

测试：

$$
\boxed{\text{passed}}
$$

但它实际上没有解决真实问题。

这说明：

$$
\boxed{\text{verifier 也是 specification}}
$$

如果 verifier 太弱：

$$
\boxed{\text{模型会 exploit benchmark}}
$$

Lecture 12 特别提到 agent benchmarks 可能存在测试不足，甚至 trivial agent 也能“solve”任务的问题，并提到通过检查 agent trace 来发现 evaluation flaws。([GitHub][2])

---

# 四十五、所以“只看总分”是 Evaluation 最大的坏习惯之一

假设：

$$
\text{SWE-Bench}=48.2%.
$$

你必须继续打开 individual examples：

```text
哪些题错了？
为什么错？
是模型错？
tool 失败？
environment bug？
scaffold 死循环？
test 错？
任务本身模糊？
```

否则一个 scalar：

$$
48.2
$$

把所有 failure modes 都压扁了。

这也是 Stanford Evaluation 一贯很强调的思路：

$$
\boxed{\text{Aggregate metrics for comparison}}
$$

但：

$$
\boxed{\text{Instances / traces for understanding}}
$$

虽然 2026 版最终 takeaway 更简化为 difficulty、realism、validity 和 rules of the game，但整讲大量案例本身都在强调这一点。([GitHub][2])

---

# 四十六、到这里出现一个非常深的问题：我们究竟在评什么对象？

以前经典 ML：

$$
\boxed{\text{Method}}
$$

例如：

```text
固定 ImageNet train
固定 test
固定 compute
```

比较：

```text
ResNet vs ViT
optimizer A vs optimizer B
```

这个游戏的目标是：

$$
\boxed{\text{算法创新}}
$$

---

现代 LLM leaderboard 很多时候评价：

$$
\boxed{\text{Model / System}}
$$

规则变成：

> Whatever it took to build it.

Model A 可能：

```text
10T private data
RL
tool use
retrieval
test-time compute
```

Model B：

```text
完全不同训练 recipe
```

只看最终：

$$
\boxed{\text{谁输出更好}}
$$

这对用户非常有价值，但对于科学研究：

> 很难知道到底哪个 method 起了作用。

Lecture 12 最后专门区分 **methods vs models/systems**。([GitHub][2])

---

# 四十七、这也是为什么 NanoGPT Speedrun 很有科研味道

例如固定：

```text
same dataset
same hardware
same validation target
```

然后问：

$$
\boxed{
\text{谁最快达到 target loss？}
}
$$

这评价的是：

$$
\boxed{\text{training method}}
$$

而不是：

> 谁愿意花更多钱。

Lecture 12 把 nanoGPT speedrun 明确作为今天仍然偏 method evaluation 的例子。([GitHub][2])

这个区别非常值得以后读论文时使用：

$$
\boxed{\text{Benchmarking a product}}
\neq
\boxed{\text{Benchmarking an algorithm}}
$$

---

# 四十八、Agent 时代这个问题会更严重

假设：

Model X + minimal loop：

$$
40%.
$$

Model Y + elaborate scaffold：

$$
70%.
$$

然后你换：

Model X + elaborate scaffold：

$$
75%.
$$

所以最初：

> “Y 模型比 X 强 30 分。”

可能完全错了。

真正是：

$$
\boxed{\text{scaffold difference}}
$$

造成。

因此所有 agent benchmark 都必须公开：

```text
model
prompt
tools
scaffold
token budget
max turns
temperature
retry policy
context policy
```

否则：

$$
\boxed{\text{结果不可解释}}
$$

这就是 Lecture 12 所谓：

$$
\boxed{\text{Clearly state the rules of the game}}
$$

([GitHub][2])

---

# 四十九、如果让我把 Lecture 12 整理成三个 Eval 维度

官方最后特别提出：

$$
\boxed{
\text{Difficulty}
,\quad
\text{Realism}
,\quad
\text{Validity}
}
$$

([GitHub][2])

我认为这是这堂课最值得背下来的框架。

---

## 第一轴：Difficulty

这个 benchmark 能否区分现在的模型？

```text
太容易 → saturation
太难 → everyone zero
```

---

## 第二轴：Realism

benchmark 是否像实际使用？

```text
MMLU
→ real usage 较远

Arena
→ real prompts

SWE-Bench
→ real repositories

professional tasks
→ 更接近真实工作
```

---

## 第三轴：Validity

分数是不是在测你声称的东西？

例如：

```text
有没有 contamination？
labels 对不对？
tests 足够吗？
judge 有 bias 吗？
metric 能被 hack 吗？
```

---

# 五十、这里可以画一个很有用的三角

```text
                 Difficulty
                    /\
                   /  \
                  /    \
                 /      \
                /        \
               /__________\
          Validity       Realism
```

理想 benchmark：

$$
\boxed{\text{三个都高}}
$$

但现实很难。

例如：

### HLE

difficulty 高。

realism 不一定高。

---

### Arena

realism 高。

但 correctness validity 更难控制。

---

### Private internal workflow

realism 高、contamination 低。

但复现性低。

所以：

$$
\boxed{\text{不存在完美 benchmark}}
$$

这正是 Lecture 12 最终结论：

$$
\boxed{\text{There is no one true evaluation.}}
$$

([GitHub][2])

---

# 五十一、再加一个第四维：Cost

我认为在今天尤其必须补上：

$$
\boxed{\text{Cost}}
$$

两个模型：

|           | Model A | Model B |
| --------- | ------: | ------: |
| SWE-Bench |     50% |     55% |
| Cost/task |   $0.10 |     $20 |
| Latency   |    30 s |  20 min |

你买哪个？

取决于 use case。

因此 evaluation 应该逐渐从：

$$
\boxed{\text{single scalar}}
$$

升级成：

$$
\boxed{\text{Pareto frontier}}
$$

例如：

$$
\boxed{\text{quality vs cost}}
$$

$$
\boxed{\text{quality vs latency}}
$$

这和 Lecture 10 的 inference economics 又接上了。

---

# 五十二、现在把 Lecture 9–12 连起来，你会看到一条特别漂亮的链

## Lecture 9 / 11

问：

$$
\boxed{\text{怎么预测更大的模型？}}
$$

得到：

$$
L(C)
$$

scaling curve。

---

## Lecture 12

突然问：

> 这个 (L) 到底代表用户想要的吗？

Validation cross entropy 更低：

$$
\not\Rightarrow
$$

SWE-Bench 必然更高。

SWE-Bench 更高：

$$
\not\Rightarrow
$$

用户更喜欢。

用户更喜欢：

$$
\not\Rightarrow
$$

更安全。

所以：

$$
\boxed{
\text{Scaling predicts a metric;
evaluation decides whether that metric matters.}
}
$$

这是两部分非常深的连接。

---

# 五十三、而 Lecture 12 → Lecture 13/14 的连接甚至更重要

官方一开头就说：

> Data shapes model behavior.

如果你的 eval 发现：

```text
代码弱
```

你可能：

$$
\boxed{\text{增加 code data}}
$$

如果：

```text
中文弱
```

你改变 multilingual mixture。

如果：

```text
数学 reasoning 弱
```

你寻找 math / synthetic reasoning data。

如果：

```text
toxicity / safety 有问题
```

你改变 filtering/post-training。

所以整个模型研发循环其实是：

```text
Train
 ↓
Evaluate
 ↓
发现 failure modes
 ↓
改变 Data / Architecture / Post-training
 ↓
Train
 ↓
Evaluate
```

所以 Lecture 12 放在 Data 之前一点都不是巧合。

$$
\boxed{\textbf{没有 evaluation，就不知道 data pipeline 应该优化什么。}}
$$

官方正是因此在 Data lectures 前先讲 Evaluation。([GitHub][2])

---

# 五十四、我建议你以后设计 Eval 时固定写一张“Evaluation Contract”

先不要写 scorer。

先写：

$$
\boxed{\text{What construct?}}
$$

例如：

> Repository-level autonomous software engineering.

然后：

$$
\boxed{\text{What unit?}}
$$

一个 issue？

一个 conversation？

一个 agent trajectory？

然后：

$$
\boxed{\text{What environment?}}
$$

有什么工具？

网络？

shell？

文件？

然后：

$$
\boxed{\text{What budget?}}
$$

最大：

```text
tokens
steps
wall-clock
$
```

然后：

$$
\boxed{\text{What success criterion?}}
$$

unit tests？

human preference？

rubric judge？

最后：

$$
\boxed{\text{What validity checks?}}
$$

contamination？

broken tasks？

judge bias？

这比一上来写：

```python
score = exact_match(...)
```

成熟得多。

---

# 五十五、如果你今后专门学习 LLM Eval，我建议把 Evaluation 分四层

这是对 Lecture 12 很自然的工程化整理。

### Layer 1：Intrinsic Model Eval

$$
\boxed{\text{Perplexity}}
$$

测 probability modeling。

---

### Layer 2：Capability Benchmarks

```text
MMLU
GPQA
HLE
ARC
math
code
```

回答：

> 模型具备哪些能力？

---

### Layer 3：Interaction / Agent Eval

```text
Arena
SWE-Bench
Terminal-Bench
MLE-Bench
```

回答：

> 系统在真实交互和环境中能完成什么？

---

### Layer 4：Deployment Eval

```text
safety
cost
latency
reliability
real user distribution
```

回答：

> 这个系统实际适不适合部署？

这四层没有谁替代谁。

---

# 五十六、我最希望你真正会回答的 10 道 Lecture 12 自测题

**1. 为什么 perplexity 很适合 model development，却不足以代表真实 usefulness？**

因为它 dense、smooth、低方差，但优化的是所有 token probability，而真实任务只关心特定 conditional behaviors。

**2. Benchmark saturation 为什么危险？**

因为：

$$
\boxed{\text{ceiling effect 导致模型之间失去 discrimination}}
$$

此时几分之几的差异可能主要是噪声。

**3. 为什么 pairwise preference 通常比 absolute 1–10 rating 更稳？**

因为比较 A/B 往往比建立统一绝对尺度更容易。

**4. 为什么 LLM-as-a-judge 不能直接当 ground truth？**

因为 judge 也有：

```text
length bias
style bias
self-preference
position bias
reasoning/correctness limits
```

所以要校准，并使用 rubric。

**5. SWE-Bench 到底是在评 model 还是 agent？**

通常是：

$$
\boxed{\text{model + scaffold + tools + budget}}
$$

必须明确 evaluation protocol。

**6. 为什么 unit-test-based benchmark 也可能 invalid？**

因为 tests 可能：

```text
不完整
错误
可被 exploit
```

所以 verifier quality 本身需要验证。

**7. Difficulty 和 Realism 为什么不同？**

GPQA 可以极难，但真实用户不一定天天做博士多选题。

**8. Train-test contamination 为什么在 foundation model 时代特别严重？**

因为：

$$
\text{train data}\approx\text{Internet}
$$

而：

$$
\text{public benchmarks}\subset\text{Internet}.
$$

**9. 为什么不存在一个“万能排行榜”？**

因为不同目标对应不同 construct：

$$
\text{knowledge}
\neq
\text{reasoning}
\neq
\text{helpfulness}
\neq
\text{safety}
\neq
\text{cost}.
$$

**10. Method evaluation 和 Model/System evaluation 最大的区别是什么？**

Method eval：

$$
\boxed{\text{固定规则，比较算法}}
$$

Model/system eval：

$$
\boxed{\text{允许 recipe 不同，比较最终产品}}
$$

两者服务完全不同的问题。([GitHub][2])

---

# 最后，我把 Lecture 12 压成一块黑板

先写：

$$
\boxed{
\text{Evaluation}
=================

\text{abstract goal}
\rightarrow
\text{measurable proxy}
}
$$

然后：

$$
\boxed{
\text{Perplexity}
\rightarrow
\text{Exam}
\rightarrow
\text{Chat}
\rightarrow
\text{Agent}
\rightarrow
\text{Real-world}
}
$$

这是越来越接近真实使用的过程。

但与此同时：

$$
\boxed{
\text{Ground-truth clarity}
}
$$

往往越来越弱。

考试：

```text
答案明确
但不真实
```

真实工作：

```text
很真实
但评分困难
```

所以整个 Evaluation 领域一直在 trade：

$$
\boxed{
\textbf{Difficulty}
+
\textbf{Realism}
+
\textbf{Validity}
}
$$

再加现代 LLM 特别重要的：

$$
\boxed{\textbf{Cost}}
$$

最后写上 Lecture 12 官方最重要的 takeaway：

$$
\boxed{
\textbf{There is no one true evaluation.}
}
$$

因为“模型好不好”根本不是一个天然存在的标量。

真正的问题永远是：

$$
\boxed{
\textbf{对于谁、在什么任务上、允许什么工具和预算、
用什么标准，我们说它“好”？}
}
$$

这也是为什么 **Evaluation 不是模型研发最后补一张排行榜**，而应该反过来处在研发循环最前面：你先决定什么行为值得优化，后面的 Data、Post-training、RL、Agent Harness 才知道应该往哪个方向推。
