---
schema: bubblevan/v1
id: career-search-r1-card
content_kind: star
title: Search-R1 — 项目卡片（占位）
date: 2026-07-19
status: seed
visibility: private
projects:
  - search-r1
career:
  target_roles:
    - ml-engineer
    - research-engineer
  competencies:
    - reinforcement-learning
    - retrieval-augmented
    - reasoning
---

## 目标

复现 Search-R1（检索增强的强化学习推理），通过 RL 训练 LLM 在推理过程中自主调用搜索引擎，实现更强的 multi-hop 推理能力。

## 技术路线（计划）

- 复现 Search-R1 核心训练流程
- RL 训练 LLM 的工具使用（搜索 API 调用）
- 对比基线：纯 LLM 推理 vs 检索增强推理
- 评估 benchmark 上的 multi-hop QA 表现

## 当前状态

项目启动中，论文阅读与实验规划阶段。

## 关联学习

- Hello Agent：Agent 工具调用理论基础
- 技术报告与前沿论文：R1 / Search-R1 系列
