---
slug: 3dgswm-manipulation
title: 
authors: bubblevan
tags: []
---

装模甲样阅读一下文献。
不过说来也巧，如果我选择去港科广读PhD的话通过connection这个组的研究方向就是这个，然后经过他们的几个月的考核，这样就不用被该死的committee折磨了，不过对我来说还是大三的PTSD更impressive一些，所以先冲个Master吧


黄思源是通讯作者，隶属于香港科技大学（广州）人工智能与数字经济实验室（**LAMDA**），主要研究方向为通用人工智能、机器人学习与 3D 视觉，但是一作是**THU**、**NTU**还有**BIGAI**，该团队聚焦通过 3D 表征与生成模型解决机器人操作的世界建模问题，即文章中 **GWM** 的研究方向

**GWM: Towards Scalable Gaussian World Models for Robotic Manipulation**这篇文章中了**ICCV 2025**
![](/blog/2025/gwm-overview.png)
该模型通过推断机器人动作作用下**高斯基元**（Gaussian primitives）的传播过程，实现对未来状态的重建。其核心是一个 latent **扩散 Transformer**（**Diffusion Transformer, DiT**），并结合了 **3D 变分自动编码器**（3D variational autoencoder），能够借助**高斯溅射**（Gaussian Splatting）技术完成细粒度的场景级未来状态重建

**GWM** 不仅能通过自监督未来预测训练，为模仿学习智能体增强视觉表征能力，还可作为支持**模型基强化学习**（model-based reinforcement learning, **MBRL**）的神经模拟器。模拟实验与真实世界实验均表明：**GWM** 能在不同机器人动作的条件下精准预测未来场景，且进一步用于策略训练时，其性能能以显著优势超越当前**SOTA**，充分展现了 3D 世界模型在初始数据扩展方面的潜力

基于视频的生成模型依赖图像输入，且缺乏 3D 几何与空间理解能力，因此易受未见过的视觉变化（如光照、相机姿态、纹理等）影响，尽管 RGB-D（彩色 - 深度）与多视图设置试图弥补这一差距，但在连贯的 3D 空间内隐式对齐图像块特征仍面临挑战

**3DGS**将点云等高效 3D 表示与高保真渲染相结合，然而，这些方法主要依赖离线逐场景重建，其计算需求给在机器人操作（尤其是**MBRL**）中的应用带来了重大挑战

![](/blog/2025/gwm-pipeline.png)

## Methodology
将真实世界的视觉输入编码为潜在 3DGS 表示，并利用基于扩散的条件生成模型，在给定机器人状态与动作的情况下，学习表示层面的动态特性
### World State Encoding
#### Feed-forward 3D Gaussian Splatting
给定某一世界状态的单视图或双视图图像输入$$I = \{I\}_{i=\{1,2\}}$$，的核心目标是先将场景编码为 3D 高斯表示，为后续动态学习与预测提供基础

3DGS采用多个非结构化 3D 高斯核$$G = \{x_p, \sigma_p, \Sigma_p, C_p\}_{p \in P}$$表示 3D 场景
> 每个高斯核是一个小的 3D 椭球，包含位置、大小、颜色等信息

其中：
$$x_p$$：高斯核中心；（3D 坐标）
$$\sigma_p$$：高斯核不透明度；（0-1，控制是否可见）
$$\Sigma_p$$：高斯核协方差矩阵；（控制椭球的形状和方向）
$$C_p$$：高斯核球谐系数。（存储颜色信息，支持视角相关颜色）

为从特定视角获取每个像素的颜色，3DGS 会将 3D 高斯核投影到图像平面，并按以下公式计算像素颜色：

$$C(G) = \sum_{p \in P} \alpha_p \cdot \text{SH}(d_p; C_p) \cdot \prod_{j=1}^{p-1} (1 - \alpha_j) \tag{1}$$
> 像素颜色 = 所有高斯核的贡献叠加

其中：
$$\alpha_p$$：按 z 深度排序的**有效不透明度**，即由协方差矩阵$$\Sigma_p$$得到的 2D 高斯权重与整体不透明度$$\sigma_p$$的乘积；
$$d_p$$：从相机到高斯核中心$$x_p$$的视角方向；
$$\text{SH}(\cdot)$$：球谐函数（spherical harmonics function）。由于基础版 **3D-GS**（vanilla 3D-GS）依赖耗时的逐场景离线优化，采用**可泛化 3D-GS** 学习 "从图像到 3D 高斯" 的前馈映射，以提升效率。

具体而言，通过 **Splatt3R** 模型获取 3D 高斯世界状态 $$G$$，该模型的实现流程为：

1. 首先利用立体重建模型 **Mast3R** 从输入图像生成 3D 点图
2. 再通过额外的预测头，基于这些 3D 点图预测每个 3D 高斯核的参数

流程示意：
```
输入图像 → Mast3R → 3D 点云
3D 点云 → 预测头 → 每个高斯核的参数
```

#### 3D Gaussian VAE

由于不同场景与任务中，每个世界状态对应的已学习 3D 高斯核数量差异显著，引入 **3D 高斯变分自动编码器**（$$E_\theta, D_\theta$$），将重建得到的 3D 高斯核 $$G$$ 编码为长度固定为 $$N$$ 的潜在嵌入 $$x \in \mathbb{R}^{N \times D}$$，具体步骤如下：

**下采样**：采用**最远点采样**（Farthest Point Sampling, **FPS**）将重建的 3D 高斯核 $$G$$ 下采样为固定数量 $$N$$ 的高斯核 $$G_N$$，即：

$$G_N = \text{FPS}(G)$$

**编码**：将下采样后的高斯核 $$G_N$$ 作为查询（query），通过一个 $$L$$ 层基于交叉注意力的编码器 $$E_\theta$$（参考 [94] 的设计），从所有高斯核 $$G$$ 中聚合信息并生成潜在嵌入 $$x$$，公式如下：

$$\begin{aligned}
X &= E_\theta (G_N, G) = E_\theta^{(L)} \circ \cdots \circ E_\theta^{(1)} (G_N, G), \\
E_\theta^{(l)} (Q, G) &= \text{LayerNorm}\left(\text{CrossAttn}\left(Q, \text{PosEmbed}(G)\right)\right) \tag{2}
\end{aligned}$$

**解码**：利用一个结构对称的基于 Transformer 的解码器 $$D_\theta$$，在潜在编码集合内传播并聚合信息，最终重建得到高斯核 $$\hat{G}$$，公式如下：

$$\hat{G} = D_\theta (x) = \text{LayerNorm}\left(\text{SelfAttn}(x, x)\right) \tag{3}$$

在 **3D 高斯变分自动编码器**（$$E_\theta, D_\theta$$）的训练过程中，采用两种损失函数进行监督：

- **倒角损失**（Chamfer Loss）：约束重建高斯核 $$\hat{G}$$ 与原始高斯核 $$G$$ 的中心对齐
- **渲染损失**（Rendering Loss）：确保重建高斯核 $$\hat{G}$$ 的渲染效果，为基于图像的策略提供高保真视觉输入

总损失函数公式如下：

$$\mathcal{L}_{\text{VAE}} = \text{Chamfer}(\hat{G}, G) + \left\| C(\hat{G}) - C(G) \right\|_1 \tag{4}$$

### Diffusion-based Dynamics Modeling

已知时刻 $$t$$ 的编码世界状态嵌入 $$x_t$$ 及其未来状态 $$x_{t+1}$$，的目标是学习世界动态 $$p(x_{t+1} | x_{\leq t}, a_{\leq t})$$（其中 $$x_{\leq t}$$、$$a_{\leq t}$$ 分别表示历史状态与历史动作）。

具体而言，构建基于扩散的动态模型，将动态学习转化为条件生成问题：以历史状态与动作 $$y_t = (x_{\leq t}, a_{\leq t})$$ 为条件，从噪声中生成未来状态 $$x_{t+1}$$。

#### 加噪过程

对真实未来状态 $$x_{t+1}^0 = x_{t+1}$$ 添加噪声，通过高斯扰动核得到带噪未来状态样本 $$x_{t+1}^\tau$$，公式如下：

$$p^{0 \to \tau} (x_{t+1}^\tau | x_{t+1}^0) = \mathcal{N}\left(x_{t+1}^\tau; x_{t+1}^0, \sigma^2(\tau) \cdot I\right) \tag{5}$$

其中：
- $$\tau$$：噪声步数索引
- $$\sigma(\tau)$$：**噪声调度**（noise schedule），用于控制不同步骤的噪声强度
- $$\mathcal{N}(\cdot; \mu, \Sigma)$$：正态分布，均值为 $$\mu$$，协方差矩阵为 $$\Sigma$$

上述扩散过程可表示为如下**随机微分方程**（SDE）的解：

$$dx = f(x, \tau) d\tau + g(\tau) dw \tag{6}$$

其中：
- $$w$$：标准维纳过程（Wiener process）
- $$f(x, \tau)$$：漂移系数（drift coefficient）
- $$g(\tau)$$：扩散系数（diffusion coefficient）

在高斯扰动核的设定下，漂移系数 $$f(x, \tau) = 0$$，扩散系数 $$g(\tau) = \sqrt{2 \cdot \dot{\sigma}(\tau) \cdot \sigma(\tau)}$$（$$\dot{\sigma}(\tau)$$ 为 $$\sigma(\tau)$$ 的导数）。

#### 逆时采样

为从噪声中生成未来状态，通过**逆时 SDE** 逆转公式（6）的扩散过程，实现采样：

$$dx = \left[ f(x, \tau) - g(\tau)^2 \cdot \nabla_x \log p^\tau(x) \right] d\tau + g(\tau) d\bar{w} \tag{7}$$

其中：
- $$\bar{w}$$：逆时维纳过程
- $$\nabla_x \log p^\tau(x)$$：**得分函数**（score function），即对数边缘概率关于 $$x$$ 的梯度，可通过网络估计

> BTW 这里引用的文献是真多，将来对 SDE 这里感兴趣的话看看它的 Reference 吧

#### 条件去噪模型训练

通过最小化 "采样未来状态 $$\hat{x}_{t+1}^0 = D_\theta(x_{t+1}^\tau, y_t)$$" 与 "真实未来状态 $$x_{t+1}^0$$" 的差异，学习条件去噪模型 $$D_\theta$$，损失函数如下：

$$\mathcal{L}(\theta) = \mathbb{E}\left[ \left\| D_\theta(x_{t+1}^\tau, y_t^\tau) - x_{t+1}^0 \right\|_2^2 \right] \tag{8}$$

其中 $$\mathbb{E}[\cdot]$$ 表示期望，$$\|\cdot\|_2^2$$ 表示 L2 平方范数。

如文献 [[33] Tero Karras, Miika Aittala, Timo Aila, and Samuli Laine. Elucidating the design space of diffusion-based generative models. Advances in Neural Information Processing Systems, 35:26565–26577, 2022. 4, A1] 所指出，直接学习去噪器 $$D_\theta(x_{t+1}^\tau, y_t)$$ 易受噪声幅度变化的影响。

因此，参考 [[1] Eloi Alonso, Adam Jelley, Vincent Micheli, Anssi Kanervisto, Amos Storkey, Tim Pearce, and François Fleuret. Diffusion for world modeling: Visual details matter in atari] 的思路，采用 **EDM**（Elucidating the Design Space of Diffusion-Based Generative Models）[33] 中的预处理策略，转而学习网络 $$F_\theta$$。

具体而言，将去噪器 $$D_\theta(x_{t+1}^\tau, y_t^\tau)$$ 参数化为：

$$D_\theta(x_{t+1}^\tau, y_t^\tau) = c_{\text{skip}}^\tau \cdot x_{t+1}^\tau + c_{\text{out}}^\tau \cdot F_\theta\left( c_{\text{in}}^\tau \cdot x_{t+1}^\tau, y_t^\tau; c_{\text{noise}}^\tau \right) \tag{9}$$

其中：
- $$c_{\text{in}}^\tau$$、$$c_{\text{out}}^\tau$$：输入 / 输出幅度缩放预处理器
- $$c_{\text{skip}}^\tau$$：跳跃连接调节预处理器
- $$c_{\text{noise}}^\tau$$：噪声水平映射预处理器，将噪声强度作为额外条件输入到 $$F_\theta$$ 中

预处理器的详细设计见附录 B.1。

基于上述参数化，可将公式（8）的损失函数重写为：

$$\mathcal{L}(\theta) = \mathbb{E}\left[ \left\| F_\theta\left( c_{\text{in}}^\tau \cdot x_{t+1}^\tau, y_t^\tau \right) - \frac{1}{c_{\text{out}}^\tau} \left( x_{t+1}^0 - c_{\text{skip}}^\tau \cdot x_{t+1}^\tau \right) \right\|_2^2 \right] \tag{10}$$

这一转化的核心价值在于：根据噪声调度 $$\sigma(\tau)$$ 自适应混合信号与噪声，为网络 $$F_\theta$$ 构建更优的训练目标 —— 在高噪声水平下（$$\sigma(\tau) \gg \sigma_{\text{data}}$$），$$c_{\text{skip}}^\tau \to 0$$，网络主要学习预测干净信号；在低噪声水平下（$$\sigma(\tau) \to 0$$），$$c_{\text{skip}}^\tau \to 1$$，网络目标转为预测噪声分量，避免损失函数趋于 trivial（无学习价值）。
#### 技术实现

在技术实现上，采用**扩散 Transformer**（**DiT**）构建网络 $$F_\theta$$，具体流程如下：

1. **带噪潜在生成**：给定真实世界状态潜在嵌入序列 $$\{x_t^0 = x_t\}_{t=1}^T$$，根据公式（5）的高斯扰动生成带噪潜在序列 $$\{x_t^\tau\}_{t=1}^T$$

2. **输入构建**：将带噪潜在嵌入与**旋转位置嵌入**（**RoPE**）拼接，作为 **DiT** 的输入

3. **条件融入**：对于条件 $$y_t = (x_{\leq t}^0, a_{\leq t}, c_{\text{noise}}^\tau)$$，通过**自适应层归一化**（**AdaLN**）调制时序嵌入，并将当前机器人动作作为 **DiT** 交叉注意力层的键（key）与值（value），实现条件生成

4. **训练稳定性优化**：为保证所有注意力机制的稳定性与效率，采用带可学习缩放因子的**均方根归一化**（**RMSNorm**），在处理空间表示的同时，将时序动作序列作为条件融入训练

### GWM for Policy Learning

#### GWM for RL

从形式化定义来看，**马尔可夫决策过程**（**MDP**）由元组 $$(S, A, p, r, \gamma, \rho_0)$$ 描述，其中：
- $$S$$、$$A$$：分别为状态空间与动作空间
- $$\gamma$$：折扣因子
- $$r(s, a)$$：奖励函数
- $$\rho_0$$：初始状态分布

**MBRL** 的核心目标是：在通过策略滚动采样（policy roll-outs）构建动态模型 $$p_\theta(s_{t+1}, r_t | s_t, a_t)$$ 的同时，学习使 "期望折扣奖励和" 最大化的策略 $$\pi^*$$，即：

$$\pi^* = \arg\max_\pi \mathbb{E}_\pi \left[ \sum_{t=0}^{\infty} \gamma^t r_t \right]$$

**Algorithm 1: Monotonic Model-Based Policy Optimization (MBPO) with Gaussian World Model**

```
for N epochs do
    Initialize policy π(at|st), Gaussian world model pθ(st+1, rt|st, at), empty replay buffer B;
    Collect data with π in real environment:
        B = B ∪ {(st, at, st+1, rt)}t;
    Train Gaussian world model pθ on dataset B via maximum likelihood:
        θ ← arg maxθ EB[log pθ(st+1, rt|st, at)];
    Optimize policy under predictive model:
        π ← arg maxπ Eπ[∑t≥0 γ^t rt];
end
```

在该框架下，在 **GWM** 基础上新增一个**奖励预测头**，用于参数化动态模型 $$p_\theta(s_{t+1}, r_t | s_t, a_t)$$。为提升视觉操作任务的性能，参考 [Jialong Wu, Shaofeng Yin, Ningya Feng, Xu He, Dong Li, Jianye Hao, and Mingsheng Long. ivideogpt: Interactive videogpts are scalable world models. Proceedings of Advances in Neural Information Processing Systems (NeurIPS)] 的设计选择构建基础强化学习策略。

#### GWM for IL

在**模仿学习**（**IL**）场景中，将 **GWM** 作为更高效的编码器，为策略学习提供更优特征。

具体而言，提取扩散过程中 "**第一步去噪后的特征向量**"，作为下游策略模型（如**行为克隆 Transformer**（**BC-transformer**）、**扩散策略**（diffusion policy））的输入 —— 第一步去噪后的特征能保留具有代表性的空间信息，可有效应对较高的噪声水平。

在实现过程中，采用 "**按序列块预测动作**" 的方式，确保机器人控制的一致性。