---
date: 2026-07-11
title: 一次 Vibe Coding 实战：Hugo 静态网站图片的自动化归档
authors: [bubblevan]
tags: []
---

## 痛点：Ctrl+V 贴图爽，Hugo 静态路径苦

我用 Hugo 搭建个人网站，最喜欢的就是在 VSCode 里随手 Ctrl+V 粘贴截图，图片直接存进 `content/daily/2026/jul/image.png` 这类路径，跟 markdown 笔记挨在一起，特别自然。

但 Hugo 的规则是：**静态资源必须放在 `static/` 目录下**，用 `/daily/...` 这样的站点绝对路径引用，否则生成站点时图片会 404。

于是每次写完笔记，我都得手动：把图片从 `content/daily/...` 复制到 `static/daily/...`，修改 markdown 里的引用链接，再把原图删掉——繁琐、易漏、完全反直觉。

这问题不只 `daily` 目录有，`blog`、`docs`、`leetcode`、`papers`、`showcase` 也各有各的图片引用习惯和静态路径规则。

所以我决定写个自动化脚本。但这次，我不想先让 AI 一把梭写代码，然后修修补补——我想借这个小项目，**刻意练习一套工业级的人机协同开发流程**。

## 方法论先行
Vibe Coding 概念由 Andrej Karpathy 在 2025 年提出，最初的极端表述是 **完全交给AI生成、人只看结果**；工业界落地后很快演变为 **「AI辅助工程实战面试」**，允许候选人开放使用AI工具，不再纯考手撕算法熟练度，核心考察人机协同的交付能力。

1. 阿里、美团、字节等大厂的创新业务、AI相关团队，已在技术面中加入「AI工具开放的编程实战题」，本质就是 Vibe Coding 的本土化落地。
2. 赛码等官方测评平台已推出「AI Coding 双轨考试体系」：传统OJ算法题 + AI工程实战题，已落地多家头部企业，从需求拆解、代码落地、漏洞排查六个维度评估人机协同能力。
3. 海外 Google、Meta 等公司的产品经理、工程师岗位，已将 Vibe Coding 现场原型构建作为常规面试环节，核心目的是防作品集造假、考察真实落地能力。
 
我把它总结成五层标准流程，作为这个项目全程的纲领：

### 1. 规范前置层
先定义项目规则文件（如`.cursorrules`、`project-rule.json`），明确目录结构、命名规范、统一响应格式、技术栈约束。

### 2. 需求设计层（PRD + TRD）
这是最核心的一步：先输出一份AI能读懂的设计文档，和AI达成 **共识** 再开工。
- PRD：产品定位、核心功能、用户流程、边界条件
- TRD：数据模型、接口规范、架构选型、异常处理规则
标准：AI读完这份文档，可以独立开工，不需要你反复解释业务逻辑。

### 3. 任务拆解层
用固定提示词让AI生成模块化的实施计划，把大项目拆成可独立验证的子任务，明确每个模块的交付标准。

### 4. 编码迭代层
按模块逐个让AI生成代码，每完成一个模块就立即运行验证，有问题快速迭代修正，避免最后集中爆雷。

### 5. 质量校验层
代码审查、边界Case验证、集成测试，确保最终交付可用、可维护。
 
## 实战案例参考
### 案例1：面试现场60分钟典型题（后端方向）
 
题目：实现一个带用户认证的待办事项 REST API
 
1. 澄清阶段（5分钟）：和面试官确认技术栈（Spring Boot + MySQL）、是否需要分页、异常处理要求、鉴权方式。
2. 设计阶段（10分钟）：输出极简技术设计文档：
- 数据表字段：user表、todo表的字段与索引
- 接口列表：注册、登录、待办增删改查
- 统一响应格式： {code, msg, data} 
3. 实现阶段（30分钟）：把设计文档喂给AI，先生成项目骨架，再按模块生成代码，边生成边运行调试。
4. 验证讲解（15分钟）：跑通核心接口，补充边界异常处理，向面试官讲解核心逻辑与设计考量。
 
### 案例2：工业级微服务项目实战
来自腾讯云开发者的真实项目：基于 Spring Cloud Tencent 的微服务接口开发
1. 先配置`.cursorrules`，定义服务注册、配置中心、统一返回格式等工程规范。
2. 编写`project-design-doc.md`，包含北极星服务注册、COS 临时密钥上传、数据库Schema、接口规范。
3. 一条Prompt让AI生成完整的 Controller、Service、FeignClient，注解自动对齐腾讯云官方规范。
4. 人工仅校验核心鉴权逻辑，其余代码由AI生成并自动通过单测。
 
### 面试中的实操建议
1. 面试前准备
- 熟练掌握1-2个主流工具（Cursor / Claude Code / GitHub Copilot），练熟上下文注入、多文件编辑的操作，不要在面试现场摸索工具。
- 准备一套自己的极简设计文档模板、代码规范模板，面试时可以快速套用，节省时间。
2. 现场高分动作
- 边做边讲：全程 narrate 你的思路，让面试官知道你在做什么决策、为什么这么做，而不是闷头和AI聊天。
- 文档先行：哪怕只有45分钟，也要花5-10分钟先写结构化的需求/设计，再喂给AI，这是区分“会用AI”和“靠AI混”的核心标志。
- 模块化验证：拆成小功能，做完一个跑通一个，宁可少做两个功能，也要保证交付的部分能正常运行。
- 保持主导：你是决策者，AI是执行者；不要AI输出什么就用什么，要主动做取舍、定方向。
3. 绝对避坑点
- 不要完全不看AI生成的代码：面试官让你解释核心逻辑时答不上来，基本直接淘汰。
- 不要死磕细节：优先跑通MVP核心功能，再谈优化，时间有限时完成度比完美度重要。
- 不要只会说“帮我写个xx”：考察的核心是你的需求拆解、约束定义、质量把控能力，而不是你会不会发指令。

## 个人实践
### Cursorrules
- [GitHub 千星合集 awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules)：由开发者 PatrickJS 维护，汇集了前后端、全栈、移动端等几十个技术栈的 Cursor 规则模板，是目前最全的公开规则库，大量团队直接复用这套规范。
- [Andrej Karpathy 公开的 12 条 CLAUDE.md 规则](https://github.com/wcbhn/obsitian_trae/blob/main/.trae/rules/project_rules.md)：他在自己 30 个项目中实测，通过这套规则把 AI 编码错误率从 41% 降到 11%，是业内最知名的规则范本

### PRD与TRD
> “先不要写代码，先扫描仓库相关目录，结合现有结构输出 PRD 和 TRD，要求能直接指导实现。”

Codex 很快扫了一遍我的 Hugo 站点，确认了真实样例：`content/daily/2026/jul/2026-7-10.md` 里有一行 `![CUHK-welcome](image.png)`，同目录下确实有 `image.png`。于是它在 `docs/automation/` 下生成了两份文档。

#### daily-image-archiver.prd
**PRD** 明确了产品边界：只处理 `content/daily` 下的图片归档；用户流程分“粘贴图片 → 写 markdown → 执行归档命令”三步；边界条件包括一图多文跳过、alt 为空时回退命名。

````
# Daily 图片自动归档 PRD

## 1. 背景

当前 Hugo 站点的图片规范主要依赖 `static/` 目录，但日常记录更自然的工作流是：

- 在 `content/daily/.../*.md` 中写笔记
- 直接 `Ctrl + V` 粘贴图片到 markdown 同级目录
- markdown 中自动生成类似 `![CUHK-welcome](image.png)` 的本地引用

这会带来几个问题：

- 图片散落在 `content/daily` 下，不符合站点静态资源归档习惯
- 图片文件名通常是 `image.png`、`image-1.png`，缺乏语义
- 后续迁移、整理、复用图片成本高
- 长期来看，`content` 目录会混入大量非正文资产

因此需要一个自动化工具，把 `content/daily` 下的图片归档到 `static/daily/...`，并自动修正文内引用。

## 2. 目标

实现一个面向 `content/daily` 的图片归档工具，支持：

- 扫描 `content/daily` 下的图片文件
- 找到它们被哪些 markdown 引用
- 将图片复制到 `static/daily/<year>/`
- 按 markdown 中的图片 alt 文本重命名图片
- 自动修改 markdown 引用到归档后的新路径
- 校验修改结果可用后删除原图
- 通过缓存避免每次全量重复处理

## 3. 非目标

本期不做：

- `content/blog`、`content/docs` 等其他内容目录的图片归档
- 自动压缩、裁剪、格式转换图片
- 智能生成 alt 文本
- 自动识别未被引用但“可能有用”的图片
- Hugo 构建流程强绑定
- 云端存储、图床接入

## 4. 目标用户

唯一目标用户是站点维护者本人，核心场景是日常写作时快速贴图，不希望手动搬运图片或手动改链接。

## 5. 核心场景

### 场景 A：标准粘贴

输入：

- `content/daily/2026/jul/2026-7-10.md`
- `content/daily/2026/jul/image.png`
- markdown 中存在 `![CUHK-welcome](image.png)`

期望结果：

- 图片被归档为 `static/daily/2026/cuhk-welcome.png`
- markdown 引用改为 `/daily/2026/cuhk-welcome.png`
- 原始 `content/daily/2026/jul/image.png` 被删除

### 场景 B：同一篇文章多个图片

输入：

- `image.png`
- `image-1.png`
- `image-2.jpg`

期望结果：

- 依次按各自 alt 文本命名
- 若命名冲突，自动追加序号

### 场景 C：重复执行

输入：

- 已归档文章再次运行工具

期望结果：

- 工具快速跳过已处理图片
- markdown 不被重复改写
- 不重复复制、不重复删除

## 6. 用户故事

- 作为站点维护者，我希望继续在 markdown 所在目录直接粘贴图片，而不是先手工放到 `static`。
- 作为站点维护者，我希望图片能自动获得语义化文件名，方便长期维护。
- 作为站点维护者，我希望工具重复执行也是安全的，不会把已经整理好的内容弄乱。
- 作为站点维护者，我希望工具只处理 `content/daily`，先把日常日志链路打通。

## 7. 功能需求

### 7.1 扫描范围

- 递归扫描 `D:\MyLab\Hugo\bubblevan.github.io\content\daily`
- 识别扩展名：`.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`
- 默认忽略 `static/`、`public/`、`.git/`

### 7.2 引用识别

工具需识别 markdown 中的图片引用：

- `![alt](relative-path)`

本期只强支持这种标准 markdown 语法。

### 7.3 引用匹配

对每个候选图片文件，工具需要定位：

- 哪个 markdown 文件引用了它
- 引用时使用的 alt 文本是什么

如果找不到唯一引用，进入“跳过并报告”。

### 7.4 归档规则

- 目标目录：`static/daily/<year>/`
- `<year>` 优先从 markdown 所在路径推断，例如 `content/daily/2026/...` 映射到 `static/daily/2026/`
- 文件名优先使用 alt 文本 slug 化结果
- 保留原始扩展名

示例：

- `![CUHK-welcome](image.png)` -> `cuhk-welcome.png`

### 7.5 冲突处理

若目标文件名已存在：

- 若文件内容相同，直接复用已有文件
- 若文件内容不同，追加数字后缀：`cuhk-welcome-2.png`

### 7.6 markdown 改写

把原引用改为站点绝对路径：

- `![CUHK-welcome](image.png)` -> `![CUHK-welcome](/daily/2026/cuhk-welcome.png)`

选择站点绝对路径而不是相对路径，原因：

- 与 markdown 所在目录解耦
- 后续文章移动目录时不需要再修图链
- Hugo `static` 语义更稳定

### 7.7 成功校验

一次归档成功至少满足：

- 目标图片文件存在
- markdown 已完成替换
- 替换后的引用路径符合预期

### 7.8 原图删除

仅在归档与改写校验成功后，删除 `content/daily` 下原图。

### 7.9 执行结果报告

输出摘要至少包含：

- 扫描到多少图片
- 成功归档多少张
- 跳过多少张
- 删除多少原图
- 哪些文件失败及原因

## 8. 异常与边界场景

- 图片未被任何 markdown 引用：跳过并报告
- 图片被多个 markdown 引用：默认跳过并报告
- alt 文本为空：回退使用 markdown 文件名 + 序号
- alt 文本含中文/空格/符号：需 slug 化
- 目标目录不存在：自动创建
- markdown 已经引用 `/daily/...`：视为已处理
- 图片和 markdown 不在同一目录，但仍使用相对路径引用：允许处理

## 9. 性能需求

- 首次运行允许全量扫描
- 后续运行应尽量基于缓存做增量处理
- 对当前仓库规模，目标是日常执行保持在可接受范围内，不要求复杂并发优化

## 10. 缓存要求

需要本地缓存，避免每次全量重做。

缓存至少记录：

- 源图片路径
- 源图片内容哈希
- 引用 markdown 路径
- 目标静态路径
- 最近处理时间
- 最近处理状态

缓存文件可放在：

- `docs/automation/.cache/daily-image-archiver.json`

或更推荐：

- `.cache/daily-image-archiver.json`

缓存应默认加入 `.gitignore`，不进入版本库。

## 11. 成功指标

- 能正确处理 `content/daily/2026/jul/2026-7-10.md` 与同目录 `image.png`
- 二次执行不会重复搬运同一图片
- 失败场景有清晰日志，不 silently fail
- 归档后 Hugo 页面图片可正常显示

## 12. 验收标准

满足以下条件即可验收：

1. 在 `content/daily` 中存在标准 markdown 图片引用时，工具能自动完成扫描、复制、改链、删除原图。
2. 目标图片位于 `static/daily/<year>/`。
3. 新文件名优先使用图片 alt 文本 slug。
4. 冲突时不会覆盖错误文件。
5. 再次运行时，已处理图片会被安全跳过。
6. 工具能输出明确的成功/跳过/失败统计。

## 13. 版本建议

### V1

- CLI 手动执行
- 仅支持 `content/daily`
- 仅支持标准 markdown 图片语法
- JSON 缓存

### V2

- 接入 `npm` script
- 增加 `--dry-run`
- 增加 `--year` / `--month` / `--file` 精确处理
- 增加构建前校验模式

### V3

- 支持日志自动打 tags
- 扩展到 `content/blog`
````
#### daily-image-archiver.trd
**TRD** 则拍板了几个关键设计，这些决策必须在写代码之前定，否则后面就是灾难：

- **语言选型**：Node.js，利用 Node 内置 `fs/path` 和 `node:test` 做零依赖脚本，符合 Hugo 站已有 Node 环境。
- **缓存策略**：JSON 文件（`.cache/daily-image-archiver.json`），不用 git 做缓存，避免污染版本历史。
- **删除原图的保守策略**：只有同时满足“复制成功 + markdown 改链成功 + 校验成功”三个条件，才删除源图片文件。任何一步失败，原图保留。
- **保守跳过规则**：一图多文、未引用图片、目标文件已存在但内容不同——全部标为 `skip`，不强行处理。

````
# Daily 图片自动归档 TRD

## 1. 设计目标

基于当前 Hugo 仓库，实现一个安全、可重复执行、增量友好的本地 CLI 工具，自动把 `content/daily` 中的图片归档到 `static/daily`。

## 2. 结论先行

### 2.1 语言选择

建议优先用 `Node.js + TypeScript`，不优先用 Python。

原因：

- 仓库已经有 `package.json` 和现成 `node scripts/*.js`
- 后续更容易接入 `npm run ...`
- 文件扫描、路径处理、JSON 缓存、CLI 参数都很顺手
- 你的站点维护入口本身更偏前端/站点工程，而不是独立数据脚本

Python 也能做，但在这个仓库里不是最自然的主链路。

### 2.2 执行方式

建议先做“手动触发 CLI”，不直接挂到 Hugo build。

建议命令：

```bash
node scripts/daily-image-archiver.mjs
```

后续可追加：

```bash
node scripts/daily-image-archiver.mjs --dry-run
node scripts/daily-image-archiver.mjs --file content/daily/2026/jul/2026-7-10.md
```

### 2.3 链接策略

建议改写为 Hugo 站点根相对路径：

```md
![CUHK-welcome](/daily/2026/cuhk-welcome.png)
```

不建议改成复杂的文件系统相对路径。

## 3. 目录与文件约定

### 3.1 输入目录

- `content/daily`

### 3.2 输出目录

- `static/daily/<year>/`

### 3.3 脚本路径

建议：

- `scripts/daily-image-archiver.mjs`

如果后续引入 TypeScript 编译流程，再升级为：

- `scripts/daily-image-archiver.ts`

### 3.4 缓存路径

建议：

- `.cache/daily-image-archiver.json`

理由：

- 不污染 `content/` 和 `static/`
- 语义上属于本地执行态
- 适合加入 `.gitignore`

## 4. 数据流

```text
扫描 content/daily 图片
  -> 扫描 content/daily markdown
  -> 建立 markdown 图片引用索引
  -> 匹配图片文件与引用记录
  -> 决定目标文件名与目标目录
  -> 复制到 static/daily/<year>/
  -> 校验复制结果
  -> 改写 markdown 引用
  -> 校验改写结果
  -> 删除源图片
  -> 更新缓存
  -> 输出报告
```

## 5. 模块设计

建议拆成 6 个逻辑模块。

### 5.1 Scanner

职责：

- 递归扫描图片文件
- 递归扫描 markdown 文件
- 过滤无关目录

输入：

- 根目录路径

输出：

- `imageFiles[]`
- `markdownFiles[]`

建议支持的图片扩展名：

- `.png`
- `.jpg`
- `.jpeg`
- `.gif`
- `.webp`

### 5.2 Markdown Reference Indexer

职责：

- 解析 markdown 中的图片语法
- 提取 `alt` 与 `src`
- 把相对路径解析成绝对文件路径用于匹配

核心正则可先从简单版本开始：

```regex
!\[([^\]]*)\]\(([^)]+)\)
```

索引结构建议：

```json
{
  "absoluteImagePath": [
    {
      "markdownPath": "absolute-md-path",
      "originalSrc": "image.png",
      "alt": "CUHK-welcome",
      "lineHint": 11
    }
  ]
}
```

### 5.3 Planner

职责：

- 判断某张图片是否应处理
- 判断是否命中缓存
- 计算目标文件名
- 计算目标静态路径

处理规则：

- 必须恰好被 1 处 markdown 图片引用命中，才进入自动处理
- 否则输出 skip

### 5.4 Executor

职责：

- 创建目标目录
- 复制图片
- 修改 markdown
- 校验
- 删除原图

执行顺序必须固定：

1. 复制图片
2. 校验目标文件存在且哈希正确
3. 修改 markdown
4. 校验 markdown 新引用已写入
5. 删除原图
6. 写入缓存

任何一步失败，都不能删原图。

### 5.5 Cache Store

职责：

- 读取/写入 JSON 缓存
- 通过源文件哈希和 markdown mtime 做增量跳过

缓存结构建议：

```json
{
  "version": 1,
  "items": {
    "content/daily/2026/jul/image.png": {
      "sourceHash": "sha256:...",
      "sourceMtimeMs": 0,
      "markdownPath": "content/daily/2026/jul/2026-7-10.md",
      "originalSrc": "image.png",
      "alt": "CUHK-welcome",
      "targetPath": "static/daily/2026/cuhk-welcome.png",
      "targetHash": "sha256:...",
      "status": "done",
      "updatedAt": "2026-07-11T00:00:00.000Z"
    }
  }
}
```

### 5.6 Reporter

职责：

- 打印成功、跳过、失败统计
- 输出详细原因，便于人工处理边角 case

## 6. 命名策略

### 6.1 主规则

目标文件名由 alt 文本 slug 化得到。

示例：

- `CUHK-welcome` -> `cuhk-welcome.png`
- `支付流程图` -> `zhi-fu-liu-cheng-tu.png` 或退化到稳定 ASCII slug

### 6.2 中文处理建议

V1 建议避免引入复杂拼音库，采用保守方案：

1. 先保留英文、数字
2. 空格和分隔符转 `-`
3. 去掉非法字符
4. 若结果为空，则回退

回退命名：

- `<markdown-basename>-image-1.png`

例如：

- `2026-7-10-image-1.png`

这是比“必须上拼音库”更稳的 V1 方案。

### 6.3 冲突规则

若 `static/daily/2026/cuhk-welcome.png` 已存在：

- 内容哈希相同：直接复用
- 内容哈希不同：尝试 `cuhk-welcome-2.png`、`cuhk-welcome-3.png`

## 7. 匹配规则

### 7.1 图片与 markdown 的关联

不是“先扫图片再 grep 整仓库”，而是更推荐：

1. 先扫描所有 markdown
2. 建一张图片引用索引表
3. 再遍历图片文件进行 O(1) 查索引匹配

这样更稳定，也更适合缓存。

### 7.2 为什么不用纯 grep 驱动

纯 grep 方案可以做 POC，但长期缺点明显：

- 很难准确拿到 alt 文本
- 路径归一化麻烦
- 多次引用时不好建模
- 缓存逻辑不自然

所以 TRD 建议“解析 markdown + 建索引”，而不是 grep-first。

## 8. 缓存策略

## 8.1 为什么不用 git 做缓存

不建议把 git 状态当缓存主机制。

原因：

- git 适合版本跟踪，不适合表达“这张图已被归档到哪个目标文件”
- 工作区可能本来就脏，不能依赖 git clean/dirty 判断
- 哈希、目标路径、处理状态这些信息 git 不能直接给

结论：

- git 用于审计变更
- JSON 缓存用于执行态增量

### 8.2 增量判定

若同时满足以下条件，可直接跳过：

- 源文件路径存在缓存
- 源文件哈希未变
- markdown 路径仍一致
- 目标文件存在
- markdown 当前已引用目标路径

否则重新处理。

### 8.3 缓存失效

以下情况必须重算：

- 源图片内容变了
- markdown 改了图片 alt
- markdown 改了图片引用
- 目标文件被删了
- 缓存版本号升级

## 9. 幂等与安全性

工具必须满足幂等：

- 运行一次和运行多次，最终状态一致
- 不重复复制同一图片
- 不重复改写同一 markdown 引用
- 不误删未成功处理的源图

安全底线：

- 默认只删除“已完成复制且已完成改写且已完成校验”的图片
- 遇到多引用、空引用、解析异常，宁可跳过

## 10. CLI 设计

V1 建议支持以下参数：

```bash
node scripts/daily-image-archiver.mjs
node scripts/daily-image-archiver.mjs --dry-run
node scripts/daily-image-archiver.mjs --file content/daily/2026/jul/2026-7-10.md
node scripts/daily-image-archiver.mjs --year 2026
```

参数说明：

- `--dry-run`：只输出计划，不写文件
- `--file`：只处理某篇 markdown 关联图片
- `--year`：只处理某年份内容

## 11. 伪代码

```text
load cache
scan markdown files
build reference index
scan image files

for each image:
  refs = index[image.absolutePath]
  if refs.count != 1:
    report skip
    continue

  ref = refs[0]
  plan = buildPlan(image, ref, cache)

  if plan.canSkipByCache:
    report skipped_cached
    continue

  if not dryRun:
    copy image to target
    verify target exists and hash matches
    rewrite markdown reference
    verify markdown contains new src
    delete source image
    update cache

  report success

save cache
print summary
```

## 12. 实现建议

### 12.1 V1 技术栈

- Node.js 内置 `fs/promises`
- Node.js 内置 `path`
- Node.js 内置 `crypto`

V1 不必引入额外依赖。

### 12.2 package.json 建议

后续可新增：

```json
{
  "scripts": {
    "daily:images": "node scripts/daily-image-archiver.mjs",
    "daily:images:dry": "node scripts/daily-image-archiver.mjs --dry-run"
  }
}
```

### 12.3 日志建议

使用清晰的状态前缀：

- `SCAN`
- `PLAN`
- `SKIP`
- `COPY`
- `REWRITE`
- `DELETE`
- `DONE`
- `FAIL`

## 13. 测试方案

至少覆盖以下 case：

1. 单图单引用
2. 多图单文章
3. 多文章各自单图
4. 图片未引用
5. 图片被多篇文章引用
6. alt 为空
7. 目标文件名冲突但内容相同
8. 目标文件名冲突且内容不同
9. 重复执行命中缓存
10. 改写后源图删除失败

## 14. 与当前仓库的对应关系

当前已确认存在真实样例：

- markdown：`content/daily/2026/jul/2026-7-10.md`
- 源图：`content/daily/2026/jul/image.png`
- 当前引用：`![CUHK-welcome](image.png)`

因此 V1 的第一条验收链路可以直接用这组样本验证。

## 15. 推荐实施顺序

1. 先实现 `--dry-run`
2. 再实现真实复制 + 改链
3. 再实现删除源图
4. 最后加缓存

原因：

- 这样最容易观察行为
- 出错面最小
- 方便你先确认命名和路径策略是否满意

## 16. 风险与取舍

### 风险 1：alt 文本不稳定

如果日后你频繁修改 alt，文件名可能也想跟着变。

V1 取舍：

- 只在首次归档时按 alt 生成文件名
- 已归档后不因 alt 变化自动重命名静态文件

这样更稳。

### 风险 2：一图多文复用

日常笔记里后续可能出现同一张图被多篇文章引用。

V1 取舍：

- 默认跳过并报告
- 不自动决策“归谁”

### 风险 3：markdown 编码历史问题

仓库里部分 daily markdown 显示出编码痕迹，脚本实现时要统一按 UTF-8 读取，并在失败时给出明确信息，避免误写乱码。

## 17. 最终建议

这件事最合适的 V1 组合是：

- `Node.js`
- 单文件 CLI
- `content/daily` 定向处理
- JSON 缓存
- 站点绝对路径改链
- 保守跳过异常 case

这会比“直接全自动全覆盖”更稳，也更适合你现在的站点维护方式。
````

### 任务拆解
基于 TRD，我把实现拆成 7 个可独立验证的任务，并严格按“**先可观察、再可写入、最后可删除**”的顺序排列：

| 任务 | 内容 | 核心输出 | 风险控制 |
|------|------|----------|----------|
| 1 | CLI 骨架与配置入口 | 参数解析、配置归一化 | 业务逻辑与接口分离，可单测 |
| 2 | 文件扫描器 Scanner | 收集 markdown 和图片文件列表 | 不过度扩大扫描范围 |
| 3 | Markdown 图片引用解析与索引 | 图片→引用关系索引表 | 只支持标准 `![alt](src)` 语法，保守 |
| 4 | 归档计划 Planner | 生成 `process/skip` 计划 | 纯决策层，不碰文件 |
| 5 | Dry-run 可视化报告 | 结构化执行预演报告 | 执行前最后一道人工审查 |
| 6 | 复制图片 + 改写 markdown（保留原图） | 真实文件写入，但不删除 | 先验证正确，再考虑删除 |
| 7 | 校验成功则删除原图 + JSON 缓存 | 闭环，可重复安全执行 | 删除条件严格，缓存版本控制 |

这个拆法的精妙之处在于：**前 5 步全是“可观察但低破坏”的**，直到对 dry-run 报告满意了，才进入真正写文件和删文件。

下面按顺序复盘每个任务的真实实现和那些值得标记的“工程动作”。

#### 1. CLI 骨架：先把接口立住

第一个文件 `scripts/daily-image-archiver.mjs`，我没让 Codex 往里塞任何业务逻辑。它只做三件事：

- 解析 `--dry-run`、`--file`、`--year` 参数
- 归一化成一致的 `cliConfig`
- 输出一份摘要，证明配置正确

验证方式就是直接跑 `node scripts/daily-image-archiver.mjs --dry-run --file content/daily/2026/jul/2026-7-10.md`，看它能不能正确打印出“当前模式、目标文件、年份”。

这一步我学到的是：**CLI 逻辑和业务逻辑的分离**。`parseCliArgs`、`normalizeCliConfig`、`formatConfigSummary` 都是纯函数，可以被单元测试覆盖，不会跟后面的文件扫描纠缠。

#### 2. Scanner：从“能扫”到“扫对”

Scanner 的任务是递归扫描 `content/daily` 下的所有 markdown 和图片。它在 `--dry-run` 下会打印扫描统计。

用真实仓库验证时，`--file content/daily/2026/jul/2026-7-10.md` 扫出了 7 个 markdown 和 1 个图片——就是我们关注的那张 `image.png`。`--year 2026` 则扫出 144 个 markdown 和同 1 张图。

这里的设计意图是：`--file` 的语义不是“只扫这一篇”，而是“把作用域收窄到这篇 markdown 所在目录”。因为图片通常和文章同目录，这比严格单文件扫描更实用。

#### 3. Reference Indexer：不是 grep，是结构化索引

这一步把“扫描到文件”升级成“知道每张图片被哪篇文章、以什么 alt 引用”。

关键函数 `parseMarkdownImageReferences()` 解析标准语法 `![alt](src)`，提取 alt、原始 src、所在行号，并把相对路径解析成绝对图片路径。`buildReferenceIndex()` 则生成一个按图片路径分组的索引，后续 Planner 直接消费。

真实样例跑通：`2026-7-10.md` 第 12 行的 `![CUHK-welcome](image.png)` 被成功索引，alt 和绝对路径都正确。

我在这里学到：**索引不是一次性字符串匹配，而是一个可供后续模块使用的结构化数据层**。这是模块化的基石。

#### 4. Planner：process 和 skip 都是正常结果

Planner 是纯“决策层”，不碰文件系统。它根据索引和扫描结果，为每张图片生成一个计划条目，要么 `process`，要么 `skip`。

命名规则用 `slugifyAlt(alt)` 把中文或英文 alt 转成稳定文件名，空 alt 则回退到 `文章名-image-序号`。年份从 markdown 路径推断。

真实样例生成计划：目标文件 `static/daily/2026/cuhk-welcome.png`，新链接 `/daily/2026/cuhk-welcome.png`。

未引用的图片被标为 `skip`，原因是 `unreferenced-image`。

#### 5. Dry-run 报告：执行前最后一道安全网

我把 dry-run 输出从简单的打印升级成结构化报告：`buildDryRunReport()` 汇总扫描数、引用数、计划数、跳过原因统计，`formatDryRunReport()` 渲染出“Process Preview”和“Skip Preview”分区。

现在，在执行任何真实操作之前，我可以肉眼审查：哪些图将被搬运、搬去哪里、markdown 会改成什么样、哪些被跳过及原因。

#### 6. Executor：先写文件，再考虑删除

到这一步，终于动真格了。但 Codex 依然保守：复制图片到 `static/daily/2026/`，改写 markdown 引用为 `/daily/2026/cuhk-welcome.png`，然后用 `fs.readFileSync` 二次读回校验——**但明确不删原图**。

我运行 `node scripts/daily-image-archiver.mjs --file content/daily/2026/jul/2026-7-10.md`，一切如预期：目标图片生成，markdown 正确改写，原图依然保留。

这种“先验证、再清理”的节奏，让第一次真实执行毫不心慌。

#### 7. 缓存与删除：闭环
最后一步：执行成功后删除源图片，并把执行结果写入 `.cache/daily-image-archiver.json`。下次运行时，通过文件哈希匹配缓存，命中则直接跳过。

现在，同一个文件跑两遍：第一次生成图片、改链、删源图、写缓存；第二次只打印 `cached-match`，啥也不做。

#### 8. 迁移多内容源
原本脚本只处理 `content/daily`，但我还有 `blog`、`docs`、`leetcode`、`papers`、`showcase` 五个内容源。于是要做泛化。

Codex 抽象出了 `SCOPE_PROFILES` 配置表，为每个栏目定义 `contentRoot` 和 `staticRoot` 映射规则，并新增 `--scope` 参数。`package.json` 里也补全了 `npm run images:blog`、`images:all` 等命令。

但在验证 `docs` 时，问题出现了：`--scope docs --dry-run --file "content/docs/undergraduate/通识杂项/大学生物学.md"` 一个图片都没扫到。

**原因**：原来 `docs` 的图片不是放在文章平级，而是放在 `media/` 子目录里。而我们的 Scanner 在 `--file` 模式下只扫描“同目录文件”，不递归子目录，导致 `media/` 里的图片被忽略。

修复方法是把 `--file` 的扫描范围从“当前目录”调整为“当前目录及其所有子孙目录（但仅限图片）”。修完之后，`docs` 的图片被正确扫到，整个 `--scope all --dry-run` 也跑通。

这个坑很有复盘价值：**真实世界的结构总比设计时想象的更乱**。幸好我们在 dry-run 阶段就发现，而不是真实执行时才发现图片丢了。

## 收获与反思
回过头看，这个项目给我最大的收获不是一个脚本工具，而是一套**可迁移的工程方法**。那五层流程在这个项目里得到了完整的验证：

- **文档先行**：PRD 和 TRD 里的边界条件、缓存策略、保守删除规则，在后面实现时一次次避免了我犯傻。没有它们，我可能会直接写一个“一把梭”脚本，然后在某次误删图片后追悔莫及。
- **任务拆解**：每一步都可验证、可停下来检查。我甚至可以中途暂停几天，回来跑一下 dry-run 就能续上，不会迷失。
- **保守策略**：从 Planner 的 `skip` 设计，到 Executor 先不删源图，再到最后严格校验后删除——每一步都留了退路。在真实工程里，这种“留一手”的习惯比炫技重要太多。
- **人机协同的主导感**：整个过程中，我是做决策的人，Codex 是高效执行者。我没有说“帮我写个图片归档工具”，而是说“先扫描仓库出 PRD，再拆任务，再实现任务 1……”。每一轮的上下文都是结构化的，而不是散乱的自然语言。

```bash
node scripts/daily-image-archiver.mjs --scope all --dry-run --year 2026
```
有个后面使用时要注意的小点：
--year 目前只对“顶层目录就是年份”的栏目最有意义，比如 daily、blog。
像 docs、showcase 这类不是按 `content/<scope>/<year>/...` 组织的内容，带 --year 可能会扫不到东西；
这时候直接用 --scope docs 或 --file ... 更合适。