import React, { useEffect, useState } from 'react';
import { useLocation } from '@docusaurus/router';

interface SidebarItem {
  type: 'doc' | 'category';
  id?: string;
  label?: string;
  items?: SidebarItem[];
}

const researchSidebar: SidebarItem[] = [
  { type: 'doc', id: 'research/intro' },
  {
    type: 'category',
    label: 'AI4Science',
    items: [
      { type: 'doc', id: 'research/ai4science/crystal-prediction' },
      { type: 'doc', id: 'research/ai4science/ed-gat' },
    ],
  },
  {
    type: 'category',
    label: '机器学习',
    items: [
      { type: 'doc', id: 'research/ml/mhnn' },
    ],
  },
  {
    type: 'category',
    label: '大模型benchmark',
    items: [
      { type: 'doc', id: 'research/llm/realhitbench' },
      { type: 'doc', id: 'research/llm/vllm-optimization' },
    ],
  },
];

const baguInfrastructureSidebar: SidebarItem[] = [
  { type: 'doc', id: 'bagu-infrastructure/intro' },
  {
    type: 'category',
    label: '数据结构与算法',
    items: [
      { type: 'doc', id: 'bagu-infrastructure/data-structures/arrays-strings' },
      { type: 'doc', id: 'bagu-infrastructure/data-structures/linked-lists' },
      { type: 'doc', id: 'bagu-infrastructure/algorithms/sorting' },
      { type: 'doc', id: 'bagu-infrastructure/algorithms/dynamic-programming' },
    ],
  },
  {
    type: 'category',
    label: '计算机网络',
    items: [
      { type: 'doc', id: 'bagu-infrastructure/network/tcp-ip' },
    ],
  },
];

const projectsSidebar: SidebarItem[] = [
  { type: 'doc', id: 'projects/intro' },
  { type: 'doc', id: 'projects/archaeological-recognition' },
  { type: 'doc', id: 'projects/joyfire-game' },
  { type: 'doc', id: 'projects/yuedong-sports' },
  { type: 'doc', id: 'projects/zju-timebox' },
];

const undergraduateNotesSidebar: SidebarItem[] = [
  { type: 'doc', id: 'undergraduate-notes/intro' },
  {
    type: 'category',
    label: '大三春夏',
    items: [
      { type: 'doc', id: 'undergraduate-notes/大三春夏/仪器系统设计' },
      { type: 'doc', id: 'undergraduate-notes/大三春夏/生产实习' },
      { type: 'doc', id: 'undergraduate-notes/大三春夏/生物医学传感与检测' },
      { type: 'doc', id: 'undergraduate-notes/大三春夏/生物医学图像处理' },
      { type: 'doc', id: 'undergraduate-notes/大三春夏/电子系统设计与实践' },
      { type: 'doc', id: 'undergraduate-notes/大三春夏/硬件描述语言' },
      { type: 'doc', id: 'undergraduate-notes/大三春夏/计算机网络' },
    ],
  },
  {
    type: 'category',
    label: '大三秋冬',
    items: [
      { type: 'doc', id: 'undergraduate-notes/大三秋冬/信号与系统' },
      { type: 'doc', id: 'undergraduate-notes/大三秋冬/嵌入式系统' },
      { type: 'doc', id: 'undergraduate-notes/大三秋冬/生物医学成像技术' },
      { type: 'doc', id: 'undergraduate-notes/大三秋冬/误差处理与数据分析' },
      { type: 'doc', id: 'undergraduate-notes/大三秋冬/高级程序设计' },
    ],
  },
  {
    type: 'category',
    label: '大二春夏',
    items: [
      { type: 'doc', id: 'undergraduate-notes/大二春夏/微机原理及应用' },
      { type: 'doc', id: 'undergraduate-notes/大二春夏/数据结构与算法基础' },
      { type: 'doc', id: 'undergraduate-notes/大二春夏/电路与电子技术II' },
      { type: 'doc', id: 'undergraduate-notes/大二春夏/电路综合创新实践' },
    ],
  },
  {
    type: 'category',
    label: '大二秋冬',
    items: [
      { type: 'doc', id: 'undergraduate-notes/大二秋冬/电路与电子技术I' },
    ],
  },
  {
    type: 'category',
    label: '编程基础',
    items: [
      { type: 'doc', id: 'undergraduate-notes/编程基础/c' },
      { type: 'doc', id: 'undergraduate-notes/编程基础/python' },
    ],
  },
  {
    type: 'category',
    label: '通识杂项',
    items: [
      { type: 'doc', id: 'undergraduate-notes/通识杂项/社会主义发展史' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/中国共产党历史' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/中国改革开放史' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/军事理论' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/区块链技术应用实践' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/大学生物学' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/形势与政策' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/微信小程序综合实践' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/性与生殖' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/新农科实践-生活园艺' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/普通化学（乙）' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/极限飞盘' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/现当代西方建筑审美' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/生命科学导论' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/生物医学工程——智慧医疗的前世今生' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/社会心理学' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/网球' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/职业生涯规划' },
      { type: 'doc', id: 'undergraduate-notes/通识杂项/龙舟' },
    ],
  },
];

const selfStudySidebar: SidebarItem[] = [
  { type: 'doc', id: 'self-study/intro' },
  {
    type: 'category',
    label: 'AI',
    items: [
      { type: 'doc', id: 'self-study/ai/computer-vision' },
      { type: 'doc', id: 'self-study/ai/deep-learning' },
      { type: 'doc', id: 'self-study/ai/nlp' },
    ],
  },
  {
    type: 'category',
    label: '前端',
    items: [
      { type: 'doc', id: 'self-study/frontend/react' },
      { type: 'doc', id: 'self-study/frontend/typescript' },
      { type: 'doc', id: 'self-study/frontend/uniapp' },
      { type: 'doc', id: 'self-study/frontend/vue' },
    ],
  },
  {
    type: 'category',
    label: '后端',
    items: [
      { type: 'doc', id: 'self-study/backend/fastapi' },
      { type: 'doc', id: 'self-study/backend/gorm' },
      { type: 'doc', id: 'self-study/backend/nestjs' },
      { type: 'doc', id: 'self-study/backend/springboot' },
    ],
  },
  {
    type: 'category',
    label: '数据库',
    items: [
      { type: 'doc', id: 'self-study/database/milvus' },
      { type: 'doc', id: 'self-study/database/mongodb' },
      { type: 'doc', id: 'self-study/database/mysql' },
    ],
  },
];

const paperReadingSidebar: SidebarItem[] = [
  { type: 'doc', id: 'paper-reading/intro' },
  { type: 'doc', id: 'paper-reading/papers/world-models-survey' },
];

const mainNavigationSidebar: SidebarItem[] = [
  {
    type: 'category',
    label: '科研经历',
    items: [{ type: 'doc', id: 'research/intro' }],
  },
  {
    type: 'category',
    label: '八股基建',
    items: [{ type: 'doc', id: 'bagu-infrastructure/intro' }],
  },
  {
    type: 'category',
    label: '项目经历',
    items: [{ type: 'doc', id: 'projects/intro' }],
  },
  {
    type: 'category',
    label: '本科笔记',
    items: [{ type: 'doc', id: 'undergraduate-notes/intro' }],
  },
  {
    type: 'category',
    label: '自学笔记',
    items: [{ type: 'doc', id: 'self-study/intro' }],
  },
  {
    type: 'category',
    label: '论文阅读',
    items: [{ type: 'doc', id: 'paper-reading/intro' }],
  },
];

const DynamicSidebar: React.FC = () => {
  const location = useLocation();
  const [sidebarItems, setSidebarItems] = useState<SidebarItem[]>(mainNavigationSidebar);

  useEffect(() => {
    const path = location.pathname;
    console.log('🔍 动态侧边栏检测到路径变化:', path);

    // 根据路径确定显示哪个侧边栏
    if (path.startsWith('/docs/research/')) {
      console.log('🔬 切换到科研经历侧边栏');
      setSidebarItems(researchSidebar);
    } else if (path.startsWith('/docs/bagu-infrastructure/')) {
      console.log('🏗️ 切换到八股基建侧边栏');
      setSidebarItems(baguInfrastructureSidebar);
    } else if (path.startsWith('/docs/projects/')) {
      console.log('🚀 切换到项目经历侧边栏');
      setSidebarItems(projectsSidebar);
    } else if (path.startsWith('/docs/undergraduate-notes/')) {
      console.log('📚 切换到本科笔记侧边栏');
      setSidebarItems(undergraduateNotesSidebar);
    } else if (path.startsWith('/docs/self-study/')) {
      console.log('📖 切换到自学笔记侧边栏');
      setSidebarItems(selfStudySidebar);
    } else if (path.startsWith('/docs/paper-reading/')) {
      console.log('📄 切换到论文阅读侧边栏');
      setSidebarItems(paperReadingSidebar);
    } else {
      console.log('🏠 切换到主导航侧边栏');
      setSidebarItems(mainNavigationSidebar);
    }
  }, [location.pathname]);

  const renderSidebarItem = (item: SidebarItem, index: number): React.ReactNode => {
    if (item.type === 'doc' && item.id) {
      const displayName = item.id.split('/').pop()?.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      return (
        <li key={index}>
          <a href={`/docs/${item.id}`}>
            {displayName}
          </a>
        </li>
      );
    } else if (item.type === 'category' && item.label && item.items) {
      return (
        <li key={index}>
          <details>
            <summary>{item.label}</summary>
            <ul>
              {item.items.map((subItem, subIndex) => renderSidebarItem(subItem, subIndex))}
            </ul>
          </details>
        </li>
      );
    }
    return null;
  };

  return (
    <nav className="sidebar">
      <ul>
        {sidebarItems.map((item, index) => renderSidebarItem(item, index))}
      </ul>
    </nav>
  );
};

export default DynamicSidebar;
