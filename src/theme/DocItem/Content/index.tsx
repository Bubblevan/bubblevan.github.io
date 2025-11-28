import React, {type ReactNode, useEffect, useState} from 'react';
import Content from '@theme-original/DocItem/Content';
import type ContentType from '@theme/DocItem/Content';
import type {WrapperProps} from '@docusaurus/types';
import styles from './styles.module.css';

type Props = WrapperProps<typeof ContentType>;

export default function ContentWrapper(props: Props): ReactNode {
  const [readingTime, setReadingTime] = useState<number | null>(null);

  useEffect(() => {
    // 计算阅读时间
    const calculateReadingTime = () => {
      const content = document.querySelector('[class*="docItemContainer"] [class*="markdown"], [class*="docItemContainer"] .markdown');
      if (!content) return;

      // 计算字数（中文字符和英文单词）
      const text = content.textContent || '';
      const chineseChars = text.match(/[\u4e00-\u9fa5]/g) || [];
      const englishWords = text.match(/[a-zA-Z]+/g) || [];
      // 中文字符按1字计算，英文单词按平均5字符计算
      const wordCount = chineseChars.length + Math.ceil(englishWords.join('').length / 5);

      // 计算预计阅读时间（按每分钟300字计算，最少1分钟）
      const time = Math.max(1, Math.ceil(wordCount / 300));
      setReadingTime(time);
    };

    // 延迟计算，确保内容已加载
    const timer = setTimeout(calculateReadingTime, 200);
    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      {readingTime !== null && (
        <div className={styles.readingTime}>
          <span className={styles.readingTimeIcon}>⏱️</span>
          <span className={styles.readingTimeText}>{readingTime} 分钟阅读</span>
        </div>
      )}
      <Content {...props} />
    </>
  );
}
