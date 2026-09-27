---
schema: bubblevan/v1
id: blog-20260917-aims5702-basic-math-assignment-1
content_kind: blog
title: "AIMS5702：张量基础、课程安排与 Assignment 1"
date: 2026-09-17
updated: 2026-09-17
status: draft
visibility: public
summary: "我对 AIMS5702 Basic Mathematics 课程内容、教学安排、张量语法和 Assignment 1 提交要求的完整整理。"
topics: [AIMS5702, PyTorch, NumPy, Tensor, GPU, Python]
projects: []
aliases: []
authors: [bubblevan]
---

今天这节 AIMS5702 给我的感觉，是老师先把课程和作业的边界说清楚，再用一整节课补齐 AI 代码最底层的张量基础。表面上看都是 dtype、切片、矩阵乘法这些入门内容，但这些东西正好决定了我以后能不能看懂更复杂的模型代码。

## 1. 先说课程安排：这是一门面授课

### 1.1 课程描述为什么临时改了

上课前十分钟发生了一件和技术内容无关、但我觉得很重要的事。老师临时接到工学院发来的邮件：项目组收到 CSCSE 通过 GSO 对课程教学形式的询问，需要避免别人把课程理解成 online teaching。

所以老师修改了课程描述，明确课程是 face-to-face teaching。正常情况下课程还是到教室上课；只有恶劣天气等特殊情况，线上教学才作为面授的替代安排。课程材料或录音的存在，也不代表这门课平时是线上课。

![课程教学形式调整的课堂截图](/daily/2026/9-17/aims5702-course-policy-email.jpg)

这也解释了为什么课程大纲里的措辞突然变得更严格。以后我判断课程安排，应该以 Blackboard 和最新课程大纲为准，而不是仅凭有没有 lecture recording 来判断上课形式。

### 1.2 课件可能在上课前更新

老师还提到，有同学发现 slide 里的错误，某些页面会在上课前或课后临时更新。他举了 page 40 的例子。因此我以后看课件时不能只保存最早下载的版本，做笔记和作业要优先看课程平台上的最新文件。

### 1.3 AI 工具可以辅助，但不能替我理解代码

老师没有把重点放在“能不能调用 AI”上，而是提醒我：即使用工具帮忙，也要知道每一行代码为什么这样写，最好能自己解释答案。因为 quiz 可能只改变数字或题目背景，真正考的是我有没有掌握方法。

如果遇到作业问题，可以联系 TA，但老师说 TA 的回复可能需要一两天。所以比较合理的做法是先自己定位问题，把完整的输入、输出和报错整理好，再发邮件，而不是只丢一句“为什么不对”。

### 1.4 出勤记录也有自己的流程

老师会从新的 uReply 系统导出出勤记录，再放回课程页面。课堂上说累计到 10 条记录可以拿到出勤部分的 5 分；如果手机端遇到问题，尤其是 iPhone 的 uReply 页面异常，要按照 FAQ 里的步骤处理。这个流程和作业提交一样，不能只做了一半就默认系统已经记上了。

## 2. 数据类型：精度、范围和显存是同一个问题

### 2.1 整数与 two's complement

`int8` 只有 8 个 bit，负数不是额外加一个负号，而是用 two's complement 表示。理解这一点对后面的量化很有用：同样的 bit 数，怎么解释 bit pattern 会决定可表示的整数范围。

### 2.2 float16 和 bfloat16

浮点数可以粗略拆成 sign、exponent 和 mantissa。`float16` 使用 5 个 exponent bits 和 10 个 mantissa bits；`bfloat16` 的 exponent bits 和 `float32` 一样，因此动态范围更大，但 mantissa 精度更低。

![课堂 quiz：float16 的 exponent 和 mantissa](/daily/2026/9-17/aims5702-quiz-float16.jpg)

![课堂 quiz：bfloat16 的主要优势](/daily/2026/9-17/aims5702-quiz-bfloat16.jpg)

所以 `bfloat16` 和 `float16` 不是简单的“谁更精确”。前者更不容易因为数值范围不够而溢出，后者在 mantissa 上保留了更多相对精度。实际使用时还要看 GPU 是否支持以及 kernel 是否高效。

### 2.3 参数量如何换算显存

估算模型参数显存时，先算参数数量，再乘以每个参数占用的 byte 数。例如 3 billion 个参数使用 `float32`，每个参数 4 bytes，总量就是 12 billion bytes，还没有算 activation、gradient、optimizer state 等额外开销。

![课堂 quiz：3 billion 参数的 float32 显存估算](/daily/2026/9-17/aims5702-quiz-vram.jpg)

## 3. Tensor 语法：先看 shape，再看操作

### 3.1 Broadcasting

逐元素运算时，某个维度如果是 1，就可以沿这个维度广播。例如 `(4, 3)` 和 `(1, 3)` 可以相加；但 `(4, 3)` 和 `(2, 3)` 没有可广播的维度，就不能直接相加。

我现在更愿意把 broadcasting 看成 shape contract：先从最后一个维度开始比较，两个维度相等或其中一个是 1 才能继续。这样读 attention 或 batch 运算的代码时，不会只凭感觉猜结果 shape。

![课件中的 broadcasting 示例](/daily/2026/9-17/aims5702-slide-broadcasting.png)

### 3.2 索引与切片

切片最容易写错的地方是“左闭右开”：`a[i:j]` 包含 `i`，但不包含 `j`。所以 `a[1:4]` 取到的是第 1、2、3 个位置。`a[-2:]` 则是从倒数第二个位置一直取到结尾。

连续切片还可以用来取一个中间区域。Boolean mask 的逻辑不同：它逐个检查 mask，保留 `True` 对应的元素，跳过 `False` 对应的元素；mask 必须和它作用的维度对齐。

![课件中的 tensor indexing 与 slicing 示例](/daily/2026/9-17/aims5702-slide-indexing-slicing.png)

索引时插入新维度也很重要。`unsqueeze` 或 `None` 并没有改变原来的数值，只是给 tensor 增加一个长度为 1 的维度，让后续 broadcasting 有机会成立。

## 4. Tensor 的 storage、stride 和 view

### 4.1 多维 tensor 实际上放在哪里

虽然我平时看到的是二维或三维 tensor，但底层 storage 通常是一段一维内存。多维索引如何映射到底层位置，取决于起始 offset 和各个维度的 stride。

![课件中的 storage、stride 与 tensor layout 示例](/daily/2026/9-17/aims5702-slide-storage-stride.png)

### 4.2 slicing 不一定复制数据

普通的连续 range slicing 可能只创建一个 view，让新 tensor 和原 tensor 共享 storage。因此修改 view 可能影响原 tensor。Boolean mask 或其他 advanced indexing 通常会创建新的 storage，这也是 view 和 copy 在内存行为上的关键区别。

transpose 往往也只是改变 stride，不一定移动数据。之后如果某个操作要求连续内存，就需要考虑 `contiguous`。reshape 能不能直接完成，同样取决于当前布局是否适合。

随机数也有类似的“不要想当然”问题：在同一环境中固定 seed 通常可以复现，但不同操作系统、Python 或 PyTorch 版本不一定产生完全相同的序列。

## 5. Reduction、矩阵乘法与 einsum

### 5.1 常见 reduction

`sum`、`product`、`min`、`max` 和 `argmax` 都可以沿指定维度做 reduction。使用它们时，我需要同时确认输出 shape 和被消掉的是哪一个维度，而不是只看数值是否“看起来对”。

矩阵乘法要求左边矩阵的列数等于右边矩阵的行数。这个维度规则也是 Assignment 1 第一题的基础。

### 5.2 einsum 把数学下标直接写出来

Einstein summation 的核心是：同一项中重复出现的 index 表示求和。它可以写点积、行求和、转置和矩阵乘法；不同的 index 排列则表达不同的输出维度。

![课件中的 Einstein summation 规则示例](/daily/2026/9-17/aims5702-slide-einsum.png)

这正好和我之前在 CS336 里看到的写法接上了：attention、Linear 和各种 tensor contraction，本质上都在用 index 规则表达 shape 之间的关系。

## 6. 为什么老师反复讲 Python coding style

这部分不是装饰。老师说，代码除了要运行正确，还要让别人读得懂、接得上、继续维护。具体包括：

- 避免不必要的 global variable；
- 保持清晰的命名、缩进和合理行宽；
- 给主要函数写 docstring；
- 在 docstring 中说明功能、参数、返回值和可能的错误；
- 按作业要求写 type hints，不能用 `Any`。

Colab 对 type hints 的支持并不完美，但 Assignment 仍然要求函数接口写清楚。这个要求和 CS336 作业很像：接口是给测试代码和其他人看的，不是只给自己临时运行的。

![课件中的函数 docstring 要求](/daily/2026/9-17/aims5702-slide-docstring.png)

## 7. CPU、GPU 与课程资源

CPU 更适合控制流程和较复杂的顺序任务，GPU 更适合大量相似的并行计算。深度学习中一次处理很多数据点或大矩阵时，GPU 能把相似计算并行展开，但 CPU 和 GPU 往往有各自的 memory，数据来回移动也有成本。

老师还从数据规模和 AI 生成内容越来越多的现状讲到课程资源：现实中的数据量很大，课堂不可能提供无限 GPU，因此需要先学会估算 memory cost、理解 tensor layout，再谈模型训练和部署。

![课件中的 CPU/GPU 计算与内存示意](/daily/2026/9-17/aims5702-slide-gpu.png)

## 8. Assignment 1：四个 function 和一次完整提交

### 8.1 我实际要写什么

老师说得很明确，这次作业只需要填写 **4 个 function**，不能为了“补全”而改动更多地方：

1. Question 1 的两层 `for` 循环版本；
2. Question 1 的无 Python loop、使用 tensor / broadcasting 的版本；
3. Question 1 的 `torch.einsum` 版本；
4. Question 2 的无循环 bilinear interpolation 版本。

Question 1 是 pairwise dot-product matrix。输入是形状 `(m, k)` 和 `(n, k)` 的二维 tensor，需要得到每一对向量的 dot product；输入维度不合法时返回 `None`。除非题目另有说明，不能使用 `torch.matmul`、`torch.mm` 或 `@`。

Question 2 是 normalized coordinate `[0, 1]` 下的二维 bilinear interpolation。需要先把 normalized coordinate 映射到网格坐标，再用四个相邻点完成插值；不能写 Python loop，也不能调用第三方插值函数。

### 8.2 提交不能漏最后一步

我会按老师演示的流程提交：先在 Blackboard 的 Assignment 1 页面进入 `View Instructions`，下载并完成 Colab notebook；然后运行所有测试，不改测试代码；最后将 notebook 分别下载为 `.ipynb` 和 `.pdf`，两个文件都上传。

最容易忘的是最后一步：**上传之后还要点击 Submit**。只 upload 文件不算完成提交。老师说可以重复提交；attempt 的具体限制以 Blackboard 页面实际显示为准。作业截止是 **2026 年 9 月 24 日（星期四）**，所以我不能只在本地跑通就算结束。

老师还说这次作业和往年难度基本一致，主要调整了 return type 和描述的清晰度。用 AI 辅助并不是问题，问题是最后必须知道自己写的每一行代码在做什么。

## 9. Quiz 就当作 Assignment 1 后的复习

今天的 quiz 题目覆盖了刚讲过的概念：样本数与复杂度、`float16` 的 bit 分配、`bfloat16` 的动态范围、参数显存估算和 two's complement。

![课堂 quiz：样本数与复杂度](/daily/2026/9-17/aims5702-quiz-complexity.jpg)

![课堂 quiz：two's complement](/daily/2026/9-17/aims5702-quiz-twos-complement.jpg)

老师会改变数字或题目背景，但方法没有变。对我来说，Assignment 1 不是 quiz 之外的额外负担，反而是把这些基础概念练熟的主要机会。

## 10. 我对这节课的整体理解

这节课的内容和 CS336、我之前学过的深度学习确实有重合，但它把注意力放在了容易被跳过的实现基础上：shape 是否匹配、切片到底有没有复制、stride 如何解释、dtype 会占多少内存、函数接口能不能被别人使用。

以后再看网络、attention 或 GPU 优化时，我应该先回到这些问题：输入输出的 shape 是什么，数据在哪个 device，内存是否 contiguous，操作是在做 view 还是 copy，数学上的求和能不能用 broadcasting 或 `einsum` 准确表达。Assignment 1 正好把这些问题集中练一遍。
