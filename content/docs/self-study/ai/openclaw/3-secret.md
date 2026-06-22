# 第三章：略讲 StablePay 后端链路——插件到底在接谁？

前两章主要讲的是 OpenClaw 插件本身：插件是什么、工具怎么注册、`src` 怎么构建到 `dist`、LLM 又是怎么通过工具名和 schema 调用插件的。

但 StablePay 插件不是一个孤立工具。它之所以复杂，是因为它背后接的是一套真实的支付后端。

这一章不打算重新完整复盘 StablePay 的微服务架构。后端那部分我已经在另一份笔记里写过，包括 API Gateway、DID Service、Payment Service、Blockchain Adapter、Verification Service、Query Service 这 6 个核心服务的职责边界、微服务拆分原因、K8s 部署、服务发现、Ingress、幂等、最终一致性和排障方法。

在 OpenClaw 插件笔记里，我只需要回答一个更聚焦的问题：

> StablePay 插件作为 OpenClaw Agent 和 StablePay 后端之间的适配层，它到底在调用哪些服务？这些后端能力对插件开发有什么影响？

---

## 3.1 插件不是后端服务，而是 Agent 到后端的工具适配层

StablePay 后端可以理解成一组服务能力：

```text
DID Service：
    负责身份、钱包、公钥、签名、防重放和 DID 状态。

Payment Service：
    负责支付请求、支付状态机、幂等、防重放和支付生命周期。

Blockchain Adapter：
    负责 Solana RPC、SPL Token 转账、交易构造、提交、确认和余额查询。

Verification Service：
    负责购买关系、purchase record、proof 和商户授权验证。

Query Service：
    负责余额、交易历史、收益统计、销售记录和读模型。

API Gateway：
    负责外部统一入口、鉴权、限流、路由、日志、request_id / trace_id 和错误格式。
```

OpenClaw 插件并不直接替代这些服务。

插件做的是另一件事：

```text
把这些后端服务包装成 Agent 可以调用的工具。
```

也就是说，插件的位置在这里：

```text
用户自然语言
   ↓
OpenClaw Agent / LLM
   ↓
StablePay OpenClaw Plugin
   ↓
StablePay API Gateway
   ↓
DID / Payment / Blockchain / Verification / Query
```

插件不是支付系统本身，而是支付系统的 Agent-facing tool layer。

这点很重要。

如果面试时只说“我做了支付插件”，听起来像是写了几个 HTTP client。更准确的说法应该是：

> 我做的是 StablePay 面向 OpenClaw Agent 的工具适配层，把后端 DID、钱包签名、402 支付接管、余额查询和购买验证封装成 LLM 可以安全调用的工具。

---

## 3.2 插件为什么优先调用 API Gateway？

从后端微服务角度看，StablePay 内部有很多服务。但插件不应该直接面对每个服务的内部地址。

插件最稳定的外部入口应该是：

```text
https://ai.wenfu.cn
```

也就是 StablePay API Gateway。

原因很简单：

```text
1. Gateway 是统一外部入口。
2. Gateway 负责鉴权、限流、request_id、trace_id 和统一错误码。
3. Gateway 负责把请求路由到 DID、Payment、Query、Verification 等服务。
4. 插件不需要知道内部服务怎么部署、端口是多少、K8s Service 名称是什么。
5. 后端服务迁移、扩容、重构时，只要 Gateway API 稳定，插件不需要频繁修改。
```

所以插件里的 `StablePayClient` 本质上不是随便访问某个服务，而是访问 StablePay Gateway。

例如：

```text
注册 DID：
插件 → API Gateway → DID Service

发起支付：
插件 → API Gateway → Payment Service → DID Service / Blockchain Adapter

查询余额：
插件 → API Gateway → Query Service / Blockchain Adapter

查询销售：
插件 → API Gateway → Query Service

验证购买：
商户或插件 → API Gateway / Verification Service
```

这也是为什么插件配置里最重要的后端参数是：

```text
backendBaseUrl
```

它默认指向线上 Gateway。

---

## 3.3 插件需要理解后端，但不应该泄漏后端复杂度

插件开发者当然需要理解后端链路。

如果我不知道 DID Service 是什么，就很难理解为什么要先注册 DID。

如果我不知道 Payment Service 有幂等和状态机，就很难理解为什么支付请求要带 idempotency key。

如果我不知道 Blockchain Adapter 负责链上交易，就很难理解为什么支付不是普通数据库写入，而是要处理 RPC 超时、链上确认和 tx hash。

如果我不知道 Verification Service 负责购买关系，就很难理解为什么“支付成功”和“商户验证已购买”不是完全同一件事。

但是，这些复杂度不应该原样暴露给新用户，也不应该全部暴露给 LLM。

用户只想说：

```text
帮我初始化 StablePay 插件。
帮我查余额。
帮我买一个测试商品。
```

LLM 也不应该每一步都纠结：

```text
我要不要直接访问 DID Service？
我要不要绕过 Gateway？
Blockchain Adapter 的 RPC 怎么配？
Verification Service 的 proof 怎么查？
```

插件应该把后端复杂度折叠成更高层的工具：

```text
stablepay_onboard：
    自动完成本地准备、钱包、DID、支付限额和余额检查。

stablepay_doctor：
    诊断插件是否能正常连接后端、读取本地状态、使用签名 runtime。

stablepay_pay_via_gateway：
    通过 Gateway 走支付链路，而不是让 LLM 自己拼一堆内部服务调用。

stablepay_query_balance：
    查询当前 DID 的余额，而不是让 LLM 理解 Query Service 和 Blockchain Adapter 的具体边界。
```

所以插件既要理解后端，又不能把后端复杂度直接甩给用户。

这就是 Agent-facing tool layer 的价值。

---

## 3.4 后端支付链路和插件工具之间的对应关系

从插件角度看，StablePay 的核心工具可以和后端能力这样对应：

```text
stablepay_register_local_did
    ↓
API Gateway
    ↓
DID Service

stablepay_query_balance
    ↓
API Gateway
    ↓
Query Service / Blockchain Adapter

stablepay_pay_via_gateway
    ↓
API Gateway
    ↓
Payment Service
    ↓
DID Service 校验身份
    ↓
Blockchain Adapter 执行链上交易
    ↓
Verification Service / purchase record

stablepay_query_sales
    ↓
API Gateway
    ↓
Query Service

stablepay_execute_paid_skill_demo
    ↓
Demo Skill Backend
    ↓
返回 402 Payment Required
    ↓
插件接管支付
    ↓
支付完成后重试 Demo Skill Backend
```

这里最重要的是 `stablepay_pay_via_gateway` 和 `stablepay_execute_paid_skill_demo` 的区别。

`stablepay_pay_via_gateway` 更像是直接走支付 API：

```text
我已经知道 skill_did、price、currency。
我直接问 Gateway：这个资源要不要付款？如果需要，就完成支付。
```

`stablepay_execute_paid_skill_demo` 更像是完整的付费资源访问流程：

```text
我先访问某个 demo skill。
如果后端返回 402，说明需要付款。
插件解析 402 里的支付要求。
插件完成支付。
插件再重试原来的 skill 请求。
```

这两个工具都和支付有关，但它们面向的用户任务不同。

这也是 Agent 工具设计里很关键的一点：

> 工具不是按代码函数随便拆，而是要按用户任务和 Agent 决策场景拆。

---

## 3.5 为什么 402 对 Agent 支付很重要？

在传统网页里，用户遇到付费资源，通常会看到一个支付页面。用户自己点击按钮、扫码、确认。

但 Agent 场景不一样。

Agent 访问一个资源时，需要一种机器可读的方式告诉它：

```text
这个资源需要付款。
付款金额是多少。
币种是什么。
收款方是谁。
支付网络是什么。
支付完成后如何重试。
```

HTTP 402 Payment Required 正好适合表达这件事。

在 StablePay 插件里，402 的意义不是简单的错误码，而是一个支付协商入口：

```text
Agent 请求资源
   ↓
后端返回 402
   ↓
响应里携带 payment requirement
   ↓
插件解析支付要求
   ↓
插件本地签名并发起支付
   ↓
支付完成后重试原请求
```

这也是为什么我后面会把 x402 单独作为一个兼容方向来写。x402 的价值在于，它让“需要付款”从一个私有业务逻辑，变成更标准化的 HTTP 支付协议表达。

不过在本章里，我只需要先记住：

> 对 Agent 来说，402 不是普通失败，而是“下一步应该调用支付工具”的结构化信号。

---

## 3.6 第三章小结：后端是能力提供方，插件是 Agent 适配层

这一章只略讲后端，因为后端微服务我已经单独复盘过。

这里需要记住的是：

```text
1. StablePay 后端由 Gateway、DID、Payment、Blockchain Adapter、Verification、Query 等服务组成。
2. 插件不直接替代这些服务，而是通过 Gateway 调用它们。
3. 插件需要理解后端职责边界，但不能把这些复杂度暴露给用户和 LLM。
4. 402 是 Agent 支付链路里的关键转折点，表示资源需要付款。
5. 插件的核心价值，是把后端复杂支付能力包装成 Agent 可调用、可恢复、可确认的工具。
```

如果面试官问：

> “StablePay OpenClaw 插件和后端微服务是什么关系？”

我可以这样回答：

```text
StablePay 后端提供 DID、支付、链上执行、购买验证和查询能力；OpenClaw 插件不是替代后端，而是作为 Agent-facing tool layer，通过 API Gateway 调用这些后端服务。它负责把用户自然语言任务转成工具调用，把钱包签名、DID 注册、402 支付接管和支付确认包装成 LLM 可以安全使用的接口。
```

这一章讲到这里就够了。

接下来第四章要进入插件侧真正容易踩坑的地方：

> 本地状态、master key、钱包绑定和安全边界。

````

# 第四章：本地状态、密钥和安全边界——为什么不能让用户手动理解 MASTER_KEY？

第三章讲的是 StablePay 插件背后的后端服务。现在回到插件自己。

如果说后端负责 DID、支付、链上交易和验证，那么插件侧最重要的问题就是：

```text
我在本地到底存了什么？
我怎么保护这些本地状态？
用户为什么会被 MASTER_KEY 卡住？
LLM 为什么会一直让用户去设置环境变量？
新版本为什么要把这些东西收进 onboard？
````

这是 StablePay 插件从“能跑”变成“能给新用户用”的关键一步。

一开始我没有意识到本地状态和密钥管理是一个产品问题。我只把它当成工程配置：缺环境变量就报错，让用户自己设置。

但后来发现，这会直接破坏 Agent 场景的体验。

因为用户不是后端工程师，LLM 也不一定能正确理解这些配置项。它可能会反复要求用户设置 `STABLEPAY_PLUGIN_MASTER_KEY`，甚至把开发环境细节讲得越来越复杂。

所以这一章的核心反思是：

> 安全配置不能粗暴甩给用户。插件要把必要的安全机制做好，但不应该要求新用户理解所有底层细节。

---

## 4.1 插件为什么需要本地状态？

StablePay 插件不是一个完全无状态的 HTTP client。

它需要记住一些本地信息，才能在多次对话、多次工具调用、Gateway 重启后继续工作。

典型本地状态包括：

```text
当前钱包名称
当前钱包公钥
当前钱包对应的 backend DID
本地支付限额
自动支付阈值
最近一次 onboard session
本地配置路径
可能还有一些支付策略信息
```

这些信息不是每次都让用户重新输入。

比如用户第一次初始化插件时创建或绑定了钱包，后面再查余额、付款、注册 DID，不应该每次都问：

```text
你的钱包名是什么？
你的公钥是什么？
你的 DID 是什么？
你的单笔支付限额是多少？
```

这些状态应该被插件保存起来。

但它们又不能随便明文乱放。因为里面包含钱包身份、DID、支付策略等敏感或半敏感信息。

所以插件需要本地 state。

---

## 4.2 本地 state 和私钥不是一回事

这里要先避免一个很大的误解。

插件保存本地状态，不等于插件直接保存用户私钥。

在 StablePay 插件里，真正的私钥应该由 OWS SDK、OWS CLI、OWS REST 或对应钱包 runtime 管理。

插件本地 state 主要保存的是：

```text
钱包名
钱包公钥
DID
支付限额
策略配置
本地状态元信息
```

而不是把用户私钥明文写进 JSON。

这点面试时一定要讲清楚。

因为一旦说“插件保存钱包信息”，面试官很可能追问：

> “那你是不是把私钥存在插件目录里了？”

我应该回答：

```text
不是。插件保存的是用于业务流程恢复的本地状态，例如钱包名、公钥、DID 和支付限额。真正的签名由 OWS runtime 完成，插件通过 SDK/CLI/REST 调签名能力，不应该直接持有用户私钥。
```

这就是本地状态和密钥托管的边界。

---

## 4.3 为什么原来的 MASTER_KEY 设计会卡住新用户？

早期设计里，插件本地 state 是加密保存的。加密当然需要一个 master key。

于是最直接的做法是要求用户设置环境变量：

```bash
export STABLEPAY_PLUGIN_MASTER_KEY="replace-with-a-long-random-secret"
```

从工程师视角看，这很合理：

```text
用户提供 key。
插件用 key 加密本地 state。
下次启动再用同一个 key 解密。
```

但从新用户和 Agent 交互视角看，这非常糟糕。

因为用户会问：

```text
MASTER_KEY 是什么？
我应该怎么生成？
生成多长？
放在哪里？
忘了怎么办？
换电脑怎么办？
为什么 OpenClaw 一直让我设置这个？
```

LLM 也可能被带偏。

它看到工具报错缺少 `STABLEPAY_PLUGIN_MASTER_KEY`，就会机械地告诉用户：

```text
请先设置 STABLEPAY_PLUGIN_MASTER_KEY。
```

但它不会主动区分：

```text
这是开发者配置还是普通用户配置？
这是临时测试还是生产部署？
用户是不是第一次初始化？
插件能不能自动生成？
```

这就导致新用户初始化体验非常差。

所以问题不只是“报错文案不好”，而是抽象边界错了。

`MASTER_KEY` 是插件内部的本地加密材料，不应该成为普通用户必须理解的产品概念。

---

## 4.4 新设计：doctor 只读检查，onboard 自动修复

后来我把这件事重新拆开：

```text
stablepay_doctor：
    只读诊断，告诉用户当前状态。
    不自动写文件，不生成 master.key，不修改 state。

stablepay_onboard：
    引导式初始化。
    在用户请求初始化时，可以自动生成本地 master.key。
    可以创建或绑定钱包。
    可以注册 DID。
    可以配置支付限额。
```

这个职责划分很重要。

`doctor` 是事实来源：

```text
当前有没有 master key？
当前 state 能不能解密？
当前签名 runtime 是否可用？
当前有没有钱包？
当前有没有 DID？
```

它只报告，不修复。

`onboard` 是引导修复流程：

```text
如果缺 master.key，就自动生成。
如果缺钱包，就问用户创建新钱包还是绑定已有钱包。
如果缺 DID，就自动注册。
如果缺支付限额，就设置默认安全限额。
```

为什么不能让 doctor 自动修复？

因为 doctor 是诊断工具。诊断工具最好是无副作用的。这样我可以随时运行它，不担心它悄悄改本地状态。

面试时可以这样讲：

```text
我把诊断和修复分开。doctor 是只读 world state，不产生副作用；onboard 才是有副作用的初始化状态机。这样 Agent 可以安全地先了解环境，再在明确初始化任务中执行写操作。
```

这句话很适合体现 Agent 工程意识。

---

## 4.5 master.key 应该放在哪里？

新的思路是：

```text
普通用户不需要手动设置环境变量。
插件在 onboard 时自动生成本地 master.key。
master.key 放在用户本地 StablePay 配置目录。
```

例如：

```text
~/.stablepay-openclaw/master.key
~/.stablepay-openclaw/stablepay-local-state.enc
~/.stablepay-openclaw/onboard-sessions.json
```

这样设计有几个好处：

```text
1. 用户不用理解 MASTER_KEY。
2. Gateway 重启后还能读取同一个 master.key。
3. 本地 state 可以继续加密保存。
4. 老用户仍然可以通过环境变量覆盖。
5. 插件目录重装或升级时，不会把用户 state 一起删掉。
```

这里要注意一个细节：

不要把长期状态放进 `dist/` 或 npm 包目录。

因为插件升级、重新安装、ClawHub 覆盖时，包目录可能被替换。用户状态应该放在用户目录下，而不是发布包目录里。

所以更合理的是：

```text
代码在插件包里。
用户状态在 ~/.stablepay-openclaw/ 里。
```

这也是很多 CLI 工具常见的设计。

---

## 4.6 为什么继续兼容环境变量？

虽然普通用户不应该手动设置 `STABLEPAY_PLUGIN_MASTER_KEY`，但环境变量仍然要保留。

原因有三个。

第一，兼容老版本。

如果之前用户已经用环境变量创建过 state，那么突然移除环境变量支持，会导致旧 state 解不开。

第二，支持生产或自定义部署。

在某些更严格的环境里，管理员可能希望通过外部 Secret 管理 master key，而不是让插件自动生成文件。

第三，便于迁移和恢复。

如果用户换机器或恢复备份，环境变量可以作为手动恢复路径。

所以新逻辑不是“删除环境变量”，而是做优先级：

```text
1. 如果 STABLEPAY_PLUGIN_MASTER_KEY 存在，优先使用它。
2. 否则读取 ~/.stablepay-openclaw/master.key。
3. 如果是 onboard 初始化流程，master.key 不存在时自动生成。
4. 如果是 doctor，只报告缺失，不自动生成。
```

这样既兼容旧系统，又改善新用户体验。

---

## 4.7 本地 state 解密失败应该怎么提示？

还有一个很常见的问题：

```text
Failed to load local plugin state
```

早期这种错误可能直接把 crypto 异常甩给用户。

但这对用户没有帮助。

本地 state 解密失败通常意味着：

```text
1. master key 换了。
2. state 文件是旧 key 加密的。
3. 用户换机器但没迁移 master.key。
4. 环境变量覆盖了文件 key。
5. state 文件损坏。
```

所以更好的错误提示应该是：

```text
无法解密本地 StablePay 状态。

可能原因：
1. 当前 master key 与创建该 state 时使用的 key 不一致。
2. 你换了机器或重新安装插件，但没有迁移 master.key。
3. STABLEPAY_PLUGIN_MASTER_KEY 环境变量覆盖了本地 key。
4. state 文件可能损坏。

建议：
1. 如果你有旧 master.key，请恢复它。
2. 如果只是测试环境，可以备份并删除旧 state，然后重新 onboard。
3. 不要把 master.key 发给别人。
```

这种文案比直接抛异常更适合 Agent 场景。

因为 LLM 看到这个结果后，也能继续引导用户：

```text
你是要恢复旧钱包，还是重新初始化测试钱包？
```

---

## 4.8 钱包创建和钱包绑定是两件事

StablePay 插件里有两个容易混的工具：

```text
stablepay_create_local_wallet
stablepay_bind_existing_wallet
```

它们不是同一个语义。

`create_local_wallet` 是新建钱包：

```text
用户第一次使用，没有现成钱包。
插件通过 OWS SDK 创建新钱包。
本地 state 记录钱包名和公钥。
```

`bind_existing_wallet` 是绑定已有钱包：

```text
用户已经有 OWS 钱包。
用户提供 wallet_name 和 public_key。
插件需要确认这个钱包名和公钥确实匹配。
必要时通过 challenge 签名来验证。
```

为什么不能随便绑定？

因为如果用户输入了错误的钱包名或错误的 public key，后面 DID 注册、支付签名、余额查询都会乱。

更严重的是，绑定过程如果不校验，可能出现“本地 state 记录的是 A 地址，但实际签名用的是 B 钱包”的错配。

所以 `bind_existing_wallet` 应该比 `create_local_wallet` 更谨慎。

面试时可以这样讲：

```text
create 是生成新身份，bind 是把已有身份接入插件。bind 不能只是写入 wallet_name 和 public_key，而应该通过 challenge 签名验证钱包确实能控制该公钥，避免名钥错配。
```

---

## 4.9 OWS SDK / CLI / REST 不应该主动暴露给新用户

OWS 是本地签名能力的来源。

插件可能支持几种 runtime：

```text
ows-sdk：
    进程内 SDK 签名，默认优先。

ows-cli：
    调用本机 ows 命令行。

wsl-ows：
    WSL 场景下调用命令行。

ows-rest：
    调用远程 OWS 签名服务。
```

这些对开发者很重要，但对新用户不重要。

用户不应该一上来被问：

```text
你想使用 ows-sdk、ows-cli、wsl-ows 还是 ows-rest？
```

这会直接把用户劝退。

更好的设计是：

```text
默认优先使用 ows-sdk。
如果 ows-sdk 可用，就隐藏 CLI / REST 细节。
如果 ows-sdk 不可用，但 CLI 可用，再提示可以使用命令行签名。
如果完全没有签名能力，再给出解决方案。
```

这就是 doctor 里 severity / required / show_in_conversation 的价值。

不是所有检测项都要展示给用户。

例如：

```text
ows-sdk 可用：
    展示：内置签名驱动可用。
    隐藏：ows-cli 未安装、ows-rest 未配置。

ows-sdk 不可用但 ows-cli 可用：
    展示：内置签名驱动不可用，但检测到 OWS CLI，可以使用替代签名方式。

全部不可用：
    展示：没有可用签名驱动，并给出安装或配置建议。
```

这不是欺骗用户，而是分层暴露复杂度。

普通用户只需要知道“能不能签名”。

开发者需要排障时，再看完整 details。

---

## 4.10 支付限额也是本地安全状态

插件本地 state 里还会保存支付限额，例如：

```text
single_purchase_limit_usdc
auto_purchase_threshold_usdc
currency
```

这部分很重要，因为支付工具不是普通查询工具。

Agent 可能误解用户意图，也可能因为上下文混乱调用了支付工具。

所以插件需要本地策略来限制支付行为。

可以分三层：

```text
低于自动支付阈值：
    可以自动支付，例如 0.1 USDC 的测试商品。

高于自动支付阈值，但低于单笔硬上限：
    返回需要用户确认。

高于单笔硬上限：
    直接拒绝支付。
```

这就是 human-in-the-loop guardrail 的基础。

从本地状态角度看，支付限额不是普通偏好配置，而是安全策略。

面试时可以这样讲：

```text
我把支付限额放进本地加密 state，作为 Agent 支付工具的安全边界。LLM 不能只凭自己的判断完成高额支付，必须经过阈值检查和用户确认。
```

---

## 4.11 onboard session 为什么可以明文存，但不能存敏感材料？

`stablepay_onboard` 引入了 State Token，用来记录初始化进行到哪一步。

例如：

```text
session_id
created_at
updated_at
expires_at
current_step
completed_steps
pending_question
answers
```

这些信息是流程状态，不是钱包私钥。

所以它可以放在：

```text
~/.stablepay-openclaw/onboard-sessions.json
```

但要注意，session 里不能存：

```text
私钥
助记词
passphrase
完整 master key
敏感 API key
```

session 只能存：

```text
当前步骤
用户已经选择创建新钱包还是绑定已有钱包
已经完成 DID 注册
已经配置支付限额
还差哪些步骤
```

这样即使 session 文件被看到，风险也远低于泄露钱包密钥。

当然，如果未来要进一步加强，也可以把 session 一起放进加密 state。但 MVP 阶段，先把“流程状态”和“敏感密钥”分清楚更重要。

---

## 4.12 为什么 State Token 不能替代 doctor？

有了 onboard session 后，可能会误以为：

```text
既然 session 记录了进度，那下次直接读 session 不就行了吗？
```

这不对。

session 只记录“对话流程”，doctor 才检查“真实环境”。

比如 session 里写着：

```text
wallet step completed
```

但用户可能后来手动删了 state 文件。

或者 session 里写着：

```text
DID registered
```

但后端 DID 查询失败，或者用户换了钱包。

所以 onboard 每次都应该先跑 doctor。

正确关系是：

```text
doctor：
    事实来源。
    检查当前环境真实状态。

State Token：
    对话流程记忆。
    记录当前问到哪一步、用户回答过什么。

onboard：
    结合 doctor 和 State Token，决定下一步。
```

这就是混合状态机设计。

面试时可以这样讲：

```text
State Token 解决的是 LLM 多轮对话容易丢上下文的问题，doctor 解决的是环境真实状态可能变化的问题。二者不能互相替代。
```

---

## 4.13 第四章小结：安全配置要产品化，而不是甩给用户

这一章讲的是插件本地状态和安全边界。

核心结论如下：

```text
1. StablePay 插件需要本地 state 来记住钱包、DID、支付限额和 onboard session。
2. 本地 state 不等于私钥；真正签名应由 OWS runtime 完成。
3. MASTER_KEY 是插件内部加密材料，不应该成为普通用户必须理解的概念。
4. doctor 必须只读，负责诊断；onboard 可以有副作用，负责初始化和修复。
5. master.key 应放在用户目录下，而不是插件 dist 或 npm 包目录里。
6. 环境变量仍然要兼容，但普通用户默认不需要手动设置。
7. 钱包创建和绑定是不同语义，绑定已有钱包要防止名钥错配。
8. OWS SDK / CLI / REST 要分层暴露，默认隐藏工程细节。
9. 支付限额是 Agent 支付工具的本地安全策略。
10. State Token 记录对话流程，doctor 检查真实环境，二者配合形成可恢复 onboard。
```

如果面试官问：

> “你们插件里本地状态和安全是怎么设计的？”

我可以这样回答：

```text
StablePay 插件本地会保存钱包名、公钥、DID、支付限额和 onboard session 等状态，但不直接保存用户私钥。签名由 OWS runtime 完成。早期版本要求用户手动设置 STABLEPAY_PLUGIN_MASTER_KEY，后来我把它改造成 onboard 自动生成本地 master.key，同时保留环境变量兼容旧部署。doctor 只读诊断，onboard 负责有副作用的初始化。支付限额也保存在本地加密 state 中，用于限制 Agent 自动支付行为，超过阈值必须 human-in-the-loop 确认。
```

到这里，StablePay OpenClaw 插件已经不只是“能调用后端 API”了。

它开始有了一个更成熟的插件运行模型：

```text
后端能力由 StablePay 微服务提供。
插件通过 Gateway 调用后端。
本地状态由加密 state 管理。
签名由 OWS runtime 负责。
初始化由 onboard 状态机完成。
诊断由 doctor 提供事实来源。
支付行为由限额和确认机制保护。
```

下一章就可以继续讲：

> 从原子工具到任务型工具：为什么 LLM 不能直接面对一堆底层 API？
