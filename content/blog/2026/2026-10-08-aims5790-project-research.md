---
schema: bubblevan/v1
id: blog-20261008-aims5790-project-research
content_kind: blog
title: "AIMS5790 项目调研：144 个课题索引、方向选择与复现路线"
date: 2026-10-08
updated: 2026-10-10
status: draft
visibility: public
summary: "记录 AIMS5790 截止日当天的项目筛选背景，保存 144 个课题分类索引、Agent 方向判断、候选项目比较与最小复现路线。"
topics: [AIMS5790, Research, LLM Agents, Agent Infrastructure, RAG, Career Planning]
projects: []
aliases: []
authors: [bubblevan]
---

## 截止日当天为什么要赶这份调研

2026 年 10 月 8 日是 AIMS5790 申请截止日。我当天才发现 CUHK Outlook 的自动转发地址填错，QQ Agent Mail 没有收到学校邮件；临时修正设置后，我仍不确定它能否正常转发，因此简历和项目调研都准备得很赶。这篇文章把当时的两份研究材料并到一个可复习入口里，不把“完成调研”误写成“已提交申请”或“已匹配导师”。

我希望争取一个能与 CUHK 教授合作、可形成实际研究或工程成果的项目。此前简历中的医疗 AI 是积累项目经验的过渡方向，不是我长期想深耕的领域；当时更关注通用 LLM Agent、Agent Infra、RAG、Memory 和后端工程，也希望项目选择不要挤压 2027 年春季的大厂实习准备。如果 AIMS5790 成功匹配，才考虑在 2027 年 1 月 Add/Drop 时再评估是否用它替换数学负担较重的 IERG5350。

> **资料口径：**下面的项目名称、导师和项目类型来自 2026 年 10 月 8 日整理的学校项目清单；分类、优先级、负担估计和复现建议是个人判断，不是学校官方评价。项目是否仍有名额、导师是否接受、是否组队及最后是否提交了某个志愿，都不能由这份调研推出。

> **候选版本说明：**当日的讨论清单把 #92、#59、#84、#41、#124 留在候选池；配套研究指南的 10 项初筛表则把 #92 与 #121 标为拟报第一、第二志愿。两份材料保存的是不同阶段的个人筛选快照，不能据此推断最终 webform 的实际提交内容。

## 一、144 个课题的分类索引

以下保留项目清单中的全部 144 项题目、导师、类型和个人分类标签。分类和“收藏 / 初筛 / 拟报”均为当时个人整理，用于缩小阅读范围；不是项目适配、竞争程度或录取概率的客观评估。


### AIMS5790 2026/27 全部 144 个课题索引

> 学校原始字段：Project #、Name of Faculty Member、Project Title、Project Type；**方向标签和主观优先级为个人添加，并非学校定义**。`P0`/`P1` 与 `收藏` 代表学习偏好，**不代表导师已接收或项目可选/有剩余名额**。项目编号严格保留用于在学校 webform 和相关邮件里查找。原始资料出现部分重复题名（如 #117/#118），保留并不擅自合并。
>
> 配套的方向分析与复现建议见本文第二部分“Agent 技术方向与复现路线”。

### 分类统计

| 个人分类 | 数量 |
| --- | ---: |
| Agent / Harness / Evaluation | 14 |
| RAG / Vector Store / AI Infra | 7 |
| LLM / Safety / Reasoning | 10 |
| Multimodal / Vision / Speech | 12 |
| Business / Other Software | 3 |
| Medical / Biomedical / Scientific Imaging | 48 |
| Robotics / Embodied / Control | 29 |
| Edge / Hardware / Sensors | 15 |
| Materials / Scientific Computing | 6 |
| **合计** | **144** |

### Agent / Harness / Evaluation（14）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 14 | CHENG Hong | Trace-Guided Recursive Self-Improvement of LLM Agent Harnesses | Individual Project | 十项初筛 |
| 51 | KING Kuo Chin Irwin | Policy-as-Code: Turning Written Rules into Executable Compliance Checkers | Individual Project | 参考 |
| 52 | KING Kuo Chin Irwin | Catching the Confident Wrong Answer: An Automatic Grounding Auditor | Individual Project | 十项初筛 |
| 53 | KING Kuo Chin Irwin | Knowing When to Say No: Tool-Using Agents That Detect Impossible Requests | Individual Project | 十项初筛 |
| 74 | LI Yu | Improving the Reliability of LLM Agents on Long-Horizon Scientific Data Analysis Tasks | Individual Project | 十项初筛 |
| 84 | LIU Weiliang | A Self-Correcting LLM Agent for Logistics Optimization Modeling | Team Project | 参考 |
| 90 | LO Chi Lik Eric | Using AI Coding Agent to write high-performance and provable multi-threaded code | Individual/ Team Project | 十项初筛 |
| 91 | LO Chi Lik Eric | AI Investing Agent | Individual/ Team Project | 参考 |
| 92 | LO Chi Lik Eric | Data Agent | Individual/ Team Project | **拟报第1志愿** |
| 121 | XUE Diwen | How Long Can a Website Hold an AI Agent? Measuring the Stopping Rules of LLM Web Agents | Team Project | **拟报第2志愿** |
| 128 | YUAN Wu | Building an Expert-Guided AI Agent | Individual/ Team Project | 十项初筛 |
| 135 | ZHANG Hanrui | LLM Agents for Strategic Persuasion | Team Project | 参考 |
| 136 | ZHANG Hanrui | LLM Agents in Bargaining Games | Team Project | 参考 |
| 142 | ZHANGWeizhao | Autonomous CAE: Agentic Harness for Closed-Loop Composite Prepreg Forming Optimization | Individual Project | 参考 |

### RAG / Vector Store / AI Infra（7）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 16 | CHENG Hong | Tracing Influential Sources in Scientific Papers with Graph and Language Models | Individual Project | 参考 |
| 57 | LEE Pak-Ching Patrick | Learned Correlation-Aware Caching for Ethereum's Key-Value Storage Layer | Individual/ Team Project | 参考 |
| 58 | LEE Pak-Ching Patrick | Lightweight Erasure-Coded Checkpoint Store for Fine-Tuning Small LLMs | Individual/ Team Project | 参考 |
| 59 | LEE Pak-Ching Patrick | Deduplicated Vector Store for Embedding-Heavy Workloads | Individual/ Team Project | 十项初筛 |
| 77 | LIANG Xiao | Private AI Inference Without Seeing the Data: Making SHARK Faster for Transformer Models | Team Project | 参考 |
| 110 | WANG Zhengrong | GPU Memory Systems and Data Placement for AI Workloads | Individual/ Team Project | 参考 |
| 111 | WANG Zhengrong | Profiling and Modeling Emerging AI Workloads on GPUs | Individual/ Team Project | 参考 |

### LLM / Safety / Reasoning（10）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 29 | CHOW Sze Ming Sherman | Cross-Modal Safety in Vision-Language Models | Individual Project | 参考 |
| 30 | CHOW Sze Ming Sherman | End-to-End Private Transformer Inference with Batch Private Lookup | Individual/ Team Project | 参考 |
| 31 | CHOW Sze Ming Sherman | Practical Zero-Knowledge Machine Learning for Verifiable Neural Network Inference | Individual/ Team Project | 参考 |
| 32 | CHOW Sze Ming Sherman | Auditing Practical Machine Unlearning for Large Language Models | Individual Project | 十项初筛 |
| 33 | CHOW Sze Ming Sherman | Continual Unlearning for Large Language Models | Individual Project | 参考 |
| 34 | CHOW Sze Ming Sherman | Privacy Leakage from Text Embeddings: Reconstruction Attacks and Defenses | Individual Project | 参考 |
| 78 | LIU Shengchao | Understand the Reasoning Dynamics in Large Language Models | Team Project | 参考 |
| 83 | LIU Shengchao | Enabling Transformers to Understand the World Model | Team Project | 参考 |
| 85 | LIU Weiyang | Next-generation LLM Architecture Research | Team Project | 参考 |
| 86 | LIU Weiyang | Formal Mathematical Reasoning with Large Language Models | Team Project | 参考 |

### Multimodal / Vision / Speech（12）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 12 | CHEN Xi | Spatial Intelligence in Vision-Language Models for Building Reconstruction | Individual Project | 参考 |
| 15 | CHENG Hong | Robust Detection and Recognition of Handwritten Chinese Text in Noisy Images | Individual Project | 参考 |
| 46 | FU Chi Wing | How VLMs recognize Ambiguous Images? | Team Project | 参考 |
| 54 | KONG Qiuqiang | Audio and Music Generation with Neural networks | Individual Project | 参考 |
| 82 | LIU Shengchao | Multi-scale Video Generation with K-Flow | Team Project | 参考 |
| 87 | LIU Xunying | Benchmark-Based Confidence-Aware Post-Correction for Multilingual ASR | Individual Project | 参考 |
| 89 | LIU Xunying | A Controllable Interaction Planner for Full-Duplex Conversational Speech Generation | Individual Project | 参考 |
| 93 | LO Chi Lik Eric | Ocean Park Dolphin RE-identification and Behavioral Analysis | Individual/ Team Project | 参考 |
| 102 | SUM Kwok Wing Anthony | Food Image Segmentation with Detectron2 | Individual Project | 参考 |
| 104 | TSANG Colin | Self-supervised image super-resolution by AI | Individual/ Team Project | 参考 |
| 107 | WANG Liwei | Narrative-Synchronized Video-to-Music Generation | Team Project | 参考 |
| 108 | WANG Liwei | Unified and Efficient Multi-Task Video Enhancement | Team Project | 参考 |

### Business / Other Software（3）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 50 | HAN Dongkun | AI-Powered Handwritten Math Grading and Personalized Learning Feedback System | Individual Project | 参考 |
| 60 | LI Lingfei | Machine Learning for Financial Applications | Team Project | 参考 |
| 134 | ZHANG Hanrui | Visualized Fair Division | Team Project | 参考 |

### Medical / Biomedical / Scientific Imaging（48）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 1 | CHAN Pui Barbara | Exploring the possibility of using AI to facilitate cell population segmentation and single-Cell target quantification in 3D PDAC Tri-Culture Tumoroids | Individual Project | 参考 |
| 2 | CHAN Pui Barbara | AI-Assisted Drug Testing Analysis of Neuroblastoma Tumoroids for Personalized Medicine | Individual Project | 参考 |
| 3 | CHAN Pui Barbara | Feasibility Assessment of AI-Based Cartilage and Bone Segmentation in Implant-Containing 3D Knee MRI | Individual Project | 参考 |
| 4 | CHAN Pui Barbara | Image segmentation and feature extraction of cells on micropatterns fabricated by the Multiphoton Microfabrication and Micropatterning (MMM) platform | Individual Project | 参考 |
| 5 | CHAN Pui Barbara | Developing an Automated Real-Time Analysis Pipeline for Live-Cell Tracking and Cell-Interface Marker Quantification | Individual Project | 参考 |
| 6 | CHEN Benmei | LLM Agent for Ultrasound Decision Support | Individual Project | 参考 |
| 8 | CHEN Chun | AI-based cough detection and localization for effective infection control | Individual Project | 参考 |
| 13 | CHENG Hong | Fine-Grained Multimodal Medication Recommendation via Natural Language and Structural Alignment | Individual Project | 参考 |
| 20 | CHENG Shing Shin | Evidence-Based Vision-Language Reasoning for Safer Laparoscopic Surgery | Individual Project | 参考 |
| 21 | CHENG Shing Shin | Making Registration Uncertainty Actionable for Image-Guided Surgical Navigation | Individual Project | 参考 |
| 28 | CHENG Shing Shin | Multimodal AI for Understanding Soft Tissue Handling in Robotic Surgery | Individual Project | 参考 |
| 35 | DOU Qi | Preoperative Surgical Planning and Visualization Tool for Liver Surgery | Team Project | 参考 |
| 37 | DOU Qi | Vision-Based Surgical Digital Twin for Tracking Gallbladder Detachment in Laparoscopic Cholecystectomy | Team Project | 参考 |
| 39 | DOU Qi | Topology-Aware Hierarchical Surgical Anatomy Segmentation Using a Vision Foundation Model | Team Project | 参考 |
| 40 | DOU Qi | Endoscopic surgical instrument segmentation based on a vision foundation model | Team Project | 参考 |
| 42 | DOU Qi | Vision-Language Models for Automatic Progress Assessment and Performance Evaluation in Robotic Surgery | Team Project | 参考 |
| 43 | DOU Qi | Adapting Vision-Language Foundation Models for Endoscopic Surgical Video Understanding | Team Project | 参考 |
| 44 | Dou Qi | Predictive AI for Surgical Video Analysis | Team Project | 参考 |
| 61 | LI Yu | Developing Time Aware AI Agents for Longitudinal Electronic Health Record Question Answering | Individual/ Team Project | 参考 |
| 62 | LI Yu | Early Prediction of Acute Respiratory Failure with Multimodal Patient Trajectories | Individual/ Team Project | 参考 |
| 63 | LI Yu | Learning Protein Representations to Decode Antibiotic Resistance | Individual/ Team Project | 参考 |
| 64 | LI Yu | Supporting Antimicrobial Stewardship with AI Agents by Modeling Patient Trajectories | Individual/ Team Project | 参考 |
| 65 | LI Yu | Epitope-conditioned Nanobody CDR Design with an OAS Prior | Individual Project | 参考 |
| 66 | LI Yu | Sequence-based model for L-RNA aptamer design | Individual Project | 参考 |
| 67 | LI Yu | Benchmarking Spatial Transcriptomics Foundation Models Across Spatial and Single Cell Approaches | Individual Project | 参考 |
| 68 | LI Yu | A Hierarchical Spatial Transcriptomics Foundation Model for Retrieval Across Cells Niches and Resolutions | Individual Project | 参考 |
| 69 | LI Yu | A Generalizable Foundation Model for Spatial Transcriptomics Imputation | Individual Project | 参考 |
| 70 | LI Yu | From Video to Clinical Record: An Agentic Multimodal LLM for Automated Colonoscopy Reporting | Individual/ Team Project | 参考 |
| 71 | LI Yu | Generative AI for Therapeutic Peptide Design | Team Project | 参考 |
| 72 | LI Yu | Lightweight Distillation of Large Biological Sequence Language Models | Individual Project | 参考 |
| 73 | LI Yu | Efficient Long-Context Language Models for Biological Sequence Data | Individual Project | 参考 |
| 75 | LI Yu | AI-Based Prediction of Spatially Resolved Cellular Responses to Perturbations | Individual Project | 参考 |
| 76 | LI Yu | Antibody-Aware Deep Learning for HLA Class II Presentation and Immunogenicity Hotspot Prediction | Individual Project | 参考 |
| 79 | LIU Shengchao | RNA Design with 3D Structures | Team Project | 参考 |
| 80 | LIU Shengchao | Utilizing Reasoning with Large Language Models for Metabolic Pathway Planning | Team Project | 参考 |
| 88 | LIU Xunying | Explainable modeling for speech decoding from EEG signals | Individual/ Team Project | 参考 |
| 97 | MAO Chuanbin | An AI-Powered Computational Framework for Simulating the Tumor Microenvironment to Accelerate Anti-Cancer Therapeutics | Team Project | 参考 |
| 103 | SUM Kwok Wing Anthony | Ocular Disease Classification from Fundus Images | Individual Project | 参考 |
| 105 | TSANG Colin | Biomedical images denoising and super-resolution by AI | Individual/ Team Project | 参考 |
| 117 | XU Mengya | Large Vision-Language Model–Guided Standardization of Hemostatic Actions in Endoscopic Submucosal Dissection Through Bleeding Event Understanding | Individual Project | 参考 |
| 118 | XU Mengya | Large Vision-Language Model–Guided Standardization of Hemostatic Actions in Endoscopic Submucosal Dissection Through Bleeding Event Understanding | Individual Project | 参考 |
| 127 | YUAN Wu | MyopiaBench-Agent: A Multimodal Benchmark and Agent Workflow for Myopia Diagnosis | Individual/ Team Project | 参考 |
| 129 | YUAN Wu | How General Are Medical Foundation Models? A Cross-Organ study | Team Project | 参考 |
| 130 | YUAN Wu | From Medical Specialists to Unified Medical AI | Team Project | 参考 |
| 132 | YUAN Wu | Geometry-Guided Registration and Fusion of Multimodal Skin Images | Individual Project | 参考 |
| 133 | YUAN Wu | Ophthalmic World Model for Learning and Predicting Disease Dynamics | Team Project | 参考 |
| 143 | ZHOU Renjie | Deep Learning-Based Feed-Forward Reconstruction for Optical Diffraction Tomography | Individual Project | 参考 |
| 144 | ZHOU Renjie | Self-supervised single-shot autofocusing for Quantitative Phase Microscopy | Team Project | 参考 |

### Robotics / Embodied / Control（29）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 7 | CHEN Benmei | LLM Agent for UAV Inspection in Smart City Environments | Individual Project | 参考 |
| 9 | CHEN Chun | Smart control of indoor environments by IoT and reinforcement learning | Individual Project | 参考 |
| 10 | CHEN Fei | LLM-Robotics: Natural Language Control for Advanced Humanoid Robot Interactive Motion Planning | Individual Project | 参考 |
| 11 | CHEN Fei | VLA-LocoMAN: Learning End-to-End Controllers for Quadruped Robot Loco-Manipulation Tasks | Individual Project | 参考 |
| 17 | CHENG Shing Shin | Learning to Reshape a Magnetic Micro-Robot Swarm in 3D | Individual Project | 参考 |
| 18 | CHENG Shing Shin | Learning Coordinated Dual-Arm Magnetic Manipulation towards Autonomous Robotic Suturing | Individual Project | 参考 |
| 19 | CHENG Shing Shin | Generative Ultrasound World Models for Embodied Ultrasound | Individual Project | 参考 |
| 22 | CHENG Shing Shin | Vision-Language-Action Models for Embodied Robotic Ultrasound Autonomous Scanning | Individual Project | 参考 |
| 23 | CHENG Shing Shin | Dexterous Embodied Actuation for Robotic Ultrasound Intervention | Individual Project | 参考 |
| 24 | CHENG Shing Shin | Uncertainty-Aware Learning of Probe Motion for Intelligent Robotic Ultrasound Scanning | Individual Project | 参考 |
| 25 | CHENG Shing Shin | A Language-Guided Hierarchical Imitation Learning Framework for Flexible Surgical Robots | Team Project | 参考 |
| 26 | CHENG Shing Shin | Physics-Constrained Learning-Based Motion Planning for Continuum Surgical Robots | Individual Project | 参考 |
| 27 | CHENG Shing Shin | Safe Reinforcement Learning for Autonomous Tissue Retraction in Bimanual Robotic Surgery | Individual Project | 参考 |
| 36 | DOU Qi | An Integrated System for Dexterous Manipulation from Human Demonstrations | Team Project | 参考 |
| 38 | DOU Qi | Humanoid Robot Adaptive Auxiliary Control for Elderly Joint Mobility Rehabilitation | Team Project | 参考 |
| 41 | DOU Qi | LLM Agents for Robotic Manipulation: Tool Interfaces and Experience Summarization | Team Project | 参考 |
| 45 | FU Chi Wing | From Sim-to-Real to LEGO-to-Real | Individual/ Team Project | 参考 |
| 47 | HAN Dongkun | Reinforcement Learning for Safe and Efficient Autonomous Driving | Individual Project | 参考 |
| 48 | HAN Dongkun | Robotic Labmate: An LLM-Supported Epistemically Embodied AI Partner for STEM Laboratory Learning | Individual Project | 参考 |
| 49 | HAN Dongkun | Digital Twin and AI-Driven Robot Simulation Platform for Robotics Learning and Experimentation | Individual Project | 参考 |
| 55 | LAU Darwin Tat Ming | Few-Shot Personalized Human Arm Motion Estimation Using Diffusion Policy | Individual Project | 参考 |
| 56 | LAU Darwin Tat Ming | Learning-Based Human Intent Prediction for Shared-Control Teleoperation | Individual/ Team Project | 参考 |
| 100 | REN Hongliang | Vision-Language-Action Model for Autonomous Endoscopy | Individual/ Team Project | 参考 |
| 119 | XU Yunjian | Safe reinforcement learning (RL) and its application on power systems | Team Project | 参考 |
| 120 | XU Yunjian | Safe reinforcement learning (RL) for robotics | Team Project | 参考 |
| 131 | YUAN Wu | Multimodal World Modeling and Predictive Planning for Robotic Skin OCT Scanning | Individual Project | 参考 |
| 137 | ZHANG Li | Automatic reward learning for fast, safe and transferable biomedical microrobot control | Team Project | 参考 |
| 138 | ZHANG Li | AI-Enabled Dual-Scale Embodied Sensing for Autonomous Microrobot Swarms | Team Project | 参考 |
| 139 | ZHANG Li | AI-based State Estimation of Magnetic Microrobots under Degraded Medical Imaging | Individual/ Team Project | 参考 |

### Edge / Hardware / Sensors（15）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 99 | Martin Stolterfoht | Deep Learning-Enhanced Tactile Sensors Integrated with Perovskite Solar Cells for Autonomous Electronic Skin Systems | Team Project | 参考 |
| 101 | SUM Kwok Wing Anthony | Lightweight Model Optimization for Edge Deployment | Individual Project | 参考 |
| 109 | WANG Zhengrong | Agent-Native EDA and RTL Simulation and Debug | Individual/ Team Project | 参考 |
| 112 | XING Guoliang | Synchronization-Aware Multimodal Edge Sensing for AIoT Systems | Individual Project | 参考 |
| 113 | XING Guoliang | LLM Agent for Adaptive Orchestration of Heterogeneous Sensor Systems | Individual Project | 参考 |
| 114 | XING Guoliang | Physics-Informed Synthetic Sensor Data Generation for Human Activity Recognition | Individual Project | 参考 |
| 115 | XING Guoliang | Edge–Cloud Open-Set Recognition with Foundation Models | Individual Project | 参考 |
| 116 | XING Guoliang | Multimodal Sensor Fusion with Foundation Models for Smart-Home Activity Recognition | Individual Project | 参考 |
| 122 | XUE Diwen | Real-Time Generative Traffic Shaping on Edge Hardware | Team Project | 参考 |
| 123 | YAN Zhenyu | Long-term personal memory from mobile and wearable data | Individual/ Team Project | 参考 |
| 124 | YAN Zhenyu | Proactive on-device AI agents | Individual/ Team Project | 参考 |
| 125 | YAN Zhenyu | Long-term spatial memory | Individual/ Team Project | 参考 |
| 126 | YAN Zhenyu | Indoor 3D sensing platform | Team Project | 参考 |
| 140 | ZHANG Li | Lightweight On-Device AI for Wearable Biomedical Sensing | Team Project | 参考 |
| 141 | ZHANG Li | Multimodal Sensor Fusion for AI-Enabled Wearable Biomedical Sensing | Team Project | 参考 |

### Materials / Scientific Computing（6）

| # | 导师 | 学校原题目 | 类型 | 个人标记 |
| --- | --- | --- | --- | --- |
| 81 | LIU Shengchao | Utilizing Reasoning with Large Language Models for Chemical Reaction Planning | Team Project | 参考 |
| 94 | LONG Yi | Data-Driven Design of Hydrogel-Based Phase-Change Systems for Personal Thermal Management | Individual Project | 参考 |
| 95 | LONG Yi | Machine Learning-Driven Design of Spectrally Selective Metasurfaces for Thermal Management | Individual Project | 参考 |
| 96 | LONG Yi | Machine Learning-Assisted Design of Electrochromic Smart Windows | Individual Project | 参考 |
| 98 | Martin Stolterfoht | Unveiling Degradation Mechanisms in Perovskite Solar Cells via AI-Assisted Analysis | Individual/ Team Project | 参考 |
| 106 | TSANG Colin | Solving partial differential equations by AI | Individual/ Team Project | 参考 |


### 数据一致性检查

- 原始表共 144 行，编号 1–144。
- 每个编号出现一次，且个人分类互斥、覆盖全部项目。
- 所有项目名称、导师与 Individual/Team 类型按提供的清单逐行转录；没有用网络信息替换这些字段。

## 二、Agent 技术方向与复现路线

下面保留配套研究指南的方向分析、资源入口、初次复现建议、个人筛选表、最小交付包模板和版本风险记录。指南把“能够运行一次”与“复现论文结论”区分开：需要固定代码、数据、模型、配置和测试集，保存逐题轨迹，再用外部评测说明改动前后的差异。


### Agent 技术版图与复现入口：从 AIMS5790 的 144 个课题出发

> **定位**：个人本地学习地图，不是给导师的申请书，也不是已完成的技术成果报告。以 2026/27 CUHK AIMS5790 的 144 个项目名称为真实选题样本，理解 Agent 及其相邻 AI/Systems 研究方向。侧重 Agent 开发、Agent Infra、后端、评测与可靠性；不再把医疗 AI 当长期主线。**所有复现建议均为待做计划，不代表已经复现、已获得结果或项目匹配成功。**
>
> **资料日期：2026-10-08**。项目表只提供编号、导师、标题、Individual/Team 类型；**没有**项目说明书、预计工作量、申请人数、录取概率、导师承诺、指定基线。这些信息不得从题目臆测为既成事实。

#### 0. 一页结论：我以后用什么准则选一个方向

当前就业目标优先级：Agent Runtime / Harness → Agent Reliability / Evaluation → Data Agent / Web Agent / Coding Agent → RAG/Memory/向量存储和后端系统 → 可迁移的大模型/多模态基础。**医疗 AI、生物 AI、机器人、端侧硬件暂不作为主线**。学术题目很热门、或技术栈看起来高级，并不意味着适合投入一个学期。

为防止同一时间启动十几个仓库，每次只允许：

1. **1 条深挖主线**：从上游仓库的官方脚本、原数据、原评分器做 mini reproduction，产生可复现数字和失败日志；持续 2–6 周，时间随实际进度调整。
2. **1 条短探索**：用 1–3 天理解新方向的任务形式、可执行 benchmark、Baseline trace 和失败类型；超时则记录阻塞并暂停。
3. **其余只进方向池**：保存官方链接、进入条件、是否可本地运行、对应 AIMS 项目编号。没有具体行动价值时不 clone。

每个复现须具备以下证据才可写进简历：`upstream commit / dataset version / model / reproducible command / baseline metric / own change / paired evaluation / limitations`。只把 demo 跑通，不能包装成论文复现成功。

#### 1. 用 AIMS5790 144 个题目看技术版图

下表的编号都来自学校项目原始清单；分类是个人建立的索引，**不是 CUHK 官方学科分类**。个别题目跨多个领域，这里只给一个主类；项目名称、导师和 Individual/Team 类型的完整分类索引见本文第一部分。

| 技术群 | 课题编号示例 | 真正研究什么 | 我对它的态度 |
| --- | --- | --- | --- |
| Agent Harness / Evaluation | #14 #52 #53 #74 #121 | 工具执行、轨迹、判断何时停止、审计错误、长任务稳定性 | **P0** |
| Data Agent / Tools | #92 #51 #128 | 自然语言转数据库操作，工具约束与多步骤分析 | **P0**；#128 要谨慎看领域 |
| Web Agent | #121 | 浏览器动作、任务判定、停止/继续、环境可重复性 | **P0** |
| Coding Agent | #90 | 修改真实仓库、运行测试、评测补丁；#90 另有并发正确性 | **P1**；形式化证明风险高 |
| Retrieval / Vector Infra | #59 #16 #58 | 索引、向量存储、去重、缓存、checkpoint、数据来源追踪 | **P1** |
| Model / Safety / Reasoning | #32 #33 #34 #78 #85 | Unlearning、隐私、推理动力学、新模型架构 | **P2**；技术可学但近期不主攻 |
| Vision / Speech / Multimodal | #46 #89 #87 | 多模态模型、实时对话、音频/语音系统 | **P2** |
| 医疗/生物 | #6 #61 #70 #127 等 | 医疗 Agent、医学模型、生物基础模型 | **不作为职业默认方向** |
| 机器人/具身 | #7 #10 #41 等 | 操作控制、VLA、模仿学习、运动规划 | **暂不投入** |
| 端侧/传感器/硬件 | #101 #109 #124 等 | 端侧推理、EDA、物理感知 | **暂不投入** |
| 材料/科学计算 | #81 #94 #106 等 | 科学任务建模、物理/材料问题 | **暂不投入** |

**重要**：#59 属于偏数据系统的课题，不意味着要自己发明 embedding 模型；#90 的“provable multi-threaded code”更接近程序验证和并发系统，而不只是让 Coding Agent 写代码；#32 的 machine unlearning 是模型研究，不是 Agent Memory 的遗忘机制。

#### 2. P0-1：Data Agent / 数据分析智能体（对应 #92）

#### 2.1 它和普通 RAG 有什么区别

输入不是“找一段文本再回答”，而可能是“请分析某个跨表业务问题”。Agent 需要识别数据库模式（schema）、规划操作、生成和执行 SQL/脚本、根据返回结果纠错、解释数值，必要时输出图表。任务成功要由**实际执行结果**核验，而不能只检查 SQL 看起来像不像答案。

核心概念：Text-to-SQL、Schema Linking、Query Planning、DB sandbox、查询副作用和权限隔离、Execution Feedback、SQL Dialect、事务/超时、数值验证。技术栈基础：Python + SQL + SQLite/DuckDB，逐步拓展 PostgreSQL 和 SQL 工具接口即可；不必第一天上 Snowflake/BigQuery。

#### 2.2 论文、可运行项目、难点

| 资源 | 它是什么 | 首次学习怎么用 | 坑 |
| --- | --- | --- | --- |
| [BIRD-SQL](https://bird-bench.github.io/) | 数据库内容较真实的 Text-to-SQL Benchmark | 读数据结构，选小型公开子集，用 Execution Accuracy 入门 | 完整数据规模和环境不小 |
| [Spider 2.0](https://github.com/xlang-ai/Spider2)（ICLR 2025 Oral） | 企业级多步骤 Text-to-SQL / Agent 工作流 | **先试 Spider2-DBT 的 DuckDB 子集**，再考虑 Lite/Snow | 官方已多次更新 split、评分与云数据访问；注意 Snowflake 账户问题 |
| [Spider 2.0 项目页](https://spider2-sql.github.io/) | benchmark/论文/数据说明 | 确认当前任务设置，不用旧文章的样本量代替现版 | 原 632-task setting 已重组为 DBT/Lite/Snow |
| [DuckDB](https://duckdb.org/) | 本地分析数据库 | 本地搭 2–3 表和可执行分析任务，排查 SQL Agent | 不等于 Spider 官方评测结果 |

**第一次小复现**：运行官方样例 baseline → 冻结少量任务 ID → 保存 `question/schema/tools/actions/sql/result/gold/checker` → 按执行结果算成功率，并人工复核 5 个失败例。比较「只生成一次 SQL」与「执行后根据数据库错误信息重试一次」，同时记录 SQL 安全边界、工具次数、延迟和 token 成本。

**可交付简历证据**：可运行 Data Agent Demo + 公开 benchmark 报告 + 失败分类 + SQL 执行沙盒/审计机制，最好有命令一键重现。**不要**把“用了 LangChain 调用 SQLite”写成企业级 Data Agent。

#### 3. P0-2：Web Agent / 浏览器智能体（对应 #121）

#### 3.1 核心问题不是“会点网页”

Agent 读页面状态、选择点击/输入/导航，重复观察直至完成任务。但实际场景存在跳转、登录、时间限制、重复操作、失败页面、不可完成任务。#121 特别关注 **Stopping Rules（何时应该终止）**：继续尝试的收益是否超过成本，是否应该报告失败、请求授权或交还用户。

核心概念：Observation / Action / Episode、DOM 或 A11y Tree、Browser State、Success Verifier、Budget、Stop/Abort/Escalate、任务无解、循环检测、环境重置。**不要只拿浏览器 Agent 的最终话术当成功证明**。

| 资源 | 它是什么 | 开始路径 | 注意 |
| --- | --- | --- | --- |
| [BrowserGym](https://github.com/ServiceNow/BrowserGym) | Web Agent 环境及多个 benchmark 的统一接口 | 先安装 core + MiniWoB 小任务，了解 observation/action 契约 | 真实 WebArena 环境配置更重 |
| [AgentLab](https://github.com/ServiceNow/AgentLab) | 用 BrowserGym 做实验、复现、轨迹分析 | 优先从现成 agent + sample task 看 trace | 运行大批 benchmark 可能用 Ray、需额外资源 |
| [WebArena](https://github.com/web-arena-x/webarena) | 自托管网站上的真实任务集 | 理解 task success verifier，再择期搭完整环境 | 上游也推荐使用 BrowserGym/AgentLab 跑实验 |
| [MiniWoB++](https://miniwob.farama.org/) | 较轻的合成网页交互任务 | 先做少量网页动作测试/循环案例 | 合成任务不能替代真实网页能力 |

**第一次小复现**：从 BrowserGym/MiniWoB 中固定 10–20 个任务；跑最简单的 baseline；人为引入“目标不存在/不可用/权限不足/卡在循环”场景（新构造样本与官方测试集分开报告）。设置步骤上限与无进展检测，比较 baseline 和改动之后的完成率、误停率、无效动作次数、平均步数和执行耗时。

**可交付简历证据**：Web Agent 的 Stop Decision 模块、failure trace viewer、任务成功判定与 paired baseline 评测。可着力研究：在保证成功率的同时，减少无效重复操作，而不是只把 max_steps 调小。

#### 4. P0-3：Agent Harness / 可靠性 / 评测（对应 #14 #52 #53 #74）

这其实是你的**可迁移主线**，不限定医疗、金融或网页。

- **Runtime/Harness**：管理模型调用、工具可用性、执行状态、预算、取消、恢复、trace、权限、安全边界。
- **Reliability**：Agent 明明有能力却失败在哪里？工具出错能否恢复？把不可完成任务当可完成怎么办？
- **Evaluation**：正确结果不能靠自我声明，应使用外部 truth、可执行环境、日志、配对评测、消融。
- **Grounding**：回答中的每条重要 claim 是否真的有检索证据，证据是否被曲解？
- **Self-Improvement**：利用失败轨迹提出策略修改，并在冻结的独立样本上验证改善；不等于改了 prompt 就是成功。

| 资源 | 对应问题 | 第一轮目标 |
| --- | --- | --- |
| [RAGChecker](https://github.com/amazon-science/RAGChecker) | #52 claim-level grounding / RAG 诊断 | 理解 retriever / generator 错误拆分、claim-level entailment |
| [τ³-bench](https://github.com/sierra-research/tau2-bench) | #53 任务规则、工具、用户交互 | 先从 mock / text 域和可执行验证起步；保留官方 version |
| [AgentDojo](https://github.com/ethz-spylab/agentdojo) | Tool-using Agent 的越权与 prompt injection | 先了解攻击与防御评测，不在正式网站试攻击 |
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | 长期上下文、跨 session、时间推理 | 对已有 Memory 实验做质量与时间信息检查 |
| [LoCoMo](https://github.com/snap-research/locomo) | 长期交互记忆 | 注意数据集很小，分数受 scorer/judge 口径影响 |
| [Mem0 OSS](https://github.com/mem0ai/mem0) | 可集成的 memory 服务组件 | 不要把其商业版分数当 OSS 复现结果 |

**第一次小复现**：先选一个**已知、可执行、外部可验证**的任务集合，重现 Single Agent baseline，保存逐步 trace，再添加一个改动（如提前拒绝、工具故障重试、答案证据审计），最后用事先未查看的测试题验证，而不是在同一批 bad cases 上持续调参。

重点日志字段：`task_id, split, seed, agent_version, model, tool_registry_hash, step, tool_call, observation_ref, terminal_status, evidence_ref, verifier_result, cost`。在真实用户数据场景，应脱敏并限制留存。

#### 5. P1-1：Coding Agent（对应 #90）

Agent 不只是给出一段代码，而是需要在仓库里定位问题、修改文件、执行测试、产出 patch，并由外部测试验证是否解决。#90 额外提到多线程代码的**高性能**与**可证明正确**，后者引入并发模型/程序验证的学习负担，所以不该直接拿通用 SWE-bench 通过率替代它的全部目标。

| 资源 | 用来学什么 | 推荐顺序 |
| --- | --- | --- |
| [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) | 极简 Agent loop、bash 工具、环境隔离、轨迹 | 首选阅读和最小运行；比维护大型框架负担小 |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) | Issue → Patch → Test 的可执行评测 | 从少量已知可运行的任务开始；不要按旧教程盲跑全量 |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | 工具界面与更复杂的代理执行 | 理解架构；其文档也推荐先尝试 mini-SWE-agent |

**小复现**：一条真实公开 issue，冻结仓库 commit 与测试环境，先无模型人工跑通复现/测试，再让 Agent 尝试、保存 patch/test logs。避免把测试失败、依赖失败、编译失败和真实逻辑错误混为一类。输出 `resolved@1 / test pass / cost / step count / patch diff`。

#### 6. P1-2：向量存储 / RAG / Memory Infra（对应 #59 #58 #16）

该方向侧重“数据怎么存、怎么检索、成本/时延/一致性怎样权衡”，不只是如何调用 embedding API。

| 资源 | 学什么 | 产出 |
| --- | --- | --- |
| [FAISS](https://github.com/facebookresearch/faiss) | Exact search、ANN、索引/速度/质量权衡 | 1 组可复现向量检索 baseline |
| [DiskANN](https://github.com/microsoft/DiskANN) | SSD/内存向量检索与索引策略 | 阅读论文/架构，复杂实验留给深挖阶段 |
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | 记忆检索实际能否回答/弃答 | 关联 recall、temporal 与答案指标 |

**小复现**：对同一批 embedding 比较 brute-force 与 FAISS 方案，记录 Recall@K、查询时延、构建耗时、内存和磁盘；实验去重时，明确区分 exact duplicate、near-duplicate、同义不同文本，不可只看储存空间节省而不测召回退化。

#### 7. P2：模型方向与专项选题（对应 #32 #78 #85）

这是**了解生态而非当前职业主线**：

- **#32 Machine Unlearning Audit**：评测删除/遗忘某些训练知识之后，模型是否继续泄漏或背诵；与删除 Agent Memory entry 不同。参考 [MUSE](https://github.com/swj0419/muse_bench) 的多维评测；不要把“模型答不出来”当充分遗忘证明。
- **#78 LLM Reasoning Dynamics**：研究推理过程的表现、置信、错误演化；可能含大量实验解释与模型内部分析。先阅读论文与实验，不急于从头训大模型。
- **#85 Next-generation LLM Architecture**：Transformer/注意力、KV Cache、推理效率、训练稳定性，可能涉及重数学和重算力；若仅求 Agent 开发岗位，不必在实习季新开这条长期实验线。
- **多模态/语音**：#46 #87 #89 可用于了解 VLM、ASR、对话交互。若明确不投多模态岗，可以只记录方向，不启动工程。

#### 8. 10 个初筛项目与个人决策记录

**这是 2026-10-08 的个人选择背景，不是招生事实。** 表格中的数学/工作量和竞争判断均是依据题目和技术性质的**主观风险估计**；没有课程项目说明书，不能写成官方要求。第一轮保留：#14、#32、#52、#53、#59、#74、#90、#92、#121、#128。并不因为项目名称含 LLM 就默认匹配求职目标。

| # | 导师 | 类型 | 技术入口 / 意义 | 数学/理论风险 | 工程与时间风险 | 可以争取的成果 | 个人选择 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 14 | CHENG Hong | Individual | Trace 驱动 Harness 改进 | 中 | 高 | 自改进/验证实验 | 备选：竞争信息未知 |
| 32 | CHOW Sze Ming Sherman | Individual | LLM Unlearning Audit | 中高 | 中高 | MUSE 类审计报告 | 暂不主攻 |
| 52 | KING Kuo Chin Irwin | Individual | Grounding Auditor | 低–中 | 中 | Claim-level 审计器 | 强备选 |
| 53 | KING Kuo Chin Irwin | Individual | 不可完成任务判断 | 低–中 | 中 | 工具任务拒绝检测 | 强备选 |
| 59 | LEE Pak-Ching Patrick | Individual/Team | 向量存储去重 | 中 | 中高–高 | 索引与性能报告 | 强备选 |
| 74 | LI Yu | Individual | 长任务科研 Agent | 中 | 中高 | 长任务可靠性评测 | 领域依赖待核实 |
| 90 | LO Chi Lik Eric | Individual/Team | Coding Agent + 并发程序 | 中高 | 高 | 可复现 patch/并发测试 | 降权，防数学和验证负担 |
| 92 | LO Chi Lik Eric | Individual/Team | Data Agent | 低–中 | 范围未明确 | 数据 Agent、SQL/工具评测 | **拟报第一志愿** |
| 121 | XUE Diwen | Team | Web Agent 停止规则 | 低–中 | 中（复杂部署可能高） | Web benchmark、stop controller | **拟报第二志愿** |
| 128 | YUAN Wu | Individual/Team | Expert-guided Agent | 低–中 | 中 | 专家反馈 Agent | 医疗/领域倾向待核实 |

**选课和学分边界**：志愿只代表申请，不能代表匹配成功；不接受推荐调剂则 webform 对应选 `No`。若 AIMS5790 成功匹配且准备替换 IERG5350，**必须等正式选课信息及 Programme Office 的答复**，不能因意向而自行提前退掉 RL。此前学校邮件提示 Project I 在 Term 2 普通 add/drop 中不可按一般课程修改，需视为有约束的学期承诺。

#### 9. 复现的“最小可交付包”模板（可复制到每个新仓库）

```text
research/<direction>/<project>/
├── README.md                    # 我在回答什么问题，官方论文/仓库/版本
├── evidence/
│   ├── source-manifest.md       # 官方 commit / release / license / README
│   ├── environment.md           # 平台、依赖、模型与数据校验和
│   └── provenance.md            # 哪些是上游，哪些是自己的改动
├── configs/                     # 模型参数、seed、task ids、tool budgets
├── scripts/                     # 原版运行与评分的薄包装脚本
├── results/
│   ├── baseline/                # 冻结原版输出
│   └── candidate/               # 只变更一个研究变量
├── analysis/
│   ├── paired_failures.md       # 逐题失效原因
│   └── final_report.md          # 结果、约束、负结论
└── demo/                        # 可选：展示而非替代评测
```

每个项目 README 至少回答：

1. **任务**：输入、目标、动作与外部成功判断是什么？
2. **Baseline**：作者原仓库可运行的是哪一条路径？是否真复现成功？
3. **数据**：来自哪里？train/dev/test 如何分？是否可能污染？
4. **指标**：为什么使用这些指标？是否包含拒答/停止/耗时/成本？
5. **变更**：自己只改了什么？有没有偷换模型、样本或评分器？
6. **失败**：逐题 trace 能否解释提升或退化？
7. **展示**：面试时怎样在 3 分钟内验证核心能力？

用下面的状态命名，避免将想法写成已完成：

```yaml
status: queued  # queued | paper_read | env_ready | baseline_running | reproduced | evaluated | paused
upstream_repo: null
upstream_commit: null
paper: null
dataset: null
dataset_version: null
model: null
seed: null
hardware: null
reproduced_metric: null
independent_eval: false
contribution: null
blocker: null
next_action: null
```

#### 10. 个人探索节奏：不再拿“多 clone 仓库”当学习成果

建议按“**主线深入 + 两次短探索**”进行，而不是排一个需要每天同时推进四个项目的日程表：

- **主线**：当前 Agent Harness / Evaluation 已有较多工程积累。把一套真实外部 benchmark 的 baseline、trace、改动前后对比打通。
- **短探索 1：Data Agent**：Spider2-DBT / DuckDB 可运行任务；弄懂 Text-to-SQL 为什么需要数据库实际执行和环境隔离。
- **短探索 2：Web Agent**：BrowserGym + 小型网页任务；明确 action/observation/stop，并保存逐步失败 trace。
- **以后**：mini-SWE-agent/SWE-bench；FAISS/DiskANN；模型安全与 Unlearning。只在确定投相关岗位、或拿到导师项目后深入。

探索最重要的是**减少未来选项目的盲区**，而非“立刻补齐所有垂直经验”。如果一个方向没有官方数据/代码/评测路径，先记为 `research-only`，不要让 Coding Agent 自创方法并在小样本上自评成功。

#### 11. 经过核对的官方入口与版本风险（更新于 2026-10-08）

| 方向 | 当前建议的官方入口 | 版本/可运行性注意 |
| --- | --- | --- |
| Text-to-SQL | https://github.com/xlang-ai/Spider2 | 采用 DBT/Lite/Snow 新划分；Snowflake 账号访问曾中断，不要默认全量可跑 |
| BIRD-SQL | https://bird-bench.github.io/ | 大数据集，先了解 split 和 SQL executable judge |
| Web Agent | https://github.com/ServiceNow/BrowserGym | 从小任务入手 |
| Web Agent Lab | https://github.com/ServiceNow/AgentLab | 用于实验管理和 trace |
| WebArena | https://github.com/web-arena-x/webarena | 官方建议配合 BrowserGym/AgentLab |
| Tool-Agent | https://github.com/sierra-research/tau2-bench | 项目当前呈现 τ³-bench；旧 `tau-bench` README 提醒旧任务未更新 |
| RAG Auditor | https://github.com/amazon-science/RAGChecker | 核对 judge 与依赖后再复现 |
| Security Agent | https://github.com/ethz-spylab/agentdojo | 隔离环境运行安全用例 |
| Coding Agent | https://github.com/SWE-agent/mini-swe-agent | 新版已迭代，pin commit；它不是 SWE-bench 的评分器 |
| Coding Benchmark | https://github.com/SWE-bench/SWE-bench | 官方 scorer, container 环境与任务版本要冻结 |
| Memory | https://github.com/xiaowu0162/LongMemEval | 数据集和评分版本有更新，包括 V2 |
| Memory | https://github.com/snap-research/locomo | 不要混淆 LoCoMo 的 category/scorer 口径 |
| Vector Search | https://github.com/facebookresearch/faiss | 可用小规模 exact/ANN 实验入门 |
| Vector Index | https://github.com/microsoft/DiskANN | 当前仓库已更新到 DiskANN3，旧 C++ 代码在历史分支 |
| LLM Unlearning | https://github.com/swj0419/muse_bench | 模型遗忘与 Agent Memory 删除概念不同 |

**当地运行约束**：有 Windows/WSL 与单卡可用，但要优先选择离线/local model 路线；不要默认必须购买 OpenAI API。某些 benchmark 上游使用 API，需单独核对本地 Qwen 接入是否改变原论文复现条件。若改变，只能称为本地迁移实验，不能宣称 strict reproduction。

#### 12. 变更日志 / 防过时信息

- 2026-10-08：建立方向地图；从 144 个 CUHK 课题建立九类主题索引，单独保存全部原题名和项目类型。
- 2026-10-08：针对个人简历与学习目标，拟选择 #92 Data Agent、#121 Web Agent Stopping Rules。**没有从这里推断申请已提交、项目已匹配或 IERG5350 已退课**。
- 下一次更新：如果 AIMS5790 匹配结果公开，更新真实状态、导师要求、团队规模、工作量与实际交付；如果更换求职方向，重新标记 P0/P1/P2，不改写历史状态。
