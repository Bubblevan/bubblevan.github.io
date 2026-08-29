---
id: rl-chapter-6
title: 第6章 随机逼近
sidebar_label: 第6章
---



# Stochastic Approximation

> **写在前面**：本章将填补知识空白，介绍随机逼近的基础知识。虽然本章不介绍任何特定的强化学习算法，但它为学习后续章节奠定了必要的基础。

计算样本均值 $\bar{x}$ 有两种方法。

第一种是**非增量方法**：先收集所有样本，再计算平均值。这种方法的缺点是，若样本数量较大，我们可能需要等待很长时间，直到所有样本都收集完毕才能进行计算；

第二种是**增量方法**，它能避免这一缺点 —— 因为该方法会以增量的方式逐步计算平均值。

假设：$w_{k+1} \triangleq \frac{1}{k}\sum_{i=1}^k x_i, \quad k = 1, 2, \dots$

由此可推出：$w_k = \frac{1}{k-1}\sum_{i=1}^{k-1} x_i, \quad k = 2, 3, \dots$

则 $w_{k+1}$ 可表示为关于 $w_k$ 的形式：

$$
\begin{aligned}
w_{k+1} &= \frac{1}{k}\sum_{i=1}^k x_i \\
&= \frac{1}{k}\left( \sum_{i=1}^{k-1} x_i + x_k \right) \\
&= \frac{1}{k}\left[ (k-1)w_k + x_k \right] \\
&= w_k - \frac{1}{k}(w_k - x_k)
\end{aligned}
$$

因此，我们得到如下增量算法：

$$
\begin{aligned}
w_{k+1} = w_k - \frac{1}{k}(w_k - x_k) \tag{6.4}
\end{aligned}
$$

该算法可用于以增量方式计算样本均值 $\bar{x}$。我们可通过以下计算验证其正确性：

$$
\begin{aligned}
w_1 &= x_1, \\
w_2 &= w_1 - \frac{1}{1}(w_1 - x_1) = x_1, \\
w_3 &= w_2 - \frac{1}{2}(w_2 - x_2) = x_1 - \frac{1}{2}(x_1 - x_2) = \frac{1}{2}(x_1 + x_2), \\
w_4 &= w_3 - \frac{1}{3}(w_3 - x_3) = \frac{1}{3}(x_1 + x_2 + x_3), \\
&\vdots \\
w_{k+1} &= \frac{1}{k}\sum_{i=1}^k x_i \tag{6.3}
\end{aligned}
$$


## Robbins-Monro algorithm

<span style={{color: "red"}}>**Robbins-Monro（简称 RM）算法**</span>是一种随机逼近（Stochastic Approximation）算法，与基于梯度等其他多种求根算法相比，随机逼近的优势在于无需知道目标函数的表达式及其导数。

> 著名的**随机梯度下降算法**正是 RM 算法的一种特殊形式。

假设我们需要求解方程的根：$g(w) = 0$

我们只能获得 $g(w)$ 的带噪观测值：$\tilde{g}(w, \eta) = g(w) + \eta$

其中，$\eta \in \mathbb{R}$ 是观测噪声，其分布可为高斯分布，也可为非高斯分布。综上，这是一个**黑箱系统** —— 我们仅知晓输入 $w$ 和带噪输出 $\tilde{g}(w, \eta)$（见图 6.2）。我们的目标是利用 $w$ 和 $\tilde{g}$ 求解方程 $g(w) = 0$。

可用于求解 $g(w) = 0$ 的 RM 算法如下：

$$
\begin{aligned}
w_{k+1} = w_k - a_k \tilde{g}(w_k, \eta_k), \quad k = 1, 2, 3, \dots \tag{6.5}
\end{aligned}
$$

其中，$w_k$ 是第 $k$ 次迭代得到的根的估计值，$\tilde{g}(w_k, \eta_k)$ 是第 $k$ 次带噪观测值，关键参数 $a_k$ 是正系数。可见，RM 算法无需任何关于函数 $g$ 的信息，仅需利用输入和输出即可迭代。

![An illustrative example of the RM algorithm](/img/rl/f6-1.png)

设 $g(w) = w^3 - 5$，该方程的真实根为 $5^{1/3} \approx 1.71$。假设我们仅能观测到输入 $w$ 和输出 $\tilde{g}(w) = g(w) + \eta$（其中 $\eta$ 独立同分布且服从均值为 0、标准差为 1 的标准正态分布），初始猜测值设为 $w_1 = 0$，系数取 $a_k = 1/k$。$w_k$ 的迭代演化过程如上图，尽管观测值受到噪声 $\eta_k$ 的干扰，估计值 $w_k$ 仍能收敛到真实根。

> 选择初始猜测值才能保证收敛！

### Convergence properties

#### Robbins-Monro theorem

在上式所示的 RM 算法中，若满足以下条件：

**（a）梯度条件**：对所有 $w$，有 $0 < c_1 \leq \nabla_w g(w) \leq c_2$（其中 $\nabla_w g(w)$ 表示 $g(w)$ 对 $w$ 的梯度）；

**（b）系数序列条件**：系数序列需满足两个关键条件：第一个条件是 $\sum_{k=1}^{\infty} a_k = \infty$，第二个条件是 $\sum_{k=1}^{\infty} a_k^2 < \infty$；

**（c）噪声条件**：观测噪声 $\eta_k$ 满足 $\mathbb{E}[\eta_k \mid H_k] = 0$ 且 $\mathbb{E}[\eta_k^2 \mid H_k] < \infty$（其中 $H_k = \{w_k, w_{k-1}, \dots\}$ 表示截至第 $k$ 步的历史观测信息集）；

则迭代序列 $w_k$ 会**几乎必然收敛**到满足 $g(w^*) = 0$ 的真实根 $w^*$。

下面对定理中的三个条件进行解释：

**条件（a）**：$0 < c_1 \leq \nabla_w g(w)$ 表明 $g(w)$ 是单调递增函数，这一条件能保证 $g(w) = 0$ 的根存在且唯一。若 $g(w)$ 是单调递减函数，可将 $-g(w)$ 定义为新函数（此时新函数单调递增），仍满足该条件。

实际应用中，若目标是优化函数 $J(w)$，可将优化问题转化为求根问题：令 $g(w) \triangleq \nabla_w J(w) = 0$（即目标函数梯度为零的点）。此时 $g(w)$ 单调递增等价于 $J(w)$ 是凸函数—— 这是优化问题中常用的假设。

而 $\nabla_w g(w) \leq c_2$ 表明 $g(w)$ 的梯度有上界。例如，$g(w) = \tanh(w-1)$ 满足该条件，但 $g(w) = w^3 - 5$ 不满足（其梯度 $3w^2$ 无界）。

**条件（b）（关于系数 $\{a_k\}$）**：这一条件在强化学习算法中很常见，需重点理解：

- $\sum_{k=1}^{\infty} a_k^2 < \infty$ 意味着当 $n \to \infty$ 时，$\sum_{k=1}^{n} a_k^2$ 的极限有上界，即要求 $a_k$ 随 $k \to \infty$ 逐步收敛到 0；

- $\sum_{k=1}^{\infty} a_k = \infty$ 意味着当 $n \to \infty$ 时，$\sum_{k=1}^{n} a_k$ 的极限为无穷大，即要求 $a_k$ 收敛到 0 的速度不能过快。

这两个子条件的具体作用将在后续进一步分析。

**条件（c）**：这是一个温和条件，不要求观测噪声 $\eta_k$ 服从高斯分布。一个重要的特殊情况是：$\{\eta_k\}$ 为独立同分布（i.i.d.）随机序列，且满足 $\mathbb{E}[\eta_k] = 0$、$\mathbb{E}[\eta_k^2] < \infty$。此时因 $\eta_k$ 与历史信息集 $H_k$ 独立，可得 $\mathbb{E}[\eta_k \mid H_k] = \mathbb{E}[\eta_k] = 0$、$\mathbb{E}[\eta_k^2 \mid H_k] = \mathbb{E}[\eta_k^2]$，满足条件（c）。

### 条件（b）的重要性分析


#### 为何条件（b）对 RM 算法的收敛至关重要？

后续将通过定理的严谨证明回答这一问题，此处先给出直观解释：

**首先**，<span style={{color: "red"}}>**条件**</span>： $\sum_{k=1}^{\infty} a_k^2 < \infty$ 意味着 $a_k \to 0$（$k \to \infty$）。若带噪观测值 $\tilde{g}(w_k, \eta_k)$ 有界，则 $a_k \tilde{g}(w_k, \eta_k) \to 0$，进而 $w_{k+1} - w_k \to 0$—— 即当迭代次数足够大时，相邻两次的估计值 $w_{k+1}$ 与 $w_k$ 会逐渐接近，避免序列持续波动。若 $a_k$ 不收敛到 0，$w_k$ 可能在迭代后期仍大幅波动，无法稳定到真实根。

**其次**，<span style={{color: "red"}}>**条件**</span>： $\sum_{k=1}^{\infty} a_k = \infty$ 意味着 $a_k$ 收敛到 0 的速度不能过快。对迭代公式进行累加：

$$w_2 - w_1 = -a_1 \tilde{g}(w_1, \eta_1), \quad w_3 - w_2 = -a_2 \tilde{g}(w_2, \eta_2), \quad w_4 - w_3 = -a_3 \tilde{g}(w_3, \eta_3), \quad \dots$$

累加后可得：

$$w_1 - w_{\infty} = \sum_{k=1}^{\infty} a_k \tilde{g}(w_k, \eta_k)$$

若 $\sum_{k=1}^{\infty} a_k < \infty$，则 $\left| \sum_{k=1}^{\infty} a_k \tilde{g}(w_k, \eta_k) \right|$ 有界（设上界为 $b$），即：

$$|w_1 - w_{\infty}| = \left| \sum_{k=1}^{\infty} a_k \tilde{g}(w_k, \eta_k) \right| \leq b$$

若初始估计值 $w_1$ 与真实根 $w^*$ 的距离满足 $|w_1 - w^*| > b$，则由上式可知 $w_{\infty}$ 不可能等于 $w^*$，即算法无法找到真实根。因此，条件 $\sum_{k=1}^{\infty} a_k = \infty$ 是保证"任意初始估计值下算法均能收敛"的必要条件。

#### 哪些序列满足条件（b）？

哪些序列满足 $\sum_{k=1}^{\infty} a_k = \infty$ 且 $\sum_{k=1}^{\infty} a_k^2 < \infty$？

一个典型序列是 <span style={{color: "red"}}>**关键序列**</span> $a_k = 1/k$：

**一方面**，当 $n \to \infty$ 时，有：

$$\lim_{n \to \infty} \left( \sum_{k=1}^{n} \frac{1}{k} - \ln n \right) = \kappa$$

其中 $\kappa \approx 0.577$ 称为**欧拉-马歇罗尼常数**（Euler-Mascheroni constant）。由于 $\ln n \to \infty$（$n \to \infty$），可得 $\sum_{k=1}^{\infty} \frac{1}{k} = \infty$。事实上，$H_n = \sum_{k=1}^{n} \frac{1}{k}$ 在数论中被称为**调和数**（harmonic number）。

**另一方面**，已知 $\sum_{k=1}^{\infty} \frac{1}{k^2} = \frac{\pi^2}{6} < \infty$—— 求解该无穷级数的问题在数学中被称为**巴塞尔问题**（Basel problem）。

综上，序列 $\{a_k = \frac{1}{k}\}$ 满足定理的条件（b）。值得注意的是，对该序列进行微小调整（如 $a_k = \frac{1}{k+1}$，或 $a_k = \frac{c_k}{k}$ 且 $c_k$ 有界）后，仍能满足条件（b）。
 

### Application to mean estimation

$$w_{k+1} = w_k + \alpha_k(x_k - w_k)$$

当 $\alpha_k = \frac{1}{k}$ 时，我们可得到 $w_{k+1}$ 的解析表达式：$w_{k+1} = \frac{1}{k}\sum_{i=1}^k x_i$。但当 $\alpha_k$ 取一般值时，无法得到这样的解析表达式，此时的收敛性分析也更为复杂。不过我们可以证明，该情况下的均值估计算法本质是一种特殊的 RM 算法，其收敛性也因此可由 RM 定理直接推导得出。

特别地，定义函数：

$$g(w) \triangleq w - \mathbb{E}[X]$$

我们的原始问题是求解 $\mathbb{E}[X]$（随机变量 $X$ 的期望），这一问题可转化为求根问题：求解 $g(w) = 0$。给定任意 $w$ 值，我们能获得的带噪观测值定义为 $\tilde{g} \triangleq w - x$（其中 $x$ 是 $X$ 的一个样本）。

需注意，$\tilde{g}$ 可改写为：

$$
\begin{aligned}
\tilde{g}(w, \eta) &= w - x \\
&= w - x + \mathbb{E}[X] - \mathbb{E}[X] \\
&= (w - \mathbb{E}[X]) + (\mathbb{E}[X] - x) \\
&\triangleq g(w) + \eta
\end{aligned}
$$

其中 $\eta \triangleq \mathbb{E}[X] - x$（$\eta$ 为观测误差）。

针对该求根问题的 RM 算法为：

$$w_{k+1} = w_k - \alpha_k \tilde{g}(w_k, \eta_k) = w_k - \alpha_k(w_k - x_k)$$

显然，该式与式（6.4）中的均值估计算法完全一致。因此，根据定理 6.1，若满足 <span style={{color: "red"}}>**条件**</span>： $\sum_{k=1}^{\infty} \alpha_k = \infty$、<span style={{color: "red"}}>**条件**</span>： $\sum_{k=1}^{\infty} \alpha_k^2 < \infty$，且样本序列 $\{x_k\}$ 为独立同分布（i.i.d.）序列，则 $w_k$ 几乎必然收敛到 $\mathbb{E}[X]$。值得一提的是，该收敛性质不依赖于对 $X$ 分布的任何假设。

### Dvoretzky's convergence theorem

> **说明**：This section is slightly mathematically intensive. Readers who are interested in the convergence analyses of stochastic algorithms are recommended to study this section. Otherwise, this section can be skipped.

上面是赵老师的话，实际上这一部分就是<span style={{color: "red"}}>**德沃雷茨基收敛定理**</span>来证明 RM 算法及多种强化学习算法的收敛性的。但是出于工程思维，数学推导还是先暂时略过，后面有缘再回来补吧。

## Stochastic gradient descent

<span style={{color: "red"}}>**随机梯度下降（SGD）**</span>！SGD 就是一种特殊的罗宾斯-门罗（RM）算法，而均值估计算法又是一种特殊的 SGD 算法。

考虑如下优化问题：

$$
\begin{aligned}
\min_{w} J(w) = \mathbb{E}[f(w, X)] \tag{6.10}
\end{aligned}
$$

其中，$w$ 是待优化的参数，$X$ 是随机变量，期望 $\mathbb{E}[\cdot]$ 针对 $X$ 计算。此处 $w$ 和 $X$ 既可以是标量，也可以是向量；函数 $f(\cdot)$ 为标量函数。

求解式（6.10）的一种直接方法是**梯度下降**。具体来说，$\mathbb{E}[f(w, X)]$ 对 $w$ 的梯度为 $\nabla_w \mathbb{E}[f(w, X)] = \mathbb{E}[\nabla_w f(w, X)]$，因此梯度下降算法的迭代公式为：

$$
\begin{aligned}
w_{k+1} = w_k - \alpha_k \nabla_w J(w_k) = w_k - \alpha_k \mathbb{E}[\nabla_w f(w_k, X)] \tag{6.11}
\end{aligned}
$$

在满足一些温和条件（如 $f$ 为凸函数）的情况下，该梯度下降算法能够找到最优解 $w^*$。

梯度下降算法需要计算期望 $\mathbb{E}[\nabla_w f(w_k, X)]$。获取该期望的一种方式是基于 $X$ 的概率分布，但在实际场景中，$X$ 的分布往往是未知的；另一种方式是收集 $X$ 的大量独立同分布（i.i.d.）样本 $\{x_i\}_{i=1}^n$，通过样本近似期望：

$$\mathbb{E}[\nabla_w f(w_k, X)] \approx \frac{1}{n}\sum_{i=1}^n \nabla_w f(w_k, x_i)$$

将其代入式（6.11），可得：

$$
\begin{aligned}
w_{k+1} = w_k - \frac{\alpha_k}{n}\sum_{i=1}^n \nabla_w f(w_k, x_i) \tag{6.12}
\end{aligned}
$$

式（6.12）所示算法存在一个问题：每次迭代都需要使用全部样本。但在实际应用中，样本往往是逐个收集的，此时更希望每收集一个样本就更新一次参数 $w$。为此，可采用如下算法：

$$
\begin{aligned}
w_{k+1} = w_k - \alpha_k \nabla_w f(w_k, x_k) \tag{6.13}
\end{aligned}
$$

其中，$x_k$ 是第 $k$ 步迭代时收集的样本。这就是著名的<span style={{color: "red"}}>**随机梯度下降算法（SGD）**</span>。该算法之所以被称为"随机"，是因为其依赖于随机样本序列 $\{x_k\}$。

与式（6.11）的梯度下降算法相比，SGD 用随机梯度 $\nabla_w f(w_k, x_k)$ 替代了真实梯度 $\mathbb{E}[\nabla_w f(w, X)]$。由于 $\nabla_w f(w_k, x_k) \neq \mathbb{E}[\nabla_w f(w, X)]$，这种替代能否保证当 $k \to \infty$ 时 $w_k \to w^*$ 呢？答案是肯定的，有证明。

具体来说，可将随机梯度拆分为真实梯度与误差项之和：

$$\nabla_w f(w_k, x_k) = \mathbb{E}[\nabla_w f(w_k, X)] + \left( \nabla_w f(w_k, x_k) - \mathbb{E}[\nabla_w f(w_k, X)] \right) \triangleq \mathbb{E}[\nabla_w f(w_k, X)] + \eta_k$$

其中，$\eta_k = \nabla_w f(w_k, x_k) - \mathbb{E}[\nabla_w f(w_k, X)]$ 为随机梯度与真实梯度的误差（扰动项）。

将上式代入式（6.13），SGD 算法可改写为：

$$w_{k+1} = w_k - \alpha_k \mathbb{E}[\nabla_w f(w_k, X)] - \alpha_k \eta_k$$

由此可见，SGD 算法与常规梯度下降算法的唯一区别在于多了一项扰动项 $\alpha_k \eta_k$。由于样本 $\{x_k\}$ 是独立同分布的，有 $\mathbb{E}_{x_k}[\nabla_w f(w_k, x_k)] = \mathbb{E}_X[\nabla_w f(w_k, X)]$，因此：

$$\mathbb{E}[\eta_k] = \mathbb{E}\left[ \nabla_w f(w_k, x_k) - \mathbb{E}[\nabla_w f(w_k, X)] \right] = \mathbb{E}_{x_k}[\nabla_w f(w_k, x_k)] - \mathbb{E}_X[\nabla_w f(w_k, X)] = 0$$

扰动项 $\eta_k$ 的均值为 0，这从直观上表明它不会破坏算法的收敛性。
### Application to mean estimation

我们将均值估计问题转化为如下优化问题：

$$
\begin{aligned}
\min_{w} J(w) = \mathbb{E}\left[ \frac{1}{2}\|w - X\|^2 \right] \triangleq \mathbb{E}[f(w, X)] \tag{6.14}
\end{aligned}
$$

其中，$f(w, X) = \frac{1}{2}\|w - X\|^2$（$\|\cdot\|$ 为范数），其对 $w$ 的梯度为 $\nabla_w f(w, X) = w - X$。通过求解 $\nabla_w J(w) = 0$，可验证该优化问题的最优解为 $w^* = \mathbb{E}[X]$。因此，该优化问题与均值估计问题是等价的。

**求解式（6.14）的梯度下降算法为**：

$$
\begin{aligned}
w_{k+1} &= w_k - \alpha_k \nabla_w J(w_k) \\
&= w_k - \alpha_k \mathbb{E}[\nabla_w f(w_k, X)] \\
&= w_k - \alpha_k \mathbb{E}[w_k - X]
\end{aligned}
$$

该梯度下降算法无法直接应用，因为等式右侧的 $\mathbb{E}[w_k - X]$（即 $\mathbb{E}[X]$）是未知的——而 $\mathbb{E}[X]$ 正是我们需要求解的目标。

**求解式（6.14）的 SGD 算法为**：

$$w_{k+1} = w_k - \alpha_k \nabla_w f(w_k, x_k) = w_k - \alpha_k (w_k - x_k)$$

其中，$x_k$ 是第 $k$ 步迭代时获取的样本。值得注意的是，该 SGD 算法与式（6.4）中的迭代式均值估计算法完全一致。因此，<span style={{color: "red"}}>**式（6.4）是专为求解均值估计问题设计的 SGD 算法**</span>。
### Convergence pattern of SGD

随机梯度下降（SGD）算法的核心思想是用随机梯度替换真实梯度。但由于随机梯度具有随机性，我们可能会疑问：SGD 的收敛速度是否较慢，或是收敛过程本身具有随机性？幸运的是，通常情况下 SGD 能高效收敛。其存在一种有趣的收敛模式：当估计值 $w_k$ 与最优解 $w^*$ 距离较远时，SGD 的表现与常规梯度下降算法相似；仅当 $w_k$ 接近 $w^*$ 时，SGD 的收敛过程才会表现出更强的随机性。

随机梯度与真实梯度之间的相对误差定义为：

$$\delta_k \triangleq \frac{|\nabla_w f(w_k, x_k) - \mathbb{E}[\nabla_w f(w_k, X)]|}{|\mathbb{E}[\nabla_w f(w_k, X)]|}$$

为简化分析，我们考虑 $w$（待优化参数）与 $\nabla_w f(w, x)$（梯度）均为标量的情况。由于 $w^*$ 是最优解，满足 $\mathbb{E}[\nabla_w f(w^*, X)] = 0$，此时相对误差可重写为：

$$
\begin{aligned}
\delta_k = \frac{|\nabla_w f(w_k, x_k) - \mathbb{E}[\nabla_w f(w_k, X)]|}{|\mathbb{E}[\nabla_w f(w_k, X)] - \mathbb{E}[\nabla_w f(w^*, X)]|} = \frac{|\nabla_w f(w_k, x_k) - \mathbb{E}[\nabla_w f(w_k, X)]|}{|\mathbb{E}[\nabla_w^2 f(\tilde{w}_k, X)(w_k - w^*)]|} \tag{6.15}
\end{aligned}
$$

其中，最后一个等号由中值定理[7,8] 推导得出，且 $\tilde{w}_k \in [w_k, w^*]$（$\tilde{w}_k$ 是 $w_k$ 与 $w^*$ 之间的某个值）。

假设 $f$ 为严格凸函数，即对所有 $w$ 和 $X$，其二阶偏导数满足 $\nabla_w^2 f \geq c > 0$（$c$ 为正的常数）。此时，式（6.15）中的分母可进一步推导为：

$$\left| \mathbb{E}[\nabla_w^2 f(\tilde{w}_k, X)(w_k - w^*)] \right| = \left| \mathbb{E}[\nabla_w^2 f(\tilde{w}_k, X)] \right| \cdot |w_k - w^*| \geq c|w_k - w^*|$$

将上述不等式代入式（6.15），可得：

![SGD convergence pattern](/img/rl/f6-2.png)

来个例子，目标函数为 $f(w, X) = \frac{1}{2}|w - X|^2$，由此可推导：

- **随机梯度**：$\nabla_w f(w, x_k) = w - x_k$（$x_k$ 是 $X$ 的第 $k$ 个样本）

- **真实梯度**：$\mathbb{E}[\nabla_w f(w, X)] = w - \mathbb{E}[X] = w - w^*$（$w^* = \mathbb{E}[X]$ 是最优解）

将上述梯度代入相对误差公式，可得：

$$\delta_k = \frac{|\nabla_w f(w_k, x_k) - \mathbb{E}[\nabla_w f(w_k, X)]|}{|\mathbb{E}[\nabla_w f(w_k, X)]|} = \frac{|(w_k - x_k) - (w_k - \mathbb{E}[X])|}{|w_k - w^*|} = \frac{|\mathbb{E}[X] - x_k|}{|w_k - w^*|}$$

该表达式清晰地印证了此前的结论：

- $\delta_k$ 与 $|w_k - w^*|$ 成反比 —— 当 $w_k$ 远离 $w^*$ 时，相对误差小，SGD 接近梯度下降的收敛效率

- $\delta_k$ 与 $|\mathbb{E}[X] - x_k|$（样本与真实期望的偏差）成正比，因此 $\delta_k$ 的均值与 $X$ 的方差成正比（方差越大，样本偏差的平均水平越高）

### A deterministic formulation of SGD

式（6.13）中 SGD 的经典表述涉及随机变量，但实际应用中，我们常会遇到不涉及任何随机变量的 SGD "确定性表述"。

考虑一组实数集合 $\{x_i\}_{i=1}^n$（其中 $x_i$ 不一定是某个随机变量的样本），需解决的优化问题为 "最小化平均值"：$\min_{w} J(w) = \frac{1}{n}\sum_{i=1}^n f(w, x_i)$。其中，$f(w, x_i)$ 是参数化函数（$w$ 是待优化参数）。求解该问题的常规梯度下降算法为：

$$w_{k+1} = w_k - \alpha_k \nabla_w J(w_k) = w_k - \alpha_k \cdot \frac{1}{n}\sum_{i=1}^n \nabla_w f(w_k, x_i)$$

若集合 $\{x_i\}_{i=1}^n$ 的规模较大（如海量样本），且每次仅能从集合中获取一个数值，则采用增量方式更新 $w_k$ 更为高效，算法形式为：

$$
\begin{aligned}
w_{k+1} = w_k - \alpha_k \nabla_w f(w_k, x_k) \tag{6.16}
\end{aligned}
$$

需特别注意：此处的 $x_k$ 是第 $k$ 步 "获取的数值"，而非集合 $\{x_i\}_{i=1}^n$ 中固定的第 $k$ 个元素。

式（6.16）的算法形式与 SGD 高度相似，但因不涉及随机变量或期望，其与 SGD 的关系曾存在争议（例如：该算法是否属于 SGD？应按顺序还是随机使用集合中的数值？）。对此的核心解释是：可通过引入随机变量，将确定性表述转化为 SGD 的经典随机表述。具体步骤如下：

- 定义随机变量 $X$，其取值空间为集合 $\{x_i\}_{i=1}^n$；
- 假设 $X$ 服从均匀概率分布，即 $p(X = x_i) = \frac{1}{n}$（每个数值被选中的概率相等）；
- 此时，确定性优化问题可严格等价于随机性优化问题：$\min_{w} J(w) = \frac{1}{n}\sum_{i=1}^n f(w, x_i) = \mathbb{E}[f(w, X)]$

由此可见，式（6.16）的算法本质就是 SGD。只要 $x_k$ 是从集合 $\{x_i\}_{i=1}^n$ 中独立均匀采样得到的（而非按固定顺序选取），其估计值就能收敛。需注意：由于采样的随机性，$x_k$ 可能重复取集合中的同一个数值。
### BGD, SGD, and mini-batch GD

随机梯度下降（SGD）在每次迭代中仅使用一个样本，接下来我们将介绍小批量梯度下降（MBGD）—— 它在每次迭代中会使用更多几个样本。若每次迭代都使用全部样本，则该算法被称为批量梯度下降（BGD）。

具体来说，假设给定随机变量 $X$ 的一组随机样本 $\{x_i\}_{i=1}^n$，我们希望找到能最小化目标函数 $J(w) = \mathbb{E}[f(w, X)]$ 的最优解。用于求解该问题的批量梯度下降（BGD）、随机梯度下降（SGD）和小批量梯度下降（MBGD）算法分别如下：

$$w_{k+1} = w_k - \alpha_k \cdot \frac{1}{n}\sum_{i=1}^n \nabla_w f(w_k, x_i) \quad \text{（BGD）}$$

$$w_{k+1} = w_k - \alpha_k \cdot \frac{1}{m}\sum_{j \in I_k} \nabla_w f(w_k, x_j) \quad \text{（MBGD）}$$

$$w_{k+1} = w_k - \alpha_k \nabla_w f(w_k, x_k) \quad \text{（SGD）}$$

在批量梯度下降（BGD）算法中，每次迭代都会使用全部样本。当样本量 $n$ 较大时，$\frac{1}{n}\sum_{i=1}^n \nabla_w f(w_k, x_i)$ 会接近真实梯度 $\mathbb{E}[\nabla_w f(w_k, X)]$。

在小批量梯度下降（MBGD）算法中，$I_k$ 是第 $k$ 步得到的集合 $\{1, \dots, n\}$ 的子集，该子集的大小为 $|I_k| = m$（即小批量样本数为 $m$），且假设 $I_k$ 中的样本服从独立同分布（i.i.d.）。

在随机梯度下降（SGD）算法中，$x_k$ 是第 $k$ 步从样本集 $\{x_i\}_{i=1}^n$ 中随机采样得到的样本。

小批量梯度下降（MBGD）可看作是随机梯度下降（SGD）与批量梯度下降（BGD）之间的中间形式，其与后两者的对比优势如下：

- **与 SGD 相比**：MBGD 使用多个样本（而非单个样本）计算梯度，随机性被平均削弱，迭代过程更稳定；
- **与 BGD 相比**：MBGD 无需每次迭代都使用全部样本，在样本量较大时灵活性更高，计算成本更低。

需要注意的是：若 $m = 1$（小批量大小为 1），则 MBGD 会退化为 SGD；但即使 $m = n$（小批量大小等于总样本数），MBGD 也不一定等同于 BGD—— 因为 MBGD 是从样本集中随机选取 $n$ 个样本（可能存在重复），而 BGD 是固定使用全部 $n$ 个样本，随机选取的 $n$ 个样本可能无法覆盖原始样本集中的所有元素。

一般来说，小批量梯度下降（MBGD）的收敛速度比随机梯度下降（SGD）更快。原因在于：SGD 仅用单个样本的梯度 $\nabla_w f(w_k, x_k)$ 近似真实梯度，而 MBGD 使用 $\frac{1}{m}\sum_{j \in I_k} \nabla_w f(w_k, x_j)$ 近似真实梯度 —— 通过对多个样本的梯度取平均，随机性被抵消，使得该近似值更接近真实梯度。MBGD 的收敛性可参照 SGD 的收敛性证明思路推导得出。
具体来说，给定一组数值 $\{x_i\}_{i=1}^n$，我们的目标是计算其均值 $\bar{x} = \frac{1}{n}\sum_{i=1}^n x_i$。该问题可等价转化为如下优化问题：

$$\min_{w} J(w) = \frac{1}{2n}\sum_{i=1}^n \|w - x_i\|^2$$

该优化问题的最优解为 $w^* = \bar{x}$（即均值）。用于求解该问题的三种梯度下降算法分别如下：

$$w_{k+1} = w_k - \alpha_k \cdot \frac{1}{n}\sum_{i=1}^n (w_k - x_i) = w_k - \alpha_k (w_k - \bar{x}) \quad \text{（BGD）}$$

$$w_{k+1} = w_k - \alpha_k \cdot \frac{1}{m}\sum_{j \in I_k} (w_k - x_j) = w_k - \alpha_k \left( w_k - \bar{x}_k^{(m)} \right) \quad \text{（MBGD）}$$

$$w_{k+1} = w_k - \alpha_k (w_k - x_k) \quad \text{（SGD）}$$

其中，$\bar{x}_k^{(m)} = \frac{1}{m}\sum_{j \in I_k} x_j$（即第 $k$ 步小批量样本的均值）。

进一步地，若取步长 $\alpha_k = \frac{1}{k}$，可对上述方程求解得到：

$$w_{k+1} = \frac{1}{k}\sum_{j=1}^k \bar{x} = \bar{x} \quad \text{（BGD）}$$

$$w_{k+1} = \frac{1}{k}\sum_{j=1}^k \bar{x}_j^{(m)} \quad \text{（MBGD）}$$

$$w_{k+1} = \frac{1}{k}\sum_{j=1}^k x_j \quad \text{（SGD）}$$

上述方程的推导过程与式（6.3）类似，此处省略。从结果可看出：批量梯度下降（BGD）在每一步的估计值都恰好是最优解 $w^* = \bar{x}$；小批量梯度下降（MBGD）的收敛速度比随机梯度下降（SGD）更快，因为 $\bar{x}_k^{(m)}$ 本身已是小批量样本的均值，随机性更低。
### Convergence of SGD

下面给出随机梯度下降（SGD）收敛性的严格证明。

**定理 6.4（SGD 的收敛性）**：对于式（6.13）所示的随机梯度下降算法，若满足以下条件，则迭代序列 $w_k$ 几乎必然收敛到方程 $\nabla_w \mathbb{E}[f(w, X)] = 0$ 的根。

- **（a）** $0 < c_1 \leq \nabla_w^2 f(w, X) \leq c_2$；
- **（b）** $\sum_{k=1}^{\infty} a_k = \infty$ 且 $\sum_{k=1}^{\infty} a_k^2 < \infty$；
- **（c）** 样本序列 $\{x_k\}_{k=1}^{\infty}$ 服从独立同分布（i.i.d.）。

以下对定理 6.4 中的三个条件进行说明：

**条件（a）**：与函数 $f$ 的凸性相关，要求 $f$ 的曲率存在上下界。此处假设 $w$ 为标量，因此 $\nabla_w^2 f(w, X)$（$f$ 对 $w$ 的二阶偏导数）也为标量；该条件可推广到 $w$ 为向量的情况 —— 此时 $\nabla_w^2 f(w, X)$ 即为著名的海森矩阵（Hessian matrix）。

**条件（b）**：与罗宾斯-门罗（RM）算法的步长条件类似。事实上，随机梯度下降（SGD）本身就是一种特殊的 RM 算法（如 6.1 节方框中的证明所示）。在实际应用中，步长 $a_k$ 常被选为一个足够小的常数；此时虽然条件（b）不再满足（因为 $\sum_{k=1}^{\infty} a_k^2 = \infty$，而非 $\sum_{k=1}^{\infty} a_k^2 < \infty$），但算法在某种意义下仍能收敛 [24，1.5 节]。

**条件（c）**：是样本序列的常见要求，即样本需服从独立同分布。
