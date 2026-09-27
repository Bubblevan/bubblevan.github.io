---
schema: bubblevan/v1
id: blog-20260910-aims5702-ai-in-practice
content_kind: blog
title: "AIMS5702：从张量、训练到部署的 AI 工程实践"
date: 2026-09-10
updated: 2026-09-10
status: draft
visibility: public
summary: "整理 AIMS5702 Artificial Intelligence in Practice 的课程主线、教学安排、考核组成，以及第一讲从数据表示到 AI 系统部署的工程视角。"
topics: [AIMS5702, AI Engineering, Deep Learning, PyTorch, GPU, CUHK]
projects: []
aliases: []
authors: [bubblevan]
---

AIMS5702《Artificial Intelligence in Practice》是一门 3 学分的工程实践课。课程不以背诵模型为目标，而是带着学生从数据表示、网络设计、训练设置一路走到模型优化、设备部署、GPU 编程和自定义算子。

## 课程定位与学习目标

课程大纲把学习目标概括为五部分：

1. 针对具体任务设计 AI 系统，包括数据准备、模型选择、训练和部署。
2. 掌握向量运算，以及多层感知机、卷积网络和循环网络等结构的基本编程方法。
3. 理解数据准备、数据加载、并行计算、优化、并行训练和分布式训练。
4. 能够围绕房价预测、视觉分类和文本分析等任务设计 AI 项目。
5. 能够使用预训练基础模型完成图像生成、大语言模型和图像分割等应用。

这门课确实有一点 Stanford CS336 的味道：它也强调理解模型和系统的底层实现，而不是只调用现成接口。但两者重点不同。CS336 更集中于从零构建语言模型，AIMS5702 的范围更宽，重点是通用 AI 系统工程，包括张量、训练、部署、硬件加速和自定义算子。课程把 CS336、CS231n、《Deep Learning》以及 PyTorch、TensorFlow、NumPy 官方教程列为参考材料，而不是把自己等同于这些课程。

## 课程内容与时间线

课程共有 12 次面授课，时间为每周四 19:00–22:00，地点 ELB LT1。课程资料、公告、录播、讲义、作业和 lab 材料通过 Blackboard 发布；八号或以上台风、黑色暴雨等情况提前确认后，课程可能切换到 Zoom。

| 日期 | 主题或活动 |
| --- | --- |
| 9 月 10 日 | Course Introduction |
| 9 月 17 日 | 基础向量运算；图像、文本、音频表示；NumPy |
| 9 月 24 日 | 基础网络设计；PyTorch |
| 10 月 1 日 | 国庆假期 |
| 10 月 8 日 | Deep Learning Practice 1：Python 基础与 toy learning task |
| 10 月 15 日 | Loss function、训练设置、训练数据创建 |
| 10 月 22 日 | 卷积、Transformer 等网络结构 |
| 10 月 29 日 | 设备端部署、模型优化 |
| 11 月 5 日 | Deep Learning Practice 2：网络训练与部署 |
| 11 月 12 日 | GPU、CUDA、Triton、自定义算子；Coding Quiz 1 |
| 11 月 19 日 | Deep Learning Practice 3：简单 Triton 算子 |
| 11 月 26 日 | Advanced Topics |
| 12 月 3 日 | Coding Quiz 2；Individual Project Q&A |
| 12 月 24 日 | Individual Project 截止提交 |

## 第一讲：从数字规律到 AI 系统

老师先用“3、5、7，接下来是什么”说明机器学习的基本过程：从训练样本中找到规律，例如 (y=2x+1)，再把新输入代入函数进行预测。换成猫识别任务后，输入变成图像，输出变成“猫 / 非猫”等类别标签。

图像可以看成二维矩阵，视频是连续图像组成的三维张量，音频可以表示为一维数组或二维表示，文本也要先转换成数字。模型本身不是魔法，而是数学、编程和计算资源结合起来的系统。

一个典型 AI 工程流程是：

1. 收集并标注训练数据。
2. 选择或设计网络结构。
3. 在 CPU / GPU 上进行训练。
4. 通过精度调整、量化等方式优化模型。
5. 把模型部署到目标设备或运行环境。

## 考核组成与关键规则

课程总成绩由以下部分组成：

| 项目 | 比例 |
| --- | ---: |
| Class Attendance | 5% |
| 2 Online Assignments | 10% |
| 3 In-class Labs | 30% |
| 2 Coding Quizzes | 30% |
| Course Project | 25% |

从两次课的口头说明看，Assignment 1 和 Assignment 3 更接近在线提交；Assignment 2、4、5 对应三次课内 lab。老师会在上课前约 1–2 小时发布当次 in-class lab，要求学生带电脑到现场完成，课程团队计划尽量在课堂内完成 grading。第一次 lab 会先验证这个流程是否可行，如果时间不够，后续的完成或批改方式可能调整；最终仍以 Blackboard 的作业页面和 rubric 为准。

课内 lab 的实际准备有一个容易被忽略的工程问题：教室充电插座很少。10 月 8 日、11 月 5 日、11 月 19 日这几次预计进行 lab 的课，应该在出门前把 laptop 充满，并确认 Google Colab、浏览器和账号已经可以使用。把它记成绑定课程事件的课前 reminder 比单独建立一个长期 TODO 更合适：前一天晚上提醒一次，当天出门前再检查一次。

Attendance 使用 uReply。普通课程在第二次休息时完成 uReply 参与；两次 quiz 课程则通过提交 quiz 试卷确认出席。老师特别提醒，uReply 需要 CWEM 登录，并可能使用 GPS 判断是否在教室或校园附近，不能只拿到二维码后在远处提交。

两次 coding quiz 都在课堂内进行：Quiz 1 在 11 月 12 日的课程后段，Quiz 2 在 12 月 3 日课程开头，随后是 Individual Project Q&A。老师明确说明 quiz 是纸笔手写、不能使用电脑；目前设想的题型包括概念选择题、填空题（参数、函数名、数据类型等），以及阅读 Python 代码、指出错误或解释某一行，预计选择和填空占多数。课程没有现成 sample paper，之后的 assignments 和 uReply 练习题会提供更接近 quiz 的练习。

非医疗原因缺席需要提前至少一周申请并提供证明；医疗原因需要按照课程大纲，在考试后两天内提交香港注册医生出具的有效证明。老师口头上还强调医疗证明的开具日期最好与 quiz 当天一致，遇到冲突时应以 Blackboard 和任课老师的最终通知为准。

迟交规则也需要提前记住：在线作业和课内 lab 第一次在截止后 7 天内提交，按所得分数扣 5%；后续迟交会按课程大纲的递进规则扣分；超过 7 天不再给分。Project 在截止后 3 天内提交，每天扣除所得分数的 20%，超过 3 天不再给分。

Individual Course Project 目前尚未设计完成，老师预计在 10 月底或 11 月初、完成主要 lecture materials 后再确定难度和题目。今年的项目会和往年有所不同，旧项目材料不能直接照搬。

## 环境、GPU 与 AI 工具

课程优先使用 Google Colab。CPU 免费，很多前期作业不需要付费 GPU；AIMS 项目提供的 GPU 额度由多门课共享，应该先用 CPU / T4 和小规模数据验证代码，再运行大规模任务。本地环境如果使用 Anaconda，老师建议选择 Python 3.12，而不是盲目追最新版本。

课程大纲采用 **Approach 2：Use only with prior permission**。不能默认在作业、lab 或项目中自由使用 ChatGPT、Copilot 等工具；如果课程教师允许，需要说明工具、用途、提示词和生成内容，并进行引用或致谢。Quiz 更偏向检查本人是否掌握基础操作，不能把“会让 AI 生成代码”当成已经掌握课程。

## 对这门课的学习策略

这门课的知识链条可以压缩成：

> 数据表示 → 张量运算 → 网络结构 → 训练与损失 → GPU 加速 → 模型优化 → 部署与项目。

因此不应只收藏模型结构，而要同步练习 NumPy、PyTorch、张量 shape、内存和 stride、训练循环、数据加载、GPU 调用以及最小可运行实验。后面的网络设计、Triton 和部署内容，都会建立在第一阶段的基础运算之上。
