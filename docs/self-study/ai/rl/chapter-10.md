---
id: rl-chapter-10
title: 第10章 Actor-Critic 方法
sidebar_label: 第10章
---

import { NoteBlock } from '@site/src/components/HighlightBlock';

# Actor-Critic Methods

从一个角度来看，"Actor-Critic" 指的是一种融合了基于策略（policy-based）和基于价值（value-based）方法的结构：其中，"**演员（Actor）**" 对应策略更新步骤，之所以称为 "演员"，是因为智能体通过遵循策略来执行动作；"**评论家（Critic）**" 对应价值更新步骤，之所以称为 "评论家"，是因为它通过评估 "演员"（策略）的对应价值来对其进行评判。

从另一个角度来看，Actor-Critic 方法本质上仍是策略梯度算法，可通过对第 9 章介绍的策略梯度算法进行扩展得到。

## The simplest actor-critic algorithm (QAC)

回顾策略梯度方法的核心思想：通过最大化标量指标 $J(\theta)$ 来寻找最优策略。用于最大化 $J(\theta)$ 的梯度上升算法为：

$$
\begin{aligned}
\theta_{t+1} &= \theta_{t}+\alpha \nabla _{\theta }J(\theta _{t}) \\
&= \theta _{t}+\alpha \mathbb {E}_{S\sim \eta ,A\sim \pi }\left[ \nabla _{\theta }\ln \pi (A|S,\theta _{t})q_{\pi }(S,A) \right] \tag{10.1}
\end{aligned}
$$

其中，$\eta$ 表示状态分布（更多信息参见定理 9.1）。

由于真实梯度无法直接获取，我们可使用随机梯度对其进行近似，得到：

$$
\begin{aligned}
\theta _{t+1}=\theta _{t}+\alpha \nabla _{\theta }\ln \pi (a_{t}|s_{t},\theta _{t})q_{t}(s_{t},a_{t}) \tag{10.2}
\end{aligned}
$$

该式与第 9 章中式（9.32）给出的算法一致。

式（10.2）的重要性在于，它清晰地展示了基于策略和基于价值的方法如何结合：

- **一方面**，它属于基于策略的算法，因为其直接更新策略参数 $\theta$；
- **另一方面**，该式需要用到 $q_{t}(s_{t}, a_{t})$（即动作价值 $q_{\pi}(s_{t}, a_{t})$ 的估计值），因此需要另一个基于价值的算法来生成 $q_{t}(s_{t}, a_{t})$。

截至目前，本书已介绍过两种估计动作价值的方法：

1. **第一种基于蒙特卡洛（Monte Carlo）学习**
2. **第二种基于时序差分（Temporal-Difference，TD）学习**

若通过蒙特卡洛学习估计 $q_{t}(s_{t}, a_{t})$，对应的算法称为 **REINFORCE 算法**（或蒙特卡洛策略梯度算法），该算法已在第 9 章中介绍；若通过 TD 学习估计 $q_{t}(s_{t}, a_{t})$，对应的算法通常称为 "**演员-评论家算法**"。

因此，演员-评论家方法可通过 "**将基于 TD 的价值估计融入策略梯度方法**" 得到。
<NoteBlock title="Algorithm 10.1: The simplest actor-critic algorithm (QAC)">

**Initialization**: A policy function $\pi(a|s, \theta_0)$ where $\theta_0$ is the initial parameter. A value function $q(s, a, w_0)$ where $w_0$ is the initial parameter. $\alpha_w, \alpha_{\theta} > 0$.

**Goal**: Learn an optimal policy to maximize $J(\theta)$.

**At time step $t$ in each episode**, do:

1. Generate $a_t$ following $\pi(a|s_t, \theta_t)$, observe $r_{t+1}, s_{t+1}$, and then generate $a_{t+1}$ following $\pi(a|s_{t+1}, \theta_t)$.
2. **Actor (policy update)**:
   $$
   \theta_{t+1} = \theta_t + \alpha_{\theta}\nabla_{\theta} \ln \pi(a_t|s_t, \theta_t)q(s_t, a_t, w_t)
   $$
3. **Critic (value update)**:
   $$
   w_{t+1} = w_t + \alpha_w \left[ r_{t+1} + \gamma q(s_{t+1}, a_{t+1}, w_t) - q(s_t, a_t, w_t) \right] \nabla_w q(s_t, a_t, w_t)
   $$

</NoteBlock>
最简单的演员-评论家算法流程总结于算法 10.1 中：

- **评论家（Critic）**：对应通过式（8.35）所示的 Sarsa 算法实现的价值更新步骤，动作价值由参数化函数 $q(s, a, w)$ 表示；
- **演员（Actor）**：对应式（10.2）所示的策略更新步骤。

该演员-评论家算法有时也被称为 **Q 演员-评论家（Q Actor-Critic，QAC）**。尽管结构简单，但 QAC 揭示了演员-评论家方法的核心思想，后续可基于其扩展出多种更复杂的进阶算法。

## Advantage actor-critic (A2C)

该算法的核心思想是引入**基线（baseline）**以降低估计方差。
### Baseline invariance
策略梯度有一个有趣的性质：它对额外引入的基线具有不变性。即：

$$\mathbb{E}_{S\sim \eta,A\sim \pi}\left[ \nabla _{\theta } \ln \pi (A|S, \theta_t)q_{\pi }(S, A) \right] = \mathbb{E}_{S\sim \eta,A\sim \pi}\left[ \nabla _{\theta } \ln \pi (A|S, \theta_t)\left(q_{\pi }(S, A) - b(S)\right) \right] \tag{10.3}$$

其中，额外基线 $b(S)$ 是关于状态 $S$ 的标量函数。

接下来我们回答关于基线的两个问题。

**第一，式（10.3）为何成立？**

式（10.3）成立的充要条件是：

$$\mathbb{E}_{S\sim \eta,A\sim \pi}\left[ \nabla _{\theta } \ln \pi (A|S, \theta_t)b(S) \right] = 0$$

该等式成立的推导过程如下：

$$\begin{aligned}
\mathbb{E}_{S\sim \eta,A\sim \pi}\left[ \nabla _{\theta } \ln \pi (A|S, \theta_t)b(S) \right] 
&= \sum_{s \in \mathcal{S}} \eta(s) \sum_{a \in \mathcal{A}} \pi(a|s, \theta_t) \nabla_{\theta} \ln \pi(a|s, \theta_t) b(s) \\
&= \sum_{s \in \mathcal{S}} \eta(s) \sum_{a \in \mathcal{A}} \nabla_{\theta} \pi(a|s, \theta_t) b(s) \\
&= \sum_{s \in \mathcal{S}} \eta(s) b(s) \sum_{a \in \mathcal{A}} \nabla_{\theta} \pi(a|s, \theta_t) \\
&= \sum_{s \in \mathcal{S}} \eta(s) b(s) \nabla_{\theta} \sum_{a \in \mathcal{A}} \pi(a|s, \theta_t) \\
&= \sum_{s \in \mathcal{S}} \eta(s) b(s) \nabla_{\theta} 1 = 0
\end{aligned}$$

（注：任意状态下所有动作的概率和为 1，即 $\sum_{a \in \mathcal{A}} \pi(a|s, \theta_t) = 1$，而常数的梯度为 0，因此最终结果为 0。）

**第二，基线为何有用？**

基线之所以有用，是因为当我们使用样本近似真实梯度时，它能降低近似方差。具体来说，令：

$$X(S, A) \doteq \nabla_{\theta} \ln \pi(A|S, \theta_t)\left[q_{\pi}(S, A) - b(S)\right] \tag{10.4}$$

此时，真实梯度即为 $\mathbb{E}[X(S, A)]$。由于我们需要使用随机样本 $x$ 来近似 $\mathbb{E}[X]$，因此若方差 $\text{var}(X)$ 较小，会更有利于近似 —— 例如，若 $\text{var}(X)$ 接近 0，则任意样本 $x$ 都能准确近似 $\mathbb{E}[X]$；反之，若 $\text{var}(X)$ 较大，则单个样本的值可能与 $\mathbb{E}[X]$ 相差甚远。

尽管 $\mathbb{E}[X]$ 对基线具有不变性，但方差 $\text{var}(X)$ 并不具备这一性质。我们的目标是设计一个优良的基线，以最小化 $\text{var}(X)$。

在 REINFORCE 算法和 QAC 算法中，我们将基线设为 $b = 0$，但这一设置并不能保证是优良的基线。事实上，能最小化 $\text{var}(X)$ 的最优基线为：

$$b^*(s) = \frac{\mathbb{E}_{A \sim \pi}\left[ \left\| \nabla_{\theta} \ln \pi(A|s, \theta_t) \right\|^2 q_{\pi}(s, A) \right]}{\mathbb{E}_{A \sim \pi}\left[ \left\| \nabla_{\theta} \ln \pi(A|s, \theta_t) \right\|^2 \right]}, \quad s \in \mathcal{S} \tag{10.5}$$

其证明过程直接跳过有缘再见。

尽管式（10.5）中的基线是最优的，但它过于复杂，难以在实际中应用。若从式（10.5）中移除权重项 $\left\| \nabla_{\theta} \ln \pi(A|s, \theta_t) \right\|^2$，可得到一个次优但表达式简洁的基线：

$$b^{\dagger}(s) = \mathbb{E}_{A \sim \pi}\left[ q_{\pi}(s, A) \right] = v_{\pi}(s), \quad s \in \mathcal{S}$$

有趣的是，这个次优基线正是状态价值 $v_{\pi}(s)$。


### Algorithm Description
当 $b(s) = v_\pi(s)$ 时，式（10.1）中的梯度上升算法可写为：

$$\begin{aligned}
\theta_{t+1} &= \theta_t + \alpha \mathbb{E}\left[ \nabla_\theta \ln \pi(A|S, \theta_t) \left[ q_\pi(S, A) - v_\pi(S) \right] \right] \\
&\doteq \theta_t + \alpha \mathbb{E}\left[ \nabla_\theta \ln \pi(A|S, \theta_t) \delta_\pi(S, A) \right] \tag{10.7}
\end{aligned}$$

其中，$\delta_\pi(S, A) \doteq q_\pi(S, A) - v_\pi(S)$ 被称为优势函数（advantage function），它反映了某一动作相对于其他动作的优势。更具体地说，注意到 $v_\pi(s) = \sum_{a \in \mathcal{A}} \pi(a|s) q_\pi(s, a)$ 是动作价值的均值：若 $\delta_\pi(s, a) > 0$，则说明对应动作的价值高于均值。

式（10.7）的随机版本为：

$$\begin{aligned}
\theta_{t+1} &= \theta_t + \alpha \nabla_\theta \ln \pi(a_t|s_t, \theta_t) \left[ q_t(s_t, a_t) - v_t(s_t) \right] \\
&= \theta_t + \alpha \nabla_\theta \ln \pi(a_t|s_t, \theta_t) \delta_t(s_t, a_t) \tag{10.8}
\end{aligned}$$

其中，$s_t$、$a_t$ 是第 $t$ 时刻状态 $S$、动作 $A$ 的样本；$q_t(s_t, a_t)$ 和 $v_t(s_t)$ 分别是 $q_{\pi(\theta_t)}(s_t, a_t)$ 和 $v_{\pi(\theta_t)}(s_t)$ 的估计值。

式（10.8）所示算法的核心特点是：策略更新基于 $q_t$ 相对于 $v_t$ 的相对价值，而非 $q_t$ 的绝对价值。这一设计在直觉上是合理的 —— 当我们在某一状态下选择动作时，真正关心的是 "哪个动作的价值相对更高"，而非动作价值的绝对大小。

若通过蒙特卡洛学习估计 $q_t(s_t, a_t)$ 和 $v_t(s_t)$，则式（10.8）对应的算法被称为 "带基线的 REINFORCE 算法（REINFORCE with a baseline）"；若通过时序差分（TD）学习估计这两个值，则该算法通常被称为优势演员 - 评论家（Advantage Actor-Critic，A2C）。

A2C 的实现流程总结于算法 10.2 中。需要注意的是，该实现中用时序差分误差（TD 误差）近似优势函数，即：

$$q_t(s_t, a_t) - v_t(s_t) \approx r_{t+1} + \gamma v_t(s_{t+1}) - v_t(s_t)$$

这一近似的合理性可通过以下推导验证：根据 $q_\pi(s_t, a_t)$ 的定义，有

$$q_\pi(s_t, a_t) - v_\pi(s_t) = \mathbb{E}\left[ R_{t+1} + \gamma v_\pi(S_{t+1}) - v_\pi(S_t) \mid S_t = s_t, A_t = a_t \right]$$

使用 TD 误差近似的一大优势是：仅需一个神经网络即可表示 $v_\pi(s)$。反之，若直接用 $\delta_t = q_t(s_t, a_t) - v_t(s_t)$ 计算优势，则需要维护两个独立的网络，分别表示 $v_\pi(s)$（状态价值）和 $q_\pi(s, a)$（动作价值）。正因如此，用 TD 误差近似的 A2C 也常被称为 "时序差分演员 - 评论家（TD Actor-Critic）"。

此外值得注意的是，策略 $\pi(\theta_t)$ 是随机策略，天然具备探索性，因此无需依赖 ε- 贪心（ε-greedy）等策略，即可直接用于生成经验样本。A2C 存在多种变体，例如异步优势演员 - 评论家（Asynchronous Advantage Actor-Critic，A3C）。

<NoteBlock title="Advantage actor-critic (A2C) or TD actor-critic">
**Initialization**: A policy function $\pi(a|s, \theta_0)$ where $\theta_0$ is the initial parameter. A value function $v(s, w_0)$ where $w_0$ is the initial parameter. $\alpha_w, \alpha_\theta > 0$.

**Goal**: Learn an optimal policy to maximize $J(\theta)$.

**At time step $t$ in each episode, do**:
1. Generate $a_t$ following $\pi(a|s_t, \theta_t)$ and then observe $r_{t+1}$, $s_{t+1}$.
2. **Advantage (TD error)**: $\delta_t = r_{t+1} + \gamma v(s_{t+1}, w_t) - v(s_t, w_t)$
3. **Actor (policy update)**: $\theta_{t+1} = \theta_t + \alpha_\theta \delta_t \nabla_\theta \ln \pi(a_t|s_t, \theta_t)$
4. **Critic (value update)**: $w_{t+1} = w_t + \alpha_w \delta_t \nabla_w v(s_t, w_t)$
</NoteBlock>
## Off-policy actor-critic
到目前为止，我们研究过的策略梯度方法（包括 **REINFORCE**、**QAC** 和 **A2C**）均为**在线（on-policy）**方法。其原因可从真实梯度的表达式中看出：

$$\nabla_{\theta} J(\theta)=\mathbb{E}_{S \sim \eta, A \sim \pi}\left[\nabla_{\theta} \ln \pi\left(A | S, \theta_{t}\right)\left(q_{\pi}(S, A)-v_{\pi}(S)\right)\right]$$

若要用样本近似这一真实梯度，必须遵循策略 $\pi(\theta)$ 来生成动作样本。因此，$\pi(\theta)$ 既是**行为策略**（生成样本的策略），也是我们希望改进的**目标策略**，故而这些策略梯度方法属于在线方法。若我们已拥有由某一给定行为策略生成的样本，仍可应用策略梯度方法来利用这些样本。要实现这一点，需引入一种名为**重要性采样（importance sampling）**的技术。值得一提的是，重要性采样并非局限于强化学习领域的技术，它是一种通用方法 —— 可利用从某一概率分布中抽取的样本，来估计另一概率分布下随机变量的期望。

### Importance sampling
考虑随机变量 $X \in \mathcal{X}$，设 $p_0(X)$ 为某一概率分布，我们的目标是估计期望 $\mathbb{E}_{X \sim p_0}[X]$。假设我们拥有一组独立同分布（i.i.d.）样本 $\{x_i\}_{i=1}^n$。

**第一种情况**：若样本 $\{x_i\}_{i=1}^n$ 是遵循分布 $p_0$ 生成的，则可使用样本均值 $\bar{x} = \frac{1}{n}\sum_{i=1}^n x_i$ 来近似 $\mathbb{E}_{X \sim p_0}[X]$。这是因为 $\bar{x}$ 是 $\mathbb{E}_{X \sim p_0}[X]$ 的无偏估计，且当 $n \to \infty$ 时，估计方差会收敛到 0。

**第二种情况**：考虑另一种场景 —— 样本 $\{x_i\}_{i=1}^n$ 并非由 $p_0$ 生成，而是由另一分布 $p_1$ 生成。此时我们仍能利用这些样本来近似 $\mathbb{E}_{X \sim p_0}[X]$ 吗？答案是肯定的。但此时不能再用 $\bar{x} = \frac{1}{n}\sum_{i=1}^n x_i$ 进行近似，因为 $\bar{x}$ 近似的是 $\mathbb{E}_{X \sim p_1}[X]$，而非 $\mathbb{E}_{X \sim p_0}[X]$。在第二种场景下，可基于重要性采样技术近似 $\mathbb{E}_{X \sim p_0}[X]$。具体而言，$\mathbb{E}_{X \sim p_0}[X]$ 满足以下等式：

$$\mathbb{E}_{X \sim p_0}[X] = \sum_{x \in \mathcal{X}} p_0(x)x = \sum_{x \in \mathcal{X}} p_1(x) \underbrace{\frac{p_0(x)}{p_1(x)}x}_{f(x)} = \mathbb{E}_{X \sim p_1}[f(X)] \tag{10.9}$$

由此，估计 $\mathbb{E}_{X \sim p_0}[X]$ 的问题转化为估计 $\mathbb{E}_{X \sim p_1}[f(X)]$ 的问题。令 $\bar{f} \doteq \frac{1}{n}\sum_{i=1}^n f(x_i)$。由于 $\bar{f}$ 可有效近似 $\mathbb{E}_{X \sim p_1}[f(X)]$，结合式（10.9）可得：

$$\mathbb{E}_{X \sim p_0}[X] = \mathbb{E}_{X \sim p_1}[f(X)] \approx \bar{f} = \frac{1}{n}\sum_{i=1}^n f(x_i) = \frac{1}{n}\sum_{i=1}^n \underbrace{\frac{p_0(x_i)}{p_1(x_i)}}_{\text{重要性权重（importance weight）}} x_i \tag{10.10}$$

式（10.10）表明，$\mathbb{E}_{X \sim p_0}[X]$ 可通过样本 $x_i$ 的加权平均来近似，其中 $\frac{p_0(x_i)}{p_1(x_i)}$ 被称为**重要性权重**。具体特性如下：当 $p_1 = p_0$ 时，重要性权重为 1，此时 $\bar{f}$ 退化为样本均值 $\bar{x}$；当 $p_0(x_i) \geq p_1(x_i)$ 时，样本 $x_i$ 在分布 $p_0$ 中被采样到的概率更高，而在 $p_1$ 中被采样到的概率更低。此时重要性权重大于 1，可 "放大" 该样本的重要性。

可能有读者会问：既然式（10.10）中仍需用到 $p_0(x)$，为何不直接利用期望的定义 $\mathbb{E}_{X \sim p_0}[X] = \sum_{x \in \mathcal{X}} p_0(x)x$ 来计算呢？答案如下：要直接使用定义计算，需满足以下任一条件 —— 要么知道 $p_0$ 的解析表达式，要么获取所有 $x \in \mathcal{X}$ 对应的 $p_0(x)$ 值。但在实际场景中，这两个条件往往难以满足：例如，若分布通过神经网络等方式表示，我们难以获取 $p_0$ 的解析表达式；而当 $\mathcal{X}$ 的规模较大时，也难以获取所有 $x \in \mathcal{X}$ 对应的 $p_0(x)$ 值。相比之下，式（10.10）仅需获取部分样本 $x_i$ 对应的 $p_0(x_i)$ 值，在实际中更易于实现。

接下来，我们通过一个示例来演示重要性采样技术。考虑随机变量 $X \in \mathcal{X}$，其中 $\mathcal{X}$ 定义为 $\{+1, -1\}$。假设分布 $p_0$ 是满足以下条件的概率分布：

$$p_0(X = +1) = 0.5,\quad p_0(X = -1) = 0.5$$

则 $X$ 在分布 $p_0$ 下的期望为：

$$\mathbb{E}_{X \sim p_0}[X] = (+1) \times 0.5 + (-1) \times 0.5 = 0$$

假设分布 $p_1$ 是另一个满足以下条件的概率分布：

$$p_1(X = +1) = 0.8,\quad p_1(X = -1) = 0.2$$

则 $X$ 在分布 $p_1$ 下的期望为：

$$\mathbb{E}_{X \sim p_1}[X] = (+1) \times 0.8 + (-1) \times 0.2 = 0.6$$

假设我们拥有一组从分布 $p_1$ 中抽取的样本 $\{x_i\}$，目标是利用这些样本来估计 $\mathbb{E}_{X \sim p_0}[X]$。如图 10.2 所示，样本中取值为 $+1$ 的数量多于取值为 $-1$ 的数量，这是因为 $p_1(X = +1) = 0.8 > p_1(X = -1) = 0.2$。若直接计算样本的均值 $\sum_{i=1}^n x_i / n$，该均值会收敛到 $\mathbb{E}_{X \sim p_1}[X] = 0.6$（见图 10.2 中的虚线）；与之相反，若按照式（10.10）计算加权均值，该均值则能成功收敛到 $\mathbb{E}_{X \sim p_0}[X] = 0$（见图 10.2 中的实线）。
![An example for demonstrating the importance sampling technique](/img/rl/f10-1.png)

图中 $X \in \{+1, -1\}$，且 $p_0(X = +1) = p_0(X = -1) = 0.5$。样本根据分布 $p_1$ 生成，其中 $p_1(X = +1) = 0.8$、$p_1(X = -1) = 0.2$。样本的均值收敛到 $\mathbb{E}_{X \sim p_1}[X] = 0.6$，而通过式（10.10）中重要性采样技术计算的加权均值收敛到 $\mathbb{E}_{X \sim p_0}[X] = 0$。

最后，用于生成样本的分布 $p_1$ 必须满足：当 $p_0(x) \neq 0$ 时，$p_1(x) \neq 0$。若出现 "$p_0(x) \neq 0$ 但 $p_1(x) = 0$" 的情况，估计结果可能会出现问题。例如，若：

$$p_1(X = +1) = 1,\quad p_1(X = -1) = 0$$

则从 $p_1$ 中生成的样本全为正值，即 $\{x_i\} = \{+1, +1, \dots, +1\}$。这些样本无法用于正确估计 $\mathbb{E}_{X \sim p_0}[X] = 0$，因为无论样本数量 $n$ 多大，都有：

$$\frac{1}{n}\sum_{i=1}^n \frac{p_0(x_i)}{p_1(x_i)} x_i = \frac{1}{n}\sum_{i=1}^n \frac{p_0(+1)}{p_1(+1)} \times 1 = \frac{1}{n}\sum_{i=1}^n \frac{0.5}{1} \times 1 \equiv 0.5$$
### The off-policy policy gradient theorem
借助重要性采样技术，我们现在可以给出离线策略梯度定理。假设 $\beta$ 为**行为策略（behavior policy）**，我们的目标是利用 $\beta$ 生成的样本学习一个**目标策略（target policy）** $\pi$，以最大化下述指标：

$$J(\theta) = \sum_{s \in \mathcal{S}} d_{\beta}(s) v_{\pi}(s) = \mathbb{E}_{S \sim d_{\beta}} \left[ v_{\pi}(S) \right]$$

其中，$d_{\beta}$ 是策略 $\beta$ 下的状态平稳分布（stationary distribution），$v_{\pi}$ 是策略 $\pi$ 下的状态价值（state value）。该指标的梯度由下述定理给出。


<NoteBlock title="Advantage actor-critic (A2C) or TD actor-critic">
**Initialization**: A policy function $\pi(a|s, \theta_0)$ where $\theta_0$ is the initial parameter. A value function $v(s, w_0)$ where $w_0$ is the initial parameter. $\alpha_w, \alpha_\theta > 0$.

**Goal**: Learn an optimal policy to maximize $J(\theta)$.

**At time step $t$ in each episode, do**:
1. Generate $a_t$ following $\pi(a|s_t, \theta_t)$ and then observe $r_{t+1}$, $s_{t+1}$.
2. **Advantage (TD error)**: $\delta_t = r_{t+1} + \gamma v(s_{t+1}, w_t) - v(s_t, w_t)$
3. **Actor (policy update)**: $\theta_{t+1} = \theta_t + \alpha_\theta \delta_t \nabla_\theta \ln \pi(a_t|s_t, \theta_t)$
4. **Critic (value update)**: $w_{t+1} = w_t + \alpha_w \delta_t \nabla_w v(s_t, w_t)$
</NoteBlock>
## Off-policy actor-critic
到目前为止，我们研究过的策略梯度方法（包括 **REINFORCE**、**QAC** 和 **A2C**）均为**在线（on-policy）**方法。其原因可从真实梯度的表达式中看出：

$$\nabla_{\theta} J(\theta)=\mathbb{E}_{S \sim \eta, A \sim \pi}\left[\nabla_{\theta} \ln \pi\left(A | S, \theta_{t}\right)\left(q_{\pi}(S, A)-v_{\pi}(S)\right)\right]$$

若要用样本近似这一真实梯度，必须遵循策略 $\pi(\theta)$ 来生成动作样本。因此，$\pi(\theta)$ 既是**行为策略**（生成样本的策略），也是我们希望改进的**目标策略**，故而这些策略梯度方法属于在线方法。若我们已拥有由某一给定行为策略生成的样本，仍可应用策略梯度方法来利用这些样本。要实现这一点，需引入一种名为**重要性采样（importance sampling）**的技术。值得一提的是，重要性采样并非局限于强化学习领域的技术，它是一种通用方法 —— 可利用从某一概率分布中抽取的样本，来估计另一概率分布下随机变量的期望。

### Importance sampling
考虑随机变量 $X \in \mathcal{X}$，设 $p_0(X)$ 为某一概率分布，我们的目标是估计期望 $\mathbb{E}_{X \sim p_0}[X]$。假设我们拥有一组独立同分布（i.i.d.）样本 $\{x_i\}_{i=1}^n$。

**第一种情况**：若样本 $\{x_i\}_{i=1}^n$ 是遵循分布 $p_0$ 生成的，则可使用样本均值 $\bar{x} = \frac{1}{n}\sum_{i=1}^n x_i$ 来近似 $\mathbb{E}_{X \sim p_0}[X]$。这是因为 $\bar{x}$ 是 $\mathbb{E}_{X \sim p_0}[X]$ 的无偏估计，且当 $n \to \infty$ 时，估计方差会收敛到 0。

**第二种情况**：考虑另一种场景 —— 样本 $\{x_i\}_{i=1}^n$ 并非由 $p_0$ 生成，而是由另一分布 $p_1$ 生成。此时我们仍能利用这些样本来近似 $\mathbb{E}_{X \sim p_0}[X]$ 吗？答案是肯定的。但此时不能再用 $\bar{x} = \frac{1}{n}\sum_{i=1}^n x_i$ 进行近似，因为 $\bar{x}$ 近似的是 $\mathbb{E}_{X \sim p_1}[X]$，而非 $\mathbb{E}_{X \sim p_0}[X]$。在第二种场景下，可基于重要性采样技术近似 $\mathbb{E}_{X \sim p_0}[X]$。具体而言，$\mathbb{E}_{X \sim p_0}[X]$ 满足以下等式：

$$\mathbb{E}_{X \sim p_0}[X] = \sum_{x \in \mathcal{X}} p_0(x)x = \sum_{x \in \mathcal{X}} p_1(x) \underbrace{\frac{p_0(x)}{p_1(x)}x}_{f(x)} = \mathbb{E}_{X \sim p_1}[f(X)] \tag{10.9}$$

由此，估计 $\mathbb{E}_{X \sim p_0}[X]$ 的问题转化为估计 $\mathbb{E}_{X \sim p_1}[f(X)]$ 的问题。令 $\bar{f} \doteq \frac{1}{n}\sum_{i=1}^n f(x_i)$。由于 $\bar{f}$ 可有效近似 $\mathbb{E}_{X \sim p_1}[f(X)]$，结合式（10.9）可得：

$$\mathbb{E}_{X \sim p_0}[X] = \mathbb{E}_{X \sim p_1}[f(X)] \approx \bar{f} = \frac{1}{n}\sum_{i=1}^n f(x_i) = \frac{1}{n}\sum_{i=1}^n \underbrace{\frac{p_0(x_i)}{p_1(x_i)}}_{\text{重要性权重（importance weight）}} x_i \tag{10.10}$$

式（10.10）表明，$\mathbb{E}_{X \sim p_0}[X]$ 可通过样本 $x_i$ 的加权平均来近似，其中 $\frac{p_0(x_i)}{p_1(x_i)}$ 被称为**重要性权重**。具体特性如下：当 $p_1 = p_0$ 时，重要性权重为 1，此时 $\bar{f}$ 退化为样本均值 $\bar{x}$；当 $p_0(x_i) \geq p_1(x_i)$ 时，样本 $x_i$ 在分布 $p_0$ 中被采样到的概率更高，而在 $p_1$ 中被采样到的概率更低。此时重要性权重大于 1，可 "放大" 该样本的重要性。

可能有读者会问：既然式（10.10）中仍需用到 $p_0(x)$，为何不直接利用期望的定义 $\mathbb{E}_{X \sim p_0}[X] = \sum_{x \in \mathcal{X}} p_0(x)x$ 来计算呢？答案如下：要直接使用定义计算，需满足以下任一条件 —— 要么知道 $p_0$ 的解析表达式，要么获取所有 $x \in \mathcal{X}$ 对应的 $p_0(x)$ 值。但在实际场景中，这两个条件往往难以满足：例如，若分布通过神经网络等方式表示，我们难以获取 $p_0$ 的解析表达式；而当 $\mathcal{X}$ 的规模较大时，也难以获取所有 $x \in \mathcal{X}$ 对应的 $p_0(x)$ 值。相比之下，式（10.10）仅需获取部分样本 $x_i$ 对应的 $p_0(x_i)$ 值，在实际中更易于实现。

接下来，我们通过一个示例来演示重要性采样技术。考虑随机变量 $X \in \mathcal{X}$，其中 $\mathcal{X}$ 定义为 $\{+1, -1\}$。假设分布 $p_0$ 是满足以下条件的概率分布：

$$p_0(X = +1) = 0.5,\quad p_0(X = -1) = 0.5$$

则 $X$ 在分布 $p_0$ 下的期望为：

$$\mathbb{E}_{X \sim p_0}[X] = (+1) \times 0.5 + (-1) \times 0.5 = 0$$

假设分布 $p_1$ 是另一个满足以下条件的概率分布：

$$p_1(X = +1) = 0.8,\quad p_1(X = -1) = 0.2$$

则 $X$ 在分布 $p_1$ 下的期望为：

$$\mathbb{E}_{X \sim p_1}[X] = (+1) \times 0.8 + (-1) \times 0.2 = 0.6$$

假设我们拥有一组从分布 $p_1$ 中抽取的样本 $\{x_i\}$，目标是利用这些样本来估计 $\mathbb{E}_{X \sim p_0}[X]$。如图 10.2 所示，样本中取值为 $+1$ 的数量多于取值为 $-1$ 的数量，这是因为 $p_1(X = +1) = 0.8 > p_1(X = -1) = 0.2$。若直接计算样本的均值 $\sum_{i=1}^n x_i / n$，该均值会收敛到 $\mathbb{E}_{X \sim p_1}[X] = 0.6$（见图 10.2 中的虚线）；与之相反，若按照式（10.10）计算加权均值，该均值则能成功收敛到 $\mathbb{E}_{X \sim p_0}[X] = 0$（见图 10.2 中的实线）。
![An example for demonstrating the importance sampling technique](/img/rl/f10-1.png)

图中 $X \in \{+1, -1\}$，且 $p_0(X = +1) = p_0(X = -1) = 0.5$。样本根据分布 $p_1$ 生成，其中 $p_1(X = +1) = 0.8$、$p_1(X = -1) = 0.2$。样本的均值收敛到 $\mathbb{E}_{X \sim p_1}[X] = 0.6$，而通过式（10.10）中重要性采样技术计算的加权均值收敛到 $\mathbb{E}_{X \sim p_0}[X] = 0$。

最后，用于生成样本的分布 $p_1$ 必须满足：当 $p_0(x) \neq 0$ 时，$p_1(x) \neq 0$。若出现 "$p_0(x) \neq 0$ 但 $p_1(x) = 0$" 的情况，估计结果可能会出现问题。例如，若：

$$p_1(X = +1) = 1,\quad p_1(X = -1) = 0$$

则从 $p_1$ 中生成的样本全为正值，即 $\{x_i\} = \{+1, +1, \dots, +1\}$。这些样本无法用于正确估计 $\mathbb{E}_{X \sim p_0}[X] = 0$，因为无论样本数量 $n$ 多大，都有：

$$\frac{1}{n}\sum_{i=1}^n \frac{p_0(x_i)}{p_1(x_i)} x_i = \frac{1}{n}\sum_{i=1}^n \frac{p_0(+1)}{p_1(+1)} \times 1 = \frac{1}{n}\sum_{i=1}^n \frac{0.5}{1} \times 1 \equiv 0.5$$
### The off-policy policy gradient theorem
借助重要性采样技术，我们现在可以给出离线策略梯度定理。假设 $\beta$ 为**行为策略（behavior policy）**，我们的目标是利用 $\beta$ 生成的样本学习一个**目标策略（target policy）** $\pi$，以最大化下述指标：

$$J(\theta) = \sum_{s \in \mathcal{S}} d_{\beta}(s) v_{\pi}(s) = \mathbb{E}_{S \sim d_{\beta}} \left[ v_{\pi}(S) \right]$$

其中，$d_{\beta}$ 是策略 $\beta$ 下的状态平稳分布（stationary distribution），$v_{\pi}$ 是策略 $\pi$ 下的状态价值（state value）。该指标的梯度由下述定理给出。

**定理 10.1（离线策略梯度定理）**：在折扣因子 $\gamma \in (0, 1)$ 的折扣情况下，$J(\theta)$ 的梯度为：

$$\nabla_{\theta} J(\theta) = \mathbb{E}_{S \sim \rho, A \sim \beta} \left[ \underbrace{\frac{\pi(A|S, \theta)}{\beta(A|S)}}_{\text{重要性权重（importance weight）}} \nabla_{\theta} \ln \pi(A|S, \theta) q_{\pi}(S, A) \right] \tag{10.11}$$

其中，状态分布 $\rho$ 的定义为：

$$\rho(s) \doteq \sum_{s' \in \mathcal{S}} d_{\beta}(s') \text{Pr}_{\pi}(s|s'), \quad s \in \mathcal{S}$$

而 $\text{Pr}_{\pi}(s|s') = \sum_{k=0}^{\infty} \gamma^k \left[ P_{\pi}^k \right]_{s's} = \left[ (I - \gamma P_{\pi})^{-1} \right]_{s's}$，表示在策略 $\pi$ 下，从状态 $s'$ 转移到状态 $s$ 的折扣总概率（discounted total probability）（注：$\left[ P_{\pi}^k \right]_{s's}$ 表示矩阵 $P_{\pi}^k$ 中第 $s'$ 行、第 $s$ 列的元素，$I$ 为单位矩阵）。

式（10.11）中的梯度与第 9 章定理 9.1 中在线情况的梯度类似，但存在两处关键差异：
1. 新增了重要性权重（即 $\frac{\pi(A|S, \theta)}{\beta(A|S)}$）；
2. 动作 $A$ 服从行为策略 $\beta$ 的分布（$A \sim \beta$），而非在线情况中服从目标策略 $\pi$ 的分布（$A \sim \pi$）。

因此，我们可以利用遵循行为策略 $\beta$ 生成的动作样本来近似真实梯度。
### Algorithm description
基于离线策略梯度定理，我们现在可以介绍**离线演员-评论家算法**。由于离线情况与在线情况非常相似，因此我们仅介绍部分关键步骤。

首先，离线策略梯度对任意额外基线 $b(s)$ 具有不变性。具体而言，我们有：

$$\nabla_{\theta} J(\theta) = \mathbb{E}_{S \sim \rho, A \sim \beta}\left[ \frac{\pi(A|S, \theta)}{\beta(A|S)} \nabla_{\theta} \ln \pi(A|S, \theta) \left( q_{\pi}(S, A) - b(S) \right) \right]$$

这是因为 $\mathbb{E}\left[ \frac{\pi(A|S, \theta)}{\beta(A|S)} \nabla_{\theta} \ln \pi(A|S, \theta) b(S) \right] = 0$。

为降低估计方差，我们可选择状态价值 $b(S) = v_{\pi}(S)$ 作为基线，此时梯度可表示为：

$$\nabla_{\theta} J(\theta) = \mathbb{E}\left[ \frac{\pi(A|S, \theta)}{\beta(A|S)} \nabla_{\theta} \ln \pi(A|S, \theta) \left( q_{\pi}(S, A) - v_{\pi}(S) \right) \right]$$

对应的随机梯度上升算法为：

$$\theta_{t+1} = \theta_t + \alpha_{\theta} \cdot \frac{\pi(a_t|s_t, \theta_t)}{\beta(a_t|s_t)} \cdot \nabla_{\theta} \ln \pi(a_t|s_t, \theta_t) \cdot \left( q_t(s_t, a_t) - v_t(s_t) \right)$$

其中 $\alpha_{\theta} > 0$（策略更新学习率）。

与在线情况类似，优势函数 $q_t(s, a) - v_t(s)$ 可替换为时序差分误差（TD 误差），即：

$$q_t(s_t, a_t) - v_t(s_t) \approx r_{t+1} + \gamma v_t(s_{t+1}) - v_t(s_t) \doteq \delta_t(s_t, a_t)$$

此时，算法可简化为：

$$\theta_{t+1} = \theta_t + \alpha_{\theta} \cdot \frac{\pi(a_t|s_t, \theta_t)}{\beta(a_t|s_t)} \cdot \nabla_{\theta} \ln \pi(a_t|s_t, \theta_t) \cdot \delta_t(s_t, a_t)$$

离线演员-评论家算法的实现流程总结于算法 10.3。可以看出，该算法与优势演员-评论家（A2C）算法的结构完全一致，唯一区别在于：演员（策略更新）和评论家（价值更新）的步骤中均额外引入了重要性权重。需特别注意的是，除演员外，评论家也通过重要性采样技术从 "在线" 转换为 "离线"。事实上，重要性采样是一种通用技术，既可应用于基于策略（policy-based）的算法，也可应用于基于价值（value-based）的算法。最后，算法 10.3 可通过多种方式扩展，以融入资格迹（eligibility traces）等更多技术。

<NoteBlock title="Algorithm 10.3: Off-policy actor-critic based on importance sampling">

**Initialization**: A given behavior policy $\beta(a|s)$. A target policy $\pi(a|s, \theta_0)$ where $\theta_0$ is the initial parameter. A value function $v(s, w_0)$ where $w_0$ is the initial parameter. $\alpha_w, \alpha_{\theta} > 0$.

**Goal**: Learn an optimal policy to maximize $J(\theta)$.

**At time step $t$ in each episode**, do:

1. Generate $a_t$ following $\beta(s_t)$ and then observe $r_{t+1}, s_{t+1}$.
2. **Advantage (TD error)**:
   $$
   \delta_t = r_{t+1} + \gamma v(s_{t+1}, w_t) - v(s_t, w_t)
   $$
3. **Actor (policy update)**: $\theta_{t+1} = \theta_t + \alpha_{\theta} \frac{\pi(a_t|s_t, \theta_t)}{\beta(a_t|s_t)} \delta_t \nabla_{\theta} \ln \pi(a_t|s_t, \theta_t)$
4. **Critic (value update)**: $w_{t+1} = w_t + \alpha_w \frac{\pi(a_t|s_t, \theta_t)}{\beta(a_t|s_t)} \delta_t \nabla_w v(s_t, w_t)$

</NoteBlock>

## Deterministic actor-critic
到目前为止，策略梯度方法中所使用的策略均为**随机策略** —— 这是因为其要求对所有（状态-动作）对 $(s, a)$，都满足 $\pi(a|s, \theta) > 0$。本节将说明，**确定性策略**同样可应用于策略梯度方法。此处的 "确定性" 指：对于任意状态，仅单个动作被赋予 1 的概率，而所有其他动作的概率均为 0。研究确定性策略具有重要意义，因为它天然具备**离线（off-policy）**属性，且能有效处理连续动作空间。

此前，我们一直用 $\pi(a|s, \theta)$ 表示通用策略（既可为随机策略，也可为确定性策略）。在本节中，我们将用 $a = \mu(s, \theta)$ 专门表示确定性策略。与 $\pi$（给出动作概率）不同，$\mu$ 是从状态空间 $\mathcal{S}$ 到动作空间 $\mathcal{A}$ 的映射，因此会直接输出动作。例如，这种确定性策略可通过神经网络实现：以状态 $s$ 为输入，动作 $a$ 为输出，$\theta$ 为网络参数。为简化表述，我们常将 $\mu(s, \theta)$ 简记为 $\mu(s)$。

### The deterministic policy gradient theorem

上一章介绍的策略梯度定理仅适用于随机策略。当我们要求策略为确定性策略时，需推导新的策略梯度定理。

**定理 10.2（确定性策略梯度定理）**：目标函数 $J(\theta)$ 的梯度为：

$$\begin{aligned}
\nabla_{\theta} J(\theta) &= \sum_{s \in \mathcal{S}} \eta(s) \nabla_{\theta} \mu(s) \cdot \left. (\nabla_{a} q_{\mu}(s, a)) \right|_{a=\mu(s)} \\
&= \mathbb{E}_{S \sim \eta} \left[ \nabla_{\theta} \mu(S) \cdot \left. (\nabla_{a} q_{\mu}(S, a)) \right|_{a=\mu(S)} \right] \tag{10.14}
\end{aligned}$$

其中，$\eta$ 为状态分布。定理 10.2 是对定理 10.3 与定理 10.4 所呈现结果的总结 —— 这两个定理中梯度的表达式结构相似。目标函数 $J(\theta)$ 与状态分布 $\eta$ 的具体表达式可参考定理 10.3 和定理 10.4。

与随机策略的情况不同，式（10.14）所示的确定性策略梯度中不包含动作随机变量 $A$。因此，当我们用样本近似真实梯度时，无需对动作进行采样。这也使得确定性策略梯度方法天然属于**离线（off-policy）**方法。

此外，部分读者可能会疑惑：为何不能将 $\left. (\nabla_{a} q_{\mu}(S, a)) \right|_{a=\mu(S)}$ 写成看似更简洁的 $\nabla_{a} q_{\mu}(S, \mu(S))$？原因很简单：若采用后一种写法，将无法明确 $q_{\mu}(S, \mu(S))$ 如何作为动作 $a$ 的函数（进而无法对 $a$ 求梯度）。一种更简洁且不易产生混淆的表述可写为 $\nabla_{a} q_{\mu}(S, a = \mu(S))$。

在本小节的剩余部分，我们将详细推导定理 10.2。具体而言，我们会针对两种常用指标推导梯度：第一种是**平均价值（average value）**，第二种是**平均奖励（average reward）**。由于这两种指标已在 9.2 节中详细讨论，因此有时会直接使用其性质而不再赘述其证明过程。
> 对多数读者而言，只需掌握定理 10.2 的内容即可，无需深入了解推导细节
#### Metric 1: Average value
我们首先推导平均价值的梯度：

$$J(\theta) = \mathbb{E}\left[ v_{\mu}(s) \right] = \sum_{s \in \mathcal{S}} d_0(s) v_{\mu}(s) \tag{10.15}$$

其中，$d_0$ 是状态的概率分布。此处为简化分析，选择 $d_0$ 与（确定性策略）$\mu$ 相互独立。选择 $d_0$ 存在两种特殊且重要的情况：

1. **第一种情况**：$d_0(s_0) = 1$ 且 $d_0(s \neq s_0) = 0$（其中 $s_0$ 是某个特定的目标状态）。在此情况下，策略的目标是最大化从 $s_0$ 出发所能获得的折扣回报。
2. **第二种情况**：$d_0$ 是某一给定行为策略（与目标策略 $\mu$ 不同）的分布。

要计算 $J(\theta)$ 的梯度，需先计算任意状态 $s \in \mathcal{S}$ 下 $v_{\mu}(s)$（策略 $\mu$ 的状态价值）的梯度。我们考虑折扣因子 $\gamma \in (0,1)$ 的折扣情况。

**引理 10.1（$v_{\mu}(s)$ 的梯度）**：在折扣情况下，对任意 $s \in \mathcal{S}$，以下等式成立：

$$\nabla_{\theta} v_{\mu}(s) = \sum_{s' \in \mathcal{S}} \text{Pr}_{\mu}(s'|s) \cdot \nabla_{\theta} \mu(s') \cdot \left. (\nabla_{a} q_{\mu}(s', a)) \right|_{a=\mu(s')} \tag{10.16}$$

其中，$\text{Pr}_{\mu}(s'|s) \doteq \sum_{k=0}^{\infty} \gamma^k \left[ P_{\mu}^k \right]_{ss'} = \left[ (I - \gamma P_{\mu})^{-1} \right]_{ss'}$ 表示在策略 $\mu$ 下，从状态 $s$ 转移到状态 $s'$ 的折扣总概率。此处 $[\cdot]_{ss'}$ 表示矩阵中第 $s$ 行、第 $s'$ 列的元素。

有了引理 10.1 的铺垫，我们现在可以推导 $J(\theta)$ 的梯度。

**定理 10.3（折扣情况下的确定性策略梯度定理）**：在折扣因子 $\gamma \in (0, 1)$ 的折扣情况下，式（10.15）中 $J(\theta)$ 的梯度为：

$$\begin{aligned}
\nabla_{\theta} J(\theta) &= \sum_{s \in \mathcal{S}} \rho_{\mu}(s) \nabla_{\theta} \mu(s) \cdot \left. (\nabla_{a} q_{\mu}(s, a)) \right|_{a=\mu(s)} \\
&= \mathbb{E}_{S \sim \rho_{\mu}} \left[ \nabla_{\theta} \mu(S) \cdot \left. (\nabla_{a} q_{\mu}(S, a)) \right|_{a=\mu(S)} \right]
\end{aligned}$$

其中，状态分布 $\rho_{\mu}$ 的定义为：

$$\rho_{\mu}(s) = \sum_{s' \in \mathcal{S}} d_0(s') \text{Pr}_{\mu}(s|s'), \quad s \in \mathcal{S}$$

此处，$\text{Pr}_{\mu}(s|s') = \sum_{k=0}^{\infty} \gamma^k \left[ P_{\mu}^k \right]_{s's} = \left[ (I - \gamma P_{\mu})^{-1} \right]_{s's}$，表示在策略 $\mu$ 下从状态 $s'$ 转移到状态 $s$ 的折扣总概率。（注：$\left[ P_{\mu}^k \right]_{s's}$ 表示矩阵 $P_{\mu}$ 的 $k$ 次幂中第 $s'$ 行、第 $s$ 列的元素；$I$ 为单位矩阵，$P_{\mu}$ 为策略 $\mu$ 对应的状态转移矩阵。）
#### Metric 2: Average reward
接下来，我们推导平均奖励的梯度：

$$\begin{aligned}
J(\theta) &= \bar{r}_\mu = \sum_{s \in \mathcal{S}} d_\mu(s) r_\mu(s) \\
&= \mathbb{E}_{S \sim d_\mu} \left[ r_\mu(S) \right] \tag{10.20}
\end{aligned}$$

其中，$r_\mu(s) = \mathbb{E}\left[ R \mid s, a = \mu(s) \right] = \sum_{r} r p\left(r \mid s, a = \mu(s)\right)$ 表示即时奖励的期望。关于该指标的更多信息可参考第 9.2 节。$J(\theta)$ 的梯度由下述定理给出。

**定理 10.4（无折扣情况下的确定性策略梯度定理）**：在无折扣情况下，式（10.20）中 $J(\theta)$ 的梯度为：

$$\begin{aligned}
\nabla_{\theta} J(\theta) &= \sum_{s \in \mathcal{S}} d_\mu(s) \nabla_{\theta} \mu(s) \cdot \left. (\nabla_{a} q_\mu(s, a)) \right|_{a=\mu(s)} \\
&= \mathbb{E}_{S \sim d_\mu} \left[ \nabla_{\theta} \mu(S) \cdot \left. (\nabla_{a} q_\mu(S, a)) \right|_{a=\mu(S)} \right]
\end{aligned}$$

其中，$d_\mu$ 是策略 $\mu$ 下的状态平稳分布。
### Algorithm description
基于定理 10.2 给出的梯度，我们可采用梯度上升算法来最大化目标函数 $J(\theta)$，具体形式如下：

$$\theta_{t+1} = \theta_t + \alpha_{\theta} \mathbb{E}_{S \sim \eta} \left[ \nabla_{\theta} \mu(S) \cdot \left. (\nabla_{a} q_{\mu}(S, a)) \right|_{a=\mu(S)} \right]$$

对应的随机梯度上升算法为：

$$\theta_{t+1} = \theta_t + \alpha_{\theta} \nabla_{\theta} \mu(s_t) \cdot \left. (\nabla_{a} q_{\mu}(s_t, a)) \right|_{a=\mu(s_t)}$$

该算法的实现流程总结于算法 10.4。需要注意的是，由于行为策略 $\beta$ 可能与目标策略 $\mu$ 不同，因此该算法属于**离线（off-policy）**算法，具体原因如下：

1. **演员（Actor）是离线的**：这一点在介绍定理 10.2 时已说明，核心在于确定性策略梯度无需动作采样，可利用任意策略生成的样本。

2. **评论家（Critic）也是离线的**：需特别注意 "为何评论家是离线的，却无需使用重要性采样技术"。具体而言，评论家所需的经验样本为 $(s_t, a_t, r_{t+1}, s_{t+1}, \tilde{a}_{t+1})$，其中 $\tilde{a}_{t+1} = \mu(s_{t+1})$。该经验样本的生成涉及两个策略：
   - **第一个策略**：在状态 $s_t$ 生成动作 $a_t$ 的策略，由于 $a_t$ 用于与环境交互，因此该策略是行为策略 $\beta$；
   - **第二个策略**：在状态 $s_{t+1}$ 生成动作 $\tilde{a}_{t+1}$ 的策略，由于评论家的目标是评估策略 $\mu$，因此该策略必须是目标策略 $\mu$。

需注意，$\tilde{a}_{t+1}$ 不会用于下一步与环境的交互，因此目标策略 $\mu$ 并非行为策略。综上，评论家属于离线模式。

**如何选择价值函数 $q(s, a, w)$？** 提出确定性策略梯度方法的原始研究 [74] 采用了线性函数来表示 $q(s, a, w)$，具体形式为：

$$q(s, a, w) = \phi^T(s, a)w$$

其中 $\phi(s, a)$ 是特征向量。目前，更主流的做法是采用神经网络来表示 $q(s, a, w)$，例如**深度确定性策略梯度（Deep Deterministic Policy Gradient，DDPG）**。

<NoteBlock title="Algorithm 10.4: Deterministic policy gradient or deterministic actor-critic">

**Initialization**: A given behavior policy $\beta(a|s)$. A deterministic target policy $\mu(s, \theta_0)$ where $\theta_0$ is the initial parameter. A value function $q(s, a, w_0)$ where $w_0$ is the initial parameter. $\alpha_w, \alpha_{\theta} > 0$.

**Goal**: Learn an optimal policy to maximize $J(\theta)$.

**At time step $t$ in each episode**, do:

1. Generate $a_t$ following $\beta$ and then observe $r_{t+1}, s_{t+1}$.
2. **TD error**:
   $$
   \delta_t = r_{t+1} + \gamma q(s_{t+1}, \mu(s_{t+1}, \theta_t), w_t) - q(s_t, a_t, w_t)
   $$
3. **Actor (policy update)**: $\theta_{t+1} = \theta_t + \alpha_{\theta}\nabla_{\theta}\mu(s_t, \theta_t)\left(\nabla_a q(s_t, a, w_t)\right)|_{a=\mu(s_t)}$
4. **Critic (value update)**:
   $$
   w_{t+1} = w_t + \alpha_w\delta_t\nabla_w q(s_t, a_t, w_t)
   $$

</NoteBlock>


## Summary
本章介绍了**演员-评论家（Actor-Critic）**方法，核心内容总结如下：

- **10.1 节**：介绍了最简单的演员-评论家算法 —— **QAC（Q 演员-评论家）**。该算法与上一章介绍的策略梯度算法 **REINFORCE** 结构相似，唯一区别在于：QAC 通过时序差分（TD）学习估计动作价值 $q$，而 REINFORCE 通过蒙特卡洛（Monte Carlo）方法估计。

- **10.2 节**：将 QAC 扩展为**优势演员-评论家（A2C）**算法。本节证明了 "策略梯度对任意额外基线具有不变性"，并指出 "最优基线可帮助降低梯度估计的方差"。

- **10.3 节**：通过引入 "**重要性采样**" 这一关键技术，将优势演员-评论家算法进一步扩展到**离线（off-policy）**场景，实现了对非目标策略（行为策略）生成样本的利用。

- **10.4 节**：此前介绍的策略梯度算法均依赖随机策略，而本节证明 "策略可强制设为确定性"，并推导了确定性策略的梯度，最终引入了**确定性策略梯度（即确定性演员-评论家）**算法。

策略梯度方法与演员-评论家方法在现代强化学习中应用广泛，文献中存在大量基于这些方法的进阶算法，例如**软演员-评论家（SAC）**、**信任域策略优化（TRPO）**、**近端策略优化（PPO）**、**双延迟深度确定性策略梯度（TD3）**等。

此外，单智能体强化学习的框架还可扩展到**多智能体强化学习**场景；经验样本也可用于拟合系统模型，从而实现**模型基强化学习**；**分布型强化学习**则为强化学习提供了与传统框架截然不同的研究视角；强化学习与控制理论的关联也已在相关文献中展开讨论。本门课程无法涵盖所有这些主题，希望书中奠定的基础能帮助读者在未来更深入地学习这些内容。