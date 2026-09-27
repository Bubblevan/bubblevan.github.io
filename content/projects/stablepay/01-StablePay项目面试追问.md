---
schema: bubblevan/v1
id: project-stablepay-agent-commerce-project
content_kind: project
title: StablePay Agent Commerce 项目面试追问
linkTitle: 01 · 项目面试追问
weight: 10
aliases:
  - /projects/stablepay/stablepay-agent-commerce-project/
date: 2026-09-19
updated: 2026-09-19
status: draft
visibility: public
projects:
  - project-stablepay
summary: 基于 StablePay 当前代码、测试和 Git history 维护的 Agent Commerce 项目面试追问文档。
topics:
  - stablepay
  - agent-commerce
  - payment
  - backend
  - project-review
---

> **文档定位**：这里只回答“这个项目实际上做了什么、为什么这样做、如何证明”。每道题优先用“30 秒回答”给结论，再按需展开“深挖 / 源码落点 / 证据 / 当前边界”。通用概念统一放在 [02 · Agent Commerce 通用八股](/projects/stablepay/02-agent-commerce通用八股/) 中。

## 面试前的事实纪律

### 0.1 状态标签

- **IMPLEMENTED**：当前 `HEAD` 的代码、测试、脚本或契约可以直接证明。
- **IN PROGRESS**：代码已有，但默认配置未启用、仍在迁移/联调，或只完成了部分边界。
- **PLANNED**：总体设计中提出、当前没有对应实现，或当前实现尚未覆盖该能力的完整闭环。

### 0.2 事实矩阵

| 能力 | 状态 | 直接证据 |
| --- | --- | --- |
| Hertz API Gateway：路由、鉴权、重放保护、限流、Kitex 下游适配 | **IMPLEMENTED** | `api-gateway/internal/app/bootstrap.go`、`api-gateway/internal/adapter/http/router.go` |
| DID 注册、`did:solana:<base58-pubkey>`、Ed25519、时间窗、nonce | **IMPLEMENTED** | `did-service/internal/application/did_app_service.go:349` |
| Payment：金额、PaymentSignature、nonce、幂等、余额、链上调用、状态轮询 | **IMPLEMENTED** | `payment-service/internal/application/service/payment_service.go:310` |
| Solana SPL Token、Mint、ATA、fee payer、base64 transaction、Devnet 确认 | **IMPLEMENTED** | `blockchain-adapter/internal/infrastructure/blockchain/transaction_builder_impl.go` |
| 业务 minor unit → SPL raw unit 的边界转换 | **IMPLEMENTED** | `blockchain-adapter/internal/domain/vo/token_amount.go`、commit `30b10067` |
| `payment_events`、RocketMQ producer/consumer、购买投影、proof、event replay 幂等 | **IMPLEMENTED** | `payment-service/internal/adapter/mq/producer.go`、`verification-service/internal/infrastructure/messaging/rocketmq_consumer.go` |
| Agent Payment Harness：policy intent、DID approval、TTL、Redis `GETDEL` | **IMPLEMENTED（默认关闭）** | `payment-service/internal/application/service/agent_payment_harness.go`、`payment-service/config/config.yaml` |
| Commerce Runtime S1：Acquisition Contract、CommerceEpisode、状态机、EpisodeEvent、DecisionProposal、Runtime Guard、replay | **IMPLEMENTED** | `commerce-runtime/internal/contract`、`internal/episode`、`internal/decision`、`internal/application` |
| S1 Episode Projection + Event 的 MySQL 原子提交、版本控制、请求/动作幂等 | **IMPLEMENTED** | `commerce-runtime/internal/infrastructure/mysql/repository.go`、`migrations/001_create_commerce_runtime.sql` |
| append-only LedgerEntry、Budget Projection、reserve/release/settle/refund、`consumed/available/sunk_cost`、`RefundReusable` | **IMPLEMENTED** | `commerce-runtime/internal/ledger/ledger.go`、`ledger/ledger_test.go` |
| Runtime-owned PaymentIntent、EconomicIdentityKey、RequestFingerprint、CredentialRef | **IMPLEMENTED** | `commerce-runtime/internal/payment/intent.go`、`application/payment_runtime.go` |
| MerchantDID / CapabilityID / PayeeDID 分离、payment authorization guard | **IMPLEMENTED** | `commerce-runtime/internal/decision/payment_guard.go`、`internal/adapters/kitex_payment.go` |
| Payment pending/failed/unknown/confirmed、unknown reconciliation、exact idempotent redelivery | **IMPLEMENTED** | `commerce-runtime/internal/application/payment_runtime.go`、`internal/reconciliation/reconciliation.go` |
| Entitlement binding：`ENTITLEMENT_VALID/INVALID/UNKNOWN` | **IMPLEMENTED** | `commerce-runtime/internal/adapters/adapters.go`、`internal/application/payment_runtime.go`、commit `2a3b8e2` |
| KitexPaymentAdapter、canonical PaymentService contract mapping | **IMPLEMENTED** | `commerce-runtime/internal/adapters/kitex_payment.go`、`kitex_payment_test.go` |
| MySQL finance transaction：EpisodeEvent、LedgerEntry、PaymentIntent 原子持久化 | **IMPLEMENTED** | `commerce-runtime/internal/infrastructure/mysql/repository.go:470`、`migrations/001_create_commerce_runtime.sql` |
| Refund accounting semantics、compensation ledger fact | **IMPLEMENTED** | `commerce-runtime/internal/ledger/ledger.go`；不等于 external refund workflow |
| `MerchantCapability` domain、MerchantDID / CapabilityID / PayeeDID 独立语义、结构化字段校验 | **IMPLEMENTED** | `commerce-runtime/internal/catalog/catalog.go`、`catalog_test.go` |
| Catalog canonical snapshot/hash、immutable version history、current-version pointer | **IMPLEMENTED** | `internal/catalog/catalog.go`、`internal/repository/inmemory.go`、`internal/infrastructure/mysql/repository.go` |
| `DiscoveryQuery` 从 Acquisition Contract 派生、hard eligibility filter、deterministic ranking、stable tie-breaker | **IMPLEMENTED** | `internal/catalog/catalog.go`、`internal/catalog/discovery.go` |
| CandidateSet 持久化、`FactsRef`、`PayloadHash`、CandidateSet expiry、discovery replay | **IMPLEMENTED** | `internal/catalog/catalog.go`、`internal/application/service.go`、`candidate_sets` migration |
| `SELECT_MERCHANT` membership/snapshot/validity guard、hallucinated/filtered merchant rejection | **IMPLEMENTED** | `internal/decision/decision.go`、`internal/application/service.go`、`s3_catalog_test.go` |
| Episode catalog snapshot binding、immutable CandidateSet payee resolution、S3 → S2 PaymentIntent Payee consistency guard | **IMPLEMENTED** | `internal/episode/episode.go`、`internal/application/payment_runtime.go` |
| `NO_ELIGIBLE_CANDIDATE` deterministic terminal path、MySQL Catalog / CandidateSet persistence | **IMPLEMENTED** | `internal/application/service.go`、`internal/infrastructure/mysql/repository.go`、`s3_integration_test.go` |
| Merchant Invoke、真实 402 consumption、Delivery Validator、完整同商户/跨商户 recovery | **PLANNED** | S4 及后续能力；S3 只完成 trusted structured discovery |
| LLM DecisionProvider、RAG、长期 Memory、Workflow learning、Self-Evolution | **PLANNED** | 当前仍是 deterministic provider/core；后续能力见总体 TRD |

### 0.3 从 Git history 讲真实迭代

不能倒装成“最初就设计好了完整 Commerce Runtime”。真实叙事是：

1. `ce3be348`：基础微服务迁移、单服务单测和跨服务契约检查具备。
2. `8cc16ff`：本地六服务、Devnet wallet、RocketMQ nameserver/topic 联调暴露问题，补运行前置检查。
3. `8c537015`：deterministic plane 的真实 E2E 入口收敛，覆盖 MySQL、Redis、RocketMQ、六服务和 Solana Devnet，并验证支付重试、购买投影、事件 replay。
4. `30b10067`：真实链路暴露业务金额与 SPL raw unit 的语义边界，新增 `BusinessMinorToTokenRaw` 和回归测试。
5. `d338353`：新增独立 `commerce-runtime` S1 Episode Core，落地 Acquisition Contract、Episode、DecisionProposal、Event Trace 和持久化边界。
6. `0e5c615`：补齐 S1 验收债务，加入 MySQL 原子提交、并发/幂等集成测试和 deterministic S1 flow。
7. `f5e9435`：S2 core 落地 append-only Ledger、Budget Projection、PaymentIntent、deterministic payment runtime 和 reconciliation。
8. `4e4c87a`：code review 暴露 transport / identity / factual-action / crash-window 问题，production payment boundary 收紧为 Kitex adapter，并补齐 S2 hardening。
9. `2a3b8e2`：pre-S3 semantic cleanup，明确 HTTP adapter 只是 optional/test，修正 Entitlement UNKNOWN、CapabilityID/PayeeDID 与 business money 语义。
10. `7ecc5c1`：S3 初版落地 trusted Merchant Catalog、structured Discovery、CandidateSet 和 selection guard。
11. `90e9ce3`：S3 final acceptance 修复 current/deactivation 语义、候选有效期检查、discovery replay、shared Merchant/Payee identity 和 MySQL acceptance tests。
12. 当前：S3 Catalog/Structured Discovery 已冻结；Merchant Invoke、402 consumption、Delivery loop 和完整 Agent Commerce Loop 仍未实现。

### 0.4 当前验证记录

- `commerce-runtime` 当前测试套件通过，覆盖 adapters、payment runtime、ledger、reconciliation、MySQL repository、proposal guard 和 S1 episode core。
- S2 测试覆盖 reserve/release/settle/refund、PaymentIntent identity/expiry、Kitex canonical mapping、authorization guard、unknown reconciliation、crash-window exact redelivery、failure/expiry compensation 和 entitlement binding。
- `0e5c615` 的 S1 InnoDB 验收路径继续保留；S2 新增 `internal/infrastructure/mysql/s2_integration_test.go` 覆盖 finance transition 的原子持久化。
- S3 测试覆盖 hard eligibility、deterministic ranking、stable tie-breaker、immutable version/current pointer、inactive/deprecated 不回退、CandidateSet hash/expiry、selection guard、Payee binding、NO_ELIGIBLE terminal path、discovery replay 和 MySQL persistence/concurrency。
- 六服务 deterministic plane 的契约检查、单测和 Real Devnet E2E 验收脚本仍是 S0 基线；S2 Payment Adapter + S3 Catalog 不能等同于一次已经接通真实 Merchant Invoke / 402 / Delivery 的 Commerce E2E。

## 第一轮：项目全貌与支付主链

下面按真实面试的自然追问链组织。主回答控制在 30 秒到 2 分钟，追问用于继续展开。

### Q1：30 秒介绍一下 StablePay

#### 30 秒回答

StablePay 原来解决的是 Agent 如何通过 DID 身份发起一次可验证的付费请求：Gateway 验签，Payment Service 做金额、nonce、幂等和余额校验，Blockchain Adapter 在 Solana Devnet 上执行 SPL Token 转账，随后通过 RocketMQ 把支付结果投影到 Verification Service，提供购买证明。

我参与的重点是把这条链迁移到 CloudWeGo 的服务边界，并通过真实 Devnet E2E 把 Gateway、DID、Payment、Blockchain、RocketMQ 和 Verification 串起来。期间实际处理过 Gateway exact body、Gateway/payment nonce 分离、RocketMQ readiness、event replay 和业务 minor unit 到 SPL raw unit 的边界问题。

现在已经进入 S3：S1 管 Contract、Episode、Event，S2 管 append-only Ledger、PaymentIntent、授权 guard、reconciliation 和 deterministic Payment Adapter，S3 管 trusted Merchant Catalog、structured Discovery、CandidateSet 和 selection guard。Merchant Invoke、真实 402 consumption、Delivery Validator 和 recovery loop 仍从 S4 开始，所以不能包装成完整 Agent Commerce Loop。

#### 深挖

当前系统可以看成确定性支付平面：Hertz Gateway 接收 HTTP 请求，GatewaySignature 保护整个 HTTP 请求；PaymentSignature 绑定 Agent、商户、金额、币种、签名交易哈希和业务 nonce；DID Service 负责 `did:solana:<pubkey>` 与 Ed25519 验证；Payment Service 保存状态、做 Redis nonce/MySQL 幂等并调用 Blockchain Adapter；Adapter 负责 SPL Token、ATA、Mint、fee payer、交易序列化和 Devnet 确认；成功事件进入 `payment_events`，Verification Service 建立购买投影。

这证明了 Agent 可以完成一次可审计支付；S1 把“支付之后如何继续推进”抽成 Episode Core，S2 又把资金事实和支付尝试放进 Runtime 控制，S3 再把商户能力目录和结构化候选选择纳入 trusted facts。当前 Runtime 能原子提交 EpisodeEvent、LedgerEntry、PaymentIntent、CandidateSet，执行 payment authorization、unknown reconciliation、entitlement binding 和 catalog/payee consistency guard；但尚未把 Merchant Invoke、真实 402 consumption、Delivery Validator 和 recovery 接成完整业务链。Payment Harness 仍作为旧付款意图治理边界存在，且默认关闭。

#### 架构展开

```text
Agent / Skill / E2E Client
        │ HTTP + GatewaySignature
        ▼
Hertz API Gateway
  ├─ raw body hash / DID auth / gateway nonce / rate limit
  └─ Kitex RPC proxy
        ├─ DID Service
        ├─ Payment Service
        ├─ Verification Service
        └─ Query Service

Payment Service
  ├─ PaymentSignature / business nonce
  ├─ MySQL payment + idempotency
  ├─ balance / optional Agent Harness
  └─ Kitex → Blockchain Adapter → Solana Devnet
                                      └─ SPL transfer / confirmation
        │
        └─ RocketMQ payment_events
             ▼
        Verification Service → Purchase Projection / proof

Commerce Runtime
  ├─ Contract / Episode
  ├─ Trusted Merchant Catalog / current version
  ├─ DiscoveryQuery / hard filter / deterministic ranking
  ├─ CandidateSet facts_ref / payload_hash / expiry
  ├─ SELECT_MERCHANT Proposal / membership guard
  ├─ immutable catalog snapshot / Payee resolution
  ├─ Decision Proposal / Runtime Guard
  ├─ EpisodeEvent
  ├─ append-only Ledger / Budget Projection
  ├─ PaymentIntent / authorization guard
  ├─ Reconciliation / entitlement binding
  └─ deterministic Kitex Payment Adapter
             ↓
       StablePay Payment Plane
```

#### 源码落点

`api-gateway/internal/app/bootstrap.go`、`payment-service/internal/application/service/payment_service.go:310`、`payment-service/internal/adapter/mq/producer.go:53`、`verification-service/internal/infrastructure/messaging/rocketmq_consumer.go:91`、`scripts/test-deterministic-e2e.ps1`。

#### 当前边界

S3 已实现 trusted Catalog 和 structured Discovery，但不能说已完成 Merchant Invoke、真实 402 consumption、Delivery Validator、同/跨商户 recovery、RAG、Memory 或完整 Agent Commerce Loop；也不要说支付成功就是 Agent 任务完成。

### Q2：这个项目到底解决什么问题？

#### 30 秒回答

要区分：

- **Payment Goal**：把某个金额结算给某个收款方，并能查询交易状态和证明。
- **Acquisition Goal**：为了完成父 Agent 的有限子任务，发现合适能力，调用商户，遇到 402 后在预算和授权内付款，再验证交付是否满足契约。

当前 StablePay 已经较完整地解决 Payment Goal；S1/S2/S3 已把 Acquisition Goal 的 Contract、Episode、预算事实、支付尝试、reconciliation、entitlement binding 和 trusted structured discovery 落进 Runtime Core，但还没有 Merchant Invoke 和 delivery loop。当前系统表达的是：

```text
请求能力 → Contract → Catalog filter/rank → CandidateSet → select → 402 → pay → settlement → verify purchase → delivery
```

它现在不仅能确认钱是否结算和是否有购买记录，还能区分 reservation、settlement、refund、sunk cost、unknown outcome、entitlement binding，以及基于可信 Catalog 的候选资格和版本快照；但仍不能完成真实 merchant invoke、402 quote 消费、交付质量验证、跨商户 recovery 或 Parent Agent 的整体自然语言任务。

#### 源码落点

`payment-service/internal/application/service/payment_service.go:480` 的 402 requirement；`commerce-runtime/internal/catalog/catalog.go`、`internal/catalog/discovery.go`；`internal/application/service.go:178` 的 discovery；`internal/application/payment_runtime.go:77` 的 PaymentIntent/预算入口；`internal/application/payment_runtime.go:548` 的 Entitlement binding。

#### 当前边界

S3 Merchant Catalog 是 trusted structured discovery，不是 RAG；也不是 Merchant Invoke 或 Delivery Validator。Payment/Entitlement factual actions 已有 Runtime-owned 边界，但真实 delivery quality 和 recovery 仍未实现。

### Q3：为什么原来的支付链路不算真正的 Agent Loop？

#### 30 秒回答

“用了模型”不是 Agent Loop 的判断标准。核心是同一个有边界的过程里，Observation 是否改变了下一步 Action：

```text
State → Action → Environment → Observation → Decision → Next Action
```

旧支付链路主要闭合支付事务；S1/S2/S3 现在已经由独立 Runtime 记录 Observation、校验 Proposal、推进 Episode、写入 EpisodeEvent/LedgerEntry/CandidateSet，并把 catalog、payment、entitlement factual actions 收回 Runtime。S3 已完成“可信目录→结构化筛选→候选集→受 guard 约束的选择”，但真实 402 consumption、merchant invoke 和 Delivery Validator 尚未接入，因此“发现商户→付款→验证交付→Retry / Ask / Stop / Switch Merchant”的完整闭环仍是 **PLANNED**。

#### 面试官继续追问

**怎么证明不是日志？**

后一个 Action 必须依赖前一个 Observation。例如 `DELIVERY_INVALID` 必须改变同一 Episode 的下一步为允许集合中的 retry 或 stop，并落到权威状态和事件中。只把错误写日志、下一次仍盲目付款，不算 Agent Loop。

#### 源码落点

旧支付侧证据是 `payment-service/internal/application/service/payment_service.go:480`、`verification-service/internal/application/service.go:38`；S1/S2/S3 Runtime 证据是 `commerce-runtime/internal/episode/episode.go:193`、`commerce-runtime/internal/decision/decision.go:151`、`commerce-runtime/internal/application/payment_runtime.go:77`、`commerce-runtime/internal/application/service.go:178`。

### Q4：为什么要增加 Commerce Runtime，而不是直接把 LLM 塞进 payment-service？

#### 30 秒回答

资金副作用必须由确定性代码控制。模型可以理解目标、解释 402、在合格候选间提出建议，但不能直接修改状态机、预算、支付金额、DID 授权、重试次数或调用 Blockchain Adapter。

```text
LLM proposes
Runtime validates
Deterministic Plane executes
Event Log records
```

当前 Payment Service 已有一个较小的 Agent Payment Harness：`Normalize → Policy → Approval → Execute`。它会根据金额上限、商户 allowlist、TTL 和 DID 用户确认生成 intent；执行 Payment 时用 Redis `GETDEL` 一次性消费，并再次比对 Agent、Skill、金额和币种。S2 又把 PaymentIntent、授权、提交、状态查询、reconciliation 和 entitlement verification 收进 Commerce Runtime 的 deterministic application service；S3 再把 Catalog eligibility、CandidateSet membership 和 selected Payee binding 收进同一条受控边界。

但 `payment-service/config/config.yaml` 中 `agent_harness.enabled: false`、`require_intent_for_payment: false`。准确说法是“治理代码已实现，默认处于迁移/观察模式”，不是“所有支付已强制经过 Harness”。Harness 也不等于完整 Commerce Runtime。

S1/S2/S3 把“模型只能提议、Runtime 才能提交”继续收紧：`DecisionProvider` 只能返回 `DecisionProposal`；`CommitProposal` 会拒绝 `RESERVE_BUDGET`、`PAYMENT_*`、`VERIFY_ENTITLEMENT` 等 runtime-owned factual actions；`SELECT_MERCHANT` 也只能引用已持久化 CandidateSet 中的成员，不能让模型直接写 PayeeDID。真正的 PaymentIntent、LedgerEntry、PaymentOutcome、Entitlement fact 和 Catalog/CandidateSet fact 只能由 deterministic runtime/repository methods 产生，并通过对应 guard 和事务写入。Runtime Guard 还会在 adapter call 前校验金额、Payee、Quote、reservation、deadline、attempt 和 authorization。

#### 源码落点

`payment-service/internal/application/service/agent_payment_harness.go:61`、`:174`；`payment-service/internal/infrastructure/redis/redis.go:72`；`payment-service/internal/application/service/payment_service.go:351`；`commerce-runtime/internal/application/service.go:141` 的 `runtimeOwnedProposalAction`；`commerce-runtime/internal/application/payment_runtime.go:141`、`:271`、`:548`；`commerce-runtime/internal/decision/payment_guard.go`；`commerce-runtime/internal/repository/repository.go:51`。

### Q5：现在真实的一次支付请求到底怎么跑？

#### 30 秒回答

```text
E2E client
  → API Gateway
  → Gateway DID 验签 / Gateway nonce
  → Payment Service Kitex
  → business amount / PaymentSignature / nonce / idempotency / balance
  → DID Service / Blockchain Adapter
  → Solana Devnet SPL settlement
  → Payment status polling
  → RocketMQ payment_events
  → Verification purchase projection
  → /verify 或 /verify/proof
```

Query Service 是并行查询面，不是每笔购买投影必经的下游：Gateway 把 `/balance`、`/transactions`、`/revenue` 路由到 Query；支付状态由 Payment 查询，购买证明由 Verification 查询。

| 步骤 | 输入 | 输出 | 失败模式 |
| --- | --- | --- | --- |
| Gateway | method/path/query/raw body、DID headers | canonical、下游请求 | body 改变、时间窗、nonce replay、限流 |
| Payment | Agent/Skill、amount、PaymentSignature、signed tx | Payment record / tx id | 签名、金额、nonce、幂等、余额失败 |
| DID | DID、message、signature、timestamp、nonce | `Valid` | inactive DID、过期、重复 nonce、Ed25519 失败 |
| Adapter | from/to、business minor、currency、signed tx | tx hash / pending | ATA/Mint、fee payer、blockhash、RPC、余额 |
| MQ/Verification | payment event | purchase projection/proof | topic/readiness、retry、DB duplicate |

#### 源码落点

`api-gateway/internal/adapter/http/middleware/auth.go:52`、`api-gateway/internal/adapter/http/handler.go:24`、`api-gateway/config/config.yaml:80`、`payment-service/internal/application/service/payment_service.go:310`、`scripts/test-deterministic-e2e.ps1:217`。

这里要把三层路径分开：上面是 S0 的真实支付平面请求路径；S3 先完成 trusted Catalog discovery/selection；然后 S2 Runtime 才执行受约束的支付路径：

```text
Commerce Runtime
  → Acquisition Contract → DiscoveryQuery
  → current Catalog active view
  → hard eligibility filter + deterministic ranking
  → persisted CandidateSet (facts_ref / payload_hash / expiry)
  → SELECT_MERCHANT membership + snapshot + validity guard
  → resolve PayeeDID from immutable CandidateSet
  → reserve PaymentIntent + BUDGET_RESERVED + EpisodeEvent
  → DID authorization + payment guard
  → local SUBMITTING commit
  → KitexPaymentAdapter
  → Payment Service canonical Kitex contract
  → outcome: CONFIRMED / FAILED / PENDING / UNKNOWN
  → reconcile payment status / chain / entitlement
  → release reservation first
  → optional settlement fact
  → CLAIMING or terminal compensation
```

S3 的入口是 `RegisterCapabilityVersion` / `DiscoverCapabilities` / `CommitMerchantSelection`；S2 的入口是 `ReservePaymentIntent` / `AuthorizeAndSubmitPayment` / `ReconcilePayment`。这些都不是让 LLM 或旧 Gateway 直接写 trusted facts。`KitexPaymentAdapter` 是 production adapter；HTTP adapter 只保留 optional/test path。S3 的 `PriceHint` 仍不是 TrustedPaymentQuote，也不会直接创建 PaymentIntent。

#### 源码落点

S3：`commerce-runtime/internal/catalog/catalog.go`、`internal/catalog/discovery.go`、`internal/application/service.go:164`–`:287`、`internal/decision/decision.go:151`–`:204`、`internal/infrastructure/mysql/repository.go:250`–`:390`；S2：`commerce-runtime/internal/application/payment_runtime.go:77`、`:271`、`:344`；`commerce-runtime/internal/adapters/kitex_payment.go:15`；`commerce-runtime/internal/reconciliation/reconciliation.go:24`。

### Q6：三种签名到底是什么？

#### 30 秒回答

| 名称 | 证明什么 | 谁签/谁验 | 绑定什么 |
| --- | --- | --- | --- |
| `GatewaySignature` | HTTP 请求没有被替换 | Agent 签；Gateway 调 DID 验 | method、path、raw query、raw body SHA-256 |
| `PaymentSignature` | Agent 同意这笔业务支付和这笔 client-signed transaction | Agent 签；Payment 调 DID 验 | Agent DID、Skill DID、业务 amount minor、currency、`sha256(signed_tx_base64)`、timestamp、payment nonce |
| `SignedTxBase64` | 一笔具体 Solana 交易的签名状态 | Agent 签 token transfer；hot wallet 补 fee payer | from/to、Mint/ATA、raw amount、recent blockhash、fee payer |

Gateway canonical 是：

```text
METHOD\nPATH\nRAW_QUERY\nsha256(raw_body_bytes)
```

`api-gateway/internal/infrastructure/auth/signature.go:14` 固定格式，Gateway 用 `ctx.Request.Body()` 原始字节算 hash。E2E 用 `curl --data-binary`，不在签名后重新序列化 JSON。

当前 Payment canonical 由 `PaymentBusinessSignPayload` 生成：

```text
agent_did|skill_did|amount_minor|currency_code|sha256_hex(signed_tx_base64) + timestamp + payment_nonce
```

Gateway nonce 和 payment nonce 必须分开：前者保护 HTTP 重放，后者属于业务签名和 Payment 防重放。真实重试使用新 Gateway nonce，复用同一业务请求和 idempotency key，返回原 tx id。

#### 源码落点

`api-gateway/internal/adapter/http/middleware/auth.go:94`、`payment-service/internal/domain/vo/values.go:200`、`did-service/internal/application/did_app_service.go:404`、`scripts/test-deterministic-e2e.ps1:92`、`:244`。

### Q7：为什么 exact body 这么敏感？

#### 30 秒回答

签名验证的是字节，不是解析后“语义相等”的 JSON。`{"a":1}` 和 `{"a": 1}` 可能解析成同一对象，但 SHA-256 输入不同。真实 E2E 先把 Go helper 生成的 exact body 写文件，再用 `--data-binary` 原样发送。

这是跨语言协议问题：单测只 mock map 或只比较解析后的 JSON，很可能漏掉。解决方法是冻结 canonical 规则，保存签名时的原始 bytes，并在测试里直接断言 body hash。

#### 证据

`payment-service/cmd/e2e-client/main.go` 的 `json.Marshal`/`buildGatewayCanonical`；`scripts/test-deterministic-e2e.ps1:86`–`:100`；`payment-service/cmd/e2e-client/main_test.go:24`。

### Q8：DID 在这里到底做了什么？

#### 30 秒回答

当前 DID 是把 Agent 的 Solana public key 注册成 `did:solana:<base58-public-key>`，DID Service 根据注册记录取公钥，验证 Ed25519 签名。验证流程包括 DID active、timestamp 窗口、nonce 未使用、Base58 解码和签名验证；成功才记录 nonce。

Agent identity 与 hot wallet 是两个 trust domain：Agent 用自己的 key 签业务 payload 和具体 transaction，hot wallet 在 adapter 侧承担 fee payer/补签。如果混成一个主体，就无法回答谁授权支付、谁承担基础设施费用。

需要诚实补充：DID Service 的 nonce cache 当前是进程内 map + mutex，不是跨实例共享 Redis store；Gateway 和 Payment 又各自有 nonce store。不能把它说成全局分布式 replay store。

#### 证据

`did-service/internal/application/did_app_service.go:23`–`:74`、`:359`–`:418`；`payment-service/cmd/e2e-client/main.go` 的 Agent/hot wallet 分离检查。

### Q9：x402 在 StablePay 里是什么角色？

#### 30 秒回答

402 是商户返回的支付要求，包含 Skill/merchant DID、价格、币种、消息和支付 endpoint。对未来 Commerce Runtime 来说，**402 是 Observation，不是付款授权**：Runtime 应先解析 quote，再结合 Acquisition Contract、policy、budget、DID、merchant capability 决定是否允许付款；付款后还要 claim/invoke 并验证交付。

- **IMPLEMENTED**：`GET /api/v1/pay/require` 返回 payment requirement；skill demo 可在 402 后付款、再请求受保护资源。
- **IMPLEMENTED（S1–S3 Core）**：Runtime 可以把规范化 Contract、Observation 和受约束 Proposal 记录进 Episode；S3 还能从 Contract 派生 DiscoveryQuery、过滤 trusted Catalog、持久化 CandidateSet，并按 CandidateSet guard 选择商户。
- **PLANNED**：把真实 402 → `TrustedPaymentQuote` → policy → payment → entitlement → delivery validation → recovery 接入同一个 Episode Loop。

不要说“有 x402 就已经是 Commerce Runtime”，也不要把当前购买查询说成 Delivery Validator。

#### 源码落点

`payment-service/internal/application/service/payment_service.go:480`、`payment-service/cmd/e2e-client/main.go`、`scripts/test-deterministic-e2e.ps1:217`；S3 入口见 `commerce-runtime/internal/catalog/discovery.go`、`internal/application/service.go:178`，真实 402 消费仍是后续设计。

### Q10：Payment 怎么保证幂等？

#### 30 秒回答

要分层讲：

1. Gateway nonce：HTTP 签名请求防重放。
2. Payment nonce：业务签名防重放。
3. `X-Idempotency-Key` 结合 Agent/Skill 后做 SHA-256，落 `payment_idempotency_keys`。
4. `tx_id`、业务 `sign_nonce` 和 idempotency key 有唯一性/查询约束。
5. 相同 key + 不同 request hash 直接 mismatch；相同 key + 已有 tx id 返回原 payment。
6. `event_id` 让下游 projection replay 幂等。

网络重试不等于重新支付。Payment Service 在写 payment record 后记录进行中 idempotency，再调用 chain；重试如果看到同一个 tx id，就不再调用第二次 chain。

必须补一个真实限制：Payment Service 的 `NonceChecker` 目前是 `IsDuplicate` + `RecordNonce` 两步；它不像 Gateway `SetNX` 或 Harness `GETDEL` 那样天然原子。面对多实例高并发，最终护栏仍是业务 idempotency + DB unique constraint，nonce checker 是后续可加固点。

#### 证据

`payment-service/internal/application/service/payment_service.go:319`–`:430`、`payment-service/internal/domain/service/validator.go:141`–`:173`、`payment-service/internal/domain/entity/payment.go:188`–`:202`、`scripts/test-deterministic-e2e.ps1:244`–`:265`。

### Q11：为什么 RocketMQ 至少一次，而 Consumer 必须幂等？

#### 30 秒回答

Consumer 可能在写 DB 后、ACK 前崩溃，同一消息会重新投递。与其追求消息层 exactly-once，不如接受 at-least-once，用 event id/业务唯一键保证业务结果不重复。

```text
payment-service → physical topic payment_events
               → tag = payment.success / payment.failed
verification consumer → envelope validate
                    → event_id dedupe
                    → purchase projection
```

E2E 会重放已发布的 event id，再检查 purchase proof 的 tx id 没变化。当前 payment 状态更新与 MQ publish 之间没有完整 Outbox 事务；producer 失败主要记录日志，不能说“DB 与 MQ 原子提交”。

#### 证据

`payment-service/internal/adapter/mq/producer.go:53`、`:131`；`verification-service/internal/infrastructure/messaging/rocketmq_consumer.go:91`–`:133`；`stablepayai-idl/docs/event-contract.md`；`scripts/test-deterministic-e2e.ps1:299`–`:337`。

### Q12：支付成功和购买成功有什么区别？

#### 30 秒回答

- `PAYMENT_CONFIRMED/COMPLETED`：Payment Service 认为链上交易已确认。
- `Purchased = true`：Verification 已消费成功事件并建立 Agent–Skill 购买投影。
- S2 Runtime 的 `PaymentIntent=CONFIRMED`：本 Intent 的 payment outcome 已确认，并进入 `CLAIMING`；它仍不等于 entitlement valid。
- `ENTITLEMENT_VALID`：Entitlement evidence 与当前 Intent/TxID/TxHash 至少有 identity binding，Episode 才能进入 `INVOKING_DELIVERY`。
- `ENTITLEMENT_INVALID`：当前 Intent 的 entitlement 证据明确不匹配，Episode 进入 `FAILED`。
- `ENTITLEMENT_UNKNOWN`：证据不足或查询不确定，Episode 留在 `CLAIMING`，是 same-state event。
- S1 Episode 状态机仍要求真实 `DELIVERY_VALID` Observation 才能从验证态进入 `FULFILLED`；S2 没有实现 Delivery Validator。

当前 `VerifyPurchase` 不是 Delivery Validator；旧购买记录也不能证明当前 PaymentIntent 成功。S1/S2 的状态和 evidence binding 是确定性边界，不等于 Parent Agent 的整体任务完成。

#### 证据

`payment-service/internal/domain/entity/payment.go:96`–`:143`、`payment-service/internal/application/service/payment_service.go:550`–`:635`、`verification-service/internal/application/service.go:38`、`commerce-runtime/internal/application/payment_runtime.go:548`、`commerce-runtime/internal/adapters/adapters.go:78`、`commerce-runtime/internal/episode/episode.go:246`–`:313`、`commerce-runtime/internal/application/service_test.go:91`。

### Q13：Solana 交易具体是什么样？

#### 30 秒回答

只讲项目实际使用的部分：SPL Token 转账、Mint、ATA、token owner signer、fee payer、recent blockhash、base64 序列化、Devnet RPC 和 transaction hash。当前主链路不使用 Anchor、PDA、CPI，不要为了凑八股扩展这些。

真实 client-signed flow 是：Adapter 构造 unsigned SPL transaction；Agent 检查 signer 后 partial sign；HTTP 携带 `signed_tx_base64`；Adapter 验证格式、fee payer、from/to/currency/amount；hot wallet 补签 fee payer；Solana 返回 tx hash；Payment 轮询确认。

如果没有 signed tx，当前 adapter 只允许 hot wallet 自持代币的 server-built path；若 `from_wallet` 不是 hot wallet，则拒绝，避免从错误 ATA 扣款。

#### 证据

`blockchain-adapter/internal/infrastructure/blockchain/transaction_builder_impl.go:130`–`:216`、`blockchain-adapter/internal/application/service/transfer_cmd_service.go:58`–`:115`、`blockchain-adapter/internal/infrastructure/blockchain/transaction_validation.go`。

### Q14：真实 Devnet E2E 为什么重要？遇到过什么 bug？

#### 30 秒回答

单测、契约测试和真实 E2E 发现的问题层次不同。最典型的是业务金额和 SPL raw unit 的数量级错位：

```text
0.01 USDC = 1 business minor = 10,000 SPL raw units
```

旧实现若把 `amount_minor = 1` 直接写入 SPL instruction，链上实际只有 `0.000001 USDC`。mock chain 只看“调用成功”可能漏掉；真实 Devnet balance 和 instruction data 才暴露。

转换放在 blockchain boundary，因为 PaymentSignature、DB、MQ event 和 Verification projection 应保留业务金额语义，只有 SPL instruction 需要 raw units。不能把 raw unit 向上泄漏，否则会破坏 API、签名和事件兼容性。

回归测试包括：`token_amount_test.go` 检查 `1 → 10000`、大小写币种、非法金额；builder/validation test 检查 instruction data；E2E helper 输出 `amount_minor`、`required_token_raw` 和 token balance 前置条件。

#### 证据

commit `30b10067`；`blockchain-adapter/internal/domain/vo/token_amount.go:17`；`blockchain-adapter/internal/application/service/transfer_cmd_service.go:67`；`blockchain-adapter/internal/domain/vo/token_amount_test.go`；`payment-service/cmd/e2e-client/main.go`。

### Q15：如果网络超时，如何判断钱到底有没有付？

#### 30 秒回答

**当前实现：** 不能把 HTTP timeout 直接解释为 chain failed，也不能马上重新支付。Adapter 在已发送但确认等待超时时返回 `pending` 和 tx hash；Payment Service 保存 tx hash 并后台查询。后续得到 confirmed/failed；轮询耗尽时当前代码标 `POLL_TIMEOUT` failed，但这不等于链上绝对没有成功。

**S2 Runtime：** `UNKNOWN` 不是 `FAILED`。`ReconcilePayment` 按 payment-service status、chain status、identity-bound entitlement 的顺序查询；仍 unresolved 时，才允许对同一个 persisted Intent 做 exact idempotent redelivery，不能创建新 Intent、换金额、换 Payee 或换 Quote。`SUBMITTING`/`UNKNOWN` 的 crash window 也走这条路径。

如果最终得到 `CONFIRMED`，先 release reservation，再 append `PAYMENT_SETTLED`；如果得到 `FAILED`，release reservation、关闭 Intent，并把 Episode 进入失败/过期补偿路径；如果仍 unknown，保留 PaymentIntent UNKNOWN 和 same-state factual event，等待后续 reconcile。

#### 证据

`blockchain-adapter/internal/application/service/transfer_cmd_service.go:170`–`:179`、`payment-service/internal/application/service/payment_service.go:531`–`:587`、`commerce-runtime/internal/application/payment_runtime.go:271`、`:344`、`internal/reconciliation/reconciliation.go:24`、`internal/application/payment_runtime_test.go:225`。

### Q16：为什么链上付款不能 rollback？Merchant A 失败后预算怎么算？

#### 30 秒回答

链上 settlement 一旦确认，不存在数据库事务意义上的 rollback，只能做退款、争议或其他 compensation。因此未来 Episode Ledger 要拆：

```text
budget_limit
reserved_amount
settled_amount
refunded_amount
available_budget
sunk_cost = max(0, settled_amount - refunded_amount)
```

S2 已把预算语义从 Episode 的缓存字段提升为 append-only `LedgerEntry` 事实：`BUDGET_RESERVED`、`BUDGET_RELEASED`、`PAYMENT_SETTLED`、`REFUND_CONFIRMED`、`COMPENSATION_RECORDED` 由 Ledger 重算 Budget Projection，再写回 Episode。`RefundReusable` 明确退款是否恢复 available budget；但 refund accounting fact 不等于 external automatic refund workflow，compensation ledger type 也不等于完整业务补偿编排。

#### 证据

`commerce-runtime/internal/ledger/ledger.go:18`–`:227`、`commerce-runtime/internal/application/payment_runtime.go:175`–`:229`、`:470`–`:548`、`commerce-runtime/internal/episode/episode_test.go:111`、`commerce-runtime/internal/ledger/ledger_test.go`。

### Q17：Agent Payment Harness 与完整 Commerce Runtime 是什么关系？

#### 30 秒回答

| 维度 | 当前 Harness | 规划中的 Runtime |
| --- | --- | --- |
| 目标 | 约束一次 payment intent | 管理一次能力获取 Episode、资金事实和支付尝试的确定性核心 |
| 状态 | pending/approved/consumed | discovering/invoking/paying/claiming/validating/recovering |
| 模型权限 | 可填 purpose，不能执行 | Proposal 不能写 Ledger、PaymentIntent、PaymentOutcome 或 Entitlement fact |
| 护栏 | policy、allowlist、TTL、DID approval、GETDEL | S2 contract、state、ledger、intent、authorization、attempt、deadline、evidence、idempotency、reconciliation |
| 当前状态 | 代码实现，默认关闭 | **IMPLEMENTED（S1/S2/S3 Core）**；Invoke/402/Delivery loop 仍 **PLANNED** |

所以 Harness 是旧付款意图安全边界；S1/S2/S3 Runtime 是 Episode/Proposal/Guard/Event/Ledger/PaymentIntent/Reconciliation/Catalog/CandidateSet 的确定性核心，但不是完整 Agent Commerce Runtime。

#### 源码落点

`payment-service/internal/application/service/agent_payment_harness.go:61`、`:174`、`payment-service/config/config.yaml`；`commerce-runtime/internal/application/service.go:141`；`commerce-runtime/internal/application/payment_runtime.go:77`；`commerce-runtime/internal/ledger/ledger.go`；`commerce-runtime/internal/reconciliation/reconciliation.go`；`commerce-runtime/internal/repository/repository.go:51`。

### Q18：为什么要把 physical topic 和 event_type 分开？

#### 30 秒回答

`payment_events` 是稳定物理 topic；`payment.success` / `payment.failed` 是 topic 内的事件类型/tag。Producer 启动时强校验物理 topic；consumer 订阅稳定通道，再按 event type 决定是否建立 projection。这样普通支付和 reward 等业务不会让 topic 名同时承担物理路由和场景语义。

#### 证据

`payment-service/internal/adapter/mq/producer.go:27`、`:131`；`verification-service/internal/infrastructure/messaging/rocketmq_consumer.go:55`；`payment-service/internal/infrastructure/config/config.go:211`；commit `8cc16ff`。

### Q19：为什么 consumer readiness 不能只看 Kitex 端口？

#### 30 秒回答

Kitex 端口监听只能证明进程绑定成功，不能证明 RocketMQ nameserver 可达、topic 正确、consumer 已订阅。当前 consumer 启动前检查 nameserver/topic，E2E 还等日志中的 `RocketMQ consumer ready` 后才开始付款。这是 readiness 和 liveness 的区别。

#### 证据

`verification-service/internal/infrastructure/messaging/rocketmq_consumer.go:55`–`:79`、`:191`–`:204`；`scripts/test-deterministic-e2e.ps1:158`–`:167`。

### Q20：从 git history 讲讲项目怎么迭代到现在？

#### 30 秒回答

先迁移服务和契约，再处理本地联调的 wallet/topic/nameserver，再用真实身份、真实签名、真实 MySQL/Redis/RocketMQ 和 Devnet 关闭 deterministic E2E，随后用真实链路暴露 token decimals bug。支付链稳定后才发现 transaction closure 仍不是 task closure，于是开始设计 Episode、Acquisition Contract、Observation、Delivery Validation 和 Recovery。`d338353` 把 S1 Episode Core 落成独立模块，`0e5c615` 又用 MySQL 并发/原子性测试关闭验收债务；`f5e9435`、`4e4c87a`、`2a3b8e2` 逐步把资金边界收紧到 S2；`7ecc5c1` 和 `90e9ce3` 再把 trusted Catalog、structured Discovery、CandidateSet replay 和 current/deactivation 语义落地。这个叙事比把最终架构倒着说更可信。

#### 证据

`git log --oneline --decorate -12`；commits `ce3be348`、`8cc16ff`、`8c537015`、`30b10067`、`d338353`、`0e5c615`、`f5e9435`、`4e4c87a`、`2a3b8e2`、`7ecc5c1`、`90e9ce3` 的实际 diff。

## 第二轮：S1 Episode Core 与状态事实

### Q21：为什么需要 CommerceEpisode，不能直接把 Payment 当 aggregate 吗？

#### 30 秒回答

不能。Payment 只负责一笔资金副作用的生命周期；Episode 要跨越 `DISCOVERING → INVOKING → NEGOTIATING → PAYING → CLAIMING → VALIDATING_DELIVERY`，还要保存 Acquisition Contract、预算、attempt、deadline、Observation 和恢复状态。一个 Episode 可能没有付款、发生多次 delivery attempt，甚至需要在一次支付后继续验证，所以 Payment 不能承载父任务的状态机。

S1 的 `CommerceEpisode` 是能力获取的权威 Projection；S2 已通过 `PaymentIntent` 和 `KitexPaymentAdapter` 把受控支付尝试接入 Runtime，S3 又把选中的 Catalog snapshot 和 PayeeDID 绑定到 Episode，之后才能进入 S2 的 payee consistency guard。

#### 源码落点

`commerce-runtime/internal/episode/episode.go:96`–`:126`；`payment-service/internal/domain/entity/payment.go`；`commerce-runtime/migrations/001_create_commerce_runtime.sql`。

### Q22：Acquisition Contract 为什么必须 immutable？

#### 30 秒回答

Episode 创建时先规范化请求，再生成 canonical JSON 和 SHA-256 snapshot hash。之后所有状态推进都引用同一份目标、输入、预算、deadline、attempt limit 和 validator 配置，不能在支付前后偷偷改变约束。否则 replay 时无法判断“当时到底承诺了什么”，也会让同一个 `request_id` 被换成另一份合同。

当前实现对 `request_id + snapshot hash` 做幂等判断；Projection 更新时再次拒绝 contract snapshot 改写。它解决的是 Contract identity，不是商户 quote 或链上金额的最终结算。

#### 源码落点

`commerce-runtime/internal/contract/contract.go:145`–`:232`、`commerce-runtime/internal/application/service.go:77`、`commerce-runtime/internal/infrastructure/mysql/repository.go:134`、`:204`。

### Q23：EpisodeEvent 为什么 append-only？为什么 Projection 和 Event 要同时保存？

#### 30 秒回答

Projection 适合查询当前状态，Event 保留每次 `Action + Observation + Decision + RuntimeVerdict + StateBefore/After`，便于审计、重试判定和 replay。Event 不能被更新，否则同一个 sequence 的历史依据会被覆盖。

但要说准确：S1 不是“所有业务事实都由 Event Sourcing 完整重建”。当前 `Reconstruct` 主要校验顺序、状态迁移和 action counters；预算真实账务、Payment、Delivery evidence 仍需要后续独立事实源/适配器。S1 用同一个 `TransitionStore` 事务同时提交 Projection 和 Event，避免只更新一边。

#### 源码落点

`commerce-runtime/internal/episode/event.go:19`、`internal/episode/replay.go:12`、`internal/repository/repository.go:39`、`internal/infrastructure/mysql/repository.go:204`。

### Q24：两个 resume 同时发生怎么办？

#### 30 秒回答

每次 Proposal 必须绑定当前 `BasedOnEventSequence`，Action 必须有 `IdempotencyKey`。Runtime 先做同 key replay 检查，再由 Guard 校验 event sequence、state、deadline 和 attempt；真正提交时，MySQL 在一个事务中锁 Episode 行，按 `version` 条件更新 Projection，并以 `(episode_id, idempotency_key)` 和 `(episode_id, sequence)` 唯一约束写 Event。

因此：同 key、同输入返回原 Event；同 key、不同输入报冲突；不同 key 但基于旧 version 的并发推进只有一个成功，另一个收到 version/stale sequence 冲突。这个组合同时解决重试和并发，不依赖“恰好只有一个 worker”。

#### 源码落点

`commerce-runtime/internal/application/service.go:141`、`internal/decision/decision.go:81`、`internal/infrastructure/mysql/repository.go:204`、`internal/infrastructure/mysql/repository_integration_test.go:22`、`internal/application/service_test.go:260`。

### Q25：DecisionProposal 为什么不是 Decision？为什么 LLM 没有 state write 权限？

#### 30 秒回答

Proposal 只是“基于哪些 Observation，我建议做什么”的候选输出；它可能过期、引用未知证据、超预算、超过 attempt 或不符合当前状态。最终允许的下一状态由 `RuntimeGuard` 根据当前 Episode、Action 和 Observation 的确定性映射计算，不能由模型直接填写。

S1 的 `StaticDecisionProvider` 只有返回 Proposal 的能力，没有 Repository 或 commit 权限；`CommitProposal` 才能生成带 RuntimeVerdict 的 Event 并调用 `TransitionStore`。因此未来替换成 LLM，只替换提议生成，不改变资金和状态写入边界。

#### 源码落点

`commerce-runtime/internal/decision/decision.go:15`、`:81`、`:144`、`:155`；`commerce-runtime/internal/application/service.go:124`。

### Q26：Event replay 怎么重建 Episode？如何处理 future event 和 duplicate event？

#### 30 秒回答

S1 replay 从初始 Projection 开始，要求 Event 按 `sequence = index + 1` 排列、Episode ID 一致、`StateBefore` 等于当前状态，并再次执行 Event validation 和 `ApplyCommittedState`。sequence 缺失、乱序、重复或状态不匹配都会拒绝，不能把历史事件当普通日志忽略。

当前 replay 是重建校验，不是任意事件修复器；数据库也用 Episode + sequence 和 Episode + idempotency key 唯一约束阻止重复历史。未来 schema evolution 要通过 `runtime_version/schema_version` 和兼容迁移处理。

#### 源码落点

`commerce-runtime/internal/episode/replay.go:12`、`internal/episode/event.go:48`、`internal/infrastructure/mysql/repository.go:204`、`migrations/001_create_commerce_runtime.sql`。

### Q27：S1 实际实现了哪些状态迁移？哪些仍只是 enum/interface？

#### 30 秒回答

S1–S3 不是只加 enum：`RuntimeGuard` 会根据 Action + Observation 计算合法 next state，`CommitProposal` 会更新 counters、生成 Event，并把 Projection 和 Event 一起提交；S3 还通过 `DiscoveryQuery`、CandidateSet 和 `SELECT_MERCHANT` guard 把目录事实纳入状态推进。测试用规则化 Proposal 在不接 LLM 的情况下走通 deterministic flow，也覆盖 terminal、deadline、same-state payment、selection guard 和 replay。

但这些是 Runtime Core 的确定性迁移，不代表真实 Merchant Invoke、402 quote 消费、Delivery Validator 或 recovery 已经接入。S2 的 Payment/Entitlement adapter 和 S3 的 Catalog/Discovery 已落地；`ActionType` 和 `ObservationType` 中的 Delivery/402 能力仍需要后续 adapter 提供事实。

#### 源码落点

`commerce-runtime/internal/episode/episode.go:285`、`internal/application/service.go:141`、`internal/application/service_test.go:91`、`internal/episode/episode_test.go:23`。

### Q28：Episode 如何记录 payment pending/unknown，又如何避免复制 Payment 状态就宣布完成？

#### 30 秒回答

S1 的 trace 定义了 `PAYMENT_PENDING`、`PAYMENT_STATUS_QUERIED`、`PAYMENT_SETTLED` 等 Observation；S2 Runtime 已通过 Payment Adapter、chain/payment reconciliation 和 Entitlement adapter 产生这些事实，Episode 仍把它们作为事件依据，保持当前状态和下一次 Proposal 的 sequence 一致，而不是复制 Payment 表。

只有在 `VALIDATING_DELIVERY` 下收到真实 `DELIVERY_VALID` Observation，Guard 才允许进入 `FULFILLED`；S2 的 Payment confirmed 和 Entitlement valid 最多推进到 Claim/Delivery 相关阶段，S3 的 Catalog selection 也不等于 delivery。Delivery Validator 仍是 Planned。

#### 源码落点

`commerce-runtime/internal/trace/trace.go:25`、`internal/episode/episode.go:285`、`internal/decision/decision.go:81`、`internal/application/service_test.go:91`。

## 第三轮：S2 资金事实与支付恢复

### Q29：为什么 Episode 的 BudgetSnapshot 不能当资金事实源？

#### 30 秒回答

`BudgetSnapshot` 是为了快速读取和与 Episode 一起做状态校验的 Projection；它可以被重算，不能单独证明钱发生过什么。真正的财务事实是 append-only `LedgerEntry`：reserve、release、settle、refund 和 compensation 都有自己的 entry、sequence、idempotency key、reference hash 和时间。

Runtime 每次 finance transition 都从 Ledger 重建 Projection，再检查它与下一版 Episode Budget 一致。这样即使缓存字段损坏，也能用 Ledger replay 检查；如果直接修改 Snapshot，就会丢失“哪一次支付、哪一次退款、哪一个 Intent”造成了变化。

#### 源码落点

`commerce-runtime/internal/ledger/ledger.go:95`–`:227`、`commerce-runtime/internal/application/payment_runtime.go:232`、`commerce-runtime/internal/infrastructure/mysql/repository.go:584`。

### Q30：为什么要有 append-only LedgerEntry？EpisodeEvent 和 LedgerEntry 有什么区别？

#### 30 秒回答

两者记录的事实层次不同：

- `EpisodeEvent`：Runtime 过程 trace，记录 Action、Observation、Decision、RuntimeVerdict、StateBefore/After。它回答“Runtime 为什么推进”。
- `LedgerEntry`：经济事实，记录金额、币种、Intent、TxID、RefundID、reference hash。它回答“预算和钱发生了什么变化”。

一个 EpisodeEvent 可以是 same-state 的 `PAYMENT_UNKNOWN`，不一定改变 Episode state；LedgerEntry 则只有明确的经济动作才改变 Budget Projection。退款必须 append 新 fact，不能把原 settlement 改成 refunded。S2 仍不是 full Event Sourcing：Ledger 是财务事实，EpisodeEvent 是运行 trace，二者各自 replay。

#### 源码落点

`commerce-runtime/internal/episode/event.go:19`、`internal/ledger/ledger.go:18`、`internal/repository/repository.go:51`、`internal/infrastructure/mysql/repository.go:470`。

### Q31：为什么 PaymentIntent 不是 Payment Service 的 Payment？它代表“钱”还是“允许尝试一次支付”？

#### 30 秒回答

`PaymentIntent` 是 Commerce Runtime 自己拥有的“在约束内允许尝试一次经济动作”的事实，不是钱已经转出去，也不是 Payment Service 的生命周期记录。它绑定 Episode、MerchantDID、CapabilityID、PayeeDID、QuoteHash、金额、预算 reservation、授权引用、credential ref、幂等键和 fingerprint，并有 `CREATED → AUTHORIZED → SUBMITTING → PENDING/UNKNOWN/CONFIRMED/FAILED/EXPIRED` 状态。

Reserve 只创建本地 Intent 和 `BUDGET_RESERVED`，不会调用 Payment Service，更不会让 `PaymentIntent=CREATED` 直接等于 settlement。真正的 Payment Service record、Solana tx 和确认结果通过 Adapter/Outcome 回到 Runtime。

#### 源码落点

`commerce-runtime/internal/payment/intent.go:15`–`:156`、`internal/application/payment_runtime.go:77`–`:229`、`internal/adapters/adapters.go:45`。

### Q32：EconomicKey 与 IdempotencyKey 有什么区别？为什么 PayeeDID 必须进入 EconomicIdentityKey？

#### 30 秒回答

`IdempotencyKey` 解决“同一个调用重试时不要重复执行”；`EconomicKey` 解决“即使调用方换了 retry key，也不能把同一经济动作伪装成另一笔，或把不同经济动作错误合并”。

当前 EconomicKey 包含 Episode、Merchant、Capability、Payee、QuoteHash、AmountMinor 和 Currency。`PayeeDID` 必须进入，因为收款主体改变就是经济语义改变；如果只绑定 MerchantDID，两个不同收款方可能被错误去重，或者重试时把钱发到另一个 payee。

#### 源码落点

`commerce-runtime/internal/payment/intent.go:54`–`:76`、`internal/repository/inmemory.go:244`、`internal/infrastructure/mysql/repository.go:592`、`migrations/001_create_commerce_runtime.sql`。

### Q33：MerchantDID、CapabilityID、PayeeDID 分别是什么？为什么把 CapabilityID 映射成 skill_did 是错误的？

#### 30 秒回答

- `MerchantDID`：提供能力的商户/主体。
- `CapabilityID`：商户目录中的能力标识，是业务资源 ID，不是 DID。
- `PayeeDID`：这次资金实际要支付给的收款主体。

早期 prototype 把 `CapabilityID` 当成 `skill_did`，会把业务 capability 字符串塞进 payment-service 需要的 DID 字段，既破坏身份语义，也无法表达“一个 merchant 提供多个 capability”或“merchant 与实际 payee 分离”。最终 Kitex mapping 使用 Agent 的 `RequesterDID` 和 `PayeeDID`，CapabilityID 留在 Runtime 的 Intent/authorization binding 中。

#### 源码落点

`commerce-runtime/internal/payment/intent.go:29`、`internal/adapters/kitex_payment.go:51`–`:62`、`internal/adapters/kitex_payment_test.go:38`；commit `2a3b8e2` 的语义清理。

### Q34：reserve budget 为什么不是支付？为什么 CONFIRMED 时先 release reservation，再 append settlement？refund 为什么 append 新 fact？

#### 30 秒回答

Reserve 只是把 Episode 的可用预算标记为这次 Intent 暂时占用，避免两个支付尝试同时花同一额度；它没有外部副作用。只有经过 authorization guard 后，Runtime 才把 Intent 置为 `SUBMITTING` 并调用 Payment Adapter。

确认结果落库时，先写 `BUDGET_RELEASED`，解除原 reservation，再写 `PAYMENT_SETTLED`，把已确认的经济事实重新计入 `settled/consumed`。如果反过来或漏掉 release，Projection 会长期把同一笔钱同时算作 reserved 和 settled，available 会被少算。

Refund 是 settlement 之后发生的新事实，必须 append `REFUND_CONFIRMED`，保留原支付的审计和 tx 关联；它不是把 settlement 行原地改写。

#### 源码落点

`commerce-runtime/internal/application/payment_runtime.go:448`–`:548`、`internal/ledger/ledger.go:112`–`:172`、`internal/ledger/ledger_test.go`。

### Q35：`consumed=max(0, settled-refunded)` 为什么这样定义？`refund_reusable=false` 意味着什么？

#### 30 秒回答

当退款可重新释放预算时，真正消耗的额度是已结算金额减去已确认退款，但不能小于零；因此 `consumed=max(0, settled-refunded)`，再用 `available = limit - consumed - reserved` 计算可用预算。`sunk_cost=max(0, settled-refunded)` 保留“最终没有拿回来的结算成本”。

当 `refund_reusable=false` 时，退款仍然是审计事实，但不把容量返还给 `available`；Projection 的 `consumed` 仍按 settled 计算。这是预算策略开关，不代表系统已经自动向链上或商户发起退款。

#### 源码落点

`commerce-runtime/internal/ledger/ledger.go:92`–`:172`、`internal/episode/episode.go:52`–`:90`、`internal/episode/episode_test.go:111`、`internal/ledger/ledger_test.go`。

### Q36：什么叫 unknown payment outcome？timeout 为什么不能直接重新支付？什么叫 blind retry？

#### 30 秒回答

`UNKNOWN` 表示 Runtime 没有足够事实判断远端是否已经接受/确认这笔支付；它不是 `FAILED`。HTTP/RPC timeout 只能说明当前观察失败，不能证明链上没有产生副作用。直接创建新 Intent 或换一组金额/Payee 再提交，就是 blind retry，可能造成双付。

S2 的 `ReconcilePayment` 先查 Payment Service status，再查 chain status，再查 identity-bound entitlement。仍然 unresolved 时，Runtime 只允许用同一个 persisted Intent 做 exact redelivery：保持 IntentID、EconomicKey、IdempotencyKey、RequestFingerprint、金额、Quote、Payee 和 CredentialRef 不变。

#### 源码落点

`commerce-runtime/internal/reconciliation/reconciliation.go:24`–`:86`、`internal/application/payment_runtime.go:271`–`:344`、`internal/application/payment_runtime_test.go:225`。

### Q37：SUBMITTING 后进程 crash 会发生什么？为什么需要 RequestFingerprint 和 CredentialRef？

#### 30 秒回答

流程可能是：本地把 Intent 置为 `SUBMITTING` 并提交 EpisodeEvent → 进程 crash → 远端 submit 结果未知。重启后不能新建一笔付款，而是读取原 Intent，先 reconcile；如果仍 unresolved，再把完全相同的 economic command redeliver 给 Payment Service。

`RequestFingerprint` 是发送给 payment plane 的稳定 command identity，防止 retry 时请求字段悄悄变化。`CredentialRef` 只保存 opaque reference，不保存签名私钥或 secret；retry 必须解析同一个 reference，才能继续生成同一类签名请求并让下游 idempotency 生效。

#### 源码落点

`commerce-runtime/internal/payment/intent.go:102`–`:134`、`internal/application/payment_runtime.go:271`–`:344`、`internal/adapters/kitex_payment.go:23`–`:53`；`internal/application/payment_runtime_test.go:225`。

### Q38：为什么 retry 必须保持原 Intent、金额、Payee、Quote 和幂等键？

#### 30 秒回答

retry 的目标是恢复同一经济命令的 unknown outcome，不是提出新的购买决定。只要 Intent、AmountMinor、Currency、PayeeDID、QuoteHash、IdempotencyKey 或 RequestFingerprint 改变，就不再是同一笔命令，原来的回执、reservation 和 reconciliation 证据也不能复用。

所以 Adapter 在 submit 前重新校验 Intent、authorization、Payee 和 fingerprint；数据库还用 EconomicKey 与 IdempotencyKey 唯一约束把“相同经济动作”和“相同调用重试”分开保护。

#### 源码落点

`commerce-runtime/internal/adapters/kitex_payment.go:23`–`:53`、`internal/adapters/http_payment.go:51`–`:80`、`internal/decision/payment_guard.go:24`–`:69`、`internal/payment/intent.go:65`–`:134`。

### Q39：为什么本地 MySQL transaction 无法把 Solana side effect 一起 rollback？为什么这不是传统 distributed transaction？

#### 30 秒回答

S2 的 MySQL transaction 能原子提交 Episode Projection、EpisodeEvent、LedgerEntry 和 PaymentIntent；它只能控制本地数据库。Solana 或 payment-service 是远程副作用，已经提交的链上转账不能由 MySQL rollback，也没有两阶段提交协议把双方锁在同一事务里。

因此 S2 使用的是“本地原子边界 + 远端 unknown reconciliation + exact idempotent redelivery”，不是传统 distributed transaction。`SUBMITTING` commit 之后 crash 的恢复依赖查询和补偿，不是回滚本地事务就假设远端没发生。

#### 源码落点

`commerce-runtime/internal/repository/repository.go:39`–`:84` 的 finance boundary 注释、`commerce-runtime/internal/infrastructure/mysql/repository.go:470`、`internal/reconciliation/reconciliation.go:24`。

### Q40：Payment settled 为什么只进入 CLAIMING？Entitlement valid 和 Payment confirmed 为什么不是一回事？

#### 30 秒回答

Payment confirmed 只证明这笔 Intent 的付款事实已经确认；它不能证明商户已经为当前请求建立了可用能力。Runtime 因此只把 confirmed payment 推到 `CLAIMING`，再调用 Entitlement adapter 验证当前 Intent/Tx 的交付资格。

只有 entitlement evidence 与当前 Intent/TxID/TxHash 绑定并返回 valid，Episode 才进入 `INVOKING_DELIVERY`。这仍然不是 `DELIVERY_VALID`，所以也不等于 `FULFILLED`。

#### 源码落点

`commerce-runtime/internal/application/payment_runtime.go:420`–`:548`、`internal/application/payment_runtime.go:548`–`:604`、`internal/adapters/adapters.go:78`–`:124`、`internal/episode/episode.go:285`–`:313`。

### Q41：Entitlement evidence 为什么必须绑定当前 Intent/Tx？旧购买记录为什么不能证明当前支付成功？`ENTITLEMENT_UNKNOWN` 和 `INVALID` 有什么区别？

#### 30 秒回答

“这个 Agent 以前买过”只能说明历史关系，不能说明当前 Intent 已成功。`MatchesIntent` 要求 evidence 至少关联当前 `PaymentIntentID`、`TxID` 或 `TxHash`，并且有 reference/evidence ref；旧 purchase projection 如果没有当前绑定，就不能作为本次支付的成功证据。

- `ENTITLEMENT_VALID`：有 identity-bound evidence，进入 `INVOKING_DELIVERY`。
- `ENTITLEMENT_INVALID`：明确发现证据与当前 Intent 不匹配，进入 `FAILED`。
- `ENTITLEMENT_UNKNOWN`：查询失败、证据不足或状态不确定，保留在 `CLAIMING`，写 same-state event，等待后续 reconcile。

这也是 `2a3b8e2` 修复的语义：UNKNOWN 不能被错误压成 INVALID，否则 Observation 错了，下一步 Action 也会错。

#### 源码落点

`commerce-runtime/internal/adapters/adapters.go:78`–`:124`、`internal/application/payment_runtime.go:548`–`:604`、`internal/trace/trace.go:50`–`:55`、commit `2a3b8e2`。

### Q42：为什么 Event 不一定意味着 State Transition？为什么 LLM 不能提交 PAYMENT_PENDING / FAILED / CONFIRMED？

#### 30 秒回答

Event 是一次经过验证的 Runtime observation/decision trace；`PAYMENT_PENDING`、`PAYMENT_UNKNOWN` 和 `ENTITLEMENT_UNKNOWN` 可能让 Episode 保持当前状态，但仍必须记录，因为它们改变了下一次 reconcile 的上下文和审计历史。

Payment confirmed/failed/unknown 是 environment facts，不能由模型“说出来就成立”。S2 把所有 payment/entitlement factual actions 标记为 runtime-owned，`CommitProposal` 直接拒绝这类 Proposal；只有 DID/payment/chain/entitlement adapter 的结果，经过 guard 和 finance transition，才能产生对应事实。

#### 源码落点

`commerce-runtime/internal/application/service.go:141`–`:224` 的 `runtimeOwnedProposalAction`；`internal/episode/episode.go:285`–`:313`；`internal/application/payment_runtime.go:344`–`:548`；`internal/decision/payment_guard.go`。

### Q43：如果 authorization denied，已经 reserve 的钱怎么处理？如果 PaymentIntent expired 呢？为什么不能留下“Episode PAYING + Intent FAILED”的 dead state？

#### 30 秒回答

authorization denied、quote mismatch、budget guard failure 或 Intent expiry 都属于 external payment 尚未被接受前的本地失败。`closePaymentIntent` 在一个 finance transaction 里同时 append `BUDGET_RELEASED`、关闭 PaymentIntent，并把 Episode 从 `PAYING` 推到 `FAILED` 或 `EXPIRED`；reservation 不会被遗留。

如果已经进入 `SUBMITTING` 且远端结果不确定，就不能直接走 FAILED compensation，而要先 reconcile；否则会出现本地说失败、远端实际已扣款的双重事实。只有确定性拒绝或确定性失败，才释放 reservation 并关闭 Intent。

#### 源码落点

`commerce-runtime/internal/application/payment_runtime.go:384`–`:470`、`internal/decision/payment_guard.go:24`–`:69`、`internal/application/payment_runtime_test.go:261`–`:318`。

## 第四轮：S3 Catalog 与可信发现

### Q44：为什么 Merchant Catalog 必须是 trusted facts，而不是 prompt text？为什么 hard filter 要在 LLM/DecisionProvider 前执行？

#### 30 秒回答

商户是谁、能力支持什么输入输出、接受哪些协议和币种、当前版本是否有效，这些都会影响后续支付和安全边界，不能让模型从一段描述文字里自行“相信”。S3 的 `MerchantCapability` 是结构化、可校验、可 canonicalize 和可 hash 的事实；`DiscoveryQuery` 从 immutable Acquisition Contract 派生，不能被 prompt 改写。

`ListActiveCapabilities` 先取得 current active view，`BuildCandidateSet` 再执行 task/content/protocol/currency/budget/time/semantic hard eligibility，最后才做 deterministic ranking。S3 没有让 LLM 覆盖 hard facts，也没有把 structured discovery 包装成 RAG。

#### 源码落点

`commerce-runtime/internal/catalog/catalog.go:70`–`:308`、`:588`–`:651`；`internal/catalog/discovery.go:15`–`:59`；`internal/application/service.go:242`–`:250`。

### Q45：MerchantDID、CapabilityID、PayeeDID 有什么区别？为什么 MerchantDID 和 PayeeDID 可以取相同值？

#### 30 秒回答

`MerchantDID` 是提供能力的商户主体，`CapabilityID` 是商户目录中的业务能力标识，`PayeeDID` 是本次经济动作的实际收款主体。它们必须独立建模，但“语义独立”不等于“字符串必须不同”：商户自己收款时，MerchantDID 和 PayeeDID 合法地相同；平台代收或分账时，二者可以不同。

早期用“不相等”做校验，把合法的 merchant-self-payee 误拒绝。最终 S3 只要求字段语义和格式正确，测试覆盖共享 Merchant/Payee identity，同时仍禁止把 CapabilityID 当 DID。

#### 源码落点

`commerce-runtime/internal/catalog/catalog.go:191`–`:223`；`internal/catalog/catalog_test.go:88`–`:105`；`internal/payment/intent.go`；commit `90e9ce3`。

### Q46：Catalog version 为什么 immutable？为什么还需要 current version pointer？

#### 30 秒回答

版本 payload 一旦参与 CandidateSet、Episode snapshot 或支付 Payee binding，就不能原地修改；否则同一个 `catalog://merchant/capability/v1` 的 hash 和含义会随时间变化，历史 replay 也无法解释当时依据。

但 discovery 不能每次扫描全部历史版本，因此另外维护一个 `(MerchantDID, CapabilityID) → current CatalogVersion` pointer。注册新版本时只推进 pointer，不修改旧版本；`ListActiveCapabilities` 只从 pointer 指向的版本中返回 ACTIVE + AVAILABLE 记录。

#### 源码落点

`commerce-runtime/internal/repository/repository.go:67`–`:78`；`internal/repository/inmemory.go:56`–`:141`；`internal/infrastructure/mysql/repository.go:250`–`:347`；`merchant_capabilities` 和 `merchant_capability_current` migration。

### Q47：inactive v2 后为什么不能 fallback 到历史 v1 ACTIVE？

#### 30 秒回答

下架是对当前 capability 的事实决策，不是“最新版本不可用就继续找旧版本”。如果 v2 是 INACTIVE/DEPRECATED，current pointer 仍指向 v2；active discovery 读取 pointer 后发现它不可 eligible，就不会把历史 v1 重新暴露。否则运营方以为已经下架，Runtime 却可能继续支付旧 Payee、旧 endpoint 或旧价格。

这也是 S3 final acceptance 修复的关键：immutable history、current pointer、active eligibility 是三个不同概念，不能用“历史上曾经 ACTIVE”覆盖当前停用状态。

#### 源码落点

`internal/infrastructure/mysql/repository.go:279`–`:290`、`:318`–`:347`；`internal/repository/inmemory.go:83`–`:141`；`internal/repository/inmemory_test.go:70`–`:123`、`internal/infrastructure/mysql/s3_integration_test.go:30`–`:104`；commit `90e9ce3`。

### Q48：CandidateSet 为什么需要 persisted fact，而不是每次选择时重新查 Catalog？

#### 30 秒回答

Discovery 得到的是一次带时间、查询 hash、候选版本和排序结果的事实。若 SELECT 时重新查 live Catalog，Catalog 变化就会让同一个 Episode 在重试中换商户、换 Payee 或换排序，失去 snapshot isolation。

S3 把 CandidateSet 存入 InMemory/MySQL，并让 selection 只从指定 CandidateSet 读取；Discovery 的默认 ID 是 `cs:<episode_id>`，因此 response 丢失后可以找回同一 operation。`candidate_sets` 表保存 Episode、QueryHash、候选列表、生成/过期时间和 hashes。

#### 源码落点

`commerce-runtime/internal/application/service.go:190`–`:250`；`internal/repository/inmemory.go:144`–`:185`；`internal/infrastructure/mysql/repository.go:350`–`:390`；`migrations/001_create_commerce_runtime.sql:166`–`:180`。

### Q49：CandidateSet 为什么要有 FactsRef 和 PayloadHash？

#### 30 秒回答

`FactsRef` 指向这组候选事实的稳定引用，便于 Event/Observation 审计；`PayloadHash` 对 CandidateSet 的 canonical payload 做 SHA-256，便于检测存储损坏、重放时内容变化和有人偷偷改 candidate/payee。

Hash 不是权限本身，也不是 quote 签名；它和 CandidateSet scope、membership、snapshot hash、runtime guard 一起构成事实完整性检查。`Validate` 会重算 payload hash，MySQL/InMemory 保存相同 ID 的不同事实会报 conflict。

#### 源码落点

`commerce-runtime/internal/catalog/catalog.go:480`–`:569`；`internal/repository/inmemory.go:144`–`:172`；`internal/infrastructure/mysql/repository.go:350`–`:383`；`internal/catalog/catalog_test.go:108`–`:118`。

### Q50：SELECT_MERCHANT 为什么不能直接接受模型写的 MerchantDID？hallucinated merchant 和 filtered merchant 如何处理？

#### 30 秒回答

Proposal 只能提供 CandidateSetID 和 MerchantDID/CapabilityID 目标；Runtime Guard 会校验 CandidateSet 属于当前 Episode/Request、候选确实是 set 的成员、候选仍在有效期内，并核对可选的 version/hash/ref。模型写一个 Catalog 中不存在的 merchant，是 `ErrMerchantNotInCandidateSet`；真实存在但因预算、协议、内容类型、状态或时间被 hard filter 掉的 merchant，同样不能被选。

所以“存在”不是“有资格”，“模型知道它”也不是“Runtime 信任它”。S3 还会把通过 guard 的 immutable snapshot 写入 Episode，而不是把模型原始 target 当事实。

#### 源码落点

`commerce-runtime/internal/decision/decision.go:151`–`:204`；`internal/application/service.go:391`–`:445`；`internal/application/s3_catalog_test.go:25`–`:125`。

### Q51：为什么 PayeeDID 不让 Proposal 提供？S3 如何把选中的 Payee 交给 S2？

#### 30 秒回答

PayeeDID 是资金副作用字段，不能由模型自由填写，否则模型可以把一个合法 capability 改成另一个收款方。Proposal 只选择 CandidateSet 中的 MerchantDID + CapabilityID；Runtime 从 frozen CandidateSet 解析 PayeeDID，并把 CatalogVersion、SnapshotHash、SnapshotRef 和 selected candidate 绑定到 Episode。

S2 `ReservePaymentIntent` 在创建 Intent 前重新检查 selected CandidateSet、catalog snapshot 和 quote Payee；quote 的 Payee 与 CandidateSet 不一致就拒绝。这是 S3 → S2 的边界，而不是“选择成功就自动授权付款”。

#### 源码落点

`commerce-runtime/internal/decision/decision.go:151`–`:203`；`internal/application/payment_runtime.go:173`–`:185`、`:248`–`:271`；`internal/application/s3_catalog_test.go:48`–`:91`。

### Q52：Catalog mutation 后旧 Episode 为什么仍绑定旧 snapshot？这和 TOCTOU 有什么关系？

#### 30 秒回答

Episode 在 selection 时保存 CandidateSetID、CatalogVersion、CatalogSnapshotHash 和 SnapshotRef；之后即使 Catalog 注册 v2，旧 Episode 仍依据已经选中的 v1 fact。这样“检查时看到 v1”和“支付时使用的 Payee/能力”不会因为中间 mutation 变成两套对象。

这就是 Catalog 场景的 TOCTOU：只在 discovery 时检查一次是不够的，选择时要从 persisted CandidateSet 读事实、检查 hash/scope/validity，PaymentIntent 创建时还要检查 quote Payee 与 selected snapshot。一致性边界是冻结事实，不是永远相信 live Catalog。

#### 源码落点

`commerce-runtime/internal/application/service.go:408`–`:415`；`internal/application/payment_runtime.go:173`–`:185`；`internal/application/s3_catalog_test.go:48`–`:91`、`:161`–`:207`；commit `90e9ce3`。

### Q53：CandidateSet expiry 和 Catalog `ValidUntil` 有什么区别？为什么 selection 时还要检查 frozen candidate 的 ValidUntil？

#### 30 秒回答

CandidateSet expiry 表示“这次 discovery 结果还能不能被这次 Episode 使用”；Catalog `ValidUntil` 表示“候选能力版本本身还能不能作为当前事实”。前者是 operation-level TTL，后者是每个 catalog snapshot 的业务有效期，二者可能不同。

因此 selection 先调用 `CandidateSet.ValidateAt(now)`，还要检查 candidate 的 `CatalogValidFrom/ValidUntil`。CandidateSet 没过期，不代表里面的某个 catalog snapshot 可以无限使用；这正是 S3 final acceptance 新增的 frozen candidate expiry test。

#### 源码落点

`commerce-runtime/internal/catalog/catalog.go:480`–`:520`；`internal/decision/decision.go:167`–`:188`；`internal/application/s3_catalog_test.go:209`–`:249`。

### Q54：`price_hint`、TrustedPaymentQuote、settlement 分别是什么？

#### 30 秒回答

`price_hint` 是 Catalog 中帮助 eligibility/ranking 的非最终价格提示，可以缺省，不能证明商户已经承诺一个交易价格。`TrustedPaymentQuote` 是后续支付边界需要的、绑定 Merchant/Capability/Payee/金额/币种/QuoteHash/expiry 的可信报价。`settlement` 则是 Payment/chain 已确认的资金事实。

三者分别属于 discovery hint、payment authorization input、external payment outcome。把 price hint 当 quote，会让目录描述直接变成付款授权；把 quote 当 settlement，又会在链上事实确认前宣布已付款。

#### 源码落点

`commerce-runtime/internal/catalog/catalog.go:94`–`:127`、`:361`–`:385`；`internal/application/payment_runtime.go:160`–`:209`；`internal/payment/intent.go`。

### Q55：为什么 `price_hint` 不能直接创建 PaymentIntent？

#### 30 秒回答

S3 discovery 只回答“哪些候选满足当前 Contract 的硬条件，以及排序如何”；它不代表商户已返回 quote，也没有完成 402 challenge、policy、DID authorization 或 payment binding。`RegisterCapabilityVersion` 的 comment 也明确说 catalog hint 不会变成 payment quote。

所以从 CandidateSet 到 PaymentIntent 还必须经过未来的 Merchant Invoke/402 consumption，得到 `TrustedPaymentQuote` 后才调用 S2 reserve。当前直接用 price hint 创建 Intent 是跨越 trust boundary，文档不能把它写成已实现。

#### 源码落点

`commerce-runtime/internal/application/service.go:164`–`:171`；`internal/application/payment_runtime.go:160`–`:209`；`internal/catalog/catalog.go:94`–`:127`。

### Q56：NO_ELIGIBLE_CANDIDATE 为什么走 deterministic terminal path，而不是调用 LLM 幻想一个商户？

#### 30 秒回答

如果 hard eligibility 结果为空，Runtime 已经知道当前 Contract、预算、协议、内容类型和时间约束下没有可信候选。调用 LLM“猜一个”只能把不满足事实约束的对象重新包装成文本，不能凭空增加可支付商户。

S3 会记录 `NO_ELIGIBLE_CANDIDATE` observation，再以稳定的 stop action 写入 `NO_ELIGIBLE_MERCHANT` terminal reason；没有 candidate 时不进入 SELECT_MERCHANT，也不创建 PaymentIntent。这样失败是可重放、可解释、不会产生资金副作用的。

#### 源码落点

`commerce-runtime/internal/application/service.go:253`–`:286`；`internal/application/s3_catalog_test.go:127`–`:159`；`internal/trace/trace.go:20`–`:57`。

### Q57：deterministic ranking 为什么需要 stable tie-breaker？

#### 30 秒回答

hard filter 决定“能不能选”，ranking 决定“候选顺序”。如果两个候选 protocol preference、output compatibility 和 price hint 都相同，直接依赖 map/数据库返回顺序会让重试和不同实例得到不同 winner。

当前排序先按 protocol preference、output compatibility、price hint known/金额，再按 MerchantDID、CapabilityID、CatalogVersion 和 snapshot hash 做稳定比较；因此排序不依赖 wall clock 或输入 slice 顺序。

#### 源码落点

`commerce-runtime/internal/catalog/catalog.go:450`–`:477`；`internal/catalog/discovery.go:174`–`:181`；`internal/catalog/catalog_test.go:28`–`:60`。

### Q58：同一个 Contract + 同一个 Catalog snapshot 为什么应该得到相同 CandidateSet ordering？

#### 30 秒回答

DiscoveryQuery 有 canonical normalization 和 query hash，Catalog capability 有 canonical snapshot/hash，CandidateSet 又保存排序后的 candidate list 和 payload hash。在同一个生成时间有效窗口内，输入事实和排序函数相同，输出顺序就应相同；这让 replay 能验证事实，而不是重新做一次不确定搜索。

测试故意用不同输入顺序构造 capabilities，要求 CandidateSet candidates 和 PayloadHash 相同。注意这不是说未来动态商户源永远不变，而是说一次已冻结的 discovery fact 可以稳定重建和校验。

#### 源码落点

`commerce-runtime/internal/catalog/catalog.go:417`–`:477`、`:535`–`:569`；`internal/catalog/catalog_test.go:28`–`:60`。

### Q59：Discovery response 丢失后如何 retry？为什么需要 operation-level idempotency/replay？

#### 30 秒回答

如果 CandidateSet 已保存、EpisodeEvent 已提交但 response 在网络中丢失，客户端重试不能重新扫描 Catalog 并创建另一组候选。S3 对默认 discovery 使用 `candidateSetID = cs:<episodeID>`，action key 为 `discover:<candidateSetID>`；重复请求先按 action identity 找旧 Event，再返回原 CandidateSet、Episode 和 terminal event。

同一个 operation、同一个 payload 返回 replay；不同 discovery identity 在同一已推进 Episode 上被拒绝；CandidateSet ID 对应不同 payload 也会产生 conflict。这样 response retry 是恢复同一事实，不是新一轮商户选择。

#### 源码落点

`commerce-runtime/internal/application/service.go:190`–`:224`、`:257`–`:286`；`internal/repository/inmemory.go:144`–`:185`；`internal/application/s3_catalog_test.go:161`–`:207`；`internal/infrastructure/mysql/s3_integration_test.go:319`–`:380`。

## 真实踩坑与复盘

### 1. Business minor vs SPL raw unit

- **现象**：`0.01 USDC = 1 minor`，若直接写 `1` 到 instruction，真实链上少 `10,000` 倍。
- **单测为什么会漏**：mock chain 只验证调用成功，或测试只看业务 amount。
- **修复**：`BusinessMinorToTokenRaw` 只在 Adapter boundary 转换；上游签名、DB、event 保留业务 amount。
- **证据**：`30b10067`、`token_amount.go`、`token_amount_test.go`。

### 2. Gateway exact-body signature

- **现象**：签名 helper 和 HTTP client 使用了不同 JSON bytes。
- **修复**：固定 `METHOD/path/query/bodySHA256`，用 `--data-binary` 发送签名时的原始 body。
- **证据**：`signature.go`、`test-deterministic-e2e.ps1:86`–`:100`。

### 3. Gateway/payment nonce 分离

- **现象**：诊断验签或 HTTP retry 复用了业务 nonce，造成不同防重放层互相污染。
- **修复**：Gateway nonce 与 Payment nonce 独立；支付 retry 换 Gateway nonce，但复用业务 request/idempotency key。
- **证据**：`e2e-client/main.go`、`test-deterministic-e2e.ps1:244`–`:265`。

### 4. RocketMQ topic/readiness

- **现象**：容器端口已监听，但 broker 尚未注册、topic 未创建或 consumer 未 ready。
- **修复**：nameserver 预处理、物理 topic 固定、脚本创建 topic、日志确认 consumer ready。
- **证据**：commit `8cc16ff`、`rocketmq_consumer.go`、E2E 脚本。

### 5. Devnet hot wallet 与 Agent identity

- **现象**：混用后无法区分业务授权主体和 fee payer；测试还会掩盖 client partial signing。
- **修复**：E2E 拒绝同一路径；Agent 自己签 transaction/payload，hot wallet 负责 fee payer/补签。
- **证据**：`e2e-client/main.go` 的 `samePath`、signer 和 balance 检查。

### 6. at-least-once event replay

- **现象**：同一 success event 被 replay 或并发 redelivery。
- **修复**：稳定 `event_id`、消费前查 event id、DB race 后二次查询、兼容 legacy rows。
- **证据**：`verification-service/internal/infrastructure/messaging/rocketmq_consumer.go:110`–`:133`、E2E replay。

### 7. S1 把 Proposal、Guard、Projection 和 Event 分开

- **问题**：如果让模型输出直接写 Episode state，就无法证明它是否基于当前状态、当前 Observation 和允许的迁移推进。
- **实现**：`DecisionProvider` 只返回 `DecisionProposal`；`RuntimeGuard` 校验 episode、event sequence、evidence、deadline、attempt 和 action；`CommitProposal` 生成结构化 `EpisodeEvent`，由 `TransitionStore` 原子更新 Projection + Event。
- **并发处理**：MySQL 用事务、行锁、version 条件更新和 `(episode_id, idempotency_key)` 唯一约束；同 key 重试返回 replay，不同 body 冲突报错。
- **证据**：`commerce-runtime/internal/decision/decision.go:81`、`commerce-runtime/internal/application/service.go:124`、`commerce-runtime/internal/infrastructure/mysql/repository.go:204`、`0e5c615` 的集成测试。

### 8. 不能夸大的可靠性结论

- Payment idempotency 能防主要 HTTP duplicate，但不是 DB 与链上副作用的 exactly-once。
- Projection 有幂等，但当前没有完整 Outbox 事务。
- DID nonce 是进程内 cache，不能说成多实例全局 replay store。
- Harness 代码有，但默认关闭。
- Purchase proof 不等于 delivery validation。
- S2 有 Ledger/Payment Runtime，但 refund accounting 不等于 external refund workflow，Kitex adapter 也不等于完整 Commerce E2E。
- S3 已实现 trusted Merchant Catalog、structured Discovery、CandidateSet 和 selection guard，但没有把 Merchant Invoke、Delivery Validator、同/跨商户 recovery 接成完整 Runtime。

### 9. HTTP adapter transport mismatch

- **早期 prototype**：Commerce Runtime 直接 `POST /api/v1/pay`。
- **问题**：Payment Service 的 canonical transport 是 Kitex；HTTP payment 必须经 Gateway，直接 POST 会绕过 Gateway canonical auth/nonce 边界，不能算 production integration。
- **最终**：`KitexPaymentAdapter` 是 production adapter；`HTTPGatewayPaymentAdapter` 只保留 optional/test path，并明确没有实现完整 Gateway authentication headers。
- **教训**：interface 存在、HTTP fake 能测通，不等于 production integration 已接上真实服务边界。
- **证据**：`commerce-runtime/internal/adapters/kitex_payment.go`、`internal/adapters/http_payment.go:40`、`internal/adapters/kitex_payment_test.go`、commit `4e4c87a`、`2a3b8e2`。

### 10. CapabilityID != PayeeDID

- **早期问题**：把 `CapabilityID` 映射成 `skill_did`。
- **为什么错**：CapabilityID 是能力资源标识，PayeeDID 是实际收款主体；混用会破坏身份、支付收款和多 capability 建模。
- **最终**：`MerchantDID`、`CapabilityID`、`PayeeDID` 独立进入 Intent、authorization binding 和 EconomicKey；Kitex `SkillDid` 使用 `PayeeDID`。
- **证据**：`commerce-runtime/internal/payment/intent.go`、`internal/adapters/kitex_payment.go:51`–`:62`、`internal/adapters/kitex_payment_test.go`、commit `2a3b8e2`。

### 11. 模型仍能写 PAYMENT_FAILED

- **问题**：`PAYMENT_FAILED` 虽然不等于 settlement，但它仍是 environment fact；如果 LLM 自己提交，Runtime 会把未验证的文本当成外部事实。
- **修复**：`CommitProposal` 拒绝 `PAYMENT_AUTHORIZATION_CHECKED`、`PAYMENT_SUBMITTED`、`PAYMENT_PENDING`、`PAYMENT_FAILED`、`PAYMENT_CONFIRMED`、`PAYMENT_UNKNOWN` 和 entitlement factual actions。只有 adapter outcome 经过 deterministic runtime method 和 finance transaction 才能写入。
- **证据**：`commerce-runtime/internal/application/service.go:141`–`:224`、`internal/application/payment_runtime.go:344`–`:548`、`internal/decision/payment_guard.go`、commit `4e4c87a`。

### 12. SUBMITTING crash window

- **场景**：`local SUBMITTING commit → process crash → remote submit outcome unknown`。
- **错误做法**：新建 PaymentIntent 或换一组金额、Payee、Quote 重新付款。
- **最终**：先 `reconcile`；仍 unresolved 时对原 Intent 做 exact same economic command redelivery，不增加新的 payment attempt，不改变 RequestFingerprint/CredentialRef/IdempotencyKey。
- **证据**：`commerce-runtime/internal/application/payment_runtime.go:271`–`:344`、`internal/reconciliation/reconciliation.go`、`internal/application/payment_runtime_test.go:225`、commit `f5e9435`、`4e4c87a`。

### 13. Entitlement 串单

- **问题**：“以前买过”不能证明“当前 Intent 成功”。只看 Agent–Skill 历史 purchase projection 会把别的 payment/tx 的 entitlement 串到当前请求。
- **修复**：Entitlement query 带 EpisodeID、IntentID、TxID、MerchantDID、CapabilityID、PayeeDID 和 RequesterDID；`MatchesIntent` 要求当前 Intent/Tx identity 和 evidence/ref 绑定。
- **证据**：`commerce-runtime/internal/adapters/adapters.go:78`–`:124`、`internal/application/payment_runtime.go:548`–`:604`、`internal/reconciliation/reconciliation.go:67`–`:78`。

### 14. UNKNOWN 被错误写成 INVALID

- **问题**：Entitlement 查询失败或证据不足时，如果直接写 `INVALID`，Episode 会错误进入 `FAILED`，下一步无法继续 reconcile。
- **最终语义**：`UNKNOWN → CLAIMING → ENTITLEMENT_UNKNOWN`；`INVALID → FAILED`。UNKNOWN 是 same-state event，不是失败 transition。
- **教训**：Observation 的语义准确性直接决定下一步 Action；不能把“没有证据”写成“证据明确无效”。
- **证据**：`commerce-runtime/internal/trace/trace.go:50`–`:55`、`internal/application/payment_runtime.go:548`–`:604`、`internal/application/payment_runtime_test.go:133`、commit `2a3b8e2`。

### 15. MerchantDID 与 PayeeDID 被错误要求不相等

- **早期问题**：Catalog validation 曾把 `MerchantDID == PayeeDID` 当成非法，假设能力提供者和收款者必须是两个不同身份。
- **为什么错**：字段需要语义分离，但商户自己收款是合法业务；semantic separation 不等于 value inequality。
- **最终**：移除不相等约束，保留 MerchantDID / CapabilityID / PayeeDID 独立字段和 downstream binding；测试覆盖 shared identity。
- **证据**：`commerce-runtime/internal/catalog/catalog.go:191`–`:223`、`internal/catalog/catalog_test.go:88`–`:105`、commit `90e9ce3`。

### 16. inactive v2 无法真正下架 active v1

- **早期问题**：current pointer 或 discovery 只看历史记录中的 ACTIVE 版本，导致 v2 INACTIVE 后仍可能 fallback 到 v1 ACTIVE。
- **为什么错**：immutable history、current version 和 active eligibility 是三个不同概念；下架当前版本后不能重新暴露旧版本。
- **最终**：注册任意新版本都推进 current pointer；`ListActiveCapabilities` 只读取 pointer 指向且当前 ACTIVE + AVAILABLE 的版本，不回退历史版本。
- **证据**：`internal/infrastructure/mysql/repository.go:250`–`:347`、`internal/repository/inmemory.go:56`–`:141`、`internal/repository/inmemory_test.go:70`–`:123`、`internal/infrastructure/mysql/s3_integration_test.go:30`–`:104`、commit `90e9ce3`。

### 17. CandidateSet TTL 与 Catalog ValidUntil 被混成一个时间条件

- **早期问题**：只检查 CandidateSet 没过期，就认为 frozen candidate 可以继续选择。
- **为什么错**：CandidateSet TTL 是 discovery operation 的有效期；Catalog `ValidUntil` 是候选能力 snapshot 的业务有效期。snapshot isolation 不等于忽略时间有效性。
- **最终**：Candidate 额外保存 `CatalogValidFrom/ValidUntil`；selection 同时检查 CandidateSet `ValidateAt(now)` 和 candidate catalog validity，过期时拒绝选择。
- **证据**：`commerce-runtime/internal/catalog/catalog.go:387`–`:520`、`internal/decision/decision.go:167`–`:188`、`internal/application/s3_catalog_test.go:209`–`:249`、commit `90e9ce3`。

### 18. Discovery response lost 后重试生成了另一组候选

- **问题场景**：CandidateSet/Event 已提交，但 HTTP/RPC response 丢失；如果 retry 重新扫描 live Catalog，可能得到不同版本、不同排序或不同 Payee。
- **最终**：默认 discovery 使用 `cs:<episode_id>` 和稳定 action key；重试先 replay 原 Event/CandidateSet，CandidateSet ID 对应不同 payload 则冲突；S3/MySQL 测试验证同 operation 不新增 Event。
- **教训**：Discovery 也有 operation-level idempotency；恢复 response 不能等价于开启新一轮 discovery。
- **证据**：`commerce-runtime/internal/application/service.go:190`–`:224`、`internal/repository/inmemory.go:144`–`:185`、`internal/application/s3_catalog_test.go:161`–`:207`、`internal/infrastructure/mysql/s3_integration_test.go:319`–`:380`、commit `90e9ce3`。

## 当前进度与 Planned 边界

### IMPLEMENTED

- CloudWeGo Hertz Gateway、Kitex/Thrift 服务边界和 IDL 契约检查。
- DID、Gateway canonical、PaymentSignature、业务 nonce、idempotency、余额检查。
- SPL Token、Mint、ATA、fee payer、recent blockhash、base64、Devnet 状态确认。
- 业务 minor 到 token raw 的边界转换。
- RocketMQ producer/consumer、购买投影、proof、event replay 验收。
- Agent Payment Harness 代码：policy、DID approval、intent TTL、allowlist、GETDEL。
- Commerce Runtime S1：Contract normalization/canonical snapshot、CommerceEpisode 状态机、BudgetSnapshot、DecisionProposal、Runtime Guard、EpisodeEvent、replay。
- S1 MySQL TransitionStore：Projection + Event 原子提交、immutable contract、optimistic version、request/action idempotency；InMemoryStore 用于确定性单测。
- S1 测试：deterministic flow、terminal/deadline、proposal guard、replay、同 key 重试、并发 transition、MySQL 原子性。
- S2 append-only LedgerEntry、Ledger-derived Budget Projection、reserve/release/settle/refund、`consumed/available/sunk_cost`、`RefundReusable`。
- Runtime-owned PaymentIntent、EconomicIdentityKey、RequestFingerprint、opaque CredentialRef、payment authorization guard。
- MerchantDID / CapabilityID / PayeeDID separation、KitexPaymentAdapter、canonical PaymentService contract mapping。
- Payment pending/failed/unknown/confirmed、unknown reconciliation、SUBMITTING crash recovery、exact idempotent redelivery。
- Payment failure/authorization denial/expiry compensation、entitlement binding、`ENTITLEMENT_VALID/INVALID/UNKNOWN`。
- MySQL finance transaction：Episode Projection、EpisodeEvent、LedgerEntry、PaymentIntent atomic persistence；S2 adapter/runtime tests。
- S3 `MerchantCapability` domain：MerchantDID / CapabilityID / PayeeDID independent semantics、structured validation、canonical snapshot/hash、immutable catalog version history 和 current-version pointer。
- S3 `DiscoveryQuery`：从 Acquisition Contract 派生、hard eligibility filtering、deterministic ranking、stable tie-breaker、price hint 只作筛选/排序事实。
- S3 CandidateSet：persisted fact、`FactsRef`、`PayloadHash`、CandidateSet TTL、candidate catalog `ValidFrom/ValidUntil`、discovery replay。
- S3 selection guard：CandidateSet scope/membership、hallucinated/filtered merchant rejection、catalog snapshot binding、selected Payee resolution、S3 → S2 PaymentIntent payee consistency。
- S3 deterministic terminal/repository：`NO_ELIGIBLE_CANDIDATE` terminal path、MySQL Catalog/current pointer/CandidateSet persistence、same-version conflict and replay tests。

### IN PROGRESS

- Harness 已实现但默认关闭，尚未成为默认支付强制门禁。
- S2 Runtime 是 deterministic finance/payment core；Production adapter 是 Kitex，HTTP adapter 仅 optional/test。
- S3 Runtime 是 deterministic trusted catalog/discovery core；Catalog current pointer、CandidateSet fact 和 selection guard 已实现，但还不是 Merchant Catalog → 402 → invoke → delivery 的完整 E2E。
- Chain unknown、MQ publish 丢失、多实例 nonce、external refund workflow 仍有加固空间。

### PLANNED

- 真实 `402 → TrustedPaymentQuote` consumption、Merchant Invoke、Delivery Validator、真实 delivery evidence、same-merchant retry。
- Cross-merchant switch/recovery、Ask Parent、external refund workflow、完整 compensation orchestration。
- LLM DecisionProvider、bounded inner loop、真实 402/Delivery Observation adapter、RAG、Memory。
- Working/Episodic/Semantic/Procedural Memory、Workflow versioning、Replay/Canary/Rollback、Outer Loop。

---

## 面试速记页

### 三句话说清项目

1. StablePay 已经从“Agent 能付款”演进到“Commerce Runtime 对能力获取和资金副作用进行受控编排”：S1 管 Contract/Episode/Event，S2 管 Ledger/PaymentIntent/reconciliation，S3 管 trusted Catalog/structured Discovery/CandidateSet，底层仍由确定性 Payment Plane 执行。
2. 我参与的重点是六服务边界、真实 Devnet 链路和 exact body、nonce、topic/readiness、event replay、token raw unit 等跨层问题。
3. S3 已能对 trusted merchant facts、hard eligibility、deterministic candidate ranking、selection snapshot 和 Payee binding 做确定性编排；真实 402 consumption、Merchant Invoke、Delivery Validator 和 recovery loop 仍从 S4 开始。

### 一分钟架构

```text
Hertz Gateway
  → DID auth / Gateway nonce / rate limit
  → Kitex
Payment Service
  → PaymentSignature / business nonce / MySQL idempotency / balance
  → Blockchain Adapter
  → SPL Token / ATA / fee payer / Solana Devnet
  → polling
  → RocketMQ payment_events
  → Verification purchase projection / proof

Commerce Runtime
  → immutable Acquisition Contract snapshot
  → CommerceEpisode / EpisodeEvent
  → Trusted Merchant Catalog / current version
  → DiscoveryQuery / hard filter / deterministic ranking
  → CandidateSet facts_ref / payload_hash / expiry
  → SELECT_MERCHANT guard / immutable catalog snapshot / Payee resolution
  → Decision Proposal / Runtime Guard
  → append-only Ledger / Budget Projection
  → PaymentIntent / authorization guard
  → Reconciliation / entitlement binding
  → deterministic KitexPaymentAdapter
       ↓
  StablePay Payment Plane

LLM/DecisionProvider cannot write financial facts.
```

### 五个最重要设计选择

1. GatewaySignature、PaymentSignature、Solana transaction signature 分层。
2. 业务 amount 保持 minor 语义，只在 blockchain boundary 转 raw。
3. HTTP retry 不等于再次支付：nonce、idempotency、tx id、event id 各自控重。
4. MQ 接受 at-least-once，Verification 用 event id/业务关系做幂等 projection。
5. LLM/Agent 只能提出意图或 proposal；Runtime Guard、Ledger、PaymentIntent 和 adapter 控制真实副作用。
6. Ledger 是财务事实，EpisodeEvent 是 Runtime trace；BudgetSnapshot 只是 Projection。
7. Production payment integration 使用 Kitex；HTTP adapter 只是 optional/test，不等于线上接入。
8. S3 Catalog facts 先经过 structured hard filter，再允许 Proposal 从 CandidateSet 中选择；S3 不等于 RAG。

### 五个真实 failure / trade-off

1. `0.01 USDC = 1 business minor = 10,000 SPL raw units`。
2. Gateway 必须签 exact raw body。
3. Gateway nonce 与 Payment nonce 分开。
4. RocketMQ topic/readiness 不能只看端口。
5. Chain timeout 是 unknown 风险；S2 用 reconcile + exact redelivery，settlement 不能 rollback。

S2 新增的 failure / trade-off：

6. HTTP adapter transport mismatch：interface 存在不等于 production Kitex integration。
7. CapabilityID ≠ PayeeDID：业务能力 ID 不能冒充收款身份。
8. SUBMITTING crash window：先 reconcile，再对同一 Intent exact redelivery。
9. UNKNOWN ≠ INVALID：Observation 语义错误会把 Episode 推到错误的下一步。

S3 新增的 failure / trade-off：

10. MerchantDID 与 PayeeDID 要语义分离，但值可以相同。
11. current pointer 指向最新版本；inactive v2 不能回退到历史 active v1。
12. CandidateSet TTL 不等于 catalog snapshot 永久有效；selection 仍要检查 Candidate ValidUntil。
13. Discovery response 丢失时 replay 原 CandidateSet，不创建新的 discovery operation。

S1 新增的并发 / 可靠性要点：Projection 与 EpisodeEvent 在同一 TransitionStore 事务中提交；同 key replay 返回原事件，不同输入冲突；旧 version 的并发提交失败。

### 核心安全边界

- GatewaySignature ≠ PaymentSignature ≠ Solana transaction signature。
- DID authentication ≠ payment authorization。
- `LLM Proposal ≠ Authorization`。
- `DecisionProposal ≠ financial fact`。
- hot wallet fee payer ≠ Agent identity。
- `PaymentIntent ≠ Payment Record`。
- `LedgerEntry ≠ EpisodeEvent`。
- `reserve ≠ settlement`。
- `payment confirmed ≠ entitlement valid`。
- `entitlement valid ≠ delivery valid`。
- `UNKNOWN ≠ FAILED`。
- `CapabilityID ≠ PayeeDID`。
- MerchantDID 与 PayeeDID 的 semantic separation ≠ value inequality。
- `Catalog fact ≠ prompt text`。
- `structured discovery ≠ RAG`。
- `candidate exists ≠ candidate eligible`。
- current catalog ≠ historical catalog version。
- `PriceHint ≠ TrustedPaymentQuote ≠ Settlement`。
- `CandidateSet ≠ live Catalog query`。
- `SELECT_MERCHANT Proposal ≠ trusted Payee`。
- catalog snapshot isolation ≠ infinite validity。
- `idempotent redelivery ≠ new payment retry`。
- Redis intent/nonce 是短期控制状态，不是财务事实源。
- `adapter interface ≠ production integration`。
- purchase proof ≠ delivery validation。
- payment settled ≠ Episode fulfilled。

### 当前进度

| 阶段 | 状态 |
| --- | --- |
| 六服务 deterministic plane、IDL、单测/契约检查 | **IMPLEMENTED** |
| Deterministic E2E 脚本与验收路径 | **IMPLEMENTED** |
| Agent Payment Harness | **IMPLEMENTED，默认关闭，迁移中** |
| Commerce Contract / Episode Core / Event Trace | **IMPLEMENTED，S1** |
| Finance / Payment Runtime / Ledger / Reconciliation | **IMPLEMENTED，S2** |
| S2.1 Payment Boundary Hardening / Semantic Cleanup | **IMPLEMENTED** |
| Merchant Catalog / Structured Discovery / CandidateSet Guard | **IMPLEMENTED，S3** |
| Merchant Invoke / 402 / Runtime Inner Loop / Delivery Validation | **PLANNED，S4** |
| Cross-merchant recovery / RAG / Memory / Workflow / Outer Loop | **PLANNED，等待 S5–S10** |

### S2/S3 合并后已经新增的问题

下面的问题现在可以从设计题升级为“我项目中这样实现了”；其中 Merchant Invoke、402 consumption、Delivery Validator 和完整 recovery 仍要标为 Planned：

- 为什么需要 `CommerceEpisode`，为什么不能把 `Payment` 当 aggregate？
- `Acquisition Contract` 为什么要 immutable snapshot 和 request hash？
- `EpisodeEvent` 为什么 append-only？Event 和 Projection 为什么同时保存？
- Episode optimistic lock 与 action idempotency 如何防止两个 `resume` 并发推进？
- `DecisionProposal` 为什么不是 `Decision`？它引用哪个 Observation sequence？
- LLM 为什么没有 state write 权限？Runtime guard 在哪一个函数执行？
- event replay 如何重建状态，如何处理 future event、duplicate event 和 schema version？
- S1 实际实现了哪些状态迁移，哪些仍只是 enum/interface？
- Episode 如何记录 payment pending/unknown，又如何避免复制 Payment 状态就宣布 Episode 完成？
- 为什么 S1 先做 deterministic `StaticDecisionProvider`，而不是直接接 LLM？
- 为什么 `CommitTransition` 必须同时提交 Projection 和 Event？
- 为什么 Episode 的 BudgetSnapshot 不能当资金事实源？
- 为什么要有 append-only LedgerEntry？EpisodeEvent 和 LedgerEntry 有什么区别？
- 为什么 PaymentIntent 不是 Payment Service 的 Payment？它代表钱还是允许尝试一次支付？
- EconomicKey 与 IdempotencyKey 有什么区别？为什么 PayeeDID 必须进入 EconomicIdentityKey？
- MerchantDID / CapabilityID / PayeeDID 分别是什么？为什么 CapabilityID 不能映射成 `skill_did`？
- reserve 为什么不是支付？为什么 CONFIRMED 先 release reservation 再 append settlement？refund 为什么 append 新 fact？
- `consumed=max(0, settled-refunded)` 和 `refund_reusable=false` 分别意味着什么？
- 什么是 unknown outcome、blind retry 和 exact idempotent redelivery？
- SUBMITTING crash window 如何恢复？RequestFingerprint 和 CredentialRef 解决什么问题？
- 为什么本地 MySQL transaction 不能 rollback Solana side effect？
- Payment settled 为什么只进入 CLAIMING？Entitlement evidence 如何绑定当前 Intent/Tx？
- ENTITLEMENT_UNKNOWN 和 INVALID 有什么区别？为什么 UNKNOWN 是 same-state event？
- 为什么 LLM 不能提交 PAYMENT_PENDING / FAILED / CONFIRMED？哪些 Action 是 runtime-owned factual action？
- authorization denied 或 Intent expired 后 reservation 如何 compensation？如何避免 `Episode PAYING + Intent FAILED` dead state？
