# 2. Go 最小语法包
这一章不是完整的 Go 语言教程。

现在的目标不是把 Go 从语法到并发模型全部学完，而是先掌握“能看懂并维护 Merchant Server 这个项目”的最小知识包。因为后端项目里的 Go 代码并不是孤立存在的，它通常和 HTTP 框架、配置加载、分层架构、数据库访问、外部服务调用一起出现。

所以我需要先赶鸭子上架，建立一个够用的 Go 认知框架。

## 2.1 package
Go 没有 Java 那种类优先的组织方式。一个 Go 文件开头一定会声明：
```go
package main
// 或者 package config
```
在当前 Merchant Server 里，目录和 package 基本是一一对应的：
```
cmd/merchant-server      -> main
config                   -> config
internal/adapter         -> adapter
internal/domain/entity   -> entity
internal/domain/repository -> repository
```
所以，理解 Go 项目的第一步，就是理解“包”是代码组织单元。

`cmd/merchant-server/main.go` 是程序入口，`internal/domain/entity/product.go` 是领域实体，`internal/infrastructure/persistence/sqlite/product_repo_impl.go` 是仓储实现。它们不是随便放的，而是通过 package 表达分层职责。

> 可以把 package 理解成一组职责相近的 Go 文件

## 2.2 struct
Go 里没有传统 OOP 里的 class，但有 struct。

比如配置对象：
```go
type Config struct {
    Server ServerConfig
}
```
商品对象：
```go
type Product struct {
    ID          string
    SKUID       string
    Title       string
    Description string
}
```
DTO、Entity、PO、配置对象，本质上都可以用 struct 表达。在这个项目里，需要重点看几类 struct：
- Config：配置结构
- Product：领域实体
- Request DTO：请求参数结构
- Response DTO：响应结构
- Client：外部服务客户端
- RepoImpl：仓储实现
- AppService：应用服务

## 2.3 method
Go 的方法定义方式和 Java、TypeScript 不一样。
它不是这样写到 Struct 里：
```java
class Product {
    isPurchasable() {} 
}
```
而是这样：
```go
func (p *Product) IsPurchasable() bool {
    return true
}
```
`(p *Product)` 叫 receiver，可以理解为“这个方法属于 Product”。
在当前项目里，领域实体、应用服务、仓储实现、Handler 都会大量使用这种写法。
> Java、Python、Typescript都好久没看到过指针，这里重新出现
比如：
```
Product.IsPurchasable()
ProductAppService.ListProducts()
HealthHandler.Healthz()
ProductRepoImpl.FindAll()
```
这类方法是理解项目调用链的关键。

## 2.4 interface
Go 的 interface 非常重要，尤其是在 Repository 模式里。
当前项目里，Domain 层会定义类似这样的接口：
```go
type ProductRepository interface {
    FindAll(ctx context.Context) ([]*Product, error)
    FindBySKUID(ctx context.Context, skuID string) (*Product, error)
}
```
Domain 层只规定“我需要什么能力”，不关心具体是内存、SQLite 还是 MySQL。

Infrastructure 层再去实现这个接口。

这就是 Go 项目里很常见的依赖倒置方式：
```
Domain 定义接口
Infrastructure 实现接口
Application 依赖接口
```
## 2.5 error
Go 不像 Java 那样主要依赖异常，也不像 JavaScript 那样经常 try/catch。

Go 更常见的写法是：
```go
result, err := service.DoSomething(ctx)
if err != nil {
    return nil, err
}
```
这种写法看起来啰嗦，但它的好处是错误路径非常明确。

在当前项目里，数据库查询失败、配置加载失败、Gateway 调用失败、商品不存在、商品不可购买，都应该通过 error 或业务结果显式表达。

我们需要习惯看到大量：
```go
if err != nil {
    return ...
}
```
## 2.6 `context.Context`
Go 后端里几乎所有重要方法都会带上 `ctx context.Context`。比如：
```
FindAll(ctx context.Context)
VerifyPurchase(ctx context.Context)
ListProducts(ctx context.Context)
```
`context.Context` 主要用于传递请求上下文，例如：
- 请求取消
- 超时控制
- 链路追踪信息
- 日志 trace id
- 认证信息

对于当前项目，我先不需要过度展开 context 的内部机制，只需要形成一个习惯：
> 凡是一次请求链路中可能调用数据库、外部 HTTP 服务、RPC 服务的方法，都应该把 ctx 传下去。
这样未来接入超时控制、链路追踪和日志时，项目结构不会推倒重来。
