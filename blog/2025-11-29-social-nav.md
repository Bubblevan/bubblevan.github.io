---
slug: social-nav
title: 社会意识的导航模型
authors: bubblevan
tags: []
---

起因是在小红书上刷到了这一篇2025年11月的新文章

![Social Navigation](/blog/2025/social-nav.jpg)

结果却搜到了[ICRA 2025] From Cognition to Precognition: A Future-Aware Framework for Social Navigation，于是误闯天家到了[Awesome Robot Social Navigation](https://github.com/Shuijing725/awesome-robot-social-navigation)的领域。

Social Navigation（社会导航）的核心思想是"以人为本"。它要求机器人不仅仅把人类当作需要避开的障碍物，而是能够理解并尊重人类的社会规范与个人空间，最终实现自然、和谐、无感知压迫的共同空间使用。例如，在走廊中与人迎面相遇时，机器人会像人一样靠右行驶；当需要穿过一群人时，它会寻找合适的时机和路径，而不是生硬地"切开"人群。

| 特性维度 | 🤖 Social Navigation (社会导航) | 🦿 LOVON (腿部开放词汇物体导航) | 👁️🗨️ VLN (视觉语言导航) |
|---------|-------------------------------|-------------------------------|------------------------|
| 核心目标 | 安全、舒适、符合社会规范地在人类共享空间中导航 | 在开放世界中，根据物体名称，自主搜索并导航到指定物体 | 根据自然语言指令，在环境中执行导航任务 (如"去厨房拿杯水") |
| 环境特点 | 动态、拥挤的人类环境，充满不确定性 | 非结构化的开放环境，地形复杂，目标物体可能被遮挡或距离遥远 | 通常基于仿真器（如Habitat, AI2-THOR），环境可以是静态的，也引入动态人类 |
| 关键输入 | 人类的位置、运动轨迹、群体行为、社会规范 | 目标物体的文本名称 (如 "chair")、机器人视觉传感器数据 | 详尽的自然语言指令、机器人视觉传感器数据 |
| 技术侧重点 | 行人轨迹预测、社交力模型、强化学习策略、舒适度与安全性评估 | 开放词汇目标检测、大语言模型任务分解、腿部机器人运动控制、抗运动模糊 | 视觉-语言对齐、指令理解、跨模态推理、路径规划 |
| 典型输出/动作 | 避让、保持社交距离、绕行、调整速度、非语言沟通 | 朝向目标物体的运动控制命令 (如速度、方向)，处理复杂地形 | 导航动作 (如"左转"、"前进1米"、"停止") |
| 核心挑战 | 对人类意图的预测、复杂社会规则的建模与量化、安全性、舒适感 | 长时序任务规划、动态模糊下的稳定感知、复杂地形下的稳定移动、开放词汇识别泛化能力 | 指令与环境的关联、未知环境泛化、长指令理解、跨模态表示学习 |

然后去[学术社区（迫真）](http://xhslink.com/o/6M94ZS8vHHm)上搜索了一下，这里seven17这位大佬也在2025年11月16-17给出了自己作为人形公司SLAM面试官对业界人形机器人在研究的算法的一些经验，非常有参考意义。

> 有一说一小红书真的比很多像是CSDN之类的更好的学术交流平台

我就很赞同这里在小红书的某个Ask Me Anything上看到的港科广的梁老师的话：

<div style={{display: 'flex', justifyContent: 'space-between', gap: '10px'}}>
  <div style={{flex: 1}}>
    <img src="/blog/2025/gkg-liang1.jpg" alt="港科广梁老师观点1" style={{width: '100%'}} />
  </div>
  <div style={{flex: 1}}>
    <img src="/blog/2025/gkg-liang2.jpg" alt="港科广梁老师观点2" style={{width: '100%'}} />
  </div>
</div>

| 活动名称 | 主要关联会议 | 活动形式 | 核心侧重点 |
|---------|------------|---------|-----------|
| RoboSense机器感知挑战赛 | IROS 2025 (官方认证竞赛) | 竞赛 | 在动态人群环境中，使机器人的导航行为符合人类的社会规范。 |
| Advances in Social Robot Navigation研讨会 | ICRA 2025 | 研讨会 | 探讨社交机器人导航在规划、人机交互等领域的最新进展，并包含基准测试挑战。 |

RoboSense挑战赛是IROS的官方认证竞赛，它设置了专门的社交导航赛道，旨在解决机器人在真实动态环境中的导航问题。

**任务目标：** 参赛者需要开发一个基于RGB-D输入的移动机器人导航模型。该模型的核心任务是让机器人在不影响周围人类行为的前提下完成导航，并使其行为符合人类的社会规范，例如主动避让、保持合适的社交距离等。

**挑战与评测：** 除了衡量导航成功率和路径效率，比赛还特别引入了个人空间合规性（PSC）和人机碰撞次数（H-Coll）等指标，专门用于量化机器人行为的"社交友好度"。

**前沿技术：** 该赛道推荐的基线模型（Baseline）是Falcon，这是一个由港科广和港科大联合提出的新算法，它通过将轨迹预测算法融入强化学习框架，让机器人能够预测行人未来的移动路径，从而实现更超前、更安全的规划。

除了竞争激烈的比赛，ICRA的"Advances in Social Robot Navigation"研讨会则是深入了解该领域学术研究和前沿发展的绝佳平台。

**活动形式：** 这是一个学术研讨会，会邀请领域内的专家进行讲座和专题讨论。同时，它也主办 Arena 4.0挑战赛，旨在为不同的社交导航策略建立基准和评测体系。

**核心议题：** 研讨会关注如何使机器人的导航行为更易于理解、更符合社交场景。探讨的技术方向包括运动任务规划、基础模型的应用、人机交互策略等。

我打算接下来的核心往 Social Navigation 上面靠，这里很符合以人为本的设计特点，而LOVON也确实面临这一困境。也如梁老师所言，这是个容易入门具身的领域。可惜这个比赛在这个时候已经结束了，下面计划的第一步是研读Falcon这个baseline（也就是上面提到的ICRA 2025中稿文章），使用[Robosense](https://robosense2025.github.io/track2)提供的GitHub代码和数据集去复现基线，然后参考排行榜的改进去思考参赛者解决的问题集中在哪里，又是如何进行的。

Resource	Link	Description
GitHub Repository	https://github.com/robosense2025/track2	Baseline code and setup instructions
Dataset	HuggingFace Dataset	Dataset with training and test splits
Baseline Model	Pre-Trained Model	Weights of the baseline model
Registration	Google Form (Closed on August 15th)	Team registration for the challenge
Evaluation Server	EvalAI Platform	Online evaluation platform
