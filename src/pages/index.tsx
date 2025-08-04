import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          包博文
        </Heading>
        <p className="hero__subtitle">浙江大学 · 生物医学工程 · 全栈开发工程师</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/resume">
            查看简历 📄
          </Link>
          <Link
            className="button button--outline button--lg"
            to="/docs/projects"
            style={{marginLeft: '10px'}}>
            项目经历 🚀
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="包博文 - 个人网站"
      description="浙江大学生物医学工程专业学生，全栈开发工程师，专注于AI、机器学习和全栈开发">
      <HomepageHeader />
      <main>
        <div className="container margin-vert--lg">
          <div className="row">
            <div className="col col--8">
              <h2>👋 关于我</h2>
              <p>
                我是包博文，浙江大学生物医学工程专业的学生。我热爱技术，专注于AI、机器学习和全栈开发。
                目前GPA 4.27/5.0，在多个重要项目中担任核心开发角色。
              </p>
              
              <h3>🎯 主要成就</h3>
              <ul>
                <li><strong>国家级奖项：</strong>第九届"互联网+"大学生创新创业大赛国家级铜奖</li>
                <li><strong>学术荣誉：</strong>获得2022-2023学年校设奖学金，获学业、公益、社会、劳动、对外交流标兵称号</li>
                <li><strong>技术能力：</strong>精通Python、Golang、TypeScript、Vue、React、SQL等技术栈</li>
                <li><strong>项目经验：</strong>主导多个AI和全栈项目的开发，包括考古识别系统、AI游戏后端等</li>
              </ul>

              <h3>🔬 科研方向</h3>
              <ul>
                <li><strong>AI4Science：</strong>图注意力等变神经网络的晶体力常数预测</li>
                <li><strong>机器学习：</strong>基于多级异构神经网络的人类活动识别系统</li>
                <li><strong>大模型评测：</strong>层级化表格分析大模型评测基准</li>
                <li><strong>系统优化：</strong>基于VLLM的端到端延迟优化模型</li>
              </ul>
            </div>
            
            <div className="col col--4">
              <div className="card">
                <div className="card__header">
                  <h3>📊 技能概览</h3>
                </div>
                <div className="card__body">
                  <h4>编程语言</h4>
                  <p>Python, Golang, C, TypeScript</p>
                  
                  <h4>前端技术</h4>
                  <p>Vue, React, Uniapp</p>
                  
                  <h4>后端技术</h4>
                  <p>FastAPI, SpringBoot, NestJS</p>
                  
                  <h4>数据库</h4>
                  <p>MySQL, MongoDB, Milvus</p>
                  
                  <h4>AI/ML</h4>
                  <p>YOLOv10, PaddleOCR, 深度学习</p>
                </div>
              </div>
              
              <div className="card margin-top--md">
                <div className="card__header">
                  <h3>📞 联系方式</h3>
                </div>
                <div className="card__body">
                  <p><strong>学校：</strong>浙江大学</p>
                  <p><strong>专业：</strong>生物医学工程</p>
                  <p><strong>邮箱：</strong>486502970@qq.com</p>
                  <p><strong>GitHub：</strong><a href="https://github.com/Bubblevan">@Bubblevan</a></p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
