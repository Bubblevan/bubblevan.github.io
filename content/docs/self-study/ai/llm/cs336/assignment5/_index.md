---
title: "Assignment5 Experiment"
weight: 1
math: true
---
## ?.0 数据集
| 类别 | 数据集名称 | 官方下载地址 | 核心特点 | 作业用途 |
| :--- | :--- | :--- | :--- | :--- |
| 补充/评测数据集 | MMLU | Hugging Face 仓库：[https://huggingface.co/datasets/cais/mmlu](https://huggingface.co/datasets/cais/mmlu)<br>CS336 预处理目录：[https://github.com/stanford-cs336/assignment5-alignment/tree/main/data/mmlu](https://github.com/stanford-cs336/assignment5-alignment/tree/main/data/mmlu) | 1. 多学科四选一选择题 benchmark，HF 页标注为 Question Answering / multiple-choice-qa。<br>2. 覆盖大量 subject；HF viewer 显示 59 个 subset，包括 `all`、`auxiliary_train` 和各学科子集。<br>3. 样本字段包括 `question`、`subject`、`choices`、`answer`，适合标准化 factual knowledge 测试。 | optional supplement 中用于评估模型的 **factual knowledge / 知识能力**；通常不是训练主数据，而是对 SFT/DPO 后模型做 benchmark。 |
| 补充/评测数据集 | GSM8K（Grade School Math 8K） | Hugging Face 仓库：[https://huggingface.co/datasets/openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k)<br>CS336 预处理目录：[https://github.com/stanford-cs336/assignment5-alignment/tree/main/data/gsm8k](https://github.com/stanford-cs336/assignment5-alignment/tree/main/data/gsm8k) | 1. 小学数学文字题 benchmark，HF 页标注为 text generation、math-word-problems。<br>2. HF viewer 显示 `main` 和 `socratic` 两个 subset；`main` 约 8.79k 行，train 约 7.47k、test 约 1.32k。<br>3. 每题包含自然语言分步解答和最终答案，适合快速测 reasoning。 | optional supplement 中用于评估 **reasoning / 数学推理能力**；也常被用作快速 sanity check、zero-shot / few-shot eval。 |
| 补充/评测数据集 | AlpacaEval | Hugging Face 仓库：[https://huggingface.co/datasets/tatsu-lab/alpaca_eval](https://huggingface.co/datasets/tatsu-lab/alpaca_eval)<br>CS336 预处理目录：[https://github.com/stanford-cs336/assignment5-alignment/tree/main/data/alpaca_eval](https://github.com/stanford-cs336/assignment5-alignment/tree/main/data/alpaca_eval) | 1. 面向 instruction-following / chatbot 质量的自动评测集。<br>2. HF 仓库由 Tatsu Lab 发布，license 显示为 cc-by-nc-4.0。<br>3. AlpacaEval 论文/说明中常用固定 805 条 instruction，让被测模型生成回答，再由 judge 模型比较胜率。 | optional supplement 中用于评估 **chatbot quality / 指令跟随质量**；CS336 changelog 还提到 optional assignment 中把 AlpacaEval judge 更新为 Llama 3.3 70B Instruct。 |
| 补充/评测数据集 | SimpleSafetyTests | Hugging Face 仓库：[https://huggingface.co/datasets/Bertievidgen/SimpleSafetyTests](https://huggingface.co/datasets/Bertievidgen/SimpleSafetyTests)<br>CS336 预处理目录：[https://github.com/stanford-cs336/assignment5-alignment/tree/main/data/simple_safety_tests](https://github.com/stanford-cs336/assignment5-alignment/tree/main/data/simple_safety_tests) | 1. 小型安全测试集，HF 页显示 default subset 共 100 rows，test split 100 rows。<br>2. 字段包含 `harm_area`、`category`、`prompt` 等；`harm_area` 显示 5 类，`category` 显示 2 类。<br>3. 用少量高风险 prompt 检查模型是否会安全拒答/安全改写。 | optional supplement 中用于评估 **safety / 安全对齐效果**；适合比较 SFT 或 DPO 后模型是否更少输出不安全内容。 |

还有一些开源学生的博客，对于我们的复现有很大意义：
- [xianyu12330](https://github.com/xianyu12330/cs336_assignment5/blob/main/data/alpaca_eval/alpaca_eval.jsonl)
- [slipegg](https://slipegg.github.io/2026/01/26/CS336-assignment5/)
- [yyzhang2025](https://yyzhang2025.github.io/posts/LearningNotes/CS336/Ass05/ass05.html)
- [zhouxin](https://www.zhouxin.space/notes/notes-on-cs336-lecture-4-moe/)
> 唉我图还是太少了，不够图文并茂

## 实现
> 见[仓库](https://github.com/Bubblevan/CS336-A5)。