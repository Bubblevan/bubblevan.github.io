## 组件：像搭乐高一样构建应用

随着应用变得越来越复杂，把所有代码都塞在一个文件里会变成一场噩梦。Vue 的核心思想就是**组件化**。它允许你将用户界面拆分成一个个独立、可复用的“积木块”，每个积木块就是一个组件。

想象一下你在刷朋友圈，整个页面可以被拆分成：一个顶部导航栏组件、一个好友列表组件、一个动态卡片组件、一个底部菜单组件……每个组件都有自己的 HTML、CSS 和 JavaScript，它们各司其职，最后再拼装成一个完整的应用。

### 定义你的第一个组件

一个 Vue 组件就是一个带有 `.vue` 后缀的文件，它通常由三部分组成：

-   `<template>`：定义组件的 HTML 结构。
-   `<script setup>`：编写组件的 JavaScript 逻辑。
-   `<style scoped>`：编写只作用于该组件的 CSS 样式。

让我们来创建一个 `UserCard.vue` 组件，它用来显示一个用户的信息卡片。

```vue title="src/components/UserCard.vue"
<template>
  <div class="user-card">
    <h3>{{ user.name }}</h3>
    <p>Email: {{ user.email }}</p>
  </div>
</template>

<script setup>
// 我们很快就会解决这个 user 是从哪里来的问题
</script>

<style scoped>
.user-card {
  border: 1px solid #ccc;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 10px;
}
</style>
```

现在，我们有了一个独立的 `UserCard` 组件。但它的数据是硬编码的，怎样才能让它显示不同的用户信息呢？答案是 `props`。

### Props：从父到子的数据传递

`props` (properties 的缩写) 是父组件向子组件传递数据的“专属通道”。它就像你在调用一个函数时传入的参数。

我们来改造一下 `UserCard.vue`，让它能接收一个 `user` 对象作为 prop。

```vue title="src/components/UserCard.vue"
<template>
  <div class="user-card">
    <h3>{{ user.name }}</h3>
    <p>Email: {{ user.email }}</p>
  </div>
</template>

<script setup>
import { defineProps } from 'vue';

// 1. 使用 defineProps 声明该组件期望接收一个名为 'user' 的 prop
const props = defineProps({
  user: {
    type: Object,     // 期望的类型是对象
    required: true,   // 这个 prop 是必需的
  },
});

// 2. 在模板中，你可以直接使用 props.user，或者更简单地，直接用 user
// Vue 在模板中会自动处理，让你感觉 user 就像本地定义的一样
</script>

<style scoped>
/* 样式保持不变 */
</style>
```

现在，`UserCard` 组件变成了一个灵活的模板。任何父组件都可以使用它，并传入不同的 `user` 数据。

假设我们有一个 `App.vue` 父组件：

```vue title="src/App.vue"
<template>
  <div>
    <h1>我的好友列表</h1>
    <UserCard :user="user1" />
    <UserCard :user="user2" />
  </div>
</template>

<script setup>
import { reactive } from 'vue';
import UserCard from './components/UserCard.vue'; // 1. 导入子组件

const user1 = reactive({ name: 'Alice', email: 'alice@example.com' });
const user2 = reactive({ name: 'Bob', email: 'bob@example.com' });
</script>
```

看到 `:user="user1"` 了吗？

-   `:` 是 `v-bind:` 的缩写，它告诉 Vue：“我要动态地绑定一个 prop。”
-   `user` 是子组件 `UserCard` 中定义的 prop 名称。
-   `"user1"` 是父组件 `App.vue` 中要传递的数据源。

这样，我们就实现了父组件向子组件的数据传递，并且成功复用了 `UserCard` 组件！

### Emit：从子到父的事件通知

我们已经解决了“从上到下”的数据流，那如果子组件想和父组件“对话”呢？比如，点击 `UserCard` 里的一个按钮，想通知父组件发生了某件事。

这就是 `emit` 的职责。子组件通过 `emit` 发出一个自定义事件，就像在说：“嘿，我这里发生了一件事！”，而父组件可以选择监听这个事件并做出响应。

让我们给 `UserCard.vue` 添加一个“选择”按钮。

```vue title="src/components/UserCard.vue"
<template>
  <div class="user-card">
    <h3>{{ user.name }}</h3>
    <p>Email: {{ user.email }}</p>
    <button @click="selectUser">选择该用户</button>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

const props = defineProps({ user: { type: Object, required: true } });

// 1. 声明该组件会触发一个名为 'user-selected' 的事件
const emit = defineEmits(['user-selected']);

const selectUser = () => {
  // 2. 触发事件，并把 user 对象作为参数传递出去
  emit('user-selected', props.user);
};
</script>

<style scoped>
/* ... */
</style>
```

现在，当按钮被点击时，`UserCard` 会向外发出一个 `user-selected` 事件，并附带上当前卡片的 `user` 数据。

父组件 `App.vue` 如何接收这个信号呢？

```vue title="src/App.vue"
<template>
  <div>
    <h1>我的好友列表</h1>
    <p v-if="selectedUser">当前已选择: {{ selectedUser.name }}</p>
    
    <UserCard 
      :user="user1" 
      @user-selected="handleUserSelection"
    />
    <UserCard 
      :user="user2" 
      @user-selected="handleUserSelection"
    />
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import UserCard from './components/UserCard.vue';

const user1 = reactive({ id: 1, name: 'Alice', email: 'alice@example.com' });
const user2 = reactive({ id: 2, name: 'Bob', email: 'bob@example.com' });

const selectedUser = ref(null);

// 3. 定义一个方法来处理子组件传来的事件
const handleUserSelection = (userFromChild) => {
  console.log('子组件传来了数据:', userFromChild);
  selectedUser.value = userFromChild;
};
</script>
```

我们在父组件中通过 `@user-selected="handleUserSelection"` 来监听子组件的自定义事件。当 `UserCard` emit `user-selected` 事件时，父组件的 `handleUserSelection` 方法就会被调用，并且能接收到子组件传递过来的 `user` 数据。

这就是 Vue 组件通信的黄金法则：**Props down, emits up** (数据通过 props 向下传递，事件通过 emits 向上通知)。这个单向数据流的模式让应用的状态变化更容易被理解和追踪。

## 深入探索：组合式 API 与自定义 Hooks

随着你对 Vue 越来越熟悉，你会遇到更强大的功能来帮助你组织代码，尤其是在大型应用中。让我们来探索其中的两个：**组合式 API (Composition API)** 和 **自定义 Hooks**。

### 组合式 API：一种更灵活的代码组织方式

Vue 3 引入了 **组合式 API** 作为传统 **选项式 API (Options API)** 的替代方案。虽然选项式 API 以其清晰的结构（`data`、`methods`、`computed`）对初学者非常友好，但组合式 API 提供了更大的灵活性，允许你将相关的逻辑组合在一起。

<details>
<summary>选项式 API vs. 组合式 API</summary>

在 Vue 2 和早期 Vue 3 中，你通常会用不同的选项块来组织组件：

- **选项式 API**: `data`, `methods`, `computed`, `watch` 等。这对于小型组件来说很直观，但当一个逻辑功能被分割到多个选项中时，会变得很麻烦。

- **组合式 API**: 通过 `<script setup>`，你可以按功能组织代码。这使得代码更易于阅读、维护和重用，对于中大型项目来说是一个巨大的优势。

</details>

下面是组合式 API 的一个简单示例，使用了生命周期钩子：

```javascript
import { onMounted, onUnmounted } from 'vue'

// 这段代码在组件的 <script setup> 内部运行
onMounted(() => {
  console.log('组件已经被挂载到 DOM 上了！')
})

onUnmounted(() => {
  console.log('组件即将被卸载。')
})
```

现在，你不再需要 `mounted` 和 `unmounted` 选项，而是可以直接在 `<script setup>` 中导入并使用这些函数，将相关的逻辑放在一起。

### 自定义 Hooks：像专家一样重用逻辑

组合式 API 最大的优势之一就是它能够通过 **自定义 Hooks** 轻松实现逻辑复用。一个 "Hook" (通常在 Vue 生态中称为 "Composable") 只是一个“钩入”Vue 响应式系统的函数。

想象一下，你有一个计数器逻辑，想在多个组件中使用。与其每次都重写逻辑，不如将它提取到一个自定义 Hook (Composable) 中。

让我们创建一个 `useCounter.js` 文件 (通常放在 `src/composables` 目录下)：

```javascript title="src/composables/useCounter.js"
// useCounter.js
import { ref } from 'vue'

export function useCounter(initialValue = 0) {
  const count = ref(initialValue)
  
  const increment = () => count.value++
  const decrement = () => count.value--
  const reset = () => {
    count.value = initialValue
  }
  
  // 暴露状态和方法
  return {
    count,
    increment,
    decrement,
    reset
  }
}
```

现在，任何组件都可以使用这个计数器逻辑：

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

通过自定义 Hooks (Composables)，你可以构建一个可重用的、响应式的逻辑库，在整个应用中轻松共享，让你的组件保持精简并专注于其表现层。