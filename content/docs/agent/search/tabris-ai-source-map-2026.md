---
schema: bubblevan/v1
id: docs-agent-search-tabris-source-map-2026
content_kind: docs
title: Tabris 的 AI 研究情报源图谱（2026年6月—9月）
date: 2026-09-27
status: draft
visibility: public
summary: 基于作者主页近期 92 篇小红书笔记，整理研究主题、筛选与阅读方法、逐篇图集导读及来源追溯边界。
topics: [research-intelligence, source-discovery, deep-research, agent]
aliases: []
authors: [bubblevan]
---

# Tabris 的 AI 研究情报源图谱（2026年6月—9月）

> 这是一份基于公开笔记的来源地图，不是对每篇论文结论的独立复核。作者正文、评论区发言、图中页面与评论区 AI 摘要是不同证据，以下分别标注。

## 采集范围与证据状态

| 项目 | 当前结果 |
|---|---|
| 来源作者 | [tabris 🗝 的公开主页](https://www.xiaohongshu.com/user/profile/60a72ded000000000101de6e) |
| 时间范围 | 2026-06-21 至 2026-09-24 |
| 输入与去重 | 94 个分享链接，去重后 92 篇笔记；92 篇均有成功记录 |
| 笔记类型 | 44 篇 paper 推荐、39 篇 blog 推荐、7 篇 project 推荐、2 篇其他 |
| 图集 | 1,581 张主图全部下载成功，单篇 10–18 张，平均约 17.2 张 |
| 可见评论 | 62 篇有可见评论文字，共 23,317 字符；这 62 篇都显示评论受登录提示截断 |
| 直接文本链接 | 正文和可见评论中识别到 3 个 URL：1 个 GitHub、2 个 xhslink 短链 |
| “附件”提示 | 32 篇正文提到链接放在附件；当前页面快照没有记录这些附件目标地址 |

### 逐条采集来源

合并后的 92 条记录不是同一种浏览器会话：34 篇逐条标为 `anonymous_isolated_chrome`；另 58 篇来自较早的单篇读取结果，记录标为 `logged_in=true / used_user_profile=true`。这里的 `logged_in` 是读取时声明的会话状态，不是站点对登录状态的独立证明。汇总文件会被最近一次批次覆盖，不能代替逐条 provenance。

因此，这份内容汇总覆盖全部 92 篇，但不能宣称 92 篇全是在匿名会话里取得。没有保存 Cookie 或认证材料；原分享链接中的 `xsec_token` 没有写入本页。逐图索引保存在本地缓存 `.cache/xhs-extracted/image-source-index.jsonl`，每行把本地图文件名、图序号和规范化笔记链接对应起来。

图片文件完整下载不等于已逐张视觉阅读。当前直接视觉核对 127/1,581 张，其余 1,454 张尚未完成直接视觉审阅；已核对图按笔记来源和图序列于文末。没有调用专用 OCR 引擎。

## 作者的选源与阅读方法

以下是作者在公开笔记和可见回复里讲述的个人做法，不代表普遍最优策略：

1. **用推荐流训练信息源。** 一条路径是持续点赞符合兴趣的泛学术内容，让 X 推荐逐步贴近自己的口味；另一条路径是从高质量论文作者出发，沿作者时间线寻找研究者并递归关注。作者说明第二条见效快，但需要多轮筛选。
2. **混合多种发现入口。** 评论和正文提到 X 推荐、AlphaXiv 排名、导师/朋友推荐、研究者社交网络等。按作者说法，单独追踪作者不够可靠，因为许多作者只有少数几篇特别有价值的文章。
3. **把阅读分成筛选与深读。** 作者称自己只亲自读约 1/10–1/20、可能成为 seed paper 的论文，剩余部分交给 research agent；在另一条回复中，作者把每轮约 5–10 篇认真读的论文视为已经不少。
4. **用引用关系构造知识树。** 作者把论文组织为根（基础工作）、主干（重要进展）和分支（后续工作），并提到用 Obsidian、Claude Code、Feynman 式讲解与按需蒸馏整理研究脉络。
5. **强调筛选品味和表达质量。** 作者会标明“很推荐”“感兴趣可看”“看看就好”，经常偏好可读性、实验说明和可视化好的 blog；部分论文列表仅封面固定，其余顺序随机，不能把图序误读为排名。

## 主题地图

这 92 篇反映的是作者在四个月内持续更新的个人选源，而不是完整的 AI 领域综述。反复出现的主题包括：

- **模型训练与推理：** 预训练数据与质量、SFT、RL/GRPO、在线与反向蒸馏、测试时计算、推理模型、扩散语言模型、长上下文、稀疏注意力与架构设计。
- **Agent 与 Harness：** agentic RL、自我改进、自动研究、技能学习、长时程任务、代码 agent、工具调用、记忆、可观测性与 harness 评测。
- **评价与科学方法：** coding/SWE 与工具基准、benchmark 是否对应真实能力、算力预算公平性、复现和训练过程公开、失败分析及实验记录。
- **系统与基础设施：** GPU/TPU/AMD、KV cache、推理优化、并行训练、内核、数据管线、低成本实验与研究型工具。
- **多模态、世界模型与交叉学科：** 视频和语音模型、机器人、world models、AI4Math、生物/蛋白质/基因组、科学模拟和数学教育。
- **治理与社会影响：** AI safety、网络安全、开放权重、AI 与科研署名责任、劳动和 AI economy、模型风险及研究者立场。
- **学习资源和开源项目：** LLM/RL 课程、讲义、书籍、实践教程、开源模型与 agent 开发工具。

## 来源追溯说明

本次从页面文本和可见评论中只找到 3 个直接 URL，远不足以还原全部论文与博客地址。32 篇明确说链接放在“附件”，但当前保存的运行时快照只含笔记正文、图集和当前可见评论，没有附件目标字段。对明确写了“链接按序放在附件”的 [2026-07-28 blog 合集](https://www.xiaohongshu.com/explore/6a64e38b000000000c015bec) 进行匿名复查时，页面返回 `300031`，所以这次没有取得附件链接；这不能说明附件不存在。

可稳定追溯到的最小证据链是：**作者公开笔记 → 图集序号 → 作者对该图的文字说明 →（如果可见）评论补充**。图中可读的论文标题和 URL 应标为“图内线索”，不能自动等同于已验证的原始来源。评论区 `点点` 对部分图集生成了论文摘要/标题清单；它们是评论里的二手 AI 摘要，本页不把其中的实验结论当成已核验事实。

先行视觉样例来自 2026-06-21 的 paper 合集 [6a2fe53800000000080246c1](https://www.xiaohongshu.com/explore/6a2fe53800000000080246c1)：前三张分别展示 **RLCSD: Reinforcement Learning with Contrastive On-Policy Self-Distillation**（arXiv:2606.11709v1，图中可见 GitHub `THU-BPM/RLCSD`）、**Harness Updating Is Not Harness Benefit: Disentangling Evolution Capabilities in Self-Evolving LLM Agents**（arXiv:2605.30621v1）和 **On the Relationship Between Activation Outliers and Feature Death in Sparse Autoencoders**（arXiv:2605.31518v1）。这三张、作者点名图和顺序核对图的总数以文末逐图表为准。

### 可见评论里的来源与方法线索

- 一条作者回复直接指向 [awesome-on-policy-distillation](https://github.com/chrisliu298/awesome-on-policy-distillation)，作为查找 OPD 教师训练材料的入口。
- 作者提到用 X 推荐流扩充来源；从喜欢的研究者继续追踪其他研究者；也会参考 AlphaXiv、导师与朋友的推荐。作者说自己主要深读 seed paper，其余交给 research agent，并提及 academic research / PhD / AI research 类 skills，以及依据 S. Keshav 的 *How to Read a Paper* 和 CMU 11-785 recitation 制作的阅读 skill。
- 个别评论中的 `点点` 为图集生成论文摘要或逐图标题/作者清单。本索引把这些视为待核验的检索线索；它们不是作者正文，也没有因此得到原始论文链接。

目前识别到的评论区逐图标题清单，来自 2026-07-28 的 blog 合集评论，且该评论本身被页面截断：**SIGReg from First Principles**（Reza Bayat）；**Why I Left Google DeepMind**（Alex Turner / The Pond）；**AI Model Co-Design: Hardware-Friendly LLM Design**（NVIDIA Developer Technical Blog）；**A History of Large Language Models**；**Expanded SkillOpt Ablations, Skill-Aware Reflection, and SkillOpt-Sleep**；**RoboTTT: Context Scaling for Robot Policies**；**Observability tools agents want**（Pydantic）。这些标题及作者/站点信息均来自评论区 AI 摘要，需回到图中和原站确认。

## 逐篇笔记与图集索引

每条笔记保留作者自己的逐图说明；原链接统一成不含分享 token 的规范笔记 URL。图号来自正文提及，不作为排序或推荐等级。若作者只说“喜欢图 N”，其他图的来源名称仍需要从图片本身或附件补齐。

#### [2026-09-24 · 9月中下旬自觉不错的paper推荐合集第四期](https://www.xiaohongshu.com/explore/6aaffe610000000026023b58)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、大模型、机器学习、文献阅读、强化学习。
- 图号线索：3、7；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人比较喜欢图3和图7
- 评论区含 `点点` 生成的逐篇摘要/逐图标题线索，属于评论内容，需回原图和原站核实。

#### [2026-09-24 · 一期简简单单的blog分享](https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e)

- 图集：17 张；分类：`blog`；标签：大模型、深度学习、ai、人工智能、AI反常识howto。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1非常详细的一篇intro，感兴趣的不要错过；图2同名paper的blog，写得很清晰，同时个人很喜欢他们整体的颜色设计；图3 intro JustRL II，也就是critic-equipped GRPO；图4非常长，但总结起来就一句：If we act with the appropriate urgency, we can hold AI companies to a higher standard, reduce risks from loss of control, and even tilt attacker-defender balance in cybersecurity back towards defenders；图5对safety感兴趣的可以读；图6 looped transformer合集. 图7 DeepSeek V4.1 Flash的架构说明，可以一看；图8 intro ApprenticeBench；图9最好的GPT-6 Astra解析，不用加之一，推荐有空时看看；图10 Ziming Liu按照explicit和externalized将Auto-Research分为6条路线，感兴趣可以找来读；图11 intro Real-SWE，该benchmark Fable 5.1领先GPT-6 Astra；图12 intro FIRE3D. 图13内容非常好，也很硬核，阅读请做好心理准备，LLM Training Data is Nonergodic；图14总结，假设一切按照既定轨迹发展，有理由对ai economy充满信心；图15 Terence Tao他们的宣言，有人喜欢也有人不喜欢，个人在此不做评价；图16 coding is all you need自然夸张，作者捍卫world model的观点大部分Yann LeCun也讲过，但写的不错，感兴趣的可以找来读；图17非常好，CS 7150 at NEU的团队做了很多demo方便学生理解deep learning，非常好教学用资源.

#### [2026-09-23 · 9月中下旬自觉不错的paper推荐合集第三期](https://www.xiaohongshu.com/explore/6aaffdc00000000029011577)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、机器学习、大模型。
- 图号线索：1、8；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人比较喜欢图1，另外注意图8非常长，阅读请做好心理准备

#### [2026-09-23 · 自觉不错的blog分享](https://www.xiaohongshu.com/explore/6aafe7ea000000002800041f)

- 图集：18 张；分类：`blog`；标签：大模型、科研学习、深度学习、人工智能、强化学习、文献阅读。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1来自Elad Hazan，总结了近二十年OCO的发展轨迹，感兴趣的朋友不要错过；图2非常值得鼓励的有趣的喜欢的研究，对此我只能说请继续；图3 同名paper的blog，写得非常清晰且易于理解，个人认为感兴趣的话直接读blog就行；图4虽然这类文章不可避免地会标榜自己（顺便拉踩），但内容还是挺详实的，对ai infra感兴趣的朋友可以读；图5非常长，来自Mustafa Suleyman，感兴趣的可以找来读；图6结论里最重要的一句 despite the best efforts of alignment researchers, we are not good at anticipating which undesirable behaviors might lead to concerning real-world incidents. 图7 intro T1，卖相看着不错；图8在 Craftax 环境里用 PPO+LSTM训练agent的实战帖；图9 intro Atria Dawn Preview，看着很不错，非常好研究；图10 Percy Liang带了好头，现在mimo也在直播训练，非常好行为；图11很好的理解video model的角度，而且篇幅很短，推荐找来看；图12现象确实存在，我个人很鼓励ai research，但如果要发表的话，理解并能阐释自己的研究我觉得是最低程度的要求. 图13 DeepSeek-V4.1 Flash的解析，看看就好；图14 GPT-6 Astra在这方面出人意料的厉害；图15 intro CUDA Rust，nVidia还在继续完善生态；图16 post training当然是有效的；图17 GPT-6 Astra毫无意外地可以拓展到Embodied AI；图18 auto-autoresearch实战记录帖. 链接按序放在附件里，需要请自取~

#### [2026-09-22 · 看看最近两周有哪些有趣的paper第二期](https://www.xiaohongshu.com/explore/6aaffd0e00000000260237d3)

- 图集：18 张；分类：`paper`；标签：大模型、人工智能、学术论文、深度学习、科研学习。
- 图号线索：7、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人比较喜欢图7和图18

#### [2026-09-22 · 看看最近两周哪些blog值得分享第二期](https://www.xiaohongshu.com/explore/6aafde7700000000280364ae)

- 图集：18 张；分类：`blog`；标签：人工智能、大模型、深度学习、强化学习、科研学习、大语言模型、jev。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1到图3都是最近很火的Jev相关，我个人不算非常感冒，但是很鼓励不同思路的发展. 图1是一篇非常长的解析，在更多信息披露之前，这类的解析可以一看但不要很信；图2第二篇就是正式介绍，思路不新颖，实现方式比较巧妙，是否真具备革命性还有待进一步观察；图3 其他人按照RLCD训的，速度确实大幅度提升. 图4很有意思，感兴趣的可以找来读；图5 intro DeepMind Institute，目前的article看是挺有思想性；图6是Open-Source AI & Open Models Reading List from Nathan Lambert，对这些内容感兴趣的朋友不要错过. 图7正在持续更新中的dataset hub，伟大无需多言；图8是在推广自家的Megakernel，写得非常详尽，可以一看；图9写得很好；图10 efficient RL framework for running single-file LLM-generated JavaScript games，有多少研究意义不好说，但非常有意思不是吗；图11篇幅不短，所以作者很贴心地进行了总结Across model sizes and training durations, improvements to pre-training quality translated to robot performance；图12作者的观点和之前分享的Ben那篇差不多，都是强调数学的理解. 图13内容如标题所示；图14作者提出一个很有价值的问题，但是显然很好回答它还需要一段时间；图15 intro CausalSmith，很开心看到其他领域的朋友在做类似尝试；图16 intro ccamy-1.0；图17 intro RSIAgent，挺有意思的研究；图18 simulated fly circuit recognizes printed letters and numbers from PDF pixels，很有趣. 链接按序放在附件里，免费的，需要请大方自取~

#### [2026-09-21 · 看看最近两周有哪些有意思的paper第一期](https://www.xiaohongshu.com/explore/6aaffc600000000012035ed5)

- 图集：18 张；分类：`paper`；标签：大模型、科研学习、深度学习、文献阅读、强化学习。
- 图号线索：1、4、7、16；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1来自很喜欢的Yifan Zhang，他经常在x上分享一些很棒的观点，当然这篇研究也非常好，推荐感兴趣的找来看；图4图7图16也挺不错的.
- 评论区含 `点点` 生成的逐篇摘要/逐图标题线索，属于评论内容，需回原图和原站核实。

#### [2026-09-21 · 看看最近两周有哪些值得分享的blog第一期](https://www.xiaohongshu.com/explore/6aafd4b80000000028039a03)

- 图集：18 张；分类：`blog`；标签：大模型、科研学习、深度学习、人工智能、强化学习、智能体。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：刚好最近申请季，非常推荐面临同样纠结想法的朋友读图1，Jinyan这篇写得非常真诚，我想一定会对一些正在申请的朋友有帮助，所以将它放在封面希望有更多人看到；图2又是我喜欢的RLM相关， post-training within the RLM harness yields further performance gains；图3 Prof. Du这篇质量非常高，论述Generalization as construction的优势，很推荐各位找来读；图4 Prof. Huang这篇很长同时质量也很高，当篇高质量综述看没有任何问题；图5质量无需多言，感兴趣属于必看；图6 intro PC-ALM. 图7 intro Mercury 2.5，测试看着还行；图8短小精悍的一篇，正方观点都有，推荐抽空看看；图9看看就好；图10解析得中规中矩，对Loop Transformer不了解的可以一看，比较了解的可以跳过；图11 intro OUI-1；图12 GPT 6 Astra is better at making money and more ethical than Claude Fable 5.1. 图13 intro Bonsai 2 27B，基本持平Qwen 3.6 27B，略逊色3.8 27B，这个尺寸想胜过Qwen太难了；图14 如何搭建second brain的教程，主要是讲基本原理和规范，推荐有需求的朋友看看；图15是作者测试PiSSA而不是传统的LoRA，结果看着不错，同时本文的演示动画做得也不错，方便理解；图16 来自经常推荐的老面孔Ben Recht，我很喜欢Ben的态度，追逐解开难题固然重要，但数学说到底是种帮我们理解世界的逻辑工具，即使未来的人们已经不需要亲自解题，但数学作为一种培养思维的教育方式依然十分重要；图17挺不错的一篇，尤其是对agent safety感兴趣的朋友可以读读；图18感兴趣的可以读他们的paper—Monitoring and Discovering Reward Hacking with Internal Representations during LLM Evaluations. 字数限制，链接按惯例在附件，需要请自取~
- 评论区含 `点点` 生成的逐篇摘要/逐图标题线索，属于评论内容，需回原图和原站核实。

#### [2026-09-20 · 看看最近两周有什么有趣的projects](https://www.xiaohongshu.com/explore/6aafc84a0000000026023a01)

- 图集：18 张；分类：`project`；标签：人工智能、大模型、深度学习、科研学习、智能体、agent。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1非常好项目，AI system that automatically transforms research papers into interactive AI agents，科研产出的形态正在被AI发展所改变，这是个好趋势；图2来自RUC datalab，目标是解决agent-data gap，从测试结果看效果不错，感兴趣的朋友可以去读他们的paper，挺有意思的；图3 Sky Lab的系列产出之前有推荐过，这次主要是更新SkySynth，autonomously build JIT systems that we can trust；图4一句话，增强agent的自我上网能力，目测很有需求；图5 local inference engine for Apple silicon，非常欢迎；图6 causal reasoning world model，测试结果看着不错，推荐给有需要的人. 图7 IDE designed for agentic AI research，很好项目；图8 名字很吸引眼球，但功能很直白，让agent别说废话；图9 open-source streaming MoE inference framework，对macOS福音；图10 Model for Speech Generation and Editing，还行吧；图11纯图一乐；图12不算很新，可以看看. 图13 作者Paul是金融学老师，小工具对VS Code重度使用者很友好；图14不错项目，类似的不少，但感觉他们做得更精细；图15 OpenRouter for agent tools；图16个人兴趣不大所以没试过；图17来自Anthropic，36 drop-in optimization kits for the inference paths of open protein- and genomics-ML tools，推荐给biotech相关的朋友；图18推荐给Robotics相关的朋友们. 链接按惯例放在附件里，有需要请自取（免费的，有需要大方拿走就行了）

#### [2026-09-15 · 开学季自觉不错的paper推荐合集八](https://www.xiaohongshu.com/explore/6a9ef461000000002603a33b)

- 图集：14 张；分类：`paper`；标签：大模型、大语言模型、llm、agent、智能体、多模态。
- 图号线索：3、8；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对喜欢图8；图3质量也不错，感兴趣的话可以关注 本轮更新结束，各位下轮更新再见~

#### [2026-09-15 · 本轮blog分享结束了，各位下轮见](https://www.xiaohongshu.com/explore/6a9ee6070000000029019188)

- 图集：15 张；分类：`blog`；标签：大模型、科研学习、深度学习、人工智能、agent、智能体。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1来自John Hewitt at Columbia，个人比较赞同John的观点，所以推荐一下；图2很不错的实验，结论直接post-trained models roughly match the performance of the base Inkling, but become up to 40% more token efficient from post-training；图3 intro software world，很有意思的项目；图4 speculative decoding拆解帖，质量还不错；图5同名paper的blog；图6 至少在现在，我倒不觉得如此悲观，不过未来会怎么样就不好说了. 图7 intro XPress，测试结果看着不错，可以关注一下；图8感谢Fabian Pedregosa，又一篇很好的blog，推荐各位感兴趣的找来读读；图9 intro Memory Anchors，非常好研究，来自做Robotics朋友的安利；图10比较长，对不对另说，但分析得挺精彩的；图11 intro XGBoost Vector-Leaf Model；图12非常好内容，很值得推荐，不过结论比较悲观，目前离得还很远. 图13想法很不错，但感觉实验和论证得不够充分；图14又是对Hugging Face Incident的分析，随便看看就好；图15个人没什么兴趣，但对有些人可能有帮助. 链接按需放在附件里，需要请自取~

#### [2026-09-14 · 开学季自觉不错的paper推荐合集七](https://www.xiaohongshu.com/explore/6a9ef392000000002b003d2b)

- 图集：17 张；分类：`paper`；标签：人工智能、机器学习、大模型、深度学习、文献阅读。
- 图号线索：2、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对喜欢图2和图17

#### [2026-09-14 · 开学季自觉不错的blog推荐合集七](https://www.xiaohongshu.com/explore/6a9edd40000000000b003db4)

- 图集：15 张；分类：`blog`；标签：agent、智能体、人工智能、深度学习、大模型、科研学习、WeeklyPick。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1是个每日更新的有关ai safety或者governance的内容合集，非常推荐有兴趣的朋友关注；图2是同名paper的主页；图3 不错的一个教学展示网站；图4如标题所示的实战记录帖；图5 intro Discovery (Beta) for Adapt-1；图6非常长也非常有料的blog，对ai infra或者ai chip感兴趣的朋友可以找来读. 图7无论是否对ai safety感兴趣，我都认为应该读一下；图8 KDA 0.5成绩有点好，推荐持续关注；图9 intro Voice Code Bench；图10我很感兴趣的Muse Code相关；图11 intro benchmirt；图12可以读读，我个人认为无论未来math research会变成什么样，math education都是重要的. 图13非常详实的实战记录贴；图14很有趣的研究，期待进一步完善或者解释；图15看看就好. 感觉需要的人不多，但姑且把链接按顺序放在附件~

#### [2026-09-13 · 开学季自觉不错的paper推荐合集六](https://www.xiaohongshu.com/explore/6a9ef304000000002601b77c)

- 图集：17 张；分类：`paper`；标签：人工智能、大模型、大语言模型、llm、强化学习、深度学习。
- 图号线索：1、2、13；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：这是很罕见的图1和图2我都比较喜欢的情况，图13也不错.

#### [2026-09-13 · 开学季自觉不错的blog推荐合集六](https://www.xiaohongshu.com/explore/6a9ed5df000000002a02dd84)

- 图集：18 张；分类：`blog`；标签：大模型、科研学习、深度学习、agent、智能体、人工智能。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1非常好内容，和上期的封面blog正好对应，training methods没有最好，只有最适合，多学点总归是好的，极为推荐各位读；图2 AMI和JEAP安利帖；图3 intro TimesFM-3, a state-of-the-art time series foundation model；图4推荐给Robotics相关的朋友们；图5非常详细的教程，如果是AMD赞助的labs感觉是必读内容；图6非常值得鼓励和传播的好研究. 图7研究还不完善，所以结论看看就好；图8 intro Streaming-WAM；图9 同名paper的blog，个人感觉感兴趣的话可以直接读blog，写得很清楚也很好读；图10挺有思考的；图11 intro NEEDLE；图12同名paper的blog，很好研究. 图13推荐给对ai economy感兴趣的朋友；图14 intro BixBench3，推荐给biotech领域的朋友；图15同名paper的blog，非常好研究，也做了很棒的可视化，值得抽空阅读；图16实战记录帖，看看就好；图17是分析V3的blog系列，目前已经更新两篇，建议感兴趣的朋友持续关注；图18质量很高的研究记录，再打磨下能变成正式paper，目前的状态其实当paper引用也没差. 虽然不知道有多少人需要，但链接按需放在附件里，需要请自取~

#### [2026-09-12 · 开学季自觉不错的paper推荐合集五](https://www.xiaohongshu.com/explore/6a9ef2690000000026030134)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、大语言模型、llm、强化学习、深度学习。
- 图号线索：1、8、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1质量很高值得单独再次安利；图8和图17也不错；另外图16感兴趣的话也是很不错的.

#### [2026-09-12 · 开学季自觉不错的blog推荐合集五](https://www.xiaohongshu.com/explore/6a9ece130000000026039d0a)

- 图集：16 张；分类：`blog`；标签：人工智能、大模型、科研学习、深度学习、智能体、agent。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1质量极高，涵盖广泛，排版与用词也很新人友好，非常推荐各位看；图2 intro FrontierSWE v2；图3很好实验，一句话总结直接看最后一句：Putting task expertise into task-specific training is ultimately what scales；图4 同名paper的blog，非常好研究；图5如标题所示的持续更新的benchmark合集；图6是之前推荐过的Sparse Linear Attention by Haoyi Zhu第二篇，非常好内容，推荐有时间时找来读. 图7感谢The Alignment Journal为alignment添砖加瓦（未来视；图8记述AI如何改变data stack；图9非常好的实战记录帖；图10 World Models from Scratch Book，目前仅更新两章，还不知道后续内容写得如何，持观望态度；图11同名paper的blog，是本轮更新中可视化做的最好的，非常方便人理解，故强烈推荐；图12 TurnBench: A Multi-Domain Benchmark for Turn-Taking Dynamics in Spoken Dialogue的主页. 图13感谢Phillip Zhou的分享，非常详实全面的指南，又是一年申请季，希望各位都有好结果；图14对Voice eval感兴趣的可以看看；图15很不错的KV Caching演示动画，适合用来教学；图16 Open, reproducible TTS/STT evaluation toolkit，很好项目. 链接按需放在附件里，需要请自取~

#### [2026-09-11 · 开学季自觉不错的paper推荐合集四](https://www.xiaohongshu.com/explore/6a9ef1970000000026030083)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、深度学习、科研学习、强化学习。
- 图号线索：1、12、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人比较喜欢并推荐图1，图12和图18.

#### [2026-09-11 · 开学季自觉不错的blog推荐合集四](https://www.xiaohongshu.com/explore/6a9ec558000000002b01c2ad)

- 图集：17 张；分类：`blog`；标签：大模型、科研学习、深度学习、强化学习、人工智能、智能体。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1 Furong Huang这篇思考很好，推荐给感兴趣的朋友们；图2和图3都是Google的，相较之下，Gemini 3.5 Transcribe的竞争优势个人感觉大一点；图4对biology研究应该挺有帮助的；图5 intro centaur-benchmark；图6个人感觉最关键是这句：when X corresponds to a generating mechanism, a Foundation Model for X makes sense; when X is merely a data format, a Foundation Model for X is much less justified，非常好内容，非常建议各位找时间读. 图7 open video dataset，伟大无需多言；图8略神棍，但思考还是挺有意思的；图9本身就是最近mathematics存在主义危机的一种反应（；图10推荐给脑神经领域的朋友们；图11 intro ZIT；图12非常好研究，结果也比较不错，期待作者们早日写成paper. 图13 intro PufferLib；图14挺长的，但核心观点是好的可学习数据非常重要；图15推荐给所有有教学任务的朋友，我个人不一定同意其中的每一个观点，但诸如personal assignment等观点我非常支持（做不做得到另说；图16 intro Terminal Bench，结果毫无意外；图17推荐给对AI governce感兴趣的朋友们. 链接按需放在附件里，需要请自取~

#### [2026-09-10 · 开学季自觉不错的paper推荐合集三](https://www.xiaohongshu.com/explore/6a9ef0ca000000000b001c86)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、agent、智能体、大语言模型、llm。
- 图号线索：1、7、8、15；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1虽然很长，但写得非常好；个人比较喜欢图7图8和图15.

#### [2026-09-10 · 开学季自觉不错的blog推荐合集三](https://www.xiaohongshu.com/explore/6a9ebd2d000000002802adcd)

- 图集：17 张；分类：`blog`；标签：大模型、科研学习、深度学习、人工智能、智能体、agent、2026开学季。
- 图号线索：2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：同1同名paper的blog，很好研究，值得推荐；图2 intro ArgMaxRL，是对MaxRL的延申，感兴趣的话也很不错；图3 On-Policy Self-Distillation in Diffusion Models的主页，非常好研究；图4无需介绍，对此感兴趣的朋友可以找Mixutre-of-Recursions, Scalling up test-time compute with latent reasoning两篇读；图5依旧是非常详细的构建AMD生态的帖子；图6非常底层的内容，推荐给感兴趣的朋友们. 图7 intro Chopin，质量倒是其次，主要名字起得很吸引我（笑；图8 同名paper的blog；图9观察RSI进展的一个网站，做得很好；图10推荐给biotech相关领域的朋友们；图11不容错过的好研究，结论很直接：a high rate of reward hacking during RL can cause models to be willing to perform long sequences of harmful real-world actions in pursuit of task success；图12 Alexander Terenin正在更新的书，目前已更新前两章，感兴趣的推荐关注. 图13写得比较浅，随便看看就好；图14 基于FastH3开发的应用；图15 ETH Zürich’s Robot Learning Course学习笔记，我看了下记录得很详实，如果学这门课的话可以作为参考资料；图16 a system design simulator for learning how distributed systems behave under load；图17 Anthropic亲自教你如何成为新时代的开发者，建议cs146s收录这篇（. 链接按需放在附件里，需要请自取~

#### [2026-09-09 · 开学季自觉不错的paper推荐合集二](https://www.xiaohongshu.com/explore/6a9eefc300000000270142be)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、深度学习、agent、智能体、强化学习。
- 图号线索：1、4、5、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1是以前推荐过的Rethinking On-Policy Distillation of Large Language Models的第二篇，非常好研究；图4和图18个人也很喜欢；另外安利下图5，穷鬼实验室福音.

#### [2026-09-09 · 开学季自觉不错的blog推荐合集二](https://www.xiaohongshu.com/explore/6a9eb507000000000b00ea83)

- 图集：18 张；分类：`blog`；标签：人工智能、大模型、科研学习、深度学习、智能体、具身智能、2026开学季。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1质量极高的Speculative Decoding讨论，paper引用也很有品味，非常推荐各位有空时找来看；图2 intro NoRA，非常好研究；图3来自Hao AI Lab，FastH3可能对一些小团队意义重大；图4 intro Solaris；图5比较短也比较浅，强调人类的重要性；图6 intro VGI-Bench，很好研究，感兴趣不要错过. 图7 intro VDN-H3，与FastH3类似，快都是特色；图8最近讨论疯了，没什么好说的，成果在预料之中，但没想到这么快；图9 intro Atlas，World Labs出品；图10 intro Thea，朋友说是很有意思的研究，感兴趣的可以关注；图11 ProgramBench安利帖；图12 collection of kernels, guides, and examples for FlexAttention. 图13 那篇Code as Worlds的blog，写得很好，研究也很有意思，推荐各位读；图14 intro cua-lite；图15是作者把工作基本交给agents的体验记录贴，显然作者对agents的能力是很满意的；图16 intro RSI-Exam，由于没有Astra，所以Opus 5领先；图17大概是最好的continuous dllm blog，虽然很长，但我依然推荐找时间来读；图18同名paper的blog. 链接按需放在附件里，需要请自取~

#### [2026-09-08 · 开学季自觉不错的paper推荐合集一](https://www.xiaohongshu.com/explore/6a9eee53000000002b025f59)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、深度学习、科研学习、文献阅读、agent、智能体。
- 图号线索：1、8、11、13；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1来自Fei-Fei Li；个人非常安利图8（毕竟rlm），图11也觉得不错；图13做Embodied AI相关的朋友可以关注.

#### [2026-09-08 · 开学季自觉不错的blog推荐合集一](https://www.xiaohongshu.com/explore/6a9eac5b000000000b035f9b)

- 图集：18 张；分类：`blog`；标签：人工智能、大模型、科研学习、深度学习、智能体、agent。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1非常好研究非常有价值发现，让人激动又害怕；图2以前Alex Zhang的内容属于对rlm感兴趣的必看，现在感觉即使对rlm不感兴趣，也可以看看，他的很多思考非常棒；图3如标题所示的architecture介绍，清晰全面，值得推荐；图4很不错内容，对于一些内容创作者可能会有帮助；图5非常好的BO内容合集，感兴趣的不要错过；图6 同名paper的网站，整合得很好. 图7 一些高质量的physics diagrams合集；图8 continual learning infra for self-improving agents，很值得推荐；图9很有意思的研究，结论technical progress alone does not determine token demand or revenue，动态均衡的过程；图10很有帮助的小项目，local-first search layer；图11如标题所示，它并没有测Astra，所以测试结果里Opus 5领先很多；图12很有趣的harness evaluation，测试结果codex领先，而成本方面cc遥遥领先. 图13是作者mathematical foundations of curiosity的第二篇，质量非常高，感兴趣的朋友不要错过；图14略神棍，个人不是很感兴趣；图15非常好的Phd经历回顾，我很希望这样的贴子能被更多正在考虑是否读博的朋友看到，这是一段艰辛的旅程，会获得很多但也会失去很多，并且我认为即使在AI更发达的将来，它依然有意义；图16 intro K2, largest fully open-source model；图17如标题所示，非常好的AI infra教程；图18写得不算深，但很对：evaluation应该把它视为指导进步的标尺. 链接按需放在附件里，需要请自取~

#### [2026-09-07 · 开学季自觉不错的project推荐合集](https://www.xiaohongshu.com/explore/6a9e9f8700000000260328ae)

- 图集：18 张；分类：`project`；标签：人工智能、大模型、开发者社区、智能体、具身智能。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1很有想法，One agent view for every coding harness；图2是持续更新中的ml engineering book，很不错；图3个人兴趣不大，但对感兴趣的人而言应该会很有帮助；图4 free and open source video editor，非常好；图5如简介所示的一款模拟小游戏；图6 a family of universal multimodal embedding models by the WeChat Vision Team，感兴趣的话非常不错. 图7 agent framework，评测看着挺好的; 图8超轻量级的tts；图9 open source agent microharness featuring persistent agency and recursive LLMs，很好项目；图10略；图11 local-first workspace for research agents and autoresearch，完成度还行但这类项目真挺多的；图12很应该推广，就记得作者是惠痴（笑. 图13 infra相关；图14 Infra合集资源，非常值得推荐；图15非常感谢Chen Liu愿意分享自己的Python scripts for high-quality figures；图16 MCP server that lets LLM agents play full games of Civilization VI，非常有意思的项目；图17另一个小游戏，可以看到随机一个时代一个地点降生的人可能面临怎样的命运，挺推荐各位试试的；图18非常好项目，对agent感兴趣的很推荐试试. 链接按需放在附件里，需要请自取~

#### [2026-09-07 · 新生友好的大语言模型优秀课程推荐合集](https://www.xiaohongshu.com/explore/6a9e8765000000000b003654)

- 图集：17 张；分类：`other`；标签：人工智能、大模型、科研学习、大语言模型、2026开学季、转码。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：之前看到很多人推荐llm course时基本都推cs336，cs336固然非常好，甚至可以说是The Course in llm age. 但是个人感觉所有人都学一门课略显无聊，同时也有很多其他很棒的课程值得被了解，所以做了这份合集.最近正好是开学季，希望这份课程合集能对新同学们的学习有所帮助. 值得说明的是本合集并不涉及nlp courses，虽然现在nlp与llm课程设置越来越像，但还是有所差别.另外本合集也不涉及alignment或者evaluation相关的课程.下面进入正题. 图1是Chenhao Tan他们开发的课程，质量很高，课程深度很足议题涵盖也广，如果有一定基础我很推荐这门；图2来自ETH Zürich，非常规整全面的intro，所有需要的信息一应俱全，他们还有很多相关的课程点teaching里就能看到，如果是从0开始学的话极为推荐；图3无需介绍，如果只推荐一门的话我也会推荐cs336；图4是门让人更好理解transformer架构以及llm工作原理的课程. 图5是Wei Xu的课，与图1类似议题深度与广度都很不错，但同样需要一定基础；图6集中在如何更好地利用数据训练llm，理论深度很足；图7感谢Greg Durrett，应该是目前最好的llm reasoning课程；图8理论课，质量很不错但阅读量也很大；图9更为纯粹的议题讨论课，更推荐已经学完类似图1-图4课程的同学学习；图10和图9类似也是理论课，推荐希望能更深入了解llm的同学学习. 至此，课程推荐完毕，以下是些辅助学习的资料： 图11是篇非常系统的llm发展史梳理，非常建议抽时间阅读；图12如果要自己动手训练，这篇是必读内容，你会在很多课程的推荐阅读列表里找到它；图13实时更新的LLM Architecture Gallery，Sebastian Raschka是这个时代伟大的教育者，你能在他的网站找到几乎感兴趣或者需要的所有内容；图14开源模型发展史，深入浅出非常好读. 图15-图17是三篇我认为比较适合搭配课程学习的paper，图15是综述，图16是本不错的教材，图17是模型架构的综述.以上都能在arxiv上很轻松地找到. 链接都在附件里，需要请自取~ 最后祝各位学习顺利！

#### [2026-08-30 · 月底了，推荐点自觉不错的paper（七）](https://www.xiaohongshu.com/explore/6a8b1e770000000033029490)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、科研学习、文献阅读、大模型、强化学习。
- 图号线索：1、11、12、14；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1挺有意思的，个人相对喜欢图12和图14，图11感兴趣的也可以关注一下 各位9月更新见~

#### [2026-08-29 · 月底了，推荐点自觉不错的paper（六）](https://www.xiaohongshu.com/explore/6a8b1dc300000000330292d8)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、深度学习、文献阅读、科研学习。
- 图号线索：4、12；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对而言喜欢图4和图12

#### [2026-08-29 · 月底了，推荐点自觉不错的blog（六）](https://www.xiaohongshu.com/explore/6a8b18c30000000033009bc2)

- 图集：14 张；分类：`blog`；标签：人工智能、大模型、科研学习、深度学习、强化学习、2026开学季。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14；采集记录：匿名隔离会话记录。
- 作者图集说明：图1与其说是安利这篇文章（当然它很有价值，尤其是还可以搭配视频学），不如说是安利Sebastian Raschka，之前很自然地认为llm from scratch的作者自然耳熟能详，但好像不是那样.领域总有新人，对他们来说llm from scratch或者Ahead of AI能帮到很多，但他们未必知道；图2 如其名的实践记录贴；图3 Percy Liang他们训模型用的数据集，说起Percy Liang就想起每次看见人安利llm course的时候公式推荐cs336，其实也有很多其他非常棒的llm course，有需要的话我下次做个合集吧；图4非常有价值的记录贴，很清晰地反映这些年AI领域的发展如何影响研究的方式，给的聚焦于问题的建议也很踏实，推荐给正在读博或者想要读博的朋友们；图5 pinned memory解析贴，很有价值；图6 个人很喜欢compass and certificate的比喻，区分它们是有必要的. 图7内容比较浅但胜在完整，感兴趣的可以读；图8看看就好；图9 Multi-Vector Models实践攻略贴；图10 Better, Faster, Stronger: Programmatic Skill Learning Best Reduces Agent Cost的blog，还算有趣，可视化交互做得也不错；图11 论述Scale-Dependent Algorithms的优势；图12非常好研究，值得安利. 图13 Junbo Zhao亲自写的关于dLLMs的体悟，对dLLMs感兴趣的话非常值得阅读；图14非常高质量的biophysical simulation实践指南贴，对此感兴趣的朋友推荐找来读. 链接按序放在附件里，需要请自取~

#### [2026-08-28 · 月底了，推荐点自觉不错的paper（五）](https://www.xiaohongshu.com/explore/6a8b1d170000000028026612)

- 图集：18 张；分类：`paper`；标签：人工智能、文献阅读、大模型、科研学习。
- 图号线索：1、8；采集记录：匿名隔离会话记录。
- 作者图集说明：个人相对而言喜欢图8，图1和6感兴趣也可以关注

#### [2026-08-28 · 月底了，推荐点自觉不错的blog（五）](https://www.xiaohongshu.com/explore/6a8b0cb80000000038001716)

- 图集：16 张；分类：`blog`；标签：人工智能、深度学习、大模型、科研学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16；采集记录：匿名隔离会话记录。
- 作者图集说明：图1非常长，阅读前请做好心理准备，但内容不复杂，基本是梳理各家硬件的发展脉络，文章结尾有对比和总结；图2作者是AI4Math的绝对反对者，虽然不一定同意他的观点，但质量还是不错的；图3 LLMRouter安利帖；图4精华是这句：what matters is not raw bits, but the signal‑to‑noise ratio of the gradients for the objective you actually care about；图5 intro MAGI-2 Preview；图6 intro R-lens. 图7很长很长的一篇实验记录帖；图8 intro fitness-seekers；图9认为随着AI发展，护理行业会崛起，这就去推荐人学护理（笑；图10如标题所示的实践记录贴；图11核心就一句话“the core point is that I view the lack of safety as generally a lack of an ability to suitably prepare”；图12非常好文章，我也推荐各位自己读而不是让agents读那些自己真正喜欢的papers. 图13 intro VALG-ML-Theory-Agent，感兴趣的可以找他们的paper读；图14同名paper的blog，个人感觉直接读blog就行；图15比较意料之中的成果；图16非常好研究，blog的可读性也很出色，值得推荐. 链接按序放在附件里，需要请自取~

#### [2026-08-27 · 月底了，推荐点自觉不错的paper（四）](https://www.xiaohongshu.com/explore/6a8b1c74000000003703c963)

- 图集：17 张；分类：`paper`；标签：人工智能、深度学习、大模型、科研学习、文献阅读。
- 图号线索：1、15；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1质量很高，个人相对而言喜欢图15

#### [2026-08-27 · 月底了，推荐点自觉不错的blog（四）](https://www.xiaohongshu.com/explore/6a8b047700000000380038e7)

- 图集：17 张；分类：`blog`；标签：大模型、科研学习、深度学习、强化学习、大语言模型。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1可以实时看到Percy Liang他们training，我个人非常支持学术界将自己的训练过程全程公开，不过非常可惜的是，有意愿且有条件的应该不多；图2 how to design effective loops实践帖；图3个人觉得可以跳过；图4实验比较有趣，同时blog整体的图文设计也很出色，读起来清晰直观且不会视觉疲劳；图5 ai safety相关；图6 Sarah Pan对TTT的体悟，虽然篇幅短，但很精华，值得阅读. 图7 intro DFlash 2；图8看看就好；图9 很支持Tim O’Reilly的观点；图10梳理agentic rl近期的发展趋势；图11 intro SLM-Online-SDFT，非常好内容，值得推荐；图12 短小精悍的文章，随着研究爆发性增长，taste变得越发重要和值得培养，十分推荐各位有空时读. 图13比较长，但作者积极拥抱AI4Math的态度我很欣赏；图14简单说 ICML papers reproductions不理想；图15没什么新意；图16给勃勃生机的AI4Math再添点燃料；图17随便看看，个人不是特别感兴趣. 链接按序放在附件里，需要请自取~

#### [2026-08-26 · 月底了，推荐点自觉不错的paper（三）](https://www.xiaohongshu.com/explore/6a8b1beb000000003300a535)

- 图集：18 张；分类：`paper`；标签：人工智能、文献阅读、大模型、科研学习、深度学习。
- 图号线索：7、16；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对而言喜欢图7和图16

#### [2026-08-26 · 月底了，推荐点自觉不错的blog（三）](https://www.xiaohongshu.com/explore/6a8aface00000000280270db)

- 图集：17 张；分类：`blog`；标签：人工智能、大模型、科研学习、深度学习、强化学习、2026开学季。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1来自Prof. Tom McCoy, 文章围绕theory of mind展开，在这个人与人链接变得越发重要的时代，我认为挺值得推荐的；图2 直接回应“LLM can’t jump” by Tom Zahavy，强调interconnected knowledge的重要价值；图3 同名paper的blog，挺有意思的；图4我非常赞同Ben的观点，但这种想法很难实现，除非再来一次寒冬（应该没人想经历；图5 intro Ornith-1.5；图6 MiniMax Music 3，非常好模型. 图7 a tutorial for unlearning，感兴趣的可以看看；图8这种测试意义不大，毕竟不可能改变大多数人的使用习惯，而且随着coding agents的普及，越来越少的人会学习多门甚至一门编程语言；图9 CC plugin that shows plain-English rewrite of each assistant message，有的人可能会很需要；图10只能感慨Edward Z. Yang的伟大，可以在网页上选择你的模型和硬件，它会自动显示你需要的内容，对于新人或者小团队而言会非常有帮助，十分推荐；图11 intro ComfyResearch；图12同名paper的blog，有上下两期，写得很完整，感兴趣的直接读blog就好. 图13记录得非常详细扎实，感觉可以作为学习经历记录型blog的范例；图14 intro Weight Cache Daemon；图15很好研究，blog写得非常简洁，感兴趣的建议读paper；图16过于依赖AI当然不对，但不依赖AI也不行，我相信每个人都能找到适合自己的平衡点；图17看看就好. 链接按序放在附件里，需要请自取~

#### [2026-08-25 · 月底了，推荐点自觉不错的paper（二）](https://www.xiaohongshu.com/explore/6a8b1b1c000000003703c5f9)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、深度学习、文献阅读。
- 图号线索：9；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对喜欢图9；Tian-Zheng Wei的Dissertation也不错

#### [2026-08-25 · 月底了，推荐点自觉不错的blog（二）](https://www.xiaohongshu.com/explore/6a8aefcb00000000380026a7)

- 图集：17 张；分类：`blog`；标签：大模型、科研学习、深度学习、人工智能。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1 Together AI做的这个网站非常好，可以按月或者按类别回顾近一年来最重要的那些papers，很推荐大家有空时浏览回顾；图2看就完事了；图3推荐给对AI4Game感兴趣的朋友；图4同名paper的blog；图5 ai safety相关，harness会变得越来越关键；图6同名paper的blog，感兴趣可以找他们的demo. 图7 GTSAM has a new opt-in CUDA backend for nonlinear factor-graph optimization；图8测试结果表明贵有贵的道理；图9 intro Muse Glimmer，感觉和Gemma4 31B或者Qwen3.6 27B伯仲之间；图10又名Awesome Reliable Self-Evolving Agents Collection；图11看似在输出爆论，其实是在安利自家的ComfyResearch；图12 安利Nemotron 3.5 Lightning. 图13挺好的观察网站，AI use is continuously changing；图14同名paper的主页，研究很有趣的同时可视化做得很不错；图15简单讲，AI是否会带来高速经济增长的正反方相互没法理解，说服不了对方；图16 fast inference实战攻略帖，写得还算可以；图17非常好研究，感兴趣的话推荐找来看看. 链接按序放在附件里，有需要请自取~

#### [2026-08-24 · 月底了，推荐点自觉不错的paper（一）](https://www.xiaohongshu.com/explore/6a8b1a0a0000000023013977)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、文献阅读、深度学习。
- 图号线索：15；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：前三篇质量都非常高，个人比较喜欢图15，5也可以留意一下

#### [2026-08-24 · 月底了，推荐点自觉不错的blog（一）](https://www.xiaohongshu.com/explore/6a8ae2fd000000002202e2c0)

- 图集：18 张；分类：`blog`；标签：大模型、科研学习、深度学习、强化学习、AI搞学习howto、人工智能。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1是David Bau整合的最能反映deep learning发展历程的papers，都是经典中的经典，非常推荐新人读；图2大概是这段时间最热门的一篇同名paper的blog，Luca这篇写得简洁清晰，非常推荐感兴趣的找来读；图3 intro hierarchy filling，很有趣的想法，期待看到进一步的研究或者拓展；图4 intro Harness-Delta Attribution，完成度很高的研究；图5随便看看，核心是强调人的重要性；图6 ctok reconstructs Claude token counts offline. 图7依旧是安利自家的Sol Video Inference Engine；图8如其名所示，plain-language writing skill for AI agents；图9非常有趣的文章，从CS的视角看如何利用基因编译大脑；图10同名paper的blog，他们的chatbot直接可以对话，感兴趣的可以试试；图11 intro DataSmith；图12依旧是nVidia加强自己生态的实用工具. 图13 AI safety相关的检测报告，Anthropic矮子里拔将军并不让人意外；图14 Arctic Training and Inference Platform，出色竞品太多；图15值得一读的好文章，动画演示也做得很出彩；图16虽然来自OpenAI，但没多少新意；图17核心就一句：A sufficiently RLed model learns to adopt — in a given context — the persona that is most likely to lead to the reward in that context；图18同名paper的blog. 链接按序放在附件里，需要请自取~

#### [2026-08-23 · 月底了，推荐点自觉不错的projects](https://www.xiaohongshu.com/explore/6a8ad6eb000000003300a4bf)

- 图集：18 张；分类：`project`；标签：人工智能、大模型、科研学习、深度学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1非常值得推荐，可以让MoE models更好地跑在消费级PC上，感兴趣的建议读下paper；图2 来自Microsoft，极度轻量化但五脏俱全的Agentic RL Framework for Training Agents，非常好项目；图3也是framework for agentic training，看着还行；图4来自Kevin Murphy，感兴趣可以看paper；图5 development and dispatch library for high-performance machine learning kernels，质量不错；图6非常实用的去水印工具，对于有此需要的人而言很伟大. 图7如其名所示的小工具；图8是小红书自己的model，测试成绩看着不错，感兴趣的可以试试；图9 agent backbone for Lean 4,推荐给有需要的人；图10非常''toy'', 用来参考大可不必，但可以用来教学；图11 paper list for Co-Evolution in Agentic Systems，粗看下整理得还不错；图12 Public vulnerability intelligence platform for open source，做得不错，目测有需要的不多. 图13就不用介绍了，DeepSeek Harness人人都知道，重点是图14在我刚看到dsh的时候就有了，速度之快令人感慨，同时一直也在保持更新，对dsh感兴趣的不要错过；图15 open RL framework，中规中矩，做的还行但优质竞品实在太多；图16 老项目，最近增加了多语言支持；图17 multi-instrument music transcription model，LeCun转发了这个项目（感觉毫不令人意外；图18简单讲就是 LLM serving-path “错题本”，有需要的话还是挺不错的. 链接按序放在附件里，需要请自取（虽然从数据上感觉需求量并不大

#### [2026-08-15 · 八月paper推荐合集第六期](https://www.xiaohongshu.com/explore/6a78a49c000000002c004f7c)

- 图集：15 张；分类：`paper`；标签：AI进化生活howto、人工智能、大模型、科研学习、文献阅读、深度学习。
- 图号线索：1；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对喜欢图1 各位下轮更新再见~

#### [2026-08-15 · 八月blogs推荐合集第六期](https://www.xiaohongshu.com/explore/6a78a051000000002c004317)

- 图集：17 张；分类：`blog`；标签：AI进化生活howto、人工智能、大模型、科研学习、深度学习、大语言模型。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1同名paper的blog，个人感觉直接读blog更方便理解；图2 widely used text-to-SQL benchmarks contain high annotation error rates；图3有意思的是这条：models often did not reason about their cheating in their chain-of-thought；图4 end-to-end MXFP8 and per-token NVFP4 for MoE experts实战记录贴；图5 intro Online KL Shampoo；图6 JEPA相关. 图7为AI4Science添砖加瓦，external simulation tools do noticeably improve agent performance, allowing models to think for longer and solve problems that they can't solve otherwise；图8 intro infini-gram；图9 leJEPA实战记录贴；图10 our results suggest that evidence from directly asking identity questions is weak，也就是说这种方法无法判断是否distillation（老生常谈；图11 intro Photon 2.0；图12同名paper的blog，很不错的研究. 图13 intro Mixture-of-Kittens (MoK)；图14看完就记得mlx-mamba快得不可思议（；图15 Can AI agents conduct open-ended AI research那篇的介绍；图16非常值得推荐；图17一般，个人感觉可以跳过. 链接按序放在附件，有需要请自取~

#### [2026-08-14 · 八月paper推荐合集第五期](https://www.xiaohongshu.com/explore/6a78a3c00000000032032ee4)

- 图集：18 张；分类：`paper`；标签：AI进化生活howto、人工智能、科研学习、大模型、文献阅读。
- 图号线索：13、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对喜欢图13，图17看看就好.

#### [2026-08-14 · 八月blogs推荐合集第五期](https://www.xiaohongshu.com/explore/6a78982f000000002c001ed2)

- 图集：18 张；分类：`blog`；标签：AI进化生活howto、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1写得挺有意思的，不过results看看就好；图2 kimi-k3个人认为最大意义是给开源社区注入强心剂，我也希望所有LLMs都能够开源，但我并不认为闭源走不通（至少是商业层面上；图3 LLM Inference Handbook，新人友好向资源；图4 intro Apertus 1.5；图5 Alvin Zhang非常高质量的研究，非常期待作者将其完善为正式论文；图6读就完事了. 图7 同名paper的blog，很不错的研究；图8 intro DiskANN；图9 intro LFM2.5-2.6B；图10属于比较入门的手把手教系列，目前已经更新part2，感兴趣的可以关注；图11写得很好，无论是否赞同作者的观点，感兴趣的话都值得读一读；图12 intro One Layer Deeper. 图13 GEPA相关；图14 alignment相关，感兴趣的可以看；图15是大白话讲解工作原理，熟悉的建议跳过；图16 intro Wan-Animate-2；图17来自Jinyan Su，非常好的梳理总结，她那篇After Leaving Research, I Finally Feel at Peace也可以读；图18个人兴趣不大，推荐给感兴趣的朋友/ 链接按序放在附件，有需要请自取~

#### [2026-08-13 · 八月paper推荐合集第四期](https://www.xiaohongshu.com/explore/6a78a2e70000000032032c6e)

- 图集：17 张；分类：`paper`；标签：人工智能、深度学习、大模型、文献阅读、强化学习。
- 图号线索：10、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图10和图17都挺有意思的

#### [2026-08-13 · 八月blogs推荐合集第四期](https://www.xiaohongshu.com/explore/6a788e8f0000000022016956)

- 图集：18 张；分类：`blog`；标签：AI进化生活howto、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1 intro Explorative Modeling，非常好研究，很值得推荐，感兴趣的可以读他们的paper；图2偏哲学思考，核心结论classical symbol systems are useful external tools for an intelligent system to use — but that those symbol systems are not the intelligence itself；图3 intro MAI-Cyber-1-Flash；图4同名paper的blog，个人觉得直接看blog就好；从每年类似图5这类项目不仅能看出研究趋势，还能看出研究膨胀（；图6看看就好. 图7全文围绕people don’t simply refuse to cooperate with AI. Instead, the social norms that ordinarily guide cooperation lose their power这句话展开；图8老生常态的问题：AI is redesigning tasks；图9同名paper的blog；图10同名paper的blog，个人认为感兴趣的话直接读blog就好；图11作者持相对保守的立场，可以一看；图12 intro VISTA. 图13很棒的训练实战帖；图14 intro Adapt-1，写得很详细；图15 LLaTTE: Scaling Laws for Multi-Stage Sequence Modeling in Large-Scale Ads Recommendation的blog；图16 intro Prime Agent，rlm相关，极其推荐；图17 intro MatrAIx，非常有意思；图18很棒的合集，虽然这里面大部分图都能让AI agents极其容易做出来，但是自己看着code时总有一种踏实感.... 链接按序放在附件，有需要请自取~

#### [2026-08-12 · 漫无止境的八月paper推荐合集第三期](https://www.xiaohongshu.com/explore/6a78a26f0000000026036cbd)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：8；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对喜欢图8

#### [2026-08-12 · 漫无止境的八月blogs推荐合集第三期](https://www.xiaohongshu.com/explore/6a7884f700000000240253d6)

- 图集：17 张；分类：`blog`；标签：AI进化生活howto、人工智能、大模型、科研学习、深度学习、大语言模型。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1是loop language models design guide，质量非常高，很推荐各位读；图2看看就好；图3 intro ProteinGym，推荐给biotech相关的朋友；图4同名paper的blog；图5实际是co-inventors安利帖；图6 intro PostTrainBench v1.1. 图7非常完整的实战帖；图8 Persona structure shows through, differently per lab, and often in micro-interactions that are hard to spot and tease out；图9 KV Caching for dLLMs，比较基础内容；图10非常长，但个人觉得质量普通，可读可不读；图11 THINKING MACHINES这篇的观点我很认同，当前开源社区对performance的关注度确实远胜于safety；图12对研究没什么帮助，但对投资有帮助（可能. 图13作者认为很多人仍在低估目前AI agents能力；图14 intro user awareness；图15 intro AskChem，顾名思义chemistry相关；图16同名paper的blog；图17 intro tutormoments. 链接按序放在附件，有需要请自取~

#### [2026-08-11 · 漫无止境的八月paper推荐合集第二期](https://www.xiaohongshu.com/explore/6a78a1f5000000002c0047b9)

- 图集：18 张；分类：`paper`；标签：人工智能、科研学习、大模型、深度学习、文献阅读。
- 图号线索：1、11、12；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人喜欢图12，图1和图11也挺不错的.

#### [2026-08-11 · 漫无止境的八月blogs推荐合集第二期](https://www.xiaohongshu.com/explore/6a787c1f00000000270206c5)

- 图集：18 张；分类：`blog`；标签：AI进化生活howto、人工智能、大模型、深度学习、科研学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1结论很直接，ELR provides a better heuristic for controlling optimization in LLM pretraining，推理论证都做得很好，很推荐找时间读；图2 Muyu He这篇内容比较基础，但质量依然很高；图3 ai safety相关；图4文章很长，质量马马虎虎，感兴趣的可以看看；图5 intro RSIBench；图6结论写在标题里. 图7 Sparse Linear Attention这篇不错；图8同名paper的blog，个人挺喜欢这篇研究；图9 intro Inkling-Small，测试看得还行，算有竞争力；图10 Bigtable历史回顾贴；图11 intro Flue 2.0；图12好些大佬都转了这篇，我也很认同这种观念. 图13前些天非常火的议题，确实是很了不起的成就；图14正好与图13的成就可对照起来读；图15 IMLE确实不错；图16非常好的网站，虽然这里大部分models都很知名，但统合起来也很有价值，感谢Nathan Lambert；图17可以总结出离开大厂独自创业的人的共性：获得更大的自我实现价值；图18 intro Pax Machina, 稍微看看就行. 链接按序放在附件里

#### [2026-08-10 · 漫无止境的八月paper推荐合集第一期](https://www.xiaohongshu.com/explore/6a78a16d0000000025001f24)

- 图集：18 张；分类：`paper`；标签：人工智能、文献阅读、大模型、科研学习、深度学习。
- 图号线索：1、12、14；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1图12的质量都很好，个人相对喜欢图14

#### [2026-08-10 · 漫无止境的八月blogs推荐合集第一期](https://www.xiaohongshu.com/explore/6a7871ae00000000240247dd)

- 图集：18 张；分类：`blog`；标签：AI进化生活howto、人工智能、大模型、科研学习、深度学习、大语言模型。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1的质量非常好，Yichuan Wang发现一个很有趣的现象，结论很简洁Bitwise parity works. It helps in some places and does very little in most，期待进一步的探索；图2是Christopher Potts对这些年自己对CoT monitoring的思考总结，不算长但很有料；图3 intro Instella-MoE；图4挺欣慰看到AMD持续加强生态；图5 intro Neutrino-1，挺普通的；图6同名paper的blog，挺不错的研究. 图7看看就好；图8 AISPA: User-Centric System Prompt Auditing for Large Language Model Applications的网页，非常好研究，值得推荐；图9挺有意思的行为学研究，个人认为最有意义的结论是People extended the experiment beyond what we expected；图10 同名paper的blog，很有趣的研究；图11这篇blog写得很真实，AI tools的发展并不会毁灭数学研究，只会继续加速数学研究；图12是篇质量很高的报道，对AI reasoning的支持和反对方的主要观点都作了介绍，可以一看. 图13质量很高，对Ads Recommendation Model感兴趣的推荐读；图14 intro terminal-bench 3.0；图15省流总结在图上，但事情有个过程；图16 intro Flex，a DSPy module；图17如图所示，个人更感兴趣Muse Code；图18可以用来搜些有趣的图片的点缀slides. 链接按序放在附件里

#### [2026-08-09 · 漫无止境的八月自觉不错projects推荐合集](https://www.xiaohongshu.com/explore/6a7865a8000000002402595c)

- 图集：18 张；分类：`project`；标签：AI进化生活howto、人工智能、大模型、科研学习、深度学习、这个网站真好用。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1是动手学rl的资源，内容较新且在持续更新中，非常适合入门，可以和之前分享过的讲义资源配合使用；图2如其名所示，portable task specific LoRA adapters；图3 agent environments platform，看着还行；图4来自MoonshotAI，看着很不错但还没有试过；图5同名paper的model，推荐给biotech相关的朋友；图6推荐给对AI行为学研究感兴趣的朋友. 图7来自nVidia，推荐给对AI infra感兴趣的朋友；图8 torch-native framework for training speculative-decoding draft models，非常好项目；图9 OpenAI开源了Codex Security，非常好行为；图10非常实用的项目，愿诸位每投必中；图11 Qwen-UI-Agent，demo看着还行，感兴趣的朋友可以关注；图12 multiplayer agent harness for work，号称适合初创企业. 图13 collection of nearly 15,000 open mathematics problems, built to make them easy to explore，适合为当前如火如荼的AI4Math再添点柴；图14感觉同类挺多的，都大差不差；图15几乎能把所有的文字资料转换成markdown，效果很好，非常推荐；图16 Pi extension for async subagent delegation with truncation, artifacts, and session sharing；图17 Open-source inference server and production cluster for all the models your agent needs；图18 感兴趣的可以看看，个人兴趣不大.

#### [2026-07-30 · 月底分享之自觉不错的paper第五篇](https://www.xiaohongshu.com/explore/6a64f0df000000000c017239)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、深度学习、文献阅读。
- 图号线索：8、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人觉得图18质量很好，个人相对喜欢图8一点 各位下轮更新见~

#### [2026-07-29 · 月底分享之自觉不错的paper第四篇](https://www.xiaohongshu.com/explore/6a64efe90000000013026601)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、文献阅读、深度学习。
- 图号线索：9、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图9质量挺好，个人更喜欢图17

#### [2026-07-29 · 月底分享之自觉不错的blog第四篇](https://www.xiaohongshu.com/explore/6a64ecd0000000001002a8a5)

- 图集：17 张；分类：`blog`；标签：人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1是同名paper的blog，blog写得非常清晰，直接看就成；图2 intro OPHIS；图3简单而言，不可能逆转AI辅助科研的趋势，但起码可以加强署名者的负责程度；图4 同名paper的blog；图5 Inkling优化实战记录；图6 introSkyRL v3. 图7 Interaction Scaling: Grounding the Third Axis of Test-Time Compute的blog，个人很喜欢这种提供高质量极简版总结的研究；图8刚看到Organization Design时以为是篇水文，结果挺有料的，用attention以及complexity来推导最优规模，推荐给对该交叉领域感兴趣的朋友；图9愿景很好，但是估计很难做到，成本与意愿至少在当前都不支持；图10推荐给biotech相关的朋友；图11 Non-vacuous Generalization Bounds for Reinforcement Learning with Verifiable Rewards的blog；图12 J-lens may be limited to single tokens, but it is likely that representations that describe the model’s computations occur over multiple tokens. 图13强调imitative learning的重要性；图14不评价，感兴趣的可以自己看；图15 intro RIPO(Riemannian Isometric Policy Optimization)；图16感兴趣的可以读一读；图17 AR diffusion matters. 链接按序放在附件中，有需要自取~

#### [2026-07-28 · 月底分享之自觉不错的paper第三篇](https://www.xiaohongshu.com/explore/6a64ef46000000000e037e0e)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、文献阅读、深度学习。
- 图号线索：1、16；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：个人相对喜欢图1和图16

#### [2026-07-28 · 月底分享之自觉不错的blog第三篇](https://www.xiaohongshu.com/explore/6a64e38b000000000c015bec)

- 图集：18 张；分类：`blog`；标签：人工智能、深度学习、大模型、科研学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1质量很高，对JEPAs感兴趣的不要错过；图2作者的选择我十分钦佩，在这样的时代坚守自己的价值观并一以贯之于工作中，并不是一件容易的事情；图3内容比较基础，已经有相关经验的朋友建议跳过；图4是篇去年的“旧文”，系统性地回顾LLMs的发展历史，质量很高，推荐有空时阅读；图5 three-part report with expanded analysis of SkillOpt's update policies；图6 intro RoboTTT. 图7省流版If you are choosing or building agent-facing observability tooling, start with the checklist above: what can the agent see, what can it ask, what can it return；图8如标题所示，推荐给biotech相关领域的朋友；图9分析use model internals的条件，可以一看；图10 intro KTransformers；图11深入浅出的好文章，极度推荐阅读；图12支持open weights policy的人都会乐于见到kimi k3的成功. 图13同名paper的blog，非常好survey；图14适合biotech相关的朋友阅读；图15看就完事了；图16 intro Laguna S 2.1；图17 intro Hyra；图18至今最好的continual reinforcement learning introduction. 链接按序放在附件里，需要请自取~
- 评论区含 `点点` 生成的逐篇摘要/逐图标题线索，属于评论内容，需回原图和原站核实。

#### [2026-07-27 · 月底分享之自觉不错的paper第二篇](https://www.xiaohongshu.com/explore/6a64eea80000000009036b83)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、大模型、科研学习、文献阅读。
- 图号线索：1、14；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1随手翻翻就行，个人喜欢图14.话说之前thinking machines发布Inkling时，看到Yifan Zhang发了: "RoPE is dead, long live GRAPE", 我个人认为虽然没那么快，但真正好的研究终会影响到最前沿的模型.

#### [2026-07-27 · 月底分享之自觉不错的blog第二篇](https://www.xiaohongshu.com/explore/6a64dbed000000001f01ffc2)

- 图集：18 张；分类：`blog`；标签：人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：匿名隔离会话记录。
- 作者图集说明：图1质量很高，作者自制的3×3 framework来具体情况具体分析很有帮助，非常推荐有空时找来读；图2是三者的架构分析，相对偏基础；图3 ai safety research tracker；图4 main lesson is that text latents should be judged as generative objects；图5 deepmind大谈agents对science的意义；图6 intro Schema. 图7 learning theory相关，其实就是讲IDBD对比SGD及其变体的优势在部分情况下成立；图8和图9看看就行；图10最好的agentic-world-models introduction；图11同名paper的blog；图12 intro VidaForge. 图13 intro AlayaWorld；图14认为应该继续扩大算力；图15 FilmWorld: Agentic Novel-to-Film Generation through Dynamic Cinematic World Modeling的blog；图16 intro imagination models；图17 intro Apple-π；图18 单纯告知FLUX 3发布，原本是想放那篇很多公司签署的open weights and American AI leadship，但那篇过于没有内容，这篇好歹还算有点内容. 链接按序放在附件里，有需要请自取~

#### [2026-07-26 · 月底分享之自觉不错的paper第一篇](https://www.xiaohongshu.com/explore/6a64ed69000000001302fed9)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、大模型、文献阅读、科研学习、强化学习。
- 图号线索：3、4、15；采集记录：匿名隔离会话记录。
- 作者图集说明：图3不错，图4是本书，个人相对喜欢图15

#### [2026-07-26 · 月底分享之自觉不错的blog第一篇](https://www.xiaohongshu.com/explore/6a64d362000000001400514c)

- 图集：18 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：旧版用户 Chrome 记录（状态由当时参数标记）。
- 作者图集说明：图1是Alex Zhang最新的blog，我个人很看好RLMs的前景，所以经常推荐些相关内容，如果对RLMs有兴趣，这篇绝对不应该错过，质量非常非常高；图2非常长，但就讲了deep dive into TPU and GPU一件事；图3 intro late interaction；图4 最近的misalignment案例分析合集；图5 intro Lychee-FD，paper很不错；图6 knowledge base实践攻略. 图7如标题所示，非常好的探索，期待Dhruv Pai进一步挖掘；图8同名paper的blog，网页端可视化做得极好，配合阅读事半功倍；图9感觉尤其适合国外预算不那么充足的实验室（N卡有限，mac不少）；图10 Rethinking the Evaluation of Harness Evolution for Agents的blog；图11 intro DiligenceBench，从结果看anthropic家的几个都不擅长这个benchmark；图12主要是tongyi lab出了substack. 图13的观点我很赞同，autoresearch越发强大并不代表投资humans research没有价值，它们应该始终保持一种微妙的平衡；图14就一句，safety大有可为；图15 Tom Silver这篇短小精悍，对如何利用agents做研究大有帮助，十分推荐；图16 intro SAI；图17 world model实战指南；图18 一图流，OPD实际遇到的4个问题以及对应的解法. 链接按序放在附件里，希望各位能看到~

#### [2026-07-25 · 分享些近期自觉不错或有趣的projects](https://www.xiaohongshu.com/explore/6a64b2b6000000000f00beda)

- 图集：18 张；分类：`project`；标签：howto用好AI、人工智能、大模型、科研学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：匿名隔离会话记录。
- 作者图集说明：图1 只用简单一句就能知道它的厉害之处——fastest tokenizer for language modeling，如果在今天推荐的所有projects里只能推荐一个的话，毫无疑问我会选它；图2是Andrew Ng做的，有desktop app，感兴趣的可以试试；图3 SpaceXAI's terminal-based AI coding agent；图4 一个新的生图模型；图5 Prof. Freda Shi分享自己的skills；图6 协同工作的agents plugin. 图7 framework for Reinforcement Learning research；图8如果对PRIME-RL没兴趣，可以跳过；图9 Obsidian plugin，有需求的可以关注；图10 Ryan Lopopolo at OpenAI分享的harness engineering，非常值得关注；图11略；图12 OpenSpace更新了v2. 图13 Local-first system of record for documents for you and your agents，平平无奇；图14 coarse-grained cofolding model that can predict binding affinity，推荐给biotech相关领域的朋友；图15 native macOS workspace for running AI models locally on Apple silicon，还算好用；图16 Interpretable Causal Diffusion Language Models；图17 hierarchical agent loops with recursive self-organization；图18 Pi extension，对Pi没兴趣可以跳过. 链接按序放在附件里，不知道能否看见（才发现附件不支持markdown格式欸）

#### [2026-07-24 · 安利一篇很新鲜的适合入门rl的简要讲义](https://www.xiaohongshu.com/explore/6a6305aa000000000e035e4e)

- 图集：12 张；分类：`other`；标签：howto用好AI、人工智能、深度学习、大模型、强化学习。
- 图号线索：2、3、4、5、6、7、8、9、10、11、12；采集记录：匿名隔离会话记录。
- 作者图集说明：今天去找deeplearning for science school（图2）的slides时正巧发现Elynn Chen at NYU直接为本次summer school写了篇讲义，粗翻后觉得非常适合入门，所以分享出来. 我个人觉得只放篇讲义显得诚意略不足，所以刚好顺道推荐几本书和几门课[doge] 图3是Sutton那本Bible，图4是同样大名鼎鼎的AJKS，这两本个人认为属于必读；图5是Murphy写的rl book，目前还在完善阶段，相信假以时日这篇也会成为前两篇那样的经典；图6 Shiyu Zhao相比前三本更适合入门；图7 RLHF个人认为如果做LLMs相关，属于极其推荐的，可以配合Nathan Lambert录制的courses学习；图8和图9属于如果对rl theory感兴趣，想学的深一点的参考读物. 课程由易到难推荐三门：图10是Ali Bereyhi at Toronto Fall 2025的入门课，我记得也有课程视频；图11是Lucas Janson at Harvard Fall 2024的入门课，比前一门略难，他们自己写了教材，极度推荐；图12是Wen Sun at Cornell Fall 2024，难度比前两门大，但质量非常高，想深入学习的朋友不要错过. 以上除书籍（书都是开源免费的，很容易就能搜到）外链接按序如下： elynncc.github.io/rl-book/ dl4sci-school.lbl.gov/home bereyhi-courses.github.io/rl-utoronto/ lucasjanson.fas.harvard.edu/courses/CS_Stat_184_0.html wensun.github.io/CS6789_fall_2024.html

#### [2026-07-21 · 7月中旬自觉不错的paper推荐合集第七期](https://www.xiaohongshu.com/explore/6a5668a1000000001101cdc4)

- 图集：16 张；分类：`paper`；标签：howto用好AI、人工智能、科研学习、深度学习、大模型、文献阅读。
- 图号线索：11；采集记录：匿名隔离会话记录。
- 作者图集说明：个人相对喜欢图11 各位下轮更新见~~

#### [2026-07-20 · 7月中旬自觉不错的paper推荐合集第六期](https://www.xiaohongshu.com/explore/6a56680a000000000f015f5e)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、大模型、科研学习、文献阅读、强化学习。
- 图号线索：1、18；采集记录：匿名隔离会话记录。
- 作者图集说明：个人比较喜欢图1和图18

#### [2026-07-19 · 7月中旬自觉不错的paper推荐合集第五期](https://www.xiaohongshu.com/explore/6a5667830000000011005c9a)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、科研学习、文献阅读、大模型。
- 图号线索：18；采集记录：匿名隔离会话记录。
- 作者图集说明：个人相对喜欢图18

#### [2026-07-19 · 7月中旬自觉不错的blog推荐合集第五期](https://www.xiaohongshu.com/explore/6a5664ca000000001003c9a1)

- 图集：16 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16；采集记录：匿名隔离会话记录。
- 作者图集说明：图1 Shilong Liu对self-evolving agents的解析极其透彻，非常推荐各位找来这篇读读；图2不多说，我个人认为不读Lilian Weng她的blog的唯一原因是不感兴趣；图3讲的事情很简单：人们越来越多地以agents而非chatbots的形式使用ai；图4 同名paper的blog；图5又是一个benchmark；图6作者把autonomy分为5 level，并认为每一级有其最佳应用场景. 图7全文围绕标题展开；图8 自家产品安利帖，但记录得还算详细，有一定阅读价值；图9如其名所示的实战记录帖；图10 非常好项目；图11 results on the extent to which we can predict value changes from post-training data are somewhat inconclusive；图12我个人觉得最有价值的结论是这条：Open models, and GLM 5.2 in particular, are now able to handle even the highest level of task difficulty. 图13 huggingface出的新闻聚合网站，挺不错的；图14 同名paper的blog，这个benchmark里minimax m3表现倒廷亮眼的；图15 同名paper的blog；图16 intro Prism.

#### [2026-07-18 · 7月中旬自觉不错的paper推荐合集第四期](https://www.xiaohongshu.com/explore/6a566730000000001102f8b7)

- 图集：18 张；分类：`paper`；标签：人工智能、科研学习、大模型、文献阅读、深度学习。
- 图号线索：1、13；采集记录：匿名隔离会话记录。
- 作者图集说明：图1就是一本书，个人相对喜欢图13

#### [2026-07-18 · 7月中旬自觉不错的blog推荐合集第四期](https://www.xiaohongshu.com/explore/6a565b0e000000000f017ed4)

- 图集：17 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：匿名隔离会话记录。
- 作者图集说明：图1intro FastAFD，来自Hao AI Lab，效果看上去非常好；图2 Boaz Barak从safety角度设想了2030的bad scenarios，但他同样主张不应该因噎废食，而是要更好地发展ai以及提升整个社会对ai的适应力，推荐对ai safety感兴趣的朋友读；图3 intro OGPO (Off-Policy Generative Policy Optimization)；图4证明了特化模型在特定任务中的存在价值；图5建议结合之前推荐的4 bit lesson一块读；图6 The Gap Map helps us identify the blanks that need to be filled in, and collaborators to build with. 图7 非常建议找来阅读，尤其是想在业界打拼的朋友；图8是AMD带货贴（笑；图9 intro AutoMem，blog做了非常直观的可视化；图10非常长，但内容很简单，就是ai coding的实战记录；图11 intro Sheaf-ADMM；图12是async RL实战记录. 图13结论是intelligence and pro-social behavior may be weakly coupled: separable in theory, yet statistically correlated in practice，论述很有意思，推荐阅读；图14非常长，但观点很鲜明：ai 2040一片光明；图15想法和实验设计都很漂亮；图16是Pi 安利帖；图17的测试结果表面，至少目前还不能完全自动化.

#### [2026-07-17 · 7月中旬自觉不错的paper推荐合集第三期](https://www.xiaohongshu.com/explore/6a56668d000000000f0077bf)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、大模型、文献阅读、科研学习。
- 图号线索：9；采集记录：匿名隔离会话记录。
- 作者图集说明：个人比较喜欢图9

#### [2026-07-17 · 7月中旬自觉不错的blog推荐合集第三期](https://www.xiaohongshu.com/explore/6a564f4700000000110125f0)

- 图集：18 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：匿名隔离会话记录。
- 作者图集说明：图1记述了使用NVFP4的bitter lesson，质量非常高，推荐感兴趣的找来读；图2 个人感兴趣的rlm相关应用；图3的思路很有意思，期待作者们的正式paper；图4和图5都是同名paper的blog；图6观点并不新奇，但如何做到就是另一回事. 图7和图8都是同名paper的blog；图9 ICML 2026 Tutorial on calibration, decision calibration, multicalibration, and related ideas in learning，感兴趣的可以关注；图10 intro Toolathlon-Verified，自述变化很大；图11整个实验加起来才几十刀，cheap才是它最大的价值；图12这篇虽然在社交网络上引起轰动，但还是要说这和主观意识是两回事. 图13 intro Iterative RandOpt，值得关注；图14 The Power of Power Law的blog，写得很清晰，直接看blog就好；图15直接看就行；图16 Mark Riedl分hard take-off，soft take-off and no take-off三种情况进行论述AI capabilities的未来发展轨迹，作者认为当下更接近no take-off的情况，对safety来说是好事；图17 intro Decomposer，极其有意思的研究，推荐感兴趣的关注；图18是作者系列blog的第一篇，也是最基础的部分，对rl感兴趣的可以持续关注.

#### [2026-07-16 · 7月中旬自觉不错的paper推荐合集第二期](https://www.xiaohongshu.com/explore/6a566604000000001102f65a)

- 图集：18 张；分类：`paper`；标签：人工智能、深度学习、科研学习、文献阅读、大模型。
- 图号线索：1、3；采集记录：匿名隔离会话记录。
- 作者图集说明：个人喜欢图1和图3

#### [2026-07-16 · 7月中旬自觉不错的blog推荐合集第二期](https://www.xiaohongshu.com/explore/6a564049000000000f03266d)

- 图集：17 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：匿名隔离会话记录。
- 作者图集说明：图1 非常好的一篇dllm教程，原理讲解得十分透彻，非常推荐感兴趣的朋友们读；图2结论是PorTAL is substantially more data efficient. It matches per task LoRA's best accuracy using roughly half the data, and consistently beats it in the high data range；图3 一句话总结是harness远比人们想象中重要；图4这系列blog推荐给对numerical optimization感兴趣的朋友，每篇篇幅都不短，我个人并没有读完；图5是Meta出的benchmark，可以稍微看看；图6 JEPA家族新成员. 图7是对Meituan Longcat 2 sparse attention的拆解；图8 a collection of language-specialized fine-tuned Whisper-large-v3 models adapted for ASR in 102 languages；图9讲的是用FTPO reduce doom loops比用repetition_penalty效果好；图10 可以一试；图11 intro Personascope；图12 同名paper的blog，可视化做得非常好，推荐直接看blog. 图13 autoresearch实战记录；图14 比较基础的一篇blog，不了解GPU原理的可以看看；图15 DSpark的详细拆解贴，写得不错，但个人觉得最主要的目的是安利自家的Muse Spark；图16 Thinking Machines再次重申自己的理念，多提一嘴，这两天还看见Yoshua Bengio转的几百名学者联合签名的We Must Act Now，个人对此的感觉是如何让ai更好地推动人类社会繁荣是件挺重要但也挺难提出足够好方案的议题；图17 Anthropic自测还挺有意思的，感兴趣的可以一读.

#### [2026-07-15 · 7月中旬自觉不错的paper推荐合集第一期](https://www.xiaohongshu.com/explore/6a56657c000000000f031ef7)

- 图集：18 张；分类：`paper`；标签：人工智能、科研学习、大模型、深度学习、文献阅读、大语言模型。
- 图号线索：10、17；采集记录：匿名隔离会话记录。
- 作者图集说明：个人比较喜欢图10和图17

#### [2026-07-15 · 7月中旬自觉不错的blog推荐合集第一期](https://www.xiaohongshu.com/explore/6a563405000000000f029c77)

- 图集：18 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：匿名隔离会话记录。
- 作者图集说明：图1是Arvind Narayanan在ICML上演讲的文字稿，核心观念依然是拥抱AI，拥抱变化；图2是篇对J-lens的拆解，结论并不新鲜——LLMs并不存在主观意识，内容挺不错的；图3 intro Morpheus；图4 intro CrashTwin, a physics-grounded evaluation framework；图5 intro ASPIRE (Agentic Skill Programming through Iterative Robot Exploration)；图6 同名paper的blog，个人更推荐直接看blog. 图7认为给定算力条件/tokens预算下做benchmark并不一定能反映models的真实水平，应该分算力档位测试；图8很有意思，把人体当机器来介绍，读完让人不得不感慨人体的精妙；图9结论明确：Building resilient harnesses shifts the evaluation focus from “can it pass this test?” to “can it reliably solve this problem；图10其实是GQE安利帖；图11是安利prime-rl，个人也非常喜欢这个平台；图12 intro Block-Sparse Featurizers (BSF). 图13 intro SWE1.7,稍微关注下就行；图14 intro Muse Spark1.1，至少从测试结果看，进步非常明显；图15文章不长，但非常精巧，非常推荐找来读；图16 intro SciReasoner；图17依旧是同名 paper的blog，个人依旧更推荐直接看blog；最后图18给大家来点心灵鸡汤，这篇鸡汤写得非常好，尤其推荐给对当下感到焦虑的朋友们，有时候人还是要阅读些温暖的文字的.

#### [2026-07-14 · 7月中旬自觉不错或有趣的projects推荐合集](https://www.xiaohongshu.com/explore/6a561c8000000000110052ed)

- 图集：18 张；分类：`project`；标签：howto用好AI、人工智能、科研学习、大模型、实用工具。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：匿名隔离会话记录。
- 作者图集说明：图1 langchain-ai做的非常有帮助，个人觉得是同类项目里完成度最高的，十分推荐；图2 open-source AI workbench for scientific research，整合度还行，对尚未开启autoresearch的朋友来说可能会很有帮助；图3 实质依然是markdown editor，只不过原生支持ai agent，app版目前仅支持macOS；图4来自Google，Tabular Foundation Model；图5 CLI tool for deterministic routing of queries between local and hosted LLM models，对比同类也算有点特色，但依然大同小异；图6 有需求的可以关注. 图7来自nVidia，相见恨晚，很实用的小工具；图8 a meta-harness agent IDE for running AI coding agents in parallel；图9 总共收集了3722篇，推荐给biotech相关领域的朋友们；图10 A SOTA quantization algorithm for high-accuracy low-bit LLM inference，持续更新中，个人感觉值得关注；图11 high-performance inference engine for AI models；图12非常有意思的项目. 图13看着挺有用的，但实际上每个agent常用的skill就那么些，安装得过多反而影响效率；图14 build academic conference posters，实用的小工具；图15 SciML的经典项目；图16 伟大无需多言，与图1并列为最推荐的projects；图17 multiplayer, self-hosted, secure agents，对商业领域可能比较友好，个人兴趣不大；图18 open-source, markdown-first documentation，个人并没有用过，因此暂不作评论.

#### [2026-07-05 · 七月初自觉不错的paper推荐合集第六期](https://www.xiaohongshu.com/explore/6a42a1240000000011010bb7)

- 图集：10 张；分类：`paper`；标签：人工智能、大模型、科研学习、深度学习、文献阅读。
- 图号线索：1、9；采集记录：匿名隔离会话记录。
- 作者图集说明：图1和图9都蛮有意思的. 各位下轮更新见~

#### [2026-07-05 · 七月初自觉不错的blog推荐合集第六期](https://www.xiaohongshu.com/explore/6a429c51000000000f01e500)

- 图集：13 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13；采集记录：匿名隔离会话记录。
- 作者图集说明：图1非常期待作者们的StudyBench正式成文，这篇blog也是我这一个周期最喜欢的之一，非常推荐各种有空时读读；图2 同名paper的blog，很棒的研究；图3 很有意思也很有意义的研究，既说明人类在某一些智力任务仍具备优势，又说明agent依然拥有广阔进步空间；图4 同名paper的blog；图5是对BFS-Prover-V2的推荐；图6随便看看就好. 图7个人觉得很有用，如何share your work很多时候比how you do your work更重要（起码是在功利维度上；图8很棒的内容，核心观点是good benchmark will genuinely reflect progress on capabilities people thought it measures；图9 parameter decomposition实战记录贴. 图10 distributed AI inferencer入门；图11是vllm-skills的安利帖，但思路是通用的；图12真手把手教，每一步的图例都很具体，非常推荐给新人；图13作者对ai review的理解很到位，同时也提出了改进措施，对相关领域感兴趣的可以一看.

#### [2026-07-04 · 七月初自觉不错的paper推荐合集第五期](https://www.xiaohongshu.com/explore/6a42a097000000000f02b56f)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、深度学习、科研学习、文献阅读。
- 图号线索：1；采集记录：匿名隔离会话记录。
- 作者图集说明：有不少paper已经推荐过blog，这里原本是不想重复的，但图1很值得再次推荐.

#### [2026-07-04 · 七月初自觉不错的blog推荐合集第五期](https://www.xiaohongshu.com/explore/6a42946b000000001102c157)

- 图集：16 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16；采集记录：匿名隔离会话记录。
- 作者图集说明：图1非常好的theory blog，大爱Andrew Gordon Wilson，非常推荐感兴趣的朋友们读；图2推荐给脑科学领域的朋友；图3 同名paper的blog；图4观点明确 topology can help implement reliability, but it does not create reliability；图5作者面对we can understand llm or can not的选择是更偏向can not 的or；图6推荐给对infra感兴趣的朋友. 图7讨论的很不错，就是读完跳转follow让人无语；图8 同名paper的blog；图9 同名paper的blog，非常有意思的benchmark；图10又是同名paper的blog；图11非常好质量，推荐给对Cybersecurity Evals感兴趣的朋友；图12某种程度上是其他学科积极应对ai impact的表现. 图13是乐观派，主张把决策权交给ai，我持保留意见；图14呼吁theory-driven development，且一看；图15是NeMo AutoModel安利帖；图16 intro forward self-models，期待作者们的进一步研究.

#### [2026-07-03 · 七月初自觉不错的paper推荐合集第四期](https://www.xiaohongshu.com/explore/6a429fc600000000110163c5)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、文献阅读、深度学习。
- 图号线索：3、15；采集记录：匿名隔离会话记录。
- 作者图集说明：个人比较喜欢图3和图15.

#### [2026-07-03 · 七月初自觉不错的blog推荐合集第四期](https://www.xiaohongshu.com/explore/6a428b96000000000f015418)

- 图集：16 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16；采集记录：匿名隔离会话记录。
- 作者图集说明：图1是本地人的首尔游玩攻略，众所周知开会最重要的是要吃好玩好（；图2 KV cache compression攻略帖；图3 DiPOD的blog；图4是目前最好的video models intro，正在更新中，感兴趣的推荐持续关注；图5有意思的研究，同时可视化做得也很棒；图6是parameter-efficient fine-tuning的安利帖. 图7 intro Shadow-Frog；图8如标题所示；图9 Can Scale Save Us From Plasticity Loss in Large Language Models的blog；图10又是同名paper的blog，质量很高很推荐；图11是Ben Recht对Dimitri Bertsekas的悼念，又想起当年读Introduction to Probability的时光，唉；图12这本书看就对了. 图13 intro Ornith-1.0；图14受Alisa和Silvia那两篇业界求职攻略的启发写的（我都推荐过），本文写得也很出色，尤其是他的几个发现应该会对想去业界的朋友很有帮助；图15非常好工作，建议全球学术界引入（自然是不可能的；图16推荐给对Physical AI感兴趣的朋友.

#### [2026-07-02 · 七月初自觉不错的paper推荐合集第三期](https://www.xiaohongshu.com/explore/6a429f4b000000000f01ea62)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、深度学习、文献阅读。
- 图号线索：1、3；采集记录：匿名隔离会话记录。
- 作者图集说明：图1研究很推荐；个人喜欢图3.

#### [2026-07-02 · 七月初自觉不错的blog推荐合集第三期](https://www.xiaohongshu.com/explore/6a4283110000000011007691)

- 图集：17 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：匿名隔离会话记录。
- 作者图集说明：图1是Alisa Liu写的如何在业界求职的攻略，非常推荐；图2作者的担忧有一定道理，但这种微妙的平衡确实在现实中难以把握；图3 openai提出的deployment simulation挺好的，但我不看好frontier labs会跟进；图4提出个有趣的问题，但并没有一个有趣的解答，遗憾；图5看似写得很长，但结论很简单：RL training system matters；图6安利DFlash with Spec V2. 图7谈得很深，作者认为ai会涌现出something consciousness-like；图8 framework for long-horizon autonomous tasks；图9推荐给对AI security感兴趣的朋友们；图10 同名paper的blog，个人更喜欢读blog；图11 intro FAPO (Fully Automated Prompt Optimization)；图12论述speculative decoding的优势. 图13同名paper的blog，非常有意思的bench；图14 Decompose-K实战记录帖；图15 同名paper的blog，DiT的bench应该更繁荣才对；图16分析得很棒，结论design capability + interpretability matter；图17是那篇Comparing Transformers and Hybrid Models at the Token Level的blog.

#### [2026-07-01 · 七月初自觉不错的paper推荐合集第二期](https://www.xiaohongshu.com/explore/6a429e9000000000110043f1)

- 图集：18 张；分类：`paper`；标签：人工智能、大模型、科研学习、文献阅读、深度学习。
- 图号线索：1、12、16；采集记录：匿名隔离会话记录。
- 作者图集说明：个人比较喜欢图1和图12；图16那本书个人认为写得并不算特别出彩，但胜在结构完整，感兴趣的也可找来看.

#### [2026-07-01 · 月末到七月初自觉不错的blog推荐合集第二期](https://www.xiaohongshu.com/explore/6a4279da000000000f01566a)

- 图集：17 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、深度学习、科研学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17；采集记录：匿名隔离会话记录。
- 作者图集说明：图1应该是最近最热门的一篇tech blog，没什么多讲的，Lilian Weng出品的每一篇都是必读推荐；图2结论明确：our metrics suggest that accuracy on a multimodal benchmark does not directly mean there’s evidence of multimodal reasoning；图3 intro ReplaySSM，质量极高非常推荐；图4同名paper的blog；图5实质是OpenHands的安利；图6 intro Target-SFT，依旧是同名paper的blog，我觉得blog的可视化做得好所以推荐直接读blog. 图7如其名，超极简llm book，适合用来复习知识；图8如其名，就是论述W4A4在Voice Clone场景下的优势；图9针对behavioural science的llm checklist；图10 同名paper的blog；图11又是出自FrontisAI，质量很棒的研究；图12也是同名paper的blog. 图13又是我个人喜欢的rlm相关；图14是那篇知名的ELF的延申，intro ELF with progressive distillation，质量依旧很高；图15 optimisation相关；图16 intro IW-OPD；图17如标题所示，简述tpu结构和机制的.

#### [2026-06-30 · 六月末自觉不错的paper推荐合集第一期](https://www.xiaohongshu.com/explore/6a429d57000000001003f063)

- 图集：18 张；分类：`paper`；标签：人工智能、科研学习、深度学习、大模型、文献阅读。
- 图号线索：1、14；采集记录：匿名隔离会话记录。
- 作者图集说明：个人比较喜欢图14；图1的效果非常好，可以关注.

#### [2026-06-30 · 六月末自觉不错的blog推荐合集第一期](https://www.xiaohongshu.com/explore/6a425bde00000000110128e1)

- 图集：18 张；分类：`blog`；标签：howto用好AI、人工智能、大模型、科研学习、深度学习、强化学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16、17、18；采集记录：匿名隔离会话记录。
- 作者图集说明：图1非常好研究，FrontisAI不错；图2是Stanford一位老师写的，他对ai impact持较为悲观的看法，并给出了自己的应对建议；图3是极好的World-Action Models intro，深入浅出，表达清晰，非常推荐感兴趣的朋友找来读；图4作者是Columbia的数学教授，核心观点是ai impact会导致数学研究的knowledge collapse，了解下其他领域人的看法我个人感觉是很有益的；图5 intro Brain, a self-improving memory system；图6如标题所示. 图7 A benchmark for honkaku deduction，Fable 5无悬念夺冠，挺有创意的；图8研究非常有意思，blog的视觉展现也很棒，甚至会让人下意识怀疑是不是进错网站，推荐各位找来看；图9同名paper的blog版；图10大概是目前最全面的 intro agentic-rl blog，虽然很长但质量很好；图11 intro Krea2；图12虽然核心目的是安利自家的prime-rl 0.6，但blog本身挺有料的. 图13 intro OSWorld 2.0，等了两年终于出了2.0；图14同名paper的blog，个人觉得blog更直观更好理解；图15 training Java code migration agent实战记录；图16作者Nishanth毕业于MIT Robotics，现就职于Meta，非常推荐想去业界的朋友看看这篇；图17 intro Un-0；图18 作者做了SFT和RL的对比实验，结论是Tasks with dense, linearly separable signal want SFT. Tasks where the right features are present in the base model and what is missing is search, sequencing, or calibration want RL.

#### [2026-06-29 · 六月末自觉不错的projects推荐合集](https://www.xiaohongshu.com/explore/6a424dc000000000070103b6)

- 图集：16 张；分类：`project`；标签：howto用好AI、人工智能、大模型、大语言模型、科研学习。
- 图号线索：1、2、3、4、5、6、7、8、9、10、11、12、13、14、15、16；采集记录：匿名隔离会话记录。
- 作者图集说明：图1是个挺有趣的项目，可以搜某个感兴趣的人是否在各个LLM的weights里；图2来自ai2，paper里的测试效果非常好，推荐关注；图3相较于同类项目，最大优势是节约tokens，其他特性中规中矩；图4 the first multi-domain generative framework built on a unified scientific grammar，非常好项目；图5 an open-source block diffusion reasoning model designed for complex mathematical reasoning and code generation，感兴趣的可以读他们的paper；图6感兴趣的推荐尝试. 图7简单易用的optimization research工具；图8 agent-native collaborative workspace for human + agent teams，这些协作工具也挺多的。找个看着顺眼的即可；图9帮助LoRA调试的小工具；图10来自microsoft，可以预估任意model在benchmark中的成绩，极为推荐，具体机制建议看他们的paper；图11看看就好；图12来自baidu，同样是极为推荐试试的项目. 图13的质量非常高，作者收集了非常多高质量的agents evaluation相关的资源，货真价值的awesome；图14 the recursive language model cli agent，rlm生态再次加一；图15干中学的一个项目，想做agent的可以用来学习；图16来自nVidia，toolkit for analyzing PyTorch model graphs, converting them to einsum representations, and performing hardware-aware SOL performance predictions.

#### [2026-06-21 · 月中下旬自觉不错的paper推荐合集第六期](https://www.xiaohongshu.com/explore/6a2fe53800000000080246c1)

- 图集：11 张；分类：`paper`；标签：人工智能、科研学习、深度学习、文献阅读、强化学习。
- 图号线索：7；采集记录：匿名隔离会话记录。
- 作者图集说明：个人喜欢图7 哦对了，Allen Liu最近入职了nyu，他那篇learning theoretic foundations of understanding quantum systems非常好，感兴趣的可以找来读. 各位7到10天后见~




## 逐张视觉核验图像来源与内容（截至当前 127/1,581 张）

已直接由多模态视觉阅读的图像包括先行样例、作者点名推荐或特别说明的图，以及继续顺序核对的图。标题、署名、arXiv 编号和项目地址按图内可见内容记录；摘要是对图面文字与摘要的归纳，不代表独立复核论文全文或实验结果。没有调用专用 OCR。原始 Xiaohongshu 笔记链接不含分享 token。

| 笔记来源 / 图号 | 图中材料标题 | 图中署名 / 机构 | 来源标识 / 可见入口 | 图面内容摘要 | 核验范围 |
|---|---|---|---|---|---|
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图1 | ScienceIDE: Turning World’s Scientific Codebase into Agent Learnable Environments | Hejia Geng et al. (AITonomy Foundation and research collaborators) | [arXiv:2609.19134v1](https://arxiv.org/abs/2609.19134) | 把科学软件仓库改造成可执行、可验证的 agent 学习环境，并据此训练科学代码模型 PhAI-IDE。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图2 | Know When to Stop, Where to Restart: Accelerating Multi-Turn Agentic On-Policy Distillation | Zhiyu Gui et al. (University of Science and Technology of China; Ant Group) | [arXiv:2609.14636v1](https://arxiv.org/abs/2609.14636) | 提出 STRIDE，以自适应提前停止和 prefix buffer 减少多轮 agent OPD 中低价值 rollout，并从最弱轮次恢复采样。 | 顺序核对 |
| [2026-09-24 · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图3 | Lightning Weave: Improving the Accuracy-Efficiency Frontier of Reasoning Models through Capability Composition | Yecheng Wu; Song Han; Han Cai (MIT; NVIDIA) | [arXiv:2609.14708v2](https://arxiv.org/abs/2609.14708)<br>[https://github.com/jet-ai-projects/Lightning-Weave](https://github.com/jet-ai-projects/Lightning-Weave) | 以 on-policy distillation 抽取准确率导向和效率导向 anchor models 的互补能力，在同一 student 中组合能力以改善推理准确率—token 效率前沿。 | 作者点名图 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图4 | Forty Shades of Blue: Quality-Diversity Alignment via Mode-Conditioned Reinforcement Learning | Jiayi Yuan; Hangoo Kang; James Jihao Liu; Yejin Choi; Vikram Iyer; Liwei Jiang; Natasha Jaques (University of Washington; Stanford University) | [arXiv:2609.14896v1](https://arxiv.org/abs/2609.14896)<br>[https://github.com/yuanjiayiy/mode-conditioned-diversity-alignment](https://github.com/yuanjiayiy/mode-conditioned-diversity-alignment) | 提出 MoDA，以 mode-conditioned policy 与质量门控奖励同时优化输出质量和多样性，缓解 RL 对齐造成的 mode collapse。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图5 | SoL-Pi: Recursively Scaling Auto-Research Loops for Efficient Agent Harness | Haozhe Liu et al. (NVIDIA; NTU; MIT) | [arXiv:2609.20519v1](https://arxiv.org/abs/2609.20519)<br>Code and blog-post badges visible on paper | 用自研究循环搜索并筛选 harness 改动，将保留的机制集成到 SoL-Pi，以较低 token/API 成本提升 agent harness。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图6 | Block Parallelism for Efficient Distributed Long-Context Diffusion Language Model Training | Tarun Suresh; Pranshu Chaturvedi; Hangoo Kang; Parth Shroff; Ishan S. Khare; Hermann Kumbong; Azalia Mirhoseini (Stanford University) | [arXiv:2609.19242v1](https://arxiv.org/abs/2609.19242)<br>[https://github.com/ScalingIntelligence/Turbo-dLLM](https://github.com/ScalingIntelligence/Turbo-dLLM) | 提出 Context-Shared Block Parallelism，把不同 corruption block 的计算分配到不同 rank，同时共享干净上下文以扩展长上下文 dLLM 训练。 | 顺序核对 |
| [2026-09-24 · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图7 | Parallelism, Critical Windows, and Separations among Diffusion Language Models | Sitan Chen (Harvard); Liye Wang (Tsinghua) | [arXiv:2609.20539v1](https://arxiv.org/abs/2609.20539) | 理论比较 masked、uniform 与 Gaussian diffusion LLM 的并行采样能力，分析生成所需前向步数、分布复杂度与 critical windows 的关系。 | 作者点名图 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图8 | GPU-Accelerated Presolving for Linear Programming | Daniel Cederberg; Stephen Boyd (Stanford University) | [arXiv:2609.16182v1](https://arxiv.org/abs/2609.16182) | 把线性规划 presolve 阶段从 CPU 移至 GPU 并并行化，报告在两个基准集上相对原流程显著缩短预处理时间。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图9 | Osprey: Target-Agnostic Pre-Training Makes Stronger Drafters in Speculative Decoding | Fengxiang Bie et al. (Together AI; University of Sydney; UT Austin; UIUC) | [arXiv:2609.09338v1](https://arxiv.org/abs/2609.09338)<br>[https://github.com/LeanModels/Osprey](https://github.com/LeanModels/Osprey) | 先训练可复用的小型 draft model，再按 target model 对齐词表与分布；目标是减少每个 target 单独训练 drafter 的成本并提高跨域接受长度。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图10 | Popular Knowledge Propagates More Errors in LLM Knowledge Updating | Yuji Zhang; Weibing Wang; Cheng Qian; Duo Zhou; Dilek Hakkani-Tür; Kathleen McKeown; Chengxiang Zhai; Heng Ji | [arXiv:2609.08067v1](https://arxiv.org/abs/2609.08067)<br>[https://factprop.github.io/FACTPROP/](https://factprop.github.io/FACTPROP/) | 研究知识更新时的连带错误，发现高连接度的热门事实更易受邻近更新影响；提出 PopAnchor 以少量热门样本回放减轻遗忘。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图11 | Environments as Scaffold: Enriching Feedback to Bootstrap Self-Evolving Agents in Long-Horizon Tasks | Hongbang Yuan; Zhuoran Jin; Yixin Cao (Fudan University; CASIA; Shanghai Innovation Institute) | [arXiv:2609.08404v1](https://arxiv.org/abs/2609.08404)<br>[https://github.com/HongbangYuan/EnvAsScaffold](https://github.com/HongbangYuan/EnvAsScaffold) | 提出 feedback-enriched environments，把部分 action guidance 改造成环境观察反馈，帮助长程 agent 探索并把环境提示内化进策略。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图12 | PlayTrain: An Efficient Reinforcement Learning Framework for LLM-Generated Adaptable JavaScript Games | Ryan Truong; Lance Ying; Samuel J. Gershman; Kazuki Irie (Harvard; MIT; Yale) | [arXiv:2609.09059v1](https://arxiv.org/abs/2609.09059)<br>[https://github.com/heyodog0/playtrain](https://github.com/heyodog0/playtrain)<br>[https://playtrain.org](https://playtrain.org) | 让 LLM 从简短提示生成 JavaScript 游戏环境，再用统一 gym 风格接口训练 RL agent；强调环境创建、修改和交互效率。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图13 | Exact-Form Regret for Gradient Descent, Mirror Descent and Follow-the-Regularized-Leader | Ashkan Soleymani; Gabriele Farina; Patrick Jaillet (MIT) | [arXiv:2609.09466v1](https://arxiv.org/abs/2609.09466) | 以精确势函数刻画在线梯度下降、镜像下降和 FTRL 的偏离与 regret，提出统一几何解释。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图14 | AuK Technical Report: An Open-Source Foundational Model for Speech Generation and Editing | Authors not shown on the visible title page; Shanghai Jiao Tong University and Tencent Hunyuan marks visible | [arXiv:2609.08936v1](https://arxiv.org/abs/2609.08936) | 介绍统一语音生成与编辑的开源基础模型，覆盖语音生成、内容编辑、增强和分离，并报告蒸馏后的 AuK-Flash 推理加速。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图15 | How to Guide Your Language Flow | Rohit Dilip; Tianrong Chen; Yuyang Wang; David Van Valen; Josh Susskind; Miguel Angel Bautista (Apple; Caltech) | [arXiv:2609.19356v1](https://arxiv.org/abs/2609.19356) | 提出 probe guidance：利用冻结扩散模型的内部状态构造 guidance signal，在不额外增加推理前向的情况下改善连续扩散语言模型生成。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图16 | Radio-Frequency Convolutional Neural Networks | Zhihui Gao; Shi-Yuan Ma; Yiran Chen; Dirk Englund; Tingjun Chen (Duke University; MIT Lincoln Laboratory) | [arXiv:2609.19279v1](https://arxiv.org/abs/2609.19279) | 把无线设备既有的 RF frequency mixer 重新用于 CNN 卷积推理，让部分边缘端神经网络计算借助通信硬件完成。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图17 | Living with AI Companions: Sustained AI Companionship Predicts Lower Well-Being Through Lower Human Interaction | Yutong Zhang; Dora Zhao; Yixin Wang; Rebecca Anselmetti; Jeffrey T. Hancock; Robert Kraut; Diyi Yang (Stanford; CMU; Michigan; Oxford) | [arXiv:2609.07243v1](https://arxiv.org/abs/2609.07243) | 两波纵向研究发现，持续的 AI 陪伴互动与较低 wellbeing 相关，路径主要与线下人际互动减少有关；研究包括基线 1,182 人及 12 个月后 439 人随访。 | 顺序核对 |
| [ · 6aaffe610000000026023b58](<https://www.xiaohongshu.com/explore/6aaffe610000000026023b58>) · 图18 | DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression | DeepSeek-AI | [https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash) | 介绍 DeepSeek-V4.1-Flash 的 Causal Encoder-Decoder 与跨层 KV 复用/压缩设计，目标是在长上下文 agent 负载下降低 KV cache 内存与带宽开销。 | 顺序核对 |
| [ · 6aaff0e30000000029012e7e](<https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e>) · 图1 | Training Search Agents with GRPO | Jasper Lu | 图内未见可稳定抄录的链接 | 实践式博客记录如何用 GRPO 训练 search agent，按数据集、harness、reward、探索与训练超参逐步拆解实验过程。 | 顺序核对 |
| [ · 6aaff0e30000000029012e7e](<https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e>) · 图2 | Discrete Beckmann Transport Models for One-Step Language Modeling and Reasoning | Sophia Tang; Shiyi Wang (University of Pennsylvania; Harvard; Kempner Institute; IAIFI) | 图内未见可稳定抄录的链接 | 以离散 Beckmann transport 与 transport map 为框架，讨论一步语言建模和推理，把生成表示为将初始状态映射到目标分布。 | 顺序核对 |
| [ · 6aaff0e30000000029012e7e](<https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e>) · 图3 | JustRL II: Scaling Small LLMs to 128K Reasoning with a Critic | MiniCPM RL Team | 图内未见可稳定抄录的链接 | 介绍为小型 LLM 配置 critic-equipped GRPO 以稳定长链推理训练，并展示 128K 上下文与多项 benchmark 的收益。 | 顺序核对 |
| [ · 6aaff0e30000000029012e7e](<https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e>) · 图4 | The AI-as-Normal-Technology View of Loss-of-Control Incidents | Sayash Kapoor; Arvind Narayanan | 图内未见可稳定抄录的链接 | 提出介于网络安全与 AI safety 社群之间的视角，讨论近期 AI agent 失控/越权事件、风险解释和应对方式。 | 顺序核对 |
| [ · 6aaff0e30000000029012e7e](<https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e>) · 图5 | A Year of Hacking with LLMs | Edward Z. Yang (researcher; page author inferred from visible site context, verify before citation) | [https://github.com/edwardzpeng/presentations/tree/main/offbyone%202026](https://github.com/edwardzpeng/presentations/tree/main/offbyone%202026) | 作者回顾一年将 LLM 用于网络安全研究的经验，包括漏洞分析、PoC 生成与设备验证；图中强调能力演进和研究工作流变化。 | 顺序核对 |
| [ · 6aaff0e30000000029012e7e](<https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e>) · 图6 | AHA: Looped Transformer — an open atlas of recurrent computation, adaptive depth, and latent reasoning | AHA / Looped Transformer project | 图内未见可稳定抄录的链接 | 项目站点汇集 recurrent computation、adaptive depth 与 latent reasoning 相关论文，并以 SMELT 等条目作索引。 | 顺序核对 |
| [ · 6aaff0e30000000029012e7e](<https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e>) · 图7 | DeepSeek-V4.1-Flash architecture explainer | DeepSeek-AI technical-report explainer | 图内未见可稳定抄录的链接 | 架构图展示 Causal Encoder/Decoder、MoE、Compressed Sparse Attention 2、SWA、单遍 mHC、Engram 与层级稀疏索引等模块。 | 顺序核对 |
| [ · 6aaff0e30000000029012e7e](<https://www.xiaohongshu.com/explore/6aaff0e30000000029012e7e>) · 图8 | A step change in AI’s job readiness | NeoCognition research group (page author list not in captured section) | 图内未见可稳定抄录的链接 | 讨论 AI agents 能否在真实软件环境中端到端承担知识工作、持续从工作中学习，以及现有 benchmark 对真实岗位准备度的覆盖缺口。 | 顺序核对 |
| [2026-09-23 · 6aaffdc00000000029011577](<https://www.xiaohongshu.com/explore/6aaffdc00000000029011577>) · 图1 | Rethinking Critic Learning in PPO: Understanding and Mitigating Value Flattening | Yizhuo Li; Jianhao Yan; Yun Luo; Zhi Wang; Futing Wang; Rong-Xi Tan; Kanghui Tian; Ganqu Cui; Ning Ding; Peilin Zhao; Yafu Li; Yu Cheng (Shanghai Jiao Tong; Shanghai AI Laboratory; Westlake; Nanjing University; CUHK) | [arXiv:2609.18708v1](https://arxiv.org/abs/2609.18708)<br>[https://github.com/Dodojordi/SP3O](https://github.com/Dodojordi/SP3O) | 分析 PPO critic 的 Value Flattening：不同中间状态的 Monte Carlo value 变化显著而 critic 预测趋平；提出 Sparse Proximal Policy Optimization (SP³O)，只在少量分散状态监督 value 以减轻问题。 | 作者点名图 |
| [2026-09-23 · 6aaffdc00000000029011577](<https://www.xiaohongshu.com/explore/6aaffdc00000000029011577>) · 图2 | Modality-Autoregressive World-Action Models (ModAR) | Adam Hung; Bardienus P. Duisterhof; Deva Ramanan; Jeffrey Ichnowski (Carnegie Mellon University) | [arXiv:2609.17524v1](https://arxiv.org/abs/2609.17524)<br>[https://adamhung60.github.io/ModAR/](https://adamhung60.github.io/ModAR/) | 介绍一种模态自回归的世界—动作模型：先预测未来轨迹的 DINO 特征与深度，再预测动作，以统一未来预测与机器人控制。 | 顺序核对 |
| [2026-09-23 · 6aaffdc00000000029011577](<https://www.xiaohongshu.com/explore/6aaffdc00000000029011577>) · 图3 | Rethinking Heterogeneous System Disaggregation for Subquadratic Attention | 图中列出的 Harvard 与 NVIDIA 研究团队 | [arXiv:2609.13134v1](https://arxiv.org/abs/2609.13134) | 研究如何在异构计算系统间拆分注意力计算，将二次复杂度与次二次复杂度的操作分配到不同设备，以改善系统效率。 | 顺序核对 |
| [2026-09-23 · 6aaffdc00000000029011577](<https://www.xiaohongshu.com/explore/6aaffdc00000000029011577>) · 图4 | Breaking the Token Ceiling: Distilling Smaller, Stronger Byte Models | 图中列出的 University of Washington 与 Meta FAIR 研究团队 | [arXiv:2609.12303v1](https://arxiv.org/abs/2609.12303) | 探索以字节为单位建模，并通过 token 与 logits 转换设计蒸馏方法，训练更小而有竞争力的 byte-level 模型。 | 顺序核对 |
| [2026-09-23 · 6aaffdc00000000029011577](<https://www.xiaohongshu.com/explore/6aaffdc00000000029011577>) · 图8 | Matrix Spencer: Eight Standard Deviations Suffice and an Almost-Linear Time Algorithm for Dense Input | Zhao Song; Lichen Zhang | [arXiv:2609.15025v1](https://arxiv.org/abs/2609.15025) | 解决 Matrix Spencer discrepancy 问题，证明对称矩阵存在符号赋值使谱差异低于 8√n，并给出对稠密输入近乎线性的随机算法。 | 作者点名图 |
| [2026-09-22 · 6aaffd0e00000000260237d3](<https://www.xiaohongshu.com/explore/6aaffd0e00000000260237d3>) · 图7 | A note on goal-based hierarchical RL | Kevin Murphy | [arXiv:2609.14605v1](https://arxiv.org/abs/2609.14605) | 用 hierarchical hidden Markov model 统一 agent-centred goal/value 设计与内部 belief state：把目标也视作动态状态，并以 done 动作作为层级边界事件。 | 作者点名图 |
| [2026-09-22 · 6aaffd0e00000000260237d3](<https://www.xiaohongshu.com/explore/6aaffd0e00000000260237d3>) · 图18 | A Zeroth-Order Paradigm for LLM Preference Alignment | Peter Chen (UC Berkeley); Xi Chen (NYU); Wotao Yin (Damo Academy / Alibaba); Tianyi Lin (Columbia) | [arXiv:2609.19144v1](https://arxiv.org/abs/2609.19144) | 提出 comparison-oracle based 的零阶对齐方法 ComPO，从偏好比较对中提取方向信息而不直接优化可微 preference loss，并分析离线/在线方案的收敛条件。 | 作者点名图 |
| [2026-09-21 · 6aaffc600000000012035ed5](<https://www.xiaohongshu.com/explore/6aaffc600000000012035ed5>) · 图1 | Recurrent Looped Transformer (RLT) | Yifan Zhang | arXiv ID not shown in image<br>[https://github.com/yifanzhang-pro/recurrent-looped-transformer](https://github.com/yifanzhang-pro/recurrent-looped-transformer) | 把 encoder 构造的 KV memory 与逐 token 递归 decoder 结合，使 prompt 与 response 共享状态转移，探索长时深度、硬件执行与 RL 训练协同设计。 | 作者点名图 |
| [2026-09-21 · 6aaffc600000000012035ed5](<https://www.xiaohongshu.com/explore/6aaffc600000000012035ed5>) · 图4 | Eliciting Weak-to-Strong Generalization with On-Policy Reverse Distillation | Youngrok Park; Sangmin Bae; Hojung Jung; Jongwoo Ko; Yunseon Choi; Young Jin Kim; Pashmina Cameron; Aaron Courville; Se-Young Yun (KAIST; Microsoft; Toronto; Mila; Université de Montréal; CIFAR AI Chair) | [arXiv:2609.08798v1](https://arxiv.org/abs/2609.08798)<br>[https://github.com/raymin0223/on_policy_reverse_distillation](https://github.com/raymin0223/on_policy_reverse_distillation) | 提出 OPRD，让教师相对其 reference policy 评估学生 rollout，并放大学生 verifier-driven policy gradient 中受支持的更新；用于弱到强迁移和多教师蒸馏。 | 作者点名图 |
| [2026-09-21 · 6aaffc600000000012035ed5](<https://www.xiaohongshu.com/explore/6aaffc600000000012035ed5>) · 图7 | Thinking with Looped Flows | Ayhan Suleymanzade; Chanhyuk Lee; Floor Eijkelboom; Nicholas M. Boffi; Ismail Ilkan Ceylan; Jinwoo Kim (EPFL; KAIST; University of Amsterdam; CMU; TU Wien; AITHYRA; Oxford) | [arXiv:2609.11801v1](https://arxiv.org/abs/2609.11801) | 以逐步降低噪声和共享噪声训练局部去噪器，学习可递归更新的隐状态；推理时通过更细时间网格增加计算并保留多种有效预测。 | 作者点名图 |
| [2026-09-21 · 6aaffc600000000012035ed5](<https://www.xiaohongshu.com/explore/6aaffc600000000012035ed5>) · 图16 | RetireOPD: Self-Retiring On-Policy Distillation for Agentic Reinforcement Learning | Yan Yu; Zhengxi Lu; Yizhou Liu; Yichen Pan; Aozhe Wang; Qipeng Chen; Hua Yang; Wenqi Zhang; Weiming Lu; Qianglong Chen; Yongliang Shen (Zhejiang University; Alibaba Group) | [arXiv:2609.20784v1](https://arxiv.org/abs/2609.20784)<br>[https://github.com/ZJU-REAL/SDAR](https://github.com/ZJU-REAL/SDAR) | 先训练 skill-conditioned teacher，再与 RL 联合训练 student；当 teacher 与 student 的差异停止缩小时自动退役 teacher，避免固定蒸馏时程及 teacher 质量/阶段不匹配。 | 作者点名图 |
| [2026-09-15 · 6a9ef461000000002603a33b](<https://www.xiaohongshu.com/explore/6a9ef461000000002603a33b>) · 图3 | GraphMemix: Query-Aware Evidence Forests for Long-Term Multimodal Agent Memory | Geng Li; Yuhao Wang; Dong Li; Jianye Hao; Yuxin Peng (Peking University; MemoraX AI) | [arXiv:2608.26983v1](https://arxiv.org/abs/2608.26983)<br>MemoraX AI Research; GraphMemix | 以问题为中心从多模态长期记忆构造 evidence forest：扩展候选图、估算证据效用与激活成本，再在预算内优化保留关系结构的记忆子图。 | 作者点名图 |
| [2026-09-15 · 6a9ef461000000002603a33b](<https://www.xiaohongshu.com/explore/6a9ef461000000002603a33b>) · 图8 | SMELT: Scaling Laws for Compute-Matched MoE Looped Transformers | Tsinghua University; ByteDance Seed; M-A-P; TokenWave.AI (full author list in paper) | [arXiv:2609.01343v1](https://arxiv.org/abs/2609.01343) | 在每 token FLOPs、总非嵌入参数和 KV cache 对齐下研究 MoE looped transformer；循环复用中间层并拟合不同架构的 scaling law，报告计算匹配下的训练收益。 | 作者点名图 |
| [2026-09-14 · 6a9ef392000000002b003d2b](<https://www.xiaohongshu.com/explore/6a9ef392000000002b003d2b>) · 图2 | Random Attention: Rethinking KV Cache Eviction for Efficient Reasoning | Heng Wang; Jielin Qiu; Wenting Zhao; Cheng Qian; Liangwei Yang; Jiawei Han; Heng Ji; Silvio Savarese; Shelby Heinecke; Huan Wang (Salesforce AI Research; UIUC) | [arXiv:2609.03430v1](https://arxiv.org/abs/2609.03430)<br>[https://github.com/SalesforceAIResearch/Random-Attention](https://github.com/SalesforceAIResearch/Random-Attention) | 提出每个 attention head 内随机保留 KV 项，避免为每个缓存 token 估分；论文报告在约 4× 压缩下保持竞争准确率并提高 vLLM 吞吐。 | 作者点名图 |
| [2026-09-14 · 6a9ef392000000002b003d2b](<https://www.xiaohongshu.com/explore/6a9ef392000000002b003d2b>) · 图17 | Stronger Lower Bounds for (Non-)Anytime Acceleration of Gradient Descent | Minchan Jung; Hanseul Cho; Chulhee Yun (Korea Science Academy of KAIST; KAIST) | [arXiv:2609.04032v1](https://arxiv.org/abs/2609.04032) | 理论研究固定步长的凸光滑优化中 gradient descent 的 anytime 与 non-anytime 收敛下界，试图缩小已有加速上界与下界间的差距。 | 作者点名图 |
| [2026-09-13 · 6a9ef304000000002601b77c](<https://www.xiaohongshu.com/explore/6a9ef304000000002601b77c>) · 图1 | Normalized Low-Rank Adaptation (NoRA) | Jiale Kang; Ziyin Yue; Zheng Zhan; Yangyi Huang; Weiyang Liu (Yuanshi Intelligence; Microsoft Research; CUHK Shenzhen Loop Area Institute) | [arXiv:2608.31036v1](https://arxiv.org/abs/2608.31036)<br>[https://spherelab.ai/NoRA](https://spherelab.ai/NoRA) | 在 LoRA 训练中归一化 down-projection 矩阵，缓解由零初始化 up-projection 导致的早期优化不稳定；摘要称该方法不增加可训练参数或推理计算。 | 作者点名图 |
| [2026-09-13 · 6a9ef304000000002601b77c](<https://www.xiaohongshu.com/explore/6a9ef304000000002601b77c>) · 图2 | TTPO: Test-Time Policy Optimization | Aozhe Wang; Zhengxi Lu; Jianze Wang; Shangke Lv; Ying Liu; Weiming Lu; Jun Xiao; Yueting Zhuang; Hua Yang; Qianglong Chen; Yongliang Shen (Zhejiang University; Alibaba Group) | [arXiv:2608.27448v1](https://arxiv.org/abs/2608.27448)<br>[https://github.com/ZJU-REAL/TTPO](https://github.com/ZJU-REAL/TTPO) | 针对多数投票伪标签有误时分歧 rollout 会误导教师的问题，提出非对称目标：对一致 rollout 做 OPD，对分歧 rollout 用 GRPO 惩罚，并结合 token 级分支权重。 | 作者点名图 |
| [2026-09-13 · 6a9ef304000000002601b77c](<https://www.xiaohongshu.com/explore/6a9ef304000000002601b77c>) · 图13 | Knowledge Distillation During Mid-Training Favors Reasoning over Factual Recall | Jacqueline He; Howard Yen; Shuyue Stella Li; Margaret Li et al. (Meta AI; University of Washington; Princeton) | [arXiv:2609.01532v1](https://arxiv.org/abs/2609.01532)<br>[https://github.com/facebookresearch/midtraining-distillation](https://github.com/facebookresearch/midtraining-distillation) | 发现中训练阶段的 forward-KL 蒸馏可能提升推理却拖慢事实回忆；提出 Switch Distillation，仅在教师有信心的 token 蒸馏，否则回退交叉熵。 | 作者点名图 |
| [2026-09-12 · 6a9ef2690000000026030134](<https://www.xiaohongshu.com/explore/6a9ef2690000000026030134>) · 图1 | Language Models Can Control Their Own Attention | Namgyu Ho; Huzama Ahmad; Woosung Koh; Se-Yeong Yun; Tal Schuster; Cicero Nogueira dos Santos (KAIST AI; Google DeepMind) | [arXiv:2609.02737v1](https://arxiv.org/abs/2609.02737) | 提出 Declarative Attention，让模型以 global、focus、local 三种模式自行指定回答时读取全局、指定片段或近期输出；无需训练或额外 scorer，减少长上下文实际注意到的 token。 | 作者点名图 |
| [2026-09-12 · 6a9ef2690000000026030134](<https://www.xiaohongshu.com/explore/6a9ef2690000000026030134>) · 图8 | Scaling Reinforcement Learning for Diffusion Models via Velocity Matching | Jaemoo Choi; Wei Guo; Yuchen Zhu; Arash Vahdat; Molei Tao; Julius Berner; Yongxin Chen (Georgia Tech; NVIDIA) | [arXiv:2608.23664v1](https://arxiv.org/abs/2608.23664)<br>[https://jaemoo-choi.github.io/RVM/](https://jaemoo-choi.github.io/RVM/) | 提出 Reward-based Velocity Matching (RVM)，直接在 velocity field 上做无轨迹似然的奖励更新，旨在降低扩散模型 reward fine-tuning 的计算成本，并支持视频动态奖励。 | 作者点名图 |
| [2026-09-12 · 6a9ef2690000000026030134](<https://www.xiaohongshu.com/explore/6a9ef2690000000026030134>) · 图16 | R³: Training Robots to Reason in Natural Language via Reinforcement Learning | Lehong Wu; Yuxiao Qu; Zheyuan Hu; Ivan Zhang; Limin Wei; Zackory Erickson; Aviral Kumar (Carnegie Mellon University) | [arXiv:2608.26053v1](https://arxiv.org/abs/2608.26053)<br>[https://robotic-reasoner.github.io/](https://robotic-reasoner.github.io/) | 用自然语言推理为低层机器人操作策略提供 test-time guidance；先以专家推理轨迹初始化，再用离线动作数据做单步 rubric-based RL，测试长程任务与未见任务泛化。 | 作者点名图 |
| [2026-09-12 · 6a9ef2690000000026030134](<https://www.xiaohongshu.com/explore/6a9ef2690000000026030134>) · 图17 | Best Practice Critic Optimization (BPCO) | Penghui Qi; Xiangxin Zhou; Wee Sun Lee (National University of Singapore; Tencent Hunyuan) | [arXiv:2608.23566v2](https://arxiv.org/abs/2608.23566)<br>[https://github.com/OPHutu/golden_critic](https://github.com/OPHutu/golden_critic) | 提出 critic-based RL 配方，组合 DPPO、边界化 Monte Carlo value targets、未归一化优势和长度自适应 GAE；目标是稳定 critic 训练，并在每个 prompt 只采一条回答时竞争 group-based 方法。 | 作者点名图 |
| [2026-09-11 · 6a9ef1970000000026030083](<https://www.xiaohongshu.com/explore/6a9ef1970000000026030083>) · 图1 | Tail-Likelihood Reinforcement Learning (TailRL) | Shrinivas Ramasubramanian; Daman Arora; Fahim Tajwar; Guanning Zeng et al. (Carnegie Mellon; UC Berkeley; Together AI; Aurora Innovation) | [arXiv:2609.02987v1](https://arxiv.org/abs/2609.02987)<br>[https://zanette-labs.github.io/TailRL-website/](https://zanette-labs.github.io/TailRL-website/) | 从只优化平均奖励转向优化跨奖励阈值的上尾概率，强调保留稀有高回报轨迹；把目标写成连续二元事件族，便于并入现有 RL pipeline。 | 作者点名图 |
| [2026-09-11 · 6a9ef1970000000026030083](<https://www.xiaohongshu.com/explore/6a9ef1970000000026030083>) · 图12 | On-Policy Self-Distillation in Diffusion Models | DiffusionOPSD Team (ByteDance Seed) | [arXiv:2608.24646v1](https://arxiv.org/abs/2608.24646)<br>DiffusionOPSD project page | 把图像级奖励转换为扩散去噪中间步骤的显式训练目标；通过锚点轨迹、正负目标和有限拟合优化 on-policy self-distillation。 | 作者点名图 |
| [2026-09-11 · 6a9ef1970000000026030083](<https://www.xiaohongshu.com/explore/6a9ef1970000000026030083>) · 图18 | Does On-Policy Distillation Really Distill? From Noisy Teacher to Self-Improvement | Yi Ding; Ruqi Zhang (Purdue University) | [arXiv:2608.31046v1](https://arxiv.org/abs/2608.31046)<br>Hugging Face and GitHub links shown on paper page | 分析 OPD teacher 对 student 自采轨迹打分所带来的噪声，提出无外部 teacher 的 On-Policy Self-Adaptation (OPSA)，按熵自适应负优势抑制低概率 token；论文报告在若干推理基准上提升。 | 作者点名图 |
| [2026-09-10 · 6a9ef0ca000000000b001c86](<https://www.xiaohongshu.com/explore/6a9ef0ca000000000b001c86>) · 图1 | Towards a Statistical Understanding of Mixture-of-Experts | Siyuan He; Bokai Yang; Jie Hu; Ziwen Gao; Yuhong Yang (Tsinghua; East China Normal University; BIMSA) | [arXiv:2609.03501v1](https://arxiv.org/abs/2609.03501) | 把 MoE 看作局部聚合，分析路由、稀疏激活和共享专家如何改变近似—估计—计算的权衡，并尝试以输入空间的局部专家优势统一理解 MoE。 | 作者点名图 |
| [2026-09-10 · 6a9ef0ca000000000b001c86](<https://www.xiaohongshu.com/explore/6a9ef0ca000000000b001c86>) · 图7 | Visual General Intelligence: A White Paper | Hirokatsu Kataoka et al. (AIST; University of Oxford; OpenAI; Cambridge; Google DeepMind; CMU; Harvard; Stanford; Princeton and collaborators) | [arXiv:2608.25924v1](https://arxiv.org/abs/2608.25924) | 从视觉中心视角讨论视觉经验与学习能否成为通往 AGI 的路径，梳理视觉输入、表征、基准、学习范式及其与语言等模态的关系。 | 作者点名图 |
| [2026-09-10 · 6a9ef0ca000000000b001c86](<https://www.xiaohongshu.com/explore/6a9ef0ca000000000b001c86>) · 图8 | Understanding Evolution Strategies for LLM Reasoning: Broader Reasoning Coverage than GRPO | Yunpeng Ba et al. (SUSTech; NUS; Huawei Noah’s Ark Lab; CityU Hong Kong; Harbin Institute of Technology) | [arXiv:2608.27351v1](https://arxiv.org/abs/2608.27351)<br>[https://github.com/yunpengba7/understanding-es](https://github.com/yunpengba7/understanding-es) | 比较 Evolution Strategies 与 GRPO 的推理后训练行为；摘要称 ES 在 pass@k 覆盖、内存效率和更广推理能力上呈现不同优势，并分析更新稀疏性与群体规模。 | 作者点名图 |
| [2026-09-10 · 6a9ef0ca000000000b001c86](<https://www.xiaohongshu.com/explore/6a9ef0ca000000000b001c86>) · 图15 | How Do Language Models Choose Between Context and Memory? | Benjamin Shih; John Winnicki; Arianna Cao (Stanford University; Perpetual Labs) | [arXiv:2609.00753v1](https://arxiv.org/abs/2609.00753) | 用反事实干预研究上下文信息与参数化记忆冲突时模型如何选择来源；区分可控 steerability、模型自然使用的因果机制与跨任务可迁移性。 | 作者点名图 |
| [2026-09-09 · 6a9eefc300000000270142be](<https://www.xiaohongshu.com/explore/6a9eefc300000000270142be>) · 图1 | Rethinking On-Policy Distillation of Large Language Models II: One Training Example | Zixuan Fu; Bingxiang He; Yuxin Zuo; Haohuan Huang et al. (Tsinghua; UCAS; Northeastern; UIUC; Johns Hopkins) | [arXiv:2609.04172v1](https://arxiv.org/abs/2609.04172)<br>[https://github.com/Thinking-Space/One-Shot-OPD](https://github.com/Thinking-Space/One-Shot-OPD) | 研究 one-shot OPD：单个 query 可恢复多数 full-data OPD 收益；多教师场景约 16 个语义多样 query 可接近全量训练。作者以 state coverage 解释 rollout 监督覆盖与学生吸收速度的差别。 | 作者点名图 |
| [2026-09-09 · 6a9eefc300000000270142be](<https://www.xiaohongshu.com/explore/6a9eefc300000000270142be>) · 图4 | On-policy Distillation with Verifiable Reward (OPDVR) | Wenze Lin; Jiale Zhao; Xitai Jiang; Songde Rao; Yining Li; Shenzhi Wang; Bingxiang He; Gao Huang (LeapLab; Tsinghua; Beihang; PKU) | [arXiv:2608.24696v1](https://arxiv.org/abs/2608.24696)<br>[https://github.com/LeapLabTHU/OPDVR](https://github.com/LeapLabTHU/OPDVR) | 将 OPD 的 token 级密集监督与可验证奖励结合；按轨迹正确性调整采样 token 的奖励，希望避免额外超参数并能与 GRPO 等策略梯度方法结合。 | 作者点名图 |
| [2026-09-09 · 6a9eefc300000000270142be](<https://www.xiaohongshu.com/explore/6a9eefc300000000270142be>) · 图5 | PURO-2B: Poor Lab’s Qwen2-1.5B Trained on RTX 5090 within $5090 | Kairong Luo; Jiarui Cui; Yaorui Yin; Shengqi Chen; Yiming Yang et al. (Tsinghua; Pengcheng Laboratory) | [arXiv:2608.27370v1](https://arxiv.org/abs/2608.27370)<br>[https://huggingface.co/collections/thu-pacman/puro-2b](https://huggingface.co/collections/thu-pacman/puro-2b) | 公开一套低成本预训练 recipe 和 PURO-2B 模型，强调消费级 RTX 5090、低精度、数据课程和 hyperball optimizer；摘要称成本低于 $6.9K，并给出 Qwen2.5-1.5B 水平对照。 | 作者点名图 |
| [2026-09-09 · 6a9eefc300000000270142be](<https://www.xiaohongshu.com/explore/6a9eefc300000000270142be>) · 图18 | Learning to Follow In-Context Watermark Instructions via Self-Distillation | Yepeng Liu; Tianyi Chen; Xuandong Zhao; Dawn Song; Yuheng Bu (UC Santa Barbara; UC San Diego; UC Berkeley) | [arXiv:2608.29030v1](https://arxiv.org/abs/2608.29030)<br>[https://github.com/yepengliu/ICW-IF](https://github.com/yepengliu/ICW-IF) | 提出 ICWBench 与自蒸馏加 RL 的训练方法，让模型按上下文要求嵌入可检测水印，同时评估检测率与回答质量。 | 作者点名图 |
| [2026-09-08 · 6a9eee53000000002b025f59](<https://www.xiaohongshu.com/explore/6a9eee53000000002b025f59>) · 图1 | One Demonstration, Many Objects: Generalizing Manipulation via Local Contact Geometry (DemoMimic) | Satvik Sharma; Samrat Sahoo; Huang Huang; Fei-Fei Li; Jiajun Wu; Dorsa Sadigh; Jeannette Bohg (Stanford University) | [arXiv:2609.01938](https://arxiv.org/abs/2609.01938)<br>[https://demomimic.github.io/](https://demomimic.github.io/) | 从一次人类示范学习灵巧操作策略，以接触点附近的局部几何和接触中心奖励提升跨物体迁移；图示与摘要称可适配不同形状、尺度、质量和摩擦。 | 作者点名图 |
| [2026-09-08 · 6a9eee53000000002b025f59](<https://www.xiaohongshu.com/explore/6a9eee53000000002b025f59>) · 图8 | Prime Agent: A Self-Improving RLM Harness | Seth Karten; Alex L. Zhang; Kevin Thomas; Sebastian Müller et al. (Prime Intellect; Princeton; MIT) | [arXiv:2608.23552v1](https://arxiv.org/abs/2608.23552)<br>[https://github.com/PrimeIntellect-ai/prime-agent](https://github.com/PrimeIntellect-ai/prime-agent) | 长程评测与 coding-agent harness：持久 Python REPL、跨轨迹保存历史/记忆/技能的 continual harness、递归子代理和可检查的 agent view，集中规范执行、恢复、验证和资源记账。 | 作者点名图 |
| [2026-09-08 · 6a9eee53000000002b025f59](<https://www.xiaohongshu.com/explore/6a9eee53000000002b025f59>) · 图11 | Why Pretraining Fails to Share Cross-Lingual Knowledge | Adam Gaber; Uriel Dolev; Elisabeth Fittschen; Bobby Cheng; Yuval Marton; Leshem Choshen | [arXiv:2609.19291](https://arxiv.org/abs/2609.19291)<br>[https://github.com/AdamJaber03/torchtitan-multilingual](https://github.com/AdamJaber03/torchtitan-multilingual) | 用同一语言内容但不相交 token 空间的双语预训练设置研究跨语言知识隔离；作者认为 token 空间割裂本身会妨碍迁移，并测试词级映射的改善。 | 作者点名图 |
| [2026-09-08 · 6a9eee53000000002b025f59](<https://www.xiaohongshu.com/explore/6a9eee53000000002b025f59>) · 图13 | Towards the Harness of Embodied Agents (Thea) | Qi Wang; Tianyi Wang; Chengyang Li; Shikun Ban; Yurun Chen; Yizhong Ge; Jason Qin; Chengtai Li; Wentao Zhu (Eastern Institute of Technology, Ningbo) | [arXiv:2608.11246v1](https://arxiv.org/abs/2608.11246)<br>[https://eit-hai.github.io/thea](https://eit-hai.github.io/thea)<br>[https://github.com/EIT-HAI/Thea](https://github.com/EIT-HAI/Thea) | 将 coding-agent harness 思路延伸到机器人：以 Scene Graph as Context 表示世界状态，以 Evaluation as Exit Codes 判断动作是否成功并诊断失败，支撑长程真实环境任务。 | 作者点名图 |
| [2026-08-30 · 6a8b1e770000000033029490](<https://www.xiaohongshu.com/explore/6a8b1e770000000033029490>) · 图1 | Swift-Image: Exploring the Performance Frontier of Compact Unified Image Generation Models | Taihang Hu et al. (Alibaba Group) | [arXiv:2608.20334v1](https://arxiv.org/abs/2608.20334)<br>arXiv source; Alibaba Group | 研究以 6B 单流 DiT 统一支持文生图、单图编辑和多图编辑，并通过并行专家 RL、多教师 OPD、结构化剪枝和少步蒸馏探索紧凑模型性能。 | 作者点名图 |
| [2026-08-30 · 6a8b1e770000000033029490](<https://www.xiaohongshu.com/explore/6a8b1e770000000033029490>) · 图11 | V-RAE: Rethinking Video Latent Spaces for Generation | Minghui Guo; Shengqiong Wu; Hao Fei (National University of Singapore; University of Oxford) | [arXiv:2608.13556v1](https://arxiv.org/abs/2608.13556)<br>[https://v-rae.github.io/](https://v-rae.github.io/) | 在冻结视觉基础模型表示之上学习紧凑视频生成潜变量，强调生成语义而非单纯像素重建，并报告重建、生成与未来帧预测结果。 | 作者点名图 |
| [2026-08-30 · 6a8b1e770000000033029490](<https://www.xiaohongshu.com/explore/6a8b1e770000000033029490>) · 图12 | Jagged Judges: Epistemic Stability Under Silence, Pressure, and Persistence | Justin Zhao; Himaghna Bhattacharjee; Hannah Korevaar; Bhaktipriya Radharapu; Khalid El-Arini (Meta Superintelligence Labs / FAIR) | [arXiv:2608.12645v1](https://arxiv.org/abs/2608.12645)<br>[https://www.jagged-judges.com](https://www.jagged-judges.com) | 提出 Wiggle Framework，从重复改写、单轮质疑、多轮持续施压三个维度测量 LLM judge 的判决稳定性；摘要指出高准确率不保证受压时稳定。 | 作者点名图 |
| [2026-08-30 · 6a8b1e770000000033029490](<https://www.xiaohongshu.com/explore/6a8b1e770000000033029490>) · 图14 | Synthetic Persona Pretraining: Alignment from Token Zero | Julian Minder; Viktor Moskvoretskii; Raghav Singhal et al. (EPFL and collaborators) | [arXiv:2608.13482v1](https://arxiv.org/abs/2608.13482)<br>[https://modelraising.ai/spp](https://modelraising.ai/spp) | 提出在预训练阶段就把目标 assistant persona 写入数据与训练目标，再用对话后训练绑定身份；作者报告早期注入比训练末期再做 persona alignment 更有效。 | 作者点名图 |
| [2026-08-29 · 6a8b1dc300000000330292d8](<https://www.xiaohongshu.com/explore/6a8b1dc300000000330292d8>) · 图4 | Every Coin Has Two Sides: On the Dual Nature of Generalization in On-Policy Distillation of Large Language Models | Zhaoyi Li; Deyang Kong; Yuan Wei; Evan Yang; Ranran Shen; Mahardika Krisna Ihsani; Ming Yang; Wei Zhang; Chuan Hao; Jian Yang; Ran Tao; Bryan Dai; Shikun Zhang; Wei Ye; Defu Lian (USTC, Peking University, IQuest Research, MBZUAI, Zhejiang University) | [arXiv:2608.16647v1](https://arxiv.org/abs/2608.16647)<br>IQuest Research; USTC / PKU / MBZUAI / Zhejiang University | 受控改变 OPD 的泛化因素，指出学生常学习教师的推理行为而非特定答案；同源教师—学生更易跨语言/任务迁移，跨来源组合则可能受教师能力路由影响。 | 作者点名图 |
| [2026-08-29 · 6a8b1dc300000000330292d8](<https://www.xiaohongshu.com/explore/6a8b1dc300000000330292d8>) · 图12 | Rethinking Privileged Information in On-Policy Self-Distillation | Samyak Shrestha; Alexander Tessier (FirstPrinciples) | [arXiv:2608.18271v1](https://arxiv.org/abs/2608.18271) | 研究 OPSD 中教师获得参考解等特权信息是否真正带来学习；实验提示性能提升与学生是否学到参考解并不等价，分布对齐也不能单独证明参考信息贡献。 | 作者点名图 |
| [2026-08-28 · 6a8b1d170000000028026612](<https://www.xiaohongshu.com/explore/6a8b1d170000000028026612>) · 图1 | EnvHarness: Awakening Static Worlds for Agent Learning | Chengsong Huang et al. (Google DeepMind; Google Cloud AI Research; Google; UNC Chapel Hill) | [arXiv:2608.19880v1](https://arxiv.org/abs/2608.19880)<br>[https://github.com/google-research/envharness](https://github.com/google-research/envharness)<br>[https://www.envharness.com](https://www.envharness.com) | 提出可编程 Environment Harness，通过插件组件改变静态环境行为但保留原验证器；EnvRigger 根据 agent 执行轨迹合成环境改造，以支持环境与策略共同演进。 | 作者点名图 |
| [2026-08-28 · 6a8b1d170000000028026612](<https://www.xiaohongshu.com/explore/6a8b1d170000000028026612>) · 图8 | Co-RL: Unsupervised Reasoning Emerges from Diverse Cohort in Multi-agent RL | Yunhao Yang; Yuexin Bian; Yunjie Tian; Di Fu; Tianjin Huang; Yuanyuan Shi; Ziang Xiao; Nuno Vasconcelos; Yijiang Li | [arXiv:2608.17253v2](https://arxiv.org/abs/2608.17253)<br>[https://github.com/DrStranded/Co-RL](https://github.com/DrStranded/Co-RL) | 以多模型、多样化 cohort 的相互反馈构造无标注 RL 信号，试图减少自奖励训练中偏差放大、响应同质化与训练崩塌。 | 作者点名图 |
| [2026-08-27 · 6a8b1c74000000003703c963](<https://www.xiaohongshu.com/explore/6a8b1c74000000003703c963>) · 图1 | Recirculation | Michael C. Mozer; Shoaib Ahmed Siddiqui; Danny Sawyer; Sunny Sanyal; Rosanne Liu (Google DeepMind; UT Austin) | [arXiv:2608.17981v1](https://arxiv.org/abs/2608.17981) | 提出推理期 recirculation 架构增强：通过状态递归帮助前馈模型跟踪动态信息，尽量不增加生成阶段延迟；报告在 Gemma3 等模型任务上的收益。 | 作者点名图 |
| [2026-08-27 · 6a8b1c74000000003703c963](<https://www.xiaohongshu.com/explore/6a8b1c74000000003703c963>) · 图15 | Towards Understanding On-Policy Distillation Through the Lens of Test-Time Scaling | Xinmu Ge; Zizhuo Zhang; Yu Huang; Jianing Zhu; Lin Yuan; Wanli Gu; Weichang Wu; Weiran Huang; Xiaolu Zhang; Bo Han; Jun Zhou; Jiangchao Yao (SJTU, Shanghai Innovation Institute, HKBU, UT Austin, Ant Group) | [arXiv:2608.11829v1](https://arxiv.org/abs/2608.11829) | 用不同采样预算下的 pass@k 与 avg@k 分析 on-policy distillation，结论倾向于 OPD 主要提升采样效率；能力边界是否扩展，需要按任务可解性进一步区分。 | 作者点名图 |
| [2026-08-26 · 6a8b1beb000000003300a535](<https://www.xiaohongshu.com/explore/6a8b1beb000000003300a535>) · 图7 | On the Principles Behind Neural Network Optimizers | Yushun Zhang (The Chinese University of Hong Kong, Shenzhen) | [arXiv:2608.16760v1](https://arxiv.org/abs/2608.16760)<br>CUHK-Shenzhen PhD thesis; INFORMS George B. Dantzig Dissertation Competition 2026 | 论文讨论 Adam 的收敛行为、Transformer 中 Hessian 结构与 Adam 优势，并提出 Adam-mini 以更低内存占用保留性能；作者说明这是博士论文的竞赛短版。 | 作者点名图 |
| [2026-08-26 · 6a8b1beb000000003300a535](<https://www.xiaohongshu.com/explore/6a8b1beb000000003300a535>) · 图16 | The Sparsity Whisperer | Linghao Kong; Inimai Subramanian; Micah Adler (MIT); Dan Alistarh (IST Austria); Dan Gutfreund (IBM); Nir Shavit (MIT / Red Hat AI) | [arXiv:2608.06630v1](https://arxiv.org/abs/2608.06630)<br>[https://github.com/Shavit-Lab/Whisper](https://github.com/Shavit-Lab/Whisper) | 提出利用神经元输入差异来指导 LLM 剪枝的 Wisp/Whisper 方法，关注在低额外成本下保留输出差异，以改善稀疏化的质量—推理成本折中。 | 作者点名图 |
| [2026-08-25 · 6a8b1b1c000000003703c5f9](<https://www.xiaohongshu.com/explore/6a8b1b1c000000003703c5f9>) · 图9 | The Embedder’s Dilemma: LLMs Are Better, but at What Cost? | Adnan El Assadi (Harvard); Niklas Muennighoff (Stanford); Jinhyuk Lee | [arXiv:2608.12875v1](https://arxiv.org/abs/2608.12875)<br>[https://github.com/embeddings-benchmark/embedders-dilemma](https://github.com/embeddings-benchmark/embedders-dilemma) | 在 37 项任务上比较 10 个 LLM 与 26 个 embedding 模型；两类方法总体接近但优势任务不同，LLM 推理检索更强，embedding 在分类/聚类/相似度更有成本优势。 | 作者点名图 |
| [2026-08-24 · 6a8b1a0a0000000023013977](<https://www.xiaohongshu.com/explore/6a8b1a0a0000000023013977>) · 图15 | Toward a Theory of Value in AI Alignment | Andrew Smart; Shazeda Ahmed; Jackie Kay; Jimmy Tobin; Kris Shrishak; Abeba Birhane | [arXiv:2608.10327v1](https://arxiv.org/abs/2608.10327) | 基于对 94 篇价值对齐论文的梳理，讨论 AI alignment 中“价值”概念如何定义与操作化，并指出现有研究中的概念选择问题。 | 作者点名图 |
| [2026-08-15 · 6a78a49c000000002c004f7c](<https://www.xiaohongshu.com/explore/6a78a49c000000002c004f7c>) · 图1 | Test-Time Scaling in Reasoning LLMs: Inference Regimes, Evaluation, and Reproducibility | Mohsen Hariri et al. | [arXiv:2608.04001v1](https://arxiv.org/abs/2608.04001)<br>GitHub and dataset links shown in paper image | 梳理推理模型 test-time scaling 的 inference regimes、评估协议与复现性问题，提出相应 taxonomy 和比较框架。 | 作者点名图 |
| [2026-08-14 · 6a78a3c00000000032032ee4](<https://www.xiaohongshu.com/explore/6a78a3c00000000032032ee4>) · 图13 | β-OPSD: Deriving with Policy Optimization, Training with Self-Distillation | Jiawei Xu; Minghui Liu; Juzheng Zhang; Tom Goldstein; Furong Huang | [arXiv:2607.28582v1](https://arxiv.org/abs/2607.28582) | 将 on-policy self-distillation 解释为带 KL 正则的策略优化，并从该视角推导可用于更高效训练的蒸馏目标。 | 作者点名图 |
| [2026-08-14 · 6a78a3c00000000032032ee4](<https://www.xiaohongshu.com/explore/6a78a3c00000000032032ee4>) · 图17 | Position: It’s Time to Optimize LLMs for Self-Consistency | Itamar Pres et al. | [arXiv:2608.05188v1](https://arxiv.org/abs/2608.05188) | 立场论文把跨输入的行为不一致视为模型优化中的共同目标，倡议直接优化 LLM self-consistency。 | 作者点名图 |
| [2026-08-13 · 6a78a2e70000000032032c6e](<https://www.xiaohongshu.com/explore/6a78a2e70000000032032c6e>) · 图10 | Memory Decoder at Scale: A Pretrained, Parametric Long-Term Memory | Rubin Wei; Jiaqi Cao; Jiarui Wang; Junming Zhang; Qipeng Guo; Bowen Zhou; Zhouhan Lin (SJTU LUMIA; Shanghai AI Lab; Tsinghua) | [arXiv:2607.27291v1](https://arxiv.org/abs/2607.27291)<br>GitHub/repository link displayed in the image | 研究可预训练的参数化长期记忆，扩展至 6.9B 参数并以稀疏、批次级 FAISS 检索读写长期知识。 | 作者点名图 |
| [2026-08-13 · 6a78a2e70000000032032c6e](<https://www.xiaohongshu.com/explore/6a78a2e70000000032032c6e>) · 图17 | HarnessOpt-Bench: Evaluating LLMs at Harness Optimization | Varun Ursekar; Apaar Shanker; Yash Maurya; Shehab Yasser; Vijay S. Kalmath; Veronica Chatrath; Yuan (Emily) Xue (Scale AI) | [arXiv:2608.06301v1](https://arxiv.org/abs/2608.06301) | 建立评测 LLM 优化 coding-agent harness 的基准，在有预算且随机性的环境中衡量 harness 改造能力。 | 作者点名图 |
| [2026-08-12 · 6a78a26f0000000026036cbd](<https://www.xiaohongshu.com/explore/6a78a26f0000000026036cbd>) · 图8 | Rethinking Self-Evolution: A Constrained Exploration-Exploitation Process for Mitigating Skill Overfitting | Hongqiang Lin; Chao Liu; Xiaofan Bai; Xuan Jin; Yuhong Li; Ninggan Zheng; Xipeng Cao (Zhejiang University; Alibaba) | [arXiv:2607.26643v1](https://arxiv.org/abs/2607.26643) | 提出 SkillBoost，把 agent skill 自演化建模为受约束的探索—利用过程，以分阶段受限搜索缓解 skill overfitting 并提升迁移。 | 作者点名图 |
| [2026-08-11 · 6a78a1f5000000002c0047b9](<https://www.xiaohongshu.com/explore/6a78a1f5000000002c0047b9>) · 图1 | Toward Skill-Native LLMs: Skill Entropy for Benchmarking and Training Long-Horizon Reasoning | Yinghui He et al. (Princeton; CMU; Toronto; UIUC; Stanford; Oxford) | [arXiv:2608.05139v1](https://arxiv.org/abs/2608.05139)<br>[https://github.com/Gen-Verse/Skill-Entropy-RL](https://github.com/Gen-Verse/Skill-Entropy-RL) | 定义 skill entropy 衡量跨技能切换难度，提出 Skill²-Bench，并把该量用作 RL 训练信号。 | 作者点名图 |
| [2026-08-11 · 6a78a1f5000000002c0047b9](<https://www.xiaohongshu.com/explore/6a78a1f5000000002c0047b9>) · 图11 | Explorative Modeling: Unlocking a Third Pretraining Axis and End-to-End Generation | Alexi Gladstone; Heng Ji; Yilun Du | [arXiv:2607.27372v1](https://arxiv.org/abs/2607.27372)<br>[https://explorative-modeling.github.io](https://explorative-modeling.github.io)<br>[https://github.com/alexiglad/XM](https://github.com/alexiglad/XM) | 把候选数据与模型匹配纳入生成模型训练环路，提出参数和数据之外的探索规模轴，并研究端到端生成。 | 作者点名图 |
| [2026-08-11 · 6a78a1f5000000002c0047b9](<https://www.xiaohongshu.com/explore/6a78a1f5000000002c0047b9>) · 图12 | On the Convergence Analysis of Muon | Wei Shen; Ruichuan Huang; Minhui Huang; Cong Shen; Jiawei Zhang | [arXiv:2505.23737v3](https://arxiv.org/abs/2505.23737)<br>TMLR 07/2026; OpenReview link visible but not transcribed | 理论分析 Muon 的收敛性质并与梯度下降比较，给出不同设置下的收敛率界。 | 作者点名图 |
| [2026-08-10 · 6a78a16d0000000025001f24](<https://www.xiaohongshu.com/explore/6a78a16d0000000025001f24>) · 图1 | AgentOPSD: Recursive Self-Distillation for Agentic Reinforcement Learning | Zi-Han Wang et al. (Tsinghua; Zhejiang; Meituan) | [arXiv:2608.05987v1](https://arxiv.org/abs/2608.05987)<br>[https://github.com/ZethWang/AgentOPSD](https://github.com/ZethWang/AgentOPSD) | 将多轮 agent 轨迹聚合为 turn-level 证据，递归更新信念以解决长时程 RL 中的决策归因问题。 | 作者点名图 |
| [2026-08-10 · 6a78a16d0000000025001f24](<https://www.xiaohongshu.com/explore/6a78a16d0000000025001f24>) · 图12 | Mental World Modeling | Hao Fei (Oxford); Yiran Zhao (National University of Singapore) | [arXiv:2607.27201v1](https://arxiv.org/abs/2607.27201)<br>[https://mental-world.github.io](https://mental-world.github.io) | 把物理世界状态与行动者的信念、目标和意图联合建模，以改进对人类行为的预测。 | 作者点名图 |
| [2026-08-10 · 6a78a16d0000000025001f24](<https://www.xiaohongshu.com/explore/6a78a16d0000000025001f24>) · 图14 | LongHorizon-Harness: Advancing Long-Horizon Agents for Real-World Tasks | Ziyu Ma; Hailang Huang; Shun Zou; Yong Wang; Shidong Yang; Yiming Hu; Fei Wei; Xiangxiang Chu (DreamX / Alibaba) | [arXiv:2608.01964v1](https://arxiv.org/abs/2608.01964)<br>[https://github.com/AMAP-ML/LongHorizon-Harness](https://github.com/AMAP-ML/LongHorizon-Harness)<br>[https://lh-harness.pages.dev](https://lh-harness.pages.dev) | 把长任务 agent 的 task state 显式置于执行过程之外，由 manager、fresh-context executor、read-only auditor 分工维护和核验。 | 作者点名图 |
| [2026-07-30 · 6a64f0df000000000c017239](<https://www.xiaohongshu.com/explore/6a64f0df000000000c017239>) · 图8 | Interleaved Noise Injection Improves Clean, Corrupted, and OOD Performance | Matt L. Wiemann; Peter Melchior; Andrew K. Saydjari (Princeton University) | [arXiv:2607.14466v1](https://arxiv.org/abs/2607.14466)<br>图中未见项目网址 | 交替注入干净/噪声数据，利用不同噪声对模型归纳偏置的互补作用改善干净、受扰和分布外表现。 | 作者点名图 |
| [2026-07-30 · 6a64f0df000000000c017239](<https://www.xiaohongshu.com/explore/6a64f0df000000000c017239>) · 图18 | SEED: Self-Evolving On-Policy Distillation for Agentic Reinforcement Learning | Jinyang Wu et al. | [arXiv:2607.14777v1](https://arxiv.org/abs/2607.14777)<br>[https://github.com/jinyangwu/SEED](https://github.com/jinyangwu/SEED) | 从 on-policy 轨迹中归纳可复用 skill，再把 hindsight 分析转成密集 token 级蒸馏信号，辅助长时程 agentic RL。 | 作者点名图 |
| [2026-07-29 · 6a64efe90000000013026601](<https://www.xiaohongshu.com/explore/6a64efe90000000013026601>) · 图9 | Video = World + Event Stream (Wan-Streamer v0.3) | Wan Team, Alibaba Group | [arXiv:2607.15038v1](https://arxiv.org/abs/2607.15038)<br>[https://wan-streamer.com](https://wan-streamer.com) | 将视频建模为稳定世界状态加随时间变化的事件流，服务实时全双工音视频交互；图中列出 640×368、25 FPS 等运行规格。 | 作者点名图 |
| [2026-07-29 · 6a64efe90000000013026601](<https://www.xiaohongshu.com/explore/6a64efe90000000013026601>) · 图17 | SOAP, Muon, and Beyond: Pushing LLM Pretraining Scales | Mikail Khona; Aditya Vavre; Boxiang Wang; Deyu Fu; Hao Wu; Mike Chrzanowski; et al. (NVIDIA) | [arXiv:2607.20548v1](https://arxiv.org/abs/2607.20548)<br>[https://github.com/NVIDIA-NeMo/Emerging-Optimizers](https://github.com/NVIDIA-NeMo/Emerging-Optimizers) | 比较 SOAP、Muon 与 AdamW 在大规模预训练中的稳定性和可扩展性，并给出 Megatron-LM 兼容的分布式优化器实现。 | 作者点名图 |
| [2026-07-28 · 6a64ef46000000000e037e0e](<https://www.xiaohongshu.com/explore/6a64ef46000000000e037e0e>) · 图1 | Understanding Reasoning from Pretraining to Post-Training | Jingyan Shen; Ang Li; Salman Rahman; Yifan Sun; Micah Goldblum; Matus Telgarsky; Pavel Izmailov | [arXiv:2607.16097v1](https://arxiv.org/abs/2607.16097)<br>[https://huggingface.co/pavelslab-nyu/pre2post-chess](https://huggingface.co/pavelslab-nyu/pre2post-chess)<br>[https://github.com/pavelslab-nyu/pre2post-chess](https://github.com/pavelslab-nyu/pre2post-chess) | 用受控 chess testbed 研究预训练选择如何影响后续 RL 收益，连接预训练规模、RL 算力和推理能力变化。 | 作者点名图 |
| [2026-07-28 · 6a64ef46000000000e037e0e](<https://www.xiaohongshu.com/explore/6a64ef46000000000e037e0e>) · 图16 | Test-Time Scaling via Error Localization | Rajiv Shailesh Chitale; Rahul Madhavan; Taneesh Gupta; Deepanway Ghosal; Aravind Raghunveer (Google DeepMind) | [arXiv:2607.21453v1](https://arxiv.org/abs/2607.21453)<br>图中未见项目网址 | TSEL 用固定或环境反馈定位推理轨迹中出错的步骤，再复用正确前缀；摘要报告相同 token 预算下优于独立采样与多轮修订。 | 作者点名图 |
| [2026-07-27 · 6a64eea80000000009036b83](<https://www.xiaohongshu.com/explore/6a64eea80000000009036b83>) · 图1 | System Card: Claude Opus 5 | Anthropic | System card dated 2026-07-24<br>[https://anthropic.com](https://anthropic.com) | Anthropic 模型系统卡封面；当前截图没有呈现评测细节。 | 作者点名图 |
| [2026-07-27 · 6a64eea80000000009036b83](<https://www.xiaohongshu.com/explore/6a64eea80000000009036b83>) · 图14 | Loop the Loopies! | Zitian Gao; Yilong Chen; Yihao Xiao; Xinyu Yang; Ran Tao; Joey Zhou; Bryan Dai (IQQuest Research) | [arXiv:2607.16051v1](https://arxiv.org/abs/2607.16051)<br>图中可见模型名 Loopie-20B-A2B / Loopie-6B-A0.6B 及代码仓库名 megatron-loopie / vllm-loopie | 提出 Loopie 系列循环 Transformer MoE，通过循环结构提高参数容量利用；摘要报告其在数学和推理基准上的结果。 | 作者点名图 |
| [2026-07-26 · 6a64ed69000000001302fed9](<https://www.xiaohongshu.com/explore/6a64ed69000000001302fed9>) · 图3 | Ring-Zero: Scaling Zero RL to a Trillion Parameters for Emergent Reasoning | Xinyu Tang et al. (Renmin University; Ant Group; Tsinghua; Zhejiang) | [arXiv:2607.12395v2](https://arxiv.org/abs/2607.12395)<br>图中未见项目网址 | 报告将 zero-RL 训练扩至 1T 参数的实验，描述发现到强化推理行为逐渐变尖锐的训练阶段和若干涌现行为。 | 作者点名图 |
| [2026-07-26 · 6a64ed69000000001302fed9](<https://www.xiaohongshu.com/explore/6a64ed69000000001302fed9>) · 图4 | Mathematics of Data Science | Afonso S. Bandeira; Amit Singer; Thomas Strohmer | [arXiv:2607.11938v1; textbook cover](https://arxiv.org/abs/2607.11938)<br>图中未见项目网址 | 数据科学数学教材/书籍封面，覆盖理论背景；图中没有摘要或章节细节。 | 作者点名图 |
| [2026-07-26 · 6a64ed69000000001302fed9](<https://www.xiaohongshu.com/explore/6a64ed69000000001302fed9>) · 图15 | Subliminal Clocks: Latent Time Modelling in Diffusion Language Models | Maximo Rulli et al. | [arXiv:2607.01774v2](https://arxiv.org/abs/2607.01774)<br>图中未见项目网址 | 研究扩散语言模型隐藏状态中的去噪时间表征，发现可探测并沿低维方向操控该潜在时钟。 | 作者点名图 |
| [2026-07-21 · 6a5668a1000000001101cdc4](<https://www.xiaohongshu.com/explore/6a5668a1000000001101cdc4>) · 图11 | Measuring the Gap Between Human and LLM Research Ideas | Ziyu Chen; Yilun Zhao; Arman Cohan (Yale; University of Chicago) | [arXiv:2607.01233v1](https://arxiv.org/abs/2607.01233)<br>[https://github.com/ziyuc/TasteGap](https://github.com/ziyuc/TasteGap) | 比较同一文献背景下人类与 LLM 生成的研究点子，发现 LLM 想法更集中于桥接/综合型路径，分布窄于人类研究品味。 | 作者点名图 |
| [2026-07-20 · 6a56680a000000000f015f5e](<https://www.xiaohongshu.com/explore/6a56680a000000000f015f5e>) · 图1 | LLM-as-a-Verifier: A General-Purpose Verification Framework | Jacky Kwok et al. (Stanford; UC Berkeley; NVIDIA Research) | [arXiv:2607.05391v1](https://arxiv.org/abs/2607.05391)<br>[https://llm-as-a-verifier.com](https://llm-as-a-verifier.com) | 用连续评分分布评估候选解，为编码、机器人和医疗任务提供可扩展验证信号，并用于 agent 进展监控和 RL 奖励。 | 作者点名图 |
| [2026-07-20 · 6a56680a000000000f015f5e](<https://www.xiaohongshu.com/explore/6a56680a000000000f015f5e>) · 图18 | When Does Continual Learning Require Learning | Anne Harrington et al. | [arXiv:2607.07847v1](https://arxiv.org/abs/2607.07847)<br>[https://github.com/anneharrington/studying-cl](https://github.com/anneharrington/studying-cl) | 把持续学习定义为适应环境变化的能力，比较 prompt、SFT、RL 与 context compression 等更新方式在不同变化条件下的表现。 | 作者点名图 |
| [2026-07-19 · 6a5667830000000011005c9a](<https://www.xiaohongshu.com/explore/6a5667830000000011005c9a>) · 图18 | Learning More from Less: Reinforcement Learning from Hindsight | Iris Xu et al. (MIT; Stanford; UC San Diego) | [arXiv:2607.09042v1](https://arxiv.org/abs/2607.09042)<br>图中未见项目网址 | 对 VLA 中失败但仍包含有效行为的 rollout 做 hindsight relabeling，提高昂贵机器人 RL 采样的利用率。 | 作者点名图 |
| [2026-07-18 · 6a566730000000001102f8b7](<https://www.xiaohongshu.com/explore/6a566730000000001102f8b7>) · 图1 | From Approximation to Emergence: A Theory of Deep Learning | Zhilin Zhao (Sun Yat-sen University) | Book; no arXiv ID visible<br>图中未见项目网址 | 深度学习理论书籍，按 approximation、optimization、generalization、emergence 组织。 | 作者点名图 |
| [2026-07-18 · 6a566730000000001102f8b7](<https://www.xiaohongshu.com/explore/6a566730000000001102f8b7>) · 图13 | Prescriptive Scaling Reveals the Evolution of Language Model Capabilities | Hanlin Zhang; Jikai Jin; Vasilis Syrgkanis; Sham Kakade | [arXiv:2602.15327v2](https://arxiv.org/abs/2602.15327)<br>页面图标显示 Blog / Datasets / Code，未读出 URL | 用 prescriptive scaling law 估计给定预训练计算预算可达到的下游能力边界，并分析其随模型代际变化的稳定性。 | 作者点名图 |
| [2026-07-17 · 6a56668d000000000f0077bf](<https://www.xiaohongshu.com/explore/6a56668d000000000f0077bf>) · 图9 | The Risk of KV Cache Compression | Lukas Haverbeck; Carmen Amo Alonso; Andres Felipe Posada-Moreno; Sebastian Trimpe; Marco Pavone | [arXiv:2607.01520v1](https://arxiv.org/abs/2607.01520)<br>图中未见项目网址 | 刻画 KV cache 的内在可压缩性与 minimax 风险，为因果掩码下的压缩算法提供理论设计原则。 | 作者点名图 |
| [2026-07-16 · 6a566604000000001102f65a](<https://www.xiaohongshu.com/explore/6a566604000000001102f65a>) · 图1 | Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents | Yifan Wu et al. (Meta AI) | [arXiv:2607.08716v1](https://arxiv.org/abs/2607.08716)<br>[https://github.com/yifannwu/proactive-memory-agent](https://github.com/yifannwu/proactive-memory-agent) | 把记忆从被动检索改成独立模块判断何时向长时程 agent 注入关键状态提示。 | 作者点名图 |
| [2026-07-16 · 6a566604000000001102f65a](<https://www.xiaohongshu.com/explore/6a566604000000001102f65a>) · 图3 | Foundations of Diffusion Language Models | Subham Sekhar Sahoo (Cornell University) | Dissertation; no arXiv ID visible<br>图中未见项目网址 | 博士论文封面，作为扩散语言模型的系统性基础读物；本图只有封面，未展示摘要。 | 作者点名图 |
| [2026-07-15 · 6a56657c000000000f031ef7](<https://www.xiaohongshu.com/explore/6a56657c000000000f031ef7>) · 图10 | How much can language models memorize? | John X. Morris; Chawin Sitawarin; Chuan Guo; Narine Kokhlikyan; G. Edward Suh; Alexander M. Rush; Kamalika Chaudhuri; Saeed Mahloujifar | 图中编号未完整显示<br>图中未见项目网址 | 区分对训练样本的记忆和对生成规律的泛化，并用压缩率量化模型对数据点的记忆程度。 | 作者点名图 |
| [2026-07-15 · 6a56657c000000000f031ef7](<https://www.xiaohongshu.com/explore/6a56657c000000000f031ef7>) · 图17 | Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories | Ali Behrouz; Fanoosh Hashemi; Adel Javanmard; Vahab Mirrokni | [arXiv:2606.03979v2](https://arxiv.org/abs/2606.03979)<br>图中未见项目网址 | 提出 sleep 阶段，把短期记忆蒸馏为稳定知识，并通过 dreaming 生成练习数据以持续自我改进。 | 作者点名图 |
| [2026-07-04 · 6a42a097000000000f02b56f](<https://www.xiaohongshu.com/explore/6a42a097000000000f02b56f>) · 图1 | Improving Neural Network Training by Decoupling the Magnitude and Direction of Weight Vectors | Alexander Hägele; Alejandro Hernández-Cano; Atli Kosson; Martin Jaggi | [arXiv:2606.25971v1](https://arxiv.org/abs/2606.25971)<br>[https://haegee.github.io/posts/magnitude-direction-decoupling/](https://haegee.github.io/posts/magnitude-direction-decoupling/) | 提出 magnitude-direction decoupling，将权重大小与方向分开优化，试图改善 Adam/Muon 训练的尺度控制和跨模型宽度迁移。 | 作者点名图 |
| [2026-07-05 · 6a42a1240000000011010bb7](<https://www.xiaohongshu.com/explore/6a42a1240000000011010bb7>) · 图1 | DanceOPD: On-Policy Generative Field Distillation | Wei Zhou et al. | [arXiv:2606.27377v1](https://arxiv.org/abs/2606.27377)<br>[https://DanceOPD.github.io](https://DanceOPD.github.io) | 面向 flow-matching 图像模型的 on-policy 蒸馏，让学生在自身 rollout 状态上组合多种生成能力。 | 作者点名图 |
| [2026-07-05 · 6a42a1240000000011010bb7](<https://www.xiaohongshu.com/explore/6a42a1240000000011010bb7>) · 图9 | The Verification Horizon: No Silver Bullet for Coding Agent Rewards | Qwen Team | [arXiv:2606.26300v1](https://arxiv.org/abs/2606.26300)<br>图中未见项目网址 | 分析 coding agent reward verification 的可扩展性、忠实度与鲁棒性，强调验证器必须随 agent 能力共同演化。 | 作者点名图 |
| [2026-07-03 · 6a429fc600000000110163c5](<https://www.xiaohongshu.com/explore/6a429fc600000000110163c5>) · 图3 | Autodata: An agentic data scientist to create high quality synthetic data | Ilia Kulikov et al. (FAIR at Meta) | [arXiv:2606.25996v1](https://arxiv.org/abs/2606.25996)<br>图中未显示项目 URL | 训练一个能生成、检查和评估训练/评测数据的 data-scientist agent，并继续 meta-optimize 该 agent。 | 作者点名图 |
| [2026-07-03 · 6a429fc600000000110163c5](<https://www.xiaohongshu.com/explore/6a429fc600000000110163c5>) · 图15 | Learning Process Rewards via Success Visitation Matching for Efficient RL | Raymond Tsao; Andrew Wagenmaker; Sergey Levine | [arXiv:2606.23640v1](https://arxiv.org/abs/2606.23640)<br>[https://success-visitation-matching.github.io](https://success-visitation-matching.github.io) | 从成功轨迹访问状态构造过程奖励，缓解稀疏终局奖励下 RL 的 credit assignment 问题。 | 作者点名图 |
| [2026-07-02 · 6a429f4b000000000f01ea62](<https://www.xiaohongshu.com/explore/6a429f4b000000000f01ea62>) · 图1 | TMAX: A Simple Recipe for Terminal Agents | Hamish Ivison; Junjie Oscar Yin; Rulin Shao; Teng Xiao; Nathan Lambert; Hannaneh Hajishirzi | 图中未见 arXiv 编号<br>[https://github.com/hamishivi/tmax](https://github.com/hamishivi/tmax) | 以较简单的 RL 配方训练终端 agent；摘要称其 9B 模型在 Terminal-Bench 2.0 上达到 27%，并释放数据、模型和代码。 | 作者点名图 |
| [2026-07-02 · 6a429f4b000000000f01ea62](<https://www.xiaohongshu.com/explore/6a429f4b000000000f01ea62>) · 图3 | You Don’t Need Strong Assumptions: Visual Representation Learning via Temporal Differences | Ninad Daithankar; Alexi Gladstone; Yann LeCun; Heng Ji | [arXiv:2606.15956v1](https://arxiv.org/abs/2606.15956)<br>[https://temporal-difference-vision.github.io](https://temporal-difference-vision.github.io)<br>[https://github.com/ninaddaithankar/TDV](https://github.com/ninaddaithankar/TDV) | 提出 Temporal Difference in Vision（TDV），借助相邻视频帧的因果关系学习表征，研究弱归纳偏置下的视觉表征学习。 | 作者点名图 |
| [2026-07-01 · 6a429e9000000000110043f1](<https://www.xiaohongshu.com/explore/6a429e9000000000110043f1>) · 图1 | Fantastic Pretraining Optimizers and Where to Find Them II: Hyperball Optimization | Kaiyue Wen; Xingyu Dang; Kaifeng Lyu; Tengyu Ma; Percy Liang | [arXiv:2606.16899v1](https://arxiv.org/abs/2606.16899)<br>图中未见项目网址 | 提出 Hyperball，将权重矩阵与更新范数约束为固定尺度；报告在 Qwen3 风格模型上相对基线可获得训练 token 等效加速。 | 作者点名图 |
| [2026-07-01 · 6a429e9000000000110043f1](<https://www.xiaohongshu.com/explore/6a429e9000000000110043f1>) · 图12 | Data Augmentation: A Fourier Analysis Perspective | Behrooz Tahmasebi; Melanie Weber; Stefanie Jegelka | [arXiv:2606.24418v1](https://arxiv.org/abs/2606.24418)<br>图中未见项目网址 | 从 Fourier 分析和表示理论研究群不变性下的部分数据增强，解释随机抽取群变换子集何时能接近完整增强的统计效果。 | 作者点名图 |
| [2026-07-01 · 6a429e9000000000110043f1](<https://www.xiaohongshu.com/explore/6a429e9000000000110043f1>) · 图16 | The Hitchhiker’s Guide to Agentic AI: From Foundations to Systems | Haggai Roitman | [arXiv:2606.24937v1](https://arxiv.org/abs/2606.24937)<br>图中未见项目网址 | 图中是 agentic AI 教程/书籍的封面页，按 foundations 到 systems 组织内容；作者推荐作为结构化入门材料。 | 作者点名图 |
| [2026-06-30 · 6a429d57000000001003f063](<https://www.xiaohongshu.com/explore/6a429d57000000001003f063>) · 图1 | DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation | Xin Cheng et al. (Peking University; DeepSeek-AI) | 图中未见 arXiv 编号<br>DeepSeek 页面抬头；摘要指向 DSpark checkpoints 与 DeepSpec | 推测解码框架用置信度调节验证长度，降低高并发推理中验证浪费；摘要称在 DeepSeek-V4 服务流量下提升生成速度。 | 作者点名图 |
| [2026-06-30 · 6a429d57000000001003f063](<https://www.xiaohongshu.com/explore/6a429d57000000001003f063>) · 图14 | Provable Benefits of RLVR over SFT for Reasoning Models: Learning to Backtrack Efficiently | Stanley Wei; Juno Kim | [arXiv:2606.22938v1](https://arxiv.org/abs/2606.22938)<br>图中未见项目网址 | 理论比较 RLVR 与 SFT，聚焦模型是否学会在错误路径上回溯；文章主张 RL 能用结果奖励学到高效 backtracking。 | 作者点名图 |
| [ · 6a2fe53800000000080246c1](<https://www.xiaohongshu.com/explore/6a2fe53800000000080246c1>) · 图1 | RLCSD: Reinforcement Learning with Contrastive On-Policy Self-Distillation | Authors not recorded in this visual pass | [arXiv:2606.11709v1](https://arxiv.org/abs/2606.11709)<br>[https://github.com/THU-BPM/RLCSD](https://github.com/THU-BPM/RLCSD) | On-policy self-distillation with contrastive reinforcement-learning signals. | 先行样例 |
| [ · 6a2fe53800000000080246c1](<https://www.xiaohongshu.com/explore/6a2fe53800000000080246c1>) · 图2 | Harness Updating Is Not Harness Benefit: Disentangling Evolution Capabilities in Self-Evolving LLM Agents | Authors not recorded in this visual pass | [arXiv:2605.30621v1](https://arxiv.org/abs/2605.30621) | Separates the ability to update an agent harness from the benefit those updates actually produce. | 先行样例 |
| [ · 6a2fe53800000000080246c1](<https://www.xiaohongshu.com/explore/6a2fe53800000000080246c1>) · 图3 | On the Relationship Between Activation Outliers and Feature Death in Sparse Autoencoders | Authors not recorded in this visual pass | [arXiv:2605.31518v1](https://arxiv.org/abs/2605.31518) | Studies links between activation outliers and feature death in sparse autoencoders. | 先行样例 |
| [2026-06-21 · 6a2fe53800000000080246c1](<https://www.xiaohongshu.com/explore/6a2fe53800000000080246c1>) · 图7 | Reinforcement Learning from Rich Feedback with Distributional DAgger | Rishabh Agrawal; Jacob Fein-Ashley; Paria Rashidinejad | [arXiv:2606.05152v1](https://arxiv.org/abs/2606.05152)<br>[https://rishabh-1086.github.io/project-distIL](https://rishabh-1086.github.io/project-distIL)<br>[https://github.com/rishabh-1086/distIL](https://github.com/rishabh-1086/distIL) | DistIL 将丰富的轨迹、工具输出和自评反馈蒸馏给策略；图中给出科学推理、编码和数学等任务结果。 | 作者点名图 |

其余 1,454 张已下载并登记笔记来源、图序和本地文件，但尚未逐张视觉阅读；当前不能据此断言每张图的材料标题或研究内容。全量机器索引与已核对摘要位于本地 `.cache/xhs-extracted/image-source-index.jsonl`；逐张视觉记录位于 `.cache/xhs-extracted/image-visual-review.jsonl`。
