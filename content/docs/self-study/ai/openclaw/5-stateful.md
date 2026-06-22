我把第六、第七章合并成一章长文。外部参考上，OpenAI Agents SDK 目前把 Agent、tools、handoff、guardrails、sessions、tracing/human-in-the-loop 都放在官方框架里，说明热门 Agent Harness 往往不是“只写一个 while loop”，而是把状态、工具、审批、可观测性一起纳入运行时。([OpenAI][1]) LangGraph 的 interrupt/checkpoint 模式则很适合对比 StablePay onboard：图执行可以在特定节点暂停，保存状态，等待外部输入后恢复。([LangChain 文档][2]) Claude Code 和 OpenCode 的 subagent/Plan/Build 机制说明，热门 Agent 项目通常会通过“角色隔离、权限隔离、上下文隔离”来管理复杂工作流。([Claude Code][3]) 你当前项目里，manifest 已经声明 17 个工具，并把 X/mock 相关工具标成 optional；package 里也已经有 `eval:tooluse`、`eval:tooluse:llm`、`eval:tooluse:kimi` 这些 harness/eval 脚本入口。 

# 第六章：stablepay_doctor 与 stablepay_onboard——从诊断工具到可恢复状态机

前面第五章讲了一个重要转变：StablePay 插件不能只停留在一堆原子工具上。原子工具可以完成具体动作，比如创建钱包、注册 DID、查询余额、发起支付，但用户真正的目标往往不是“调用某个底层函数”，而是：

```text id="nuwe8l"
帮我初始化 StablePay 插件。
帮我查余额。
帮我买一个测试商品。
为什么我现在付不了款？
```

这些目标不是单步函数，而是多步流程。

所以 StablePay 插件需要两个更高层的任务型工具：

```text id="ggr2n8"
stablepay_doctor：
    只读诊断工具，把当前环境转成结构化 world state。

stablepay_onboard：
    状态化初始化工具，把新手初始化流程做成可恢复、多轮、可提问的状态机。
```

这一章把第六章和第七章合并起来写，重点放在 onboard 的状态机设计上，同时结合热门 Agent Harness 的实现思路来反思：

```text id="hnk3k2"
1. 为什么 doctor 必须只读？
2. 为什么 onboard 不能只是一个“一键初始化函数”？
3. 为什么要引入 State Token？
4. 为什么 State Token 不能替代 doctor？
5. 热门 Agent Harness 一般怎么处理状态、工具、审批、恢复和可观测性？
6. StablePay onboard 和这些 Harness 思想有什么关系？
```

---

## 6.1 为什么需要 doctor？

最开始我只有 `stablepay_runtime_status` 这种工具。

它能返回一些 runtime 状态，例如：

```text id="d5u5x1"
requested_driver
active_driver
available_drivers
local_state_path
has_wallet
wallet
payment_config
```

这些信息对开发者有用，但对普通用户和 LLM 仍然太底层。

用户并不关心：

```text id="haab4d"
requested_driver 是什么？
active_driver 是什么？
available_drivers 为什么有三个？
local_state_path 到底对不对？
```

LLM 也不一定能稳定判断：

```text id="do8z7f"
哪些问题是阻塞？
哪些只是 warning？
哪些应该展示给用户？
哪些应该隐藏？
下一步应该调用哪个工具？
```

所以我需要一个比 `runtime_status` 更高层的诊断工具。

这就是 `stablepay_doctor`。

它的目标不是返回所有底层细节，而是回答：

```text id="t815jk"
StablePay 插件现在能不能用？
如果不能，卡在哪一步？
这个问题是阻塞问题，还是普通建议？
用户需要知道吗？
LLM 下一步应该怎么引导？
```

---

## 6.2 doctor 的核心原则：只读、无副作用

`doctor` 的第一条原则是：

```text id="fa5u69"
doctor 只能诊断，不能修复。
```

在代码里，这个原则被直接写进了文件注释：

```ts id="dknqzz"
/**
 * stablepay_doctor — Read-only diagnostic tool.
 *
 * CRITICAL RULE: doctor MUST NOT write files, auto-generate keys,
 * modify state, or perform any side effects.
 *
 * DoctorCheck uses severity/required/show_in_conversation to control
 * what the LLM sees and what counts as "all_ok".
 */
```

这条原则很重要。

如果 doctor 会自动生成 master key、修改 state、创建钱包，那它就不再是诊断工具，而是有副作用的初始化工具。

这样会带来几个问题：

```text id="xhwyo8"
1. 我无法放心随时运行 doctor。
2. LLM 可能在用户只是想“看看状态”时触发写操作。
3. 排障时诊断行为本身会改变现场。
4. 安全边界不清楚：到底谁负责检查，谁负责修复？
```

所以我把职责拆开：

```text id="qruw5a"
doctor：
    只读诊断，提供事实状态。

onboard：
    有副作用，可以自动修复或引导用户输入。
```

这其实和很多 Agent Harness 的思想一致：先观察，再行动；观察工具应该尽量无副作用，行动工具才需要权限和确认。

---

## 6.3 DoctorCheck：把“状态”变成“可决策信息”

`doctor` 最重要的设计不是检查项本身，而是 `DoctorCheck` 这个结构。

代码里是这样定义的：

```ts id="c2z06o"
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

这个结构比普通 JSON 状态强很多。

普通状态只告诉我：

```text id="vx6jz8"
has_wallet: false
active_driver: "ows-sdk"
payment_config: null
```

但 `DoctorCheck` 会告诉我：

```text id="f28495"
这个检查项叫什么？
是否通过？
问题严重程度是什么？
是否阻塞主流程？
是否应该展示给用户？
有没有解决方案？
```

也就是说，doctor 不是单纯返回状态，而是把状态加工成决策信号。

这对 LLM 很重要。

因为 LLM 后续不是要自己解析一堆原始字段，而是可以直接根据：

```text id="yyzckf"
severity
required
show_in_conversation
solutions
```

来判断下一步该怎么做。

---

## 6.4 severity / required / show_in_conversation 三个字段的意义

这三个字段是 doctor 的核心。

### severity：问题严重程度

```text id="jxps7v"
info：
    正常信息，不构成问题。

warning：
    建议处理，但不一定阻塞主流程。

error：
    错误，可能阻塞流程。
```

### required：是否阻塞主流程

不是所有 error 或 warning 都应该影响 `all_ok`。

比如 OWS CLI 没装，但 OWS SDK 可用，那么 CLI 没装不是问题。

所以 `all_ok` 不应该简单等于所有检查都 ok，而应该只看：

```text id="tx4pa4"
required === true 且 severity === "error" 且 ok === false
```

代码里也是这样处理的：

```ts id="nrqn7r"
const blocking = checks.filter((c) => c.required && c.severity === "error" && !c.ok);
const allOk = blocking.length === 0;
```

这让我避免了一个常见错误：

```text id="g7othf"
把所有“没配置”的东西都当成失败。
```

例如：

```text id="4b8z8f"
ows-rest 没配置，不一定失败。
ows-cli 不在 PATH，不一定失败。
DID 未注册，可能只是下一步还没做。
支付限额未配置，也可能由 onboard 自动配置。
```

### show_in_conversation：是否展示给用户

有些细节应该留给开发者，不应该展示给普通用户。

比如 OWS SDK 已经可用时，是否安装 OWS CLI 就不重要。

所以 doctor 可以把 CLI/REST 检查保留在 `checks` 里，但设置：

```ts id="cjr7fn"
show_in_conversation: false
```

这样 LLM 和用户看到的是简化版诊断，开发者需要排障时仍然可以看完整 details。

这就是“分层暴露复杂度”。

---

## 6.5 OWS 三层暴露：不要让用户选择不该选择的东西

OWS runtime 是 StablePay 插件里非常容易把用户劝退的部分。

插件可能支持：

```text id="qrbd4l"
ows-sdk
ows-cli
wsl-ows
ows-rest
```

但普通用户不应该一上来被问：

```text id="a2wjfh"
你想使用 ows-sdk、ows-cli、wsl-ows 还是 ows-rest？
```

这不是产品问题，而是抽象泄漏。

doctor 里对 OWS 做了三层暴露。

第一层，SDK 可用。

```ts id="nky229"
if (owsSdk) {
  checks.push({
    name: "签名驱动",
    ok: true,
    detail: "内置签名驱动可用",
    severity: "info",
    required: false,
    show_in_conversation: true,
  });
  checks.push({
    name: "OWS CLI",
    ok: true,
    detail: "可用（但不需要，内置驱动已就绪）",
    severity: "info",
    required: false,
    show_in_conversation: false,
  });
}
```

这时用户只需要看到：

```text id="mf9zyd"
✅ 签名驱动：内置签名驱动可用
```

不需要知道 CLI/REST。

第二层，SDK 不可用，但 CLI 或 REST 可用。

```text id="wkca0f"
内置签名驱动不可用，但检测到替代方案。
```

这时才提示用户或开发者可以使用替代 runtime。

第三层，完全没有签名能力。

```text id="xbt99x"
没有可用的签名驱动。
```

这才是阻塞错误。

这个设计非常适合 Agent 场景，因为它限制了 LLM 的提问范围。LLM 不会在正常情况下主动问用户“你要用哪种 runtime”，而是只有 doctor 发现内置驱动不可用时，才暴露替代方案。

---

## 6.6 从 doctor 到 onboard：诊断只是第一步

doctor 解决的是“当前状态是什么”。

但用户要的是“帮我初始化”。

这两者不一样。

如果用户说：

```text id="rtezy3"
帮我初始化 StablePay 插件。
```

doctor 只能告诉他：

```text id="k8jhj8"
缺 master key。
缺钱包。
DID 未注册。
支付限额未配置。
```

但用户还需要一个工具继续做：

```text id="zce72o"
自动生成 master key。
询问创建新钱包还是绑定已有钱包。
自动注册 DID。
自动配置默认支付限额。
最后告诉用户是否需要充值测试 USDC。
```

这就是 `stablepay_onboard`。

---

## 6.7 为什么 onboard 不能只是一个“一键函数”？

最简单的想法是：

```text id="bhy105"
stablepay_onboard()
    自动完成所有事情。
```

但这样做有问题。

因为初始化流程里有些步骤可以自动做，有些步骤必须问用户。

可以自动做的：

```text id="iuovhh"
生成 master.key。
检查 backend。
检查 signing runtime。
注册 DID。
配置默认支付限额。
```

必须问用户的：

```text id="bgzdh3"
是创建新钱包，还是绑定已有钱包？
如果绑定已有钱包，wallet_name 是什么？
public_key 是什么？
如果支付限额不想用默认值，用户希望是多少？
```

所以 onboard 不能是一个完全无脑的一键函数。

它应该是：

```text id="ufmo2g"
每次调用先诊断。
能自动做的自动做。
不能自动决定的只问一个问题。
用户回答后，下一轮继续。
```

这就是状态机。

---

## 6.8 onboard 的状态机总览

在 `src/onboard.ts` 顶部，代码已经把设计目标写清楚了：

```ts id="qyi7cv"
/**
 * stablepay_onboard — stateful onboarding state machine.
 *
 * Hybrid approach:
 *   1. State Token (onboard_session_id) stored in ~/.stablepay-openclaw/onboard-sessions.json
 *      records the in-progress flow across LLM turns.
 *   2. Every call still runs runDoctor() as the source of truth.
 *   3. If session is missing/expired → fallback to doctor-based re-derivation.
 *
 * Step order: local_config/master_key → backend → signing_runtime → wallet → did → payment_limits → balance_or_funding → complete
 */
```

这段注释非常关键，它说明 onboard 不是随便写几个 if/else，而是一个混合状态机。

它有三个核心设计：

```text id="yoavw6"
1. State Token：
   记录多轮对话里的流程状态。

2. runDoctor：
   每次都重新诊断真实环境，作为事实来源。

3. fallback：
   session 丢失、过期或无效时，不崩溃，而是根据 doctor 重新推导进度。
```

这就比单纯依赖 LLM 上下文稳定得多。

---

## 6.9 onboard 的步骤顺序

代码里定义了所有步骤：

```ts id="mlz8el"
export type OnboardOnboardStep =
  | "local_config"
  | "master_key"
  | "backend"
  | "signing_runtime"
  | "wallet"
  | "did"
  | "payment_limits"
  | "balance_or_funding"
  | "complete";
```

同时也定义了实际执行顺序：

```ts id="g0luyq"
const ALL_STEPS: OnboardOnboardStep[] = [
  "local_config",
  "master_key",
  "backend",
  "signing_runtime",
  "wallet",
  "did",
  "payment_limits",
  "balance_or_funding",
];
```

这个顺序不是随便排的。

它符合依赖关系：

```text id="ybsyx4"
1. local_config / master_key
   没有本地密钥，就无法安全读写加密 state。

2. backend
   后端不可达，DID 注册和支付都没法继续。

3. signing_runtime
   没有签名能力，就无法创建/绑定可用钱包和执行支付。

4. wallet
   没有钱包，就没有 agent 身份基础。

5. did
   没有 DID，后端无法识别当前 Agent。

6. payment_limits
   没有支付限额，支付工具没有安全策略。

7. balance_or_funding
   前面都完成后，才检查是否有余额或提示领取测试资金。
```

这就是状态机设计的第一条经验：

> 步骤顺序应该来自真实依赖关系，而不是 UI 上看起来方便。

---

## 6.10 State Token：为什么要有 onboard_session_id？

如果没有 State Token，LLM 需要完全依赖上下文记忆：

```text id="yzjy57"
刚才问到哪一步了？
用户回答的是哪个问题？
这个回答应该填到哪个参数？
现在 session 到底是不是同一个？
```

这在短对话里可能没问题，但一旦上下文变长、模型换轮、用户插话，就容易丢。

所以 onboard 引入了：

```text id="o6b1b0"
onboard_session_id
```

它的类型在参数里：

```ts id="uw7ldz"
export type OnboardParams = {
  onboard_session_id?: string;

  single_purchase_limit_usdc?: number;
  auto_purchase_threshold_usdc?: number;
  currency?: "USDC" | "USDT";
  wallet_mode?: "create_new" | "bind_existing";
  wallet_name?: string;
  public_key?: string;
  ows_wallet_id?: string;
  allow_register_did?: boolean;
};
```

第一次调用没有 `onboard_session_id`，工具会创建一个新的 session。

后续 LLM 调用时，把上一次返回的 `onboard_session_id` 带回来。

这样 onboard 可以知道：

```text id="ynp0nu"
这是同一次初始化流程。
用户刚刚回答的是这个流程里的问题。
之前已完成哪些步骤。
当前 pending_question 是什么。
```

---

## 6.11 session 存什么，不存什么？

`OnboardSession` 的定义如下：

```ts id="mrxrjk"
export type OnboardSession = {
  version: 1;
  session_id: string;
  created_at: string;
  updated_at: string;
  expires_at: string;
  current_step: string;
  completed_steps: Array<{
    step: string;
    result_summary: Record<string, unknown>;
  }>;
  pending_question?: {
    field: string;
    prompt: string;
    options?: Array<{ value: string; label: string }>;
  };
  answers: Record<string, unknown>;
};
```

它存的是流程状态：

```text id="u17s5f"
当前 session id
创建时间
更新时间
过期时间
当前步骤
已完成步骤
当前等待用户回答的问题
用户已经给过的答案
```

它不应该存：

```text id="y64ipe"
私钥
助记词
passphrase
完整 master key
API key
可直接盗用的钱包凭证
```

这点很重要。

State Token 是为了恢复流程，不是为了保存敏感材料。

session 文件路径也写得很明确：

```ts id="ea2qkl"
const SESSION_FILE = path.join(os.homedir(), ".stablepay-openclaw", "onboard-sessions.json");
const SESSION_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
```

也就是说，它保存在用户目录下：

```text id="ra7tkh"
~/.stablepay-openclaw/onboard-sessions.json
```

并且 24 小时过期。

这是一种轻量级本地 session，不需要数据库，也不依赖远程服务。

---

## 6.12 State Token 不能替代 doctor

有了 session 后，很容易误以为：

```text id="tk3djq"
既然 session 记录了 current_step，那我直接按 session 走就行了。
```

这不对。

因为 session 记录的是“对话流程状态”，不是“真实环境状态”。

真实环境随时可能变：

```text id="b9s075"
用户删了 ~/.stablepay-openclaw/stablepay-local-state.enc。
用户换了 master.key。
用户手动绑定了钱包。
后端 DID 注册状态变化了。
Gateway 暂时不可达。
OWS SDK 加载失败了。
```

所以 onboard 每次都必须重新运行 doctor。

代码里也是这样：

```ts id="revbxl"
// 3. Run doctor (always the source of truth)
const report = await runDoctor(runtime, client, cfg);
const derived = deriveStepFromDoctor(report as unknown as Parameters<typeof deriveStepFromDoctor>[0]);
```

这句注释很关键：

```text id="730eed"
doctor is always the source of truth.
```

session 只能帮助恢复对话，不能决定事实。

正确关系是：

```text id="hgtrx9"
doctor：
    检查真实环境。

State Token：
    记录对话流程。

onboard：
    综合两者，决定下一步。
```

面试时可以这样讲：

```text id="rwyi6g"
State Token 解决 LLM 多轮对话容易丢上下文的问题，doctor 解决环境真实状态可能变化的问题。我的 onboard 每次都先运行 doctor，再结合 session 推导当前步骤，所以即使 token 丢失或过期，也能 fallback 到真实环境重新恢复。
```

---

## 6.13 deriveStepFromDoctor：由事实状态推导流程状态

`deriveStepFromDoctor` 是 onboard 状态机的关键函数。

它的目标是：

```text id="wi49ge"
根据 doctor 的检查结果，推导当前已经完成哪些步骤，还缺哪些步骤，当前应该处理哪一步。
```

核心代码结构如下：

```ts id="xepwod"
function deriveStepFromDoctor(report: ReturnType<typeof runDoctor> extends Promise<infer T> ? T : never): {
  current_step: OnboardOnboardStep;
  remaining_steps: string[];
  completed_steps: Array<{ step: string; result_summary: Record<string, unknown> }>;
} {
  const checks = (report as unknown as { checks: Array<{ name: string; ok: boolean; detail: string }> }).checks;
  const completed: Array<{ step: string; result_summary: Record<string, unknown> }> = [];
  const remaining: OnboardOnboardStep[] = [];

  function check(name: string): boolean {
    return checks.find((c) => c.name === name)?.ok ?? false;
  }
  function checkDetail(name: string): string {
    return checks.find((c) => c.name === name)?.detail ?? "";
  }

  const mkOk = check("本地加密密钥");
  if (!mkOk) {
    remaining.push("local_config", "master_key");
  } else {
    completed.push({ step: "local_config", result_summary: { detail: "本地环境可用" } });
    completed.push({ step: "master_key", result_summary: { detail: checkDetail("本地加密密钥") } });
  }

  const beOk = check("后端网关");
  if (!beOk) {
    remaining.push("backend");
  } else {
    completed.push({ step: "backend", result_summary: { detail: checkDetail("后端网关") } });
  }

  const srOk = check("签名驱动");
  if (!srOk) {
    remaining.push("signing_runtime");
  } else {
    completed.push({ step: "signing_runtime", result_summary: { detail: checkDetail("签名驱动") } });
  }

  const current = remaining.length > 0 ? remaining[0] : "complete";

  return { current_step: current, remaining_steps: remaining, completed_steps: completed };
}
```

这段逻辑体现了一个重要设计：

```text id="b9zpos"
onboard 的状态不是凭空维护出来的，而是从 doctor 的事实检查中派生出来的。
```

这就避免了 session 和真实环境长期漂移。

---

## 6.14 每次只问一个问题

onboard 的另一个重要原则是：

```text id="rrxhgk"
一次只问一个问题。
```

例如当前步骤是 wallet，但用户还没有提供 `wallet_mode`，onboard 不会一次性问一堆东西：

```text id="c4w3qt"
你要创建还是绑定？
钱包名是什么？
public_key 是什么？
支付限额是多少？
是否注册 DID？
```

它只问：

```ts id="en8vs7"
resultCurrentQuestion = {
  field: "wallet_mode",
  prompt: "需要创建或绑定一个钱包。你想：",
  options: [
    { value: "create_new", label: "创建新钱包（测试用，默认配置）" },
    { value: "bind_existing", label: "绑定已有 OWS 钱包" },
  ],
};
```

这对用户和 LLM 都更稳定。

用户只需要回答一个选择。

LLM 也知道下一轮要把用户回答映射到哪个字段：

```text id="q6un29"
wallet_mode: "create_new"
```

这就是 Agent 多轮工作流里很实用的经验：

> 把复杂表单拆成单步问题，降低模型填参错误率，也降低用户认知负担。

---

## 6.15 自动修复和人工选择的边界

onboard 并不是所有步骤都问用户。

它会自动处理一些确定性步骤。

### master key 可以自动生成

```ts id="t9ukje"
case "local_config":
case "master_key": {
  const mkDir = path.join(os.homedir(), ".stablepay-openclaw");
  const mkFile = path.join(mkDir, "master.key");
  try {
    await fs.mkdir(mkDir, { recursive: true });
    const newKey = crypto.randomBytes(32).toString("base64");
    await fs.writeFile(mkFile, newKey + "\n", { encoding: "utf8", mode: 0o600 });
    try { await fs.chmod(mkFile, 0o600); } catch { /* ignore */ }
    session.completed_steps.push({ step: "master_key", result_summary: { detail: `已自动生成 ${mkFile}` } });
    session.completed_steps.push({ step: "local_config", result_summary: { detail: "本地配置文件目录已就绪" } });
  } catch (e) {
    resultError = `无法创建 master key 文件：${e instanceof Error ? e.message : String(e)}`;
  }
  break;
}
```

这里不需要用户理解 `MASTER_KEY`。

用户只需要知道：

```text id="zw3ur1"
插件已经准备好本地加密密钥。
```

### DID 可以自动注册

只要钱包存在，DID 注册可以自动执行：

```ts id="j4thjp"
case "did": {
  try {
    const status = await runtime.getStatus();
    const walletInfo = status.wallet as { wallet_address?: string; wallet_id?: string; wallet_name?: string } | null;
    if (!walletInfo?.wallet_address) {
      resultError = "没有钱包，无法注册 DID。请先创建或绑定钱包。";
      break;
    }
    const registered = await client.registerLocalDid(
      {
        user_type: "agent",
        public_key: walletInfo.wallet_address,
        wallet_address: walletInfo.wallet_address,
        wallet_id: walletInfo.wallet_id,
        wallet_name: walletInfo.wallet_name,
        metadata: { sign_runtime: (status.active_driver as string) ?? "unknown", source: "@stablepay/openclaw-plugin" },
      },
      undefined,
    );
    await runtime.registerWallet(registered);
    session.completed_steps.push({ step: "did", result_summary: { did: registered.did, wallet: registered.wallet_address } });
    session.current_step = "payment_limits";
    resultMessage = `✅ DID 已自动注册：${registered.did}`;
  } catch (e) {
    resultError = `DID 注册失败：${e instanceof Error ? e.message : String(e)}`;
  }
  break;
}
```

### 支付限额可以默认配置

```ts id="vk97hd"
case "payment_limits": {
  try {
    const limit = params.single_purchase_limit_usdc ?? 2;
    const threshold = params.auto_purchase_threshold_usdc ?? 0.5;
    const currency = params.currency ?? "USDC";
    await runtime.configurePaymentLimits({
      single_purchase_limit_usdc: limit,
      auto_purchase_threshold_usdc: threshold,
      currency,
    });
    session.completed_steps.push({
      step: "payment_limits",
      result_summary: { single_purchase_limit_usdc: limit, auto_purchase_threshold_usdc: threshold, currency },
    });
    session.current_step = "balance_or_funding";
    resultMessage =
      `✅ 支付限额已配置：单笔 ${limit} ${currency}，自动扣款阈值 ${threshold} ${currency}\n` +
      `（之后可以通过 stablepay_configure_payment_limits 修改）`;
  } catch (e) {
    resultError = `设置支付限额失败：${e instanceof Error ? e.message : String(e)}`;
  }
  break;
}
```

这体现了一个很重要的产品判断：

```text id="yk4b7z"
用户第一次使用时，不应该因为不知道支付限额怎么填而卡住。
```

默认值可以先跑通流程，之后再允许用户修改。

---

## 6.16 什么时候必须问用户？

和自动处理相反，有些地方不能替用户决定。

最典型的是钱包选择。

```ts id="hil0kh"
case "wallet": {
  const walletMode = params.wallet_mode as string | undefined;
  if (walletMode === "create_new") {
    await runtime.createLocalWallet({ wallet_name: params.wallet_name });
    session.current_step = "did";
    resultMessage = "✅ 新钱包已创建";
  } else if (walletMode === "bind_existing") {
    if (!params.wallet_name || !params.public_key) {
      resultNeedsInput = true;
      resultCurrentQuestion = {
        field: "bind_details",
        prompt: "绑定已有钱包需要提供以下信息：\n• wallet_name：钱包名称\n• public_key：Solana 地址（Base58）",
      };
    } else {
      await runtime.bindExistingWallet({
        wallet_name: params.wallet_name,
        public_key: params.public_key,
        ows_wallet_id: params.ows_wallet_id,
      });
      session.current_step = "did";
      resultMessage = "✅ 已有钱包已绑定";
    }
  } else {
    resultNeedsInput = true;
    resultCurrentQuestion = {
      field: "wallet_mode",
      prompt: "需要创建或绑定一个钱包。你想：",
      options: [
        { value: "create_new", label: "创建新钱包（测试用，默认配置）" },
        { value: "bind_existing", label: "绑定已有 OWS 钱包" },
      ],
    };
  }
  break;
}
```

这里不能自动选择是有原因的。

创建新钱包和绑定已有钱包代表两种完全不同的用户意图：

```text id="q6iir6"
create_new：
    用户是第一次测试，可以生成一个新身份。

bind_existing：
    用户已经有钱包，希望沿用旧身份、旧资产、旧 DID。
```

如果插件擅自创建新钱包，用户可能会困惑：

```text id="fvqg5n"
我明明有钱包，为什么现在查的是另一个地址？
```

所以钱包选择必须由用户确认。

这也是 Agent Harness 里的一个常见边界：

> 可以自动执行确定性的低风险步骤，但涉及用户身份、资金、权限、持久化选择的步骤，需要人类输入或确认。

---

## 6.17 onboard 返回值：message 给人，details 给 LLM

onboard 的返回值也很关键。

它不仅要给用户看，还要帮助 LLM 下一轮继续调用。

代码里构造 details：

```ts id="idpr95"
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

这就是双层返回：

```text id="spilkj"
message：
    给用户看的中文说明。

details：
    给 LLM 继续执行流程用的结构化状态。
```

例如：

```json id="ggwzfj"
{
  "status": "needs_input",
  "onboard_session_id": "onb-1712345678-abcdef",
  "progress": {
    "done": 4,
    "total": 7,
    "step_name": "wallet"
  },
  "current_question": {
    "field": "wallet_mode",
    "prompt": "需要创建或绑定一个钱包。你想：",
    "options": [
      { "value": "create_new", "label": "创建新钱包（测试用，默认配置）" },
      { "value": "bind_existing", "label": "绑定已有 OWS 钱包" }
    ]
  },
  "remaining_steps": ["wallet", "did", "payment_limits", "balance_or_funding"]
}
```

LLM 看到这个 details 后，不需要重新猜下一步。

它只要问用户：

```text id="x5e1az"
你想创建新钱包，还是绑定已有钱包？
```

用户回答后，再调用：

```json id="r3sj2h"
{
  "onboard_session_id": "onb-1712345678-abcdef",
  "wallet_mode": "create_new"
}
```

这就是任务型工具和普通 API 的区别。

普通 API 只返回结果。

任务型工具返回结果，也返回下一步应该怎么继续。

---

## 6.18 从热门 Agent Harness 看 onboard 的设计位置

现在横向看一下热门 Agent/Harness 项目的共性。

不同项目名字不一样：

```text id="ynzx6a"
OpenAI Agents SDK
LangGraph
Claude Code
OpenCode
AutoGen
CrewAI
MCP-based tool runners
```

但它们在工程上都在解决类似问题：

```text id="wudvsx"
1. 怎么描述 Agent 能调用哪些工具？
2. 怎么保存多轮任务状态？
3. 怎么在关键步骤暂停等待人类输入？
4. 怎么限制高风险动作？
5. 怎么记录执行轨迹，方便调试和评估？
6. 怎么把复杂任务拆成子任务或子 Agent？
```

这几个问题和 StablePay onboard 非常接近。

---

## 6.19 OpenAI Agents SDK：Agent + Tools + Guardrails + Sessions + Tracing

OpenAI Agents SDK 的设计里，核心模块通常包括：

```text id="wcwst1"
Agent：
    持有 instructions、tools、handoffs 等。

Runner：
    执行 agent loop。

Tools：
    外部能力调用。

Guardrails：
    输入、输出或工具调用前后的约束。

Sessions：
    多轮上下文或工作状态。

Tracing：
    记录模型调用、工具调用、handoff、guardrail 等执行轨迹。
```

这个思路对 StablePay 的启发是：

```text id="wpbq3t"
onboard 不能只看作一个函数。
它应该看作一个小型 agent workflow runtime：
    有状态；
    有工具；
    有 guardrail；
    有用户输入；
    有可追踪 details；
    有 session。
```

StablePay 没有直接引入 OpenAI Agents SDK，但 onboard 的设计已经对应了其中几个概念：

```text id="gv8gnv"
onboard_session_id ≈ session
doctor report ≈ world state / observation
current_question ≈ human input request
payment limits ≈ guardrail
details / eval trace ≈ tracing / observability
```

这说明我们不一定要硬改 Agent runtime，也能在插件工具层体现 Agent 工程能力。

---

## 6.20 LangGraph：Graph State + Checkpoint + Interrupt

LangGraph 的典型思路是把流程建成图：

```text id="jcmy85"
StateGraph
  ↓
node
  ↓
edge
  ↓
checkpoint
  ↓
interrupt / resume
```

它很适合多步流程和 human-in-the-loop。

比如一个流程可以在某个节点暂停：

```text id="vwq0r7"
执行到 payment_approval 节点
  ↓
触发 interrupt
  ↓
保存当前 graph state
  ↓
等待用户审批
  ↓
resume 后继续执行
```

StablePay onboard 不是 LangGraph，但思想非常像：

```text id="pm6tuc"
OnboardSession ≈ checkpoint state
current_step ≈ 当前节点
pending_question ≈ interrupt payload
onboard_session_id ≈ resume token
runDoctor ≈ 每次恢复前重新观察环境
```

如果用 LangGraph 风格画 StablePay onboard，大概是：

```text id="yd19ex"
[local_config/master_key]
        ↓
[backend]
        ↓
[signing_runtime]
        ↓
[wallet] --需要用户选择--> interrupt: wallet_mode
        ↓
[did]
        ↓
[payment_limits]
        ↓
[balance_or_funding]
        ↓
[complete]
```

这个对比非常适合面试。

我可以说：

```text id="lzs3hh"
虽然我没有直接引入 LangGraph，但我借鉴了 graph workflow 的思想，把初始化流程拆成有序 step。每次调用 onboard 都像 resume 一次 workflow：先加载 session，再运行 doctor 重新确认事实状态，然后继续当前 step。如果需要用户输入，就返回 current_question，相当于一个轻量 interrupt。
```

---

## 6.21 Claude Code / OpenCode：Plan / Build / Subagent / 权限隔离

Claude Code 和 OpenCode 这类编码 Agent 的 harness 还有另一个启发：它们通常会区分不同角色和权限。

常见模式是：

```text id="j1s9pq"
Plan：
    只读规划，不改文件。

Build：
    可以执行修改。

Explore / Scout：
    搜索和理解代码库，不污染主上下文。

Subagent：
    特定任务交给专门上下文，工具权限可以限制。
```

这对 StablePay doctor/onboard 的启发是：

```text id="f8p6ku"
doctor 像 Plan / Explore：
    只读，不修改状态。

onboard 像 Build：
    可以写 master.key、创建钱包、注册 DID、配置限额。

pay 工具像高风险 action：
    必须受支付限额和用户确认约束。
```

这说明 doctor/onboard 的拆分不是随意的，而是符合 Agent Harness 的通用设计：

```text id="tyvr5j"
观察和修改要分开。
低风险和高风险要分开。
通用诊断和具体执行要分开。
不同工具要有不同权限边界。
```

这也是我面试时可以重点讲的能力。

---

## 6.22 AutoGen / CrewAI：多 Agent 协作与 Human-in-the-loop

AutoGen、CrewAI 这类框架常常强调：

```text id="peugjj"
多个 Agent 分工
任务编排
人类反馈
流程控制
memory
observability
```

这些框架更偏多 Agent 编排，但对 StablePay onboard 的启发是：

```text id="qqje0k"
复杂任务不能只靠一个大 prompt。
需要明确角色、状态、工具、停止条件和人类介入点。
```

StablePay 当前不是多 Agent 系统，但它已经具备一个小型 workflow harness 的结构：

```text id="oad2jn"
状态：
    OnboardSession

观察：
    runDoctor

决策：
    deriveStepFromDoctor + switch(currentStep)

行动：
    create master key / create wallet / bind wallet / register DID / configure limits

人类输入：
    current_question

恢复：
    onboard_session_id + doctor fallback

输出：
    message + details
```

这套结构比“让 LLM 自己一步步想”稳定得多。

---

## 6.23 MCP：工具标准化与工具注册表思想

MCP 的核心价值是把模型和外部工具、资源连接起来，降低每个模型/工具之间都要单独集成的成本。

对 StablePay 的启发是：

```text id="jnno7n"
工具应该是可描述、可发现、可调用、可审计的能力单元。
```

OpenClaw 的 `contracts.tools` 也体现了类似思想：

```text id="f4eu4v"
工具不能只藏在 runtime 里。
manifest 里也要声明工具契约。
```

StablePay manifest 现在已经列出 17 个工具，并把 optional 工具单独标注，这说明插件能力开始具备静态可发现性。

这对 Agent Harness 很重要。

因为 Harness 在执行之前，需要知道：

```text id="kig8av"
有哪些工具？
哪些工具默认可用？
哪些工具是 optional？
哪些工具可能需要权限？
哪些工具是高风险 action？
```

这也是为什么 `check:manifest-tools` 这种脚本有意义。

它保证 runtime 注册工具和 manifest 声明工具不会漂移。

---

## 6.24 Harness 的共性总结：一个 Agent 运行框架通常包含什么？

综合热门项目，可以把 Agent Harness 抽象成几个模块：

```text id="fb7jl3"
1. Tool Registry：
   注册可用工具，描述工具 schema、参数和权限。

2. State Store：
   保存会话、任务进度、上下文或 workflow state。

3. Planner / Policy：
   决定下一步该调用什么工具，或者是否需要用户输入。

4. Executor：
   真正执行工具调用或副作用动作。

5. Guardrail / Permission：
   在高风险动作前检查、阻断或请求审批。

6. Interrupt / Human Input：
   暂停流程，等待用户回答或确认。

7. Trace / Observability：
   记录模型调用、工具调用、参数、结果、错误和恢复过程。

8. Eval Harness：
   用任务集衡量工具选择、参数填充、成功率、安全拦截和 jargon leak。
```

对应到 StablePay：

```text id="f5cttq"
Tool Registry：
    OpenClaw api.registerTool + openclaw.plugin.json contracts.tools

State Store：
    ~/.stablepay-openclaw/onboard-sessions.json
    stablepay-local-state.enc

Planner / Policy：
    deriveStepFromDoctor + switch(currentStep)

Executor：
    runtime.createLocalWallet
    runtime.bindExistingWallet
    client.registerLocalDid
    runtime.configurePaymentLimits

Guardrail：
    payment limits
    confirm_over_threshold
    doctor required/error checks

Interrupt / Human Input：
    current_question
    pending_question
    onboard_session_id

Trace / Observability：
    details
    completed_steps
    remaining_steps
    evals/traces

Eval Harness：
    npm run eval:tooluse
    npm run eval:tooluse:llm
    npm run eval:tooluse:kimi
```

所以我可以很有底气地说：

> StablePay onboard 虽然不是完整通用 Agent runtime，但它已经包含了一个垂直领域 Agent Harness 的核心元素。

---

## 6.25 onboard 的完整执行链路

现在可以把 onboard 的运行过程完整串起来。

用户说：

```text id="ef0l0y"
帮我初始化 StablePay 插件。
```

LLM 调用：

```json id="nytb00"
{}
```

onboard 做：

```text id="fmu2lv"
1. loadSessions()
2. 没有 onboard_session_id，创建新 session
3. runDoctor()
4. deriveStepFromDoctor()
5. 发现缺 master key
6. 自动生成 ~/.stablepay-openclaw/master.key
7. 再 runDoctor()
8. 推导下一步是 wallet
9. 返回 current_question：创建新钱包还是绑定已有钱包
10. 返回 onboard_session_id
```

用户回答：

```text id="nia1yx"
创建新钱包。
```

LLM 调用：

```json id="byb7wz"
{
  "onboard_session_id": "onb-...",
  "wallet_mode": "create_new"
}
```

onboard 做：

```text id="yda3li"
1. 读取 session
2. runDoctor()
3. 确认当前缺 wallet
4. createLocalWallet()
5. session.current_step = "did"
6. runDoctor()
7. 继续自动注册 DID 或返回下一步
```

后续继续：

```text id="1meyne"
DID 注册
  ↓
支付限额配置
  ↓
余额/充值提示
  ↓
complete
```

这就是状态机的意义。

用户不需要理解所有步骤，LLM 也不需要自己推理完整流程。

---

## 6.26 为什么用本地 session 文件，而不是服务端数据库？

当前 onboard session 存在：

```text id="tx1mbg"
~/.stablepay-openclaw/onboard-sessions.json
```

这个设计很轻量。

优点：

```text id="zgbcja"
1. 不需要后端数据库。
2. 不依赖网络。
3. OpenClaw gateway 重启后仍能恢复。
4. 适合本地插件场景。
5. 不存敏感材料，风险可控。
```

缺点：

```text id="w0zi11"
1. 不能跨设备同步。
2. 多进程并发写可能需要进一步加锁。
3. 文件损坏时需要 fallback。
4. 不适合多人共享同一个插件目录。
```

但对于当前 StablePay 插件来说，本地 session 是合理的 MVP。

因为 onboarding 是本地用户初始化流程，不是一个多人协作服务端流程。

未来如果要做更强版本，可以考虑：

```text id="swx747"
1. 给 session 文件加文件锁。
2. 把 session 放进加密 state。
3. 给 session 增加 cleanup 机制。
4. 给 onboard 输出 trace_id，关联 eval traces。
5. 在多用户环境中按 OpenClaw workspace 或 user id 隔离。
```

---

## 6.27 当前 onboard 设计的不足和改进点

这章也要诚实反思。

### 1. deriveStepFromDoctor 依赖中文 check name

现在 `deriveStepFromDoctor` 通过中文检查项名称查找：

```ts id="j9k1ul"
function check(name: string): boolean {
  return checks.find((c) => c.name === name)?.ok ?? false;
}
```

例如：

```text id="w5p9z7"
本地加密密钥
后端网关
签名驱动
本地钱包
DID 注册
支付限额
```

这个实现简单，但不够稳。

如果以后 doctor 的中文名字改了，onboard 推导就会坏。

更好的设计是给 `DoctorCheck` 增加稳定的 `code` 字段：

```ts id="xsj4jj"
type DoctorCheck = {
  code:
    | "plugin_loaded"
    | "backend_reachable"
    | "master_key"
    | "signing_runtime"
    | "wallet"
    | "did"
    | "payment_limits";
  name: string;
  ok: boolean;
  detail: string;
  severity: "info" | "warning" | "error";
  required: boolean;
  show_in_conversation: boolean;
  solutions?: string[];
};
```

然后 onboard 用 `code` 推导，不用中文 name。

### 2. session 保存没有显式文件锁

`saveSessions` 现在直接写文件：

```ts id="xilp9k"
await fs.writeFile(SESSION_FILE, JSON.stringify(sessions, null, 2), "utf8");
```

单用户单进程基本够用。

但如果未来 OpenClaw gateway 多进程或并发调用 onboard，可能出现写覆盖。

可以后续加：

```text id="t378jn"
原子写临时文件后 rename
文件锁
按 session_id 单独存文件
```

### 3. signing_runtime 步骤的替代方案还不够优雅

当前如果 SDK 不可用但 CLI/REST 可用，会让用户选择替代方案。

但 `current_question.field` 现在写成 `wallet_mode`，语义有点不准确。

更好应该是：

```text id="51xa13"
field: "signing_runtime"
options:
  - ows-cli
  - ows-rest
```

然后后续钱包步骤再问 wallet_mode。

### 4. balance_or_funding 目前只是完成提示

当前 `balance_or_funding` 直接：

```ts id="xlwj49"
resultMessage = "🎉 所有步骤已完成！你的 StablePay 插件已就绪。";
```

但更好的状态机应该真的查余额：

```text id="kqf7ii"
如果余额 > 0：
    complete，可以测试购买。

如果余额 = 0：
    needs_funding，提示钱包地址，让用户找管理员打测试 USDC。
```

这样 onboard 才是真正闭环。

### 5. trace 还可以更强

当前 details 已经有 completed_steps / remaining_steps。

未来可以增加：

```text id="m1tmdg"
trace_id
tool_call_id
doctor_snapshot_hash
before_state
after_state
```

这样可以和 eval traces 对齐。

---

## 6.28 面试怎么讲 onboard 状态机？

如果面试官问：

> “你这个项目里 Agent workflow 是怎么设计的？”

我可以这样回答：

```text id="f0dnzf"
StablePay 初始化不是一个单步函数，而是一个强状态、多轮、带副作用的 workflow。它涉及本地密钥、签名 runtime、钱包、DID、支付限额和余额检查。直接把这些原子工具暴露给 LLM，模型容易选错顺序或泄漏工程细节。

所以我设计了 stablepay_doctor + stablepay_onboard。doctor 是只读诊断工具，负责把当前环境转成结构化 world state；onboard 是有副作用的状态机，负责按 local_config/master_key、backend、signing_runtime、wallet、did、payment_limits、balance_or_funding 的顺序推进。

onboard 使用 State Token 记录多轮流程状态，session 存在本地 onboard-sessions.json，24 小时过期。每次调用仍然先运行 doctor，因为 doctor 才是真实环境的事实来源。如果 session 丢失或过期，onboard 不会崩溃，而是通过 doctor 重新推导当前步骤。需要用户输入时，工具返回 current_question 和 options，让 LLM 每次只问一个问题。
```

如果面试官继续问：

> “这和 Agent Harness 有什么关系？”

可以回答：

```text id="l8j5bm"
我没有直接改 OpenClaw runtime，但在工具层实现了一个垂直领域的小型 Harness。它包含 tool registry、state store、planner、executor、interrupt、guardrail 和 trace/eval。比如 onboard_session_id 类似 session/resume token，current_question 类似 interrupt，doctor 类似 observation/world state，payment limits 类似 guardrail，eval:tooluse 用来评估模型是否正确使用这些工具。
```

这就能把项目从“支付插件”提升到“Agent 工程”。

---

## 6.29 本章总结

这一章的核心是 doctor/onboard 状态机设计。

StablePay 插件的初始化流程不是一条简单命令，而是一个多步 Agent workflow。

核心结论如下：

```text id="w018d9"
1. doctor 是只读诊断工具，不允许修改本地状态。
2. doctor 通过 severity / required / show_in_conversation 把底层状态变成可决策信息。
3. onboard 是有副作用的状态机，负责自动修复、提问和推进流程。
4. onboard 每次调用都先运行 doctor，因为真实环境才是事实来源。
5. State Token 记录多轮对话状态，但不能替代 doctor。
6. current_question 让 LLM 每次只问一个问题，降低用户负担和填参错误率。
7. master key、DID 注册、支付限额可以自动处理；钱包创建/绑定这种身份选择必须问用户。
8. 热门 Agent Harness 普遍包含工具注册、状态存储、执行器、guardrail、interrupt、trace 和 eval。
9. StablePay onboard 虽然不是通用 Agent runtime，但已经具备垂直领域 Harness 的核心结构。
```

用一句话总结：

> `stablepay_doctor` 负责看清世界，`stablepay_onboard` 负责带着用户一步步改变世界；State Token 记住对话，doctor 校准事实，guardrail 控制风险，eval harness 检查 Agent 是否真的会用。

这就是 StablePay OpenClaw 插件从“工具集合”演进成 “Agentic Payment Tooling” 的关键一章。


[1]: https://openai.github.io/openai-agents-python/?utm_source=chatgpt.com "OpenAI Agents SDK"
[2]: https://docs.langchain.com/oss/python/langgraph/interrupts?utm_source=chatgpt.com "Interrupts - Docs by LangChain"
[3]: https://code.claude.com/docs/zh-CN/sub-agents?utm_source=chatgpt.com "创建自定义 subagents - Claude Code Docs"
