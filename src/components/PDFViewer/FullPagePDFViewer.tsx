import React, { useState, useRef, useEffect } from 'react';
import styles from './styles.module.css';

interface FullPagePDFViewerProps {
  src: string;
  className?: string;
  pageSpacing?: number; // 页面间距
  maxWidth?: string | number; // 最大宽度
}

const FullPagePDFViewer: React.FC<FullPagePDFViewerProps> = ({
  src,
  className = '',
  pageSpacing = 20,
  maxWidth = '100%',
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalPages, setTotalPages] = useState(0);
  const [renderedPages, setRenderedPages] = useState<HTMLCanvasElement[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const [pdfDoc, setPdfDoc] = useState<import('pdfjs-dist').PDFDocumentProxy | null>(null);

  useEffect(() => {
    loadPDF();
  }, [src]);

  const loadPDF = async () => {
    try {
      setLoading(true);
      setError(null);
      setRenderedPages([]);

      // 动态加载PDF.js
      const pdfjsLib = await import('pdfjs-dist');
      // 使用本地worker文件
      pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

      const loadingTask = pdfjsLib.getDocument(src);
      const pdf = await loadingTask.promise;
      
      setPdfDoc(pdf);
      setTotalPages(pdf.numPages);
      
      // 渲染所有页面
      await renderAllPages(pdf);
      
      setLoading(false);
    } catch (err) {
      console.error('PDF加载失败:', err);
      setError('无法加载PDF文件');
      setLoading(false);
    }
  };

  const renderAllPages = async (pdf: import('pdfjs-dist').PDFDocumentProxy) => {
    const canvases: HTMLCanvasElement[] = [];
    
    // 获取容器宽度来计算合适的缩放比例
    const containerWidth = containerRef.current?.clientWidth || 800;
    
    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      try {
        const page = await pdf.getPage(pageNum);
        
        // 计算缩放比例，使PDF页面适应容器宽度
        const viewport = page.getViewport({ scale: 1.0 });
        const scale = Math.min(containerWidth / viewport.width, 2.0); // 最大缩放2倍
        const scaledViewport = page.getViewport({ scale });
        
        // 创建canvas元素
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        canvas.height = scaledViewport.height;
        canvas.width = scaledViewport.width;
        canvas.style.display = 'block';
        canvas.style.marginBottom = `${pageSpacing}px`;
        canvas.style.maxWidth = typeof maxWidth === 'number' ? `${maxWidth}px` : maxWidth;
        canvas.style.width = '100%';
        canvas.style.height = 'auto';
        canvas.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        canvas.style.borderRadius = '4px';
        
        if (context) {
          const renderContext = {
            canvasContext: context,
            viewport: scaledViewport,
          };
          
          await page.render(renderContext).promise;
        }
        
        canvases.push(canvas);
      } catch (err) {
        console.error(`页面 ${pageNum} 渲染失败:`, err);
      }
    }
    
    setRenderedPages(canvases);
  };

  // 当容器大小改变时重新渲染
  useEffect(() => {
    const handleResize = () => {
      if (pdfDoc && renderedPages.length > 0) {
        renderAllPages(pdfDoc);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [pdfDoc, renderedPages.length]);

  // 将canvas元素添加到DOM
  useEffect(() => {
    const container = containerRef.current;
    if (container && renderedPages.length > 0) {
      // 清空容器
      container.innerHTML = '';
      
      // 添加所有渲染的页面
      renderedPages.forEach((canvas, index) => {
        const pageWrapper = document.createElement('div');
        pageWrapper.className = styles.pageWrapper || 'page-wrapper';
        pageWrapper.style.textAlign = 'center';
        pageWrapper.style.marginBottom = `${pageSpacing}px`;
        
        // 页码标识已移除
        pageWrapper.appendChild(canvas);
        container.appendChild(pageWrapper);
      });
    }
  }, [renderedPages, pageSpacing]);

  return (
    <div className={`${styles.fullPagePdfViewer || 'full-page-pdf-viewer'} ${className}`}>
      {loading && (
        <div className={styles.loading || 'loading'}>
          <div className={styles.spinner || 'spinner'}></div>
          <p>正在加载PDF...</p>
        </div>
      )}
      
      {error && (
        <div className={styles.error || 'error'}>
          <p>❌ {error}</p>
          <p>请检查文件路径是否正确</p>
          <button 
            onClick={loadPDF}
            className={styles.retryButton || 'retry-button'}
          >
            重试
          </button>
        </div>
      )}
      
      {/* 总页数显示已移除 */}
      
      <div 
        ref={containerRef}
        className={styles.pagesContainer || 'pages-container'}
        style={{
          width: '100%',
          maxWidth: typeof maxWidth === 'number' ? `${maxWidth}px` : maxWidth,
          margin: '0 auto'
        }}
      />
    </div>
  );
};

export default FullPagePDFViewer;