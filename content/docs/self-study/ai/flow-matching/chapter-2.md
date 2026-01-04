# Constructing a Training Target

在上一节中，我们构建了**流模型**和**扩散模型**，通过模拟**SDE**和**ODE**我们得到了轨迹\((X_{t})_{0 \leq t \leq 1}\)：

\[X_{0} \sim p_{init}, \quad dX_{t}=u_{t}^{\theta}\left(X_{t}\right) dt \quad \text{（Flow model）} \quad (10)\]

\[X_{0} \sim p_{init}, \quad dX_{t}=u_{t}^{\theta}\left(X_{t}\right) dt+\sigma_{t} dW_{t} \quad \text{（Diffusion model）} \quad (11)\]

其中\(u_{t}^{\theta}\)是一个**神经网络**，\(\sigma_{t}\)是一个**固定的扩散系数**。

**问题**：如果我们只是随机初始化神经网络\(u_{t}^{\theta}\)的参数\(\theta\)，那么对常微分方程/随机微分方程的模拟只会产生无意义的结果。与机器学习中的常规操作一样，我们需要**训练这个神经网络**。

**训练方法**：我们通过最小化一个损失函数\(\mathcal{L}(\theta)\)来实现这一点，例如**均方误差**：

\[\mathcal{L}(\theta)=\| u_{t}^{\theta}(x)-\underbrace{u_{t}^{target}(x)}_{\text{训练目标}} \|^{2}\]

其中\(u_{t}^{target}(x)\)是我们想要逼近的**训练目标**。

**本章目标**：为了推导训练算法，我们分两步进行：
- **本章**：找到训练目标\(u_{t}^{target}\)的方程
- **下一章**：描述一种逼近训练目标\(u_{t}^{target}\)的训练算法

自然地，和神经网络\(u_{t}^{\theta}\)一样，训练目标本身也应该是一个**向量场**\(u_{t}^{target}: \mathbb{R}^{d} \times[0,1] \to \mathbb{R}^{d}\)。此外，\(u_{t}^{target}\)应该实现我们期望\(u_{t}^{\theta}\)实现的功能：**将噪声转化为数据**。

因此，本章的目标是推导训练目标\(u_{t}^{target}\)的公式，使得相应的常微分方程/随机微分方程能将\(p_{init}\)转化为\(p_{data}\)。在此过程中，我们将遇到来自物理学和随机微积分的两个基本结果：**连续性方程**和**福克-普朗克方程**。和之前一样，我们将首先阐述常微分方程的核心思想，然后再将其推广到随机微分方程。

<!--more-->

## 条件概率路径和边缘概率路径

构建训练目标的第一步，是给"噪声→数据"的转换铺一条"**渐进过渡的路线**"—— 这就是**概率路径**。

**概率路径**本质是一系列分布（从\(t=0\)到\(t=1\)），作用是让初始噪声分布\(p_{init}\)"一步步插值成"数据分布\(p_{data}\)。

### 条件概率路径

针对单个数据点\(z\)（比如一张猫图、一个分子结构），定义一组分布\(p_t(x|z)\)，满足两个关键条件：

\[p_{0}(\cdot | z)=p_{init}, \quad p_{1}(\cdot | z)=\delta_{z} \quad \text{for all } z \in \mathbb{R}^{d} \quad (12)\]

- **\(t=0\)时**：\(p_0(x|z) = p_{init}\)（起点是纯噪声，和数据点\(z\)无关）
- **\(t=1\)时**：\(p_1(x|z) = \delta_z\)（终点是"**狄拉克 δ 分布**"）

**狄拉克 δ 分布**\(\delta_z\)：最简单的确定性分布 —— 从它里面采样，永远只返回\(z\)（比如从\(\delta_{\text{猫图}}\)采样，只能得到这张猫图）。

![](/img/flow-matching/f4.png)

**图4**：通过高斯条件概率路径从噪声到数据的渐进插值，用于一组图像。


### 边缘概率路径

条件路径是"单个数据点的桥"，**边缘路径**是"所有数据点的桥的总和"—— 把数据分布\(p_{data}\)里的所有\(z\)的条件路径整合起来，得到整体的过渡。

在概率论中，"**边缘化**"是指对联合分布中的某个变量求和/积分，得到另一个变量的分布。这里：

- **联合分布**：\(p_t(x,z)=p_t(x|z)p_{data}(z)\)（\(x\)和\(z\)的联合分布）
- **边缘分布**：\(p_t(x)=\int p_t(x,z)dz=\int p_t(x|z)p_{data}(z)dz\)（只关心\(x\)，把\(z\)"积分掉"）

**类比理解**：
- **条件路径**：从A城到B城的路线（A=噪声，B=特定的猫图）
- **边缘路径**：从A城出发，随机选择一个城市（所有城市都在数据集中），然后走那条路线

**采样方式**（式 13）：先从\(p_{data}\)采一个数据点\(z\)，再从\(p_t(x|z)\)采\(x\)，最终\(x\)服从的分布就是\(p_t(x)\)：

\[z \sim p_{data}, \quad x \sim p_{t}(\cdot | z) \Rightarrow x \sim p_{t} \quad \text{（从边缘路径采样）} \quad (13)\]

**密度公式**（式 14）：

\[p_{t}(x)=\int p_{t}(x | z) p_{data}(z) dz \quad \text{（边缘路径的密度）} \quad (14)\]

这表示\(p_t(x) = \int p_t(x|z)p_{data}(z)dz\)（积分是"求和"的意思，即所有\(z\)的条件路径加权平均）。

**直观理解**：

对每个可能的\(z\)，计算"从\(z\)的条件路径得到\(x\)的概率"乘以"\(z\)在数据集中出现的概率"，然后把所有这些值加起来（积分就是求和）。

假设在时刻\(t\)，我们看到一个样本\(x\)，它可能来自：
- 数据点\(z_1\)的条件路径（概率是\(p_t(x|z_1) \times p_{data}(z_1)\)）
- 数据点\(z_2\)的条件路径（概率是\(p_t(x|z_2) \times p_{data}(z_2)\)）
- ...（对所有数据点求和）

最终的\(p_t(x)\)就是所有这些可能性的总和。

**重要性质**：我们知道如何从\(p_{t}\)中采样，但由于积分难以处理，我们不知道密度值\(p_{t}(x)\)。由于式（12）中对\(p_{t}(\cdot | z)\)的条件限制，边缘概率路径\(p_{t}\)在\(p_{init}\)和\(p_{data}\)之间进行插值：

\[p_{0}=p_{init} \quad \text{and} \quad p_{1}=p_{data} \quad \text{（噪声-数据插值）} \quad (15)\]

![](/img/flow-matching/f5.png)

**图5**：条件概率路径（上）和边缘概率路径（下）的图示。在这里，我们绘制了一个高斯概率路径，其参数为\(\alpha_{t}=t\)、\(\beta_{t}=1-t\)。对于单个数据点\(z\)，条件概率路径插值了高斯分布\(p_{init}=\mathcal{N}(0, I_{d})\)和\(p_{data}=\delta_{z}\)。边缘概率路径插值了高斯分布和数据分布\(p_{data}\)（这里，\(p_{data}\)是\(d=2\)维的一个玩具分布，由棋盘图案表示）。

> **实际例子（图像生成）**
>
> 假设数据集有3张图片：猫、狗、鸟
>
> **条件路径**：
> - \(p_t(x|\text{猫})\)：噪声 → 猫图
> - \(p_t(x|\text{狗})\)：噪声 → 狗图
> - \(p_t(x|\text{鸟})\)：噪声 → 鸟图
>
> **边缘路径**\(p_t(x)\)：
> - 在时刻\(t\)，随机选择一张图片（按它们在数据集中的频率），然后沿着那条条件路径采样
> - 这样得到的样本，可能像猫、像狗、像鸟，或者介于它们之间
> - 整体来看，这个分布会从噪声逐渐过渡到由猫、狗、鸟组成的数据分布

#### 高斯概率路径

一种特别受欢迎的概率路径是**高斯概率路径**。这是**去噪扩散模型**所使用的概率路径。

**噪声调度器**：令\(\alpha_{t}\)、\(\beta_{t}\)为两个具有以下性质的连续可微单调函数：
- \(\alpha_{0}=\beta_{1}=0\)
- \(\alpha_{1}=\beta_{0}=1\)

**直观理解**：
- \(\alpha_0=0\)、\(\alpha_1=1\)：\(t\)越大，数据\(z\)的权重越大
- \(\beta_0=1\)、\(\beta_1=0\)：\(t\)越大，噪声的权重越小

然后我们定义**条件概率路径**：

\[p_{t}(\cdot | z)=\mathcal{N}\left(\alpha_{t} z, \beta_{t}^{2} I_{d}\right) \quad \text{（高斯条件路径）} \quad (16)\]

条件概率路径直接定义为**高斯分布**，\(t\)时刻的分布，均值是"\(\alpha_t\)乘以数据点\(z\)"，方差是"\(\beta_t^2\)乘以单位矩阵"。

**验证边界条件**：
- **\(t=0\)**：\(\alpha_0=0\)、\(\beta_0=1\)，所以\(p_0(x|z) = \mathcal{N}(0, I_d) = p_{init}\)（纯噪声，符合要求）
- **\(t=1\)**：\(\alpha_1=1\)、\(\beta_1=0\)，方差为0的高斯分布就是\(\delta_z\)（纯数据，符合要求）

根据我们对\(\alpha_{t}\)和\(\beta_{t}\)施加的条件，它满足：

\[p_{0}(\cdot | z)=\mathcal{N}\left(\alpha_{0} z, \beta_{0}^{2} I_{d}\right)=\mathcal{N}\left(0, I_{d}\right), \quad p_{1}(\cdot | z)=\mathcal{N}\left(\alpha_{1} z, \beta_{1}^{2} I_{d}\right)=\delta_{z}\]

这里我们用到了一个事实，即方差为零且均值为\(z\)的正态分布就是\(\delta_{z}\)。因此，对于\(p_{init}=\mathcal{N}(0, I_{d})\)来说，这种\(p_{t}(x | z)\)的选择满足式（12），因此是一条有效的条件插值路径。

**从边缘高斯路径\(p_t(x)\)采样**：

\[z \sim p_{data}, \quad \epsilon \sim p_{init}=\mathcal{N}(0, I_{d}) \Rightarrow x=\alpha_{t} z+\beta_{t} \epsilon \sim p_{t} \quad \text{（从边缘高斯路径采样）}\]

**采样步骤**：先从\(p_{data}\)采\(z\)（数据点），从\(p_{init}\)采\(\epsilon\)（噪声），两者加权求和就是\(t\)时刻的样本。

**直观效果**：\(t\)越小，\(\beta_t\)越大（噪声权重高），\(x\)越模糊；\(t\)越大，\(\alpha_t\)越大（数据权重高），\(x\)越清晰（图5底部就是2维玩具数据的过渡：\(t=0\)是纯高斯噪声，\(t=1\)是棋盘状的数据分布）。

## 条件向量场和边缘向量场

**核心思路**：流模型的本质是"让 ODE 轨迹沿概率路径走（从噪声→数据）"，所以训练目标是找到一个**目标向量场**\(u_t^{target}\)，让 ODE 轨迹\(X_t\)刚好服从边际概率路径\(p_t(x)\)（最终\(X_1 \sim p_{data}\)）。

但直接求\(u_t^{target}(x)\)很难，于是换个思路：先求"单个数据点\(z\)的专属向量场"（**条件向量场**\(u_t^{target}(x|z)\)），再通过"加权平均"得到全局的边际向量场 —— 这就是"**边缘化技巧**"的核心。

**Theorem 10 (Marginalization trick)**

对于每个数据点\(z \in \mathbb{R}^{d}\)，令\(u_{t}^{target}(\cdot | z)\)表示一个**条件向量场**，其定义为相应的常微分方程（ODE）产生条件概率路径\(p_{t}(\cdot | z)\)，即：

\[X_{0} \sim p_{init}, \quad \frac{d}{dt}X_{t}=u_{t}^{target}(X_{t} | z) \Rightarrow X_{t} \sim p_{t}(\cdot | z) \quad (0 \leq t \leq 1) \quad (18)\]

那么，由

\[u_{t}^{target}(x)=\int u_{t}^{target}(x | z) \frac{p_{t}(x | z) p_{data}(z)}{p_{t}(x)} dz \quad (19)\]

定义的**边缘向量场**\(u_{t}^{target}(x)\)遵循边际概率路径，即

\[X_{0} \sim p_{init}, \quad \frac{d}{dt} X_{t}=u_{t}^{target}\left(X_{t}\right) \Rightarrow X_{t} \sim p_{t} \quad (0 \leq t \leq 1) \quad (20)\]

特别是，对于这个常微分方程（ODE）来说\(X_{1} \sim p_{data}\)，因此我们可以说"\(u_{t}^{target}\)将噪声\(p_{init}\)转换为数据\(p_{data}\)"。

**边缘化技巧的三步走**：

**第一步：定义"专属向量场"（条件向量场\(u_t^{target}(x|z)\)）**

针对单个数据点\(z\)（比如一张猫图），定义一个向量场\(u_t^{target}(x|z)\)，满足：若从\(X_0 \sim p_{init}\)（噪声）出发，沿这个向量场走 ODE（\(\frac{d}{dt}X_t = u_t^{target}(X_t|z)\)），则轨迹\(X_t\)刚好服从条件概率路径\(p_t(\cdot|z)\)（即"噪声→慢慢变成\(z\)"的过渡，对应图6上排：轨迹最终贴合单个\(z\)）。

**关键**：这个"专属向量场"能手动解析推导（不用训练，靠代数运算），后面的高斯示例会验证。

**第二步：加权整合得到"通用向量场"（边际向量场\(u_t^{target}(x)\)）**

把所有数据点\(z\)的"专属向量场"按"贡献度"加权求和，就得到全局的边际向量场：

\[u_t^{target}(x) = \int u_t^{target}(x|z) \cdot \frac{p_t(x|z)p_{data}(z)}{p_t(x)} dz\]

**权重解读**：\(\frac{p_t(x|z)p_{data}(z)}{p_t(x)}\)是"在当前位置\(x\)、时间\(t\)下，数据点\(z\)对全局分布的贡献占比"—— 简单说，哪个\(z\)和\(x\)更相关（条件概率\(p_t(x|z)\)大）、在数据集中更常见（\(p_{data}(z)\)大），它的"专属向量场"权重就越高。

**第三步：最终效果**

这个边际向量场对应的 ODE 轨迹，会刚好服从边际概率路径\(p_t(x)\)（即"噪声→慢慢变成整体数据分布"的过渡，对应图6下排：轨迹最终贴合全局数据分布），最终\(X_1 \sim p_{data}\)—— 相当于"把所有单个\(z\)的专属向量场，整合成了能生成任意数据的通用向量场"。

![](/img/flow-matching/f6.png)

**图6**：定理10的图示。使用常微分方程（ODEs）模拟概率路径。蓝色背景为数据分布\(p_{data}\)。红色背景为高斯分布\(p_{init}\)。**上排**：条件概率路径。左图：来自条件路径\(p_{t}(\cdot | z)\)的真实样本。中图：不同时间的常微分方程样本。右图：通过用式（21）中的\(u_{t}^{target}(x | z)\)模拟常微分方程得到的轨迹。**下排**：模拟边缘概率路径。左图：来自\(p_{t}\)的真实样本。中图：不同时间的常微分方程样本。右图：通过用边缘向量场\(u_{t}^{flow}(x)\)模拟常微分方程得到的轨迹。可以看出，条件向量场遵循条件概率路径，边缘向量场遵循边缘概率路径。

### Example (Target ODE for Gaussian probability paths)

之前讲过"**高斯概率路径**"是扩散模型的标配（\(p_t(x|z) = \mathcal{N}(\alpha_t z, \beta_t^2 I_d)\)），这里直接推导它的条件向量场，证明"专属向量场能解析求"。

**目标**：证明条件高斯向量场

\[u_t^{target}(x|z) = \left(\dot{\alpha}_t - \frac{\dot{\beta}_t}{\beta_t}\alpha_t\right) z + \frac{\dot{\beta}_t}{\beta_t} x \quad (21)\]

满足定理10的条件，即如果\(X_0 \sim p_{init}=\mathcal{N}(0, I_d)\)，则其ODE轨迹\(X_t\)满足\(X_t \sim p_t(\cdot|z) = \mathcal{N}(\alpha_t z, \beta_t^2 I_d)\)。

其中\(\dot{\alpha}_t = \frac{\partial}{\partial t}\alpha_t\)和\(\dot{\beta}_t = \frac{\partial}{\partial t}\beta_t\)分别是\(\alpha_t\)和\(\beta_t\)对时间的导数。

**证明**：

**步骤1：构造条件流\(\psi_t^{target}(x|z)\)**

定义条件流：

\[\psi_t^{target}(x|z) = \alpha_t z + \beta_t x \quad (22)\]

如果\(X_t\)是流\(\psi_t^{target}(\cdot|z)\)的ODE轨迹，且\(X_0 \sim p_{init}=\mathcal{N}(0, I_d)\)，那么根据定义：

\[X_t = \psi_t^{target}(X_0|z) = \alpha_t z + \beta_t X_0 \sim \mathcal{N}(\alpha_t z, \beta_t^2 I_d) = p_t(\cdot|z)\]

因此，轨迹的分布与条件概率路径一致（即满足式（18））。

**步骤2：从流中提取向量场**

根据流的定义（式（2b）），对于所有\(x, z \in \mathbb{R}^d\)：

\[\frac{d}{dt}\psi_t^{target}(x|z) = u_t^{target}(\psi_t^{target}(x|z)|z)\]

**第一步**：对\(\psi_t^{target}(x|z)\)求时间导数：

\[\frac{d}{dt}\psi_t^{target}(x|z) = \frac{d}{dt}(\alpha_t z + \beta_t x) = \dot{\alpha}_t z + \dot{\beta}_t x\]

**第二步**：变量替换（将流的位置换回\(x\)）：

因为\(\psi_t^{target}(x|z) = \alpha_t z + \beta_t x\)，所以\(x = \frac{\psi_t^{target}(x|z) - \alpha_t z}{\beta_t}\)。

设\(y = \psi_t^{target}(x|z) = \alpha_t z + \beta_t x\)，则：

\[\dot{\alpha}_t z + \dot{\beta}_t x = \dot{\alpha}_t z + \dot{\beta}_t \cdot \frac{y - \alpha_t z}{\beta_t} = \dot{\alpha}_t z + \frac{\dot{\beta}_t}{\beta_t}(y - \alpha_t z)\]

**第三步**：整理得到向量场：

\[u_t^{target}(y|z) = \dot{\alpha}_t z + \frac{\dot{\beta}_t}{\beta_t}(y - \alpha_t z) = \left(\dot{\alpha}_t - \frac{\dot{\beta}_t}{\beta_t}\alpha_t\right) z + \frac{\dot{\beta}_t}{\beta_t} y\]

将\(y\)替换回\(x\)，得到：

\[u_t^{target}(x|z) = \left(\dot{\alpha}_t - \frac{\dot{\beta}_t}{\beta_t}\alpha_t\right) z + \frac{\dot{\beta}_t}{\beta_t} x \quad (21)\]

这就是式（21）中定义的条件高斯向量场，证明完成。

> 教案这里的下一步是通过连续性方程（定理 12）去证明上面的定理 10，即证明 “边际向量场真的能让轨迹沿边际概率路径走”
> 
> 这里我数学不好，直接跳过，有缘再见

## 条件和边际得分函数

我们刚刚成功构建了一个流模型的训练目标。现在我们将这一推理扩展到随机微分方程（SDEs）。为此，我们将\(p_{t}\)的边际得分函数定义为\(\nabla log p_{t}(x)\)。

### Theorem 13 (SDE extension trick)

如前所述，已知流模型的条件向量场\(u_t^{target}(x|z)\)（单个数据点\(z\)的专属向量场）和边际向量场\(u_t^{target}(x)\)（全局通用向量场），只要引入**扩散系数**\(\sigma_t \geq 0\)（控制噪声强度），就能构建一个遵循相同概率路径的随机微分方程（SDE）：

\[X_{0} \sim p_{init}, \quad dX_{t}=\left[u_{t}^{target}(X_{t})+\frac{\sigma_{t}^{2}}{2}\nabla \log p_{t}(X_{t})\right]dt+\sigma_{t}dW_{t} \Rightarrow X_{t} \sim p_{t} \quad (0 \leq t \leq 1) \quad (25)\]

这个 SDE 的轨迹\(X_t\)，会和原 ODE 的轨迹服从完全相同的概率路径\(p_t(x)\)（即\(X_t \sim p_t\)，\(0 \leq t \leq 1\)）。**最终目标**：当\(t=1\)时，\(X_1 \sim p_{data}\)（和 ODE 一样能"噪声变数据"）。

**SDE 的三个组成部分**：

**1. 原有项：\(u_t^{target}(X_t) dt\)**

这是流模型中已经验证有效的"**核心导航项**"—— 它能保证轨迹"平均意义上"沿着概率路径\(p_t(x)\)走（比如从噪声向数据方向移动），是 SDE 的基础骨架。

**2. 新增随机项：\(\sigma_t dW_t\)**

- \(dW_t\)：布朗运动的瞬时变化（核心随机源，比如"随机绕弯"）
- \(\sigma_t\)：扩散系数（控制扰动强度，\(\sigma_t\)越大，随机性越强，样本多样性越高）
- **作用**：让轨迹从"确定性单一路径"变成"随机性多条路径"—— 但如果只加这个项，轨迹会因为噪声偏离概率路径，所以需要第三个项来"校正"

**3. 校正项：\(\frac{\sigma_t^2}{2} \nabla \log p_t(X_t) dt\)（拉回正途的"引力项"）**

这是定理的灵魂，核心作用是抵消随机项的偏离，让轨迹整体仍贴合\(p_t(x)\)：

- \(\nabla \log p_t(x)\)：**分数函数**（边际得分函数），本质是"概率密度的梯度方向"—— 指向概率密度更高的区域（比如数据分布的核心区域，像"引力场"）
- 系数\(\frac{\sigma_t^2}{2}\)：和随机项强度匹配（\(\sigma_t\)越大，校正力越强，避免被噪声带偏）
- **直观效果**：随机项让轨迹"乱走"，校正项像"导航罗盘"，把轨迹拉回概率路径的方向 —— 最终所有随机轨迹的"统计平均"，依然和 ODE 的确定性轨迹一致（都服从\(p_t(x)\)）

> 如果我们把 “边际向量场\(u_t^{target}(x)\)、边际概率\(p_t(x)\)” 换成 “条件向量场\(u_t^{target}(x|z)\)、条件概率\(p_t(x|z)\)”，同样的恒等式仍然成立 —— 即能构造出贴合单个数据点 z 的条件 SDE（轨迹最终收敛到\(\delta_z\)）


![](/img/flow-matching/f7.png)

**图7**：定理13的说明。使用随机微分方程模拟概率路径。这重复了图6中的图表，并使用公式（25）进行随机微分方程采样。蓝色背景为数据分布\(p_{data}\)。红色背景为高斯分布\(p_{init}\)。**上行**：条件路径。**下行**：边际概率路径。可以看到，随机微分方程将样本从\(p_{init}\)传输到（条件路径的）\(\delta_{z}\)的样本中，以及（边际路径的）\(p_{data}\)的样本中。

**边际得分函数的边缘化**

定理13中的公式很有用，因为和之前类似，我们可以通过**条件得分函数**\(\nabla \log p_{t}(x | z)\)来表示边际得分函数：

\[\nabla \log p_{t}(x)=\frac{\nabla p_{t}(x)}{p_{t}(x)}=\frac{\nabla \int p_{t}(x | z) p_{data}(z) dz}{p_{t}(x)}=\frac{\int \nabla p_{t}(x | z) p_{data}(z) dz}{p_{t}(x)}=\int \nabla \log p_{t}(x | z) \frac{p_{t}(x | z) p_{data}(z)}{p_{t}(x)} dz \quad (27)\]

而如下例所示，条件得分函数\(\nabla \log p_{t}(x | z)\)通常是我们可以通过解析方法得到的。

**高斯路径的条件得分函数**

对于高斯路径\(p_{t}(x | z)=\mathcal{N}(x ; \alpha_{t} z, \beta_{t}^{2} I_{d})\)，我们可以使用高斯概率密度的形式得到：

\[\nabla \log p_{t}(x | z)=\nabla \log \mathcal{N}\left(x ; \alpha_{t} z, \beta_{t}^{2} I_{d}\right)=-\frac{x-\alpha_{t} z}{\beta_{t}^{2}} \quad (28)\]

**注意**：该分数是\(x\)的线性函数。这是高斯分布的一个独特特征。

> 下面则是更进一步的证明。通过福克-普朗克方程证明定理13，该方程将连续性方程从常微分方程扩展到了随机微分方程。
> 然后这玩意又会有一个著名的特例，要引入郎之万动力学
> 我觉得没有必要研究太多数学的内容，简简单单过一遍

### 福克-普朗克方程证明

#### 预备知识：算子

##### \(\nabla\)（梯度算子）

**含义**：对空间变量 \(x\) 的梯度，表示"函数在各个方向上的变化率"。

**数学定义**（\(d\) 维空间）：

\[\nabla f(x) = \left(\frac{\partial f}{\partial x_1}, \frac{\partial f}{\partial x_2}, \ldots, \frac{\partial f}{\partial x_d}\right)^T\]

**例子**：
- 如果 \(f(x_1, x_2) = x_1^2 + x_2^2\)（二维），则：
  \[\nabla f(x) = (2x_1, 2x_2)^T\]
- 这是一个向量，指向函数值增长最快的方向

**直观理解**：
- 梯度指向"上坡"方向（函数值增加最快的方向）
- 梯度的大小表示"坡度"的陡峭程度
- 在概率分布中，\(\nabla \log p_t(x)\) 指向概率密度更高的区域

##### \(\text{div}\)（散度算子）

**含义**：向量场的散度，表示"向量场在某点的'源'或'汇'的强度"。

**数学定义**（对向量场 \(v(x) = (v_1(x), v_2(x), \ldots, v_d(x))\)）：

\[\text{div}(v)(x) = \sum_{i=1}^{d} \frac{\partial v_i}{\partial x_i} = \frac{\partial v_1}{\partial x_1} + \frac{\partial v_2}{\partial x_2} + \cdots + \frac{\partial v_d}{\partial x_d}\]

**直观理解**（流体力学类比）：
- **正散度**：向量场从该点"发散"（像水从水龙头流出）
- **负散度**：向量场向该点"汇聚"（像水流入下水道）
- **零散度**：向量场在该点"无源无汇"（像不可压缩流体）

**在概率中的含义**：
- \(\text{div}(p_t u_t)(x)\) 表示"概率质量在位置 \(x\) 的流动强度"
- 如果 \(\text{div}(p_t u_t)(x) > 0\)：概率质量从 \(x\) 流出（该位置概率减少）
- 如果 \(\text{div}(p_t u_t)(x) < 0\)：概率质量向 \(x\) 流入（该位置概率增加）

**例子**（二维）：
- 如果 \(v(x_1, x_2) = (x_1, x_2)\)，则：
  \[\text{div}(v)(x) = \frac{\partial x_1}{\partial x_1} + \frac{\partial x_2}{\partial x_2} = 1 + 1 = 2\]
- 这表示向量场从原点向外发散

##### \(\Delta\)（拉普拉斯算子）

**含义**：函数的拉普拉斯算子，表示"函数的'平均曲率'或'扩散强度'"。

**数学定义**：

\[\Delta f(x) = \sum_{i=1}^{d} \frac{\partial^2 f}{\partial x_i^2} = \frac{\partial^2 f}{\partial x_1^2} + \frac{\partial^2 f}{\partial x_2^2} + \cdots + \frac{\partial^2 f}{\partial x_d^2}\]

**等价关系**：

\[\Delta f = \text{div}(\nabla f)\]

**直观理解**：
- 拉普拉斯算子衡量函数在某个点的"平均曲率"
- **正拉普拉斯**：函数在该点"凸起"（像山峰）
- **负拉普拉斯**：函数在该点"凹陷"（像山谷）
- **零拉普拉斯**：函数在该点"平坦"

**在扩散中的含义**：
- \(\Delta p_t(x)\) 表示"概率密度在位置 \(x\) 的扩散强度"
- 扩散会让概率质量从高密度区域流向低密度区域（像热量扩散）

**例子**（二维）：
- 如果 \(f(x_1, x_2) = x_1^2 + x_2^2\)，则：
  \[\Delta f = \frac{\partial^2 (x_1^2 + x_2^2)}{\partial x_1^2} + \frac{\partial^2 (x_1^2 + x_2^2)}{\partial x_2^2} = 2 + 2 = 4\]
- 这表示函数在所有方向都是凸的


#### Theorem 15 (Fokker-Planck Equation)

我们想要一个 SDE，使得它的轨迹 \(X_t\) 服从概率路径 \(p_t\)：

\[X_{0} \sim p_{init}, \quad dX_{t}=u_{t}\left(X_{t}\right) dt+\sigma_{t} dW_{t}\]

当且仅当**福克-普朗克方程**成立时，对于所有 \(0 \leq t \leq 1\)，\(X_{t}\) 具有分布 \(p_{t}\)：

\[\partial_{t} p_{t}(x)=-\text{div}\left(p_{t} u_{t}\right)(x)+\frac{\sigma_{t}^{2}}{2} \Delta p_{t}(x) \quad \text{for all } x \in \mathbb{R}^{d}, 0 \leq t \leq 1 \quad (30)\]

**方程含义**：
- **左边**：\(p_t(x)\) 随时间的变化率
- **右边第一项**：\(-\text{div}(p_t u_t)(x)\)
    - 向量场 \(u_t\) 驱动的概率流动
    - 负号表示：如果向量场在某点发散（\(\text{div} > 0\)），该点概率减少
    - 这是 ODE 的连续性方程部分

- **右边第二项**：\(\frac{\sigma_t^2}{2} \Delta p_t(x)\)
    - 随机扩散项
    - \(\sigma_t^2\)：扩散强度（噪声方差）
    - \(\Delta p_t(x)\)：扩散效应（概率从高密度区域扩散到低密度区域）

#### 定理13的证明

上面的就是福克-普朗克方程，接下来要做的就是反向推导。

**目标**：构造 SDE，使得 \(X_t \sim p_t\)

**已知**：\(p_t\) 满足连续性方程（ODE 情况）：

\[\partial_t p_t = -\text{div}(p_t u_t^{target})\]

**策略**：在 ODE 基础上加随机项，并用校正项抵消偏离

**推导步骤**：

**步骤 (i)**：从连续性方程开始

\[\partial_t p_t = -\text{div}(p_t u_t^{target})\]

**步骤 (ii)**：添加并减去扩散项（**关键技巧**）

\[= -\text{div}(p_t u_t^{target}) - \frac{\sigma_t^2}{2} \Delta p_t + \frac{\sigma_t^2}{2} \Delta p_t\]

**步骤 (iii)**：利用 \(\Delta p_t = \text{div}(\nabla p_t)\)

\[= -\text{div}(p_t u_t^{target}) - \text{div}\left(\frac{\sigma_t^2}{2} \nabla p_t\right) + \frac{\sigma_t^2}{2} \Delta p_t\]

**步骤 (iv)**：利用 \(\nabla \log p_t = \frac{\nabla p_t}{p_t}\)，即 \(\nabla p_t = p_t \nabla \log p_t\)

\[= -\text{div}(p_t u_t^{target}) - \text{div}\left(p_t \cdot \frac{\sigma_t^2}{2} \nabla \log p_t\right) + \frac{\sigma_t^2}{2} \Delta p_t\]

**步骤 (v)**：合并散度项

\[= -\text{div}\left(p_t \left[u_t^{target} + \frac{\sigma_t^2}{2} \nabla \log p_t\right]\right) + \frac{\sigma_t^2}{2} \Delta p_t\]

**结论**：这个形式正好是 **Fokker-Planck 方程**！对应的 SDE 是：

\[dX_t = \left[u_t^{target}(X_t) + \frac{\sigma_t^2}{2} \nabla \log p_t(X_t)\right]dt + \sigma_t dW_t\]

上述推导表明，式（25）中定义的 SDE 满足 \(p_{t}\) 的福克-普朗克方程。根据定理15，这意味着对于 \(0 \leq t \leq 1\)，有 \(X_{t} \sim p_{t}\)，正如所期望的那样。

### 重要特例：朗之万动力学

当概率路径是"**静态**"的（\(p_t = p\)，比如固定的目标分布），此时\(u_t^{target}=0\)，SDE 简化为：

\[dX_t = \frac{\sigma_t^2}{2} \nabla \log p(X_t) dt + \sigma_t dW_t\]

**作用**：从任意初始分布\(p'\)出发，轨迹会逐渐收敛到静态分布\(p\)。这就是著名的**朗之万动力学**（Langevin dynamics），常用于从复杂分布中采样。
与许多马尔可夫链一样，在相当一般的条件下，这些动态会收敛到平稳分布p（见3.3节）。也就是说，如果我们改为采用\(X_{0} ~ p' ≠p\)，那么\(X_{t} ~ p_{t}'\)，在温和条件下\(p_{t} \to p\)。这一事实使得朗之万动力学极为有用，因此它成为了例如分子动力学模拟以及贝叶斯统计和自然科学领域中许多其他马尔可夫链蒙特卡洛（MCMC）方法的基础。

## Summary

### 一、流模型的训练目标：边际向量场\(u_t^{target}(x)\)

**核心思想**：从单个数据的"专属导航"，整合出所有数据的"通用导航"，步骤如下：

**第一步：选"过渡路线"（条件概率路径\(p_t(x|z)\)）**

先定一条满足"噪声→单个数据"的路径：对任意数据点\(z\)，\(t=0\)时是纯噪声（\(p_0(\cdot|z)=p_{init}\)），\(t=1\)时是确定性数据\(z\)（\(p_1(\cdot|z)=\delta_z\)，\(\delta_z\)是"采样必返回\(z\)"的分布）。

**第二步：找"专属导航"（条件向量场\(u_t^{target}(x|z)\)）**

找到一个向量场，让 ODE 轨迹刚好沿上面的"过渡路线"走：从噪声\(X_0 \sim p_{init}\)出发，经这个向量场引导，\(X_t=\psi_t^{target}(X_0|z)\)（\(\psi\)是流映射）刚好服从\(p_t(\cdot|z)\)（即"噪声慢慢变成\(z\)"）。

**等价验证**：这个向量场满足"连续性方程"（概率质量守恒，确保轨迹不偏离路线）。

**第三步：整合"通用导航"（边际向量场\(u_t^{target}(x)\)）**

把所有数据点\(z\)的"专属导航"按"贡献度"加权求和，得到全局通用的向量场：

\[u_t^{target}(x) = \int u_t^{target}(x|z) \cdot \frac{p_t(x|z)p_{data}(z)}{p_t(x)} dz \quad (32)\]

**权重解读**：\(\frac{p_t(x|z)p_{data}(z)}{p_t(x)}\)是"数据点\(z\)对当前位置\(x\)的影响占比"——\(z\)和\(x\)越相关（\(p_t(x|z)\)大）、在数据集中越常见（\(p_{data}(z)\)大），它的"专属导航"权重越高。

**最终效果**：这个"通用导航"对应的 ODE 轨迹，会沿"全局过渡路线"（边际概率路径\(p_t(x)\)）走：

\[X_0 \sim p_{init}, \quad \frac{d}{dt}X_t = u_t^{target}(X_t) \Rightarrow X_t \sim p_t \quad (0 \leq t \leq 1), \quad X_1 \sim p_{data} \quad (33)\]

完美实现"噪声→数据"的确定性生成。
### 二、扩展到扩散模型：带校正项的 SDE

流模型是"确定性导航"，扩散模型要加"随机噪声"（提升样本多样性），但噪声会让轨迹跑偏，所以加"校正项"拉回正途。

**核心修改：加噪声 + 加校正**

引入随时间变化的扩散系数\(\sigma_t\)（控制噪声强度），将 ODE 扩展为 SDE：

\[dX_t = \left[ u_t^{target}(X_t) + \frac{\sigma_t^2}{2} \nabla \log p_t(X_t) \right] dt + \sigma_t dW_t \quad (34)\]

**SDE 的三个组成部分**：

- **原有项**\(u_t^{target}(X_t) dt\)：流模型的"通用导航"，保证轨迹"平均方向"不偏
- **随机项**\(\sigma_t dW_t\)：布朗运动驱动的噪声，注入多样性
- **校正项**\(\frac{\sigma_t^2}{2} \nabla \log p_t(X_t) dt\)：分数函数（\(\nabla \log p_t(x)\)）是"概率密度梯度"，指向数据分布核心（像"引力"），\(\sigma_t\)越大校正力越强，抵消噪声的偏离

**关键组件：边际得分函数（\(\nabla \log p_t(x)\)）**

和边际向量场一样，它是所有数据点\(z\)的"专属得分函数"按贡献度加权求和：

\[\nabla \log p_t(x) = \int \nabla \log p_t(x|z) \cdot \frac{p_t(x|z)p_{data}(z)}{p_t(x)} dz \quad (36)\]

专属得分函数\(\nabla \log p_t(x|z)\)可手动推导（不用复杂计算）。

**最终效果**：这个 SDE 的轨迹依然沿"全局过渡路线"\(p_t(x)\)走：

\[X_0 \sim p_{init}, \quad dX_t = \left[u_t^{target}(X_t) + \frac{\sigma_t^2}{2}\nabla \log p_t(X_t)\right]dt + \sigma_t dW_t \Rightarrow X_t \sim p_t \quad (0 \leq t \leq 1), \quad X_1 \sim p_{data} \quad (35)\]

既保留了"噪声→数据"的核心，又通过随机性生成多样化样本。
### 三、实例：高斯概率路径（扩散模型标配）

高斯概率路径是最常用的落地实现，直接给出 3 个核心公式（扩散模型的基础）：

**1. 条件概率路径（过渡路线）**

\[p_t(x|z) = \mathcal{N}(\alpha_t z, \beta_t^2 I_d) \quad (16)\]

高斯分布，均值\(\alpha_t z\)、方差\(\beta_t^2\)。

**2. 条件向量场（专属导航）**

\[u_t^{target}(x|z) = \left(\dot{\alpha}_t - \frac{\dot{\beta}_t}{\beta_t}\alpha_t\right) z + \frac{\dot{\beta}_t}{\beta_t} x \quad (21)\]

其中\(\dot{\alpha}_t = \frac{\partial}{\partial t}\alpha_t\)是\(\alpha_t\)的时间变化率。

**3. 条件得分函数（专属校正）**

\[\nabla \log p_t(x|z) = -\frac{x - \alpha_t z}{\beta_t^2} \quad (28)\]

指向数据\(z\)的"引力方向"。

**噪声调度器**：\(\alpha_t\)、\(\beta_t\)是连续可微、单调函数，满足：
- \(\alpha_0 = \beta_1 = 0\)（\(t=0\)时\(\alpha_t=0 \rightarrow\)纯噪声，\(t=1\)时\(\beta_t=0 \rightarrow\)纯数据）
- \(\alpha_1 = \beta_0 = 1\)（\(t=1\)时\(\alpha_t=1 \rightarrow\)数据权重满，\(t=0\)时\(\beta_t=1 \rightarrow\)噪声权重满）
