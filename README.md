# bubblevan.github.io

个人操作系统仪表盘、知识库、项目复盘与职业资产站点。基于 Hugo + Hextra 构建，全部 Markdown 驱动，静态部署。

## 目录结构

```
content/           → Hugo 内容（blog、daily、docs、papers、leetcode、projects、career）
data/              → 仪表盘数据文件（reminders、bookmarks、sources、projects）
archetypes/        → Hugo 内容模板（blog、daily、doc、project 等 7 种）
layouts/           → 自定义布局与 partials
scripts/           → 本地工具链
  kb/              → Python：内容校验 + 标记提取 + 审查 + 提升
  image-archiver/  → Node.js：图片归档与引用重写
planning/          → 规划文档（IA-RFC、PRD、TRD）
```

## 快速开始

```bash
# 开发服务器
npm run dev

# 构建
npm run build
```

## 工具链

### `scripts/kb` — 知识库管线

Phase 2 本地提取与校验工具，纯 Python 标准库。

```bash
# 校验 Phase 1 schema 合规性
python -m scripts.kb validate

# 从 daily 中提取结构化标记
python -m scripts.kb extract content/daily/2026/jul/2026-7-19.md
```

详见 [scripts/kb/README.md](scripts/kb/README.md)。

### `scripts/image-archiver` — 图片归档器

将 Markdown 中的本地图片引用迁移到 `static/` 目录下。

```bash
npm run images:daily        # 归档 daily 图片
npm run images:daily:dry    # 预览模式
npm run images:all          # 全站归档
npm run test:daily-images   # 运行测试（34 个用例）
```

### npm scripts 速查

| 命令 | 用途 |
|---|---|
| `npm run dev` | Hugo 开发服务器 |
| `npm run build` | Hugo 构建 |
| `npm run images:daily` | 归档 daily 图片 |
| `npm run images:all` | 全站图片归档 |
| `npm run test:daily-images` | 图片归档测试 |
| `npm run kb:validate` | 内容 schema 校验 |
| `npm run kb:extract` | 标记提取（需自行指定文件路径） |
| `npm run kb:review` | 审查待提升的提取条目 |
| `npm run kb:promote` | 提升条目到 data/*.yaml（需 capture_id） |

## Phase 进度

| Phase | 状态 | 内容 |
|---|---|---|
| Phase 1 | 完成 | 内容分类、frontmatter 约定、archetypes、数据文件、项目目录、career 体系 |
| Phase 2.1 | 完成 | `validate` + `extract` 管线、图片归档器重组 |
| Phase 2.2 | 完成 | `review` + `promote` 管线，审查队列与数据提升 |
| Phase 3 | 待启动 | Gateway/WeChat 捕获接入、LLM 自由文本提取 |
