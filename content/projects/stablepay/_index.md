---
schema: bubblevan/v1
id: project-stablepay
content_kind: project
title: StablePay
date: 2026-03-11
updated: 2026-07-19
status: active
visibility: public
summary: 支付与 Agent 网关项目，集成 OpenClaw 插件体系实现自动化支付流程。
topics:
  - payment
  - agent
  - backend
project:
  role: Backend / Agent Infrastructure
  stage: active
  highlights:
    - OpenClaw 插件开发与支付网关集成
    - 幂等性设计与 429 限流排障
    - Solana 链上转账集成
  tech_stack:
    - OpenClaw
    - Node.js
    - Solana Web3
  repository:
  demo:
---

## 项目背景

StablePay 是一个支付与 Agent 网关项目，通过 OpenClaw 插件体系实现自动化支付流程编排。项目涉及支付网关后端、OpenClaw 插件开发、Solana 链上交互以及限流/幂等性等基础设施问题。

## 个人角色

负责后端与 Agent 基础设施部分，包括 OpenClaw 插件架构设计、支付幂等性方案、速率限制调优以及与 Solana 链的集成。

## 相关博文

- [StablePay 初始笔记](/blog/2026/2026-03-11-stablepay-initial/)
- [OpenClaw Plugin 自救](/blog/2026/2026-06-07-stablepay-onboard/)
- [Solana 转账实战](/blog/2026/2026-06-07-solana-transfer/)
