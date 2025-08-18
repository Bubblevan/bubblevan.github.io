import React from 'react';
import { FullPagePDFViewer } from '../index';

/**
 * FullPagePDFViewer 使用示例
 * 展示如何将PDF完整展开显示
 */
const FullPageExample: React.FC = () => {
  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '30px' }}>PDF完整展开示例</h1>
      
      {/* 基础使用示例 */}
      <section style={{ marginBottom: '50px' }}>
        <h2>基础使用</h2>
        <p>这是最简单的使用方式，PDF会自动适应容器宽度：</p>
        <FullPagePDFViewer 
          src="/static/pdfs/误差理论与数据处理.pdf"
        />
      </section>
      
      {/* 自定义配置示例 */}
      <section style={{ marginBottom: '50px' }}>
        <h2>自定义配置</h2>
        <p>可以自定义页面间距和最大宽度：</p>
        <FullPagePDFViewer 
          src="/static/pdfs/生物医学图像处理复习笔记.pdf"
          pageSpacing={30}
          maxWidth={800}
          className="custom-pdf-viewer"
        />
      </section>
      
      {/* 小尺寸PDF示例 */}
      <section style={{ marginBottom: '50px' }}>
        <h2>紧凑显示</h2>
        <p>适合较小的PDF文档或需要紧凑显示的场景：</p>
        <FullPagePDFViewer 
          src="/static/pdfs/传感HW1.pdf"
          pageSpacing={10}
          maxWidth={600}
        />
      </section>
    </div>
  );
};

export default FullPageExample;

/**
 * 在MDX文件中的使用示例：
 * 
 * ```mdx
 * import { FullPagePDFViewer } from '@/components/PDFViewer';
 * 
 * # 误差处理与数据分析
 * 
 * 这是课程的复习笔记，包含了所有重要的概念和公式。
 * 
 * <FullPagePDFViewer 
 *   src="/static/pdfs/误差理论与数据处理.pdf"
 *   pageSpacing={25}
 *   maxWidth={900}
 * />
 * 
 * ## 总结
 * 
 * 通过上述PDF内容，我们可以看到...
 * ```
 */

/**
 * 样式自定义示例：
 * 
 * ```css
 * .custom-pdf-viewer {
 *   background-color: #fafafa;
 *   border: 1px solid #e0e0e0;
 *   border-radius: 12px;
 *   padding: 20px;
 *   box-shadow: 0 4px 12px rgba(0,0,0,0.1);
 * }
 * 
 * .custom-pdf-viewer .page-wrapper {
 *   margin-bottom: 40px;
 *   transition: transform 0.2s ease;
 * }
 * 
 * .custom-pdf-viewer .page-wrapper:hover {
 *   transform: translateY(-2px);
 * }
 * 
 * .custom-pdf-viewer .loading {
 *   background: linear-gradient(45deg, #f0f0f0, #e0e0e0);
 *   border-radius: 8px;
 *   padding: 40px;
 *   text-align: center;
 * }
 * ```
 */