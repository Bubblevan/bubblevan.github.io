---
title: "React"
weight: 2
---

作为如今前端两大著名框架之一，React 最吸引人的地方，在于它把 UI 看作状态的函数。我们只需要描述"在某个状态下界面长什么样"，其余的更新、渲染、协调工作都交给 React 背后的虚拟 DOM 与 Fiber 架构处理。

> BTW 它最烦的一点在于版本更新 Page Router 还有 APP Router 不一样，当初在那个 chatgpt 还不存在的时候看英文博客差点给我看似了。

## 入门准备

在正式深入学习之前，先搭建好开发环境并熟悉基础工具。

### 环境要求

- [Node.js](https://nodejs.org/) ≥ 14.0.0  
- 包管理器：npm / Yarn / pnpm（任选其一）

我们将使用 [Vite](https://vitejs.dev/) 来快速搭建 React 项目，它提供极速的开发体验。

### 创建第一个 React 项目

打开终端执行：

```bash
npm create vite@latest my-react-app -- --template react
```

进入项目目录并安装依赖：

```bash
cd my-react-app
npm install
```

安装完成后，你的项目结构应该如下所示：

```
my-react-app/
├── node_modules/
├── public/
│   └── vite.svg
├── src/
│   ├── App.css
│   ├── App.jsx
│   ├── index.css
│   ├── main.jsx
│   └── assets/
│       └── react.svg
├── .gitignore
├── index.html
├── package.json
└── vite.config.js
```

现在，让我们启动开发服务器：

```bash
npm run dev
```

Vite 将会启动一个本地开发服务器，你可以在浏览器中打开 `http://localhost:5173` (端口号可能会不同) 来查看你的应用。

## 学习路线导航

下面的文档按照"入门 → 进阶 → 状态管理 → 实战复用"的顺序排列，可按章节顺序阅读，也可以根据需求跳读。

### React 入门与核心概念

- [React 基础](./basics)

### 组件进阶与状态提升

- [React 进阶](./advanced)

### 状态管理选型指南

- [状态管理](./state-management)

### 实战组件与项目案例

- [实战项目](./projects)

## 延伸资源

### 官方文档

- [React 官方文档](https://react.dev/)
- [React 中文文档](https://zh-hans.react.dev/)

### 在线课程

（待补充）

### 实践项目

- GitHub 上的开源项目、个人作品集网站、企业管理系统……
