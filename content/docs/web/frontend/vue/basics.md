---
id: vue-basics
title: Vue 核心语法与响应式基础
sidebar_label: 核心语法
---



## 入门准备

```bash
npm init vue@latest my-vue-app
cd my-vue-app
npm install
npm run dev
```

![Vue 默认项目预览](/img/vue/vue1.png)

你可以对比一下./src下面的核心入口文件，React是`App.jsx`、`App.css`、`index.css`、`main.jsx`，Vue是`App.vue`、`main.js`。这其实很好的体现了 SFC（Single File Component）的优势，将组件的模板、样式、逻辑都写在一个文件中，方便维护和管理。

### Vue 应用如何启动

Vue 将所有功能打包进应用实例，再挂载到某个 DOM 节点上：

```javascript title="src/main.js"
import { createApp } from 'vue';
import App from './App.vue';

createApp(App).mount('#app');
```
这段代码看起来很简单，但它做了三件至关重要的事：

1.  **`import { createApp } from 'vue'`**: 我们从 Vue 的核心库中取出了 `createApp` 这个工具，专门用来生产我们的 Vue 应用。
2.  **`import App from './App.vue'`**: `App.vue` 是我们应用的“根组件”。你可以把它想象成一棵树的树根，所有的枝叶（其他组件）都将从这里生长出来。它定义了应用最外层的结构和内容。
3.  **`createApp(App).mount('#app')`**: 
    *   `createApp(App)`：我们调用“工厂”函数，告诉它：“请用 `App.vue` 这个蓝图来创建我的应用吧！”
    *   `.mount('#app')`：创建好应用后，我们需要告诉 Vue 把它显示在哪里。这行代码的意思是：“找到 HTML 页面里那个 ID 是 `app` 的元素，然后把我的整个应用都渲染到那里去！”

> 小贴士：Vue 3 推荐以组件为中心组织代码，根组件 `App.vue` 就是我们渲染的起点。

### 响应式数据：`ref` 与 `reactive`

静态的页面是无趣的。Vue 的“响应式系统”就是当你的数据变化时，页面上依赖这些数据的地方会自动更新。在组合式 API (Composition API) 中，我们有两个方法来创建这种“会响应”的数据：`ref` 和 `reactive`。

#### `ref`
```javascript title="src/components/Counter.vue"
import { ref, reactive } from 'vue';

const count = ref(0); // 适合基本类型

console.log(count.value); // 输出: 0
// 要想改变盒子里面的值，你需要通过 .value 属性
count.value++;
console.log(count.value); // 输出: 1
```
- **为什么需要 `.value`？** `ref` 会将你的值包装在一个特殊的对象里，这样 Vue 才能“监视”到它的变化。在 JavaScript 逻辑中，你必须通过 `.value` 来访问或修改这个值。
- 好消息是，在模板 (`<template>`) 中使用 `count` 时，你不需要写 `.value`。Vue 会自动帮你“拆箱”。

#### `reactive`
```javascript title="src/components/Counter.vue"
import { ref, reactive } from 'vue';

const user = reactive({
  name: 'Bubblevan',
  age: 21,
}); // 适合对象、数组

console.log(user.name); // 输出: Bubblevan
// 要想改变盒子里面的值，你需要通过 .value 属性
user.age++;
console.log(user.age); // 输出: 22
```
| 特性 | `ref` | `reactive` |
| :--- | :--- | :--- |
| **适用场景** | 基本类型 (Number, String, Boolean) 或需要重新分配整个对象的场景 | 对象、数组 (Object, Array) |
| **访问方式** | 在脚本中通过 `.value` 访问 | 直接访问属性 |
| **模板中访问** | 直接访问，Vue 会自动解包 | 直接访问属性 |
| **返回类型** | 返回一个包含 `.value` 属性的 RefImpl 对象 | 返回一个响应式的 Proxy 对象 |

### 模板语法与事件绑定

我们已经学会了如何创建“活”数据，现在是时候让用户与这些数据互动了。
在 Vue 中，HTML 结构写在 `<template>` 块里，而交互逻辑则放在 `<script setup>` 块中。让我们来看一个经典的计数器例子：

```vue title="src/components/Counter.vue"
<template>
  <div class="card">
    <!-- 使用双花括号来显示数据 -->
    <p>当前计数：{{ count }}</p>

    <!-- 使用 @click 来监听点击事件 -->
    <button @click="increment">点我 +1</button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

// 1. 定义一个响应式数据 count
const count = ref(0);

// 2. 定义一个函数，用来修改 count 的值
const increment = () => {
  count.value += 1;
};
</script>
```

这个小小的组件展示了 Vue 的两大核心特性：

1.  **数据绑定 (`{{ count }}`**): `{{ }}` 是 Mustache 语法**（因其形似胡子而得名）**。它会在 `count` 和 `<p>` 标签之间建立一座“桥梁”。当 `count` 的值变化时，桥梁会自动将新值传输到页面上，实现视图的更新。Vue 知道 `count` 是一个响应式依赖，所以会时刻关注它的动向。

2.  **事件绑定 (`@click="increment"`)**: `@` 符号是 `v-on:` 的简写，是 Vue 用来监听 DOM 事件的指令。`@click="increment"` 的意思是：“当这个按钮被点击时，请执行 `<script>` 部分的 `increment` 函数。”

    - 当 `increment` 函数被调用时，`count.value` 会加 1。
    - 响应式系统监测到 `count` 的变化。
    - 它立刻通知所有依赖 `count` 的地方进行更新——也就是我们的 `<p>` 标签。
    - 于是，页面上的数字就增加了！

- `v-bind`（缩写 `:`）：动态绑定属性。
- `v-model`：实现双向数据绑定，底层是 `value` + `@input`。
- `v-if` / `v-else` / `v-show`：条件渲染，`v-show` 通过控制 `display`。
- `v-for`：列表渲染，记得写 `key`。



### 计算属性：声明式派生状态
有时候，你需要根据已有的状态计算出新的值。例如，根据用户的姓和名，得到完整的姓名。你当然可以每次都在模板里拼接字符串，但这样既不优雅，也效率低下。

更好的方法是使用 `computed`（计算属性）。

想象一下，你有一个购物车，里面有几件商品，每件商品都有价格和数量。你希望实时显示总价。总价就是一个“派生状态”，它完全依赖于商品的价格和数量。

```vue title="src/components/ShoppingCart.vue"
<template>
  <div>
    <p>商品A: 10元/件, 买了 {{ productA.quantity }} 件</p>
    <button @click="productA.quantity++">增加A</button>
    
    <p>商品B: 20元/件, 买了 {{ productB.quantity }} 件</p>
    <button @click="productB.quantity++">增加B</button>

    <hr>
    <h3>总价：{{ totalPrice }} 元</h3>
  </div>
</template>

<script setup>
import { reactive, computed } from 'vue';

const productA = reactive({ price: 10, quantity: 1 });
const productB = reactive({ price: 20, quantity: 2 });

// 定义一个计算属性 totalPrice
const totalPrice = computed(() => {
  console.log('正在重新计算总价...');
  return productA.price * productA.quantity + productB.price * productB.quantity;
});
</script>
```

`computed` 带来了两大好处：

1.  **声明式与可读性**：你只需声明 `totalPrice` 是如何由其他数据计算得来的。代码意图清晰明了，`totalPrice` 就像一个普通的响应式数据一样可以在模板中使用。

2.  **智能缓存**：`computed` 是懒加载且带缓存的。只有当它的依赖（`productA.quantity` 或 `productB.quantity`）发生变化时，它才会重新执行计算函数。如果你多次访问 `totalPrice` 而依赖没有变，它会直接返回上一次缓存的结果，避免了不必要的计算开销。你可以打开浏览器的控制台，点击按钮，看看 "正在重新计算总价..." 是不是只在必要时才打印。

将 `computed` 和普通函数做个对比：

- **普通函数**：每次在模板中调用 `{{ someFunction() }}`，它都会在每次渲染时重新执行一遍，无论依赖变不变。
- **计算属性**：只有在依赖更新后，第一次访问时才会重新计算，之后返回缓存值。

因此，当你需要从响应式数据派生出新值时，始终优先考虑使用 `computed`。
