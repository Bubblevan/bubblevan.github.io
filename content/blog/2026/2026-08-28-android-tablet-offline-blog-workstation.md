---
schema: bubblevan/v1
id: blog-20260828-android-tablet-offline-blog-workstation
content_kind: blog
title: 把安卓平板变成离线博客工作站：Termux + code-server + Git
date: 2026-08-28
updated: 2026-08-28
status: draft
visibility: public
summary: 为了解决火车上网络不稳定却又想继续维护 Hugo 博客的问题，我最终把 Termux 当作本地 Linux 后端，用 code-server 提供 VS Code GUI，再用 Git 完成真正离线的编辑与提交。
topics: [Android, Termux, code-server, VS Code, Git, Hugo, Blog]
projects: [bubblevan.github.io]
aliases: []
authors: [bubblevan]
---

我一直有一个很具体、也很朴素的需求：

**坐火车的时候继续写自己的 Hugo 博客。**

问题在于，我在平板上最常用博客的场景，恰恰不是坐在一个 Wi-Fi 稳定的咖啡馆里，而是在高铁、普速列车或者各种移动网络时好时坏的地方。`github.dev` 看上去几乎完美：浏览器里直接就是 VS Code，可以改 Markdown，也可以看 Git diff。但它终究还是围绕 GitHub 在线仓库工作的。

而我真正想要的是：

- 整个 `Bubblevan/bubblevan.github.io` 仓库完整地躺在平板本地；
- 没网的时候照样能搜索、浏览和编辑；
- 不需要逼自己学习 Vim / Neovim；
- 能像桌面 VS Code 一样看 Explorer、diff、Source Control；
- 没网时可以正常 `commit`；
- 等网络恢复以后再 `push`；
- 最好之后还能在平板本地跑 `hugo server` 预览博客。

最后得到的方案非常简单：

```text
Android Tablet
├── Termux
│   ├── Git
│   ├── OpenSSH
│   ├── code-server
│   ├── Hugo（可选）
│   └── ~/projects/bubblevan.github.io
│
└── Browser
    ├── 127.0.0.1:8080 → VS Code
    └── 127.0.0.1:1313 → Hugo Preview（后续）
```

真正改变体验的一点是：

> **Termux 不需要成为我的编辑器。它只需要成为平板里的 Linux 后端。**

我依然可以当一个正常的 GUI 用户。

---

## 1. 为什么没有直接用 github.dev

如果网络稳定，`github.dev` 确实是一个非常舒服的方案。

把：

```text
github.com/Bubblevan/bubblevan.github.io
```

改成：

```text
github.dev/Bubblevan/bubblevan.github.io
```

就能直接进入一个 VS Code 风格的 Web 编辑器。

但我的核心场景是：

```text
火车
↓
网络时好时坏
↓
甚至长时间完全离线
```

这时候我不希望每次打开文件、切换目录甚至恢复编辑状态，都要担心远端连接。

因此我最后把两者的定位分开：

- `github.dev`：有网时临时改两笔；
- Termux + code-server：真正的离线工作站。

---

## 2. 打开平板以后，我发现自己以前显然折腾过不少东西

本来只是想装个 VS Code。

结果打开平板以后，我发现里面已经有：

- Termux；
- Termux:X11；
- Wine；
- ExaGear ED302。

这很像一次数字考古。

以前的我显然尝试过在 Android 上运行更完整的 Linux / Windows 环境，但这次认真想了一遍之后发现，为了写博客完全没有必要走那么重的路线。

这些东西在这次任务里的定位大概是：

| 工具 | 它解决什么问题 | 这次是否需要 |
| --- | --- | --- |
| Termux | Android 上的 Linux 用户空间 | 需要 |
| Termux:X11 | 显示 Linux GUI 程序 | 暂时不需要 |
| Wine | 运行 Windows 程序兼容层 | 不需要 |
| ExaGear | 兼容 / 翻译旧 Windows/x86 软件环境 | 不需要 |
| code-server | 浏览器里的 VS Code | 核心 |
| Git | 本地版本控制 | 核心 |
| Hugo | 本地博客预览 | 后续可选 |

最后真正需要的其实只有：

```text
Termux
+
Git
+
code-server
+
浏览器
```

并不需要为了“得到一个 VS Code 界面”，真的在 Android 里再套一整个桌面系统。

---

## 3. 最关键的认知：Termux 不是我的编辑器

我以前对 Termux 最大的不适感来自于：

> 它看起来就是一个黑色 CLI 窗口。

这会自然让人联想到：

```text
vim xxx.md
git status
git add .
git commit
```

然后仿佛下一步就应该开始背 Vim 键位。

但这其实完全没有必要。

我最后采用的是：

```text
Termux
   ↓
code-server
   ↓
127.0.0.1:8080
   ↓
Chrome / Edge
   ↓
VS Code GUI
```

Termux 负责：

- Linux 用户空间；
- Git；
- SSH；
- Node；
- code-server；
- Hugo。

浏览器负责：

- Explorer；
- Markdown 编辑；
- 全局搜索；
- Source Control；
- Git diff；
- commit；
- 文件管理。

这一下体验就从“在手机上硬用 Linux CLI”变成了：

> **平板本地跑了一个 VS Code 后端，而浏览器只是它的显示器。**

---

## 4. 安装 Git 和 OpenSSH

首先更新 Termux：

```bash
pkg update
pkg upgrade
```

然后安装：

```bash
pkg install git openssh
```

安装完成以后，我看到了 OpenSSH 自动生成的一堆 key：

![Termux 安装 Git 和 OpenSSH](/blog/2026/termux-git-openssh.webp)

当时很容易产生一个误解：

> “不是已经有 SSH key 了吗？”

实际上，这些：

```text
ssh_host_rsa_key
ssh_host_ecdsa_key
ssh_host_ed25519_key
```

是 **SSH host key**。

它们用于 Termux 自己作为 SSH Server 时证明：

> “我是这台机器。”

而 GitHub 登录需要的是另一套 **用户身份 key**。

这两者不能混在一起。

---

## 5. SSH host key 和 GitHub authentication key 不是一回事

GitHub 真正需要的是：

```text
~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub
```

生成方式：

```bash
ssh-keygen -t ed25519 -C "your@email.com"
```

这里我还非常自然地打错了一次命令：

```bash
ssh-key -t ed25519 ...
```

然后 Termux 非常诚实地告诉我：

```text
No command ssh-key found
```

正确命令是：

```text
ssh-keygen
```

生成过程中一路按回车即可。

如果不想每次 Git 操作都输入 SSH key 的 passphrase，也可以暂时不给 key 设置额外密码。

完成以后：

```bash
ls -l ~/.ssh/
```

应该能看到：

```text
id_ed25519
id_ed25519.pub
```

其中：

```text
id_ed25519
```

是私钥。

**绝对不要上传给任何人。**

而：

```text
id_ed25519.pub
```

才是可以交给 GitHub 的公钥。

---

## 6. GitHub 为什么说 `Key is invalid`

第一次生成 key 后，终端会显示：

```text
The key fingerprint is:
SHA256:xxxxxxxxxxxxxxxx

The key's randomart image is:

+--[ED25519 256]--+
| ...             |
| ...             |
+----[SHA256]-----+
```

我一开始把这里的 fingerprint 当成了公钥。

于是 GitHub 报：

```text
Key is invalid.
You must supply a key in OpenSSH public key format.
```

这里真正需要复制的是：

```bash
cat ~/.ssh/id_ed25519.pub
```

输出应该是一整行：

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... your@email.com
```

GitHub 要的就是：

```text
ssh-ed25519
+
公钥正文
+
comment/email
```

而不是：

```text
SHA256:xxxxxx
```

更不是下面那张 randomart。

配置完成后可以测试：

```bash
ssh -T git@github.com
```

如果出现：

```text
Hi Bubblevan! You've successfully authenticated, but GitHub does not provide shell access.
```

就说明 SSH 已经配置成功。

---

## 7. 安装 code-server

接下来安装 code-server：

```bash
pkg install tur-repo
pkg install code-server
```

理论上，到这里运行：

```bash
code-server
```

就应该结束。

事情当然没有这么顺利。

---

## 8. 第一个真正的大坑：`EVP_MD_CTX_get_size_ex`

第一次启动 code-server 时，我得到了：

![code-server 启动时的 OpenSSL / Node 动态链接错误](/blog/2026/code-server-openssl-node.webp)

关键错误是：

```text
CANNOT LINK EXECUTABLE
...
cannot locate symbol "EVP_MD_CTX_get_size_ex"
```

一开始看起来很像：

> “缺了一个 `.so` 文件？”

但实际问题不是简单缺动态库，而是 **Node.js 和 Termux 当前 OpenSSL 环境发生了 ABI / symbol mismatch**。

可以粗略理解为：

```text
code-server
    ↓
Node.js
    ↓
需要某个 OpenSSL symbol
    ↓
当前 Termux 里的 libcrypto / OpenSSL
    ↓
版本没有对齐
```

截图里还有一个非常关键的信息：

```text
204 not upgraded
```

也就是说，我的 Termux 是一个已经放了很久、又装过很多东西的环境。

一部分包比较新：

```text
code-server
Node.js
```

另一部分底层依赖却还停留在旧版本。

Termux 本身又比较偏 rolling release，这种“半升级”状态很容易制造 ABI mismatch。

---

## 9. 修复方式不是乱塞 `.so`，而是让包版本重新一致

遇到这种错误，网上很容易搜到一些很刺激的操作：

```bash
export LD_LIBRARY_PATH=...
```

或者手工去下载：

```text
libssl.so
libcrypto.so
```

然后扔进某个目录。

我没有这么做。

这类做法很容易变成：

```text
今天修一个 symbol
↓
明天炸另一个 symbol
↓
后天开始怀疑人生
```

更合理的方式是先把 Termux package set 恢复到相对一致的状态。

首先：

```bash
termux-change-repo
```

选择一个正常可用的 Main repository。

然后完整更新：

```bash
pkg update
pkg upgrade
```

如果仍然需要，可以重装关键依赖：

```bash
pkg reinstall openssl
pkg reinstall nodejs-24
```

再检查 Node：

```bash
/data/data/com.termux/files/usr/opt/nodejs-24/bin/node --version
```

确认 Node 自己能正常运行后，再：

```bash
code-server
```

这一次终于成功。

---

## 10. code-server 真正启动了

启动成功以后，终端会显示：

![code-server 成功监听本地 8080 端口](/blog/2026/code-server-8080.webp)

核心信息是：

```text
HTTP server listening on http://127.0.0.1:8080/
Authentication is enabled
Using password from ~/.config/code-server/config.yaml
```

中间还有类似：

```text
Unable to retrieve mac address
Unsupported platform
```

的提示。

但后面扩展 host 仍然正常启动，所以对当前使用场景并不是致命问题。

真正重要的是：

```text
127.0.0.1:8080
```

已经开始监听。

---

## 11. 为什么 `127.0.0.1` 可以完全离线

这是整套方案里我最喜欢的一点。

浏览器访问：

```text
http://127.0.0.1:8080
```

并不是访问互联网。

`127.0.0.1` 是 loopback，也就是：

> **这台平板访问自己。**

因此即使：

- 开飞行模式；
- 没有 SIM；
- 没有 Wi-Fi；
- 火车钻进隧道；
- 山区完全没信号；

浏览器和 code-server 之间仍然可以正常通信。

也就是说：

```text
Chrome
   ↓
127.0.0.1
   ↓
Termux 中的 code-server
```

这一整条链路都发生在平板内部。

---

## 12. code-server 密码在哪里

第一次打开：

```text
http://127.0.0.1:8080
```

会要求输入密码。

密码保存在：

```text
~/.config/code-server/config.yaml
```

可以直接：

```bash
cat ~/.config/code-server/config.yaml
```

看到类似：

```yaml
bind-addr: 127.0.0.1:8080
auth: password
password: xxxxxxxxxxxxxxxxx
cert: false
```

如果只是平板自己使用，也可以考虑：

```yaml
auth: none
```

但前提是继续保持：

```yaml
bind-addr: 127.0.0.1:8080
```

不要一边：

```yaml
bind-addr: 0.0.0.0:8080
```

一边：

```yaml
auth: none
```

否则就有可能把没有认证的 code-server 暴露到局域网。

---

## 13. 终于在 Android 上看到了 VS Code

然后在浏览器中打开：

```text
http://127.0.0.1:8080
```

终于出现了：

![Android 浏览器中的 code-server / VS Code UI](/blog/2026/android-code-server-vs-code-ui.webp)

这就是我真正想要的东西。

左边还是熟悉的：

- Explorer；
- Search；
- Source Control；
- Extensions。

中间还是 VS Code 编辑器。

也就是说，从这一步开始，我已经不需要在 Termux 里编辑 Markdown 了。

Termux 只需要默默躺在后台。

---

## 14. Git 仓库不要放 `/sdcard`

下一步是在 Termux 内建立自己的项目目录：

```bash
mkdir -p ~/projects
cd ~/projects
```

这里有一个很重要的原则：

**Git 主仓库不要直接放 Android shared storage。**

也就是不要把它放到：

```text
/sdcard/
/storage/emulated/0/Documents/
```

而应该放到 Termux 自己的 home：

```text
/data/data/com.termux/files/home/projects/
```

也就是：

```text
~/projects/
```

因此我的博客最终会在：

```text
~/projects/bubblevan.github.io
```

这样 Git、权限、symlink 等行为都会更接近正常 Linux 文件系统。

---

## 15. Clone 我的 Hugo 博客

SSH 配置完成以后：

```bash
cd ~/projects
```

然后：

```bash
git clone git@github.com:Bubblevan/bubblevan.github.io.git
```

完成后：

```bash
cd ~/projects/bubblevan.github.io
git status
```

正常会看到：

```text
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

然后回到 code-server：

```text
Open Folder
```

打开：

```text
/data/data/com.termux/files/home/projects/bubblevan.github.io
```

从此以后，左侧 Explorer 看到的就是完整的 Hugo 博客仓库。

---

## 16. 从这里开始，我终于可以完全不碰 CLI 写博客

以后在平板里的日常操作大概是：

```text
Explorer
↓
content/
↓
blog/
↓
2026/
↓
xxx.md
```

然后直接写 Markdown。

Git 操作也可以在左侧：

```text
Source Control
```

完成。

修改以后可以直接看：

```text
Changes
```

点开文件就是熟悉的 diff。

然后：

```text
Stage
↓
填写 commit message
↓
Commit
```

这里有一个特别重要的事实：

> **Git commit 不需要网络。**

很多时候我们把 Git 和 GitHub 用得太紧密，会下意识觉得：

```text
commit = 上传
```

其实不是。

---

## 17. Git 为什么天然适合这种离线工作流

Git 本质上是 distributed version control system。

本地仓库本身就保存：

- commit；
- history；
- branch；
- diff；
- HEAD；
- object database。

GitHub 只是一个 remote。

所以：

```text
commit ≠ upload
push = upload
```

这意味着我完全可以：

```text
GitHub 上的 A
    ↓ pull

本地 A

──── 进入火车，无网络 ────

A
↑
B  完善文章
↑
C  补截图
↑
D  修 typo

──── 到站，恢复网络 ────

git push

GitHub:
A → B → C → D
```

整个 B、C、D 的创建过程都不需要 GitHub 在线。

---

## 18. 我的火车写博客工作流

最终我想要的工作流其实非常简单。

### 出发前

有网络的时候：

```bash
cd ~/projects/bubblevan.github.io
git pull
```

确保平板上的仓库已经是最新版本。

### 火车上

打开 Termux：

```bash
code-server ~/projects/bubblevan.github.io
```

然后浏览器打开：

```text
http://127.0.0.1:8080
```

此后完全可以断网。

继续：

```text
编辑 Markdown
↓
看 diff
↓
commit
↓
继续编辑
↓
再 commit
```

### 到站以后

网络恢复：

```bash
git push
```

或者直接在 VS Code 的 Source Control 里：

```text
Sync Changes
```

完成同步。

---

## 19. 下一步：Hugo 本地 Preview

现在 code-server + Git 已经解决了：

> **离线编辑。**

下一步还可以继续解决：

> **离线看最终网页效果。**

如果 Termux 环境能够安装 Hugo：

```bash
pkg install hugo
```

然后：

```bash
cd ~/projects/bubblevan.github.io
hugo server
```

一般会监听：

```text
http://127.0.0.1:1313
```

于是浏览器可以同时开两个 Tab：

```text
Tab 1
127.0.0.1:8080
→ VS Code

Tab 2
127.0.0.1:1313
→ Hugo Preview
```

最终体验就是：

```text
写 Markdown
↓
切另一个 Tab
↓
看博客实际页面
```

这一套依然可以完全离线。

---

## 20. 再下一步：让 Termux 这个黑框彻底消失

现在每天仍然需要先打开 Termux：

```bash
code-server ~/projects/bubblevan.github.io
```

但理论上还可以继续自动化。

例如以后可以考虑：

- Termux:Widget；
- shell startup script；
- Android Shortcut；
- 自动打开浏览器；
- 自动进入项目目录。

最终目标可以变成：

```text
Android 桌面
↓
点击「Bubblevan Dev」
↓
启动 code-server
↓
打开 127.0.0.1:8080
↓
直接进入博客仓库
```

到那时，Termux 就真正退化成一个隐藏在后台的 runtime。

---

## 21. Wine、Termux:X11 和 ExaGear 最后都没有用上

回过头看非常有意思。

我平板里原本已经有：

```text
Termux:X11
Wine
ExaGear
```

如果按照以前的思路，很容易一路变成：

```text
Android
↓
Linux Desktop / Wine
↓
Windows / Linux GUI
↓
VS Code
```

但这次最终采用的是：

```text
Android
↓
Termux
↓
code-server
↓
Browser
```

少了很多中间层。

我并不是真的需要“在 Android 上跑桌面版 VS Code.exe”。

我真正需要的是：

> **VS Code 的交互界面 + 一个可靠的本地 Linux/Git runtime。**

code-server 刚好把两者拆开了。

---

## 22. 踩坑速查

| 问题 | 原因 | 正确处理 |
| --- | --- | --- |
| `ssh-key: command not found` | 命令写错 | 用 `ssh-keygen` |
| 安装 OpenSSH 已经有 key，为什么还要生成？ | `ssh_host_*` 是 host key | 另外生成 `~/.ssh/id_ed25519` |
| GitHub `Key is invalid` | 复制了 SHA256 fingerprint | `cat ~/.ssh/id_ed25519.pub` |
| `EVP_MD_CTX_get_size_ex` | Node / OpenSSL 版本不一致 | `pkg update && pkg upgrade`，必要时重装依赖 |
| `Unsupported platform` | Android/Termux 某些平台 API 不受支持 | 若 server 后续正常启动，可先观察 |
| `127.0.0.1` 需要网络吗？ | 不需要，它是本机 loopback | 飞行模式也可以访问 |
| repo 能不能放 `/sdcard` | 不推荐 | 放 `~/projects` |
| `git commit` 需要联网吗 | 不需要 | 只有 pull / push 需要远端 |
| Termux 是不是必须配 Vim | 完全不是 | Termux 只做后端，code-server 做 GUI |

---

## 23. 总结

最后的方案其实比一开始想象得简单：

```text
Termux = 本地 Linux 后端
code-server = VS Code
Browser = GUI
Git = 离线版本控制
GitHub = 有网时同步
Hugo = 本地博客 Preview
```

我最开始对 Termux 的抗拒，很大一部分来自于把：

```text
Termux
```

和：

```text
CLI 编辑器
```

绑定在了一起。

但两者其实完全没有必然关系。

对于我这种只是想在火车上维护 Hugo 博客、又不想成为 Vim 高手的人来说，最舒服的方式反而是：

> **让 Termux 负责它擅长的 Linux runtime，把编辑体验完整交给 VS Code GUI。**

这样当火车进入隧道、移动网络彻底消失时，我仍然拥有：

- 完整仓库；
- 完整 Markdown；
- 搜索；
- diff；
- Git history；
- commit；
- 本地预览的可能性。

等重新有网以后，再把这些变化一次性 push 回 GitHub。

这才是我真正想要的“移动开发环境”。
