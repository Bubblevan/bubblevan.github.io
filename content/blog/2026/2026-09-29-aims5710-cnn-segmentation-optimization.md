---
schema: bubblevan/v1
id: blog-20260929-aims5710-cnn-segmentation-optimization
content_kind: blog
title: "AIMS5710：CNN 反向传播、语义分割、架构演进与优化开篇"
date: 2026-09-29
updated: 2026-09-29
status: draft
visibility: public
summary: "我按 9 月 29 日晚课的转写顺序整理 CNN 卷积反传、语义分割、经典网络架构与优化方法开篇，并把关键梯度一步步展开。"
topics: [AIMS5710, CNN, Backpropagation, Semantic Segmentation, ResNet, Optimization]
projects: []
aliases: []
authors: [bubblevan]
---

今天的晚课从上次留下的 CNN 开始：先把卷积和上下文操作复习一遍，再推一维卷积的反向传播；之后回到语义分割，接着按架构演进讲 AlexNet、VGG、Inception、ResNet、DenseNet、MobileNet 和 EfficientNet；最后才转入梯度下降、动量、权重衰减和二阶优化。

## 1. 开课先交代作业与 AI 使用

老师先提醒大家：作业参考解答还没有发布，会等缓冲提交期结束后再放出来，预计大约一周；HW2 当天已经发布，内容主要围绕 CNN，可以先开始做。老师还建议以后写作业、论文或发布代码时说明 AI 用在了哪里，让读者知道哪些部分需要特别审慎地检查。这不是“用了 AI 就不行”，而是把工具使用过程讲清楚。

## 2. CNN：局部滤波、尺度上下文与反向传播

### 2.1 从全连接改成局部连接和共享权重

老师先把 CNN 和普通全连接网络对照：全连接层里不同位置通常有各自的权重；卷积则用同一个小滤波器在输入上滑动。这样每个输出只连接局部邻域，而且不同位置共享滤波器参数，既降低参数量，也利用了图像等信号的局部结构。

卷积不是深度学习专属的概念，它早就在控制理论和信号处理里使用。把输入想成由不同频率成分组成的信号，滤波器会响应或抑制不同模式。讲到图像时，老师用远看、近看会看到不同内容的例子解释低频与高频：粗略布局与细节边缘处在不同尺度，网络不能只盯着一个很小的邻域。

把这个局部连接写成二维形式，若卷积核支持范围记作 \(\mathcal K\)，位置 \((i,j)\) 的输出是

$$
y_{i,j}=\sum_{(u,v)\in\mathcal K}w_{u,v}x_{i+u,j+v}+b.
$$

也就是说，先取以 \((i,j)\) 为中心的一块输入，逐点乘上核权重，再把乘积加起来并加偏置；核权重在不同输出位置重复使用。板书写的是不翻转核的索引形式，这也是深度学习框架中常见的卷积实现约定。

![9月29日晚课白板全景，记录 CNN 回顾、卷积与架构示意](/blog/2026/9-29/aims5710-2026-09-29-cnn-board-overview.jpg)

*图源：9月29日 AIMS5710 课堂白板照片。*

### 2.2 Stride、pooling、dilation 各自改变什么

老师把三种常见操作放在“扩大上下文或降低分辨率”的问题下比较：

- **Stride（步幅）**：滤波器滑动时跳过一些位置，输出空间尺寸变小，常见效果是大约下采样两倍。它直接减少后续要处理的位置数。
- **Pooling（池化）**：在局部窗口里做 max 或 average，再缩小特征图。Max pooling 保留窗口中较强的响应，average pooling 求平均；它不是把同一个位置的卷积简单重复一次，而是额外做局部汇聚。
- **Dilation / atrous convolution（空洞卷积）**：在卷积核元素之间留间隔，扩大有效感受野，但不必增加可学习权重，也不等于自己把特征图下采样。

10:45 左右有同学追问图里的虚线圆圈。结合老师的解释和卷积核示意图，它们表示扩张后的核间隔位置按零处理，不是图像边界处补出来的 padding。这样仍可沿用普通卷积的滑动实现方式，同时让核在空间上“看得更远”。

![板书中的二维卷积公式、一维卷积连线，以及 stride、pooling 和 dilation 示意](/blog/2026/9-29/aims5710-2026-09-29-convolution-board.jpg)

*图源：9月29日 AIMS5710 课堂白板近景。板书将 pooling ratio 标为 2，并把 stride 2 的下采样与转置卷积的上采样作对照（图中把上采样尺度标作 1/2）；空洞卷积则通过在核位置之间留空来扩大感受野。*

还有一个容易混淆的术语：卷积对平移通常表现为**等变**——输入平移，特征图也相应平移；它不自动保证输出完全不随平移变化。池化、步幅、全局汇聚等操作可能带来一定平移不变性或容忍度，但这与卷积本身的等变性不是一回事。

### 2.3 一维卷积前向：先把下标约定钉牢

13:06 开始复习卷积反传。老师说这次先不把非线性混进公式，先看最简单的卷积层；有激活函数时，再像全连接网络一样用链式法则把激活导数乘回来。

为了让索引不打架，我把板书里的 1D 例子写成：

$$
y_i = \sum_{k=-r}^{r} w_k x_{i+k}.
$$

这里 \(i\) 是输出位置，\(k\) 是卷积核相对中心的位置，\(w_k\) 是共享的核权重，\(x_{i+k}\) 是该输出位置读到的输入。今晚举的核大小为 3，因此 \(k\in\{-1,0,1\}\)。越界项由所采用的 padding 规则决定；下面求和只对有效位置成立。

令

$$
\delta_i \equiv \frac{\partial J}{\partial y_i}
$$

表示损失对第 \(i\) 个卷积输出的梯度。接下来分别求输入梯度和核权重梯度。

### 2.4 对输入求导：为什么核会反过来

目标是求固定输入位置 \(x_j\) 对损失的影响。由于 \(J\) 通过各个 \(y_i\) 依赖 \(x_j\)，链式法则先写成：

$$
\frac{\partial J}{\partial x_j}
= \sum_i \frac{\partial J}{\partial y_i}
  \frac{\partial y_i}{\partial x_j}.
$$

现在逐项算后半段。前向式为 \(y_i=\sum_k w_k x_{i+k}\)。只有当 \(i+k=j\) 时，\(y_i\) 里才含有 \(x_j\)，所以这个核位置必须满足 \(k=j-i\)。因此：

$$
\frac{\partial y_i}{\partial x_j}
= w_{j-i}.
$$

把它代回链式法则：

$$
\frac{\partial J}{\partial x_j}
= \sum_i \delta_i w_{j-i}.
$$

这已经是输入梯度。若想看清楚“翻转”从哪来，把求和索引改写成 \(i=j+q\)：

$$
\frac{\partial J}{\partial x_j}
= \sum_q \delta_{j+q} w_{-q}.
$$

输出梯度往 \(x_j\) 汇聚时，位置 (j+q) 对应的权重是 \(w_{-q}\)，而不是 \(w_q\)，所以反传到输入的核索引次序反过来。老师用沿着连线反向看哪些输出会影响某个输入位置，解释了板书里为什么出现反序的滤波器。

### 2.5 对权重求导：把共享位置的贡献全部加起来

同一个 \(w_k\) 在每个输出位置都会被复用，因此它的梯度要汇总所有位置的贡献：

$$
\frac{\partial J}{\partial w_k}
= \sum_i \frac{\partial J}{\partial y_i}
  \frac{\partial y_i}{\partial w_k}.
$$

前向式中 \(w_k\) 乘的是 \(x_{i+k}\)，所以：

$$
\frac{\partial y_i}{\partial w_k}=x_{i+k},
\qquad
\frac{\partial J}{\partial w_k}
=\sum_i \delta_i x_{i+k}.
$$

这和对输入求导的索引方向不同：权重梯度把每个输出位置所看到的输入片段，与该输出位置的上游梯度相乘后累加。若加偏置 \(b\)，每个输出多一项 \(b\)，于是 \(\frac{\partial y_i}{\partial b}=1\)，故 \(\frac{\partial J}{\partial b}=\sum_i\delta_i\)。若卷积后还有 \(h_i=g(y_i)\)，则先令传入卷积的梯度为 \(\frac{\partial J}{\partial y_i}=\frac{\partial J}{\partial h_i}g'(y_i)\)，再使用上述两式。

板书暂时忽略 bias；老师说有 bias 时照全连接层的处理即可。随后还提到 batch normalization、dropout 和 ReLU 等非线性模块：它们改变整条网络的梯度路径，但卷积核共享这一部分的求导方式仍然按上面拆解。

## 3. 语义分割：每个像素都要作一次分类

### 3.1 为什么直接放大分类器输出不够

21:02，老师回到 Semantic Segmentation：不是给整张图一个类别，而是要给图中每个像素分配类别，也可以理解为预测一个或多个目标的 mask。分类网络经过多次 stride 和 pooling 后，特征图的空间分辨率可能只剩输入的 (1/32)。如果把这种粗特征直接放大到原图，边界会很粗，细小物体和位置细节也容易丢失。

评价时不能只看 pixel accuracy。若背景像素占绝大多数，即使模型把大部分像素都猜成背景，像素准确率也可能很高。因此课件强调按类别计算 IoU，再对类别求平均：

$$
\operatorname{IoU}_c
=\frac{TP_c}{TP_c+FP_c+FN_c},
\qquad
\operatorname{mIoU}
=\frac{1}{C}\sum_{c=1}^{C}\operatorname{IoU}_c.
$$

这里每类的 IoU 都同时考虑漏检 (FN) 和误检 (FP)，不会让大量背景像素单方面主导指标。

### 3.2 FCN、U-Net 与 FPN：让高低层特征重新见面

FCN 把分类网络的全连接部分改成卷积式预测，并逐步上采样。课件里的融合路径是把 pool5 的 (1/32) 预测上采样到 (1/16)，与 pool4 融合；再与 pool3 的 (1/8) 信息融合。深层特征有较强语义，浅层特征有较精确的位置细节；逐级融合比只把最深层特征一次放大更能恢复边界。

U-Net 把同一空间分辨率的 encoder 与 decoder 特征通过横向 skip connection 接起来，使用**通道拼接**保留细节，再由 decoder 继续整合。它像一个 U 形的下采样—上采样结构：左侧逐级提取上下文，右侧逐级恢复分辨率，同尺度横向连接把高分辨率细节补回来。

![U-Net 在编码器和解码器同尺度特征之间使用拼接式 skip connection](/blog/2026/9-29/aims5710-unet-skip-concat.png)

*图源：AIMS5710 课件《Semantic Segmentation》，第 14 页，按 U-Net 结构裁切。*

FPN 也把高层语义传回低层，但课件中的 lateral fusion 使用**相加**，不是 U-Net 的拼接；它最初面向目标检测，也能构造多尺度分割特征。录音里这部分有几处被识别成 “feature parameter”，结合课件应为 Feature Pyramid Network（FPN）。老师把 FPN 视为不必另建复杂 decoder 的多尺度融合方式。

### 3.3 DeepLab：少丢分辨率，再用空洞卷积扩大视野

DeepLab 系列的出发点是：ImageNet 分类器里连续 max pooling 下采样太多，分割要细位置，不能照搬所有下采样。DeepLabv1 减少空间下采样、使用空洞卷积扩大感受野；再用双线性插值放大特征图，也试过多尺度预测和 CRF 后处理。CRF 属于进一步修整边界的后处理，并不是空洞卷积本身的必要组成。

DeepLabv2 在分类头之前加入 **ASPP（Atrous Spatial Pyramid Pooling）**，并行使用不同 dilation rate，让模型在多个感受野下观察同一特征图。DeepLabv3 继续扩展空洞卷积的多尺度设计，包括 multi-grid；同时使用 batch normalization 和 image-level/global-average-pooling 特征。DeepLabv3+ 则在 DeepLabv3 encoder 外加一个 decoder：高层特征先上采样 4 倍；低层 encoder 特征先经 \(1\times1\) 卷积压缩通道；两路拼接后用 \(3\times3\) 卷积细化，再上采样 4 倍回到原图尺度。相比直接一次性放大 16 倍，decoder 能把低层空间细节重新引入预测。

![DeepLabv3+ 的 ASPP encoder 与低层特征 decoder](/blog/2026/9-29/aims5710-deeplabv3plus-decoder.png)

*图源：AIMS5710 课件《Semantic Segmentation》，第 21 页，按 encoder-decoder 结构裁切。*

课件还列了 PSPNet 的 pyramid pooling，以及 EncNet 的 class-context 编码和 channel attention。老师没有逐篇论文拆细节，而是提醒这门课更重要的是理解卷积如何计算、各模块要解决什么问题；等 Transformer 讲完还会回到 segmentation。

## 4. 经典 CNN 的第一条线：特征能不能迁移

### 4.1 AlexNet 之后，不只看最终分类准确率

37:27 转入网络架构。老师先强调模块化的重要性：CNN 设计常由大量实验组合出来，层数增加后，若每个位置都重新设计，网络会很难分析和训练。模块化是把不同职责拆开、再组合。

AlexNet（2012）有 5 个卷积层和 2 个全连接层，max pooling 放在第 1、2、5 个卷积层之后。在今天看很小，但当时是 ImageNet 的重要突破。接下来讲的 Yosinski 等人特征可迁移性实验，问题不是“一个网络分类分数多高”，而是它学到的中间表示能否拿去解决另一组类别。

### 4.2 A/B 类别实验：冻结表示和微调表示不是一回事

课件把 ImageNet 类别拆成 A、B 两组，各自训练一个 8 层 AlexNet，得到 baseA 和 baseB。再从 baseA 或 baseB 拿前 \(n\) 层初始化新网络：

- **Self-transfer（\(B_nB\)）**：从 B 任务复制前 \(n\) 层并冻结，在 B 数据上训练后续层，作为同任务控制组。
- **Transfer（\(A_nB\)）**：从 A 复制前 \(n\) 层并冻结，在目标 B 上训练后续层，观察异任务特征能否直接复用。
- **带 “+” 的版本**：同样从 A 或 B 初始化，但允许全部层继续学习，检验迁移特征作为初始化是否有帮助。

结论要拆开读：高层表示更贴近原任务，跨任务冻结时不一定好用；层与层之间还可能形成 co-adaptation（协同适配），只冻结一段、只训练另一段会破坏原先共同形成的表示。但允许进一步 fine-tune 后，迁移权重可以成为不错的初始化。任务越不相似，迁移性通常越低；这不妨碍 ImageNet 预训练权重后来成为很多视觉任务微调的常见起点。

## 5. 架构演进：把职责拆开，再把网络做深

### 5.1 Clarifai、OverFeat 与 VGG：下采样和模块重复

Clarifai 的改动包括把首层卷积从 \(11\times11\)、stride 4 改为 \(7\times7\)、stride 2，减少早期信息损失；增加卷积特征图通道数也带来小幅提升。OverFeat 的方向是减少 pooling、增加 filters。它们在提醒我：网络架构不仅是“加几层”，首层的核、步幅、通道数都会改变后面能保留的信息。

Chatfield 的 CNN-F/M/S 对照还检验了具体训练细节：CNN-S 表现最好但计算更慢；把输入缩放到较短边 256，再取中心和四角 \(224\times224\) crop 并翻转，比不做增强提升约 3%；灰度图比彩色图表现低约 3%；把 fc7 从 4096 缩到 128，特征维度小 32 倍，但性能约下降 2%；ranking hinge loss 和 L2 feature normalization 在 PASCAL VOC 2007 上也带来明显增益。老师用这些结果说明，architecture 和训练 recipe 常常一起影响结果。

VGG 的主要设计是统一使用 \(3\times3\) 卷积，并把卷积块与下采样模块按固定方式重复。它的模块结构清楚，便于从 11 层扩展到 16/19 层；但仅仅堆深并不能自动解决训练困难，这也把课堂引向梯度消失和 ResNet。

### 5.2 \(1\times1\) 卷积、Inception 与全局平均池化

Network-in-Network 把 \(1\times1\)（pointwise）卷积放在卷积层之后。因为空间核只有一个位置，它主要在同一像素处混合通道，不负责跨空间滤波；因此可以把“空间邻域特征提取”和“通道维度变换”分开，也能压缩通道数、减少后续较大卷积的成本。

GoogLeNet / Inception 把几种不同路径并行放在一个模块里，例如 \(1\times1\)、\(3\times3\)、\(5\times5\) 卷积与 pooling，再把分支合并。大核卷积之前先用 \(1\times1\) bottleneck 减少输入通道，可降低计算。多个 Inception module 可以重复堆叠；辅助分类头是早期帮助深网训练的办法之一。

另一个重要取舍是全连接层的参数量。若末端特征图为 \(7\times7\times1024\)，展平后再接大 FC 会产生大量参数；global average pooling 对每个通道的整张特征图求一个平均值，把空间维压成每通道一个数。表达能力有所改变，但参数更省，也可能更不容易过拟合。

Inception-v2/v3 又把 batch normalization 和卷积分解纳入设计：\(5\times5\) 可由两个 \(3\times3\) 近似；\(3\times3\) 可拆成 \(3\times1\) 后接 \(1\times3\)，权重项从 9 降到 6；更大的 \(7\times7\) 也可以拆成横纵方向的细长卷积。下采样时，stride convolution 和 pooling 都能缩小特征图：前者学会如何下采样，后者先做局部汇聚；具体选择是计算、适应性与梯度路径的取舍。

## 6. ResNet：把恒等路径显式留给梯度

### 6.1 从拟合 \(H(x)\) 改成拟合残差 \(F(x)\)

随着网络越堆越深，plain network 会遇到 degradation：56 层网络甚至可能比 20 层网络训练误差更大，这不是简单的“模型容量不够”，而是优化变难。ResNet 的做法不是直接让两层去拟合目标映射 \(H(x)\)，而是定义残差：

$$
F(x)=H(x)-x,
\qquad H(x)=F(x)+x.
$$

输入 \(x\) 沿 shortcut 原样传到加法节点，卷积分支只需学 \(F(x)\)。如果理想映射已经接近 identity，网络只需学习较小的改动；若残差分支暂时学不好，identity 仍然提供直接的信息通路。

![ResNet 残差块：卷积分支输出残差 F(x)，shortcut 把输入 x 加回来](/blog/2026/9-29/aims5710-resnet-identity-shortcut.png)

*图源：AIMS5710 课件《Different CNN Structures》，第 37 页，按 residual block 裁切。*

### 6.2 一步步看恒等分支如何进入导数

为了只看 skip connection 的作用，先把加法之前的残差分支看作 \(F(x)\)：

1. 输出是 \(H(x)=F(x)+x\)。
2. 对输入 \(x\) 求导：
   $$\frac{\partial H}{\partial x}=\frac{\partial F}{\partial x}+\frac{\partial x}{\partial x}.$$
3. 因为 \(\partial x/\partial x=1\)，所以：
   $$\frac{\partial H}{\partial x}=\frac{\partial F}{\partial x}+1.$$
4. 多维向量时，标量 1 换成单位矩阵 \(I\)：
   $$\nabla_x H=\nabla_x F+I.$$

这正是老师在板书上强调的点：即使残差支路的梯度很小，shortcut 也给反传提供一条恒等梯度路径。实际网络还可能在加法后接 ReLU 等非线性，所以完整 Jacobian 要再乘对应激活导数；上面是用来单独看清 shortcut 的简化推导。

![课堂回顾与 ResNet 残差路径板书](/blog/2026/9-29/aims5710-2026-09-29-resnet-recap-board.jpg)

*图源：9月29日 AIMS5710 课堂白板照片；红色笔迹强调 \(H(x)=F(x)+x\) 中 shortcut 对导数的贡献。*

ResNet 基本块用 \(3\times3\) 卷积，ImageNet 版本采用 batch normalization；当 feature map 尺寸变化或通道数增加时，shortcut 要用 stride 或 \(1\times1\) projection 对齐维度。课件比较 A（identity 加零填充）、B（维度增加时用 \(1\times1\) 投影）和 C（所有 shortcut 都投影），最终采用 B 作为后续常用设计。

### 6.3 ResNet 之后：密集连接、分组和多尺度

DenseNet 把此前各层特征**拼接**起来：

$$
x_l=H_l([x_0,x_1,\ldots,x_{l-1}]).
$$

因此后面的层可以直接读到更早的表示，而不只读相邻上一层。拼接要求 feature map 空间尺寸一致，所以 DenseNet 把网络分成多个 dense block；block 内尺寸保持不变，block 之间用 batch normalization、\(1\times1\) 卷积和平均池化压缩/下采样。

ResNeXt 把分支的 split–transform–aggregate 做成 grouped convolution 等结构，把不同变换分支并行后汇总。老师把它与 Inception 的多尺度支路联系起来：架构设计不只是加深，也是在寻找有用的 inductive bias 和模块化方式。

## 7. MobileNet 与 EfficientNet：从准确率扩展到效率

### 7.1 Depthwise separable convolution 怎么省计算

到 MobileNet，关注点从“只追分类准确率”扩展为“在移动设备上也能算得动”。普通卷积需要每个输入通道与每个输出通道之间都做空间卷积。若输入通道数为 \(M\)、输出通道数为 \(N\)、核边长为 \(D_k\)、特征图边长为 \(D_f\)，乘加量正比于：

$$
D_k^2 M N D_f^2.
$$

Depthwise separable convolution 分成两步：

1. **Depthwise convolution**：每个输入通道各用自己的 \(D_k\times D_k\) 核做空间滤波，不在这一步混合通道，代价 \(D_k^2 M D_f^2\)。
2. **Pointwise convolution**：再用 \(1\times1\) 卷积组合输入通道并产生 \(N\) 个输出通道，代价 \(MN D_f^2\)。

所以新旧计算量比例为：

$$
\frac{D_k^2 M D_f^2+MN D_f^2}{D_k^2MN D_f^2}
=\frac{1}{N}+\frac{1}{D_k^2}.
$$

当核是 \(3\times3\)、输出通道也不少时，计算量会明显下降。它不仅省参数/乘加，也把空间滤波与通道混合拆成两个职责不同的步骤。

![Depthwise convolution 先逐通道做空间滤波，再用 pointwise convolution 混合通道](/blog/2026/9-29/aims5710-depthwise-separable-convolution.png)

*图源：AIMS5710 课件《Different CNN Structures》，第 59 页，按 depthwise-separable 示意图裁切。*

MobileNetV2 在这条线上加入 inverted residual、linear bottleneck 和 depthwise convolution 等设计；课上提到 ReLU6（\(\min(\max(x,0),6)\)）作为受限数值范围下的非线性处理。老师比较了速度与准确率，说明这些结构是为高效率推理而设计，而不只是追更深。

### 7.2 EfficientNet 的 compound scaling 与 MBConv

常见扩模型方式有三种：增加 depth（层数）、width（通道数），或 resolution（输入图像分辨率）。EfficientNet 的 compound scaling 同时协调三者：

$$
d=\alpha^\phi,\qquad w=\beta^\phi,\qquad r=\gamma^\phi,
\qquad \alpha\beta^2\gamma^2\approx 2.
$$

这里 \(\phi\) 控制总资源预算；卷积计算量近似随 depth、width 的平方、resolution 的平方增长，所以约束 \(\alpha\beta^2\gamma^2\approx2\) 让资源增加时三个维度按较平衡的比例扩展。先找一个较好的 EfficientNet-B0 baseline，再按该规则生成更大的版本。

基本模块 MBConv 借鉴 MobileNet 的 inverted bottleneck 和 depthwise convolution，并使用 Squeeze-and-Excitation（SE）对不同通道进行重新加权。老师把它和前面 segmentation 中“上下文/通道注意力”的想法相连：根据整体特征调节通道重要性，而不是所有通道永远等权。

![EfficientNet 的 MBConv 与 Fused-MBConv 模块结构](/blog/2026/9-29/aims5710-mbconv-squeeze-excitation.png)

*图源：AIMS5710 课件《Different CNN Structures》，第 67 页，按 MBConv 示意图裁切。*

## 8. 优化开篇：梯度更新、动量、权重衰减与 Newton

### 8.1 经验风险与梯度下降

02:08 左右，老师从架构转到 optimization：前面已经求出了网络的梯度，现在要问怎样用梯度更新参数。给训练样本 \((x^{(i)},y^{(i)})\)，网络预测 \(\hat y^{(i)}=f(x^{(i)};\theta)\)，损失汇总成目标函数 \(J(\theta;D)\)。参数 \(\theta\) 的梯度是每个参数偏导组成的向量：

$$
\nabla J(\theta)=\left[\frac{\partial J}{\partial\theta_1},\ldots,
\frac{\partial J}{\partial\theta_P}\right]^T.
$$

梯度下降先沿负梯度走：

$$
\theta_{t+1}=\theta_t-\eta\nabla J(\theta_t),
$$

其中 \(\eta\) 是学习率。它决定每一步走多远：太小会走得慢，太大可能越过低谷。完整数据集上每轮计算所有样本梯度很贵，所以 mini-batch SGD 每步只抽一小批样本估计梯度。它更快，但估计会有噪声；mini-batch 要尽量兼顾样本与标签变化，也要大到足以支持 batch normalization（课件举例至少约 8 或 16）。

### 8.2 Momentum：把过去的方向也带进来

普通梯度下降每次只看当前位置的梯度，路径可能在狭长谷底两侧来回摆，学习率又必须兼顾“别太大”和“别太小”。课件把上一步的参数更新向量 \(\Delta\theta^{(t-1)}\) 比作速度，按以下方式平滑当前梯度：

$$
\Delta\theta^{(t)}
=\mu\Delta\theta^{(t-1)}+(1-\mu)\nabla J(\theta^{(t)}),
\qquad \Delta\theta^{(0)}=0,
$$

然后用这份方向更新参数：

$$
\theta^{(t+1)}=\theta^{(t)}-\eta\Delta\theta^{(t)}.
$$

按课件的写法，\(\mu\) 常设为 0.9。展开递推式后，当前更新会混合多次过去的梯度，越新的梯度权重越大；它能减轻突然改变方向造成的震荡，也可能更快沿稳定方向收敛。不同教材的 momentum 记号有时把 \(1-\mu\) 或学习率放在不同位置，复习时我按本课 slide 的定义来。

![课堂课件中的 Momentum 梯度路径与更新向量](/blog/2026/9-29/aims5710-optimization-momentum.png)

*图源：AIMS5710 课件《Optimization of Deep Neural Networks》，第 7 页，裁取动量示意图。*

### 8.3 Weight decay：把参数规模纳入目标

神经网络表达能力强，小数据上容易过拟合。课件把 L2 正则加到训练目标：

$$
J_{\mathrm{reg}}(\theta)
=J(\theta)+\frac{\lambda}{2}\|\theta\|_2^2.
$$

逐步对参数求梯度：

$$
\nabla_\theta J_{\mathrm{reg}}
=\nabla_\theta J+\frac{\lambda}{2}\nabla_\theta(\theta^T\theta)
=\nabla_\theta J+\lambda\theta,
$$

因为 \(\nabla_\theta(\theta^T\theta)=2\theta\)。代入普通 SGD：

$$
\theta_{t+1}
=\theta_t-\eta(\nabla J(\theta_t)+\lambda\theta_t)
=\theta_t-\eta\nabla J(\theta_t)-\eta\lambda\theta_t.
$$

最后一项会把参数往零缩，因此称 weight decay。课件还区分 decoupled weight decay：先按未加 L2 的原始损失算梯度，再单独做参数衰减。对最简单的 SGD，两种写法可化成相同更新；加上 momentum 或 adaptive optimizer 后，衰减是否进入梯度累积会改变算法，所以不能把一般情况下的 L2 与 decoupled decay 当作完全相同。

### 8.4 二阶信息和 Newton：在局部抛物面上找更好的步长

老师接着问为什么不直接用二阶信息。Hessian \(H=\nabla^2J(\theta)\) 是 \(P\times P\) 矩阵，每个元素是参数两两之间的二阶偏导。它记录目标函数在不同方向上的曲率。

在当前位置 \(\theta_t\) 附近，用二阶 Taylor 展开近似目标函数：

$$
J(\theta_t+\Delta\theta)
\approx J(\theta_t)+g_t^T\Delta\theta
+\frac12\Delta\theta^TH_t\Delta\theta,
$$

其中 \(g_t=\nabla J(\theta_t)\)，\(H_t=\nabla^2J(\theta_t)\)。现在把右边看成关于步长向量 \(\Delta\theta\) 的局部二次函数。逐步求它的最小点：

1. 常数项 \(J(\theta_t)\) 对 \(\Delta\theta\) 求导为 0。
2. 线性项 \(g_t^T\Delta\theta\) 的导数为 \(g_t\)。
3. 对称 Hessian 下，二次项 \(\frac12\Delta\theta^TH_t\Delta\theta\) 的导数为 \(H_t\Delta\theta\)。
4. 所以一阶条件是 \(g_t+H_t\Delta\theta=0\)。
5. 解这个线性方程，得到 \(\Delta\theta=-H_t^{-1}g_t\)。若定义 \(d=H_t^{-1}g_t\)，更新方向写成 \(\theta_{t+1}=\theta_t-\alpha d\)，再用 line search 选 \(\alpha\)。

在一维时它就是 Newton 法：利用当前位置附近的曲率来估算导数何时会到零，而不只拿一个固定学习率乘当前斜率。老师最后用切线/Taylor 近似解释这个图像，并讲到把近似导数设为零；转写在此处结束。

二阶方法的代价是 Hessian 对角线以外也有大量参数交互项。若模型有约 6000 万参数，稠密 Hessian 的尺寸约为 \(60{,}000{,}000\times60{,}000{,}000\)，显然不适合直接存储和求逆。这是深度学习大量采用一阶梯度方法、或设法近似二阶信息的原因之一。

## 9. 今晚的主线回看

我现在把今晚的内容串成一条线：卷积的局部连接和权重共享带来高效特征提取；stride、pooling 与 dilation 在分辨率和感受野间做取舍；卷积反传里输入梯度的核索引会反过来，权重梯度则把共享位置贡献求和；分割要用多尺度与跳连弥补下采样丢失的像素细节；CNN 架构不断在模块化、梯度流和计算效率之间折中；有了反传梯度后，优化方法再决定如何稳当地更新参数。

今晚 lecture 的重点范围到 Newton 的局部二次近似为止。虽然优化 PDF 接下来列出 Rprop、Adagrad、RMSprop、Adam/AdamW、初始化和多 GPU，但它们不在这份录音的实际讲授尾段里；我之后会等课堂讲到再补，不从目录倒推出“老师今天讲过”。
