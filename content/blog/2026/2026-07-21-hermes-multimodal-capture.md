---
schema: bubblevan/v1
id: blog-20260721-hermes-multimodal-capture
content_kind: blog
title: Hermes × 多模态内容捕获：从微信转发到博客沉淀的自动化回路
date: 2026-07-21
updated: 2026-07-21
status: draft
visibility: public
summary: 一条小红书链接经过 Hermes 的完整旅程——短链解析、SSR 正文提取、PaddleOCR GPU 图文识别、Playwright 评论区抓取、子 Agent 整理 Markdown、PKB 写入 Hugo 博客，以及三个 Python 环境并存的真实原因
topics: [hermes, agent, workflow, xiaohongshu, ocr, paddleocr, playwright, pkb, hugo, multimodal, automation]
projects: [pkb]
aliases: []
authors: [bubblevan]
---

## 0. 一次真实运行

7 月 21 日，我读到了三篇小红书帖子——博主 Link 写的「2026 AI 行业观察暴论」系列。三篇加起来 9 张图、超过 150 条评论，内容涉及基座模型行情、Infra 收缩、多模态窗口期。

我把三条链接转发给 Hermes，附了一句"帮我记录，图文和评论区都要"。几分钟后，本地目录里多了这些东西：

- 3 份结构化 JSON（元数据）
- 3 份 OCR 结果 JSON（图片文字）
- 3 份评论 JSON（评论区讨论）
- 3 篇 Markdown 草稿（整理后的阅读笔记）
- 3 条 PKB capture 记录（关联 URL、标签、来源）

![小红书帖子转发Hermes整理](/blog/2026/hermes.png)

---

## 1. 原来我是怎么做的

在 Hermes 接入这条链路之前，我保存一篇小红书内容的流程大概是：

```
微信看到链接
  → 打开小红书 App
  → 逐张截图 / 长按保存图片
  → 把图片传到电脑
  → 打开 OCR 工具逐张识别
  → 复制正文到 VSCode
  → 翻评论区，手动摘录有价值的讨论
  → 补充 frontmatter
  → 移动到 Hugo 的 content/blog/ 目录
  → git add && git commit
```

一篇图文大约要 15-20 分钟。三篇就是将近一小时。而且大部分时间花在"搬运"而不是"理解"上——OCR、格式、frontmatter、目录移动，每一步都是纯机械操作。

评论区尤其尴尬：有价值的信息在评论里，但手动翻 50+ 条评论、筛选高信号内容、逐条复制粘贴，做完一篇就已经不想做第二篇了。

---

## 2. 我希望 Hermes 负责到哪里

先定义边界。这条链路里，Hermes 自动完成的部分和人工保留的部分有明确分工：

| Hermes 自动完成 | 人工保留 |
|---|---|
| 识别小红书链接 → 解析短链 → 提取 SSR 正文 | 判断这篇值不值得存 |
| 下载所有图片 | 修正 OCR 里的关键错字（比如"杀伤力"→"条伤力"）|
| 对图片执行 OCR | 核查 Agent 摘要是否编造了原文没有的观点 |
| 通过浏览器抓取评论区 | 决定最终是否公开 |
| 整合三份数据为结构化 Markdown 草稿 | 执行 `git push` |
| 以 URL 去重写入 PKB | |

---

## 3. 当前系统长什么样

一条小红书链接经过四段数据路径：

```text
消息入口
  微信 → Hermes
  （用户原话 + 链接 → Skill 路由）

内容获取
  xhs_note_reader     → 短链解析、SSR 正文、图片元数据、下载缓存
  extract_paddleocr   → GPU OCR 图片文字
  xhs_comment_reader  → Playwright 浏览器抓取评论区

内容整理
  三份 JSON → evidence bundle → Hermes 草稿
  （子 Agent 按整理规则合并输出 Markdown）

内容发布
  pkb-capture → content/blog/2026/ → Hugo → GitHub Pages
```

三个 Python 环境（base / py312 / paddle3.7）是实现约束，不是架构层。它们的存在原因在第六节展开。

---

## 4. 一条链接实际经过了什么

以暴论一（「好行情基本结束」）为例，一条链接经过的完整路径。

### 4.1 Hermes 收到微信消息

我在微信里发了这条消息：

> 2026 AI 行业观察暴论一 好行情基本结束 http://xhslink.com/o/5pWUyHx6bJ9
> 帮我记录，图文和评论区都要

Hermes 拿到的东西：链接、用户原话、一个隐含意图（"记录"）、一个显式要求（"评论区也要"）。Skill 路由根据 `xhslink.com` 域名匹配到 `xhs-note-reader`。

### 4.2 解析公开正文（不用浏览器）

拿小红书正文不需要打开浏览器。流程如下：

1. 短链 `xhslink.com/o/...` 发出 HTTP 请求，小红书返回 307 重定向到 `xiaohongshu.com/discovery/item/<noteId>`
2. 请求这个 `discovery/item` 页面，服务端返回的 HTML 里嵌了一段 JSON：`<script>window.__INITIAL_STATE__=...`
3. `xhs_note_reader.py` 解析这个 JSON，提取标题、正文、作者、标签、互动数、图片 CDN URL
4. 图片下载到本地缓存目录 `.cache/xhs_note_reader/<noteId>/`
5. 输出一份统一 JSON：

```json
{
  "ok": true,
  "note_id": "6a58420c0000000006013e47",
  "title": "2026 AI 行业观察暴论一",
  "desc": "好行情基本结束...",
  "author": { "nickname": "Link" },
  "images": [ { "index": 1, "url": "...", "local_path": "..." } ],
  "combined_text": "...",
  "errors": []
}
```

整个过程 <5 秒，不依赖浏览器、不依赖登录态。也意味着评论区不在这里——评论是通过页面加载后的 XHR 请求动态拉取的。

### 4.3 PaddleOCR 读取图片文字

拿到图片后，需要一个 OCR 引擎把图片里的文字提取出来。这件事比我预想的曲折。

**第一反应：用 Hermes Skill 里写的 `--ocr-engine auto`。** 结果遇到了 PaddleOCR 3.x 在 Windows CPU 上的 oneDNN/PIR 报错。`py312` 环境里装了 PaddleOCR 3.x 和 PaddlePaddle 3.3.1，但每张图 OCR 耗时 120+ 秒，且全部抛出 `pir::ArrayAttribute` 异常。

**第二反应：在 `py312` 里重装 PaddlePaddle GPU 版。** 不行——`py312` 环境已经装了 Playwright 全家桶，空间不够塞下 CUDA 运行时。

**最终方案：用机器上已有的 `paddle3.7` 环境。** Python 3.7 + PaddlePaddle 2.5.2 + CUDA 11 编译 + PaddleOCR 2.7.0.2。独立 OCR 脚本 `extract_paddleocr.py` 改回了 PaddleOCR 2.x 的 `ocr()` API，模型只加载一次，批量处理同一目录下所有图片。

单张图片检测耗时 ~0.5 秒，识别耗时 ~0.6 秒。三张图总计不到 4 秒。

**关于 VLM 回退。** `xhs_note_reader` 本身支持三种 OCR 模式：
- `--ocr-engine paddle`：只用 PaddleOCR
- `--ocr-engine vlm`：只用本地 MiniCPM-V 模型
- `--ocr-engine auto`（仓库默认）：PaddleOCR 优先，失败时自动回退到 VLM

本次运行固定使用 `--ocr-engine paddle`，避免将图片内容发送给任何远程模型。Skill 文件里也明确写了：在 Bubblevan 的笔记本上，不要自动调用 MiniCPM-V（它会吃满内存让机器卡住）。用 Skill 约束 Agent 行为，而不是改工具的默认参数——工具保留能力，Skill 表达策略。

### 4.4 Playwright 获取评论区

正文能从 SSR HTML 里拿到，评论不行。评论是通过页面加载后发出的 XHR 请求动态获取的，必须要一个浏览器环境。

所以这里出动 `xhs_comment_reader.py`：Playwright 启动一个带持久化 profile 的 Chromium 实例，打开小红书页面，滚动加载评论，拦截网络响应里包含评论数据的请求，递归提取主评论和子回复。

为什么要有持久化 profile？因为小红书会检查登录态。没登录的页面能看到的评论数量有限，而且一些敏感内容会被折叠。用 `C:\Users\bubblevan\.xhs-playwright-profile` 保存浏览器状态，不需要每次都重新登录。

但这个 profile 有一个硬限制：**同一个 profile 同时只能被一个 Chromium 进程稳定占用。** 我第一次尝试三篇并行抓取评论区，三个 Playwright 实例同时抢同一个 profile，全部抛出 `TargetClosedError`。改为串行执行后三篇全部成功。

评论区抓取也有固有的不完整性：滚动时间有限（`--max-seconds 120`）、分页不保证翻到底、某些被折叠的评论拿不到。所以我在笔记的质量状态里标了 `comment_capture: partial`——50 条评论不等于完整的评论区，只是一个有偏快照。

### 4.5 Hermes 整理三份资料

这一步不是简单的"把三份 JSON 拼在一起"。子 Agent 收到三份源文件后，需要按照明确规则整理：

- 正文 + OCR 结果视为主资料，按原文结构和顺序排列
- 评论区只保留提供**新信息、反例或补充链接**的内容——重复赞同、纯表情回复、和原文观点完全重叠的评论剔除
- 无法确认的事实标注「待核实」，不做隐性填补
- Agent **不替原作者补写观点**——你不是 Link，不要替他下判断
- 输出保留来源位置，方便回溯哪句话来自正文、哪句来自评论

最终输出：一篇 Markdown，包含标题、原文要点（按章节）、评论区精华（按话题分组）、核心主题提炼。

### 4.6 PKB 写入 Hugo

整理好的 Markdown 写入 PKB：

```bash
python -m scripts.pkb.cli capture \
  --type note \
  --url "https://www.xiaohongshu.com/discovery/item/6a58420c0000000006013e47" \
  --text "2026 AI 行业观察暴论一：好行情基本结束..." \
  --topic "AI行业观察" --topic "校招" \
  --visibility private \
  --source-agent hermes \
  --source-platform windows \
  --source-channel weixin \
  --raw "2026AI 行业观察暴论一 ... 帮我记录，图文和评论区都要"
```

PKB 在写入前做 URL 去重（SHA256），同一链接不会被捕获两次。`private` 的笔记生成草稿但不发布。`source_agent`、`source_channel` 写进 capture 记录的可追溯元数据。最终的 Markdown 文件落到 Hugo 的 `content/blog/2026/` 下，由我来决定何时 `git commit && git push`。

### 4.7 整条链路的产物演化

每一步的输出长什么样：

```
微信消息
  { text: "帮我记录", url: "xhslink.com/o/..." }

        ↓  xhs_note_reader

note.json
  { title, desc, author, stats, images[], combined_text, errors[] }

        ↓  extract_paddleocr

ocr.json
  { "img_01.jpg": ["第一行文字", "第二行文字", ...], ... }

        ↓  xhs_comment_reader (串行)

comments.json
  { ok, comment_count, comments: [{ content, user, sub_comments, ... }], ... }

        ↓  子 Agent 整理

evidence bundle
  { source, fetched_at, original_text, image_ocr, comments, extraction_errors }

        ↓  Hermes 草稿

summary.md
  { 标题, 原文要点, 评论区精华（按话题）, 核心提炼, 待核实项 }

        ↓  pkb-capture

PKB capture
  { type: note, url, topic[], visibility, source_agent, source_channel, raw }

        ↓  Hugo

content/blog/2026/2026-07-21-ai-industry-baolun-1.md
  (frontmatter: date, title, authors, tags)
```

---

## 5. 桥梁：Hermes 和 Hugo 之间传递的不只是文件

PKB 是写入入口，但真正把两边连起来的，是以下三样东西。

### 5.1 来源记录

每篇内容至少保留：

```yaml
source_url: https://www.xiaohongshu.com/discovery/item/6a58420c0000000006013e47
source_platform: xiaohongshu
captured_at: 2026-07-21T17:41:53+08:00
source_agent: hermes
source_channel: weixin
```

半年后你不会记得这篇文章是从哪来的。这些字段让你能追溯到原始链接，判断内容是否需要更新。

### 5.2 内容分层

一篇笔记里可能混着五种不同来源的文本：

```text
原始标题与正文    ← 小红书笔记的公开 SSR
OCR 原文          ← PaddleOCR 从图片中识别
评论原文          ← Playwright 从网络响应中抓取
Hermes 摘要       ← Agent 整合后的结构化笔记
你自己的补充      ← 发布前人工添加的看法
```

不分层的话，半年后你分不清"基座模型进头部封死"这句话是博主 Link 说的、某个评论者说的、还是 Hermes 推断的。

### 5.3 质量状态

```yaml
capture_status: complete
ocr_engine: paddle
ocr_reviewed: false
comment_capture: partial    # 不等于"完整评论区"
```

评论抓取有滚动时间、登录态、分页的多重限制。"抓到了 50 条"不等于"评论区已完整"。标注 `partial` 是对未来读者的诚实。

---

## 6. 为什么系统有三个 Python 环境

不是设计如此，是被依赖逼出来的。

| 环境 | Python | 为什么存在 | 不能被谁替代 | 当前风险 |
|------|--------|-----------|-------------|---------|
| base (hermes venv) | 3.11 | 链接解析 + PKB CLI，能正常访问 HTTPS | py312 SSL 握手超时，paddle3.7 版本太旧没有 `pkb` 依赖 | 依赖污染（hermes venv 的 click/pydantic 会泄漏到其他环境） |
| py312 | 3.12 | Playwright 浏览器自动化 | Python 3.7 不支持 Playwright | profile 路径在 bash/PowerShell 间不一致 |
| paddle3.7 | 3.7 | PaddleOCR 2.7 + PaddlePaddle 2.5.2 GPU | py312 空间不足装 GPU 运行时 | 版本旧（PaddlePaddle 2.5.2, CUDA 11） |

每个环境的 Python 版本差异导致了严格的隔离要求：`paddle3.7` 的 PaddlePaddle 导入 `httpx` 时，如果 PYTHONPATH 泄漏了 hermes venv 的 `click`（用了 Python 3.11+ 语法），直接 `SyntaxError`。所以每个命令前面都挂着 `PYTHONPATH=""`。

同样，bash 不继承 conda 的 PATH。`paddle3.7` 环境里的 CUDA DLL（`cublas64_11.dll`）在 `D:\Anaconda\envs\paddle3.7\Library\bin` 下，不手动加进 PATH 就报 `cublas64_118.dll not found`。

---

## 7. 三个真正影响设计的故障

### 故障一：PaddleOCR 3.x CPU 上的 oneDNN/PIR

**现象**：`ocr.ocr()` 调用报 `ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute]`

**错误判断**：以为是环境变量没设对。试了 `PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=False`、`FLAGS_use_mkldnn=0`、`KMP_AFFINITY=disabled`，都不行。

**实际原因**：PaddleOCR 3.x + PaddlePaddle 3.3.1 在 Windows CPU 上的 oneDNN 后端有兼容性 bug。即使设置了上述环境变量，`ocr()` 调用仍然触发 PIR 属性转换异常。而 `predict()` API 虽然不报错，但每张图耗时 120+ 秒。

**修改**：放弃 PaddleOCR 3.x。切换到已有的 `paddle3.7` 环境（PaddleOCR 2.7 + PaddlePaddle 2.5.2 GPU 编译版）。OCR 脚本改用 2.x 的 `ocr()` API，模型只加载一次，11 张图总计 ~4 秒。

**留下的限制**：`paddle3.7` 的 Python 版本和 PaddlePaddle 版本都偏旧，未来如果 PaddleOCR 2.x 不再维护，需要找到新的 GPU 环境方案。

### 故障二：Git Bash、Conda PATH 与 CUDA DLL

**现象**：`paddle3.7` 的 Python 导入 PaddlePaddle 正常，`paddle.device.is_compiled_with_cuda()` 返回 `True`，`paddle.device.cuda.device_count()` 返回 `1`。但 OCR 调用时报 `cublas64_118.dll not found`。

**错误判断**：以为机器上没有 CUDA 11.8。去 `C:\Program Files\NVIDIA GPU Computing Toolkit\` 下搜，只有 CUDA 12.5 的 `cublas64_12.dll`。

**实际原因**：`cublas64_11.dll` 不在系统 CUDA 目录里，在 conda 环境里：`D:\Anaconda\envs\paddle3.7\Library\bin\cublas64_11.dll`。PowerShell 里 `conda activate paddle3.7` 会自动把这个路径加入 PATH。但 git-bash 不继承 conda 的 PATH 修改。

**修改**：每个 OCR 命令前置 `PATH="/d/Anaconda/envs/paddle3.7/Library/bin:$PATH"`。

**留下的限制**：硬编码路径。如果环境目录名改变，所有命令都要更新。

### 故障三：Playwright 持久化 profile 并发冲突

**现象**：三篇笔记同时抓取评论区，全部 `TargetClosedError: Target page, context or browser has been closed`。Chromium 进程启动后立刻退出。

**错误判断**：以为是 git-bash 环境不支持启动 Chromium GUI。试了 PowerShell 包装，仍然失败。又以为是 `$HOME` 路径在 bash 和 Python 之间解析错误（确实出现过 `D:\c\Users\...` 的拼接错误）。

**实际原因**：同一个 Playwright 持久化 profile 只能被一个 Chromium 进程稳定占用。三个实例同时抢同一个 `user-data-dir`，后启动的导致先启动的崩掉，连带反应全部失败。

**修改**：评论区抓取改为串行。三个笔记一次只跑一个，等前一个写完 JSON 再启动下一个。同时将 bash 环境下的命令改为 `powershell -NoProfile -Command "..."` 包装，避免路径解析问题。

**留下的限制**：串行意味着三篇评论区需要累积等待时间（~90 秒）。如果未来要批量抓取更多内容，需要实现 profile 池或轮流占用。

---

## 8. 这次运行的结果

| 指标 | 数据 |
|------|------|
| 链接数量 | 3 |
| 图片数量 | 9（每篇 3 张） |
| OCR 总耗时 | ~8 秒（paddle3.7 GPU，含模型加载） |
| 抓取评论数 | 暴论一 19 / 暴论二 13 / 暴论三 19，共 51 条 |
| 生成草稿 | 3 篇 Markdown + 3 条 PKB capture |
| OCR 典型错字 | 「杀伤力」→「条伤力」、「捋」→「持」、「复盘」→部分丢失 |
| 从转发到草稿 | ~10 分钟（含评论区串行等待） |
| 最终仍需人工 | 核查 Agent 摘要未编造内容、修正 OCR 错字、决定公开、git push |

时间从过去的一小时降到了十分钟，而且大部分等待时间在评论区 **串行** 爬取——我可以在等的时候做别的事。

---

## 9. 目前还没有自动化的部分

诚实地说，当前系统距离"发一条微信就自动出博客"还有这些缺口：

- **评论区不是完整的。** 小红书评论有滚动深度、登录态、折叠策略的限制。`comment_capture: partial` 是事实，不是谦虚。
- **小红书改版会导致解析器失效。** SSR HTML 结构和 `window.__INITIAL_STATE__` 的 key 名称完全依赖小红书前端。一旦改版，`xhs_note_reader` 需要跟进适配。
- **OCR 仍然会出错。** 特殊字体、密集排版、水印覆盖的文字都会导致误识别。本次 OCR 结果里「杀伤力」变成「条伤力」就是一个例子。
- **Agent 摘要需要人工核查。** Hermes 可能把评论区的某句话当成原文观点，或者在整理过程中遗漏了关键段落。目前的策略是"对 Agent 的输出保持信任但验证"。
- **知乎适配尚未完成。** 虽然已有框架，但知乎的页面结构和评论系统跟小红书完全不同。
- **发布仍然需要人工确认。** git commit、git push、Hugo rebuild 没有自动化。这是有意为之——目前我希望每篇博客发布前有人工最终审查。
- **Skill 更新缺少自动回归测试。** Skill 文件修改后，无法自动验证"下次 Agent 调用同样的命令是否还能跑通"。

---

## 10. 下一步只做三件事

1. **统一 provenance 与质量字段。** 每次 capture 自动附带 `source_url`、`ocr_engine`、`ocr_reviewed`、`comment_capture` 等结构化字段，而不是靠人工在 Markdown 里补注释。
2. **一条端到端 fixture。** 选一篇已成功捕获的小红书笔记，固定它的 JSON 输出作为测试用例。每次改完 Skill 或工具链，跑一遍这条 fixture 确认没有退化。
3. **capture → review → publish 三态流程。** 当前 PKB 的 `private`/`public` 是二态的。需要一个中间的 `review` 状态：Hermes 写入草稿 → 我修正 OCR 和摘要 → 确认发布。

其他方向（飞书接入、定时抓取、Telegram 适配、Cron 自动采集关注博主、Newsletter 生成）都很有吸引力，但先把上面三条做好。

---

## 附录

### A. 环境矩阵

| 环境名 | Python | 关键包 | 用途 |
|--------|--------|--------|------|
| base (hermes venv) | 3.11 | pkb CLI, xhs_note_reader | 链接解析、元数据提取、图片下载、PKB 写入 |
| py312 | 3.12 | playwright, chromium | 浏览器自动化抓取评论区 |
| paddle3.7 | 3.7 | paddlepaddle-gpu 2.5.2, paddleocr 2.7.0.2 | GPU 加速 OCR |

### B. 完整命令

**元数据 + 图片下载（base 环境）：**
```bash
cd D:\MyLab\Hugo\bubblevan.github.io
python scripts/tools/xhs_note_reader.py \
  --url "http://xhslink.com/o/5pWUyHx6bJ9" \
  --download-images --max-images 20 \
  --out-json "D:/MyLab/xhs-note.json"
```

**GPU OCR（paddle3.7 环境）：**
```bash
PATH="/d/Anaconda/envs/paddle3.7/Library/bin:$PATH" \
PYTHONPATH="" \
/d/Anaconda/envs/paddle3.7/python.exe \
  scripts/tools/extract_paddleocr.py \
  ".cache/xhs_note_reader/<noteId>" \
  > ocr.json
```

**评论区抓取（py312 环境，串行，PowerShell 包装）：**
```powershell
powershell -NoProfile -Command "
  cd D:\MyLab\Hugo\bubblevan.github.io
  D:\Anaconda\envs\py312\python.exe scripts/tools/xhs_comment_reader.py \
    --url 'http://xhslink.com/o/5pWUyHx6bJ9' \
    --out-json 'D:/MyLab/comments.json' \
    --user-data-dir 'C:\Users\bubblevan\.xhs-playwright-profile' \
    --max-seconds 120 --max-scrolls 40
"
```

**PKB 捕获（base 环境）：**
```bash
python -m scripts.pkb.cli capture \
  --type note \
  --url "<xiaohongshu-url>" \
  --text "<summary>" \
  --topic "AI行业观察" \
  --visibility private \
  --source-agent hermes --source-platform windows --source-channel weixin \
  --raw "<verbatim user message>"
```

### C. 目录结构

```text
D:\MyLab\Hugo\bubblevan.github.io\
├── scripts/tools/
│   ├── xhs_note_reader.py
│   ├── extract_paddleocr.py
│   └── xhs_comment_reader.py
├── .cache/xhs_note_reader/<noteId>/
│   └── *.jpg
├── content/blog/2026/
│   └── *.md
└── data/
    └── captures/
```

### D. 相关 Skill 文件

- `xhs-note-reader/SKILL.md`：小红书链接 → OCR → PKB 完整工作流
- `xhs-comment-reader/SKILL.md`：评论区 Playwright 串行抓取规范
- `bubblevan-pkb-capture/SKILL.md`：capture 类型判断与默认参数
- `bubblevan-local-vision/SKILL.md`：本地 VLM 仅作显式回退
