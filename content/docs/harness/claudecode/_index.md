在Claude Code源码泄露后，Agent在工业界的实践经验：《Harness design for long-running application development》
内容来自Claude官方博客，链接如下：
https://www.anthropic.com/engineering/harness-design-long-running-apps

源码外泄，但只要我自动进化的够快，就不用担心泄露

Harness 只是一种思想，Anthropic 和 OpenAI 有不同的实现和理解。这是OpenAI的：
openai.com/index/harness-engineering
openai认为harness是驾驭coding agent的一种人机协作模式，而anthropic和langchain认为harness是控制LLM，从而形成agent的外壳
《Harness engineering: leveraging Codex in an agent-first world》
内容来自OpenAI官方，链接如下：
https://openai.com/index/harness-engineering/

Building effective human-agent teams
https://claude.com/blog/building-effective-human-agent-teams

1. 核心观点: 本期解读 Anthropic 官方博客《Building effective human-agent teams》，重点是 agent 进入真实团队后，组织要把上下文、职责、权限、目标和验收方式讲清楚。
2. 背景变化: AI 使用正在从一个人面对一个聊天窗口，转向多人和多个 agent 共用 Slack、文档、代码库和会议记录这些团队工作区。
3. 团队型 agent: 这类 agent 不只是回答个人请求，而是带着持久记忆、独立凭据和工具权限，围绕同一个团队目标持续工作。
4. 上下文前提: 对 agent 来说，没有写下来、不能搜索、没有权限访问的信息基本等于不存在，公开工作和清楚边界会直接影响结果质量。
5. 角色职责: 人和 agent 要在同一张 roster 里分清谁设目标、谁分析、谁写代码、谁检查、谁做最终取舍，避免每个人私下拉一套 AI 重复做事。
6. 北极星目标: 团队先写清长期方向，再决定哪些 agent 可以主动提出新工作；没有方向的主动性很容易变成噪音。
7. 信任建立: Anthropic 的经验是先人工复核，再用检查清单、Doer Verifier、复盘记录和按任务类型授权，逐步扩大 agent 的自主范围。
8. 人类注意力: 好的团队型 agent 应该批量提问、补齐关键背景、控制待审数量，把人类留给敏感权限、困难取舍和最终审查。
9. 系列定位: Dynamic Workflows 更偏长任务编排，Codexmaxxing 更偏个人工作系统，本期补的是 agent 进入组织后需要的协作制度和团队基本功。