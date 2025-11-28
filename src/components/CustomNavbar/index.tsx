import React, { useState, useMemo } from 'react';
import { useColorMode } from '@docusaurus/theme-common';
import { useLocation } from '@docusaurus/router';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import { usePluginData } from '@docusaurus/useGlobalData';
import clsx from 'clsx';
import styles from './styles.module.css';

interface SearchResult {
  title: string;
  url: string;
  type: 'blog' | 'doc';
  excerpt?: string;
}

export default function CustomNavbar(): JSX.Element {
  const { colorMode, setColorMode } = useColorMode();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const location = useLocation();
  const { siteConfig } = useDocusaurusContext();

  // 获取博客和文档数据
  const blogData = usePluginData('docusaurus-plugin-content-blog') as {
    posts: any[];
  } | undefined;
  const docsData = usePluginData('docusaurus-plugin-content-docs') as any;

  // 准备搜索数据
  const searchableData = useMemo(() => {
    const data: SearchResult[] = [];
    
    // 添加博客文章
    if (blogData?.posts) {
      blogData.posts.forEach((post: any) => {
        data.push({
          title: post.metadata?.title || post.title || '',
          url: post.metadata?.permalink || post.permalink || '',
          type: 'blog',
          excerpt: post.metadata?.description || post.description || '',
        });
      });
    }
    
    // 添加文档
    if (docsData?.versions?.[0]?.docs) {
      docsData.versions[0].docs.forEach((doc: any) => {
        if (doc.id && doc.permalink) {
          data.push({
            title: doc.title || doc.id,
            url: doc.permalink,
            type: 'doc',
            excerpt: doc.description || '',
          });
        }
      });
    }
    
    return data;
  }, [blogData, docsData]);

  const toggleColorMode = () => {
    setColorMode(colorMode === 'dark' ? 'light' : 'dark');
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }
    
    const query = searchQuery.toLowerCase().trim();
    const results = searchableData.filter((item) => {
      const titleMatch = item.title.toLowerCase().includes(query);
      const excerptMatch = item.excerpt?.toLowerCase().includes(query);
      return titleMatch || excerptMatch;
    }).slice(0, 10); // 限制最多显示10个结果
    
    setSearchResults(results);
    setShowResults(results.length > 0);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    
    if (!value.trim()) {
      setSearchResults([]);
      setShowResults(false);
    } else {
      handleSearch(e as any);
    }
  };

  const handleResultClick = (url: string) => {
    setShowResults(false);
    setSearchQuery('');
    window.location.href = url;
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

          <div className={styles.quickLinks}>
            <Link
              to="/blog"
              className={styles.quickLink}
            >
              📝 技术博客
            </Link>
          </div>
          
          <div className={styles.searchContainer}>
            <form onSubmit={handleSearch} className={styles.searchForm}>
              <span className={styles.searchIcon}>🔍</span>
              <input
                type="text"
                placeholder="搜索博客和文档..."
                value={searchQuery}
                onChange={handleSearchChange}
                onFocus={() => {
                  if (searchResults.length > 0) {
                    setShowResults(true);
                  }
                }}
                onBlur={() => {
                  // 延迟隐藏，以便点击结果
                  setTimeout(() => setShowResults(false), 200);
                }}
                className={styles.searchInput}
              />
            </form>
            {showResults && searchResults.length > 0 && (
              <div className={styles.searchResults}>
                {searchResults.map((result, index) => (
                  <div
                    key={index}
                    className={styles.searchResultItem}
                    onClick={() => handleResultClick(result.url)}
                    onMouseDown={(e) => e.preventDefault()} // 防止 blur 事件
                  >
                    <div className={styles.searchResultTitle}>
                      {result.type === 'blog' ? '📝' : '📚'} {result.title}
                    </div>
                    {result.excerpt && (
                      <div className={styles.searchResultExcerpt}>{result.excerpt}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          
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
