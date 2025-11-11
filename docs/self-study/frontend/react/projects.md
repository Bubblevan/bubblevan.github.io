---
sidebar_position: 5
---

import BrowserWindow from '@site/src/components/BrowserWindow';
import Marquee from '@site/src/components/magicui/marquee';
import HighlightBlock, { TipBlock, WarningBlock } from '@site/src/components/HighlightBlock';

# 实战项目

用 React 可以做很多厉害的东西，像是笔者之前参加的创赛，其考古报告提取的前端我记得就是用 React 写的，然后一些入门的项目（像是 XLAB 万年不变的评论区）我也写过，不过最近的实践貌似都集中在一些博客/知识库网站构建的应用上，这里就以Docusaurus所用到的组件来进行说明。


## BrowserWindow 组件

`BrowserWindow` 组件用于模拟一个浏览器窗口，通常用于展示项目截图或嵌入其他内容，提供一个更具沉浸感的视觉体验。

### 功能与用途

- **模拟浏览器 UI**：包含窗口按钮（关闭、最小化、最大化）、地址栏和菜单图标，创造出逼真的浏览器外观。
- **内容嵌入**：通过 `children` prop，可以在窗口主体内嵌入任何 React 内容，如图片、文本或交互式组件。
- **可定制性**：支持通过 `minHeight` 和 `url` props 自定义最小高度和地址栏中显示的链接。

### 代码解析 (`src/components/BrowserWindow/index.tsx`)

```tsx
import React from 'react';
import styles from './styles.module.css';

function BrowserWindow({ children, minHeight, url }) {
  return (
    <div className={styles.browserWindow} style={{ minHeight }}>
      <div className={styles.browserWindowHeader}>
        <div className={styles.buttons}>
          <span className={styles.dot} style={{ background: '#f25f58' }} />
          <span className={styles.dot} style={{ background: '#fbbe3c' }} />
          <span className={styles.dot} style={{ background: '#58cb42' }} />
        </div>
        
        <div className={styles.browserWindowAddressBar}>{url}</div>
        <div className={styles.browserWindowMenuIcon}>
          <div>
            <span className={styles.bar} />
            <span className={styles.bar} />
            <span className={styles.bar} />
          </div>
        </div>
      </div>
      <div className={styles.browserWindowBody}>{children}</div>
    </div>
  );
}

export default BrowserWindow;
```

- **Props**：
  - `children`：任何可渲染的 React 节点，将显示在窗口主体中。
  - `minHeight`：窗口的最小高度，通过内联样式设置。
  - `url`：显示在地址栏中的 URL 字符串。
- **结构**：组件由头部 (`browserWindowHeader`) 和主体 (`browserWindowBody`) 组成。头部包含了模拟的窗口控件和地址栏，而主体则通过 `{children}` 渲染传入的内容。
- **样式**：组件的样式由 `styles.module.css` 文件定义，实现了 CSS 模块化，避免了全局样式冲突。

### 使用示例

你可以在 MDX 文件中这样使用它，来展示一张图片：

```mdx
<BrowserWindow url="https://example.com">
  <img src="/img/screenshot.png" alt="示例截图" />
</BrowserWindow>
```

<BrowserWindow url="https://bubblevan-now.dev/docs" minHeight="420px">
  <img
    src="/img/react/react5.png"
    alt="BrowserWindow 组件在本站的实际视觉效果"
  />
</BrowserWindow>

## Marquee 跑马灯组件

`Marquee` 是一个高度可定制的跑马灯组件，用于创建平滑滚动的动画效果，常用于展示客户 Logo、特性列表或任何需要循环播放的内容。

### 功能与用途

- **无限滚动**：通过复制内容并使用 CSS 动画，实现无缝的循环滚动。
- **方向控制**：支持水平和垂直滚动。
- **交互性**：可以配置为当鼠标悬停时暂停动画。
- **可重复性**：可以指定内容重复的次数，以确保动画的连续性。

### 代码解析 (`src/components/magicui/marquee.tsx`)

```tsx
import { cn } from '../../lib/utils';

interface MarqueeProps {
  className?: string;
  reverse?: boolean;
  pauseOnHover?: boolean;
  children?: React.ReactNode;
  vertical?: boolean;
  repeat?: number;
  [key: string]: any;
}

export default function Marquee({
  className,
  reverse,
  pauseOnHover = false,
  children,
  vertical = false,
  repeat = 4,
  ...props
}: MarqueeProps) {
  return (
    <div
      {...props}
      className={cn(
        'group flex overflow-hidden p-2 [--duration:40s] [--gap:1rem] [gap:var(--gap)]',
        {
          'flex-row': !vertical,
          'flex-col': vertical,
        },
        className,
      )}
    >
      {Array(repeat)
        .fill(0)
        .map((_, i) => (
          <div
            key={i}
            className={cn('flex shrink-0 justify-around [gap:var(--gap)]', {
              'animate-marquee flex-row': !vertical,
              'animate-marquee-vertical flex-col': vertical,
              'group-hover:[animation-play-state:paused]': pauseOnHover,
              '[animation-direction:reverse]': reverse,
            })}
          >
            {children}
          </div>
        ))}
    </div>
  );
}
```

- **Props**：
  - `vertical`：如果为 `true`，则垂直滚动；否则水平滚动。
  - `reverse`：如果为 `true`，则反向滚动。
  - `pauseOnHover`：如果为 `true`，鼠标悬停时动画暂停。
  - `repeat`：内容重复的次数，默认为 4。
- **核心逻辑**：
  - 组件使用 `Array(repeat).fill(0).map(...)` 来动态创建内容的多个副本。
  - `cn` 工具函数（通常来自 `clsx` 或类似库）用于根据 props 动态地组合 CSS 类。
  - 动画本身由 CSS 类（如 `animate-marquee`）和 CSS 变量（如 `--duration`）控制，实现了表现与逻辑的分离。

### 使用示例

你可以用它来展示一系列技术图标：

```tsx
const icons = [
  // ... an array of icon components or images
];

<Marquee>
  {icons.map(icon => <div className="mx-4">{icon}</div>)}
</Marquee>
```
具体可参考首页下技术栈的跑马灯效果。

## HighlightBlock 高亮提示组件

`HighlightBlock` 是文档中常用的高亮提示组件，可用于强调注意事项、成功提示或警告信息，为读者提供更清晰的阅读导航。

### 功能与用途

- **多种类型**：通过 `type` prop 快速切换 `info`、`warning`、`success`、`tip` 等风格，内置默认图标。
- **自定义标题与图标**：可以传入 `title` 与 `icon`，满足不同语气与场景需求。
- **模块化样式**：样式隔离在 `styles.module.css` 中，便于维护。

### 代码解析 (`src/components/HighlightBlock/index.tsx`)

```tsx
import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

export default function HighlightBlock({ type = 'info', title, icon, children, className }) {
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
```

### 使用示例

```mdx
<HighlightBlock type="tip" title="使用场景">
  在复杂的教程或流程中加入提示块，可以让读者快速抓住重点或避坑信息。
</HighlightBlock>
```

<TipBlock title="学习小贴士">
  结合项目需求先挑选最核心的功能组件，再逐步扩展，可以让学习路径更清晰。
</TipBlock>

<WarningBlock title="注意">
  高亮块会占据额外的垂直空间，别忘了在文档中控制使用频率。
</WarningBlock>


这些都是你在构建自己的 React 应用时可以借鉴的宝贵经验。希望通过这些组件，你能更深入地理解 React 的核心思想，并能将这些知识应用到你未来的项目中。

