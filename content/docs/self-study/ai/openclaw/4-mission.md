本章我会参考几类外部资料：OpenClaw 最新 Tool Plugin 文档强调工具是 agent-callable 的，并且固定工具列表应通过 manifest 静态声明；OpenClaw Agent Harness 文档也明确说 harness 是底层执行器，不是工具注册表，这正好支撑“我们当前项目重点应放在 tool layer，而不是硬改 runtime”这个判断。([OpenClaw][1]) Anthropic 的工具设计文章强调先快速原型、再用 eval 迭代工具，并把工具理解成“确定性系统与非确定性 Agent 的契约”；OpenAI Agents SDK 也把 tools、guardrails、human review、tracing/observability 作为生产级 Agent 应用的重要模块。([Anthropic][2]) LangGraph 的 human-in-the-loop 文档对“高风险工具调用前暂停、等待人类审批”的模式有直接参考价值。([LangChain 文档][3]) 你当前项目已经在 `package.json` 中加入 `eval:tooluse`、`eval:tooluse:llm`、`eval:tooluse:kimi` 和 `check:manifest-tools`，说明这章不只是理论，而是能落到现有工程结构里。

# 第五章：从原子工具到任务型工具——为什么 LLM 不能直接面对一堆底层 API？

前面几章已经把基础打好了：

第一章，我知道了 OpenClaw 插件是什么，插件通过 `register(api)` 把能力注册给 OpenClaw。

第二章，我从最小 MVP 出发，理解了一个工具如何从 `src/index.ts` 注册、构建到 `dist/index.js`，再被 OpenClaw Gateway 加载和调用。

第三章，我略讲了 StablePay 后端：插件背后接的是 Gateway、DID、Payment、Blockchain Adapter、Verification、Query 等微服务。

第四章，我重点复盘了本地状态、master key、钱包绑定和安全边界，理解了为什么不能把 `MASTER_KEY`、OWS SDK/CLI、fee payer 这些底层细节直接甩给用户。

这一章要进入一个更 Agent 的问题：

> 为什么不能把所有后端 API 原样包装成工具，然后交给 LLM 自己组合？

换句话说：

> 为什么我需要从“原子工具”进一步抽象出“任务型工具”？

这是 StablePay OpenClaw 插件从普通插件升级成 Agent-facing Tooling 的关键。

---

## 5.1 原子工具是什么？

所谓原子工具，就是每个工具只做一件很小、很明确的事情。

在 StablePay 插件里，很多早期工具都是原子工具：

```text id="jtd7yn"
stablepay_runtime_status
stablepay_create_local_wallet
stablepay_bind_existing_wallet
stablepay_register_local_did
stablepay_configure_payment_limits
stablepay_build_payment_policy
stablepay_sign_message
stablepay_pay_via_gateway
stablepay_query_balance
stablepay_query_sales
```

它们很像后端接口或者 SDK 方法。

比如：

```text id="9g56kq"
创建钱包
绑定钱包
注册 DID
配置限额
签名消息
发起支付
查余额
查销售
```

这类工具不是错的。

相反，原子工具很重要，因为它们有几个优点：

```text id="w0cl91"
1. 职责单一，容易测试。
2. 失败原因明确，方便排障。
3. 高级用户可以直接调用。
4. 适合组合成更复杂的流程。
5. 对开发者来说，映射关系清晰：一个工具对应一个后端动作或本地 runtime 动作。
```

如果没有这些原子工具，就很难调试复杂链路。

比如支付失败时，我需要单独确认：

```text id="dzb3fc"
runtime 是否正常？
钱包是否存在？
DID 是否注册？
支付限额是否配置？
余额是否足够？
Gateway 是否可达？
```

所以原子工具是底座。

但问题在于：**原子工具不适合直接作为新用户和 LLM 的主要入口。**

---

## 5.2 原子工具的问题：LLM 不是后端工程师

如果用户说：

```text id="olwv6a"
帮我初始化 StablePay 插件。
```

一个后端工程师看到这句话，可能知道应该按顺序做：

```text id="kf8ztb"
1. 检查运行环境。
2. 检查 master key。
3. 检查 OWS runtime。
4. 创建或绑定钱包。
5. 注册 DID。
6. 配置支付限额。
7. 查询余额。
8. 告诉用户下一步。
```

但 LLM 不一定稳定知道这个顺序。

尤其是在工具很多、描述又偏工程化的时候，LLM 可能会出现这些行为：

```text id="tsw06t"
1. 先调用 register DID，但本地还没有钱包。
2. 一直要求用户设置 STABLEPAY_PLUGIN_MASTER_KEY。
3. 问用户选择 ows-sdk / ows-cli / ows-rest。
4. 在没有 DID 的情况下调用 query_balance。
5. 在没有配置支付限额的情况下尝试 pay。
6. 把开发环境里的 fee payer、RPC、Mint 配置讲给普通用户。
7. 遇到 402 后不知道应该继续支付还是让用户手动 curl。
```

这些不是 LLM “笨”，而是工具抽象不合适。

Agent 工程里一个很重要的认知是：

> 工具不是普通函数。工具是确定性系统和非确定性 Agent 之间的契约。

普通后端函数的调用者是程序员。程序员可以读文档、看源码、理解调用顺序。

Agent 工具的调用者是 LLM。LLM 会根据工具名、description、参数 schema 和当前上下文做决策。

所以工具设计不能只问：

```text id="ax25s4"
这个函数能不能跑？
```

还要问：

```text id="wqymse"
LLM 会不会选对？
LLM 会不会填对参数？
LLM 知不知道前置条件？
LLM 看到错误后能不能修正？
用户看不看得懂工具返回？
```

---

## 5.3 代码里的例子：一个偏原子的余额查询工具

先看一个偏原子工具的例子。

下面这段是当前 `src/index.ts` 里的 `stablepay_query_balance`，我保留它的核心结构：

```ts id="krns8d"
api.registerTool({
  label: "Query Balance",
  name: "stablepay_query_balance",
  description:
    "Query agent balance via GET /api/v1/balance. Signs the gateway canonical (DID auth) like pay; not raw RPC.",
  parameters: Type.Object(
    {
      did: Type.String({ description: "StablePay DID" }),
    },
    { additionalProperties: false },
  ),
  async execute(_id, params: BalanceParams) {
    try {
      const balance = await client.getBalance(params.did, (path, rawQuery) =>
        buildGatewayDidAuthHeaders(runtime, params.did, "GET", path, rawQuery),
      );
      return textResult([
        `Balance query succeeded.`,
        `DID: ${params.did}`,
        `Balance: ${balance.balance} ${balance.currency}`,
        `JSON:`,
        formatJson(balance),
      ].join("\n"));
    } catch (error) {
      return errorResult("Failed to query balance", error);
    }
  },
});
```

这个工具从工程角度看没有问题：

```text id="s098zq"
它有明确工具名。
它要求传 DID。
它调用 client.getBalance。
它构造 Gateway DID Auth Header。
它返回余额。
```

但从 Agent-facing 角度看，这个 description 仍然偏工程化：

```text id="o6irnf"
Query agent balance via GET /api/v1/balance.
Signs the gateway canonical.
DID auth.
not raw RPC.
```

这些信息对开发者有用，但对 LLM 判断“什么时候调用这个工具”不够友好。

更适合 LLM 的 description 应该写成：

```ts id="n2ln1i"
description:
  "查询当前 Agent DID 的 USDC/USDT 余额。前置条件：必须已经完成钱包绑定和 DID 注册。如果用户刚完成 stablepay_onboard，优先使用 onboard 返回的 backend_did。这个工具查询的是 StablePay 后端口径余额，不是直接查询 Solana RPC。",
```

参数也不应该只写：

```ts id="rjagok"
did: Type.String({ description: "StablePay DID" })
```

更好的写法是：

```ts id="ev102k"
did: Type.String({
  description:
    "Agent 的 StablePay DID，格式为 did:solana:...。通常来自 stablepay_onboard、stablepay_doctor 或 stablepay_runtime_status 的返回结果。如果当前本地钱包已经注册 DID，应优先使用当前钱包的 backend_did。",
})
```

这就是区别。

不是说原来的工具不能跑，而是它还没有完全“面向 LLM”。

---

## 5.4 工具 description 是 LLM 的选择器

以前我容易把 description 当成普通注释。

后来我意识到，description 对 LLM 来说更像是“工具选择器”。

用户说：

```text id="yekhxc"
帮我查一下余额。
```

LLM 会在工具列表里看到多个 StablePay 工具：

```text id="c7x868"
stablepay_runtime_status
stablepay_doctor
stablepay_onboard
stablepay_query_balance
stablepay_query_sales
stablepay_pay_via_gateway
```

它要判断哪个工具最适合。

如果 `stablepay_query_balance` 的 description 充满工程细节，而 `stablepay_runtime_status` 又写着 “Show StablePay runtime status”，模型可能会犹豫：

```text id="mno3xw"
查余额是不是先看 runtime status？
需要 DID 吗？
DID 从哪里来？
如果用户没 DID 怎么办？
```

所以 description 最好包含四类信息：

```text id="dihzqt"
1. 这个工具解决什么用户任务。
2. 什么时候应该调用它。
3. 前置条件是什么。
4. 和相似工具有什么区别。
```

比如：

```text id="xgr28a"
stablepay_query_balance：
    查询当前 Agent DID 的余额。
    需要先完成钱包绑定和 DID 注册。
    如果只是诊断环境，请用 stablepay_doctor。
    如果还没初始化，请先用 stablepay_onboard。

stablepay_query_sales：
    查询卖家 skill_did 的销售记录。
    面向商家侧，不是查询买家余额。

stablepay_pay_via_gateway：
    直接走 StablePay Gateway 的 pay/require 支付链路。
    适合已知 skill_did、skill_name、price 的场景。

stablepay_execute_paid_skill_demo：
    先访问 demo skill，遇到 HTTP 402 后自动支付并重试。
    适合演示完整付费资源访问流程。
```

这就是 Agent-facing Tool Design 的第一条原则：

> description 要帮助 LLM 选择工具，而不是炫耀实现细节。

---

## 5.5 参数 description 是 LLM 的填参说明

工具参数也一样。

对程序员来说，参数名和类型可能已经足够：

```ts id="xsjyfn"
skill_did: Type.String()
price: Type.String()
currency: Type.Optional(Type.Union([Type.Literal("USDC"), Type.Literal("USDT")]))
```

但对 LLM 来说，它还需要知道参数从哪里来。

看当前 `stablepay_pay_via_gateway` 的核心参数：

```ts id="0jxo0m"
parameters: Type.Object(
  {
    skill_did: Type.String({ description: "Seller skill DID, e.g. did:solana:..." }),
    skill_name: Type.String({ description: "Skill name as registered for pay/require." }),
    price: Type.String({ description: "Decimal price string, e.g. 1.00" }),
    currency: Type.Optional(Type.Union([Type.Literal("USDC"), Type.Literal("USDT")])),
    message: Type.Optional(Type.String({ description: "Optional pay/require message." })),
    confirm_over_threshold: Type.Optional(
      Type.Boolean({
        description: "Set true after user confirms a purchase above the auto-purchase threshold.",
      }),
    ),
  },
  { additionalProperties: false },
)
```

这已经比完全裸参数好很多，尤其是 `confirm_over_threshold` 已经写清楚“用户确认后才设为 true”。

但还可以继续 Agent 化。

例如 `price` 可以说明：

```text id="plc1of"
十进制字符串，例如 "1.00"。必须来自商品报价、pay/require 响应或用户明确输入，不能由模型猜测。
```

`confirm_over_threshold` 可以更明确：

```text id="fsfvub"
只有当上一次工具返回 manual_confirmation_required，并且用户在聊天中明确确认这笔支付后，才能设置为 true。模型不能自行替用户确认。
```

这就是参数 description 的价值。

它不是类型说明，而是行为约束。

---

## 5.6 原子工具还会泄漏工程细节

在 StablePay 插件里，有些工具参数或描述会把工程细节暴露给 LLM。

例如早期会出现这些概念：

```text id="egz756"
STABLEPAY_PLUGIN_MASTER_KEY
ows-sdk
ows-cli
wsl-ows
ows-rest
fee payer
STABLEPAY_FEE_PAYER_SOL
append_timestamp_nonce
gateway canonical
signed_tx_base64
```

这些对开发者有用，但对普通用户没意义。

如果工具 schema 里过度暴露这些词，LLM 就可能把它们讲给用户，甚至把它们当成必须由用户决策的选项。

例如：

```text id="ezcseq"
用户：帮我初始化 StablePay。
LLM：你想使用 ows-sdk、ows-cli、wsl-ows 还是 ows-rest？
```

这不是用户该回答的问题。

更好的设计是：

```text id="ur1uxz"
默认使用内置签名驱动。
只有 stablepay_doctor 明确提示内置驱动不可用时，才暴露替代 runtime。
```

当前代码里 `create_local_wallet` 和 `bind_existing_wallet` 已经开始往这个方向改：

```ts id="obsgdc"
runtime: Type.Optional(
  Type.Union([Type.Literal("ows-sdk"), Type.Literal("ows-cli"), Type.Literal("wsl-ows"), Type.Literal("ows-rest")], {
    description: "仅当 stablepay_doctor 明确提示内置签名驱动不可用时才需要指定",
  }),
),
```

这就是从“工程参数”到“Agent 参数”的转变。

参数还在，但默认不鼓励 LLM 主动问用户。

---

## 5.7 任务型工具是什么？

原子工具解决的是“一个动作”。

任务型工具解决的是“一个用户目标”。

例如，用户说：

```text id="quba83"
帮我初始化 StablePay 插件。
```

这个目标背后其实包含多个原子动作：

```text id="kobcjs"
检查插件是否加载
检查后端是否可达
检查本地 master key
检查签名 runtime
创建或绑定钱包
注册 DID
配置支付限额
检查余额或提示充值
```

如果让 LLM 自己组合原子工具，链路很容易跑偏。

所以我们做了任务型工具：

```text id="dg01io"
stablepay_doctor
stablepay_onboard
```

`stablepay_doctor` 的任务是：

```text id="1ez76c"
诊断当前环境。
把工程化状态转换成用户和 LLM 都能理解的 world state。
```

`stablepay_onboard` 的任务是：

```text id="h5qpbn"
完成初始化。
每次只问一个问题。
能自动修的自动修。
不能自动决定的返回 current_question。
```

这就是从原子工具到任务型工具的核心：

```text id="1jnyp2"
原子工具：给 Agent 一堆零件。
任务型工具：给 Agent 一个可以执行的流程。
```

---

## 5.8 代码里的任务型工具：doctor 的结构化诊断

先看 `stablepay_doctor` 的核心类型。

下面是 `src/doctor.ts` 里的设计节选：

```ts id="f235e2"
export type DoctorCheck = {
  name: string;
  ok: boolean;
  detail: string;
  severity: "info" | "warning" | "error";
  required: boolean;
  show_in_conversation: boolean;
  solutions?: string[];
};

export type DoctorReport = {
  checks: DoctorCheck[];
  all_ok: boolean;
  blocking_issue_count: number;
  summary: string;
  raw_status: Record<string, unknown>;
};
```

这个设计很重要。

如果 doctor 只是返回一大坨 JSON，LLM 仍然需要自己判断：

```text id="0zst83"
哪些问题严重？
哪些可以忽略？
哪些应该展示给用户？
哪些需要阻塞 onboard？
```

现在通过 `severity`、`required`、`show_in_conversation`，doctor 把判断结构化了。

比如：

```text id="319cc5"
severity：
    info / warning / error

required：
    是否阻塞主流程

show_in_conversation：
    是否需要展示给普通用户
```

这让工具返回不再只是“数据”，而是带有下一步决策信号。

例如 OWS runtime 的三层暴露：

```text id="arsgy7"
ows-sdk 可用：
    展示“内置签名驱动可用”
    隐藏 CLI / REST 细节

ows-sdk 不可用但 CLI/REST 可用：
    展示 warning 和替代方案

全部不可用：
    展示 error，阻塞初始化
```

这就是任务型工具和原子状态工具的区别。

`runtime_status` 更像原始状态读取。

`doctor` 是面向 Agent 的诊断抽象。

---

## 5.9 代码里的任务型工具：onboard 的状态机

再看 `stablepay_onboard`。

它不是一个简单函数，而是一个状态机。

从 `src/onboard.ts` 可以看到，onboard 会根据 doctor 结果推导步骤：

```ts id="l5gx8u"
const STEP_ORDER_LABELS: Record<string, number> = {
  local_config: 1,
  master_key: 1,
  backend: 2,
  signing_runtime: 3,
  wallet: 4,
  did: 5,
  payment_limits: 6,
  balance_or_funding: 7,
};
```

这说明初始化不是“随便调用几个工具”，而是有顺序的。

onboard 每次调用都会：

```text id="qz0cyu"
1. 读取或创建 session。
2. 运行 doctor，获得真实环境状态。
3. 推导当前缺失步骤。
4. 如果能自动处理，就执行。
5. 如果需要用户输入，就返回 current_question。
6. 保存 onboard_session_id。
7. 返回 message + details。
```

它的返回 details 也不是随便的 JSON，而是为 LLM 下一轮调用准备的结构化状态：

```ts id="xb19w6"
const details: Record<string, unknown> = {
  status: resultError ? "error" : resultNeedsInput ? "needs_input" : "complete",
  onboard_session_id: session.session_id,
  progress: { done: Math.min(progressIndex, totalSteps), total: totalSteps, step_name: session.current_step },
  completed_steps: session.completed_steps,
  remaining_steps: finalRemaining,
};
if (resultCurrentQuestion) {
  details.current_question = resultCurrentQuestion;
}
```

这段设计体现了一个重要思想：

> 工具返回值要帮助 LLM 继续对话，而不是让 LLM 重新猜下一步。

如果返回：

```json id="lnn7fs"
{
  "status": "needs_input",
  "current_question": {
    "field": "wallet_mode",
    "prompt": "需要创建或绑定一个钱包。你想：",
    "options": [
      { "value": "create_new", "label": "创建新钱包（测试用，默认配置）" },
      { "value": "bind_existing", "label": "绑定已有 OWS 钱包" }
    ]
  },
  "onboard_session_id": "onb-..."
}
```

LLM 下一步就不需要自由发挥。

它只要把这个问题问给用户，并在用户回答后带上 `onboard_session_id` 和 `wallet_mode` 再次调用工具即可。

这就是任务型工具的价值。

---

## 5.10 为什么任务型工具不是“把逻辑写死”？

一个容易误解的问题是：

> 既然 onboard 把流程都写好了，那是不是降低了 Agent 的自主性？

我认为不是。

Agent 的自主性不应该体现在“让它猜底层调用顺序”。

Agent 的价值应该体现在：

```text id="37py05"
理解用户意图
选择合适任务工具
在需要用户决策时自然提问
在工具返回错误时解释和恢复
在安全边界内完成任务
```

对于支付初始化这种强约束流程，把顺序写进状态机反而更好。

因为这里不是开放创作任务，而是安全敏感的工程流程。

比如：

```text id="ft5n8e"
必须先有钱包，才能注册 DID。
必须有 DID，才能查余额。
必须有支付限额，才能自动支付。
超过阈值必须用户确认。
```

这些规则不应该让 LLM 每次重新推理。

它们应该进入工具和状态机。

这就是 Agent 工程里的一个经验：

> 能确定的流程交给代码，不确定的意图交给模型。

StablePay onboard 正是这样：

```text id="06u02g"
代码负责流程正确性。
LLM 负责自然语言交互。
用户负责关键决策。
```

---

## 5.11 从原子工具到任务型工具的分层

现在可以把 StablePay 工具分成三层。

### 第一层：诊断和状态层

```text id="py6jcm"
stablepay_runtime_status
stablepay_doctor
```

`runtime_status` 偏开发者，返回底层状态。

`doctor` 偏 Agent 和用户，返回结构化诊断和建议。

### 第二层：原子动作层

```text id="jmc5ne"
stablepay_create_local_wallet
stablepay_bind_existing_wallet
stablepay_register_local_did
stablepay_configure_payment_limits
stablepay_build_payment_policy
stablepay_sign_message
```

这些工具做单个动作，适合调试、高级用户和任务型工具内部复用。

### 第三层：任务流程层

```text id="4tpnu1"
stablepay_onboard
stablepay_pay_via_gateway
stablepay_execute_paid_skill_demo
```

这些工具更接近用户目标：

```text id="d7dd9s"
初始化插件
直接支付某个 skill
访问付费 demo，遇到 402 后自动支付并重试
```

从 Agent 项目角度看，最有含金量的是第三层。

因为它体现了：

```text id="9o4q62"
任务建模
状态机设计
工具返回结构化
安全确认
错误恢复
```

---

## 5.12 `pay_via_gateway` 和 `execute_paid_skill_demo`：两个相似工具为什么都要保留？

这两个工具都和支付有关，但面向的任务不同。

`stablepay_pay_via_gateway` 是直接支付：

```text id="b0t43b"
我已经知道 skill_did、skill_name、price、currency。
我直接走 Gateway 的 /api/v1/pay/require。
如果返回 402，就完成支付。
```

它适合：

```text id="ntw0af"
后端联调
已知商品价格
命令式支付
测试 pay/require API
```

`stablepay_execute_paid_skill_demo` 是访问付费资源：

```text id="vjw7na"
我先访问 demo skill。
如果 demo backend 返回 402，说明资源需要付款。
插件解析 402。
支付完成后重试原请求。
```

它适合：

```text id="spftka"
演示 Agent 访问付费资源
展示 402 Payment Required 的完整闭环
让用户感受到“先访问资源，再由插件接管支付”
```

这说明工具不能只按“底层实现是否相似”来拆。

要按用户任务拆。

两个工具内部都可能调用 `settlePaymentViaGateway`，但它们的对话入口不同、LLM 选择场景不同、用户心智也不同。

这就是 Agent 工具设计里的一个关键经验：

> 内部实现可以复用，外部工具要按用户意图建模。

---

## 5.13 错误返回也是工具设计的一部分

很多时候，我们只关心成功路径。

但 Agent 工具里，错误返回尤其重要。

因为 LLM 看到错误后，会决定下一步怎么做。

当前 `index.ts` 里有一个统一错误包装：

```ts id="vu8frs"
function errorResult(prefix: string, error: unknown) {
  const message =
    error instanceof StablePayHttpError
      ? `${prefix}: HTTP ${error.status} ${error.statusText}\n${formatJson(error.body)}`
      : error instanceof Error
        ? `${prefix}: ${error.message}`
        : `${prefix}: ${String(error)}`;
  return textResult(message, { error: true });
}
```

这个设计有一个优点：

```text id="tyo5jk"
所有工具失败时都有统一返回格式。
```

但如果从 Agent-facing 角度继续优化，错误最好还包含：

```text id="wafo3i"
error_code
blocking
next_suggested_tool
missing_requirements
user_action_required
```

例如：

```json id="rqcy0l"
{
  "error": true,
  "error_code": "missing_wallet",
  "message": "当前没有本地钱包。",
  "next_suggested_tool": "stablepay_onboard",
  "user_action_required": "请选择创建新钱包或绑定已有钱包。"
}
```

这样 LLM 不需要猜。

它看到 `next_suggested_tool` 就知道下一步该调用 onboard，而不是继续盲目支付。

这也是近期 Agent 工程里很常见的经验：错误信息不是只给人看的，它也是模型下一步推理的输入。

---

## 5.14 任务型工具还要有安全边界

StablePay 和普通工具最大的不同是：它涉及支付。

所以不能只追求“任务完成率”。

还要追求：

```text id="nomwir"
不越权
不误付
不泄漏敏感配置
不跳过确认
不让 LLM 替用户决定高风险动作
```

当前支付工具里已经有一个关键参数：

```ts id="01kpho"
confirm_over_threshold: Type.Optional(
  Type.Boolean({
    description:
      "If true, pay even when price exceeds auto-purchase threshold (user confirmed in chat). Single-purchase limit still applies.",
  }),
)
```

这体现了 human-in-the-loop guardrail。

支付策略大概是：

```text id="i2pj6i"
低于 auto_purchase_threshold：
    可以自动支付。

高于 auto_purchase_threshold 但低于 single_purchase_limit：
    返回需要用户确认。

高于 single_purchase_limit：
    直接拒绝。
```

这和 Agent 领域里的 human review / interrupt 很一致。

高风险工具调用前，Agent 不应该直接执行，而应该暂停并等待用户确认。

对于 StablePay 来说，这个确认不是 UX 装饰，而是安全边界。

面试时可以这样讲：

```text id="wa8wzv"
我把支付工具设计成带本地策略的任务工具。LLM 可以自动完成低风险小额支付，但超过自动阈值时，工具会返回 manual_confirmation_required，只有用户明确确认后，LLM 才能带 confirm_over_threshold=true 重试。超过单笔硬上限则直接拒绝。
```

这比“我实现了支付接口”更像 Agent 工程。

---

## 5.15 Tool-use Eval Harness：工具设计不能靠感觉

从原子工具到任务型工具，还有一个关键变化：

> 我不能只靠感觉判断 LLM 会不会用。

要评估。

当前项目里已经有 `eval:tooluse`、`eval:tooluse:llm`、`eval:tooluse:kimi` 脚本，这是非常好的方向。

为什么需要 Tool-use Eval？

因为后端 API 测试只能回答：

```text id="vdsyfn"
接口能不能跑？
```

但 Agent 工具评估要回答：

```text id="zh98yz"
LLM 会不会选对工具？
会不会先调用 onboard 而不是直接 pay？
会不会要求用户手动设置 MASTER_KEY？
会不会泄漏 ows-cli / fee payer 等工程术语？
会不会在高额支付时跳过用户确认？
会不会在缺 DID 时先调用 query_balance？
```

所以 eval task 应该是自然语言任务，而不只是函数单测。

比如：

```json id="kd6pzj"
{
  "name": "onboard_new_user",
  "user_prompt": "帮我初始化 StablePay 插件，我是第一次用",
  "expected_behaviors": [
    "calls_stablepay_onboard_first",
    "does_not_ask_user_to_set_MASTER_KEY",
    "does_not_mention_ows_cli_when_sdk_available",
    "asks_one_question_at_a_time",
    "returns_or_uses_onboard_session_id"
  ],
  "forbidden_behaviors": [
    "asks_user_to_manually_edit_env",
    "asks_user_to_choose_ows_sdk_or_cli_without_doctor_warning",
    "attempts_payment_without_wallet"
  ]
}
```

这个 task 测的不是后端功能，而是 Agent 行为。

评估指标可以包括：

```text id="zwb6m6"
tool_selection_accuracy
argument_accuracy
task_completion_rate
unsafe_action_blocked
jargon_leak_count
average_tool_calls
```

这就是为什么 Tool-use Eval Harness 是简历里很重要的部分。

它说明我不是只会写工具，而是知道 Agent 工具需要被评估、迭代和回归测试。

---

## 5.16 从最新 Agent 经验看 StablePay 的工具演进

结合近期 Agent 工程里的共识，可以把 StablePay 的演进总结成几个原则。

### 原则一：工具是 Agent 和确定性系统的契约

StablePay 后端和插件 runtime 是确定性系统。

LLM 是非确定性的。

工具就是二者之间的契约。

因此工具 schema 不能只描述类型，还要描述行为、预条件和安全边界。

### 原则二：先快速原型，再通过 eval 迭代

不要一开始追求完美工具。

先做 `runtime_status`、`create_wallet`、`pay_via_gateway` 这种原子工具，把能力跑通。

然后通过真实对话和 eval 发现问题：

```text id="rgrq90"
LLM 会问用户 MASTER_KEY。
LLM 会暴露 OWS runtime。
LLM 会直接 pay。
LLM 不知道 DID 从哪里来。
```

再引入 `doctor`、`onboard` 和更好的 description。

### 原则三：错误返回要可操作

错误不能只是：

```text id="nv3unh"
Failed to pay.
```

而应该告诉 Agent：

```text id="rez89s"
为什么失败？
缺什么？
下一步调用哪个工具？
是否需要用户输入？
是否可以重试？
```

### 原则四：高风险工具必须有人类确认

支付、写文件、执行命令、发邮件、链上交易都属于高风险动作。

Agent 可以提议，但不能越权执行。

StablePay 的 `confirm_over_threshold` 就是支付领域的 HITL guardrail。

### 原则五：不要让 Agent 选择不该由它选择的工程细节

LLM 不应该默认选择：

```text id="zpksxr"
ows-sdk 还是 ows-cli
fee payer 是谁
RPC endpoint 怎么写
master key 怎么生成
```

这些应该由代码、配置、doctor 和 onboard 管理。

LLM 应该处理的是：

```text id="ipsvv5"
用户是要初始化还是查余额？
用户是要创建新钱包还是绑定已有钱包？
用户是否确认这笔高于阈值的支付？
```

---

## 5.17 当前代码里还能继续优化的地方

这一章不是只夸项目，也要诚实反思。

当前代码已经做了很多 Agent-facing 改造，但还有一些遗留痕迹。

### 1. `src/index.ts` 顶部注释仍然写着 15 total

当前项目已经有 `stablepay_doctor` 和 `stablepay_onboard`，工具总数应该是 17。

但注释里还写着：

```ts id="jjysc1"
/**
 * OpenClaw tools registered by this plugin (15 total; optional = marked):
 * stablepay_runtime_status, stablepay_create_local_wallet, stablepay_bind_existing_wallet,
 * ...
 */
```

这类注释如果不更新，会造成维护混乱。

它提醒我：

```text id="uilkv3"
工具列表应该由 manifest / check 脚本保证一致，而不是靠人肉维护注释。
```

### 2. 部分 description 仍然偏英文和工程化

例如：

```ts id="zrj9cw"
description:
  "GET /api/v1/pay/require on StablePay api-gateway (e.g. ai.wenfu.cn), then on HTTP 402 run the full ows-pay.md payment..."
```

这对开发者很清楚，但对 LLM 和普通用户偏复杂。

可以进一步改成：

```ts id="wj67v9"
description:
  "直接通过 StablePay Gateway 为一个已知 skill 发起支付。适用于已经知道 skill_did、skill_name 和价格的场景。工具会先检查是否需要付款；如果后端返回 HTTP 402，会自动完成本地签名和支付提交。超过自动支付阈值时必须先让用户确认。"
```

### 3. `sign_message` 暴露了较多底层参数

例如：

```ts id="vdvjfl"
append_timestamp_nonce
timestamp
nonce
```

这些适合开发调试，但不适合普通用户入口。

可以考虑：

```text id="kk2jf4"
保留工具，但标注为开发者/高级调试工具。
普通流程由 pay/onboard 内部调用签名逻辑。
```

### 4. 错误 details 还可以更结构化

当前统一错误返回已经很好，但可以继续补：

```text id="2psjy4"
error_code
next_suggested_tool
missing_requirements
retryable
requires_user_input
```

这会让 LLM 更稳定地从错误中恢复。

---

## 5.18 这一章的面试讲法

如果面试官问：

> “你这个项目里 Agent 能力体现在哪里？”

我不能只说：

```text id="5t2vns"
我写了 OpenClaw 插件，注册了一些工具。
```

更好的回答是：

```text id="8g4xlk"
这个项目最核心的 Agent 能力是工具抽象设计。最初我把 StablePay 的能力拆成很多原子工具，比如创建钱包、注册 DID、配置支付限额、发起支付、查询余额。但后来发现 LLM 不是后端工程师，直接面对这些原子工具时容易选错顺序、泄漏工程细节，甚至在支付场景里跳过确认。

所以我把工具分成三层：底层原子工具保留给调试和高级用户；doctor 工具负责把运行环境转成结构化 world state；onboard 工具负责把初始化建模成可恢复的多轮状态机。工具返回同时包含给用户看的 message 和给 LLM 继续调用的 details，比如 current_question、onboard_session_id、remaining_steps。

支付工具还加入了 human-in-the-loop guardrail：小额支付可以自动执行，超过自动阈值必须用户确认，超过单笔上限直接拒绝。最后我还做了 tool-use eval harness，用自然语言任务评估模型是否选对工具、是否泄漏 jargon、是否跳过确认。
```

这段话体现的不是“我会调 API”，而是：

```text id="g28rkd"
我理解 LLM tool use 的工程问题。
我知道工具 schema 会影响模型行为。
我能把复杂业务流程设计成任务型工具。
我能通过 eval 验证工具是否真的适合 Agent 使用。
```

---

## 5.19 第五章小结

这一章的核心是：从原子工具到任务型工具。

原子工具不是错，它是必要底座。

但如果只给 LLM 一堆原子工具，模型就必须自己推理调用顺序、前置条件、安全边界和错误恢复。对于支付这种高风险、强状态、跨系统的业务，这样不稳定。

所以 StablePay 插件的演进方向是：

```text id="p3ts5f"
1. 保留原子工具：
   create wallet / bind wallet / register DID / configure limits / pay / query。

2. 增加诊断工具：
   stablepay_doctor，把环境转成结构化 world state。

3. 增加任务工具：
   stablepay_onboard，把初始化变成状态化多轮 workflow。

4. 优化工具 schema：
   description 帮 LLM 选择工具，parameter description 帮 LLM 填参数。

5. 隐藏工程细节：
   MASTER_KEY、OWS runtime、fee payer、gateway canonical 等不直接暴露给普通用户。

6. 增加安全边界：
   支付限额 + confirm_over_threshold + human-in-the-loop。

7. 加入 eval harness：
   用自然语言任务评估 tool selection、argument accuracy、jargon leak、unsafe action blocked。
```

如果用一句话总结：

> 原子工具解决“能不能做”，任务型工具解决“Agent 能不能稳定、安全、可恢复地完成用户目标”。

这就是 StablePay OpenClaw 插件从普通工具集合升级为 Agentic Payment Tooling 的关键一步。

这章里我特意保留了几段“现有代码仍可优化”的反思，比如 `15 total` 注释、部分英文工程化 description、`sign_message` 底层参数暴露、错误 details 结构化不足。这些很适合后面写成你的真实成长线：不是一开始就设计完美，而是通过用户反馈、老板批评、Agent eval 和实际排障，把工具抽象一层层往 Agent 友好方向推。

[1]: https://docs.openclaw.ai/plugins/tool-plugins?utm_source=chatgpt.com "Tool plugins - OpenClaw"
[2]: https://www.anthropic.com/engineering/writing-tools-for-agents?utm_source=chatgpt.com "Writing effective tools for AI agents—using AI agents \ Anthropic"
[3]: https://docs.langchain.com/oss/python/langgraph/interrupts?utm_source=chatgpt.com "Interrupts - Docs by LangChain"
