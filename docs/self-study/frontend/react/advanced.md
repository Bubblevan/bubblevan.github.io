---
id: react-advanced
title: 组件交互与数据传递
sidebar_label: 组件交互
---

import BrowserWindow from '@site/src/components/BrowserWindow';
import CollapsibleBlock from '@site/src/components/CollapsibleBlock';

现在，让我们把组件之间的互动、数据流转、渲染策略梳理得更系统：先解决通讯，再掌握列表与 key，最后处理跨组件共享和副作用。

## 组件之间的通讯

### 使用 Props 传递数据

**Props**（properties 的缩写）是从父组件传递给子组件的数据。这让我们的组件更加灵活和可复用。

让我们来创建一个 `Greeting` 组件，它接收一个 `name` prop 并显示一条问候消息：

```jsx title="src/components/Greeting.jsx"
function Greeting(props) {
  return <h1>你好, {props.name}！</h1>;
}

export default Greeting;
```

现在，我们可以在 `App.jsx` 中使用这个组件，并传递一个 `name` prop 给它：

```jsx title="src/App.jsx"
import Greeting from './components/Greeting';

function App() {
  return (
    <div>
      <Greeting name="张三" />
      <Greeting name="李四" />
    </div>
  );
}

export default App;
```

<BrowserWindow url="http://localhost:5173">
  <div>
    <img src={require('@site/static/img/react/react4.png').default} alt="React 组件传递" />
  </div>
</BrowserWindow>

Props 是只读的，一个组件永远不能修改它自己的 props，只能根据传入的值去表现。

### 条件渲染

应用中经常需要根据不同条件显示或隐藏某些内容。React 提供了多种写法来实现**条件渲染**。

最直接的方式是使用 `if` 语句：

```jsx
function UserGreeting() {
  return <h1>欢迎回来！</h1>;
}

function GuestGreeting() {
  return <h1>请先登录。</h1>;
}

function Greeting(props) {
  const isLoggedIn = props.isLoggedIn;
  if (isLoggedIn) {
    return <UserGreeting />;
  }
  return <GuestGreeting />;
}
```

对于更简单的条件，可以使用三元运算符：

```jsx
function Greeting(props) {
  const isLoggedIn = props.isLoggedIn;
  return (
    <div>
      {isLoggedIn
        ? <UserGreeting />
        : <GuestGreeting />
      }
    </div>
  );
}
```

#### 使用逻辑与 `&&` 运算符

如果条件为 `true`，`&&` 右侧的 JSX 会被渲染，否则直接跳过：

```jsx
function Mailbox(props) {
  const unreadMessages = props.unreadMessages;
  return (
    <div>
      <h1>你好！</h1>
      {unreadMessages.length > 0 &&
        <h2>
          你有 {unreadMessages.length} 条未读消息。
        </h2>
      }
    </div>
  );
}
```

## 列表渲染与 Keys

### 使用 `map` 渲染列表

可以利用 JavaScript 的 `map()` 方法把数组转换成一组元素：

```jsx
const numbers = [1, 2, 3, 4, 5];
const listItems = numbers.map((number) =>
  <li>{number}</li>
);

ReactDOM.render(
  <ul>{listItems}</ul>,
  document.getElementById('root')
);
```

<CollapsibleBlock title="箭头函数 =>？" defaultExpanded={false}>
 详细说明可参考《[JavaScript：箭头函数与 this](/docs/self-study/frontend/javascript#箭头函数-与-this)》。
</CollapsibleBlock>
### 维护稳定的 Key

**Keys** 帮助 React 识别哪些元素被改变、添加或删除，应该稳定且唯一：

```jsx
const todoItems = todos.map((todo) =>
  <li key={todo.id}>
    {todo.text}
  </li>
);
```

Key 只需要在兄弟节点之间保持唯一，不必全局唯一。稳定的 key 是构建复杂交互界面的基础。

## 状态提升与共享数据

当多个组件需要共享同一份状态时，可以将 state 提升到它们最近的共同父组件，再通过 props 将数据和回调下发。

```jsx title="src/components/TemperatureConverter.jsx"
import { useState } from 'react';

function TemperatureInput({ label, value, onChange }) {
  return (
    <label>
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function TemperatureConverter() {
  const [celsius, setCelsius] = useState('');
  const [fahrenheit, setFahrenheit] = useState('');

  const handleCelsiusChange = (next) => {
    setCelsius(next);
    setFahrenheit(next === '' ? '' : (Number(next) * 9) / 5 + 32);
  };

  const handleFahrenheitChange = (next) => {
    setFahrenheit(next);
    setCelsius(next === '' ? '' : ((Number(next) - 32) * 5) / 9);
  };

  return (
    <div>
      <TemperatureInput label="摄氏度" value={celsius} onChange={handleCelsiusChange} />
      <TemperatureInput label="华氏度" value={fahrenheit} onChange={handleFahrenheitChange} />
    </div>
  );
}

export default TemperatureConverter;
```

这样可以确保两侧输入框的值始终保持同步。

## 副作用与生命周期

函数组件通过 `useEffect` 处理数据获取、订阅、计时器等副作用。

```jsx title="src/components/OnlineStatus.jsx"
import { useEffect, useState } from 'react';

function OnlineStatus() {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    const handleFocus = () => setIsOnline(true);
    const handleBlur = () => setIsOnline(false);

    window.addEventListener('focus', handleFocus);
    window.addEventListener('blur', handleBlur);

    return () => {
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('blur', handleBlur);
    };
  }, []);

  return <span>{isOnline ? '在线' : '离线'}</span>;
}

export default OnlineStatus;
```

- **依赖数组**：第二个参数控制副作用何时执行。  
  - `[]` 表示仅在挂载/卸载时触发。  
  - `[foo, bar]` 表示当依赖变化时重新执行。
- **清理函数**：在返回的函数里释放资源，避免内存泄漏或重复订阅。

掌握 props、条件渲染、列表与 key、状态提升和 useEffect，便能搭出大部分业务场景所需的组件交互模型。
