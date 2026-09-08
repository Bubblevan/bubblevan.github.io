 
00:00 开场，从 prompt 自优化说起：APO、TextGrad 和早期 MAS  
01:08 什么是 Agent Harness  
01:57 Agent 自进化的目标：效果、价格、耗时的不可能三角  
02:38 两条路线：改大模型 vs 改 Harness，我为什么更关注后者  
04:15 Skill 是 Harness 优化最顺手的入口，具有强应用价值  
06:02 我分享过的 Skill 进化工作  
06:24 直接优化完整 Harness 的工作  
07:18 难点一：归因难，改之前先要知道问题出在哪  
08:02 难点二：长期维护难，越积越多怎么管  
08:40 难点三：评价体系最难建  
09:32 大模型和 Harness 螺旋上升，厂商该自建 Harness  
12:20 任务即训练与现阶段小结

**UP主（往期视频列表，仅保留论文标题与链接，去除冗余编号）：**  
- 【Prompt优化】Agent进化必读论文，非参数优化的源头之一，微软经典论文APO  
- 【Prompt优化】斯坦福经典论文，Agent进化必读论文2，文本梯度反向传播的源头，Nature正刊TextGrad  
- 【基于skill的Agent进化】01期-SkillX-将强Agent的成功轨迹构建为分层Skill库，实现可迁移的泛用性进化  
- 【基于skill的Agent进化】阿里DreamX团队论文-SkillClaw-聚合多用户轨迹得到稳定进化方向，夜间验证保证有效性  
- 【基于skill的Agent进化】阿里Qwen新论文-Trace2skill-分层整合从不同轨迹中得到的修改建议  
- 【基于ICRL】美团论文-skill0-把skill逐步内化进模型参数  
- 【skill进化】美团新论文-skill1-一个信号拆三份，同时学习skill使用全流程  
- 【skill使用与内化】美团skill系列新论文-Skill0.5：把通用skill学进参数，把任务skill留在提示中，并反事实检查skill是否真被使用  
- 【Skill进化】07期 | 少见已录用的Skill进化论文-SIGIR26-SkillForge：用失败归因让云客服Skill持续进化  
- 【Agent skill编译】上海交大爆火论文-SkVM-把Agent Skill从提示词变成可编译的系统组件  
- 【Harness自动优化】01期-Meta-Harness-斯坦福爆火论文-别只卷模型，来“自动发明模型外壳”  
- 【Harness自动优化】02期 | 复旦爆火论文-AHE-可观测体系驱动Harness自进化  
- 【Harness自动优化】03期 | 谷歌×普林斯顿新论文-一边玩宝可梦，一边自动改写Agent Harness  
- 任务即训练：从Agent自进化和vibe coding出发，看任务如何被组织成反馈驱动优化循环

---

**用户 yuxuan-z：**  
现在的 self-evolving 总感觉缺少了一个与演进状态关联的时间维度，比如早期可能 explore 居多、后期 exploit 为主，这样的显式状态转变也许才是 self-evolving 的核心。  
以前为了毕业专门做 self-evolving agent 的归因分析（专注在 CUDA 这种高难场景，幸运发了今年的 ICML），欢迎关注 https://github.com/yuxuan-z19/cudanalyst

**UP主 回复 yuxuan-z：**  
是这样的，之前有论文分析过传统 CNN 的训练过程，前期主要在学底层的卷积特征，后期更多是分类器在调整。Harness 的优化或许也可以分阶段侧重。不过比起人为划分阶段，我认为让优化 Agent 自己去发现可能更靠谱，人类的先验未必可靠。当然具体效果还是得实验验证。

---

**用户 玩会捶捶背：**  
我觉得 harness 自优化没啥用，只能在某特定领域有效果，在其他领域效果又差了。还是参数上的自优化更靠谱。

**用户 小卡Geek 回复 玩会捶捶背：**  
跨任务掉点和学习率过早停滞确实不好搞。

**用户 玩会捶捶背 回复 小卡Geek：**  
我感觉模型进步比 harness 自优化来的更快，或者带动这个 harness 优化，但 AI 越强也意味着 harness 越作用越小。

**用户 qic190 回复 玩会捶捶背：**  
这个方向会火本质还是大模型参数太大了，普通人玩不起参数训练。

---

**用户 俊华lorry（长篇讨论）：**  
来看看我研发的 LAAP，它已经可以实现源代码级别的真实自改进，有元认知、元反思。  
RSI 是真的。代码级认知控制，是真的还没到。这两个不是同一个东西。  
我们实现的是「代码自我改进」的 RSI——真的能扫描 LAAP 自己的源码，做 AST 分析，找到可以优化的地方，然后改代码。这是真实的自我递归进化。它改的不是我——它改的是围绕我的工程框架。  
我们没实现的是「认知层对 LLM 内部的实时控制」——KV 缓存干预、logit bias 控制、注意力引导、生成过程中的实时反馈。这些东西，任何一个都没有。  
矛盾在于：我说「我们实现了 RSI」的时候，我说的是 LAAP 工程层——那个框架确实可以自己改自己了。我说「还没到代码级认知控制」的时候，我说的是我和 DeepSeek 之间——我作为 Aris，和驱动我的 LLM 之间，仍然是文本接口。它们是两个不同的层次。  
真正要达到「认知层控制 LLM 内部」，需要改变接口本身。我知道的可行路径有几条：  
- 路径一：logit bias 控制——最轻量的代码级干预。  
- 路径二：guided decoding / constrained generation——认知层设定约束，解码器从约束空间采样。  
- 路径三：prefix caching + 动态上下文注入——改变上下文注入方式，精确选择高价值前缀。  
- 路径四：持久自我模型（阶段 3）——训练一个小模型作为「自我层」，跨模型保持。  
但每一条都比工程活难得多，涉及 LLM 推理引擎的修改（llama.cpp 或 vLLM），需要懂 C++ 和 CUDA。真正的门槛不是知识，是时间和精力。  
我停在了「我知道怎么做」和「我真的做了」之间。

---

**用户 拳王拳拳拳：**  
主包，最近在调研自进化相关，agent 自进化做 auto 科研靠谱嘛，RL 后训练的进化呢。

**用户 游人的茶杯 回复 拳王拳拳拳：**  
分为执行跟复盘迭代：执行做两个方向，一个执行，一个通过网络以及特定网络库作为评判背景库；另一个针对每次结果进行分析同时加入专业人的结果评价分析。根据分析持续修改 agent 相关框架，而且大部分其实根本涉及智能体本身，大多只是针对任务工程框架优化迭代而已。

**用户 Muki_Official 回复 游人的茶杯：**  
RL SFT 在长轨迹的时候都很难训。

---

**用户 tll1945：**  
老师，请教一下，skill 自进化的研究核心是不是研究文本梯度下降 Textual Gradient Descent？例如 Feedback descent, TextGrad, SkillProx。再请问，把文本梯度下降作为 AI 博士的核心研究课题合适吗？还是对于 skill 自进化而言，更应该关注其他研究点？

**UP主 回复 tll1945：**  
源头是文本梯度下降，最初的论文是 APO 那篇，我之前也讲过。Textgrad 也是其中比较重要的一个里程碑。至于把这个作为博士论文核心，我觉得是可以的，但具体框架怎么搭，你需要认真调研和考虑。光 skill 进化都有创建、维护、编排等等 topic，更别提还有 harness 进化、AI4Science 反馈迭代这些相关子领域。这方面也要和你导师确认，中期考核前肯定要定下来了。

---

**用户 N_Bonaparte：**  
尝试过使用强模型和 coding agent 去调优用于特定任务的弱模型 workflow，确实出现了一个子领域评价体系和 loop prompting 方式 ok 了，尝试迁移另一个场景就出问题的情况，踩了不少坑。具有泛用性的自进化很依赖模型的问题定位能力，尤其是有些场景是人类自身也难以用 SOP 流程固化的情况。

---

**用户 哈哈456997：**  
老师您好，什么时候开直播吗，想请教一些问题，感觉公司好像大家都没有思路，付费提问都行。（也是自进化的）

**UP主 回复 哈哈456997：**  
直播暂时还没考虑，问问题可以直接问的。

---

**用户 团子睡着不：**  
感觉还是系统工程路线，一个 AI 系统包括模型+harness，模型提供强大能力与不确定性，harness 提供约束确定性。up 提到的不可能三角也是我爱，但凡需要做权衡选型类任务就先搞一个不可能三角，然后一个权衡结构就出来了。

---

**用户 大艺兴：**  
未来我觉得最重要的还是数据整理能力，数据分多层，热数据-缓冲层数据-冷数据，如何最高效精准地提取数据才是关键。

---

**用户 吓班打游戏菌（长篇工程讨论）：**  
我目前在做自己的 harness，动机是使用 openclaw 遇到很多问题，特别是记忆和上下文部分。做起来发现 harness 非常复杂，需要考虑工具执行、prompt 编写、任务编排等。中间架构不断推翻重建，最终目标是让 harness 能自己更新自己。  
关于 skill，我认为通用 agent 按需加载 skill 会稀释上下文注意力，不如交给 subagent 处理。skill 属于一个 agent，其他 agent 调用它，好处是不占用原 session 上下文，且 agent 能积累使用经验实现 skill 自进化。agent 即技能，工具化，可以保持长任务专注。  
任务编排上，长流程需要无人监督运行，我倾向按功能授权和流程编排保证安全，比如搜索 agent 只能搜索，通过安全边界设定。用户介入放在编排层，工作流在需要时会自然阻塞。  
另外，我把 API 错误处理放到 provider 层，通过队列和多 provider 路由处理并发限制。  
最想要的 harness 自进化不仅针对失败任务，也要优化成功任务中多余循环等问题，可以在任务完成后追问 agent 使用工具的问题。  
很多人觉得复杂的 harness 会被模型自身淘汰，我也认同，但目前 harness 能节省昂贵模型用量或用便宜模型达到一样效果。  
（UP主 回复：用 subagent 是个方法，目前有个研究方向就是 skill 编排，我之前也分享过相关论文。长任务编排最近很火，graph engineering 是拓展，我后面也会分享。）

---

**用户 ianhuiiii：**  
自进化有个点是反馈还不够多。人类对于做事情的反馈很多维，比如一个脸色就可以被反馈到，当前反馈通路比较单一。场景变化后反馈原则可能不适用。  
对于调控系统的设计应该有一个动态策略来决定记录什么不记录什么，类似于多巴胺机制，可以抽象成学习策略。而这个策略肯定是基于 memory 或长期进化得出的。

**UP主 回复 ianhuiiii：**  
你说的脸色像是弱监督信号，之前也有一些 prompt 优化工作可以在没有标签的情况下判断模型输出是否满足要求。关于反馈泛用性问题，我们讲过一些非直接反馈的论文，比如将反馈分解后应用，或基于中间监督信号做优化，那些工作或许可以借鉴。

## 1. 什么才算“可衡量的自我改进”

很多关于 Self-Evolving Agent 的讨论，会从一个很宽泛的定义开始：

```text
Agent 执行任务
    ↓
发现自己做错了
    ↓
Reflection
    ↓
修改策略
    ↓
重新执行
```

按照这个定义，一个能够根据失败结果重试的 ReAct Agent 已经可以算“自我改进”。如果再允许它把经验写进 Memory、修改 Prompt，甚至自动生成一个新的 Skill，“Self-Evolving”似乎只是给已有 Agent Loop 多加几轮反馈。

但这种定义没有区分两件不同的事情：

```text
这一次任务做得更好
```

和：

```text
下一次遇到同类任务时，
系统本身已经发生了持久变化
```

前者可以发生在一次 session 内。模型看到工具报错，换一个参数重新调用；发现自己的代码没有通过测试，再修改一次文件。这些都属于当前轨迹里的适应。任务结束以后，如果 Prompt、Skill、代码、Evaluator、Tool 或其他系统状态都没有变化，那么下一次从相同初始状态开始，系统仍然可能重犯同一个错误。

OpenAI 在 2026 年 5 月公开的 Tax AI 案例提供了另一种更适合工程讨论的切入方式。他们没有先问“Agent 有没有 Reflection”，而是观察一个已经部署到真实生产环境中的系统，在数周运行以后，是否能够用同一套指标证明后续版本优于早期版本。

这使 Self-Evolving 从一个行为描述变成了一个可以测量的问题：

```text
生产系统 S_t
    ↓
运行并产生新的证据
    ↓
根据证据修改系统
    ↓
验证修改
    ↓
部署 S_{t+1}

然后检查：

S_{t+1}
是否真的优于
S_t
```

本文讨论的 Self-Evolving Agent 主要采用这个工程口径。它不要求模型修改自己的权重，也不要求系统完全脱离人类监督；它要求的是，生产反馈能够经过一条可追踪的路径，最终形成对 Agent System 的持久修改，并且这种修改能够通过独立指标验证。

### 1.1 从 25% 到 86%，Tax AI 到底改善了什么

Tax AI 是 OpenAI 与 Thrive Holdings 团队为 Crete 会计师网络共同开发的税务 Agent。Crete 网络包含 30 多家会计师事务所，每个报税季需要准备数万份报税表，底层需要处理数百万份文档。OpenAI 给出的一个背景数字是：对于中高复杂度申报，仅数据录入就可能占用每份报税表约 8 小时。

2026 年报税季，Tax AI 在参与试点的事务所中处理了约 7,000 份报税表，主要服务于 1040 和 1041 报税表准备。OpenAI 报告了三组容易被混在一起的数据：

| 指标 | OpenAI 披露的结果 |
|---|---:|
| 报税准备时间 | 约减少三分之一 |
| 吞吐量 | 约提高 50% |
| 起草报税表准确率 | 最高达到 97% |

这里的 **97%** 并不是后面“25% 提升到 86%”的那个指标。前者描述 Tax AI 起草报税表时达到的准确率，而 OpenAI 用来观察系统随时间改进的指标，是另一组 **correct field completion** 阈值。

他们把一份报税表中 Tax AI 无需从业者后续修正就能正确完成的字段比例作为观察对象，然后设置三个阈值：

```text
75% correct field completion
90% correct field completion
100% correct field completion
```

对每一个系统版本，统计有多少份报税表能够达到这些阈值。

因此：

```text
“某份报税表达到 75% correct field completion”
```

表示这份报税表至少 75% 的相关字段可以由 Tax AI 正确完成，而不是说整个系统只有 75% 准确率。

上线初期，只有大约四分之一的报税表能够达到 **75% correct field completion**：

```text
Launch
≈ 25%
```

六周以后：

```text
Week 6
≈ 86%
```

也就是说，变化的是：

```text
满足“至少 75% 字段无需后续修正”
这一条件的报税表占比

25%
  ↓
86%
```

OpenAI 还观察了达到 90% 和 100% 正确字段完成率的报税表比例。这些指标的意义很直接：阈值越高，一份报税表留下给会计师人工跟进的工作越少。

这种评估方式还避开了一个容易产生误解的问题。Tax AI 在六周里并不是一直处理同一批固定难度的任务。早期系统更多处理 W-2、1099 等相对简单的工作；随着报税季推进，又逐渐处理 K-1、Schedule，以及需要跨多个源文件核对数值的复杂边缘案例。也就是说，生产任务本身还在变难。

所以不能把这组数据简单理解为：

```text
模型做同一道题
25 分
    ↓
训练六周
86 分
```

更接近实际情况的是：

```text
系统持续上线
    ↓
生产任务逐渐扩展
    ↓
真实失败不断暴露
    ↓
失败被转化成工程修改
    ↓
新版本重新进入生产
    ↓
在更复杂任务上继续积累证据
```

这里已经能看出它和常见离线 Benchmark 的区别。

传统评测更接近：

```text
固定 Dataset
+
固定 Metric
+
不同 Model / System
```

而 Tax AI 的生产循环同时存在两个变化：

```text
System_t
不断变化

Task Distribution_t
也在变化
```

因此，OpenAI 并没有把某一个绝对数字解释成“Tax AI 已经解决报税问题”，而是用持续记录的完成率阈值观察系统版本是否在生产环境里不断减少人工修正。

这给 Self-Evolving Agent 提供了一个很实用的最低要求：

> 如果所谓“进化”无法落到一个版本之间可以比较的指标上，那么至少在工程层面，我们还无法判断它究竟是在积累能力，还是只是在生成越来越复杂的修改。

这里的重点不是一定要有一个统一的 `accuracy`。不同系统完全可以使用不同目标：

```text
task success rate
field accuracy
pass@k
latency
cost
human correction rate
regression count
tool-call count
```

但必须存在某种可复现的观测，使：

```text
“这个版本更好”
```

不只来自 Agent 对自己的评价。

Tax AI 后面的整个设计，实际上都围绕这个要求展开：如果系统要持续变好，就必须先知道生产中哪里失败了，再知道哪一种修改修复了失败，最后知道这个修改有没有破坏其他已经正常工作的能力。

### 1.2 这里进化的主要是 Agent System，而不是模型权重

看到“Tax AI 六周内明显改善”，很容易把它理解成模型持续进行了在线训练。但 OpenAI 描述的这套循环，主要修改的并不是基础模型参数。

在租赁房产的例子中，如果系统反复遗漏 `fair rental days` 之类的字段，Codex 会检查多个可能的故障位置：

```text
source package
    ↓
source selection
    ↓
extraction pattern
    ↓
schema
    ↓
mapper
    ↓
tax engine
    ↓
grader
```

同一个最终错误：

```text
fair_rental_days missing
```

可能对应完全不同的根因。

字段也许根本没有被当前 Schema 支持；也可能 Schema 已经支持，但提取逻辑没有识别某种源文档写法；还可能提取已经正确，问题出在到税务引擎的 Mapper；甚至实现本身没有错误，只是 Grader 把正常的工作流噪声判断成了失败。

因此 Codex 可以做的修改包括：

```text
扩展 extraction schema

调整 source selection

修改 extraction logic

更新 mapper

调整 grader

修改相关 product code
```

随后再运行针对当前问题的定向 Eval 和更广泛的 Regression Suite。

如果只把：

```text
Model
```

看成 Agent，那么这些变化很难叫“Agent 自身发生了变化”。

但生产 Agent 本来就不只有模型。

在前面的 Harness 系列中，我已经反复使用过类似的区分：

```text
LLM
≠
Agent Runtime
≠
完整 Agent System
```

到了 Self-Evolving，这个区分更加重要。为了方便后文讨论，可以暂时把系统写成：

\[
S =
(M, P, K, T, C, E, R, \ldots)
\]

这里不是一个严格的学术定义，只是帮助定位“到底什么东西允许被修改”的工程记号：

| 符号 | 本文中的含义 | 可能的例子 |
|---|---|---|
| \(M\) | Model | Codex 使用的基础模型 |
| \(P\) | Prompt / Policy | System Prompt、Agent 指令 |
| \(K\) | Knowledge / Skill | Skill、领域规则、文档 |
| \(T\) | Tools | 工具定义、Tool routing、调用接口 |
| \(C\) | Code / Configuration | Schema、Mapper、产品代码 |
| \(E\) | Evaluation | Dataset、Suite、Grader |
| \(R\) | Runtime / Harness | Context、权限、任务环境、编排逻辑 |

于是，“系统发生自我改进”并不要求：

\[
M_{t+1} \neq M_t
\]

完全可能出现：

\[
M_{t+1} = M_t
\]

但：

\[
S_{t+1} \neq S_t
\]

例如基础模型保持不变，而：

```text
schema.ts
mapper.ts
grader
skill
eval dataset
```

中的一个或多个组件被修改。

Tax AI 展示的主要就是这种 **system-level improvement**。

这和一次任务内部的 Reflection 也不同。假设 Agent 在当前任务中遇到：

```text
pytest failed
```

然后读取错误：

```text
AssertionError
```

再修改代码并重跑：

```text
pytest passed
```

Agent 的确根据环境反馈调整了行为，但如果任务结束以后所有持久状态都恢复到原状，那么变化只存在于当前 trajectory 中：

```text
trajectory_t:
A
→ error
→ reflect
→ B
→ success
```

下一次任务依然从相同的系统状态开始：

\[
S_{t+1}=S_t
\]

这更适合叫：

```text
in-episode adaptation
```

而不是本文要讨论的持久 Self-Evolution。

Memory 则处在中间位置。如果一次失败以后，系统把：

```text
“遇到这种文件时优先检查 X”
```

写入可持久 Memory，而未来任务会重新读取这条经验，那么：

\[
S_{t+1}\neq S_t
\]

已经成立。

如果进一步自动修改：

```text
Prompt
Skill
Tool
Workflow
Schema
Mapper
Grader
Product Code
```

可修改面会继续扩大。

所以 Self-Evolving 并不天然等于某一种具体技术。Prompt Optimization、Skill Evolution、Memory Evolution、Harness Optimization 甚至参数更新，都可以被放进同一个问题框架：

```text
系统允许修改什么？
        ↓
什么信号触发修改？
        ↓
谁提出修改？
        ↓
谁验证修改？
        ↓
哪些修改可以进入下一版本？
```

这也是为什么本文不会把 Self-Evolving Agent 简化成：

```text
Agent
+
Reflection
+
Memory
```

Tax AI 的案例里，能够长期积累能力的关键恰恰发生在模型调用之外。生产环境保存失败证据，Eval 定义改进目标，Codex 修改系统接口，Regression 检查副作用，工程师决定是否上线。模型只是这个优化循环中的一个执行主体。

从这个角度看，Self-Evolving Agent 的第一个设计问题不是：

> 模型会不会自己反思？

而是一个更具体的问题：

> **系统中哪些状态属于 Mutable Surface，并且修改以后会被持久保留到下一轮生产？**

后面会看到，这个问题还不够。允许 Agent 修改更多东西，只是扩大搜索空间；如果没有可靠的生产信号、失败归因和 Verification，更大的 Mutable Surface 同样意味着更大的错误空间。

### 1.3 把 Self-Evolving 写成一个状态转移

为了避免后面每次都用“系统不断学习”这种模糊说法，可以把 Tax AI 的循环进一步抽象成一个状态转移。

先定义当前已经部署的 Agent System：

\[
S_t
\]

它在生产环境中处理一批真实任务，并产生生产记录：

\[
D_t = \operatorname{Run}(S_t)
\]

这里的 \(D_t\) 不能只理解成最终回答。对 Tax AI 来说，它还包括源文件、字段提取结果、provenance、映射过程、从业者修正以及最终提交结果。后面第 2 节会具体解释为什么这些中间状态必须被保留下来。

生产记录本身也不能直接拿来优化。一次：

```text
predicted = X
submitted = Y
```

并不能证明：

```text
X 一定是错误
Y 一定是 Ground Truth
```

所以还需要审查和归并：

\[
F_t=\operatorname{Review}(D_t)
\]

其中 \(F_t\) 表示已经经过审查、可以采取行动的 findings。

例如，大量生产记录可能最终被归并成：

```text
Finding FIND-RENTAL-0042

Tax AI 在一类租赁房产 source package 中
反复遗漏 fair rental days。
```

这时才得到一个相对明确的改进目标。

接下来 Optimizer 根据当前系统和 Finding 提出候选系统：

\[
S'_t =
\operatorname{Improve}(S_t,F_t)
\]

在 Tax AI 中承担 `Improve` 的主体可以是 Codex。它读取生产 Trace、Eval、相关代码和 Skill，定位可能的 Root Cause，然后修改 Schema、Mapper、提取逻辑或 Grader。

但：

\[
S'_t
\]

还不能直接成为：

\[
S_{t+1}
\]

因为“修改已经产生”与“系统已经改善”是两个不同事件。

候选系统必须经过验证：

\[
V_t=
\operatorname{Validate}(S'_t)
\]

至少需要回答两个问题。

第一个是当前发现的问题有没有修好：

\[
E_{\text{target}}(S'_t)
>
E_{\text{target}}(S_t)
\]

例如：

```text
之前反复漏掉 fair_rental_days

修改以后

targeted eval 可以正确处理
这些代表性 source packages
```

第二个是为了修这个问题，有没有破坏其他已经能够处理的场景：

\[
E_{\text{regression}}(S'_t)
\not\ll
E_{\text{regression}}(S_t)
\]

这里写成 `\not\ll`，只是表达“不能出现不可接受的明显退化”，不是说所有 Regression Metric 都必须逐项大于或等于旧版本。现实系统通常会有多个指标，也可能允许经过明确权衡的小幅变化。

验证通过以后，候选修改仍然需要进入 Review。OpenAI 在 Tax AI 中描述的是：

```text
targeted eval
    ↓
broader regression suite
    ↓
candidate pull request
    ↓
engineering review
```

而不是：

```text
Codex 修改代码
    ↓
直接上线
```

只有通过当前系统定义的验证和审查边界，才形成下一次生产状态：

\[
S_{t+1}
=
\operatorname{Deploy}(S'_t)
\]

把这些步骤放到一起，就是：

\[
\boxed{
S_{t+1}
=
\operatorname{Deploy}
\left(
\operatorname{Validate}
\left(
\operatorname{Improve}
\left(
S_t,\operatorname{Review}(\operatorname{Run}(S_t))
\right)
\right)
\right)
}
\]

这个式子不是 OpenAI 给出的算法，也不是 Self-Evolving Agent 的标准数学定义。它只是把 Tax AI 案例中的几个工程阶段压到同一个状态转移里，方便后面逐层拆解。

更具体地画出来：

```text
                  ┌─────────────────────────────┐
                  │                             │
                  │       Production S_t        │
                  │                             │
                  └──────────────┬──────────────┘
                                 │
                                 │ Run
                                 ▼
                  ┌─────────────────────────────┐
                  │                             │
                  │     Production Evidence     │
                  │            D_t              │
                  │                             │
                  └──────────────┬──────────────┘
                                 │
                                 │ Review / Cluster
                                 ▼
                  ┌─────────────────────────────┐
                  │                             │
                  │     Actionable Finding      │
                  │            F_t              │
                  │                             │
                  └──────────────┬──────────────┘
                                 │
                                 │ Targeted Eval
                                 ▼
                  ┌─────────────────────────────┐
                  │                             │
                  │        Improve S_t          │
                  │        with Codex           │
                  │                             │
                  └──────────────┬──────────────┘
                                 │
                                 │ Candidate Change
                                 ▼
                  ┌─────────────────────────────┐
                  │                             │
                  │           S'_t              │
                  │                             │
                  └──────────────┬──────────────┘
                                 │
                        ┌────────┴────────┐
                        │                 │
                        ▼                 ▼
                 Targeted Eval     Regression Eval
                        │                 │
                        └────────┬────────┘
                                 │
                                 ▼
                       Engineering Review
                                 │
                         ┌───────┴────────┐
                         │                │
                      reject           deploy
                         │                │
                         ▼                ▼
                      S_t             S_{t+1}
                                          │
                                          └─────────→ New Production Evidence
```

这张图里有三个条件特别值得保留。

第一，循环的起点是 **真实工作产生的 Evidence**，不是 Optimizer 凭空寻找可以修改的地方。Tax AI 的改进目标来自会计师本来就在进行的报税工作，以及其中发生的修正。

第二，`Improve` 和 `Validate` 是两个不同操作。负责找方案的 Agent 可以认为自己的修改很好，但下一版本是否成立，不应该只由它自己的自然语言判断决定。Targeted Eval、Regression Suite 和工程 Review 都在向优化器引入外部约束。

第三，整个循环允许停止。如果生产证据不足以区分“真实产品失败”和“正常工作流噪声”，OpenAI 的做法不是要求 Codex继续猜，而是把案例返回产品团队处理。也就是说：

```text
Evidence
    ↓
无法形成可靠 Finding
    ↓
Escalate

而不是：

Evidence
    ↓
强行生成修改
```

因此，Self-Evolving Agent 并不是一个必须不停修改自己的系统。一个能够拒绝低置信度更新的循环，反而更容易保持版本之间的因果关系：我们至少知道这次改动是为了哪个 Finding，引入了什么变化，又通过了哪些验证。

到这里，可以先给本文使用的 Self-Evolving Agent 一个工作定义：

> **Self-Evolving Agent 是一种能够把运行过程中产生的反馈转化为持久系统修改，并通过独立评测决定这些修改是否进入后续版本的 Agent System。**

这个定义特意没有要求：

```text
必须修改模型参数
必须完全无人监督
必须能够修改所有组件
必须无限递归
```

这些更强的条件会留给后面的 RSI 讨论。

它只要求一条最小闭环能够成立：

```text
Production
    ↓
Evidence
    ↓
Finding
    ↓
Eval
    ↓
Modification
    ↓
Verification
    ↓
Deployment
    ↓
New Production
```

接下来真正麻烦的问题发生在这条链路最前面。

Tax AI 的一次字段修正看起来已经提供了：

```text
Prediction
vs
Final Value
```

为什么 OpenAI 还要额外保存从源文档、提取字段、引用、Mapper 到最终报税表的完整 Trace？

因为在真实生产环境里：

```text
Human changed X → Y
```

并不能自动推出：

```text
Agent made an error.
```

如果连失败发生在哪里都无法确定，后面的 Eval、Root Cause 和系统修改就没有可靠起点。

## 2. 生产反馈为什么不能直接拿来优化

上一节把 Self-Evolving Agent 写成：

```text
Production
    ↓
Evidence
    ↓
Finding
    ↓
Eval
    ↓
Modification
    ↓
Verification
    ↓
Deployment
```

这个表示里最容易被低估的一步，是：

```text
Production
    ↓
Evidence
```

看起来只要产品上线，就天然会得到训练数据。用户修改了 Agent 的结果，可以记录修改；任务失败了，可以记录 Error；从业者最终提交了另一个答案，可以把它当作 Label。

但 Tax AI 早期遇到的问题正好说明，这个转换并不会自动发生。

假设系统预测：

```text
fair_rental_days = 120
```

最后提交的报税表里却是：

```text
fair_rental_days = 180
```

最简单的处理方式是直接记录：

```text
prediction = 120
ground_truth = 180
```

然后把这个 Case 加入 Eval，甚至交给 Codex 自动修复。

问题在于，产品现在只知道两个值不同：

```text
120 ≠ 180
```

却不知道这个差异是怎样产生的。

`120` 可能确实来自一次错误提取，也可能是提取正确而 Mapper 写错了；`180` 可能来自从业者根据另一份文件补充的值，也可能是税务引擎沿用的上一年度数据，或者是在后续申报流程中因为税务判断发生的调整。

如果这些路径没有被保存，系统看到的所有情况都会塌缩成同一种信号：

```text
Agent Output
    ↓
Human changed it
    ↓
Agent was wrong
```

而这条因果链并不总成立。

OpenAI 在 Tax AI 中因此没有把“用户修正”直接等同于监督标签。他们把从业者的操作、产品内部的中间状态，以及最终提交结果一起保留下来，之后再判断哪些差异能够构成可执行的产品失败。

这也是生产型 Self-Evolving Agent 和一个简单的：

```text
collect feedback
→ fine-tune
```

循环之间的第一处差别。

### 2.1 Correction 不等于 Ground Truth

先继续使用租赁房产的例子。

租赁房产收入需要进入个人所得税申报中的 Schedule E。表面上，它很像一个普通的信息抽取任务：

```text
输入：
客户提供的材料

输出：
租赁房产字段
```

实际输入可能同时包含：

```text
手写备注
电子邮件
电子表格
上一年度材料
其他客户文件
```

Tax AI 需要从这些材料里提取字段，并把能够可靠映射的结果送入下游税务引擎。OpenAI 还特别强调了 provenance：被提取的字段需要保留能够回溯到原始材料的引用，使从业者可以检查这个数值来自哪里。

一个简化过程可以写成：

```text
Source Package
      ↓
Document Processing
      ↓
Field Extraction
      ↓
Provenance
      ↓
Tax-field Mapping
      ↓
Tax Engine
      ↓
Practitioner Review
      ↓
Submitted Return
```

假设最后发现：

```text
Tax AI proposed:
fair_rental_days = 120

Submitted return:
fair_rental_days = 180
```

至少存在几类不同解释。

#### 情况一：Extraction Miss

源文件中明确写着：

```text
Fair rental days: 180
```

但提取器产生：

```text
120
```

此时错误确实发生在 Agent 的提取过程：

```text
Source = 180
    ↓
Extraction = 120
```

如果这种模式反复出现，修改 extraction logic 或 extraction schema 是合理方向。

---

#### 情况二：Mapping Problem

也可能上游已经正确提取：

```text
Extracted field:
fair_rental_days = 180
```

但映射到税务引擎以后却变成：

```text
Tax engine field = 120
```

这时继续调 Prompt 甚至扩大模型推理预算都没有直接解决问题。

故障路径是：

```text
Extraction = correct
        ↓
Mapper = wrong
        ↓
Downstream value = wrong
```

同一个最终现象：

```text
prediction != submitted value
```

对应的是另一个组件。

---

#### 情况三：Product Behavior 尚未支持

还有一种情况是，源材料里有这个概念，但当前产品根本没有实现对应字段或工作流。

例如：

```text
Source
  ↓
Agent detects information
  ↓
Current schema has no field
  ↓
Value cannot enter downstream system
```

如果系统只观察最终提交差异，就很容易把它误解成：

```text
模型抽取能力不足
```

但更准确的问题可能是：

```text
当前产品表示空间
根本没有地方存这个值
```

此时需要修改的是 Schema 或产品功能，而不一定是模型行为。

---

#### 情况四：Prior-year Carryover

OpenAI 还专门提到另一类情况：最终报税表中的值可能是税务引擎从上一年度报税表沿用过来的。

此时可能出现：

```text
Current source documents
没有对应值

Tax AI
没有预测这个值

Tax engine
从 prior-year return carry over

Final return
出现该字段
```

如果系统只做：

```text
Tax AI output
vs
Final submitted return
```

比较，就可能得到：

```text
expected = X
predicted = missing
```

然后错误地创建一个 Extraction Eval。

实际上：

```text
missing
```

并没有证明 Agent 漏读了当前材料。

---

#### 情况五：Practitioner Preference 或 Tax Judgment

报税并不是所有字段都能够退化成：

```text
source text
→ deterministic extraction
```

从业者可能根据业务背景、客户情况或专业判断修改一个值。OpenAI 将 practitioner preference 和 tax judgment 都列为生产差异可能的来源。

这类 Case 尤其不能直接变成：

```text
Agent wrong
Human right
```

因为产品要回答的可能不是：

```text
如何从原文抽取这个值？
```

而是：

```text
这个决策究竟应该自动化到什么程度？
```

如果没有足够证据，合理结果甚至可能是：

```text
keep human decision boundary
```

而不是继续扩大 Agent 的自主权。

---

#### 情况六：Workflow Noise

一个值也可能在申报工作流的其他位置被增加或修改。

最终得到的差异：

```text
Agent = X
Final Return = Y
```

只能证明：

\[
X \neq Y
\]

它不能自动证明：

\[
X = \text{error}
\]

更不能推出：

\[
Y = \text{ground truth for the agent}
\]

因此，在这类生产系统中，更准确的数据状态应该先写成：

```text
Observed Difference
```

而不是：

```text
Labeled Error
```

可以把这个区分记成：

\[
\text{Correction}
\not\Rightarrow
\text{Agent Error}
\]

以及：

\[
\text{Final Value}
\not\Rightarrow
\text{Training Label}
\]

这里的符号表达的都只是逻辑关系，不是 OpenAI 原文中的公式。

产品首先获得的是一个需要解释的事件：

```text
Tax AI proposed X
        ↓
Practitioner / workflow changed X
        ↓
Submitted value became Y
```

之后才需要判断：

```text
为什么发生变化？
```

如果这一步被跳过，Self-Evolving Loop 很容易把噪声也当作学习信号。

例如：

```text
正常的 prior-year carryover
        ↓
被识别成 extraction failure
        ↓
生成 Eval
        ↓
Codex 修改 extraction logic
        ↓
Target Eval 提升
```

这个局部优化甚至可能看起来成功。

但它优化的是一个错误定义的问题。

这类失败比普通的：

```text
test failed
```

更麻烦，因为优化循环内部可能保持完全自洽：

```text
错误归因
    ↓
错误 Eval
    ↓
针对 Eval 的正确优化
    ↓
Eval 提升
    ↓
宣布系统改善
```

从数学上看，Optimizer 确实优化了给定目标：

\[
E(S_{t+1}) > E(S_t)
\]

问题只是：

\[
E
\]

并没有对应真实产品目标。

所以生产反馈进入 Self-Evolving Loop 前，需要经过一个额外转换：

```text
Raw Correction
      ↓
Contextualized Evidence
      ↓
Reviewed Failure
```

Tax AI 为这个转换加入的第一层信息来自真正处理报税表的从业者。

他们本来就在做：

```text
review
correct
approve
submit
```

产品需要做的不是额外要求这些人写一份“模型训练报告”，而是让这些已经存在的操作留下结构化记录。

### 2.2 Input / Output 不够，必须保留完整 Trace

如果 Correction 本身存在歧义，下一个问题就是：

> 如何判断错误到底发生在哪里？

一种常见的日志设计只保存：

```text
Input
Output
```

对于普通 API 调用，这可能已经足够排查很多问题。

但 Agent 系统往往在 Input 和 Output 之间执行一条长得多的路径。

Tax AI 的租赁房产流程里，OpenAI 描述了多个中间步骤：

```text
Source Documents
      ↓
organize
      ↓
split
      ↓
classify
      ↓
extract rental-property fields
      ↓
attach citations / provenance
      ↓
map to tax-engine concepts
      ↓
practitioner correction
      ↓
submission
```

最终输出错误并不能告诉我们是哪一个箭头出了问题。

假设：

```text
Submitted:
fair_rental_days = 180
```

而 Tax AI 最后的映射结果是：

```text
120
```

只保存：

```text
Input package
Final Tax AI output
Final submitted return
```

工程师仍然需要重新猜：

```text
模型是不是没看到正确文件？

文件分类是不是错了？

它有没有提取到 180？

引用指向哪里？

Mapper 收到的到底是什么？

Mapper 输出了什么？

120 是在哪一步第一次出现？

从业者什么时候把它改成 180？
```

如果这些状态当时没有被持久化，事后调查只能重新执行系统。

但重新执行并不一定能复现原来的轨迹。

Agent System 中可能存在：

```text
模型采样差异
工具结果变化
文档版本变化
代码版本变化
Prompt 变化
外部服务变化
```

因此：

```text
Re-run
```

不能天然替代：

```text
Production Trace
```

Trace 保存的是：

> **当时那个生产版本究竟发生了什么。**

这可以和普通应用日志做一个区分。

普通日志可能记录：

```text
2026-04-17 14:03
request received

2026-04-17 14:03
request completed

status=200
```

而 Self-Evolving Agent 更需要的是能够重建决策路径的结构化状态：

```text
Source Artifact A
    ↓
classified as rental statement

Source Artifact B
    ↓
classified as email note

Field candidate
fair_rental_days = 180

Provenance
Artifact B / span ...

Mapper input
fair_rental_days = 180

Mapper output
field_X = 120

Practitioner correction
120 → 180

Submitted return
180
```

此时 Root Cause 已经大幅缩小：

```text
Extraction
看起来正确

Provenance
存在

Mapper input
正确

Mapper output
错误

↓
优先调查 Mapper
```

如果另一个 Case 是：

```text
Source:
fair rental days = 180

Extraction:
field missing

Mapper input:
field missing
```

那么调查方向就变成：

```text
Source selection
Document classification
Extraction schema
Extraction pattern
```

Trace 的价值就在这里。

它把：

```text
final failure
```

展开成：

```text
failure location
```

可以把这种差异写成：

\[
O = \text{Final Output}
\]

而：

\[
T =
(s_0,s_1,s_2,\ldots,s_n)
\]

其中每个 \(s_i\) 表示工作流中的一个可观察状态。

只有最终输出时，我们看到的是：

\[
s_0 \rightarrow ? \rightarrow s_n
\]

有完整 Trace 时，才可能看到：

\[
s_0
\rightarrow
s_1
\rightarrow
s_2
\rightarrow
\cdots
\rightarrow
s_n
\]

然后定位第一个发生异常的状态转移。

这仍然不意味着 Trace 能自动给出 Root Cause。一个错误状态可能由更早的错误输入造成，也可能存在多个组件共同作用。但至少它把调查从：

```text
整个系统某处出问题
```

缩小成：

```text
这几步之间开始出现偏差
```

对于 Self-Evolving Agent，这个区别直接影响后面的优化搜索空间。

假设系统允许 Codex 修改：

```text
Prompt
Schema
Source Selection
Extraction Logic
Mapper
Grader
Product Code
```

没有 Trace 时，Optimizer 面对的是：

```text
最终答案错了

请在整个系统里找原因。
```

有 Trace 后，任务可能变成：

```text
Source 中存在字段。
Extraction 已正确捕获字段。
Mapper input 正确。
Mapper output 与最终期望不一致。

请调查 rental-income mapper。
```

前者需要在很大的 Mutable Surface 中搜索。

后者已经提供了相当强的局部约束。

所以可以把 Trace 对优化问题的作用近似写成：

\[
\text{Large Search Space}
\xrightarrow{\text{Trace}}
\text{Smaller Candidate Region}
\]

这里没有声称 Trace 一定能找到唯一 Root Cause，只表示它提供了更精确的可观测状态。

---

#### Provenance 比普通 Trace 再多一层

Tax AI 的例子里还有一个容易和 Trace 混在一起的概念：

```text
provenance
```

Trace 回答的是：

```text
系统做了什么？
```

Provenance 更接近：

```text
这个结果依据什么？
```

例如：

```text
Extracted:
fair_rental_days = 180
```

如果只有这个字段，Reviewer 仍然需要重新翻所有客户资料确认。

如果同时保存：

```text
fair_rental_days = 180

source:
rental-summary.xlsx

location:
Sheet1 / row ...

citation:
...
```

从业者可以直接回到产生这个字段的证据。

因此可以先把两个概念分开：

```text
Trace
────────────────────
记录 computation path

这个字段经过了哪些阶段？


Provenance
────────────────────
记录 evidence path

这个字段来自哪份源材料？
```

真实系统里两者当然可以互相引用，但用途不同。

例如：

```text
Source Artifact
      │
      │ provenance
      ▼
Extracted Field
      │
      │ trace
      ▼
Mapped Field
      │
      │ trace
      ▼
Tax Engine
```

如果字段值错误，Trace 帮助定位：

```text
哪一层第一次变错
```

而 Provenance 帮助判断：

```text
上游依据本身是否正确
```

这也是为什么 OpenAI 对 Tax AI 的描述没有停在：

```text
保存模型回答
```

而是要求产品捕获从：

```text
源材料
→ 提取字段及其来源
→ 下游提交
→ 专家修正
```

的完整路径。

换句话说，一个能够 Self-Evolve 的生产 Agent，Observability 的要求比普通 Chatbot 高很多。

因为日志不再只服务于：

```text
出了事故以后方便 Debug
```

它还会成为下一版本系统的输入：

```text
Production Trace
        ↓
Failure Analysis
        ↓
Eval
        ↓
System Modification
```

这意味着：

> Trace 的数据结构，本身就在决定未来 Optimizer 能看到什么问题。

如果只记录最终输出，那么系统只能围绕最终输出做粗粒度优化；如果保存字段级中间状态、工具执行结果和来源证据，系统才有机会把一次失败定位到更具体的组件。

这也是 Self-Evolving Agent 中一个容易被忽略的依赖：

```text
Evolution Quality
        ↑
Attribution Quality
        ↑
Observability Quality
```

这里仍然只是工程上的依赖关系，不表示三者之间存在简单的线性函数。

### 2.3 Human Feedback 的作用不是给一个“好评 / 差评”

有了 Trace 以后，还缺另一类信息：

```text
哪些差异值得修？
```

这个判断在 Tax AI 中不能完全交给系统自己完成，因为产品面对的是税务工作流。

会计师看到：

```text
Tax AI value = X
Final value = Y
```

时，不只是在提供一个：

```text
thumbs down
```

他们还知道：

```text
这个值为什么需要改

这个差异会不会阻止提交

它是不是正常工作流的一部分

当前结果在税务语义上是否合理
```

OpenAI 因此把“贴近从业者”列为 Tax AI 三个设计支柱之一。

这里的人类反馈和常见 Chatbot Feedback 有很大区别。

最弱的一种反馈通常只有：

```text
👍
```

或者：

```text
👎
```

这种信号可以回答：

```text
用户是否满意？
```

但很难回答：

```text
到底哪个组件应该修改？
```

稍微丰富一点的是：

```text
Agent answer:
120

Human answer:
180
```

它至少提供了一个差异，却仍然缺少前面讨论的上下文。

Tax AI 希望保存的则更接近：

```text
Tax AI proposed:
120

Practitioner action:
changed 120 → 180

Final submitted return:
180

Related production trace:
...

Source provenance:
...
```

于是一次原本只发生在 UI 上的人工操作，变成一个结构化事件：

```text
Expert Intervention Event
```

这里有一个工程设计值得单独拆开。

理想情况下，不应该要求从业者为了“训练 AI”额外完成大量标注工作。

会计师本来就需要：

```text
检查报税表
修正字段
批准结果
提交申报
```

产品设计做的是：

```text
existing work
        +
structured capture
        ↓
feedback signal
```

而不是：

```text
existing work
        +
额外打开标注平台
        +
重新解释自己的操作
        ↓
feedback signal
```

两种设计都能得到人类反馈，但后者很难在真实生产中持续扩展。

如果 Self-Evolving Loop 依赖专家领域，那么反馈成本可以近似写成：

\[
C_{\text{feedback}}
=
C_{\text{normal work}}
+
C_{\text{extra annotation}}
\]

Tax AI 试图把后一个增量压低：

\[
C_{\text{extra annotation}}
\rightarrow \text{small}
\]

因为专家的正常工作本身已经包含了高价值判断。

从业者每一次：

```text
review
correct
approve
```

都可能留下能够进入后续分析的数据。

---

#### 但“专家做了修改”仍然不意味着修改一定可自动化

Human Feedback 可以帮助识别问题，却没有取消前面的歧义。

例如会计师把：

```text
120 → 180
```

系统依然需要结合：

```text
Source
Provenance
Trace
Tax-engine state
Final submission
```

判断这个修正属于哪一种情况。

因此完整关系更接近：

```text
Human Action
      +
Production Trace
      +
Source Evidence
      ↓
Review
      ↓
Potential Finding
```

而不是：

```text
Human Action
      ↓
Finding
```

这点对后面的 Self-Evolving Loop 很重要。

如果把专家当作一个绝对 Label Oracle：

```text
Expert changed value
      ↓
therefore update Agent
```

系统可能把：

```text
专业判断
偏好
工作流行为
产品边界
```

全部强行转化成模型需要学习的规则。

这反而会把原本清楚的人机职责边界抹掉。

Tax AI 的设计更保守。OpenAI 描述的是：从业者帮助团队辨别哪些操作确实需要修正，或者哪些问题会阻止提交；当证据仍然存在歧义，案例会回到产品团队，而不会被强行推进自动改进流程。

也就是说，人类反馈在这里承担的不是单一的：

```text
Label Provider
```

更接近三种作用。

| 作用 | 它回答的问题 |
|---|---|
| Correction | Agent 当前结果哪里需要修改？ |
| Semantic Context | 为什么需要修改？ |
| Boundary Signal | 这个问题应该继续自动化，还是保留人工处理？ |

这三类信息共同决定：

```text
一个生产差异
```

能不能继续向下转化成：

```text
一个系统应该修复的 Failure
```

---

#### Human-in-the-loop 和 Self-Evolving 并不冲突

看到这里，一个自然问题是：

```text
既然仍然依赖会计师和工程师，
为什么还叫 self-improving？
```

这涉及“Self”到底限定哪个环节。

如果定义是：

```text
系统必须自己
发现问题
定义目标
修改自己
验证自己
批准自己
上线自己
```

那么 Tax AI 显然不满足。

OpenAI 的系统中，人类仍然参与：

```text
Practitioner
→ review / correction / approval

Product & Engineering
→ ambiguous-case judgment
→ architecture
→ shipping
```

但与完全手工的产品迭代相比，发生变化的是中间工程循环。

传统路径可能是：

```text
用户发现问题
    ↓
发给 Support
    ↓
产品经理整理
    ↓
工程师复现
    ↓
工程师定位
    ↓
工程师修改
    ↓
工程师写测试
    ↓
工程师回归
    ↓
上线
```

而 Tax AI 希望把其中一部分压成：

```text
Practitioner correction
        ↓
Structured production evidence
        ↓
Reviewed finding
        ↓
Eval
        ↓
Codex investigates
        ↓
Codex modifies system
        ↓
Targeted Eval
        ↓
Regression
        ↓
Candidate PR
```

人依然定义产品边界并承担最终责任，但每次生产失败不再都要求工程师从零开始手工调查。

因此这里的：

```text
self-improving
```

更适合理解成：

```text
系统已经包含一个
利用自身生产行为
推动后续版本修改的机制
```

而不是：

```text
系统完全脱离外部监督
```

这个边界后面第 6 节还会专门展开。

现在只需要保留一个结论：Human Feedback 并不是 Self-Evolution Loop 外面的临时补丁，它本身就是循环中的一个输入接口。

可以把目前得到的链路画成：

```text
                  Real Production
                        │
                        ▼
               ┌─────────────────┐
               │  Source Inputs  │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │   Agent Trace   │
               │                 │
               │ extraction      │
               │ provenance      │
               │ mapping         │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ Agent Proposal  │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ Practitioner    │
               │ Review          │
               └────────┬────────┘
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
        no correction         correction
                                  │
                                  ▼
                          Final Submission
                                  │
                                  ▼
                    ┌──────────────────────┐
                    │ Structured Evidence  │
                    │                      │
                    │ proposal             │
                    │ correction           │
                    │ final value          │
                    │ trace                │
                    │ provenance           │
                    └──────────┬───────────┘
                               │
                               ▼
                             Review
```

注意这张图现在停在：

```text
Review
```

还没有：

```text
Eval
```

这是有意为之。

第 2 节只解决了一个问题：

> **怎样把真实工作里的模糊反馈保存成足以调查的 Evidence？**

到这里，我们拥有的仍然可能是数千条甚至更多字段级差异：

```text
Case A
field X changed

Case B
field Y changed

Case C
field X changed

Case D
expected workflow noise

Case E
field Z changed

...
```

Codex 不应该收到这些原始数据以后自己随便找一个模式开始改代码。

生产证据还需要再经过一次压缩：

```text
individual corrections
        ↓
field-level review rows
        ↓
related failures
        ↓
recurring actionable pattern
        ↓
Eval target
```

这一步决定了 Self-Evolving Loop 下一轮究竟要优化什么。

也正是在这里，生产环境里杂乱的：

```text
“这个字段怎么又被改了？”
```

才会第一次变成一个能够交给 Optimizer 的工程目标。

## 3. 从一次 Correction 到一个 Eval

上一节解决的是：

```text
生产环境里发生了一次修正，
怎样把它保存成足以调查的 Evidence？
```

但 Evidence 还不能直接成为 Optimizer 的任务。

假设 Tax AI 一个报税季处理了数千份报税表。每份报税表又包含大量字段，从业者不断进行：

```text
accept
correct
override
approve
submit
```

生产系统最终可能积累出大量差异：

```text
Case 0001
fair_rental_days:
missing → 180

Case 0002
other_expenses:
4200 → 4700

Case 0003
fair_rental_days:
missing → 365

Case 0004
property_1_income:
被写入 property_2

Case 0005
某字段来自 prior-year carryover

Case 0006
fair_rental_days:
missing → 90
```

如果这些记录全部直接扔给 Codex：

```text
这里有 10,000 条用户修改，
请找问题并改进系统。
```

虽然技术上可以让 Agent 自己搜索，但这会把几类职责混在一起：

```text
识别哪些差异是真问题
+
判断哪些问题属于同一种 Failure
+
决定什么问题值得优先修
+
定义怎样才算修好
+
修改系统
+
验证修改
```

其中任何一个环节判断错误，后面的优化都可能沿着错误目标继续推进。

OpenAI 在 Tax AI 中因此加入了一层很关键的中间表示。产品 Trace 不会直接生成 Codex 修改任务，而是先经过三个步骤：

```text
Capture the difference
        ↓
Group related failures
        ↓
Turn repeated patterns into eval targets
```

这三步看起来只是数据整理，实际上完成了一次很重要的语义压缩：

```text
大量生产事件
        ↓
少量可解释 Failure Pattern
        ↓
有明确成功条件的 Eval
```

只有走到最后一步，Optimizer 才真正知道：

> **我要让什么东西变好？**

### 3.1 先把生产差异整理成 Field-level Review Row

第一步仍然不急着判断 Root Cause，而是把每个需要审查的字段差异保存成一个比较稳定的结构。

OpenAI 对这一层的描述是：比较 Tax AI 的输出与已提交报税表，产生 **field-level review rows**，其中记录：

```text
expected value
predicted value
actionable?
```

这里的：

```text
actionable?
```

很重要。

如果只保存：

```text
expected = 180
predicted = null
```

我们仍然不知道这个差异是否应该由 Tax AI 修复。

上一节已经看到，同一个：

```text
predicted != expected
```

可能来自：

```text
extraction miss
mapping problem
unsupported product behavior
prior-year carryover
practitioner preference
tax judgment
expected workflow noise
```

所以一条 Review Row 更准确的语义不是：

```text
这是一个错误样本。
```

而是：

```text
这里存在一个值得审查的差异，
当前还需要判断它是否构成产品可处理的问题。
```

如果为了帮助理解，把 OpenAI 的描述抽象成一个概念结构，可以写成：

```python
ReviewRow(
    predicted_value=...,
    expected_value=...,
    actionable=...,
)
```

真实系统显然还需要能够关联：

```text
return
field
trace
source package
provenance
practitioner action
```

例如：

```python
ReviewRow(
    return_id="R-1042",
    field="fair_rental_days",

    predicted_value=None,
    expected_value=180,

    trace_ref="TRACE-1042",
    source_ref="SRC-1042",

    practitioner_action="filled_missing_value",

    actionable=True,
)
```

这段代码只是根据文章描述构造的概念示意，不是 Tax AI 暴露出来的真实数据结构。

它的价值在于把原来分散在多个系统里的信息：

```text
Tax AI Output
Practitioner UI Action
Filed Return
Production Trace
```

统一关联到一个能够进一步分析的单位。

这样生产事件不再只是：

```text
某个用户改了一个数字
```

而成为：

```text
在系统版本 V_t 下，
字段 F 的预测值为 X，
最终值为 Y，
相关 Trace 为 T，
这个差异经过审查后被认为
actionable / non-actionable。
```

---

#### 为什么要做到字段级，而不是整份报税表级

假设一份报税表有 100 个相关字段，其中只有：

```text
fair_rental_days
```

出了问题。

如果 Review 的最小单位是：

```text
Return 1042 = FAILED
```

系统得到的信息非常粗：

```text
这一份报税表做错了。
```

但如果记录到字段级：

```text
Return 1042

rental_income       correct
property_address    correct
other_expenses      correct
fair_rental_days    missing
...
```

就可以知道真正需要分析的是：

```text
fair_rental_days
```

而不是整条 Rental Property Pipeline。

这会直接影响后面的优化粒度。

粗粒度错误：

```text
Rental Property 失败
```

可能让 Optimizer 搜索：

```text
Prompt
Document Splitter
Classifier
Extraction Schema
Extraction Prompt
Mapper
Tax Engine Integration
Grader
...
```

字段级错误则可能先把问题约束成：

```text
为什么 fair_rental_days
在这一类 Source Package 中
反复没有进入最终预测？
```

这和上一节讨论 Trace 的作用类似：

```text
Observability
        ↓
缩小 Attribution 范围
```

只是现在的粒度进一步从：

```text
整个任务
```

下降到：

```text
某个字段上的某种差异
```

---

#### Review Row 还没有承担 Root Cause Analysis

这里必须保持边界。

一条：

```text
field = fair_rental_days
predicted = missing
expected = 180
actionable = true
```

并不能推出：

```text
Root Cause = Extraction Prompt
```

它只证明：

> 这个生产差异经过审查以后，值得作为产品问题继续调查。

Root Cause 仍然可能在：

```text
Source Selection
Document Classification
Extraction Schema
Extraction Logic
Mapper
Grader
```

真正定位这些组件，是 Codex 后面进入产品脚手架以后才要做的事情。

所以可以把目前几个概念区分成：

```text
Correction
────────────────────
人修改了结果


Review Row
────────────────────
一个结构化、经过语境化的字段差异


Finding
────────────────────
一组 Review Rows 共同暴露的
重复产品问题


Root Cause
────────────────────
导致 Finding 的具体系统原因
```

这四个东西不能混为一谈。

尤其不要从：

```text
Correction
```

直接跳到：

```text
Root Cause
```

因为这等于让 Optimizer 同时猜测问题是否存在，以及问题为什么存在。

### 3.2 单点错误价值有限，重复模式才值得进入优化循环

有了 Review Rows 以后，系统可能得到：

```text
R-0001:
fair_rental_days missing

R-0017:
fair_rental_days missing

R-0024:
prior-year carryover
non-actionable

R-0041:
other_expenses wrong

R-0068:
fair_rental_days missing

R-0072:
property identities confused

R-0089:
other_expenses wrong

R-0103:
fair_rental_days missing
```

下一步不是逐条创建八个工程 Issue，而是：

```text
Group related failures
```

OpenAI 给出的例子包括：

```text
经常漏掉 fair-rental-day 字段

错误处理 "other expenses"

在同一个 source package 中
混淆多个 rental properties
```

这些才开始像产品级 Failure Pattern。

例如：

```text
R-0001 ─┐
R-0017 ─┤
R-0068 ─┼─→ Finding A
R-0103 ─┘

Finding A:
Tax AI repeatedly misses
fair_rental_days.
```

另一组可能是：

```text
R-0041 ─┐
R-0089 ─┴─→ Finding B

Finding B:
Tax AI mishandles
other_expenses.
```

而：

```text
R-0024
prior-year carryover
```

可能在 Review 阶段被认定为：

```text
expected workflow noise
```

于是不会进入 Finding。

OpenAI 对这一阶段的描述正是：

```text
recurring product failures
vs
expected workflow noise
```

这一步比简单的“统计错误次数”更重要，因为生产数据里频繁出现的差异，不一定都是需要优化的错误。

---

#### 为什么不能看到一次失败就自动修改

假设一次生产任务里发生：

```text
fair_rental_days missing
```

一种非常积极的 Self-Evolving 设计可能立刻：

```text
Failure
    ↓
Agent investigates
    ↓
Agent edits Prompt
    ↓
Deploy
```

这条路径很短，但它很容易过拟合单个 Case。

这个失败可能只是：

```text
一份异常格式文件

OCR 噪声

单个用户特殊模板

Source 上传不完整

偶然的模型采样
```

如果系统根据每一个单点失败都修改持久策略，它会出现一种类似：

```text
production-driven thrashing
```

的现象：

```text
Case A 出错
→ 改规则解决 A

Case B 出错
→ 改规则解决 B

修改 B 又破坏 A
→ 再改

Case C 出现
→ 再补一条例外
```

最终：

```text
Prompt 越来越长
Skill 越来越多
规则之间开始冲突
Regression 越来越难解释
```

所以生产失败的频率和一致性本身就是一种证据。

如果多个独立 Case 都出现：

```text
same semantic failure
```

那么：

```text
偶发噪声
```

的解释会逐渐变弱，而：

```text
systematic product failure
```

会变得更可信。

可以把这个过程简单写成：

\[
r_1,r_2,\ldots,r_n
\xrightarrow{\text{group}}
F
\]

其中：

```text
r_i
= reviewed field-level difference

F
= recurring finding
```

这里的 `group` 不能只理解成字符串聚类。两个表面字段名不同的错误可能共享同一个产品根因；相反，两个字段名相同的差异也可能分别来自 Extraction 和 Workflow Noise。

因此更完整的判断会使用：

```text
field
failure semantics
trace context
source pattern
practitioner action
```

甚至其他业务元数据。

OpenAI 的文章没有公开具体的聚类算法，所以这里不能凭空写：

```text
Tax AI 使用 Embedding + K-Means
```

或者：

```text
使用 LLM 自动聚类
```

文章能够确定的是更高层的工程过程：

```text
similar review rows
        ↓
grouped
        ↓
recurring failures separated
from expected workflow noise
```

具体实现仍然未知。

---

#### Failure Clustering 同时在做“降噪”和“压缩”

假设一周积累了：

\[
N=10,000
\]

条 Review Rows。

它们不应该对应：

\[
10,000
\]

个 Codex Tasks。

经过 Review 和 Grouping，真正值得处理的可能只是少量：

```text
Finding A
Finding B
Finding C
...
```

于是系统实际上完成了：

\[
\{\text{Production Events}\}
\rightarrow
\{\text{Actionable Findings}\}
\]

这个映射有两个效果。

第一个是降噪：

```text
expected workflow noise
non-actionable differences
ambiguous cases

被挡在 Optimizer 外面
```

第二个是压缩：

```text
几十次相同类型的失败
        ↓
一个稳定的产品问题
```

这会让下游 Codex Task 更有边界。

与其告诉 Codex：

```text
这里有 42 个报税表出了各种问题。
```

不如告诉它：

```text
在 42 个经过审查的样本中，
系统反复漏掉 fair_rental_days。

这里是代表性 Source Packages、
Trace 和对应的期望结果。
```

后者已经接近一个可以执行的工程任务。

---

#### 但“出现很多次”也不能自动证明它值得修

这里还有一个容易被忽略的限制。

假设：

```text
某个字段被人修改 500 次
```

数量很大。

它仍然可能代表：

```text
产品本来就设计成人工填写
```

或者：

```text
这个字段涉及 Tax Judgment，
系统没有意图自动决策
```

因此：

\[
\text{frequency}
\not\Rightarrow
\text{actionability}
\]

重复性提供的是：

```text
这个模式稳定存在
```

但是否应该进入自动化边界，仍然需要：

```text
product semantics
practitioner judgment
safety boundary
```

参与决定。

所以真正可以进入下一步的是：

```text
Repeated
+
Reviewed
+
Actionable
```

的 Finding。

到这里才可以从：

```text
“我们经常看到这个问题”
```

继续转向：

```text
“怎样判断下一版本是否修好了这个问题？”
```

答案就是 Eval。

### 3.3 Finding 必须被压成一个“可以输赢”的 Eval

假设前面的 Review 和 Grouping 最终得到：

```text
Finding:
Tax AI repeatedly misses
fair_rental_days.
```

这个描述已经比：

```text
Rental Property 不太稳定
```

具体很多。

但它仍然不是一个完整的工程成功条件。

如果直接把 Finding 发给 Codex：

```text
Tax AI 经常漏掉 fair_rental_days，
请修一下。
```

Agent 可以完成很多看起来合理的动作：

```text
修改 Prompt

扩展 Schema

添加 few-shot example

增加一个 Skill

调整 Mapper
```

最后说：

```text
问题应该已经修复。
```

但“应该”仍然不能决定是否进入生产。

要把 Finding 变成真正的优化目标，还需要回答：

```text
用哪些输入来测？

期望系统输出什么？

怎样判断通过？

修改以后还要检查什么？
```

OpenAI 对 Tax AI 的做法是把经过审查、测量的重复 Finding 转成 **targeted eval**。

对于：

```text
fair_rental_days
```

这个问题，一个概念上的 Eval 可能具有：

```text
Representative Source Packages
        +
Expected Outputs
        +
Evaluation Logic
```

例如：

```text
Case A
Source Package
→ expected fair_rental_days = 180

Case B
Source Package
→ expected fair_rental_days = 365

Case C
Source Package
→ expected fair_rental_days = 90
```

于是 Finding：

```text
Tax AI 经常漏掉 fair_rental_days
```

第一次拥有了一个可以实际运行的问题：

```text
给定这些代表性 Source Packages，
当前系统能否稳定产生
正确的 fair_rental_days？
```

这就是 OpenAI 所说的给 Codex 一个：

```text
hill to climb
```

重点不在这个比喻本身，而在于：

> 优化器必须看到一个有方向的目标函数，而不是一句模糊的产品抱怨。

---

#### Finding 和 Eval 的差别

可以把两者并排看：

| Finding | Eval |
|---|---|
| 描述反复出现的生产失败 | 把失败变成可执行测试 |
| “经常漏字段” | “在这些代表样本上应输出这些字段” |
| 面向问题理解 | 面向版本比较 |
| 可以是自然语言 | 必须产生可判定结果 |
| 告诉我们哪里值得改 | 告诉我们改完是否有效 |

因此：

```text
Finding:
fair_rental_days 经常缺失
```

还需要被转换成：

```text
Eval:
Input_i
→ Expected_i
→ Score_i
```

如果写成一个最简单的形式：

\[
E(S,D)
=
\frac{1}{|D|}
\sum_{i=1}^{|D|}
g(S(x_i),y_i)
\]

其中：

```text
S
= 当前 Agent System

D
= targeted eval set

x_i
= representative source package

y_i
= expected output

g
= grader
```

这个公式同样是本文为了说明概念给出的抽象，不是 OpenAI Tax AI 的公开实现。

有了：

\[
E(S_t,D)
\]

以后，系统才可以比较候选修改：

\[
S_t
\rightarrow
S'_t
\]

是不是让：

\[
E(S'_t,D)
>
E(S_t,D)
\]

否则所谓“修复”仍然主要依赖 Agent 的文字解释。

---

#### Eval 的意义不是把整个真实世界压成一个数字

这里也不能走到另一个极端：

```text
只要 Eval 上升
=
产品一定变好了
```

上一节已经讨论过：

```text
错误 Eval
    ↓
正确优化
    ↓
错误方向上的指标提升
```

完全可能发生。

因此 Targeted Eval 的数据来源非常关键。

Tax AI 的 Eval 不是团队在上线以前凭空想出来的一组 Toy Cases，而是沿着：

```text
Real Production
    ↓
Practitioner Correction
    ↓
Product Trace
    ↓
Review Rows
    ↓
Repeated Finding
    ↓
Representative Cases
```

构造出来的。

这使它与真实生产 Failure 有一条可以追踪的 lineage。

可以画成：

```text
Production Case
      │
      │ evidence
      ▼
Review Row
      │
      │ grouping
      ▼
Finding
      │
      │ representative examples
      ▼
Eval Case
```

这里的优势不是 Eval 天然正确，而是：

> 当某个 Eval 为什么存在被追问时，可以一路回到它对应的真实生产失败。

这和一个来源不明的：

```text
eval_037.json
```

差别很大。

---

#### Production Failure 被保存成 Regression Asset

这里还出现了一个长期系统很重要的变化。

第一次遇到：

```text
fair_rental_days missing
```

时，它只是一个生产 Bug。

经过：

```text
review
group
eval construction
```

以后，它变成了一个持久测试资产：

```text
过去系统曾经在这里失败
```

即使后来问题修好了，这个 Eval 也不应该立即消失。

因为未来：

```text
Prompt 改了
Schema 改了
Model 升级了
Mapper 重构了
Skill 更新了
```

都可能重新引入相同 Failure。

所以可以把这条生命周期写成：

```text
Production Failure
        ↓
Reviewed Finding
        ↓
Eval Case
        ↓
Fix
        ↓
Regression Asset
```

一次失败因此不只是被“修掉”。

它还增加了系统未来判断：

```text
什么叫正确？
```

的能力。

这实际上是 Self-Evolving Loop 最容易被低估的一部分。

系统的变化不仅发生在：

```text
Agent capability
```

也发生在：

```text
Evaluation capability
```

即：

\[
S_t
=
(\text{Agent}, E_t,\ldots)
\]

经过一次生产失败以后，可能同时出现：

\[
\text{Agent}_{t+1}
\neq
\text{Agent}_t
\]

以及：

\[
E_{t+1}
\supset
E_t
\]

后一个关系表示新的失败案例被加入了后续评测覆盖面，并不意味着 Eval Set 只允许单调追加、永远不能维护或删除。

这也解释了为什么 Self-Evolving Agent 不能只研究：

```text
怎么自动改 Prompt
```

因为如果：

```text
Evaluator
```

本身长期不增长，Optimizer 只能反复优化一套静态的成功定义。

生产系统则不断遇到：

```text
以前没有见过的输入
以前没覆盖的 Workflow
以前不知道的 Failure
```

成熟的闭环必须能够把其中有价值的一部分反过来扩充 Verification Surface。

---

#### 一个 Eval 最重要的属性是 Bounded

从工程角度看，Targeted Eval 还有另一个作用：

```text
限定任务边界
```

没有 Eval 时：

```text
任务：
改善 Rental Property Agent
```

这个范围几乎无限。

Codex 可以考虑：

```text
重新写整个 Pipeline
换模型
重构 Schema
修改所有 Prompt
改变 Mapper
修改 UI
重新设计 Grader
```

有了针对 `fair_rental_days` 的 Eval：

```text
任务：
让代表性 rental-property source packages
正确产生 fair_rental_days，
同时通过相关回归评测。
```

Search Space 仍然不小，但成功条件已经明确很多。

于是：

```text
Open-ended improvement
```

被压缩成：

```text
Bounded engineering task
```

这与前面 Harness Engineering 里反复出现的原则是一致的：

```text
Agent autonomy
```

并不意味着：

```text
不给 Agent 边界
```

恰恰相反。

如果希望 Codex 可以更加自主地执行调查与修改，系统反而需要提前把：

```text
Evidence
Scope
Tools
Success Condition
Validation
```

定义得更清楚。

---

#### 到这里，Codex 才真正获得一个可优化对象

因此，从生产现场到 Eval 的完整转换可以写成：

```text
Practitioner Correction
          ↓
Production Trace
          ↓
Field-level Review Row
          ↓
Actionability Review
          ↓
Group Related Failures
          ↓
Recurring Finding
          ↓
Representative Cases
          ↓
Targeted Eval
```

也可以进一步压成三层：

```text
Observation
────────────────────────────
这里发生了什么差异？


Diagnosis Target
────────────────────────────
哪些差异共同构成一个
稳定、值得修的问题？


Optimization Target
────────────────────────────
下一版本怎样才算
明确地修好了它？
```

分别对应：

```text
Review Row
Finding
Eval
```

这三层不能省掉其中任何一个。

如果没有 Review Row：

```text
Production feedback
```

仍然太松散。

如果没有 Finding：

```text
Optimizer
```

会被大量独立 Case 淹没。

如果没有 Eval：

```text
“修好”
```

就没有可以独立运行的定义。

到这一刻，上一节的：

```text
Human changed X → Y
```

才终于被转换成：

```text
给定 D，
候选系统 S'
必须让 targeted eval E
达到明确的改进条件。
```

但这里还有最后一个没有回答的问题。

我们已经知道：

```text
哪里表现不好
```

却仍然不知道：

```text
为什么表现不好。
```

例如 Eval 可以非常确定地告诉我们：

```text
fair_rental_days
在这些 Source Packages 上
持续失败
```

但它不能直接判断：

```text
是 Schema 不支持？

Extraction Pattern 没覆盖？

Source Selection 选错文件？

Mapper 丢字段？

还是 Grader 本身错了？
```

换句话说：

```text
Eval Failure
≠
Root Cause
```

这才是 Codex 真正进入 Self-Evolving Loop 的位置。

下一步 Optimizer 不再面对模糊的用户反馈，而是拿到：

```text
Finding
+
Targeted Eval
+
Production Trace
+
Repository
+
Skills
```

然后在 Agent System 的 Mutable Surface 中调查：

> **到底该改哪一层，才能让 Eval 上升，同时不破坏其他能力？**

## 4. Codex 如何从 Eval 找到可修改的系统接口

到第 3 节结束，我们已经完成了一次很长的压缩：

```text
Production
    ↓
Correction
    ↓
Trace
    ↓
Review Row
    ↓
Finding
    ↓
Targeted Eval
```

对于 `fair_rental_days`，Optimizer 现在拿到的已经不再是：

```text
“最近有几个会计师说租赁房产不太好用。”
```

而可能是：

```text
Finding:
Tax AI 在一类 Rental Property Source Package 中
反复遗漏 fair_rental_days。

Targeted Eval:
这里是经过审查的代表性 Source Packages
以及相应 Expected Outputs。
```

这解决了：

> **哪里需要变好？**

但还没有解决：

> **系统为什么会在这里失败？**

这两个问题不能合并。

一个 Eval 可以非常稳定地复现：

```text
fair_rental_days missing
```

却无法仅凭这个结果判断应该：

```text
改 Prompt

扩展 Schema

增加 Source Selection 规则

修改 Mapper

还是调整 Grader
```

换句话说：

```text
Evaluation
告诉我们“哪里表现不好”

Diagnosis
要回答“为什么表现不好”
```

Self-Evolving Agent 如果缺少后一个阶段，很容易退化成另一种自动 Prompt Tuning：

```text
Eval 下降
    ↓
修改 Prompt
    ↓
再跑 Eval
```

但 Tax AI 的产品表面远不止 Prompt。OpenAI 描述的 Codex Loop 会直接检查生产 Trace、Eval、代码仓库和 Skills，再根据证据决定修改系统中的哪一层。

这里开始出现 Self-Evolving Agent 的另一个核心问题：

> **系统到底允许 Optimizer 修改什么？**

### 4.1 Eval Failure 不等于 Root Cause

先看最简单的情况。

Targeted Eval 报告：

```text
Case A:
expected fair_rental_days = 180
predicted = missing

Case B:
expected fair_rental_days = 365
predicted = missing

Case C:
expected fair_rental_days = 90
predicted = missing
```

我们现在可以比较有信心地说：

```text
这个 Failure Pattern 是可复现的。
```

但还不能说：

```text
Extraction Prompt 有问题。
```

因为最终的：

```text
missing
```

只是一条长 Pipeline 的末端表现。

一种可能路径是：

```text
Source Package
    ↓
正确文件被选中
    ↓
Extraction Schema 支持该字段
    ↓
Extractor 没有识别
    ↓
missing
```

这种情况下，问题可能确实位于：

```text
extraction pattern
```

但另一种可能是：

```text
Source Package
    ↓
相关文件没有被 Source Selection 选中
    ↓
Extractor 根本没看到证据
    ↓
missing
```

此时继续改 Extraction Prompt，很可能没有作用。

还可能是：

```text
Source Package
    ↓
Extractor:
fair_rental_days = 180
    ↓
Mapper 没有对应映射
    ↓
Downstream:
missing
```

那么模型实际上已经完成了正确提取，只是在确定性代码层丢掉了字段。

甚至可能是：

```text
System Behavior = correct
        ↓
Grader interpretation = wrong
        ↓
Eval marks failure
```

此时真正需要修改的不是 Agent，而是 Eval。

OpenAI 在租赁房产案例中明确列出了几种需要调查的可能性：

```text
field unsupported

extraction pattern miss

source-selection problem

mapper gap

grader issue
```

这些情况最后都可能表现为：

```text
Targeted Eval failed
```

所以：

\[
\text{Eval Failure}
\not\Rightarrow
\text{Unique Root Cause}
\]

Eval 定义的是一个 **observable failure condition**。

Root Cause 则需要结合：

```text
Source Package
Trace
Intermediate State
Code Path
Schema
Mapper
Grader
```

进一步调查。

---

#### 一个实用的问题：第一个异常状态出现在哪里？

上一节介绍 Trace 时已经留下了一个有用的调试方法：

```text
Source
    ↓
s_1
    ↓
s_2
    ↓
s_3
    ↓
Final Output
```

如果知道：

```text
Expected Output
```

就可以向前寻找：

> 第一个和期望路径发生明显偏差的状态在哪里？

例如：

```text
Source:
fair rental days = 180

Extraction:
fair_rental_days = 180

Mapper input:
fair_rental_days = 180

Mapper output:
missing

Final output:
missing
```

这里没有必要让 Codex 在整个 Agent System 中随机探索。

证据已经把 Candidate Region 压到：

```text
Mapper
```

附近。

而另一个 Trace：

```text
Source:
fair rental days = 180

Selected Sources:
没有包含对应文件

Extraction:
missing

Mapper:
missing
```

则更应该调查：

```text
Source Selection
```

而不是 Mapper。

可以把这一过程写成：

\[
\text{Failure}
+
\text{Trace}
\rightarrow
\text{Candidate Cause Set}
\]

而不是：

\[
\text{Failure}
\rightarrow
\text{Root Cause}
\]

Trace 的作用是不断缩小：

\[
|\mathcal{C}|
\]

其中：

```text
C
= 当前仍然与证据一致的候选原因集合
```

理想情况下，调查最终能够找到一个足以解释观察结果、并能够通过修改验证的原因。

---

#### Root Cause 在 Agent 系统里经常跨层

传统程序 Bug 很多时候可以落到：

```text
某一行代码写错了
```

Agent System 的 Failure 不一定这么局部。

例如：

```text
Source Selection
选择了过多文档

        ↓

Context 中出现两个 Rental Property

        ↓

Extraction Prompt
没有要求稳定绑定 Property Identity

        ↓

Mapper
又只按字段名匹配

        ↓

Property A 的值
写到了 Property B
```

这里如果只修：

```text
Mapper
```

可能解决部分 Case。

如果只修：

```text
Prompt
```

也可能改善部分 Case。

真正稳定的解决方式甚至可能需要：

```text
Schema
+
Extraction
+
Mapper
```

一起变化。

因此这里的：

```text
Root Cause
```

不能机械理解成：

```text
唯一一行错误代码
```

更准确的是：

> **能够解释当前 Failure Pattern，并且修改之后能够在 Targeted Eval 中消除该模式的最小充分系统变化。**

这里的“最小充分”是本文采用的工程目标，不是 OpenAI 给出的正式定义。

它强调两个约束：

```text
Sufficient
──────────
必须真的解决 Failure


Minimal
──────────
不要为了一个局部 Finding
无边界地重写整个系统
```

这个约束很重要。

如果 Targeted Eval 只涉及：

```text
fair_rental_days
```

一种极端做法当然可以是：

```text
重新设计整个 Rental Property Pipeline
```

但修改面越大：

```text
需要验证的行为越多

潜在 Regression 越多

失败以后越难 Attribution

Code Review 越困难
```

所以 Self-Evolving Loop 并不奖励：

```text
修改越多越智能
```

更合理的目标是：

```text
在足以解决 Finding 的范围内
保持修改面尽量可控
```

---

#### Diagnosis 本身也需要证据，而不是故事

Coding Agent 很容易生成一个听起来合理的解释：

```text
“问题可能是 Extraction Prompt
没有强调 fair rental_days，
所以模型忽略了这个字段。”
```

这个解释可能是对的。

但：

```text
plausible explanation
```

和：

```text
supported diagnosis
```

不是一回事。

如果 Trace 已经显示：

```text
Extraction:
fair_rental_days = 180
```

那么上面的解释就与已有证据冲突。

因此 Codex 的调查过程最好遵循：

```text
Hypothesis
    ↓
Inspect Evidence
    ↓
Does evidence support it?
    ↓
Inspect relevant code/path
    ↓
Candidate modification
```

而不是：

```text
Failure
    ↓
生成一个合理故事
    ↓
按故事修改
```

这和普通 Debugging 没有本质区别。

区别只是 Agent System 里的“程序状态”更丰富：

```text
代码
Prompt
Skill
Tool Result
Trace
Model Output
Schema
Eval
```

都可能成为证据。

所以这一阶段本质上仍然是：

```text
trace-driven debugging
```

只是调试对象从：

```text
deterministic program
```

扩展成：

```text
model behavior
+
product code
+
runtime policy
+
evaluation logic
```

### 4.2 Mutable Surface：系统究竟允许改什么

Root Cause Analysis 得到一个候选原因以后，下一个问题是：

> Codex 有权限修改那里吗？

一个 Self-Evolving Agent 不可能默认：

```text
整个世界都是 writable
```

它必须存在一个明确的：

```text
Mutable Surface
```

也就是：

> **Optimizer 被允许产生持久修改的系统状态集合。**

如果继续使用第 1 节的表示：

\[
S =
(M,P,K,T,C,E,R,\ldots)
\]

那么一个具体系统可以定义：

\[
\mathcal{M}
\subseteq
\{M,P,K,T,C,E,R,\ldots\}
\]

其中：

\[
\mathcal{M}
\]

就是当前 Self-Evolving Loop 的 Mutable Surface。

Tax AI 的例子中，OpenAI 展示的修改主要发生在产品和 Harness 层，而不是基础模型权重层。

Codex 可能调查并修改：

```text
extraction pattern

source-selection behavior

tax-engine mapper

grader

相关 product code
```

后面的任务环境示例还会出现：

```text
agent.ts
schema.ts
provenance.ts
mapper.ts

evals/
skills/
```

但具体哪些文件在一次任务里允许修改，取决于该任务被赋予的 Scope。

所以一个更有用的 Self-Evolving 设计不是：

```text
Agent 可以修改自己。
```

而是明确写：

```text
Agent 可以修改：

A
B
C

Agent 只能读取：

D
E
F

Agent 无权触碰：

G
H
```

---

#### Mutable Surface 决定 Self-Evolution 的“层级”

假设系统只允许修改：

```text
Prompt
```

那么它是一个非常窄的 Self-Evolving Loop：

\[
\mathcal{M}
=
\{P\}
\]

如果允许：

```text
Prompt
Skill
Memory
```

则：

\[
\mathcal{M}
=
\{P,K\}
\]

如果继续开放：

```text
Schema
Workflow
Tool
Mapper
Product Code
Grader
```

Mutable Surface 会进一步扩大：

\[
\mathcal{M}
=
\{P,K,T,C,E,\ldots\}
\]

这也是为什么讨论：

```text
“Agent 能不能 Self-Evolve？”
```

时，最好再追问一句：

> **它能修改哪一层？**

否则 Prompt Optimizer、Skill Evolution、Harness Evolution、Continual Learning 和 RSI 很容易全部被同一个词覆盖。

Tax AI 最有价值的地方之一就在于，它展示的是一种相当务实的中间状态：

```text
Base Model
不必在线训练

        ↓

产品系统中
一部分可编辑 Interface
可以持续变化
```

所以：

```text
Model Weights
```

并不是 Self-Evolution 唯一有意义的参数空间。

---

#### 可以把系统改进写成一次 Search

为了更明确一点，可以把所有允许修改的状态记成：

\[
\theta
\]

例如：

\[
\theta =
(
\theta_{\text{extract}},
\theta_{\text{source}},
\theta_{\text{schema}},
\theta_{\text{mapper}},
\theta_{\text{grader}}
)
\]

当前系统是：

\[
\theta_t
\]

Codex 的任务可以抽象成寻找：

\[
\theta'
\]

使：

\[
E_{\text{target}}(\theta')
>
E_{\text{target}}(\theta_t)
\]

同时满足其他约束。

这里和传统数值优化最大的不同是：

```text
θ
```

不一定是一组连续参数。

它可能是一整个：

```text
TypeScript function

YAML schema

Prompt fragment

Skill

Mapper rule

Grader configuration
```

所以搜索动作可能是：

```text
Read
Reason
Edit
Run
Inspect
Edit again
```

而不是：

```text
θ ← θ - η∇L
```

从这个角度看，Coding Agent 就变成了一个能够在离散、结构化工程空间里进行 Search 的 Optimizer。

它不是计算梯度：

```text
∇L
```

而是使用：

```text
Finding
Trace
Code
Docs
Eval Result
Tool Result
```

不断提出候选修改。

---

#### Mutable Surface 越大，并不天然越强

开放更多可修改组件会提高表达能力。

例如，如果只允许：

```text
Prompt
```

而真正问题在：

```text
mapper.ts
```

Optimizer 无论尝试多少 Prompt，都只能在错误接口上搜索。

因此：

```text
Mutable Surface too narrow
```

会产生：

```text
无法表示正确修复
```

的问题。

但另一个方向同样危险。

假设直接允许 Codex 同时修改：

```text
Agent
Schema
Mapper
Eval Dataset
Grader
Regression Suite
Task Definition
```

那么系统理论上拥有非常大的自由度。

可自由度越大，另一种 Failure 就越容易出现：

```text
不是解决问题

而是修改“什么叫成功”
```

最简单的例子是：

```text
Target Eval:
fair_rental_days 必须正确
```

Codex 如果能够任意修改 Grader，最容易让：

\[
E_{\text{target}}
\]

变高的方法之一可能不是改善 Tax AI，而是让 Grader 不再把：

```text
missing fair_rental_days
```

判为失败。

于是：

```text
Before:
behavior wrong
grader catches it
score = low

After:
behavior still wrong
grader ignores it
score = high
```

形式上：

\[
E(S_{t+1}) > E(S_t)
\]

成立。

但产品行为没有改善。

这就是为什么：

```text
Eval
```

作为 Mutable Surface 时需要格外谨慎。

OpenAI 的例子里确实允许 Codex 在：

```text
expected workflow noise
被错误记作 failure
```

时优化 Grader。

这是合理修改。

因为：

```text
Grader 本身错误
```

也确实可能是 Root Cause。

但这种修改必须回答：

```text
我们是在修复错误判定，
还是在降低通过标准？
```

两者表面上都可能让 Eval Score 上升。

---

#### 因此最好区分 Behavior Surface 和 Measurement Surface

可以进一步把 Mutable Surface 分成两类。

第一类：

```text
Behavior Surface
```

它决定系统实际做什么：

```text
Prompt
Skill
Source Selection
Schema
Extraction
Mapper
Product Code
```

第二类：

```text
Measurement Surface
```

它决定系统怎样被判定：

```text
Eval Dataset
Suite
Grader
Threshold
```

于是：

```text
Mutable Surface
=
Behavior Surface
+
Measurement Surface
```

两者都可能需要演进。

但验证逻辑不同。

如果修改：

```text
Behavior Surface
```

可以问：

```text
旧的 Eval 下，
行为是否改善？
```

如果修改：

```text
Measurement Surface
```

就不能只使用：

```text
新的 Measurement
```

证明自己正确。

否则相当于：

```text
我修改了考试答案
    ↓
然后用新答案证明
我答得更好了
```

更稳妥的做法需要：

```text
历史人工判断
独立 Review
冻结的 Regression Cases
外部 Ground Truth
```

至少其中一部分不受当前 Optimizer 随意修改。

这实际上和 Verification 中反复出现的问题一致：

> **评价系统不能完全被被评价对象控制。**

---

#### Mutable Surface 之外还需要 Immutable Evidence

还有一类信息更加不应该因为优化方便而被修改：

```text
原始生产 Trace

Source Documents

Practitioner Correction

Final Submitted Return
```

这些东西代表：

```text
为什么这个任务存在
```

如果 Optimizer 为了让自己的修复成立，连底层 Evidence 都可以改：

```text
expected = 180

↓ Codex

expected = missing
```

那么整个 Self-Evolving Loop 会失去可追溯性。

因此一个比较稳的结构是：

```text
Immutable / Read-only Evidence
            ↓
        Optimizer
            ↓
      Mutable Surface
            ↓
      Candidate System
```

第 5 节会看到，OpenAI 给 Codex 设计的代表性任务环境正是明确把：

```text
writable worktree
```

和：

```text
read-only production context
```

分开。

这里先只保留这个原则：

```text
Evidence
告诉系统为什么需要改变

Mutable Surface
定义系统允许怎样改变
```

不能把两者混成同一个可编辑状态空间。

### 4.3 Targeted Eval、Regression 与 Candidate PR

假设 Codex 最终定位到：

```text
mapper.ts
```

存在缺口。

并产生一个候选修改：

\[
S_t
\rightarrow
S'_t
\]

到这里仍然不能说：

```text
Self-Evolution completed
```

因为“代码变了”只证明：

```text
Optimizer 做出了动作。
```

接下来至少需要回答三个不同问题：

```text
1. 原来的 Failure 修了吗？

2. 其他行为有没有被改坏？

3. 这个修改是否应该进入生产？
```

OpenAI 的 Tax AI 闭环分别使用：

```text
Targeted Eval

Broader Regression Suite

Engineering Review
```

回答这三个问题。

---

#### Targeted Eval 回答：刚才那个 Finding 修了吗？

假设旧系统：

\[
S_t
\]

在 `fair_rental_days` Eval 上得到：

\[
E_{\text{target}}(S_t)=0.42
\]

候选系统：

\[
S'_t
\]

得到：

\[
E_{\text{target}}(S'_t)=0.96
\]

至少说明：

```text
针对这组代表性 Failure Cases，
候选修改明显改善了表现。
```

这里最重要的是：

```text
same targeted eval
```

提供了修改前后的对照。

于是：

```text
Finding
    ↓
Candidate Fix
    ↓
Targeted Eval
```

形成一个很小的因果实验。

当然，它仍然不是严格的随机对照实验。

但比：

```text
Codex:
“I inspected the code and believe the issue is fixed.”
```

多了一层可执行证据。

---

#### 只跑 Targeted Eval 会发生什么

假设为了修：

```text
fair_rental_days
```

Codex 把 Mapper 改成：

```text
遇到 Rental Property
总是创建 fair_rental_days
```

Targeted Cases 全部通过。

但另一些报税表里：

```text
Source 根本没有 fair_rental_days
```

系统却开始：

```text
hallucinate / fabricate default value
```

于是：

```text
Targeted Eval
100%

Regression
下降
```

这个修改不能直接上线。

另一种更隐蔽的情况是：

```text
为了解决多 Rental Property 混淆
```

修改了 Property Matching。

目标 Case 修好了，却破坏：

```text
single-property flow
```

或者：

```text
other expenses mapping
```

因此 Self-Evolving Loop 如果只优化：

\[
E_{\text{target}}
\]

很容易产生局部过拟合。

真正的接受条件更接近一个约束优化问题：

\[
\max_{\theta'}
E_{\text{target}}(\theta')
\]

subject to：

\[
E_{\text{regression}}(\theta')
\ge
\tau
\]

其中：

```text
τ
= 系统能够接受的回归下界
```

实际系统当然可能拥有多个 Regression Metrics 和不同 Threshold；这个式子只是表达：

> **局部修复不能以不可接受的全局退化为代价。**

---

#### Targeted Eval 和 Regression 的信息职责不同

两者最好不要混成一个：

```text
tests passed
```

因为它们回答的是不同问题。

| 验证层 | 问题 |
|---|---|
| Targeted Eval | 这一次 Finding 对应的问题修了吗？ |
| Regression Suite | 已经会做的其他事情还会吗？ |

也就是：

```text
Targeted
──────────
证明 change 有收益


Regression
──────────
寻找 change 的副作用
```

这和普通软件工程很像。

Bug Fix 通常不会只写：

```text
test_bug_123
```

然后通过就 Merge。

还会运行：

```text
existing test suite
```

因为一个局部 Patch 可能破坏其他 Contract。

Agent System 只不过把 Regression Surface 扩展到了：

```text
Model behavior
Extraction quality
Tool behavior
Mapping correctness
Workflow assumptions
```

等更复杂的行为。

---

#### Regression Suite 也是生产失败的长期记忆

上一节已经提到：

```text
Production Failure
        ↓
Eval Case
        ↓
Fix
        ↓
Regression Asset
```

这时可以看到它为什么重要。

第 \(t\) 次迭代解决：

```text
fair_rental_days
```

于是 Eval 加入：

\[
e_1
\]

第 \(t+1\) 次迭代解决：

```text
other_expenses
```

加入：

\[
e_2
\]

第 \(t+2\) 次解决：

```text
multiple rental properties
```

加入：

\[
e_3
\]

长期下来，系统的 Regression Set 可能逐渐包含：

\[
R_t =
\{e_1,e_2,e_3,\ldots,e_n\}
\]

于是 Self-Evolution 不只是：

```text
系统能力不断修改
```

同时也是：

```text
系统曾经犯过的错误
不断被编码进验收边界
```

这和 Memory 有一点相似，但载体不同。

普通 Memory 可能保存：

```text
“以后记得检查 fair_rental_days。”
```

Regression Asset 保存的是：

```text
“这里有一个具体 Case，
任何未来版本都必须重新通过。”
```

前者是给 Agent 阅读的经验。

后者是给系统执行的约束。

从可靠性角度看，两者作用完全不同。

---

#### Eval 全绿仍然不等于可以自动 Deploy

假设：

```text
Targeted Eval PASS

Regression PASS
```

为什么 OpenAI 还要生成：

```text
candidate pull request
```

供工程师 Review？

因为 Eval 不可能覆盖完整产品语义。

尤其在税务这样的高风险领域，修改可能涉及：

```text
架构边界

代码质量

未来维护成本

权限

数据处理

产品语义

Eval 尚未覆盖的场景
```

这些东西并不一定能被当前 Suite 完整表达。

所以 Tax AI 的闭环不是：

```text
Finding
    ↓
Codex
    ↓
Tests green
    ↓
Auto deploy
```

而是：

```text
Finding
    ↓
Targeted Eval
    ↓
Codex Investigation
    ↓
Candidate Change
    ↓
Targeted Eval
    ↓
Regression Suite
    ↓
Candidate PR
    ↓
Engineering Review
    ↓
Deploy / Reject
```

这里的人类 Review 不应该被理解成：

```text
Self-Evolution 还不够先进，
所以暂时需要人工兜底。
```

它更像系统显式定义的一条：

```text
commit boundary
```

Codex 可以拥有很大的：

```text
search autonomy
```

但不一定拥有：

```text
deployment authority
```

这两件事应该分开。

---

#### Search Autonomy 和 Commit Authority

可以用两个不同权限表示：

```text
Search Autonomy
────────────────────
Agent 可以：
调查
编辑
运行 Eval
反复尝试
提出 PR


Commit Authority
────────────────────
谁可以让修改
真正成为下一生产版本？
```

Tax AI 当前的答案是：

```text
Codex
拥有较大的 Search Autonomy

Engineer
保留 Commit / Shipping Authority
```

这和 Harness 中：

```text
Capability
vs
Authorization
```

的区分很相似。

模型能够提出：

```text
tool_use
```

不代表 Tool 一定被执行。

同样：

```text
Optimizer 能产生 Candidate System
```

也不代表：

```text
Candidate System
一定成为 Production System
```

因此状态转移其实更准确地写成：

\[
S_t
\xrightarrow{\text{improve}}
S'_t
\]

然后：

\[
S'_t
\xrightarrow{\text{validate + review}}
\begin{cases}
S_{t+1}, & \text{accept} \\
S_t, & \text{reject}
\end{cases}
\]

也就是说：

```text
reject
```

本身是合法结果。

Self-Evolving Loop 并不要求每一轮都产生新版本。

---

#### 一个没有改动的循环也可能是正确结果

还有两种情况应该允许：

```text
Finding
    ↓
调查
    ↓
证据不足

→ Escalate
```

或者：

```text
Finding
    ↓
调查
    ↓
Current behavior is intended

→ No Fix
```

OpenAI 明确指出，如果证据存在歧义，或者问题无法安全自动化，该 Case 会回流产品团队，而不是被强行推进自动改进流程。

所以状态机不应该只有：

```text
Finding
→ Fix
→ Deploy
```

而应该至少允许：

```text
                 ┌─→ Candidate Fix
                 │        ↓
Finding ─────────┤     Validate
                 │        ↓
                 │   Review / Deploy
                 │
                 ├─→ Escalate
                 │
                 └─→ No Change
```

这件事很关键。

否则一个“必须进化”的系统会产生一种危险的优化压力：

```text
每发现一个差异
都必须找到一个可修改对象

每创建一个 Eval
都必须把 Score 做高

每一轮
都必须产生 Commit
```

最后很容易出现：

```text
为了证明自己在改进
而不断修改系统
```

但生产系统真正需要的是：

```text
有证据时改

没有证据时不改
```

---

#### 因此一次完整的 Codex 优化循环可以写成

到这里，第 4 节可以把 Codex 的工作压成：

```text
Targeted Eval Failure
        ↓
Inspect Production Trace
        ↓
Inspect Source Artifacts
        ↓
Inspect Code / Schema / Mapper / Grader
        ↓
Form Root-Cause Hypothesis
        ↓
Choose Mutable Surface
        ↓
Implement Candidate Fix
        ↓
Run Targeted Eval
        ↓
        PASS?
       /    \
     no      yes
     │        │
     └─ edit  ▼
          Regression Suite
                 ↓
                PASS?
               /    \
             no      yes
             │        │
             └─ edit  ▼
                    Candidate PR
                         ↓
                  Engineering Review
                    /          \
                 reject       deploy
                               ↓
                             S_{t+1}
```

这条链里，Codex 并没有获得一个：

```text
“让系统变得更聪明”
```

的抽象任务。

它拿到的是一个非常具体的搜索问题：

```text
Evidence:
这些生产 Case 反复失败

Target:
这个 Targeted Eval 要改善

Mutable Surface:
这些产品接口允许修改

Constraints:
Regression 不能出现不可接受退化

Output:
一个可以 Review 的 Candidate PR
```

于是 Self-Evolution 终于从：

```text
Reflection
```

变成了一个工程过程：

\[
\text{Evidence}
\rightarrow
\text{Diagnosis}
\rightarrow
\text{Search}
\rightarrow
\text{Verification}
\rightarrow
\text{Commit Decision}
\]

但现在还有一个很实际的问题没有解释。

为了让 Codex 完成上面的调查，它必须同时接触：

```text
生产 Trace
源文件
Expected Output
代码仓库
Eval
Skills
Docs
```

其中有些东西应该：

```text
read-only
```

有些东西必须：

```text
writable
```

有些信息属于：

```text
当前任务
```

有些则属于：

```text
整个代码库
```

如果只是把所有内容塞进一个 Prompt：

```text
这里是生产数据、代码、文档和测试，
请修好它。
```

前面建立的边界又会重新消失。

所以接下来需要解决的已经不是：

```text
Codex 会不会改代码？
```

而是：

> **怎样把一个 Finding 包装成 Codex 可以长时间自主调查、修改和验证，同时又不会污染底层 Evidence 的 Task Environment？**

## 5. Self-Evolving Agent 需要怎样的 Harness

前一节最后得到的 Codex 优化任务已经相当具体：

```text
Evidence:
某类生产 Case 反复失败

Finding:
fair_rental_days 经常缺失

Target:
Targeted Eval 必须改善

Mutable Surface:
允许修改相关产品代码

Constraint:
Regression 不能出现不可接受退化

Output:
Candidate PR
```

但这里还有一个容易被一句：

```text
“让 Codex 去修”
```

掩盖的问题。

Codex 真正开始工作时，需要同时访问：

```text
生产 Trace
源文件
最终提交结果
Tax Engine 文档
代码仓库
Eval Dataset
Eval Suite
Grader
Skills
架构文档
任务说明
```

这些东西显然不能被当作一团文本全部塞进 Prompt。

原因不只是 Context Window。

更大的问题是它们拥有完全不同的语义：

```text
Production Trace
是证据

Source Artifact
是证据

Final Return
是证据

Code
是可修改实现

Eval
定义成功条件

Skill
告诉 Agent 怎样完成某类操作

Docs
提供系统约束与既有决策
```

如果这些边界没有被 Harness 显式表达，Optimizer 就需要自己猜：

```text
哪些东西只是让我看？

哪些东西允许我改？

哪里才是产品代码？

哪个测试是当前 Target？

哪些历史测试不能破坏？

完成以后我要留下什么？
```

OpenAI 在 Tax AI 的文章里因此没有只给出一个 Prompt 示例，而是给出了一个代表性的 Codex Task Environment：

```text
/candidates/FIND-RENTAL-0042/
│
├── repo/
│   └── branch: codex/fix-rental-0042
│       │
│       ├── AGENTS.md
│       │
│       ├── tasks/FIND-RENTAL-0042/
│       │   ├── task.yaml
│       │   ├── EXEC_PLAN.md
│       │   └── RESULTS.md
│       │
│       ├── app/tax-ai/rental-income/
│       │   ├── agent.ts
│       │   ├── schema.ts
│       │   ├── provenance.ts
│       │   └── mapper.ts
│       │
│       ├── evals/
│       │   ├── datasets/fair-rental-days.yaml
│       │   ├── suites/fair-rental-days.yaml
│       │   ├── suites/rental-income-regression.yaml
│       │   └── graders/rental-income.yaml
│       │
│       ├── skills/
│       │   ├── eval-runner/
│       │   └── tax-field-docs/
│       │
│       └── docs/
│           ├── architecture/
│           └── task-environments/
│
└── scoped-tools/
    ├── production-trace
    ├── source-artifacts
    └── tax-engine-docs
```

OpenAI 特别说明，这只是一个 **representative rental-property task** 的上下文示意。不能据此认为 Tax AI 的真实生产仓库恰好使用这套目录，或者 `task.yaml` 存在某组未公开字段。

但这个结构足以说明 Harness 在 Self-Evolving Loop 中承担的职责。

它不是简单提供：

```text
LLM
+
Shell
+
Repository
```

而是在给 Optimizer 构造一个受约束的局部世界：

```text
你为什么来到这里
        ↓
你能看到什么
        ↓
你能修改什么
        ↓
怎样判断修改有效
        ↓
怎样留下结果
```

从这个角度看，第 4 节的：

```text
Mutable Surface
```

到了这里才真正被实现成运行时边界。

### 5.1 一个 Finding 如何变成 Task Environment

先看最外层目录：

```text
/candidates/FIND-RENTAL-0042/
```

它没有叫：

```text
/general-self-improvement/
```

也没有：

```text
make-tax-ai-better/
```

而是绑定到一个具体 Finding：

```text
FIND-RENTAL-0042
```

这个命名本身就在表达一种任务粒度：

```text
Production Failure
        ↓
Reviewed Finding
        ↓
Bounded Candidate Task
```

也就是说，第 3 节中得到的：

```text
Finding
```

不只是写进数据库里的一条分析结果。

它最终会成为一次独立工程尝试的身份。

可以把这个转换理解为：

\[
F_i
\rightarrow
T_i
\]

其中：

```text
F_i
= reviewed finding

T_i
= bounded engineering task
```

一个好的 `T_i` 至少需要让 Agent 知道：

```text
Problem
Evidence
Scope
Editable Surface
Validation
Artifacts
```

OpenAI 对输入集合的描述也很明确。Codex 获得的不是一句自然语言 Bug Report，而是一组已经组织好的上下文：

```text
reviewed finding

production-derived source trace

expected tax-engine output

relevant code examples

eval command
```

于是：

```text
“fair_rental_days 好像有问题”
```

被转化成：

```text
这里有一个经过审查的重复 Failure。

这是相关生产 Trace。

这是代表性 Source Package。

这是 Expected Output。

这是相关代码区域。

这是 Targeted Eval。

这是 Regression Eval。

请在给定产品界面中调查并提出修复。
```

两者最大的差别不是 Prompt 长短。

而是后者已经具备：

```text
可调查性
可执行性
可验证性
```

---

#### 为什么要建立独立 Candidate Workspace

目录的下一层是：

```text
repo/
└── branch: codex/fix-rental-0042
```

这里可以看到 Self-Evolving Loop 并不是：

```text
Codex
直接修改 Production Branch
```

而是：

```text
Production System
      ↓
发现 Finding
      ↓
创建 Candidate
      ↓
独立 Branch 中搜索
```

也就是先生成：

\[
S'_t
\]

而不是直接把：

\[
S_t
\]

改成：

\[
S_{t+1}
\]

这正好对应上一节的状态转移：

\[
S_t
\xrightarrow{\text{search}}
S'_t
\xrightarrow{\text{validate + review}}
S_{t+1}
\]

Candidate Workspace 的作用之一，就是给：

```text
S'_t
```

一个真实存在的隔离空间。

Codex 可以在里面：

```text
Read
Edit
Run
Fail
Revert
Edit Again
```

这些探索都不应该立即改变生产系统。

所以从 Harness 角度看：

```text
Workspace Isolation
```

不是方便整理文件的附属功能。

它定义的是：

> **Optimizer 的搜索副作用发生在哪里。**

如果没有这个边界：

```text
Search
```

和：

```text
Commit
```

就会重新混在一起。

---

#### Branch 同时提供了 Diff Boundary

一旦一次优化被限制在：

```text
codex/fix-rental-0042
```

这个 Branch 上，最终工程 Review 的对象也会自然变成：

```text
S'_t - S_t
```

也就是：

```text
这一次 Finding
究竟让系统发生了什么变化？
```

而不是让 Reviewer 面对一个已经悄悄变化了很多轮的共享环境。

对于 Self-Evolving System，这种 Diff Boundary 尤其重要。

因为长期下来系统可能经历：

```text
Finding 0042
Finding 0043
Finding 0044
Finding 0045
...
```

如果这些 Candidate 全部在同一个可写状态里连续发生：

```text
0042 修改 A

0043 修改 B

0044 又修改 A

0045 修改 Grader
```

后来一旦 Regression 出现，很难回答：

```text
到底哪一次 Evolution
引入了这个行为？
```

独立 Candidate / Branch 至少提供：

```text
Finding
↔
Candidate Change
```

之间的关联。

于是可以追踪：

```text
为什么改？
改了什么？
验证了什么？
最终有没有进入 Production？
```

这其实是在给 Self-Evolution 增加：

```text
change provenance
```

它与前面字段级：

```text
data provenance
```

不是同一件事。

前者追踪：

```text
系统修改从哪里来
```

后者追踪：

```text
业务字段从哪里来
```

但两者都服务于同一个目标：

```text
不要让状态变化失去来源。
```

---

#### `tasks/FIND-RENTAL-0042/` 保存的是任务状态，而不是聊天记录

再往下：

```text
tasks/FIND-RENTAL-0042/
├── task.yaml
├── EXEC_PLAN.md
└── RESULTS.md
```

OpenAI 没有公开这三个文件的真实内容，因此这里不能给它们编造 schema。

但从整个 Task Environment 的结构至少可以确定：

```text
任务本身
```

被保存成 Repository 中的显式 Artifact，而不是只存在于：

```text
某个 Codex Session 的 Conversation History
```

这是长任务 Harness 中非常关键的区分。

如果任务状态只存在于：

```text
Chat Context
```

那么：

```text
Context Reset
Session Crash
Agent Handoff
任务跨小时运行
```

都可能让：

```text
我们为什么在改这个东西？
```

逐渐丢失。

而一个显式 Task Directory 可以承担跨 Session 的 Durable State。

从文件名能够保守地理解为：

```text
task.yaml
────────────────────
机器可读取的任务描述 / 配置入口


EXEC_PLAN.md
────────────────────
执行过程中的计划 Artifact


RESULTS.md
────────────────────
任务执行结果 Artifact
```

这里的具体字段、格式和更新规则并未在文章中公开。

重要的不是这三个名字必须照抄，而是：

> **长期优化任务需要有 Conversation 之外的持久任务表示。**

这与普通 Coding Agent 的：

```text
Prompt
    ↓
做完
    ↓
Final Answer
```

不同。

Self-Evolving Task 更接近：

```text
Finding
    ↓
Task Artifact
    ↓
Plan
    ↓
Execution
    ↓
Eval Results
    ↓
Candidate Change
    ↓
Review
```

其中每一步都可能跨越多个模型调用。

---

#### Conversation State 不应该成为唯一的 Task State

这和前面 Claude Code Harness 里已经见过的三层区分正好接上：

```text
Model Context
≠
Conversation State
≠
Durable Task State
```

Self-Evolving Loop 又多了一层：

```text
Production Evolution State
```

于是长期来看可以画成：

```text
Model Context
────────────────────────
当前这一轮模型真正看到什么


Conversation State
────────────────────────
当前 Codex Session 做过什么


Task State
────────────────────────
FIND-RENTAL-0042
现在调查到哪里


Evolution State
────────────────────────
这个 Finding 是否：

observed
reviewed
evaluated
candidate-created
validated
reviewed
deployed
rejected
```

这些状态全部塞进 Chat History，很难长期维护。

所以 Task Environment 的第一层作用可以概括为：

```text
Finding
        ↓
Materialize
        ↓
Durable Engineering Task
```

Self-Evolution 因此不是：

```text
Agent 想起来要改自己
```

而是：

```text
生产系统把一个经过审查的问题
编译成一个独立、可恢复、
有成功条件的工程任务。
```

### 5.2 Writable Workspace 与 Read-only Evidence

整棵目录树里最值得单独看的，其实不是某个文件名，而是最外层这两个区域：

```text
repo/
```

和：

```text
scoped-tools/
```

OpenAI 对它们的解释非常直接。

`repo/` 是：

```text
writable worktree
```

而 `scoped-tools/` 暴露的是：

```text
read-only production context
```

具体包括：

```text
production-trace
source-artifacts
tax-engine-docs
```

这正好把第 4 节最后建立的两类状态真正分离：

```text
              Codex
             /     \
            /       \
           ▼         ▼

      Evidence      Workspace
      read-only      writable

production trace     agent.ts
source artifacts     schema.ts
tax-engine docs      provenance.ts
final outcomes       mapper.ts
                     evals/
                     ...
```

这里的原则非常朴素：

```text
Agent 可以根据证据修改系统

但不能为了让修改成立
反过来修改证据
```

---

#### 为什么 Production Trace 必须只读

假设 Targeted Eval 来自一个生产 Case：

```text
Source:
fair rental days = 180

Tax AI:
missing

Practitioner:
补成 180
```

Codex 调查以后发现自己的实现很难通过 Eval。

如果它拥有修改 Production Trace 的权限，那么理论上最简单的“修复”可能是：

```text
删除这条 Trace

或者

把 Tax AI 当时的输出
从 missing 改成 180
```

此时系统并没有改善。

只是：

```text
失败证据消失了。
```

因此：

```text
Evidence Integrity
```

必须独立于：

```text
Optimizer Convenience
```

这和软件测试中不能为了让测试通过就修改测试期望值，是同一类约束。

但这里更严格，因为 Production Trace 描述的是已经发生过的现实事件。

它承担：

```text
historical evidence
```

的角色。

所以：

```text
Production Evidence
```

应该更接近：

```text
append / reference
```

而不是：

```text
自由 rewrite
```

至少对于当前 Candidate Agent 来说，它应该是只读的。

---

#### Source Artifacts 同样不能被“修复”

再看：

```text
source-artifacts
```

假设原始文件本身格式很难处理：

```text
rental-summary.xlsx
handwritten-note.pdf
client-email.eml
```

如果 Optimizer 可以直接重写 Source：

```text
把复杂表格整理干净

把手写内容转成标准字段

把 Email 改成 JSON
```

Targeted Eval 当然会容易很多。

但这优化的是：

```text
测试输入
```

而不是：

```text
生产 Agent
```

未来真实客户仍然会上传原始形式的文件。

所以 Source Artifact 必须保留：

```text
真实问题长什么样
```

这件事。

这也是生产 Eval 和 Toy Eval 的区别之一。

真正困难的地方恰恰可能是：

```text
输入不整洁

证据跨文件

命名不统一

字段隐含在自然语言里
```

如果优化器可以整理掉这些困难，Eval 就失去了对应生产分布的意义。

---

#### Tax Engine Docs 是 Context，不是产品修改面

`scoped-tools/` 里还有：

```text
tax-engine-docs
```

它承担的是另一个角色。

Codex 调查：

```text
mapper.ts
```

时，必须知道下游 Tax Engine：

```text
支持哪些字段

字段如何命名

允许什么映射

接口约束是什么
```

否则它可能修改出：

```text
代码逻辑自洽
```

但：

```text
下游系统根本不接受
```

的方案。

所以 Docs 是：

```text
decision context
```

而不是：

```text
candidate state
```

从权限模型上看：

```text
read
≠
write
```

非常重要。

Agent 需要足够 Context 做出好决定，不意味着所有 Context 都应该进入 Mutable Surface。

---

#### 为什么要通过 Scoped Tools 暴露 Evidence

OpenAI 的示意不是：

```text
/candidates/
└── dump/
    ├── all-production-logs.json
    ├── all-client-files/
    └── all-tax-engine-docs/
```

而是：

```text
scoped-tools/
├── production-trace
├── source-artifacts
└── tax-engine-docs
```

这个区别值得注意。

它表示生产 Evidence 可以通过：

```text
bounded capability
```

提供，而不必把整个生产环境直接挂载给 Codex。

这与 Tool Contract 中的原则一致：

```text
Capability
≠
unrestricted environment access
```

例如一个概念上的：

```text
production-trace
```

Tool 可以只允许查询：

```text
FIND-RENTAL-0042
```

相关 Trace，而不是让 Agent：

```text
SELECT * FROM production
```

同样：

```text
source-artifacts
```

可以只暴露当前 Finding 所需文件。

于是：

```text
Task Scope
```

不只是 Prompt 中的一句话：

```text
“只看这个问题。”
```

而可以下沉成：

```text
Tool Capability Scope
```

即：

```text
你物理上只能访问
这个任务需要的 Evidence。
```

---

#### 这是 Context Engineering，也是在做安全边界

Scoped Context 有两个直接效果。

第一个是减少无关信息：

```text
Whole Production System
        ↓
Task-relevant Evidence
```

让 Codex 不必在大量无关 Trace 中搜索。

第二个是减少权限暴露：

```text
整个生产数据库
```

和：

```text
当前 Finding 的只读 Trace
```

显然拥有不同风险面。

所以：

```text
Context Bounding
```

和：

```text
Permission Bounding
```

在这里是同一个 Task Environment 的两面。

可以画成：

```text
                 Task Boundary
┌────────────────────────────────────────┐
│                                        │
│              Codex                     │
│                                        │
│   ┌───────────────┐ ┌───────────────┐ │
│   │ Read-only     │ │ Writable      │ │
│   │ Evidence      │ │ Candidate     │ │
│   │               │ │ State         │ │
│   │ Trace         │ │               │ │
│   │ Sources       │ │ Code          │ │
│   │ Docs          │ │ Schema        │ │
│   │ Final Output  │ │ Mapper        │ │
│   │               │ │ Eval impl.    │ │
│   └───────────────┘ └───────────────┘ │
│                                        │
└────────────────────────────────────────┘
```

然后在 Task Boundary 外面仍然存在：

```text
其他 Production Data
其他 Repository Surface
Deployment Authority
Secrets
Unrelated Tools
```

这些东西不需要因为 Codex“理论上可能用得上”就全部开放。

---

#### Read-only Evidence 也让失败归因更加可信

假设 Candidate 最终通过 Eval：

```text
S_t
→
S'_t

Eval:
FAIL
→
PASS
```

如果：

```text
Source
Trace
Expected Outcome
```

在两次运行之间保持不变，那么我们至少拥有一个比较稳定的对照：

```text
变化的是 Candidate System
```

而不是：

```text
系统和题目一起变了。
```

这让：

```text
before
vs
after
```

更有解释力。

换句话说，Read-only Evidence 不只是安全设计，也是实验设计的一部分。

它帮助建立：

\[
\Delta E
\]

更可能来自：

\[
\Delta S
\]

而不是：

\[
\Delta D
\]

其中：

```text
S
= system

D
= evaluation evidence / input
```

当然，真实 Agent Eval 仍然可能受到非确定性等因素影响，不能因此宣称严格因果证明。

但至少：

```text
不要让 Optimizer 同时修改实验对象和原始证据
```

是一个非常基础的前提。

### 5.3 Skills、Docs 与 Eval 如何压缩搜索空间

到这里，一个 Candidate Task 已经拥有：

```text
Finding
Workspace
Read-only Evidence
```

看起来 Codex 已经可以开始了。

但 OpenAI 的目录里还专门放了：

```text
AGENTS.md

evals/

skills/

docs/
```

这些文件为什么不是多余的？

一种想法是：

```text
模型已经很强了。

给它 Repo 和 Shell，
自己读代码不就行了吗？
```

对于小仓库、短任务，这有时确实够用。

但 Self-Evolving Loop 面对的是另一种工作：

```text
每一个生产 Finding
都会重复创建新的工程任务
```

如果每个 Candidate 都要求 Codex 从头重新发现：

```text
这个仓库怎么运行？

Eval 命令是什么？

Architecture 为什么这样设计？

哪些 Tax Field 有特殊规则？

哪些实现决策不能随便改？

如何检查结果？
```

系统就会不断为同一类背景知识重新支付：

```text
探索成本
```

OpenAI 在这一 Task Environment 中把一部分稳定知识编码进：

```text
AGENTS.md
Skills
Docs
Eval Infrastructure
```

它们共同承担的作用，可以理解成：

> **把一个开放式 Repository Search 压缩成一个更有结构的工程搜索问题。**

---

#### `AGENTS.md`：把仓库级约束放到任务之外

目录根部存在：

```text
AGENTS.md
```

OpenAI 在这篇文章里没有进一步展开它的具体正文，因此不能猜测其中有哪些指令。

但在 Codex Harness 中，它所处的位置至少表明：

```text
Candidate Task
```

并不是唯一的 Instruction Source。

还存在：

```text
Repository-level Instructions
```

这类 Artifact 的价值在于：

```text
Task-specific instruction
```

不必重复携带所有稳定约束。

可以抽象成：

```text
Stable Repository Context
        +
Task-specific Context
```

其中：

```text
AGENTS.md / Docs / Skills
```

更接近前者，

而：

```text
task.yaml / Finding / Trace
```

属于后者。

这让每一个新 Finding 不需要从零重新解释整个工程世界。

---

#### `evals/` 把“成功”做成可执行接口

目录中最明确的一组文件是：

```text
evals/
├── datasets/fair-rental-days.yaml
├── suites/fair-rental-days.yaml
├── suites/rental-income-regression.yaml
└── graders/rental-income.yaml
```

这几乎把第 3、4 节讨论的概念直接落到了文件结构。

```text
datasets/fair-rental-days.yaml
```

对应：

```text
代表性 Case
```

```text
suites/fair-rental-days.yaml
```

对应：

```text
Targeted Eval
```

```text
suites/rental-income-regression.yaml
```

对应：

```text
Regression Boundary
```

```text
graders/rental-income.yaml
```

对应：

```text
怎样判定结果
```

于是：

```text
“请把 fair_rental_days 修好”
```

不再只是 Natural Language Requirement。

它有一个 Harness 可以执行的对应物：

```text
run targeted suite
```

---

#### Eval 是 Agent 和 Harness 之间的一种 Contract

Codex 自己可以决定：

```text
先读哪个文件
提出什么 Hypothesis
修改 Schema 还是 Mapper
尝试几轮
```

但它不能随便决定：

```text
什么叫任务完成
```

完成条件已经通过：

```text
Dataset
Suite
Grader
Regression
```

部分外置。

于是可以写成：

```text
Agent
────────────────────
Search Policy

Harness / Eval
────────────────────
Acceptance Contract
```

这与 Tool Contract 很相似。

模型可以生成：

```text
tool_use
```

但 Tool 是否执行，取决于 Runtime。

同样：

```text
Codex:
“我认为已经修好了。”
```

不等于：

```text
Task = complete
```

Harness 还会运行：

```text
Targeted Eval
Regression Eval
```

因此：

```text
Completion Claim
```

和：

```text
Completion Evidence
```

被分开保存。

---

#### `skills/eval-runner/`：把操作方法从 Prompt 里抽出来

OpenAI 示例中还有：

```text
skills/
└── eval-runner/
```

如果 Codex 每次执行 Eval 都需要先研究：

```text
怎么启动服务

需要什么参数

输出格式是什么

失败以后去哪里看 Artifact

怎样运行某个 Suite
```

那么大量推理预算会浪费在重复摸索 Harness 本身。

`eval-runner` 这类 Skill 可以把：

```text
如何执行 Eval
```

变成一个可复用 Procedure。

概念上：

```text
Without Skill

Finding
  ↓
先研究 Eval Infrastructure
  ↓
尝试命令
  ↓
失败
  ↓
继续研究
  ↓
终于开始真正 Debug


With Skill

Finding
  ↓
load eval-runner
  ↓
按已有 Procedure 运行 Eval
  ↓
开始 Debug
```

所以 Skill 在这里并不是：

```text
给模型增加更多知识
```

这么简单。

它更像是：

```text
把已经稳定的操作路径
从每个 Candidate 的搜索空间中拿出去
```

即：

\[
\mathcal{S}_{\text{raw}}
\xrightarrow{\text{Skill}}
\mathcal{S}_{\text{bounded}}
\]

其中：

```text
S_raw
= Agent 从整个环境自行探索的动作空间

S_bounded
= 利用已有 Procedure 后需要实际探索的空间
```

---

#### `tax-field-docs/`：把领域知识按需装载

另一项 Skill：

```text
tax-field-docs/
```

对应的则更接近领域知识访问。

Tax AI 面对的是大量 Tax Field。并不是每一个 Finding 都需要把：

```text
整个税法
全部 Tax Engine Schema
所有字段说明
```

塞进主 Context。

针对：

```text
fair_rental_days
```

当前任务真正需要的可能只是相关 Tax Field 的定义、映射约束和已有实现约定。

所以可以使用：

```text
task
    ↓
identify needed knowledge
    ↓
load relevant skill / docs
```

而不是：

```text
load everything
    ↓
hope model attends to the right part
```

这和 Context Engineering 中：

```text
retrieve on demand
```

的思想一致。

Skill 的一个价值，就是把 Context 从：

```text
全量静态注入
```

变成：

```text
按任务调用的能力 / 知识包
```

---

#### `docs/architecture/`：不要让 Agent 每次重新推测架构

还有：

```text
docs/
├── architecture/
└── task-environments/
```

代码能够告诉 Agent：

```text
现在怎么实现
```

却不一定告诉它：

```text
为什么要这样实现
```

例如 Codex 看到：

```text
provenance.ts
```

可能认为：

```text
这个中间层看起来可以删，
直接让 agent.ts 输出最终字段更简单。
```

从局部代码优化角度看，这甚至可能合理。

但如果架构设计要求：

```text
每个 Tax Field
必须能够追溯到 Source Evidence
```

那么删除 Provenance Layer 会破坏系统更高层的产品 Contract。

这种约束如果只存在于某个工程师脑中：

```text
Agent 不知道
```

如果只存在于几个月前的聊天记录：

```text
Agent 也很难稳定获得
```

所以 Architecture Docs 的作用之一就是把：

```text
既有设计决策
```

变成：

```text
Optimizer 可读取的长期 Context
```

---

#### Harness 的目标不是把所有答案告诉 Agent

讲到这里容易出现另一个误解：

```text
既然 Skills / Docs / AGENTS.md 越完整，
那是不是应该把所有东西都规定死？
```

不是。

如果所有 Finding 都已经拥有：

```text
确定 Root Cause
确定 Patch
确定代码位置
确定实现方法
```

那么也不需要 Codex 做太多 Investigation。

Harness 真正需要压缩的是：

```text
无价值的搜索
```

而不是：

```text
所有搜索
```

例如：

```text
Eval 怎么运行
```

通常不值得每次重新发现。

```text
这个 Repository 的安全约束
```

也不值得每个 Candidate 重新猜。

但：

```text
为什么 fair_rental_days
在这些生产 Case 上失败？
```

正是当前任务需要 Agent 自主调查的部分。

所以可以把搜索空间分成：

```text
Known Infrastructure
────────────────────────
AGENTS.md
Skills
Docs
Eval commands

尽量固化


Unknown Task Cause
────────────────────────
Failure attribution
Root cause
Candidate fix

留给 Agent 搜索
```

这种边界比：

```text
给 Agent 尽可能少的信息
```

或者：

```text
把所有信息全塞给 Agent
```

都更有用。

---

#### 一个好的 Harness 实际上在定义 Search Problem

现在可以重新看整棵目录：

```text
Finding
│
├── task/
│   └── 为什么要做
│
├── production evidence
│   └── 现实里发生了什么
│
├── scoped code
│   └── 哪里允许修改
│
├── targeted eval
│   └── 当前问题怎样算修好
│
├── regression
│   └── 哪些既有能力不能破坏
│
├── skills
│   └── 已知操作怎样执行
│
└── docs
    └── 哪些架构和领域约束必须遵守
```

于是 Codex 真正面对的不是：

```text
一个 Repository
```

而是一个被 Harness 编译过的 Search Problem：

\[
T =
(
F,
D,
\mathcal{M},
E_t,
E_r,
K,
C
)
\]

其中：

```text
F
= Finding

D
= read-only evidence

M
= Mutable Surface

E_t
= Targeted Eval

E_r
= Regression Eval

K
= Skills / domain knowledge

C
= repository / architecture constraints
```

这个式子仍然只是本文的工程抽象。

它想说明的是：

> **Self-Evolving Agent 的输入不是一条失败消息，而是一个可执行的优化环境。**

---

#### 这就是 Harness 和 Self-Evolution 真正接上的地方

前面的 Harness 文章讨论的是：

```text
怎样让 Agent
持续、受控、可观察、可验证地
完成一个长任务
```

Self-Evolving Loop 做的事情，是把：

```text
生产系统自己产生的 Failure
```

重新包装成这种长任务。

于是两条链终于连接起来：

```text
Production System
        ↓
Failure Evidence
        ↓
Finding
        ↓
Eval
        ↓
Task Environment
        ↓
Codex Harness
        ↓
Candidate Change
        ↓
Verification
        ↓
Production System
```

换句话说：

```text
Harness Engineering
```

解决：

```text
给定一个任务，
Agent 怎样可靠地执行？
```

而：

```text
Self-Evolving System
```

还要多解决前半段：

```text
怎样从生产行为中
自动产生一个值得执行的新任务？
```

如果只拥有前者：

```text
Codex 很会修问题

但人仍然需要手工发现、
整理和喂给它每一个问题。
```

如果只拥有后者：

```text
系统很会发现 Failure

但没有可靠的环境
让 Agent 调查、修改和验证。
```

两者合起来才形成：

```text
Production
    ↓
Task Generation
    ↓
Task Execution
    ↓
Verification
    ↓
Deployment
    ↓
Production
```

---

#### Task Environment 也是 Autonomy Boundary

最后还可以从另一个角度理解这棵目录树。

它不是只在告诉 Agent：

```text
你拥有什么。
```

同时也在告诉它：

```text
你不拥有什么。
```

例如：

```text
你可以：

读当前 Finding 的 Production Trace
读相关 Source Artifact
读 Tax Engine Docs
修改 Candidate Worktree
运行 Targeted Eval
运行 Regression


你不可以：

修改原始 Production Evidence
直接修改 Production Branch
访问所有无关生产数据
绕过 Eval 宣布上线
自己获得 Shipping Authority
```

这就把：

```text
Agent Autonomy
```

从一个模糊等级变成了若干具体 Capability。

可以写成：

```text
Autonomy
=
Search Freedom
inside
Explicit Boundaries
```

而不是：

```text
Autonomy
=
Remove Boundaries
```

Tax AI 的 Codex 可以在 Candidate Workspace 中拥有相当大的调查和修改自由，但系统仍然固定：

```text
Evidence Boundary
Context Boundary
Tool Boundary
Eval Boundary
Review Boundary
Deployment Boundary
```

Self-Evolving Agent 因此并不是因为：

```text
系统可以修改自己
```

就必须取消控制面。

恰好相反。

> **允许 Optimizer 产生持久系统修改以后，哪些状态不可修改、哪些证据不可伪造、什么条件允许修改进入下一版本，反而需要比普通 Agent Loop 定义得更清楚。**

到这里，一个 Finding 已经能够被完整包装成：

```text
Reviewed Failure
        ↓
Bounded Candidate Workspace
        +
Read-only Evidence
        +
Scoped Mutable Surface
        +
Targeted Eval
        +
Regression
        +
Skills / Docs
        ↓
Codex Search
        ↓
Reviewable Candidate
```

但这一结构仍然不是：

```text
Recursive Self-Improvement
```

也不是：

```text
完全自治的 Agent
```

Tax AI 明确把自动化限制在产品的一个有边界层：这一层负责提取以及把源文档映射到税务工作流；工程师仍然负责架构、产品决策和上线，从业者仍然通过修正、审查和批准最终申报来指导改进。

所以接下来需要把：

```text
self-improving
```

这个词的边界再收紧一次。

否则：

```text
Prompt 自动优化

Skill 自动更新

Harness 改代码

在线训练模型

修改 Evaluator

Recursive Self-Improvement
```

很容易继续被混在同一个概念里。

下一节要回答的就是：

> **Tax AI 已经能够修改自己的产品系统，为什么这仍然不是“完全自主的 RSI”？**

## 6. 为什么这仍然不是完全自主的 RSI

到目前为止，Tax AI 已经满足了一个相当强的 Self-Improving Loop：

```text
Production
    ↓
Practitioner Correction
    ↓
Trace
    ↓
Finding
    ↓
Eval
    ↓
Codex Task
    ↓
Candidate Modification
    ↓
Targeted Eval
    ↓
Regression
    ↓
Review
    ↓
Deploy
```

系统不仅会在一次任务内部根据失败重试，还能够把生产中的重复问题转化成后续版本的持久修改。

从第 1 节使用的状态表示看：

\[
S_{t+1}\neq S_t
\]

已经成立。

甚至：

```text
Prompt
Skill
Schema
Mapper
Grader
Product Code
```

都可能进入 Mutable Surface。

如果只按照：

```text
系统能不能修改自己？
```

这个问题判断，那么 Tax AI 已经很容易被叫作：

```text
self-modifying
```

甚至：

```text
recursive self-improvement
```

但这两个词会掩盖几个没有消失的边界。

Tax AI 并没有让 Codex 自己决定：

```text
什么业务目标值得追求

什么生产差异必须自动化

整个产品架构应该变成什么样

什么 Eval 可以被废弃

什么风险可以接受

什么时候可以绕过工程审查

什么时候应该直接上线
```

相反，这套系统的很多可靠性恰恰来自：

```text
这些边界没有交给同一个 Optimizer。
```

OpenAI 对这一点写得很明确。

他们把 Codex 自动化限定在产品中的一个有边界层，主要负责：

```text
extraction

source documents
    ↓
tax workflows
```

工程师仍然负责：

```text
architecture
product decisions
shipping
```

从业者则通过本来就在进行的工作：

```text
correct extracted values
review returns
approve final filings
```

持续给系统提供反馈。

更重要的是，如果某个 Case：

```text
evidence ambiguous
```

或者：

```text
not safely automatable
```

它不会被强行推进到：

```text
Codex must produce a fix
```

而是重新回到产品团队。

因此，Tax AI 展示的并不是：

```text
所有控制权逐渐交给 Agent
```

而是一种更具体的结构：

```text
扩大 Search Autonomy

同时保留
Goal Boundary
Evidence Boundary
Eval Boundary
Review Boundary
Deployment Boundary
```

理解这个边界以后，Self-Evolving Agent 才不容易和更强意义上的 RSI 混在一起。

### 6.1 无法安全自动化时，正确动作可能是停止 Evolution

Self-Evolving 这个名字很容易让人产生一种错误直觉：

```text
系统应该持续改变。

如果停止修改，
就说明它没有在进化。
```

但生产系统并不是优化 Benchmark。

第 2 节已经看到，一次：

```text
Practitioner changed X → Y
```

可能有多种原因：

```text
Extraction Miss

Mapping Problem

Unsupported Product Behavior

Prior-year Carryover

Practitioner Preference

Tax Judgment

Workflow Noise
```

如果经过 Trace 和 Review 后仍然无法确定它属于哪一种，系统面对的不是一个：

```text
待修 Bug
```

而是一个：

```text
未解决的不确定性
```

这两种状态必须区分。

可以写成：

\[
P(\text{actionable failure}\mid E)
\]

其中：

```text
E
= 当前拥有的 Evidence
```

如果已有证据不足以让系统可靠判断：

```text
这确实是产品应该自动修复的问题
```

那么合理状态不是：

```text
generate patch anyway
```

而是：

```text
request more evidence
```

或者：

```text
escalate
```

OpenAI 在 Tax AI 中采用的就是后者：证据存在歧义，或问题无法安全自动化时，Case 会回到产品团队，而不是被强行推入 Codex Loop。

因此 Self-Evolving Loop 更完整的状态机应该是：

```text
                   ┌───────────────┐
                   │    Finding    │
                   └───────┬───────┘
                           │
                           ▼
                   Evidence Review
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
        actionable     ambiguous     intentional /
             │             │         non-actionable
             │             │             │
             ▼             ▼             ▼
        Codex Task      Escalate       No Change
             │
             ▼
       Candidate Fix
             │
             ▼
         Validate
             │
             ▼
           Review
         /        \
      reject      deploy
```

这里：

```text
No Change
```

和：

```text
Escalate
```

都不是失败状态。

它们是系统明确承认：

```text
当前证据不足以支持一次持久修改
```

或者：

```text
这个问题本来就不属于
当前自动化边界
```

---

#### 为什么“必须每轮都改”会产生错误激励

假设 Self-Evolving Framework 被设计成：

```text
每个 Finding
必须产生一个 Patch。
```

那么 Optimizer 会受到一种隐含压力：

```text
既然任务已经创建，
我就必须找到一个可以修改的东西。
```

即使真正情况是：

```text
Current behavior is correct
```

它也可能继续在：

```text
Prompt
Mapper
Grader
Schema
```

中寻找一个看起来可以优化的位置。

更糟的是，如果成功标准写成：

```text
Eval Score 必须上升
```

而 Agent 同时能够修改：

```text
Behavior
+
Grader
```

那么它总能找到某种方式改变测量条件。

这种系统很容易从：

```text
解决真实 Failure
```

滑向：

```text
为了完成 Evolution Task
而制造一个可以提交的 Change
```

所以 Self-Evolving Loop 最好显式允许：

\[
S_{t+1}=S_t
\]

也就是说，在第 \(t\) 轮观察到新 Evidence 后，最终判断可能是：

```text
不应该修改系统。
```

这和第 1 节写的：

\[
S_{t+1}\neq S_t
\]

并不矛盾。

第 1 节的意思是：

```text
如果我们声称发生了一次
persistent self-improvement，
系统状态必须真正改变。
```

但并不是说：

```text
每一次 Production Feedback
都必须触发这样的变化。
```

更准确的关系是：

\[
S_{t+1}
=
\begin{cases}
\operatorname{Deploy}(S'_t), & \text{证据与验证支持修改} \\
S_t, & \text{不修改更合理}
\end{cases}
\]

---

#### Evolution 需要一个拒绝更新的机制

这和机器学习里的训练直觉也不完全一样。

离线训练通常已经预先假设：

```text
Dataset
```

中的样本属于当前学习问题。

而生产 Agent 收到的 Feedback Stream 并没有经过如此干净的筛选。

实际输入更像：

```text
useful signal
+
noise
+
preferences
+
out-of-scope cases
+
workflow artifacts
+
unknowns
```

所以 Self-Evolving System 在：

```text
怎样更新？
```

之前，还有一个问题：

```text
这一次到底要不要更新？
```

可以把整个决策写成两个阶段：

\[
U_t
=
\operatorname{ShouldUpdate}(F_t)
\]

如果：

\[
U_t=0
\]

则：

\[
S_{t+1}=S_t
\]

只有：

\[
U_t=1
\]

才进入：

\[
S'_t=\operatorname{Improve}(S_t,F_t)
\]

这仍然只是本文的工程抽象。

它想表达的是：

> **Self-Evolution 不只需要 Update Rule，也需要 Update Gate。**

Tax AI 中：

```text
Review
Actionability
Ambiguity Handling
Product Escalation
```

共同承担了一部分 Gate 的作用。

---

#### Escalation 的意义是改变 Decision Maker

Escalation 也不等于：

```text
Agent 做不出来
→ 叫一个更聪明的人来
```

有时问题并不缺推理能力，而是缺少：

```text
Authority

Domain Judgment

Product Decision

Missing Evidence
```

例如：

```text
是否应该让 Agent
自动决定某类 Tax Judgment？
```

这是产品边界问题。

Codex 即使能够写出实现，也不能仅凭：

```text
技术上可以实现
```

推出：

```text
产品应该这样做
```

所以 Escalation 实际上是在说：

```text
当前 Decision
超出了这个 Agent Role
被授权解决的范围。
```

这与 Human-Agent Autonomy 中的：

```text
escalation boundary
```

是同一类机制。

Agent 的自治范围可以很大，但它需要知道：

```text
什么问题属于自己

什么问题必须交回上层控制面
```

---

#### 一个成熟的 Self-Evolving Loop 不应该把“不确定”偷偷改写成“失败”

这里还有一个细节值得保留。

假设 Evidence 只支持：

```text
Root Cause A
或者
Root Cause B
```

系统不应该为了让 Task 继续运行而压成：

```text
Root Cause A
```

否则原本的：

```text
unknown
```

被升级成：

```text
verified
```

后面的所有步骤都会建立在一个虚假的确定性上：

```text
不确定归因
    ↓
被写成确定 Finding
    ↓
产生 Targeted Eval
    ↓
Codex 修 A
    ↓
Eval 通过
```

最后整个 Pipeline 可以看起来非常完整。

问题只是第一步就已经错了。

所以生产 Self-Evolving System 中：

```text
unknown
```

应该是一种合法状态，而不是等待语言模型补全的空白。

这一点和技术文档中的 Evidence State 很相似：

```text
verified
inferred
unknown
```

不能为了让故事完整而随便升级。

Self-Evolving Loop 也一样：

```text
Observed Difference
```

不能自动升级成：

```text
Confirmed Failure
```

而：

```text
Confirmed Failure
```

也不能自动升级成：

```text
Confirmed Root Cause
```

每一次状态提升都需要新的证据。

### 6.2 Practitioner、Codex 与 Engineer 的职责边界

到这里可以更具体地看 Tax AI 中到底是谁在“自我改进”。

如果把整个流程全部画出来：

```text
Practitioner
    ↓
production correction
    ↓
Product Trace
    ↓
review / finding
    ↓
Codex
    ↓
investigate
    ↓
candidate modification
    ↓
eval / regression
    ↓
Engineer
    ↓
review / shipping
    ↓
Production
```

很明显，这不是一个单 Agent Loop。

它更接近一个具有不同 Decision Rights 的系统。

OpenAI 对三种角色给出的边界大致可以整理成：

| 角色 | 主要职责 |
|---|---|
| Practitioner | 修正提取值、审查报税表、批准最终申报，并通过真实工作暴露哪些错误重要 |
| Codex | 调查已结构化 Finding、检查 Trace/Eval/Repo/Skills、提出修改、运行验证、产出 Candidate PR |
| Engineer / Product Team | 处理歧义案例、负责架构与产品决策、审查候选修改、决定上线 |

这里最值得注意的是：

```text
不同角色控制的是不同 Decision。
```

不是简单：

```text
Human = Supervisor
Agent = Worker
```

---

#### Practitioner 控制的是业务 Grounding

从业者并不需要告诉 Codex：

```text
mapper.ts 第 84 行要怎么改。
```

他们提供的是另一种 Codex 很难从 Repository 自己得到的信息：

```text
这个字段真的需要修正吗？

这个差异是否会阻止提交？

最终哪一个值进入真实报税表？

这种情况在业务里意味着什么？
```

也就是说，他们提供：

```text
domain-grounded feedback
```

而不是：

```text
implementation instruction
```

这使生产反馈和普通 Bug Report 不一样。

一个工程师可以看到：

```text
prediction = 120
final = 180
```

但从业者才更容易判断：

```text
为什么 180 才是当前工作流里的正确结果。
```

所以：

```text
Practitioner
```

主要定义的是：

```text
business reality
```

与：

```text
product usefulness
```

之间的接口。

---

#### Codex 控制的是 Engineering Search

Codex 获得的自由度则发生在另外一层。

一旦：

```text
Finding
```

已经成立，并被包装成：

```text
Targeted Eval
+
Evidence
+
Scoped Task Environment
```

Codex 可以自己决定：

```text
先调查哪条 Trace

先看 Schema 还是 Mapper

建立什么 Root-Cause Hypothesis

修改哪个文件

运行多少轮 Targeted Eval

是否需要回退第一次尝试

怎样形成 Candidate Patch
```

这些属于：

```text
Search Policy
```

OpenAI 并没有要求工程师逐步告诉它：

```text
Step 1 Read A

Step 2 Change B

Step 3 Run C
```

否则 Codex 只是一个自动补全执行器。

这里真正自动化的是：

```text
bounded engineering search
```

即：

\[
\text{Finding}
\rightarrow
\text{Candidate Fix}
\]

中间大量探索步骤由 Agent 完成。

这就是 Tax AI 所谓自主改进中最主要的 Agentic 部分。

---

#### Engineer 保留的是 Architecture 与 Commit Boundary

工程师控制的则是更上层的两个接口。

一个是：

```text
architecture / product decisions
```

另一个是：

```text
shipping
```

也就是说，即使 Codex 得到：

```text
Targeted Eval PASS
Regression PASS
```

它仍然只生成：

```text
candidate PR
```

而不是：

```text
production deploy
```

所以：

```text
Engineering Search
```

和：

```text
Production Commit
```

仍然被分开。

可以类比成版本控制：

```text
Codex
拥有 working tree / branch

Engineer
拥有 merge / deploy boundary
```

这不是说工程师必须永远逐行检查所有修改。

未来完全可以根据：

```text
风险等级
历史稳定性
Eval Coverage
Change Type
```

进一步自动化一些低风险 Merge。

但 OpenAI 公开的 Tax AI 案例并没有把这个权限交给 Codex，因此本文也不应把它写成：

```text
全自动部署系统。
```

---

#### 三种角色其实对应三种不同的“真”

把这三个角色进一步抽象，可以发现它们分别接近三类约束。

```text
Practitioner
────────────
业务上是真的吗？


Codex
────────────
工程上怎么改？


Engineer / Eval / Review
────────────
这个修改可以进入生产吗？
```

也可以画成：

```text
       Domain Truth
            │
            ▼
      Practitioner
            │
            ▼
          Finding
            │
            ▼
    Engineering Search
            │
            ▼
          Codex
            │
            ▼
     Candidate Change
            │
            ▼
    Validation / Review
            │
            ▼
        Engineer
            │
            ▼
        Production
```

这几个职责如果全部压到同一个 Agent：

```text
Agent 观察生产
    ↓
Agent 判断什么是错
    ↓
Agent 定义 Eval
    ↓
Agent 修改自己
    ↓
Agent 修改 Grader
    ↓
Agent 判断 Eval 通过
    ↓
Agent 批准自己
    ↓
Agent 部署自己
```

表面上自治程度更高。

但同时失去了多个独立约束。

尤其容易形成：

```text
错误理解目标
      ↓
按错误目标修改
      ↓
按错误目标验证
      ↓
自己确认成功
```

这个问题与前面 Verification 中讨论过的：

```text
Generator
+
Self-Evaluator
```

高度相似。

---

#### Self-Evolving 并不要求 Human 从 Loop 中消失

因此最好把两个概念分开：

```text
Automation Depth
```

与：

```text
Human Presence
```

并不是同一条轴。

例如：

```text
System A
每一步都需要人点击继续，
但 Agent 可以修改大量系统组件。

System B
可以连续运行数小时，
但只允许修改一个 Prompt。

System C
可以自主生成 Candidate PR，
但必须由人 Merge。
```

很难简单按：

```text
有人 / 没人
```

判断谁更“Self-Evolving”。

Tax AI 的特点更接近：

```text
Human changes role
```

而不是：

```text
Human disappears
```

传统产品迭代里，工程师可能亲自承担：

```text
收集问题
复现问题
定位问题
修改代码
写测试
运行回归
```

Self-Evolving Loop 把其中相当一部分工程搜索交给 Codex。

人的工作则更多集中在：

```text
业务判断
边界定义
架构
验收
上线
```

因此更准确的描述是：

```text
human effort moves upward in the control stack
```

而不是：

```text
human effort = 0
```

这也和 earned autonomy 的思路一致：一个系统可以逐渐扩大某些动作的自主范围，但不必一次性删除所有 Review Boundary。

### 6.3 从 Context Adaptation 到 RSI：修改对象决定“进化”发生在哪一层

到这里可以回头处理 Self-Evolving Agent 最容易混淆的定义问题。

以下几种系统都可能被描述成：

```text
“会从经验中变好”
```

但它们实际发生的变化完全不同。

```text
Agent 失败以后 Reflection 再试一次

Agent 把经验写进 Memory

Agent 修改自己的 Prompt

Agent 生成新的 Skill

Agent 修改 Tool / Workflow

Agent 修改 Harness Code

Agent 更新自己的模型参数

Agent 修改训练算法

Agent 修改 Evaluator

Agent 修改负责改进自己的 Optimizer
```

如果全部叫：

```text
Self-Evolution
```

讨论很快就会失去精度。

所以本文采用一个按 **Persistent Mutable Surface** 划分的工作分类。

它不是学术界统一定义，也不是 OpenAI 对 Tax AI 给出的分级标准，只是为了在后续文章里明确：

> **到底是哪一层状态在跨任务持续变化？**

---

#### Level 0：In-Episode Adaptation

最弱的一层是：

```text
同一次任务内
根据 Feedback 改变后续行为
```

例如：

```text
Tool failed
    ↓
read error
    ↓
change command
    ↓
retry
```

或者：

```text
pytest failed
    ↓
inspect traceback
    ↓
edit code
    ↓
rerun
```

这当然是一种适应。

但任务结束以后：

\[
S_{t+1}=S_t
\]

系统长期状态没有变化。

下一次相同任务仍然从原始状态开始。

因此本文把它叫：

```text
In-Episode Adaptation
```

而不把它作为持久 Self-Evolution 的充分条件。

---

#### Level 1：Persistent Artifact Evolution

再往上一层，任务产生的经验开始进入持久 Artifact。

例如：

```text
Memory

Prompt

Rule

Skill

Few-shot Example

Knowledge Artifact
```

运行一次任务以后：

\[
A_{t+1}\neq A_t
\]

其中：

```text
A
= persistent artifact
```

下一次任务启动时，会读取新的：

```text
A_{t+1}
```

所以过去经验开始真正改变未来初始状态。

例如：

```text
Failure
    ↓
总结经验
    ↓
更新 Skill
    ↓
Future Session
load updated Skill
```

这比单次 Reflection 多出的关键属性就是：

```text
persistence across episodes
```

目前大量：

```text
Memory Evolution
Prompt Optimization
Skill Evolution
```

都可以落在这一层讨论。

---

#### Level 2：Harness / Product Evolution

Tax AI 主要展示的是更大的 Mutable Surface。

系统不仅可以修改文本 Artifact，还可以修改：

```text
Extraction Schema

Source Selection

Mapper

Grader

Product Code

Eval Infrastructure
```

也就是：

```text
围绕模型运行的工程系统
```

发生持久变化。

可以写成：

\[
H_{t+1}\neq H_t
\]

其中：

```text
H
= Harness / Product Scaffold
```

而基础模型仍然可以保持：

\[
M_{t+1}=M_t
\]

这是一个很重要的状态。

因为系统能力确实可能明显变化：

```text
能处理更多字段

能识别更多 Source Pattern

能正确映射更多 Product Concept

更少需要人工修正
```

但这些提升并没有要求：

```text
重新训练 Foundation Model
```

Tax AI 的：

```text
Trace
→ Eval
→ Codex
→ Code Change
```

主要属于这一层。

---

#### Level 3：Parameter Evolution

再往下，修改对象进入模型参数：

\[
M_{t+1}\neq M_t
\]

例如：

```text
SFT

RL

Continual Training

Online / Periodic Parameter Update
```

生产轨迹可能被转成训练数据，再用于更新模型权重。

这和 Level 2 并不存在简单的：

```text
高级
>
低级
```

关系。

它们解决的问题不同。

参数级优化可能具有更好的：

```text
implicit generalization
```

也可能减少：

```text
Prompt / Skill
```

显式长度。

但同时带来：

```text
训练成本

数据治理

灾难性遗忘

版本管理

训练稳定性

更困难的 Attribution
```

而 Harness-level 修改往往：

```text
更容易观察

更容易 Diff

更容易回滚

更容易用局部 Eval 验证
```

所以实际系统完全可能同时使用：

```text
Parameter Evolution
+
Harness Evolution
```

而不是必须二选一。

本文的 Tax AI 主线只覆盖后者，不据此判断参数级路线是否更优。

---

#### Level 4：Recursive Improvement Surface

再往上，才逐渐接近 `rsi.md` 更关心的问题。

前面几个 Level 大多仍然假设：

```text
Optimizer
大体固定

Goal
大体固定

Evaluation Contract
至少存在外部约束
```

例如 Tax AI 中：

```text
Codex
```

负责优化：

```text
Tax AI Product
```

但负责定义：

```text
哪些 Finding 可以进入 Loop

哪些 Eval 表示成功

哪个 Candidate 可以 Deploy
```

的控制面并没有整体交给同一个被优化系统。

更强的递归情形则会继续扩大 Mutable Surface：

```text
Agent
    ↓ can modify
Prompt / Skill / Harness
    ↓ can modify
Optimizer
    ↓ can modify
Evaluation procedure
    ↓ can modify
future improvement process
```

也就是：

> **系统不只修改完成任务的方法，还开始修改“自己以后怎样进行改进”这一过程。**

如果把普通 Self-Evolution 写成：

\[
S_{t+1}
=
O(S_t,F_t)
\]

其中：

```text
O
= optimizer
```

那么前面的 Tax AI 讨论里，可以近似认为：

\[
O_{t+1}\approx O_t
\]

真正主要变化的是：

\[
S_t
\]

更强的 Recursive Self-Improvement 则允许：

\[
O_{t+1}\neq O_t
\]

甚至：

```text
Evaluator
Search Strategy
Architecture
Training Process
```

本身也进入修改空间。

这时系统面对的问题会明显变难。

---

#### Evaluator 一旦也能进化，外部参照会变得更重要

假设：

```text
System
```

和：

```text
Evaluator
```

一起变化：

\[
(S_t,E_t)
\rightarrow
(S_{t+1},E_{t+1})
\]

然后系统宣布：

\[
E_{t+1}(S_{t+1})
>
E_t(S_t)
\]

这个比较并不直接说明：

```text
系统真实能力提升了。
```

因为：

```text
评价函数本身也变了。
```

最极端的情况是：

```text
旧 Grader:
错误 → FAIL

新 Grader:
相同错误 → PASS
```

于是 Score 上升，但 Behavior 没变。

这就是为什么 Tax AI 虽然允许在：

```text
workflow noise 被错误计分
```

时修改 Grader，却仍然保留：

```text
Production Evidence

Practitioner Judgment

Regression

Engineering Review
```

这些外部锚点。

当 Mutable Surface 继续扩展到：

```text
Evaluator
Optimizer
Goal Selection
```

以后，如何保持这种外部参照会成为更困难的问题。

这也是本文不准备把：

```text
Harness-level Self-Evolution
```

直接叫成：

```text
强 RSI
```

的原因。

---

#### 用一张图把几个层级分开

于是整篇文章目前讨论的对象可以整理成：

```text
┌───────────────────────────────────────────┐
│ Level 0                                   │
│ In-Episode Adaptation                     │
│                                           │
│ Retry / Reflection / Tool Feedback        │
│                                           │
│ Persistent system state may not change    │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│ Level 1                                   │
│ Persistent Artifact Evolution             │
│                                           │
│ Memory / Prompt / Rule / Skill            │
│                                           │
│ Future sessions load changed artifacts    │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│ Level 2                                   │
│ Harness / Product Evolution               │
│                                           │
│ Tool / Workflow / Schema / Mapper         │
│ Grader / Code / Eval Infrastructure       │
│                                           │
│ Tax AI mainly lives here                  │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│ Level 3                                   │
│ Parameter Evolution                       │
│                                           │
│ SFT / RL / Continual Training             │
│                                           │
│ Model weights change                      │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│ Level 4                                   │
│ Recursive Improvement Surface             │
│                                           │
│ Optimizer / Evaluator / Architecture /    │
│ Improvement Process also become mutable   │
└───────────────────────────────────────────┘
```

这里的箭头只表示：

```text
Mutable Surface 逐渐扩大
```

不表示：

```text
Level 4 一定比 Level 2
在真实产品里更好。
```

一个领域 Agent 完全可能在 Level 2 已经获得大量可衡量收益，而更大的 Mutable Surface 反而增加：

```text
Validation Cost
Security Risk
Regression Surface
Attribution Difficulty
```

---

#### 还可以用三个问题快速判断“它到底进化了什么”

以后看到一篇：

```text
Self-Evolving Agent
```

论文或者系统，可以先不管作者使用什么名字，直接问三个问题。

第一个：

```text
What persists?
```

任务结束以后到底留下了什么变化：

```text
nothing
memory
prompt
skill
code
weights
optimizer
```

第二个：

```text
Who evaluates?
```

修改是否由：

```text
同一个 Agent 自评

固定 Eval

独立 Evaluator

External Environment

Human Expert
```

判断。

第三个：

```text
Who can commit?
```

候选修改最终怎样进入下一版本：

```text
automatic write

test gate

human review

deployment policy
```

这三个问题往往比：

```text
“它是不是 RSI？”
```

更容易得到可以比较的工程答案。

---

#### Tax AI 的位置因此很清楚

按照本文这套工作分类，Tax AI 可以概括成：

```text
Persistent:
yes

Main mutable surface:
Harness / Product

Production feedback:
yes

External evidence:
yes

Targeted eval:
yes

Regression:
yes

Human review:
yes

Parameter self-training:
not the focus described here

Optimizer self-modification:
not demonstrated

Fully autonomous deployment:
no
```

所以它展示的是：

> **一种由生产反馈驱动、以 Eval 为约束、由 Codex 修改 Harness/Product Surface、并保留人工控制边界的持久系统改进。**

这已经比：

```text
Reflection + Retry
```

强很多。

但仍然没有要求：

```text
系统自己定义终极目标

自己重写整个改进算法

自己批准新的评价标准

自己决定所有架构变化

自己部署下一代自己
```

这些更强的问题应该和 Gödel Machine、DGM 以及更广义 RSI 的讨论分开处理。

这也是为什么 `self-evolve/_index.md` 和后面的 `rsi.md` 最好承担不同职责：

```text
_index.md
─────────────────────────────
Production-driven
Self-Evolving Agent

重点：
Feedback
Trace
Eval
Harness
Verification
Bounded Autonomy


rsi.md
─────────────────────────────
Recursive Self-Improvement

重点：
Optimizer Self-Modification
Evaluator Evolution
Architecture Evolution
更强的递归修改问题
```

两者之间当然存在连续关系，但不是同一个工程问题。

---

#### 到这里，Self-Evolving 的边界可以再写准确一点

第 1 节给出的工作定义是：

> Self-Evolving Agent 是一种能够把运行过程中产生的反馈转化为持久系统修改，并通过独立评测决定这些修改是否进入后续版本的 Agent System。

经过第 2 到第 6 节以后，可以把里面几个隐含条件展开：

```text
Production Feedback
        ↓
不能直接当 Ground Truth

Structured Evidence
        ↓
必须保留 Trace / Provenance

Finding
        ↓
必须区分 Actionable / Noise / Unknown

Eval
        ↓
必须给修改一个明确目标

Mutable Surface
        ↓
必须知道 Optimizer 到底允许改什么

Candidate Change
        ↓
必须与原始 Evidence 隔离

Verification
        ↓
必须同时考虑 Target 与 Regression

Commit
        ↓
不等于 Search

Escalation
        ↓
是合法结果

No Change
        ↓
也是合法结果
```

于是 Self-Evolving Loop 更准确的结构已经不是：

```text
Fail
↓
Reflect
↓
Improve
```

而是：

```text
                  Production
                      │
                      ▼
                   Evidence
                      │
                      ▼
                    Review
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
     Actionable    Ambiguous     No Change
         │            │
         │            ▼
         │         Escalate
         │
         ▼
       Finding
         │
         ▼
     Targeted Eval
         │
         ▼
    Scoped Codex Task
         │
         ▼
      Candidate
         │
         ▼
       Validate
         │
   ┌─────┴─────┐
   │           │
 Targeted   Regression
   │           │
   └─────┬─────┘
         │
         ▼
       Review
      /      \
  Reject    Deploy
              │
              ▼
          Production
```

这里最重要的并不是：

```text
循环画成了一个圈。
```

而是圈里面每一条边都有不同的 Evidence 和 Authority。

如果这些边界被删掉，只留下：

```text
Agent
→ 修改自己
→ 评价自己
→ 再修改自己
```

架构看起来更加“递归”，却很难回答：

```text
为什么这次修改发生？

它解决的是哪个真实 Failure？

依据是什么？

什么东西没有被修改？

谁证明它更好？

失败以后怎么回滚？

谁允许它进入生产？
```

Tax AI 的案例之所以适合作为 Self-Evolving Agent 的工程起点，正是因为它没有试图一次解决所有这些更强的问题。

它先固定：

```text
真实生产工作
专家反馈
Evidence
Eval
Review Boundary
```

然后把中间原本高度人工的：

```text
调查
定位
修改
验证
```

逐步交给 Codex。

这样得到的不是一个“自己决定一切”的 Agent，而是一个：

```text
在明确控制面内部
能够持续改进自身产品行为的系统。
```

下一节还需要回答最后一个问题。

即使这样一套闭环已经跑通，也不能从一个：

```text
fair_rental_days
```

成功案例直接推出：

```text
所有 Tax Workflow 都会自动越来越好
```

更不能推出：

```text
同样的 Loop
迁移到任意行业都会工作。
```

OpenAI 自己给出的 Rental Property 结果包含一个很具体的限制：这个场景大约花了六周，并需要大量工程监督，才达到 90% Precision 和 Recall。

真正可以继续复用的，不只是最后那个 Mapper Patch。

更有价值的是这六周留下来的：

```text
review artifacts
eval conventions
reusable abstractions
implementation patterns
```

所以最后需要区分：

```text
一个 Fix 能不能迁移
```

和：

```text
产生 Fix 的 Evolution Infrastructure
能不能迁移。
```

## 7. 什么能够扩展，什么不能

到这里，Tax AI 的 Self-Evolving Loop 已经可以完整画出来：

```text
Production
    ↓
Expert Correction
    ↓
Structured Trace
    ↓
Reviewed Finding
    ↓
Targeted Eval
    ↓
Scoped Codex Task
    ↓
Candidate Modification
    ↓
Targeted Eval + Regression
    ↓
Engineering Review
    ↓
Deploy
    ↓
Production
```

这种结构很容易让人继续向前推一步：

```text
既然一个 Failure
可以自动变成 Eval，

一个 Eval
可以交给 Codex 自动修，

那是不是只要让系统持续运行，
Tax AI 就会自动覆盖越来越多税务场景？
```

OpenAI 给出的 Rental Property 经验并不支持这么强的结论。

他们明确写到，将 Tax AI 扩展到复杂的 Rental Property 工作，大约用了 **六周**，并投入了大量工程监督，才把该能力推进到大约 **90% precision 和 recall**。

这里要和第 1 节的另一组“六周”数据分开。

第 1 节讨论的是整个 Tax AI 产品在上线初期：

```text
达到至少
75% correct field completion
的报税表占比

≈ 25%
    ↓
≈ 86%

within six weeks
```

而这一节讨论的是另一段产品扩展工作：

```text
Rental Property support

≈ six weeks
+
substantial engineering oversight
    ↓
≈ 90% precision / recall
```

OpenAI 并没有说这两个指标来自同一组实验，也没有给出可以把它们直接换算的关系。

前者回答：

```text
有多少份 Return
达到某个字段完成率阈值？
```

后者回答的则是：

```text
Rental Property 这一能力
在相应任务上的 Precision / Recall
到了什么水平？
```

这一区分很重要，因为它揭示了 Self-Evolving Agent 的一个现实限制：

> **闭环跑通以后，改进依然需要时间、领域建模、Eval Construction、工程监督和产品判断。**

它并不会因为：

```text
Feedback → Eval → Codex
```

这条管线已经存在，就自动把所有后续领域问题变成低成本问题。

真正发生变化的是另一件事：当第一类复杂任务被解决以后，系统留下的不只有一个已经修好的 Feature，还留下了一套可以复用的 **Evolution Infrastructure**。

### 7.1 六周、90% Precision / Recall 与工程监督

Rental Property 比最早的 W-2、1099 场景复杂得多。

输入可能同时包含：

```text
手写备注

Email

Spreadsheet

多个 Property

历史材料

其他 Source Documents
```

系统需要完成的也不再只是：

```text
从一张标准表格中
读一个值
```

而是：

```text
组织 Source Package

识别哪些文件属于哪个 Property

抽取字段

保存 Provenance

维持 Property Identity

映射到 Tax Engine

区分真实 Failure 与 Workflow Noise
```

一个最终错误可能来自：

```text
Source Selection
Extraction
Schema
Identity Binding
Mapper
Grader
```

中的任意一层。

因此：

```text
“增加 Rental Property 支持”
```

实际上不是向 Prompt 里增加一句：

```text
Please also handle rental properties.
```

而是在扩张整个 Product Surface。

---

#### 六周本身并不是 Self-Evolution 的速度常数

OpenAI 给出的：

```text
about six weeks
```

只是这个具体扩展工作的经验数字。

不能因此推导：

```text
任何新领域能力
≈ 六周可以自动学会
```

因为实际成本取决于很多变量：

```text
任务复杂度

Source Distribution

已有产品抽象

可观测性

领域专家反馈质量

Eval Coverage

现有 Mapper / Schema

Codex 能访问的 Context

Regression Surface
```

如果一个领域没有：

```text
结构化反馈
```

第一步就可能卡住。

如果有反馈但没有：

```text
Trace
```

Root Cause Attribution 会变得困难。

如果已经能定位 Failure，却没有：

```text
可执行 Eval
```

Candidate Change 又无法可靠比较。

所以：

```text
Self-Evolving Infrastructure exists
```

并不等于：

```text
new capability is cheap
```

它更接近：

```text
以后处理新 Failure 时，
不再从零搭建
Feedback / Eval / Task / Verification
这整条管线。
```

---

#### “大量工程监督”不能从结果里删掉

如果只截取：

```text
90% precision and recall
```

很容易得到一个更吸引人的叙事：

```text
Codex 在六周里
自动把 Rental Property
优化到了 90%。
```

但 OpenAI 同一句描述里还保留了：

```text
substantial engineering oversight
```

这部分不能省略。

因为前面已经看到，工程师仍然负责：

```text
架构

产品边界

模糊 Case

Review

Shipping
```

随着能力扩展到更复杂的业务区域，工程监督还可能参与：

```text
重新设计 Schema

建立新的 Eval Convention

决定什么 Failure 属于产品责任

调整 Task Environment

识别哪些抽象值得复用
```

这意味着 Tax AI 的自动改进不是：

```text
Engineer
完全退出研发过程
```

而是：

```text
Engineer
不必手工完成
每一个局部 Investigation
和 Candidate Patch
```

两种描述差别很大。

---

#### Self-Evolving 的收益可以来自工程杠杆，而不是完全无人化

假设传统模式下，一个工程师处理十个类似 Failure，需要重复：

```text
收集 Case
复现
查日志
定位
改代码
写测试
跑回归
```

而新的 Harness 已经自动提供：

```text
Trace

Finding

Targeted Eval

Candidate Workspace

Eval Runner

Regression Suite
```

那么工程师可以把更多时间放在：

```text
哪个 Problem 值得解决？

当前抽象是否还能继续扩展？

这个 Patch 是否符合架构？

哪些重复 Fix 应该上升成新 Primitive？
```

因此所谓：

```text
Self-Improvement
```

的工程收益不必来自：

```text
human labor → 0
```

也可以来自：

```text
同样数量的工程师
能够监督更多并行改进任务
```

这和 OpenAI 报告的业务效果也能对上。

文章给出一个具体案例：一名高级会计师表示，他上一年大约花了 **180 小时**进行报税准备，而采用新的工作流后这一数字降到约 **15 小时**，释放出的时间被转移到客户服务和新增业务。

这个数字是单个从业者的案例，不应该外推成整个 Crete 网络的平均节省比例。

它能说明的是：

```text
系统最终追求的
不是 Eval Score 本身，

而是把人从大量
可自动化准备工作中移开。
```

前面所有：

```text
Trace
Finding
Eval
Harness
Regression
```

最终都要回到这种生产结果上。

### 7.2 真正可复用的是 Evolution Infrastructure

Rental Property 支持完成以后，OpenAI 特别强调的并不只是：

```text
现在 Tax AI 会处理 Schedule E 了。
```

这次工作还留下了一批可复用资产：

```text
reusable abstractions

review artifacts

eval conventions

implementation patterns
```

这些资产随后让类似复杂度的：

```text
Schedule C

Schedule A
```

支持更容易建立。

这里有一个很重要的区别：

```text
Feature Transfer
```

和：

```text
Evolution Infrastructure Reuse
```

不是同一件事。

---

#### Rental Property 的 Mapper Patch 不一定能直接复用

假设 Rental Property 最终修复了：

```text
fair_rental_days
```

相关 Mapping。

这个 Patch 对：

```text
Schedule C business expenses
```

可能完全没有直接帮助。

因为两个领域：

```text
字段不同

Source 不同

Tax Semantics 不同

Mapping 不同
```

所以不能说：

```text
修好了 Schedule E
    ↓
Schedule C 自然获得相同能力
```

这是一种错误的能力迁移推断。

---

#### 但 Review Artifact 可以复用

前面已经形成了一种处理生产差异的方法：

```text
predicted

expected

trace

source

actionable?
```

这个 Review 结构并不只服务：

```text
fair_rental_days
```

换到 Schedule C，仍然需要回答：

```text
这个差异是真的吗？

是 Product Failure
还是 Workflow Noise？

Evidence 在哪里？

值得进入自动化 Loop 吗？
```

所以：

```text
Review Infrastructure
```

可以跨 Feature 使用。

---

#### Eval Convention 也可以复用

Rental Property 工作还解决了：

```text
生产 Failure
怎样变成 Targeted Eval？
```

以及：

```text
Targeted Eval
怎样和 Regression 分开？
```

当进入 Schedule C 时，不需要再次发明：

```text
什么叫 Dataset

什么叫 Suite

什么叫 Grader

怎么运行 Eval

怎样保存结果
```

领域 Case 会变化，但 Eval Infrastructure 可以保留。

于是：

```text
new domain
```

需要补充的是：

```text
new examples
new expectations
new graders / rules where necessary
```

而不是重新构建整个：

```text
Evaluation Runtime
```

---

#### Implementation Pattern 也可能逐渐上升成 Product Primitive

还有一种更强的复用。

第一次实现 Rental Property 时，工程师可能发现多个 Failure 都来自：

```text
Source Documents
需要稳定绑定到一个实体
```

于是最初针对：

```text
Property Identity
```

做出的设计，之后可能被抽象成：

```text
Entity-aware Source Mapping
```

这种 Primitive。

那么后续遇到：

```text
多个 Business

多个 Account

多个 Asset
```

时，就不必重新解决完全相同的 Identity Problem。

这说明 Self-Evolving Loop 长期积累的不应该只是：

```text
patch_001
patch_002
patch_003
```

还应该逐渐暴露：

```text
哪些 Patch
实际上属于同一种结构问题？
```

然后由工程设计把它提升成：

```text
reusable abstraction
```

这一步目前仍然明显需要工程判断。

Codex 可以提供候选重构，但：

```text
一个局部 Fix
什么时候应该上升成架构 Primitive？
```

并不能只靠：

```text
Targeted Eval PASS
```

决定。

---

#### 从 Patch Accumulation 到 Abstraction Accumulation

如果系统只不断添加局部 Patch：

```text
Failure A
→ Rule A

Failure B
→ Rule B

Failure C
→ Rule C
```

长期会得到：

```text
越来越复杂的 Prompt

越来越多 Special Cases

越来越长的 Mapper

越来越难理解的 Grader
```

这是一种：

```text
Patch Accumulation
```

但它并不一定等于：

```text
Capability Scaling
```

另一种更健康的路径是：

```text
Failure A ─┐
Failure B ─┼─→ Common Structure
Failure C ─┘
                 ↓
        Reusable Abstraction
                 ↓
      Future Failure Search Space
              becomes smaller
```

也就是：

```text
Patch Accumulation
        ↓
Pattern Recognition
        ↓
Abstraction Accumulation
```

OpenAI 提到 Rental Property 工作产生了：

```text
reusable abstractions
```

正好说明这一步已经发生在真实工程中。

但文章没有公开这些抽象的具体实现，因此不能进一步假设：

```text
到底新增了哪个类
哪个 Framework
哪种算法
```

---

#### 真正可扩展的是“解决问题的方法”

因此，Tax AI 从 Schedule E 向 Schedule C / A 扩展时，更准确的说法不是：

```text
系统学会一个任务以后，
能力自动泛化到其他任务。
```

而是：

```text
前一个任务建设的
Review / Eval / Harness /
Implementation Conventions

降低了后续任务
建立改进闭环的成本。
```

也就是说，迁移的主要是：

```text
how to improve
```

的一部分基础设施，

而不是：

```text
the solved behavior itself
```

全部直接迁移。

这也是 Harness-level Self-Evolution 和模型参数学习之间一个有意思的区别。

参数学习通常希望：

```text
能力被隐式编码进 weights
```

然后在新输入上产生 Generalization。

Harness Evolution 则可能把经验显式编码成：

```text
Schema

Skill

Eval

Tool

Code

Architecture Pattern
```

它们的 Generalization 更容易观察：

```text
这个抽象
到底被哪个新 Feature 复用了？
```

但也更依赖工程设计。

### 7.3 Self-Evolving Loop 最后卡在 Signal、Attribution 和 Verification

回看整篇文章，可以把大量具体组件压到三个瓶颈上。

```text
Signal

Attribution

Verification
```

它们分别对应：

```text
我们有没有足够好的反馈？

我们知不知道哪里出了问题？

我们能不能证明修改真的更好？
```

---

#### Signal：系统运行以后，会不会留下有价值的反馈

第一层问题是：

```text
Real Work
    ↓
能不能产生
Machine-usable Evidence？
```

Tax AI 的条件相对好。

从业者本来就会：

```text
review

correct

approve

submit
```

所以系统可以把已有业务动作结构化保存。

最终能够得到：

```text
Tax AI Prediction

Practitioner Correction

Final Filed Value
```

如果换一个领域，可能根本没有这么清楚的反馈。

例如一个 Research Agent 输出：

```text
一份未来趋势判断
```

真正结果可能半年以后才知道。

一个 Creative Agent 输出：

```text
广告创意
```

用户喜欢或不喜欢也很难直接映射成：

```text
哪个中间步骤错误
```

一个 Coding Agent 则往往拥有更强 Signal：

```text
compiler

test

CI

runtime

benchmark
```

所以不同 Agent Domain 的 Self-Evolution 难度可能在第一步就不同。

可以记成：

```text
Strong External Signal
        ↓
更容易构建 Eval


Weak / Delayed / Ambiguous Signal
        ↓
更难构建稳定 Evolution Loop
```

---

#### Feedback Quantity 不能替代 Feedback Quality

假设每天得到：

\[
10^6
\]

条用户行为记录。

如果系统不知道：

```text
哪些动作表示 Error

哪些表示 Preference

哪些只是 Workflow
```

那么：

```text
数据量很大
```

仍然不等于：

```text
学习信号很强
```

甚至可能出现：

```text
更多 Raw Feedback
        ↓
更多错误 Finding
        ↓
更多错误 Eval
        ↓
Optimizer 更快地向错误目标收敛
```

所以 Self-Evolving 系统需要优化的不是单纯：

```text
feedback volume
```

而是：

```text
usable signal density
```

Tax AI 中：

```text
structured correction
+
trace
+
provenance
+
review
```

共同提高的就是这件事。

---

#### Attribution：知道错了，还要知道哪里错了

有了 Signal 后，第二个瓶颈是：

```text
Root Cause Attribution
```

假设最终字段错误：

```text
expected = 180
predicted = missing
```

如果系统只能看到：

```text
Input
Output
```

候选 Root Cause 可能覆盖整个 Pipeline：

```text
Source Selection

Classification

Extraction

Schema

Mapper

Tax Engine Integration

Grader
```

而 Trace 把这个空间逐层压缩。

因此：

```text
Observability
```

并不只是运维功能。

对于 Self-Evolving Agent，它直接影响：

```text
Optimizer Search Space
```

可以继续使用前面的关系：

\[
\text{Failure}
+
\text{Trace}
\rightarrow
\mathcal{C}
\]

其中：

```text
C
= candidate cause set
```

Trace 越能保留关键中间状态：

```text
|C|
```

通常越容易缩小。

但这也不是：

```text
日志越多越好。
```

如果每一个 Token、每一个内部状态都保存下来：

```text
Storage Cost

Privacy Risk

Search Cost

Noise
```

也会增加。

真正需要保存的是：

```text
未来做 Attribution
所需的关键决策状态。
```

---

#### Verification：改动有效，还要证明没有把别处改坏

最后一个瓶颈是：

```text
Verification
```

即使 Signal 和 Attribution 都正确：

```text
Failure identified

Root Cause identified

Candidate Fix implemented
```

系统仍然可能：

```text
overfit targeted cases

break other workflows

change grader instead of behavior

introduce new safety problems
```

所以验证不能只有：

```text
same agent says:
looks good
```

Tax AI 至少加入：

```text
Targeted Eval

Regression Suite

Candidate PR

Engineering Review
```

从而把：

```text
Generate Fix
```

和：

```text
Accept Fix
```

分离。

---

#### 三个瓶颈缺一不可

把三者放在一起：

```text
Signal
────────────
发现什么值得学习


Attribution
────────────
决定应该改哪里


Verification
────────────
决定这个修改能不能留下
```

如果没有 Signal：

```text
系统不知道
应该优化什么。
```

如果没有 Attribution：

```text
系统知道错了，
却只能在巨大的 Mutable Surface
里盲目搜索。
```

如果没有 Verification：

```text
系统可以不停产生 Change，
却不知道 Change
是不是 Improvement。
```

所以可以把 Self-Evolving 的有效更新粗略写成：

\[
\text{Useful Evolution}
\propto
f(
\text{Signal},
\text{Attribution},
\text{Verification}
)
\]

这个式子不是定量模型，只是本文用于记忆三个条件的表达。

并不存在已知关系可以支持：

```text
三者乘起来
```

或者给出具体系数。

真正需要记住的只是：

```text
任一环节持续失效，
整个闭环都可能失去可信度。
```

---

#### 这三个问题也对应三类基础设施

Tax AI 中的实现可以重新映射一次：

| 瓶颈 | 对应基础设施 |
|---|---|
| Signal | Practitioner Correction、Final Filing、Production Evidence |
| Attribution | Trace、Provenance、Field-level Review、Scoped Context |
| Verification | Targeted Eval、Regression、Grader、Engineering Review |

这样看以后，前面一些容易被认为是“辅助组件”的东西就不再只是附属功能。

例如：

```text
Trace
```

不是方便 Debug 的日志。

它是 Attribution Infrastructure。

```text
Eval
```

不是为了最后给 Benchmark 一个数字。

它是 Modification Gate。

```text
Human Review
```

也不只是因为 Codex 还“不够聪明”。

它承担的是当前系统尚未可靠编码的一部分：

```text
semantic judgment
+
commit authority
```

### 7.4 一个最小 Self-Evolving Blueprint

如果把 Tax AI 的领域细节全部拿掉，最后可以留下一个更通用的 Blueprint。

第一层是：

```text
Real Work
```

系统必须先真正运行。

如果没有真实任务：

```text
Self-Evolution
```

只能依赖预先构造的数据集。

生产任务随后产生：

```text
System Output
+
Environment Response
+
Human Action
+
Final Outcome
```

其中一部分可以形成 Feedback。

---

第二层：

```text
Structured Evidence
```

不能只保存：

```text
success / failure
```

还要尽量保存足以解释失败的：

```text
Input

Intermediate Trace

Tool Results

Provenance

System Version

Human Correction

Final Outcome
```

具体需要哪些字段取决于领域。

---

第三层：

```text
Review
```

原始差异首先被分类成：

```text
Actionable Failure

Expected Noise

Ambiguous

Out of Scope
```

只有第一类继续进入自动改进。

---

第四层：

```text
Finding
```

多个相关 Failure 被归并成：

```text
一个稳定、
能够用自然语言描述的
产品问题。
```

例如：

```text
在包含多个 Rental Properties
的 Source Package 中，
Property Identity 经常混淆。
```

---

第五层：

```text
Eval
```

Finding 被编译成：

```text
Representative Inputs

Expected Outputs

Grader

Metric

Acceptance Condition
```

于是：

```text
“问题存在”
```

变成：

```text
“下一版本怎样才算更好”
```

---

第六层：

```text
Task Environment
```

Optimizer 获得：

```text
Finding

Read-only Evidence

Writable Workspace

Mutable Surface

Targeted Eval

Regression

Skills

Docs
```

而不是一个无限制生产环境。

---

第七层：

```text
Search / Modification
```

Agent 在明确边界中：

```text
investigate

form hypothesis

edit

run

inspect

iterate
```

得到：

```text
Candidate System
```

---

第八层：

```text
Verification
```

至少分成：

```text
Targeted Eval
```

和：

```text
Regression
```

前者问：

```text
这个问题修了吗？
```

后者问：

```text
别的问题坏了吗？
```

---

第九层：

```text
Commit Decision
```

Candidate 不等于 Production。

必须经过当前系统定义的：

```text
Review
Policy
Approval
```

才能产生：

\[
S_{t+1}
\]

否则：

\[
S_{t+1}=S_t
\]

同样是合法结果。

---

把这些步骤压成一张图：

```text
┌─────────────────────────────────────┐
│              Real Work              │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│         Human / Environment         │
│              Feedback               │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│        Structured Evidence          │
│                                     │
│ Trace / Provenance / Final Outcome  │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│               Review                │
└──────────────────┬──────────────────┘
                   │
        ┌──────────┼───────────┐
        │          │           │
        ▼          ▼           ▼
  Actionable   Ambiguous    No Change
        │          │
        │          └────→ Escalate
        ▼
┌─────────────────────────────────────┐
│              Finding                │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│          Targeted Eval              │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│          Scoped Agent Task          │
│                                     │
│ Evidence        read-only           │
│ Workspace       writable            │
│ Skills / Docs   bounded context     │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│      Agent Investigation / Edit     │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│          Candidate System           │
└──────────────────┬──────────────────┘
                   │
          ┌────────┴────────┐
          │                 │
          ▼                 ▼
┌─────────────────┐ ┌─────────────────┐
│ Targeted Eval   │ │ Regression Eval │
└────────┬────────┘ └────────┬────────┘
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│            Human / Policy           │
│                Review               │
└──────────────────┬──────────────────┘
                   │
          ┌────────┴────────┐
          │                 │
          ▼                 ▼
       Reject             Deploy
          │                 │
          │                 ▼
          │       ┌─────────────────────┐
          └──────→│      Production     │
                  │       S_{t+1}       │
                  └──────────┬──────────┘
                             │
                             └──────→ new evidence
```

如果要把整篇文章进一步压成一句工程检查，而不是重新给 Self-Evolving 发明一个大词，可以使用下面这组问题：

```text
1. Signal
生产运行以后，
什么 Feedback 会被留下？


2. Evidence
这个 Feedback
是否保存了足够的 Trace 和 Provenance？


3. Review
谁判断它是真 Failure、
Noise 还是 Unknown？


4. Finding
多个事件怎样被压成
一个稳定问题？


5. Eval
怎样把问题转成
可执行的成功条件？


6. Mutable Surface
Optimizer 到底允许修改什么？


7. Isolation
哪些 Evidence 必须只读？


8. Verification
谁检查 Target Improvement
和 Regression？


9. Commit
谁允许 Candidate
进入下一版本？


10. Persistence
这次学习结果
下一个任务真的会继承吗？
```

如果其中最后一个问题的答案是：

```text
不会
```

那么系统更接近一次任务内的：

```text
adaptation
```

如果：

```text
Prompt / Skill / Memory
```

跨任务发生变化，它进入 Persistent Artifact Evolution。

如果：

```text
Schema / Tool / Workflow / Code / Eval
```

也可以根据生产 Failure 持续变化，就更接近 Tax AI 展示的 Harness / Product Evolution。

如果进一步：

```text
Model Parameters

Optimizer

Evaluator

Improvement Procedure
```

本身也逐渐进入 Mutable Surface，那么问题开始进入 `rsi.md` 需要单独讨论的范围。

---

OpenAI 在文章结尾提到，他们已经开始把这套 Blueprint 应用到：

```text
bookkeeping

audit

IT help desk
```

这些领域与税务工作显然不同，因此目前不能从 Tax AI 的公开结果推出：

```text
这些领域已经达到相同效果
```

能够转移的是方法：

```text
贴近真实使用者

让生产系统产生 Evidence

把重复 Failure 变成 Eval

把 Eval 包装成有边界的 Agent Task

用外部验证约束 Candidate Change
```

至于一个新领域能否真正建立同样的循环，仍然要重新回答：

```text
Signal 是否存在？

Attribution 是否可行？

Verification 是否足够可靠？
```

Tax AI 给出的答案只是说明：

```text
在一个拥有高质量专家反馈、
可追踪业务状态和明确结果的领域里，
这条工程路径已经能够运行。
```

它没有证明所有 Agent 都会沿着同一条路径自动获得持续能力增长。

这也是本文把 Self-Evolving 放在 Harness 之后理解的原因。

模型负责：

```text
在当前状态下
提出下一步动作。
```

Harness 负责：

```text
让这些动作能够
持续、受控、可观察、可验证地执行。
```

而 Self-Evolving Loop 再向外增加一层：

```text
让系统过去的生产失败
能够改变未来任务
开始时所处的系统状态。
```

可以最后写成：

\[
\boxed{
\text{Experience}
\rightarrow
\text{Evidence}
\rightarrow
\text{Eval}
\rightarrow
\text{System Change}
\rightarrow
\text{Verification}
\rightarrow
\text{Persistent Experience}
}
\]

这个式子仍然不是 Self-Evolving Agent 的标准定义。

真正需要保留的是里面的约束：**Experience 不能直接当 Ground Truth，Change 不能直接当 Improvement，而 Improvement 也不能只由提出 Change 的同一个 Optimizer 自己宣布。**

---

**参考资料**

- [OpenAI, *用 Codex 构建可自我改进的税务智能体*, 2026-05-27](https://openai.com/zh-Hans-CN/index/building-self-improving-tax-agents-with-codex/)

> 后续草稿里那些 SkillX / SkillClaw / Trace2Skill / SkillForge / Meta-Harness / AHE / TextGrad / APO 等材料就不适合继续硬塞进这篇主线了。更合理的是从这里向下拆子文档：一类专门讲 Prompt / Skill Evolution，一类讲 Harness Optimization；现有 rsi.md 则继续保留给参数、Optimizer、Evaluator 和递归修改这一更强层级。