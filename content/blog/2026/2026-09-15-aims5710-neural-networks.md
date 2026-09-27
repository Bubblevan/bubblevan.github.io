---
schema: bubblevan/v1
id: blog-20260915-aims5710-backpropagation-and-mlp
content_kind: blog
title: "AIMS5710：反向传播、MLP 与激活函数"
date: 2026-09-15
updated: 2026-09-16
status: draft
visibility: public
summary: "依据 2026 年 9 月 15 日课堂录音与板书，逐步整理计算图、softmax/交叉熵、全连接层反向传播、MLP、激活函数及梯度消失与爆炸。"
topics: [AIMS5710, Deep Learning, Neural Networks, Backpropagation, MLP, CUHK]
projects: []
aliases: []
authors: [bubblevan]
---

今天继续上 AIMS5710《Deep Learning Fundamentals and Theories》。

## 1. 课堂现场照片

![AIMS5710 课堂现场与白板上的课程提醒](/daily/2026/9-15/aims5710-2026-09-15-lecture-overview.jpg)

这张课堂现场照片里的白板写着 recap：Homework 1 截止 **9 月 29 日**，覆盖 Lectures 1–2；Quiz 1 在 **10 月 27 日（Week 8）**，覆盖 Lectures 1–6。白板同时列出了线性回归和逻辑回归的估计器、损失和梯度更新，可是课明明都还没开始，说不定是上节课的内容。

## 2. 课程信息与需要核对的地方

课程大纲记录这门课为 3 学分，安排在每周二 18:30–21:30，地点是 Yasumoto Int'l Acad Park LT4，授课时间从 2026 年 9 月 8 日到 12 月 1 日，共 13 次。课程主线包括传统机器学习与深度学习的关系、多层感知机、卷积网络、深度网络优化、循环神经网络、Transformer、生成网络和高级主题。

课程网站是 Blackboard，讨论区使用 Piazza。部分课程活动和作业允许使用生成式 AI，但必须明确致谢并在使用其生成的文字、图片、数据或其他内容时进行恰当引用；作业还需要完成学术诚信声明。

评价信息存在一处需要保留的冲突：大纲的 Assessment 表写的是 essay test or exam 50%、homework or assignment 50%；但教学安排同时列出了 Week 8 的 Quiz 1 和 Week 13 的 Quiz 2，之前课堂记录中也出现过两个 quiz 各占 25% 的说法。所以先要肯定这两个 Quiz 后面再继续。

迟交一周以内会扣除该作业所得分数的 20%，超过一周不再接收提交。考试或 quiz 缺席也有提前申请和证明要求，不能等到考试结束后再临时补手续。

课堂白板进一步写明 Homework 1 的截止日期是 9 月 29 日，题目范围是 Lectures 1–2；Quiz 1 的日期是 10 月 27 日，范围是 Lectures 1–6。Homework 2 和 Homework 3 的具体截止时间待定ing

## 3. 从线性模型到 softmax
先回顾一下上一节课的内容。所有模型都可以按这个流程看：

1. **模型输出**：\(z=\theta^T x\)，然后可能再套一个函数。
2. **损失函数**：衡量预测和真实目标差多少。
3. **求梯度**：算 \(\partial J/\partial \theta\)。
4. **更新参数**：\(\theta \leftarrow \theta-\alpha \partial J/\partial \theta\)。

**线性回归、逻辑回归、softmax 回归，最后对参数的梯度都能写成“（预测 - 目标）× 输入”。**  
区别只是“预测”和“目标”的形式不同。

### 3.1 线性回归
对于线性回归：误差信号是 \(y-h\)。我们预测：

\[
h_\theta(x)=\theta^T x
\]

损失用平方误差MSE：

\[
J=\frac12 (y-h_\theta(x))^2
\]

对某个参数 \(\theta_j\) 求导：

\[
\frac{\partial J}{\partial \theta_j}
=-(y-h_\theta(x))x_j
\]

梯度下降：

\[
\theta_j \leftarrow \theta_j-\alpha \frac{\partial J}{\partial \theta_j}
\]

所以：

\[
\theta_j \leftarrow \theta_j+\alpha (y-h_\theta(x))x_j
\]

多样本时：

\[
\theta_j \leftarrow \theta_j+
\alpha\sum_r (y^{(r)}-h_\theta(x^{(r)}))x_j^{(r)}
\]

其 **几何解释** 也就是说：
- 如果真实值 \(y\) 比预测 \(h\) 大，残差 \(y-h>0\)，参数沿 \(x_j\) 方向移动，让预测变大。
- 如果预测过大，\(y-h<0\)，参数反方向移动，让预测变小。
### 3.2 逻辑回归

逻辑回归做二分类，标签 \(y\in\{0,1\}\)。  
模型先算线性得分：

\[
z=\theta^T x
\]

再把它压到 \(0\) 到 \(1\) 之间，作为概率：

\[
p=\sigma(z)=\frac{1}{1+e^{-z}}
\]

其中这个sigmoid函数：

\[
\sigma(z)\in(0,1)
\]

如果还用平方误差，求导会带一个 \(\sigma'(z)\)，训练会变慢。  
所以逻辑回归通常用**交叉熵损失**，前面我们提到过，就是负对数似然：

\[
J=-\left[y\log p+(1-y)\log(1-p)\right]
\]

对 \(z\) 求导：

\[
\frac{\partial J}{\partial p}
=-\frac{y}{p}+\frac{1-y}{1-p}
\]

而：

\[
\frac{\partial p}{\partial z}=p(1-p)
\]

所以：

\[
\frac{\partial J}{\partial z}
=
\left(-\frac{y}{p}+\frac{1-y}{1-p}\right)p(1-p)
\]

化简：

\[
=-y(1-p)+(1-y)p
=p-y
\]

于是：

\[
\frac{\partial J}{\partial \theta_j}
=
\frac{\partial J}{\partial z}\frac{\partial z}{\partial \theta_j}
=
(p-y)x_j
\]

更新：

\[
\theta_j \leftarrow \theta_j-\alpha(p-y)x_j
=
\theta_j+\alpha(y-p)x_j
\]

**和线性回归对比：**

- 线性回归：误差信号是 \(y-h\)
- 逻辑回归：误差信号是 \(y-p\)

形式很像，但逻辑回归的 \(p=\sigma(z)\) 只在极限情况下才等于 0 或 1。  
所以除非 \(z\to+\infty\) 或 \(z\to-\infty\)，\(p\) 不会严格等于标签。  
这解释了原笔记说的：**逻辑回归的“残差”不会像线性回归那样在有限参数处精确变成 0。**

#### 3.2.1 感知机
感知机直接看有没有分错：

- 分对了，不更新；
- 分错了，沿 \(x\) 或 \(-x\) 更新。

如果标签用 \(+1/-1\)，可以写成：

\[
\theta \leftarrow \theta+\alpha y x
\]

但它不是最小化一个光滑损失，所以“不完全等同于梯度下降”。

线性可分时，感知机可能有限步停止，但能把数据分开的权重通常不唯一。  
SVM 则进一步要求：不仅要分开，还要让最近样本到分界面的距离尽量大。这是延伸，不是当前主线。

### 3.3 多分类：从sigmoid到Softmax
现在有 \(K\) 个类别。  
每个类别都有自己的权重向量 \(\theta_i\)，第 \(i\) 类的线性得分是：

\[
z_i=\theta_i^T x
\]

这些 \(z_i\) 叫 **logit**。  
为了变成概率向量，用 softmax：

\[
p_i=\frac{e^{z_i}}{\sum_{k=1}^{K}e^{z_k}}
\]

它满足：

\[
p_i>0,\qquad \sum_{i=1}^{K}p_i=1
\]

**二分类是特例：**

当 \(K=2\) 时：

\[
p_1=\frac{e^{z_1}}{e^{z_0}+e^{z_1}}
=\frac{1}{1+e^{-(z_1-z_0)}}
=\sigma(z_1-z_0)
\]

如果令 \(z_0=0\)，则：

\[
p_1=\sigma(z_1),\qquad p_0=1-p_1
\]

所以二分类逻辑回归就是 softmax 多分类在 \(K=2\) 时的特殊情况。
#### 3.3.1 独热编码

多分类时，目标也要变成向量。  
如果真实类别是第 \(c\) 类，就用 one-hot：

\[
y_i=
\begin{cases}
1,& i=c\\
0,& i\neq c
\end{cases}
\]

交叉熵损失：

\[
J=-\sum_{i=1}^{K}y_i\log p_i
\]

因为只有正确类别 \(y_c=1\)，其他都是 0，所以它也等于：

\[
J=-\log p_c
\]

也就是：正确类别的预测概率越小，损失越大。
#### 3.3.2 Softmax的梯度
这里可能有点混乱，先给一张表：

| 模型 | 预测 | 目标 | 对 logit 的梯度 | 对参数的梯度 | 更新 |
|---|---|---|---|---|---|
| 线性回归 | \(h\) | \(y\) | \(h-y\) | \((h-y)x_j\) | \(\theta_j+\alpha(y-h)x_j\) |
| 逻辑回归 | \(p=\sigma(z)\) | \(y\in\{0,1\}\) | \(p-y\) | \((p-y)x_j\) | \(\theta_j+\alpha(y-p)x_j\) |
| Softmax | \(p_j\) | one-hot \(y_j\) | \(p_j-y_j\) | \((p_j-y_j)x_k\) | \(\theta_{j,k}+\alpha(y_j-p_j)x_k\) |
因为 softmax 是**多个输入 → 多个输出**。

输入是 \(K\) 个 logit：

\[
z_1,z_2,\dots,z_K
\]

输出是 \(K\) 个概率：

\[
p_1,p_2,\dots,p_K
\]

其中：

\[
p_i=\frac{e^{z_i}}{\sum_{k=1}^{K}e^{z_k}}
\]

问题来了：\(p_1\) 不仅和 \(z_1\) 有关，还和 \(z_2,z_3,\dots,z_K\) 有关，因为分母里有所有人。

所以我们要问的是：

> 如果我稍微动一下 \(z_j\)，\(p_i\) 会怎么变？

这就是偏导数：

\[
\frac{\partial p_i}{\partial z_j}
\]

- 当 \(i=j\)：动的是自己的 logit。
- 当 \(i\neq j\)：动的是别人的 logit。

一共 \(K\times K\) 个偏导数，排成矩阵就是 **Jacobian**。

**所以雅各比矩阵复习一下，它就是把所有“谁对谁求导”的结果摆成一张表。**

![课件中的 softmax 分式求导起点](/daily/2026/9-15/aims5710-nn-softmax-quotient-rule.png)

##### 手算：\(i=j\) 时，\(\frac{\partial p_i}{\partial z_i}\)
为了不混淆，先设：

\[
S=\sum_{k=1}^{K}e^{z_k}
\]

那么：

\[
p_i=\frac{e^{z_i}}{S}
\]

现在对 \(z_i\) 求偏导。注意：\(z_i\) 同时出现在分子和分母里。

用商法则。设：

\[
f=e^{z_i},\qquad g=S
\]

先算：

\[
\frac{\partial f}{\partial z_i}=e^{z_i}
\]

因为 \(e^{z_i}\) 对 \(z_i\) 求导还是自己。

再算：

\[
\frac{\partial g}{\partial z_i}
=
\frac{\partial S}{\partial z_i}
=
\frac{\partial}{\partial z_i}\sum_{k=1}^{K}e^{z_k}
\]

和式里只有 \(k=i\) 那一项含 \(z_i\)，所以：

\[
\frac{\partial S}{\partial z_i}=e^{z_i}
\]

现在用商法则：

\[
\frac{\partial p_i}{\partial z_i}
=
\frac{
e^{z_i}\cdot S-e^{z_i}\cdot e^{z_i}
}{S^2}
\]

分子提取 \(e^{z_i}\)：

\[
=
\frac{e^{z_i}(S-e^{z_i})}{S^2}
\]

把它拆成两项：

\[
=
\frac{e^{z_i}}{S}\cdot\frac{S-e^{z_i}}{S}
\]

而：

\[
\frac{e^{z_i}}{S}=p_i
\]

并且：

\[
\frac{S-e^{z_i}}{S}
=
1-\frac{e^{z_i}}{S}
=
1-p_i
\]

所以：

\[
\boxed{\frac{\partial p_i}{\partial z_i}=p_i(1-p_i)}
\]

这就是 \(i=j\) 的情况。

##### 手算：\(i\neq j\) 时，\(\frac{\partial p_i}{\partial z_j}\)

现在动的是别人的 logit \(z_j\)，其中 \(j\neq i\)。

还是：

\[
p_i=\frac{e^{z_i}}{S}
\]

这次对 \(z_j\) 求导。注意：分子 \(e^{z_i}\) 里没有 \(z_j\)，所以分子对 \(z_j\) 求导是 **0**。

分母 \(S\) 对 \(z_j\) 求导：

\[
\frac{\partial S}{\partial z_j}=e^{z_j}
\]

用商法则：

\[
\frac{\partial p_i}{\partial z_j}
=
\frac{
0\cdot S-e^{z_i}\cdot e^{z_j}
}{S^2}
\]

\[
=
-\frac{e^{z_i}e^{z_j}}{S^2}
\]

把它拆成两项相乘：

\[
=
-\frac{e^{z_i}}{S}\cdot\frac{e^{z_j}}{S}
\]

\[
\boxed{\frac{\partial p_i}{\partial z_j}=-p_i p_j}
\]

这就是 \(i\neq j\) 的情况。

##### final
现在我们有：

- 如果 \(i=j\)：\(\frac{\partial p_i}{\partial z_j}=p_i(1-p_i)\)
- 如果 \(i\neq j\)：\(\frac{\partial p_i}{\partial z_j}=-p_i p_j\)

引入一个符号 \(\delta_{ij}\)：

![课件中的 softmax Jacobian 分情况结果](/daily/2026/9-15/aims5710-nn-softmax-jacobian-case-split.png)

\[
\delta_{ij}=
\begin{cases}
1,& i=j\\
0,& i\neq j
\end{cases}
\]

那么两种情况可以统一写成：

\[
\boxed{\frac{\partial p_i}{\partial z_j}=p_i(\delta_{ij}-p_j)}
\]

验证一下：

- 当 \(i=j\)：\(\delta_{ij}=1\)，所以 \(p_i(1-p_j)=p_i(1-p_i)\)，对。
- 当 \(i\neq j\)：\(\delta_{ij}=0\)，所以 \(p_i(0-p_j)=-p_i p_j\)，也对。

##### 现在求交叉熵对 logit 的导数

交叉熵（负对数似然）：

\[
J=-\sum_{i=1}^{K}y_i\log p_i
\]

其中 \(y_i\) 是 one-hot，正确类别为 1，其余为 0。

我们要算：

\[
\frac{\partial J}{\partial z_j}
\]

这里 \(J\) 通过所有 \(p_i\) 依赖于 \(z_j\)，所以用多元链式法则：

\[
\frac{\partial J}{\partial z_j}
=
\sum_{i=1}^{K}
\frac{\partial J}{\partial p_i}
\cdot
\frac{\partial p_i}{\partial z_j}
\]

第一步：算 \(\frac{\partial J}{\partial p_i}\)

\[
J=-\sum_{i=1}^{K}y_i\log p_i
\]

对 \(p_i\) 求偏导，和式里只有第 \(i\) 项含 \(p_i\)：

\[
\frac{\partial J}{\partial p_i}
=
-y_i\cdot\frac{1}{p_i}
=
-\frac{y_i}{p_i}
\]

第二步：代入链式法则

\[
\frac{\partial J}{\partial z_j}
=
\sum_{i=1}^{K}
\left(-\frac{y_i}{p_i}\right)
\cdot
p_i(\delta_{ij}-p_j)
\]

\(p_i\) 和分母的 \(p_i\) 约掉：

\[
=
-\sum_{i=1}^{K}
y_i(\delta_{ij}-p_j)
\]

把求和拆开：

\[
=
-\sum_{i=1}^{K}y_i\delta_{ij}
+
\sum_{i=1}^{K}y_i p_j
\]

第三步：算两项

第一项：

\[
\sum_{i=1}^{K}y_i\delta_{ij}
\]

\(\delta_{ij}\) 只在 \(i=j\) 时为 1，所以这一项就是：

\[
y_j
\]

第二项：

\[
\sum_{i=1}^{K}y_i p_j
=
p_j\sum_{i=1}^{K}y_i
\]

因为 one-hot 只有一个 1，所以：

\[
\sum_{i=1}^{K}y_i=1
\]

因此第二项是：

\[
p_j
\]

第四步：合起来

\[
\frac{\partial J}{\partial z_j}
=
-y_j+p_j
\]

\[
\boxed{\frac{\partial J}{\partial z_j}=p_j-y_j}
\]

![课件中的 softmax 加交叉熵梯度总结](/daily/2026/9-15/aims5710-nn-softmax-gradient-summary.png)

课堂黑笔板书把 logits 记作 \(y\)，把 one-hot 标签记作 \(\hat y\)；本文前面为了和线性模型区分，用 \(z\) 表示 logits、用 \(y\) 表示标签。对应关系只是符号不同：

\[
\ell=\sum_i\hat y_i\log p_i,
\qquad
\nabla_z\ell=\hat y-p.
\]

本文使用最小化交叉熵 \(J=-\ell\)，所以得到

\[
\nabla_zJ=p-y.
\]

接回全连接层的结果，就是

\[
\frac{\partial J}{\partial W}
=(p-y)x^T,
\qquad
\frac{\partial J}{\partial b}
=p-y,
\qquad
\frac{\partial J}{\partial x}
=W^T(p-y).
\]

课堂黑笔板书中 softmax、全连接层和多层反向传播的关系可以在下面这张总图里一起看到：

![AIMS5710 课堂黑笔板书中的 softmax 与多层反向传播](/daily/2026/9-15/aims5710-2026-09-15-softmax-backprop-full.jpg)

![AIMS5710 白板上的 softmax 与交叉熵推导](/daily/2026/9-15/aims5710-2026-09-15-softmax-derivation-01.jpg)

![AIMS5710 白板上的 softmax 梯度展开](/daily/2026/9-15/aims5710-2026-09-15-softmax-derivation-02.jpg)

## 4. 为什么需要计算图

### 4.1 计算图是什么

计算图 是**把一个复合函数拆成一系列简单节点**。每个节点只做一件小事，比如加法、乘法、指数、损失计算。节点之间用边连接，表示数据依赖关系。

这样做的好处是：  
**前向计算**沿着图从输入到输出算一遍，得到预测和损失；  
**反向传播**沿着同一张图从输出到输入算一遍，用链式法则得到每个参数的梯度。

所以其核心价值是：**把“求导”这件事，变成沿着图逐步做局部求导，再相乘累加。**

### 4.2 线性回归的计算图表示

线性回归的预测是：

\[
\hat y = w_1x_1+w_2x_2+\cdots+w_nx_n+b
\]

损失用平方误差（L2范数，向量的欧几里得距离）：

\[
J=\lVert y-\hat y\rVert_2^2
\]

如果只有一个样本且输出是标量，它就等于：

\[
J=(y-\hat y)^2
\]

如果是向量，则：

\[
J=\sum_{i=1}^{m}(y_i-\hat y_i)^2
\]

#### 4.2.1 常数输入节点 \(x_0=1\)

为了把偏置 \(b\) 也写成“权重 × 输入”的形式，可以人为增加一个输入：

\[
x_0=1
\]

并令：

\[
w_0=b
\]

于是：

\[
w_0x_0 = w_0\cdot 1 = b
\]

原来的预测就可以统一写成：

\[
\hat y = w_0x_0+w_1x_1+\cdots+w_nx_n
\]

这样所有项都是“权重乘输入”，在计算图里可以画成很多个乘法节点，再加一个加法节点。

#### 4.2.2 线性回归的计算图

一个简单的计算图可以这样画：

```text
x0=1 ──┐
x1 ────┤
x2 ────┤──> 乘法节点 ──> 加法节点 ──> \hat y ──> 损失节点 J
...    │
xn ────┘
w0,w1,...,wn ──> 分别与对应 x 相乘
```

更具体地说：

1. 每个 \(w_i\) 和 \(x_i\) 做一个乘法，得到 \(w_ix_i\)。
2. 把所有 \(w_ix_i\) 加起来，得到 \(\hat y\)。
3. 用真实值 \(y\) 和预测 \(\hat y\) 算损失 \(J\)。

每个节点都只负责自己的局部计算，后续反向传播时，每个节点也只需要提供自己的局部导数。

### 4.3 一个简单复合函数的逐步推导

老师给了例子：

\[
u=bc,\qquad v=a+u,\qquad J=3v
\]

我们把它拆成计算图：

```text
b, c ──> 乘法节点 u = b * c
a, u ──> 加法节点 v = a + u
v ────> 乘法节点 J = 3 * v
```

#### 4.3.1 前向计算

假设：

\[
a=2,\quad b=3,\quad c=4
\]

按顺序算：

\[
u = b\cdot c = 3\times 4 = 12
\]

\[
v = a+u = 2+12 = 14
\]

\[
J = 3v = 3\times 14 = 42
\]

这就是前向计算：从输入 \(a,b,c\) 一路算出 \(J\)。

#### 4.3.2 反向传播：从 \(J\) 往回求导

我们要算 \(\frac{\partial J}{\partial b}\)。  
因为 \(b\) 通过 \(u\) 影响 \(v\)，再通过 \(v\) 影响 \(J\)，所以用链式法则：

\[
\frac{\partial J}{\partial b}
=
\frac{\partial J}{\partial v}
\cdot
\frac{\partial v}{\partial u}
\cdot
\frac{\partial u}{\partial b}
\]

现在一项一项算。

**第一项：\(\frac{\partial J}{\partial v}\)**

\[
J=3v
\]

对 \(v\) 求导：

\[
\frac{\partial J}{\partial v}=3
\]

**第二项：\(\frac{\partial v}{\partial u}\)**

\[
v=a+u
\]

对 \(u\) 求导：

\[
\frac{\partial v}{\partial u}=1
\]

**第三项：\(\frac{\partial u}{\partial b}\)**

\[
u=bc
\]

对 \(b\) 求导：

\[
\frac{\partial u}{\partial b}=c
\]

**乘起来：**

\[
\frac{\partial J}{\partial b}
=
3\times 1\times c
=
3c
\]

因为 \(c=4\)，所以：

\[
\frac{\partial J}{\partial b}=12
\]

同样可以算：

\[
\frac{\partial J}{\partial a}
=
\frac{\partial J}{\partial v}\cdot\frac{\partial v}{\partial a}
=
3\times 1 = 3
\]

\[
\frac{\partial J}{\partial c}
=
\frac{\partial J}{\partial v}\cdot\frac{\partial v}{\partial u}\cdot\frac{\partial u}{\partial c}
=
3\times 1\times b = 3b = 9
\]

### 4.4 局部梯度的概念

计算图里，每个节点只需要知道自己的**局部梯度**。

| 节点 | 公式 | 局部梯度 |
|---|---|---|
| 乘法 | \(u=bc\) | \(\frac{\partial u}{\partial b}=c,\quad \frac{\partial u}{\partial c}=b\) |
| 加法 | \(v=a+u\) | \(\frac{\partial v}{\partial a}=1,\quad \frac{\partial v}{\partial u}=1\) |
| 乘常数 | \(J=3v\) | \(\frac{\partial J}{\partial v}=3\) |

反向传播时，把上游传下来的梯度，乘以当前节点的局部梯度，再继续往下传。

例如从 \(J\) 传到 \(b\)：

1. 上游梯度：\(\frac{\partial J}{\partial v}=3\)
2. 经过加法节点：\(3\times \frac{\partial v}{\partial u}=3\times 1=3\)
3. 经过乘法节点：\(3\times \frac{\partial u}{\partial b}=3\times c=3c\)

这就是链式法则在计算图上的操作。

### 4.5 为什么计算图能避免重复计算

一个训练迭代分成两段：

1. **前向计算**：从输入到输出，算出预测和损失。中间结果 \(u,v\) 都保留下来。
2. **反向传播**：从损失到输入，用链式法则算梯度。反向时直接使用前向已经算好的中间结果，不需要重新计算。

如果没有计算图，每次求导都要把整个复合函数展开，既容易出错，又有很多重复计算。计算图把复合函数拆成节点后，每个节点只算一次，前向和反向共用同一套结构。

> 计算图是 PyTorch、TensorFlow 等自动微分框架的基础。

## 5. 全连接层梯度：按板书逐步推导

### 5.1 符号定义

先固定符号：

- 输入：\(x\in\mathbb{R}^{n\times 1}\)，是一个 \(n\) 维列向量。
- 权重：\(W\in\mathbb{R}^{C\times n}\)，有 \(C\) 行、\(n\) 列。
- 偏置：\(b\in\mathbb{R}^{C\times 1}\)，是一个 \(C\) 维列向量。
- 输出：\(y\in\mathbb{R}^{C\times 1}\)，也是一个 \(C\) 维列向量。

前向计算：

\[
y=Wx+b
\]

把第 \(i\) 个输出拆开：

\[
y_i=\sum_{j=1}^{n}w_{ij}x_j+b_i
\]

其中：

- \(w_{ij}\) 是矩阵 \(W\) 第 \(i\) 行第 \(j\) 列的元素。
- \(x_j\) 是输入向量第 \(j\) 个分量。
- \(b_i\) 是偏置向量第 \(i\) 个分量。

### 5.2 对单个权重 \(w_{ij}\) 求导

#### 5.2.1 展开第 \(i\) 个输出

\[
y_i=w_{i1}x_1+\cdots+w_{ij}x_j+\cdots+w_{in}x_n+b_i
\]

现在对 \(w_{ij}\) 求偏导。注意：求和式里只有 \(w_{ij}x_j\) 这一项含有 \(w_{ij}\)，其他项都不含。

所以：

\[
\frac{\partial y_i}{\partial w_{ij}}
=
\frac{\partial}{\partial w_{ij}}(w_{ij}x_j)
=
x_j
\]

而 \(w_{ij}\) 不会影响其他输出 \(y_r\)（\(r\neq i\)），因为其他输出用的是别的行权重。所以：

\[
\frac{\partial y_r}{\partial w_{ij}}=0\qquad(r\neq i)
\]

#### 5.2.2 用链式法则得到损失对 \(w_{ij}\) 的梯度

损失 \(J\) 通过 \(y_i\) 才能受到 \(w_{ij}\) 的影响。所以：

\[
\frac{\partial J}{\partial w_{ij}}
=
\frac{\partial J}{\partial y_i}
\cdot
\frac{\partial y_i}{\partial w_{ij}}
=
\frac{\partial J}{\partial y_i}
\cdot
x_j
\]

这里：

- \(\frac{\partial J}{\partial y_i}\) 是上游传下来的梯度，表示损失对第 \(i\) 个输出的敏感度。
- \(x_j\) 是这一层的局部导数。

---

### 5.3 对偏置 \(b_i\) 求导

因为：

\[
y_i=\cdots+b_i
\]

所以：

\[
\frac{\partial y_i}{\partial b_i}=1
\]

再次用链式法则：

\[
\frac{\partial J}{\partial b_i}
=
\frac{\partial J}{\partial y_i}
\cdot
\frac{\partial y_i}{\partial b_i}
=
\frac{\partial J}{\partial y_i}
\cdot 1
=
\frac{\partial J}{\partial y_i}
\]

把所有输出节点放回向量形式：

\[
\frac{\partial J}{\partial b}
=
\frac{\partial J}{\partial y}
\]

也就是说，偏置的梯度就是上游传回来的梯度，形状都是 \(C\times 1\)。

---

### 5.4 对输入 \(x_j\) 求导：为什么有求和

一个输入 \(x_j\) 会影响所有输出 \(y_i\)（\(i=1,\dots,C\)），因为每个 \(y_i\) 的求和式里都有 \(w_{ij}x_j\) 这一项。

所以不能只看一条路径，必须把所有路径的贡献加起来：

\[
\frac{\partial J}{\partial x_j}
=
\sum_{i=1}^{C}
\frac{\partial J}{\partial y_i}
\cdot
\frac{\partial y_i}{\partial x_j}
\]

现在算 \(\frac{\partial y_i}{\partial x_j}\)。从：

\[
y_i=\sum_{r=1}^{n}w_{ir}x_r+b_i
\]

可以看出，只有 \(r=j\) 那一项 \(w_{ij}x_j\) 与 \(x_j\) 有关，所以：

\[
\frac{\partial y_i}{\partial x_j}=w_{ij}
\]

代回去：

\[
\frac{\partial J}{\partial x_j}
=
\sum_{i=1}^{C}
\frac{\partial J}{\partial y_i}
\cdot
w_{ij}
\]

这个求和正好是矩阵 \(W^T\frac{\partial J}{\partial y}\) 的第 \(j\) 个分量。因为 \(W^T\) 的第 \(j\) 行第 \(i\) 列是 \(w_{ij}\)，所以：

![课件中的全连接层参数梯度推导](/daily/2026/9-15/aims5710-nn-fully-connected-gradient.png)

![课件中的全连接层输入梯度推导](/daily/2026/9-15/aims5710-nn-input-gradient.png)

\[
\left(W^T\frac{\partial J}{\partial y}\right)_j
=
\sum_{i=1}^{C}
w_{ij}
\frac{\partial J}{\partial y_i}
\]

因此：

\[
\frac{\partial J}{\partial x}
=
W^T\frac{\partial J}{\partial y}
\]

---

### 5.5 把标量偏导数整理成矩阵

前面已经得到：

\[
\frac{\partial J}{\partial w_{ij}}
=
\frac{\partial J}{\partial y_i}
\cdot
x_j
\]

现在看形状：

- \(\frac{\partial J}{\partial y}\) 是 \(C\times 1\) 列向量。
- \(x^T\) 是 \(1\times n\) 行向量。

它们的外积：

\[
\frac{\partial J}{\partial y}x^T
\]

形状是：

\[
(C\times 1)(1\times n)=C\times n
\]

正好和 \(W\) 的形状一致。它的第 \(i\) 行第 \(j\) 列元素是：

\[
\left(\frac{\partial J}{\partial y}x^T\right)_{ij}
=
\frac{\partial J}{\partial y_i}
\cdot
x_j
=
\frac{\partial J}{\partial w_{ij}}
\]

所以：

\[
\boxed{
\frac{\partial J}{\partial W}
=
\frac{\partial J}{\partial y}x^T
}
\]

同理：

\[
\boxed{
\frac{\partial J}{\partial b}
=
\frac{\partial J}{\partial y}
}
\]

\[
\boxed{
\frac{\partial J}{\partial x}
=
W^T\frac{\partial J}{\partial y}
}
\]

这三个公式就是全连接层反向传播的核心。

![AIMS5710 白板上的 softmax Jacobian 与全连接层梯度](/daily/2026/9-15/aims5710-2026-09-15-gradient-derivation.jpg)

---

### 5.6 多层网络中的链式法则

把每层看成一个函数：

\[
x^{(0)}
\longrightarrow
x^{(1)}
\longrightarrow
\cdots
\longrightarrow
x^{(L)}
\longrightarrow
J
\]

- \(x^{(0)}\) 是输入。
- \(x^{(1)}\) 是第一层输出，也是第二层输入，以此类推。
- \(x^{(L)}\) 是最后一层输出。
- \(J\) 是损失。

前向传播从左到右；反向传播从损失 \(J\) 向左传。

标量形式下，链式法则写成：

\[
\frac{\partial J}{\partial x^{(0)}}
=
\frac{\partial J}{\partial x^{(L)}}
\cdot
\frac{\partial x^{(L)}}{\partial x^{(L-1)}}
\cdots
\frac{\partial x^{(2)}}{\partial x^{(1)}}
\cdot
\frac{\partial x^{(1)}}{\partial x^{(0)}}
\]

向量情况下，每个普通导数换成 Jacobian 矩阵，但乘法方向不变：先用最后一层的局部导数算出上一层的上游梯度，再一层一层向左传。

![课件中的 forward 与 backpropagation 计算图](/daily/2026/9-15/aims5710-nn-forward-backpropagation.png)

实际实现时，通常不会显式构造巨大的 Jacobian，而是用**向量-雅可比积**（VJP）直接计算梯度。这也是反向传播高效的原因。

最右边的局部梯度先作用，这就是“反向”的含义：从损失开始，先算最后一层，再往前传。

---

### 5.7 小结

全连接层反向传播三个核心公式：

\[
\frac{\partial J}{\partial W}=\frac{\partial J}{\partial y}x^T,
\qquad
\frac{\partial J}{\partial b}=\frac{\partial J}{\partial y},
\qquad
\frac{\partial J}{\partial x}=W^T\frac{\partial J}{\partial y}
\]

记住形状：

- \(\frac{\partial J}{\partial y}\)：\(C\times 1\)
- \(x^T\)：\(1\times n\)
- \(\frac{\partial J}{\partial W}\)：\(C\times n\)，和 \(W\) 一致
- \(\frac{\partial J}{\partial b}\)：\(C\times 1\)，和 \(b\) 一致
- \(\frac{\partial J}{\partial x}\)：\(n\times 1\)，和 \(x\) 一致

多层网络就是把单层的这三个公式重复使用，用链式法则从后往前传。


## 6. 被麦克风遮挡的 Jacobian：从一层回传到上一层

这一部分的照片被麦克风挡住了。下面的公式不是把遮挡处当作“看见了”，而是根据同一块板书上可见的前向定义、链式法则和上下文作出的完整还原。

设第 \(l\) 层先做线性变换，再做逐元素激活：

\[
x_i^{(l)}
=\sum_{k=1}^{n_{l-1}}W_{ik}^{(l)}h_k^{(l-1)}+b_i^{(l)},
\qquad
h_j^{(l)}=g\left(x_j^{(l)}\right).
\]

其中 \(x^{(l)}\) 是 pre-activation，\(h^{(l)}\) 是 activation。先看激活函数这一步。因为 \(h_j^{(l)}\) 只依赖同一个位置的 \(x_j^{(l)}\)，所以

$$
\frac{\partial h_j^{(l)}}{\partial x_k^{(l)}}
=
\begin{cases}
g'\left(x_j^{(l)}\right),&j=k,\\
0,&j\ne k.
\end{cases}
$$

用 Kronecker delta \(\delta_{jk}\) 合并，就是

\[
\frac{\partial h_j^{(l)}}{\partial x_k^{(l)}}
=g'\left(x_j^{(l)}\right)\delta_{jk},
\qquad
\nabla_{x^{(l)}}h^{(l)}
=\operatorname{diag}\left(g'(x^{(l)})\right).
\]

### 6.1 逐元素求 \(\frac{\partial x_i^{(l)}}{\partial x_j^{(l-1)}}\)

目标是求上一层 pre-activation \(x_j^{(l-1)}\) 改变时，本层 pre-activation \(x_i^{(l)}\) 如何改变。中间变量是上一层 activation \(h^{(l-1)}\)，因此要对所有中间节点 \(h_k^{(l-1)}\) 的路径求和：

\[
\frac{\partial x_i^{(l)}}{\partial x_j^{(l-1)}}
=\sum_{k=1}^{n_{l-1}}
\frac{\partial x_i^{(l)}}{\partial h_k^{(l-1)}}
\frac{\partial h_k^{(l-1)}}{\partial x_j^{(l-1)}}.
\]

分别计算链式法则中的两项。由线性层定义

\[
x_i^{(l)}
=\sum_{r=1}^{n_{l-1}}W_{ir}^{(l)}h_r^{(l-1)}+b_i^{(l)}
\]

可知只有 \(r=k\) 的一项依赖 \(h_k^{(l-1)}\)，所以

\[
\frac{\partial x_i^{(l)}}{\partial h_k^{(l-1)}}
=W_{ik}^{(l)}.
\]

由上一层激活函数的逐元素导数，

\[
\frac{\partial h_k^{(l-1)}}{\partial x_j^{(l-1)}}
=g'\left(x_k^{(l-1)}\right)\delta_{kj}.
\]

把这两项代回：

\[
\begin{aligned}
\frac{\partial x_i^{(l)}}{\partial x_j^{(l-1)}}
&=\sum_{k=1}^{n_{l-1}}
W_{ik}^{(l)}
g'\left(x_k^{(l-1)}\right)\delta_{kj}\\
&=W_{ij}^{(l)}g'\left(x_j^{(l-1)}\right).
\end{aligned}
\]

最后一步是因为 \(\delta_{kj}\) 只在 \(k=j\) 时等于 1，求和中的其他项全部为 0。

![被麦克风遮挡的反向传播板书](/daily/2026/9-15/aims5710-2026-09-15-backprop-occluded-whiteboard.jpg)

### 6.2 写成板书采用的分母布局 Jacobian

如果把 \(\nabla_{x^{(l-1)}}x^{(l)}\) 定义为“分母变量 \(x^{(l-1)}\) 放在行、分子变量 \(x^{(l)}\) 放在列”的 Jacobian，那么它的第 \(j,i\) 个元素就是

\[
\left[\nabla_{x^{(l-1)}}x^{(l)}\right]_{ji}
=\frac{\partial x_i^{(l)}}{\partial x_j^{(l-1)}}.
\]

刚才的逐元素结果因此可以整理为

\[
\boxed{
\nabla_{x^{(l-1)}}x^{(l)}
=\operatorname{diag}\left(g'(x^{(l-1)})\right)
W^{(l)T}
}.
\]

维度检查：

\[
\underbrace{\operatorname{diag}\left(g'(x^{(l-1)})\right)}_{n_{l-1}\times n_{l-1}}
\underbrace{W^{(l)T}}_{n_{l-1}\times n_l}
=n_{l-1}\times n_l.
\]

这与分母布局下的 Jacobian 形状一致。若课堂或软件采用相反的 numerator-layout 约定，同一个局部映射会写成转置形式；关键是先固定约定，再检查每个矩阵的维度。

### 6.3 它怎样把误差传回上一层

设已经知道本层的上游梯度 \(\nabla_{x^{(l)}}J\)。继续用链式法则：

\[
\nabla_{x^{(l-1)}}J
=\nabla_{x^{(l-1)}}x^{(l)}
\nabla_{x^{(l)}}J.
\]

代入刚才的 Jacobian：

\[
\boxed{
\nabla_{x^{(l-1)}}J
=\operatorname{diag}\left(g'(x^{(l-1)})\right)
W^{(l)T}
\nabla_{x^{(l)}}J
}.
\]

逐元素看第 \(j\) 项：

\[
\frac{\partial J}{\partial x_j^{(l-1)}}
=g'\left(x_j^{(l-1)}\right)
\sum_{i=1}^{n_l}
W_{ij}^{(l)}
\frac{\partial J}{\partial x_i^{(l)}}.
\]

这就是反向传播逐层回传误差信号的核心：先用 \(W^{(l)T}\) 汇总来自本层所有输出的梯度，再逐元素乘上一层激活函数的导数。

## 7. MLP 的核心不是堆线性层，而是插入非线性

多层感知机可以看成多个全连接层的组合。若只把线性层连续相乘，最终仍然等价于一个更大的线性变换，增加层数不会增加表达非线性关系的能力。因此全连接层之间需要插入激活函数。

课件列出的几种激活函数是：

\[
\sigma(x)=\frac{1}{1+e^{-x}},
\qquad
\tanh(x)=\frac{e^x-e^{-x}}{e^x+e^{-x}},
\]

\[
\operatorname{ReLU}(x)=\max(0,x),
\qquad
\operatorname{LeakyReLU}(x)=
\begin{cases}
\alpha x,&x<0,\\
x,&x\ge 0,
\end{cases}
\]

### 7.1 从 ReLU 到 LeakyReLU：逐段求导

先看普通 ReLU：

\[
g(x)=\max(0,x)=
\begin{cases}
0,&x<0,\\
x,&x\ge0.
\end{cases}
\]

因此在 \(x<0\) 时，函数是常数 0，导数为 0；在 \(x>0\) 时，函数是 \(x\)，导数为 1：

\[
g'(x)=
\begin{cases}
0,&x<0,\\
1,&x>0.
\end{cases}
\]

\(x=0\) 处不可导，实际实现会采用约定的次梯度。ReLU 的问题是：如果某个神经元长期落在负半轴，它的梯度一直为 0，参数就很难再把它拉回有效区域。

LeakyReLU 把负半轴改成一条斜率为 \(\alpha\) 的直线：

\[
g(x)=
\begin{cases}
\alpha x,&x<0,\\
x,&x\ge0.
\end{cases}
\]

现在分两段求导。第一段 \(x<0\)：

\[
\frac{\partial g(x)}{\partial x}
=\frac{\partial(\alpha x)}{\partial x}
=\alpha.
\]

第二段 \(x>0\)：

\[
\frac{\partial g(x)}{\partial x}
=\frac{\partial x}{\partial x}
=1.
\]

所以

\[
g'(x)=
\begin{cases}
\alpha,&x<0,\\
1,&x>0.
\end{cases}
\]

只要 \(\alpha\ne0\)，负半轴就保留了非零梯度；但 \(\alpha\) 通常取小于 1 的正数。若 \(\alpha=1\)，整个函数变成线性函数，失去插入非线性的意义；若 \(\alpha>1\)，负半轴梯度大于 1，层数增加时又可能带来梯度爆炸风险。

![AIMS5710 板书中的 LeakyReLU 分段导数](/daily/2026/9-15/aims5710-2026-09-15-leakyrelu-whiteboard.jpg)

这张照片左侧仍然是上一段 softmax Jacobian 的推导；右侧才是激活函数部分：先写 \(x_j<0\) 时的导数 \(\alpha\)，再写 \(x_j>0\) 时的导数 1，最后合并成指示函数形式。这里的 \(\alpha\) 与前面线性回归里的 learning rate 只是同一个字母的不同用途，不能混为一谈。

课件用 MNIST 说明 MLP 的输入处理：原本的 32×32 图像可以展平成 1024 维向量，再交给全连接网络分类。浅层网络的最后一层可以作为分类器，前面的层逐渐把原始像素变换成更容易线性分开的表示。这里也能看出 MLP 的限制：展平会丢失二维邻域结构，而且第一层参数量会随输入尺寸快速增长。

这节课录音强调的重点不是“层数越深一定越好”，而是多层网络可以在执行分类的同时学习中间特征：早期层倾向于学习较低层次的模式，后续层再组合成更抽象的表示。这个观点是经验性的表示学习动机，不应误写成训练必然成功的保证。

## 8. MSE 与 L1：录音最后的损失函数补充

课件把 MSE/L2 loss 写成

\[
J=\frac{1}{2N}\sum_{i=1}^{N}(z^{(i)}-\hat z^{(i)})^2,
\qquad
\frac{\partial J}{\partial z^{(i)}}
=\frac{1}{N}(z^{(i)}-\hat z^{(i)}).
\]

L1 loss 使用绝对值，通常对异常值更不敏感，但在零点处需要处理不可导或次梯度问题。分类部分通常使用 softmax 与交叉熵，不能只因为 MSE 形式熟悉就把它套到所有输出上。


## 9. 深层网络中的梯度消失与梯度爆炸

录音在多层反向传播之后专门讨论了一个问题：链式法则虽然让梯度可以逐层计算，但也会把许多局部导数乘在一起。

先看最简单的标量线性网络：

\[
x^{(1)}=w^{(1)}x^{(0)},\qquad
x^{(2)}=w^{(2)}x^{(1)},\qquad
\ldots,\qquad
x^{(L)}=w^{(L)}x^{(L-1)}.
\]

连续使用链式法则：

\[
\frac{\partial x^{(L)}}{\partial x^{(0)}}
=\frac{\partial x^{(L)}}{\partial x^{(L-1)}}
\frac{\partial x^{(L-1)}}{\partial x^{(L-2)}}
\cdots
\frac{\partial x^{(1)}}{\partial x^{(0)}}
=w^{(L)}w^{(L-1)}\cdots w^{(1)}.
\]

如果每个权重的绝对值大致小于 1，乘积会随着层数增加而快速变小，早期层收到的梯度就接近 0，这叫梯度消失；如果权重的绝对值大致大于 1，乘积则可能越来越大，这叫梯度爆炸。实际网络还会叠加激活函数的导数，因此 sigmoid 等饱和激活函数也可能让局部梯度变得很小。

录音还提到计算复杂度：反向传播不是重新从头计算每一条路径，而是复用前向计算得到的中间结果，并沿计算图反向做局部链式法则。因此，理想情况下反向计算的量级与前向计算相近；但网络越深，参数和中间梯度的管理仍然会带来显著计算与存储成本，这也是 GPU 等专用硬件重要的原因。

## 10. 总结

今天把线性模型复习、多分类 softmax/交叉熵、计算图、全连接层梯度、逐层反向传播、MLP、激活函数、梯度消失/爆炸和 L1 串成了一条复习主线。
