---
title: "自学"
weight: 2
---

一个自己总结出来的让AI撰写出更符合初学者学习/复盘笔记的SKILLS：
```
DECISION-CHAIN-TECH-NOTES
│  SKILL.md
│
├─agents
│      openai.yaml
│
└─references
        domain-example.md
        pattern-catalog.md
```
## SKILL
````
---
name: decision-chain-tech-notes
description: use this skill when the user asks for technical learning notes, project review notes, architecture or code-evolution notes, interview-oriented explanations, or study notes that should explain why an implementation, abstraction, algorithm, workflow, or debugging method emerged. trigger for backend, frontend, full-stack web, agent development, coding agents, agentic rl, post-training, llms, go/python basics, leetcode, protocols, frameworks, tests, refactoring, troubleshooting, or interview prep. produce notes as a causal decision chain, not a file-by-file tour, with mvp hand-built implementation, core concepts, and debugging practice.
---

# Decision Chain Tech Notes

Write technical learning notes as a **decision chain**: start from a concrete wish, tiny failing example, confusing symptom, or repeated pain; show the naive attempt; let failure, duplication, boundary confusion, performance limits, evaluation mismatch, or production risk force the next abstraction; then explain the principle and interview value.

Do not write a code说明书. Avoid making the main structure “file A does X, file B does Y” unless the user explicitly asks for a code review. Use files and code only as evidence inside a broader causal narrative.

## Core rule

For every major concept, explain it with this causal shape:

```text
我想做到什么
  ↓
我先写了最小愿望/最小测试/最小页面/最小接口/最小训练循环/最小题解
  ↓
它编译不过、测不过、跑不通、重复太多、边界变脏、指标不对、线上会有风险
  ↓
所以某个字段/函数/组件/状态/抽象/协议边界/训练阶段/算法技巧被逼出来
  ↓
这背后的原则是什么
  ↓
面试时怎么讲
```

Use “不是为了套架构/设计模式/论文名词”, “先有行为，后有字段”, “先有痛点，后有抽象”, “先有失败反馈，后有工程边界” as guiding ideas.

## Default output structure

Use this three-part structure unless the user requests another format:

1. **MVP 手把手最小实现**
   - Start with a tiny wish, failing test, broken UI, minimal API, naive agent loop, minimal training/evaluation loop, or simplest algorithm attempt.
   - Include incomplete examples (`???`), fake implementations, intentionally naive code, or intentionally failing cases when they teach why the next decision appears.
   - Let each next step emerge from compile failure, test failure, UI state bug, duplicated code, poor metrics, unsafe behavior, unclear responsibility, or debugging pressure.

2. **八股概念基础知识点**
   - Explain concepts only after the MVP has created the need for them.
   - Tie every concept to the decision chain, not textbook definitions alone.
   - Include interview-ready phrasing.

3. **排障过程实践**
   - Use realistic symptoms, commands, logs, metrics, screenshots-to-check, or failing examples.
   - Prefer “看到什么错误/现象 → 说明什么 → 怎么缩小范围 → 怎么修” over generic tips.

## Generalization across domains

This skill is not only for backend. Apply the decision-chain style to any technical learning area.

### Backend / DDD / COLA

Start from a behavior, not a layer diagram. Example: “商品应该可以购买” forces `Product` and `IsPurchasable`; counterexamples force `Status`, `Price`, `SkillDid`; repetition forces Builder; precision risk forces `Money`; cross-object rules force Domain Service; Application needing data forces Repository. See `references/domain-example.md` when the user asks about Domain, DDD, COLA, Entity, Value Object, Repository, or protocol boundaries.

### Frontend / full-stack web

Start from a visible interaction: “用户点击购买按钮后页面应该进入 loading，再展示成功或错误”. Let bugs force state boundaries:

- DOM copy-paste works for one page; component appears when repeated UI diverges.
- `useState` appears when UI must remember user input.
- `useEffect` appears when rendering must synchronize with external data.
- Client cache/query library appears when loading/error/refetch logic repeats.
- Form schema appears when scattered validation becomes inconsistent.
- API contract appears when frontend and backend disagree on fields/status codes.

Do not introduce React/Vue patterns as doctrine; introduce them when interaction bugs or duplication force them.

### Agent / coding agent / tool-use systems

Start from a naive loop: “模型应该读任务、调用工具、检查结果、继续修”. Let failures force structure:

- Prompt-only approach fails to remember state → task state / scratchpad / plan appears.
- Model hallucinates tool arguments → schema and validation appear.
- Tool succeeds but result not verified → evaluator/verifier appears.
- Long tasks lose context → checkpoints and artifacts appear.
- Agent loops forever → stop conditions and budget appear.
- Coding agent makes broad unsafe edits → diff review, tests, and rollback boundaries appear.

Explain agent architecture from failure modes, not from buzzwords.

### Agentic RL / post-training / LLM alignment

Start from a minimal training/evaluation wish: “模型在任务上应该更常成功”. Let metric and behavior failures force methods:

- Supervised traces imitate answers but fail at exploration → RL objective appears.
- Reward is sparse or gamed → reward shaping / verifier / preference model appears.
- Offline examples are not enough → online rollouts appear.
- Policy improves benchmark but harms safety/style → multi-objective evaluation appears.
- Long-horizon agents fail credit assignment → trajectory-level rewards and step-level diagnostics appear.

Be honest about uncertainty; when details may be current, verify online in the normal response and cite sources.

### Go / Python basics

Start from a tiny program that fails, not a syntax encyclopedia.

- Go: unused variable/import errors force stricter compile habits; interfaces appear when a caller wants behavior without caring about implementation; `go test` appears when business rules need proof; goroutines/channels appear when concurrency pressure is real.
- Python: dynamic typing makes quick scripts easy but runtime failures force type hints/tests; list/dict comprehensions appear after loops become noisy; context managers appear after resource cleanup bugs.

Teach syntax as a response to concrete pain.

### LeetCode / algorithms

Start from the brute force solution and let limits force the technique.

- Time limit exceeded forces hash map, two pointers, prefix sum, heap, monotonic stack, binary search, DP, or graph traversal.
- Wrong answer on edge cases forces invariants and boundary conditions.
- Repeated subproblems force memoization/DP.
- Need “best so far” over a moving range forces sliding window.

Always include: naive attempt → why it fails → key invariant → optimized solution → complexity → common traps.

### Protocols / APIs / infrastructure

Start from an integration wish and let boundary failures force contracts.

- “服务 A 调服务 B” starts with curl; repeated parameter confusion forces DTO/schema.
- Ambiguous errors force error codes.
- Retry risk forces idempotency keys.
- Payment/security risk forces signature verification.
- Version migration forces compatibility layer.
- Transport details belong near Adapter; durable business contract belongs near Domain/core model.

## Code and artifact guidance

Use code blocks as teaching artifacts, not exhaustive dumps. Prefer small runnable examples, failing tests, minimal requests, minimal components, or tiny pseudocode loops.

When writing code-evolution notes, label the intent:

- “先写假实现，让测试能跑”
- “加反例后，这个实现被推翻”
- “重复创建对象后，抽象才出现”
- “线上风险出现后，边界才收紧”
- “指标不对后，评估/训练方法才出现”
- “TLE/WA 后，算法不变量才出现”

## Anti-patterns to avoid

- Do not summarize uploaded files sequentially as the main body.
- Do not introduce all layers/components/algorithms at the beginning as if preplanned.
- Do not explain design patterns, frameworks, RL methods, or algorithm templates as textbook doctrine.
- Do not hide naive code; include the草棚 version when it teaches why the abstraction appeared.
- Do not make notes only conceptual; include concrete tests, commands, error messages, metrics, logs, minimal examples, and refactoring steps.
- Do not force backend terms such as Entity/Repository onto frontend, LLM, RL, or LeetCode notes. Use domain-appropriate abstractions.

## Interview closure

End major sections with concise interview phrasing that follows the chain:

```text
我不是一开始套某个架构/框架/算法模板，而是先写最小可验证版本。
失败反馈告诉我哪里不够：编译失败逼出类型，反例逼出字段，重复逼出抽象，
边界混乱逼出分层，线上风险逼出校验，指标失败逼出评估或训练方法。
所以最后的设计不是凭空画出来的，而是从问题一步步长出来的。
```
````
## agents
```yaml
interface:
  display_name: "Decision Chain Tech Notes"
  short_description: "Write technical study notes as causal decision chains across coding, full-stack, agents, LLMs, algorithms, and debugging."
```
## reference
### domain-example
````
# Domain decision-chain example

Use this reference when the user specifically asks for Domain, DDD, COLA, Entity, Value Object, Domain Service, Repository, or interview notes about domain modeling.

## Skeleton

```markdown
# 第 X 章：Domain 层不是先画架构，而是被业务规则逼出来的

## 一、MVP 手把手最小实现

### 1. 第一个愿望：我希望 [业务对象] 可以 [业务行为]
写一个测试，允许 `???` 暂时存在。
解释编译失败告诉我们需要什么类型/方法。

### 2. 第一个假实现：先让测试能跑
只写最小类型和方法。
强调这不是最终正确，只是建立反馈回路。

### 3. 加反例：不能所有情况都成立
写反例测试。
让字段/状态/校验被业务规则逼出来。

### 4. 重复出现后才抽象
当测试 setup 重复，才引入 Builder/helper。
当值计算有风险，才引入 Value Object。
当跨对象规则别扭，才引入 Domain Service。
当 Application 查不到实体，才引入 Repository 接口。

## 二、八股概念基础知识点
解释 Entity、Value Object、Domain Service、Repository、依赖倒置。
每个概念都必须回扣“它为什么在刚才的决策链里出现”。

## 三、排障过程实践
列出 test/build/package/import/precision/boundary errors。
```

## Useful phrasing

- 字段不是设计出来的，是业务反例逼出来的。
- Builder 不是因为设计模式书说好，而是因为测试 setup 重复到受不了。
- Money 不是为了 DDD 教条，而是因为支付金额不能算错。
- Repository 不是一开始规划好的，是 Application Service 写不下去时出现的。
- 协议核心结构属于业务合约；编码、header、状态码属于传输细节。

## Mini example

```go
func TestProductCanBePurchased(t *testing.T) {
    product := ???
    if !product.IsPurchasable() {
        t.Error("一个上架、有价格、有收款身份的商品应该可以购买")
    }
}
```

Decision chain:

```text
测试编译失败
  ↓
需要 Product 类型和 IsPurchasable 方法
  ↓
假实现 return true 让测试能跑
  ↓
草稿商品反例推翻假实现
  ↓
Status 出现
  ↓
没有价格/没有 SkillDid 的反例继续推翻实现
  ↓
Price、SkillDid 出现
```
````
### pattern-catalog
````
# Decision-chain pattern catalog

Use this reference when the user asks for topics outside backend/domain modeling.

## Frontend / full-stack

### MVP chain

```text
我希望用户点击按钮后看到 loading 和结果
  ↓
先写一个页面变量/DOM 操作
  ↓
多个按钮、失败态、重试态混在一起
  ↓
组件、状态、effect、query cache、表单 schema 被逼出来
```

### Interview phrasing

“我不是先为了用 React Query/表单库而引入它，而是当多个页面都在重复 loading/error/refetch 状态，且缓存一致性开始出错时，才把请求状态抽到统一的数据层。”

## Agent / coding agent

### MVP chain

```text
我希望 Agent 能完成一个任务
  ↓
先写 prompt-only loop
  ↓
模型忘记目标、乱调用工具、成功后不验证、失败后无限循环
  ↓
plan/state/tool schema/verifier/budget/checkpoint 被逼出来
```

### Interview phrasing

“我的 Agent 结构不是从名词开始堆，而是从失败模式倒推：工具参数幻觉需要 schema，结果不可信需要 verifier，长任务丢上下文需要 checkpoint，循环不退出需要预算和停止条件。”

## Agentic RL / post-training / LLM

### MVP chain

```text
我希望模型在任务上成功率更高
  ↓
先做 SFT/示例模仿
  ↓
模型会模仿但不会探索，或指标提升但行为变坏
  ↓
reward/verifier/rollout/preference/multi-objective eval 被逼出来
```

### Interview phrasing

“我会先问失败来自哪里：是数据覆盖不够、奖励不稳定、评估指标错位，还是长程 credit assignment。不同失败才对应 SFT、RL、reward shaping、verifier 或 evaluation harness，不是看到 post-training 就直接堆术语。”

## Go / Python basics

### MVP chain

```text
我希望写一个最小程序
  ↓
Go 编译器报 unused/undefined/package mismatch
  ↓
严格编译习惯、package 边界、测试文件规则被逼出来
```

```text
我希望 Python 脚本快速处理数据
  ↓
运行时才发现 None/type/key/resource cleanup 问题
  ↓
type hints、单元测试、dataclass、context manager 被逼出来
```

## LeetCode / algorithms

### MVP chain

```text
先写暴力解
  ↓
TLE/WA/边界错
  ↓
观察重复计算、单调性、窗口不变量、前缀关系、状态转移
  ↓
对应技巧被逼出来
```

### Required sections

- 暴力解为什么自然
- 它在哪里失败
- 关键不变量是什么
- 优化后的代码
- 复杂度
- 常见坑

## Protocols / infrastructure

### MVP chain

```text
两个服务先能 curl 通
  ↓
字段误解、重试重复、错误不可判、版本迁移、线上风险出现
  ↓
DTO/schema/error code/idempotency/signature/version compatibility 被逼出来
```
````