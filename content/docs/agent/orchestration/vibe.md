Maximizing the value of your Claude Code sessions
https://claude.com/blog/maximizing-the-value-of-your-claude-code-sessions

选题来源：同样修一个 bug，用 Claude Code 来修，花的钱可以差出好几倍。八月十四号，Anthropic 官方博客发了一篇文章。整篇文章就做一件事：把 Claude Code 的 token 账单拆开，告诉你钱花在哪，哪些操作在白白烧钱。
核心内容：官方给了六条建议。第一，任务之间跑 /clear。第二，开局定好模型和推理强度，中途别切。第三，提到文件用 @ 引用，别只打文件名。第四，给输出多的命令加静默参数，或者扔进子 agent。第五，新会话先跑一次 /context，看看开局加载了什么。第六，离开键盘之前跑 /compact。
具体效果：官方给的一个对比，同样一个修复，一个会话里 Claude 直接读那两个相关文件，改完收工，一共五次请求。另一个会话里，它先在仓库里 grep 了一圈，一路上读了十几个文件才找到这两个，一共十八次请求，而且从这以后每一轮都拖着这些文件往前走。
系列定位: codexmaxxing 讲长期工作法，Opus 4.8 那期讲模型与推理旋钮，GPT-5.6 那期讲服务端降本，本期补上单次 Claude Code 会话的使用侧账单。

Anthropic这六条建议很实用，尤其是/clear和/compact这两条。实际上最大的token浪费不在于单次对话的冗余，而是上下文滚雪球——每轮都拖着之前读过的文件继续走，请求越多token翻倍越厉害。我们最近也在算AI Agent的运营成本账，发现合理管理上下文窗口能眀60%以上的token开销。这期选题太及时了
