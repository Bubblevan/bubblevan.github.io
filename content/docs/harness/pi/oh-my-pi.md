---
title: "从 Pi 到 Oh My Pi：Minimal Harness 的压力测试"
weight: 11
draft: true
---

> 占位页：把 Oh My Pi 作为 Pi 的 fork 和对照实验，研究一个 minimal coding harness 为什么会加入 IDE、调试器、持久化运行时和更强的 delegation。

## 预期比较

```text
Pi loop
    + LSP
    + DAP
    + persistent Python / Bun
    + Rust native tooling
    + subagents / advisor
    + memory / web / ACP
    ↓
IDE-aware coding harness
```

## 待回答的问题

- LSP 是一个额外 Tool，还是改变了 edit pipeline？
- 为什么 high-frequency tool 值得移入 native process？
- persistent REPL 相比每次 shell fork 改变了什么？
- typed subagent result 与 prose result 有什么取舍？

## 参考入口

- [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi)
