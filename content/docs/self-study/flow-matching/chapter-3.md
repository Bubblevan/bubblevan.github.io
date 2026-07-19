# Training Flow and Diffusion Models

在前两节中，我们展示了如何利用神经网络给出的向量场 \(u_{t}^{\theta}\) 构建**生成模型**，并推导了**训练目标** \(u_{t}^{\text{target}}\) 的公式。在本节中，我们将介绍如何训练神经网络 \(u_{t}^{\theta}\) 以逼近训练目标 \(u_{t}^{\text{target}}\)。首先，我们再次将讨论范围限定在**常微分方程（ODEs）**上，通过这种方式恢复**流匹配**。其次，我们将说明如何通过**分数匹配**将该方法扩展到**随机微分方程（SDEs）**。最后，我们将考虑**高斯概率路径**这一特殊情况，由此恢复**去噪扩散模型**。借助这些工具，我们最终将获得一个端到端的流程，用于训练基于常微分方程和随机微分方程的生成模型并从中采样。

## 流匹配 (Flow Matching)

如前所述，让我们考虑由
\[X_{0} \sim p_{\text{init}}, \quad \mathrm{d} X_{t}=u_{t}^{\theta}\left(X_{t}\right) \mathrm{d} t . \quad \text{Flow Model (40)}\]
给出的**流模型**。
流模型的训练目标是让神经网络向量场 \(u_t^\theta(x)\) 逼近 **边缘向量场** \(u_t^{\text{target}}(x)\)（全局通用导航，能让 ODE 轨迹从噪声→数据）。但有个关键问题：边缘向量场的公式是积分形式（式 43）：\(u_t^{\text{target}}(x) = \int u_t^{\text{target}}(x|z) \cdot \frac{p_t(x|z)p_{\text{data}}(z)}{p_t(x)} \mathrm{d}z\)。

这个积分 **难处理（intractable）**—— 计算量极大，工程上没法实现。于是换个思路：既然 **条件向量场** \(u_t^{\text{target}}(x|z)\)（单个数据 \(z\) 的专属导航）有解析公式（能直接算），那能不能用它替代边缘向量场来训练？

> **请注意区别**：我们使用**条件向量场** \(u_{t}^{\text{target}}(x | z)\)，而非**边缘向量场** \(u_{t}^{\text{target}}(x)\)。由于我们拥有 \(u_{t}^{\text{target}}(x | z)\) 的解析公式，因此可以轻松地最小化上述损失。但问题是，如果我们关注的是边缘向量场，那么对条件向量场进行回归有什么意义呢？事实证明，通过明确地对易于处理的条件向量场进行回归，我们是在间接地对难以处理的边缘向量场进行回归。

**定理 18**

**边际流匹配损失 (Marginal Flow Matching Loss)** \(\mathcal{L}_{FM}(\theta)\)
\[\mathcal{L}_{FM}(\theta)=\mathbb{E}_{t\sim \text{Unif},z\sim p_{\text{data}},x\sim p_{t}(\cdot|z)}[\|u_{t}^{\theta}(x)-u_{t}^{\text{target}}(x)\|^{2}]\]
**直观含义**：
*   **抽随机时间** \(t\in[0,1]\)（覆盖噪声→数据的全过渡阶段）；
*   **抽数据** \(z\)、从条件概率路径 \(p_t(\cdot|z)\) **采带噪声的** \(x\)（比如加 \(\epsilon\) 噪声）；
*   **算神经网络输出** \(u_t^\theta(x)\) 与 **边际向量场** \(u_t^{\text{target}}(x)\) 的**均方误差 (MSE)**。

**问题**：\(u_t^{\text{target}}(x)\) 算不了，所以这个损失只是 “**理想目标**”，没法直接用。

利用条件向量场 \(u_{t}^{\text{target}}(x | z)\) 是可处理的这一事实，定义**条件流匹配损失**
\[\mathcal{L}_{\text{CFM}}(\theta)=\mathbb{E}_{t \sim \text{Unif}, z \sim p_{\text{data}}, x \sim p_{t}(\cdot | z)}\left[\left\| u_{t}^{\theta}(x)-u_{t}^{\text{target}}(x | z)\right\| ^{2}\right] . (44)\]
**核心修改**：把 “**边际向量场** \(u_t^{\text{target}}(x)\)” 换成 “**条件向量场** \(u_t^{\text{target}}(x|z)\)”。

**关键优势**：\(u_t^{\text{target}}(x|z)\) 有 **解析公式**（比如高斯路径下的式 47），能直接计算，所以这个损失能落地优化。

**边缘流匹配损失**等于**条件流匹配损失**加上一个常数。即：

\[\mathcal{L}_{\text{FM}}(\theta)=\mathcal{L}_{\text{CFM}}(\theta)+C\]

其中 \(C\) 与 \(\theta\) 无关。因此，它们的梯度一致：

\[\nabla _{\theta }\mathcal {L}_{\text{FM}}(\theta )=\nabla _{\theta }\mathcal {L}_{\text{CFM}}(\theta ).\]

因此，使用例如 **随机梯度下降（SGD）** 最小化 \(\mathcal{L}_{\text{CFM}}(\theta)\)，等价于以相同方式最小化 \(\mathcal{L}_{\text{FM}}(\theta)\)。特别是，对于 \(\mathcal{L}_{\text{CFM}}(\theta)\) 的最小值点 \(\theta^{*}\)，将有 \(u_{t}^{\theta^{*}}=u_{t}^{\text{target}}\) 成立（假设参数化具有无限的表达能力）。

**证明**：该证明通过将均方误差展开为三个部分并移除常数项来完成：

\[\begin{aligned}
\mathcal {L}_{FM}(\theta )
&\overset {(i)}{=}\mathbb {E}_{t\sim \text{Unif},x\sim p_{t}}\left[\| u_{t}^{\theta }(x)-u_{t}^{target}(x)\| ^{2}\right]\\
&\overset {(ii)}{=}\mathbb {E}_{t\sim \text{Unif},x\sim p_{t}}\left[\| u_{t}^{\theta }(x)\| ^{2}-2u_{t}^{\theta }(x)^{T}u_{t}^{target}(x)+\| u_{t}^{target}(x)\| ^{2}\right]\\
&\overset {(iii)}{=}\mathbb {E}_{t\sim \text{Unif},x\sim p_{t}}\left[ \| u_{t}^{\theta }(x)\| ^{2}\right]
-2\mathbb {E}_{t\sim \text{Unif},x\sim p_{t}}\left[ u_{t}^{\theta }(x)^{T}u_{t}^{target}(x)\right]
+\underbrace {\mathbb {E}_{t\sim \text{Unif}_{[0,1]},x\sim p_{t}}\left[\left\| u_{t}^{target}(x)\right\| ^{2}\right] }_{=:C_{1}}\\
&\overset {(iv)}{=}\mathbb {E}_{t\sim \text{Unif},z\sim p_{data},x\sim p_{t}(\cdot | z)}\left[ \left\| u_{t}^{\theta }(x)\right\| ^{2}\right]
-2\mathbb {E}_{t\sim \text{Unif},x\sim p_{t}}\left[ u_{t}^{\theta }(x)^{T}u_{t}^{target}(x)\right] +C_{1}
\end{aligned}\]
其中，(i) 由定义直接得到；在 \((ii)\) 中我们使用了公式 \(\|a-b\|^{2}=\|a\|^{2}-2 a^{T} b+\|b\|^{2}\)；在 (iii) 中我们定义了常数 \(C_{1}\)；在 \((iv)\) 中我们使用了式 (13) 给出的 \(p_{t}\) 的采样过程。下面我们重新改写第二项：  
\[\begin{aligned} \mathbb{E}_{t \sim Unif, x \sim p_{t}}\left[u_{t}^{\theta}(x)^{T} u_{t}^{target }(x)\right] & \stackrel{(i)}{=} \int_{0}^{1} \int p_{t}(x) u_{t}^{\theta}(x)^{T} u_{t}^{target }(x) d x d t \\ & \stackrel{(i i)}{=} \int_{0}^{1} \int p_{t}(x) u_{t}^{\theta}(x)^{T}\left[\int u_{t}^{target }(x | z) \frac{p_{t}(x | z) p_{data }(z)}{p_{t}(x)} d z\right] d x d t \\ & \stackrel{(i i i)}{=} \int_{0}^{1} \iint u_{t}^{\theta}(x)^{T} u_{t}^{target }(x | z) p_{t}(x | z) p_{data }(z) d z d x d t \\ & \stackrel{(i v)}{=} \mathbb{E}_{t \sim Unif, z \sim p_{data }, x \sim p_{t}(\cdot | z)}\left[u_{t}^{\theta}(x)^{T} u_{t}^{target }(x | z)\right] \end{aligned}\]

其中，在 (i) 中我们将期望值表示为积分；在 \((ii)\) 中我们使用了式 (43)；在 (iii) 中我们利用了积分的线性性质；在 \((iv)\) 中我们将积分表示为期望值。

等式的开头使用了**边缘向量场** \(u_{t}^{\text{target}}(x)\)，而结尾使用了**条件向量场** \(u_{t}^{\text{target}}(x | z)\)。我们将其代入 \(\mathcal{L}_{\text{FM}}\) 的方程中，得到：

\[\begin{aligned}
\mathcal {L}_{\text{FM}}(\theta )
&\stackrel {(i)}{=}\mathbb {E}_{t\sim \text{Unif},z\sim p_{\text{data}},x\sim p_{t}(\cdot | z)}\left[\| u_{t}^{\theta }(x)\| ^{2}\right]
-2\mathbb {E}_{t\sim \text{Unif},z\sim p_{\text{data}},x\sim p_{t}(\cdot | z)}\left[u_{t}^{\theta }(x)^{T}u_{t}^{\text{target}}(x|z)\right]+C_{1}\\
&\overset {(ii)}{=}\mathbb {E}_{t\sim \text{Unif},z\sim p_{\text{data}},x\sim p_{t}(\cdot | z)}\left[\| u_{t}^{\theta }(x)\| ^{2}-2u_{t}^{\theta }(x)^{T}u_{t}^{\text{target}}(x|z)+\| u_{t}^{\text{target}}(x|z)\| ^{2}-\| u_{t}^{\text{target}}(x|z)\| ^{2}\right]+C_{1}\\
&\overset {(iii)}{=}\mathbb {E}_{t\sim \text{Unif},z\sim p_{\text{data}},x\sim p_{t}(\cdot | z)}\left[\| u_{t}^{\theta }(x)-u_{t}^{\text{target}}(x|z)\| ^{2}\right]
+\underbrace {\mathbb {E}_{t\sim \text{Unif},z\sim p_{\text{data}},x\sim p_{t}(\cdot | z)}\left[ -\| u_{t}^{\text{target}}(x|z)\| ^{2}\right] }_{C_{2}}+C_{1}\\
&\overset {(iv)}{=}\mathcal {L}_{\text{CFM}}(\theta )+\underbrace {C_{2}+C_{1}}_{=:C}.
\end{aligned}\]

其中，在 (i) 中我们代入了推导得出的方程；在 \((ii)\) 中我们添加并减去了相同的值；在 (iii) 中我们再次使用了公式 \(\|a-b\|^{2}=\|a\|^{2}-2 a^{T} b+\|b\|^{2}\)；在 (iv) 中我们在 \(\theta\) 中定义了一个常数。至此，证明完毕。

一旦训练好 \(u_{t}^{\theta}\)，我们就可以通过例如算法1来模拟流模型
\[\mathrm{d}X_{t}=u_{t}^{\theta }(X_{t})\, \mathrm{d}t, \quad X_{0} \sim p_{\text{init}} \quad (45)\]
，以获得样本 \(X_{1} \sim p_{\text{data}}\)。这整个流程在文献[14, 16, 1, 15]中被称为流匹配。训练过程总结于算法5，并在图9中进行了可视化展示。
![](/img/flow-matching/f9.png)
**图9：使用高斯CondOT概率路径对定理18的说明：从训练后的流匹配模型模拟常微分方程。数据分布为棋盘图案（右上角）。上行：来自真实边缘概率路径\(p_{t}(x)\)的直方图。下行：来自流匹配模型的样本直方图。可以看到，训练后上行和下行匹配（存在训练误差）。该模型使用算法5进行训练。**

现在，让我们针对高斯概率路径的选择来实例化条件流匹配损失：

条件概率路径：\(p_t(x|z) = \mathcal{N}(\alpha_t z, \beta_t^2 I_d)\)（α_t、β_t 是噪声调度器，α_t 从 0→1，β_t 从 1→0）；

采样 x：\(x = \alpha_t z + \beta_t \epsilon\)（ε 是高斯噪声，\(\epsilon \sim \mathcal{N}(0, I_d)\)）；

条件向量场（解析公式，式 47）：
\(u_t^{target}(x|z) = (\dot{\alpha}_t - \frac{\dot{\beta}_t}{\beta_t}\alpha_t)z + \frac{\dot{\beta}_t}{\beta_t}x\)。

其中 \(\dot{\alpha}_{t}=\partial_{t} \alpha_{t}\) 和 \(\dot{\beta}_{t}=\partial_{t} \beta_{t}\) 是各自的时间导数。

代入L_CFM这个公式，条件流匹配损失为
\[\begin{aligned} \mathcal{L}_{\text{CFM}}(\theta) & =\mathbb{E}_{t \sim \text{Unif}, z \sim p_{\text{data}}, x \sim \mathcal{N}\left(\alpha_{t} z, \beta_{t}^{2} I_{d}\right)}\left[\left\| u_{t}^{\theta}(x)-\left(\dot{\alpha}_{t}-\frac{\dot{\beta}_{t}}{\beta_{t}} \alpha_{t}\right) z-\frac{\dot{\beta}_{t}}{\beta_{t}} x\right\| ^{2}\right] \\ & \stackrel{(i)}{=} \mathbb{E}_{t \sim \text{Unif}, z \sim p_{\text{data}}, \epsilon \sim \mathcal{N}\left(0, I_{d}\right)}\left[\left\| u_{t}^{\theta}\left(\alpha_{t} z+\beta_{t} \epsilon\right)-\left(\dot{\alpha}_{t} z+\dot{\beta}_{t} \epsilon\right)\right\| ^{2}\right] \end{aligned}\]
，其中在（i）中我们代入了式（46）并用 \(\alpha_{t} z+\beta_{t} \epsilon\) 替换了 \(x\)。

注意 \(\mathcal{L}_{\text{CFM}}\) 的简洁性：我们采样一个数据点 \(z\)，采样一些噪声 \(\epsilon\)，然后计算均方误差。

让我们针对 \(\alpha_{t}=t\) 和 \(\beta_{t}=1-t\) 的特殊情况使其更加具体。相应的概率 \(p_{t}(x | z)=\mathcal{N}(t z,(1-t)^{2})\) 有时被称为（高斯）CondOT概率路径。然后我们有 \(\dot{\alpha}_{t}=1\)、\(\dot{\beta}_{t}=-1\)，因此
\[\mathcal{L}_{\text{CFM}}(\theta )=\mathbb {E}_{t\sim \text{Unif},z\sim p_{\text{data}},\epsilon \sim \mathcal {N}(0,I_{d})}[\| u_{t}^{\theta }(tz+(1-t)\epsilon )-(z-\epsilon )\| ^{2}]\]

**算法 3：流匹配训练过程（高斯 CondOT 路径）**

```text
Algorithm 3 Flow Matching Training Procedure (Gaussian CondOT path p_t(x|z)=N(t z, (1-t)^2))
Require: dataset samples z ~ p_data, neural network u_t^θ
1: for each mini-batch of data do
2:   sample z from the dataset
3:   sample t ~ Unif[0,1]
4:   sample ε ~ N(0, I_d)
5:   set x = t z + (1-t) ε        (general case: x ~ p_t(·|z))
6:   compute loss: L(θ) = ||u_t^θ(x) - (z - ε)||^2
     (general case: ||u_t^θ(x) - u_t^target(x|z)||^2)
7:   update θ via gradient descent on L(θ)
8: end for
```

## Score Matching
让我们将刚刚找到的算法从常微分方程（ODEs）扩展到随机微分方程（SDEs）：

\[\begin{aligned}
dX_{t}
&=\left[ u_{t}^{target}(X_{t})+\frac {\sigma _{t}^{2}}{2}\nabla \log p_{t}(X_{t})\right] dt+\sigma _{t}dW_{t} \quad (48)
\end{aligned}\]

\[X_{0} \sim p_{init} \quad (49)\]

\[\Rightarrow X_{t} \sim p_{t} \quad(0 \leq t \leq 1) (50)\]

其中，\(u_{t}^{target }\) 是边缘向量场，\(\nabla \log p_{t}(x)\) 是通过公式
\[\nabla \log p_{t}(x)=\int \nabla \log p_{t}(x | z) \frac{p_{t}(x | z) p_{data }(z)}{p_{t}(x)} d z . \quad (51)\]
表示的边缘得分函数。

**边缘得分函数** \(\nabla \log p_{t}(x)\)：全局的“引力场”，但它是积分形式（式 51），**难算 (intractable)** —— 需要遍历所有数据点 \(z\)，工程上做不到。

**条件得分函数** \(\nabla \log p_{t}(x|z)\)：单个数据点 \(z\) 的“专属引力场”，在一些路径（如高斯路径）下有解析公式，能直接计算。

为了逼近边缘得分 \(\nabla \log p_{t}\)，我们用一个神经网络（分数网络）
\[s_{t}^{\theta}: \mathbb{R}^{d} \times [0,1] \to \mathbb{R}^{d}.\]
与之前相同，我们可以设计一个分数匹配损失和一个条件分数匹配损失：

**理想但无用**：边缘分数匹配损失 \(\mathcal{L}_{SM}(\theta)\)。想让分数网络 \(s_t^\theta(x)\) 逼近边缘得分，但 \(\nabla \log p_{t}(x)\) 算不了，只能是“理想目标”。
\[\mathcal {L}_{SM}(\theta )=\mathbb {E}_{t\sim \text{Unif},z\sim p_{data},x\sim p_{t}(\cdot |z)}\left[ \| s_{t}^{\theta }(x)-\nabla \log p_{t}(x)\| ^{2}\right]\]

**实用且可算**：条件分数匹配损失 \(\mathcal{L}_{CSM}(\theta)\)。把目标换成“条件得分 \(\nabla \log p_{t}(x|z)\)”，条件得分能解析算，损失能直接优化。
\[\mathcal {L}_{CSM}(\theta)=\mathbb{E}_{t \sim \text{Unif}, z \sim p_{data }, x \sim p_{t}(\cdot | z)}\left[\left\| s_{t}^{\theta}(x)-\nabla \log p_{t}(x | z)\right\| ^{2}\right]\]

其中的区别再次在于使用边缘得分 \(\nabla \log p_{t}(x)\) 还是使用条件得分 \(\nabla \log p_{t}(x | z)\)。和之前一样，我们无法直接最小化边缘分数匹配损失，但条件分数匹配损失是一个易于处理的替代方案：

**定理 20**
得分匹配损失等于条件得分匹配损失加上一个常数：

\[\mathcal{L}_{SM}(\theta)=\mathcal{L}_{CSM}(\theta)+C,\]

其中 \(C\) 与参数 \(\theta\) 无关。因此，它们的梯度一致：

\[\nabla_{\theta} \mathcal{L}_{SM}(\theta)=\nabla_{\theta } \mathcal{L}_{CSM}(\theta)\]

特别是，对于极小值点 \(\theta^{*}\)，将有 \(s_{t}^{\theta^{*}}=\nabla \log p_{t}\) 成立。

**证明**：注意到 \(\nabla \log p_{t}\) 的公式（式 51）与 \(u_{t}^{target }\) 的公式（式 43）形式相同。因此，本证明与定理 18 的证明相同，只需将 \(u_{t}^{target }\) 替换为 \(\nabla \log p_{t}\) 即可。

上述过程描述了扩散模型的基本训练过程。训练完成后，我们可以选择任意的扩散系数 \(\sigma_{t} \ge 0\)，然后模拟 SDE
\[\begin{aligned}
X_{0} &\sim p_{init},\\
dX_{t} &=\left[ u_{t}^{\theta }(X_{t})+\frac {\sigma _{t}^{2}}{2}s_{t}^{\theta }(X_{t})\right] dt+\sigma _{t}dW_{t}. \quad (52)
\end{aligned}\]
来生成样本\(X_{1} ~ p_{data }\)。理论上，在完美训练的情况下，每个\(\sigma_{t}\)都应该生成样本\(X_{1} ~ p_{data }\)。在实际操作中，我们会遇到两类误差：（1）由于SDE模拟不完善导致的数值误差；（2）训练误差。（即，模型\(u_{t}^{\theta}\)并不完全等于\(u_{t}^{target }\)）。因此，存在一个最优的未知噪声水平\(\sigma_{t}\)——这可以通过凭经验测试不同的值来凭经验确定（例如参见[1,12,17]）。乍一看，如果我们现在想使用扩散模型而不是流模型，就必须同时学习\(s_{t}^{\theta}\)和\(u_{t}^{\theta}\)，这似乎是一个缺点。然而，请注意，我们通常可以在一个具有两个输出的单一网络中直接实现\(s_{t}^{\theta}\)和\(u_{t}^{\theta}\)，因此额外的计算量通常是最小的。此外，正如我们将要看到的，对于高斯概率路径这一特殊情况，\(s_{t}^{\theta}\)和\(u_{t}^{\theta}\)可以相互转换，因此我们不必分别对它们进行训练。

### 去噪扩散模型
在本文档中，这些模型只是具有高斯概率路径的扩散模型\(p_{t}(\cdot | z)=N(\alpha_{t} z ; \beta_{t}^{2} I_{d})\)
首先，让我们为\(p_{t}(x | z)=N(\alpha_{t} z, \beta_{t}^{2} I_{d})\)的情况实例化去噪分数匹配损失。正如我们在公式（28）中推导的那样，条件分数 \(\nabla \log p_{t}(x | z)\) 的公式为
\[\nabla \log p_{t}(x | z)=-\frac{x-\alpha_{t} z}{\beta_{t}^{2}} . \quad (53)\]
代入这个公式，条件得分匹配损失变为：

\[\begin{aligned} \mathcal{L}_{CSM}(\theta) & =\mathbb{E}_{t \sim Unif, z \sim p_{data }, x \sim p_{t}(\cdot | z)}\left[\| s_{t}^{\theta}(x)+\frac{x-\alpha_{t} z}{\beta_{t}^{2}}\right\| ^{2}] \\ & \stackrel{(i)}{=} \mathbb{E}_{t \sim Unif, z \sim p_{data }, \epsilon \sim \mathcal{N}\left(0, I_{d}\right)}\left[\left\| s_{t}^{\theta}\left(\alpha_{t} z+\beta_{t} \epsilon\right)+\frac{\epsilon}{\beta_{t}}\right\| ^{2}\right] \\ & =\mathbb{E}_{t \sim Unif, z \sim p_{data }, \epsilon \sim \mathcal{N}\left(0, I_{d}\right)}\left[\frac{1}{\beta_{t}^{2}}\left\| \beta_{t} s_{t}^{\theta}\left(\alpha_{t} z+\beta_{t} \epsilon\right)+\epsilon\right\| ^{2}\right] \end{aligned}\]

其中在（i）中，我们代入了式（46），并用\(\alpha_{t} z+\beta_{t} \epsilon\)替换了x。注意，网络\(s_{t}^{\theta}\)本质上是学习预测用于破坏数据样本z的噪声。因此，上述训练损失也被称为去噪得分匹配，它是最早用于学习扩散模型的方法之一。人们很快意识到，当\(\beta_{t} \approx 0\)接近零时，上述损失在数值上是不稳定的（即只有加入足够量的噪声，去噪得分匹配才有效）。因此，在一些关于去噪扩散模型的早期研究中（参见《DDPM》，[9]），有人提议去掉损失中的常数\(\frac{1}{\beta_{t}^{2}}\)，并通过以下方式将\(s_{t}^{\theta}\)重新参数化为噪声预测器网络\(\epsilon_{t}^{\theta}: \mathbb{R}^{d} \times[0,1] \to \mathbb{R}^{d}\)：

\[-\beta_{t} s_{t}^{\theta}(x)=\epsilon_{t}^{\theta}(x) \Rightarrow \mathcal{L}_{DDPM}(\theta)=\mathbb{E}_{t \sim Unif, z \sim p_{data }, \epsilon \sim \mathcal{N}\left(0, I_{d}\right)}\left[\left\| \epsilon_{t}^{\theta}\left(\alpha_{t} z+\beta_{t} \epsilon\right)-\epsilon\right\| ^{2}\right]\]

**算法 4：得分匹配训练过程（高斯概率路径）**

```text
Algorithm 4 Score Matching Training Procedure (Gaussian probability path)
Require: dataset samples z ~ p_data, score network s_t^θ or noise predictor ε_t^θ
1: for each mini-batch of data do
2:   sample z from the dataset
3:   sample t ~ Unif[0,1]
4:   sample ε ~ N(0, I_d)
5:   set x_t = α_t z + β_t ε           (general case: x_t ~ p_t(·|z))
6:   compute loss:
     L(θ) = || s_t^θ(x_t) + ε/β_t ||^2
     (general case: || s_t^θ(x_t) - ∇ log p_t(x_t|z) ||^2)
     alternatively:
     L(θ) = || ε_t^θ(x_t) - ε ||^2
7:   update θ via gradient descent on L(θ)
8: end for
```

### 高斯路径优势
除了其简单性之外，高斯概率路径还有另一个有用的特性：学习 \(s_{t}^{\theta}\) 或 \(\epsilon_{t}^{\theta}\) 时，也会“自动”学到 \(u_{t}^{\theta}\)，反之亦然：

**命题 1（高斯概率路径的转换公式）**

对于高斯概率路径 \(p_{t}(x | z)=\mathcal{N}(\alpha_{t} z, \beta_{t}^{2} I_{d})\)，条件（以及边缘）向量场可以转换为条件（以及边缘）得分：

\[u_{t}^{target}(x|z)=\left( \beta _{t}^{2}\frac {\dot {\alpha }_{t}}{\alpha _{t}}-\dot {\beta }_{t}\beta _{t}\right)\nabla \log p_{t}(x|z)+\frac {\dot {\alpha }_{t}}{\alpha _{t}}x\]

\[u_{t}^{target}(x)=\left( \beta _{t}^{2}\frac {\dot {\alpha }_{t}}{\alpha _{t}}-\dot {\beta }_{t}\beta _{t}\right)\nabla \log p_{t}(x)+\frac {\dot {\alpha }_{t}}{\alpha _{t}}x\]

其中，上述边缘向量场\(u_{t}^{target }\)的公式在文献中被称为概率流常微分方程（更准确地说，是相应的常微分方程）。

**证明**：对于条件向量场和条件得分，我们可以推导出：

\[\begin{aligned}
u_{t}^{target}(x|z)
&=\left( \dot {\alpha }_{t}-\frac {\dot {\beta }_{t}}{\beta _{t}}\alpha _{t}\right) z+\frac {\dot {\beta }_{t}}{\beta _{t}}x\\
&\stackrel {(i)}{=}\left( \beta _{t}^{2}\frac {\dot {\alpha }_{t}}{\alpha _{t}}-\dot {\beta }_{t}\beta _{t}\right)\left( \frac {\alpha _{t}z-x}{\beta _{t}^{2}}\right) +\frac {\dot {\alpha }_{t}}{\alpha _{t}}x\\
&=\left( \beta _{t}^{2}\frac {\dot {\alpha }_{t}}{\alpha _{t}}-\dot {\beta }_{t}\beta _{t}\right)\nabla \log p_{t}(x | z)+\frac {\dot {\alpha }_{t}}{\alpha _{t}}x
\end{aligned}\]

其中，在（i）中我们仅进行了一些代数运算。通过积分，相同的恒等式适用于边际流向量场和边际得分函数：

\[\begin{aligned}
u_{t}^{target}(x)
&=\int u_{t}^{target}(x | z) \frac{p_{t}(x | z) p_{data }(z)}{p_{t}(x)} d z\\
&=\int\left[\left(\beta_{t}^{2} \frac{\dot{\alpha}_{t}}{\alpha_{t}}-\dot{\beta}_{t} \beta_{t}\right) \nabla \log p_{t}(x | z)+\frac{\dot{\alpha}_{t}}{\alpha_{t}} x\right] \frac{p_{t}(x | z) p_{data }(z)}{p_{t}(x)} d z\\
&\stackrel{(i)}{=}\left(\beta_{t}^{2} \frac{\dot{\alpha}_{t}}{\alpha_{t}}-\dot{\beta}_{t} \beta_{t}\right) \nabla \log p_{t}(x)+\frac{\dot{\alpha}_{t}}{\alpha_{t}} x
\end{aligned}\]

我们可以使用转换公式，通过
\[u_{t}^{\theta }(x)=\left( \beta _{t}^{2}\frac {\dot {\alpha }_{t}}{\alpha _{t}}-\dot {\beta }_{t}\beta _{t}\right) s_{t}^{\theta }(x)+\frac {\dot {\alpha }_{t}}{\alpha _{t}}x. \quad (54)\]
将分数网络\(s_{t}^{\theta}\)和向量场网络\(u_{t}^{\theta}\)进行相互参数化。

同样地，只要 \(\beta_{t}^{2} \dot{\alpha}_{t}-\alpha_{t} \dot{\beta}_{t} \beta_{t} \neq 0\)（对 \(t \in [0,1)\) 始终为真），就可以得出
\[s_{t}^{\theta}(x)=\frac{\alpha_{t} u_{t}^{\theta}(x)-\dot{\alpha}_{t} x}{\beta_{t}^{2} \dot{\alpha}_{t}-\alpha_{t} \dot{\beta}_{t} \beta_{t}} . \quad (55)\]

![](/img/flow-matching/f10.png)
图10：通过两种不同方式获得的分数对比。上图：通过分数匹配独立学习到的分数场\(s_{t}^{\theta}(x)\)的可视化（参见算法4）。下图：如式（55）所示，使用\(u_{t}^{\theta}(x)\)参数化的分数场\(\tilde{s}_{t}^{\theta}(x)\)的可视化。

通过这种参数化方法可以证明，去噪分数匹配损失和条件流匹配损失在相差一个常数的情况下是相同的。我们得出结论：对于高斯概率路径，无需分别训练边缘分数和边缘向量场，因为知道其中一个就足以计算出另一个。特别地，我们可以选择使用流匹配还是分数匹配来进行训练。在图10中，我们直观地比较了通过分数匹配得到的近似分数和使用式（55）得到的参数化分数。如果我们训练了一个分数网络 \(s_{t}^{\theta}\)，那么根据式（52），我们可以使用任意的 \(\sigma_{t} \ge 0\) 从 SDE
\[\begin{aligned}
X_{0} &\sim p_{init},\\
dX_{t} &=\left[ \left( \beta _{t}^{2}\frac {\dot {\alpha }_{t}}{\alpha _{t}}-\dot {\beta }_{t}\beta _{t}+\frac {\sigma _{t}^{2}}{2}\right) s_{t}^{\theta }(X_{t})+\frac {\dot {\alpha }_{t}}{\alpha _{t}}X_{t}\right] dt+\sigma _{t}dW_{t}. \quad (56)
\end{aligned}\]
中进行采样以获取样本\(X_{1} ~ p_{data }\)（直至训练和模拟误差）。这对应于从去噪扩散模型中进行随机采样。

## 扩散模型综述

文献中围绕 “扩散 / 流匹配” 有一整套模型，但都是 “噪声→数据” 的生成逻辑，只是在 时间表示、路径构建、训练目标推导 上用了不同表述 —— 本文档的 “连续时间 + 概率路径 + 福克 - 普朗克方程” 是更通用、数学更简洁的现代框架，其他都是历史或特定场景的变体

### 离散时间 vs 连续时间
早期文献（如 DDPM）：离散时间
做法：把 “噪声→数据” 分成固定步数（t=0,1,2,...,T），构建离散马尔可夫链（每步加一点噪声）。
优点：简单直观，容易理解。
缺点：① 训练前要先定 “步数 T”（比如 1000 步），不灵活；② 损失用 ELBO（证据下界），是 “近似值”（不是我们真正想最小化的损失，只是它的下界）。
现代框架（本文）：连续时间
做法：时间 t 是 [0,1] 的连续值，用 SDE/ODE 描述轨迹（不是固定步数）。
优点：① 数学更 “干净”——Song 等人证明，离散时间本质是连续 SDE 的近似；② 损失是 “精确等式”（比如定理 18/20，不是下界），优化更准确；③ 训练后可通过采样器调整步长，控制模拟误差。
两者最终用的损失函数核心一致，只是 “连续时间是精确版，离散时间是近似版”，现在主流用连续时间（SDE/ODE）

### 正向过程 vs 概率路径
早期文献：正向过程
做法：从 “数据 z” 出发，用 SDE 慢慢加噪（d¯Xₜ = uᵗᶠᵒʳʷ(¯Xₜ) dt + σᵗᶠᵒʳʷd¯Wₜ），直到 t→∞（无限时间）收敛到高斯噪声 N (0,I_d)。
本质：就是一条 “高斯概率路径”，但有两个局限：① 时间约定倒置（t=0 是数据，t→∞是噪声，和本文 “t=0 是噪声，t=1 是数据” 相反）；② 向量场 uᵗᶠᵒʳʷ必须是 “仿射形式”（uᵗᶠᵒʳʷ(x)=aₜx）—— 因为要知道 “加噪后 Xₜ|X₀=z” 的闭式分布（不然没法训练，总不能真模拟到 t→∞）。
本文框架：概率路径
做法：直接定义 “噪声 p_init ↔ 数据 p_data” 的连续插值（t=0→噪声，t=1→数据），不用模拟到无限时间，也不限定路径是高斯。
优点：① 更通用 —— 可设计任意路径（不只是高斯）；② 更高效 —— 训练时不用模拟 SDE，直接从路径采样 x（比如 x=αₜz+βₜε）。
正向过程只能做 “高斯路径 + 无限时间收敛”，概率路径是它的通用版（有限时间 + 任意路径），所以本文优先用概率路径。

### 时间反转 vs 福克-普朗克方程
早期文献：时间反转
做法：先定义 “正向过程”（数据→噪声），再通过 “时间反转” 得到 “反向过程”（噪声→数据）—— 反向过程的 SDE 就是训练目标。
本质：是本文 “福克 - 普朗克方程推导训练目标” 的特例（只能用于正向过程的仿射向量场）。
缺点：不通用，容易得到次优结果（比如不如 “概率流 ODE” 效果好）。
本文框架：福克 - 普朗克方程
做法：直接通过 “概率质量守恒”（连续性方程 / 福克 - 普朗克方程）推导训练目标（边际向量场 / 分数函数），不用依赖正向过程。
优点：通用 —— 不管路径是什么、向量场是什么形式，都能推导，现在主流用这种方式。
所有现代扩散模型（包括 Stable Diffusion）的训练目标，本质都是用福克 - 普朗克方程推导的，只是早期用时间反转的说法。

### 流匹配/ 随机插值 vs 扩散模型
流匹配（FM）：本文框架的 “纯 ODE 版”
核心：只用水 ODE（无随机项 σₜ=0），训练目标是边际向量场，采样是确定性的（只有初始噪声 X₀是随机，之后轨迹唯一）。
创新：证明 “不用正向过程和 SDE，纯流模型也能规模化训练”，比扩散模型简单。
随机插值（SI）：本文框架的 “ODE+SDE 版”
核心：兼顾纯流（ODE）和带噪声的 SDE（通过朗之万动力学扩展，对应定理 13），是更统一的框架。
扩散模型（早期）：本文框架的 “高斯特例版”
核心：只能用 “高斯初始分布 p_init=N (0,I_d)+ 高斯概率路径”，而流匹配 / 随机插值可以用 “任意 p_init→任意 p_data + 任意路径”，更通用。
本文的框架就是整合了这三者 —— 流匹配是基础（ODE），扩散模型是加噪声的特例（SDE），随机插值是两者的统一。

## Summary
流匹配包括通过最小化条件流匹配损失
\[\begin{array} {r}{\nabla _{FM}(\theta )=\mathbb {E}_{z\sim p_{data},t\sim Unif, x\sim p_{t}(\cdot | z)}\left[ \| u_{t}^{\theta }(x)-u_{t}^{target}(x | z)\| ^{2}\right] (conditional flow matching loss) (60)}\end{array}\]
来训练神经网络\(u_{t}^{\theta}\)，其中\(u_{t}^{target }(x | z)\)是条件向量场（参见算法5）。训练后，通过模拟相应的常微分方程来生成样本（参见算法1）。为了将其扩展到扩散模型，我们可以使用分数网络\(s_{t}^{\theta}\)，并通过条件分数匹配
\[\mathcal{L}_{CSM}(\theta)=\mathbb{E}_{z \sim p_{data }, t \sim Unif, x \sim p_{t}(\cdot | z)}\left[\left\| s_{t}^{\theta}(x)-\nabla log p_{t}(x | z)\right\| ^{2}\right] \quad (denoising score matching loss) (61)\]
对其进行训练。
对于每个扩散系数\(\sigma_{t} ≥0\)，模拟SDE（例如通过算法2）
\[X_{0} {\sim }p_{init}, d X_{t}=\left[ u_{t}^{\theta }(X_{t})+\frac {\sigma _{t}^{2}}{2}s_{t}^{\theta }(X_{t})\right] d t+\sigma _{t} d W_{t} (62)\]
将生成来自\(p_{data }\)的近似样本。可以凭经验找到最优的\(\sigma_{t} ≥0\)。
高斯概率路径。对于高斯概率路径\(p_{t}(x | z)=N(x ; \alpha_{t} z, \beta_{t}^{2} I_{d})\)这一特殊情况，条件得分匹配也被称为去噪得分匹配。该损失和条件流匹配损失如下：

\[\mathcal {L}_{CFM}(\theta )=\mathbb {E}_{t\sim Unif,z\sim p_{data},\epsilon \sim \mathcal {N}(0,I_{d})}[\| u_{t}^{\theta }(\alpha _{t}z+\beta _{t}\epsilon )-(\dot {\alpha }_{t}z+\beta _{t}\epsilon )\| ^{2}]\]



\[\mathcal{L}_{CSM}(\theta)=\mathbb{E}_{t \sim Unif, z \sim p_{data }, \epsilon \sim \mathcal{N}\left(0, I_{d}\right)}\left[\left\| s_{t}^{\theta}\left(\alpha_{t} z+\beta_{t} \epsilon\right)+\frac{\epsilon}{\beta_{t}}\right\| ^{2}\right]\]
在这种情况下，无需分别训练\(s_{t}^{\theta}\)和\(u_{t}^{\theta}\)，因为我们可以在训练后通过以下公式对它们进行转换：

\[u_{t}^{\theta }(x)=\left( \beta _{t}^{2}\frac {\dot {\alpha }_{t}}{\alpha _{t}}-\dot {\beta }_{t}\beta _{t}\right) s_{t}^{\theta }(x)+\frac {\dot {\alpha }_{t}}{\alpha _{t}}x\]
同样，在这里，训练后我们可以通过算法2模拟式（62）中的SDE，以获得样本\(X_{1}\)。
去噪扩散模型。去噪扩散模型是具有高斯概率路径的扩散模型。因此，它们只需学习\(u_{t}^{\theta}\)或\(s_{t}^{\theta}\)即可，因为它们可以相互转换。
虽然流匹配仅允许通过常微分方程（ODE）进行确定性的模拟过程，但它们允许进行确定性（概率流常微分方程）或随机性（随机微分方程采样）的模拟。然而，与流匹配或随机插值不同，流匹配或随机插值允许通过任意概率路径将任意分布\(p_{init }\)转换为任意分布\(p_{data }\)，去噪扩散模型仅适用于高斯初始分布\(p_{init }=N(0, I_{d})\)和高斯概率路径。
文献中流行的扩散模型的替代公式如下：
离散时间：人们经常使用通过离散时间马尔可夫链对随机微分方程（SDEs）进行的近似。
1.2. 倒置时间约定：普遍采用一种倒置时间约定，其中\(t=0\)对应\(p_{data }\)（与此处的情况不同，此处\(t=0\)对应\(p_{init }\)）。
3. 正向过程：正向过程（或加噪过程）是构建（高斯）概率路径的方法。
4. 4. 通过时间反转的训练目标：训练目标也可以通过随机微分方程（SDEs）的时间反转来构建。这是本文所提出的构建方法的一个具体实例（采用了倒置的时间约定）。
