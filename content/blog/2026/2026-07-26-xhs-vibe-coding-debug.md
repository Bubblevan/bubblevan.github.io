---
schema: bubblevan/v1
id: blog-20260726-xhs-vibe-coding-debug
content_kind: blog
title: "从\"Token 失效\"误判到 11/11 抓取成功：一次 Vibe Coding 下的人机协作 Debug 实践"
date: 2026-07-26
updated: 2026-07-26
status: draft
visibility: public
summary: Agent 帮我写小红书爬虫，信心满满地告诉我"55% 数据已失效"。直到我要求它出示原始证据，才发现是正则表达式少了一个连字符。
topics: [vibe-coding, agent, debugging, xhs, playwright, scraping]
projects: [pkb]
aliases: []
---

## 背景：不止是"想爬一个人的笔记"

我在小红书关注了一个 AI/RL 方向的博主 momo.v，她的"基模日记"系列从 Day 0 写到 Day 10，内容覆盖 GRPO 训练、Coding Agent 商业分析、RLHF 实践经验。质量很高，值得沉淀到自己的知识库。

手动复制粘贴 11 篇不是不能干，但这不是工程师的解法。我希望：给一个作者主页 URL，自动输出该作者全部笔记的标题、正文、图片链接、标签、互动数据。

技术栈选 Playwright（浏览器自动化），因为 XHS 需要登录态 cookie。

第一步就遇到了登录墙：

![XHS 浏览器登录墙](/blog/2026/xhs-before-login.png)

好在之前已经配置过 Playwright persistent profile (`%USERPROFILE%\.xhs-playwright-profile`)，登录态可以复用。从 `xhslink.cn` 短链进入，观察浏览器的重定向链路：

```
[18:57:25] GOTO https://xhslink.cn/m/61TDMg78zBi
[18:57:26] REDIRECT https://www.xiaohongshu.com/user/profile/6a127fbb0000000002002405?xsec_token=...
[18:57:26] [200] /api/sns/web/v1/user/me
[18:57:42] DONE
```

`xhslink.cn/m/` 短链重定向到 `/user/profile/{uid}`，浏览器带着 cookie 自动登录。这个重定向本身也携带了一个 `xsec_token`——这个参数后面会反复出现。

## Phase 1：先把标题拿到手

XHS 的个人主页会调用 `edith.xiaohongshu.com/api/sns/web/v1/user_posted`，按 `cursor` 分页返回笔记列表（每页 30 条）。用 Playwright 的 `page.on('response')` 拦截这个 API：

```python
async def on_response(resp):
    if "user_posted" not in resp.url or resp.status != 200:
        return
    data = await resp.json()
    notes = data.get("data", {}).get("notes", [])
    for n in notes:
        collected[n["note_id"]] = {
            "note_id": n["note_id"],
            "title": n.get("display_title", n.get("title", "")),
            "type": n.get("type"),
            "liked_count": n.get("interact_info", {}).get("liked_count"),
        }

page.on("response", on_response)
```

滚动触发分页加载（XHS 不支持 `page.mouse.wheel()`，需要用 `window.scrollBy()`）：

```python
for i in range(10):
    await page.evaluate("window.scrollBy(0, 3000)")
    await page.wait_for_timeout(1500)
```

对于小博主（< 30 篇笔记），`user_posted` API 可能不触发。这时走 DOM 回退，直接扫描页面上的 `[data-note-id]` 元素。

Phase 1 的结果存放在 `posts.json`：

```json
[
  {"note_id": "6a60836a000000002201837e", "title": "基模日记 Day 10 GRPO 阶段性梳理"},
  {"note_id": "6a549fba000000000f00672c", "title": "基模日记 Day 9 有意思的强化学习"},
  {"note_id": "6a4be7fd000000000f0288b9", "title": "基模周记 Day 8 Coding Agent 商业浅析"},
  {"note_id": "6a42512f00000000110102c4", "title": "基模日记 Day 7 勇于高频迭代"},
  {"note_id": "6a38b813000000001101dc02", "title": "基模日记 Day 6 端午做了些有趣的研究"},
  {"note_id": "6a3213fc000000001003ee76", "title": "基模碎碎念 Day 5 总结这件事应该放在早上"},
  {"note_id": "6a2f6b16000000000f0058cd", "title": "基模碎碎念 Day 4 心情不错的周末"},
  {"note_id": "6a2ae20f000000003502db31", "title": "基模碎碎念 Day 3 完美主义"},
  {"note_id": "6a22f2220000000022021302", "title": "基模碎碎念 Day 2 研究 hermes"},
  {"note_id": "6a1f03ac0000000035024057", "title": "基模碎碎念 Day 1 我开始实践了"},
  {"note_id": "6a1db4f6000000003502b85a", "title": "基模碎碎念 Day 0 每天做一点输出吧"}
]
```

11 篇，note_id 加标题。但离"正文内容"还差一步。

## 问题浮现：有 note_id，为什么进不去正文

XHS 的单篇笔记 URL 格式是 `/explore/{note_id}`。我拿 Phase 1 的 note_id 直接拼了一个 URL 去访问，404。

打开浏览器 F12 发现，实际发出去的请求是 `/explore/{note_id}?xsec_token=...`——URL 里有一个叫 `xsec_token` 的查询参数。`user_posted` API 不返回这个 token。它在哪？

## Phase 2：在 HTML 里发现 xsec_token

加载完 profile 页面后，我把完整的 HTML 保存为 `profile.html`（903KB）。文本搜索 `xsec_token`，找到了。它不在任何 API 响应里，而是在笔记卡片的 `<a>` 标签 `href` 属性中。

以 Day 10 的卡片为例，`profile.html` 中的原始 HTML：

```html
<a href="/user/profile/6a127fbb0000000002002405/6a60836a000000002201837e?xsec_token=ABtDFfiRV3GxFhMugOYe7fffIqlfbnlbmwTTJhHZ6AH70="
   data-v-9122bc6a="">
  <div class="note-item" data-note-id="6a60836a000000002201837e">
    <!-- 笔记卡片内容 -->
  </div>
</a>
```

规律很清晰：`/user/profile/{uid}/{note_id}?xsec_token=...`。每张笔记卡片自带一个独立的 xsec_token。写正则提取即可。

**这里埋下了全文最大的坑。**

## 错误结论："55% Token 已失效"

Phase 2 跑完后，结果如下：

| 笔记 | 提取到的 token | 长度 | 判断 |
|------|---------------|------|------|
| Day 10 | `ABtDFfiRV3GxFhMugOYe...` | 46 字符 | 可用 |
| Day 9 | `ABbO8ggqyyk6Y9uYaeTi...` | 25 字符 | 过期 |
| Day 8 | `ABQWTQTeSXTyhuMeNWVw...` | 46 字符 | 可用 |
| Day 7 | `AB2IqLkOfeTAc3Ivlgmk...` | 46 字符 | 可用 |
| Day 6 | `ABG` | 3 字符 | 过期 |
| Day 5 | `ABXtXc7kejgE6eshaKhc...` | 42 字符 | 过期 |
| Day 4 | `AB` | 2 字符 | 过期 |
| Day 3 | `AB_jpiPcl4h_5fcHufPc...` | 46 字符 | 可用 |
| Day 2 | `ABAghhcuc05J6H8oFP_8...` | 46 字符 | 可用 |
| Day 1 | `ABzGXnh60RvQH5US0pc1...` | 23 字符 | 过期 |
| Day 0 | `ABXmKWAqDuL1yERLMrIv...` | 46 字符 | 可用 |

6 个 token 长度正常（46 字符），5 个明显短了（2 到 42 字符不等）。拼成完整 URL 访问，短 token 全部返回 404，长 token 全部正常打开。

于是下结论：

> SSR token 是静态的（页面渲染时写入 HTML），约 55% 可用，其余已过期。对于过期的 token，需要用户提供分享链接来重新生成。

数据支撑、逻辑自洽、验证通过。唯一的问题是：**结论是错的。**

## 推翻假设：回到 `profile.html` 看原始数据

看到这个结果，我的反应是：

> 不可能有剩下 5 篇不能。你给我链接，我自己去试。

这句话改变了调试方向。不是继续优化 token 获取策略，而是回头检查原始数据。

回到 `profile.html`，找到 Day 6（提取结果只有 3 字符 `ABG`）对应的原始 `<a>` 标签：

```html
<a href="/user/profile/6a127fbb0000000002002405/6a38b813000000001101dc02?xsec_token=ABG-8Y_0XjOrl8ZZs8hGs9RBaXXG0ukSn9TxlZ4gCXSLU="
   data-v-9122bc6a="">
  <div class="note-item" data-note-id="6a38b813000000001101dc02">
    ...
  </div>
</a>
```

HTML 里的 token 是 `ABG-8Y_0XjOrl8ZZs8hGs9RBaXXG0ukSn9TxlZ4gCXSLU=`，46 字符。但提取出来只有 `ABG`。被截断了。

再看 Day 4，提取结果只有 `AB`（2 字符）：

```html
<a href="/user/profile/6a127fbb0000000002002405/6a2f6b16000000000f0058cd?xsec_token=AB-CaCEi6m22pRVjMBHFxF3fYxDTA0AsG2WzHwaFOvqf0="
   data-v-9122bc6a="">
```

HTML 里是 `AB-CaCEi6m22pRVjMBHFxF3fYxDTA0AsG2WzHwaFOvqf0=`（46 字符）。提取出来只有 `AB`。

**5 个"过期"的 token，全部是在遇到 `-`（连字符）时被截断的。不是平台限制，是提取逻辑有 bug。**

## 根因：正则表达式漏了一个字符

原来的正则：

```python
# 错误：字符类里缺少连字符 -
XSEC_PATTERN = re.compile(
    r'/user/profile/\w+/([a-f0-9]{24})\?xsec_token=([A-Za-z0-9_+/=]+)'
)
```

`-` 不在 `[A-Za-z0-9_+/=]` 这个字符类里。XHS 的 xsec_token 是 base64 风格的 46 字符字符串，约一半的 token 包含 `-`。正则遇到 `ABG-8Y...` 时只匹配到 `ABG` 就停了——`-` 不在允许的字符集里，匹配终止。

修复：

```python
# 正确：字符类加一个 -
XSEC_PATTERN = re.compile(
    r'/user/profile/\w+/([a-f0-9]{24})\?xsec_token=([A-Za-z0-9_+/=-]+)'
)
```

修复后的完整对比：

| 笔记 | 旧 regex 提取 | 新 regex 提取 | 根因 |
|------|-------------|-------------|------|
| Day 10 | `ABtDFfiRV3GxFhMugOYe...` (46c) | `ABtDFfiRV3GxFhMugOYe...` (46c) | 无 `-`，恰好没触发 |
| Day 9 | `ABbO8ggqyyk6Y9uYaeTi...` (25c) | `ABbO8ggqyyk6Y9uYaeTi...` (46c) | 含 `-`，在第 25 位切断 |
| Day 8 | `ABQWTQTeSXTyhuMeNWVw...` (46c) | `ABQWTQTeSXTyhuMeNWVw...` (46c) | 无 `-` |
| Day 7 | `AB2IqLkOfeTAc3Ivlgmk...` (46c) | `AB2IqLkOfeTAc3Ivlgmk...` (46c) | 无 `-` |
| Day 6 | `ABG` (3c) | `ABG-8Y_0XjOrl8ZZs8hG...` (46c) | `ABG` 后紧跟 `-` |
| Day 5 | `ABXtXc7kejgE6eshaKhc...` (42c) | `ABXtXc7kejgE6eshaKhc...` (46c) | 含 `-`，在第 42 位切断 |
| Day 4 | `AB` (2c) | `AB-CaCEi6m22pRVjMBHF...` (46c) | `AB` 后紧跟 `-` |
| Day 3 | `AB_jpiPcl4h_5fcHufPc...` (46c) | `AB_jpiPcl4h_5fcHufPc...` (46c) | 无 `-` |
| Day 2 | `ABAghhcuc05J6H8oFP_8...` (46c) | `ABAghhcuc05J6H8oFP_8...` (46c) | 无 `-` |
| Day 1 | `ABzGXnh60RvQH5US0pc1...` (23c) | `ABzGXnh60RvQH5US0pc1...` (46c) | 含 `-`，在第 23 位切断 |
| Day 0 | `ABXmKWAqDuL1yERLMrIv...` (46c) | `ABXmKWAqDuL1yERLMrIv...` (46c) | 无 `-` |

5/11 的 token 含 `-`，全部被截断。修复后 11/11 的 token 都是 46 字符，全部可访问。

## Phase 3：正文提取的又一个坑

token 修好后，Phase 3 用 Playwright 逐个 navigate 到单篇 URL，提取内嵌在页面里的 `window.__INITIAL_STATE__`。XHS 把笔记的完整数据（标题、正文、图片列表、标签、互动统计、作者信息）全部序列化在这个全局变量里。

第一次尝试直接 `page.evaluate()` 取 JS 对象：

```python
# 失败：__INITIAL_STATE__ 有循环引用，无法序列化
raw_state = await page.evaluate("() => window.__INITIAL_STATE__")
# -> Page.evaluate: Cannot serialize result: object reference chain is too long
```

`__INITIAL_STATE__` 是一个巨大的嵌套对象，内部存在循环引用，Playwright 的 `evaluate()` 无法将其序列化返回。

修复思路：不取 JS 对象，先取页面 HTML，再用已有的 HTML 解析器处理。项目里恰好有一个 `xhs_note_reader.py`，已经实现了 `extract_initial_state(html)` 和 `find_note(state, note_id)`，可以直接复用：

```python
# 成功：先取 HTML，再用已有解析器
html = await page.content()
state = extract_initial_state(html)     # 从 HTML 中提取 __INITIAL_STATE__ JSON 字符串并解析
note = find_note(state, note_id)        # 在巨大的 state 树里精确定位当前笔记

# 提取各字段
title = note.get("title")
desc = note.get("desc")
images = extract_image_urls(note)       # 解析 imageList，取高质量图片 URL
tags = extract_tags(note)              # 提取 tagList
stats = extract_stats(note)            # 提取 likedCount / collectedCount / commentCount
```

最终 Phase 3 的运行结果：

```
[1/11] 基模日记 Day 10 GRPO 阶段性梳理... 完成 (7 images)
[2/11] 基模日记 Day 9 有意思的强化学习... 完成 (6 images)
[3/11] 基模周记 Day 8 Coding Agent 商业浅析... 完成 (7 images)
[4/11] 基模日记 Day 7 勇于高频迭代... 完成 (7 images)
[5/11] 基模日记 Day 6 端午做了些有趣的研究... 完成 (6 images)
[6/11] 基模碎碎念 Day 5 总结这件事应该放在早上... 完成 (4 images)
[7/11] 基模碎碎念 Day 4 心情不错的周末... 完成 (6 images)
[8/11] 基模碎碎念 Day 3 完美主义... 完成 (4 images)
[9/11] 基模碎碎念 Day 2 研究 hermes... 完成 (3 images)
[10/11] 基模碎碎念 Day 1 我开始实践了... 完成 (3 images)
[11/11] 基模碎碎念 Day 0 每天做一点输出吧... 完成 (3 images)
====================================
TOTAL: 11 notes, 11 accessible
```

11 篇全部成功，总计 60 张图片，完整正文内容。

## 最终架构

回顾整个链路，实际形成了一条三阶段流水线：

```
Phase 1: 主页加载
  ├── 拦截 user_posted API（大博主，30 篇以上）
  └── DOM 回退 [data-note-id]（小博主）
  -> 输出: {note_id: title}

Phase 2: SSR HTML 解析
  └── 正则提取 <a href="/user/profile/{uid}/{note_id}?xsec_token=...">
  -> 输出: {note_id: xsec_token}

Phase 3: 单篇内容提取
  ├── navigate 到 /explore/{note_id}?xsec_token=...
  ├── 取 page.content() -> extract_initial_state()
  └── find_note() -> 提取 title / desc / images / tags / stats
  -> 输出: 完整笔记数据
```

最终输出 `profile_posts.json` 的结构：

```json
{
  "profile": "https://www.xiaohongshu.com/user/profile/6a127fbb0000000002002405",
  "count": 11,
  "accessible": 11,
  "notes": [
    {
      "note_id": "6a60836a000000002201837e",
      "title": "基模日记 Day 10 GRPO 阶段性梳理",
      "desc": "最近感觉 claude code 很难用，codex 也不香了，好想自己整一个简易又帅气的 coding agent...",
      "images": [
        "http://sns-webpic-qc.xhscdn.com/202607262014/0cb8e5e9bea379a99609e5d53efc4316/..."
      ],
      "tags": ["大模型", "GRPO", "强化学习", "智能体", "codex"],
      "stats": {"likes": "163", "collects": "176", "comments": "13"},
      "author": {"nickname": "momo.v", "user_id": "6a127fbb0000000002002405"},
      "xsec_token": "ABtDFfiRV3GxFhMugOYe7fffIqlfbnlbmwTTJhHZ6AH70=",
      "accessible": true
    }
  ]
}
```

## Vibe Coding 复盘：AI Agent 辅助开发的三条教训

**1. Agent 的实验结论需要"证据链审计"**

Agent 跑实验、出数据、下结论。这条链上任何一个环节出错，结论就全错。正则少一个字符，实验数据（token 提取结果）就已经被污染了，后续的一切推断（"55% 过期""静态 token 会失效"）都是基于脏数据做的。

我不是因为"比 Agent 聪明"才发现问题。我只是做了工程师该做的事：在相信结论之前，要求查看原始数据。打开 `profile.html`，搜索 `xsec_token`，肉眼比较提取值和原始值——5 分钟的事。

**2. 保留中间产物**

`profile.html`（903KB）存了完整 SSR 页面，`probe.log` 记录了 HTTP 重定向链路，`posts.json` 保留了 Phase 1 的中间结果。这些文件让整个 debug 过程可以脱机进行：不需要重新登录 XHS，不需要重新跑浏览器，在 VS Code 里搜索文本就能定位问题。

删掉它们就没有回头路。最便宜的错误保险就是别删中间文件。

**3. "AI 错了"不是问题，"没人检查"才是问题**

Agent 基于被截断的 token 得出"55% 过期"的结论，这个推理路径本身没有逻辑错误——如果输入数据确实只有 3 字符的 `ABG`，判断它过期是合理的。真正的问题是：把这个结论当成"平台限制"写入 skill 之前，没有复核过原始 HTML。

修正的方向不是"不用 AI"，而是"AI 出数据 -> 人验数据 -> AI 更新"。

## 工具沉淀

最终不是一次性脚本：

- `scripts/tools/profile_capture.py`：三阶段流水线，给定任意 XHS 作者主页 URL，自动输出全部笔记的完整内容
- Skill `xhs-profile-scraper` v2.0：流程文档化，包含 xsec_token 提取的正确正则和常见坑位
- 输出通过 `bubblevan-pkb-capture` 自动进入个人知识库，整个链路无需手动操作
