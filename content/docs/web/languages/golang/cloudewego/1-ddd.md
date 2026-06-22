# 1. 后端分层对象
这一章不再从 HTTP、JSON、路由这些基础概念讲起，更需要补上的其实是另一个后端高频问题：为什么项目里会出现这么多“对象”？

很多刚开始写后端的人，最容易写出这样的代码：

```go
func ListProducts(ctx context.Context, c *app.RequestContext) {
    // 1. 直接从 HTTP query 里拿参数
    // 2. 直接查数据库
    // 3. 直接把数据库结果改一改
    // 4. 直接 c.JSON 返回
}
```
这当然能跑。小 demo 里甚至很方便。

但问题是，业务一复杂，这个 Handler 就会同时承担很多职责：
- HTTP 参数解析
- 数据库查询
- 业务规则判断
- 价格格式转换
- 支付状态验证
- 响应 JSON 组装
- 错误码处理
- 日志记录

久而久之，Handler 会变成一个“上帝函数”。你想改接口字段，可能影响数据库逻辑；你想换数据库，可能影响 API 响应；你想测试商品是否可购买，结果还得启动 HTTP 服务和数据库。

后端分层对象的价值就在这里：不同对象服务于不同层，分别表达不同阶段的数据形态。

在企业后端里，经常会看到这些名词：
| 缩写 | 标准英文全称 | 中文 | 常用场景 & 例句 |
|------|-------------|------|----------------|
| **DTO** | **Data Transfer Object** | 数据传输对象 | 跨层、跨服务传输数据<br>例：Convert entity to DTO.（实体转DTO） |
| **PO** | **Persistent Object** | 持久化对象 | 映射数据库表，DAO/数据库层专用 |
| **DO** | **Domain Object** | 领域对象 | 领域模型、业务核心实体（DDD 领域驱动设计） |
| **BO** | **Business Object** | 业务对象 | 业务层聚合数据，承载业务数据组合 |
| **VO** | **View Object** | 视图对象 | 向前端页面返回、视图展示用 |
| **Query** | Query Object | 查询对象 | 接口查询入参（分页、筛选条件） |
| **Request** | Request DTO / Request Object | 请求对象 | 前端传给后端的接口入参 |
| **Response** | Response DTO / Response Object | 响应对象 | 后端返回给前端的接口出参 |
| **Entity** | Entity / Entity Class | 实体类 | 现代主流叫法 ≈ PO，MyBatis/JPA 标配 |

它们不是某种绝对统一的标准，不同团队、不同框架、不同语言会有差异。但背后的核心思想是一样的：

> 不要让同一个对象同时承担接口入参、数据库表结构、业务模型、页面展示、领域规则这五种职责。

下面我按照常见理解来梳理。

## 1.1 DTO：Data Transfer Object，数据传输对象
DTO 是最常见的后端对象之一。

它的核心作用是：**在不同进程、不同系统、不同层之间传输数据**。

在 Web 后端里，DTO 最常见的使用场景就是 API 的请求和响应。

比如商品列表接口：

```http
GET /api/v1/products?page=1&page_size=20
```

请求参数可以被组织成一个 Request DTO：
```go
type ListProductsRequest struct {
    Page     int `query:"page"`
    PageSize int `query:"page_size"`
}
```
响应结果也可以组织成一个 Response DTO：
```go
type ProductListResponse struct {
    Items []ProductItem `json:"items"`
    Total int           `json:"total"`
}
```
这里的 `ProductItem` 也是 DTO，因为它是给 API 调用方看的：
```go
type ProductItem struct {
    SKUID       string `json:"sku_id"`
    Title       string `json:"title"`
    Description string `json:"description"`
    Price       string `json:"price"`
    Currency    string `json:"currency"`
}
```
DTO 的关键点是：它关注的是“接口长什么样”，而不是“业务内部怎么存”。

比如内部 `Product` Entity 里可能有：
```text
内部数据库 ID
商品状态
SkillDid
创建时间
更新时间
是否删除
成本价
商户 ID
```
但商品列表 API 未必需要全部返回。对外接口应该只返回调用方需要的字段。

所以 DTO 是一种边界对象。它站在系统边界上，负责和外部世界交换数据。

在当前 Merchant Server 里，`internal/adapter/dto` 目录里的 request 和 response，本质上就是 DTO。它们属于 Adapter 层，因为它们和 HTTP API 的输入输出关系最密切。

> 一旦 API 发布出去，DTO 的字段就不能随便改，因为调用方可能已经依赖它了。
## 1.2 PO：Persistent Object，持久化对象
PO 通常表示“数据库持久化对象”。

它和数据库表结构关系最紧密。

比如未来我们把商品存进 SQLite （权益之计，后面是 MySQL），可能有一张表：
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    price TEXT NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    skill_did TEXT NOT NULL,
    created_at DATETIME,
    updated_at DATETIME
);
```
对应的 Go 结构体可以叫：
```go
type ProductPO struct {
    ID          int64
    SKUID       string
    Title       string
    Description string
    Price       string
    Currency    string
    Status      string
    SkillDid    string
    CreatedAt   time.Time
    UpdatedAt   time.Time
}
```
PO 的特点是：
```text
字段通常和数据库列接近
类型通常服务于数据库读写
可能包含数据库内部字段
不一定适合直接暴露给前端或 Agent
```
比如 `id` 是数据库自增主键，外部 API 未必需要知道。
比如 `created_at`、`updated_at` 是数据库审计字段，商品列表接口未必展示。
比如未来有 `deleted_at` 或 `is_deleted`，这更不应该直接暴露给外部。

PO 不应该承担业务规则。它主要是为了让 Infrastructure 层和数据库打交道。

在当前项目里，虽然目录已经叫 `sqlite/product_repo_impl.go`，但第一阶段可以先不急着设计完整 PO。因为现在的重点是跑通领域模型和商品 API。等真正接入 SQLite 时，再单独引入 ProductPO 会更自然。
## 1.3 DO：Domain Object，领域对象
DO 通常表示领域对象，也可以叫 Domain Object。很多 DDD（领域驱动开发）项目里也会直接叫 Entity。

它关注的是业务本身，而不是接口长什么样，也不是数据库怎么存。

在当前项目里，`Product` 就可以理解为一个领域对象：
```go
type Product struct {
    ID          string
    SKUID       string
    Title       string
    Description string
    Price       string
    Currency    string
    Status      ProductStatus
    SkillDid    string
}
```
更重要的是，它不应该只是字段集合，还应该包含和商品自身有关的业务行为。

比如：
```go
func (p *Product) IsPurchasable() bool {
    return p.Status == ProductStatusActive &&
        p.Price != "" &&
        p.SkillDid != ""
}
```
这就不是 DTO，也不是 PO，而是领域逻辑。

如果某个商品是草稿状态，它不能购买；如果没有价格，它不能购买；如果没有 `SkillDid`，商户后端无法生成稳定的支付要求，它也不能购买。

这些规则属于商品业务本身，所以应该放在 Domain 层，而不是 Handler 或 SQL 里。

DO 的特点是：
```text
表达业务概念
包含业务规则
尽量不依赖框架
尽量不依赖数据库
可以独立单元测试
```
我更倾向于使用 `Entity` 这个命名，因为当前目录已经是：

```text
internal/domain/entity/product.go
```
也就是说，项目里不一定真的要命名成 `ProductDO`，但在概念上它承担的就是 DO / Entity 的职责。
## 1.4 BO：Business Object，业务对象
BO 是一个容易让人困惑的概念，因为它和 DO、Entity、DTO 有时候会重叠。

通常可以把 BO 理解为：**面向某个业务流程组合出来的对象**。

它不一定严格对应数据库表，也不一定是最核心的领域实体，而是服务于某个业务动作。

举个例子，商品本身是 Product Entity。
但“购买商品”这个动作可能需要更多信息：

```text
商品信息
Agent DID
支付金额
支付币种
商户收款地址
x402 payment requirement
当前是否已购买
proof 信息
```

这些信息组合在一起，可以形成一个 BO，比如：

```go
type PurchaseBO struct {
    Product      *Product
    AgentDID     string
    SkillDID     string
    AmountMinor  string
    Currency     string
    Purchased    bool
    PaymentProof *PaymentProof
}
```
这个对象不是数据库表，也不是 HTTP 响应本身，而是应用层或领域服务在处理“购买流程”时使用的业务中间对象。

BO 的特点是：
```text
面向业务流程
可能组合多个 Entity
可能包含计算后的业务字段
不一定直接持久化
不一定直接返回给外部
```

在当前项目早期，如果业务还简单，可以不急着显式创建 BO。比如 `ExecutePurchase` 里先直接使用 Product、VerifyResult、PaymentRequiredResponse 也可以。等购买流程复杂起来，比如支持订单、库存、优惠、购物车、多商品结算时，再引入 BO 会更合理。
## 1.5 VO：Value Object / View Object，两种常见含义

VO 是最容易混淆的一个词，因为它在不同语境下可能有两个意思。

第一种是 DDD 里的 Value Object，值对象。
第二种是前后端接口里的 View Object，视图对象。

这两个完全不是一回事。
### 1.5.1 Value Object：值对象
在 DDD 语境下，VO 是 Value Object。

值对象没有独立身份，通常用来表达一个不可拆分的业务值。

比如：
```text
Money
Price
Currency
WalletAddress
DID
```
以 Money 为例：
```go
type Money struct {
    AmountMinor int64
    Currency    string
}
```
它不关心自己是数据库第几行，也不需要独立 ID。
两个 Money 只要 `AmountMinor` 和 `Currency` 一样，就可以认为它们相等。

值对象的特点是：
```text
没有独立 ID
通过属性判断相等
通常不可变
表达业务值
可以封装校验逻辑
```

在 StablePay 项目里，`DID`、`WalletAddress`、`Money` 都很适合慢慢抽象成 Value Object。

比如现在很多地方可能直接用 string 表示 DID：
```go
AgentDID string
SkillDID string
```
第一阶段这样写没有问题。但如果后面 DID 校验越来越多，可以封装成：
```go
type DID string

func NewDID(raw string) (DID, error) {
    if !strings.HasPrefix(raw, "did:solana:") {
        return "", errors.New("invalid did")
    }
    return DID(raw), nil
}
```

这样 DID 的格式校验就不会散落在各个 Handler 里。

> 可以这样理解：
> Value Object = 有业务含义的值
### 1.5.2 View Object：视图对象
在很多 Java Web 项目里，VO 也会被用来表示 View Object，也就是给前端页面展示的数据对象。

比如：
```go
type ProductCardVO struct {
    Title       string
    PriceLabel  string
    Badge       string
    ButtonText  string
}
```
这种 VO 更接近“页面展示模型”。

但在当前 Merchant Server 里，调用方不是传统网页前端，而是 OpenClaw Agent。所以我们未必需要 View Object 这个概念。多数情况下，用 Response DTO 就足够了。

为了避免混乱，我在这个项目里会尽量这样约定：

```text
VO 如果出现在 Domain 层，表示 Value Object
DTO 如果出现在 Adapter 层，表示 API 请求/响应对象
不要轻易用 VO 表示接口响应，避免和 Value Object 混淆
```
## 1.6 Entity：实体对象
Entity 和 DO 很接近，但在 DDD 语境里 Entity 更强调“有唯一身份”。

比如 Product 是一个 Entity，因为它有自己的身份：
```text
ID
SKUID
SkillDID
```
即使商品标题改了、描述改了、价格改了，它仍然是同一个商品。

Entity 的特点是：
```text
有唯一标识
生命周期会变化
包含业务行为
属于领域层核心对象
```
Product 就是典型 Entity。

比如：
```go
func (p *Product) Activate() {
    p.Status = ProductStatusActive
}

func (p *Product) Deactivate() {
    p.Status = ProductStatusInactive
}

func (p *Product) IsPurchasable() bool {
    return p.Status == ProductStatusActive &&
        p.Price != "" &&
        p.SkillDid != ""
}
```
这些方法都围绕商品自己的生命周期和业务状态展开。

> 可以这样理解：
> Entity = 有身份、有生命周期、有业务规则的领域对象
## 1.7 当前项目里应该怎么使用这些对象？
结合 Merchant Server 当前的 COLA 四层结构，我可以把对象放置规则整理成这样：
```text
Adapter 层：
  Request DTO
  Response DTO

Application 层：
  Command
  Query
  Result
  BO，可选

Domain 层：
  Entity
  Value Object
  Repository Interface
  Domain Service

Infrastructure 层：
  PO
  DAO / Repository Impl
  外部 Client 返回对象
```
更具体一点：
```text
internal/adapter/dto/request.go
  ListProductsRequest
  ExecutePurchaseRequest

internal/adapter/dto/response.go
  ProductListResponse
  ProductDetailResponse
  PaymentRequiredResponse
  PurchaseExecuteResponse

internal/domain/entity/product.go
  Product
  ProductStatus

internal/domain/repository/product_repo.go
  ProductRepository

internal/domain/service/product_domain_service.go
  ProductDomainService

internal/infrastructure/persistence/sqlite/product_repo_impl.go
  ProductPO
  ProductRepoImpl

internal/infrastructure/client/stablepay_client.go
  VerifyPurchaseRequest
  VerifyPurchaseResponse
```
注意，这不是说每个对象都必须立刻创建。分层对象是为复杂度服务的，不是为了制造复杂度。

当前项目处于 MVP 阶段，所以可以遵循一个原则：

```text
先保证对象边界清晰；
不要为了名词完整而过度设计。
```

也就是说：
1. API 入参和出参优先用 DTO；
2. 核心业务对象用 Entity；
3. 数据库真正落地后再引入 PO；
4. 购买流程复杂后再引入 BO；
5. DID、Money、WalletAddress 等校验变多后再抽 Value Object。
## 1.8 一个商品列表请求在这些对象之间如何流转？
以未来的 `GET /api/v1/products` 为例。

完整链路可以这样理解：
```text
HTTP Query
  ↓
ListProductsRequest DTO
  ↓
ProductAppService.ListProducts()
  ↓
ProductRepository.FindAll()
  ↓
ProductPO / 数据库记录
  ↓
Product Entity
  ↓
ProductListResponse DTO
  ↓
JSON Response
```
如果画成分层结构：

```text
Adapter 层
  接收 HTTP 请求
  解析成 Request DTO
  调用 Application

Application 层
  编排 ListProducts 这个用例
  调用 Repository
  把 Entity 转成 Response DTO

Domain 层
  定义 Product Entity
  定义 ProductRepository 接口
  保留商品业务规则

Infrastructure 层
  用 SQLite 查询 ProductPO
  把 ProductPO 转成 Product Entity
```
这里最关键的是两个转换：
```text
ProductPO → Product Entity
Product Entity → ProductResponse DTO
```
第一个转换发生在 Infrastructure 层附近，因为它要把数据库结构转成业务对象。

第二个转换发生在 Application 或 Adapter 层附近，因为它要把业务对象转成外部接口响应。
## 1.9 一个购买请求在这些对象之间如何流转？
购买流程会更复杂。以未来的：
```http
GET /api/v1/products/:sku_id/execute?agent_did=did:solana:xxx
```
为例。

如果 Agent 没有购买，流程大概是：
```text
ExecutePurchaseRequest DTO
  ↓
ProductAppService.ExecutePurchase()
  ↓
ProductRepository.FindBySKUID()
  ↓
Product Entity
  ↓
ProductDomainService.CheckPurchasable()
  ↓
StablePayClient.VerifyPurchase()
  ↓
发现未购买
  ↓
生成 PaymentRequiredResponse DTO
  ↓
HTTP 402 Payment Required
```

如果 Agent 已经购买，流程大概是：
```text
ExecutePurchaseRequest DTO
  ↓
ProductAppService.ExecutePurchase()
  ↓
查 Product Entity
  ↓
验证 purchased = true
  ↓
生成 PurchaseExecuteResponse DTO
  ↓
HTTP 200 OK
```

这里可能会出现 `PurchaseContextBO`。它可以临时承载：
```text
Product
AgentDID
SkillDID
PaymentRequired
VerifyResult
```

## 1.10 不同对象之间最容易犯的错误
### 错误 1：直接把数据库对象返回给外部

比如：

```go
c.JSON(200, productPO)
```

问题是，数据库对象可能包含内部字段，比如自增 ID、删除状态、成本价、审计字段。外部 API 不应该被数据库结构绑死。

更好的做法是：

```text
ProductPO → Product Entity → ProductResponse DTO
```

---

### 错误 2：把业务规则写在 DTO 里

比如在 `ProductListResponse` 里写：

```go
func (p ProductListResponse) IsPurchasable() bool
```

这不合理。Response DTO 是给外部看的结果，不应该承载核心业务判断。

业务判断应该放在 Product Entity 或 Domain Service 里。

### 错误 3：把 HTTP 逻辑写进 Domain 层

比如 Domain 层里直接返回：

```go
return 402, PaymentRequiredResponse{}
```

这也不合理。HTTP 402 是协议层概念，属于 Adapter 层。Domain 层可以表达“未支付”这个业务结果，但不应该知道 HTTP 状态码。

更好的方式是：

```text
Domain/Application 返回业务错误或业务结果
Adapter 决定转成 402 还是 200
```
### 错误 4：为每一个概念都强行建对象

比如一开始就写：

```text
ProductDTO
ProductVO
ProductBO
ProductDO
ProductPO
ProductEntity
ProductModel
```

这会让项目变得非常臃肿。

对象拆分应该随着复杂度增长逐渐引入。

当前阶段最重要的是：

```text
Request DTO
Response DTO
Product Entity
ProductRepository Interface
ProductRepoImpl
```

这些已经足够支撑第一版商品列表和购买流程。

## 1.11 小结
这一章最重要的结论是：
```text
DTO 关注接口传输
PO 关注数据库持久化
Entity / DO 关注业务核心
BO 关注业务流程组合
VO 在本项目中优先理解为 Value Object
```
对应到 Merchant Server：
```text
Agent 看到的是 DTO
数据库保存的是 PO
业务判断依赖的是 Product Entity
购买流程可能会组合出 BO
DID、Money、WalletAddress 未来可以抽成 Value Object
```
后端分层对象的本质不是背名词，而是 **降低耦合**。

如果接口字段变了，不应该影响数据库表。
如果数据库换了，不应该影响领域规则。
如果商品可购买规则变了，不应该散落在每个 Handler 里。
如果支付流程变复杂，不应该把所有参数都塞进一个巨大的函数里。
