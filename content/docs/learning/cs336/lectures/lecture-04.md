---
title: "L04 · MoE"
weight: 4
date: 2026-08-28
updated: 2026-09-08
course: "CS336"
topics: ["CS336", "attention alternatives", "moe", "architecture"]
aliases:
  - /blog/2026/2026-08-28-cs336-lecture4/
---

Lecture 3 建立的是一个 dense Transformer：每个 token 都参与 attention，每个 token 都经过同一个 FFN。Lecture 4 追问的是：**为什么每一次计算都要访问全部历史、全部参数？**

这堂课的两个主线看似不同，实际上都在做同一件事：把“模型拥有的总能力”与“一次 forward 真正访问的计算”分开。

- 对 attention：不要让每个 query 与所有历史位置发生同等昂贵的交互。
- 对 FFN：让不同 token 只激活一小部分 experts。

前者导向 linear attention、state-space model 和 sparse attention；后者导向 Mixture of Experts（MoE）。

![Attention alternatives：full attention、linear/SSM 与 sparse attention 的三条路线](/learning/cs336/lectures/l4-attention-alternatives.png)

> 图：用一个统一视角看 Lecture 4 前半。full attention 保留并访问全部交互，linear/SSM 把历史写入有限状态，sparse attention 保留历史但只选择少数位置。该图按本地 OpenAI 风格绘制。

## 1. 从 full attention 到 linear attention：关键是换括号

标准 self-attention 的核心计算是

$$
Y=\operatorname{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V,
\qquad Q,K\in\mathbb{R}^{N\times d_k},\ V\in\mathbb{R}^{N\times d_v}.
$$

先忽略 softmax 和缩放项，只看矩阵乘法：

$$
(QK^\top)V.
$$

矩阵乘法满足结合律，所以可以改成

$$
(QK^\top)V=Q(K^\top V).
$$

两种写法的数学结果相同，但中间矩阵完全不同。

原来的顺序先计算

$$
QK^\top:\quad [N,d_k][d_k,N]\rightarrow[N,N],
$$

代价约为 $O(N^2d_k)$；再与 $V$ 相乘，总代价约为

$$
O\left(N^2(d_k+d_v)\right).
$$

新顺序先算

$$
K^\top V:\quad [d_k,N][N,d_v]\rightarrow[d_k,d_v],
$$

再计算 $Q(K^\top V)$。当 $d_k,d_v$ 相对 $N$ 固定时，代价从关于 $N$ 的二次增长变成线性增长：

$$
O\left(Nd_kd_v\right)=O(N).
$$

原始课件把这一点放在最前面，是因为它是后续所有 recurrent 形式的入口：不是先背模型名，而是先看清楚**计算顺序决定了中间对象的形状**。

![Lecture 4 原始课件第 4 页：linear attention 的结合律重排](/learning/cs336/lectures/l4-slide-04-04.png)

> 原始课件页：这里的线性化不是把标准 softmax attention “优化”成了等价的低复杂度实现，而是先移除了 softmax，改变了模型的数学形式。

### softmax 为什么不能一起换括号？

标准 attention 不能直接写成

$$
Q\operatorname{softmax}(K^\top V),
$$

因为 softmax 是非线性函数，一般不存在

$$
\operatorname{softmax}(QK^\top)V
=Q(K^\top V).
$$

因此这里有一个必须分清的边界：

> **linear attention 的线性复杂度来自不同的计算结构，不是对 full softmax attention 做了一个完全等价的括号优化。**

这也解释了为什么“把复杂度从 $O(N^2)$ 变成 $O(N)$”并不等于问题已经解决。你需要付出的代价是：如何在不显著损失表达能力的情况下，把历史表示成一个可维护的有限状态。

## 2. causal 形式为什么自然变成 recurrent state

在 causal language model 中，第 $t$ 个 token 只能读取前缀。忽略归一化后，linear attention 可以写成

$$
y_t=q_t^\top\left(\sum_{i\le t}k_iv_i^\top\right).
$$

把括号里的历史汇总定义为

$$
S_t=\sum_{i\le t}k_iv_i^\top,
$$

就得到递推式

$$
S_t=S_{t-1}+k_tv_t^\top,
\qquad y_t=q_t^\top S_t.
$$

这就是一个很典型的 recurrent state：新 token 到来时，用 $k_t,v_t$ 更新状态，再用 $q_t$ 读取状态。训练时可以使用并行的矩阵形式，推理时可以使用逐 token 的 recurrence，因此它同时保留了 GPU 友好的训练路径和固定状态的 decode 路径。

这与普通 attention 的 KV cache 形成鲜明对比。full attention 需要保留越来越长的 $K_1,\ldots,K_t$ 和 $V_1,\ldots,V_t$；linear recurrence 只需要维护

$$
S_t\in\mathbb{R}^{d_k\times d_v},
$$

状态大小不随 context length 增长。对极长上下文来说，这是非常诱人的性质。

但固定状态也正是风险所在。full attention 保留历史中的每一个 token；recurrent model 必须把整个历史压进固定大小的 $S_t$。如果很早的位置藏着一个关键事实，模型就必须在很长的序列中持续保护它，而不能让后续信息把它冲淡。

所以前半部分真正的 trade-off 是：

$$
\boxed{\text{更低的访问成本}\quad\leftrightarrow\quad\text{更强的历史保真度}}
$$

### 从“只会加”到带遗忘和改写的状态

朴素更新

$$
S_t=S_{t-1}+k_tv_t^\top
$$

只会写入，不会遗忘。一个更接近现代 SSM 的教学抽象是

$$
S_t=\gamma_tS_{t-1}+k_tv_t^\top,
\qquad 0\le\gamma_t\le1.
$$

$\gamma_t$ 接近 1 时保留旧状态，接近 0 时快速遗忘。再进一步，Gated DeltaNet 一类方法不只控制“保留多少”，还根据当前 key 的预测误差定向擦除并写入：

$$
\hat v_t=S_{t-1}k_t,
\qquad e_t=v_t-\hat v_t,
$$

$$
S_t=S_{t-1}+\beta_t e_tk_t^\top.
$$

其中 $-\beta_tS_{t-1}k_tk_t^\top$ 可以理解为擦掉当前 key 方向的旧记忆，$+\beta_tv_tk_t^\top$ 则写入新 value。这样看，许多 attention alternatives 又出现了类似 LSTM 的门控和记忆更新；真正的不同在于，它们通常还设计了适合并行训练的形式。

## 3. 不压缩，改成筛选：sparse attention

linear/SSM 的哲学是“压缩历史”。另一条路线是不把 token 合并，而是让 query 只访问少数重要位置。原始课件用 DeepSeek Sparse Attention（DSA）说明这种思路：先用一个较轻的 indexer 找候选位置，再对 top-$k$ 位置执行更昂贵的 attention。

可以把它想成两级检索：先用低维、低精度或更便宜的表示快速判断哪些位置值得看，再只在选中的位置上运行高质量的 attention。

如果 $N=1{,}000{,}000$ 而最终只保留 $k=2048$ 个位置，主 attention 的工作量就不必直接面对全部一百万个 token。不过，indexer 本身仍然需要做广泛的匹配，因此 DSA 不是严格意义上的“把所有计算都变成 $O(N)$”。它更准确的价值是：**让最昂贵的那部分计算变成 sparse，并把筛选部分做得足够便宜。**

这和 FlashAttention 也要区分开：FlashAttention 主要优化 exact attention 的执行和内存访问，数学上的 pairwise interaction 仍然存在；linear/SSM 改变了状态表示；sparse attention 则保留历史、减少访问。

| 路线 | 历史如何保存 | 主要节省什么 |
| --- | --- | --- |
| Full attention | 每个位置都可直接访问 | 不主动压缩，能力最完整 |
| Linear / SSM | 压入固定大小 state | 长上下文的状态和访问成本 |
| Sparse attention | 保留 token，只访问少数位置 | 主要 attention 的计算量 |
| FlashAttention | 数学形式不变 | HBM 访问和 kernel 执行开销 |

实践中因此很自然地出现 hybrid architecture：大多数层采用便宜的 linear/recurrent 结构，间隔性插入 full attention，让模型仍有机会直接读取未压缩的历史。它不是一个“所有层都换掉”的二元选择，而是在信息保真度和计算成本之间调节比例。

## 4. MoE：让 FFN 也变成条件计算

前半在问“每个 query 是否真的需要看所有 token”，后半把同样的问题问到 FFN：每个 token 是否真的需要经过同一个完整的 FFN？

一个 dense FFN 可以替换成许多 experts，再加一个 router。对某个 token，router 只选择 top-$k$ 个 expert，最后把它们的输出按路由权重加权合并。

![Lecture 4 原始课件第 15 页：MoE 的基本结构](/learning/cs336/lectures/l4-slide-15-15.png)

> 原始课件页：MoE 的基本结构是“替换 FFN，再用 router 选择少数模块”；它不是把 Transformer 的 attention 骨架完全推翻。

![MoE routing：router 从多个 experts 中选择 top-k，并合并被选中的输出](/learning/cs336/lectures/l4-moe-routing.png)

> 图：对一个 hidden state，只有被 top-$k$ 选中的 experts 参与计算。未选中的 expert 不产生本次 token 的 FFN FLOPs。该图按本地 OpenAI 风格绘制。

假设原来的 FFN 有 $P$ 个参数，复制成 4 个 experts 后总参数约为 $4P$，但每个 token 如果只选择一个 expert，激活的 FFN 参数仍约为 $P$。这就是 MoE 的核心收益：

$$
\boxed{\text{扩大总参数容量，但不按同样比例扩大每 token 的 FFN 计算}}
$$

因此“总参数”和“激活参数”必须分开读。一个标记为 200B total、20B active 的模型，并不是普通的 20B dense model：前者决定存储容量、统计容量和通信规模，后者只是近似描述一个 token 实际经过了多少专家参数。

### router、token choice 与 expert choice

最简单的 router 是一层线性映射：

$$
r=W_rx,\qquad r\in\mathbb{R}^{E},
$$

再对 logits 做 softmax 并取 top-$k$。若 $E=64,K=2$，一个 token 可能被送到 Expert 7 和 Expert 41，输出可以抽象为

$$
y=p_7E_7(x)+p_{41}E_{41}(x).
$$

常见的 token-choice routing 是“token 选择自己要去的 experts”；expert-choice routing 则是“每个 expert 从 token 中选择自己要处理的那一批”。前者直观、实现常见，但会带来容量和负载不均衡问题。

![Lecture 4 原始课件第 27 页：routing function 的几种基本视角](/learning/cs336/lectures/l4-slide-27-27.png)

> 原始课件页：routing 不只是一个 top-k 函数，还牵涉 token 如何分发、expert 如何接收，以及整个路由目标如何被优化。

### expert collapse 与 load balancing

稀疏路由有一个正反馈陷阱：某个 expert 偶然稍强，router 就把更多 token 送给它；它得到更多梯度后变得更强，于是吸引更多 token。最后可能只有少数 experts 真正工作，其余 experts 既没有足够数据，也没有足够梯度。

一种经典的辅助均衡目标可以写成

$$
L_{\text{balance}}=\alpha E\sum_{i=1}^{E}f_iP_i,
$$

其中 $f_i$ 是真正被发送给 expert $i$ 的 token 比例，$P_i$ 是 router 分配给它的平均 probability mass。若所有 experts 均匀，$f_i$ 和 $P_i$ 都接近 $1/E$；若所有 token 都涌向 expert 1，则 $f_1\approx P_1\approx1$，损失会显著增大。

比背公式更重要的是看它在推动什么。对 $P_i$ 求导：

$$
\frac{\partial L_{\text{balance}}}{\partial P_i}=\alpha E f_i.
$$

已经很热门的 expert 拥有更大的 $f_i$，所以 loss 会更强地压低它的路由概率。这是一个负反馈，目的不是让每个 expert 学到完全一样的东西，而是避免系统只用其中一小部分。

均衡还不只是优化问题，也是系统问题。如果一个 expert 收到 2000 个 token，另一个只收到 100 个，整个 step 的速度由最忙的那张卡决定；如果 experts 分布在不同 GPU，还要额外承担 token dispatch、all-to-all 和返回通信。于是 MoE 的真实成本必须同时看 FLOPs、显存、通信、负载均衡和 kernel 利用率。

## 5. DeepSeekMoE：更细的 experts 和 shared expert

把大 expert 切成更多小 expert，可以在类似激活预算下增加组合空间。例如从“8 个 experts 选 2 个”改成“64 个小 experts 选 16 个”，组合数从

$$
\binom82=28
$$

变成

$$
\binom{64}{16},
$$

不同 token 可以获得更细粒度的 expert mixture。这就是 fine-grained experts 的直觉：不是简单堆更多完整 FFN，而是把路由粒度做细。

但有些能力几乎每个 token 都需要。如果每个 routed expert 都重复学习通用语言建模、基本句法和常见 feature transformation，容量会被大量冗余消耗。shared expert 因此承担一部分始终激活的通用能力，routed experts 则负责更有区分度的 specialization。

原始课件用 DeepSeekMoE → DeepSeek-V2 → DeepSeek-V3 串起了这一系列设计变化：先是 fine-grained routed experts 与 shared experts，再叠加 MLA 来压缩 KV cache，最后继续处理负载均衡和训练目标之间的冲突。

![Lecture 4 原始课件第 56 页：DeepSeekMoE V3 的结构变化](/learning/cs336/lectures/l4-slide-56-56.png)

> 原始课件页：DeepSeek-V3 不是单独某个技巧，而是 MoE、MLA、负载均衡和训练配方共同演化的结果。

### auxiliary-loss-free balancing 的动机

传统做法把负载均衡写进总目标：

$$
L=L_{\text{LM}}+\lambda L_{\text{balance}}.
$$

问题在于，均衡是系统约束，却未必是语言建模目标。如果 $\lambda$ 太强，模型可能为了平均分发 token 而牺牲有意义的 specialization。DeepSeek-V3 采用动态的 expert-selection bias 作为主要均衡手段，只保留很弱的辅助项来避免极端失衡；这体现的是一个更一般的原则：**能用路由机制解决的系统约束，就尽量少污染模型真正优化的任务目标。**

## 6. MoE 的系统代价：稀疏不等于免费

MoE 降低的是每 token 的激活计算，不会自动降低所有成本。

- **参数存储**：所有 experts 都要驻留在显存或分布式设备中，总参数仍然决定模型容量和存储压力。
- **通信**：router 之后，token 可能需要被发往另一张 GPU 的 expert，再把结果发回来。
- **负载不均衡**：热门 expert 或热门设备会成为整个 step 的瓶颈。
- **kernel 效率**：每个 expert 收到的 token 数量较小或不规则时，GEMM 可能难以达到 dense 大矩阵的利用率。
- **数值稳定性**：router logits、softmax、top-k 和容量限制都可能把训练推到敏感区域。

这就是为什么“理论 FLOPs 很漂亮”不等于“真实速度一定漂亮”。Lecture 2 讲的 memory、bandwidth、arithmetic intensity，在 MoE 里又通过 dispatch、all-to-all 和 device-level balancing 重新出现。

MoE 也因此增加了一个自然的并行维度：expert parallelism。可以把不同 experts 放到不同设备上，router 完成之后先做 token dispatch，expert 计算完成后再做一次反向 dispatch。它扩大了模型可容纳的 expert 数量，却把架构问题与后续的分布式系统问题紧紧绑在一起。

### router 的数值问题与训练稳定性

router 的局部计算看起来只是

$$
x\rightarrow W_rx\rightarrow\operatorname{softmax}\rightarrow\operatorname{TopK},
$$

但它位于大量 token 的分发边界上。logits 过大、概率过尖、容量溢出或低精度误差，都可能导致训练突然失衡。因此实践中会看到更高精度的 router、z-loss、容量控制和其他稳定化策略。这里和 Lecture 3 对 softmax、logit scale 与训练稳定性的讨论是同一条线：小算子在大规模训练里可能成为关键边界。

## 7. upcycling、fine-tuning 与为什么要看总容量

如果已经有一个训练好的 dense FFN，不一定只能从头训练 MoE。upcycling 的基本想法是复制 dense FFN 得到多个初始相同的 experts，再初始化 router 继续训练：

$$
E_1=E_2=\cdots=E_E
\quad\longrightarrow\quad
E_i\text{ 在不同路由和梯度下逐渐分化}.
$$

它可以把已有 dense checkpoint 作为 MoE 的起点，但也不是免费的转换：router 要学会分工，experts 要获得足够多样的数据和梯度，通信与均衡问题仍然存在。

fine-tuning 时则要反过来警惕“active 参数很少”的错觉。一个 200B total、20B active 的 MoE，每个 token 的 FFN 计算可能接近 20B 级别，但它依然拥有 200B 的可调整容量。下游数据很小时，过拟合和路由偏移可能比 dense 小模型更难控制；只调整 attention 或非 MoE 部分，有时反而是更稳妥的起点。

## 8. 把 Lecture 2、3、4 串起来

三讲可以压缩成一条很清楚的演进链：

1. **Lecture 2：成本从哪里来？** 看 FLOPs、显存、带宽、算术强度，以及训练和 decode 的不同瓶颈。
2. **Lecture 3：dense Transformer 怎么造？** 看 residual stream、normalization、attention、RoPE、SwiGLU 与训练稳定性。
3. **Lecture 4：哪些 dense 计算其实可以条件化？** 对历史使用压缩或筛选，对 FFN 使用路由和稀疏激活。

因此，看到一个新架构时可以先问三个问题：

- 它是在改变数学对象，还是只是在优化执行？FlashAttention 属于后者。
- 它是在压缩历史、筛选历史，还是保留完整历史？linear/SSM、sparse attention 和 full attention 的差别就在这里。
- 它减少的是每 token 的激活计算，还是模型真正的总容量？MoE 的 active parameters 与 total parameters 不能混为一谈。

对 A1 来说，Lecture 4 不是要求你立刻实现 Mamba、DSA 或 MoE。A1 的主线仍然是 tokenizer、标准 Transformer、optimizer 和训练循环；Lecture 4 更适合在 baseline 跑通后，用来设计 GQA、hybrid attention、MoE 或其他 architecture ablation。先把 dense baseline 的 shape、数值稳定性和 profiling 做扎实，再引入稀疏结构，才能知道速度变化究竟来自架构、kernel 还是通信。

## 9. 复盘时必须能自己推出来的内容

**第一，为什么 linear attention 可以线性化？** 写出

$$
(QK^\top)V=Q(K^\top V),
$$

标出两种中间矩阵的 shape，并解释为什么 softmax 破坏了这个重排。

**第二，causal recurrence 怎么来？** 从

$$
y_t=q_t^\top\sum_{i\le t}k_iv_i^\top
$$

推出

$$
S_t=S_{t-1}+k_tv_t^\top,
\qquad y_t=q_t^\top S_t.
$$

**第三，为什么固定 state 可能丢信息？** 因为整个历史必须被压缩进固定大小的状态，而 full attention 保留了每个 token 的独立访问路径。

**第四，MoE 的 total 与 active 怎么算？** 例如 100 个 experts、每个 100M 参数、top-2：总 expert 参数是 10B，每个 token 激活约 200M；这不是一个“200M 模型”，因为存储和统计容量仍接近 10B 级别。

**第五，为什么会 expert collapse？** 说清楚“被选中 → 得到更多梯度 → 变得更强 → 更容易被选中”的正反馈，并说明 load-balancing loss 如何对热门 expert 形成负反馈。

**第六，为什么 MoE 的真实速度未必随理论 FLOPs 改善？** 至少要想到 all-to-all communication、load imbalance、irregular/tiny GEMM、router overhead、所有 experts 的显存，以及设备之间的同步等待。

如果最后只留下两个公式，我会留下：

$$
(QK^\top)V\Rightarrow Q(K^\top V)\Rightarrow S_t
$$

它代表把全历史交互改写成可递推的状态；以及

$$
y(x)=\sum_{i\in\operatorname{TopK}(r(x))}p_i(x)E_i(x),
$$

它代表把“所有参数都参与”改成“由输入选择少数参数”。整堂 Lecture 4 的核心不是某个模型名，而是一个架构判断：**一次计算究竟需要访问模型拥有的全部信息，还是只需要其中一部分？**
