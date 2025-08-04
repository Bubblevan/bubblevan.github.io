import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  icon: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'AI & 机器学习',
    icon: '🤖',
    description: (
      <>
        专注于AI4Science、计算机视觉、自然语言处理等领域。在多个科研项目中取得重要成果，
        包括晶体力常数预测、人类活动识别、大模型评测等。
      </>
    ),
  },
  {
    title: '全栈开发',
    icon: '💻',
    description: (
      <>
        精通前后端技术栈，包括Vue、React、FastAPI、SpringBoot等。
        主导多个全栈项目开发，具备从需求分析到部署上线的完整项目经验。
      </>
    ),
  },
  {
    title: '学术研究',
    icon: '🎓',
    description: (
      <>
        在浙江大学攻读生物医学工程专业，GPA 4.27/5.0。
        参与多个前沿科研项目，发表论文，申请专利，具备扎实的学术研究能力。
      </>
    ),
  },
];

function Feature({title, icon, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <div className={styles.featureIcon} role="img">
          {icon}
        </div>
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
