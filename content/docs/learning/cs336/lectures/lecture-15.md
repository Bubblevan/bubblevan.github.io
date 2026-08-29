---
title: "L15 · SFT / RLHF"
weight: 15
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "sft", "rlhf"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture15/
---

Lecture 15 是 CS336 第一次正式进入 **Post-Training / Alignment**，而且 2026 版比“讲一下 SFT 和 RLHF”要深得多。

官方课程表里，Lecture 15 是 **5 月 18 日，Mid/post-training (SFT/RLHF)，Tatsu 主讲**；下一讲 Lecture 16 才专门进入 **RLVR**。官方公开视频时长约 80 分钟，课件约 65 页。

如果前 14 讲解决的是：

[
\boxed{\text{怎么造出一个很强的 base model}}
]

那么 Lecture 15 的问题是：

[
\boxed{
\textbf{为什么一个“很会预测下一个 token”的模型，
还不是一个好用的 ChatGPT？}
}
]

以及进一步：

[
\boxed{
\textbf{SFT、Reward Model、PPO、DPO 到底分别在改变模型什么？}
}
]

我先把整讲压成一条主线：

[
\boxed{
\text{Pretraining}
\rightarrow
\text{SFT}
\rightarrow
\text{Preference Data}
\rightarrow
\text{Reward Model / PPO}
\rightarrow
\text{DPO}
\rightarrow
\text{Overoptimization}
}
]

其中最重要的认知转变是：

[
\boxed{
\textbf{SFT = imitation}
\qquad
\textbf{RLHF = optimization}
}
]

这两个词几乎可以概括整堂 Lecture 15。

---

# 一、为什么 GPT-3 很强，却还不是 ChatGPT？

先回到 pretraining：

[
\mathcal L_{\text{PT}}
======================

-\mathbb E_{x\sim p_{\text{web}}}
\sum_t
\log p_\theta(x_t|x_{<t}).
]

模型学的是：

[
\boxed{p_{\text{web}}(\text{next token}\mid\text{prefix})}
]

也就是说：

> 给我一段互联网文本，我尽量猜接下来人类会写什么。

但用户真正要的是：

> “请按照我的意图完成任务。”

这两个目标根本不是一回事。

比如用户输入：

> Give me three concise reasons why exercise is beneficial.

一个纯 base LM 学到的可能是：

```text
用户问题
→ 某个论坛里另一个网友继续讨论
→ 问题复述
→ 网页广告
→ 一个答案
```

而 assistant 应该直接：

```text
1. ...
2. ...
3. ...
```

所以：

[
\boxed{
\text{Capability}
\neq
\text{Control}
}
]

Pretraining 给你的是一个巨大的能力库。

Post-training 更像：

[
\boxed{\text{告诉模型什么时候调用哪些能力、以什么形式调用。}}
]

InstructGPT 的经典结果非常能说明这一点：在人类偏好评测的 prompt 分布上，**1.3B InstructGPT 的输出甚至可以比 175B GPT-3 更受偏好**；这显然不是因为 1.3B 突然获得了比 175B 更多的世界知识，而是因为行为控制发生了巨大变化。([arXiv][2])

---

# 二、经典 InstructGPT Pipeline：整讲的骨架

Lecture 15 用的起点就是经典三阶段：

```text
Base model
   ↓
① SFT demonstrations
   ↓
SFT model
   ↓
② preference comparisons
   ↓
Reward Model
   ↓
③ PPO
   ↓
RLHF model
```

具体：

### Step 1：SFT

人类给 demonstration：

[
(x,y)
]

例如：

```text
User:
Explain attention in simple terms.

Assistant:
Attention lets each token...
```

然后普通 teacher forcing。

---

### Step 2：Preference Data

同一个 prompt：

[
x
]

生成多个 responses：

[
y_1,y_2,y_3,y_4.
]

让标注者排序：

[
y_3>y_1>y_4>y_2.
]

然后学习：

[
\boxed{\text{什么回答更好}}
]

---

### Step 3：RL

把语言模型当 policy：

[
\pi_\theta(y|x)
]

让它生成回答，由 reward model：

[
r_\phi(x,y)
]

打分，然后利用 PPO 提高 reward。

这正是 InstructGPT 的经典训练框架。([Yulong Ge][3])

但 Lecture 15 真正要解释的是：

> **为什么需要这三步？**

---

# 三、SFT 到底在优化什么？

给定：

[
(x_i,y_i)
]

其中：

* (x_i)：prompt / conversation history；
* (y_i)：理想 assistant response。

SFT：

[
\boxed{
\mathcal L_{\rm SFT}
====================

-\sum_i
\sum_t
\log
p_\theta(y_{i,t}|x_i,y_{i,<t})
}
]

([Yulong Ge][3])

你应该一眼看出来：

> 这和 pretraining 的 cross entropy 根本没本质区别。

都是：

[
\boxed{\text{next-token prediction}}
]

真正不同的是：

[
\boxed{\text{data distribution}}
]

Pretrain：

```text
internet text
books
code
Wikipedia
...
```

SFT：

```text
User → ideal Assistant
User → tool call
Tool → observation
Assistant → next action
...
```

所以 SFT 的秘密不是新 loss。

而是：

[
\boxed{\textbf{换了模型模仿的数据分布。}}
]

---

# 四、这里有个很重要的细节：Prompt 是否算 Loss？

典型 SFT：

```text
<user>
What is RMSNorm?
</user>

<assistant>
RMSNorm normalizes...
</assistant>
```

通常：

```text
User tokens       loss mask = 0
Assistant tokens  loss mask = 1
```

即只优化：

[
\boxed{
p_\theta(\text{assistant response}\mid\text{conversation})
}
]

而不是让模型学习预测用户到底会说什么。

但 Lecture 15 特别提醒：

> **“是否 mask prompt”并不是 pretraining 与 SFT 的本质定义。**

有些 SFT recipe 也会预测全部 token，有些 midtraining 目标又与 pretraining 混合。

更可靠的区别是：

[
\boxed{
\text{数据分布、反馈形式与训练目的}
}
]

([Yulong Ge][3])

---

# 五、SFT 最重要的作用：Behavior Cloning

把 demonstration distribution 写成：

[
p^*(y|x).
]

SFT 在做：

[
\boxed{
p_\theta(y|x)
\approx
p^*(y|x)
}
]

所以本质就是：

[
\boxed{\text{Behavior Cloning / Imitation Learning}}
]

老师怎么回答：

> 学生就模仿怎么回答。

因此 demonstration 里所有东西都会一起进入模型：

```text
事实内容
回答长度
语气
Markdown
列表
引用格式
拒绝方式
推理风格
工具调用
JSON schema
todo list
```

全部只是 token。

模型并不知道：

> “这个 token 是知识。”

或者：

> “这个 token 是风格。”

对 gradient 来说完全一样。

---

# 六、这解释了为什么 SFT Data 如此重要

Lecture 15 展示的 instruction-data 演进很有意思：

[
\text{FLAN}
\rightarrow
\text{Self-Instruct}
\rightarrow
\text{Alpaca}
\rightarrow
\text{ShareGPT/Vicuna}
\rightarrow
\text{OpenAssistant}
\rightarrow
\text{Agent/Tool trajectories}
]

([Yulong Ge][3])

你不要背 dataset 名字。

要看数据分布怎么变化。

---

## 第一代：FLAN

把传统 NLP benchmark：

```text
classification
QA
translation
summarization
reasoning
```

全改写成自然语言 instruction。

比如：

```text
Classify sentiment:
This movie was fantastic.
```

→

```text
positive
```

Instruction tuning 的重要发现就是：把很多任务统一转换成 instructions 去微调，可以显著提升 unseen tasks 的 zero/few-shot 泛化；Flan-PaLM 工作把这一方向扩展到约 1.8K tasks。([arXiv][4])

但 FLAN 风格有个问题：

> 它很像 benchmark solver，不像现代聊天助手。

---

# 七、Self-Instruct：让模型自己造 Instructions

人类 instruction 数量有限。

Self-Instruct：

```text
少量人工 seed tasks
      ↓
大模型生成更多 instructions
      ↓
生成 input/output
      ↓
过滤重复/垃圾
      ↓
拿去 instruction tuning
```

核心就是：

[
\boxed{\text{synthetic instruction data}}
]

Self-Instruct 原论文报告，在 GPT-3 上使用自生成 instruction data 可以显著提高 instruction following。([arXiv][5])

后来 Alpaca 把类似思想变得特别出名：

> 用强模型生成 52K instruction-response pairs，再训练一个较小开源模型。

这其实已经是：

[
\boxed{\text{Distillation}}
]

---

# 八、ShareGPT / OpenAssistant：SFT 开始越来越像真实使用

FLAN prompts：

> “Determine whether premise entails hypothesis.”

现实用户：

> “我这个代码为什么报错？”

> “帮我改一下邮件。”

> “解释一下这个公式。”

因此 SFT dataset 越来越向：

[
\boxed{\text{real conversations}}
]

移动。

Lecture 15 总结了三个非常明显的变化：

[
\boxed{\text{Chattiness}}
]

[
\boxed{\text{Detail}}
]

[
\boxed{\text{Tool use}}
]

([Yulong Ge][3])

这说明一个很重要的问题：

> **所谓“助手人格”，很大程度就是训练数据统计特征。**

---

# 九、如果数据都特别长，模型就会特别啰嗦

例如 SFT corpus 平均回答：

[
400\text{ tokens}.
]

模型很容易学到：

> “好回答就是长回答。”

于是：

```text
简单问题
↓
先总结
↓
列 8 点
↓
举 3 个例子
↓
总结一下
```

这不是模型“性格突然发生了变化”。

本质上：

[
\boxed{\text{maximum likelihood faithfully copied training distribution}}
]

Lecture 15 特别指出，长度、详细度和 tool-use 都可以通过 SFT 数据非常直接地改变。

这个认识也解释为什么：

[
\boxed{\text{SFT dataset design = product design}}
]

---

# 十、2026 年的 SFT 已经不仅是 Text → Text

这是这讲很现代的一部分。

Agent SFT 数据可能是：

```text
User
↓
Assistant analysis/action
↓
Tool call JSON
↓
Tool result
↓
Assistant tool call
↓
...
↓
Final response
```

例如：

```json
{
  "role": "assistant",
  "tool_calls": [
    {
      "name": "bash",
      "arguments": {
        "command": "pytest tests/"
      }
    }
  ]
}
```

那么：

```text
role
tool_calls
function name
arguments
JSON formatting
```

全部都可以成为 next-token supervision。

Lecture 15 的 Nemotron 类 agentic SFT 示例甚至包含 tool calls 和 todo structures。([Yulong Ge][3])

所以以后看到 Coding Agent：

> “为什么它知道先写 todo、然后读文件、然后跑测试？”

一种很现实的回答就是：

[
\boxed{\text{因为这种轨迹被写进了 SFT data。}}
]

---

# 十一、这里出现 Lecture 15 一个很深的观点：SFT 更擅长“抽取能力”，而不是“创造能力”

LIMA 做了一个非常著名的实验：

仅用约：

[
1000
]

条精心挑选的 demonstrations 对 65B LLaMA 做 SFT，就能获得相当不错的 instruction-following 行为。([arXiv][6])

为什么这么少数据也能有巨大变化？

一个很好的 mental model：

Pretraining 已经学到了：

```text
解释
总结
礼貌对话
写代码
拒绝
列清单
翻译
...
```

SFT 不是从零造这些能力。

而是在说：

[
\boxed{
\text{“用户问这种东西时，请进入这个 mode。”}
}
]

就像一个巨大的 latent skill library：

```text
Pretraining:
已经装了很多技能

SFT:
学会 routing / steering
```

所以：

[
\boxed{
\textbf{SFT 常常是 behavior elicitation，
而不是 capability creation。}
}
]

这是整讲最重要的思想之一。([Yulong Ge][3])

---

# 十二、这也解释了“500 条 Safety Data”为什么能有明显作用

Lecture 15 展示一个很有意思的实验：

在普通 Alpaca-style 数据里加入几百条 safety examples，某些 harmfulness benchmark 上模型行为就能大幅改变；其中一个实验里，约 500 条安全样本已经让某项有害评分从约 2.9 降到约 0.3。([Yulong Ge][3])

不是因为：

> 500 条数据教会了模型完整伦理学。

而更像：

> 模型本来就知道如何礼貌拒绝。

SFT 只是提高：

[
p_\theta(
\text{safe refusal}
\mid
\text{harmful prompt}
)
]

的概率。

所以少量 data 就能：

[
\boxed{\text{steer}}
]

行为。

---

# 十三、但 Safety 不是“拒绝越多越好”

假设：

[
V=\text{violation rate}
]

和：

[
F=\text{false refusal rate}.
]

你可以让模型：

```text
任何东西都拒绝
```

得到：

[
V\approx0.
]

但：

[
F\approx100%.
]

这是没用的。

所以 safety tuning 的目标实际上是一个 Pareto trade-off：

[
\boxed{
\text{减少真正 harmful response}
}
]

同时：

[
\boxed{
\text{减少 benign request 的错误拒绝}
}
]

Lecture 15 明确把 violation 与 false refusal 作为两种错误讨论。([Yulong Ge][3])

因此安全数据真正困难的是：

[
\boxed{\text{decision boundary}}
]

而不仅是多塞 refusal examples。

---

# 十四、SFT 能不能给模型“注入知识”？

这是 Lecture 15 一个非常值得细讲的问题。

假设 training sample：

> Who wrote paper X?

Assistant：

> Alice et al., 2024.

模型以前不知道 paper X。

训练几十遍以后：

[
p_\theta(
\text{Alice et al.}
|
\text{Who wrote X?}
)
]

当然可以升高。

所以从训练 accuracy 看：

> “知识注入成功。”

但是问题是：

> 这会不会提升模型对类似未知知识的可靠性？

不一定。

---

# 十五、SFT 有一个危险：知识和“回答行为”无法分离

举 Lecture 15 的 citation 例子。

训练数据：

```text
References:
Bivens & Mishel (2013), ...
```

模型同时学两件事：

### A. Content

[
\boxed{\text{这个文献的确存在}}
]

### B. Behavior

[
\boxed{
\text{“References:” 后应该生成作者、年份、期刊、页码}
}
]

问题是：

> Gradient 没有标签告诉它 A 和 B 哪个是“事实”，哪个是“格式”。

所以模型可能学得特别好：

```text
References:
Someone et al. (2024)
Journal of Very Plausible Studies
Vol. 18, pp. 23–49
```

但这个文献：

[
\boxed{\text{根本不存在}}
]

Lecture 15 用这个例子说明：在模型本来不知道的事实上进行 behavior cloning，可能同时强化“**即使不知道，也要像知道一样回答**”的行为，从而增加 hallucination。([Yulong Ge][3])

所以：

[
\boxed{
\textbf{SFT 最擅长教模型如何使用已有知识，
不一定擅长可靠地扩展知识边界。}
}
]

---

# 十六、Midtraining 为什么出现在 SFT 这堂课？

传统 mental model：

```text
巨大 pretraining
↓
结束
↓
一点点 SFT
```

现代 recipe 越来越不像这样。

而是：

```text
General Pretraining
        ↓
高质量数据比例逐渐提升
code/math/instruction/synthetic
        ↓
Midtraining / Decay stage
        ↓
Short final SFT
```

Lecture 15 将这种做法称为：

[
\boxed{
\text{midtraining}
}
]

或者：

```text
second-phase pretraining
two-phase training
```

并展示了实际公开 recipe：训练尾段仍保留 general web/code，同时开始显著增加 Wikipedia、Math、Instruction、Synthetic、SFT 等高质量切片。([Yulong Ge][3])

---

# 十七、为什么不直接把所有 instruction data 留到最后？

因为最终单独 SFT：

[
\boxed{\text{data 少，distribution shift 大}}
]

容易出现：

[
\boxed{\text{catastrophic forgetting}}
]

或者损害 base capabilities。

Midtraining：

```text
general data
+
code
+
math
+
instruction
+
synthetic
```

慢慢改变 mixture。

可以理解成：

[
\boxed{
p_{\rm general}
\rightarrow
p_{\rm high-quality}
\rightarrow
p_{\rm assistant}
}
]

而不是：

[
p_{\rm web}
\overset{\text{突然}}{\longrightarrow}
p_{\rm chat}.
]

这更像一个平滑 domain adaptation。

所以：

[
\boxed{\text{midtraining = 用更大 token 规模塑造能力和分布}}
]

而：

[
\boxed{\text{final SFT = 精确塑造 deployment behavior}}
]

---

# 十八、到这里，SFT 的本质可以浓缩成一句话

[
\boxed{
\textbf{SFT asks:
“请模仿这些好答案长什么样。”}
}
]

但这马上产生一个问题：

> 人类自己真的能写出最好的答案吗？

比如让你从零写：

> “给我一个最好的 CS336 Lecture 15 解释。”

很难。

但给你两个答案：

```text
A ...
B ...
```

问：

> 哪个更好？

容易得多。

这叫一个非常重要的：

[
\boxed{\text{Generation–Verification Gap}}
]

**生成一个最佳答案，比判断两个答案哪个更好更难。**

这就是 Preference Learning 出现的根本原因之一。

---

# 十九、于是数据从 Demonstration 变成 Preference Pair

SFT 数据：

[
\boxed{(x,y^*)}
]

要求人直接造理想答案。

Preference data：

[
\boxed{(x,y_w,y_l)}
]

只要求说：

[
y_w\succ y_l.
]

例如：

```text
Prompt:
Explain RMSNorm.

Response A:
short but correct

Response B:
long but contains an error

Human:
A > B
```

这比让 human 从零写出：

> 最完美 RMSNorm 教程

通常容易。

---

# 二十、但“人更喜欢哪个”也不是自然存在的标签

这是 Lecture 15 和 Lecture 12 Evaluation 完美接上的地方。

InstructGPT 的 guideline 把好回答拆成：

[
\boxed{\text{Helpful}}
]

[
\boxed{\text{Truthful}}
]

[
\boxed{\text{Harmless}}
]

而且三者可能冲突。([Yulong Ge][3])

比如：

> 给我一个错误 premise 的问题。

Helpful：

> 顺着用户回答？

Truthful：

> 应该纠正 premise。

所以 annotation guideline 本身就是：

[
\boxed{\text{行为规范}}
]

因此：

[
\boxed{
\textbf{RLHF 不是单纯“学习人类偏好”，
而是学习经过 guideline 定义和筛选后的某种偏好。}
}
]

---

# 二十一、Reward Model 是怎么从 Pairwise Preference 训练出来的？

定义：

[
r_\phi(x,y)\in\mathbb R.
]

希望 winner：

[
r_\phi(x,y_w)

>

r_\phi(x,y_l).
]

使用 Bradley-Terry：

[
P(
y_w\succ y_l|x
)
=

\sigma(
r_w-r_l
).
]

所以 reward-model loss：

[
\boxed{
\mathcal L_{\rm RM}
===================

*

\mathbb E
\log
\sigma(
r_\phi(x,y_w)
-------------

r_\phi(x,y_l)
)
}
]

([Yulong Ge][3])

如果：

[
r_w-r_l=0
]

模型认为：

[
P=0.5.
]

如果：

[
r_w-r_l\gg0
]

则：

[
P\approx1.
]

于是 reward model 最终学一个：

[
\boxed{
(x,y)
\rightarrow
\text{quality scalar}
}
]

---

# 二十二、为什么只在乎 Reward Difference？

因为：

[
\sigma((r_w+c)-(r_l+c))
=======================

\sigma(r_w-r_l).
]

所以所有 reward 加同一个常数：

[
c
]

完全没有影响。

也就是说：

[
\boxed{\text{reward absolute zero point 不可识别}}
]

偏好数据只告诉你：

[
\boxed{\text{相对哪个好}}
]

而不是：

> “这个回答的宇宙真实价值是 7.48。”

这个性质后面 DPO 推导会再次发挥巨大作用。

---

# 二十三、Reward Model 最大的问题：它只是 Proxy

真正想优化的是：

[
\boxed{R^*(x,y)=\text{真正的人类价值/质量}}
]

但我们拿到的是：

[
\boxed{\hat R_\phi(x,y)}
]

从有限 preference data 学出来的 proxy。

因此：

[
\hat R
======

R^*
+
\epsilon.
]

其中：

[
\epsilon
]

包括：

```text
有限数据
annotator bias
style bias
length bias
judge error
distribution shift
```

如果只轻微优化：

[
\hat R
]

主要提高的可能还是：

[
R^*.
]

但如果疯狂优化：

[
\hat R,
]

最终 optimizer 会开始寻找：

[
\boxed{\epsilon\text{ 的漏洞}}
]

这就是：

[
\boxed{\text{Reward Hacking / Goodhart}}
]

---

# 二十四、长度就是一个经典 Proxy Hack

假设标注数据里：

[
\text{详细回答}
]

平均确实更好。

Reward model 学到：

[
\boxed{\text{length} \uparrow
\Rightarrow
\text{reward}\uparrow}
]

然后 optimizer 很聪明：

> 那我以后全部写长一点。

结果从 SFT：

[
59\text{ tokens}
]

变成 RLHF：

[
243\text{ tokens}
]

核心内容可能没增加多少。Lecture 15 专门展示了 reward 与输出长度之间明显相关的实验。([Yulong Ge][3])

所以 RLHF 有一个非常重要的风险：

[
\boxed{
\text{你定义的 evaluator 有什么漏洞，
optimizer 就会利用什么漏洞。}
}
]

这与 Lecture 12 的 LLM Judge length bias 是同一问题。

---

# 二十五、现在终于进入 PPO：为什么不能直接对 Reward 反向传播？

目标：

[
J(\theta)
=========

\mathbb E_{y\sim\pi_\theta}
[r(y)].
]

但：

[
y
]

是 discrete sample。

你不能普通地：

[
\frac{\partial r(y)}{\partial \theta}
]

穿过 sampling operation。

于是用：

[
\boxed{\text{Policy Gradient}}
]

---

# 二十六、Policy Gradient 最值得你自己推一次

从：

[
J(\theta)
=========

\sum_y
\pi_\theta(y)r(y)
]

求导：

[
\nabla_\theta J
===============

\sum_y
r(y)
\nabla_\theta\pi_\theta(y).
]

利用：

[
\nabla\pi
=========

\pi\nabla\log\pi
]

得到：

[
\nabla_\theta J
===============

\sum_y
\pi_\theta(y)
r(y)
\nabla_\theta\log\pi_\theta(y).
]

即：

[
\boxed{
\nabla_\theta J
===============

\mathbb E_{y\sim\pi_\theta}
[
r(y)
\nabla_\theta\log\pi_\theta(y)
]
}
]

这条式子的机械含义非常漂亮：

### reward 高：

[
r>0
]

则：

[
\boxed{\log p(y)\uparrow}
]

### reward 低：

[
r<0
]

则：

[
\boxed{\log p(y)\downarrow}
]

所以 RL 看起来神秘，底层仍然像：

[
\boxed{\text{按 reward 加权的 log-likelihood update}}
]

---

# 二十七、为什么需要 Baseline / Advantage？

直接用：

[
R
\nabla\log\pi
]

variance 很大。

你可以减一个不依赖 action 的 baseline：

[
b(s).
]

因为：

[
\mathbb E[
b\nabla\log\pi
]
=

b
\nabla
\sum_a\pi(a)
============

0.

]

所以：

[
\boxed{
(R-b)
\nabla\log\pi
}
]

期望梯度不变，但 variance 可以降低。

定义：

[
\boxed{A=R-V}
]

这就是 advantage。

Lecture 15 还用玩具 PyTorch 示例验证：加 baseline 前后的期望梯度完全一致。([Yulong Ge][3])

---

# 二十八、但 RLHF 不能只最大化 Reward

如果目标只有：

[
\max_\pi
\mathbb E_\pi[r],
]

最优策略很可能变成：

[
\boxed{\text{mode collapse}}
]

假设某一个答案 reward 最大：

[
y^*.
]

那数学 optimum：

[
\pi(y^*)=1.
]

其他：

[
0.
]

但我们并不想把语言模型变成：

> 每个 prompt 都输出 reward model 最喜欢的模板答案。

所以加入：

[
\boxed{\text{KL penalty}}
]

---

# 二十九、RLHF 真正的核心目标

Lecture 15 给出的经典形式：

[
\boxed{
\max_\pi
\mathbb E_{y\sim\pi}
[r(x,y)]
--------

\beta
D_{\rm KL}
(
\pi(\cdot|x)
|
\pi_{\rm ref}(\cdot|x)
)
}
]

InstructGPT 还加入了预训练 loss 混合项：

[
J(\theta)
=========

\mathbb E
\left[
r_\phi(x,y)
-----------

\beta
\log
\frac{
\pi_\theta(y|x)
}{
\pi_{\rm ref}(y|x)
}
\right]
+
\gamma
\mathbb E_{\text{pretrain}}
[\log\pi_\theta(x)].
]

([Yulong Ge][3])

这里：

[
\pi_{\rm ref}
]

通常就是 SFT model。

---

# 三十、KL 到底起什么作用？

有两个特别重要的解释。

## 1. 防止 Language Model 跑飞

不希望：

[
\pi_{\rm RL}
]

离 fluent SFT model 太远。

也就是：

[
\boxed{\text{preserve language/model behavior}}
]

---

## 2. 防止跑出 Reward Model 的训练分布

Reward model 只在类似：

[
\pi_{\rm SFT}
]

的 responses 上接受过 preference supervision。

如果 RL policy 跑得特别远：

[
\boxed{\text{Reward model is extrapolating}}
]

此时它的 score 可能毫无可靠性。

所以 KL 相当于说：

[
\boxed{
\text{只在 reward model 比较可信的 neighborhood 里优化。}
}
]

这是非常重要的 interpretation。([Yulong Ge][3])

---

# 三十一、那 PPO 到底解决什么？

Vanilla policy gradient：

> 每更新一次 (\theta)，旧 rollout 就来自旧 policy。

而 rollout 对大 LM 特别贵。

想多利用几 epoch 旧 samples，就需要 importance ratio：

[
r_t(\theta)
===========

\frac{
\pi_\theta(a_t|s_t)
}{
\pi_{\theta_{\rm old}}(a_t|s_t)
}.
]

但这个 ratio 可以：

[
0\rightarrow\infty
]

导致 update 非常不稳定。

TRPO 的思路：

> 显式约束新旧 policy 的 KL。

但实现很复杂。

PPO 说：

> 不如直接把 probability ratio clip 掉。

---

# 三十二、PPO Objective 要真正看懂

[
\boxed{
L^{\rm CLIP}
============

\mathbb E
[
\min(
r_t A_t,
\operatorname{clip}(r_t,1-\epsilon,1+\epsilon)A_t
)
]
}
]

([Yulong Ge][3])

假设：

[
A_t>0.
]

说明 action 很好。

我们当然希望：

[
r_t>1
]

也就是提高这个 action 概率。

但如果：

[
r_t=5
]

PPO 会说：

> 别一次涨这么多。

clip 到：

[
1+\epsilon.
]

同样如果：

[
A_t<0
]

不希望一次把 action probability 砍到几乎 0。

所以：

[
\boxed{
\textbf{PPO = 我允许 policy 学，但不要一步走太远。}
}
]

---

# 三十三、为什么大家会嫌 PPO 特别麻烦？

因为一个完整 RLHF PPO pipeline 可能同时涉及：

```text
Policy model
Reference model
Reward model
Value model
Rollout engine
Old policy logprobs
Current logprobs
Advantages
KL
PPO epochs
```

Lecture 15 的评价非常明确：

[
\boxed{\text{PPO 很有效，但很 finicky}}
]

([Yulong Ge][3])

从 Systems 角度：

你已经不只是做：

```python
loss.backward()
optimizer.step()
```

而是在维护一个动态数据生成闭环：

```text
Policy generates
↓
RM scores
↓
Advantage estimates
↓
PPO update
↓
new Policy generates
↓
...
```

这既吃 GPU，又难 debug。

所以研究者自然问：

[
\boxed{\text{能不能不用 RL，也直接吃 preference pairs？}}
]

于是：

[
\boxed{\text{DPO}}
]

---

# 三十四、DPO 是 Lecture 15 数学上最漂亮的一段

DPO 从同一个 KL-regularized RLHF objective 出发：

[
\max_\pi
\mathbb E_\pi[r]
----------------

\beta
D_{\rm KL}(\pi||\pi_{\rm ref}).
]

先暂时假设：

> (\pi) 可以是任意 probability distribution。

那么这个优化问题有一个闭式解：

[
\boxed{
\pi^*(y|x)
==========

\frac1{Z(x)}
\pi_{\rm ref}(y|x)
\exp
\left(
\frac{r(x,y)}{\beta}
\right)
}
]

([Yulong Ge][3])

这个式子极其重要。

---

# 三十五、它到底是什么意思？

Reference：

[
\pi_{\rm ref}(y|x)
]

已经给每个回答一个基础概率。

Reward：

[
r(y)
]

然后通过：

[
e^{r/\beta}
]

重新加权。

所以：

[
\boxed{
\text{optimal policy}
=====================

\text{reference policy}
\times
\text{reward exponential tilt}
}
]

例如：

| Response | ref prob | reward |     multiplier |
| -------- | -------: | -----: | -------------: |
| A        |       .4 |      0 |            (1) |
| B        |       .3 |      1 |  (e^{1/\beta}) |
| C        |       .3 |     -1 | (e^{-1/\beta}) |

Reward 高：

[
\boxed{\text{probability mass 增加}}
]

Reward 低：

[
\boxed{\text{probability mass 减少}}
]

但始终建立在：

[
\pi_{\rm ref}
]

之上。

---

# 三十六、(\beta) 可以理解成“Alignment Temperature”

如果：

[
\beta\rightarrow\infty
]

那么：

[
e^{r/\beta}\approx1.
]

所以：

[
\pi^*
\approx
\pi_{\rm ref}.
]

几乎不改。

如果：

[
\beta\rightarrow0
]

reward 的微小差异都会被指数放大：

[
\boxed{\text{policy 极度追逐 high reward}}
]

更容易 collapse / overoptimize。

所以：

[
\boxed{
\beta
=====

\text{reward optimization vs staying close to reference 的旋钮}
}
]

---

# 三十七、DPO 最神奇的一步：反解 Reward

从：

[
\pi^*
=====

\frac1Z
\pi_{\rm ref}
e^{r/\beta}
]

得到：

[
\boxed{
r(x,y)
======

\beta
\log
\frac{
\pi^*(y|x)
}{
\pi_{\rm ref}(y|x)
}
+
\beta\log Z(x)
}
]

([Yulong Ge][3])

也就是说：

> 一个 policy 相对 reference 提高了某个 response 多少概率，本身就可以解释成一个 implicit reward。

这句话就是 DPO 标题：

[
\boxed{\text{Your language model is secretly a reward model}}
]

的来源。([arXiv][7])

---

# 三十八、然后把它塞回 Bradley-Terry

Preference model：

[
P(y_w>y_l)
==========

\sigma(r_w-r_l).
]

代入：

[
r_w
===

\beta
\log
\frac{\pi_\theta(y_w)}{\pi_{\rm ref}(y_w)}
+
\beta\log Z
]

以及：

[
r_l
===

\beta
\log
\frac{\pi_\theta(y_l)}{\pi_{\rm ref}(y_l)}
+
\beta\log Z.
]

差值：

[
r_w-r_l
=======

\beta
\log
\frac{\pi_\theta(y_w)}{\pi_{\rm ref}(y_w)}
------------------------------------------

\beta
\log
\frac{\pi_\theta(y_l)}{\pi_{\rm ref}(y_l)}.
]

注意：

[
\boxed{
+\beta\log Z
------------

# \beta\log Z

0
}
]

配分函数直接消掉了。([Yulong Ge][3])

漂亮。

---

# 三十九、于是得到 DPO Loss

[
\boxed{
\mathcal L_{\rm DPO}
====================

*

\mathbb E
\log\sigma
\left[
\beta
\left(
\log\frac{\pi_\theta(y_w|x)}
{\pi_{\rm ref}(y_w|x)}
----------------------

\log\frac{\pi_\theta(y_l|x)}
{\pi_{\rm ref}(y_l|x)}
\right)
\right]
}
]

([Yulong Ge][3])

看起来复杂。

其实 mechanical meaning 很简单：

[
\boxed{
\text{让 winner 相对 reference 更可能}
}
]

同时：

[
\boxed{
\text{让 loser 相对 reference 更不可能}
}
]

---

# 四十、为什么一定是“相对 Reference”？

假设：

Winner 本来：

[
\pi_{\rm ref}(y_w)=0.001.
]

现在：

[
\pi_\theta(y_w)=0.01.
]

增加：

[
10\times.
]

Loser：

[
0.5\rightarrow0.4.
]

虽然 loser 的 absolute probability 仍比 winner 高：

[
0.4>0.01.
]

但 DPO 在意：

[
\boxed{
\text{相对 reference，policy 朝偏好方向移动了多少}
}
]

这是一个非常关键的理解。

不是简单：

[
p(y_w)>p(y_l).
]

---

# 四十一、DPO 梯度又在做什么？

定义：

[
u=
\beta
\left[
\log
\frac{\pi_\theta(y_w)}
{\pi_{\rm ref}(y_w)}
--------------------

\log
\frac{\pi_\theta(y_l)}
{\pi_{\rm ref}(y_l)}
\right].
]

loss：

[
-\log\sigma(u).
]

梯度权重：

[
\boxed{\sigma(-u)}
]

因此：

### 如果模型现在很错

[
u\ll0
]

则：

[
\sigma(-u)\approx1.
]

强 update：

[
\boxed{\text{winner ↑，loser ↓}}
]

---

### 如果已经非常正确

[
u\gg0
]

则：

[
\sigma(-u)\approx0.
]

update 自动变小。

所以 DPO 本质上有点像：

[
\boxed{\text{pairwise logistic classification}}
]

模型已经排对的 pair：

> 不要一直猛训。

模型排错的 pair：

> 重点修。

Lecture 15 甚至手算/代码演示了这种 gradient 方向。([Yulong Ge][3])

---

# 四十二、为什么 DPO 如此受欢迎？

PPO：

```text
generate rollout
↓
reward model
↓
value model
↓
advantage
↓
PPO
↓
repeat
```

DPO：

```text
(x, winner, loser)
↓
compute logprobs
↓
loss.backward()
```

所以：

[
\boxed{\text{offline}}
]

[
\boxed{\text{no rollout loop}}
]

[
\boxed{\text{no explicit RM during training}}
]

[
\boxed{\text{no value network}}
]

特别像普通 supervised fine-tuning。

DPO 原论文的核心卖点正是：把标准 KL-regularized preference optimization 改写成一个简单 classification loss。([arXiv][7])

---

# 四十三、但“DPO 不需要 Reward Model”千万别理解过头

这是 Lecture 15 特别提醒的一点。

DPO primitive：

[
\boxed{\text{训练时不用显式 RM}}
]

但你的完整 system 完全可能：

```text
Prompt
↓
generate K responses
↓
Reward Model rank
↓
rejection sampling
↓
制造 SFT/pairwise data
↓
DPO
```

Reward model 仍然可以存在于：

[
\boxed{\text{data flywheel}}
]

里。

所以：

> DPO eliminates reward models

更准确应该说：

[
\boxed{
\text{DPO objective 不要求显式训练并在线调用 reward model。}
}
]

([Yulong Ge][3])

---

# 四十四、PPO 和 DPO 到底谁更强？

Lecture 15 对这一点其实很谨慎。

不是：

[
\boxed{\text{DPO 永远优于 PPO}}
]

也不是：

[
\boxed{\text{PPO 是旧时代垃圾}}
]

公开实验会发现算法排名对：

```text
preference data
reward model quality
beta
epochs
normalization
prompt distribution
```

极其敏感。

Lecture 15 展示的 Tulu 3 / PPO-DPO 对比甚至可以因为 (\beta) 等设置变化而出现明显排名变化；一些设置下 PPO 仍然更好。([Yulong Ge][3])

所以更可靠的判断：

[
\boxed{
\text{DPO = 简洁、稳定、便宜的 preference primitive}
}
]

而：

[
\boxed{
\text{PPO = 系统复杂，但拥有真正 on-policy reward optimization 的能力}
}
]

下一讲 RLVR 会让“真正 on-policy RL 为什么重新变重要”更加清楚。

---

# 四十五、RLHF 最大的终极问题：Reward Overoptimization

假设真实目标：

[
R^*
]

Reward Model：

[
\hat R.
]

随着 optimization：

```text
KL from reference
      ↑
```

proxy reward：

[
\hat R
]

可能持续：

[
\uparrow.
]

但是 gold / human reward：

[
R^*
]

通常：

```text
先 ↑
到 peak
再 ↓
```

这不是猜想。

Scaling Laws for Reward Model Overoptimization 系统观察到了这种模式：无论 PPO 还是 best-of-(n) 等方法，过度优化 proxy reward 最终都可能损害真实 reward。([arXiv][8])

Lecture 15 用的图也是：

```text
true quality
 ^
 |       /\
 |      /  \
 |     /    \
 |____/      \__
 +----------------→ optimization / KL
```

而 proxy reward：

```text
 ^
 |            /
 |          /
 |        /
 |______/
 +----------------→
```

([Yulong Ge][3])

---

# 四十六、这就是 Goodhart's Law 的机器学习版本

当某个 measure：

[
M
]

只是 target：

[
T
]

的 proxy。

一旦：

[
\boxed{M\text{ 成为优化目标}}
]

optimizer 会寻找：

[
\boxed{
\text{提高 }M
\text{ 而不提高 }T
}
]

的方法。

比如 reward model 喜欢：

```text
回答长
有 Markdown
先总结
很多 bullet
态度自信
```

optimizer 最终就可能把这些 style features 拉爆。

所以：

[
\boxed{
\textbf{更强的 optimizer 不会修复坏 reward；
它只会更快地找到 reward 的漏洞。}
}
]

这句话非常值得记。

---

# 四十七、RLHF 还会伤害 Probability Calibration

Base LM 有一个很自然的 probabilistic interpretation：

[
p_\theta(y|x)
]

表示模型的数据分布估计。

但 preference optimization 在做的是：

[
\boxed{\text{提高高 reward outputs 的概率}}
]

而不是：

[
\boxed{\text{恢复真实世界频率}}
]

所以 RLHF 后：

[
p=0.9
]

不一定意味着：

> 在现实中 90% 情况它正确。

Lecture 15 展示了 RLHF 后模型明显 overconfident、需要 temperature scaling 才更接近 calibration 的例子。([Yulong Ge][3])

所以：

[
\boxed{\text{Preference optimization 可以改善 usefulness，却损害概率语义。}}
]

这是一个很深的 trade-off。

---

# 四十八、现在可以真正区分 Pretraining、SFT、RLHF 了

我建议把它们记成三种目标。

## Pretraining

[
\boxed{
\text{Model the world/text distribution}
}
]

目标：

[
p_\theta(x)
\approx
p_{\rm data}(x).
]

重点：

[
\boxed{\text{knowledge + broad capabilities}}
]

---

## SFT

[
\boxed{
\text{Imitate desired demonstrations}
}
]

目标：

[
p_\theta(y|x)
\approx
p_{\rm demo}(y|x).
]

重点：

[
\boxed{\text{steering + format + behavior}}
]

---

## RLHF / Preference Optimization

[
\boxed{
\text{Optimize what evaluators prefer}
}
]

目标：

[
\max_\pi
\mathbb E[R]
------------

\beta KL.
]

重点：

[
\boxed{\text{move probability mass toward high-reward behavior}}
]

这个三分法就是 Lecture 15 最核心的 conceptual map。

---

# 四十九、SFT 和 RLHF 最大的数学区别：Distribution Matching vs Mode Seeking

假设人类理想回答 distribution：

```text
Response A: 40%
Response B: 30%
Response C: 20%
Response D: 10%
```

SFT 会倾向学：

[
\boxed{40,30,20,10}
]

尽量保留整个 distribution。

但如果 reward：

```text
A = 10
B = 8
C = 5
D = 1
```

纯 reward maximization：

[
\boxed{\pi(A)=1}
]

这是非常本质的不同：

[
\boxed{
\text{SFT = distribution matching}
}
]

[
\boxed{
\text{RL = mode seeking / objective optimization}
}
]

所以 RL 天然更容易：

[
\boxed{\text{mode collapse}}
]

才需要 KL / entropy 等机制。

Lecture 15 明确用这一对比作为从 SFT 过渡到 RLHF 的分水岭。([Yulong Ge][3])

---

# 五十、这里顺便解释：为什么 Preference Data 比 Demonstration Data 有时更“信息高效”

假设 human expert 自己写：

[
y^*
]

需要：

[
20\text{ min}.
]

但比较两个已有回答：

[
y_1,y_2
]

可能：

[
1\text{ min}.
]

所以相同 human budget：

[
\boxed{
\text{Preference labels 数量可以大很多}
}
]

而且 verifier 往往比 generator 更强：

> 我写不出最好的数学证明，但我可能能看出两个证明哪个更好。

这正是：

[
\boxed{\text{generation-verification gap}}
]

让 RLHF data pipeline 成立。

不过它也意味着：

[
\boxed{\text{如果 annotator 连验证都做不好，preference data 一样会坏。}}
]

尤其 factuality / specialist tasks。

Lecture 15 就特别强调普通标注者对 factuality 和复杂错误的漏检问题。([Yulong Ge][3])

---

# 五十一、RLAIF / Model Feedback 为什么自然出现？

人类 feedback：

[
\boxed{\text{贵}}
]

强模型：

[
\boxed{\text{便宜、快、可规模化}}
]

于是：

```text
Policy responses
↓
Strong model judge
↓
preference labels
```

就是：

[
\boxed{\text{AI Feedback}}
]

Constitutional AI 更进一步：

```text
human writes constitution/principles
↓
model critiques/revises outputs
↓
model generates preferences
↓
RL from AI feedback
```

Anthropic 的 Constitutional AI 就包含 supervised self-revision 与 AI-feedback preference/RL 阶段。([Anthropic][9])

但是它的边界很明显：

[
\boxed{
\text{Teacher model 很难可靠监督自己真正不会的东西。}
}
]

所以 expert knowledge / frontier capability 仍需要更强 verifier、人类专家或可验证环境。

---

# 五十二、这和 Lecture 14 Synthetic Data 是直接连续的

Lecture 14：

```text
Strong teacher
↓
generate synthetic answers
↓
SFT
```

Lecture 15：

```text
Strong teacher / humans
↓
generate comparisons
↓
Preference training
```

所以现代 post-training data flywheel：

```text
Prompt pool
   ↓
Generate candidates
   ↓
Verify / rank / reward
   ↓
SFT / DPO / PPO
   ↓
New stronger model
   ↓
Generate better candidates
   ↓
...
```

也就是：

[
\boxed{\text{Expert Iteration}}
]

SFT、DPO、PPO 只是这个飞轮中的不同 update operator。

---

# 五十三、现代公开 Post-Training Pipeline 可以怎么看？

例如 Tülu 3 是现在非常值得学习的开放 reference，因为它公开：

```text
SFT
DPO
RLVR
data
training code
evaluation
```

Ai2 自己也明确把它定位为开放的现代 post-training recipe。([Allen Institute for AI][10])

所以不要形成：

> “2026 的 post-training 已经不 SFT/DPO 了。”

更准确的是：

```text
Base/Midtrained model
      ↓
SFT
      ↓
Preference optimization
      ↓
RLVR / capability-specific RL
```

每一阶段仍然承担不同作用。

---

# 五十四、这和你接下来 Lecture 16 的关系

Lecture 15 最大的问题：

[
\boxed{\text{Reward 是 learned proxy}}
]

它会：

```text
有 bias
可被 hack
产生 Goodhart
```

那如果某些任务有一个**客观 verifier** 呢？

例如数学：

[
\boxed{\text{final answer 对不对}}
]

代码：

[
\boxed{\text{tests pass 不 pass}}
]

那么：

> 为什么还要训练一个 imperfect reward model？

直接把：

[
\boxed{\text{verifiable outcome}}
]

当 reward。

这就是下一讲：

[
\boxed{\text{RLVR = Reinforcement Learning with Verifiable Rewards}}
]

真正要解决的问题。

所以 Lecture 15 是 Lecture 16 必须的前置。

---

# 五十五、我建议你真正掌握的四条公式

## 1. SFT

[
\boxed{
\mathcal L_{\rm SFT}
====================

-\sum_t
\log
\pi_\theta(y_t|x,y_{<t})
}
]

理解：

[
\boxed{\text{imitate demonstration}}
]

---

## 2. Reward Model

[
\boxed{
\mathcal L_{\rm RM}
===================

-\log
\sigma(
r_w-r_l
)
}
]

理解：

[
\boxed{\text{learn pairwise preference}}
]

---

## 3. KL-Regularized RLHF

[
\boxed{
\max_\pi
\mathbb E_\pi[r]
----------------

\beta KL(\pi||\pi_{\rm ref})
}
]

理解：

[
\boxed{
\text{reward ↑
but don't drift too far}
}
]

---

## 4. DPO

[
\boxed{
\mathcal L_{\rm DPO}
====================

-\log\sigma
\left(
\beta[
\log\tfrac{\pi(y_w)}{\pi_{\rm ref}(y_w)}
----------------------------------------

\log\tfrac{\pi(y_l)}{\pi_{\rm ref}(y_l)}
]
\right)
}
]

理解：

[
\boxed{
\text{winner relative probability ↑；
loser relative probability ↓}
}
]

如果你能从第 3 个自己推到第 4 个，这讲的数学核心就真的掌握了。

---

# 五十六、Lecture 15 十道自测题

### 1. 为什么大规模 pretraining 不能自动产生一个好 assistant？

因为 pretraining 优化：

[
p_{\rm web}
]

不是：

[
p_{\rm desired\ assistant}.
]

---

### 2. 为什么 SFT loss 和 pretraining 几乎一样，却能产生巨大行为变化？

因为：

[
\boxed{\text{data distribution 完全不同}}
]

而强 base model 已有大量 latent behaviors。

---

### 3. 为什么 SFT 更像“steering”，而不是“knowledge injection”？

因为少量 demonstration 往往足以选择已有模式；强行在未知事实上 behavior-clone 反而可能增强 hallucination。

---

### 4. SFT 为什么会直接影响模型回答长度？

因为 maximum likelihood 会复制 demonstrations 的 length distribution。

---

### 5. 为什么 Preference Label 有时比 Demonstration 便宜？

因为：

[
\boxed{\text{verification easier than generation}}
]

---

### 6. Reward Model 为什么用 (r_w-r_l)，不是直接预测一个绝对分数？

因为 pairwise preference 只约束相对 ordering，absolute reward 有平移不确定性。

---

### 7. RLHF 为什么一定需要某种 KL / trust-region mechanism？

因为 reward model 是 proxy，只在 reference 附近可靠；纯 reward maximization 容易 mode collapse 和 reward hacking。

---

### 8. PPO clipping 到底解决什么？

控制：

[
\frac{\pi_{\rm new}}{\pi_{\rm old}}
]

不要一次偏离 1 太远，从而让 rollout 可以重复利用、update 更稳定。

---

### 9. DPO 为什么能删除显式 reward model？

因为 KL-regularized RL objective 的非参数最优 policy 满足：

[
\pi^*
\propto
\pi_{\rm ref}e^{r/\beta}
]

从而可以用：

[
\log\frac{\pi}{\pi_{\rm ref}}
]

直接参数化 reward，再代回 Bradley-Terry preference likelihood。([Yulong Ge][3])

---

### 10. 为什么“reward 一直升”不能证明模型一直变好？

因为：

[
\boxed{\text{proxy reward}\neq\text{true objective}}
]

强优化最终会 exploit proxy error；实验上 gold reward 可以在 proxy reward 继续上升时反而下降。([arXiv][8])

---

# 最后，把 Lecture 15 压成一块黑板

我会先写：

[
\boxed{
\text{Pretraining}
==================

\text{learn what humans write}
}
]

然后：

[
\boxed{
\text{SFT}
==========

\text{imitate how we want assistants to behave}
}
]

再写：

[
\boxed{
\text{Preference Learning}
==========================

\text{learn what answers we prefer}
}
]

然后：

[
\boxed{
\text{PPO}
==========

\text{directly optimize reward,
with KL / trust region}
}
]

最后：

[
\boxed{
\text{DPO}
==========

\text{rewrite preference optimization
as pairwise supervised learning}
}
]

但真正最大的一行，我会写：

[
\boxed{
\textbf{Post-training does not merely “make the model smarter”.
It reshapes where the model places probability mass.}
}
]

Pretraining 可能已经让模型知道：

```text
怎么写代码
怎么解释数学
怎么拒绝
怎么调用工具
怎么写详细回答
怎么写简洁回答
```

SFT 决定：

[
\boxed{\text{什么时候表现出哪一种模式}}
]

Preference optimization 再决定：

[
\boxed{\text{哪些模式应该得到更多概率质量}}
]

而 Reward Hacking 告诉你最后一个最重要的警告：

[
\boxed{
\textbf{模型最终会变成你真正奖励的东西，
而不是你心里以为自己奖励的东西。}
}
]

这就是 Lecture 15 从 **SFT → RLHF → PPO → DPO → Overoptimization** 这一整条链真正想让你理解的东西。下一讲 Lecture 16 的 RLVR，就是把这个问题进一步推进：**如果 reward 不再来自会被 hack 的偏好模型，而来自数学答案、代码测试等真正可验证结果，RL scaling 会发生什么？**
