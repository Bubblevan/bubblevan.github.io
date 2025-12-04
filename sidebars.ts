import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  // 静态侧边栏配置 - 所有板块都显示
  tutorialSidebar: [
    {
      type: 'category',
      label: '科研经历',
      link: { type: 'doc', id: 'research/intro' },
      items: [
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
    },
    {
      type: 'category',
      label: '八股基建',
      link: { type: 'doc', id: 'bagu-infrastructure/intro' },
      items: [
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
      ],
    },
    {
      type: 'category',
      label: '项目经历',
      link: { type: 'doc', id: 'projects/intro' },
      items: [
        'projects/archaeological-recognition',
        'projects/joyfire-game',
        'projects/yuedong-sports',
        'projects/zju-timebox',
      ],
    },
    {
      type: 'category',
      label: '本科笔记',
      link: { type: 'doc', id: 'undergraduate-notes/intro' },
      items: [
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
      ],
    },
    {
      type: 'category',
      label: '自学笔记',
      link: { type: 'doc', id: 'self-study/intro' },
      items: [
        {
          type: 'category',
          label: '人工智能',
          items: [
            'self-study/ai/cv',
            'self-study/ai/dl',
            'self-study/ai/nlp',
            {
              type: 'category',
              label: '强化学习',
              link: { type: 'doc', id: 'self-study/ai/rl' },
              items: [
                'self-study/ai/rl/rl-chapters-2-3',
                'self-study/ai/rl/rl-chapter-4',
                'self-study/ai/rl/rl-chapter-5',
                'self-study/ai/rl/rl-chapter-6',
                'self-study/ai/rl/rl-chapter-7',
                'self-study/ai/rl/rl-chapter-8',
                'self-study/ai/rl/rl-chapter-9',
                'self-study/ai/rl/rl-chapter-10',
              ],
            },
            'self-study/ai/graphics',
            'self-study/ai/multimodal',
            'self-study/ai/llm',
          ],
        },
        {
          type: 'category',
          label: '具身智能',
          link: { type: 'doc', id: 'self-study/embodied/intro' },
          items: [
            'self-study/embodied/vla',
            'self-study/embodied/vln',
            'self-study/embodied/llm4x',
          ],
        },
        {
          type: 'category',
          label: '前端',
          items: [
            'self-study/frontend/css',
            'self-study/frontend/javascript',
            'self-study/frontend/react',
            'self-study/frontend/typescript',
            'self-study/frontend/n_xtjs',
            'self-study/frontend/vue',
          ],
        },
        {
          type: 'category',
          label: '客户端',
          link: { type: 'doc', id: 'self-study/client/intro' },
          items: [
            'self-study/client/pyqt',
            'self-study/client/uniapp-quickstart',
          ],
        },
        {
          type: 'category',
          label: '后端',
          items: [
            'self-study/backend/fastapi',
            'self-study/backend/gin',
            {
              type: 'category',
              label: '中间件',
              link: {type: 'generated-index'},
              items: [
                'self-study/backend/middleware/auth',
                'self-study/backend/middleware/message-queue',
                'self-study/backend/middleware/redis',
              ],
            },
            {
              type: 'category',
              label: 'DevOps',
              link: {type: 'generated-index'},
              items: [
                'self-study/backend/devops/docker',
                'self-study/backend/devops/ci-cd',
              ],
            },
            'self-study/backend/nestjs',
            'self-study/backend/springboot',
          ],
        },
        {
          type: 'category',
          label: '数据库',
          items: [
            'self-study/database/intro',
            'self-study/database/milvus',
            'self-study/database/mongodb',
            'self-study/database/mysql',
            'self-study/database/postgresql',
            'self-study/database/gorm',
            'self-study/database/prisma',
            'self-study/database/typeorm',
          ],
        },
      ],
    },
  ],
};

export default sidebars;