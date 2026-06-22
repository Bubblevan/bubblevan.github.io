# 第二章：最小 MVP——先注册一个能跑的工具

第一章里，我先建立了一个基本心智模型：StablePay OpenClaw 插件本质上是一个 Tool Plugin。它不是直接把后端 API 暴露给用户，而是把 StablePay 的能力包装成 LLM 可以选择和调用的工具。

但是只理解概念还不够。真正开始写插件时，我最应该先做的不是支付，也不是钱包，也不是 Solana，而是一个最小 MVP：

**注册一个工具，让 OpenClaw 能看见它，让 LLM 能调用它，让它返回一个稳定的结果。**

这一章就围绕这个最小 MVP 展开。

如果这个环节没有跑通，后面所有复杂能力都会变得不可控。因为支付失败时，我无法判断到底是支付逻辑错了，还是插件根本没有被加载，还是工具 schema 写错，还是我改了源码但没有重新 build。

所以最小 MVP 的价值不是“功能简单”，而是帮我建立一条确定的运行链路。

---

## 2.1 为什么不能一上来就写支付？

我一开始很容易想直接写最终功能：

```text id="36w0bq"
用户：帮我买一个测试商品
插件：自动检查余额、签名、支付、重试后端
```

这个目标当然是最终要实现的，但它不适合作为第一个版本。

因为支付链路里同时涉及太多变量：

```text id="v4jz2z"
OpenClaw 插件有没有加载？
工具有没有注册成功？
LLM 有没有选对工具？
参数 schema 有没有写对？
StablePay 网关能不能访问？
本地 state 能不能读取？
OWS SDK 能不能签名？
DID 有没有注册？
钱包有没有 USDC？
Solana RPC 是否稳定？
后端是否正确返回 402？
```

如果一开始就做完整支付，一旦失败，我很难定位问题。

所以最小 MVP 应该只验证一件事：

```text id="fndd2n"
OpenClaw 能不能加载我的插件，并调用我注册的工具。
```

这就是为什么第一个工具最好是 `stablepay_runtime_status` 或一个更简单的 `hello` 工具。它不需要支付、不需要链上余额、不需要后端写入状态，只需要告诉我：

```text id="zbuw0n"
插件活着。
工具能被调用。
返回值能被 LLM 看到。
```

这个阶段的目标不是业务闭环，而是工程闭环。

---

## 2.2 最小工具应该长什么样？

一个最小工具至少需要这几部分：

```text id="fyyu90"
1. name：工具名，LLM 和 OpenClaw 用它识别工具。
2. description：工具说明，LLM 用它判断什么时候调用。
3. parameters：参数 schema，告诉 LLM 这个工具需要什么输入。
4. execute：真正执行逻辑的函数。
```

如果先不考虑 StablePay 业务，一个最小工具大概可以写成这样：

```ts id="sewggk"
api.registerTool({
  name: "stablepay_hello",
  label: "StablePay Hello",
  description: "测试 StablePay 插件是否已被 OpenClaw 正确加载。无需参数。",
  parameters: Type.Object({}),
  async execute() {
    return {
      content: [
        {
          type: "text",
          text: "StablePay 插件已加载，hello 工具调用成功。"
        }
      ],
      details: {
        ok: true,
        plugin: "stablepay-agentpay-dev"
      }
    };
  }
});
```

这个工具虽然没有业务价值，但它能验证最关键的链路：

```text id="bz3bs3"
src/index.ts 里注册工具
        ↓
npm run build 生成 dist/index.js
        ↓
OpenClaw Gateway 加载 dist/index.js
        ↓
LLM 发现 stablepay_hello
        ↓
LLM 调用工具
        ↓
工具返回结果
```

如果这个流程通了，说明插件开发的最小闭环已经建立。

当然，在真实项目里，我们不一定真的保留 `stablepay_hello`。StablePay 插件更自然的第一个工具是：

```text id="z9ym1m"
stablepay_runtime_status
```

因为它既能测试插件加载，又能返回当前 runtime 状态。

---

## 2.3 为什么第一个正式工具选择 runtime_status？

`stablepay_runtime_status` 的价值在于：它是一个低风险诊断工具。

它不修改状态，不发起支付，不创建钱包，不注册 DID。它只是告诉我插件当前看到的环境是什么。

一个合理的 runtime status 至少应该回答这些问题：

```text id="hk70ew"
1. 插件当前读取到的 backendBaseUrl 是什么？
2. 本地 state 文件路径是什么？
3. 当前有没有本地钱包？
4. 当前钱包名是什么？
5. 当前有没有 backend DID？
6. 当前配置的 OWS runtime 是什么？
7. 实际可用的签名 driver 是什么？
8. 支付限额有没有配置？
```

这类信息对两类对象都有用。

第一类是人，也就是我自己：

```text id="jaqqby"
我需要知道插件到底加载了哪份配置。
我需要知道本地 state 有没有读出来。
我需要知道钱包是不是已经存在。
```

第二类是 LLM：

```text id="k13oiv"
LLM 需要知道下一步应该创建钱包，还是注册 DID，还是查询余额。
```

这也是后来 `stablepay_doctor` 的基础。

`runtime_status` 更偏工程化，适合开发调试；`doctor` 更偏用户友好，适合对话式诊断。二者不是互相替代，而是抽象层级不同。

---

## 2.4 插件入口：src/index.ts

在 StablePay 插件里，最重要的入口文件是：

```text id="uggf3n"
src/index.ts
```

它大概承担这些职责：

```text id="nd5e0a"
1. 定义插件入口。
2. 读取插件配置。
3. 初始化 StablePayClient。
4. 初始化 StablePayRuntime。
5. 注册 stablepay_* 工具。
```

从学习角度看，我可以先把它理解成：

```ts id="eigbax"
export default definePluginEntry({
  id: "stablepay-agentpay-dev",
  name: "stablepay-agentpay-dev",
  description: "StablePay plugin for OpenClaw",
  register(api) {
    // 在这里注册工具
  }
});
```

`register(api)` 是整个插件最关键的生命周期函数。

OpenClaw Gateway 加载插件 runtime 后，会调用这个函数。插件在这个函数里通过 `api.registerTool(...)` 把能力注册给 OpenClaw。

所以如果我新增一个工具，通常就要改 `src/index.ts`：

```ts id="36ydjg"
api.registerTool({
  name: "stablepay_runtime_status",
  label: "StablePay Runtime Status",
  description: "查看 StablePay 插件当前状态，包括本地钱包、DID、支付限额和签名驱动。",
  parameters: Type.Object({}),
  async execute() {
    const status = await runtime.getStatus();
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(status, null, 2)
        }
      ],
      details: status
    };
  }
});
```

这段代码背后有几个关键点。

第一，`name` 要稳定。

工具名是 LLM 和 OpenClaw 识别工具的关键。如果工具名经常变，README、manifest、测试脚本、LLM 调用习惯都会跟着失效。

第二，`description` 不是普通注释。

它会影响 LLM 是否选择这个工具。写成“Query runtime JSON”这种工程描述，LLM 未必知道什么时候该用；写成“查看 StablePay 插件当前状态，包括钱包、DID、支付限额和签名驱动”，就更容易被模型选中。

第三，`parameters` 即使为空也要写清楚。

如果工具不需要参数，就写 `Type.Object({})`。这样模型知道调用时不需要填东西。

第四，`execute` 是真正执行逻辑的地方。

工具的业务逻辑不要全部堆在 `src/index.ts`，否则入口文件会越来越长。比较好的做法是：`index.ts` 负责注册工具，具体逻辑放到 `runtime.ts`、`client.ts`、`doctor.ts`、`onboard.ts` 等文件里。

---

## 2.5 TypeBox：工具参数 schema 怎么写？

OpenClaw 工具的参数 schema 通常会用 `@sinclair/typebox` 写。

例如，一个查询余额工具可能需要一个可选的 DID：

```ts id="dj3rlg"
parameters: Type.Object({
  agent_did: Type.Optional(
    Type.String({
      description: "要查询余额的 Agent DID。通常来自 stablepay_runtime_status 或 stablepay_onboard 的返回结果。"
    })
  )
})
```

这里的重点不是 TypeBox 语法本身，而是“参数 description 是写给 LLM 的”。

我以前容易把参数描述写成这样：

```ts id="9fl8d3"
description: "StablePay DID"
```

这对人也许够了，但对 LLM 不够。LLM 会不知道这个 DID 从哪里来，是用户手填，还是从上一步工具结果里拿。

更好的写法应该告诉模型：

```text id="yav0ov"
这个参数什么时候需要？
格式是什么？
通常从哪里来？
如果没有要不要留空？
```

比如：

```ts id="5gc2ma"
description: "可选。要查询余额的 Agent DID，格式为 did:solana:...。如果用户刚完成 stablepay_onboard，优先使用 onboard 返回的 backend_did；如果没有提供，工具会尝试使用当前本地钱包绑定的 DID。"
```

这就是 Agent-facing Tool Design 的细节。

普通 API 参数描述是给程序员看的；OpenClaw 工具参数描述要服务 LLM 填参。

---

## 2.6 工具返回值：message 给人，details 给 LLM

一个工具执行完之后，不能只返回一段随便的字符串。

对于 Agent 工具来说，返回值最好分成两层：

```text id="uj8wc7"
1. content / message：给用户看的自然语言结果。
2. details：给 LLM 继续推理用的结构化数据。
```

比如 `stablepay_runtime_status` 可以返回：

```json id="rr3zro"
{
  "has_wallet": true,
  "wallet": {
    "wallet_name": "stablepay-agent",
    "public_key": "..."
  },
  "backend_did": "did:solana:...",
  "payment_config": {
    "single_purchase_limit_usdc": 2,
    "auto_purchase_threshold_usdc": 0.5
  },
  "active_driver": "ows-sdk"
}
```

但直接把这坨 JSON 展示给新用户，体验并不好。新用户更希望看到：

```text id="q3ngd9"
StablePay 插件状态正常。

✅ 已绑定本地钱包：stablepay-agent
✅ 已注册 DID
✅ 已配置支付限额：单笔 2 USDC，自动支付阈值 0.5 USDC
✅ 当前签名驱动：内置签名驱动
```

所以更好的返回是：

```ts id="zpk3l4"
return {
  content: [
    {
      type: "text",
      text: humanReadableMessage
    }
  ],
  details: rawStatus
};
```

这样做有两个好处：

```text id="mf6pr3"
1. 用户看到的是清楚的中文状态。
2. LLM 拿到的是结构化 details，可以继续决定下一步工具调用。
```

这也是后来 `stablepay_doctor` 和 `stablepay_onboard` 的基本思想。

---

## 2.7 从 src 到 dist：为什么改完代码要 build？

这是我必须真正理解的一点。

我写的源码在：

```text id="lgf49l"
src/index.ts
src/runtime.ts
src/client.ts
...
```

但 OpenClaw 加载的是：

```text id="xlq2jo"
dist/index.js
```

也就是说，`src` 是开发者写的 TypeScript，`dist` 是构建后的 JavaScript runtime。

所以每次改完源码，我至少要执行：

```bash id="wjo5bh"
npm run check
npm run build
```

`npm run check` 负责 TypeScript 类型检查。它能帮我发现：

```text id="babmw7"
类型不匹配
参数拼错
import 路径错误
返回值结构不符合预期
```

`npm run build` 负责生成 OpenClaw 实际加载的 JavaScript 文件。

如果我只运行 `npm run check`，没有运行 `npm run build`，那么 `dist/index.js` 不会更新。OpenClaw Gateway 重启后仍然可能加载旧代码。

这就是插件开发里一个非常常见的错误：

```text id="0710n0"
我改了 src，但忘了 build。
```

为了避免这个问题，发布前应该形成固定流程：

```bash id="3bxsul"
npm run check
npm run build
npm run eval:tooluse
npm run check:manifest-tools
```

其中 `eval:tooluse` 和 `check:manifest-tools` 是后面演进出来的工程化检查。最小 MVP 阶段至少要先养成 `check + build` 的习惯。

---

## 2.8 manifest 里的工具声明：为什么新版还要写 contracts.tools？

最小工具注册在 `src/index.ts` 里，但新版 OpenClaw 还要求 runtime 注册的工具出现在 manifest 的 `contracts.tools` 里。

这件事一开始看起来有点重复：

```text id="0dyo8n"
明明 registerTool 已经注册工具了，为什么 manifest 里还要再写一遍？
```

原因在于：OpenClaw 不希望为了知道“某个插件有哪些工具”，就必须急切加载每个插件的 runtime 代码。

如果工具列表写在 manifest 里，OpenClaw 可以先静态读取：

```json id="2mobxq"
"contracts": {
  "tools": [
    "stablepay_runtime_status",
    "stablepay_doctor",
    "stablepay_onboard"
  ]
}
```

这样即使还没真正运行 `dist/index.js`，OpenClaw 也能知道这个插件声明了哪些工具。

这带来两个好处：

```text id="dqffxv"
1. 工具发现更快，不需要急切加载所有插件 runtime。
2. 插件能力更清晰，方便平台做配置校验、权限控制、工具归属判断。
```

但这也带来一个新问题：

```text id="2cx5fx"
manifest 里的 contracts.tools 必须和 runtime 里的 api.registerTool 保持一致。
```

否则会出现工具漂移：

```text id="wlj64f"
manifest 声明了工具，但 runtime 没注册。
runtime 注册了工具，但 manifest 没声明。
```

这就是为什么我们需要 `check:manifest-tools` 脚本。

它的职责不是业务逻辑，而是工程一致性检查：

```text id="ayir2d"
读取 src/index.ts 中的 registerTool 工具名
读取 openclaw.plugin.json 中的 contracts.tools
比较两边是否一致
如果不一致，直接失败
```

这个脚本对面试也很有价值，因为它说明我不只是能把功能写出来，还开始关注插件工程化和版本兼容。

---

## 2.9 本地安装和测试最小工具

最小 MVP 写完之后，不能只看 TypeScript 编译通过，还要真正让 OpenClaw 加载它。

一个典型测试流程是：

```bash id="kcbx02"
npm run check
npm run build
openclaw gateway restart
openclaw tui
```

进入 TUI 后，可以让模型调用工具：

```text id="gmh5pp"
请调用 stablepay_runtime_status，只返回工具结果。
```

如果工具能返回结果，说明几个条件都成立：

```text id="8k4ev4"
1. OpenClaw 找到了插件。
2. Gateway 成功加载 dist/index.js。
3. register(api) 被执行。
4. stablepay_runtime_status 被注册。
5. LLM 或 TUI 能调用这个工具。
6. execute 函数能正常返回结果。
```

如果失败，就按层排查。

第一层，插件有没有安装：

```bash id="ia4lbn"
openclaw plugins inspect stablepay-agentpay-dev --json
```

第二层，Gateway 有没有重启：

```bash id="6rhhb7"
openclaw gateway restart
```

第三层，dist 是否更新：

```bash id="fh8aem"
npm run build
```

第四层，工具名是否写错：

```text id="kj97x3"
manifest 里的 contracts.tools
src/index.ts 里的 registerTool name
LLM 调用时使用的工具名
```

这三处必须一致。

---

## 2.10 最小 MVP 到 StablePay 真实插件的演进

最小 MVP 只需要证明“工具能被调用”。但 StablePay 的真实插件要继续演进：

```text id="njjhl5"
第一步：stablepay_runtime_status
  证明插件已加载，runtime 可读。

第二步：stablepay_create_local_wallet / stablepay_bind_existing_wallet
  让插件具备钱包创建和绑定能力。

第三步：stablepay_register_local_did
  把本地钱包注册到 StablePay DID 服务。

第四步：stablepay_configure_payment_limits
  给支付动作加上安全边界。

第五步：stablepay_pay_via_gateway
  真正接管 402 支付流程。

第六步：stablepay_doctor
  把工程化状态翻译成用户可读、LLM 可用的诊断报告。

第七步：stablepay_onboard
  把一堆原子步骤组织成一个状态化初始化流程。

第八步：Tool-use Eval Harness
  评估 LLM 是否真的会正确选择和使用这些工具。
```

这条路径很重要。

如果我直接展示最终版本，别人可能只觉得项目复杂；但如果我能从最小 MVP 讲起，就能说明我是逐步建立工程抽象的：

```text id="s7i3lu"
先让工具能被调用。
再让工具能返回状态。
再让工具能修改状态。
再让工具能完成支付。
再让工具能被 LLM 稳定使用。
最后让工具调用行为可评估。
```

这就是从普通插件走向 Agentic Tooling 的过程。

---

## 2.11 第二章小结

这一章的重点是最小 MVP。

我不应该一上来就追求完整支付闭环，而应该先完成一个最小工具的注册、构建、加载和调用。

核心结论如下：

```text id="zg7gxx"
1. 最小 MVP 的目标是验证 OpenClaw 能加载插件，并调用我注册的工具。
2. 第一个正式工具适合选择 stablepay_runtime_status，因为它低风险、只读、方便排查。
3. api.registerTool 是 Tool Plugin 的核心接口。
4. 工具的 name、description、parameters、execute 分别承担不同职责。
5. description 和参数 schema 会影响 LLM 的工具选择和参数填充。
6. 工具返回值最好分成给用户看的 message 和给 LLM 用的 details。
7. OpenClaw 实际加载 dist/index.js，所以改完 src 后必须 npm run build。
8. 新版 manifest 里的 contracts.tools 要和 runtime 里的 registerTool 保持一致。
9. 最小工具跑通后，才能逐步叠加钱包、DID、支付、doctor、onboard 和 eval harness。
```

如果面试官问我“你是怎么从零开始做 OpenClaw 插件的”，我可以这样回答：

> 我没有一开始就写完整支付链路，而是先做了一个最小 Tool Plugin MVP。通过 `api.registerTool` 注册 `stablepay_runtime_status`，确认 OpenClaw Gateway 能加载 `dist/index.js`，LLM 能发现并调用工具，工具能返回结构化状态。这个阶段帮助我理解了插件入口、TypeScript 构建、manifest 工具声明和 LLM tool schema 的关系。之后我才逐步叠加钱包绑定、DID 注册、402 支付接管、doctor 诊断和 onboard 状态机。

这一章结束后，我至少应该能讲清楚：

```text id="eeq3vl"
1. 一个工具是怎么从 src/index.ts 暴露给 OpenClaw 的？
2. 为什么改完 TypeScript 后必须 build？
3. 为什么工具 description 和参数 schema 是 Agent 工程的一部分？
4. 为什么 runtime 注册和 manifest contracts.tools 要保持一致？
```

这就是 StablePay OpenClaw 插件从 0 到 1 的第一步。
