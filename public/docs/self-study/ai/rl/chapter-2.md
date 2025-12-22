---
id: rl-chapter-2
title: 第2章 贝尔曼公式
sidebar_label: 第2章
---

## 2、Bellman Equation

来来来看看这是什么Value？State Value！

有了State Value，我们才能量化评估"遵循某一策略时，从某状态出发的长期收益期望"。

### 2.1 Significance of Return

![Policy Comparison](/img/rl/f2-2.png)

左政策使 $s_1$ 直接避开禁止区域，中政策使 $s_1$ 必然进入禁止区域，右政策使 $s_1$ 有 50% 概率进入禁止区域。

回报等于轨迹上所有奖励的折扣和。从直觉出发，当然是左政策最优、中政策最差对吧？但需通过数学化的回报验证：
- 左政策轨迹：$s_1 \to s_3 \to s_4 \to s_4 \cdots$，折扣回报为 $return_1 = 0 + \gamma \cdot 1 + \gamma^2 \cdot 1 + \cdots = \frac{\gamma}{1-\gamma}$
- 中政策轨迹：$s_1 \to s_2 \to s_4 \to s_4 \cdots$，因进入禁止区域获即时负奖励 $-1$，折扣回报为 $return_2 = -1 + \frac{\gamma}{1-\gamma}$；
- 右政策（随机）：两种轨迹各占 50% 概率，平均回报（期望）为 $return_3 = 0.5 \times return_2 + 0.5 \times return_1 = -0.5 + \frac{\gamma}{1-\gamma}$

对比可知，对任意 $\gamma$ 均满足 $return_1 > return_3 > return_2$，数学结论与直觉完全一致。

### 2.2 Calculate Return
（1）Discounted sum of all rewards

![Return Calculation](/img/rl/f2-3.png)

设 $v_i$ 为从 $s_i$ 出发的回报，则：

$$
\begin{aligned}
v_1 &= r_1 + \gamma r_2 + \gamma^2 r_3 + \cdots, \\
v_2 &= r_2 + \gamma r_3 + \gamma^2 r_4 + \cdots, \\
v_3 &= r_3 + \gamma r_4 + \gamma^2 r_1 + \cdots, \\
v_4 &= r_4 + \gamma r_1 + \gamma^2 r_2 + \cdots.
\end{aligned}
$$

（2）Bootstrapping based

观察上述表达式可发现，某状态的回报可拆分为 "即时奖励" 与 "未来状态回报的折扣"。例如 $v_1 = r_1 + \gamma (r_2 + \gamma r_3 + \cdots) = r_1 + \gamma v_2$，同理可得：

$$v_1 = r_1 + \gamma v_2, \quad v_2 = r_2 + \gamma v_3, \quad v_3 = r_3 + \gamma v_4, \quad v_4 = r_4 + \gamma v_1$$

这种 "用其他未知量表示当前未知量" 的思想即**自举（Bootstrapping）**，看似是 "循环依赖"，实则可转化为线性方程组求解：

将上述方程组写成矩阵形式：

$$\begin{bmatrix} v_1 \\ v_2 \\ v_3 \\ v_4 \end{bmatrix} = \begin{bmatrix} r_1 \\ r_2 \\ r_3 \\ r_4 \end{bmatrix} + \gamma \begin{bmatrix} 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 1 \\ 1 & 0 & 0 & 0 \end{bmatrix} \begin{bmatrix} v_1 \\ v_2 \\ v_3 \\ v_4 \end{bmatrix}$$

记 $\mathbf{v} = \begin{bmatrix} v_1 \\ v_2 \\ v_3 \\ v_4 \end{bmatrix}$，$\mathbf{r} = \begin{bmatrix} r_1 \\ r_2 \\ r_3 \\ r_4 \end{bmatrix}$，$P = \begin{bmatrix} 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 1 \\ 1 & 0 & 0 & 0 \end{bmatrix}$，则上式可简写为：

$$\mathbf{v} = \mathbf{r} + \gamma P \mathbf{v}$$

其中转移矩阵 $P$ 表示状态转移概率。进一步简化为：
$$v = r + \gamma P v$$

1. 移项得到：$v - \gamma P v = r$
2. 提取公因子：$(I - \gamma P) v = r$（其中 $I$ 为单位矩阵）
3. 两边同时左乘逆矩阵：$v = (I - \gamma P)^{-1} r$

这就是大名鼎鼎的**贝尔曼方程**的雏形！

总结一下，计算回报有两个关键思路：
- **直接加**：把每一步的奖励按时间打折后加起来（比如现在拿 10 分，下一步拿 10 分，折扣 0.9，总回报就是 10 + 10×0.9 + 10×0.9² + ...）；
- **互相借力（自举）**：比如从状态 A 出发的回报 = 状态 A 的即时奖励 + 折扣 × 从状态 B 出发的回报（因为 A 下一步会到 B）。
这就像 “想知道 A 的价值，先看看 B 的价值”，虽然绕，但能简化计算。

### 2.3 State Value

State Value（状态价值）是 Return 的 "平均版"—— 因为很多时候，从同一个状态出发可能有不同结果（比如随机选动作），没法确定一个固定回报。

**直观理解**：
从状态 $s$ 出发，一半概率拿到 10 分回报，一半概率拿到 20 分回报，那 $s$ 的状态价值就是 $(10+20) \div 2 = 15$ 分。

**重要性质**：
- 它只和 "状态" 和 "策略" 有关：同一个状态，用不同策略（比如选动作的规则），价值可能不一样；
- 但和 "什么时候到这个状态" 无关（今天来和明天来，价值相同）。

**数学定义**：
$$v_{\pi}(s) \doteq \mathbb{E}\left[G_{t} \mid S_{t}=s\right]$$

这个定义告诉我们：
- $v_{\pi}(s)$ 依赖于状态 $s$：定义中以 "从状态 $s$ 出发" 为条件；
- $v_{\pi}(s)$ 依赖于策略 $\pi$：轨迹由策略 $\pi$ 生成，不同策略对应不同状态价值；
- $v_{\pi}(s)$ 与时间步 $t$ 无关：状态价值由策略决定，与当前时刻无关。

### 2.4 Bellman Equation

贝尔曼方程就是把 State Value 和 Bootstrapping 结合起来的简单规则，本质就一句话：

**一个状态的价值 = 现在能拿到的平均奖励 + 未来能拿到的平均价值（打折扣）**

**拆成两步理解**：
1. **现在的奖励**：在这个状态选动作，能立刻拿到的平均分数（比如选动作 $a_1$ 拿 5 分，选动作 $a_2$ 拿 3 分，策略里 $a_1$ 选 80%、$a_2$ 选 20%，平均就是 $5 \times 0.8 + 3 \times 0.2 = 4.6$ 分）；
2. **未来的价值**：选完动作会转到下一个状态，下一个状态的价值乘以折扣（比如下一个状态价值 10 分，折扣 $\gamma = 0.9$，就是 $10 \times 0.9 = 9$ 分）；
3. **加起来就是当前状态的价值**：$4.6 + 9 = 13.6$ 分。

整个逻辑串起来：想算状态价值，不用硬加所有未来奖励，只要知道 "现在能拿多少" 和 "下一步状态值多少"，用贝尔曼方程就能算。

#### 数学推导过程

**第一步：将回报 $G_t$ 进行分解**

我们知道回报的定义是：
$$G_t = R_{t+1} + \gamma R_{t+2} + \gamma^2 R_{t+3} + \cdots$$

可以将它分解为：
$$
\begin{aligned}
G_{t} &= R_{t+1} + \gamma R_{t+2} + \gamma^{2} R_{t+3} + \cdots \\
&= R_{t+1} + \gamma \left(R_{t+2} + \gamma R_{t+3} + \cdots\right) \\
&= R_{t+1} + \gamma G_{t+1}
\end{aligned}
$$

**为什么要这样分解？** 因为我们想把 "从 $t$ 时刻开始的回报" 拆成 "$t+1$ 时刻的即时奖励" 和 "从 $t+1$ 时刻开始的未来回报"。这样就能用自举的思想：用 $G_{t+1}$ 来表示 $G_t$。

**第二步：对两边取条件期望**

条件期望 $\mathbb{E}[X \mid Y=y]$ 的含义是：在已知 $Y=y$ 的条件下，随机变量 $X$ 的平均值。比如 "在状态 $s$ 的条件下，回报 $G_t$ 的期望值"。

对第一步的等式两边取条件期望（以 $S_t=s$ 为条件）：
$$
\begin{aligned}
v_{\pi}(s) &= \mathbb{E}\left[G_{t} \mid S_{t}=s\right] \\
&= \mathbb{E}\left[R_{t+1}+\gamma G_{t+1} \mid S_{t}=s\right] \\
&= \mathbb{E}\left[R_{t+1} \mid S_{t}=s\right]+\gamma \mathbb{E}\left[G_{t+1} \mid S_{t}=s\right] \quad (2.4)
\end{aligned}
$$

**为什么期望可以拆开？** 因为期望的线性性质：$\mathbb{E}[X+Y] = \mathbb{E}[X] + \mathbb{E}[Y]$，即使有条件也成立。

现在我们需要分别计算这两项：$\mathbb{E}\left[R_{t+1} \mid S_{t}=s\right]$ 和 $\mathbb{E}\left[G_{t+1} \mid S_{t}=s\right]$。

**第三步：计算 "现在能拿到的平均奖励"**

$$
\begin{aligned}
\mathbb{E}\left[R_{t+1} \mid S_{t}=s\right] &= \sum_{a \in \mathcal{A}} \pi(a \mid s) \mathbb{E}\left[R_{t+1} \mid S_{t}=s, A_{t}=a\right] \\
&= \sum_{a \in \mathcal{A}} \pi(a \mid s) \sum_{r \in \mathcal{R}} p(r \mid s, a) r \quad (2.5)
\end{aligned}
$$

**这一步在做什么？**

1. **第一行**：我们想算 "在状态 $s$ 下，能拿到多少平均奖励"。但奖励不仅依赖状态，还依赖动作。所以我们要考虑所有可能的动作 $a$，每个动作按策略 $\pi(a\mid s)$ 的概率被选中，然后计算 "在状态 $s$ 且选动作 $a$ 的条件下，能拿到多少平均奖励"。

2. **第二行**：进一步，"在状态 $s$ 且选动作 $a$ 的条件下，能拿到多少平均奖励" 就是所有可能的奖励值 $r$，按概率 $p(r\mid s,a)$ 加权平均，即 $\sum_{r \in \mathcal{R}} p(r \mid s, a) r$。

**举个例子**：假设在状态 $s$，策略是：80% 选动作 $a_1$（能拿 5 分），20% 选动作 $a_2$（能拿 3 分）。那么平均奖励 = $0.8 \times 5 + 0.2 \times 3 = 4.6$ 分。

**第四步：计算 "未来能拿到的平均价值"**

利用马尔可夫性（未来回报仅依赖当前状态，与历史无关），可得：
$$
\begin{aligned}
\mathbb{E}\left[G_{t+1} \mid S_{t}=s\right] &= \sum_{s' \in \mathcal{S}} \mathbb{E}\left[G_{t+1} \mid S_{t+1}=s'\right] p\left(s' \mid s\right) \\
&= \sum_{s' \in \mathcal{S}} v_{\pi}\left(s'\right) \sum_{a \in \mathcal{A}} p\left(s' \mid s, a\right) \pi(a \mid s) \quad (2.6)
\end{aligned}
$$

**这一步在做什么？**

1. **第一行**：我们想算 "在状态 $s$ 下，未来能拿到多少平均价值"。但未来价值取决于下一步会到哪个状态 $s'$。所以我们要考虑所有可能的下一个状态 $s'$，按转移概率 $p(s'\mid s)$ 加权，然后计算 "在状态 $s'$ 的条件下，能拿到多少未来价值"。

2. **关键点**：$\mathbb{E}\left[G_{t+1} \mid S_{t+1}=s'\right]$ 就是状态价值 $v_{\pi}(s')$ 的定义！因为 $G_{t+1}$ 就是从 $t+1$ 时刻开始的回报，在状态 $s'$ 的条件下，它的期望就是 $v_{\pi}(s')$。

3. **第二行**：转移概率 $p(s'\mid s)$ 需要进一步分解。因为转移不仅依赖状态，还依赖动作。所以 $p(s'\mid s) = \sum_{a \in \mathcal{A}} p(s'\mid s,a) \pi(a\mid s)$，即所有可能的动作 $a$，按策略 $\pi(a\mid s)$ 的概率被选中，然后计算在动作 $a$ 下从 $s$ 转移到 $s'$ 的概率。

**举个例子**：假设在状态 $s$，下一步可能到 $s_1'$（概率 0.6，价值 10 分）或 $s_2'$（概率 0.4，价值 8 分）。那么未来平均价值 = $0.6 \times 10 + 0.4 \times 8 = 9.2$ 分。

**第五步：得到贝尔曼方程的最终形式**

将式 (2.5) 和 (2.6) 代入式 (2.4)，得到：
$$
\begin{aligned}
v_{\pi}(s) &= \sum_{a \in \mathcal{A}} \pi(a \mid s)\left[\sum_{r \in \mathcal{R}} p(r \mid s, a) r+\gamma \sum_{s' \in \mathcal{S}} p\left(s' \mid s, a\right) v_{\pi}\left(s'\right)\right], \\
&\forall s \in \mathcal{S} \quad (2.7)
\end{aligned}
$$

**这个公式的直观理解**：
- 外层求和：对所有可能的动作 $a$ 求和，按策略 $\pi(a\mid s)$ 加权；
- 内层第一项：选动作 $a$ 后能拿到的平均即时奖励；
- 内层第二项：选动作 $a$ 后，会转移到某个状态 $s'$，$s'$ 的价值乘以折扣 $\gamma$，再对所有可能的 $s'$ 按概率加权平均。

**关键说明**：
- 贝尔曼方程是 "方程组"：针对所有状态 $s \in \mathcal{S}$ 建立方程，联合求解所有状态价值；
- 包含已知量和未知量：
  - **已知量**：策略 $\pi(a\mid s)$、系统模型 $p(r\mid s,a)$ 和 $p(s'\mid s,a)$；
  - **未知量**：所有状态价值 $v_{\pi}(s)$；
- **核心意义**：状态价值由 "即时奖励的期望" 和 "未来状态价值的折扣期望" 组成。

**等价形式**：

结合全概率公式 $p(s'\mid s,a)=\sum_{r \in \mathcal{R}} p(s',r\mid s,a)$，可改写为：
$$v_{\pi}(s)=\sum_{a \in \mathcal{A}} \pi(a \mid s) \sum_{s' \in \mathcal{S}} \sum_{r \in \mathcal{R}} p\left(s', r \mid s, a\right)\left[r+\gamma v_{\pi}\left(s'\right)\right]$$

若奖励仅依赖下一状态（$r=r(s')$），则 $p(r(s')\mid s,a)=p(s'\mid s,a)$，代入得：
$$v_{\pi}(s)=\sum_{a \in \mathcal{A}} \pi(a \mid s) \sum_{s' \in \mathcal{S}} p\left(s' \mid s, a\right)\left[r(s')+\gamma v_{\pi}\left(s'\right)\right]$$

#### 矩阵与向量形式

可将所有状态的方程整合为矩阵 - 向量形式，便于分析和求解。

定义：

- **状态价值向量**：$v_{\pi} = [v_{\pi}(s_1), v_{\pi}(s_2), \cdots, v_{\pi}(s_n)]^T \in \mathbb{R}^n$（$n=|\mathcal{S}|$为状态数）
- **即时奖励均值向量**：$r_{\pi} = [r_{\pi}(s_1), r_{\pi}(s_2), \cdots, r_{\pi}(s_n)]^T$，其中$r_{\pi}(s) = \sum_{a \in \mathcal{A}} \pi(a|s) \sum_{r \in \mathcal{R}} p(r|s,a) r$
- **转移概率矩阵**：$P_{\pi} \in \mathbb{R}^{n \times n}$，其中$[P_{\pi}]_{ij} = p_{\pi}(s_j|s_i) = \sum_{a \in \mathcal{A}} \pi(a|s_i) p(s_j|s_i,a)$（策略$\pi$下从$s_i$转移到$s_j$的概率）

矩阵 - 向量形式：

$$v_{\pi} = r_{\pi} + \gamma P_{\pi} v_{\pi}$$

#### 求解贝尔曼方程的State Value

由矩阵 - 向量形式$v_{\pi} = r_{\pi} + \gamma P_{\pi} v_{\pi}$，整理得闭式解：

$$v_{\pi} = \left(I - \gamma P_{\pi}\right)^{-1} r_{\pi}$$

当然这个逆太难顶了，所以一般不这么做，而是迭代解：

$$v_{k+1} = r_{\pi} + \gamma P_{\pi} v_k, \quad k=0,1,2,\cdots \quad (2.11)$$

其中$v_0$是初始猜测值。

**收敛性**：当$k \to \infty$时，$v_k$收敛到闭式解：$v_k \to v_{\pi} = \left(I - \gamma P_{\pi}\right)^{-1} r_{\pi}$。

**收敛性证明（简要）**：定义误差$\delta_k = v_k - v_{\pi}$，代入迭代式得$\delta_{k+1} = \gamma P_{\pi} \delta_k$。由于$\gamma < 1$且$P_{\pi}$元素非负且不大于 1，故$\delta_k \to 0$，迭代收敛。

### 2.5 Action Value

状态 - 动作对$(s,a)$的动作价值，记为$q_{\pi}(s,a)$，定义为：

$$q_{\pi}(s,a) \doteq \mathbb{E}\left[G_t | S_t=s, A_t=a\right]$$

即 "在状态s采取动作a后，遵循策略$\pi$获得的期望回报"。

**状态价值与动作价值的关系**：

状态价值是动作价值的期望（按策略概率加权）：

$$v_{\pi}(s) = \sum_{a \in \mathcal{A}} \pi(a|s) q_{\pi}(s,a) \quad (2.13)$$

动作价值依赖即时奖励和未来状态价值：对比式 (2.13) 与贝尔曼方程（式 2.7），可得：

$$q_{\pi}(s,a) = \sum_{r \in \mathcal{R}} p(r|s,a) r + \gamma \sum_{s' \in \mathcal{S}} p(s'|s,a) v_{\pi}(s') \quad (2.14)$$

#### 基于动作价值的贝尔曼方程

将式 (2.13) 代入式 (2.14)，得到动作价值的贝尔曼方程：

$$q_{\pi}(s,a) = \sum_{r \in \mathcal{R}} p(r|s,a) r + \gamma \sum_{s' \in \mathcal{S}} p(s'|s,a) \sum_{a' \in \mathcal{A}(s')} \pi(a'|s') q_{\pi}(s',a')$$

**矩阵 - 向量形式**：

$$q_{\pi} = \tilde{r} + \gamma P \Pi q_{\pi} \quad (2.15)$$

其中：
- $q_{\pi}$：动作价值向量（索引为状态 - 动作对）；
- $\tilde{r}$：即时奖励向量（$[\tilde{r}]_{(s,a)} = \sum_{r \in \mathcal{R}} p(r|s,a) r$）；
- $P$：转移概率矩阵（$[P]_{(s,a),s'} = p(s'|s,a)$）；
- $\Pi$：块对角矩阵（$\Pi_{(s',a')} = \pi(a'|s')$，其余元素为 0）。

**特点**：$\tilde{r}$和$P$仅由系统模型决定，与策略无关；策略嵌入在$\Pi$中。该方程是压缩映射，存在唯一解，可通过迭代求解。

### 2.6 Summary

#### 一、State Value（状态价值） vs. Action Value（动作价值）

想象你在玩一款 "迷宫寻宝游戏"：

**State Value（状态价值）** $v_\pi(s)$：你现在在迷宫的某个路口（状态s），按照策略$\pi$（比如 "50% 概率走左路，50% 概率走右路" 的选路规则）行动，最终能拿到的 "平均宝藏总和"（把未来找到的宝藏按 "时间折扣" 加起来的平均值）。它回答的是："这个路口本身有多'值钱'？"

**Action Value（动作价值）** $q_\pi(s,a)$：你现在在迷宫的某个路口（状态s），先选一个具体动作a（比如 "走左路"），之后再按照策略$\pi$行动，最终能拿到的 "平均宝藏总和"。它回答的是："在这个路口选这个动作有多'值钱'？"

#### 二、State Value 和 Action Value 的 "互相推导"

它们是 "整体" 和 "部分" 的关系，能通过公式互相计算：

**从 Action Value 算 State Value**：

$$v_\pi(s) = \sum_a \pi(a|s) \, q_\pi(s,a)$$

解释：策略$\pi$会以概率$\pi(a|s)$选每个动作a，所以 "状态s的价值" 就是 "所有动作a的价值$q_\pi(s,a)$按概率加权后的平均值"。

类比：路口有两条路，左路（概率 60%，价值 10）、右路（概率 40%，价值 8），则状态价值 = $0.6×10 + 0.4×8 = 9.2$。

**从 State Value 算 Action Value**：

$$q_\pi(s,a) = \sum_r p(r|s,a)r + \gamma \sum_{s'} p(s'|s,a) v_\pi(s')$$

解释："动作a的价值" 由两部分组成：

1. 选动作a后立刻拿到的平均奖励（比如走左路后立刻捡到 1 个金币）；
2. 选动作a后转移到下一个路口$s'$，下一个路口的价值的折扣平均值（比如下一个路口价值 10，折扣率$\gamma=0.9$，则这部分价值是$0.9×10=9$）。

所以$q_\pi$就是 Action Value。

#### 三、矩阵迷宫里的 Policy 和 Action
![Policy 和 Action 区分](/img/rl/f2-4.png)
图中的四个格子是四个状态（$s_1, s_2, s_3, s_4$），绿色箭头是 **"策略（Policy）选择的动作（Action）"**，两者是 "规则→执行" 的关系，不冲突：

**Policy（策略）**：是 "在每个状态下选什么动作的规则"。比如：
- 状态$s_1$的策略：选 "向右移动" 的动作；
- 状态$s_2$的策略：选 "向下移动" 的动作；
- 状态$s_3$的策略：选 "向右移动" 的动作；
- 状态$s_4$的策略：无（因为是终点，用圆圈标记）。

**Action（动作）**：是策略的具体执行。比如$s_1$的 "向右移动" 就是一个动作，执行后转移到$s_2$；$s_2$的 "向下移动" 是一个动作，执行后转移到$s_4$，以此类推。

#### 实际例子：咖啡屋寻宝游戏

你在一家咖啡屋玩寻宝游戏，咖啡屋有 4 个区域（对应 4 个状态$s_1, s_2, s_3, s_4$），每个区域有不同的 "移动规则" 和 "奖励"：

- **$s_1$（左上角）**：只能向右走，奖励$r=-1$（因为走过去要花 1 分钟，是负奖励）
- **$s_2$（右上角）**：只能向下走，奖励$r=1$（因为能捡到 1 颗糖）
- **$s_3$（左下角）**：只能向右走，奖励$r=1$（因为能捡到 1 颗糖）
- **$s_4$（右下角）**：终点，无动作，奖励$r=1$（因为待在这里每回合都能拿 1 颗糖）

折扣率$\gamma=0.9$（未来的奖励没现在值钱，打 9 折）。

**策略$\pi$**：在每个状态下 "只能选唯一的动作"（比如$s_1$只能选 "向右"，$s_2$只能选 "向下"）。

##### 1. 计算 State Value（状态价值$v_\pi(s)$）

状态价值是 "从该状态出发，按策略行动能拿到的平均奖励总和"。我们逐个计算：

**$v_\pi(s_4)$**：$s_4$是终点，每回合拿 1 颗糖，且一直待在这里。所以回报是：

$$1 + \gamma \times 1 + \gamma^2 \times 1 + \cdots = \frac{1}{1-\gamma} = \frac{1}{1-0.9} = 10$$

即$v_\pi(s_4) = 10$。

**$v_\pi(s_2)$**：$s_2$只能向下走到$s_4$，即时奖励$r=1$，之后$s_4$的价值是 10。所以：

$$v_\pi(s_2) = 1 + \gamma \times v_\pi(s_4) = 1 + 0.9 \times 10 = 10$$

**$v_\pi(s_3)$**：$s_3$只能向右走到$s_4$，即时奖励$r=1$，之后$s_4$的价值是 10。所以：

$$v_\pi(s_3) = 1 + \gamma \times v_\pi(s_4) = 1 + 0.9 \times 10 = 10$$

**$v_\pi(s_1)$**：$s_1$只能向右走到$s_2$，即时奖励$r=-1$（**负奖励！**），之后$s_2$的价值是 10。所以：

$$v_\pi(s_1) = -1 + \gamma \times v_\pi(s_2) = -1 + 0.9 \times 10 = 8$$

**重要观察**：虽然$v_\pi(s_1) = 8$是正数，但明显小于其他状态的价值（都是 10）。这是因为$s_1$的策略导致必须经过一个负奖励（$-1$），降低了整体价值。**如果策略更差，State Value 可能变成负数，这表示该策略非常不好！**

##### 2. 计算 Action Value（动作价值$q_\pi(s,a)$）

动作价值是 "在该状态选该动作后，按策略行动能拿到的平均奖励总和"。我们看每个状态的动作：

- **$q_\pi(s_1, \text{向右})$**：选 "向右" 动作，即时奖励$r=-1$，之后到$s_2$（价值 10）。所以：

  $$q_\pi(s_1, \text{向右}) = -1 + 0.9 \times 10 = 8$$

  （和$v_\pi(s_1)$相等，因为$s_1$只有这一个动作）

- **$q_\pi(s_2, \text{向下})$**：选 "向下" 动作，即时奖励$r=1$，之后到$s_4$（价值 10）。所以：

  $$q_\pi(s_2, \text{向下}) = 1 + 0.9 \times 10 = 10$$

  （和$v_\pi(s_2)$相等，因为$s_2$只有这一个动作）

- **$q_\pi(s_3, \text{向右})$**：选 "向右" 动作，即时奖励$r=1$，之后到$s_4$（价值 10）。所以：

  $$q_\pi(s_3, \text{向右}) = 1 + 0.9 \times 10 = 10$$

  （和$v_\pi(s_3)$相等，因为$s_3$只有这一个动作）

- **$q_\pi(s_4, \text{无动作})$**：终点无动作，即时奖励$r=1$，之后还在$s_4$（价值 10）。所以：

  $$q_\pi(s_4, \text{无动作}) = 1 + 0.9 \times 10 = 10$$

##### 3. 验证贝尔曼方程

贝尔曼方程的核心是 "当前状态价值 = 所有动作的（即时奖励 + 未来状态价值折扣）的加权平均"。以$s_1$为例：

$$
\begin{aligned}
v_\pi(s_1) &= \sum_a \pi(a|s_1) \left[ \sum_r p(r|s_1,a)r + \gamma \sum_{s'} p(s'|s_1,a) v_\pi(s') \right] \\
&= 1 \times \left[ (-1) + 0.9 \times v_\pi(s_2) \right] \\
&= -1 + 0.9 \times 10 = 8
\end{aligned}
$$

（因为$s_1$只有一个动作，$\pi(\text{向右}|s_1)=1$，$p(r=-1|s_1,\text{向右})=1$，$p(s_2|s_1,\text{向右})=1$）

##### 4. 不同策略的影响

**关键点：不同的策略会导致不同的 State Value！**

假设我们改变策略，让$s_1$可以向左走（如果允许的话），但向左走会导致更大的负奖励$r=-5$。那么：

$$v'_\pi(s_1) = -5 + \gamma \times v'_\pi(s_2) = -5 + 0.9 \times 10 = 4$$

可以看到，这个新策略的 State Value（4）比原来的策略（8）**更差**。

**更极端的情况**：如果某个策略导致 State Value 为**负数**，比如：

$$v''_\pi(s_1) = -15 + \gamma \times v''_\pi(s_2) = -15 + 0.9 \times 10 = -6$$

这表示该策略非常差！从$s_1$出发，按这个策略行动，**长期来看会得到负的累积奖励**，说明这个策略不应该被采用。

**总结**：
- **State Value 为正且较大**：策略好，能够获得正收益
- **State Value 为正但较小**：策略一般，收益有限
- **State Value 为负**：策略很差，应该避免使用

#### 四、贝尔曼公式的作用

贝尔曼方程是强化学习的 "核心计算器"，专门用来计算 State Value。它的逻辑很简单：

$$\text{当前状态的价值} = \text{所有动作的「即时奖励 + 未来状态价值的折扣」的加权平均}$$

这也是上述公式的核心 —— 通过不断把 "当前状态" 和 "未来状态" 的价值关联起来，就能算出每个状态到底多 "值钱"。

如果还是觉得抽象，再举个 "点外卖" 的例子：

**State Value**：你现在饿了（状态s），按照 "50% 点美团、50% 点饿了么" 的策略，最终吃到饭的 "满足感总和"（美团满足感 8，饿了么 6，状态价值 = $0.5×8 + 0.5×6 = 7$）。

**Action Value**：你现在饿了（状态s），选 "点美团"（动作a），之后不管选啥，最终满足感的总和（比如点美团后满足感 8，那动作价值$q_\pi(s, \text{美团})=8$）。
