# 3. CloudWeGo Hertz MVP
Go 语言本身已经提供了原生 HTTP 标准库 `net/http`。这意味着，如果我只是想写一个最小 HTTP 服务，其实完全不需要引入任何第三方框架。

例如，用原生 `net/http` 写一个 `/healthz` 接口，大概是这样：
```go
package main

import (
    "encoding/json"
    "net/http"
)
func main() {
	// 注册路由与处理器函数
	// 含义：监听访问路径 /healthz 的 HTTP 请求，并使用后面的匿名函数处理请求
	http.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		// 设置响应头：指定返回的数据格式为 JSON
		w.Header().Set("Content-Type", "application/json")

		// 创建 JSON 编码器，将 map 字典转为 JSON 格式并写入响应体返回给客户端
		// map[string]any：键为字符串，值可以是任意类型
		json.NewEncoder(w).Encode(map[string]any{
			"status": "ok", // 健康检查返回状态标识
		})
	})

	// 启动 HTTP 服务
	// 第一个参数 ":8787"：监听本机所有网卡的 8787 端口
	// 第二个参数 nil：使用默认的路由分发器
	// 该方法会阻塞运行，一直提供服务
	http.ListenAndServe(":8787", nil)
}
```
运行`go run main.go`然后`curl http://localhost:8787/healthz`即可。

如果要返回 JSON，原生写法也不复杂：
```go
package main

import (
	"encoding/json"
	"net/http"
	"time"
)

type HealthResp struct {
	OK        bool   `json:"ok"`
	Message   string `json:"message"`
	Timestamp string `json:"timestamp"`
}

func main() {
	http.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
        // 组装健康检查响应实体
		resp := HealthResp{
			OK:        true,
			Message:   "service is healthy",
			Timestamp: time.Now().Format(time.RFC3339),
		}
        // 告知客户端本次响应的数据类型为 JSON
		w.Header().Set("Content-Type", "application/json")
        // http.StatusOK 对应标准 200 状态码，表示请求处理成功
		w.WriteHeader(http.StatusOK)
        // 序列化结构体为 JSON 并写入响应流，返回给客户端
		json.NewEncoder(w).Encode(resp)
	})

	http.ListenAndServe(":8080", nil)
}
```
所以问题来了：既然 Go 原生 HTTP 已经够用，为什么 Merchant Server 还要用 CloudWeGo Hertz？

答案不是“原生不好”，而是“项目目标不同”。

如果只是写一个 demo，`net/http` 完全可以。

但如果我要写一个未来会上云、会接支付、会接 K8s、会有中间件、会有统一错误处理、会给 Agent 和其他服务调用的商家后端，那么引入一个成熟 Web 框架会更合适。

## 3.1 原生 net/http 适合什么场景？
如果我的目标只是：
- 启动一个端口
- 注册一个 /healthz
- 返回一段 JSON
那原生库完全没问题。

但 Merchant Server 不只是一个健康检查服务。它后面至少要有：
```
商品列表接口
商品详情接口
商品执行购买接口
x402 402 响应
统一错误响应
参数绑定和校验
中间件
日志
跨域
请求追踪
Gateway Client 调用
K8s 健康检查
```
这些能力如果全部用原生 `net/http` 手写，当然也能做，但会逐渐变成大量重复代码。

比如原生处理路径参数就不够自然。假设我想写`/api/v1/products/:sku_id`，原生 net/http 里最朴素的写法可能是：
```go
func main() {
	// 注册路由：匹配 /api/v1/products/ 开头的请求，使用匿名函数处理请求
	http.HandleFunc("/api/v1/products/", func(w http.ResponseWriter, r *http.Request) {
		// 截取 URL 路径，去掉前缀 /api/v1/products/，剩余部分即为 skuID
		skuID := strings.TrimPrefix(r.URL.Path, "/api/v1/products/")

		// 判断截取后结果是否为空（未传递商品SKU编号）
		if skuID == "" {
			// 返回 400 错误响应：提示缺少 sku_id 参数
			// http.StatusBadRequest 对应 HTTP 400 状态码（请求参数非法）
			http.Error(w, "missing sku_id", http.StatusBadRequest)
			return // 终止当前处理函数，不再向下执行
		}
		// 拼接字符串并写入响应体，返回给客户端
		fmt.Fprintf(w, "product sku_id = %s", skuID)
	})
	http.ListenAndServe(":8080", nil)
}
```
这能跑，但可读性一般，而且后续如果出现更复杂的路由，例如：
- `/api/v1/products/:sku_id/execute`
- `/api/v1/merchants/:merchant_id/products/:sku_id`
手写字符串解析就会越来越难维护。

再比如 **中间件**。原生当然可以通过包装 `http.Handler` 实现，但每个项目都要自己组织一套：
```go
// logging 日志中间件函数
// 入参 next: 被包装的下一个 HTTP 处理器
// 出参: 包装后的新 HTTP 处理器
func logging(next http.Handler) http.Handler {
	// 返回一个匿名 Handler 函数，实现请求拦截与日志打印
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 记录请求开始的时间点
		start := time.Now()
		// 执行原本的请求处理逻辑（调用下一个处理器）
		next.ServeHTTP(w, r)
		// 请求处理完成后，打印日志：请求方法、请求路径、接口耗时
		fmt.Println(r.Method, r.URL.Path, time.Since(start))
	})
}
```
这能帮助理解中间件本质，但如果每个服务都自己写一套日志、鉴权、错误恢复、跨域、限流，就会偏离业务目标。
## 3.2 Hertz 提供了更适合业务开发的抽象
CloudWeGo Hertz 是一个 Go HTTP 框架。对于 Merchant Server 来说，它主要提供了几类更方便的能力。
```go
package main

import (
	// Go 标准库上下文：用于传递请求生命周期的控制信息、超时、取消信号等
	"context"

	// Hertz 框架的应用上下文包：封装了 HTTP 请求和响应的所有操作
	"github.com/cloudwego/hertz/pkg/app"
	// Hertz 框架的服务器包：用于创建和配置 HTTP 服务器
	"github.com/cloudwego/hertz/pkg/app/server"
	// Hertz 框架的常量包：包含 HTTP 状态码、请求方法等通用常量
	"github.com/cloudwego/hertz/pkg/protocol/consts"
)
func main() {
	// 1. 创建默认配置的 Hertz 服务器实例
	// server.WithHostPorts("127.0.0.1:8080")：指定服务器监听的地址和端口
	// 这里只监听本机 127.0.0.1 的 8080 端口，外网无法访问
	// 如果想允许外网访问，写成 ":8080" 即可（等价于 "0.0.0.0:8080"）
	h := server.Default(server.WithHostPorts("127.0.0.1:8080"))

	// 2. 注册 GET 路由
	// 第一个参数 "/ping"：路由路径
	// 第二个参数：该路由的请求处理函数
	h.GET("/ping", func(ctx context.Context, c *app.RequestContext) {
		// ctx：标准上下文，用于传递请求生命周期的控制信号
		// c：Hertz 专属请求上下文，包含所有请求和响应的操作方法

		// 返回字符串类型的响应
		// 第一个参数：HTTP 状态码，consts.StatusOK 等价于 200
		// 第二个参数：响应内容
		c.String(consts.StatusOK, "pong")
	})

	// 3. 启动 HTTP 服务器并开始监听请求
	// Spin() 是阻塞方法，会一直运行直到程序退出
	// 等价于标准库的 http.ListenAndServe()
	h.Spin()
}
```
和原生版本相比，代码变化不大，但有几个明显不同点：
```
server.Default(...) 创建 Hertz Server
h.GET(...) 注册 GET 路由
RequestContext 统一处理请求上下文
c.String(...) 统一返回响应
h.Spin() 启动服务
```
> 它给我的第一印象很像 Gin，有咩有觉得，但属于 CloudWeGo 生态。
再写一个 Hertz 版本的 `/healthz`：
```go
package main
import (
	"context"
	"time"
	"github.com/cloudwego/hertz/pkg/app"
	"github.com/cloudwego/hertz/pkg/app/server"
	"github.com/cloudwego/hertz/pkg/protocol/consts"
)
type HealthResp struct {
	OK        bool   `json:"ok"`
	Message   string `json:"message"`
	Timestamp string `json:"timestamp"`
}

func main() {
	h := server.Default(server.WithHostPorts("127.0.0.1:8080"))

	// 对比标准库：等价于 http.HandleFunc("/healthz", handler)
	h.GET("/healthz", func(ctx context.Context, c *app.RequestContext) {
		// ctx：标准上下文，用于跨函数传递请求生命周期信息
		// c：Hertz专属请求上下文，所有请求/响应操作都通过它完成

		resp := HealthResp{
			OK:        true,                              // 标记服务正常运行
			Message:   "service is healthy",              // 状态说明
			Timestamp: time.Now().Format(time.RFC3339),  // 格式化当前时间为RFC3339标准
		}

		// 直接返回JSON响应（Hertz核心快捷方法）
		// 对比标准库：自动完成了以下3件事
		// 1) w.Header().Set("Content-Type", "application/json")
		// 2) w.WriteHeader(consts.StatusOK)
		// 3) json.NewEncoder(w).Encode(resp)
		c.JSON(consts.StatusOK, resp)
	})

	h.Spin()
}
```
Hertz 这里的优势不是少写了多少代码，而是让我从一开始就按框架推荐的方式处理请求和响应。

在原生 `net/http` 里，我要自己写：
```go
w.Header().Set("Content-Type", "application/json")
w.WriteHeader(http.StatusOK)
json.NewEncoder(w).Encode(resp)
```
在 Hertz 里则是：
```go
c.JSON(consts.StatusOK, resp)
```
这对于大型项目很重要，因为统一风格能减少很多低级错误。

## 3.3 Hertz 路由组
当前 Merchant Server 后续会有这些接口：
```
GET /healthz
GET /api/v1/products
GET /api/v1/products/:id
GET /api/v1/products/:id/execute
```
这类接口天然适合分组：
```go
func main() {
	h := server.Default(server.WithHostPorts("127.0.0.1:8080"))
	// 1. 注册根级路由：健康检查接口
	// 访问地址：http://127.0.0.1:8080/healthz
	h.GET("/healthz", healthz)

	// 2. 创建路由分组：所有以 /api/v1 开头的路由都归到这个组
	// 好处：统一前缀、统一加中间件、代码结构清晰
	v1 := h.Group("/api/v1")
	{
		// 注意：这里的大括号只是代码格式化用的，不是语法必须
		// 但强烈推荐这样写，让路由层级一目了然

		// 分组内路由自动拼接前缀：实际完整路径 = /api/v1 + /products
		v1.GET("/products", listProducts) // 完整路径：/api/v1/products

		// 【核心】路径参数路由：:id 表示这是一个动态参数
		// 匹配所有 /api/v1/products/xxx 格式的请求，xxx 会被解析为 id 参数
		v1.GET("/products/:id", getProduct) // 完整路径：/api/v1/products/:id

		// 路径参数可以和固定路径组合
		v1.GET("/products/:id/execute", executeProduct) // 完整路径：/api/v1/products/:id/execute
	}
	h.Spin()
}
```
这里有两个好处。
- 第一，路径结构更清晰：
    - 运维接口：/healthz
    - 业务接口：/api/v1/...
- 第二，后面可以很自然地在 `/api/v1` 这个分组上挂中间件。
    - 比如未来我可能要给业务 API 增加日志、API Key 校验、限流，但 `/healthz` 不一定需要同样的逻辑。
    - 路由分组可以让这种需求更自然地落地。
```go
// 日志中间件（和之前学的标准库中间件逻辑一样）
func logging() app.HandlerFunc {
	return func(ctx context.Context, c *app.RequestContext) {
		start := time.Now()
		c.Next(ctx) // 执行后续路由逻辑
		fmt.Println(c.Method(), c.Path(), time.Since(start))
	}
}
// 创建分组时直接加上中间件
v1 := h.Group("/api/v1", logging())
```

## 3.4 `main.go`
当前项目的启动入口是`cmd/merchant-server/main.go`，它不是直接在 `main()` 里写一堆业务逻辑，而是做“依赖组装”，把各层对象按顺序创建出来：
1. config.Load("") 加载配置
2. sqlite.NewProductRepo() 创建商品仓储
3. productRepo.Seed(...) 写入种子商品
4. client.NewStablePayClient(...) 创建 Gateway 客户端
5. domainSvc.NewProductDomainService(...) 创建领域服务
6. appSvc.NewProductAppService(...) 创建应用服务
7. server.Default(...) 创建 Hertz HTTP Server
8. handler.NewHealthHandler(...) 创建 Handler
9. adapter.NewRouter(...) 注册路由
10. h.Spin() 启动服务

