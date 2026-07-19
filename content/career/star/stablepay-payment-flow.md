---
schema: bubblevan/v1
id: star-stablepay-rate-limit
content_kind: star
title: StablePay 支付幂等与限流排障
date: 2026-07-19
status: draft
visibility: private
projects:
  - stablepay
career:
  target_roles:
    - backend
  competencies:
    - troubleshooting
    - system-design
    - payment
star:
  situation: >
    StablePay 支付链路在上线测试阶段遇到 429 Rate Limit 错误，同时存在重复支付风险。
    作为后端负责人，需要排查限流根因并设计幂等性方案。
  task: >
    1. 定位 429 错误的触发条件和频率
    2. 设计支付幂等性方案防止重复扣款
    3. 确保限流不影响正常支付链路
  action: >
    - 分析 API Gateway 限流中间件（令牌桶算法），定位到特定支付端点触发 429
    - 在 Payment Service 中引入 Nonce 幂等控制：DB 唯一约束 + 状态机
    - 调整限流阈值，区分 Agent 调用与普通 API 调用的限流策略
    - 添加支付链路全流程日志追踪
  result: >
    - 429 错误率降至零，支付链路稳定运行
    - 幂等方案通过重复提交测试，零重复扣款
    - 限流策略支持 19 条路由差异化配置
  metrics:
    - 429 错误率：从高频触发降至 0
    - 幂等测试通过率：100%
  followups:
    - Payment Service 内部 DID 二次验签仍为 TODO 占位
    - 限流策略可进一步支持动态调整
---

## Situation

StablePay 支付链路在上线测试阶段遇到 429 Rate Limit 错误，同时存在重复支付风险。作为后端负责人，需要排查限流根因并设计幂等性方案。

## Task

1. 定位 429 错误的触发条件和频率
2. 设计支付幂等性方案防止重复扣款
3. 确保限流不影响正常支付链路

## Action

- 分析 API Gateway 限流中间件（令牌桶算法），定位到特定支付端点触发 429
- 在 Payment Service 中引入 Nonce 幂等控制：DB 唯一约束 + 状态机
- 调整限流阈值，区分 Agent 调用与普通 API 调用的限流策略
- 添加支付链路全流程日志追踪

## Result

- 429 错误率降至零，支付链路稳定运行
- 幂等方案通过重复提交测试，零重复扣款
- 限流策略支持 19 条路由差异化配置

## Lessons Learned

- 微服务场景下的限流需要分层设计：网关层 + 服务层
- 幂等性是支付系统的底线，Nonce + DB 约束是最小可行方案
- Agent 的调用频率与传统用户不同，限流策略不能一刀切
