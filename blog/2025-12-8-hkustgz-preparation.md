---
slug: hkustgz-preparation
title: 港科广红鸟面试准备
authors: bubblevan
tags: []
---

# 红鸟面试准备

上面那则hk-master的文档有点太满了，所以放在这里。

## 群面

在流程方面，上午10:00开始：头脑风暴，A+B，B是五大主题，A由AI随机生成一个形容词。

### 1. 低空经济 (Low-altitude Economy)

#### eVTOL (电动垂直起降飞行器)

> **人话**："空中的士"或"放大版的大疆无人机（能坐人）"。不需要跑道，电动的，声音小，适合在城市楼顶起降。

#### 无人机物流

> **人话**："美团/顺丰空投"。外卖不走马路，走窗户。关键技术是航路规划（不撞楼）和末端投放（不砸人）。

#### 低空旅游

> **人话**：坐直升机/eVTOL看风景。

#### 农业植保无人机

> **人话**："农田洒水机"。大疆在这个领域很强，用无人机喷农药、播种，效率是人的几十倍。

### 2. 未来健康 (Future Health)

#### 脑机接口 (BCI)

> **人话**："意念控制"。在大脑植入芯片或戴个头盔，捕获脑电波，让瘫痪的人能控制鼠标或机械臂（像马斯克的Neuralink）。

#### AI辅助诊断

> **人话**："AI看片"。医生看CT要10分钟，AI看只要1秒，还能发现肉眼看不到的小结节。

#### 基因编辑 (CRISPR)

> **人话**："上帝的手术刀"。像编辑Word文档一样修改DNA，把致病的片段剪掉，换上好的。

#### 远程手术

> **人话**："5G隔空开刀"。医生在北京操作机械臂，给新疆的病人做手术，延迟极低。

#### 可穿戴监测

> **人话**：Apple Watch的医疗级进阶版。贴在皮肤上的柔性电路，能测汗液成分、血糖等。

### 3. 可持续生活 (Sustainable Living)

#### 零碳建筑

> **人话**："自给自足的房子"。房子本身发电（光伏）= 房子消耗的电。不给地球排二氧化碳。

#### 垂直农业

> **人话**："摩天大楼种菜"。在市中心的写字楼里，一层层架子上用水培技术种菜，省地、省水、不需要运输。

#### 水循环系统

> **人话**："中水回用"。洗澡水过滤后用来冲厕所，雨水收集起来浇花。

#### 可降解材料

> **人话**："吃土塑料"。袋子扔土里，几个月就被细菌吃没了，变回泥土。

#### 共享经济

> **人话**："只用不买"。共享单车、共享充电宝、共享雨伞。

### 4. 智能工业化 (Smart Industry)

#### 数字孪生 (Digital Twin)

> **人话**："虚拟克隆体"。工厂里有一台机器，电脑里有一个一模一样的3D模型。机器动，模型也动；模型预测机器明天会坏，机器明天真就坏了。

#### 柔性制造

> **人话**："个性化定制流水线"。以前一条线只能产黑色T型车，现在这条线上一秒产红色SUV，下一秒产蓝色跑车。

#### 工业物联网 (IIoT)

> **人话**："机器说话"。螺丝刀、机械臂、传送带都连网，互相发数据，协同工作。

#### 人机协作机器人 (Cobots)

> **人话**："不伤人的机械臂"。以前机械臂要把人围起来怕打死人，现在的Cobot碰到人会自动停，可以跟人肩并肩干活。

### 5. 海洋科技 (Ocean)

#### 海水淡化

> **人话**：把咸水变纯净水。中东国家常用。

#### 海上风电

> **人话**：把大风车插在海里。海风比陆地风大且稳。

#### 海底数据中心

> **人话**："把服务器扔海里"。微软干过。因为海底冷，省了空调电费；而且海底没氧气，机器不容易氧化。

#### 深海采矿

> **人话**：去海底捡"土豆"（多金属结核），里面全是稀有金属。

#### 海上漂浮城市

> **人话**：像巨型航母或积木一样的城市，浮在水面上，应对海平面上升。

> **注意**：我不知道可不可以带平板，可以带平板的话能不能问AI，根据面经下午的个面有人带平板过的（当稿子）

### 城市基础五大系统

> **城市类型分类**：根据产业定位，城市可分为**农业城**（第一产业）、**工业城**（第二产业）、**旅游城**（第三产业）等。不同城市类型会突出不同的系统模块。例如：**寒冷的智能工业化城市** = 具备高度智能工业化生产能力，且能够在严寒环境中提供可持续的生活条件和高效管理的未来城市，包含智能工业中心、严寒能源供应与管理系统、智能交通网络、常温智能居住区、抗寒垂直农业与生态等模块。

| 模块序号 | 模块名称 | 功能定义 | ZJU仪器切入点 |
|---------|---------|---------|-------------|
| Module 1 | 核心产业区 (The Core) | 这是题眼。根据抽到的5大主题变身（如工厂、医院、机场）。 | 部署自动化流水线 / 手术机器人 / 植保无人机。 |
| Module 2 | 能源动力区 (Energy Hub) | 给城市供电。风/光/核/地热。 | 能源管理系统(EMS)：部署传感器监控能耗，进行PID调节。 |
| Module 3 | 立体交通网 (Transport) | 人流物流。地面/地下/空中。 | 轨迹规划算法：无人驾驶调度，防碰撞系统。 |
| Module 4 | 生活与生态区 (Living & Eco) | 给人住的 + 处理垃圾/水的。 | 非侵入式健康监测：智能家居里藏着传感器，养老不用穿戴设备。 |
| Module 5 | 中央指挥大脑 (The Brain) | 你的主场。控制中心/数据中心。 | 数字孪生/IoT平台：所有传感器数据汇聚于此，大屏幕实时报警。 |


### 针对五大主题的应用

#### 1. 低空经济 (Low-altitude Economy)

- **M1 核心产业**：eVTOL垂直起降枢纽（像蜂巢一样的停机坪）
- **M2 能源**：分布式换电站（无人机飞累了直接换电池，不用充）
- **M3 交通**：3D空域航道（用绳子拉出空中轨道，分层飞行）
- **M4 生活**：空投接收阳台（每家每户窗外有个伸缩平台接外卖）
- **M5 大脑**：空域流量监管塔（雷达+视觉识别，防止撞机）

#### 2. 未来健康 (Future Health)

- **M1 核心产业**：个性化基因治疗中心 或 脑机接口康复仓
- **M2 能源**：生物质能发电厂（利用医疗废弃物发电）
- **M3 交通**：急救绿色通道（地下真空管道，胶囊列车运送器官/病人）
- **M4 生活**：全适老化社区（防摔倒地板+情绪监测墙壁）
- **M5 大脑**：全民健康云平台（实时处理所有市民的心跳血压数据）

#### 3. 可持续生活 (Sustainable Living)

- **M1 核心产业**：垂直农业塔（每一层都种菜，像DNA螺旋结构）
- **M2 能源**：光伏玻璃幕墙 + 雨水收集净化罐
- **M3 交通**：共享单车/步行绿道网络（禁止机动车）
- **M4 生活**：模块化可降解住宅（房子是积木拼的，不想住了拆了换地方）
- **M5 大脑**：碳足迹追踪中心（计算每个人排了多少碳，以此发货币）

#### 4. 智能工业化 (Smart Industry)

- **M1 核心产业**：黑灯工厂（无人工厂，机械臂自动作业）
- **M2 能源**：微型核聚变反应堆（工业耗电大，需要强能源）
- **M3 交通**：AGV自动物流小车轨道（地面全是二维码，小车跑来跑去）
- **M4 生活**：职住一体胶囊公寓（工人住在工厂楼上，下楼上班）
- **M5 大脑**：工业数字孪生中心（你的测控强项：预测性维护，机器坏之前先报警）

#### 5. 海洋科技 (Ocean)

- **M1 核心产业**：深海矿产采集站 或 海底数据中心
- **M2 能源**：潮汐能/波浪能发电机（利用海浪晃动发电）
- **M3 交通**：潜水艇驳接港口
- **M4 生活**：海上漂浮居住岛（像荷叶一样漂在水面）
- **M5 大脑**：水下声呐监测网（监控鱼群和海啸）

### 用"形容词"进行针对性调整

#### 1. 负面/困难类形容词（如：寒冷的、焦虑的、破碎的、危险的）

> **策略**：加"防御"和"冗余"

- **寒冷的** → 给M2能源加"供热管道"，给M4住宅加"保温层"，M1工厂变成"全封闭式"
- **焦虑的** → 给M4生活区加"心理疗愈花园"，M5大脑加强"隐私加密算法"，M3交通强调"绝对安全防撞"
- **危险的** → 给整个城市加"防护罩"，M5大脑变成"灾难预警中心"

#### 2. 正面/抽象类形容词（如：快乐的、甚至、漫游的、无形的）

> **策略**：加"体验"和"连接"

- **快乐的** → M1产业里增加"多巴胺制造"，M4生活区增加"游戏化设施"
- **独自漫游的** → M3交通变成"单人飞行器"，M4住宅变成"移动房车"
- **无形的** → 强调M5大脑（看不见的网），实体建筑都做成透明的或者地下的

### 评分标准

> **说明**：这一块有点冷冰冰（形式主义）了，有点像卡戴珊那种莫名其妙的东西必须得做。

#### 头脑风暴阶段

- 提出了至少一个具体的想法
- 提出了至少一个澄清性问题或重述了队友的想法
- 提出了至少一个在方法或内容上不同于其他人的想法
- 口头承认了队友反馈，或根据反馈提出了调整建议

#### 制作城市阶段

- 尺寸要求：长、宽、高分别为 75.5cm、51.5cm、>43cm
- 在项目的某个方面进行了实际操作（例如，放置材料、调整设计等）
- 负责完成了至少一项分配的任务，并且无需提醒
- 与另一名队员在至少一项具体任务上合作（如规划或构建）
- 在构建阶段遇到问题时提出了至少一个解决方案
- 至少一次分配或委派任务给队友体现领导能力

#### 交易/适应阶段

- 在交易阶段提出了至少一次交易或模块交换的建议
- 至少与其他团队进行了一次谈判，无论是提供还是接受条件
- 根据挑战任务提出了至少一个设计调整建议或进行调整
- 在挑战任务引入时保持参与而没有退缩或失去参与感

#### 最终展示阶段

- 清晰地演讲自己在项目中的角色，无需队友提示
- 提出了至少一项团队应对挑战任务的行动建议体现领导力
- 提出了一个直接应对挑战的解决方案（例如，功能改动，增加新特性等）
- 鼓励了至少一位队友参与或征求了他们的意见
- 在展示过程中至少回答了评委的一个问题




## 个面

### 稿子

#### 演讲评分标准

- 演讲要聚焦于申请人选择的五个主题之一——智能工业化
- 要展示多角度的思考，并解决了现实问题或未来挑战
- 演讲应该结构合理，有明确的开头、主体和结论
- 展示对内容的深入理解，并简化复杂的主题
- 幻灯片无误，与内容一致，并有效支持演讲
- 表达要流畅清晰，避免多余叹词和模糊不清的表达
- 演讲过程中，申请人要有效地与评委进行眼神接触并互动
- 在演讲中要提供创造性或独特的观点
- 要清晰阐述自己为何适合RB项目，将个人目标与项目目标对齐

#### Slide 1-2: Title

Good afternoon, professors. I am Bao Bowen from Zhejiang University. Today, I present my proposal for the Redbird program: 'Towards Socially Aware Embodied AI in Smart Manufacturing.'

#### Slide 3: Personal Intro

I am majoring in Biomedical Engineering with a GPA of 3.97. During my undergraduate studies, I didn't limit myself to coursework. I actively participated in interdisciplinary research and innovation competitions, winning the University Scholarship. This rigorous engineering training provided me with a solid foundation in Artificial Intelligence, preparing me for complex system design.

#### Slide 4: Why Smart Industrialization

So, why Smart Industrialization? Please look at this diagram from the World Economic Forum's latest report. It shows a 'Lighthouse Factory' achieving a 67% increase in productivity using mobile robots. This is impressive, but... it is mostly limited to isolated, caged zones. This gap is exactly my motivation. My goal at Redbird is to develop algorithms that allow robots to seamlessly integrate into dynamic environments—ensuring they are not just efficient, but safe alongside human workers.

#### Slide 5: Research Exp 1 - Wavelet

To achieve this, I first built my foundation in data processing. In my research on Wavelet Convolutions, I optimized time-series analysis for medical data. While this was for healthcare, the core capability is universal: I learned to design lightweight, efficient algorithms that extract precise features from noisy data. This mathematical intuition is critical for any real-time robotic system.

#### Slide 6: Research Exp 2 - Internet+ / Entrepreneurship

In the 'Internet+' Innovation Competition, where we won the National Bronze Award, I led a project that was more than just coding—it was an entrepreneurial venture. We identified a real market pain point: the labor-intensive digitization of archaeological reports. I led the team to build a product that fused YOLO detection with LLMs to automate this process. This experience taught me how to transform technical solutions into viable products, which aligns perfectly with Redbird's maker spirit and focus on real-world impact.

#### Slide 7: Research Interests

Moving forward, I have identified two key research directions for my Master's. First is World Models—giving robots an internal simulator to predict future consequences before acting. Second is End-to-End Control, similar to XPeng's recent work on pure vision-action models. I believe the future lies in combining these two.

#### Slide 8: Bachelor Thesis

Currently, I am using my Bachelor Thesis as an entry point into this field. I chose Social Navigation because it allows me to focus on Reinforcement Learning logic without getting bogged down by complex kinematics yet. I am optimizing the Falcon baseline by adding a Risk Awareness Module. The goal is simple: train an agent that doesn't just reach the goal, but knows how to be 'polite' and maintain safe distances from humans.

#### Slide 9: Deployment / The "Crash" Story

Beyond simulation, I am also learning the harsh reality of hardware deployment. I am porting the existing LOVON algorithm to a Unitree Go2 robot. It's a learning process. For example, currently, the robot lacks occlusion awareness—if a person hides behind a wall, the dog might crash into the wall trying to chase them. Debugging these real-world failures is exactly where I am gaining my Sim-to-Real experience.

#### Slide 10: Roadmap

Looking at my roadmap for Redbird:

- **Short-term**: I will finish my thesis and continue solving those hardware navigation issues.
- **Mid-term**: At HKUST(GZ), I plan to dive deeper into the Brain-Cerebellum architecture, exploring how to integrate better environmental representations.
- **Long-term**: I hope to leverage the GBA supply chain to test these algorithms in actual logistics scenarios, moving from the lab to the factory floor.

#### Slide 11: Why Redbird

Finally, why Redbird? HKUST(GZ)'s strong ecosystem aligns perfectly with my goal of building deployable systems for the GBA. I specifically value three things here:

1. The Interdisciplinary Synergy that allows me to collaborate across hubs;
2. The access to the GBA's robust Supply Chain for rapid hardware iteration;
3. And the university's proven track record of incubation, which gives me the confidence to turn my research into a startup.

#### Closing

I am transitioning from BME to Robotics because I believe the best robots should understand the world like humans do. I am ready to bring my interdisciplinary background to the Redbird team. Thank you.

### 提问

#### 提问环节评分标准

- 理解并准确回应了评委的问题
- 回答经过深思熟虑，并显示了对主题的深入理解
- 面对压力时保持冷静镇定，沉着应对难题
- 很好地应对挑战性或意外问题，并提供相关的解决方案或观点
- 展示逻辑推理能力，分析问题并提供有见地的回答
- 提供团队合作的具体例子，并表达对协作的强烈兴趣
- 观点具有说服力，并能够有效支持其立场
- 展示自我意识，讨论了自身的优势、劣势和需要改进的地方
- 根据评委的反馈调整自己的回答，并与他们进行有意义的互动