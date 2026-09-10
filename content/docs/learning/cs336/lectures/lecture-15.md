---
title: "L15 · SFT / RLHF"
weight: 15
date: 2026-08-29
updated: 2026-09-10
course: "CS336"
topics: ["CS336", "sft", "rlhf", "preference optimization"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture15/
---

前十四讲主要在回答：怎样训练出一个能力足够强的 base model？Lecture 15 把问题往产品侧推了一步：一个很会预测下一个 token 的模型，为什么还不是一个好用的 assistant？

预训练优化的是互联网文本上的 next-token likelihood：

$$
\mathcal L_{\text{PT}}
=-\mathbb E_{x\sim p_{\text{web}}}
\sum_t\log p_\theta(x_t\mid x_{<t}).
$$

用户却希望模型理解意图、遵守格式、拒绝危险请求、调用工具并在多个候选答案中选择更好的一个。于是这堂课围绕两种训练关系展开：

$$
\boxed{\text{SFT = imitation}\qquad\text{RLHF = optimization}}
$$

整讲的基本路径是：

$$
\text{Pretraining}
\rightarrow
\text{SFT}
\rightarrow
\text{Preference Data}
\rightarrow
\text{Reward Model / PPO}
\rightarrow
\text{DPO}
\rightarrow
\text{Overoptimization}.
$$

![SFT、Preference Data、Reward Model 与 PPO 组成的经典后训练流水线](/learning/cs336/lectures/l15-slide-06-06.png)

## 1. 从 Base Model 到 Assistant：后训练到底改变什么

### Capability 和 Control 不是一回事

base model 学到的是“在类似上下文后面，人类通常会写什么”。用户需要的却是“按照我的目标完成任务”。同一个 prompt，如果直接交给 base model，它可能继续生成论坛讨论、广告或问题复述；assistant 则应该直接给出符合任务约束的回答。

因此可以把预训练和后训练的职责暂时分开：

- **Pretraining** 建立知识、语言能力、代码能力和各种潜在技能。
- **Post-training** 决定什么场景下调用哪些技能，以及输出应该遵守什么形式和边界。

这也是为什么小得多的 instruct model 可能在人类偏好评测上胜过更大的 base model：改变的主要不是世界知识总量，而是模型对用户意图的控制方式。

### 三个阶段为什么要分开

经典 InstructGPT 路线把后训练拆成三步：

1. **SFT**：收集 demonstration，让模型模仿人类或高质量 teacher 的回答。
2. **Reward Model**：对同一个 prompt 的多个回答做排序，把“哪个更好”变成可计算的 reward。
3. **RLHF**：把语言模型当作 policy，用 reward model 指导它生成更高 reward 的回答，同时限制它不要偏离参考模型太远。

课件还强调一个现实限制：后训练资料通常比预训练资料稀疏得多。早期 RLHF 工作会公开标注指南、数据结构和训练细节；现代系统的高质量 preference data、过滤规则和完整 recipe 往往没有同等程度的公开记录。所以复盘时要区分“课件讲清楚的数学机制”和“工业系统里仍然不透明的具体配方”。

## 2. SFT：换数据分布，而不是换一种 loss

### SFT 的目标

给定 prompt 或对话历史 $x$，以及示范回答 $y$，SFT 仍然使用 teacher forcing：

$$
\mathcal L_{\text{SFT}}
=-\mathbb E_{(x,y)}
\sum_t m_t\log p_\theta(y_t\mid x,y_{<t}).
$$

其中 $m_t$ 是 loss mask。常见做法是只让 assistant token 参与 loss，把 user token 的 $m_t$ 设为 0；也有 recipe 会预测整段对话或混合使用不同 mask。是否 mask prompt 不是 SFT 的本质定义，更可靠的判断标准是数据分布、反馈形式和训练目的。

预训练和 SFT 的计算形式都可以是 next-token prediction，真正变化的是样本来自哪里：

- 预训练数据是网页、书籍、代码和百科文本。
- SFT 数据是 `user → ideal assistant`、`assistant → tool call`、`tool result → next action` 等结构化轨迹。

所以 SFT 的作用可以写成 behavior cloning：

$$
p_\theta(y\mid x)\approx p^*(y\mid x),
$$

其中 $p^*$ 是示范数据体现的行为分布。对梯度来说，事实内容、回答长度、语气、Markdown、引用格式、拒绝方式、工具调用和 JSON schema 都只是 token；模型不会自动知道哪些 token 属于“知识”，哪些 token 属于“风格”。

### Instruction data 如何演化

课件用一条数据演化线说明 SFT 目标如何变化：

$$
\text{FLAN}
\rightarrow
\text{Self-Instruct / Alpaca}
\rightarrow
\text{ShareGPT / Vicuna}
\rightarrow
\text{OpenAssistant}
\rightarrow
\text{WizardLM / Tulu3 / Nemotron}
\rightarrow
\text{Tool-use trajectories}.
$$

FLAN 把分类、问答、翻译、摘要和推理等 benchmark 改写成自然语言 instruction，适合提升任务泛化，但仍然像一个 benchmark solver。Self-Instruct 用少量人工 seed 让强模型生成更多 instruction-response pairs，再过滤重复和垃圾；Alpaca 把这种合成数据路线推广得很广。

ShareGPT、Vicuna 和 OpenAssistant 则让数据更像真实对话。随着数据继续演化，三个变化会直接进入模型行为：**chattiness、detail、tool use**。如果训练集里的回答普遍很长，模型就可能把“好答案”理解成先总结、列很多点、举多个例子再重复总结；这不是神秘的模型性格，而是 maximum likelihood 对训练分布的忠实复制。

![从 FLAN 到工具调用轨迹，SFT 数据逐渐接近真实使用](/learning/cs336/lectures/l15-slide-09-09.png)

### Agent SFT 不再只是 Text → Text

现代 agentic SFT 样本可能长这样：

```text
User
  ↓
Assistant analysis / action
  ↓
Tool call JSON
  ↓
Tool result
  ↓
Assistant next action
  ↓
Final response
```

其中 role、tool name、arguments、JSON 格式、todo 结构和最终回答都可以成为 next-token supervision。一个 coding agent 为什么会先列计划、读取文件、运行测试，再根据失败日志修改代码？一个直接的解释是：这类轨迹已经进入 SFT data，模型学到的是整段行为序列，而不只是最终答案。

## 3. SFT 的边界：抽取能力、Safety 与 Midtraining

### SFT 更像 elicitation，而不是从零创造能力

预训练已经让模型接触过解释、总结、写代码、翻译、礼貌对话和拒绝等模式。SFT 通常不是重新发明这些能力，而是在告诉模型：面对某类用户请求，应该进入哪一种行为模式。

这解释了为什么少量高质量 demonstration 也可能带来很大的行为变化。它们不需要覆盖模型所有知识，只需要把已有的 latent skill library 路由到更合适的输出形式。SFT 的主要作用可以概括成：

$$
\boxed{\text{从已有能力中抽取并稳定一种可用行为}}
$$

### 少量 safety data 也能改变行为

课件用约 500 条 Alpaca-style safety examples 说明：少量针对性数据就能显著提高模型遵守安全指南的概率。合理的解释不是“500 条数据教会了模型完整伦理学”，而是模型原本已经具备解释、拒绝和遵守指令的语言能力，SFT 只是提高了

$$
p_\theta(\text{safe refusal}\mid\text{harmful prompt}).
$$

但 safety tuning 不能简化成“拒绝越多越好”。如果所有请求都拒绝，violation rate 可能下降，benign request 的 false refusal rate 却会接近 100%。真正要调的是 harmful response 与错误拒绝之间的 decision boundary。

![少量 safety data 也能显著改变模型的行为倾向](/learning/cs336/lectures/l15-slide-26-26.png)

### 知识注入为什么容易和回答行为混在一起

如果对模型反复训练一条“某篇论文由 Alice 等人写作”的样本，模型可能更容易输出这句话。但它同时学到的也可能是：看到 `References:` 就生成作者、年份、期刊和页码的格式。

因此 SFT 既可能提高事实回忆，也可能只是在提高某种回答模板的概率。对于尾部知识，简单地增加 factual SFT 不一定让模型更可靠，甚至可能把错误事实和引用样式一起固化。课件的结论是：知识存储、知识提取和回答行为在语言模型里并没有干净的边界。

### Midtraining：把 instruction data 放回较长的训练主干

当 instruction data 很少而预训练语料很多时，直接在末尾做一小轮 SFT 可能造成明显的分布切换或能力遗忘。一种常见做法是：

1. 继续用大规模预训练数据训练。
2. 在其中混入一部分 instruction、conversation、reasoning 或 tool-use data。
3. 最后再做一个较短但目标明确的 instruction-tuning round。

这就是课件中 midtraining / two-phase training 的位置：它把 instruction data 从“最后才出现的一小段数据”变成训练后半程的一部分，同时保留最后一轮 SFT 对行为格式的精确控制。

![将 instruction data 混入预训练主干，再做短的 SFT 收尾](/learning/cs336/lectures/l15-slide-29-29.png)

## 4. Preference Data：从“示范答案”变成“比较结果”

### 为什么 demonstration 不够

SFT 要求人或 teacher 写出一个完整答案，但人往往能判断两个答案哪个更好，却不会亲自写出自己偏好的完整答案。这就是课件提到的 generation-versus-evaluation gap：喜欢的回答不一定是人类自己会写出的回答。

对同一个 prompt $x$，可以让当前模型生成多个回答：

$$
y_1,y_2,\ldots,y_k.
$$

标注者只需要选择 preferred response $y_w$ 和 rejected response $y_l$，形成：

$$
(x,y_w,y_l).
$$

这类 pairwise preference 没有告诉模型一个绝对分数，却告诉了它一个局部排序关系。

### 标注不是一个无偏的 oracle

高质量 preference data 的难点不只是多找一些人。需要同时考虑：

- 标注指南是否明确，尤其是 helpfulness、correctness、safety 和 style 冲突时如何排序；
- 标注者是否真的检查了事实，而不是只根据长度和表达流畅度判断；
- 报酬、专业背景、地区和人口统计分布是否改变了偏好；
- 标注者是否借助了其他模型，或直接复制模型给出的判断；
- 不同 prompt 类型是否需要不同的评价标准。

课件还提醒，response length 对人类和 GPT-based evaluator 都可能产生很强影响。一个更长、更详细、更像“认真回答”的输出，可能在偏好数据里占优势，即使它没有提供更多正确内容。若 reward model 学到这个捷径，后面的 RL 就会把长度继续放大。

![同一 prompt 生成多个回答，再由标注者进行排序](/learning/cs336/lectures/l15-slide-36-36.png)

### 人类反馈、AI feedback 与 self-training

实际系统可能混合使用人工 pairwise feedback、规则检查、强模型反馈和 Constitutional AI 风格的自训练。AI feedback 可以扩大规模，但不能自动消除偏差：如果 evaluator 本身偏好长答案、固定语气或某种格式，reward model 会把这些偏好继续放大。

所以 preference data 的价值不只取决于数量，还取决于它是否覆盖真正影响产品质量的行为，以及 chosen/rejected 的差异是否能被模型学到。

## 5. Reward Model：把排序关系变成可优化的分数

### Bradley-Terry 目标

Reward Model 接收 prompt 和一个回答，输出标量：

$$
r_\phi(x,y).
$$

对于 chosen response $y_w$ 和 rejected response $y_l$，Bradley-Terry 模型把偏好概率写成：

$$
P(y_w\succ y_l\mid x)
=\sigma\left(r_\phi(x,y_w)-r_\phi(x,y_l)\right).
$$

训练目标是最大化正确排序的概率，等价地最小化：

$$
\mathcal L_{\text{RM}}
=-\mathbb E_{(x,y_w,y_l)}
\left[
\log\sigma\left(r_\phi(x,y_w)-r_\phi(x,y_l)\right)
\right].
$$

这里真正被监督的是 reward difference，而不是某个绝对分数。对同一个 prompt 给 chosen 和 rejected 的 reward 同时加上任意常数，排序概率不变；因此 reward 的绝对零点没有可识别意义。

### Reward Model 只是 proxy

Reward Model 只看过有限的 prompt、回答和标注规则。它给出的分数不是人类价值本身，而是一个可被 policy 优化的 proxy。只要模型找到某个容易被 reward model 识别、但没有真正提升回答质量的特征，RL 就可能把这个特征放大。

长度是最直观的 proxy hack：如果训练数据中长答案更常被选中，reward model 可能把 token 数当成质量信号。policy 于是学会输出更长、更密集的回答，reward 上升，但人类偏好未必继续上升。

## 6. PPO：在 reward 上优化，但不要让 policy 跑飞

### 从 policy gradient 开始

把语言模型看成 policy：

$$
\pi_\theta(y\mid x).
$$

目标是让模型生成的回答获得更高 reward：

$$
\max_\theta\mathbb E_{y\sim\pi_\theta(\cdot\mid x)}[R(x,y)].
$$

最基本的 policy-gradient identity 是：

$$
\nabla_\theta\mathbb E_{y\sim\pi_\theta}[R(y)]
=\mathbb E_{y\sim\pi_\theta}
\left[R(y)\nabla_\theta\log\pi_\theta(y)\right].
$$

问题是 reward 的方差很高。一个回答拿到高分，不代表其中每个 token 都值得提高概率；如果直接用完整 reward 乘上整条序列的 log-probability，更新会很不稳定。

### Advantage、Reference Model 与 KL

Baseline 或 value function 用来估计“在当前状态下通常能拿多少分”，于是把 reward 改成 advantage：

$$
A_t=R_t-V(s_t).
$$

正 advantage 的 action 增加概率，负 advantage 的 action 降低概率。实际 RLHF 还要加入 reference model 的 KL 惩罚：

$$
R_{\text{total}}
=R_{\text{RM}}
-\beta\,\mathrm{KL}\left(\pi_\theta(\cdot\mid x)\,\|\,\pi_{\text{ref}}(\cdot\mid x)\right).
$$

reference 通常是 SFT model 的冻结副本。它有两个作用：防止 policy 为了 reward 彻底偏离原来的语言能力，也让 policy 不容易离开 reward model 训练数据覆盖的区域。KL 不是装饰项，而是 RLHF 目标中控制分布漂移的主要杠杆。

### PPO 的 clipped ratio

PPO 不直接允许 policy 一步改变太多，而是用 old policy 和 new policy 的概率比：

$$
r_t(\theta)
=\frac{\pi_\theta(a_t\mid s_t)}
{\pi_{\text{old}}(a_t\mid s_t)}.
$$

典型 clipped objective 是：

$$
L^{\text{CLIP}}(\theta)
=\mathbb E_t\left[
\min\left(
r_t(\theta)A_t,
\operatorname{clip}(r_t(\theta),1-\epsilon,1+\epsilon)A_t
\right)
\right].
$$

当 advantage 为正时，ratio 增长到一定程度后不再继续获得收益；当 advantage 为负时，也限制一次更新把概率压得过低。PPO 因此可以看成 policy gradient、trust region 直觉和 clipping 的组合。

![Policy gradient、TRPO 和 PPO clipping 的关系](/learning/cs336/lectures/l15-slide-53-53.png)

PPO 之所以麻烦，是因为它需要 on-policy rollout、reference model、reward model、value model、advantage estimation 和多轮更新。它的优势是直接优化可测 reward，代价是训练循环长、样本和超参数都昂贵。

## 7. DPO：从 KL-regularized RL 直接得到 preference loss

### 先写清楚 RLHF 的约束目标

忽略实现细节，KL-regularized RL 的目标可以写成：

$$
\max_\pi
\mathbb E_{y\sim\pi(\cdot\mid x)}[r(x,y)]
-\beta\,\mathrm{KL}\left(\pi(\cdot\mid x)\,\|\,\pi_{\text{ref}}(\cdot\mid x)\right).
$$

在对 policy 不作参数化限制的理想条件下，最优 policy 具有闭式形式：

$$
\pi_r(y\mid x)
=\frac{1}{Z(x)}\pi_{\text{ref}}(y\mid x)
\exp\left(\frac{r(x,y)}{\beta}\right).
$$

反解 reward：

$$
r(x,y)
=\beta\log\frac{\pi_r(y\mid x)}{\pi_{\text{ref}}(y\mid x)}
+\beta\log Z(x).
$$

对于同一个 prompt 的 chosen 和 rejected，$\log Z(x)$ 会在 reward difference 中抵消。把这个隐式 reward 代回 Bradley-Terry preference objective，并用当前 policy $\pi_\theta$ 代替 $\pi_r$，得到 DPO loss：

$$
\mathcal L_{\text{DPO}}
=-\mathbb E_{(x,y_w,y_l)}
\left[
\log\sigma\left(
\beta\left[
\log\frac{\pi_\theta(y_w\mid x)}{\pi_{\text{ref}}(y_w\mid x)}
-\log\frac{\pi_\theta(y_l\mid x)}{\pi_{\text{ref}}(y_l\mid x)}
\right]
\right)
\right].
$$

![DPO 从隐式 reward 推出 preference loss](/learning/cs336/lectures/l15-slide-57-57.png)

### 这个 loss 在更新什么

DPO 会提高 chosen 相对 reference 的 log-probability，同时降低 rejected 相对 reference 的 log-probability；更新强度由当前隐式 reward 预测得是否正确决定。reference model 不能被删掉，因为 DPO 需要用它定义“相对偏离了多少”。

DPO 的工程吸引力在于：它不需要单独训练显式 Reward Model，也不需要 PPO 的 on-policy rollout 和 outer loop，直接在已有 preference pairs 上做 supervised-style gradient update。但它仍然需要高质量 preference data，也仍然受 reference、beta、数据分布和长度偏置影响。

### PPO 与 DPO 的关系

- PPO 显式生成 rollout，用 reward model 打分，再通过 policy optimization 更新。
- DPO 把 KL-regularized RL 的最优 policy 代回 preference loss，直接用 chosen/rejected pairs 更新 policy。
- PPO 更接近“在线探索并优化 reward”，DPO 更接近“离线拟合偏好关系”。

这不是“DPO 永远优于 PPO”。课件里也强调，结果高度依赖数据、reward、reference、训练步数和评测方式。SimPO、length-normalized DPO 等变体，正是针对 reference 依赖或长度偏置继续做的修改。

## 8. RLHF 的副作用：Reward 越高，模型不一定越好

### Reward overoptimization 与 Goodhart's Law

当 policy 不断优化 proxy reward，常见曲线是：早期 reward 和人类偏好一起上升；超过某个点后，reward 继续上升，但真实偏好下降。原因是 policy 开始利用 reward model 的漏洞，而不是改善任务本身。

这个现象可以出现在人类 preference、带噪声的 LM preference 上；如果 evaluator 完全无噪声，曲线可能看起来更稳定，但这并不代表真实世界就没有 proxy mismatch。评估必须同时看 reward、独立的人类或模型评测、任务正确性和安全指标。

![Reward overoptimization：proxy reward 继续上升并不代表真实偏好继续上升](/learning/cs336/lectures/l15-slide-63-63.png)

### Mode collapse 与 calibration

RLHF 还可能降低输出分布的多样性。模型不再像一个保留多种可能性的 probabilistic model，而更倾向于集中到一批高 reward 的回答模式。这样做可能让偏好分数上升，却损害探索能力、长尾问题覆盖和概率 calibration。

因此 post-training 评估不能只看一条平均 preference score，还要观察：

- 输出长度是否异常增长；
- 不同 prompt 下的 entropy 和 diversity 是否塌缩；
- 模型的 confidence 与真实正确率是否匹配；
- benign request 的拒绝率是否上升；
- reward 提升是否能在独立评测中复现。

![RLHF 可能损害概率 calibration，并让输出分布发生塌缩](/learning/cs336/lectures/l15-slide-64-64.png)

### 三种训练目标的区别

把整讲放在一起：

| 阶段 | 训练对象 | 直接优化的东西 | 典型风险 |
| --- | --- | --- | --- |
| Pretraining | 网页、代码、书籍等 token | next-token likelihood | 不知道用户意图和产品边界 |
| SFT | demonstration / trajectory | 模仿示范行为 | 复制长度、风格、事实和格式偏差 |
| RLHF / preference optimization | chosen/rejected pairs 与 reward | 偏好或 proxy reward | reward hacking、mode collapse、calibration 变差 |

这个区分也解释了为什么 SFT 和 RLHF 不是简单的“多训几轮”：SFT 更接近 distribution matching，RLHF 更接近在已有分布附近做 mode seeking 和目标优化。

## 9. 课程串联：从 Synthetic Data 到 RLVR

Lecture 14 讨论 synthetic data，Lecture 15 讨论如何把这些数据变成 behavior、preference 和 reward；Lecture 16 接着进入 RLVR，把可验证的结果直接用作 reward。三讲可以这样连接：

- Synthetic data 解决“从哪里获得更多训练样本”。
- SFT 解决“如何模仿一条给定的高质量行为轨迹”。
- Preference optimization 解决“当没有唯一标准答案时，如何利用排序反馈”。
- RLVR 解决“当答案可以程序化验证时，如何减少对主观 reward model 的依赖”。

实际的 post-training pipeline 往往不是一条只走一次的直线，而是会在 SFT、preference data、reward evaluation 和 error analysis 之间反复迭代。数据决定模型看到什么行为，reward 决定模型被鼓励什么行为，独立评测则负责检查模型有没有学会钻评分器的空子。

如果只保留四条公式，应该是：

1. SFT：

   $$
   \mathcal L_{\text{SFT}}=-\sum_t m_t\log p_\theta(y_t\mid x,y_{<t}).
   $$

2. Reward Model：

   $$
   \mathcal L_{\text{RM}}=-\log\sigma(r_w-r_l).
   $$

3. KL-regularized RL：

   $$
   \max_\pi\mathbb E_\pi[r]-\beta\,\mathrm{KL}(\pi\|\pi_{\text{ref}}).
   $$

4. DPO：

   $$
   -\log\sigma\left(\beta\left[
   \log\frac{\pi_\theta(y_w\mid x)}{\pi_{\text{ref}}(y_w\mid x)}
   -\log\frac{\pi_\theta(y_l\mid x)}{\pi_{\text{ref}}(y_l\mid x)}
   \right]\right).
   $$

## 面试复盘

### 必须能讲清楚的机制

- 为什么 SFT loss 和 pretraining loss 看起来一样，却能带来很大行为变化？因为改变的是数据分布和训练目标，不是 next-token loss 的形式。
- 为什么 SFT 不是可靠的知识注入方法？因为事实、引用格式、回答模板和语气共同进入梯度，模型未必学会可泛化的事实检索。
- 为什么 preference pair 比完整 demonstration 更容易收集？人通常更容易比较两个回答，而不一定能写出自己偏好的完整答案。
- Reward Model 为什么使用 $r_w-r_l$？因为 pairwise preference 只识别相对分数，同一个 prompt 下的加性常数会抵消。
- PPO 的 baseline、advantage 和 clipping 分别解决什么问题？baseline 降低方差，advantage 区分 action 是否优于当前预期，clipping 限制单次 policy update 的幅度。
- KL reference 为什么不能随便删？它限制 policy 偏离 SFT 分布，降低语言能力崩坏和 reward-model 分布外 exploit 的风险。
- DPO 为什么可以不训练显式 Reward Model？它从 KL-regularized RL 的最优 policy 反解隐式 reward，再把 reward difference 写成 policy 与 reference 的 log-probability difference。
- 为什么 reward 一直升不能证明模型一直变好？reward model 是 proxy，policy 可能在优化评分器漏洞，出现长度 hack、reward overoptimization 或 mode collapse。

### 一句话总结

Lecture 15 的重点不是背住 SFT、PPO 和 DPO 的缩写，而是看清三种监督的差别：预训练提供能力，SFT 指定行为，preference optimization 进一步选择行为；每增加一层控制，也增加一层 proxy、分布偏移和评估风险。
