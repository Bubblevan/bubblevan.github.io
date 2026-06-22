---
date: 2026-06-07
title: Openclaw Plugin 自救
authors: [bubblevan]
tags: []
---

## 1. 插件入口：`openclaw.plugin.json`

OpenClaw gateway 启动后，读到这个文件就知道该加载什么：

```json
{
  "id": "stablepay-agentpay-dev",          // 插件唯一 ID
  "name": "stablepay-agentpay-dev",
  "version": "0.3.15",
  // configSchema 定义了用户在 OpenClaw UI 里可以配置哪些字段
  "configSchema": {
    "properties": {
      "backendBaseUrl": { "default": "https://ai.wenfu.cn" },
      "requestTimeoutMs": { "default": 90000 },
      "rewardAmount": { "default": 1 },
      "owsRuntime": { "enum": ["auto","ows-sdk","ows-cli","wsl-ows","ows-rest"], "default": "ows-sdk" },
      // ... 还有 localStatePath, didRegisterPath, owsRestBaseUrl 等
    }
  }
}
```

然后在 `package.json` 里关联到编译产物：

```json
"openclaw": {
  "extensions": ["./dist/index.js"],
  "compat": { "pluginApi": ">=2026.3.1", "minGatewayVersion": "2026.3.1" }
}
```

最后 `dist/index.js` 是 gateway 实际加载的入口。

## 二、功能入口：`src/index.ts`

核心结构：

```typescript
export default definePluginEntry({
  id: "stablepay-agentpay-dev",
  name: "stablepay-agentpay-dev",
  description: "StablePay wallet runtime, ...",

  register(api) {
    // (1) 读取配置
    const cfg = getPluginConfig(api);

    // (2) 初始化 HTTP 客户端（调用 StablePay 后端）
    const client = new StablePayClient(cfg);

    // (3) 初始化运行时（管理本地钱包、OWS 签名、加密状态文件）
    const runtime = new StablePayRuntime(cfg);

    // (4) 注册 15 个工具给 LLM 调用 ↓
    api.registerTool({ name: "stablepay_runtime_status", ... });
    api.registerTool({ name: "stablepay_create_local_wallet", ... });
    api.registerTool({ name: "stablepay_bind_existing_wallet", ... });
    api.registerTool({ name: "stablepay_register_local_did", ... });
    api.registerTool({ name: "stablepay_configure_payment_limits", ... });
    api.registerTool({ name: "stablepay_build_payment_policy", ... });
    api.registerTool({ name: "stablepay_sign_message", ... });
    api.registerTool({ name: "stablepay_execute_paid_skill_demo", ... });
    api.registerTool({ name: "stablepay_pay_via_gateway", ... });
    api.registerTool({ name: "stablepay_generate_verify_link", ... });       // optional
    api.registerTool({ name: "stablepay_seed_mock_tweet", ... });            // optional
    api.registerTool({ name: "stablepay_verify_x_mock", ... });              // optional
    api.registerTool({ name: "stablepay_query_balance", ... });
    api.registerTool({ name: "stablepay_query_sales", ... });
    api.registerTool({ name: "stablepay_get_verify_status", ... });          // optional
  },
});
```

```
OpenClaw gateway 启动
  │
  ├─ 读取 openclaw.plugin.json        ← 发现插件 ID、配置项
  │
  ├─ npm 加载 dist/index.js           ← 插件 ES module
  │
  ├─ 执行 definePluginEntry({...})     ← 返回插件对象
  │
  ├─ gateway 调用 register(api)        ← api 是 gateway 注入的上下文
  │    │
  │    ├─ getPluginConfig(api)         ← 合并用户配置 + 环境变量 + 默认值
  │    ├─ new StablePayClient(cfg)     ← HTTP 客户端，所有请求发到 StablePay backend
  │    ├─ new StablePayRuntime(cfg)     ← 本地钱包管理、OWS 签名、加密状态持久化
  │    └─ api.registerTool(...) × 15   ← 每个工具 = { name, description, parameters, execute() }
  │
  ├─ LLM 对话时，AI 根据 description 选择调用哪个工具
  │    │
  │    └─ 工具 execute() 内部调用 client 或 runtime 完成操作
```

# 三、15 个工具的分组一览

| 分组 | 工具名 | 做的事情 |
| :--- | :--- | :--- |
| 钱包管理 | `stablepay_runtime_status` | 查本地运行时状态：用了哪个签名驱动、有没有钱包 |
| | `stablepay_create_local_wallet` | 创建新钱包（OWS SDK/CLI/REST） |
| | `stablepay_bind_existing_wallet` | 绑定 OWS 里已存在的钱包 |
| DID 注册 | `stablepay_register_local_did` | 把本地钱包注册到 StablePay DID Service，拿到 `did:solana:...` |
| 支付配置 | `stablepay_configure_payment_limits` | 设置单次限额 / 自动扣款阈值 |
| | `stablepay_build_payment_policy` | 构建付款策略（发给 Skill 的 offer） |
| 签名 | `stablepay_sign_message` | 用本地钱包对任意消息签名（用于验证身份） |
| 付款流程 | `stablepay_execute_paid_skill_demo` | 先 GET 执行 skill → 收到 402 → 查 price → 付款 → 重试 |
| | `stablepay_pay_via_gateway` | 给定 `skill_did` + price，直接走 x402 付款 |
| X 验证 | `stablepay_seed_mock_tweet` | 模拟一条推文（测试用） |
| | `stablepay_verify_x_mock` | 验证模拟推文 → 完成 DID 社交绑定 |
| | `stablepay_get_verify_status` | 查 DID 的 X 验证状态 |
| 查询 | `stablepay_query_balance` | 查 DID 余额（需要签名验证身份） |
| | `stablepay_query_sales` | 查某个 Skill 的销售记录 |
| | `stablepay_generate_verify_link` | 生成可分享的验证链接 URL |

每个工具的 `parameters` 用 `@sinclair/typebox` 定义 JSON Schema，gateway 用这套 schema 验证 LLM 传的参数是否合法。

# 四、内部架构：四大模块

## 1. `config.ts` — 配置合并层

```typescript
export function getPluginConfig(api): Required<PluginConfig>
```

合并优先级：**用户配置 > 环境变量 > 内置默认值**

例如 `feePayerSolanaAddress`：
1. 取 `api.pluginConfig.feePayerSolanaAddress`
2. 没设就取 `process.env.STABLEPAY_FEE_PAYER_SOL`
3. 还没设则用 `builtin_defaults.ts` 里的硬编码主网热钱包地址

```typescript
// builtin_defaults.ts
BUILTIN_FEE_PAYER_PUBKEY = "9Qe1uxmznPUnGcmLG7HSSsHcoC3cFxY54PPNAKTFnq2u";
BUILTIN_MAINNET_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
BUILTIN_CLIENT_MAINNET_RPC = "https://api.mainnet-beta.solana.com";
```

## 2. `client.ts` — HTTP 客户端

```typescript
class StablePayClient {
  async registerLocalDid(...)   // POST /api/v1/did/register
  async seedMockTweet(...)      // POST /api/v1/mock/twitter/tweets
  async verifyTwitter(...)       // POST /verify-twitter
  async getVerifyStatus(...)     // GET /verify?did=...
  async getBalance(...)          // GET /api/v1/balance → 需要签名认证
  async executeDemoSkill(...)    // GET 外部 skill URL → 捕获 402
  async initiatePayment(...)     // POST /api/v1/pay
  async fetchPayRequire(...)     // GET /api/v1/pay/require → 获取报价
  async getSales(...)            // GET /api/v1/sales
}
```

所有请求走到 `rawRequest()`，统一处理：
- 超时（`AbortController`，默认 90s）
- 状态码检查（允许部分 4xx 如 402 做业务逻辑）
- JSON 解析容错（`safeJsonParse`）

## 3. `runtime.ts` — 运行时（核心复杂）

这是最复杂的文件（~900 行），职责：

- **钱包状态管理**：加密存储到 `~/.stablepay-openclaw/stablepay-local-state.enc`（AES‑256‑GCM）
- **签名驱动探测**：`detectAvailability()` 按优先级检测
  - `ows-sdk`  (Node 进程内 `@open-wallet-standard/core`)   ← 默认
  - `ows-cli`  (PATH 上有 `ows` 命令)
  - `wsl-ows`  (WSL 里有 `ows`)
  - `ows-rest` (HTTP 签名服务)
- **三种签名路径**：
  - `OwsWalletProvider`（SDK）：`@open-wallet-standard/core` 的 `createWallet()` + `signMessage()`
  - `signWithOwsCli()` / `signSolanaMessageHexWithOwsCli()`：`spawn ows sign message --json`
  - `signWithOwsRestHex()`：POST JSON 到远程签名服务

## 4. `gateway_auth.ts` — DID 身份认证（签名）

当查询余额 / 销售记录时，StablePay API Gateway 要求 DID 签名认证。

```typescript
async function buildGatewayDidAuthHeaders(runtime, agentDid, method, path, rawQuery)
```

流程：
1. 构造 canonical 字符串：`${method}\n${path}\n${rawQuery}\n${sha256(emptyBody)}`
2. 用本地钱包签名（OWS SDK/CLI/REST）
3. 组装 headers：`X-StablePay-DID` + `X-StablePay-Signature` + `X-StablePay-Timestamp` + `X-StablePay-Nonce`

## 5. `tx_builder.ts` + `pay_settlement.ts` — 付款核心（x402 协议）

x402 = HTTP 402 Payment Required 的支付流程，大逻辑：

```
stablepay_pay_via_gateway / stablepay_execute_paid_skill_demo 被调用
  │
  ├─ (1) fetchPayRequire() → GET /api/v1/pay/require
  │       返回 { skill_did, price, currency, _x402 }
  │
  ├─ (2) 策略检查：单次限额 / 自动扣款阈值
  │       超限 → 返回 "manual_confirmation_required" 让 LLM 问用户
  │
  ├─ (3) buildPartiallySignedSplTransferTx()       ← tx_builder.ts
  │     ├─ 用 @solana/web3.js 构建 SPL Transfer 指令
  │     ├─ 用 OWS 签名 tx.serializeMessage()（买方签名）
  │     ├─ 嵌入 ed25519 签名到交易（fee payer 的签名留空）
  │     └─ 返回 signed_tx_base64
  │
  ├─ (4) 业务层签名：agentDid + skill_did + amount + txHash → 签名
  │
  ├─ (5) Gateway 层签名：POST body SHA256 → 签名
  │
  └─ (6) POST /api/v1/pay
         Headers: X-StablePay-DID + X-StablePay-Signature ... + X-Idempotency-Key
         Body: { agent_did, skill_did, amount, signed_tx_base64, signature, ... }
```

---

# 五、完整文件依赖关系图

```
index.ts  (插件入口)
  ├── config.ts          ──→ builtin_defaults.ts     (默认地址/额度的硬编码)
  ├── client.ts          ──→ types.ts               (所有接口类型)
  ├── runtime.ts         ──→ ows_sign_tx.ts         (OWS CLI 签名辅助)
  │                         └─ bind_verify.ts       (Ed25519 签名验证)
  ├── gateway_auth.ts    ──→ runtime.ts             (签名来自 runtime)
  ├── pay_settlement.ts  ──→ tx_builder.ts          (SPL 转账交易构建)
  │                         └─ builtin_defaults.ts  (USDC mint, RPC)
  ├── plugin_log.ts                                (日志工具)
  └── utils.ts                                     (小工具函数)
```

# 六、总结：宏观视角

这是典型的 **vibe coding** 产物 — 它的核心就是把 StablePay 的链上能力（创建 Solana 钱包、签名、USDC 转账、DID 注册、X 验证）打包成一组 LLM 能理解并调用的工具。

### 关键设计决策

| 决策 | 原因 |
| :--- | :--- |
| **15 个独立工具，而不是一个「万能工具」** | 每个工具职责单一，LLM 根据 `description` + `parameters` 精确匹配，减少幻觉 |
| **配置 + 环境变量 + 默认值三层合并** | 开发时零配置就能跑（全走内建测试参数），生产时通过 env 覆盖敏感值 |
| **三种 OWS 签名驱动** | 适配不同部署场景：`ows-sdk`（Node 进程内）、`ows-cli`（子进程）、`ows-rest`（远程 HTTP） |
| **部分签名（partial sign）** | 买方用自己的私钥签消息，fee payer 签名留空由 StablePay server 补上，平衡 **不暴露 fee payer 私钥** + **不要求买家付 SOL 当 gas** |
| **加密本地状态文件** | 钱包密钥材料不裸落在磁盘上，AES‑256‑GCM 加密，密钥来自环境变量 |
