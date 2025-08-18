import React, { useState, useRef, useEffect } from 'react';
import styles from './styles.module.css';

interface AdvancedPDFViewerProps {
  src: string;
  title?: string;
  width?: string | number;
  height?: string | number;
  showToolbar?: boolean;
  className?: string;
}

const AdvancedPDFViewer: React.FC<AdvancedPDFViewerProps> = ({
  src,
  title = 'PDF文档',
  width = '100%',
  height = '600px',
  showToolbar = true,
  className = '',
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.0);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdfDoc, setPdfDoc] = useState<import('pdfjs-dist').PDFDocumentProxy | null>(null);

  useEffect(() => {
    loadPDF();
  }, [src]);

  const loadPDF = async () => {
    try {
      setLoading(true);
      setError(null);

      // 动态加载PDF.js
      const pdfjsLib = await import('pdfjs-dist');
      // 使用本地worker文件
      pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

      const loadingTask = pdfjsLib.getDocument(src);
      const pdf = await loadingTask.promise;
      
      setPdfDoc(pdf);
      setTotalPages(pdf.numPages);
      setCurrentPage(1);
      setLoading(false);
      
      renderPage(pdf, 1);
    } catch (err) {
      console.error('PDF加载失败:', err);
      setError('无法加载PDF文件');
      setLoading(false);
    }
  };

  const renderPage = async (pdf: import('pdfjs-dist').PDFDocumentProxy, pageNum: number) => {
    try {
      const page = await pdf.getPage(pageNum);
      const canvas = canvasRef.current;
      if (!canvas) return;

      const viewport = page.getViewport({ scale });
      const context = canvas.getContext('2d');

      canvas.height = viewport.height;
      canvas.width = viewport.width;

      const renderContext = {
        canvasContext: context,
        viewport: viewport,
      };

      await page.render(renderContext).promise;
    } catch (err) {
      console.error('页面渲染失败:', err);
      setError('页面渲染失败');
    }
  };

  const goToPage = (pageNum: number) => {
    if (pageNum >= 1 && pageNum <= totalPages && pdfDoc) {
      setCurrentPage(pageNum);
      renderPage(pdfDoc, pageNum);
    }
  };

  const changeScale = (newScale: number) => {
    setScale(newScale);
    if (pdfDoc) {
      renderPage(pdfDoc, currentPage);
    }
  };

  const zoomIn = () => {
    changeScale(Math.min(scale + 0.2, 3.0));
  };

  const zoomOut = () => {
    changeScale(Math.max(scale - 0.2, 0.5));
  };

  const resetZoom = () => {
    changeScale(1.0);
  };

  const downloadPDF = () => {
    const link = document.createElement('a');
    link.href = src;
    link.download = title;
    link.click();
  };

  const printPDF = () => {
    window.open(src, '_blank');
  };

  return (
    <div className={`${styles.pdfViewer} ${className}`}>
      <div className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        {showToolbar && (
          <div className={styles.toolbar}>
            <button 
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              className={styles.toolbarButton}
              title="上一页"
            >
              ◀
            </button>
            
            <span className={styles.pageInfo}>
              {currentPage} / {totalPages}
            </span>
            
            <button 
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className={styles.toolbarButton}
              title="下一页"
            >
              ▶
            </button>
            
            <div className={styles.separator}></div>
            
            <button 
              onClick={zoomOut} 
              className={styles.toolbarButton}
              title="缩小"
            >
              🔍-
            </button>
            
            <span className={styles.scaleInfo}>{Math.round(scale * 100)}%</span>
            
            <button 
              onClick={zoomIn} 
              className={styles.toolbarButton}
              title="放大"
            >
              🔍+
            </button>
            
            <button 
              onClick={resetZoom} 
              className={styles.toolbarButton}
              title="重置缩放"
            >
              🔄
            </button>
            
            <div className={styles.separator}></div>
            
            <button 
              onClick={printPDF} 
              className={styles.toolbarButton}
              title="打印"
            >
              🖨️
            </button>
            
            <button 
              onClick={downloadPDF} 
              className={styles.toolbarButton}
              title="下载PDF"
            >
              📥
            </button>
          </div>
        )}
      </div>
      
      <div className={styles.container}>
        {loading && (
          <div className={styles.loading}>
            <div className={styles.spinner}></div>
            <p>正在加载PDF...</p>
          </div>
        )}
        
        {error && (
          <div className={styles.error}>
            <p>❌ {error}</p>
            <p>请检查文件路径是否正确</p>
            <button 
              onClick={loadPDF}
              className={styles.retryButton}
            >
              重试
            </button>
          </div>
        )}
        
        <div className={styles.canvasContainer}>
          <canvas
            ref={canvasRef}
            className={styles.pdfCanvas}
            style={{ width, height: 'auto' }}
          />
        </div>
      </div>
    </div>
  );
};

export default AdvancedPDFViewer;