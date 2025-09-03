import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

export interface HighlightBlockProps {
  type?: 'info' | 'warning' | 'success' | 'error' | 'note' | 'tip' | 'question';
  title?: string;
  icon?: string;
  children: React.ReactNode;
  className?: string;
}

export default function HighlightBlock({
  type = 'info',
  title,
  icon,
  children,
  className,
}: HighlightBlockProps): JSX.Element {
  const getDefaultIcon = () => {
    switch (type) {
      case 'warning':
        return '⚠️';
      case 'success':
        return '✅';
      case 'error':
        return '❌';
      case 'note':
        return '📝';
      case 'tip':
        return '💡';
      case 'question':
        return '❓';
      default:
        return 'ℹ️';
    }
  };

  const displayIcon = icon || getDefaultIcon();

  return (
    <div className={clsx(styles.highlightBlock, styles[type], className)}>
      <div className={styles.header}>
        <span className={styles.icon}>{displayIcon}</span>
        {title && <span className={styles.title}>{title}</span>}
      </div>
      <div className={styles.content}>{children}</div>
    </div>
  );
}

// 预定义的组件变体
export function InfoBlock(props: Omit<HighlightBlockProps, 'type'>) {
  return <HighlightBlock {...props} type="info" />;
}

export function WarningBlock(props: Omit<HighlightBlockProps, 'type'>) {
  return <HighlightBlock {...props} type="warning" />;
}

export function SuccessBlock(props: Omit<HighlightBlockProps, 'type'>) {
  return <HighlightBlock {...props} type="success" />;
}

export function ErrorBlock(props: Omit<HighlightBlockProps, 'type'>) {
  return <HighlightBlock {...props} type="error" />;
}

export function NoteBlock(props: Omit<HighlightBlockProps, 'type'>) {
  return <HighlightBlock {...props} type="note" />;
}

export function TipBlock(props: Omit<HighlightBlockProps, 'type'>) {
  return <HighlightBlock {...props} type="tip" />;
}

export function QuestionBlock(props: Omit<HighlightBlockProps, 'type'>) {
  return <HighlightBlock {...props} type="question" />;
}
