# LOVON 相关 Baseline 调研
本篇内容主要集中在针对 LOVON 论文中所对比的 paper 工作，他的仿真指标，一方面顺着前人的工作一路做下来思路比较直接也比较连贯，另一方面我还是觉得`gym-unrealcv`这个模拟仿真的引擎相对`MatterPort3d`还是小众了一点，也没有现成的博客文章去汇总有哪些工作用到了这个。

![这个仿真得分已经终结这个领域了](/blog/2025/lovon-baseline.png)

## DIMP: Learning discriminative model prediction for tracking

## SARL: End-to-end active object tracking and its real-world deployment via reinforcement learning

## AD-VAT: End-to-end active object tracking and its real-world deployment via reinforcement learning

## AD-VAT+: An asymmetric dueling mechanism for learning and understanding visual active tracking

## TS: Towards distraction-robust active visual tracking

## RSPT: reconstruct surroundings and predict trajectory for generalizable active object tracking

## EVT: Empowering embodied visual tracking with visual foundation models and offline RL

## TrakVLA: Embodied visual tracking in the wild
> PKU在2025年5月的工作，VLA对训练算力和时间的要求堪称恐怖，所以这里单纯参考一下思想

Embodied visual tracking enables an agent to follow a specific target in dynamic environments using **only egocentric vision**. 

This task is inherently challenging as it requires both accurate target recognition and effective trajectory planning under conditions of **severe occlusion** and **high scene dynamics**, 也就是遮挡和高动态性。

| 研究方向 | 现有方法特点 | 局限性 |
| --- | --- | --- |
| 具身视觉跟踪 | 分模型基（IBVS）、RL 基（AD-VAT、EVT [6]）、IL 基（Uni-NaVid） | 误差累积；Uni-NaVid 依赖离散动作空间 |
| 具身导航 | 聚焦静态室内环境（如视觉 - 语言导航） | 忽略真实世界动态性 |
| VLA 模型 | 用于操纵/导航，基于预训练 VLM 扩展动作生成 | 推理效率低，仅在低动态环境验证 |

而现有的相关工作都是将Recognition和Trajectory Planning给decouple出来的，而these methods are limited to category-level tracking in relatively open areas, 看来大家都意识到了这个问题，而作者指出这是因为上面decoupling的两个模块会产生error accumulation——识别错误可能导致规划失效，反之亦然。

因此要用unified framework统合起来，共用token encoding（deconding的时候再分为两个头，一个language modeling head解码识别任务的文本响应，一个anchor-based diffusion head生成航点轨迹应用于规划任务）

![overview](blog/2025/trackVLA_overview.png)

