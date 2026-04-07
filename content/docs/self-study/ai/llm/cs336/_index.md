---
title: "动手学大模型"
weight: 1
---

[官方仓库](https://github.com/stanford-cs336/)因为我的VPN到期了所以暂时打不开，不慌我们可以先看看[隔壁gitee](https://gitee.com/stanford-cs336-learning)

在进入CS336之前，确保下列技术栈：
- Python
- PyTorch

https://stanford-cs336.github.io/spring2025/
https://github.com/stanford-cs336/spring2025-lectures
https://gitee.com/stanford-cs336-learning

来自[这就是小c](https://docs.qq.com/s/HPpBdg5v5VwDPt3ZqafRKG/folder/aOjtgwKGfLxI)的腾讯文档讲义分享
还有即将飞升讲师的[群友Zou的github主页笔记](https://yyzhang2025.github.io/posts/LearningNotes/LLM-Series/)

CS336 Spring 2025 一共 19 讲，主线是：**Basics → Systems → Scaling → Data → Alignment → Guest lectures**。
## 课程主线
### 1–2：最前面的基础层
1. **Lecture 1 — Overview, tokenization**
   课程总览 + tokenizer/BPE/词表这些最基础的输入处理。BPE、Tokenizer 封装，基本就在这条线上。 
2. **Lecture 2 — PyTorch, resource accounting**
   PyTorch 基础、张量、模型/优化器/训练循环，以及训练语言模型时最核心的两类资源：**内存**和 **FLOPs**。官方还特别说明：这讲**不会展开讲 Transformer 细节**，Transformer 更多放到 A1 handout 和实现里。 

### 3–4：模型结构本体
3. **Lecture 3 — Architectures, hyperparameters**
   Transformer 架构设计与关键超参数，比如层数、宽度、头数、上下文长度、FFN 比例等。 
4. **Lecture 4 — Mixture of experts**
   MoE（混合专家）架构，讲怎么在参数规模很大时只激活一部分参数来提高效率。 

### 5–8：系统与加速
5. **Lecture 5 — GPUs**
   GPU 基础，为什么深度学习训练依赖 GPU、GPU 上的并行和内存层次大概怎么影响性能。 
6. **Lecture 6 — Kernels, Triton**
   kernel 编程和 Triton，和后面自己实现高效 attention/kernel 优化直接相关。 
7. **Lecture 7 — Parallelism**
   并行训练第一讲，通常对应数据并行/模型并行/流水线并行等大模型训练方式。 
8. **Lecture 8 — Parallelism**
   并行训练第二讲，继续展开多机多卡训练时的实现与权衡。 

### 9–12：规模、推理、评测
9. **Lecture 9 — Scaling laws**
   Scaling laws 第一讲：模型大小、数据量、算力和效果之间的关系。 
10. **Lecture 10 — Inference**
    推理阶段：生成、解码、吞吐/延迟、服务化时的性能问题。 
11. **Lecture 11 — Scaling laws**
    Scaling laws 第二讲，更系统地讲如何拟合和使用 scaling law 来预估训练收益。 
12. **Lecture 12 — Evaluation**
    模型评测：怎么衡量语言模型质量、任务表现和实际效果。 

### 13–14：数据工程
13. **Lecture 13 — Data**
    预训练数据第一讲：数据来源、构建数据集、预处理。 
14. **Lecture 14 — Data**
    预训练数据第二讲：更偏工程的一面，比如清洗、过滤、去重这类会直接影响模型性能的步骤。课程作业 A4 也明确要求把 Common Crawl 变成可用预训练数据，并做 filtering / deduplication。 

### 15–17：对齐与强化学习
15. **Lecture 15 — Alignment - SFT/RLHF**
    对齐第一讲：SFT（监督微调）和 RLHF 的整体框架。 
16. **Lecture 16 — Alignment - RL**
    对齐第二讲：更偏强化学习部分。 
17. **Lecture 17 — Alignment - RL**
    对齐第三讲：继续讲 RL 视角下的对齐训练。作业 A5 也对应“用 SFT 和强化学习训练模型做推理/数学题”。 

### 18–19：客座讲座
18. **Lecture 18 — Guest Lecture by Junyang Lin**
    客座讲座，官方课表列出嘉宾是 **Junyang Lin**，但课表页没有再展开主题标题。 
19. **Lecture 19 — Guest Lecture by Mike Lewis**
    客座讲座，嘉宾是 **Mike Lewis**，课表页同样没有给出更细的主题标题。 

### 总结五阶段
* **1–4**：先把 LM 的基本构件搭起来
* **5–8**：让它在 GPU/多卡上高效跑起来
* **9–12**：理解规模、推理和评测
* **13–14**：理解数据从哪来、怎么处理
* **15–17**：理解对齐、SFT、RLHF/RL
* **18–19**：工业界/研究界客座分享  

## 作业主线

