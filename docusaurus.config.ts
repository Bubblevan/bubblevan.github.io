import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: '包博文 - 个人网站',
  tagline: '浙江大学',
  favicon: 'img/favicon.ico',

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: 'https://bubblevan.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'bubblevan', // Usually your GitHub org/user name.
  projectName: 'bubblevan.github.io', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
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
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/bubblevan/bubblevan.github.io/tree/main/',
        },
        blog: {
          showReadingTime: true,
          feedOptions: {
            type: ['rss', 'atom'],
            xslt: true,
          },
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/bubblevan/bubblevan.github.io/tree/main/',
          // Useful options to enforce blogging best practices
          onInlineTags: 'warn',
          onInlineAuthors: 'warn',
          onUntruncatedBlogPosts: 'warn',
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // Replace with your project's social card
    image: 'img/docusaurus-social-card.jpg',
    navbar: {
      title: '包博文',
      logo: {
        alt: '包博文 Logo',
        src: 'img/logo.svg',
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
            {
              label: '简历',
              to: '/docs/resume',
            },
            {
              label: '项目经历',
              to: '/docs/projects',
            },
            {
              label: '科研经历',
              to: '/docs/research',
            },
          ],
        },
        {
          title: '学习笔记',
          items: [
            {
              label: '本科笔记',
              to: '/docs/undergraduate-notes',
            },
            {
              label: '自学笔记',
              to: '/docs/self-study',
            },
            {
              label: '技术博客',
              to: '/blog',
            },
          ],
        },
        {
          title: '联系方式',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/Bubblevan',
            },
            {
              label: '邮箱',
              href: 'mailto:486502970@qq.com',
            },
            {
              label: '浙江大学',
              href: 'https://www.zju.edu.cn',
            },
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
