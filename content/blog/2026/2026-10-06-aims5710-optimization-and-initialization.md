---
schema: bubblevan/v1
id: blog-20261006-aims5710-optimization-and-initialization
content_kind: blog
title: "AIMS5710：从梯度下降、动量到权重初始化"
date: 2026-10-06
updated: 2026-10-06
status: draft
visibility: public
summary: "我按 10 月 6 日课堂顺序复盘深度网络优化：梯度下降、weight decay、动量与连续时间解释、Newton/BFGS、自适应优化器、Xavier/He 初始化，以及数据增强和学习率调度。"
topics: [AIMS5710, Optimization, Gradient Descent, Momentum, Newton Method, Weight Initialization]
projects: []
aliases: []
authors: [bubblevan]
---

今天是 AIMS5710 第五周。老师没有只沿着 PPT 逐条讲优化器，而是频繁转到白板：先从梯度下降的更新式讲起，用动量解释“记住过去的方向”，再把离散更新写成连续时间动力学；接着讨论 Hessian、Newton 和 BFGS，最后回到深层网络训练中很实际的权重初始化、数据准备和学习率调度。下面我尽量沿着课堂推进顺序记，公式以课件和板书相互校对。

## 1. 开场：HW2、Quiz 和考试用纸

白板上写着 **HW2 于 10 月 20 日截止，Quiz 1 于 10 月 27 日进行**。开场有人问考试计算量和可带材料，老师说不会有很多硬计算，并同意带**一张双面 cheat sheet**。我理解为考试时可以带一张双面纸；老师没说这是要提交的 calculation paper，纸张尺寸等细节会在之后几周补充。

老师还说考试当天自己会因出席会议而不在场，希望 TA 在考试时补充说明；后续几周会再交代更具体的考试安排。

## 2. 从目标函数回到梯度下降

### 2.1 优化对象是参数，不是数据

设训练集由 N 组输入与标签样本组成，网络输出为 \(\hat y=f(x;\theta)\)，训练目标写作 \(J(\theta;D)\)。数据集给定后，优化的是模型参数 \(\theta\)，目标是找到使损失尽量小的参数：

$$
\theta^*=\arg\min_{\theta}J(\theta;D).
$$

### 2.2 负梯度是局部下降方向

梯度 \(\nabla J(\theta)\) 指向目标函数局部上升最快的方向，因此最直接的下降更新是

$$
\theta_{t+1}=\theta_t-\eta\nabla J(\theta_t),
$$

其中 \(\eta\) 是 learning rate。老师用下坡骑车作比喻：梯度只告诉当前位置附近坡往哪边升，不保证远处仍是同一个坡度。步长太大会越过谷底、来回震荡甚至发散；步长太小则下降很慢。选择学习率是在“走得动”和“不走过头”之间折中。

![10 月 6 日白板回顾梯度下降、weight decay 与动量](/blog/2026/10-6/aims5710-2026-10-06-gradient-momentum-board.jpg)

*图源：10 月 6 日课堂照片。白板回顾了梯度下降更新、L2 weight decay，以及 HW2 和 Quiz 1 的日期。*

## 3. Weight decay 与 momentum：一个缩小参数，一个累积方向

### 3.1 L2 正则化和 weight decay

神经网络可表示的函数很多，小数据集上容易过拟合。老师把 L2 正则项加到原始损失上：

$$
J_{\mathrm{reg}}(\theta)=J(\theta)+\frac{\lambda}{2}\lVert\theta\rVert_2^2.
$$

沿这个目标做 SGD，会多出一个把参数往零拉的项：

$$
\theta_{t+1}=\theta_t-\eta\nabla J(\theta_t)-\eta\lambda\theta_t.
$$

限制参数幅度相当于限制模型可用的函数复杂度，通常能帮助泛化。课件还专门区分了 **decoupled weight decay**：先对未加 L2 的原损失算梯度，再单独衰减参数。对普通 SGD，两者写法容易看成同一件事；换成 Adam 这类自适应优化器后，L2 项会被梯度归一化一起缩放，和单独衰减参数不再等价，这也是 AdamW 要把 weight decay 解耦出来的原因。

### 3.2 Momentum：更新不只看眼前的梯度

普通 GD 每一步只看当前梯度，局部噪声或方向突然改变时容易左右震荡。老师用带质量的运动物体解释 momentum：物体不会因为某一瞬间的力稍微变化就立刻完全改向，之前积累的速度也会影响现在的位置。

把负梯度记作下降方向 \(g_t=-\nabla J(\theta_t)\)，一种常见写法是

$$
v_t=\beta v_{t-1}+(1-\beta)g_t,\qquad
\theta_{t+1}=\theta_t+\eta v_t.
$$

课件也把更新向量直接记成 \(\Delta\theta_t\)；不同写法可能把 \(\eta\) 或 \((1-\beta)\) 吸收到速度定义里。核心是递推地保留上一时刻的更新。\(\beta=0\) 时退化为普通梯度下降；\(\beta\) 越大，方向记忆越强。

老师让大家把递推式展开，比较早期和近期梯度对参数位置的累计贡献。早期梯度影响了更多次后续更新，所以在**累计参数位移**中的系数可呈现 \(1+\beta+\beta^2+\cdots\)，而较新的梯度经历的更新次数更少。这里说的是梯度对累计位移的总贡献；若只看某一步的速度向量，展开后的 EMA 则是越早的梯度权重越小，两者不是同一个量。

### 3.3 把离散 momentum 看成连续时间动力学

大约 31 分钟后，老师明确说下面的 ODE 分析是帮助理解，**不作为考试要求**。当 learning rate 趋近于零，普通梯度下降可看成 gradient flow：

$$
\dot\theta(t)=-\nabla J(\theta(t)).
$$

Momentum 多了一个速度状态，因此相应地变成二阶动力学。对一维二次目标

$$
J(\theta)=\frac{a}{2}\theta^2,
$$

其阻尼形式可写成

$$
\ddot\theta(t)+\gamma\dot\theta(t)+a\theta(t)=0.
$$

白板上画了不同阻尼下的轨迹：阻尼过大时像慢慢爬向谷底；阻尼较小时会越过谷底并振荡；临界值与 \(2\sqrt a\) 有关。放到多维目标里，不同特征方向的曲率不同，同一个阻尼或固定 momentum 未必能同时适配所有方向。这套连续时间解释的用途，是理解惯性、曲率和收敛速度之间的关系，而不是要求把 ODE 解法背成考试题。

![Momentum 的连续时间解释：gradient flow、阻尼振荡与曲率](/blog/2026/10-6/aims5710-2026-10-06-momentum-ode-board.jpg)

*图源：课堂白板。左侧从离散更新过渡到 gradient flow，中央用二次目标推导带阻尼的二阶方程，右侧画出不同阻尼下的收敛轨迹。*

## 4. 二阶信息：Newton 与 BFGS

### 4.1 Hessian 描述梯度变化得有多快

梯度是一阶信息；二阶信息由 Hessian 矩阵 \(H=\nabla^2J(\theta)\) 描述，它告诉我们目标函数在各个方向上的曲率。对当前位置附近做二阶 Taylor 展开：

$$
J(\theta+\Delta\theta)\approx J(\theta)+\nabla J(\theta)^\top\Delta\theta+
\frac12\Delta\theta^\top H(\theta)\Delta\theta.
$$

把这个局部二次近似对 \(\Delta\theta\) 求导并令其为零，会得到 Newton 方向：

$$
\Delta\theta=-H(\theta)^{-1}\nabla J(\theta),\qquad
\theta_{t+1}=\theta_t+\alpha\Delta\theta.
$$

一维时就是 \(\theta_{t+1}=\theta_t-\alpha J'(\theta_t)/J''(\theta_t)\)。\(\alpha\) 可通过 line search 选取；课件举的简单方式是 backtracking，逐渐缩小步长，直到目标函数下降。曲率大的方向自动取得较小步长，平坦方向则可以走得更远。

问题在于，若网络有 \(P\) 个参数，完整 Hessian 是 \(P\times P\) 矩阵：不仅计算成本高，保存它也很困难。因此深度网络训练通常不能直接照搬完整 Newton 更新。

### 4.2 Quasi-Newton：用相邻两步估计曲率

Quasi-Newton 不显式计算完整 Hessian，而从相邻两步的参数差和梯度差里抽取曲率信息。课上记

$$
p=\theta_{t+1}-\theta_t,\qquad q=g_{t+1}-g_t,
$$

局部近似满足 secant relation \(q\approx Hp\)。因此可以更新一个 Hessian（或其逆）的近似矩阵。老师在白板上推了 BFGS 更新，并建议看到复杂矩阵式时先看一维特例：转置在标量情形下消失，\(p\) 与 \(q\) 分别就是参数变化和梯度变化，曲率估计退化成 \(q/p\)，逆曲率则是 \(p/q\)。这样能看清复杂更新的目的，是让近似矩阵满足 secant 条件并保留合理曲率，而不是凭空多出一堆符号。L-BFGS 再用有限历史信息近似 BFGS，减少存储需求。

![Newton、BFGS 与方差推导的课堂板书](/blog/2026/10-6/aims5710-2026-10-06-newton-bfgs-board.jpg)

*图源：课堂白板近景。照片中间是二次近似与 Newton 更新，右侧写有 BFGS 的参数差/梯度差记号，最右侧转入初始化分析所需的独立性和方差性质。*

## 5. 不显式求 Hessian 时怎样调整每个参数的步长

老师随后按课件顺序快速过了几种一阶自适应方法。它们试图根据每个参数过去的梯度大小和方向调整更新，不必真的构造二阶 Hessian。

### 5.1 Rprop：先只看梯度符号

Rprop 对每个参数分别维护步长，只使用梯度的正负号：符号连续一致，说明方向可能可靠，就增大该参数步长；符号发生翻转，则可能越过了局部最优点，于是缩小步长。它暂时不关心梯度幅度到底是 0.01 还是 100。

### 5.2 Adagrad、Adadelta 与 RMSprop：记录梯度的尺度

Adagrad 为每个参数累计平方梯度：

$$
G_{t,i}=\sum_{\tau=1}^{t}g_{\tau,i}^2,\qquad
\theta_{t+1,i}=\theta_{t,i}-\frac{\eta}{\sqrt{G_{t,i}}+\epsilon}g_{t,i}.
$$

某个参数历史上更新很多，分母就会变大、有效学习率变小；缺点是平方梯度一直累加，训练久了步长可能缩得过小。Adadelta 和 RMSprop 改用平方梯度的指数移动平均，让统计量更关注近期历史，而不是永久累计全部旧梯度。Adadelta 还用参数更新幅度的移动平均处理梯度与参数单位不匹配的问题。

### 5.3 Adam 和 AdamW：一阶动量加二阶尺度

Adam 同时维护梯度的一阶移动平均 \(m_t\) 和平方梯度的二阶移动平均 \(v_t\)：

$$
m_t=\beta_1m_{t-1}+(1-\beta_1)g_t,\qquad
v_t=\beta_2v_{t-1}+(1-\beta_2)g_t^2.
$$

由于两者从零开始，初期会偏向零，因此 Adam 做 bias correction：

$$
\hat m_t=\frac{m_t}{1-\beta_1^t},\qquad
\hat v_t=\frac{v_t}{1-\beta_2^t},\qquad
\theta_{t+1}=\theta_t-\eta\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon}.
$$

课件给的常见默认值是 \(\beta_1=0.9,\beta_2=0.999\)。Adam 把方向平滑和逐参数学习率结合起来；AdamW 则把 weight decay 从 Adam 的梯度归一化中拆开，避免衰减强度也被 \(\sqrt{\hat v_t}\) 改变。老师顺带提了一种近年的优化器 Muon，作为优化器仍在持续发展的例子，没有在这节课里展开其算法。

## 6. 权重初始化：让前向信号和反向梯度都保持合适尺度

### 6.1 为什么不能把权重随便初始化

初始化不是无关紧要的起点。深层网络中，每层的导数会连乘；如果权重尺度使这些因子整体小于 1，梯度向浅层传播时会逐层变小；尺度太大又可能导致梯度爆炸。老师先回顾了 Batch Normalization、gradient clipping、residual connections 和 activation function 等相关办法，再转到通过初始化本身控制信号尺度。

### 6.2 线性层的前向方差与 Xavier

先看一层线性变换 \(y=Wx+b\)。为便于估算，课件假设 \(W,x,b\) 相互独立、权重元素 i.i.d. 且均值为零、输入各维 i.i.d. 且已中心化、偏置初始化为零。在这些假设下，若输入维度是 \(d_{\mathrm{in}}\)，则

$$
\operatorname{Var}(y_i)=d_{\mathrm{in}}\operatorname{Var}(W_{ij})\operatorname{Var}(x_j).
$$

希望前向传播后各层激活方差不要逐层放大或缩小，于是前向分析要求 \(\operatorname{Var}(W)=1/d_{\mathrm{in}}\)。从反向传播的方差做同样推导，会得到与输出维度相关的 \(1/d_{\mathrm{out}}\)。两边兼顾，就得到 Xavier/Glorot 的折中：

$$
\operatorname{Var}(W)=\frac{2}{d_{\mathrm{in}}+d_{\mathrm{out}}}.
$$

如果用正态分布，标准差取 \(\sqrt{2/(d_{\mathrm{in}}+d_{\mathrm{out}})}\)；若用均匀分布，则取区间 \([-\sqrt{6/(d_{\mathrm{in}}+d_{\mathrm{out}})},\sqrt{6/(d_{\mathrm{in}}+d_{\mathrm{out}})}]\)。Xavier 没有把非线性激活函数纳入推导，更适合激活分布近似对称的情况。

### 6.3 把 ReLU 考虑进去：He/Kaiming 初始化

ReLU 会把负值变为零，所以输出不再零均值；不能简单把二阶矩当作方差。若输入对称、正负各占一半，则 ReLU 后保留下来的二阶矩约为原来的一半：

$$
\mathbb E[\operatorname{ReLU}(z)^2]\approx\frac12\mathbb E[z^2].
$$

为了抵消这个减半，He/Kaiming 初始化把权重方差设为

$$
\operatorname{Var}(W)=\frac{2}{d_{\mathrm{in}}},
$$

正态初始化的标准差因此是 \(\sqrt{2/d_{\mathrm{in}}}\)；若从反向传播方向推导，则相应考虑 fan-out。它与 Xavier 的关键差别不是“更随机”，而是把 ReLU 的截断效应补偿进方差。

![权重初始化白板：前向/反向方差、ReLU 与 He 初始化](/blog/2026/10-6/aims5710-2026-10-06-initialization-board.jpg)

*图源：课堂白板。板书沿着线性层的方差展开前向和反向条件，再用 ReLU 的对称性说明为什么 Kaiming 初始化多出因子 2。*

## 7. 数据增强、预处理与学习率调度

### 7.1 数据增强不只是“把数据变多”

数据集较小时，可以利用数据中的对称性或领域知识生成保持标签的变化。图像可加噪声、平移、缩放或旋转；老师提醒，CNN 对平移本来就有一定结构性处理能力，因此不同变换带来的增益不一样，缩放等变化可能更值得关注。语音可以用 SpecAugment 在频谱的时间或频率方向做遮挡。

在自监督学习里，增强的目标也不只是扩充样本数量，而是让表示对某些扰动保持不变；例如遮住文本 token、图像区域或语音片段，再预测缺失部分，可以学习上下文表示。课上还把输入 normalization 和训练样本 shuffle 放在数据准备一并讨论：不同特征不应仅因为量纲不同就被模型偏爱；每轮打乱样本，则可减少固定数据顺序带来的无关模式。

### 7.2 固定学习率、衰减与 warmup

课件列了 time-based、step、exponential、cosine 等 schedule，也介绍 cosine warm restart 和 warmup。老师补充说，学习率并非在所有任务里都必须一路衰减：固定步长有时也能训练得很好，非凸目标附近持续移动还可能避免过早停在不理想的区域。课件展示的 CIFAR 比较中，cosine schedule 优于固定学习率；但这应视为具体实验，不是所有模型的统一结论。

Warmup 则是在训练开始阶段逐步把学习率升高，之后再进入衰减，Transformer 等架构有时会从中受益。最后由于时间不够，老师没有讲完 GPU/多 GPU 部分，并提醒课件中的硬件比较有些过时，可以自行阅读。

## 8. 我把今天的优化主线收在四个问题里

1. **一步该走多远？** GD 用 learning rate 控制；Newton 用曲率调整；Rprop、Adagrad、RMSprop、Adam 则尝试按参数自适应调整。
2. **方向要不要记住过去？** Momentum 把历史更新累积进当前速度，减轻震荡；Adam 把一阶动量和二阶梯度尺度合并。
3. **曲率算不算得起？** Newton 需要 Hessian，神经网络上存储和计算都太贵；BFGS/L-BFGS 用相邻梯度变化近似曲率。
4. **深层信号能否稳定传递？** 通过 Xavier 或 Kaiming 初始化，让前向激活和反向梯度的尺度不要随着层数失控。

这堂课最值得复习的不是把优化器名称背成清单，而是先看清每种方法在补哪一个短板：梯度方向太抖、尺度因参数而异、曲率未知，或深层网络里的信号逐层消失。考试计算表的正式细节等老师后续说明；眼下我按白板先记住 HW2 的 10 月 20 日截止和 Quiz 1 的 10 月 27 日日期。
