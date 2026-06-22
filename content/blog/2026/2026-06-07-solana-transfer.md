---
date: 2026-06-07
title: OWS 转账 USDC：Solana 支付排障
authors: [bubblevan]
tags: []
---
## 1. Solana 支付、签名、ATA 和排障入门
我一开始以为，给同学的 OWS 钱包转 1.5 USDC，或许区块链浏览器会有一个转账接口，填上对方钱包地址、金额，然后调用一下就完了。后来真正开始查 Solana 的资料，才发现这件事没那么像传统 Web2 支付，也不像我们平时在钱包 App 里点几下那么简单。

在钱包界面里，用户看到的是“转账”。但在代码里，我们真正要做的是：
> 选择 Solana mainnet 这条链，确认 USDC 的 mint 地址，找到发送方和接收方各自的 USDC token account，必要时帮接收方创建 Associated Token Account，构造一笔包含 token transfer 指令的 Solana transaction，用本地钱包或私钥对这笔 transaction 签名，然后把签好名的交易发给 RPC，最后再查询这笔交易是否真的确认成功。

这也是为什么我之前只靠 AI 改脚本时一直卡住。AI 很容易给出一段“看起来像对的代码”，但如果你不理解 Solana 账户模型、SPL Token、签名、blockhash、RPC 提交和确认状态这些基础概念，一旦报错，就只能继续让 AI 猜。猜到最后，代码越改越乱，真正的问题却可能只是：把钱包主地址当成了 token account，把 devnet 的配置拿到 mainnet 用，或者以为 `sendTransaction` 返回了 signature 就等于到账成功。

这篇笔记的目标不是把 Solana 全部讲完（这个的纸上谈兵自学笔记在隔壁），而是只讲清楚完成一件具体事情所需的 **最小知识**：假如我有一个 OWS 钱包，我想在 Solana mainnet 上给另一个同学的 OWS 钱包转 1.5 USDC，我到底需要理解什么？应该怎么写脚本？遇到错误时应该怎么排查？

## 2. 前置概念
### 2.1 SPL Token

日常聊天里我们可能会说：“我给你的 OWS 钱包转 1.5 USDC。”这句话在人和人之间沟通没问题，但写代码或真正操作时需要更精确。为此，我们先要弄清楚几个最基本的概念。

首先，**Solana 是一条区块链**，可以把它理解成一个公开的、分布式的账本。在这个账本上，除了记录原生的 SOL 币之外，还可以记录其他资产，比如 USDC。  
其次，**USDC 是一种在区块链上发行的“代币（Token）”**，类似于现实世界中的“美元数字化凭证”。同一个 USDC 可以发行在不同的区块链上（比如以太坊、Solana、Polygon），但它们彼此独立，不能直接混用。

然后，**OWS 是一个本地钱包工具**。它负责安全地保存你的私钥、生成地址、对交易进行签名。OWS 本身不是一个区块链，也不是一个转账系统。

因此，我们要做的事情并不是“调用 OWS 的转账功能”，而是在 **Solana 这条区块链上构造并发送一笔代币转账交易**，并且 OWS 只是用来签名授权这笔交易。

那么，Solana 上的代币（如 USDC）遵循什么规则呢？**SPL Token** 就是 Solana 链上的官方代币标准，类似于以太坊上的 ERC‑20。SPL 是 **Solana Program Library** 的缩写，它是一套 Solana 官方维护的链上程序（智能合约）集合。
> 概念不用完全理解，略读就行：其中 **SPL Token** 这个程序定义了同质化代币（fungible token）的创建、转账、销毁等一系列标准操作。任何在 Solana 上发行的同质化代币——包括 USDC、USDT、SRM 等——都必须遵循 SPL Token 标准，才能被钱包、浏览器和各种应用正确识别和处理。

所以，我们这笔转账的本质是：**在 Solana 主网上执行一笔符合 SPL Token 标准的 USDC 转账交易**。具体流程是：

- 从我（转出方）的 Solana 地址所控制的 **USDC 代币账户（token account）** 中，转出 1.5 USDC；
- 转入到同学（接收方）的 Solana 地址对应的 USDC 代币账户；
- 整笔交易由我的钱包（OWS）签名授权；
- 交易被发送到 Solana 主网（mainnet）；
- 网络确认后，同学的钱包里就会显示收到 USDC。

这里有几个非常重要的点。

**第一**，同学需要给你的不是“OWS 钱包名字”，也不是本地钱包 ID，而是他 OWS 钱包里对应的 **Solana 主网地址**。这个地址通常是一串 Base58 字符，看起来像一长串大小写字母和数字（例如 `FMNs7xqezz4bYYioPyfqPzxLLmZyJhjSzbGApMdnrC2Z`）。只有拿到这个地址，你才知道转给谁。

**第二**，你要转的是 **Solana 主网上** 的 USDC，而不是以太坊、Polygon 或其他链上的 USDC，也不是测试网（devnet）上的测试 USDC。不同链上的 USDC 是完全不同的账户系统，地址格式、转账程序、RPC 节点、交易确认方式都不一样。转错了链，资产就会丢失。

**第三**，因为 Solana 采用 SPL Token 标准，USDC 的余额通常 **不是直接记录在你的主钱包地址上**，而是记录在一个叫做 **代币账户（token account）** 的地方。最常见的一种代币账户是 **ATA（Associated Token Account）**，可以把它理解成“某个钱包专门用来收存某一种特定代币的子账户”。例如，每个 Solana 地址都可以为自己的 USDC 派生出一个独一无二的 ATA，这个 ATA 的地址与主地址不同，但由主地址控制。

因此，我们要避免一个常见的误解：转账操作不是“从钱包地址 A 转到钱包地址 B”，而是 **“从钱包 A 的 USDC 代币账户转到钱包 B 的 USDC 代币账户”**。钱包主地址仍然非常重要，因为它是控制代币账户的“主人”，并且可以通过算法推导出对应的 ATA 地址；但在真正执行 USDC 转账指令时，交易中的 `source` 和 `destination` 字段应该填写代币账户的地址，而不是钱包的主地址。

### 2.2 钱包、地址、私钥、签名：到底谁在控制资产？
钱包不是钱本身。钱包更像一个密钥管理工具。Phantom、Solflare、Backpack、OWS 都可以是钱包。钱包负责保存私钥、派生地址、展示余额、发起签名、广播交易。钱包里看到的资产，其实是钱包帮你从链上查出来的状态。

地址是公钥的可读表示。别人给你转 SOL 或 USDC 时，通常会问你要地址。地址可以公开，别人知道地址只能给你转钱或查询链上公开状态，不能直接花你的钱。

私钥是控制权。谁掌握私钥，谁就能对交易签名，谁就能动用这个地址控制的资产。所以私钥不能发给别人，不能贴进聊天窗口，不能提交到 GitHub，也最好不要写死在脚本里。

签名是授权。Solana 网络不会因为你“登录了某个系统”就允许你转钱。它只认交易上的签名是否有效。你用私钥对一笔具体交易签名，相当于声明：“我同意执行这笔交易里的这些指令。”验证者可以用公钥验证签名是否来自对应私钥，但无法反推出私钥。

这也是本地签名的核心意义。RPC 节点不是银行柜台，也不是你的业务后端。它不会替你保管私钥，也不应该替你签名。你应该在本地钱包、硬件钱包、OWS 或受控脚本环境里完成签名，然后把签好名的交易发给 RPC。

> 如果用的是 OWS，理想模式一般不是把 OWS 的私钥导出来给 Python 脚本，而是让 OWS 继续承担“本地密钥托管和签名”的职责。脚本负责构造交易，OWS 负责签名，签完以后再广播。这样密钥边界更清楚，也更符合钱包的设计目标。
> 当然，学习和调试时也可以用本地 keypair 直接签名，比如用环境变量读取 Solana keypair JSON。这样上手快，但安全风险更高。只要脚本能碰到私钥，就必须把这个脚本和运行环境当成高风险资产来管理。

### 2.3 支付本质是一笔 transaction
在传统互联网产品里，支付可能是后端调用支付平台 API，然后数据库更新订单状态。但在 Solana 上，支付的核心对象是一笔 transaction，也就是交易。

一笔 Solana transaction 里面通常包含：

- 签名列表；
- 交易消息 message；
- message 里的账户列表；
- message 里的 recent blockhash；
- message 里的一个或多个 instruction。

instruction 可以理解成“要求某个链上程序做一件事”。比如转 SOL，通常是让 System Program 做 lamports 转移。转 USDC，则是让 Token Program 把一定数量的 token 从一个 token account 移到另一个 token account。

这点非常重要：Solana 的交易不是一个“转账 API 请求”，而是一组要被链上程序执行的指令。你构造 transaction 时，必须把这些 **指令** 需要读写的账户、签名者、金额、mint、destination 等信息准备好。签名之后，RPC 只是把这笔交易送进网络，链上的程序会根据规则执行它。

一笔 transaction 可以包含多条 instruction，而且这些 instruction 通常是 **原子执行** 的。所谓原子执行，就是要么整笔交易成功，要么整笔交易失败。比如你给同学转 USDC 时，如果同学还没有 USDC ATA，你可以在同一笔交易里先创建他的 ATA，再执行 USDC 转账。如果第二步转账失败，整笔交易失败，前面的创建动作也不会作为成功结果单独留下来。

### 2.4 USDC 的 mint、decimals 和最小单位
接下来讲 USDC。我们平时说“转 1.5 USDC”，但程序不能只写一个字符串 `"USDC"`。链上必须知道你转的是哪个 mint。

mint 可以理解成某种 SPL Token 的发行定义。Solana 上每种 SPL Token 都有自己的 mint 地址。USDC 在 Solana mainnet 上有官方 mint 地址。
写脚本时一定要明确使用 Solana mainnet 上的 USDC mint，而不是其他 token 的 mint，也不是 devnet 上的测试 mint。

其次，USDC 有 decimals，也就是小数位。Solana 程序执行 token 转账时使用整数最小单位，不直接使用 1.5 这种小数。USDC 常见 decimals 是 6，所以：

1 USDC = 1,000,000 个最小单位
1.5 USDC = 1,500,000 个最小单位
0.01 USDC = 10,000 个最小单位

如果你在代码里把 `1.5` 直接作为链上 amount 传入，那就是错误的。正确做法是把人类可读金额转换成整数最小单位。更稳妥的写法是使用字符串或 Decimal 处理金额，避免浮点数精度问题。

例如：

```python
from decimal import Decimal

USDC_DECIMALS = 6

def ui_amount_to_base_units(amount: str, decimals: int) -> int:
    return int(Decimal(amount) * (10 ** decimals))

amount = ui_amount_to_base_units("1.5", USDC_DECIMALS)
print(amount)  # 1500000
```

这段代码本身很简单，但背后的原则非常重要：链上转账金额永远应该是整数最小单位。UI 展示的是 1.5，链上指令里放的是 1500000。日志里最好同时打印这两个值，这样排障时不会看到一个孤零零的数字，不知道它到底是不是预期金额。

### 2.5 为什么转 USDC 还要 SOL？
很多人第一次写 token 转账时会困惑：我钱包里有 USDC，为什么还提示余额不足？原因是 Solana 上的交易手续费用 SOL 支付，不是用 USDC 支付。

即使你转的是 USDC，交易本身仍然需要 fee payer 支付 SOL。fee payer 通常是发送方钱包，也可以是其他愿意代付的账户。只要这个账户要付手续费，它就必须签名，因为它授权花费自己的 SOL。

除了基础交易费，**创建 ATA 也需要 SOL**。Solana 上创建账户需要为账户分配存储空间并满足 rent-exempt 要求。
直观理解就是：如果同学从来没收过 Solana USDC，他的钱包可能还没有 USDC ATA。你第一次给他转 USDC 时，需要先创建这个 token account，而创建账户的人要付一小笔 SOL 成本。

所以，检查“我能不能转 1.5 USDC”时，不能只看 USDC 余额。你至少要检查：
- 发送方是否有足够 USDC；
- 发送方或 fee payer 是否有足够 SOL；
- 发送方 USDC ATA 是否存在；
- 接收方 USDC ATA 是否存在；
- 如果接收方 ATA 不存在，脚本是否会创建；
- 创建 ATA 的 payer 是否有 SOL 并且会签名。

### 2.6 ATA
ATA 是 Associated Token Account 的缩写。它是由“钱包地址 + token mint”确定性派生出来的标准 token account。

可以这样理解：
- 钱包主地址：代表一个用户或一个钱包。
- USDC mint：代表 Solana mainnet 上的 USDC。
- USDC ATA：代表这个钱包用来存放 Solana USDC 的标准 token account。

假如 Alice 的钱包地址是 A，Solana USDC 的 mint 是 M，那么 Alice 的 USDC ATA 就可以由 A 和 M 推导出来。Bob 的钱包地址是 B，那么 Bob 的 USDC ATA 就由 B 和 M 推导出来。别人给 Bob 转 USDC 时，通常应该转到 Bob 的 USDC ATA，而不是直接转到 Bob 的主钱包地址。

但是，能推导出 ATA 地址，不代表这个账户已经存在。可以把 ATA 地址理解成一个可以提前算出来的门牌号，但门牌号存在不代表房子已经建好。只有账户真的在链上创建并初始化后，它才可以接收 token。

因此，一个健壮的转账脚本通常这样做：
1. 先根据发送方钱包地址和 USDC mint 推导发送方 USDC ATA；
2. 再根据接收方钱包地址和 USDC mint 推导接收方 USDC ATA；
3. 查询接收方 ATA 是否存在；
4. 如果不存在，就在交易里添加创建 ATA 的 instruction；
5. 然后添加 TransferChecked 转账 instruction；
6. 最后签名并发送。

这也是为什么很多示例代码里会出现 `get_associated_token_address`、`create_associated_token_account` 之类的调用。前者只是推导地址，后者才是在链上创建账户。推导地址不需要签名、不花钱；创建账户是链上状态变更，需要交易、签名和 SOL。

排障时一定要区分这两步。很多错误不是“转账失败”，而是“destination token account 不存在”。也有一些错误是把钱包主地址错误地传给了 token transfer 的 destination，导致 Token Program 发现这个账户不是合法的 token account。

> 一句话总结：SPL Token 转账发生在 token account 之间，ATA 是钱包地址和某个 token mint 对应的标准 token account。

### 2.7 TransferChecked vs Transfer？
SPL Token 转账常见有两类指令：Transfer 和 TransferChecked。两者都和 token 转账有关，但 TransferChecked 更适合支付脚本，尤其是转 USDC 这种有真实价值的资产。

普通 Transfer 主要告诉 Token Program：从哪个 token account 转到哪个 token account，转多少。它默认你已经把账户和 mint 关系处理对了。

TransferChecked 会多要求你提供 mint 和 decimals，并在执行时检查这些信息是否符合预期。也就是说，它不仅转账，还会检查“这是不是我以为的那个 token”和“精度是不是我以为的那个精度”。

这听起来只是多写几个参数，但对真实支付非常有用。假如你不小心填错了 mint、混用了 devnet/mainnet 配置，或者把某个 token account 搞错了，TransferChecked 更容易让交易失败，而不是悄悄执行一笔不符合预期的转账。对于支付来说，失败并不可怕，静默转错才可怕。

### 2.8 mainnet、devnet 和 testnet
Solana 有不同的 cluster，常见的是 mainnet、devnet、testnet。它们不是同一个网络的不同视图，而是不同环境。
- mainnet 是真实资产环境。这里的 SOL、USDC 都有真实金融价值。
- devnet 是开发测试环境。它适合调试程序、测试流程，资产没有真实价值。
- testnet 更偏网络升级、性能和验证者测试。

新手最容易犯的错误之一，就是网络混用。比如：
- RPC 指向 mainnet，但浏览器 explorer 还在 devnet。
- 在 devnet 上创建了 ATA，却以为 mainnet 上也有。
- 使用 devnet 测试 USDC mint，却在 mainnet 上转。
- devnet 钱包里有空投 SOL，以为 mainnet 钱包也能付手续费。
- 拿 mainnet 的交易 signature 去 devnet explorer 查，当然查不到。
- 本地 CLI 配置是 devnet，但 Python 脚本里写的是 mainnet RPC。
这些错误很隐蔽，因为 Solana 地址看起来都像一串 Base58 字符，单看格式不容易分辨属于哪个网络。地址本身不是“带网络前缀”的，所以你必须通过 RPC、mint、explorer、日志来确认自己到底在哪个 cluster 操作。

建议所有脚本启动时都打印：当前 cluster；RPC URL；USDC mint；发送方地址；接收方地址；source ATA；destination ATA；amount 的 UI 值和最小单位值。
真实排障时，越早记录关键上下文，越少靠猜。

### 2.8 recent blockhash：为什么签好的交易会过期？
Solana transaction 里有一个很重要的字段叫 recent blockhash。可以把它理解成交易的时效戳。它用于防止旧交易被无限期重复提交。

这意味着：Solana 交易不是签好以后永久有效。如果你获取 blockhash、构造交易、签名，然后隔了太久才发送，这笔交易可能会因为 blockhash 过期而失败。常见表现包括 blockhash not found、transaction expired，或者提交后一直查不到成功状态。

更关键的是，blockhash 是交易 message 的一部分，而签名是对具体 message 的签名。所以如果你更换了 blockhash，就必须重新签名。不能拿旧签名配新 blockhash，也不能先签名再随便改交易内容。

这解释了一个常见排障结论：修改交易内容后一定要重新签名。这里的交易内容包括收款地址、金额、账户列表、instruction、recent blockhash 等。只要 message 变了，旧签名就不再对应新交易。

实际写脚本时，比较稳妥的流程是：
1. 获取最新 blockhash；
2. 构造 transaction message；
3. 立即签名；
4. 立即发送；
5. 根据 signature 查询状态。

### 2.9 RPC：它只是入口，不是最终成功证明
RPC 是脚本和 Solana 网络交互的入口。你通过 RPC 查询账户、获取 blockhash、模拟交易、提交交易、查询交易状态。

但 RPC 不是银行，不是你的支付后端，也不是担保方。你调用 `sendTransaction`，通常是把一笔已经签名的交易提交给 RPC。RPC 可以做一些预检查和转发，但它返回 signature 并不代表交易已经最终成功。


## 3. 完整排障流程
把上面的概念连起来，一次完整转账可以拆成以下步骤。

第一步，确认网络是 Solana mainnet。
RPC、explorer、USDC mint、钱包余额都必须属于 mainnet。不要混用 devnet。

第二步，拿到收款人的 Solana 地址。
让同学从 OWS 钱包里复制 Solana mainnet 地址，而不是复制钱包名称、钱包 ID 或其他链的地址。

第三步，确认 USDC mint 和 decimals。
Solana mainnet USDC 有固定 mint，USDC decimals 是 6。1.5 USDC 要转换为 1,500,000。

第四步，确认发送方有 USDC 和 SOL。
USDC 用来转给同学，SOL 用来支付交易手续费和可能的 ATA 创建成本。

第五步，推导发送方和接收方的 USDC ATA。
source ATA 是发送方的 USDC token account；destination ATA 是接收方的 USDC token account。

第六步，检查接收方 ATA 是否存在。
如果不存在，就在交易里添加创建 ATA 的 instruction。

第七步，添加 TransferChecked instruction。
从 source ATA 转 1,500,000 个最小单位到 destination ATA，并指定 USDC mint 和 decimals。

第八步，获取 latest blockhash。
这一步给交易一个有效期。

第九步，构造 transaction 并签名。
如果直接用 keypair，脚本签名；如果用 OWS，则把交易交给 OWS 签名。

第十步，发送交易。
通过 RPC 提交 signed transaction，拿到 signature。

第十一步，确认交易状态。
不要只看 signature。要查询交易是否 confirmed 或 finalized，是否有错误日志。

第十二步，记录结果。
日志中保留 signature、cluster、RPC、mint、amount、sender、receiver、source ATA、destination ATA、确认状态。

这就是一笔 Solana USDC 支付的完整骨架。

### 3.1 一个 OWS 钱包、两个收款地址、一笔 Solana USDC 转账
这次环境里，发送方不是普通 Solana CLI 钱包，而是一个 OWS 钱包。`ows wallet list` 里能看到类似这样的信息：

```text
ID:      071ccfe1-c6c4-4b4c-bbad-274033f17c61
Name:    stablepay-agent
Secured: ✓ (encrypted)
  eip155:1 (ethereum) → 0x9a1C3803Fb4A68c8824a82fc9013D29d8617327C
  solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp (solana) → 2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF
```

这里最重要的是 Solana 地址：

```text
2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF
```

它是 `stablepay-agent` 这个 OWS 钱包在 Solana mainnet 上的地址。钱包里有 USDC，但一开始没有 SOL。两个收款地址是：

```text
Et7cSfibAZHUMQEMfpsqnHaJtA2UqvxyygAHUqApiecU
Gub6tcj7GFkgc15WjMdGHUSnnmxqgo8aCNNwk5znJxGj
```

目标很简单：给这两个地址各转 `1.5 USDC`。

Solana mainnet 上 USDC 的 mint 是：

```text
EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
```

USDC 的 decimals 是 6，所以：

```text
1 USDC   = 1,000,000
0.01 USDC = 10,000
1.49 USDC = 1,490,000
1.5 USDC  = 1,500,000
```
一开始我想得比较简单：既然 OWS 钱包里有 USDC，那是不是直接找个工具发一下就行？于是先试了 Mirage。

### 3.2 Mirage
#### 3.2.1 什么是 Mirage？
Mirage 是由 Solana 生态的 **MagicBlock** 团队开发的一款 **命令行（CLI）隐私支付工具**。它的定位是 **让用户（包括 AI 代理）能在 Solana 上像普通转账一样操作，但可以选择性地隐藏交易的关键细节**。

为了理解这个功能的价值，我们需要先弄清楚一个容易被忽视的事实：**在 Solana（以及几乎所有公链）上，正常交易是完全透明的**。
- 正常交易：你随便在一个区块链浏览器（比如 Solscan）里输入一个钱包地址，就能看到它的每一笔转账记录：何时、向谁、转了多少。如果你用 Phantom、Backpack 或 OWS 直接签名发送一笔 USDC，发送方地址、接收方地址、金额都会 **永久公开** 地记录在链上。任何人都能分析地址之间的资金流动。
- 隐藏交易：Mirage 的隐私功能（通过 `mirage private-transfer` 子命令启用）可以在链上公开信息中 **混淆发送方、接收方和金额**。它使用的核心技术叫 **私有化临时 Rollup（Private Ephemeral Rollup, PER）**，结合硬件级可信执行环境（TEE，如 Intel TDX），在 Solana 主网之外创建一个临时、加密的私有执行环境。核心逻辑（金额、地址）在这个“黑盒子”里处理，经过混淆后再提交到 Solana 主网。外人看到的是一团经过“打码”的交易数据，无法建立“A 地址 → B 地址”的直接关联，也不知道具体金额。

#### 3.2.2 为什么需要隐藏交易？
在 Web3 世界里，完全透明会带来一些现实问题，尤其对机器人、AI 代理或处理敏感资产的用户：
- **防止抢跑和三明治攻击**：如果你的交易机器人策略公开，恶意节点可以监控你的交易，在你之前插入自己的交易（抢跑）或通过套利攻击（三明治）来获利。Mirage 的隐私保护可以隐藏你的交易意图。
- **保护交易策略机密**：高频交易或量化策略的核心是“买什么、卖什么、何时交易”。透明链上记录等于直接公开源代码。
- **避免地址关联追踪**：即使普通用户，也可能不希望别人通过链上记录追踪自己的消费习惯、收入来源。隐私功能可以从源头切断关联分析。
- **保障商业支付机密**：工资发放、供应链结算等通常属于商业机密，不宜公开给所有人。

#### 3.2.3 Mirage 的主要功能与特性
- **私密 SPL 代币转账**：支持 USDC、USDT 等主流代币的隐私版转账。
- **金额混淆**：自动将单笔大额转账拆分为最多 15 笔随机金额的小额交易，并做整数倍混淆，外人无法计算真实总额。
- **时序混淆**：在转账时引入随机时间延迟，外人无法通过时间关联推断哪些子交易属于同一次转账。
- **AI 代理集成**：可以安装为 Claude Code Skill，实现与 AI 工作流的无缝集成，让 AI 能执行私密链上操作。
- **CLI 交互**：完全通过终端命令操作，适合开发者和高级用户在脚本、机器人中集成。

#### 3.2.4 Mirage 与 OWS 的分工
在一次转账中，Mirage 和 OWS 扮演了清晰互补的角色：
| 角色 | 工具 | 核心职责 | 类比 |
| :--- | :--- | :--- | :--- |
| **私钥管理员** | OWS | 安全保管私钥，对交易进行签名授权 | 你的“私密印章” |
| **交易执行者** | Mirage | 构建交易、混淆隐私、请求签名、广播上链 | 你的“专业跑腿小哥” |

Mirage 负责构建这笔带“隐身衣”的转账交易，然后调用 OWS 请求签名，最后将签名后的交易广播到 Solana 网络。OWS 本身不直接与网络交互，Mirage 也不保存私钥。

### 3.3 坑1：RPC
回到我们的具体转账任务。发送方是一个 OWS 钱包 `stablepay-agent`，Solana 地址为 `2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF`。钱包里有 USDC，但一开始没有 SOL。两个收款地址分别是 `Et7cSfibAZHUMQEMfpsqnHaJtA2UqvxyygAHUqApiecU` 和 `Gub6tcj7GFkgc15WjMdGHUSnnmxqgo8aCNNwk5znJxGj`。目标是给这两个地址各转 `1.5 USDC`。

Solana mainnet 上 USDC 的 mint 地址是 `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`，decimals 为 6，因此 `1.5 USDC = 1,500,000` 单位。

一开始我尝试使用 Mirage 进行普通（非隐私）转账。先设置环境变量：

```bash
export RPC_URL="https://api.mainnet-beta.solana.com"
export WALLET="stablepay-agent"
export SRC="2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF"
export USDC_MINT="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

export TO_1="Et7cSfibAZHUMQEMfpsqnHaJtA2UqvxyygAHUqApiecU"
export TO_2="Gub6tcj7GFkgc15WjMdGHUSnnmxqgo8aCNNwk5znJxGj"
```
确认 Mirage 能读到 OWS 钱包地址：
```bash
mirage address --wallet "$WALLET"
# 输出: 2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF
```
查余额（后来打入了 SOL 后）：
```bash
mirage balance --wallet "$WALLET"
# 输出类似:
# 0.005901 SOL    $0.38        Solana
# 2.300000 USDC   $2.30        USDC
```
尝试给第一个地址转 `0.01 USDC`（测试）：
```bash
mirage transfer \
  --wallet "$WALLET" \
  --cluster mainnet \
  --rpc-url "$RPC_URL" \
  --visibility public \
  --from-balance base \
  --to-balance base \
  --mint "$USDC_MINT" \
  --amount 0.01 \
  --to "$TO_1" \
  --memo "test transfer 0.01 USDC to recipient 1"
```
结果遇到：
```text
fetch failed
```

这个错误一开始很迷惑，没有说明是 RPC 失败、MagicBlock API 失败还是 OWS 签名失败。排查发现当时 `https://api.mainnet-beta.solana.com` 的某些 RPC 请求不稳定：`getHealth` 可以返回 `ok`，但 `getAccountInfo` 会卡住。换成另一个稳定 RPC `https://api.mainnet.solana.com` 后，USDC mint 的 `getAccountInfo` 能正常返回，里面显示：
```text
decimals: 6
owner: TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
```
### 3.4 坑2：SOL
换 RPC 之后，我再次执行 Mirage 转账，结果变成：
```text
broadcast failed: RPC error:
Transaction simulation failed:
Attempt to debit an account but found no record of a prior credit.
AccountNotFound
```
这句话的意思不是说 USDC 不够，而是说交易模拟时要从某个账户扣 lamports，但链上没有这个账户的 prior credit。通俗说，就是 fee payer 这个 Solana 账户没有 SOL，甚至没有链上余额记录。

我查了一下发送方和另一个有 SOL 的 gas 钱包：
```bash
export SRC="2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF"
export GAS="9Qe1uxmznPUnGcmLG7HSSsHcoC3cFxY54PPNAKTFnq2u"

curl -sS "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getBalance\",\"params\":[\"$SRC\",{\"commitment\":\"confirmed\"}]}" \
  | python -c 'import sys,json; j=json.load(sys.stdin); print("SRC SOL =", j["result"]["value"]/1_000_000_000)'

curl -sS "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getBalance\",\"params\":[\"$GAS\",{\"commitment\":\"confirmed\"}]}" \
  | python -c 'import sys,json; j=json.load(sys.stdin); print("GAS SOL =", j["result"]["value"]/1_000_000_000)'
```
结果是：
```text
SRC SOL = 0.0
GAS SOL = 0.041519104
```

这就对上了。我的 OWS 钱包 `2gL5...` 里有 USDC，但没有 SOL。Solana 上转 USDC 也要付 SOL 手续费。如果收款人还没有对应 USDC ATA，还可能要额外付创建 ATA 的 rent 成本。USDC 不能自动拿来抵扣 Solana gas。

我当时想：能不能让另一个地址 `9Qe1...` 代付 gas？Solana 原理上可以，一笔 transaction 可以让 A 付 fee，让 B 授权移动 token。但 Mirage 的 CLI 并没有暴露一个简单的 `--fee-payer` 参数给我用，所以最稳的办法不是硬做 gas sponsor，而是先从 `9Qe1...` 给 `2gL5...` 转一点 SOL。

这个 `9Qe1...` 钱包是我之前用 Solana keygen 生成的：

```bash
solana-keygen new \
  --outfile ~/.config/stablepay-mainnet/fee-payer-mainnet.json
```

确认这个 keypair 文件对应的公钥：

```bash
export FEE_KP="$HOME/.config/stablepay-mainnet/fee-payer-mainnet.json"
solana-keygen pubkey "$FEE_KP"
```

输出是：

```text
9Qe1uxmznPUnGcmLG7HSSsHcoC3cFxY54PPNAKTFnq2u
```

说明这个 keypair 文件就是有 SOL 的那个地址。

我一开始尝试用 Solana CLI 转 SOL：

```bash
solana transfer "$SRC" 0.01 \
  --from "$FEE_KP" \
  --fee-payer "$FEE_KP" \
  --allow-unfunded-recipient \
  --url "$RPC_URL"
```
但 CLI 对 RPC 请求报错：
```text
Error: error sending request for url (...)
```
于是我绕开 CLI，用 Python 直接从 keypair 文件发 SOL。脚本如下：

```python
import json
import os
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import transfer, TransferParams
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client

RPC_URL = os.environ.get("RPC_URL", "https://api.mainnet-beta.solana.com")
FEE_KP = os.environ["FEE_KP"]
TO_ADDR = os.environ["SRC"]

LAMPORTS_PER_SOL = 1_000_000_000
AMOUNT_SOL = "0.01"
LAMPORTS = int(float(AMOUNT_SOL) * LAMPORTS_PER_SOL)

with open(FEE_KP, "r") as f:
    secret = json.load(f)

payer = Keypair.from_bytes(bytes(secret))
to_pubkey = Pubkey.from_string(TO_ADDR)

client = Client(RPC_URL)

print("RPC:", RPC_URL)
print("From:", payer.pubkey())
print("To:", to_pubkey)
print("Amount SOL:", AMOUNT_SOL)
print("Lamports:", LAMPORTS)

balance = client.get_balance(payer.pubkey()).value
print("From balance before:", balance / LAMPORTS_PER_SOL, "SOL")

ix = transfer(
    TransferParams(
        from_pubkey=payer.pubkey(),
        to_pubkey=to_pubkey,
        lamports=LAMPORTS,
    )
)

latest = client.get_latest_blockhash().value.blockhash
msg = MessageV0.try_compile(
    payer=payer.pubkey(),
    instructions=[ix],
    address_lookup_table_accounts=[],
    recent_blockhash=latest,
)

tx = VersionedTransaction(msg, [payer])

resp = client.send_transaction(tx)
print("Signature:", resp.value)
```
运行：
```bash
export RPC_URL="https://api.mainnet-beta.solana.com"
export FEE_KP="$HOME/.config/stablepay-mainnet/fee-payer-mainnet.json"
export SRC="2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF"

python /tmp/send_sol_fee_payer.py
```
输出：
```text
RPC: https://api.mainnet-beta.solana.com
From: 9Qe1uxmznPUnGcmLG7HSSsHcoC3cFxY54PPNAKTFnq2u
To: 2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF
Amount SOL: 0.01
Lamports: 10000000
From balance before: 0.041519104 SOL
Signature: 4drqjG5qDU2SarxNPTj8Cqk2X8Zmdmt5jh4r3WWXzXYChp8d6etFhArh4w5ZqWV4xQ4DyoPswD5xXX7XaV2V4ShW
```

再查余额：

```bash
solana -u mainnet-beta balance "$SRC"
solana -u mainnet-beta balance "$GAS"
```

结果：

```text
0.01 SOL
0.031514104 SOL
```

这一步之后，`2gL5...` 已经有 SOL，可以作为 fee payer 继续转 USDC。

> 这里要强调一个安全点：`~/.config/stablepay-mainnet/fee-payer-mainnet.json` 是 Solana keypair 文件，里面是能直接控制 `9Qe1...` 资产的私钥材料。不要把这个文件内容发给 AI，不要截图，不要提交到 GitHub。我们这里只是用它给 OWS 地址打了一点 SOL。


### 3.5 坑3：OWS passphrase
在 Mirage 执行时，它提示：
```text
OWS passphrase (press enter for none):
```

我一开始不知道 OWS passphrase 是什么，所以直接回车跳过。后来我也怀疑：是不是因为 passphrase 没填，所以转账失败？

从实际日志看，这次不是。

原因是，如果 passphrase 真错了，或者 OWS 钱包无法解密，错误通常会发生在签名阶段。也就是说，程序应该在“拿不到签名”时就失败，不会进入 Solana RPC 模拟，更不会出现 Token Program 的链上执行日志。

但我遇到的错误是：
```text
broadcast failed: RPC error:
Transaction simulation failed
```

后面甚至有链上 program logs：

```text
Program ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL invoke [1]
Program log: CreateIdempotent
Program ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL success
Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke [1]
Program log: Error: InvalidAccountData
Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA failed: invalid account data for instruction
```

这说明交易已经签名并提交到 RPC 进行 simulation 了。换句话说，至少在这次环境里，空回车并没有阻止 OWS 给交易签名。可能这个钱包的加密 passphrase 为空，也可能 OWS 当前配置允许这样签；但无论原因是什么，这次 `InvalidAccountData` 不是 passphrase 引起的。

### 3.6 坑4：`InvalidAccountData`
给 `2gL5...` 打入 SOL 后，我再次用 Mirage 测试 `0.01 USDC`：
```bash
mirage transfer \
  --wallet "$WALLET" \
  --cluster mainnet \
  --rpc-url "$RPC_URL" \
  --visibility public \
  --from-balance base \
  --to-balance base \
  --mint "$USDC_MINT" \
  --amount 0.01 \
  --to "$TO_1" \
  --memo "test transfer 0.01 USDC to recipient 1"
```

这次不再是 `AccountNotFound`，而是：
```text
Transaction simulation failed:
Error processing Instruction 1: invalid account data for instruction
```
日志里更关键的是：
```text
Program AToken... CreateIdempotent success
Program Tokenkeg... Error: InvalidAccountData
```
第一条 instruction 是 Associated Token Account Program 的 `CreateIdempotent`，它成功了。第二条 instruction 进入 Token Program 转账时失败，错误是 `InvalidAccountData`。

这个错误通常说明 Token Program 收到的某个账户，不是它期望的 token account 数据格式。SPL Token 转账不是从“钱包主地址”转到“钱包主地址”，而是从“发送方 USDC token account”转到“接收方 USDC token account”。如果构造交易时把某个普通 wallet address 当成 source/destination token account，或者余额类型被解释错，就可能出现这种错误。

我查了发送方的 USDC token account：
```bash
curl -sS "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\":\"2.0\",
    \"id\":1,
    \"method\":\"getTokenAccountsByOwner\",
    \"params\":[
      \"$SRC\",
      {\"mint\":\"$USDC_MINT\"},
      {\"encoding\":\"jsonParsed\",\"commitment\":\"confirmed\"}
    ]
  }" | python /tmp/show_token_accounts.py
```
输出：
```text
tokenAccount: E8o2ozKCCckYWKsNKZgyCsVU98uEbZDXCa52h7D5pgoT
owner: 2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF
mint: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
amount: 5300000
uiAmountString: 5.3
```

这说明发送方 USDC ATA 确实存在，余额也是 `5.3 USDC`。问题不在“没有 USDC”，而在 Mirage 构造出来的 transfer instruction 对账户的解释不符合这个普通 SPL Token 转账场景。

所以我最后没有继续硬调 Mirage。既然我们已经明确知道自己要做什么，那就自己构造最标准的 Solana SPL Token 交易：
- 创建接收方 ATA，如果它还不存在；
- 用 TransferChecked 从发送方 USDC ATA 转到接收方 USDC ATA；
- 用 OWS 对 transaction 签名；
- 用 RPC simulate、send、confirm。

这就是最后跑通的方案。

## 4. 最终跑通方案
最终可用的工具链是：
```text
@solana/web3.js        负责 Solana transaction、RPC、发送确认
@solana/spl-token      负责 ATA 和 TransferChecked 指令
@open-wallet-standard/core 负责调用 OWS 钱包签名
```
先创建目录并安装依赖：
```bash
mkdir -p ~/stablepay-tools
cd ~/stablepay-tools

npm init -y
npm install @solana/web3.js @solana/spl-token @open-wallet-standard/core
```
然后写脚本 `transfer-usdc-ows.mjs`：
```javascript
import {
  Connection,
  PublicKey,
  Transaction,
} from "@solana/web3.js";

import {
  getAssociatedTokenAddressSync,
  createAssociatedTokenAccountIdempotentInstruction,
  createTransferCheckedInstruction,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";

import {
  signTransaction,
} from "@open-wallet-standard/core";

const [
  ,
  ,
  recipientArg,
  amountArg = "0.01",
] = process.argv;

if (!recipientArg) {
  console.error("Usage: node transfer-usdc-ows.mjs <recipient_wallet> <amount_ui>");
  process.exit(1);
}

const RPC_URL = process.env.RPC_URL || "https://api.mainnet-beta.solana.com";
const WALLET = process.env.WALLET || "stablepay-agent";
const SRC = new PublicKey(process.env.SRC);
const USDC_MINT = new PublicKey(process.env.USDC_MINT);
const RECIPIENT = new PublicKey(recipientArg);

const USDC_DECIMALS = 6;

function uiAmountToBaseUnits(amountUi, decimals) {
  if (!/^\d+(\.\d+)?$/.test(amountUi)) {
    throw new Error(`Invalid amount: ${amountUi}`);
  }

  const [whole, fraction = ""] = amountUi.split(".");
  if (fraction.length > decimals) {
    throw new Error(`Too many decimal places. USDC supports ${decimals}.`);
  }

  return BigInt(whole) * 10n ** BigInt(decimals)
    + BigInt(fraction.padEnd(decimals, "0") || "0");
}

const amountBaseUnits = uiAmountToBaseUnits(amountArg, USDC_DECIMALS);

const connection = new Connection(RPC_URL, "confirmed");

const sourceAta = getAssociatedTokenAddressSync(
  USDC_MINT,
  SRC,
  false,
  TOKEN_PROGRAM_ID,
);

const recipientAta = getAssociatedTokenAddressSync(
  USDC_MINT,
  RECIPIENT,
  false,
  TOKEN_PROGRAM_ID,
);

console.log("RPC:", RPC_URL);
console.log("OWS wallet:", WALLET);
console.log("Source wallet:", SRC.toBase58());
console.log("Recipient wallet:", RECIPIENT.toBase58());
console.log("USDC mint:", USDC_MINT.toBase58());
console.log("Source USDC ATA:", sourceAta.toBase58());
console.log("Recipient USDC ATA:", recipientAta.toBase58());
console.log("Amount UI:", amountArg);
console.log("Amount base units:", amountBaseUnits.toString());

const latest = await connection.getLatestBlockhash("confirmed");

const tx = new Transaction({
  feePayer: SRC,
  recentBlockhash: latest.blockhash,
});

tx.add(
  createAssociatedTokenAccountIdempotentInstruction(
    SRC,
    recipientAta,
    RECIPIENT,
    USDC_MINT,
    TOKEN_PROGRAM_ID,
  ),
);

tx.add(
  createTransferCheckedInstruction(
    sourceAta,
    USDC_MINT,
    recipientAta,
    SRC,
    amountBaseUnits,
    USDC_DECIMALS,
    [],
    TOKEN_PROGRAM_ID,
  ),
);

const unsignedBytes = tx.serialize({
  requireAllSignatures: false,
  verifySignatures: false,
});

const unsignedHex = Buffer.from(unsignedBytes).toString("hex");

const signResult = signTransaction(
  WALLET,
  "solana",
  unsignedHex,
  process.env.OWS_PASSPHRASE || undefined,
);

if (!signResult?.signature) {
  throw new Error("OWS did not return a signature.");
}

tx.addSignature(SRC, Buffer.from(signResult.signature, "hex"));

const signedBytes = tx.serialize({
  requireAllSignatures: true,
  verifySignatures: true,
});

const simulation = await connection.simulateTransaction(tx);

if (simulation.value.err) {
  console.error("Simulation failed:");
  console.error(JSON.stringify(simulation.value.err, null, 2));
  console.error("Logs:");
  console.error((simulation.value.logs || []).join("\n"));
  process.exit(1);
}

console.log("Simulation ok. Sending transaction...");

const sig = await connection.sendRawTransaction(signedBytes, {
  skipPreflight: false,
  preflightCommitment: "confirmed",
});

console.log("Signature:", sig);

const confirmation = await connection.confirmTransaction(
  {
    signature: sig,
    blockhash: latest.blockhash,
    lastValidBlockHeight: latest.lastValidBlockHeight,
  },
  "confirmed",
);

if (confirmation.value.err) {
  console.error("Confirmation failed:");
  console.error(JSON.stringify(confirmation.value.err, null, 2));
  process.exit(1);
}

console.log("Confirmed:", sig);
```
再设置环境变量：
```bash
export RPC_URL="https://api.mainnet-beta.solana.com"
export WALLET="stablepay-agent"
export SRC="2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF"
export USDC_MINT="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

export TO_1="Et7cSfibAZHUMQEMfpsqnHaJtA2UqvxyygAHUqApiecU"
export TO_2="Gub6tcj7GFkgc15WjMdGHUSnnmxqgo8aCNNwk5znJxGj"
```

先给两个地址各试转 `0.01 USDC`：

```bash
cd ~/stablepay-tools

node transfer-usdc-ows.mjs "$TO_1" 0.01
node transfer-usdc-ows.mjs "$TO_2" 0.01
```

成功时，输出里会有这些关键信息：

```text
RPC: https://api.mainnet-beta.solana.com
OWS wallet: stablepay-agent
Source wallet: 2gL5tHKBp2ZWGX9chgcHFtEqLcwG2GT76CimizqFqXXF
Recipient wallet: Gub6tcj7GFkgc15WjMdGHUSnnmxqgo8aCNNwk5znJxGj
USDC mint: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
Source USDC ATA: E8o2ozKCCckYWKsNKZgyCsVU98uEbZDXCa52h7D5pgoT
Recipient USDC ATA: 5VjcZDR7ZQMYJ8H9sFUUeb6WATDJ5ZEeQ6X2jqEznnm3
Amount UI: 0.01
Amount base units: 10000
Simulation ok. Sending transaction...
Signature: 5By7kgLnk4Xo8C5g4JdtgfVTmLJdEfX5uUF9FkTMNX3BAXiJcVWJHZs4Dspie9rvUk5E6a2tgMPjuFNH4KKhht9G
Confirmed: 5By7kgLnk4Xo8C5g4JdtgfVTmLJdEfX5uUF9FkTMNX3BAXiJcVWJHZs4Dspie9rvUk5E6a2tgMPjuFNH4KKhht9G
```

然后查余额：

```bash
mirage balance --wallet "$WALLET"
```

输出：

```text
0.007956 SOL    Solana
5.280000 USDC   USDC
```

这说明两个 `0.01 USDC` 测试都已经扣掉了。原来是 `5.30 USDC`，两笔测试后是 `5.28 USDC`，完全对得上。

确认测试成功后，再补正式金额。因为每个地址已经收到 `0.01 USDC`，正式补 `1.49 USDC` 即可：

```bash
node transfer-usdc-ows.mjs "$TO_1" 1.49
node transfer-usdc-ows.mjs "$TO_2" 1.49
```

实际成功日志如下：

```text
Amount UI: 1.49
Amount base units: 1490000
Simulation ok. Sending transaction...
Signature: 4g1Z3Dewu5RzdQRvtwBZ5Br2fjQ87teXDHe1bsjbPw4zha4u82tj4X7XEUZfmAF34vjrgUD4rKc24yp2frZckadJ
Confirmed: 4g1Z3Dewu5RzdQRvtwBZ5Br2fjQ87teXDHe1bsjbPw4zha4u82tj4X7XEUZfmAF34vjrgUD4rKc24yp2frZckadJ
```

第二笔：

```text
Amount UI: 1.49
Amount base units: 1490000
Simulation ok. Sending transaction...
Signature: oSZFhLmcdsTqAyhT1JLj6ebX7ud7nJPoK2LsNpRGiwaZKJGKuBrgMeUCQxtEC1cCAG6zJS5tYbdWzvK6hPGNpDy
Confirmed: oSZFhLmcdsTqAyhT1JLj6ebX7ud7nJPoK2LsNpRGiwaZKJGKuBrgMeUCQxtEC1cCAG6zJS5tYbdWzvK6hPGNpDy
```

到这里，整条链路才算真正跑通。

这个脚本里最关键的几行其实不是发送交易，而是构造账户和指令：

```javascript
const sourceAta = getAssociatedTokenAddressSync(
  USDC_MINT,
  SRC,
  false,
  TOKEN_PROGRAM_ID,
);

const recipientAta = getAssociatedTokenAddressSync(
  USDC_MINT,
  RECIPIENT,
  false,
  TOKEN_PROGRAM_ID,
);
```

这两行说明：USDC 转账不是直接从 `SRC` 转到 `RECIPIENT`，而是先根据钱包地址和 USDC mint 推导各自的 ATA。

接着：

```javascript
createAssociatedTokenAccountIdempotentInstruction(
  SRC,
  recipientAta,
  RECIPIENT,
  USDC_MINT,
  TOKEN_PROGRAM_ID,
)
```

这行负责“如果收款人的 USDC ATA 不存在，就创建；如果已经存在，就不重复报错”。这对真实转账很重要，因为你不能假设每个收款人都已经收过 Solana USDC。

最后：

```javascript
createTransferCheckedInstruction(
  sourceAta,
  USDC_MINT,
  recipientAta,
  SRC,
  amountBaseUnits,
  USDC_DECIMALS,
  [],
  TOKEN_PROGRAM_ID,
)
```

这行才是真正的 USDC 转账。它使用的是 `TransferChecked`，显式带上 mint 和 decimals。对 USDC 这类真实资产来说，我更愿意让程序多做检查，而不是偷懒用更少参数的普通 transfer。

这次跑通后，我对 Solana 支付的理解也变了。以前我以为关键是“找到正确的转账工具”；现在我觉得关键是“知道自己到底在构造什么交易”。工具可以换，RPC 可以换，语言可以换，Mirage 可以不用，Python 也可以不用，但底层问题不会变：
- 我在哪条链上？
- 转的是哪个 USDC mint？
- amount 有没有按 decimals 转换？
- source ATA 是哪个？
- recipient ATA 是哪个？
- 收款人 ATA 不存在时有没有创建？
- fee payer 有没有 SOL？
- 交易是谁签名的？
- 签名后有没有改 transaction？
- RPC 有没有模拟成功？
- send 之后有没有 confirmed？

这些问题都回答清楚之后，所谓“Solana USDC 转账”就不再是一团黑盒。最后真正跑通的不是某条神奇命令，而是一条完整链路：

```text
OWS 钱包保存私钥
        ↓
Node 脚本构造 transaction
        ↓
脚本推导 source ATA 和 recipient ATA
        ↓
脚本添加 create ATA 和 TransferChecked 指令
        ↓
OWS 对 unsigned transaction 签名
        ↓
RPC simulateTransaction
        ↓
RPC sendRawTransaction
        ↓
confirmTransaction
        ↓
拿到 confirmed signature
```
