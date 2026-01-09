---
title: "Locomotion 论文精读（四）Legged Locomotion in Challenging Terrains using Egocentric Vision"
---

> https://arxiv.org/pdf/2211.07638

## 研究背景
2022年老资历，首先批判一番本体感知的缺陷，即高程图构建+foothold规划的两阶段流程存在3个问题：
- 高程图易受噪声干扰、易失效；
- 需专用硬件（如多相机、激光雷达），成本高；
- 不符合生物运动逻辑（人类无需预构建高程图即可行走）。
![](/paper/vision-locomotion-problems.png)

那个时候还是预编程步态的时候，小尺寸机器人爬台阶的时候就容易被台阶阻挡或者下坡的时候倾倒。
所以写这篇是目的是为了开发端到端 locomotion 系统，使小尺寸四足机器人（Unitree A1）仅通过单目前置深度相机，在室内外、昼夜、城市 / 自然复杂地形（台阶、路缘、踏脚石、缝隙）稳定移动，且无需预编程步态。


## 方法论

![](/paper/vision-locomotion-pipeline.png)
