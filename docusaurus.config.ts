import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// 引入数学公式处理插件
const remarkMath = require('remark-math');
const rehypeKatex = require('rehype-katex');

const config: Config = {
  markdown: {
    mermaid: true,
  },
  title: 'Bubblevan',
  tagline: '浙江大学',
  favicon: 'img/logo.png',

  future: {
    v4: true,
  },

  url: 'https://bubblevan.github.io',
  baseUrl: '/',

  organizationName: 'bubblevan',
  projectName: 'bubblevan.github.io',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'zh-Hans',
    locales: ['zh-Hans'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'docs',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          sidebarCollapsible: true,
          editUrl: 'https://github.com/bubblevan/bubblevan.github.io/tree/main/',
          remarkPlugins: [remarkMath],
          rehypePlugins: [rehypeKatex],
          include: ['**/*.md', '**/*.mdx'],
        },
        blog: {
          showReadingTime: true,
          feedOptions: {
            type: ['rss', 'atom'],
            xslt: true,
          },
          editUrl: 'https://github.com/bubblevan/bubblevan.github.io/tree/main/',
          onInlineTags: 'warn',
          onInlineAuthors: 'warn',
          onUntruncatedBlogPosts: 'ignore',
          // 博客也添加数学公式支持
          remarkPlugins: [remarkMath],
          rehypePlugins: [rehypeKatex],
        },
        theme: {
          customCss: ['./src/css/custom.css', './src/css/pdf-viewer.css'],
        },
      } satisfies Preset.Options,
    ],
  ],

  themes: ['@docusaurus/theme-mermaid'],

  // 移除所有插件，使用单一文档实例
  plugins: [],

  // 添加 KaTeX 样式表
  stylesheets: [
    {
      href: 'https://cdn.jsdelivr.net/npm/katex@0.16.4/dist/katex.min.css',
      integrity: 'sha384-vKruj+a13U8yHIkAyGgK1J3ArTLzrFGBbBc0tDp4ad/EyewESeXE/Iv67Aj8gKZ0',
      crossorigin: 'anonymous',
    },
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    navbar: {
      style: 'dark',
      title: 'Bubblevan',
      logo: {
        alt: 'Bubblevan logo',
        src: 'img/logo.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: '文档',
        },
        {
          to: '/blog',
          label: '博客',
          position: 'left',
        },
        {
          href: 'https://github.com/Bubblevan',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: '个人资料',
          items: [
            // { label: '项目经历', to: '/docs/projects/intro' },
            { label: '科研经历', to: '/docs/research/intro' },
            { label: 'GitHub', href: 'https://github.com/Bubblevan' },
          ],
        },
        {
          title: '学习笔记',
          items: [
            // { label: '本科笔记', to: '/docs/undergraduate-/intro' },
            // { label: '自学笔记', to: '/docs/self-study/intro' },
            { label: '技术博客', to: '/blog' },
          ],
        },
        {
          title: '联系方式',
          items: [
            { label: 'GitHub', href: 'https://github.com/Bubblevan' },
            { label: '邮箱', href: 'mailto:486502970@qq.com' },
            { label: '浙江大学', href: 'https://www.zju.edu.cn' },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} 包博文. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
    colorMode: {
      defaultMode: 'dark',
      disableSwitch: false,
      respectPrefersColorScheme: true,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
