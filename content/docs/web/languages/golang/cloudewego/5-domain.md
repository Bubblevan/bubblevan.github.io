# 5. Domain 层：从 Product 实体开始，把商品业务规则真正写进去

前面几章已经讲过：这个 Merchant Server 采用类似 COLA 的四层结构。Adapter 层处理 HTTP，Application 层编排 Use Case，Infrastructure 层负责数据库和外部服务，而 Domain 层负责表达最核心的业务规则。

现在我要真正开始补 Domain 层。​当前项目里的 domain 层主要有三个目录：​
- internal/domain/entity
- internal/domain/repository
- internal/domain/service
它们分别对应：​
- entity：领域实体，比如 Product
- repository：仓储接口，比如 ProductRepository
- service：领域服务，比如 ProductDomainService

如果 Domain 层不把这些规则收住，后面就会被迫写到 Handler 或 Application Service 里，代码会越来越乱。​
所以本章目标是：​
1. 完善 Product 实体；
2. 引入 Money 值对象，解决 USDC 金额转换；
3. 完善 ProductDomainService 的购买校验和 proof 签名；
4. 按 x402 v2 新格式定义 PaymentRequired；
5. 给 Domain 层补最小测试，证明它不是 vibe coding。

## 5.1 Why First？
从业务流程看，Agent 购买商品大致是：
```
Agent 请求商品执行接口
  ↓
商户后端查询 Product
  ↓
判断 Product 是否可购买
  ↓
把商品价格转成 USDC minor units
  ↓
生成 x402 Payment Required
  ↓
Agent 支付后重试
  ↓
商户后端验证支付并返回内容
```
这里面有几个规则明显不应该写在 Handler 里：
- 商品什么状态可以购买？
- 价格字符串如何安全转成 minor units？
- USDC 有几位小数？
- x402 v2 PaymentRequired 应该长什么样？
- proof 签名如何生成？
Handler 应该只是 HTTP 翻译器。Application Service 负责编排流程。真正的规则应该往 Domain 层沉。

所以我先改 Domain，而不是先写 /api/v1/products Handler。
## 5.2 逻辑大纲
### 5.2.1 Entity
以`entity/product.go`为例逐段讲解一下：
#### 5.2.1.1 版权与包声明
```go
package entity
import "time"
```
包名 entity 是 COLA 架构的标准命名，专门存放领域实体
#### 5.2.1.2 领域错误定义
```go
var (
	ErrInvalidProduct        = errors.New("invalid product")
	ErrProductNotFound       = errors.New("product not found")
	ErrProductNotPurchasable = errors.New("product is not purchasable")
)
```
这是领域层的标准做法：所有业务相关的错误都在领域层提前定义，而不是在 Service 层零散创建。

上层（应用层 / 适配器层）可以通过 errors.Is() 统一判断错误类型，返回对应的 HTTP 状态码。
#### 5.2.1.3 状态枚举定义
```go
type ProductStatus string

const (
	ProductStatusActive   ProductStatus = "active"   // 上架，可购买
	ProductStatusInactive ProductStatus = "inactive" // 下架，不可购买
	ProductStatusDraft    ProductStatus = "draft"    // 草稿，不可购买
)
```
1. **类型安全**：用自定义类型 ProductStatus 代替普通 string，防止传入任意字符串作为状态
2. **可读性优先**：使用 string 而不是 int 作为枚举值，数据库里直接存 "active"，不需要额外映射
3. **生命周期清晰**：完整定义了商品从创建到下架的所有状态，所有和状态相关的业务规则都围绕这三个值展开
#### 5.2.1.4 Product 领域实体结构体
```go
// Product is the product domain entity.
//
// It is intentionally not a database PO and not an API DTO. Product captures the
// merchant-side business meaning of an item that an Agent may purchase.
type Product struct {
	// ID is the internal persistence ID. It is not exposed as the public product ID.
	ID int64 `json:"-"`

	// SKUID is the stable public product identifier used in URLs and x402 resources.
	SKUID string `json:"sku_id"`

	Title       string        `json:"title"`
	Description string        `json:"description"`
	Price       string        `json:"price"`
	Currency    string        `json:"currency"`
	Author      string        `json:"author,omitempty"`
	Tags        []string      `json:"tags,omitempty"`
	Status      ProductStatus `json:"status"`

	// SkillDid binds this merchant product to the StablePay payment identity.
	// In the current Solana MVP it is commonly did:solana:<seller_pubkey>.
	SkillDid string `json:"skill_did,omitempty"`

	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}
```
| 字段 | 业务意义 | 设计要点 |
|------|----------|----------|
| `ID int64 \`json:"-"`` | 数据库自增主键 | 对外隐藏（`json:"-"`），仅内部使用，实现内外ID解耦 |
| `SKUID string` | 对外唯一业务标识 | 所有外部系统（前端、URL、支付系统）都用SKUID识别商品 |
| `Price string` | 商品价格 | 不用float64，避免金融场景的浮点数精度问题 |
| `Currency string` | 货币类型 | 支持多币种支付，这里默认是USDC稳定币 |
| `Status ProductStatus` | 商品生命周期状态 | 用枚举保证类型安全 |
| `SkillDid string` | 支付身份标识 | 绑定卖家的Solana钱包地址，用于收款 |
| `CreatedAt/UpdatedAt` | 时间戳 | 由领域层维护，不由数据库自动生成 |

#### 5.2.1.5 核心业务方法
这是领域实体和数据库PO最本质的区别，**所有和商品相关的业务规则都内聚在这里**，而不是散落在各个Service中。

从下面开始散落的`func`多了起来。如果说 Python 用 class 把所有属性和方法嵌套缩进在一个块里，那么因为 Go 没有 class 关键字，它用 **结构体存属性** + **独立方法绑定** 的方式实现面向对象。

Go 的 `func (p *Product) Xxx()` 完全等价于 Python 的 `def Xxx(self)`:
- Go 的 (p *Product) 接收器 = Python 的 self
- 所有带 (p *Product) 的方法，逻辑上都属于 Product 这个 "类"
- 只是 Go 没有把它们缩进在结构体的大括号里而已
##### 可购买性校验
```go
// IsPurchasable returns whether the product can enter the payment flow.
func (p *Product) IsPurchasable() bool {
	return p != nil && p.ValidatePurchasable() == nil
}

// ValidatePurchasable checks the core invariant before building x402 payment requirements.
func (p *Product) ValidatePurchasable() error {
	if p == nil {
		return ErrProductNotFound
	}
	if err := p.ValidateBasic(); err != nil {
		return fmt.Errorf("%w: %v", ErrProductNotPurchasable, err)
	}
	if p.Status != ProductStatusActive {
		return fmt.Errorf("%w: status=%s", ErrProductNotPurchasable, p.Status)
	}
	if strings.TrimSpace(p.SkillDid) == "" {
		return fmt.Errorf("%w: skill_did is required", ErrProductNotPurchasable)
	}
	if _, err := p.PriceMoney(); err != nil {
		return fmt.Errorf("%w: %v", ErrProductNotPurchasable, err)
	}
	return nil
}
```
- **职责拆分**：
  - `IsPurchasable()`：快速判断，返回bool，用于前端展示"购买按钮"等场景
  - `ValidatePurchasable()`：详细校验，返回错误信息，用于支付流程的严格校验
- **业务不变量**：明确了商品可购买的5个必要条件：
  1. 商品存在
  2. 基础字段合法
  3. 状态为"上架"
  4. 已绑定支付身份（SkillDid）
  5. 价格合法
- **错误包装**：用 `%w` 保留原始错误，上层可以通过 `errors.Is(err, ErrProductNotPurchasable)` 判断错误类型
##### 基础字段校验
```go
// ValidateBasic checks fields needed for storing or displaying a product.
func (p *Product) ValidateBasic() error {
	if p == nil {
		return ErrProductNotFound
	}
	if strings.TrimSpace(p.SKUID) == "" {
		return fmt.Errorf("%w: sku_id is required", ErrInvalidProduct)
	}
	if strings.TrimSpace(p.Title) == "" {
		return fmt.Errorf("%w: title is required", ErrInvalidProduct)
	}
	if strings.TrimSpace(p.Price) == "" {
		return fmt.Errorf("%w: price is required", ErrInvalidProduct)
	}
	if strings.TrimSpace(p.Currency) == "" {
		return fmt.Errorf("%w: currency is required", ErrInvalidProduct)
	}
	if !IsValidProductStatus(p.Status) {
		return fmt.Errorf("%w: unsupported status=%s", ErrInvalidProduct, p.Status)
	}
	return nil
}
```
- **通用校验**：所有场景（创建、更新、展示）都需要执行的基础字段校验
- **防御性编程**：自动Trim空格，防止用户输入的空白字符导致校验失败
- **复用性**：Builder模式的`Build()`方法会调用这个校验，保证创建出来的实体始终合法
##### 价格处理方法
```go
// PriceMoney returns a Money value object for this product price.
func (p *Product) PriceMoney() (Money, error) {
	if p == nil {
		return Money{}, ErrProductNotFound
	}
	return NewMoneyFromDecimal(p.Price, p.Currency)
}

// GetPriceMinorUnits returns the product price in minor units.
//
// This method keeps backward compatibility with the existing Application layer.
// New code should prefer PriceMoney() when it needs explicit error handling.
func (p *Product) GetPriceMinorUnits() string {
	money, err := p.PriceMoney()
	if err != nil {
		return "0"
	}
	return money.AmountMinor
}
```
- **值对象模式**：引入`Money`值对象处理金额，封装了金额解析、单位转换、货币校验等逻辑
- **向后兼容**：`GetPriceMinorUnits()` 保留旧接口，避免改动上层应用层代码
- **最佳实践**：新代码优先使用`PriceMoney()`，因为它有明确的错误处理，不会静默失败

#### 5.2.1.6 状态变更方法
```go
// Activate marks the product as active.
func (p *Product) Activate() {
	p.Status = ProductStatusActive
	p.touch()
}

// Deactivate marks the product as inactive.
func (p *Product) Deactivate() {
	p.Status = ProductStatusInactive
	p.touch()
}

// MarkDraft marks the product as draft.
func (p *Product) MarkDraft() {
	p.Status = ProductStatusDraft
	p.touch()
}

func (p *Product) touch() {
	p.UpdatedAt = time.Now()
}
```
这是**充血模型的经典体现**：把状态变更封装成方法，而不是直接修改`Status`字段。
- 好处1：自动更新`UpdatedAt`时间戳，不需要上层手动调用
- 好处2：以后可以在这些方法里添加业务规则（比如"草稿状态不能直接变成下架"）
- 好处3：所有状态变更都有统一的入口，便于排查问题

#### 5.2.1.7 Builder模式（实体创建器）
这是**创建复杂领域实体的标准方式**，解决了构造函数参数过多、可读性差的问题。
##### Builder定义与默认值
```go
// ProductBuilder helps construct Product while keeping defaults in one place.
type ProductBuilder struct {
	product *Product
}

// NewProductBuilder creates a product builder with safe MVP defaults.
func NewProductBuilder() *ProductBuilder {
	now := time.Now()
	return &ProductBuilder{
		product: &Product{
			Status:    ProductStatusDraft,
			Currency:  CurrencyUSDC,
			CreatedAt: now,
			UpdatedAt: now,
		},
	}
}
```
- **默认值集中管理**：所有默认值都在`NewProductBuilder()`中设置，避免分散在代码各处
- **安全默认值**：新建商品默认是"草稿"状态，默认货币是USDC，自动设置创建和更新时间
##### 链式设置方法
```go
func (b *ProductBuilder) WithSKUID(skuID string) *ProductBuilder {
	b.product.SKUID = strings.TrimSpace(skuID)
	return b
}

// ... 省略其他Withxxx方法 ...

func (b *ProductBuilder) WithSellerAddress(sellerAddress string) *ProductBuilder {
	b.product.SkillDid = "did:solana:" + strings.TrimSpace(sellerAddress)
	return b
}
```
- **链式调用**：每个`WithXxx`方法都返回Builder自身，支持链式调用
- **自动数据清洗**：所有字符串字段自动Trim空格，防止无效输入
- **业务封装**：`WithSellerAddress()`自动生成`SkillDid`，上层不需要关心DID的格式

##### 构建方法
```go
// Build constructs and validates a product entity.
func (b *ProductBuilder) Build() (*Product, error) {
	if err := b.product.ValidateBasic(); err != nil {
		return nil, err
	}
	return b.product, nil
}

// MustBuild constructs a product and panics on invalid input.
// Use it only for seed data and tests.
func (b *ProductBuilder) MustBuild() *Product {
	p, err := b.Build()
	if err != nil {
		panic(err)
	}
	return p
}
```
- **`Build()`**：生产环境使用，返回错误，由上层处理
- **`MustBuild()`**：测试和种子数据使用，失败直接panic，简化代码
- **强制校验**：构建时自动调用`ValidateBasic()`，保证创建出来的实体始终合法
### 5.2.2 Service
- **实体（Entity）**：负责单个对象自身的行为（如商品的上架、下架、可购买性判断）
- **领域服务（Domain Service）**：负责**跨多个实体的协调逻辑**、**无状态的领域计算**、**生成领域级别的结果对象**
- 两者都不包含任何技术相关代码（如HTTP、数据库操作）
后面以`service/product_domain_service.go`为例进行讲解：
#### 5.2.2.1 领域服务结构体与构造函数
```go
// ProductDomainService contains product-related domain logic.
type ProductDomainService struct {
	repo repository.ProductRepository
}

// NewProductDomainService creates a product domain service.
func NewProductDomainService(repo repository.ProductRepository) *ProductDomainService {
	return &ProductDomainService{repo: repo}
}
```
1. **依赖注入**：
   - 通过构造函数注入`ProductRepository`接口，而不是在服务内部创建具体实现
   - 好处：解耦服务与仓库的具体实现，便于单元测试（可以注入Mock仓库）
2. **无状态设计**：
   - 领域服务是无状态的，所有状态都保存在实体或仓库中
   - 可以被多个线程安全地并发调用
#### 5.2.2.2 领域业务方法
##### 可购买性校验（跨实体扩展点）
```go
// CanPurchase checks whether a product can enter the x402 payment flow.
func (s *ProductDomainService) CanPurchase(product *entity.Product) error {
	if product == nil {
		return entity.ErrProductNotFound
	}
	return product.ValidatePurchasable()
}
```
- **为什么不直接在应用层调用`product.ValidatePurchasable()`？**
  - 这是一个**预留扩展点**：如果未来可购买性判断需要依赖其他实体（比如用户的购买权限、商品库存、用户余额），只需要修改这个方法，不需要改动应用层代码
  - 示例：以后添加库存校验时，代码会变成：
    ```go
    func (s *ProductDomainService) CanPurchase(product *entity.Product, user *entity.User) error {
        if product == nil {
            return entity.ErrProductNotFound
        }
        if err := product.ValidatePurchasable(); err != nil {
            return err
        }
        // 新增：校验库存
        if err := s.repo.CheckStock(product.SKUID); err != nil {
            return err
        }
        // 新增：校验用户购买权限
        if err := user.CanPurchase(product); err != nil {
            return err
        }
        return nil
    }
    ```
- 现在它只是转发实体的方法，但已经把"可购买性判断"这个业务概念抽象成了领域服务的一个方法，未来扩展不会破坏上层代码
##### 向后兼容的金额转换方法
```go
// UsdcToMinorUnits converts a USDC decimal string to minor units.
// This method keeps backward compatibility with the current Application layer.
// New code should call entity.NewMoneyFromDecimal for explicit error handling.
func (s *ProductDomainService) UsdcToMinorUnits(amount string) string {
	minor, err := entity.DecimalToMinorUnits(amount, entity.USDCDecimals)
	if err != nil {
		return "0"
	}
	return minor
}
```
#### 5.2.2.3 领域值对象定义
```go
// PurchaseProof is a domain-level proof issued after the merchant verifies access.
type PurchaseProof struct {
	ProofVersion string `json:"proof_version"`
	ProofID      string `json:"proof_id"`
	AgentDID     string `json:"agent_did"`
	ProductID    string `json:"product_id"`
	IssuedAt     string `json:"issued_at"`
	Signature    string `json:"signature"`
}
```
- **值对象（Value Object）**：
  - 没有唯一标识，所有字段共同决定对象的身份
  - 不可变：创建后不能修改字段
  - 代表业务领域中的一个"描述性概念"，而不是一个"实体"
- **业务意义**：
  - 代表用户购买商品后获得的访问凭证
  - 包含了凭证的所有必要信息：版本、唯一ID、用户DID、商品ID、签发时间、防篡改签名
#### 5.2.3.4 核心领域逻辑：构建签名购买凭证
```go
// BuildSignedProof builds an HMAC-SHA256 proof for purchased content access.
func (s *ProductDomainService) BuildSignedProof(agentDID, productID, proofSecret string) (*PurchaseProof, error) {
	// 1. 参数清洗与校验
	agentDID = strings.TrimSpace(agentDID)
	productID = strings.TrimSpace(productID)
	proofSecret = strings.TrimSpace(proofSecret)
	if agentDID == "" {
		return nil, fmt.Errorf("build proof: agent_did is required")
	}
	if productID == "" {
		return nil, fmt.Errorf("build proof: product_id is required")
	}
	if proofSecret == "" {
		return nil, fmt.Errorf("build proof: proof secret is required")
	}

	// 2. 生成凭证元数据
	issuedAt := time.Now().UTC().Format(time.RFC3339) // UTC时间，避免时区问题
	proofID := fmt.Sprintf("proof_%s_%d", productID, time.Now().UnixMilli()) // 唯一凭证ID

	// 3. 构建待签名消息（固定顺序，用|分隔）
	message := strings.Join([]string{"v1", proofID, agentDID, productID, issuedAt}, "|")

	// 4. HMAC-SHA256签名（防篡改）
	mac := hmac.New(sha256.New, []byte(proofSecret))
	_, _ = mac.Write([]byte(message))
	signature := hex.EncodeToString(mac.Sum(nil))

	// 5. 返回不可变的凭证值对象
	return &PurchaseProof{
		ProofVersion: "v1",
		ProofID:      proofID,
		AgentDID:     agentDID,
		ProductID:    productID,
		IssuedAt:     issuedAt,
		Signature:    signature,
	}, nil
}
```
1. **参数清洗与校验**：
   - 自动Trim所有字符串参数，防止空白字符导致的签名不一致
   - 校验必填参数，返回明确的错误信息

2. **时间处理**：
   - 使用`UTC()`统一时间，避免不同服务器时区不同导致的签名验证失败
   - 使用`time.RFC3339`标准格式，跨平台解析兼容性最好

3. **唯一ID生成**：
   - 格式：`proof_<商品ID>_<毫秒级时间戳>`
   - 保证每个凭证都有唯一的ID，便于追踪和管理

4. **签名机制**：
   - 算法：HMAC-SHA256，业界标准的消息认证码算法
   - 作用：防止凭证被篡改——任何人修改凭证的任何字段，都会导致签名验证失败
   - 签名内容：包含所有关键信息（版本、ID、用户DID、商品ID、签发时间），确保整个凭证的完整性

5. **返回值**：
   - 返回不可变的`PurchaseProof`值对象，上层不能修改其字段
   - 错误返回明确，便于上层处理
#### 5.2.3.5 向后兼容的旧API
```go
// BuildProof keeps the old map-based API for the current Application layer.
func (s *ProductDomainService) BuildProof(agentDID, productID, proofSecret string) map[string]interface{} {
	proof, err := s.BuildSignedProof(agentDID, productID, proofSecret)
	if err != nil {
		return map[string]interface{}{
			"proof_version": "v1",
			"agent_did":     agentDID,
			"product_id":    productID,
			"issued_at":     time.Now().UTC().Format(time.RFC3339),
			"signature":     "",
			"error":         err.Error(),
		}
	}
	return map[string]interface{}{
		"proof_version": proof.ProofVersion,
		"proof_id":      proof.ProofID,
		"agent_did":     proof.AgentDID,
		"product_id":    proof.ProductID,
		"issued_at":     proof.IssuedAt,
		"signature":     proof.Signature,
	}
}
```
- **旧API兼容设计**：
  - 应用层原来使用的是map格式的返回值，为了不破坏现有代码，保留了这个方法
  - 内部调用新的`BuildSignedProof`方法，然后转换成map格式
  - 错误处理也保持了旧API的风格（在map中返回error字段）
- **演进式重构**：
  - 先添加新的、更好的API（返回强类型的`PurchaseProof`）
  - 保留旧API，标记为兼容用途
  - 逐步引导应用层代码迁移到新API
  - 未来所有旧代码都迁移后，可以删除这个方法

#### 5.2.3.6 设计原则总结
1. **无状态**：领域服务不保存任何业务状态，所有状态都由实体或仓库管理
2. **单一职责**：一个领域服务只负责一个业务领域的逻辑（如`ProductDomainService`只负责商品相关的领域逻辑）
3. **依赖抽象**：只依赖领域层的接口，不依赖具体实现
4. **业务内聚**：所有核心业务逻辑都应该放在领域层（实体或领域服务），而不是应用层
5. **向后兼容**：代码演进时，尽量保留旧API，避免破坏现有代码

| 对比项 | 领域服务（Domain Service） | 应用服务（Application Service） |
|--------|---------------------------|---------------------------------|
| **职责** | 包含核心业务逻辑、跨实体协调 | 流程编排、事务控制、对象转换 |
| **依赖** | 只依赖领域层接口 | 依赖领域层的实体和服务 |
| **粒度** | 细粒度，对应单个业务动作 | 粗粒度，对应一个完整用例 |
| **可复用性** | 可被多个应用服务复用 | 每个用例对应一个应用服务方法 |
### 5.2.3 Respository
`repository` 包就是**数据存取的“业务接口契约”**：
告诉整个系统「商品数据需要哪些增删改查能力」，但**完全不关心数据存在哪里、怎么存**，是 DDD 分层里解耦「业务」和「存储」最关键的一层。
```go
// ProductRepository is the storage contract for Product entities.
type ProductRepository interface {
	// FindAll returns paginated purchasable/listable products and total count.
	FindAll(ctx context.Context, page, size int) ([]*entity.Product, int64, error)

	// FindBySKUID returns a product by public SKU ID.
	FindBySKUID(ctx context.Context, skuID string) (*entity.Product, error)

	// FindByID returns a product by internal persistence ID.
	FindByID(ctx context.Context, id int64) (*entity.Product, error)

	// Save persists a new or existing product.
	Save(ctx context.Context, product *entity.Product) error

	// UpdateStatus changes product lifecycle state.
	UpdateStatus(ctx context.Context, id int64, status entity.ProductStatus) error
}
```
接口只定义方法签名（方法名、入参、出参），没有实现逻辑。
所有方法第一个参数都是 ctx context.Context：
- Go 服务标准规范，用于传递请求上下文、链路追踪、超时控制、请求取消。
- 整个调用链（Handler → AppService → DomainService → Repository）上下文透传。
对于上层（Application Service/Domain Service）调用，依赖于 `ProductRepository` 接口注入：
```go
type ProductAppService struct {
	repo repository.ProductRepository // 依赖接口，不是具体 MySQL 实现
}
```
对于基础设施层，伪代码类似：
```go
// infra/repo/mysql/product_repo.go
type MySQLProductRepo struct {
	db *gorm.DB
}

// 实现 repository.ProductRepository 所有方法
func (m *MySQLProductRepo) FindAll(ctx context.Context, page, size int) ([]*entity.Product, int64, error) {
    // 执行 SQL 查询，组装并返回 []*entity.Product
}

// 其余 FindBySKUID / FindByID / Save / UpdateStatus 全部实现
```
### 5.2.4 单元测试
所有层都应该写单元测试，这里以 Domain 层为例。
所有 Go 单元测试都必须遵守这三个规则：
1. **文件名**：必须以 `_test.go` 结尾（比如 `product_domain_service_test.go`）
2. **函数名**：必须以 `Test` 开头，后跟大写字母（比如 `TestBuildPaymentRequiredV2`）
3. **参数**：必须只有一个参数 `t *testing.T`，用于控制测试流程、断言结果
```bash
# 运行当前目录及所有子目录下的所有单元测试
go test ./...
```
#### 5.2.4.1 第一个测试用例
这个测试是整个文件的核心，测试 **构建 x402 协议标准的支付要求** 功能，这是 StablePay 支付流程的第一步。
```go
func TestBuildPaymentRequiredV2(t *testing.T) {
	// 1. 准备测试数据：创建一个合法的商品领域实体
	// 用之前学的 Builder 模式快速构建测试用的商品
	product := entity.NewProductBuilder().
		WithSKUID("report-001").       // 测试用商品SKU
		WithTitle("Report").           // 商品标题
		WithDescription("Paid report").// 商品描述
		WithPrice("2.00", entity.CurrencyUSDC). // 价格2.00 USDC
		WithStatus(entity.ProductStatusActive). // 上架状态
		WithTags([]string{"AI", "Agent"}).      // 标签
		WithSellerAddress("seller111").         // 卖家Solana地址
		.MustBuild() // 测试用例必须合法，失败直接panic

	// 2. 创建待测试的领域服务实例
	// 这里传 nil 是因为 BuildPaymentRequiredV2 方法不依赖 ProductRepository
	svc := NewProductDomainService(nil)

	// 3. 调用待测试的业务方法
	// 传入构建 x402 支付要求所需的所有参数
	required, err := svc.BuildPaymentRequiredV2(BuildPaymentRequiredInput{
		Product:        product, // 要购买的商品
		ResourceURL:    "https://merchant.example.com/api/v1/products/report-001/execute", // 受保护的资源地址
		PayTo:          "seller111", // 收款地址
		Asset:          "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", // USDC在Solana上的官方合约地址
		Network:        "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1", // Solana主网链ID
		FacilitatorURL: "https://ai.wenfu.cn", // StablePay支付网关地址
	})

	// 4. 断言结果正确性
	if err != nil {
		t.Fatalf("unexpected error: %v", err) // 有错误直接终止测试
	}
	if required.X402Version != X402VersionV2 {
		t.Fatalf("got version %d, want %d", required.X402Version, X402VersionV2) // 断言x402协议版本正确
	}
	if required.Accepts[0].Amount != "2000000" {
		t.Fatalf("got amount %s, want 2000000", required.Accepts[0].Amount) // 断言金额正确：2.00 USDC = 2000000 最小单位
	}
	if required.Accepts[0].Network != "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1" {
		t.Fatalf("unexpected network %s", required.Accepts[0].Network) // 断言区块链网络正确
	}
}
```
这个测试模拟了 **当AI Agent访问受保护的付费资源时，后端生成x402支付要求** 的完整流程：
1. 商品价格是`2.00` USDC，转换成最小单位就是`2000000`（USDC是6位小数），这和之前的`GetPriceMinorUnits`方法逻辑一致
2. 生成的`X402PaymentRequired`结构体包含了所有支付所需的信息：收款地址、金额、资产类型、区块链网络、支付网关地址
3. 这个结构体会被编码成HTTP响应头，返回给AI Agent，触发StablePay的自动支付流程
#### 5.2.4.2 第二个测试用例
这个测试测试 **把x402支付要求编码成标准HTTP头** 的功能，这是后端返回402 Payment Required响应的关键步骤。
```go
func TestEncodePaymentRequiredHeader(t *testing.T) {
	// 1. 手动构造一个x402支付要求结构体
	header, err := EncodePaymentRequiredHeader(&X402PaymentRequired{
		X402Version: X402VersionV2,
		Resource:    X402ResourceInfo{URL: "https://merchant.example.com/resource"}, // 受保护资源地址
		Accepts: []X402PaymentRequirements{{
			Scheme:            X402SchemeExact, // 支付方案：固定金额
			Network:           "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1", // Solana主网
			Amount:            "1", // 金额1最小单位（测试用）
			Asset:             "USDC", // 资产类型
			PayTo:             "seller111", // 收款地址
			MaxTimeoutSeconds: 60, // 支付超时时间60秒
		}},
	})

	// 2. 断言结果
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if header == "" {
		t.Fatal("expected non-empty header") // 断言编码后的头不为空
	}
}
```
- `EncodePaymentRequiredHeader` 函数会把结构化的 `X402PaymentRequired` 转换成 Base64 编码的字符串
- 后端会把这个字符串放到 HTTP 响应头 `X-402-Payment-Required` 中，同时返回 `402 Payment Required` 状态码
- StablePay Agent 收到这个响应后，会自动解析头信息，完成支付，然后重新请求资源
#### 5.2.4.3 意义
1. **领域层是核心中的核心**：支付相关的业务逻辑绝对不能出错，一个金额计算错误就会导致资金损失，所以领域层的代码必须100%覆盖单元测试
2. **纯单元测试，运行速度极快**：不依赖任何外部服务，每次代码修改后都可以在几毫秒内跑完所有测试，快速发现bug
3. **文档作用**：测试用例本身就是最好的文档，看测试用例就能知道这个方法的输入输出、业务场景和预期行为
4. **重构保障**：以后重构`BuildPaymentRequiredV2`方法时，只要测试能通过，就说明业务逻辑没有被破坏

## 5.3 决策链路
前面几章已经知道，这个 Merchant Server 最终会有 Adapter、Application、Domain、Infrastructure 四层。但真正开始写 Domain 层时，最容易犯的错误是：一上来就先画目录、先背概念、先定义一堆 Entity、VO、Repository、Service。

这会让 Domain 层变成“架构表演”。

更自然的写法应该反过来：先从一个业务愿望开始。

我现在想做的事情很简单：

> 我希望商家可以发布商品，Agent 可以购买商品，没买的时候返回 x402 付款要求，买了以后返回内容。

这句话里还没有数据库、没有 HTTP、没有 Handler、没有 DTO，也没有 SQLite。它只有几个业务问题：
```
什么是商品？
商品什么时候能买？
价格怎么表示？
USDC 金额怎么转成链上需要的 atomic units？
x402 付款要求到底属于谁的规则？
购买成功后如何生成 proof？
Application Service 需要查商品时，Domain 层要不要定义 Repository？
```
Domain 层就是从这些问题里长出来的。
### 5.3.1 第一个愿望：我希望商品可以被购买
先不要急着设计 `Product` 有哪些字段。先写一个最小的测试愿望。
```go
func TestProductCanBePurchased(t *testing.T) {
    // 我的商品长什么样？还不知道。
    // 但我希望最终可以这样问：
    product := ???

    if !product.IsPurchasable() {
        t.Error("一个上架、有价格、有收款身份的商品应该可以购买")
    }
}
```
这个测试当然编译不过，因为现在什么都没有。

但这个编译错误不是坏事。它告诉我至少需要两个东西：
```text
Product 类型
IsPurchasable 方法
```
于是实体的起点不是“我要设计一个 Product 表”，而是：
> 我需要一个对象，能够回答“自己能不能被购买”。
先写最小代码：
```go
type Product struct{}
func (p *Product) IsPurchasable() bool {
    return true
}
```
这看起来很傻，但它让测试有了第一个落点。
此时 Domain 层的第一个对象出现了：

```text
Product Entity
```
为什么它是 Entity？不是因为目录叫 `entity`，而是因为它代表业务世界里一个有身份、有状态、有生命周期的东西：商品。

### 5.3.2 第二个愿望：不能所有商品都能被购买
第一个假实现返回 `true`，但很快会发现不对。
- 草稿商品不能购买。
- 下架商品不能购买。
- 没有价格的商品不能购买。
- 没有收款身份的商品也不能购买。
于是测试变成这样：
```go
func TestDraftProductCannotBePurchased(t *testing.T) {
    product := &Product{}

    if product.IsPurchasable() {
        t.Error("草稿商品不应该可以购买")
    }
}
```
这时 `return true` 就失败了。

为了让测试表达“上架”和“草稿”的区别，我才被迫引入 `Status`。
```go
type ProductStatus string

const (
    ProductStatusActive   ProductStatus = "active"
    ProductStatusInactive ProductStatus = "inactive"
    ProductStatusDraft    ProductStatus = "draft"
)

type Product struct {
    Status ProductStatus
}

func (p *Product) IsPurchasable() bool {
    return p.Status == ProductStatusActive
}
```

这一步很重要。`Status` 不是我拍脑袋设计出来的字段，而是因为业务规则需要区分“上架”和“未上架”，所以它才出现。

这就是 Domain 的第一条原则：
> 先有行为，后有字段。字段是被业务规则逼出来的，不是为了凑数据库表设计出来的。
### 5.3.3 第三个愿望：有状态还不够，还要有价格
商品上架了，但没有价格，当然也不能购买。继续写测试：
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
这个测试逼出第二个字段：
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
这里价格先用 `string`，不是最终完美设计，而是因为当前外部世界里价格通常来自配置、数据库或 JSON，例如 `"2.00"`。

这时先不要急着上 Money 对象。因为一开始我只是想判断“有没有价格”，不是“如何精确计算金额”。

过早引入 Money，会让简单测试变复杂。
### 5.3.4 第四个愿望：商品不仅要有价格，还要知道付给谁
在 StablePay 里，商品不是普通展示卡片。它要能触发支付。

Agent 请求商品内容时，Merchant Server 需要告诉 Agent：
```
你要付多少钱
付什么资产
付到哪个地址
买的是哪个资源
支付后我怎么验证你买过
```
所以商品还需要一个和支付身份绑定的字段。

当前代码里叫`SkillDid string`，它表示这个商品或商户在 StablePay 支付验证里的 DID 标识。

于是测试继续变成：
```go
func TestProductWithoutSkillDidCannotBePurchased(t *testing.T) {
    product := &Product{
        Status: ProductStatusActive,
        Price:  "2.00",
    }

    if product.IsPurchasable() {
        t.Error("没有 SkillDid 的商品无法生成稳定支付要求，不应该可以购买")
    }
}
```
这一步逼出第三个关键字段：
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

这时 `IsPurchasable()` 才开始像一个真正业务规则：
- 商品必须上架
- 商品必须有价格
- 商品必须有支付身份
注意，这里仍然没有数据库，也没有 HTTP。

这说明 `IsPurchasable()` 是 Domain 层规则，而不是 Handler 层规则。

### 5.3.5 第五个愿望：商品还需要被展示，所以字段继续长出来
现在我只解决了“能不能买”。但商品还要被 Agent 列表展示。

商品列表至少要有：
```text
SKU ID
标题
描述
作者
标签
价格
币种
状态
```
于是 Product 才继续长出这些字段：
```go
type Product struct {
    ID          int64
    SKUID       string
    Title       string
    Description string
    Price       string
    Currency    string
    Author      string
    Tags        []string
    Status      ProductStatus
    SkillDid    string
    CreatedAt   time.Time
    UpdatedAt   time.Time
}
```
这里也要分清楚哪些字段是核心规则逼出来的，哪些字段是展示和管理需要的。
- `Status`、`Price`、`SkillDid` 是购买规则直接需要的字段。
- `Title`、`Description`、`Author`、`Tags` 是商品展示需要的字段。
- `CreatedAt`、`UpdatedAt` 是生命周期管理需要的字段。
- `ID` 可能是内部存储需要的字段。
- `SKUID` 是外部稳定识别商品需要的字段。
这样理解以后，就不会把 Product 当成“数据库表字段集合”。

Product 是业务对象。它只是刚好也会被数据库保存，也会被 API 展示。
### 5.3.6 第六个愿望：只返回 bool 不够，我还想知道为什么不能买
`IsPurchasable()` 很好用，但它只有 true/false。
当商品不能买时，Application Service 后面会想知道原因：
```text
商品不存在？
商品下架？
商品没有价格？
商品缺少 SkillDid？
价格格式错误？
```
所以会出现另一个方法：
```go
func (p *Product) ValidatePurchasable() error
```
它和 `IsPurchasable()` 的关系可以这样理解：
```go
func (p *Product) IsPurchasable() bool {
    return p.ValidatePurchasable() == nil
}
```
- `IsPurchasable()` 适合测试和简单判断。
- `ValidatePurchasable()` 适合业务流程，因为它能给出错误原因。

我一开始只写 IsPurchasable，因为测试只关心 true/false。
但当 Application 层要把错误原因转成业务响应时，bool 不够用了，
所以我才引入 ValidatePurchasable。
这体现了领域模型是从用例中演进出来的，不是一开始拍脑袋设计完整的。
### 5.3.7 第七个愿望：写了几个测试以后，创建商品太烦了
一开始测试里可以直接写：
```go
product := &Product{
    SKUID:    "report-001",
    Title:    "Report",
    Price:    "2.00",
    Currency: "USDC",
    Status:   ProductStatusActive,
    SkillDid: "did:solana:seller111",
}
```
写一次没问题。

写三次也能忍。

但当测试越来越多时，会出现大量重复：
```go
product := &Product{
    SKUID:    "report-001",
    Title:    "Report",
    Price:    "2.00",
    Currency: "USDC",
    Status:   ProductStatusActive,
    SkillDid: "did:solana:seller111",
}
```
然后下一个测试只是把 `Status` 改成 draft：
```go
product := &Product{
    SKUID:    "report-001",
    Title:    "Report",
    Price:    "2.00",
    Currency: "USDC",
    Status:   ProductStatusDraft,
    SkillDid: "did:solana:seller111",
}
```
再下一个测试只是把 `Price` 置空。

这时候我需要 **Builder**。

Builder 不是因为“设计模式书上说 Builder 好”，而是因为：

```text
创建 Product 的样板代码太多；
默认 Currency 总是 USDC；
默认 CreatedAt / UpdatedAt 总要填；
有些测试只关心一个字段变化；
直接 struct literal 让测试噪音太大。
```
所以我引入：
```go
product := NewProductBuilder().
    WithSKUID("report-001").
    WithTitle("Report").
    WithPrice("2.00", "USDC").
    WithStatus(ProductStatusActive).
    WithSellerAddress("seller111").
    Build()
```
这样测试的重点会更清楚。

如果我要测试草稿商品，只改关键差异：
```go
product := NewProductBuilder().
    WithSKUID("report-001").
    WithTitle("Report").
    WithPrice("2.00", "USDC").
    WithStatus(ProductStatusDraft).
    WithSellerAddress("seller111").
    Build()
```
Builder 的真实动机是降低测试和 seed 数据的创建成本。它不是 Domain 层一开始必须有的东西，而是当重复创建实体变得烦人时，自然长出来的工具。
### 5.3.8 第八个愿望：Build 不应该总是 panic
最早 Builder 里可能写：
```go
func (b *ProductBuilder) Build() *Product {
    if b.product.SKUID == "" || b.product.Title == "" {
        panic("product: sku_id and title are required")
    }
    return b.product
}
```
这在 seed 数据里可以接受。因为种子数据写错，启动时直接崩掉反而容易暴露问题。

但在普通业务流程里，panic 不合适。创建失败应该返回 error。

所以更稳妥的演进是：
```go
func (b *ProductBuilder) Build() (*Product, error) {
    if err := b.product.ValidateBasic(); err != nil {
        return nil, err
    }
    return b.product, nil
}

func (b *ProductBuilder) MustBuild() *Product {
    p, err := b.Build()
    if err != nil {
        panic(err)
    }
    return p
}
```

业务代码用 Build，显式处理错误；测试和种子数据可以用 MustBuild，失败直接暴露。

panic 适合不可恢复的程序员错误；业务输入错误应该返回 error。

### 5.3.9 第九个愿望：价格不能只是字符串，我怕算错钱
现在 Product 里有：
```go
Price    string
Currency string
```

商品展示时 `"2.00" USDC` 很自然。
但支付时不能把 `"2.00"` 原样传给链上。

USDC 常见精度是 6 位小数，所以：
```text
2.00 USDC      = 2000000 atomic units
0.5 USDC       = 500000 atomic units
0.000001 USDC  = 1 atomic unit
```
这时我会想在 Product 上写：
```go
func (p *Product) GetPriceMinorUnits() string
```
但刚开始很容易写错。

比如有人可能写：
```go
amount, _ := strconv.ParseFloat(p.Price, 64)
return fmt.Sprintf("%.0f", amount*1000000)
```
问题是金额不能用浮点数随便算。

浮点数适合科学计算，不适合钱。
因为很多十进制小数无法被二进制浮点精确表示。
一旦出现精度误差，支付金额可能多一位、少一位，甚至在极端情况下出现无法解释的 **四舍五入问题**：`0.1 + 0.2 = 0.30000000000000004`
这时 Money 值对象才出现，因为：
- 我怕算错钱；
- 我希望金额转换集中在一个地方；
- 我希望金额转换能被独立测试；
- 我不希望各个 Service 里都手写 USDC * 1000000。

于是出现：
```go
type Money struct {
    AmountMinor string
    Currency    string
    Decimals    int
}
```
以及：
```go
func NewMoneyFromDecimal(amount, currency string) (Money, error)
func DecimalToMinorUnits(amount string, decimals int) (string, error)
```
它们解决的问题是：
```text
"2.00" + USDC -> "2000000"
"0.000001" + USDC -> "1"
"0.0000001" + USDC -> error
```
这就是 Value Object 的真实来源。

Value Object 不是“没有 ID 的小对象”这么抽象，而是某个值本身有业务含义，而且这个值有自己的校验和计算规则。

在 StablePay 里，Money 是 Value Object。
将来 DID、WalletAddress、ResourceURL 也可能变成 Value Object。
### 5.3.10 第十个愿望：Product 可以调用 Money，但不应该懂太多支付协议
Product 可以提供：
```go
func (p *Product) PriceMoney() (Money, error)
```
或兼容旧代码：
```go
func (p *Product) GetPriceMinorUnits() string
```
这说明 Product 知道自己的价格如何转成可支付金额。

但 Product 不应该知道完整 x402 PaymentRequired 怎么构造。

因为 x402 PaymentRequired 不只需要商品自己的字段，还需要：
```text
resource URL
network
asset
payTo
facilitator URL
timeout
extensions
```
这些不是 Product 自己一个实体能完整决定的。

所以这里出现了一个边界：
- Product 负责“我是一个什么商品，我能不能买，我的价格是多少”；
- Domain Service 负责“围绕商品构造更完整的购买规则”。
### 5.3.11 第十一个愿望：我需要一个地方表达“这个商品要怎么付款”
原来 x402 结构可能会很自然地先写在 Adapter DTO 里，因为它最终确实通过 HTTP 402 返回给 Agent。

但写着写着会发现不对。

`PaymentRequired` 本质上不是“接口返回 JSON”这么简单。它描述的是一个业务合约：
```text
你要访问哪个资源？
这个资源需要多少钱？
可以用什么支付方案？
在哪条链上支付？
付什么资产？
付给谁？
多长时间内有效？
```
即使将来不用 HTTP，而是改成 gRPC、MCP、A2A，甚至消息队列，这个规则仍然存在。

也就是说：
- “付多少钱拿什么资源”是业务合约；
- “把这个合约 Base64 后塞进 PAYMENT-REQUIRED Header”才是 HTTP 传输细节。
所以 x402 的核心结构应该往 Domain 层移动，而不是留在 Adapter DTO。

旧版本里我们是：
```json
{
  "accepts": [
    {
      "scheme": "exact",
      "network": "solana:...",
      "maxAmountRequired": "2000000",
      "payTo": "...",
      "asset": "...",
      "resource": "/api/v1/products/report-001/execute"
    }
  ]
}
```
但 x402 v2 的结构更明确：
```json
{
  "x402Version": 2,
  "error": "PAYMENT-SIGNATURE header is required",
  "resource": {
    "url": "https://merchant.example.com/api/v1/products/report-001/execute",
    "description": "Access to premium report",
    "mimeType": "application/json"
  },
  "accepts": [
    {
      "scheme": "exact",
      "network": "solana:...",
      "amount": "2000000",
      "asset": "USDC mint",
      "payTo": "seller wallet",
      "maxTimeoutSeconds": 300,
      "extra": {
        "currency": "USDC",
        "productId": "report-001",
        "skillDid": "did:solana:..."
      }
    }
  ],
  "extensions": {}
}
```
关键变化有几个：
- 必须带 x402Version = 2
- resource 独立出来，不再只是 accepts 里的字符串
- 金额字段使用 amount，而不是 maxAmountRequired
- network 使用 CAIP-2 风格网络标识
- HTTP Header 使用 PAYMENT-REQUIRED / PAYMENT-SIGNATURE / PAYMENT-RESPONSE
这会影响 Domain 设计。

因为我不能继续让 Application 层手搓旧的 `X402AcceptItem`，否则后面 Adapter、插件、Gateway 都会围绕过时结构继续扩散。

所以 Domain 层需要定义 x402 v2 的核心结构：
```go
type X402PaymentRequired struct {
    X402Version int
    Error       string
    Resource    X402ResourceInfo
    Accepts     []X402PaymentRequirements
    Extensions  map[string]any
}
```
以及：
```go
type X402PaymentRequirements struct {
    Scheme            string
    Network           string
    Amount            string
    Asset             string
    PayTo             string
    MaxTimeoutSeconds int
    Extra             map[string]any
}
```
这一步是为了纠正边界：
- x402 核心结构属于 Domain；
- HTTP Header 编解码属于 Adapter；
- 调用 Gateway 验证支付属于 Infrastructure Client；
- 购买流程编排属于 Application。

### 5.3.12 第十二个愿望：有些规则不属于单个 Product，于是 Domain Service 出现
现在已经有：
```text
Product：商品实体
Money：金额值对象
X402PaymentRequired：支付合约
```
但还缺一个协调者。

构造 x402 PaymentRequired 时，需要同时使用：
```text
Product
Money
resource URL
payTo
asset
network
facilitator URL
timeout
extensions
```
这些信息不是 Product 自己全部拥有的。Product 只知道“我是哪个商品、多少钱、是否可购买”。它不应该知道 Merchant Server 的完整 URL，也不应该知道全部 x402 扩展字段。

于是出现 Domain Service：
```go
type ProductDomainService struct{}
```
它的职责不是替代 Product，而是处理那些“不自然属于某一个实体”的领域逻辑。例如：
```go
func (s *ProductDomainService) CanPurchase(product *Product) error
```
这只是对 Product 校验的统一入口。再例如：
```go
func (s *ProductDomainService) BuildPaymentRequiredV2(input BuildPaymentRequiredInput) (*X402PaymentRequired, error)
```
它负责把商品、金额、资源、网络、收款地址组合成 x402 v2 PaymentRequired。

这就是 Domain Service 的真实动机：

> 当一个业务规则需要协调多个对象，放进任何一个实体都别扭时，才引入 Domain Service。

不是所有业务都要有 Domain Service。
如果 `Product.IsPurchasable()` 足够表达，就不要硬塞进 Service。
如果规则跨越 Product、Money、x402 合约，那就应该放到 Domain Service。
### 5.3.13 第十三个愿望：购买成功后，我要给本次访问一个 proof
支付完成后，Gateway 可以证明链上支付发生过。

但 Merchant Server 也可能需要返回一个 proof，表示我这个商户后端确认你可以访问这个商品内容，这个 proof 至少应该包含：
```text
proof_id
proof_version
agent_did
product_id
issued_at
signature
```
一开始可以写占位：
```go
"signature": "pending_implementation"
```
Domain Service 可以提供：
```go
func BuildSignedProof(agentDID, productID, proofSecret string) (*PurchaseProof, error)
```

它不需要知道 HTTP，也不需要知道数据库。
它只关心：给定 Agent、商品、密钥，生成一个可校验的访问证明。

注意，`proofSecret` 不应该写死在 Domain 层。
它应该来自配置或 Secret，由 Application 层传入。

Domain 层负责算法和结构，不负责密钥来源。
### 5.3.14 第十四个愿望：准备写 Application Service 时，突然发现我需要查商品
到这里，如果只写 Product、Money、x402、DomainService，还都可以在内存里直接创建对象测试。

但当我准备写 Application Service 时，购买流程会变成：
```text
ExecutePurchase(skuID, agentDID)
  ↓
根据 skuID 查商品
  ↓
校验商品是否可购买
  ↓
检查是否已支付
  ↓
未支付返回 PaymentRequired
  ↓
已支付返回内容和 proof
```
这时候会卡住：
```go
func ExecutePurchase(ctx context.Context, skuID, agentDID string) {
    product := ??? // 从哪里来？
}
```
我需要一个“查商品”的地方。

这就是 Repository 接口出现的时机。

不是项目一开始就要先写 Repository，而是当 Application Service 写不下去时，我才发现：

> 我需要一种方式获取 Product，但我不想让 Application/Domain 直接依赖 SQLite 或 MySQL。

于是 Domain 层定义接口：
```go
type ProductRepository interface {
    FindAll(ctx context.Context, page, size int) ([]*Product, int64, error)
    FindBySKUID(ctx context.Context, skuID string) (*Product, error)
    FindByID(ctx context.Context, id int64) (*Product, error)
    Save(ctx context.Context, product *Product) error
    UpdateStatus(ctx context.Context, id int64, status ProductStatus) error
}
```
为什么接口放在 Domain？

因为 Domain 层定义的是业务需要的能力：
- 我要查商品
- 我要保存商品
- 我要修改商品状态
至于这个能力怎么实现，是内存 map、SQLite、MySQL、Redis，还是远程 API，那是 Infrastructure 的事。

这就是依赖倒置的真实动机：
- 业务层不依赖数据库；
- 业务层只依赖“查商品”这个抽象能力；
- 数据库实现反过来满足业务层定义的接口。
### 5.3.15 Repository 一开始不要设计太大
Repository 也容易过度设计。

一开始不要写：
```go
FindByTitle
FindByAuthor
FindByTag
FindByPriceRange
FindByStatus
FindByCreatedAt
Search
BatchSave
SoftDelete
HardDelete
```
先根据 Use Case 来。

当前最小 Use Case 是：
```text
商品列表：FindAll
商品详情：FindBySKUID
购买执行：FindBySKUID
后台新增或 seed：Save
上下架：UpdateStatus
```
所以 Repository 接口有这些就够了。

Repository 接口也应该被业务逼出来，而不是被数据库表逼出来。

如果以后真的要做搜索，再加 `SearchProducts`。
如果以后真的要做商户后台，再加 `FindByMerchantID`。
如果以后真的要做库存，再重新思考 Product 和 Inventory 的边界。

### 5.3.16 最终 Domain 层是怎样长出来的？
把前面的决策链串起来，Domain 层不是一次性设计出来的，而是这样长出来的：
```text
我想问商品能不能买
  ↓
Product + IsPurchasable 出现

不能所有商品都能买
  ↓
Status 出现

上架但没价格也不能买
  ↓
Price 出现

有价格但没有支付身份也不能买
  ↓
SkillDid 出现

商品要展示
  ↓
SKUID / Title / Description / Author / Tags 出现

只返回 bool 不够
  ↓
ValidatePurchasable 出现

测试里创建商品太重复
  ↓
ProductBuilder 出现

价格要转成 USDC atomic units，我怕算错钱
  ↓
Money Value Object 出现

x402 付款要求不是普通 HTTP DTO，而是“付多少钱拿什么资源”的业务合约
  ↓
X402PaymentRequired / Resource / PaymentRequirements 出现

构造 x402 需要协调 Product、Money、配置和资源信息
  ↓
ProductDomainService 出现

购买成功后要有商户侧访问证明
  ↓
PurchaseProof / BuildSignedProof 出现

Application Service 要查商品，但不想依赖数据库
  ↓
ProductRepository 接口出现
```

这才是 Domain 层真正的学习路线。

## 5.4 Domain 层每个部分的面试讲法
### Product Entity
```text
我没有一开始照着数据库表设计 Product。
我是先从“商品能不能被购买”这个业务问题出发，
写出 IsPurchasable，再被规则逼出 Status、Price、SkillDid 这些字段。
所以 Product 不是贫血模型，它包含自己的业务判断。
```
### ProductStatus
```text
商品状态是购买规则的核心。
active 可以购买，draft 和 inactive 不可以购买。
我用 ProductStatus 枚举收敛状态，避免代码里到处散落字符串。
```
### Builder
```text
Builder 不是为了套设计模式。
它是在测试和 seed 数据里反复创建 Product 时自然出现的。
当每个测试都要写 Currency、Status、CreatedAt 这些重复字段时，
Builder 可以提供默认值，让测试只表达关心的差异。
```
### Money Value Object
```text
Money 的出现是因为支付金额不能用 float64 随便算。
USDC 是 6 位精度，2.00 要变成 2000000 atomic units。
我把金额转换集中在 Money 值对象里，用字符串和整数逻辑处理，避免精度问题。
```
### x402 PaymentRequired
```text
x402 PaymentRequired 描述的是一个付费资源的业务合约：
访问哪个资源，需要付多少钱，付什么资产，付到哪里。
这个规则即使不用 HTTP 也成立，所以核心结构属于 Domain。
但 PAYMENT-REQUIRED Header、Base64 编码、HTTP 402 状态码属于 Adapter。
```
### Domain Service
```text
Product 自己能判断是否可购买，但它不应该知道完整 x402 合约怎么拼。
x402 需要 Product、Money、resource、payTo、asset、network 等多个信息。
这种跨对象的领域规则放到 ProductDomainService 里更自然。
```
### Repository
```text
Repository 不是我一开始为了套架构写的。
是当 Application Service 要实现 ListProducts 和 ExecutePurchase 时，
我发现需要查询商品，但又不希望业务层直接依赖 SQLite。
所以我在 Domain 层定义 ProductRepository 接口，
让 Infrastructure 去实现它。
```
