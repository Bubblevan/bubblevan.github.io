import React, {type ReactNode, useEffect, useRef} from 'react';
import BlogLayout from '@theme-original/BlogLayout';
import type BlogLayoutType from '@theme/BlogLayout';
import type {WrapperProps} from '@docusaurus/types';
import {useLocation} from '@docusaurus/router';
import BlogSidebar from '@theme/BlogSidebar';
import {createRoot, type Root} from 'react-dom/client';

type Props = WrapperProps<typeof BlogLayoutType>;

export default function BlogLayoutWrapper(props: Props): ReactNode {
  const location = useLocation();
  const isBlogPostPage = location.pathname.startsWith('/blog/') && 
                         !location.pathname.match(/^\/blog\/?$/) &&
                         !location.pathname.match(/^\/blog\/page\/\d+$/);
  const sidebarRootRef = useRef<Root | null>(null);
  const sidebarContainerRef = useRef<HTMLDivElement | null>(null);

  // 在详情页动态添加左侧侧边栏到 row 中
  useEffect(() => {
    if (isBlogPostPage && typeof window !== 'undefined') {
      const timer = setTimeout(() => {
        const row = document.querySelector('.blog-wrapper .row');
        // 检查是否已经有侧边栏（通过 data-blog-sidebar 属性或 blogSidebar 类）
        const existingSidebarByAttr = document.querySelector('.blog-wrapper .col.col--3[data-blog-sidebar]');
        const existingSidebarByClass = document.querySelector('.blog-wrapper [class*="blogSidebar"]') ||
                                       row?.querySelector('.col.col--3 [class*="blogSidebar"]');
        const existingSidebar = existingSidebarByAttr || existingSidebarByClass;
        const mainContent = row?.querySelector('main.col.col--9');
        
        // 如果已经有侧边栏（可能是从列表页带来的），先移除它
        if (existingSidebar && existingSidebar.parentNode) {
          // 检查是否是我们的侧边栏容器
          if (existingSidebar.getAttribute('data-blog-sidebar')) {
            // 如果是我们的容器，先卸载 React 根
            if (sidebarRootRef.current) {
              sidebarRootRef.current.unmount();
              sidebarRootRef.current = null;
            }
          }
          existingSidebar.remove();
        }
        
        if (row && mainContent) {
          // 创建左侧侧边栏容器
          const sidebarContainer = document.createElement('div');
          sidebarContainer.className = 'col col--3';
          sidebarContainer.setAttribute('data-blog-sidebar', 'true');
          sidebarContainerRef.current = sidebarContainer;
          
          // 插入到 row 的第一个位置（在 main 之前）
          row.insertBefore(sidebarContainer, mainContent);
          
          // 使用 React 18+ createRoot 渲染侧边栏
          try {
            const root = createRoot(sidebarContainer);
            sidebarRootRef.current = root;
            root.render(<BlogSidebar />);
            
            // 等待 React 渲染完成后再调整
            setTimeout(() => {
              if (mainContent) {
                // 检查是否有侧边栏
                const sidebar = row.querySelector('.col.col--3[data-blog-sidebar]');
                if (sidebar) {
                  // 移除 mainContent 的 offset 类，因为我们已经有了侧边栏
                  if (mainContent.classList.contains('col--offset-1')) {
                    mainContent.classList.remove('col--offset-1');
                  }
                  (mainContent as HTMLElement).style.paddingLeft = '1rem';
                }
              }
            }, 200);
          } catch (e) {
            // 静默处理错误
          }
        }
      }, 100);
      
      return () => {
        clearTimeout(timer);
        // 清理
        if (sidebarRootRef.current) {
          sidebarRootRef.current.unmount();
          sidebarRootRef.current = null;
        }
        if (sidebarContainerRef.current?.parentNode) {
          sidebarContainerRef.current.remove();
          sidebarContainerRef.current = null;
        }
      };
    } else {
      // 如果不是博客详情页，清理可能存在的侧边栏
      if (sidebarRootRef.current) {
        sidebarRootRef.current.unmount();
        sidebarRootRef.current = null;
      }
      if (sidebarContainerRef.current?.parentNode) {
        sidebarContainerRef.current.remove();
        sidebarContainerRef.current = null;
      }
    }
  }, [isBlogPostPage, location.pathname]);

  return (
    <>
      <BlogLayout {...props} />
    </>
  );
}
