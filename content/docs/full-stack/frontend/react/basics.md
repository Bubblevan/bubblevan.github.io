---
id: react-basics
title: 核心概念：组件、JSX 和 State
sidebar_label: 核心概念
---



OK 啊宝鸡们，我们已经拥有了一个可运行的 Vite + React 项目。接下来顺着目录往里走，从项目结构到第一份组件代码，再到 JSX 的来龙去脉，完整理解 React 的基础。

## 入门准备

- 熟悉 `src` 目录结构，搞清入口、组件、样式文件分别在哪。
- 了解 React 函数组件的基本写法与运行流程。
- 理解 JSX 为什么能在 JavaScript 里写出类似 HTML 的结构。

## 项目结构速览

在 `src` 目录下，有几个核心文件：

*   `main.jsx`: 这是应用的入口文件。它使用 `ReactDOM.createRoot()` 来告诉 React 将应用渲染到 `index.html` 中的 `<div id="root"></div>` 元素上。
*   `App.jsx`: 这是我们的第一个 React 组件。它是一个简单的函数，返回了一些 JSX。
*   `index.css` 和 `App.css`: 这些是应用的样式文件。

## 第一个 React 组件：从函数开始

React 的核心思想就是**组件化**。组件是独立的、可复用的代码块，它负责渲染 UI 的一部分。

让我们来修改 `App.jsx`，创建我们自己的第一个组件。

打开 `src/App.jsx` 文件，并将其内容替换为：

```jsx title="src/App.jsx"
function App() {
  return (
    <div>
      <h1>你好，React！</h1>
      <p>这是一个简单的 React 组件。</p>
    </div>
  );
}

export default App;
```

保存文件后，浏览器中的页面会自动更新。

![React 项目预览](/img/react/react2.png)

我们刚刚创建了一个名为 `App` 的**函数式组件**。它返回了一段类似 HTML 的代码，这就是 **JSX**。

## 深入理解 JSX

JSX (JavaScript XML) 是 React 的一个语法扩展，它允许我们在 JavaScript 中编写看起来像 HTML 的代码。这让我们可以将 UI 逻辑和渲染逻辑放在同一个地方，使得代码更加直观和易于维护。

### 1. XML (eXtensible Markup Language - 可扩展标记语言)

**是什么？**
XML 是一种用来**存储和传输数据**的标记语言。它的设计初衷是“让数据能被机器和人同时轻松读懂”。

**核心特点：**
*   **自定义标签**：你可以根据数据结构创建任何你想要的标签，比如 `<student>`, `<name>`, `<score>`。
*   **语法严格**：所有标签都必须闭合，必须有唯一的根元素。这保证了数据结构的严谨性。
*   **纯数据，无表现**：XML 只关心“数据是什么”，不关心“数据长什么样”。它本身不带任何样式。

**生活中的例子：**
想象一下，XML 就像一份非常规范的个人档案表格。

```xml
<person id="007">
  <name>James Bond</name>
  <profession>Secret Agent</profession>
  <skills>
    <skill>Marksmanship</skill>
    <skill>Espionage</skill>
  </skills>
</person>
```
这份“档案”结构清晰，程序可以轻松地解析出姓名、职业等信息。很多应用的配置文件、早期的数据接口（SOAP）都用它。

---

### 2. JSX (JavaScript XML)

**是什么？**
JSX 是 **JavaScript 的一个语法扩展**，它允许您在 JavaScript 代码中编写类似 HTML 的结构。它由 React 推广开来，但现在也被 Vue 等其他框架支持。

**核心特点：**
*   **在 JS 中写 UI**：它让开发者可以用声明式、类似 HTML 的语法来描述用户界面应该长什么样，而不是用繁琐的命令式代码（如 `document.createElement`）去一步步创建。
*   **不是真正的 HTML**：虽然看起来像，但它会被编译器（如 Babel）转换成常规的 JavaScript 函数调用。
*   **强大的 JavaScript 能力**：你可以在 JSX 中无缝地使用 JavaScript 的变量、函数和逻辑（通过 `{}` 包裹）。

**生活中的例子：**
JSX 就像一个“宜家家具的图纸”。

```jsx
// 这不是字符串，也不是 HTML，这是 JSX
const user = "Bubblevan";
const myComponent = (
  <div className="profile">
    <h1>Welcome, {user}!</h1>
    <p>This is your personalized dashboard.</p>
  </div>
);
```
这张“图纸”清晰地描述了一个组件的样子，并且还能动态地把 `{user}` 这个变量“组装”进去。最终，React 这个“工匠”会根据这张图纸，把它变成浏览器里真正的网页元素。

---

### 3. MDX (Markdown for the Component Era)

**是什么？**
MDX 是 **Markdown 的超集**。它允许您在写 Markdown 文档的同时，无缝地**导入和使用 JSX 组件**。

**核心特点：**
*   **Markdown + JSX**：您可以像往常一样用 `#` 写标题，用 `*` 写列表，但同时，您可以像写 React 代码一样，直接在文档里插入一个交互式图表、一个视频播放器或者任何您创建的组件。
*   **内容与交互的融合**：它打破了静态内容（文章）和动态应用（组件）之间的墙。

本站（Docusaurus）正是一个大量使用 MDX 的例子：
```mdx
---
title: My Awesome Document
---

import { Chart } from '@site/src/components/Chart';
import { VideoPlayer } from '@site/src/components/VideoPlayer';

# 我的神奇文档

这是一段普通的 Markdown 文本。

我们甚至可以直接在这里插入一个动态图表：

<Chart data={[10, 40, 25, 60]} />

甚至可以放一个视频播放器：

<VideoPlayer url="https://example.com/my-video.mp4" />

---
```

| 特性 | XML | JSX | MDX |
| --- | --- | --- | --- |
| **核心用途** | 结构化数据 | 在 JS 中描述 UI | 交互式文档 |
| **本质** | 标记语言 | JS 的语法扩展 | Markdown 的超集 |
| **运行环境** | 任何能解析 XML 的程序 | JavaScript（需编译） | Markdown 解析器 + JS 框架（需编译） |
| **好比** | 数据的蓝图 | UI 的蓝图 | 文章的蓝图 |

虽然 JSX 看起来很像 HTML，但它实际上是 JavaScript。在编译时，Babel 会将 JSX 转换为 `React.createElement()` 的调用。

## 让组件拥有状态

静态的组件是不够的。在实际应用中，我们需要处理用户的交互，并根据数据的变化来更新 UI。这就是 **State** 的用武之地。

State 是组件内部私有的数据。当 State 发生变化时，React 会自动重新渲染组件，以反映最新的数据。

让我们来创建一个计数器组件来理解 State。

在 `src` 目录下创建一个新文件 `Counter.jsx`，并添加以下代码：

```jsx title="src/components/Counter.jsx"
import React, { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <p>你点击了 {count} 次</p>
      <button onClick={() => setCount(count + 1)}>
        点我
      </button>
    </div>
  );
}

export default Counter;
```

这里我们用到了 `useState`，这是 React 提供的一个 **Hook**。

> Hook 顾名思义就是钩子函数，把它理解成用你的钩子去转一个组件里面的密码锁齿轮，让这个齿轮的 State 变换，就像 Java 里面一个类单独暴露出一个 setValue 方法来一样

Hook 让你可以在函数式组件中使用 React 的特性，比如 State。

*   `useState(0)` 初始化了一个名为 `count` 的 state 变量，其初始值为 `0`。
*   `useState` 返回一个数组，包含两个元素：当前的 state 值 (`count`) 和一个更新该 state 的函数 (`setCount`)。
*   当我们点击按钮时，`onClick` 事件会触发，调用 `setCount(count + 1)`。这会更新 `count` 的值，并告诉 React 重新渲染 `Counter` 组件。

现在，让我们在 `App.jsx` 中使用这个新组件。

```jsx title="src/App.jsx"
import Counter from './components/Counter';

function App() {
  return (
    <div>
      <h1>你好，React！</h1>
      <p>这是一个简单的 React 组件。</p>
      <hr />
      <h2>这是一个计数器：</h2>
      <Counter />
    </div>
  );
}

export default App;
```

![React 计数器示例](/img/react/react3.png)

现在，你可以在页面上点击按钮，看到数字不断增加。这就是 React 响应式更新！

让我们小结一下：

- 组件是 React 的最小单位，函数返回 JSX 就能定义界面。
- JSX 只是语法糖，最终都会被编译成 `React.createElement`。
- `useState` 让组件拥有内部状态，配合事件即可响应用户交互。
