import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  // 动态侧边栏生成器
  tutorialSidebar: async ({defaultSidebarItemsGenerator, ...args}) => {
    const {item} = args;
    
    // 根据当前文档路径返回不同的侧边栏
    if (item && typeof item === 'object' && 'id' in item) {
      const docId = item.id as string;
      
      if (docId.startsWith('research/')) {
        return [
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
        ];
      } else if (docId.startsWith('bagu-infrastructure/')) {
        return [
          'bagu-infrastructure/intro',
          {
            type: 'category',
            label: '数据结构与算法',
            items: [
              'bagu-infrastructure/data-structures/arrays-strings',
              'bagu-infrastructure/data-structures/linked-lists',
              'bagu-infrastructure/algorithms/sorting',
              'bagu-infrastructure/algorithms/dynamic-programming',
            ],
          },
          {
            type: 'category',
            label: '计算机网络',
            items: [
              'bagu-infrastructure/network/tcp-ip',
            ],
          },
        ];
      } else if (docId.startsWith('projects/')) {
        return [
          'projects/intro',
          'projects/archaeological-recognition',
          'projects/joyfire-game',
          'projects/yuedong-sports',
          'projects/zju-timebox',
        ];
      } else if (docId.startsWith('undergraduate-notes/')) {
        return [
          'undergraduate-notes/intro',
          {
            type: 'category',
            label: '大三春夏',
            items: [
              'undergraduate-notes/大三春夏/仪器系统设计',
              'undergraduate-notes/大三春夏/生产实习',
              'undergraduate-notes/大三春夏/生物医学传感与检测',
              'undergraduate-notes/大三春夏/生物医学图像处理',
              'undergraduate-notes/大三春夏/电子系统设计与实践',
              'undergraduate-notes/大三春夏/硬件描述语言',
              'undergraduate-notes/大三春夏/计算机网络',
            ],
          },
          {
            type: 'category',
            label: '大三秋冬',
            items: [
              'undergraduate-notes/大三秋冬/信号与系统',
              'undergraduate-notes/大三秋冬/嵌入式系统',
              'undergraduate-notes/大三秋冬/生物医学成像技术',
              'undergraduate-notes/大三秋冬/误差处理与数据分析',
              'undergraduate-notes/大三秋冬/高级程序设计',
            ],
          },
          {
            type: 'category',
            label: '大二春夏',
            items: [
              'undergraduate-notes/大二春夏/微机原理及应用',
              'undergraduate-notes/大二春夏/数据结构与算法基础',
              'undergraduate-notes/大二春夏/电路与电子技术II',
              'undergraduate-notes/大二春夏/电路综合创新实践',
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
            label: '编程基础',
            items: [
              'undergraduate-notes/编程基础/c',
              'undergraduate-notes/编程基础/python',
            ],
          },
          {
            type: 'category',
            label: '通识杂项',
            items: [
              'undergraduate-notes/通识杂项/社会主义发展史',
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
              'undergraduate-notes/通识杂项/社会心理学',
              'undergraduate-notes/通识杂项/网球',
              'undergraduate-notes/通识杂项/职业生涯规划',
              'undergraduate-notes/通识杂项/龙舟',
            ],
          },
        ];
      } else if (docId.startsWith('self-study/')) {
        return [
          'self-study/intro',
          {
            type: 'category',
            label: 'AI',
            items: [
              'self-study/ai/computer-vision',
              'self-study/ai/deep-learning',
              'self-study/ai/nlp',
            ],
          },
          {
            type: 'category',
            label: '前端',
            items: [
              'self-study/frontend/react',
              'self-study/frontend/typescript',
              'self-study/frontend/uniapp',
              'self-study/frontend/vue',
            ],
          },
          {
            type: 'category',
            label: '后端',
            items: [
              'self-study/backend/fastapi',
              'self-study/backend/gorm',
              'self-study/backend/nestjs',
              'self-study/backend/springboot',
            ],
          },
          {
            type: 'category',
            label: '数据库',
            items: [
              'self-study/database/milvus',
              'self-study/database/mongodb',
              'self-study/database/mysql',
            ],
          },
        ];
      } else if (docId.startsWith('paper-reading/')) {
        return [
          'paper-reading/intro',
          'paper-reading/papers/world-models-survey',
        ];
      }
    }
    
    // 默认返回主导航侧边栏
    return [
      {
        type: 'category',
        label: '科研经历',
        items: [
          'research/intro',
        ],
      },
      {
        type: 'category',
        label: '八股基建',
        items: [
          'bagu-infrastructure/intro',
        ],
      },
      {
        type: 'category',
        label: '项目经历',
        items: [
          'projects/intro',
        ],
      },
      {
        type: 'category',
        label: '本科笔记',
        items: [
          'undergraduate-notes/intro',
        ],
      },
      {
        type: 'category',
        label: '自学笔记',
        items: [
          'self-study/intro',
        ],
      },
      {
        type: 'category',
        label: '论文阅读',
        items: [
          'paper-reading/intro',
        ],
      },
    ];
  },
};

export default sidebars;