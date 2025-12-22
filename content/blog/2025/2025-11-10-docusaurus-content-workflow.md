---
date: 2025-11-10
title: 在 Docusaurus 3 里搭建内容生产流水线
authors: [bubblevan]
tags: [docusaurus, docs, blog]
---

作为一套以文档驱动为核心的前端框架，Docusaurus 3 天然把「内容生产」拆成两个入口：`docs` 和 `blog`。最近整理站点时，我也顺手理了一遍这套流程，写下来算是备忘。

<!-- truncate -->

最初我完全没有博客的需求，因此从 `docs` 入手，把课程笔记、强化学习章节放进 `docs/self-study/ai` 一类的目录。

每个 Markdown 或 MDX 文件都可以用 front matter 决定 `id`、标题和侧边栏标签，然后通过 `sidebars.ts` 统一组织结构。

只要在某个类别下列出文档路径，访问 `/docs/...` 时就能看到层级清晰的目录树。

但是文档的内容太多太长了。如果想让一篇文档拆成多个小章节，除了常规的多文件方案，这里另一个常规解决方案是吧父级文件改成 `.mdx`，像 React 组件一样 `import` 子文档，再内联渲染，你就能在同一个页面里拼装章节，同时保留侧边栏导航。

```
import Chapter1 from './rl/chapter-1.md';
import Chapter2 from './rl/chapter-2.md';
import Chapter3 from './rl/chapter-3.md';

<Chapter1 />

<Chapter2 />

<Chapter3 />
```

写到这里就不可避免要碰 `docusaurus.config.ts`。`classic` 预设里 `docs` 与 `blog` 的配置都在这里：`routeBasePath` 决定入口路径，`editUrl` 可以连到 GitHub。

想让数学公式在博客和文档里都生效，就把 `remark-math`、`rehype-katex` 同时塞进两个插件配置。

导航栏是在 `themeConfig.navbar.items` 里布置的，像 `type: 'docSidebar'` 这样的条目，可以把整个文档侧边栏挂到顶栏里；而 `to: '/blog'` 则直接跳转到博客首页。

说到博客，Docusaurus 会自动扫描 `./blog` 目录，按照日期或 slug 生成路由。文章同样支持 Markdown、MDX，还有 `authors.yml`、`tags.yml` 管理作者与标签。比如这篇文章就使用 front matter 里的 `tags: [docusaurus, docs, blog]`，最终会渲染成标签页链接。

写作体验跟文档差不多，但因为博客默认暴露 RSS、Atom 订阅，还能在配置文件里打开阅读时长统计，所以我常把学习心得、踩坑记录放在这里。

MDX 则是打通 React 组件和 Markdown 的桥梁：你可以引入现成的组件，也可以在 `src/components` 写一个自定义卡片，然后在任意文档、博客中 `<Highlight>` 一下。如果要引用别的 Markdown 片段，直接 `import Section from '../foo/bar.md'`，接着 `<Section />`，Docusaurus 在构建时会内联处理。这在编写重复的导言、FAQ 时很好用，既不会复制粘贴，也不怕链接失效。

管理多章节文档时，我越来越喜欢把大纲拆成子目录，再在 `_category_.json` 里加入 `generated-index`。这样一来，访问目录本身就能看到自动生成的索引页，还能写简介。必要时也能通过 `link` 配置生成手写的 md 页面。随着文档越来越多，还可以在类别层级上应用 `collapsed: false` 让关键模块默认展开，读者体验会好很多。

最后补一笔 React 组件的故事。Docusaurus 的主题本质是 React 应用，所以自带的布局、`DocItem` 等部件都能 override。只要在 `src/theme` 下按需复制对应组件，就能自定义渲染逻辑，例如替换文档页眉、给博客加上分享按钮。我自己常把一些重复的提示条、总结卡片抽成小组件，既能保持风格统一，又方便在 MDX 中复用。
