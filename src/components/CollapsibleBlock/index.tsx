import React, { useState } from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

export interface CollapsibleBlockProps {
  title: string;
  icon?: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  className?: string;
}

export default function CollapsibleBlock({
  title,
  icon = '📋',
  children,
  defaultExpanded = false,
  className,
}: CollapsibleBlockProps): JSX.Element {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className={clsx(styles.collapsibleBlock, className)}>
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <span className={styles.icon}>{icon}</span>
          <span className={styles.title}>{title}</span>
        </div>
        <button
          className={clsx(styles.toggleButton, { [styles.expanded]: isExpanded })}
          onClick={toggleExpanded}
          aria-label={isExpanded ? '收起内容' : '展开内容'}
        >
          <span className={styles.toggleIcon}>^</span>
        </button>
      </div>
      <div className={clsx(styles.content, { [styles.expanded]: isExpanded })}>
        {children}
      </div>
    </div>
  );
}