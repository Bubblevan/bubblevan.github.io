# Vue.js 自学笔记

## 学习目标

掌握 Vue.js 3.x 的核心概念和开发技能，能够独立开发 Vue.js 应用。

## 核心概念

### 响应式系统
- **响应式原理**: 基于 Proxy 的响应式系统
- **响应式数据**: ref, reactive, computed, watch
- **生命周期**: 组件生命周期钩子

### 组件系统
- **单文件组件**: .vue 文件结构
- **组件通信**: props, emit, provide/inject
- **组件注册**: 全局和局部注册

### 模板语法
- **插值**: {{ }} 文本插值
- **指令**: v-if, v-for, v-on, v-bind
- **事件处理**: @click, @input 等

## 学习路径

### 第一阶段：基础语法
1. **Vue 实例创建**
```javascript
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)
app.mount('#app')
```

2. **响应式数据**
```javascript
import { ref, reactive } from 'vue'

// ref 用于基本类型
const count = ref(0)

// reactive 用于对象
const state = reactive({
  name: '包博文',
  age: 25
})
```

3. **计算属性**
```javascript
import { computed } from 'vue'

const doubleCount = computed(() => count.value * 2)
```

### 第二阶段：组件开发
1. **组件定义**
```vue
<template>
  <div class="user-card">
    <h3>{{ user.name }}</h3>
    <p>{{ user.email }}</p>
    <button @click="handleClick">点击</button>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  user: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['click'])

const handleClick = () => {
  emit('click', props.user)
}
</script>
```

2. **组件通信**
- **Props 传递**: 父组件向子组件传递数据
- **Emit 事件**: 子组件向父组件发送事件
- **Provide/Inject**: 跨层级组件通信

### 第三阶段：高级特性
1. **组合式 API**
```javascript
import { onMounted, onUnmounted } from 'vue'

onMounted(() => {
  console.log('组件已挂载')
})

onUnmounted(() => {
  console.log('组件已卸载')
})
```

2. **自定义 Hook**
```javascript
// useCounter.js
import { ref } from 'vue'

export function useCounter(initialValue = 0) {
  const count = ref(initialValue)
  
  const increment = () => count.value++
  const decrement = () => count.value--
  const reset = () => count.value = initialValue
  
  return {
    count,
    increment,
    decrement,
    reset
  }
}
```

## 实战项目

### 项目一：待办事项应用
- **功能**: 添加、删除、完成待办事项
- **技术**: Vue 3 + Composition API
- **状态管理**: Pinia

### 项目二：用户管理系统
- **功能**: 用户列表、添加、编辑、删除
- **技术**: Vue 3 + Element Plus
- **API**: 与后端接口交互

### 项目三：电商购物车
- **功能**: 商品展示、购物车、结算
- **技术**: Vue 3 + Vue Router + Pinia
- **UI**: 自定义组件库

## 最佳实践

### 代码组织
- **目录结构**: 清晰的目录组织
- **组件命名**: 语义化的组件命名
- **文件命名**: 统一的文件命名规范

### 性能优化
- **懒加载**: 路由懒加载
- **虚拟滚动**: 大数据列表优化
- **缓存**: 组件缓存和计算属性缓存

### 测试
- **单元测试**: 使用 Vitest 进行单元测试
- **组件测试**: 使用 Vue Test Utils
- **E2E 测试**: 使用 Cypress 或 Playwright

## 学习资源

### 官方文档
- [Vue.js 官方文档](https://vuejs.org/)
- [Vue.js 中文文档](https://cn.vuejs.org/)

### 在线课程
- Vue.js 官方教程
- 慕课网 Vue.js 课程
- 极客时间 Vue.js 专栏

### 实践项目
- GitHub 上的开源项目
- 个人博客系统
- 企业管理系统

## 学习心得

### 学习建议
1. **理论结合实践**: 边学边做项目
2. **循序渐进**: 从基础到高级逐步学习
3. **多看源码**: 学习优秀开源项目的源码
4. **参与社区**: 参与 Vue.js 社区讨论

### 常见问题
1. **响应式数据**: 理解 ref 和 reactive 的区别
2. **组件通信**: 选择合适的通信方式
3. **性能优化**: 避免不必要的重渲染
4. **TypeScript**: 结合 TypeScript 提升开发体验 