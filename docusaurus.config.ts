import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// 引入数学公式处理插件
const remarkMath = require('remark-math');
const rehypeKatex = require('rehype-katex');

const config: Config = {
  title: '包博文 - 个人网站',
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
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/bubblevan/bubblevan.github.io/tree/main/',
          // 添加数学公式处理插件
          remarkPlugins: [remarkMath],
          rehypePlugins: [rehypeKatex],
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
          onUntruncatedBlogPosts: 'warn',
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
      title: '包博文',
      logo: {
        alt: '包博文 Logo',
        src: 'img/logo.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'resumeSidebar',
          position: 'left',
          label: '我',
        },
        {
          type: 'docSidebar',
          sidebarId: 'undergraduateNotesSidebar',
          position: 'left',
          label: '本科笔记',
        },
        {
          type: 'docSidebar',
          sidebarId: 'projectsSidebar',
          position: 'left',
          label: '项目介绍',
        },
        {
          type: 'docSidebar',
          sidebarId: 'researchSidebar',
          position: 'left',
          label: '科研经历',
        },
        {
          type: 'docSidebar',
          sidebarId: 'selfStudySidebar',
          position: 'left',
          label: '自学笔记',
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
            { label: '简历', to: '/docs/resume' },
            { label: '项目经历', to: '/docs/projects/intro' },
            { label: '科研经历', to: '/docs/research/intro' },
          ],
        },
        {
          title: '学习笔记',
          items: [
            { label: '本科笔记', to: '/docs/undergraduate-notes/intro' },
            { label: '自学笔记', to: '/docs/self-study/intro' },
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
  } satisfies Preset.ThemeConfig,
};

export default config;
