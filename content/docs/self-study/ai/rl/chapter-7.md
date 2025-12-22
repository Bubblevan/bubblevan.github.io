---
id: rl-chapter-7
title: 第7章 时序差分方法
sidebar_label: 第7章
---



# Temporal-Difference Methods

与时序差分（TD）学习类似，蒙特卡洛（MC）学习同样属于无模型方法，但 TD 学习因其增量式的形式而具备一些优势。

## TD learning of state values

给定一个策略 $\pi$，我们的目标是估计所有状态 $s \in S$ 对应的状态值 $v_{\pi}(s)$。假设我们拥有依据策略 $\pi$ 生成的若干经验样本 $(s_0, r_1, s_1, \dots, s_t, r_{t+1}, s_{t+1}, \dots)$，其中 $t$ 表示时间步。可通过以下 TD 算法利用这些样本估计状态值：

$$
\begin{aligned}
v_{t+1}(s_t) = v_t(s_t) - \alpha_t(s_t)[v_t(s_t) - (r_{t+1} + \gamma v_t(s_{t+1}))] \tag{7.1}
\end{aligned}
$$

对所有 $s \neq s_t$，有：

$$
\begin{aligned}
v_{t+1}(s) = v_t(s) \tag{7.2}
\end{aligned}
$$

其中 $t = 0, 1, 2, \dots$。式中，$v_t(s_t)$ 表示 $t$ 时刻对 $v_{\pi}(s_t)$ 的估计值；$\alpha_t(s_t)$ 表示 $t$ 时刻状态 $s_t$ 对应的学习率。

需要注意的是，在 $t$ 时刻，仅对已访问状态 $s_t$ 的状态值进行更新。如式 (7.2) 所示，未访问状态（$s \neq s_t$）的状态值保持不变。为简洁起见，式 (7.2) 常被省略，但需牢记其存在 —— 若缺少该式，算法在数学层面将不完整。

首次接触 TD 学习算法的读者可能会疑惑，该算法为何如此设计。事实上，它可被视为用于求解贝尔曼方程的一种特殊随机近似算法。要理解这一点，首先回顾状态值的定义：

$$
\begin{aligned}
v_{\pi}(s) = \mathbb{E}[R_{t+1} + \gamma G_{t+1} \mid S_t = s], \quad s \in S \tag{7.3}
\end{aligned}
$$

我们可将式 (7.3) 重写为：

$$
\begin{aligned}
v_{\pi}(s) = \mathbb{E}[R_{t+1} + \gamma v_{\pi}(S_{t+1}) \mid S_t = s], \quad s \in S \tag{7.5}
\end{aligned}
$$

这是因为 $\mathbb{E}[G_{t+1} \mid S_t = s] = \sum_a \pi(a|s) \sum_{s'} p(s'|s, a) v_{\pi}(s') = \mathbb{E}[v_{\pi}(S_{t+1}) \mid S_t = s]$。式 (7.5) 是贝尔曼方程的另一种表达形式，有时也被称为贝尔曼期望方程。

将 RM 算法（第 6 章）应用于求解式 (7.5) 中的贝尔曼方程，即可推导出 TD 算法。
### Property analysis

首先，我们对 TD 算法的表达式进行更细致的分析:

<div style={{textAlign: 'center'}}>

![TD 算法表达式分析](/img/rl/f7-1.png)

</div>

其中，$\bar{v}_{t} \doteq r_{t+1}+\gamma v_{t}(s_{t+1})$ 被称为 **TD 目标**；而 $\delta_{t} \doteq v_{t}(s_{t}) - \bar{v}_{t} = v_{t}(s_{t}) - (r_{t+1}+\gamma v_{t}(s_{t+1}))$ 被称为 **TD 误差**。可见，新估计值 $v_{t+1}(s_{t})$ 是当前估计值 $v_{t}(s_{t})$ 与 TD 误差 $\delta_{t}$ 的结合体。

- <span style={{color: "red"}}>**为何 $\bar{v}_{t}$ 被称为 TD 目标？**</span>

这是因为 $\bar{v}_{t}$ 是算法试图使 $v(s_{t})$ 逼近的目标值。为验证这一点，对式 (7.1) 两边同时减去 $\bar{v}_{t}$，可得：

$$
\begin{aligned}
v_{t+1}(s_{t}) - \bar{v}_{t} &= \left[ v_{t}(s_{t}) - \bar{v}_{t} \right] - \alpha_{t}(s_{t}) \left[ v_{t}(s_{t}) - \bar{v}_{t} \right] \\
&= \left[ 1 - \alpha_{t}(s_{t}) \right] \left[ v_{t}(s_{t}) - \bar{v}_{t} \right]
\end{aligned}
$$

对上述等式两边取绝对值，有：

$$|v_{t+1}(s_{t}) - \bar{v}_{t}| = |1 - \alpha_{t}(s_{t})| \cdot |v_{t}(s_{t}) - \bar{v}_{t}|$$

由于 $\alpha_{t}(s_{t})$ 是一个较小的正数，因此 $0 < 1 - \alpha_{t}(s_{t}) < 1$。由此可推出：

$$|v_{t+1}(s_{t}) - \bar{v}_{t}| < |v_{t}(s_{t}) - \bar{v}_{t}|$$

这不等式表明新值 $v_{t+1}(s_{t})$ 相比旧值 $v_{t}(s_{t})$ 更接近 $\bar{v}_{t}$。因此，从数学角度而言，该算法会**驱动 $v_{t}(s_{t})$ 向 $\bar{v}_{t}$ 逼近** —— 这正是 $\bar{v}_{t}$ 被称为 TD 目标的原因。

- <span style={{color: "red"}}>**TD 误差的含义是什么？**</span>

首先，该误差被称为 "时序差分（temporal-difference）误差"，是因为 $\delta_{t} = v_{t}(s_{t}) - (r_{t+1}+\gamma v_{t}(s_{t+1}))$ 反映了 $t$ 步与 $t+1$ 步这两个时间步之间的差异。

其次，当状态值估计准确时，TD 误差的期望为零。具体来说，当 $v_{t} = v_{\pi}$（估计值等于真实状态值）时，TD 误差的期望为：

$$
\begin{aligned}
\mathbb{E}[\delta_{t} \mid S_{t} = s_{t}] &= \mathbb{E}\left[ v_{\pi}(S_{t}) - (R_{t+1}+\gamma v_{\pi}(S_{t+1})) \mid S_{t} = s_{t} \right] \\
&= v_{\pi}(s_{t}) - \mathbb{E}\left[ R_{t+1}+\gamma v_{\pi}(S_{t+1}) \mid S_{t} = s_{t} \right] \\
&= 0 \quad (\text{由式(7.3)可得})
\end{aligned}
$$

因此，TD 误差不仅反映了两个时间步之间的差异，更重要的是，它还反映了估计值 $v_{t}$ 与真实状态值 $v_{\pi}$ 之间的差异。从更抽象的层面来看，TD 误差可被理解为 <span style={{color: "red"}}>**"新息（innovation）"**</span>—— 即从经验样本 $(s_{t}, r_{t+1}, s_{t+1})$ 中获取的新信息。TD 学习的核心思想正是基于新获取的信息，修正当前的状态值估计。<span style={{color: "red"}}>**"新息"**</span> 这一概念在诸多估计问题（如卡尔曼滤波）中都具有基础性地位。

> 式 (7.1) 所示的 TD 算法仅能估计给定策略的状态值。若要寻找最优策略，还需进一步计算动作值，再执行策略改进步骤。

<span style={{color: "red"}}>**尽管 TD 学习与蒙特卡洛（MC）学习均为无模型方法，但二者的优缺点有何差异？**</span>

| 特性 | TD 学习 | 蒙特卡洛（MC）学习 |
|------|---------|-------------------|
| **增量式** | TD 学习是增量式的，在接收到经验样本后可立即更新状态 / 动作值。 | MC 学习是**非增量式**的，必须等待一个回合（episode）完整收集后才能更新 —— 这是因为它需要计算该回合的折扣回报。 |
| **任务类型** | 支持持续任务：由于是增量式，TD 学习可同时处理回合制任务（episodic tasks）与持续任务（continuing tasks）。其中，持续任务可能不存在终止状态。 | 由于是非增量式，MC 学习仅能处理**回合制任务** —— 这类任务的每个回合会在有限步后终止。 |
| **自举性（Bootstrapping）** | TD 学习具有自举性，因为其状态 / 动作值的更新依赖于该值之前的估计结果。因此，TD 学习需要对值进行初始猜测。 | MC 学习不具备自举性，因为它无需初始猜测即可直接估计状态 / 动作值。 |
| **估计方差** | TD 学习的估计方差低于 MC 学习，原因是它涉及的随机变量更少。例如，要估计动作值 $q_{\pi}(s_{t}, a_{t})$，Sarsa 仅需三个随机变量的样本：$R_{t+1}$、$S_{t+1}$、$A_{t+1}$。 | MC 学习的估计方差更高，因为它涉及大量随机变量。例如，要估计 $q_{\pi}(s_{t}, a_{t})$，需要 $R_{t+1}+\gamma R_{t+2}+\gamma^2 R_{t+3}+\dots$ 的样本。假设每个回合的长度为 $L$，且每个状态的动作数均为 $A$，那么在软策略（soft policy）下，可能存在 $A^L$ 种不同的回合。若仅用少量回合进行估计，估计方差较高便不足为奇。 |

**表 7.1**：TD 学习与蒙特卡洛（MC）学习的对比

### Convergence analysis

**定理 7.1（TD 学习的收敛性）**：给定一个策略 $\pi$，若对所有状态 $s \in S$，均满足 $\sum_{t} \alpha_{t}(s)=\infty$ 且 $\sum_{t} \alpha_{t}^{2}(s)<\infty$，则通过式 (7.1) 的 TD 算法，当 $t \to \infty$ 时，对所有 $s \in S$，状态值估计 $v_{t}(s)$ 几乎必然收敛到真实状态值 $v_{\pi}(s)$。

关于学习率 $\alpha_{t}$ 的几点说明如下：

- 条件 $\sum_{t} \alpha_{t}(s)=\infty$ 与 $\sum_{t} \alpha_{t}^{2}(s)<\infty$ 必须对所有 $s \in S$ 均成立。需要注意的是，在时刻 $t$，若状态 $s$ 被访问，则 $\alpha_{t}(s)>0$；否则 $\alpha_{t}(s)=0$。

- 条件 $\sum_{t} \alpha_{t}(s)=\infty$ 要求状态 $s$ 被访问无限多次（或足够多次），这需要满足探索起始条件（exploring starts）或采用探索性策略（exploratory policy），以确保每个状态-动作对（state-action pair）都有可能被多次访问。

- 在实际应用中，学习率 $\alpha_{t}$ 通常被选为一个较小的正常数。此时，$\sum_{t} \alpha_{t}^{2}(s)<\infty$ 这一条件不再成立。但即便 $\alpha$ 为常数，仍可证明该算法在期望意义下收敛。

## TD learning of action values: Sarsa

上面的第一种 TD Learning 仅能估计 state value，而本节的 Sarsa 可直接估计 action value。估计动作值具有重要意义，因为它可与策略改进步骤相结合，从而学习最优策略。
### Algorithm description
> 初始时智能体在 “起点 s₀”，按策略 π 选了动作 a₀（比如 “向右”）；
> 执行 a₀后，环境反馈一个回报 r₁（比如 “没碰到墙，得 - 1 分”，因为每走一步消耗成本），同时智能体进入新状态 s₁（“下一个路口”）；
> 在 s₁，智能体再按策略 π 选动作 a₁（比如还是 “向右”）；
> 重复这个过程，就记录下序列：(s₀,a₀,r₁,s₁,a₁,r₂,s₂,a₂,…,sₜ,aₜ,rₜ₊₁,sₜ₊₁,aₜ₊₁)—— 这就是 “依据策略 π 生成的经验样本”，每一段 (sₜ,aₜ,rₜ₊₁,sₜ₊₁,aₜ₊₁) 都对应 “t 时刻的决策→环境反馈→t+1 时刻的决策”。

给定一个策略 $\pi$，我们的目标是估计其动作值。假设我们拥有依据策略 $\pi$ 生成的经验样本：$(s_0, a_0, r_1, s_1, a_1, \dots, s_t, a_t, r_{t+1}, s_{t+1}, a_{t+1}, \dots)$。可通过以下 **Sarsa 算法**估计动作值：

$$
\begin{aligned}
q_{t+1}(s_t, a_t) = q_t(s_t, a_t) - \alpha_t(s_t, a_t)\left[ q_t(s_t, a_t) - (r_{t+1} + \gamma q_t(s_{t+1}, a_{t+1})) \right] \tag{7.12}
\end{aligned}
$$

对于所有 $(s, a) \neq (s_t, a_t)$，有：

$$
\begin{aligned}
q_{t+1}(s, a) = q_t(s, a)
\end{aligned}
$$

其中，$t = 0, 1, 2, \dots$，$\alpha_t(s_t, a_t)$ 为学习率；$q_t(s_t, a_t)$ 是动作值 $q_{\pi}(s_t, a_t)$ 的估计值。在时刻 $t$，**仅更新 $(s_t, a_t)$ 对应的动作值（q 值），其余 $(s, a)$ 的 q 值保持不变**。

> 智能体在 t 时刻只做了一件事：在 sₜ选了 aₜ，得到了 rₜ₊₁和 sₜ₊₁—— 这仅能告诉我们 “(sₜ,aₜ) 的效果如何”，没有任何关于 “其他状态（比如 s₁、s₂）或其他动作（比如在 sₜ选‘向左’）” 的新信息；没有新信息，就无法判断 “之前对其他 (s,a) 的估计是否需要改”，所以只能保持原来的估计（qₜ₊₁(s,a)=qₜ(s,a)）。
- <span style={{color: "red"}}>**为何该算法被命名为 Sarsa？**</span>

因为算法的每一次迭代都需要用到样本 $(s_t, a_t, r_{t+1}, s_{t+1}, a_{t+1})$，而 "Sarsa" 正是 "**状态-动作-回报-状态-动作**"（state-action-reward-state-action）的缩写。

- <span style={{color: "red"}}>**Sarsa 算法为何如此设计？**</span>

不难发现，Sarsa 算法与 7.1 节式 (7.1) 的 TD 算法存在相似性。事实上，**只需将 TD 算法中的 "状态值估计" 替换为 "动作值估计"，即可轻松得到 Sarsa 算法**。

- <span style={{color: "red"}}>**从数学角度看，Sarsa 算法的作用是什么？**</span>

与 7.1 节式 (7.1) 的 TD 算法类似，Sarsa 算法是用于求解给定策略贝尔曼方程的随机近似算法，其对应的贝尔曼方程为：

$$
\begin{aligned}
q_\pi(s, a) = \mathbb{E}\left[ R + \gamma q_\pi(S', A') \mid s, a \right], \quad \forall (s, a) \tag{7.13}
\end{aligned}
$$

式 (7.13) 是基于动作值的贝尔曼方程表达形式，其证明过程直接跳了。

- <span style={{color: "red"}}>**Sarsa 算法是否收敛？**</span>

由于 Sarsa 算法是 7.1 节式 (7.1) TD 算法的 "动作值版本"，其收敛性结论与定理 7.1 类似，具体如下：

**定理 7.2（Sarsa 算法的收敛性）**：给定一个策略 $\pi$，若对所有 $(s, a)$，均满足 $\sum_{t} \alpha_t(s, a) = \infty$ 且 $\sum_{t} \alpha_t^2(s, a) < \infty$，则通过式 (7.12) 的 Sarsa 算法，当 $t \to \infty$ 时，对所有 $(s, a)$，动作值估计 $q_t(s, a)$ 几乎必然收敛到真实动作值 $q_{\pi}(s, a)$。

该定理的证明过程与定理 7.1 类似，此处省略。需注意，$\sum_{t} \alpha_t(s, a) = \infty$ 与 $\sum_{t} \alpha_t^2(s, a) < \infty$ 这两个条件需对所有 $(s, a)$ 成立。其中，$\sum_{t} \alpha_t(s, a) = \infty$ 要求**每个状态-动作对都必须被访问无限多次（或足够多次）**。在时刻 $t$，若 $(s, a) = (s_t, a_t)$，则 $\alpha_t(s, a) > 0$；否则 $\alpha_t(s, a) = 0$。

### Optimal policy learning via Sarsa

式 (7.12) 的 Sarsa 算法仅能估计给定策略的动作值，若要寻找最优策略，需将其与策略改进步骤相结合。这种 "**动作值估计+策略改进**" 的组合方法通常也被称为 Sarsa 算法：

#### Optimal policy learning by Sarsa

- **Initialization**: $\alpha_t(s, a) = \alpha > 0$ for all $(s, a)$ and all $t$. $\epsilon \in (0, 1)$. Initial $q_0(s, a)$ for all $(s, a)$. Initial $\epsilon$-greedy policy $\pi_0$ derived from $q_0$.
- **Goal**: Learn an optimal policy that can lead the agent to the target state from an initial state $s_0$.
- **For each episode, do**:
  - Generate $a_0$ at $s_0$ following $\pi_0(s_0)$
  - If $s_t$ ($t = 0, 1, 2, \dots$) is not the target state, do:
    - Collect an experience sample $(r_{t+1}, s_{t+1}, a_{t+1})$ given $(s_t, a_t)$: generate $r_{t+1}, s_{t+1}$ by interacting with the environment; generate $a_{t+1}$ following $\pi_t(s_{t+1})$.
    - Update q-value for $(s_t, a_t)$:
      $$q_{t+1}(s_t, a_t) = q_t(s_t, a_t) - \alpha_t(s_t, a_t)\left[ q_t(s_t, a_t) - (r_{t+1} + \gamma q_t(s_{t+1}, a_{t+1})) \right]$$
    - Update policy for $s_t$: $s_t \leftarrow s_{t+1}$, $a_t \leftarrow a_{t+1}$
      $$\pi_{t+1}(a|s_t) = \begin{cases} 1 - \epsilon + \frac{\epsilon}{|A(s_t)|} & \text{if } a = \arg\max_a q_{t+1}(s_t, a) \\ \frac{\epsilon}{|A(s_t)|} & \text{otherwise} \end{cases}$$


如算法 7.1 所示，每一次迭代包含**两个核心步骤**：
第一步是更新已访问状态-动作对的 q 值；第二步是将策略更新为 $\epsilon$-贪婪策略。其中，q 值更新步骤仅更新时刻 $t$ 访问的那个状态-动作对的 q 值，随后立即更新 $s_t$ 对应的策略——这意味着在更新策略前，我们并未对当前策略进行充分评估，其理论依据是 "**广义策略迭代**"（generalized policy iteration）思想。此外，策略更新后会立即用于生成下一个经验样本，而此处采用 $\epsilon$-贪婪策略的目的是**保证策略具有探索性**。
为验证 Sarsa 算法的有效性，图 7.2 给出了一个仿真示例。与本书此前介绍的任务不同，该任务的目标是寻找从 "**特定初始状态**" 到 "**目标状态**" 的最优路径，而非为所有状态寻找最优策略。

<div style={{textAlign: 'center'}}>

![Sarsa 算法仿真结果](/img/rl/f7-2.png)

</div>

**仿真设置**：所有回合均从左上角的初始状态开始，到达目标状态后终止。回报设置为：目标状态回报 $r_{\text{target}} = 0$，禁止状态回报 $r_{\text{forbidden}}$ 与边界状态回报 $r_{\text{boundary}}$ 均为 $-10$，其他状态回报 $r_{\text{other}} = -1$。对所有 $t$，设 $\alpha_t(s, a) = 0.1$，探索率 $\epsilon = 0.1$；所有 $(s, a)$ 的初始动作值猜测为 $q_0(s, a) = 0$；初始策略为均匀分布策略，即对所有 $s$ 和 $a$，$\pi_0(a \mid s) = 0.2$。

**学到的策略**：图 7.2 左图展示了 Sarsa 算法学到的最终策略。可见，该策略能成功引导智能体从初始状态到达目标状态，但其他部分状态的策略可能并非最优——这是因为这些状态未得到充分探索。

**每个回合的总回报**：图 7.2 右上子图展示了每个回合的总回报（总回报为所有即时回报的非折扣和）。可见，总回报随回合数增加逐渐上升：初始策略性能较差，智能体频繁获得负回报；随着策略不断优化，总回报逐步提高。

**每个回合的长度**：图 7.2 右下子图显示，每个回合的长度（即智能体从初始状态到目标状态的步数）随回合数增加逐渐减少：初始策略性能差，智能体可能需要绕很多弯路才能到达目标状态；随着策略优化，路径长度逐渐缩短。需注意，部分回合的长度可能突然增加（如第 460 个回合），对应的总回报也会急剧下降——这是因为策略为 $\epsilon$-贪婪策略，存在选择非最优动作的概率。解决该问题的一种方法是采用 "**衰减型 $\epsilon$**"，即让 $\epsilon$ 的值随回合数增加逐渐收敛到 0。

## TD learning of action values: n-step Sarsa

本节介绍 **n 步 Sarsa 算法**，它是 Sarsa 算法的扩展形式。后文将表明，Sarsa 算法与蒙特卡洛（MC）学习均为 n 步 Sarsa 算法的两种极端情况。

回顾动作值的定义：

$$
\begin{aligned}
q_\pi(s, a) = \mathbb{E}[G_t \mid S_t = s, A_t = a] \tag{7.16}
\end{aligned}
$$

其中，$G_t$ 为折扣回报，满足：
$$
\begin{aligned}
G_t = R_{t+1} + \gamma R_{t+2} + \gamma^2 R_{t+3} + \dots
\end{aligned}
$$

事实上，$G_t$ 还可分解为多种形式：

<div style={{textAlign: 'center'}}>

![折扣回报的分解形式](/img/rl/f7-3.png)

</div>

需注意，$G_t = G_t^{(1)} = G_t^{(2)} = G_t^{(n)} = G_t^{(\infty)}$，上标仅用于区分 $G_t$ 的不同分解结构，不改变其本质含义。将 $G_t^{(n)}$ 的不同分解形式代入式 (7.16) 中 $q_\pi(s, a)$ 的表达式，可得到不同的算法。

**1. 当 $n=1$ 时**

此时有：

$$q_\pi(s, a) = \mathbb{E}[G_t^{(1)} \mid s, a] = \mathbb{E}[R_{t+1} + \gamma q_\pi(S_{t+1}, A_{t+1}) \mid s, a]$$

求解该方程对应的随机近似算法为：

$$q_{t+1}(s_t, a_t) = q_t(s_t, a_t) - \alpha_t(s_t, a_t)\left[ q_t(s_t, a_t) - (r_{t+1} + \gamma q_t(s_{t+1}, a_{t+1})) \right]$$

这正是式 (7.12) 中的 **Sarsa 算法**。

**2. 当 $n=\infty$ 时**

此时有：

$$q_\pi(s, a) = \mathbb{E}[G_t^{(\infty)} \mid s, a] = \mathbb{E}[R_{t+1} + \gamma R_{t+2} + \gamma^2 R_{t+3} + \dots \mid s, a]$$

求解该方程对应的算法为：

$$q_{t+1}(s_t, a_t) = g_t \doteq r_{t+1} + \gamma r_{t+2} + \gamma^2 r_{t+3} + \dots$$

其中，$g_t$ 是 $G_t$ 的一个样本。实际上，这就是 **蒙特卡洛（MC）学习算法**——它利用从 $(s_t, a_t)$ 开始的整个回合的折扣回报，来近似 $(s_t, a_t)$ 的动作值。

**3. 当 $n$ 为一般值时**

此时有：

$$q_\pi(s, a) = \mathbb{E}[G_t^{(n)} \mid s, a] = \mathbb{E}[R_{t+1} + \gamma R_{t+2} + \cdots + \gamma^n q_\pi(S_{t+n}, A_{t+n}) \mid s, a]$$

求解上述方程对应的算法为：

$$
\begin{aligned}
q_{t+1}(s_t, a_t) &= q_t(s_t, a_t) \\
&\quad - \alpha_t(s_t, a_t)\left[ q_t(s_t, a_t) - (r_{t+1} + \gamma r_{t+2} + \cdots + \gamma^n q_t(s_{t+n}, a_{t+n})) \right] \tag{7.17}
\end{aligned}
$$

该算法被称为 **n 步 Sarsa 算法**。

综上，n 步 Sarsa 算法是一种更具一般性的算法：当 $n=1$ 时，它退化为（1 步）Sarsa 算法；当 $n=\infty$ 且设置 $\alpha_t=1$ 时，它退化为蒙特卡洛（MC）学习算法。

要实现式 (7.17) 的 n 步 Sarsa 算法，需用到经验样本 $(s_t, a_t, r_{t+1}, s_{t+1}, a_{t+1}, \dots, r_{t+n}, s_{t+n}, a_{t+n})$。由于在时刻 $t$，$(r_{t+n}, s_{t+n}, a_{t+n})$ 尚未被收集，因此**必须等待到时刻 $t+n$，才能更新 $(s_t, a_t)$ 的 q 值**。为此，可将式 (7.17) 重写为：

$$
\begin{aligned}
q_{t+n}(s_t, a_t) &= q_{t+n-1}(s_t, a_t) \\
&\quad - \alpha_{t+n-1}(s_t, a_t)\left[ q_{t+n-1}(s_t, a_t) - (r_{t+1} + \gamma r_{t+2} + \cdots + \gamma^n q_{t+n-1}(s_{t+n}, a_{t+n})) \right]
\end{aligned}
$$

其中，$q_{t+n}(s_t, a_t)$ 是时刻 $t+n$ 时对 $q_\pi(s_t, a_t)$ 的估计值。

由于 n 步 Sarsa 算法将 Sarsa 算法和蒙特卡洛学习视为两种极端情况，因此其性能介于两者之间也就不足为奇了。具体来说：

- **若 $n$ 取值较大**，n 步 Sarsa 算法会接近蒙特卡洛学习：估计结果的**方差相对较高，但偏差较小**；
- **若 $n$ 取值较小**，n 步 Sarsa 算法则接近 Sarsa 算法：估计结果的**偏差相对较大，但方差较低**。

最后需说明，本节介绍的 n 步 Sarsa 算法仅用于**策略评估**（即估计给定策略的动作值），若要学习最优策略，必须将其与策略改进步骤相结合。其实现过程与 Sarsa 算法类似，此处不再赘述。

## TD learning of optimal action values: Q-learning

本节将介绍 **Q 学习算法**，它是强化学习领域最经典的算法之一。回顾可知，Sarsa 算法仅能估计给定策略的动作值，若要寻找最优策略，必须将其与策略改进步骤相结合。与之不同的是，**Q 学习可直接估计最优动作值并找到最优策略**。

Q 学习算法的表达式如下：

$$
\begin{aligned}
q_{t+1}(s_t, a_t) = q_t(s_t, a_t) - \alpha_t(s_t, a_t)\left[ q_t(s_t, a_t) - \left( r_{t+1} + \gamma \max_{a \in \mathcal{A}(s_{t+1})} q_t(s_{t+1}, a) \right) \right] \tag{7.18}
\end{aligned}
$$

对于所有 $(s, a) \neq (s_t, a_t)$，有：
$$
\begin{aligned}
q_{t+1}(s, a) = q_t(s, a)
\end{aligned}
$$
其中 $t = 0, 1, 2, \dots$。式中，$q_t(s_t, a_t)$ 是状态-动作对 $(s_t, a_t)$ 最优动作值的估计值，$\alpha_t(s_t, a_t)$ 是状态-动作对 $(s_t, a_t)$ 对应的学习率。

Q 学习与 Sarsa 的表达式较为相似，TD 目标的前半部分 $r_{t+1}$ 是即时回报—— 表示 "在 $t$ 时刻执行动作 $a_t$ 后，环境立即反馈的奖励"。二者的差异仅体现在 TD 目标的后半部分上：**Q 学习的 TD 目标为 $r_{t+1} + \gamma \max_a q_t(s_{t+1}, a)$，而 Sarsa 的 TD 目标为 $r_{t+1} + \gamma q_t(s_{t+1}, a_{t+1})$**。

**Sarsa 的 TD 目标** —— $r_{t+1} + \gamma q_t(s_{t+1}, a_{t+1})$

这里的 $a_{t+1}$ 是有下标的 "**特定动作**"，需要先明确它的来源：$a_{t+1}$ 是 "智能体在 $t+1$ 时刻，处于状态 $s_{t+1}$ 时，按照当前策略 $\pi$ 实际选择的动作"（比如 Sarsa 用 $\epsilon$-贪婪策略，在 $s_{t+1}$ 有 90% 概率选当前 q 值最大的动作，10% 随机选，$a_{t+1}$ 就是这次实际选的那个）；$q_t(s_{t+1}, a_{t+1})$ 是 "到 $t$ 时刻为止，对'在 $s_{t+1}$ 选 $a_{t+1}$' 这个动作值的估计"。

所以 Sarsa 的 TD 目标数学含义是："当前动作 $(s_t, a_t)$ 的'理想价值' = 即时回报 $r_{t+1}$ + 折扣后的'下一步实际动作的估计价值'"—— 它依赖 "**下一步实际做了什么动作**"，是一种 "**跟随当前策略的保守估计**"。

举个例子：假设智能体在 $t$ 时刻处于 "路口 $s_t$"，选了 "向右 $a_t$"，得到即时回报 $r_{t+1}=-1$（走一步成本），进入新状态 "下一个路口 $s_{t+1}$"；按当前 $\epsilon$-贪婪策略，在 $s_{t+1}$ 实际选了 "向上 $a_{t+1}$"，且当前对 $(s_{t+1}, a_{t+1})$ 的估计是 $q_t(s_{t+1}, a_{t+1})=-8$（预计还要走 8 步到终点）。那么 Sarsa 的 TD 目标就是：$-1 + 0.9 \times (-8) = -8.2$—— 它基于 "下一步实际选的向上动作" 来计算当前动作的理想价值。

**Q 学习的 TD 目标** —— $r_{t+1} + \gamma \max_a q_t(s_{t+1}, a)$

这里的 $a$ 是无下标的 "**所有可能动作**"，$\max_a$ 是 "对所有动作取最大值"，需要拆解两个关键点：

- **无下标的 $a$**：代表 "状态 $s_{t+1}$ 下所有可选的动作"（比如 $s_{t+1}$ 是路口，可选动作是 "上、下、左、右"，这里的 $a$ 就遍历这 4 个动作）；
- **$\max_a q_t(s_{t+1}, a)$**：表示 "在 $s_{t+1}$ 的所有可选动作中，找到当前估计值 $q_t$ 最大的那个动作，取它的 q 值"—— 这是 "不考虑当前策略实际选了什么，只追求'理论上最好的动作价值'"。

所以 Q 学习的 TD 目标数学含义是："当前动作 $(s_t, a_t)$ 的'理想价值' = 即时回报 $r_{t+1}$ + 折扣后的'下一步所有动作中最好的估计价值'"—— 它不依赖 "下一步实际做了什么"，只关心 "**下一步理论上最好的结果**"，是一种 "**追求最优的激进估计**"。

延续上面的例子：智能体在 $t$ 时刻选 "向右 $a_t$" 后，进入 $s_{t+1}$，得到 $r_{t+1}=-1$；$s_{t+1}$ 的 4 个动作估计值分别是：上（-8）、下（-15）、左（-10）、右（-5）。那么 Q 学习的 TD 目标就是：$-1 + 0.9 \times \max(-8, -15, -10, -5) = -1 + 0.9 \times (-5) = -5.5$—— 它不管下一步实际选了 "向上" 还是 "向右"，只取所有动作中 q 值最大的 "向右" 来计算当前动作的理想价值。

此外，给定状态-动作对 $(s_t, a_t)$ 时，Sarsa 算法每次迭代需用到样本 $(r_{t+1}, s_{t+1}, a_{t+1})$，而 Q 学习仅需用到样本 $(r_{t+1}, s_{t+1})$。

**简单来说**：Sarsa 是 "**走一步看一步，跟着当前策略的实际动作算价值**"，所以需要下一步的实际动作；Q 学习是 "**走一步看最好的一步，不管当前策略实际走了什么，只按理论最优算价值**"，所以不需要下一步的实际动作。这其实是在线离线策略的一种对比体现，在后面会详细说明。

- <span style={{color: "red"}}>**Q 学习为何设计成式 (7.18) 的形式？其数学意义是什么？**</span>

Q 学习是用于求解以下方程的随机近似算法：

$$
\begin{aligned}
q(s, a) = \mathbb{E}\left[ R_{t+1} + \gamma \max_a q(S_{t+1}, a) \mid S_t = s, A_t = a \right] \tag{7.19}
\end{aligned}
$$

该方程是基于动作值的贝尔曼最优方程，其证明过程直接跳了。

### Off-policy vs On-policy

Q 学习与其他时序差分（TD）算法相比，稍显特殊的一点在于：**Q 学习属于离线策略学习，而其他 TD 算法均属于在线策略学习**。

在任何强化学习任务中，都存在两种策略：**行为策略（Behavior Policy）** 和 **目标策略（Target Policy）**。

- **行为策略**：用于生成经验样本的策略；
- **目标策略**：不断更新以逐步收敛到最优策略的策略。

当行为策略与目标策略相同时，这种学习过程被称为 **在线策略学习**；反之，当两者不同时，学习过程被称为 **离线策略学习**。

离线策略学习的优势在于，它可以基于其他策略生成的经验样本学习最优策略 —— 例如，这些样本可能来自人类操作者执行的策略。一个重要的应用场景是：行为策略可被选为具有强探索性的策略。例如，若要估计所有状态-动作对的动作值，必须生成足够多的回合，确保每个状态-动作对都被充分访问。尽管 Sarsa 算法会采用 $\epsilon$-贪婪策略来维持一定的探索能力，但 $\epsilon$ 值通常较小，导致探索能力有限。相比之下，若我们能使用探索能力更强的策略生成回合，再通过离线策略学习来优化策略，**学习效率将显著提升**。

- <span style={{color: "red"}}>**如何判断算法属于在线策略还是离线策略？**</span>
可从两个维度判断：
1. 算法旨在求解的数学问题；
2. 算法所需的经验样本形式。

**1. Sarsa 算法属于在线策略学习**

原因如下：Sarsa 算法的每次迭代包含两个步骤：
- **第一步**：通过求解某一策略 $\pi$ 的贝尔曼方程，对该策略进行评估。要实现这一步，需要策略 $\pi$ 生成的样本，因此 $\pi$ 是行为策略；
- **第二步**：基于策略 $\pi$ 的估计值，得到一个改进后的策略。因此，$\pi$ 同时也是目标策略 —— 它会不断更新，最终收敛到最优策略。

综上，Sarsa 算法的行为策略与目标策略完全相同，故属于在线策略学习。

从 "算法所需样本" 的角度也可验证：Sarsa 算法每次迭代需要的样本为 $(s_t, a_t, r_{t+1}, s_{t+1}, a_{t+1})$，其生成过程可表示为：

$$s_t \xrightarrow{\pi_b} a_t \xrightarrow{\text{模型（model）}} r_{t+1}, s_{t+1} \xrightarrow{\pi_b} a_{t+1}$$

可见，行为策略 $\pi_b$ 负责在状态 $s_t$ 生成动作 $a_t$，在状态 $s_{t+1}$ 生成动作 $a_{t+1}$。Sarsa 算法的目标是估计某一策略 $\pi_T$ 下 $(s_t, a_t)$ 的动作值，而 $\pi_T$ 会基于每次迭代的估计值进行改进，因此是目标策略。实际上，$\pi_T$ 与 $\pi_b$ 完全相同 —— 因为对 $\pi_T$ 的评估依赖于样本 $(r_{t+1}, s_{t+1}, a_{t+1})$，而 $a_{t+1}$ 正是由 $\pi_b$ 生成的。换句话说，**Sarsa 算法评估的策略，与生成样本的策略是同一个**。

**2. Q 学习算法属于离线策略学习**

根本原因在于：Q 学习是用于求解贝尔曼最优方程的算法，而 Sarsa 算法是用于求解给定策略的贝尔曼方程的算法。求解贝尔曼方程仅能评估对应的策略，而求解贝尔曼最优方程可直接得到最优值和最优策略。

具体来看 Q 学习所需的样本：Q 学习每次迭代需要的样本为 $(s_t, a_t, r_{t+1}, s_{t+1})$，其生成过程可表示为：

$$s_t \xrightarrow{\pi_b} a_t \xrightarrow{\text{模型（model）}} r_{t+1}, s_{t+1}$$

可见，行为策略 $\pi_b$ 仅负责在状态 $s_t$ 生成动作 $a_t$。Q 学习的目标是估计 $(s_t, a_t)$ 的最优动作值，这一估计过程仅依赖样本 $(r_{t+1}, s_{t+1})$；而 $(r_{t+1}, s_{t+1})$ 的生成不涉及 $\pi_b$—— 它由系统模型（或智能体与环境的交互）决定。因此，对 $(s_t, a_t)$ 最优动作值的估计与 $\pi_b$ 无关，我们可使用任意行为策略在 $s_t$ 生成动作 $a_t$。此外，此处的目标策略 $\pi_T$ 是基于估计的最优值得到的贪婪策略（见算法 7.3），行为策略无需与目标策略相同。

**3. 蒙特卡洛（MC）学习属于在线策略学习**

原因与 Sarsa 算法类似：待评估和改进的目标策略，与生成样本的行为策略是同一个。

**易混淆概念：在线学习（Online Learning）与离线学习（Offline Learning）**

"在线策略 / 离线策略" 常与 "在线学习 / 离线学习" 混淆，二者的区别如下：

- **在线学习**：智能体在与环境交互的过程中，同步更新价值和策略；
- **离线学习**：智能体不与环境交互，仅使用预先收集的经验数据更新价值和策略。

两者的关联的是：若算法属于在线策略学习，则仅能以在线方式实现，无法使用其他策略预先收集的数据；若算法属于离线策略学习，则既可在线实现（边交互边学习），也可离线实现（用预收集数据学习）。

由于 Q 学习属于离线策略算法，因此它既可以采用在线策略方式实现，也可以采用离线策略方式实现。

**Q 学习的在线策略版本**如算法 7.2 所示。该实现方式与算法 7.1 中 Sarsa 算法的实现方式类似：此处的行为策略与目标策略完全相同，均为 $\epsilon$-贪婪策略。

**Q 学习的离线策略版本**如算法 7.3 所示。行为策略 $\pi_b$ 可以是任意策略，只要它能生成足够的经验样本即可；通常当 $\pi_b$ 具有探索性时，算法表现更为有利。此处的目标策略 $\pi_T$ 为贪婪策略（而非 $\epsilon$-贪婪策略），原因是该目标策略无需用于生成样本，因此不需要具备探索性。此外，本节介绍的 Q 学习离线策略版本采用离线方式实现：先收集所有经验样本，再对其进行处理。
#### Algorithm 7.2: Optimal policy learning via Q-learning (on-policy version)

- **Initialization**: $\alpha_t(s, a) = \alpha > 0$ for all $(s, a)$ and all $t$. $\epsilon \in (0, 1)$. Initial $q_0(s, a)$ for all $(s, a)$. Initial $\epsilon$-greedy policy $\pi_0$ derived from $q_0$.
- **Goal**: Learn an optimal path that can lead the agent to the target state from an initial state $s_0$.
- **For each episode, do**:
  - If $s_t$ ($t = 0, 1, 2, \dots$) is not the target state, do:
    - Collect the experience sample $(a_t, r_{t+1}, s_{t+1})$ given $s_t$: generate $a_t$ following $\pi_t(s_t)$; generate $r_{t+1}, s_{t+1}$ by interacting with the environment.
    - Update q-value for $(s_t, a_t)$:
      $$q_{t+1}(s_t, a_t) = q_t(s_t, a_t) - \alpha_t(s_t, a_t)\left[ q_t(s_t, a_t) - (r_{t+1} + \gamma \max_a q_t(s_{t+1}, a)) \right]$$
    - Update policy for $s_t$:
      $$\pi_{t+1}(a|s_t) = \begin{cases} 1 - \epsilon + \frac{\epsilon}{|A(s_t)|} & \text{if } a = \arg\max_a q_{t+1}(s_t, a) \\ \frac{\epsilon}{|A(s_t)|} & \text{otherwise} \end{cases}$$



#### Algorithm 7.3: Optimal policy learning via Q-learning (off-policy version)

- **Initialization**: Initial guess $q_0(s, a)$ for all $(s, a)$. Behavior policy $\pi_b(a|s)$ for all $(s, a)$. $\alpha_t(s, a) = \alpha > 0$ for all $(s, a)$ and all $t$.
- **Goal**: Learn an optimal target policy $\pi_T$ for all states from the experience samples generated by $\pi_b$.
- **For each episode** $\{s_0, a_0, r_1, s_1, a_1, r_2, \dots\}$ generated by $\pi_b$, do:
  - For each step $t = 0, 1, 2, \dots$ of the episode, do:
    - Update q-value for $(s_t, a_t)$:
      $$q_{t+1}(s_t, a_t) = q_t(s_t, a_t) - \alpha_t(s_t, a_t)\left[ q_t(s_t, a_t) - (r_{t+1} + \gamma \max_a q_t(s_{t+1}, a)) \right]$$
    - Update target policy for $s_t$:
      $$\pi_{T,t+1}(a|s_t) = \begin{cases} 1 & \text{if } a = \arg\max_a q_{t+1}(s_t, a) \\ 0 & \text{otherwise} \end{cases}$$



<div style={{textAlign: 'center'}}>

![Q 学习在线策略版本仿真结果](/img/rl/f7-4.png)

</div>

如上，左图展示了算法最终学到的策略；右图分别展示了每个回合的总回报和回合长度。所有回合均从左上角的初始状态开始，到达目标状态后终止。任务目标是寻找从初始状态到目标状态的最优路径。回报设置：目标状态回报 $r_{\text{target}} = 0$，禁止状态回报 $r_{\text{forbidden}}$ 与边界状态回报 $r_{\text{boundary}}$ 均为 $-10$，其他状态回报 $r_{\text{other}} = -1$；学习率 $\alpha = 0.1$，探索率 $\epsilon = 0.1$。

下面通过示例来演示 Q 学习的效果。

**第一个示例**如上图所示，用于演示在线策略 Q 学习。该示例的目标是寻找从初始状态到目标状态的最优路径，具体设置详见图注。从结果可以看出，**Q 学习最终能够找到最优路径**；在学习过程中，每个回合的长度逐渐缩短，而每个回合的总回报则逐渐增加。

**第二个系列示例**如图 7.5 和图 7.6 所示，用于演示离线策略 Q 学习。该示例的目标是为所有状态寻找最优策略，具体参数设置如下：边界状态回报 $r_{\text{boundary}}$ 与禁止状态回报 $r_{\text{forbidden}}$ 均为 $-1$，目标状态回报 $r_{\text{target}} = 1$；折扣率 $\gamma=0.9$；学习率 $\alpha=0.1$。

- **真值（Ground Truth）**：为验证 Q 学习的有效性，我们首先需要明确最优策略和最优状态值的真值。此处的真值通过基于模型的策略迭代算法获得，具体结果如图 7.5 (a) 和图 7.5 (b) 所示。

- **经验样本**：行为策略采用均匀分布策略 —— 在任意状态下选择任意动作的概率均为 0.2（见图 7.5 (c)）。基于该策略生成一个包含 10 万步的回合（见图 7.5 (d)）。由于该行为策略具有良好的探索能力，该回合会多次访问所有状态-动作对。

- **学习结果**：基于行为策略生成的回合，Q 学习最终学到的目标策略如图 7.5 (e) 所示。该策略为最优策略，理由是如图 7.5 (f) 所示，估计的状态值误差（均方根误差）最终收敛到零。此外，不难发现，学到的最优策略与图 7.5 (a) 中的真值策略并非完全一致 —— 实际上，**存在多个具有相同最优状态值的最优策略**。

- **不同初始值的影响**：由于 Q 学习具有自举特性，算法性能会依赖于动作值的初始猜测。如图 7.5 (g) 所示，当初始猜测值接近真值时，估计结果在约 1 万步内即可收敛；若初始猜测值与真值偏差较大，则需要更多步数才能收敛（见图 7.5 (h)）。尽管如此，这些结果仍表明，**即使初始值不够准确，Q 学习仍能快速收敛**。

- **不同行为策略的影响**：当行为策略缺乏探索性时，学习性能会显著下降。以图 7.6 中的行为策略为例：这些策略均为 $\epsilon$-贪婪策略，且 $\epsilon$ 值分别为 0.5 和 0.1（图 7.5 (c) 中的均匀策略可视为 $\epsilon=1$ 的 $\epsilon$-贪婪策略）。结果显示，当 $\epsilon$ 值从 1 降至 0.5、再进一步降至 0.1 时，**学习速度显著下降** —— 这是因为策略的探索能力减弱，导致经验样本不足。

<div style={{textAlign: 'center'}}>

![Q 学习离线策略版本仿真结果（一）](/img/rl/f7-5.png)

</div>

<div style={{textAlign: 'center'}}>

![Q 学习离线策略版本仿真结果（二）](/img/rl/f7-6.png)

</div>
## A unified viewpoint

到目前为止，我们已经介绍了多种时序差分（TD）算法，如 Sarsa 算法、n 步 Sarsa 算法以及 Q 学习算法。本节将介绍一个统一框架，以涵盖所有这些算法与蒙特卡洛（MC）学习。

具体而言，（用于动作值估计的）时序差分（TD）算法可表示为如下统一形式：

$$
\begin{aligned}
q_{t+1}(s_t, a_t) = q_t(s_t, a_t) - \alpha_t(s_t, a_t)\left[ q_t(s_t, a_t) - \bar{q}_t \right] \tag{7.20}
\end{aligned}
$$

式中，$\bar{q}_t$ 为时序差分（TD）目标。不同 TD 算法的 $\bar{q}_t$ 表达式不同，具体汇总见表 7.2。

| 算法 | 式 (7.20) 中 TD 目标 $\bar{q}_t$ 的表达式 | 算法待求解的方程 |
|------|------------------------------------------|----------------|
| **Sarsa 算法** | $\bar{q}_t = r_{t+1} + \gamma q_t(s_{t+1}, a_{t+1})$ | BE：$q_\pi(s, a) = \mathbb{E}\left[ R_{t+1} + \gamma q_\pi(S_{t+1}, A_{t+1}) \mid S_t = s, A_t = a \right]$ |
| **n 步 Sarsa 算法** | $\bar{q}_t = r_{t+1} + \gamma r_{t+2} + \cdots + \gamma^n q_t(s_{t+n}, a_{t+n})$ | BE：$q_\pi(s, a) = \mathbb{E}\left[ R_{t+1} + \gamma R_{t+2} + \cdots + \gamma^n q_\pi(S_{t+n}, A_{t+n}) \mid S_t = s, A_t = a \right]$ |
| **Q 学习算法** | $\bar{q}_t = r_{t+1} + \gamma \max_a q_t(s_{t+1}, a)$ | BOE：$q(s, a) = \mathbb{E}\left[ R_{t+1} + \gamma \max_a q(S_{t+1}, a) \mid S_t = s, A_t = a \right]$ |
| **蒙特卡洛学习** | $\bar{q}_t = r_{t+1} + \gamma r_{t+2} + \gamma^2 r_{t+3} + \dots$ | BE：$q_\pi(s, a) = \mathbb{E}\left[ R_{t+1} + \gamma R_{t+2} + \gamma^2 R_{t+3} + \dots \mid S_t = s, A_t = a \right]$ |

**表 7.2**：时序差分（TD）算法的统一视角。其中，BE 代表贝尔曼方程（Bellman Equation），BOE 代表贝尔曼最优方程（Bellman Optimality Equation）。

蒙特卡洛（MC）学习可视为式 (7.20) 的一种特殊情况：只需令 $\alpha_t(s_t, a_t) = 1$，式 (7.20) 即可简化为 $q_{t+1}(s_t, a_t) = \bar{q}_t$。

式 (7.20) 所示算法可视为用于求解如下统一方程的随机近似算法：

$$q(s, a) = \mathbb{E}\left[ \bar{q}_t \mid s, a \right]$$

随着 $\bar{q}_t$ 表达式的不同，该统一方程也会呈现出不同形式，具体汇总见表 7.2。可见，**除 Q 学习算法以求解贝尔曼最优方程为目标外，其余所有算法均以求解贝尔曼方程为目标**。

## Summary

本章介绍了强化学习中的一类重要算法 —— **时序差分（TD）学习算法**。我们具体介绍的算法包括 Sarsa 算法、n 步 Sarsa 算法和 Q 学习算法。所有这些算法均可视为用于求解贝尔曼方程或贝尔曼最优方程的随机近似算法。

TD 之所以叫 TD，这来自这些算法的 TD 误差，该误差表示新样本与当前估计值之间的差异。由于这种差异是在不同时间步之间计算得出的，因此被称为 “时序差分（temporal-difference）”，这也是 “TD” 的由来。而 “Learning” 本质上就是 “Estimating”：即通过样本估计状态值或动作值，再基于估计得到的价值确定策略。

本章介绍的 TD 算法中，除 Q 学习外，其余算法均用于**评估给定策略**：即通过经验样本估计给定策略的状态值或动作值。将这些算法与策略改进步骤相结合，即可用于学习最优策略。此外，这些算法均属于**在线策略算法**：目标策略会作为行为策略，用于生成经验样本。

Q 学习与其他 TD 算法相比稍显特殊，因为它属于**离线策略算法** —— 在 Q 学习中，目标策略可与行为策略不同。Q 学习之所以是离线策略算法，根本原因在于：**它以求解贝尔曼最优方程为目标，而非求解给定策略的贝尔曼方程**。

值得一提的是，存在一些方法可将在线策略算法转换为离线策略算法，**重要性采样（Importance Sampling）** 便是其中一种广泛应用的方法，我们将在第 10 章对其进行介绍。最后，本章介绍的 TD 算法还存在一些变体与扩展形式。例如，**TD ($\lambda$) 方法**为时序差分学习提供了更具一般性的统一框架。
