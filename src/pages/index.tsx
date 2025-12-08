import type {ReactNode} from 'react';
import { useState, useEffect, useMemo } from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

import styles from './index.module.css';

function TypewriterText() {
  const [displayText, setDisplayText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showCursor, setShowCursor] = useState(true);
  const fullText = '欢迎来到Bubblevan的泡泡车';

  useEffect(() => {
    if (currentIndex < fullText.length) {
      const timer = setTimeout(() => {
        setDisplayText(prev => prev + fullText[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, 200); // 每个字符间隔200ms

      return () => clearTimeout(timer);
    } else {
      // 文字打完后，延迟隐藏光标
      const cursorTimer = setTimeout(() => {
        setShowCursor(false);
      }, 1000);

      return () => clearTimeout(cursorTimer);
    }
  }, [currentIndex, fullText]);

  // 光标闪烁效果
  useEffect(() => {
    const blinkTimer = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => clearInterval(blinkTimer);
  }, []);

  return (
    <div className={styles.typewriterContainer}>
      <span className={styles.typewriterText}>
        {displayText}
      </span>
      {currentIndex < fullText.length && showCursor && (
        <span className={styles.typewriterCursor}>|</span>
      )}
    </div>
  );
}

function HeroSection() {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const images = [
    '/img/calamity1.jpg',
    '/img/calamity2.jpg',
    '/img/calamity3.jpg'
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex(prev => (prev + 1) % images.length);
    }, 4000); // 每4秒切换一张图片

    return () => clearInterval(interval);
  }, [images.length]);

  return (
    <section className={styles.heroSection}>
      <div className={styles.heroImage}>
        {images.map((image, index) => (
          <img
            key={index}
            src={image}
            alt={`Calamity Background ${index + 1}`}
            className={`${styles.backgroundImage} ${
              index === currentImageIndex ? styles.active : ''
            }`}
          />
        ))}
      </div>
      <div className={styles.heroOverlay}>
        <div className={styles.heroContent}>
          <TypewriterText />
        </div>
      </div>
    </section>
  );
}

function TechStackMarquee() {
  const techStack = useMemo(() => {
    const context = (require as any).context('../../static/img/subjects', false, /\.svg$/);
    const items = context.keys().map((key: string) => {
      const filename = key.replace('./', '');
      const name = filename.replace('.svg', '');
      return {
        src: `/img/subjects/${filename}`,
        alt: name,
      };
    });

    return items.sort((a, b) => a.alt.localeCompare(b.alt, 'zh-Hans'));
  }, []);

  if (techStack.length === 0) {
    return null;
  }

  // 重复技术栈以实现无缝循环
  const duplicatedStack = Array.from({ length: 3 }, () => techStack).flat();

  return (
    <section className={styles.marqueeSection}>
      <div className={styles.marqueeContainer}>
        <div className={styles.marqueeTrack}>
          {duplicatedStack.map((tech, index) => (
            <div key={index} className={styles.techItem}>
              <img
                src={tech.src}
                alt={tech.alt}
                title={tech.alt}
                className={styles.techIcon}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function OfficialAccountsAndConferences() {
  const officialAccounts = [
    {
      title: '机器之心',
      url: 'https://www.jiqizhixin.com/',
    },
    {
      title: '新智元',
      url: 'https://aiera.com.cn/',
    },
    {
      title: '量子位',
      url: 'https://www.qbitai.com/',
    },
  ];

  const conferences = [
    {
      title: 'NeurIPS',
      url: 'https://neurips.cc/',
      fullName: 'Neural Information Processing Systems',
    },
    {
      title: 'ICML',
      url: 'https://icml.cc/',
      fullName: 'International Conference on Machine Learning',
    },
    {
      title: 'ICLR',
      url: 'https://iclr.cc/',
      fullName: 'International Conference on Learning Representations',
    },
  ];

  return (
    <section className={styles.knowledgeSection}>
      <div className={styles.knowledgeContainer}>
        <div className={styles.knowledgeColumn}>
          <h3 className={styles.knowledgeColumnTitle}>
            <span className={styles.knowledgeIcon}>📱</span>
            公众号
          </h3>
          <ul className={styles.knowledgeList}>
            {officialAccounts.map((item, index) => (
              <li key={index} className={styles.knowledgeItem}>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.knowledgeLink}
                >
                  <span className={styles.knowledgeLinkText}>{item.title}</span>
                  <span className={styles.knowledgeLinkArrow}>→</span>
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* <div className={styles.knowledgeColumn}>
          <h3 className={styles.knowledgeColumnTitle}>
            <span className={styles.knowledgeIcon}>🎓</span>
            三大顶会
          </h3>
          <ul className={styles.knowledgeList}>
            {conferences.map((item, index) => (
              <li key={index} className={styles.knowledgeItem}>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.knowledgeLink}
                >
                  <div className={styles.knowledgeLinkContent}>
                    <span className={styles.knowledgeLinkText}>{item.title}</span>
                    <span className={styles.knowledgeLinkDescription}>{item.fullName}</span>
                  </div>
                  <span className={styles.knowledgeLinkArrow}>→</span>
                </a>
              </li>
            ))}
          </ul>
        </div> */}
      </div>
    </section>
  );
}

function PersonalBlogs() {
  const blogs = [
    {
      title: 'Colah\'s Blog',
      url: 'https://colah.github.io/',
      description: '深度学习可视化与理解',
      author: 'Christopher Olah',
    },
    {
      title: '真理孑然',
      url: 'https://son4ta.github.io/blog/',
      description: 'Here, I Stand - 技术博客与经验分享',
      author: 'Fang C. Jie',
    },
    // 可以在这里添加更多优秀的个人博客
  ];

  return (
    <section className={styles.blogsSection}>
      <div className={styles.blogsContainer}>
        <h2 className={styles.blogsTitle}>
          <span className={styles.blogsIcon}>✨</span>
          优秀个人博客
        </h2>
        <p className={styles.blogsSubtitle}>值得关注的 Geek 和技术博客</p>
        <div className={styles.blogsList}>
          {blogs.map((blog, index) => (
            <article key={index} className={styles.blogCard}>
              <a
                href={blog.url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.blogCardLink}
              >
                <div className={styles.blogCardHeader}>
                  <h3 className={styles.blogCardTitle}>{blog.title}</h3>
                  <span className={styles.blogCardArrow}>↗</span>
                </div>
                {blog.author && (
                  <div className={styles.blogCardAuthor}>by {blog.author}</div>
                )}
                {blog.description && (
                  <p className={styles.blogCardDescription}>{blog.description}</p>
                )}
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="Bubblevan's Blog"
      description="">

      <HeroSection />
      <TechStackMarquee />
      <OfficialAccountsAndConferences />
      <PersonalBlogs />

    </Layout>
  );
}
