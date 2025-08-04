import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  // 简历侧边栏
  resumeSidebar: [
    'resume',
    {
      type: 'category',
      label: '基本信息',
      items: [
        'resume/basic-info',
        'resume/education',
        'resume/skills',
      ],
    },
    {
      type: 'category',
      label: '荣誉奖项',
      items: [
        'resume/honors',
      ],
    },
  ],

  // 本科笔记侧边栏
  undergraduateNotesSidebar: [
    'undergraduate-notes/intro',
    'undergraduate-notes/电子系统设计与实践',
    'undergraduate-notes/生物医学传感与检测',
    'undergraduate-notes/硬件描述语言',
    'undergraduate-notes/计算机网络',
    'undergraduate-notes/生物医学图像处理',
    'undergraduate-notes/离散数学',
    'undergraduate-notes/仪器系统设计',
    'undergraduate-notes/信号与系统',
    'undergraduate-notes/高级程序设计',
    'undergraduate-notes/生物医学成像技术',
    'undergraduate-notes/嵌入式系统',
    'undergraduate-notes/误差处理与数据分析',
  ],

  // 项目介绍侧边栏
  projectsSidebar: [
    'projects/intro',
    {
      type: 'category',
      label: 'AI项目',
      items: [
        'projects/ai/archaeological-recognition',
        'projects/ai/joyfire-game',
      ],
    },
    {
      type: 'category',
      label: '全栈项目',
      items: [
        'projects/fullstack/yuedong-sports',
        'projects/fullstack/zju-timebox',
      ],
    },
  ],

  // 科研经历侧边栏
  researchSidebar: [
    'research/intro',
    {
      type: 'category',
      label: 'AI4Science',
      items: [
        'research/ai4science/crystal-prediction',
        'research/ai4science/ed-gat',
      ],
    },
    {
      type: 'category',
      label: '机器学习',
      items: [
        'research/ml/human-activity-recognition',
        'research/ml/mhnn',
      ],
    },
    {
      type: 'category',
      label: '大模型benchmark',
      items: [
        'research/llm/realhitbench',
        'research/llm/vllm-optimization',
      ],
    },
  ],

  // 自学笔记侧边栏
  selfStudySidebar: [
    'self-study/intro',
    {
      type: 'category',
      label: '前端技术',
      items: [
        'self-study/frontend/vue',
        'self-study/frontend/react',
        'self-study/frontend/typescript',
      ],
    },
    {
      type: 'category',
      label: '后端技术',
      items: [
        'self-study/backend/fastapi',
        'self-study/backend/springboot',
        'self-study/backend/nestjs',
      ],
    },
    {
      type: 'category',
      label: '数据库',
      items: [
        'self-study/database/mysql',
        'self-study/database/mongodb',
        'self-study/database/milvus',
      ],
    },
    {
      type: 'category',
      label: 'AI/ML',
      items: [
        'self-study/ai/deep-learning',
        'self-study/ai/computer-vision',
        'self-study/ai/nlp',
      ],
    },
  ],
};

export default sidebars;
