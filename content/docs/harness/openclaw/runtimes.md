---
title: "OpenClaw Runtimes：谁真正拥有 Agent Loop？"
weight: 4
draft: true
---

> 占位页：建立 OpenClaw、Codex、Pi、Hermes 等系统的 Runtime ownership 比较坐标系。

## 预期比较维度

```text
Who owns model loop?
Who owns thread history?
Who owns tool execution?
Who owns compaction?
Who owns context assembly?
Who owns delivery?
```

## 初始比较表

| 责任 | OpenClaw native runtime | Codex app-server 作为嵌入 Runtime |
| --- | --- | --- |
| model loop | OpenClaw | Codex |
| thread state | OpenClaw transcript | Codex thread + mirror |
| dynamic tools | OpenClaw native | bridged |
| native tools | OpenClaw | Codex native |
| context | OpenClaw | projected into Codex |
| compaction | OpenClaw / context engine | Codex native |
| delivery | OpenClaw | OpenClaw |

后续正文需要用实际源码和事件流核实，而不是把这张表当作不变的产品事实。
