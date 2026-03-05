---
id: Solana
title: 为规模化而生的高性能区块链
sidebar_label: 03-Solana
---

## 并行执行
传统区块链（例如以太坊）最大瓶颈之一，是交易执行通常是顺序的。因为在执行前，系统并不知道两笔交易会不会冲突，于是只能先达成共识排好队，再一笔一笔执行。

Solana 则认为，如果能先把顺序确定下来，再把互不冲突的交易丢给不同 CPU 核心并行跑，就能把硬件性能真正用起来。

但“先确定顺序”在去中心化网络里并不容易。分布式系统里可以信任时间戳（A 在 10:00:01.523 到，B 在 10:00:01.891 到，就先 A 后 B），可区块链节点不能信任彼此的时钟，还会有网络延迟、恶意节点伪造时间等问题。于是 Solana 用 **Proof of History（PoH） **做了一个可验证的加密时钟，让顺序在共识前就能被证明。

具体而言，PoH 不停对输出做哈希(SHA-256)，把上一次的输出当下一次输入，这样你无法跳步，只能老老实实算下去，于是“算到第 N 步”本身就证明了时间经过。
```bash
hash(data)             → output_1
hash(output_1 + data)  → output_2
hash(output_2 + data)  → output_3
hash(output_3 + data)  → output_4
```

当交易来时，把交易哈希“插入”这条链里，就能证明先后顺序

```bash
hash(output_42)                 → output_43
hash(output_43 + transaction_A) → output_44
hash(output_44)                 → output_45
hash(output_45 + transaction_B) → output_46
```
> 因为你不可能直接生成 output_46 而不先生成 output_44、output_45，所以 A 一定在 B 前面，这个顺序是可验证的

顺序一旦先被钉死，Solana 就可以做并行执行。也就是运行时先看每笔交易会读写哪些账户；不冲突的就同时跑，冲突的再排队。
| 以太坊（顺序执行） | Solana（并行执行） |
| --- | --- |
| 事务A执行→更新状态<br>事务B执行→更新状态<br>事务C执行→更新状态<br>事务D执行→更新状态<br><br>一次只有一笔交易运行。<br>总时间 = 所有交易执行时间的总和。 | Solana 分析了这些有序交易：<br><br>- 交易A修改账户{1, 2, 3}<br>- 交易B修改账户{4, 5, 6}<br>- 交易C修改账户{2, 7, 8}<br>- 交易D修改账户{9, 10, 11}<br><br>交易A和B不涉及共同账户——它们可以同时执行。<br>交易C与A冲突（双方都接触账户2），因此必须等待。<br>交易D与无任何冲突，可以立即执行。 |

Solana 通过强制交易预先声明其读/写的账户，使运行时能够构建依赖图，从而并行执行无冲突的交易。
例如，交易 A 修改账户 {1,2,3} 与交易 B 修改 {4,5,6} 可同时执行，而与 A 冲突的 C（涉及账户 2）则需等待。
这一机制结合PoH历史证明，实现了高吞吐量：生产中每秒处理 5000+ 笔交易，理论容量超过 65000 TPS，区块时间仅 400 毫秒，最终确定性通常在 1-2 秒内完成。相比之下，以太坊顺序执行约 15 TPS，区块时间 12 秒，最终确认需 13 分钟；比特币约 7 TPS，区块时间 10 分钟，6 次确认耗时 60 分钟。
高吞吐量和低延迟（如 0.00025 美元的交易成本）使实时应用、微支付、复杂 DeFi 策略、大规模 NFT 铸造以及面向小用户的 DeFi 成为可能。然而，这种性能以**更高的硬件需求**（验证器需 12+ CPU 核心、256 GB 内存）、明确的账户声明（增加开发者规划成本）和高速网络为代价，但仍维持了 1000 多个独立验证者，在性能与去中心化间取得平衡。

## 万物皆账户
Solana 把很多东西统一成一种原语——账户（Account）。钱包地址是账户，程序（智能合约）也是账户，代币余额是账户，NFT 元数据也是账户。账户本质是一个容器，里面放余额（lamports）、数据（字节）、owner（哪个程序控制它）、以及这个账户是不是可执行代码。
### 账户结构
每个账户包含五个字段：
```bash
pub struct Account {
    /// 账户中的 lamports 余额
    pub lamports: u64,
    /// 此账户持有的数据，这些信息可以是用户资料、代币余额、NFT元数据、游戏状态或其他任何信息。最大容量为10M字节（10,485,760字节）
    pub data: Vec<u8>,
    /// 拥有此账户的程序，该字段是一个32字节的公钥，用于标识拥有程序
    pub owner: Pubkey,
    /// 表示该账户是否包含可执行程序代码。程序账户将此设置为 true。数据账户将此设置为 false。
    pub executable: bool,
    /// 此账户下一次欠租的纪元，现在已经不再活跃使用，但仍然保留在账户结构中。
    pub rent_epoch: Epoch,
}
```
每个账户都有一个唯一的32字节地址，以base58编码的字符串显示，该地址作为账户在区块链上的标识符。如`14grJpemFaf88c8tiVb77W7TYg2W3ir6pfkKz3YjhhZ5`。
> NFT，Non-Fungible Token，非同质化代币，就是一般等价物和记名代金券中的后者类比
> 
> lamports，Solana最小单位余额（1 SOL = 1,000,000,000 lamports）

### 账户类型
所有账户结构相同，但根据所有者和可执行文件标志，其用途不同。
- **系统账户**：归系统项目所有。这些是用户直接与之互动以发送和接收SOL的基础钱包账户。当你创建钱包时，你实际上是在创建一个系统账户。系统程序允许账户持有人（拥有私钥者）转移时光并将账户重新分配到其他程序。
- **代币账户**：由代币计划拥有。这些设备存储SPL代币余额和元数据。你持有的每一个代币（USDC、BONK、任何SPL代币）都存在于代币项目拥有的一个代币账户中。代币计划执行转账规则并维持余额。
- **数据账户**：由定制程序拥有。这些存储了应用特定的状态：用户资料、游戏数据、NFT元数据、贷款头寸，或你的程序所需的任何其他信息。拥有程序定义数据格式和访问规则。
- **项目账户**：包含可执行代码，并将可执行标志设置为 true。这些账户存储已编译的程序字节码。当事务调用程序时，运行时会从这些账户加载代码。

### 所有权规则
账户所有权这一块，owner 指的是程序所有者，不是我有没有私钥。每个账户都归某个程序所有。只有拥有账户的程序可以修改账户数据或提取其 Lamport。
Solana 的所有权更多是权限模型：只有 owning program 才能改数据、从账户里扣 lamports 等；而任何人都能往账户里打钱、也能读取账户数据（链上数据默认公开）。
当你想持有 USDC 时，你会调用 SPL Token Program 来为你创建一个专门的“保险箱”，也就是代币账户 (Token Account)。这个账户归 SPL Token Program 所有，因为只有这个程序知道如何操作它里面的数据。
在这个“保险箱”内部的数据结构中，有一个专门的字段叫 owner（为了区分，我们叫它“账户所有者”或“钱包所有者”）。SPL Token Program 会把你的钱包地址填进这个字段
```rust
pub struct Account {
    pub mint: Pubkey,      // 这个保险箱装的是什么代币？(USDC)
    pub owner: Pubkey,     // 这个保险箱是谁的？(你的钱包地址)
    pub amount: u64,       // 里面有多少钱？
    // ... 其他数据
}
```
> owner 字段不是指“这个账户属于哪个用户”，而是“哪个程序拥有对这个账户的写入权限”。
现在，这个“保险箱”账户就有了两个角色：
- 程序所有者 (Program Owner)：是 SPL Token Program。它就像是“房东”，拥有修改这个账户内部数据的“钥匙”（权限）。任何对账户数据的修改，都必须通过它来执行。
- 钱包所有者 (Wallet Owner)：是你的钱包地址。它就像是“房客”，只有你能证明你是这个“保险箱”的主人，并指示“房东”（SPL Token Program）帮你办事。
这也解释了为什么 SPL（Solana Program Library） Token 账户虽然“属于我”，但它的 owner 是 Token Program，我转账得调用 Token Program 的指令，而不是自己随便改余额。

### 创建账户
Solana 需要你“显式创建并打钱”，通常由 System Program 提供 `create_account` 指令
```rust
pub fn create_account(
    from: &Pubkey,          // 谁支付账户创建费用
    to: &Pubkey,            // 新账户的地址
    lamports: u64,          // 免租金最低额度 + 额外金额
    space: u64,             // 数据大小（字节）
    owner: &Pubkey,         // 哪个程序将拥有该账户
) -> Instruction

// 1. 为账户地址生成一个新的密钥对
let account = Keypair::new();

// 2. 计算免租金最低额度
let rent = Rent::default();
let account_size = 165; // 字节
let lamports = rent.minimum_balance(account_size);
// 免租最低额度取决于账户规模，而一个165字节的账户（通用大小）约0.00114 SOL

// 3. 创建账户
let instruction = system_instruction::create_account(
    &payer.pubkey(),
    &account.pubkey(),
    lamports,
    account_size as u64,
    &my_program_id,
);

// 4. 发送交易，同时使用付款人和新账户作为签名者
```
EVM 合约是自己存状态，但是 solana 里，你往往先要设计“有哪些数据账户、每个账户多大、谁付押金、由哪个程序拥有”，然后程序再去读写它们。
### 无状态合约
更有意思的是，Solana 的程序被设计成**无状态（stateless）**：程序账户里只有代码，不放数据；数据放在独立的数据账户里。这样同一个程序被多笔交易调用时，只要它们操作的是不同的数据账户，就可以并行跑，因为代码是只读的，真正变化的是各自的数据账户。
对于以太坊，一个智能合约的合约代码（程序）和它的数据（状态变量）都存储在同一个账户里。店员和货架是同一个实体——你不能把店员（负责执行操作的程序，比如“买一瓶水”）叫到另一家店去工作，因为他的知识和货架（放着各种商品的数据，比如价格、库存）是绑定的。当你想调用这个合约的函数时，整个合约（包括代码和数据）都会被加载，而且一次只能有一个操作修改数据（因为要避免冲突）。
Solana 把“店员”和“货架”分开了，程序账户只存放“店员”的知识——也就是可执行的代码。这个账户是只读的，而且可以被很多人同时调用；数据账户专门存放“货架”上的数据。每个数据账户都属于某个程序（即由那个程序“拥有”），但数据本身是独立存储的。
举个例子，你想写一个简单的计数器程序：
```rust
pub fn increment(accounts: &[AccountInfo]) -> ProgramResult {
    // 1. 从传入的账户列表里取出第一个账户（索引0）
    let counter_account = &accounts[0];

    // 2. 读取该账户数据的前 8 个字节，并解释成一个 u64 类型的整数（小端序）
    let mut count = u64::from_le_bytes(counter_account.data[0..8]);

    // 3. 把读出的数字加 1
    count += 1;

    // 4. 把加 1 后的数字重新转换成 8 字节的小端序字节数组，写回账户数据的前 8 个字节
    counter_account.data[0..8].copy_from_slice(&count.to_le_bytes());

    // 5. 返回成功
    Ok(())
}
```
关键在于程序代码是只读的，而冲突只发生在数据层面，分开就能并行。假设有两个人同时想用这个计数器程序，但用的是不同的数据账户，两人可以同时调用程序，同时两个数据账户不同，所以写操作也不会互相干扰，于是这两笔交易就可以并行执行。
### 读写账户内容
Solana 程序通过读取和写入账户的 data 字段来存储和修改状态。由于链上存储的是原始字节，程序需要在内存中将字节反序列化为结构化类型，修改后再序列化回字节写回账户。
以下是一个使用 borsh（Binary Object Representation Serializer for Hashing） 序列化库的示例：
```rust
// 引入 borsh 库中的两个核心 trait：BorshSerialize 和 BorshDeserialize
// 它们提供了序列化（结构体→字节）和反序列化（字节→结构体）的方法
use borsh::{BorshSerialize, BorshDeserialize};

// 定义一个结构体 UserAccount，代表我们要存储在链上账户中的数据
// 通过 #[derive(...)] 让编译器自动实现 BorshSerialize 和 BorshDeserialize
// 这样 UserAccount 就具备了“把自己变成字节”和“从字节变回自己”的能力
#[derive(BorshSerialize, BorshDeserialize)]
pub struct UserAccount {
    pub name: String,   // 用户名，长度可变
    pub balance: u64,   // 余额，固定 8 字节
    pub posts: Vec<u32>, // 帖子 ID 列表，长度可变
}

// 这是一个 Solana 程序的入口函数，用来更新用户数据
// accounts: 当前指令涉及的账户列表（由调用者提供）
// new_name: 新的用户名（由指令参数传入）
pub fn update_user_data(accounts: &[AccountInfo], new_name: String) -> ProgramResult {
    // 按照约定，第一个账户（索引0）就是我们要修改的 UserAccount 数据账户
    let user_account = &accounts[0];

    // --- 反序列化：从账户的原始字节中还原出 UserAccount 结构体 ---

    // 1. 获取账户 data 字段的不可变借用（返回一个 Ref 智能指针，这里我们只需要字节切片）
    //    user_account.data 是一个 RefCell 包装的 Vec<u8>，borrow() 获得 Ref<Vec<u8>>，
    //    然后我们可以通过 Deref 把它当作 &[u8] 使用。
    // 2. UserAccount::try_from_slice() 是 borsh 提供的方法，它尝试从字节切片中解析出 UserAccount。
    //    如果字节格式正确，就会返回 Ok(UserAccount)，否则返回错误（? 运算符会把错误提前返回）。
    let mut user_data = UserAccount::try_from_slice(&user_account.data.borrow())?;

    // --- 修改内存中的数据 ---
    // 现在我们有了一个可变的 user_data 结构体，可以直接修改它的字段
    user_data.name = new_name;

    // --- 序列化：将修改后的结构体重新转换成字节，写回账户的 data 字段 ---

    // 1. 获取账户 data 字段的**可变**借用（borrow_mut() 返回 RefMut<Vec<u8>>）
    //    我们需要把字节写入这个 Vec 中。
    // 2. &mut user_account.data.borrow_mut()[..] 得到整个 Vec 的可变切片（&mut [u8]）。
    // 3. user_data.serialize() 是 borsh 提供的序列化方法，它会将结构体内容写入指定的字节切片。
    //    注意这里用了两层 &mut：&mut &mut ... 是因为 serialize 接受一个实现了 Write 的泛型参数，
    //    而 &mut [u8] 恰好实现了 Write，这样序列化后的字节会直接填充到切片中。
    //    如果切片长度不够，serialize 会返回错误，这里我们用 ? 传播错误。
    user_data.serialize(&mut &mut user_account.data.borrow_mut()[..])?;

    // 一切成功，返回 Ok(())
    Ok(())
}
```
1. 读取：&user_account.data.borrow() 获取账户数据的字节切片。
2. 反序列化：try_from_slice 将字节解析为 Rust 结构体。
3. 修改：在内存中操作结构体字段。
4. 序列化：serialize 将结构体转换回字节。
5. 写入：通过 borrow_mut() 获取可变引用，将字节写回账户。

程序始终在内存中处理结构化数据，但链上存储的只是原始字节。
### 关联代币账户（ATA）
每个用户可以持有多种 SPL 代币（如 USDC、BONK），每种代币需要一个独立的账户来记录余额。如果没有标准，查找某个代币的账户地址就需要手动追踪，容易出错。
关联代币账户（Associated Token Account，ATA） 通过确定性地址推导解决了这个问题。给定钱包地址和代币铸币地址，可以唯一计算出对应的 ATA 地址：
```rust
associated_token_address = derive_address(
    seeds: [wallet_address, token_program_id, token_mint_address],
    program_id: associated_token_program_id
)
```
- 每个钱包 + 每种代币 → 只有一个确定的 ATA。
- 钱包可以自动找到自己的 USDC 账户，程序也知道该把代币发送到哪里，无需手动管理地址。
当有人首次向你发送某种代币时，你的 ATA 可能还不存在。发送方（或钱包）可以在交易中代为创建该账户，并支付免租的最低 lamports 费用。
### 查看账户信息
- **[Solana Explorer](https：//explorer.solana.com)**：官方浏览器，可查看余额、owner、数据、交易历史。
- **[Solscan](https：//solscan.io)**：界面更友好，数据可视化更强，适合非技术用户。

推荐前者。
## 交易与指令
Solana 的交易（Transaction）是由指令（Instruction）组成的“原子操作包”：要么全部成功，要么全部失败，不会半成功。一个交易由**签名**和**消息**组成，其数据结构如下：
```rust
Transaction {
    signatures: Vec<Signature>,         // 交易的签名列表
    message: Message {
        header: MessageHeader {
            num_required_signatures: u8,          // 所需签名数
            num_readonly_signed_accounts: u8,     // 只读且签名的账户数
            num_readonly_unsigned_accounts: u8,    // 只读且未签名的账户数
        },
        account_keys: Vec<Pubkey>,      // 交易中涉及的所有账户的公钥
        recent_blockhash: Hash,         // 最近区块哈希，用于防止交易重放
        instructions: Vec<CompiledInstruction>, // 指令列表
    },
}
```
交易必须提前声明会访问哪些账户、哪些可写、哪些要签名。这是 Solana 能并行调度的前提，因为运行时只看声明就能构建依赖关系图。
```rust
// 导入 Solana 程序库中所需的模块
use solana_program::{
    account_info::AccountInfo,   // 账户信息结构，包含账户的元数据和数据
    entrypoint,                  // 用于声明程序入口点的宏
    entrypoint::ProgramResult,   // 程序返回类型，是 Result<()> 的别名
    pubkey::Pubkey,              // 公钥类型，用于表示程序 ID、账户地址等
};

// 使用 entrypoint 宏将 process_instruction 函数声明为程序的入口点
// 当交易调用此程序时，运行时将调用此函数
entrypoint!(process_instruction);

/// Solana 程序的入口函数
///
/// # 参数
/// - `program_id`: 当前被调用的程序的公钥（即此程序的 ID）
/// - `accounts`: 交易中传递给程序的所有账户的切片。每个元素是 AccountInfo，
///    包含该账户的元数据（如是否可写、是否为签名者、所有者等）和数据
/// - `instruction_data`: 指令携带的附加数据，通常是一个字节数组，
///    用于告诉程序要执行什么操作（例如转账、更新状态）以及相关参数
///
/// # 返回
/// 返回 `ProgramResult`，成功时返回 `Ok(())`，失败时返回包含错误码的 `ProgramError`
pub fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    // 1. 解析 instruction_data，确定要执行的操作（例如通过第一个字节作为操作码）
    //    并根据需要提取操作参数（如转账金额、新名字等）

    // 2. 验证 accounts 中提供的账户是否符合要求：
    //    - 检查必要的账户是否存在且顺序正确
    //    - 确认某些账户是否已签名（即拥有者授权了此次操作）
    //    - 确认账户是否可写（如果需要修改数据）
    //    - 确认账户的所有者是否正确（例如，某些账户必须归当前程序所有）
    //    - 检查账户数据长度是否足够等

    // 3. 执行实际操作：读取或修改账户数据，调用其他程序等
    //    例如：从某个账户中扣除 lamports，向另一个账户增加 lamports；
    //    或者反序列化账户数据，修改字段后重新序列化写回

    // 4. 如果一切顺利，返回 Ok(())；如果出现错误（如余额不足、未授权），
    //    返回相应的 ProgramError

    Ok(())
}
```
总的来说，无状态程序处理指令，事务提供原子性，PDA（程序派生地址）实现程序权限，CPI（跨程序调用）允许程序相互调用。
### 程序衍生地址(PDA)
BYD 如果程序没有私钥，它怎么“持有资金”或者“作为权限主体”操作资产？
答案就是PDA（Program Derived Address）：这是由程序用固定 seeds 推导出来的地址，不对应任何私钥，但运行时可以验证“你提供的 seeds 的确推导出这个地址”，从而把它当成某些调用里的“签名者”。

```rust
use solana_program::pubkey::Pubkey;

// 查找一个 PDA
let (pda, bump) = Pubkey::find_program_address(
    &[
        b"vault",              // 种子可以是任意字节
        user_pubkey.as_ref(),  // 例如用户的公钥
    ],
    program_id,                // 派生此 PDA 的程序 ID
);
```
PDA 的生成通过接受一组种子和程序 ID，并返回一个地址和一个 bump 值（一个用于确保地址不在椭圆曲线上的修正因子）：
- 运行时从 bump = 255 开始尝试，将种子和 bump 组合，计算地址。
- 如果计算出的地址落在椭圆曲线上（即有对应的私钥），则 bump 减 1 重试，直到找到一个不在曲线上的地址。
- 最终得到的地址就是 PDA，它没有对应的私钥，因此只有派生它的程序才能“代表”它。
特点在于：
- 确定性：相同的种子和程序 ID 总是生成相同的 PDA。
- 无私钥：PDA 不在椭圆曲线上，所以没有人（包括程序）拥有它的私钥。
- 程序拥有**签名权**：程序可以通过在跨程序调用中提供种子和 bump 来证明它派生了该 PDA，运行时将其视为 PDA 的签名。

上面是我们计算得到PDA的方法。而当我们需要用到PDA的时候，想象你（程序）有一个保险箱（PDA 账户），保险箱的钥匙（私钥）不存在，但你知道保险箱的密码（种子）。你想让银行（Token Program）从保险箱里取钱给另一个人，银行必须确认你确实有权打开这个保险箱。

在 Solana 中，银行（Token Program）只看签名：谁签名了，谁就授权了这笔转账。但保险箱（PDA）没有私钥，没法直接签名。

这时候你（程序）对银行说：“我知道这个保险箱的密码（种子），我可以当场算给你看这个保险箱的地址，证明我就是它的主人。”
银行（运行时）验证了你提供的密码（种子），发现算出来的地址确实和保险箱的地址一样，于是银行就相信你确实有权代表保险箱，然后允许转账。

`invoke_signed` 就是用来做这个证明的：你调用另一个程序时，附上种子，运行时验证通过后，就会把该 PDA 当作一个签名者传给被调用的程序。
```rust
use solana_program::program::invoke_signed;

// 假设我们之前已经找到这个 PDA
let (pda, bump) = Pubkey::find_program_address(
    &[b"vault", user.key.as_ref()],   // 种子：一个常量字符串 + 用户的公钥
    program_id,                        // 当前程序的 ID
);

// 构建用于签名的种子切片（必须包含 bump）
// 注意：这里的 seeds 是“种子列表”，用于在 invoke_signed 中重新派生出 PDA
let seeds = &[
    b"vault",                // 常量种子
    user.key.as_ref(),       // 用户公钥作为种子
    &[bump],                 // bump 值必须以字节切片形式提供，它是派生时的调整值
];

// 调用 Token Program 的 transfer 指令，将 PDA 拥有的代币账户中的代币转出
invoke_signed(
    // 第一个参数：要调用的指令
    &spl_token::instruction::transfer(
        &token_program.key,              // Token Program 的 ID（被调用者）
        &pda_token_account.key,          // 源代币账户（由 PDA 拥有）
        &destination_token_account.key,  // 目标代币账户
        &pda,                            // 授权者：这里必须是 PDA，因为它是源代币账户的 owner
        &[],                             // 额外的签名者（这里不需要）
        amount,                          // 转账金额
    )?,

    // 第二个参数：本次调用涉及的所有账户（必须与指令中的账户一一对应）
    &[
        pda_token_account.clone(),       // 源代币账户（可写）
        destination_token_account.clone(), // 目标代币账户（可写）
        token_program.clone(),            // Token Program（只读，系统账户）
    ],

    // 第三个参数：用于 PDA 签名的种子数组（可以有多个 PDA 同时签名，这里只有一个）
    &[seeds],   // 提供种子，运行时用这些种子重新计算地址，如果与 pda 一致，就认为 pda 已签名
)?;
```
### 原子操作
下面的交易一次性执行三个操作：转账 SOL、转账代币、更新用户资料。它们要么全部成功，要么全部失败。
```rust
let transaction = Transaction::new_signed_with_payer(
    &[
        // 指令 1: 转账 SOL
        system_instruction::transfer(
            &payer.pubkey(),
            &recipient.pubkey(),
            1_000_000,
        ),
        // 指令 2: 转账代币 (SPL Token)
        spl_token::instruction::transfer(
            &token_program_id,
            &source_token_account,
            &dest_token_account,
            &owner.pubkey(),
            &[],
            500_000,
        )?,
        // 指令 3: 更新用户资料 (自定义程序)
        my_program::instruction::update_profile(
            &program_id,
            &user_account,
            "New Username".to_string(),
        )?,
    ],
    Some(&payer.pubkey()),   // 付费者
    &[&payer, &owner],       // 签名者
    recent_blockhash,
);
```

### 交易大小与费用
一个交易的最大大小为 1,232 字节（包括签名、账户密钥、指令数据、消息头等）。超过的话，要么将操作拆分为多个交易，要么使用地址查找表（Address Lookup Tables） 压缩账户列表，要么就老实最小化指令数据的长度。

而**交易费用**由两部分组成：
1. 基础费用
每个签名 5,000 lamports（1 lamport = 10⁻⁹ SOL）。
例如：一笔交易有 1 个签名，费用为 5,000 lamports；3 个签名则为 15,000 lamports。
2. 优先级费用（可选）
在网络拥堵时，可通过支付优先级费用提高处理优先级。
```bash
prioritization_fee = compute_unit_limit × compute_unit_price
```

### 跨程序调用(CPI)
Solana 的组合性很多时候来自 CPI（Cross-Program Invocation）：一个程序可以在同一笔交易里调用另一个程序，比如调用 Token Program 转账、调用 System Program 创建账户，甚至串起来做更复杂的业务逻辑，而且仍然保持原子性。
#### 基本CPI：invoke
```rust
use solana_program::program::invoke;

let transfer_instruction = spl_token::instruction::transfer(
    &token_program.key,
    &source_account.key,
    &destination_account.key,
    &authority.key,
    &[],
    amount,
)?;

invoke(
    &transfer_instruction,
    &[
        source_account.clone(),
        destination_account.clone(),
        authority.clone(),
        token_program.clone(),
    ],
)?;
```

#### 使用 PDA 签名的 CPI：invoke_signed
```rust
invoke_signed(
    &transfer_instruction,
    &[
        source_account.clone(),
        destination_account.clone(),
        pda.clone(),          // 授权者是 PDA
        token_program.clone(),
    ],
    &[seeds],                 // 提供 PDA 的种子（包含 bump）
)?;
```
> CPI 最多可嵌套 4 层。例如：程序 A 调用 B，B 调用 C，C 调用 D 是允许的，但再调用 E 会失败。

原始事务签署者在整个CPI链中保持其权限——如果用户签署了该事务，他们调用的程序（以及程序调用的程序）会将该用户视为签署者。如果账户在原始交易中被标记为可写，则该账户在所有CPI级别中仍可写，允许程序修改该账户。所有CPI共享交易的计算预算（默认20万计算单元），超过该限制的复杂CPI链会失败，但开发者可请求更高的计算限制。

### 总结
一笔典型的 Solana 交易从构造到最终确认，会经历以下步骤：

1. **用户构造交易**  
   钱包（客户端）收集要执行的指令、涉及的账户列表以及一个最近的区块哈希，然后用户使用私钥对交易进行签名。

2. **提交交易**  
   签名后的交易通过 RPC 节点广播到整个网络，最终被当前负责产生区块的**领导者（Leader）** 验证者接收。

3. **领导者接收并调度**  
   领导者收到交易后，运行时（Runtime）会分析该交易将要访问的所有账户。根据账户的占用情况（是否正被其他事务修改），将交易安排到合适的时机执行，以实现并行处理。

4. **执行指令**  
   运行时调用交易中指定的程序，并传入相应的账户信息和指令数据。程序内部会验证账户权限、数据合法性等，然后执行预定的操作。

5. **跨程序调用（CPI）**  
   如果程序需要调用其他程序（例如代币程序），会通过 CPI 机制在同一原子上下文中递归执行这些调用。

6. **提交或回滚**  
   - 若所有指令执行成功，则所有状态变更被提交（写入账本）。  
   - 若任意一条指令失败，则整个交易的所有变更都会被回滚，交易标记为失败。

7. **确认与最终性**  
   成功执行的交易会被打包进一个区块，待网络完成对该区块的最终确认后，交易便成为不可逆的最终状态。

整个过程通常在**毫秒级**内完成。Solana 通过并行执行机制（在不同 CPU 核心上同时运行无冲突的交易）极大地提升了吞吐量。


## 参考资料
- [总结](https://learn.blueshift.gg/en/courses/understanding-solana/conclusion)