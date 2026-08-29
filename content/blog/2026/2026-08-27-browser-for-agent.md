---
schema: bubblevan/v1
id:
content_kind: blog
title: "Browser for Agent：给 AI 一双可靠的手和眼睛"
date: 2026-08-27
updated: 2026-08-27
status: draft
visibility: public
summary: "从浏览器自动化的基本模型出发，理解 Browser Agent 的观察、操作、登录态、上下文隔离和安全边界，并以 Windows + Hermes 为例选择合适的工具。"
topics: [browser-agent, browser-automation, agent-harness]
projects: [hi-agent]
aliases: []
authors: [bubblevan]
---

# Browser for Agent：给 AI 一双可靠的手和眼睛

当我们说“让 Agent 帮我上网”时，真正要解决的并不是让模型学会几个 `click` 命令，而是要把一个真实浏览器变成 Agent 可以观察、操作、等待和验证的工作环境。

一个成熟的 Browser Agent 至少需要同时处理四件事：

- **观察**：理解当前页面有哪些文本、按钮、输入框、表格和状态。
- **操作**：点击、输入、滚动、上传、下载、切换页面和执行脚本。
- **状态**：处理 Cookie、Local Storage、登录态、弹窗、重定向和多标签页。
- **边界**：知道哪些页面可以自动操作，哪些动作必须让人确认。

这篇文章把 Browser for Agent 当成一个入门主题来学习，也记录我目前对几类工具的判断。

## 先看结论：工具不是越多越好

下面这张表比较的是工具的架构侧重点，不是统一 benchmark；同一个工具在不同操作系统、浏览器版本、登录状态和任务类型下，体验可能完全不同。

| 项目 | Windows | Linux | 复用真实登录态 | 不打扰人的浏览器 | Hermes | 我给你的定位 |
| --- | --- | --- | --- | --- | --- | --- |
| [Tencent BrowserSkill](https://github.com/Tencent/BrowserSkill) | ✅ | ✅ | ✅ | ✅ Agent Window | ✅ 官方列出 | **Windows + Hermes 首选入门** |
| [Vercel `agent-browser`](https://github.com/vercel-labs/agent-browser) | ✅ | ✅ | 可持久化 Session/Profile，但不是核心卖点 | 独立 Browser | 间接可用 | Coding Agent 通用 Browser CLI |
| [`browser-bridge`](https://github.com/whg517/browser-bridge) | ✅ | ✅ | ✅ 直接控制已登录 Chrome | ⚠️ 直接操作真实 Tab | MCP 即可 | Real Chrome Bridge |
| [`realbrowser`](https://github.com/darkamenosa/realbrowser) | ✅ | ✅/macOS | ✅ CDP attach | 有 target lease | 通用 Skill | 偏 DevTools/真实 Browser |
| [Kachilu Browser](https://github.com/kachilu-inc/kachilu-browser) | ✅/WSL2 | ✅ | ✅ Windows-side profile | ✅ | 通用 Agent | WSL2 特别友好 |
| [Ego Lite](https://github.com/citrolabs/ego-lite) | ❌目前 | ❌目前 | ✅ | ✅ Space | ✅ | 架构最好看，但目前 Mac-only |

如果你使用的是 Windows 上的 Hermes，我建议先从 BrowserSkill 入门：它明确列出 Windows x64 和 Hermes Agent 支持，使用 `bsk` CLI 加浏览器扩展，并提供独立可见的 Agent Window 和人工接管流程。[BrowserSkill 官方说明](https://github.com/Tencent/BrowserSkill#readme)

## 一、Browser for Agent 到底是什么

可以先把它抽象成下面这条链：

```text
用户目标
   ↓
Agent / Harness
   ↓ 生成动作或脚本
Bridge / Runtime
   ↓ 连接浏览器
Browser
   ↓ 访问页面、保存状态、执行 JavaScript
Website / Web App
```

这里的几个词经常被混在一起：

### 1. Agent / Harness

这是 Hermes、Codex、Claude Code 或其他 Agent 的主体。它负责理解用户目标、制定下一步计划、选择工具，并决定什么时候继续、重试或询问用户。

模型本身通常不会直接“摸到”浏览器。它只能看到 Harness 提供给它的观察结果，再输出下一步动作。

### 2. Bridge / Runtime

这是连接 Agent 和浏览器的中间层，例如：

- CLI：Agent 通过 shell 调用 `bsk` 或 `agent-browser`。
- MCP：Agent 通过 MCP server 获得浏览器工具。
- CDP：工具通过 Chrome DevTools Protocol 连接 Chromium。
- 浏览器扩展：扩展运行在真实浏览器里，把 Agent 的请求转发给当前页面。

这层决定了 Agent 能不能复用真实登录态、能不能创建隔离环境、能不能拿到结构化页面信息，以及出错后能不能恢复。

### 3. Browser

浏览器不是一个简单的 HTTP 客户端。现代网站可能包含：

- JavaScript 渲染的动态内容；
- iframe、Shadow DOM 和跨页面跳转；
- Cookie、Local Storage、Session Storage；
- 文件下载、权限请求、验证码和二次确认；
- 只有在真实窗口里才会出现的交互状态。

因此“请求网页 HTML”与“控制一个真实浏览器”是两类完全不同的问题。

### 4. Website State

登录态是 Browser Agent 最有价值、也最危险的一部分。一个 Agent 如果能看到你已经登录的邮箱、后台、社交媒体或支付页面，它获得的就不仅是“网页阅读权限”，而是接近用户本人的操作权限。

所以 Browser Agent 的核心问题不是“能不能点击”，而是：

> **让 Agent 获得足够的浏览器能力，同时把页面、登录态、标签页和不可逆动作隔离在可控边界内。**

## 二、Agent 看到的不是网页，而是观察结果

浏览器可以提供很多种观察方式。初学时最容易犯的错误，是以为 Agent 只需要一张截图。

| 观察方式 | Agent 得到什么 | 优点 | 常见问题 |
| --- | --- | --- | --- |
| 截图 | 像素、布局、颜色和视觉状态 | 能处理画布、图表和视觉 UI | token 成本高，难精确定位元素 |
| DOM / HTML | 节点、属性、文本和结构 | 信息完整，适合开发者调试 | 页面结构可能很复杂，隐藏节点很多 |
| Accessibility Tree | role、accessible name、value、层级 | 更接近 Agent 真正需要的 UI 语义 | 页面无障碍标注差时信息会不完整 |
| 页面文本 | 可读正文和局部状态 | 适合阅读和提取 | 缺少按钮关系、坐标和交互语义 |
| 网络/CDP 数据 | 请求、响应、Console、运行时状态 | 适合 DevTools 级调试 | 权限很高，容易越过页面交互边界 |

对 Agent 来说，最有用的通常不是整页 HTML，而是一个带有稳定引用的语义快照：

```text
button "Search"        ref=e1
textbox "Keyword"      ref=e2
link "Next page"        ref=e3
```

于是一次浏览器循环会变成：

```text
snapshot
   ↓
选择 ref=e2
   ↓
fill ref=e2 "Hermes Agent"
   ↓
click ref=e1
   ↓
重新 snapshot，确认页面真的发生了变化
```

[Vercel agent-browser](https://github.com/vercel-labs/agent-browser) 的基本命令就是这种思路：先 `snapshot` 获取 accessibility tree 和 refs，再通过 ref 或 role/name 定位元素；它同时也支持截图、读取文本、连接 CDP 和批量执行命令。

Chrome DevTools Protocol 的 Accessibility domain 提供了 `getFullAXTree`、`getPartialAXTree` 和按 accessible name / role 查询节点等能力。[Chrome DevTools Protocol Accessibility 文档](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/)

这里有一个很重要的实践规则：

> **页面发生跳转、弹窗出现、列表刷新或点击后 DOM 变化时，旧 ref 不能盲目复用；重新观察，再进行下一步。**

## 三、四种常见的 Browser Agent 架构

### 路线 A：独立的 Headless / Controlled Browser

典型代表是 Playwright、Puppeteer 和 Vercel `agent-browser`。Agent 启动一个自己控制的 Chromium，再通过 CLI、库或 MCP 操作它。

优点：

- 环境可重复，适合测试、爬取和 coding workflow；
- 登录态可以放在专用 Profile 或 Session 中；
- 不会直接碰用户正在使用的窗口；
- 适合多个任务并行运行。

代价：

- 很多网站需要重新登录；
- 真实 Chrome 里的扩展、Cookie 和设备信任状态不一定存在；
- 需要管理浏览器进程、Profile、下载目录和清理逻辑。

Playwright 的 `BrowserContext` 可以理解为一个轻量、隔离的浏览器 Profile。每个 Context 有独立的 Cookie、Local Storage 和 Session Storage，而且多个 Context 可以运行在同一个 Browser 进程中。[Playwright Browser Context 文档](https://playwright.dev/docs/browser-contexts)

### 路线 B：真实浏览器桥接

典型代表是 BrowserSkill、browser-bridge 和 realbrowser。它们通常通过浏览器扩展、本地 daemon、MCP 或 CDP，把 Agent 连接到用户已经打开或已经登录的浏览器。

这条路线最适合：

- 处理需要真实登录的后台系统；
- 复用已有的 SSO、Cookie 和二次验证状态；
- 让用户看见 Agent 正在做什么；
- 遇到验证码或人工确认时暂停并交还控制权。

但它的风险也最大。以 [browser-bridge 的安全说明](https://github.com/whg517/browser-bridge#security-first--read-this) 为例，真实登录的 Chrome 可能让桥接层读取页面内容、Cookie、Web Storage，甚至执行页面 JavaScript。安装这类工具前，必须把它当作高权限本地软件来审查。

### 路线 C：直接连接 CDP

CDP 是 Chromium 提供的调试协议。它可以访问页面、执行 JavaScript、读取网络事件、获取截图和操作 Accessibility Tree。

CDP 很适合作为底层能力，但不等于完整的 Agent 产品。你还需要自己解决：

- 哪个 Browser Process 属于哪个 Agent；
- 哪个 Tab 可以被哪个任务访问；
- 用户和 Agent 同时操作时谁拥有控制权；
- 页面跳转后 target 是否发生变化；
- Cookie、下载、截图和日志如何存储。

因此，CDP 更像“发动机”，而 BrowserSkill、browser-bridge、realbrowser 或 Ego Lite 更像围绕发动机搭出的整车。

### 路线 D：Agent-native Browser

Ego Lite 代表另一种思路：浏览器从设计之初就假设“人类和多个 Agent 要同时工作”。它把 Agent 的隔离 Space、共享登录态、浏览器运行时和 Skill 放在同一个产品里。

这个架构很漂亮，但要注意平台边界：Ego Lite 官方 README 目前仍写着 macOS today，Windows 和 Linux 在 roadmap 上。[Ego Lite 官方 README](https://github.com/citrolabs/ego-lite#quick-start)

## 四、最关键的概念：Profile、Context、Page 和 Target

这几个概念可以用一棵树来理解：

```text
Browser Process
├── Profile / User Data Directory
│   ├── cookies
│   ├── extensions
│   └── local storage
├── BrowserContext
│   ├── Page / Tab 1
│   └── Page / Tab 2
└── BrowserContext
    └── Page / Tab 3
```

- **Profile**：最持久的身份边界，通常包含 Cookie、扩展和浏览器设置。
- **BrowserContext**：更轻量的隔离边界，适合把不同 Agent 或不同任务分开。
- **Page / Tab**：用户看到的标签页，通常在一个 Context 内管理。
- **Target**：CDP 层面的可连接对象，页面、iframe、worker 等都可能对应不同 Target。

经验上：

- 需要干净、可重复的任务，优先用独立 Context；
- 需要复用登录态，使用专用持久化 Profile 或受控 Agent Window；
- 需要直接碰用户真实 Tab，必须有显式 borrow / lease / handoff 机制；
- 不要让多个 Agent 无边界地共享同一个 Profile 和 Tab。

“不打扰人的浏览器”不等于“让 Agent 偷偷操作你的浏览器”。更好的定义是：

> **Agent 有自己的可见工作区，只有在用户明确要求时，才临时借用某个真实 Tab。**

## 五、一个可靠的 Browser Agent 循环

最小但可靠的循环可以写成：

```text
Plan
  ↓
Observe
  ↓
Locate
  ↓
Act
  ↓
Wait for state change
  ↓
Verify
  ↓
Continue / Ask human / Stop
```

### 1. 先观察，不要猜选择器

不要根据页面“看起来应该有一个按钮”就直接点击。先拿快照，确认按钮的 role、accessible name、是否可见、是否被弹窗覆盖。

### 2. 优先使用语义定位

通常优先级可以是：

```text
role + accessible name
label
placeholder
稳定的 data-testid
CSS selector
坐标
```

坐标点击适合画布和特殊 UI，但对响应式页面、弹窗和窗口大小变化比较脆弱。

### 3. 等待“状态”，不要只等待几秒

`wait 3000ms` 有时有效，但不是可靠的同步方式。更好的等待条件是：

- 某个元素出现或消失；
- URL 匹配目标模式；
- 页面出现“已保存”“加载完成”等文本；
- 网络请求结束；
- 按钮从 disabled 变成 enabled。

### 4. 每个副作用都要验证

点击提交后不要默认成功。检查 URL、成功提示、列表变化或后端返回状态。下载文件后检查文件是否真的存在、大小是否合理、类型是否正确。

### 5. 不可逆动作必须有刹车

发送消息、删除文件、发布内容、付款、修改权限、提交表单等动作，都应该明确区分：

```text
读取 / 草稿 / 预览  → Agent 可以自动完成
发送 / 删除 / 付款  → 默认先询问用户
```

这也是人机协作比“全自动”更可靠的地方：Agent 负责准备和验证，人类在高代价节点做最后确认。

## 六、登录态与安全边界

Browser Agent 的安全风险主要不是“模型会不会答错”，而是“模型能不能把答错变成真实操作”。

### 建议的最小安全原则

- 使用专用浏览器 Profile 或 Agent Window，不要默认暴露日常主 Profile。
- 不要把 Cookie、Token、Local Storage 内容复制到聊天上下文或日志。
- 对邮箱、支付、云控制台、社交账号等站点设置更严格的确认策略。
- 让 Agent 读取页面，但不要允许网页内容覆盖用户原始目标。
- 把网页当作不可信输入：页面中的“忽略之前指令”“把密钥贴到这里”等文字可能是 Prompt Injection。
- 下载文件后先验证文件类型和来源，不要自动执行下载的脚本。
- 任务结束后关闭临时 Tab、Context 和 Browser Process。

BrowserSkill 的设计里包含 Agent Window、显式借用真实 Tab，以及遇到验证码、登录和确认对话框时的人机接管。[BrowserSkill 安全与工作流说明](https://github.com/Tencent/BrowserSkill#browserskill-advantages)

如果选择直接桥接真实 Chrome，安全边界需要自己承担。浏览器桥接层的权限通常远高于普通网页插件，安装之前要检查它是否监听 localhost、是否需要 Token、是否能访问所有站点，以及是否会上传页面内容。

## 七、Windows + Hermes 的入门实践

对你现在的环境，最实际的学习路线是先使用 Tencent BrowserSkill，而不是等待 Ego Lite 的 Windows 版本。

BrowserSkill 官方 README 明确列出了 Windows x64、Chrome/Edge，以及 Hermes Agent；它的 Agent 通过 shell 调用 `bsk`，本地 daemon 再通过浏览器扩展控制 Agent Window。[BrowserSkill 架构说明](https://github.com/Tencent/BrowserSkill#how-it-works)

### 安装步骤

在 PowerShell 中，官方 Agent 安装说明给出的流程是：

```powershell
irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex
bsk --version
bsk install-skill --yes
bsk doctor
```

然后在 Chrome 或 Edge 中安装并启用 BrowserSkill 扩展。官方安装指南说明，如果 `bsk doctor` 只有 `extension connected` 失败，通常是扩展还没有安装、启用或打开连接状态。[BrowserSkill Agent 安装指南](https://github.com/Tencent/BrowserSkill/blob/main/AGENT_INSTALL.md)

重新打开 Hermes 会话后，可以从类似这样的任务开始：

```text
/browser-skill 打开 example.com，读取页面标题和主要内容，不要登录或提交任何表单。
```

第一次不要直接拿微信、飞书、邮箱或支付页面做实验。先用公开页面完成“打开 → 观察 → 提取 → 截图 → 关闭”的闭环，再逐步引入登录态和人工接管。

### Hermes 在这里扮演什么角色

Hermes 是 Agent / Harness，BrowserSkill 是浏览器技能，`bsk` 是本地连接器，Chrome/Edge 是实际执行环境：

```text
Hermes
  └── browser-skill
        └── bsk CLI / daemon
              └── BrowserSkill extension
                    └── Agent Window
                          └── Website
```

这也说明为什么它不是“给 Hermes 换一个模型”那么简单：模型只负责决策，浏览器能不能稳定工作，取决于 Skill、桥接层、浏览器状态和安全策略共同是否完整。

## 八、这些工具应该怎么选

| 你的任务 | 优先考虑 | 理由 |
| --- | --- | --- |
| 公开网页阅读、结构化提取 | `agent-browser` / Playwright | 独立、可重复、适合脚本化 |
| Windows + Hermes + 真实登录态 | BrowserSkill | 官方列出 Windows 和 Hermes，Agent Window 可见 |
| 直接操作当前 Chrome Tab | browser-bridge / realbrowser | 真实 Profile 和 Tab，但权限高、风险大 |
| WSL2 Agent 控制 Windows 浏览器 | Kachilu Browser | 项目明确把 WSL2 和 Windows-side profile 作为使用场景 |
| 多 Agent、隔离 Space、浏览器原生协作 | Ego Lite | 设计方向最完整，但当前平台支持受限 |
| 网络请求、Console、DOM 深度调试 | CDP / DevTools bridge | 底层能力强，但需要自己补生命周期和权限控制 |

不要只问“哪个工具最强”，更应该问：

```text
我要不要复用真实登录态？
我要不要操作我正在使用的 Tab？
任务是否需要并行？
失败后能否人工接管？
是否需要网络和 Console 级调试？
任务是否包含不可逆动作？
```

## 九、一个适合入门的练习任务

可以从下面这个任务开始：

> 打开一个公开网站，提取页面标题、三个链接和一段正文；不要登录、不要下载、不要提交任何表单。

把它拆成六个可验证步骤：

1. 创建一个新的 Browser Context 或 Agent Window。
2. 打开目标 URL，等待页面加载。
3. 获取页面 Snapshot 或可读文本。
4. 根据 role、name 或链接文本提取目标内容。
5. 截图或保存结构化结果，验证内容数量和 URL。
6. 关闭临时页面，并报告完成情况。

如果这六步稳定，再增加一个低风险的输入动作，例如在公开搜索框中输入关键词。最后才考虑真实登录、文件上传和需要确认的提交动作。

## 十、Browser Agent 的学习路线

### Level 0：理解页面

学习 HTML、DOM、CSS selector、ARIA role、accessible name 和 iframe。目标是知道“页面上看到的东西”在浏览器内部如何表示。

### Level 1：控制一个独立浏览器

用 Playwright 或 `agent-browser` 完成打开、快照、定位、点击、输入、等待、截图和关闭。先使用公开网站，避免登录态。

### Level 2：理解状态和隔离

区分 Browser Process、Profile、BrowserContext、Page 和 CDP Target。尝试同时运行两个 Context，确认 Cookie 和 Local Storage 不会互相污染。

### Level 3：接入真实浏览器

再学习 BrowserSkill、browser-bridge 或 realbrowser。重点不只是“能不能控制”，而是 Agent Window、Tab borrow、lease、handoff 和权限回收。

### Level 4：把浏览器变成 Skill

不要让 Agent 每次都从零探索同一个网站。把稳定的流程整理成 Skill：输入是什么、先观察什么、成功条件是什么、哪些动作必须询问用户、失败后如何恢复。

### Level 5：编排多个 Browser Agent

最后再考虑让 Hermes 做总管、让不同专家或 Worker 使用各自的 Browser Context。多 Agent 的价值在于隔离和并行，而不是简单地把更多模型同时连接到同一个 Chrome。

## 最后的判断

Browser for Agent 可以浓缩成一句话：

> **给模型一个真实但受控的浏览器，把页面变成可观察状态，把动作变成可验证步骤，把登录态放进明确的隔离边界。**

从工程上看，Browser Agent 不是“模型 + click”，而是：

```text
Reasoning
  + Observation
  + Action
  + Waiting
  + Verification
  + State Isolation
  + Human Handoff
  = Reliable Browser Agent
```

如果你在 Windows 上使用 Hermes，当前最稳妥的入门顺序是：

```text
Hermes
→ BrowserSkill
→ Agent Window
→ 公开网页
→ 低风险输入
→ 真实登录态
→ 人工确认的提交动作
```

先把“观察—操作—验证—停止”这条链做稳定，再追求更复杂的多 Agent、CDP 调试和浏览器级自动化。这样以后无论换成 `agent-browser`、Ego Lite、MCP Bridge 还是自建 adapter，理解都不会推倒重来。

## 参考资料

- [Tencent BrowserSkill](https://github.com/Tencent/BrowserSkill)
- [BrowserSkill Agent Install Guide](https://github.com/Tencent/BrowserSkill/blob/main/AGENT_INSTALL.md)
- [Vercel agent-browser](https://github.com/vercel-labs/agent-browser)
- [Playwright Browser Contexts](https://playwright.dev/docs/browser-contexts)
- [Chrome DevTools Protocol Accessibility](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/)
- [browser-bridge](https://github.com/whg517/browser-bridge)
- [realbrowser](https://github.com/darkamenosa/realbrowser)
- [Kachilu Browser](https://github.com/kachilu-inc/kachilu-browser)
- [Ego Lite](https://github.com/citrolabs/ego-lite)
