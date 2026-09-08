---
title: "DSH Extensions：Runtime Self-Modification 的边界"
weight: 11
draft: true
---

> 占位页：研究 DSH 如何支持 live plugin/service inspection、model-written mount 和 unmount，并把它与 Skill Learning 和 Model Self-Improvement 区分开。

## 三种概念不要混淆

```text
runtime self-modification
        ≠
long-term skill learning
        ≠
model weight self-improvement
```

这篇重点研究运行期能力树的可观察、挂载、卸载和回滚，而不是把“模型可以写 Plugin”直接等同于 Agent 已经完成自我进化。

## 源码入口

```text
packages/extensions/
Cordis service inspection
plugin / service mount / unmount effects
```
