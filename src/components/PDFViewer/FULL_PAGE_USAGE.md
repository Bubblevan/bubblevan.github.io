# FullPagePDFViewer 使用指南

## 概述

`FullPagePDFViewer` 是一个专门用于将PDF文档完整展开显示的React组件。与传统的PDF查看器不同，它会将PDF的所有页面一次性渲染出来，用户可以通过滚动查看整个文档，无需分页操作。

## 特性

- ✅ **完整展开显示**：一次性渲染PDF的所有页面
- ✅ **自适应宽度**：根据容器宽度自动调整页面大小
- ✅ **无工具栏**：纯净的阅读体验，无打印、下载、缩放按钮
- ✅ **响应式设计**：支持不同屏幕尺寸
- ✅ **页面间距可调**：可自定义页面之间的间距
- ✅ **加载状态**：提供加载和错误状态显示

## 基本使用

```tsx
import React from 'react';
import { FullPagePDFViewer } from '@/components/PDFViewer';

const MyComponent = () => {
  return (
    <div>
      <h1>我的PDF文档</h1>
      <FullPagePDFViewer 
        src="/static/pdfs/my-document.pdf"
      />
    </div>
  );
};

export default MyComponent;
```

## 高级配置

```tsx
import React from 'react';
import { FullPagePDFViewer } from '@/components/PDFViewer';

const AdvancedExample = () => {
  return (
    <div className="pdf-container">
      <FullPagePDFViewer 
        src="/static/pdfs/large-document.pdf"
        className="custom-pdf-viewer"
        pageSpacing={30}  // 页面间距30px
        maxWidth={800}    // 最大宽度800px
      />
    </div>
  );
};

export default AdvancedExample;
```

## Props 参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `src` | `string` | - | PDF文件的URL路径（必需） |
| `className` | `string` | `''` | 自定义CSS类名 |
| `pageSpacing` | `number` | `20` | 页面之间的间距（像素） |
| `maxWidth` | `string \| number` | `'100%'` | 容器的最大宽度 |

## 在Markdown中使用

如果你想在MDX文件中使用这个组件：

```mdx
import { FullPagePDFViewer } from '@/components/PDFViewer';

# 我的文档标题

这里是一些介绍文字...

<FullPagePDFViewer 
  src="/static/pdfs/误差理论与数据处理.pdf"
  pageSpacing={25}
  maxWidth={900}
/>

继续其他内容...
```

## 样式自定义

你可以通过CSS来进一步自定义样式：

```css
/* 自定义容器样式 */
.custom-pdf-viewer {
  background-color: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
}

/* 自定义页面包装器 */
.custom-pdf-viewer .page-wrapper {
  margin-bottom: 40px;
}

/* 自定义加载状态 */
.custom-pdf-viewer .loading {
  text-align: center;
  padding: 50px;
  color: #666;
}
```

## 性能考虑

- **大文件处理**：对于页数很多的PDF文件，组件会一次性渲染所有页面，可能会消耗较多内存
- **网络优化**：建议将PDF文件放在CDN或静态资源服务器上
- **移动端适配**：在移动设备上，大型PDF可能需要更长的加载时间

## 与其他PDF组件的对比

| 组件 | 显示方式 | 工具栏 | 适用场景 |
|------|----------|--------|----------|
| `PDFViewer` | iframe嵌入 | 浏览器默认 | 简单预览 |
| `AdvancedPDFViewer` | 分页显示 | 完整工具栏 | 交互式阅读 |
| `FullPagePDFViewer` | 完整展开 | 无工具栏 | 文档展示、打印预览 |

## 故障排除

### PDF无法加载
- 检查PDF文件路径是否正确
- 确保PDF文件可以通过浏览器直接访问
- 检查CORS设置（如果PDF在不同域名下）

### 页面显示不完整
- 检查容器的CSS样式是否限制了高度
- 确保没有`overflow: hidden`等样式影响显示

### 性能问题
- 考虑使用较小的PDF文件
- 可以考虑将大PDF拆分成多个小文件
- 在移动端可以考虑使用分页版本的组件

## 示例项目

查看 `src/components/PDFViewer/examples/` 目录下的完整示例代码。