---
title: "L16 · RLVR"
weight: 16
date: 2026-08-29
updated: 2026-09-10
course: "CS336"
topics: ["CS336", "rlvr", "reasoning", "grpo"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture16/
---

Lecture 15 讨论的是 RLHF：用人类偏好或 learned reward model 让模型更符合人的期待。Lecture 16 把 reward 换成了另一类信号：如果一个任务的结果可以自动检查，就直接把检查结果拿来训练。

$$
\boxed{\text{RLVR = Reinforcement Learning with Verifiable Rewards}}
$$

整讲可以沿着这条线复盘：

$$
\text{RLHF 的 proxy reward 问题}
\rightarrow
\text{PPO}
\rightarrow
\text{GRPO}
\rightarrow
\text{GRPO 的偏差}
\rightarrow
\text{R1 / Kimi / Qwen3}
\rightarrow
\text{test-time scaling}.
$$

![Lecture 16 的两条主线：PPO 到 GRPO，以及 R1、Kimi 1.5、Qwen3 案例](/learning/cs336/lectures/l16-slide-04-04.png)

## 1. RLVR：把模糊偏好换成可执行的检查

### 为什么 RLHF 难以无限放大

RLHF 的目标是最大化真实的人类满意度，但实际训练通常只能得到一个有限数据上拟合出来的 reward model：

$$
\max_\theta
\mathbb E_{y\sim\pi_\theta(\cdot\mid x)}
[\hat R_\phi(x,y)].
$$

当 policy 优化得不够深时，\(\hat R_\phi\) 可以作为真实偏好的近似；继续优化后，policy 可能开始寻找 reward model 的漏洞。Lecture 15 讲的 reward overoptimization、长度 hack、mode collapse 和 calibration degradation，都会限制 RLHF 的可扩展性。

RLVR 选择一类更窄、但 reward 更可靠的任务：数学答案可以和 ground truth 比较，代码可以编译并运行测试，形式化证明可以交给 proof checker，游戏或工具环境可以返回明确的成功状态。

### Outcome reward 与 format reward

例如题目是：

```text
Solve x^2 - 5x + 6 = 0.
```

模型可以生成很长的 reasoning，最后输出答案。验证器只需要检查最终答案是否等于 \(2,3\)：

$$
R_{\text{accuracy}}
=\mathbf 1[\text{answer is correct}].
$$

还可以加一个格式奖励，要求 reasoning 放进 `<think>...</think>`，答案放在规定位置：

$$
R=R_{\text{accuracy}}+R_{\text{format}}.
$$

这种 reward 通常是稀疏的，甚至只有 0/1，但它不需要另训一个神经网络去猜“人类可能喜欢什么”。模型最终要优化的就是可执行的任务结果。

### Verifiable 不等于 perfectly specified

验证器仍然是一个 specification。`predicted_answer == ground_truth` 可能被多答案输出、解析漏洞或格式边界绕过；代码测试覆盖不全时，能通过测试也不代表程序真的正确。

Multiple choice 也有类似问题：四选一随机猜中就有 25% 的正奖励，即使模型没有完成 reasoning。自由答案题的随机命中率通常更低，因此更适合提供有区分度的 outcome signal。

所以 RLVR 的准确说法是：它把 learned fuzzy proxy 换成了通常更可靠的 executable proxy，而不是消除了 reward hacking。

## 2. 从 PPO 到 GRPO：为什么可以去掉 Value Model

### PPO 在语言模型上的实际成本

语言模型是 policy，生成的 token 是 action，整条回答或 trajectory 最后得到 reward。最基本的 policy-gradient identity 是：

$$
\nabla_\theta\mathbb E_{y\sim\pi_\theta}[R(y)]
=
\mathbb E_{y\sim\pi_\theta}
\left[R(y)\nabla_\theta\log\pi_\theta(y)\right].
$$

为了降低方差，PPO 通常还需要 value model 估计 baseline，计算 advantage，再使用 old policy 与 new policy 的 ratio 和 clipping：

$$
\rho_t(\theta)
=\frac{\pi_\theta(a_t\mid s_t)}
{\pi_{\text{old}}(a_t\mid s_t)}.
$$

$$
L_{\text{PPO}}
=\mathbb E_t\left[
\min\left(
\rho_t A_t,
\operatorname{clip}(\rho_t,1-\epsilon,1+\epsilon)A_t
\right)
\right].
$$

在 RLHF 中还要加入 reference policy 的 KL penalty。实际系统因此包含 rollout、policy、reference model、reward model、value model、advantage estimation 和多轮 inner-loop update。value model 占显存，还需要额外调参；on-policy rollout 又让训练吞吐受到推理速度限制。

### Group Relative Policy Optimization

GRPO 的关键观察是：同一个 prompt 可以一次采样一组回答，而不是只采样一个。设组大小为 \(G\)，得到回答和 reward：

$$
(y_1,r_1),(y_2,r_2),\ldots,(y_G,r_G).
$$

先在组内计算均值和标准差：

$$
\mu_G=\frac1G\sum_{i=1}^G r_i,
\qquad
\sigma_G=\operatorname{std}(r_1,\ldots,r_G).
$$

再用组内相对位置构造 advantage：

$$
\hat A_i=\frac{r_i-\mu_G}{\sigma_G+\varepsilon}.
$$

最简单的 GRPO 可以理解成：保留 PPO 的 importance ratio、clipping 和 KL regularization，但删除独立的 value model，把同一道题的其他 rollout 当作 relative baseline。

$$
L_{\text{GRPO}}
\approx
\mathbb E\left[
\frac1G\sum_i\frac1{|y_i|}\sum_t
\min\left(
\rho_{i,t}\hat A_i,
\operatorname{clip}(\rho_{i,t},1-\epsilon,1+\epsilon)\hat A_i
\right)
-\beta D_{\text{KL}}(\pi_\theta\|\pi_{\text{ref}})
\right].
$$

这就是 GRPO 的工程吸引力：不再训练一个和 policy 接近大小的 critic，代码和显存占用都更简单。

![GRPO 用同一 prompt 的 group rewards 做归一化 advantage](/learning/cs336/lectures/l16-slide-18-18.png)

### 一个具体的 group baseline

如果一组 8 个回答的 binary reward 是

$$
[1,0,0,1,0,0,0,0],
$$

那么 \(\mu_G=0.25\)。不做标准差归一化时，正确回答得到 \(1-0.25=0.75\)，错误回答得到 \(0-0.25=-0.25\)。同一个 prompt 提供了一个局部 counterfactual：回答都面对同一道题，差别主要来自各自的 reasoning trajectory。

不过，组内 z-score 只是一个相对归一化方法，不是对任意状态都无偏的 value baseline。后续工作和 Dr. GRPO 等变体正是从这个角度分析标准 GRPO 的统计偏差。

## 3. GRPO 的两个偏差：难度加权与长度偏置

### Standard deviation 会改变题目权重

当 reward 是 binary 时，某组的正确比例为 \(p\)：

$$
\mu=p,
\qquad
\sigma=\sqrt{p(1-p)}.
$$

正确回答的 normalized advantage 约为

$$
\hat A_{+}=\frac{1-p}{\sqrt{p(1-p)}},
$$

错误回答的 normalized advantage 约为

$$
\hat A_{-}=\frac{-p}{\sqrt{p(1-p)}}.
$$

这意味着非常容易或非常困难的题目可能因为组内标准差而获得不同权重。若所有 rollout 都正确或都错误，组内没有区分度，\(\sigma\) 接近零，加入稳定项只能避免数值爆炸，不能凭空创造学习信号。

### Response length normalization

许多 GRPO 实现还会把 response-level loss 除以输出长度。这个选择会产生不对称的 bias：对于正 advantage，较短的正确回答每个 token 得到更大的梯度；对于负 advantage，较长的错误回答受到的平均惩罚可能更小。

于是标准 objective 可能同时鼓励“正确答案更短”和“错误答案更长”。这提供了一个谨慎解读 R1-Zero 长 CoT 现象的理由：训练中 response 变长，不一定全部来自模型自己发现了更深的 reasoning，也可能有 objective 和 normalization 的作用。

![GRPO 的长度偏置会同时改变 reward、正确答案长度和错误答案长度](/learning/cs336/lectures/l16-slide-24-24.png)

GRPO 的结论因此不是“删掉 critic 就万事大吉”，而是：它用很低的系统成本换来了一个适合大规模 rollout 的 baseline，但 advantage normalizer、length normalization、importance ratio 和 KL 都会改变训练行为。

## 4. DeepSeek-R1：Outcome RL 如何长出 reasoning

### R1-Zero：Base Model 直接接 GRPO

R1-Zero 的 controlled setting 可以概括为：

$$
\text{DeepSeek-V3-Base}
\rightarrow
\text{GRPO}.
$$

它没有先做 long-CoT SFT，主要依靠两类 reward：

- **Accuracy reward**：数学最终答案是否正确，代码是否通过测试。
- **Format reward**：是否按照规定的 thinking tag 和答案格式输出。

课件用结果表说明它的 reasoning 能力很强，但也指出了明显副作用：CoT 变长、语言混杂、格式不稳定、可读性下降。verifier 只关心答案是否正确，不会因为“这段英文夹中文、读起来很别扭”而扣分。

![R1-Zero 用 accuracy reward 和 format reward 直接训练 reasoning](/learning/cs336/lectures/l16-slide-28-28.png)

### R1 为什么又加入 SFT

真正的 DeepSeek-R1 不再坚持纯 RL，而是把 SFT 和 RL 分工：

```text
DeepSeek-V3
    ↓
Cold-start long-CoT SFT
    ↓
Reasoning RL with GRPO
    ↓
Rejection sampling + SFT
    ↓
General RL / alignment
```

冷启动 SFT 提供一批较可读、格式稳定、语言一致的 long-CoT behavior prior；RLVR 在这个分布附近搜索更高成功率的 reasoning strategy；随后用成功轨迹继续 SFT，并在不可验证任务或一般对齐目标上加入更广的 RL。课件提到的量级是数千条 cold-start reasoning data，之后约 600k reasoning examples 和约 200k non-reasoning examples 用于进一步 SFT，具体配方仍应以原始报告为准。

这可以浓缩成两句话：

$$
\boxed{\text{SFT = teach the language of reasoning}}
$$

$$
\boxed{\text{RLVR = optimize reasoning for success}}
$$

![R1 将 DeepSeek-V3、reasoning SFT、GRPO 和后续 SFT/RLHF 串成完整 pipeline](/learning/cs336/lectures/l16-slide-31-31.png)

### 为什么不用 Process Reward Model 和 MCTS

Process Reward Model 看起来更适合 credit assignment：每个中间步骤都可以得到 reward，而不是等最终答案。但“一个 reasoning step”很难定义，中间步骤是否正确也很难自动判断；人工标注不能无限扩展，neural PRM 还会重新引入 reward hacking。

MCTS 在棋类任务中依赖明确的 state/action 和有限的搜索空间；自然语言 reasoning 的节点边界不清楚，每个 prefix 后面都有巨大的 token continuation space，还需要可靠的 value model。它可以帮助 inference-time search，却很难直接变成稳定、便宜的 self-improving training loop。

因此 R1 的经验不是“PRM 和 MCTS 永远没用”，而是：在这套大规模实验里，简单的 sampling + outcome reward + GRPO 更容易扩展。

### Distillation：发现和继承可以分开

R1 生成的大量成功轨迹可以写成

$$
(x,\text{CoT},y).
$$

对小模型重新用 0/1 reward 探索出同样的轨迹，成功概率可能很低；直接对强模型产生的 reasoning traces 做 SFT distillation，通常更省计算。课件还强调，32B 级模型从强 R1 traces distill，可能比自己从 base model 做大规模 R1-Zero 式 RL 更好。

所以可以把规模角色分开：frontier model 用 RL 发现可行的 reasoning strategy，小模型用 distillation 继承已经发现的 trajectory。

## 5. Kimi k1.5：把 context length 变成 RL scaling 轴

### Reasoning tokens 也是 compute budget

Kimi k1.5 与 R1 同期，但给出了一个更明确的视角：模型大小、训练 token 之外，reasoning context length 也是 scaling axis。可用的 reasoning context 增大到约 128K 后，困难任务仍可能继续改善。

于是出现新的计算取舍：

$$
\text{Model FLOPs per token}
\times
\text{Reasoning tokens}.
$$

可以选择“大模型 × 短思考”，也可以选择“小模型 × 长思考”。小模型如果学会更有效地使用长 CoT，性能可以追近更大的模型，但大模型通常仍然更 token-efficient，且上限更高。

### 数据筛选、课程学习与长度控制

Kimi 的数据流程包含难度筛选：排除 multiple choice / true-false 等容易产生 false positive 的样本，只保留模型 best-of-8 仍然经常失败、但答案可验证的问题。训练过程中还可以根据 success rate 做 curriculum，减少已经完全学会的问题，把 rollout 预算放到当前最有学习价值的难题上。

Kimi 还使用 reference-based reward 和受 DPO 推导启发的 policy objective，并在后期加入 length reward：正确回答逐渐倾向更短，错误回答也被鼓励不要无限延长。长度控制不能一开始就强压，否则模型可能还没有学会 reasoning 就被迫停止；更合理的顺序是先获得 capability，再优化 efficiency。

![Kimi k1.5 使用 reference-based reward 和正则化 policy objective](/learning/cs336/lectures/l16-slide-42-42.png)

### RL 系统本身是瓶颈

RLVR 的循环是：

```text
current policy
    ↓
generate long rollouts
    ↓
verify
    ↓
compute group advantages
    ↓
update policy
    ↓
repeat
```

它和普通 SFT 的 fixed-data loop 不同：rollout 是慢速自回归推理，训练和 rollout 可能使用不同框架，长 CoT 又让 batch 长度非常不均匀。Kimi 讨论的 partial rollout、复用已有 trajectory prefix 和长上下文基础设施，说明 reasoning RL 的一半问题是算法，另一半是 inference systems。

## 6. Qwen3：把 thinking mode 变成产品控制面

### Thinking 与 non-thinking 融合

R1 风格模型遇到简单问候也可能生成很长 CoT，这会浪费推理成本。Qwen3 的思路是把 thinking 和 non-thinking 数据放进同一个模型，用特殊标记控制模式：

```text
<user>{query} /think<|im_end|>
<assistant><think>{thinking_content}</think>{response}
```

或者：

```text
<user>{query} /no_think<|im_end|>
<assistant><think></think>{response}
```

这样同一个模型可以根据 inference flag 选择是否展开 reasoning。

![Qwen3 用 thinking / no-thinking 数据和特殊标记控制 CoT 长度](/learning/cs336/lectures/l16-slide-52-52.png)

### Thinking budget 与 test-time scaling

Qwen3 还展示了一个产品化方向：对 reasoning token 设置预算。预算为 0 时更像快速回答；预算为 2K 时允许有限推理；困难问题则可以提供 16K 或更大的 budget。达到阈值后插入停止 thinking 的特殊序列，再根据已有 reasoning 生成 final answer。

于是目标从单纯最大化 accuracy 变成：

$$
\max \text{quality}
\qquad
\text{s.t. reasoning budget}.
$$

Qwen3 的 recipe 仍然沿用 long-CoT cold start、reasoning RL、thinking-mode fusion 和 general RL；课件还提到只用约 3995 个筛选后的样本做 GRPO，强调数据质量和难度筛选比盲目扩大问题数量更重要。

### 与前面课程的连接

Lecture 9 讨论训练时如何分配模型规模、数据量和 compute；Lecture 10 讨论每个 reasoning token 的 inference cost；Lecture 15 讨论 SFT、preference 和 RLHF；Lecture 16 再加上一条 test-time compute 轴：

$$
\text{Performance}
=f(N,D,C_{\text{RL}},C_{\text{test}}).
$$

模型训练完成后，系统仍然可以用更多 reasoning tokens 换取更高的正确率，但这会直接增加延迟、显存和服务成本。

## 7. Verifier、探索与 RLVR 的边界

### Verifier 仍然会被攻击

一个代码 verifier 只运行有限测试，模型可能学会针对测试样例；一个数学 parser 可能接受多个答案或被格式绕过；一个工具环境可能把“调用成功”误当成“任务完成”。因此：

$$
\boxed{\text{Verifiable}\neq\text{Perfectly specified}}
$$

RLVR 把 reward 变得更可解释，但没有消除 specification loophole。训练集中的 verifier 也要像模型一样做 adversarial testing、覆盖率检查和独立评测。

### RL 更擅长放大可发现的行为

如果模型对某道题采样的所有结果都是错误的：

$$
[0,0,0,0,0,0,0,0],
$$

那么 group mean 和每个 advantage 都没有方向性学习信号。RL 需要探索空间里至少偶尔出现成功 trajectory，才能提高它的概率。

这说明 RLVR 更擅长放大模型已经能够发现、但尚未稳定输出的行为，而不是从全错的初始模型中凭空创造高级知识。base model quality、math continued pretraining、cold-start SFT 和 distillation 因此仍然重要。

### 适合 RLVR 的任务边界

RLVR 特别适合数学、代码、形式化证明、游戏、工具环境和结构化任务；对于“写一篇真正有文学价值的小说”这类没有明确 objective verifier 的任务，仍然要回到人类反馈、AI feedback 或其他 learned proxy，并承担 Lecture 15 中的 reward overoptimization 风险。

## 8. RLVR 的系统成本：Rollout、长度与数据利用率

RLVR 的训练吞吐不只由 backward 决定，rollout 通常是更慢的部分。长短不一的 reasoning 会导致 padding 浪费、GPU 利用率下降和 batch 等待；切换 inference engine 与 training framework 还会产生权重同步和调度开销。

因此一个可用的 RLVR 系统通常需要同时优化：

- rollout worker 与 trainer 的权重同步；
- partial rollout 和 prefix reuse；
- 长度分桶、动态 batch 与 early stop；
- verifier 的并行执行和结果缓存；
- reward、advantage 与训练样本的 replay / filtering；
- reasoning token 预算和难度 curriculum。

![RLVR 系统由 rollout workers、trainer、reward models 和 replay buffer 组成](/learning/cs336/lectures/l16-slide-45-45.png)

这些问题与 Lecture 10 的 serving 系统直接相连：PagedAttention、continuous batching、KV cache 管理和高效 decode 并不是推理阶段的孤立优化，而是 reasoning RL 的基础设施。

## 9. 课程串联：从 RLHF 到可验证 reasoning

把 Lecture 15 和 Lecture 16 放在一起，可以得到一个清晰的选择框架：

| 训练方式 | reward 来源 | 适合场景 | 主要风险 |
| --- | --- | --- | --- |
| PPO-RLHF | learned reward model | 开放式偏好、风格、安全 | reward hacking、分布偏移、critic 成本 |
| DPO | chosen / rejected pairs | 离线偏好优化 | reference、数据偏差、长度偏置 |
| GRPO-RLVR | executable verifier | 数学、代码、证明、工具环境 | verifier hacking、稀疏 reward、长度 bias |

它们并不是互相替代的三个版本，而是对应不同的信息形态：

- 只有完整示范时，用 SFT 做 imitation。
- 只有相对偏好时，用 Reward Model、PPO 或 DPO。
- 有可靠 outcome verifier 时，用 RLVR 直接优化可检查结果。

最终的 reasoning pipeline 也不是“纯 RL 取代 SFT”：SFT 提供可读和可探索的初始分布，RLVR 放大成功策略，distillation 把 frontier model 的轨迹传给更小的模型，general RL 再处理不可验证的产品行为。

## 面试复盘

### 必须写出的公式

1. Policy gradient：

   $$
   \nabla_\theta\mathbb E[R]
   =\mathbb E[R\nabla_\theta\log\pi_\theta].
   $$

2. GRPO group advantage：

   $$
   \hat A_i=\frac{r_i-\mu_G}{\sigma_G+\varepsilon}.
   $$

3. PPO / GRPO importance ratio：

   $$
   \rho_{i,t}=\frac{\pi_\theta(y_{i,t}\mid s_{i,t})}
   {\pi_{\text{old}}(y_{i,t}\mid s_{i,t})}.
   $$

4. KL-regularized objective：

   $$
   \max_\pi\mathbb E_\pi[R]
   -\beta\,\mathrm{KL}(\pi\|\pi_{\text{ref}}).
   $$

### 常见追问

- RLVR 为什么比 RLHF 更不容易出现 reward overoptimization？因为 reward 直接来自 verifier，少了一层 learned reward model；但 verifier 仍可能有 specification loophole。
- Final-answer-only reward 为什么也能训练 reasoning？因为 policy gradient 可以把整条成功 trajectory 的正 advantage 传回生成它的 token，GRPO 又用同题失败样本提供相对 baseline。
- GRPO 为什么能删除 Value Model？同一 prompt 的多个 rollout 可以用组内 reward 估计 relative performance，代价是引入 group normalization 和 length bias。
- 为什么 R1-Zero 的 CoT 变长不能直接证明 RL 发明了更深 reasoning？base model 可能已经有 self-reflection，GRPO 的长度归一化也会改变不同长度 response 的梯度。
- 为什么 R1 仍然需要 cold-start SFT？SFT 提供可读、格式稳定、语言一致的 reasoning prior，降低模型从稀疏 0/1 reward 中盲目探索的成本。
- 为什么小模型更适合 distillation？强 teacher 已经提供成功 trajectory，小模型直接模仿比从全错或低成功率的探索空间中重新发现它便宜。
- Kimi k1.5 为什么把 context length 当作 scaling 轴？因为 reasoning tokens 本身是 test-time compute，增加可用上下文可能继续提高困难任务的成功率。
- Qwen3 的 thinking mode fusion 解决什么产品问题？让同一个模型在简单问题上快速回答，在复杂问题上按 budget 展开 reasoning。
- RLVR 能不能训练模型学会完全未知的高级知识？如果 rollout 全部失败，advantage 没有方向；RL 更适合放大可探索行为，而不是凭空创造缺失知识。

### 一句话总结

RLVR 的价值在于把“希望模型更聪明”变成“让可验证的成功轨迹概率变高”；GRPO 让这件事更省 critic 和显存，但 verifier 质量、rollout 系统、长度偏置和探索覆盖率决定了最终上限。
