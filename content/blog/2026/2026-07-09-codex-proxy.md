---
date: 2026-07-09
title: Codex 网络代理配置调整
authors: [bubblevan]
tags: []
---

Codex **不必须**开启 TUN 模式才能运行。出现“正在重新连接”并重试5次，主要是因为网络代理配置没让 Codex 正确走通。

### 为什么会有“正在重新连接”的5次重试？

这5次重试是 Codex 的一种**降级策略**。它默认会优先尝试建立 **WebSocket** 连接，以获得更低的延迟。但如果代理不支持 WebSocket 导致连接失败，它会重试5次（每次约15-20秒），之后才降级到 **HTTPS** 连接。这5次重试过程会拖慢 Codex 的启动。

### 如何配置才能避免？

核心思路是让 Codex 能正确识别并使用代理。

通过 `.env` 文件配置代理是最直接的方法，强制 Codex 使用代理，从而避免它陷入5次重试的循环。

1.  **找到 Codex 的配置目录**：
    *   **Windows**: `C:\Users\<你的用户名>\.codex`
    *   **macOS/Linux**: `~/.codex`
2.  **在目录中新建一个名为 `.env` 的文件**。
3.  **在 `.env` 文件中添加以下内容**（将端口号换成你代理软件的实际端口，如 Clash 通常是 `7890`，V2rayN 通常是 `10809`）：

```env
HTTP_PROXY="http://127.0.0.1:7892"
HTTPS_PROXY="http://127.0.0.1:7892"
ALL_PROXY="socks5://127.0.0.1:7892"
NO_PROXY="localhost,127.0.0.1"
```


4.  **保存文件，并完全退出（不是关闭窗口）并重启 Codex**。

#### 方案二：强制 Codex 使用 HTTPS（禁用 WebSocket）

如果配置代理后仍有重试，可以通过修改配置直接禁用 WebSocket，让 Codex 一开始就使用 HTTPS 连接。

1.  在 Codex 的配置目录（同上）中找到 `config.toml` 文件。
2.  在文件中添加或修改以下内容：

```toml
model_provider = "openai_http"

[model_providers.openai_http]
name = "OpenAI HTTP only"
wire_api = "responses"
requires_openai_auth = true
supports_websockets = false
```


> **注意**：`model_provider = "openai_http"` 需要放在配置文件的最外层。

