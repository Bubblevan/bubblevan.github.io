# 9. Go 单元测试
以前我写 Python 比较多，也比较依赖 AI 帮我把代码“写出来”。这种方式最大的问题是：代码看起来像是对的，但我自己没有一套稳定的方法证明它真的对。

我也听说过一种 TDD（Test-Driven Development） 的说法，叫 **测试驱动开发**。
它不是简单地“先写测试后写代码”，更准确地说，它是一种开发节奏：
```
Red：先写一个失败测试
Green：写最少的代码让测试通过
Refactor：在测试保护下重构代码
```
在 Product 例子里：
```
Red：写 TestProductWithoutPriceCannotBePurchased，编译失败或测试失败
Green：给 Product 加 Price 字段，修改 IsPurchasable
Refactor：把重复创建 Product 的代码改成 Builder
```
好处不是让代码“更高级”，而是让我每一步都有反馈。

我不用等整个项目写完、Docker 跑起来、ACK 部署成功，才知道商品规则写错了。

所以这一章的目标不是把 Go 测试讲得很全，而是先建立一套最小工作流：
```
写一个业务愿望
  ↓
写一个最小测试
  ↓
让测试先编译失败
  ↓
补最小实现
  ↓
go test 跑通
  ↓
再加反例测试
  ↓
逼出真正的字段和规则
```
## 9.1 开始测试
### 9.1.1 最小测试
我现在有一个最小愿望：
> 一个上架、有价格、有收款身份的商品，应该可以被购买。
先不要急着设计数据库表。

先不要急着写 Handler。

先不要急着写 SQLite。

先从测试开始。
假设我要测试 `internal/domain/entity/product.go`，那么测试文件就放在同一个目录 `internal/domain/entity/product_test.go`
最开始可以写成这样：
```go
package entity

import "testing"

func TestProductCanBePurchased(t *testing.T) {
    product := ???
    if !product.IsPurchasable() {
        t.Error("一个上架、有价格、有收款身份的商品应该可以购买")
    }
}
```
这段代码一定编译不过，因为：
- Product 还不存在
- product 怎么创建还不知道
- IsPurchasable 方法也不存在

但这就是测试的意义，不是等代码全写完以后才补。测试可以先表达“我希望代码最终能怎么被使用”。

### 9.1.2 为了让测试编译，先写最小 Product
为了让测试编译，我先把 `???` 换成最小结构：
```go
func TestProductCanBePurchased(t *testing.T) {
    product := &Product{}
    if !product.IsPurchasable() {
        t.Error("一个上架、有价格、有收款身份的商品应该可以购买")
    }
}
```
然后创建 `product.go`：
```go
package entity
type Product struct{}
func (p *Product) IsPurchasable() bool {
    return true
}
```
这就是最小实现。
运行`go test ./internal/domain/entity`后：
```bash
ok   stablepay-merchant/internal/domain/entity  0.003s
```
### 9.1.3 现在开始加反例：草稿商品不能购买
如果 `IsPurchasable()` 永远返回 true，那所有商品都可以买，这明显不对。
```go
func TestDraftProductCannotBePurchased(t *testing.T) {
    product := &Product{
        Status: ProductStatusDraft,
    }

    if product.IsPurchasable() {
        t.Error("草稿商品不应该可以购买")
    }
}
```
这时编译又失败，因为还没有 `Status` 和 `ProductStatusDraft`。

于是字段被测试逼出来：
```go
type ProductStatus string
const (
    ProductStatusActive ProductStatus = "active"
    ProductStatusDraft  ProductStatus = "draft"
)
type Product struct {
    Status ProductStatus
}
func (p *Product) IsPurchasable() bool {
    return p.Status == ProductStatusActive
}
```
继续跑`go test ./internal/domain/entity`，这时第一个测试失败，因为第一个 product 是空的，没有 Active 状态。

于是第一个测试也要补成更真实的商品：
```go
func TestProductCanBePurchased(t *testing.T) {
    product := &Product{
        Status: ProductStatusActive,
    }

    if !product.IsPurchasable() {
        t.Error("一个上架、有价格、有收款身份的商品应该可以购买")
    }
}
```
### 9.1.4 再加反例：上架但没有价格，也不能购买
继续写测试：
```go
func TestProductWithoutPriceCannotBePurchased(t *testing.T) {
    product := &Product{
        Status: ProductStatusActive,
    }

    if product.IsPurchasable() {
        t.Error("没有价格的商品不应该可以购买")
    }
}
```
为了让它通过，我需要 `Price`：
```go
type Product struct {
    Status ProductStatus
    Price  string
}

func (p *Product) IsPurchasable() bool {
    return p.Status == ProductStatusActive &&
        p.Price != ""
}
```

再把正例补上：
```go
func TestProductCanBePurchased(t *testing.T) {
    product := &Product{
        Status: ProductStatusActive,
        Price:  "2.00",
    }
    if !product.IsPurchasable() {
        t.Error("一个上架、有价格、有收款身份的商品应该可以购买")
    }
}
```
#### 9.1.5 再加反例：没有 SkillDid，也不能购买
StablePay 的商品不是普通商品，它要和支付验证绑定。

所以仅仅有价格还不够，还要知道支付身份，例如 `SkillDid`
```go 
func TestProductWithoutSkillDidCannotBePurchased(t *testing.T) {
    product := &Product{
        Status: ProductStatusActive,
        Price:  "2.00",
    }

    if product.IsPurchasable() {
        t.Error("没有 SkillDid 的商品不应该可以购买")
    }
}
```

实现变成：
```go
type Product struct {
    Status   ProductStatus
    Price    string
    SkillDid string
}

func (p *Product) IsPurchasable() bool {
    return p.Status == ProductStatusActive &&
        p.Price != "" &&
        p.SkillDid != ""
}
```

正例也补完整：
```go
func TestProductCanBePurchased(t *testing.T) {
    product := &Product{
        Status:   ProductStatusActive,
        Price:    "2.00",
        SkillDid: "did:solana:seller111",
    }

    if !product.IsPurchasable() {
        t.Error("一个上架、有价格、有收款身份的商品应该可以购买")
    }
}
```
再跑 `go test ./internal/domain/entity`。
到这里，最小 Product 规则就长出来了：**能购买 = active + 有价格 + 有 SkillDid**

这就是单元测试最核心的体验：不是一开始把字段都设计好，而是让测试和业务规则一步步把字段逼出来。

## 9.2 `go test`
测试函数通常写在 `_test.go` 文件里，命名为 `TestXxx`，并通过 `go test` 执行。
| 项目 | 内容 |
| ---- | ---- |
| 执行流程 | 1. 编译业务代码 + 测试代码<br>2. 自动运行测试函数 |
| 测试文件规范 | **文件名** 后缀：`_test.go` |
| 测试函数规范 | **函数名** 以 `Test` 开头，入参为 `*testing.T` |
| 常用执行命令 | `go test ./internal/domain/entity`：执行指定包下所有测试 |
| 测试失败标识 | 代码中调用 `t.Error()` / `t.Fatalf()` 即判定测试失败 |

普通 `go test` 输出很少。如果想看每个测试名，可以加 `-v`：

```bash
go test -v ./internal/domain/entity
```
输出类似：
```
=== RUN   TestProductCanBePurchased
--- PASS: TestProductCanBePurchased (0.00s)
=== RUN   TestDraftProductCannotBePurchased
--- PASS: TestDraftProductCannotBePurchased (0.00s)
=== RUN   TestProductWithoutPriceCannotBePurchased
--- PASS: TestProductWithoutPriceCannotBePurchased (0.00s)
=== RUN   TestProductWithoutSkillDidCannotBePurchased
--- PASS: TestProductWithoutSkillDidCannotBePurchased (0.00s)
PASS
ok   stablepay-merchant/internal/domain/entity  0.003s
```

当测试越来越多时，我不想每次都跑全部测试。这个时候加上 `-run` 参数。

比如我只想跑“没有价格不能购买”这个测试：
```bash
go test -v ./internal/domain/entity -run TestProductWithoutPriceCannotBePurchased
```
如果我想跑所有名字里包含 `Product` 的测试：
```bash
go test -v ./internal/domain/entity -run Product
```

在这个项目里，最常用的命令不是很多。

检查整个项目能不能编译：
```bash
go build ./...
```
运行整个项目所有测试：
```bash
go test ./...
```
只测试 Domain 层：
```bash
go test ./internal/domain/...
```
只测试 Entity 包：
```bash
go test ./internal/domain/entity
```
查看详细输出：
```bash
go test -v ./internal/domain/entity
```
只跑某一个测试：
```bash
go test -v ./internal/domain/entity -run TestProductCanBePurchased
```
看覆盖率：
```bash
go test -cover ./internal/domain/...
```
这一组命令够我完成现有的开发。

## 9.3 `go build`
`go build` 则用于编译包和依赖，编译普通包时会忽略 `_test.go` 文件。
| 项目 | 内容 |
| ---- | ---- |
| 核心作用 | 编译代码，校验项目是否可正常构建 |
| 常用命令 | `go build ./...`：从当前模块开始，编译**所有包** |
| 可检查项 | 语法错误、导入错误、类型错误、未使用变量、循环依赖、包路径错误 |
| 注意事项 | 仅做编译校验，**不会执行单元测试** |
| 能力边界 | 仅判断：代码能否编译；无法校验业务逻辑是否正确 |

两者对比：
| 命令 | 编译普通代码 | 编译 `_test.go` | 运行测试 | 主要用途 |
| ---- | :----------: | :-------------: | :------: | -------- |
| `go build ./...` | 是 | 否 | 否 | 全局检查项目能否正常构建 |
| `go test ./...` | 是 | 是 | 是 | 批量执行所有单元测试 |
| `go test -run X` | 是 | 是 | 是（仅运行匹配的测试） | 单独执行指定测试，问题定位 |
| `go test -cover` | 是 | 是 | 是 | 执行测试并查看代码测试覆盖率 |

## 9.4 什么是 table-driven test？
Go 里很常见的一种测试写法叫表驱动测试。

当我发现自己写了很多结构类似的测试：
```go
func TestDraftProductCannotBePurchased(t *testing.T) {}
func TestProductWithoutPriceCannotBePurchased(t *testing.T) {}
func TestProductWithoutSkillDidCannotBePurchased(t *testing.T) {}
```

就可以改成一张测试表。
例如：
```go
func TestProductIsPurchasable(t *testing.T) {
    tests := []struct {
        name    string
        product *Product
        want    bool
    }{
        {
            name: "active product with price and skill did can be purchased",
            product: &Product{
                Status:   ProductStatusActive,
                Price:    "2.00",
                SkillDid: "did:solana:seller111",
            },
            want: true,
        },
        {
            name: "draft product cannot be purchased",
            product: &Product{
                Status:   ProductStatusDraft,
                Price:    "2.00",
                SkillDid: "did:solana:seller111",
            },
            want: false,
        },
        {
            name: "product without price cannot be purchased",
            product: &Product{
                Status:   ProductStatusActive,
                SkillDid: "did:solana:seller111",
            },
            want: false,
        },
        {
            name: "product without skill did cannot be purchased",
            product: &Product{
                Status: ProductStatusActive,
                Price:  "2.00",
            },
            want: false,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := tt.product.IsPurchasable()
            if got != tt.want {
                t.Fatalf("IsPurchasable() = %v, want %v", got, tt.want)
            }
        })
    }
}
```
这里的 `t.Run` 会创建子测试。

运行：
```bash
go test -v ./internal/domain/entity
```
会看到每个 case 的名字。

表驱动测试适合：
- 同一个函数
- 多个输入
- 多个期望输出

比如后面 Money 转换就非常适合：
```
"2.00" -> "2000000"
"0.5" -> "500000"
"0.000001" -> "1"
"0.0000001" -> error
```

### 9.4.1 `t.Error` 和 `t.Fatal` 有什么区别？
常见写法有 `t.Error("failed")` 和 `t.Fatal("failed")`。

区别是：
- t.Error：标记失败，但继续执行当前测试
- t.Fatal：标记失败，并立刻终止当前测试

如果后面的代码依赖前面的结果，就用 `t.Fatal`。
例如：
```go
money, err := NewMoneyFromDecimal("2.00", "USDC")
if err != nil {
    t.Fatalf("unexpected error: %v", err)
}

if money.AmountMinor != "2000000" {
    t.Fatalf("AmountMinor = %s, want 2000000", money.AmountMinor)
}
```

如果 `NewMoneyFromDecimal` 已经失败，后面再检查 `money.AmountMinor` 没意义，所以用 `Fatalf`。

## 9.5 测试文件用同包还是外部包？
Go 测试文件可以写：
```go
package entity
```
也可以写：
```go
package entity_test
```
区别是：
- package entity：测试和被测代码在同一个包，可以访问未导出的内容
- package entity_test：测试站在外部使用者角度，只能访问导出的 API

等 API 稳定后，可以补一部分 `entity_test` 风格的测试，用来模拟外部调用者如何使用这个包。
