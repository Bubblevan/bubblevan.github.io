---
title: "L10 · Inference"
weight: 10
date: 2026-08-29
updated: 2026-09-10
course: "CS336"
topics: ["CS336", "inference", "serving"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture10/
---

Lecture 10 讨论的不是 `model.generate()` 这个 API，而是一个模型上线以后反复发生的系统问题：如何在有限的显存和带宽下，持续服务大量长度不一、到达时间不一的请求。

训练通常是一次性成本；推理则会发生在聊天、代码补全、评测、强化学习 rollout，以及 agent 的内部轨迹中。尤其是 agent，用户最后看到的输出可能很短，但模型在中间产生的思考和工具调用轨迹很长，所以每一个生成 token 都会变成真实的计算和服务成本。

![原始课件中的 inference workload 总览](/learning/cs336/lectures/l10-inference-schema.png)

这堂课可以沿着一条线复盘：先理解推理为什么和训练不同，再找出 memory-bound 的瓶颈，最后分别从模型结构、采样算法和 serving 系统三个层面下手。

## 1. 推理的三个速度指标

### 先分清楚“快”到底指什么

推理场景里至少有三个经常被混在一起的指标：

- **Time to First Token（TTFT）**：请求发出后，用户看到第一个 token 需要等多久。它主要由 prompt 的 prefill 决定，直接影响交互的即时感。
- **Inter-token latency**：生成阶段相邻 token 之间的间隔，也可以粗略写成 seconds/token。它决定打字机效果是否流畅。
- **Throughput**：单位时间服务了多少 token，通常写成 tokens/second。它对批处理、离线评测和大规模 rollout 更重要。

这三个指标并不总是同向变化。增大 batch 往往能提高总体吞吐，却会让每一步要搬运的 KV cache 变多，从而拉长单个请求的延迟。一个 serving 系统不能只报一个“tokens/s”就宣称自己更快，必须说明是在优化 TTFT、单请求延迟，还是并发吞吐。

### 为什么推理值得单独优化

推理中的 token 来源大致有三类：面向用户的实际产品、用来测模型能力的评测，以及需要大量采样的 RL/agent 工作流。它们共同的特点是：训练只做一遍，推理会把同一个模型的成本放大很多遍。

训练时，一批样本的目标 token 通常已经全部给出，Transformer 可以沿着 sequence 维度并行做矩阵乘法；自回归推理则必须先生成当前 token，才能知道下一个 token 的输入。于是推理虽然也有大矩阵乘法，却被一个无法消除的顺序依赖包住了。

可以先记住这句判断：

$$
\boxed{\text{训练更关心把计算单元喂饱；推理更关心少搬数据并处理动态请求。}}
$$

## 2. Prefill、Decode 与推理的顺序依赖

### 两个阶段

一次带 prompt 的生成通常分成两个阶段：

1. **Prefill**：把已有 prompt 的所有 token 一次性送进模型，计算出隐藏状态和 KV cache。sequence 维度可以并行，因此通常更容易变成 compute-bound。
2. **Decode**：每一步只生成一个新 token，再把它接回上下文继续生成。这个阶段是顺序的，且每一步都要读取模型权重和已有 KV cache，通常更容易受显存带宽限制。

如果没有 KV cache，生成第一个新 token 时要处理 prompt；生成第二个新 token 时又把 prompt 和第一个新 token 全部重算一遍。假设要生成 \(T\) 个 token，每次前向都要处理不断增长的历史，那么重复工作会让总计算量呈现 \(O(T^3)\) 的增长趋势：单次 attention 对长度为 \(T\) 的序列是二次量级，而每一步都重算历史。

KV cache 的想法很直接：历史 token 的 key/value 已经算过，就把它们保存下来；下一步只需要为新 token 计算 query、key、value，再和已有 cache 交互。这样做牺牲显存换取计算和延迟，成为实际推理系统的基本前提。

### 训练和生成为什么有不同的并行性

训练的输入形状可以看成 \(B\times S\times D\)：\(B\) 是 batch，\(S\) 是序列长度，\(D\) 是 hidden dimension。大量 token 同时经过同一组权重，矩阵乘法的复用非常好。

Decode 时，每个请求通常只新增一个 token。虽然可以把多个请求拼成 batch，但每个请求都有自己的历史和自己的 KV cache；权重可以复用，cache 却不能像权重一样被所有请求直接共享。这正是后面“增大 batch 能否救回效率”这个问题的关键。

## 3. Arithmetic intensity：为什么 Decode 容易 memory-bound

### 先用一个矩阵乘法看瓶颈

设输入 \(X\in\mathbb{R}^{B\times D}\)，权重 \(W\in\mathbb{R}^{D\times F}\)，输出为 \(Y=XW\)。如果使用 bf16，每个元素占 2 bytes，则：

$$
\text{FLOPs}=2BDF
$$

$$
\text{HBM bytes}=2BD+2DF+2BF
$$

Arithmetic intensity 定义为单位内存搬运对应的计算量：

$$
I=\frac{2BDF}{2BD+2DF+2BF}
$$

在 \(B\ll D,F\) 时，权重项 \(DF\) 占主要部分，于是 \(I\approx B\)。也就是说，增大 batch 可以让同一份权重被更多样本复用，提升计算强度；batch 很小时，GPU 大量时间花在从 HBM 读权重上。

以 H100 为例，粗略的计算峰值除以显存带宽约为 \(295\) FLOPs/byte。只有当工作负载的 arithmetic intensity 超过这个拐点，才有机会成为 compute-bound。\(B=1\) 的矩阵向量乘法强度大约只有 1，显然属于 memory-bound：读完一整块权重，却只做相对少量的计算。

### MLP：batch 可以帮忙，但 Decode 的 \(T=1\) 很尴尬

对 Transformer MLP 的三个主要矩阵乘法做同样的估算。令 \(T\) 表示本轮要处理的 token 数，则：

$$
\text{FLOPs}_{\text{MLP}}=6BTDF
$$

$$
\text{HBM bytes}_{\text{MLP}}=4BTD+4BTF+6DF
$$

当 \(BT\ll D,F\) 时，arithmetic intensity 近似为：

$$
I_{\text{MLP}}\approx BT
$$

Prefill 中 \(T=S\)，长 prompt 和较大的 batch 可以让 \(BT\) 足够大，所以 MLP 比较容易吃满计算单元。Decode 中每个请求每轮只产生一个 token，即 \(T=1\)，强度退化成约 \(B\)，只能依靠并发请求来弥补。

### Attention：Decode 时 batch 也救不了太多

设 \(S\) 是已经存在的历史 token 数，\(T\) 是本轮新生成的 token 数。只看 FlashAttention 中主要的矩阵乘法，有：

$$
\text{FLOPs}_{\text{attn}}=4BSTD
$$

$$
\text{HBM bytes}_{\text{attn}}=4BSD+4BTD
$$

于是：

$$
I_{\text{attn}}=\frac{ST}{S+T}
$$

Prefill 时 \(T=S\)，所以 \(I_{\text{attn}}=S/2\)，长 prompt 能够带来较高的计算强度；Decode 时 \(T=1\)，则：

$$
I_{\text{attn}}=\frac{S}{S+1}<1
$$

这里没有 \(B\)。原因是不同请求拥有不同的 KV cache，batch 不能像 MLP 那样让所有样本反复复用同一份 attention 输入。于是可以得到整堂课最重要的性能结论：

- Prefill 往往偏 compute-bound，Decode 往往偏 memory-bound。
- Prefill 的 MLP 强度约为 \(BS\)，Decode 的 MLP 强度约为 \(B\)。
- Prefill 的 attention 强度约为 \(S/2\)，Decode 的 attention 强度小于 1，增大 batch 也无法从根本上改变它。

### 从内存账估算 latency 和 throughput

可以把 Decode 的每一步再粗略地写成一笔内存账。令 \(V\) 是词表大小，\(N\) 是 query head 数，\(K\) 是 KV head 数，\(H\) 是 head dimension，\(L\) 是层数，则参数量近似为

$$
P=2VD+3DFL+(2DNH+2DKH)L.
$$

bf16 下参数本身占 \(2P\) bytes；长度为 \(S\) 的单条序列，其 K/V cache 占

$$
M_{\text{KV,seq}}=4SKHL
$$

bytes。并发 batch 为 \(B\) 时，总显存读写量可以先近似成

$$
M(B)=2P+B\cdot4SKHL.
$$

如果假设计算和通信可以完美重叠，并忽略 kernel、调度和通信开销，显存带宽为 \(W\)，则单 token latency 约为 \(M(B)/W\)，并发吞吐约为

$$
\text{throughput}(B)\approx\frac{B}{M(B)/W}.
$$

这组公式把 batch 的 trade-off 写得很清楚：batch 增大时，权重读取被更多请求摊薄，所以 throughput 上升；但 KV cache 按 \(B\) 增长，所以单请求 latency 变差，最终还会遇到显存上限。

用课件中的 Llama 2 13B + H100 粗算：\(S=1024\)、\(D=5120\)、\(F=13824\)、\(N=K=40\)、\(H=128\)、\(L=40\)、\(V=32000\)，H100 显存带宽取 \(3.35\) TB/s、显存取 80 GB。参数约 13.0B，bf16 参数约 26.0 GB，单条序列 KV cache 约 0.84 GB。理想模型下，\(B=1\) 占约 26.9 GB，\(B=64\) 占约 79.7 GB，\(B=256\) 则需要约 240.8 GB，已经无法放进一张 H100。这个例子说明“大 batch 提高吞吐”不是无限成立的：KV cache 会先把显存吃满。

## 4. KV cache：先从模型结构减少搬运量

### 从 MHA 到 GQA/MQA

标准 Multi-Head Attention（MHA）为每一个 query head 配一组 key/value head。设 query head 数为 \(N\)，KV head 数为 \(K\)，head dimension 为 \(H\)，则 KV cache 的规模与 \(K\times H\times L\) 成正比，其中 \(L\) 是层数。

- MHA：\(K=N\)，每个 query head 都有自己的 KV。
- MQA：\(K=1\)，所有 query head 共享一组 KV。
- GQA：\(1<K<N\)，把 query head 分成若干组，每组共享一组 KV。

GQA 把 cache 大小减少约 \(N/K\) 倍。因为推理是 memory-bound，减少需要读写的 cache 不只是省显存，还可能降低延迟并允许更大的 batch。代价是 KV 表达能力下降，需要通过训练和评测确认 accuracy 没有明显损失。

### MLA：把 KV 压成 latent

GQA 仍然直接保存若干组完整的 key/value。Multi-head Latent Attention（MLA）进一步把 hidden state 压缩成低维 latent vector，只保存压缩后的表示，在需要计算 attention 时再投影出 K/V：

$$
c=W_c h,\qquad K=W_K c,\qquad V=W_V c
$$

原始课件用 DeepSeek 的例子说明了这个量级变化：完整 KV 表示的维度可以从 \(N\times H=16384\) 压到约 \(C=512\)，再为 RoPE 额外保留一小段维度。核心不是某个具体数字，而是把“每层、每个 token 都要保存的状态”变成更紧凑的 latent。

![MLA 将 KV 表示压缩为 latent，再在计算时恢复](/learning/cs336/lectures/l10-mla-schema.png)

### 跨层共享与局部注意力

还有两类思路：

- **Cross-Layer Attention（CLA）**：让相邻层共享 KV，利用层间的冗余减少 cache，而不只是在 head 维度共享。
- **Local/Sliding-window Attention**：每层只关注最近一段上下文，使 cache 不再随着整条序列无限增长。多层叠加后，信息仍然可以逐层传播到更远位置。

局部注意力的风险是丢掉远距离依赖，因此实践中常把局部层和全局层交错使用。它体现了一个通用的 trade-off：为了服务效率主动限制上下文，并用模型结构把被丢掉的信息影响控制在可接受范围内。

![Sliding-window attention 只读取局部上下文](/learning/cs336/lectures/l10-longformer-attention.png)

更激进的长上下文方案会继续压缩或筛选历史信息。原始课件用 DeepSeek v4 attention 作为例子：它面向约 1M context，先用 **Compressed Sparse Attention（CSA）** 把一段 token 压缩成更短的表示，再用 **DeepSeek Sparse Attention（DSA）** 选择最相关的 top-k；**Heavily Compressed Attention（HCA）** 则进一步提高压缩率。它们都在回答同一个问题：当完整 KV cache 随上下文长度线性增长时，哪些历史值得保留，哪些可以低成本近似。

![DeepSeek v4 attention 中对长上下文的压缩与稀疏化思路](/learning/cs336/lectures/l10-deepseek-v4-attention.png)

从复盘角度看，这一节的共同目标可以统一成一句话：**既然 Decode 的主要成本是搬运 KV，就要减少 KV 的维度、精度、长度，或者让多个请求共享它。**

## 5. 有损的捷径：量化、剪枝与蒸馏

### 量化：用更少的 bit 表示数字

推理常用 bf16，每个参数占 2 bytes。若把权重或 activation 降到 fp8、int8、int4，显存占用和带宽压力都会下降；在 memory-bound 场景中，这有机会直接换来更高吞吐和更低延迟。但精度损失不能被忽略，量化的核心就是在“少搬数据”和“保留模型行为”之间找平衡。

最基本的 affine quantization 可以写成：

$$
q=\operatorname{round}(x/s)+z,\qquad \hat{x}=(q-z)s
$$

其中 \(s\) 是 scale，\(z\) 是 zero-point，\(q\) 是低精度整数，\(\hat{x}\) 是反量化后的近似值。实际方法还要决定按 tensor、channel 还是 group 统计 scale，以及哪些中间值需要保留更高精度。

量化大致分两类：

- **Quantization-aware training（QAT）**：训练过程中模拟量化误差，让模型主动适应低精度，但需要承担完整训练成本。
- **Post-training quantization（PTQ）**：训练完成后用校准数据估计 scale 和误差，成本低得多，适合已经训练好的模型。

PTQ 中还有 GPTQ 这类逐层方法：用校准数据估计量化误差，并借助近似的二阶信息调整尚未量化的权重，把误差从重要方向转移到相对不敏感的方向。AWQ 的侧重点则是用 activation 找出需要被保护的权重，两者都是在低 bit 下尽量保留原模型行为，但误差补偿的依据不同。

AWQ 的直觉是 activation 中存在少数幅值很大的 channel，它们命中的权重更重要，因此不能平均地对所有权重做同样激进的压缩。根据 activation 找出这部分敏感权重，给它们更多精度，其余权重则使用更低 bit。

![AWQ 根据 activation 的重要性保护少量敏感权重](/learning/cs336/lectures/l10-awq-schema.png)

### 剪枝与蒸馏：删掉结构，再把行为补回来

剪枝不只是把权重置零，而是识别并删除不重要的 layer、head 或 hidden dimension，得到一个真正更小的模型。典型流程是：

1. 用一小批 calibration data 估计不同结构单元的重要性。
2. 删除不重要的层、头或维度，形成更快的 student model。
3. 用原始模型作为 teacher 做 distillation，修复剪枝带来的行为损失。

因此，剪枝本身只负责降低计算和内存成本，蒸馏负责把 accuracy 拉回来。它和 GQA/MLA 的差别在于：后者主要改变 attention 的 cache 结构，剪枝则直接缩小模型本体；两者也可以叠加。

剪枝的结果不能只看“删掉了多少参数”，还要看删掉的是不是硬件真正能跳过的结构，以及蒸馏后质量是否恢复。原始课件的结果图采用 calibration data 识别重要的 layer、head 和 hidden dimension，再把被剪模型交给 teacher 修复；这也是为什么结构化剪枝通常比任意稀疏 mask 更容易转化为真实加速。

![结构化剪枝后用 teacher distillation 修复模型行为](/learning/cs336/lectures/l10-pruning-kd.png)

## 6. 无损的捷径：Speculative Decoding

### 为什么“验证”比“生成”便宜

Prefill 可以并行处理一串 token，属于更容易利用矩阵乘法的阶段；Decode 每次只生成一个 token，反复读大模型权重。于是可以让一个便宜的小模型先猜几个 token，再让大模型一次性检查这串候选。

设 draft model 的分布为 \(p\)，target model 的分布为 \(q\)：

1. draft model 自回归地产生一小段候选，例如 4 个 token。
2. target model 并行计算这段候选每个位置的概率。
3. 对第 \(i\) 个候选，以概率 \(\min(1,q(x_i)/p(x_i))\) 接受它。
4. 遇到拒绝时，从残差分布重新采样；即使整段候选都被接受，也要从 target 分布继续采样一个新 token。

![Speculative sampling 的候选、验证和接受过程](/learning/cs336/lectures/l10-speculative-sampling-algorithm.png)

### 为什么它仍然是 target model 的精确采样

接受概率会抵消 draft model 过度采样的部分。以二元 vocabulary \(\{A,B\}\) 为例，假设 \(p(A)>q(A)\)，则 draft 对 A 采样过多，对 B 采样不足。拒绝 A 后，残差分布会把概率质量补回 B：

$$
P(A)=p(A)\frac{q(A)}{p(A)}=q(A)
$$

$$
P(B)=p(B)+p(A)\left(1-\frac{q(A)}{p(A)}\right)=q(B)
$$

因此，理想情况下 speculative sampling 的最终样本分布与直接从 target model 采样完全一致；它改变的是计算路径，不是目标分布。现实收益取决于 draft model 是否足够快、候选是否足够容易被接受，以及 target model 的并行验证能否摊薄固定成本。

### Draft model 也可以继续优化

一个简单的 draft model 可以是同系列的小模型，也可以专门蒸馏出来。Medusa 让 target model 顶部增加多个 prediction heads，同时提出多个未来 token；EAGLE 则利用 target model 的高层特征构造更强的 draft。它们的共同方向是提高候选长度和接受率，同时不重新承担一次完整的大模型自回归生成。

![Medusa 与 EAGLE 都在改进 speculative decoding 的 draft 路径](/learning/cs336/lectures/l10-medusa-eagle.png)

## 7. Dynamic Workload：Continuous Batching

### 静态 batch 为什么不适合在线生成

训练数据通常可以整理成规则的 \(B\times S\times H\) 张量；在线请求却有三个动态性：到达时间不同、生成长度不同、prompt 前缀可能相同。

如果采用静态 batch，系统必须等一批请求都准备好，并让短请求等长请求；某个请求生成结束后，它占用的 batch 位置也可能只能被 padding 填满。这样既增加等待，又浪费计算。

### Iteration-level scheduling

Continuous batching 的做法是把调度粒度从“一整个请求”缩短到“一次 decode iteration”：

- 每轮只为当前仍在生成的请求执行一步。
- 新请求准备好后，可以在下一轮加入，而不必等当前 batch 全部结束。
- 已经完成的请求立刻退出，把位置和资源让给其他请求。

这样做需要把 attention 和非 attention 计算分开处理。不同请求的 KV cache 长度不同，attention 不能简单地堆成一个规则矩阵；而 MLP 等部分可以把各请求当前的 token 拼接成一个更大的二维张量，继续使用高效的批量矩阵乘法。

Continuous batching 解决了“什么时候把哪些请求放在一起”的问题，但还没有解决“不同长度的 KV cache 如何放进显存”。后一个问题正是 PagedAttention 的入口。

## 8. PagedAttention：把操作系统的分页搬到 KV cache

### 预分配为什么会浪费显存

传统做法往往在请求开始时，按最大可能长度为 prompt 和 response 预留一整段连续 KV cache。实际生成通常不会达到最大长度，于是尾部产生大量内部碎片；不同请求之间还可能因为长度不同留下外部碎片。

![连续预分配导致 KV cache 碎片和浪费](/learning/cs336/lectures/l10-paged-attention-fragmentation.png)

PagedAttention 借鉴操作系统的虚拟内存：把一条请求的 KV cache 切成固定大小的 block，逻辑上的连续 token 不要求对应物理显存连续。请求增长时按需申请 block，结束时按 block 回收。attention kernel 根据 block table 找到需要读取的物理位置。

因此，“一条请求的 KV cache 是一块连续大张量”只是逻辑视图，不是物理布局要求。block table 把逻辑 token 范围映射到不连续的物理 block，最后一个 block 没有填满也只浪费一个小块，而不是浪费按最大长度预留的整段空间。

![PagedAttention 将逻辑上的连续 KV cache 映射到物理 blocks](/learning/cs336/lectures/l10-paged-attention-blocks.png)

### Prefix sharing 与 copy-on-write

如果多个请求共享 system prompt，或者同一个 prompt 需要采样多条候选答案，它们的前缀 KV cache 可以只保存一份。不同请求共享前缀 block；一旦某个请求要写入不同内容，再在 block 级别做 copy-on-write。

![多个请求通过共享前缀减少重复的 KV cache](/learning/cs336/lectures/l10-paged-attention-sharing.png)

这让系统同时获得三种收益：显存碎片减少、cache 可以按需增长、重复前缀无需重复计算和保存。它也解释了为什么 serving 系统需要像内存管理器一样管理 KV cache，而不是把 cache 当作一个普通的张量变量。

## 9. 从模型到系统：一张推理优化地图

把 Lecture 10 的技巧放在一起，可以得到三层优化：

### 模型层：减少每一步必须保存和读取的状态

GQA、MQA、MLA、CLA、局部注意力降低 KV cache 的维度、层数或有效长度；量化降低参数和 cache 的字节数；剪枝与蒸馏直接缩小模型计算图。它们大多需要在 accuracy 和效率之间做设计取舍。

### 算法层：减少大模型自回归调用次数

Speculative decoding 用小模型提出候选，让大模型并行验证；只要接受率足够高，就能用一次 target forward 产出多个 token，同时保持 target distribution 的正确性。这是“改变执行路径但不改变结果分布”的典型系统算法。

### Serving 层：让动态请求尽可能共享硬件

Continuous batching 负责动态调度，PagedAttention 负责动态分配显存，prefix sharing 负责复用重复上下文，kernel fusion 和 CUDA Graphs 则降低 kernel launch 等固定开销。它们共同解决的是：同一个大模型如何在真实、稀疏、长度不齐的请求流上保持高利用率。

这一层次也能和前面的课程串起来：

- Lecture 2 的 Transformer 计算图告诉我们权重、attention 和 KV cache 分别在哪里产生。
- Lecture 3 的并行与通信视角提醒我们，真正的瓶颈可能是数据搬运而不是 FLOPs。
- Lecture 4 的训练系统重点是把规则的训练 batch 扩展到多设备；Lecture 10 则面对在线推理的不规则 batch 和动态显存。
- Lecture 9 的 scaling 讨论模型、数据和训练预算；本讲进一步追问模型训练完成后，如何把每一次生成的边际成本降下来。

最后可以把整个推理系统压缩成五个问题：

1. 当前阶段是 prefill 还是 decode？
2. 这一层的 arithmetic intensity 是否低于硬件拐点？
3. 需要保存多少 KV cache，能否压缩、量化或共享？
4. 能否让小模型先猜、大模型批量验证？
5. 动态请求如何调度，KV cache 如何按需分配？

## 面试复盘

### 需要熟练写出的公式

1. 矩阵乘法 \(X_{B\times D}W_{D\times F}\) 的 FLOPs 是 \(2BDF\)，bf16 下的内存搬运量是 \(2BD+2DF+2BF\)。
2. MLP 的推理强度近似为 \(I_{\text{MLP}}\approx BT\)；Decode 时 \(T=1\)，主要依赖 batch。
3. Attention 的强度是 \(I_{\text{attn}}=ST/(S+T)\)；Decode 时 \(T=1\)，小于 1 且不随 batch 增长。
4. GQA 把 KV head 从 \(N\) 降到 \(K\)，KV cache 大约缩小 \(N/K\) 倍。
5. Speculative sampling 的接受概率是 \(\min(1,q(x)/p(x))\)，拒绝后的残差采样保证最终分布仍然是 \(q\)。

### 常见追问

- 为什么推理通常比训练更 memory-bound？因为 Decode 每轮只生成极少 token，却必须读取庞大的权重和历史 KV cache。
- 为什么增大 batch 能提高 MLP 吞吐，却不能根治 attention Decode？MLP 权重在请求间共享，KV cache 则基本按请求独立。
- TTFT 主要由哪个阶段决定？Prefill；而 inter-token latency 主要由 Decode 决定。
- Continuous batching 与 PagedAttention 分别解决什么问题？前者解决请求级动态调度，后者解决不规则 KV cache 的显存分配和共享。
- PagedAttention 为什么像操作系统分页？逻辑 token 序列和物理显存 block 解耦，可以按需分配、回收和共享。
- 量化、剪枝和 speculative decoding 的区别是什么？前两者通常牺牲或修复模型表示能力来降低单步成本，后者通过改变采样执行路径减少 target model 的调用次数。

### 一句话总结

推理优化的核心不是单纯追求更多 FLOPs，而是围绕动态请求流，减少每一步需要搬运的参数和 KV cache，并尽量让一次昂贵的 target 计算服务更多有效 token。
