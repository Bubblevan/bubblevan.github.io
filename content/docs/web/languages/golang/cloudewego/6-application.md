# 6. Application 层
上一章我从一个最小愿望开始，把 Domain 层一点点“逼”了出来。

我先想问商品能不能买，于是有了 `Product.IsPurchasable()`。
后来发现价格不能用 float 算，于是有了 `Money`。
再后来发现 x402 PaymentRequired 描述的是“付多少钱拿什么资源”的业务合约，于是把 x402 v2 的核心结构放到了 Domain。
最后，当我准备写购买流程时，发现需要查询商品，于是有了 `ProductRepository` 接口。

到这里，Domain 层已经能表达一批核心规则：
- 商品能不能买；
- 商品价格怎么转成 USDC minor units；
- x402 v2 PaymentRequired 应该如何构造；
- 购买成功后如何生成商户侧 proof；
- 业务层需要通过 Repository 查询商品。
但是，Domain 层还不能直接完成“Agent 购买商品”这个完整动作。

因为购买商品不是一个孤立规则，而是一个流程。

这个流程大概是：
```text
Agent 请求执行商品
  ↓
根据 sku_id 查商品
  ↓
判断商品是否可购买
  ↓
验证 Agent 是否已经支付
  ↓
没支付：返回 x402 v2 PaymentRequired
  ↓
已支付：生成商户 proof，返回解锁内容
```
这就是 Application 层出现的原因。它的真实职责是：
> 把一个业务用例需要的多个对象、多个规则、多个外部能力串起来。
## 6.1 决策链路
## 6.1.1 从一个测试愿望开始：我想执行一个商品
```go
func TestExecutePurchase(t *testing.T) {
    // 我现在还不知道 ProductAppService 长什么样。
    // 但我希望最终能这样调用：
    result, err := app.ExecutePurchase(ctx, ExecutePurchaseCommand{
        SKUID:    "report-001",
        AgentDID: "did:solana:agent111",
    })

    if err != nil {
        t.Fatal(err)
    }

    if result.Purchased {
        t.Error("还没有付款时，不应该直接解锁内容")
    }

    if result.PaymentRequired == nil {
        t.Error("未付款时，应该返回 x402 v2 PaymentRequired")
    }
}
```
这段测试一开始肯定编译不过。但它逼出了几个东西：
```text
ProductAppService
ExecutePurchase 方法
ExecutePurchaseCommand
ExecutePurchaseResult
PaymentRequired 结果
```
这就是 Application 层的起点。
### 6.1.2 为什么不是直接在 Handler 里写这个流程？
最简单的写法当然是：
```go
func ExecuteProductHandler(ctx context.Context, c *app.RequestContext) {
    skuID := c.Param("id")
    agentDID := c.Query("agent_did")

    product, _ := repo.FindBySKUID(ctx, skuID)

    if !product.IsPurchasable() {
        c.JSON(400, ...)
        return
    }

    purchased := gateway.Verify(agentDID, product.SkillDid)

    if !purchased {
        requirement := domain.BuildPaymentRequiredV2(...)
        c.JSON(402, requirement)
        return
    }

    proof := domain.BuildProof(...)
    c.JSON(200, proof)
}
```
这能跑，但它把太多东西塞进 Handler 了。
Handler 里同时出现了：
- HTTP 参数读取；
- Repository 查询；
- Domain 校验；
- Gateway 验证；
- x402 构造；
- proof 生成；
- HTTP 状态码；
- JSON 响应。
这会让 Handler 很快变成“大杂烩”。
更好的拆法是：
```text
Handler：
  只负责 HTTP 参数和响应转换

Application Service：
  负责执行购买这个用例

Domain：
  负责商品规则、金额规则、x402 业务合约、proof 签名

Infrastructure：
  负责真正调用 StablePay Gateway
```

所以 Handler 不应该知道完整购买流程。

它只应该说`result, err := productAppService.ExecutePurchase(ctx, command)`然后根据 result 决定返回 HTTP 200 还是 402。

### 6.1.3 第一个 Application 对象：ProductAppService
Application 层的核心对象可以叫：
```go
type ProductAppService struct {}
```
它代表商品相关用例的入口。

现在它至少要支持三个用例：
```text
ListProducts：查询商品列表；
GetProductDetail：查询商品详情；
ExecutePurchase：执行购买/解锁流程。
```
为什么这三个方法放在 Application 层？

因为它们都是面向“用户动作”或“Agent 动作”的用例。
- `Product.IsPurchasable()` 是商品自己的规则。
- `Money.DecimalToMinorUnits()` 是金额自己的规则。
- `BuildPaymentRequiredV2()` 是 x402 合约构造规则。
但“Agent 请求执行一个商品时，先查商品，再验证支付，再决定返回 402 还是内容”不是单个实体自己的规则。

它是一个 **业务流程**，所以它属于 Application 层。
### 6.1.4 Application Service 需要依赖什么？
现在尝试写 `ExecutePurchase`：
```go
func (s *ProductAppService) ExecutePurchase(ctx context.Context, cmd ExecutePurchaseCommand) (*ExecutePurchaseResult, error) {
    product := ??? // 从哪里查？
    err := ???     // 谁判断商品能不能买？
    paid := ???    // 谁验证支付？
    proof := ???   // 谁生成 proof？
}
```
这个函数还写不下去。

它告诉我，Application Service 需要几类依赖：
```text
ProductRepository：
  查询商品

ProductDomainService：
  校验商品、构造 x402、生成 proof

PaymentVerifier：
  验证 Agent 是否已经付款

配置值：
  sellerAddress
  proofSecret
  facilitatorURL
  usdcMint
  solanaNetwork
  merchantPublicBaseURL
```
于是 `ProductAppService` 的字段长出来了：
```go
type ProductAppService struct {
    productRepo     repository.ProductRepository
    domainService   *domainSvc.ProductDomainService
    paymentVerifier appPort.PaymentVerifier

    merchantPublicBaseURL string
    sellerAddress         string
    proofSecret           string
    facilitatorURL        string
    usdcMint              string
    solanaNetwork         string
}
```
这些依赖不是凭空设计的，而是 `ExecutePurchase` 这个用例写不下去时被逼出来的。

这也说明 Application 层不是纯粹“调用 Domain”这么简单。它是一个编排者，所以它天然需要拿到多个能力。

### 6.1.5 为什么要引入 PaymentVerifier Port？
现在有个问题：Application 层需要验证支付。
最直接的写法是：
```go
import "github.com/stablepay/merchant-server/internal/infrastructure/client"

type ProductAppService struct {
    stablepayClient *client.StablePayClient
}
```
这样也能跑，但依赖方向有问题：
- Application 是业务用例层。
- Infrastructure 是技术实现层。
如果 Application 直接依赖 `StablePayClient`，那将来我把 HTTP Client 从 `net/http` 换成 Hertz Client，或者把 Gateway SDK 换掉，Application 层也会跟着动。

这不是我想要的！Application 层真正需要的不是“某个 StablePayClient 类”，而是一种能力：
> 给定 AgentDID、SkillDID 和可选 PaymentSignature，告诉我这个 Agent 是否已经购买。

于是我定义一个 Port：
```go
type PaymentVerifier interface {
    VerifyPurchase(ctx context.Context, req VerifyPurchaseRequest) (*VerifyPurchaseResult, error)
}
```
这就是 Application Port。

它表达的是 Use Case 需要的外部能力，而不是外部能力的实现方式。

请求模型是：
```go
type VerifyPurchaseRequest struct {
    AgentDID         string
    SkillDID         string
    PaymentSignature string
}
```
返回模型是：
```go
type VerifyPurchaseResult struct {
    Purchased bool
    TxID      string
    TxHash    string
    Proof     map[string]any
}
```
### 6.1.6 为什么 PaymentVerifier 不放 Domain 层？
这也是一个容易混的地方。

验证支付听起来像业务规则，为什么不放 Domain？

因为“是否已经支付”这个判断需要访问外部系统：
```text
StablePay Gateway；
链上交易记录；
proof 存储；
支付签名验证。
```
Domain 层应该保持纯粹，不应该直接依赖外部服务。

Domain 可以表达：
```text
什么样的 PaymentRequired 是合法的；
商品是否可购买；
proof 应该如何签名。
```
但“去 Gateway 查这个 Agent 是否已经买过”是一个外部能力。

这个能力应该通过 Application Port 表达，再由 Infrastructure 实现。

所以：
```text
PaymentRequired 合约属于 Domain；
PaymentVerifier Port 属于 Application；
StablePayClient 属于 Infrastructure。
```
### 6.1.7 ExecutePurchaseCommand：为什么需要 Command 对象？
一开始可以这样写：
```go
func ExecutePurchase(ctx context.Context, skuID, agentDID string) {}
```
但很快会发现参数会变多。

x402 v2 里，Agent 支付后重试请求时，可能会带`PAYMENT-SIGNATURE header`

后面还可能加：
```text
幂等键；
客户端版本；
请求来源；
trace id；
资源变体。
```
如果函数签名一直加参数，会变成：

```go
func ExecutePurchase(ctx context.Context, skuID, agentDID, paymentSignature, idempotencyKey, clientVersion string) {}
```
这就不优雅了。

所以更好的方式是引入 Command：
```go
type ExecutePurchaseCommand struct {
    SKUID            string
    AgentDID         string
    PaymentSignature string
}
```
Command 的意义是：
- 把一个用例的输入收成一个对象；
- 避免函数参数越来越长；
- 让 Handler 到 Application 的边界更清楚。

它不是 DTO：
- DTO 是 Adapter 层面对 HTTP 的对象。
- Command 是 Application 层面对 Use Case 的对象。

Handler 未来要做的是：
```text
HTTP query/header/path
  ↓
PurchaseExecuteReq DTO
  ↓
ExecutePurchaseCommand
  ↓
ProductAppService.ExecutePurchase
```

### 6.1.8 ExecutePurchaseResult：为什么不是直接返回 HTTP 402？
同样，Application 层也不应该直接返回 HTTP 402。

错误写法是`return consts.StatusPaymentRequired, paymentRequired`

这会让 Application 依赖 HTTP 协议。

但 Application 的输出应该是业务结果：
```go
type ExecutePurchaseResult struct {
    Purchased       bool
    Product         *ProductListItem
    PaymentRequired *domainSvc.X402PaymentRequired
    MerchantProof   *domainSvc.PurchaseProof
    GatewayProof    map[string]any
    TxID            string
    TxHash          string
    Content         map[string]any
}
```
它表达的是：
```text
这个商品是否已经购买；
如果没买，需要什么付款要求；
如果买了，商户给什么 proof；
Gateway 返回了什么交易信息；
最终解锁什么内容。
```
至于怎么转 HTTP：
```text
Purchased == false：
  Adapter 返回 HTTP 402
  Header 写 PAYMENT-REQUIRED
  Body 返回错误提示

Purchased == true：
  Adapter 返回 HTTP 200
  Body 返回内容和 proof
```
这是 Adapter 的职责，不是 Application 的职责。

所以 Application 层不 import Hertz，也不写 `c.JSON()`。
### 6.1.9 ExecutePurchase 的完整决策链
现在终于可以写 `ExecutePurchase` 了。

它的逻辑不是“业务规则”，而是“流程编排”。

第一步，校验命令：
```go
if cmd.SKUID == "" {
    return nil, fmt.Errorf("execute purchase: sku_id is required")
}
if cmd.AgentDID == "" {
    return nil, fmt.Errorf("execute purchase: agent_did is required")
}
```
这属于用例输入校验。

第二步，查商品：
```go
product, err := s.productRepo.FindBySKUID(ctx, cmd.SKUID)
```
这里 Application 依赖的是 Repository 接口，不关心商品存在内存、SQLite 还是 MySQL。

第三步，问 Domain 能不能买：
```go
if err := s.domainService.CanPurchase(product); err != nil {
    return nil, fmt.Errorf("execute purchase: %w", err)
}
```
Application 不重复写：
```go
if product.Status != active || product.Price == "" ...
```
因为那是 Domain 规则。

第四步，问 PaymentVerifier 是否已支付：
```go
verification, err := s.paymentVerifier.VerifyPurchase(ctx, appPort.VerifyPurchaseRequest{
    AgentDID:         cmd.AgentDID,
    SkillDID:         product.SkillDid,
    PaymentSignature: cmd.PaymentSignature,
})
```
这里 Application 不知道 Gateway 怎么实现，也不自己构造 HTTP 请求。

第五步，如果没买，构造 x402 v2 PaymentRequired：
```go
paymentRequired, err := s.domainService.BuildPaymentRequiredV2(...)
```
注意，构造规则在 Domain，但“什么时候需要构造”由 Application 决定。

第六步，如果买了，生成商户 proof：
```go
proof, err := s.domainService.BuildSignedProof(cmd.AgentDID, product.SKUID, s.proofSecret)
```
最后返回结果：
```go
return &ExecutePurchaseResult{
    Purchased:     true,
    Product:       productToListItem(product),
    MerchantProof: proof,
    TxID:          verification.TxID,
    TxHash:        verification.TxHash,
    Content:       buildUnlockedContent(product, proof, verification),
}, nil
```
这就是 Application Service 的核心价值：把多个对象和外部能力组合成一个业务用例。

### 6.1.10 为什么 Application 可以知道 x402，但不能知道 HTTP Header？
这个点要分清楚。

Application 知道 x402 PaymentRequired，是合理的。
因为它需要决定“未支付时返回付款要求”。

但 Application 不应该知道：
```text
HTTP status code = 402；
Header 名叫 PAYMENT-REQUIRED；
Header value 要 Base64；
Hertz 的 c.Header 怎么写。
```
也就是说：
```text
Application 可以返回 X402PaymentRequired 对象；
Adapter 负责把它翻译成 HTTP 402 + PAYMENT-REQUIRED Header。
```
这一点和上一章 Domain 的边界连起来：
```text
Domain：
  定义 x402 v2 PaymentRequired 业务合约

Application：
  决定当前 Use Case 是否需要 PaymentRequired

Adapter：
  决定 PaymentRequired 如何通过 HTTP 表达
```
如果未来不是 HTTP，而是 MCP Tool 或 gRPC，Domain 和 Application 大概率还可以复用。只需要换 Adapter。这就是分层的价值。

### 6.1.11 为什么 StablePayClient 现在只是 stub 也有价值？
当前 `StablePayClient.VerifyPurchase` 还没有真正发 HTTP 请求，而是返回：
```go
return &appPort.VerifyPurchaseResult{
    Purchased: false,
}, nil
```
这看起来像没实现。

但它仍然有价值，因为现在已经确定了边界：
```text
Application 只依赖 PaymentVerifier；
Infrastructure 的 StablePayClient 实现 PaymentVerifier；
真实 HTTP 调用以后补在 Infrastructure；
ExecutePurchase 的主流程不用再改。
```
这和之前“TODO 乱放”不一样。
- 之前的 TODO 是业务规则没写完，比如金额转换和 proof 签名。
- 现在的 TODO 是外部技术实现还没接，但架构边界已经确定。

这两种 TODO 的风险完全不同。

当前阶段先让它返回未购买，可以推动 x402 402 流程先跑起来。
下一阶段接 Gateway 时，只需要把 `StablePayClient.VerifyPurchase` 从 stub 改成真实请求。
### 6.1.12 Application 层测试应该测什么？
Application 层测试不应该重复测试 Money 怎么转换，也不应该测试 Product 状态枚举。

那些是 Domain 测试。

Application 测试应该测流程。

比如：未付款时返回 x402 v2 PaymentRequired。
```go
func TestExecutePurchaseWithoutPaymentReturnsX402V2Requirement(t *testing.T) {
    app := newTestApp(fakePaymentVerifier{})

    result, err := app.ExecutePurchase(context.Background(), ExecutePurchaseCommand{
        SKUID:    "report-001",
        AgentDID: "did:solana:agent111",
    })

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if result.Purchased {
        t.Fatal("expected unpaid result")
    }

    if result.PaymentRequired == nil {
        t.Fatal("expected payment requirement")
    }

    if result.PaymentRequired.X402Version != domainSvc.X402VersionV2 {
        t.Fatal("expected x402 v2")
    }

    if result.PaymentRequired.Accepts[0].Amount != "2000000" {
        t.Fatal("expected 2.00 USDC to become 2000000")
    }
}
```
这个测试不是在细测 `DecimalToMinorUnits`。
它是在测试整个 Use Case 的结果：当商品价格是 2.00 USDC 且未付款时，Application 应该返回 x402 v2 付款要求。

再测：已付款时返回内容和 proof。
```go
func TestExecutePurchaseWhenPaidReturnsContentAndProof(t *testing.T) {
    app := newTestApp(fakePaymentVerifier{
        result: &appPort.VerifyPurchaseResult{
            Purchased: true,
            TxID:      "tx-001",
            TxHash:    "hash-001",
        },
    })

    result, err := app.ExecutePurchase(context.Background(), ExecutePurchaseCommand{
        SKUID:            "report-001",
        AgentDID:         "did:solana:agent111",
        PaymentSignature: "signed-payment-payload",
    })

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if !result.Purchased {
        t.Fatal("expected purchased result")
    }

    if result.PaymentRequired != nil {
        t.Fatal("did not expect payment requirement after purchase")
    }

    if result.MerchantProof == nil || result.MerchantProof.Signature == "" {
        t.Fatal("expected signed merchant proof")
    }
}
```
这就是 Application 测试的重点：

```text
fake repository 提供商品；
fake verifier 控制支付状态；
ProductAppService 编排流程；
测试最终结果是否符合 Use Case 预期。
```

- 不需要真的启动 HTTP 服务。
- 不需要真的连 SQLite。
- 不需要真的访问 StablePay Gateway。
这就是分层以后测试变轻的好处。

### 6.1.13 Application 层和 Domain 层的区别
到这里，我可以比较清楚地区分两者。
| 层级 | 内容 |
| ---- | ---- |
| Domain 层 | 商品是否可购买？<br>价格如何转换？<br>x402 PaymentRequired 合约如何构造？<br>proof 如何签名？ |
| Application 层 | Agent 请求执行商品时，先做什么、后做什么？<br>什么时候查商品？<br>什么时候验证支付？<br>什么时候返回 PaymentRequired？<br>什么时候生成 proof？<br>最终给 Adapter 什么结果？ |

一句话：
- Domain 负责规则；
  - 如果把流程塞进 Domain，Domain 会开始依赖 Gateway、配置、Repository、HTTP 场景。
- Application 负责流程。
  - 如果把规则塞进 Application，Application 会变成又长又难测的业务大杂烩。

### 6.1.14 当前 Application 层最终长成什么样？
本章之后，Application 相关文件变成：
```text
internal/application/
├── port/
│   └── payment_verifier.go
└── service/
    ├── product_app_service.go
    └── product_app_service_test.go
```
它们的职责是：
```text
payment_verifier.go：
  定义 PaymentVerifier 端口，让 Application 不依赖具体 Gateway Client

product_app_service.go：
  实现 ListProducts、GetProductDetail、ExecutePurchase 三个 Use Case

product_app_service_test.go：
  用 fake repo 和 fake verifier 测试用例编排
```
同时，Infrastructure 里：
```text
internal/infrastructure/client/stablepay_client.go
```
开始实现 `PaymentVerifier` 端口。
main.go 也开始真正把 `stablepayClient` 注入到 `ProductAppService`，不再只是创建后 `_ = stablepayClient`。

### 6.1.15 最重要的决策链
这一章的代码不是从“我需要一个 Application Service”开始的，而是被购买流程逼出来的：

```text
我想让 Agent 执行商品
  ↓
需要 ExecutePurchase 这个 Use Case

ExecutePurchase 参数开始变多
  ↓
需要 ExecutePurchaseCommand

ExecutePurchase 结果不只是成功/失败
  ↓
需要 ExecutePurchaseResult

Use Case 要查商品
  ↓
需要 ProductRepository

Use Case 要判断商品是否可购买
  ↓
调用 ProductDomainService，而不是重复写规则

Use Case 要验证支付
  ↓
需要 PaymentVerifier Port

不想让 Application 依赖 StablePay HTTP Client
  ↓
PaymentVerifier 接口放在 Application，StablePayClient 放在 Infrastructure 实现

未付款时要返回 x402 v2 要求
  ↓
Application 调用 Domain 的 BuildPaymentRequiredV2

已付款时要返回内容和 proof
  ↓
Application 调用 Domain 的 BuildSignedProof

x402 结果最终要变成 HTTP 402
  ↓
留给下一章 Adapter 层处理
```

这就是 Application 层的学习方法：

> 不要先写 Service。先写一个完整用例，让流程告诉我需要哪些输入、输出、端口和依赖。

## 6.2 面试讲法
我的 Application 层不是写业务规则的地方，而是 Use Case 编排层。
比如 ExecutePurchase 这个用例，它会根据 sku_id 查商品，调用 Domain 判断商品是否可购买，
再通过 PaymentVerifier Port 验证 Agent 是否已经付款。
如果未付款，它返回 Domain 构造的 x402 v2 PaymentRequired；
如果已付款，它生成商户侧 proof 并返回解锁内容。

如果面试官问为什么引入 Port，可以回答：

```text
因为验证支付是外部能力。
Application 层只需要知道“我能验证支付”，不应该依赖具体 StablePay HTTP Client。
所以我在 Application 层定义 PaymentVerifier 接口，
由 Infrastructure 的 StablePayClient 去实现。
这样未来 Gateway API、HTTP 客户端或 SDK 改了，Use Case 不需要跟着改。
```

如果面试官问为什么 Application 不直接返回 HTTP 402，可以回答：

```text
HTTP 402 和 PAYMENT-REQUIRED Header 是 Adapter 层的传输表达。
Application 层只返回业务结果：是否已购买、是否需要 PaymentRequired、购买后 proof 是什么。
这样未来如果不是 HTTP，而是 MCP Tool 或 gRPC，Application 和 Domain 仍然可以复用。
```

本章结束后，项目的核心购买流程已经在 Application 层成型。下一章自然应该进入 Adapter 层：把 `ExecutePurchaseResult` 翻译成真正的 HTTP 200 或 HTTP 402，并按 x402 v2 写入 `PAYMENT-REQUIRED` Header。
