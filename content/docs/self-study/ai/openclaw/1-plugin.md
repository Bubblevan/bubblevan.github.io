# 从 0 到 Agentic Payment Tooling：StablePay OpenClaw 插件开发笔记
那我问你，Skills和Plugin区别是什么？

我们需要先建立一个最小的心智模型！
## 1.1 Openclaw Plugin
从官方文档的角度看，OpenClaw 插件不是只能做一种事情。它是一种扩展机制，可以给 OpenClaw 增加不同类型的能力，例如：
1. Channel：把 OpenClaw 接到 Discord、飞书、Telegram 等消息平台。
2. Provider：增加新的模型提供商，或者接入自定义 LLM / Agent 后端。
3. CLI Backend：把本地 AI CLI 映射成 OpenClaw 可用的文本后端。
4. Tool：给 Agent 增加可以调用的工具。
5. Hook：参与 OpenClaw 的生命周期，例如工具调用前后、会话状态、运行时清理等。
6. HTTP Route / Gateway Method：给 Gateway 增加接口能力。

我们的 StablePay 插件目前最核心的形态是 **Tool Plugin**。

也就是说，它不是新增一个聊天平台，也不是新增一个模型 provider，而是把 StablePay 的支付能力注册成 OpenClaw Agent 可以调用的一组工具。

这组工具包括：
```text
stablepay_runtime_status
stablepay_doctor
stablepay_onboard
stablepay_create_local_wallet
stablepay_bind_existing_wallet
stablepay_register_local_did
stablepay_configure_payment_limits
stablepay_pay_via_gateway
stablepay_execute_paid_skill_demo
stablepay_query_balance
...
```
这些工具不是给人手动点按钮用的，而是给 LLM 在对话中根据用户意图选择调用的。

这就是 OpenClaw Tool Plugin 和普通后端接口最大的区别。

普通后端接口的调用方通常是程序员写的代码，而 OpenClaw Tool Plugin 的调用方往往是 Agent。Agent 会读工具名、工具描述、参数 schema、当前上下文，然后决定是否调用这个工具、如何填参数、下一步该怎么继续。

因此，体现 Agent 的一个落点在于：
- LLM 能不能知道什么时候该调用它？
- LLM 能不能知道参数从哪里来？
- 工具失败时，LLM 能不能知道下一步怎么修？
- 用户能不能看懂工具返回的信息？

## 1.2 Openclaw TUI
插件一般由 OpenClaw Gateway 加载和管理。可以把运行链路理解为：
```text
用户在 OpenClaw TUI / 飞书 / 其他入口发消息
        ↓
OpenClaw Agent 读取上下文和可用工具
        ↓
模型决定是否调用某个工具
        ↓
OpenClaw Gateway 调用对应插件工具
        ↓
插件执行本地逻辑或请求后端
        ↓
工具结果返回给 Agent
        ↓
Agent 继续回复用户或进行下一步工具调用
```
因此我一开始比较失望，这就像是某种中间件/Adapter而不是完整的Agent框架。
它一边面对 OpenClaw：
```text
注册工具
接收工具调用参数
返回结构化结果
```
另一边面对 StablePay 后端：
```text
调用 api-gateway
注册 DID
查询余额
构造支付请求
执行 402 支付接管
```
此外，它还面对本地环境：
```text
读取本地加密 state
管理 master.key
调用 OWS SDK / CLI / REST 签名
构造 Solana 交易
```
所以这个插件不是一个单纯的 HTTP client，它同时承担了三层职责：
1. OpenClaw 工具层：让 LLM 能调用。
2. StablePay 业务层：完成钱包、DID、支付、余额查询。
3. 本地 runtime 层：管理本地状态和签名能力。

理解这三层之后，再看项目结构就会清楚很多。

## 1.3 `package.json`
在一个 OpenClaw 插件项目里，`package.json` 首先还是一个 npm 包描述文件。它会声明：
```text
包名
版本号
模块类型
依赖
构建脚本
发布文件
OpenClaw 扩展入口
```
比如：
```json
"openclaw": {
  "extensions": [
    "./dist/index.js"
  ],
  "compat": {
    "pluginApi": ">=2026.3.1",
    "minGatewayVersion": "2026.3.1"
  },
  "build": {
    "openclawVersion": "2026.3.1",
    "pluginSdkVersion": "2026.3.1"
  }
}
```
这说明 OpenClaw 加载插件 runtime 时，会去找 `./dist/index.js`。因此每次改完记得`npm run build`一次。
> 这里又涉及到TS和JS的爱恨情仇了:
> src/   开发者写的 TypeScript 源码
> dist/  构建后给 OpenClaw 实际加载的 JavaScript 产物
> 这里略过来日再写。

## 1.4 `openclaw.plugin.json`
`openclaw.plugin.json` 是插件 manifest。它描述的是 OpenClaw 需要提前知道的插件元信息。它通常包括：
- 插件 id
- 插件名称
- 插件描述
- 插件版本
- 激活策略
- 工具契约
- optional 工具元数据
- 配置 schema
- UI hints

在旧版 OpenClaw 中，很多时候 Gateway 会通过 runtime 加载插件，然后执行 `register(api)`，从而知道插件注册了哪些工具。

但新版 OpenClaw 越来越强调静态发现。也就是说，OpenClaw 不应该每次都急切加载所有插件 runtime，才能知道每个插件提供哪些工具。为了实现这一点，runtime 注册的工具需要同步写进 manifest 的 `contracts.tools`。

这就形成了双轨机制：
| 版本 | 启动流程 | 工具发现方式 | 核心特点 |
| ---- | -------- | ------------ | -------- |
| 旧版 OpenClaw | 1. 运行 `dist/index.js`<br>2. 代码内执行 `register(api)` 完成注册 | 运行时调用 `api.registerTool` 动态感知、注册工具 | 工具发现依赖**代码运行**，动态注册 |
| 新版 OpenClaw | 1. 先读取配置文件 `openclaw.plugin.json`<br>2. 通过 `contracts.tools` 静态识别工具归属<br>3. 运行时再加载 `dist/index.js` | 优先通过配置文件**静态发现**工具，运行时再执行脚本逻辑 | 先静态解析配置，后加载运行代码，解耦工具声明与执行逻辑 |

这也是我们 0.3.17 manifest 版本要补 `contracts.tools` 的原因。

在这个项目里，manifest 里的工具列表必须和 `src/index.ts` 里实际 `api.registerTool` 注册的工具保持一致。否则就会出现两个问题：
1. manifest 里声明了工具，但 runtime 没注册：OpenClaw 以为工具存在，实际调用失败。
2. runtime 注册了工具，但 manifest 没声明：旧版能用，新版可能静态发现不到。

## 1.5 `src/index.ts`：插件真正的入口
如果说 `package.json` 告诉 OpenClaw 去哪里加载 runtime，`openclaw.plugin.json` 告诉 OpenClaw 插件长什么样，那么 `src/index.ts` 就是插件真正的业务入口。

一个典型的 OpenClaw 插件入口会使用：
```ts
definePluginEntry({
  id: "...",
  name: "...",
  description: "...",
  register(api) {
    // 在这里注册工具、provider、hook 等能力
  }
})
```
`register(api)` 是关键。OpenClaw Gateway 加载插件时，会调用这个函数，并传入一个 `api` 对象。插件通过这个 `api` 对象向 OpenClaw 声明自己能提供什么能力。

对 StablePay 插件来说，最重要的是：
```ts
api.registerTool(...)
```
每调用一次 `api.registerTool`，就注册一个 Agent 可以调用的工具。
工具通常包含：
- name：工具名
- label：展示名
- description：告诉 LLM 什么时候该用这个工具
- parameters：参数 schema
- execute：真正执行工具逻辑的函数

例如，一个简化版工具可以理解成：
```ts
api.registerTool({
  name: "stablepay_doctor",
  description: "诊断 StablePay 插件当前状态，检查网关、钱包、DID、支付限额和签名驱动。",
  parameters: Type.Object({}),
  async execute() {
    return await runDoctor(...)
  }
})
```
职责划分上：
```text
registerTool 负责把能力暴露给 OpenClaw
description 负责帮助 LLM 选择工具
parameters 负责约束 LLM 怎么填参数
execute 负责真正运行代码
```
这也是 OpenClaw 插件开发最核心的模式。
> BTW，README 不会被 LLM 当知识库。
### 1.5.1 README
| 使用主体 | 核心阅读/依赖内容 | 说明 |
| ---- | ---- | ---- |
| 人类（README 读者） | 开发者、使用者、ClawHub 浏览者、项目维护者、面试讲解对象 | 面向人做**功能介绍、使用指南、架构说明、场景讲解** |
| LLM（工具调用场景） | 工具名、工具描述(description)、参数 schema、对话上下文、工具返回结果、系统提示、平台工具目录 | 面向大模型做**指令解析、参数拼装、工具调用、结果承接** |

所以如果工具 description 写得很差，即使 README 写得很详细，LLM 仍然可能误用工具。

比如原来某些工具描述偏工程化：
```text
Query agent balance via GET /api/v1/balance. Signs the gateway canonical...
```
这对后端工程师可能有意义，但对 LLM 的工具选择不够友好。更好的写法应该是：
```text
查询当前已注册 DID 的 USDC 余额。需要先完成钱包绑定和 DID 注册。
```
这句话同时告诉 LLM 三件事：
1. 这个工具用于查询余额。
2. 查询的是当前 DID。
3. 前置条件是钱包绑定和 DID 注册。

### 1.5.2 TOOL PLUGIN
普通 SDK 的调用者是程序员，所以 SDK 可以暴露比较细的函数。
例如：
```
createWallet()
bindWallet()
registerDid()
configureLimits()
pay()
queryBalance()
```
程序员可以阅读文档，理解调用顺序，然后在代码里写好流程。

但 Agent 调工具时不是这样。LLM 面对的是自然语言任务：
```text
帮我初始化 StablePay 插件
帮我买一个测试商品
查一下我的余额
这个商品要 1 USDC，能不能付款？
```
如果我们只暴露一堆底层工具，LLM 就必须自己推理调用顺序：
```text
先 runtime_status？
还是先 create wallet？
MASTER_KEY 没有怎么办？
OWS SDK 和 CLI 选哪个？
DID 注册需要什么参数？
支付限额应该什么时候设置？
```
这就是为什么 StablePay 插件后来要从“原子工具集合”升级成“任务型工具层”。

原子工具仍然有价值，适合调试和高级用户：
```
stablepay_create_local_wallet
stablepay_register_local_did
stablepay_configure_payment_limits
stablepay_pay_via_gateway
```

但新手入口应该是任务型工具：
- `stablepay_doctor` 负责告诉 Agent 当前世界状态。
- `stablepay_onboard` 负责引导用户一步步完成初始化。

这就是 Agent-facing Tool Design 的核心：不是把所有后端 API 原样暴露给 LLM，而是把复杂业务流程重新设计成 LLM 容易选择、容易填参、容易恢复的工具。

## 1.6 小结
现在我可以更准确地描述这个项目了。
其运行链路可以写成：
```
OpenClaw Gateway
  加载 package.json 里的 openclaw.extensions
  运行 dist/index.js
  执行插件 register(api)
  注册 stablepay_* 工具
        ↓
OpenClaw Agent
  根据用户自然语言选择工具
  填充工具参数
  调用插件工具
        ↓
StablePay Plugin Runtime
  读取本地配置和 state
  调用 OWS SDK / CLI / REST 完成签名
  调用 StablePay api-gateway
  构造或提交支付请求
        ↓
StablePay 后端与链上系统
  DID 注册
  支付验证
  交易提交
  余额和销售查询
```
这个链路里，插件最重要的价值不是“我能不能发出 HTTP 请求”，而是：
1. 把 StablePay 的支付能力变成 Agent 可调用工具。
2. 把复杂初始化流程变成可恢复的多轮 onboarding。
3. 把支付动作放进 human-in-the-loop guardrail。
4. 把工具调用行为纳入 eval harness 进行测试。

所以咱不是插件，应该叫 **面向 OpenClaw Agent 的支付工具层（Agentic Payment Tooling for OpenClaw）** 更好听些（bushi）

如果面试官问我“OpenClaw 插件是什么”，我现在可以这样回答：
> OpenClaw 插件是一种扩展 OpenClaw Gateway 和 Agent 能力的机制。插件通过 manifest 描述静态信息，通过 runtime entry 加载 JavaScript 入口，并在 `register(api)` 中注册工具、provider、channel 或 hook。我的 StablePay 插件属于 Tool Plugin，它把钱包初始化、DID 注册、OWS 签名、402 支付接管、余额查询等能力封装成 LLM 可以调用的工具。后续我又把底层工具进一步组织成 `doctor` 和 `onboard` 这种任务型工具，让 Agent 能基于当前环境状态完成多轮初始化，而不是让用户手动照着 Quickstart 配置。

能够体现 Agent 味道的地方则在于，**优化工具 description 和参数 schema 对 Agent 行为表现的影响**。