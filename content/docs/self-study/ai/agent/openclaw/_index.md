## OpenClaw

- [一文读懂：openClaw 分析与教程+免费大模型（Moltbot、Clawdbot） 二更](https://zhuanlan.zhihu.com/p/2000850539936765122)
- [从零开始玩转OpenClaw：最全面的中文教程，涵盖安装、配置、实战案例和避坑指南（github版）](https://github.com/pudge0313/openclaw-)
- [类Clawhub The Open Agent Skills Ecosystem](https://skills.sh/)

## Windows 安装
有一说一我不是很想在Windows上装，之前在WSL里装好了，现在因为要开发插件了，所以重新开始吧：
```powershell
nvm install 22
nvm use 22
npm install -g openclaw
```

## 插件开发
```powershell
(base) PS D:\MyLab\StablePay\stablepay-openclaw-plugin>  openclaw plugins install -l ./stablepay-openclaw-plugin

🦞 OpenClaw 2026.3.23-2 (7ffe7e4) — Give me a workspace and I'll give you fewer tabs, fewer toggles, and more oxygen.

`--link` requires a local path.

(base) PS D:\MyLab\StablePay\stablepay-openclaw-plugin>  openclaw plugins enable stablepay-mock-plugin

🦞 OpenClaw 2026.3.23-2 (7ffe7e4) — Alexa, but with taste.

Config warnings:
- plugins.entries.stablepay-mock-plugin: plugin not found: stablepay-mock-plugin (stale config entry ignored; remove it from plugins config)
Enabled plugin "stablepay-mock-plugin". Restart the gateway to apply.
```
下一步是
```
  # 配置（在 OpenClaw 配置里加入 backendBaseUrl 等）
  openclaw plugins doctor
```
