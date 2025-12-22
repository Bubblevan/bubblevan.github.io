### **第一部分：CSS 核心基础**

1.  **CSS 是什么 & 如何工作**
    *   简介：CSS 的角色——网页的“化妆师”。
    *   三种引入方式：内联样式、内部样式表、外部样式表。
    *   核心概念：**层叠 (Cascade)**, **优先级 (Specificity)**, 和 **继承 (Inheritance)** —— 理解“谁的样式说了算”。

2.  **选择器 (Selectors): 精准定位你的目标**
    *   基础选择器：标签、类 (`.class`)、ID (`#id`)。
    *   组合选择器：后代 (` `)、子代 (`>`)、相邻兄弟 (`+`)、通用兄弟 (`~`)。
    *   伪类与伪元素：
        *   伪类 (Pseudo-classes): `:hover`, `:focus`, `:nth-child()`, `:not()` 等，用于描述元素在特定状态下的样式。
        *   伪元素 (Pseudo-elements): `::before`, `::after`, `::first-line` 等，用于在元素内容之外添加样式。

3.  **盒模型 (The Box Model): 万物皆为盒**
    *   `content`, `padding`, `border`, `margin` 的可视化解释。
    *   关键属性 `box-sizing: border-box`：为什么它能让布局更直观。