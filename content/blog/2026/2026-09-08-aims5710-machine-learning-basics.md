---
schema: bubblevan/v1
id: blog-20260908-aims5710-machine-learning-basics
content_kind: blog
title: "AIMS5710：机器学习基础、回归与分类"
date: 2026-09-08
updated: 2026-09-08
status: draft
visibility: public
summary: "记录 AIMS5710 第一讲对机器学习基础、线性回归、逻辑回归、softmax 分类和 Homework 1 要求的整理。"
topics: [AIMS5710, Machine Learning, Deep Learning, CUHK]
projects: []
aliases: []
authors: [bubblevan]
---

今天整理 AIMS5710《Deep Learning Fundamentals and Theories》的课程介绍、Machine Learning Basics 讲义和 Homework 1。下面的公式和结论来自课程材料；还没有把 Homework 1 做成完整解答。

## 先把机器学习写成一个映射问题

课程从一个基本目标开始：利用训练数据学习一个映射函数，把输入特征向量映射为目标输出。若函数形式固定，可以用参数向量 \(\theta\) 表示待学习的模型，并通过训练集

\[
D=\{(x^{(1)},y^{(1)}),(x^{(2)},y^{(2)}),\ldots,(x^{(m)},y^{(m)})\}
\]

估计一个预测函数 \(\hat f\)。函数的参数形式会影响模型能否表达数据中的关系，这部分设计通常需要结合问题本身的知识。

监督学习的输入是成对的特征和目标。目标是连续值时，问题通常称为回归；目标是有限个离散类别时，问题通常称为分类。课程给出的通用流程是：定义输入与输出、选择函数形式、定义代价函数、优化参数，然后在未见过的样本上测试。

## 线性回归把预测写成参数和特征的内积

在线性回归中，给特征补上常数项 \(x_0=1\)，模型可以写成

\[
h_\theta(x)=\theta^T x=\theta_0+\theta_1x_1+\cdots+\theta_nx_n
\]

课程使用平方误差代价函数衡量训练集上的预测偏差：

\[
J(\theta)=\frac{1}{2}\sum_{i=1}^{m}\left(h_\theta(x^{(i)})-y^{(i)}\right)^2
\]

学习参数就是最小化这个代价函数。梯度下降从一组初始参数开始，沿负梯度方向更新：

\[
\theta_j\leftarrow\theta_j-\alpha\frac{\partial J(\theta)}{\partial\theta_j}
\]

讲义还比较了三种更新粒度：每轮使用全部训练样本的 batch gradient descent、每轮只使用一个样本的 stochastic gradient descent，以及取两者之间的 mini-batch gradient descent。SGD 单次更新通常更快，但参数可能在最小值附近振荡；mini-batch 是实际训练中常见的折中。

## 逻辑回归用 sigmoid 表示二分类概率

线性模型的输出没有范围限制，直接拿来表示二分类结果不合适。逻辑回归先计算 \(\theta^Tx\)，再通过 sigmoid 函数映射到 \([0,1]\)：

\[
h_\theta(x)=g(\theta^Tx)=\frac{1}{1+e^{-\theta^Tx}}
\]

这个连续输出可以解释为样本属于正类的置信度或概率。对标签 \(y\in\{0,1\}\)，课程把单个样本的概率写成

\[
p(y\mid x;\theta)=h_\theta(x)^y\left(1-h_\theta(x)\right)^{1-y}
\]

整个训练集的似然取对数后，乘法会变成求和，参数可以通过梯度上升最大化 log likelihood。Homework 1 进一步要求推导“sigmoid 假设配合 MSE/L2 损失”时的梯度，并讨论为什么这种损失组合通常不如二元交叉熵合适。

## softmax 把线性得分变成多分类概率

多分类时，每个类别先有一个线性得分 \(\Theta_j^Tx\)，再通过 softmax 归一化为类别概率：

\[
p(y=j\mid x;\Theta)=\frac{\exp(\Theta_j^Tx)}{\sum_{l=1}^{k}\exp(\Theta_l^Tx)}
\]

这些概率之和为 1。课程对 softmax 使用交叉熵代价函数，并用梯度下降更新所有类别的参数；即使某个训练样本只属于一个类别，其他类别对应的参数也会在同一次更新中发生变化。

## Homework 1 的要求与待确认事项

下面是 `homework_1.pdf` 中的课程作业要求，不是我额外添加的个人计划：

- 第 1 题（30 分）：给定两个样本和三个类别的 softmax 参数，计算归一化交叉熵、三个类别参数的负梯度，以及学习率为 0.1 时的一次梯度下降更新。
- 第 2 题（40 分）：推导逻辑分类假设配合 MSE/L2 损失时的梯度，并讨论不应这样组合的原因。
- 第 3 题（30 分）：为题目给出的 1D 和 2D 数据设计特征变换，使变换后的数据可以线性可分。

提交与格式方面，我在这份 PDF 中看到的是：到 Blackboard 查看截止时间并提交；截止后有 4 小时宽限；其他迟交按 0 分处理；结果可以保留分数或四舍五入到 3 位小数。PDF 没有明确写“可以使用 LaTeX”，所以这件事仍应以 Blackboard 或老师的最新通知为准。

课程介绍页还写了“AI 只能在明确致谢的情况下使用”，并给出了课程层面的迟交说明。它与 Homework 1 的具体表述不完全一致，实际提交前需要以 Blackboard 上当前作业页面为准。

目前状态是：课程基础概念已经整理，Homework 1 还没有开始推导和计算。
