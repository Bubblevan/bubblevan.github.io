---
id: dl-chapter-2
title: 第2章 Transformer
sidebar_label: 第2章
---

## 1. 一切的起点：为什么要发明Attention？

在Transformer诞生之前，处理序列数据（比如一句话）的主流模型是RNN（循环神经网络）。

### RNN的工作方式
RNN像一个"单核处理器"，一个词一个词地读。读完第一个词，把信息压缩一下传给第二个词；读完第二个词，再把包含前两个词的信息压缩一下传给第三个词……

### RNN的致命弱点
这就像一个**"传话游戏"**。信息每传递一步，就会有一些损失和遗忘。当句子很长时，传到最后，开头的信息可能已经面目全非了。这导致它很难捕捉长距离依赖关系。

**举例说明：**
比如这句话："我在法国长大，……（中间省略50个词）……，所以我能说一口流利的法语。"

RNN很难把最后的"法语"和开头的"法国"紧密联系起来。

RNN的核心是**"循环"**，它试图通过一个循环传递的隐藏状态 (hidden state, h) 来模拟人类的"短期记忆"。

## 2. 数学与代码实现

让我们来看一个最简单的RNN单元在 t 时刻是如何工作的。

### 输入
- 当前时刻的输入向量：$x_t$ (比如一个词的词向量)
- 上一时刻的隐藏状态：$h_{t-1}$ (来自过去的"记忆")

### 计算
- **更新隐藏状态**：将"当前输入"和"过去记忆"结合起来，通过一个激活函数（通常是 tanh）来生成新的记忆
- **生成输出**：根据新的记忆，生成当前时刻的输出

### 数学公式

$$h_t = \tanh(W_{hh} h_{t-1} + W_{xh} x_t + b_h)$$

$$y_t = W_{hy} h_t + b_y$$

其中：
- $W_{hh}, W_{xh}, W_{hy}$ 是权重矩阵，是模型需要学习的参数。它们在所有时间步都是共享的
- $b_h, b_y$ 是偏置项
- $\tanh$ 是一个将数值压缩到 (-1, 1) 区间的激活函数
### 梯度消失问题

这个链式结构带来了严重的问题。在训练时，误差需要沿着这条链反向传播回来，以更新权重。

**数学推导（直观理解）：**
假设我们要计算损失 $L$ 对最早的隐藏状态 $h_1$ 的梯度 $\frac{\partial L}{\partial h_1}$，根据链式法则，它看起来是这样的：

$$\frac{\partial L}{\partial h_1} = \frac{\partial L}{\partial h_T} \frac{\partial h_T}{\partial h_{T-1}} \frac{\partial h_{T-2}}{\partial h_{T-1}} \cdots \frac{\partial h_1}{\partial h_2}$$

注意到其中反复出现的项 $\frac{\partial h_t}{\partial h_{t-1}}$ 吗？它约等于权重矩阵 $W_{hh}$。这意味着，为了把误差从序列末尾传到开头，你需要将 $W_{hh}$ 连乘很多次。

- 如果 $W_{hh}$ 中的值（严格来说是它的范数）普遍大于1，连乘后梯度会变得超级大，导致**梯度爆炸** (Gradient Exploding)
- 如果 $W_{hh}$ 中的值普遍小于1，连乘后梯度会趋近于0，导致**梯度消失** (Gradient Vanishing)

梯度消失是更常见也更致命的。它意味着模型几乎无法从很久之前的输入中学到任何东西，也就是我们说的"遗忘"。


## 3. Attention的革命性思想

**打破这种"链式"处理！** 让序列中的任何一个词，都能**直接"看到"**并连接到序列中的任何其他词，无论它们相距多远。它把信息处理从"单核单线程"变成了"多核并行"。

### 3.1 核心思想：从"逐步传递"到"一步直达"

Attention说："我不要再玩传话游戏了！在序列的任何一个位置，我都要能直接看到所有其他位置的信息！"

### 3.2 数学与代码实现 (Self-Attention)

我们直接来看Transformer里的自注意力机制，它是如何用Q, K, V实现"一步直达"的。

#### 输入
一个完整的词向量序列 $X \in \mathbb{R}^{N \times d}$ (N是序列长度, d是词向量维度)

#### 计算

**生成Q, K, V：** 用三个不同的、可学习的权重矩阵 $W_Q, W_K, W_V$ 将输入序列 $X$ 投影，得到Q, K, V。

$$Q = XW_Q$$
$$K = XW_K$$
$$V = XW_V$$

**计算注意力分数：**

$$Scores = QK^T$$

这里 $Q \in \mathbb{R}^{N \times d_k}$，$K^T \in \mathbb{R}^{d_k \times N}$，所以结果 $Scores \in \mathbb{R}^{N \times N}$。这是一个注意力矩阵，它的第 (i, j) 个元素表示第 i 个词对第 j 个词的关注程度。

**缩放、归一化、加权求和：**

$$Attention(Q,K,V) = softmax(\frac{QK^T}{\sqrt{d_k}})V$$

- 除以 $\sqrt{d_k}$ 是为了缩放，防止点积结果过大导致softmax梯度消失
- softmax 对分数的每一行进行操作，确保每一行的权重总和为1
- 最后乘以 V，将所有词的Value根据权重加权求和

2. 注意力机制的核心：Q, K, V的图书馆比喻
Attention的计算过程听起来很复杂，但它的本质思想非常直观。我们可以用一个“去图书馆查资料”的比喻来理解 Query (Q), Key (K), Value (V) 这三个关键角色。

想象一下，你要写一篇关于“人工智能在医疗领域的应用”的论文。

Query (Q) - 你的查询意图
你脑子里的研究主题就是Query。它代表了：“我当前关心的是什么？我需要什么样的信息？”

Key (K) - 书架上每本书的“关键词标签”
图书馆里成千上万的书，你不可能一本一本地翻。每本书都有一个书名或关键词标签，这就是Key。它高度概括了这本书是关于什么的，用来和你脑中的Query做匹配。

Value (V) - 书本里真正的“知识内容”
关键词标签只是索引，书里面详实的内容才是你最终想要的知识，这就是Value。Key和Value是一一对应的，同一本书，它的标签是Key，内容是Value。

注意力计算的三部曲：

第一步：计算相关性分数 (Score)
你拿着你的Query（研究主题），去和书架上每一本书的Key（关键词标签）进行比对。比对的方式在Transformer里就是点积 (dot product)。匹配度越高，分数就越高。

Score = Query · Key

第二步：分数归一化 (Softmax)
你得到了一堆相关性分数，但这些分数大小不一，不方便使用。于是你用 Softmax 函数将它们转换成一个总和为1的权重（或叫“注意力分布”）。

Weights = Softmax(Scores)

结果可能是：《AI与影像诊断》这本书分配到70%的注意力。

《机器学习入门》分配到20%的注意力。

《古代史》分配到0.01%的注意力。

第三步：加权求和 (Weighted Sum)
你不会只看一本书。你会根据刚刚得到的注意力权重，去“借阅”所有书的内容（Value），然后组合成一份定制的“信息摘要”。

Output = Weights × Value

最终输出 = 70%的《AI与影像诊断》内容 + 20%的《机器学习入门》内容 + 0.01%的《古代史》内容...

这样，输出结果就高度集中了与你Query最相关的信息。

在Transformer的自注意力 (Self-Attention) 中，Q, K, V都来源于同一个输入序列。也就是说，序列中的每一个词，都既是"查询者"，又是"被查询者"。

```python
import torch.nn.functional as F
import math

# --- 参数定义 ---
seq_length = 5   # 序列长度
d_model = 32     # 词向量维度
d_k = 8          # Q, K 的维度 (通常 d_k = d_model / num_heads)

# --- 模拟输入数据 ---
# (批次大小, 序列长度, 词向量维度)
X = torch.randn(1, seq_length, d_model)

# --- 模拟线性投影层 ---
W_q = nn.Linear(d_model, d_k)
W_k = nn.Linear(d_model, d_k)
W_v = nn.Linear(d_model, d_k) # V的维度可以不同，这里为了简单设为一样

# 1. 生成Q, K, V
Q = W_q(X) # (1, 5, 8)
K = W_k(X) # (1, 5, 8)
V = W_v(X) # (1, 5, 8)

print("--- Self-Attention 手动计算过程 ---")
# 2. 计算分数 Q·K^T 
# K.transpose(-2, -1) 将 (1, 5, 8) 变为 (1, 8, 5)
scores = torch.matmul(Q, K.transpose(-2, -1)) # (1, 5, 5)
print(f"注意力分数矩阵形状: {scores.shape}")

# 3. 缩放
scores = scores / math.sqrt(d_k)

# 4. Softmax归一化
attention_weights = F.softmax(scores, dim=-1)
print(f"注意力权重矩阵 (第一行加总应为1): \n{attention_weights[0]}")
print(f"第一行权重加总: {attention_weights[0][0].sum()}")

# 5. 加权求和
output = torch.matmul(attention_weights, V) # (1, 5, 5) x (1, 5, 8) -> (1, 5, 8)
print(f"最终输出形状: {output.shape}")
```

## 4. 解决顺序问题：位置编码 (Positional Encoding)

刚才的QKV流程有一个大问题：它完全忽略了词的顺序！在他看来，"猫追老鼠"和"老鼠追猫"是一样的，因为词的集合没变。这显然不行。为了让模型理解顺序，我们需要引入位置信息。

### 4.1 经典位置编码 (Absolute Positional Encoding)

**思想：** 给每个位置（第1个、第2个、第3个...）创建一个独一无二的、固定不变的"位置向量"。

**做法：** 将这个"位置向量"直接加到对应位置的"词向量"上。

**比喻：** 就像给每个进教室的学生发一个固定的"座位号"，学生A + 1号座位 和 学生A + 5号座位 对于模型来说是完全不同的输入。

我们反复强调，自注意力机制本身是无序的，它就像一个"装着词的袋子"。为了让模型理解单词的顺序，我们必须手动将位置信息注入到模型中。

### 4.2 sin 和 cos 公式的数学与代码实现

原始 Transformer 论文中使用了一种非常巧妙的 sin 和 cos 函数组合来创建固定的位置编码。

#### 数学公式
对于位置为 pos、维度为 i 的编码，其计算方式如下：

$$PE_{(pos,2i)} = \sin(\frac{pos}{10000^{2i/d_{model}}})$$

$$PE_{(pos,2i+1)} = \cos(\frac{pos}{10000^{2i/d_{model}}})$$

其中：
- pos: 词在序列中的位置 (0, 1, 2, ...)
- i: 向量的维度索引 (0, 1, 2, ...)
- d_model: 词向量的总维度

#### 直观理解
这个公式的巧妙之处在于，它利用了不同频率的 sin/cos 波：

- 在低维部分（i 较小），波长很长，编码值变化很慢
- 在高维部分（i 较大），波长很短，编码值变化很快

这种组合使得每个位置都有一个独一无二的编码向量，并且模型可以很容易地学习到相对位置关系。

#### 代码实现与可视化
我们来创建一个标准的位置编码模块，并把它可视化，这是理解它最好的方式！

```python
import torch
import torch.nn as nn
import math
import matplotlib.pyplot as plt

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super().__init__()

        # 创建一个足够长的位置编码矩阵
        pe = torch.zeros(max_len, d_model)

        # 位置索引 (0, 1, ..., max_len-1)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)

        # 维度索引的除数项 (10000^(2i/d_model))
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        # 偶数维度用 sin
        pe[:, 0::2] = torch.sin(position * div_term)
        # 奇数维度用 cos
        pe[:, 1::2] = torch.cos(position * div_term)

        # 将 pe 注册为 buffer，它不是模型的参数，但会随模型移动(e.g., to(device))
        self.register_buffer('pe', pe)

    def forward(self, x):
        # x: (batch_size, seq_len, d_model)
        # 将位置编码加到输入词向量上
        # self.pe 是 (max_len, d_model)，我们只需要取前 seq_len 个
        # unsqueeze(0) 是为了匹配 batch 维度
        return x + self.pe[:x.size(1), :].unsqueeze(0)

# --- 可视化 ---
plt.figure(figsize=(10, 5))
pe_module = PositionalEncoding(d_model=128, max_len=100)
pe_matrix = pe_module.pe.squeeze(0).numpy() # 获取 (100, 128) 的矩阵

plt.pcolormesh(pe_matrix, cmap='viridis')
plt.xlabel('Embedding Dimension (i)')
plt.ylabel('Position (pos)')
plt.colorbar()
plt.title("Positional Encoding Matrix Visualization")
plt.show()

# --- 使用示例 ---
# 创建一个 dummy 输入
dummy_word_embeddings = torch.randn(2, 10, 128) # (batch=2, seq_len=10, d_model=128)
# 添加位置编码
embeddings_with_pos = pe_module(dummy_word_embeddings)
print("\n--- 位置编码使用示例 ---")
print("原始词向量形状:", dummy_word_embeddings.shape)
print("加入位置编码后形状:", embeddings_with_pos.shape)
```
可视化结果解读：
你会看到一张彩色的图，这张图完美地揭示了位置编码的奥秘：

Y轴是位置，从上到下代表序列的开头到结尾。

X轴是维度，从左到右代表128维向量的每一维。

你会清晰地看到平滑变化的正弦/余弦波。左侧（低维）的波纹很宽，右侧（高维）的波纹非常密集。正是这种独特的、跨越不同频率的“模式”，让Transformer能够精确地“感知”到每个词的绝对和相对位置。
旋转位置编码 (RoPE - Rotary Positional Embedding)

这是现在大模型（如Llama）更青睐的方式，它编码的是相对位置。

思想：不直接给一个固定的“座位号”，而是给每个词的向量赋予一个随位置变化的“旋转角度”。

比喻：想象每个词向量都是一个罗盘指针。

第1个词的指针不旋转。

第2个词的指针旋转15°。

第3个词的指针旋转30°...

好处：当计算两个词（比如第2个和第5个）的相关性时，模型关注的是它们指针之间的夹角（比如 75° - 15° = 60°）。这个相对夹角是固定的，无论这两个词出现在句子的开头还是结尾。这使得模型能更好地泛化到不同长度的句子。

4. 机制升级：多头注意力 (Multi-Head Attention)
一个注意力机制（一个“头”）可能只能学习到一种关系模式（比如语法关系）。但一句话里可能包含多种关系（语法关系、语义关系、指代关系等）。怎么办？

思想：大力出奇迹！一次不行，就多来几次。

比喻：你不是只派一个图书管理员（一个头）去查资料，而是派了一个专家团队。

Head 1 (语法专家)：他的QKV被训练得专门去寻找主谓宾关系。

Head 2 (语义专家)：他的QKV专门去寻找同义词、反义词。

Head 3 (上下文专家)：他的QKV专门去寻找长距离的因果、指代关系。

做法：

把原始的词向量切分成N份（比如8个头，就切成8份）。

每一份都独立地进行一次完整的QKV注意力计算。

得到N个各自的输出结果。

将这N个结果拼接起来，再通过一个线性层进行信息融合。

好处：让模型能够并行地从不同的“子空间”中学习到多种多样的信息，极大地丰富了模型的表达能力。
1. 为什么一个“头”不够用？
单个自注意力机制，就像只有一个关注点的人。在阅读一句话时，他可能只学会了关注语法结构（比如动词和主语的关系），但可能会忽略语义上的关联（比如“苹果”和“水果”的关系）。

我们希望模型能更“聪明”，能同时捕捉到多种不同类型的关系。

2. 核心思想：专家团队并行工作
多头注意力的思想非常暴力且有效：“既然一个头不够，那就同时上八个头！”

比喻：还是那个图书馆查资料的例子。你不再只派一个图书管理员去帮你查，而是派了一个专家委员会，比如一个8人的团队。

Head 1 (语法专家)：他只负责寻找句子成分关系。

Head 2 (语义专家)：他只负责寻找近义词、反义词关系。

Head 3 (指代专家)：他只负责寻找 "it", "he", "they" 到底指向谁。

...

Head 8 (长距离主题专家)：他负责寻找文章的整体主题关联。

这8位专家同时出发，并行工作，每个人都独立地进行自己的 Q, K, V 计算，最后带回一份自己的“信息摘要”。

3. 数学与代码实现
输入:

词向量序列 X∈R 
N×d_model
 

头的数量 h (比如 h=8)

计算:

维度划分：首先，我们将模型的总维度 d_model 划分给每个头。例如，d_model=512，有 h=8 个头，那么每个头分到的维度就是 d_k=d_v=d_model/h=512/8=64。

独立投影：为每一个头 i (i=1,...,h) 都创建一套独立的、可学习的权重矩阵：$W_Q^i, W_K^i, W_V^i$。然后，用它们来生成每个头专属的 Q, K, V。

$$Q_i = X W_Q^i, \quad K_i = X W_K^i, \quad V_i = X W_V^i$$
 
并行计算注意力：每个头都独立地执行我们上节课学的注意力计算。

$$\text{head}_i = \text{Attention}(Q_i, K_i, V_i) = \text{softmax}\left(\frac{Q_i K_i^T}{\sqrt{d_k}}\right) V_i$$
 
拼接与融合：将所有头得到的输出 head_i 拼接起来。

$$\text{Concat}(\text{head}_1, \text{head}_2, \ldots, \text{head}_h) \in \mathbb{R}^{N \times (h \times d_v) = N \times d_{\text{model}}}$$

最后，将这个拼接后的大矩阵再通过一个最终的线性层 $W_O$ 进行一次信息融合，得到多头注意力的最终输出。

$$\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, \ldots, \text{head}_h) W_O$$
 
PyTorch代码示例 (简化版):

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model=512, num_heads=8):
        super().__init__()
        assert d_model % num_heads == 0
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        # 将所有头的 W_q, W_k, W_v 矩阵合并成一个大的线性层，更高效
        self.W_qkv = nn.Linear(d_model, d_model * 3) 
        self.W_o = nn.Linear(d_model, d_model)

    def forward(self, x):
        # x: (batch, seq_len, d_model)
        batch_size, seq_len, _ = x.shape

        # 1. 独立投影 + 维度划分
        # (batch, seq_len, d_model * 3) -> 3 * (batch, seq_len, d_model)
        qkv = self.W_qkv(x).chunk(3, dim=-1)
        # 3 * (batch, seq_len, num_heads, d_k) -> 3 * (batch, num_heads, seq_len, d_k)
        q, k, v = [val.view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2) for val in qkv]

        # 2 & 3. 并行计算注意力 (用一个函数封装)
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d_k)
        attention_weights = F.softmax(scores, dim=-1)
        context = torch.matmul(attention_weights, v)

        # 4. 拼接与融合
        # (batch, num_heads, seq_len, d_k) -> (batch, seq_len, num_heads, d_k) -> (batch, seq_len, d_model)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)

        output = self.W_o(context)
        return output

# --- 测试 ---
mha = MultiHeadAttention()
input_tensor = torch.randn(2, 10, 512) # (batch=2, seq_len=10, d_model=512)
output_tensor = mha(input_tensor)
print(f"多头注意力输出形状: {output_tensor.shape}") # 应为 (2, 10, 512)
```


## 5. 完整的Transformer架构 - 不仅仅是Attention

Attention虽然是灵魂，但一个完整的Transformer模型还需要一些重要的"辅助组件"。我们以Encoder（编码器）为例，看看一个标准的模块长什么样。

### 5.1 Encoder Block（编码器模块）的构成

它就像一个乐高积木，可以重复堆叠。每个积木块包含两个核心部分。

#### 第一部分：多头自注意力层 (Multi-Head Self-Attention)
就是我们刚刚讲的，负责让输入序列内部的词元互相"交流"，捕捉上下文关系。

#### 第二部分：前馈神经网络 (Feed-Forward Network, FFN)
这是一个非常简单的两层全连接网络，被独立地作用于序列中的每一个词元上。

**作用：** 它为模型提供了非线性变换的能力。如果说注意力层负责"信息交互与融合"，那么FFN层就负责对融合后的信息进行"深度加工和提炼"。

#### 重要的辅助组件：残差连接 (Add) 和层归一化 (Norm)

你会发现，在Attention层和FFN层之后，都跟着一个 Add & Norm 操作。

- **Add (残差连接)：** 就是把该层的输入 X 直接加到该层的输出 Y 上，即 X+Y。
  - **作用：** 这是一个"高速公路"，允许信息和梯度直接跳过某些层向前或向后流动。这极大地缓解了深度网络中的梯度消失问题，让我们可以把模型做得非常深。

- **Norm (层归一化)：** 对每个样本的特征进行归一化，使其均值为0，方差为1。
  - **作用：** 让模型的训练过程更稳定、更快速。

### 5.2 完整的Encoder-Decoder架构

原始的Transformer是为机器翻译（Seq2Seq任务）设计的，所以它包含一个编码器(Encoder)和一个解码器(Decoder)。

**比喻：** 一位精通双语的翻译官

#### Encoder (阅读和理解阶段)
- 它由一堆Encoder Block堆叠而成（比如6个）
- 它的任务是完整地阅读源语言句子（比如英文："I love cats"）
- 经过层层处理，它最终输出一套富含上下文信息的特征向量。这份输出可以被看作是Encoder对整个句子的深度理解

#### Decoder (翻译和生成阶段)
- 它也由一堆Decoder Block堆叠而成
- 它的任务是一个词一个词地生成目标语言的句子（比如法文："J'aime les chats"）

**Decoder的核心区别：** 它内部有两个注意力层！

1. **第一个是"带掩码的"多头自注意力 (Masked MHA)：** Decoder在生成第3个词时，只能看到第1、2个词，**不能"偷看"**后面的答案。这个"掩码"就是用来遮挡未来信息的。

2. **第二个是"交叉注意力" (Cross-Attention)：** 这是连接Encoder和Decoder的桥梁！在这一层，Q来自于Decoder自身（它想知道下一步该生成什么），而 K和V来自于Encoder的最终输出（即Encoder对源句子的深度理解）。

这完美地模拟了翻译过程：Decoder一边思考自己已经说出口的法文，一边反复回顾原文（英文）的含义，来决定下一个最合适的法文单词。

**最后一步：** Decoder的最终输出会经过一个线性层和Softmax，来预测词典中每个词成为下一个词的概率。
## 6. 为什么需要"掩码" (Mask)？

我们先回顾一下场景：这个机制专门用在 Transformer 的 Decoder 部分。

Decoder 的任务是生成，比如从英文翻译成法文。它是一个词一个词地往外"吐"的，这个过程叫自回归 (Autoregressive)。

### 6.1 问题分析
**问题：** 假设我们正在翻译 "I love cats" -> "J'aime les chats"。当 Decoder 准备生成第3个词 "les" 的时候，它只能看到它已经生成的前两个词 "J'aime"。它绝对不能看到答案 "les" 或者更后面的 "chats"。如果看到了，那就是"作弊"，模型就学不到真正的预测能力了。

**挑战：** 但是，我们之前学的自注意力是全局的 (All-to-All)！它会让 "J'aime"、"les"、"chats" 互相看到对方。

**解决方案：** 我们需要一个掩码 (Mask)，像一个"遮挡板"，在计算注意力分数时，强行把"未来"的信息给遮住。

### 6.2 "掩码"的数学与代码实现

这个"遮挡"操作非常巧妙，它发生在计算完分数矩阵 $QK^T$ 之后，但在进行 Softmax 之前。

#### 数学原理
Softmax 函数是 $e^x$ 的归一化。指数函数 $e^x$ 有一个特点：当 x 是一个非常大的负数（比如 $-\infty$）时，$e^x$ 会无限趋近于 0。

所以，我们只需要把所有想"遮挡"的位置的注意力分数，都设置为一个非常大的负数，那么经过 Softmax 之后，这些位置的注意力权重就自然变成 0 了。

#### 代码实现与详解
我们来手动构建这个过程，看看张量在每一步的变化。

```python
import torch
import torch.nn.functional as F
import math

# 假设序列长度为 4
seq_len = 4

# --- 1. 创建一个"未来"信息的遮挡板 (Mask) ---
# torch.triu 创建一个上三角矩阵, diagonal=1 表示不包括对角线
# 值为1的地方，就是我们需要遮挡的"未来"位置
mask = torch.triu(torch.ones(seq_len, seq_len), diagonal=1).bool()

print("--- Step 1: 创建遮挡 Mask ---")
print("Mask (True=遮挡):")
print(mask)
# tensor([[False,  True,  True,  True],
#         [False, False,  True,  True],
#         [False, False, False,  True],
#         [False, False, False, False]])

# --- 2. 模拟一个注意力分数矩阵 (Q·K^T 的结果) ---
# 假设这是一个已经计算好的分数
scores = torch.randn(seq_len, seq_len)

print("\n--- Step 2: 原始注意力分数 (Softmax之前) ---")
print(scores)

# --- 3. 应用 Mask ---
# 将 mask 中为 True 的位置，在 scores 中用 -infinity 填充
scores.masked_fill_(mask, float('-inf'))

print("\n--- Step 3: 应用 Mask 后的分数 ---")
print("注意右上角都被替换成了 -inf")
print(scores)

# --- 4. 进行 Softmax ---
attention_weights = F.softmax(scores, dim=-1)

print("\n--- Step 4: Softmax 后的最终注意力权重 ---")
print("注意右上角权重都变成了 0.0")
print(attention_weights.round(decimals=2))
```

#### 代码输出分析（关键！）

你会看到，最终的 attention_weights 矩阵：

- **第1行：** 只有第1个位置有权重，它只能关注自己
- **第2行：** 只有前2个位置有权重，它只能关注自己和第1个词
- **第3行：** 只有前3个位置有权重，它能关注自己和前2个词