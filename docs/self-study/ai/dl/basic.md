---
id: dl-chapter-1
title: 第1章 Basic Concepts
sidebar_label: 第1章
---
# 深度学习基础

## 第1章 数学基础

别担心，这部分不会特别硬核，只讲神经网络里真正会用到的东西。

### 1.1 线性代数 - 矩阵乘法

#### 1.1.1 向量：神经网络的基本单位

首先，**向量就是一串数字**。比如一张 28×28 的手写数字图片，可以展平成一个 784 维的向量：

$$x = \begin{bmatrix} x_1 \\ x_2 \\ \vdots \\ x_{784} \end{bmatrix}$$

- **列向量**：像上面这样竖着写
- **行向量**：$x^T = [x_1, x_2, \ldots, x_{784}]$ 横着写

为什么要区分？**因为矩阵乘法对顺序有要求！**

#### 1.1.2 矩阵乘法：神经网络的灵魂操作

假设我们有一个权重矩阵 $W$（大小 $m \times n$）和输入向量 $x$（大小 $n \times 1$）：

$$y = Wx$$

计算规则：结果 $y$ 的第 $i$ 个元素是：

$$y_i = \sum_{j=1}^{n} W_{ij} x_j$$

举个例子：

$$\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} \begin{bmatrix} 5 \\ 6 \end{bmatrix} = \begin{bmatrix} 1 \times 5 + 2 \times 6 \\ 3 \times 5 + 4 \times 6 \end{bmatrix} = \begin{bmatrix} 17 \\ 39 \end{bmatrix}$$

**几何意义**：矩阵乘法其实是一种线性变换。你可以把 $W$ 想象成一个"变换器"，把输入空间的向量 $x$ 变换到输出空间。

#### 1.1.3 在神经网络中的应用

**全连接层**（或者叫线性层）的核心操作就是：

$$h = Wx + b$$

其中 $b$ 是**偏置向量**。一个神经网络里可能有几十上百层这样的操作！

#### 1.1.4 推荐视频

- [3Blue1Brown - 线性代数的本质](https://www.bilibili.com/video/BV1ys411472E/?spm_id_from=333.1387.search.video_card.click)
- [3Blue1Brown - 微积分的本质](https://www.bilibili.com/video/BV1qW411N7FU/?spm_id_from=333.1387.search.video_card.click)
- [3Blue1Brown - 反向传播的直观理解](https://www.bilibili.com/video/BV16x411V7Qg/?spm_id_from=333.1387.search.video_card.click)

### 1.2 求导法则

#### 1.2.1 为什么要求导？

训练神经网络的核心就是：**找到让损失函数最小的参数**。怎么找？靠**梯度下降**，而梯度就是导数（或者说偏导数）。

#### 1.2.2 基本求导规则（快速回顾）

这些应该在高数课上学过，快速过一遍：

| 函数 | 导数 |
|------|------|
| $f(x) = C$ | $f'(x) = 0$ |
| $f(x) = x^n$ | $f'(x) = nx^{n-1}$ |
| $f(x) = e^x$ | $f'(x) = e^x$ |
| $f(x) = \ln x$ | $f'(x) = \frac{1}{x}$ |
| $f(x) = \sin x$ | $f'(x) = \cos x$ |

#### 1.2.3 链式法则（Chain Rule）

这个是**重中之重**！神经网络的反向传播完全依赖链式法则。

**一元函数的链式法则**：

如果 $y = f(u)$ 且 $u = g(x)$，那么：

$$\frac{dy}{dx} = \frac{dy}{du} \cdot \frac{du}{dx}$$

举个例子：

$$y = (2x + 1)^3$$

设 $u = 2x + 1$，则 $y = u^3$：

$$\frac{dy}{dx} = \frac{dy}{du} \cdot \frac{du}{dx} = 3u^2 \cdot 2 = 6(2x + 1)^2$$

#### 1.2.4 多元函数与偏导数

神经网络的损失函数通常是多元函数，比如 $L(W, b)$ 依赖于很多参数。

**偏导数**：对某一个变量求导，其他变量当常数。

$$\frac{\partial L}{\partial w_i}$$

表示 $L$ 对 $w_i$ 的偏导数。

#### 1.2.5 梯度（Gradient）

梯度就是所有偏导数组成的向量：

$$\nabla L = \begin{bmatrix} \frac{\partial L}{\partial w_1} \\ \frac{\partial L}{\partial w_2} \\ \vdots \\ \frac{\partial L}{\partial w_n} \end{bmatrix}$$

- **梯度的方向**：函数值增长最快的方向
- **梯度下降**：我们沿着梯度的反方向走，让损失函数减小

#### 1.2.6 多元链式法则

假设 $z = f(x, y)$，$x = g(t)$，$y = h(t)$，那么：

$$\frac{dz}{dt} = \frac{\partial z}{\partial x} \frac{dx}{dt} + \frac{\partial z}{\partial y} \frac{dy}{dt}$$

这就是**反向传播的数学基础**！

## 第2章 神经网络的结构

> 推荐视频：[3Blue1Brown - 神经网络的结构](https://www.bilibili.com/video/BV1bx411M7Zx/?spm_id_from=333.1387.search.video_card.click)

### 2.1 线性层（全连接层 / Fully Connected Layer）

#### 2.1.1 从感知机说起

1958 年，Rosenblatt 提出了**感知机（Perceptron）**，这是神经网络的鼻祖。它的想法超级简单：

$$y = f(W^T x + b)$$

其中：
- $x$：输入特征向量
- $W$：权重向量
- $b$：偏置（bias）
- $f$：激活函数（比如阶跃函数）

感知机能解决**线性可分**的问题（比如 AND、OR），但解决不了 **XOR 问题**。这就引出了**多层感知机（MLP）**。

#### 2.1.2 线性层的数学表达

一个线性层就是：

$$y = Wx + b$$

- **输入**：$x \in \mathbb{R}^n$（$n$ 维向量）
- **权重矩阵**：$W \in \mathbb{R}^{m \times n}$（$m$ 行 $n$ 列）
- **偏置**：$b \in \mathbb{R}^m$
- **输出**：$y \in \mathbb{R}^m$

#### 2.1.3 前向传播的计算过程

举个例子：输入是 3 维，输出是 2 维

$$y = \begin{bmatrix} w_{11} & w_{12} & w_{13} \\ w_{21} & w_{22} & w_{23} \end{bmatrix} \begin{bmatrix} x_1 \\ x_2 \\ x_3 \end{bmatrix} + \begin{bmatrix} b_1 \\ b_2 \end{bmatrix}$$

```python
import torch
import torch.nn as nn

# 定义一个线性层：输入 3 维，输出 2 维
linear = nn.Linear(in_features=3, out_features=2)

# 输入一个 batch 的数据（batch_size=4）
x = torch.randn(4, 3)  # shape: (4, 3)
y = linear(x)           # shape: (4, 2)
```

#### 2.1.4 线性层的局限性

**问题**：如果我们把多个线性层叠加起来会怎样？

$$y = W_2(W_1 x + b_1) + b_2$$

展开后发现：

$$y = (W_2 W_1)x + (W_2 b_1 + b_2) = W'x + b'$$

**结论**：无论堆叠多少层线性层，最终还是一个线性变换！

怎么办？**需要引入非线性，也就是激活函数！**

### 2.2 激活函数

**激活函数是神经网络的"灵魂"**，没有它，再深的网络也只是个线性回归。

#### 2.2.1 为什么需要激活函数？

前面我们证明了：**多层线性层 = 一层线性层**。这意味着没有激活函数的深度网络毫无意义。激活函数引入了**非线性**，让神经网络能够拟合复杂的函数。

#### 2.2.2 常见激活函数

常见的激活函数包括：

- **Sigmoid**：$\sigma(x) = \frac{1}{1 + e^{-x}}$
- **Tanh**：$\tanh(x) = \frac{e^x - e^{-x}}{e^x + e^{-x}}$
- **ReLU**：$\text{ReLU}(x) = \max(0, x)$
- **Leaky ReLU**：$\text{LeakyReLU}(x) = \max(\alpha x, x)$，其中 $\alpha$ 是小的正数（通常取 0.01）
- **ELU**：指数线性单元

  $$\text{ELU}(x) = \begin{cases} x & \text{if } x > 0 \\ \alpha(e^x - 1) & \text{if } x \leq 0 \end{cases}$$

- **SELU**：缩放指数线性单元

  $$\text{SELU}(x) = \lambda \begin{cases} x & \text{if } x > 0 \\ \alpha(e^x - 1) & \text{if } x \leq 0 \end{cases}$$

  其中 $\lambda \approx 1.0507$，$\alpha \approx 1.6733$

- **Swish**：$x \cdot \sigma(x)$

  $$\text{Swish}(x) = x \cdot \frac{1}{1 + e^{-x}}$$

- **Mish**：$x \cdot \tanh(\ln(1 + e^x))$

  $$\text{Mish}(x) = x \cdot \tanh(\ln(1 + e^x))$$

- **Softmax**：$\text{softmax}(x_i) = \frac{e^{x_i}}{\sum_{j} e^{x_j}}$

激活函数图像可参考：

<table>
<tr>
<td align="center">![Softmax](/img/dl/softmax.png)<br/>Softmax</td>
<td align="center">![Swish](/img/dl/swish.png)<br/>Swish</td>
<td align="center">![ReLU](/img/dl/relu.png)<br/>ReLU</td>
<td align="center">![Leaky ReLU](/img/dl/leakyrelu.png)<br/>Leaky ReLU</td>
</tr>
<tr>
<td align="center">![ELU](/img/dl/elu.png)<br/>ELU</td>
<td align="center">![SELU](/img/dl/selu.png)<br/>SELU</td>
<td align="center">![Mish](/img/dl/mish.png)<br/>Mish</td>
<td align="center">![PReLU](/img/dl/prelu.png)<br/>PReLU</td>
</tr>
</table>

## 第3章 梯度下降与反向传播

### 3.1 梯度下降：沿着山坡往下走

#### 3.1.1 直观理解

想象你在一座山上蒙着眼睛，想走到山底（最低点）。你会怎么做？

1. 感受脚下的坡度
2. 朝着最陡的下坡方向走一小步
3. 重复上述过程

这就是**梯度下降的思想**！

#### 3.1.2 数学表达

假设我们要最小化损失函数 $L(w)$：

$$w_{\text{new}} = w_{\text{old}} - \eta \nabla L(w_{\text{old}})$$

其中：
- $\nabla L$：损失函数的梯度（指向函数增长最快的方向）
- $\eta$：学习率（步长），控制每次走多远
- 负号：沿着梯度的反方向走（下山而不是上山）

### 3.2 三种梯度下降

#### 3.2.1 批量梯度下降（Batch Gradient Descent, BGD）

每次更新参数时，用所有训练样本计算梯度：

$$w = w - \eta \frac{1}{N} \sum_{i=1}^{N} \nabla L_i(w)$$

- **优点**：稳定，收敛平滑
- **缺点**：慢！如果数据集很大，每次更新要算 $N$ 个样本的梯度

#### 3.2.2 随机梯度下降（Stochastic Gradient Descent, SGD）

每次只用一个样本计算梯度：

$$w = w - \eta \nabla L_i(w)$$

- **优点**：快！每次更新只需要一个样本
- **缺点**：不稳定，损失函数震荡

#### 3.2.3 小批量梯度下降（Mini-batch GD）

每次用一小批样本（比如 32、64、128）计算梯度：

$$w = w - \eta \frac{1}{B} \sum_{i=1}^{B} \nabla L_i(w)$$

其中 $B$ 是 batch size。

- **优点**：结合了前两者的优点，既快又稳定
- **这是现在的标准做法！**
- **一定要明白，是对数据分布求对应的导数！**

这里可以看强化学习那一部分对这种 SGD 的解释：[强化学习章节 6](../../rl/chapter-6.md)

### 3.3 反向传播（Backpropagation）

**问题**：神经网络有成千上万个参数，怎么计算每个参数的梯度？

**答案**：**反向传播算法**！利用链式法则，从输出层往回算。

#### 3.3.1 计算图

把神经网络画成一个计算图，每个节点是一个操作。

举个简单例子：

$$L = (w_1 x_1 + w_2 x_2 + b)^2$$

计算图：

```
x1 --- [* w1]---> a ---> [+] ---> z ---> [^2] ---> L
x2 --- [* w2]---> b -----^
[+ b] ---------------^
```

#### 3.3.2 前向传播（Forward Pass）

从输入到输出，计算每一层的值：

$$a_1 = w_1 x_1$$

$$a_2 = w_2 x_2$$

$$z = a_1 + a_2 + b$$

$$L = z^2$$

#### 3.3.3 反向传播（Backward Pass）

从输出往回，用链式法则计算梯度：

$$\frac{\partial L}{\partial z} = 2z$$

$$\frac{\partial L}{\partial a_1} = \frac{\partial L}{\partial z} \cdot \frac{\partial z}{\partial a_1} = 2z \cdot 1 = 2z$$

$$\frac{\partial L}{\partial a_2} = \frac{\partial L}{\partial z} \cdot \frac{\partial z}{\partial a_2} = 2z \cdot 1 = 2z$$

$$\frac{\partial L}{\partial w_1} = \frac{\partial L}{\partial a_1} \cdot \frac{\partial a_1}{\partial w_1} = 2z \cdot x_1$$

$$\frac{\partial L}{\partial w_2} = \frac{\partial L}{\partial a_2} \cdot \frac{\partial a_2}{\partial w_2} = 2z \cdot x_2$$

$$\frac{\partial L}{\partial b} = \frac{\partial L}{\partial z} \cdot \frac{\partial z}{\partial b} = 2z \cdot 1 = 2z$$

**关键点**：每次算梯度时，都复用前面已经算好的中间结果！

#### 3.3.4 两层神经网络的反向传播推导

假设网络结构：

$$z^{[1]} = W^{[1]} x + b^{[1]}$$

$$a^{[1]} = \text{ReLU}(z^{[1]})$$

$$z^{[2]} = W^{[2]} a^{[1]} + b^{[2]}$$

$$y = \text{softmax}(z^{[2]})$$

$$L = \text{crossEntropy}(y, \hat{y})$$

反向传播步骤：

1. **计算输出层梯度**：

$$\frac{\partial L}{\partial z^{[2]}} = y - \hat{y}$$

2. **计算第二层权重梯度**：

$$\frac{\partial L}{\partial W^{[2]}} = \frac{\partial L}{\partial z^{[2]}} (a^{[1]})^T$$

3. **向前传播梯度**：

$$\frac{\partial L}{\partial a^{[1]}} = (W^{[2]})^T \frac{\partial L}{\partial z^{[2]}}$$

4. **通过 ReLU**：

$$\frac{\partial L}{\partial z^{[1]}} = \frac{\partial L}{\partial a^{[1]}} \odot \mathbf{1}_{z^{[1]} > 0}$$

其中 $\odot$ 表示逐元素相乘，$\mathbf{1}_{z^{[1]} > 0}$ 是指示函数。

5. **计算第一层权重梯度**：

$$\frac{\partial L}{\partial W^{[1]}} = \frac{\partial L}{\partial z^{[1]}} x^T$$

> 推荐视频：[3Blue1Brown 梯度下降法](https://www.bilibili.com/video/BV1Ux411j7ri/?spm_id_from=333.1387.search.video_card.click)

代码示例（PyTorch 自动求导）：

```python
import torch

# 定义参数
w = torch.tensor([1.0], requires_grad=True)
x = torch.tensor([2.0])
# 前向传播
y = w * x
loss = y ** 2
# 反向传播（PyTorch 自动计算梯度！）
loss.backward()
print(f"梯度 dL/dw = {w.grad}")  # 输出: 8.0
```

### 3.4 训练相关的术语

#### 3.4.1 损失函数（Loss Function）

衡量模型预测和真实标签之间差距的函数。常见的有：

- **均方误差（MSE）**：回归问题常用（并且 MLE 可以从数学上证明 = MSE）

$$L = \frac{1}{N} \sum_{i=1}^{N} (y_i - \hat{y}_i)^2$$

**最大似然估计（Maximum Likelihood Estimation, MLE）**：

$$\text{MLE} = \arg\max_x P[(a_1, b_1), (a_2, b_2), \ldots | x] = \arg\max_x \exp\left(-\frac{\|Ax - b\|^2}{2\sigma^2}\right) = \arg\min_x \|Ax - b\|^2$$

**MSE = MLE with Gaussian noise assumption**

- **交叉熵（Cross Entropy）**：分类问题常用

$$L = -\sum_{i=1}^{N} y_i \log(\hat{y}_i)$$

#### 3.4.2 优化器（Optimizer）

用来更新参数的算法。常见的有：

- **SGD（Stochastic Gradient Descent）**：最基础的
- **Adam**：目前最流行的，自动调整学习率
- **AdamW**：Adam 的改进版，现代大模型常用

#### 3.4.3 学习率（Learning Rate, lr）

控制参数更新的步长。太大容易震荡，太小收敛慢。通常设在 $10^{-3}$ 到 $10^{-4}$ 之间。

$$w_{\text{new}} = w_{\text{old}} - \text{lr} \cdot \nabla L$$

#### 3.4.4 Epoch、Batch、Iteration

- **Epoch**：把整个训练集过一遍叫一个 epoch
- **Batch**：一次喂给模型的样本数（比如 32、64、128）
- **Iteration**：一次参数更新

举个例子：训练集有 1000 个样本，batch size = 100
- 1 个 epoch = 10 个 iteration
- 训练 5 个 epoch = 50 个 iteration

### 3.5 模型泛化相关的术语

#### 3.5.1 过拟合（Overfitting）与欠拟合（Underfitting）

- **欠拟合**：模型太简单，训练集和测试集都表现差（high bias）
- **过拟合**：模型太复杂，训练集表现好但测试集差（high variance）

#### 3.5.2 正则化（Regularization）

防止过拟合的技巧：

- **L2 正则化（Weight Decay）**：给损失函数加一项 $\lambda \|w\|^2$，让权重不要太大

$$L_{\text{total}} = L + \lambda \|w\|^2$$

- **Dropout**：训练时随机"关闭"一些神经元
- **数据增强（Data Augmentation）**：对图片旋转、翻转、裁剪等，增加训练样本多样性

## 第4章 现代的网络结构

### 4.1 MLP（多层感知机）

![MLP网络结构示意图](/img/dl/mlp.png)

#### 4.1.1 MLP 的结构

一个典型的 MLP 包含：
- **输入层**：接收原始数据
- **多个隐藏层**：每层 = 线性变换 + 激活函数
- **输出层**：产生最终预测

数学表达：

$$h_1 = \sigma(W_1 x + b_1)$$

$$h_2 = \sigma(W_2 h_1 + b_2)$$

$$\vdots$$

$$y = W_L h_{L-1} + b_L$$

#### 4.1.2 万能逼近定理（Universal Approximation Theorem）

理论上，只要隐藏层足够宽，一个单隐藏层的 MLP 就能逼近任意连续函数！

但实践中，我们更倾向于用 **"深而窄"** 的网络，而不是 **"浅而宽"** 的网络。为什么？
- 深层网络能学到层次化的特征表示
- 参数更少，更容易训练

#### 4.1.3 代码示例

```python
import torch
import torch.nn as nn

class MLP(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super(MLP, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, output_dim)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)  # 输出层不加激活函数
        return x

# 使用示例
model = MLP(input_dim=784, hidden_dim=256, output_dim=10)
x = torch.randn(32, 784)  # batch_size=32
output = model(x)  # shape: (32, 10)
```

#### 4.1.4 MLP 的应用场景

- 表格数据（比如房价预测、信用评分）
- 简单的分类/回归任务
- 作为其他网络的组件（比如 Transformer 里的 FFN）

**缺点是什么？** 对于图像、文本这种有空间/时间结构的数据，MLP 效果不太好。这就引出了 **CNN**。

### 4.2 CNN（卷积神经网络）

CNN 是计算机视觉的基石，2012 年 AlexNet 横空出世后，深度学习彻底火了。

#### 4.2.1 从连续卷积到离散卷积

**连续卷积的定义**（信号处理中）：

$$(f * g)(t) = \int_{-\infty}^{\infty} f(\tau) g(t - \tau) d\tau$$

**离散卷积**（用在图像上）：

$$(I * K)(i, j) = \sum_{m} \sum_{n} I(i + m, j + n) K(m, n)$$

其中 $I$ 是图像，$K$ 是卷积核（kernel）。

实际上，深度学习里用的是**互相关（cross-correlation）**，但大家习惯叫它卷积：

$$(I \star K)(i, j) = \sum_{m} \sum_{n} I(i + m, j + n) K(m, n)$$

![卷积核示意图](/img/dl/convolution-kernel.png)

#### 4.2.2 卷积层的工作原理

**卷积核（Filter/Kernel）**：

一个卷积核就是一个小矩阵，比如 3×3 或 5×5。它在图像上滑动，每次计算一个位置的加权和。

举个例子，一个 3×3 的卷积核：

$$\begin{bmatrix} -1 & -1 & -1 \\ 0 & 0 & 0 \\ 1 & 1 & 1 \end{bmatrix}$$

这个卷积核可以检测**水平边缘**！

**步长（Stride）**：

卷积核每次移动几个像素。**stride=1** 表示每次移动 1 个像素，**stride=2** 表示跳着走。

**填充（Padding）**：

在图像边缘填充 0，让卷积后的特征图尺寸不变。

**输出尺寸计算**：

$$\text{output\_size} = \frac{\text{input\_size} - \text{kernel\_size} + 2 \times \text{padding}}{\text{stride}} + 1$$

#### 4.2.3 池化层（Pooling）

池化层用来降低特征图的空间分辨率。

- **Max Pooling**：取局部区域的最大值

$$\text{MaxPool}(R) = \max_{(i,j) \in R} I(i, j)$$

- **Average Pooling**：取平均值

$$\text{AvgPool}(R) = \frac{1}{|R|} \sum_{(i,j) \in R} I(i, j)$$

其中 $R$ 是池化窗口区域。

![感受野示意图](/img/dl/receptive-field.png)

#### 4.2.4 感受野（Receptive Field）

感受野是指卷积神经网络中，某一层特征图上的一个点，对应输入图像上的区域大小。感受野越大，看到的原始图像范围就越大。

#### 4.2.5 CNN 的三大优势

1. **局部连接（Local Connectivity）**

   每个神经元只连接输入的一小块区域，而不是全部。**大大减少了参数量**。

2. **权值共享（Weight Sharing）**

   同一个卷积核在整张图片上共享参数。一个 3×3 卷积核只有 9 个参数！

3. **平移不变性（Translation Invariance）**

   不管猫在图片的左上角还是右下角，CNN 都能识别出来。

#### 4.2.6 经典 CNN 架构简介



##### LeNet-5
![LeNet](/img/dl/lenet.png)


**LeNet** 是最早的卷积神经网络之一。1998年，**Yan LeCun** 第一次将 LeNet 卷积神经网络应用到图像分类上，在手写数字识别任务中取得了巨大成功。LeNet 通过连续使用卷积和池化层的组合提取图像特征，其架构如所图示，这里展示的是作者论文中的 **LeNet-5** 模型：

上图就是 LeNet 网络的结构模型，其中包含：

- **第一模块**：包含 5×5 的 6 通道卷积和 2×2 的池化。卷积提取图像中包含的特征模式（激活函数使用 sigmoid），图像尺寸从 32 减小到 28。经过池化层可以降低输出特征图对空间位置的敏感性，图像尺寸减到 14。

- **第二模块**：和第一模块尺寸相同，通道数由 6 增加为 16。卷积操作使图像尺寸减小到 10，经过池化后变成 5。

- **第三模块**：包含 5×5 的 120 通道卷积。卷积之后的图像尺寸减小到 1，但是通道数增加为 120。将经过第 3 次卷积提取到的特征图输入到全连接层。第一个全连接层的输出神经元的个数是 64，第二个全连接层的输出神经元个数是分类标签的类别数，对于手写数字识别其大小是 10。然后使用 **Softmax** 激活函数即可计算出每个类别的预测概率。

虽然 LeNet 网络模型对手写数字的识别取得的效果很明显，因为手写数字的输入图片尺寸仅为 28×28，但是当输入图片的尺寸过大时（224×224），它的效果就不尽人意了。

##### AlexNet
![AlexNet](/img/dl/alexnet.png)


在 2012 年，**Alex Krizhevsky** 等人提出的 **AlexNet** 以很大优势获得了 ImageNet 比赛的冠军。这一成果极大的激发了产业界对神经网络的兴趣，开创了使用深度神经网络解决图像问题的途径，随后也在这一领域涌现出越来越多的优秀成果。

AlexNet 与 LeNet 相比，具有更深的网络结构，包含 **5 层卷积和 3 层全连接**，同时使用了如下三种方法改进模型的训练过程：

1. **数据增广**：深度学习中常用的一种处理方式，通过对训练随机加一些变化，比如平移、缩放、裁剪、旋转、翻转或者增减亮度等，产生一系列跟原始图片相似但又不完全相同的样本，从而扩大训练数据集。通过这种方式，可以随机改变训练样本，避免模型过度依赖于某些属性，能从一定程度上抑制过拟合。

2. **使用 Dropout 抑制过拟合**

3. **使用 ReLU 激活函数减少梯度消失现象**

AlexNet 的具体结构如图：

其中有四个模块：

- **第一模块**：包含了 11×11 步长为 4 的 96 通道卷积以及一个最大池化

- **第二模块**：包含了 5×5 步的 256 通道卷积以及一个最大池化

- **第三模块**：包含了两个 3×3 的 384 通道以及一个 3×3 的 256 通道的卷积，后面加一个最大池化

- **第四模块**：包含了两个 4096 通道输入的全连接层，每个全连接层后面加一个 Dropout 层来抑制过拟合，以及还有最后一个 1000 通道的全连接层
##### VGG

![VGG](/img/dl/vgg.png)

**VGG** 是当前最流行的 CNN 模型之一，2014 年由 **Simonyan** 和 **Zisserman** 提出，其命名来源于论文作者所在的实验室 **Visual Geometry Group**。AlexNet 模型通过构造多层网络，取得了较好的效果，但是并没有给出深度神经网络设计的方向。VGG 通过使用一系列大小为 **3×3 的小尺寸卷积核**和 pooling 层构造深度卷积神经网络，并取得了较好的效果。VGG 模型因为结构简单、应用性极强而广受研究者欢迎，尤其是它的网络结构设计方法，为构建深度神经网络提供了方向。

下图是 **VGG-16** 的网络结构示意图，有 **13 层卷积和 3 层全连接层**。VGG 网络的设计严格使用 3×3 的卷积层和池化层来提取特征，并在网络的最后面使用三层全连接层，将最后一层全连接层的输出作为分类的预测。在 VGG 中每层卷积将使用 **ReLU** 作为激活函数，在全连接层之后添加 **dropout** 来抑制过拟合。

使用小的卷积核能够有效地减少参数的个数，使得训练和测试变得更加有效。比如使用两层 3×3 卷积层，可以得到感受野为 5 的特征图，而比使用 5×5 的卷积层需要更少的参数。由于卷积核比较小，可以堆叠更多的卷积层，加深网络的深度，这对于图像分类任务来说是有利的。**VGG 模型的成功证明了增加网络的深度，可以更好的学习图像中的特征模式**。


##### GoogLeNet
![GoogLeNet](/img/dl/googlenet.png)

**GoogLeNet** 是 2014 年 ImageNet 比赛的冠军，它的主要特点是网络不仅有深度，还在横向上具有 **"宽度"**。由于图像信息在空间尺寸上的巨大差异，如何选择合适的卷积核大小来提取特征就显得比较困难了。空间分布范围更广的图像信息适合用较大的卷积核来提取其特征，而空间分布范围较小的图像信息则适合用较小的卷积核来提取其特征。为了解决这个问题，GoogLeNet 提出了一种被称为 **Inception 模块**的方案。如下图所示：

其中（a）是 Inception 模块的设计思想，使用 3 个不同大小的卷积核对输入图片进行卷积操作，并附加最大池化，将这 4 个操作的输出沿着通道这一维度进行拼接，构成的输出特征图将会包含经过不同大小的卷积核提取出来的特征。Inception 模块采用**多通路（multi-path）**的设计形式，每个支路使用不同大小的卷积核，最终输出特征图的通道数是每个支路输出通道数的总和，这将会导致输出通道数变得很大，尤其是使用多个 Inception 模块串联操作的时候，模型参数量会变得非常大。

为了减小参数量，Inception 模块使用了图(b)中的设计方式，在每个 3×3 和 5×5 的卷积层之前，增加 **1×1 的卷积层**来控制输出通道数；在最大池化层后面增加 1×1 卷积层减小输出通道数。基于这一设计思想，形成了上图(b)中所示的结构。

GoogLeNet 的架构如下图所示，在主体卷积部分中使用 **5 个模块（block）**，每个模块之间使用步幅为 2 的 3×3 最大池化层来减小输出高宽。

其中：

- **第一模块**：使用一个 64 通道的 7×7 卷积层

- **第二模块**：使用 2 个卷积层：首先是 64 通道的 1×1 卷积层，然后是将通道增大 3 倍的 3×3 卷积层

- **第三模块**：串联 2 个完整的 Inception 块

- **第四模块**：串联了 5 个 Inception 块

- **第五模块**：串联了 2 个 Inception 块

第五模块的后面紧跟输出层，使用**全局平均池化层**来将每个通道的高和宽变成 1，最后接上一个输出个数为标签类别数的全连接层。

并且：在原作者的论文中添加了图中所示的 **softmax1** 和 **softmax2** 两个辅助分类器，如下图所示，训练时将三个分类器的损失函数进行加权求和，以缓解梯度消失现象。这里的程序作了简化，没有加入辅助分类器。

##### ResNet

![ResNet-50](/img/dl/resnet-50.png)
**ResNet** 是 2015 年 ImageNet 比赛的冠军，将图像分类识别错误率降低到了 **3.6%**，这个结果甚至超出了正常人眼识别的精度。

通过前面几个经典模型学习，我们可以发现随着深度学习的不断发展，模型的层数越来越多，网络结构也越来越复杂。那么是否加深网络结构，就一定会得到更好的效果呢？从理论上来说，假设新增加的层都是恒等映射，只要原有的层学出跟原模型一样的参数，那么深模型结构就能达到原模型结构的效果。换句话说，原模型的解只是新模型的解的子空间，在新模型解的空间里应该能找到比原模型解对应的子空间更好的结果。但是实践表明，增加网络的层数之后，训练误差往往不降反升。

**Kaiming He** 等人提出了残差网络 **ResNet** 来解决上述问题，其基本思想如下图所示。

(a)：表示增加网络的时候，将 $x$ 映射成 $y$ 输出。

$$y = F(x)$$

(b)：对(a)作了改进，输出：

$$y = F(x) + x$$

这时不是直接学习输出特征 $y$ 的表示，而是学习**残差** $F(x) = y - x$。如果想学习出原模型的表示，只需将 $F(x)$ 的参数全部设置为 0，则 $y = x$ 是恒等映射。$F(x) = y - x$ 也叫做**残差项**，如果 $x \to y$ 的映射接近恒等映射，(b)中通过学习残差项也比(a)学习完整映射形式更加容易。

(b)的结构是残差网络的基础，这种结构也叫做**残差块（residual block）**。输入 $x$ 通过**跨层连接（skip connection）**，能更快的向前传播数据，或者向后传播梯度。

下图表示出了 **ResNet-50** 的结构，一共包含 **49 层卷积和 1 层全连接**，所以被称为 ResNet-50。
#### 4.2.7 代码示例

```python
import torch.nn as nn

class SimpleCNN(nn.Module):
    def __init__(self):
        super(SimpleCNN, self).__init__()
        
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 10)
        self.relu = nn.ReLU()

    def forward(self, x):
        # x shape: (batch, 1, 28, 28)
        x = self.relu(self.conv1(x))  # -> (batch, 32, 28, 28)
        x = self.pool(x)               # -> (batch, 32, 14, 14)
        x = self.relu(self.conv2(x))  # -> (batch, 64, 14, 14)
        x = self.pool(x)               # -> (batch, 64, 7, 7)
        x = x.view(-1, 64 * 7 * 7)    # flatten
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x
```

### 4.3 RNN 和 LSTM

RNN 是处理序列数据的利器，但它有个致命缺陷：**梯度消失**。**LSTM** 就是来解决这个问题的。

#### 4.3.1 RNN 的基本结构

**为什么需要 RNN？**

MLP 和 CNN 都假设输入是固定长度的，但很多数据是序列：
- **文本**："今天天气真不错"（长度可变）
- **语音**：一段录音（长度可变）
- **时间序列**：股票价格（长度可变）

**RNN 的核心思想**：维护一个隐藏状态 $h_t$，在处理序列时不断更新

$$h_t = \tanh(W_{hh} h_{t-1} + W_{xh} x_t + b_h)$$

$$y_t = W_{hy} h_t + b_y$$

其中：
- $h_t$：时刻 $t$ 的隐藏状态
- $x_t$：时刻 $t$ 的输入
- $y_t$：时刻 $t$ 的输出
- $W_{hh}$、$W_{xh}$、$W_{hy}$：权重矩阵
- $b_h$、$b_y$：偏置向量

![RNN结构示意图](/img/dl/rnn.png)

**时间展开（Unrolling in Time）**：

虽然 RNN 看起来有循环，但我们可以把它"展开"成一个很长的前馈网络：

```
x1 -> [RNN] -> h1 -> [RNN] -> h2 -> [RNN] -> h3 -> ...
↓             ↓             ↓
y1            y2            y3
```

#### 4.3.2 RNN 的问题：梯度消失和梯度爆炸

反向传播时，梯度要沿着时间步往回传。假设序列长度是 $T$，梯度会连乘 $T$ 次：

$$\frac{\partial L}{\partial h_1} = \prod_{t=1}^{T} \frac{\partial h_{t+1}}{\partial h_t} \cdot \frac{\partial L}{\partial h_T}$$

- 如果每个 $\frac{\partial h_{t+1}}{\partial h_t}$ 小于 1，连乘 $T$ 次后会接近 0（**梯度消失**）
- 如果大于 1，会指数爆炸（**梯度爆炸**）

**结果**：RNN 很难学到**长期依赖（long-term dependencies）**


#### 4.3.3 LSTM 的结构

**LSTM (Long Short-Term Memory)** 在 1997 年被提出，专门解决梯度消失问题。

**LSTM 的核心**：引入**细胞状态** $c_t$，用**门控机制（gate）**来控制信息流动

**三个门**：

1. **遗忘门（Forget Gate）**：决定丢弃多少旧信息

$$f_t = \sigma(W_f \cdot [h_{t-1}, x_t] + b_f)$$

遗忘门决定让那些信息继续通过这个 cell，以上一单元的输出 $h_{t-1}$ 和本单元的输入 $x_t$ 为输入的 sigmoid 函数，为 $C_{t-1}$ 中的每一项产生一个在 [0,1] 内的值，来控制上一单元状态被遗忘的程度。

2. **输入门（Input Gate）**：决定存储多少新信息

$$i_t = \sigma(W_i \cdot [h_{t-1}, x_t] + b_i)$$

$$\tilde{C}_t = \tanh(W_C \cdot [h_{t-1}, x_t] + b_C)$$

传入门决定让多少新的信息加入到 cell 状态中来，再把 cell 状态从 $C_{t-1}$ 更新为 $C_t$。实现这个需要包括两个步骤：

首先 input gate layer 的 sigmoid 层决定哪些信息需要更新；一个 tanh 层生成一个向量，也就是备选的用来更新的内容 $\tilde{C}_t$。

把 cell 状态从 $C_{t-1}$ 更新为 $C_t$：首先我们把旧的状态 $C_{t-1}$ 和 $f_t$ 相乘，就是遗忘后保留的部分信息；然后加上 $i_t \odot \tilde{C}_t$。这部分信息就是我们要添加的新内容。

3. **输出门（Output Gate）**：决定输出什么

$$o_t = \sigma(W_o \cdot [h_{t-1}, x_t] + b_o)$$

输出主要是依赖于 cell 的状态 $C_t$ 和经过一个过滤的处理。首先用一个 sigmoid 层的计算结果决定将 $C_t$ 中的哪部分信息输出。再把 $C_t$ 用一个 tanh 层把数值都归到 -1 和 1 之间，最后把 tanh 层的输出和 sigmoid 层计算出来的权重相乘以得到输出结果。

**细胞状态更新**：

$$C_t = f_t \odot C_{t-1} + i_t \odot \tilde{C}_t$$

**隐藏状态更新**：

$$h_t = o_t \odot \tanh(C_t)$$

![LSTM结构示意图](/img/dl/lstm.png)

![LSTM门控机制示意图](/img/dl/lstm-gate.png)

**为什么 LSTM 能解决梯度消失？**

细胞状态 $c_t$ 是**加法更新**的，梯度可以直接流过，不会连乘！
#### 4.3.4 GRU 简介

**GRU (Gated Recurrent Unit)** 是 LSTM 的简化版，只有两个门：
- **更新门（Update Gate）**
- **重置门（Reset Gate）**

参数更少，训练更快，效果和 LSTM 差不多。它把 LSTM 中的细胞状态和隐藏状态进行了合并，最后模型比标准 LSTM 结构简单。

![GRU结构示意图](/img/dl/gru.png)

**GRU 的数学表达**：

**重置门（Reset Gate）**：

$$r_t = \sigma(W_r \cdot [h_{t-1}, x_t] + b_r)$$

**更新门（Update Gate）**：

$$z_t = \sigma(W_z \cdot [h_{t-1}, x_t] + b_z)$$

**候选隐藏状态**：

$$\tilde{h}_t = \tanh(W \cdot [r_t \odot h_{t-1}, x_t] + b)$$

**隐藏状态更新**：

$$h_t = (1 - z_t) \odot h_{t-1} + z_t \odot \tilde{h}_t$$

其中，$r_t$ 表示重置门，$z_t$ 表示更新门。重置门决定是否将之前的状态忘记。（作用相当于合并了 LSTM 中的遗忘门和传入门）当 $r_t$ 趋于 0 的时候，前一个时刻的状态信息 $h_{t-1}$ 会被忘掉，隐藏状态 $\tilde{h}_t$ 会被重置为当前输入的信息。更新门决定是否要将隐藏状态更新为新的状态 $\tilde{h}_t$（作用相当于 LSTM 中的输出门）。

##### 4.3.4.1 GRU 与 LSTM 的对比

与 LSTM 相比：

1. **GRU 少一个门**，同时少了细胞状态 $C_t$

2. 在 LSTM 中，通过遗忘门和传入门控制信息的保留和传入；GRU 则通过重置门来控制是否要保留原来隐藏状态的信息，但是不再限制当前信息的传入。

3. 在 LSTM 中，虽然得到了新的细胞状态 $C_t$，但是还不能直接输出，而是需要经过一个过滤的处理：$h_t = o_t \odot \tanh(C_t)$；同样，在 GRU 中，虽然我们也得到了新的隐藏状态 $\tilde{h}_t$，但是还不能直接输出，而是通过更新门来控制最后的输出：$h_t = (1 - z_t) \odot h_{t-1} + z_t \odot \tilde{h}_t$

#### 4.3.5 代码示例

```python
import torch.nn as nn

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        lstm_out, (h_n, c_n) = self.lstm(x)
        # lstm_out shape: (batch, seq_len, hidden_size)
        # 取最后一个时间步的输出
        out = self.fc(lstm_out[:, -1, :])
        return out
```

### 4.4 GNN（图神经网络）

**图（Graph）**是一种非常通用的数据结构：社交网络、分子结构、知识图谱都可以用图表示。**GNN** 就是处理图数据的神经网络。

#### 4.4.1 图的基本概念

一个图 $G = (V, E)$ 包含：
- **节点（Vertices）**：$V = \{1, 2, \ldots, n\}$
- **边（Edges）**：$E \subseteq \{(i, j) : i, j \in V\}$

**邻接矩阵（Adjacency Matrix）**：

$$A_{ij} = \begin{cases} 1 & \text{if } (i, j) \in E \\ 0 & \text{otherwise} \end{cases}$$

每个节点可以有特征向量 $x_i \in \mathbb{R}^d$，所有节点的特征可以组成特征矩阵 $X \in \mathbb{R}^{n \times d}$。

#### 4.4.2 Spatial GNN

**Spatial 方法的核心思想**：聚合邻居节点的信息

**消息传递框架（Message Passing）**：

1. **消息聚合（Aggregate）**：

$$m_i = \text{AGGREGATE}\{h_j : j \in \mathcal{N}(i)\}$$

其中 $\mathcal{N}(i)$ 表示节点 $i$ 的邻居集合。

2. **节点更新（Update）**：

$$h_i^{(l+1)} = \text{UPDATE}(h_i^{(l)}, m_i)$$

**GCN（Graph Convolutional Network）**：

最经典的 GNN 模型，公式很简洁：

$$H^{(l+1)} = \sigma(\tilde{D}^{-\frac{1}{2}} \tilde{A} \tilde{D}^{-\frac{1}{2}} H^{(l)} W^{(l)})$$

其中 $\tilde{A} = A + I$（加自环），$\tilde{D}$ 是度矩阵，$D_{ii} = \sum_j \tilde{A}_{ij}$。

**GraphSAGE**：

采样邻居，而不是聚合所有邻居（适合大规模图）

$$h_i^{(l+1)} = \sigma(W^{(l)} \cdot \text{CONCAT}(h_i^{(l)}, \text{AGGREGATE}\{h_j^{(l)} : j \in \mathcal{N}(i)\}))$$

**GAT（Graph Attention Network）**：

用注意力机制动态计算邻居的权重

$$e_{ij} = \text{LeakyReLU}(a^T [W h_i || W h_j])$$

$$\alpha_{ij} = \frac{\exp(e_{ij})}{\sum_{k \in \mathcal{N}(i)} \exp(e_{ik})}$$

$$h_i' = \sigma\left(\sum_{j \in \mathcal{N}(i)} \alpha_{ij} W h_j\right)$$

其中 $a$ 是注意力参数向量，$||$ 表示拼接操作。


#### 4.4.3 Spectral GNN

**Spectral 方法**基于图信号处理理论，用到一些图论知识。

**图拉普拉斯矩阵（Graph Laplacian）**：

$$L = D - A$$

其中 $D$ 是度矩阵，$A$ 是邻接矩阵。

**归一化拉普拉斯矩阵**：

$$L_{\text{sym}} = I - D^{-\frac{1}{2}} A D^{-\frac{1}{2}}$$

**谱域卷积的想法**：

1. 对图信号做傅里叶变换（特征分解）
2. 在谱域做卷积（相当于滤波）
3. 逆变换回来

**ChebNet** 用切比雪夫多项式近似谱卷积，**GCN 是 ChebNet 的一阶近似**。

**Spatial 与 Spectral 的联系**：

GCN 可以从两个角度推导出来！Spectral 提供了理论基础，Spatial 提供了直观理解。

#### 4.4.4 异构图

**异构图（Heterogeneous Graph）**：节点和边有不同的类型

举个例子：学术网络
- **节点类型**：论文、作者、会议
- **边类型**：写作、发表、引用

**元路径（Meta-path）**：

在异构图上定义的路径模板，比如 "作者-论文-会议"

**HAN（Heterogeneous Attention Network）**：对不同类型的邻居用不同的注意力机制

**HGT（Heterogeneous Graph Transformer）**：

结合 Transformer 和异构图，处理大规模异构图

#### 4.4.5 代码示例

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class GCNLayer(nn.Module):
    def __init__(self, in_features, out_features):
        super(GCNLayer, self).__init__()
        self.linear = nn.Linear(in_features, out_features)

    def forward(self, X, A):
        # X: (N, in_features), A: (N, N) adjacency matrix
        # 添加自环并归一化
        A_hat = A + torch.eye(A.size(0), device=A.device)
        D_hat = torch.diag(A_hat.sum(1))
        D_inv_sqrt = torch.pow(D_hat, -0.5)
        D_inv_sqrt[torch.isinf(D_inv_sqrt)] = 0.
        A_norm = D_inv_sqrt @ A_hat @ D_inv_sqrt

        # GCN操作
        out = A_norm @ X
        out = self.linear(out)
        return F.relu(out)
```

![GCN结构示意图](/img/dl/gcn.png)

> **提示**：接下来就该讲 Attention 啦，请移步 `./transformer.md`

## 第5章 现代视觉领域

### 5.1 U-Net

**U-Net** 最初是为医学图像分割设计的，现在已经成为图像分割的标准架构。

**U-Net 采用对称的 Encoder-Decoder 结构**，形状像字母 "U"：

- **Encoder（下采样路径）**：
  - 不断用卷积+池化降低分辨率
  - 提取高层语义特征

- **Decoder（上采样路径）**：
  - 用上采样（或转置卷积）恢复分辨率
  - 生成像素级的预测

**跳跃连接（Skip Connection）**：

这是 U-Net 的关键！Encoder 的特征直接连接到 Decoder 的对应层。

![U-Net结构示意图](/img/dl/unet.png)

**好处**：结合低层细节（边缘、纹理）和高层语义（物体类别）

**应用**：医学图像分割、卫星图像分割、图像修复等

### 5.2 ViT（Vision Transformer）

2020 年 Google 的 **ViT** 证明：**纯 Transformer 也能在视觉任务上打败 CNN！**

**将 Transformer 应用到图像的挑战**：

图像是 2D 的，像素太多（比如 224×224=50176 个像素）。如果每个像素都是一个 token，attention 的计算量是 $O(n^2)$，太大了！

**图像分块（Patch Embedding）**：

ViT 的做法：把图像切成小块（patch），比如 16×16 的 patch

$$\text{Image}(224 \times 224) \to \text{patches}(14 \times 14) \to \text{Flatten to tokens}(196)$$

每个 patch 用线性层映射成 embedding，就像 NLP 里的 word embedding。

**ViT 的完整流程**：

1. 图像分块 → 196 个 patch tokens
2. 加上位置编码
3. 加一个特殊的 **[CLS] token**（用于分类）
4. 送入标准的 Transformer Encoder
5. 取 [CLS] token 的输出做分类

![ViT结构示意图](/img/dl/vit.png)

**ViT vs CNN**：

- ViT 需要更多数据才能训练好（**归纳偏置（inductive bias）更少**）
- 在大规模数据集上，ViT 效果更好
- ViT 的计算效率更高（可以并行）

**ViT 的改进**：

- **DeiT (Data-efficient Image Transformer)**：用知识蒸馏，减少数据需求
- **Swin Transformer**：分层的 Transformer，在局部窗口内做 attention，效率更高



### 5.3 DPT（Dense Prediction Transformer）

**密集预测任务**：每个像素都要输出一个值
- **深度估计**：预测每个像素的深度
- **语义分割**：预测每个像素的类别

**DPT 的想法**：用 ViT 做 backbone，加上一个密集预测的 head

**关键设计**：重新组装（Reassemble）ViT 的特征，恢复空间分辨率

![DPT结构示意图](/img/dl/dpt.png)

### 5.4 CLIP

**CLIP (Contrastive Language-Image Pre-training)** 是 OpenAI 2021 年的工作，通过对比学习连接视觉和语言。

**对比学习（Contrastive Learning）**：

让相似的样本在特征空间中靠近，不相似的样本远离。

**CLIP 的训练方式**：
![CLIP训练示意图](/img/dl/clip.png)
- **数据**：4 亿个图像-文本对（从互联网爬取）
- **训练目标**：
  - **正样本**：匹配的图像-文本对，余弦相似度要高
  - **负样本**：不匹配的图像-文本对，余弦相似度要低





**损失函数**：

$$\mathcal{L} = -\frac{1}{N} \sum_{i=1}^{N} \log \frac{\exp(\text{sim}(I_i, T_i) / \tau)}{\sum_{j=1}^{N} \exp(\text{sim}(I_i, T_j) / \tau)}$$

其中 $\text{sim}(I, T)$ 是图像和文本特征的余弦相似度，$\tau$ 是温度参数。

**Zero-shot 学习能力**：

训练好的 CLIP 可以不用微调，直接做分类！怎么做？给类别写文本描述，算图像和每个描述的相似度，取最大的。

**应用**：图像分类、图像检索、文本到图像生成（**DALL-E**、**Stable Diffusion** 都用了 CLIP）



### 5.5 Equivariant Network（等变网络）

**等变性（Equivariance）的数学定义**：

如果 $f(T(x)) = T(f(x))$，则 $f$ 对变换 $T$ 是等变的。

**CNN 的平移等变性**：

卷积操作对平移是等变的：先平移再卷积 = 先卷积再平移

$$\text{conv}(T_{\text{shift}}(I)) = T_{\text{shift}}(\text{conv}(I))$$

但 **CNN 不是旋转等变的**！

**ViT 的等变性**：

标准 ViT 没有平移等变性（因为位置编码是绝对的），但可以通过相对位置编码实现（参考论文：[Relative Position Encoding](https://arxiv.org/pdf/2306.06722)）

**旋转等变网络**：

在分子、3D 点云等任务中，旋转不变性很重要。

**E(n) Equivariant GNN**：保持旋转和平移等变性的图神经网络

## 第6章 生成模型

### 6.1 GAN（生成对抗网络）

**GAN** 是 2014 年 **Ian Goodfellow** 提出的，被 **Yann LeCun** 称为"过去10年机器学习最有趣的想法"。

**GAN 的基本思想**：

- **生成器（Generator）**：生成假数据，骗过判别器
- **判别器（Discriminator）**：区分真假数据

两者对抗训练，互相进步！

**GAN 的损失函数**：

$$\min_G \max_D \mathbb{E}_{x \sim p_{\text{data}}}[\log D(x)] + \mathbb{E}_{z \sim p_z}[\log(1 - D(G(z)))]$$

- $D$ 想最大化这个目标：真数据分对（$\log D(x)$ 大），假数据分对（$\log(1 - D(G(z)))$ 大）
- $G$ 想最小化这个目标：让假数据骗过 $D$

**训练挑战**：

- **模式崩塌（Mode Collapse）**：只生成几种样本
- **训练不稳定**：$G$ 和 $D$ 的平衡很难把握
- **梯度消失**：$D$ 太强时，$G$ 收不到有效梯度

**经典 GAN 变体**：

- **DCGAN**：用深度卷积网络，引入 BatchNorm
- **StyleGAN**：控制生成图像的风格，质量超高
- **CycleGAN**：无需配对数据的图像翻译（马→斑马）



### 6.2 VAE（变分自编码器）

**自编码器（Autoencoder）**：

- **Encoder**：$z = f_{\text{enc}}(x)$（压缩）
- **Decoder**：$\hat{x} = f_{\text{dec}}(z)$（重建）
- **目标**：让 $\hat{x} \approx x$

**VAE 的改进**：让 $z$ 服从某个分布（比如标准正态分布）

$$q_\phi(z|x) \sim \mathcal{N}(\mu(x), \sigma^2(x))$$

**重参数化技巧（Reparameterization Trick）**：

不能直接对采样操作求梯度。改写成：

$$z = \mu(x) + \sigma(x) \odot \epsilon, \quad \epsilon \sim \mathcal{N}(0, I)$$

**ELBO（Evidence Lower Bound）**：

$$\mathcal{L} = \mathbb{E}_{q_\phi(z|x)}[\log p_\theta(x|z)] - D_{\text{KL}}(q_\phi(z|x) || p(z))$$

第一项是**重建误差**，第二项是**KL散度**（让 $q$ 接近先验 $p$）




### 6.3 DDPM & Flow Matching
扩散模型（Diffusion Model）是目前生成模型的主流 ！
前向扩散过程（Forward Diffusion）：
逐步给图像加噪声，最终变成纯噪声
$$q(x_t | x_{t-1}) = \mathcal{N}(x_t; \sqrt{1 - \beta_t} x_{t-1}, \beta_t I)$$
反向去噪过程（Reverse Denoising）：
训练一个神经网络 (xt , t) 预测噪声 ，逐步去噪
$$p_\theta(x_{t-1} | x_t) = \mathcal{N}(x_{t-1}; \mu_\theta(x_t, t), \Sigma_\theta(x_t, t))$$
DDPM 的训练：
损失函数超简单：
$$\mathcal{L} = \mathbb{E}_{t, x_0, \epsilon} \|\epsilon - \epsilon_\theta(x_t, t)\|^2$$
就是预测噪声的 MSE ！
Flow Matching：
最近的新方法，直接学习从噪声到数据的 ODE 流

比 DDPM 更快，训练更稳定

[图片占位符： 扩散模型的前向和反向过程示意图]



### 6.4 Stable Diffusion

**Latent Diffusion Model** 的思想：

直接在像素空间做扩散太慢！先用 VAE 压缩到潜空间（latent space）

**Stable Diffusion 的架构**：

1. **VAE Encoder**：图像 → 潜空间 (512×512 → 64×64)
2. **U-Net 去噪网络**：在潜空间做扩散
3. **CLIP Text Encoder**：文本 → embedding
4. **Cross-Attention**：把文本 embedding 注入 U-Net
5. **VAE Decoder**：潜空间 → 图像

**为什么叫 Stable Diffusion？**

- 在 latent space 做，更稳定、更快
- 开源，人人都能跑（相比 DALL-E）



### 6.5 Conditional Generation（条件生成）

**条件生成**：根据给定条件生成内容（比如根据文本生成图像）

**Cross Attention**：

在扩散模型的 U-Net 中，加入 Cross-Attention 层：
- **Query** 来自图像特征
- **Key** 和 **Value** 来自文本 embedding

$$\text{Attention}(Q_{\text{image}}, K_{\text{text}}, V_{\text{text}})$$

**Token Concat**：

直接把条件信息拼接到输入上（简单粗暴）

**ControlNet**：

参考论文：[ControlNet: Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/pdf/2302.05543)

**核心思想**：复制预训练模型，加上额外的条件输入（边缘、深度图等）

- **训练时**：
  - 冻结原模型参数
  - 只训练新加的分支
- **推理时**：两个分支的输出相加

**好处**：保留预训练模型的生成能力，同时添加精确控制



## 第7章 大模型（语言&视觉）

### 7.1 解码方式

#### 7.1.1 单向解码（Autoregressive）

**GPT 系列的做法**：从左到右生成，每次预测下一个 token

**Causal Masking（因果掩码）**：

在 Self-Attention 中，只能看到左边的 token，看不到右边的

**解码策略**：

- **贪婪解码（Greedy）**：每次选概率最大的 token

$$t = \arg\max P(x_t | x_1, \ldots, x_{t-1})$$

- **Beam Search**：保留 top-k 个候选序列

**采样策略**：

- **Temperature Sampling**：$P(x) \propto \exp(\log p(x) / T)$
- **Top-k Sampling**：只从概率最高的 k 个 token 中采样
- **Top-p (Nucleus) Sampling**：累积概率达到 p 时停止

#### 7.1.2 双向解码

**BERT 的做法**：随机 mask 一些 token，预测被 mask 的内容

**Masked Language Modeling (MLM)**：

$$\log p(x_{\text{mask}} | x_{\text{context}})$$

**双向上下文的优势**：

可以同时利用左边和右边的信息，理解能力更强

- **适合**：文本分类、问答、命名实体识别等理解任务
- **不适合**：文本生成（因为没有自回归的训练）

**BERT 的预训练+微调范式**：

1. **预训练**：在大规模语料上做 MLM
2. **微调**：在下游任务上 fine-tune



### 7.2 GRPO

**GRPO (Group Relative Policy Optimization)** 是强化学习在大模型训练中的应用

**RLHF (Reinforcement Learning from Human Feedback)**：

1. **预训练**：在大规模文本上训练语言模型
2. **奖励模型**：人类标注哪个回答更好，训练 reward model
3. **RL 微调**：用 PPO 等算法优化模型，让它生成高奖励的回答

**GRPO vs PPO**：

GRPO 是 PPO 的改进，用相对奖励而不是绝对奖励

$$\mathcal{L}_{\text{GRPO}} = \mathbb{E}[\log \pi_\theta(y | x) \cdot (r(y) - \bar{r}(x))]$$

其中 $\bar{r}(x)$ 是同一个 prompt $x$ 下的一组回答的平均奖励。

**好处**：减少奖励模型的方差，训练更稳定