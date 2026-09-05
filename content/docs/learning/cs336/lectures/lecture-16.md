---
title: "L16 · RLVR"
weight: 16
date: 2026-08-29
updated: 2026-08-29
course: "CS336"
topics: ["CS336", "rlvr", "reasoning"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture16/
---
可以。Lecture 16 是 CS336 里非常关键的一讲，因为它真正进入了过去两年最火的 **Reasoning RL / RLVR**。

Stanford 2026 官方课程表中，Lecture 16 是 5 月 20 日 Tatsu 主讲的 **Post-training – RLVR**；同一天正式发布 Assignment 5：**Alignment and Reasoning RL**。官方 A5 也明确要求实现 GRPO，并把语言模型训练到数学 reasoning 场景。([GitHub][1])

如果 Lecture 15 的问题是：

$$
\boxed{
\text{怎么让模型“符合人的偏好”？}
}
$$

那么 Lecture 16 突然把问题改成：

$$
\boxed{
\textbf{如果我根本不需要“人告诉我哪个好”，
因为答案可以自动验证呢？}
}
$$

这就是：

$$
\boxed{
\textbf{RLVR =
Reinforcement Learning with Verifiable Rewards}
}
$$

整讲大致可以压成：

$$
\boxed{
\text{RLHF 的问题}
\rightarrow
\text{Policy Gradient / PPO}
\rightarrow
\text{GRPO}
\rightarrow
\text{GRPO 的坑}
\rightarrow
\text{DeepSeek-R1}
\rightarrow
\text{Kimi k1.5}
\rightarrow
\text{Qwen3}
}
$$

Stanford 的 Lecture 16 确实就是按“算法 → 三个 reasoning model case study”的路线组织的。([GitHub][2])

---

# 一、为什么 Lecture 15 讲完 RLHF，还要再发明 RLVR？

Lecture 15 已经告诉你 RLHF 最大的问题：

我们真正想优化：

$$
R^*(x,y)
========

\text{真实的人类满意度}.
$$

但拿不到。

所以先收集 preference：

$$
y_w\succ y_l
$$

再训练 reward model：

$$
\hat R_\phi(x,y).
$$

然后 PPO 优化：

$$
\max_\theta
\mathbb E_{y\sim\pi_\theta}
[\hat R_\phi(x,y)].
$$

问题是：

$$
\boxed{
\hat R_\phi
\neq
R^*
}
$$

模型优化得越狠，就越可能开始 exploit：

$$
\hat R_\phi
$$

的漏洞。

所以出现 Lecture 15 的：

$$
\boxed{\text{reward overoptimization}}
$$

以及：

$$
\boxed{\text{mode collapse / calibration degradation}}
$$

Lecture 16 开头就是从这两个问题接着往下讲。([GitHub][2])

---

# 二、但数学题突然给了我们一个“完美 Reward”

假设问题：

> Solve (x^2-5x+6=0).

模型输出一大堆 CoT，最后：

$$
\boxed{x=2,3}.
$$

我们根本不需要训练一个 neural reward model 问：

> “这个回答看起来好吗？”

直接：

```python
correct = verify(prediction, ground_truth)
```

得到：

$$
R=
\begin{cases}
1 & \text{correct}\
0 & \text{wrong}
\end{cases}
$$

就完事了。

这就是：

$$
\boxed{\text{Verifiable Reward}}
$$

---

# 三、哪些领域特别适合 RLVR？

最典型的两个：

## 数学

最终答案：

$$
\boxed{\text{correct / incorrect}}
$$

甚至可以 symbolic equivalence：

$$
\frac12
=======

# 0.5

\frac{2}{4}.
$$

---

## Coding

模型写：

```python
def solve(...):
    ...
```

然后：

```bash
pytest
```

或者：

```text
compiler
+
test cases
```

得到：

$$
\boxed{\text{pass / fail}}
$$

DeepSeek-R1 就使用 rule-based accuracy rewards：数学检查最终答案，代码运行 compiler/test cases；此外还加入 format reward。DeepSeek 特别说明 reasoning 阶段不采用 neural reward model，一个原因正是避免其在大规模 RL 中被 reward hacking。([Nature][3])

这就是 RLVR 最大的吸引力：

$$
\boxed{
\text{Reward 不需要被“学出来”}
}
$$

而是来自：

$$
\boxed{\text{environment / verifier}}
$$

---

# 四、所以 RLVR 和 RLHF 最大的区别是什么？

## RLHF

```text
model response
     ↓
learned reward model
     ↓
0.734
```

Reward：

$$
\boxed{\text{approximate}}
$$

---

## RLVR

```text
model response
     ↓
parser / compiler / tests / answer checker
     ↓
0 or 1
```

Reward：

$$
\boxed{\text{much more objective}}
$$

于是 Goodhart 问题显著减轻。

注意我说的是：

$$
\boxed{\text{减轻}}
$$

不是消失。

因为 verifier 本身仍然可能被 hack。

后面我们会回来讲。

---

# 五、先把语言模型重新写成一个 RL 问题

这一步非常重要。

给定数学题：

$$
x.
$$

模型生成：

$$
y=(y_1,y_2,\dots,y_T).
$$

把它看成 MDP：

### State

当前 prefix：

$$
s_t=(x,y_{<t}).
$$

### Action

下一个 token：

$$
a_t=y_t.
$$

### Policy

语言模型：

$$
\boxed{
\pi_\theta(a_t|s_t)
}
$$

### Trajectory

整段 reasoning：

$$
\tau=(a_1,\dots,a_T).
$$

### Reward

最后验证答案：

$$
R(\tau)\in{0,1}.
$$

于是 reasoning LM 就变成：

$$
\boxed{
\text{一个超长 action-space 的 episodic RL agent}
}
$$

---

# 六、这里立刻出现一个巨大的 Credit Assignment 问题

假设模型输出：

```text
Step 1 正确
Step 2 正确
Step 3 错
Step 4 在错误基础上继续
Step 5 碰巧纠正
Step 6 得到正确答案
```

最终：

$$
R=1.
$$

那到底哪个 token 应该奖励？

我们不知道。

RLVR 最简单的做法甚至是：

$$
\boxed{\text{整条 trajectory 都拿同一个 final reward}}
$$

这听起来极其粗糙。

但偏偏非常有效。

这就是 DeepSeek-R1 最令人意外的地方之一：

> 复杂 reasoning 并不一定要求精确地给每一步一个 reward。

---

# 七、Policy Gradient 为什么可以只靠 Final Reward 学？

目标：

$$
J(\theta)
=========

\mathbb E_{y\sim\pi_\theta(\cdot|x)}
[R(y)].
$$

Policy-gradient：

$$
\boxed{
\nabla_\theta J
===============

\mathbb E
[
R(y)
\nabla_\theta
\log\pi_\theta(y|x)
]
}
$$

而：

$$
\log\pi_\theta(y|x)
===================

\sum_t
\log
\pi_\theta(y_t|x,y_{<t}).
$$

所以：

$$
\boxed{
\nabla_\theta J
===============

\mathbb E
\left[
R(y)
\sum_t
\nabla_\theta
\log\pi_\theta(y_t|s_t)
\right]
}
$$

如果这条 reasoning 最终成功：

$$
R>0
$$

它整条 trajectory：

$$
\boxed{\text{概率提高}}
$$

失败：

$$
R<\text{baseline}
$$

则整条 trajectory：

$$
\boxed{\text{概率降低}}
$$

所以它没有明确告诉模型：

> “第 37 个 token 是错误源头。”

而是在说：

> “这种整体 reasoning trajectory 比另一种好。”

---

# 八、为什么这竟然能工作？

因为 RLVR 并不是让一个随机网络从零学习数学。

Base model 已经通过 pretraining 学到了：

```text
代数
数学事实
推导格式
自我纠错
尝试不同解法
backtracking
verification
```

大量 latent behaviors。

RL 更像：

$$
\boxed{
\text{从已有 behavior distribution 中重新分配概率质量}
}
$$

这和 Lecture 15 对 SFT 的理解非常接近。

你可以这样理解：

### Pretraining

造出：

$$
\boxed{\text{reasoning repertoire}}
$$

### RLVR

根据最终成败：

$$
\boxed{\text{筛选并强化有效 reasoning strategies}}
$$

所以 RL 往往不是：

> “从无到有发明微积分。”

而是：

> “找到 base model 已经会的哪些行为更容易得到正确答案。”

这点后面的 R1-Zero 分析会再回来。

---

# 九、为什么 Vanilla REINFORCE 不够？

还是：

$$
\nabla J
========

\mathbb E[
R\nabla\log\pi
].
$$

问题：

$$
\boxed{\text{variance 太大}}
$$

假设两个题：

### Problem A 很简单

模型正常：

$$
P(\text{correct})=0.95.
$$

### Problem B 很难

$$
P(\text{correct})=0.05.
$$

单纯 reward：

$$
R\in{0,1}
$$

完全没有告诉 optimizer：

> 这一个 1 是“简单题正常做对”，还是“困难题的珍贵成功”。

所以需要：

$$
\boxed{\text{baseline / advantage}}
$$

---

# 十、最简单的 Advantage

定义：

$$
A=R-b.
$$

其中 baseline：

$$
b\approx\mathbb E[R|x].
$$

于是：

### 简单题

预期：

$$
0.95.
$$

做对：

$$
A=1-0.95=0.05.
$$

没什么惊喜。

做错：

$$
A=0-0.95=-0.95.
$$

这是非常值得纠正的失败。

---

### 难题

预期：

$$
0.05.
$$

做对：

$$
A=1-0.05=0.95.
$$

这是：

$$
\boxed{\text{珍贵成功}}
$$

值得强化。

这就是：

$$
\boxed{\text{relative success}}
$$

比绝对：

$$
0/1
$$

更有信息。

---

# 十一、PPO 为什么需要 Value Model？

传统 PPO 里面：

$$
V_\psi(s_t)
$$

预测：

> “从这个 prefix 往后，我预计还能拿多少 reward？”

然后：

$$
A_t
\approx
R_t-V_\psi(s_t)
$$

或通过 GAE：

$$
\hat A_t.
$$

于是完整 RLHF 系统变成：

```text
Policy model
Reward model
Value model
Reference model
```

再加：

```text
rollouts
GAE
importance ratios
PPO clipping
KL
```

非常复杂。

Stanford Lecture 16 花了不少时间重新从 policy gradient → TRPO → PPO，把这一条推了一遍，并强调 LLM PPO 在实际实现中有大量容易踩坑的细节。([GitHub][2])

---

# 十二、GRPO 的关键脑洞：我为什么还需要 Value Model？

假设一道题：

$$
x.
$$

不是只生成一个答案。

而是一次 sample：

$$
G=8
$$

个：

$$
y_1,\dots,y_8.
$$

得到：

$$
r_1,\dots,r_8.
$$

比如：

$$
[1,0,0,1,0,0,0,0].
$$

那么：

$$
\bar r
======

# \frac{2}{8}

0.25.
$$

现在直接：

$$
\boxed{
A_i
===

r_i-\bar r
}
$$

于是两个正确回答：

$$
A_{\rm good}
============

# 1-0.25

0.75.
$$

六个错误回答：

$$
A_{\rm bad}
===========

# 0-0.25

-0.25.
$$

你根本没有训练：

$$
V_\psi.
$$

直接用同一道题其他 samples：

$$
\boxed{\text{作为 relative baseline}}
$$

这就是：

$$
\boxed{\text{Group Relative}}
$$

的来源。

GRPO 最早由 DeepSeekMath 提出，目标之一就是删除 PPO 的 value model，从而降低 PPO 的额外显存和复杂度。([arXiv][4])

---

# 十三、标准 GRPO 又进一步做 Z-score

典型 GRPO：

$$
\boxed{
\hat A_i
========

\frac{
r_i-\mu_G
}{
\sigma_G+\epsilon
}
}
$$

其中：

$$
\mu_G
=====

\frac1G\sum_i r_i.
$$

然后 policy update 仍然保留 PPO 风格的重要性比率：

$$
\rho_{i,t}
==========

\frac{
\pi_\theta(y_{i,t}|s_{i,t})
}{
\pi_{\rm old}(y_{i,t}|s_{i,t})
}.
$$

于是概念上：

$$
\boxed{
L_{\rm GRPO}
\sim
----

\sum_{i,t}
\min(
\rho_{i,t}\hat A_i,
\operatorname{clip}(\rho_{i,t})\hat A_i
)
+
\beta KL
}
$$

Stanford Lecture 16 就是把 GRPO 解释成：

$$
\boxed{
\text{PPO}
----------

\text{Value Model}
+
\text{Group-normalized rewards}
}
$$

。([GitHub][2])

---

# 十四、GRPO 真正漂亮的地方：一道题自己提供 Counterfactual

同一道题：

```text
response A → correct
response B → wrong
response C → wrong
response D → correct
```

它们：

* prompt 相同；
  -知识需求相同；
  -难度相同；

只有 reasoning trajectory 不同。

所以可以直接问：

$$
\boxed{
\text{“在相同问题上，哪些生成行为比同伴更成功？”}
}
$$

这比跨不同题比较绝对 reward 干净很多。

---

# 十五、Binary Reward 下，GRPO 有一个特别漂亮的结构

设这一组：

$$
G
$$

个 responses 中，正确比例：

$$
\hat p.
$$

那么：

$$
\mu=\hat p.
$$

如果暂时不除标准差：

### Correct trajectory

$$
A_+
===

1-\hat p.
$$

### Incorrect trajectory

$$
A_-
===

-\hat p.
$$

所以当：

$$
\hat p=0.5
$$

正确：

$$
+0.5
$$

错误：

$$
-0.5.
$$

信号很好。

---

# 十六、如果一道题所有 sample 都正确呢？

$$
[1,1,1,1,1,1,1,1].
$$

则：

$$
\mu=1.
$$

所以：

$$
A_i=0.
$$

没有梯度信号。

合理：

> **这道题已经学会了。**

---

# 十七、如果全部错误呢？

$$
[0,0,0,0,0,0,0,0].
$$

则：

$$
\mu=0.
$$

还是：

$$
A_i=0.
$$

也没有梯度。

这非常关键。

因为它告诉你：

$$
\boxed{
\textbf{RLVR 最喜欢的题，
既不是太简单，也不是太难。}
}
$$

而是：

$$
\boxed{
0
<
P(\text{success})
<
1
}
$$

最好有：

$$
\boxed{\text{success / failure 混合}}
$$

这样 group 内才能形成 contrast。

---

# 十八、所以 Dataset Difficulty 本身就是 RL Algorithm 的一部分

这是 Lecture 16 一个非常深的思想。

SFT：

一条特别难的题，即使模型完全不会：

> 仍然有 teacher solution，可以 teacher-force。

RLVR：

如果一道题模型：

$$
P(\text{correct})\approx0
$$

那么你采：

$$
64
$$

次也可能全错。

得到：

$$
\boxed{\text{几乎零 learning signal}}
$$

所以：

$$
\boxed{
\text{RL training data 必须跟当前 policy 的能力匹配。}
}
$$

模型不断变强以后，difficulty 又会移动。

这就是为什么现代 RLVR 经常有：

$$
\boxed{\text{curriculum / dynamic sampling}}
$$

---

# 十九、Kimi k1.5 就把这件事做得特别明确

Kimi 会跟踪每个问题的 success rate：

$$
s_i.
$$

然后优先采模型做得不好的问题，例如：

$$
\boxed{
p_i\propto1-s_i
}
$$

同时使用 curriculum：

> 先更容易的问题，再逐渐进入更难的问题。

原因非常直观：一开始全上最难题，模型几乎采不到正确 trajectory，RL compute 基本白烧。Kimi k1.5 原论文就明确使用 curriculum sampling 和基于 success rate 的 prioritized sampling。([arXiv][5])

这就是：

$$
\boxed{
\textbf{RL Data Loader 本身就是一个在线 curriculum algorithm。}
}
$$

---

# 二十、但标准 GRPO 其实并没有那么“理论完美”

Stanford 2026 Lecture 16 非常值得注意的一点是：

> 它没有把 GRPO 当神圣算法。

反而专门讲了后续批评。

其中最重要两个问题：

$$
\boxed{\text{std normalization}}
$$

和：

$$
\boxed{\text{length normalization}}
$$

。([GitHub][2])

---

# 二十一、第一个坑：为什么除以 Group Standard Deviation 很可疑？

GRPO：

$$
\hat A_i
========

\frac{r_i-\mu}{\sigma}.
$$

减：

$$
\mu
$$

很好理解：

> 去除 problem difficulty baseline。

但是除：

$$
\sigma
$$

不只是 variance reduction。

它会改变：

$$
\boxed{\text{不同 prompts 的相对 gradient weight}}
$$

。

对于 binary reward：

$$
\sigma
\approx
\sqrt{p(1-p)}.
$$

因此：

$$
A_+
\approx
\frac{1-p}{\sqrt{p(1-p)}}
=========================

\sqrt{\frac{1-p}{p}}.
$$

如果：

$$
p=0.01,
$$

一个极罕见正确 sample 会得到非常大的 normalized advantage。

这相当于：

> **GRPO 自己重新定义了“哪种难度的问题更重要”。**

这不是一个无害的 baseline。

后来的 Dr. GRPO 工作正是批评这一类优化偏差，并提出更直接的修正。([arXiv][6])

---

# 二十二、第二个坑：Response Length

很多 GRPO 实现还会对一条 response 的 token losses 做：

$$
\frac1{T_i}
\sum_{t=1}^{T_i}
\ell_{i,t}.
$$

这意味着 sequence 的 gradient weighting 和：

$$
T_i
$$

绑定。

在标准 GRPO 的实际 objective 下，会产生 length-related optimization bias：错误长回答可能被相对轻罚，而正确短回答可能获得更高效的正向更新，从而产生奇怪的长度激励。Stanford Lecture 16 特别强调：部分“CoT 越训越长”的现象可能并不完全是模型自动发现“想得越久越聪明”，而是 objective 本身存在长度偏差。([GitHub][2])

这点非常重要。

---

# 二十三、所以 R1-Zero 的“思维越来越长”不能太浪漫化

DeepSeek-R1 论文里一个很著名的图：

随着 RL：

$$
\boxed{\text{response length}\uparrow}
$$

同时：

$$
\boxed{\text{accuracy}\uparrow}.
$$

作者把它解释成：

> 模型开始花更多 test-time compute solving hard problems。

并观察到模型会产生：

```text
Wait...
Let me reconsider...
I made a mistake...
Let's try another approach...
```

也就是著名：

$$
\boxed{\text{“Aha moment”}}
$$

。([arXiv][7])

这确实很有意思。

但 Stanford Lecture 16 特别提醒：

后续工作发现 DeepSeek-V3-Base 本身就已经会出现类似 self-reflection；GRPO 本身又存在 length bias。换句话说：

$$
\boxed{
\text{RL 很可能是在强化已有 reasoning behavior，
而不是凭空发明 “aha”。}
}
$$

Dr. GRPO 的分析正是其中代表。([arXiv][6])

这是比“RL 让模型突然学会思考”更准确的理解。

---

# 二十四、现在正式看 DeepSeek-R1-Zero

整个 recipe 令人吃惊地简单：

$$
\boxed{
\text{DeepSeek-V3-Base}
\rightarrow
\text{GRPO}
}
$$

没有先做：

$$
\boxed{\text{long-CoT SFT}}
$$

主要 reasoning reward：

$$
\boxed{
R
=

R_{\rm accuracy}
+
R_{\rm format}
}
$$

Accuracy：

数学答案 / code tests。

Format：

例如要求 reasoning 放在：

```text
<think>
...
</think>
```

。DeepSeek 明确把 R1-Zero 定义为直接从 base model 做大规模 RL；它确实取得很强 reasoning，但也出现 readability 和 language mixing 问题。([arXiv][8])

这就是 R1-Zero 最重要的 scientific experiment：

$$
\boxed{
\textbf{只靠 outcome RL，
base model 的 reasoning 能力究竟能被推多远？}
}
$$

---

# 二十五、R1-Zero 的问题也非常明显

纯 RL 后出现：

```text
超长 CoT
中英文混杂
奇怪格式
可读性差
```

这说明：

$$
\boxed{
\text{verifiable reward 只关心“对不对”，
不关心“人喜不喜欢读”。}
}
$$

如果：

```text
中文 → 英文 → 中文 → Python → 自言自语
```

最后答案对了：

$$
R_{\rm accuracy}=1.
$$

RL 没理由修。

所以：

$$
\boxed{\text{Objective 决定 behavior}}
$$

这又回到了 Lecture 12–15 反复讲的核心。

---

# 二十六、因此真正 DeepSeek-R1 不再是“纯 RL”

R1 采用四阶段式路线，核心可以概括成：

```text
Base
 ↓
① Cold-start long-CoT SFT
 ↓
② Reasoning RL
 ↓
③ Rejection sampling + SFT
 ↓
④ General RL / alignment
```

DeepSeek 报告 cold start 使用数千条 long-CoT data；reasoning RL 后又采样约 600k reasoning examples，加上约 200k non-reasoning examples 做 SFT，然后再继续对 general scenarios 做 RL。([arXiv][7])

所以真正工程结论不是：

$$
\boxed{\text{SFT 已经没用了，全部 GRPO}}
$$

而是：

$$
\boxed{
\text{SFT 和 RL 承担不同职责。}
}
$$

---

# 二十七、我会怎么区分 R1 Pipeline 中 SFT 和 RL 的职责？

## SFT

给一个：

$$
\boxed{\text{reasonable initial reasoning distribution}}
$$

例如：

```text
可读
格式稳定
会输出 long CoT
不乱混语言
```

也就是：

$$
\boxed{\text{Behavior prior}}
$$

---

## RLVR

在这个 distribution 内：

$$
\boxed{\text{利用真实 correctness signal 找更好的 reasoning strategy}}
$$

所以你可以粗略记：

$$
\boxed{
\text{SFT = teach the language of reasoning}
}
$$

$$
\boxed{
\text{RLVR = optimize reasoning for success}
}
$$

这两者不是竞争关系。

---

# 二十八、一个很有意思的问题：既然 final answer reward 已经够用，为什么不使用 Process Reward Model？

直觉上 PRM 更高级。

CoT：

```text
Step 1 → reward
Step 2 → reward
Step 3 → reward
...
```

比只给：

```text
final answer → reward
```

credit assignment 明显更好。

DeepSeek 确实试过。

但他们报告的问题包括：

* reasoning 中“一个 step”很难定义；
* 判断 intermediate step 是否正确很难；
* 人工标注不能 scale；
* neural PRM 又重新带回 reward hacking；
* 训练和维护 PRM 增加大量复杂度。

因此在他们的大规模 R1 实验中，PRM 的收益没有抵消额外代价。([arXiv][7])

注意：

$$
\boxed{
\text{这不是证明 PRM 永远没用。}
}
$$

只是：

> **R1 这套工程实验中，简单 outcome reward 更划算。**

---

# 二十九、MCTS 为什么也没有成为 R1 的核心？

AlphaGo：

$$
\boxed{\text{MCTS}}
$$

极其成功。

自然会想：

> 那 reasoning 也做 tree search 不就好了？

问题是棋：

$$
\boxed{\text{state/action 非常明确}}
$$

而自然语言 reasoning：

> 一个“reasoning step”到底是什么？

一句话？

一个 token？

一个 equation？

一个 paragraph？

而每个节点可继续生成的自然语言空间又几乎无限。

DeepSeek 报告 MCTS 在 inference 时可以带来帮助，但把它扩展成稳定的 self-improving training loop 很困难，尤其依赖高质量 value model，而 token-generation search space 也非常巨大。([arXiv][7])

于是 R1 最令人惊讶的 lesson 之一反而是：

$$
\boxed{
\textbf{Simple sampling + RL
竟然可以比复杂 search pipeline 更实用。}
}
$$

---

# 三十、R1 还有一个很重要的结论：小模型优先 Distill

大 reasoning model：

$$
\boxed{\text{R1}}
$$

已经产生大量优秀：

$$
(x,\text{CoT},y)
$$

trajectory。

那么对于 1.5B / 7B / 14B / 32B：

为什么非要：

$$
\boxed{\text{重新从 0/1 reward 慢慢探索？}}
$$

直接 SFT imitation：

$$
\boxed{\text{Distillation}}
$$

往往便宜得多。

DeepSeek 自己的实验就发现，32B 模型直接做大规模 R1-Zero 式 RL，仍明显不如从强 R1 reasoning traces distill 的 32B 模型。([arXiv][7])

所以非常重要的经验：

$$
\boxed{
\textbf{Frontier model：RL 可能负责发现；
Small model：Distillation 往往负责继承。}
}
$$

这其实对你看很多 1.5B reasoning 工作非常有帮助。

---

# 三十一、Kimi k1.5 给 Lecture 16 带来的第一个新视角：Context Length 本身就是 RL Scaling Axis

DeepSeek R1 给人的印象是：

> RL steps 越多，CoT 越长。

Kimi k1.5 更明确提出：

$$
\boxed{\text{Long-context RL scaling}}
$$

把 reasoning context 最终扩到：

$$
128K.
$$

他们发现随着可用 reasoning context 增大，困难任务还可以持续改善；论文甚至把 context length 视为 RL scaling 的一个关键维度。([arXiv][5])

也就是说以前 scaling：

$$
\boxed{\text{model size}}
$$

$$
\boxed{\text{training tokens}}
$$

现在 reasoning model 又增加：

$$
\boxed{\text{test-time reasoning tokens}}
$$

这一轴。

---

# 三十二、于是“模型大小”和“思考长度”可以发生替代

Kimi 的 ablation 很有意思：

更大的模型一开始当然更强。

但是较小模型如果通过 RL 学会使用更长 CoT：

$$
\boxed{\text{性能可以追近较大模型}}
$$

不过大模型通常仍然更 token-efficient、upper bound 更高。([arXiv][5])

所以现在出现一种新的 compute trade-off：

$$
\boxed{
\text{Model FLOPs per token}
\times
\text{Reasoning tokens}
}
$$

你可以：

```text
大模型 × 短思考
```

或者：

```text
小模型 × 长思考
```

这就是：

$$
\boxed{\text{Test-Time Scaling}}
$$

真正开始变成经济学问题。

---

# 三十三、但 CoT 无限增长当然不行

Recall Lecture 10：

每多生成一个 token：

$$
\boxed{\text{都要支付 inference cost}}
$$

所以：

$$
accuracy\uparrow
$$

同时：

$$
tokens\uparrow
$$

并不自动意味着系统更好。

Kimi k1.5 因此专门加入 length reward，对正确 outputs 倾向鼓励更短 reasoning，并且不会在训练一开始马上强压长度，而是在 later stage 再逐步启用 penalty，避免 reasoning 还没学会就被迫“少想”。([arXiv][5])

这就是非常漂亮的：

$$
\boxed{
\text{Capability first}
\rightarrow
\text{Efficiency later}
}
$$

---

# 三十四、Kimi 还告诉你：RLVR 真正的工程瓶颈其实是 Rollout

SFT：

```text
read fixed data
↓
forward
↓
backward
```

RLVR：

```text
current policy
↓
generate very long outputs
↓
verify
↓
compute advantage
↓
train
↓
new policy
↓
repeat
```

生成本身：

$$
\boxed{\text{autoregressive}}
$$

非常慢。

而且：

```text
Question A → 1000 tokens
Question B → 15000 tokens
Question C → 80000 tokens
```

batch 极其不规则。

Kimi k1.5 论文专门讨论了 long-context RL infrastructure 和 partial rollouts：重用已有 trajectory 前缀，避免每次都从头生成，从而提高 RL 系统效率。([arXiv][5])

所以：

$$
\boxed{
\textbf{Reasoning RL 的核心问题一半是 RL 算法，
另一半是 inference systems。}
}
$$

Lecture 7–10 的知识又全部回来了。

---

# 三十五、Qwen3 又进一步解决一个产品问题

R1 风格 reasoning model：

> 遇到“你好”也想半天。

这显然很浪费。

简单问题：

$$
\boxed{\text{不需要 10K CoT}}
$$

困难数学：

$$
\boxed{\text{可能需要 20K CoT}}
$$

所以 Qwen3 把：

$$
\boxed{\text{thinking}}
$$

和：

$$
\boxed{\text{non-thinking}}
$$

放进同一个模型。

官方 Qwen3 Technical Report 描述的 post-training 大致是：

$$
\boxed{
1.\ Long-CoT Cold Start
}
$$

$$
\boxed{
2.\ Reasoning RL
}
$$

$$
\boxed{
3.\ Thinking Mode Fusion
}
$$

$$
\boxed{
4.\ General RL
}
$$

。([arXiv][9])

---

# 三十六、Thinking Mode Fusion 到底是什么？

训练数据同时存在：

```text
/think
```

和：

```text
/no_think
```

模式。

于是：

### Think

```text
User: solve this /think

Assistant:
<think>
...
long reasoning
...
</think>
answer
```

### No Think

```text
User: hello /no_think

Assistant:
<think>
</think>
Hello!
```

最终同一个模型可以：

$$
\boxed{\text{根据 inference flag 改变 reasoning budget}}
$$

。Qwen3 的官方技术报告就是通过 continual SFT 把 thinking/non-thinking 数据融合进 reasoning-RL 模型。([优视媒体][10])

---

# 三十七、然后就可以人为控制 Thinking Budget

假设最大允许：

$$
8192
$$

thinking tokens。

生成到阈值后直接插入：

```text
I need to answer based on the reasoning so far.
</think>
```

然后让模型给 final answer。

于是：

$$
\boxed{\text{budget}=0}
$$

可以变成 fast model。

$$
\boxed{\text{budget}=2K}
$$

中等 reasoning。

$$
\boxed{\text{budget}=16K}
$$

困难任务充分思考。

Qwen3 报告这种 thinking-budget 控制能够实现较平滑的 performance–inference-cost trade-off。([优视媒体][10])

所以 reasoning model 的产品目标开始从：

$$
\boxed{\max accuracy}
$$

变成：

$$
\boxed{
\max\text{ quality}
\quad
\text{s.t. reasoning budget}
}
$$

---

# 三十八、这就把 Lecture 9 和 Lecture 16 接起来了

Lecture 9：

$$
\boxed{
\text{Training compute scaling}
}
$$

问：

$$
N,D
$$

应该怎么增长。

Lecture 16：

$$
\boxed{
\text{Test-time compute scaling}
}
$$

又问：

$$
\boxed{\text{给单个问题多少 reasoning tokens？}}
$$

所以一个模型的能力不再只有：

$$
f(N,D).
$$

还开始变成：

$$
\boxed{
\text{Performance}
==================

f(
N,
D,
C_{\rm RL},
C_{\rm test}
)
}
$$

其中：

$$
C_{\rm test}
$$

是 inference/test-time compute。

这就是 reasoning model 时代最重要的变化之一。

---

# 三十九、RLVR 是不是就彻底没有 Reward Hacking 了？

不是。

假设 verifier：

```python
return predicted_answer == ground_truth
```

模型可能学会：

* 猜答案分布；
* exploit parser；
* 输出多个答案；
* 利用格式 loophole。

Coding verifier 也可能：

```text
通过测试
```

但代码实际逻辑错误，因为：

$$
\boxed{\text{tests coverage 不完整}}
$$

这就是 Lecture 12 的：

$$
\boxed{\text{verifier hacking}}
$$

重新回来。

所以：

$$
\boxed{
\text{Verifiable}
\neq
\text{Perfectly specified}
}
$$

RLVR 只是把 reward 从：

$$
\text{learned fuzzy proxy}
$$

变成：

$$
\text{通常更可靠的 executable/rule proxy}.
$$

---

# 四十、为什么 Multiple Choice 甚至不是特别好的 RLVR Data？

假设四选一。

完全随机：

$$
P(\text{reward}=1)
==================

25%.
$$

模型根本不会 reasoning：

> 也有 25% success。

这种：

$$
\boxed{\text{false positive reward}}
$$

非常危险。

自由答案数学题：

随机猜中：

$$
\approx0.
$$

所以 reward 更可信。

这也是为什么 Kimi 等 reasoning recipe 会特别谨慎处理 multiple choice / true-false data，并强调可可靠验证、低误判的训练任务。Lecture 16 的 Kimi case study 也特别指出了这一点。([GitHub][2])

---

# 四十一、为什么 RLVR 很难直接扩展到“写一篇好小说”？

因为：

$$
\boxed{\text{没有 objective verifier}}
$$

小说：

> 好不好？

只能让：

$$
\text{human}
$$

或：

$$
\text{LLM judge}
$$

评。

于是又回到：

$$
\boxed{\text{RLHF / RLAIF}}
$$

及其 learned-proxy 问题。

所以 RLVR 特别强的地方通常是：

```text
math
coding
formal proof
games
tool environments
structured tasks
```

即：

$$
\boxed{\text{outcome can be checked}}
$$

的领域。

Lecture 16 自己最后也把“RLVR 能否泛化到更开放任务”列为开放问题。([GitHub][2])

---

# 四十二、RLVR 能不能给模型注入全新知识？

通常不能指望它做这件事。

假设模型根本不知道：

$$
\text{某个高级代数定理}.
$$

而所有 sampled trajectories：

$$
\boxed{\text{全错}}
$$

那么 group：

$$
[0,0,0,0,0,0,0,0].
$$

Advantage：

$$
0.
$$

没有 learning signal。

所以 RLVR 需要：

$$
\boxed{\text{探索空间里至少偶尔出现成功轨迹}}
$$

。

这又解释为什么：

$$
\boxed{\text{Base model quality 非常关键}}
$$

以及为什么 math continued pretraining、cold-start SFT、distillation 等仍然重要。

你可以把它总结成：

$$
\boxed{
\textbf{RL is better at amplifying discoverable behavior
than creating missing knowledge from nothing.}
}
$$

---

# 四十三、所以为什么 R1 的 Small Model 最后选择 Distillation？

因为对于 small model：

$$
P(\text{自己探索出正确高阶 trajectory})
$$

可能非常小。

强 teacher 已经知道：

$$
\boxed{\text{成功 trajectory}}
$$

那直接：

$$
\boxed{\text{SFT}}
$$

就是一个高密度 token-level supervision。

相比：

$$
\text{0/1 sparse reward}
$$

当然 sample efficient 得多。

所以：

$$
\boxed{
\text{SFT / Distillation：高密度 supervision}
}
$$

vs

$$
\boxed{
\text{RLVR：低密度但能超越 demonstrations 的 online optimization}
}
$$

这是非常值得记住的一组 trade-off。

---

# 四十四、现在可以真正理解 SFT、DPO、RLHF、RLVR 的区别

| 方法        | 数据来源             | Feedback        | Online? | 最大特点                   |
| --------- | ---------------- | --------------- | ------- | ---------------------- |
| SFT       | Demonstrations   | 每 token target  | 否       | 模仿                     |
| DPO       | Preference pairs | winner vs loser | 通常否     | 简单 preference learning |
| PPO-RLHF  | Policy rollout   | Learned reward  | 是       | 灵活但 reward 可 hack      |
| GRPO-RLVR | Policy rollout   | Verifier reward | 是       | 无 critic、适合 reasoning  |

最重要的不是算法名字。

而是两个问题：

$$
\boxed{\text{Feedback 从哪里来？}}
$$

以及：

$$
\boxed{\text{Data 是 static 还是 current policy 自己生成？}}
$$

---

# 四十五、On-Policy 是 Lecture 16 特别重要的一个词

DPO data：

$$
\boxed{\text{固定}}
$$

可能来自几周前的旧模型。

随着 model 更新：

$$
\pi_\theta
$$

distribution 变了。

旧 pairs：

> 可能已经太简单、太远、没有学习价值。

RLVR：

```text
当前 policy
↓
现场 rollout
↓
现场 verify
↓
现场 update
```

于是训练数据跟：

$$
\boxed{\text{当前模型 distribution}}
$$

一起移动。

这就是：

$$
\boxed{\text{On-policy}}
$$

的巨大优势。

但代价就是：

$$
\boxed{\text{贵}}
$$

因为每一步都需要重新推理生成大量 trajectories。

---

# 四十六、这就是为什么 RL Infra 突然变成前沿 Infra

传统 training：

$$
\boxed{\text{training throughput}}
$$

最重要。

RL：

你同时需要：

$$
\boxed{\text{rollout inference throughput}}
$$

和：

$$
\boxed{\text{training throughput}}
$$

而且二者模型权重还需要不断同步。

大概：

```text
Actor / rollout workers
        ↓
trajectories
        ↓
verifier
        ↓
trainer
        ↓
new checkpoint
        ↓
actors update weights
```

所以你需要考虑：

```text
vLLM/SGLang
FSDP
tensor parallel
asynchronous rollout
weight sync
KV cache
long sequences
stragglers
packing
```

这就是为什么 Lecture 16 末尾会特别强调 RL infrastructure。([GitHub][2])

这也是今天：

```text
VERL
SLIME
OpenRLHF
OAT
...
```

这一类 RL infra 突然非常重要的根本原因。

---

# 四十七、2026 A5 和 Lecture 16 几乎直接一一对应

官方 CS336 网站在 Lecture 16 当天发布：

$$
\boxed{\text{Assignment 5: Alignment and Reasoning RL}}
$$

目标就是：

> 对语言模型做 SFT + reinforcement learning，让它解决数学 reasoning tasks。([GitHub][1])

官方仓库：

```text
tests/test_grpo.py
```

就是直接测试你的 GRPO 实现。([GitHub][11])

而且 2026-05-20 的 A5 v2.0 还加入了：

$$
\boxed{\text{MaxRL}}
$$

和：

$$
\boxed{\text{GSPO}}
$$

等进一步实验；adapter 已经暴露了：

```text
baseline = mean / none
advantage_normalizer = std / none / mean
importance_reweighting = none / noclip / grpo / gspo
loss_normalization = sequence / constant
```

这些参数实际上就是让你**亲手验证 Lecture 16 讲的 GRPO 各个设计选择到底有没有问题**。([GitHub][12])

所以 A5 真正有意思的地方，并不是：

> “复现一个 GRPO loss。”

而是：

$$
\boxed{
\textbf{把 GRPO 拆成多个设计 knob，
逐项实验它们如何改变训练。}
}
$$

这很 CS336。

---

# 四十八、如果你真的要把 Lecture 16 学懂，我认为必须掌握这 5 条公式

## 1. Policy gradient

$$
\boxed{
\nabla_\theta J
===============

\mathbb E[
R
\nabla_\theta\log\pi_\theta(y|x)
]
}
$$

理解：

> 成功 trajectory 概率 ↑，失败 trajectory 概率 ↓。

---

## 2. Baseline

$$
\boxed{
A=R-b
}
$$

理解：

> 不是问“好不好”，而是问“比预期好多少”。

---

## 3. Group baseline

$$
\boxed{
A_i
===

r_i-\frac1G\sum_jr_j
}
$$

理解：

> 同一道题多个 rollout 互相做 baseline。

---

## 4. GRPO normalized advantage

$$
\boxed{
\hat A_i
========

\frac{r_i-\mu_G}
{\sigma_G+\epsilon}
}
$$

同时一定要知道：

> 除 (\sigma_G) 不是理所当然，它会改变 problem weighting。

---

## 5. PPO / GRPO importance ratio

$$
\boxed{
\rho_t
======

\frac{
\pi_\theta(a_t|s_t)
}{
\pi_{\rm old}(a_t|s_t)
}
}
$$

以及：

$$
\boxed{
\min(
\rho_t A,
\operatorname{clip}(\rho_t,1-\epsilon,1+\epsilon)A
)
}
$$

理解：

> rollout 来自旧 policy，但不能让新 policy 一步跑得太远。

---

# 四十九、给你 10 道 Lecture 16 自测题

### 1. 为什么 RLVR 比 RLHF 更不容易 reward overoptimization？

因为 reward 来自 executable/rule verifier，而不是从有限 preference data 拟合的 reward model。

但 verifier 仍可能有 specification loopholes。

---

### 2. 为什么 final-answer-only reward 也可以训练 reasoning？

因为 policy gradient 会增加整个成功 trajectory 的 likelihood；base model 已经提供合理 reasoning prior。

---

### 3. GRPO 为什么可以删除 Value Model？

因为同一 prompt 的多个 rollouts 可以用 group reward mean 估计 relative performance。

---

### 4. 如果一个 prompt 的 8 个 rollouts reward 是：

$$
[1,1,0,0,0,0,0,0]
$$

不用 std normalization 时：

$$
\mu=0.25.
$$

正确 advantage：

$$
\boxed{0.75}
$$

错误：

$$
\boxed{-0.25}
$$

---

### 5. 为什么全部正确或全部错误都几乎没有 group-relative signal？

因为：

$$
r_i-\bar r=0.
$$

所以 RLVR 数据必须有合适 difficulty。

---

### 6. 为什么 GRPO 的 std normalization 不是一个纯粹无害的 variance-reduction trick？

因为它会按：

$$
1/\sigma_G
$$

重新缩放不同问题的 gradient，从而改变问题难度权重。

---

### 7. 为什么不能看到 R1-Zero CoT 越来越长，就直接得出“RL 自动发明了更深 reasoning”？

因为 base model 已经存在 self-reflection behavior，而且标准 GRPO 的 length normalization 本身存在增长 response length 的 optimization bias。([arXiv][6])

---

### 8. 为什么 DeepSeek-R1 最后还是加入 Cold-Start SFT？

为了：

```text
readability
stable reasoning format
减少 language mixing
提供更好的 initial policy
```

纯 RL 的 reward 并不关心这些行为。([arXiv][7])

---

### 9. 为什么 small reasoning model 常常 distillation 比直接 RL 更划算？

强 teacher 已经给出成功 trajectory，SFT 提供 dense token-level supervision；小模型自己用 sparse 0/1 reward 探索成功 trajectory 非常昂贵。DeepSeek 自己也观察到其 32B distilled model 明显强于直接做大规模 R1-Zero 式 RL 的对应模型。([arXiv][7])

---

### 10. 为什么 Qwen3 的 thinking budget 是一个重要新方向？

因为 reasoning quality 和 inference cost 同时取决于生成多少 thinking tokens，于是模型应该允许：

$$
\boxed{
\text{performance}
\leftrightarrow
\text{test-time compute}
}
$$

连续调节，而不是简单“永远思考”或“永远不思考”。([arXiv][9])

---

# 最后，把 Lecture 16 压成一块黑板

第一行我会写：

$$
\boxed{
\text{RLHF}
===========

\text{optimize a learned proxy reward}
}
$$

然后：

$$
\boxed{
\text{RLVR}
===========

\text{optimize an executable/verifiable outcome}
}
$$

再写：

$$
\boxed{
\text{PPO}
==========

\text{Policy + Value + Advantage + Clip}
}
$$

然后：

$$
\boxed{
\text{GRPO}
===========

## \text{PPO}

\text{Value Model}
+
\text{Group Relative Reward}
}
$$

再写：

$$
\boxed{
\text{R1-Zero}
==============

\text{Base Model}
+
\text{Outcome RL}
}
$$

而真正实用的：

$$
\boxed{
\text{R1}
=========

\text{Cold-start SFT}
+
\text{RLVR}
+
\text{Distillation/SFT}
+
\text{General Alignment}
}
$$

最后写最大的一句话：

$$
\boxed{
\textbf{Reasoning RL 的力量，并不在于告诉模型每一步该怎么想；
而在于让模型自己探索很多思考轨迹，
然后用可靠的最终结果不断筛选和强化成功策略。}
}
$$

但 Lecture 16 同时又故意给这波“RL 热”泼了一盆非常必要的冷水：

$$
\boxed{
\textbf{Longer CoT 不自动等于更深 reasoning，GRPO 也不是最终算法。}
}
$$

你必须同时检查：

$$
\text{Reward}
$$

有没有 loophole，

$$
\text{Objective}
$$

有没有 length/difficulty bias，

$$
\text{Base Model}
$$

原本就会什么，

$$
\text{Data}
$$

是不是处在有 learning signal 的难度区间，

以及：

$$
\text{Rollout Infra}
$$

是否真的足够高效。

所以我认为 Lecture 16 真正的主题甚至不是 **“GRPO”**，而是：

$$
\boxed{
\textbf{如何把可验证环境转化成可扩展的自我改进信号。}
}
$$

这也正是为什么它会直接成为 CS336 A5 的主体。
