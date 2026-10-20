---
schema: bubblevan/v1
id: 2026-10-07-coding-agent-explore-executor
content_kind: blog
title: "Coding Agent 里的 Explore、Executor 与上下文"
date: 2026-10-07
updated: 2026-10-07
status: draft
visibility: public
summary: "从评论区关于 ZCode、Kimi Code 和 Superpowers 的讨论出发，核对 Explore、Executor、Skills 与子 Agent 上下文隔离的实际取舍。"
topics: [coding-agent, agent-harness, context-engineering]
projects: []
aliases: []
authors: [bubblevan]
---

逛评论区时看到有人讨论 ZCode、Kimi Code 和 Superpowers：coding agent 也许不需要堆很多复杂流程，先把探索和执行分开，就能让主 Agent 少背一些搜索过程。我把这段讨论交给 ChatGPT 复核，并对照了产品文档、更新记录和多 Agent 资料。大方向说得通，但有几处需要说得更准确。

## Explore 和 Executor 是一个够小的起点

评论里说的 “Explore + Execute”，对应 ZCode 文档里的 `Explore` 和 `general-purpose`：前者只读代码、搜调用链和收集证据，后者可以改文件、运行命令。`Execute` 不是 ZCode 的官方角色名称，不过作为对后者的概括，意思基本清楚。[ZCode 的 Subagents 文档](https://zcode.z.ai/en/docs/subagents)说明了这两个内置角色的权限区别。

Kimi Code 也提供 `explore`，但内置角色还包括 `plan` 和 `coder`，所以不能说它和 ZCode 完全一样。[Kimi Code 的 Agents 文档](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents)说明这些角色会在独立上下文中处理任务，再把结果交回调用者。它们共有的设计思路，是把特定子任务交给有边界的角色，而不是让主 Agent 把每次搜索和尝试都留在自己的对话历史里。

实际工作时，Explore 可以负责回答“代码从哪里进入、调用链经过哪些模块、相关测试在哪”；执行角色则在范围明确后负责改动和验证。若任务已经清楚，额外规划未必有必要；若需求复杂、需要先拆分工作，Plan 才可能值得加入。角色数量应该跟任务复杂度一起变化。

## 子 Agent 节省主上下文，不等于省下总成本

单 Agent 调查代码时，主上下文可能逐步积累搜索结果、打开的文件、测试日志和失败尝试。子 Agent 可以在自己的上下文里读这些材料，再把关键发现整理成摘要。这样主 Agent 能收到更短、更有针对性的结果，降低上下文被过程信息挤满的机会。

但子 Agent 自己也会消耗上下文和 token，还要产生摘要并交接。它可能让主 Agent 更轻，却让系统整体做更多工作。Anthropic 对其研究型多 Agent 系统的回顾也指出，多 Agent 并行能扩大研究范围，但会带来明显更高的 token 消耗；这是该团队特定研究系统的观察，不应该直接当成所有 coding agent 的成本比例。[Anthropic 的 Multi-Agent Research System 复盘](https://www.anthropic.com/engineering/multi-agent-research-system)把并行探索带来的能力收益和额外消耗放在一起讨论。

因此评价子 Agent 时，最好把两件事分开看：主 Agent 是否保留了足够空间来做决策，以及整个任务是否因为并行、隔离或更少的错误而值得额外调用。上下文隔离有价值，但不自动等于 token 优化。

## Skills 该按任务启用

我也把评论里对 Skills 的疑问拿去核对了。ZCode 的 Skills 文档说明，启用的 Skill 名称和描述会进入每轮上下文，详细内容则按需读取；文档建议只启用当前任务会用到的 Skills，避免无关描述挤占上下文。[ZCode 的 Skills 文档](https://zcode.z.ai/en/docs/skill)

不过，不能把这个结论扩展成“复杂 Skills 都没必要”。[Superpowers](https://github.com/obra/superpowers)提供的是较完整的软件开发工作流，其中包含构思、计划、测试和审查等连续步骤。对需要团队遵循固定开发过程、或需要减少遗漏的任务，这种约束可能有帮助；对查一个函数、做一处小修改，完整流程可能只增加额外步骤。该选哪种做法，取决于任务风险、重复性和需要遵守的团队约定。

## 断流体验不一定是模型本身的问题

评论者还提到 Kimi Code 里模型偶尔断流，而 ZCode 感觉更稳定。公开资料可以找到某个环境下关于 Kimi CLI 请求流卡住的[用户反馈](https://github.com/MoonshotAI/kimi-cli/issues/2582)，也能在[ZCode 更新记录](https://zcode.z.ai/en/changelog)里看到针对中断流恢复的修复。这说明请求传输、客户端恢复和 Agent harness 都会影响使用体验。

这些资料不足以证明 Kimi Code 普遍比 ZCode 更容易断流，也不足以把问题归到某个模型上。issue 只记录一个具体环境中的报告，更新记录则只证明某个版本修过相应问题；要做产品稳定性比较，还需要相同模型、相同 API、相同网络条件和明确的重复测试。

## 暂时的判断

我目前把这套讨论理解成一个够小的起点：让 Explore 处理不确定的代码调查，执行 Agent 负责范围明确的改动；任务确实需要先拆解时再加 Plan。是否继续增加角色和流程，应该看它们带来的并行收益、上下文隔离或质量控制，能不能覆盖额外的调用和交接成本。

这不是说两种角色就适合所有任务，而是先把“调查”和“改动”这两类动作分清，再按实际需要加机制。对 harness 的评价，也要把模型、提示词、工具、上下文管理和流式恢复等部分分开看，不能只凭一次体验归因。
