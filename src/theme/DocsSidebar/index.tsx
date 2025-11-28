import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { JSX } from 'react';
import { usePluginData, useAllPluginInstancesData } from '@docusaurus/useGlobalData';
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

interface SidebarItem {
  type: 'doc' | 'category';
  id?: string;
  label?: string;
  items?: SidebarItem[];
  href?: string;
}

export default function DocsSidebar(): JSX.Element | null {
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

  const listRef = useRef<HTMLDivElement>(null); // 实际的滚动容器引用
  const [visibleCount, setVisibleCount] = useState(INITIAL_LOAD_COUNT);
  const [isLoading, setIsLoading] = useState(false);
  
  // 从全局数据获取所有文档
  const docsData = usePluginData('docusaurus-plugin-content-docs') as any;
  const allDocsInstances = useAllPluginInstancesData('docusaurus-plugin-content-docs') as any;
  
  // 扁平化所有文档项
  const flattenedItems = useMemo(() => {
    // 尝试多种方式获取文档数据
    let docs: any[] = [];
    
    // 首先尝试从 docsData 获取
    if (docsData?.versions?.[0]?.docs) {
      docs = docsData.versions[0].docs;
    } else if (docsData?.docs) {
      docs = docsData.docs;
    } else if (allDocsInstances && typeof allDocsInstances === 'object' && !Array.isArray(allDocsInstances)) {
      // 尝试从 allDocsInstances 获取
      const keys = Object.keys(allDocsInstances);
      if (keys.length > 0) {
        const instanceData = allDocsInstances[keys[0]] as any;
        if (instanceData?.versions?.[0]?.docs) {
          docs = instanceData.versions[0].docs;
        } else if (instanceData?.docs) {
          docs = instanceData.docs;
        }
      }
    }
    
    if (!docs || docs.length === 0) return [];
    
    const result: Array<{ id: string; label: string; href: string }> = [];
    
    docs.forEach((doc: any) => {
      if (doc.id && (doc.permalink || doc.path)) {
        result.push({
          id: doc.id,
          label: doc.title || doc.id,
          href: doc.permalink || doc.path || `/docs/${doc.id}`,
        });
      }
    });
    
    // 按 permalink 排序
    return result.sort((a, b) => a.href.localeCompare(b.href));
  }, [docsData, allDocsInstances]);

  // 计算初始可见数量（基于侧边栏高度）
  useEffect(() => {
    if (listRef.current && flattenedItems.length > 0) {
      const sidebarHeight = listRef.current.clientHeight;
      const calculatedCount = Math.ceil(sidebarHeight / ITEM_HEIGHT) + 2; // 多加载2个作为缓冲
      setVisibleCount(Math.min(calculatedCount, INITIAL_LOAD_COUNT));
    }
  }, [flattenedItems.length]);

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
      if (visibleCount < flattenedItems.length) {
        setIsLoading(true);
        // 使用setTimeout模拟加载延迟，避免过快加载
        setTimeout(() => {
          setVisibleCount((prev) => Math.min(prev + LOAD_MORE_COUNT, flattenedItems.length));
          setIsLoading(false);
        }, 100);
      }
    }
  }, [visibleCount, flattenedItems.length, isLoading]);

  // 绑定滚动事件 - 修复：绑定到实际的滚动容器（docsSidebarList）
  useEffect(() => {
    const scrollContainer = listRef.current;
    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', handleScroll, { passive: true });
      return () => scrollContainer.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);
  
  // 点击加载更多的备用方案
  const handleLoadMore = useCallback(() => {
    if (!isLoading && visibleCount < flattenedItems.length) {
      setIsLoading(true);
      setTimeout(() => {
        setVisibleCount((prev) => Math.min(prev + LOAD_MORE_COUNT, flattenedItems.length));
        setIsLoading(false);
      }, 100);
    }
  }, [visibleCount, flattenedItems.length, isLoading]);

  // 调试：检查 docs 页面的DOM结构和CSS样式
  useEffect(() => {
    if (typeof window !== 'undefined' && location.pathname.startsWith('/docs/')) {
      const docMainContainer = document.querySelector('[class*="docMainContainer"], .docMainContainer_gTbr');
      const row = docMainContainer?.querySelector('.row, [class*="row"]');
      const leftSidebar = docMainContainer?.querySelector('.col.col--3[data-docs-sidebar]');
      const mainContent = docMainContainer?.querySelector('main, [class*="docItemContainer"]');
      const rightTOC = docMainContainer?.querySelector('.col.col--2, [class*="tableOfContents"]');
      
      console.log('[DocsLayout Debug] ========== 开始调试 ==========');
      console.log('[DocsLayout Debug] 当前路径:', location.pathname);
      console.log('[DocsLayout Debug] docMainContainer:', docMainContainer);
      console.log('[DocsLayout Debug] row:', row);
      console.log('[DocsLayout Debug] leftSidebar (.col.col--3[data-docs-sidebar]):', leftSidebar);
      console.log('[DocsLayout Debug] mainContent:', mainContent);
      console.log('[DocsLayout Debug] rightTOC:', rightTOC);
      console.log('[DocsLayout Debug] flattenedItems 数量:', flattenedItems.length);
      
      if (row) {
        const children = Array.from(row.children);
        console.log('[DocsLayout Debug] row 子元素数量:', children.length);
        children.forEach((child, index) => {
          const childStyle = window.getComputedStyle(child);
          console.log(`[DocsLayout Debug] row 子元素 ${index}:`, {
            tagName: child.tagName,
            className: child.className,
            width: childStyle.width,
            flex: childStyle.flex,
            order: childStyle.order,
            left: child.getBoundingClientRect().left,
          });
        });
      }
      
      if (leftSidebar) {
        const sidebarStyle = window.getComputedStyle(leftSidebar);
        console.log('[DocsLayout Debug] ========== 左侧侧边栏样式 ==========');
        console.log('[DocsLayout Debug] leftSidebar computed width:', sidebarStyle.width);
        console.log('[DocsLayout Debug] leftSidebar computed flex:', sidebarStyle.flex);
        console.log('[DocsLayout Debug] leftSidebar computed max-width:', sidebarStyle.maxWidth);
        console.log('[DocsLayout Debug] leftSidebar computed min-width:', sidebarStyle.minWidth);
        console.log('[DocsLayout Debug] leftSidebar computed overflow:', sidebarStyle.overflow);
        console.log('[DocsLayout Debug] leftSidebar computed box-sizing:', sidebarStyle.boxSizing);
        console.log('[DocsLayout Debug] leftSidebar left (getBoundingClientRect):', leftSidebar.getBoundingClientRect().left);
        console.log('[DocsLayout Debug] leftSidebar right (getBoundingClientRect):', leftSidebar.getBoundingClientRect().right);
      }
      
      if (mainContent) {
        const mainStyle = window.getComputedStyle(mainContent);
        console.log('[DocsLayout Debug] ========== 主内容区域样式 ==========');
        console.log('[DocsLayout Debug] mainContent classes:', mainContent.className);
        console.log('[DocsLayout Debug] mainContent computed width:', mainStyle.width);
        console.log('[DocsLayout Debug] mainContent computed flex:', mainStyle.flex);
        console.log('[DocsLayout Debug] mainContent computed padding-left:', mainStyle.paddingLeft);
        console.log('[DocsLayout Debug] mainContent computed margin-left:', mainStyle.marginLeft);
        console.log('[DocsLayout Debug] mainContent computed left (getBoundingClientRect):', mainContent.getBoundingClientRect().left);
        console.log('[DocsLayout Debug] mainContent computed right (getBoundingClientRect):', mainContent.getBoundingClientRect().right);
      }
      
      if (docMainContainer) {
        const containerStyle = window.getComputedStyle(docMainContainer);
        console.log('[DocsLayout Debug] ========== Container样式 ==========');
        console.log('[DocsLayout Debug] docMainContainer computed padding-left:', containerStyle.paddingLeft);
        console.log('[DocsLayout Debug] docMainContainer computed margin-left:', containerStyle.marginLeft);
        console.log('[DocsLayout Debug] docMainContainer computed left (getBoundingClientRect):', docMainContainer.getBoundingClientRect().left);
        console.log('[DocsLayout Debug] docMainContainer computed right (getBoundingClientRect):', docMainContainer.getBoundingClientRect().right);
      }
      
      if (rightTOC) {
        const tocStyle = window.getComputedStyle(rightTOC);
        console.log('[DocsLayout Debug] ========== 右侧TOC样式 ==========');
        console.log('[DocsLayout Debug] rightTOC computed width:', tocStyle.width);
        console.log('[DocsLayout Debug] rightTOC computed flex:', tocStyle.flex);
        console.log('[DocsLayout Debug] rightTOC left (getBoundingClientRect):', rightTOC.getBoundingClientRect().left);
      }
      
      console.log('[DocsLayout Debug] ========== 调试结束 ==========');
    }
  }, [location.pathname, flattenedItems.length]);

  // 当前可见的文档项
  const visibleItems = flattenedItems.slice(0, visibleCount);
  const hasMore = visibleCount < flattenedItems.length;
  
  // 条件返回必须在所有 hooks 之后
  if (flattenedItems.length === 0) {
    return null;
  }
  
  return (
    <div className={styles.docsSidebar}>
      <h3 className={styles.docsSidebarTitle}>文档目录</h3>
      <div
        ref={listRef}
        className={styles.docsSidebarList}
        style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}
      >
        {visibleItems.map((item) => {
          const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
          return (
            <SafeLink
              key={item.id}
              to={item.href}
              className={`${styles.docsSidebarItem} ${isActive ? styles.docsSidebarItemActive : ''}`}
            >
              <div className={styles.docsSidebarItemTitle}>{item.label}</div>
            </SafeLink>
          );
        })}
        {hasMore && (
          <div 
            className={styles.docsSidebarLoading}
            onClick={handleLoadMore}
            style={{ cursor: 'pointer', userSelect: 'none' }}
          >
            {isLoading ? '加载中...' : `查看剩余 ${flattenedItems.length - visibleCount} 篇文档`}
          </div>
        )}
      </div>
    </div>
  );
}

