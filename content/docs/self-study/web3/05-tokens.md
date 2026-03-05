---
id: Tokens
title: Tokens on Solana
sidebar_label: 05-tokens
---

Solana 不像以太坊那样每发一个 ERC-20 就部署一份新合约代码，而是把“代币的行为规则”集中在同一个 SPL Token 程序里，所有 token 都复用它，所以钱包、DEX、dApp 只要对接一次就能支持几乎所有 SPL token（这就是它经常被说的 composability）。

## Tokens on Solana：为什么“一个程序”就能覆盖所有代币

我现在更能理解那句“Solana 不追踪交易，它追踪账户状态”。SOL 在你的钱包账户里；USDC、BONK 之类的 SPL token 并不在钱包账户里，而在“属于你（owner 是你）但由 SPL Token 程序管理（owner program 是 SPL Token）”的 token account 里。为了让别人不用问你“你的 USDC 收款地址到底是哪一个”，Associated Token Account（ATA）把地址做成了可推导的标准答案：owner + mint 组合一固定，就能算出同一个 ATA。
这章还把“统一带来的现实好处”用成本和速度讲得很直白：创建 token 在 Solana 本质是创建 mint account（不是部署代码），转账的基础费率按签名很低，因此能支撑更大规模的空投、游戏道具、积分体系这种“量大但单笔价值小”的场景。并且它也提前埋了伏笔：SPL Token 很极简，所以后来出现 Token Extensions（也叫 Token-2022）用可选扩展来进化，而不是把生态拆成多个不兼容标准。

## Mint account：代币的“出生证明”，供应量和权限都写在明面上

我把 mint account 当成“这是什么币，以及谁能管它”的公开档案。课程直接给了 mint 的数据结构：mint_authority 决定谁能增发；supply 是总量（用最小单位存）；decimals 决定显示精度；freeze_authority 决定谁能冻结账户。

```rust
pub struct Mint {
    pub mint_authority: COption<Pubkey>,
    pub supply: u64,
    pub decimals: u8,
    pub is_initialized: bool,
    pub freeze_authority: COption<Pubkey>,
}
```

我最喜欢它的一点是：是否能增发、是否能冻结，并不是藏在合约逻辑里，而是一个字段就写清楚了。比如固定供应的 token，mint_authority 直接是 None；而无限供应的 token，mint_authority 会是 Some(某个地址)。

```rust
mint_authority: None
```

```rust
mint_authority: Some(authority_pubkey)
```

冻结权限也是同样的思路：如果项目想做到“任何人都无法冻结任何人的 token account”，freeze_authority 直接设为 None，而且一旦撤销就是永久撤销。

```rust
freeze_authority: None
```

decimals 这一段对新手特别友好，因为它把“显示上的 1 USDC”如何对应到链上最小单位讲透了，而且强调 decimals 创建后就不能改。课程用 0、6、9 三个常见值做了例子：0 代表不可分割（NFT、票、投票份额）；6 是稳定币常用；9 对齐 SOL 的 lamports 精度。

```rust
decimals: 0
```

```rust
decimals: 6
```

```rust
decimals: 9
```

它还给了几个“拿真实项目对照字段”的例子，我感觉非常适合用来练习看浏览器：USDC 因为要合规，所以 mint_authority / freeze_authority 都是 Some；BONK 则 mint_authority / freeze_authority 都是 None；典型 NFT mint 则 supply 为 1、decimals 为 0。

```text
mint_authority: Some(Circle's authority address)
supply: 28,000,000,000,000,000 (28 billion with 6 decimals)
decimals: 6
freeze_authority: Some(Circle's freeze authority address)
```

```text
mint_authority: None
supply: 93,000,000,000,000,000,000 (93 trillion with 5 decimals)
decimals: 5
freeze_authority: None
```

```text
mint_authority: None
supply: 1
decimals: 0
freeze_authority: None
```

因为 mint account 是公开的，所以“查清楚权力结构”可以很直接：要么去 Solana Explorer / Solscan 看字段，要么用 RPC 把 mint 读出来。课程保留了一个 getMint 的 TypeScript 例子，我觉得可以当作以后写脚本的模板。

```typescript
const mint = await getMint(connection, mintAddress);

console.log("Supply:", mint.supply.toString());
console.log("Decimals:", mint.decimals);
console.log("Mint Authority:", mint.mintAuthority);
console.log("Freeze Authority:", mint.freezeAuthority);
```

最后它也提醒了一个很现实的“持币风险判断方式”：只要 mint_authority 还存在，就意味着有人可以增发；只要 freeze_authority 还存在，就意味着有人可以让你的 token account 不能转出。对短线交易这可能没那么可怕，但如果打算长期持有，就要先把这两个字段看一眼再决定。

## Token account：余额真正住在哪里，以及为什么 ATA 会成为默认答案

我以前会下意识觉得“我的地址里有 USDC”，但 Solana 这里完全不是这样：钱包地址主要对应一个系统账户，里面有 SOL；而每一种 SPL token 余额，都在你名下的一个 token account 里。token account 的结构也给得很清晰：它记录了这个账户属于哪个 mint、owner 是谁、amount 有多少，以及委托(delegate)与冻结状态(state)这些和权限相关的字段。

```rust
pub struct Account {
    pub mint: Pubkey,
    pub owner: Pubkey,
    pub amount: u64,
    pub delegate: COption<Pubkey>,
    pub state: AccountState,
    pub is_native: COption<u64>,
    pub delegated_amount: u64,
    pub close_authority: COption<Pubkey>,
}
```

当我把“一个 token account 只对应一种 token”这个规则记牢以后，很多现象就顺了：你持有 10 种 token，就会有 10 个 token account；而链上程序之所以能快速判断并行冲突，也和这种“结构固定、owner program 固定”有关。

ATA 的意义我现在会用一句话概括：它是“每个人对每种 token 的默认收款箱”。因为地址可推导，别人只需要知道你的钱包地址和那个 token 的 mint 地址，就能算出你应该接收代币的 ATA 地址，不用你额外发一串“我的 USDC 子账户地址”。课程给了 getAssociatedTokenAddressSync 的例子，我原样留下来：

```typescript
const ata = getAssociatedTokenAddressSync(
    mintAddress,   // USDC mint
    ownerAddress   // Your wallet
);
```

它也顺便解释了一个很实用的细节：ATA 是“每个 owner + mint 只能有一个”，所以你没法创建第二个“同 mint 的 ATA”；但你仍然可以创建非 ATA 的随机 token account，用在更进阶的场景，比如同一种 token 分多个用途分仓、或者给程序做金库/托管。

## “功能性操作”里最该记住的：租金押金、关闭回收、委托、冻结/解冻

Token account 不是“凭空存在”的，第一次收某个 token 时，要先创建对应的 token account（大多数钱包会自动帮你做）。它的账户大小是固定的 165 bytes，所以会有一个相对固定的 rent-exempt 押金成本；课程给的数字是 0.00203928 SOL，并且强调这笔 SOL 存在账户里，你把账户关掉就能拿回。

我之前对“approve/委托”在 Solana 的对应关系不太敏感，这章把它说得很像我熟悉的 ERC-20 approve：你仍然是 owner，但你允许一个 delegate 在额度范围内花你的 token，常见于 DEX 交换、托管、限价单等。课程用字段层面的例子表达“授权”和“撤销授权”，我感觉比背指令名更容易记住。

```rust
delegate: Some(dex_program_address)
delegated_amount: 1000000  // 1 USDC with 6 decimals
```

```rust
delegate: None
delegated_amount: 0
```

冻结/解冻则完全由 mint 的 freeze_authority 决定：如果它存在，就能把某个 token account 的 state 变成 Frozen，让它无法转出（但仍可接收）；解冻后 state 回到 Initialized。

```rust
state: Frozen
```

```rust
state: Initialized
```

这几个机制连起来，我现在会形成一个很“钱包使用习惯”的结论：如果钱包里堆了很多零余额 token account，可以考虑关闭它们回收押金；如果曾经给某个 DEX/程序做过委托，但后来不需要了，最好撤销掉，降低未来被动花费的风险。

## Metaplex Token Metadata 与 Token-2022：从“外挂程序”到“可选扩展”

我对“为什么需要 Token-2022”的理解，核心来自这句：SPL Token 本来就故意做得很小，只负责铸造、转账、销毁；所以想要元数据、转账限制、利息型余额、隐私转账等能力，过去只能靠额外程序来拼装。元数据最典型的就是 Metaplex Token Metadata：mint 本体只有 82 bytes，但 Metaplex 的 metadata PDA 需要 679+ bytes，还要额外租金和额外交互，做个最基础的 name/symbol/URI 都显得有点重。

Token-2022 的思路是“别再到处外挂了，把常见能力做成可选扩展字段”，需要的人启用，不需要的人保持最简，从而尽量避免生态割裂。它给了很多扩展结构体例子，我理解它们更像一组“插件配置”。最直观的是 Metadata Extension：把 name/symbol/uri 直接塞进 mint；还有 Transfer Hook：每次转账都能触发你自定义的程序逻辑，用来做合规校验、版税、日志、条件转账等。

```rust
pub struct TokenMetadata {
    pub name: String,
    pub symbol: String,
    pub uri: String,
}
```

```rust
pub struct TransferHook {
    pub authority: Pubkey,
    pub program_id: Pubkey,
}
```

它还给了几个我觉得“读完会立刻有画面”的扩展：Permanent Delegate 适合监管类资产（发行方必须能追回/处置）；Transfer Fee 适合把手续费直接写进 token 机制；Interest-Bearing 适合存款凭证类 token（余额随利率增长，不用手动 rebase）；Confidential Transfer 适合隐私转账；Non-Transferable 适合 soulbound 证书；Immutable Owner 更像一个安全型约束；MemoTransfer 和 DefaultAccountState 则偏合规控制。

```rust
pub struct PermanentDelegate {
    pub delegate: Pubkey,
}
```

```rust
pub struct TransferFeeConfig {
    pub transfer_fee_basis_points: u16,
    pub maximum_fee: u64,
}
```

```rust
pub struct InterestBearingConfig {
    pub rate: i16,  // Basis points per year
    pub last_update_timestamp: i64,
}
```

```rust
pub struct ConfidentialTransferMint {
    pub authority: Pubkey,
    pub auto_approve_new_accounts: bool,
}
```

```rust
pub struct NonTransferable {}
```

```rust
pub struct ImmutableOwner {}
```

```rust
pub struct MemoTransfer {
    pub require_incoming_transfer_memos: bool,
}
```

```rust
pub struct DefaultAccountState {
    pub state: AccountState,
}
```

我觉得它最重要的承诺是“向后兼容”：Token-2022 的基础字段布局与 SPL Token 保持一致，扩展字段放在后面，所以不关心扩展的老程序只读基础字段也能工作；而新程序才会去解析扩展部分。于是新项目可以用 Token-2022 的高级能力，同时不至于把 DEX、钱包、借贷协议逼到“必须选边站”的局面。

最后还有一个非常工程化的提醒：扩展最好在 mint 创建时（或刚创建、尚未铸造供应量之前）就规划好，因为一旦已经有 supply，就不能随意给既有 mint 加扩展了。课程也给了“如何检查扩展”和“如何用 Token-2022 创建 mint 并初始化 metadata pointer”的 TypeScript 例子，我也原样保留，之后做实验会很好用。

```typescript
const mint = await getMint(
    connection,
    mintAddress,
    'confirmed',
    TOKEN_2022_PROGRAM_ID
);

// Check for metadata extension
const metadata = getMetadataPointerState(mint);
// Check for transfer fee extension
const transferFeeConfig = getTransferFeeConfig(mint);
```

```typescript
const mint = await createMint(
    connection,
    payer,
    mintAuthority,
    freezeAuthority,
    decimals,
    keypair,
    confirmOptions,
    TOKEN_2022_PROGRAM_ID  // Use Token-2022 program
);
// Enable metadata extension
await createInitializeMetadataPointerInstruction(
    mint,
    mintAuthority,
    metadataAddress,
    TOKEN_2022_PROGRAM_ID
);
```

## 这一部分的收尾：我现在会怎么“从浏览器读懂一个 token”

这几节合在一起，我现在看一个 token 会很有流程感：先找 mint account，看 decimals、mint_authority、freeze_authority，判断它是“固定供应还是可增发”“能否被冻结”；再看自己或目标地址对应的 token account/ATA 是否存在、余额是多少、是否被冻结、是否有 delegate；如果是 Token-2022，再额外看它启用了哪些 extensions，特别是 transfer hook、transfer fee 这种会影响转账行为的扩展。

[1]: https://learn.blueshift.gg/en/courses/tokens-on-solana/introduction "One Program, Every Token | Tokens on Solana | Blueshift"
[2]: https://learn.blueshift.gg/en/courses/tokens-on-solana/mint-and-token-accounts "Mint Accounts and Supply Control | Tokens on Solana | Blueshift"
[3]: https://learn.blueshift.gg/en/courses/tokens-on-solana/functionalities "Token Accounts and Ownership | Tokens on Solana | Blueshift"
[4]: https://learn.blueshift.gg/en/courses/tokens-on-solana/metaplex-token-metadata "Token Extensions and Token-2022 | Tokens on Solana | Blueshift"
[5]: https://learn.blueshift.gg/en/courses/tokens-on-solana/conclusion "Key Takeaways | Tokens on Solana | Blueshift"
