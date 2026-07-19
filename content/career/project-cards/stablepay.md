---
schema: bubblevan/v1
id: career-stablepay-card
content_kind: star
title: StablePay 项目卡片
date: 2026-07-19
status: draft
visibility: private
projects:
  - stablepay
career:
  target_roles:
    - backend
    - agent-engineer
    - golang-developer
  competencies:
    - microservices
    - payment-system
    - agent-integration
    - cloud-native
---

## 一句话定位

为 AI Agent 构建的去中心化支付网关系统，基于 CloudWeGo 微服务生态，集成 OpenClaw Agent 插件与 Solana 链上结算。

## 技术架构

### 后端微服务（Go / CloudWeGo）

| 服务 | 职责 | 技术点 |
|---|---|---|
| API Gateway | 统一入口、鉴权、限流、路由（19 条规则） | Hertz, JWT, Nonce 防重放, Rate Limit |
| Payment Service | 支付链路、幂等控制、状态流转 | 幂等 Nonce, RocketMQ, COLA 分层 |
| DID Service | 去中心化身份 `did:solana` 的生成/查询/验签 | Kitex RPC, Ed25519 |
| Blockchain Adapter | Solana RPC 封装、SPL Token 转账、热钱包 | Solana Web3, Fee Payer 审计 |
| Verification Service | 购买验证、证明生成、奖励发放 | RocketMQ Consumer, X API |
| Query Service | 余额/交易/收益查询、账本同步 | Chain Balance, Upsert 幂等 |

### Agent 侧（TypeScript）

- **OpenClaw Plugin**：18 个可调用工具，钱包管理、支付策略、Onboarding、Doctor
- **MCP SDK**：同一套工具暴露为 MCP Server，支持 Claude Code / Codex / Cursor

### 基础设施

- MySQL + Redis + RocketMQ
- Docker + Kubernetes (ACK)
- Solana Devnet/Mainnet

## 核心贡献

1. **API Gateway 鉴权与限流体系**：JWT 签名验签 + Nonce 防重放 + 令牌桶限流，支撑 19 条路由策略
2. **支付幂等性方案**：基于 Nonce 的幂等控制，防止重复扣款
3. **区块链适配层**：抽象 Solana RPC，支持 SPL Token 转账、热钱包补贴、交易审计
4. **Agent 支付链路**：实现 x402 Payment Required → Agent 自动支付 → 重试资源访问的完整闭环
5. **COLA 分层架构落地**：在 Go 项目中实践 Adapter / Application / Domain / Infrastructure 四层架构

## 学习沉淀

- [CloudWeGo 后端复盘](/docs/web/languages/golang/cloudewego/) — DDD/COLA 分层、Hertz、Kitex、微服务全链路
- [OpenClaw Plugin 自救](/blog/2026/2026-06-07-stablepay-onboard/) — Agent 插件开发实战
- [Solana 转账实战](/blog/2026/2026-06-07-solana-transfer/) — 链上交互

## 可量化指标

| 维度 | 数据 |
|---|---|
| 微服务数量 | 6 个独立服务 + 1 个 Agent 插件 |
| API 路由数 | 19 条 |
| OpenClaw 工具数 | 18 个 |
| 支付链路 | 端到端 x402 闭环 |
| 测试覆盖 | Payment / DID / Verification 核心链路已测试 |

## 面试要点

- 为什么选择 CloudWeGo 而不是 Gin/Echo？（高性能、微服务生态、Kitex RPC 集成）
- 幂等性怎么做的？（Nonce + DB 唯一约束 + 状态机）
- Agent 支付和传统支付的区别？（无浏览器交互、x402 协议、链上结算）
- 限流怎么设计的？（令牌桶、429 排障经验）
