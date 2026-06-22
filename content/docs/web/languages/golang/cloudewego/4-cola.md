# 4. COLA v5
我们不是在写 Java 版 COLA，也不是必须照搬阿里巴巴 COLA 的所有规范，而是在 Go + CloudWeGo 项目里借鉴它的分层思想。

所以当前项目采用了类似 COLA 的四层思想：
```
Adapter        适配层
Application    应用层
Domain         领域层
Infrastructure 基础设施层
```
具体可以参考隔壁的[博客](../../../../../blog/2026/2026-03-19-cola-v5.md)。
## 4.1 项目结构
当前项目结构大致是：
```
merchant/
├── cmd/
│   └── merchant-server/
│       └── main.go
├── config/
│   ├── config.go
│   └── config.yaml
├── internal/
│   ├── adapter/
│   │   ├── dto/
│   │   ├── handler/
│   │   └── router.go
│   ├── application/
│   │   └── service/
│   ├── domain/
│   │   ├── entity/
│   │   ├── repository/
│   │   └── service/
│   └── infrastructure/
│       ├── client/
│       └── persistence/
│           └── sqlite/
└── docs/
```
我先给每个目录一个非常朴素的理解：
- cmd：服务入口，负责启动
- config：配置加载
- adapter：HTTP 入口和接口 DTO
- application：业务用例编排
- domain：核心业务模型和规则
- infrastructure：数据库、外部服务等技术细节
- docs：架构、开发、面试文档

## 4.2 `cmd/merchant-server/main.go`：启动入口
上一章已经说过了，`main.go`主要完成手写依赖注入：
- 加载配置
- 创建仓储
- 创建外部客户端
- 创建领域服务
- 创建应用服务
- 创建 Hertz Server
- 创建 Handler
- 注册路由
- 启动服务
比如：
```
productRepo 传给 productDomainSvc
productDomainSvc 传给 productAppSvc
healthHandler 传给 Router
Router 注册到 Hertz Server
```
这样做的好处是：我能清楚看到对象之间的依赖关系。

如果以后要把 `ProductRepoImpl` 从内存模拟换成真正 SQLite，理论上只需要改 `main.go` 里的组装和 Infrastructure 实现，而不用改 Domain 层的业务规则。
## 4.3 Adapter 层：处理 HTTP 世界
当前项目里的 Adapter 层在`internal/adapter`，它下面有：
```
dto/
handler/
router.go
```
Adapter 层面对的是 HTTP 世界，所以它关心：
- URL 怎么设计
- Query 参数怎么取
- Path 参数怎么取
- Header 怎么读
- Body 怎么解析
- 返回什么 JSON
- HTTP 状态码是多少
比如现在的 `router.go` 里注册：
```go
// 职责：作为系统对外的入口，适配不同的接入方式（HTTP、gRPC、MQ 等）
package adapter

// 导入依赖包
import (
	// Hertz 框架服务器核心包：提供 HTTP 服务器实例和路由能力
	"github.com/cloudwego/hertz/pkg/app/server"
	// 内部处理器包：存放所有接口的业务处理逻辑
	// 按 COLA 规范，handler 只负责参数接收、校验、返回结果，不包含业务逻辑
	"github.com/stablepay/merchant-server/internal/adapter/handler"
)

// Router 路由注册器
// 【设计思想】采用 单一职责原则 + 依赖注入
// 1. 单一职责：这个类只做一件事——注册所有 HTTP 路由
// 2. 依赖注入：通过构造函数传入所有依赖（Hertz 实例、各个 Handler），解耦创建和使用
// 3. COLA 风格：将路由注册逻辑从 main 函数中抽离，集中管理所有接口
type Router struct {
	// srv Hertz 服务器实例
	// 所有路由最终都注册到这个实例上
	srv *server.Hertz

	// healthHandler 健康检查处理器
	// 所有 /healthz 相关的请求都由这个处理器处理
	// 【业务意义】运维接口，用于 K8s 容器探测、负载均衡健康检查
	healthHandler *handler.HealthHandler
}

// NewRouter 路由注册器构造函数
// 【语法】Go 中构造函数的标准写法：NewXxx 命名，返回 *Xxx 指针
// 【设计思想】依赖注入的入口
// 外部将已经创建好的 Hertz 实例和 Handler 传入，Router 只负责组装和注册
// 好处：便于单元测试（可以传入 Mock 的 Handler）、解耦依赖创建
func NewRouter(srv *server.Hertz, hh *handler.HealthHandler) *Router {
	// 返回初始化后的 Router 指针
	return &Router{
		srv:           srv,
		healthHandler: hh,
	}
}

// Register 执行路由注册
// 【业务意义】这是路由模块的唯一对外方法，main 函数只需要调用这一个方法就能完成所有路由注册
// 【设计原则】
// 1. 分层注册：运维接口、公开 API、内部 API 分块管理，一目了然
// 2. 预留扩展：按模块预留分组位置，后续添加新模块只需在对应区域添加
// 3. 统一规范：所有接口遵循相同的命名和路径规则
func (r *Router) Register() {
	// ==================== 运维 & 内部接口区 ====================
	// 【业务规范】所有运维接口都放在根路径，不添加版本前缀
	// 行业标准路径：
	// - /healthz：存活探测（Liveness Probe）
	// - /readyz：就绪探测（Readiness Probe）
	// - /metrics：Prometheus 监控指标
	// - /debug/pprof：性能分析接口
	r.srv.GET("/healthz", r.healthHandler.Healthz)

	// ==================== 公开 API v1 分组区 ====================
	// 【业务规范】所有对外公开的业务接口都使用 /api/v1/ 前缀
	// 版本号前缀的意义：
	// 1. 支持多版本共存，便于不兼容升级
	// 2. 统一管理所有公开接口
	// 3. 可以给整个 v1 分组统一添加中间件（如鉴权、限流、日志）
	// v1 := r.srv.Group("/api/v1")
	// {
	// 	// 商品模块路由
	// 	v1.GET("/products", r.productHandler.ListProducts)    // 获取商品列表
	// 	v1.GET("/products/:id", r.productHandler.GetProduct) // 获取单个商品详情
	// 	v1.POST("/products/:id/execute", r.productHandler.ExecutePurchase) // 执行商品购买
	//
	// 	// 后续添加新模块直接在这里加
	// 	// 订单模块路由
	// 	// v1.GET("/orders", r.orderHandler.ListOrders)
	// }
}
```
一个后端系统，会被**各种各样的外部系统/客户端**调用，它们用的通信协议、数据格式、调用方式完全不一样：
| 接入方式 | 通信协议 | 数据格式 | 典型使用场景 | 调用方式 |
|---------|---------|---------|-------------|---------|
| **HTTP** | HTTP/HTTPS | JSON | 前端网页、手机APP、第三方API调用 | 同步调用：发请求 → 等响应 |
| **gRPC** | HTTP/2 | Protobuf | 微服务之间的内部调用 | 同步调用：高性能、强类型 |
| **MQ（消息队列）** | TCP | 自定义二进制/JSON | 异步事件通知、解耦系统 | 异步调用：发消息就走，不等待结果 |
| **WebSocket** | WebSocket | JSON | 实时通信（聊天、推送） | 双向长连接 |
| **Dubbo** | TCP | Hessian/Java序列化 | 传统Java微服务内部调用 | 同步调用 |

**同一个业务逻辑，能被上面所有不同的接入方式调用，而不需要改业务代码。**

举个最经典的例子：**「创建订单」这个业务逻辑**
- 前端用户在网页上下单 → 用 **HTTP** 调用
- 订单服务调用支付服务 → 用 **gRPC** 调用
- 支付成功后，MQ通知订单服务更新状态 → 用 **MQ** 调用
如果没有adapter层，你需要写4份几乎一样的业务代码，分别处理这4种接入方式；

如果有adapter层，你只需要写**1份业务逻辑**，然后写4个不同的**适配器**，把不同的输入转换成业务层能理解的格式。

下面 `Router` 和 `Handler` 就是**HTTP适配器**，属于 `adapter` 层的一部分。
- `Router` 负责注册HTTP路由，把不同的URL路径映射到对应的Handler
- `Handler` 负责把HTTP请求转换成业务层的DTO，调用业务层，再把结果转换成HTTP响应

如果以后要加gRPC接口，只需要在 `adapter` 目录下新建一个 `grpc` 文件夹，写一个 `OrderGRPCServer`，注入同一个 `OrderService` 即可。
如果以后要加MQ消费者，就新建一个 `mq` 文件夹，写一个 `OrderMQConsumer`，还是注入同一个 `OrderService`。

这就是COLA架构中adapter层的核心价值：**对外屏蔽内部实现，对内屏蔽外部差异**。
### 4.3.1 Handler
Handler 不写核心业务逻辑，它把 HTTP 请求翻译成应用层能理解的参数，再把应用层结果翻译成 HTTP 响应。
比如未来商品列表 Handler 大概应该是：
```go
func (h *ProductHandler) ListProducts(ctx context.Context, c *app.RequestContext) {
	page := parsePage(c)
	size := parseSize(c)
	result, total, err := h.productAppService.ListProducts(ctx, page, size)

	if err != nil {
		c.JSON(consts.StatusInternalServerError, dto.ErrorResponse(...))
		return
	}

	c.JSON(consts.StatusOK, dto.ProductListResponse{
		Items: result,
		Total: total,
	})
}
```
注意，这里 Handler 只取参数、调服务、处理错误、返回 JSON。

它不应该自己判断商品是否可购买，也不应该自己查数据库，更不应该自己拼 x402 支付参数。
### 4.3.2 DTO：Adapter 层的接口合同
`internal/adapter/dto` 里放的是请求和响应对象。目前就俩`request.go`和`response.go`。
这些对象的重点不是业务内部怎么实现，而是对外 API 怎么长。
比如商品列表响应：
```go
type ProductListResponse struct {
	Items []ProductItem `json:"items"`
	Total int64         `json:"total"`
}
```
对于 Merchant Server 来说，Agent 调用接口时看到的不是数据库表，也不是领域对象，而是 DTO 序列化后的 JSON。
所以 DTO 应该放在 Adapter 层附近，而不是到处乱传。
## 4.4 Application 层：一个方法对应一个 Use Case
在`internal/application/service/product_app_service.go`里，核心对象是`ProductAppService`。

Application 层可以理解为“业务流程编排层”。

它不直接处理 HTTP，也不直接写数据库细节，而是负责把一个完整业务动作串起来。
比如商品列表：
```go
// 【架构定位】DDD 应用层（Application Layer）方法，属于"用例编排器"
// 核心职责：
// 1. 参数合法性校验（非业务规则的基础校验）
// 2. 调用基础设施层（仓库）获取数据
// 3. 对象转换：领域对象(DO) → 数据传输对象(DTO)
// 4. 错误包装与返回
// 【设计原则】应用层只做流程编排，不包含核心业务规则
// 【调用链路】Adapter层Handler → 本方法 → 基础设施层Repository
func (s *ProductAppService) ListProducts(ctx context.Context, page, size int) ([]*ProductListItem, int64, error) {
	// 分页参数兜底校验（应用层职责：防止非法参数穿透到数据库）
	// 业务规则：页码必须从1开始，每页条数限制在1-100之间
	if page < 1 {
		page = 1 // 默认第1页
	}
	if size < 1 || size > 100 {
		size = 20 // 默认每页20条，最大100条（防止一次性查询大量数据拖垮数据库）
	}

	// 调用商品仓库查询商品列表和总数
	// 【架构说明】productRepo 是领域层定义的仓库接口，由基础设施层实现
	// 符合 DDD 依赖倒置原则：应用层依赖抽象接口，不依赖具体实现
	products, total, err := s.productRepo.FindAll(ctx, page, size)
	if err != nil {
		// 错误包装：使用 %w 保留原始错误栈，便于上层排查问题
		// 前缀"list products:"标识错误发生的上下文
		return nil, 0, fmt.Errorf("list products: %w", err)
	}

	// 预分配切片容量（Go性能优化最佳实践）
	// 提前知道切片长度，避免动态扩容带来的性能损耗
	items := make([]*ProductListItem, 0, len(products))

	// 领域对象(ProductDO) → 传输对象(ProductListItem DTO) 转换
	// 【架构意义】隔离内部领域模型与外部返回格式
	// 好处：1. 不暴露内部敏感字段 2. 按需裁剪字段 3. 外部格式变化不影响领域层
	for _, p := range products {
		items = append(items, &ProductListItem{
			ID:          p.SKUID,       // 兼容前端字段命名
			SKUID:       p.SKUID,       // 商品唯一SKU编号
			Title:       p.Title,       // 商品标题
			Description: p.Description, // 商品描述
			Price:       p.Price,       // 商品价格（分/最小货币单位）
			Currency:    p.Currency,    // 货币类型（CNY/USD等）
			Author:      p.Author,      // 商品作者/供应商
			Tags:        p.Tags,        // 商品标签数组
			Status:      string(p.Status), // 枚举转字符串，适配前端JSON格式
		})
	}

	// 返回值说明：
	// 1. []*ProductListItem：商品列表DTO（最终返回给前端的数据）
	// 2. int64：符合条件的商品总数（用于前端分页控件计算总页数）
	// 3. error：错误信息，nil表示成功
	return items, total, nil
}
```
> 关键词是编排、调度、Use Case、事务边界、DTO / Entity 转换。
## 4.5 Domain 层：业务核心
当前项目里的 Domain 层在 `internal/domain`，它下面有：
```
entity/
repository/
service/
```
比如商品实体`Product`，它应该关心：
```
商品 ID
商品标题
商品价格
商品状态
商品对应的 SkillDid
商品是否可购买
```
一个典型的领域方法是：
```go
func (p *Product) IsPurchasable() bool {
	return p.Status == ProductStatusActive &&
		p.Price != "" &&
		p.SkillDid != ""
}
```
这段逻辑和 HTTP 没关系，和 SQLite 也没关系，和 Hertz 更没关系。
它表达的是商品本身的业务规则。

所以 Domain 层最好保持纯粹：
- 不 import Hertz
- 不 import SQLite
- 不处理 HTTP 状态码
- 不直接读 config.yaml
它只关心业务概念和业务规则。

这也是为什么 Domain 层可以比较容易做单元测试。测试 `Product.IsPurchasable()` 不需要启动 HTTP 服务，也不需要连数据库。
### 4.5.1 Repository
这是四层结构里比较容易绕的地方。直觉上，Repository 好像是数据库相关，为什么不放到 Infrastructure？
关键在于：
- Domain 层定义“我需要什么能力”
- Infrastructure 层提供“这个能力怎么实现”

ProductRepository 接口只定义能力：
```
FindAll
FindBySKUID
FindByID
Save
UpdateStatus
```
它不说这些能力来自 SQLite、MySQL、Redis 还是内存。

真正的实现放在`internal/infrastructure/persistence/sqlite/product_repo_impl.go`。
这样以后从内存模拟换成 SQLite，再从 SQLite 换成 MySQL，上层可以尽量少改。

这就是依赖倒置最朴素的体现：
- 业务层依赖接口
- 技术层实现接口
而不是业务层直接依赖 SQLite。

## 4.6 Infrastructure 层：所有技术细节
当前项目里的 Infrastructure 层在`internal/infrastructure`，它下面有：
```
client/
persistence/
```
这层负责和外部技术系统打交道。比如：
```
SQLite / MySQL
StablePay Gateway HTTP Client
文件系统
缓存
消息队列
外部 API
```
Infrastructure 层的特点是：
- 它最容易变
- 它最依赖具体技术
- 它不应该污染 Domain 层
比如数据库从 SQLite 换成 MySQL，变的是 Infrastructure。
StablePay Gateway 地址变化，变的是 config 和 client。
但 Product 是否可购买的规则，不应该因此变化。

## 4.7 调用方向
理想调用方向可以这样理解：
```
HTTP 请求
  ↓
Adapter Handler
  ↓
Application Service
  ↓
Domain Service / Entity / Repository Interface
  ↓
Infrastructure Repository Impl / StablePay Client
```
更具体一点：
```
Router
  ↓
HealthHandler / ProductHandler
  ↓
ProductAppService
  ↓
ProductDomainService + ProductRepository
  ↓
ProductRepoImpl / StablePayClient
```
这里要注意一个细节：Infrastructure 层实现了 Domain 层定义的接口，所以从代码依赖上看，Infrastructure 也会 import Domain。

这不是矛盾，而是依赖倒置：
```
Domain 定义规则和接口
Infrastructure 适配技术实现
Application 通过接口使用能力
```
