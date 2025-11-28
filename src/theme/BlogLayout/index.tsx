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
    console.log('[BlogLayout Debug] ========== BlogLayout useEffect 触发 ==========');
    console.log('[BlogLayout Debug] 当前路径:', location.pathname);
    console.log('[BlogLayout Debug] isBlogPostPage:', isBlogPostPage);
    console.log('[BlogLayout Debug] 路径匹配结果:', {
      startsWithBlog: location.pathname.startsWith('/blog/'),
      isBlogRoot: !!location.pathname.match(/^\/blog\/?$/),
      isBlogPage: !!location.pathname.match(/^\/blog\/page\/\d+$/),
    });
    
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
      // 如果不是博客详情页，只清理我们创建的侧边栏（带有 data-blog-sidebar 属性的）
      // 不要删除 Docusaurus 原生的侧边栏
      console.log('[BlogLayout Debug] 非博客详情页，检查并清理我们创建的侧边栏');
      
      const timer = setTimeout(() => {
        const row = document.querySelector('.blog-wrapper .row');
        // 只检查我们创建的侧边栏（带有 data-blog-sidebar 属性）
        const ourSidebar = document.querySelector('.blog-wrapper .col.col--3[data-blog-sidebar]');
        const mainContent = row?.querySelector('main.col.col--9');
        
        console.log('[BlogLayout Debug] row 元素:', row);
        console.log('[BlogLayout Debug] ourSidebar (我们创建的):', ourSidebar);
        console.log('[BlogLayout Debug] mainContent:', mainContent);
        
        if (row) {
          const rowChildren = Array.from(row.children);
          console.log('[BlogLayout Debug] row 子元素数量:', rowChildren.length);
          rowChildren.forEach((child, index) => {
            const rect = (child as HTMLElement).getBoundingClientRect();
            const computedStyle = window.getComputedStyle(child as HTMLElement);
            const element = child as HTMLElement;
            console.log(`[BlogLayout Debug] row 子元素 ${index} 详细信息:`, {
              tagName: child.tagName,
              className: child.className,
              hasDataBlogSidebar: child.getAttribute('data-blog-sidebar'),
              // 位置信息
              left: rect.left,
              right: rect.right,
              top: rect.top,
              bottom: rect.bottom,
              width: rect.width,
              height: rect.height,
              // 布局样式
              marginLeft: computedStyle.marginLeft,
              marginRight: computedStyle.marginRight,
              marginTop: computedStyle.marginTop,
              marginBottom: computedStyle.marginBottom,
              paddingLeft: computedStyle.paddingLeft,
              paddingRight: computedStyle.paddingRight,
              paddingTop: computedStyle.paddingTop,
              paddingBottom: computedStyle.paddingBottom,
              // Flex 相关
              flex: computedStyle.flex,
              flexBasis: computedStyle.flexBasis,
              flexGrow: computedStyle.flexGrow,
              flexShrink: computedStyle.flexShrink,
              // 其他
              display: computedStyle.display,
              boxSizing: computedStyle.boxSizing,
              // Inline 样式
              inlineStyle: element.style.cssText,
            });
          });
        }
        
        if (mainContent) {
          const mainStyle = window.getComputedStyle(mainContent);
          const mainRect = mainContent.getBoundingClientRect();
          console.log('[BlogLayout Debug] mainContent 完整样式信息:', {
            className: mainContent.className,
            // 位置和尺寸
            left: mainRect.left,
            right: mainRect.right,
            top: mainRect.top,
            bottom: mainRect.bottom,
            width: mainRect.width,
            height: mainRect.height,
            offsetWidth: (mainContent as HTMLElement).offsetWidth,
            offsetHeight: (mainContent as HTMLElement).offsetHeight,
            clientWidth: mainContent.clientWidth,
            clientHeight: mainContent.clientHeight,
            // 边距
            marginLeft: mainStyle.marginLeft,
            marginRight: mainStyle.marginRight,
            marginTop: mainStyle.marginTop,
            marginBottom: mainStyle.marginBottom,
            // 内边距
            paddingLeft: mainStyle.paddingLeft,
            paddingRight: mainStyle.paddingRight,
            paddingTop: mainStyle.paddingTop,
            paddingBottom: mainStyle.paddingBottom,
            // Flex 相关
            flex: mainStyle.flex,
            flexBasis: mainStyle.flexBasis,
            flexGrow: mainStyle.flexGrow,
            flexShrink: mainStyle.flexShrink,
            // 其他
            display: mainStyle.display,
            boxSizing: mainStyle.boxSizing,
            maxWidth: mainStyle.maxWidth,
            // 类检查
            hasOffset1: mainContent.classList.contains('col--offset-1'),
            // Inline 样式
            inlinePaddingLeft: (mainContent as HTMLElement).style.paddingLeft,
            inlineStyle: (mainContent as HTMLElement).style.cssText,
          });
          
          // 检查是否有原生侧边栏存在
          const nativeSidebar = row?.querySelector('[class*="blogSidebar"]:not([data-blog-sidebar])');
          console.log('[BlogLayout Debug] nativeSidebar (原生侧边栏):', nativeSidebar);
          
          // 如果有原生侧边栏，需要移除 mainContent 的 col--offset-1 类
          if (nativeSidebar && mainContent.classList.contains('col--offset-1')) {
            console.log('[BlogLayout Debug] ⚠️ 发现 mainContent 有 col--offset-1 类，但存在原生侧边栏，移除该类');
            mainContent.classList.remove('col--offset-1');
            console.log('[BlogLayout Debug] 已移除 mainContent 的 col--offset-1 类');
            
            // 强制重置 paddingLeft，因为 col--offset-1 可能通过 CSS 设置了 paddingLeft
            // 使用 !important 确保覆盖 CSS 规则
            (mainContent as HTMLElement).style.setProperty('padding-left', '16px', 'important');
            console.log('[BlogLayout Debug] 已强制设置 paddingLeft 为 16px (important)');
            
            // 再次检查样式，确保移除成功
            setTimeout(() => {
              const updatedStyle = window.getComputedStyle(mainContent);
              const updatedRect = mainContent.getBoundingClientRect();
              console.log('[BlogLayout Debug] 移除 col--offset-1 后的 mainContent 样式:', {
                className: mainContent.className,
                left: updatedRect.left,
                width: updatedRect.width,
                marginLeft: updatedStyle.marginLeft,
                paddingLeft: updatedStyle.paddingLeft,
                flex: updatedStyle.flex,
                flexBasis: updatedStyle.flexBasis,
              });
              
              // 如果仍然异常，再次强制设置
              if (parseInt(updatedStyle.paddingLeft) > 50) {
                console.log('[BlogLayout Debug] ⚠️ paddingLeft 仍然异常，再次强制设置');
                (mainContent as HTMLElement).style.setProperty('padding-left', '16px', 'important');
              }
            }, 100);
          }
          
          // 即使没有 col--offset-1 类，也检查是否有异常的 paddingLeft
          if (nativeSidebar && !mainContent.classList.contains('col--offset-1')) {
            const currentPaddingLeft = window.getComputedStyle(mainContent).paddingLeft;
            if (parseInt(currentPaddingLeft) > 50) {
              console.log('[BlogLayout Debug] ⚠️ 虽然没有 col--offset-1 类，但发现异常的 paddingLeft:', currentPaddingLeft, '，强制重置为 16px');
              (mainContent as HTMLElement).style.setProperty('padding-left', '16px', 'important');
              
              // 延迟再次检查
              setTimeout(() => {
                const checkStyle = window.getComputedStyle(mainContent);
                if (parseInt(checkStyle.paddingLeft) > 50) {
                  console.log('[BlogLayout Debug] ⚠️ paddingLeft 仍然异常，再次强制设置');
                  (mainContent as HTMLElement).style.setProperty('padding-left', '16px', 'important');
                }
              }, 100);
            }
          }
          
          // 检查 row 的样式，看看是否有影响布局的样式
          if (row) {
            const rowStyle = window.getComputedStyle(row);
            const rowRect = row.getBoundingClientRect();
            console.log('[BlogLayout Debug] row 容器样式:', {
              className: row.className,
              width: rowRect.width,
              paddingLeft: rowStyle.paddingLeft,
              paddingRight: rowStyle.paddingRight,
              marginLeft: rowStyle.marginLeft,
              marginRight: rowStyle.marginRight,
              display: rowStyle.display,
              justifyContent: rowStyle.justifyContent,
              alignItems: rowStyle.alignItems,
            });
          }
          
          // 如果删除了我们创建的侧边栏，需要清理 mainContent 的样式
          if (ourSidebar) {
            console.log('[BlogLayout Debug] ⚠️ 发现我们创建的侧边栏，准备清理');
            // 清理 mainContent 的样式
            if ((mainContent as HTMLElement).style.paddingLeft) {
              (mainContent as HTMLElement).style.paddingLeft = '';
              console.log('[BlogLayout Debug] 已清理 mainContent 的 inline paddingLeft');
            }
          }
        }
        
        // 只删除我们创建的侧边栏
        if (ourSidebar) {
          console.log('[BlogLayout Debug] 删除我们创建的侧边栏');
          if (sidebarRootRef.current) {
            sidebarRootRef.current.unmount();
            sidebarRootRef.current = null;
          }
          ourSidebar.remove();
          console.log('[BlogLayout Debug] 我们创建的侧边栏已移除');
        } else {
          console.log('[BlogLayout Debug] 没有发现我们创建的侧边栏，保留 Docusaurus 原生侧边栏');
        }
      }, 100);
      
      if (sidebarRootRef.current) {
        sidebarRootRef.current.unmount();
        sidebarRootRef.current = null;
      }
      if (sidebarContainerRef.current?.parentNode) {
        sidebarContainerRef.current.remove();
        sidebarContainerRef.current = null;
      }
      
      return () => {
        clearTimeout(timer);
      };
    }
  }, [isBlogPostPage, location.pathname]);

  return (
    <>
      <BlogLayout {...props} />
    </>
  );
}
