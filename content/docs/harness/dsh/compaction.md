---
title: "DSH Compaction：Projection、Spill 与 Durable History"
weight: 7
draft: true
---

> 占位页：区分 truncate tool result、spill oversized result 和 compact conversation，研究压缩如何不破坏可恢复的 Session log。

## 预期区分

```text
truncate tool result
        ≠
spill oversized result
        ≠
compact conversation
```

核心问题：原始 Session log 是否被删除？哪一层被压缩？压缩后的 durable fact 如何继续支持 replay、fork 和 resume？

## 源码入口

```text
packages/compaction/
packages/spill/
Session projection / model history derivation
```

后续正文需要分别追踪 Service Definition、basic Provider 和 command Consumer，而不是把 compaction 简化成“让模型总结旧对话”。
