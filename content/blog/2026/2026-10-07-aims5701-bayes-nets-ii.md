---
schema: bubblevan/v1
id: blog-20261007-aims5701-bayes-nets-ii
content_kind: blog
title: "AIMS5701 Lecture 4：Bayes Nets II 的精确推断与采样"
date: 2026-10-07
updated: 2026-10-07
status: draft
visibility: public
summary: "我按 10 月 7 日课堂推进顺序，从 Bayes net 的联合分布和后验查询出发，整理枚举、因子、Variable Elimination，再比较 Prior、Rejection、Likelihood Weighting 与 Gibbs Sampling。"
topics: [AIMS5701, Bayesian Networks, Probabilistic Inference, Variable Elimination, Sampling]
projects: []
aliases: []
authors: [bubblevan]
---

这节课接着上次的 Bayes net 表示和条件独立，转向概率推断。前半段老师从 Alarm Network 的完整赋值概率开始，说明如何在 evidence 下查询 posterior；随后用 Traffic Network 引出因子、join 和 marginalization，逐步把一次性展开整个联合分布改成 Variable Elimination。后半段转到近似推断，依次讲 Prior Sampling、Rejection Sampling、Likelihood Weighting 和 Gibbs Sampling。

我按录音里的讲解顺序整理。转写在一些变量名和术语上有明显误识别；涉及公式、网络结构和数值时，我用 Lecture 4 课件校正了拼写与计算。

## 1. 开场：作业与课程项目安排

老师先提醒 Assignment 1 目前写的是下周三截止，即 10 月 14 日，负责 TA 是 Hao Du。有人提到作业与其他截止时间挤在一起，希望延期；老师表示会考虑并在公告里说明。因此目前我先按课件上的 10 月 14 日记，是否延期等 Blackboard 的后续通知。

Final Project 需要尽快组队并确定方向，但选题之后仍可以调整。TA 提供的方向只是参考，我可以自行提出主题；需要讨论时可以找任一位 TA。老师强调，项目评价关注我如何提出研究问题、解释决策并系统地完成研究过程，不要求做出 state-of-the-art 结果。

项目第一个里程碑是一页 mini-proposal，包含标题、背景、相关工作和问题定义等，课堂上说目标是下周日（10 月 11 日），具体公告稍后发布。第二个里程碑是一页阶段进度报告，约在第一个里程碑一个月后；最后提交 final report 并做 poster presentation。

## 2. 从 Bayes net 的局部 CPT 回到联合分布

Bayes net 用有向无环图表示随机变量之间的结构，每个节点配一张条件概率表（CPT）。CPT 为节点在不同父节点取值下分别指定条件分布；每组父节点条件下，子节点所有可能取值的概率和为 1。

一组完整赋值的联合概率，是每个节点相应局部条件概率的乘积。以 Alarm Network 为例，Burglary \(B\) 与 Earthquake \(E\) 是 Alarm \(A\) 的父节点，\(A\) 又影响 John calls \(J\) 和 Mary calls \(M\)：

$$
P(B,E,A,J,M)=P(B)P(E)P(A\mid B,E)P(J\mid A)P(M\mid A).
$$

比如要计算 \(P(+b,-e,+a,-j,+m)\)，就从每张 CPT 中取与这组赋值对应的条目相乘：

$$
P(+b)P(-e)P(+a\mid +b,-e)P(-j\mid +a)P(+m\mid +a).
$$

Bayes net 的紧凑性来自每个节点通常只依赖少量父节点。若直接储存所有变量的联合表，变量增加时表格会迅速变大；网络则用局部 CPT 的乘积隐式表示联合分布。

## 3. 推断要区分 query、evidence 和 hidden variables

这里的 inference 是从联合概率分布求出关心的量；它和神经网络里把输入送进模型得到输出时所说的 inference 不是同一个语境。今天主要查询后验分布 \(P(Q\mid e)\)：\(Q\) 是 query variable，\(e\) 是已经观察到的 evidence。其余既不是 query、也不是 evidence 的变量是 hidden variables。

即使问题没有直接问 hidden variable，它们仍然会影响 query 和 evidence 的联合概率，所以一般需要对它们求和消去。另一个可能的问题是找给定 evidence 下最可能的赋值（MAP / most likely explanation）；如果仍有其他变量未观测，通常要先对这些 hidden variables 求和，不能把所有求和操作不加区分地换成 max。

## 4. 精确推断的直接做法：Enumeration

Inference by enumeration 可以分成三步：

1. 只保留与 evidence 取值一致的联合赋值。
2. 对所有 hidden variables 求和，得到 query 与 evidence 的联合量 \(P(Q,e)\)。
3. 对所有 query 取值归一化，得到 \(P(Q\mid e)\)。

一般写成：

$$
P(Q\mid e)=\frac{P(Q,e)}{\sum_q P(q,e)},\qquad
P(Q,e)=\sum_h P(Q,h,e).
$$

以 Alarm Network 的 \(P(B\mid +j,+m)\) 为例，evidence 是两人都打电话，\(A\) 和 \(E\) 是 hidden variables：

$$
P(B\mid +j,+m)\propto
P(B)\sum_{a,e}P(E=e)P(A=a\mid B,e)P(+j\mid a)P(+m\mid a).
$$

最后对 \(B\) 的两个可能取值归一化。若 hidden variables 有 \(r\) 个二元变量，完整枚举最多要检查 \(2^r\) 种组合；变量多时，反复重算相同的乘积和就会很浪费。

## 5. 用因子看清楚中间计算

老师先把 CPT 和联合表统一看作 factor：一个带有若干变量维度的多维数组。变量用大写字母表示仍可变化的维度，用小写值固定某个维度；因此因子中大写变量的数量就是当前表格的维度数。

这也解释了几种容易混淆的写法：

- \(P(X,Y)\) 是联合分布，\(X,Y\) 都变化，所有条目加起来为 1。
- \(P(x,Y)\) 固定了 \(X=x\)，是联合表的一个切片；对所有 \(Y\) 求和得到 \(P(x)\)。
- \(P(Y\mid x)\) 固定条件 \(x\)，是 \(Y\) 的条件分布，条目和为 1。
- \(P(Y\mid X)\) 表示对每一种 \(X\) 取值各有一组 \(Y\) 的条件分布；每组分别归一化，全部条目加起来是 \(|X|\)，不一定是 1。
- \(P(y\mid X)\) 固定了结果 \(y\)，但 \(X\) 仍变化；它不是一个关于 \(X\) 归一化的分布，跨不同 \(x\) 的值没有统一的和为 1 性质。

因子视角有用，是因为 Variable Elimination 的每一步都只需组合当前涉及的局部表，不必先构造完整联合分布。

## 6. Join 与 marginalization：先用 Traffic Network 演示

Traffic Network 的结构是 \(R\rightarrow T\rightarrow L\)：是否下雨 \(R\) 影响交通状况 \(T\)，交通再影响是否迟到 \(L\)。它的联合分布写作：

$$
P(R,T,L)=P(R)P(T\mid R)P(L\mid T).
$$

要算边缘分布 \(P(L)\)，可以对 \(R,T\) 求和：

$$
P(L)=\sum_{r,t}P(r)P(t\mid r)P(L\mid t).
$$

**Join factors** 是把共享变量上的因子逐项相乘，并得到涵盖这些因子变量并集的新因子；课上把它类比为数据库 join。比如 \(P(R)\) 与 \(P(T\mid R)\) join 后得到 \(P(R,T)\)。若再与 \(P(L\mid T)\) join，就得到包含 \(R,T,L\) 的完整表。

**Eliminate / marginalize** 是沿某个变量维度把对应条目求和。例如对 \(P(R,T)\) 消去 \(R\)，剩下 \(P(T)\)；对 \(P(R,T,L)\) 消去 \(R\)，留下 \(P(T,L)\)。变量维度和表格大小随之缩小。

枚举方式会先把三个 CPT 全部 join 成八行的 \(P(R,T,L)\)，之后再依次消去 \(R,T\)。课件里的结果为 \(P(+l)=0.134\)、\(P(-l)=0.866\)。

## 7. Variable Elimination：把求和提前

Variable Elimination（VE）的关键是交错执行 join 和 sum-out，而不是先乘出完整联合表再统一求和：

1. 用局部 CPT 建立初始因子；如果有 evidence，先选出符合 evidence 的条目。
2. 选择一个 hidden variable，收集所有包含它的因子并 join。
3. 立刻对该变量求和，生成不再包含它的较小因子。
4. 重复处理其余 hidden variables。
5. join 剩余因子并对 query 归一化。

Traffic 例子中先 join \(P(R)\) 与 \(P(T\mid R)\)，马上消去 \(R\) 得到 \(P(T)\)；再与 \(P(L\mid T)\) join，消去 \(T\) 得到 \(P(L)\)。这个顺序的最大中间表有 4 个条目，而一次性展开 \(P(R,T,L)\) 需要 8 个条目。两种算法给出相同结果，差别在中间计算的规模。

有 evidence 时，将它先代入因子、删除不符合观察的行。例如求 \(P(L\mid +r)\) 时只保留 \(R=+r\) 的条目，消去 \(T\)，得到与 \(R=+r\) 对应的 \(L\) 切片，再归一化：

$$
P(+l\mid +r)=0.26,\qquad P(-l\mid +r)=0.74.
$$

课上用 Alarm Network 再走了一遍 VE：查询 \(P(B\mid +j,+m)\)，先消去 \(A\)，将 \(P(A\mid B,E),P(+j\mid A),P(+m\mid A)\) join 后对 \(A\) 求和，得到只依赖 \(B,E\) 的因子；再与 \(P(E)\) join 并消去 \(E\)，得到只依赖 \(B\) 的因子，最后与 \(P(B)\) 合并并归一化。老师特意提醒，按课件逐行展开所有求和的长等式不必死背；更适合把每个中间因子和被消去的变量逐步写出来。

## 8. 消元顺序决定最大中间因子

VE 的计算量和内存主要由过程中最大的 factor 决定。一个含 \(k\) 个二元变量的 factor 有 \(2^k\) 个条目；变量域更一般时，表格大小是各维度大小的乘积。因此中间 factor 的 scope 稍微变大，表格就可能指数级增长。

课件给了一个共同父节点 \(Z\) 指向 \(X_1,\ldots,X_n\)，而每个 \(X_i\) 都有已观察的子节点 \(Y_i\) 的结构。若先消去 \(Z\)，就必须把 \(Z\) 的先验与所有 \(P(X_i\mid Z)\) 一起组合，形成一个覆盖许多 \(X_i\) 的大因子，二元情形规模可达 \(2^n\)。如果先逐个消去各分支上的 \(X_i\)，每个分支先汇总成只依赖 \(Z\) 的小因子，最后再消去 \(Z\)，最大因子可以保持在常数规模（课件例子为 2 个条目）。

因此消元顺序可能造成很大的效率差异；但不是所有网络都存在能避免大因子的顺序。VE 通常比枚举更有效，最坏情形仍然对网络规模呈指数复杂度。

## 9. 从精确计算转到采样

当网络很大、CPT 不完整，或者精确计算成本过高时，可以用 sampling 估算概率。它类似重复模拟：从目标相关的抽样分布中生成 \(N\) 个样本，以频率或权重估计后验。样本数增加时，估计通常趋近目标概率，但有限样本不保证等于真值。

从离散分布抽一个值时，可以先用 Python 的 `random()` 从 \([0,1)\) 均匀取 \(u\)，再按结果概率把区间切开。例如 red、green、blue 的概率分别是 \(0.6,0.1,0.3\)：

$$
0\leq u<0.6\to red,\quad
0.6\leq u<0.7\to green,\quad
0.7\leq u<1\to blue.
$$

若得到 \(u=0.83\)，样本就是 blue。每个区间的长度等于对应结果的概率。

## 10. Prior Sampling：按网络拓扑生成完整赋值

Prior Sampling 不使用 evidence。按照拓扑顺序遍历节点，父节点先抽样，然后从 \(P(X_i\mid Parents(X_i))\) 抽出当前节点取值；最终返回一组完整赋值。Cloudy–Sprinkler–Rain–WetGrass 例子里，先抽 Cloudy，再根据 Cloudy 抽 Sprinkler 和 Rain，最后根据 Sprinkler 与 Rain 抽 WetGrass。

某个完整样本出现的概率，是每一步条件抽样概率的乘积，正好等于 Bayes net 对该完整赋值的联合概率。因此样本频率可以估计先验分布。例如课件的五个样本里 WetGrass 为 wet 出现 4 次、dry 出现 1 次，频率估计 \(P(+w)=0.8\)、\(P(-w)=0.2\)；样本多时估计会更接近真实边缘分布。

缺点是它不能直接处理条件查询的 evidence。可以从完整样本中筛选 evidence，但那就进入 Rejection Sampling。即使没有 evidence，稀有事件也可能很少出现，估计小概率需要大量样本；只抽很少样本虽然快，误差可能很大。

## 11. Rejection Sampling：不符合 evidence 就丢弃

要估 \(P(Q\mid e)\)，Rejection Sampling 仍按 prior 生成样本，但遇到与 evidence 不一致的样本就拒绝，只对通过筛选的样本统计 query。它在样本数趋于无穷时是正确的条件概率估计，也继承了 prior sampling 的简单性。

问题是当 evidence 很少见时，大多数样本都会被丢掉。若 evidence 的边缘概率是 \(p(e)\)，接受率约为 \(p(e)\)，要得到 \(N\) 个有效样本，平均需要生成约 \(N/p(e)\) 个样本。老师举例说明：如果 evidence 是很罕见的地震，可能需要抽很多次才能得到少数符合条件的样本。估计 \(0.001\) 量级概率且要求较小相对误差，本身也可能需要约 \(10^7\) 个样本，再乘上 \(1/p(e)\) 的筛选成本。

## 12. Likelihood Weighting：固定 evidence 并给样本加权

Likelihood Weighting 不再因为 evidence 变量抽错就丢弃样本，而是把 evidence 节点直接固定为观察值；其余非 evidence 节点仍按拓扑顺序抽样。每次生成样本时，权重从 1 开始；遇到 evidence 节点 \(E_j=e_j\)，就乘上该观察值在当前父节点条件下的概率：

$$
w^{(i)}=\prod_{E_j\in E}P(e_j\mid Parents(E_j)).
$$

用加权频率估算 posterior：

$$
\widehat{P}(Q=q\mid e)=
\frac{\sum_i w^{(i)}\mathbf{1}[q^{(i)}=q]}
{\sum_i w^{(i)}}.
$$

课件的 Cloudy 网络例子把 Sprinkler \(S=+s\) 和 WetGrass \(W=+w\) 设为 evidence。若先抽到 \(C=+c,R=+r\)，则固定 \(S=+s\) 的权重因子是 \(P(+s\mid +c)=0.1\)，固定 \(W=+w\) 的因子是 \(P(+w\mid +s,+r)=0.99\)，因此该样本权重为 \(1\times0.1\times0.99\)。这等价于避免实际抽出大量不符合 evidence 的结果，而用权重表达它们对目标估计的贡献。

它比 rejection 更充分地利用了每个样本，但并没有解决所有问题：evidence 只会影响其后代节点的抽样，无法反向影响它的祖先节点；如果样本权重差异特别大，少数高权重样本会支配估计，导致有效样本数很少。

## 13. Gibbs Sampling：固定证据，逐个重抽其他变量

Gibbs Sampling 先建立一个与 evidence 一致的完整赋值，再反复随机选择一个非 evidence 变量，根据其他变量当前取值重新抽它；evidence 始终固定。重复更新后，链在极限下的状态分布对应给定 evidence 的 posterior。与 Likelihood Weighting 不同，更新某个变量时，证据能通过网络结构影响其祖先和后代。

重抽单个变量不需要查看网络里所有其他变量，只需使用它的 Markov blanket：该节点的父节点、子节点，以及这些子节点的其他父节点。后面这组“子节点的其他父节点”不能漏掉，因为子节点的 CPT 同时依赖所有父节点。

以 Alarm Network 中的 \(A\) 为例，给定其他节点取值后，涉及 \(A\) 的局部因子是 \(P(A\mid B,E)\)、\(P(F\mid A,D)\)、\(P(G\mid A,E)\)（课件用 \(F,G\) 表示 \(A\) 的子节点及相关父节点）。先把这些因子按候选 \(A\) 取值相乘，再对 \(A\) 归一化，最后从该条件分布抽新值。Cloudy–Sprinkler 网络里重抽 \(S\) 的一个式子是：

$$
P(S\mid +c,+r,-w)\propto P(S\mid +c)P(-w\mid S,+r),
$$

因为与 \(S\) 无关、在两个候选值间相同的项可以约掉。

Gibbs 的样本是未加权的，但链上相邻状态相关，开始时也会受初始化影响。需要 warm-up，也需要足够长的链；强依赖、尖锐 posterior 或由确定性关系分隔的状态可能导致 mixing 很慢。老师在总结时特别补充，不能只凭网络更稠密就断言 Gibbs 一定混得更快；真正的 mixing 速度取决于依赖强度、evidence 形成的 posterior 形状及更新方式。丢掉固定数量的 warm-up 样本也不能单独证明链已收敛。

## 14. 四种采样方法放在一起比较

| 方法 | 如何处理 evidence | 估计方式 | 主要限制 |
| --- | --- | --- | --- |
| Prior Sampling | 不处理 evidence | 完整赋值的普通频率 | 不能直接估 posterior；稀有事件需要大量样本 |
| Rejection Sampling | 丢弃与 evidence 不符的完整样本 | 对保留样本计数 | evidence 稀有时拒绝率很高 |
| Likelihood Weighting | 固定 evidence 值，按条件概率累计权重 | 加权频率 | 权重可能高度不均；上游抽样不受下游 evidence 影响 |
| Gibbs Sampling | evidence 固定，逐个重抽其他变量 | 马尔可夫链状态频率 | warm-up、混合速度和样本相关性影响估计 |

精确方法里，Enumeration 易于直接定义，但会重复展开大量赋值；VE 通过提前 marginalize 减少中间计算，却仍受最大因子和消元顺序限制。采样不保证有限步内得到精确值，优点是能用局部抽样估计大网络的概率；方法之间的关键差别，在于 evidence 怎样进入抽样过程、计算结果是否带权，以及样本是否彼此独立。
