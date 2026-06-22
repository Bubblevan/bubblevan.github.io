---
title: "CloudWeGo 后端复盘"
weight: 1
math: true
---

在正式复盘 CloudWeGo、Go 后端和 COLA 分层之前，我需要先搞清楚一件事：这个项目到底是在解决什么问题。

StablePay 当前做的是一个面向 AI Agent 的支付系统。传统互联网产品里，支付通常是“人”在浏览器或 App 里完成的：用户点击购买按钮，进入支付页面，扫码或者输入密码，支付完成后再回到业务页面。但 Agent 不一样。Agent 没有传统意义上的浏览器交互，也不适合依赖“人手动点按钮、扫码、跳转页面”这一整套流程。

所以，StablePay 想做的是：让 AI Agent 自己拥有钱包，自己判断是否需要购买，自己调用支付工具完成付款，然后继续访问付费资源。

在之前的 demo 里，我们已经有一个 `showmethemoney-skill` 仓库，它更像是一个“单商品、单技能、单流程”的付费演示后端。OpenClaw 插件里也有一个类似 `stablepay_execute_paid_skill_demo` 的工具，用来演示 Agent 如何访问一个付费 Skill，遇到 402 后再发起支付。

这个 demo 是有价值的，因为它证明了最核心的支付链路：

```text
Agent 请求付费资源
  ↓
商家后端返回 402 Payment Required
  ↓
Agent 调用 StablePay Gateway 完成付款
  ↓
Agent 重试原请求
  ↓
商家后端验证付款成功
  ↓
返回解锁后的内容
```

但是，当我们从 demo 往真实产品推进时，这种写死的单技能流程就不够用了。

真实的商家后端应该至少支持：

1. 远程获取商品列表；
2. 每个商品有自己的标题、描述、价格、状态；
3. Agent 可以先浏览商品，再选择某一个商品购买；
4. 商家后端能根据商品信息生成 x402 付款要求；
5. 支付完成后，商家后端能验证购买状态并返回商品内容；
6. 后续可以部署到云上，接入 ACR、ACK、网关和监控体系。

因此，我现在要做的不是简单地再写一个 demo，而是从零搭建一个真正的 Merchant Server。

这个 Merchant Server 的定位可以这样理解：

```text
OpenClaw Plugin 是 Agent 侧的钱包和工具入口；
StablePay Gateway 是支付、验证和链上结算入口；
Merchant Server 是商家侧的商品和付费资源入口。
```

三者之间的关系大致是：

```text
OpenClaw Agent
  ↓ 查询商品 / 请求执行商品
Merchant Server
  ↓ 验证是否已支付
StablePay Gateway
  ↓ 链上支付与 proof
Solana / USDC
```

我希望这个 Merchant Server 最终具备几个特点。

第一，它要用 Go 写，因为我们现有后端技术栈更偏 Go 微服务体系，未来部署、维护和团队协作都会更统一。

第二，它要使用 CloudWeGo Hertz 作为 HTTP 框架。Hertz 是 CloudWeGo 生态中的 HTTP 框架，适合用来写高性能的 Go Web 服务。当前阶段我先只用 Hertz，不急着引入 Kitex RPC，因为这个商家后端第一阶段主要对外暴露 REST API。

第三，它要借鉴 COLA 四层架构思想。这里要特别说明，我不是在写 Java 版 COLA，也不是直接使用阿里巴巴 COLA 框架。我是在 Go 项目里吸收 COLA 的分层思想，把代码拆成适配层、应用层、领域层、基础设施层。

也就是：

```text
Adapter 层：处理 HTTP 请求和响应
Application 层：编排业务用例
Domain 层：表达核心业务规则
Infrastructure 层：处理数据库和外部服务调用
```

这样做的原因不是为了“看起来架构很高级”，而是因为这个项目会逐渐演进。第一阶段可能只是内存商品列表，第二阶段换成 SQLite，后面可能再换成 MySQL；第一阶段可能只是本地运行，后面会 Docker 化并部署到 ACK；第一阶段只支持单商品购买，后面可能会支持购物车、订单、库存、优惠和更多商品类型。

如果一开始就把 HTTP、数据库、支付验证、商品规则全部写在一个 Handler 里，那么项目很快就会变得难以维护。分层的目的，就是让每一部分代码只关心自己的职责。

所以这份学习笔记的路线不是“直接复制一个成熟框架”，而是从一个能跑起来的最小服务开始，一步一步往上加能力：

```text
第 1 步：CloudWeGo Hertz 最小服务 + /healthz
第 2 步：商品领域模型 + 内存仓储
第 3 步：商品列表 API
第 4 步：商品详情 API
第 5 步：x402 购买执行接口
第 6 步：StablePay Gateway 验证支付
第 7 步：SQLite 持久化
第 8 步：Docker + ACK 部署
第 9 步：OpenClaw 插件侧工具改造
```

这也是我写这份笔记的原因：我不想只是靠 vibe coding 把代码堆出来，而是希望自己能真正讲清楚每一层为什么存在、每个文件为什么这样放、每个对象为什么这样命名，以及这个后端如何从一个 MVP 慢慢演进成一个可以面试讲解的项目。
