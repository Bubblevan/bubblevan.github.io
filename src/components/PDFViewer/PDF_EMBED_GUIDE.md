# PDF嵌入使用指南

## 概述

我已经为您创建了一个完整的PDF嵌入解决方案，包括：

1. **无缝融入的PDF查看器** - 完美融入页面内容，无边框分隔
2. **React PDF查看器组件** - 功能丰富的PDF查看器
3. **简单的iframe嵌入** - 直接在Markdown中嵌入PDF
4. **文件组织结构** - 重新组织的图片和PDF资源

## 文件结构

```
src/components/PDFViewer/
├── PDFViewer.tsx              # 基础PDF查看器组件
├── AdvancedPDFViewer.tsx      # 高级PDF查看器（使用PDF.js）
├── SimplePDFViewer.tsx        # 简化版PDF查看器
├── SeamlessPDFViewer.tsx      # 无缝融入PDF查看器
├── PDFViewerMDX.tsx           # MDX兼容组件
├── styles.module.css          # 样式文件
├── types.d.ts                 # 类型声明
└── index.ts                   # 导出文件

static/pdfs/
└── 电子系统设计与实践.pdf      # PDF文件

docs/undergraduate-notes/
└── 电子系统设计与实践.md       # 包含PDF嵌入的Markdown文件
```

## 使用方法

### 方法1: 无缝融入iframe（推荐，完美融入）

在Markdown文件中直接使用iframe，无边框无分隔：

```markdown
<iframe 
  src="/pdfs/您的PDF文件.pdf"
  title="PDF文档标题"
  style={{
    width: '100%',
    height: '800px',
    border: 'none',
    margin: '20px 0'
  }}
>
  <p>您的浏览器不支持PDF预览，请 <a href="/pdfs/您的PDF文件.pdf" target="_blank">点击这里下载PDF文件</a></p>
</iframe>
```

### 方法2: 使用CSS类（简洁）

```markdown
<div className="pdf-container">
  <iframe 
    src="/pdfs/您的PDF文件.pdf"
    title="PDF文档标题"
  >
    <div className="pdf-fallback">
      <p>您的浏览器不支持PDF预览，请 <a href="/pdfs/您的PDF文件.pdf" target="_blank">点击这里下载PDF文件</a></p>
    </div>
  </iframe>
</div>
```

### 方法3: 使用React组件（需要配置MDX）

如果您想使用更高级的PDF查看器，需要：

1. 安装PDF.js依赖：
   ```bash
   npm install pdfjs-dist
   ```

2. 在Docusaurus配置中注册组件
3. 使用MDX语法

## 添加新的PDF文件

1. **将PDF文件复制到static目录**：
   ```bash
   copy "您的PDF文件.pdf" "static/pdfs/"
   ```

2. **在Markdown中嵌入**：
   ```markdown
   <iframe 
     src="/pdfs/您的PDF文件.pdf"
     title="PDF文档标题"
     style={{
       width: '100%',
       height: '800px',
       border: 'none',
       margin: '20px 0'
     }}
   >
     <p>您的浏览器不支持PDF预览，请 <a href="/pdfs/您的PDF文件.pdf" target="_blank">点击这里下载PDF文件</a></p>
   </iframe>
   ```

## 功能特性

### 无缝融入方式
- ✅ 完美融入页面内容
- ✅ 无边框无分隔
- ✅ 透明背景
- ✅ 响应式设计
- ✅ 支持深色模式
- ✅ 浏览器原生PDF支持

### React组件方式
- ✅ 自定义工具栏
- ✅ 更好的用户体验
- ✅ 加载状态提示
- ✅ 错误处理
- ✅ 深色模式支持

## 样式变体

### 默认样式
```markdown
<iframe 
  src="/pdfs/文件.pdf"
  style={{
    width: '100%',
    height: '800px',
    border: 'none',
    margin: '20px 0'
  }}
>
```

### 紧凑样式
```markdown
<iframe 
  src="/pdfs/文件.pdf"
  style={{
    width: '100%',
    height: '600px',
    border: 'none',
    margin: '10px 0'
  }}
>
```

### 全屏样式
```markdown
<iframe 
  src="/pdfs/文件.pdf"
  style={{
    width: '100%',
    height: '100vh',
    border: 'none',
    margin: '0'
  }}
>
```

## 注意事项

1. **文件路径**：确保PDF文件放在`static/pdfs/`目录下
2. **文件大小**：大文件可能需要较长加载时间
3. **浏览器兼容性**：现代浏览器都支持PDF预览
4. **移动设备**：iframe在移动设备上也能正常工作
5. **样式继承**：无缝融入会继承页面的主题样式

## 示例

当前已配置的示例：
- 文件：`电子系统设计与实践.pdf`
- 路径：`/pdfs/电子系统设计与实践.pdf`
- 嵌入位置：`docs/undergraduate-notes/电子系统设计与实践.md`

## 故障排除

### PDF无法显示
1. 检查文件路径是否正确
2. 确认文件已复制到static/pdfs目录
3. 检查文件是否损坏

### 加载缓慢
1. 考虑压缩PDF文件
2. 使用CDN加速
3. 添加加载提示

### 样式问题
1. 确保使用正确的CSS变量
2. 检查深色模式兼容性
3. 测试响应式布局 