# 14. KiTex 与 IDL
前面 Merchant Server 的章节里，我一直依赖 vibe 在写 HTTP：
```
Agent
  ↓ HTTP
Merchant Server
  ↓ HTTP / Gateway
StablePay Gateway
```
这是对外入口很自然的形态。Agent、浏览器、curl、OpenClaw 插件，都更容易通过 HTTP 访问。

但当我们决定将后端变为 6 大微服务之后，如果也全部互相 curl，当然可以跑，但很快会出现一堆问题：
- 请求和响应结构靠文档约定，容易写错字段名；
- 每个服务都要手写 HTTP client；
- 超时、重试、熔断、服务发现很分散；
- 接口改动后调用方不一定能及时发现；
- 没有统一的内部服务契约；
- 服务之间的调用不像“调用方法”，而像“拼 URL”。

于是就出现了 Kitex 和 IDL。
## 14.1 IDL
假如说，现在 Merchant Server 或 API Gateway 想问 Verification Service 一个问题：`这个 agent_did 是否购买过这个 skill_did？`

merchant Server 当然要写 HTTP：
```bash
curl -X POST http://verification-service/internal/verify \
  -d '{"agent_did":"did:solana:agent111","skill_did":"did:solana:skill222"}'
```
但在内部微服务里，我更希望像调用一个本地方法一样：
```go
resp, err := verificationClient.VerifyPurchase(ctx, &VerifyPurchaseRequest{
    AgentDid: "did:solana:agent111",
    SkillDid: "did:solana:skill222",
})
```
这个愿望逼出了几个问题：
- VerifyPurchaseRequest 长什么样？
- VerifyPurchaseResponse 长什么样？
- VerificationService 有哪些方法？
- 客户端怎么调用？
- 服务端怎么实现？
- 请求和响应怎么序列化？

这就是 IDL 出现的时机。它不是“又一种配置文件”，而是服务间调用的契约。
### 14.1.1 第一个 IDL
最小 IDL 可以这样写：
```thrift
namespace go stablepay.verification_service

struct VerifyPurchaseRequest {
  1: string agent_did,
  2: string skill_did,
}

struct VerifyPurchaseResponse {
  1: bool purchased,
  2: optional string tx_id,
}

service VerificationService {
  VerifyPurchaseResponse VerifyPurchase(1: VerifyPurchaseRequest req),
}
```
注意字段前面的 `1`、`2` 不是装饰品。

这个数字是字段编号，是 Thrift 序列化时识别字段的重要依据。后续做兼容演进时，不能随便改旧字段编号。

这和 JSON 只看字段名不太一样，IDL 的字段编号就是契约的一部分。

这一小段东西已经定义清楚了四件事：
- Go 包名空间：stablepay.verification_service
- 请求结构：VerifyPurchaseRequest
- 响应结构：VerifyPurchaseResponse
- 服务方法：VerifyPurchase
### 14.1.2 统一请求格式
写完第一个 IDL 后，很快会发现每个内部 RPC 都需要类似东西：
```text
request_id
trace_id
timestamp_ms
idempotency_key
code
message
```
如果每个服务都复制一遍，就会乱。

于是出现 `common.thrift`。

我们（实际上是企业给的）的实现主要包括通用错误码，例如 `SUCCESS`、`INVALID_PARAMETERS`、`RESOURCE_NOT_FOUND`、`SIGNATURE_VERIFICATION_FAILED`、`INSUFFICIENT_BALANCE`、`SERVICE_UNAVAILABLE` 等；还定义了 `Currency`、`PaymentStatus`、`DID`、`TxId`、`TxHash`、`BaseReq` 和 `BaseResp`。

概念上，对应的 IDL 大概是：
```thrift
namespace go stablepay.common

typedef string DID
typedef string TxId
typedef string TxHash

enum ErrorCode {
  SUCCESS = 0,
  INVALID_PARAMETERS = 10001,
  RESOURCE_NOT_FOUND = 10002,
  SIGNATURE_VERIFICATION_FAILED = 10004,
  INTERNAL_SERVER_ERROR = 30001,
}

enum Currency {
  USDC = 1,
  USDT = 2,
}

struct BaseReq {
  1: optional string request_id,
  2: optional string trace_id,
  3: optional i64 timestamp_ms,
  4: optional string idempotency_key,
}

struct BaseResp {
  1: i32 code,
  2: string message,
  3: optional string request_id,
  4: optional string trace_id,
}
```
有了 `common.thrift`，每个服务的 IDL 就可以：
```thrift
include "common.thrift"
```
然后使用：
```thrift
1: common.BaseReq base
2: common.DID agent_did
```
从而使得 StablePay 的服务间调用必须统一：
- 错误码
- 币种
- 支付状态
- DID
- tx_id / tx_hash
- request_id / trace_id
- 幂等键
### 14.1.3 某微服务实例
回到 Verification Service：
```thrift
/**
 * verification-service 内部 RPC 契约（一期）
 *
 * 说明：
 * - 本服务主要通过消费支付事件写入购买关系；同时对外提供 verify/proof 等查询能力。
 */
namespace go stablepay.verification_service

include "common.thrift"

struct VerifyPurchaseRequest {
  1: common.BaseReq base,
  2: common.DID agent_did,
  3: common.DID skill_did,
}

struct VerifyPurchaseResponse {
  1: common.BaseResp base,
  2: bool purchased,
  3: optional string purchase_time,
  4: optional common.TxId tx_id,
  5: optional i64 amount_minor,
  6: optional common.Currency currency,
}

struct BatchVerifyItem {
  1: common.DID skill_did,
  2: bool purchased,
  3: optional string purchase_time,
  4: optional common.TxId tx_id,
}

struct BatchVerifyPurchaseRequest {
  1: common.BaseReq base,
  2: common.DID agent_did,
  3: list<common.DID> skill_dids,
}

struct BatchVerifyPurchaseResponse {
  1: common.BaseResp base,
  2: list<BatchVerifyItem> items,
}

struct GetPurchaseProofRequest {
  1: common.BaseReq base,
  2: common.DID agent_did,
  3: common.DID skill_did,
}

struct GetPurchaseProofResponse {
  1: common.BaseResp base,
  2: bool purchased,
  3: optional string purchase_time,
  4: optional common.TxId tx_id,
  5: optional i64 amount_minor,
  6: optional common.Currency currency,
  7: optional common.TxHash tx_hash,
  /** 建议字段：proof 版本 */
  8: optional string proof_version,
}

service VerificationService {
  VerifyPurchaseResponse VerifyPurchase(1: VerifyPurchaseRequest req),
  BatchVerifyPurchaseResponse BatchVerifyPurchase(1: BatchVerifyPurchaseRequest req),
  GetPurchaseProofResponse GetPurchaseProof(1: GetPurchaseProofRequest req),
}
```
## 14.2 Kitex
写完 IDL 之后，不需要自己手写所有请求结构体、序列化、客户端、服务端骨架。

Kitex 代码生成工具会帮我们生成两大类代码：一类是底层 IDL 编译器生成的结构体编解码代码，另一类是 Kitex 在此基础上生成的 RPC 调用桩代码；这些代码默认生成在 `kitex_gen` 目录下。
```bash
kitex -module <your-module> -service payment-service -thrift <path-to>/stablepayai-idl/idl/payment-service.thrift
```

如果要生成 **服务端脚手架，**则类似：
```bash
kitex \
  -module verification-service \
  -service verification-service \
  -use verification-service/kitex_gen \
  idl/verification-service.thrift
```

这里几个参数要理解：
```
-module：
    生成代码所属的 Go module 名称。
-service：
    生成服务端脚手架，告诉 Kitex 这是一个要启动的服务。
-use：
    复用已有 kitex_gen，而不是重复生成一份。
```

生成以后会看到类似：
```
kitex_gen/
  stablepay/
    common/
    verification_service/
      verification-service.go
      verificationservice/
        client.go
        server.go
        verificationservice.go
```
`verification-service.go` 是 thriftgo 生成的请求/响应结构体和服务接口；`client.go` 是 Kitex 生成的客户端代码，里面有 `NewClient` 和各个 RPC 方法。 
### 14.2.1 Handler
IDL 生成以后，真正要手写的是业务 handler。
生成代码里会有一个接口：
```go
type VerificationService interface {
    VerifyPurchase(ctx context.Context, req *VerifyPurchaseRequest) (*VerifyPurchaseResponse, error)
    BatchVerifyPurchase(ctx context.Context, req *BatchVerifyPurchaseRequest) (*BatchVerifyPurchaseResponse, error)
    GetPurchaseProof(ctx context.Context, req *GetPurchaseProofRequest) (*GetPurchaseProofResponse, error)
}
```

手写服务端时，核心就是实现这个接口：
```go
type VerificationServiceImpl struct{}

func (s *VerificationServiceImpl) VerifyPurchase(
    ctx context.Context,
    req *verification_service.VerifyPurchaseRequest,
) (*verification_service.VerifyPurchaseResponse, error) {
    // 1. 校验 req.AgentDid / req.SkillDid
    // 2. 查 purchase_records
    // 3. 组装 VerifyPurchaseResponse
}
```
然后启动 Kitex Server：
```go
svr := verificationservice.NewServer(new(VerificationServiceImpl))
err := svr.Run()
```

这一步的关键是：业务开发者不需要知道请求如何二进制序列化，也不需要手写 socket 处理。Kitex 生成的 server skeleton 会把网络请求转成方法调用。

### 14.2.2 RPC
调用方不需要自己拼 HTTP URL，生成的客户端已经提供：
```go
c, err := verificationservice.NewClient(
    "verification-service",
    client.WithHostPorts("127.0.0.1:8888"),
)
```
然后直接调用：
```go
resp, err := c.VerifyPurchase(ctx, &verification_service.VerifyPurchaseRequest{
    AgentDid: "did:solana:agent111",
    SkillDid: "did:solana:skill222",
})
```
`client.go` 里，`NewClient` 会根据 IDL 创建服务客户端，客户端接口提供 `VerifyPurchase`、`BatchVerifyPurchase`、`GetPurchaseProof`、`VerifyXTweet`、`GetXVerificationStatus` 等方法。

### 14.2.3 MVP
一个比较自然的结构是：
```
verification-service/
├── idl/
│   ├── common.thrift
│   └── verification-service.thrift
├── kitex_gen/
│   └── stablepay/
│       ├── common/
│       └── verification_service/
├── cmd/
│   └── server/
│       └── main.go
├── internal/
│   ├── handler/
│   │   └── verification_handler.go
│   ├── application/
│   ├── domain/
│   └── infrastructure/
└── go.mod
```
- idl/：人维护的契约源头（我们单独开了一个云效仓库）。

- kitex_gen/：机器生成代码，不手改。

- cmd/server：启动入口。

- internal/handler：实现生成出来的 VerificationService 接口。

- internal/application/domain/infrastructure：继续按 COLA 思路放业务编排、领域规则和数据库实现。

## 14.3 基础知识
### 14.3.1 Kitex 是什么
Kitex 是 CloudWeGo 生态里的 Go RPC 框架。它面向服务间调用，强调高性能和扩展性，支持 Thrift、Kitex Protobuf、gRPC 等消息协议，也提供服务发现、负载均衡、熔断、限流、重试、监控、链路追踪等服务治理扩展。
```mermaid
flowchart TD
    subgraph IDL [接口定义语言]
        Protobuf
        ThriftIDL[Thrift IDL]
    end

    subgraph RPC_Frameworks [RPC框架]
        gRPC
        Thrift
        Kitex
        tRPC
    end

    subgraph Language_Imple [具体语言实现]
        gRPC_Go[gRPC-Go]
        Thrift_Go[ThriftGo]
        Kitex_Go[Kitex (Kitex-Go)]
        tRPC_Go[tRPC-Go]
    end

    Protobuf -- 默认使用 --> gRPC
    Protobuf -- 可选使用 --> Kitex
    Protobuf -- 可选使用 --> tRPC
    ThriftIDL -- 原生支持 --> Thrift
    ThriftIDL -- 可选使用 --> Kitex

    gRPC --> gRPC_Go
    Thrift --> Thrift_Go
    Kitex -- 其Go实现 --> Kitex_Go
    tRPC -- 其Go实现 --> tRPC_Go

    Kitex -.->|"支持gRPC协议\n可互通"| gRPC
    tRPC -.->|"支持gRPC协议\n可互通"| gRPC
```

### 14.3.2 IDL 是什么
IDL 是 Interface Definition Language，接口定义语言。
| 分类 | 包含内容 | 具体项说明 |
| ---- | ---- | ---- |
| 要描述 | 接口基础与数据定义 | 1. 服务名<br>2. 方法名<br>3. 请求结构<br>4. 响应结构<br>5. 字段类型<br>6. 字段编号<br>7. 字段是否可选(optional)<br>8. 公共数据类型<br>9. 枚举定义 |
| 不描述 | 业务落地与工程实现 | 1. 数据库查询语句<br>2. 业务逻辑代码<br>3. 日志打印规则<br>4. 服务部署流程<br>5. 具体 Handler 实现代码 |

比如我们 StablePay 里的 IDL 负责告诉所有服务：
- VerifyPurchaseRequest 一定有 agent_did 和 skill_did；
- InitiatePaymentRequest 一定有 amount_minor 和 currency；
- BaseReq 里有 request_id / trace_id / idempotency_key；
- BaseResp 里有 code / message。

### 14.3.3 RPC
| 层次 | 技术 |
| :--- | :--- |
| **RPC框架** | gRPC, Thrift, Kitex, tRPC |
| **IDL (接口定义语言)** | Protocol Buffers (protobuf), Thrift IDL |
| **通信协议/传输层** | HTTP/2, TCP, 自定义协议 |

Kitex 和 IDL 的关系也可以这样理解：
- IDL：写契约。
- thriftgo / protoc：根据契约生成结构体和序列化代码。
- kitex：在结构体基础上生成 RPC client/server 桩代码。
- 业务开发者：实现 handler，调用 client。

所以完整链路是：
```
verification-service.thrift
  ↓
kitex 命令
  ↓
kitex_gen/stablepay/verification_service/*.go
  ↓
VerificationServiceImpl 实现接口
  ↓
Kitex Server 启动
  ↓
其他服务通过 Kitex Client 调用
```
有了 IDL 后可以用 kitex 工具生成项目代码；生成结果分为 IDL 编译器生成的结构体编解码代码，以及 Kitex 叠加生成的 RPC 调用桩代码。
### 14.3.4 KiTex vs Hertz
| 对比项  | Hertz                         | Kitex                                            |
| ---- | ----------------------------- | ------------------------------------------------ |
| 定位   | HTTP Web 框架                   | RPC 微服务框架                                        |
| 典型入口 | 外部用户、Agent、浏览器、curl           | 内部服务之间                                           |
| 契约方式 | OpenAPI / 文档 / DTO            | IDL                                              |
| 调用方式 | 拼 URL，请求 HTTP                 | 像调用方法一样调 client                                  |
| 编解码  | JSON 常见                       | Thrift / Protobuf / gRPC                         |
| 适合场景 | API Gateway、Merchant HTTP API | DID、Payment、Verification、Blockchain Adapter 内部调用 |
| 关注点  | 路由、中间件、HTTP 状态码               | 服务发现、超时、重试、负载均衡、RPC 编解码                          |

- Hertz 更适合对外 HTTP 接入层，因为外部调用方天然理解 URL、Header、JSON 和状态码。
- Kitex 更适合内部微服务调用，因为内部服务更需要强契约、生成客户端、超时重试和服务治理。

## 14.4 面试讲法
StablePay 内部微服务之间使用 Kitex RPC 和 Thrift IDL 定义服务契约。
IDL 里定义每个服务的请求、响应、错误码、公共 BaseReq/BaseResp 和服务方法。
Kitex 根据 IDL 生成结构体、序列化代码、client stub 和 server skeleton。
业务侧只需要实现生成接口，比如 VerificationServiceImpl 实现 VerifyPurchase；
调用方则通过生成的 client 像调用本地方法一样调用内部服务。

如果面试官问为什么不用 HTTP，可以回答：
```
HTTP 适合作为外部 API，因为它通用、易调试、适合 Agent 和前端。
但内部服务之间更需要强契约和服务治理。
Kitex + IDL 可以在编译期暴露字段和方法不匹配问题，也能统一超时、重试、服务发现和链路追踪扩展。
```

如果面试官问 IDL 怎么演进，可以回答：
```
IDL 是跨服务契约，不能像普通 Go struct 一样随便改。
字段编号不能改，删除字段不能复用编号，新增字段尽量 optional。
如果要改请求或响应，应该先改 thrift 文件，再重新生成 kitex_gen，最后调整 handler 和调用方。
生成代码不能手改，因为下一次生成会覆盖。
```

如果面试官问 BaseReq / BaseResp 有什么用，可以回答：
```
BaseReq / BaseResp 是内部服务治理的基础。
BaseReq 透传 request_id、trace_id、timestamp_ms、idempotency_key；
BaseResp 统一 code、message、request_id、trace_id。
这样 API Gateway、Payment、Verification、Query 等服务之间可以统一日志、错误码、幂等和链路追踪。
```