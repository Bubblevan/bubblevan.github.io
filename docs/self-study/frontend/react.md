# React 自学笔记

## 学习目标

掌握 React 18.x 的核心概念和开发技能，能够独立开发 React 应用。

## 核心概念

### 组件化开发
- **函数组件**: 现代 React 的主要组件形式
- **类组件**: 传统组件形式，仍在使用
- **组件生命周期**: 挂载、更新、卸载阶段

### 状态管理
- **useState**: 函数组件状态管理
- **useReducer**: 复杂状态逻辑管理
- **Context API**: 跨组件状态共享

### 虚拟 DOM
- **虚拟 DOM 原理**: 高效的 DOM 更新机制
- **Diff 算法**: 最小化 DOM 操作
- **Fiber 架构**: React 18 的并发特性

## 学习路径

### 第一阶段：基础语法
1. **组件创建**
```jsx
import React from 'react'

function App() {
  return (
    <div className="App">
      <h1>Hello React</h1>
    </div>
  )
}

export default App
```

2. **状态管理**
```jsx
import React, { useState } from 'react'

function Counter() {
  const [count, setCount] = useState(0)
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        增加
      </button>
    </div>
  )
}
```

3. **事件处理**
```jsx
function Form() {
  const [input, setInput] = useState('')
  
  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('提交:', input)
  }
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <button type="submit">提交</button>
    </form>
  )
}
```

### 第二阶段：高级特性
1. **useEffect Hook**
```jsx
import React, { useState, useEffect } from 'react'

function UserProfile({ userId }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetch(`/api/users/${userId}`)
        const userData = await response.json()
        setUser(userData)
      } catch (error) {
        console.error('获取用户信息失败:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchUser()
  }, [userId])
  
  if (loading) return <div>加载中...</div>
  if (!user) return <div>用户不存在</div>
  
  return (
    <div>
      <h2>{user.name}</h2>
      <p>{user.email}</p>
    </div>
  )
}
```

2. **自定义 Hook**
```jsx
// useLocalStorage.js
import { useState, useEffect } from 'react'

function useLocalStorage(key, initialValue) {
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.error(error)
      return initialValue
    }
  })
  
  const setValue = (value) => {
    try {
      setStoredValue(value)
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.error(error)
    }
  }
  
  return [storedValue, setValue]
}

// 使用示例
function App() {
  const [name, setName] = useLocalStorage('name', '包博文')
  
  return (
    <div>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="输入姓名"
      />
    </div>
  )
}
```

### 第三阶段：状态管理
1. **Context API**
```jsx
// UserContext.js
import React, { createContext, useContext, useState } from 'react'

const UserContext = createContext()

export function UserProvider({ children }) {
  const [user, setUser] = useState(null)
  
  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const context = useContext(UserContext)
  if (!context) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}
```

2. **Redux Toolkit**
```jsx
// store/userSlice.js
import { createSlice } from '@reduxjs/toolkit'

const userSlice = createSlice({
  name: 'user',
  initialState: {
    currentUser: null,
    loading: false,
    error: null
  },
  reducers: {
    setUser: (state, action) => {
      state.currentUser = action.payload
    },
    setLoading: (state, action) => {
      state.loading = action.payload
    },
    setError: (state, action) => {
      state.error = action.payload
    }
  }
})

export const { setUser, setLoading, setError } = userSlice.actions
export default userSlice.reducer
```

## 实战项目

### 项目一：待办事项应用
- **功能**: 添加、删除、完成待办事项
- **技术**: React + Hooks
- **状态管理**: Context API

### 项目二：博客系统
- **功能**: 文章列表、详情、评论
- **技术**: React + React Router
- **状态管理**: Redux Toolkit

### 项目三：电商平台
- **功能**: 商品展示、购物车、订单管理
- **技术**: React + TypeScript
- **UI**: Ant Design

## 最佳实践

### 代码组织
- **目录结构**: 按功能模块组织代码
- **组件拆分**: 合理拆分组件粒度
- **文件命名**: 统一的命名规范

### 性能优化
- **React.memo**: 避免不必要的重渲染
- **useMemo/useCallback**: 缓存计算结果和函数
- **懒加载**: 路由和组件懒加载

### 测试
- **单元测试**: 使用 Jest + React Testing Library
- **集成测试**: 测试组件交互
- **E2E 测试**: 使用 Cypress

## 学习资源

### 官方文档
- [React 官方文档](https://react.dev/)
- [React 中文文档](https://zh-hans.react.dev/)

### 在线课程
- React 官方教程
- 慕课网 React 课程
- 极客时间 React 专栏

### 实践项目
- GitHub 上的开源项目
- 个人作品集网站
- 企业管理系统

## 学习心得

### 学习建议
1. **理解核心概念**: 深入理解组件、状态、生命周期
2. **多写代码**: 通过项目实践巩固知识
3. **关注生态**: 了解 React 生态系统
4. **性能优化**: 学习性能优化技巧

### 常见问题
1. **状态管理**: 选择合适的状态管理方案
2. **性能问题**: 避免不必要的重渲染
3. **异步操作**: 正确处理异步数据获取
4. **TypeScript**: 结合 TypeScript 提升开发体验 