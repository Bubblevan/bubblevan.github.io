---
id: rl-chapter-9
title: 第9章 策略梯度方法
sidebar_label: 第9章
---

# Policy Gradient Methods

## Policy representation: From table to function

当策略的表示方式从表格型切换为函数型时，有必要明确这两种表示方法之间的差异：

**第一，如何定义最优策略？**

当采用表格型表示时，若某策略能最大化每个状态的价值（state value），则该策略被定义为最优策略；当采用函数型表示时，若某策略能最大化特定标量指标（scalar metric），则该策略被定义为最优策略。

**第二，如何更新策略？**

当采用表格型表示时，可通过直接修改表格中的条目来更新策略；当采用参数化函数表示时，策略无法再通过这种方式更新，而是只能通过调整参数 $\theta$ 来实现更新。

**第三，如何获取动作的概率？**

在表格型表示中，动作的概率可通过直接查询表格中对应的条目获得；在函数型表示中，需将（状态 s，动作 a）输入函数以计算该动作的概率。根据函数结构的不同，也可仅输入状态 s，进而输出所有动作的概率。

**策略梯度方法的基本思想**可总结如下：假设 $J(\theta)$ 为一个标量指标，通过基于梯度的算法对该指标进行优化，即可获得最优策略，算法公式如下：

$$
\begin{aligned}
\theta_{t+1} = \theta_t + \alpha\nabla_{\theta}J(\theta_t)
\end{aligned}
$$

其中，$\nabla_{\theta}J$ 表示指标 $J$ 对参数 $\theta$ 的梯度，$t$ 为时间步（time step），$\alpha$ 为学习率（optimization rate）。

基于这一基本思想，本章后续内容将解答以下三个问题：

1. **应采用哪些指标？**（9.2 节）
2. **如何计算指标的梯度？**（9.3 节）
3. **如何利用经验样本计算梯度？**（9.4 节）

## Metrics for defining optimal policies

若策略以函数形式表示，则存在两类用于定义最优策略的标量指标：一类基于状态值（state values），另一类基于即时奖励（immediate rewards）。

**指标 1：平均状态值（Average State Value）**

第一类指标是平均状态值，简称平均值，其定义为：

$$
\begin{aligned}
\overline{v}_{\pi} = \sum_{s \in \mathcal{S}} d(s)v_{\pi}(s)
\end{aligned}
$$

其中，$d(s)$ 表示状态 $s$ 的权重，满足对任意 $s \in \mathcal{S}$，$d(s) \geq 0$，且 $\sum_{s \in \mathcal{S}} d(s) = 1$。因此，可将 $d(s)$ 解释为状态 $s$ 的概率分布。

此时，该指标可改写为期望形式：

$$
\begin{aligned}
\overline{v}_{\pi} = \mathbb{E}_{S \sim d}\left[v_{\pi}(S)\right]
\end{aligned}
$$

**如何选择分布 $d$？**这是一个关键问题，主要分为两种情况：

**情况 1：$d$ 与策略 $\pi$ 无关**

此时，我们特意将 $d$ 记为 $d_0$，将 $\overline{v}_{\pi}$ 记为 $\overline{v}_{\pi}^0$，以表明该分布与策略无关。

- 一种场景是认为所有状态的重要性相同，此时选择 $d_0(s) = 1/|\mathcal{S}|$（其中 $|\mathcal{S}|$ 表示状态空间 $\mathcal{S}$ 中状态的总数）；
- 另一种场景是仅关注某个特定状态 $s_0$（例如，智能体始终从 $s_0$ 出发），此时可设定：

$$
\begin{aligned}
d_0(s_0) = 1,\quad d_0(s \neq s_0) = 0
\end{aligned}
$$

**情况 2：$d$ 与策略 $\pi$ 相关**

此时，通常选择 $d$ 为策略 $\pi$ 下的平稳分布（stationary distribution），记为 $d_{\pi}$。

平稳分布 $d_{\pi}$ 的一个基本性质是满足：

$$
\begin{aligned}
d_{\pi}^T P_{\pi} = d_{\pi}^T
\end{aligned}
$$

其中 $P_{\pi}$ 是策略 $\pi$ 对应的状态转移概率矩阵。关于平稳分布的更多信息，可参考 8.1 节的补充内容（Box 8.1）。

**选择 $d_{\pi}$ 的含义如下**：平稳分布反映了马尔可夫决策过程（MDP）在给定策略下的长期行为 —— 若某个状态在长期中被频繁访问，则其重要性更高，应赋予更大权重；若某个状态极少被访问，则其重要性较低，应赋予更小权重。

**平均状态值 $\overline{v}_{\pi}$ 的等价表达式**

顾名思义，$\overline{v}_{\pi}$ 是状态值的加权平均。参数 $\theta$ 的取值不同，$\overline{v}_{\pi}$ 的值也会不同。我们的最终目标是找到最优策略（或等价地，找到最优参数 $\theta$），以最大化 $\overline{v}_{\pi}$。

以下介绍 $\overline{v}_{\pi}$ 的另外两个重要等价表达式：

**等价表达式 1：基于奖励序列的期望形式**

假设智能体遵循给定策略 $\pi(\theta)$，收集到奖励序列 $\{R_{t+1}\}_{t=0}^{\infty}$。读者在文献中常能看到以下指标：

$$
\begin{aligned}
J(\theta) = \lim_{n \to \infty} \mathbb{E}\left[\sum_{t=0}^{n} \gamma^t R_{t+1}\right] = \mathbb{E}\left[\sum_{t=0}^{\infty} \gamma^t R_{t+1}\right] \tag{9.1}
\end{aligned}
$$

该指标初看之下不易理解，但实际上它与 $\overline{v}_{\pi}$ 相等。证明如下：

$$
\begin{aligned}
\mathbb{E}\left[\sum_{t=0}^{\infty} \gamma^t R_{t+1}\right] = \sum_{s \in \mathcal{S}} d(s)\mathbb{E}\left[\sum_{t=0}^{\infty} \gamma^t R_{t+1} \mid S_0 = s\right] = \sum_{s \in \mathcal{S}} d(s)v_{\pi}(s) = \overline{v}_{\pi}
\end{aligned}
$$

上述等式中，第一个等号由全期望公式（law of total expectation）推导得出，第二个等号由状态值的定义（$v_{\pi}(s)$ 是从状态 $s$ 出发的长期折扣奖励期望）推导得出。

**等价表达式 2：向量内积形式**

$\overline{v}_{\pi}$ 也可改写为两个向量的内积。具体地，令：

$$
\begin{aligned}
v_{\pi} = \left[\dots, v_{\pi}(s), \dots\right]^T \in \mathbb{R}^{|\mathcal{S}|}
\end{aligned}
$$

$$
\begin{aligned}
d = \left[\dots, d(s), \dots\right]^T \in \mathbb{R}^{|\mathcal{S}|}
\end{aligned}
$$

则有：

$$
\begin{aligned}
\overline{v}_{\pi} = d^T v_{\pi}
\end{aligned}
$$

该表达式在后续分析 $\overline{v}_{\pi}$ 的梯度时会非常有用。**指标 2：平均奖励（Average Reward）**

第二类指标是单步平均奖励，简称平均奖励 [2, 64, 65]。具体地，其定义为：

$$
\begin{aligned}
\overline{r}_{\pi} \doteq \sum_{s \in \mathcal{S}} d_{\pi}(s)r_{\pi}(s) = \mathbb{E}_{S \sim d_{\pi}}\left[r_{\pi}(S)\right] \tag{9.2}
\end{aligned}
$$

其中：
- $d_{\pi}$ 是策略 $\pi$ 下的平稳分布；
- $r_{\pi}(s)$ 是即时奖励的期望，其定义为：

$$
\begin{aligned}
r_{\pi}(s) \doteq \sum_{a \in \mathcal{A}} \pi(a \mid s, \theta)r(s, a) = \mathbb{E}_{A \sim \pi(s, \theta)}\left[r(s, A) \mid s\right] \tag{9.3}
\end{aligned}
$$

这里的 $r(s, a)$ 表示在状态 $s$ 执行动作 $a$ 时的即时奖励期望，即 $r(s, a) \doteq \mathbb{E}\left[R \mid s, a\right] = \sum_{r} r p(r \mid s, a)$（其中 $p(r \mid s, a)$ 是在状态 $s$ 执行动作 $a$ 时获得奖励 $r$ 的概率）。

**平均奖励 $\overline{r}_{\pi}$ 的等价表达式**

以下介绍 $\overline{r}_{\pi}$ 的另外两个重要等价表达式：

**等价表达式 1：基于长期平均奖励的极限形式**

假设智能体遵循给定策略 $\pi(\theta)$，收集到奖励序列 $\{R_{t+1}\}_{t=0}^{\infty}$。读者在文献中常能看到以下指标：

$$
\begin{aligned}
J(\theta) = \lim_{n \to \infty} \frac{1}{n}\mathbb{E}\left[\sum_{t=0}^{n-1} R_{t+1}\right] \tag{9.4}
\end{aligned}
$$

该指标初看之下不易理解，但实际上它与 $\overline{r}_{\pi}$ 相等：

$$
\begin{aligned}
\lim_{n \to \infty} \frac{1}{n}\mathbb{E}\left[\sum_{t=0}^{n-1} R_{t+1}\right] = \sum_{s \in \mathcal{S}} d_{\pi}(s)r_{\pi}(s) = \overline{r}_{\pi} \tag{9.5}
\end{aligned}
$$

式（9.5）的证明可参考 9.1 节的补充内容（Box 9.1）。

**等价表达式 2：向量内积形式**

式（9.2）中的平均奖励 $\overline{r}_{\pi}$ 也可改写为两个向量的内积。具体地，令：

$$
\begin{aligned}
r_{\pi} = \left[\dots, r_{\pi}(s), \dots\right]^T \in \mathbb{R}^{|\mathcal{S}|}
\end{aligned}
$$

$$
\begin{aligned}
d_{\pi} = \left[\dots, d_{\pi}(s), \dots\right]^T \in \mathbb{R}^{|\mathcal{S}|}
\end{aligned}
$$

其中 $r_{\pi}(s)$ 的定义如式（9.3）所示。此时显然有：

$$
\begin{aligned}
\overline{r}_{\pi} = \sum_{s \in \mathcal{S}} d_{\pi}(s)r_{\pi}(s) = d_{\pi}^T r_{\pi}
\end{aligned}
$$

该表达式在后续推导 $\overline{r}_{\pi}$ 的梯度时会非常有用。

**几点说明**

| 指标 | 表达式 1 | 表达式 2 | 表达式 3 |
|------|---------|---------|---------|
| 平均状态值 $\overline{v}_{\pi}$ | $\sum_{s \in \mathcal{S}} d(s)v_{\pi}(s)$ | $\mathbb{E}_{S \sim d}\left[v_{\pi}(S)\right]$ | $\lim_{n \to \infty} \mathbb{E}\left[\sum_{t=0}^{n} \gamma^t R_{t+1}\right]$ |
| 平均奖励 $\overline{r}_{\pi}$ | $\sum_{s \in \mathcal{S}} d_{\pi}(s)r_{\pi}(s)$ | $\mathbb{E}_{S \sim d_{\pi}}\left[r_{\pi}(S)\right]$ | $\lim_{n \to \infty} \frac{1}{n}\mathbb{E}\left[\sum_{t=0}^{n-1} R_{t+1}\right]$ |

**表 9.2**：平均状态值 $\overline{v}_{\pi}$ 与平均奖励 $\overline{r}_{\pi}$ 的不同但等价表达式汇总

到目前为止，我们已介绍两类指标：平均状态值 $\overline{v}_{\pi}$ 与平均奖励 $\overline{r}_{\pi}$。每类指标都有多个不同但等价的表达式，具体汇总于表 9.2。我们有时会用 $\overline{v}_{\pi}$ 特指 "状态分布为平稳分布 $d_{\pi}$" 的情况，用 $\overline{v}_{\pi}^0$ 特指 "分布 $d_0$ 与策略 $\pi$ 无关" 的情况。

以下是关于这些指标的几点说明：

- 所有这些指标都是策略 $\pi$ 的函数。由于策略 $\pi$ 由参数 $\theta$ 参数化，因此这些指标也是 $\theta$ 的函数。换句话说，$\theta$ 的取值不同，指标的数值也会不同。因此，我们可通过寻找 $\theta$ 的最优值来最大化这些指标 —— 这正是策略梯度方法的核心思想。

- 在折扣因子 $\gamma < 1$ 的折扣场景下，平均状态值 $\overline{v}_{\pi}$ 与平均奖励 $\overline{r}_{\pi}$ 是等价的。具体可证明：

$$\overline{r}_{\pi} = (1 - \gamma)\overline{v}_{\pi}$$

上述等式表明，两类指标可同时达到最大化。该等式的证明有缘再见。

## Gradients of the metrics

我们可采用基于梯度的方法来最大化这些指标。要实现这一点，首先需计算这些指标的梯度。本章最重要的理论结果是下述定理：

**定理 9.1（策略梯度定理）**

指标 $J(\theta)$ 的梯度为：

$$\nabla_{\theta}J(\theta) = \sum_{s \in \mathcal{S}} \eta(s) \sum_{a \in \mathcal{A}} \nabla_{\theta}\pi(a|s, \theta)q_{\pi}(s, a) \tag{9.8}$$

其中，$\eta$ 为状态分布，$\nabla_{\theta}\pi$ 表示策略 $\pi$ 对参数 $\theta$ 的梯度。

此外，式（9.8）可表示为更简洁的期望形式：

$$\nabla_{\theta}J(\theta) = \mathbb{E}_{S \sim \eta,A \sim \pi(S,\theta)}\left[\nabla_{\theta} \ln \pi(A|S, \theta)q_{\pi}(S, A)\right] \tag{9.9}$$

其中，$\ln$ 表示自然对数。

**关于定理 9.1 的几点重要说明**

需注意，定理 9.1 是对定理 9.2、定理 9.3 和定理 9.5 结果的汇总。这三个定理分别对应不同场景：涵盖不同指标（如 $\overline{v}_{\pi}^0$、$\overline{v}_{\pi}$、$\overline{r}_{\pi}$）及 "折扣 / 无折扣" 情况。这些场景下的梯度表达式形式相似，因此汇总为定理 9.1。$J(\theta)$ 与 $\eta$ 的具体表达式未在定理 9.1 中给出，需参考上述三个细分定理；式（9.8）中的等式可能是严格等式，也可能是近似等式，且分布 $\eta$ 在不同场景下也会有所不同。
需特别注意：为保证 $\ln \pi(a|s, \theta)$ 有意义（即对数的真数为正），所有 $(s, a)$（状态 - 动作对）对应的策略概率 $\pi(a|s, \theta)$ 都必须为正值。这一要求可通过 softmax 函数实现，具体形式为：

$$\pi(a|s, \theta) = \frac{e^{h(s,a,\theta)}}{\sum_{a' \in \mathcal{A}} e^{h(s,a',\theta)}}, \quad a \in \mathcal{A} \tag{9.12}$$

其中，$h(s, a, \theta)$ 是 "状态 $s$ 下选择动作 $a$ 的偏好函数"（可理解为对动作 $a$ 的 "打分"）。

式（9.12）定义的策略满足两个关键性质：

- 对任意状态 $s \in \mathcal{S}$，任意动作 $a \in \mathcal{A}$，$\pi(a|s, \theta) \in (0, 1)$（概率值在 0 到 1 之间）；
- 对任意状态 $s \in \mathcal{S}$，$\sum_{a \in \mathcal{A}} \pi(a|s, \theta) = 1$（所有动作的概率和为 1，符合概率分布的定义）。

该策略可通过神经网络实现：网络的输入为状态 $s$，输出层采用 softmax 层，最终输出所有动作 $a$ 对应的 $\pi(a|s, \theta)$（且输出值的和为 1），具体可参考图 9.2 (b)。由于所有动作的概率 $\pi(a|s, \theta) > 0$，该策略是随机策略—— 它不会直接指定 "应选择哪个动作"，而是要求根据策略的概率分布 "随机采样生成动作"，因此天然具备 "探索性"（即不会永远只选当前最优动作，也会尝试概率较低的动作）。
### Derivation of the gradients in the discounted case

接下来，我们推导折扣场景（其中 $\gamma \in (0, 1)$）下指标的梯度。折扣场景中的状态值（state value）与动作值（action value）定义如下：

$$v_{\pi}(s) = \mathbb{E}\left[R_{t+1} + \gamma R_{t+2} + \gamma^2 R_{t+3} + \dots \mid S_t = s\right]$$

$$q_{\pi}(s, a) = \mathbb{E}\left[R_{t+1} + \gamma R_{t+2} + \gamma^2 R_{t+3} + \dots \mid S_t = s, A_t = a\right]$$

易知以下关系成立：$v_{\pi}(s) = \sum_{a \in \mathcal{A}} \pi(a \mid s, \theta) q_{\pi}(s, a)$，且状态值满足贝尔曼方程（Bellman equation）。

首先，我们证明 $\overline{v}_{\pi}(\theta)$ 与 $\overline{r}_{\pi}(\theta)$ 是等价指标

**引理 9.1（$\overline{v}_{\pi}(\theta)$ 与 $\overline{r}_{\pi}(\theta)$ 的等价性）**：在 $\gamma \in (0, 1)$ 的折扣场景下，有

$$\overline{r}_{\pi} = (1 - \gamma)\overline{v}_{\pi} \tag{9.13}$$

**证明**：注意到 $\overline{v}_{\pi}(\theta) = d_{\pi}^T v_{\pi}$ 且 $\overline{r}_{\pi}(\theta) = d_{\pi}^T r_{\pi}$，其中 $v_{\pi}$ 与 $r_{\pi}$ 满足贝尔曼方程 $v_{\pi} = r_{\pi} + \gamma P_{\pi} v_{\pi}$。在贝尔曼方程两侧同时左乘 $d_{\pi}^T$，可得：

$$\overline{v}_{\pi} = \overline{r}_{\pi} + \gamma d_{\pi}^T P_{\pi} v_{\pi} = \overline{r}_{\pi} + \gamma d_{\pi}^T v_{\pi} = \overline{r}_{\pi} + \gamma \overline{v}_{\pi}$$

由此可推出式（9.13）。

其次，下述引理给出了任意状态 $s$ 对应的 $v_{\pi}(s)$ 的梯度

**引理 9.2（$v_{\pi}(s)$ 的梯度）**：在折扣场景下，对任意 $s \in \mathcal{S}$，有

$$\nabla_{\theta} v_{\pi}(s) = \sum_{s' \in \mathcal{S}} \text{Pr}_{\pi}(s' \mid s) \sum_{a \in \mathcal{A}} \nabla_{\theta} \pi(a \mid s', \theta) q_{\pi}(s', a) \tag{9.14}$$

其中，$\text{Pr}_{\pi}(s' \mid s) \doteq \sum_{k=0}^{\infty} \gamma^k \left[P_{\pi}^k\right]_{ss'} = \left[(I_n - \gamma P_{\pi})^{-1}\right]_{ss'}$ 表示在策略 $\pi$ 下，从状态 $s$ 转移到状态 $s'$ 的折扣总概率。此处，$[\cdot]_{ss'}$ 表示矩阵中 "第 $s$ 行、第 $s'$ 列" 的元素，而 $\left[P_{\pi}^k\right]_{ss'}$ 表示在策略 $\pi$ 下，从状态 $s$ 经过恰好 $k$ 步转移到状态 $s'$ 的概率。

借助引理 9.2 的结果，我们现在可以推导平均状态值 $\overline{v}_{\pi}^0$ 的梯度。

**定理 9.2（折扣场景下 $\overline{v}_{\pi}^0$ 的梯度）**

在 $\gamma \in (0, 1)$ 的折扣场景下，平均状态值 $\overline{v}_{\pi}^0 = d_0^T v_{\pi}$ 的梯度为：

$$\nabla_{\theta}\overline{v}_{\pi}^0 = \mathbb{E}\left[\nabla_{\theta}\ln\pi(A \mid S, \theta)q_{\pi}(S, A)\right]$$

其中，状态 $S$ 服从分布 $\rho_{\pi}$（即 $S \sim \rho_{\pi}$），动作 $A$ 服从策略分布 $\pi(S, \theta)$（即 $A \sim \pi(S, \theta)$）。

此处的状态分布 $\rho_{\pi}$ 定义为：

$$\rho_{\pi}(s) = \sum_{s' \in \mathcal{S}} d_0(s')Pr_{\pi}(s \mid s'),\quad s \in \mathcal{S} \tag{9.19}$$

其中，$Pr_{\pi}(s \mid s') = \sum_{k=0}^{\infty} \gamma^k [P_{\pi}^k]_{s's} = [(I - \gamma P_{\pi})^{-1}]_{s's}$，表示在策略 $\pi$ 下，从状态 $s'$ 转移到状态 $s$ 的折扣总概率。

借助引理 9.1 和引理 9.2，我们可推导平均奖励 $\overline{r}_{\pi}$ 与平均状态值 $\overline{v}_{\pi}$ 的梯度。

**定理 9.3（折扣场景下 $\overline{r}_{\pi}$ 与 $\overline{v}_{\pi}$ 的梯度）**

在 $\gamma \in (0, 1)$ 的折扣场景下，平均奖励 $\overline{r}_{\pi}$ 与平均状态值 $\overline{v}_{\pi}$ 的梯度满足：

$$\nabla_{\theta}\overline{r}_{\pi} = (1 - \gamma)\nabla_{\theta}\overline{v}_{\pi} \approx \sum_{s \in \mathcal{S}} d_{\pi}(s) \sum_{a \in \mathcal{A}} \nabla_{\theta}\pi(a \mid s, \theta)q_{\pi}(s, a) = \mathbb{E}\left[\nabla_{\theta}\ln\pi(A \mid S, \theta)q_{\pi}(S, A)\right]$$

其中，状态 $S$ 服从平稳分布 $d_{\pi}$（即 $S \sim d_{\pi}$），动作 $A$ 服从策略分布 $\pi(S, \theta)$（即 $A \sim \pi(S, \theta)$）。此处，$\gamma$ 越接近 1，该近似的精度越高。

### Derivation of the gradients in the undiscounted case

接下来，我们将说明如何在 $\gamma = 1$ 的无折扣场景下计算指标的梯度。读者可能会疑惑，为何在《深度强化学习》的前半内容中仅讨论了折扣场景，现在却突然开始考虑无折扣场景。事实上，平均奖励 $\overline{r}_{\pi}$ 的定义对折扣场景和无折扣场景均适用。尽管折扣场景下 $\overline{r}_{\pi}$ 的梯度是近似值，但我们将看到，无折扣场景下其梯度的形式更为简洁优雅。


状态值与泊松方程
在无折扣场景下，需要重新定义状态值（state value）与动作值（action value）。由于无折扣奖励和（即$\mathbb{E}[R_{t+1} + R_{t+2} + R_{t+3} + \dots \mid S_t = s]$）可能会发散，因此需以特殊方式定义状态值与动作值[64]：  
$$v_{\pi}(s) \doteq \mathbb{E}\left[(R_{t+1} - \overline{r}_{\pi}) + (R_{t+2} - \overline{r}_{\pi}) + (R_{t+3} - \overline{r}_{\pi}) + \dots \mid S_t = s\right],$$  
$$q_{\pi}(s, a) \doteq \mathbb{E}\left[(R_{t+1} - \overline{r}_{\pi}) + (R_{t+2} - \overline{r}_{\pi}) + (R_{t+3} - \overline{r}_{\pi}) + \dots \mid S_t = s, A_t = a\right],$$  

其中，$\overline{r}_{\pi}$为平均奖励，其值由给定的策略$\pi$唯一确定。在文献中，$v_{\pi}(s)$有多种不同名称，例如“差分奖励（differential reward）”[65]或“偏差（bias）”[2，第8.2.1节]。可以验证，上述定义的状态值满足以下**类贝尔曼方程（Bellman-like equation）**：  
$$v_{\pi}(s) = \sum_{a} \pi(a \mid s, \theta) \left[ \sum_{r} p(r \mid s, a)(r - \overline{r}_{\pi}) + \sum_{s'} p(s' \mid s, a)v_{\pi}(s') \right] \tag{9.22}$$  


由于$v_{\pi}(s) = \sum_{a \in \mathcal{A}} \pi(a \mid s, \theta) q_{\pi}(s, a)$，可推出动作值满足：$q_{\pi}(s, a) = \sum_{r} p(r \mid s, a)(r - \overline{r}_{\pi}) + \sum_{s'} p(s' \mid s, a)v_{\pi}(s')$。式（9.22）的**矩阵-向量形式**为：  
$$v_{\pi} = r_{\pi} - \overline{r}_{\pi} \mathbf{1}_n + P_{\pi} v_{\pi} \tag{9.23}$$  

其中，$\mathbf{1}_n = [1, \dots, 1]^T \in \mathbb{R}^n$（即$n$维全1向量）。式（9.23）与贝尔曼方程类似，它有一个专门的名称——**泊松方程（Poisson equation）**[65, 67]。


如何从泊松方程求解$v_{\pi}$？
下述定理给出了该问题的答案。

定理9.4（泊松方程的解）
设  
$$v_{\pi}^* = (I_n - P_{\pi} + \mathbf{1}_n d_{\pi}^T)^{-1} r_{\pi} \tag{9.24}$$  

则$v_{\pi}^*$是式（9.23）所示泊松方程的一个解。此外，泊松方程的任意解都具有以下形式：  
$$v_{\pi} = v_{\pi}^* + c \mathbf{1}_n$$  

其中，$c \in \mathbb{R}$（即$c$为任意实数）。

该定理表明，泊松方程的解可能不唯一。
具有唯一性。具体而言，由泊松方程可推出：

$$\begin{aligned}
\overline{r}_{\pi}\mathbf{1}_n &= r_{\pi} + (P_{\pi} - I_n)v_{\pi} \\
&= r_{\pi} + (P_{\pi} - I_n)(v_{\pi}^* + c\mathbf{1}_n) \\
&= r_{\pi} + (P_{\pi} - I_n)v_{\pi}^*.
\end{aligned}$$

值得注意的是，待定值 $c$ 在此过程中被消去，因此 $\overline{r}_{\pi}$ 具有唯一性。基于此，我们可计算无折扣场景下\(\overline{r}_{\pi}\)的梯度。此外，由于\(v_{\pi}\)不唯一，\(\overline{v}_{\pi}\)（平均状态值）也同样不唯一，因此本章不研究无折扣场景下\(\overline{v}_{\pi}\)的梯度。对于感兴趣的读者，值得一提的是：我们可通过添加更多约束条件，从泊松方程中唯一求解\(v_{\pi}\)。例如，通过假设存在一个循环状态（recurrent state），可确定该循环状态的状态值，进而确定c的值。除此之外，还有其他方法可唯一确定\(v_{\pi}\)。以下给出无折扣场景下\(\overline{r}_{\pi}\)的梯度。
定理9.5（无折扣场景下\(\overline{r}_{\pi}\)的梯度）在无折扣场景下，平均奖励\(\overline{r}_{\pi}\)的梯度为：$$\begin{aligned}
\nabla_{\theta}\overline{r}_{\pi} &= \sum_{s \in \mathcal{S}} d_{\pi}(s) \sum_{a \in \mathcal{A}} \nabla_{\theta}\pi(a \mid s, \theta)q_{\pi}(s, a) \\
&= \mathbb{E}\left[\nabla_{\theta}\ln\pi(A \mid S, \theta)q_{\pi}(S, A)\right]
\end{aligned}$$其中，状态S服从平稳分布\(d_{\pi}\)（即\(S \sim d_{\pi}\)），动作A服从策略分布\(\pi(S, \theta)\)（即\(A \sim \pi(S, \theta)\)）。与定理9.3所示的折扣场景相比，无折扣场景下\(\overline{r}_{\pi}\)的梯度更简洁优雅：一方面，式（9.28）严格成立（无需近似）；另一方面，状态S服从平稳分布，理论性质更清晰。

## Monte Carlo policy gradient (REINFORCE)
借助定理 9.1 中给出的梯度，我们接下来将说明如何使用基于梯度的方法优化指标，以获得最优策略。用于最大化 $J(\theta)$ 的梯度上升算法为：

$$\begin{aligned}
\theta_{t+1} &= \theta_t + \alpha\nabla_{\theta}J(\theta_t) \\
&= \theta_t + \alpha\mathbb{E}\left[\nabla_{\theta}\ln\pi(A|S, \theta_t)q_{\pi}(S, A)\right] \tag{9.31}
\end{aligned}$$

其中，$\alpha > 0$ 是常数学习率。由于式（9.31）中的真实梯度未知，我们可以用随机梯度替代真实梯度，得到如下算法：

$$\theta_{t+1} = \theta_t + \alpha\nabla_{\theta}\ln\pi(a_t|s_t, \theta_t)q_t(s_t, a_t) \tag{9.32}$$

其中，$q_t(s_t, a_t)$ 是 $q_{\pi}(s_t, a_t)$ 的近似值。若\(q_t(s_t, a_t)\)通过蒙特卡洛估计得到，则该算法被称为REINFORCE算法[68]（或蒙特卡洛策略梯度算法），它是最早、最简单的策略梯度算法之一。式（9.32）所示的算法具有重要意义，因为许多其他策略梯度算法都可通过对其扩展得到。接下来，我们将更深入地解读式（9.32）的含义。由\(\nabla_{\theta}\ln\pi(a_t|s_t, \theta_t) = \frac{\nabla_{\theta}\pi(a_t|s_t, \theta_t)}{\pi(a_t|s_t, \theta_t)}\)，可将式（9.32）改写为：\(\theta_{t+1} = \theta_t + \alpha\underbrace{\left( \frac{q_t(s_t, a_t)}{\pi(a_t|s_t, \theta_t)} \right)}_{\beta_t}\nabla_{\theta}\pi(a_t|s_t, \theta_t)\)进一步简化为：
$$\theta_{t+1} = \theta_t + \alpha\beta_t\nabla_{\theta}\pi(a_t|s_t, \theta_t) \tag{9.33}$$
从该式中可得出两个重要解读：解读一：梯度上升对动作概率的调节作用由于式（9.33）是简单的梯度上升算法，可得出以下结论：若\(\beta_t \geq 0\)，则选择（\(s_t, a_t\)）的概率会增强，即： \(\pi(a_t|s_t, \theta_{t+1}) \geq \pi(a_t|s_t, \theta_t)\)\(\beta_t\)的值越大，增强效果越强。若\(\beta_t < 0\)，则选择（\(s_t, a_t\)）的概率会降低，即： \(\pi(a_t|s_t, \theta_{t+1}) < \pi(a_t|s_t, \theta_t)\)上述结论的证明如下：当\(\theta_{t+1} - \theta_t\)足够小时，由泰勒展开可得：\(\begin{aligned}
\pi(a_t|s_t, \theta_{t+1}) &\approx \pi(a_t|s_t, \theta_t) + \left(\nabla_{\theta}\pi(a_t|s_t, \theta_t)\right)^T (\theta_{t+1} - \theta_t) \\
&= \pi(a_t|s_t, \theta_t) + \alpha\beta_t\left(\nabla_{\theta}\pi(a_t|s_t, \theta_t)\right)^T \left(\nabla_{\theta}\pi(a_t|s_t, \theta_t)\right) \quad (\text{代入式（9.33）}) \\
&= \pi(a_t|s_t, \theta_t) + \alpha\beta_t\left\|\nabla_{\theta}\pi(a_t|s_t, \theta_t)\right\|_2^2
\end{aligned}\)显然，当\(\beta_t \geq 0\)时，\(\pi(a_t|s_t, \theta_{t+1}) \geq \pi(a_t|s_t, \theta_t)\)；当\(\beta_t < 0\)时，\(\pi(a_t|s_t, \theta_{t+1}) < \pi(a_t|s_t, \theta_t)\)。解读二：探索与利用的平衡由\(\beta_t = \frac{q_t(s_t, a_t)}{\pi(a_t|s_t, \theta_t)}\)的表达式可知，该算法能在一定程度上实现探索（exploration）与利用（exploitation）的平衡：利用（ exploitation ）：\(\beta_t\)与\(q_t(s_t, a_t)\)成正比。若（\(s_t, a_t\)）的动作值较大，则\(\pi(a_t|s_t, \theta_t)\)会被增强，使得选择\(a_t\)的概率上升——算法倾向于“利用”价值更高的动作。探索（ exploration ）：当\(q_t(s_t, a_t) > 0\)时，\(\beta_t\)与\(\pi(a_t|s_t, \theta_t)\)成反比。若选择\(a_t\)的概率较小，则\(\pi(a_t|s_t, \theta_t)\)会被增强，使得选择\(a_t\)的概率上升——算法倾向于“探索”概率较低的动作。此外，由于式（9.32）通过采样近似式（9.31）中的真实梯度，明确“如何获取采样样本”十分重要：如何采样状态S？ 真实梯度\(\mathbb{E}\left[\nabla_{\theta}\ln\pi(A|S, \theta_t)q_{\pi}(S, A)\right]\)中的S需服从分布\(\eta\)，该分布可为策略\(\pi\)下的平稳分布\(d_{\pi}\)，或式（9.19）中的折扣总概率分布\(\rho_{\pi}\)。无论是\(d_{\pi}\)还是\(\rho_{\pi}\)，都反映了策略\(\pi\)下的长期行为。如何采样动作A？ 真实梯度中的A需服从\(\pi(A|S, \theta)\)的分布。理想的采样方式是遵循\(\pi(a|s_t, \theta_t)\)选择\(a_t\)——因此，策略梯度算法是同策略（on-policy） 算法（即采样与更新使用同一策略）。遗憾的是，在实际应用中，由于样本利用效率较低，上述理想的S和A采样方式并未被严格遵循。式（9.32）的一种更高样本效率的实现方式如算法9.1所示：首先遵循策略\(\pi(θ)\)生成一个回合（episode），然后利用回合中的每一个经验样本对\(\theta\)进行多次更新。
#### Policy Gradient by Monte Carlo (REINFORCE)
**Initialization**: Initial parameter $\theta$; $\gamma \in (0, 1)$; $\alpha > 0$.

**Goal**: Learn an optimal policy for maximizing $J(\theta)$.

**For each episode, do**:
1. Generate an episode $\{s_0, a_0, r_1, \dots, s_{T-1}, a_{T-1}, r_T\}$ following $\pi(\theta)$.
2. **For** $t = 0, 1, \dots, T - 1$:
   - **Value update**: $q_t(s_t, a_t) = \sum_{k=t+1}^{T} \gamma^{k-t-1} r_k$
   - **Policy update**: $\theta \leftarrow \theta + \alpha \nabla_{\theta} \ln \pi(a_t|s_t, \theta) q_t(s_t, a_t)$
 

## Summary
本章介绍了策略梯度方法，它是许多现代强化学习算法的基础。策略梯度方法属于“基于策略（policy-based）”的方法，是一大突破——因为前序章节介绍的所有方法均为“value-based”的方法。
策略梯度方法的核心思想十分简洁：选择合适的标量指标，通过梯度上升算法对其进行优化。
策略梯度方法中最复杂的部分是指标梯度的推导——这是因为我们需要区分“不同指标”“折扣/无折扣场景”等多种情况。幸运的是，不同场景下的梯度表达式具有相似性，因此我们将其汇总为定理9.1（本章最重要的理论结果）。
> 对许多读者而言，无需理解证明过程，只需掌握该定理的结论即可。
式（9.32）所示的策略梯度算法必须被准确理解，因为它是许多高级策略梯度算法的基础。在下一章中，该算法将被扩展为另一种重要的策略梯度方法——Actor-Critic。
