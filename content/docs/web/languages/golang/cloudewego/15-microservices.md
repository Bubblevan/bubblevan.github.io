# 15. 微服务架构
前面我已经分别学过几个看起来分散的主题：

```text
CloudWeGo Hertz：对外 HTTP 服务怎么写
Kitex + IDL：内部 RPC 服务怎么定义契约
ACK / K8s：服务怎么部署、发现、滚动更新
COLA 分层：单个服务内部怎么拆层
x402：Agent 支付时怎么用 HTTP 402 表达“需要付款”
```

这些知识点单独看都很碎。

但放回 StablePay 项目里，它们其实共同指向一个问题：

> 当一个后端系统不再是一个 main.go，而是拆成多个服务时，我到底应该怎么理解“微服务”？

我以前害怕“微服务”这个词，是因为它听起来像一整套成熟公司才会有的架构：注册中心、服务治理、链路追踪、熔断、限流、分布式事务、消息队列、Kubernetes、DevOps。

但真的做到 StablePay 这个项目时，我发现微服务不是从这些大词开始的。

它是从一个很朴素的问题开始的：

> 这个系统里有几类能力，它们的职责、风险、变化频率、依赖资源完全不一样，继续塞在一个服务里会越来越难维护。

StablePay 最初可以写成一个单体服务。一个 Go 程序里包含：

```text
DID 创建
签名校验
支付发起
链上转账
购买验证
余额查询
收益统计
HTTP 网关
```

这样当然能跑。

但很快会发现它很难维护。

身份签名出了问题，不应该影响余额查询。
Solana RPC 超时，不应该拖垮 DID 创建接口。
支付状态机要严格保证幂等，不应该和普通查询逻辑混在一起。
验证购买关系要高频读取，不应该和链上转账的慢路径耦合。
外部 HTTP 鉴权、限流、日志、request_id，不应该每个服务都重复写一套。
链上执行涉及热钱包、Gas 补贴、RPC 节点和交易确认，不应该散落在 Payment Service 里。

于是 StablePay 自然拆成了 6 个核心微服务：

```text
API Gateway
DID Service
Payment Service
Blockchain Adapter
Verification Service
Query Service
```

再加上我后来补的 Merchant Backend，它更像是接入 StablePay 的商家侧示例服务，不属于最核心的 6 大基础微服务，但它可以用来演示 Agent 如何购买商品。

这一章的重点不是背“微服务定义”，而是把 StablePay 的微服务拆分讲成一条自然决策链。

---

# 第一部分：MVP 手把手最小实现

## 13.1 从一个单体开始：所有逻辑都写在一个服务里

先假设我完全不懂微服务。

我只想做一个最小 StablePay：

```text
用户创建 DID
用户发起支付
系统校验签名
系统执行 Solana 转账
系统记录支付状态
系统验证是否购买
系统查询余额和交易记录
```

最简单的代码可能是：

```go
func main() {
    r.POST("/api/v1/did", createDID)
    r.POST("/api/v1/pay", createPayment)
    r.GET("/api/v1/pay/:tx_id", getPaymentStatus)
    r.GET("/api/v1/verify", verifyPurchase)
    r.GET("/api/v1/balance", getBalance)
    r.GET("/api/v1/transactions", listTransactions)
}
```

这就是单体。

它的好处很明显：

```text
开发简单
本地启动简单
函数之间直接调用
不用考虑服务间通信
不用考虑分布式事务
不用考虑服务发现
```

早期 MVP 这样写完全合理。

但是，当业务开始变复杂，我会发现这个单体服务里混了六类完全不同的东西。

```text
DID：身份和签名
Payment：支付状态机和幂等
Blockchain：链上交易和 RPC
Verification：购买关系和 proof
Query：余额、历史、统计、缓存
Gateway：外部入口、鉴权、限流、路由
```

这些东西的变化原因不一样。

如果 Solana RPC 节点换了，不应该改 DID 代码。
如果支付状态机加一个 `REFUNDING`，不应该影响 Query 的缓存。
如果 Gateway 增加限流策略，不应该重新发布 Blockchain Adapter。
如果 Query Service 被大量读请求打爆，不应该影响 Payment 的支付写流程。

这时我才开始思考拆服务。

---

## 13.2 第一次拆分：先把 API Gateway 拆出去

第一个最自然的拆分，是把 API Gateway 拆出来。

因为外部请求都有一些共同动作：

```text
生成 request_id
透传 trace_id
鉴权
限流
防重放
统一错误码
统一响应格式
路由到下游服务
```

如果没有 Gateway，每个服务都要重复写一套：

```go
func CreateDIDHandler(...) {
    extractRequestID()
    verifyAPIKey()
    checkRateLimit()
    recoverPanic()
    logAccess()
    ...
}

func CreatePaymentHandler(...) {
    extractRequestID()
    verifyAPIKey()
    checkRateLimit()
    recoverPanic()
    logAccess()
    ...
}
```

这很快会失控。

所以 API Gateway 的出现不是为了“架构上多一层”，而是因为我发现：

> 外部 HTTP 接入的通用治理能力应该集中处理，不应该散落在每个业务服务里。

于是第一版架构变成：

```text
Agent / 前端 / curl
      ↓
API Gateway
      ↓
后端业务服务
```

Gateway 做：

```text
统一 HTTP 入口
统一鉴权
统一限流
统一日志
统一 request_id / trace_id
统一错误码
统一响应格式
请求路由
```

它不做：

```text
不生成 DID
不决定支付状态机
不直接操作链上
不直接写 purchase records
不做收益统计
```

这是一条很重要的面试边界。

API Gateway 是“接入层”，不是“万能业务层”。

---

## 13.3 第二次拆分：把 DID Service 拆出去

接下来我会发现，身份相关逻辑也应该单独拆。

StablePay 用的是 `did:solana` 这一套身份体系。它涉及：

```text
DID 创建
钱包地址绑定
公钥保存
签名校验
身份状态 active / disabled
时间戳 / nonce 防重放
配置管理
```

这些逻辑安全性很高。

如果把 DID 逻辑直接写进 Payment Service，那么 Payment Service 会越来越胖：

```text
支付参数校验
签名校验
DID 查询
DID 状态判断
nonce 防重放
链上转账
支付状态机
幂等控制
```

这不合理。

所以第二个拆分是：

```text
DID Service：
    专门负责身份、钱包、公钥、签名和 DID 状态。

Payment Service：
    需要校验身份时，调用 DID Service。
```

这样 Payment Service 不需要知道 DID 内部怎么存，也不需要自己解析所有 DID 状态规则。

它只需要问：

```text
这个 agent_did 的签名是否合法？
这个 DID 是否 active？
这个 nonce 是否重复？
```

这就是微服务里的“职责边界”。

---

## 13.4 第三次拆分：把 Blockchain Adapter 拆出去

再往下做支付，会遇到 Solana。

链上交易不是普通业务逻辑。它涉及：

```text
RPC 节点
blockhash
交易构造
交易签名
交易提交
交易确认轮询
Gas 补贴
热钱包
SPL Token
ATA
链上错误码
网络超时
```

如果这些都写进 Payment Service，Payment Service 会同时承担两种语义：

```text
支付业务语义：
    谁付给谁？
    金额是否合法？
    是否重复支付？
    状态机怎么流转？
    幂等键如何处理？

区块链执行语义：
    Solana 交易怎么构造？
    blockhash 有没有过期？
    tx_hash 有没有确认？
    Gas fee 谁付？
    RPC 节点挂了怎么办？
```

这两类东西不能混。

于是 Blockchain Adapter 出现：

```text
Payment Service：
    管支付业务流程。

Blockchain Adapter：
    管链上执行和查询。
```

Payment Service 对 Blockchain Adapter 说：

```text
请帮我执行这笔稳定币转账。
请帮我查这个钱包余额。
请帮我查这个 tx_hash 状态。
```

Blockchain Adapter 不应该关心：

```text
这个商品是不是已经买过？
这个 Agent 是否有权限？
这个支付是否重复？
这个订单是否应该创建？
```

它只关心链上。

这就是服务边界设计里非常经典的一句话：

> Payment Service 处理支付业务语义，Blockchain Adapter 处理链上执行语义。

这句话面试一定要会讲。

---

## 13.5 第四次拆分：把 Verification Service 拆出去

支付成功以后，系统里会多出一种事实：

```text
某个 agent_did 已经购买了某个 skill_did
```

这件事和支付本身有关，但不等同于支付。

Payment Service 关心的是：

```text
这笔支付从 CREATED 到 COMPLETED 怎么走？
链上有没有成功？
幂等键有没有重复？
签名和 nonce 是否安全？
```

Verification Service 关心的是：

```text
agent_did + skill_did 是否存在购买关系？
购买 proof 是什么？
什么时候购买的？
tx_id / tx_hash 是什么？
开发者后端来验证时怎么快速返回？
验证请求要不要写审计日志？
```

如果每次商户都直接查 Payment Service 的支付表，会出现几个问题：

```text
Payment Service 的写流程和验证读流程耦合
高频验证查询可能影响支付主流程
验证日志和支付记录混在一起
购买关系的唯一性规则不清楚
proof 生成逻辑散落
```

于是 Verification Service 拆出来。

它的职责是：

```text
维护 purchase records
提供 VerifyPurchase 查询
提供 BatchVerifyPurchase
提供 GetPurchaseProof
写 verification logs
保证购买关系唯一性
```

这时面试官可能会问：

> “为什么 Payment Service 不能直接查自己表验证购买？”

可以回答：

```text
Payment Service 可以提供支付状态查询，但购买验证是另一个读模型。
支付状态面向支付生命周期，验证关系面向资源授权。
验证请求可能高频来自商户后端或 Gateway，如果全部打到 Payment Service，会把支付写流程和授权读流程耦合在一起。
所以我把购买关系和 proof 查询拆到 Verification Service。
```

---

## 13.6 第五次拆分：把 Query Service 拆出去

再往后，用户和开发者会有很多查询需求：

```text
查余额
查交易记录
查支付历史
查收益统计
查销售记录
按时间筛选
分页
排序
缓存
聚合统计
```

这些都不应该塞进 Payment Service。

Payment Service 的核心是写流程：

```text
发起支付
状态机流转
幂等控制
链上协调
支付结果落库
```

Query Service 的核心是读流程：

```text
读多
分页多
筛选多
缓存多
聚合多
性能优化多
```

读写的关注点完全不同。

于是 Query Service 拆出来：

```text
Payment Service：
    管支付写流程和状态。

Query Service：
    管余额、交易记录、收益统计、销售记录等读模型。
```

这也可以理解为一种轻量 CQRS：

```text
Command：
    Payment Service 处理支付写命令。

Query：
    Query Service 处理各种读请求。
```

这里不要把 CQRS 讲得太玄。

面试时说简单点：

```text
我不是一上来就上复杂 CQRS。
只是因为支付写流程和统计查询读流程的压力、索引、缓存策略不同，所以把 Query Service 拆出来。
```

---

## 13.7 最终六服务架构

最终 StablePay 六个核心服务可以这样看：

```text
                  ┌────────────────────┐
                  │    API Gateway      │
                  │  鉴权/限流/路由/日志 │
                  └─────────┬──────────┘
                            │
        ┌───────────────────┼────────────────────┐
        │                   │                    │
┌───────▼───────┐   ┌───────▼────────┐   ┌───────▼────────┐
│  DID Service   │   │ Payment Service │   │ Query Service   │
│ 身份/签名/DID  │   │ 支付状态机/幂等 │   │ 查询/统计/缓存  │
└───────────────┘   └───────┬────────┘   └───────┬────────┘
                            │                    │
                    ┌───────▼────────┐           │
                    │ Blockchain      │◄──────────┘
                    │ Adapter         │
                    │ 链上执行/查询   │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │ Solana Network  │
                    └────────────────┘

                    ┌────────────────┐
                    │ Verification    │
                    │ Service         │
                    │ 购买关系/proof  │
                    └────────────────┘
```

更准确的调用链可以写成：

```text
创建 DID：
Agent → Gateway → DID Service

发起支付：
Agent → Gateway → Payment Service
              → DID Service 校验签名
              → Blockchain Adapter 执行链上转账

查询支付状态：
Agent → Gateway → Payment Service

验证是否购买：
Merchant / Gateway → Verification Service

查询余额/历史/收益：
Agent / Developer → Gateway → Query Service
                               → Blockchain Adapter 或数据库/缓存
```

这就是 StablePay 的微服务版图。

---

## 13.8 本地 MVP 怎么跑这 6 个服务？

本地最小环境可以这样理解：

```text
先启动基础设施：
MySQL
Redis
RocketMQ

再启动六个服务：
Verification Service
Query Service
DID Service
Blockchain Adapter
Payment Service
API Gateway
```

它们分别监听：

```text
API Gateway：8080
DID Service：8081
Payment Service：8082
Blockchain Adapter：8083
Query Service：8084
Verification Service：8085
```

本地测试时，所有外部请求优先打 Gateway：

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
curl -X POST http://localhost:8080/api/v1/did
curl -X POST http://localhost:8080/api/v1/pay
curl http://localhost:8080/api/v1/balance
curl http://localhost:8080/api/v1/verify
```

这样我不需要让用户记住 6 个端口。

Gateway 是统一入口。

内部服务可以自己监听端口，但对外暴露的是 Gateway 的路由。

这也是面试里很重要的一点：

> 微服务不是让外部用户面对一堆服务端口，而是内部拆分，外部统一入口。

---

# 第二部分：八股概念基础知识点

## 13.9 微服务是什么？

一句话：

```text
微服务是把一个大系统按业务能力拆成多个可以独立开发、独立部署、独立扩缩容的小服务。
```

但这个定义太空。

结合 StablePay，更具体地说：

```text
微服务不是按技术层拆：
    controller-service-dao

而是按业务能力拆：
    DID、Payment、Blockchain、Verification、Query、Gateway
```

这是非常重要的区别。

错误拆法：

```text
UserController Service
PaymentController Service
DAO Service
Util Service
```

正确拆法：

```text
身份服务
支付服务
链上适配服务
验证服务
查询服务
网关服务
```

微服务拆的是业务边界，不是代码文件夹。

---

## 13.10 微服务和单体的区别

单体不是低级，微服务也不是天然高级。

单体的优点：

```text
部署简单
本地调试简单
调用链短
事务简单
开发初期效率高
```

单体的问题：

```text
模块边界容易腐烂
所有功能一起发布
一个模块故障可能拖垮整个应用
不同模块不能独立扩容
团队协作容易互相影响
```

微服务的优点：

```text
服务职责清晰
可以独立部署
可以独立扩缩容
故障隔离更好
技术实现可以按服务选择
团队可以按服务分工
```

微服务的问题：

```text
服务间通信复杂
分布式事务复杂
部署运维复杂
排障链路变长
本地联调变麻烦
需要网关、注册发现、日志、追踪、监控
```

所以面试回答不能说：

```text
微服务比单体好。
```

应该说：

```text
微服务解决了一部分复杂度，但也引入了新的复杂度。
StablePay 拆微服务，是因为身份、支付、链上执行、验证、查询、网关这些边界确实稳定且差异明显。
```

---

## 13.11 服务边界怎么划？

面试很容易问：

> “你们为什么这样拆服务？”

我可以从四个角度回答。

第一，职责边界。

```text
DID 负责身份。
Payment 负责支付。
Blockchain Adapter 负责链上。
Verification 负责购买关系。
Query 负责读模型。
Gateway 负责接入治理。
```

第二，变化频率。

```text
Gateway 的限流和路由可能经常变。
Payment 的状态机比较敏感，不能频繁乱改。
Blockchain Adapter 会随着链、RPC、SDK 变化。
Query 的字段和统计需求会经常变。
```

第三，性能特征。

```text
Query 是读多。
Payment 是写关键路径。
Blockchain 是慢外部依赖。
Verification 是高频授权查询。
Gateway 是所有流量入口。
```

第四，安全边界。

```text
DID 涉及签名和身份。
Payment 涉及扣款和幂等。
Blockchain Adapter 可能涉及热钱包。
Gateway 涉及外部流量防护。
```

所以 StablePay 不是按“代码量”拆服务，而是按“职责、变化、性能、安全”拆服务。

---

## 13.12 API Gateway 是什么？

API Gateway 是统一接入层。

它处理外部请求进入系统前后的通用逻辑：

```text
统一路由
统一鉴权
统一限流
统一熔断
统一日志
统一 request_id / trace_id
统一错误码
统一响应格式
协议转换
```

它不处理核心业务规则。

在 StablePay 里，Gateway 应该知道：

```text
/api/v1/did 去 DID Service
/api/v1/pay 去 Payment Service
/api/v1/verify 去 Verification Service
/api/v1/balance 去 Query Service
```

但它不应该知道：

```text
DID 如何生成
支付状态机如何流转
Solana 交易怎么构造
购买 proof 怎么签名
收益统计怎么算
```

这就是 Gateway 的边界。

如果面试官问：

> “为什么不把支付逻辑写在 Gateway？”

可以回答：

```text
Gateway 是接入层，适合做通用治理；支付逻辑属于 Payment Service。
如果把支付状态机、链上协调、幂等控制都写进 Gateway，Gateway 会变成上帝服务，失去统一接入层的意义。
```

---

## 13.13 服务间通信：HTTP 还是 RPC？

StablePay 里两种都存在。

对外：

```text
Agent / 前端 / curl → Gateway
```

这适合 HTTP，因为外部世界天然理解：

```text
URL
Header
JSON
HTTP 状态码
HTTP 402
```

对内：

```text
Payment Service → DID Service
Payment Service → Blockchain Adapter
Gateway → Verification Service
Query Service → Blockchain Adapter
```

这更适合 RPC，因为内部服务需要：

```text
强契约
生成 client
统一超时
统一重试
服务治理
IDL 演进
```

所以我可以这样回答：

```text
Hertz 用于对外 HTTP 接口，Kitex 用于内部 RPC 调用。
HTTP 适合开放边界，RPC 适合内部服务间强契约调用。
```

当然，MVP 阶段内部也可以先用 HTTP client。
但一旦服务数量变多，IDL + RPC 的优势就会显现。

---

## 13.14 服务发现是什么？

单机时代，我调用服务可能写：

```text
http://127.0.0.1:8082
```

但上 K8s 后，Pod 会重建，IP 会变。

如果 Payment Service 的 Pod IP 变了，Gateway 不可能每次手动改配置。

所以需要服务发现。

在 ACK/K8s 里，Service 就是最基础的服务发现入口。

```text
stablepay-payment-service
stablepay-did-service
stablepay-query-service
stablepay-verification-service
stablepay-blockchain-adapter
```

调用方不需要关心后面有几个 Pod，也不需要关心 Pod IP。

它只访问 Service DNS。

```text
Gateway → stablepay-payment-service:8082
Payment → stablepay-did-service:8081
Payment → stablepay-blockchain-adapter:8083
```

一句话：

```text
Pod 会死，Service 永存。
```

这句话很适合面试。

---

## 13.15 什么是服务治理？

服务拆开以后，调用链变长，必须有治理能力。

服务治理包括：

```text
超时
重试
熔断
限流
降级
负载均衡
健康检查
注册发现
日志
指标
链路追踪
```

不要把它们混在一起。

### 超时

每次远程调用都必须设置超时。

错误写法：

```go
client.Do(req) // 没有 timeout
```

如果 Blockchain Adapter 卡住，Payment Service 也会一直挂着。

正确思路：

```text
Gateway 调 Payment：短超时
Payment 调 DID：短超时
Payment 调 Blockchain：较长超时，但不能无限等
Query 调链上余额：有超时，有缓存兜底
```

### 重试

重试只适合临时失败。

但支付写请求不能无脑重试。

```text
查询余额失败：
    可以重试。

提交链上交易失败：
    必须结合 tx_id / idempotency_key / 状态查询，不能盲目重复提交。

创建支付失败：
    必须有幂等键，否则可能重复扣款。
```

### 熔断

如果 Blockchain Adapter 连续失败，Payment Service 不能无限堆请求。

可以熔断：

```text
短时间直接返回 blockchain unavailable
避免线程/协程堆积
给下游恢复时间
```

### 限流

限流主要在 Gateway 做第一层：

```text
IP 级限流
DID 级限流
接口级限流
```

服务内部也可以做细粒度保护，比如 Payment Service 对支付接口做更严格限流。

### 降级

Query Service 查链上余额失败，可以先返回缓存。
Payment Service 扣款不能随便降级成成功。
Verification Service 查询失败不能随便说 purchased=true。

所以降级要看场景。

---

## 13.16 幂等是什么？为什么支付系统必须有？

幂等是指：

> 同一个请求执行一次和执行多次，最终效果应该一致。

支付系统必须幂等，因为客户端可能重试：

```text
网络超时
Gateway 超时
用户重复点击
Agent 重试工具调用
Payment Service 调 Blockchain 超时
```

如果没有幂等，可能出现重复扣款。

StablePay 的支付请求应该带：

```text
X-Idempotency-Key
```

服务端可以组合：

```text
agent_did + skill_did + client_idempotency_key
```

作为幂等键。

处理逻辑：

```text
第一次请求：
    创建支付记录，进入 CREATED/PENDING。

同一个 key + 同样参数：
    返回第一次的 tx_id 和状态。

同一个 key + 不同参数：
    返回 idempotency key mismatch。
```

数据库上要有唯一索引。

这样即使并发请求同时进来，也只有一个能成功创建，另一个读已有结果。

面试金句：

```text
幂等不是为了让接口看起来规范，而是为了防止支付、链上交易这类副作用操作被重复执行。
```

---

## 13.17 分布式事务怎么处理？

微服务面试很喜欢问：

> “服务拆开以后，事务怎么办？”

在单体里，我可以用数据库事务：

```text
begin
insert payment
update balance
insert purchase_record
commit
```

但微服务里，Payment、Blockchain、Verification 可能是不同服务、不同数据库、不同外部系统。

不可能简单用一个本地事务包住 Solana 链上交易。

所以 StablePay 更适合用：

```text
本地事务 + 状态机 + 幂等 + 补偿 + 最终一致性
```

比如发起支付：

```text
1. Payment Service 创建 payment 记录，状态 CREATED。
2. 调 Blockchain Adapter 提交链上交易，状态 PENDING。
3. 查询链上确认成功，状态 CONFIRMED。
4. 业务完成，状态 COMPLETED。
5. 如果中间失败，进入 FAILED 或继续 PENDING 等待补偿查询。
```

如果调用 Blockchain Adapter 超时，不能马上判定失败。

因为可能出现：

```text
Payment Service 没收到响应
但链上交易已经提交成功
```

所以要进入 PENDING，然后通过 tx_hash 或交易状态查询补偿。

这就是为什么支付状态机不能只有 success/fail。

---

## 13.18 最终一致性是什么？

最终一致性不是“不一致也没关系”。

它的意思是：

> 在分布式系统里，短时间内不同服务看到的状态可能不同，但经过重试、补偿、事件同步后，最终会收敛到一致状态。

比如：

```text
Payment Service 已经确认支付成功
Verification Service 还没生成 purchase record
```

这时短暂查询可能失败。

系统要通过：

```text
重试
补偿任务
事件消费
幂等写入
定时校验
```

让购买关系最终补上。

面试时要强调：

```text
最终一致性不是放弃正确性，而是承认跨服务和链上系统不能用一个本地事务解决，所以通过状态机和补偿保证最终收敛。
```

---

## 13.19 可观测性：request_id、trace_id、日志

微服务一拆，最大的问题是排障变难。

单体里查一个日志文件就行。
微服务里一次请求可能经过：

```text
Gateway
Payment
DID
Blockchain Adapter
Verification
Query
```

如果没有统一 request_id / trace_id，就会找不到同一条请求的日志。

所以 Gateway 应该生成或透传：

```text
request_id
trace_id
```

每个服务日志都带上它。

这样排障时可以：

```bash
grep "trace_id=xxx" gateway.log
grep "trace_id=xxx" payment.log
grep "trace_id=xxx" blockchain.log
```

面试可以说：

```text
微服务不是拆完就结束，拆完以后必须有可观测性。
request_id 用于单次请求定位，trace_id 用于跨服务链路追踪。
没有这些，线上排障会非常痛苦。
```

---

## 13.20 微服务部署到 K8s 后，对应哪些资源？

一个服务在 ACK/K8s 里通常对应：

```text
Deployment：
    管 Pod 副本、滚动更新、回滚。

Service：
    提供稳定 ClusterIP 和 DNS，做服务发现。

ConfigMap：
    存非敏感配置。

Secret：
    存密码、API Key、私钥等敏感配置。

Ingress：
    对外 HTTP/HTTPS 路由。

Probe：
    livenessProbe / readinessProbe 健康检查。
```

比如一个 Payment Service 应该有：

```text
stablepay-payment-service Deployment
stablepay-payment-service Service
payment-config ConfigMap
stablepay-secrets Secret 引用
/healthz 和 /readyz 探针
```

这里要能讲清楚：

```text
Deployment 管“有几个 Pod、怎么更新”。
Service 管“别人怎么稳定访问这些 Pod”。
Ingress 管“公网流量怎么进来”。
ConfigMap/Secret 管“配置怎么注入”。
Probe 管“K8s 怎么判断服务是否可用”。
```

---

# 第三部分：排障过程实践

## 13.21 排障第一层：请求到底有没有进 Gateway？

现象：

```text
curl https://ai.wenfu.cn/api/v1/pay 返回 404
curl https://ai.wenfu.cn/api/v1/did 没响应
curl https://ai.wenfu.cn/merchant 返回前端 HTML
```

不要一上来怀疑 Payment Service。

先判断请求有没有进 Gateway 或对应后端。

排查顺序：

```bash
kubectl -n zheda-agent describe ingress stablepay-ingress
kubectl -n zheda-agent get ingress stablepay-ingress -o yaml
kubectl -n zheda-agent get svc stablepay-api-gateway
kubectl -n zheda-agent get endpoints stablepay-api-gateway
kubectl -n zheda-agent logs deploy/stablepay-api-gateway --tail=100
```

如果 Ingress 规则没生效，请求可能被前端兜底规则吃掉。

如果 Service 没有 endpoints，说明 Gateway Pod 没 Ready，或者 Service selector 和 Pod label 对不上。

排障思路：

```text
公网请求 → Ingress / ALB → Service → Endpoints → Pod → Hertz 路由
```

一层一层查，不要跳。

---

## 13.22 排障第二层：Gateway 到下游服务调不通

现象：

```text
Gateway 返回 502 / 503
日志显示 downstream unavailable
Gateway 自己 healthz 正常
```

这说明入口服务活着，但下游服务可能不可达。

排查：

```bash
kubectl -n zheda-agent get svc
kubectl -n zheda-agent get endpoints stablepay-payment-service
kubectl -n zheda-agent get pods -l app=stablepay-payment-service
kubectl -n zheda-agent logs deploy/stablepay-payment-service --tail=100
```

如果是 HTTP 调用，可以临时起 debug Pod：

```bash
kubectl -n zheda-agent run netshoot --rm -it \
  --image=nicolaka/netshoot -- /bin/bash

curl http://stablepay-payment-service:8082/healthz
```

如果是 Kitex RPC，要检查：

```text
服务名
端口
协议
IDL 版本
client 连接地址
K8s Service port / targetPort 是否一致
```

常见坑：

```text
服务监听 8082，但 Service targetPort 写错。
client 连接 127.0.0.1，在 Pod 里其实指自己。
Service selector 匹配不到 Pod。
Pod 没 Ready，所以 endpoints 为空。
```

---

## 13.23 排障第三层：支付重复或幂等失效

现象：

```text
用户重复支付
同一个 Agent 买同一个 Skill 产生多条记录
同一个 idempotency key 返回不同结果
```

排查：

```sql
select * from payments where agent_did = ? and skill_did = ?;
select * from idempotency_records where idempotency_key = ?;
```

要看：

```text
是否有唯一索引
idempotency_key 是否真的传到 Payment Service
Gateway 是否透传 X-Idempotency-Key
Payment Service 是否把请求参数 hash 存起来
重复 key + 不同参数时是否拒绝
```

正确处理：

```text
同 key + 同参数：
    返回已有 tx_id 和状态。

同 key + 不同参数：
    返回 idempotency key mismatch。

并发插入冲突：
    捕获唯一索引冲突，读取已有记录，而不是直接 500。
```

面试时可以说：

```text
幂等要靠接口协议、应用逻辑和数据库唯一索引共同保证，不能只靠前端不要重复点。
```

---

## 13.24 排障第四层：链上超时，到底算成功还是失败？

现象：

```text
Payment Service 调 Blockchain Adapter 超时
用户看到支付处理中
链上过一会儿又成功了
```

这种场景不能简单认为失败。

因为链上系统可能已经收到交易，只是响应超时。

处理方式：

```text
Payment 记录进入 PENDING
保存 tx_hash 或 request_id
后台轮询 GetTxStatus
确认成功后转 CONFIRMED / COMPLETED
确认失败后转 FAILED
超时一直查不到则进入补偿流程
```

排查：

```bash
kubectl -n zheda-agent logs deploy/stablepay-payment-service --tail=200
kubectl -n zheda-agent logs deploy/stablepay-blockchain-adapter --tail=200
```

查数据库：

```sql
select tx_id, status, tx_hash, created_at, updated_at
from payments
where tx_id = ?;
```

面试可以说：

```text
链上提交是典型的不确定外部副作用，不能用一次 RPC 的成功失败判断最终结果。
我会用支付状态机承接不确定性，用 PENDING + 交易状态补偿查询保证最终一致。
```

---

## 13.25 排障第五层：验证失败，明明支付了为什么商家说没买？

现象：

```text
Payment 已经 COMPLETED
但 VerifyPurchase 返回 purchased=false
Merchant 仍然返回 402
```

这时要区分：

```text
支付状态
购买关系
商户资源授权
```

排查：

```sql
select * from payments where agent_did=? and skill_did=?;
select * from purchase_records where agent_did=? and skill_did=?;
select * from verification_logs where agent_did=? and skill_did=? order by created_at desc;
```

可能原因：

```text
Payment 成功了，但 Verification Service 没写入 purchase_records。
agent_did 或 skill_did 不一致。
不同服务使用了不同 DID 格式。
Verification Service 查询的是 tx_hash，但商户传的是 agent_did + skill_did。
proof 生成失败。
```

处理：

```text
先确认 Payment 状态是否 COMPLETED。
再确认 purchase_records 是否存在。
再确认 VerifyPurchase 的入参是否和支付时一致。
最后确认商户侧传给 Gateway/Verification 的 agent_did 和 skill_did 是否正确。
```

面试可以说：

```text
支付成功和购买关系可验证是两个阶段。
Payment Service 负责支付生命周期，Verification Service 负责授权读模型。
如果验证失败，我会沿 tx_id、agent_did、skill_did、request_id 追查两边状态是否一致。
```

---

## 13.26 排障第六层：查询慢，Query Service 怎么优化？

现象：

```text
/api/v1/transactions 很慢
/api/v1/revenue 很慢
/api/v1/balance 偶发超时
```

先区分查询类型：

```text
查数据库历史记录
查聚合统计
查链上实时余额
查缓存
```

排查：

```sql
explain select ...
show indexes from payments;
```

服务侧看：

```bash
kubectl -n zheda-agent logs deploy/stablepay-query-service --tail=100
```

优化方向：

```text
分页必须有 page_size 上限
常用筛选字段加索引
收益统计可以做按日聚合表
余额查询可以加 Redis 缓存
链上查询设置超时
缓存 key 设计要包含 did + currency + network
```

面试可以说：

```text
Query Service 拆出来就是为了读优化。
我不会让 Payment Service 承担复杂统计和缓存逻辑。
查询慢时我会先看索引和分页，再看是否可以引入 Redis 缓存或预聚合读模型。
```

---

## 13.27 排障第七层：服务上线后 Pod 不 Ready

现象：

```text
kubectl get pods
stablepay-payment-service-xxx 0/1 Running
```

排查：

```bash
kubectl -n zheda-agent describe pod <pod>
kubectl -n zheda-agent logs <pod> --tail=100
```

常见原因：

```text
配置缺失
Secret key 不存在
数据库连不上
端口监听错
探针路径错
镜像拉取失败
启动命令错
```

如果是 Secret：

```bash
kubectl -n zheda-agent get secret stablepay-secrets -o yaml
```

如果是 Service 没 endpoints：

```bash
kubectl -n zheda-agent get endpoints stablepay-payment-service
```

记住：

```text
Pod Running 不等于 Ready。
Ready 之后才会进入 Service endpoints。
如果 endpoints 为空，上游服务就算访问 Service，也没有后端可转发。
```

---

## 13.28 排障第八层：一次线上问题应该怎么讲成 STAR

面试喜欢问：

> “讲一次你排查微服务问题的经历。”

可以用这个模板：

```text
S：背景
StablePay 有多个服务部署在 ACK，包括 Gateway、Payment、DID、Query、Verification、Blockchain Adapter。
我当时上线一个新服务或新路由，希望通过统一 Ingress 暴露。

T：目标
让服务能通过公网域名访问，同时不影响已有 MySQL、Redis、RocketMQ 和其他业务服务。

A：行动
我先按层级排查：
Deployment 是否存在；
Pod 是否 Ready；
Pod 日志是否正常；
Service 是否有 endpoints；
集群内部是否能 curl；
Ingress 规则是否存在；
公网请求是否命中正确服务。

过程中发现错误 apply 了 base infra，导致基础设施 Deployment 被更新，新旧 Pod 共存，新 Pod 卡在 ImagePullBackOff / ContainerCreating。
我没有删除 PVC，因为里面有生产数据，而是 rollout undo 回滚基础设施 Deployment。
然后重新梳理部署边界：ack/infra 管基础设施，ack/apps 管业务服务，ack/platform 管 Ingress。

R：结果
基础设施恢复，业务服务按 apps YAML 单独上线，Ingress 增加路径路由后公网访问恢复。
同时沉淀了排障 checklist，后续上线避免再次误 apply base infra。
```

这个故事的重点不是“我会 kubectl”，而是：

```text
我知道微服务部署要分层；
我知道先保护数据；
我知道从外到内或从内到外排查；
我知道 Deployment / Pod / Service / Ingress 的关系；
我能把事故沉淀成规范。
```

---

# 第四部分：面试拷打题集中整理

## Q1：你们为什么要拆成微服务？

```text
不是为了微服务而微服务，而是因为 StablePay 里存在几个稳定边界：
DID 是身份签名边界；
Payment 是支付状态机和幂等边界；
Blockchain Adapter 是链上执行边界；
Verification 是购买关系和 proof 边界；
Query 是读模型和缓存边界；
API Gateway 是统一接入和治理边界。

这些模块的安全要求、扩缩容方式、故障影响面和变化频率都不同，所以拆成 6 个服务更合理。
```

---

## Q2：微服务有什么缺点？

```text
微服务会引入分布式复杂度。
比如服务间调用会失败，事务不能靠一个本地数据库事务解决，排障链路变长，本地联调更麻烦，还需要服务发现、配置管理、日志、监控、链路追踪、熔断限流和 K8s 部署能力。

所以我不会说微服务一定比单体好。
StablePay 拆服务，是因为身份、支付、链上执行、验证、查询、网关这些职责差异足够明显。
```

---

## Q3：Gateway 是不是单点瓶颈？

```text
Gateway 是所有外部流量入口，确实是关键组件。
所以它本身应该无状态化，支持多副本部署，通过 K8s Deployment 扩容，通过 Service 和 Ingress/ALB 做负载均衡。
Gateway 不保存核心业务状态，只做鉴权、限流、路由、日志和错误归一化。
这样它可以水平扩容，也可以快速替换。
```

---

## Q4：服务之间用 HTTP 还是 RPC？

```text
对外接口用 HTTP/Hertz，因为 Agent、前端、curl、x402 都天然基于 HTTP、Header、JSON 和状态码。
内部服务之间更适合 Kitex RPC + IDL，因为内部调用需要强契约、生成 client/server、统一超时重试和服务治理。

但 MVP 阶段也可以先用 HTTP client，只要通过 Port/接口隔离，后续可以把 HTTP client 换成 Kitex client。
```

---

## Q5：服务发现怎么做？

```text
本地可以写 localhost:port。
上 K8s 后不能写 Pod IP，因为 Pod 会重建，IP 会变化。
K8s Service 提供稳定的 ClusterIP 和 DNS，比如 stablepay-payment-service。
调用方通过 Service 名称访问，不关心后端 Pod IP。
这就是服务发现。
```

---

## Q6：Payment Service 和 Blockchain Adapter 为什么分开？

```text
Payment Service 处理支付业务语义：
支付状态机、幂等、防重放、签名校验、支付历史、补偿。

Blockchain Adapter 处理链上执行语义：
Solana RPC、交易构造、签名、提交、确认轮询、Gas 补贴、余额查询、交易状态查询。

如果 Payment 直接写 Solana 细节，会导致业务流程和链上执行强耦合。
拆开后，未来支持多链或替换 Solana SDK，也主要影响 Blockchain Adapter。
```

---

## Q7：支付状态机为什么需要 CREATED / PENDING / CONFIRMED / COMPLETED？

```text
因为链上支付不是同步一步完成的。

CREATED 表示支付请求创建；
PENDING 表示链上交易处理中；
CONFIRMED 表示链上确认；
COMPLETED 表示业务完成；
FAILED 表示失败；
CANCELLED 表示取消。

如果只有 success/fail，无法表达“链上提交了但还没确认”或“请求超时但交易可能已经上链”的中间状态。
状态机可以防止非法跳转，也便于补偿任务恢复状态。
```

---

## Q8：重复支付怎么防？

```text
通过幂等键。
客户端传 X-Idempotency-Key。
服务端组合 agent_did + skill_did + idempotency_key 作为唯一键。
相同 key + 相同参数返回已有结果。
相同 key + 不同参数返回 mismatch 错误。
数据库层加唯一索引，防止并发请求绕过应用层判断。
```

---

## Q9：分布式事务怎么解决？

```text
不使用一个大事务包住所有服务和链上交易。
StablePay 更适合本地事务 + 状态机 + 幂等 + 补偿 + 最终一致性。

Payment Service 先落本地支付记录，再调用 Blockchain Adapter。
如果链上调用超时，支付进入 PENDING，不立刻判失败。
后续通过查询 tx_hash 或补偿任务把状态推进到 CONFIRMED / COMPLETED 或 FAILED。
```

---

## Q10：Verification Service 为什么单独拆？

```text
Payment Service 关注支付生命周期。
Verification Service 关注购买关系和授权验证。

商户后端或 Gateway 经常要问 agent_did 是否购买过 skill_did，这是高频读请求。
如果全部打到 Payment Service，会影响支付主流程。
所以把 purchase records、proof、verification logs 拆到 Verification Service，更适合高并发验证和审计。
```

---

## Q11：Query Service 为什么单独拆？

```text
Query Service 是读模型服务。
它处理余额、交易记录、收益统计、销售记录、分页、筛选、缓存和聚合。
Payment Service 是写流程核心，不适合承载复杂统计和缓存。
读写分开后，Query Service 可以独立优化索引、Redis 缓存和聚合表，也可以独立扩容。
```

---

## Q12：服务挂了怎么办？

```text
先看是哪一层挂了。
Gateway 挂了，外部请求进不来。
Payment 挂了，支付写流程不可用。
DID 挂了，签名验证不可用。
Blockchain Adapter 挂了，链上执行不可用，但已创建支付可以进入 PENDING 等待恢复。
Verification 挂了，购买验证受影响。
Query 挂了，查询和统计受影响。

K8s 层面用 livenessProbe 自动重启异常 Pod，用 readinessProbe 控制是否接流量，用 Deployment 保证副本数，用 Service 屏蔽 Pod IP 变化。
业务层面用超时、重试、熔断、降级和补偿处理下游异常。
```

---

# 第五部分：本章总结

微服务不是“把一个项目拆成很多仓库”这么简单。

真正的微服务设计要回答：

```text
为什么拆？
按什么边界拆？
服务之间怎么通信？
接口契约怎么维护？
调用失败怎么办？
重复请求怎么办？
状态不一致怎么办？
怎么部署？
怎么发现服务？
怎么排障？
怎么观察一条请求经过了哪些服务？
```

StablePay 的答案是：

```text
API Gateway：
    统一接入、鉴权、限流、路由、日志、错误码和 request_id / trace_id。

DID Service：
    身份、钱包、公钥、签名、防重放、DID 状态。

Payment Service：
    支付状态机、幂等、防重放、支付流程、链上协调。

Blockchain Adapter：
    Solana RPC、稳定币转账、余额查询、交易状态、Gas 补贴。

Verification Service：
    purchase records、proof、授权验证、审计日志。

Query Service：
    余额、交易历史、收益统计、读模型、Redis 缓存。
```

我以后再遇到“微服务”问题，不应该只背定义。

应该从 StablePay 这条链路出发：

```text
单体最简单
  ↓
职责开始混乱
  ↓
先拆 Gateway 做统一入口
  ↓
再拆 DID 做身份边界
  ↓
再拆 Payment 做支付状态机
  ↓
再拆 Blockchain Adapter 做链上执行
  ↓
再拆 Verification 做购买关系验证
  ↓
再拆 Query 做读模型和缓存
  ↓
服务间用 HTTP / RPC / IDL 通信
  ↓
K8s Service 做服务发现
  ↓
Ingress / ALB 做公网入口
  ↓
幂等、状态机、补偿、熔断、限流、trace_id 处理分布式复杂度
```

如果面试官问我有没有微服务经验，我不能只说“我了解微服务”。

我应该说：

```text
我在 StablePay 里实际参与过一个由 API Gateway、DID、Payment、Blockchain Adapter、Verification、Query 组成的微服务系统。
我理解每个服务为什么拆、边界在哪里、服务之间怎么通信、上 ACK 后如何通过 Deployment / Service / Ingress 部署和发现。
同时我也知道微服务带来的问题，比如幂等、补偿、服务调用失败、最终一致性和链路追踪，并在支付状态机、Gateway 中间件、K8s 排障中实际处理过这些问题。
```

这才是这个项目里“微服务经验”的真正含金量。



## 11.10 Service：Pod 会变，Service 名称不能变



Pod 的名字是会变的：



```text

stablepay-merchant-backend-6957bdbb8f-zkdxg

```



下一次滚动更新后，名字就会变。



所以不能让别的服务直接访问 Pod IP 或 Pod 名。



Kubernetes 用 Service 提供稳定入口：



```yaml

apiVersion: v1

kind: Service

metadata:

  name: stablepay-merchant-backend

  namespace: zheda-agent

spec:

  selector:

    app: stablepay-merchant-backend

  ports:

    - name: http

      port: 8787

      targetPort: 8787

```



这里的关键是 selector：



```yaml

selector:

  app: stablepay-merchant-backend

```



它会选中所有带这个 label 的 Pod：



```yaml

labels:

  app: stablepay-merchant-backend

```



如果 Service 访问不通，要查三件事：



```bash

kubectl -n zheda-agent get svc stablepay-merchant-backend

kubectl -n zheda-agent get endpoints stablepay-merchant-backend

kubectl -n zheda-agent get pods -l app=stablepay-merchant-backend

```



如果 endpoints 为空，通常说明：



```text

Service selector 没选中 Pod；

Pod 没 Ready；

Pod label 和 Service selector 不一致。

```



这就是 Service 的核心：



> Service 不是“启动服务”，而是给一组动态变化的 Pod 一个稳定的访问入口。



---



## 11.11 Ingress：公网进来的请求如何走到 merchant-backend



Pod 和 Service 都在集群内部。外网不能直接访问 ClusterIP Service。



所以需要 Ingress。



对于 StablePay，公网统一入口是：



```text

https://ai.wenfu.cn

```



然后不同路径进入不同后端：



```text

/                     → stablepay-frontend

/api                  → stablepay-api-gateway

/pay                  → stablepay-api-gateway

/verify               → stablepay-api-gateway

/merchant             → stablepay-merchant-backend

```



merchant 的目标路径是：



```text

https://ai.wenfu.cn/merchant/api/v1/products

```



这条请求的链路是：



```text

浏览器 / Agent

  ↓

DNS：ai.wenfu.cn

  ↓

ALB

  ↓

Ingress 规则：path /merchant

  ↓

Service：stablepay-merchant-backend:8787

  ↓

Pod：merchant-backend 容器 8787

  ↓

Hertz Router：/merchant/api/v1/products

```



这里有一个容易踩坑的地方：Ingress 是否要 rewrite？



有两种设计。



### 方案 A：Ingress 不 rewrite，应用自己支持 `/merchant` 前缀



请求路径保持原样：



```text

外部请求：/merchant/api/v1/products

转发到 Pod 后仍然是：/merchant/api/v1/products

```



这时 Hertz 必须注册：



```text

/merchant/healthz

/merchant/api/v1/products

```



这次 merchant-backend 就是这么处理的。



优点是简单，不依赖 ALB rewrite 特性。

缺点是应用需要知道自己挂在 `/merchant` 前缀下。



### 方案 B：Ingress rewrite，应用只支持 `/api/v1`



请求路径被网关改写：



```text

外部请求：/merchant/api/v1/products

转发到 Pod 后变成：/api/v1/products

```



这时应用只需要注册：



```text

/api/v1/products

```



优点是应用不知道外部前缀。

缺点是要正确配置 Ingress Controller 的 rewrite annotation，而且不同云厂商实现不完全一样。



这次选择方案 A，因为它更直接：



```text

Ingress 只负责把 /merchant 前缀转发到 merchant Service；

Hertz 同时注册 /api/v1 和 /merchant/api/v1；

避免在 ALB rewrite 上继续排坑。

```

