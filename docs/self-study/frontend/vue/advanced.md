---
id: vue-advanced
title: 第三阶段 高级特性
sidebar_label: 第三阶段
---
import CollapsibleBlock from '@site/src/components/CollapsibleBlock';

## 高级特性

随着你对 Vue 越来越熟悉，你会渴望更高效、更优雅的方式来组织代码，尤其是在构建复杂应用时。

Vue 3 提供了强大的 **组合式 API (Composition API)** 和 **自定义 Hooks (Composables)**。

### 组合式 API (Composition API)

在 Vue 2 中，我们习惯于 **选项式 API (Options API)**，它通过 `data`、`methods`、`computed` 等选项来组织代码。这种方式结构清晰，对初学者非常友好。但随着组件功能的增多，同一个逻辑（比如，处理用户数据）的代码会散落在不同的选项里，难以维护。

**组合式 API** 正是为了解决这个问题而生。它允许你将相关的逻辑代码组织在一起，形成一个高内聚的“功能单元”。

让我们看一个简单的生命周期钩子示例：

```javascript
import { onMounted, onUnmounted } from 'vue'

// 这段代码通常在组件的 <script setup> 内部运行
onMounted(() => {
  console.log('组件已经被挂载到 DOM 上了！')
  // 可以在这里执行初始化操作，比如获取数据
})

onUnmounted(() => {
  console.log('组件即将被卸载。')
  // 可以在这里执行清理操作，比如移除事件监听器
})
```

看到了吗？不再需要 `mounted` 和 `unmounted` 选项，你可以直接在 `<script setup>` 中导入并使用这些函数。所有与“组件挂载/卸载”相关的逻辑都集中在了一起，一目了然。

<CollapsibleBlock title="深入了解：<script> 的三种写法与 Vue 版本差异" defaultExpanded={false}>

在单文件组件（`.vue` 文件）中，`<script>` 标签是组件逻辑的核心。随着 Vue 的发展，它演变出了几种不同的写法。

#### 1. `<script>` 的三种形态

**a) 经典 `<script>` (选项式 API)**

这是 Vue 2 的标志性写法，在 Vue 3 中也完全兼容。代码通过 `data`、`methods`、`computed` 等选项来组织。

```vue
<script>
export default {
  data() {
    return {
      message: 'Hello, Options API!'
    }
  },
  methods: {
    greet() {
      alert(this.message);
    }
  }
}
</script>
```

**b) `<script>` 配合 `setup()` 函数 (组合式 API)**

在不使用 `<script setup>` 语法糖时，你也可以在 `<script>` 标签内使用组合式 API。但这需要一个 `setup()` 函数，并且必须**手动 `return`** 所有需要暴露给模板的变量和函数。

```vue
<script>
import { ref } from 'vue';

export default {
  setup() {
    const message = ref('Hello, Composition API!');

    function greet() {
      alert(message.value);
    }

    // 必须手动暴露
    return {
      message,
      greet
    };
  }
}
</script>
```

**c) `<script setup>` (组合式 API 的最佳实践 - 推荐)**

这是 Vue 3.2+ 引入的语法糖，它极大地简化了组合式 API 的使用。代码更简洁，无需 `setup()` 函数和 `return`。在 `<script setup>` 中声明的顶层变量、函数和导入的组件，都会**自动暴露给模板**。

```vue
<template>
  <button @click="greet">{{ message }}</button>
</template>

<script setup>
import { ref } from 'vue';

const message = ref('Hello, <script setup>!');

function greet() {
  alert(message.value);
}
</script>
```

#### 2. Vue 2 vs. Vue 3 的核心区别

| 特性 | Vue 2 | Vue 3 |
| :--- | :--- | :--- |
| **核心 API** | **选项式 API**：逻辑按选项分散，不利于复杂逻辑的组织。 | **组合式 API**：逻辑按功能组织，代码更内聚、更易复用。 |
| **性能** | 通过 `Object.defineProperty` 实现响应式，对对象属性的增删无法直接检测。 | 通过 `Proxy` 重写响应式系统，性能更好，且能直接监听对象和数组的动态变化。 |
| **模板根节点** | 模板必须有**一个**根元素。 | 支持**多个**根元素 (Fragments)，代码结构更灵活。 |
| **v-model** | 一个组件上只能使用一个 `v-model`。 | 支持在同一个组件上绑定多个 `v-model`，如 `v-model:title` 和 `v-model:content`。 |

</CollapsibleBlock>

### 自定义 Hooks (Composables)

组合式 API 最大的魅力在于它能够通过 **自定义 Hooks** (官方称之为 **Composables**) 轻松实现逻辑复用。一个 "Composable" 本质上就是一个“钩入”Vue 响应式系统的函数。

想象一下，你有一个计数器逻辑，想在多个组件中使用。与其每次都重写，不如将它提取到一个自定义 Composable 中。

按照惯例，我们将这些文件放在 `src/composables` 目录下。

**1. 创建你的 Composable:**

```javascript title="src/composables/useCounter.js"
// useCounter.js
import { ref } from 'vue'

// Composable 函数名通常以 "use" 开头
export function useCounter(initialValue = 0) {
  const count = ref(initialValue)
  
  const increment = () => count.value++
  const decrement = () => count.value--
  const reset = () => {
    count.value = initialValue
  }
  
  // 暴露状态和方法，供组件使用
  return {
    count,
    increment,
    decrement,
    reset
  }
}
```

**2. 在组件中使用它:**

现在，任何组件都可以像调用一个普通函数一样，轻松地使用这个计数器逻辑。

```vue title="src/components/MyCounter.vue"
<template>
  <div>
    <p>Count: {{ count }}</p>
    <button @click="increment">Increment</button>
    <button @click="decrement">Decrement</button>
    <button @click="reset">Reset</button>
  </div>
</template>

<script setup>
import { useCounter } from '../composables/useCounter.js'

// 使用自定义 Hook，并传入初始值 10
const { count, increment, decrement, reset } = useCounter(10)
</script>
```

通过自定义 Composables，你可以构建一个可重用的、响应式的逻辑库，在整个应用中轻松共享，让你的组件保持精简并专注于其 UI 呈现。

### 样式隔离与预处理器

`<style>` 标签用于定义组件的样式，它有两个非常实用的属性，能让你的样式管理更轻松：

- **`scoped`**: 当 `<style>` 标签带有 `scoped` 属性时，它的 CSS 只会应用到当前组件的元素上。Vue 会为组件的 DOM 元素添加一个唯一的属性（如 `data-v-f3f3eg9`），然后重写你的 CSS 选择器，确保样式不会“泄露”出去影响到其他组件。这就像给组件的样式穿上了一层“防护服”。

- **`lang="scss"`**: `lang` 属性允许你使用 CSS 预处理器，如 [Sass](https://sass-lang.com/) (SCSS)、Less 或 Stylus。这让你能使用变量、嵌套、混入（mixins）等高级功能，编写更强大、更易于维护的样式代码。

下面是一个结合了 `scoped` 和 SCSS 的例子：

```vue
<style lang="scss" scoped>
/* 使用 SCSS 变量定义主题色 */
$primary-color: #42b983;

.my-component {
  color: $primary-color;

  /* SCSS 嵌套语法让结构更清晰 */
  p {
    font-size: 16px;
    
    &:hover {
      color: darken($primary-color, 10%);
    }
  }
}
</style>
```