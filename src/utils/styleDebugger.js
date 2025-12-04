/**
 * 样式调试工具
 * 在浏览器控制台输出样式相关的调试信息
 */

export function initStyleDebugger() {
  // 只在开发环境或明确启用时运行
  if (typeof window === 'undefined') return;

  // 检查是否启用调试（可以通过URL参数 ?debug=style 启用）
  const urlParams = new URLSearchParams(window.location.search);
  const enableDebug = urlParams.get('debug') === 'style' || 
                      localStorage.getItem('styleDebugEnabled') === 'true';

  if (!enableDebug) {
    // 提供启用调试的方法
    console.log('%c🎨 样式调试工具', 'color: #2563eb; font-weight: bold; font-size: 14px;');
    console.log('%c要启用样式调试，请在控制台运行：', 'color: #64748b;');
    console.log('%clocalStorage.setItem("styleDebugEnabled", "true"); location.reload();', 
                'color: #3b82f6; font-family: monospace; background: #f1f5f9; padding: 4px;');
    return;
  }

  console.log('%c🎨 样式调试工具已启用', 'color: #2563eb; font-weight: bold; font-size: 16px;');
  console.log('=====================================');

  // 检测当前主题
  const theme = document.documentElement.getAttribute('data-theme') || 'light';
  console.log(`%c当前主题: ${theme}`, `color: ${theme === 'dark' ? '#60a5fa' : '#2563eb'}; font-weight: bold;`);

  // 检测侧边栏状态
  function checkSidebarStyles() {
    console.log('\n%c📋 侧边栏样式检查', 'color: #2563eb; font-weight: bold;');
    
    const sidebarLinks = document.querySelectorAll('.theme-doc-sidebar-menu .menu__link');
    const activeLinks = document.querySelectorAll('.theme-doc-sidebar-menu .menu__link--active');
    const parentLinks = document.querySelectorAll('.theme-doc-sidebar-menu .menu__list-item:has(.menu__link--active) > .menu__link:not(.menu__link--active)');

    console.log(`总链接数: ${sidebarLinks.length}`);
    console.log(`激活链接数: ${activeLinks.length}`);
    console.log(`父级链接数（有子项被选中）: ${parentLinks.length}`);

    activeLinks.forEach((link, index) => {
      const styles = window.getComputedStyle(link);
      const classes = link.className;
      const isParent = link.closest('.menu__list-item')?.querySelector('.menu__list') !== null;
      // 检查是否有内联样式
      const inlineStyle = link.getAttribute('style');
      // 获取所有匹配的CSS规则
      const matchedRules = [];
      if (window.getMatchedCSSRules) {
        const rules = window.getMatchedCSSRules(link);
        if (rules) {
          rules.forEach(rule => {
            if (rule.style && rule.style.backgroundColor && rule.style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
              matchedRules.push({
                selector: rule.selectorText,
                backgroundColor: rule.style.backgroundColor,
                source: rule.styleSheet?.href || 'inline'
              });
            }
          });
        }
      }
      console.log(`\n%c激活链接 ${index + 1}:`, 'color: #10b981; font-weight: bold;');
      console.log(`  文本: ${link.textContent?.trim()}`);
      console.log(`  类名: ${classes}`);
      console.log(`  是否为父级: ${isParent}`);
      console.log(`  背景色: ${styles.backgroundColor}`);
      console.log(`  背景色（计算值）: ${styles.backgroundColor}`);
      console.log(`  background-clip: ${styles.backgroundClip}`);
      console.log(`  background-origin: ${styles.backgroundOrigin}`);
      console.log(`  文字颜色: ${styles.color}`);
      console.log(`  字体粗细: ${styles.fontWeight}`);
      if (inlineStyle) {
        console.log(`  ⚠️ 内联样式: ${inlineStyle}`);
      }
      if (matchedRules.length > 0) {
        console.log(`  匹配的CSS规则（背景色）:`, matchedRules);
      }
      
      // 检查子元素（展开icon可能在这里）
      const children = link.querySelectorAll('*');
      if (children.length > 0) {
        console.log(`  子元素数量: ${children.length}`);
        children.forEach((child, childIndex) => {
          const childStyles = window.getComputedStyle(child);
          console.log(`    子元素 ${childIndex + 1}: ${child.tagName}.${child.className}`);
          console.log(`      背景色: ${childStyles.backgroundColor}`);
          console.log(`      内容: ${child.textContent?.trim() || '(空)'}`);
        });
      }
      
      // 检查父元素和兄弟元素（展开icon可能在menu__list-item的其他位置）
      const listItem = link.closest('.menu__list-item');
      if (listItem) {
        const listItemStyles = window.getComputedStyle(listItem);
        console.log(`  父元素(.menu__list-item)背景色: ${listItemStyles.backgroundColor}`);
        
        // 检查兄弟元素
        const siblings = Array.from(listItem.children).filter(child => child !== link);
        if (siblings.length > 0) {
          console.log(`  兄弟元素数量: ${siblings.length}`);
          siblings.forEach((sibling, siblingIndex) => {
            const siblingStyles = window.getComputedStyle(sibling);
            console.log(`    兄弟元素 ${siblingIndex + 1}: ${sibling.tagName}.${sibling.className}`);
            console.log(`      背景色: ${siblingStyles.backgroundColor}`);
            console.log(`      内容: ${sibling.textContent?.trim() || '(空)'}`);
          });
        }
      }
      
      console.log(`  元素:`, link);
    });

    parentLinks.forEach((link, index) => {
      const styles = window.getComputedStyle(link);
      console.log(`\n%c父级链接 ${index + 1}（子项被选中）:`, 'color: #f59e0b; font-weight: bold;');
      console.log(`  文本: ${link.textContent?.trim()}`);
      console.log(`  背景色: ${styles.backgroundColor}`);
      console.log(`  文字颜色: ${styles.color}`);
      console.log(`  字体粗细: ${styles.fontWeight}`);
    });
  }

  // 检测博客和文档页面样式
  function checkBlogStyles() {
    console.log('\n%c📝 博客/文档页面样式检查', 'color: #2563eb; font-weight: bold;');
    
    // 先尝试博客页面
    let blogMarkdown = document.querySelector('.blog-wrapper article .markdown, .blog-wrapper .markdown, article .markdown');
    // 如果不是博客页面，尝试文档页面
    if (!blogMarkdown) {
      blogMarkdown = document.querySelector('.theme-doc-markdown.markdown, .theme-doc-markdown, .markdown');
    }
    
    if (blogMarkdown) {
      const styles = window.getComputedStyle(blogMarkdown);
      const classes = blogMarkdown.className;
      const parentClasses = blogMarkdown.closest('article')?.className || 
                           blogMarkdown.closest('.blog-wrapper')?.className || 
                           blogMarkdown.closest('.theme-doc-markdown')?.className || '';
      const pageType = classes.includes('theme-doc-markdown') ? '文档页面' : '博客页面';
      console.log(`${pageType}容器:`);
      console.log(`  类名: ${classes}`);
      console.log(`  父级类名: ${parentClasses}`);
      console.log(`  文字颜色: ${styles.color}`);
      console.log(`  背景色: ${styles.backgroundColor}`);
      console.log(`  元素路径:`, blogMarkdown);
      
      // 检查子元素
      const paragraphs = blogMarkdown.querySelectorAll('p');
      const headings = blogMarkdown.querySelectorAll('h1, h2, h3, h4, h5, h6');
      const lists = blogMarkdown.querySelectorAll('ul, ol, li');
      
      console.log(`\n子元素统计:`);
      console.log(`  段落数: ${paragraphs.length}`);
      console.log(`  标题数: ${headings.length}`);
      console.log(`  列表项数: ${lists.length}`);

      if (paragraphs.length > 0) {
        const firstP = paragraphs[0];
        const pStyles = window.getComputedStyle(firstP);
        console.log(`\n第一个段落样式:`);
        console.log(`  文字颜色: ${pStyles.color}`);
        console.log(`  背景色: ${pStyles.backgroundColor}`);
        console.log(`  计算后的颜色值: ${pStyles.color}`);
      }

      if (headings.length > 0) {
        const firstH = headings[0];
        const hStyles = window.getComputedStyle(firstH);
        console.log(`\n第一个标题样式:`);
        console.log(`  文字颜色: ${hStyles.color}`);
        console.log(`  背景色: ${hStyles.backgroundColor}`);
        console.log(`  计算后的颜色值: ${hStyles.color}`);
      }
    } else {
      console.log('未检测到博客/文档文章容器');
    }
  }

  // 检测CSS变量
  function checkCSSVariables() {
    console.log('\n%c🎨 CSS变量检查', 'color: #2563eb; font-weight: bold;');
    
    const root = document.documentElement;
    const computedStyle = getComputedStyle(root);
    
    const importantVars = [
      '--ifm-color-primary',
      '--ifm-color-emphasis-100',
      '--ifm-color-emphasis-900',
      '--ifm-color-background',
      '--ifm-color-background-2',
    ];

    importantVars.forEach(varName => {
      const value = computedStyle.getPropertyValue(varName).trim();
      console.log(`  ${varName}: ${value || '(未设置)'}`);
    });
  }

  // 执行检查
  setTimeout(() => {
    checkCSSVariables();
    checkSidebarStyles();
    checkBlogStyles();
    
    console.log('\n%c=====================================', 'color: #64748b;');
    console.log('%c💡 提示: 要禁用调试，运行 localStorage.removeItem("styleDebugEnabled"); location.reload();', 
                'color: #64748b; font-size: 12px;');
  }, 500);

  // 监听主题切换
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
        const newTheme = document.documentElement.getAttribute('data-theme');
        console.log(`\n%c🔄 主题已切换为: ${newTheme}`, 
                    `color: ${newTheme === 'dark' ? '#60a5fa' : '#2563eb'}; font-weight: bold;`);
        setTimeout(() => {
          checkCSSVariables();
          checkSidebarStyles();
          checkBlogStyles();
        }, 100);
      }
    });
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });

  // 强制修复侧边栏激活的父级链接背景色
  function fixSidebarActiveParentLinks() {
    // 修复所有激活的链接，包括sublist和普通链接
    const activeLinks = document.querySelectorAll(
      '.theme-doc-sidebar-menu .menu__link--active'
    );
    const activeSublistLinks = document.querySelectorAll(
      '.theme-doc-sidebar-menu .menu__link--active.menu__link--sublist, ' +
      '.theme-doc-sidebar-menu .menu__link--active.menu__link--sublist-caret'
    );
    
    // 先处理所有激活的链接（深色主题统一处理）
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    if (theme === 'dark') {
      activeLinks.forEach(link => {
        const bgColor = '#3b82f6';
        link.style.setProperty('background-color', bgColor, 'important');
        link.style.setProperty('background', bgColor, 'important');
        link.style.setProperty('background-image', 'none', 'important');
        link.style.setProperty('color', '#ffffff', 'important');
      });
    }
    
    activeSublistLinks.forEach(link => {
      const theme = document.documentElement.getAttribute('data-theme') || 'light';
      const isSublistCaret = link.classList.contains('menu__link--sublist-caret');
      
      // 深色主题：所有激活的链接（包括sublist）都用蓝色背景+白色文字
      // 浅色主题：所有sublist链接（包括sublist-caret）都用黑色文字+透明背景
      if (theme === 'dark') {
        const bgColor = '#3b82f6';
        // 强制设置蓝色背景和白色文字，确保覆盖所有其他规则
        link.style.setProperty('background-color', bgColor, 'important');
        link.style.setProperty('background', bgColor, 'important');
        link.style.setProperty('background-image', 'none', 'important');
        link.style.setProperty('color', '#ffffff', 'important');
        link.style.setProperty('background-clip', 'border-box', 'important');
        link.style.setProperty('background-origin', 'border-box', 'important');
      } else {
        // 浅色主题：所有sublist链接都用黑色文字+透明背景
        link.style.setProperty('background-color', 'transparent', 'important');
        link.style.setProperty('background', 'transparent', 'important');
        link.style.setProperty('background-image', 'none', 'important');
        link.style.setProperty('color', '#111827', 'important');
      }
      
      // 移除可能存在的padding-box设置
      const currentBg = link.style.getPropertyValue('background');
      if (currentBg && currentBg.includes('padding-box')) {
        link.style.removeProperty('background');
      }
      
      // 检查父元素（menu__list-item），确保它也没有背景色覆盖
      const listItem = link.closest('.menu__list-item');
      if (listItem) {
        const itemStyle = window.getComputedStyle(listItem);
        if (itemStyle.backgroundColor !== 'rgba(0, 0, 0, 0)' && 
            itemStyle.backgroundColor !== 'transparent') {
          listItem.style.setProperty('background-color', 'transparent', 'important');
        }
        
        // 检查listItem的所有直接子元素，找到展开icon容器
        Array.from(listItem.children).forEach(child => {
          if (child !== link) {
            // 这可能是展开icon的容器
            const childStyle = window.getComputedStyle(child);
            // 如果这个元素有背景色且不是蓝色，设置为透明或蓝色
            if (childStyle.backgroundColor !== 'rgba(0, 0, 0, 0)' && 
                childStyle.backgroundColor !== 'transparent' &&
                !childStyle.backgroundColor.includes('rgb(37, 99, 235)') &&
                !childStyle.backgroundColor.includes('rgb(59, 130, 246)')) {
              // 设置为透明，让父元素的蓝色背景显示
              child.style.setProperty('background-color', 'transparent', 'important');
              child.style.setProperty('background', 'transparent', 'important');
            } else if (childStyle.backgroundColor === 'rgba(0, 0, 0, 0)' || 
                       childStyle.backgroundColor === 'transparent') {
              // 如果已经是透明的，确保它不会阻挡父元素的背景
              child.style.setProperty('background-color', 'transparent', 'important');
            }
          }
        });
      }
      
      // 确保展开icon容器也有蓝色背景
      // 查找可能的icon容器（可能是子元素）
      const iconContainers = link.querySelectorAll('*');
      iconContainers.forEach(icon => {
        // 如果icon容器有背景色，设置为透明，让父元素的蓝色背景显示出来
        const computedStyle = window.getComputedStyle(icon);
        const iconBgColor = computedStyle.backgroundColor;
        // 检查是否是透明或rgba(0,0,0,0)
        if (iconBgColor && iconBgColor !== 'rgba(0, 0, 0, 0)' && 
            iconBgColor !== 'transparent' &&
            !iconBgColor.includes('rgb(37, 99, 235)') && // 浅色主题蓝色
            !iconBgColor.includes('rgb(59, 130, 246)')) { // 深色主题蓝色
          icon.style.setProperty('background-color', 'transparent', 'important');
          icon.style.setProperty('background', 'transparent', 'important');
        }
      });
      
      // 确保链接本身完全覆盖整个区域
      // 检查是否有padding或margin影响背景显示
      const linkStyles = window.getComputedStyle(link);
      const linkPadding = linkStyles.padding;
      const linkMargin = linkStyles.margin;
      // 如果padding或margin很大，可能需要调整
    });
    
    if (activeSublistLinks.length > 0) {
      console.log(`\n%c🔧 已强制修复 ${activeSublistLinks.length} 个激活的父级链接背景色`, 
                  'color: #10b981; font-weight: bold;');
    }
  }

  // 监听DOM变化，自动修复
  const sidebarObserver = new MutationObserver(() => {
    fixSidebarActiveParentLinks();
  });

  // 观察侧边栏容器的变化
  const sidebarContainer = document.querySelector('.theme-doc-sidebar-menu');
  if (sidebarContainer) {
    sidebarObserver.observe(sidebarContainer, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class']
    });
  }

  // 初始修复
  setTimeout(() => {
    fixSidebarActiveParentLinks();
  }, 100);

  // 提供手动检查函数
  window.styleDebug = {
    checkSidebar: checkSidebarStyles,
    checkBlog: checkBlogStyles,
    checkVariables: checkCSSVariables,
    fixSidebar: fixSidebarActiveParentLinks,
    checkAll: () => {
      checkCSSVariables();
      checkSidebarStyles();
      checkBlogStyles();
      fixSidebarActiveParentLinks();
    }
  };

  console.log('\n%c💡 可以使用 window.styleDebug.checkAll() 手动触发检查', 
              'color: #10b981; font-style: italic;');
  console.log('%c💡 可以使用 window.styleDebug.fixSidebar() 强制修复侧边栏背景色', 
              'color: #10b981; font-style: italic;');
}

