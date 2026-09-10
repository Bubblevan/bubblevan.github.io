---
title: "L11 · Scaling Laws"
weight: 11
date: 2026-08-29
updated: 2026-09-10
course: "CS336"
topics: ["CS336", "scaling-laws", "hyperparameter scaling", "optimizers"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture11/
---

Lecture 9 讨论的是 loss、模型规模、数据量和 compute 之间的关系。Lecture 11 往前再走一步：**如果不同规模的模型没有使用各自合适的 learning rate、batch size、初始化和训练 schedule，那么你拟合出来的 loss scaling law 可能只是在测量 training recipe 的好坏。**

假设 100M、1B、10B 模型全部使用同一组配置：

$$
\eta=3\times10^{-4},\qquad B=4\text{M tokens},
$$

小模型可能训练不足，中等模型还可以，大模型却刚好合适。此时随着模型变大，loss 的变化同时混入了模型规模和 hyperparameter mismatch 两个因素。Lecture 11 的核心因此不是“再拟合一条曲线”，而是：**scale 一整套 training recipe。**

![Lecture 11 原始课件第 2 页：为什么 scaling practice 需要额外的实验设计](/learning/cs336/lectures/l11-slide-02-02.png)

> 原始课件页：课程先把问题从“模型能不能 scale”改成“训练实践能不能可靠地 scale”。

![Scaling recipe 由模型规模、数据规模、超参数和训练日程共同决定](/learning/cs336/lectures/l11-scaling-recipe.png)

> 图：一次可迁移的 scaling recipe 同时约束模型、数据、超参数和训练日程，不能只记录参数量和 token 数。该图按本地 OpenAI 风格绘制。

## 1. 两种 hyperparameter scaling 哲学

Lecture 11 可以先压缩成两个选择。

第一条路线是改变 parameterization，让最优超参数尽量不随模型宽度漂移。代表方法是 maximal update parameterization（μP）以及对应的 μTransfer：在小 proxy model 上调好超参数，再把它迁移到更大的 target model。

第二条路线承认最优超参数会随规模变化，直接用实验拟合它们的 scaling law。例如对每个 compute 或 $(N,D)$ 组合做 LR × batch sweep，得到

$$
\eta^*=f(N,D,C),
\qquad
B^*=g(N,D,C).
$$

然后分别拟合 $\eta^*$ 和 $B^*$ 随规模的变化。

两条路线没有高低之分：μP 试图让 optimum 稳定，hyperparameter scaling law 试图预测 optimum 如何移动。前者减少昂贵的调参，后者保留更多 recipe 自由度；实际工作也可以混合使用，例如用 μP 稳住学习率，再用 scaling study 处理 batch、数据量和 optimizer。

## 2. μP：保持 activation 和 function update 的尺度

普通 parameterization 下，模型变宽并不保证一次 optimizer step 对网络函数造成的改变保持相同。真正应该稳定的是

$$
\boxed{\text{一次 update 让 network function 改变多少}}
$$

而不是单个参数元素的绝对改变量。

考虑一层

$$
h_l=W_lh_{l-1}.
$$

随着 hidden width $n$ 增大，参数矩阵的 fan-in、fan-out、梯度方差和更新方向都会变化。如果仍然使用同一个初始化和 learning rate，可能出现：

- activation 随 width 增大而爆炸或消失；
- update 对每个 coordinate 越来越小，模型变宽后反而学不动；
- update 太大，训练在大模型上变得不稳定。

μP 想守住两类极限。

### 初始化尺度

对每个 coordinate，希望

$$
h_{l,i}=\Theta(1),
$$

因此整层向量的 norm 可以随宽度增长为

$$
\lVert h_l\rVert=\Theta(\sqrt{n_l}),
$$

但单个 feature 不应因为网络变宽而改变数量级。

### 更新尺度

一次更新

$$
W_l\leftarrow W_l+\Delta W_l
$$

带来的 function 或 activation change 也应该有良好极限，不能因为 width 增大而趋近于 0 或无穷大。μP 的要点不是“所有学习率除以 width”，而是根据 parameter role 的 fan-in、fan-out 和 optimizer update 规则，分别设置初始化和学习率缩放。

![Lecture 11 原始课件第 44 页：μP 的最大更新参数化](/learning/cs336/lectures/l11-slide-44-44.png)

> 原始课件页：μP 关注的是不同宽度下 activation 和 update 的极限行为，而不是给整个模型乘一个统一的 magic factor。

Transformer 里至少要区分 embedding、attention projection、MLP 输入矩阵、MLP 输出矩阵、LM head 和 normalization 参数；换成 Adam、AdamW 或 Muon 后，update scaling 还会继续变化。因此真正实现 μP 时，必须使用与 parameter type 和 optimizer 匹配的完整规则，不能只记一条“LR / width”。

### μTransfer 为什么能省实验成本

如果 μP 让宽度变化后的 optimum 足够稳定，那么可以在小模型上做昂贵的 LR sweep：

$$
\text{proxy model}
\xrightarrow{\text{tune}}
\text{hyperparameters}
\xrightarrow{\text{transfer}}
\text{target model}.
$$

这不是说 target model 完全不需要验证，而是把搜索范围从“重新扫一整张网格”缩小为“验证迁移是否仍在合理区间”。小实验因此真正具备了工程价值。

原始课程用一个很具体的尺度变化说明 μTransfer 的目标：先在约 40M 参数的 proxy model 上做 learning-rate sweep，再把选出的 recipe 迁移到约 6.7B 的 GPT-like target model。这里的关键不是这两个数字本身，而是把昂贵的超参数搜索放在小模型上，把大模型运行留给少量迁移验证；如果每次换宽度都重新扫完整网格，hero run 的成本会迅速失控。

## 3. WSD：让不同数据规模共享训练主干

μP 主要处理 width 和 parameterization；batch 和训练 horizon 仍然会随目标 loss、数据量和训练阶段变化。Lecture 11 用 Warmup–Stable–Decay（WSD）处理另一个常见问题：让不同训练长度的实验能够复用稳定的中间阶段。

WSD 可以抽象为

$$
\text{warmup}\rightarrow\text{stable trunk}\rightarrow\text{decay}.
$$

![Lecture 11 原始课件第 15 页：WSD 学习率曲线在 MiniCPM scaling 中的作用](/learning/cs336/lectures/l11-slide-15-15.png)

> 原始课件页：稳定阶段形成可复用的训练主干，末尾再根据目标训练长度接不同的 decay tail。

### 为什么 cosine 不适合直接做 data sweep

cosine schedule 是

$$
\eta(t)=\frac{\eta_{\max}}2
\left[1+\cos\left(\frac{\pi t}{T}\right)\right],
$$

其中 $T$ 是总训练长度。假设分别比较 100B、200B、400B 和 800B tokens：

- 100B run 到终点时学习率已经接近 0；
- 800B run 在 100B checkpoint 处学习率仍然很高。

所以 800B run 的 100B checkpoint 不是一个完整的 100B-token recipe。若想公平比较每个 data budget，必须分别从头训练，成本很高。

WSD 把大部分训练放进与最终 horizon 相对解耦的 stable trunk，再从不同 checkpoint 分叉多个 decay tail。这样可以共享昂贵的前半段计算，同时让每个候选数据规模拥有自己的末尾衰减。

因此，WSD 的价值不只是某个单次训练的最终 loss，而是改变 data-scaling experiment 的成本结构。Cosine 往往需要分别训练 100B、200B、400B、800B 四条完整轨迹；WSD 可以先跑到最长 horizon 的 stable trunk，再从 100B、200B、400B 等 checkpoint 分叉较短的 decay tail。主干计算从“各个 horizon 相加”变成“一条最长主干加多个尾部”，这才让多个数据预算的比较变得可复用。

MiniCPM 一类实验还提醒我们，compute-optimal 的 token/parameter 比例会随数据质量、schedule 和整体 recipe 改变。原始课件中出现过明显高于经典 20:1 记忆值的经验比例；它不应被当成新的固定常数，真正需要迁移的是方法：用可复用的训练主干，在多个数据 horizon 上测量并验证比例如何变化。

![Lecture 11 原始课件第 20 页：batch 与 learning rate 需要放在同一张实验网格中](/learning/cs336/lectures/l11-slide-20-20.png)

> 原始课件页：训练日程、学习率和 batch 是联动的 recipe 变量，不能在 scaling study 中只调整其中一个。

## 4. batch、learning rate 与 hyperparameter surface

μP 可以让 LR 更容易跨 width transfer，但不意味着 batch size 变成常数。Lecture 9 已经说明过 critical batch size：batch 较小时，增大 batch 可以减少梯度噪声并提高并行效率；超过临界区间后，继续增加 batch 的收益会快速变小。

而且最佳 batch 不一定只由 compute $C$ 决定。相同的

$$
C\approx6ND
$$

可以来自大模型少数据，也可以来自小模型多数据；这两种训练的 optimization dynamics 不必相同。因此更谨慎的经验形式是

$$
\eta^*=\eta(N,D),
\qquad
B^*=B(D)
$$

或在更粗略的研究中使用 $\eta^*(C)$、$B^*(C)$ 作为近似。

实际实验不应只记录网格中唯一的最低点，还要看附近的 loss landscape。如果 LR × batch 的低损失区域是一个宽盆地，那么 grid quantization error 和少量测量噪声不会显著改变配置；如果它是一个尖点，所谓 optimum 对步长、warmup 和随机种子都会非常敏感。

这也是为什么“optimal hyperparameter”不能脱离搜索网格解读：学习率只试了 $10^{-4}$ 和 $3\times10^{-4}$，得到的 optimum 可能只是离散网格中的最好点，而不是连续空间里的真实最优。

## 5. DeepSeek 与 StepFun：直接拟合最优超参数

DeepSeek 采取的是第二条路线：不强迫 LR 跨规模保持不变，而是对 LR × batch 做系统搜索。在每个规模或 compute budget 上找到

$$
(\eta^*,B^*)
$$

再拟合它们随 $C$、$N$ 或 $D$ 的变化。公开实验中常见的趋势是：compute 增加时，最优 learning rate 下降，最优 batch size 上升；但公式中的常数和单位依赖实验定义，不能直接照抄到自己的训练。

StepFun 的结果进一步提醒：$C$ 可能不是唯一充分变量。若固定 $C=6ND$，改变 $D/N$ 仍然会改变“一个参数被多少 token 使用”的 optimization regime。因此可以直接拟合二维或多维关系，例如

$$
\eta(N,D)\propto N^{-a}D^b,
\qquad
B(D)\propto D^c.
$$

从方法上看，这已经不再是 Lecture 9 那种单条 $L(C)$ 曲线，而是 response surface estimation：模型规模、数据量、batch、learning rate 和训练日程共同决定最终结果。

课件中的 DeepSeek 例子给出了一个具体的“先扫再拟合”形式：在它的 compute 和 batch 单位定义下，最优学习率和 batch size 可近似写成

$$
\eta_{\mathrm{opt}}\approx0.3118C^{-0.1250},
\qquad
B_{\mathrm{opt}}\approx0.2920C^{0.3271}.
$$

这些常数不能直接搬到别的训练系统，但方向很有用：compute 增大时，最优 learning rate 下降，最优 batch size 上升。StepFun 的结果进一步说明只用 $C$ 可能不够；在不同的 $N,D$ 组合下，可以拟合类似

$$
\eta(N,D)\approx1.79N^{-0.713}D^{0.307},
\qquad
B(D)\approx0.58D^{0.571}.
$$

同样，公式中的常数依赖单位、模型族和实验范围，不能脱离原始实验解释。真正重要的是从一维的 $L(C)$ 转向多维的 response surface，并检查 LR × batch 的近最优区域是否足够宽。

![Lecture 11 原始课件第 32 页：StepFun 的 scaling study 把优化器和超参数选择放在可外推的实验框架中](/learning/cs336/lectures/l11-slide-32-32.png)

> 原始课件页：scaling study 的目标是找出能随规模迁移的选择规则，而不是报告某个小模型上的单点最好结果。

### μP 与 hyperparameter scaling law 的关系

可以把两者写成同一个问题的两种答案：

$$
\text{小模型的 optimum 如何迁移到大模型？}
$$

- **μP**：改变参数化，让 $\eta^*(N)$ 尽量接近常数；
- **直接拟合**：保留原参数化，估计 $\eta^*(N,D,C)$ 的变化。

μP 的优势是 proxy transfer 便宜，代价是它依赖参数化和 optimizer 的假设；直接拟合更灵活，代价是需要更多规模和超参数实验。新架构、MoE、特殊 optimizer 或不同 weight decay 都可能破坏既有迁移规律，因此仍需要 held-out scale 验证。

## 6. Optimizer scaling：Muon 为什么值得单独看

Lecture 11 后半把 optimizer 放进 scaling recipe，是因为优化器的相对优势也可能随规模改变。AdamW 更接近 coordinate-wise normalization：每个参数坐标根据历史一阶、二阶统计量调整步长。

Muon 则更关注矩阵梯度的几何结构。对 momentum matrix $M$ 做 SVD：

$$
M=U\Sigma V^\top,
$$

理想化的 orthogonalized update 可以写成

$$
UV^\top,
$$

相当于不让 singular values 的差异直接决定 update 的尺度。真实实现不会每一步都完整做 SVD，而是使用 Newton–Schulz iterations 近似矩阵正交化；2D weight matrix 通常使用 Muon，bias、norm 参数等仍可能由 AdamW 一类 optimizer 处理。

![Lecture 11 原始课件第 38 页：不同 optimizer 的 scale sensitivity](/learning/cs336/lectures/l11-slide-38-38.png)

> 原始课件页：optimizer comparison 需要看随模型规模变化的曲线，而不是一个小模型上的单点排名。

比较 optimizer 时最容易犯的错误是把一个 optimizer 调到较优状态，另一个却使用默认配置，然后把 loss 差异归因于算法本身。公平比较至少要考虑：

- 每个 optimizer 是否都有自己的 LR、weight decay 和 warmup 搜索；
- 是否使用相同的有效 token、compute 和 batch；
- 差异在多个模型规模上是否保持；
- 训练早期、稳定阶段和 decay 后的优势是否一致。

小模型上赢 20% 不等于大规模预训练上仍然赢 20%。Muon 的 scaling study 之所以有价值，正是因为它把“矩阵几何看起来更合适”推进到了 scale validation，而不是停在局部实验。

## 7. Scaling recipe：从小实验到 held-out hero run

一套可执行的 Lecture 11 workflow 可以写成以下顺序。

### 冻结模型族和计量口径

先固定 architecture ratios，例如 $d_{ff}/d$、head 数随 hidden size 的关系、词表和数据 tokenizer。明确参数量、activated parameters、训练 token、理论 FLOPs 和实际吞吐的定义，否则后面不同实验无法比较。

### 处理最敏感的超参数

先决定采用 μP 迁移还是直接拟合 LR/batch scaling law；随后在小模型上画 LR × batch surface，检查 optimum 是否是宽盆地。不要把一个粗糙网格上的最低点直接当成精确常数。

### 选择训练 schedule

如果要比较多个 data horizon，优先考虑 WSD 这类可以共享 stable trunk 的 schedule；如果使用 cosine，就必须明确每个数据预算是否从头训练完整 schedule。

### 做 IsoFLOP sweep

固定 compute budget $C_i$，扫描模型大小 $N$，并按

$$
D=\frac{C_i}{6N}
$$

调整训练 token。得到每个预算下的候选最优点

$$
N^*(C_i),\quad D^*(C_i).
$$

之后再拟合 $L^*(C)$、$N^*(C)$、$D^*(C)$，以及必要时的 $B^*(C)$、$\eta^*(C)$ 和 architecture-specific 参数。

### 留出一个真正的 held-out scale

如果用 $10^{17}$–$10^{19}$ FLOPs 拟合，就不要把 $10^{20}$ 同时放入拟合。用前面的实验预测 $10^{20}$，再实际运行一次，验证的是 extrapolation，而不是 interpolation。

![Lecture 11 原始课件第 58 页：scaling recipe 的问题、解法和最终检查](/learning/cs336/lectures/l11-slide-58-58.png)

> 原始课件页：最终需要检查的不只是 loss 曲线，还包括 batch、optimizer、数据规模和计算预算是否随着规模一起被正确处理。

## 8. 这些方法的适用边界

μP 不是“停止调参”的许可证。它依赖 parameterization、width scaling、optimizer update 和具体网络结构；RMSNorm、RoPE、SwiGLU、MoE、QK-Norm、weight decay 以及 normalized optimizer 都可能改变 scale dynamics。换新架构时仍要检查：

$$
\text{LR optimum 是否重合？}
\qquad
\text{loss curve 是否平行？}
$$

$$
\text{activation/update statistics 是否稳定？}
$$

直接拟合也有自己的限制：搜索网格过稀时会有 quantization error；只用一个 compute 轴会忽略 $N,D$ 的不同组合；低规模训练不足会把 warmup 或 schedule 的影响误当成 scaling trend。

同样，optimizer comparison 不能只看默认配置，architecture comparison 不能只看一个模型尺寸，data scaling 不能只看 token 数。每个结论都应带上它的 compute、数据、recipe 和验证范围。

## 9. 课程串联

Lecture 9 问的是：

$$
\boxed{\text{固定 compute，模型规模 }N\text{ 和数据量 }D\text{ 应该怎么分？}}
$$

Lecture 11 问的是：

$$
\boxed{\text{你凭什么相信每个规模都被训练得接近最优？}}
$$

所以 Lecture 9 的

$$
L(N,D),\qquad N^*(C),\qquad D^*(C)
$$

必须和 Lecture 11 的

$$
\eta^*(N,D,C),\qquad B^*(N,D,C),\qquad \text{schedule},\qquad \text{optimizer}
$$

一起看。Lecture 2 的 FLOPs、memory 和实际吞吐则决定这些实验是否公平；A3 的 scaling study 正好要求你把这几讲合并成一个可复现的实验方案。

## 面试复盘

**1. 为什么只拟合 $L(C)$ 可能得到错误 scaling law？** 因为不同 compute 下的模型可能离各自 optimal learning rate、batch 或 schedule 的距离不同，loss 曲线混入了 recipe mismatch。

**2. μP 想保持什么不变？** 不是参数值本身，而是随 width 增大时 activation scale 和 function/update scale 的良好极限。

**3. μTransfer 为什么能省钱？** 如果 optimum 对 width 足够稳定，就可以在小 proxy 上调超参数，再把搜索结果迁移到 target model，减少 hero-scale grid search。

**4. 为什么 WSD 适合 data scaling study？** stable trunk 与最终 training horizon 相对解耦，可以从共享 checkpoint 分叉不同 decay tail；cosine 则让整个轨迹依赖最终训练长度。

**5. DeepSeek/StepFun 与 μP 的区别是什么？** μP 改参数化，让 optimum 尽量稳定；直接拟合则保留原参数化，预测 $\eta^*$ 和 $B^*$ 如何随 $N,D,C$ 移动。

**6. 为什么 $B^*$ 和 $\eta^*$ 不一定只依赖 compute？** 相同的 $C\approx6ND$ 可以由不同的模型规模和数据量组成，而 $D/N$ 会改变优化动力学。

**7. 为什么要看 LR × batch 的宽盆地？** 宽盆地意味着网格误差和随机噪声不容易改变结论；尖点 optimum 则很难迁移，也更容易被误读。

**8. 一个 optimizer 在小模型上赢了，为什么不能直接 scale？** 它可能只是超参数调得更好，或者优势只存在于当前模型尺寸；必须在多个 scale、相同 compute 和各自合理调参下验证。

**9. Muon 和 AdamW 的几何直觉差异是什么？** AdamW 更接近 coordinate-wise normalization，Muon 试图按矩阵的 spectral geometry 处理 2D weight update。

**10. 一次完整 scaling experiment 最重要的 held-out 是什么？** 留出一个没有参与拟合的更大 compute/模型规模，用它验证 extrapolation 是否成立。

如果只带走一句话，可以记成：

$$
\boxed{\text{不要只 scale 模型和数据，要 scale 一整套可验证的 training recipe。}}
$$
