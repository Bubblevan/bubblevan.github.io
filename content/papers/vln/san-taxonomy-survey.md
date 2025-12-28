---
title: "A Survey on Socially Aware Robot Navigation: Taxonomy and Future Challenges"
---

这些综述对我去写开题报告的文献综述也是有用的。这一篇主要是覆盖 2013-2024 的工作

## 预备知识

### Definition

导航定义：导航是具身智能体（机器人或人类）在环境中改变位置以达成目标的行为，过程中可能遇到其他共享该环境的智能体。
三类导航术语辨析：
Human-aware navigation（人类感知导航）：算法需专门考虑机器人附近人类的存在、活动及偏好，但不要求机器人表现出自然或社交行为。
    - 它只强调“考虑到人”，但不假设机器人的行为必须表现得自然或符合社交规范 。简单来说，只要机器人能避开人并尊重人的基本偏好（如不撞到人），就可以称之为“Human-aware”
Social navigation（社交导航）：整合人类互动时的社交规则、协议和角色，但存在无法区分人机社交行为与能力的表述风险。
    - 这个词的风险在于，它在字面上很难区分机器人表现出的社交行为是由于其能力限制，还是在模仿人类的真实社交行为
Socially aware navigation（社交感知导航）：强调在人类附近导航的社交属性，却不强制机器人社交行为与人类完全一致，因此本文选用该术语，相关智能体称为 “社交（导航）智能体”。
    - 这是一个更具包容性的定义，至少作者是这么认为的，下面是它给出的定义：
社交感知机器人的核心属性（满足则可称具有 “社交感知” 能力）：
检测人类并将其视为特殊实体，安全为首要优先级；
行为设计以最小化对人类的干扰、不适和困惑为目标；
显性或隐性地表达自身导航意图；
冲突时以社交方式解决（可能牺牲自身任务），需理解人类意图与协商能力。
关键补充：“人类智能体” 含个体人类及人类控制的车辆 / 机器人；因人类意图受场景影响难预测，现有研究多聚焦前 3 个属性，而最低要求是满足前 2 个属性。
> BTW，目前主流的中文翻译趋势是将 Socially Aware 翻译为 “社会感知” 或 “社会意识”；而将 Social Navigation 翻译为 “社交导航”

## Proposed Taxonomies

![](/paper\san-survey-taxonomy-robottype.png)
![](/paper\san-survey-taxonomy-plan-decision-make.png)
![](/paper\san-survey-taxonomy-situation-aware-assess.png)
![](/paper\san-survet-taxonomy-tools-evaluation.png)

