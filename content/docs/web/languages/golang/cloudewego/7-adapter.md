# 7. Adapter 层
上一章 Application 层已经完成了一个重要转变：我不再让 Handler 直接处理购买流程，而是让 `ProductAppService.ExecutePurchase` 返回一个业务结果。

这个结果大概长这样：
```go
type ExecutePurchaseResult struct {
    Purchased       bool
    Product         *ProductListItem
    PaymentRequired *X402PaymentRequired
    MerchantProof   *PurchaseProof
    GatewayProof    map[string]any
    TxID            string
    TxHash          string
    Content         map[string]any
}
```
它已经回答了业务层的问题：

```text
这个 Agent 有没有买过？
没买的话，需要什么 x402 PaymentRequired？
买了的话，返回什么内容？
商户侧 proof 是什么？
Gateway proof 是什么？
```

但是它还没有回答 HTTP 层的问题：

```text
哪个 URL 调哪个 Use Case？
商品 ID 从 path 里取还是 query 里取？
Agent DID 从哪里取？
PAYMENT-SIGNATURE 从哪个 header 读？
未支付时 HTTP 状态码是多少？
PAYMENT-REQUIRED header 怎么写？
成功时 body 长什么样？
错误时 body 长什么样？
```

这些问题都不应该污染 Domain，也不应该塞进 Application。

这就是 Adapter 层出现的地方。

---

## 8.1 从一个最小愿望开始：我想让 Agent 调接口看到商品列表

先不要急着写 ProductHandler。

先写一个请求愿望：

```bash
curl http://127.0.0.1:8787/api/v1/products
```

我希望它返回：

```json
{
  "ok": true,
  "message": "products listed",
  "products": [
    {
      "id": "ai-agent-job-2025",
      "sku_id": "ai-agent-job-2025",
      "title": "AI Agent 岗位分析报告 2025",
      "price": "2.00",
      "currency": "USDC",
      "status": "active"
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "size": 20
  }
}
```

这个愿望立刻逼出几个东西：

```text
路由：GET /api/v1/products
Handler：ListProducts
请求 DTO：ProductListReq
响应 DTO：ProductListResp
ProductAppService.ListProducts 调用
Application read model 到 HTTP DTO 的转换
```

所以 Adapter 层不是“随便写几个接口”，而是从“外部调用者希望怎么访问系统”开始长出来的。

---

## 8.2 为什么不能直接把 Application 的 ProductListItem 返回出去？

Application 层已经有：

```go
type ProductListItem struct {
    ID          string
    SKUID       string
    Title       string
    Description string
    Price       string
    Currency    string
    Author      string
    Tags        []string
    Status      string
}
```

看起来和 HTTP 返回结果很像。

那 Handler 能不能直接：

```go
c.JSON(200, items)
```

能，但不推荐。

因为 Application read model 和 HTTP API contract 不是同一个东西。

Application 的 `ProductListItem` 是用例输出。
Adapter 的 `ProductItem` 是对外接口合同。

它们现在很像，是因为项目还小。以后很可能分化：

```text
Application 可能需要内部字段；
HTTP API 可能需要隐藏字段；
OpenClaw 插件可能希望字段名更稳定；
前端页面可能希望增加展示字段；
不同版本 API 可能返回不同 DTO。
```

所以我在 Adapter 层保留：

```go
type ProductItem struct {
    ID          string   `json:"id"`
    SKUID       string   `json:"sku_id"`
    Title       string   `json:"title"`
    Description string   `json:"description"`
    Price       string   `json:"price"`
    Currency    string   `json:"currency"`
    Author      string   `json:"author,omitempty"`
    Tags        []string `json:"tags,omitempty"`
    Status      string   `json:"status"`
}
```

然后在 Handler 里做转换：

```go
func mapProductItem(item *appSvc.ProductListItem) dto.ProductItem {
    return dto.ProductItem{
        ID:          item.ID,
        SKUID:       item.SKUID,
        Title:       item.Title,
        Description: item.Description,
        Price:       item.Price,
        Currency:    item.Currency,
        Author:      item.Author,
        Tags:        append([]string(nil), item.Tags...),
        Status:      item.Status,
    }
}
```

这不是重复劳动，而是边界转换。

面试时可以这样说：

```text
Application read model 是内部用例结果，DTO 是外部 API 合同。
它们可以长得很像，但我不会默认它们是同一个对象。
这样未来接口字段变化不会反向污染 Application 层。
```

---

## 8.3 ProductHandler 是被三个 HTTP 愿望逼出来的

现在有三个 HTTP 愿望：

```text
GET /api/v1/products
GET /api/v1/products/:id
GET /api/v1/products/:id/execute
```

于是 `ProductHandler` 出现。

```go
type ProductHandler struct {
    productAppService *ProductAppService
}
```

它的依赖只有 Application Service。

这条依赖方向很重要：

```text
HTTP Handler → Application Service
```

而不是：

```text
HTTP Handler → ProductRepository
HTTP Handler → ProductDomainService
HTTP Handler → StablePayClient
```

如果 Handler 直接依赖这些东西，它就会变成购买流程的大杂烩。

当前 `ProductHandler` 有三个方法：

```go
func (h *ProductHandler) ListProducts(ctx context.Context, c *app.RequestContext)
func (h *ProductHandler) GetProduct(ctx context.Context, c *app.RequestContext)
func (h *ProductHandler) ExecutePurchase(ctx context.Context, c *app.RequestContext)
```

它们分别对应三个 URL。

这就是 Adapter 的核心职责：

> 把 HTTP 请求翻译成 Application 命令，再把 Application 结果翻译成 HTTP 响应。

---

## 8.4 第一个翻译：分页参数属于 HTTP 输入，不属于 Domain

商品列表接口会有分页：

```bash
GET /api/v1/products?page=1&size=20
```

这里的 `page` 和 `size` 来自 query string。

它们首先是 HTTP 输入，不是领域规则。

所以解析分页放在 Adapter：

```go
func parsePagination(c *app.RequestContext) (int, int) {
    page := parsePositiveInt(c.DefaultQuery("page", "1"), 1)
    size := parsePositiveInt(c.DefaultQuery("size", "20"), 20)
    if size > MaxSize {
        size = MaxSize
    }
    return page, size
}
```

然后再调用 Application：

```go
items, total, err := h.productAppService.ListProducts(ctx, page, size)
```

这里的决策是：

```text
Adapter 负责从 query 里拿 page/size；
Application 负责执行 ListProducts 用例；
Repository 负责怎么分页查商品。
```

不要把 `c.Query("page")` 这种 Hertz 代码传到 Application 里。

---

## 8.5 第二个翻译：商品 ID 来自 path，不是业务层自己猜

商品详情接口：

```bash
GET /api/v1/products/ai-agent-job-2025
```

这里的 `ai-agent-job-2025` 是 path 参数。

Hertz 里可以通过：

```go
skuID := c.Param("id")
```

取出来。

于是 Handler 做：

```go
skuID := strings.TrimSpace(c.Param("id"))
if skuID == "" {
    writeError(c, 400, "MISSING_PRODUCT_ID", "product id is required")
    return
}

item, err := h.productAppService.GetProductDetail(ctx, skuID)
```

注意，Application 不应该知道这个 skuID 是从 path、query、body，还是 MCP tool 参数来的。

它只知道：

```text
我要查这个 skuID 的商品详情。
```

这就是 Adapter 翻译层的意义。

---

## 8.6 第三个翻译：AgentDID 暂时来自 query，但以后可以改

购买执行接口：

```bash
GET /api/v1/products/ai-agent-job-2025/execute?agent_did=did:solana:xxx
```

这里我暂时让 `agent_did` 从 query 里传入。

于是 Handler 做：

```go
agentDID := strings.TrimSpace(c.Query("agent_did"))
if agentDID == "" {
    writeError(c, 400, "MISSING_AGENT_DID", "agent_did query parameter is required")
    return
}
```

为什么不是放在 Domain？

因为 `agent_did` 从哪里来，是传输层设计。

今天它来自 query。
明天可以来自 header。
后天可能来自 OpenClaw 插件的 tool input。
将来如果有登录态，也可能来自认证上下文。

这些变化不应该影响 Domain 和 Application。

所以 Application 只接收：

```go
ExecutePurchaseCommand{
    SKUID:    skuID,
    AgentDID: agentDID,
}
```

它不关心 AgentDID 是怎么被 HTTP 解析出来的。

---

## 8.7 x402 v2 的核心 Adapter 决策：读 PAYMENT-SIGNATURE

购买流程最关键的 HTTP 输入是：

```text
PAYMENT-SIGNATURE
```

这是 x402 v2 里客户端支付后重试请求时携带的 header。

未支付时，Agent 第一次请求一般没有这个 header。
支付后，Agent 再次请求同一个资源，会带上它。

所以 Handler 做：

```go
paymentSignature := strings.TrimSpace(
    string(c.GetHeader(domainSvc.X402PaymentSignatureHeader)),
)
```

这里 `domainSvc.X402PaymentSignatureHeader` 的值是：

```text
PAYMENT-SIGNATURE
```

为什么这个动作在 Adapter？

因为“从 HTTP Header 读字符串”是 HTTP 细节。

Application 不应该知道 Hertz 的 `GetHeader`。
Domain 不应该知道请求头。
Infrastructure 不应该处理资源接口的 HTTP 输入。

于是 Handler 把它翻译成 Command：

```go
cmd := ExecutePurchaseCommand{
    SKUID:            skuID,
    AgentDID:         agentDID,
    PaymentSignature: paymentSignature,
}
```

这就是边界。

---

## 8.8 为什么临时兼容 `Payment-Signature`？

代码里还做了一个兼容：

```go
if paymentSignature == "" {
    paymentSignature = strings.TrimSpace(string(c.GetHeader("Payment-Signature")))
}
```

严格来说，HTTP Header 本来大小写不敏感，`PAYMENT-SIGNATURE` 和 `Payment-Signature` 应该等价。但在真实工程里，不同 SDK、代理、网关、日志系统可能显示不同形态。

这里兼容一下不是为了继续支持旧协议，而是为了降低本地联调时的摩擦。

不过笔记里要明确：

```text
规范上以 x402 v2 的 PAYMENT-SIGNATURE 为准；
兼容写法只是迁移期工程处理；
最终文档和插件都应该使用 canonical header。
```

---

## 8.9 Application 返回未支付，Adapter 才决定 HTTP 402

`ExecutePurchase` 返回：

```go
result.Purchased == false
result.PaymentRequired != nil
```

这时 Application 只是说：

```text
业务上还没买，需要付款。
```

但它没有说：

```text
HTTP status code 应该是 402。
Header 应该叫 PAYMENT-REQUIRED。
Header value 应该是 Base64 JSON。
Body 应该怎么返回。
```

这些都是 Adapter 的职责。

于是 Handler 做：

```go
if !result.Purchased {
    writePaymentRequired(c, result)
    return
}
```

`writePaymentRequired` 里才出现 HTTP 402：

```go
c.Header("PAYMENT-REQUIRED", headerValue)
c.JSON(402, body)
```

这条边界非常关键。

如果 Application 直接返回 `consts.StatusPaymentRequired`，它就开始依赖 Hertz/HTTP。
如果 Domain 直接处理 Header，它就更糟糕。

所以正确分工是：

```text
Domain：定义 PaymentRequired 业务合约
Application：决定当前用例是否需要 PaymentRequired
Adapter：把 PaymentRequired 表达成 HTTP 402 + PAYMENT-REQUIRED Header
```

---

## 8.10 PAYMENT-REQUIRED Header 为什么由 Adapter 写？

x402 v2 要求资源服务端在未支付时返回 `PAYMENT-REQUIRED`，其中包含 base64 编码的 JSON PaymentRequired。

于是 Adapter 做：

```go
headerValue, err := domainSvc.EncodePaymentRequiredHeader(result.PaymentRequired)
if err != nil {
    writeError(c, 500, "PAYMENT_REQUIRED_ENCODE_FAILED", err.Error())
    return
}

c.Header(domainSvc.X402PaymentRequiredHeader, headerValue)
```

严格分层时，`EncodePaymentRequiredHeader` 这种 JSON + Base64 逻辑更靠近 Adapter，因为它是 HTTP Header 传输格式。当前代码里它暂时在 Domain Service 包里，是为了复用和推进实现，但要知道它已经站在 Domain 和 Adapter 的边界上。

更准确的长期方向是：

```text
X402PaymentRequired 结构：Domain
Encode to PAYMENT-REQUIRED header：Adapter / transport helper
```

这个反思很重要，因为它说明我不是机械地说“x402 都放 Domain”，而是区分：

```text
付多少钱拿什么资源：业务合约
怎么塞进 HTTP Header：传输细节
```

---

## 8.11 为什么 402 body 也返回 PaymentRequired？

既然 header 已经有 `PAYMENT-REQUIRED`，body 还要不要返回？

我选择 body 也返回可读的 PaymentRequired：

```json
{
  "x402Version": 2,
  "error": "PAYMENT-SIGNATURE header is required",
  "resource": {
    "url": "http://127.0.0.1:8787/api/v1/products/ai-agent-job-2025/execute",
    "description": "...",
    "mimeType": "application/json"
  },
  "accepts": [
    {
      "scheme": "exact",
      "network": "solana:...",
      "amount": "2000000",
      "asset": "USDC mint",
      "payTo": "seller address"
    }
  ]
}
```

原因很现实：

```text
Header 给 x402 客户端自动解析；
Body 给人类调试、curl、日志和 OpenClaw 排障看。
```

这不违背 x402。
Header 是机器流程的核心；body 是调试友好性。

尤其现在我们还在本地联调阶段，body 里看到 `amount`、`resource.url`、`payTo` 会非常有帮助。

---

## 8.12 为什么 DTO 里也定义了一份 x402 响应结构？

Domain 里已经有：

```go
X402PaymentRequired
X402ResourceInfo
X402PaymentRequirements
```

Adapter DTO 里又定义：

```go
PaymentRequiredResp
X402ResourceInfo
X402PaymentRequirement
```

看起来重复。

但这和 ProductItem 的原因一样：Domain 对象是业务合约，DTO 是 HTTP 响应合同。

现在二者字段基本一致，是因为 x402 本身就是一个公开协议对象。
但未来仍然可能出现差异：

```text
Domain 里可能增加内部校验字段；
HTTP body 可能隐藏某些 extensions；
不同版本 API 可能返回不同字段；
Header 编码对象和 body 调试对象可能分离。
```

所以 Handler 里做一次转换：

```go
func mapPaymentRequired(required *X402PaymentRequired) PaymentRequiredResp
```

这让边界更清楚。

如果后面确认完全不需要分离，也可以复用 Domain struct 直接响应。但在学习分层时，保留 DTO 更利于理解边界。

---

## 8.13 已购买时，Adapter 返回 HTTP 200

如果 Application 返回：

```go
result.Purchased == true
```

说明业务流程已经确认 Agent 可以访问资源。

这时 Adapter 返回：

```go
c.JSON(200, PurchaseExecuteResp{
    Product:       ...,
    MerchantProof: ...,
    GatewayProof:  ...,
    TxID:          ...,
    TxHash:        ...,
    Content:       ...,
})
```

这一步同样是翻译：

```text
Application 说：已购买，可以解锁。
Adapter 说：HTTP 200，body 返回内容。
```

如果有 tx 信息，Adapter 还会写：

```text
PAYMENT-RESPONSE
```

这可以作为客户端或调试工具读取的结算摘要。

注意，这里的 `PAYMENT-RESPONSE` 仍然是 HTTP 传输细节，所以只出现在 Adapter。

---

## 8.14 Router 为什么现在才真正注册商品路由？

之前 Router 里只有：

```go
GET /healthz
```

商品路由还是 TODO。

原因是前面还没有 Application Service 可调用。如果过早注册路由，Handler 要么只能返回假数据，要么就会把业务流程写死在 Adapter 里。

现在 Application 层已经有：

```go
ListProducts
GetProductDetail
ExecutePurchase
```

所以 Router 可以自然注册：

```go
v1 := r.srv.Group("/api/v1")
{
    v1.GET("/products", r.productHandler.ListProducts)
    v1.GET("/products/:id", r.productHandler.GetProduct)
    v1.GET("/products/:id/execute", r.productHandler.ExecutePurchase)
}
```

这一步不是简单“把 TODO 放开”，而是说明依赖链完整了：

```text
Route → Handler → Application → Domain / Port → Infrastructure
```

---

## 8.15 main.go 为什么要把 ProductHandler 接起来？

上一章 Application patch 里，`productAppSvc` 已经创建了，但还没有真正注入 Handler。

这意味着服务启动了，Use Case 也有了，但 HTTP 入口还没接上。

现在 main.go 做：

```go
productHandler := handler.NewProductHandler(productAppSvc)

router := adapter.NewRouter(h, healthHandler, productHandler)
router.Register()
```

这一步体现的是启动装配：

```text
Infrastructure 创建 repo/client
Domain 创建 domain service
Application 创建 app service
Adapter 创建 handler/router
Hertz 启动 HTTP 服务
```

`main.go` 仍然不写业务，只负责把对象组装起来。

---

## 8.16 Adapter 层的错误处理先简单，但边界要对

当前错误处理是 MVP 版本：

```go
func writeAppError(c *app.RequestContext, err error) {
    msg := err.Error()

    switch {
    case strings.Contains(msg, "is required"):
        status = 400
    case strings.Contains(msg, "not found"):
        status = 404
    case strings.Contains(msg, "not purchasable"):
        status = 400
    default:
        status = 500
    }

    c.JSON(status, dto.Error(code, msg))
}
```

这不是最终生产级写法。

更成熟的方式应该是：

```text
Domain/Application 定义 typed error；
Adapter 用 errors.Is / errors.As 判断；
统一错误码；
统一 request_id / trace_id；
内部错误不直接暴露给外部。
```

但现在先这样做有两个好处：

```text
不会阻塞主流程；
能让 curl 立刻看到清楚错误；
保留了未来重构成 typed error 的空间。
```

关键是：错误到 HTTP 状态码的映射放在 Adapter，而不是 Domain。

---

## 8.17 这一章以后，curl 应该怎么测？

服务启动：

```bash
go run ./cmd/merchant-server
```

查询商品列表：

```bash
curl -s http://127.0.0.1:8787/api/v1/products | python -m json.tool
```

查询商品详情：

```bash
curl -s http://127.0.0.1:8787/api/v1/products/ai-agent-job-2025 | python -m json.tool
```

第一次请求付费资源，不带 `PAYMENT-SIGNATURE`：

```bash
curl -i "http://127.0.0.1:8787/api/v1/products/ai-agent-job-2025/execute?agent_did=did:solana:agent111"
```

预期看到：

```text
HTTP/1.1 402 Payment Required
PAYMENT-REQUIRED: <base64 json>
```

body 里应该有：

```json
{
  "x402Version": 2,
  "resource": {
    "url": "..."
  },
  "accepts": [
    {
      "scheme": "exact",
      "amount": "2000000",
      "asset": "...",
      "payTo": "..."
    }
  ]
}
```

这说明 Adapter 已经把 Application 的“未支付”业务结果翻译成了 x402 v2 HTTP 形态。

---

## 8.18 当前 Adapter 层最终长成什么样？

本章之后，Adapter 层主要有：

```text
internal/adapter/
├── dto/
│   ├── request.go
│   └── response.go
├── handler/
│   ├── health_handler.go
│   └── product_handler.go
└── router.go
```

职责分别是：

```text
request.go：
  定义 HTTP 请求 DTO，包括 agent_did 和 PAYMENT-SIGNATURE

response.go：
  定义 HTTP 响应 DTO，包括商品列表、商品详情、x402 v2 402 body、购买成功 body

product_handler.go：
  解析 path/query/header，调用 ProductAppService，把结果翻译成 HTTP 200/402/错误响应

router.go：
  注册 /healthz 和 /api/v1/products 系列路由
```

这时商品购买链路终于能从 HTTP 入口走到 Application 和 Domain。

---

## 8.19 这一章最重要的决策链

这一章不是从“我要写 Controller”开始的，而是被 HTTP 边界逼出来的：

```text
我想 curl 查询商品列表
  ↓
需要 GET /api/v1/products
  ↓
需要 ProductHandler.ListProducts
  ↓
需要 ProductListResp DTO

我想 curl 查询商品详情
  ↓
需要 GET /api/v1/products/:id
  ↓
需要从 path 里取 id
  ↓
需要 Handler 把 id 传给 Application

我想 Agent 请求付费资源
  ↓
需要 GET /api/v1/products/:id/execute
  ↓
需要从 query 里取 agent_did
  ↓
需要从 PAYMENT-SIGNATURE header 里取支付签名

Application 返回未购买
  ↓
Adapter 返回 HTTP 402
  ↓
Adapter 写 PAYMENT-REQUIRED header
  ↓
Adapter 返回可读的 PaymentRequired body

Application 返回已购买
  ↓
Adapter 返回 HTTP 200
  ↓
Adapter 返回 content、merchant proof、gateway proof

ProductAppService 已经创建但没入口
  ↓
main.go 创建 ProductHandler
  ↓
router.go 注册商品路由
```

这就是 Adapter 层的学习方法：

> 不要先问“Controller 目录怎么放”。先问外部调用者怎么访问我，然后让 URL、Header、Query、Status Code 把 Handler 和 DTO 逼出来。

---

## 8.20 面试讲法

面试时可以这样讲 Adapter 层：

```text
我的 Adapter 层只处理 HTTP 协议边界。
比如商品购买接口里，Handler 会从 path 里取 sku_id，从 query 里取 agent_did，
从 PAYMENT-SIGNATURE header 里取 x402 支付签名，然后组装成 ExecutePurchaseCommand 调用 Application。
如果 Application 返回未购买，Adapter 才把它翻译成 HTTP 402，并写入 PAYMENT-REQUIRED header；
如果已购买，Adapter 返回 HTTP 200 和解锁内容。
```

如果面试官问为什么不在 Application 里返回 402，可以回答：

```text
因为 HTTP 402 是传输层表达，不是业务用例本身。
Application 只返回“未支付，需要 PaymentRequired”这个业务结果；
Adapter 再决定用 HTTP 402、PAYMENT-REQUIRED Header 和 JSON body 表达它。
这样未来如果换成 MCP Tool、gRPC 或其他协议，Application 和 Domain 仍然能复用。
```

如果面试官问 x402 为什么 body 和 header 都有，可以回答：

```text
PAYMENT-REQUIRED header 是给 x402 客户端自动解析的 canonical 传输位置；
body 返回同样的结构是为了 curl、本地调试和日志可读性。
生产上客户端应该以 header 为准，body 主要是辅助排障。
```

到这里，Agent 侧已经可以通过 HTTP 访问商户后端了。下一章自然应该进入 Infrastructure 层：把现在还是 stub 的 StablePayClient 真正接到 Gateway 验证接口，或者把当前内存仓储替换成真正 SQLite。
