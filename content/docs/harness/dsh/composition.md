---
title: "DSH Composition：Cordis、Profile、Bundle 与 Effect"
weight: 4
draft: true
---

> 占位页：研究 DSH 如何从空 Plugin Tree 启动，通过 Profile、Bundle、Patch 和 Effect 组合出可运行 Harness。

## 预期主线

```text
empty plugin tree
      ↓
profile bundle
      ↓
profile cordis.patch.yml
      ↓
home-level patch
      ↓
--patch overlay
      ↓
running Cordis tree
```

重点比较 `web`、`headless`、`sdk`、`sdk-minimal` 和 `acp` profiles，并用 `dsh --profile web --dump-config` 观察实际启动的 Plugin Tree。

## 待回答的问题

- 为什么 DSH 不在中央 Runtime 中 import 所有能力？
- 如何替换 LLM、FS、Subprocess、Sandbox 或 Agent Loop？
- Plugin 卸载时 registration effect 如何反向撤销？

## 源码入口

```text
packages/core/
packages/bundle/
packages/profile/
packages/preset/
Cordis / patch / effect runtime
```
