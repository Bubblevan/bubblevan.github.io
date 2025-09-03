import React, { useEffect, useState } from 'react';
import styles from './styles.module.css';

export interface DocumentMetadataProps {
  className?: string;
}

export default function DocumentMetadata({ className }: DocumentMetadataProps): JSX.Element {
  const [metadata, setMetadata] = useState({
    wordCount: 0,
    codeLines: 0,
    readingTime: 0,
  });

  useEffect(() => {
    // 计算文档元数据
    const calculateMetadata = () => {
      const content = document.querySelector('main') || document.body;
      if (!content) return;

      // 计算字数（中文字符）
      const text = content.textContent || '';
      const chineseChars = text.match(/[\u4e00-\u9fa5]/g) || [];
      const wordCount = chineseChars.length;

      // 计算代码行数
      const codeBlocks = content.querySelectorAll('pre code, .prism-code');
      let codeLines = 0;
      codeBlocks.forEach(block => {
        const lines = (block.textContent || '').split('\n').length;
        codeLines += lines;
      });

      // 计算预计阅读时间（按每分钟300字计算）
      const readingTime = Math.ceil(wordCount / 300);

      setMetadata({ wordCount, codeLines, readingTime });
    };

    // 延迟计算，确保内容已加载
    const timer = setTimeout(calculateMetadata, 100);
    return () => clearTimeout(timer);
  }, []);

  if (metadata.wordCount === 0) {
    return null;
  }

  return (
    <div className={styles.metadata}>
      <span className={styles.metadataItem}>
        <span className={styles.icon}>📝</span>
        约 {metadata.wordCount} 个字
      </span>
      <span className={styles.metadataItem}>
        <span className={styles.icon}>&lt;/&gt;</span>
        {metadata.codeLines} 行代码
      </span>
      <span className={styles.metadataItem}>
        <span className={styles.icon}>⏱️</span>
        预计阅读时间 {metadata.readingTime} 分钟
      </span>
    </div>
  );
}
