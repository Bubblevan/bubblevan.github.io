https://openai.com/zh-Hans-CN/index/open-source-codex-orchestration-symphony/

1. 核心观点: Symphony 把 Codex 从聊天窗口里的代码助手，推进成围绕任务长期运行的工程队友。
2. 背景问题: 当工程师同时管理多个 coding agent 会话时，真正瓶颈不再是模型写代码，而是人类注意力和监督成本。
3. 编排方式: Symphony 以 Linear 这类任务系统为控制面，把 issue 映射到独立 workspace，并让 agent 在任务生命周期里持续推进工作。
4. 关键机制: 任务状态、隔离工作区、依赖 DAG、PR 回流、CI 和 review 反馈处理，共同构成可观察、可恢复的 agent 工作流。
5. 工程价值: 团队可以更低成本地发起探索性任务、处理例行实现、推进最后一公里，把更多想法送进可审查的工程流程。
6. 角色变化: PM 和设计师也能从任务系统发起 feature request，拿到 review packet 或 walkthrough，但最终判断仍由工程 review、CI 和规范把关。
7. 失败处理: agent 跑偏不应只靠人工救火，而要沉淀成测试、文档、工具、guardrail 和更清晰的 workflow。
8. 使用边界: Symphony 更适合目标明确、可验证、可流程化的 routine implementation work，模糊架构判断和复杂取舍仍需要工程师主导。