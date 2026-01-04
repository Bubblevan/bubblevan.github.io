---
title: "流匹配与扩散模型"
description: "MIT Class 6.S184: Generative AI With Stochastic Differential Equations, 2025"
---

## 课程信息

**MIT Class 6.S184: Generative AI With Stochastic Differential Equations, 2025**

**An Introduction to Flow Matching and Diffusion Models**

## 学习目标

好吧我们开始我们的扩散模型与流匹配模型学习，主要是为了能够看懂 **VLA** 的 **π-0** 都在做什么。

## 学习资源

### GitHub 参考实现

- [MIT6.S184 - lhxcs](https://github.com/lhxcs/MIT6.S184)
- [mit6s184 - cxzhou35](https://github.com/cxzhou35/mit6s184)

这两篇同学的 **Github** 可以 follow 一下。

### 其他资源

- [豆包对话](https://www.doubao.com/chat/34337422246470658)：类似教案一类的文档，但是肯定不能止步于此
- **Bilibili** 里的转载：还需要看，我需要学会手推！

## 课程大纲

| Lecture | 主题 | 主讲人 |
| --- | --- | --- |
| **Lecture 1** | 流模型与扩散模型基础 | Peter Holderrieth |
| | - 生成模型介绍 | |
| | - 常微分和随机微分方程 | |
| | - 从流和扩散模型采样 | |
| **Lecture 2** | 构建训练目标 | Peter Holderrieth |
| | - 条件和边际概率路径 | |
| | - 连续性方程和 Fokker-Planck 方程 | |
| | - 边际向量场和边际分数函数 | |
| **Lecture 3** | 训练流和扩散模型 | Peter Holderrieth |
| | - 流匹配 | |
| | - 分数匹配 | |
| | - 扩散模型的各种方法 | |
| **Lecture 4** | 构建图像生成器 | Peter Holderrieth |
| | - 引导和条件生成 | |
| | - 神经网络架构 | |
| | - 最新模型概述 | |
| **Lecture 5** | 生成式机器人技术 | Benjamin Burchfiel |
| | - 丰田研究院 Benjamin Burchfiel 客座讲座 | |
| | - 大型行为模型 | |
| | - 机器人领域的扩散模型 | |
| **Lecture 6** | 生成式蛋白质设计 | Jason Yim |
| | - MIT 的 Jason Yim 客座讲座 | |
| | - 用 AI 设计新蛋白质 | |
| | - 蛋白质结构生成的流匹配 | |

> **注意**：第六节 **Lecture** 因为我不做AI4S所以忽略掉，主要关注一下它的 **lab**。

## 实验课程

### 课程资源

- **GitHub 仓库**: [iap-diffusion-labs](https://github.com/eje24/iap-diffusion-labs)
- **课程官方网站**: [diffusion.csail.mit.edu](https://diffusion.csail.mit.edu)

仓库包含 3 个主要实验室，全部以 **Jupyter Notebook** 形式提供，可通过 **Google Colab** 运行：

| 实验室 | 主题 | 链接 |
| --- | --- | --- |
| **Lab 1** | 随机微分方程(SDE)基础 | [labs/lab1.ipynb](https://github.com/eje24/iap-diffusion-labs/blob/2025/labs/lab1.ipynb) |
| **Lab 2** | 扩散模型与流匹配 | [labs/lab2.ipynb](https://github.com/eje24/iap-diffusion-labs/blob/2025/labs/lab2.ipynb) |
| **Lab 3** | 条件扩散与高级应用 | [labs/lab3.ipynb](https://github.com/eje24/iap-diffusion-labs/blob/2025/labs/lab3.ipynb) |

## 更多资源

- **课程讲义**: [lecture-notes.pdf](https://diffusion.csail.mit.edu/docs/lecture-notes.pdf)
- **视频讲座**: [课程官网主页](https://diffusion.csail.mit.edu)
- **实验解答**: 仓库中的 `solutions` 文件夹 

