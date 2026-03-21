---
date: 2026-03-10
title: 远程服务器配置代理与codex
authors: [bubblevan]
tags: []
---

配置代理有两种方式，一种是直接在远程服务器上安装`mihomo-linux-amd64-v1.19.20.gz`，然后将自己的代理文件`yaml`给粘贴到对应的地方去；另一种是设置端口转发——而只有后者才能成功登陆codex。

## mihomo 远程服务器代理
mihomo类似很多Clash的内核，可以自行在Github仓库去找对应的`release`：

```bash
gunzip mihomo-linux-amd64-v1.19.20.gz
mv mihomo-linux-amd64-v1.19.20 mihomo
chmod +x mihomo
sudo mv mihomo /usr/local/bin/
mihomo
# 这个时候配置文件会生成在/root/.config/mihomo/config.yaml
# 在这里导入代理文件即可
# 查看当前是否设置了代理
git config --global --get http.proxy
git config --global --get https.proxy

# 如果发现有代理设置，且你当前不需要使用代理，可以先取消它
git config --global --unset http.proxy
git config --global --unset https.proxy
# unset http_proxy https_proxy
```

## Cursor/VSCode Remote SSH 端口转发
| 用途           | VS Code              | Cursor                    |
|----------------|------------------------------------|--------------------------------------|
| 远程端配置目录 | `~/.vscode-server/data/Machine/`  | `~/.cursor-server/data/Machine/`     |
| 远程端配置文件 | `~/.vscode-server/data/Machine/settings.json` | `~/.cursor-server/data/Machine/settings.json` |

### 1. 本机：SSH 端口转发

编辑本机 `~/.ssh/config`：

```
Host 你的服务器名
    HostName 服务器IP或域名
    User 你的用户名
    Port 22
    RemoteForward 1082 127.0.0.1:7890
```

- `1082`：远程机上看到的端口（可自选，如 1082）。
- `7890`：本机代理端口（Clash/V2Ray 等实际监听的端口）。

这样远程上的 `127.0.0.1:1082` 会连到你本机的代理。

### 2. 远程：创建 Cursor 代理配置

SSH 登录到远程服务器后：

```bash
# 路径用 Cursor 的，不是 .vscode-server
vi ~/.cursor-server/data/Machine/settings.json
```

若文件不存在，就新建，内容示例（端口和上面 RemoteForward 第一个端口一致）：

```json
{
  "http.proxy": "http://127.0.0.1:1082",
  "http.proxySupport": "override",
  "http.proxyStrictSSL": false
}
```

保存后，**断开 Cursor 的 Remote SSH，再重新连一次**，让 Cursor 读到新配置。

### 3. 验证

在**远程**上：

```bash
# 看端口是否在监听（1082 换成你设的远程端口）
ss -tuln | grep 1082

# 测代理是否通（端口同上）
curl -x http://127.0.0.1:1082 https://www.google.com
```
现在可以开始使用codex了，如果`operation timed out`就多试几次。
