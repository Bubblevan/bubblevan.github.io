import React, { useState } from 'react';

interface SeamlessPDFViewerProps {
  src: string;
  title?: string;
  height?: string | number;
  className?: string;
  variant?: 'default' | 'compact' | 'fullscreen';
}

const SeamlessPDFViewer: React.FC<SeamlessPDFViewerProps> = ({
  src,
  title = 'PDF文档',
  height = '800px',
  className = '',
  variant = 'default',
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleLoad = () => {
    setLoading(false);
  };

  const handleError = () => {
    setLoading(false);
    setError('无法加载PDF文件');
  };

  const getContainerClass = () => {
    const baseClass = 'pdf-container';
    switch (variant) {
      case 'compact':
        return `${baseClass} ${baseClass}-compact`;
      case 'fullscreen':
        return `${baseClass} ${baseClass}-fullscreen`;
      default:
        return baseClass;
    }
  };

  return (
    <div className={`${getContainerClass()} ${className}`}>
      {loading && (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: typeof height === 'number' ? `${height}px` : height,
          fontSize: '14px',
          color: 'var(--ifm-color-emphasis-600)'
        }}>
          正在加载PDF...
        </div>
      )}
      
      {error && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: typeof height === 'number' ? `${height}px` : height,
          fontSize: '14px',
          color: 'var(--ifm-color-emphasis-600)'
        }}>
          <p>❌ {error}</p>
          <p>请检查文件路径是否正确</p>
        </div>
      )}
      
      <iframe 
        src={src}
        title={title}
        style={{
          width: '100%',
          height: variant === 'fullscreen' ? '100vh' : 
                 variant === 'compact' ? '600px' : 
                 typeof height === 'number' ? `${height}px` : height,
          border: 'none',
          display: loading || error ? 'none' : 'block'
        }}
        onLoad={handleLoad}
        onError={handleError}
      >
        <div className="pdf-fallback">
          <p>您的浏览器不支持PDF预览，请 <a href={src} target="_blank" rel="noopener noreferrer">点击这里下载PDF文件</a></p>
        </div>
      </iframe>
    </div>
  );
};

export default SeamlessPDFViewer; 