---
title: "OpenClaw Gateway：从 Channel 到 Agent 的入口"
weight: 2
draft: true
---

> 占位页：追踪一条 Telegram、Discord、WebChat 或其他 Channel 消息如何被 Gateway 认证、规范化、路由成 session，再交给 Agent Runtime。

## 预期主线

```text
Channel ingress
    ↓
Gateway
    ↓
authentication / pairing
    ↓
normalize inbound message
    ↓
binding / routing
    ↓
sessionKey
    ↓
agent RPC
    ↓
streaming events
    ↓
channel delivery
```

## 源码入口

```text
src/gateway/
src/channels/
src/routing/
src/auto-reply/
src/chat/
```

## 待回答的问题

- 为什么 Channel 不直接调用 LLM？
- Gateway 为什么必须长期运行？
- WebSocket、pairing 和 idempotency key 分别解决什么问题？
- Device Node 与普通 Client 为什么共享 Gateway？
