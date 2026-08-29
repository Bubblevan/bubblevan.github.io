Agent在工业界的实践经验：《Claude Skills构建和使用指南》
内容来自Claude官方的3篇博客，链接如下：
https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers
https://claude.com/blog/building-agents-with-skills-equipping-agents-for-specialized-work
https://claude.com/blog/complete-guide-to-building-skills-for-claude

skills是给ReAct模式的agent用的，它在agent loop里动态调用，有点像动态提示词。workflow则是人工提前写好的流程程序，虽然里面可能会用到LLM，但执行完全按代码走。也就是说，agent有了skills，不一定会按你希望的顺序用，而workflow一定会按流程执行。实际应用中，用带skills的ReAct agent还是workflow，要看场景，前者更灵活、能探索，后者更可控、稳定。

Agent在工业界的实践经验：《skill-creator升级详解》
内容来自Claude官方博客和github库里面的skill，链接如下：
https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills
https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
https://github.com/MegaSuperKitty/WeClaw
最后一个链接是我在1月做的类openclaw应用，里面集成了我几乎所有视频提到的技术


还有几个2026早期的prompt联合优化：
工作流Agent多Prompt联合优化（1）GEPA：超越GRPO，让Prompt 像基因一样进化
01-29
工作流Agent多Prompt联合优化（2）MIPRO：贝叶斯优化探索最优Prompt提示词组合
586
0
08:00
工作流Agent多Prompt联合优化（2）MIPRO：贝叶斯优化探索最优Prompt提示词组合
01-30
工作流Agent多Prompt联合优化（3）ADOPT：超越GEPA，像训练模型一样训练Prompt
988
0
08:27
工作流Agent多Prompt联合优化（3）ADOPT：超越GEPA，像训练模型一样训练Prompt

以及半年内的
[Agent skill编排]01-腾讯GraSP-编排skill graph，规划Agent行动路径
3310
0
10:03
[Agent skill编排]01-腾讯GraSP-编排skill graph，规划Agent行动路径
04-23
[Agent skill编译] 上海交大爆火论文-SkVM-把Agent Skill从提示词变成可编译的系统组件
4146
0
12:45
[Agent skill编译] 上海交大爆火论文-SkVM-把Agent Skill从提示词变成可编译的系统组件
04-26
[Agent skill编排]02-阿里最新论文-SKILLGRAPH-让技能关系图和模型参数共同进化
4122
1
09:16
[Agent skill编排]02-阿里最新论文-SKILLGRAPH-让技能关系图和模型参数共同进化
05-24
[Agent Skills] 视觉Skill来了-上海交大新论文-MMSkills让Agent学会判断屏幕状态
3984
1
09:05
[Agent Skills] 视觉Skill来了-上海交大新论文-MMSkills让Agent学会判断屏幕状态
06-03
[Agent skill编译] 港中文新论文-SkillRAE：把检索到的技能在线编译为有效且紧凑的上下文
2304
0
10:44
[Agent skill编译] 港中文新论文-SkillRAE：把检索到的技能在线编译为有效且紧凑的上下文
07-14