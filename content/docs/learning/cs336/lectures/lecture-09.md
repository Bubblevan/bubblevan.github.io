---
title: "L09 · Scaling Laws"
weight: 9
date: 2026-08-29
updated: 2026-09-10
course: "CS336"
topics: ["CS336", "scaling-laws", "compute-optimal training"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture9/
---

前八讲主要在回答“怎样把一个模型训练起来”：tokenizer、Transformer、kernel、显存和并行策略都已经出现了。Lecture 9 换了一个问题：**在给定算力和时间预算时，到底应该训练多大的模型、喂多少 token、选什么 batch size？**

假设手里有一批 GPU 和固定训练窗口，直接尝试 70B、100B、150B 模型并不现实。Scaling law 的工程价值，就是在小规模上改变模型大小、数据量和计算预算，测出 loss 如何变化，再把规律外推到目标规模。它不是一条脱离实验的自然定律，而是一套“实验—拟合—外推—验证”的决策方法。

![Scaling law 的实验工作流：从小规模实验到大规模决策，再反馈回实验](/learning/cs336/lectures/l9-scaling-workflow.png)

> 图：一轮 scaling study 的最小闭环。大规模运行的结果仍然应该反馈到下一轮小规模实验，而不是把一次外推当成永久正确的配置。该图按本地 OpenAI 风格绘制。

## 1. Power law：为什么 loss 会随规模呈现可拟合的曲线

最常见的单变量形式是

$$
L(R)=L_\infty+A R^{-\alpha},
$$

其中 $R$ 可以是参数量 $N$、训练 token 数 $D$ 或计算量 $C$；$L(R)$ 是验证损失，$L_\infty$ 是资源无限时仍无法消除的误差，$A$ 是尺度常数，$\alpha$ 是 scaling exponent。

例如只改变数据量时，可以写成

$$
L(D)=L_\infty+A_DD^{-\alpha_D}.
$$

$\alpha_D>0$ 意味着增加数据会降低 loss，但边际收益会变小。这里的“幂律”不是说每个规模都严格落在同一条线上；真实实验会受到优化器、训练时长、数据分布和测量噪声影响，因此首先要检查的是一个稳定的 scaling regime，而不是强行把所有点拟合成一条线。

对上式移项并取对数：

$$
\log(L-L_\infty)=\log A-\alpha\log R.
$$

如果 $L_\infty$ 估计得合理，log-log 图上的数据会接近直线，斜率就是 $-\alpha$。这解释了 scaling-law 论文为什么总喜欢画 log-log 图：它把“资源增加一倍能得到多少改善”变成一个可以比较的斜率。

幂律还有一个很有用的性质：它对资源尺度是 scale-free 的。若把资源扩大为 $R\rightarrow\lambda R$，则

$$
L(\lambda R)-L_\infty
=
\lambda^{-\alpha}\bigl(L(R)-L_\infty\bigr).
$$

也就是说，在同一个 scaling regime 里，reducible loss 的改善比例主要由“资源扩大了多少倍”决定，而不是由当前绝对规模决定。比如从 10M 到 100M，和从 10B 到 100B，都是把资源扩大 10 倍；如果两者都处在同一条幂律区间，理论上对应相同的相对改善。这正是 scaling law 可以用于外推的原因，但也正是为什么一旦跨出了有效区间，外推会失效。

这个结论同时说明了数据 scaling 的残酷之处。Kaplan 风格的实验常见一个约为 $\alpha_D\approx0.095$ 的数据 exponent。若只看可约部分，数据扩大 10 倍后，loss 大约乘上

$$
10^{-0.095}\approx0.80,
$$

也就是只下降约 20%。如果希望可约损失减半，需要满足

$$
\frac{D_{\text{new}}}{D_{\text{old}}}
\approx 2^{1/0.095}\approx 1.5\times 10^3.
$$

这个约 1500 倍不是生产规则，而是帮助建立数量级直觉：在低 exponent 的幂律下，想获得线性级别的收益，往往需要付出极大的数据或计算代价。

![模型行为呈现可预测的 scaling 关系](/learning/cs336/lectures/l9-slide-04-04.png)

> 原始课件页：课程首先把 scaling law 放在“简单、可预测的经验规律”这个语境里，但后面会不断提醒这些规律有适用范围。

### 三个区域不能混在一起拟合

一条漂亮的 power law 通常只覆盖中间的有效区间。资源太少时，模型可能还没有进入稳定训练区，数据点会受到初始化、warmup 或优化失败的影响；资源足够大时，loss 接近下限，曲线进入 saturation，噪声和不可约误差开始占主导。

因此做实验时要先判断：

| 区域 | 典型现象 | 不能直接得出的结论 |
| --- | --- | --- |
| 数据或模型太小 | loss 受训练是否充分、warmup 等影响很大 | 不能把局部斜率当成通用 exponent |
| power-law regime | log-log 图近似直线，跨多个规模趋势稳定 | 可以做有限范围的拟合与外推 |
| saturation | 增加资源的收益很小，误差接近下限 | 继续套同一条幂律会高估收益 |

Lecture 9 的方法论重点就在这里：先找出可解释、可复现的 regime，再谈拟合和预测。

## 2. Architecture、optimizer 与 batch：参数量不是唯一变量

Scaling study 如果只改变参数量，得到的往往只是一个非常窄的结论。模型的 depth、width、attention head 数、FFN 宽度、词表大小、数据混合、optimizer 和学习率都可能改变曲线的斜率或截距。

在许多实验中，architecture 的影响更像改变截距：两个模型随规模增长的趋势相近，但其中一个在同一规模下整体 loss 更低。也有些 architecture 会改变 exponent，尤其当模型太浅、太窄，或者某个模块成为瓶颈时。读图时不能只问“哪条线在左边更低”，还要问两条线是否拥有相同的渐近趋势。

模型参数量也不是一个完全中性的横轴。embedding、输出头、共享权重和非 Transformer 参数是否计入，都会改变参数量的定义；如果不同实验的 parameter count 口径不同，拟合出来的“每参数规律”就没有可比性。原始课件专门把这些细节列为 scaling law 的实验坑。

### optimizer 与 μP 的问题

换 optimizer 或学习率通常会移动 scaling curve。一个更好的优化器可能让同样的模型在相同 token 数下达到更低 loss，但这不代表它改变了数据本身的难度；它可能只是减少了优化误差。

这也是 μP（maximal update parameterization）值得放在这里讨论的原因：如果参数化方式使不同宽度的模型拥有更一致的更新尺度，就可以在较小模型上选择学习率等超参数，再把选择迁移到更宽的模型。它的价值不是“免去所有调参”，而是让跨宽度迁移更有依据。

## 3. Batch size：什么时候继续加 batch 已经不划算

增大 batch 可以减少梯度噪声，让每一步的估计更稳定；但当 batch 已经足够大时，继续增加它并不会带来同等比例的优化收益。此时你只是用更多样本换一个更接近的梯度，却没有明显减少达到目标 loss 所需的总 token 数。

可以用一个临界 batch size $B_{\text{crit}}$ 来描述这个转折：

$$
B\ll B_{\text{crit}}\quad\text{时，增大 batch 往往能提高并行效率；}
$$

$$
B\gg B_{\text{crit}}\quad\text{时，边际收益趋于饱和。}
$$

临界 batch 不是一个只由模型参数量决定的常数。它会随训练阶段、目标 loss、数据噪声和优化器变化。Lecture 9 的图里，batch 的收益先随规模增加，经过一个转折后变得平坦；这个转折比“batch 越大越快”的口号更值得记。

![critical batch size 的几何直觉](/learning/cs336/lectures/l9-slide-37-37.png)

> 原始课件页：batch 增大可以减少噪声，但当不同 batch 的更新方向已经接近时，额外样本不会等比例减少训练成本。

学习率也不能脱离 batch 和模型规模单独讨论。batch 变大时，学习率常常需要一起调整；模型宽度变化时，参数化方式又会改变合适的学习率尺度。一个在小模型上工作良好的固定学习率，不能直接假设会在大模型上保持稳定。

## 4. Joint scaling：固定算力时，模型和数据应该怎样分配

单变量 scaling law 只告诉你“把某个资源增加会发生什么”，但训练预算通常同时受模型大小 $N$ 和数据量 $D$ 约束。一个常用近似是：

$$
C\approx cND,
$$

其中 $C$ 是训练计算量，$c$ 吸收了每 token 的前向、反向和实现常数。

如果验证损失由模型误差和数据误差共同决定，可以写成一种简化的 joint scaling law：

$$
L(N,D)=L_\infty+\frac{A}{N^\alpha}+\frac{B}{D^\beta}.
$$

第一项随模型变大而下降，第二项随数据变多而下降。给定固定的 $C$，不能同时把 $N$ 和 $D$ 无限增大，因为 $ND$ 近似受限。最优点就是在这条预算约束上寻找 loss 最低的位置。

如果把数据约束写成 $D=C/(cN)$，就得到

$$
L(N)=L_\infty+A N^{-\alpha}+B\left(\frac{C}{cN}\right)^{-\beta}
=L_\infty+A N^{-\alpha}+B' C^{-\beta}N^{\beta}.
$$

第一项随 $N$ 增大而下降，第二项却随 $N$ 增大而上升：模型太小会导致欠参数化，模型太大则会因为 token 不够而训练不足。于是曲线出现一个内部最优点。

![模型规模和数据规模的 compute-optimal trade-off](/learning/cs336/lectures/l9-slide-45-45.png)

> 原始课件页：给定训练计算预算时，模型参数和训练数据之间不是“越多越好”的独立选择，而是需要沿预算约束一起分配。

### 把最优点求出来

对上面的 $L(N)$ 求导：

$$
\frac{dL}{dN}=-\alpha A N^{-\alpha-1}+\beta B'C^{-\beta}N^{\beta-1}.
$$

令导数为零：

$$
\alpha A N^{-\alpha-1}
=\beta B'C^{-\beta}N^{\beta-1}.
$$

整理后得到

$$
N^{\alpha+\beta}\propto C^\beta,
\qquad
N_*(C)\propto C^{\frac{\beta}{\alpha+\beta}}.
$$

由于 $D=C/(cN)$，于是

$$
D_*(C)\propto C^{\frac{\alpha}{\alpha+\beta}}.
$$

这两个 exponent 就是 compute-optimal scaling 的核心：随着预算增加，模型和数据都应该增加，但增加速度由两种误差项的 exponent 决定。

## 5. Kaplan 与 Chinchilla：结论差异来自实验问题

早期 scaling work 观察到 loss 可以随参数、数据和 compute 呈现稳定的 power law。Kaplan 2020 的一组结论倾向于：在固定 compute 下，更大的模型更值得优先投入，训练 token 数相对少一些也可以接受。

后来 Chinchilla 重新做了 compute-optimal study，得到更均衡的结论：在给定训练计算量时，模型参数和训练 token 都应该随着预算增长；当时常用的粗略记忆是，大约需要几十个训练 token 对应一个参数，常被简化为“约 20 tokens/parameter”。这个数字不是永恒常数，也不能脱离 tokenization、数据质量、训练配方和算力定义使用。

两者的差异至少来自几类实验条件：

- 早期实验可能让模型训练得不够久，较大的模型看起来更占优；
- 参数量、训练 token、计算量和 batch 的定义或范围不同；
- 是否真的沿着固定 compute budget 寻找最优点不同；
- warmup、学习率、数据质量和训练步数会改变低规模曲线；
- 外推范围越远，任何小的拟合偏差都会被放大。

因此“Kaplan 错了，Chinchilla 对了”不是一个足够好的总结。更准确的问法是：**两项研究各自测量了什么，固定了什么，在哪个尺度和训练 regime 上拟合？**

![不同模型给出的 token/parameter 经验比例](/learning/cs336/lectures/l9-slide-54-54.png)

> 原始课件页：token/parameter 比例是经验配置，不应脱离模型、数据和训练目标被当成固定定律。

## 6. Chinchilla-style：compute-optimal 结论怎样测出来

Lecture 9 介绍了三种互相补充的方法。它们不是三套互斥理论，而是三种从实验数据中寻找 compute-optimal 配置的方式。

### 方法一：minimum over runs / lower envelope

先收集不同模型大小、不同训练 token 数的实验结果。对每一个参数规模，只保留在训练过程中达到的最低验证 loss，再看这些最优点随 compute 如何变化。连接这些点得到的 lower envelope，近似表示在每个 compute budget 下可以达到的最好结果。

它的优点是直观，不需要一开始假定完整的二维函数；缺点是对实验网格和训练曲线很敏感。如果某个模型没有训练到足够久，或者中间 checkpoint 保存得太稀疏，lower envelope 可能只是实验采样的假象。

### 方法二：IsoFLOP sweep

固定若干个 compute budget，在每个 budget 内改变模型大小和对应的训练 token 数。每一个预算得到一条 loss—model size 曲线，曲线最低点给出该预算下的近似最优模型规模。

记录不同预算下的最优点后，再拟合

$$
N_*(C)\propto C^a,
\qquad
D_*(C)\propto C^b.
$$

这就是 IsoFLOP 的价值：它把“总预算固定，如何在模型和数据之间分配”直接变成实验坐标系。要注意，IsoFLOP sweep 中的训练步数、batch、warmup 和学习率必须保持可解释的关系，否则最低点混合了架构变化和配方变化。

原始课件还用三个模型族说明了“固定 compute、扫描自由度”的共同套路：

- **Dense LM**：近似固定 $C\approx6ND$，在每条预算曲线上扫描模型参数量 $N$，由此改变训练 token 数 $D$。
- **MoE**：固定每个 token 的 active compute，同时扫描 total experts、active experts 和 model width。总参数量可以变大，但一次 forward 真正访问的专家数量仍受控。
- **Diffusion**：固定训练或采样的 compute，扫描 denoiser 的模型规模，观察 loss 或生成质量是否出现 U-shaped valley。

三者的架构不同，但实验判据一致：如果每个 compute budget 的曲线都有谷底，就取谷底作为该预算下的候选 optimum，再观察 optimum 如何随 $C$ 移动。这样 IsoFLOP 不是只服务于 dense Transformer，也能用于比较稀疏模型和不同生成模型族。

![IsoFLOP 方法的实验结构](/learning/cs336/lectures/l9-slide-47-47.png)

> 原始课件页：固定 compute，扫描模型大小，再比较每条预算曲线的最低点。

### 方法三：直接拟合二维 loss surface

也可以直接假设一个联合函数，例如

$$
L(N,D)=L_\infty+A N^{-\alpha}+B D^{-\beta},
$$

用不同 $N,D$ 组合的实验点拟合参数，然后在给定 $C\approx cND$ 的约束下求最优点。它利用了更多数据，能同时估计多个 exponent；但模型假设也更多，低规模噪声、warmup 和参数量口径都会影响结果。

这三种方法共同给出一个实验原则：**不要只画一条漂亮的外推线，要检查不同的拟合方式是否对最优方向给出相近答案。**

## 7. Predictability：为什么可预测性比一次最优更重要

Scaling study 的目的不是在当前小预算上找到一个偶然最低的点，而是让下一次更大的训练少走弯路。为此，预测误差比局部最优更值得关注。

至少有三个常见陷阱：

1. **参数量口径不一致**：是否包含 embedding、输出头和共享参数必须写清楚。
2. **warmup 和训练是否充分**：小模型如果没有完成 warmup，或者大模型只跑了很短时间，比较就失去了意义。
3. **batch size 和 learning rate 没有一起缩放**：改变 batch 却固定学习率，等于同时改变了优化问题。

所以一项 scaling result 最少应该记录：模型配置、总参数、训练 token、有效 batch、学习率 schedule、warmup、optimizer、数据混合和验证 checkpoint。否则别人看到的可能只是“某个配方在某个点更低”，而不是可以迁移的 scaling relation。

## 8. Data scaling：质量、重复与生产目标

“token 越多越好”只在数据质量和分布近似不变时成立。高质量数据、低质量数据、重复数据和来自不同领域的数据，对 loss 的贡献并不相同。把更多低质量 token 填入预算，可能比减少 token、提高数据质量更差。

数据重复也不是简单的“第二个 epoch 完全没有用”。第一次看到样本时，模型获得的是新的信息；重复样本可能继续改善拟合、减少梯度噪声，但收益通常下降，也可能加剧过拟合。更合理的实验是把数据质量和重复次数作为变量，分别观察 validation loss、下游任务和训练稳定性。

这也解释了为什么 compute-optimal 不一定等于 production-optimal。实际系统可能更在意：

- 推理成本和延迟，而不是只看预训练 FLOPs；
- 模型总参数带来的显存和部署限制；
- 训练后还要进行 instruction tuning、RL 或领域适配；
- 数据许可、污染、覆盖范围和质量过滤；
- 长上下文、工具调用或特定下游任务的能力。

因此 Chinchilla-style 的 token/parameter 比例应该作为一个基线，而不是生产系统的最终答案。生产目标可能偏向更小模型、更长训练，或者保留更多数据来提升迁移和泛化。

## 9. 实验设计：把 scaling law 落到 A3

对 CS336 的 scaling study，最实用的不是复述 exponent，而是把它落成一组可复现的实验。

### 第一步：先固定问题和预算

明确要预测的对象：给定目标 FLOPs，选择模型参数和 token 数；或者给定目标模型，预测需要的训练 token。固定 tokenizer、数据版本、评估 split、optimizer 和主要训练配方，避免每个实验同时改变太多因素。

### 第二步：选择多个小尺度 budget

不要只做一个模型和一个训练长度。选择若干个相差明显的 compute budget，每个 budget 至少覆盖几个模型大小；所有点都应记录实际 FLOPs、实际 token、有效 batch 和训练时间。

### 第三步：在每个 budget 内做 IsoFLOP sweep

对同一预算改变 $N$，按 $C\approx cND$ 调整 $D$。保存训练曲线和验证 checkpoint，而不是只保存最后一个 loss。这样既能找到每个预算下的最低点，也能检查低规模是否尚未进入稳定 regime。

### 第四步：用多种方式拟合

同时检查 lower envelope、IsoFLOP 最优点和二维 loss surface。比较它们给出的 $N_*(C)$、$D_*(C)$ 趋势是否一致；如果差异很大，先检查数据范围、warmup、batch 和参数口径，而不是马上选择看起来最漂亮的那条线。

### 第五步：外推后保留一次 target-ish run

外推到目标规模后，至少安排一次接近目标的验证运行。它的作用不是重新做完整 hyperparameter search，而是确认小规模拟合没有跨出适用范围。若验证点偏离预测，应该回到小规模实验更新模型，而不是把偏差解释成“偶然噪声”。

![scaling law 的最终用途是理解数据、模型和预算之间的取舍](/learning/cs336/lectures/l9-slide-57-57.png)

> 原始课件页：课程最后把 scaling law 收束为三个动作——理解 data scaling、理解 model scaling、用 scaling 做资源决策。

## 10. 课程串联

Lecture 2 讲过，训练成本不能只看 FLOPs，还要看 memory、bandwidth 和实际硬件利用率。Scaling law 里的 $C$ 如果只是理论 FLOPs，而不同模型的 kernel 利用率、通信和 batch efficiency 差异很大，拟合出来的 compute-optimal 结论就不一定对应真实墙钟时间。

Lecture 8 的数据和训练系统问题也会直接进入 scaling study：数据过滤改变有效数据质量，数据混合改变 $D$ 的含义，训练吞吐和 checkpoint 策略改变每个实验点的实际成本。Scaling law 并没有绕开这些工程细节，它要求你把这些变量记录清楚。

对 A3 来说，最容易犯的错误是把 scaling study 做成一张模型排行榜：只比较不同配置最后的 loss，然后挑最低的一组。真正的实验应该能够回答：

- 在固定 compute 下，模型大小和数据量如何分配？
- 这个结论是否在多个 budget 上稳定？
- 改变 batch、warmup 或 optimizer 后，曲线是否移动？
- 预测到更大规模时，验证运行是否仍然落在置信范围内？

## 面试复盘

**1. 为什么要画 log-log 图？** 从

$$
L-L_\infty=AR^{-\alpha}
$$

推出

$$
\log(L-L_\infty)=\log A-\alpha\log R,
$$

并说明斜率在什么前提下才可以解释成 exponent。

**2. 为什么固定 compute 会产生一个内部最优模型大小？** 使用

$$
C\approx cND,
$$

解释模型太小和模型太大分别受到什么限制。

**3. 为什么 Kaplan 与 Chinchilla 可以得到不同的建议？** 至少检查训练是否充分、参数和 token 的定义、compute budget 的设计、warmup、batch 和拟合范围。

**4. IsoFLOP sweep 的横轴和约束是什么？** 固定每条曲线的 compute，改变模型大小，并相应改变训练 token；曲线最低点才是该 budget 下的候选 optimum。

**5. 为什么一个更好的 optimizer 会改变 scaling curve，却不一定改变数据 scaling exponent？** 区分优化误差、模型误差和数据误差，不要把截距移动直接解释成新的数据规律。

**6. critical batch size 说明了什么？** 小 batch 区间里增加 batch 可能提高样本效率或硬件利用率；超过临界点后，更多样本只带来很小的边际收益。

**7. 为什么 production-optimal 不一定是 Chinchilla-optimal？** 把推理成本、部署显存、下游适配、数据质量和训练后流程加入目标函数。

**8. 你会怎样设计一次小规模 scaling study？** 写清楚固定变量、budget、模型/数据 sweep、记录字段、拟合方法和一次 target-ish 验证运行。

如果只在黑板上留下一个公式，可以留下 joint scaling law：

$$
L(N,D)=L_\infty+\frac{A}{N^\alpha}+\frac{B}{D^\beta},
\qquad C\approx cND.
$$

它把 Lecture 9 的两个判断放在了一起：模型太小会留下模型误差，数据太少会留下数据误差；算力预算则迫使你在两者之间做取舍。Scaling law 的最终产物不是一个神奇比例，而是一份经过小实验检验、知道适用边界、能够支撑下一次训练决策的实验方案。
