---
id: vue-components
title: 第二阶段 组件开发
sidebar_label: 第二阶段
---

## 组件开发

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

