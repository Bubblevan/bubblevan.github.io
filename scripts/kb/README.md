# `kb` — Knowledge Base Pipeline

Phase 2 local extraction and validation toolset. Pure Python standard library, no external
dependencies.

## Quickstart

```bash
# Validate Phase 1 schema compliance
python -m scripts.kb validate

# Extract explicit markers from a daily note
python -m scripts.kb extract content/daily/2026/jul/2026-7-19.md

# Extract to a custom output directory
python -m scripts.kb extract content/daily/2026/jul/2026-7-19.md --out generated/extraction
```

## Commands

### `validate`

Scans `content/**/*.md` and checks files that opt into `schema: bubblevan/v1` or live under
`content/projects/` / `content/career/`.

Checks performed:

| Check | Severity |
|---|---|
| Duplicate `id` values across content files | error |
| Required fields (`schema`, `id`, `content_kind`, `title`, `date`, `status`, `visibility`) | error |
| `content_kind` is one of the allowed values | error |
| `projects` references match known ids in `data/projects.yaml` | error |
| Data file ids are unique across `data/*.yaml` | error |
| `visibility: private` under public `content/` tree | warning |

Exit codes: `0` = clean, `1` = errors found. Warnings do not fail.

### `extract`

Parses explicit one-line capture markers from markdown files. Outputs JSON to
`generated/extraction/<stem>.json`. Never modifies source files.

## Marker Syntax

Write these in any markdown file (default target: `content/daily`). One marker per line.
Markers work inside markdown list items (`- ` or `- [ ]` prefixes are stripped).

### `@task` — 待办任务

捕获一个带有截止日期的任务提醒。

```
@task YYYY-MM-DD <任务描述> [#话题...]
```

| 部分 | 含义 | 必填 |
|---|---|---|
| `@task` | 标记类型：任务 | 是 |
| `YYYY-MM-DD` | 截止日期 | 是 |
| `<任务描述>` | 任务内容 | 是 |
| `#topic` | 分类标签（多个以空格分隔） | 否 |

示例：

```markdown
- @task 2026-07-25 写 StablePay 限流根因复盘笔记 #stablepay #backend
- @task 2026-07-30 准备医疗 Agent 项目提案 #medical-agent
```

提取输出：

```json
{ "type": "task", "due": "2026-07-25", "text": "写 StablePay 限流根因复盘笔记", "topics": ["stablepay", "backend"] }
```

### `@link` — 链接收藏

捕获一个值得保存的外部链接。

```
@link [标题](URL) [注释描述] [#话题...]
@link <URL> <注释描述> [#话题...]
```

| 部分 | 含义 | 必填 |
|---|---|---|
| `@link` | 标记类型：链接 | 是 |
| `[标题](URL)` | 推荐写法，保持 daily 正文可读 | 是 |
| `<URL>` | 兼容旧写法，完整链接地址 | 是 |
| `<注释描述>` | 链接说明，会写入 `note` | 否 |
| `#topic` | 分类标签 | 否 |

示例：

```markdown
- @link [DeepSeek-R1 论文](https://arxiv.org/abs/2501.12948) 推理训练参考 #rl #llm
- @link https://arxiv.org/abs/2501.12948 DeepSeek-R1 论文 #rl #llm
- @link https://github.com/anthropics/skills Anthropic Skills 规范 #agent
```

提取输出：

```json
{ "type": "link", "url": "https://arxiv.org/abs/2501.12948", "text": "DeepSeek-R1 论文", "note": "推理训练参考", "topics": ["rl", "llm"] }
```

### `@event` — 事件/日程

捕获一个日程事件或备忘事件。写日期时按显式日期提取；不写日期时，自动使用当前 markdown frontmatter 中的 `date`。

```
@event YYYY-MM-DD <事件描述> [#话题...]
@event <事件描述> [#话题...]
```

| 部分 | 含义 | 必填 |
|---|---|---|
| `@event` | 标记类型：事件 | 是 |
| `YYYY-MM-DD` | 事件日期；省略时取 frontmatter `date` | 否 |
| `<事件描述>` | 事件内容 | 是 |
| `#topic` | 分类标签 | 否 |

示例：

```markdown
- @event 2026-08-01 港中文注册材料提交截止 #school
- @event 给妈妈买手机 #daily
- @event 2026-09-15 实习投递开始 #career
```

提取输出：

```json
{ "type": "event", "event_date": "2026-08-01", "text": "港中文注册材料提交截止", "topics": ["school"] }
```

### `@project` — 项目笔记

捕获一条与特定项目相关的记录（bug、想法、进展），`project_id` 对应 `data/projects.yaml` 中的项目 id。

```
@project <项目id> <笔记内容> [#话题...]
```

| 部分 | 含义 | 必填 |
|---|---|---|
| `@project` | 标记类型：项目日志 | 是 |
| `<项目id>` | 项目标识，对应 `data/projects.yaml` 中的 `id` | 是 |
| `<笔记内容>` | 记录内容 | 是 |
| `#topic` | 分类标签 | 否 |

示例：

```markdown
- @project stablepay API Gateway 限流改用 per-endpoint 桶，压测 QPS 提升 3x #backend
- @project medical-agent 读了 CS336 的 DPO 那节，准备在医疗 QA 上试一版 #rl
```

提取输出：

```json
{ "type": "project_log", "project_id": "stablepay", "text": "API Gateway 限流改用 per-endpoint 桶，压测 QPS 提升 3x", "topics": ["backend"] }
```

### 完整 Daily 示例

```markdown
## Log

今天把 StablePay 的限流中间件拆出来了，429 根因定位到令牌桶粒度太粗。

- @task 2026-07-25 写 StablePay 限流根因复盘笔记 #stablepay #backend
- @task 2026-07-30 准备医疗 Agent 项目提案 #medical-agent

## Links

- @link https://arxiv.org/abs/2501.12948 DeepSeek-R1 论文 #rl #llm
- @link https://github.com/anthropics/skills Anthropic Skills 规范 #agent

## Events

- @event 2026-08-01 港中文注册材料提交截止 #school

## Project Notes

- @project stablepay API Gateway 限流改用 per-endpoint 桶，压测 QPS 提升 3x #backend
- @project medical-agent 读了 CS336 的 DPO 那节，准备在医疗 QA 上试一版 #rl
```

运行提取：

```bash
python -m scripts.kb extract content/daily/2026/jul/2026-7-18.md
```

输出 `generated/extraction/2026-7-18.json`，包含 6 条结构化条目：

| capture_id | type | 提取内容 |
|---|---|---|
| cap-... | task | due=07-25, "写 StablePay 限流根因复盘笔记", [stablepay, backend] |
| cap-... | task | due=07-30, "准备医疗 Agent 项目提案", [medical-agent] |
| cap-... | link | url=arxiv.org/..., "DeepSeek-R1 论文", [rl, llm] |
| cap-... | link | url=github.com/..., "Anthropic Skills 规范", [agent] |
| cap-... | event | event_date=08-01, "港中文注册材料提交截止", [school] |
| cap-... | project_log | project_id=stablepay, "API Gateway 限流改用 per-endpoint 桶...", [backend] |

## Output Schema

Extraction produces JSON files with this shape:

```json
{
  "schema": "bubblevan/extraction/v1",
  "source_path": "content/daily/2026/jul/2026-7-19.md",
  "generated_at": "2026-07-19T12:00:00+00:00",
  "items": [
    {
      "capture_id": "cap-4c2b69291d743799",
      "type": "task",
      "source_path": "content/daily/2026/jul/2026-7-19.md",
      "line": 11,
      "raw": "@task 2026-07-30 Write note #stablepay",
      "text": "Write note",
      "topics": ["stablepay"],
      "due": "2026-07-30",
      "confidence": 1.0
    }
  ]
}
```

Type-specific fields:

| `type` | Extra fields |
|---|---|
| `task` | `due` (date string) |
| `link` | `url` (full URL) |
| `event` | `event_date` (date string) |
| `project_log` | `project_id` (matches `data/projects.yaml` id) |

### `review` (Phase 2.2)

Print pending items from `generated/extraction/*.json`. Items already promoted are excluded.

```bash
python -m scripts.kb review
```

Output shows capture_id, type, text, and source file for each pending item.

### `promote` (Phase 2.2)

Write an extracted item into the appropriate `data/*.yaml` file.

```bash
python -m scripts.kb promote <capture_id>
```

Mapping:

| extracted type | target file |
|---|---|
| `task` | `data/reminders.yaml` |
| `event` | `data/reminders.yaml` |
| `link` | `data/bookmarks.yaml` |
| `project_log` | not yet — Phase 3 / project retrospective |

Double-promote is blocked by default. Use `--force` to override.

Promoted `task`, `event`, and `link` items are dashboard-facing and are written as
`visibility: public`. This is intentional for the public site workflow. Do not promote
items that should stay out of the public repository.

`generated/reviewed.json` is local temporary queue state. Long-term state belongs in
`data/*.yaml`, `content/projects`, or a future private store.

## Daily Workflow

```
1. Write daily note in content/daily/
   ↓
   Use @task / @link / @event / @project markers inline
   ↓
2. python -m scripts.kb extract content/daily/.../today.md
   ↓
   Output: generated/extraction/today.json
   ↓
3. python -m scripts.kb review
   ↓
   Inspect pending items
   ↓
4. python -m scripts.kb promote <capture_id>
   ↓
   Item lands in data/reminders.yaml or data/bookmarks.yaml
   ↓
5. npm run build
   ↓
   Dashboard renders the new data
```

## Relationship to Hugo

- Extraction and validation are **independent of Hugo**. They run as standalone Python.
- `generated/extraction/` is outside Hugo's content tree and is not published.
- `data/*.yaml` files feed Hugo templates (see `layouts/partials/home/`).
- `promote` writes reviewed items into `data/*.yaml`.

## Phase 2.1 vs 2.2 vs 3

| Phase | Scope |
|---|---|
| 2.1 (complete) | `validate` + `extract` explicit markers |
| 2.2 (current) | Review queue rendering + `promote` to data files |
| 2.3 (planned) | Dashboard read-model builder |
| 3 (planned) | Gateway/WeChat capture ingestion |

## Running from Any Directory

The scripts resolve paths relative to the repository root. Use `--root` to override:

```bash
python -m scripts.kb validate --root /path/to/repo
python -m scripts.kb extract daily/2026-7-19.md --root /path/to/repo
```
