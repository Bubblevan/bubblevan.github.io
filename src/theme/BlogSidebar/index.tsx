import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { JSX } from 'react';
import { useAllPluginInstancesData, usePluginData } from '@docusaurus/useGlobalData';
import styles from './styles.module.css';

// 安全的链接组件，使用普通 <a> 标签，但尝试使用 Docusaurus 导航
function SafeLink({ to, className, children }: { to: string; className?: string; children: React.ReactNode }) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    // 尝试使用 Docusaurus 的导航（如果可用）
    if (typeof window !== 'undefined' && (window as any).docusaurus?.navigate) {
      e.preventDefault();
      (window as any).docusaurus.navigate(to);
    } else if (typeof window !== 'undefined' && (window as any).__docusaurus?.router) {
      e.preventDefault();
      (window as any).__docusaurus.router.push(to);
    }
    // 如果没有 Docusaurus 导航，使用默认的浏览器导航
  };
  
  return (
    <a href={to} className={className} onClick={handleClick}>
      {children}
    </a>
  );
}

const INITIAL_LOAD_COUNT = 10; // 初始加载数量
const LOAD_MORE_COUNT = 10; // 每次加载更多时的数量
const ITEM_HEIGHT = 60; // 每个列表项的估算高度（px）

export default function BlogSidebar(): JSX.Element | null {
  // 所有 hooks 必须在组件顶部，不能在条件返回之后
  // 使用 window.location 作为 location 的源，避免 Router 上下文问题
  const [location, setLocation] = useState<{ pathname: string }>(() => ({
    pathname: typeof window !== 'undefined' ? window.location.pathname : ''
  }));
  
  // 监听路径变化
  useEffect(() => {
    const updateLocation = () => {
      if (typeof window !== 'undefined') {
        setLocation({ pathname: window.location.pathname });
      }
    };
    
    // 初始设置
    updateLocation();
    
    // 监听 popstate 事件（浏览器前进/后退）
    window.addEventListener('popstate', updateLocation);
    
    // 定期检查路径变化（作为备用方案）
    const interval = setInterval(updateLocation, 100);
    
    return () => {
      window.removeEventListener('popstate', updateLocation);
      clearInterval(interval);
    };
  }, []);
  const allPluginData = useAllPluginInstancesData('docusaurus-plugin-content-blog');
  const blogData = usePluginData('docusaurus-plugin-content-blog') as {
    posts: any[];
    postNum: number;
    tagNum: number;
  } | undefined;
  
  const sidebarRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null); // 实际的滚动容器引用
  const [allPosts, setAllPosts] = useState<any[]>([]);
  const [visibleCount, setVisibleCount] = useState(INITIAL_LOAD_COUNT);
  const [isLoading, setIsLoading] = useState(false);
  
  // 使用 useEffect 异步获取所有博客数据
  useEffect(() => {
    async function fetchAllBlogPosts() {
      try {
        // 首先尝试从 blogData 获取
        if (blogData?.posts && Array.isArray(blogData.posts)) {
          const posts = blogData.posts.map((post: any) => ({
            id: post.id,
            title: post.metadata?.title || post.title,
            permalink: post.metadata?.permalink || post.permalink,
            date: post.metadata?.date || post.date,
          })).sort((a: any, b: any) => {
            return new Date(b.date).getTime() - new Date(a.date).getTime();
          });
          setAllPosts(posts);
          return;
        }
        
        // 如果 blogData 没有数据，尝试从 allPluginData 获取
        if (allPluginData && typeof allPluginData === 'object' && !Array.isArray(allPluginData)) {
          const keys = Object.keys(allPluginData);
          if (keys.length > 0) {
            const pluginData = allPluginData[keys[0]] as any;
            if (pluginData?.posts && Array.isArray(pluginData.posts)) {
              const posts = pluginData.posts.map((post: any) => ({
                id: post.id,
                title: post.metadata?.title || post.title,
                permalink: post.metadata?.permalink || post.permalink,
                date: post.metadata?.date || post.date,
              })).sort((a: any, b: any) => {
                return new Date(b.date).getTime() - new Date(a.date).getTime();
              });
              setAllPosts(posts);
              return;
            }
          }
        }
      } catch (e) {
        // 静默处理错误
      }
    }
    
    fetchAllBlogPosts();
  }, [blogData, allPluginData]);
  
  // 计算初始可见数量（基于侧边栏高度）
  useEffect(() => {
    if (sidebarRef.current && allPosts.length > 0) {
      const sidebarHeight = sidebarRef.current.clientHeight;
      const calculatedCount = Math.ceil(sidebarHeight / ITEM_HEIGHT) + 2; // 多加载2个作为缓冲
      setVisibleCount(Math.min(calculatedCount, INITIAL_LOAD_COUNT));
    }
  }, [allPosts.length]);

  // 处理滚动事件 - 懒加载
  const handleScroll = useCallback((e: Event) => {
    if (isLoading) return;
    
    const target = e.target as HTMLElement;
    if (!target) return;

    const scrollTop = target.scrollTop;
    const scrollHeight = target.scrollHeight;
    const clientHeight = target.clientHeight;

    // 当滚动到底部80%时，加载更多
    if (scrollTop + clientHeight >= scrollHeight * 0.8) {
      if (visibleCount < allPosts.length) {
        setIsLoading(true);
        // 使用setTimeout模拟加载延迟，避免过快加载
        setTimeout(() => {
          setVisibleCount((prev) => Math.min(prev + LOAD_MORE_COUNT, allPosts.length));
          setIsLoading(false);
        }, 100);
      }
    }
  }, [visibleCount, allPosts.length, isLoading]);

  // 绑定滚动事件 - 修复：绑定到实际的滚动容器（blogSidebarList）
  useEffect(() => {
    const scrollContainer = listRef.current;
    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', handleScroll, { passive: true });
      return () => scrollContainer.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);
  
  // 点击加载更多的备用方案
  const handleLoadMore = useCallback(() => {
    if (!isLoading && visibleCount < allPosts.length) {
      setIsLoading(true);
      setTimeout(() => {
        setVisibleCount((prev) => Math.min(prev + LOAD_MORE_COUNT, allPosts.length));
        setIsLoading(false);
      }, 100);
    }
  }, [visibleCount, allPosts.length, isLoading]);


  // 按年份分组博客
  const postsByYear = useMemo(() => {
    const grouped: { [year: string]: typeof allPosts } = {};
    allPosts.forEach((post) => {
      const year = new Date(post.date).getFullYear().toString();
      if (!grouped[year]) {
        grouped[year] = [];
      }
      grouped[year].push(post);
    });
    // 按年份倒序排序
    return Object.keys(grouped)
      .sort((a, b) => parseInt(b) - parseInt(a))
      .map((year) => ({ year, posts: grouped[year] }));
  }, [allPosts]);

  // 计算可见的年份和文章
  const visibleYearPosts = useMemo(() => {
    let currentCount = 0;
    const result: Array<{ year: string; posts: typeof allPosts; visiblePosts: typeof allPosts }> = [];
    
    for (const { year, posts } of postsByYear) {
      if (currentCount >= visibleCount) break;
      
      const remaining = visibleCount - currentCount;
      const visiblePosts = posts.slice(0, remaining);
      result.push({ year, posts, visiblePosts });
      currentCount += visiblePosts.length;
    }
    
    return result;
  }, [postsByYear, visibleCount]);

  const hasMore = visibleCount < allPosts.length;
  
  // 条件返回必须在所有 hooks 之后
  if (allPosts.length === 0) {
    return null;
  }
  
  return (
    <div className={styles.blogSidebar}>
      <h3 className={styles.blogSidebarTitle}>所有博客</h3>
      <div
        ref={listRef}
        className={styles.blogSidebarList}
        style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}
      >
        {visibleYearPosts.map(({ year, visiblePosts: yearPosts }) => (
          <div key={year} className={styles.blogSidebarYearGroup}>
            <h4 className={styles.blogSidebarYearTitle}>{year} 年</h4>
            {yearPosts.map((post) => {
              const isActive = location.pathname === post.permalink;
              return (
                <SafeLink
                  key={post.id}
                  to={post.permalink}
                  className={`${styles.blogSidebarItem} ${isActive ? styles.blogSidebarItemActive : ''}`}
                >
                  <div className={styles.blogSidebarItemTitle}>{post.title}</div>
                  <div className={styles.blogSidebarItemDate}>
                    {new Date(post.date).toLocaleDateString('zh-CN', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>
                </SafeLink>
              );
            })}
          </div>
        ))}
        {hasMore && (
          <div 
            className={styles.blogSidebarLoading}
            onClick={handleLoadMore}
            style={{ cursor: 'pointer', userSelect: 'none' }}
          >
            {isLoading ? '加载中...' : `查看剩余 ${allPosts.length - visibleCount} 篇博客`}
          </div>
        )}
      </div>
    </div>
  );
}

