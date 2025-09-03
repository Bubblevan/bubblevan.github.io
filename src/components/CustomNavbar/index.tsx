import React, { useState } from 'react';
import { useColorMode } from '@docusaurus/theme-common';
import { useLocation } from '@docusaurus/router';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import clsx from 'clsx';
import styles from './styles.module.css';

export default function CustomNavbar(): JSX.Element {
  const { colorMode, setColorMode } = useColorMode();
  const [searchQuery, setSearchQuery] = useState('');
  const location = useLocation();
  const { siteConfig } = useDocusaurusContext();



  const toggleColorMode = () => {
    setColorMode(colorMode === 'dark' ? 'light' : 'dark');
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // 这里可以实现搜索功能
    console.log('搜索:', searchQuery);
  };

  const isActive = (path: string) => {
    return location.pathname.startsWith(path);
  };

  return (
    <div className={styles.customNavbar}>
      {/* 第一行：笔记本标题和功能按钮 */}
      <div className={styles.topRow}>
        <div className={styles.leftSection}>
          <span className={styles.notebookIcon}>📓</span>
          <span className={styles.notebookTitle}>Bubblevan的笔记本</span>
        </div>
        
        <div className={styles.rightSection}>
          <button
            className={styles.themeToggle}
            onClick={toggleColorMode}
            aria-label="切换主题"
          >
            {colorMode === 'dark' ? '☀️' : '🌙'}
          </button>
          
          <form onSubmit={handleSearch} className={styles.searchForm}>
            <span className={styles.searchIcon}>🔍</span>
            <input
              type="text"
              placeholder="搜索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
          </form>
          
          <Link
            href="https://github.com/Bubblevan"
            className={styles.githubLink}
            target="_blank"
            rel="noopener noreferrer"
          >
            <span className={styles.githubIcon}>⭐</span>
            <span className={styles.githubText}>Bubblevan/Notebook</span>
          </Link>
        </div>
      </div>

      {/* 第二行：导航链接 */}
      <div className={styles.bottomRow}>
        <nav className={styles.navigation}>
          <Link
            to="/"
            className={clsx(styles.navLink, { [styles.active]: location.pathname === '/' })}
          >
            🏠 主页
          </Link>
          <Link
            to="/docs/undergraduate-notes/intro"
            className={clsx(styles.navLink, { [styles.active]: isActive('/docs/undergraduate-notes') })}
          >
            📚 本科笔记
          </Link>
          <Link
            to="/docs/bagu-infrastructure/intro"
            className={clsx(styles.navLink, { [styles.active]: isActive('/docs/bagu-infrastructure') })}
          >
            🏗️ 八股基建
          </Link>
          <Link
            to="/docs/projects/intro"
            className={clsx(styles.navLink, { [styles.active]: isActive('/docs/projects') })}
          >
            🚀 项目介绍
          </Link>
          <Link
            to="/docs/research/intro"
            className={clsx(styles.navLink, { [styles.active]: isActive('/docs/research') })}
          >
            🔬 科研经历
          </Link>
          <Link
            to="/docs/self-study/intro"
            className={clsx(styles.navLink, { [styles.active]: isActive('/docs/self-study') })}
          >
            📖 自学笔记
          </Link>
          <Link
            to="/docs/paper-reading/intro"
            className={clsx(styles.navLink, { [styles.active]: isActive('/docs/paper-reading') })}
          >
            📄 论文阅读
          </Link>
        </nav>
      </div>
    </div>
  );
}
