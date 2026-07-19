---
schema: bubblevan/v1
id: project-stablepay-arch
content_kind: project
title: StablePay 架构
date: 2026-07-19
updated: 2026-07-19
status: draft
visibility: public
projects:
  - stablepay
---

## OpenClaw 插件体系

StablePay 通过 OpenClaw Gateway 加载自定义插件，实现 Agent 驱动的支付流程。插件通过 `openclaw.plugin.json` 声明配置，Gateway 启动后自动加载。

## 支付幂等性

待补充。

## 限流策略

待补充。
