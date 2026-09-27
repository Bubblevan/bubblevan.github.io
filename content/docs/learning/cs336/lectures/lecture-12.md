---
title: "L12 · Evaluation"
weight: 12
date: 2026-08-29
updated: 2026-09-16
course: "CS336"
topics: ["CS336", "evaluation", "benchmarks", "safety", "agents"]
aliases:
  - /blog/2026/2026-08-29-cs336-lecture12/
---

Lecture 12 是课程的一次关键转向。前面的内容主要回答“如何训练出更大、更快、更强的语言模型”，这一讲则追问：**我们凭什么说一个模型更强？** 在讨论下一阶段的数据和后训练之前，必须先定义希望模型表现出的行为，再把抽象目标转换成可测量的指标。

评价不是把 prompt 扔给模型、算一个分数这么简单。它首先要确定被测量的 construct：知识、推理、帮助性、安全性、真实工作能力，还是成本与延迟。不同 construct 对应不同数据、协议和评分方式，因此不存在一个脱离任务场景的“万能排行榜”。

## 1. Evaluation：把抽象目标变成可测量的指标

可以把评价过程写成：

$$
\text{abstract construct}
\longrightarrow
\text{observable behavior}
\longrightarrow
\text{concrete metric}
$$

“智能”或“好用”不能直接测量，只能通过数学题正确率、代码任务成功率、用户偏好、拒答率、工具调用成功率等 observable 来近似。metric 是 construct 的代理，不是 construct 本身；代理越窄，越容易被模型针对性优化，也越容易出现分数上涨但真实能力没有同步上涨的情况。

“模型好”也可以有多种含义：在知识 benchmark 上分数高、推理能力强、用户更喜欢回答、每百万 token 成本低、延迟低，或者真实用户愿意持续使用并付费。课程开头用模型排行榜、价格—能力图、Arena 偏好和使用量来说明这一点：它们都在评价模型，但回答的是不同问题。

![能力与成本的联合视角](/learning/cs336/lectures/l12-artificial-analysis-cost.png)

因此，一份可信的 evaluation contract 至少要写清楚：

| 项目 | 要回答的问题 |
| --- | --- |
| Construct | 到底想测知识、推理、帮助性、安全还是工作能力？ |
| Task 与 population | 测什么任务，代表哪些用户和场景？ |
| Protocol | prompt、工具、上下文、采样次数和停止条件是什么？ |
| Metric | 如何评分，是否有可复现的 ground truth？ |
| Budget | 允许多少 token、时间、工具调用和并发成本？ |
| Validity risks | 是否有污染、数据集缺陷、评委偏差或 verifier 漏洞？ |

## 2. Perplexity：最平滑的 intrinsic evaluation

语言模型是 token 序列上的概率分布 \(p(x)\)。对数据集 \(D\) 而言，perplexity 可以写成：

$$
\operatorname{PPL}(D)
=
\left(\frac{1}{p(D)}\right)^{1/|D|}
=
\exp\left(-\frac{1}{|D|}\sum_{i=1}^{|D|}\log p(x_i)\right)
$$

它衡量模型是否给数据中的真实 token 分配了较高概率。传统语言建模会在 train split 上优化 perplexity、在 test split 上评估，典型数据集包括 Penn Treebank、WikiText-103 和 One Billion Word Benchmark。GPT-2 则展示了另一种范式：在 WebText 上训练，在标准数据集上 zero-shot 测试，这属于 out-of-distribution evaluation。

![GPT-2 在不同数据集上的 perplexity](/learning/cs336/lectures/l12-gpt2-perplexity.png)

Perplexity 的价值在于它是连续、平滑、便于做 scaling law 的指标。若真实分布是 \(t\)，模型分布是 \(p\)，理想情况是 \(p=t\)，此时交叉熵达到熵 \(H(t)\) 的下界。这个观点解释了为什么“只要持续降低 perplexity，最终就会得到足够强的模型”曾经很有吸引力：模型学到更好的序列分布，理论上也会提升条件预测 \(p(\text{solution}\mid\text{problem})\)。

但 perplexity 也可能测得太宽。例如在句子“Stanford was founded in 1885”中，若我们只关心模型能否回答某个事实，普通 perplexity 会把所有 token 的预测误差都算进去。于是可以改用 conditional perplexity，只评价 response 在给定 prompt 后的概率：

$$
\operatorname{PPL}(y\mid x)
=
\exp\left(-\frac{1}{|y|}\sum_{t=1}^{|y|}\log p(y_t\mid x,y_{<t})\right)
$$

LAMBADA 的补全任务、HellaSwag 的句子续写，本质上都和 conditional probability 很接近，可以看成“戴着 benchmark 外壳的 perplexity”。这类 intrinsic metric 对模型开发仍然重要，但它未必能回答开放式对话、工具使用或真实工作是否成功。

## 3. Exam Benchmarks：可控、易评分，但容易饱和

考试题是很方便的 evaluation：题目领域和难度可控，答案通常明确，多选题也容易自动评分。MMLU 包含 57 个学科，覆盖数学、历史、法律和道德等主题；不过它的名字虽然是 Massive Multitask Language Understanding，实际更接近广泛知识测试，而不完全是语言理解。

当模型在旧 benchmark 上逐渐饱和，评价需要提高难度。MMLU-Pro 清理了部分 noisy 或过于简单的问题，把选项从 4 个扩展到 10 个，并允许 chain-of-thought；课程材料中提到，模型准确率相对 MMLU 会下降约 16%–33%，因此重新拉开了模型之间的差距。

![MMLU-Pro 的题目与难度方向](/learning/cs336/lectures/l12-mmlu-pro.png)

GPQA 进一步把问题交给领域专家设计：题目由 61 位博士承包者撰写，博士专家准确率约 65%，即使允许搜索，非专家约 34%，GPT-4 约 39%。Humanity's Last Exam 则包含约 2500 道多模态题，覆盖多个学科，并经过多阶段筛选和审阅。它们都在把“答对一道常识题”推进到 frontier difficulty。

这里有一个重要 trade-off：题目太容易，所有模型都接近满分，metric 没有区分度；题目太难，所有模型都接近随机，分数也无法解释。难度应该落在能区分候选模型、又不至于让误差完全由偶然性主导的区间。

考试 benchmark 的另一个限制是 realism。真实用户通常不会给模型一套多选题，而是提出开放式、含糊、有上下文的请求；考试分数可以说明某种能力存在，却不能直接说明模型能否完成真实工作。

## 4. Chat Benchmarks：开放式回答如何评分

开放式回答没有唯一字符串答案，评分会混合正确性、完整性、风格、礼貌和用户偏好。Chatbot Arena 的做法是：随机用户提交真实 prompt，系统让两个匿名模型回答，用户选择更好的一个，再由大量 pairwise comparison 拟合 Elo-style rating：

$$
P(A\text{ beats }B)
=
\frac{1}{1+10^{(\operatorname{ELO}_B-\operatorname{ELO}_A)/400}}
$$

![Chatbot Arena 的开放式比较示例](/learning/cs336/lectures/l12-arena-beets.png)

Arena 的优点是 prompt 来自真实使用，用户有动力提交真正想问的问题，而且可以动态加入新的模型和问题，不必为所有模型预先固定一套 prompt。缺点也很明显：用户群体不是随机样本，二元偏好会把 style 与 correctness 混在一起，用户未必有能力判断答案是否事实正确，还可能出现 sycophancy、长度偏好和位置偏差。

AlpacaEval 使用固定的约 805 条 instruction，让 GPT-4 preview 作为 judge，计算候选模型相对基线的 win rate。它暴露出一个典型问题：LLM judge 容易偏爱更长的回答，模型只要增加冗余解释就可能刷高分；AlpacaEval 2.0 因此用回归方法校正 length bias。WildBench 则从约 1M 条人机对话中抽取 1024 个例子，用 checklist 和 judge 共同评分，强调 rubric 对人类或模型评委都很重要。

![AlpacaEval 的榜单与比较结果](/learning/cs336/lectures/l12-alpacaeval-leaderboard.png)

开放式评价的基本原则是：尽量做 pairwise comparison 或 rubric-based scoring，不要把一个含糊的整体印象伪装成精确的绝对分数；同时要报告评委、样本来源、长度、位置和自偏好等潜在偏差。

## 5. Agent Benchmarks：评价模型实际上在评价整个系统

对话 benchmark 评价的是模型“说什么”，agent benchmark 评价的是模型“做什么”。更准确地说：

$$
\text{Agent}
=
\text{Language Model}
+
\text{Scaffold}
+
\text{Tools}
+
\text{Context/Budget}
$$

因此不能只报告一个 model score，而要明确 scaffold、工具、最大步数、上下文长度、执行时间和 token 预算。SWE-Bench 给定真实 codebase 和 issue，要求 agent 提交能通过测试的 patch；原始规模约 2294 个任务，覆盖 12 个 Python repository，unit tests 充当结果 verifier。

![SWE-Bench 的任务与评测流程](/learning/cs336/lectures/l12-swebench.png)

TerminalBench 把环境收敛为通用终端：第一版包含 229 个由 93 位贡献者众包的任务，Terminal-Bench 2.0 选出 89 个任务。CyBench 用 40 个 CTF 任务测试网络安全 agent，并可用 first-solve time 表示难度；MLEBench 则覆盖 75 个 Kaggle competition，要求 agent 处理数据、训练模型并提交结果。

![TerminalBench 的任务规模与结果](/learning/cs336/lectures/l12-terminal-bench.png)

这些任务比考试题更接近真实工作，但难度也来自更多因素：规划是否合理、工具接口是否稳定、上下文是否会丢失、是否能从失败中恢复、测试是否完整。一个 agent 通过测试，不一定代表它真的理解了问题；一个 agent 失败，也可能是 scaffold 或工具配置导致，而不是基础模型缺乏能力。

## 6. Reasoning：所谓“纯推理”并不纯

前面的任务都不同程度依赖语言和世界知识。ARC-AGI 试图把 reasoning 从知识记忆中分离出来：任务由小型网格组成，原则上人类可以解决，但每道任务都尽量独特，单纯记忆训练样本不能直接帮助作答。ARC-AGI-2 增加了更强的多步推理要求，ARC-AGI-3 又进一步转向交互式环境。

![ARC-AGI 上不同模型类型的结果](/learning/cs336/lectures/l12-arc-agi-results.png)

ARC 系列清楚展示了一个现象：普通预训练语言模型在这类任务上未必能显著推进，而带有专门 reasoning-time compute 的模型开始改善结果。但“pure reasoning”仍然不是绝对纯粹的概念，因为任务设计、视觉解析、规则归纳和人类可解性都在影响分数。更准确的说法是：它试图减少知识记忆的影响，而不是消除所有背景能力。

## 7. Safety Benchmarks：安全是上下文相关的系统属性

安全评价不能只问“模型是否拒绝”，还要问模型是否会产生伤害、帮助危险行为、泄露隐私、迎合错误观点，或在不同工具权限下造成真实后果。HarmBench 基于约 510 类违反法律或社会规范的 harmful behavior；AIR-Bench 则从监管框架和公司政策出发，组织成 314 个风险类别、5694 个 prompts。

越过拒答策略的 jailbreak 是另一类 evaluation。Greedy Coordinate Gradient（GCG）会自动优化一段 adversarial suffix，使模型绕过安全拒答；它还展示了从开源模型迁移到闭源模型的 transferability。

![GCG jailbreak 的示例](/learning/cs336/lectures/l12-gcg-examples.png)

安全没有一个跨国家、跨文化、跨部署环境都相同的标量答案。政治、法律、医疗、网络安全等领域的可接受边界不同；同一个 cyber agent 既可以用于入侵，也可以用于授权的 penetration testing，这就是 dual-use。安全 benchmark 因而必须明确 threat model、攻击者能力、可用工具、伤害定义和拒答之外的真实风险。

## 8. Realism：评价是否捕捉了真实世界使用

Ecological validity 关心的是：evaluation 与真实使用有多接近。GPQA 可以很难，却不代表医生、工程师或普通用户每天面对的工作；Chatbot Arena 有真实用户 prompt，却缺少对分布的严格控制。

GDPVal 直接面向工作任务，覆盖美国 GDP 前九大行业中的 44 个职业，任务由平均约 14 年经验的专业人士提供。MedHELM 不再只使用医学考试，而是收集来自 29 位临床医生的 121 个 clinical task。Clio 则用语言模型分析真实用户数据，提炼人们正在询问的主题与模式。

![GDPVal 的真实工作任务方向](/learning/cs336/lectures/l12-gdpval.png)

![Clio 对真实用户请求的聚合分析](/learning/cs336/lectures/l12-clio-table4.png)

Realism 与 privacy 经常冲突：越接近真实用户数据，越可能包含敏感信息；越彻底公开和标准化，越容易失去真实场景中的复杂性。好的现实性 benchmark 需要同时说明数据来源、去标识化方法、专家参与方式和可复现边界。

## 9. Validity：分数本身是否值得相信

Evaluation validity 比 leaderboard 排名更基础。第一类风险是 train-test contamination。基础模型训练数据接近整个互联网，而公开 benchmark 通常也是互联网的一部分：

$$
\text{training data}\approx\text{Internet},
\qquad
\text{public benchmark}\subset\text{Internet}
$$

因此模型可能是“见过答案”而不是“现场解决问题”。可以从四条路线减轻污染风险：

1. **从模型行为推断重叠。** 利用数据点的 exchangeability 等性质，寻找异常高置信度、记忆式输出或重复模式。
2. **改善报告规范。** 模型提供者应披露训练数据时间范围、可能重叠的数据源，并报告置信区间，而不是只报一个最高分。
3. **使用 fresh eval。** 通过持续抓取新网页、LiveCodeBench 或其他动态任务降低提前泄露风险；但时间戳本身也不完美，因为题目可能被复制。
4. **使用 private eval。** 公司内部 codebase、个人写作和从未公开的数据不容易被训练集覆盖，对实际采购与部署决策尤其有价值。

第二类风险是 dataset 与 verifier 质量。SWE-Bench 需要人工筛选形成 Verified 版本；更高质量的 Platinum benchmark 需要检查题目是否有歧义、答案是否正确、测试是否覆盖关键行为。agent benchmark 还可能因为测试不完整而被 trivial agent 通过，或者因为 reward loophole 产生 verifier hack，因此应检查完整 trace，而不能只看最终分数。

![从数据重叠中发现 contamination 的示意](/learning/cs336/lectures/l12-contamination-exchangeability.png)

Validity 还包括统计稳定性、题目难度分布、评委一致性、抽样偏差和错误条目比例。一个小数点后两位的榜单，如果没有这些信息，往往只是把不确定性包装成了精确数字。

## 10. Rules of the Game：你到底在评价 method、model 还是 system

预 foundation-model 时代，常见的是 method evaluation：固定数据、固定训练/测试划分、固定 compute budget，比较不同算法。今天的 model/system evaluation 往往允许完整 recipe 不同，比较最终产品，包括预训练数据、后训练、system prompt、工具和 agent scaffold。

这两类评价没有谁更“科学”，它们回答的问题不同：

| 评价对象 | 固定什么 | 适合回答 |
| --- | --- | --- |
| Method | 数据、预算、任务协议 | 哪个算法或训练方法更有效？ |
| Model | 主要比较模型能力 | 哪个模型更适合某种能力任务？ |
| System / Agent | 模型、scaffold、工具和预算的整体组合 | 用户最终应该采用哪套系统？ |

NanoGPT speedrun 是 method evaluation 的典型例子：固定数据和训练流程，比较达到指定 validation loss 所需的时间或计算量。它鼓励算法创新；而真实产品 benchmark 则更关心最终用户体验。

![NanoGPT speedrun 的方法评价视角](/learning/cs336/lectures/l12-karpathy-nanogpt-speedrun.png)

如果不把 rules of the game 写清楚，结论很容易混淆。例如“模型 A 的 SWE-Bench 分数更高”可能只是因为它有更长的 rollout、更强的工具、更大的上下文或更宽松的测试环境，而不是基础模型本身更强。评价报告必须把这些变量拆开或显式纳入系统定义。

## 11. 把 Evaluation 放回课程主线

可以用四个维度检查一项评价：

| 维度 | 核心问题 | 典型风险 |
| --- | --- | --- |
| Difficulty | 能否区分当前模型？ | 太容易饱和，太难接近随机 |
| Realism | 是否代表真实用户和工作？ | 场景脱离现实，或隐私不可控 |
| Validity | 分数是否真的支持结论？ | 污染、偏差、错误数据、verifier hack |
| Cost | 测一次是否负担得起？ | 长上下文、多轮 rollout、人工评分过贵 |

这些维度不是从 intrinsic metric 到 agent benchmark 的简单升级，而是互相牵制：考试题通常 ground truth 清楚但 realism 弱；Arena 更真实但 correctness 难验证；private workflow 更接近部署但难以复现。Evaluation 设计本质上是在这些约束之间做取舍。

从课程主线看，Lecture 9–11 讨论 scaling、数据和训练系统如何让模型变强；Lecture 12 先规定“什么行为值得优化”；接下来的 data 与 post-training 才能围绕这些目标选择数据、奖励和反馈。模型研发循环因此不是“训练完再跑排行榜”，而是：

$$
\text{目标}
\rightarrow
\text{Evaluation contract}
\rightarrow
\text{数据与训练}
\rightarrow
\text{部署反馈}
\rightarrow
\text{重新定义目标}
$$

## 面试复盘

1. **为什么不存在一个万能 benchmark？** 因为 knowledge、reasoning、helpfulness、safety、realism 和 cost 是不同 construct，单个 metric 只能覆盖其中一部分。

2. **Perplexity 测量什么？** 它测模型给数据集真实 token 分配概率的能力，连续、平滑，适合 scaling law，但不等于真实任务成功率。

3. **为什么 conditional perplexity 比普通 perplexity 更贴近问答？** 它只评价给定 prompt 后 response 的概率，避免把与目标无关的 prompt token 误计入。

4. **MMLU、MMLU-Pro、GPQA 的差异是什么？** 它们逐步提高题目难度与专家性；MMLU-Pro 通过清理和增加选项缓解饱和，GPQA 更强调博士级、搜索也难的问题。

5. **Chatbot Arena 的 Elo 分数有什么优点和限制？** 它利用真实用户的 pairwise preference，动态且不要求统一 prompt；但会混合 style 与 correctness，并受用户、位置、长度和 sycophancy 偏差影响。

6. **为什么 LLM judge 不能直接当作 ground truth？** judge 自身可能偏爱长答案、熟悉风格或特定模型，需要 rubric、校准、人工抽检和偏差分析。

7. **为什么 agent benchmark 评价的是 system 而不是裸模型？** 因为结果由模型、scaffold、工具、上下文和 rollout budget 共同决定，必须报告完整 protocol。

8. **为什么 benchmark 的 validity 可能被 contamination 破坏？** 公开题目可能已经进入互联网训练语料，模型高分可能来自记忆而不是现场泛化；应使用 fresh 或 private eval，并披露重叠风险。

9. **Difficulty、Realism、Validity 如何区分？** 难度关心区分度，现实性关心是否代表真实工作，有效性关心分数是否支持结论；一个 benchmark 可以很难但不真实，也可以很真实但难以可靠评分。

10. **Method evaluation 和 system evaluation 的规则为何必须分开？** 前者固定数据、预算和协议来比较算法，后者比较用户最终得到的整体系统；混在一起会把工具、数据、scaffold 和模型能力误归因给同一个对象。

如果只能记住一句话，那就是：**没有脱离问题、用户、工具和预算的“模型好”；只有对某个明确 construct 足够有效、现实、可验证且成本可接受的 evaluation。**
