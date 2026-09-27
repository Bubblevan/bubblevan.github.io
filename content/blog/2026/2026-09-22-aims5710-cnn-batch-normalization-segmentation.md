---
schema: bubblevan/v1
id: blog-20260922-aims5710-cnn-batch-normalization-segmentation
content_kind: blog
title: "AIMS5710：Batch Normalization、CNN 反向传播与 Semantic Segmentation"
date: 2026-09-22
updated: 2026-09-22
status: draft
visibility: public
summary: "依据 2026 年 9 月 22 日课堂录音，逐步整理 Batch Normalization、Dropout、残差连接、卷积前向与反向传播、感受野、Pooling，以及语义分割的多尺度网络。"
topics: [AIMS5710, Deep Learning, CNN, Backpropagation, Batch Normalization, Semantic Segmentation, CUHK]
projects: []
aliases: []
authors: [bubblevan]
---

今天的 AIMS5710 终于从前面的全连接网络推进到了 CNN。老师先把上一节的计算图、softmax 和交叉熵反向传播重新接上，然后补充 Batch Normalization、Dropout、Autoencoder 和残差连接，后半节才进入卷积网络以及 Semantic Segmentation。

## 1. 先把上一节的反向传播接起来

### 1.1 Softmax 和交叉熵仍然只是计算图中的两个节点

![AIMS5710 课堂板书：交叉熵、Softmax、全连接层与 MLP 的反向传播总复盘](/daily/2026/9-22/aims5710-2026-09-22-board-recap.jpg)

这张板书把几个模块并排放在一起比较：交叉熵和 softmax 都是 Param: None，全连接层才有 \(W,b\)；它们各自先算自己的 backward，再把梯度交给前一个模块。右侧还写了 softmax Jacobian 的矩阵形式 \(\operatorname{diag}(p)-pp^T\)，以及多层感知机前向时反复使用的线性层加非线性结构。

设网络最后输出 logits \(y=(y_1,\ldots,y_K)\)，softmax 给出概率：

\[
p_i=\operatorname{softmax}(y)_i
=\frac{\exp(y_i)}{\sum_{r=1}^{K}\exp(y_r)}.
\]

真实标签用 one-hot 向量表示为 \(\hat y\)，交叉熵为：

\[
J=-\sum_{i=1}^{K}\hat y_i\log p_i.
\]

这两个操作本身都没有需要训练的参数。真正需要的是把损失的梯度沿计算图传回前面的权重。上一节已经得到 softmax 加交叉熵的简洁结果：

\[
\frac{\partial J}{\partial y_j}=p_j-\hat y_j.
\]

今天老师重新检查这个结果，是为了提醒我们：不要把最终公式当成黑箱。只要把每一个中间变量的偏导写清楚，复杂网络也只是重复使用链式法则。

### 1.2 为什么 Jacobian 要看成矩阵

如果输入和输出都是向量，就不能只写一个普通导数。对向量函数 \(h(x)\)，Jacobian 的一个元素是：

\[
\left[\nabla_x h\right]_{ij}
=\frac{\partial h_i}{\partial x_j}.
\]

例如逐元素激活函数 \(h_i=g(x_i)\) 中，\(h_i\) 不依赖 \(x_j\)（当 \(i\ne j\)），因此：

\[
\frac{\partial h_i}{\partial x_j}
=g'(x_i)\mathbf 1[i=j].
\]

于是整个 Jacobian 是对角矩阵：

\[
\nabla_x h=\operatorname{diag}\bigl(g'(x)\bigr).
\]

这个事实后面会不断出现：激活函数只在自己的位置传梯度，而线性层会把不同位置混合起来。

### 1.3 把每一层当成一个有输入、输出和 backward 的接口

板书其实是在给每个模块做“接口说明”：

- Cross-Entropy 接收概率 `p` 和 one-hot 标签 `ŷ`，输出 `J`，没有参数；它的 backward 是 `∂J/∂p_i = -ŷ_i/p_i`。
- Softmax 接收 logits `y`，输出 `p_i = exp(y_i) / Σ_j exp(y_j)`，没有参数；它的 Jacobian 元素是 `∂p_i/∂y_j = p_i·1[i=j] - p_i p_j`。
- Fully Connected 接收 `x`，输出 `y = Wx + b`，参数是 `W,b`，反向时分别得到
  \[
  \frac{\partial J}{\partial x}=W^T\frac{\partial J}{\partial y},
  \qquad
  \frac{\partial J}{\partial W}=\frac{\partial J}{\partial y}x^T,
  \qquad
  \frac{\partial J}{\partial b}=\frac{\partial J}{\partial y}.
  \]

把 CNN 看成同样的模块，只是把稠密矩阵换成了具有局部连接和权重共享的卷积算子，后面的推导就不会显得突然。

## 2. 让深层网络更容易训练

### 2.1 Batch Normalization 在做什么

如果每层的激活值尺度越来越大或越来越小，梯度传播就会变得不稳定。Batch Normalization 的想法是在网络内部对一个 mini-batch 的特征做标准化，而不是只在输入端做一次预处理。

对某个特征，在一个 batch 中先计算均值和方差：

\[
\mu_B=\frac{1}{m}\sum_{r=1}^{m}x^{(r)},
\qquad
\sigma_B^2=\frac{1}{m}\sum_{r=1}^{m}\left(x^{(r)}-\mu_B\right)^2.
\]

然后标准化：

\[
\hat x^{(r)}
=\frac{x^{(r)}-\mu_B}{\sqrt{\sigma_B^2+\varepsilon}}.
\]

如果只把它固定在均值 0、方差 1，模型表达能力可能会受到限制，所以再加两个可学习参数：

\[
y^{(r)}=\gamma\hat x^{(r)}+\beta.
\]

这里 \(\gamma\) 和 \(\beta\) 分别可以重新调整尺度和偏移。老师强调，BN 的价值主要是经验性的：它通常能让优化更容易、允许更大的学习率、缓解训练过程中的尺度问题，但不能把它理解成一个对所有网络都严格成立的理论保证。

BN 每次要额外计算 batch 的统计量，单个操作不一定更快；但如果它让训练更稳定、收敛更快，整体训练时间反而可能下降。除了 batch normalization，也可以沿特征或 channel 方向做其他 normalization，具体选择取决于数据形状和任务。

### 2.2 Dropout 是随机的 masking

Dropout 可以写成在网络中插入一个随机 mask。训练时，一些神经元被暂时去掉；推理时则使用完整网络。抽象地写：

\[
\tilde h=M\odot h,
\]

其中 \(M\) 是随机生成的 0/1 mask，\(\odot\) 表示逐元素乘法。

直觉上，网络不能一直依赖某几个固定神经元，因而会学到更分散的表示。老师展示的曲线也说明了一个容易混淆的现象：没有 dropout 时，训练集 loss 可能更低，但测试集 loss 反而更高，因为模型过拟合；加入 dropout 后，测试误差下降得更好。

现代网络往往把多个模块堆起来，例如：

\[
\text{Linear}
\rightarrow\text{BN}
\rightarrow\text{LeakyReLU}
\rightarrow\text{Linear}
\rightarrow\text{BN}
\rightarrow\text{LeakyReLU}
\rightarrow\text{Dropout}
\rightarrow\text{Classifier}.
\]

这不是唯一结构，但它说明网络并不只是“线性层接激活函数”这么简单。

### 2.3 残差连接为什么有利于梯度传播

如果一个模块的输出写成：

\[
z=x+F(x),
\]

那么：

\[
\frac{\partial z}{\partial x}
=I+\frac{\partial F(x)}{\partial x}.
\]

即使 \(F\) 的导数很小，旁边的恒等映射仍然留下了 \(I\)。所以残差连接给梯度提供了一条更直接的路径，能够缓解深层网络中梯度过小的问题。它不是保证梯度永远不会爆炸的魔法，而是让信息和梯度更容易沿 identity path 传播。

### 2.4 Autoencoder：用瓶颈逼模型学表示

Autoencoder 由 encoder 和 decoder 组成：

\[
x\xrightarrow{\text{encoder}}z
\xrightarrow{\text{decoder}}\tilde x.
\]

训练目标是让重建结果 \(\tilde x\) 接近原输入 \(x\)。如果中间表示没有任何限制，模型可能只是把输入原样复制；因此通常会设置一个更小的 bottleneck，或者向输入加入噪声，让模型必须保留真正有用的结构。

线性 autoencoder 与 PCA 有联系：它会尝试学习能表示数据主要变化方向的低维子空间；非线性 autoencoder 则可以表示更复杂的流形。老师把 denoising autoencoder、VAE 和 diffusion 作为相关方向提到，但今天没有展开。

## 3. 为什么图像不能只用全连接层

### 3.1 全连接层忽略了图像的空间结构

图像中相邻像素通常相关，但一个全连接层会把每个输入像素和每个输出神经元都连接起来。这样做有两个问题：参数量巨大，而且模型没有显式利用“附近像素更相关”这个事实。

更重要的是，图像中的对象可能出现在不同位置。同一个边缘、眼睛或轮廓，不应该因为平移到另一个位置就必须重新学习一套完全不同的参数。全连接层没有自然地表达这种平移等变性。

### 3.2 局部连接与共享权重

CNN 做两件事：

1. 每个输出只看输入的一个局部区域，也就是 local receptive field；
2. 同一个 filter 在不同空间位置重复使用，也就是 weight sharing。

因此，一个 filter 可以学成检测边缘、纹理或其他局部模式的模板。输入平移时，特征图中的响应也会相应平移，这就是共享权重带来的平移等变结构。

从矩阵角度看，全连接层是稠密矩阵；卷积可以写成一个稀疏、带有 Toeplitz 结构的矩阵。卷积的参数更少，不是因为它“不做计算”，而是因为它把局部性和共享权重作为模型结构的一部分。

## 4. 卷积的前向计算

### 4.1 从一张 RGB 图片到多个 feature map

假设输入图片大小为 \(P\times Q\times C\)，其中 \(C=3\) 表示 RGB 三个 channel。一个 filter 的空间大小是 \(K\times K\)，并且要覆盖全部输入 channel，因此它的形状是：

\[
K\times K\times C.
\]

在一个位置上，filter 与对应的输入 patch 逐元素相乘，再把空间位置和 channel 全部加起来，并加上 bias，得到一个输出值。一个 filter 会产生一个 output channel；如果有 \(D\) 个 filter，就会得到 \(D\) 个 output channels。

以单 channel、无 padding、stride 为 1 的 5×5 输入和 3×3 filter 为例，filter 只能在输入上滑出 3×3 个位置，因此输出空间大小是 3×3。多 channel 时，先分别计算每个输入 channel 的乘积，再沿 channel 相加；多 filter 时，重复这个过程得到多张 feature map。

### 4.2 Padding、stride、dilation 分别改变什么

输出的空间大小由输入大小、kernel、padding、stride 和 dilation 一起决定。老师提醒我们不要只背一个公式，而要理解每个参数的作用：

- padding 在边缘补值，可以保持空间大小，也能让边界像素被充分看到；
- stride 大于 1 时，filter 跳着移动，输出会下采样；
- 更大的 kernel 或 dilation 会扩大有效 receptive field；
- output channel 的数量由 filter 的数量决定，不直接改变空间尺寸。

所以卷积层既是特征提取器，也是一个可以控制空间分辨率的模块。

## 5. 一维卷积的反向传播：一步一步推

### 5.1 先固定一个不容易混淆的记号

二维卷积的图很容易被板书上的索引和边界遮住，所以我先用一维版本说明。采用“互相关”的常见深度学习记号，令：

\[
y_i=\sum_{k=-r}^{r}w_kx_{i+k},
\]

超出输入范围的 \(x\) 视为 0。这里 \(w_{-r},\ldots,w_r\) 是共享的 kernel，\(y_i\) 是在位置 \(i\) 的输出。

设后面的网络已经传回来：

\[
g_i=\frac{\partial J}{\partial y_i}.
\]

现在分别求输入和 kernel 的梯度。

### 5.2 对输入 x_j 求导

![AIMS5710 课堂板书：一维卷积反向传播中的索引对应与 kernel 旋转](/daily/2026/9-22/aims5710-2026-09-22-conv-backprop-board.jpg)

板书左侧用 \(y_1,\ldots,y_7\) 和 \(x_1,\ldots,x_7\) 画出了共享权重的滑动连接；红色箭头聚焦在 \(x_4\)，表示求 \(\partial J/\partial x_4\) 时，要把所有依赖 \(x_4\) 的输出路径贡献加起来。右侧最后写成了 \(\operatorname{rot}_{180}(w)\otimes\partial J/\partial y\)，正好对应下面的逐项推导。

第一步，直接套链式法则。损失依赖很多个输出 \(y_i\)，而每个 \(y_i\) 可能依赖 \(x_j\)：

\[
\frac{\partial J}{\partial x_j}
=\sum_i\frac{\partial J}{\partial y_i}
\frac{\partial y_i}{\partial x_j}.
\]

第二步，把 \(\partial y_i/\partial x_j\) 展开。由

\[
y_i=\sum_k w_kx_{i+k},
\]

只有当 \(i+k=j\) 时，\(x_j\) 才出现在这一项中。因此：

\[
\frac{\partial y_i}{\partial x_j}
=w_{j-i}.
\]

第三步代回去：

\[
\frac{\partial J}{\partial x_j}
=\sum_i g_iw_{j-i}.
\]

这个结果看起来和原来的滑动计算很像，但 kernel 的索引方向反过来了。也就是说，在二维情形里，对输入的梯度可以看成把 upstream gradient 与旋转 180° 的 kernel 做卷积（具体写成 convolution 还是 cross-correlation，取决于教材采用的索引约定）。

板书里老师特意纠正了一个索引方向：如果前向写成 \(x_{i+k}\)，就不能在后面突然写成 \(x_{i-k}\) 而不同时调整 kernel 的定义。真正不变的结论是：反向传播要把所有使用了 \(x_j\) 的输出贡献加起来，索引对应自然会产生 kernel 的翻转。

### 5.3 对共享 kernel w_k 求导

这次固定某一个 kernel 参数 \(w_k\)。它会在每个空间位置被重复使用，所以所有位置的贡献都要累加：

\[
\frac{\partial J}{\partial w_k}
=\sum_i\frac{\partial J}{\partial y_i}
\frac{\partial y_i}{\partial w_k}.
\]

由前向公式：

\[
\frac{\partial y_i}{\partial w_k}=x_{i+k}.
\]

因此：

\[
\frac{\partial J}{\partial w_k}
=\sum_i g_ix_{i+k}.
\]

如果每个输出还有 bias \(b\)，因为 \(y_i\) 中包含同一个 \(b\)，所以：

\[
\frac{\partial J}{\partial b}=\sum_i g_i.
\]

### 5.4 为什么这和全连接层乘 W^T 是同一个思想

把卷积写成矩阵乘法，可以表示为：

\[
y=Ax,
\]

其中 \(A\) 是由共享 kernel 组成的稀疏 Toeplitz 矩阵。于是：

\[
\nabla_xJ=A^T\nabla_yJ.
\]

这与全连接层 \(y=Wx\) 的反向传播完全平行：

\[
\nabla_xJ=W^T\nabla_yJ.
\]

只不过卷积矩阵具有特殊的稀疏和共享结构，所以 \(A^T\) 在实现上表现为一个旋转 kernel 的卷积，而不是显式构造巨大的矩阵。这样看，CNN 的反向传播并没有脱离上一节的框架。

## 6. Receptive Field、Pooling 与 CNN 变体

### 6.1 Receptive field 是一层能看到的区域

某个神经元在输入图像上实际能看到的区域，叫它的 receptive field。单层小 kernel 只能看到局部；多堆几层以后，一个高层神经元对应的原图区域会变大，因而可以利用更多上下文。

CNN 的一个张力是：局部信息适合识别边缘和细节，但分类或分割又需要更大的全局语义。增大 kernel、堆更多层、使用 dilation 或下采样，都可以扩大 receptive field，但它们的计算量、分辨率和信息损失不同。

### 6.2 Max pooling 的前向与反向

Max pooling 在一个窗口内只保留最大值。例如一个 2×2 窗口为：

\[
\begin{bmatrix}
12&20\\
8&12
\end{bmatrix},
\]

那么输出就是 20。它没有可学习参数，却能完成下采样；stride 也可以设为 2，让窗口之间不重叠。

反向传播时，窗口的梯度只传给前向时的 argmax 位置，其他位置的梯度为 0。可以把它看成由 argmax 产生的 mask：

\[
\nabla_xJ=M\odot\nabla_yJ.
\]

Pooling 的好处是降低分辨率并扩大后续层的有效 receptive field，代价是丢失精细的空间信息，甚至可能产生 aliasing。Global Average Pooling 更极端：每个 channel 直接对整张 feature map 求平均，得到长度等于 channel 数的向量，常用于替代分类末端的大型全连接层。

### 6.3 常见的 CNN 设计变化

CNN 中仍然可以使用 ReLU、LeakyReLU、PReLU、trainable ReLU、sigmoid 和 softmax。Dropout 也可以推广到二维特征图：不只是随机丢掉一个 scalar feature，还可以随机丢掉整个 channel 的 feature map。

LeNet 是一个很早的代表性结构：卷积层、subsampling/pooling 层和全连接层交替出现。它使用 tanh，而现在更常见的是 ReLU 一类激活函数。

标准卷积把 filter 设计成固定大小的方形，并在位置之间共享权重。Deformable Convolution 则让 filter 的采样位置发生可学习的偏移，使形状可以适应物体轮廓；相关变体还尝试部分放松固定的 weight sharing，让不同位置使用不同程度的参数。它们的动机是减少人工写死的 inductive bias，但是否真正更好必须看论文和实验，不能只凭名字相信。

卷积也不只属于规则的二维网格。它可以推广到 submanifold 或 graph 上，例如知识图谱和计算机网络中的 graph convolution。

## 7. Semantic Segmentation：给每个像素分类

### 7.1 语义分割和普通分类的差别

图像分类只回答“这张图里有什么”；semantic segmentation 要回答“每个像素属于哪一类”。因此输出必须保留空间位置。

如果每个像素只用一个整数表示类别，标签形状可以是 \(H\times W\)；如果每个像素用 one-hot 类别向量表示，输出可以写成 \(H\times W\times C\)，其中 \(C\) 是类别数。课堂上老师也特别澄清了这两种编码方式，不要把它们混为一谈。

常见数据集包括 Pascal VOC、ADE20K 和 Cityscapes：前者类别相对少，ADE20K 包含更多室内外场景类别，Cityscapes 更偏道路和自动驾驶场景。不同数据集的类别数、图像数量和 label 定义不同，不能只记一个数字套到所有数据集上。

### 7.2 为什么 1×1 卷积能做像素分类

假设某个位置的 feature vector 是 \(h\in\mathbb R^C\)。一个 \(1\times1\) 卷积不会混合相邻像素，只会在 channel 维度做线性变换：

\[
z=Wh+b,
\qquad W\in\mathbb R^{C_{\text{out}}\times C}.
\]

因此，对每个像素位置分别应用同一个线性分类器，就可以产生每个像素的 class logits，再接 softmax 得到像素级类别概率。这就是为什么 segmentation 网络的最后常见一个 1×1 convolution。

### 7.3 最简单的全卷积网络为什么还不够

最直接的想法是：从头到尾只用 convolution 和 activation，不做 downsampling，这样输出空间大小可以一直与输入相同。这种 fully convolutional network 保留了分辨率，但它主要只能利用局部信息，缺少高层语义和大范围上下文。

反过来，如果使用分类 backbone，经过多次下采样后空间尺寸可能缩小到原图的 \(1/32\)。这对图像分类通常没问题，因为只需要判断整张图；但对像素级分割来说，边界会变得很粗，细小物体也容易消失。

所以分割的核心矛盾是：

- 高分辨率特征保留边缘和局部细节，但语义较弱；
- 低分辨率特征拥有更大 receptive field 和更强语义，但空间定位较粗。

### 7.4 Multi-scale、Encoder–Decoder、U-Net 与 FPN

一种办法是保留不同层级的 feature map，把它们上采样到相同空间大小后拼接，再用 1×1 卷积做像素分类。这样可以同时利用浅层的细节和深层的语义。

另一种更系统的办法是 encoder–decoder：

1. encoder 逐步下采样，提取更抽象、更大范围的表示；
2. decoder 逐步上采样，把空间分辨率恢复回来；
3. decoder 可以用 transpose convolution 等带参数的上采样操作；
4. encoder 中对应尺度的 feature map 通过 skip connection 传给 decoder，补回边界细节。

U-Net 的特点是这种对称的多尺度跳跃连接。这里常见的是 concatenate，而不是简单相加：拼接后 decoder 可以自己学习如何组合两路特征，表达能力更灵活。

Feature Pyramid Network（FPN）也在做多尺度特征融合，思想与 U-Net 相近，但组织方式更偏向金字塔式的自顶向下融合。课堂最后还预告了 DeepLab 和 dilation/dynamic convolution 一类方法，下一节可能继续展开。

## 8. 今天这节课我真正要带走的东西

### 8.1 三条贯穿始终的线

第一条线是 **结构决定梯度如何流动**：逐元素激活产生对角 Jacobian，线性层反传用转置矩阵，卷积反传则是特殊稀疏矩阵的转置。

第二条线是 **结构先验减少学习负担**：CNN 的局部连接和共享权重不是额外装饰，而是把图像的空间规律写进网络。

第三条线是 **分辨率和语义之间的交换**：下采样换来更大 receptive field 和更强语义，但会损失细节；语义分割因此需要多尺度融合和 skip connection。

### 8.2 作业提醒

今天开头老师提醒，Homework 1 是下周二，也就是 **9 月 29 日** 截止，范围接着前两节课。手写作业或 LaTeX 排版后导出的 PDF 都可以；老师还问大家是否需要上传源文件，方便后续学习（AI时代没有手搓Latex源码的吧）。