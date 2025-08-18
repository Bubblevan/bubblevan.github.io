import React, { useState, useRef, useEffect } from 'react';
import styles from './styles.module.css';

interface PDFViewerProps {
  src: string;
  title?: string;
  width?: string | number;
  height?: string | number;
  showToolbar?: boolean;
  className?: string;
}

const PDFViewer: React.FC<PDFViewerProps> = ({
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
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
  }, [src]);

  const handleLoad = () => {
    setLoading(false);
  };

  const handleError = () => {
    setLoading(false);
    setError('无法加载PDF文件');
  };

  const zoomIn = () => {
    setScale(prev => Math.min(prev + 0.2, 3.0));
  };

  const zoomOut = () => {
    setScale(prev => Math.max(prev - 0.2, 0.5));
  };

  const resetZoom = () => {
    setScale(1.0);
  };

  const downloadPDF = () => {
    const link = document.createElement('a');
    link.href = src;
    link.download = title;
    link.click();
  };

  return (
    <div className={`${styles.pdfViewer} ${className}`}>
      <div className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        {showToolbar && (
          <div className={styles.toolbar}>
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
          </div>
        )}
        
        <iframe
          ref={iframeRef}
          src={`${src}#toolbar=${showToolbar ? '1' : '0'}&navpanes=1&scrollbar=1&view=FitH`}
          width={width}
          height={height}
          className={styles.pdfFrame}
          onLoad={handleLoad}
          onError={handleError}
          style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}
          title={title}
        />
      </div>
    </div>
  );
};

export default PDFViewer; 