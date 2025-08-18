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
    {
      type: 'category',
      label: '编程基础',
      items: [
        'undergraduate-notes/编程基础/c',
        'undergraduate-notes/编程基础/python',
      ],
    },
    {
      type: 'category',
      label: '数理基础',
      items: [
        'undergraduate-notes/数理基础/index',
      ],
    },
    {
      type: 'category',
      label: '大二秋冬',
      items: [
        'undergraduate-notes/大二秋冬/电路与电子技术I',
      ],
    },
    {
      type: 'category',
      label: '大二春夏',
      items: [
        'undergraduate-notes/大二春夏/电路与电子技术II',
        'undergraduate-notes/大二春夏/数据结构与算法基础',
        'undergraduate-notes/大二春夏/微机原理及应用',
        'undergraduate-notes/大二春夏/电路综合创新实践',
      ],
    },
    {
      type: 'category',
      label: '大三秋冬',
      items: [
        'undergraduate-notes/大三秋冬/信号与系统',
        'undergraduate-notes/大三秋冬/嵌入式系统',
        'undergraduate-notes/大三秋冬/生物医学成像技术',
        'undergraduate-notes/大三秋冬/高级程序设计',
        'undergraduate-notes/大三秋冬/误差处理与数据分析',
      ],
    },
    {
      type: 'category',
      label: '大三春夏',
      items: [
        'undergraduate-notes/大三春夏/生物医学传感与检测',
        'undergraduate-notes/大三春夏/生物医学图像处理',
        'undergraduate-notes/大三春夏/电子系统设计与实践',
        'undergraduate-notes/大三春夏/硬件描述语言',
        'undergraduate-notes/大三春夏/计算机网络',
        'undergraduate-notes/大三春夏/仪器系统设计',
        'undergraduate-notes/大三春夏/生产实习',
      ],
    },
    {
      type: 'category',
      label: '通识杂项',
      items: [
        'undergraduate-notes/通识杂项/中国共产党历史',
        'undergraduate-notes/通识杂项/中国改革开放史',
        'undergraduate-notes/通识杂项/军事理论',
        'undergraduate-notes/通识杂项/区块链技术应用实践',
        'undergraduate-notes/通识杂项/大学生物学',
        'undergraduate-notes/通识杂项/形势与政策',
        'undergraduate-notes/通识杂项/微信小程序综合实践',
        'undergraduate-notes/通识杂项/性与生殖',
        'undergraduate-notes/通识杂项/新农科实践-生活园艺',
        'undergraduate-notes/通识杂项/普通化学（乙）',
        'undergraduate-notes/通识杂项/极限飞盘',
        'undergraduate-notes/通识杂项/现当代西方建筑审美',
        'undergraduate-notes/通识杂项/生命科学导论',
        'undergraduate-notes/通识杂项/生物医学工程——智慧医疗的前世今生',
        'undergraduate-notes/通识杂项/社会主义发展史',
        'undergraduate-notes/通识杂项/社会心理学',
        'undergraduate-notes/通识杂项/网球',
        'undergraduate-notes/通识杂项/职业生涯规划',
        'undergraduate-notes/通识杂项/龙舟',
      ]
    },
  ],

  // 项目介绍侧边栏
  projectsSidebar: [
    'projects/intro',
    'projects/archaeological-recognition',
    'projects/joyfire-game',
    'projects/yuedong-sports',
    'projects/zju-timebox',
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
