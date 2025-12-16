---
slug: pi-series-daily
title: VLA 学习计划与资源整理
authors: bubblevan
tags: []
---

今天打算进行分野，一半空余时间拿来学习，一半拿来研究

然后这里暂时备忘录写一下，都是明年2026三四月要做的：
1、办理香港签证
2、申请校友邮箱
3、延长校网以支持cc98访问

根据[这个帖子](https://www.xiaohongshu.com/explore/692ff979000000001e01164e?xsec_token=AB_MHi050wk48-lggmIts9bDVIDFAAFtAnzhDdsF1tGUQ=&xsec_source=pc_search&source=unknown)，入门VLA主要需要做的是这几点：
- 继续完善赵老师的强化学习理论学习，并补足其未涉及的PPO、GRPO等算法
- 这里楼主推荐的是[huggingface强化学习实践](https://huggingface.co/learn/deep-rl-course/unit1/rl-framework)，而不是Hands-on-RL，我想都一样
- 整合学习VLM（CLIP或LLaVA）然后扩展到VLA（添加Action输出）
    - 理解VLA的核心内容：基于预训练的VLM通过finetune预测机器人动作，挑战包括数据稀缺、实时性和sim2real
    - 一些关键概念：action chunking、flow matching和分层架构（高水平规划+低水平执行）
    - 阅读论文：RT-2、OpenVLA、π0（Physical Intelligence）、Gemini Robotics
    - VLA算法的复现，对于ACT、DP等基础算法的公式的一个推导深入理解
    - 对于机器臂，首推用lerobot的so101做一个实体机器人的算法的复现，方便后续进行一个其他算法的拓展，实现自己改造的VLA算法
    - 还可以找自动驾驶的项目啥的，但是lz不熟

在这里就可以引出新关注到的两位老师了：
一个是[陳林](https://xhslink.com/m/AeDaNtzi8If)，自动驾驶领域高手，目前主要更新的内容是【每天思考一个强化学习问题】，比较有意思
一个是[彭思达](https://www.xiaohongshu.com/user/profile/56daf09784edcd4fa92ef524?xsec_token=ABmkhgoHqDjr9VKIDj3tkjPqiQDBmLU9QBKd32GwYGM3M=&xsec_source=pc_note)，是我们浙大软件学院百人计划研究员，研究方向是面向空间智能体的闭环仿真训练，而阅读它的[科研入门文档](https://github.com/pengsida/learning_research?tab=readme-ov-file)给了我很大裨益，当然有点多还没有看完，其Github主页的公开仓库也值得关注。
一个是[无敌正义雷欧奥特曼](https://www.xiaohongshu.com/user/profile/5d1c50060000000012017d39?xsec_token=ABuqA2q9bT__59RJHbM6B7aDOaRwt6-YLvV6iUwGoBlD8=&xsec_source=pc_note)，主要是通过其26fall的秋招面试去反推这些企业都有哪些，需要什么技术栈，截止12月13号已经有92面了

还有这个[GAiR的星河AI研究所](https://gair.ai/community.html)，算是一个比较大型的民间付费社群，我在B站上看到的3类世界模型的视频就是他们的。

又有一位西工大在读博士，研究兴趣为三维视觉的[Gavin Sun](https://xhslink.com/m/58sqs9Cj3uD)非常厉害，在推荐其日常读到的论文，重点是是用笔记的形式写的，和我的方向也有交叉！
还有就是[tabris](https://xhslink.com/m/59cZSRbXitb)，属于是人形分享器，据说多数是X推给他的，少数是师友分享的，对我来说也非常有用，像是spatial intelligence这种、
