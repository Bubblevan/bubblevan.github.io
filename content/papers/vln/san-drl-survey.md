---
title: "SOCIALLY AWARE NAVIGATION FOR MOBILE ROBOTS: A SURVEY ON DEEP REINFORCEMENT LEARNING APPROACHES"
---

社会感知导航是用于指代这一领域的少数术语之一。通常情况下，除非作者明确说明，否则这些术语的含义都是相同的。最常用的术语有“社会感知导航”“人类感知导航”“人群感知导航”和“社交导航”。“社会感知导航”侧重于让机器人在人类环境中移动时遵守社会规范。“人类感知导航”侧重于在考虑人类社会规范的同时，理解、回应人类或一小群人并在其周围移动。“人群感知导航”涉及在大量人群中进行社交性导航（这些人群通常密集分布），同时还要理解他们的集体行为。“社交导航”是一个更宽泛的术语，可能包含上述所有内容，涉及机器人在社交环境或社交规范中的所有导航方面。这些社会规范或行为举止通常是支配人类互动的微妙规则或行为，例如保持适当距离（空间关系学）、避免穿过正在交谈的人群、预测人类的移动以及对人类的手势和暗示做出反应。


![Principles for social robot navigation [2].](/paper/san-drl-survey-principles.png)
> 来自 A. Francis et al., ‘Principles and Guidelines for Evaluating Social Robot Navigation Algorithms’, ACM Trans. Hum.-Robot Interact., vol. 14, no. 2, pp. 1–65, June 2025, doi: 10.1145/3700599.

正如文献[2]所提出的，其中一些规则和考量因素包括：安全性、舒适性、易懂性、礼貌性、社交能力、智能体理解能力、主动性和情境适宜性。

![](/paper/san-drl-survey-overview.png)

## LEARNING IN SOCIALLY AWARE NAVIGATION

**SAN** 的方法源于 20 世纪 90 年代末博物馆导游机器人（德国 **RHINO**、美国 **MINERVA**）的早期尝试，核心是让机器人在人类环境中遵循**社交规范**，按文献 [15] 分为**反应式**、**主动式**、**基于学习的方法**三类，核心差异在于是否具备"**预测能力**"和"**学习能力**"：

### Approaches in SAN

#### 反应式方法（纯规则驱动，无预测/学习）

**核心逻辑**：仅对环境中移动智能体（人/其他机器人）做出即时反应，依赖预设规则，不预测未来行为、不积累经验。

**代表技术**：

- **社会力模型**：用"**吸引力**（向目标）""**排斥力**（避障碍）"描述运动，是早期基础方法
- **速度障碍法**：传统导航常用，适配 **SAN** 场景
- **互惠速度障碍法**：假设智能体独立导航、避撞行为一致，但无法处理静态障碍和复杂人际交互
- **最优互惠避撞（ORCA）**：支持多机器人无通信安全导航，但在智能体匀速运动时性能显著下降

**关键局限**：拥挤环境中难以捕捉复杂人际交互，适应性差。

#### 主动式方法（轨迹预测驱动，主动规划）

**核心逻辑**：假设人类会协作导航（非对抗性），又称"**轨迹基方法**"——通过大规模数据集构建"**运动预测模型**"，预测人类轨迹后规划路径。

**代表技术**：

- **交互高斯过程（IGP）**：预测机器人与人群未来状态，建模**社交合规导航**，但需平衡"**路径最优性**"和"**计算复杂度**"
- **蒙特卡洛树搜索（MCTS）+Y-net**：模拟未来状态、评估局部目标质量，提升拥挤区域导航决策

**关键优势**：主动考虑人类行为，交互更平滑，更符合**社交规范**。

#### 基于学习的方法（近年主流，从数据/交互中学习）

**核心逻辑**：依赖**深度学习**、**深度强化学习（DRL）**、**逆强化学习**或**模仿学习**，从数据/环境交互中学习**社交导航策略**，是当前研究重点。

**核心技术与应用**：

- **DRL**：主流方向，文献 [25] 是早期将**社交感知**融入避撞的代表性研究；常用网络架构包括 **LSTM**（编码人群集体影响）、**自注意力机制**（**SARL**，建模机器人-人群交互）、**图卷积神经网络（GCN）**、**时空 Transformer**
- **模仿学习**：如**生成对抗模仿学习（GAIL）**，结合视觉输入获取**社交导航模型**，也可与**强化学习**结合用于单目标导航

**关键优势**：能适配动态、复杂的社交环境，自主学习**社交规范**，灵活性最强。

### Benefits and Evolution of DRL for SAN

#### 传统方法的致命缺陷

- 把人类当"**静态障碍物**"，没法实时适应人的动态行为（比如人突然转身、停下交谈）
- 依赖固定模型（如**社会力模型**、**ORCA**），这些模型是"**死规则**"，应付不了复杂多变的社交场景（比如不同人对"**安全距离**"的接受度不同）

#### DRL 的突破

- 能从与环境的交互中"**自主学习**"导航策略，不用预设所有规则
- 能生成更"**类人**"的动作（比如缓慢避让、排队等待），更贴合**社交规范**（如**近距学**、**礼貌性**）

#### RL 的演进历程

- **早期 RL**：只关注"**避障**"，不考虑社交
- **中期 RL**：开始融入**社交因素**（如保持安全距离、协作避让）
- **现在 DRL**：因为能处理高维数据（如摄像头、激光雷达的输入），更容易制定兼顾"**导航效率**"和"**社交合规**"的策略，最新研究重点是设计更合理的"**奖励函数**"（比如让机器人知道"**避让行人**"比"**走捷径**"更重要）

#### Deep Reinforcement Learning

首先来一个 **MDP（Markov Decision Process）**，这个已经老生常谈了，用元组 $<S, A, P, R, \gamma>$ 描述，目标：找到**最优策略** $\pi^*$，让每个状态下的动作都能最大化"**预期总奖励**"。

以 **Q-Learning** 举例：

**算法流程**：

```python
Input: the policy π
Initialization: Q(s,a)  # 先给所有Q(s,a)赋随机值（比如全0），相当于机器人刚开始啥也不懂
for each episode do:
    initialize s
    for each non-terminal state s in each episode do:
        a ← action for s derived by Q  # 根据当前Q值选动作（结合探索率ε，偶尔试新动作）
        select action a, observe r, s'  # 执行后观察到新状态s'和奖励r
        Q(s,a) ← Q(s,a) + α[r + γ·max Q(s',a') - Q(s,a)]  # 根据新体验修正之前的价值判断（α是学习率，控制修正幅度）
        s ← s'
    end for
end for
Output: action-value function Q  # 输出：学到的Q函数，机器人后续只需选每个状态下Q值最大的动作，就是最优策略
```

**核心更新公式**：

$$Q(s, a) \leftarrow Q(s, a) + \alpha[r + \gamma \max_{a'} Q(s', a') - Q(s, a)]$$

其中：
- $Q(s, a)$：状态-动作价值函数
- $\alpha$：**学习率**，控制修正幅度
- $r$：即时奖励
- $\gamma$：**折扣因子**
- $\max_{a'} Q(s', a')$：下一状态的最大 Q 值
- $\epsilon$：**探索率**，用于平衡探索与利用

#### Value-Based RL
**基于价值的深度强化学习（Value-based DRL）**，简单说：给"机器人当前状态 + 每个可能动作"打个"**价值分**"，机器人永远选分最高的动作。

- **「价值」** = 做这个动作后，从当前状态到未来能拿到的"**总预期奖励**"（比如"当前在商场走廊 + 向左避让行人"的价值 = 10 分，"向前冲"的价值 = -100 分）
- 早期用「**Q 表**」（类似"状态-动作得分对照表"）存分数，复杂场景（比如社交导航的高维环境数据）改用「**神经网络**」（**价值网络**）替代 Q 表，这就是"基于价值的 DRL"
- **核心逻辑**：不用直接学"该选什么动作"，而是学"每个动作值多少分"，通过不断更新分数（用**贝尔曼方程** + **动态规划**），自然得到**最优策略**

#### 为什么它在社交感知导航中最常用？（核心优势）

- **决策稳定、安全合规**：直接给动作打分，机器人每次都选最高分动作，行为可预测、不"乱决策"——这对社交导航至关重要（比如在医院、商场，机器人必须稳定避让行人，不能突发怪异动作）
- **学习效率高、收敛快**：重点关注"动作的价值"，而非复杂的策略本身，在社交导航的复杂环境中能更快学到有效策略
- **适配简单场景 + 实体机器人**：
  - 适合"少智能体、少动作"的场景（比如室内稀疏行人，机器人只有"前后左右 + 等待"5 个动作）
  - 奖励稀疏场景（比如行人少、交互少）中计算成本低，不会占用太多机器人机载算力，适合现实部署
- **人类舒适度高**：动作离散且可预测（比如每次只选固定几个动作），人类能预判机器人行为（比如之前交互过知道它会向左避让），减少不安感

#### 局限：哪些场景用不了？

- **「环境越复杂越吃力」**：如果场景里行人多（多智能体）、机器人动作多（比如连续调整速度/转向角），"状态-动作"组合会爆炸式增长，计算量剧增，性能下降
- **「只能处理"离散动作"」**：比如机器人只能选"左转/右转"，不能选"左转 30 度/左转 45 度"这种连续动作，限制了运动的灵活性

#### 以 DQN 为例：用神经网络升级传统 Q 学习

**DQN（Deep Q-Network）** 的本质是「用**神经网络**升级传统 Q 学习」，用深度神经网络 $Q(s, a; \theta)$ 近似 Q 函数，其中 $\theta$ 是网络参数。

**算法原理**：

1. **价值函数近似**：用神经网络 $Q(s, a; \theta)$ 替代 Q 表，输入状态 $s$，输出所有动作的 Q 值
2. **经验回放（Experience Replay）**：将经验 $(s_t, a_t, r_t, s_{t+1})$ 存入**回放缓冲区** $\mathcal{D}$，训练时随机采样，打破数据相关性
3. **目标网络（Target Network）**：使用独立的**目标网络** $Q(s, a; \theta^-)$ 计算目标 Q 值，定期更新参数，稳定训练过程

**核心更新公式**：

$$Q(s, a; \theta) \leftarrow Q(s, a; \theta) + \alpha[r + \gamma \max_{a'} Q(s', a'; \theta^-) - Q(s, a; \theta)]$$

**DQN 算法伪代码**：

```python
# 初始化
Initialize replay buffer D with capacity N
Initialize Q-network Q(s, a; θ) with random weights θ
Initialize target network Q(s, a; θ⁻) with weights θ⁻ = θ
Initialize exploration rate ε = ε_start

for episode = 1 to M do:
    Initialize state s₁
    for t = 1 to T do:
        # ε-贪婪策略选择动作
        if random() < ε:
            a_t = random_action()  # 探索
        else:
            a_t = argmax_a Q(s_t, a; θ)  # 利用
        
        # 执行动作，观察奖励和下一状态
        Execute action a_t, observe reward r_t and next state s_{t+1}
        
        # 存储经验到回放缓冲区
        Store transition (s_t, a_t, r_t, s_{t+1}) in D
        
        # 从回放缓冲区采样小批量经验
        Sample random minibatch of transitions (s_j, a_j, r_j, s_{j+1}) from D
        
        # 计算目标 Q 值
        if s_{j+1} is terminal:
            y_j = r_j
        else:
            y_j = r_j + γ · max_{a'} Q(s_{j+1}, a'; θ⁻)  # 使用目标网络
        
        # 更新 Q 网络参数（最小化损失函数）
        Loss = (y_j - Q(s_j, a_j; θ))²
        Perform gradient descent step on Loss with respect to θ
        
        # 定期更新目标网络
        if t mod C == 0:
            θ⁻ = θ  # 复制主网络参数到目标网络
        
        # 更新状态
        s_t = s_{t+1}
        
        # 衰减探索率
        ε = max(ε_min, ε · ε_decay)
    end for
end for
```

**关键优势**：
- **计算高效**：一次网络计算就能算出所有动作的分数，不用逐个查 Q 表
- **经验回放**：把之前的"状态-动作-奖励"存起来反复学习，避免重复犯错（比如之前撞到行人的经历会一直提醒机器人避让），同时打破数据的时间相关性，提高样本效率
- **目标网络**：使用独立的目标网络计算目标值，减少训练过程中的不稳定性

**局限与扩展**：
- **只能处理离散动作**（和所有价值基方法一样）
- **容易"过拟合"**（只记住最近的经验，比如刚避让过左边行人，就一直往左躲）
- **扩展版本**：
  - **加 LSTM 的 DQN**：能处理时序数据（比如预测行人下一步动作）
  - **SafeDQN**：针对安全关键场景（比如医院），加入"患者病情严重程度"模型，确保优先避让脆弱人群
  - **Double DQN**：解决 Q 值过估计问题
  - **Dueling DQN**：分离状态价值和优势函数，提高学习效率

Table 2. Comparative Analysis of Some Value-Based Approaches
| Reference 论文名                                                                                                                                                                                                 | 算法类型   | 网络类型   | 状态动作空间 | 机器人数量 | 测试框架 | Comfort | Naturalness（自然性） | Trajectory Prediction（轨迹预测） | Attention Mechanism（注意力机制） | Physical Input（物理输入） | Context Awareness（上下文感知） | Intention Prediction（意图预测） | Advanced Socialness（高级社交性） |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|------------|--------------|------------|----------|---------|-----------------------|----------------------------------|----------------------------------|---------------------------|----------------------------------|----------------------------------|----------------------------------|
| SRL-ORCA: A Socially Aware Multi-Agent Mapless Navigation Algorithm in Complex Dynamic Scenes                                                                                                                     | Q-learning  | FFNN       | CC           | 单机器人   | Sim      | √       | ×                     | √                                | ×                                | ×                         | ×                                | √                                | ×                                |
| Socially-Aware Multi-Agent Following with 2D Laser Scans via Deep Reinforcement Learning and Potential Field                                                                                                       | Q-learning  | FFNN       | CD           | 多机器人   | Sim      | √       | ×                     | ×                                | ×                                | √                         | ×                                | ×                                | ×                                |
| Learning a Group-Aware Policy for Robot Navigation                                                                                                                                                                | DQN        | CNN        | CD           | 多机器人   | Sim      | √       | ×                     | ×                                | √                                | √                         | ×                                | ×                                | ×                                |
| ST2: Spatial-Temporal State Transformer for Crowd-Aware Autonomous Navigation                                                                                                                                     | DQN        | Transformer| CD           | 单机器人   | Sim      | √       | √                     | √                                | ×                                | ×                         | ×                                | ×                                | ×                                |
| Transformable Gaussian Reward Function for Socially-Aware Navigation with Deep Reinforcement Learning                                                                                                               | DQN        | FFNN       | CD           | 单机器人   | Sim      | √       | ×                     | √                                | √                                | √                         | √                                | ×                                | ×                                |
| Robot Navigation in Crowds Environment Base Deep Reinforcement Learning with POMDP                                                                                                                                 | DQN        | LSTM       | CD           | 单机器人   | Sim      | √       | ×                     | ×                                | ×                                | √                         | ×                                | ×                                | ×                                |
| Memory-driven deep-reinforcement learning for autonomous robot navigation in partially observable environments                                                                                                       | Q-learning  | LSTM       | CD           | 单机器人   | Sim      | √       | ×                     | ×                                | ×                                | ×                         | √                                | ×                                | √                                |
| End-to-End Mobile Robot Navigation using a Residual Deep Reinforcement Learning in Dynamic Human Environments                                                                                                      | DQN        | CNN        | CD           | 单机器人   | Both     | √       | ×                     | ×                                | ×                                | √                         | ×                                | ×                                | ×                                |
| Socially Aware Hybrid Robot Navigation via Deep Reinforcement Learning                                                                                                                                              | DQN        | FFNN       | CD           | 单机器人   | Sim      | √       | ×                     | √                                | ×                                | ×                         | ×                                | ×                                | ×                                |
| Robot Navigation in Crowds by Graph Convolutional Networks With Attention Learned From Human Gaze                                                                                                                  | DQN        | GNN        | CD           | 单机器人   | Sim      | √       | √                     | √                                | ×                                | ×                         | ×                                | ×                                | ×                                |
| Social Navigation for Mobile Robots in the Emergency Department                                                                                                                                                     | DQN        | FFNN       | CC           | 单机器人   | Both     | √       | √                     | ×                                | ×                                | √                         | ×                                | ×                                | ×                                |
| Online Context Learning for Socially-compliant Navigation                                                                                                                                                           | DQN        | FFNN       | CD           | 单机器人   | Sim      | √       | ×                     | ×                                | ×                                | √                         | √                                | ×                                | ×                                |
| Learning Crowd Behaviors in Navigation with Attention-based Spatial-Temporal Graphs                                                                                                                                | DQN        | Transformer| CD           | 单机器人   | Sim      | √       | ×                     | √                                | ×                                | ×                         | ×                                | ×                                | ×                                |
| Risk-Aware Deep Reinforcement Learning for Robot Crowd Navigation                                                                                                                                                  | DQN        | CNN        | CC           | 单机器人   | Both     | √       | √                     | √                                | ×                                | ×                         | ×                                | ×                                | ×                                |
| Robot Navigation with Entity-Based Collision Avoidance using Deep Reinforcement Learning                                                                                                                            | DQN        | FFNN       | CD           | 单机器人   | Sim      | √       | ×                     | ×                                | √                                | √                         | ×                                | ×                                | ×                                |
| Navigating Robots in Dynamic Environment With Deep Reinforcement Learning                                                                                                                                           | DQN        | CNN        | CD           | 单机器人   | Both     | √       | ×                     | √                                | ×                                | ×                         | ×                                | √                                | √                                |
| SANG: Socially Aware Navigation Between Groups                                                                                                                                                                     | DQN        | Transformer| CD           | 单机器人   | Sim      | √       | √                     | √                                | ×                                | ×                         | √                                | ×                                | ×                                |
| Safety-Critical Deep Q-Network (SafeDQN)（对应Ref[46]：Social Navigation for Mobile Robots in the Emergency Department 修正：Ref[46]原文为A. M. Taylor等，标题Social Navigation for Mobile Robots in the Emergency Department） | DQN        | FFNN       | CC           | 单机器人   | Sim      | √       | ×                     | ×                                | ×                                | √                         | ×                                | ×                                | ×                                |
| Social Navigation with Human Empowerment Driven Deep Reinforcement Learning                                                                                                                                         | DQN        | CNN        | CD           | 单机器人   | Sim      | √       | √                     | ×                                | ×                                | ×                         | √                                | ×                                | ×                                |
| Interaction-Aware Crowd Navigation via Augmented Relational Graph Learning                                                                                                                                          | DQN        | Transformer| CD           | 单机器人   | Sim      | √       | √                     | √                                | ×                                | ×                         | √                                | ×                                | ×                                |
| Socially Compliant Robot Navigation in Crowded Environment by Human Behavior Resemblance Using Deep Reinforcement Learning                                                                                            | DQN        | GNN        | CD           | 单机器人   | Both     | √       | ×                     | √                                | ×                                | ×                         | √                                | ×                                | ×                                |
| RMRL: Robot Navigation in Crowd Environments With Risk Map-Based Deep Reinforcement Learning                                                                                                                       | DQN        | CNN        | CD           | 单机器人   | Sim      | √       | ×                     | ×                                | ×                                | √                         | ×                                | ×                                | ×                                |
| Safe and socially compliant robot navigation in crowds with fast-moving pedestrians via deep reinforcement learning                                                                                                  | Deep V-learning | FFNN    | CD           | 单机器人   | Both     | √       | ×                     | ×                                | ×                                | ×                         | ×                                | ×                                | √                                |
| Group-Aware Robot Navigation in Crowds Using Spatio-Temporal Graph Attention Network With Deep Reinforcement Learning                                                                                                | Q-learning  | GNN        | CD           | 单机器人   | Both     | √       | √                     | √                                | √                                | ×                         | ×                                | ×                                | ×                                |
| Heterogeneous Relational Deep Reinforcement Learning for Decentralized Multi-Robot Crowd Navigation                                                                                                                | DDQN       | GNN        | CC           | 单机器人   | Both     | √       | √                     | √                                | √                                | √                         | √                                | √                                | √                                |

#### Policy-Based RL
基于策略的强化学习（Policy-based RL）简单说：直接学习 “状态→动作” 的 “行动手册”（策略），不用先给动作打分（价值函数）
「策略」= 机器人的 “条件反射”：比如 “看到前方 3 米有行人（状态）→ 减速 50%+ 向左微调 15 度（动作）”，直接映射，不绕弯；
「表示方式」：复杂场景（社交导航）中，用神经网络替代简单规则，让策略能适配高维环境（比如激光雷达感知的人群分布）；
「和价值基方法的核心区别」：价值基是 “先打分再选动作”（比如 DQN 先算每个动作的价值分），策略基是 “直接选动作”，跳过 “打分” 步骤。
为什么它适合社交导航？（核心优势）
动作更灵活：支持 “连续动作空间”价值基方法（如 DQN）只能选 “左转 / 右转 / 前进” 这种离散动作，而策略基能处理 “左转 10 度 / 左转 25 度”“速度从 0.5m/s 提到 0.8m/s” 这种连续动作 —— 就像人类走路会微调步速和方向，机器人也能做 “精细操作”，不会出现突然急动（价值基的通病），在拥挤商场、地铁站等场景中更自然，能减少人类的不安感。
学习更稳定：适配人类行为的不可预测性社交导航中人类行为多变（比如突然停下交谈、变向），策略基算法（尤其是 PPO）能避免 “策略大幅跳跃”（比如之前还在避让，突然冲上去），学习过程平稳 —— 就像人类慢慢适应新环境，不会突然改变行为模式，保障人类安全与舒适。
适配复杂场景：处理多智能体和稀疏奖励面对密集人群（多智能体交互）、很少得到奖励（比如长时间没遇到行人，只有到达目标才获奖）的场景，策略基（如 PPO）能高效学习，泛化能力强（换个商场、车站也能用上）。
包括确定性策略梯度（DPG）、信任域策略优化（TRPO）、以及基于TRPO改进的近端策略优化算法（PPO）
PPO 是社交导航的 “明星算法”，计算效率更高 —— 在给策略 “加惩罚”（比如撞到行人就惩罚）以提升安全性时，不用复杂计算就能避免策略突变，学习又快又稳。
稳定可靠：人类行为不可预测，PPO 不会因环境变化导致学习崩溃；
泛化性强：换不同密度的人群、不同场景（商场 / 工地）都能适配；
多场景兼容：能同时学习 “策略” 和 “价值函数”（评论网络），也能融入安全约束（比如用拉格朗日方法确保不碰撞）；
TRPO 是 PPO 的前身（稳定但计算复杂），DPG 适合 “确定性动作”（比如固定速度避让），但在社交导航中应用不如 PPO 广泛。

#### Actor-Critic Algorithms

> 先缓一会，我大概这篇文章看完了，主要是描述网络与方法的应用，在描述Simulator里竟然没有描述Issac，但有一说一确实Issac是没有吧。
> 然后方法这一块放这里还是太难顶了，我打算额外放到CS285里然后引用过来。

