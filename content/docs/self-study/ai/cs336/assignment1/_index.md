---
title: "Assignment1 Experiment"
weight: 1
math: true
---
## 7.0 数据集
| 类别 | 数据集名称 | 官方下载地址 | 核心特点 | 作业用途 |
| :--- | :--- | :--- | :--- | :--- |
| 核心入门数据集 | TinyStories V2（GPT4版本） | 训练集：https://huggingface.co/datasets/roneneldan/TinyStories/resolve/main/TinyStoriesV2-GPT4-train.txt<br>验证集：https://huggingface.co/datasets/roneneldan/TinyStories/resolve/main/TinyStoriesV2-GPT4-valid.txt | 1. GPT4生成英文儿童短故事，语料干净、句式简单、语义连贯无冗余噪声<br>2. 训练集约2GB，算力要求极低，消费级GPU/CPU均可30分钟~2小时完成小模型预训练<br>3. 小参数量Transformer即可快速收敛，文本生成通顺，易直观观测训练效果 | A1作业首选入门数据集；用于训练BPE分词器、完成Transformer端到端训练与超参调优，验证模型基础能力 |
| 进阶通用数据集 | OpenWebText（OWT）官方子样本 | 训练集：https://huggingface.co/datasets/stanford-cs336/owt-sample/resolve/main/owt_train.txt.gz<br>验证集：https://huggingface.co/datasets/stanford-cs336/owt-sample/resolve/main/owt_valid.txt.gz | 1. 源自Reddit高赞外链网页文本，通用预训练经典语料，覆盖新闻、百科、博客等多场景<br>2. 语义更复杂，语言分布贴近真实世界<br>3. 课程精简子样本，规避全量几十GB体积，适合入门通用预训练实验 | A1作业进阶实验数据集；在TinyStories验证代码后，在此数据集完成进阶预训练，对比不同超参实验效果 |

工业界主流数据集：

| 数据集 | 规模 | 特点 | 适用场景 |
|--------|------|------|----------|
| FineWeb-Edu | 10T token | 目前业界公认的高质量通用预训练语料，清洗严格、教育类内容占比高，比C4效果更好 | 单卡/多卡训通用大模型，追求SOTA效果 |
| C4 (Colossal Cleaned Common Crawl) | 800GB+ | 经典的清洗后通用网页语料，覆盖全领域，工业界预训练的标准基线 | 通用预训练、复现主流模型 |
| RedPajama | 1.2T token | 完全开源的LLaMA训练语料复刻版，包含书籍、网页、论文、代码等多模态语料 | 复刻开源大模型、多领域预训练 |
| SlimPajama | 627B token | RedPajama的去重清洗版，体积更小、质量更高，适合单卡训练 | 单卡训中等规模模型，平衡质量与体积 |

{{% jupyter "a1.ipynb" %}}