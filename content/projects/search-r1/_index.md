---
schema: bubblevan/v1
id: project-search-r1
content_kind: project
title: Search-R1 复现
date: 2026-07-19
updated: 2026-07-19
status: seed
visibility: public
summary: 复现 Search-R1：通过强化学习训练 LLM 在推理中自主调用搜索引擎，实现检索增强推理。
topics:
  - rl
  - llm
  - retrieval
project:
  role: ML Engineer
  stage: plan
  highlights: []
  tech_stack: []
  repository:
  demo:
---

## 目标

复现 Search-R1（检索增强的强化学习推理），通过 RL 训练 LLM 在推理过程中自主调用搜索引擎。

## 路线图

1. 精读 Search-R1 论文及 R1 系列相关工作
2. 搭建 RL 训练环境（GRPO / PPO）
3. 集成搜索 API（Brave / SerpAPI）
4. 在 multi-hop QA benchmark 上评估

## 相关资源

- Search-R1 Paper
- GRPO / DeepSeek-R1
