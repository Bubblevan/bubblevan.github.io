---
title: "CSS"
weight: 1
---

CSS属于前端里最牢的知识了，有点像编程界的C++，你永远没法说自己精通了CSS，而且前端开发和UI设计本身也在合流，这样一来就更牢了。
这里大纲先这样写着，后面再来补充。

```mermaid
graph TD
    A[CSS 学习指南] --> B[核心基础];
    A --> C[现代布局];
    A --> D[响应式设计];
    A --> E[视觉与交互];
    A --> F[生态与工具];

    B --> B1["CSS 是什么 & 如何工作"];
    B --> B2[选择器];
    B --> B3[盒模型];

    C --> C1[Flexbox];
    C --> C2[Grid];

    D --> D1[媒体查询];
    D --> D2[流式单位];

    E --> E1[CSS 变量];
    E --> E2[过渡];
    E --> E3[动画];

    F --> F1["预处理器 (Sass/SCSS)"];
    F --> F2["CSS 框架 (Tailwind)"];
```

- [核心基础](./bedrock)
- [现代布局](./layouts)
- [响应式设计](./responsive)
- [视觉与交互](./interactivity)
- [生态与工具](./ecosystem)
