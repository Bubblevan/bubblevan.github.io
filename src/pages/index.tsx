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

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="包博文 - 个人网站"
      description="浙江大学学生，全栈开发工程师">

      <HeroSection />
      <TechStackMarquee />

    </Layout>
  );
}
