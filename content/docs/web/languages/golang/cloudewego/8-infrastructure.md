# 8. Infrastructure 层
前面三章已经把核心链路拆出来了。
| 层级 | 内容 |
| ---- | ---- |
| Domain 层 | 商品是什么？<br>商品什么时候能买？<br>价格怎么精确转换？<br>x402 v2 PaymentRequired 这个业务合约怎么表达？<br>购买成功后 proof 怎么生成？ |
| Application 层 | Agent 请求执行商品时，先查商品，再判断是否可购买，再验证是否已支付。<br>如果未支付，返回 PaymentRequired。<br>如果已支付，返回内容和 proof。 |
| Adapter 层 | URL 怎么设计？<br>sku_id 从 path 取还是 query 取？<br>agent_did 从哪里取？<br>PAYMENT-SIGNATURE 从哪个 header 读？<br>未支付时怎么返回 HTTP 402？<br>PAYMENT-REQUIRED header 怎么写？ |

Infrastructure 层负责把 Application 需要的能力真正接起来：
```text
ProductRepository 接口
  ↓
SQLite ProductRepoImpl

PaymentVerifier 接口
  ↓
StablePayClient HTTP 调用 Gateway
```
## 8.1 决策链路
### 8.1.1 从第一个痛点开始：内存 map 不能支撑真实商户后端
最早为了让 Application 能跑，我可以写一个内存仓储：

```go
type ProductRepoImpl struct {
    products map[string]*Product
}
```

这非常适合第一阶段。

因为那时我最关心的是：

```text
Domain 规则是否能跑？
Application Use Case 是否能串起来？
Adapter 能不能返回商品列表和 HTTP 402？
```

内存 map 的好处是简单：

```text
不用装数据库
不用写 SQL
不用处理迁移
测试很快
代码容易理解
```

但它很快会暴露问题。

服务一重启，商品没了。
多个进程不能共享数据。
本地测试和云上部署的数据状态完全不稳定。
后续商品管理、状态更新、seed 数据都不好持续演进。

于是新的愿望出现了：

```text
我希望商品能持久化。
我希望服务重启后商品还在。
我希望不直接动已有 MySQL。
我希望 MVP 阶段不用单独部署数据库。
```

这几个愿望把我逼向 SQLite。

---

## 9.2 为什么是 SQLite，而不是立刻上 MySQL？

如果一开始就接 MySQL，也不是不行。

但当前 Merchant Server 还是 MVP 阶段。它首先要证明的是：

```text
Agent 能远程查询商品；
Agent 能请求商品执行接口；
未支付时商户返回 x402 v2 PaymentRequired；
支付后能验证并解锁内容。
```

这时直接接 MySQL 会引入很多额外复杂度：

```text
数据库实例在哪里？
连接串怎么管理？
K8s Secret 怎么配？
本地开发怎么连？
测试库怎么清理？
迁移工具怎么跑？
多人开发如何共享 schema？
```

SQLite 更适合现在这个阶段：

```text
它是文件数据库；
不需要单独部署服务；
本地和容器里都能跑；
适合少量商品的商户 MVP；
未来切 MySQL 时，上层不用大改。
```

所以这里的决策不是“SQLite 比 MySQL 更高级”，而是：

> 当前阶段我需要轻量持久化，不需要一上来引入完整数据库运维复杂度。

这也是 Repository 接口提前存在的意义。

Application 依赖的是：

```go
type ProductRepository interface {
    FindAll(...)
    FindBySKUID(...)
    Save(...)
}
```

它不关心底层是内存、SQLite 还是 MySQL。

现在我只是把 Infrastructure 实现从内存 map 换成 SQLite。

---

## 9.3 Repository 接口不是数据库接口，而是业务所需能力

这里要再强调一次。

`ProductRepository` 放在 Domain 层，不是因为 Domain 想碰数据库。

它表达的是业务需要：

```text
我要列出商品。
我要根据 sku_id 查商品。
我要保存商品。
我要修改商品状态。
```

这些是业务语言。

但 SQL 是技术语言：

```sql
SELECT ...
INSERT ...
UPDATE ...
CREATE TABLE ...
```

Infrastructure 的职责就是翻译：

```text
业务需要的 ProductRepository 方法
  ↓
具体 SQLite SQL 语句
```

所以 SQLite 实现的起点不是“我想写一张 products 表”，而是：

> 我已经有了 ProductRepository 接口，现在要让它真的能从 SQLite 里读写 Product。

---

## 9.4 什么时候才需要 PO？

前面第 1 章讲过 DTO、PO、DO、BO、VO。

到了 Infrastructure 层，PO 的动机才真正出现。

Domain 里的 `Product` 是业务对象：

```go
type Product struct {
    SKUID    string
    Title    string
    Price    string
    Currency string
    Status   ProductStatus
    SkillDid string
    Tags     []string
}
```

但 SQLite 里不认识 `ProductStatus`，也不能直接存 `[]string`。
数据库关心的是列：

```sql
sku_id TEXT
title TEXT
price TEXT
currency TEXT
status TEXT
skill_did TEXT
tags_json TEXT
```

于是我需要一次转换：

```text
SQLite row
  ↓
Product Entity
```

或者：

```text
Product Entity
  ↓
SQLite row
```

这就是 PO 的真实动机。

但当前 Go 实现里，我不一定要显式创建一个 `ProductPO` struct。
也可以直接在 scan/insert/update 函数里完成转换。

例如：

```text
Product.Tags []string
  ↓
json.Marshal
  ↓
tags_json TEXT

tags_json TEXT
  ↓
json.Unmarshal
  ↓
Product.Tags []string
```

这个转换属于 Infrastructure。

Domain 不应该知道 tags 是以 JSON 字符串存在 SQLite 里。
Application 也不应该知道。

所以 PO 的本质不是“必须建一个 ProductPO 文件”，而是：

> 数据库行结构和领域对象之间需要隔离。

当前实现选择了轻量方式：不额外暴露 ProductPO，而是在 SQLite Repo 内部完成 row/entity 转换。

---

## 9.5 第一张表是被 ProductRepository 逼出来的

当我开始实现 `FindBySKUID`，我自然需要 `sku_id`。

当我开始实现 `FindAll`，我自然需要 `status` 和分页排序字段。

当我开始实现 `Save`，我自然需要 `created_at`、`updated_at`。

于是表结构长成：

```sql
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price TEXT NOT NULL,
    currency TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL,
    skill_did TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

这个表不是从“数据库设计模板”里抄出来的，而是被几个用例逼出来的：

```text
商品列表需要 title、description、price、currency、status。
商品详情需要 sku_id 查找。
购买流程需要 skill_did。
支付金额需要 price、currency。
展示标签需要 tags。
生命周期需要 created_at、updated_at。
分页和内部更新需要 id。
```

再加索引：

```sql
CREATE INDEX IF NOT EXISTS idx_products_status_id ON products(status, id);
CREATE INDEX IF NOT EXISTS idx_products_sku_id ON products(sku_id);
```

这也是被查询模式逼出来的。

`FindAll` 只列 active 商品，并按 id 分页，所以需要 `(status, id)`。
`FindBySKUID` 高频根据 sku_id 查商品，所以需要 `sku_id`。

数据库 schema 不是为了“看起来完整”，而是服务查询路径。

---

## 9.6 为什么需要 Migrate？

本地第一次启动时，数据库文件可能不存在。
即使文件存在，表也可能不存在。

如果每次启动都要求手动建表，开发体验会很差。

所以 Infrastructure 层需要：

```go
func (r *ProductRepoImpl) Migrate(ctx context.Context) error
```

它负责：

```text
CREATE TABLE IF NOT EXISTS products
CREATE INDEX IF NOT EXISTS ...
```

这件事显然不是 Domain 的职责。
Product 不应该知道数据库表怎么建。
Application 也不应该在 Use Case 里建表。
Adapter 更不应该在 HTTP Handler 里建表。

所以 Migrate 放在 SQLite Repo 里。

启动时 main.go 根据配置决定是否执行：

```text
database.auto_migrate = true
```

这就是 Infrastructure 的典型职责：

> 处理技术资源的初始化。

---

## 9.7 为什么需要 Seed？

服务第一次启动后，如果商品表是空的，`GET /api/v1/products` 会返回空列表。

从技术上说这没错。
但从本地联调和产品演示角度看，这很不方便。

因为我希望一启动就能测：

```bash
curl http://127.0.0.1:8787/api/v1/products
```

然后马上看到几个商品。

所以需要 seed 数据。

但 seed 也不能每次启动都重复写。
否则商品会重复、ID 会乱、测试也不稳定。

所以 Seed 的规则是：

```text
如果 products 表为空，写入种子商品；
如果已经有商品，什么都不做。
```

这也是 Infrastructure 层的技术初始化逻辑。

为什么 seed 里仍然用 `ProductBuilder`？

因为即使是种子数据，也应该先构造合法 Product Entity，再通过 Repository 保存。

这样可以复用 Domain 校验：

```text
seed 数据不能绕过 Product 的基本规则。
```

---

## 9.8 Save 为什么不是简单 INSERT？

一开始我可能会写：

```sql
INSERT INTO products ...
```

但很快会遇到问题。

如果 seed 重跑了怎么办？
如果后台未来编辑商品怎么办？
如果 product.ID 已经存在怎么办？
如果 sku_id 已经存在但 ID 没传怎么办？

所以 Save 逐渐变成：

```text
如果 product.ID == 0：
    先根据 sku_id 查是否已有记录
    如果已有，转成更新
    如果没有，插入

如果 product.ID != 0：
    根据 id 更新
```

这一步不是为了炫技，而是为了让 Save 更符合 Repository 语义：

```text
Save 表示“保存这个 Product 的当前状态”；
它不应该只会插入，不会更新。
```

当然，生产环境里可以进一步拆成：

```text
CreateProduct
UpdateProduct
UpsertProduct
```

但 MVP 阶段，`Save` 足够支撑 seed 和简单管理。

---

## 9.9 为什么 DBReady 属于 Infrastructure？

之前 `/healthz` 里需要判断数据库是否可用。

如果是内存 map，`DBReady()` 永远返回 true。

但接入 SQLite 以后，健康检查应该至少执行：

```go
db.PingContext(ctx)
```

这说明 DBReady 是数据库技术状态检查。

它不属于 Domain。
商品是否可购买和数据库连接是否正常不是一回事。

它也不属于 Application。
Use Case 不应该负责健康检查数据库连接。

所以 DBReady 放在 SQLite Repo，main.go 注入 HealthHandler：

```go
healthHandler := handler.NewHealthHandler(cfg.Server.Name, productRepo.DBReady)
```

这样 `/healthz` 能继续工作，但数据库细节仍然留在 Infrastructure。

---

## 9.10 为什么 SQLite 要设置 MaxOpenConns(1)、busy_timeout、WAL？

这类配置是典型 Infrastructure 决策。

SQLite 是文件数据库。它轻量，但并发写入时容易遇到锁问题。

所以 MVP 阶段我选择保守策略：

```go
db.SetMaxOpenConns(1)
db.SetMaxIdleConns(1)
```

这意味着同一进程里 SQLite 写入更容易被串行化，少踩 “database is locked” 的坑。

再加：

```sql
PRAGMA busy_timeout = 5000;
PRAGMA journal_mode = WAL;
```

目的分别是：

```text
busy_timeout：
    遇到锁时不要立刻失败，等一小段时间。

WAL：
    文件数据库常用模式，有利于读写表现。
```

这不是业务逻辑。
Product 不需要知道。
Application 不需要知道。
Handler 更不需要知道。

这就是 Infrastructure 的价值：它吸收技术实现中的脏活、细节和坑。

---

## 9.11 第二个痛点：StablePayClient 不能永远返回 Purchased=false

前面 Application 层为了跑通未支付流程，允许 `PaymentVerifier` 返回：

```go
Purchased: false
```

这很适合先打通 402。

但真正购买后，商户后端必须能确认：

```text
这个 Agent 是否已经为这个 SkillDid / Product 支付过？
如果支付过，对应 tx_id 是什么？
tx_hash 是什么？
Gateway proof 是什么？
```

否则购买成功后还是永远返回 402。

所以 Infrastructure 的第二个任务是：

> 让 StablePayClient 实现 PaymentVerifier，并真正调用 StablePay Gateway。

---

## 9.12 StablePayClient 为什么实现 Application Port？

Application 层定义了：

```go
type PaymentVerifier interface {
    VerifyPurchase(ctx context.Context, req VerifyPurchaseRequest) (*VerifyPurchaseResult, error)
}
```

这代表 Use Case 需要的能力。

Infrastructure 现在实现它：

```go
type StablePayClient struct {
    baseURL    string
    apiKey     string
    httpClient *http.Client
}
```

然后：

```go
func (c *StablePayClient) VerifyPurchase(ctx context.Context, req VerifyPurchaseRequest) (*VerifyPurchaseResult, error)
```

这条依赖方向很重要：

```text
Application 定义接口；
Infrastructure 实现接口。
```

而不是：

```text
Application import StablePayClient。
```

这样以后 Gateway API 改了，或者从 HTTP 换成 SDK，Application 不需要改。
只要新的实现还满足 `PaymentVerifier` 接口即可。

这就是 Port/Adapter 的真实用途。

---

## 9.13 StablePayClient 具体做了什么？

当前实现把 Application 的请求：

```go
VerifyPurchaseRequest{
    AgentDID: "...",
    SkillDID: "...",
    PaymentSignature: "...",
}
```

翻译成 Gateway HTTP 请求：

```text
GET /api/v1/verify/proof?agent_did=...&skill_did=...
X-API-Key: ...
PAYMENT-SIGNATURE: ...
```

这里每个字段都有来源：

```text
agent_did：
    Agent 的 DID，来自 Adapter 解析后传给 Application。

skill_did：
    商品绑定的 StablePay 支付身份，来自 Product。

X-API-Key：
    Gateway 访问密钥，来自配置。

PAYMENT-SIGNATURE：
    x402 v2 客户端支付后重试时携带的签名，来自 HTTP Header。
```

StablePayClient 再把 Gateway 响应转换成 Application 认识的结果：

```go
type VerifyPurchaseResult struct {
    Purchased bool
    TxID      string
    TxHash    string
    Proof     map[string]any
}
```

这一步叫“归一化”。

Gateway 的 JSON 可以很复杂，但 Application 不应该关心它的原始响应长什么样。

---

## 9.14 为什么 404 可以被解释成未购买？

在验证支付时，可能出现两类失败：

```text
Gateway 挂了、认证失败、响应格式错误；
这个 Agent 确实没有购买记录。
```

前者应该返回 error。
后者不应该让整个用例 500。

所以当前实现里，Gateway 返回 404 时会被解释成：

```go
Purchased: false
```

这是一种工程选择。

因为对商户资源来说，“没找到购买证明”通常意味着“未购买”，接下来应该返回 402，而不是直接报系统错误。

但非 2xx 且不是 404 的响应，比如 401、500，则作为错误返回。

这条规则以后可以根据真实 Gateway 协议再细化。

---

## 9.15 为什么要限制响应体大小？

StablePayClient 读取 Gateway 响应时用了：

```go
io.LimitReader(resp.Body, 1<<20)
```

也就是最多读 1 MiB。

这属于典型 Infrastructure 防御性代码。

原因是外部服务响应不应该无限制读入内存。
即使 Gateway 是自己家的，也应该保持基本边界。

这不是业务规则。
这也不应该出现在 Application。

Infrastructure 层负责这种技术安全细节。

---

## 9.16 为什么 http.Client 要可注入？

`StablePayClient` 提供：

```go
NewStablePayClientWithHTTPClient(...)
```

这样测试可以传入自定义 HTTP client 或 httptest server。

这一步的动机是测试。

我希望测试 StablePayClient 时，不真的请求 `https://ai.wenfu.cn`。
而是启动一个本地 httptest server，模拟 Gateway 返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "purchased": true,
    "tx_id": "tx-001",
    "tx_hash": "hash-001"
  }
}
```

然后验证 StablePayClient 是否正确映射成：

```go
VerifyPurchaseResult{
    Purchased: true,
    TxID: "tx-001",
    TxHash: "hash-001",
}
```

这就是 Infrastructure 测试的重点：

```text
不测业务规则；
测技术适配是否正确。
```

---

## 9.17 main.go 为什么要改？

原来 main.go 里是：

```go
productRepo := sqlite.NewProductRepo()
```

因为当时 repo 只是内存实现，不可能失败。

现在 repo 要打开 SQLite 文件、创建目录、执行 PRAGMA、迁移 schema。
这些都可能失败。

所以必须改成：

```go
productRepo, err := sqlite.NewProductRepo(cfg.Database.Path, cfg.Database.AutoMigrate)
if err != nil {
    log.Fatalf("FATAL: failed to initialize product repository: %v", err)
}
defer productRepo.Close()
```

这一步说明 main.go 的职责仍然是“依赖装配”。

它不写 SQL，也不写业务规则。
它只是负责：

```text
根据配置创建 Infrastructure 实例；
把 Infrastructure 实例注入 Domain/Application/Adapter；
启动服务；
退出时释放资源。
```

---

## 9.18 Infrastructure 不是“低级层”，而是反腐层

写到这里，Infrastructure 层的意义会更清楚。

它不只是“放数据库代码的地方”。

它更像一个反腐层，负责把外部世界的形状转成内部系统的形状。

SQLite 的外部形状是：

```text
SQL row
TEXT
INTEGER
tags_json
created_at 字符串
sql.ErrNoRows
```

Domain 想要的是：

```text
Product Entity
[]string Tags
ProductStatus
time.Time
ErrProductNotFound
```

Gateway 的外部形状是：

```text
HTTP status
JSON envelope
X-API-Key
PAYMENT-SIGNATURE
data.tx_hash
data.purchased
```

Application 想要的是：

```text
VerifyPurchaseResult
Purchased
TxID
TxHash
Proof map
```

Infrastructure 的任务就是翻译。

所以它不是业务核心，但它很重要。
如果 Infrastructure 做不好，业务层就会被 SQL、HTTP、JSON envelope、错误码和外部接口污染。

---

## 9.19 这一章最终形成了什么？

本章之后，Infrastructure 层主要有：

```text
internal/infrastructure/
├── client/
│   ├── stablepay_client.go
│   └── stablepay_client_test.go
└── persistence/
    └── sqlite/
        └── product_repo_impl.go
```

职责分别是：

```text
product_repo_impl.go：
    用 SQLite 实现 ProductRepository；
    负责建表、索引、迁移、seed、SQL 查询、row/entity 转换、DBReady。

stablepay_client.go：
    用 HTTP 实现 PaymentVerifier；
    负责调用 StablePay Gateway verify/proof 接口；
    负责解析 Gateway JSON envelope；
    负责把外部响应归一化成 VerifyPurchaseResult。

stablepay_client_test.go：
    用 httptest 验证 Gateway HTTP 适配逻辑。
```

同时 main.go 也完成了新的依赖装配：

```text
SQLite ProductRepoImpl
  ↓
ProductDomainService
  ↓
ProductAppService
  ↓
ProductHandler
  ↓
Router
```

以及：

```text
StablePayClient
  ↓ implements PaymentVerifier
ProductAppService
```

---

## 9.20 这一章最重要的决策链

Infrastructure 层不是从“我要写数据库代码”开始的，而是这样被逼出来的：

```text
商品不能只存在内存里
  ↓
需要持久化

不想一开始动 MySQL
  ↓
选择 SQLite 文件数据库

Application 已经依赖 ProductRepository
  ↓
SQLite ProductRepoImpl 实现这个接口

SQL row 和 Product Entity 不一样
  ↓
需要 row/entity 转换

Product.Tags 是 []string，SQLite 没有这个类型
  ↓
tags_json 字段出现

第一次启动没有表
  ↓
Migrate 出现

本地联调需要默认商品
  ↓
Seed 出现

K8s /healthz 需要知道数据库是否可用
  ↓
DBReady 从永远 true 变成 db.PingContext

StablePayClient 不能永远返回未购买
  ↓
需要真实 Gateway HTTP 调用

Application 不想依赖 HTTP Client
  ↓
StablePayClient 实现 PaymentVerifier Port

Gateway JSON 不等于 Application 结果
  ↓
需要响应解析和结果归一化
```

这就是 Infrastructure 的学习方法：

> 不要先问“数据库代码放哪里”。先问 Application 需要什么外部能力，再用 Infrastructure 把这个能力真实接上，同时把技术细节挡在外面。

---

## 9.21 面试讲法

面试时可以这样讲 Infrastructure 层：

```text
我的 Infrastructure 层主要做两件事：数据持久化和外部服务适配。
数据侧，我让 SQLite ProductRepoImpl 实现 Domain 层定义的 ProductRepository 接口，
Application 仍然只依赖查商品、保存商品这些抽象能力，不关心 SQL。
支付侧，我让 StablePayClient 实现 Application 层定义的 PaymentVerifier Port，
把 Gateway 的 HTTP + JSON 响应归一化成 VerifyPurchaseResult。
```

如果面试官问为什么用 SQLite，可以回答：

```text
当前 Merchant Server 还是商户 MVP，商品量小，重点是先验证 Agent 查询商品、x402 付款、支付后解锁的闭环。
SQLite 不需要单独部署，适合本地开发和容器内轻量持久化。
同时上层只依赖 ProductRepository，所以未来换 MySQL 不需要重写 Domain 和 Application。
```

如果面试官问为什么不让 Application 直接调 Gateway，可以回答：

```text
Application 层需要的是“验证支付”这个能力，不应该依赖具体 HTTP Client 或 Gateway 响应格式。
所以我在 Application 层定义 PaymentVerifier Port，
Infrastructure 的 StablePayClient 去实现它。
这样 Gateway API 或 SDK 改了，Use Case 不需要跟着改。
```

如果面试官问 Infrastructure 和 Domain 的区别，可以回答：

```text
Domain 表达业务规则，比如商品是否可购买、金额如何转换、x402 PaymentRequired 业务合约如何构造。
Infrastructure 表达技术实现，比如 SQLite 表结构、SQL 查询、Gateway HTTP 请求、JSON envelope 解析。
两者之间通过接口隔离，避免技术细节污染业务核心。
```

到这里，Merchant Server 的四层已经基本闭环：

```text
Adapter：
    HTTP API 和 x402 Header

Application：
    购买商品 Use Case 编排

Domain：
    商品、金额、支付合约和 proof 规则

Infrastructure：
    SQLite 持久化和 Gateway 验证
```

下一步就不再是继续补某一层，而是做“端到端联调”：启动服务，查询商品，第一次请求返回 402，支付后携带 PAYMENT-SIGNATURE 重试，并确认 Gateway 验证通过后返回解锁内容。
